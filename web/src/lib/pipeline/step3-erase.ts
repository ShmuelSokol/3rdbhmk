import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { getPageImageBuffer, updatePipelineStatus } from './shared'
import sharp from 'sharp'

/**
 * Step 3: Hebrew erasure — remove Hebrew text, clean up the photo,
 * save blank images to Supabase storage.
 */
export async function runStep3(pageId: string) {
  const { buffer, page, imgW, imgH } = await getPageImageBuffer(pageId)

  const ocrResult = await prisma.oCRResult.findUnique({
    where: { pageId },
    include: {
      boxes: { orderBy: [{ lineIndex: 'asc' }, { wordIndex: 'asc' }] },
    },
  })

  if (!ocrResult) throw new Error('OCR not yet run (step 1 required)')

  const boxes = ocrResult.boxes.filter((b) => !b.skipTranslation)

  if (boxes.length === 0) {
    // No text to erase — save original as erased image
    const storagePath = `pipeline/${page.bookId}/${page.pageNumber}/erased.png`
    const supabase = getSupabase()
    await supabase.storage.from('bhmk').upload(storagePath, buffer, {
      contentType: 'image/png',
      upsert: true,
    })
    await upsertErasedImage(pageId, storagePath, imgW, imgH)
    await updatePipelineStatus(pageId, 'step3_erased')
    return { storagePath, width: imgW, height: imgH }
  }

  // Group boxes into lines
  const lineMap = new Map<number, typeof boxes>()
  for (const box of boxes) {
    const li = box.lineIndex ?? -1
    if (!lineMap.has(li)) lineMap.set(li, [])
    lineMap.get(li)!.push(box)
  }

  const metadata = await sharp(buffer).metadata()
  const channels = metadata.channels || 3
  const rawPixels = await sharp(buffer).raw().toBuffer()

  // Local background luminance computation
  const getLocalBgLum = (pxLeft: number, pxTop: number, pxRight: number, pxBottom: number): number => {
    const sideLums: number[] = []
    const tbLums: number[] = []
    const stripH = Math.max(10, Math.round((pxBottom - pxTop) * 0.25))
    const stripW = Math.max(8, Math.round((pxRight - pxLeft) * 0.08))
    const sideRegions = [
      [pxTop, pxBottom, Math.max(0, pxLeft - stripW), pxLeft],
      [pxTop, pxBottom, pxRight, Math.min(imgW, pxRight + stripW)],
    ]
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
    let lums: number[]
    if (sideLums.length >= 20) {
      lums = sideLums
    } else {
      lums = sideLums.concat(tbLums)
    }
    if (lums.length === 0) return 240
    lums.sort((a, b) => a - b)
    return lums[Math.floor(lums.length * 0.5)]
  }

  const isCleanRow = (rowY: number, x0: number, x1: number, threshold: number): boolean => {
    if (rowY < 0 || rowY >= imgH) return false
    for (let x = x0; x < x1; x += 2) {
      const idx = (rowY * imgW + Math.min(x, imgW - 1)) * channels
      const lum = rawPixels[idx] * 0.299 + rawPixels[idx + 1] * 0.587 + rawPixels[idx + 2] * 0.114
      if (lum < threshold) return false
    }
    return true
  }

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

  // Create erasure patches
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

    const localBgLum = getLocalBgLum(pxLeft, pxTop, pxRight, pxBottom)
    const cleanThreshold = localBgLum - 40

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

    // Per-pixel residual cleanup
    if (hasAnyRef) {
      const [bgR, bgG, bgB] = sampleLocalBg(pxLeft, pxTop, pxRight, pxBottom, localBgLum)
      const floorLum = localBgLum - 35
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

  // Apply all erasure patches
  let result = sharp(buffer)
  if (composites.length > 0) {
    result = result.composite(composites)
  }
  const erasedBuffer = await result.png().toBuffer()

  // Upload to Supabase storage
  const storagePath = `pipeline/${page.bookId}/${page.pageNumber}/erased.png`
  const supabase = getSupabase()
  await supabase.storage.from('bhmk').upload(storagePath, erasedBuffer, {
    contentType: 'image/png',
    upsert: true,
  })

  await upsertErasedImage(pageId, storagePath, imgW, imgH)
  await updatePipelineStatus(pageId, 'step3_erased')

  return { storagePath, width: imgW, height: imgH }
}

async function upsertErasedImage(pageId: string, storagePath: string, width: number, height: number) {
  const existing = await prisma.erasedImage.findUnique({ where: { pageId } })
  if (existing) {
    await prisma.erasedImage.update({
      where: { pageId },
      data: { storagePath, width, height },
    })
  } else {
    await prisma.erasedImage.create({
      data: { pageId, storagePath, width, height },
    })
  }
}
