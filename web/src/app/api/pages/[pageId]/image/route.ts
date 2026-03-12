import { NextResponse } from 'next/server'
import { getPageImageBuffer } from '@/lib/pipeline/shared'

export async function GET(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const { pageId } = params
    const { buffer } = await getPageImageBuffer(pageId)

    return new NextResponse(new Uint8Array(buffer), {
      headers: {
        'Content-Type': 'image/png',
        'Cache-Control': 'public, max-age=3600',
      },
    })
  } catch (error) {
    console.error('Error getting page image:', error)
    return NextResponse.json(
      { error: 'Failed to get page image' },
      { status: 500 }
    )
  }
}
