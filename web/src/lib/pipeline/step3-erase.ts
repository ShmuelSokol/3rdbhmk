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

  // Sample ~30 points in a tight ring around the text box, filter out
  // text-colored points, return the most common background color.
  const samplePerimeterBg = (
    pxLeft: number, pxTop: number, pxRight: number, pxBottom: number
  ): [number, number, number] => {
    const margin = 3 // pixels outside the box edge
    const samples: [number, number, number][] = []
    const pxW = pxRight - pxLeft
    const pxH = pxBottom - pxTop
    const perimeter = 2 * (pxW + pxH)
    const numTarget = 30
    const step = Math.max(1, Math.floor(perimeter / numTarget))

    // Walk around the 4 edges, sampling just outside
    // Top edge
    for (let x = pxLeft; x < pxRight; x += step) {
      const sy = Math.max(0, pxTop - margin)
      if (sy < imgH && x < imgW) {
        const idx = (sy * imgW + x) * channels
        samples.push([rawPixels[idx], rawPixels[idx + 1], rawPixels[idx + 2]])
      }
    }
    // Bottom edge
    for (let x = pxLeft; x < pxRight; x += step) {
      const sy = Math.min(imgH - 1, pxBottom + margin)
      if (sy >= 0 && x < imgW) {
        const idx = (sy * imgW + x) * channels
        samples.push([rawPixels[idx], rawPixels[idx + 1], rawPixels[idx + 2]])
      }
    }
    // Left edge
    for (let y = pxTop; y < pxBottom; y += step) {
      const sx = Math.max(0, pxLeft - margin)
      if (y < imgH && sx < imgW) {
        const idx = (y * imgW + sx) * channels
        samples.push([rawPixels[idx], rawPixels[idx + 1], rawPixels[idx + 2]])
      }
    }
    // Right edge
    for (let y = pxTop; y < pxBottom; y += step) {
      const sx = Math.min(imgW - 1, pxRight + margin)
      if (y < imgH && sx >= 0) {
        const idx = (y * imgW + sx) * channels
        samples.push([rawPixels[idx], rawPixels[idx + 1], rawPixels[idx + 2]])
      }
    }

    if (samples.length === 0) return [255, 255, 255]

    // Determine text color: sample interior points, take 30th percentile luminance
    const interiorLums: number[] = []
    const cx = Math.floor((pxLeft + pxRight) / 2)
    const cy = Math.floor((pxTop + pxBottom) / 2)
    const stepX = Math.max(1, Math.floor(pxW / 6))
    const stepY = Math.max(1, Math.floor(pxH / 4))
    for (let dy = -2; dy <= 2; dy++) {
      for (let dx = -3; dx <= 3; dx++) {
        const ix = Math.min(Math.max(cx + dx * stepX, 0), imgW - 1)
        const iy = Math.min(Math.max(cy + dy * stepY, 0), imgH - 1)
        const idx = (iy * imgW + ix) * channels
        interiorLums.push(
          rawPixels[idx] * 0.299 + rawPixels[idx + 1] * 0.587 + rawPixels[idx + 2] * 0.114
        )
      }
    }
    interiorLums.sort((a, b) => a - b)
    const textLum = interiorLums[Math.floor(interiorLums.length * 0.3)]

    // Filter out perimeter samples that are close to the text color
    const bgSamples = samples.filter(([r, g, b]) => {
      const lum = r * 0.299 + g * 0.587 + b * 0.114
      return Math.abs(lum - textLum) > 40
    })

    const pool = bgSamples.length >= 3 ? bgSamples : samples

    // Bucket by color (bin size 16) to find most common background color
    const buckets = new Map<string, { rSum: number; gSum: number; bSum: number; count: number }>()
    for (const [r, g, b] of pool) {
      const key = `${r >> 4},${g >> 4},${b >> 4}`
      const existing = buckets.get(key)
      if (existing) {
        existing.rSum += r; existing.gSum += g; existing.bSum += b; existing.count++
      } else {
        buckets.set(key, { rSum: r, gSum: g, bSum: b, count: 1 })
      }
    }

    let best = { rSum: 255, gSum: 255, bSum: 255, count: 1 }
    buckets.forEach((b) => { if (b.count > best.count) best = b })

    return [
      Math.round(best.rSum / best.count),
      Math.round(best.gSum / best.count),
      Math.round(best.bSum / best.count),
    ]
  }

  // Create erasure patches
  const composites: sharp.OverlayOptions[] = []
  const lineEntries: (typeof boxes)[] = []
  lineMap.forEach((lineBoxes) => lineEntries.push(lineBoxes))

  const FEATHER = 3 // pixels of alpha feathering at patch edges

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

    const [bgR, bgG, bgB] = samplePerimeterBg(pxLeft, pxTop, pxRight, pxBottom)

    // Create RGBA patch: solid background color with alpha feathering at edges
    const patchW = pxW + 2 * FEATHER
    const patchH = pxH + 2 * FEATHER
    const rgbaBuf = Buffer.alloc(patchW * patchH * 4)

    for (let y = 0; y < patchH; y++) {
      for (let x = 0; x < patchW; x++) {
        const idx = (y * patchW + x) * 4
        rgbaBuf[idx] = bgR
        rgbaBuf[idx + 1] = bgG
        rgbaBuf[idx + 2] = bgB
        // Alpha: fully opaque in center, fading at edges
        const distFromEdge = Math.min(x, y, patchW - 1 - x, patchH - 1 - y)
        rgbaBuf[idx + 3] = distFromEdge >= FEATHER ? 255 : Math.round((distFromEdge / FEATHER) * 255)
      }
    }

    try {
      const patchPng = await sharp(rgbaBuf, { raw: { width: patchW, height: patchH, channels: 4 } })
        .png()
        .toBuffer()
      composites.push({
        input: patchPng,
        left: Math.max(0, pxLeft - FEATHER),
        top: Math.max(0, pxTop - FEATHER),
      })
    } catch {
      // Fallback: solid SVG rect without feathering
      composites.push({
        input: Buffer.from(
          `<svg width="${pxW}" height="${pxH}"><rect width="${pxW}" height="${pxH}" fill="rgb(${bgR},${bgG},${bgB})"/></svg>`
        ),
        left: pxLeft,
        top: pxTop,
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
