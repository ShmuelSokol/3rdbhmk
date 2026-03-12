import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

/** POST /api/books/[bookId]/pipeline/run-all
 * Run all pipeline steps on all pages of a book sequentially.
 * Skips locked pages. Re-runs step 1 if textPixelSize is missing.
 * For pages without translation, runs steps 1-4 only.
 */
export const maxDuration = 300 // 5 minute timeout

export async function POST(
  request: Request,
  { params }: { params: { bookId: string } }
) {
  try {
    const bookId = params.bookId
    const book = await prisma.book.findUnique({
      where: { id: bookId },
      include: {
        pages: {
          orderBy: { pageNumber: 'asc' },
          select: { id: true, pageNumber: true, pipelineStatus: true },
        },
      },
    })

    if (!book) {
      return NextResponse.json({ error: 'Book not found' }, { status: 404 })
    }

    const results: { pageNumber: number; steps: { step: number; success: boolean; error?: string }[] }[] = []

    for (const page of book.pages) {
      if (page.pipelineStatus === 'locked') {
        results.push({ pageNumber: page.pageNumber, steps: [{ step: 0, success: true, error: 'Skipped (locked)' }] })
        continue
      }

      const pageResults: { step: number; success: boolean; error?: string }[] = []

      // Check if existing OCR needs enrichment (textPixelSize missing)
      const existingOcr = await prisma.oCRResult.findUnique({
        where: { pageId: page.id },
        include: { boxes: { take: 1, select: { textPixelSize: true } } },
      })
      const needsReOcr = !existingOcr || existingOcr.boxes.length === 0 || existingOcr.boxes[0].textPixelSize === null

      // Check if page has translation (needed for steps 5-6)
      const hasTranslation = await prisma.translation.findUnique({
        where: { pageId: page.id },
        select: { id: true },
      })

      // Determine which steps to run
      const maxStep = hasTranslation ? 6 : 4 // Without translation, can only go to step 4

      const steps = [
        { num: 1, run: needsReOcr, fn: async () => { const { runStep1 } = await import('@/lib/pipeline/step1-ocr'); return runStep1(page.id) } },
        { num: 2, run: true, fn: async () => { const { runStep2 } = await import('@/lib/pipeline/step2-regions'); return runStep2(page.id) } },
        { num: 3, run: true, fn: async () => { const { runStep3 } = await import('@/lib/pipeline/step3-erase'); return runStep3(page.id) } },
        { num: 4, run: true, fn: async () => { const { runStep4 } = await import('@/lib/pipeline/step4-expand'); return runStep4(page.id) } },
        { num: 5, run: maxStep >= 5, fn: async () => { const { runStep5 } = await import('@/lib/pipeline/step5-fit'); return runStep5(page.id) } },
        { num: 6, run: maxStep >= 6, fn: async () => { const { runStep6 } = await import('@/lib/pipeline/step6-verify'); return runStep6(page.id) } },
      ]

      for (const step of steps) {
        if (!step.run) continue
        try {
          await step.fn()
          pageResults.push({ step: step.num, success: true })
        } catch (err) {
          pageResults.push({
            step: step.num,
            success: false,
            error: err instanceof Error ? err.message : 'Unknown error',
          })
          break // Stop this page on first failure, continue to next page
        }
      }

      results.push({ pageNumber: page.pageNumber, steps: pageResults })
      console.log(`Pipeline page ${page.pageNumber}: ${pageResults.map(r => `step${r.step}:${r.success ? 'ok' : 'FAIL'}`).join(', ')}`)
    }

    return NextResponse.json({
      bookId,
      totalPages: book.pages.length,
      results,
    })
  } catch (error) {
    console.error('Batch pipeline error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Batch pipeline failed' },
      { status: 500 }
    )
  }
}
