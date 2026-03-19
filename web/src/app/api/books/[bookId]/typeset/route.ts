import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { PDFDocument, StandardFonts, rgb, PDFFont, PDFPage } from 'pdf-lib'
import { getPageImageBuffer } from '@/lib/pipeline/shared'
import { existsSync } from 'fs'
import { readFile } from 'fs/promises'
import path from 'path'
import sharp from 'sharp'

// ─── Typeset Config (tunable for autoresearch) ─────────────────────────────

export interface TypesetConfig {
  pageWidth: number       // PDF points (72pt = 1 inch)
  pageHeight: number
  marginTop: number
  marginBottom: number
  marginLeft: number
  marginRight: number
  bodyFontSize: number
  headerFontSize: number
  subheaderFontSize: number
  lineHeight: number      // multiplier of font size
  paragraphSpacing: number // points between paragraphs
  headerSpacingAbove: number
  headerSpacingBelow: number
  illustrationMaxWidth: number   // fraction of text width
  illustrationPadding: number    // points above/below illustration
  textColor: [number, number, number]
  headerColor: [number, number, number]
  pageNumberFontSize: number
  firstLineIndent: number  // points for paragraph first-line indent
  illustrationGapThreshold: number // % of page height gap to detect illustration
}

const DEFAULT_CONFIG: TypesetConfig = {
  pageWidth: 468,         // 6.5 inches — book trim size
  pageHeight: 648,        // 9 inches
  marginTop: 54,          // 0.75 inch
  marginBottom: 54,
  marginLeft: 54,
  marginRight: 54,
  bodyFontSize: 10.5,
  headerFontSize: 14,
  subheaderFontSize: 12,
  lineHeight: 1.55,
  paragraphSpacing: 6,
  headerSpacingAbove: 14,
  headerSpacingBelow: 6,
  illustrationMaxWidth: 0.85,
  illustrationPadding: 10,
  textColor: [0.12, 0.10, 0.08],
  headerColor: [0.08, 0.06, 0.04],
  pageNumberFontSize: 9,
  firstLineIndent: 18,
  illustrationGapThreshold: 8, // % of page height
}

// ─── Text helpers ───────────────────────────────────────────────────────────

function sanitizeForPdf(text: string): string {
  return text
    .replace(/[\u0590-\u05FF]/g, '')   // remove Hebrew
    .replace(/[^\x00-\x7F]/g, '')       // remove non-ASCII
    .replace(/\s+/g, ' ')
    .trim()
}

function wrapText(text: string, font: PDFFont, fontSize: number, maxWidth: number): string[] {
  const words = text.split(/\s+/)
  if (words.length === 0) return []

  const lines: string[] = []
  let currentLine = ''

  for (const word of words) {
    if (!word) continue
    const testLine = currentLine ? `${currentLine} ${word}` : word
    const width = font.widthOfTextAtSize(testLine, fontSize)
    if (width <= maxWidth && currentLine) {
      currentLine = testLine
    } else if (!currentLine) {
      // First word on line — must accept it even if too wide
      currentLine = word
    } else {
      lines.push(currentLine)
      currentLine = word
    }
  }
  if (currentLine) lines.push(currentLine)
  return lines
}

interface ContentElement {
  type: 'header' | 'body' | 'illustration'
  text?: string         // for header/body
  isAllBold?: boolean   // for body paragraphs
  imageData?: Buffer    // for illustrations (JPEG)
  imageWidth?: number   // original px
  imageHeight?: number  // original px
  pageNumber?: number   // source Hebrew page number
}

// ─── Illustration detection & cropping ──────────────────────────────────────

interface RegionBounds {
  origY: number
  origHeight: number
  regionType: string
}

async function detectAndCropIllustrations(
  pageId: string,
  pageNumber: number,
  bookId: string,
  regions: RegionBounds[],
  cfg: TypesetConfig,
): Promise<{ y: number; imageData: Buffer; width: number; height: number }[]> {
  if (regions.length === 0) return []

  // Sort regions by Y position
  const sorted = [...regions].sort((a, b) => a.origY - b.origY)

  // Find gaps between regions that might be illustrations
  const gaps: { topY: number; bottomY: number }[] = []

  // Gap before first region (if first region doesn't start near top)
  const firstRegionTop = sorted[0].origY
  if (firstRegionTop > cfg.illustrationGapThreshold + 5) {
    gaps.push({ topY: 3, bottomY: firstRegionTop - 1 })
  }

  // Gaps between consecutive regions
  for (let i = 0; i < sorted.length - 1; i++) {
    const bottomOfCurrent = sorted[i].origY + sorted[i].origHeight
    const topOfNext = sorted[i + 1].origY
    const gapSize = topOfNext - bottomOfCurrent

    if (gapSize > cfg.illustrationGapThreshold) {
      gaps.push({ topY: bottomOfCurrent + 0.5, bottomY: topOfNext - 0.5 })
    }
  }

  // Gap after last region (if last region doesn't reach near bottom)
  const lastRegionBottom = sorted[sorted.length - 1].origY + sorted[sorted.length - 1].origHeight
  if (lastRegionBottom < 100 - cfg.illustrationGapThreshold - 5) {
    gaps.push({ topY: lastRegionBottom + 1, bottomY: 97 })
  }

  if (gaps.length === 0) return []

  // Get original page image
  const imgBuf = await getPageImage(pageId, pageNumber, bookId)
  if (!imgBuf) return []

  const metadata = await sharp(imgBuf).metadata()
  const imgW = metadata.width || 1655
  const imgH = metadata.height || 2340

  const results: { y: number; imageData: Buffer; width: number; height: number }[] = []

  for (const gap of gaps) {
    const cropTop = Math.round((gap.topY / 100) * imgH)
    const cropBottom = Math.round((gap.bottomY / 100) * imgH)
    const cropHeight = cropBottom - cropTop

    if (cropHeight < 50) continue // too small to be meaningful

    try {
      // Crop with small horizontal margins to avoid page edges
      const marginX = Math.round(imgW * 0.03)
      const cropData = await sharp(imgBuf)
        .extract({
          left: marginX,
          top: cropTop,
          width: imgW - marginX * 2,
          height: cropHeight,
        })
        .jpeg({ quality: 90 })
        .toBuffer()

      // Check if the crop actually contains content (not just blank space)
      const stats = await sharp(imgBuf)
        .extract({
          left: marginX,
          top: cropTop,
          width: imgW - marginX * 2,
          height: cropHeight,
        })
        .stats()

      // If variance is very low, it's probably blank space
      const avgVariance = stats.channels.reduce((s, c) => s + (c.stdev || 0), 0) / stats.channels.length
      if (avgVariance < 15) continue

      const croppedMeta = await sharp(cropData).metadata()
      results.push({
        y: gap.topY,
        imageData: cropData,
        width: croppedMeta.width || imgW,
        height: croppedMeta.height || cropHeight,
      })
    } catch {
      // Skip failed crops
    }
  }

  return results
}

async function getPageImage(pageId: string, pageNumber: number, bookId: string): Promise<Buffer | null> {
  // Check cache first
  const cachePath = path.join('/tmp/bhmk', bookId, 'pages', `page-${pageNumber}.png`)
  if (existsSync(cachePath)) {
    return readFile(cachePath)
  }

  // Use shared helper (downloads PDF from Supabase, extracts page, caches)
  try {
    const result = await getPageImageBuffer(pageId)
    return result.buffer
  } catch {
    return null
  }
}

// ─── PDF Page Rendering ─────────────────────────────────────────────────────

function drawPageNumber(
  pdfPage: PDFPage,
  pageNum: number,
  font: PDFFont,
  cfg: TypesetConfig,
) {
  const text = `${pageNum}`
  const width = font.widthOfTextAtSize(text, cfg.pageNumberFontSize)
  pdfPage.drawText(text, {
    x: (cfg.pageWidth - width) / 2,
    y: cfg.marginBottom / 2,
    size: cfg.pageNumberFontSize,
    font,
    color: rgb(0.5, 0.5, 0.5),
  })
}

async function renderElements(
  doc: PDFDocument,
  elements: ContentElement[],
  fonts: { body: PDFFont; bold: PDFFont; header: PDFFont },
  cfg: TypesetConfig,
  startPageNum: number,
): Promise<number> {
  const textWidth = cfg.pageWidth - cfg.marginLeft - cfg.marginRight
  const textHeight = cfg.pageHeight - cfg.marginTop - cfg.marginBottom
  let curY = cfg.pageHeight - cfg.marginTop
  let pdfPage = doc.addPage([cfg.pageWidth, cfg.pageHeight])
  let pageCount = 1

  drawPageNumber(pdfPage, startPageNum, fonts.body, cfg)

  // Draw a thin decorative line under header area
  pdfPage.drawLine({
    start: { x: cfg.marginLeft, y: cfg.pageHeight - cfg.marginTop + 8 },
    end: { x: cfg.pageWidth - cfg.marginRight, y: cfg.pageHeight - cfg.marginTop + 8 },
    thickness: 0.5,
    color: rgb(0.8, 0.78, 0.75),
  })

  const newPage = () => {
    pdfPage = doc.addPage([cfg.pageWidth, cfg.pageHeight])
    pageCount++
    curY = cfg.pageHeight - cfg.marginTop
    drawPageNumber(pdfPage, startPageNum + pageCount - 1, fonts.body, cfg)
    pdfPage.drawLine({
      start: { x: cfg.marginLeft, y: cfg.pageHeight - cfg.marginTop + 8 },
      end: { x: cfg.pageWidth - cfg.marginRight, y: cfg.pageHeight - cfg.marginTop + 8 },
      thickness: 0.5,
      color: rgb(0.8, 0.78, 0.75),
    })
  }

  for (const el of elements) {
    if (el.type === 'illustration' && el.imageData) {
      // Embed illustration
      let img
      try {
        img = await doc.embedJpg(el.imageData)
      } catch {
        continue
      }

      const maxW = textWidth * cfg.illustrationMaxWidth
      const scale = Math.min(maxW / img.width, (textHeight * 0.6) / img.height)
      const drawW = img.width * scale
      const drawH = img.height * scale
      const totalH = drawH + cfg.illustrationPadding * 2

      if (curY - totalH < cfg.marginBottom) {
        newPage()
      }

      curY -= cfg.illustrationPadding
      const imgX = cfg.marginLeft + (textWidth - drawW) / 2
      pdfPage.drawImage(img, {
        x: imgX,
        y: curY - drawH,
        width: drawW,
        height: drawH,
      })
      curY -= drawH + cfg.illustrationPadding

    } else if (el.type === 'header') {
      const text = sanitizeForPdf(el.text || '')
      if (!text) continue

      const fontSize = cfg.headerFontSize
      const font = fonts.header
      const lh = fontSize * cfg.lineHeight

      curY -= cfg.headerSpacingAbove

      const lines = wrapText(text, font, fontSize, textWidth)
      const blockH = lines.length * lh

      if (curY - blockH < cfg.marginBottom) {
        newPage()
      }

      for (const line of lines) {
        const lineW = font.widthOfTextAtSize(line, fontSize)
        const x = cfg.marginLeft + (textWidth - lineW) / 2 // centered
        pdfPage.drawText(line, {
          x,
          y: curY - fontSize,
          size: fontSize,
          font,
          color: rgb(...cfg.headerColor),
        })
        curY -= lh
      }

      curY -= cfg.headerSpacingBelow

    } else if (el.type === 'body') {
      const rawText = el.text || ''
      if (!rawText.trim()) continue

      // Split into paragraphs by double newlines
      const paragraphs = rawText.split(/\n\s*\n/).map(p => p.replace(/\n/g, ' ').trim()).filter(Boolean)

      for (const para of paragraphs) {
        const isAllBold = para.startsWith('**') && para.endsWith('**')
        const cleanText = sanitizeForPdf(
          para.replace(/\*\*([\s\S]*?)\*\*/g, '$1').replace(/^#+\s+/gm, '').replace(/`([^`]+)`/g, '$1')
        )
        if (!cleanText) continue

        const font = isAllBold ? fonts.bold : fonts.body
        const fontSize = isAllBold ? cfg.subheaderFontSize : cfg.bodyFontSize
        const lh = fontSize * cfg.lineHeight

        const lines = wrapText(cleanText, font, fontSize, textWidth - (isAllBold ? 0 : cfg.firstLineIndent))

        // Re-wrap subsequent lines at full width
        let allLines: string[]
        if (!isAllBold && lines.length > 0 && cfg.firstLineIndent > 0) {
          // First line is narrower (indented), rest at full width
          allLines = [lines[0]]
          if (lines.length > 1) {
            const restText = lines.slice(1).join(' ')
            allLines.push(...wrapText(restText, font, fontSize, textWidth))
          }
        } else {
          allLines = wrapText(cleanText, font, fontSize, textWidth)
        }

        const blockH = allLines.length * lh + cfg.paragraphSpacing

        if (curY - blockH < cfg.marginBottom) {
          newPage()
        }

        for (let i = 0; i < allLines.length; i++) {
          const line = allLines[i]
          let x = cfg.marginLeft

          if (isAllBold) {
            // Center bold subheaders
            const lineW = font.widthOfTextAtSize(line, fontSize)
            x = cfg.marginLeft + (textWidth - lineW) / 2
          } else if (i === 0 && cfg.firstLineIndent > 0) {
            x += cfg.firstLineIndent
          }

          pdfPage.drawText(line, {
            x,
            y: curY - fontSize,
            size: fontSize,
            font,
            color: rgb(...cfg.textColor),
          })
          curY -= lh
        }

        curY -= cfg.paragraphSpacing
      }
    }
  }

  return pageCount
}

// ─── Main Route ─────────────────────────────────────────────────────────────

export async function GET(
  request: Request,
  { params }: { params: { bookId: string } },
) {
  try {
    const { bookId } = params
    const url = new URL(request.url)
    const from = parseInt(url.searchParams.get('from') || '1')
    const to = parseInt(url.searchParams.get('to') || '367')

    // Load config overrides from ?config=JSON query param (for autoresearch)
    const configParam = url.searchParams.get('config')
    let overrides: Partial<TypesetConfig> = {}
    if (configParam) {
      try { overrides = JSON.parse(configParam) } catch { /* ignore bad JSON */ }
    }
    const cfg: TypesetConfig = { ...DEFAULT_CONFIG, ...overrides }

    // Fetch book and pages
    const book = await prisma.book.findUnique({ where: { id: bookId } })
    if (!book) return NextResponse.json({ error: 'Book not found' }, { status: 404 })

    const pages = await prisma.page.findMany({
      where: {
        bookId,
        pageNumber: { gte: from, lte: to },
      },
      include: {
        regions: { orderBy: { regionIndex: 'asc' } },
        translation: true,
      },
      orderBy: { pageNumber: 'asc' },
    })

    if (pages.length === 0) {
      return NextResponse.json({ error: 'No pages found in range' }, { status: 404 })
    }

    // Create PDF
    const doc = await PDFDocument.create()
    const bodyFont = await doc.embedFont(StandardFonts.TimesRoman)
    const boldFont = await doc.embedFont(StandardFonts.TimesRomanBold)
    const headerFont = await doc.embedFont(StandardFonts.TimesRomanBold)
    const fonts = { body: bodyFont, bold: boldFont, header: headerFont }

    // Title page
    const titlePage = doc.addPage([cfg.pageWidth, cfg.pageHeight])
    const titleText = sanitizeForPdf(book.name || 'Lishchno Tidreshu')
    const titleWidth = headerFont.widthOfTextAtSize(titleText, 20)
    titlePage.drawText(titleText, {
      x: (cfg.pageWidth - titleWidth) / 2,
      y: cfg.pageHeight * 0.6,
      size: 20,
      font: headerFont,
      color: rgb(...cfg.headerColor),
    })
    const subtitleText = 'English Translation'
    const subWidth = bodyFont.widthOfTextAtSize(subtitleText, 14)
    titlePage.drawText(subtitleText, {
      x: (cfg.pageWidth - subWidth) / 2,
      y: cfg.pageHeight * 0.6 - 30,
      size: 14,
      font: bodyFont,
      color: rgb(0.4, 0.38, 0.35),
    })

    let totalPdfPages = 1 // title page

    for (const page of pages) {
      // Build content elements for this Hebrew page
      const elements: ContentElement[] = []
      const regions = page.regions || []
      const translation = page.translation

      // If page has regions with translations, use those
      if (regions.length > 0 && regions.some(r => r.translatedText?.trim())) {
        // Detect and crop illustrations from gaps between regions
        const illustrations = await detectAndCropIllustrations(
          page.id, page.pageNumber, bookId, regions, cfg,
        )

        // Build ordered list: text regions interspersed with illustrations
        const sortedRegions = [...regions].sort((a, b) => a.origY - b.origY)
        let illustIdx = 0

        for (const region of sortedRegions) {
          // Insert any illustrations that come before this region
          while (illustIdx < illustrations.length && illustrations[illustIdx].y < region.origY) {
            elements.push({
              type: 'illustration',
              imageData: illustrations[illustIdx].imageData,
              imageWidth: illustrations[illustIdx].width,
              imageHeight: illustrations[illustIdx].height,
            })
            illustIdx++
          }

          if (!region.translatedText?.trim()) continue

          if (region.regionType === 'header') {
            elements.push({
              type: 'header',
              text: region.translatedText,
            })
          } else {
            elements.push({
              type: 'body',
              text: region.translatedText,
            })
          }
        }

        // Remaining illustrations after all regions
        while (illustIdx < illustrations.length) {
          elements.push({
            type: 'illustration',
            imageData: illustrations[illustIdx].imageData,
            imageWidth: illustrations[illustIdx].width,
            imageHeight: illustrations[illustIdx].height,
          })
          illustIdx++
        }

      } else if (translation?.englishOutput?.trim()) {
        // Fallback: use full translation text
        elements.push({
          type: 'body',
          text: translation.englishOutput,
        })
      } else {
        // No translation — render original page image as-is
        const imgBuf = await getPageImage(page.id, page.pageNumber, bookId)
        if (imgBuf) {
          const jpgBuf = await sharp(imgBuf).jpeg({ quality: 85 }).toBuffer()
          elements.push({
            type: 'illustration',
            imageData: jpgBuf,
            imageWidth: 1655,
            imageHeight: 2340,
          })
        }
        continue
      }

      if (elements.length > 0) {
        const pagesAdded = await renderElements(doc, elements, fonts, cfg, totalPdfPages + 1)
        totalPdfPages += pagesAdded
      }
    }

    // Generate PDF buffer
    const pdfBytes = await doc.save()

    const filename = `${sanitizeForPdf(book.name || 'book')}_English_p${from}-${to}.pdf`

    return new Response(pdfBytes, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `inline; filename="${filename}"`,
        'Content-Length': String(pdfBytes.length),
      },
    })
  } catch (error) {
    console.error('Typeset error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Typeset failed' },
      { status: 500 },
    )
  }
}
