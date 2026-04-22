#!/usr/bin/env node
/**
 * Option B: try NEW algorithm STRUCTURES (not just param tuning).
 *
 * 1. Per-page oracle (upper bound): for each page, pick the algo that
 *    scores highest — shows how much headroom exists.
 * 2. Ensemble union: combine outputs, then merge overlapping crops.
 * 3. Ensemble IoU-cluster: group overlapping candidates across algos,
 *    return cluster centroid (like non-max suppression but averaged).
 * 4. Agreement filter: keep only crops that 2+ algos agree on.
 * 5. Per-algo best selection via simple heuristics (page color density).
 */

const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

// Reuse algos from race script
const race = path.join(__dirname, 'race-10-algorithms.js');
// The race file defines algos as local functions; load them by requiring fresh modules.
// We'll rebuild the exact algo pipelines here with the tuned V2 params.
const { extractCrops: v2Extract } = require('./cropper-v2-blob');
const { extractCrops: v1Extract } = require('./cropper-skill');

const IMAGES = '/tmp/bhmk/jcqje5aut5wve5w5b8hv6fcq8/pages';
const CROPS_JSON = path.join(__dirname, '../../public/illustration-crops.json');
const BEST_V1 = path.join(__dirname, 'best-params.json');
const BEST_V2 = path.join(__dirname, 'best-params-autoresearch.json'); // tuned from phase 3
const LOG = path.join(__dirname, 'hybrid-log.jsonl');

function loadGT() {
  const d = JSON.parse(fs.readFileSync(CROPS_JSON, 'utf8'));
  const locked = d._locked || [];
  const gt = {};
  for (const pn of locked) gt[pn] = d[pn] || [];
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
  if (!gt.length && !auto.length) return 1;
  if (!gt.length && auto.length) return Math.max(0, 1 - auto.length * 0.35);
  if (gt.length && !auto.length) return 0;
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

// ─── Pixel helpers for bespoke algos ──────────────────────────────────────

function isColored(r, g, b) {
  const br = (r + g + b) / 3;
  if (br > 215 || br < 45) return false;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), rng = mx - mn;
  if (rng < 20 && br < 180) return false;
  if (r > 195 && g > 180 && b > 145 && rng < 40) return false;
  return true;
}
async function getPixels(f) {
  const buf = fs.readFileSync(f);
  const meta = await sharp(buf).metadata();
  const W = meta.width, H = meta.height, ch = meta.channels || 3;
  const raw = await sharp(buf).raw().toBuffer();
  return { raw, W, H, ch, buf };
}

// V7 column-first (copied from race, as simple dependency-free function)
async function v7Extract(f) {
  const { raw, W, H, ch } = await getPixels(f);
  const colD = new Float32Array(W);
  for (let x = 0; x < W; x += 2) {
    let c = 0, t = 0;
    for (let y = Math.round(H * 0.1); y < Math.round(H * 0.95); y += 3) {
      const i = (y * W + x) * ch; t++;
      if (isColored(raw[i], raw[i + 1], raw[i + 2])) c++;
    }
    colD[x] = t > 0 ? c / t : 0;
  }
  const clusters = []; let inC = false, cSt = 0;
  for (let x = 0; x < W; x += 2) {
    if (colD[x] > 0.04) { if (!inC) { inC = true; cSt = x; } }
    else { if (inC) { if ((x - cSt) / W > 0.06) clusters.push({ left: cSt, right: x }); inC = false; } }
  }
  if (inC && (W - cSt) / W > 0.06) clusters.push({ left: cSt, right: W });
  const results = [];
  for (const cl of clusters) {
    const rowD = new Float32Array(H);
    for (let y = 0; y < H; y++) {
      let c = 0, t = 0;
      for (let x = cl.left; x < cl.right; x += 3) {
        const i = (y * W + x) * ch; t++;
        if (isColored(raw[i], raw[i + 1], raw[i + 2])) c++;
      }
      rowD[y] = t > 0 ? c / t : 0;
    }
    const bands = []; let inB = false, st = 0;
    for (let y = 0; y < H; y++) {
      if (rowD[y] > 0.06) { if (!inB) { inB = true; st = y; } }
      else { if (inB) { if ((y - st) / H > 0.04) bands.push({ top: st, bottom: y }); inB = false; } }
    }
    if (inB && (H - st) / H > 0.04) bands.push({ top: st, bottom: H });
    for (const b of bands) {
      if (b.top / H < 0.12 && (b.bottom - b.top) / H < 0.08) continue;
      const pad = W * 0.008;
      results.push({
        topPct: Math.max(0, b.top - pad) / H,
        leftPct: Math.max(0, cl.left - pad) / W,
        widthPct: Math.min(W, cl.right - cl.left + pad * 2) / W,
        heightPct: Math.min(H, b.bottom - b.top + pad * 2) / H,
      });
    }
  }
  return results.filter(c => c.widthPct > 0.06 && c.heightPct > 0.035);
}

// ─── Ensemble strategies ─────────────────────────────────────────────────

/** Merge crops that have IoU > threshold (union, take bounding box). */
function mergeOverlapping(crops, minIoU = 0.3) {
  const used = new Array(crops.length).fill(false);
  const out = [];
  for (let i = 0; i < crops.length; i++) {
    if (used[i]) continue;
    let cur = { ...crops[i] };
    used[i] = true;
    for (let j = i + 1; j < crops.length; j++) {
      if (used[j]) continue;
      if (iou(cur, crops[j]) > minIoU) {
        // Union bbox
        const L = Math.min(cur.leftPct, crops[j].leftPct);
        const T = Math.min(cur.topPct, crops[j].topPct);
        const R = Math.max(cur.leftPct + cur.widthPct, crops[j].leftPct + crops[j].widthPct);
        const B = Math.max(cur.topPct + cur.heightPct, crops[j].topPct + crops[j].heightPct);
        cur = { leftPct: L, topPct: T, widthPct: R - L, heightPct: B - T };
        used[j] = true;
      }
    }
    out.push(cur);
  }
  return out;
}

/** Cluster crops by IoU and return per-cluster centroid (averaged bbox). */
function clusterCentroid(crops, minIoU = 0.3) {
  const used = new Array(crops.length).fill(false);
  const out = [];
  for (let i = 0; i < crops.length; i++) {
    if (used[i]) continue;
    const cluster = [crops[i]];
    used[i] = true;
    for (let j = i + 1; j < crops.length; j++) {
      if (used[j]) continue;
      if (iou(crops[i], crops[j]) > minIoU) { cluster.push(crops[j]); used[j] = true; }
    }
    const avg = { leftPct: 0, topPct: 0, widthPct: 0, heightPct: 0, _n: cluster.length };
    for (const c of cluster) { avg.leftPct += c.leftPct; avg.topPct += c.topPct; avg.widthPct += c.widthPct; avg.heightPct += c.heightPct; }
    avg.leftPct /= cluster.length; avg.topPct /= cluster.length;
    avg.widthPct /= cluster.length; avg.heightPct /= cluster.length;
    out.push(avg);
  }
  return out;
}

/** Keep only crops that at least K algorithms agree on. */
function agreementFilter(perAlgoCrops, K, minIoU = 0.25) {
  // Flatten to (algoIdx, crop) pairs
  const flat = [];
  for (let a = 0; a < perAlgoCrops.length; a++) {
    for (const c of perAlgoCrops[a]) flat.push({ algo: a, crop: c });
  }
  const out = [];
  const used = new Array(flat.length).fill(false);
  for (let i = 0; i < flat.length; i++) {
    if (used[i]) continue;
    const algos = new Set([flat[i].algo]);
    const cluster = [flat[i].crop];
    used[i] = true;
    for (let j = i + 1; j < flat.length; j++) {
      if (used[j]) continue;
      if (iou(flat[i].crop, flat[j].crop) > minIoU) { algos.add(flat[j].algo); cluster.push(flat[j].crop); used[j] = true; }
    }
    if (algos.size >= K) {
      // Union bbox across the cluster
      let L = 1, T = 1, R = 0, B = 0;
      for (const c of cluster) {
        L = Math.min(L, c.leftPct); T = Math.min(T, c.topPct);
        R = Math.max(R, c.leftPct + c.widthPct); B = Math.max(B, c.topPct + c.heightPct);
      }
      out.push({ leftPct: L, topPct: T, widthPct: R - L, heightPct: B - T });
    }
  }
  return out;
}

// ─── Main evaluation ─────────────────────────────────────────────────────

async function main() {
  const gt = loadGT();
  const pages = Object.keys(gt);
  const paramsV1 = JSON.parse(fs.readFileSync(BEST_V1, 'utf8'));
  const paramsV2 = JSON.parse(fs.readFileSync(BEST_V2, 'utf8'));
  fs.writeFileSync(LOG, '');
  console.log(`[hybrid] ${pages.length} pages, running 3 base algos + 4 ensemble strategies`);

  // Cache per-algo outputs
  const v1Out = {}, v2Out = {}, v7Out = {};
  const t0 = Date.now();
  let done = 0;
  for (const pn of pages) {
    const f = path.join(IMAGES, `page-${pn}.jpg`);
    if (!fs.existsSync(f)) continue;
    try {
      v1Out[pn] = await v1Extract(f, paramsV1);
      v2Out[pn] = await v2Extract(f, paramsV2);
      v7Out[pn] = await v7Extract(f);
      done++;
    } catch (e) { /* skip */ }
  }
  console.log(`Base extraction: ${done}/${pages.length} pages in ${((Date.now() - t0) / 1000).toFixed(1)}s`);

  function avgScore(predFn) {
    let tot = 0, n = 0;
    for (const pn of pages) {
      if (!v2Out[pn]) continue;
      tot += scorePage(predFn(pn), gt[pn]);
      n++;
    }
    return n > 0 ? tot / n * 100 : 0;
  }

  // Individual
  console.log('\n─── Individual algos ───');
  console.log('V1 (row+col):    ', avgScore(pn => v1Out[pn] || []).toFixed(2));
  console.log('V2 (blob):       ', avgScore(pn => v2Out[pn] || []).toFixed(2));
  console.log('V7 (col-first):  ', avgScore(pn => v7Out[pn] || []).toFixed(2));

  // Oracle upper bound (best per-page)
  console.log('\n─── Oracles (upper bounds) ───');
  let oracleScore = 0, n = 0;
  const algoCounts = { v1: 0, v2: 0, v7: 0 };
  for (const pn of pages) {
    if (!v2Out[pn]) continue;
    const s1 = scorePage(v1Out[pn] || [], gt[pn]);
    const s2 = scorePage(v2Out[pn] || [], gt[pn]);
    const s7 = scorePage(v7Out[pn] || [], gt[pn]);
    const best = Math.max(s1, s2, s7);
    if (best === s1) algoCounts.v1++; else if (best === s2) algoCounts.v2++; else algoCounts.v7++;
    oracleScore += best;
    n++;
  }
  console.log('per-page oracle (best of 3):  ', (oracleScore / n * 100).toFixed(2));
  console.log('  algos picked:', algoCounts);

  // Ensemble: union with overlap merge (various IoU thresholds)
  console.log('\n─── Ensemble: union+merge (all 3 algos) ───');
  for (const mI of [0.2, 0.3, 0.4, 0.5]) {
    const sc = avgScore(pn => mergeOverlapping([...(v1Out[pn] || []), ...(v2Out[pn] || []), ...(v7Out[pn] || [])], mI));
    console.log(`  minIoU=${mI}:  ${sc.toFixed(2)}`);
  }

  // Ensemble: cluster centroid
  console.log('\n─── Ensemble: cluster centroid ───');
  for (const mI of [0.2, 0.3, 0.4]) {
    const sc = avgScore(pn => clusterCentroid([...(v1Out[pn] || []), ...(v2Out[pn] || []), ...(v7Out[pn] || [])], mI));
    console.log(`  minIoU=${mI}:  ${sc.toFixed(2)}`);
  }

  // Ensemble: agreement filter (K of 3 algos must agree)
  console.log('\n─── Ensemble: K-of-3 agreement ───');
  for (const K of [1, 2, 3]) {
    for (const mI of [0.2, 0.3]) {
      const sc = avgScore(pn => agreementFilter([v1Out[pn] || [], v2Out[pn] || [], v7Out[pn] || []], K, mI));
      console.log(`  K=${K} minIoU=${mI}:  ${sc.toFixed(2)}`);
    }
  }

  // V2+V7 only (drop V1 which scored lowest in prior runs)
  console.log('\n─── Ensemble: V2+V7 only ───');
  for (const mI of [0.2, 0.3, 0.4]) {
    const sc = avgScore(pn => mergeOverlapping([...(v2Out[pn] || []), ...(v7Out[pn] || [])], mI));
    console.log(`  V2+V7 merge minIoU=${mI}:  ${sc.toFixed(2)}`);
  }
  for (const K of [1, 2]) {
    const sc = avgScore(pn => agreementFilter([v2Out[pn] || [], v7Out[pn] || []], K, 0.3));
    console.log(`  V2+V7 agreement K=${K}:  ${sc.toFixed(2)}`);
  }
}

main().catch(e => { console.error(e); process.exit(1); });
