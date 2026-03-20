#!/usr/bin/env node
/**
 * Audit inline Hebrew-English translation pairings.
 * Finds cases where Hebrew quotes are paired with unrelated English translations.
 */
const { PrismaClient } = require('@prisma/client');
const fs = require('fs');
const path = require('path');

const envPath = path.join(__dirname, '..', '.env.local');
if (fs.existsSync(envPath)) {
  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    if (line.trim() && !line.startsWith('#') && line.includes('=')) {
      const [key, ...vals] = line.split('=');
      process.env[key.trim()] = vals.join('=').trim();
    }
  }
}

const prisma = new PrismaClient();

// Hebrew keyword → expected English keyword mappings
const HEBREW_ENGLISH_MAP = {
  'משכן': ['mishkan', 'tabernacle', 'dwelling'],
  'מקדש': ['mikdash', 'temple', 'sanctuary'],
  'כהן': ['kohen', 'priest', 'kohanim'],
  'מזבח': ['mizbei', 'altar'],
  'ארון': ['aron', 'ark'],
  'היכל': ['heichal', 'sanctuary', 'temple hall'],
  'חומה': ['wall', 'chomah'],
  'שער': ['gate', 'sha\'ar'],
  'לשכה': ['chamber', 'lishkah', 'leshakah', 'lishkas'],
  'אמה': ['amah', 'amos', 'cubit'],
  'חצר': ['courtyard', 'azarah', 'chatzer'],
  'עזרה': ['azarah', 'courtyard'],
  'קרבן': ['korban', 'offering', 'sacrifice'],
  'כרוב': ['keruv', 'cheruv', 'keruvim'],
  'מנורה': ['menorah', 'candelabr'],
  'שלחן': ['shulchan', 'table'],
  'פרכת': ['paroches', 'curtain', 'partition'],
  'סורג': ['soreg', 'lattice'],
  'חיל': ['cheil'],
  'תא': ['cell', 'chamber', 'ta\''],
  'אולם': ['ulam', 'vestibule', 'hall'],
  'דביר': ['devir', 'kodesh', 'holy of holies'],
  'טפח': ['tefach', 'handbreath'],
  'קנה': ['kaneh', 'reed', 'measuring'],
  'חורבן': ['destruction', 'churban'],
  'בית': ['beis', 'house', 'bayis'],
  'ירושלים': ['yerushalayim', 'jerusalem'],
  'ציון': ['tzion', 'zion'],
  'שכינה': ['shechinah', 'divine presence'],
  'נבואה': ['prophecy', 'nevuah'],
  'יחזקאל': ['yechezkel', 'ezekiel'],
};

// Words that indicate the English is about a completely different topic
const UNRELATED_ENGLISH = [
  'my head is filled with dew',
  'i don\'t see',
  'i apologize',
  'could you please',
  'i cannot',
];

async function audit() {
  const regions = await prisma.contentRegion.findMany({
    where: { page: { bookId: 'jcqje5aut5wve5w5b8hv6fcq8' } },
    select: { id: true, translatedText: true, hebrewText: true, regionType: true, page: { select: { pageNumber: true } } },
    orderBy: [{ page: { pageNumber: 'asc' } }, { regionIndex: 'asc' }]
  });

  const issues = [];

  for (const r of regions) {
    const t = (r.translatedText || '').trim();
    if (!t || t.length < 30) continue;

    // Find inline Hebrew-English pairs: Hebrew text — English text
    // Pattern: Hebrew chars followed by em-dash/hyphen then English
    const pairs = [];
    const pairRegex = /([\u0590-\u05FF][\u0590-\u05FF\s\u05F3\u05F4'".,;:\d\[\]\(\)]{2,80})\s*[\u2014\u2013\-]+\s*([A-Z"][^"\u0590-\u05FF]{5,100})/g;
    let match;
    while ((match = pairRegex.exec(t)) !== null) {
      pairs.push({ hebrew: match[1].trim(), english: match[2].trim() });
    }

    for (const pair of pairs) {
      const heb = pair.hebrew;
      const eng = pair.english.toLowerCase();

      // Check for obviously unrelated English
      for (const unrelated of UNRELATED_ENGLISH) {
        if (eng.includes(unrelated)) {
          issues.push({
            page: r.page.pageNumber,
            type: 'unrelated',
            hebrew: heb,
            english: pair.english.substring(0, 80),
            reason: 'English contains unrelated/meta text'
          });
        }
      }

      // Check Hebrew keywords against English
      for (const [hebWord, engWords] of Object.entries(HEBREW_ENGLISH_MAP)) {
        if (heb.includes(hebWord)) {
          const hasMatch = engWords.some(ew => eng.includes(ew.toLowerCase()));
          if (!hasMatch && eng.length > 20) {
            // Hebrew has a keyword but English doesn't mention it at all
            // Only flag if the English seems completely unrelated
            const hebKeyCount = Object.entries(HEBREW_ENGLISH_MAP)
              .filter(([hw]) => heb.includes(hw)).length;
            const engKeyCount = Object.entries(HEBREW_ENGLISH_MAP)
              .filter(([, ews]) => ews.some(ew => eng.includes(ew.toLowerCase()))).length;

            // Only flag if Hebrew has keywords but English has NONE of the expected translations
            if (hebKeyCount >= 2 && engKeyCount === 0) {
              issues.push({
                page: r.page.pageNumber,
                type: 'keyword_mismatch',
                hebrew: heb.substring(0, 60),
                english: pair.english.substring(0, 80),
                reason: `Hebrew contains ${hebKeyCount} recognizable terms but English has none of their translations`
              });
              break; // One issue per pair
            }
          }
        }
      }
    }

    // Also check: English text that quotes Hebrew but the quote seems wrong
    // Pattern: Hebrew in the middle of English that doesn't relate to surrounding context
    const midHebrew = t.match(/[a-zA-Z]{10,}\s+[\u0590-\u05FF]{3,30}\s+[a-zA-Z]{3,}/g);
    if (midHebrew) {
      for (const mh of midHebrew) {
        const hebPart = mh.match(/[\u0590-\u05FF]+/)?.[0] || '';
        const engPart = mh.replace(/[\u0590-\u05FF]+/g, '').toLowerCase();
        // Check if the Hebrew word relates to the English context
        let related = false;
        for (const [hw, ews] of Object.entries(HEBREW_ENGLISH_MAP)) {
          if (hebPart.includes(hw) && ews.some(ew => engPart.includes(ew.toLowerCase()))) {
            related = true;
            break;
          }
        }
        // Don't flag — too many false positives with mid-text Hebrew
      }
    }
  }

  // Deduplicate
  const seen = new Set();
  const deduped = issues.filter(i => {
    const key = `${i.page}:${i.hebrew.substring(0, 20)}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  console.log('=== TRANSLATION MISMATCH AUDIT ===\n');
  console.log('Total issues found:', deduped.length);

  if (deduped.length === 0) {
    console.log('No obvious mismatches found!');
  }

  for (const i of deduped) {
    console.log('\n---');
    console.log(`PAGE: ${i.page} | TYPE: ${i.type}`);
    console.log(`HEBREW: ${i.hebrew}`);
    console.log(`ENGLISH: ${i.english}`);
    console.log(`REASON: ${i.reason}`);
  }

  await prisma.$disconnect();
}

audit().catch(console.error);
