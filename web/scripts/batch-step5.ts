/**
 * Batch re-run step 5 (text fitting with per-region translation) on all pages.
 * Processes 3 pages concurrently. Skips pages where all regions already have translations.
 * Usage: npx tsx scripts/batch-step5.ts [startPage]
 */
import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()
const BOOK_ID = 'jcqje5aut5wve5w5b8hv6fcq8'
const BATCH_SIZE = 3
const BASE_URL = 'http://localhost:3000'
const TIMEOUT_MS = 300_000

async function runPage(pageId: string, pageNumber: number): Promise<boolean> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  try {
    const res = await fetch(`${BASE_URL}/api/pages/${pageId}/pipeline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step: 5 }),
      signal: controller.signal,
    })
    clearTimeout(timer)
    if (!res.ok) {
      const body = await res.text()
      console.error(`  Page ${pageNumber} FAILED: HTTP ${res.status}: ${body.slice(0, 200)}`)
      return false
    }
    return true
  } catch (err: unknown) {
    clearTimeout(timer)
    const msg = err instanceof Error ? err.message : String(err)
    console.error(`  Page ${pageNumber} FAILED: ${msg}`)
    return false
  }
}

async function main() {
  const startPage = parseInt(process.argv[2] || '1', 10)

  const pages = await prisma.page.findMany({
    where: { bookId: BOOK_ID, pageNumber: { gte: startPage } },
    orderBy: { pageNumber: 'asc' },
    select: { id: true, pageNumber: true },
  })

  console.log(`Total pages from ${startPage}: ${pages.length}`)

  // Check how many regions still need translation
  const needTranslation = await prisma.contentRegion.count({
    where: {
      page: { bookId: BOOK_ID },
      translatedText: null,
      hebrewText: { not: null },
    },
  })
  console.log(`Regions still needing translation: ${needTranslation}`)
  console.log(`Processing ${BATCH_SIZE} pages at a time\n`)

  let done = 0
  let errors = 0
  let skipped = 0
  const startTime = Date.now()

  for (let i = 0; i < pages.length; i += BATCH_SIZE) {
    const batch = pages.slice(i, i + BATCH_SIZE)
    const results = await Promise.all(
      batch.map((p) => runPage(p.id, p.pageNumber))
    )

    for (const ok of results) {
      if (ok) done++
      else errors++
    }

    const lastPage = batch[batch.length - 1].pageNumber
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(0)
    const total = done + errors + skipped
    const pagesPerMin = total / ((Date.now() - startTime) / 60000)
    const remaining = pagesPerMin > 0 ? Math.round((pages.length - total) / pagesPerMin) : '?'
    console.log(
      `[${elapsed}s] ${total}/${pages.length} (${done} ok, ${errors} err, ${skipped} skip) — page ${lastPage} — ~${remaining}min left`
    )
  }

  console.log(`\nDone! ${done} succeeded, ${errors} failed, ${skipped} skipped out of ${pages.length}`)
  const totalMin = ((Date.now() - startTime) / 60000).toFixed(1)
  console.log(`Total time: ${totalMin} minutes`)
  await prisma.$disconnect()
}

main().catch((err) => {
  console.error('Fatal:', err)
  process.exit(1)
})
