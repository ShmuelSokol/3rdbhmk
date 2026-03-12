import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { stepIndex } from '@/lib/pipeline/shared'

/** POST — run all remaining pipeline steps for a page */
export async function POST(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const pageId = params.pageId
    const page = await prisma.page.findUnique({ where: { id: pageId } })
    if (!page) return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    if (page.pipelineStatus === 'locked') {
      return NextResponse.json({ error: 'Page is locked' }, { status: 400 })
    }

    const currentStep = stepIndex(page.pipelineStatus)
    const results: { step: number; success: boolean; error?: string }[] = []

    const steps = [
      { num: 1, fn: async () => { const { runStep1 } = await import('@/lib/pipeline/step1-ocr'); return runStep1(pageId) } },
      { num: 2, fn: async () => { const { runStep2 } = await import('@/lib/pipeline/step2-regions'); return runStep2(pageId) } },
      { num: 3, fn: async () => { const { runStep3 } = await import('@/lib/pipeline/step3-erase'); return runStep3(pageId) } },
      { num: 4, fn: async () => { const { runStep4 } = await import('@/lib/pipeline/step4-expand'); return runStep4(pageId) } },
      { num: 5, fn: async () => { const { runStep5 } = await import('@/lib/pipeline/step5-fit'); return runStep5(pageId) } },
      { num: 6, fn: async () => { const { runStep6 } = await import('@/lib/pipeline/step6-verify'); return runStep6(pageId) } },
    ]

    for (const step of steps) {
      if (step.num <= currentStep) continue // Skip completed steps
      try {
        await step.fn()
        results.push({ step: step.num, success: true })
      } catch (err) {
        results.push({
          step: step.num,
          success: false,
          error: err instanceof Error ? err.message : 'Unknown error',
        })
        break // Stop on first failure
      }
    }

    return NextResponse.json({ results })
  } catch (error) {
    console.error('Run-all error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Pipeline failed' },
      { status: 500 }
    )
  }
}
