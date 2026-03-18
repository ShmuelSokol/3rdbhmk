import { NextResponse } from 'next/server'
import { computeTextBlocks } from '@/lib/compute-text-blocks'

export async function GET(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const result = await computeTextBlocks(params.pageId)
    return NextResponse.json(result, {
      headers: { 'Cache-Control': 'no-cache' },
    })
  } catch (error) {
    console.error('Error computing text blocks:', error)
    return NextResponse.json(
      { error: 'Failed to compute text blocks' },
      { status: 500 }
    )
  }
}
