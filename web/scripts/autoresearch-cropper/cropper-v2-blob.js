#!/usr/bin/env node
/**
 * V2 Illustration Cropper — 2D Blob Detection
 * 
 * Instead of row-then-column analysis, this:
 * 1. Creates a binary "color mask" of the full page
 * 2. Downsamples to a grid (e.g., 100x140 cells)
 * 3. Finds connected components (blobs) of colored cells
 * 4. Filters blobs by size, aspect ratio, position
 * 5. Returns bounding boxes of remaining blobs
 */

const sharp = require('sharp');
const fs = require('fs');

const PARAMS = {
  // Grid resolution for blob detection
  gridCols: 100,
  gridRows: 140,
  // Minimum fraction of colored pixels in a cell to count as "filled"
  cellThreshold: 0.08,
  // Minimum blob size in grid cells
  minBlobCells: 40,
  // Minimum blob dimensions as fraction of page
  minBlobWidth: 0.08,
  minBlobHeight: 0.06,
  // Header filter: blobs entirely within top N% of page
  headerZone: 0.11,
  // Maximum blob height for header filter (short + at top = header bar)
  headerMaxHeight: 0.08,
  // Padding around blob bounding box (fraction of page)
  padding: 0.008,
  // Color detection
  brightnessMax: 215,
  brightnessMin: 45,
  minColorRange: 20,
  creamR: 195, creamG: 180, creamB: 145, creamRange: 40,
};

function isColored(r, g, b, P) {
  const br = (r + g + b) / 3;
  if (br > P.brightnessMax || br < P.brightnessMin) return false;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), rng = mx - mn;
  if (rng < P.minColorRange && br < 180) return false;
  if (r > P.creamR && g > P.creamG && b > P.creamB && rng < P.creamRange) return false;
  return true;
}

// Union-Find for connected components
class UnionFind {
  constructor(n) { this.parent = Array.from({length: n}, (_, i) => i); this.rank = new Uint8Array(n); }
  find(x) { while (this.parent[x] !== x) { this.parent[x] = this.parent[this.parent[x]]; x = this.parent[x]; } return x; }
  union(a, b) {
    a = this.find(a); b = this.find(b);
    if (a === b) return;
    if (this.rank[a] < this.rank[b]) [a, b] = [b, a];
    this.parent[b] = a;
    if (this.rank[a] === this.rank[b]) this.rank[a]++;
  }
}

async function extractCrops(imagePath, params) {
  const P = { ...PARAMS, ...params };
  const buf = fs.readFileSync(imagePath);
  const meta = await sharp(buf).metadata();
  const W = meta.width, H = meta.height, ch = meta.channels || 3;
  const raw = await sharp(buf).raw().toBuffer();

  const GC = P.gridCols, GR = P.gridRows;
  const cellW = W / GC, cellH = H / GR;

  // Build grid: each cell = fraction of colored pixels
  const grid = new Float32Array(GR * GC);
  for (let gr = 0; gr < GR; gr++) {
    for (let gc = 0; gc < GC; gc++) {
      const y0 = Math.round(gr * cellH), y1 = Math.min(H, Math.round((gr + 1) * cellH));
      const x0 = Math.round(gc * cellW), x1 = Math.min(W, Math.round((gc + 1) * cellW));
      let colored = 0, total = 0;
      for (let y = y0; y < y1; y += 2) {
        for (let x = x0; x < x1; x += 2) {
          const i = (y * W + x) * ch;
          total++;
          if (isColored(raw[i], raw[i + 1], raw[i + 2], P)) colored++;
        }
      }
      grid[gr * GC + gc] = total > 0 ? colored / total : 0;
    }
  }

  // Binary mask: cell is "filled" if above threshold
  const mask = new Uint8Array(GR * GC);
  for (let i = 0; i < GR * GC; i++) mask[i] = grid[i] >= P.cellThreshold ? 1 : 0;

  // Connected components via Union-Find
  const uf = new UnionFind(GR * GC);
  for (let r = 0; r < GR; r++) {
    for (let c = 0; c < GC; c++) {
      if (!mask[r * GC + c]) continue;
      // Connect to right neighbor
      if (c + 1 < GC && mask[r * GC + c + 1]) uf.union(r * GC + c, r * GC + c + 1);
      // Connect to bottom neighbor
      if (r + 1 < GR && mask[(r + 1) * GC + c]) uf.union(r * GC + c, (r + 1) * GC + c);
      // Connect diagonals for better blob merging
      if (r + 1 < GR && c + 1 < GC && mask[(r + 1) * GC + c + 1]) uf.union(r * GC + c, (r + 1) * GC + c + 1);
      if (r + 1 < GR && c > 0 && mask[(r + 1) * GC + c - 1]) uf.union(r * GC + c, (r + 1) * GC + c - 1);
    }
  }

  // Collect blob bounding boxes
  const blobs = new Map(); // root -> {minR, maxR, minC, maxC, count}
  for (let r = 0; r < GR; r++) {
    for (let c = 0; c < GC; c++) {
      if (!mask[r * GC + c]) continue;
      const root = uf.find(r * GC + c);
      if (!blobs.has(root)) blobs.set(root, { minR: r, maxR: r, minC: c, maxC: c, count: 0 });
      const b = blobs.get(root);
      b.minR = Math.min(b.minR, r);
      b.maxR = Math.max(b.maxR, r);
      b.minC = Math.min(b.minC, c);
      b.maxC = Math.max(b.maxC, c);
      b.count++;
    }
  }

  // Convert to page coordinates and filter
  const results = [];
  for (const [, blob] of blobs) {
    if (blob.count < P.minBlobCells) continue;

    const topPct = blob.minR / GR;
    const leftPct = blob.minC / GC;
    const widthPct = (blob.maxC - blob.minC + 1) / GC;
    const heightPct = (blob.maxR - blob.minR + 1) / GR;

    // Filter too small
    if (widthPct < P.minBlobWidth || heightPct < P.minBlobHeight) continue;

    // Filter header bars (short + at top of page)
    if (topPct < P.headerZone && heightPct < P.headerMaxHeight) continue;

    // Apply padding
    const pad = P.padding;
    const finalTop = Math.max(0, topPct - pad);
    const finalLeft = Math.max(0, leftPct - pad);
    const finalW = Math.min(1 - finalLeft, widthPct + pad * 2);
    const finalH = Math.min(1 - finalTop, heightPct + pad * 2);

    results.push({
      topPct: Math.round(finalTop * 1000) / 1000,
      leftPct: Math.round(finalLeft * 1000) / 1000,
      widthPct: Math.round(finalW * 1000) / 1000,
      heightPct: Math.round(finalH * 1000) / 1000,
    });
  }

  // Sort top to bottom
  results.sort((a, b) => a.topPct - b.topPct);
  return results;
}

module.exports = { extractCrops, PARAMS };

if (require.main === module) {
  const imagePath = process.argv[2];
  if (!imagePath) { console.error('Usage: node cropper-v2-blob.js <image.png>'); process.exit(1); }
  extractCrops(imagePath).then(crops => console.log(JSON.stringify(crops, null, 2)));
}
