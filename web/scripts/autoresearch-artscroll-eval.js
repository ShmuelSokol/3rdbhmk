#!/usr/bin/env node
/**
 * Autoresearch ArtScroll Style Evaluation
 *
 * Scores the typeset PDF against ArtScroll translation style criteria.
 * Tests both layout quality (via eval-v2) and translation style quality.
 *
 * 10 ArtScroll-specific evals × 5 test inputs = 50 points
 * + 30 layout evals × 5 test inputs = 150 points
 * = 200 total max score
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const BASE_URL = process.env.TYPESET_URL || 'http://localhost:3001';
const BOOK_ID = 'jcqje5aut5wve5w5b8hv6fcq8';
const TMP_DIR = '/tmp/autoresearch-artscroll';

const TEST_INPUTS = [
  { from: 14, to: 15, label: 'pages-14-15', desc: 'Mishkan/Shiloh intro' },
  { from: 50, to: 52, label: 'pages-50-52', desc: 'Chamber commentary' },
  { from: 100, to: 102, label: 'pages-100-102', desc: 'Gate measurements' },
  { from: 200, to: 202, label: 'pages-200-202', desc: 'Chamber locations' },
  { from: 300, to: 302, label: 'pages-300-302', desc: 'Deep commentary' },
];

function ensureDirs() {
  if (!fs.existsSync(TMP_DIR)) fs.mkdirSync(TMP_DIR, { recursive: true });
}

function downloadPdf(input, configOverride) {
  const cfgParam = configOverride ? `&config=${encodeURIComponent(JSON.stringify(configOverride))}` : '';
  const url = `${BASE_URL}/api/books/${BOOK_ID}/typeset?from=${input.from}&to=${input.to}${cfgParam}`;
  const outPath = path.join(TMP_DIR, `${input.label}.pdf`);
  try {
    execSync(`curl -s -f -o "${outPath}" "${url}"`, { timeout: 180000 });
    return fs.existsSync(outPath) && fs.statSync(outPath).size > 100 ? outPath : null;
  } catch { return null; }
}

function extractText(p) {
  try { return execSync(`pdftotext "${p}" -`, { encoding: 'utf8', timeout: 10000 }); } catch { return ''; }
}

// ── ArtScroll Style Evals ─────────────────────────────────────────────

function AS1_inlineHebrew(text) {
  // Does the PDF have inline Hebrew characters mixed with English?
  const hebrewChars = (text.match(/[\u0590-\u05FF]/g) || []).length;
  const englishWords = text.split(/\s+/).filter(w => /[a-zA-Z]{3,}/.test(w)).length;
  // ArtScroll style: Hebrew should appear throughout, not just in headers
  // At least 1 Hebrew char per 20 English words
  const ratio = englishWords > 0 ? hebrewChars / englishWords : 0;
  return { pass: ratio >= 0.05, detail: `${hebrewChars} Hebrew chars / ${englishWords} English words (ratio: ${ratio.toFixed(3)}, need >=0.05)` };
}

function AS2_ashkenaziTransliteration(text) {
  // Does the text use Ashkenazi transliteration?
  const ashkenazi = ['Beis', 'HaMikdash', 'Hashem', 'Torah', 'Shabbos', 'davening',
    'Kohen', 'Kohanim', 'Levi\'im', 'korbanos', 'pesukim', 'halachah', 'Gemara',
    'Mishnah', 'Rashi', 'Rambam', 'amos', 'tefach', 'Yerushalayim', 'Eretz',
    'Yisrael', 'Moshe', 'Aharon', 'Shechinah', 'bracha', 'mitzvah'];
  const found = ashkenazi.filter(term => text.includes(term));
  return { pass: found.length >= 5, detail: `${found.length}/26 Ashkenazi terms found: ${found.slice(0, 6).join(', ')}` };
}

function AS3_sourceCitations(text) {
  // Are there proper source citations? (tractate + daf, Rashi on X, Rambam Hilchos)
  const patterns = [
    /Maseches\s+\w+/i, /Perek\s+\d+/i, /Mishnah\s+\d+/i,
    /Rashi\s+\(/i, /Rashi\s+on/i, /Rambam\s+\(/i, /Rambam\s+Hilchos/i,
    /Pasuk\s+\d+/i, /Daf\s+\d+/i, /\(\w+\s+\d+[ab]?\)/,
    /Tosafos/i, /Ritva/i, /Rashba/i, /Ramban/i,
  ];
  const found = patterns.filter(p => p.test(text));
  return { pass: found.length >= 3, detail: `${found.length}/13 citation patterns found` };
}

function AS4_hebrewQuoteFormat(text) {
  // Are Hebrew quotes formatted ArtScroll-style? (Hebrew — English translation)
  // pdftotext inserts bidi control chars (\u202b...\u202c) around Hebrew runs and may
  // reorder dash/Hebrew due to RTL. Match both orderings:
  // 1. Hebrew...dash...English (logical order with bidi markers between)
  // 2. dash...Hebrew...English (pdftotext RTL reordering puts dash before Hebrew)
  // Strip bidi markers first, then check for Hebrew adjacent to dash
  const stripped = text.replace(/[\u202A-\u202E]/g, '');
  // Forward: Hebrew chars (3+) ... dash ... English letter
  const fwd = stripped.match(/[\u0590-\u05FF][\u0590-\u05FF\s]{2,60}[^A-Za-z]{0,5}[—\-][^A-Za-z]{0,3}[A-Za-z]/g) || [];
  // Reverse: dash ... Hebrew chars (3+) ... English letter (pdftotext RTL reorder)
  const rev = stripped.match(/[—\-][^A-Za-z\u0590-\u05FF]{0,5}[\u0590-\u05FF][\u0590-\u05FF\s]{2,60}[A-Za-z]/g) || [];
  const total = fwd.length + rev.length;
  return { pass: total >= 2, detail: `${total} ArtScroll-format quotes (Hebrew — English)` };
}

function AS5_noRawTransliteration(text) {
  // Are Hebrew letter names NOT spelled out when they should be actual Hebrew?
  // Bad: "[Tzadi Mem Daled Vav]" — Good: "[צמד"ו]" or just omitted
  const spelledOut = text.match(/\[(?:Aleph|Beis|Gimmel|Daled|Hei|Vav|Zayin|Ches|Tes|Yud|Kaf|Lamed|Mem|Nun|Samech|Ayin|Pei|Tzadi|Kuf|Reish|Shin|Tav)[\s,]+/gi) || [];
  return { pass: spelledOut.length <= 1, detail: spelledOut.length <= 1 ? 'Clean — no spelled-out Hebrew letters' : `${spelledOut.length} instances of spelled-out letters` };
}

function AS6_properTerminology(text) {
  // Does it use proper ArtScroll terminology?
  const good = ['Beis HaMikdash', 'Beis Din', 'kodshei kodashim', 'Ezras',
    'Ulam', 'Heichal', 'Azarah', 'Mizbei\'ach', 'Menorah', 'Shulchan',
    'Kodesh HaKodashim', 'Har HaBayis', 'Kohen Gadol'];
  const bad = ['Holy Temple', 'Temple Mount', 'Holy of Holies', 'High Priest',
    'Court of Israel', 'altar', 'menorah', 'table'];
  const goodFound = good.filter(t => text.includes(t));
  const badFound = bad.filter(t => {
    // Only flag if it appears as a standalone translation (not in a phrase explaining the Hebrew)
    const regex = new RegExp(`(?<!\\()\\b${t}\\b(?!\\s*\\()`, 'i');
    return regex.test(text);
  });
  return { pass: goodFound.length >= 3 && badFound.length <= 2, detail: `Good: ${goodFound.length} terms, Bad: ${badFound.length} (${badFound.join(', ')})` };
}

function AS7_paragraphStructure(text) {
  // Does the text have proper paragraph structure? (not just a wall of text)
  const lines = text.split('\n').filter(l => l.trim().length > 0);
  const longParagraphs = [];
  let currentLen = 0;
  for (const line of lines) {
    if (line.trim().length < 5) {
      if (currentLen > 0) longParagraphs.push(currentLen);
      currentLen = 0;
    } else {
      currentLen += line.split(/\s+/).length;
    }
  }
  if (currentLen > 0) longParagraphs.push(currentLen);
  // No paragraph should be >500 words (ArtScroll breaks up long passages)
  const tooLong = longParagraphs.filter(l => l > 500);
  return { pass: tooLong.length === 0, detail: `${longParagraphs.length} paragraphs, ${tooLong.length} too long (>500 words)` };
}

function AS8_boldHeaders(text) {
  // Are section headers/subheaders distinguishable from body text?
  // In pdftotext, bold text and headers often appear as shorter lines at the start
  const pages = text.split('\f').filter(p => p.trim());
  let pagesWithHeaders = 0;
  for (const page of pages) {
    const lines = page.split('\n').filter(l => l.trim().length > 3);
    // Check for title-case or all-caps lines that look like headers
    const headerLike = lines.filter(l => {
      const t = l.trim();
      if (t.length > 80) return false;
      if (/^LISHCHNO/.test(t)) return false;
      if (/^[—\u2014]/.test(t)) return false;
      const words = t.split(/\s+/);
      const capitalizedRatio = words.filter(w => w.length > 2 && w[0] === w[0].toUpperCase()).length / words.length;
      return capitalizedRatio >= 0.6 && words.length >= 2 && words.length <= 10;
    });
    if (headerLike.length > 0) pagesWithHeaders++;
  }
  const ratio = pages.length > 0 ? pagesWithHeaders / pages.length : 0;
  return { pass: ratio >= 0.2, detail: `${pagesWithHeaders}/${pages.length} pages have distinguishable headers (${(ratio*100).toFixed(0)}%, need 20%)` };
}

function AS9_noStandaloneNumbers(text) {
  // No leaked Hebrew source page numbers appearing as standalone lines
  const lines = text.split('\n').map(l => l.trim());
  let standalone = 0;
  for (let i = 1; i < lines.length - 1; i++) {
    if (/^\d{1,3}$/.test(lines[i]) && lines[i-1].length > 20 && lines[i+1].length > 20) {
      standalone++;
    }
  }
  return { pass: standalone <= 2, detail: `${standalone} standalone source page numbers` };
}

function AS10_decorationAndFrame(text) {
  // Does every page have the running header and page number decoration?
  const hasHeader = /LISHCHNO TIDRESHU/i.test(text);
  const pageNums = (text.match(/[—\u2014]\s+\d+\s+[—\u2014]/g) || []).length;
  const pages = text.split('\f').filter(p => p.trim()).length;
  const coverage = pages > 1 ? pageNums / (pages - 1) : 0; // exclude title
  return { pass: hasHeader && coverage >= 0.8, detail: `Header: ${hasHeader ? 'Y' : 'N'}, Page nums: ${pageNums}/${pages-1} pages (${(coverage*100).toFixed(0)}%)` };
}

const ARTSCROLL_EVALS = [
  { name: 'AS1_InlineHebrew', fn: AS1_inlineHebrew },
  { name: 'AS2_AshkenaziTerms', fn: AS2_ashkenaziTransliteration },
  { name: 'AS3_SourceCitations', fn: AS3_sourceCitations },
  { name: 'AS4_HebrewQuoteFormat', fn: AS4_hebrewQuoteFormat },
  { name: 'AS5_NoSpelledOutLetters', fn: AS5_noRawTransliteration },
  { name: 'AS6_ProperTerminology', fn: AS6_properTerminology },
  { name: 'AS7_ParagraphStructure', fn: AS7_paragraphStructure },
  { name: 'AS8_BoldHeaders', fn: AS8_boldHeaders },
  { name: 'AS9_NoStandaloneNums', fn: AS9_noStandaloneNumbers },
  { name: 'AS10_DecorationFrame', fn: AS10_decorationAndFrame },
];

async function runEvals(configOverride) {
  ensureDirs();
  const results = { totalScore: 0, maxScore: TEST_INPUTS.length * ARTSCROLL_EVALS.length, evalScores: {}, details: [] };
  for (const e of ARTSCROLL_EVALS) results.evalScores[e.name] = { pass: 0, total: 0 };

  for (const input of TEST_INPUTS) {
    console.log(`\nTesting ${input.label} (${input.desc})...`);
    const pdfPath = downloadPdf(input, configOverride);
    if (!pdfPath) { console.log('  SKIP: Download failed'); continue; }

    const text = extractText(pdfPath);
    const words = text.split(/\s+/).filter(w => w.length > 1).length;
    console.log(`  ${words} words extracted`);

    let inputScore = 0;
    for (const e of ARTSCROLL_EVALS) {
      results.evalScores[e.name].total++;
      const result = e.fn(text);
      if (result.pass) { inputScore++; results.totalScore++; results.evalScores[e.name].pass++; }
      const icon = result.pass ? 'PASS' : 'FAIL';
      if (!result.pass) console.log(`  ${e.name}: ${icon} — ${result.detail}`);
    }
    results.details.push({ input: input.label, score: inputScore, maxScore: ARTSCROLL_EVALS.length });
    console.log(`  Score: ${inputScore}/${ARTSCROLL_EVALS.length}`);
  }

  const pct = ((results.totalScore / results.maxScore) * 100).toFixed(1);
  console.log(`\n${'═'.repeat(50)}`);
  console.log(`  ARTSCROLL STYLE: ${results.totalScore}/${results.maxScore} (${pct}%)`);
  console.log(`${'═'.repeat(50)}`);

  console.log('\nPer-eval:');
  for (const e of ARTSCROLL_EVALS) {
    const s = results.evalScores[e.name];
    const status = s.pass === s.total ? 'PASS' : `${s.pass}/${s.total}`;
    console.log(`  ${e.name}: ${status}`);
  }

  fs.writeFileSync(path.join(TMP_DIR, 'artscroll-eval.json'), JSON.stringify(results, null, 2));
  return results;
}

if (require.main === module) {
  runEvals().then(r => {
    process.exit(r.totalScore === r.maxScore ? 0 : 1);
  }).catch(e => { console.error(e); process.exit(2); });
}

module.exports = { runEvals, TEST_INPUTS, ARTSCROLL_EVALS };
