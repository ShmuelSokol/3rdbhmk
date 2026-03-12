import { prisma } from '@/lib/prisma'
import { analyzePageImage } from '@/lib/azure-ocr'
import { getPageImageBuffer, updatePipelineStatus } from './shared'
import sharp from 'sharp'

/**
 * Enrich existing bounding boxes with textPixelSize, textPixelWidth, isBold
 * without re-running Azure OCR. Used when boxes already exist but lack these fields.
 */
async function enrichExistingBoxes(pageId: string) {
  const { buffer, imgW, imgH } = await getPageImageBuffer(pageId)
  const metadata = await sharp(buffer).metadata()
  const channels = metadata.channels || 3
  const rawPixels = await sharp(buffer).raw().toBuffer()

  const ocrResult = await prisma.oCRResult.findUnique({
    where: { pageId },
    include: { boxes: true },
  })
  if (!ocrResult) throw new Error('No OCR result to enrich')

  // First pass: compute pixel dimensions and ink density for each box
  const boxMetrics: { id: string; textPixelSize: number; textPixelWidth: number; inkDensity: number }[] = []

  for (const box of ocrResult.boxes) {
    const pxLeft = Math.round((box.x / 100) * imgW)
    const pxTop = Math.round((box.y / 100) * imgH)
    const pxRight = Math.round(((box.x + box.width) / 100) * imgW)
    const pxBottom = Math.round(((box.y + box.height) / 100) * imgH)

    const textPixelWidth = pxRight - pxLeft
    const textPixelSize = pxBottom - pxTop

    // Sample all pixels within the bounding box to measure ink density
    let darkPixelCount = 0
    let totalPixels = 0
    for (let y = pxTop; y < pxBottom; y++) {
      for (let x = pxLeft; x < pxRight; x++) {
        if (x >= 0 && x < imgW && y >= 0 && y < imgH) {
          const idx = (y * imgW + x) * channels
          const lum = rawPixels[idx] * 0.299 + rawPixels[idx + 1] * 0.587 + rawPixels[idx + 2] * 0.114
          if (lum < 100) darkPixelCount++
          totalPixels++
        }
      }
    }
    const inkDensity = totalPixels > 0 ? darkPixelCount / totalPixels : 0

    boxMetrics.push({ id: box.id, textPixelSize, textPixelWidth, inkDensity })
  }

  // Calculate median ink density across all boxes
  const densities = boxMetrics.map((m) => m.inkDensity).filter((d) => d > 0).sort((a, b) => a - b)
  const medianInkDensity = densities.length > 0
    ? densities.length % 2 === 1
      ? densities[Math.floor(densities.length / 2)]
      : (densities[densities.length / 2 - 1] + densities[densities.length / 2]) / 2
    : 0

  // Second pass: determine isBold relative to median and persist
  for (const m of boxMetrics) {
    const isBold = medianInkDensity > 0 && m.inkDensity > medianInkDensity * 1.3

    await prisma.boundingBox.update({
      where: { id: m.id },
      data: { textPixelSize: m.textPixelSize, textPixelWidth: m.textPixelWidth, isBold },
    })
  }

  await prisma.page.update({
    where: { id: pageId },
    data: { status: 'ocr_done' },
  })
  await updatePipelineStatus(pageId, 'step1_ocr')

  return ocrResult
}

/**
 * Step 1: Full OCR — extract every word with exact coordinates,
 * text pixel size, text pixel width, and bold detection.
 *
 * If OCR boxes already exist but lack textPixelSize, enriches them
 * without re-running Azure OCR (saves time and API cost).
 */
export async function runStep1(pageId: string, forceReOcr = false) {
  // Check if we can just enrich existing boxes
  if (!forceReOcr) {
    const existing = await prisma.oCRResult.findUnique({
      where: { pageId },
      include: { boxes: { take: 1, select: { textPixelSize: true } } },
    })
    if (existing && existing.boxes.length > 0 && existing.boxes[0].textPixelSize === null) {
      // Boxes exist but lack enrichment — enrich without re-OCR
      return enrichExistingBoxes(pageId)
    }
    if (existing && existing.boxes.length > 0 && existing.boxes[0].textPixelSize !== null) {
      // Already fully enriched — just update status
      await updatePipelineStatus(pageId, 'step1_ocr')
      return existing
    }
  }

  const { buffer, imgW, imgH } = await getPageImageBuffer(pageId)

  // Compress image for Azure (max 4MB)
  let ocrBuffer: Buffer = buffer
  if (buffer.length > 3 * 1024 * 1024) {
    ocrBuffer = await sharp(buffer).jpeg({ quality: 85 }).toBuffer()
  }

  // Run Azure OCR
  const ocrWords = await analyzePageImage(ocrBuffer)

  // Load raw pixels for text pixel analysis
  const metadata = await sharp(buffer).metadata()
  const channels = metadata.channels || 3
  const rawPixels = await sharp(buffer).raw().toBuffer()

  // First pass: compute text pixel size, width, and ink density for each word
  const wordsWithMetrics = ocrWords.map((word) => {
    const pxLeft = Math.round((word.x / 100) * imgW)
    const pxTop = Math.round((word.y / 100) * imgH)
    const pxRight = Math.round(((word.x + word.width) / 100) * imgW)
    const pxBottom = Math.round(((word.y + word.height) / 100) * imgH)

    const textPixelWidth = pxRight - pxLeft
    const textPixelSize = pxBottom - pxTop

    // Sample all pixels within the bounding box to measure ink density
    let darkPixelCount = 0
    let totalPixels = 0
    for (let y = pxTop; y < pxBottom; y++) {
      for (let x = pxLeft; x < pxRight; x++) {
        if (x >= 0 && x < imgW && y >= 0 && y < imgH) {
          const idx = (y * imgW + x) * channels
          const lum = rawPixels[idx] * 0.299 + rawPixels[idx + 1] * 0.587 + rawPixels[idx + 2] * 0.114
          if (lum < 100) darkPixelCount++
          totalPixels++
        }
      }
    }
    const inkDensity = totalPixels > 0 ? darkPixelCount / totalPixels : 0

    return {
      ...word,
      textPixelSize,
      textPixelWidth,
      inkDensity,
    }
  })

  // Calculate median ink density across all boxes on this page
  const densities = wordsWithMetrics.map((w) => w.inkDensity).filter((d) => d > 0).sort((a, b) => a - b)
  const medianInkDensity = densities.length > 0
    ? densities.length % 2 === 1
      ? densities[Math.floor(densities.length / 2)]
      : (densities[densities.length / 2 - 1] + densities[densities.length / 2]) / 2
    : 0

  // Second pass: determine isBold relative to median ink density
  const enrichedWords = wordsWithMetrics.map((word) => ({
    ...word,
    isBold: medianInkDensity > 0 && word.inkDensity > medianInkDensity * 1.3,
  }))

  // Delete existing OCR result if any (cascade deletes boxes)
  const existing = await prisma.oCRResult.findUnique({ where: { pageId } })
  if (existing) {
    await prisma.oCRResult.delete({ where: { pageId } })
  }

  // Create new OCR result with enriched bounding boxes
  const ocrResult = await prisma.oCRResult.create({
    data: {
      pageId,
      boxes: {
        create: enrichedWords.map((word) => ({
          x: word.x,
          y: word.y,
          width: word.width,
          height: word.height,
          hebrewText: word.hebrewText,
          confidence: word.confidence,
          lineIndex: word.lineIndex,
          wordIndex: word.wordIndex,
          textPixelSize: word.textPixelSize,
          textPixelWidth: word.textPixelWidth,
          isBold: word.isBold,
        })),
      },
    },
    include: {
      boxes: {
        orderBy: [{ lineIndex: 'asc' }, { wordIndex: 'asc' }],
      },
    },
  })

  // Update page statuses
  await prisma.page.update({
    where: { id: pageId },
    data: { status: 'ocr_done' },
  })
  await updatePipelineStatus(pageId, 'step1_ocr')

  return ocrResult
}
