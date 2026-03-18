#!/usr/bin/env node
/**
 * Autoresearch Pipeline Optimizer
 *
 * Automatically tunes pipeline parameters (step 2/4/5) to maximize
 * the composite quality score across all pages.
 *
 * Flow:
 *   1. Score all pages → baseline
 *   2. Pick test pages (worst N pages + random sample)
 *   3. For each parameter variation:
 *      a. Write config override to pipeline-config.json
 *      b. Re-run pipeline steps 2+4 on test pages via API
 *      c. Re-score test pages
 *      d. If improved → keep; if regressed → revert
 *   4. With best config, re-run full book
 *   5. Final scoring
 *
 * Usage:
 *   BASE_URL=http://localhost:3000 node scripts/autoresearch-pipeline.js
 *   BASE_URL=http://localhost:3000 node scripts/autoresearch-pipeline.js --dry-run
 *   BASE_URL=http://localhost:3000 node scripts/autoresearch-pipeline.js --test-pages 18,42,100
 *   BASE_URL=http://localhost:3000 node scripts/autoresearch-pipeline.js --steps 2,4
 *   BASE_URL=http://localhost:3000 node scripts/autoresearch-pipeline.js --full-rerun
 */

const fs = require('fs')
const path = require('path')

const BASE = process.env.BASE_URL || 'http://localhost:3000'
const BOOK_ID = 'jcqje5aut5wve5w5b8hv6fcq8'
const CONFIG_PATH = path.join(process.cwd(), 'pipeline-config.json')
const RESULTS_DIR = path.join(process.cwd(), 'autoresearch-results')

// Parse args
const opts = {
  dryRun: process.argv.includes('--dry-run'),
  testPages: null,
  steps: [2, 4], // which pipeline steps to re-run (skip 3/5 for speed; 3=erase, 5=fit are expensive)
  testSetSize: 30,
  fullRerun: process.argv.includes('--full-rerun'),
  maxIterations: 100,
}
for (let i = 2; i < process.argv.length; i++) {
  if (process.argv[i] === '--test-pages') opts.testPages = process.argv[++i].split(',').map(Number)
  if (process.argv[i] === '--steps') opts.steps = process.argv[++i].split(',').map(Number)
  if (process.argv[i] === '--test-size') opts.testSetSize = parseInt(process.argv[++i])
  if (process.argv[i] === '--max-iter') opts.maxIterations = parseInt(process.argv[++i])
}

// === Default config (matches hardcoded values in pipeline steps) ===
const DEFAULT_CONFIG = {
  step2: {
    zoneGapMultiplier: 3,
    zoneGapMin: 3,
    bodyGapMultiplier: 2,
    bodyGapMin: 1.5,
    headerCutoffMultiplier: 2,
    headerCutoffMin: 2,
    multiColWindow: 5,
    multiColXSep: 20,
    bodyCharThreshold: 30,
    scatteredBucketWidth: 15,
    scatteredTop2Threshold: 0.55,
    scatteredMinBuckets: 3,
    tableMergeGap: 5,
    centeredMaxWidth: 30,
    centeredBodyWidthRatio: 0.7,
    centeredSymmetryThreshold: 15,
    annotationYGap: 2,
    columnXOverlap: 0.3,
    widthTransitionThreshold: 10,
  },
  step4: {
    varianceThreshold: 200,
    colorDistThreshold: 25,
    expansionStep: 1,
    pageMargin: 2,
    buffer: 1,
    gapScanHeight: 0.3,
    gapScanVariance: 50,
    expandTableHorizontal: false,
  },
  step5: {
    minFontRatio: 0.5,
    lineHeightMultiplier: 1.3,
    fontSizeScale: 0.9,
    wideLineThreshold: 0.8,
    minAbsoluteFont: 14,
    emptyLineHeightRatio: 0.5,
  },
}

// === Parameter search space ===
// Each entry: [stepKey, paramName, [values to try]]
// Values are listed from smallest to largest
const SEARCH_SPACE = [
  // Step 2: Region detection
  ['step2', 'zoneGapMultiplier', [2, 2.5, 3, 3.5, 4]],
  ['step2', 'bodyGapMultiplier', [1.5, 2, 2.5, 3]],
  ['step2', 'headerCutoffMultiplier', [1.5, 2, 2.5, 3]],
  ['step2', 'multiColXSep', [15, 20, 25, 30]],
  ['step2', 'bodyCharThreshold', [20, 25, 30, 35, 40]],
  ['step2', 'scatteredBucketWidth', [10, 12, 15, 18, 20]],
  ['step2', 'scatteredTop2Threshold', [0.45, 0.5, 0.55, 0.6, 0.65]],
  ['step2', 'tableMergeGap', [3, 4, 5, 6, 8]],
  ['step2', 'centeredMaxWidth', [25, 28, 30, 35, 40]],
  ['step2', 'centeredBodyWidthRatio', [0.6, 0.65, 0.7, 0.75, 0.8]],
  ['step2', 'centeredSymmetryThreshold', [10, 12, 15, 18, 20]],
  ['step2', 'widthTransitionThreshold', [7, 8, 10, 12, 15]],

  // Step 4: Expansion
  ['step4', 'varianceThreshold', [150, 175, 200, 225, 250, 300]],
  ['step4', 'colorDistThreshold', [18, 20, 25, 30, 35]],
  ['step4', 'pageMargin', [1, 1.5, 2, 2.5, 3]],
  ['step4', 'buffer', [0.5, 0.75, 1, 1.25, 1.5]],
  ['step4', 'gapScanVariance', [30, 40, 50, 60, 80]],

  // Step 5: Fitting (only tested when steps include 5)
  ['step5', 'minFontRatio', [0.4, 0.45, 0.5, 0.55, 0.6]],
  ['step5', 'lineHeightMultiplier', [1.15, 1.2, 1.25, 1.3, 1.35, 1.4]],
  ['step5', 'fontSizeScale', [0.8, 0.85, 0.9, 0.95, 1.0]],
  ['step5', 'wideLineThreshold', [0.7, 0.75, 0.8, 0.85, 0.9]],
  ['step5', 'minAbsoluteFont', [10, 12, 14, 16, 18]],
]

// === Helper functions ===

async function fetchJSON(url) {
  const res = await fetch(url, { signal: AbortSignal.timeout(120000) })
  return res.json()
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(120000),
  })
  return res.json()
}

function writeConfig(config) {
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2))
}

function clearConfig() {
  try { fs.unlinkSync(CONFIG_PATH) } catch {}
}

function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj))
}

/** Score test pages and return { avgComposite, scores } */
async function scorePages(pageIds) {
  const results = []
  for (const { id, pageNumber } of pageIds) {
    try {
      const data = await fetchJSON(`${BASE}/api/pages/${id}/pipeline`)
      if (data.error) { results.push({ pageNumber, composite: 0 }); continue }

      const regions = data.regions || []
      if (regions.length === 0) { results.push({ pageNumber, composite: 1 }); continue }

      // Simplified scoring (same metrics as score-pipeline.js but condensed)
      let P4 = 1, P5 = 1, P7 = 1

      // P4: Region overlap
      const expanded = regions
        .filter(r => (r.expandedX ?? r.origX) != null)
        .map(r => ({
          x: r.expandedX ?? r.origX, y: r.expandedY ?? r.origY,
          w: r.expandedWidth ?? r.origWidth, h: r.expandedHeight ?? r.origHeight,
        }))
      let maxOverlap = 0
      for (let i = 0; i < expanded.length; i++) {
        for (let j = i + 1; j < expanded.length; j++) {
          const a = expanded[i], b = expanded[j]
          const ox = Math.max(0, Math.min(a.x+a.w, b.x+b.w) - Math.max(a.x, b.x))
          const oy = Math.max(0, Math.min(a.y+a.h, b.y+b.h) - Math.max(a.y, b.y))
          const area = ox * oy
          const min = Math.min(a.w*a.h, b.w*b.h)
          if (min > 0) maxOverlap = Math.max(maxOverlap, area/min)
        }
      }
      P4 = maxOverlap < 0.01 ? 1 : Math.max(0, 1 - maxOverlap * 2)

      // P5: Translation coverage
      const withHeb = regions.filter(r => r.hebrewText?.trim())
      const withTrans = withHeb.filter(r => r.translatedText?.trim())
      P5 = withHeb.length > 0 ? withTrans.length / withHeb.length : 1

      // P7: Expansion efficiency
      const expRatios = []
      for (const r of regions) {
        if (!r.expandedWidth || !r.origWidth) continue
        const orig = r.origWidth * r.origHeight
        const exp = r.expandedWidth * r.expandedHeight
        if (orig > 0) expRatios.push(exp / orig)
      }
      if (expRatios.length > 0) {
        const avg = expRatios.reduce((s,v) => s+v, 0) / expRatios.length
        if (avg < 1.2) P7 = avg / 1.2
        else if (avg <= 3.5) P7 = 1
        else P7 = Math.max(0, 1 - (avg - 3.5) / 5)
      }

      // Composite from key metrics (P4, P5, P7 are most affected by step 2/4 changes)
      const composite = (P4 + P5 + P7) / 3
      results.push({ pageNumber, composite, P4, P5, P7, regionCount: regions.length })
    } catch (err) {
      results.push({ pageNumber, composite: 0, error: err.message })
    }
  }

  const avg = results.length > 0
    ? results.reduce((s, r) => s + r.composite, 0) / results.length
    : 0

  return { avgComposite: avg, scores: results }
}

/** Re-run pipeline steps on pages with optional config overrides */
async function rerunPages(pageIds, steps, config) {
  let ok = 0, fail = 0
  for (const { id, pageNumber } of pageIds) {
    for (const step of steps) {
      try {
        const res = await postJSON(`${BASE}/api/pages/${id}/pipeline`, { step, config })
        if (res.error) {
          fail++
          process.stdout.write(`x`)
          break
        }
        process.stdout.write(`.`)
      } catch (err) {
        fail++
        process.stdout.write(`x`)
        break
      }
    }
    ok++
  }
  return { ok, fail }
}

async function main() {
  fs.mkdirSync(RESULTS_DIR, { recursive: true })

  console.log(`=== Autoresearch Pipeline Optimizer ===`)
  console.log(`Server: ${BASE}`)
  console.log(`Steps to optimize: ${opts.steps.join(', ')}`)
  console.log(`Dry run: ${opts.dryRun}`)
  console.log()

  // 1. Get all pages
  console.log('Fetching book pages...')
  const book = await fetchJSON(`${BASE}/api/books/${BOOK_ID}/pipeline`)
  if (book.error) { console.error('Error:', book.error); process.exit(1) }

  const allPages = book.pages
    .filter(p => p.pipelineStatus !== 'pending' && p.pipelineStatus !== 'locked')
    .sort((a, b) => a.pageNumber - b.pageNumber)
  console.log(`${allPages.length} pages available`)

  // 2. Select test pages
  let testPages
  if (opts.testPages) {
    const pageSet = new Set(opts.testPages)
    testPages = allPages.filter(p => pageSet.has(p.pageNumber))
  } else {
    // Score all pages to find the worst ones
    console.log('\nPhase 1: Baseline scoring...')
    const baseline = await scorePages(allPages)
    console.log(`Baseline composite: ${baseline.avgComposite.toFixed(3)}`)

    // Pick test set: worst N pages + some random ones for diversity
    const sorted = [...baseline.scores].sort((a, b) => a.composite - b.composite)
    const worstN = Math.min(Math.ceil(opts.testSetSize * 0.6), sorted.length)
    const randomN = opts.testSetSize - worstN
    const worstPages = sorted.slice(0, worstN).map(s => s.pageNumber)

    // Random sample from remaining
    const remaining = sorted.slice(worstN).map(s => s.pageNumber)
    const randomPages = []
    for (let i = 0; i < randomN && remaining.length > 0; i++) {
      const idx = Math.floor(Math.random() * remaining.length)
      randomPages.push(remaining.splice(idx, 1)[0])
    }

    const testPageNumbers = new Set([...worstPages, ...randomPages])
    testPages = allPages.filter(p => testPageNumbers.has(p.pageNumber))

    console.log(`Test set: ${testPages.length} pages (${worstN} worst + ${randomPages.length} random)`)
    console.log(`Worst pages: ${worstPages.slice(0, 10).join(', ')}${worstPages.length > 10 ? '...' : ''}`)

    // Save baseline
    fs.writeFileSync(
      path.join(RESULTS_DIR, 'baseline.json'),
      JSON.stringify({ timestamp: new Date().toISOString(), ...baseline }, null, 2)
    )
  }

  // 3. Score test pages at baseline
  console.log('\nScoring test pages at baseline...')
  const testBaseline = await scorePages(testPages)
  console.log(`Test set baseline: ${testBaseline.avgComposite.toFixed(3)}`)

  // 4. Optimization loop
  const bestConfig = deepClone(DEFAULT_CONFIG)
  let bestScore = testBaseline.avgComposite
  let iteration = 0
  const improvements = []

  // Filter search space to only include params for the steps we're optimizing
  const activeSteps = new Set(opts.steps.map(s => `step${s}`))
  const activeParams = SEARCH_SPACE.filter(([stepKey]) => activeSteps.has(stepKey))

  console.log(`\nPhase 2: Parameter optimization (${activeParams.length} parameters)...`)

  for (const [stepKey, paramName, values] of activeParams) {
    if (iteration >= opts.maxIterations) break

    const currentValue = bestConfig[stepKey][paramName]
    const alternatives = values.filter(v => v !== currentValue)

    if (alternatives.length === 0) continue

    process.stdout.write(`\n  ${stepKey}.${paramName} (current=${currentValue}): `)

    let bestValueForParam = currentValue
    let bestScoreForParam = bestScore

    for (const value of alternatives) {
      iteration++
      process.stdout.write(`${value}`)

      if (opts.dryRun) {
        process.stdout.write(`(skip) `)
        continue
      }

      // Write config with this parameter changed
      const testConfig = deepClone(bestConfig)
      testConfig[stepKey][paramName] = value

      // Re-run pipeline on test pages with new config
      process.stdout.write(`[run`)
      const configForApi = {}
      for (const s of opts.steps) {
        configForApi[`step${s}`] = testConfig[`step${s}`]
      }
      await rerunPages(testPages, opts.steps, configForApi)
      process.stdout.write(`]`)

      // Score
      const result = await scorePages(testPages)
      const delta = result.avgComposite - bestScoreForParam

      if (delta > 0.001) { // meaningful improvement
        process.stdout.write(`+${(delta*100).toFixed(1)}% `)
        bestValueForParam = value
        bestScoreForParam = result.avgComposite
      } else if (delta < -0.001) {
        process.stdout.write(`-${(-delta*100).toFixed(1)}% `)
      } else {
        process.stdout.write(`= `)
      }
    }

    // Apply best value for this parameter
    if (bestValueForParam !== currentValue) {
      bestConfig[stepKey][paramName] = bestValueForParam
      bestScore = bestScoreForParam
      improvements.push({
        param: `${stepKey}.${paramName}`,
        from: currentValue,
        to: bestValueForParam,
        scoreDelta: +(bestScoreForParam - testBaseline.avgComposite).toFixed(4),
      })
      process.stdout.write(`→ ${bestValueForParam}`)
    } else {
      process.stdout.write(`→ keep ${currentValue}`)
    }
  }

  // 5. Restore test pages to best config
  if (!opts.dryRun && improvements.length > 0) {
    console.log(`\n\nPhase 3: Applying best config to test pages...`)
    const configForApi = {}
    for (const s of opts.steps) {
      configForApi[`step${s}`] = bestConfig[`step${s}`]
    }
    await rerunPages(testPages, opts.steps, configForApi)
    const finalTestScore = await scorePages(testPages)
    console.log(`Final test score: ${finalTestScore.avgComposite.toFixed(3)} (was ${testBaseline.avgComposite.toFixed(3)})`)
  }

  // 6. Report
  console.log(`\n${'='.repeat(60)}`)
  console.log(`AUTORESEARCH RESULTS`)
  console.log(`${'='.repeat(60)}`)
  console.log(`Iterations: ${iteration}`)
  console.log(`Baseline score: ${testBaseline.avgComposite.toFixed(3)}`)
  console.log(`Best score: ${bestScore.toFixed(3)}`)
  console.log(`Improvement: ${((bestScore - testBaseline.avgComposite) * 100).toFixed(1)}%`)
  console.log(`\nParameter changes:`)
  if (improvements.length === 0) {
    console.log(`  (none — defaults are optimal for this test set)`)
  } else {
    for (const imp of improvements) {
      console.log(`  ${imp.param}: ${imp.from} → ${imp.to} (+${(imp.scoreDelta*100).toFixed(1)}%)`)
    }
  }

  // Save best config
  if (improvements.length > 0) {
    const configOutPath = path.join(RESULTS_DIR, 'best-config.json')
    fs.writeFileSync(configOutPath, JSON.stringify(bestConfig, null, 2))
    console.log(`\nBest config saved to: ${configOutPath}`)
    console.log(`To apply: cp ${configOutPath} pipeline-config.json`)
  }

  // Save full results
  const resultsOutPath = path.join(RESULTS_DIR, `run-${Date.now()}.json`)
  fs.writeFileSync(resultsOutPath, JSON.stringify({
    timestamp: new Date().toISOString(),
    server: BASE,
    opts,
    baseline: testBaseline.avgComposite,
    bestScore,
    improvements,
    bestConfig,
    testPages: testPages.map(p => p.pageNumber),
  }, null, 2))
  console.log(`Full results: ${resultsOutPath}`)

  // 7. Optional full rerun
  if (opts.fullRerun && improvements.length > 0 && !opts.dryRun) {
    console.log(`\nPhase 4: Full book re-run with best config...`)
    writeConfig(bestConfig)
    let completed = 0
    for (const page of allPages) {
      await rerunPages([page], opts.steps, null) // uses pipeline-config.json
      completed++
      if (completed % 20 === 0) {
        console.log(`  ${completed}/${allPages.length} pages`)
      }
    }
    clearConfig()
    console.log(`Full re-run complete: ${completed} pages`)
  }

  // Clean up config file (don't leave it on disk)
  clearConfig()
}

main().catch(e => { console.error(e); process.exit(1) })
