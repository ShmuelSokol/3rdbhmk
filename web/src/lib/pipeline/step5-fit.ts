import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { getPageImageBuffer, updatePipelineStatus } from './shared'
import sharp from 'sharp'

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

  // Render text into SVG overlays for each region
  const composites: sharp.OverlayOptions[] = []
  const CHAR_WIDTH = 0.55 // average char width as fraction of fontSize

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

    // Font size: try to fit in region, but enforce a minimum of 14px.
    // If text doesn't fit at minimum, let it overflow (SVG height will grow).
    const MIN_FONT_SIZE = 14
    let fontSize = Math.round(avgHebrewSize * 0.9)
    for (let attempt = 0; attempt < 30; attempt++) {
      const lh = Math.round(fontSize * 1.3)
      const cpl = Math.floor(pxWidth / (fontSize * CHAR_WIDTH))
      if (cpl < 3) { fontSize = Math.max(MIN_FONT_SIZE, fontSize - 2); continue }
      let totalLines = 0
      for (const line of text.split('\n')) {
        if (line.trim() === '') { totalLines += 1; continue }
        const words = line.split(/\s+/)
        let cur = 0; totalLines += 1
        for (const w of words) {
          if (cur + w.length + 1 > cpl && cur > 0) { totalLines += 1; cur = w.length }
          else { cur += (cur > 0 ? 1 : 0) + w.length }
        }
      }
      if (totalLines * lh + 10 <= pxHeight) break
      if (fontSize <= MIN_FONT_SIZE) { fontSize = MIN_FONT_SIZE; break }
      fontSize = Math.max(MIN_FONT_SIZE, fontSize - 1)
    }

    const lineHeight = Math.round(fontSize * 1.3)
    const charsPerLine = Math.max(3, Math.floor(pxWidth / (fontSize * CHAR_WIDTH)))

    // Detect centering from actual box positions (not regionType)
    let isCentered = false
    if (regionBoxes.length > 0) {
      const boxMinX = Math.min(...regionBoxes.map((b) => b.x))
      const boxMaxX = Math.max(...regionBoxes.map((b) => b.x + b.width))
      const leftGap = boxMinX
      const rightGap = 100 - boxMaxX
      const boxWidth = boxMaxX - boxMinX
      isCentered = Math.abs(leftGap - rightGap) < 15 && boxWidth < 50
    }

    // Detect bold: ink density, markdown markers, or centered text defaults to bold
    const boldBoxCount = regionBoxes.filter((b) => b.isBold).length
    const inkBold = regionBoxes.length > 0 && boldBoxCount > regionBoxes.length / 2
    const regionIsBold = inkBold || isCentered
    const hasBoldMarkers = text.includes('**')

    // Sample text color from ORIGINAL region coordinates (not expanded)
    const origPxLeft = Math.round((region.origX / 100) * imgW)
    const origPxTop = Math.round((region.origY / 100) * imgH)
    const origPxWidth = Math.round((region.origWidth / 100) * imgW)
    const origPxHeight = Math.round((region.origHeight / 100) * imgH)
    const textColor = sampleTextColor(origPxLeft, origPxTop, origPxWidth, origPxHeight)

    // Word-wrap text into lines
    const inputLines = text.split('\n')
    type WrappedLine = { words: string[]; spilled: boolean }
    const wrappedLines: (WrappedLine | 'gap')[] = []

    for (const line of inputLines) {
      if (line.trim() === '') { wrappedLines.push('gap'); continue }
      const clean = hasBoldMarkers ? line.replace(/\*\*/g, '') : line
      const words = clean.split(/\s+/).filter(Boolean)
      let curWords: string[] = []
      let curLen = 0
      for (const word of words) {
        if (curLen + word.length + 1 > charsPerLine && curLen > 0) {
          // This line is full — next word spilled over
          wrappedLines.push({ words: curWords, spilled: true })
          curWords = [word]
          curLen = word.length
        } else {
          curWords.push(word)
          curLen += (curLen > 0 ? 1 : 0) + word.length
        }
      }
      if (curWords.length > 0) {
        wrappedLines.push({ words: curWords, spilled: false })
      }
    }

    // Calculate total height
    let totalHeight = 0
    for (const wl of wrappedLines) {
      totalHeight += wl === 'gap' ? lineHeight * 0.5 : lineHeight
    }

    // Body text starts at top; centered text gets vertical centering
    const topPad = isCentered ? Math.max(0, (pxHeight - totalHeight) / 2) : 0
    // Use the larger of region height and content height for SVG
    const svgHeight = Math.max(pxHeight, Math.ceil(totalHeight + fontSize))
    let yPos = topPad + fontSize

    const fontWeightAttr = (regionIsBold && !hasBoldMarkers) ? ' font-weight="bold"' : ''
    const svgLines: string[] = []

    for (const wl of wrappedLines) {
      if (wl === 'gap') { yPos += lineHeight * 0.5; continue }

      const lineText = wl.words.map((w) => escapeXml(w)).join(' ')

      if (isCentered || wl.spilled) {
        // Centered: originally-centered text, OR full lines that spilled
        svgLines.push(`<text x="${pxWidth / 2}" y="${yPos}" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="${fontSize}" fill="${textColor}"${fontWeightAttr}>${lineText}</text>`)
      } else {
        // Left-aligned: last line of paragraph (no spill)
        svgLines.push(`<text x="0" y="${yPos}" font-family="Arial,Helvetica,sans-serif" font-size="${fontSize}" fill="${textColor}"${fontWeightAttr}>${lineText}</text>`)
      }
      yPos += lineHeight
    }

    const svg = `<svg width="${pxWidth}" height="${svgHeight}" xmlns="http://www.w3.org/2000/svg">${svgLines.join('')}</svg>`

    composites.push({
      input: Buffer.from(svg),
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

function escapeXml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
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
