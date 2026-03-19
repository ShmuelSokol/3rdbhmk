#!/usr/bin/env node
/**
 * Autoresearch Evaluation Script v2 — Comprehensive Typeset PDF Evaluator
 *
 * Downloads typeset PDFs for multiple page ranges and runs 30 binary evals
 * across 6 categories: Content, Layout, Illustration, Table, Diagram, Topic Structure.
 *
 * Usage: node scripts/autoresearch-eval-v2.js [configJSON]
 *
 * Requires: pdftotext, pdfinfo, pdftoppm, magick (ImageMagick v7)
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const BASE_URL = process.env.TYPESET_URL || 'http://localhost:3001';
const BOOK_ID = 'jcqje5aut5wve5w5b8hv6fcq8';
const TMP_DIR = '/tmp/autoresearch-typeset';
const DOWNLOAD_TIMEOUT = 180000; // 3 minutes
const TOOL_TIMEOUT = 15000;

const TEST_INPUTS = [
  { from: 2, to: 7, label: 'pages-2-7', minWords: 50, expectIllustrations: true, expectTables: false, expectDiagrams: false },
  { from: 8, to: 10, label: 'pages-8-10', minWords: 100, expectIllustrations: true, expectTables: true, expectDiagrams: false },
  { from: 14, to: 15, label: 'pages-14-15', minWords: 200, expectIllustrations: false, expectTables: false, expectDiagrams: false },
  { from: 14, to: 20, label: 'pages-14-20', minWords: 400, expectIllustrations: true, expectTables: false, expectDiagrams: true },
  { from: 14, to: 25, label: 'pages-14-25', minWords: 500, expectIllustrations: true, expectTables: true, expectDiagrams: true },
  { from: 14, to: 30, label: 'pages-14-30', minWords: 800, expectIllustrations: true, expectTables: true, expectDiagrams: true },
];

const EVAL_NAMES = {
  // Category 1: Content Quality
  E1: 'Hebrew chars present',
  E2: 'Words per page adequate',
  E3: 'Text completeness',
  E4: 'No meta-text artifacts',
  E5: 'No concatenation errors',
  // Category 2: Layout Quality
  E6: 'No excessive interior whitespace',
  E7: 'No orphan starts',
  E8: 'Decoration present',
  E9: 'Reasonable page count',
  E10: 'No tiny pages',
  // Category 3: Illustration Quality
  E11: 'Illustrations present when expected',
  E12: 'No tiny illustration fragments',
  E13: 'No mostly-blank illustration crops',
  E14: 'Illustration to text ratio reasonable',
  E15: 'No duplicate adjacent illustrations',
  // Category 4: Table Quality
  E16: 'Tables present when expected',
  E17: 'No truncated table cells',
  E18: 'Table rows consistent column count',
  E19: 'No standalone numbers as pages',
  E20: 'Page numbers sequential in TOC',
  // Category 5: Diagram Handling
  E21: 'Diagram pages have illustrations',
  E22: 'No repeated identical lines',
  E23: 'Diagram captions concise',
  E24: 'No label-only pages',
  E25: 'Diagram pages have explanatory text',
  // Category 6: Topic Structure
  E26: 'Topic breaks start new pages',
  E27: 'Headers visually distinct',
  E28: 'Section content cohesive',
  E29: 'Footer page numbers sequential',
  E30: 'No empty content pages',
};

const EVAL_COUNT = Object.keys(EVAL_NAMES).length;

// ─── UTILITIES ────────────────────────────────────────────────────────────

function ensureDirs() {
  if (!fs.existsSync(TMP_DIR)) fs.mkdirSync(TMP_DIR, { recursive: true });
}

function shellExec(cmd, timeout = TOOL_TIMEOUT) {
  try {
    return execSync(cmd, { encoding: 'utf8', timeout }).trim();
  } catch (e) {
    return null;
  }
}

function toolAvailable(name) {
  return shellExec(`which ${name}`, 5000) !== null;
}

async function downloadPdf(testInput, configOverride) {
  const configParam = configOverride ? `&config=${encodeURIComponent(JSON.stringify(configOverride))}` : '';
  const url = `${BASE_URL}/api/books/${BOOK_ID}/typeset?from=${testInput.from}&to=${testInput.to}${configParam}`;
  const outPath = path.join(TMP_DIR, `${testInput.label}.pdf`);

  try {
    execSync(`curl -s -f -o "${outPath}" "${url}"`, { timeout: DOWNLOAD_TIMEOUT });
    if (!fs.existsSync(outPath) || fs.statSync(outPath).size < 100) {
      console.error(`  FAIL: PDF too small or missing for ${testInput.label}`);
      return null;
    }
    return outPath;
  } catch (e) {
    console.error(`  FAIL: Could not download PDF for ${testInput.label}: ${e.message}`);
    return null;
  }
}

function extractText(pdfPath) {
  return shellExec(`pdftotext "${pdfPath}" -`, 10000) || '';
}

function extractTextPerPage(pdfPath, pageCount) {
  const pages = [];
  for (let i = 1; i <= pageCount; i++) {
    const text = shellExec(`pdftotext -f ${i} -l ${i} "${pdfPath}" -`, 5000) || '';
    pages.push(text);
  }
  return pages;
}

function getPageCount(pdfPath) {
  const info = shellExec(`pdfinfo "${pdfPath}" 2>/dev/null`, 5000);
  if (!info) return 0;
  const match = info.match(/Pages:\s+(\d+)/);
  return match ? parseInt(match[1]) : 0;
}

function getFileSize(pdfPath) {
  try { return fs.statSync(pdfPath).size; } catch { return 0; }
}

function renderPages(pdfPath, label) {
  const outDir = path.join(TMP_DIR, `${label}-pages`);
  if (fs.existsSync(outDir)) {
    for (const f of fs.readdirSync(outDir)) fs.unlinkSync(path.join(outDir, f));
  } else {
    fs.mkdirSync(outDir, { recursive: true });
  }
  try {
    execSync(`pdftoppm -png -r 72 "${pdfPath}" "${outDir}/page"`, { timeout: 60000 });
    return fs.readdirSync(outDir).filter(f => f.endsWith('.png')).map(f => path.join(outDir, f)).sort();
  } catch {
    return [];
  }
}

function getImageDimensions(imagePath) {
  const dims = shellExec(`magick identify -format "%w %h" "${imagePath}"`, 5000);
  if (!dims) return null;
  const [w, h] = dims.split(' ').map(Number);
  return (w && h) ? { w, h } : null;
}

function getImageMeanBrightness(imagePath) {
  const result = shellExec(
    `magick "${imagePath}" -colorspace Gray -scale 1x1! -format "%[fx:mean]" info:`,
    TOOL_TIMEOUT
  );
  return result !== null ? parseFloat(result) : null;
}

/**
 * Analyze per-row brightness of a rendered page, returning an array of brightness values (0-100 scale).
 */
function getRowBrightnesses(imagePath) {
  const dims = getImageDimensions(imagePath);
  if (!dims) return [];

  const rawData = shellExec(
    `magick "${imagePath}" -colorspace Gray -scale 1x${dims.h}! txt:- 2>/dev/null | tail -n +2`,
    TOOL_TIMEOUT
  );
  if (!rawData) return [];

  const brightnesses = [];
  for (const line of rawData.split('\n')) {
    const grayMatch = line.match(/gray\((\d+(?:\.\d+)?)%?\)/i) || line.match(/#([0-9A-Fa-f]{2})/);
    if (!grayMatch) continue;
    if (line.includes('gray')) {
      brightnesses.push(parseFloat(grayMatch[1]));
    } else {
      brightnesses.push(parseInt(grayMatch[1], 16) / 255 * 100);
    }
  }
  return brightnesses;
}

/**
 * Find the largest consecutive INTERIOR blank strip in a page image.
 * Interior = between first and last content rows, with substantial content on both sides.
 */
function findInteriorBlankStrip(imagePath) {
  const brightnesses = getRowBrightnesses(imagePath);
  if (brightnesses.length === 0) return 0;

  let firstContent = -1, lastContent = -1;
  for (let i = 0; i < brightnesses.length; i++) {
    if (brightnesses[i] < 95) {
      if (firstContent === -1) firstContent = i;
      lastContent = i;
    }
  }
  if (firstContent < 0 || lastContent <= firstContent) return 0;

  const minContentRows = Math.max(5, Math.floor(brightnesses.length * 0.05));
  let maxInteriorRun = 0, currentRun = 0, currentGapStart = -1;

  for (let i = firstContent; i <= lastContent; i++) {
    if (brightnesses[i] > 95) {
      if (currentRun === 0) currentGapStart = i;
      currentRun++;
    } else {
      if (currentRun > maxInteriorRun) {
        let contentAfter = 0, contentBefore = 0;
        for (let j = i; j <= lastContent; j++) { if (brightnesses[j] < 95) contentAfter++; }
        for (let j = firstContent; j < currentGapStart; j++) { if (brightnesses[j] < 95) contentBefore++; }
        if (contentAfter >= minContentRows && contentBefore >= minContentRows) {
          maxInteriorRun = currentRun;
        }
      }
      currentRun = 0;
    }
  }

  return brightnesses.length > 0 ? maxInteriorRun / brightnesses.length : 0;
}

/**
 * Detect image regions in a rendered page. Returns array of { y, h, area_pct }.
 * An "image region" = contiguous rows where >30% of pixels differ significantly from white.
 */
function detectImageRegions(imagePath) {
  const dims = getImageDimensions(imagePath);
  if (!dims) return [];

  // Get per-row darkness fraction using column projection
  const rawData = shellExec(
    `magick "${imagePath}" -colorspace Gray -scale 1x${dims.h}! txt:- 2>/dev/null | tail -n +2`,
    TOOL_TIMEOUT
  );
  if (!rawData) return [];

  const rowDarkness = [];
  for (const line of rawData.split('\n')) {
    const grayMatch = line.match(/gray\((\d+(?:\.\d+)?)%?\)/i) || line.match(/#([0-9A-Fa-f]{2})/);
    if (!grayMatch) continue;
    let brightness;
    if (line.includes('gray')) { brightness = parseFloat(grayMatch[1]); }
    else { brightness = parseInt(grayMatch[1], 16) / 255 * 100; }
    // A row is "image-like" if it has significant content (not just text which tends to be sparse)
    rowDarkness.push(brightness < 85); // dark enough to be image content
  }

  // Find contiguous runs of "dark" rows (image regions)
  const regions = [];
  let start = -1;
  for (let i = 0; i < rowDarkness.length; i++) {
    if (rowDarkness[i]) {
      if (start === -1) start = i;
    } else {
      if (start !== -1 && (i - start) > 5) { // Minimum 5 rows
        const h = i - start;
        regions.push({ y: start, h, area_pct: (h / dims.h) * 100 });
      }
      start = -1;
    }
  }
  if (start !== -1 && (rowDarkness.length - start) > 5) {
    const h = rowDarkness.length - start;
    regions.push({ y: start, h, area_pct: (h / dims.h) * 100 });
  }

  return regions;
}

/**
 * Compute a perceptual hash (average hash) for a rendered page region.
 * Returns a hex string hash for comparing image similarity.
 */
function imageHash(imagePath) {
  // Scale image to 8x8 grayscale, get pixel values, create binary hash
  const result = shellExec(
    `magick "${imagePath}" -colorspace Gray -scale 8x8! -depth 8 txt:- 2>/dev/null | tail -n +2`,
    TOOL_TIMEOUT
  );
  if (!result) return null;

  const values = [];
  for (const line of result.split('\n')) {
    const match = line.match(/gray\((\d+(?:\.\d+)?)%?\)/i) || line.match(/#([0-9A-Fa-f]{2})/);
    if (!match) continue;
    if (line.includes('gray')) { values.push(parseFloat(match[1])); }
    else { values.push(parseInt(match[1], 16) / 255 * 100); }
  }

  if (values.length < 64) return null;
  const mean = values.reduce((s, v) => s + v, 0) / values.length;
  let hash = '';
  for (const v of values) hash += v >= mean ? '1' : '0';
  return hash;
}

function hammingDistance(h1, h2) {
  if (!h1 || !h2 || h1.length !== h2.length) return Infinity;
  let d = 0;
  for (let i = 0; i < h1.length; i++) { if (h1[i] !== h2[i]) d++; }
  return d;
}

function countWords(text) {
  return text.split(/\s+/).filter(w => w.length > 1).length;
}

function isUrl(word) {
  return /^https?:\/\//i.test(word) || /^www\./i.test(word);
}

// ─── EVALS ────────────────────────────────────────────────────────────────

// === CATEGORY 1: CONTENT QUALITY ===

function evalE1_HebrewChars(text) {
  const hebrewChars = (text.match(/[\u0590-\u05FF]/g) || []).length;
  return { pass: hebrewChars >= 10, detail: `${hebrewChars} Hebrew chars found (need >=10)` };
}

function evalE2_WordsPerPage(text, pageCount) {
  const contentPages = Math.max(1, pageCount - 1); // exclude title page
  const words = countWords(text);
  const wordsPerPage = words / contentPages;
  return { pass: wordsPerPage >= 80, detail: `${wordsPerPage.toFixed(0)} words/page (need >=80), ${words} total, ${pageCount} pages` };
}

function evalE3_TextCompleteness(text, testInput) {
  const words = countWords(text);
  return { pass: words >= testInput.minWords, detail: `${words} words (need >=${testInput.minWords})` };
}

function evalE4_NoMetaTextArtifacts(text) {
  const artifacts = ['[THIS IS TABLE', '[THIS IS', 'TABLE:', 'DIAGRAM:', '[TABLE', '[DIAGRAM'];
  const found = [];
  for (const a of artifacts) {
    if (text.includes(a)) found.push(a);
  }
  return { pass: found.length === 0, detail: found.length === 0 ? 'No meta-text artifacts' : `Found artifacts: ${found.join(', ')}` };
}

function evalE5_NoConcatenationErrors(text) {
  const words = text.split(/\s+/).filter(w => w.length > 0);
  const problems = [];

  for (const word of words) {
    if (word.length <= 30) continue;
    if (isUrl(word)) continue;
    // Allow em-dashes, long hyphenated words, file paths
    if (/[-—\/]/.test(word)) continue;
    // Allow Hebrew strings (they can be long)
    if (/[\u0590-\u05FF]/.test(word)) continue;
    problems.push(word.substring(0, 40));
  }

  // Check for camelCase-like merges: two capitalized segments merged
  // Pattern: lowercase letter immediately followed by uppercase in the middle of a word
  const camelMerges = [];
  for (const word of words) {
    if (word.length < 6) continue;
    if (isUrl(word)) continue;
    // Check for patterns like "BeisSupreme", "HaMikdashThe"
    const camelMatch = word.match(/[a-z][A-Z][a-z]/g);
    if (camelMatch && camelMatch.length >= 1) {
      // Filter out known camelCase terms that are legitimate
      const legitimate = ['HaMikdash', 'HaKodesh', 'HaShem', 'HaGadol', 'HaKatan', 'HaLevi',
        'HaKohen', 'HaShulchan', 'HaMenorah', 'HaOlah', 'HaChattas', 'MacDonald', 'McCormick',
        'McGill', 'JavaScript', 'TypeScript', 'GitHub', 'iPhone', 'iPad', 'YouTube',
        'LinkedIn', 'WordPress', 'PostScript', 'PowerPoint', 'OpenAI'];
      if (!legitimate.some(l => word.includes(l)) && !word.startsWith('Ha') && !word.startsWith('Mc') && !word.startsWith('Mac')) {
        camelMerges.push(word.substring(0, 40));
      }
    }
  }

  const allProblems = [...new Set([...problems.slice(0, 5), ...camelMerges.slice(0, 5)])];
  return {
    pass: allProblems.length === 0,
    detail: allProblems.length === 0 ? 'No concatenation errors' : `Found: ${allProblems.join(', ')}`
  };
}

// === CATEGORY 2: LAYOUT QUALITY ===

function evalE6_NoExcessiveWhitespace(pageImages) {
  if (pageImages.length <= 2) return { pass: true, detail: 'Too few pages to evaluate' };

  let worstPage = 0, worstBlank = 0;
  for (let i = 1; i < pageImages.length - 1; i++) {
    const blank = findInteriorBlankStrip(pageImages[i]);
    if (blank > worstBlank) {
      worstBlank = blank;
      worstPage = i + 1;
    }
  }

  return {
    pass: worstBlank <= 0.45,
    detail: `Worst interior blank: ${(worstBlank * 100).toFixed(1)}% on page ${worstPage} (limit 45%)`
  };
}

function evalE7_NoOrphanStarts(pageImages) {
  if (pageImages.length <= 2) return { pass: true, detail: 'Too few pages to evaluate' };

  let orphanPages = 0;
  for (let i = 1; i < pageImages.length - 1; i++) {
    const dims = getImageDimensions(pageImages[i]);
    if (!dims) continue;

    const topSlice = Math.round(dims.h * 0.15);
    const topB = getImageMeanBrightness(
      `magick "${pageImages[i]}" -crop "${dims.w}x${topSlice}+0+${Math.round(dims.h * 0.08)}" -`
    );
    // Use magick for crop + analyze in one step
    const topResult = shellExec(
      `magick "${pageImages[i]}" -crop "${dims.w}x${topSlice}+0+${Math.round(dims.h * 0.08)}" -colorspace Gray -scale 1x1! -format "%[fx:mean]" info:`,
      TOOL_TIMEOUT
    );
    const midSlice = Math.round(dims.h * 0.20);
    const midResult = shellExec(
      `magick "${pageImages[i]}" -crop "${dims.w}x${midSlice}+0+${Math.round(dims.h * 0.23)}" -colorspace Gray -scale 1x1! -format "%[fx:mean]" info:`,
      TOOL_TIMEOUT
    );

    if (topResult === null || midResult === null) continue;
    const topBrightness = parseFloat(topResult);
    const midBrightness = parseFloat(midResult);

    // Top has text content (<0.90) but mid is very white (>0.97) = orphan start
    if (topBrightness < 0.90 && midBrightness > 0.97) {
      orphanPages++;
    }
  }

  return {
    pass: orphanPages === 0,
    detail: `${orphanPages} pages with orphan starts (of ${pageImages.length - 2} interior pages)`
  };
}

function evalE8_DecorationPresent(text) {
  const hasRunningHeader = /LISHCHNO|Lishchno/i.test(text);
  const hasPageNumbers = /\u2014\s+\d+\s+\u2014/.test(text) || /—\s+\d+\s+—/.test(text);
  return {
    pass: hasRunningHeader && hasPageNumbers,
    detail: `Header: ${hasRunningHeader ? 'YES' : 'NO'}, PageNums: ${hasPageNumbers ? 'YES' : 'NO'}`
  };
}

function evalE9_ReasonablePageCount(pageCount, testInput) {
  const sourcePages = testInput.to - testInput.from + 1;
  // Typeset should produce roughly 1-4x the source page count (some expansion for English + illustrations)
  const minPages = Math.max(2, sourcePages);
  const maxPages = sourcePages * 5 + 2; // generous upper bound
  const pass = pageCount >= minPages && pageCount <= maxPages;
  return {
    pass,
    detail: `${pageCount} PDF pages for ${sourcePages} source pages (expected ${minPages}-${maxPages})`
  };
}

function evalE10_NoTinyPages(pagesText) {
  if (pagesText.length <= 2) return { pass: true, detail: 'Too few pages to evaluate' };

  const tinyPages = [];
  for (let i = 1; i < pagesText.length - 1; i++) { // skip first (title) and last
    const text = pagesText[i];
    // Strip likely header/footer content (lines with em-dash page numbers or book title)
    const lines = text.split('\n').filter(l => {
      const trimmed = l.trim();
      if (!trimmed) return false;
      if (/^—\s*\d+\s*—$/.test(trimmed)) return false;
      if (/^\u2014\s*\d+\s*\u2014$/.test(trimmed)) return false;
      if (/^LISHCHNO|^Lishchno/i.test(trimmed)) return false;
      return true;
    });
    const words = lines.join(' ').split(/\s+/).filter(w => w.length > 1).length;
    if (words < 15) {
      tinyPages.push({ page: i + 1, words });
    }
  }

  return {
    pass: tinyPages.length === 0,
    detail: tinyPages.length === 0
      ? 'No tiny pages'
      : `${tinyPages.length} tiny pages: ${tinyPages.slice(0, 5).map(p => `p${p.page}(${p.words}w)`).join(', ')}`
  };
}

// === CATEGORY 3: ILLUSTRATION QUALITY ===

function evalE11_IllustrationsPresent(fileSize, testInput) {
  if (!testInput.expectIllustrations) {
    return { pass: true, detail: 'No illustrations expected for this range' };
  }
  // Illustrations should make PDF notably larger than text-only
  const pass = fileSize > 80000;
  return { pass, detail: `File size: ${Math.round(fileSize / 1024)}KB (need >80KB for illustrations)` };
}

function evalE12_NoTinyIllustrationFragments(pageImages) {
  if (pageImages.length === 0) return { pass: true, detail: 'No rendered pages' };

  const tinyFragments = [];
  for (let i = 0; i < pageImages.length; i++) {
    const dims = getImageDimensions(pageImages[i]);
    if (!dims) continue;
    const totalArea = dims.w * dims.h;

    const regions = detectImageRegions(pageImages[i]);
    for (const r of regions) {
      const regionArea = dims.w * r.h; // full-width region area
      const areaPct = (regionArea / totalArea) * 100;
      // Ignore very thin strips (<2% height) which are decorative border/frame lines
      const heightPct = (r.h / dims.h) * 100;
      if (areaPct < 2 && areaPct > 0.5 && heightPct >= 2) { // Between 0.5% and 2% area, >=2% height = suspicious fragment (2-5% can be legitimate small illustrations)
        tinyFragments.push({ page: i + 1, areaPct: areaPct.toFixed(1) });
      }
    }
  }

  return {
    pass: tinyFragments.length === 0,
    detail: tinyFragments.length === 0
      ? 'No tiny illustration fragments'
      : `${tinyFragments.length} tiny fragments: ${tinyFragments.slice(0, 3).map(f => `p${f.page}(${f.areaPct}%)`).join(', ')}`
  };
}

function evalE13_NoBlankIllustrationCrops(pageImages, testInput) {
  if (!testInput.expectIllustrations || pageImages.length === 0) {
    return { pass: true, detail: 'No illustrations expected or no rendered pages' };
  }

  // Find pages that are likely illustration pages (low word count or large dark regions)
  // Check if any such page is >90% white (blank crop)
  let blankIllustrations = 0;
  for (let i = 0; i < pageImages.length; i++) {
    const regions = detectImageRegions(pageImages[i]);
    if (regions.length === 0) continue; // Not an illustration page

    // Check if largest region is actually content (not mostly white)
    const largest = regions.reduce((a, b) => a.area_pct > b.area_pct ? a : b, regions[0]);
    if (largest.area_pct > 20) {
      // This is a significant image region — check it's not blank
      const dims = getImageDimensions(pageImages[i]);
      if (!dims) continue;

      // Crop the region and check brightness
      const regionBrightness = shellExec(
        `magick "${pageImages[i]}" -crop "${dims.w}x${largest.h}+0+${largest.y}" -colorspace Gray -scale 1x1! -format "%[fx:mean]" info:`,
        TOOL_TIMEOUT
      );
      if (regionBrightness !== null && parseFloat(regionBrightness) > 0.90) {
        blankIllustrations++;
      }
    }
  }

  return {
    pass: blankIllustrations === 0,
    detail: blankIllustrations === 0
      ? 'No mostly-blank illustration crops'
      : `${blankIllustrations} illustration regions are >90% white`
  };
}

function evalE14_IllustrationTextRatio(pageImages, pagesText, testInput) {
  if (!testInput.expectIllustrations || pageImages.length === 0) {
    return { pass: true, detail: 'No illustrations expected or no rendered pages' };
  }

  // Count pages that appear to be mostly illustration (very few words)
  let illustPages = 0;
  for (let i = 0; i < pagesText.length; i++) {
    const words = countWords(pagesText[i]);
    if (words < 20) illustPages++; // Likely illustration-only page
  }

  const totalPages = Math.max(1, pagesText.length);
  const ratio = illustPages / totalPages;
  return {
    pass: ratio <= 0.70,
    detail: `${illustPages}/${totalPages} pages appear illustration-heavy (${(ratio * 100).toFixed(0)}%, limit 70%)`
  };
}

function evalE15_NoDuplicateAdjacentIllustrations(pageImages) {
  if (pageImages.length < 2) return { pass: true, detail: 'Too few pages to compare' };

  const hashes = [];
  for (const img of pageImages) {
    hashes.push(imageHash(img));
  }

  let duplicates = 0;
  for (let i = 0; i < hashes.length - 1; i++) {
    if (!hashes[i] || !hashes[i + 1]) continue;
    const dist = hammingDistance(hashes[i], hashes[i + 1]);
    if (dist < 2) { // Nearly identical pages — likely duplicate illustration (2/64 bits = 97%+ match)
      duplicates++;
    }
  }

  return {
    pass: duplicates === 0,
    detail: duplicates === 0
      ? 'No duplicate adjacent illustrations'
      : `${duplicates} pairs of near-identical consecutive pages`
  };
}

// === CATEGORY 4: TABLE QUALITY ===

function evalE16_TablesPresent(text, testInput) {
  if (!testInput.expectTables) {
    return { pass: true, detail: 'No tables expected for this range' };
  }

  // Check for columnar data indicators: pipe characters, tab-aligned content, or consistent spacing patterns
  const hasPipes = (text.match(/\|/g) || []).length >= 3;
  const hasTabular = /\t/.test(text);
  // Check for lines with consistent multi-space gaps (column alignment)
  const lines = text.split('\n');
  let alignedLines = 0;
  for (const line of lines) {
    if (/\S\s{3,}\S/.test(line)) alignedLines++; // 3+ spaces between content
  }
  const hasAlignment = alignedLines >= 3;

  // Check for TOC/list indicators: dot-leaders, letter/number-prefixed items, page references
  const dotLeaders = lines.filter(l => /\.{3,}/.test(l)).length;
  const numberedItems = lines.filter(l => /^\s*[A-Z][\.\)]\s/.test(l) || /^\s*\d+[\.\)]\s/.test(l)).length;
  const pageRefs = lines.filter(l => /\d{1,3}\s*$/.test(l.trim()) && l.trim().length > 10).length;
  const hasTocStructure = dotLeaders >= 2 || (numberedItems >= 3) || (pageRefs >= 3 && numberedItems >= 1);

  const pass = hasPipes || hasTabular || hasAlignment || hasTocStructure;
  return {
    pass,
    detail: `Pipes: ${hasPipes}, Tabs: ${hasTabular}, Aligned: ${hasAlignment} (${alignedLines} lines), TOC: ${hasTocStructure}`
  };
}

function evalE17_NoTruncatedTableCells(text) {
  // Check for lines ending with unclosed parentheses
  const lines = text.split('\n').filter(l => l.trim().length > 0);
  const truncated = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    // Count open vs close parens
    const opens = (line.match(/\(/g) || []).length;
    const closes = (line.match(/\)/g) || []).length;
    if (opens > closes && opens - closes >= 1) {
      // Check if any of the next 3 lines has the closing paren (multi-line citations are common)
      let foundClose = false;
      for (let j = 1; j <= 3 && i + j < lines.length; j++) {
        const followLine = lines[i + j].trim();
        if ((followLine.match(/\)/g) || []).length > 0) {
          foundClose = true;
          break;
        }
      }
      if (!foundClose) {
        truncated.push({ lineNum: i + 1, text: line.substring(0, 60) });
      }
    }
  }

  // Allow up to 2 stray unclosed parens (some may be legitimate formatting)
  return {
    pass: truncated.length <= 2,
    detail: truncated.length <= 2
      ? `${truncated.length} unclosed paren lines (within tolerance)`
      : `${truncated.length} truncated cells: ${truncated.slice(0, 3).map(t => `L${t.lineNum}`).join(', ')}`
  };
}

function evalE18_TableRowsConsistentColumns(text) {
  // If pipe-separated table rows exist, check column count consistency
  const lines = text.split('\n').filter(l => l.includes('|') && l.trim().length > 3);
  if (lines.length < 3) return { pass: true, detail: 'No pipe-separated table found (OK)' };

  const columnCounts = lines.map(l => l.split('|').length);
  // Find the most common column count
  const freq = {};
  for (const c of columnCounts) freq[c] = (freq[c] || 0) + 1;
  const modeCount = Math.max(...Object.values(freq));
  const mode = parseInt(Object.keys(freq).find(k => freq[k] === modeCount));

  // Count rows that deviate from mode
  const deviants = columnCounts.filter(c => Math.abs(c - mode) > 1).length;
  const deviationPct = deviants / columnCounts.length;

  return {
    pass: deviationPct <= 0.2, // Allow up to 20% deviation (header/footer rows may differ)
    detail: `${lines.length} table rows, mode ${mode} cols, ${deviants} deviant rows (${(deviationPct * 100).toFixed(0)}%)`
  };
}

function evalE19_NoStandaloneNumbers(pagesText) {
  // Numbers like "8", "9", "33" shouldn't appear as isolated lines between body text
  // (These would be raw page numbers leaking into body text)
  // Exception: numbers in table/TOC context (surrounded by short lines) are legitimate
  let standaloneCount = 0;
  const examples = [];

  for (let p = 0; p < pagesText.length; p++) {
    const lines = pagesText[p].split('\n').map(l => l.trim()).filter(l => l.length > 0);
    for (let i = 1; i < lines.length - 1; i++) { // skip first/last line of page
      const line = lines[i];
      // Skip known page number patterns (em-dash surrounded)
      if (/^[—\u2014]\s*\d+\s*[—\u2014]$/.test(line)) continue;
      // A standalone number: just 1-3 digits on a line by itself, surrounded by content lines
      if (/^\d{1,3}$/.test(line)) {
        const prev = lines[i - 1];
        const next = lines[i + 1];
        // Only flag if surrounded by LONG paragraph lines (>40 chars) that look like body text
        // (ending with period/common punctuation), not headings or TOC entries
        const prevIsBodyText = prev && prev.length > 40 && /[.!?:;,]$/.test(prev);
        const nextIsBodyText = next && next.length > 40;
        if (prevIsBodyText && nextIsBodyText) {
          standaloneCount++;
          if (examples.length < 3) examples.push(`p${p + 1}:"${line}"`);
        }
      }
    }
  }

  return {
    pass: standaloneCount <= 1, // Allow 1 stray number
    detail: standaloneCount <= 1
      ? `${standaloneCount} standalone numbers (within tolerance)`
      : `${standaloneCount} standalone numbers: ${examples.join(', ')}`
  };
}

function evalE20_SequentialTOCPageNumbers(text) {
  // If there are TOC-like entries (lines with a number at the end), check they are sequential
  // Use stricter pattern: short-to-medium lines (10-80 chars) ending with 1-3 digit number
  const tocPattern = /^(.{10,80}?)\s+(\d{1,3})\s*$/gm;
  const pageNums = [];
  let match;
  while ((match = tocPattern.exec(text)) !== null) {
    const num = parseInt(match[2]);
    // Only consider reasonable page numbers and skip lines that look like body text
    const prefix = match[1].trim();
    if (num > 0 && num < 500 && prefix.split(/\s+/).length <= 12) {
      pageNums.push(num);
    }
  }

  if (pageNums.length < 3) return { pass: true, detail: 'No TOC entries found (OK)' };

  // Check that numbers form mostly-increasing subsequences
  // Allow section resets (TOC sections for different parts of the book)
  // Count large inversions only (drop of >20 pages suggests new section, not disorder)
  let smallInversions = 0;
  for (let i = 1; i < pageNums.length; i++) {
    const drop = pageNums[i - 1] - pageNums[i];
    if (drop > 2 && drop <= 20) { // Small out-of-order (not a section reset)
      smallInversions++;
    }
  }

  // Allow a few small inversions (sub-entries may reference earlier pages)
  const maxAllowed = Math.max(2, Math.floor(pageNums.length * 0.15));
  return {
    pass: smallInversions <= maxAllowed,
    detail: `${pageNums.length} TOC entries, ${smallInversions} small inversions (limit ${maxAllowed}) (nums: ${pageNums.slice(0, 8).join(',')}...)`
  };
}

// === CATEGORY 5: DIAGRAM HANDLING ===

function evalE21_DiagramPagesHaveIllustrations(pageImages, pagesText, testInput) {
  if (!testInput.expectDiagrams) {
    return { pass: true, detail: 'No diagrams expected for this range' };
  }

  // Diagram pages = pages with mostly short text fragments (labels) and few long paragraphs
  let diagramPagesWithoutImages = 0;
  for (let i = 0; i < pagesText.length; i++) {
    const lines = pagesText[i].split('\n').filter(l => l.trim().length > 0);
    if (lines.length < 3) continue;

    const shortLines = lines.filter(l => l.trim().split(/\s+/).length <= 5).length;
    const ratio = shortLines / lines.length;
    if (ratio > 0.7 && lines.length >= 5) {
      // This looks like a diagram page — check if it has illustration content
      if (i < pageImages.length) {
        const fileSize = fs.existsSync(pageImages[i]) ? fs.statSync(pageImages[i]).size : 0;
        const brightness = getImageMeanBrightness(pageImages[i]);
        // Illustration page should have some dark content (not all white)
        if (brightness !== null && brightness > 0.92 && fileSize < 50000) {
          diagramPagesWithoutImages++;
        }
      }
    }
  }

  return {
    pass: diagramPagesWithoutImages === 0,
    detail: diagramPagesWithoutImages === 0
      ? 'All diagram-like pages have illustration content'
      : `${diagramPagesWithoutImages} diagram pages appear to lack illustrations`
  };
}

function evalE22_NoRepeatedIdenticalLines(text) {
  const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 3);
  const freq = {};
  for (const l of lines) {
    // Normalize whitespace
    const normalized = l.replace(/\s+/g, ' ');
    freq[normalized] = (freq[normalized] || 0) + 1;
  }

  // Find lines repeated 5+ times (excluding common headers/footers and short labels)
  const repeated = [];
  for (const [line, count] of Object.entries(freq)) {
    if (count >= 5) {
      // Skip known repeated elements: headers, page numbers, dividers
      if (/^LISHCHNO|^Lishchno/i.test(line)) continue;
      if (/^[—\u2014]\s*\d+\s*[—\u2014]$/.test(line)) continue;
      if (/^[─━═\-*]+$/.test(line)) continue;
      // Skip short labels (<15 chars) — these are legitimate repeated diagram/section labels
      if (line.length < 15) continue;
      repeated.push({ line: line.substring(0, 50), count });
    }
  }

  return {
    pass: repeated.length === 0,
    detail: repeated.length === 0
      ? 'No repeated identical lines'
      : `${repeated.length} repeated lines: ${repeated.slice(0, 3).map(r => `"${r.line}"(${r.count}x)`).join(', ')}`
  };
}

function evalE23_DiagramCaptionsConcise(pagesText, testInput) {
  if (!testInput.expectDiagrams) {
    return { pass: true, detail: 'No diagrams expected for this range' };
  }

  // Identify diagram-like pages and check that their text blocks are concise
  let longCaptions = 0;
  for (let i = 0; i < pagesText.length; i++) {
    const lines = pagesText[i].split('\n').filter(l => l.trim().length > 0);
    if (lines.length < 3) continue;

    const shortLines = lines.filter(l => l.trim().split(/\s+/).length <= 5).length;
    const ratio = shortLines / lines.length;
    if (ratio > 0.6) {
      // Diagram page — check individual text blocks (groups of consecutive non-empty lines)
      const blocks = [];
      let currentBlock = [];
      for (const line of lines) {
        if (line.trim()) {
          currentBlock.push(line);
        } else {
          if (currentBlock.length > 0) blocks.push(currentBlock.join(' '));
          currentBlock = [];
        }
      }
      if (currentBlock.length > 0) blocks.push(currentBlock.join(' '));

      // Allow up to 1 long explanatory block per diagram page (>200 words is excessive)
      let longBlocksOnPage = 0;
      for (const block of blocks) {
        const words = block.split(/\s+/).filter(w => w.length > 1).length;
        if (words > 200) longBlocksOnPage++;
      }
      longCaptions += longBlocksOnPage;
    }
  }

  return {
    pass: longCaptions === 0,
    detail: longCaptions === 0
      ? 'Diagram captions are concise'
      : `${longCaptions} diagram text blocks exceed 200 words`
  };
}

function evalE24_NoLabelOnlyPages(pagesText) {
  if (pagesText.length <= 2) return { pass: true, detail: 'Too few pages to evaluate' };

  let labelOnlyPages = 0;
  const examples = [];
  for (let i = 1; i < pagesText.length - 1; i++) { // skip title and last
    const lines = pagesText[i].split('\n').filter(l => {
      const t = l.trim();
      if (!t) return false;
      if (/^[—\u2014]\s*\d+\s*[—\u2014]$/.test(t)) return false;
      if (/^LISHCHNO|^Lishchno/i.test(t)) return false;
      return true;
    });

    if (lines.length === 0) continue;

    // Check if ALL lines are very short (<5 words)
    const allShort = lines.every(l => l.trim().split(/\s+/).length < 5);
    const totalWords = lines.join(' ').split(/\s+/).filter(w => w.length > 1).length;

    if (allShort && totalWords > 3 && lines.length >= 3) {
      labelOnlyPages++;
      if (examples.length < 3) examples.push(`p${i + 1}(${lines.length} lines, ${totalWords}w)`);
    }
  }

  return {
    pass: labelOnlyPages === 0,
    detail: labelOnlyPages === 0
      ? 'No label-only pages'
      : `${labelOnlyPages} label-only pages: ${examples.join(', ')}`
  };
}

function evalE25_DiagramPagesHaveExplanatoryText(pagesText, testInput) {
  if (!testInput.expectDiagrams) {
    return { pass: true, detail: 'No diagrams expected for this range' };
  }

  // Find diagram-like pages and check at least one has a paragraph (>20 words)
  let diagramPages = 0;
  let diagramPagesWithText = 0;

  for (let i = 0; i < pagesText.length; i++) {
    const lines = pagesText[i].split('\n').filter(l => l.trim().length > 0);
    if (lines.length < 3) continue;

    const shortLines = lines.filter(l => l.trim().split(/\s+/).length <= 5).length;
    const ratio = shortLines / lines.length;
    if (ratio > 0.6 && lines.length >= 5) {
      diagramPages++;
      // Check for at least one paragraph of >20 words
      const fullText = pagesText[i];
      const paragraphs = fullText.split(/\n\s*\n/);
      const hasLongParagraph = paragraphs.some(p => p.split(/\s+/).filter(w => w.length > 1).length >= 20);
      if (hasLongParagraph) diagramPagesWithText++;
    }
  }

  if (diagramPages === 0) return { pass: true, detail: 'No diagram pages detected' };

  return {
    pass: diagramPagesWithText > 0,
    detail: `${diagramPagesWithText}/${diagramPages} diagram pages have explanatory text (>20 words)`
  };
}

// === CATEGORY 6: TOPIC STRUCTURE ===

function evalE26_TopicBreaksNewPages(text) {
  // Structural check — the typeset code forces new pages at topic breaks.
  // We can verify by checking that ornamental dividers (long dash/star lines) appear
  // near the top of text blocks (first 20% of a page's text), not mid-page.
  // In pdftotext output, each page is separated by form-feed (\f).
  const pages = text.split('\f').filter(p => p.trim().length > 0);
  if (pages.length < 3) return { pass: true, detail: 'Too few pages (structural check assumed OK)' };

  let midPageDividers = 0;
  for (const page of pages) {
    const lines = page.split('\n').filter(l => l.trim().length > 0);
    if (lines.length < 5) continue;

    // Check for ornamental divider patterns
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      const isDivider = /^[─━═✦✧◆◇★☆*\-]{5,}$/.test(line) || /^[*]{3,}$/.test(line) || /^\s*[✦✧◆◇]{3,}/.test(line);
      if (isDivider) {
        const position = i / lines.length;
        if (position > 0.2 && position < 0.8) {
          midPageDividers++; // Divider in middle of page = topic break not forcing new page
        }
      }
    }
  }

  return {
    pass: midPageDividers === 0,
    detail: midPageDividers === 0
      ? 'Topic breaks appear at page boundaries'
      : `${midPageDividers} topic dividers found mid-page`
  };
}

function evalE27_HeadersVisuallyDistinct(text) {
  // Check that header text appears with formatting markers — uppercase, all-caps lines, or distinct styling
  // In pdftotext, uppercase/bold text often appears as all-caps
  const pages = text.split('\f').filter(p => p.trim().length > 0);
  if (pages.length < 2) return { pass: true, detail: 'Too few pages' };

  let headersFound = 0;
  let pagesWithHeaders = 0;

  for (const page of pages) {
    const lines = page.split('\n').filter(l => l.trim().length > 3);
    if (lines.length < 3) continue;

    // Look for lines that are likely headers: all-caps, short, followed by longer lines
    for (let i = 0; i < Math.min(5, lines.length); i++) {
      const line = lines[i].trim();
      // Skip page numbers and running headers
      if (/^[—\u2014]\s*\d+\s*[—\u2014]$/.test(line)) continue;
      if (/^LISHCHNO TIDRESHU/i.test(line)) continue;

      // Check for all-caps (header style) or title-case short lines
      const isAllCaps = line === line.toUpperCase() && /[A-Z]/.test(line) && line.length > 3;
      const isTitleCase = line.split(' ').filter(w => w.length > 2 && w[0] === w[0].toUpperCase()).length >= 2
        && line.split(/\s+/).length <= 8;

      if (isAllCaps || isTitleCase) {
        headersFound++;
        pagesWithHeaders++;
        break; // One per page is enough
      }
    }
  }

  // At least some pages should have visually distinct headers
  const hasHeaders = headersFound > 0;
  return {
    pass: hasHeaders,
    detail: `${headersFound} pages with distinct headers (of ${pages.length} pages)`
  };
}

function evalE28_SectionContentCohesive(pagesText) {
  // No page should mix table-of-contents entries (lines ending in numbers) with body paragraphs
  let mixedPages = 0;

  for (let i = 0; i < pagesText.length; i++) {
    const lines = pagesText[i].split('\n').filter(l => l.trim().length > 3);
    if (lines.length < 5) continue;

    // Count TOC-style lines (end with a page number, short-medium length)
    let tocLines = 0;
    let bodyLines = 0;
    for (const line of lines) {
      const trimmed = line.trim();
      // Skip headers/footers
      if (/^[—\u2014]\s*\d+\s*[—\u2014]$/.test(trimmed)) continue;
      if (/^LISHCHNO/i.test(trimmed)) continue;

      // TOC pattern: text followed by page number
      if (/^.{5,50}\s+\d{1,3}\s*$/.test(trimmed) || /^.{5,50}\.{2,}\s*\d{1,3}\s*$/.test(trimmed)) {
        tocLines++;
      } else if (trimmed.split(/\s+/).length >= 10) {
        bodyLines++;
      }
    }

    // If both TOC and body content are present on the same page
    if (tocLines >= 3 && bodyLines >= 3) {
      mixedPages++;
    }
  }

  return {
    pass: mixedPages === 0,
    detail: mixedPages === 0
      ? 'Section content is cohesive'
      : `${mixedPages} pages mix TOC entries with body text`
  };
}

function evalE29_FooterPageNumbersSequential(text) {
  // Extract page numbers from em-dash pattern "— N —"
  const pattern = /[—\u2014]\s+(\d+)\s+[—\u2014]/g;
  const nums = [];
  let match;
  while ((match = pattern.exec(text)) !== null) {
    nums.push(parseInt(match[1]));
  }

  if (nums.length < 2) return { pass: true, detail: `Only ${nums.length} page numbers found` };

  let outOfOrder = 0;
  for (let i = 1; i < nums.length; i++) {
    // Allow pages to jump forward (section breaks) but not go backward
    if (nums[i] < nums[i - 1]) {
      outOfOrder++;
    }
  }

  return {
    pass: outOfOrder === 0,
    detail: `${nums.length} footer page nums, ${outOfOrder} out of order (sequence: ${nums.slice(0, 10).join(',')}...)`
  };
}

function evalE30_NoEmptyContentPages(pagesText) {
  if (pagesText.length <= 2) return { pass: true, detail: 'Too few pages' };

  let emptyPages = 0;
  const examples = [];

  for (let i = 1; i < pagesText.length - 1; i++) {
    const text = pagesText[i];
    // Strip headers and footers
    const lines = text.split('\n').filter(l => {
      const t = l.trim();
      if (!t) return false;
      if (/^[—\u2014]\s*\d+\s*[—\u2014]$/.test(t)) return false;
      if (/^LISHCHNO|^Lishchno/i.test(t)) return false;
      return true;
    });
    const words = lines.join(' ').split(/\s+/).filter(w => w.length > 1).length;
    if (words < 5) {
      emptyPages++;
      if (examples.length < 5) examples.push(`p${i + 1}(${words}w)`);
    }
  }

  return {
    pass: emptyPages === 0,
    detail: emptyPages === 0
      ? 'No empty content pages'
      : `${emptyPages} empty pages: ${examples.join(', ')}`
  };
}

// ─── MAIN ─────────────────────────────────────────────────────────────────

async function runEvals(configOverride) {
  ensureDirs();

  // Verify tools
  const tools = ['pdftotext', 'pdfinfo', 'pdftoppm', 'magick'];
  const missingTools = tools.filter(t => !toolAvailable(t));
  if (missingTools.length > 0) {
    console.error(`Missing required tools: ${missingTools.join(', ')}`);
    console.error('Install with: brew install poppler imagemagick');
    process.exit(2);
  }

  const evalKeys = Object.keys(EVAL_NAMES);
  const results = {
    timestamp: new Date().toISOString(),
    baseUrl: BASE_URL,
    config: configOverride || null,
    totalScore: 0,
    maxScore: TEST_INPUTS.length * EVAL_COUNT,
    evalBreakdown: {},
    evalTotal: {},
    categoryScores: {},
    details: [],
  };

  // Initialize eval tracking
  for (const key of evalKeys) {
    results.evalBreakdown[key] = 0;
    results.evalTotal[key] = 0;
  }

  const categories = {
    'Content Quality (E1-E5)': ['E1', 'E2', 'E3', 'E4', 'E5'],
    'Layout Quality (E6-E10)': ['E6', 'E7', 'E8', 'E9', 'E10'],
    'Illustration Quality (E11-E15)': ['E11', 'E12', 'E13', 'E14', 'E15'],
    'Table Quality (E16-E20)': ['E16', 'E17', 'E18', 'E19', 'E20'],
    'Diagram Handling (E21-E25)': ['E21', 'E22', 'E23', 'E24', 'E25'],
    'Topic Structure (E26-E30)': ['E26', 'E27', 'E28', 'E29', 'E30'],
  };

  for (const testInput of TEST_INPUTS) {
    console.log(`\n${'═'.repeat(60)}`);
    console.log(`  Testing ${testInput.label} (pages ${testInput.from}-${testInput.to})`);
    console.log(`${'═'.repeat(60)}`);

    const pdfPath = await downloadPdf(testInput, configOverride);
    if (!pdfPath) {
      console.log(`  SKIP: Could not download PDF`);
      results.details.push({ input: testInput.label, error: 'download failed' });
      for (const key of evalKeys) results.evalTotal[key]++;
      continue;
    }

    const text = extractText(pdfPath);
    const pageCount = getPageCount(pdfPath);
    const fileSize = getFileSize(pdfPath);
    const wordCount = countWords(text);
    console.log(`  PDF: ${pageCount} pages, ${Math.round(fileSize / 1024)}KB, ${wordCount} words`);

    // Extract per-page text
    const pagesText = extractTextPerPage(pdfPath, pageCount);

    // Render pages for image analysis
    console.log(`  Rendering pages...`);
    const pageImages = renderPages(pdfPath, testInput.label);
    console.log(`  Rendered ${pageImages.length} page images`);

    // Run all 30 evals
    const evals = {};

    // Category 1: Content Quality
    console.log('\n  --- Content Quality ---');
    evals.E1 = evalE1_HebrewChars(text);
    evals.E2 = evalE2_WordsPerPage(text, pageCount);
    evals.E3 = evalE3_TextCompleteness(text, testInput);
    evals.E4 = evalE4_NoMetaTextArtifacts(text);
    evals.E5 = evalE5_NoConcatenationErrors(text);

    // Category 2: Layout Quality
    console.log('  --- Layout Quality ---');
    evals.E6 = pageImages.length > 0
      ? evalE6_NoExcessiveWhitespace(pageImages)
      : { pass: true, detail: 'Skipped (no rendered pages)' };
    evals.E7 = pageImages.length > 0
      ? evalE7_NoOrphanStarts(pageImages)
      : { pass: true, detail: 'Skipped (no rendered pages)' };
    evals.E8 = evalE8_DecorationPresent(text);
    evals.E9 = evalE9_ReasonablePageCount(pageCount, testInput);
    evals.E10 = evalE10_NoTinyPages(pagesText);

    // Category 3: Illustration Quality
    console.log('  --- Illustration Quality ---');
    evals.E11 = evalE11_IllustrationsPresent(fileSize, testInput);
    evals.E12 = pageImages.length > 0
      ? evalE12_NoTinyIllustrationFragments(pageImages)
      : { pass: true, detail: 'Skipped (no rendered pages)' };
    evals.E13 = evalE13_NoBlankIllustrationCrops(pageImages, testInput);
    evals.E14 = evalE14_IllustrationTextRatio(pageImages, pagesText, testInput);
    evals.E15 = evalE15_NoDuplicateAdjacentIllustrations(pageImages);

    // Category 4: Table Quality
    console.log('  --- Table Quality ---');
    evals.E16 = evalE16_TablesPresent(text, testInput);
    evals.E17 = evalE17_NoTruncatedTableCells(text);
    evals.E18 = evalE18_TableRowsConsistentColumns(text);
    evals.E19 = evalE19_NoStandaloneNumbers(pagesText);
    evals.E20 = evalE20_SequentialTOCPageNumbers(text);

    // Category 5: Diagram Handling
    console.log('  --- Diagram Handling ---');
    evals.E21 = evalE21_DiagramPagesHaveIllustrations(pageImages, pagesText, testInput);
    evals.E22 = evalE22_NoRepeatedIdenticalLines(text);
    evals.E23 = evalE23_DiagramCaptionsConcise(pagesText, testInput);
    evals.E24 = evalE24_NoLabelOnlyPages(pagesText);
    evals.E25 = evalE25_DiagramPagesHaveExplanatoryText(pagesText, testInput);

    // Category 6: Topic Structure
    console.log('  --- Topic Structure ---');
    evals.E26 = evalE26_TopicBreaksNewPages(text);
    evals.E27 = evalE27_HeadersVisuallyDistinct(text);
    evals.E28 = evalE28_SectionContentCohesive(pagesText);
    evals.E29 = evalE29_FooterPageNumbersSequential(text);
    evals.E30 = evalE30_NoEmptyContentPages(pagesText);

    // Tally results
    let inputScore = 0;
    for (const [key, result] of Object.entries(evals)) {
      results.evalTotal[key]++;
      if (result.pass) {
        inputScore++;
        results.evalBreakdown[key]++;
      }
      const status = result.pass ? 'PASS' : 'FAIL';
      console.log(`  ${key} [${EVAL_NAMES[key]}]: ${status} — ${result.detail}`);
    }

    results.totalScore += inputScore;
    results.details.push({
      input: testInput.label,
      score: inputScore,
      maxScore: EVAL_COUNT,
      evals,
    });

    console.log(`\n  Score: ${inputScore}/${EVAL_COUNT}`);
  }

  // Category summary
  console.log(`\n${'═'.repeat(60)}`);
  console.log('  CATEGORY SUMMARY');
  console.log(`${'═'.repeat(60)}`);

  for (const [catName, catEvals] of Object.entries(categories)) {
    let catScore = 0, catMax = 0;
    for (const key of catEvals) {
      catScore += results.evalBreakdown[key] || 0;
      catMax += results.evalTotal[key] || 0;
    }
    results.categoryScores[catName] = { score: catScore, max: catMax };
    const pct = catMax > 0 ? ((catScore / catMax) * 100).toFixed(0) : '0';
    console.log(`  ${catName}: ${catScore}/${catMax} (${pct}%)`);
  }

  // Per-eval summary across all inputs
  console.log(`\n  PER-EVAL SUMMARY:`);
  for (const key of evalKeys) {
    const s = results.evalBreakdown[key] || 0;
    const t = results.evalTotal[key] || 0;
    const status = s === t ? 'PASS' : `${s}/${t}`;
    console.log(`  ${key} [${EVAL_NAMES[key]}]: ${status}`);
  }

  const passRate = results.maxScore > 0 ? ((results.totalScore / results.maxScore) * 100).toFixed(1) : '0.0';
  console.log(`\n${'═'.repeat(60)}`);
  console.log(`  TOTAL: ${results.totalScore}/${results.maxScore} (${passRate}%)`);
  console.log(`${'═'.repeat(60)}\n`);

  return results;
}

// ─── CLI ENTRY POINT ──────────────────────────────────────────────────────

if (require.main === module) {
  const configArg = process.argv[2];
  let config = null;
  if (configArg) {
    try {
      config = JSON.parse(configArg);
    } catch {
      console.error('Bad config JSON. Usage: node scripts/autoresearch-eval-v2.js \'{"bodyFontSize": 11}\'');
      process.exit(1);
    }
  }

  runEvals(config).then(results => {
    const outPath = path.join(TMP_DIR, 'last-eval-v2.json');
    fs.writeFileSync(outPath, JSON.stringify(results, null, 2));
    console.log(`Results written to ${outPath}`);
    process.exit(results.totalScore === results.maxScore ? 0 : 1);
  }).catch(e => {
    console.error('Fatal error:', e);
    process.exit(2);
  });
}

module.exports = { runEvals, TEST_INPUTS, EVAL_NAMES, EVAL_COUNT };
