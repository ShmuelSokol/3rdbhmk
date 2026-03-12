import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

/** GET /api/pages/[pageId]/pipeline — get pipeline status for a page */
export async function GET(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const page = await prisma.page.findUnique({
      where: { id: params.pageId },
      include: {
        ocrResult: { include: { boxes: { select: { id: true, regionId: true, isBold: true, textPixelSize: true } } } },
        regions: { orderBy: { regionIndex: 'asc' } },
        erasedImage: true,
        fittedPage: true,
        verificationOcr: true,
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    return NextResponse.json({
      id: page.id,
      pageNumber: page.pageNumber,
      pipelineStatus: page.pipelineStatus,
      lockedAt: page.lockedAt,
      ocrBoxCount: page.ocrResult?.boxes.length || 0,
      regionCount: page.regions.length,
      regions: page.regions,
      hasErasedImage: !!page.erasedImage,
      hasFittedPage: !!page.fittedPage,
      verification: page.verificationOcr
        ? {
            passRate: page.verificationOcr.passRate,
            passed: page.verificationOcr.passed,
            missingCount: (page.verificationOcr.missingWords as string[]).length,
            extraCount: (page.verificationOcr.extraWords as string[]).length,
          }
        : null,
    })
  } catch (error) {
    console.error('Pipeline status error:', error)
    return NextResponse.json({ error: 'Failed to get pipeline status' }, { status: 500 })
  }
}

/** POST /api/pages/[pageId]/pipeline — run a specific step */
export async function POST(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const { step } = await request.json()
    const pageId = params.pageId

    const page = await prisma.page.findUnique({ where: { id: pageId } })
    if (!page) return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    if (page.pipelineStatus === 'locked') {
      return NextResponse.json({ error: 'Page is locked' }, { status: 400 })
    }

    let result: unknown

    switch (step) {
      case 1: {
        const { runStep1 } = await import('@/lib/pipeline/step1-ocr')
        result = await runStep1(pageId)
        break
      }
      case 2: {
        const { runStep2 } = await import('@/lib/pipeline/step2-regions')
        result = await runStep2(pageId)
        break
      }
      case 3: {
        const { runStep3 } = await import('@/lib/pipeline/step3-erase')
        result = await runStep3(pageId)
        break
      }
      case 4: {
        const { runStep4 } = await import('@/lib/pipeline/step4-expand')
        result = await runStep4(pageId)
        break
      }
      case 5: {
        const { runStep5 } = await import('@/lib/pipeline/step5-fit')
        result = await runStep5(pageId)
        break
      }
      case 6: {
        const { runStep6 } = await import('@/lib/pipeline/step6-verify')
        result = await runStep6(pageId)
        break
      }
      default:
        return NextResponse.json({ error: 'Invalid step (1-6)' }, { status: 400 })
    }

    return NextResponse.json({ success: true, step, result })
  } catch (error) {
    console.error('Pipeline step error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Pipeline step failed' },
      { status: 500 }
    )
  }
}
