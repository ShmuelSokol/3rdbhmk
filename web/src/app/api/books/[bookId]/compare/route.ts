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
          include: {
            translation: {
              select: {
                id: true,
                englishOutput: true,
                status: true,
              },
            },
          },
          orderBy: { pageNumber: 'asc' },
        },
      },
    })

    if (!book) {
      return NextResponse.json({ error: 'Book not found' }, { status: 404 })
    }

    return NextResponse.json({
      id: book.id,
      name: book.name,
      totalPages: book.totalPages,
      pages: book.pages.map((p) => ({
        id: p.id,
        pageNumber: p.pageNumber,
        status: p.status,
        translation: p.translation,
      })),
    })
  } catch (error) {
    console.error('Error fetching compare data:', error)
    return NextResponse.json(
      { error: 'Failed to fetch comparison data' },
      { status: 500 }
    )
  }
}
