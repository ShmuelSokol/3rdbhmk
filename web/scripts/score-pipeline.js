#!/usr/bin/env node
/**
 * Pipeline Quality Scoring — evaluates the current pipeline output for all pages.
 * Scores each page on 8 quality metrics (P1-P8) using ContentRegion data from the DB.
 *
 * Usage:
 *   BASE_URL=https://3rdbhmk.ksavyad.com node scripts/score-pipeline.js
 *   BASE_URL=https://3rdbhmk.ksavyad.com node scripts/score-pipeline.js --start 1 --end 50
 *   BASE_URL=https://3rdbhmk.ksavyad.com node scripts/score-pipeline.js --pages 18,42,100
 *   BASE_URL=https://3rdbhmk.ksavyad.com node scripts/score-pipeline.js --image  # include image-based scoring (slower)
 */

const BASE = process.env.BASE_URL || 'http://localhost:3000'
const BOOK_ID = process.argv.includes('--book')
  ? process.argv[process.argv.indexOf('--book') + 1]
  : 'jcqje5aut5wve5w5b8hv6fcq8'

// Parse args
const args = {
  start: 1,
  end: 367,
  pages: null,
  image: false,
  json: false,
}
for (let i = 2; i < process.argv.length; i++) {
  if (process.argv[i] === '--start') args.start = parseInt(process.argv[++i])
  if (process.argv[i] === '--end') args.end = parseInt(process.argv[++i])
  if (process.argv[i] === '--pages') args.pages = process.argv[++i].split(',').map(Number)
  if (process.argv[i] === '--image') args.image = true
  if (process.argv[i] === '--json') args.json = true
}

async function fetchJSON(url) {
  const res = await fetch(url, { signal: AbortSignal.timeout(60000) })
  return res.json()
}

/**
 * Score a single page on all metrics.
 * Returns { pageNumber, P1..P8, composite, details }
 */
async function scorePage(pageId, pageNumber) {
  const result = {
    pageId,
    pageNumber,
    P1: -1, P2: -1, P3: -1, P4: -1, P5: -1, P6: -1, P7: -1, P8: -1,
    composite: 0,
    regionCount: 0,
    details: {},
    error: null,
  }

  try {
    // Fetch pipeline data (includes regions with all coordinates + fitted data)
    const data = await fetchJSON(`${BASE}/api/pages/${pageId}/pipeline`)
    if (data.error) { result.error = data.error; return result }

    const regions = data.regions || []
    result.regionCount = regions.length
    if (regions.length === 0) {
      result.P1 = 1; result.P2 = 1; result.P3 = 1; result.P4 = 1
      result.P5 = 1; result.P6 = 1; result.P7 = 1; result.P8 = 1
      result.composite = 1
      return result
    }

    // === P1: Font Size Adequacy ===
    // fittedFontSize vs estimated Hebrew font size (from origHeight)
    const fontRatios = []
    for (const r of regions) {
      if (!r.fittedFontSize || !r.origHeight) continue
      // origHeight is in % of image. Typical page is ~3000px tall.
      // We don't know exact image dims from this API, so use ratio of
      // fittedFontSize to a reference Hebrew size estimated from origHeight
      // A region covering 5% of a 3000px image = 150px tall
      // With ~3 lines, each line is ~50px = reasonable Hebrew font
      const hebrewText = r.hebrewText || ''
      const lines = Math.max(1, Math.ceil(hebrewText.length / 40)) // rough line estimate
      const estimatedLineHeight = (r.origHeight / 100 * 3000) / lines
      if (estimatedLineHeight > 0) {
        fontRatios.push(Math.min(1, r.fittedFontSize / estimatedLineHeight))
      }
    }
    if (fontRatios.length > 0) {
      const avg = fontRatios.reduce((s, v) => s + v, 0) / fontRatios.length
      result.P1 = Math.min(1, avg)
      result.details.fontRatios = fontRatios.map(r => +r.toFixed(3))
      result.details.avgFontRatio = +avg.toFixed(3)
    } else {
      result.P1 = 1 // no font data = pass
    }

    // === P2: Space Utilization ===
    // How well does fitted text fill the expanded region?
    const utilizations = []
    for (const r of regions) {
      if (!r.fittedText || !r.fittedFontSize) continue
      const expW = r.expandedWidth ?? r.origWidth
      const expH = r.expandedHeight ?? r.origHeight
      if (!expW || !expH) continue

      // Estimate text height: wrap text at region width, count lines
      const charsPerLine = Math.max(1, Math.floor((expW / 100 * 2000) / (r.fittedFontSize * 0.55)))
      const textLines = Math.ceil(r.fittedText.length / charsPerLine)
      const textHeight = textLines * r.fittedFontSize * 1.3
      const regionHeightPx = expH / 100 * 3000
      const util = Math.min(1, textHeight / regionHeightPx)
      utilizations.push(util)
    }
    if (utilizations.length > 0) {
      const avg = utilizations.reduce((s, v) => s + v, 0) / utilizations.length
      // Score: 0.3-0.9 is ideal. Too low = wasted space, too high = overflow risk
      result.P2 = avg >= 0.3 ? Math.min(1, avg / 0.8) : avg / 0.3
      result.details.avgUtilization = +avg.toFixed(3)
    } else {
      result.P2 = 1
    }

    // === P3: Text Integrity ===
    // Was text excessively shortened? Compare fittedText to translatedText
    const integrityRatios = []
    for (const r of regions) {
      if (!r.translatedText?.trim() || !r.fittedText?.trim()) continue
      const ratio = r.fittedText.length / r.translatedText.replace(/\*\*/g, '').length
      integrityRatios.push(Math.min(1, ratio))
    }
    if (integrityRatios.length > 0) {
      const worst = Math.min(...integrityRatios)
      result.P3 = worst >= 0.8 ? 1 : worst / 0.8
      result.details.worstIntegrity = +worst.toFixed(3)
      const shortened = integrityRatios.filter(r => r < 0.8).length
      result.details.shortenedRegions = shortened
    } else {
      result.P3 = 1
    }

    // === P4: Region Overlap (expanded regions overlapping each other) ===
    const expandedRegions = regions
      .filter(r => (r.expandedX ?? r.origX) != null)
      .map(r => ({
        x: r.expandedX ?? r.origX,
        y: r.expandedY ?? r.origY,
        w: r.expandedWidth ?? r.origWidth,
        h: r.expandedHeight ?? r.origHeight,
        id: r.id,
      }))

    let maxOverlap = 0
    let overlapCount = 0
    for (let i = 0; i < expandedRegions.length; i++) {
      for (let j = i + 1; j < expandedRegions.length; j++) {
        const a = expandedRegions[i]
        const b = expandedRegions[j]
        const ox = Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x))
        const oy = Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y))
        const overlapArea = ox * oy
        const minArea = Math.min(a.w * a.h, b.w * b.h)
        const overlapFrac = minArea > 0 ? overlapArea / minArea : 0
        if (overlapFrac > 0.01) {
          overlapCount++
          maxOverlap = Math.max(maxOverlap, overlapFrac)
        }
      }
    }
    result.P4 = overlapCount === 0 ? 1 : Math.max(0, 1 - maxOverlap * 2)
    result.details.regionOverlapCount = overlapCount
    result.details.maxRegionOverlap = +maxOverlap.toFixed(3)

    // === P5: Translation Coverage ===
    const withHebrew = regions.filter(r => r.hebrewText?.trim())
    const withTranslation = withHebrew.filter(r => r.translatedText?.trim())
    result.P5 = withHebrew.length > 0 ? withTranslation.length / withHebrew.length : 1
    result.details.translatedRegions = `${withTranslation.length}/${withHebrew.length}`

    // === P6: Font Consistency ===
    // Standard deviation of font sizes across body regions (lower = better)
    const bodyFontSizes = regions
      .filter(r => r.regionType === 'body' && r.fittedFontSize)
      .map(r => r.fittedFontSize)
    if (bodyFontSizes.length >= 2) {
      const mean = bodyFontSizes.reduce((s, v) => s + v, 0) / bodyFontSizes.length
      const variance = bodyFontSizes.reduce((s, v) => s + (v - mean) ** 2, 0) / bodyFontSizes.length
      const std = Math.sqrt(variance)
      const cv = std / mean // coefficient of variation
      result.P6 = Math.max(0, 1 - cv * 2)
      result.details.fontSizeStd = +std.toFixed(1)
      result.details.fontSizeMean = +mean.toFixed(1)
      result.details.fontSizeCV = +cv.toFixed(3)
    } else {
      result.P6 = 1
    }

    // === P7: Expansion Efficiency ===
    // How much did expansion add vs original? Too little = wasted, too much = risky
    const expansionRatios = []
    for (const r of regions) {
      if (!r.expandedWidth || !r.origWidth) continue
      const origArea = r.origWidth * r.origHeight
      const expArea = r.expandedWidth * r.expandedHeight
      if (origArea > 0) {
        expansionRatios.push(expArea / origArea)
      }
    }
    if (expansionRatios.length > 0) {
      const avgExp = expansionRatios.reduce((s, v) => s + v, 0) / expansionRatios.length
      // 1.0 = no expansion (not great), 1.5-3.0 = ideal, >4.0 = possibly too aggressive
      if (avgExp < 1.2) result.P7 = avgExp / 1.2
      else if (avgExp <= 3.5) result.P7 = 1
      else result.P7 = Math.max(0, 1 - (avgExp - 3.5) / 5)
      result.details.avgExpansionRatio = +avgExp.toFixed(2)
    } else {
      result.P7 = 1
    }

    // === P8: Region Size Balance ===
    // No single region should dominate the page (>60% of total area)
    // unless it's the only region
    if (expandedRegions.length >= 2) {
      const areas = expandedRegions.map(r => r.w * r.h)
      const totalArea = areas.reduce((s, v) => s + v, 0)
      const maxFrac = Math.max(...areas) / totalArea
      result.P8 = maxFrac > 0.7 ? Math.max(0, 1 - (maxFrac - 0.7) * 3) : 1
      result.details.maxRegionAreaFrac = +maxFrac.toFixed(3)
    } else {
      result.P8 = 1
    }

    // === Composite Score ===
    const scores = [result.P1, result.P2, result.P3, result.P4, result.P5, result.P6, result.P7, result.P8]
    const validScores = scores.filter(s => s >= 0)
    result.composite = validScores.length > 0
      ? validScores.reduce((s, v) => s + v, 0) / validScores.length
      : 0

  } catch (err) {
    result.error = err.message
  }

  return result
}

async function main() {
  console.log(`Pipeline Quality Scoring | Server: ${BASE}`)
  console.log(`Fetching book pages...`)

  const book = await fetchJSON(`${BASE}/api/books/${BOOK_ID}/pipeline`)
  if (book.error) { console.error('Error:', book.error); process.exit(1) }

  let pages = book.pages
    .filter(p => p.pipelineStatus !== 'pending')
    .sort((a, b) => a.pageNumber - b.pageNumber)

  if (args.pages) {
    const pageSet = new Set(args.pages)
    pages = pages.filter(p => pageSet.has(p.pageNumber))
  } else {
    pages = pages.filter(p => p.pageNumber >= args.start && p.pageNumber <= args.end)
  }

  console.log(`Scoring ${pages.length} pages...\n`)

  const results = []
  const startTime = Date.now()

  for (let i = 0; i < pages.length; i++) {
    const page = pages[i]
    const t0 = Date.now()
    const result = await scorePage(page.id, page.pageNumber)
    const elapsed = ((Date.now() - t0) / 1000).toFixed(1)
    results.push(result)

    if (!args.json) {
      const scores = `P1=${fmt(result.P1)} P2=${fmt(result.P2)} P3=${fmt(result.P3)} P4=${fmt(result.P4)} P5=${fmt(result.P5)} P6=${fmt(result.P6)} P7=${fmt(result.P7)} P8=${fmt(result.P8)}`
      const status = result.error ? `ERR: ${result.error}` : `${result.regionCount}rgn`
      console.log(`  [${i+1}/${pages.length}] Page ${String(result.pageNumber).padStart(3)}: ${fmt(result.composite)} | ${scores} | ${status} (${elapsed}s)`)
    }

    // Progress update every 50 pages
    if (!args.json && (i + 1) % 50 === 0 && i > 0) {
      const elapsed = ((Date.now() - startTime) / 1000 / 60).toFixed(1)
      const rate = (i + 1) / parseFloat(elapsed)
      const remaining = ((pages.length - i - 1) / rate).toFixed(0)
      console.log(`  === ${elapsed}min | ${i+1}/${pages.length} scored | ~${remaining}min left ===`)
    }
  }

  // Summary
  const scored = results.filter(r => !r.error)
  if (!args.json && scored.length > 0) {
    console.log(`\n${'='.repeat(70)}`)
    console.log(`PIPELINE QUALITY SUMMARY — ${scored.length} pages scored`)
    console.log(`${'='.repeat(70)}`)

    for (const metric of ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P8']) {
      const vals = scored.map(r => r[metric]).filter(v => v >= 0)
      const avg = vals.reduce((s, v) => s + v, 0) / vals.length
      const pass = vals.filter(v => v >= 0.8).length
      const fail = vals.filter(v => v < 0.5).length
      const name = {
        P1: 'Font Size   ',
        P2: 'Utilization ',
        P3: 'Text Integ. ',
        P4: 'No Overlap  ',
        P5: 'Translation ',
        P6: 'Consistency ',
        P7: 'Expansion   ',
        P8: 'Size Balance',
      }[metric]
      console.log(`  ${metric} ${name}: avg=${fmt(avg)} | ${pass} pass | ${fail} fail`)
    }

    const composites = scored.map(r => r.composite)
    const avgComposite = composites.reduce((s, v) => s + v, 0) / composites.length
    console.log(`\n  Composite: ${fmt(avgComposite)} average`)

    // Worst pages
    const worst = [...scored].sort((a, b) => a.composite - b.composite).slice(0, 15)
    console.log(`\n  Worst 15 pages:`)
    for (const r of worst) {
      const failMetrics = ['P1','P2','P3','P4','P5','P6','P7','P8']
        .filter(m => r[m] < 0.7)
        .map(m => `${m}=${fmt(r[m])}`)
        .join(' ')
      console.log(`    Page ${String(r.pageNumber).padStart(3)}: ${fmt(r.composite)} — ${failMetrics || 'all ok'}`)
    }
  }

  // Save results
  const outPath = `${process.cwd()}/pipeline-scores.json`
  const fs = await import('fs')
  fs.writeFileSync(outPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    server: BASE,
    pagesScored: scored.length,
    avgComposite: scored.length > 0
      ? +(scored.map(r => r.composite).reduce((s,v) => s+v, 0) / scored.length).toFixed(3)
      : 0,
    pages: results,
  }, null, 2))
  console.log(`\nResults saved to ${outPath}`)

  // Also output JSON if requested
  if (args.json) {
    console.log(JSON.stringify(results))
  }
}

function fmt(v) {
  if (v < 0) return '  — '
  return v.toFixed(2).padStart(4)
}

main().catch(e => { console.error(e); process.exit(1) })
