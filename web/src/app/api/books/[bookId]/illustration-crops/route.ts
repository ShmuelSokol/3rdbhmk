import { NextResponse } from 'next/server'
import { readFile, writeFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'
import { getSupabase } from '@/lib/supabase'

const LOCAL_PATH = path.join(process.cwd(), 'public', 'illustration-crops.json')
const SUPABASE_PATH = 'config/illustration-crops-v2.json'

export async function GET() {
  try {
    // Try Supabase first (has latest user edits)
    try {
      const supabase = getSupabase()
      const { data, error } = await supabase.storage.from('bhmk').download(SUPABASE_PATH)
      if (!error && data) {
        const text = await data.text()
        const parsed = JSON.parse(text)
        return NextResponse.json(parsed)
      }
    } catch { /* fall through to local */ }

    // Fall back to local file
    if (existsSync(LOCAL_PATH)) {
      const raw = await readFile(LOCAL_PATH, 'utf-8')
      return NextResponse.json(JSON.parse(raw))
    }

    return NextResponse.json({})
  } catch (error) {
    console.error('Error reading illustration-crops:', error)
    return NextResponse.json({}, { status: 200 })
  }
}

export async function PUT(request: Request) {
  try {
    const body = await request.json()
    const jsonStr = JSON.stringify(body, null, 2)

    // Save to Supabase (works on Railway)
    const supabase = getSupabase()
    const { error } = await supabase.storage.from('bhmk').upload(
      SUPABASE_PATH,
      Buffer.from(jsonStr),
      { contentType: 'application/json', upsert: true }
    )
    if (error) {
      console.error('Supabase save error:', error)
      throw new Error('Supabase save failed: ' + error.message)
    }

    // Also try local write (works in dev)
    try {
      await writeFile(LOCAL_PATH, jsonStr, 'utf-8')
    } catch { /* read-only fs on Railway — OK */ }

    return NextResponse.json({ ok: true })
  } catch (error) {
    console.error('Error saving illustration-crops:', error)
    return NextResponse.json(
      { error: 'Failed to save crops' },
      { status: 500 }
    )
  }
}
