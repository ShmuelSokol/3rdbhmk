import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export const dynamic = 'force-dynamic'

const REQUIRED_TABLES = [
  'book',
  'page',
  'oCRResult',
  'boundingBox',
  'translation',
] as const

export async function GET() {
  const missing: string[] = []
  let checked = 0

  for (const t of REQUIRED_TABLES) {
    try {
      // @ts-expect-error — indexing Prisma client by model name
      await prisma[t].count()
      checked++
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      if (msg.includes('does not exist') || msg.includes('P2021')) {
        missing.push(t)
      } else {
        return NextResponse.json(
          { status: 'degraded', error: `Unexpected DB error on ${t}: ${msg.slice(0, 200)}` },
          { status: 503 }
        )
      }
    }
  }

  if (missing.length) {
    return NextResponse.json(
      { status: 'schema-missing', missingTables: missing, checked },
      { status: 503 }
    )
  }

  return NextResponse.json({ status: 'ok', v: 4, tablesChecked: checked, t: Date.now() })
}
