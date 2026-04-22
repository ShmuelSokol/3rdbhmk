#!/usr/bin/env node
/**
 * Autoresearch: find crop params that best match user-locked crops.
 *
 * Ground truth: user-locked pages in public/illustration-crops.json (85 pages).
 * Score: IoU-based per-page score (area 0.6 + precision 0.2 + recall 0.2).
 *
 * Phase 1: baseline (current best-params-v2.json).
 * Phase 2: random search (200 trials).
 * Phase 3: local coordinate descent on top-N candidates.
 * Reports accuracy % at each phase so user can decide when to apply.
 */

const { extractCrops, PARAMS: DEFAULT_PARAMS } = require('./cropper-v2-blob');
const fs = require('fs');
const path = require('path');

const IMAGES = '/tmp/bhmk/jcqje5aut5wve5w5b8hv6fcq8/pages';
const CROPS_JSON = path.join(__dirname, '../../public/illustration-crops.json');
const BEST_PATH = path.join(__dirname, 'best-params-v2.json');
const LOG_PATH = path.join(__dirname, 'autoresearch-log.jsonl');

function loadGT() {
  const d = JSON.parse(fs.readFileSync(CROPS_JSON, 'utf8'));
  const locked = d._locked || [];
  const gt = {};
  for (const pn of locked) gt[pn] = d[pn] || []; // may be empty for "no crop here" pages
  return gt;
}

function iou(a, b) {
  const aL = a.leftPct, aR = aL + a.widthPct, aT = a.topPct, aB = aT + a.heightPct;
  const bL = b.leftPct, bR = bL + b.widthPct, bT = b.topPct, bB = bT + b.heightPct;
  const iL = Math.max(aL, bL), iR = Math.min(aR, bR);
  const iT = Math.max(aT, bT), iB = Math.min(aB, bB);
  if (iR <= iL || iB <= iT) return 0;
  const inter = (iR - iL) * (iB - iT);
  const union = a.widthPct * a.heightPct + b.widthPct * b.heightPct - inter;
  return union > 0 ? inter / union : 0;
}

function scorePage(auto, gt) {
  // Both empty → perfect "no crop here"
  if (!gt.length && !auto.length) return 1;
  // GT says no crop but algo produced one → penalize heavily
  if (!gt.length && auto.length) return Math.max(0, 1 - auto.length * 0.35);
  // GT has crops but algo produced none → fail
  if (gt.length && !auto.length) return 0;
  // Bipartite match by best IoU
  const matched = new Set();
  let totalIoU = 0;
  for (const g of gt) {
    let best = 0, bi = -1;
    for (let i = 0; i < auto.length; i++) {
      if (matched.has(i)) continue;
      const s = iou(g, auto[i]);
      if (s > best) { best = s; bi = i; }
    }
    if (bi >= 0 && best > 0.1) { matched.add(bi); totalIoU += best; }
  }
  const precision = auto.length > 0 ? matched.size / auto.length : 1;
  const recall = gt.length > 0 ? matched.size / gt.length : 1;
  const area = gt.length > 0 ? totalIoU / gt.length : 0;
  return area * 0.6 + precision * 0.2 + recall * 0.2;
}

async function evaluate(params, gt) {
  const pages = Object.keys(gt);
  let total = 0, count = 0;
  const details = [];
  for (const pn of pages) {
    const f = path.join(IMAGES, `page-${pn}.jpg`);
    if (!fs.existsSync(f)) continue;
    try {
      const auto = await extractCrops(f, params);
      const s = scorePage(auto, gt[pn]);
      total += s; count++;
      details.push({ pn, score: s, auto: auto.length, gt: gt[pn].length });
    } catch (e) {
      details.push({ pn, err: e.message.slice(0, 50) });
    }
  }
  return { score: count > 0 ? total / count * 100 : 0, count, details };
}

// ─── Search Space ──────────────────────────────────────────────────────────

const SPACE = {
  gridCols:        { type: 'int',   min: 80,  max: 500 },
  gridRows:        { type: 'int',   min: 100, max: 450 },
  cellThreshold:   { type: 'float', min: 0.03, max: 0.3 },
  minBlobCells:    { type: 'int',   min: 20,  max: 400 },
  minBlobWidth:    { type: 'float', min: 0.05, max: 0.3 },
  minBlobHeight:   { type: 'float', min: 0.04, max: 0.25 },
  headerZone:      { type: 'float', min: 0.05, max: 0.25 },
  headerMaxHeight: { type: 'float', min: 0.05, max: 0.25 },
  padding:         { type: 'float', min: 0.0,  max: 0.03 },
  brightnessMax:   { type: 'int',   min: 180, max: 240 },
  brightnessMin:   { type: 'int',   min: 5,   max: 80 },
  minColorRange:   { type: 'float', min: 1,   max: 40 },
  creamR:          { type: 'int',   min: 170, max: 220 },
  creamG:          { type: 'int',   min: 160, max: 210 },
  creamB:          { type: 'int',   min: 130, max: 200 },
  creamRange:      { type: 'float', min: 15,  max: 60 },
};

function randParam(name) {
  const s = SPACE[name];
  const r = s.min + Math.random() * (s.max - s.min);
  return s.type === 'int' ? Math.round(r) : Math.round(r * 1000) / 1000;
}

function randomParams(base) {
  const p = { ...base };
  for (const name of Object.keys(SPACE)) p[name] = randParam(name);
  return p;
}

function mutateParams(base, intensity = 0.2) {
  const p = { ...base };
  const keys = Object.keys(SPACE);
  const n = Math.max(1, Math.round(keys.length * intensity));
  const picks = new Set();
  while (picks.size < n) picks.add(keys[Math.floor(Math.random() * keys.length)]);
  for (const k of picks) {
    const s = SPACE[k];
    const cur = p[k];
    const range = (s.max - s.min) * 0.15;
    let next = cur + (Math.random() - 0.5) * 2 * range;
    next = Math.max(s.min, Math.min(s.max, next));
    p[k] = s.type === 'int' ? Math.round(next) : Math.round(next * 1000) / 1000;
  }
  return p;
}

function log(line) {
  fs.appendFileSync(LOG_PATH, JSON.stringify(line) + '\n');
}

async function main() {
  const gt = loadGT();
  const nPages = Object.keys(gt).length;
  console.log(`[autoresearch] ground truth: ${nPages} user-locked pages`);

  const currentBest = { ...DEFAULT_PARAMS, ...JSON.parse(fs.readFileSync(BEST_PATH, 'utf8')) };
  fs.writeFileSync(LOG_PATH, '');

  // ── Phase 1: baseline ─────────────────────────────────────────────────
  console.log('\n[phase 1] Baseline with current best-params-v2.json');
  const t0 = Date.now();
  const baseline = await evaluate(currentBest, gt);
  console.log(`  score: ${baseline.score.toFixed(2)}% on ${baseline.count} pages (${((Date.now() - t0) / 1000).toFixed(1)}s)`);
  log({ phase: 'baseline', score: baseline.score, params: currentBest });

  let best = { score: baseline.score, params: currentBest };

  // ── Phase 2: random search (explore) ──────────────────────────────────
  const N_RANDOM = parseInt(process.env.N_RANDOM || '60');
  console.log(`\n[phase 2] Random search (${N_RANDOM} trials)`);
  for (let i = 0; i < N_RANDOM; i++) {
    const p = randomParams(currentBest);
    const r = await evaluate(p, gt);
    log({ phase: 'random', trial: i, score: r.score, params: p });
    if (r.score > best.score) {
      best = { score: r.score, params: p };
      console.log(`  #${i}: ${r.score.toFixed(2)}% ← NEW BEST (was ${baseline.score.toFixed(2)}%)`);
    } else if (i % 10 === 0) {
      console.log(`  #${i}: ${r.score.toFixed(2)}% (best ${best.score.toFixed(2)}%)`);
    }
  }

  // ── Phase 3: coordinate descent around best ───────────────────────────
  const N_REFINE = parseInt(process.env.N_REFINE || '80');
  console.log(`\n[phase 3] Local refine around best (${N_REFINE} trials, decaying intensity)`);
  for (let i = 0; i < N_REFINE; i++) {
    const intensity = 0.3 * Math.exp(-i / 40);
    const p = mutateParams(best.params, intensity);
    const r = await evaluate(p, gt);
    log({ phase: 'refine', trial: i, intensity, score: r.score, params: p });
    if (r.score > best.score) {
      best = { score: r.score, params: p };
      console.log(`  #${i}: ${r.score.toFixed(2)}% ← NEW BEST (intensity ${intensity.toFixed(3)})`);
    } else if (i % 10 === 0) {
      console.log(`  #${i}: ${r.score.toFixed(2)}% (best ${best.score.toFixed(2)}%)`);
    }
  }

  // ── Summary ───────────────────────────────────────────────────────────
  console.log('\n═══ Final ═══');
  console.log(`baseline:  ${baseline.score.toFixed(2)}%`);
  console.log(`best:      ${best.score.toFixed(2)}%`);
  console.log(`improved by ${(best.score - baseline.score).toFixed(2)} points`);
  fs.writeFileSync(path.join(__dirname, 'best-params-autoresearch.json'), JSON.stringify(best.params, null, 2));
  console.log('\nwrote best-params-autoresearch.json');
}

main().catch(e => { console.error(e); process.exit(1); });
