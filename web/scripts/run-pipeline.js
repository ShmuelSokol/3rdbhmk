#!/usr/bin/env node
/**
 * Run the pipeline on all pages of a book.
 * Usage: node scripts/run-pipeline.js [bookId] [maxStep]
 *
 * - bookId: defaults to full book
 * - maxStep: 1-6, defaults to 4 (skip fitting/verification for untranslated pages)
 *
 * Skips pages that are already at or past the target step.
 * Can be re-run safely — picks up where it left off.
 */

const BASE = process.env.BASE_URL || 'http://localhost:3000'
const BOOK_ID = process.argv[2] || 'jcqje5aut5wve5w5b8hv6fcq8'
const MAX_STEP = parseInt(process.argv[3] || '4')

const STEP_ORDER = ['pending', 'step1_ocr', 'step2_regions', 'step3_erased', 'step4_expanded', 'step5_fitted', 'step6_verified', 'locked']
function stepIdx(s) { return STEP_ORDER.indexOf(s) }

async function main() {
  console.log(`Pipeline | Book: ${BOOK_ID} | Max step: ${MAX_STEP} | Server: ${BASE}`)
  const bookRes = await fetch(`${BASE}/api/books/${BOOK_ID}/pipeline`)
  const book = await bookRes.json()
  if (book.error) { console.error('Error:', book.error); process.exit(1) }

  console.log(`Book: ${book.name} | ${book.totalPages} pages`)
  console.log(`Current: ${JSON.stringify(book.stepCounts)}`)

  const targetStepKey = STEP_ORDER[MAX_STEP] // e.g. MAX_STEP=4 → 'step4_expanded'
  const targetIdx = MAX_STEP

  let completed = 0
  let skipped = 0
  let failed = 0
  const startTime = Date.now()

  for (const page of book.pages) {
    const currentIdx = stepIdx(page.pipelineStatus)

    if (currentIdx >= targetIdx) {
      skipped++
      continue
    }

    const stepsToRun = []
    for (let s = currentIdx + 1; s <= targetIdx; s++) {
      stepsToRun.push(s)
    }

    process.stdout.write(`Page ${page.pageNumber}/${book.totalPages} [${stepsToRun.map(s => s).join(',')}]... `)

    let ok = true
    for (const step of stepsToRun) {
      let attempts = 0
      let stepOk = false
      while (attempts < 3) {
        const t0 = Date.now()
        try {
          const res = await fetch(`${BASE}/api/pages/${page.id}/pipeline`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ step }),
          })
          const data = await res.json()
          const elapsed = ((Date.now() - t0) / 1000).toFixed(1)

          if (!res.ok) {
            if (data.error && data.error.includes('429')) {
              attempts++
              const wait = 5 + attempts * 3
              process.stdout.write(`[rate-limited, waiting ${wait}s] `)
              await new Promise(r => setTimeout(r, wait * 1000))
              continue
            }
            console.log(`FAIL step${step} (${elapsed}s): ${data.error}`)
            ok = false
            break
          }
          process.stdout.write(`s${step}:${elapsed}s `)
          stepOk = true
          break
        } catch (err) {
          attempts++
          if (attempts < 3) {
            process.stdout.write(`[err, retry] `)
            await new Promise(r => setTimeout(r, 3000))
          } else {
            console.log(`ERR step${step}: ${err.message}`)
            ok = false
          }
        }
      }
      if (!stepOk) { ok = false; break }
    }

    // Throttle between pages to avoid Azure rate limits (free tier: ~15 req/min)
    if (ok) await new Promise(r => setTimeout(r, 4000))

    if (ok) {
      completed++
      console.log('OK')
    } else {
      failed++
    }

    // Progress update every 10 pages
    if ((completed + failed) % 10 === 0) {
      const elapsed = ((Date.now() - startTime) / 1000 / 60).toFixed(1)
      const rate = completed / (elapsed / 60) || 0
      const remaining = (book.totalPages - skipped - completed - failed) / (rate || 1)
      console.log(`  [${elapsed}min elapsed | ${completed} done, ${failed} failed, ${skipped} skipped | ~${remaining.toFixed(0)}h remaining]`)
    }
  }

  const totalElapsed = ((Date.now() - startTime) / 1000 / 60).toFixed(1)
  console.log(`\n=== Done in ${totalElapsed} min ===`)
  console.log(`Completed: ${completed} | Skipped: ${skipped} | Failed: ${failed}`)

  // Final status
  const finalRes = await fetch(`${BASE}/api/books/${BOOK_ID}/pipeline`)
  const final = await finalRes.json()
  console.log('Final:', JSON.stringify(final.stepCounts))
}

main().catch(e => { console.error(e); process.exit(1) })
