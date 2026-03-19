#!/usr/bin/env node
/**
 * Enhance existing translations with ArtScroll-style inline Hebrew quotes.
 *
 * For each region:
 * 1. Extract Hebrew phrases from the source hebrewText
 * 2. Find where they're referenced in the English translation
 * 3. Insert the original Hebrew inline before the English translation
 * 4. Fix transliteration patterns (spell out Hebrew letter names → actual Hebrew)
 *
 * Run: node scripts/enhance-artscroll.js [--dry-run] [--page=N]
 */

const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

const DRY_RUN = process.argv.includes('--dry-run');
const PAGE_ARG = process.argv.find(a => a.startsWith('--page='));
const SINGLE_PAGE = PAGE_ARG ? parseInt(PAGE_ARG.split('=')[1]) : null;
const BOOK_ID = 'jcqje5aut5wve5w5b8hv6fcq8';

// Hebrew letter name → actual Hebrew character mappings
const LETTER_NAMES = {
  'Aleph': 'א', 'Beis': 'ב', 'Gimmel': 'ג', 'Daled': 'ד', 'Hei': 'ה',
  'Vav': 'ו', 'Zayin': 'ז', 'Ches': 'ח', 'Tes': 'ט', 'Yud': 'י',
  'Kaf': 'כ', 'Lamed': 'ל', 'Mem': 'מ', 'Nun': 'נ', 'Samech': 'ס',
  'Ayin': 'ע', 'Pei': 'פ', 'Tzadi': 'צ', 'Kuf': 'ק', 'Reish': 'ר',
  'Shin': 'ש', 'Tav': 'ת',
};

/** Check if text contains Hebrew characters */
function hasHebrew(text) {
  return /[\u0590-\u05FF]/.test(text);
}

/** Extract short Hebrew phrases (1-8 words) from Hebrew text */
function extractHebrewPhrases(hebrewText) {
  if (!hebrewText) return [];
  // Split by common delimiters and extract phrases
  const phrases = [];
  // Look for quoted phrases or short segments
  const segments = hebrewText.split(/[,.:;!?\-\[\](){}]/).map(s => s.trim()).filter(s => s.length > 1);
  for (const seg of segments) {
    const words = seg.split(/\s+/).filter(w => /[\u0590-\u05FF]/.test(w));
    if (words.length >= 1 && words.length <= 8) {
      phrases.push(words.join(' '));
    }
  }
  return phrases;
}

/** Find the best Hebrew quote to insert before an English phrase */
function findMatchingHebrew(englishPhrase, hebrewPhrases) {
  // Simple heuristic: if the English mentions a specific pasuk/verse reference,
  // look for the corresponding Hebrew
  // This is a basic matching — we rely on position/order
  return null; // Placeholder for now
}

/**
 * Enhance a translation with inline Hebrew:
 * - Insert Hebrew source text at the beginning of Mishnah/pasuk quotes
 * - Replace [Letter Name] patterns with actual Hebrew
 * - Add Hebrew for verse quotes that are currently transliterated
 */
function enhanceTranslation(hebrewText, englishText) {
  if (!englishText || !hebrewText) return englishText;
  if (hasHebrew(englishText)) return englishText; // Already has Hebrew

  let enhanced = englishText;

  // 1. Replace spelled-out Hebrew letter references with actual letters
  // e.g., "[Tzadi Mem Daled Vav]" → "[צמד"ו]"
  enhanced = enhanced.replace(/\[([A-Z][a-z]+ )+[A-Z][a-z]+\]/g, (match) => {
    const inner = match.slice(1, -1);
    const words = inner.split(' ');
    let hebrew = '';
    let allMatched = true;
    for (const w of words) {
      if (LETTER_NAMES[w]) {
        hebrew += LETTER_NAMES[w];
      } else {
        allMatched = false;
        break;
      }
    }
    return allMatched && hebrew ? `[${hebrew}]` : match;
  });

  // 2. Extract Hebrew quotes from source and insert inline
  // Look for verse patterns in the Hebrew: "כתוב ... : ..." or quoted passages
  const hebrewQuotePatterns = hebrewText.match(/[\u0590-\u05FF][\u0590-\u05FF\s\u0027\u05F3\u05F4]{3,40}/g) || [];

  // For each Hebrew phrase, check if the English has a translation of it
  // and insert the Hebrew before the English translation
  // Strategy: find verse quotes in English ("As it is written:", followed by translation)
  // and prepend the Hebrew source

  // Look for patterns like: 'as it is written (Reference): "English quote"'
  // and insert Hebrew before the English quote
  const quotePattern = /((?:as it is written|it is written|as it states|the pasuk says|the Navi says|Chazal said)[^:]*:\s*)([""]?)([^"""\n]{10,80})/gi;

  // Only insert if we have Hebrew phrases available
  if (hebrewQuotePatterns.length > 0) {
    let quoteIdx = 0;
    enhanced = enhanced.replace(quotePattern, (match, prefix, openQuote, englishQuote) => {
      // Find the next Hebrew phrase that could be this quote
      if (quoteIdx < hebrewQuotePatterns.length) {
        const hebPhrase = hebrewQuotePatterns[quoteIdx].trim();
        quoteIdx++;
        if (hebPhrase.length >= 4 && hebPhrase.length <= 50) {
          return `${prefix}${hebPhrase} — ${openQuote}${englishQuote}`;
        }
      }
      return match;
    });
  }

  // 3. For Mishnah/Gemara quotes that start a paragraph, add Hebrew prefix
  // Pattern: "The Mishnah teaches:" or "The Gemara says:" at start
  const mishnahPattern = /^(The (?:Mishnah|Gemara|Baraisa) (?:teaches|says|states)[^:]*:\s*)/;
  const mishnahMatch = enhanced.match(mishnahPattern);
  if (mishnahMatch && hebrewQuotePatterns.length > 0) {
    const firstHebPhrase = hebrewQuotePatterns[0].trim();
    if (firstHebPhrase.length >= 3 && firstHebPhrase.length <= 30 && !enhanced.includes(firstHebPhrase)) {
      enhanced = enhanced.replace(mishnahPattern, `$1\n${firstHebPhrase} — `);
    }
  }

  // 4. Insert the main Hebrew verse at the top if this is a verse commentary
  // (region starts with a pasuk quote in Hebrew)
  const hebrewWords = hebrewText.split(/\s+/).filter(w => /[\u0590-\u05FF]/.test(w));
  if (hebrewWords.length >= 2 && hebrewWords.length <= 12) {
    // The Hebrew text is a short verse — this is likely a pasuk being commented on
    const hebrewVerse = hebrewWords.join(' ');
    if (!enhanced.includes(hebrewVerse) && hebrewVerse.length >= 4) {
      // Check if the English starts with a translation of this verse
      const firstSentence = enhanced.split(/[.!]\s/)[0];
      if (firstSentence && firstSentence.length < 150) {
        enhanced = `${hebrewVerse} — ${enhanced}`;
      }
    }
  }

  return enhanced;
}

async function main() {
  const where = { bookId: BOOK_ID };
  if (SINGLE_PAGE) {
    console.log(`Processing only page ${SINGLE_PAGE}`);
  }

  const pages = await prisma.page.findMany({
    where: SINGLE_PAGE
      ? { ...where, pageNumber: SINGLE_PAGE }
      : where,
    include: {
      regions: {
        where: { translatedText: { not: null } },
        orderBy: { regionIndex: 'asc' }
      }
    },
    orderBy: { pageNumber: 'asc' },
  });

  let enhanced = 0;
  let skipped = 0;
  let unchanged = 0;

  for (const page of pages) {
    for (const region of page.regions) {
      if (!region.translatedText || !region.hebrewText) {
        skipped++;
        continue;
      }

      // Skip if already has inline Hebrew
      if (hasHebrew(region.translatedText)) {
        skipped++;
        continue;
      }

      const newText = enhanceTranslation(region.hebrewText, region.translatedText);

      if (newText === region.translatedText) {
        unchanged++;
        continue;
      }

      if (DRY_RUN) {
        console.log(`\n--- Page ${page.pageNumber}, Region #${region.regionIndex} ---`);
        console.log('BEFORE:', region.translatedText.substring(0, 100));
        console.log('AFTER:', newText.substring(0, 100));
        enhanced++;
      } else {
        await prisma.contentRegion.update({
          where: { id: region.id },
          data: { translatedText: newText },
        });
        enhanced++;
        if (enhanced % 50 === 0) {
          console.log(`Enhanced ${enhanced} regions (page ${page.pageNumber})...`);
        }
      }
    }
  }

  console.log(`\nDone! Enhanced: ${enhanced}, Skipped: ${skipped}, Unchanged: ${unchanged}`);
  console.log(`Total: ${enhanced + skipped + unchanged} regions`);

  await prisma.$disconnect();
}

main().catch(e => { console.error(e); process.exit(1); });
