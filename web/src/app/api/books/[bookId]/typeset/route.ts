import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { PDFDocument, StandardFonts, rgb, PDFFont, PDFPage } from 'pdf-lib'
import fontkit from '@pdf-lib/fontkit'
import { getPageImageBuffer } from '@/lib/pipeline/shared'
import { existsSync } from 'fs'
import { readFile } from 'fs/promises'
import path from 'path'
import sharp from 'sharp'
import { generateHtmlBook, htmlToPdf } from '@/lib/html-book-generator'
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import type { TocEntry as HtmlTocEntry } from '@/lib/html-book-generator'

// bidi-js: Unicode Bidirectional Algorithm for proper RTL text rendering
// eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/no-var-requires, @typescript-eslint/no-require-imports
let _bidiModule: any = null
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function getBidi() {
  if (!_bidiModule) {
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const mod = require('bidi-js')
      // bidi-js exports a factory function — call it to get the API
      _bidiModule = typeof mod === 'function' ? mod() : (mod.default ? (typeof mod.default === 'function' ? mod.default() : mod.default) : mod)
    } catch {
      // Fallback: return stub that passes text through unchanged
      _bidiModule = {
        getEmbeddingLevels: (text: string) => ({ levels: new Uint8Array(text.length) }),
        getReorderedString: (text: string) => text,
      }
    }
  }
  return _bidiModule
}

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
  paragraphSpacing: 8,    // visual separation between paragraphs
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
      .replace(/[\u0000-\u001F]/g, '')  // remove control chars
      .replace(/[\u200B-\u200F\u2028\u2029\u202A-\u202E\uFEFF]/g, '') // remove ALL bidi marks, zero-width, embeddings
      .replace(/[\u2000-\u200A\u2010-\u2027\u2030-\u206F]/g, ' ') // replace remaining general punctuation with space
      .replace(/[\uFB50-\uFDFF\uFE70-\uFEFF]/g, '') // remove Arabic presentation forms (not in our fonts)
      .replace(/\s+/g, ' ')
      .trim()
  }
  return text
    .replace(/[\u0590-\u05FF]/g, '')   // remove Hebrew
    .replace(/[^\x00-\x7F]/g, '')       // remove non-ASCII
    .replace(/\s+/g, ' ')
    .trim()
}

/** Split text into segments of [text, isHebrew] for bidi rendering.
 *  Hebrew characters form Hebrew segments; everything else (Latin, digits,
 *  punctuation) forms non-Hebrew segments. Spaces and punctuation between
 *  two Hebrew runs stay with Hebrew so inline Hebrew phrases stay atomic. */
interface TextSegment { text: string; hebrew: boolean }

function splitBidi(text: string): TextSegment[] {
  if (!text) return []
  // Strip bidi control characters — we handle directionality via font switching
  const cleaned = text.replace(/[\u200E\u200F\u202A-\u202E]/g, '')
  if (!cleaned) return []

  // Phase 1: split into runs of Hebrew vs non-Hebrew characters.
  // Spaces/punctuation stick with the current run type.
  const segments: TextSegment[] = []
  let cur = ''
  // Find first strong character (Hebrew or Latin) to seed direction
  let curHeb = false
  for (const ch of cleaned) {
    if (isHebrew(ch)) { curHeb = true; break }
    if (/[a-zA-Z0-9]/.test(ch)) { curHeb = false; break }
  }

  for (const ch of cleaned) {
    const heb = isHebrew(ch)
    const isStrong = heb || /[a-zA-Z0-9]/.test(ch)  // has definite direction

    if (!isStrong) {
      // Neutral character (space, punctuation) — stays with current run
      cur += ch
    } else if (heb === curHeb) {
      cur += ch
    } else {
      // Direction change at a strong character
      if (cur) segments.push({ text: cur, hebrew: curHeb })
      cur = ch
      curHeb = heb
    }
  }
  if (cur) segments.push({ text: cur, hebrew: curHeb })

  // Phase 2: Fix neutral-only trailing segments and re-attach trailing neutrals.
  // When a segment ends with neutrals (spaces, punctuation) and the NEXT segment
  // has a different direction, move the trailing neutrals to the next segment.
  // This prevents e.g. ") " at the end of a Hebrew segment from being word-reversed.
  const fixed: TextSegment[] = []
  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i]
    if (i < segments.length - 1 && seg.hebrew !== segments[i + 1].hebrew) {
      // Check for trailing neutrals in this segment
      const match = seg.text.match(/^(.*[^\s\(\)\[\]\{\}.,;:!?\-–—"'""''`\/#@&*+<>=…·•°])([\s\(\)\[\]\{\}.,;:!?\-–—"'""''`\/#@&*+<>=…·•°]+)$/)
      if (match) {
        fixed.push({ text: match[1], hebrew: seg.hebrew })
        // Prepend trailing neutrals to the next segment
        segments[i + 1] = { text: match[2] + segments[i + 1].text, hebrew: segments[i + 1].hebrew }
      } else {
        fixed.push(seg)
      }
    } else {
      fixed.push(seg)
    }
  }

  return fixed
}

/** Split text into Hebrew/Latin segments for font switching.
 *  Simple character-class grouping — no bidi reordering.
 *  Hebrew text stays in logical order (font handles RTL glyph shaping). */
function getVisualSegments(text: string): TextSegment[] {
  if (!text) return []
  const segments: TextSegment[] = []
  let cur = ''
  let curHeb = false
  let started = false

  for (const ch of text) {
    const heb = isHebrew(ch)
    const isStrong = heb || /[a-zA-Z0-9]/.test(ch)

    if (!started) {
      cur = ch
      curHeb = isStrong ? heb : false
      started = true
      continue
    }

    if (!isStrong) {
      if (curHeb) {
        // Neutral char after Hebrew — check if it's safe to draw with Hebrew font
        // Only keep with Hebrew if it's a space or Hebrew punctuation (geresh, gershayim, maqaf)
        const code = ch.charCodeAt(0)
        const isHebrewSafe = ch === ' ' || (code >= 0x0590 && code <= 0x05FF) || (code >= 0xFB1D && code <= 0xFB4F) || ch === '\u05F3' || ch === '\u05F4' || ch === '\u05BE'
        if (isHebrewSafe) {
          cur += ch
        } else {
          // Push Hebrew segment, start new non-Hebrew segment for this punctuation
          if (cur) segments.push({ text: cur, hebrew: curHeb })
          cur = ch
          curHeb = false
        }
      } else {
        cur += ch // neutral chars after Latin stay with Latin (Latin font has all ASCII)
      }
    } else if (heb === curHeb) {
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

/** Draw a line of mixed bidi text using per-segment visual positioning.
 *  Uses bidi-js to determine visual order of segments, then draws each
 *  segment left-to-right with the appropriate font. Hebrew characters
 *  are in logical order for correct font shaping. */
function drawBidiLine(
  page: PDFPage,
  line: string,
  x: number,
  y: number,
  fontSize: number,
  latinFont: PDFFont,
  hebrewFont: PDFFont,
  color: ReturnType<typeof rgb>,
  maxX?: number,
) {
  // Strip ALL bidi control chars that cause rectangles — safety net
  const cleanLine = line.replace(/[\u200B-\u200F\u202A-\u202E\u2066-\u2069\uFEFF]/g, '')
  const segments = getVisualSegments(cleanLine)
  let curX = x
  const rightBound = maxX || (x + 500)

  for (const seg of segments) {
    if (curX >= rightBound) break

    const font = seg.hebrew ? hebrewFont : latinFont
    // Filter out characters that might cause rectangles — draw character by character if needed
    let drawText = seg.text
    try {
      // Test if the whole segment can be encoded
      font.widthOfTextAtSize(drawText, fontSize)
    } catch {
      // Some chars can't be encoded — filter them out
      drawText = Array.from(drawText).filter(ch => {
        try { font.widthOfTextAtSize(ch, fontSize); return true } catch { return false }
      }).join('')
      if (!drawText) {
        // Try with alternate font
        const altFont = seg.hebrew ? latinFont : hebrewFont
        drawText = Array.from(seg.text).filter(ch => {
          try { altFont.widthOfTextAtSize(ch, fontSize); return true } catch { return false }
        }).join('')
      }
    }

    if (drawText) {
      try {
        const segWidth = font.widthOfTextAtSize(drawText, fontSize)
        if (curX + segWidth <= rightBound + 5) {
          page.drawText(drawText, { x: curX, y, size: fontSize, font, color })
        }
        curX += segWidth
      } catch { /* skip entirely */ }
    }
  }
}

/** Measure width of a bidi line across both fonts.
 *  Uses visual-order splitting (after bidi reorder) for accurate width measurement
 *  that matches what drawBidiLine will actually render. */
function bidiLineWidth(line: string, fontSize: number, latinFont: PDFFont, hebrewFont: PDFFont): number {
  const cleanLine = line.replace(/[\u200B-\u200F\u202A-\u202E\u2066-\u2069\uFEFF]/g, '')
  const segments = getVisualSegments(cleanLine)
  let w = 0
  for (const seg of segments) {
    const font = seg.hebrew ? hebrewFont : latinFont
    try { w += font.widthOfTextAtSize(seg.text, fontSize) } catch { /* skip */ }
  }
  return w
}

/** Draw a justified bidi line — distributes extra space between words to fill targetWidth.
 *  Only justifies if the extra space per gap is reasonable (≤ 4pt). */
function drawJustifiedBidiLine(
  page: PDFPage,
  line: string,
  x: number,
  y: number,
  fontSize: number,
  latinFont: PDFFont,
  hebrewFont: PDFFont,
  color: ReturnType<typeof rgb>,
  targetWidth: number,
  maxX?: number,
) {
  const words = line.split(/(\s+)/).filter(w => w.trim().length > 0)
  if (words.length <= 1) {
    drawBidiLine(page, line, x, y, fontSize, latinFont, hebrewFont, color, maxX)
    return
  }

  // Measure total word width (without spaces)
  let totalWordWidth = 0
  for (const word of words) {
    totalWordWidth += bidiLineWidth(word, fontSize, latinFont, hebrewFont)
  }

  const gaps = words.length - 1
  const slack = targetWidth - totalWordWidth
  const extraPerGap = slack / gaps

  // Only justify if extra space is reasonable (≤ 4pt per gap)
  if (extraPerGap < 0 || extraPerGap > 4) {
    drawBidiLine(page, line, x, y, fontSize, latinFont, hebrewFont, color, maxX)
    return
  }

  let curX = x
  for (let i = 0; i < words.length; i++) {
    drawBidiLine(page, words[i], curX, y, fontSize, latinFont, hebrewFont, color, maxX)
    curX += bidiLineWidth(words[i], fontSize, latinFont, hebrewFont)
    if (i < words.length - 1) curX += extraPerGap
  }
}

/** Wrap text using bidi-aware chunking.
 *  Hebrew phrases are treated as atomic units — never split across lines.
 *  If a Hebrew phrase is too long for the remaining line, the ENTIRE phrase
 *  moves to the next line. Only if a Hebrew phrase is too long for a full
 *  empty line do we break it at word boundaries within the Hebrew run. */
function wrapTextBidi(text: string, latinFont: PDFFont, hebrewFont: PDFFont, fontSize: number, maxWidth: number): string[] {
  if (!text.trim()) return []

  // Step 1: Split text into bidi segments (preserves original order)
  const segments = splitBidi(text)
  if (segments.length === 0) return []

  // Step 2: Build "chunks" — atomic units for line-wrapping.
  // English segments split on whitespace (each word is a chunk).
  // Hebrew segments stay whole as one chunk (atomic), preserving internal spaces.
  interface Chunk { text: string; hebrew: boolean }
  const chunks: Chunk[] = []

  for (const seg of segments) {
    if (!seg.hebrew) {
      // English text: split on whitespace, each word is a separate chunk
      // Preserve leading/trailing space awareness
      const words = seg.text.split(/(\s+)/)
      for (const w of words) {
        if (w) chunks.push({ text: w, hebrew: false })
      }
    } else {
      // Hebrew text: keep as one atomic chunk (including internal spaces)
      // Trim trailing space only — leading space preserved
      const trimmed = seg.text.replace(/\s+$/, '')
      if (trimmed) chunks.push({ text: trimmed, hebrew: true })
    }
  }

  if (chunks.length === 0) return []

  // Step 3: Wrap chunks into lines
  const lines: string[] = []
  let currentLine = ''

  const measureLine = (line: string) => bidiLineWidth(line, fontSize, latinFont, hebrewFont)

  for (const chunk of chunks) {
    // Skip whitespace-only chunks at the start of a line
    if (!currentLine && /^\s+$/.test(chunk.text)) continue

    // For whitespace chunks, just append
    if (/^\s+$/.test(chunk.text)) {
      currentLine += chunk.text
      continue
    }

    const testLine = currentLine ? `${currentLine.trimEnd()} ${chunk.text}` : chunk.text
    const testWidth = measureLine(testLine)

    if (testWidth <= maxWidth) {
      // Fits on current line
      currentLine = testLine
    } else if (!currentLine) {
      // Empty line but chunk doesn't fit — need to force-break
      if (chunk.hebrew) {
        // Break Hebrew at word boundaries within the phrase
        const hebrewWords = chunk.text.split(/\s+/)
        let hebLine = ''
        for (const hw of hebrewWords) {
          if (!hw) continue
          const testHeb = hebLine ? `${hebLine} ${hw}` : hw
          if (measureLine(testHeb) <= maxWidth && hebLine) {
            hebLine = testHeb
          } else if (!hebLine) {
            hebLine = hw
          } else {
            lines.push(hebLine)
            hebLine = hw
          }
        }
        if (hebLine) currentLine = hebLine
      } else {
        // A single English word wider than maxWidth — just place it
        currentLine = chunk.text
      }
    } else {
      // Doesn't fit — push current line and start new with this chunk
      lines.push(currentLine.trimEnd())
      // Now check if the chunk fits on a fresh line
      if (chunk.hebrew && measureLine(chunk.text) > maxWidth) {
        // Hebrew phrase too long for a full line — break at word boundaries
        const hebrewWords = chunk.text.split(/\s+/)
        let hebLine = ''
        for (const hw of hebrewWords) {
          if (!hw) continue
          const testHeb = hebLine ? `${hebLine} ${hw}` : hw
          if (measureLine(testHeb) <= maxWidth && hebLine) {
            hebLine = testHeb
          } else if (!hebLine) {
            hebLine = hw
          } else {
            lines.push(hebLine)
            hebLine = hw
          }
        }
        currentLine = hebLine || ''
      } else {
        currentLine = chunk.text
      }
    }
  }
  if (currentLine.trimEnd()) lines.push(currentLine.trimEnd())
  return lines
}

// wrapText removed — use wrapTextBidi instead

interface ContentElement {
  type: 'header' | 'body' | 'illustration' | 'divider' | 'table' | 'caption'
  text?: string         // for header/body/caption
  isAllBold?: boolean   // for body paragraphs
  imageData?: Buffer    // for illustrations (JPEG)
  imageWidth?: number   // original px
  imageHeight?: number  // original px
  pageNumber?: number   // source Hebrew page number
  rows?: string[][]     // for tables: array of rows, each row is array of cell strings
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
  hasDiagramRef = false, // true if page has "[THIS IS DIAGRAM" or "Drawing N" in text
): Promise<{ y: number; imageData: Buffer; width: number; height: number }[]> {
  if (regions.length === 0) return []

  // Sort regions by Y position
  const sorted = [...regions].sort((a, b) => a.origY - b.origY)

  // Find gaps between regions that might be illustrations
  const gaps: { topY: number; bottomY: number }[] = []

  // Gap before first region (if first region doesn't start near top)
  const firstRegionTop = sorted[0].origY
  if (firstRegionTop > cfg.illustrationGapThreshold + 5) {
    gaps.push({ topY: 3, bottomY: firstRegionTop - 0.5 })
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

  // Merge adjacent gaps that are close together (< 10% apart) — prevents splitting
  // one illustration into two crops when gap detection finds a thin text band in the middle
  const mergedGaps: { topY: number; bottomY: number }[] = []
  for (const gap of gaps.sort((a, b) => a.topY - b.topY)) {
    const prev = mergedGaps[mergedGaps.length - 1]
    if (prev && gap.topY - prev.bottomY < 10) {
      prev.bottomY = gap.bottomY // merge into previous gap
    } else {
      mergedGaps.push({ ...gap })
    }
  }

  // Get original page image
  const imgBuf = await getPageImage(pageId, pageNumber, bookId)
  if (!imgBuf) return []

  const metadata = await sharp(imgBuf).metadata()
  const imgW = metadata.width || 1655
  const imgH = metadata.height || 2340

  const results: { y: number; imageData: Buffer; width: number; height: number }[] = []

  for (const gap of mergedGaps) {
    const cropTop = Math.round((gap.topY / 100) * imgH)
    const cropBottom = Math.round((gap.bottomY / 100) * imgH)
    const cropHeight = cropBottom - cropTop

    if (cropHeight < 200) continue // min 200px height — filters out page design residue

    try {
      // Minimal horizontal margins — just 1% to avoid very edge artifacts
      // (was 3% but cut off letter/image content on sides)
      const marginX = Math.round(imgW * 0.01)
      const cropData = await sharp(imgBuf)
        .extract({
          left: marginX,
          top: cropTop,
          width: imgW - marginX * 2,
          height: cropHeight,
        })
        .jpeg({ quality: 50 })
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

      // If variance is low, it's probably blank space or just page design/borders
      // Use lower threshold (15) for pages with known diagram references to preserve real diagrams
      // Use higher threshold (30) for other pages to filter beige/cream page design residue
      const avgVariance = stats.channels.reduce((s, c) => s + (c.stdev || 0), 0) / stats.channels.length
      const varianceThreshold = hasDiagramRef ? 15 : 30
      if (avgVariance < varianceThreshold) continue

      // Check mean brightness — bright crops with low variance are just page background/borders
      const avgMean = stats.channels.reduce((s, c) => s + (c.mean || 0), 0) / stats.channels.length
      if (avgMean > 200 && avgVariance < 50) continue // bright + low-medium variance = page background
      if (avgMean > 230 && avgVariance < 55) continue // very bright — higher variance still noise
      // Also filter crops that are very uniform in any channel (page design patterns)
      const minStdev = Math.min(...stats.channels.map(c => c.stdev || 0))
      if (minStdev < 10 && avgMean > 180) continue // at least one channel is very uniform + bright
      if (minStdev < 15 && avgMean > 220) continue // almost uniform + very bright

      // Trim yellowish/beige borders to maximize illustration area
      const trimmedData = await trimIllustrationBorders(cropData)
      const trimmedMeta = await sharp(trimmedData).metadata()
      results.push({
        y: gap.topY,
        imageData: trimmedData,
        width: trimmedMeta.width || imgW,
        height: trimmedMeta.height || cropHeight,
      })
    } catch {
      // Skip failed crops
    }
  }

  return results
}

/** Trim yellowish/beige borders from cropped illustrations to maximize image area */
async function trimIllustrationBorders(imgBuffer: Buffer): Promise<Buffer> {
  const meta = await sharp(imgBuffer).metadata()
  const w = meta.width || 100
  const h = meta.height || 100
  if (w < 20 || h < 20) return imgBuffer

  // Get raw pixel data to analyze edges
  const { data, info } = await sharp(imgBuffer)
    .raw()
    .toBuffer({ resolveWithObject: true })

  const channels = info.channels
  const stride = info.width * channels

  // Helper: check if a pixel is "border-like" (yellowish/beige/white background)
  const isBorderPixel = (offset: number): boolean => {
    const r = data[offset]
    const g = data[offset + 1]
    const b = data[offset + 2]
    // Yellowish/beige: high R, high G, lower B, generally bright
    const lum = 0.299 * r + 0.587 * g + 0.114 * b
    if (lum > 200) return true // near-white
    if (r > 180 && g > 160 && b < r - 30 && lum > 150) return true // yellowish
    if (r > 170 && g > 150 && b > 130 && Math.abs(r - g) < 40 && lum > 170) return true // beige
    return false
  }

  // Check if an entire row is mostly border pixels
  const isRowBorder = (row: number): boolean => {
    let borderCount = 0
    const sampleStep = Math.max(1, Math.floor(info.width / 30))
    let samples = 0
    for (let x = 0; x < info.width; x += sampleStep) {
      const off = row * stride + x * channels
      if (isBorderPixel(off)) borderCount++
      samples++
    }
    return borderCount / samples > 0.85
  }

  // Check if an entire column is mostly border pixels
  const isColBorder = (col: number): boolean => {
    let borderCount = 0
    const sampleStep = Math.max(1, Math.floor(info.height / 30))
    let samples = 0
    for (let y = 0; y < info.height; y += sampleStep) {
      const off = y * stride + col * channels
      if (isBorderPixel(off)) borderCount++
      samples++
    }
    return borderCount / samples > 0.85
  }

  // Find content bounds by scanning inward from edges
  let top = 0
  while (top < info.height * 0.3 && isRowBorder(top)) top++

  let bottom = info.height - 1
  while (bottom > info.height * 0.7 && isRowBorder(bottom)) bottom--

  let left = 0
  while (left < info.width * 0.3 && isColBorder(left)) left++

  let right = info.width - 1
  while (right > info.width * 0.7 && isColBorder(right)) right--

  // Only trim if we found significant borders (at least 3px on any side)
  const trimmedW = right - left + 1
  const trimmedH = bottom - top + 1
  if (trimmedW < info.width * 0.5 || trimmedH < info.height * 0.5) {
    return imgBuffer // trimming would remove too much — likely not a border issue
  }
  if (top < 3 && left < 3 && right > info.width - 4 && bottom > info.height - 4) {
    return imgBuffer // nothing meaningful to trim
  }

  return sharp(imgBuffer)
    .extract({ left, top, width: trimmedW, height: trimmedH })
    .jpeg({ quality: 60 })
    .toBuffer()
}

/** Parse table text: split by pipes and newlines into rows/columns */
function parseTableText(text: string): string[][] {
  const lines = text.split(/\n/).map(l => l.trim()).filter(Boolean)
  const rows: string[][] = []
  for (const line of lines) {
    if (line.includes('|')) {
      rows.push(line.split('|').map(c => c.trim()).filter(Boolean))
    } else {
      // Single-column row
      rows.push([line])
    }
  }
  return rows
}

/** Detect if text content looks like a table (numbered list, pipe-separated, aligned data) */
function isTableContent(text: string, regionType: string): boolean {
  if (regionType === 'table') return true
  if (text.includes('|')) return true
  // Check for numbered list pattern (at least 3 items like "1. ...", "2. ...", "3. ...")
  const numberedLines = text.split('\n').filter(l => /^\s*\d+[\.\)]\s/.test(l))
  if (numberedLines.length >= 3) return true
  return false
}

/** Clean translation text: remove meta-text artifacts from Claude translations */
function cleanTranslationText(text: string): string {
  return text
    // Remove meta-text markers like "[THIS IS TABLE:", "[THIS IS DIAGRAM:", "[TABLE:", etc.
    .replace(/\[THIS IS (TABLE|DIAGRAM|CHART|IMAGE|FIGURE)[:\]]/gi, '')
    .replace(/\[(TABLE|DIAGRAM|CHART|IMAGE|FIGURE):\s*/gi, '')
    .replace(/\[END (TABLE|DIAGRAM|CHART|FIGURE)\]/gi, '')
    .replace(/\[Note:.*?\]/gi, '')
    // Remove [Diagram showing measurements: ...] blocks
    .replace(/\[(?:Diagram|Figure|Drawing)\s+showing\s+[^\]]*\]/gi, '')
    // Fix concatenation errors: insert space between camelCase-like merges
    .replace(/([a-z])\n([A-Z])/g, '$1 $2')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    // Strip leading Hebrew block up to separator (em-dash or hyphen).
    // Matches: any prefix containing Hebrew chars, up to and including " — " or " - "
    // Must contain at least one Hebrew char; stops at the separator.
    .replace(/^[^\n]*?[\u0590-\u05FF\uFB1D-\uFB4F][^\n]*?\s*[\u2014\u2013]\s*/g, '')
    .replace(/^[^\n]*?[\u0590-\u05FF\uFB1D-\uFB4F][^\n]*?\s+\-\s+/g, '')
    // Then strip orphan page numbers left behind (number + period/space + newline)
    .replace(/^\d+[.\s]*\n/g, '')
    // Strip Hebrew-only lines at the start (no em-dash, just pure Hebrew line then English)
    .replace(/^[\u0590-\u05FF\u200E\u200F\uFB1D-\uFB4F\s׳״']+\n+/g, '')
    // Strip leftover separator junk at start: ". — ", "— ", "- ", etc.
    .replace(/^[\s.,;:\u2014\u2013\-]+(?=[A-Z([\d])/g, '')
    // Collapse repeated consecutive words (case-insensitive), excluding valid English patterns
    .replace(/\b(\w{3,})\s+\1\b/gi, (match, word) => {
      const lower = word.toLowerCase()
      if (['there', 'that', 'had', 'very', 'so', 'now'].includes(lower)) return match
      return word
    })
    // Strip trailing ] left from [THIS IS DIAGRAM: ...] cleanup
    .replace(/\]$/g, '')
    .replace(/\]\s*\./g, '.')
    .trim()
}

/** Remove consecutive duplicate sentences/clauses from text.
 *  Only removes when a sentence/clause is immediately repeated (back-to-back). */
function deduplicatePhrases(text: string): string {
  if (!text || text.length < 80) return text
  // Split by sentence boundaries and remove consecutive identical sentences
  const sentences = text.split(/(?<=[.!?])\s+/)
  if (sentences.length < 2) return text
  const deduped: string[] = [sentences[0]]
  for (let i = 1; i < sentences.length; i++) {
    const prev = deduped[deduped.length - 1].toLowerCase().trim()
    const curr = sentences[i].toLowerCase().trim()
    // Skip if this sentence is identical to the previous one
    if (curr === prev) continue
    // Skip if this sentence is a substring of the previous (partial repeat)
    if (prev.length > 30 && curr.length > 30 && prev.includes(curr)) continue
    deduped.push(sentences[i])
  }
  return deduped.join(' ')
}

/** Check if text is primarily a garbled measurement diagram — numbers + units
 *  arranged spatially in Hebrew that lose meaning when linearized.
 *  These should be skipped since the original Hebrew page image is shown. */
function isMeasurementNoise(text: string): boolean {
  const lines = text.split(/\n/).filter(l => l.trim())
  if (lines.length < 2) return false
  const measLines = lines.filter(l => {
    const lt = l.trim()
    return /^\d+\.?\d*\s*(?:amos?|amah?|a'|tefach)/i.test(lt) ||
           /^(?:amos?|amah?|a')\s*=?\s*\d/i.test(lt) ||
           /^\d+\s*(?:amos?|amah?|a')$/i.test(lt) ||
           /^\d+$/i.test(lt) ||
           (lt.split(/\s+/).length <= 3 && /\d/.test(lt) && /amo|ama|a'/i.test(lt))
  })
  // If ≥30% of lines are measurement-only and there are at least 2, it's noise
  return measLines.length >= 2 && measLines.length / lines.length > 0.3
}

/** Check if text is a recurring Hebrew source header that should be filtered out.
 *  These repeat on every page of the Hebrew book and shouldn't appear inline.
 *  pageRegionCount: how many regions this page has — if it's the only region, keep it (title page). */
function isRecurringSourceHeader(text: string, hebrewText?: string, pageRegionCount?: number): boolean {
  // If this is the only content on the page, DON'T filter it (it's a title/cover page)
  if (pageRegionCount !== undefined && pageRegionCount <= 2) return false

  const t = text.trim().toLowerCase()
  const h = (hebrewText || '').trim()
  // Filter recurring Hebrew section markers (exact match only)
  const recurringHebrew = ['באור חי', 'קץ הימין', 'השלמת שרת']
  for (const rh of recurringHebrew) {
    if (h === rh) return true
  }
  // Filter "לשכנו תדרשו" when standalone and on a page with other content
  if (h === 'לשכנו תדרשו' && t.length < 60) return true
  // Filter English versions of recurring headers
  const recurringEnglish = [
    "or chai", "ketz hayamin", "the completion of service",
  ]
  for (const re of recurringEnglish) {
    if (t === re) return true
  }
  return false
}

/** Detect if a page is a Table of Contents page (should be skipped — we generate our own) */
function isTocPage(regions: { translatedText?: string | null; hebrewText?: string | null; regionType: string }[]): boolean {
  const allText = regions.map(r => (r.translatedText || '') + ' ' + (r.hebrewText || '')).join(' ').toLowerCase()
  // Look for TOC indicators
  const hasTocTitle = /main topics|table of contents|contents|תוכן עניינים/.test(allText)
  const hasPageRefs = (allText.match(/\d+-\d+/g) || []).length >= 3 // page ranges like "97-100"
  const hasPasukRefs = (allText.match(/perek|pasuk|פרק|פסוק/gi) || []).length >= 3
  return hasTocTitle && (hasPageRefs || hasPasukRefs)
}

/** Check if text is just a standalone Hebrew source page number (should be filtered out) */
function isStandalonePageNumber(text: string): boolean {
  const trimmed = text.trim()
  // Just a number (1-3 digits) — likely a Hebrew source page number
  if (/^\d{1,3}$/.test(trimmed)) return true
  // Number with surrounding whitespace/newlines only
  if (/^\s*\d{1,3}\s*$/.test(trimmed)) return true
  return false
}

/** Detect if a page is primarily a diagram/flowchart (mostly short labels, not body text) */
function isDiagramPage(regions: { translatedText?: string | null; regionType: string; origHeight: number }[]): boolean {
  const translated = regions.filter(r => r.translatedText?.trim())

  // Check for explicit diagram markers — but only in SHORT regions (<50 words)
  // where the marker IS the primary content, not just mentioned in passing
  // in a long body paragraph like "See Drawing 5 on the next page"
  const diagramMarkerPattern = /\[THIS IS DIAGRAM|\[DIAGRAM LABELS|^\s*Drawing \d|^\s*Diagram \d|^\s*Sketch of|^\s*Layout of|^\s*Figure \d|^\s*Floor plan/i
  let diagramMarkerCount = 0
  for (const r of translated) {
    const text = (r.translatedText || '').trim()
    if (text.split(/\s+/).length < 50 && diagramMarkerPattern.test(text)) {
      diagramMarkerCount++
    }
  }
  // Need at least 2 diagram marker regions, or 1 marker + many short labels
  if (diagramMarkerCount >= 2) return true

  if (translated.length < 3) return false

  const shortLabels = translated.filter(r => {
    const words = (r.translatedText || '').trim().split(/\s+/).length
    return words < 10
  })

  // If >50% of regions are short labels and there are at least 4 of them, it's a diagram page
  if (shortLabels.length >= 4 && shortLabels.length / translated.length > 0.5) return true

  // 1 diagram marker + significant short labels (>30%) = diagram page
  if (diagramMarkerCount >= 1 && shortLabels.length >= 3 && shortLabels.length / translated.length > 0.3) return true

  // Also check for repeated similar text (diagram labels often repeat)
  const texts = translated.map(r => (r.translatedText || '').trim().toLowerCase())
  const uniqueTexts = new Set(texts)
  if (texts.length > 4 && uniqueTexts.size < texts.length * 0.5) return true

  return false
}

/** Detect if a page is an approval/endorsement letter (handwritten text, official letterhead) */
function isLetterPage(regions: { translatedText?: string | null; regionType: string; hebrewText?: string | null }[], pageNumber: number): boolean {
  // Pages 2-12 are the intro/letter section of the Hebrew book
  // These contain approval letters, endorsements, and acknowledgments
  // that should be shown as full images with translation below
  if (pageNumber >= 4 && pageNumber <= 12) {
    const allText = regions.map(r => (r.translatedText || '')).join(' ').toLowerCase()
    const letterKeywords = [
      'letter of endorsement', 'letter of approbation', 'letter of blessing',
      'with blessings', 'fax', 'tel:', 'p.o.b.', 'phone:', 'under the auspices',
      'federation', 'yeshiv', 'with the blessing of', 'hereby give my blessing',
      'endorsement', 'approbation', 'haskamah', 'kollel', 'beis knesses',
      'beis medrash', 'beis din', 'rav and av', 'chief rabbi', 'harav',
      'shlita', 'address', 'registered association', 'date:',
    ]
    const matches = letterKeywords.filter(kw => allText.includes(kw))
    // For pages in the letter section, require only 1 match (more lenient)
    return matches.length >= 1
  }
  return false
}

/** Generate a meaningful description of what a diagram/image depicts based on its labels and context */
function generateImageDescription(
  labels: string[],
  bodyTexts: string[],
): string {
  // Deduplicate labels
  const uniqueLabels = Array.from(new Set(labels.map(l => l.trim()))).filter(Boolean)

  // If there are body texts (longer passages), use those as the main description
  if (bodyTexts.length > 0) {
    return bodyTexts.join('\n\n')
  }

  // Otherwise, create a descriptive summary from the labels
  if (uniqueLabels.length === 0) return ''

  // Group labels by theme to create a meaningful description
  const hasSpiritual = uniqueLabels.some(l => /spiritual|ruchani/i.test(l))
  const hasPhysical = uniqueLabels.some(l => /physical|gashmiy/i.test(l))
  const hasBeis = uniqueLabels.some(l => /beis|mikdash|temple/i.test(l))
  const hasMishkan = uniqueLabels.some(l => /mishkan|tabernacle/i.test(l))
  const hasMeasurements = uniqueLabels.some(l => /amos|cubit|ama/i.test(l))

  let description = 'This diagram illustrates '
  if (hasSpiritual && hasPhysical) {
    description += 'the relationship between the spiritual and physical dimensions of the Batei Mikdash'
  } else if (hasBeis && hasMishkan) {
    description += 'the connection between the Mishkan and the Beis HaMikdash'
  } else if (hasMeasurements) {
    description += 'the architectural measurements and layout of the structure'
  } else if (hasBeis) {
    description += 'aspects of the Beis HaMikdash structure'
  } else {
    description += 'the following concepts: ' + uniqueLabels.slice(0, 6).join(', ')
  }
  description += '.'

  return description
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

  // Running header — positioned ABOVE the border frame, not on it
  if (runningTitle) {
    const titleStr = runningTitle.toUpperCase()
    const titleW = font.widthOfTextAtSize(titleStr, 7)
    const headerY = fy2 + 10 // 10pt above the outer border top line
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

  // Page numbers are drawn AFTER all pages are finalized (see addPageNumbers)
  // This ensures correct numbering even after TOC page insertion
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

interface TocEntry {
  title: string
  pageNum: number // relative to content start (will be adjusted for TOC pages)
  isPerek?: boolean // true if this is a Perek-level entry (used for TOC grouping)
  afterDivider?: boolean // true if this header immediately follows a section divider
}

/** Clean a header title for TOC display: remove leading punctuation, quotes, stray chars */
function cleanTocTitle(title: string): string {
  let cleaned = title
    .replace(/^[\s'"`,.\-:;*#()\[\]]+/, '') // remove leading punctuation
    .replace(/[\s'"`,.\-:;*#()\[\]]+$/, '') // remove trailing punctuation
    .replace(/^\d+\s+[A-Z]\d+\s+/, '')      // remove leading numbering like "5 A5 "
    .replace(/^\.\s*[A-Z][\.\)]\s*/, '')     // remove leading ". A." style numbering
    .replace(/^\d+(?:[.\)]?\s*)?(?=[A-Z])/, '') // remove leading "19" or "28" before title text
    .replace(/\*\*/g, '')                     // remove markdown bold markers
    .replace(/^Page\s+\d+\s*/i, '')          // remove "Page 85" prefixes
    .replace(/\s+/g, ' ')
    .trim()

  // Strip recurring book subtitle patterns from the END of titles
  // Run in a loop because stripping one suffix may expose another
  // (e.g., "The Chambers You Shall Seek" → strip "You Shall Seek" → strip "The Chambers")
  let prev = ''
  while (cleaned !== prev) {
    prev = cleaned
    cleaned = cleaned
      .replace(/\s*,?\s*(?:Lishchno|L'Shichno|Leshachno|Lishkano|Lishluno|Le Sichno)\s+(?:Tidreshu|Sidrosh|Sidreshu|Tidr.shu|Tidrsheu|tidr.shu|Tidrsu)\s*$/i, '')
      .replace(/\s*(?:"?To His dwelling (?:shall |place )?you shall seek"?)$/i, '')
      .replace(/\s*(?:"?His dwelling (?:shall )?you shall seek"?)$/i, '')
      .replace(/\s*(?:"?(?:Its|Their|Your|its|their|your) chambers? you shall (?:seek|inquire)"?)$/i, '')
      .replace(/\s*(?:"?(?:Its|Their|Your|its|their|your) dwelling place you shall seek"?)$/i, '')
      .replace(/\s*(?:"?(?:Seek out His dwelling place)"?)$/i, '')
      .replace(/\s*(?:"?For (?:their|its) chambers? you shall seek"?)$/i, '')
      .replace(/\s*(?:"?(?:you shall seek|shall you seek)\s*"?)$/i, '')
      .replace(/\s*(?:Or Chai|Ohr Chai|B'Or Chai|Ba'or Chai|Or Chayim)[\d\s]*.*$/i, '')
      .replace(/\s*(?:The )?Completion of Service$/i, '')
      .replace(/\s*(?:"?to (?:inquire|seek) (?:of )?(?:its|their|his) chambers?"?)$/i, '')
      .replace(/\s*You Shall Seek His Dwelling\s*$/i, '')
      .replace(/\s*"?To His dwelling\s*$/i, '')
      .replace(/\s*"?To His dwelling place\s*$/i, '')
      .replace(/\s*His Dwelling Place\s*$/i, '')
      .replace(/\s*The Chambers That\s*$/i, '')
      .replace(/\s*The Chambers\s*$/i, '')
      .replace(/\s*To seek them out\s*$/i, '')
      .replace(/\s*"?To His chambers\s.*$/i, '')
      .replace(/\s*"?To its chambers\s*$/i, '')
      .replace(/\s*"?to its chambers\s.*$/i, '')
      .replace(/\s*You shall seek their chambers\s*$/i, '')
      .replace(/\s*"?And you shall seek out its chambers\s*$/i, '')
      .replace(/\s*"?their chambers you shall seek\s*$/i, '')
      .replace(/\s*You shall seek\s*$/i, '')
      .replace(/[\s'"`,.\-:;]+$/, '')
      .replace(/\s+["']?(?:And|To|to|For|for|In|in|A|a|The|the|Of|of|On|on)["']?$/i, '')
      .replace(/[\s'"`,.\-:;:]+$/, '')
      .trim()
  }

  return cleaned
}

/** Check if a TOC entry title should be excluded (noise/garbage) */
function isTocExcluded(title: string): boolean {
  if (!title) return true
  // Pasuk/Pesukim entries can be shorter (e.g., "Pasuk 1" = 7 chars after cleaning)
  const isPasuk = /^pasuk|^pesukim/i.test(title)
  const minLen = isPasuk ? 7 : 15
  if (title.length < minLen || title.length > 90) return true
  const words = title.split(/\s+/)
  if (!isPasuk && words.length < 2) return true
  if (/^\d+$/.test(title.trim())) return true

  const lower = title.toLowerCase()
  const excludePatterns = [
    /^or chai/i,
    /^ketz\b/i,
    /^completion\b/i,
    /^the completion of service/i,
    /^north\b$/i, /^south\b$/i, /^east\b$/i, /^west\b$/i,
    /^\d+\s*amos?\b/i,
    /^translation of/i,
    /^this diagram/i,
    /^this table/i,
    /^table of contents/i,
    /^main topics/i,
    /^lishchno tidreshu$/i,
    /^l'shichno\b/i,
    /^leshachno\b/i,
    /^lishkano\b/i,
    /^published by/i,
    /^here in the/i,
    /^shows measurement/i,
    /^sefer\b/i,
    /^diagram\b/i,
    /^rabbi\b/i,               // Rabbi names from letter pages
    /^rav\s/i,                 // Rav names from letter pages
    /^harav\b/i,               // HaRav names
    /spiritual beis supreme/i, // diagram labels
    /physical beis\b/i,        // diagram labels
    /^to his dwelling/i,       // recurring book subtitle
    /^his dwelling/i,
    /^a psalm of/i,
    /^le sichno/i,
    /^le'sichno/i,
    /about the book/i,
    /^you shall seek/i,
    /^seek out his/i,
    /^seek his dwelling/i,
    /^its dwelling/i,
    /^west\d/i,              // garbled table text
    /minority.*majority/i,  // garbled table text
    /^the prophecy of/i,
    /^part [IV]+$/i,         // just "Part I" etc.
    /^a psalm\b/i,
    /^lishluno\b/i,
    /^And he (made|measured)/i, // quote beginnings
    /^"And\b/i,              // quote-only entries
    /^And there was/i,
    /^"In visions/i,
    /^you shall seek/i,       // recurring book subtitle variant
    /^shall you seek/i,       // recurring book subtitle variant
    /^his dwelling\b/i,
    /^their chambers\b/i,
  ]
  for (const pat of excludePatterns) {
    if (pat.test(lower)) return true
  }
  return false
}

/** Determine if a header is TOC-worthy — meaningful topic headers a reader would look up.
 *  This is used as a secondary check; post-divider headers are always included. */
function isTocWorthyHeader(title: string): boolean {
  if (isTocExcluded(title)) return false
  const lower = title.toLowerCase()

  // High-value keywords that indicate a real section
  const sectionKeywords = [
    'introduction', 'foreword', 'preface', 'overview', 'conclusion',
    'chapter', 'perek', 'summary',
  ]
  if (sectionKeywords.some(kw => lower.includes(kw))) return true

  return false
}

async function renderElements(
  doc: PDFDocument,
  elements: ContentElement[],
  fonts: { body: PDFFont; bold: PDFFont; header: PDFFont; hebrew: PDFFont; hebrewBold: PDFFont },
  cfg: TypesetConfig,
  startPageNum: number,
  runningTitle?: string,
): Promise<{ pageCount: number; tocEntries: TocEntry[] }> {
  const textWidth = cfg.pageWidth - cfg.marginLeft - cfg.marginRight
  const safeMarginBottom = cfg.marginBottom + 20 // generous buffer — text must NEVER touch page numbers
  const textHeight = cfg.pageHeight - cfg.marginTop - safeMarginBottom
  let curY = cfg.pageHeight - cfg.marginTop
  let pdfPage = doc.addPage([cfg.pageWidth, cfg.pageHeight])
  let pageCount = 1
  const tocEntries: TocEntry[] = []

  decoratePage(pdfPage, startPageNum, fonts.body, cfg, runningTitle)

  let contentRenderedOnPage = false // tracks if real content was rendered on current page

  // Deferred text: when a short body/header/caption precedes a bottom-placed image,
  // we defer its rendering so it can be drawn just above the image.
  let deferredText: {
    lines: string[];
    font: PDFFont;
    hebFont: PDFFont;
    fontSize: number;
    lh: number;
    isAllBold: boolean;
    hasIndent: boolean;
    centered: boolean;
    color: [number, number, number];
    spacingAfter: number;
  } | null = null

  const newPage = () => {
    pdfPage = doc.addPage([cfg.pageWidth, cfg.pageHeight])
    pageCount++
    curY = cfg.pageHeight - cfg.marginTop
    contentRenderedOnPage = false
    decoratePage(pdfPage, startPageNum + pageCount - 1, fonts.body, cfg, runningTitle)
  }

  let lastWasDivider = true // first header is always a topic start
  for (let elIdx = 0; elIdx < elements.length; elIdx++) {
    const el = elements[elIdx]

    // Safety: flush deferred text if the current element is NOT an illustration
    // (deferred text is only meant to be consumed by the next illustration)
    if (deferredText && el.type !== 'illustration') {
      const dt = deferredText
      for (let li = 0; li < dt.lines.length; li++) {
        if (curY - dt.lh < safeMarginBottom) newPage()
        const ln = dt.lines[li]
        let x = cfg.marginLeft
        if (dt.centered) {
          const lineW = bidiLineWidth(ln, dt.fontSize, dt.font, dt.hebFont)
          x = cfg.marginLeft + (textWidth - lineW) / 2
        } else if (li === 0 && dt.hasIndent) {
          x += cfg.firstLineIndent
        }
        drawBidiLine(pdfPage, ln, x, curY - dt.fontSize, dt.fontSize, dt.font, dt.hebFont, rgb(...dt.color), cfg.pageWidth - cfg.marginRight)
        curY -= dt.lh
      }
      curY -= dt.spacingAfter
      contentRenderedOnPage = true
      deferredText = null
    }

    if (el.type === 'divider') {
      // New topic = new page (matches Hebrew book layout)
      // EXCEPTION: if the next element is an illustration and there's space on this page,
      // skip the new page — let the image fill the remaining space instead of leaving blank
      // Check next few elements after divider — if an illustration is coming soon,
      // keep it on the current page to fill blank space
      const remainingSpace = curY - safeMarginBottom
      const usedSpace = (cfg.pageHeight - cfg.marginTop) - curY
      let illustrationComingSoon = false
      for (let look = 1; look <= 3 && elIdx + look < elements.length; look++) {
        const upcoming = elements[elIdx + look]
        if (upcoming.type === 'illustration') { illustrationComingSoon = true; break }
        if (upcoming.type === 'divider') break // another divider = stop looking
        if (upcoming.type === 'body') break // body text = it's a real section, not just an image
      }

      if (illustrationComingSoon && remainingSpace > textHeight * 0.25) {
        // Enough space for an image — just draw a small divider, don't force new page
        curY -= 8
        drawSectionDivider(pdfPage, curY, cfg)
        curY -= 14
      } else if (usedSpace > 20 && contentRenderedOnPage) {
        // Only create a new page if we actually rendered content on this one.
        // If no content was rendered (blank page), suppress the new page to avoid blank pages.
        newPage()
        curY -= 8
        drawSectionDivider(pdfPage, curY, cfg)
        curY -= 14
      } else {
        // Already at top of page or no content rendered — just draw divider in place
        curY -= 8
        drawSectionDivider(pdfPage, curY, cfg)
        curY -= 14
      }
      lastWasDivider = true
      continue
    }

    if (el.type === 'illustration' && el.imageData) {
      // Check if previous element was a caption/header that should stay with this image
      // If we're about to start a new page for the image, check if the caption above
      // used less than 15% of the page — if so, it's an orphaned caption that should
      // move to the new page with us. Since we can't undo drawn text, we instead
      // ensure captions preceding illustrations always have enough room for both.
      // (The actual prevention happens in the caption rendering with look-ahead below)

      // Embed illustration
      let img
      try {
        img = await doc.embedJpg(el.imageData)
      } catch {
        continue
      }

      // Scale images to use available space generously
      // Full-page images (letters/diagrams): up to 95% width, 80% height
      // Regular illustrations: up to 95% width, 65% height (was 85%/50% — too small)
      const isFullPageImage = img.width > 800 && img.height > 1000
      const maxW = textWidth * 0.95
      const maxH = textHeight * (isFullPageImage ? 0.80 : 0.65)
      const baseScale = Math.min(maxW / img.width, maxH / img.height)
      let drawW = img.width * baseScale
      let drawH = img.height * baseScale
      let totalH = drawH + cfg.illustrationPadding * 2

      // Minimum 65% of base size — keep images reasonably large
      // If it doesn't fit at 65%, start a new page instead
      const minDrawW = drawW * 0.65
      const minDrawH = drawH * 0.65

      const remaining = curY - safeMarginBottom
      if (totalH > remaining) {
        const spaceForImg = remaining - cfg.illustrationPadding * 2
        const fitScale = Math.min(maxW / img.width, spaceForImg / img.height)
        const fitW = img.width * fitScale
        const fitH = img.height * fitScale
        // Only shrink to fit if the result is >= 70% of the original size
        if (fitW >= minDrawW && fitH >= minDrawH && spaceForImg > 0) {
          drawW = fitW
          drawH = fitH
          totalH = drawH + cfg.illustrationPadding * 2
        } else {
          // Too small — start a new page to show image at full size
          newPage()
        }
      }

      // Check if this image should be placed at the BOTTOM of the page
      // (when the next element is a divider/new topic, put image at bottom
      // so blank space is above the image, not below)
      const nextEl = elIdx + 1 < elements.length ? elements[elIdx + 1] : null
      const nextIsDividerOrEnd = !nextEl || nextEl.type === 'divider'
      const spaceAfterImage = (curY - cfg.illustrationPadding - drawH) - safeMarginBottom

      if (nextIsDividerOrEnd && spaceAfterImage > textHeight * 0.15) {
        // Place image at bottom of page
        const imgBottomY = cfg.marginBottom + cfg.illustrationPadding
        const imgX = cfg.marginLeft + (textWidth - drawW) / 2
        pdfPage.drawImage(img, {
          x: imgX,
          y: imgBottomY,
          width: drawW,
          height: drawH,
        })

        // If there's deferred text, draw it just above the bottom-placed image
        if (deferredText) {
          const dt = deferredText
          const dtTotalH = dt.lines.length * dt.lh + dt.spacingAfter
          let dtY = imgBottomY + drawH + cfg.illustrationPadding + dtTotalH
          for (let li = 0; li < dt.lines.length; li++) {
            const ln = dt.lines[li]
            let x = cfg.marginLeft
            if (dt.centered) {
              const lineW = bidiLineWidth(ln, dt.fontSize, dt.font, dt.hebFont)
              x = cfg.marginLeft + (textWidth - lineW) / 2
            } else if (li === 0 && dt.hasIndent) {
              x += cfg.firstLineIndent
            }
            drawBidiLine(pdfPage, ln, x, dtY - dt.fontSize, dt.fontSize, dt.font, dt.hebFont, rgb(...dt.color), cfg.pageWidth - cfg.marginRight)
            dtY -= dt.lh
          }
          deferredText = null
        }

        curY = safeMarginBottom // page is full after bottom-placed image
      } else {
        // Normal placement: image flows top-down
        // If there's deferred text, draw it first in normal flow
        if (deferredText) {
          const dt = deferredText
          for (let li = 0; li < dt.lines.length; li++) {
            if (curY - dt.lh < safeMarginBottom) newPage()
            const ln = dt.lines[li]
            let x = cfg.marginLeft
            if (dt.centered) {
              const lineW = bidiLineWidth(ln, dt.fontSize, dt.font, dt.hebFont)
              x = cfg.marginLeft + (textWidth - lineW) / 2
            } else if (li === 0 && dt.hasIndent) {
              x += cfg.firstLineIndent
            }
            drawBidiLine(pdfPage, ln, x, curY - dt.fontSize, dt.fontSize, dt.font, dt.hebFont, rgb(...dt.color), cfg.pageWidth - cfg.marginRight)
            curY -= dt.lh
          }
          curY -= dt.spacingAfter
          deferredText = null
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
      }
      contentRenderedOnPage = true

    } else if (el.type === 'caption') {
      // Render as smaller italic-style caption text (centered)
      const text = sanitizeForPdf(el.text || '', true)
      if (!text) continue

      const captionSize = cfg.bodyFontSize * 0.85
      const captionLh = captionSize * cfg.lineHeight
      const lines = wrapTextBidi(text, fonts.body, fonts.hebrew, captionSize, textWidth * 0.85)
      const captionH = lines.length * captionLh

      // Look-ahead: if next element is an illustration, keep caption + image together
      // If both don't fit on current page, start a new page NOW (before the caption)
      const nextEl2 = elIdx + 1 < elements.length ? elements[elIdx + 1] : null
      if (nextEl2 && nextEl2.type === 'illustration') {
        // Estimate image height (at least 200pt for a typical illustration)
        const estimatedImgH = textHeight * 0.3 // conservative estimate
        if (curY - captionH - estimatedImgH < safeMarginBottom) {
          newPage()
        }
      }

      if (curY - captionH < safeMarginBottom && contentRenderedOnPage) {
        newPage()
      }

      for (const line of lines) {
        const lineW = bidiLineWidth(line, captionSize, fonts.body, fonts.hebrew)
        const x = cfg.marginLeft + (textWidth - lineW) / 2
        drawBidiLine(pdfPage, line, x, curY - captionSize, captionSize, fonts.body, fonts.hebrew, rgb(0.35, 0.33, 0.30))
        curY -= captionLh
      }
      curY -= cfg.paragraphSpacing * 0.5
      contentRenderedOnPage = true

    } else if (el.type === 'table' && el.rows) {
      // Render table with aligned columns and text wrapping
      // Reverse column order (Hebrew tables are RTL, English should be LTR)
      const rows = el.rows.map(row => [...row].reverse())
      if (rows.length === 0) continue

      // Store first row as header for carryover across pages
      const headerRow = rows[0]

      const tableFontSize = cfg.bodyFontSize * 0.88
      const tableLh = tableFontSize * cfg.lineHeight
      const maxCols = Math.max(...rows.map(r => r.length))

      // Calculate column widths proportionally based on content
      const colMaxWidths = new Array(maxCols).fill(0)
      for (const row of rows) {
        for (let c = 0; c < row.length; c++) {
          const w = bidiLineWidth(row[c] || '', tableFontSize, fonts.body, fonts.hebrew)
          colMaxWidths[c] = Math.max(colMaxWidths[c] || 0, w)
        }
      }
      const totalContentW = colMaxWidths.reduce((s, w) => s + w, 0) || 1
      const colWidths = colMaxWidths.map(w => Math.max(
        textWidth * 0.1, // minimum 10% per column
        (w / totalContentW) * textWidth * 0.92 // proportional, with padding
      ))
      // Normalize to fit textWidth
      const colTotal = colWidths.reduce((s, w) => s + w, 0)
      const colScale = textWidth / colTotal
      const finalColWidths = colWidths.map(w => w * colScale)

      curY -= 6 // gap above table

      // Top line
      pdfPage.drawLine({
        start: { x: cfg.marginLeft, y: curY },
        end: { x: cfg.marginLeft + textWidth, y: curY },
        thickness: 0.5, color: rgb(0.62, 0.58, 0.52),
      })
      curY -= 3

      for (let rIdx = 0; rIdx < rows.length; rIdx++) {
        const row = rows[rIdx]

        // Calculate row height (max wrapped lines across columns)
        let maxLinesInRow = 1
        const cellWrapped: string[][] = []
        for (let c = 0; c < maxCols; c++) {
          const cellText = cleanTranslationText(sanitizeForPdf(row[c] || '', true))
          const cellW = finalColWidths[c] - 8 // padding
          const wrapped = cellText ? wrapTextBidi(cellText, fonts.body, fonts.hebrew, tableFontSize, cellW) : ['']
          cellWrapped.push(wrapped)
          maxLinesInRow = Math.max(maxLinesInRow, wrapped.length)
        }

        const rowH = maxLinesInRow * tableLh + 4

        if (curY - rowH < safeMarginBottom) {
          newPage()
          // Redraw top line on new page
          pdfPage.drawLine({
            start: { x: cfg.marginLeft, y: curY },
            end: { x: cfg.marginLeft + textWidth, y: curY },
            thickness: 0.5, color: rgb(0.62, 0.58, 0.52),
          })
          curY -= 3

          // Carry over header row on new page (if not the header row itself)
          if (rIdx > 0 && headerRow) {
            const hdrWrapped: string[][] = []
            let hdrMaxLines = 1
            for (let c = 0; c < maxCols; c++) {
              const ct = cleanTranslationText(sanitizeForPdf(headerRow[c] || '', true))
              const cw = finalColWidths[c] - 8
              const wr = ct ? wrapTextBidi(ct, fonts.bold, fonts.hebrewBold, tableFontSize, cw) : ['']
              hdrWrapped.push(wr)
              hdrMaxLines = Math.max(hdrMaxLines, wr.length)
            }
            const hdrH = hdrMaxLines * tableLh + 4
            let hCellX = cfg.marginLeft
            for (let c = 0; c < maxCols; c++) {
              const hLines = hdrWrapped[c] || ['']
              for (let li = 0; li < hLines.length; li++) {
                drawBidiLine(pdfPage, hLines[li], hCellX + 4, curY - tableFontSize - li * tableLh, tableFontSize, fonts.bold, fonts.hebrewBold, rgb(...cfg.headerColor))
              }
              if (c < maxCols - 1) {
                pdfPage.drawLine({ start: { x: hCellX + finalColWidths[c], y: curY }, end: { x: hCellX + finalColWidths[c], y: curY - hdrH + 2 }, thickness: 0.3, color: rgb(0.82, 0.78, 0.73) })
              }
              hCellX += finalColWidths[c]
            }
            curY -= hdrH
            // Header separator line
            pdfPage.drawLine({ start: { x: cfg.marginLeft, y: curY + 1 }, end: { x: cfg.marginLeft + textWidth, y: curY + 1 }, thickness: 0.4, color: rgb(0.72, 0.68, 0.62) })
          }
        }

        // Draw each cell with column dividers
        let cellX = cfg.marginLeft
        for (let c = 0; c < maxCols; c++) {
          const lines = cellWrapped[c] || ['']
          for (let li = 0; li < lines.length; li++) {
            drawBidiLine(
              pdfPage, lines[li],
              cellX + 4, curY - tableFontSize - li * tableLh,
              tableFontSize, fonts.body, fonts.hebrew, rgb(...cfg.textColor)
            )
          }
          // Draw vertical column divider line between columns
          if (c < maxCols - 1) {
            const divX = cellX + finalColWidths[c]
            pdfPage.drawLine({
              start: { x: divX, y: curY },
              end: { x: divX, y: curY - rowH + 2 },
              thickness: 0.3, color: rgb(0.82, 0.78, 0.73),
            })
          }
          cellX += finalColWidths[c]
        }
        curY -= rowH

        // Row separator
        if (rIdx < rows.length - 1) {
          pdfPage.drawLine({
            start: { x: cfg.marginLeft, y: curY + 1 },
            end: { x: cfg.marginLeft + textWidth, y: curY + 1 },
            thickness: 0.2, color: rgb(0.85, 0.82, 0.78),
          })
        }
      }

      // Bottom line
      pdfPage.drawLine({
        start: { x: cfg.marginLeft, y: curY },
        end: { x: cfg.marginLeft + textWidth, y: curY },
        thickness: 0.5, color: rgb(0.62, 0.58, 0.52),
      })
      curY -= cfg.paragraphSpacing
      contentRenderedOnPage = true

    } else if (el.type === 'header') {
      const text = sanitizeForPdf((el.text || '').replace(/\*\*/g, ''), true)
      if (!text) continue
      // Filter standalone numbers that slipped through as headers (e.g., "19")
      if (/^\d{1,3}$/.test(text.trim())) continue

      const fontSize = cfg.headerFontSize
      const font = fonts.header
      const hebFont = fonts.hebrewBold
      const lh = fontSize * cfg.lineHeight

      curY -= cfg.headerSpacingAbove

      const lines = wrapTextBidi(text, font, hebFont, fontSize, textWidth)
      const blockH = lines.length * lh

      if (curY - blockH < safeMarginBottom && contentRenderedOnPage) {
        // Only start a new page for the header if we already have content on this page.
        // If the page is empty, start rendering here — per-line breaks will handle overflow.
        newPage()
      } else if (curY - blockH < safeMarginBottom + 120 && contentRenderedOnPage) {
        // Header fits but leaves <120pt for content below — orphan header.
        // Push to next page so the header has room for content below it.
        newPage()
      }

      // Track ALL headers with metadata — filtering is done post-rendering
      // Use minimal cleaning here (just strip Hebrew + punctuation), save full cleaning for display
      const rawTocTitle = text.replace(/[\u0590-\u05FF\u200E\u200F]+/g, '').replace(/\s*[—\-]\s*/g, ' ').replace(/\s+/g, ' ').trim()
      const basicTitle = rawTocTitle
        .replace(/^[\s'"`,.\-:;*#()\[\]]+/, '').replace(/[\s'"`,.\-:;*#()\[\]]+$/, '')
        .replace(/^\d+(?:[.\)]?\s*)?(?=[A-Z])/, '')
        .replace(/^Page\s+\d+\s*/i, '')
        .replace(/\*\*/g, '')
        .replace(/\s+/g, ' ').trim()
      const isPerekHeader = /perek|chapter/i.test(basicTitle)
      if (basicTitle.length >= 10) {
        tocEntries.push({
          title: basicTitle,
          pageNum: startPageNum + pageCount - 1,
          isPerek: isPerekHeader,
          afterDivider: lastWasDivider,
        })
      }
      lastWasDivider = false

      // Look-ahead: if this header is short and followed by a bottom-placed illustration,
      // defer rendering so the header draws just above the image instead of stranded high up.
      {
        let hdrIllFollows = false
        let hdrIllBottomPlace = false
        for (let look = 1; look <= 3 && elIdx + look < elements.length; look++) {
          const upcoming = elements[elIdx + look]
          if (upcoming.type === 'illustration') {
            hdrIllFollows = true
            const afterIll = elIdx + look + 1 < elements.length ? elements[elIdx + look + 1] : null
            hdrIllBottomPlace = !afterIll || afterIll.type === 'divider'
            break
          }
          if (upcoming.type === 'divider') continue
          break
        }
        if (hdrIllFollows && lines.length <= 3) {
          const hdrH = blockH + cfg.headerSpacingAbove + cfg.headerSpacingBelow
          const estimatedImgH = textHeight * 0.3
          const spaceAfterHdrAndImg = curY - hdrH - estimatedImgH
          // Defer if: (a) image would be bottom-placed with gap, OR (b) image won't fit at all
          const wouldBottomPlaceWithGap = hdrIllBottomPlace && spaceAfterHdrAndImg > safeMarginBottom + textHeight * 0.10
          const wouldOverflow = spaceAfterHdrAndImg < safeMarginBottom && contentRenderedOnPage
          if (wouldBottomPlaceWithGap || wouldOverflow) {
            deferredText = {
              lines,
              font,
              hebFont,
              fontSize,
              lh,
              isAllBold: true,
              hasIndent: false,
              centered: true,
              color: cfg.headerColor as [number, number, number],
              spacingAfter: cfg.headerSpacingBelow,
            }
            continue // skip normal rendering — will be drawn with the image
          }
        }
      }

      for (const line of lines) {
        // Per-line page break check (headers can be long on title pages)
        if (curY - lh < safeMarginBottom) {
          newPage()
        }
        const lineW = bidiLineWidth(line, fontSize, font, hebFont)
        const x = cfg.marginLeft + (textWidth - lineW) / 2 // centered
        drawBidiLine(pdfPage, line, x, curY - fontSize, fontSize, font, hebFont, rgb(...cfg.headerColor), cfg.pageWidth - cfg.marginRight)
        curY -= lh
      }

      curY -= cfg.headerSpacingBelow
      contentRenderedOnPage = true

    } else if (el.type === 'body') {
      const rawText = el.text || ''
      if (!rawText.trim()) continue

      // Check if next element is a divider — if so, this is last content before topic break
      const nextIsDivider = elIdx + 1 < elements.length && elements[elIdx + 1].type === 'divider'

      // Look-ahead: keep short descriptive body text with the following illustration.
      // If this body is short (<3 wrapped lines) and followed by an illustration
      // (directly or after a divider), ensure both fit on the same page.
      // Also: if the illustration will be bottom-placed (next after it is divider/end),
      // defer rendering this text so it can be drawn just above the image.
      {
        let illustrationFollows = false
        let illustrationWillBottomPlace = false
        for (let look = 1; look <= 3 && elIdx + look < elements.length; look++) {
          const upcoming = elements[elIdx + look]
          if (upcoming.type === 'illustration') {
            illustrationFollows = true
            // Check if the element AFTER the illustration is divider/end
            const afterIll = elIdx + look + 1 < elements.length ? elements[elIdx + look + 1] : null
            illustrationWillBottomPlace = !afterIll || afterIll.type === 'divider'
            break
          }
          if (upcoming.type === 'divider') continue // skip dividers
          break // any other element = stop looking
        }
        if (illustrationFollows) {
          const testLines = wrapTextBidi(
            sanitizeForPdf(rawText.replace(/\*\*([\s\S]*?)\*\*/g, '$1'), true),
            fonts.body, fonts.hebrew, cfg.bodyFontSize, textWidth - cfg.firstLineIndent,
          )
          if (testLines.length <= 3) {
            const bodyH = testLines.length * cfg.bodyFontSize * cfg.lineHeight + cfg.paragraphSpacing
            const estimatedImgH = textHeight * 0.3

            const spaceForBoth = curY - bodyH - estimatedImgH
            const wouldBottomPlace = illustrationWillBottomPlace && spaceForBoth > safeMarginBottom + textHeight * 0.10
            const wouldOverflow = spaceForBoth < safeMarginBottom && contentRenderedOnPage
            if (wouldBottomPlace || wouldOverflow) {
              // Defer: image will be bottom-placed with gap, or won't fit at all
              const isAllBold = rawText.startsWith('**') && rawText.endsWith('**')
              const cleanBody = sanitizeForPdf(
                rawText.replace(/\*\*([\s\S]*?)\*\*/g, '$1').replace(/^#+\s+/gm, '').replace(/`([^`]+)`/g, '$1'),
                true,
              )
              const bFont = isAllBold ? fonts.bold : fonts.body
              const bHebFont = isAllBold ? fonts.hebrewBold : fonts.hebrew
              const bFontSize = isAllBold ? cfg.subheaderFontSize : cfg.bodyFontSize
              const bLh = bFontSize * cfg.lineHeight
              let allLines: string[]
              if (!isAllBold && cfg.firstLineIndent > 0) {
                const first = wrapTextBidi(cleanBody, bFont, bHebFont, bFontSize, textWidth - cfg.firstLineIndent)
                allLines = [first[0] || '']
                if (first.length > 1) {
                  allLines.push(...wrapTextBidi(first.slice(1).join(' '), bFont, bHebFont, bFontSize, textWidth))
                }
              } else {
                allLines = wrapTextBidi(cleanBody, bFont, bHebFont, bFontSize, textWidth)
              }
              deferredText = {
                lines: allLines,
                font: bFont,
                hebFont: bHebFont,
                fontSize: bFontSize,
                lh: bLh,
                isAllBold,
                hasIndent: !isAllBold && cfg.firstLineIndent > 0,
                centered: isAllBold,
                color: cfg.textColor as [number, number, number],
                spacingAfter: cfg.paragraphSpacing,
              }
              continue // skip normal rendering — deferred text will be drawn above the image
            }

            if (curY - bodyH - estimatedImgH < safeMarginBottom && contentRenderedOnPage) {
              newPage()
            }
          }
        }
      }

      // Split into paragraphs by double newlines
      let paragraphs = rawText.split(/\n\s*\n/).map(p => p.replace(/\n/g, ' ').trim()).filter(Boolean)

      // Break up giant paragraphs (>400 words) at sentence boundaries
      const MAX_PARA_WORDS = 400
      const splitParagraphs: string[] = []
      for (const para of paragraphs) {
        const wordCount = para.split(/\s+/).length
        if (wordCount > MAX_PARA_WORDS) {
          // Split at sentence boundaries: period/exclamation/question/closing paren
          // followed by whitespace and a capital letter or Hebrew char
          const sentences = para.split(/(?<=[.!?)\u202c])\s+(?=[A-Z\u0590-\u05FF"(])/)
          if (sentences.length <= 1) {
            // Fallback: split by periods
            const fallbackSentences = para.split(/\.\s+/)
            let chunk = ''
            let chunkWords = 0
            for (let si = 0; si < fallbackSentences.length; si++) {
              const sent = fallbackSentences[si] + (si < fallbackSentences.length - 1 ? '.' : '')
              const sentWords = sent.split(/\s+/).length
              if (chunkWords + sentWords > MAX_PARA_WORDS && chunkWords > 0) {
                splitParagraphs.push(chunk.trim())
                chunk = sent
                chunkWords = sentWords
              } else {
                chunk += (chunk ? ' ' : '') + sent
                chunkWords += sentWords
              }
            }
            if (chunk.trim()) splitParagraphs.push(chunk.trim())
          } else {
            let chunk = ''
            let chunkWords = 0
            for (const sent of sentences) {
              const sentWords = sent.split(/\s+/).length
              if (chunkWords + sentWords > MAX_PARA_WORDS && chunkWords > 0) {
                splitParagraphs.push(chunk.trim())
                chunk = sent
                chunkWords = sentWords
              } else {
                chunk += (chunk ? ' ' : '') + sent
                chunkWords += sentWords
              }
            }
            if (chunk.trim()) splitParagraphs.push(chunk.trim())
          }
        } else {
          splitParagraphs.push(para)
        }
      }
      paragraphs = splitParagraphs

      for (let pIdx = 0; pIdx < paragraphs.length; pIdx++) {
        const para = paragraphs[pIdx]
        const isLastPara = pIdx === paragraphs.length - 1
        const isAllBold = para.startsWith('**') && para.endsWith('**')
        const cleanText = deduplicatePhrases(sanitizeForPdf(
          para.replace(/\*\*([\s\S]*?)\*\*/g, '$1').replace(/^#+\s+/gm, '').replace(/`([^`]+)`/g, '$1'),
          true // keep Hebrew
        ))
        if (!cleanText) continue

        const font = isAllBold ? fonts.bold : fonts.body
        const hebFont = isAllBold ? fonts.hebrewBold : fonts.hebrew
        let fontSize = isAllBold ? cfg.subheaderFontSize : cfg.bodyFontSize

        // Orphan prevention: if this is the last paragraph before a topic break
        // and it would create orphan lines (1-5 lines spilling to next page),
        // try progressively squeezing font (5%, 8%, 10%, 12%) to keep them on current page
        if (isLastPara && nextIsDivider) {
          const lhTest = fontSize * cfg.lineHeight
          const testLines = wrapTextBidi(cleanText, font, hebFont, fontSize, textWidth - (isAllBold ? 0 : cfg.firstLineIndent))
          const remaining = curY - safeMarginBottom
          const linesOnCurrentPage = Math.floor(remaining / lhTest)
          const spillOver = testLines.length - linesOnCurrentPage

          if (spillOver > 0 && spillOver <= 5) {
            // Try progressively larger squeezes
            for (const squeezeFactor of [0.95, 0.92, 0.90, 0.88]) {
              const squeezedSize = fontSize * squeezeFactor
              const squeezedLh = squeezedSize * cfg.lineHeight
              const squeezedLines = wrapTextBidi(cleanText, font, hebFont, squeezedSize, textWidth - (isAllBold ? 0 : cfg.firstLineIndent))
              const squeezedFit = Math.floor(remaining / squeezedLh)
              if (squeezedFit >= squeezedLines.length) {
                fontSize = squeezedSize
                break
              }
            }
          }
        }

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
        // Also handle orphan prevention at page-break boundaries
        // Use marginBottom + 8 to ensure text doesn't encroach on page number area

        for (let i = 0; i < allLines.length; i++) {
          if (curY - lh < safeMarginBottom) {
            // About to start a new page — check for orphan situation
            // If this is the last body element before a divider, and only 1-5 lines remain,
            // try squeezing the remaining lines to fit on the current page
            const remainingLines = allLines.length - i
            if (isLastPara && nextIsDivider && remainingLines > 0 && remainingLines <= 5) {
              const spaceLeft = curY - safeMarginBottom
              // Try progressively larger squeezes for the remaining lines
              let squeezed = false
              for (const factor of [0.92, 0.88, 0.85]) {
                const sqH = remainingLines * (lh * factor)
                if (sqH <= spaceLeft) {
                  // Re-render remaining lines with squeezed spacing
                  const sqFontSize = fontSize * factor
                  const sqLhActual = sqFontSize * cfg.lineHeight
                  for (let j = i; j < allLines.length; j++) {
                    const ln = allLines[j]
                    let x = cfg.marginLeft
                    if (isAllBold) {
                      const lineW = bidiLineWidth(ln, sqFontSize, font, hebFont)
                      x = cfg.marginLeft + (textWidth - lineW) / 2
                    }
                    drawBidiLine(pdfPage, ln, x, curY - sqFontSize, sqFontSize, font, hebFont, rgb(...cfg.textColor))
                    curY -= sqLhActual
                  }
                  squeezed = true
                  break
                }
              }
              if (squeezed) break // all remaining lines were squeezed onto current page
            }
            newPage()
          }

          const line = allLines[i]
          let x = cfg.marginLeft
          const isLastLine = i === allLines.length - 1

          if (isAllBold) {
            const lineW = bidiLineWidth(line, fontSize, font, hebFont)
            x = cfg.marginLeft + (textWidth - lineW) / 2
            drawBidiLine(pdfPage, line, x, curY - fontSize, fontSize, font, hebFont, rgb(...cfg.textColor), cfg.pageWidth - cfg.marginRight)
          } else if (i === 0 && cfg.firstLineIndent > 0) {
            x += cfg.firstLineIndent
            // Justify first line within its narrower width (textWidth - indent)
            if (!isLastLine && allLines.length > 2) {
              drawJustifiedBidiLine(pdfPage, line, x, curY - fontSize, fontSize, font, hebFont, rgb(...cfg.textColor), textWidth - cfg.firstLineIndent, cfg.pageWidth - cfg.marginRight)
            } else {
              drawBidiLine(pdfPage, line, x, curY - fontSize, fontSize, font, hebFont, rgb(...cfg.textColor), cfg.pageWidth - cfg.marginRight)
            }
          } else if (!isLastLine && allLines.length > 2) {
            // Justify non-last lines of multi-line paragraphs
            drawJustifiedBidiLine(pdfPage, line, x, curY - fontSize, fontSize, font, hebFont, rgb(...cfg.textColor), textWidth, cfg.pageWidth - cfg.marginRight)
          } else {
            drawBidiLine(pdfPage, line, x, curY - fontSize, fontSize, font, hebFont, rgb(...cfg.textColor), cfg.pageWidth - cfg.marginRight)
          }
          curY -= lh
        }

        curY -= cfg.paragraphSpacing
        contentRenderedOnPage = true
      }
    }
  }

  return { pageCount, tocEntries }
}

// ─── Shared TOC Line Builder ─────────────────────────────────────────────────

/** Meaningful topic descriptions for Perek/Pasuk entries */
const topicDescriptions: Record<string, string> = {
  '40:1': 'The Vision of the Third Beis HaMikdash',
  '40:2': 'Visions of Eretz Yisrael',
  '40:3': 'Arrival at Har HaBayis \u2014 The Measuring Angel',
  '40:5': 'The Wall of Har HaBayis',
  '40:6': 'The Eastern Gate and the Soreg',
  '40:7': 'The Chambers of the Gate',
  '40:8': 'The Ulam of the Gate',
  '40:12': 'The Borders of the Chambers',
  '40:13': 'The Width of the Gate',
  '40:14': 'The Pillars and Doorposts',
  '40:16': 'The Narrow Windows and Palm Decorations',
  '40:17': 'The Outer Courtyard and its Chambers',
  '40:19': 'The Width of the Courtyard',
  '40:20': 'The Northern Gate',
  '40:28': 'The Inner Courtyard \u2014 Southern Gate',
  '40:29': 'The Inner Gate Chambers',
  '40:31': 'The Vestibule of the Inner Azarah',
  '40:36': 'Overview of the Beis HaMikdash Structure',
  '40:39': 'The Tables for Korbanos',
  '40:42': 'The Slaughter Tables and Hooks',
  '40:44': 'The Chambers of the Singers',
  '40:45': 'The Chamber of the Kohanim',
  '40:47': "The Inner Courtyard \u2014 The Mizbei'ach",
  '40:48': 'The Ulam of the Heichal',
  '40:49': 'The Steps to the Ulam',
  '41:1': 'The Heichal \u2014 The Pillars',
  '41:3': 'The Kodesh HaKodashim',
  '41:4': 'The Aron and the Kapores',
  '41:5': "The Side Chambers (Ta'im)",
  '41:6': 'The Three Stories of Chambers',
  '41:7': 'The Winding Staircases',
  '41:8': 'The Foundation Platform',
  '41:9': 'The Outer Wall of the Chambers',
  '41:12': 'The Building Behind the Heichal (Beis HaChalifos)',
  '41:13': 'Total Measurements of the House',
  '41:15': 'The Interior Galleries and Decorations',
  '41:16': 'The Doorframes, Windows, and Galleries',
  '41:17': 'The Keruvim and Palm Tree Carvings',
  '41:22': "The Golden Mizbei'ach (Mizbei'ach HaZahav)",
  '41:23': 'The Doors of the Heichal and Kodesh HaKodashim',
  '41:25': 'The Wooden Canopy of the Ulam',
  '41:26': 'The Windows and Palm Trees of the Side Chambers',
  '42:1': 'The Upper Chambers in the North',
  '42:3': 'The Galleries Opposite the Courtyard',
  '42:4': 'The Walkway Before the Chambers',
  '42:5': 'The Upper Chambers Are Shorter',
  '42:6': 'The Pillars of the Chambers',
  '42:7': 'The Outer Wall',
  '42:9': 'The Lower Chambers',
  '42:10': 'The Southern Chambers',
  '42:11': 'The Doorways of the Chambers',
  '42:12': 'The Entrances and Holy Garments',
  '42:13': 'Eating Kodshei Kodashim',
  '42:15': 'Measuring the Outer Perimeter',
}

interface TocLineItem {
  type: 'section' | 'entry'
  text: string
  pageNum?: number
}

/** Build structured TOC lines from raw TocEntry[] using the smart selection logic.
 *  Shared between HTML and pdf-lib renderers. */
function buildTocLines(entries: TocEntry[]): TocLineItem[] {
  // Step 1: Exclude noise
  const cleanEntries = entries.filter(e => {
    if (isTocExcluded(e.title)) return false
    const displayForm = cleanTocTitle(e.title)
    if (isTocExcluded(displayForm)) return false
    return true
  })

  // Step 2: Deduplicate
  const seenTitles = new Set<string>()
  const seenPrefixes = new Set<string>()
  const dedupedToc: TocEntry[] = []
  for (const entry of cleanEntries) {
    const key = entry.title.toLowerCase().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, ' ').trim()
    if (seenTitles.has(key)) continue
    const normKey = key.replace(/\b(a|an|the)\b/g, '').replace(/\s+/g, ' ').trim()
    const prefix = normKey.substring(0, 35)
    if (seenPrefixes.has(prefix)) continue
    seenTitles.add(key)
    seenPrefixes.add(prefix)
    dedupedToc.push(entry)
  }

  // Step 3: Classify and select
  const pasukRegex = /pasuk(?:im)?\s+(\d+)/i
  const perekRegex = /(?:yechezkel\s+)?(?:chapter|perek)\s+(\d+)/i
  const tocItems: TocEntry[] = []
  const seenPereks = new Set<string>()
  const seenPasukPerPerek: Record<string, number> = {}

  let currentPerek = ''
  for (const entry of dedupedToc) {
    const perekMatch = entry.title.match(perekRegex)
    if (perekMatch) currentPerek = perekMatch[1]
    ;(entry as TocEntry & { _perek?: string })._perek = currentPerek
  }

  currentPerek = ''
  for (const entry of dedupedToc) {
    const perekMatch = entry.title.match(perekRegex)
    const pasukMatch = entry.title.match(pasukRegex)
    const lower = entry.title.toLowerCase()
    const entryPerek = (entry as TocEntry & { _perek?: string })._perek || ''

    if (/introduction|foreword|preface|overview|summary|history|about the book/i.test(lower)) {
      tocItems.push(entry); continue
    }
    if (perekMatch && !pasukMatch) {
      tocItems.push(entry)
      if (!seenPereks.has(perekMatch[1])) seenPereks.add(perekMatch[1])
      currentPerek = perekMatch[1]; continue
    }
    if (pasukMatch) {
      const pk = entryPerek || currentPerek || 'unknown'
      const pasukKey = `${pk}:${pasukMatch[1]}`
      if (!seenPasukPerPerek[pasukKey]) {
        seenPasukPerPerek[pasukKey] = 1
        tocItems.push(entry)
      }
      continue
    }
    const displayCheck = cleanTocTitle(entry.title)
    const garbledDigits = (displayCheck.match(/\d/g) || []).length
    const expectedDigits = (displayCheck.match(/\b\d+\b/g) || []).length * 2
    const isGarbled = garbledDigits > expectedDigits + 2 || /\d{2}[A-Za-z]/.test(displayCheck)
    const isGeneric = /^you shall|^shall you|^seek|^his dwelling|^their chamber/i.test(displayCheck)
    if (entry.afterDivider && entry.title.length >= 20 && !isGarbled && !isGeneric) {
      tocItems.push(entry); continue
    }
    if (isTocWorthyHeader(entry.title)) {
      tocItems.push(entry)
    }
  }

  // Step 4: Trim if too many
  let finalTocItems = tocItems
  if (finalTocItems.length > 60) {
    const essential = finalTocItems.filter(e =>
      /introduction|foreword|perek|chapter/i.test(e.title) || e.afterDivider
    )
    finalTocItems = essential.length >= 20 ? essential : finalTocItems.slice(0, 60)
  }

  // Step 5: Build structured TOC lines
  const tocLines: TocLineItem[] = []
  let lastPerek = ''

  tocLines.push({ type: 'entry', text: 'Haskamos (Approval Letters)', pageNum: 2 })

  for (const entry of finalTocItems) {
    const perekMatch = entry.title.match(perekRegex)
    if (perekMatch) {
      const perekLabel = `YECHEZKEL PEREK ${perekMatch[1]}`
      if (perekLabel !== lastPerek) {
        lastPerek = perekLabel
        tocLines.push({ type: 'section', text: perekLabel })
      }
    }
    let displayTitle = entry.title
    if (perekMatch && lastPerek) {
      const stripped = displayTitle.replace(perekRegex, '').replace(/^\s*[,:\-\u2014.]+\s*/, '').trim()
      if (stripped.length < 10) continue
      displayTitle = stripped
    }
    let cleanDisplay = cleanTocTitle(displayTitle)
    if (cleanDisplay.length < 10) {
      let fallback = cleanTocTitle(entry.title)
      if (perekMatch) {
        fallback = fallback.replace(perekRegex, '').replace(/^\s*[,:\-\u2014.]+\s*/, '').trim()
      }
      cleanDisplay = fallback.length >= 8 ? fallback : cleanDisplay
    }
    const pasukForDesc = cleanDisplay.match(/^P[ae]suk(?:im)?\s+(\d+)(?:[\s\-]+(\d+))?/i)
    if (pasukForDesc && lastPerek) {
      const pasukNum = pasukForDesc[1]
      const perekNum = lastPerek.replace('YECHEZKEL PEREK ', '')
      const descKey = `${perekNum}:${pasukNum}`
      const description = topicDescriptions[descKey]
      if (description) {
        cleanDisplay = `Pasuk${pasukForDesc[2] ? 'im ' + pasukNum + '-' + pasukForDesc[2] : ' ' + pasukNum}: ${description}`
      }
    }
    const isPasukEntry = /^pasuk|^pesukim/i.test(cleanDisplay)
    const minDisplayLen = isPasukEntry ? 7 : 12
    if (cleanDisplay.length >= minDisplayLen) {
      tocLines.push({ type: 'entry', text: cleanDisplay, pageNum: entry.pageNum })
    }
  }

  return tocLines
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

    // Renderer selection: ?renderer=pdflib for legacy, default is html (Playwright)
    const renderer = url.searchParams.get('renderer') || 'html'

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

    // ── Collect ALL elements from ALL pages into one continuous flow ──
    // This is shared between both renderers (pdf-lib and Playwright HTML)
    // This prevents half-empty pages between sections
    const allElements: ContentElement[] = []
    let isFirstSection = true

    const hebrewTocTitles: string[] = [] // topics from Hebrew TOC pages

    for (const page of pages) {
      const pageElements: ContentElement[] = []
      const regions = page.regions || []
      const translation = page.translation

      // Extract TOC entries from Hebrew TOC pages before skipping them
      if (isTocPage(regions)) {
        // Save the translated topic names from the Hebrew TOC
        for (const r of regions) {
          if (!r.translatedText?.trim()) continue
          const text = cleanTranslationText(r.translatedText).replace(/[\u0590-\u05FF\u200E]+/g, '').replace(/\s*[—\-]\s*/g, ' ').trim()
          // Extract topic titles (not page numbers, not section labels)
          if (text.length > 15 && text.length < 120 && !/^\d/.test(text) && text.split(/\s+/).length >= 3) {
            hebrewTocTitles.push(text)
          }
        }
        continue
      }

      // Skip the half-title page (usually source page 2) — it just repeats the book title
      // which we already show on the English title page
      if (page.pageNumber === 2 && regions.length <= 2) {
        const allText = regions.map(r => (r.translatedText || '')).join(' ')
        if (allText.length < 100) continue // skip half-title page (just book title)
      }

      if (regions.length > 0 && regions.some(r => r.translatedText?.trim())) {
        // Check if this page has explicit diagram references — use lower filter threshold
        const allRegionText = regions.map(r => (r.translatedText || '')).join(' ')
        const explicitDiagramRef = /\[THIS IS DIAGRAM|Drawing \d|Diagram \d|Sketch of|Layout of|שרטוט|ציור \d/i.test(allRegionText)

        // Also detect pages with scattered measurement labels (amos/amah with numbers)
        const hasMeasurementLabels = /\d+\s*amos?\b|\bamos?\s*\d|\d+\s*amah?\b|\bamah?\s*\d|\d+\s*אמ[הות]/i.test(allRegionText)

        // Detect pages with large illustration gaps (>20% of page height) AND many short regions
        const sortedRegs = [...regions].sort((a, b) => a.origY - b.origY)
        let hasLargeGap = false
        for (let ri = 0; ri < sortedRegs.length - 1; ri++) {
          const gapSize = sortedRegs[ri + 1].origY - (sortedRegs[ri].origY + sortedRegs[ri].origHeight)
          if (gapSize > 20) { hasLargeGap = true; break }
        }
        // First region far from top or last region far from bottom also counts
        if (!hasLargeGap && sortedRegs.length > 0) {
          if (sortedRegs[0].origY > 25) hasLargeGap = true
          const lastBottom = sortedRegs[sortedRegs.length - 1].origY + sortedRegs[sortedRegs.length - 1].origHeight
          if (lastBottom < 75) hasLargeGap = true
        }
        const shortRegionCount = regions.filter(r => {
          const words = (r.translatedText || '').trim().split(/\s+/).length
          return words > 0 && words < 10
        }).length
        const gapWithShortRegions = hasLargeGap && shortRegionCount >= 3

        // Safety net: known Hebrew pages with diagrams that fail variance checks
        const knownDiagramPages = new Set([22, 36, 40, 41, 57, 64, 132, 196, 270, 271, 284, 295])
        const isKnownDiagramPage = knownDiagramPages.has(page.pageNumber)

        const pageHasDiagramRef = explicitDiagramRef || hasMeasurementLabels || gapWithShortRegions || isKnownDiagramPage

        const illustrations = await detectAndCropIllustrations(
          page.id, page.pageNumber, bookId, regions, cfg, pageHasDiagramRef,
        )

        // Filter out tiny/nonsensical illustration crops (minimum 200×200 px)
        const validIllustrations = illustrations.filter(ill =>
          ill.width >= 200 && ill.height >= 200
        )

        // Check page type: letter, diagram, or normal
        const letterPage = isLetterPage(regions, page.pageNumber)
        // Check both the algorithmic detection AND the known diagram pages list
        const knownDiagrams = new Set([22, 24, 26, 36, 38, 40, 41, 47, 48, 57, 64, 132, 160, 166, 188, 196, 203, 215, 221, 270, 271, 284, 295, 296, 348])
        // Also treat pages with measurement-noise regions as diagram pages —
        // the original Hebrew page image shows measurements with arrows/annotations
        // that get lost when illustration crops exclude the text label areas
        const hasMeasurementNoise = regions.some(r =>
          r.translatedText?.trim() && isMeasurementNoise(cleanTranslationText(r.translatedText.trim()))
        )
        const diagramPage = !letterPage && (isDiagramPage(regions) || knownDiagrams.has(page.pageNumber) || hasMeasurementNoise)
        const imageOnlyPage = letterPage || diagramPage

        if (imageOnlyPage) {
          // For letter/diagram pages: embed the FULL source page image
          // Letter pages: show original (don't translate handwritten text on image)
          // Diagram pages: show original + add description of what it depicts
          const fullPageImg = await getPageImage(page.id, page.pageNumber, bookId)
          if (fullPageImg) {
            try {
              const imgMeta = await sharp(fullPageImg).metadata()
              const imgW = imgMeta.width || 1655
              const imgH = imgMeta.height || 2340
              // Minimal margins (2%) — preserve full letter/image content
              const marginPct = 0.02
              const cropData = await sharp(fullPageImg)
                .extract({
                  left: Math.round(imgW * marginPct),
                  top: Math.round(imgH * marginPct),
                  width: Math.round(imgW * (1 - 2 * marginPct)),
                  height: Math.round(imgH * (1 - 2 * marginPct)),
                })
                .jpeg({ quality: 30 })
                .toBuffer()
              const cropMeta = await sharp(cropData).metadata()
              // Don't trim borders on letter pages — preserve full letter content
              const finalImg = letterPage ? cropData : await trimIllustrationBorders(cropData)
              const finalMeta = letterPage ? cropMeta : await sharp(finalImg).metadata()
              pageElements.push({
                type: 'illustration',
                imageData: finalImg,
                imageWidth: finalMeta.width || cropMeta.width || imgW,
                imageHeight: finalMeta.height || cropMeta.height || imgH,
              })
            } catch {
              for (const ill of validIllustrations) {
                pageElements.push({ type: 'illustration', imageData: ill.imageData, imageWidth: ill.width, imageHeight: ill.height })
              }
            }
          }

          if (letterPage) {
            // Force letter images to start on a new page (add divider before)
            // This ensures the image + "Translation of the above letter:" are together
            if (allElements.length > 0) {
              // The pageElements already has the illustration; we'll add a divider
              // before pushing them to allElements (handled below)
            }

            // For letter pages: add CLEAN translation below the image
            // Strip all Hebrew + skip English text that duplicates letterhead content
            const textParts = regions
              .filter(r => r.translatedText?.trim())
              .map(r => {
                let text = cleanTranslationText(r.translatedText || '')
                // Strip Hebrew header prefix: "Hebrew — English" → just "English"
                text = text.replace(/^[\u0590-\u05FF][\u0590-\u05FF\s\u200E]{2,60}\s*[\u2014\-]\s*/g, '')
                // Strip all remaining inline Hebrew quotes
                text = text.replace(/[\u0590-\u05FF][\u0590-\u05FF\s\u200E]{2,60}\s*[\u2014\-]\s*/g, '')
                // Strip orphaned Hebrew characters
                text = text.replace(/[\u0590-\u05FF\u200E]+/g, '').replace(/\s+/g, ' ').trim()
                return text
              })
              .filter(t => t.length > 10)
              // Skip duplicate English from letterheads (English text in Hebrew regions)
              // Remove very short fragments and exact duplicates
              .filter(t => t.split(/\s+/).length >= 4)
            const uniqueParts = Array.from(new Set(textParts))
            if (uniqueParts.length > 0) {
              pageElements.push({ type: 'caption', text: 'Translation of the above letter:' })
              pageElements.push({ type: 'body', text: uniqueParts.join('\n\n') })
            }
          } else {
            // Diagram page: generate a meaningful description of what the diagram depicts
            const labels = Array.from(new Set(
              regions
                .filter(r => r.translatedText?.trim())
                .map(r => cleanTranslationText(r.translatedText || '').trim())
                .filter(Boolean)
            ))
            const shortLabels = labels.filter(l => l.split(/\s+/).length < 10)
            const bodyTexts = labels.filter(l => l.split(/\s+/).length >= 10)

            const description = generateImageDescription(shortLabels, bodyTexts)
            if (description) {
              pageElements.push({ type: 'body', text: description })
            }
          }
        } else {
          // Normal page: render text with interleaved illustrations
          const sortedRegions = [...regions].sort((a, b) => a.origY - b.origY)
          let illustIdx = 0

          for (const region of sortedRegions) {
            while (illustIdx < validIllustrations.length && validIllustrations[illustIdx].y < region.origY) {
              pageElements.push({
                type: 'illustration',
                imageData: validIllustrations[illustIdx].imageData,
                imageWidth: validIllustrations[illustIdx].width,
                imageHeight: validIllustrations[illustIdx].height,
              })
              illustIdx++
            }

            if (!region.translatedText?.trim()) continue

            // Clean the translation text (remove meta-text artifacts, fix concatenation)
            const trimmed = cleanTranslationText(region.translatedText.trim())
            if (!trimmed) continue
            // Filter out standalone Hebrew source page numbers
            if (isStandalonePageNumber(trimmed)) continue
            // Filter out recurring Hebrew source headers (book title, section markers)
            if (isRecurringSourceHeader(trimmed, region.hebrewText || undefined, regions.length)) continue
            // Filter out garbled measurement diagrams (numbers + units that lost spatial layout)
            if (isMeasurementNoise(trimmed)) continue
            const wordCount = trimmed.split(/\s+/).length

            // Detect diagram labels / captions: short text (< 8 words) near illustrations
            if (wordCount < 8 && region.regionType !== 'header') {
              const nearIllustration = validIllustrations.some(ill =>
                Math.abs(ill.y - region.origY) < 15 || Math.abs(ill.y - (region.origY + region.origHeight)) < 15
              )
              if (nearIllustration) {
                pageElements.push({ type: 'caption', text: trimmed })
                continue
              }
              if (wordCount < 3) continue
            }

            // Detect table content
            if (isTableContent(trimmed, region.regionType)) {
              const rows = parseTableText(trimmed)
              if (rows.length > 0 && rows.some(r => r.length > 1)) {
                pageElements.push({ type: 'table', rows })
                continue
              }
            }

            if (region.regionType === 'header') {
              // Skip headers that are page numbers or recurring source headers
              if (!isStandalonePageNumber(trimmed) && !isRecurringSourceHeader(trimmed, region.hebrewText || undefined, regions.length)) {
                pageElements.push({ type: 'header', text: trimmed })
              }
            } else {
              pageElements.push({ type: 'body', text: trimmed })
            }
          }

          while (illustIdx < validIllustrations.length) {
            pageElements.push({
              type: 'illustration',
              imageData: validIllustrations[illustIdx].imageData,
              imageWidth: validIllustrations[illustIdx].width,
              imageHeight: validIllustrations[illustIdx].height,
            })
            illustIdx++
          }
        }

      } else if (translation?.englishOutput?.trim()) {
        pageElements.push({ type: 'body', text: cleanTranslationText(translation.englishOutput) })
      } else {
        continue
      }

      if (pageElements.length > 0) {
        // Deduplicate consecutive identical text elements (e.g., repeated diagram labels)
        const dedupedElements: ContentElement[] = []
        const seenTexts = new Set<string>()
        for (const el of pageElements) {
          if (el.type === 'header' || el.type === 'body' || el.type === 'caption') {
            const key = `${el.type}:${el.text || ''}`
            if (seenTexts.has(key)) continue
            seenTexts.add(key)
          }
          dedupedElements.push(el)
        }

        // Force new page for letter pages (each letter starts fresh)
        // so the image + "Translation of the above letter:" are always together
        const hasLetterContent = dedupedElements.some(e => e.type === 'caption' && (e.text || '').includes('Translation of the above'))
        const isLetterPg = hasLetterContent || (page.pageNumber >= 4 && page.pageNumber <= 12 && dedupedElements.some(e => e.type === 'illustration'))
        if (!isFirstSection && isLetterPg) {
          allElements.push({ type: 'divider' })
        }

        // Add topic dividers for content pages (not intro section)
        // Exception: Introduction/Foreword pages get dividers even in the intro section
        const startsWithHeader = dedupedElements[0]?.type === 'header'
        const isIntroSection = page.pageNumber <= 12
        const headerText = startsWithHeader ? (dedupedElements[0].text || '') : ''
        const isIntroOrForeword = /introduction|foreword/i.test(headerText)
        if (!isFirstSection && !isLetterPg && startsWithHeader && (!isIntroSection || isIntroOrForeword)) {
          allElements.push({ type: 'divider' })
        }
        isFirstSection = false
        allElements.push(...dedupedElements)
      }
    }

    // ── Collect TOC entries from header elements ──────────────────────────
    // This runs before rendering for both paths. For the HTML path we need
    // TOC entries without a pdf-lib rendering pass.
    const collectedTocEntries: TocEntry[] = []
    {
      let lastWasDivider = true
      for (const el of allElements) {
        if (el.type === 'divider') { lastWasDivider = true; continue }
        if (el.type === 'header') {
          const text = sanitizeForPdf(el.text || '', true)
          if (!text) { lastWasDivider = false; continue }
          const rawTocTitle = text.replace(/[\u0590-\u05FF\u200E\u200F]+/g, '').replace(/\s*[—\-]\s*/g, ' ').replace(/\s+/g, ' ').trim()
          const basicTitle = rawTocTitle
            .replace(/^[\s'"`,.\-:;*#()\[\]]+/, '').replace(/[\s'"`,.\-:;*#()\[\]]+$/, '')
            .replace(/^\d+(?:[.\)]?\s*)?(?=[A-Z])/, '')
            .replace(/^Page\s+\d+\s*/i, '')
            .replace(/\*\*/g, '')
            .replace(/\s+/g, ' ').trim()
          const isPerekHeader = /perek|chapter/i.test(basicTitle)
          if (basicTitle.length >= 10) {
            collectedTocEntries.push({
              title: basicTitle,
              pageNum: 2, // placeholder — HTML renderer handles pagination via CSS
              isPerek: isPerekHeader,
              afterDivider: lastWasDivider,
            })
          }
        }
        lastWasDivider = false
      }
    }

    // ── Build TOC lines (shared logic for both renderers) ────────────────
    const tocLinesForBook = buildTocLines(collectedTocEntries)

    // ════════════════════════════════════════════════════════════════════════
    // RENDERER BRANCHING
    // ════════════════════════════════════════════════════════════════════════

    if (renderer === 'html') {
      // ── Playwright HTML-to-PDF renderer ──────────────────────────────
      // Perfect bidi/Hebrew via Chromium's native HarfBuzz support.
      console.log(`[typeset/html] Generating HTML book for pages ${from}-${to} (${allElements.length} elements, ${tocLinesForBook.length} TOC lines)`)

      const htmlContent = await generateHtmlBook(
        allElements as import('@/lib/html-book-generator').ContentElement[],
        tocLinesForBook,
        cfg,
        book.name || 'Lishchno Tidreshu',
      )

      console.log(`[typeset/html] HTML generated (${Math.round(htmlContent.length / 1024)}KB), launching Playwright...`)

      const pdfBuffer = await htmlToPdf(htmlContent, cfg)

      console.log(`[typeset/html] PDF generated (${Math.round(pdfBuffer.length / 1024)}KB)`)

      const filename = `${sanitizeForPdf(book.name || 'book')}_English_p${from}-${to}.pdf`

      return new Response(new Uint8Array(pdfBuffer), {
        headers: {
          'Content-Type': 'application/pdf',
          'Content-Disposition': `inline; filename="${filename}"`,
          'Content-Length': String(pdfBuffer.length),
        },
      })
    }

    // ── pdf-lib renderer (legacy fallback: ?renderer=pdflib) ───────────

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

    // Hebrew title (original book name)
    const hebrewTitle = '\u05DC\u05E9\u05DB\u05E0\u05D5 \u05EA\u05D3\u05E8\u05E9\u05D5' // לשכנו תדרשו
    const hebTitleWidth = bidiLineWidth(hebrewTitle, 20, headerFont, hebrewBoldFont)
    drawBidiLine(titlePage, hebrewTitle, (cfg.pageWidth - hebTitleWidth) / 2, cfg.pageHeight * 0.63, 20, headerFont, hebrewBoldFont, rgb(...cfg.headerColor))

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

    // Render all elements in one continuous flow
    // Content starts after title page; we'll insert TOC pages after rendering
    let renderedTocEntries: TocEntry[] = []
    if (allElements.length > 0) {
      const result = await renderElements(doc, allElements, fonts, cfg, totalPdfPages + 1, runningTitle)
      totalPdfPages += result.pageCount
      renderedTocEntries = result.tocEntries
    }

    // Generate Table of Contents and insert after title page
    // We now know exactly which page each topic landed on.
    // Insert TOC pages at index 1 (after title page, before content).
    // This shifts all content page numbers by tocPageCount, so we adjust.
    if (renderedTocEntries.length > 0) {
      // For pdf-lib path, rebuild TOC lines from renderedTocEntries (which have correct page numbers)
      const pdfLibTocLines = buildTocLines(renderedTocEntries)

      // Calculate how many TOC pages we need
      const tocFontSize = cfg.bodyFontSize * 0.9
      const tocEntryLineHeight = tocFontSize * 1.7
      const tocSectionLineHeight = tocFontSize * 2.2
      const tocTitleSpace = cfg.headerFontSize + cfg.headerSpacingBelow + 22
      const tocTextHeight = cfg.pageHeight - cfg.marginTop - cfg.marginBottom

      let totalTocHeight = tocTitleSpace
      for (const line of pdfLibTocLines) {
        totalTocHeight += line.type === 'section' ? tocSectionLineHeight : tocEntryLineHeight
      }
      const tocPageCount = Math.max(1, Math.ceil(totalTocHeight / tocTextHeight))

      // Adjust all page numbers: content shifts right by tocPageCount
      const adjustedTocLines = pdfLibTocLines.map(line => ({
        ...line,
        pageNum: line.pageNum !== undefined ? line.pageNum + tocPageCount : undefined,
      }))

      // Create and insert TOC pages directly at position 1 (after title page)
      let tocLineIdx = 0
      const textWidth = cfg.pageWidth - cfg.marginLeft - cfg.marginRight

      for (let tp = 0; tp < tocPageCount; tp++) {
        const tocPage = doc.insertPage(1 + tp, [cfg.pageWidth, cfg.pageHeight])
        decoratePage(tocPage, tp + 2, fonts.body, cfg)

        let y = cfg.pageHeight - cfg.marginTop
        const safeBottom = cfg.marginBottom + 20

        if (tp === 0) {
          const tocTitleStr = 'TABLE OF CONTENTS'
          const tocTitleW = fonts.header.widthOfTextAtSize(tocTitleStr, cfg.headerFontSize)
          tocPage.drawText(tocTitleStr, {
            x: (cfg.pageWidth - tocTitleW) / 2,
            y: y - cfg.headerFontSize,
            size: cfg.headerFontSize,
            font: fonts.header,
            color: rgb(...cfg.headerColor),
          })
          y -= cfg.headerFontSize + cfg.headerSpacingBelow + 10
          tocPage.drawLine({
            start: { x: cfg.marginLeft + 20, y },
            end: { x: cfg.pageWidth - cfg.marginRight - 20, y },
            thickness: 0.4,
            color: rgb(0.72, 0.68, 0.62),
          })
          y -= 12
        }

        while (tocLineIdx < adjustedTocLines.length) {
          const line = adjustedTocLines[tocLineIdx]
          const lineH = line.type === 'section' ? tocSectionLineHeight : tocEntryLineHeight

          if (y - lineH < safeBottom) break

          if (line.type === 'section') {
            y -= tocFontSize * 0.4
            try {
              tocPage.drawText(line.text, {
                x: cfg.marginLeft,
                y: y - tocFontSize,
                size: tocFontSize,
                font: fonts.bold,
                color: rgb(...cfg.headerColor),
              })
            } catch { /* skip */ }
            y -= tocSectionLineHeight - tocFontSize * 0.4
          } else {
            let title = line.text
            if (title.length > 70) title = title.substring(0, 67) + '...'

            const pageStr = line.pageNum !== undefined ? String(line.pageNum) : ''
            const pageW = pageStr ? fonts.body.widthOfTextAtSize(pageStr, tocFontSize) : 0
            const titleMaxW = textWidth - pageW - 20
            const latinTitle = title.replace(/[\u0590-\u05FF\u200E\u200F]+/g, '').replace(/\s+/g, ' ').trim()

            let actualTitleW = 0
            try {
              actualTitleW = fonts.body.widthOfTextAtSize(latinTitle, tocFontSize)
              const displayTitle = actualTitleW > titleMaxW
                ? latinTitle.substring(0, Math.floor(latinTitle.length * titleMaxW / actualTitleW)) + '...'
                : latinTitle
              const displayW = fonts.body.widthOfTextAtSize(displayTitle, tocFontSize)
              tocPage.drawText(displayTitle, {
                x: cfg.marginLeft + 10,
                y: y - tocFontSize,
                size: tocFontSize,
                font: fonts.body,
                color: rgb(...cfg.textColor),
              })
              actualTitleW = displayW
            } catch { /* skip */ }

            if (pageStr) {
              const dotsY = y - tocFontSize + 2
              const dotSpacing = 4
              const dotsStart = cfg.marginLeft + 10 + actualTitleW + 6
              const dotsEnd = cfg.pageWidth - cfg.marginRight - pageW - 6
              if (dotsEnd > dotsStart + 8) {
                for (let dx = dotsStart; dx < dotsEnd; dx += dotSpacing) {
                  tocPage.drawText('.', { x: dx, y: dotsY, size: tocFontSize * 0.7, font: fonts.body, color: rgb(0.6, 0.58, 0.55) })
                }
              }
              tocPage.drawText(pageStr, {
                x: cfg.pageWidth - cfg.marginRight - pageW,
                y: y - tocFontSize,
                size: tocFontSize,
                font: fonts.body,
                color: rgb(...cfg.textColor),
              })
            }

            y -= tocEntryLineHeight
          }

          tocLineIdx++
        }
      }

      totalPdfPages += tocPageCount
    }

    // Add page numbers to ALL pages as the final step
    const finalPages = doc.getPages()
    for (let i = 0; i < finalPages.length; i++) {
      const pg = finalPages[i]
      const num = i + 1
      if (i === 0) continue
      const pageStr = `\u2014  ${num}  \u2014`
      const pnW = bodyFont.widthOfTextAtSize(pageStr, cfg.pageNumberFontSize)
      pg.drawText(pageStr, {
        x: (cfg.pageWidth - pnW) / 2,
        y: cfg.marginBottom / 2 - 2,
        size: cfg.pageNumberFontSize,
        font: bodyFont,
        color: rgb(0.48, 0.45, 0.42),
      })
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
