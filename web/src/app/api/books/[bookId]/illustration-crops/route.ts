import { NextResponse } from 'next/server'
import { readFile, writeFile, mkdir } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'
import { getSupabase } from '@/lib/supabase'

const BUNDLED_PATH = path.join(process.cwd(), 'public', 'illustration-crops.json')
const TMP_PATH = '/tmp/illustration-crops-edits.json'
const SUPABASE_PATH = 'config/illustration-crops-v3.json'

export async function GET() {
  try {
    // 1. Check /tmp for recent edits (fastest, always fresh)
    if (existsSync(TMP_PATH)) {
      const raw = await readFile(TMP_PATH, 'utf-8')
      return NextResponse.json(JSON.parse(raw), {
        headers: { 'Cache-Control': 'no-cache' },
      })
    }

    // 2. Try Supabase (has persisted user edits)
    try {
      const supabase = getSupabase()
      const { data, error } = await supabase.storage.from('bhmk').download(SUPABASE_PATH)
      if (!error && data) {
        const text = await data.text()
        const parsed = JSON.parse(text)
        if (Object.keys(parsed).length > 1) {
          // Cache to /tmp for fast reads
          try { await writeFile(TMP_PATH, text, 'utf-8') } catch {}
          return NextResponse.json(parsed, {
            headers: { 'Cache-Control': 'no-cache' },
          })
        }
      }
    } catch { /* fall through */ }

    // 3. Fall back to bundled file
    if (existsSync(BUNDLED_PATH)) {
      const raw = await readFile(BUNDLED_PATH, 'utf-8')
      return NextResponse.json(JSON.parse(raw), {
        headers: { 'Cache-Control': 'no-cache' },
      })
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

    // 1. Write to /tmp immediately (fast, available for next GET)
    await writeFile(TMP_PATH, jsonStr, 'utf-8')

    // 2. Persist to Supabase (survives container restarts)
    try {
      const supabase = getSupabase()
      await supabase.storage.from('bhmk').upload(
        SUPABASE_PATH,
        Buffer.from(jsonStr),
        { contentType: 'application/json', upsert: true }
      )
    } catch (e) {
      console.error('Supabase save error (tmp save succeeded):', e)
    }

    // 3. Try local public/ write (dev only)
    try { await writeFile(BUNDLED_PATH, jsonStr, 'utf-8') } catch {}

    return NextResponse.json({ ok: true })
  } catch (error) {
    console.error('Error saving illustration-crops:', error)
    return NextResponse.json(
      { error: 'Failed to save crops' },
      { status: 500 }
    )
  }
}
