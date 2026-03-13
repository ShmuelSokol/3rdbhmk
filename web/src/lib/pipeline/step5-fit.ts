import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { getPageImageBuffer, updatePipelineStatus } from './shared'
import { translateHebrew } from '@/lib/translate'
import sharp from 'sharp'
import { createCanvas } from 'canvas'

/**
 * Step 5: English text fitting — center English text in expanded regions,
 * match Hebrew pixel sizes, render onto erased image, upload to Supabase.
 */
export async function runStep5(pageId: string) {
  const { buffer: origBuffer, imgW, imgH, page } = await getPageImageBuffer(pageId)

  // Load original image pixels for color sampling
  const origMeta = await sharp(origBuffer).metadata()
  const origPixels = await sharp(origBuffer).raw().toBuffer()
  const origChannels = origMeta.channels || 3

  // Sample the dominant text color from a region of the original image
  function sampleTextColor(pxLeft: number, pxTop: number, pxWidth: number, pxHeight: number): string {
    const darkPixels: [number, number, number][] = []
    const pxRight = Math.min(imgW, pxLeft + pxWidth)
    const pxBottom = Math.min(imgH, pxTop + pxHeight)
    for (let y = pxTop; y < pxBottom; y += 3) {
      for (let x = pxLeft; x < pxRight; x += 3) {
        const idx = (y * imgW + x) * origChannels
        const r = origPixels[idx], g = origPixels[idx + 1], b = origPixels[idx + 2]
        const lum = r * 0.299 + g * 0.587 + b * 0.114
        // Collect dark pixels (text pixels, not background)
        if (lum < 100) {
          darkPixels.push([r, g, b])
        }
      }
    }
    if (darkPixels.length === 0) return 'black'
    // Average the dark pixel colors
    const avg = darkPixels.reduce(
      (acc, [r, g, b]) => [acc[0] + r, acc[1] + g, acc[2] + b],
      [0, 0, 0]
    )
    const r = Math.round(avg[0] / darkPixels.length)
    const g = Math.round(avg[1] / darkPixels.length)
    const b = Math.round(avg[2] / darkPixels.length)
    return `rgb(${r},${g},${b})`
  }

  // Get erased image from Supabase
  const erasedRecord = await prisma.erasedImage.findUnique({ where: { pageId } })
  if (!erasedRecord) throw new Error('Erased image not found (step 3 required)')

  const supabase = getSupabase()
  const { data: erasedData, error: dlErr } = await supabase.storage
    .from('bhmk')
    .download(erasedRecord.storagePath)
  if (dlErr || !erasedData) throw new Error('Failed to download erased image')
  const erasedBuffer = Buffer.from(await erasedData.arrayBuffer())

  // Load erased image pixels for background color sampling
  const erasedPixels = await sharp(erasedBuffer).raw().toBuffer()
  const erasedMeta = await sharp(erasedBuffer).metadata()
  const erasedChannels = erasedMeta.channels || 3

  // Sample background color from erased image in a region
  function sampleBgColor(pxLeft: number, pxTop: number, pxWidth: number, pxHeight: number): string {
    const lightPixels: [number, number, number][] = []
    const pxRight = Math.min(imgW, pxLeft + pxWidth)
    const pxBottom = Math.min(imgH, pxTop + pxHeight)
    for (let y = pxTop; y < pxBottom; y += 3) {
      for (let x = pxLeft; x < pxRight; x += 3) {
        const idx = (y * imgW + x) * erasedChannels
        const r = erasedPixels[idx], g = erasedPixels[idx + 1], b = erasedPixels[idx + 2]
        const lum = r * 0.299 + g * 0.587 + b * 0.114
        if (lum > 180) {
          lightPixels.push([r, g, b])
        }
      }
    }
    if (lightPixels.length === 0) return 'rgb(255,255,255)'
    const avg = lightPixels.reduce(
      (acc, [r, g, b]) => [acc[0] + r, acc[1] + g, acc[2] + b],
      [0, 0, 0]
    )
    const r = Math.round(avg[0] / lightPixels.length)
    const g = Math.round(avg[1] / lightPixels.length)
    const b = Math.round(avg[2] / lightPixels.length)
    return `rgb(${r},${g},${b})`
  }

  // Get regions with translations
  const regions = await prisma.contentRegion.findMany({
    where: { pageId },
    orderBy: { regionIndex: 'asc' },
  })

  if (regions.length === 0) {
    // Nothing to fit — save erased as fitted
    const storagePath = `pipeline/${page.bookId}/${page.pageNumber}/fitted.png`
    await supabase.storage.from('bhmk').upload(storagePath, erasedBuffer, {
      contentType: 'image/png',
      upsert: true,
    })
    await upsertFittedPage(pageId, storagePath, imgW, imgH)
    await updatePipelineStatus(pageId, 'step5_fitted')
    return { storagePath, width: imgW, height: imgH }
  }

  // Translate each region individually if not already translated
  // Build full page context for better translation quality
  const fullPageHebrew = regions.map((r) => r.hebrewText || '').join('\n\n')
  for (const region of regions) {
    if (!region.translatedText && region.hebrewText?.trim()) {
      const hebrewText = region.hebrewText.trim()

      // Hebrew numerals (gematria) — just keep as-is
      const isHebrewNumeral = /^[\u05D0-\u05EA]{1,3}$/u.test(hebrewText) && hebrewText.length <= 3
      if (isHebrewNumeral) {
        region.translatedText = hebrewText
        await prisma.contentRegion.update({
          where: { id: region.id },
          data: { translatedText: hebrewText },
        })
        continue
      }

      // Only send context for longer regions (short text + long context confuses the model)
      const useContext = hebrewText.length > 20 ? fullPageHebrew : undefined
      const english = await translateHebrew({
        hebrewText,
        context: useContext,
      })
      await prisma.contentRegion.update({
        where: { id: region.id },
        data: { translatedText: english },
      })
      region.translatedText = english
    }
  }

  // Build assignments directly from each region's own translation
  const assignments: { region: typeof regions[0]; text: string }[] = regions
    .map((region) => ({ region, text: region.translatedText || '' }))

  // Get OCR boxes for bold/font detection
  const ocrResult = await prisma.oCRResult.findUnique({
    where: { pageId },
    include: { boxes: true },
  })

  // Render text onto canvas for each region, then composite onto erased image
  const composites: sharp.OverlayOptions[] = []

  for (const { region, text } of assignments) {
    if (!text.trim()) continue

    // Use manual coordinates if set, else expanded, else original
    const rx = region.manualX ?? region.expandedX ?? region.origX
    const ry = region.manualY ?? region.expandedY ?? region.origY
    const rw = region.manualWidth ?? region.expandedWidth ?? region.origWidth
    const rh = region.manualHeight ?? region.expandedHeight ?? region.origHeight

    const pxLeft = Math.round((rx / 100) * imgW)
    const pxTop = Math.round((ry / 100) * imgH)
    const pxWidth = Math.round((rw / 100) * imgW)
    const pxHeight = Math.round((rh / 100) * imgH)

    if (pxWidth <= 0 || pxHeight <= 0) continue

    // Determine target font size from Hebrew text pixel size
    const regionBoxes = ocrResult?.boxes.filter((b) => b.regionId === region.id) || []
    const avgHebrewSize = regionBoxes.length > 0
      ? regionBoxes.reduce((s, b) => s + (b.textPixelSize || 20), 0) / regionBoxes.length
      : 20

    // Detect centering from actual box positions
    let isCentered = false
    if (regionBoxes.length > 0) {
      const boxMinX = Math.min(...regionBoxes.map((b) => b.x))
      const boxMaxX = Math.max(...regionBoxes.map((b) => b.x + b.width))
      const leftGap = boxMinX
      const rightGap = 100 - boxMaxX
      const boxWidth = boxMaxX - boxMinX
      isCentered = Math.abs(leftGap - rightGap) < 15 && boxWidth < 50
    }

    // Detect bold
    const boldBoxCount = regionBoxes.filter((b) => b.isBold).length
    const inkBold = regionBoxes.length > 0 && boldBoxCount > regionBoxes.length / 2
    const regionIsBold = inkBold || isCentered

    // Sample text color from ORIGINAL region coordinates
    const origPxLeft = Math.round((region.origX / 100) * imgW)
    const origPxTop = Math.round((region.origY / 100) * imgH)
    const origPxWidth = Math.round((region.origWidth / 100) * imgW)
    const origPxHeight = Math.round((region.origHeight / 100) * imgH)
    const textColor = sampleTextColor(origPxLeft, origPxTop, origPxWidth, origPxHeight)

    // Strip bold markers from text
    const cleanText = text.replace(/\*\*/g, '')

    // Use canvas measureText for word wrapping — find font size that fits
    const measureCanvas = createCanvas(1, 1)
    const measureCtx = measureCanvas.getContext('2d')

    const fontStyle = regionIsBold ? 'bold' : 'normal'
    // Use Hebrew font size — only shrink if a single word is wider than the region
    let fontSize = Math.max(20, Math.round(avgHebrewSize * 0.9))

    const wrapText = (fs: number): string[] => {
      measureCtx.font = `${fontStyle} ${fs}px Arial`
      const allLines: string[] = []
      for (const paragraph of cleanText.split('\n')) {
        if (paragraph.trim() === '') { allLines.push(''); continue }
        const words = paragraph.split(/\s+/).filter(Boolean)
        let currentLine = ''
        for (const word of words) {
          const testLine = currentLine ? currentLine + ' ' + word : word
          if (measureCtx.measureText(testLine).width > pxWidth && currentLine) {
            allLines.push(currentLine)
            currentLine = word
          } else {
            currentLine = testLine
          }
        }
        if (currentLine) allLines.push(currentLine)
      }
      return allLines
    }

    // Shrink until text fits within region height (but never below 50% of Hebrew size)
    const minFontSize = Math.max(20, Math.round(avgHebrewSize * 0.5))
    for (let attempt = 0; attempt < 30; attempt++) {
      const lines = wrapText(fontSize)
      const lh = Math.round(fontSize * 1.3)
      if (lines.length * lh <= pxHeight) break
      if (fontSize <= minFontSize) { fontSize = minFontSize; break }
      fontSize--
    }

    // Render onto canvas — clipped to region size
    const wrappedLines = wrapText(fontSize)
    const lineHeight = Math.round(fontSize * 1.3)
    const totalHeight = wrappedLines.length * lineHeight
    const canvasHeight = pxHeight

    const canvas = createCanvas(pxWidth, canvasHeight)
    const ctx = canvas.getContext('2d')

    // Fill body regions with opaque background to cover erasure artifacts
    // Skip headers/page numbers to preserve decorative elements (circles, borders)
    if (region.regionType === 'body' || region.regionType === 'table') {
      const bgColor = sampleBgColor(pxLeft, pxTop, pxWidth, pxHeight)
      ctx.fillStyle = bgColor
      ctx.fillRect(0, 0, pxWidth, canvasHeight)
    }

    ctx.font = `${fontStyle} ${fontSize}px Arial`
    ctx.fillStyle = textColor
    ctx.textBaseline = 'top'

    // Body text starts at top; centered text gets vertical centering
    const topPad = isCentered ? Math.max(0, (pxHeight - totalHeight) / 2) : 0
    let yPos = topPad

    for (const line of wrappedLines) {
      if (line === '') { yPos += lineHeight * 0.5; continue }
      if (isCentered) {
        const w = measureCtx.measureText(line).width
        ctx.fillText(line, (pxWidth - w) / 2, yPos)
      } else {
        ctx.fillText(line, 0, yPos)
      }
      yPos += lineHeight
    }

    composites.push({
      input: canvas.toBuffer('image/png'),
      left: pxLeft,
      top: pxTop,
    })

    // Save fitted text and font size to region
    await prisma.contentRegion.update({
      where: { id: region.id },
      data: {
        fittedFontSize: fontSize,
        fittedText: text,
      },
    })
  }

  // Composite text onto erased image
  let result = sharp(erasedBuffer)
  if (composites.length > 0) {
    result = result.composite(composites)
  }
  const fittedBuffer = await result.png().toBuffer()

  // Upload to Supabase
  const storagePath = `pipeline/${page.bookId}/${page.pageNumber}/fitted.png`
  await supabase.storage.from('bhmk').upload(storagePath, fittedBuffer, {
    contentType: 'image/png',
    upsert: true,
  })

  await upsertFittedPage(pageId, storagePath, imgW, imgH)
  await updatePipelineStatus(pageId, 'step5_fitted')

  return { storagePath, width: imgW, height: imgH }
}

async function upsertFittedPage(pageId: string, storagePath: string, width: number, height: number) {
  const existing = await prisma.fittedPage.findUnique({ where: { pageId } })
  if (existing) {
    await prisma.fittedPage.update({
      where: { pageId },
      data: { storagePath, width, height },
    })
  } else {
    await prisma.fittedPage.create({
      data: { pageId, storagePath, width, height },
    })
  }
}
