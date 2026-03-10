import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function GET(
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

    return NextResponse.json(page.ocrResult?.boxes || [])
  } catch (error) {
    console.error('Error getting boxes:', error)
    return NextResponse.json(
      { error: 'Failed to get bounding boxes' },
      { status: 500 }
    )
  }
}

export async function PATCH(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const { pageId } = params
    const body = await request.json()

    if (!Array.isArray(body)) {
      return NextResponse.json(
        { error: 'Expected an array of box updates' },
        { status: 400 }
      )
    }

    // Verify the page exists and has an OCR result
    const page = await prisma.page.findUnique({
      where: { id: pageId },
      include: { ocrResult: true },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    if (!page.ocrResult) {
      return NextResponse.json(
        { error: 'No OCR result found for this page' },
        { status: 400 }
      )
    }

    // Update each box
    const updates = await Promise.all(
      body.map(
        async (update: {
          id: string
          x?: number
          y?: number
          width?: number
          height?: number
          editedText?: string
          skipTranslation?: boolean
          englishText?: string
        }) => {
          const { id, ...data } = update
          return prisma.boundingBox.update({
            where: { id },
            data,
          })
        }
      )
    )

    return NextResponse.json(updates)
  } catch (error) {
    console.error('Error updating boxes:', error)
    return NextResponse.json(
      { error: 'Failed to update bounding boxes' },
      { status: 500 }
    )
  }
}

export async function POST(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const { pageId } = params
    const body = await request.json()

    // Verify the page exists and has an OCR result
    const page = await prisma.page.findUnique({
      where: { id: pageId },
      include: { ocrResult: true },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    if (!page.ocrResult) {
      return NextResponse.json(
        { error: 'No OCR result found for this page. Run OCR first.' },
        { status: 400 }
      )
    }

    const box = await prisma.boundingBox.create({
      data: {
        ocrResultId: page.ocrResult.id,
        x: body.x,
        y: body.y,
        width: body.width,
        height: body.height,
        hebrewText: body.hebrewText || '',
        editedText: body.editedText,
        englishText: body.englishText,
        confidence: body.confidence,
        lineIndex: body.lineIndex,
        wordIndex: body.wordIndex,
        isImage: body.isImage ?? false,
        skipTranslation: body.skipTranslation ?? false,
      },
    })

    return NextResponse.json(box, { status: 201 })
  } catch (error) {
    console.error('Error creating box:', error)
    return NextResponse.json(
      { error: 'Failed to create bounding box' },
      { status: 500 }
    )
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const url = new URL(request.url)
    const boxId = url.searchParams.get('id')

    if (!boxId) {
      return NextResponse.json(
        { error: 'Missing id query parameter' },
        { status: 400 }
      )
    }

    // Verify the box belongs to this page
    const { pageId } = params
    const page = await prisma.page.findUnique({
      where: { id: pageId },
      include: { ocrResult: true },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    if (!page.ocrResult) {
      return NextResponse.json(
        { error: 'No OCR result found for this page' },
        { status: 400 }
      )
    }

    // Verify the box belongs to this page's OCR result
    const box = await prisma.boundingBox.findUnique({
      where: { id: boxId },
    })

    if (!box || box.ocrResultId !== page.ocrResult.id) {
      return NextResponse.json(
        { error: 'Bounding box not found for this page' },
        { status: 404 }
      )
    }

    await prisma.boundingBox.delete({ where: { id: boxId } })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting box:', error)
    return NextResponse.json(
      { error: 'Failed to delete bounding box' },
      { status: 500 }
    )
  }
}
