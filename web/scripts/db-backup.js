#!/usr/bin/env node
/**
 * Export all 3rdBHMK tables to a timestamped JSON file with 30-day rotation.
 */
const { PrismaClient } = require("@prisma/client");
const fs = require("fs");
const path = require("path");

const TABLES = [
  "book",
  "page",
  "pageLayout",
  "oCRResult",
  "boundingBox",
  "translation",
  "flag",
  "contentRegion",
  "erasedImage",
  "fittedPage",
  "verificationOcr",
];

async function main() {
  const dirFlag = process.argv.indexOf("--dir");
  const outDir = dirFlag !== -1 ? process.argv[dirFlag + 1] : path.join(__dirname, "..", "backups");
  fs.mkdirSync(outDir, { recursive: true });

  const prisma = new PrismaClient();
  const snapshot = { takenAt: new Date().toISOString(), tables: {} };

  for (const t of TABLES) {
    try {
      const rows = await prisma[t].findMany();
      snapshot.tables[t] = { count: rows.length, rows };
      console.log(`  ${t}: ${rows.length} rows`);
    } catch (e) {
      snapshot.tables[t] = { error: e.message.slice(0, 200) };
      console.log(`  ${t}: ERROR (${e.message.slice(0, 80)})`);
    }
  }
  await prisma.$disconnect();

  const today = new Date().toISOString().slice(0, 10);
  const outPath = path.join(outDir, `db-${today}.json`);
  fs.writeFileSync(outPath, JSON.stringify(snapshot, null, 2));
  console.log(`\nWrote ${outPath}`);

  const files = fs.readdirSync(outDir).filter((n) => /^db-\d{4}-\d{2}-\d{2}\.json$/.test(n)).sort();
  const KEEP = 30;
  if (files.length > KEEP) {
    for (const f of files.slice(0, files.length - KEEP)) {
      fs.unlinkSync(path.join(outDir, f));
      console.log(`Pruned old backup: ${f}`);
    }
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
