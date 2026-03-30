import { NextResponse } from 'next/server'
import { readFile, writeFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'
import { getSupabase } from '@/lib/supabase'

const BUNDLED_PATH = path.join(process.cwd(), 'public', 'illustration-crops.json')
const TMP_PATH = '/tmp/illustration-crops-edits.json'
const TMP_TS_PATH = '/tmp/illustration-crops-ts.txt'

// Use timestamped Supabase path to bust CDN cache
function getSupabasePath() {
  return 'config/illustration-crops-live.json'
}

export async function GET() {
  try {
    // 1. Check /tmp for recent edits on THIS container
    if (existsSync(TMP_PATH)) {
      const raw = await readFile(TMP_PATH, 'utf-8')
      const parsed = JSON.parse(raw)
      if (Object.keys(parsed).length > 1) {
        return NextResponse.json(parsed, {
          headers: { 'Cache-Control': 'no-store, no-cache, must-revalidate' },
        })
      }
    }

    // 2. Try Supabase with cache-bust
    try {
      const supabase = getSupabase()
      const { data, error } = await supabase.storage.from('bhmk').download(getSupabasePath())
      if (!error && data) {
        const text = await data.text()
        const parsed = JSON.parse(text)
        if (Object.keys(parsed).length > 1) {
          // Cache to /tmp
          try { await writeFile(TMP_PATH, text, 'utf-8') } catch {}
          return NextResponse.json(parsed, {
            headers: { 'Cache-Control': 'no-store, no-cache, must-revalidate' },
          })
        }
      }
    } catch { /* fall through */ }

    // 3. Fall back to bundled file
    if (existsSync(BUNDLED_PATH)) {
      const raw = await readFile(BUNDLED_PATH, 'utf-8')
      return NextResponse.json(JSON.parse(raw), {
        headers: { 'Cache-Control': 'no-store, no-cache, must-revalidate' },
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
    const jsonStr = JSON.stringify(body)

    // 1. Write to /tmp (instant for this container)
    await writeFile(TMP_PATH, jsonStr, 'utf-8')

    // 2. Delete old + upload new to Supabase (bust CDN cache)
    try {
      const supabase = getSupabase()
      const p = getSupabasePath()
      await supabase.storage.from('bhmk').remove([p])
      await supabase.storage.from('bhmk').upload(p, Buffer.from(jsonStr), {
        contentType: 'application/json',
      })
    } catch (e) {
      console.error('Supabase persist error:', e)
    }

    return NextResponse.json({ ok: true })
  } catch (error) {
    console.error('Error saving illustration-crops:', error)
    return NextResponse.json({ error: 'Failed to save' }, { status: 500 })
  }
}
