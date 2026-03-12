import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { extractPageAsImage } from '@/lib/pdf-utils'
import { writeFile, mkdir, readFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'
import Anthropic from '@anthropic-ai/sdk'
import sharp from 'sharp'

let _anthropic: Anthropic | null = null
function getClient(): Anthropic {
  if (!_anthropic) {
    _anthropic = new Anthropic({
      apiKey: process.env["ANTHROPIC_API_KEY"]!,
    })
  }
  return _anthropic
}

interface LayoutRegion {
  type: 'text' | 'illustration' | 'header' | 'subtitle' | 'table' | 'chart'
  x: number
  y: number
  width: number
  height: number
  label?: string
}

const LAYOUT_PROMPT = `Analyze this scanned Hebrew book page. Identify ALL regions and their types.

Return a JSON array of regions. Each region has:
- type: one of "header", "subtitle", "text", "illustration", "table", "chart"
- x, y, width, height: bounding box as PERCENTAGE of page (0-100)
- label: optional short description

Region types:
- "header": The colored banner/strip at the very top of the page (usually orange/gold with small Hebrew text). Typically the first 2-4% of the page.
- "subtitle": The decorative title area BELOW the header banner. This includes: any circular/oval badge with a Hebrew page number, and any large decorative Hebrew title text below it. This is NOT body text — it is a decorative page title that should be preserved as-is. Typically spans from below the header to about 12-18% of the page.
- "text": Normal body text paragraphs meant for translation. This is regular-sized Hebrew paragraph text, NOT large decorative titles.
- "illustration": Images, photos, 3D renders, drawings, any visual artwork.
- "table": Structured table or index with rows and columns.
- "chart": Diagram with labels.

CRITICAL RULES:
- The "subtitle" region must include the ENTIRE decorative area between the header banner and where normal body text begins. Look for: a circular badge with Hebrew letters, and/or large decorative Hebrew calligraphy text. This whole area is ONE "subtitle" region.
- "text" regions should contain ONLY normal-sized paragraph text, never decorative titles.
- IMPORTANT: There must be NO GAP between regions. The "text" region should start exactly where the "subtitle" region ends. If the subtitle ends at y=16%, the first text region should start at y=16%, not y=18%. Cover all body text — do not leave any uncovered gaps.
- Text regions should span the FULL WIDTH of the text column (typically x=2 to x=98 for single-column pages).
- Mark ALL images/illustrations/3D renders/photos as "illustration"
- Text regions should NOT overlap with illustration regions
- If text labels appear ON TOP of an illustration, include them as part of the illustration region
- Look for multi-column layouts and create separate text regions for each column
- For pages with charts/diagrams, mark the ENTIRE chart area as one "chart" region

Return ONLY valid JSON array, no other text. Example:
[
  {"type": "header", "x": 0, "y": 0, "width": 100, "height": 3},
  {"type": "subtitle", "x": 2, "y": 3, "width": 96, "height": 13},
  {"type": "text", "x": 2, "y": 16, "width": 96, "height": 30},
  {"type": "illustration", "x": 5, "y": 46, "width": 90, "height": 52}
]`

async function getPageImage(pageId: string): Promise<Buffer> {
  const page = await prisma.page.findUnique({
    where: { id: pageId },
    include: { book: true },
  })
  if (!page) throw new Error('Page not found')

  const book = page.book
  const cacheDir = path.join('/tmp', 'bhmk', book.id, 'pages')
  const cachedImagePath = path.join(cacheDir, `page-${page.pageNumber}.png`)

  if (existsSync(cachedImagePath)) {
    return readFile(cachedImagePath)
  }

  const pdfDir = path.join('/tmp', 'bhmk', book.id)
  const pdfPath = path.join(pdfDir, book.filename)

  if (!existsSync(pdfPath)) {
    const supabase = getSupabase()
    const storagePath = `books/${book.id}/${book.filename}`
    const { data, error } = await supabase.storage
      .from('bhmk')
      .download(storagePath)
    await mkdir(pdfDir, { recursive: true })
    if (!error && data) {
      await writeFile(pdfPath, Buffer.from(await data.arrayBuffer()))
    } else {
      // Fall back to chunk-based download (for large PDFs uploaded in parts)
      const chunks: Buffer[] = []
      for (let i = 0; ; i++) {
        const chunkPath = `books/${book.id}/chunks/${book.filename}.part${i}`
        const { data: chunkData, error: chunkError } = await supabase.storage
          .from('bhmk')
          .download(chunkPath)
        if (chunkError || !chunkData) break
        chunks.push(Buffer.from(await chunkData.arrayBuffer()))
      }
      if (chunks.length === 0) throw new Error('Failed to download PDF')
      await writeFile(pdfPath, Buffer.concat(chunks))
    }
  }

  const imageBuffer = await extractPageAsImage(pdfPath, page.pageNumber)
  await mkdir(cacheDir, { recursive: true })
  await writeFile(cachedImagePath, imageBuffer)
  return imageBuffer
}

export async function GET(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const { pageId } = params

    // Check cache first — never query Claude twice for the same page
    const existing = await prisma.pageLayout.findUnique({
      where: { pageId },
    })
    if (existing) {
      return NextResponse.json(existing)
    }

    return NextResponse.json(
      { error: 'Layout not analyzed yet. POST to analyze.' },
      { status: 404 }
    )
  } catch (error) {
    console.error('Error getting layout:', error)
    return NextResponse.json(
      { error: 'Failed to get layout' },
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

    // Check cache — support force re-analyze via ?force=true
    const url = new URL(request.url)
    const force = url.searchParams.get('force') === 'true'

    if (!force) {
      const existing = await prisma.pageLayout.findUnique({
        where: { pageId },
      })
      if (existing) {
        return NextResponse.json(existing)
      }
    }

    // Verify page exists
    const page = await prisma.page.findUnique({ where: { id: pageId } })
    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    // Get page image and resize if needed (Claude's 5MB base64 limit — 3.5MB raw ≈ 4.7MB base64)
    let imageBuffer = await getPageImage(pageId)
    if (imageBuffer.length > 3.5 * 1024 * 1024) {
      imageBuffer = await sharp(imageBuffer)
        .resize({ width: 1200, withoutEnlargement: true })
        .jpeg({ quality: 80 })
        .toBuffer()
    }
    const isJpeg = imageBuffer[0] === 0xFF && imageBuffer[1] === 0xD8
    const mediaType = isJpeg ? 'image/jpeg' : 'image/png'
    const base64Image = imageBuffer.toString('base64')

    // Send to Claude Vision (use Haiku for cost savings)
    const client = getClient()
    const response = await client.messages.create({
      model: 'claude-haiku-4-5-20251001',
      max_tokens: 2048,
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'image',
              source: {
                type: 'base64',
                media_type: mediaType as 'image/jpeg' | 'image/png',
                data: base64Image,
              },
            },
            {
              type: 'text',
              text: LAYOUT_PROMPT,
            },
          ],
        },
      ],
    })

    const textBlock = response.content.find((b) => b.type === 'text')
    if (!textBlock || textBlock.type !== 'text') {
      throw new Error('No text response from Claude')
    }

    // Parse JSON response — extract array robustly
    let regions: LayoutRegion[]
    try {
      const arrayMatch = textBlock.text.match(/\[[\s\S]*\]/)
      if (!arrayMatch) throw new Error('No JSON array found')
      regions = JSON.parse(arrayMatch[0])
    } catch {
      console.error('Failed to parse layout JSON:', textBlock.text)
      throw new Error('Invalid layout response from Claude')
    }

    // Validate and clamp regions
    regions = regions
      .filter(
        (r) =>
          ['text', 'illustration', 'header', 'subtitle', 'table', 'chart'].includes(r.type) &&
          typeof r.x === 'number' &&
          typeof r.y === 'number' &&
          typeof r.width === 'number' &&
          typeof r.height === 'number' &&
          r.x >= 0 && r.y >= 0 && r.width > 0 && r.height > 0
      )
      .map((r) => ({
        ...r,
        x: Math.max(0, Math.min(100, r.x)),
        y: Math.max(0, Math.min(100, r.y)),
        width: Math.min(r.width, 100 - Math.max(0, r.x)),
        height: Math.min(r.height, 100 - Math.max(0, r.y)),
      }))

    // Store in DB — upsert to handle concurrent requests safely
    const layout = await prisma.pageLayout.upsert({
      where: { pageId },
      update: {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        regions: regions as unknown as any,
      },
      create: {
        pageId,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        regions: regions as unknown as any,
      },
    })

    return NextResponse.json(layout)
  } catch (error) {
    console.error('Error analyzing layout:', error)
    return NextResponse.json(
      { error: 'Failed to analyze layout' },
      { status: 500 }
    )
  }
}
