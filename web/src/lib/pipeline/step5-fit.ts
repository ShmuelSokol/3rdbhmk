import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { getPageImageBuffer, updatePipelineStatus } from './shared'
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

  // Get regions with translations
  const regions = await prisma.contentRegion.findMany({
    where: { pageId },
    orderBy: { regionIndex: 'asc' },
  })

  // Get translation for this page
  const translation = await prisma.translation.findUnique({ where: { pageId } })

  if (regions.length === 0 || !translation) {
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

  // Parse the English translation into paragraphs
  const englishText = translation.englishOutput
  const paragraphs = englishText.split(/\n\n+/).filter((p) => p.trim())

  // Get OCR boxes for bold/font detection
  const ocrResult = await prisma.oCRResult.findUnique({
    where: { pageId },
    include: { boxes: true },
  })

  // Assign paragraphs to regions by content length similarity.
  // Longer Hebrew text produces longer English translations, so match by length rank.
  const assignments: { region: typeof regions[0]; text: string }[] = []

  if (paragraphs.length === regions.length) {
    // Match by Hebrew/English length rank — sort both by length, pair them, then
    // restore to region order so each region gets the right paragraph
    const regionsByLen = regions.map((r, i) => ({ region: r, idx: i, len: (r.hebrewText || '').length }))
      .sort((a, b) => a.len - b.len)
    const parasByLen = paragraphs.map((p, i) => ({ text: p, idx: i, len: p.length }))
      .sort((a, b) => a.len - b.len)
    const matched: { region: typeof regions[0]; text: string }[] = []
    for (let i = 0; i < regionsByLen.length; i++) {
      matched.push({ region: regionsByLen[i].region, text: parasByLen[i].text })
    }
    // Restore to region order (by regionIndex)
    matched.sort((a, b) => a.region.regionIndex - b.region.regionIndex)
    assignments.push(...matched)
  } else if (paragraphs.length > regions.length) {
    // More paragraphs than regions — distribute proportionally
    const totalChars = regions.reduce((sum, r) => sum + (r.hebrewText?.length || 1), 0)
    let paraIdx = 0
    for (let ri = 0; ri < regions.length; ri++) {
      const region = regions[ri]
      const isLast = ri === regions.length - 1
      if (isLast) {
        assignments.push({ region, text: paragraphs.slice(paraIdx).join('\n\n') })
      } else {
        const charRatio = (region.hebrewText?.length || 1) / totalChars
        const paraCount = Math.max(1, Math.round(charRatio * paragraphs.length))
        const regionParas = paragraphs.slice(paraIdx, paraIdx + paraCount)
        paraIdx += paraCount
        assignments.push({ region, text: regionParas.join('\n\n') || '' })
      }
    }
  } else {
    // Fewer paragraphs than regions — match by length rank, extras get empty text
    const regionsByLen = regions.map((r, i) => ({ region: r, idx: i, len: (r.hebrewText || '').length }))
      .sort((a, b) => a.len - b.len)
    const parasByLen = paragraphs.map((p, i) => ({ text: p, idx: i, len: p.length }))
      .sort((a, b) => a.len - b.len)
    const matchMap = new Map<string, string>()
    // Match shortest paragraphs to shortest regions
    for (let i = 0; i < parasByLen.length; i++) {
      matchMap.set(regionsByLen[i].region.id, parasByLen[i].text)
    }
    for (const region of regions) {
      assignments.push({ region, text: matchMap.get(region.id) || '' })
    }
  }

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

    // Only shrink if the longest single word doesn't fit the width
    measureCtx.font = `${fontStyle} ${fontSize}px Arial`
    const longestWord = cleanText.split(/\s+/).reduce((a, b) => a.length > b.length ? a : b, '')
    while (fontSize > 20 && measureCtx.measureText(longestWord).width > pxWidth) {
      fontSize--
      measureCtx.font = `${fontStyle} ${fontSize}px Arial`
    }

    // Render onto canvas
    const wrappedLines = wrapText(fontSize)
    const lineHeight = Math.round(fontSize * 1.3)
    const totalHeight = wrappedLines.length * lineHeight
    const canvasHeight = Math.max(pxHeight, totalHeight + fontSize)

    const canvas = createCanvas(pxWidth, canvasHeight)
    const ctx = canvas.getContext('2d')

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
