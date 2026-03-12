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

  // Assign paragraphs to regions sequentially — one paragraph per region when counts match,
  // otherwise distribute proportionally by Hebrew char count
  const assignments: { region: typeof regions[0]; text: string }[] = []

  if (paragraphs.length === regions.length) {
    // Perfect match: one paragraph per region, top-to-bottom
    for (let i = 0; i < regions.length; i++) {
      assignments.push({ region: regions[i], text: paragraphs[i] })
    }
  } else if (paragraphs.length > regions.length) {
    // More paragraphs than regions — distribute proportionally
    const totalChars = regions.reduce((sum, r) => sum + (r.hebrewText?.length || 1), 0)
    let paraIdx = 0
    for (let ri = 0; ri < regions.length; ri++) {
      const region = regions[ri]
      const isLast = ri === regions.length - 1
      if (isLast) {
        // Last region gets all remaining paragraphs
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
    // Fewer paragraphs than regions — assign one paragraph to each region that has
    // the closest Hebrew content match, remaining regions get empty text
    const usedParas = new Set<number>()
    for (const region of regions) {
      let bestIdx = -1
      let bestScore = -1
      for (let pi = 0; pi < paragraphs.length; pi++) {
        if (usedParas.has(pi)) continue
        // Simple sequential matching — prefer paragraphs in order
        const score = pi === 0 && regions.indexOf(region) === 0 ? 1000 : 0
        const seqScore = 100 - Math.abs(pi - regions.indexOf(region))
        if (score + seqScore > bestScore) {
          bestScore = score + seqScore
          bestIdx = pi
        }
      }
      if (bestIdx >= 0) {
        usedParas.add(bestIdx)
        assignments.push({ region, text: paragraphs[bestIdx] })
      } else {
        assignments.push({ region, text: '' })
      }
    }
  }

  // Render text into SVG overlays for each region
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
    // Binary search for font size that fits all text in the region
    const lines = text.split('\n')
    let fontSize = Math.round(avgHebrewSize * 0.9) // Start slightly smaller than Hebrew
    let fitted = false

    for (let attempt = 0; attempt < 20; attempt++) {
      const lineHeight = Math.round(fontSize * 1.3)
      // Estimate: chars per line based on avg char width (~0.55 * fontSize)
      const charsPerLine = Math.floor(pxWidth / (fontSize * 0.55))
      if (charsPerLine < 5) {
        fontSize = Math.max(8, fontSize - 2)
        continue
      }

      // Word-wrap all lines
      let totalLines = 0
      for (const line of lines) {
        if (line.trim() === '') { totalLines += 1; continue }
        const words = line.split(/\s+/)
        let currentLineLen = 0
        totalLines += 1
        for (const word of words) {
          if (currentLineLen + word.length + 1 > charsPerLine && currentLineLen > 0) {
            totalLines += 1
            currentLineLen = word.length
          } else {
            currentLineLen += (currentLineLen > 0 ? 1 : 0) + word.length
          }
        }
      }

      const requiredHeight = totalLines * lineHeight + 10
      if (requiredHeight <= pxHeight) {
        fitted = true
        break
      }
      fontSize = Math.max(8, fontSize - 1)
    }

    if (!fitted) fontSize = 8

    // Detect bold from bounding boxes (measured ink density) or markdown markers
    const boldBoxCount = regionBoxes.filter((b) => b.isBold).length
    const regionIsBold = regionBoxes.length > 0 && boldBoxCount > regionBoxes.length / 2
    const hasBoldMarkers = text.includes('**')
    const isCentered = region.regionType === 'header'

    // Sample text color from original image at this region
    const textColor = sampleTextColor(pxLeft, pxTop, pxWidth, pxHeight)

    // Build SVG text with word wrapping
    const lineHeight = Math.round(fontSize * 1.3)
    const charsPerLine = Math.max(5, Math.floor(pxWidth / (fontSize * 0.55)))

    // First pass: compute all wrapped lines to know total height for vertical centering
    type WrappedLine = { segments: { text: string; bold: boolean }[] }
    const allWrappedLines: (WrappedLine | 'gap')[] = []

    for (const line of lines) {
      if (line.trim() === '') {
        allWrappedLines.push('gap')
        continue
      }

      // Handle bold markers
      const segments = hasBoldMarkers
        ? line.split(/(\*\*[^*]+\*\*)/).filter(Boolean)
        : [line]

      // Word wrap
      const wrappedLines: WrappedLine[] = [{ segments: [] }]
      let currentLineLen = 0

      for (const segment of segments) {
        const isBoldSeg = segment.startsWith('**') && segment.endsWith('**')
        const cleanText = isBoldSeg ? segment.slice(2, -2) : segment
        const words = cleanText.split(/\s+/).filter(Boolean)

        for (const word of words) {
          if (currentLineLen + word.length + 1 > charsPerLine && currentLineLen > 0) {
            wrappedLines.push({ segments: [] })
            currentLineLen = 0
          }
          wrappedLines[wrappedLines.length - 1].segments.push({ text: word, bold: isBoldSeg })
          currentLineLen += word.length + 1
        }
      }

      allWrappedLines.push(...wrappedLines)
    }

    // Calculate total content height
    let totalContentHeight = 0
    for (const wl of allWrappedLines) {
      totalContentHeight += wl === 'gap' ? lineHeight * 0.5 : lineHeight
    }

    // Vertically center: compute starting yPos
    const verticalPadding = Math.max(0, (pxHeight - totalContentHeight) / 2)
    let yPos = verticalPadding + fontSize // fontSize offset for baseline

    const svgLines: string[] = []
    for (const wl of allWrappedLines) {
      if (wl === 'gap') {
        yPos += lineHeight * 0.5
        continue
      }

      const lineText = wl.segments.map((w) => {
        const escaped = escapeXml(w.text)
        if (w.bold) {
          return `<tspan font-weight="bold">${escaped}</tspan>`
        }
        return escaped
      }).join(' ')

      const xPos = isCentered ? pxWidth / 2 : 5
      const anchor = isCentered ? 'middle' : 'start'
      const fontWeight = (regionIsBold && !hasBoldMarkers) ? ' font-weight="bold"' : ''
      svgLines.push(`<text x="${xPos}" y="${yPos}" text-anchor="${anchor}" font-family="Arial, Helvetica, sans-serif" font-size="${fontSize}" fill="${textColor}"${fontWeight}>${lineText}</text>`)
      yPos += lineHeight
    }

    const svg = `<svg width="${pxWidth}" height="${pxHeight}" xmlns="http://www.w3.org/2000/svg">${svgLines.join('')}</svg>`

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
