const { PrismaClient } = require('@prisma/client');
const { PDFDocument, StandardFonts, rgb } = require('pdf-lib');
const prisma = new PrismaClient();

async function main() {
  const book = await prisma.book.findUnique({
    where: { id: '5qje5lvpqtuu1th3cnnbd73gz' },
    include: {
      pages: { include: { translation: true }, orderBy: { pageNumber: 'asc' } },
    },
  });

  const translated = book.pages.filter(
    (p) => p.translation && p.translation.englishOutput
  );
  console.log('Book:', book.name, '- Translated pages:', translated.length);

  const pdfDoc = await PDFDocument.create();
  const font = await pdfDoc.embedFont(StandardFonts.TimesRoman);
  const boldFont = await pdfDoc.embedFont(StandardFonts.TimesRomanBold);

  for (const page of translated) {
    const text = page.translation.englishOutput;
    // Check for problematic chars
    const nonAscii = [];
    for (let i = 0; i < text.length; i++) {
      const code = text.charCodeAt(i);
      if (code > 127) {
        nonAscii.push({
          pos: i,
          char: text[i],
          code,
          context: text.substring(Math.max(0, i - 5), i + 5),
        });
      }
    }
    if (nonAscii.length > 0) {
      console.log(
        `Page ${page.pageNumber} has ${nonAscii.length} non-ASCII chars:`
      );
      nonAscii.slice(0, 5).forEach((c) => console.log('  ', c));
    }

    try {
      const testPage = pdfDoc.addPage([612, 792]);
      // Try drawing all lines
      const lines = text.split('\n');
      let y = 700;
      for (const line of lines) {
        const clean = line.trim();
        if (!clean) {
          y -= 10;
          continue;
        }
        try {
          testPage.drawText(clean, { x: 72, y, size: 12, font });
        } catch (e) {
          console.log(
            `Page ${page.pageNumber} line error: "${clean.substring(0, 50)}" -> ${e.message.substring(0, 100)}`
          );
        }
        y -= 18;
      }
      console.log(`Page ${page.pageNumber} - OK`);
    } catch (e) {
      console.log(
        `Page ${page.pageNumber} - ERROR: ${e.message.substring(0, 200)}`
      );
    }
  }

  await prisma.$disconnect();
}
main().catch((e) => {
  console.error(e);
  process.exit(1);
});
