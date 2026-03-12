import { prisma } from '@/lib/prisma'
import { analyzePageImage } from '@/lib/azure-ocr'
import { getPageImageBuffer, updatePipelineStatus } from './shared'
import sharp from 'sharp'

/**
 * Step 1: Full OCR — extract every word with exact coordinates,
 * text pixel size, text pixel width, and bold detection.
 */
export async function runStep1(pageId: string) {
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

  // Compute text pixel size and width for each word, and detect bold
  const enrichedWords = ocrWords.map((word) => {
    // Convert % coordinates to pixel coordinates
    const pxLeft = Math.round((word.x / 100) * imgW)
    const pxTop = Math.round((word.y / 100) * imgH)
    const pxRight = Math.round(((word.x + word.width) / 100) * imgW)
    const pxBottom = Math.round(((word.y + word.height) / 100) * imgH)

    const textPixelWidth = pxRight - pxLeft
    const textPixelSize = pxBottom - pxTop

    // Bold detection: measure average stroke width by looking at dark pixel density
    // Bold text has higher dark pixel ratio in its bounding box
    let darkPixelCount = 0
    let totalPixels = 0
    for (let y = pxTop; y < pxBottom; y += 2) {
      for (let x = pxLeft; x < pxRight; x += 2) {
        if (x >= 0 && x < imgW && y >= 0 && y < imgH) {
          const idx = (y * imgW + x) * channels
          const lum = rawPixels[idx] * 0.299 + rawPixels[idx + 1] * 0.587 + rawPixels[idx + 2] * 0.114
          if (lum < 128) darkPixelCount++
          totalPixels++
        }
      }
    }
    const darkRatio = totalPixels > 0 ? darkPixelCount / totalPixels : 0
    // Bold threshold: typically bold text has >30% dark pixels, regular <25%
    const isBold = darkRatio > 0.30

    return {
      ...word,
      textPixelSize,
      textPixelWidth,
      isBold,
    }
  })

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
