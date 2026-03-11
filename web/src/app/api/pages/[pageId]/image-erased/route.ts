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
    const cacheDir = path.join('/tmp', 'bhmk', book.id, 'pages-erased-v3')
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

    // Load raw pixel data once for local color sampling
    const rawPixels = await sharp(imageBuffer).raw().toBuffer()
    const channels = metadata.channels || 3

    // Sample the local background color around a pixel region
    // Filter out dark pixels (text/grid lines) to get the true background color
    const sampleLocalBg = (pxLeft: number, pxTop: number, pxRight: number, pxBottom: number): [number, number, number] => {
      let rSum = 0, gSum = 0, bSum = 0, count = 0
      const stripW = Math.max(5, Math.round((pxRight - pxLeft) * 0.03))
      const stripH = Math.max(5, Math.round((pxBottom - pxTop) * 0.15))

      const regions = [
        // Left strip
        { x0: Math.max(0, pxLeft - stripW), y0: pxTop, x1: pxLeft, y1: pxBottom },
        // Right strip
        { x0: pxRight, y0: pxTop, x1: Math.min(imgW, pxRight + stripW), y1: pxBottom },
        // Strip above
        { x0: pxLeft, y0: Math.max(0, pxTop - stripH), x1: pxRight, y1: pxTop },
        // Strip below
        { x0: pxLeft, y0: pxBottom, x1: pxRight, y1: Math.min(imgH, pxBottom + stripH) },
      ]

      for (const { x0, y0, x1, y1 } of regions) {
        for (let y = y0; y < y1; y += 2) {
          for (let x = x0; x < x1; x += 2) {
            const idx = (y * imgW + x) * channels
            const r = rawPixels[idx]
            const g = rawPixels[idx + 1]
            const b = rawPixels[idx + 2]
            // Skip dark pixels (text, grid lines) — only sample background
            const lum = r * 0.299 + g * 0.587 + b * 0.114
            if (lum < 140) continue
            rSum += r
            gSum += g
            bSum += b
            count++
          }
        }
      }

      if (count === 0) return [255, 255, 255]
      return [Math.round(rSum / count), Math.round(gSum / count), Math.round(bSum / count)]
    }

    // Create erasure rectangles for each line with locally-sampled colors
    const composites: sharp.OverlayOptions[] = []

    lineMap.forEach((lineBoxes) => {
      const minX = Math.min(...lineBoxes.map((b) => b.x))
      const minY = Math.min(...lineBoxes.map((b) => b.y))
      const maxX = Math.max(...lineBoxes.map((b) => b.x + b.width))
      const maxY = Math.max(...lineBoxes.map((b) => b.y + b.height))

      const pad = 0.3
      const pxLeft = Math.max(0, Math.round(((minX - pad) / 100) * imgW))
      const pxTop = Math.max(0, Math.round(((minY - pad) / 100) * imgH))
      const pxRight = Math.min(imgW, Math.round(((maxX + pad) / 100) * imgW))
      const pxBottom = Math.min(imgH, Math.round(((maxY + pad) / 100) * imgH))
      const pxW = pxRight - pxLeft
      const pxH = pxBottom - pxTop

      if (pxW > 0 && pxH > 0) {
        const [r, g, b] = sampleLocalBg(pxLeft, pxTop, pxRight, pxBottom)
        composites.push({
          input: Buffer.from(
            `<svg width="${pxW}" height="${pxH}">
              <rect width="${pxW}" height="${pxH}" fill="rgb(${r},${g},${b})" />
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
