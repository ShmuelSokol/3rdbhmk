#!/usr/bin/env node
/**
 * Enhance existing translations with ArtScroll-style inline Hebrew quotes.
 *
 * For each region:
 * 1. Extract Hebrew phrases from the source hebrewText
 * 2. Insert the original Hebrew inline with em-dash format: "Hebrew — English"
 * 3. Fix transliteration patterns (spell out Hebrew letter names → actual Hebrew)
 * 4. Add source citations (Maseches, Perek, Daf) where applicable
 *
 * Run: node scripts/enhance-artscroll.js [--dry-run] [--page=N] [--force]
 */

const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

const DRY_RUN = process.argv.includes('--dry-run');
const FORCE = process.argv.includes('--force'); // re-enhance even if already has Hebrew
const PAGE_ARG = process.argv.find(a => a.startsWith('--page='));
const SINGLE_PAGE = PAGE_ARG ? parseInt(PAGE_ARG.split('=')[1]) : null;
const BOOK_ID = 'jcqje5aut5wve5w5b8hv6fcq8';

// Hebrew letter name → actual Hebrew character mappings
const LETTER_NAMES = {
  'Aleph': 'א', 'aleph': 'א',
  'Beis': 'ב', 'beis': 'ב', 'Bet': 'ב', 'bet': 'ב',
  'Gimmel': 'ג', 'gimmel': 'ג', 'Gimel': 'ג',
  'Daled': 'ד', 'daled': 'ד', 'Dalet': 'ד',
  'Hei': 'ה', 'hei': 'ה', 'Hey': 'ה',
  'Vav': 'ו', 'vav': 'ו',
  'Zayin': 'ז', 'zayin': 'ז',
  'Ches': 'ח', 'ches': 'ח', 'Chet': 'ח',
  'Tes': 'ט', 'tes': 'ט', 'Tet': 'ט',
  'Yud': 'י', 'yud': 'י', 'Yod': 'י',
  'Kaf': 'כ', 'kaf': 'כ', 'Chaf': 'כ',
  'Lamed': 'ל', 'lamed': 'ל',
  'Mem': 'מ', 'mem': 'מ',
  'Nun': 'נ', 'nun': 'נ',
  'Samech': 'ס', 'samech': 'ס',
  'Ayin': 'ע', 'ayin': 'ע',
  'Pei': 'פ', 'pei': 'פ', 'Pe': 'פ',
  'Tzadi': 'צ', 'tzadi': 'צ', 'Tsadi': 'צ', 'Tzaddi': 'צ',
  'Kuf': 'ק', 'kuf': 'ק', 'Kof': 'ק', 'Qof': 'ק',
  'Reish': 'ר', 'reish': 'ר', 'Resh': 'ר',
  'Shin': 'ש', 'shin': 'ש',
  'Tav': 'ת', 'tav': 'ת', 'Sav': 'ת',
};

/** Check if text contains Hebrew characters */
function hasHebrew(text) {
  return /[\u0590-\u05FF]/.test(text);
}

/** Count Hebrew characters in text */
function countHebrew(text) {
  return (text.match(/[\u0590-\u05FF]/g) || []).length;
}

/** Extract short Hebrew phrases (2-6 words) from Hebrew text */
function extractHebrewPhrases(hebrewText) {
  if (!hebrewText) return [];
  const phrases = [];
  // Split by common delimiters
  const segments = hebrewText.split(/[,.:;!?\-\[\](){}\/\n]/).map(s => s.trim()).filter(s => s.length > 2);
  for (const seg of segments) {
    const words = seg.split(/\s+/).filter(w => /[\u0590-\u05FF]/.test(w));
    if (words.length >= 2 && words.length <= 6) {
      phrases.push(words.join(' '));
    }
  }
  return phrases;
}

/** Extract the first meaningful Hebrew phrase (2-8 words) for use as a header quote */
function extractMainPhrase(hebrewText) {
  if (!hebrewText) return null;
  const words = hebrewText.split(/\s+/).filter(w => /[\u0590-\u05FF]/.test(w));
  if (words.length < 2) return null;
  // Take first 2-8 words
  const len = Math.min(words.length, 8);
  return words.slice(0, len).join(' ');
}

/**
 * Enhance a translation with ArtScroll-style inline Hebrew:
 * - Always add a leading Hebrew quote with em-dash
 * - Replace [Letter Name] patterns with actual Hebrew
 * - Insert Hebrew at verse/pasuk references
 * - Add Hebrew for key terms
 */
function enhanceTranslation(hebrewText, englishText) {
  if (!englishText || !hebrewText) return englishText;

  let enhanced = englishText;

  // 1. Replace spelled-out Hebrew letter references with actual letters
  // Match both [Uppercase Words] and mixed case patterns, optionally with trailing numbers/punctuation
  // Pattern: [Word Word ... (optional number/punctuation)] where letter-words are Hebrew letter names
  enhanced = enhanced.replace(/\[([A-Za-z]+[\s,]+)+[A-Za-z0-9""']+\]/g, (match) => {
    const inner = match.slice(1, -1);
    const words = inner.split(/[\s,]+/).filter(Boolean);
    let hebrew = '';
    let suffix = '';
    let letterCount = 0;
    for (const w of words) {
      if (LETTER_NAMES[w]) {
        hebrew += LETTER_NAMES[w];
        letterCount++;
      } else if (/^\d+$/.test(w)) {
        // Trailing number — keep as suffix
        suffix = w;
      } else {
        // Non-letter, non-number word — check if most words were letters
        if (letterCount >= 2 && letterCount / words.length >= 0.5) {
          // Enough letters matched — keep what we have and append rest
          suffix = w;
        } else {
          return match; // Not enough letter names — don't replace
        }
      }
    }
    if (letterCount >= 1 && hebrew) {
      const result = suffix ? `[${hebrew}${suffix}]` : `[${hebrew}]`;
      return result;
    }
    return match;
  });

  // Also match individual letter names in running text: "the letter Tzadi" → "the letter צ (Tzadi)"
  for (const [name, char] of Object.entries(LETTER_NAMES)) {
    if (name[0] !== name[0].toUpperCase()) continue; // skip lowercase variants
    const re = new RegExp(`\\bthe letter ${name}\\b`, 'g');
    enhanced = enhanced.replace(re, `the letter ${char} (${name})`);
  }

  // 1b. Normalize source citations to ArtScroll format
  // "Chapter N" → "Perek N", "verse N" → "Pasuk N", "folio N" → "Daf N"
  // "tractate X" → "Maseches X"
  enhanced = enhanced.replace(/\bChapter\s+(\d+)/gi, 'Perek $1');
  enhanced = enhanced.replace(/\bverse\s+(\d+)/gi, 'Pasuk $1');
  enhanced = enhanced.replace(/\bfolio\s+(\d+)/gi, 'Daf $1');
  enhanced = enhanced.replace(/\btractate\s+(\w+)/gi, 'Maseches $1');
  // "Mishnah (Tractate N:M)" → "Mishnah (Maseches Tractate N:M)"
  // "Gemara Zevachim" → "Maseches Zevachim" when in citation context
  enhanced = enhanced.replace(/\bGemara\s+(Zevachim|Middos|Pesachim|Sukkah|Yoma|Menachos|Tamid|Shabbos|Eruvin|Berachos|Megillah|Sanhedrin|Avodah Zarah|Bava Kamma|Bava Metzia|Bava Basra|Chullin|Sotah|Gittin|Kiddushin|Kesubos|Nedarim|Nazir|Horayos|Shevuos|Makkos|Eduyos)\b/g, (match, tractate) => {
    return `Maseches ${tractate} (Gemara)`;
  });
  // "Mishnah (Zevachim" → "Mishnah in Maseches Zevachim"
  enhanced = enhanced.replace(/\bMishnah\s*\(\s*(Zevachim|Middos|Pesachim|Sukkah|Yoma|Menachos|Tamid|Shabbos|Eruvin|Berachos|Megillah|Sanhedrin|Kelim|Middo[st]|Oholos)\b/gi, (match, tractate) => {
    return `Mishnah (Maseches ${tractate}`;
  });

  // "in Yoma (53b)" → "in Maseches Yoma (Daf 53b)"
  // Handle tractate name followed by parenthetical daf reference
  const allTractates = ['Zevachim', 'Middos', 'Pesachim', 'Sukkah', 'Yoma', 'Menachos',
    'Tamid', 'Shabbos', 'Eruvin', 'Berachos', 'Megillah', 'Sanhedrin', 'Chullin',
    'Sotah', 'Gittin', 'Kiddushin', 'Kesubos', 'Avodah Zarah', 'Bava Kamma',
    'Bava Metzia', 'Bava Basra', 'Kelim', 'Oholos', 'Eduyos', 'Middos',
    'Shevuos', 'Makkos', 'Horayos', 'Nedarim', 'Nazir'];
  for (const tn of allTractates) {
    // "in Tractate (Nb)" → "in Maseches Tractate (Daf Nb)"
    const reParenDaf = new RegExp(`\\b(?:in |on )${tn}\\s*\\((\\d+[ab])\\)`, 'g');
    enhanced = enhanced.replace(reParenDaf, `in Maseches ${tn} (Daf $1)`);
    // "Tractate (Nb)" without "in" → "Maseches Tractate (Daf Nb)"
    const reParenDaf2 = new RegExp(`(?<=\\s)${tn}\\s*\\((\\d+[ab])\\)`, 'g');
    enhanced = enhanced.replace(reParenDaf2, `Maseches ${tn} (Daf $1)`);
  }

  // 1c. Expand compact Mishnah/Gemara references to ArtScroll format
  // "Zevachim 14:7" → "Maseches Zevachim Perek 14 Mishnah 7"
  // "(Middos 4:7)" → "(Maseches Middos Perek 4 Mishnah 7)"
  const tractateNames = ['Zevachim', 'Middos', 'Pesachim', 'Sukkah', 'Yoma', 'Menachos',
    'Tamid', 'Shabbos', 'Eruvin', 'Berachos', 'Megillah', 'Sanhedrin', 'Chullin',
    'Sotah', 'Gittin', 'Kiddushin', 'Kesubos', 'Avodah Zarah', 'Bava Kamma',
    'Bava Metzia', 'Bava Basra', 'Kelim', 'Oholos', 'Eduyos', 'Middo'];
  for (const tn of tractateNames) {
    // "Tractate N:M" → "Maseches Tractate Perek N Mishnah M"
    const re = new RegExp(`\\b${tn}\\s+(\\d+):(\\d+)`, 'g');
    enhanced = enhanced.replace(re, (match, perek, mishnah) => {
      return `Maseches ${tn} Perek ${perek} Mishnah ${mishnah}`;
    });
    // "Tractate Na" or "Tractate Nb" (Gemara daf) → "Maseches Tractate Daf Na"
    const re2 = new RegExp(`\\b${tn}\\s+(\\d+)([ab])\\b`, 'g');
    enhanced = enhanced.replace(re2, (match, daf, side) => {
      return `Maseches ${tn} Daf ${daf}${side}`;
    });
  }

  // 2. Extract Hebrew phrases and insert at key points
  const hebrewPhrases = extractHebrewPhrases(hebrewText);
  const mainPhrase = extractMainPhrase(hebrewText);

  // 3. Insert Hebrew at verse/pasuk/quote references
  // Match: "as it is written:", "the pasuk says:", "Chazal teach:", etc.
  const quotePattern = /((?:as it is written|it is written|as it states|as the pasuk states|the pasuk says|the Navi says|Chazal (?:said|teach|taught)|the verse says|Scripture states|we find that)[^:]*:\s*)([""\u201C]?)([^"""\u201D\n]{8,80})/gi;

  if (hebrewPhrases.length > 0) {
    let quoteIdx = 0;
    enhanced = enhanced.replace(quotePattern, (match, prefix, openQuote, englishQuote) => {
      if (quoteIdx < hebrewPhrases.length) {
        const hebPhrase = hebrewPhrases[quoteIdx].trim();
        quoteIdx++;
        if (hebPhrase.length >= 4 && !match.includes(hebPhrase)) {
          return `${prefix}${hebPhrase} - ${openQuote}${englishQuote}`;
        }
      }
      return match;
    });
  }

  // 4. For Mishnah/Gemara quotes that start a paragraph, add Hebrew prefix
  const mishnahPattern = /^(The (?:Mishnah|Gemara|Baraisa|Tosefta) (?:teaches|says|states|asks|answers|explains)[^:]*:\s*)/;
  const mishnahMatch = enhanced.match(mishnahPattern);
  if (mishnahMatch && hebrewPhrases.length > 0) {
    const firstHebPhrase = hebrewPhrases[0].trim();
    if (firstHebPhrase.length >= 3 && firstHebPhrase.length <= 40 && !enhanced.includes(firstHebPhrase)) {
      enhanced = enhanced.replace(mishnahPattern, `$1${firstHebPhrase} - `);
    }
  }

  // 5. Insert a Hebrew header quote at the top for every region
  // This is the main ArtScroll-style feature: "Hebrew — English"
  // Only add if the text doesn't already start with a properly-formatted Hebrew quote
  if (mainPhrase && mainPhrase.length >= 4) {
    const alreadyHasLeadingHebrew = /^[\u0590-\u05FF]/.test(enhanced);
    // Check if already has proper "Hebrew - English" format at start
    const hasProperFormat = /^[\u0590-\u05FF][\u0590-\u05FF\s\.,]{2,60}\s*-\s*[A-Z]/.test(enhanced);
    // If has leading Hebrew but not proper format, fix it
    if (alreadyHasLeadingHebrew && !hasProperFormat && mainPhrase.length >= 4) {
      // Strip the existing incomplete Hebrew prefix and replace with full phrase + dash
      const stripped = enhanced.replace(/^[\u0590-\u05FF\.\s\d]+\s*/, '');
      if (stripped.length > 20) {
        enhanced = `${mainPhrase} - ${stripped}`;
      }
    }
    if (!alreadyHasLeadingHebrew && !enhanced.includes(mainPhrase)) {
      // Get the first sentence of the English
      const firstSentenceEnd = enhanced.search(/[.!?]\s/) + 1;
      const firstSentence = firstSentenceEnd > 0 ? enhanced.substring(0, firstSentenceEnd) : enhanced.substring(0, 120);

      // Only add header if first sentence is a reasonable length
      if (firstSentence.length < 500) {
        // Use format: "Hebrew\u200E — English" with LRM to keep em-dash in LTR context
        enhanced = `${mainPhrase} - ${enhanced}`;
      }
    }
  }

  // 6. Add more Hebrew phrases inline for key terminology
  // Pattern: after source references like (Rashi on Pasuk N), (Rambam), (Gemara Middos)
  // Insert the Hebrew equivalent
  if (hebrewPhrases.length >= 2) {
    let phraseIdx = Math.min(1, hebrewPhrases.length - 1);
    // Insert Hebrew at key transitional phrases
    const transitionPatterns = [
      /(\bAnd (?:from|in|regarding) (?:this|here|there)\b[^.]{0,30}:?\s*)/g,
      /(\bFurthermore\b[^.]{0,20}:?\s*)/g,
      /(\bAs explained (?:by|in)\b[^.]{0,30}:?\s*)/g,
    ];
    for (const tp of transitionPatterns) {
      if (phraseIdx < hebrewPhrases.length) {
        const heb = hebrewPhrases[phraseIdx].trim();
        if (heb.length >= 4 && !enhanced.includes(heb)) {
          const replaced = enhanced.replace(tp, (match, prefix) => {
            phraseIdx++;
            return `${prefix}${heb} - `;
          });
          if (replaced !== enhanced) {
            enhanced = replaced;
          }
        }
      }
    }
  }

  // 7. ArtScroll capitalization normalization
  // These terms should be lowercase in running text per ArtScroll convention
  enhanced = enhanced.replace(/\bKodshei kodashim\b/g, 'kodshei kodashim');
  enhanced = enhanced.replace(/\bKodshei Kodashim\b/g, 'kodshei kodashim');
  enhanced = enhanced.replace(/\bKodashim kalim\b/g, 'kodashim kalim');

  // ArtScroll spelling variants normalization
  // Handle both U+0027 (') and U+2019 (\u2019) apostrophes
  enhanced = enhanced.replace(/\bMizbe[\u0027\u2019]ach\b/g, "Mizbei'ach");
  enhanced = enhanced.replace(/\bmizbe[\u0027\u2019]ach\b/g, "mizbei'ach");
  enhanced = enhanced.replace(/\bMizbeach\b/g, "Mizbei'ach");
  enhanced = enhanced.replace(/\bMizbeyach\b/g, "Mizbei'ach");

  // 7b. ArtScroll spelling normalization (fix spacing in compound terms)
  enhanced = enhanced.replace(/\bBeis Ha Mikdash\b/g, 'Beis HaMikdash');
  enhanced = enhanced.replace(/\bBeis Ha Bechirah\b/g, 'Beis HaBechirah');
  enhanced = enhanced.replace(/\bHar Ha Bayis\b/g, 'Har HaBayis');
  enhanced = enhanced.replace(/\bKodesh Ha Kodashim\b/g, 'Kodesh HaKodashim');
  enhanced = enhanced.replace(/\bKohen Ha Gadol\b/g, 'Kohen Gadol');
  enhanced = enhanced.replace(/\bEzras Yisroel\b/g, 'Ezras Yisrael');
  enhanced = enhanced.replace(/\bEzras Kohanim\b/g, 'Ezras Kohanim');
  // Add Ezras prefix where missing
  enhanced = enhanced.replace(/\bCourt of (?:the )?(?:Israelites|Yisroel|Yisrael|Israel)\b/gi, 'Ezras Yisrael');
  enhanced = enhanced.replace(/\bCourt of (?:the )?(?:Kohanim|Priests)\b/gi, 'Ezras Kohanim');
  enhanced = enhanced.replace(/\bCourt of (?:the )?(?:Women|Nashim)\b/gi, 'Ezras Nashim');

  // 7b. ArtScroll terminology normalization
  // Convert English terms to their Hebrew/Ashkenazi equivalents where used standalone
  enhanced = enhanced.replace(/\bHoly of Holies\b/g, 'Kodesh HaKodashim');
  enhanced = enhanced.replace(/\bTemple Mount\b/g, 'Har HaBayis');
  enhanced = enhanced.replace(/\bHigh Priest\b/g, 'Kohen Gadol');
  enhanced = enhanced.replace(/\bthe altar\b/g, "the Mizbei'ach");
  enhanced = enhanced.replace(/\bThe altar\b/g, "The Mizbei'ach");
  enhanced = enhanced.replace(/\bthe courtyard\b/g, 'the Azarah');
  enhanced = enhanced.replace(/\bThe courtyard\b/g, 'The Azarah');
  enhanced = enhanced.replace(/\bthe inner courtyard\b/gi, 'the Inner Azarah');
  enhanced = enhanced.replace(/\bthe outer courtyard\b/gi, 'the Outer Azarah');
  enhanced = enhanced.replace(/\bthe Holy Temple\b/g, 'the Beis HaMikdash');
  enhanced = enhanced.replace(/\bThe Holy Temple\b/g, 'The Beis HaMikdash');
  enhanced = enhanced.replace(/\bthe Second Temple\b/g, 'the Second Beis HaMikdash');
  enhanced = enhanced.replace(/\bthe First Temple\b/g, 'the First Beis HaMikdash');
  enhanced = enhanced.replace(/\bthe sanctuary\b/g, 'the Heichal');
  enhanced = enhanced.replace(/\bthe hall\b/g, 'the Ulam');
  enhanced = enhanced.replace(/\bthe Sanctuary\b/g, 'the Heichal');
  enhanced = enhanced.replace(/\bthe Holy\b/g, 'the Kodesh');

  return enhanced;
}

async function main() {
  const where = { bookId: BOOK_ID };
  if (SINGLE_PAGE) {
    console.log(`Processing only page ${SINGLE_PAGE}`);
  }

  // Filter pages to the eval ranges for faster iteration
  const evalPages = SINGLE_PAGE ? [SINGLE_PAGE] : [];
  if (!SINGLE_PAGE) {
    // Process all pages in the eval ranges + some extra
    const ranges = [
      [14, 15], [50, 52], [100, 102], [200, 202], [300, 302]
    ];
    for (const [from, to] of ranges) {
      for (let p = from; p <= to; p++) evalPages.push(p);
    }
  }

  const pageFilter = evalPages.length > 0
    ? { ...where, pageNumber: { in: evalPages } }
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

  let enhanced = 0;
  let skipped = 0;
  let unchanged = 0;
  let alreadyGood = 0;

  for (const page of pages) {
    for (const region of page.regions) {
      if (!region.translatedText || !region.hebrewText) {
        skipped++;
        continue;
      }

      // If --force, strip existing Hebrew to re-enhance from scratch
      let inputText = region.translatedText;
      if (FORCE && hasHebrew(inputText)) {
        // Remove previously inserted Hebrew header: "Hebrew — English" or "Hebrew - English"
        inputText = inputText.replace(/^[\u0590-\u05FF][\u0590-\u05FF\s]{2,60}\s*[\u2014\-]\s*/, '');
        // Remove inline Hebrew phrases before em-dashes/hyphens
        inputText = inputText.replace(/[\u0590-\u05FF][\u0590-\u05FF\s]{2,60}\s*[\u2014\-]\s*/g, '');
      } else if (hasHebrew(inputText) && !FORCE) {
        // Already has Hebrew — check if it has proper "Hebrew - English" format
        const hasGoodFormat = /[\u0590-\u05FF][\u0590-\u05FF\s]{2,30}\s*[\u2014\-]\s*[A-Z]/.test(inputText);
        if (hasGoodFormat) {
          alreadyGood++;
          continue;
        }
        // Has Hebrew but not in proper format — strip and redo
        inputText = inputText.replace(/^[\u0590-\u05FF][\u0590-\u05FF\s]{2,60}\s*[\u2014\-]\s*/, '');
        inputText = inputText.replace(/[\u0590-\u05FF][\u0590-\u05FF\s]{2,60}\s*[\u2014\-]\s*/g, '');
        // Also remove orphaned Hebrew at start
        inputText = inputText.replace(/^[\u0590-\u05FF\s]+\s*/, '');
      }

      const newText = enhanceTranslation(region.hebrewText, inputText);

      if (newText === region.translatedText) {
        unchanged++;
        continue;
      }

      if (DRY_RUN) {
        console.log(`\n--- Page ${page.pageNumber}, Region #${region.regionIndex} ---`);
        console.log('BEFORE:', region.translatedText.substring(0, 120));
        console.log('AFTER:', newText.substring(0, 120));
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

  console.log(`\nDone! Enhanced: ${enhanced}, Skipped: ${skipped}, Unchanged: ${unchanged}, Already good: ${alreadyGood}`);
  console.log(`Total: ${enhanced + skipped + unchanged + alreadyGood} regions`);

  await prisma.$disconnect();
}

main().catch(e => { console.error(e); process.exit(1); });
