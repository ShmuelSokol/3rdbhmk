import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { extractPageAsImage } from '@/lib/pdf-utils'
import { writeFile, mkdir, readFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'
import sharp from 'sharp'

export async function GET(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const { pageId } = params

    const page = await prisma.page.findUnique({
      where: { id: pageId },
      include: {
        book: true,
        ocrResult: {
          include: {
            boxes: {
              orderBy: [{ lineIndex: 'asc' }, { wordIndex: 'asc' }],
            },
          },
        },
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    const book = page.book

    // Check for cached erased image
    const cacheDir = path.join('/tmp', 'bhmk', book.id, 'pages-erased')
    const cachedPath = path.join(cacheDir, `page-${page.pageNumber}.png`)

    if (existsSync(cachedPath)) {
      const buf = await readFile(cachedPath)
      return new NextResponse(new Uint8Array(buf), {
        headers: {
          'Content-Type': 'image/png',
          'Cache-Control': 'public, max-age=3600',
        },
      })
    }

    // Get the original page image
    const origCacheDir = path.join('/tmp', 'bhmk', book.id, 'pages')
    const origCachedPath = path.join(origCacheDir, `page-${page.pageNumber}.png`)

    let imageBuffer: Buffer
    if (existsSync(origCachedPath)) {
      imageBuffer = await readFile(origCachedPath)
    } else {
      const pdfDir = path.join('/tmp', 'bhmk', book.id)
      const pdfPath = path.join(pdfDir, book.filename)
      if (!existsSync(pdfPath)) {
        const supabase = getSupabase()
        const storagePath = `books/${book.id}/${book.filename}`
        const { data, error } = await supabase.storage
          .from('bhmk')
          .download(storagePath)
        if (error || !data) throw new Error('Failed to download PDF')
        await mkdir(pdfDir, { recursive: true })
        await writeFile(pdfPath, Buffer.from(await data.arrayBuffer()))
      }
      imageBuffer = await extractPageAsImage(pdfPath, page.pageNumber)
      await mkdir(origCacheDir, { recursive: true })
      await writeFile(origCachedPath, imageBuffer)
    }

    // Get image dimensions
    const metadata = await sharp(imageBuffer).metadata()
    const imgW = metadata.width || 1655
    const imgH = metadata.height || 2340

    // Get OCR boxes — skip header lines (top 4%) and skipTranslation boxes
    const boxes = (page.ocrResult?.boxes || []).filter(
      (b) => !b.skipTranslation && b.y >= 4
    )

    if (boxes.length === 0) {
      // No text to erase, return original
      return new NextResponse(new Uint8Array(imageBuffer), {
        headers: {
          'Content-Type': 'image/png',
          'Cache-Control': 'public, max-age=3600',
        },
      })
    }

    // Group boxes into lines
    const lineMap = new Map<number, typeof boxes>()
    for (const box of boxes) {
      const li = box.lineIndex ?? -1
      if (!lineMap.has(li)) lineMap.set(li, [])
      lineMap.get(li)!.push(box)
    }

    // Sample background color from page margins (left 2% strip, middle vertical area)
    // This gives us the paper color to use for erasing
    const sampleX = 0
    const sampleY = Math.round(imgH * 0.3)
    const sampleW = Math.max(1, Math.round(imgW * 0.02))
    const sampleH = Math.max(1, Math.round(imgH * 0.1))
    const sampleBuf = await sharp(imageBuffer)
      .extract({ left: sampleX, top: sampleY, width: sampleW, height: sampleH })
      .raw()
      .toBuffer()
    // Average the sampled pixels
    let rSum = 0, gSum = 0, bSum = 0
    const pixelCount = sampleBuf.length / 3
    for (let i = 0; i < sampleBuf.length; i += 3) {
      rSum += sampleBuf[i]
      gSum += sampleBuf[i + 1]
      bSum += sampleBuf[i + 2]
    }
    const bgR = Math.round(rSum / pixelCount)
    const bgG = Math.round(gSum / pixelCount)
    const bgB = Math.round(bSum / pixelCount)

    // Create erasure rectangles for each line
    const composites: sharp.OverlayOptions[] = []

    lineMap.forEach((lineBoxes) => {
      // Bounding rect of the line (coordinates are percentages 0-100)
      const minX = Math.min(...lineBoxes.map((b) => b.x))
      const minY = Math.min(...lineBoxes.map((b) => b.y))
      const maxX = Math.max(...lineBoxes.map((b) => b.x + b.width))
      const maxY = Math.max(...lineBoxes.map((b) => b.y + b.height))

      // Convert to pixels with small padding
      const pad = 0.3 // percentage padding
      const pxLeft = Math.max(0, Math.round(((minX - pad) / 100) * imgW))
      const pxTop = Math.max(0, Math.round(((minY - pad) / 100) * imgH))
      const pxRight = Math.min(imgW, Math.round(((maxX + pad) / 100) * imgW))
      const pxBottom = Math.min(imgH, Math.round(((maxY + pad) / 100) * imgH))
      const pxW = pxRight - pxLeft
      const pxH = pxBottom - pxTop

      if (pxW > 0 && pxH > 0) {
        composites.push({
          input: Buffer.from(
            `<svg width="${pxW}" height="${pxH}">
              <rect width="${pxW}" height="${pxH}" fill="rgb(${bgR},${bgG},${bgB})" />
            </svg>`
          ),
          left: pxLeft,
          top: pxTop,
        })
      }
    })

    // Apply all erasure rectangles
    let result = sharp(imageBuffer)
    if (composites.length > 0) {
      result = result.composite(composites)
    }
    const erasedBuffer = await result.png().toBuffer()

    // Cache the result
    await mkdir(cacheDir, { recursive: true })
    await writeFile(cachedPath, erasedBuffer)

    return new NextResponse(new Uint8Array(erasedBuffer), {
      headers: {
        'Content-Type': 'image/png',
        'Cache-Control': 'public, max-age=3600',
      },
    })
  } catch (error) {
    console.error('Error creating erased image:', error)
    return NextResponse.json(
      { error: 'Failed to create erased image' },
      { status: 500 }
    )
  }
}
