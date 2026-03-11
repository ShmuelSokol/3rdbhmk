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
          where: {
            translation: { isNot: null },
          },
          include: {
            translation: {
              select: {
                id: true,
                englishOutput: true,
                status: true,
              },
            },
            layout: {
              select: {
                id: true,
                regions: true,
              },
            },
            ocrResult: {
              include: {
                boxes: {
                  orderBy: [{ lineIndex: 'asc' }, { wordIndex: 'asc' }],
                },
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
      pages: book.pages.map((p) => {
        // Group OCR boxes into lines with bounding rectangles
        const lines: { lineIndex: number; x: number; y: number; width: number; height: number; text: string }[] = []
        if (p.ocrResult?.boxes) {
          const lineMap = new Map<number, typeof p.ocrResult.boxes>()
          for (const box of p.ocrResult.boxes) {
            // Use -1 sentinel for null lineIndex to avoid merging with real line 0
            const li = box.lineIndex ?? -1
            if (!lineMap.has(li)) lineMap.set(li, [])
            lineMap.get(li)!.push(box)
          }
          lineMap.forEach((boxes, lineIndex) => {
            // Use only non-skipped boxes for both bounding rect and text
            const textBoxes = boxes.filter((b) => !b.skipTranslation)
            if (textBoxes.length === 0) return // skip lines with only skipTranslation boxes
            const minX = Math.min(...textBoxes.map((b) => b.x))
            const minY = Math.min(...textBoxes.map((b) => b.y))
            const maxX = Math.max(...textBoxes.map((b) => b.x + b.width))
            const maxY = Math.max(...textBoxes.map((b) => b.y + b.height))
            const text = textBoxes
              .map((b) => b.editedText ?? b.hebrewText)
              .join(' ')
            if (!text.trim()) return // skip empty lines
            lines.push({
              lineIndex,
              x: minX,
              y: minY,
              width: maxX - minX,
              height: maxY - minY,
              text,
            })
          })
          lines.sort((a, b) => a.lineIndex - b.lineIndex)
        }

        return {
          id: p.id,
          pageNumber: p.pageNumber,
          status: p.status,
          translation: p.translation,
          layout: p.layout,
          lines,
        }
      }),
    })
  } catch (error) {
    console.error('Error fetching compare data:', error)
    return NextResponse.json(
      { error: 'Failed to fetch comparison data' },
      { status: 500 }
    )
  }
}
