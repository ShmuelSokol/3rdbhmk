import { NextResponse } from 'next/server'
import { readFile, writeFile, mkdir } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'
import { getSupabase } from '@/lib/supabase'

export async function GET(
  request: Request,
  { params }: { params: { bookId: string } }
) {
  try {
    const { bookId } = params
    const url = new URL(request.url)
    const pageNum = url.searchParams.get('page')

    if (!pageNum) {
      return NextResponse.json({ error: 'Missing page parameter' }, { status: 400 })
    }

    // Try local cache first (PNG)
    const cachedPng = path.join('/tmp', 'bhmk', bookId, 'pages', `page-${pageNum}.png`)
    if (existsSync(cachedPng)) {
      const buffer = await readFile(cachedPng)
      return new NextResponse(new Uint8Array(buffer), {
        headers: {
          'Content-Type': 'image/png',
          'Cache-Control': 'public, max-age=3600',
        },
      })
    }

    // Try local cache (JPG)
    const cachedJpg = path.join('/tmp', 'bhmk', bookId, 'pages', `page-${pageNum}.jpg`)
    if (existsSync(cachedJpg)) {
      const buffer = await readFile(cachedJpg)
      return new NextResponse(new Uint8Array(buffer), {
        headers: {
          'Content-Type': 'image/jpeg',
          'Cache-Control': 'public, max-age=3600',
        },
      })
    }

    // Fetch from Supabase storage
    const supabase = getSupabase()
    const storagePath = `pages/${bookId}/page-${pageNum}.jpg`
    const { data, error } = await supabase.storage.from('bhmk').download(storagePath)

    if (error || !data) {
      return NextResponse.json(
        { error: `Page image not found for page ${pageNum}` },
        { status: 404 }
      )
    }

    const buffer = Buffer.from(await data.arrayBuffer())

    // Cache locally for next time
    try {
      const cacheDir = path.join('/tmp', 'bhmk', bookId, 'pages')
      await mkdir(cacheDir, { recursive: true })
      await writeFile(cachedJpg, buffer)
    } catch { /* cache write failure is non-fatal */ }

    return new NextResponse(new Uint8Array(buffer), {
      headers: {
        'Content-Type': 'image/jpeg',
        'Cache-Control': 'public, max-age=3600',
      },
    })
  } catch (error) {
    console.error('Error serving page image:', error)
    return NextResponse.json(
      { error: 'Failed to get page image' },
      { status: 500 }
    )
  }
}
