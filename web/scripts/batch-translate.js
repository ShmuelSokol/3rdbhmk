#!/usr/bin/env node
/**
 * Batch translate all pages of a book, then run pipeline steps 5-6.
 * Uses the existing /api/pages/[pageId]/translate endpoint (Ashkenazi style).
 * Skips pages that already have translations.
 *
 * Usage: node scripts/batch-translate.js [bookId]
 */

const BASE = process.env.BASE_URL || 'http://localhost:3000'
const BOOK_ID = process.argv[2] || 'jcqje5aut5wve5w5b8hv6fcq8'

async function main() {
  console.log(`Batch translate | Book: ${BOOK_ID} | Server: ${BASE}`)

  // Get all pages
  const bookRes = await fetch(`${BASE}/api/books/${BOOK_ID}/pipeline`)
  const book = await bookRes.json()
  if (book.error) { console.error('Error:', book.error); process.exit(1) }
  console.log(`Book: ${book.name} | ${book.totalPages} pages\n`)

  let translated = 0
  let skipped = 0
  let failed = 0
  const startTime = Date.now()

  for (const page of book.pages) {
    // Check if translation already exists
    const checkRes = await fetch(`${BASE}/api/pages/${page.id}/translate`)
    if (checkRes.ok) {
      const existing = await checkRes.json()
      if (existing && existing.id) {
        skipped++
        continue
      }
    }

    // Check if page has OCR (needed for translation)
    const pageRes = await fetch(`${BASE}/api/pages/${page.id}/pipeline`)
    const pageData = await pageRes.json()
    if (pageData.ocrBoxCount === 0) {
      process.stdout.write(`Page ${page.pageNumber}: no OCR, skipping\n`)
      skipped++
      continue
    }

    // Translate
    process.stdout.write(`Page ${page.pageNumber}/${book.totalPages} translate... `)
    const t0 = Date.now()
    try {
      const res = await fetch(`${BASE}/api/pages/${page.id}/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      const data = await res.json()
      const elapsed = ((Date.now() - t0) / 1000).toFixed(1)

      if (!res.ok) {
        // Handle rate limits
        if (res.status === 429 || (data.error && data.error.includes('rate'))) {
          process.stdout.write(`rate limited, waiting 30s... `)
          await new Promise(r => setTimeout(r, 30000))
          // Retry once
          const retry = await fetch(`${BASE}/api/pages/${page.id}/translate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
          })
          if (retry.ok) {
            const retryElapsed = ((Date.now() - t0) / 1000).toFixed(1)
            process.stdout.write(`OK (${retryElapsed}s) `)
          } else {
            console.log(`FAIL: ${data.error}`)
            failed++
            continue
          }
        } else {
          console.log(`FAIL (${elapsed}s): ${data.error}`)
          failed++
          continue
        }
      } else {
        process.stdout.write(`${elapsed}s `)
      }

      // Now run step 5 (fit) and step 6 (verify)
      for (const step of [5, 6]) {
        const st0 = Date.now()
        const stepRes = await fetch(`${BASE}/api/pages/${page.id}/pipeline`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ step }),
        })
        const stepElapsed = ((Date.now() - st0) / 1000).toFixed(1)
        if (stepRes.ok) {
          process.stdout.write(`s${step}:${stepElapsed}s `)
        } else {
          const stepData = await stepRes.json()
          process.stdout.write(`s${step}:FAIL(${stepData.error}) `)
        }
      }

      translated++
      console.log('OK')
    } catch (err) {
      console.log(`ERR: ${err.message}`)
      failed++
    }

    // Throttle to avoid Claude API rate limits
    await new Promise(r => setTimeout(r, 2000))

    // Progress every 10 pages
    if ((translated + failed) % 10 === 0 && translated + failed > 0) {
      const elapsed = ((Date.now() - startTime) / 1000 / 60).toFixed(1)
      const rate = translated > 0 ? (translated / (parseFloat(elapsed))) : 1
      const remaining = ((book.totalPages - skipped - translated - failed) / rate).toFixed(0)
      console.log(`  [${elapsed}min | ${translated} translated, ${failed} failed, ${skipped} skipped | ~${remaining}min remaining]`)
    }
  }

  const totalElapsed = ((Date.now() - startTime) / 1000 / 60).toFixed(1)
  console.log(`\n=== Done in ${totalElapsed} min ===`)
  console.log(`Translated: ${translated} | Skipped: ${skipped} | Failed: ${failed}`)
}

main().catch(e => { console.error(e); process.exit(1) })
