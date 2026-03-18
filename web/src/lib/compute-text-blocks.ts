import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { extractPageAsImage } from '@/lib/pdf-utils'
import { writeFile, mkdir, readFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'
import sharp from 'sharp'

export interface TextBlock {
  x: number
  y: number
  width: number
  height: number
  hebrewCharCount: number
  avgLineHeightPct: number
  centered: boolean
  isTableRegion?: boolean
  columnDividers?: number[] // x-percentages of internal vertical grid lines
  _columnMaxX?: number
  _columnMinX?: number
}

export interface ComputeResult {
  blocks: TextBlock[]
  hasTableRegions: boolean
}

/**
 * Core text-block detection algorithm.
 * Loads page image, runs OCR line grouping, zone classification,
 * block creation (with illustration-gap splitting, per-line splitting),
 * and pixel-based safe expansion.
 *
 * Used by: text-blocks API endpoint, pipeline step2, PDF export.
 */
export async function computeTextBlocks(pageId: string): Promise<ComputeResult> {
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

  if (!page) throw new Error('Page not found')

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
    return { blocks: [], hasTableRegions: false }
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
    // Ensure minimum width for lines with single-point OCR boxes
    const lineWidth = Math.max(maxX - minX, 2)
    ocrLines.push({ y: minY, height: maxY - minY, x: minX, width: lineWidth, charCount: text.length })
  })
  ocrLines.sort((a, b) => a.y - b.y)

  if (ocrLines.length === 0) {
    return { blocks: [], hasTableRegions: false }
  }

  // --- Detect table regions vs body text per-line ---
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

  // Merge body zones sandwiched between table zones
  const isZoneCentered = (z: Zone): boolean => {
    if (z.lines.length === 0 || z.lines.length > 3) return false
    return z.lines.every((line) => {
      if (line.width > 30) return false
      const leftGap = line.x
      const rightGap = 100 - (line.x + line.width)
      const mid = line.x + line.width / 2
      return Math.abs(leftGap - rightGap) < 15 && mid > 30 && mid < 70
    })
  }
  for (let i = 1; i < zones.length - 1; i++) {
    if (!zones[i].isTable && zones[i - 1].isTable && zones[i + 1].isTable) {
      if (!isZoneCentered(zones[i])) {
        zones[i].isTable = true
      }
    }
  }
  for (let i = 0; i < zones.length; i++) {
    if (!zones[i].isTable && zones[i].lines.length < 3) {
      if (!isZoneCentered(zones[i])) {
        if ((i > 0 && zones[i - 1].isTable) || (i < zones.length - 1 && zones[i + 1].isTable)) {
          zones[i].isTable = true
        }
      }
    }
  }
  // Merge adjacent same-type zones
  const mergedZones: Zone[] = []
  for (const z of zones) {
    if (mergedZones.length > 0 && z.isTable === mergedZones[mergedZones.length - 1].isTable) {
      const prev = mergedZones[mergedZones.length - 1]
      prev.endY = z.endY
      prev.lines.push(...z.lines)
    } else {
      mergedZones.push({ ...z })
    }
  }

  // Reclassify sparse table zones as body text
  for (const z of mergedZones) {
    if (!z.isTable || z.lines.length < 2) continue
    const yRanges = z.lines.map(l => ({ top: l.y, bot: l.y + l.height }))
    yRanges.sort((a, b) => a.top - b.top)
    const mergedY: { top: number; bot: number }[] = [{ ...yRanges[0] }]
    for (let i = 1; i < yRanges.length; i++) {
      const last = mergedY[mergedY.length - 1]
      if (yRanges[i].top <= last.bot + 0.5) {
        last.bot = Math.max(last.bot, yRanges[i].bot)
      } else {
        mergedY.push({ ...yRanges[i] })
      }
    }
    const gaps: number[] = []
    for (let i = 1; i < mergedY.length; i++) {
      gaps.push(mergedY[i].top - mergedY[i - 1].bot)
    }
    gaps.sort((a, b) => a - b)
    const medianGap = gaps.length > 0 ? gaps[Math.floor(gaps.length / 2)] : 0
    const maxGap = gaps.length > 0 ? gaps[gaps.length - 1] : 0
    if (medianGap > 3 || maxGap > 8) {
      z.isTable = false
    }
  }

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

  // Reclassify diagram/illustration table zones
  for (const z of mergedZones) {
    if (!z.isTable || z.lines.length < 3) continue
    const zMinX = Math.min(...z.lines.map(l => l.x))
    const zMaxX = Math.max(...z.lines.map(l => l.x + l.width))
    const zWidth = zMaxX - zMinX
    const stripVars: number[] = []
    const sortedLines = [...z.lines].sort((a, b) => a.y - b.y)
    for (let i = 0; i < sortedLines.length - 1; i++) {
      const botOfCurr = sortedLines[i].y + sortedLines[i].height
      const topOfNext = sortedLines[i + 1].y
      const gapH = topOfNext - botOfCurr
      if (gapH < 0.5) continue
      const v = computeStripVariance(botOfCurr, Math.min(gapH, 2), zMinX, zWidth)
      stripVars.push(v)
    }
    if (stripVars.length < 2) continue
    stripVars.sort((a, b) => a - b)
    const medianVar = stripVars[Math.floor(stripVars.length / 2)]
    if (medianVar > 400) {
      z.isTable = false
    }
  }

  // --- Build blocks from zones ---

  const allBlocks: TextBlock[] = []

  for (const zone of mergedZones) {
    if (zone.isTable) {
      const tMinX = Math.min(...zone.lines.map((l) => l.x))
      const tMaxX = Math.max(...zone.lines.map((l) => l.x + l.width))

      // Detect column dividers
      const dividers: number[] = []

      // Method 1: dark vertical lines
      const pxYStart = Math.round((zone.startY / 100) * imgH)
      const pxYEnd = Math.round((zone.endY / 100) * imgH)
      for (let xPct = tMinX + 2; xPct < tMaxX - 2; xPct += 0.2) {
        const pxX = Math.round((xPct / 100) * imgW)
        let darkCount = 0
        let totalCount = 0
        for (let py = pxYStart; py < pxYEnd; py += 4) {
          for (let dx = -1; dx <= 1; dx++) {
            const px = Math.max(0, Math.min(imgW - 1, pxX + dx))
            const idx = (py * imgW + px) * channels
            const lum = rawPixels[idx] * 0.299 + rawPixels[idx + 1] * 0.587 + rawPixels[idx + 2] * 0.114
            if (lum < 100) darkCount++
            totalCount++
          }
        }
        if (totalCount > 0 && darkCount / totalCount > 0.25) {
          if (!dividers.some((d) => Math.abs(d - xPct) < 3)) {
            dividers.push(xPct)
          }
        }
      }

      // Method 2: OCR line x-coverage gaps
      const xRanges = zone.lines.map((l) => ({ left: l.x, right: l.x + l.width }))
      xRanges.sort((a, b) => a.left - b.left)
      const merged: { left: number; right: number }[] = []
      for (const r of xRanges) {
        if (merged.length > 0 && r.left <= merged[merged.length - 1].right + 2) {
          merged[merged.length - 1].right = Math.max(merged[merged.length - 1].right, r.right)
        } else {
          merged.push({ ...r })
        }
      }
      for (let i = 1; i < merged.length; i++) {
        const gap = merged[i].left - merged[i - 1].right
        if (gap > 2) {
          const mid = (merged[i - 1].right + merged[i].left) / 2
          if (!dividers.some((d) => Math.abs(d - mid) < 3)) {
            dividers.push(mid)
          }
        }
      }

      // Method 3: per-line pair gap detection
      const ocrGapCandidates = new Map<number, number>()
      const zoneSorted = [...zone.lines].sort((a, b) => a.y - b.y)
      for (let i = 0; i < zoneSorted.length; i++) {
        const line = zoneSorted[i]
        for (let j = i + 1; j < Math.min(i + 6, zoneSorted.length); j++) {
          const other = zoneSorted[j]
          if (other.y > line.y + line.height + 1) break
          const yOvlp = Math.min(line.y + line.height, other.y + other.height) - Math.max(line.y, other.y)
          if (yOvlp <= 0) continue
          const [left, right] = line.x < other.x ? [line, other] : [other, line]
          const gapStart = left.x + left.width
          const gapEnd = right.x
          if (gapEnd - gapStart < 1) continue
          const mid = (gapStart + gapEnd) / 2
          const bucket = Math.round(mid / 2) * 2
          ocrGapCandidates.set(bucket, (ocrGapCandidates.get(bucket) || 0) + 1)
        }
      }
      ocrGapCandidates.forEach((count, pos) => {
        if (count >= 2 && !dividers.some(d => Math.abs(d - pos) < 3)) {
          dividers.push(pos)
        }
      })

      dividers.sort((a, b) => a - b)

      // Two-column book page detection
      const blockWidth = tMaxX - tMinX
      const blockCenter = tMinX + blockWidth / 2
      const totalChars = zone.lines.reduce((s, l) => s + l.charCount, 0)
      const centerDivider = dividers.length > 0
        ? dividers.reduce((closest, d) => Math.abs(d - blockCenter) < Math.abs(closest - blockCenter) ? d : closest)
        : blockCenter
      const isTwoColumnBook =
        dividers.length >= 1 &&
        dividers.length <= 20 &&
        blockWidth > 75 &&
        totalChars > 400 &&
        Math.abs(centerDivider - blockCenter) < 8

      const dividerSpan = dividers.length >= 2 ? dividers[dividers.length - 1] - dividers[0] : 0
      const isMarginalAnnotations =
        dividers.length >= 2 &&
        blockWidth > 50 &&
        totalChars > 200 &&
        dividerSpan < blockWidth * 0.5 &&
        (Math.max(...dividers) < blockCenter - 5 || Math.min(...dividers) > blockCenter + 5)

      if (isTwoColumnBook || isMarginalAnnotations) {
        let didColumnSplit = false
        if (isTwoColumnBook) {
          const divider = centerDivider
          const bodyLines = zone.lines.filter(l => l.charCount >= 15)
          const leftLines = bodyLines.filter(l => l.x + l.width / 2 < divider)
          const rightLines = bodyLines.filter(l => l.x + l.width / 2 >= divider)
          if (leftLines.length >= 3 && rightLines.length >= 3) {
            const leftMaxX = Math.max(...leftLines.map(l => l.x + l.width))
            const rightMinX = Math.min(...rightLines.map(l => l.x))
            const columnBoundary = (leftMaxX + rightMinX) / 2

            const allLeftZoneLines = zone.lines.filter(l => l.x + l.width / 2 < divider)
            const allRightZoneLines = zone.lines.filter(l => l.x + l.width / 2 >= divider)

            for (const [colBodyLines, allColLines] of [
              [leftLines, allLeftZoneLines],
              [rightLines, allRightZoneLines],
            ] as const) {
              if (colBodyLines.length === 0) continue
              const isLeft = colBodyLines === leftLines

              const sortedAll = [...allColLines].sort((a, b) => a.y - b.y)
              const sortedMinX = sortedAll.map(l => l.x).sort((a, b) => a - b)
              const medianMinX = sortedMinX[Math.floor(sortedMinX.length / 2)]
              const X_SHIFT = 20

              const isNarrowed = sortedAll.map(l => l.x > medianMinX + X_SHIFT)

              type Run = { start: number; end: number; narrowed: boolean }
              const runs: Run[] = []
              let runStart = 0
              for (let i = 1; i <= sortedAll.length; i++) {
                if (i === sortedAll.length || isNarrowed[i] !== isNarrowed[runStart]) {
                  runs.push({ start: runStart, end: i - 1, narrowed: isNarrowed[runStart] })
                  runStart = i
                }
              }

              type SubRegion = { lines: typeof sortedAll; narrow: boolean }
              const subRegions: SubRegion[] = []
              let curRegionLines: typeof sortedAll = []
              let curNarrow = false

              for (let ri = 0; ri < runs.length; ri++) {
                const run = runs[ri]
                const runLines = sortedAll.slice(run.start, run.end + 1)
                const atBottomEdge = ri === runs.length - 1
                let isRealNarrowing = run.narrowed && (runLines.length >= 2 || atBottomEdge)

                if (isRealNarrowing && runLines.length === 1 && atBottomEdge) {
                  const nLine = runLines[0]
                  const gapX = medianMinX
                  const gapW = nLine.x - medianMinX - 1
                  if (gapW > 5) {
                    const gapVar = computeStripVariance(nLine.y, nLine.height, gapX, gapW)
                    if (gapVar < 200) {
                      isRealNarrowing = false
                    }
                  } else {
                    isRealNarrowing = false
                  }
                }

                if (run.narrowed && !isRealNarrowing) {
                  curRegionLines.push(...runLines)
                  continue
                }

                if (isRealNarrowing !== curNarrow && curRegionLines.length > 0) {
                  subRegions.push({ lines: curRegionLines, narrow: curNarrow })
                  curRegionLines = []
                }
                curNarrow = isRealNarrowing
                curRegionLines.push(...runLines)
              }
              if (curRegionLines.length > 0) {
                subRegions.push({ lines: curRegionLines, narrow: curNarrow })
              }

              // Helper: split column lines at illustration gaps
              const splitAtIllustGaps = (lines: typeof colBodyLines): (typeof colBodyLines)[] => {
                if (lines.length <= 1) return [lines]
                const sorted = [...lines].sort((a, b) => a.y - b.y)
                const result: (typeof colBodyLines)[] = []
                let curGroup = [sorted[0]]
                for (let li = 1; li < sorted.length; li++) {
                  const prevBot = curGroup[curGroup.length - 1].y + curGroup[curGroup.length - 1].height
                  const gap = sorted[li].y - prevBot
                  if (gap > 1.0) {
                    const gMinXG = Math.min(curGroup[curGroup.length - 1].x, sorted[li].x)
                    const gMaxXG = Math.max(
                      curGroup[curGroup.length - 1].x + curGroup[curGroup.length - 1].width,
                      sorted[li].x + sorted[li].width
                    )
                    const gWidthG = Math.max(5, gMaxXG - gMinXG)
                    const gVar = computeStripVariance(prevBot, Math.min(gap, 3), gMinXG, gWidthG)
                    if (gVar > 200) {
                      result.push(curGroup)
                      curGroup = [sorted[li]]
                      continue
                    }
                  }
                  curGroup.push(sorted[li])
                }
                result.push(curGroup)
                return result
              }

              if (subRegions.length <= 1 && !subRegions[0]?.narrow) {
                const colLineGroups = splitAtIllustGaps(colBodyLines)
                for (const grpLines of colLineGroups) {
                  const colMinX = Math.min(...grpLines.map(l => l.x))
                  const colMaxX = Math.max(...grpLines.map(l => l.x + l.width))
                  const colMinY = Math.min(...grpLines.map(l => l.y))
                  const colMaxY = Math.max(...grpLines.map(l => l.y + l.height))
                  allBlocks.push({
                    x: colMinX, y: colMinY,
                    width: colMaxX - colMinX, height: colMaxY - colMinY,
                    hebrewCharCount: grpLines.reduce((s, l) => s + l.charCount, 0),
                    avgLineHeightPct: grpLines.reduce((s, l) => s + l.height, 0) / grpLines.length,
                    centered: false,
                    _columnMaxX: isLeft ? columnBoundary : undefined,
                    _columnMinX: isLeft ? undefined : columnBoundary,
                  })
                }
              } else {
                for (let sri = 0; sri < subRegions.length; sri++) {
                  const region = subRegions[sri]
                  const nextRegion = sri < subRegions.length - 1 ? subRegions[sri + 1] : null
                  const rYTop = Math.min(...region.lines.map(l => l.y))
                  const rYBot = nextRegion
                    ? Math.min(...nextRegion.lines.map(l => l.y))
                    : Math.max(...region.lines.map(l => l.y + l.height)) + 1
                  const prevRegion = sri > 0 ? subRegions[sri - 1] : null
                  let wideBlockLines = region.narrow
                    ? region.lines
                    : colBodyLines.filter(l => l.y >= rYTop - 0.5 && l.y < rYBot)
                  if (!region.narrow && prevRegion?.narrow && wideBlockLines.length > 1) {
                    const fullWidthThresh = medianMinX + X_SHIFT / 2
                    const firstFullIdx = wideBlockLines.findIndex(l => l.x <= fullWidthThresh)
                    if (firstFullIdx > 0) {
                      wideBlockLines = wideBlockLines.slice(firstFullIdx)
                    }
                  }
                  const blockLines = wideBlockLines
                  if (blockLines.length === 0) continue
                  const gMinX = Math.min(...blockLines.map(l => l.x))
                  const gMaxX = Math.max(...blockLines.map(l => l.x + l.width))
                  const gMinY = Math.min(...blockLines.map(l => l.y))
                  const gMaxY = Math.max(...blockLines.map(l => l.y + l.height))
                  const narrowMinBound = region.narrow ? gMinX - 2 : undefined
                  allBlocks.push({
                    x: gMinX, y: gMinY,
                    width: gMaxX - gMinX, height: gMaxY - gMinY,
                    hebrewCharCount: blockLines.reduce((s, l) => s + l.charCount, 0),
                    avgLineHeightPct: blockLines.reduce((s, l) => s + l.height, 0) / blockLines.length,
                    centered: false,
                    _columnMaxX: isLeft ? columnBoundary : undefined,
                    _columnMinX: isLeft ? narrowMinBound : columnBoundary,
                  })
                }
              }
            }
            didColumnSplit = true
          }
        }

        if (!didColumnSplit) {
          allBlocks.push({
            x: tMinX,
            y: zone.startY,
            width: blockWidth,
            height: zone.endY - zone.startY,
            hebrewCharCount: totalChars,
            avgLineHeightPct: zone.lines.reduce((s, l) => s + l.height, 0) / zone.lines.length,
            centered: false,
          })
        }
      } else {
        allBlocks.push({
          x: tMinX,
          y: zone.startY,
          width: blockWidth,
          height: zone.endY - zone.startY,
          hebrewCharCount: totalChars,
          avgLineHeightPct: zone.lines.reduce((s, l) => s + l.height, 0) / zone.lines.length,
          centered: false,
          isTableRegion: true,
          columnDividers: dividers.length > 0 ? dividers : undefined,
        })
      }
      continue
    }

    // Body zone — group with header splitting
    const zoneLines = zone.lines
    const bodyWidth = Math.max(...zoneLines.map((l) => l.width))

    const isCenteredLine = (line: typeof ocrLines[0]): boolean => {
      if (line.width > 30 && line.width > bodyWidth * 0.7) return false
      const mid = line.x + line.width / 2
      const leftGap = line.x
      const rightGap = 100 - (line.x + line.width)
      return Math.abs(leftGap - rightGap) < 15 && mid > 30 && mid < 70
    }

    const GAP_THRESHOLD = 2.5
    const ILLUST_GAP_MIN = 1.0
    const ILLUST_VAR_THRESH = 200
    const groups: (typeof ocrLines)[] = []
    let currentGroup = [zoneLines[0]]
    for (let i = 1; i < zoneLines.length; i++) {
      const prev = currentGroup[currentGroup.length - 1]
      const prevBottom = prev.y + prev.height
      const gap = zoneLines[i].y - prevBottom
      const typeSwitch = isCenteredLine(prev) && !isCenteredLine(zoneLines[i])

      let illustGap = false
      if (gap > ILLUST_GAP_MIN && gap <= GAP_THRESHOLD) {
        const gapMinX = Math.min(prev.x, zoneLines[i].x)
        const gapMaxX = Math.max(prev.x + prev.width, zoneLines[i].x + zoneLines[i].width)
        const gapWidth = Math.max(5, gapMaxX - gapMinX)
        const gapVar = computeStripVariance(prevBottom, gap, gapMinX, gapWidth)
        if (gapVar > ILLUST_VAR_THRESH) {
          illustGap = true
        }
      }

      if (gap > GAP_THRESHOLD || typeSwitch || illustGap) {
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

    for (let gi = 0; gi < refined.length; gi++) {
      const group = refined[gi]
      const minX = Math.min(...group.map((l) => l.x))
      const minY = Math.min(...group.map((l) => l.y))
      const maxX = Math.max(...group.map((l) => l.x + l.width))
      const maxY = Math.max(...group.map((l) => l.y + l.height))
      const groupArea = (maxX - minX) * (maxY - minY)
      const groupChars = group.reduce((s, l) => s + l.charCount, 0)
      const groupDensity = groupArea > 0 ? groupChars / groupArea : 0

      if (groupChars < 3) continue

      if (groupDensity < 0.06 && group.length > 1 && groupChars < 50) {
        for (const line of group) {
          let lineW = line.width
          let lineX = line.x
          if (line.charCount < 20 && line.width > 50) {
            lineW = Math.min(line.width, Math.max(25, line.charCount * 2.5))
            const centerX = line.x + line.width / 2
            lineX = Math.max(3, centerX - lineW / 2)
          }
          allBlocks.push({
            x: lineX, y: line.y,
            width: lineW, height: line.height,
            hebrewCharCount: line.charCount,
            avgLineHeightPct: line.height,
            centered: false,
          })
        }
        continue
      }

      const centeredCount = group.filter((l) => isCenteredLine(l)).length
      const centered = centeredCount > group.length / 2
      const lineHeightPct = centered
        ? Math.max(...group.map((l) => l.height))
        : group.reduce((s, l) => s + l.height, 0) / group.length
      allBlocks.push({
        x: minX, y: minY, width: maxX - minX, height: maxY - minY,
        hebrewCharCount: groupChars,
        avgLineHeightPct: lineHeightPct,
        centered,
      })
    }
  }

  allBlocks.sort((a, b) => a.y - b.y)

  // --- Expand non-table blocks using pixel analysis ---
  const VARIANCE_THRESHOLD = 200
  const COLOR_DIST_THRESHOLD = 25
  const STEP = 1
  const LOW_DENSITY_THRESHOLD = 0.08

  const expandedBlocks: TextBlock[] = allBlocks.map((block, bi) => {
    const blockBottom = block.y + block.height
    const blockArea = block.width * block.height
    const textDensity = blockArea > 0 ? block.hebrewCharCount / blockArea : 0
    const isLowDensity = textDensity < LOW_DENSITY_THRESHOLD && !block.centered && block.hebrewCharCount < 30

    // Find the ACTUAL background color by sampling inter-line gaps within the block
    const GAP_SCAN_H = 0.3
    const sampleX = Math.max(0, block.x + block.width / 2 - 5)
    const sampleW = Math.min(10, 100 - sampleX)
    const gapColors: [number, number, number][] = []

    for (let sy = block.y; sy < blockBottom; sy += 0.3) {
      const v = computeStripVariance(sy, GAP_SCAN_H, sampleX, sampleW)
      if (v < 50) {
        gapColors.push(computeStripRGB(sy, GAP_SCAN_H, sampleX, sampleW))
        if (gapColors.length >= 5) break
      }
    }

    let refRGB: [number, number, number]
    if (gapColors.length > 0) {
      refRGB = [
        gapColors.reduce((s, c) => s + c[0], 0) / gapColors.length,
        gapColors.reduce((s, c) => s + c[1], 0) / gapColors.length,
        gapColors.reduce((s, c) => s + c[2], 0) / gapColors.length,
      ]
    } else {
      const sideY = block.y
      const sideH = block.height
      const leftX = Math.max(0, block.x - 5)
      const leftW = Math.min(3, block.x - leftX)
      const rightX = block.x + block.width + 1
      const rightW = Math.min(3, 100 - rightX)
      const leftRGB = leftW > 0 ? computeStripRGB(sideY, sideH, leftX, leftW) : [255, 255, 255] as [number, number, number]
      const rightRGB = rightW > 0 ? computeStripRGB(sideY, sideH, rightX, rightW) : [255, 255, 255] as [number, number, number]
      refRGB = [
        (leftRGB[0] + rightRGB[0]) / 2,
        (leftRGB[1] + rightRGB[1]) / 2,
        (leftRGB[2] + rightRGB[2]) / 2,
      ]
    }

    const isSafe = (yPct: number, hPct: number, xPct: number, wPct: number): boolean => {
      const variance = computeStripVariance(yPct, hPct, xPct, wPct)
      if (variance > VARIANCE_THRESHOLD) return false
      const rgb = computeStripRGB(yPct, hPct, xPct, wPct)
      if (colorDist(rgb, refRGB) > COLOR_DIST_THRESHOLD) return false
      return true
    }

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

    const expandedH = safeBottom - safeTop

    if (block.isTableRegion) {
      const PAGE_MARGIN = 2
      const BUFFER = 1
      const finalLeft = Math.max(PAGE_MARGIN, block.x) + BUFFER
      const finalRight = Math.min(100 - PAGE_MARGIN, block.x + block.width) - BUFFER
      return {
        x: finalLeft,
        y: safeTop,
        width: Math.max(0, finalRight - finalLeft),
        height: expandedH,
        hebrewCharCount: block.hebrewCharCount,
        avgLineHeightPct: block.avgLineHeightPct,
        centered: block.centered,
        isTableRegion: true,
        columnDividers: block.columnDividers,
      }
    }

    if (isLowDensity) {
      const limitedTop = Math.max(block.y - 1, prevBlockBottom)
      const limitedBottom = Math.min(blockBottom + 1, nextBlockTop)
      const PAGE_MARGIN = 2
      const BUFFER = 1
      return {
        x: Math.max(PAGE_MARGIN, block.x) + BUFFER,
        y: limitedTop,
        width: Math.max(0, Math.min(100 - PAGE_MARGIN, block.x + block.width) - BUFFER - (Math.max(PAGE_MARGIN, block.x) + BUFFER)),
        height: limitedBottom - limitedTop,
        hebrewCharCount: block.hebrewCharCount,
        avgLineHeightPct: block.avgLineHeightPct,
        centered: block.centered,
        isTableRegion: false,
      }
    }

    const SCAN_H = 0.3

    const scanHoriz = (scanY: number) => {
      const isHSafe = (xPct: number, wPct: number): boolean => {
        const variance = computeStripVariance(scanY, SCAN_H, xPct, wPct)
        if (variance > VARIANCE_THRESHOLD) return false
        const rgb = computeStripRGB(scanY, SCAN_H, xPct, wPct)
        if (colorDist(rgb, refRGB) > COLOR_DIST_THRESHOLD) return false
        return true
      }
      let left = 50
      for (let x = 50 - STEP; x >= 0; x -= STEP) {
        if (!isHSafe(x, STEP)) break
        left = x
      }
      let right = 50
      for (let x = 50; x < 100; x += STEP) {
        if (!isHSafe(x, STEP)) break
        right = x + STEP
      }
      return { left, right }
    }

    const scanPositions: number[] = []
    for (let sy = block.y; sy < blockBottom; sy += 0.5) {
      scanPositions.push(sy)
    }
    scanPositions.push(Math.max(0, block.y - 0.15))
    scanPositions.push(blockBottom + 0.05)
    const gapAbove = block.y - prevBlockBottom
    const gapBelow = nextBlockTop - blockBottom
    if (gapAbove >= 0.3) scanPositions.push(prevBlockBottom + gapAbove * 0.5)
    if (gapBelow >= 0.3) scanPositions.push(blockBottom + gapBelow * 0.3)

    let bestLeft = 50
    let bestRight = 50

    for (const sy of scanPositions) {
      const { left, right } = scanHoriz(sy)
      if ((right - left) > (bestRight - bestLeft)) {
        bestLeft = left
        bestRight = right
      }
    }

    const hasColumnBounds = block._columnMaxX !== undefined || block._columnMinX !== undefined
    if (block.centered || hasColumnBounds) {
      for (const sy of scanPositions) {
        const isHSafe = (xPct: number, wPct: number): boolean => {
          const variance = computeStripVariance(sy, SCAN_H, xPct, wPct)
          if (variance > VARIANCE_THRESHOLD) return false
          const rgb = computeStripRGB(sy, SCAN_H, xPct, wPct)
          if (colorDist(rgb, refRGB) > COLOR_DIST_THRESHOLD) return false
          return true
        }
        let edgeLeft = block.x
        for (let x = block.x - STEP; x >= 0; x -= STEP) {
          if (!isHSafe(x, STEP)) break
          edgeLeft = x
        }
        let edgeRight = block.x + block.width
        for (let x = block.x + block.width; x < 100; x += STEP) {
          if (!isHSafe(x, STEP)) break
          edgeRight = x + STEP
        }
        if ((edgeRight - edgeLeft) > (bestRight - bestLeft)) {
          bestLeft = edgeLeft
          bestRight = edgeRight
        }
      }
    }

    const safeLeft = bestLeft
    const safeRight = bestRight

    const PAGE_MARGIN = 2
    const BUFFER = 1
    const colMaxX = block._columnMaxX
    const colMinX = block._columnMinX
    let finalLeft = Math.max(PAGE_MARGIN, safeLeft) + BUFFER
    let finalRight = Math.min(100 - PAGE_MARGIN, safeRight) - BUFFER
    if (colMaxX !== undefined) finalRight = Math.min(finalRight, colMaxX - BUFFER)
    if (colMinX !== undefined) finalLeft = Math.max(finalLeft, colMinX + BUFFER)
    return {
      x: finalLeft,
      y: safeTop,
      width: Math.max(0, finalRight - finalLeft),
      height: expandedH,
      hebrewCharCount: block.hebrewCharCount,
      avgLineHeightPct: block.avgLineHeightPct,
      centered: block.centered,
      isTableRegion: false,
    }
  })

  // Resolve vertical overlaps between adjacent blocks
  expandedBlocks.sort((a, b) => a.y - b.y)
  for (let i = 1; i < expandedBlocks.length; i++) {
    const prev = expandedBlocks[i - 1]
    const prevBottom = prev.y + prev.height
    if (prevBottom > expandedBlocks[i].y) {
      const xOverlap = Math.min(prev.x + prev.width, expandedBlocks[i].x + expandedBlocks[i].width) -
                        Math.max(prev.x, expandedBlocks[i].x)
      if (xOverlap < 2) continue
      const mid = (prevBottom + expandedBlocks[i].y) / 2
      prev.height = mid - prev.y
      const newY = mid
      expandedBlocks[i].height = (expandedBlocks[i].y + expandedBlocks[i].height) - newY
      expandedBlocks[i].y = newY
    }
  }

  // Filter out blocks too small to display meaningful text
  const filteredBlocks = expandedBlocks.filter(b =>
    b.width >= 3 && b.height >= 0.5 && b.hebrewCharCount >= 2
  )

  const finalHasTable = filteredBlocks.some(b => b.isTableRegion)
  return { blocks: filteredBlocks, hasTableRegions: finalHasTable }
}
