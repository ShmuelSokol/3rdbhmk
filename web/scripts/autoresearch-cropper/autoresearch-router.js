#!/usr/bin/env node
/**
 * Build a per-page router: pick which algo (V1, V2, V7) runs on each page
 * based on simple image features. Goal: close the gap from V2-alone (78.53%)
 * to the per-page oracle (84.74%).
 *
 * Approach: extract cheap features per page, fit decision rules via grid
 * search over single-feature thresholds. Report best router accuracy.
 */
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const { extractCrops: v1Extract } = require('./cropper-skill');
const { extractCrops: v2Extract } = require('./cropper-v2-blob');

const IMAGES = '/tmp/bhmk/jcqje5aut5wve5w5b8hv6fcq8/pages';
const CROPS_JSON = path.join(__dirname, '../../public/illustration-crops.json');
const BEST_V1 = path.join(__dirname, 'best-params.json');
const BEST_V2 = path.join(__dirname, 'best-params-autoresearch.json');

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
  const matched = new Set(); let tI = 0;
  for (const g of gt) {
    let best = 0, bi = -1;
    for (let i = 0; i < auto.length; i++) { if (matched.has(i)) continue; const s = iou(g, auto[i]); if (s > best) { best = s; bi = i; } }
    if (bi >= 0 && best > 0.1) { matched.add(bi); tI += best; }
  }
  const p = auto.length > 0 ? matched.size / auto.length : 1;
  const r = gt.length > 0 ? matched.size / gt.length : 1;
  const a = gt.length > 0 ? tI / gt.length : 0;
  return a * 0.6 + p * 0.2 + r * 0.2;
}
function isColored(r, g, b) {
  const br = (r + g + b) / 3;
  if (br > 215 || br < 45) return false;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), rng = mx - mn;
  if (rng < 20 && br < 180) return false;
  if (r > 195 && g > 180 && b > 145 && rng < 40) return false;
  return true;
}
async function pageFeatures(f) {
  const buf = fs.readFileSync(f);
  const meta = await sharp(buf).metadata();
  const W = meta.width, H = meta.height, ch = meta.channels || 3;
  const raw = await sharp(buf).raw().toBuffer();
  let coloredPx = 0, total = 0;
  // Sample coarse for speed
  for (let y = 0; y < H; y += 4) {
    for (let x = 0; x < W; x += 4) {
      const i = (y * W + x) * ch; total++;
      if (isColored(raw[i], raw[i + 1], raw[i + 2])) coloredPx++;
    }
  }
  const colorDensity = coloredPx / total;
  // Row density profile for band count
  const rowD = new Float32Array(H);
  for (let y = 0; y < H; y++) {
    let c = 0, t = 0;
    for (let x = 0; x < W; x += 3) { const i = (y * W + x) * ch; t++; if (isColored(raw[i], raw[i + 1], raw[i + 2])) c++; }
    rowD[y] = t > 0 ? c / t : 0;
  }
  let bands = 0, inB = false, st = 0, maxBandH = 0;
  for (let y = 0; y < H; y++) {
    if (rowD[y] > 0.05) { if (!inB) { inB = true; st = y; } }
    else { if (inB) { bands++; maxBandH = Math.max(maxBandH, (y - st) / H); inB = false; } }
  }
  if (inB) { bands++; maxBandH = Math.max(maxBandH, (H - st) / H); }
  return { colorDensity, bands, maxBandH };
}

function clamp(x, a, b) { return Math.max(a, Math.min(b, x)); }

async function main() {
  const d = JSON.parse(fs.readFileSync(CROPS_JSON, 'utf8'));
  const locked = d._locked || [];
  const pages = [];
  const paramsV1 = JSON.parse(fs.readFileSync(BEST_V1, 'utf8'));
  const paramsV2 = JSON.parse(fs.readFileSync(BEST_V2, 'utf8'));

  // Pull v7 from the hybrid script (copy-inline)
  async function v7(f) {
    const buf = fs.readFileSync(f);
    const meta = await sharp(buf).metadata();
    const W = meta.width, H = meta.height, ch = meta.channels || 3;
    const raw = await sharp(buf).raw().toBuffer();
    const colD = new Float32Array(W);
    for (let x = 0; x < W; x += 2) {
      let c = 0, t = 0;
      for (let y = Math.round(H * 0.1); y < Math.round(H * 0.95); y += 3) { const i = (y * W + x) * ch; t++; if (isColored(raw[i], raw[i + 1], raw[i + 2])) c++; }
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
      for (let y = 0; y < H; y++) { let c = 0, t = 0; for (let x = cl.left; x < cl.right; x += 3) { const i = (y * W + x) * ch; t++; if (isColored(raw[i], raw[i + 1], raw[i + 2])) c++; } rowD[y] = t > 0 ? c / t : 0; }
      const bands = []; let inB = false, st = 0;
      for (let y = 0; y < H; y++) { if (rowD[y] > 0.06) { if (!inB) { inB = true; st = y; } } else { if (inB) { if ((y - st) / H > 0.04) bands.push({ top: st, bottom: y }); inB = false; } } }
      if (inB && (H - st) / H > 0.04) bands.push({ top: st, bottom: H });
      for (const b of bands) {
        if (b.top / H < 0.12 && (b.bottom - b.top) / H < 0.08) continue;
        const pad = W * 0.008;
        results.push({ topPct: Math.max(0, b.top - pad) / H, leftPct: Math.max(0, cl.left - pad) / W, widthPct: Math.min(W, cl.right - cl.left + pad * 2) / W, heightPct: Math.min(H, b.bottom - b.top + pad * 2) / H });
      }
    }
    return results.filter(c => c.widthPct > 0.06 && c.heightPct > 0.035);
  }

  console.log('Extracting per-page outputs + features...');
  for (const pn of locked) {
    const f = path.join(IMAGES, `page-${pn}.jpg`);
    if (!fs.existsSync(f)) continue;
    try {
      const [o1, o2, o7, feat] = await Promise.all([
        v1Extract(f, paramsV1), v2Extract(f, paramsV2), v7(f), pageFeatures(f),
      ]);
      const gt = d[pn] || [];
      const s1 = scorePage(o1, gt), s2 = scorePage(o2, gt), s7 = scorePage(o7, gt);
      pages.push({ pn, gt, o1, o2, o7, s1, s2, s7, feat });
    } catch (e) {
      console.log('err', pn, e.message.slice(0, 80));
    }
  }
  console.log(`Pages loaded: ${pages.length}`);

  const mean = s => s.reduce((a, b) => a + b, 0) / s.length;
  const V1_ALONE = mean(pages.map(p => p.s1)) * 100;
  const V2_ALONE = mean(pages.map(p => p.s2)) * 100;
  const V7_ALONE = mean(pages.map(p => p.s7)) * 100;
  const ORACLE = mean(pages.map(p => Math.max(p.s1, p.s2, p.s7))) * 100;
  console.log(`\nBaselines:  V1=${V1_ALONE.toFixed(2)}  V2=${V2_ALONE.toFixed(2)}  V7=${V7_ALONE.toFixed(2)}  ORACLE=${ORACLE.toFixed(2)}`);

  // ─── Strategy A: Fallback cascade ─────────────────────────────────────
  console.log('\n─── Fallback cascade (V2 → V7/V1 on low-conf) ───');
  // If V2 returns 0 crops, fall back to V7 (or V1)
  function cascade(p, fallbackOrder) {
    let cur = p.o2;
    for (const fb of fallbackOrder) {
      if (cur.length === 0 || (cur.length === 1 && (cur[0].widthPct * cur[0].heightPct < 0.04))) {
        cur = p[`o${fb}`];
      }
    }
    return scorePage(cur, p.gt);
  }
  console.log(`  V2→V7:       ${mean(pages.map(p => cascade(p, [7]))) * 100}`);
  console.log(`  V2→V1:       ${mean(pages.map(p => cascade(p, [1]))) * 100}`);
  console.log(`  V2→V7→V1:    ${mean(pages.map(p => cascade(p, [7, 1]))) * 100}`);

  // ─── Strategy B: Feature-threshold router ─────────────────────────────
  console.log('\n─── Feature-threshold router (grid search) ───');
  const featNames = ['colorDensity', 'bands', 'maxBandH'];
  const algos = ['o1', 'o2', 'o7'];
  let bestRouter = { score: V2_ALONE, desc: 'V2 always' };
  for (const feat of featNames) {
    const values = pages.map(p => p.feat[feat]).sort((a, b) => a - b);
    const thresholds = [];
    for (let q = 0.1; q < 1; q += 0.05) thresholds.push(values[Math.floor(values.length * q)]);
    for (const t of thresholds) {
      for (const aLo of algos) for (const aHi of algos) {
        if (aLo === aHi) continue;
        const sc = mean(pages.map(p => {
          const out = p.feat[feat] < t ? p[aLo] : p[aHi];
          return scorePage(out, p.gt);
        })) * 100;
        if (sc > bestRouter.score) {
          bestRouter = { score: sc, desc: `${feat}<${t.toFixed(3)} ? ${aLo} : ${aHi}` };
          console.log(`  ${sc.toFixed(2)}  ${bestRouter.desc}`);
        }
      }
    }
  }
  console.log(`BEST router: ${bestRouter.score.toFixed(2)}  (${bestRouter.desc})`);

  // ─── Strategy C: Two-feature router ───────────────────────────────────
  console.log('\n─── Two-feature router (shallow decision tree) ───');
  let bestTree = { score: bestRouter.score, desc: bestRouter.desc };
  for (const f1 of featNames) {
    const v1 = pages.map(p => p.feat[f1]).sort((a, b) => a - b);
    for (let q1 = 0.2; q1 < 0.9; q1 += 0.1) {
      const t1 = v1[Math.floor(v1.length * q1)];
      for (const f2 of featNames) {
        if (f2 === f1) continue;
        const v2 = pages.map(p => p.feat[f2]).sort((a, b) => a - b);
        for (let q2 = 0.2; q2 < 0.9; q2 += 0.1) {
          const t2 = v2[Math.floor(v2.length * q2)];
          for (const A of algos) for (const B of algos) for (const C of algos) for (const D of algos) {
            const sc = mean(pages.map(p => {
              let a;
              if (p.feat[f1] < t1) a = p.feat[f2] < t2 ? p[A] : p[B];
              else a = p.feat[f2] < t2 ? p[C] : p[D];
              return scorePage(a, p.gt);
            })) * 100;
            if (sc > bestTree.score) {
              bestTree = { score: sc, desc: `${f1}<${t1.toFixed(3)} ? (${f2}<${t2.toFixed(3)}?${A}:${B}) : (${f2}<${t2.toFixed(3)}?${C}:${D})` };
            }
          }
        }
      }
    }
  }
  console.log(`BEST 2-feature: ${bestTree.score.toFixed(2)}  (${bestTree.desc})`);
  console.log(`\n═══ Summary ═══`);
  console.log(`V2 alone:         ${V2_ALONE.toFixed(2)}`);
  console.log(`Best 1-feature:   ${bestRouter.score.toFixed(2)}`);
  console.log(`Best 2-feature:   ${bestTree.score.toFixed(2)}`);
  console.log(`Per-page oracle:  ${ORACLE.toFixed(2)}`);
  fs.writeFileSync(path.join(__dirname, 'best-router.json'), JSON.stringify({ single: bestRouter, tree: bestTree }, null, 2));
}

main().catch(e => { console.error(e); process.exit(1); });
