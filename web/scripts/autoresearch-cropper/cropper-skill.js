#!/usr/bin/env node
/**
 * Illustration Crop Extraction Skill
 *
 * Extracts illustration regions (3D renders, diagrams, floor plans) from
 * Hebrew source page images using pixel-level color density analysis.
 *
 * PARAMETERS (tunable by autoresearch):
 */
const PARAMS = {
  // Row density threshold for detecting colored bands
  rowThreshold: 0.06,
  // Minimum band height as fraction of page height
  minBandHeight: 0.035,
  // Merge gap: bands closer than this fraction are merged
  mergeGap: 0.02,
  // Header filter: bands starting above this Y% AND shorter than headerMaxH are filtered
  headerMaxY: 0.12,
  headerMaxH: 0.10,
  // Minimum crop height (fraction of page) — user deletes crops shorter than this
  minCropHeight: 0.12,
  // Column density threshold for finding horizontal extent
  colThreshold: 0.05,
  // Minimum crop width (fraction of page)
  minCropWidth: 0.08,
  // Side-by-side gap: column gap larger than this = separate illustrations
  sideBySideGap: 0.05,
  // Padding around crops (fraction of page)
  padding: 0.01,
  // Color detection: brightness thresholds
  brightnessMax: 215,
  brightnessMin: 45,
  // Color detection: minimum channel range for "colored"
  minColorRange: 20,
  // Cream filter: skip cream/beige pixels
  creamR: 195, creamG: 180, creamB: 145, creamRange: 40,
};

const sharp = require('sharp');
const fs = require('fs');

function isColored(r, g, b, P) {
  const br = (r + g + b) / 3;
  if (br > P.brightnessMax || br < P.brightnessMin) return false;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), rng = mx - mn;
  if (rng < P.minColorRange && br < 180) return false;
  if (r > P.creamR && g > P.creamG && b > P.creamB && rng < P.creamRange) return false;
  return true;
}

async function extractCrops(imagePath, params) {
  const P = { ...PARAMS, ...params };
  const buf = fs.readFileSync(imagePath);
  const meta = await sharp(buf).metadata();
  const W = meta.width, H = meta.height, ch = meta.channels || 3;
  const raw = await sharp(buf).raw().toBuffer();

  // Row density
  const rowD = new Float32Array(H);
  for (let y = 0; y < H; y++) {
    let c = 0, t = 0;
    for (let x = Math.round(W * 0.03); x < Math.round(W * 0.97); x += 2) {
      const i = (y * W + x) * ch; t++;
      if (isColored(raw[i], raw[i + 1], raw[i + 2], P)) c++;
    }
    rowD[y] = c / t;
  }

  // Smooth
  const sm = new Float32Array(H);
  for (let y = 1; y < H - 1; y++) sm[y] = (rowD[y - 1] + rowD[y] + rowD[y + 1]) / 3;
  sm[0] = rowD[0]; sm[H - 1] = rowD[H - 1];

  // Find bands
  const bands = [], minH = Math.round(H * P.minBandHeight);
  let inB = false, st = 0;
  for (let y = 0; y < H; y++) {
    if (sm[y] > P.rowThreshold) { if (!inB) { inB = true; st = y; } }
    else { if (inB) { if (y - st >= minH) bands.push({ top: st, bottom: y }); inB = false; } }
  }
  if (inB && H - st >= minH) bands.push({ top: st, bottom: H });

  // Merge close bands
  const mg = [];
  for (const b of bands) {
    if (mg.length > 0 && b.top - mg[mg.length - 1].bottom < H * P.mergeGap)
      mg[mg.length - 1].bottom = b.bottom;
    else mg.push({ ...b });
  }

  // Filter headers
  const filtered = mg.filter(b => {
    const yP = b.top / H, hP = (b.bottom - b.top) / H;
    if (yP < P.headerMaxY && hP < P.headerMaxH) return false;
    if (hP < P.minCropHeight) return false;
    return true;
  });

  const results = [];

  for (const band of filtered) {
    // Column density within this band
    const colD = new Float32Array(W);
    for (let x = 0; x < W; x += 2) {
      let c = 0, t = 0;
      for (let y = band.top; y < band.bottom; y += 3) {
        const i = (y * W + x) * ch; t++;
        if (isColored(raw[i], raw[i + 1], raw[i + 2], P)) c++;
      }
      colD[x] = t > 0 ? c / t : 0;
    }

    // Find column clusters
    const clusters = [];
    let inC = false, cSt = 0;
    for (let x = 0; x < W; x += 2) {
      if (colD[x] > P.colThreshold) { if (!inC) { inC = true; cSt = x; } }
      else { if (inC) { if (x - cSt > W * P.minCropWidth) clusters.push({ left: cSt, right: x }); inC = false; } }
    }
    if (inC && W - cSt > W * P.minCropWidth) clusters.push({ left: cSt, right: W });

    // Detect side-by-side
    const groups = [];
    if (clusters.length >= 2) {
      let merged = [clusters[0]];
      for (let i = 1; i < clusters.length; i++) {
        if (clusters[i].left - merged[merged.length - 1].right > W * P.sideBySideGap) {
          groups.push(merged);
          merged = [clusters[i]];
        } else {
          merged[merged.length - 1].right = clusters[i].right;
        }
      }
      groups.push(merged);
    }

    if (groups.length >= 2) {
      for (const group of groups) {
        const left = group[0].left, right = group[group.length - 1].right;
        const pad = Math.round(W * P.padding);
        const cL = Math.max(0, left - pad), cR = Math.min(W, right + pad);
        const cT = Math.max(0, band.top - pad), cB = Math.min(H, band.bottom + pad);
        if ((cR - cL) > W * P.minCropWidth && (cB - cT) > H * P.minCropHeight) {
          results.push({
            topPct: Math.round(cT / H * 1000) / 1000,
            leftPct: Math.round(cL / W * 1000) / 1000,
            widthPct: Math.round((cR - cL) / W * 1000) / 1000,
            heightPct: Math.round((cB - cT) / H * 1000) / 1000
          });
        }
      }
    } else {
      let minX = W, maxX = 0;
      for (let x = 0; x < W; x += 2) {
        if (colD[x] > P.colThreshold) { if (x < minX) minX = x; maxX = x; }
      }
      const pad = Math.round(W * P.padding);
      const cL = Math.max(0, minX - pad), cR = Math.min(W, maxX + pad);
      const cT = Math.max(0, band.top - pad), cB = Math.min(H, band.bottom + pad);
      if ((cR - cL) > W * P.minCropWidth && (cB - cT) > H * P.minCropHeight) {
        results.push({
          topPct: Math.round(cT / H * 1000) / 1000,
          leftPct: Math.round(cL / W * 1000) / 1000,
          widthPct: Math.round((cR - cL) / W * 1000) / 1000,
          heightPct: Math.round((cB - cT) / H * 1000) / 1000
        });
      }
    }
  }
  return results;
}

module.exports = { extractCrops, PARAMS };

// CLI mode
if (require.main === module) {
  const args = process.argv.slice(2);
  const paramsArg = args.find(a => a.startsWith('--params='));
  const params = paramsArg ? JSON.parse(paramsArg.split('=').slice(1).join('=')) : {};
  const imagePath = args.find(a => !a.startsWith('--'));
  if (!imagePath) { console.error('Usage: node cropper-skill.js <image.png> [--params=JSON]'); process.exit(1); }
  extractCrops(imagePath, params).then(crops => console.log(JSON.stringify(crops)));
}
