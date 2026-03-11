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
  avgLineHeightPct: number
  centered: boolean
  isTableRegion?: boolean
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
      ocrLines.push({ y: minY, height: maxY - minY, x: minX, width: maxX - minX, charCount: text.length })
    })
    ocrLines.sort((a, b) => a.y - b.y)

    if (ocrLines.length === 0) {
      return NextResponse.json({ blocks: [], hasTableRegions: false })
    }

    // --- Detect table regions vs body text per-line ---
    // A line is "multi-column" if it has y-overlapping neighbors at different x positions
    const isMultiColLine = (idx: number): boolean => {
      const line = ocrLines[idx]
      for (let j = Math.max(0, idx - 5); j < Math.min(ocrLines.length, idx + 6); j++) {
        if (j === idx) continue
        const other = ocrLines[j]
        const yOverlap = Math.min(line.y + line.height, other.y + other.height) - Math.max(line.y, other.y)
        if (yOverlap > 0) {
          const xSep = Math.abs((line.x + line.width / 2) - (other.x + other.width / 2)) > 20
          if (xSep) return true
        }
      }
      return false
    }

    const lineIsTable = ocrLines.map((_, i) => isMultiColLine(i))

    // Group consecutive lines into zones of same type
    type Zone = { startY: number; endY: number; isTable: boolean; lines: typeof ocrLines }
    const zones: Zone[] = []
    let curZone: Zone = {
      startY: ocrLines[0].y,
      endY: ocrLines[0].y + ocrLines[0].height,
      isTable: lineIsTable[0],
      lines: [ocrLines[0]],
    }
    for (let i = 1; i < ocrLines.length; i++) {
      const gap = ocrLines[i].y - curZone.endY
      const sameType = lineIsTable[i] === curZone.isTable
      if (!sameType || gap > 8) {
        zones.push(curZone)
        curZone = {
          startY: ocrLines[i].y,
          endY: ocrLines[i].y + ocrLines[i].height,
          isTable: lineIsTable[i],
          lines: [ocrLines[i]],
        }
      } else {
        curZone.endY = Math.max(curZone.endY, ocrLines[i].y + ocrLines[i].height)
        curZone.lines.push(ocrLines[i])
      }
    }
    zones.push(curZone)

    // Merge small non-table zones into adjacent table zones
    const mergedZones: Zone[] = []
    for (const z of zones) {
      if (mergedZones.length > 0 && z.isTable === mergedZones[mergedZones.length - 1].isTable) {
        const prev = mergedZones[mergedZones.length - 1]
        prev.endY = z.endY
        prev.lines.push(...z.lines)
      } else if (!z.isTable && z.lines.length < 3 && mergedZones.length > 0 && mergedZones[mergedZones.length - 1].isTable) {
        const prev = mergedZones[mergedZones.length - 1]
        prev.endY = z.endY
        prev.lines.push(...z.lines)
      } else {
        mergedZones.push({ ...z })
      }
    }

    const hasTableRegions = mergedZones.some((z) => z.isTable)

    // --- Pixel analysis functions ---

    const computeStripRGB = (yPct: number, heightPct: number, xPct: number, widthPct: number): [number, number, number] => {
      const pxY = Math.max(0, Math.round((yPct / 100) * imgH))
      const pxH = Math.max(1, Math.round((heightPct / 100) * imgH))
      const pxX = Math.max(0, Math.round((xPct / 100) * imgW))
      const endY = Math.min(imgH, pxY + pxH)
      const endX = Math.min(imgW, pxX + Math.max(1, Math.round((widthPct / 100) * imgW)))

      let rSum = 0, gSum = 0, bSum = 0, count = 0
      for (let y = pxY; y < endY; y += 3) {
        for (let x = pxX; x < endX; x += 3) {
          const idx = (y * imgW + x) * channels
          rSum += rawPixels[idx]
          gSum += rawPixels[idx + 1]
          bSum += rawPixels[idx + 2]
          count++
        }
      }
      if (count === 0) return [255, 255, 255]
      return [rSum / count, gSum / count, bSum / count]
    }

    const computeStripVariance = (yPct: number, heightPct: number, xPct: number, widthPct: number): number => {
      const pxY = Math.max(0, Math.round((yPct / 100) * imgH))
      const pxH = Math.max(1, Math.round((heightPct / 100) * imgH))
      const pxX = Math.max(0, Math.round((xPct / 100) * imgW))
      const endY = Math.min(imgH, pxY + pxH)
      const endX = Math.min(imgW, pxX + Math.max(1, Math.round((widthPct / 100) * imgW)))

      let sum = 0, sumSq = 0, count = 0
      for (let y = pxY; y < endY; y += 3) {
        for (let x = pxX; x < endX; x += 3) {
          const idx = (y * imgW + x) * channels
          const lum = rawPixels[idx] * 0.299 + rawPixels[idx + 1] * 0.587 + rawPixels[idx + 2] * 0.114
          sum += lum
          sumSq += lum * lum
          count++
        }
      }
      if (count < 2) return 0
      const mean = sum / count
      return (sumSq / count) - (mean * mean)
    }

    const colorDist = (a: [number, number, number], b: [number, number, number]): number =>
      Math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)

    // --- Build blocks from zones ---

    const allBlocks: TextBlock[] = []

    for (const zone of mergedZones) {
      if (zone.isTable) {
        allBlocks.push({
          x: 2,
          y: zone.startY,
          width: 96,
          height: zone.endY - zone.startY,
          hebrewCharCount: zone.lines.reduce((s, l) => s + l.charCount, 0),
          avgLineHeightPct: zone.lines.reduce((s, l) => s + l.height, 0) / zone.lines.length,
          centered: false,
          isTableRegion: true,
        })
        continue
      }

      // Body zone — group with header splitting
      const zoneLines = zone.lines
      const bodyWidth = Math.max(...zoneLines.map((l) => l.width))

      const isCenteredLine = (line: typeof ocrLines[0]): boolean => {
        if (line.width > bodyWidth * 0.7) return false
        const mid = line.x + line.width / 2
        const leftGap = line.x
        const rightGap = 100 - (line.x + line.width)
        return Math.abs(leftGap - rightGap) < 15 && mid > 30 && mid < 70
      }

      const GAP_THRESHOLD = 3
      const groups: (typeof ocrLines)[] = []
      let currentGroup = [zoneLines[0]]
      for (let i = 1; i < zoneLines.length; i++) {
        const prev = currentGroup[currentGroup.length - 1]
        const prevBottom = prev.y + prev.height
        const gap = zoneLines[i].y - prevBottom
        const typeSwitch = isCenteredLine(prev) && !isCenteredLine(zoneLines[i])

        if (gap > GAP_THRESHOLD || typeSwitch) {
          groups.push(currentGroup)
          currentGroup = [zoneLines[i]]
        } else {
          currentGroup.push(zoneLines[i])
        }
      }
      groups.push(currentGroup)

      // Second pass: split centered→body within groups
      const refined: (typeof ocrLines)[] = []
      for (const group of groups) {
        if (group.length <= 1) { refined.push(group); continue }
        let splitIdx = -1
        for (let i = 0; i < group.length - 1; i++) {
          if (isCenteredLine(group[i]) && !isCenteredLine(group[i + 1])) {
            splitIdx = i + 1
            break
          }
        }
        if (splitIdx > 0) {
          refined.push(group.slice(0, splitIdx))
          refined.push(group.slice(splitIdx))
        } else {
          refined.push(group)
        }
      }

      for (const group of refined) {
        const minX = Math.min(...group.map((l) => l.x))
        const minY = Math.min(...group.map((l) => l.y))
        const maxX = Math.max(...group.map((l) => l.x + l.width))
        const maxY = Math.max(...group.map((l) => l.y + l.height))
        const centeredCount = group.filter((l) => isCenteredLine(l)).length
        allBlocks.push({
          x: minX, y: minY, width: maxX - minX, height: maxY - minY,
          hebrewCharCount: group.reduce((s, l) => s + l.charCount, 0),
          avgLineHeightPct: group.reduce((s, l) => s + l.height, 0) / group.length,
          centered: centeredCount > group.length / 2,
        })
      }
    }

    allBlocks.sort((a, b) => a.y - b.y)

    // --- Expand non-table blocks using pixel analysis ---
    const VARIANCE_THRESHOLD = 200
    const COLOR_DIST_THRESHOLD = 25
    const STEP = 1

    const expandedBlocks: TextBlock[] = allBlocks.map((block, bi) => {
      if (block.isTableRegion) return block

      // Reference background color from strips just outside the text block
      const aboveRGB = computeStripRGB(Math.max(0, block.y - 2), 1, block.x, block.width)
      const belowRGB = computeStripRGB(block.y + block.height, 1, block.x, block.width)
      const aboveBright = aboveRGB[0] + aboveRGB[1] + aboveRGB[2]
      const belowBright = belowRGB[0] + belowRGB[1] + belowRGB[2]
      const refRGB = aboveBright >= belowBright ? aboveRGB : belowRGB

      const isSafe = (yPct: number, hPct: number, xPct: number, wPct: number): boolean => {
        const variance = computeStripVariance(yPct, hPct, xPct, wPct)
        if (variance > VARIANCE_THRESHOLD) return false
        const rgb = computeStripRGB(yPct, hPct, xPct, wPct)
        if (colorDist(rgb, refRGB) > COLOR_DIST_THRESHOLD) return false
        return true
      }

      const blockBottom = block.y + block.height
      const nextBlockTop = bi < allBlocks.length - 1 ? allBlocks[bi + 1].y : 100
      const prevBlockBottom = bi > 0 ? allBlocks[bi - 1].y + allBlocks[bi - 1].height : 4

      let safeBottom = blockBottom
      for (let y = blockBottom; y < nextBlockTop; y += STEP) {
        if (!isSafe(y, STEP, block.x, block.width)) break
        safeBottom = y + STEP
      }

      let safeTop = block.y
      for (let y = block.y - STEP; y >= prevBlockBottom; y -= STEP) {
        if (!isSafe(y, STEP, block.x, block.width)) break
        safeTop = y
      }

      const expandedY = safeTop
      const expandedH = safeBottom - safeTop

      let safeLeft = block.x
      for (let x = block.x - STEP; x >= 0; x -= STEP) {
        if (!isSafe(expandedY, expandedH, x, STEP)) break
        safeLeft = x
      }

      let safeRight = block.x + block.width
      for (let x = safeRight; x < 100; x += STEP) {
        if (!isSafe(expandedY, expandedH, x, STEP)) break
        safeRight = x + STEP
      }

      const PAGE_MARGIN = 2
      return {
        x: Math.max(PAGE_MARGIN, safeLeft),
        y: safeTop,
        width: Math.min(100 - PAGE_MARGIN, safeRight) - Math.max(PAGE_MARGIN, safeLeft),
        height: expandedH,
        hebrewCharCount: block.hebrewCharCount,
        avgLineHeightPct: block.avgLineHeightPct,
        centered: block.centered,
        isTableRegion: false,
      }
    })

    return NextResponse.json({
      blocks: expandedBlocks,
      hasTableRegions,
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
