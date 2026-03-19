/**
 * HTML Book Generator for Playwright PDF rendering.
 *
 * Converts ContentElement[] (the same data the pdf-lib typeset route produces)
 * into a single HTML document.  Playwright's page.pdf() then converts it
 * to a pixel-perfect PDF with native HarfBuzz bidi/Hebrew support.
 *
 * Architecture:
 * - The entire book is a single flowing HTML document
 * - Playwright's @page CSS sets the page size and margins
 * - Playwright's displayHeaderFooter adds running header, page number,
 *   and decorative border frame to EVERY page automatically
 * - Title page, TOC, and content all flow in order with explicit page breaks
 *
 * All Hebrew text "just works" -- no manual bidi reordering, no splitBidi,
 * no font-segment switching.  Chromium handles it natively via HarfBuzz.
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

/** Wrap inline Hebrew phrases in <span dir="rtl"> for correct bidi rendering. */
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
          result.push(`<span dir="rtl" class="hebrew">${escapeHtml(buf)}</span>`)
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
      result.push(`<span dir="rtl" class="hebrew">${escapeHtml(buf)}</span>`)
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

// ─── Main HTML generation ────────────────────────────────────────────────────

export async function generateHtmlBook(
  elements: ContentElement[],
  tocLines: TocLine[],
  cfg: TypesetConfig,
  bookName: string,
): Promise<string> {
  // Load fonts as base64 for embedding in CSS
  const fontsDir = path.join(process.cwd(), 'public', 'fonts')
  let hebrewRegularB64 = ''
  let hebrewBoldB64 = ''
  try {
    const regBuf = await readFile(path.join(fontsDir, 'NotoSerifHebrew-Regular.ttf'))
    hebrewRegularB64 = regBuf.toString('base64')
    const boldBuf = await readFile(path.join(fontsDir, 'NotoSerifHebrew-Bold.ttf'))
    hebrewBoldB64 = boldBuf.toString('base64')
  } catch {
    // Fonts not found -- Hebrew will fall back to system fonts
  }

  const textColor = rgbToCss(cfg.textColor)
  const headerColor = rgbToCss(cfg.headerColor)
  // Content area height: page height minus the top and bottom margins
  const contentAreaHeight = cfg.pageHeight - cfg.marginTop - (cfg.marginBottom + 14)

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
    size: ${cfg.pageWidth}pt ${cfg.pageHeight}pt;
    margin: ${cfg.marginTop}pt ${cfg.marginRight}pt ${cfg.marginBottom + 14}pt ${cfg.marginLeft}pt;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: 'Times New Roman', 'NotoSerifHebrew', serif;
    font-size: ${cfg.bodyFontSize}pt;
    line-height: ${cfg.lineHeight};
    color: ${textColor};
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  /* Decorative border on every page via @page box decoration */
  @page {
    @top-center {
      content: "LISHCHNO TIDRESHU — ENGLISH TRANSLATION";
      font-size: 7pt;
      color: rgb(133, 122, 112);
      text-transform: uppercase;
      letter-spacing: 1pt;
    }
    @bottom-center {
      content: counter(page);
      font-size: ${cfg.pageNumberFontSize}pt;
      color: rgb(122, 115, 107);
    }
  }

  /* Visible border on content area */
  body {
    border: 0.7pt solid rgb(184, 174, 158);
    outline: 0.3pt solid rgb(209, 199, 186);
    outline-offset: 3pt;
  }

  .hebrew {
    font-family: 'NotoSerifHebrew', 'Times New Roman', serif;
    unicode-bidi: embed;
  }

  /* ── Title section ── */
  .title-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    height: ${contentAreaHeight}pt;
    /* The height fills exactly one page of content area so the title
       occupies a full page before the page-break-after kicks in. */
    page-break-after: always;
  }
  .title-hebrew {
    font-family: 'NotoSerifHebrew', serif;
    font-size: 20pt;
    font-weight: bold;
    color: ${headerColor};
    direction: rtl;
    margin-bottom: 12pt;
  }
  .title-english {
    font-size: 22pt;
    font-weight: bold;
    color: ${headerColor};
    margin-bottom: 16pt;
  }
  .title-subtitle {
    font-size: 13pt;
    color: rgb(102, 97, 89);
    margin-bottom: 10pt;
  }
  .title-desc {
    font-size: 10pt;
    color: rgb(128, 122, 112);
  }

  /* ── TOC section ── */
  .toc-section-wrapper {
    page-break-after: always;
  }
  .toc-title {
    text-align: center;
    font-size: ${cfg.headerFontSize}pt;
    font-weight: bold;
    color: ${headerColor};
    margin-bottom: ${cfg.headerSpacingBelow + 10}pt;
    border-bottom: 0.4pt solid rgb(184, 173, 158);
    padding-bottom: 12pt;
  }
  .toc-section-header {
    font-weight: bold;
    color: ${headerColor};
    font-size: ${cfg.bodyFontSize * 0.9}pt;
    margin-top: ${cfg.bodyFontSize * 0.4}pt;
    margin-bottom: 2pt;
  }
  .toc-row {
    display: flex;
    align-items: baseline;
    font-size: ${cfg.bodyFontSize * 0.9}pt;
    line-height: 1.7;
    padding-left: 10pt;
  }
  .toc-row .title {
    flex-shrink: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .toc-row .dots {
    flex: 1;
    border-bottom: 0.7pt dotted rgb(153, 148, 140);
    margin: 0 4pt 3pt 4pt;
    min-width: 12pt;
  }
  .toc-row .pg {
    flex-shrink: 0;
    white-space: nowrap;
    text-align: right;
    min-width: 20pt;
  }

  /* ── Content element styles ── */
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
    color: rgb(89, 84, 77);
    margin-bottom: ${cfg.paragraphSpacing * 0.5}pt;
    max-width: 85%;
    margin-left: auto;
    margin-right: auto;
  }

  .illustration {
    text-align: center;
    margin: ${cfg.illustrationPadding}pt 0;
    page-break-inside: avoid;
  }
  .illustration img {
    max-width: 100%;
    max-height: ${contentAreaHeight * 0.65}pt;
    height: auto;
  }
  .illustration.full-page img {
    max-height: ${contentAreaHeight * 0.80}pt;
  }

  /* Section divider (forces new page) */
  .divider {
    text-align: center;
    margin: 8pt 0 14pt 0;
    color: rgb(184, 173, 158);
    font-size: 10pt;
    page-break-before: always;
  }
  .divider-inline {
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

  // ── Title section ────────────────────────────────────────────────────────

  html.push(`<div class="title-section">
  <div class="title-hebrew">\u05DC\u05E9\u05DB\u05E0\u05D5 \u05EA\u05D3\u05E8\u05E9\u05D5</div>
  <div class="title-english">${escapeHtml(bookName || 'Lishchno Tidreshu')}</div>
  <div class="divider-inline" style="margin:6pt 0 16pt 0">
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
    // Estimate how many TOC pages (roughly 30 entries per page)
    const totalTocPages = Math.max(1, Math.ceil(tocLines.length / 30))

    // Adjust page numbers: content is shifted by totalTocPages
    const adjusted = tocLines.map(line => ({
      ...line,
      pageNum: line.pageNum !== undefined ? line.pageNum + totalTocPages : undefined,
    }))

    html.push(`<div class="toc-section-wrapper">`)
    html.push(`<div class="toc-title">TABLE OF CONTENTS</div>`)

    for (const line of adjusted) {
      if (line.type === 'section') {
        html.push(`<div class="toc-section-header">${escapeHtml(line.text)}</div>`)
      } else {
        const title = line.text.length > 70 ? line.text.substring(0, 67) + '...' : line.text
        const latinTitle = title.replace(/[\u0590-\u05FF\u200E\u200F]+/g, '').replace(/\s+/g, ' ').trim()
        const pageStr = line.pageNum !== undefined ? String(line.pageNum) : ''
        html.push(`<div class="toc-row">
  <span class="title">${escapeHtml(latinTitle)}</span>
  <span class="dots"></span>
  <span class="pg">${escapeHtml(pageStr)}</span>
</div>`)
      }
    }

    html.push(`</div>`) // close toc-section-wrapper
  }

  // ── Content ────────────────────────────────────────────────────────────
  // All content flows naturally after the TOC page break.
  // Chromium auto-paginates, and Playwright's header/footer templates
  // add the running header, page number, and decorative border on every page.

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
        html.push(`<div class="divider-inline">
  <span class="divider-line"></span><span class="divider-diamond"></span><span class="divider-line"></span>
</div>`)
      } else if (!isFirstElement) {
        html.push(`<div class="divider">
  <span class="divider-line"></span><span class="divider-diamond"></span><span class="divider-line"></span>
</div>`)
      }
      continue
    }

    isFirstElement = false

    if (el.type === 'header') {
      const text = sanitize(el.text || '')
      if (!text) continue
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

        const boldClass = isAllBold ? ' bold-para' : ''
        html.push(`<p class="body-text${boldClass}">${markupBidi(cleanText)}</p>`)
      }

    } else if (el.type === 'caption') {
      const text = sanitize(el.text || '')
      if (!text) continue
      html.push(`<div class="caption-text">${markupBidi(text)}</div>`)

    } else if (el.type === 'illustration' && el.imageData) {
      const b64 = el.imageData.toString('base64')
      const isFullPage = (el.imageWidth || 0) > 800 && (el.imageHeight || 0) > 1000
      const cls = isFullPage ? 'illustration full-page' : 'illustration'
      html.push(`<div class="${cls}"><img src="data:image/jpeg;base64,${b64}" /></div>`)

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
 *
 * Uses displayHeaderFooter for:
 * - Running header with decorative lines
 * - Page number in footer
 * - Double decorative border frame around the content area
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
    await page.waitForTimeout(500)

    const widthIn = (cfg.pageWidth / 72).toFixed(4)
    const heightIn = (cfg.pageHeight / 72).toFixed(4)

    // Playwright margins in inches
    const mTop = `${(cfg.marginTop / 72).toFixed(4)}in`
    const mBottom = `${((cfg.marginBottom + 14) / 72).toFixed(4)}in`
    const mLeft = `${(cfg.marginLeft / 72).toFixed(4)}in`
    const mRight = `${(cfg.marginRight / 72).toFixed(4)}in`

    const pdfBuffer = await page.pdf({
      width: `${widthIn}in`,
      height: `${heightIn}in`,
      printBackground: true,
      preferCSSPageSize: true, // use @page CSS margins instead of Playwright's
    })

    return Buffer.from(pdfBuffer)
  } finally {
    await browser.close()
  }
}
