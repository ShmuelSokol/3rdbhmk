import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { PDFDocument, StandardFonts, rgb, PDFFont, PDFPage } from 'pdf-lib'
import fontkit from '@pdf-lib/fontkit'
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

// Optimized via autoresearch (20 experiments, 83.3% → 100%)
// Best combo: exp 20 (bodyFontSize 11, paragraphSpacing 8, lineHeight 1.5)
const DEFAULT_CONFIG: TypesetConfig = {
  pageWidth: 468,         // 6.5 inches — book trim size
  pageHeight: 648,        // 9 inches
  marginTop: 54,          // 0.75 inch
  marginBottom: 54,
  marginLeft: 54,
  marginRight: 54,
  bodyFontSize: 11,       // optimized: 10.5 → 11 (better readability)
  headerFontSize: 14,
  subheaderFontSize: 12,
  lineHeight: 1.5,        // optimized: 1.55 → 1.5 (compensates for larger font)
  paragraphSpacing: 8,    // optimized: 6 → 8 (better visual separation)
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

/** Check if a character is Hebrew (U+0590–U+05FF or U+FB1D–U+FB4F) */
function isHebrew(ch: string): boolean {
  const c = ch.charCodeAt(0)
  return (c >= 0x0590 && c <= 0x05FF) || (c >= 0xFB1D && c <= 0xFB4F)
}

/** Sanitize text for PDF — preserve Hebrew & common Unicode, remove only truly unsupported chars */
function sanitizeForPdf(text: string, keepHebrew = false): string {
  if (keepHebrew) {
    return text
      .replace(/[\u0000-\u001F]/g, '')  // remove control chars only
      .replace(/\s+/g, ' ')
      .trim()
  }
  return text
    .replace(/[\u0590-\u05FF]/g, '')   // remove Hebrew
    .replace(/[^\x00-\x7F]/g, '')       // remove non-ASCII
    .replace(/\s+/g, ' ')
    .trim()
}

/** Split text into segments of [text, isHebrew] for bidi rendering */
interface TextSegment { text: string; hebrew: boolean }

function splitBidi(text: string): TextSegment[] {
  if (!text) return []
  const segments: TextSegment[] = []
  let cur = ''
  let curHeb = isHebrew(text[0])

  for (const ch of text) {
    const heb = isHebrew(ch)
    if (heb === curHeb || ch === ' ') {
      cur += ch
    } else {
      if (cur) segments.push({ text: cur, hebrew: curHeb })
      cur = ch
      curHeb = heb
    }
  }
  if (cur) segments.push({ text: cur, hebrew: curHeb })
  return segments
}

/** For inline Hebrew quotes in ArtScroll style, we keep logical order.
 *  Each Hebrew word is visually recognizable in LTR rendering. */
function reverseHebrew(text: string): string {
  // No reversal — keep logical order for readability in mixed bidi context
  return text
}

/** Draw a line of mixed bidi text, handling font switching and RTL reversal */
function drawBidiLine(
  page: PDFPage,
  line: string,
  x: number,
  y: number,
  fontSize: number,
  latinFont: PDFFont,
  hebrewFont: PDFFont,
  color: ReturnType<typeof rgb>,
) {
  const segments = splitBidi(line)
  let curX = x

  for (const seg of segments) {
    const font = seg.hebrew ? hebrewFont : latinFont
    const drawText = seg.hebrew ? reverseHebrew(seg.text) : seg.text
    try {
      page.drawText(drawText, { x: curX, y, size: fontSize, font, color })
      curX += font.widthOfTextAtSize(drawText, fontSize)
    } catch {
      // If font can't encode a char, skip that segment
    }
  }
}

/** Measure width of a bidi line across both fonts */
function bidiLineWidth(line: string, fontSize: number, latinFont: PDFFont, hebrewFont: PDFFont): number {
  const segments = splitBidi(line)
  let w = 0
  for (const seg of segments) {
    const font = seg.hebrew ? hebrewFont : latinFont
    try { w += font.widthOfTextAtSize(seg.text, fontSize) } catch { /* skip */ }
  }
  return w
}

/** Wrap text using latin font for measurement (Hebrew chars measured with hebrewFont) */
function wrapTextBidi(text: string, latinFont: PDFFont, hebrewFont: PDFFont, fontSize: number, maxWidth: number): string[] {
  const words = text.split(/\s+/)
  if (words.length === 0) return []

  const lines: string[] = []
  let currentLine = ''

  for (const word of words) {
    if (!word) continue
    const testLine = currentLine ? `${currentLine} ${word}` : word
    const width = bidiLineWidth(testLine, fontSize, latinFont, hebrewFont)
    if (width <= maxWidth && currentLine) {
      currentLine = testLine
    } else if (!currentLine) {
      currentLine = word
    } else {
      lines.push(currentLine)
      currentLine = word
    }
  }
  if (currentLine) lines.push(currentLine)
  return lines
}

// wrapText removed — use wrapTextBidi instead

interface ContentElement {
  type: 'header' | 'body' | 'illustration' | 'divider'
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

// ─── PDF Page Decoration ─────────────────────────────────────────────────────

function decoratePage(
  pdfPage: PDFPage,
  pageNum: number,
  font: PDFFont,
  cfg: TypesetConfig,
  runningTitle?: string,
) {
  const frameColor = rgb(0.72, 0.68, 0.62)
  const lightColor = rgb(0.82, 0.78, 0.73)
  const borderOff = 8

  // Outer border frame
  const fx1 = cfg.marginLeft - borderOff
  const fy1 = cfg.marginBottom - borderOff
  const fx2 = cfg.pageWidth - cfg.marginRight + borderOff
  const fy2 = cfg.pageHeight - cfg.marginTop + borderOff + 14
  // Top line
  pdfPage.drawLine({ start: { x: fx1, y: fy2 }, end: { x: fx2, y: fy2 }, thickness: 0.7, color: frameColor })
  // Bottom line
  pdfPage.drawLine({ start: { x: fx1, y: fy1 }, end: { x: fx2, y: fy1 }, thickness: 0.7, color: frameColor })
  // Left line
  pdfPage.drawLine({ start: { x: fx1, y: fy1 }, end: { x: fx1, y: fy2 }, thickness: 0.7, color: frameColor })
  // Right line
  pdfPage.drawLine({ start: { x: fx2, y: fy1 }, end: { x: fx2, y: fy2 }, thickness: 0.7, color: frameColor })

  // Inner frame (double-line effect)
  const ix1 = fx1 + 3, iy1 = fy1 + 3, ix2 = fx2 - 3, iy2 = fy2 - 3
  pdfPage.drawLine({ start: { x: ix1, y: iy2 }, end: { x: ix2, y: iy2 }, thickness: 0.3, color: lightColor })
  pdfPage.drawLine({ start: { x: ix1, y: iy1 }, end: { x: ix2, y: iy1 }, thickness: 0.3, color: lightColor })
  pdfPage.drawLine({ start: { x: ix1, y: iy1 }, end: { x: ix1, y: iy2 }, thickness: 0.3, color: lightColor })
  pdfPage.drawLine({ start: { x: ix2, y: iy1 }, end: { x: ix2, y: iy2 }, thickness: 0.3, color: lightColor })

  // Running header
  if (runningTitle) {
    const titleStr = runningTitle.toUpperCase()
    const titleW = font.widthOfTextAtSize(titleStr, 7)
    const headerY = cfg.pageHeight - cfg.marginTop + 20
    pdfPage.drawText(titleStr, {
      x: (cfg.pageWidth - titleW) / 2,
      y: headerY,
      size: 7,
      font,
      color: rgb(0.52, 0.48, 0.44),
    })
    // Small decorative lines flanking the title
    const halfGap = 6
    pdfPage.drawLine({
      start: { x: cfg.marginLeft + 10, y: headerY + 3 },
      end: { x: (cfg.pageWidth - titleW) / 2 - halfGap, y: headerY + 3 },
      thickness: 0.3, color: lightColor,
    })
    pdfPage.drawLine({
      start: { x: (cfg.pageWidth + titleW) / 2 + halfGap, y: headerY + 3 },
      end: { x: cfg.pageWidth - cfg.marginRight - 10, y: headerY + 3 },
      thickness: 0.3, color: lightColor,
    })
  }

  // Page number with decorative dashes
  const pageStr = `\u2014  ${pageNum}  \u2014`
  const pnW = font.widthOfTextAtSize(pageStr, cfg.pageNumberFontSize)
  pdfPage.drawText(pageStr, {
    x: (cfg.pageWidth - pnW) / 2,
    y: cfg.marginBottom / 2 - 2,
    size: cfg.pageNumberFontSize,
    font,
    color: rgb(0.48, 0.45, 0.42),
  })
}

/** Draw a centered ornamental divider between sections */
function drawSectionDivider(pdfPage: PDFPage, y: number, cfg: TypesetConfig) {
  const centerX = cfg.pageWidth / 2
  const dividerColor = rgb(0.72, 0.68, 0.62)

  // Draw a diamond shape using lines (WinAnsi-safe — no special chars)
  const dSize = 3
  pdfPage.drawLine({ start: { x: centerX, y: y + dSize }, end: { x: centerX + dSize, y }, thickness: 0.6, color: dividerColor })
  pdfPage.drawLine({ start: { x: centerX + dSize, y }, end: { x: centerX, y: y - dSize }, thickness: 0.6, color: dividerColor })
  pdfPage.drawLine({ start: { x: centerX, y: y - dSize }, end: { x: centerX - dSize, y }, thickness: 0.6, color: dividerColor })
  pdfPage.drawLine({ start: { x: centerX - dSize, y }, end: { x: centerX, y: y + dSize }, thickness: 0.6, color: dividerColor })

  // Lines flanking the diamond
  const lineLen = 40
  pdfPage.drawLine({
    start: { x: centerX - dSize - 6 - lineLen, y },
    end: { x: centerX - dSize - 6, y },
    thickness: 0.4, color: dividerColor,
  })
  pdfPage.drawLine({
    start: { x: centerX + dSize + 6, y },
    end: { x: centerX + dSize + 6 + lineLen, y },
    thickness: 0.4, color: dividerColor,
  })
}

async function renderElements(
  doc: PDFDocument,
  elements: ContentElement[],
  fonts: { body: PDFFont; bold: PDFFont; header: PDFFont; hebrew: PDFFont; hebrewBold: PDFFont },
  cfg: TypesetConfig,
  startPageNum: number,
  runningTitle?: string,
): Promise<number> {
  const textWidth = cfg.pageWidth - cfg.marginLeft - cfg.marginRight
  const textHeight = cfg.pageHeight - cfg.marginTop - cfg.marginBottom
  let curY = cfg.pageHeight - cfg.marginTop
  let pdfPage = doc.addPage([cfg.pageWidth, cfg.pageHeight])
  let pageCount = 1

  decoratePage(pdfPage, startPageNum, fonts.body, cfg, runningTitle)

  const newPage = () => {
    pdfPage = doc.addPage([cfg.pageWidth, cfg.pageHeight])
    pageCount++
    curY = cfg.pageHeight - cfg.marginTop
    decoratePage(pdfPage, startPageNum + pageCount - 1, fonts.body, cfg, runningTitle)
  }

  for (const el of elements) {
    if (el.type === 'divider') {
      // Ornamental section divider between Hebrew pages
      const divH = 20
      if (curY - divH < cfg.marginBottom) {
        newPage()
      }
      curY -= 8
      drawSectionDivider(pdfPage, curY, cfg)
      curY -= divH - 8
      continue
    }

    if (el.type === 'illustration' && el.imageData) {
      // Embed illustration
      let img
      try {
        img = await doc.embedJpg(el.imageData)
      } catch {
        continue
      }

      const maxW = textWidth * cfg.illustrationMaxWidth
      const maxH = textHeight * 0.5 // cap at 50% of text area
      const baseScale = Math.min(maxW / img.width, maxH / img.height)
      let drawW = img.width * baseScale
      let drawH = img.height * baseScale
      let totalH = drawH + cfg.illustrationPadding * 2

      const remaining = curY - cfg.marginBottom
      if (totalH > remaining) {
        // Try scaling to fit remaining space instead of creating a page break gap
        const spaceForImg = remaining - cfg.illustrationPadding * 2
        if (spaceForImg > textHeight * 0.2) {
          // Remaining space is >= 20% of page — scale illustration to fit
          const fitScale = Math.min(maxW / img.width, spaceForImg / img.height)
          drawW = img.width * fitScale
          drawH = img.height * fitScale
          totalH = drawH + cfg.illustrationPadding * 2
        } else {
          // Too little space left — new page
          newPage()
        }
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
      const text = sanitizeForPdf(el.text || '', true)
      if (!text) continue

      const fontSize = cfg.headerFontSize
      const font = fonts.header
      const hebFont = fonts.hebrewBold
      const lh = fontSize * cfg.lineHeight

      curY -= cfg.headerSpacingAbove

      const lines = wrapTextBidi(text, font, hebFont, fontSize, textWidth)
      const blockH = lines.length * lh

      if (curY - blockH < cfg.marginBottom) {
        newPage()
      }

      for (const line of lines) {
        const lineW = bidiLineWidth(line, fontSize, font, hebFont)
        const x = cfg.marginLeft + (textWidth - lineW) / 2 // centered
        drawBidiLine(pdfPage, line, x, curY - fontSize, fontSize, font, hebFont, rgb(...cfg.headerColor))
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
          para.replace(/\*\*([\s\S]*?)\*\*/g, '$1').replace(/^#+\s+/gm, '').replace(/`([^`]+)`/g, '$1'),
          true // keep Hebrew
        )
        if (!cleanText) continue

        const font = isAllBold ? fonts.bold : fonts.body
        const hebFont = isAllBold ? fonts.hebrewBold : fonts.hebrew
        const fontSize = isAllBold ? cfg.subheaderFontSize : cfg.bodyFontSize
        const lh = fontSize * cfg.lineHeight

        const lines = wrapTextBidi(cleanText, font, hebFont, fontSize, textWidth - (isAllBold ? 0 : cfg.firstLineIndent))

        // Re-wrap subsequent lines at full width
        let allLines: string[]
        if (!isAllBold && lines.length > 0 && cfg.firstLineIndent > 0) {
          allLines = [lines[0]]
          if (lines.length > 1) {
            const restText = lines.slice(1).join(' ')
            allLines.push(...wrapTextBidi(restText, font, hebFont, fontSize, textWidth))
          }
        } else {
          allLines = wrapTextBidi(cleanText, font, hebFont, fontSize, textWidth)
        }

        // Render lines one by one, splitting across pages as needed
        // (prevents huge blank gaps when a long paragraph doesn't fit)
        for (let i = 0; i < allLines.length; i++) {
          // Check if current line fits on this page
          if (curY - lh < cfg.marginBottom) {
            newPage()
          }

          const line = allLines[i]
          let x = cfg.marginLeft

          if (isAllBold) {
            const lineW = bidiLineWidth(line, fontSize, font, hebFont)
            x = cfg.marginLeft + (textWidth - lineW) / 2
          } else if (i === 0 && cfg.firstLineIndent > 0) {
            x += cfg.firstLineIndent
          }

          drawBidiLine(pdfPage, line, x, curY - fontSize, fontSize, font, hebFont, rgb(...cfg.textColor))
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

    // Create PDF with fontkit for custom font embedding
    const doc = await PDFDocument.create()
    doc.registerFontkit(fontkit)

    const bodyFont = await doc.embedFont(StandardFonts.TimesRoman)
    const boldFont = await doc.embedFont(StandardFonts.TimesRomanBold)
    const headerFont = await doc.embedFont(StandardFonts.TimesRomanBold)

    // Load Hebrew fonts
    let hebrewFont: PDFFont = bodyFont // fallback
    let hebrewBoldFont: PDFFont = boldFont
    try {
      const fontsDir = path.join(process.cwd(), 'public', 'fonts')
      const hebRegularPath = path.join(fontsDir, 'NotoSerifHebrew-Regular.ttf')
      const hebBoldPath = path.join(fontsDir, 'NotoSerifHebrew-Bold.ttf')
      if (existsSync(hebRegularPath)) {
        const hebBytes = await readFile(hebRegularPath)
        hebrewFont = await doc.embedFont(hebBytes, { subset: true })
      }
      if (existsSync(hebBoldPath)) {
        const hebBoldBytes = await readFile(hebBoldPath)
        hebrewBoldFont = await doc.embedFont(hebBoldBytes, { subset: true })
      }
    } catch (e) {
      console.error('Failed to load Hebrew fonts:', e)
    }

    const fonts = { body: bodyFont, bold: boldFont, header: headerFont, hebrew: hebrewFont, hebrewBold: hebrewBoldFont }

    const runningTitle = 'Lishchno Tidreshu \u2014 English Translation'

    // Title page with elegant design
    const titlePage = doc.addPage([cfg.pageWidth, cfg.pageHeight])
    const frameColor = rgb(0.72, 0.68, 0.62)

    // Title page decorative border
    const tfx1 = cfg.marginLeft - 8, tfy1 = cfg.marginBottom - 8
    const tfx2 = cfg.pageWidth - cfg.marginRight + 8, tfy2 = cfg.pageHeight - cfg.marginTop + 22
    for (const off of [0, 3]) {
      const w = off === 0 ? 0.7 : 0.3
      titlePage.drawLine({ start: { x: tfx1 + off, y: tfy2 - off }, end: { x: tfx2 - off, y: tfy2 - off }, thickness: w, color: frameColor })
      titlePage.drawLine({ start: { x: tfx1 + off, y: tfy1 + off }, end: { x: tfx2 - off, y: tfy1 + off }, thickness: w, color: frameColor })
      titlePage.drawLine({ start: { x: tfx1 + off, y: tfy1 + off }, end: { x: tfx1 + off, y: tfy2 - off }, thickness: w, color: frameColor })
      titlePage.drawLine({ start: { x: tfx2 - off, y: tfy1 + off }, end: { x: tfx2 - off, y: tfy2 - off }, thickness: w, color: frameColor })
    }

    // Title text
    const titleText = sanitizeForPdf(book.name || 'Lishchno Tidreshu', true)
    const titleWidth = bidiLineWidth(titleText, 22, headerFont, hebrewBoldFont)
    drawBidiLine(titlePage, titleText, (cfg.pageWidth - titleWidth) / 2, cfg.pageHeight * 0.58, 22, headerFont, hebrewBoldFont, rgb(...cfg.headerColor))

    // Ornamental divider under title
    drawSectionDivider(titlePage, cfg.pageHeight * 0.55, cfg)

    // Subtitle
    const subtitleText = 'English Translation'
    const subWidth = bodyFont.widthOfTextAtSize(subtitleText, 13)
    titlePage.drawText(subtitleText, {
      x: (cfg.pageWidth - subWidth) / 2,
      y: cfg.pageHeight * 0.50,
      size: 13,
      font: bodyFont,
      color: rgb(0.4, 0.38, 0.35),
    })

    // Description
    const descText = 'The Third Beis HaMikdash According to Yechezkel HaNavi'
    const descW = bodyFont.widthOfTextAtSize(descText, 10)
    titlePage.drawText(descText, {
      x: (cfg.pageWidth - descW) / 2,
      y: cfg.pageHeight * 0.46,
      size: 10,
      font: bodyFont,
      color: rgb(0.5, 0.48, 0.44),
    })

    let totalPdfPages = 1 // title page

    // Collect ALL elements from ALL pages into one continuous flow
    // This prevents half-empty pages between sections
    const allElements: ContentElement[] = []
    let isFirstSection = true

    for (const page of pages) {
      const pageElements: ContentElement[] = []
      const regions = page.regions || []
      const translation = page.translation

      if (regions.length > 0 && regions.some(r => r.translatedText?.trim())) {
        const illustrations = await detectAndCropIllustrations(
          page.id, page.pageNumber, bookId, regions, cfg,
        )

        const sortedRegions = [...regions].sort((a, b) => a.origY - b.origY)
        let illustIdx = 0

        for (const region of sortedRegions) {
          while (illustIdx < illustrations.length && illustrations[illustIdx].y < region.origY) {
            pageElements.push({
              type: 'illustration',
              imageData: illustrations[illustIdx].imageData,
              imageWidth: illustrations[illustIdx].width,
              imageHeight: illustrations[illustIdx].height,
            })
            illustIdx++
          }

          if (!region.translatedText?.trim()) continue

          // Skip very short body regions (labels, numbers) — they waste page space
          const trimmed = region.translatedText.trim()
          const wordCount = trimmed.split(/\s+/).length
          if (region.regionType !== 'header' && wordCount < 3) continue

          if (region.regionType === 'header') {
            pageElements.push({ type: 'header', text: region.translatedText })
          } else {
            pageElements.push({ type: 'body', text: region.translatedText })
          }
        }

        while (illustIdx < illustrations.length) {
          pageElements.push({
            type: 'illustration',
            imageData: illustrations[illustIdx].imageData,
            imageWidth: illustrations[illustIdx].width,
            imageHeight: illustrations[illustIdx].height,
          })
          illustIdx++
        }

      } else if (translation?.englishOutput?.trim()) {
        pageElements.push({ type: 'body', text: translation.englishOutput })
      } else {
        continue
      }

      if (pageElements.length > 0) {
        if (!isFirstSection) {
          allElements.push({ type: 'divider' })
        }
        isFirstSection = false
        allElements.push(...pageElements)
      }
    }

    // Render all elements in one continuous flow
    if (allElements.length > 0) {
      const pagesAdded = await renderElements(doc, allElements, fonts, cfg, totalPdfPages + 1, runningTitle)
      totalPdfPages += pagesAdded
    }

    // Generate PDF buffer
    const pdfBytes = await doc.save()

    const filename = `${sanitizeForPdf(book.name || 'book')}_English_p${from}-${to}.pdf`

    return new Response(Buffer.from(pdfBytes), {
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
