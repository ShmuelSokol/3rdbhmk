import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'

/** GET /api/pages/[pageId]/pipeline/image?type=erased|fitted
 * Serve pipeline images from Supabase storage */
export async function GET(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const url = new URL(request.url)
    const type = url.searchParams.get('type') || 'erased'

    let storagePath: string | null = null

    if (type === 'erased') {
      const record = await prisma.erasedImage.findUnique({ where: { pageId: params.pageId } })
      storagePath = record?.storagePath || null
    } else if (type === 'fitted') {
      const record = await prisma.fittedPage.findUnique({ where: { pageId: params.pageId } })
      storagePath = record?.storagePath || null
    }

    if (!storagePath) {
      return NextResponse.json({ error: `No ${type} image found` }, { status: 404 })
    }

    const supabase = getSupabase()
    const { data, error } = await supabase.storage.from('bhmk').download(storagePath)
    if (error || !data) {
      return NextResponse.json({ error: 'Failed to download image' }, { status: 500 })
    }

    const buffer = Buffer.from(await data.arrayBuffer())
    return new NextResponse(new Uint8Array(buffer), {
      headers: {
        'Content-Type': 'image/png',
        'Cache-Control': 'public, max-age=60',
      },
    })
  } catch (error) {
    console.error('Pipeline image error:', error)
    return NextResponse.json({ error: 'Failed to get image' }, { status: 500 })
  }
}
