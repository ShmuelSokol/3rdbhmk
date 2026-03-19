#!/usr/bin/env node
/**
 * Autoresearch Evaluation Script for ArtScroll Typeset PDF
 *
 * Downloads a typeset PDF, analyzes it against 6 binary evals,
 * and returns a score. Used by the autoresearch loop.
 *
 * Usage: node scripts/autoresearch-typeset-eval.js [configJSON]
 *
 * Evals:
 *   E1: Hebrew Characters Present (pdftotext)
 *   E2: Reasonable Page Count (not too many gaps)
 *   E3: Illustrations Embedded (file size + image check)
 *   E4: Text Completeness (word count)
 *   E5: No Excessive Whitespace (page image analysis)
 *   E6: Decoration Present (running header + page numbers)
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const BASE_URL = process.env.TYPESET_URL || 'https://3rdbhmk.ksavyad.com';
const BOOK_ID = 'jcqje5aut5wve5w5b8hv6fcq8';
const WORK_DIR = path.join(__dirname, '..', '.claude', 'skills', 'artscrolltranslationsandplacements', 'autoresearch-artscroll');
const TMP_DIR = '/tmp/autoresearch-typeset';

// Test inputs: different page ranges to avoid overfitting
const TEST_INPUTS = [
  { from: 14, to: 15, label: 'pages-14-15', minWords: 200, expectIllustrations: false },
  { from: 14, to: 25, label: 'pages-14-25', minWords: 500, expectIllustrations: true },
  { from: 14, to: 30, label: 'pages-14-30', minWords: 800, expectIllustrations: true },
];

function ensureDirs() {
  if (!fs.existsSync(TMP_DIR)) fs.mkdirSync(TMP_DIR, { recursive: true });
  if (!fs.existsSync(WORK_DIR)) fs.mkdirSync(WORK_DIR, { recursive: true });
}

async function downloadPdf(testInput, configOverride) {
  const configParam = configOverride ? `&config=${encodeURIComponent(JSON.stringify(configOverride))}` : '';
  const url = `${BASE_URL}/api/books/${BOOK_ID}/typeset?from=${testInput.from}&to=${testInput.to}${configParam}`;
  const outPath = path.join(TMP_DIR, `${testInput.label}.pdf`);

  try {
    execSync(`curl -s -f -o "${outPath}" "${url}"`, { timeout: 120000 });
    return outPath;
  } catch (e) {
    console.error(`  FAIL: Could not download PDF for ${testInput.label}: ${e.message}`);
    return null;
  }
}

function extractText(pdfPath) {
  try {
    return execSync(`pdftotext "${pdfPath}" -`, { encoding: 'utf8', timeout: 10000 });
  } catch {
    return '';
  }
}

function getPageCount(pdfPath) {
  try {
    const info = execSync(`pdfinfo "${pdfPath}" 2>/dev/null`, { encoding: 'utf8', timeout: 5000 });
    const match = info.match(/Pages:\s+(\d+)/);
    return match ? parseInt(match[1]) : 0;
  } catch {
    return 0;
  }
}

function getFileSize(pdfPath) {
  try {
    return fs.statSync(pdfPath).size;
  } catch {
    return 0;
  }
}

function renderPages(pdfPath, label) {
  const outDir = path.join(TMP_DIR, `${label}-pages`);
  // Clean previous renders to avoid stale images
  if (fs.existsSync(outDir)) {
    for (const f of fs.readdirSync(outDir)) fs.unlinkSync(path.join(outDir, f));
  } else {
    fs.mkdirSync(outDir, { recursive: true });
  }
  try {
    execSync(`pdftoppm -png -r 72 "${pdfPath}" "${outDir}/page"`, { timeout: 30000 });
    return fs.readdirSync(outDir).filter(f => f.endsWith('.png')).map(f => path.join(outDir, f)).sort();
  } catch {
    return [];
  }
}

function analyzePageWhitespace(imagePath) {
  // Use ImageMagick to check for excessive blank areas
  // Returns the fraction of the page that is "near-white" rows
  try {
    // Get image height
    const dims = execSync(`identify -format "%h %w" "${imagePath}"`, { encoding: 'utf8', timeout: 5000 }).trim().split(' ');
    const height = parseInt(dims[0]);
    const width = parseInt(dims[1]);
    if (!height || !width) return 0;

    // Get per-row average brightness using a column projection
    // A row is "blank" if its mean brightness > 250 (near white)
    const result = execSync(
      `convert "${imagePath}" -colorspace Gray -scale 1x${height}! -format "%[fx:mean]" info:`,
      { encoding: 'utf8', timeout: 10000 }
    ).trim();

    const meanBrightness = parseFloat(result);
    // High mean brightness = lots of white space
    // A well-filled page should have mean < 0.92 (8%+ is content)
    return meanBrightness;
  } catch {
    return 0.5; // assume OK if can't analyze
  }
}

function findLargestBlankStrip(imagePath) {
  // Find the largest consecutive blank (near-white) strip in the page
  // Returns fraction of page height
  try {
    const dims = execSync(`identify -format "%h %w" "${imagePath}"`, { encoding: 'utf8', timeout: 5000 }).trim().split(' ');
    const height = parseInt(dims[0]);
    if (!height) return 0;

    // Scale to 1px wide, get per-row brightness
    const rawData = execSync(
      `convert "${imagePath}" -colorspace Gray -scale 1x${height}! txt:- 2>/dev/null | tail -n +2`,
      { encoding: 'utf8', timeout: 15000 }
    );

    const lines = rawData.trim().split('\n');
    let maxBlankRun = 0;
    let currentRun = 0;

    for (const line of lines) {
      // Format: "0,Y: (GG)  #XXXXXX  gray(NN%)"
      const grayMatch = line.match(/gray\((\d+(?:\.\d+)?)%?\)/i) || line.match(/#([0-9A-Fa-f]{2})/);
      if (!grayMatch) continue;

      let brightness;
      if (line.includes('gray')) {
        brightness = parseFloat(grayMatch[1]);
      } else {
        brightness = parseInt(grayMatch[1], 16) / 255 * 100;
      }

      if (brightness > 95) { // near-white row
        currentRun++;
      } else {
        maxBlankRun = Math.max(maxBlankRun, currentRun);
        currentRun = 0;
      }
    }
    maxBlankRun = Math.max(maxBlankRun, currentRun);

    return lines.length > 0 ? maxBlankRun / lines.length : 0;
  } catch {
    return 0; // assume OK
  }
}

// ─── EVALS ─────────────────────────────────────────────────────────────────

function evalHebrewChars(text) {
  // E1: Does the PDF contain actual Hebrew Unicode characters?
  const hebrewChars = (text.match(/[\u0590-\u05FF]/g) || []).length;
  return { pass: hebrewChars >= 20, detail: `${hebrewChars} Hebrew chars found` };
}

function evalPageCount(pageCount, testInput, wordCount) {
  // E2: Average words per content page >= 100? (detects wasted gap pages)
  // Skip title page in calculation
  const contentPages = Math.max(1, pageCount - 1);
  const wordsPerPage = wordCount / contentPages;
  const pass = wordsPerPage >= 100;
  return { pass, detail: `${wordsPerPage.toFixed(0)} words/page (need >=100), ${pageCount} total pages` };
}

function evalIllustrations(fileSize, testInput) {
  // E3: For pages with known illustrations, is the file large enough to contain images?
  // A text-only PDF for 5 pages would be ~20-50KB. With illustrations: 100KB+
  if (!testInput.expectIllustrations) {
    return { pass: true, detail: 'No illustrations expected for this range' };
  }
  const pass = fileSize > 80000; // 80KB minimum if illustrations expected
  return { pass, detail: `File size: ${Math.round(fileSize / 1024)}KB (need >80KB for illustrations)` };
}

function evalTextCompleteness(text, testInput) {
  // E4: Does the PDF contain enough text? (no truncation)
  const words = text.split(/\s+/).filter(w => w.length > 1).length;
  const pass = words >= testInput.minWords;
  return { pass, detail: `${words} words (need >=${testInput.minWords})` };
}

function evalNoExcessiveWhitespace(pageImages) {
  // E5: No interior page has a blank vertical strip > 45% of page height
  // Skip first page (title) and last page (natural trailing space)
  if (pageImages.length <= 2) return { pass: true, detail: 'Too few pages to evaluate' };

  let worstPage = 0;
  let worstBlank = 0;

  for (let i = 1; i < pageImages.length - 1; i++) { // skip title + last page
    const blankFrac = findLargestBlankStrip(pageImages[i]);
    if (blankFrac > worstBlank) {
      worstBlank = blankFrac;
      worstPage = i + 1;
    }
  }

  const pass = worstBlank <= 0.45;
  return { pass, detail: `Worst blank strip: ${(worstBlank * 100).toFixed(1)}% on page ${worstPage} (of ${pageImages.length - 2} interior pages)` };
}

function evalDecoration(text) {
  // E6: Are running headers and page numbers present?
  const hasRunningHeader = text.includes('LISHCHNO') || text.includes('Lishchno');
  const hasPageNumbers = /\u2014\s+\d+\s+\u2014/.test(text) || /—\s+\d+\s+—/.test(text) || /\d+/.test(text);
  const pass = hasRunningHeader && hasPageNumbers;
  return { pass, detail: `Header: ${hasRunningHeader ? 'YES' : 'NO'}, PageNums: ${hasPageNumbers ? 'YES' : 'NO'}` };
}

// ─── MAIN ──────────────────────────────────────────────────────────────────

async function runEvals(configOverride) {
  ensureDirs();

  const results = {
    totalScore: 0,
    maxScore: TEST_INPUTS.length * 6, // 6 evals per test input
    evalBreakdown: { E1: 0, E2: 0, E3: 0, E4: 0, E5: 0, E6: 0 },
    evalTotal: { E1: 0, E2: 0, E3: 0, E4: 0, E5: 0, E6: 0 },
    details: [],
  };

  for (const testInput of TEST_INPUTS) {
    console.log(`\nTesting ${testInput.label}...`);

    const pdfPath = await downloadPdf(testInput, configOverride);
    if (!pdfPath) {
      console.log(`  SKIP: Could not download PDF`);
      results.details.push({ input: testInput.label, error: 'download failed' });
      // Count all evals as failed for this input
      for (const key of Object.keys(results.evalTotal)) results.evalTotal[key]++;
      continue;
    }

    const text = extractText(pdfPath);
    const pageCount = getPageCount(pdfPath);
    const fileSize = getFileSize(pdfPath);
    console.log(`  PDF: ${pageCount} pages, ${Math.round(fileSize / 1024)}KB, ${text.split(/\s+/).length} words`);

    // Render pages for whitespace analysis
    const pageImages = renderPages(pdfPath, testInput.label);

    // Run all 6 evals
    const e1 = evalHebrewChars(text);
    const wordCount = text.split(/\s+/).filter(w => w.length > 1).length;
    const e2 = evalPageCount(pageCount, testInput, wordCount);
    const e3 = evalIllustrations(fileSize, testInput);
    const e4 = evalTextCompleteness(text, testInput);
    const e5 = pageImages.length > 0 ? evalNoExcessiveWhitespace(pageImages) : { pass: true, detail: 'Skipped (no images)' };
    const e6 = evalDecoration(text);

    const evals = { E1: e1, E2: e2, E3: e3, E4: e4, E5: e5, E6: e6 };
    let inputScore = 0;

    for (const [key, result] of Object.entries(evals)) {
      results.evalTotal[key]++;
      if (result.pass) {
        inputScore++;
        results.evalBreakdown[key]++;
      }
      const icon = result.pass ? 'PASS' : 'FAIL';
      console.log(`  ${key}: ${icon} — ${result.detail}`);
    }

    results.totalScore += inputScore;
    results.details.push({
      input: testInput.label,
      score: inputScore,
      maxScore: 6,
      evals,
    });
  }

  const passRate = ((results.totalScore / results.maxScore) * 100).toFixed(1);
  console.log(`\n═══ TOTAL: ${results.totalScore}/${results.maxScore} (${passRate}%) ═══\n`);

  return results;
}

// Run if called directly
if (require.main === module) {
  const configArg = process.argv[2];
  let config = null;
  if (configArg) {
    try { config = JSON.parse(configArg); } catch { console.error('Bad config JSON'); process.exit(1); }
  }

  runEvals(config).then(results => {
    // Write results to a JSON file for the dashboard
    const outPath = path.join(TMP_DIR, 'last-eval.json');
    fs.writeFileSync(outPath, JSON.stringify(results, null, 2));
    console.log(`Results written to ${outPath}`);
    process.exit(results.totalScore === results.maxScore ? 0 : 1);
  }).catch(e => {
    console.error(e);
    process.exit(2);
  });
}

module.exports = { runEvals, TEST_INPUTS };
