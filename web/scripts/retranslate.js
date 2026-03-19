const { PrismaClient } = require('@prisma/client');
const Anthropic = require('@anthropic-ai/sdk');

const prisma = new PrismaClient();
const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const SYSTEM_PROMPT = `You are an expert translator of Hebrew Torah literature into Ashkenazi English. This book is about the Third Beis HaMikdash based on Yechezkel's prophecy (chapters 40-42).

CRITICAL: Use Ashkenazi transliterations and keep Hebrew terms where natural. NEVER anglicize these:
- Yechezkel (NOT Ezekiel), Yeshayahu (NOT Isaiah), Yirmiyahu (NOT Jeremiah), Shlomo (NOT Solomon), Moshe (NOT Moses), Dovid (NOT David)
- Perek (NOT chapter), Pasuk/Pesukim (NOT verse/verses), Parsha (NOT portion), Sefer (NOT book)
- Beis HaMikdash (NOT Temple), Mishkan (NOT Tabernacle), Mizbeiach (NOT altar), Menorah, Shulchan, Aron HaKodesh
- Shabbos (NOT Shabbat), Yom Tov (NOT holiday), davening (NOT praying), tefillah (NOT prayer)
- Hashem (NOT God), HaKadosh Baruch Hu, Ribbono Shel Olam
- Kohen/Kohanim (NOT priest/priests), Kohen Gadol (NOT High Priest), Leviim (NOT Levites)
- Gemara (NOT Talmud when referring to the text), Mishnah, Rashi, Tosafos, Rambam
- Amah/Amos (NOT cubit/cubits), Tefach/Tefachim (NOT handbreadth)
- Azarah (NOT courtyard), Heichal (NOT Sanctuary), Kodesh HaKodashim (NOT Holy of Holies)
- Korban/Korbanos (NOT sacrifice/sacrifices), Olah (NOT burnt offering), Shelamim (NOT peace offering)
- Har HaBayis (NOT Temple Mount), Eretz Yisroel (NOT Land of Israel)
- Chazal (NOT "the Sages"), Klal Yisroel (NOT "the Jewish people" — though "Jewish people" is ok as clarification)

Rules:
- Keep the scholarly tone of the original
- Preserve all source references in their original form (e.g., Yechezkel 40:5, Maseches Middos 2:1)
- When translating measurements, keep the Hebrew unit and add English equivalent in parentheses only if helpful
- Do not add explanatory notes unless absolutely necessary
- Use "the" before Hebrew terms when natural in English (e.g., "the Beis HaMikdash", "the Azarah")
Return ONLY the English translation, no commentary.`;

async function retranslate(pageId, pageNum) {
  const page = await prisma.page.findUnique({
    where: { id: pageId },
    include: { ocrResult: { include: { boxes: { orderBy: [{ lineIndex: 'asc' }, { wordIndex: 'asc' }] } } } }
  });

  if (!page.ocrResult) {
    console.log('  No OCR result, skipping');
    return;
  }

  const boxes = page.ocrResult.boxes.filter(b => !b.skipTranslation);
  const lineMap = new Map();
  for (const box of boxes) {
    const idx = box.lineIndex || 0;
    const text = box.editedText || box.hebrewText;
    if (!lineMap.has(idx)) lineMap.set(idx, []);
    lineMap.get(idx).push(text);
  }
  const sortedEntries = [];
  lineMap.forEach((val, key) => sortedEntries.push([key, val]));
  sortedEntries.sort((a, b) => a[0] - b[0]);
  const lines = sortedEntries.map(e => e[1].join(' '));
  const hebrewText = lines.join('\n');

  console.log('Translating page', pageNum, '(' + boxes.length + ' boxes)...');

  const response = await anthropic.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 4096,
    system: SYSTEM_PROMPT,
    messages: [{ role: 'user', content: 'Translate the following Hebrew text:\n\n' + hebrewText }]
  });

  const englishOutput = response.content.find(b => b.type === 'text').text;

  await prisma.translation.upsert({
    where: { pageId },
    create: { pageId, hebrewInput: hebrewText, englishOutput, status: 'draft' },
    update: { hebrewInput: hebrewText, englishOutput, status: 'draft' }
  });

  console.log('  Done. Preview:', englishOutput.substring(0, 120));
  console.log();
}

async function main() {
  const pages = await prisma.page.findMany({
    where: { status: 'translated' },
    orderBy: { pageNumber: 'asc' }
  });

  console.log('Re-translating', pages.length, 'pages with improved Ashkenazi prompt...\n');

  for (const p of pages) {
    await retranslate(p.id, p.pageNumber);
  }

  console.log('All done!');
  await prisma.$disconnect();
}

main().catch(e => { console.error(e); process.exit(1); });
