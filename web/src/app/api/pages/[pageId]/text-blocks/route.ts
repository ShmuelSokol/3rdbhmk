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
  columnDividers?: number[] // x-percentages of internal vertical grid lines
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

    // --- Pixel analysis functions (defined early for use in zone splitting) ---
    const computeStripVarianceEarly = (yPct: number, heightPct: number, xPct: number, widthPct: number): number => {
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
      // Ensure minimum width for lines with single-point OCR boxes
      const lineWidth = Math.max(maxX - minX, 2)
      ocrLines.push({ y: minY, height: maxY - minY, x: minX, width: lineWidth, charCount: text.length })
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

    // Merge body zones sandwiched between table zones, and small body zones adjacent to table
    // But NEVER absorb zones whose lines are all centered — those are section headers
    const isZoneCentered = (z: Zone): boolean => {
      if (z.lines.length === 0 || z.lines.length > 3) return false
      return z.lines.every((line) => {
        if (line.width > 30) return false // absolute: section headers < 30% of page
        const leftGap = line.x
        const rightGap = 100 - (line.x + line.width)
        const mid = line.x + line.width / 2
        return Math.abs(leftGap - rightGap) < 15 && mid > 30 && mid < 70
      })
    }
    // First pass: mark body zones that are between two table zones for absorption
    for (let i = 1; i < zones.length - 1; i++) {
      if (!zones[i].isTable && zones[i - 1].isTable && zones[i + 1].isTable) {
        if (!isZoneCentered(zones[i])) {
          zones[i].isTable = true // absorb into table
        }
      }
    }
    // Also absorb small body zones (< 3 lines) adjacent to table
    for (let i = 0; i < zones.length; i++) {
      if (!zones[i].isTable && zones[i].lines.length < 3) {
        if (!isZoneCentered(zones[i])) {
          if ((i > 0 && zones[i - 1].isTable) || (i < zones.length - 1 && zones[i + 1].isTable)) {
            zones[i].isTable = true
          }
        }
      }
    }
    // Now merge adjacent same-type zones
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

    // Reclassify sparse table zones as body text (AFTER merging).
    // Illustration/diagram pages have scattered captions that look "multi-column" but
    // have large vertical gaps between lines (illustrations sit between text).
    // A real table has dense, evenly-spaced rows.
    for (const z of mergedZones) {
      if (!z.isTable || z.lines.length < 2) continue
      // Merge overlapping y-ranges to get UNIQUE text coverage
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
      const uniqueTextH = mergedY.reduce((s, r) => s + (r.bot - r.top), 0)
      const zoneH = z.endY - z.startY
      const textDensity = zoneH > 0 ? uniqueTextH / zoneH : 1
      // Check gaps between merged y-ranges
      const gaps: number[] = []
      for (let i = 1; i < mergedY.length; i++) {
        gaps.push(mergedY[i].top - mergedY[i - 1].bot)
      }
      gaps.sort((a, b) => a - b)
      const medianGap = gaps.length > 0 ? gaps[Math.floor(gaps.length / 2)] : 0
      const maxGap = gaps.length > 0 ? gaps[gaps.length - 1] : 0
      // Sparse zone: median gap > 3% (illustrations between rows) OR any gap > 8% (major break)
      if (medianGap > 3 || maxGap > 8) {
        z.isTable = false
      }
    }

    // Reclassify two-column book pages as body text.
    // Two-column Hebrew book pages have exactly 1 column divider at the center,
    // dense continuous text, and span nearly the full page width. Real tables
    // typically have off-center dividers, less text, or narrower spans.
    // This check runs during block creation below (after column dividers are computed).

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

    // Reclassify diagram/illustration table zones as body text.
    // Real tables have uniform background between text rows.
    // Diagrams have colored blocks, arrows, illustrations → high pixel variance.
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
        // Use OCR line extents as the table bounds (not hardcoded)
        const tMinX = Math.min(...zone.lines.map((l) => l.x))
        const tMaxX = Math.max(...zone.lines.map((l) => l.x + l.width))

        // Detect column dividers: dark vertical lines + OCR text gaps
        const dividers: number[] = []

        // Method 1: scan for dark vertical lines (3px wide to avoid missing thin lines)
        const pxYStart = Math.round((zone.startY / 100) * imgH)
        const pxYEnd = Math.round((zone.endY / 100) * imgH)
        for (let xPct = tMinX + 2; xPct < tMaxX - 2; xPct += 0.2) {
          const pxX = Math.round((xPct / 100) * imgW)
          let darkCount = 0
          let totalCount = 0
          for (let py = pxYStart; py < pxYEnd; py += 4) {
            // Check 3 pixels wide to catch thin lines
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

        // Method 2: find large gaps in OCR line x-coverage (whitespace column separators)
        // Collect all x-ranges covered by text
        const xRanges = zone.lines.map((l) => ({ left: l.x, right: l.x + l.width }))
        xRanges.sort((a, b) => a.left - b.left)
        // Merge overlapping ranges
        const merged: { left: number; right: number }[] = []
        for (const r of xRanges) {
          if (merged.length > 0 && r.left <= merged[merged.length - 1].right + 2) {
            merged[merged.length - 1].right = Math.max(merged[merged.length - 1].right, r.right)
          } else {
            merged.push({ ...r })
          }
        }
        // Gaps > 2% between merged ranges are column separators
        for (let i = 1; i < merged.length; i++) {
          const gap = merged[i].left - merged[i - 1].right
          if (gap > 2) {
            const mid = (merged[i - 1].right + merged[i].left) / 2
            if (!dividers.some((d) => Math.abs(d - mid) < 3)) {
              dividers.push(mid)
            }
          }
        }

        // Method 3: per-line pair gap detection. For y-overlapping line pairs
        // at different x positions, find the gap between them. This catches
        // two-column gutters that Method 2 misses when columns nearly touch.
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

        // Two-column book page detection: if exactly 1 divider near the center
        // of a wide, text-dense block, it's two-column prose, not a table.
        const blockWidth = tMaxX - tMinX
        const blockCenter = tMinX + blockWidth / 2
        const totalChars = zone.lines.reduce((s, l) => s + l.charCount, 0)
        // Two-column book page detection: find the divider closest to the center.
        // Zones with illustrations may have extra dividers from labels, but the
        // dominant column split is still near center.
        const centerDivider = dividers.length > 0
          ? dividers.reduce((closest, d) => Math.abs(d - blockCenter) < Math.abs(closest - blockCenter) ? d : closest)
          : blockCenter
        const isTwoColumnBook =
          dividers.length >= 1 &&
          dividers.length <= 20 &&          // not a real multi-column table
          blockWidth > 75 &&               // spans most of page width
          totalChars > 400 &&              // dense continuous text
          Math.abs(centerDivider - blockCenter) < 8  // dominant divider near center

        // Marginal annotations detection: all dividers clustered in a narrow band
        // on one SIDE of the block (e.g., verse references on the left margin).
        // Real tables have dividers spread across the full width.
        const dividerSpan = dividers.length >= 2 ? dividers[dividers.length - 1] - dividers[0] : 0
        const isMarginalAnnotations =
          dividers.length >= 2 &&
          blockWidth > 50 &&
          totalChars > 200 &&
          dividerSpan < blockWidth * 0.5 &&
          // Dividers must be offset from center (on one side, not spanning middle)
          (Math.max(...dividers) < blockCenter - 5 || Math.min(...dividers) > blockCenter + 5);

        if (isTwoColumnBook || isMarginalAnnotations) {
          // For two-column book pages, check if columns have different heights
          // (indicating an illustration in one column's lower area). If so,
          // split into separate column blocks to avoid overlapping illustrations.
          let didColumnSplit = false
          if (isTwoColumnBook) {
            const divider = centerDivider
            // Filter out short scattered lines (likely illustration labels, not body text)
            const bodyLines = zone.lines.filter(l => l.charCount >= 15)
            const leftLines = bodyLines.filter(l => l.x + l.width / 2 < divider)
            const rightLines = bodyLines.filter(l => l.x + l.width / 2 >= divider)
            const leftMaxY = leftLines.length > 0 ? Math.max(...leftLines.map(l => l.y + l.height)) : zone.startY
            const rightMaxY = rightLines.length > 0 ? Math.max(...rightLines.map(l => l.y + l.height)) : zone.startY
            if (leftLines.length >= 3 && rightLines.length >= 3) {
              // Split into separate column blocks. Each block is limited to its
              // column's x-range so horizontal expansion won't cause overlap.
              const leftMaxX = Math.max(...leftLines.map(l => l.x + l.width))
              const rightMinX = Math.min(...rightLines.map(l => l.x))
              const columnBoundary = (leftMaxX + rightMinX) / 2

              // Sub-block splitting: detect illustration boundaries within columns.
              // Use ALL zone lines (not just bodyLines) for narrowing detection,
              // since narrow column text may have < 15 chars per line.
              const allLeftZoneLines = zone.lines.filter(l => l.x + l.width / 2 < divider)
              const allRightZoneLines = zone.lines.filter(l => l.x + l.width / 2 >= divider)

              for (const [colBodyLines, allColLines] of [
                [leftLines, allLeftZoneLines],
                [rightLines, allRightZoneLines],
              ] as const) {
                if (colBodyLines.length === 0) continue
                const isLeft = colBodyLines === leftLines

                // Sort ALL column lines by y for narrowing detection
                const sortedAll = [...allColLines].sort((a, b) => a.y - b.y)
                const sortedMinX = sortedAll.map(l => l.x).sort((a, b) => a - b)
                const medianMinX = sortedMinX[Math.floor(sortedMinX.length / 2)]
                const X_SHIFT = 20 // 20% of page width = significant narrowing

                // Mark each line as "narrowed" if its left edge shifted significantly
                const isNarrowed = sortedAll.map(l => l.x > medianMinX + X_SHIFT)

                // Find contiguous runs of same-type lines
                type Run = { start: number; end: number; narrowed: boolean }
                const runs: Run[] = []
                let runStart = 0
                for (let i = 1; i <= sortedAll.length; i++) {
                  if (i === sortedAll.length || isNarrowed[i] !== isNarrowed[runStart]) {
                    runs.push({ start: runStart, end: i - 1, narrowed: isNarrowed[runStart] })
                    runStart = i
                  }
                }

                // Build sub-block regions directly from runs.
                // Real narrowing = narrowed run with >= 2 lines OR at column edge.
                // Isolated narrow lines in the middle (paragraph endings) stay in the wide block.
                type SubRegion = { lines: typeof sortedAll; narrow: boolean }
                const subRegions: SubRegion[] = []
                let curRegionLines: typeof sortedAll = []
                let curNarrow = false

                for (let ri = 0; ri < runs.length; ri++) {
                  const run = runs[ri]
                  const runLines = sortedAll.slice(run.start, run.end + 1)
                  // Only allow single-line narrowing at the BOTTOM edge (last run),
                  // AND only if pixel analysis confirms an illustration beside the narrow text.
                  // Top-edge single lines are usually captions/page numbers, not illustrations.
                  const atBottomEdge = ri === runs.length - 1
                  let isRealNarrowing = run.narrowed && (runLines.length >= 2 || atBottomEdge)

                  // Pixel validation for single-line bottom-edge narrowing:
                  // check if the gap between the column's normal left edge and the
                  // narrowed line actually contains illustration pixels (high variance).
                  if (isRealNarrowing && runLines.length === 1 && atBottomEdge) {
                    const nLine = runLines[0]
                    const gapX = medianMinX
                    const gapW = nLine.x - medianMinX - 1
                    if (gapW > 5) {
                      const gapVar = computeStripVariance(nLine.y, nLine.height, gapX, gapW)
                      if (gapVar < 200) { // same as VARIANCE_THRESHOLD defined below
                        // Low variance = background, not illustration → paragraph ending
                        isRealNarrowing = false
                      }
                    } else {
                      // Gap too small to contain an illustration
                      isRealNarrowing = false
                    }
                  }

                  if (run.narrowed && !isRealNarrowing) {
                    // Isolated narrow line in middle → absorb into current region
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

                // Helper: split column lines at illustration gaps (y-gaps with high pixel variance)
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
                      if (gVar > 200) { // illustration content in gap
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

                // If no narrowing detected, single block (or split at illustration gaps)
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
                    } as any)
                  }
                } else {
                  // Create a sub-block for each region
                  for (let sri = 0; sri < subRegions.length; sri++) {
                    const region = subRegions[sri]
                    const nextRegion = sri < subRegions.length - 1 ? subRegions[sri + 1] : null
                    const rYTop = Math.min(...region.lines.map(l => l.y))
                    // Bound the y-range by the next region's start to prevent overlap
                    const rYBot = nextRegion
                      ? Math.min(...nextRegion.lines.map(l => l.y))
                      : Math.max(...region.lines.map(l => l.y + l.height)) + 1
                    // Narrow regions: use the narrowed lines directly (not all y-range lines,
                    // which might include wide lines that pull the block into illustration area).
                    // Wide regions: use only bodyLines (filters scattered labels).
                    // For wide regions after narrow regions, skip leading transitional
                    // lines whose x is still shifted (illustration zone) to prevent the
                    // wide block from starting too high and overlapping the illustration.
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
                    // For narrow sub-blocks, constrain expansion to text area.
                    // The illustration is in the space the text wraps around.
                    const narrowMinBound = region.narrow ? gMinX - 2 : undefined
                    allBlocks.push({
                      x: gMinX, y: gMinY,
                      width: gMaxX - gMinX, height: gMaxY - gMinY,
                      hebrewCharCount: blockLines.reduce((s, l) => s + l.charCount, 0),
                      avgLineHeightPct: blockLines.reduce((s, l) => s + l.height, 0) / blockLines.length,
                      centered: false,
                      _columnMaxX: isLeft ? columnBoundary : undefined,
                      _columnMinX: isLeft ? narrowMinBound : columnBoundary,
                    } as any)
                  }
                }
              }
              didColumnSplit = true
            }
          }

          if (!didColumnSplit) {
            // Treat as single body block instead of table
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
        // Use both relative (for multi-line zones) and absolute checks
        if (line.width > 30 && line.width > bodyWidth * 0.7) return false
        const mid = line.x + line.width / 2
        const leftGap = line.x
        const rightGap = 100 - (line.x + line.width)
        return Math.abs(leftGap - rightGap) < 15 && mid > 30 && mid < 70
      }

      const GAP_THRESHOLD = 2.5
      // Illustration-gap splitting: when a gap between body lines contains
      // illustration pixels (high variance), force a split there. This prevents
      // blocks from spanning across illustrations even with small gaps.
      const ILLUST_GAP_MIN = 1.0 // minimum gap (%) to check for illustration
      const ILLUST_VAR_THRESH = 200 // same as expansion VARIANCE_THRESHOLD
      const groups: (typeof ocrLines)[] = []
      let currentGroup = [zoneLines[0]]
      for (let i = 1; i < zoneLines.length; i++) {
        const prev = currentGroup[currentGroup.length - 1]
        const prevBottom = prev.y + prev.height
        const gap = zoneLines[i].y - prevBottom
        const typeSwitch = isCenteredLine(prev) && !isCenteredLine(zoneLines[i])

        // Check for illustration content in the gap
        let illustGap = false
        if (gap > ILLUST_GAP_MIN && gap <= GAP_THRESHOLD) {
          // Gap is small enough that normal splitting wouldn't trigger,
          // but might contain illustration pixels
          const gapMinX = Math.min(prev.x, zoneLines[i].x)
          const gapMaxX = Math.max(prev.x + prev.width, zoneLines[i].x + zoneLines[i].width)
          const gapWidth = Math.max(5, gapMaxX - gapMinX) // at least 5% width
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

        // Skip near-empty groups (< 3 chars) — these are artifacts or page numbers
        // on illustration-heavy pages, not meaningful text blocks.
        if (groupChars < 3) continue

        // Low-density groups with multiple lines: create per-line blocks
        // instead of one wide block spanning all scattered labels.
        // Also cap width for ultra-wide low-char lines on illustration pages.
        if (groupDensity < 0.06 && group.length > 1 && groupChars < 50) {
          for (const line of group) {
            let lineW = line.width
            let lineX = line.x
            // Cap ultra-wide lines with few chars to prevent covering illustrations
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

    // Low text density threshold: blocks below this are likely small labels
    // within illustrations — limit their expansion to prevent covering illustrations.
    const LOW_DENSITY_THRESHOLD = 0.08 // chars per pct² area

    const expandedBlocks: TextBlock[] = allBlocks.map((block, bi) => {
      const blockBottom = block.y + block.height
      const blockArea = block.width * block.height
      const textDensity = blockArea > 0 ? block.hebrewCharCount / blockArea : 0
      const isLowDensity = textDensity < LOW_DENSITY_THRESHOLD && !block.centered && block.hebrewCharCount < 30

      // Find the ACTUAL background color by sampling inter-line gaps within the block.
      // Inter-line gaps have low variance (pure background at the text's level).
      // Sample a strip centered on the Hebrew text's x-center.
      const GAP_SCAN_H = 0.3
      const sampleX = Math.max(0, block.x + block.width / 2 - 5)
      const sampleW = Math.min(10, 100 - sampleX)
      const gapColors: [number, number, number][] = []

      for (let sy = block.y; sy < blockBottom; sy += 0.3) {
        const v = computeStripVariance(sy, GAP_SCAN_H, sampleX, sampleW)
        if (v < 50) { // very low variance = inter-line gap (background only)
          gapColors.push(computeStripRGB(sy, GAP_SCAN_H, sampleX, sampleW))
          if (gapColors.length >= 5) break
        }
      }

      let refRGB: [number, number, number]
      if (gapColors.length > 0) {
        // Average the sampled gap colors
        refRGB = [
          gapColors.reduce((s, c) => s + c[0], 0) / gapColors.length,
          gapColors.reduce((s, c) => s + c[1], 0) / gapColors.length,
          gapColors.reduce((s, c) => s + c[2], 0) / gapColors.length,
        ]
      } else {
        // Fallback for single-line blocks: sample from LEFT and RIGHT sides of text
        // at the same y-level — this gets the correct background color even at
        // color boundaries (e.g. reddish header vs white body)
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

      // Expand vertically using the block's own width for scanning
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

      // Tables: don't expand horizontally — the grid border is the boundary
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

      // Low-density blocks (likely labels within illustrations): skip horizontal
      // expansion, limit vertical to ±1%. This keeps them tight around the text
      // instead of expanding into surrounding illustration areas.
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

      // Horizontal expansion: scan from page center outward
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

      // Collect all scan y-positions
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

      // Body text: use widest paired span (left+right from same scan row)
      for (const sy of scanPositions) {
        const { left, right } = scanHoriz(sy)
        if ((right - left) > (bestRight - bestLeft)) {
          bestLeft = left
          bestRight = right
        }
      }

      // For centered text or column-split blocks, also scan from text edges outward
      // (center-out scan may hit the text itself, or the column gutter, and fail to expand)
      const hasColumnBounds = (block as any)._columnMaxX !== undefined || (block as any)._columnMinX !== undefined
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
      const BUFFER = 1 // 1% inset so text doesn't sit on region edges
      // Respect column bounds for column-split blocks
      const colMaxX = (block as any)._columnMaxX
      const colMinX = (block as any)._columnMinX
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
        // Skip overlap resolution for side-by-side column blocks (non-overlapping x)
        const xOverlap = Math.min(prev.x + prev.width, expandedBlocks[i].x + expandedBlocks[i].width) -
                          Math.max(prev.x, expandedBlocks[i].x)
        if (xOverlap < 2) continue
        // Split the overlap evenly
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

    // Compute from final blocks, not zones (two-column reclassification may remove table status)
    const finalHasTable = filteredBlocks.some(b => b.isTableRegion)
    return NextResponse.json({
      blocks: filteredBlocks,
      hasTableRegions: finalHasTable,
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
