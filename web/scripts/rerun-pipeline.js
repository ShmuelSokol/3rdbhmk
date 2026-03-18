#!/usr/bin/env node
/**
 * Force-rerun pipeline steps 2-5 on all pages (against live site).
 * Step 2: Regenerate regions using improved text-blocks algorithm
 * Step 3: Re-erase Hebrew text
 * Step 4: Skip (no-op — step2 already writes expanded coords)
 * Step 5: Re-align translations to new regions + re-render fitted page
 *
 * Usage: BASE_URL=https://3rdbhmk.ksavyad.com node scripts/rerun-pipeline.js
 */

const BASE = process.env.BASE_URL || 'http://localhost:3000'
const BOOK_ID = process.argv[2] || 'jcqje5aut5wve5w5b8hv6fcq8'
const STEPS = [2, 3, 4, 5]

async function main() {
  console.log(`Rerun pipeline | Steps: ${STEPS.join(',')} | Server: ${BASE}`)

  const bookRes = await fetch(`${BASE}/api/books/${BOOK_ID}/pipeline`)
  const book = await bookRes.json()
  if (book.error) { console.error('Error:', book.error); process.exit(1) }

  // Only rerun pages that have OCR data (not pending)
  const pages = book.pages.filter(p => p.pipelineStatus !== 'pending' && p.pipelineStatus !== 'locked')
  console.log(`${book.name} | ${pages.length} pages to rerun (${book.totalPages} total)`)

  let completed = 0
  let failed = 0
  const startTime = Date.now()

  for (const page of pages) {
    process.stdout.write(`P${page.pageNumber}/${book.totalPages} `)

    let ok = true
    for (const step of STEPS) {
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
            if (data.error?.includes('429') || res.status === 429) {
              attempts++
              const wait = 5 + attempts * 5
              process.stdout.write(`[429, ${wait}s] `)
              await new Promise(r => setTimeout(r, wait * 1000))
              continue
            }
            process.stdout.write(`FAIL:s${step}(${data.error?.slice(0, 40)}) `)
            ok = false
            break
          }
          process.stdout.write(`s${step}:${elapsed}s `)
          stepOk = true
          break
        } catch (err) {
          attempts++
          if (attempts < 3) {
            process.stdout.write(`[err,retry] `)
            await new Promise(r => setTimeout(r, 3000))
          } else {
            process.stdout.write(`ERR:s${step} `)
            ok = false
          }
        }
      }
      if (!stepOk) { ok = false; break }
    }

    if (ok) {
      completed++
      console.log('OK')
    } else {
      failed++
      console.log('FAILED')
    }

    if ((completed + failed) % 20 === 0 && (completed + failed) > 0) {
      const elapsed = ((Date.now() - startTime) / 1000 / 60).toFixed(1)
      const pagesPerMin = (completed + failed) / parseFloat(elapsed) || 1
      const remaining = ((pages.length - completed - failed) / pagesPerMin).toFixed(0)
      console.log(`  === ${elapsed}min | ${completed}ok ${failed}fail | ~${remaining}min left ===`)
    }
  }

  const totalElapsed = ((Date.now() - startTime) / 1000 / 60).toFixed(1)
  console.log(`\n=== Done in ${totalElapsed} min | ${completed} ok | ${failed} failed ===`)
}

main().catch(e => { console.error(e); process.exit(1) })
