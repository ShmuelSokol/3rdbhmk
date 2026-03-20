#!/usr/bin/env node
/**
 * Full illustration audit: compare detected crops against source Hebrew pages
 * to find noise crops, cut-off illustrations, and missing illustrations.
 */
const { PrismaClient } = require('@prisma/client');
const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const prisma = new PrismaClient();
const BOOK_ID = 'jcqje5aut5wve5w5b8hv6fcq8';
const CACHE_DIR = '/tmp/bhmk/' + BOOK_ID + '/pages';
const GAP_THRESHOLD = 8; // % of page height

// Load env
const envPath = path.join(__dirname, '..', '.env.local');
if (fs.existsSync(envPath)) {
  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    if (line.trim() && !line.startsWith('#') && line.includes('=')) {
      const [key, ...vals] = line.split('=');
      process.env[key.trim()] = vals.join('=').trim();
    }
  }
}

async function getSourceImage(pageNumber) {
  const imgPath = path.join(CACHE_DIR, `page-${pageNumber}.png`);
  if (fs.existsSync(imgPath)) return fs.readFileSync(imgPath);
  return null;
}

async function analyzeGapCrop(imgBuf, topPct, bottomPct) {
  const meta = await sharp(imgBuf).metadata();
  const imgW = meta.width || 1655;
  const imgH = meta.height || 2340;

  const cropTop = Math.round((topPct / 100) * imgH);
  const cropBottom = Math.round((bottomPct / 100) * imgH);
  const cropHeight = cropBottom - cropTop;
  if (cropHeight < 100) return { valid: false, reason: 'too_small' };

  const marginX = Math.round(imgW * 0.01);
  try {
    const stats = await sharp(imgBuf)
      .extract({ left: marginX, top: cropTop, width: imgW - marginX * 2, height: cropHeight })
      .stats();

    const avgVariance = stats.channels.reduce((s, c) => s + (c.stdev || 0), 0) / stats.channels.length;
    const avgMean = stats.channels.reduce((s, c) => s + (c.mean || 0), 0) / stats.channels.length;
    const minStdev = Math.min(...stats.channels.map(c => c.stdev || 0));

    // Check if this is a real illustration vs noise
    const isNoise = (avgVariance < 30 && avgMean > 180) || // bright + low variance = page background
                    (avgMean > 200 && avgVariance < 45) || // very bright + low-medium variance
                    (minStdev < 10 && avgMean > 180);      // uniform channel + bright

    // Check edges for cut-off content (high variance at top/bottom edge)
    const topEdge = await sharp(imgBuf)
      .extract({ left: marginX, top: cropTop, width: imgW - marginX * 2, height: Math.min(20, cropHeight) })
      .stats();
    const bottomEdge = await sharp(imgBuf)
      .extract({ left: marginX, top: Math.max(cropTop, cropBottom - 20), width: imgW - marginX * 2, height: Math.min(20, cropHeight) })
      .stats();

    const topEdgeVar = topEdge.channels.reduce((s, c) => s + (c.stdev || 0), 0) / topEdge.channels.length;
    const bottomEdgeVar = bottomEdge.channels.reduce((s, c) => s + (c.stdev || 0), 0) / bottomEdge.channels.length;

    // If edges have high variance, the illustration might be cut off
    const topCutOff = topEdgeVar > 40 && topPct > 5;
    const bottomCutOff = bottomEdgeVar > 40 && bottomPct < 95;

    return {
      valid: !isNoise,
      isNoise,
      avgVariance: Math.round(avgVariance * 10) / 10,
      avgMean: Math.round(avgMean),
      cropHeight,
      topPct: Math.round(topPct * 10) / 10,
      bottomPct: Math.round(bottomPct * 10) / 10,
      topCutOff,
      bottomCutOff,
      topEdgeVar: Math.round(topEdgeVar * 10) / 10,
      bottomEdgeVar: Math.round(bottomEdgeVar * 10) / 10,
    };
  } catch (e) {
    return { valid: false, reason: 'error: ' + e.message };
  }
}

async function audit() {
  const pages = await prisma.page.findMany({
    where: { bookId: BOOK_ID },
    include: {
      regions: {
        orderBy: { regionIndex: 'asc' },
        select: { origY: true, origHeight: true, regionType: true }
      }
    },
    orderBy: { pageNumber: 'asc' }
  });

  const knownDiagrams = new Set([22, 24, 26, 47, 48, 132, 160, 166, 188, 196, 203, 215, 221, 270, 271, 284, 295, 296, 348]);
  const letterPages = new Set([4,5,6,7,8,9,10,11,12]);

  const noiseResults = [];
  const cutOffResults = [];
  const missingResults = [];
  let processed = 0;
  let totalCrops = 0;

  for (const p of pages) {
    if (knownDiagrams.has(p.pageNumber) || letterPages.has(p.pageNumber)) continue;

    const regions = p.regions.filter(r => r.origY != null && r.origHeight != null);
    if (regions.length === 0) continue;

    const sorted = [...regions].sort((a, b) => a.origY - b.origY);
    const gaps = [];

    // Gap before first region
    if (sorted[0].origY > GAP_THRESHOLD + 5) {
      gaps.push({ topY: 3, bottomY: sorted[0].origY - 0.5 });
    }

    // Gaps between regions
    for (let i = 0; i < sorted.length - 1; i++) {
      const bottom = sorted[i].origY + sorted[i].origHeight;
      const top = sorted[i + 1].origY;
      if (top - bottom > GAP_THRESHOLD) {
        gaps.push({ topY: bottom + 0.5, bottomY: top - 0.5 });
      }
    }

    // Gap after last region
    const lastBottom = sorted[sorted.length - 1].origY + sorted[sorted.length - 1].origHeight;
    if (lastBottom < 100 - GAP_THRESHOLD - 5) {
      gaps.push({ topY: lastBottom + 1, bottomY: 97 });
    }

    // Merge close gaps
    const merged = [];
    for (const gap of gaps.sort((a, b) => a.topY - b.topY)) {
      const prev = merged[merged.length - 1];
      if (prev && gap.topY - prev.bottomY < 10) {
        prev.bottomY = gap.bottomY;
      } else {
        merged.push({ ...gap });
      }
    }

    if (merged.length === 0) continue;

    const imgBuf = await getSourceImage(p.pageNumber);
    if (!imgBuf) continue;

    processed++;
    for (const gap of merged) {
      totalCrops++;
      const result = await analyzeGapCrop(imgBuf, gap.topY, gap.bottomY);

      if (result.isNoise) {
        noiseResults.push({
          page: p.pageNumber,
          ...result
        });
      }
      if (result.topCutOff || result.bottomCutOff) {
        cutOffResults.push({
          page: p.pageNumber,
          cutSide: (result.topCutOff ? 'top' : '') + (result.topCutOff && result.bottomCutOff ? '+' : '') + (result.bottomCutOff ? 'bottom' : ''),
          ...result
        });
      }
    }
  }

  console.log('=== ILLUSTRATION AUDIT RESULTS ===\n');
  console.log('Pages analyzed:', processed);
  console.log('Total illustration crops checked:', totalCrops);

  console.log('\n=== NOISE CROPS (should be filtered) ===');
  console.log('Count:', noiseResults.length);
  for (const r of noiseResults) {
    console.log(`  p${r.page}: variance=${r.avgVariance}, mean=${r.avgMean}, area=${r.topPct}%-${r.bottomPct}%, height=${r.cropHeight}px`);
  }

  console.log('\n=== POTENTIALLY CUT-OFF ILLUSTRATIONS ===');
  console.log('Count:', cutOffResults.length);
  for (const r of cutOffResults.slice(0, 30)) {
    console.log(`  p${r.page}: cut=${r.cutSide}, area=${r.topPct}%-${r.bottomPct}%, topEdge=${r.topEdgeVar}, botEdge=${r.bottomEdgeVar}, variance=${r.avgVariance}`);
  }
  if (cutOffResults.length > 30) console.log(`  ... and ${cutOffResults.length - 30} more`);

  await prisma.$disconnect();
}

audit().catch(console.error);
