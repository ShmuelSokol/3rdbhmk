#!/usr/bin/env node
/**
 * Autoresearch Round 3: New Feature Optimization
 * Tests config variations for illustration sizing, table formatting,
 * topic breaks, orphan prevention, and caption styling.
 *
 * 20 experiments testing new config parameters.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const EVAL_SCRIPT = path.join(__dirname, 'autoresearch-typeset-eval.js');
const RESULTS_DIR = path.join(__dirname, '..', '.claude', 'skills', 'artscrolltranslationsandplacements', 'autoresearch-artscroll');

// Experiments: each tests ONE config change against the current default
const EXPERIMENTS = [
  // Illustration sizing (now with border trimming, test larger illustrations)
  { id: 21, config: { illustrationMaxWidth: 0.90 }, desc: 'illustrationMaxWidth 0.90 — wider illustrations with border trimming' },
  { id: 22, config: { illustrationMaxWidth: 0.95 }, desc: 'illustrationMaxWidth 0.95 — near-full-width illustrations' },
  { id: 23, config: { illustrationPadding: 6 }, desc: 'illustrationPadding 6 — tighter illustration spacing' },
  { id: 24, config: { illustrationPadding: 14 }, desc: 'illustrationPadding 14 — more illustration breathing room' },
  { id: 25, config: { illustrationGapThreshold: 6 }, desc: 'illustrationGapThreshold 6 — detect smaller illustration gaps' },
  { id: 26, config: { illustrationGapThreshold: 10 }, desc: 'illustrationGapThreshold 10 — only detect larger illustration gaps' },

  // Font/spacing combos optimized for new features
  { id: 27, config: { bodyFontSize: 10.5, lineHeight: 1.5 }, desc: 'bodyFontSize 10.5 + lineHeight 1.5 — slightly smaller text' },
  { id: 28, config: { bodyFontSize: 11.5, lineHeight: 1.45 }, desc: 'bodyFontSize 11.5 + lineHeight 1.45 — larger text, tighter lines' },
  { id: 29, config: { bodyFontSize: 11, lineHeight: 1.45 }, desc: 'bodyFontSize 11 + lineHeight 1.45 — current font, tighter lines' },
  { id: 30, config: { bodyFontSize: 11, lineHeight: 1.55 }, desc: 'bodyFontSize 11 + lineHeight 1.55 — current font, looser lines' },

  // Margin experiments (affect page density and topic break blank space)
  { id: 31, config: { marginLeft: 48, marginRight: 48 }, desc: 'marginLeft/Right 48 — wider text area' },
  { id: 32, config: { marginLeft: 60, marginRight: 60 }, desc: 'marginLeft/Right 60 — narrower text column' },
  { id: 33, config: { marginTop: 48, marginBottom: 48 }, desc: 'marginTop/Bottom 48 — taller text area' },

  // Header spacing (affects topic breaks)
  { id: 34, config: { headerSpacingAbove: 18, headerSpacingBelow: 8 }, desc: 'more header spacing — better topic separation' },
  { id: 35, config: { headerSpacingAbove: 10, headerSpacingBelow: 4 }, desc: 'less header spacing — more compact topics' },

  // Paragraph spacing variations
  { id: 36, config: { paragraphSpacing: 6 }, desc: 'paragraphSpacing 6 — tighter paragraphs' },
  { id: 37, config: { paragraphSpacing: 10 }, desc: 'paragraphSpacing 10 — more paragraph separation' },

  // Indent variations
  { id: 38, config: { firstLineIndent: 12 }, desc: 'firstLineIndent 12 — smaller indent' },
  { id: 39, config: { firstLineIndent: 24 }, desc: 'firstLineIndent 24 — deeper indent' },

  // Combined best from previous + new features
  { id: 40, config: { illustrationMaxWidth: 0.92, illustrationPadding: 8, bodyFontSize: 11, lineHeight: 1.48, paragraphSpacing: 8 }, desc: 'balanced combo — optimized for new features' },
];

function runExperiment(exp) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`EXPERIMENT ${exp.id}: ${exp.desc}`);
  console.log(`Config: ${JSON.stringify(exp.config)}`);
  console.log('='.repeat(60));

  try {
    const output = execSync(
      `TYPESET_URL=http://localhost:3001 node "${EVAL_SCRIPT}" '${JSON.stringify(exp.config)}'`,
      { encoding: 'utf8', timeout: 600000, cwd: path.join(__dirname, '..') }
    );

    // Parse results
    const totalMatch = output.match(/TOTAL:\s+(\d+)\/(\d+)\s+\((\d+\.\d+)%\)/);
    if (!totalMatch) {
      console.log('Could not parse results');
      return { ...exp, score: 0, maxScore: 24, passRate: 0, status: 'error' };
    }

    const score = parseInt(totalMatch[1]);
    const maxScore = parseInt(totalMatch[2]);
    const passRate = parseFloat(totalMatch[3]);

    // Extract worst blank strip info
    const stripMatch = output.match(/Worst interior blank:\s+([\d.]+)%/g);
    let worstStrip = 0;
    if (stripMatch) {
      for (const m of stripMatch) {
        const val = parseFloat(m.match(/([\d.]+)%/)[1]);
        if (val > worstStrip) worstStrip = val;
      }
    }

    const status = score === maxScore ? 'keep' : 'discard';
    console.log(`\nRESULT: ${score}/${maxScore} (${passRate}%) — ${status.toUpperCase()}`);
    console.log(`Worst interior blank: ${worstStrip}%`);

    return { ...exp, score, maxScore, passRate, status, worstStrip };
  } catch (e) {
    // Check if the eval output is in stderr/stdout
    const output = (e.stdout || '') + (e.stderr || '');
    const totalMatch = output.match(/TOTAL:\s+(\d+)\/(\d+)\s+\((\d+\.\d+)%\)/);
    if (totalMatch) {
      const score = parseInt(totalMatch[1]);
      const maxScore = parseInt(totalMatch[2]);
      const passRate = parseFloat(totalMatch[3]);
      const stripMatch = output.match(/Worst interior blank:\s+([\d.]+)%/g);
      let worstStrip = 0;
      if (stripMatch) {
        for (const m of stripMatch) {
          const val = parseFloat(m.match(/([\d.]+)%/)[1]);
          if (val > worstStrip) worstStrip = val;
        }
      }
      const status = score === maxScore ? 'keep' : 'discard';
      console.log(`\nRESULT: ${score}/${maxScore} (${passRate}%) — ${status.toUpperCase()}`);
      return { ...exp, score, maxScore, passRate, status, worstStrip };
    }
    console.error(`Experiment ${exp.id} failed: ${e.message}`);
    return { ...exp, score: 0, maxScore: 24, passRate: 0, status: 'error', worstStrip: 0 };
  }
}

async function main() {
  console.log('Autoresearch Round 3: New Feature Optimization');
  console.log(`Running ${EXPERIMENTS.length} experiments...\n`);

  // First run baseline (current config, no overrides)
  console.log('Running baseline (current defaults)...');
  const baseline = runExperiment({ id: 'baseline', config: {}, desc: 'current defaults (round 3 baseline)' });

  const results = [baseline];

  for (const exp of EXPERIMENTS) {
    const result = runExperiment(exp);
    results.push(result);
  }

  // Summary
  console.log('\n\n' + '='.repeat(60));
  console.log('ROUND 3 SUMMARY');
  console.log('='.repeat(60));

  const kept = results.filter(r => r.status === 'keep');
  const discarded = results.filter(r => r.status === 'discard');

  console.log(`\nTotal: ${results.length} experiments`);
  console.log(`Kept (24/24): ${kept.length}`);
  console.log(`Discarded: ${discarded.length}`);

  // Sort kept by worst strip (lower is better)
  kept.sort((a, b) => (a.worstStrip || 99) - (b.worstStrip || 99));

  console.log('\nBest configs (all maintain 24/24):');
  for (const r of kept.slice(0, 5)) {
    console.log(`  Exp ${r.id}: worst strip ${r.worstStrip?.toFixed(1)}% — ${r.desc}`);
  }

  // Write results
  const outPath = path.join(RESULTS_DIR, 'round3-results.json');
  fs.writeFileSync(outPath, JSON.stringify({
    round: 3,
    baseline: baseline,
    experiments: results,
    kept: kept.map(r => ({ id: r.id, config: r.config, worstStrip: r.worstStrip, desc: r.desc })),
    discarded: discarded.map(r => ({ id: r.id, config: r.config, passRate: r.passRate, desc: r.desc })),
  }, null, 2));
  console.log(`\nResults saved to ${outPath}`);

  // Also write TSV
  const tsvPath = path.join(RESULTS_DIR, 'round3-results.tsv');
  const tsvLines = ['experiment\tscore\tmax_score\tpass_rate\tstatus\tworst_strip\tdescription'];
  for (const r of results) {
    tsvLines.push(`${r.id}\t${r.score}\t${r.maxScore}\t${r.passRate}%\t${r.status}\t${r.worstStrip?.toFixed(1) || 'N/A'}%\t${r.desc}`);
  }
  fs.writeFileSync(tsvPath, tsvLines.join('\n') + '\n');
  console.log(`TSV saved to ${tsvPath}`);
}

main().catch(console.error);
