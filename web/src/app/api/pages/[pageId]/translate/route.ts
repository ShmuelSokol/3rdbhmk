import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { translateHebrew } from '@/lib/translate'

export async function POST(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const { pageId } = params

    const page = await prisma.page.findUnique({
      where: { id: pageId },
      include: {
        ocrResult: {
          include: {
            boxes: {
              orderBy: [{ lineIndex: 'asc' }, { wordIndex: 'asc' }],
            },
          },
        },
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    if (!page.ocrResult || page.ocrResult.boxes.length === 0) {
      return NextResponse.json(
        { error: 'No OCR result found. Run OCR first.' },
        { status: 400 }
      )
    }

    // Get all bounding boxes, skip those marked skipTranslation
    const boxes = page.ocrResult.boxes.filter((box) => !box.skipTranslation)

    // Group by lineIndex and build full Hebrew text
    const lineMap = new Map<number, string[]>()
    for (const box of boxes) {
      const lineIdx = box.lineIndex ?? 0
      const text = box.editedText ?? box.hebrewText
      if (!lineMap.has(lineIdx)) {
        lineMap.set(lineIdx, [])
      }
      lineMap.get(lineIdx)!.push(text)
    }

    // Build text with lines in order
    const sortedLines = Array.from(lineMap.entries())
      .sort(([a], [b]) => a - b)
      .map(([, words]) => words.join(' '))

    const hebrewText = sortedLines.join('\n')

    if (!hebrewText.trim()) {
      return NextResponse.json(
        { error: 'No text to translate' },
        { status: 400 }
      )
    }

    // Run translation
    const englishOutput = await translateHebrew({ hebrewText })

    // Upsert translation record
    const translation = await prisma.translation.upsert({
      where: { pageId },
      create: {
        pageId,
        hebrewInput: hebrewText,
        englishOutput,
        status: 'draft',
      },
      update: {
        hebrewInput: hebrewText,
        englishOutput,
        status: 'draft',
      },
    })

    // Update page status
    await prisma.page.update({
      where: { id: pageId },
      data: { status: 'translated' },
    })

    return NextResponse.json(translation)
  } catch (error) {
    console.error('Error translating page:', error)
    return NextResponse.json(
      { error: 'Failed to translate page' },
      { status: 500 }
    )
  }
}
