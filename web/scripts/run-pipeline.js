#!/usr/bin/env node
/**
 * Run the full pipeline on all pages of the content book.
 * Usage: node scripts/run-pipeline.js
 *
 * Processes pages sequentially against the local dev server.
 * For pages with existing OCR boxes, enriches without re-running Azure.
 * For pages without translation, runs steps 1-4 only.
 */

const BASE = process.env.BASE_URL || 'http://localhost:3000'
const BOOK_ID = '5qje5lvpqtuu1th3cnnbd73gz' // Lishchno Tidreshu (Content)

async function main() {
  console.log(`Fetching book pipeline status from ${BASE}...`)
  const bookRes = await fetch(`${BASE}/api/books/${BOOK_ID}/pipeline`)
  const book = await bookRes.json()
  if (book.error) { console.error('Error:', book.error); process.exit(1) }

  console.log(`Book: ${book.name} | ${book.totalPages} pages`)
  console.log(`Current statuses:`, JSON.stringify(book.stepCounts))
  console.log()

  for (const page of book.pages) {
    console.log(`--- Page ${page.pageNumber} (current: ${page.pipelineStatus}) ---`)

    if (page.pipelineStatus === 'locked') {
      console.log('  Skipped (locked)')
      continue
    }

    // Run step by step to get progress output
    const steps = [1, 2, 3, 4, 5, 6]
    for (const step of steps) {
      const t0 = Date.now()
      console.log(`  Step ${step}...`)
      try {
        const res = await fetch(`${BASE}/api/pages/${page.id}/pipeline`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ step }),
        })
        const data = await res.json()
        const elapsed = ((Date.now() - t0) / 1000).toFixed(1)

        if (!res.ok) {
          console.log(`  Step ${step} FAILED (${elapsed}s): ${data.error}`)
          break // Stop this page, continue to next
        }
        console.log(`  Step ${step} OK (${elapsed}s)`)
      } catch (err) {
        console.log(`  Step ${step} ERROR: ${err.message}`)
        break
      }
    }
    console.log()
  }

  // Final status
  const finalRes = await fetch(`${BASE}/api/books/${BOOK_ID}/pipeline`)
  const final = await finalRes.json()
  console.log('=== Final Status ===')
  console.log(JSON.stringify(final.stepCounts, null, 2))
}

main().catch(e => { console.error(e); process.exit(1) })
