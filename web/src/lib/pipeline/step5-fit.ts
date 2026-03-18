import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { getPageImageBuffer, updatePipelineStatus } from './shared'
import sharp from 'sharp'
import { createCanvas } from 'canvas'
import Anthropic from '@anthropic-ai/sdk'
import { type Step5Config, DEFAULT_CONFIG } from './config'

/**
 * Step 5: English text fitting — render English text in expanded regions,
 * with per-line font sizing, per-line color sampling, exact X positioning,
 * and AI-powered text shortening when text overflows.
 */
export async function runStep5(pageId: string, configOverrides?: Partial<Step5Config>) {
  const cfg: Step5Config = { ...DEFAULT_CONFIG.step5, ...configOverrides }
  const { buffer: origBuffer, imgW, imgH, page } = await getPageImageBuffer(pageId)

  // Load original image pixels for color sampling
  const origMeta = await sharp(origBuffer).metadata()
  const origPixels = await sharp(origBuffer).raw().toBuffer()
  const origChannels = origMeta.channels || 3

  // Sample text color from a bounding box in the original image.
  // Handles both dark-on-light and light-on-dark text.
  function sampleTextColor(pxLeft: number, pxTop: number, pxWidth: number, pxHeight: number): string {
    const pxRight = Math.min(imgW, pxLeft + pxWidth)
    const pxBottom = Math.min(imgH, pxTop + pxHeight)
    let lumSum = 0, lumCount = 0
    const darkPixels: [number, number, number][] = []
    const lightPixels: [number, number, number][] = []

    for (let y = pxTop; y < pxBottom; y += 3) {
      for (let x = pxLeft; x < pxRight; x += 3) {
        const idx = (y * imgW + x) * origChannels
        const r = origPixels[idx], g = origPixels[idx + 1], b = origPixels[idx + 2]
        const lum = r * 0.299 + g * 0.587 + b * 0.114
        lumSum += lum
        lumCount++
        if (lum < 100) darkPixels.push([r, g, b])
        if (lum > 180) lightPixels.push([r, g, b])
      }
    }

    const avgLum = lumCount > 0 ? lumSum / lumCount : 200

    // Dark background → text is the light pixels
    if (avgLum < 120 && lightPixels.length > 0) {
      const avg = lightPixels.reduce(
        (acc, [r, g, b]) => [acc[0] + r, acc[1] + g, acc[2] + b],
        [0, 0, 0]
      )
      return `rgb(${Math.round(avg[0] / lightPixels.length)},${Math.round(avg[1] / lightPixels.length)},${Math.round(avg[2] / lightPixels.length)})`
    }

    // Light background → text is the dark pixels
    if (darkPixels.length === 0) return 'black'
    const avg = darkPixels.reduce(
      (acc, [r, g, b]) => [acc[0] + r, acc[1] + g, acc[2] + b],
      [0, 0, 0]
    )
    return `rgb(${Math.round(avg[0] / darkPixels.length)},${Math.round(avg[1] / darkPixels.length)},${Math.round(avg[2] / darkPixels.length)})`
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

  // Align translations from existing full-page Translation record
  const anyMissing = regions.some((r) => !r.translatedText && r.hebrewText?.trim())
  if (anyMissing) {
    const translation = await prisma.translation.findUnique({ where: { pageId } })
    if (translation) {
      // Deduplicate regions by normalized Hebrew text before alignment
      // so identical labels (like 5x "בית רוחני") get the same translation
      const textToIndices = new Map<string, number[]>()
      for (let i = 0; i < regions.length; i++) {
        const norm = normalize(regions[i].hebrewText || '')
        if (!norm) continue
        if (!textToIndices.has(norm)) textToIndices.set(norm, [])
        textToIndices.get(norm)!.push(i)
      }

      // Build unique regions for alignment (first occurrence of each text)
      const uniqueEntries: { firstIdx: number; norm: string }[] = []
      textToIndices.forEach((indices, norm) => {
        uniqueEntries.push({ firstIdx: indices[0], norm })
      })
      const uniqueRegions = uniqueEntries.map((e) => regions[e.firstIdx])

      const aligned = alignTranslation(uniqueRegions, translation.hebrewInput, translation.englishOutput)

      // Map translations back to all regions (including duplicates)
      for (let u = 0; u < uniqueEntries.length; u++) {
        const text = aligned[u]
        if (!text) continue
        const allIndices = textToIndices.get(uniqueEntries[u].norm) || []
        for (const idx of allIndices) {
          if (!regions[idx].translatedText) {
            regions[idx].translatedText = text
            await prisma.contentRegion.update({
              where: { id: regions[idx].id },
              data: { translatedText: text },
            })
          }
        }
      }
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
  const measureCanvas = createCanvas(1, 1)
  const measureCtx = measureCanvas.getContext('2d')

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

    // Get OCR boxes for this region, grouped by lineIndex
    const regionBoxes = ocrResult?.boxes.filter((b) => b.regionId === region.id) || []
    const lineMap = new Map<number, typeof regionBoxes>()
    for (const box of regionBoxes) {
      const li = box.lineIndex ?? -1
      if (!lineMap.has(li)) lineMap.set(li, [])
      lineMap.get(li)!.push(box)
    }

    // Build per-line properties (font size, color, bold, position)
    type LineInfo = {
      fontSize: number
      color: string
      isBold: boolean
      centerX: number // page percentage (0-100)
      charCount: number
    }
    const lineInfos: LineInfo[] = []
    lineMap.forEach((lineBoxes) => {
      const minX = Math.min(...lineBoxes.map((b) => b.x))
      const maxX = Math.max(...lineBoxes.map((b) => b.x + b.width))
      const minY = Math.min(...lineBoxes.map((b) => b.y))
      const maxY = Math.max(...lineBoxes.map((b) => b.y + b.height))
      const avgPS = lineBoxes.reduce((s, b) => s + (b.textPixelSize || 20), 0) / lineBoxes.length
      const boldCount = lineBoxes.filter((b) => b.isBold).length
      // Per-line color from original image
      const lpxL = Math.round((minX / 100) * imgW)
      const lpxT = Math.round((minY / 100) * imgH)
      const lpxW = Math.max(1, Math.round(((maxX - minX) / 100) * imgW))
      const lpxH = Math.max(1, Math.round(((maxY - minY) / 100) * imgH))
      lineInfos.push({
        fontSize: Math.max(cfg.minAbsoluteFont, Math.round(avgPS * cfg.fontSizeScale)),
        color: sampleTextColor(lpxL, lpxT, lpxW, lpxH),
        isBold: lineBoxes.length > 0 && boldCount > lineBoxes.length / 2,
        centerX: (minX + maxX) / 2,
        charCount: lineBoxes.reduce((s, b) => s + (b.hebrewText?.length || 0), 0),
      })
    })

    // Fallback values when no OCR boxes
    const defaultFontSize = lineInfos.length > 0
      ? lineInfos[Math.floor(lineInfos.length / 2)].fontSize
      : cfg.minAbsoluteFont
    const defaultColor = lineInfos.length > 0
      ? lineInfos[0].color
      : sampleTextColor(
          Math.round((region.origX / 100) * imgW),
          Math.round((region.origY / 100) * imgH),
          Math.round((region.origWidth / 100) * imgW),
          Math.round((region.origHeight / 100) * imgH)
        )

    // Hebrew text center X relative to region (0 to 1)
    const hebrewCenterX = regionBoxes.length > 0
      ? ((Math.min(...regionBoxes.map((b) => b.x)) + Math.max(...regionBoxes.map((b) => b.x + b.width))) / 2 - rx) / rw
      : 0.5

    // Region-level bold (majority of boxes)
    const boldBoxCount = regionBoxes.filter((b) => b.isBold).length
    const regionIsBold = regionBoxes.length > 0 && boldBoxCount > regionBoxes.length / 2

    const cleanText = text.replace(/\*\*/g, '')

    // Check if per-line rendering is needed (distinct font sizes across OCR lines)
    const uniqueSizes = new Set(lineInfos.map((l) => l.fontSize))
    const usePerLine = uniqueSizes.size > 1 && lineInfos.length > 1

    if (usePerLine) {
      // === PER-LINE RENDERING ===
      // Map English text to Hebrew line segments proportionally by character count
      const totalChars = lineInfos.reduce((s, l) => s + l.charCount, 0) || 1
      const words = cleanText.split(/\s+/).filter(Boolean)
      const segments: { text: string; info: LineInfo }[] = []
      let wordIdx = 0

      for (let li = 0; li < lineInfos.length; li++) {
        const frac = lineInfos[li].charCount / totalChars
        const targetWordCount = Math.max(1, Math.round(frac * words.length))
        if (li === lineInfos.length - 1) {
          segments.push({ text: words.slice(wordIdx).join(' '), info: lineInfos[li] })
        } else {
          segments.push({ text: words.slice(wordIdx, wordIdx + targetWordCount).join(' '), info: lineInfos[li] })
          wordIdx += targetWordCount
        }
      }

      // Word wrap each segment at its own font size
      type RenderedLine = { text: string; fontSize: number; color: string; isBold: boolean; centerX: number }
      const renderedLines: RenderedLine[] = []
      for (const seg of segments) {
        if (!seg.text.trim()) continue
        const fs = seg.info.fontSize
        const style = seg.info.isBold ? 'bold' : 'normal'
        measureCtx.font = `${style} ${fs}px Arial`
        const segWords = seg.text.split(/\s+/).filter(Boolean)
        let currentLine = ''
        for (const word of segWords) {
          const testLine = currentLine ? currentLine + ' ' + word : word
          if (measureCtx.measureText(testLine).width > pxWidth && currentLine) {
            renderedLines.push({ text: currentLine, fontSize: fs, color: seg.info.color, isBold: seg.info.isBold, centerX: seg.info.centerX })
            currentLine = word
          } else {
            currentLine = testLine
          }
        }
        if (currentLine) {
          renderedLines.push({ text: currentLine, fontSize: fs, color: seg.info.color, isBold: seg.info.isBold, centerX: seg.info.centerX })
        }
      }

      // Check total height, shrink proportionally if needed
      let totalHeight = renderedLines.reduce((s, l) => s + Math.round(l.fontSize * cfg.lineHeightMultiplier), 0)
      if (totalHeight > pxHeight) {
        const scale = pxHeight / totalHeight
        for (const rl of renderedLines) {
          rl.fontSize = Math.max(cfg.minAbsoluteFont, Math.round(rl.fontSize * scale))
        }
        totalHeight = renderedLines.reduce((s, l) => s + Math.round(l.fontSize * cfg.lineHeightMultiplier), 0)
      }

      // Render
      const canvas = createCanvas(pxWidth, pxHeight)
      const ctx = canvas.getContext('2d')
      const fillBg = region.regionType === 'body' || region.regionType === 'table'
      const bgColor = fillBg ? sampleBgColor(pxLeft, pxTop, pxWidth, pxHeight) : ''
      ctx.textBaseline = 'top'
      const topPad = totalHeight < pxHeight ? Math.max(0, (pxHeight - totalHeight) / 2) : 0
      let yPos = topPad

      for (const rl of renderedLines) {
        const style = rl.isBold ? 'bold' : 'normal'
        ctx.font = `${style} ${rl.fontSize}px Arial`
        const lh = Math.round(rl.fontSize * cfg.lineHeightMultiplier)
        const lineW = ctx.measureText(rl.text).width
        // Position at Hebrew line's center X
        const targetCenterPx = ((rl.centerX - rx) / rw) * pxWidth
        let xPos = targetCenterPx - lineW / 2
        xPos = Math.max(0, Math.min(pxWidth - lineW, xPos))
        // Wide lines → left-align for readability
        if (lineW > pxWidth * cfg.wideLineThreshold) xPos = 0
        // Fill background strip behind this text line only (preserves illustrations)
        if (fillBg) {
          ctx.fillStyle = bgColor
          ctx.fillRect(0, yPos, pxWidth, lh)
        }
        ctx.fillStyle = rl.color
        ctx.fillText(rl.text, xPos, yPos)
        yPos += lh
      }

      composites.push({ input: canvas.toBuffer('image/png'), left: pxLeft, top: pxTop })
      const medFS = renderedLines.length > 0 ? renderedLines[Math.floor(renderedLines.length / 2)].fontSize : defaultFontSize
      await prisma.contentRegion.update({
        where: { id: region.id },
        data: { fittedFontSize: medFS, fittedText: cleanText },
      })
    } else {
      // === UNIFORM RENDERING (single font size, improved positioning) ===
      let fontSize = defaultFontSize
      const fontStyle = regionIsBold ? 'bold' : 'normal'

      const wrapText = (fs: number, txt: string): string[] => {
        measureCtx.font = `${fontStyle} ${fs}px Arial`
        const allLines: string[] = []
        for (const paragraph of txt.split('\n')) {
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

      // Shrink until text fits
      const minFontSize = Math.max(cfg.minAbsoluteFont, Math.round(defaultFontSize * cfg.minFontRatio))
      for (let attempt = 0; attempt < 30; attempt++) {
        const lines = wrapText(fontSize, cleanText)
        const lh = Math.round(fontSize * cfg.lineHeightMultiplier)
        if (lines.length * lh <= pxHeight) break
        if (fontSize <= minFontSize) { fontSize = minFontSize; break }
        fontSize--
      }

      // Check if text still overflows → AI shorten
      let finalText = cleanText
      const wrappedCheck = wrapText(fontSize, cleanText)
      const checkLH = Math.round(fontSize * cfg.lineHeightMultiplier)
      if (wrappedCheck.length * checkLH > pxHeight) {
        const charsPerLine = Math.max(1, Math.floor(pxWidth / (fontSize * 0.55)))
        const maxLines = Math.max(1, Math.floor(pxHeight / checkLH))
        const maxChars = charsPerLine * maxLines
        try {
          finalText = await shortenText(cleanText, maxChars)
        } catch {
          // AI shortening failed, render what fits
        }
      }

      const wrappedLines = wrapText(fontSize, finalText)
      const lineHeight = Math.round(fontSize * cfg.lineHeightMultiplier)
      const totalHeight = wrappedLines.length * lineHeight

      const canvas = createCanvas(pxWidth, pxHeight)
      const ctx = canvas.getContext('2d')
      const fillBg = region.regionType === 'body' || region.regionType === 'table'
      const bgColor = fillBg ? sampleBgColor(pxLeft, pxTop, pxWidth, pxHeight) : ''

      ctx.font = `${fontStyle} ${fontSize}px Arial`
      ctx.fillStyle = defaultColor
      ctx.textBaseline = 'top'

      // Vertical centering for short text blocks
      const topPad = totalHeight < pxHeight ? Math.max(0, (pxHeight - totalHeight) / 2) : 0
      let yPos = topPad

      // Horizontal positioning: center each line at Hebrew text's center X
      const targetCenterPx = hebrewCenterX * pxWidth

      for (const line of wrappedLines) {
        if (line === '') { yPos += lineHeight * cfg.emptyLineHeightRatio; continue }
        measureCtx.font = `${fontStyle} ${fontSize}px Arial`
        const lineW = measureCtx.measureText(line).width
        let xPos = targetCenterPx - lineW / 2
        xPos = Math.max(0, Math.min(pxWidth - lineW, xPos))
        // Wide lines → left-align for readability
        if (lineW > pxWidth * cfg.wideLineThreshold) xPos = 0
        // Fill background strip behind this text line only (preserves illustrations)
        if (fillBg) {
          ctx.fillStyle = bgColor
          ctx.fillRect(0, yPos, pxWidth, lineHeight)
        }
        ctx.fillStyle = defaultColor
        ctx.fillText(line, xPos, yPos)
        yPos += lineHeight
      }

      composites.push({
        input: canvas.toBuffer('image/png'),
        left: pxLeft,
        top: pxTop,
      })

      await prisma.contentRegion.update({
        where: { id: region.id },
        data: {
          fittedFontSize: fontSize,
          fittedText: finalText,
        },
      })
    }
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

/**
 * AI-powered text shortening — asks Claude to condense text when it doesn't
 * fit in the available space after maximum font shrinking.
 */
async function shortenText(text: string, maxChars: number): Promise<string> {
  const client = new Anthropic({ apiKey: process.env["ANTHROPIC_API_KEY"]! })
  const response = await client.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 1024,
    system: 'You are a concise editor. Shorten the given English text to approximately the specified character count while preserving the essential meaning. Use shorter words and simpler phrasing. Return ONLY the shortened text, nothing else.',
    messages: [{
      role: 'user',
      content: `Shorten to approximately ${maxChars} characters:\n\n${text}`,
    }],
  })
  const block = response.content.find((b) => b.type === 'text')
  return block?.type === 'text' ? block.text : text
}

/**
 * Align existing full-page translation to individual regions using Hebrew position matching.
 * Finds where each region's Hebrew text appears in the full Hebrew input, then assigns
 * corresponding English paragraphs in order — no API calls needed.
 */
function alignTranslation(
  regions: { hebrewText: string | null; translatedText: string | null }[],
  fullHebrew: string,
  fullEnglish: string
): string[] {
  const result = new Array(regions.length).fill('')

  // Split both into non-blank lines
  const hebLines = fullHebrew.split('\n').filter((l) => l.trim())
  const engLines = fullEnglish.split('\n').filter((l) => l.trim())

  // Phase 1: Single-line exact matching
  // Match regions whose normalized text equals exactly one Hebrew line
  const usedHebLines = new Set<number>()
  const usedEngLines = new Set<number>()

  for (let ri = 0; ri < regions.length; ri++) {
    if (!regions[ri].hebrewText?.trim()) continue
    const regionNorm = normalize(regions[ri].hebrewText!)

    for (let li = 0; li < hebLines.length; li++) {
      if (usedHebLines.has(li)) continue
      if (normalize(hebLines[li]) === regionNorm && li < engLines.length && !usedEngLines.has(li)) {
        result[ri] = engLines[li]
        usedHebLines.add(li)
        usedEngLines.add(li)
        break
      }
    }
  }

  // Phase 2: Position-based proportional assignment for remaining regions
  // Uses \n\n-split paragraphs from the original English, skipping fully consumed ones
  const unmatchedRegions = regions
    .map((r, i) => ({ r, i }))
    .filter(({ i }) => !result[i] && regions[i].hebrewText?.trim())

  if (unmatchedRegions.length > 0) {
    // Build English paragraphs, excluding those fully consumed by line matching
    const allParas = fullEnglish.split(/\n\n+/).filter((p) => p.trim())
    const engParas: string[] = []
    for (const para of allParas) {
      const paraLines = para.split('\n').filter((l) => l.trim())
      const unusedLines = paraLines.filter((pl) => {
        const idx = engLines.indexOf(pl)
        return idx < 0 || !usedEngLines.has(idx)
      })
      if (unusedLines.length > 0) {
        engParas.push(unusedLines.join('\n'))
      }
    }

    const normFull = normalize(fullHebrew)
    const positioned = unmatchedRegions.map(({ r, i }) => {
      const normH = normalize(r.hebrewText!)
      let start = normFull.indexOf(normH)
      if (start < 0 && normH.length > 10) start = normFull.indexOf(normH.slice(0, 10))
      if (start < 0 && normH.length > 5) start = normFull.indexOf(normH.slice(0, 5))
      return { idx: i, start, len: normH.length }
    })

    const sorted = positioned.filter((x) => x.start >= 0).sort((a, b) => a.start - b.start)
    const totalLen = normFull.length || 1
    let paraIdx = 0

    for (let si = 0; si < sorted.length; si++) {
      const { idx, len } = sorted[si]
      const isLast = si === sorted.length - 1

      if (isLast) {
        result[idx] = engParas.slice(paraIdx).join('\n\n')
      } else {
        const hebrewFrac = len / totalLen
        const remaining = sorted.length - si - 1
        const parasNeeded = Math.max(1, Math.round(hebrewFrac * engParas.length))
        const maxParas = engParas.length - paraIdx - remaining
        const take = Math.min(parasNeeded, Math.max(1, maxParas))
        result[idx] = engParas.slice(paraIdx, paraIdx + take).join('\n\n')
        paraIdx += take
      }
    }
  }

  return result
}

function normalize(s: string): string {
  return s.replace(/[\s\-\u05BE\u200F\u200E]/g, '').replace(/["'״׳]/g, '')
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
