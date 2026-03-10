import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function GET(
  request: Request,
  { params }: { params: { bookId: string } }
) {
  try {
    const { bookId } = params

    const book = await prisma.book.findUnique({
      where: { id: bookId },
      include: {
        pages: {
          select: {
            id: true,
            pageNumber: true,
            status: true,
          },
          orderBy: { pageNumber: 'asc' },
        },
      },
    })

    if (!book) {
      return NextResponse.json({ error: 'Book not found' }, { status: 404 })
    }

    // Build page count by status
    const statusCounts: Record<string, number> = {}
    for (const page of book.pages) {
      statusCounts[page.status] = (statusCounts[page.status] || 0) + 1
    }

    return NextResponse.json({
      ...book,
      statusSummary: statusCounts,
    })
  } catch (error) {
    console.error('Error getting book:', error)
    return NextResponse.json(
      { error: 'Failed to get book' },
      { status: 500 }
    )
  }
}
