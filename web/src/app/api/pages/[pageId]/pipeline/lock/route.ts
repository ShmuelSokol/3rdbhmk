import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

/** POST — lock/unlock a page */
export async function POST(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const { lock } = await request.json()
    const page = await prisma.page.findUnique({ where: { id: params.pageId } })
    if (!page) return NextResponse.json({ error: 'Page not found' }, { status: 404 })

    if (lock) {
      await prisma.page.update({
        where: { id: params.pageId },
        data: {
          pipelineStatus: 'locked',
          lockedAt: new Date(),
        },
      })
    } else {
      await prisma.page.update({
        where: { id: params.pageId },
        data: {
          pipelineStatus: 'step6_verified',
          lockedAt: null,
        },
      })
    }

    return NextResponse.json({ success: true, locked: lock })
  } catch (error) {
    console.error('Lock error:', error)
    return NextResponse.json({ error: 'Failed to update lock' }, { status: 500 })
  }
}
