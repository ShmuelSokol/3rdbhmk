#!/usr/bin/env node
/**
 * Insert inline Hebrew for pasuk/Gemara quotations.
 *
 * For each region that quotes a pasuk in English (e.g. "as it is written (Devarim 12:13): ...")
 * but doesn't have the Hebrew source text inline, this script:
 * 1. Extracts Hebrew phrases from the OCR source text (hebrewText)
 * 2. Matches them to quote patterns in the English translation
 * 3. Inserts the Hebrew before the English quote in ArtScroll em-dash format
 *
 * Run: node scripts/insert-pesukim-hebrew.js [--dry-run] [--page=N]
 */

const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

const DRY_RUN = process.argv.includes('--dry-run');
const PAGE_ARG = process.argv.find(a => a.startsWith('--page='));
const SINGLE_PAGE = PAGE_ARG ? parseInt(PAGE_ARG.split('=')[1]) : null;
const BOOK_ID = 'jcqje5aut5wve5w5b8hv6fcq8';

function hasHebrew(text) {
  return /[\u0590-\u05FF]/.test(text);
}

/** Extract all Hebrew phrases (2-10 words) from OCR text, preserving order */
function extractHebrewPhrases(hebrewText) {
  if (!hebrewText) return [];
  const phrases = [];
  // Split by punctuation/delimiters
  const segments = hebrewText.split(/[,.:;!?\[\](){}\/\n\r]/).map(s => s.trim()).filter(s => s.length > 2);
  for (const seg of segments) {
    const words = seg.split(/\s+/).filter(w => /[\u0590-\u05FF]/.test(w));
    if (words.length >= 2 && words.length <= 10) {
      phrases.push(words.join(' '));
    }
    // Also extract sub-phrases for long segments
    if (words.length > 6) {
      for (let start = 0; start < words.length - 2; start++) {
        for (let len = 2; len <= Math.min(6, words.length - start); len++) {
          const sub = words.slice(start, start + len).join(' ');
          if (!phrases.includes(sub)) phrases.push(sub);
        }
      }
    }
  }
  return phrases;
}

/** Find the best Hebrew phrase to match a quote position */
function findBestPhrase(phrases, usedIndices) {
  for (let i = 0; i < phrases.length; i++) {
    if (!usedIndices.has(i) && phrases[i].length >= 4) {
      return { phrase: phrases[i], index: i };
    }
  }
  return null;
}

/**
 * Insert Hebrew at quote patterns in the English text.
 * Only inserts at explicit quote introductions — does NOT add a generic header.
 */
function insertPesukimHebrew(hebrewText, englishText) {
  if (!englishText || !hebrewText) return englishText;

  const phrases = extractHebrewPhrases(hebrewText);
  if (phrases.length === 0) return englishText;

  let enhanced = englishText;
  const usedIndices = new Set();

  // Pattern 1: "as it is written (Source N:N): English quote"
  // Insert Hebrew before the English quote
  const writtenPattern = /((?:as it is written|it is written|as it states|as it says|it states|the pasuk says|the pasuk states|as the pasuk|the Navi says|Scripture states|the verse says|it is stated)\s*(?:\([^)]+\))?\s*:\s*)([""\u201C]?)([^"""\u201D\n]{8,120})/gi;

  enhanced = enhanced.replace(writtenPattern, (match, prefix, openQuote, englishQuote) => {
    // Skip if already has Hebrew
    if (hasHebrew(match)) return match;
    const best = findBestPhrase(phrases, usedIndices);
    if (best && best.phrase.length >= 4) {
      usedIndices.add(best.index);
      return `${prefix}${best.phrase} \u2014 ${openQuote}${englishQuote}`;
    }
    return match;
  });

  // Pattern 2: "The Mishnah/Gemara teaches/says: English quote"
  const talmudPattern = /((?:The (?:Mishnah|Gemara|Baraisa|Tosefta|Beraisa) (?:teaches|says|states|asks|answers|explains|records|rules))\s*(?:\([^)]+\))?\s*:\s*)/gi;

  enhanced = enhanced.replace(talmudPattern, (match, prefix) => {
    if (hasHebrew(match)) return match;
    const best = findBestPhrase(phrases, usedIndices);
    if (best && best.phrase.length >= 4) {
      usedIndices.add(best.index);
      return `${prefix}${best.phrase} \u2014 `;
    }
    return match;
  });

  // Pattern 3: "Chazal said/taught/expounded: English quote"
  const chazalPattern = /(Chazal (?:said|taught|teach|expounded|derived|learned|explained)\s*(?:[^:]{0,40}):\s*)([""\u201C]?)([^"""\u201D\n]{8,80})/gi;

  enhanced = enhanced.replace(chazalPattern, (match, prefix, openQuote, englishQuote) => {
    if (hasHebrew(match)) return match;
    const best = findBestPhrase(phrases, usedIndices);
    if (best && best.phrase.length >= 4) {
      usedIndices.add(best.index);
      return `${prefix}${best.phrase} \u2014 ${openQuote}${englishQuote}`;
    }
    return match;
  });

  // Pattern 4: Inline Mishnah/Gemara quote at paragraph start
  // "באו לשילה — They came to Shiloh" style (already has Hebrew, skip)
  // But if paragraph starts with English and has a colon-introduced quote, add Hebrew
  const colonQuote = /^([A-Z][^:]{10,60}:\s*)([""\u201C]?)([^"""\u201D\n]{8,80})/m;
  if (!hasHebrew(enhanced.substring(0, 30))) {
    const m = enhanced.match(colonQuote);
    if (m && !hasHebrew(m[0])) {
      const best = findBestPhrase(phrases, usedIndices);
      if (best && best.phrase.length >= 4) {
        usedIndices.add(best.index);
        enhanced = enhanced.replace(colonQuote, `$1${best.phrase} \u2014 $2$3`);
      }
    }
  }

  return enhanced;
}

async function main() {
  const where = { bookId: BOOK_ID };
  const pageFilter = SINGLE_PAGE
    ? { ...where, pageNumber: SINGLE_PAGE }
    : where;

  const pages = await prisma.page.findMany({
    where: pageFilter,
    include: {
      regions: {
        where: { translatedText: { not: null } },
        orderBy: { regionIndex: 'asc' }
      }
    },
    orderBy: { pageNumber: 'asc' },
  });

  // Skip pages 14-15 (manually crafted)
  const PROTECTED = new Set([14, 15]);

  // Quote patterns to identify regions worth processing
  const quotePattern = /(?:as it is written|it is written|as it states|as it says|it states|the pasuk says|the pasuk states|the Navi says|Scripture states|the verse says|it is stated|Chazal.*?(?:said|taught|teach|expounded|derived)|The (?:Mishnah|Gemara|Baraisa) (?:teaches|says|states))/i;

  let updated = 0, skipped = 0, noChange = 0;

  for (const page of pages) {
    if (PROTECTED.has(page.pageNumber)) { skipped += page.regions.length; continue; }

    for (const region of page.regions) {
      if (!region.translatedText || !region.hebrewText) { skipped++; continue; }

      // Only process regions that have quote patterns
      if (!quotePattern.test(region.translatedText)) { skipped++; continue; }

      const newText = insertPesukimHebrew(region.hebrewText, region.translatedText);

      if (newText === region.translatedText) { noChange++; continue; }

      if (DRY_RUN) {
        console.log(`\n--- Page ${page.pageNumber}, Region #${region.regionIndex} ---`);
        // Show the diff around the inserted Hebrew
        const oldLines = region.translatedText.split('\n');
        const newLines = newText.split('\n');
        for (let i = 0; i < newLines.length; i++) {
          if (i >= oldLines.length || newLines[i] !== oldLines[i]) {
            console.log('  BEFORE:', (oldLines[i] || '').substring(0, 120));
            console.log('  AFTER: ', newLines[i].substring(0, 120));
            break;
          }
        }
        // If no line diff found, show first difference
        if (newText.length !== region.translatedText.length) {
          const diffPos = [...newText].findIndex((c, i) => c !== region.translatedText[i]);
          if (diffPos >= 0) {
            console.log('  AT pos', diffPos + ':', JSON.stringify(newText.substring(Math.max(0, diffPos - 30), diffPos + 80)));
          }
        }
        updated++;
      } else {
        await prisma.contentRegion.update({
          where: { id: region.id },
          data: { translatedText: newText }
        });
        updated++;
        if (updated % 20 === 0) console.log(`Updated ${updated} regions (page ${page.pageNumber})...`);
      }
    }
  }

  console.log(`\nDone! Updated: ${updated}, Skipped: ${skipped}, No change: ${noChange}`);
  await prisma.$disconnect();
}

main().catch(e => { console.error(e); process.exit(1); });
