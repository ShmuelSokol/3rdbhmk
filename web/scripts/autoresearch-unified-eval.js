#!/usr/bin/env node
/**
 * Unified Autoresearch Evaluation — 40 evals (30 layout + 10 ArtScroll)
 * Runs both eval suites, combines scores, saves results + PDFs to catalog.
 *
 * Usage:
 *   node scripts/autoresearch-unified-eval.js                         # baseline
 *   node scripts/autoresearch-unified-eval.js '{"bodyFontSize": 11}'  # with config
 *   node scripts/autoresearch-unified-eval.js --dry-run               # no catalog save
 */

const fs = require('fs');
const path = require('path');
const catalog = require('./autoresearch-catalog');

// Import eval suites
const { runEvals: runLayoutEvals } = require('./autoresearch-eval-v2');
const { runEvals: runArtscrollEvals } = require('./autoresearch-artscroll-eval');

const DRY_RUN = process.argv.includes('--dry-run');
const DESC_ARG = process.argv.find(a => a.startsWith('--desc='));
const DESCRIPTION = DESC_ARG ? DESC_ARG.split('=').slice(1).join('=') : '';

// ── Importance Weights ───────────────────────────────────────────────
// 3 = Critical (makes or breaks the book)
// 2 = Important (noticeable quality issue)
// 1 = Nice-to-have (polish)
//
// When evals conflict, higher-weight evals always win.
// Weighted score = sum(pass × weight) / sum(weight) per input.

const EVAL_WEIGHTS = {
  // Layout evals
  E1:  3,  // Hebrew chars present — core ArtScroll feature
  E2:  2,  // Words per page — density matters
  E3:  3,  // Text completeness — can't lose content
  E4:  1,  // No meta-text artifacts — minor cleanup
  E5:  1,  // No concatenation errors — minor cleanup
  E6:  2,  // No excessive whitespace — visible quality
  E7:  2,  // No orphan starts — visible quality
  E8:  3,  // Decoration present — page design identity
  E9:  1,  // Reasonable page count — sanity check
  E10: 3,  // No tiny/blank pages — critical (user complaint)
  E11: 2,  // Illustrations present — important for diagrams
  E12: 1,  // No tiny fragments — minor visual
  E13: 1,  // No blank crops — minor visual
  E14: 1,  // Illustration ratio — sanity check
  E15: 1,  // No duplicate illustrations — minor
  E16: 1,  // Tables present — structural
  E17: 1,  // No truncated cells — minor
  E18: 1,  // Consistent columns — minor
  E19: 2,  // No standalone numbers — visible quality (user complaint)
  E20: 1,  // Sequential TOC numbers — minor
  E21: 2,  // Diagram pages have images — important
  E22: 2,  // No repeated lines — visible quality
  E23: 1,  // Diagram captions concise — minor
  E24: 1,  // No label-only pages — minor
  E25: 1,  // Diagram explanatory text — minor
  E26: 2,  // Topic breaks = new pages — user requested
  E27: 1,  // Headers visually distinct — polish
  E28: 1,  // Section content cohesive — minor
  E29: 2,  // Sequential footer numbers — visible
  E30: 3,  // No empty content pages — critical (user complaint)

  // ArtScroll evals
  AS1:  3,  // Inline Hebrew — THE core ArtScroll feature
  AS2:  3,  // Ashkenazi terms — core style identity
  AS3:  2,  // Source citations — important scholarly feature
  AS4:  3,  // Hebrew quote format — core ArtScroll feature
  AS5:  1,  // No spelled-out letters — minor cleanup
  AS6:  2,  // Proper terminology — important style
  AS7:  2,  // Paragraph structure — readability
  AS8:  1,  // Bold headers — polish
  AS9:  2,  // No standalone numbers — visible quality
  AS10: 2,  // Decoration & frame — page design
};

async function runUnifiedEval(configOverride, description) {
  const experimentId = catalog.generateExperimentId();
  const startTime = Date.now();
  const git = catalog.getGitInfo();

  console.log(`\n${'═'.repeat(60)}`);
  console.log(`  UNIFIED EVAL: ${experimentId}`);
  console.log(`  Git: ${git.hash} (${git.branch})${git.dirty ? ' [dirty]' : ''}`);
  if (configOverride) console.log(`  Config: ${JSON.stringify(configOverride)}`);
  if (description) console.log(`  Description: ${description}`);
  console.log(`${'═'.repeat(60)}\n`);

  // Run layout evals (30 evals × 5 inputs = 150 max)
  console.log('--- LAYOUT EVALS (30 × 5 inputs) ---\n');
  const layoutResults = await runLayoutEvals(configOverride);

  // Save layout PDFs to catalog
  const pdfPaths = [];
  const layoutTmpDir = '/tmp/autoresearch-typeset';
  if (fs.existsSync(layoutTmpDir) && !DRY_RUN) {
    const pdfs = fs.readdirSync(layoutTmpDir).filter(f => f.endsWith('.pdf'));
    for (const pdf of pdfs) {
      const src = path.join(layoutTmpDir, pdf);
      const saved = catalog.savePdf(experimentId, `layout-${pdf.replace('.pdf', '')}`, src);
      if (saved) pdfPaths.push(saved);
    }
  }

  // Run ArtScroll evals (10 evals × 5 inputs = 50 max)
  console.log('\n--- ARTSCROLL EVALS (10 × 5 inputs) ---\n');
  const artscrollResults = await runArtscrollEvals(configOverride);

  // Save ArtScroll PDFs
  const artscrollTmpDir = '/tmp/autoresearch-artscroll';
  if (fs.existsSync(artscrollTmpDir) && !DRY_RUN) {
    const pdfs = fs.readdirSync(artscrollTmpDir).filter(f => f.endsWith('.pdf'));
    for (const pdf of pdfs) {
      const src = path.join(artscrollTmpDir, pdf);
      const saved = catalog.savePdf(experimentId, `artscroll-${pdf.replace('.pdf', '')}`, src);
      if (saved) pdfPaths.push(saved);
    }
  }

  // Build per-eval summary
  const layoutPerEval = {};
  for (const [key, val] of Object.entries(layoutResults.evalBreakdown || {})) {
    layoutPerEval[key] = val;
  }
  const artscrollPerEval = {};
  for (const [key, val] of Object.entries(artscrollResults.evalScores || {})) {
    artscrollPerEval[key] = typeof val === 'object' ? val.pass : val;
  }

  // Calculate WEIGHTED scores (importance-based)
  // Each eval's contribution = passes × weight (out of total_inputs × weight)
  let weightedTotal = 0;
  let weightedMax = 0;
  const weightedPerEval = {};

  // Layout evals
  for (const [key, passes] of Object.entries(layoutPerEval)) {
    const total = layoutResults.evalTotal?.[key] || 5;
    const weight = EVAL_WEIGHTS[key] || 1;
    weightedPerEval[key] = { passes, total, weight, weighted: passes * weight };
    weightedTotal += passes * weight;
    weightedMax += total * weight;
  }

  // ArtScroll evals
  for (const [key, val] of Object.entries(artscrollPerEval)) {
    const passes = typeof val === 'number' ? val : (val?.pass || 0);
    const evalData = artscrollResults.evalScores?.[key];
    const total = evalData?.total || 5;
    const weight = EVAL_WEIGHTS[key] || 1;
    weightedPerEval[key] = { passes, total, weight, weighted: passes * weight };
    weightedTotal += passes * weight;
    weightedMax += total * weight;
  }

  const weightedPct = weightedMax > 0 ? (weightedTotal / weightedMax * 100) : 0;

  // Also keep unweighted for reference
  const combinedTotal = layoutResults.totalScore + artscrollResults.totalScore;
  const combinedMax = layoutResults.maxScore + artscrollResults.maxScore;
  const combinedPct = combinedMax > 0 ? (combinedTotal / combinedMax * 100) : 0;

  // Check critical eval failures (weight=3 evals that fail)
  const criticalFailures = Object.entries(weightedPerEval)
    .filter(([, v]) => v.weight >= 3 && v.passes < v.total)
    .map(([key, v]) => `${key}: ${v.passes}/${v.total}`);


  const results = {
    id: experimentId,
    timestamp: new Date().toISOString(),
    status: 'complete',
    git,
    config: configOverride || {},
    description: description || '',
    scores: {
      layout: {
        total: layoutResults.totalScore,
        max: layoutResults.maxScore,
        pct: parseFloat((layoutResults.totalScore / layoutResults.maxScore * 100).toFixed(1)),
        perEval: layoutPerEval,
      },
      artscroll: {
        total: artscrollResults.totalScore,
        max: artscrollResults.maxScore,
        pct: parseFloat((artscrollResults.totalScore / artscrollResults.maxScore * 100).toFixed(1)),
        perEval: artscrollPerEval,
      },
      combined: {
        total: combinedTotal,
        max: combinedMax,
        pct: parseFloat(combinedPct.toFixed(1)),
      },
      weighted: {
        total: weightedTotal,
        max: weightedMax,
        pct: parseFloat(weightedPct.toFixed(1)),
        perEval: weightedPerEval,
        criticalFailures,
      },
    },
    weights: EVAL_WEIGHTS,
    decision: 'pending', // caller decides keep/discard based on WEIGHTED score
    pdfs: pdfPaths,
    durationMs: Date.now() - startTime,
  };

  // Print summary
  console.log(`\n${'═'.repeat(60)}`);
  console.log(`  LAYOUT:    ${layoutResults.totalScore}/${layoutResults.maxScore} (${results.scores.layout.pct}%)`);
  console.log(`  ARTSCROLL: ${artscrollResults.totalScore}/${artscrollResults.maxScore} (${results.scores.artscroll.pct}%)`);
  console.log(`  UNWEIGHTED: ${combinedTotal}/${combinedMax} (${combinedPct.toFixed(1)}%)`);
  console.log(`  WEIGHTED:  ${weightedTotal}/${weightedMax} (${weightedPct.toFixed(1)}%) ← decision score`);
  if (criticalFailures.length > 0) {
    console.log(`  ⚠ CRITICAL FAILURES: ${criticalFailures.join(', ')}`);
  }
  console.log(`  Duration:  ${(results.durationMs / 1000).toFixed(0)}s`);
  console.log(`${'═'.repeat(60)}\n`);

  // Save to catalog
  if (!DRY_RUN) {
    catalog.appendExperiment(results);
    catalog.rebuildIndex();
    console.log(`Saved to catalog: ${experimentId}`);
    console.log(`Results: ${catalog.RESULTS_DIR}`);
  }

  return results;
}

if (require.main === module) {
  const args = process.argv.slice(2).filter(a => !a.startsWith('--'));
  let config = null;
  if (args[0]) {
    try { config = JSON.parse(args[0]); } catch { console.error('Bad config JSON'); process.exit(1); }
  }

  runUnifiedEval(config, DESCRIPTION).then(r => {
    process.exit(r.scores.combined.total === r.scores.combined.max ? 0 : 1);
  }).catch(e => { console.error(e); process.exit(2); });
}

module.exports = { runUnifiedEval };
