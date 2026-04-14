/**
 * HTML Book Generator for Playwright PDF rendering.
 *
 * Converts ContentElement[] into a single HTML document.
 * Playwright's page.pdf() converts it to a pixel-perfect PDF with native
 * HarfBuzz bidi/Hebrew support.
 *
 * Border strategy:
 * - Left/right borders: CSS position:fixed pseudo-elements (repeat every printed page)
 * - Top/bottom borders + running header + page number: Playwright displayHeaderFooter
 *
 * All Hebrew text "just works" via Chromium's native HarfBuzz — no manual bidi.
 */

import { readFile } from 'fs/promises'
import path from 'path'

// ─── Types (mirrored from typeset/route.ts) ─────────────────────────────────

export interface TypesetConfig {
  pageWidth: number
  pageHeight: number
  marginTop: number
  marginBottom: number
  marginLeft: number
  marginRight: number
  bodyFontSize: number
  headerFontSize: number
  subheaderFontSize: number
  lineHeight: number
  paragraphSpacing: number
  headerSpacingAbove: number
  headerSpacingBelow: number
  illustrationMaxWidth: number
  illustrationPadding: number
  textColor: [number, number, number]
  headerColor: [number, number, number]
  pageNumberFontSize: number
  firstLineIndent: number
  illustrationGapThreshold: number
}

export interface ContentElement {
  type: 'header' | 'body' | 'illustration' | 'divider' | 'table' | 'caption'
  text?: string
  isAllBold?: boolean
  imageData?: Buffer
  imageWidth?: number
  imageHeight?: number
  pageNumber?: number
  rows?: string[][]
}

export interface TocEntry {
  title: string
  pageNum: number
  isPerek?: boolean
  afterDivider?: boolean
}

interface TocLine {
  type: 'section' | 'entry'
  text: string
  pageNum?: number
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function isHebrew(ch: string): boolean {
  const c = ch.charCodeAt(0)
  return (c >= 0x0590 && c <= 0x05FF) || (c >= 0xFB1D && c <= 0xFB4F)
}

function containsHebrew(text: string): boolean {
  for (const ch of text) {
    if (isHebrew(ch)) return true
  }
  return false
}

/** Wrap inline Hebrew phrases in <bdi dir="rtl"> for correct bidi rendering. */
function markupBidi(text: string): string {
  if (!containsHebrew(text)) return escapeHtml(text)

  const result: string[] = []
  let buf = ''
  let bufIsHebrew = false
  let started = false

  for (const ch of text) {
    const heb = isHebrew(ch)
    const isStrong = heb || /[a-zA-Z0-9]/.test(ch)

    if (!started) {
      buf = ch
      bufIsHebrew = isStrong ? heb : false
      started = true
      continue
    }

    if (!isStrong) {
      buf += ch
    } else if (heb === bufIsHebrew) {
      buf += ch
    } else {
      if (buf) {
        if (bufIsHebrew) {
          result.push(`<bdi dir="rtl" class="hebrew">${escapeHtml(buf)}</bdi>`)
        } else {
          result.push(escapeHtml(buf))
        }
      }
      buf = ch
      bufIsHebrew = heb
    }
  }
  if (buf) {
    if (bufIsHebrew) {
      result.push(`<bdi dir="rtl" class="hebrew">${escapeHtml(buf)}</bdi>`)
    } else {
      result.push(escapeHtml(buf))
    }
  }
  return result.join('')
}

function cleanTranslationText(text: string): string {
  return text
    .replace(/\[THIS IS (TABLE|DIAGRAM|CHART|IMAGE|FIGURE)[:\]]/gi, '')
    .replace(/\[(TABLE|DIAGRAM|CHART|IMAGE|FIGURE):\s*/gi, '')
    .replace(/\[END (TABLE|DIAGRAM|CHART|FIGURE)\]/gi, '')
    .replace(/\[Note:.*?\]/gi, '')
    .replace(/([a-z])\n([A-Z])/g, '$1 $2')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .trim()
}

function sanitize(text: string): string {
  return text
    .replace(/[\u0000-\u001F]/g, '')
    .replace(/[\u200E\u200F\u200B-\u200D\u2028\u2029\uFEFF]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function rgbToCss(c: [number, number, number]): string {
  return `rgb(${Math.round(c[0] * 255)}, ${Math.round(c[1] * 255)}, ${Math.round(c[2] * 255)})`
}

/** Check if text is junk that should be filtered from body content. */
function isJunkText(text: string): boolean {
  // Empty quotes like " " or "" or " ", possibly with trailing punctuation
  if (/^[""\u201C\u201D\u2018\u2019'`\s,.:;\-]{1,8}$/.test(text)) return true
  // Very short non-word content (under 4 chars with no alphanumeric)
  if (text.length < 4 && !/[a-zA-Z0-9\u0590-\u05FF]/.test(text)) return true
  // Stray punctuation runs like ", , : : - , , : :" or ". — "
  if (/^[,.:;\-\u2014\u2013\s]{4,}/.test(text)) return true
  // Leading period/comma at start of otherwise short text
  if (/^[.,]\s/.test(text) && text.length < 20) return true
  // Text that's only quotes + punctuation + whitespace (no real words)
  if (text.length < 12 && !/[a-zA-Z]{2,}/.test(text) && !/[\u0590-\u05FF]{2,}/.test(text)) return true
  return false
}

/**
 * Clean a header for display: strip stray Hebrew that appears alongside
 * an already-translated English version.
 */
function cleanHeaderForDisplay(text: string): string {
  let cleaned = text
  // Remove standalone Hebrew text before em-dash + English
  cleaned = cleaned.replace(/^[\u0590-\u05FF][\u0590-\u05FF\s\u200E\-.]*\s*[\u2014\u2015\u2013—\-]\s*/g, '')
  // Remove trailing Hebrew after em-dash
  cleaned = cleaned.replace(/\s*[\u2014\u2015\u2013—\-]\s*[\u0590-\u05FF][\u0590-\u05FF\s\u200E\-.]*$/g, '')
  // Remove standalone Hebrew-only prefix before Latin text
  cleaned = cleaned.replace(/^[\u0590-\u05FF\s\u200E]+(?=[A-Z])/g, '')
  // Remove trailing Hebrew chunk after Latin text ending
  cleaned = cleaned.replace(/(?<=[a-z.!?"])\s*[\u0590-\u05FF\s\u200E]+$/g, '')
  // Remove numbering artifacts
  cleaned = cleaned.replace(/^\d+\.\s*/, '')
  cleaned = cleaned.replace(/^[A-Z]\d+\s*[\-:.]?\s*/, '')
  cleaned = cleaned.replace(/\s+/g, ' ').trim()
  return cleaned
}

/**
 * Estimate page numbers for TOC entries by simulating pagination.
 * Returns an array of estimated page numbers, one per header element
 * in the elements array (in order of appearance).
 */
function estimateHeaderPages(
  elements: ContentElement[],
  tocPageCount: number,
): number[] {
  const headerPages: number[] = []

  // Content area: page height minus Playwright margins (~30pt top + ~30pt bottom)
  const contentHeightPt = 648 - 60 // page height minus margins
  const lineHeightPt = 11 * 1.5 // bodyFontSize * lineHeight
  const linesPerPage = Math.floor(contentHeightPt / lineHeightPt)

  // Content starts after: title page (1) + TOC pages
  let currentPage = 1 + tocPageCount + 1
  let currentLine = 0

  for (let i = 0; i < elements.length; i++) {
    const el = elements[i]

    if (el.type === 'divider') {
      currentPage++
      currentLine = 0
      continue
    }

    if (el.type === 'header') {
      headerPages.push(currentPage)
      currentLine += 3
      if (currentLine >= linesPerPage) { currentPage++; currentLine = 0 }
      continue
    }

    if (el.type === 'body') {
      const charCount = (el.text || '').length
      // ~65 chars per line with current font/margins
      const lines = Math.max(1, Math.ceil(charCount / 65))
      currentLine += lines + 1
      while (currentLine >= linesPerPage) {
        currentLine -= linesPerPage
        currentPage++
      }
    } else if (el.type === 'illustration') {
      const isFullPage = (el.imageWidth || 0) > 800 && (el.imageHeight || 0) > 1000
      currentLine += isFullPage ? linesPerPage : Math.ceil(linesPerPage * 0.45)
      if (currentLine >= linesPerPage) { currentPage++; currentLine = 0 }
    } else if (el.type === 'table') {
      currentLine += (el.rows?.length || 3) + 2
      if (currentLine >= linesPerPage) { currentPage++; currentLine = 0 }
    } else if (el.type === 'caption') {
      currentLine += 2
      if (currentLine >= linesPerPage) { currentPage++; currentLine = 0 }
    }
  }

  return headerPages
}

// ─── Main HTML generation ────────────────────────────────────────────────────

export async function generateHtmlBook(
  elements: ContentElement[],
  tocLines: TocLine[],
  cfg: TypesetConfig,
  bookName: string,
): Promise<string> {
  // Load fonts as base64
  const fontsDir = path.join(process.cwd(), 'public', 'fonts')
  let hebrewRegularB64 = ''
  let hebrewBoldB64 = ''
  try {
    const regBuf = await readFile(path.join(fontsDir, 'NotoSerifHebrew-Regular.ttf'))
    hebrewRegularB64 = regBuf.toString('base64')
    const boldBuf = await readFile(path.join(fontsDir, 'NotoSerifHebrew-Bold.ttf'))
    hebrewBoldB64 = boldBuf.toString('base64')
  } catch {
    // Fonts not found — Hebrew will fall back to system fonts
  }

  const textColor = rgbToCss(cfg.textColor)
  const headerColor = rgbToCss(cfg.headerColor)
  const pageW = cfg.pageWidth  // 468pt = 6.5"
  const pageH = cfg.pageHeight // 648pt = 9"

  // ── Layout geometry (all in pt) ──
  // Outer border: 8pt inset from page edge on all 4 sides
  const OUTER_INSET = 8
  // Inner border: 3pt inside the outer border
  const INNER_GAP = 3
  // Content padding: 10pt inside the inner border
  const CONTENT_PAD = 10
  // Total margin from page edge to content start:
  //   OUTER_INSET (8) + outer border (0.7) + INNER_GAP (3) + inner border (0.3) + CONTENT_PAD (10) = ~22pt
  // Plus space for running header above and page number below
  const HEADER_SPACE = 20 // space for running header text above the outer border
  const FOOTER_SPACE = 20 // space for page number text below the outer border

  // Playwright margins define where body content can flow
  const PW_MARGIN_TOP = OUTER_INSET + INNER_GAP + CONTENT_PAD + HEADER_SPACE  // ~35pt
  const PW_MARGIN_BOTTOM = OUTER_INSET + INNER_GAP + CONTENT_PAD + FOOTER_SPACE // ~35pt
  const _PW_MARGIN_LEFT = OUTER_INSET + INNER_GAP + CONTENT_PAD + 14  // ~35pt — enough clearance from inner border
  const _PW_MARGIN_RIGHT = OUTER_INSET + INNER_GAP + CONTENT_PAD + 14  // ~35pt
  void _PW_MARGIN_LEFT; void _PW_MARGIN_RIGHT;

  // Estimate TOC pages (roughly 30 entries per page)
  const totalTocPages = tocLines.length > 0 ? Math.max(1, Math.ceil(tocLines.length / 30)) : 0

  // Estimate page numbers for headers
  const headerPages = estimateHeaderPages(elements, totalTocPages)

  // Map TOC entry indices to estimated page numbers.
  // TOC entries are built from headers in order, so the Nth TOC 'entry' line
  // corresponds to the Nth estimated page number.
  // We need to count only 'entry' type TOC lines (skip 'section' headers).
  let headerIdx = 0
  const tocEntryPages: number[] = []
  for (const line of tocLines) {
    if (line.type === 'entry') {
      tocEntryPages.push(headerIdx < headerPages.length ? headerPages[headerIdx] : 3)
      headerIdx++
    }
  }

  // Content height available for illustrations
  const contentH = pageH - PW_MARGIN_TOP - PW_MARGIN_BOTTOM

  const html: string[] = []

  html.push(`<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<style>
  @font-face {
    font-family: 'NotoSerifHebrew';
    font-weight: 400;
    src: url('data:font/truetype;base64,${hebrewRegularB64}') format('truetype');
  }
  @font-face {
    font-family: 'NotoSerifHebrew';
    font-weight: 700;
    src: url('data:font/truetype;base64,${hebrewBoldB64}') format('truetype');
  }

  @page {
    size: ${pageW}pt ${pageH}pt;
    margin: 60pt 0 55pt 0;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: 'Times New Roman', 'NotoSerifHebrew', serif;
    font-size: ${cfg.bodyFontSize}pt;
    line-height: ${cfg.lineHeight};
    color: ${textColor};
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
    /* Padding pushes content inside the border frame on all sides */
    padding-left: ${OUTER_INSET + INNER_GAP + CONTENT_PAD}pt;
    padding-right: ${OUTER_INSET + INNER_GAP + CONTENT_PAD}pt;
    padding-top: ${OUTER_INSET + INNER_GAP + CONTENT_PAD + 5}pt;
    padding-bottom: ${OUTER_INSET + INNER_GAP + CONTENT_PAD + 5}pt;
  }

  /* ── Left/right vertical border lines ──
     position:fixed elements repeat on EVERY printed page in Chromium. */

  /* Left side: outer + inner border */
  body::before {
    content: '';
    position: fixed;
    left: ${OUTER_INSET}pt;
    top: ${OUTER_INSET}pt;
    bottom: ${OUTER_INSET}pt;
    width: ${INNER_GAP}pt;
    border-left: 0.7pt solid rgb(184, 174, 158);
    border-right: 0.3pt solid rgb(209, 199, 186);
    z-index: 1000;
    pointer-events: none;
  }
  /* Right side: outer + inner border */
  body::after {
    content: '';
    position: fixed;
    right: ${OUTER_INSET}pt;
    top: ${OUTER_INSET}pt;
    bottom: ${OUTER_INSET}pt;
    width: ${INNER_GAP}pt;
    border-right: 0.7pt solid rgb(184, 174, 158);
    border-left: 0.3pt solid rgb(209, 199, 186);
    z-index: 1000;
    pointer-events: none;
  }

  .hebrew, bdi.hebrew {
    font-family: 'NotoSerifHebrew', 'Times New Roman', serif;
    unicode-bidi: isolate;
    direction: rtl;
  }

  /* ── Title page ── */
  .title-page {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    height: ${pageH}pt;
    page-break-after: always;
  }
  .title-hebrew {
    font-family: 'NotoSerifHebrew', serif;
    font-size: 22pt;
    font-weight: bold;
    color: ${headerColor};
    direction: rtl;
    margin-bottom: 14pt;
  }
  .title-english {
    font-size: 24pt;
    font-weight: bold;
    color: ${headerColor};
    margin-bottom: 18pt;
  }
  .title-subtitle {
    font-size: 14pt;
    color: rgb(102, 97, 89);
    margin-bottom: 10pt;
  }
  .title-desc {
    font-size: 11pt;
    color: rgb(128, 122, 112);
    margin-top: 6pt;
  }

  /* ── Divider ornament ── */
  .divider-ornament {
    text-align: center;
    margin: 8pt 0 14pt 0;
    color: rgb(184, 173, 158);
    font-size: 10pt;
  }
  .divider-line {
    display: inline-block;
    width: 40pt;
    height: 0;
    border-top: 0.4pt solid rgb(184, 173, 158);
    vertical-align: middle;
    margin: 0 6pt;
  }
  .divider-diamond {
    display: inline-block;
    width: 6pt;
    height: 6pt;
    transform: rotate(45deg);
    border: 0.6pt solid rgb(184, 173, 158);
    vertical-align: middle;
    margin: 0 2pt;
  }

  /* ── TOC ── */
  .toc-wrapper {
    page-break-after: always;
  }
  .toc-title {
    text-align: center;
    font-size: ${cfg.headerFontSize}pt;
    font-weight: bold;
    color: ${headerColor};
    margin-bottom: ${cfg.headerSpacingBelow + 8}pt;
    border-bottom: 0.4pt solid rgb(184, 173, 158);
    padding-bottom: 10pt;
  }
  .toc-section-header {
    font-weight: bold;
    color: ${headerColor};
    font-size: ${cfg.bodyFontSize * 0.95}pt;
    margin-top: ${cfg.bodyFontSize * 0.5}pt;
    margin-bottom: 3pt;
  }
  .toc-row {
    display: flex;
    align-items: baseline;
    font-size: ${cfg.bodyFontSize * 0.9}pt;
    line-height: 1.8;
    padding-left: 10pt;
  }
  .toc-row .toc-title-text {
    flex-shrink: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .toc-row .toc-dots {
    flex: 1;
    border-bottom: 0.7pt dotted rgb(170, 165, 155);
    margin: 0 4pt 3pt 4pt;
    min-width: 12pt;
  }
  .toc-row .toc-pg {
    flex-shrink: 0;
    white-space: nowrap;
    text-align: right;
    min-width: 22pt;
  }

  /* ── Content styles ── */
  .section-header {
    text-align: center;
    font-size: ${cfg.headerFontSize}pt;
    font-weight: bold;
    color: ${headerColor};
    margin-top: ${cfg.headerSpacingAbove}pt;
    margin-bottom: ${cfg.headerSpacingBelow}pt;
    line-height: ${cfg.lineHeight};
  }

  .body-text {
    text-indent: ${cfg.firstLineIndent}pt;
    margin-bottom: ${cfg.paragraphSpacing}pt;
    text-align: justify;
    hyphens: auto;
    orphans: 2;
    widows: 2;
  }
  .body-text.bold-para {
    text-indent: 0;
    text-align: center;
    font-size: ${cfg.subheaderFontSize}pt;
    font-weight: bold;
  }

  .caption-text {
    text-align: center;
    font-size: ${cfg.bodyFontSize * 0.85}pt;
    font-style: italic;
    color: rgb(89, 84, 77);
    margin-bottom: ${cfg.paragraphSpacing * 0.5}pt;
    max-width: 85%;
    margin-left: auto;
    margin-right: auto;
  }

  .illustration {
    text-align: center;
    margin: ${cfg.illustrationPadding}pt auto;
    page-break-inside: avoid;
  }
  .figure-group {
    page-break-inside: avoid;
  }
  /* Push last illustration to bottom of page when it's the final element in a section */
  .illustration-bottom {
    margin-top: auto;
  }
  /* Section wrapper for flex bottom-push */
  .section-content {
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .illustration img {
    max-width: 100%;
    height: auto;
  }
  .illustration.normal img {
    max-height: ${Math.round(contentH * 0.55)}pt;
  }
  .illustration.full-page img {
    max-height: ${Math.round(contentH * 0.72)}pt;
  }

  /* Section divider — forces a new page */
  .section-break {
    page-break-before: always;
  }
  .inline-break {
    text-align: center;
    margin: 8pt 0 14pt 0;
    color: rgb(184, 173, 158);
  }

  /* ── Table styles ── */
  .content-table {
    width: 100%;
    border-collapse: collapse;
    font-size: ${cfg.bodyFontSize * 0.88}pt;
    margin: 6pt 0 ${cfg.paragraphSpacing}pt 0;
  }
  .content-table td, .content-table th {
    padding: 2pt 4pt;
    vertical-align: top;
    border-bottom: 0.2pt solid rgb(217, 209, 199);
  }
  .content-table th {
    font-weight: bold;
    color: ${headerColor};
    border-bottom: 0.4pt solid rgb(184, 173, 158);
  }
  .content-table tr:first-child td,
  .content-table tr:first-child th {
    border-top: 0.5pt solid rgb(158, 148, 133);
  }
  .content-table tr:last-child td {
    border-bottom: 0.5pt solid rgb(158, 148, 133);
  }
</style>
</head>
<body>
`)

  // ── Title page ──────────────────────────────────────────────────────────

  const cleanBookName = (bookName || 'Lishchno Tidreshu').replace(/\s*\(Full\)\s*$/i, '')

  html.push(`<div class="title-page">
  <div class="title-hebrew">\u05DC\u05E9\u05DB\u05E0\u05D5 \u05EA\u05D3\u05E8\u05E9\u05D5</div>
  <div class="title-english">${escapeHtml(cleanBookName)}</div>
  <div class="divider-ornament" style="margin:6pt 0 18pt 0">
    <span class="divider-line"></span>
    <span class="divider-diamond"></span>
    <span class="divider-line"></span>
  </div>
  <div class="title-subtitle">English Translation</div>
  <div class="title-desc">The Third Beis HaMikdash According to Yechezkel HaNavi</div>
</div>
`)

  // ── Table of Contents ──────────────────────────────────────────────────

  if (tocLines.length > 0) {
    html.push(`<div class="toc-wrapper">`)
    html.push(`<div class="toc-title">TABLE OF CONTENTS</div>`)

    let entryIdx = 0
    for (const line of tocLines) {
      if (line.type === 'section') {
        html.push(`<div class="toc-section-header">${escapeHtml(line.text)}</div>`)
      } else {
        // Get estimated page number from our pre-computed array
        const pageNum = entryIdx < tocEntryPages.length ? tocEntryPages[entryIdx] : undefined
        entryIdx++

        const title = line.text.length > 72 ? line.text.substring(0, 69) + '...' : line.text
        const latinTitle = title.replace(/[\u0590-\u05FF\u200E\u200F]+/g, '').replace(/\s+/g, ' ').trim()
        if (!latinTitle) continue
        const pageStr = pageNum !== undefined ? String(pageNum) : ''
        html.push(`<div class="toc-row">
  <span class="toc-title-text">${escapeHtml(latinTitle)}</span>
  <span class="toc-dots"></span>
  <span class="toc-pg">${escapeHtml(pageStr)}</span>
</div>`)
      }
    }

    html.push(`</div>`)
  }

  // ── Content ────────────────────────────────────────────────────────────

  let isFirstElement = true

  for (let elIdx = 0; elIdx < elements.length; elIdx++) {
    const el = elements[elIdx]

    if (el.type === 'divider') {
      let illustrationComingSoon = false
      for (let look = 1; look <= 3 && elIdx + look < elements.length; look++) {
        const upcoming = elements[elIdx + look]
        if (upcoming.type === 'illustration') { illustrationComingSoon = true; break }
        if (upcoming.type === 'divider' || upcoming.type === 'body') break
      }

      if (illustrationComingSoon) {
        html.push(`<div class="inline-break">
  <span class="divider-line"></span><span class="divider-diamond"></span><span class="divider-line"></span>
</div>`)
      } else if (!isFirstElement) {
        html.push(`<div class="section-break">
  <div class="divider-ornament">
    <span class="divider-line"></span><span class="divider-diamond"></span><span class="divider-line"></span>
  </div>
</div>`)
      }
      continue
    }

    isFirstElement = false

    if (el.type === 'header') {
      let text = sanitize(el.text || '')
      if (!text) continue
      text = cleanHeaderForDisplay(text)
      if (!text || text.length < 3) continue
      html.push(`<div class="section-header">${markupBidi(text)}</div>`)

    } else if (el.type === 'body') {
      const rawText = el.text || ''
      if (!rawText.trim()) continue

      const paragraphs = rawText.split(/\n\s*\n/).map(p => p.replace(/\n/g, ' ').trim()).filter(Boolean)

      for (const para of paragraphs) {
        const isAllBold = para.startsWith('**') && para.endsWith('**')
        const cleanText = sanitize(
          para
            .replace(/\*\*([\s\S]*?)\*\*/g, '$1')
            .replace(/^#+\s+/gm, '')
            .replace(/`([^`]+)`/g, '$1')
        )
        if (!cleanText) continue
        if (isJunkText(cleanText)) continue

        const boldClass = isAllBold ? ' bold-para' : ''
        html.push(`<p class="body-text${boldClass}">${markupBidi(cleanText)}</p>`)
      }

    } else if (el.type === 'caption') {
      const text = sanitize(el.text || '')
      if (!text) continue
      // Check if next element is an illustration — if so, group them together
      const nextEl = elIdx + 1 < elements.length ? elements[elIdx + 1] : null
      if (nextEl?.type === 'illustration' && nextEl.imageData) {
        // Open figure group: caption + illustration kept together
        html.push(`<div class="figure-group">`)
        html.push(`<div class="caption-text">${markupBidi(text)}</div>`)
        const b64 = nextEl.imageData.toString('base64')
        const isFullPage = (nextEl.imageWidth || 0) > 800 && (nextEl.imageHeight || 0) > 1000
        const cls = isFullPage ? 'illustration full-page' : 'illustration normal'
        html.push(`<div class="${cls}"><img src="data:image/jpeg;base64,${b64}" /></div>`)
        // Check if the element after the illustration is also a caption (label below image)
        const afterIll = elIdx + 2 < elements.length ? elements[elIdx + 2] : null
        if (afterIll?.type === 'caption') {
          const afterText = sanitize(afterIll.text || '')
          if (afterText) html.push(`<div class="caption-text">${markupBidi(afterText)}</div>`)
          elIdx += 2 // skip both illustration and trailing caption
        } else {
          elIdx += 1 // skip just the illustration
        }
        html.push(`</div>`) // close figure-group
      } else {
        html.push(`<div class="caption-text">${markupBidi(text)}</div>`)
      }

    } else if (el.type === 'illustration' && el.imageData) {
      const b64 = el.imageData.toString('base64')
      const isFullPage = (el.imageWidth || 0) > 800 && (el.imageHeight || 0) > 1000
      const cls = isFullPage ? 'illustration full-page' : 'illustration normal'

      // Check if this illustration is the last content before a divider or end of book
      // If so, push it to the bottom of the page
      let isLastBeforeBreak = false
      const nextEl = elIdx + 1 < elements.length ? elements[elIdx + 1] : null
      const afterNext = elIdx + 2 < elements.length ? elements[elIdx + 2] : null
      if (!nextEl || nextEl.type === 'divider') isLastBeforeBreak = true
      if (nextEl?.type === 'caption' && (!afterNext || afterNext.type === 'divider')) isLastBeforeBreak = true
      const bottomClass = isLastBeforeBreak ? ' illustration-bottom' : ''

      // Check if next element is a caption — group them together
      if (nextEl?.type === 'caption') {
        const capText = sanitize(nextEl.text || '')
        html.push(`<div class="figure-group${bottomClass}">`)
        html.push(`<div class="${cls}"><img src="data:image/jpeg;base64,${b64}" /></div>`)
        if (capText) html.push(`<div class="caption-text">${markupBidi(capText)}</div>`)
        html.push(`</div>`)
        elIdx += 1 // skip the caption
      } else {
        html.push(`<div class="${cls}${bottomClass}"><img src="data:image/jpeg;base64,${b64}" /></div>`)
      }

    } else if (el.type === 'table' && el.rows) {
      const rows = el.rows.map(row => [...row].reverse())
      if (rows.length === 0) continue

      html.push(`<table class="content-table">`)
      for (let rIdx = 0; rIdx < rows.length; rIdx++) {
        const row = rows[rIdx]
        const tag = rIdx === 0 ? 'th' : 'td'
        html.push(`<tr>`)
        for (const cell of row) {
          const cellText = sanitize(cleanTranslationText(cell || ''))
          html.push(`  <${tag}>${markupBidi(cellText)}</${tag}>`)
        }
        html.push(`</tr>`)
      }
      html.push(`</table>`)
    }
  }

  html.push(`</body></html>`)

  return html.join('\n')
}

/**
 * Convert HTML to PDF using Playwright.
 */
export async function htmlToPdf(
  htmlContent: string,
  cfg: TypesetConfig,
): Promise<Buffer> {
  const { chromium } = await import('playwright')

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  })

  try {
    const page = await browser.newPage()

    await page.setContent(htmlContent, { waitUntil: 'networkidle' })
    await page.waitForTimeout(800)

    const widthIn = (cfg.pageWidth / 72).toFixed(4)
    const heightIn = (cfg.pageHeight / 72).toFixed(4)

    // Border geometry — MUST match the CSS values in generateHtmlBook
    const OUTER_INSET = 8
    const INNER_GAP = 3
    const CONTENT_PAD = 10
    const _HEADER_SPACE = 14
    void _HEADER_SPACE;

    // Colors
    const outerColor = 'rgb(184,174,158)'
    const innerColor = 'rgb(209,199,186)'
    const headerTextColor = 'rgb(133,122,112)'
    const pageNumColor = 'rgb(122,115,107)'

    // Playwright margins in pt (converted to inches for API)
    const mTopPt = 65  // Must clear: header text + outer border + inner border + padding
    const mBottomPt = 60 // Must clear: page number + outer border + inner border + padding
    const mLeftPt = 1   // body padding handles actual content indentation
    const mRightPt = 1  // body padding handles actual content indentation

    const mTop = `${(mTopPt / 72).toFixed(4)}in`
    const mBottom = `${(mBottomPt / 72).toFixed(4)}in`
    const mLeft = `${(mLeftPt / 72).toFixed(4)}in`
    const mRight = `${(mRightPt / 72).toFixed(4)}in`

    // Header template: running title text ABOVE the outer border, then border lines
    const headerTemplate = `
      <div style="width:100%; font-size:7pt; text-align:center; padding:0 ${OUTER_INSET}pt; color:${headerTextColor};">
        <div style="font-family:'Times New Roman',serif; letter-spacing:0.4pt; padding:2pt 0 3pt 0;">
          <span style="color:${innerColor};">\u2014\u2014</span>
          <span style="margin:0 6pt;">LISHCHNO TIDRESHU \u2014 ENGLISH TRANSLATION</span>
          <span style="color:${innerColor};">\u2014\u2014</span>
        </div>
        <div style="border-top:0.7pt solid ${outerColor}; margin:0;"></div>
        <div style="border-top:0.3pt solid ${innerColor}; margin:${INNER_GAP}pt ${INNER_GAP}pt 0 ${INNER_GAP}pt;"></div>
      </div>`

    // Footer template: border lines then page number BELOW the outer border
    const footerTemplate = `
      <div style="width:100%; font-size:${cfg.pageNumberFontSize}pt; text-align:center; padding:0 ${OUTER_INSET}pt; color:${pageNumColor};">
        <div style="border-bottom:0.3pt solid ${innerColor}; margin:0 ${INNER_GAP}pt ${INNER_GAP}pt ${INNER_GAP}pt;"></div>
        <div style="border-bottom:0.7pt solid ${outerColor}; margin:0 0 3pt 0;"></div>
        <div style="font-family:'Times New Roman',serif; padding:2pt 0;">\u2014 <span class="pageNumber"></span> \u2014</div>
      </div>`

    const pdfBuffer = await page.pdf({
      width: `${widthIn}in`,
      height: `${heightIn}in`,
      margin: {
        top: mTop,
        bottom: mBottom,
        left: mLeft,
        right: mRight,
      },
      printBackground: true,
      displayHeaderFooter: true,
      headerTemplate,
      footerTemplate,
    })

    return Buffer.from(pdfBuffer)
  } finally {
    await browser.close()
  }
}
