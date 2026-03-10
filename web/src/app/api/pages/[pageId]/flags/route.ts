import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function GET(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const { pageId } = params

    const page = await prisma.page.findUnique({ where: { id: pageId } })
    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    const flags = await prisma.flag.findMany({
      where: { pageId },
      orderBy: { createdAt: 'desc' },
    })

    return NextResponse.json(flags)
  } catch (error) {
    console.error('Error listing flags:', error)
    return NextResponse.json(
      { error: 'Failed to list flags' },
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

    const page = await prisma.page.findUnique({ where: { id: pageId } })
    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    const { x, y, width, height, type, note } = body

    if (x == null || y == null || width == null || height == null || !type) {
      return NextResponse.json(
        { error: 'Missing required fields: x, y, width, height, type' },
        { status: 400 }
      )
    }

    const flag = await prisma.flag.create({
      data: {
        pageId,
        x,
        y,
        width,
        height,
        type,
        note: note || null,
      },
    })

    return NextResponse.json(flag, { status: 201 })
  } catch (error) {
    console.error('Error creating flag:', error)
    return NextResponse.json(
      { error: 'Failed to create flag' },
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
    const { id, resolved, note, type } = body

    if (!id) {
      return NextResponse.json(
        { error: 'Missing flag id' },
        { status: 400 }
      )
    }

    // Verify the flag belongs to this page
    const existingFlag = await prisma.flag.findUnique({ where: { id } })
    if (!existingFlag || existingFlag.pageId !== pageId) {
      return NextResponse.json(
        { error: 'Flag not found for this page' },
        { status: 404 }
      )
    }

    const updateData: Record<string, unknown> = {}
    if (resolved !== undefined) updateData.resolved = resolved
    if (note !== undefined) updateData.note = note
    if (type !== undefined) updateData.type = type

    const flag = await prisma.flag.update({
      where: { id },
      data: updateData,
    })

    return NextResponse.json(flag)
  } catch (error) {
    console.error('Error updating flag:', error)
    return NextResponse.json(
      { error: 'Failed to update flag' },
      { status: 500 }
    )
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const { pageId } = params
    const url = new URL(request.url)
    const flagId = url.searchParams.get('id')

    if (!flagId) {
      return NextResponse.json(
        { error: 'Missing id query parameter' },
        { status: 400 }
      )
    }

    // Verify the flag belongs to this page
    const existingFlag = await prisma.flag.findUnique({
      where: { id: flagId },
    })
    if (!existingFlag || existingFlag.pageId !== pageId) {
      return NextResponse.json(
        { error: 'Flag not found for this page' },
        { status: 404 }
      )
    }

    await prisma.flag.delete({ where: { id: flagId } })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting flag:', error)
    return NextResponse.json(
      { error: 'Failed to delete flag' },
      { status: 500 }
    )
  }
}
