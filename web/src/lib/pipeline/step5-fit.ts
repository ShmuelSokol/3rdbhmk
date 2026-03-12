import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { getPageImageBuffer, updatePipelineStatus } from './shared'
import sharp from 'sharp'

/**
 * Step 5: English text fitting — center English text in expanded regions,
 * match Hebrew pixel sizes, render onto erased image, upload to Supabase.
 */
export async function runStep5(pageId: string) {
  const { imgW, imgH, page } = await getPageImageBuffer(pageId)

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

  // Get OCR boxes for bold detection
  const ocrResult = await prisma.oCRResult.findUnique({
    where: { pageId },
    include: { boxes: true },
  })

  // Assign paragraphs to regions proportionally by Hebrew char count
  const totalChars = regions.reduce((sum, r) => sum + (r.hebrewText?.length || 1), 0)
  const assignments: { region: typeof regions[0]; text: string }[] = []

  let paraIdx = 0
  for (const region of regions) {
    const charRatio = (region.hebrewText?.length || 1) / totalChars
    const paraCount = Math.max(1, Math.round(charRatio * paragraphs.length))
    const regionParas = paragraphs.slice(paraIdx, paraIdx + paraCount)
    paraIdx += paraCount

    assignments.push({
      region,
      text: regionParas.join('\n\n') || '',
    })
  }
  // Assign remaining paragraphs to last region
  if (paraIdx < paragraphs.length && assignments.length > 0) {
    assignments[assignments.length - 1].text += '\n\n' + paragraphs.slice(paraIdx).join('\n\n')
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

    // Detect bold words from text (markdown **bold**)
    const hasBoldMarkers = text.includes('**')
    const isCentered = region.regionType === 'header'

    // Build SVG text with word wrapping
    const lineHeight = Math.round(fontSize * 1.3)
    const charsPerLine = Math.max(5, Math.floor(pxWidth / (fontSize * 0.55)))

    const svgLines: string[] = []
    let yPos = fontSize + 5 // Start with some top padding

    for (const line of lines) {
      if (line.trim() === '') {
        yPos += lineHeight * 0.5
        continue
      }

      // Handle bold markers
      const segments = hasBoldMarkers
        ? line.split(/(\*\*[^*]+\*\*)/).filter(Boolean)
        : [line]

      // Word wrap
      const wrappedLines: { text: string; bold: boolean }[][] = [[]]
      let currentLineLen = 0

      for (const segment of segments) {
        const isBoldSeg = segment.startsWith('**') && segment.endsWith('**')
        const cleanText = isBoldSeg ? segment.slice(2, -2) : segment
        const words = cleanText.split(/\s+/).filter(Boolean)

        for (const word of words) {
          if (currentLineLen + word.length + 1 > charsPerLine && currentLineLen > 0) {
            wrappedLines.push([])
            currentLineLen = 0
          }
          wrappedLines[wrappedLines.length - 1].push({ text: word, bold: isBoldSeg })
          currentLineLen += word.length + 1
        }
      }

      for (const wLine of wrappedLines) {
        const lineText = wLine.map((w) => {
          const escaped = escapeXml(w.text)
          if (w.bold) {
            return `<tspan font-weight="bold">${escaped}</tspan>`
          }
          return escaped
        }).join(' ')

        const xPos = isCentered ? pxWidth / 2 : 5
        const anchor = isCentered ? 'middle' : 'start'
        svgLines.push(`<text x="${xPos}" y="${yPos}" text-anchor="${anchor}" font-family="Arial, Helvetica, sans-serif" font-size="${fontSize}" fill="black">${lineText}</text>`)
        yPos += lineHeight
      }
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
