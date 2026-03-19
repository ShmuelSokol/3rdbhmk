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

  // Combine scores
  const combinedTotal = layoutResults.totalScore + artscrollResults.totalScore;
  const combinedMax = layoutResults.maxScore + artscrollResults.maxScore;
  const combinedPct = combinedMax > 0 ? (combinedTotal / combinedMax * 100) : 0;

  // Build per-eval summary
  const layoutPerEval = {};
  for (const [key, val] of Object.entries(layoutResults.evalBreakdown || {})) {
    layoutPerEval[key] = val;
  }
  const artscrollPerEval = {};
  for (const [key, val] of Object.entries(artscrollResults.evalScores || {})) {
    artscrollPerEval[key] = typeof val === 'object' ? val.pass : val;
  }

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
    },
    decision: 'pending', // caller decides keep/discard
    pdfs: pdfPaths,
    durationMs: Date.now() - startTime,
  };

  // Print summary
  console.log(`\n${'═'.repeat(60)}`);
  console.log(`  LAYOUT:    ${layoutResults.totalScore}/${layoutResults.maxScore} (${results.scores.layout.pct}%)`);
  console.log(`  ARTSCROLL: ${artscrollResults.totalScore}/${artscrollResults.maxScore} (${results.scores.artscroll.pct}%)`);
  console.log(`  COMBINED:  ${combinedTotal}/${combinedMax} (${combinedPct.toFixed(1)}%)`);
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
