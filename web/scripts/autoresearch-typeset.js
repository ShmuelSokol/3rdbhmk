#!/usr/bin/env node
/**
 * Autoresearch for Typeset PDF — iteratively optimizes typesetting parameters
 * to produce print-grade English book output.
 *
 * Scoring metrics:
 *   S1: Page efficiency — English pages per Hebrew page (target: ~1.0, penalize >1.5 or <0.7)
 *   S2: Font readability — body font size (target: 10-12pt, penalize <9 or >13)
 *   S3: Illustration coverage — illustration area as fraction of total (target: 0.1-0.4)
 *   S4: Margin balance — text width vs page width ratio (target: 0.65-0.80)
 *   S5: Line density — lines per page (target: 30-45, penalize sparse or cramped)
 *
 * Usage:
 *   BASE_URL=https://3rdbhmk.ksavyad.com node scripts/autoresearch-typeset.js
 *   BASE_URL=https://3rdbhmk.ksavyad.com node scripts/autoresearch-typeset.js --iterations 10
 */

const fs = require('fs')
const path = require('path')

const BASE = process.env.BASE_URL || 'https://3rdbhmk.ksavyad.com'
const BOOK_ID = 'jcqje5aut5wve5w5b8hv6fcq8'
const TEST_FROM = 10
const TEST_TO = 35
const RESULTS_DIR = path.join(process.cwd(), 'autoresearch-results')

const maxIterations = parseInt(
  process.argv.includes('--iterations')
    ? process.argv[process.argv.indexOf('--iterations') + 1]
    : '10'
)

// ─── Typeset config defaults (must match route.ts) ──────────────────────────

const DEFAULT_CONFIG = {
  pageWidth: 468,
  pageHeight: 648,
  marginTop: 54,
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
  firstLineIndent: 18,
  illustrationGapThreshold: 8,
}

// ─── Search space ───────────────────────────────────────────────────────────

const SEARCH_SPACE = [
  ['bodyFontSize', [9.5, 10, 10.5, 11, 11.5, 12]],
  ['headerFontSize', [12, 13, 14, 15, 16]],
  ['lineHeight', [1.35, 1.45, 1.55, 1.65, 1.75]],
  ['paragraphSpacing', [3, 4, 6, 8, 10]],
  ['marginTop', [36, 45, 54, 63, 72]],
  ['marginBottom', [36, 45, 54, 63, 72]],
  ['marginLeft', [45, 54, 63, 72]],
  ['marginRight', [45, 54, 63, 72]],
  ['firstLineIndent', [0, 12, 18, 24]],
  ['illustrationMaxWidth', [0.7, 0.8, 0.85, 0.9, 0.95]],
  ['illustrationPadding', [6, 8, 10, 14, 18]],
  ['headerSpacingAbove', [8, 10, 14, 18, 22]],
  ['headerSpacingBelow', [4, 6, 8, 10]],
  ['illustrationGapThreshold', [5, 6, 8, 10, 12]],
]

// ─── Scoring ────────────────────────────────────────────────────────────────

/**
 * Score a typeset PDF by analyzing its properties.
 * Downloads the PDF and extracts metrics using pdf-lib.
 */
async function scoreConfig(config) {
  // Build query string with config overrides
  const params = new URLSearchParams({
    from: String(TEST_FROM),
    to: String(TEST_TO),
  })
  // Pass config as JSON in query (we'll add this to the route)
  const configParam = encodeURIComponent(JSON.stringify(config))
  const url = `${BASE}/api/books/${BOOK_ID}/typeset?from=${TEST_FROM}&to=${TEST_TO}&config=${configParam}`

  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(120000) })
    if (!res.ok) return { score: 0, error: `HTTP ${res.status}` }

    const pdfBytes = await res.arrayBuffer()
    const pdfSize = pdfBytes.byteLength

    // Use pdf-lib to count pages
    const { PDFDocument } = require('pdf-lib')
    const doc = await PDFDocument.load(pdfBytes)
    const pageCount = doc.getPageCount()

    const hebrewPages = TEST_TO - TEST_FROM + 1 // 26 Hebrew pages
    const pdfPagesExTitle = pageCount - 1 // subtract title page

    // S1: Page efficiency (target: ~1.0 English pages per Hebrew page)
    const ratio = pdfPagesExTitle / hebrewPages
    let S1
    if (ratio >= 0.8 && ratio <= 1.2) S1 = 1.0
    else if (ratio < 0.8) S1 = Math.max(0, ratio / 0.8)
    else S1 = Math.max(0, 1.0 - (ratio - 1.2) / 1.0)

    // S2: Font readability (based on config — target 10-12pt)
    const fontSize = config.bodyFontSize
    let S2
    if (fontSize >= 10 && fontSize <= 12) S2 = 1.0
    else if (fontSize < 10) S2 = Math.max(0, fontSize / 10)
    else S2 = Math.max(0, 1.0 - (fontSize - 12) / 4)

    // S3: PDF size as proxy for illustration quality (target: reasonable size)
    // Too small = no illustrations, too big = bloated
    const kbPerPage = (pdfSize / 1024) / pdfPagesExTitle
    let S3
    if (kbPerPage >= 50 && kbPerPage <= 500) S3 = 1.0
    else if (kbPerPage < 50) S3 = kbPerPage / 50
    else S3 = Math.max(0, 1.0 - (kbPerPage - 500) / 1000)

    // S4: Margin balance (text area ratio)
    const textW = config.pageWidth - config.marginLeft - config.marginRight
    const textH = config.pageHeight - config.marginTop - config.marginBottom
    const textRatio = (textW * textH) / (config.pageWidth * config.pageHeight)
    let S4
    if (textRatio >= 0.55 && textRatio <= 0.75) S4 = 1.0
    else if (textRatio < 0.55) S4 = textRatio / 0.55
    else S4 = Math.max(0, 1.0 - (textRatio - 0.75) / 0.25)

    // S5: Line density (estimated from font size + line height + text area)
    const linesPerPage = textH / (config.bodyFontSize * config.lineHeight)
    let S5
    if (linesPerPage >= 30 && linesPerPage <= 45) S5 = 1.0
    else if (linesPerPage < 30) S5 = linesPerPage / 30
    else S5 = Math.max(0, 1.0 - (linesPerPage - 45) / 20)

    const composite = (S1 * 3 + S2 * 2 + S3 + S4 + S5) / 8 // weight page efficiency and readability higher

    return {
      score: +composite.toFixed(4),
      pageCount,
      pdfPagesExTitle,
      ratio: +ratio.toFixed(2),
      fontSize,
      kbPerPage: +kbPerPage.toFixed(0),
      textRatio: +textRatio.toFixed(3),
      linesPerPage: +linesPerPage.toFixed(0),
      S1: +S1.toFixed(3), S2: +S2.toFixed(3), S3: +S3.toFixed(3), S4: +S4.toFixed(3), S5: +S5.toFixed(3),
    }
  } catch (err) {
    return { score: 0, error: err.message }
  }
}

// ─── Main ───────────────────────────────────────────────────────────────────

async function main() {
  fs.mkdirSync(RESULTS_DIR, { recursive: true })

  console.log('=== Typeset Autoresearch ===')
  console.log(`Server: ${BASE}`)
  console.log(`Test pages: ${TEST_FROM}-${TEST_TO} (${TEST_TO - TEST_FROM + 1} pages)`)
  console.log(`Max iterations: ${maxIterations}`)
  console.log()

  // Baseline
  console.log('Scoring baseline...')
  const baseline = await scoreConfig(DEFAULT_CONFIG)
  console.log(`Baseline: score=${baseline.score} pages=${baseline.pageCount} ratio=${baseline.ratio} fontSize=${baseline.fontSize}`)
  console.log(`  S1=${baseline.S1} S2=${baseline.S2} S3=${baseline.S3} S4=${baseline.S4} S5=${baseline.S5}`)
  console.log()

  let bestConfig = { ...DEFAULT_CONFIG }
  let bestScore = baseline.score
  let iteration = 0
  const improvements = []

  for (let round = 0; round < maxIterations; round++) {
    console.log(`\n--- Round ${round + 1}/${maxIterations} ---`)
    let roundImproved = false

    for (const [param, values] of SEARCH_SPACE) {
      if (iteration >= maxIterations * SEARCH_SPACE.length) break

      const currentValue = bestConfig[param]
      const alternatives = values.filter(v => v !== currentValue)
      if (alternatives.length === 0) continue

      process.stdout.write(`  ${param} (${currentValue}): `)

      let bestForParam = currentValue
      let bestScoreForParam = bestScore

      for (const value of alternatives) {
        iteration++
        const testConfig = { ...bestConfig, [param]: value }

        process.stdout.write(`${value}`)
        const result = await scoreConfig(testConfig)

        if (result.error) {
          process.stdout.write(`(err) `)
          continue
        }

        const delta = result.score - bestScoreForParam
        if (delta > 0.005) {
          process.stdout.write(`+${(delta * 100).toFixed(1)}% `)
          bestForParam = value
          bestScoreForParam = result.score
        } else if (delta < -0.005) {
          process.stdout.write(`-${(-delta * 100).toFixed(1)}% `)
        } else {
          process.stdout.write(`= `)
        }
      }

      if (bestForParam !== currentValue) {
        bestConfig[param] = bestForParam
        bestScore = bestScoreForParam
        improvements.push({
          round: round + 1,
          param,
          from: currentValue,
          to: bestForParam,
          score: bestScore,
        })
        process.stdout.write(`-> ${bestForParam}`)
        roundImproved = true
      } else {
        process.stdout.write(`-> keep ${currentValue}`)
      }
      console.log()
    }

    if (!roundImproved) {
      console.log('\nNo improvements this round — converged.')
      break
    }
  }

  // Final report
  console.log(`\n${'='.repeat(60)}`)
  console.log('TYPESET AUTORESEARCH RESULTS')
  console.log(`${'='.repeat(60)}`)
  console.log(`Baseline: ${baseline.score}`)
  console.log(`Best:     ${bestScore}`)
  console.log(`Improvement: ${((bestScore - baseline.score) * 100).toFixed(1)}%`)
  console.log()
  console.log('Parameter changes:')
  if (improvements.length === 0) {
    console.log('  (none — defaults are optimal)')
  } else {
    for (const imp of improvements) {
      console.log(`  [R${imp.round}] ${imp.param}: ${imp.from} -> ${imp.to} (score=${imp.score})`)
    }
  }
  console.log()
  console.log('Best config:')
  console.log(JSON.stringify(bestConfig, null, 2))

  // Save
  const outPath = path.join(RESULTS_DIR, `typeset-${Date.now()}.json`)
  fs.writeFileSync(outPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    baseline: baseline.score,
    bestScore,
    improvements,
    bestConfig,
  }, null, 2))
  console.log(`\nResults saved to: ${outPath}`)
}

main().catch(e => { console.error(e); process.exit(1) })
