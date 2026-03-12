import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

/** GET /api/books/[bookId]/pipeline — get pipeline status for all pages */
export async function GET(
  request: Request,
  { params }: { params: { bookId: string } }
) {
  try {
    const book = await prisma.book.findUnique({
      where: { id: params.bookId },
      include: {
        pages: {
          select: {
            id: true,
            pageNumber: true,
            pipelineStatus: true,
            lockedAt: true,
            status: true,
          },
          orderBy: { pageNumber: 'asc' },
        },
      },
    })

    if (!book) {
      return NextResponse.json({ error: 'Book not found' }, { status: 404 })
    }

    const stepCounts = {
      pending: 0,
      step1_ocr: 0,
      step2_regions: 0,
      step3_erased: 0,
      step4_expanded: 0,
      step5_fitted: 0,
      step6_verified: 0,
      locked: 0,
    }

    for (const p of book.pages) {
      const status = p.pipelineStatus as keyof typeof stepCounts
      if (status in stepCounts) stepCounts[status]++
    }

    return NextResponse.json({
      id: book.id,
      name: book.name,
      totalPages: book.totalPages,
      stepCounts,
      pages: book.pages,
    })
  } catch (error) {
    console.error('Pipeline overview error:', error)
    return NextResponse.json({ error: 'Failed to get pipeline overview' }, { status: 500 })
  }
}
