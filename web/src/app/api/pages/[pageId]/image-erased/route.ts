import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getPageImageBuffer } from '@/lib/pipeline/shared'
import { readFile, writeFile, mkdir } from 'fs/promises'
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
    const cacheDir = path.join('/tmp', 'bhmk', book.id, 'pages-erased-v9')
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

    // Get the original page image (handles chunk-based PDF download)
    const { buffer: imageBuffer, imgW: fetchedW, imgH: fetchedH } = await getPageImageBuffer(pageId)

    // Get image dimensions
    const metadata = await sharp(imageBuffer).metadata()
    const imgW = fetchedW
    const imgH = fetchedH

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

    // Compute local background luminance for an area.
    // Prioritizes LEFT and RIGHT strips (same y-level as text) to avoid
    // contamination from different-colored zones above/below (e.g., white
    // page body above a yellowish tile footer). Falls back to above/below
    // strips only when side strips yield too few samples. Uses median
    // instead of 75th percentile for robustness against outliers.
    const getLocalBgLum = (pxLeft: number, pxTop: number, pxRight: number, pxBottom: number): number => {
      const sideLums: number[] = []
      const tbLums: number[] = []
      const stripH = Math.max(10, Math.round((pxBottom - pxTop) * 0.25))
      const stripW = Math.max(8, Math.round((pxRight - pxLeft) * 0.08))
      // Left and right strips (same y-level — most reliable)
      const sideRegions = [
        [pxTop, pxBottom, Math.max(0, pxLeft - stripW), pxLeft],
        [pxTop, pxBottom, pxRight, Math.min(imgW, pxRight + stripW)],
      ]
      // Above and below strips (may cross color boundaries)
      const tbRegions = [
        [Math.max(0, pxTop - stripH), pxTop, pxLeft, pxRight],
        [pxBottom, Math.min(imgH, pxBottom + stripH), pxLeft, pxRight],
      ]
      for (const [y0, y1, x0, x1] of sideRegions) {
        for (let y = y0; y < y1; y += 2) {
          for (let x = x0; x < x1; x += 3) {
            const idx = (y * imgW + x) * channels
            sideLums.push(rawPixels[idx] * 0.299 + rawPixels[idx + 1] * 0.587 + rawPixels[idx + 2] * 0.114)
          }
        }
      }
      for (const [y0, y1, x0, x1] of tbRegions) {
        for (let y = y0; y < y1; y += 2) {
          for (let x = x0; x < x1; x += 3) {
            const idx = (y * imgW + x) * channels
            tbLums.push(rawPixels[idx] * 0.299 + rawPixels[idx + 1] * 0.587 + rawPixels[idx + 2] * 0.114)
          }
        }
      }
      // Use side strips if we have enough samples (>20); otherwise combine all
      let lums: number[]
      if (sideLums.length >= 20) {
        lums = sideLums
      } else {
        lums = sideLums.concat(tbLums)
      }
      if (lums.length === 0) return 240
      lums.sort((a, b) => a - b)
      // Median — robust against contamination from adjacent color zones
      return lums[Math.floor(lums.length * 0.5)]
    }

    // Check if a pixel row is "clean" — threshold adapts to local background
    const isCleanRow = (rowY: number, x0: number, x1: number, threshold: number): boolean => {
      if (rowY < 0 || rowY >= imgH) return false
      for (let x = x0; x < x1; x += 2) {
        const idx = (rowY * imgW + Math.min(x, imgW - 1)) * channels
        const lum = rawPixels[idx] * 0.299 + rawPixels[idx + 1] * 0.587 + rawPixels[idx + 2] * 0.114
        if (lum < threshold) return false
      }
      return true
    }

    // Fallback: sample solid background color from edges, adaptive threshold
    const sampleLocalBg = (pxLeft: number, pxTop: number, pxRight: number, pxBottom: number, bgLum: number): [number, number, number] => {
      let rSum = 0, gSum = 0, bSum = 0, count = 0
      const minLum = bgLum - 30
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
            if (lum < minLum) continue
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

      // Compute local background luminance for adaptive thresholds
      const localBgLum = getLocalBgLum(pxLeft, pxTop, pxRight, pxBottom)
      const cleanThreshold = localBgLum - 40 // e.g. white(240)→200, orange(170)→130

      // Per-row erasure: for each pixel row, find the nearest clean row
      // and copy its pixels. Threshold adapts to local background color.
      const replBuf = Buffer.alloc(pxW * pxH * 3)
      const cleanCache = new Map<number, boolean>()
      const checkClean = (rowY: number): boolean => {
        if (cleanCache.has(rowY)) return cleanCache.get(rowY)!
        const result = isCleanRow(rowY, pxLeft, pxRight, cleanThreshold)
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

      // Per-pixel residual cleanup: brighten dark pixels toward local background.
      // Uses sampleLocalBg (original image edges) for the blend target instead of
      // sampling the replacement buffer, which may contain copied wrong-color rows.
      // floorLum margin widened to -35 to avoid blending pixels that are only
      // slightly darker than estimated bg (prevents yellow-to-white washing).
      if (hasAnyRef) {
        const [bgR, bgG, bgB] = sampleLocalBg(pxLeft, pxTop, pxRight, pxBottom, localBgLum)
        const floorLum = localBgLum - 35 // wider margin: avoid blending near-bg pixels
        for (let i = 0; i < replBuf.length; i += 3) {
          const lum = replBuf[i] * 0.299 + replBuf[i + 1] * 0.587 + replBuf[i + 2] * 0.114
          if (lum < floorLum) {
            const alpha = Math.min(1.0, (floorLum - lum) / 100)
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
          const [r, g, b] = sampleLocalBg(pxLeft, pxTop, pxRight, pxBottom, localBgLum)
          composites.push({
            input: Buffer.from(`<svg width="${pxW}" height="${pxH}"><rect width="${pxW}" height="${pxH}" fill="rgb(${r},${g},${b})"/></svg>`),
            left: pxLeft, top: pxTop,
          })
        }
      } else {
        const [r, g, b] = sampleLocalBg(pxLeft, pxTop, pxRight, pxBottom, localBgLum)
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
