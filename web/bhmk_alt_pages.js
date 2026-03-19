const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();
async function main() {
  const candidates = [180, 200, 300, 320, 45];
  for (const pn of candidates) {
    const page = await prisma.bhmk_Page.findFirst({
      where: { bookId: 'jcqje5aut5wve5w5b8hv6fcq8', pageNumber: pn },
      include: { ocrResult: { include: { boxes: true } } }
    });
    if (!page) { console.log('Page ' + pn + ': not found'); continue; }
    const boxes = page.ocrResult?.boxes || [];
    const lines = new Set(boxes.map(b => b.lineIndex)).size;
    const chars = boxes.reduce((s, b) => s + (b.text?.length || 0), 0);
    console.log('Page ' + pn + ' (' + page.id + '): ' + lines + ' lines, ' + chars + ' chars, ' + boxes.length + ' boxes');
  }
  await prisma.$disconnect();
}
main().catch(e => { console.error(e); process.exit(1); });
