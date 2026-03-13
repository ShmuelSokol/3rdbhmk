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

  // Map lineIndex → regionId using boxes' regionId field
  const lineToRegion = new Map<number, string>()
  for (const box of boxes) {
    if (box.lineIndex != null && box.regionId) {
      lineToRegion.set(box.lineIndex, box.regionId)
    }
  }

  // Load region coordinates so we can clamp samples within region borders
  const regions = await prisma.contentRegion.findMany({
    where: { pageId },
    select: { id: true, origX: true, origY: true, origWidth: true, origHeight: true },
  })
  const regionPxBounds = new Map<string, { pxLeft: number; pxTop: number; pxRight: number; pxBottom: number }>()
  for (const r of regions) {
    regionPxBounds.set(r.id, {
      pxLeft: Math.max(0, Math.round((r.origX / 100) * imgW)),
      pxTop: Math.max(0, Math.round((r.origY / 100) * imgH)),
      pxRight: Math.min(imgW, Math.round(((r.origX + r.origWidth) / 100) * imgW)),
      pxBottom: Math.min(imgH, Math.round(((r.origY + r.origHeight) / 100) * imgH)),
    })
  }

  const metadata = await sharp(buffer).metadata()
  const channels = metadata.channels || 3
  const rawPixels = await sharp(buffer).raw().toBuffer()

  // Collect ~30 raw RGB samples from a tight ring (3px) around a text line box.
  // Samples are clamped to stay within the region boundary (never outside the region).
  const collectPerimeterSamples = (
    pxLeft: number, pxTop: number, pxRight: number, pxBottom: number,
    regionLeft: number, regionTop: number, regionRight: number, regionBottom: number
  ): [number, number, number][] => {
    const margin = 3
    const samples: [number, number, number][] = []
    const pxW = pxRight - pxLeft
    const pxH = pxBottom - pxTop
    const perimeter = 2 * (pxW + pxH)
    const step = Math.max(1, Math.floor(perimeter / 30))

    // Clamp helpers: stay within region bounds AND image bounds
    const clampX = (x: number) => Math.max(regionLeft, Math.min(regionRight - 1, Math.min(imgW - 1, x)))
    const clampY = (y: number) => Math.max(regionTop, Math.min(regionBottom - 1, Math.min(imgH - 1, y)))

    // Top edge (sample just above the text line, within region)
    for (let x = pxLeft; x < pxRight; x += step) {
      const sx = clampX(x)
      const sy = clampY(pxTop - margin)
      const idx = (sy * imgW + sx) * channels
      samples.push([rawPixels[idx], rawPixels[idx + 1], rawPixels[idx + 2]])
    }
    // Bottom edge
    for (let x = pxLeft; x < pxRight; x += step) {
      const sx = clampX(x)
      const sy = clampY(pxBottom + margin)
      const idx = (sy * imgW + sx) * channels
      samples.push([rawPixels[idx], rawPixels[idx + 1], rawPixels[idx + 2]])
    }
    // Left edge
    for (let y = pxTop; y < pxBottom; y += step) {
      const sx = clampX(pxLeft - margin)
      const sy = clampY(y)
      const idx = (sy * imgW + sx) * channels
      samples.push([rawPixels[idx], rawPixels[idx + 1], rawPixels[idx + 2]])
    }
    // Right edge
    for (let y = pxTop; y < pxBottom; y += step) {
      const sx = clampX(pxRight + margin)
      const sy = clampY(y)
      const idx = (sy * imgW + sx) * channels
      samples.push([rawPixels[idx], rawPixels[idx + 1], rawPixels[idx + 2]])
    }
    return samples
  }

  // Pick the most common non-text background color from a pool of RGB samples.
  // Hebrew text is dark on light background, so we keep only the lighter half
  // of samples (above median luminance) to exclude text-colored pixels.
  const pickBgColor = (
    samples: [number, number, number][]
  ): [number, number, number] => {
    if (samples.length === 0) return [255, 255, 255]

    // Compute luminance for each sample
    const withLum = samples.map(([r, g, b]) => ({
      r, g, b,
      lum: r * 0.299 + g * 0.587 + b * 0.114,
    }))
    withLum.sort((a, b) => a.lum - b.lum)

    // Keep only the brighter half — these are background, not text
    const midpoint = Math.floor(withLum.length / 2)
    const brightHalf = withLum.slice(midpoint)
    const pool: [number, number, number][] = brightHalf.map((s) => [s.r, s.g, s.b])

    // Bucket by RGB (bin size 16) → most common = background
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

  // Pre-compute pixel bounds for each line
  type LineBounds = {
    lineIdx: number
    lineBoxes: typeof boxes
    pxLeft: number; pxTop: number; pxRight: number; pxBottom: number
    pxW: number; pxH: number
  }
  const lineBounds: LineBounds[] = []
  lineMap.forEach((lineBoxes, lineIdx) => {
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
    if (pxW > 0 && pxH > 0) {
      lineBounds.push({ lineIdx, lineBoxes, pxLeft, pxTop, pxRight, pxBottom, pxW, pxH })
    }
  })

  const FEATHER = 3 // pixels of alpha feathering at patch edges

  // Pool perimeter samples from ALL lines in the same region, then pick one
  // background color per region. This ensures consistent color within a region
  // while sampling close to each actual text line (not just the region boundary).
  const regionSamples = new Map<string, [number, number, number][]>()
  for (const lb of lineBounds) {
    const regionId = lineToRegion.get(lb.lineIdx)
    if (!regionId) continue
    const rBounds = regionPxBounds.get(regionId) || { pxLeft: 0, pxTop: 0, pxRight: imgW, pxBottom: imgH }
    const samples = collectPerimeterSamples(
      lb.pxLeft, lb.pxTop, lb.pxRight, lb.pxBottom,
      rBounds.pxLeft, rBounds.pxTop, rBounds.pxRight, rBounds.pxBottom
    )
    const existing = regionSamples.get(regionId)
    if (existing) {
      existing.push(...samples)
    } else {
      regionSamples.set(regionId, [...samples])
    }
  }

  // Pick one color per region from pooled samples
  const regionBgCache = new Map<string, [number, number, number]>()
  regionSamples.forEach((samples, regionId) => {
    regionBgCache.set(regionId, pickBgColor(samples))
  })

  for (const lb of lineBounds) {
    const { lineIdx, pxLeft, pxTop, pxRight, pxBottom, pxW, pxH } = lb

    // Use region's pooled color, or fall back to per-line sampling
    const regionId = lineToRegion.get(lineIdx)
    const cached = regionId ? regionBgCache.get(regionId) : undefined
    const [bgR, bgG, bgB] = cached
      || pickBgColor(
        collectPerimeterSamples(pxLeft, pxTop, pxRight, pxBottom, 0, 0, imgW, imgH)
      )

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
