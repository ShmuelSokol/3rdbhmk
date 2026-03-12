import { prisma } from '@/lib/prisma'
import { getPageImageBuffer, updatePipelineStatus } from './shared'
import sharp from 'sharp'

/**
 * Step 4: Region expansion — carefully expand regions using pixel analysis,
 * save expanded coordinates.
 */
export async function runStep4(pageId: string) {
  const { buffer, imgW, imgH } = await getPageImageBuffer(pageId)

  const regions = await prisma.contentRegion.findMany({
    where: { pageId },
    orderBy: { regionIndex: 'asc' },
  })

  if (regions.length === 0) {
    await updatePipelineStatus(pageId, 'step4_expanded')
    return []
  }

  const metadata = await sharp(buffer).metadata()
  const channels = metadata.channels || 3
  const rawPixels = await sharp(buffer).raw().toBuffer()

  // Pixel analysis functions
  const computeStripRGB = (yPct: number, heightPct: number, xPct: number, widthPct: number): [number, number, number] => {
    const pxY = Math.max(0, Math.round((yPct / 100) * imgH))
    const pxH = Math.max(1, Math.round((heightPct / 100) * imgH))
    const pxX = Math.max(0, Math.round((xPct / 100) * imgW))
    const endY = Math.min(imgH, pxY + pxH)
    const endX = Math.min(imgW, pxX + Math.max(1, Math.round((widthPct / 100) * imgW)))

    let rSum = 0, gSum = 0, bSum = 0, count = 0
    for (let y = pxY; y < endY; y += 3) {
      for (let x = pxX; x < endX; x += 3) {
        const idx = (y * imgW + x) * channels
        rSum += rawPixels[idx]
        gSum += rawPixels[idx + 1]
        bSum += rawPixels[idx + 2]
        count++
      }
    }
    if (count === 0) return [255, 255, 255]
    return [rSum / count, gSum / count, bSum / count]
  }

  const computeStripVariance = (yPct: number, heightPct: number, xPct: number, widthPct: number): number => {
    const pxY = Math.max(0, Math.round((yPct / 100) * imgH))
    const pxH = Math.max(1, Math.round((heightPct / 100) * imgH))
    const pxX = Math.max(0, Math.round((xPct / 100) * imgW))
    const endY = Math.min(imgH, pxY + pxH)
    const endX = Math.min(imgW, pxX + Math.max(1, Math.round((widthPct / 100) * imgW)))

    let sum = 0, sumSq = 0, count = 0
    for (let y = pxY; y < endY; y += 3) {
      for (let x = pxX; x < endX; x += 3) {
        const idx = (y * imgW + x) * channels
        const lum = rawPixels[idx] * 0.299 + rawPixels[idx + 1] * 0.587 + rawPixels[idx + 2] * 0.114
        sum += lum
        sumSq += lum * lum
        count++
      }
    }
    if (count < 2) return 0
    const mean = sum / count
    return (sumSq / count) - (mean * mean)
  }

  const colorDist = (a: [number, number, number], b: [number, number, number]): number =>
    Math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)

  const VARIANCE_THRESHOLD = 200
  const COLOR_DIST_THRESHOLD = 25
  const STEP = 1

  // Sort regions by y for overlap resolution
  const sortedRegions = [...regions].sort((a, b) => a.origY - b.origY)

  // Expand each region
  const expanded = sortedRegions.map((region, ri) => {
    const block = {
      x: region.origX,
      y: region.origY,
      width: region.origWidth,
      height: region.origHeight,
    }
    const blockBottom = block.y + block.height

    // Sample background color from inter-line gaps
    const GAP_SCAN_H = 0.3
    const sampleX = Math.max(0, block.x + block.width / 2 - 5)
    const sampleW = Math.min(10, 100 - sampleX)
    const gapColors: [number, number, number][] = []

    for (let sy = block.y; sy < blockBottom; sy += 0.3) {
      const v = computeStripVariance(sy, GAP_SCAN_H, sampleX, sampleW)
      if (v < 50) {
        gapColors.push(computeStripRGB(sy, GAP_SCAN_H, sampleX, sampleW))
        if (gapColors.length >= 5) break
      }
    }

    let refRGB: [number, number, number]
    if (gapColors.length > 0) {
      refRGB = [
        gapColors.reduce((s, c) => s + c[0], 0) / gapColors.length,
        gapColors.reduce((s, c) => s + c[1], 0) / gapColors.length,
        gapColors.reduce((s, c) => s + c[2], 0) / gapColors.length,
      ]
    } else {
      const sideY = block.y
      const sideH = block.height
      const leftX = Math.max(0, block.x - 5)
      const leftW = Math.min(3, block.x - leftX)
      const rightX = block.x + block.width + 1
      const rightW = Math.min(3, 100 - rightX)
      const leftRGB = leftW > 0 ? computeStripRGB(sideY, sideH, leftX, leftW) : [255, 255, 255] as [number, number, number]
      const rightRGB = rightW > 0 ? computeStripRGB(sideY, sideH, rightX, rightW) : [255, 255, 255] as [number, number, number]
      refRGB = [
        (leftRGB[0] + rightRGB[0]) / 2,
        (leftRGB[1] + rightRGB[1]) / 2,
        (leftRGB[2] + rightRGB[2]) / 2,
      ]
    }

    const isSafe = (yPct: number, hPct: number, xPct: number, wPct: number): boolean => {
      const variance = computeStripVariance(yPct, hPct, xPct, wPct)
      if (variance > VARIANCE_THRESHOLD) return false
      const rgb = computeStripRGB(yPct, hPct, xPct, wPct)
      if (colorDist(rgb, refRGB) > COLOR_DIST_THRESHOLD) return false
      return true
    }

    const nextTop = ri < sortedRegions.length - 1 ? sortedRegions[ri + 1].origY : 100
    const prevBottom = ri > 0 ? sortedRegions[ri - 1].origY + sortedRegions[ri - 1].origHeight : 4

    // Vertical expansion
    let safeBottom = blockBottom
    for (let y = blockBottom; y < nextTop; y += STEP) {
      if (!isSafe(y, STEP, block.x, block.width)) break
      safeBottom = y + STEP
    }
    let safeTop = block.y
    for (let y = block.y - STEP; y >= prevBottom; y -= STEP) {
      if (!isSafe(y, STEP, block.x, block.width)) break
      safeTop = y
    }

    // Tables: don't expand horizontally
    if (region.regionType === 'table') {
      const PAGE_MARGIN = 2
      const BUFFER = 1
      const finalLeft = Math.max(PAGE_MARGIN, block.x) + BUFFER
      const finalRight = Math.min(100 - PAGE_MARGIN, block.x + block.width) - BUFFER
      return {
        id: region.id,
        expandedX: finalLeft,
        expandedY: safeTop,
        expandedWidth: Math.max(0, finalRight - finalLeft),
        expandedHeight: safeBottom - safeTop,
      }
    }

    // Horizontal expansion from page center outward
    const SCAN_H = 0.3
    const scanHoriz = (scanY: number) => {
      const isHSafe = (xPct: number, wPct: number): boolean => {
        const variance = computeStripVariance(scanY, SCAN_H, xPct, wPct)
        if (variance > VARIANCE_THRESHOLD) return false
        const rgb = computeStripRGB(scanY, SCAN_H, xPct, wPct)
        if (colorDist(rgb, refRGB) > COLOR_DIST_THRESHOLD) return false
        return true
      }
      let left = 50
      for (let x = 50 - STEP; x >= 0; x -= STEP) {
        if (!isHSafe(x, STEP)) break
        left = x
      }
      let right = 50
      for (let x = 50; x < 100; x += STEP) {
        if (!isHSafe(x, STEP)) break
        right = x + STEP
      }
      return { left, right }
    }

    let bestLeft = 50
    let bestRight = 50
    const scanPositions: number[] = []
    for (let sy = block.y; sy < blockBottom; sy += 0.5) {
      scanPositions.push(sy)
    }
    scanPositions.push(Math.max(0, block.y - 0.15))
    scanPositions.push(blockBottom + 0.05)
    const gapAbove = block.y - prevBottom
    const gapBelow = nextTop - blockBottom
    if (gapAbove >= 0.3) scanPositions.push(prevBottom + gapAbove * 0.5)
    if (gapBelow >= 0.3) scanPositions.push(blockBottom + gapBelow * 0.3)

    for (const sy of scanPositions) {
      const { left, right } = scanHoriz(sy)
      if ((right - left) > (bestRight - bestLeft)) {
        bestLeft = left
        bestRight = right
      }
    }

    // For centered text, also scan from text edges outward
    if (region.regionType === 'header') {
      for (const sy of scanPositions) {
        const isHSafe = (xPct: number, wPct: number): boolean => {
          const variance = computeStripVariance(sy, SCAN_H, xPct, wPct)
          if (variance > VARIANCE_THRESHOLD) return false
          const rgb = computeStripRGB(sy, SCAN_H, xPct, wPct)
          if (colorDist(rgb, refRGB) > COLOR_DIST_THRESHOLD) return false
          return true
        }
        let edgeLeft = block.x
        for (let x = block.x - STEP; x >= 0; x -= STEP) {
          if (!isHSafe(x, STEP)) break
          edgeLeft = x
        }
        let edgeRight = block.x + block.width
        for (let x = block.x + block.width; x < 100; x += STEP) {
          if (!isHSafe(x, STEP)) break
          edgeRight = x + STEP
        }
        if ((edgeRight - edgeLeft) > (bestRight - bestLeft)) {
          bestLeft = edgeLeft
          bestRight = edgeRight
        }
      }
    }

    const PAGE_MARGIN = 2
    const BUFFER = 1
    const finalLeft = Math.max(PAGE_MARGIN, bestLeft) + BUFFER
    const finalRight = Math.min(100 - PAGE_MARGIN, bestRight) - BUFFER

    return {
      id: region.id,
      expandedX: finalLeft,
      expandedY: safeTop,
      expandedWidth: Math.max(0, finalRight - finalLeft),
      expandedHeight: safeBottom - safeTop,
    }
  })

  // Resolve vertical overlaps
  expanded.sort((a, b) => a.expandedY - b.expandedY)
  for (let i = 1; i < expanded.length; i++) {
    const prev = expanded[i - 1]
    const prevBottom = prev.expandedY + prev.expandedHeight
    if (prevBottom > expanded[i].expandedY) {
      const mid = (prevBottom + expanded[i].expandedY) / 2
      prev.expandedHeight = mid - prev.expandedY
      const newY = mid
      expanded[i].expandedHeight = (expanded[i].expandedY + expanded[i].expandedHeight) - newY
      expanded[i].expandedY = newY
    }
  }

  // Save expanded coordinates to DB
  for (const e of expanded) {
    await prisma.contentRegion.update({
      where: { id: e.id },
      data: {
        expandedX: e.expandedX,
        expandedY: e.expandedY,
        expandedWidth: e.expandedWidth,
        expandedHeight: e.expandedHeight,
      },
    })
  }

  await updatePipelineStatus(pageId, 'step4_expanded')
  return expanded
}
