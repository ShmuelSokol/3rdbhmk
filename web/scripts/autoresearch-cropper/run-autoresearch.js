#!/usr/bin/env node
/**
 * Autoresearch loop for illustration cropper.
 * Tests parameter mutations against user-approved crops (ground truth).
 * Scores by IoU (intersection over union) per crop.
 */

const { extractCrops, PARAMS } = require('./cropper-skill');
const fs = require('fs');
const path = require('path');

const GROUND_TRUTH_PATH = '/tmp/user_crops_v3.json';
const IMAGES_PATH = '/tmp/bhmk/jcqje5aut5wve5w5b8hv6fcq8/pages';
const ORIGINAL_CROPS_PATH = path.join(__dirname, '../../public/illustration-crops.json');
const RESULTS_DIR = __dirname;
const MAX_EXPERIMENTS = 25;

// Load ground truth (user-edited pages only)
function loadGroundTruth() {
  const current = JSON.parse(fs.readFileSync(GROUND_TRUTH_PATH, 'utf8'));
  const original = JSON.parse(fs.readFileSync(ORIGINAL_CROPS_PATH, 'utf8'));
  const locked = current._locked || [];

  const groundTruth = {};
  for (const key of Object.keys(current)) {
    if (key === '_locked') continue;
    const isEdited = JSON.stringify(current[key]) !== JSON.stringify(original[key]);
    const isLocked = locked.includes(key);
    if (isEdited || isLocked) {
      groundTruth[key] = current[key];
    }
  }
  return groundTruth;
}

// Compute IoU between two rectangles (in 0-1 pct space)
function iou(a, b) {
  const aL = a.leftPct, aR = a.leftPct + a.widthPct, aT = a.topPct, aB = a.topPct + a.heightPct;
  const bL = b.leftPct, bR = b.leftPct + b.widthPct, bT = b.topPct, bB = b.topPct + b.heightPct;
  const iL = Math.max(aL, bL), iR = Math.min(aR, bR), iT = Math.max(aT, bT), iB = Math.min(aB, bB);
  if (iR <= iL || iB <= iT) return 0;
  const inter = (iR - iL) * (iB - iT);
  const union = a.widthPct * a.heightPct + b.widthPct * b.heightPct - inter;
  return union > 0 ? inter / union : 0;
}

// Score auto crops against ground truth for one page
function scorePage(autoCrops, gtCrops) {
  if (gtCrops.length === 0 && autoCrops.length === 0) return { countMatch: true, avgIou: 1, falsePos: 0, missed: 0, widthAcc: 1 };

  const countMatch = autoCrops.length === gtCrops.length;

  // Match auto crops to GT crops by best IoU (greedy)
  const matched = new Set();
  let totalIou = 0, matchedCount = 0, widthErrors = 0;

  for (const gt of gtCrops) {
    let bestIou = 0, bestIdx = -1;
    for (let i = 0; i < autoCrops.length; i++) {
      if (matched.has(i)) continue;
      const score = iou(gt, autoCrops[i]);
      if (score > bestIou) { bestIou = score; bestIdx = i; }
    }
    if (bestIdx >= 0 && bestIou > 0.1) {
      matched.add(bestIdx);
      totalIou += bestIou;
      matchedCount++;
      const wErr = Math.abs(autoCrops[bestIdx].widthPct - gt.widthPct) / gt.widthPct;
      if (wErr <= 0.15) widthErrors++;
    }
  }

  const avgIou = matchedCount > 0 ? totalIou / Math.max(gtCrops.length, 1) : 0;
  const falsePos = autoCrops.length - matched.size;
  const missed = gtCrops.length - matchedCount;
  const widthAcc = gtCrops.length > 0 ? widthErrors / gtCrops.length : 1;

  return { countMatch, avgIou, falsePos, missed, widthAcc };
}

// Run one experiment with given params
async function runExperiment(params, groundTruth) {
  const pages = Object.keys(groundTruth);
  let totalCountMatch = 0, totalIou = 0, totalFalsePos = 0, totalMissed = 0, totalWidthAcc = 0;

  for (const pageNum of pages) {
    const imgPath = path.join(IMAGES_PATH, `page-${pageNum}.png`);
    if (!fs.existsSync(imgPath)) continue;

    try {
      const autoCrops = await extractCrops(imgPath, params);
      const gtCrops = groundTruth[pageNum];
      const score = scorePage(autoCrops, gtCrops);

      if (score.countMatch) totalCountMatch++;
      totalIou += score.avgIou;
      totalFalsePos += score.falsePos;
      totalMissed += score.missed;
      totalWidthAcc += score.widthAcc;
    } catch (e) {
      // Page processing failed
    }
  }

  const n = pages.length;
  return {
    countMatchRate: totalCountMatch / n,
    avgIou: totalIou / n,
    avgFalsePos: totalFalsePos / n,
    avgMissed: totalMissed / n,
    widthAccRate: totalWidthAcc / n,
    // Combined score: weighted sum (IoU is most important)
    score: (totalIou / n) * 50 + (totalCountMatch / n) * 20 + (totalWidthAcc / n) * 15 + (1 - totalFalsePos / Math.max(n, 1)) * 10 + (1 - totalMissed / Math.max(n, 1)) * 5,
  };
}

// Parameter mutations to try
function generateMutations(baseParams) {
  const mutations = [];
  const tweaks = {
    rowThreshold: [0.03, 0.04, 0.05, 0.07, 0.08, 0.10],
    minBandHeight: [0.02, 0.025, 0.03, 0.04, 0.05],
    mergeGap: [0.01, 0.015, 0.025, 0.03, 0.04],
    headerMaxY: [0.08, 0.10, 0.15],
    headerMaxH: [0.06, 0.08, 0.12],
    minCropHeight: [0.08, 0.10, 0.14, 0.16],
    colThreshold: [0.03, 0.04, 0.06, 0.08, 0.10],
    minCropWidth: [0.05, 0.06, 0.10, 0.12],
    sideBySideGap: [0.03, 0.04, 0.06, 0.08, 0.10],
    padding: [0.005, 0.015, 0.02, 0.03],
    brightnessMax: [205, 210, 220, 225],
    brightnessMin: [35, 40, 50, 55],
    minColorRange: [15, 18, 22, 25, 30],
  };

  for (const [key, values] of Object.entries(tweaks)) {
    for (const val of values) {
      if (val === baseParams[key]) continue;
      mutations.push({
        description: `${key}: ${baseParams[key]} -> ${val}`,
        params: { ...baseParams, [key]: val },
      });
    }
  }

  // Shuffle for variety
  for (let i = mutations.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [mutations[i], mutations[j]] = [mutations[j], mutations[i]];
  }

  return mutations;
}

function updateDashboard(experiments, status) {
  const data = {
    skill_name: 'illustration-cropper',
    status,
    current_experiment: experiments.length - 1,
    baseline_score: experiments[0]?.score || 0,
    best_score: Math.max(...experiments.map(e => e.score)),
    experiments: experiments.map((e, i) => ({
      id: i,
      score: Math.round(e.score * 10) / 10,
      max_score: 100,
      pass_rate: Math.round(e.score * 10) / 10,
      status: e.status,
      description: e.description,
      avgIou: Math.round((e.avgIou || 0) * 1000) / 10,
    })),
  };
  fs.writeFileSync(path.join(RESULTS_DIR, 'results.json'), JSON.stringify(data, null, 2));
}

async function main() {
  console.log('Loading ground truth...');
  const groundTruth = loadGroundTruth();
  console.log('Ground truth pages:', Object.keys(groundTruth).length);

  const experiments = [];
  const changelog = [];
  let bestParams = { ...PARAMS };
  let bestScore = 0;

  // Baseline
  console.log('\n=== Experiment 0: BASELINE ===');
  const baseline = await runExperiment(PARAMS, groundTruth);
  baseline.status = 'baseline';
  baseline.description = 'original parameters';
  experiments.push(baseline);
  bestScore = baseline.score;
  console.log(`  Score: ${baseline.score.toFixed(1)}/100  IoU: ${(baseline.avgIou * 100).toFixed(1)}%  Count: ${(baseline.countMatchRate * 100).toFixed(0)}%  FP: ${baseline.avgFalsePos.toFixed(1)}  Miss: ${baseline.avgMissed.toFixed(1)}`);
  changelog.push(`## Experiment 0 — baseline\nScore: ${baseline.score.toFixed(1)}/100\nIoU: ${(baseline.avgIou * 100).toFixed(1)}%\n`);
  updateDashboard(experiments, 'running');

  // Generate mutations
  let mutations = generateMutations(bestParams);
  let expNum = 1;

  for (const mutation of mutations) {
    if (expNum > MAX_EXPERIMENTS) break;

    console.log(`\n=== Experiment ${expNum}: ${mutation.description} ===`);
    const result = await runExperiment(mutation.params, groundTruth);

    if (result.score > bestScore) {
      result.status = 'keep';
      result.description = mutation.description;
      bestScore = result.score;
      bestParams = { ...mutation.params };
      console.log(`  KEEP! Score: ${result.score.toFixed(1)}/100 (was ${bestScore.toFixed(1)})`);
      changelog.push(`## Experiment ${expNum} — KEEP\nScore: ${result.score.toFixed(1)}/100\nChange: ${mutation.description}\nIoU: ${(result.avgIou * 100).toFixed(1)}% Count: ${(result.countMatchRate * 100).toFixed(0)}%\n`);

      // Generate new mutations from improved params
      const newMutations = generateMutations(bestParams).filter(m =>
        !mutations.some(om => om.description === m.description)
      );
      mutations.push(...newMutations.slice(0, 10));
    } else {
      result.status = 'discard';
      result.description = mutation.description;
      console.log(`  Discard. Score: ${result.score.toFixed(1)}/100`);
      changelog.push(`## Experiment ${expNum} — discard\nScore: ${result.score.toFixed(1)}/100\nChange: ${mutation.description}\n`);
    }

    experiments.push(result);
    updateDashboard(experiments, 'running');
    expNum++;
  }

  // Final results
  updateDashboard(experiments, 'complete');

  console.log('\n=== FINAL RESULTS ===');
  console.log(`Baseline: ${experiments[0].score.toFixed(1)}/100`);
  console.log(`Best: ${bestScore.toFixed(1)}/100`);
  console.log(`Improvement: +${(bestScore - experiments[0].score).toFixed(1)}`);
  console.log(`Best params:`, JSON.stringify(bestParams, null, 2));
  console.log(`Experiments: ${expNum - 1} (${experiments.filter(e => e.status === 'keep').length} kept)`);

  // Save best params
  fs.writeFileSync(path.join(RESULTS_DIR, 'best-params.json'), JSON.stringify(bestParams, null, 2));
  fs.writeFileSync(path.join(RESULTS_DIR, 'changelog.md'), changelog.join('\n'));

  // Save results.tsv
  const tsv = ['experiment\tscore\tavgIou\tcountMatch\tfalsePosAvg\tmissedAvg\tstatus\tdescription'];
  experiments.forEach((e, i) => {
    tsv.push(`${i}\t${e.score.toFixed(1)}\t${((e.avgIou || 0) * 100).toFixed(1)}%\t${((e.countMatchRate || 0) * 100).toFixed(0)}%\t${(e.avgFalsePos || 0).toFixed(1)}\t${(e.avgMissed || 0).toFixed(1)}\t${e.status}\t${e.description}`);
  });
  fs.writeFileSync(path.join(RESULTS_DIR, 'results.tsv'), tsv.join('\n'));
}

main().catch(e => { console.error(e); process.exit(1); });
