import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

/** GET — get all regions for a page */
export async function GET(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const regions = await prisma.contentRegion.findMany({
      where: { pageId: params.pageId },
      orderBy: { regionIndex: 'asc' },
    })
    return NextResponse.json(regions)
  } catch (error) {
    console.error('Get regions error:', error)
    return NextResponse.json({ error: 'Failed to get regions' }, { status: 500 })
  }
}

/** PUT — update translated text for a region */
export async function PUT(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const { regionId, translatedText } = await request.json()

    if (!regionId || translatedText === undefined) {
      return NextResponse.json({ error: 'regionId and translatedText required' }, { status: 400 })
    }

    const region = await prisma.contentRegion.findUnique({ where: { id: regionId } })
    if (!region || region.pageId !== params.pageId) {
      return NextResponse.json({ error: 'Region not found' }, { status: 404 })
    }

    const updated = await prisma.contentRegion.update({
      where: { id: regionId },
      data: { translatedText },
    })

    return NextResponse.json(updated)
  } catch (error) {
    console.error('Update translation error:', error)
    return NextResponse.json({ error: 'Failed to update translation' }, { status: 500 })
  }
}

/** PATCH — update manual coordinates for a region */
export async function PATCH(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const { regionId, manualX, manualY, manualWidth, manualHeight } = await request.json()

    if (!regionId) {
      return NextResponse.json({ error: 'regionId required' }, { status: 400 })
    }

    const region = await prisma.contentRegion.findUnique({ where: { id: regionId } })
    if (!region || region.pageId !== params.pageId) {
      return NextResponse.json({ error: 'Region not found' }, { status: 404 })
    }

    const updated = await prisma.contentRegion.update({
      where: { id: regionId },
      data: {
        manualX: manualX ?? null,
        manualY: manualY ?? null,
        manualWidth: manualWidth ?? null,
        manualHeight: manualHeight ?? null,
      },
    })

    return NextResponse.json(updated)
  } catch (error) {
    console.error('Update region error:', error)
    return NextResponse.json({ error: 'Failed to update region' }, { status: 500 })
  }
}
