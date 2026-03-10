import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { extractPageAsImage } from '@/lib/pdf-utils'
import { writeFile, mkdir, readFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'

export async function GET(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const { pageId } = params

    const page = await prisma.page.findUnique({
      where: { id: pageId },
      include: { book: true },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    const book = page.book

    // Check for cached page image
    const cacheDir = path.join('/tmp', 'bhmk', book.id, 'pages')
    const cachedImagePath = path.join(cacheDir, `page-${page.pageNumber}.png`)

    if (existsSync(cachedImagePath)) {
      const imageBuffer = await readFile(cachedImagePath)
      return new NextResponse(new Uint8Array(imageBuffer), {
        headers: {
          'Content-Type': 'image/png',
          'Cache-Control': 'public, max-age=3600',
        },
      })
    }

    // Get the PDF - check /tmp cache first, then download from Supabase
    const pdfDir = path.join('/tmp', 'bhmk', book.id)
    const pdfPath = path.join(pdfDir, book.filename)

    if (!existsSync(pdfPath)) {
      const supabase = getSupabase()
      const storagePath = `books/${book.id}/${book.filename}`
      const { data, error } = await supabase.storage
        .from('bhmk')
        .download(storagePath)

      if (error || !data) {
        console.error('Failed to download PDF from Supabase:', error)
        return NextResponse.json(
          { error: 'Failed to retrieve PDF' },
          { status: 500 }
        )
      }

      await mkdir(pdfDir, { recursive: true })
      const pdfBuffer = Buffer.from(await data.arrayBuffer())
      await writeFile(pdfPath, pdfBuffer)
    }

    // Extract the page as an image
    const imageBuffer = await extractPageAsImage(pdfPath, page.pageNumber)

    // Cache the extracted image
    await mkdir(cacheDir, { recursive: true })
    await writeFile(cachedImagePath, imageBuffer)

    return new NextResponse(new Uint8Array(imageBuffer), {
      headers: {
        'Content-Type': 'image/png',
        'Cache-Control': 'public, max-age=3600',
      },
    })
  } catch (error) {
    console.error('Error getting page image:', error)
    return NextResponse.json(
      { error: 'Failed to get page image' },
      { status: 500 }
    )
  }
}
