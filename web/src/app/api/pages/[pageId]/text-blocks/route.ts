import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { extractPageAsImage } from '@/lib/pdf-utils'
import { writeFile, mkdir, readFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'
import sharp from 'sharp'

interface TextBlock {
  x: number
  y: number
  width: number
  height: number
  hebrewCharCount: number
  avgLineHeightPct: number // average Hebrew line height as % of page
}

export async function GET(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const { pageId } = params

    const page = await prisma.page.findUnique({
      where: { id: pageId },
      include: {
        book: true,
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

    const book = page.book

    // Load the page image
    const origCacheDir = path.join('/tmp', 'bhmk', book.id, 'pages')
    const origCachedPath = path.join(origCacheDir, `page-${page.pageNumber}.png`)

    let imageBuffer: Buffer
    if (existsSync(origCachedPath)) {
      imageBuffer = await readFile(origCachedPath)
    } else {
      const pdfDir = path.join('/tmp', 'bhmk', book.id)
      const pdfPath = path.join(pdfDir, book.filename)
      if (!existsSync(pdfPath)) {
        const supabase = getSupabase()
        const storagePath = `books/${book.id}/${book.filename}`
        const { data, error } = await supabase.storage
          .from('bhmk')
          .download(storagePath)
        if (error || !data) throw new Error('Failed to download PDF')
        await mkdir(pdfDir, { recursive: true })
        await writeFile(pdfPath, Buffer.from(await data.arrayBuffer()))
      }
      imageBuffer = await extractPageAsImage(pdfPath, page.pageNumber)
      await mkdir(origCacheDir, { recursive: true })
      await writeFile(origCachedPath, imageBuffer)
    }

    const metadata = await sharp(imageBuffer).metadata()
    const imgW = metadata.width || 1655
    const imgH = metadata.height || 2340
    const channels = metadata.channels || 3

    // Load raw pixels for variance analysis
    const rawPixels = await sharp(imageBuffer).raw().toBuffer()

    // Get OCR boxes — skip header and skipTranslation
    const boxes = (page.ocrResult?.boxes || []).filter(
      (b) => !b.skipTranslation && b.y >= 4
    )

    if (boxes.length === 0) {
      return NextResponse.json({ blocks: [] })
    }

    // Group boxes into lines
    const lineMap = new Map<number, typeof boxes>()
    for (const box of boxes) {
      const li = box.lineIndex ?? -1
      if (!lineMap.has(li)) lineMap.set(li, [])
      lineMap.get(li)!.push(box)
    }

    // Build lines with bounding rects
    const ocrLines: { y: number; height: number; x: number; width: number; charCount: number }[] = []
    lineMap.forEach((lineBoxes) => {
      const textBoxes = lineBoxes.filter((b) => !b.skipTranslation)
      if (textBoxes.length === 0) return
      const minX = Math.min(...textBoxes.map((b) => b.x))
      const minY = Math.min(...textBoxes.map((b) => b.y))
      const maxX = Math.max(...textBoxes.map((b) => b.x + b.width))
      const maxY = Math.max(...textBoxes.map((b) => b.y + b.height))
      const text = textBoxes.map((b) => b.editedText ?? b.hebrewText).join('')
      if (!text.trim()) return
      ocrLines.push({
        y: minY,
        height: maxY - minY,
        x: minX,
        width: maxX - minX,
        charCount: text.length,
      })
    })
    ocrLines.sort((a, b) => a.y - b.y)

    if (ocrLines.length === 0) {
      return NextResponse.json({ blocks: [], isTable: false })
    }

    // Detect split-column / table layouts:
    // Check if many lines overlap vertically but are at different x positions
    // (i.e., multiple columns side by side)
    let multiColPairs = 0
    let totalPairs = 0
    for (let i = 0; i < ocrLines.length; i++) {
      for (let j = i + 1; j < Math.min(i + 10, ocrLines.length); j++) {
        const a = ocrLines[i]
        const b = ocrLines[j]
        const yOverlap = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y)
        if (yOverlap > 0) {
          totalPairs++
          // Lines at same y but different x = multi-column
          const xSeparated = Math.abs((a.x + a.width / 2) - (b.x + b.width / 2)) > 20
          if (xSeparated) multiColPairs++
        }
      }
    }
    const isTable = totalPairs > 5 && (multiColPairs / totalPairs) > 0.3

    if (isTable) {
      return NextResponse.json({
        blocks: [],
        isTable: true,
      }, {
        headers: { 'Cache-Control': 'no-cache' },
      })
    }

    // Group lines into blocks (gap > 3% = new block)
    const GAP_THRESHOLD = 3
    const groups: (typeof ocrLines)[] = []
    let currentGroup = [ocrLines[0]]
    for (let i = 1; i < ocrLines.length; i++) {
      const prev = currentGroup[currentGroup.length - 1]
      const prevBottom = prev.y + prev.height
      const gap = ocrLines[i].y - prevBottom
      if (gap > GAP_THRESHOLD) {
        groups.push(currentGroup)
        currentGroup = [ocrLines[i]]
      } else {
        currentGroup.push(ocrLines[i])
      }
    }
    groups.push(currentGroup)

    // Build raw blocks
    const rawBlocks: TextBlock[] = groups.map((group) => {
      const minX = Math.min(...group.map((l) => l.x))
      const minY = Math.min(...group.map((l) => l.y))
      const maxX = Math.max(...group.map((l) => l.x + l.width))
      const maxY = Math.max(...group.map((l) => l.y + l.height))
      const hebrewCharCount = group.reduce((s, l) => s + l.charCount, 0)
      const avgLineHeightPct = group.reduce((s, l) => s + l.height, 0) / group.length
      return { x: minX, y: minY, width: maxX - minX, height: maxY - minY, hebrewCharCount, avgLineHeightPct }
    })

    // Compute pixel variance for a horizontal strip (percentage coords)
    // Returns average variance across the strip — low = empty background, high = illustration
    const computeStripVariance = (yPct: number, heightPct: number, xPct: number, widthPct: number): number => {
      const pxY = Math.max(0, Math.round((yPct / 100) * imgH))
      const pxH = Math.max(1, Math.round((heightPct / 100) * imgH))
      const pxX = Math.max(0, Math.round((xPct / 100) * imgW))
      const pxW = Math.max(1, Math.round((widthPct / 100) * imgW))
      const endY = Math.min(imgH, pxY + pxH)
      const endX = Math.min(imgW, pxX + pxW)

      let sum = 0
      let sumSq = 0
      let count = 0

      // Sample every 3rd pixel for speed
      for (let y = pxY; y < endY; y += 3) {
        for (let x = pxX; x < endX; x += 3) {
          const idx = (y * imgW + x) * channels
          // Use luminance
          const lum = rawPixels[idx] * 0.299 + rawPixels[idx + 1] * 0.587 + rawPixels[idx + 2] * 0.114
          sum += lum
          sumSq += lum * lum
          count++
        }
      }

      if (count < 2) return 0
      const mean = sum / count
      return (sumSq / count) - (mean * mean) // variance
    }

    // For each block, try to expand downward into empty background
    // Scan in 1% increments, stop when we hit high-variance content (illustration)
    const VARIANCE_THRESHOLD = 200 // background is typically < 50, illustrations > 500
    const STEP = 1 // percentage step

    const expandedBlocks: TextBlock[] = rawBlocks.map((block, bi) => {
      const blockBottom = block.y + block.height
      // Don't expand past the next block's top
      const nextBlockTop = bi < rawBlocks.length - 1 ? rawBlocks[bi + 1].y : 100
      const maxBottom = nextBlockTop

      let safeBottom = blockBottom
      for (let y = blockBottom; y < maxBottom; y += STEP) {
        const variance = computeStripVariance(y, STEP, block.x, block.width)
        if (variance > VARIANCE_THRESHOLD) break
        safeBottom = y + STEP
      }

      // Also try expanding upward (between header and first text, or between blocks)
      const prevBlockBottom = bi > 0 ? rawBlocks[bi - 1].y + rawBlocks[bi - 1].height : 4
      const minTop = prevBlockBottom

      let safeTop = block.y
      for (let y = block.y - STEP; y >= minTop; y -= STEP) {
        const variance = computeStripVariance(y, STEP, block.x, block.width)
        if (variance > VARIANCE_THRESHOLD) break
        safeTop = y
      }

      // Expand horizontally — scan left and right as far as safe
      const expandedY = safeTop
      const expandedH = safeBottom - safeTop

      let safeLeft = block.x
      for (let x = block.x - STEP; x >= 0; x -= STEP) {
        const variance = computeStripVariance(expandedY, expandedH, x, STEP)
        if (variance > VARIANCE_THRESHOLD) break
        safeLeft = x
      }

      let safeRight = block.x + block.width
      for (let x = safeRight; x < 100; x += STEP) {
        const variance = computeStripVariance(expandedY, expandedH, x, STEP)
        if (variance > VARIANCE_THRESHOLD) break
        safeRight = x + STEP
      }

      return {
        x: safeLeft,
        y: safeTop,
        width: safeRight - safeLeft,
        height: expandedH,
        hebrewCharCount: block.hebrewCharCount,
        avgLineHeightPct: block.avgLineHeightPct,
      }
    })

    return NextResponse.json({
      blocks: expandedBlocks,
      raw: rawBlocks,
    }, {
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
