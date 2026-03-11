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
    const cacheDir = path.join('/tmp', 'bhmk', book.id, 'pages-erased-v7')
    const cachedPath = path.join(cacheDir, `page-${page.pageNumber}.png`)

    if (existsSync(cachedPath)) {
      const buf = await readFile(cachedPath)
      return new NextResponse(new Uint8Array(buf), {
        headers: {
          'Content-Type': 'image/png',
          'Cache-Control': 'public, max-age=60',
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
          'Cache-Control': 'public, max-age=60',
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

    // Check if a pixel row is "clean" (no dark text/line pixels)
    const isCleanRow = (rowY: number, x0: number, x1: number): boolean => {
      if (rowY < 0 || rowY >= imgH) return false
      for (let x = x0; x < x1; x += 2) {
        const idx = (rowY * imgW + Math.min(x, imgW - 1)) * channels
        const lum = rawPixels[idx] * 0.299 + rawPixels[idx + 1] * 0.587 + rawPixels[idx + 2] * 0.114
        if (lum < 170) return false
      }
      return true
    }

    // Fallback: sample solid background color from edges, filtering dark pixels
    const sampleLocalBg = (pxLeft: number, pxTop: number, pxRight: number, pxBottom: number): [number, number, number] => {
      let rSum = 0, gSum = 0, bSum = 0, count = 0
      const stripW = Math.max(5, Math.round((pxRight - pxLeft) * 0.03))
      const stripH = Math.max(5, Math.round((pxBottom - pxTop) * 0.15))
      const regions = [
        { x0: Math.max(0, pxLeft - stripW), y0: pxTop, x1: pxLeft, y1: pxBottom },
        { x0: pxRight, y0: pxTop, x1: Math.min(imgW, pxRight + stripW), y1: pxBottom },
        { x0: pxLeft, y0: Math.max(0, pxTop - stripH), x1: pxRight, y1: pxTop },
        { x0: pxLeft, y0: pxBottom, x1: pxRight, y1: Math.min(imgH, pxBottom + stripH) },
      ]
      for (const { x0, y0, x1, y1 } of regions) {
        for (let y = y0; y < y1; y += 2) {
          for (let x = x0; x < x1; x += 2) {
            const idx = (y * imgW + x) * channels
            const lum = rawPixels[idx] * 0.299 + rawPixels[idx + 1] * 0.587 + rawPixels[idx + 2] * 0.114
            if (lum < 180) continue
            rSum += rawPixels[idx]; gSum += rawPixels[idx + 1]; bSum += rawPixels[idx + 2]; count++
          }
        }
      }
      if (count === 0) return [255, 255, 255]
      return [Math.round(rSum / count), Math.round(gSum / count), Math.round(bSum / count)]
    }

    // Create erasure patches — prefer copying real background strips over solid fills
    const composites: sharp.OverlayOptions[] = []
    const lineEntries: (typeof boxes)[] = []
    lineMap.forEach((lineBoxes) => lineEntries.push(lineBoxes))

    for (const lineBoxes of lineEntries) {
      const minX = Math.min(...lineBoxes.map((b) => b.x))
      const minY = Math.min(...lineBoxes.map((b) => b.y))
      const maxX = Math.max(...lineBoxes.map((b) => b.x + b.width))
      const maxY = Math.max(...lineBoxes.map((b) => b.y + b.height))

      const pad = 0.4
      const pxLeft = Math.max(0, Math.round(((minX - pad) / 100) * imgW))
      const pxTop = Math.max(0, Math.round(((minY - pad) / 100) * imgH))
      const pxRight = Math.min(imgW, Math.round(((maxX + pad) / 100) * imgW))
      const pxBottom = Math.min(imgH, Math.round(((maxY + pad) / 100) * imgH))
      const pxW = pxRight - pxLeft
      const pxH = pxBottom - pxTop

      if (pxW <= 0 || pxH <= 0) continue

      // Per-row erasure: for each pixel row, find the nearest clean row
      // and copy its pixels. This correctly handles color boundaries
      // (e.g. reddish header meeting white body area).
      const replBuf = Buffer.alloc(pxW * pxH * 3)
      const cleanCache = new Map<number, boolean>()
      const checkClean = (rowY: number): boolean => {
        if (cleanCache.has(rowY)) return cleanCache.get(rowY)!
        const result = isCleanRow(rowY, pxLeft, pxRight)
        cleanCache.set(rowY, result)
        return result
      }

      let hasAnyRef = false
      for (let y = 0; y < pxH; y++) {
        const actualY = pxTop + y
        // Find nearest clean row by searching outward from this y
        let refY = -1
        for (let d = 1; d <= 60; d++) {
          if (actualY - d >= 0 && checkClean(actualY - d)) { refY = actualY - d; break }
          if (actualY + d < imgH && checkClean(actualY + d)) { refY = actualY + d; break }
        }
        for (let x = 0; x < pxW; x++) {
          const dIdx = (y * pxW + x) * 3
          if (refY >= 0) {
            hasAnyRef = true
            const srcIdx = (refY * imgW + Math.min(pxLeft + x, imgW - 1)) * channels
            replBuf[dIdx] = rawPixels[srcIdx]
            replBuf[dIdx + 1] = rawPixels[srcIdx + 1]
            replBuf[dIdx + 2] = rawPixels[srcIdx + 2]
          } else {
            replBuf[dIdx] = 255; replBuf[dIdx + 1] = 255; replBuf[dIdx + 2] = 255
          }
        }
      }

      // Per-pixel residual cleanup: brighten any remaining dark pixels toward background
      if (hasAnyRef) {
        let bgR = 0, bgG = 0, bgB = 0, bgCount = 0
        for (let i = 0; i < replBuf.length; i += 3 * 7) {
          const lum = replBuf[i] * 0.299 + replBuf[i + 1] * 0.587 + replBuf[i + 2] * 0.114
          if (lum > 200) { bgR += replBuf[i]; bgG += replBuf[i + 1]; bgB += replBuf[i + 2]; bgCount++ }
        }
        if (bgCount > 0) { bgR = Math.round(bgR / bgCount); bgG = Math.round(bgG / bgCount); bgB = Math.round(bgB / bgCount) }
        else { bgR = 255; bgG = 255; bgB = 255 }
        for (let i = 0; i < replBuf.length; i += 3) {
          const lum = replBuf[i] * 0.299 + replBuf[i + 1] * 0.587 + replBuf[i + 2] * 0.114
          if (lum < 190) {
            const alpha = Math.min(1.0, (190 - lum) / 100)
            replBuf[i]     = Math.round(replBuf[i]     + (bgR - replBuf[i])     * alpha)
            replBuf[i + 1] = Math.round(replBuf[i + 1] + (bgG - replBuf[i + 1]) * alpha)
            replBuf[i + 2] = Math.round(replBuf[i + 2] + (bgB - replBuf[i + 2]) * alpha)
          }
        }
      }

      if (hasAnyRef) {
        try {
          const patchPng = await sharp(replBuf, { raw: { width: pxW, height: pxH, channels: 3 } })
            .blur(2.0)
            .png()
            .toBuffer()
          composites.push({ input: patchPng, left: pxLeft, top: pxTop })
        } catch {
          const [r, g, b] = sampleLocalBg(pxLeft, pxTop, pxRight, pxBottom)
          composites.push({
            input: Buffer.from(`<svg width="${pxW}" height="${pxH}"><rect width="${pxW}" height="${pxH}" fill="rgb(${r},${g},${b})"/></svg>`),
            left: pxLeft, top: pxTop,
          })
        }
      } else {
        const [r, g, b] = sampleLocalBg(pxLeft, pxTop, pxRight, pxBottom)
        composites.push({
          input: Buffer.from(`<svg width="${pxW}" height="${pxH}"><rect width="${pxW}" height="${pxH}" fill="rgb(${r},${g},${b})"/></svg>`),
          left: pxLeft, top: pxTop,
        })
      }
    }

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
        'Cache-Control': 'public, max-age=60',
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
