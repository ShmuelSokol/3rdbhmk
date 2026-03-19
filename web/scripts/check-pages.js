const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  const pages = await prisma.page.findMany({
    include: { translation: { select: { id: true } } },
    orderBy: { pageNumber: 'asc' },
  });
  for (const p of pages) {
    const hasTrans = p.translation ? 'YES' : 'no';
    console.log(`Page ${p.pageNumber} - status: ${p.status} - translation: ${hasTrans}`);
  }

  const books = await prisma.book.findMany();
  for (const b of books) {
    console.log(`\nBook: ${b.id} - "${b.name}" - ${b.totalPages} pages`);
  }

  await prisma.$disconnect();
}
main();
