import { NextResponse } from 'next/server'
import { readFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'

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

    const cachedPath = path.join('/tmp', 'bhmk', bookId, 'pages', `page-${pageNum}.png`)

    if (!existsSync(cachedPath)) {
      return NextResponse.json(
        { error: `Page image not found: page-${pageNum}.png. Run OCR on this page first.` },
        { status: 404 }
      )
    }

    const buffer = await readFile(cachedPath)
    return new NextResponse(new Uint8Array(buffer), {
      headers: {
        'Content-Type': 'image/png',
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
