import { prisma } from '@/lib/prisma'
import { updatePipelineStatus } from './shared'

/**
 * Step 2: Region detection — figure out content blocks from word positions.
 * Groups OCR boxes into lines, detects table vs body regions, saves coordinates.
 */
export async function runStep2(pageId: string) {
  const page = await prisma.page.findUnique({
    where: { id: pageId },
    include: {
      ocrResult: {
        include: {
          boxes: { orderBy: [{ lineIndex: 'asc' }, { wordIndex: 'asc' }] },
        },
      },
    },
  })

  if (!page) throw new Error('Page not found')
  if (!page.ocrResult) throw new Error('OCR not yet run (step 1 required)')

  const boxes = page.ocrResult.boxes.filter(
    (b) => !b.skipTranslation
  )

  if (boxes.length === 0) {
    await updatePipelineStatus(pageId, 'step2_regions')
    return []
  }

  // Group boxes into lines
  const lineMap = new Map<number, typeof boxes>()
  for (const box of boxes) {
    const li = box.lineIndex ?? -1
    if (!lineMap.has(li)) lineMap.set(li, [])
    lineMap.get(li)!.push(box)
  }

  type OcrLine = { y: number; height: number; x: number; width: number; charCount: number; boxIds: string[] }
  const ocrLines: OcrLine[] = []
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
      y: minY, height: maxY - minY, x: minX, width: maxX - minX,
      charCount: text.length,
      boxIds: textBoxes.map((b) => b.id),
    })
  })
  ocrLines.sort((a, b) => a.y - b.y)

  if (ocrLines.length === 0) {
    await updatePipelineStatus(pageId, 'step2_regions')
    return []
  }

  // Compute average line height for text-size-based gap thresholds
  const avgLineHeight = ocrLines.reduce((s, l) => s + l.height, 0) / ocrLines.length
  // Zone split: gap > 3x average line height (replaces hardcoded 8%)
  const ZONE_GAP_THRESHOLD = Math.max(3, avgLineHeight * 3)
  // Body group split: gap > 2x average line height (replaces hardcoded 3%)
  const BODY_GAP_THRESHOLD = Math.max(1.5, avgLineHeight * 2)
  // Running header cutoff: lines above 2x average line height from top
  const HEADER_CUTOFF_Y = Math.max(2, avgLineHeight * 2)

  // Detect table regions vs body text
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

  // Separate running-header lines — each gets its own zone
  const headerLines: OcrLine[] = []
  const bodyLines: { line: OcrLine; isTable: boolean }[] = []
  for (let i = 0; i < ocrLines.length; i++) {
    if (ocrLines[i].y < HEADER_CUTOFF_Y) {
      headerLines.push(ocrLines[i])
    } else {
      bodyLines.push({ line: ocrLines[i], isTable: lineIsTable[i] })
    }
  }

  // Group consecutive body lines into zones of same type
  type Zone = { startY: number; endY: number; isTable: boolean; isRunningHeader: boolean; lines: OcrLine[] }
  const zones: Zone[] = []

  // Each header line becomes its own zone (never table, flagged as running header)
  for (const hl of headerLines) {
    zones.push({
      startY: hl.y,
      endY: hl.y + hl.height,
      isTable: false,
      isRunningHeader: true,
      lines: [hl],
    })
  }

  // Group body lines
  if (bodyLines.length > 0) {
    let curZone: Zone = {
      startY: bodyLines[0].line.y,
      endY: bodyLines[0].line.y + bodyLines[0].line.height,
      isTable: bodyLines[0].isTable,
      isRunningHeader: false,
      lines: [bodyLines[0].line],
    }
    for (let i = 1; i < bodyLines.length; i++) {
      const gap = bodyLines[i].line.y - curZone.endY
      const sameType = bodyLines[i].isTable === curZone.isTable
      if (!sameType || gap > ZONE_GAP_THRESHOLD) {
        zones.push(curZone)
        curZone = {
          startY: bodyLines[i].line.y,
          endY: bodyLines[i].line.y + bodyLines[i].line.height,
          isTable: bodyLines[i].isTable,
          isRunningHeader: false,
          lines: [bodyLines[i].line],
        }
      } else {
        curZone.endY = Math.max(curZone.endY, bodyLines[i].line.y + bodyLines[i].line.height)
        curZone.lines.push(bodyLines[i].line)
      }
    }
    zones.push(curZone)
  }

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
    if (!zones[i].isTable && !zones[i].isRunningHeader && zones[i - 1].isTable && zones[i + 1].isTable) {
      if (!isZoneCentered(zones[i])) zones[i].isTable = true
    }
  }
  for (let i = 0; i < zones.length; i++) {
    if (!zones[i].isTable && !zones[i].isRunningHeader && zones[i].lines.length < 3) {
      if (!isZoneCentered(zones[i])) {
        if ((i > 0 && zones[i - 1].isTable) || (i < zones.length - 1 && zones[i + 1].isTable)) {
          zones[i].isTable = true
        }
      }
    }
  }
  // Merge adjacent same-type zones (but never merge running-header zones)
  // For table zones, don't merge if there's a large gap (separate content sections)
  const mergedZones: Zone[] = []
  for (const z of zones) {
    const prev = mergedZones.length > 0 ? mergedZones[mergedZones.length - 1] : null
    if (prev && z.isTable === prev.isTable && !z.isRunningHeader && !prev.isRunningHeader) {
      const gap = z.startY - prev.endY
      if (z.isTable && gap > 5) {
        // Large gap between table zones — keep separate (annotation vs body text sections)
        mergedZones.push({ ...z })
      } else {
        prev.endY = z.endY
        prev.lines.push(...z.lines)
      }
    } else {
      mergedZones.push({ ...z })
    }
  }

  // Build regions from zones (with header splitting for body zones)
  type RegionData = {
    regionType: string
    origX: number
    origY: number
    origWidth: number
    origHeight: number
    boxIds: string[]
    hebrewText: string
  }
  const regions: RegionData[] = []

  for (const zone of mergedZones) {
    // Running-header zones: each line is its own "header" region
    if (zone.isRunningHeader) {
      for (const line of zone.lines) {
        const allBoxIds = line.boxIds
        const hebrewText = boxes
          .filter((b) => allBoxIds.includes(b.id))
          .map((b) => b.editedText ?? b.hebrewText)
          .join(' ')
        regions.push({
          regionType: 'header',
          origX: line.x,
          origY: line.y,
          origWidth: line.width,
          origHeight: line.height,
          boxIds: allBoxIds,
          hebrewText,
        })
      }
      continue
    }

    if (zone.isTable) {
      // Split table zone into annotation lines (short, scattered) and body text (long, dense)
      const { annotations, body } = splitTableByDensity(zone.lines)

      // Create individual regions for each annotation cluster
      if (annotations.length > 0) {
        const clusters = clusterAnnotationLines(annotations)
        for (const cluster of clusters) {
          const minX = Math.min(...cluster.map((l) => l.x))
          const minY = Math.min(...cluster.map((l) => l.y))
          const maxX = Math.max(...cluster.map((l) => l.x + l.width))
          const maxY = Math.max(...cluster.map((l) => l.y + l.height))
          const clusterBoxIds = cluster.flatMap((l) => l.boxIds)
          const hebrewText = boxes
            .filter((b) => clusterBoxIds.includes(b.id))
            .map((b) => b.editedText ?? b.hebrewText)
            .join(' ')

          regions.push({
            regionType: 'header',
            origX: minX,
            origY: minY,
            origWidth: maxX - minX,
            origHeight: maxY - minY,
            boxIds: clusterBoxIds,
            hebrewText,
          })
        }
      }

      // Create table region(s) for body text — split into X columns if lines
      // cluster into non-overlapping X ranges (e.g., two-column layout with illustrations)
      if (body.length > 0) {
        const bodyColumns = splitBodyByXColumns(body)
        for (const colLines of bodyColumns) {
          const tMinX = Math.min(...colLines.map((l) => l.x))
          const tMaxX = Math.max(...colLines.map((l) => l.x + l.width))
          const tMinY = Math.min(...colLines.map((l) => l.y))
          const tMaxY = Math.max(...colLines.map((l) => l.y + l.height))
          const allBoxIds = colLines.flatMap((l) => l.boxIds)
          const hebrewText = boxes
            .filter((b) => allBoxIds.includes(b.id))
            .map((b) => b.editedText ?? b.hebrewText)
            .join(' ')

          regions.push({
            regionType: 'table',
            origX: tMinX,
            origY: tMinY,
            origWidth: tMaxX - tMinX,
            origHeight: tMaxY - tMinY,
            boxIds: allBoxIds,
            hebrewText,
          })
        }
      }
      continue
    }

    // Body zone — group with header splitting
    const zoneLines = zone.lines
    const bodyWidth = Math.max(...zoneLines.map((l) => l.width))

    const isCenteredLine = (line: OcrLine): boolean => {
      if (line.width > 30 && line.width > bodyWidth * 0.7) return false
      const mid = line.x + line.width / 2
      const leftGap = line.x
      const rightGap = 100 - (line.x + line.width)
      return Math.abs(leftGap - rightGap) < 15 && mid > 30 && mid < 70
    }

    const groups: OcrLine[][] = []
    let currentGroup = [zoneLines[0]]
    for (let i = 1; i < zoneLines.length; i++) {
      const prev = currentGroup[currentGroup.length - 1]
      const prevBottom = prev.y + prev.height
      const gap = zoneLines[i].y - prevBottom
      const prevCentered = isCenteredLine(prev)
      const curCentered = isCenteredLine(zoneLines[i])
      // Split on: large gap, centered→body transition, OR body→centered transition
      const typeSwitch = prevCentered !== curCentered
      if (gap > BODY_GAP_THRESHOLD || typeSwitch) {
        groups.push(currentGroup)
        currentGroup = [zoneLines[i]]
      } else {
        currentGroup.push(zoneLines[i])
      }
    }
    groups.push(currentGroup)

    // Further split: any centered/body boundary within a group gets split out
    const refined: OcrLine[][] = []
    for (const group of groups) {
      if (group.length <= 1) { refined.push(group); continue }
      // Split at every transition between centered and non-centered
      let chunk: OcrLine[] = [group[0]]
      for (let i = 1; i < group.length; i++) {
        const prevCentered = isCenteredLine(group[i - 1])
        const curCentered = isCenteredLine(group[i])
        if (prevCentered !== curCentered) {
          refined.push(chunk)
          chunk = [group[i]]
        } else {
          chunk.push(group[i])
        }
      }
      refined.push(chunk)
    }

    for (const group of refined) {
      const minX = Math.min(...group.map((l) => l.x))
      const minY = Math.min(...group.map((l) => l.y))
      const maxX = Math.max(...group.map((l) => l.x + l.width))
      const maxY = Math.max(...group.map((l) => l.y + l.height))
      const centeredCount = group.filter((l) => isCenteredLine(l)).length
      const centered = centeredCount > group.length / 2
      const allBoxIds = group.flatMap((l) => l.boxIds)
      const hebrewText = boxes
        .filter((b) => allBoxIds.includes(b.id))
        .map((b) => b.editedText ?? b.hebrewText)
        .join(' ')

      regions.push({
        regionType: centered ? 'header' : 'body',
        origX: minX,
        origY: minY,
        origWidth: maxX - minX,
        origHeight: maxY - minY,
        boxIds: allBoxIds,
        hebrewText,
      })
    }
  }

  regions.sort((a, b) => a.origY - b.origY)

  // Delete existing content regions for this page
  await prisma.contentRegion.deleteMany({ where: { pageId } })

  // Create new content regions and link boxes
  const created = []
  for (let i = 0; i < regions.length; i++) {
    const r = regions[i]
    const region = await prisma.contentRegion.create({
      data: {
        pageId,
        regionIndex: i,
        regionType: r.regionType,
        origX: r.origX,
        origY: r.origY,
        origWidth: r.origWidth,
        origHeight: r.origHeight,
        hebrewText: r.hebrewText,
      },
    })

    // Link bounding boxes to this region
    if (r.boxIds.length > 0) {
      await prisma.boundingBox.updateMany({
        where: { id: { in: r.boxIds } },
        data: { regionId: region.id },
      })
    }

    created.push(region)
  }

  await updatePipelineStatus(pageId, 'step2_regions')
  return created
}

/**
 * Split a table zone's lines into annotation lines (short, scattered labels)
 * and body text lines (long, dense column text).
 * Uses a density transition: finds where consecutive lines shift from short to long.
 */
type OcrLineType = { y: number; height: number; x: number; width: number; charCount: number; boxIds: string[] }

function splitTableByDensity(lines: OcrLineType[]): { annotations: OcrLineType[]; body: OcrLineType[] } {
  if (lines.length === 0) return { annotations: [], body: [] }

  const sorted = [...lines].sort((a, b) => a.y - b.y)

  // Find the first Y position where a sliding window of lines has high avg charCount
  // This marks the transition from annotations to body text
  const BODY_CHAR_THRESHOLD = 30
  const WINDOW = 3
  let splitIdx = -1

  for (let i = 0; i <= sorted.length - WINDOW; i++) {
    const window = sorted.slice(i, i + WINDOW)
    // All lines in the window must be long — avoids catching a single short annotation
    // line adjacent to body text
    if (window.every((l) => l.charCount >= BODY_CHAR_THRESHOLD)) {
      splitIdx = i
      break
    }
  }

  // No body text found — all annotations (if scattered), else all table
  if (splitIdx < 0) {
    const avgChars = sorted.reduce((s, l) => s + l.charCount, 0) / sorted.length
    if (avgChars < 25 && isScatteredLayout(sorted)) {
      return { annotations: sorted, body: [] }
    }
    return { annotations: [], body: sorted }
  }

  // No annotations before body text
  if (splitIdx === 0) {
    return { annotations: [], body: sorted }
  }

  const candidateAnnotations = sorted.slice(0, splitIdx)
  // Verify the candidate annotations are actually scattered, not a structured table
  if (isScatteredLayout(candidateAnnotations)) {
    return {
      annotations: candidateAnnotations,
      body: sorted.slice(splitIdx),
    }
  }

  // Not scattered — treat entire zone as table
  return { annotations: [], body: sorted }
}

/**
 * Check if lines are scattered across the page (like diagram annotations)
 * vs organized in consistent columns (like a table or multi-column text).
 * Scattered = many distinct X positions; columnar = lines cluster into 2-3 X columns.
 */
function isScatteredLayout(lines: OcrLineType[]): boolean {
  if (lines.length < 3) return false

  const centers = lines.map((l) => l.x + l.width / 2)
  // Count unique X buckets (15% wide — wide enough to capture table columns)
  const xBuckets = new Map<number, number>()
  for (const c of centers) {
    const bucket = Math.round(c / 15)
    xBuckets.set(bucket, (xBuckets.get(bucket) || 0) + 1)
  }

  const bucketCounts: number[] = []
  xBuckets.forEach((v) => bucketCounts.push(v))
  bucketCounts.sort((a, b) => b - a)
  // If top 2 buckets hold most lines, it's columnar (table), not scattered
  if (bucketCounts.length >= 2) {
    const top2 = bucketCounts[0] + bucketCounts[1]
    if (top2 >= lines.length * 0.55) return false
  }
  // If 1 dominant bucket holds most lines, it's single-column, not scattered
  if (bucketCounts[0] >= lines.length * 0.5) return false

  // Many unique X positions relative to line count = scattered
  return xBuckets.size >= 3
}

/**
 * Split body lines into distinct X columns when lines form non-overlapping
 * X ranges (e.g., two-column layout with illustrations between columns).
 * Clusters lines by X range overlap, then verifies columns are separated.
 */
function splitBodyByXColumns(lines: OcrLineType[]): OcrLineType[][] {
  if (lines.length <= 2) return [lines]

  // Cluster lines by X range overlap
  const clusters: OcrLineType[][] = []

  for (const line of lines) {
    let merged = false
    for (const cluster of clusters) {
      const clusterMinX = Math.min(...cluster.map((l) => l.x))
      const clusterMaxX = Math.max(...cluster.map((l) => l.x + l.width))

      const overlap =
        Math.min(line.x + line.width, clusterMaxX) - Math.max(line.x, clusterMinX)
      const minWidth = Math.min(line.width, clusterMaxX - clusterMinX)

      if (overlap > minWidth * 0.3) {
        cluster.push(line)
        merged = true
        break
      }
    }
    if (!merged) {
      clusters.push([line])
    }
  }

  // Must have 2+ columns, each with 2+ lines
  const validColumns = clusters.filter((c) => c.length >= 2)
  if (validColumns.length < 2) return [lines]

  // Absorb singleton clusters into nearest valid column
  const singletons = clusters.filter((c) => c.length < 2)
  for (const singleton of singletons) {
    const line = singleton[0]
    const lineCenterX = line.x + line.width / 2
    let bestCol = validColumns[0]
    let bestDist = Infinity
    for (const col of validColumns) {
      const colCenterX =
        (Math.min(...col.map((l) => l.x)) + Math.max(...col.map((l) => l.x + l.width))) / 2
      const dist = Math.abs(lineCenterX - colCenterX)
      if (dist < bestDist) {
        bestDist = dist
        bestCol = col
      }
    }
    bestCol.push(line)
  }

  // Verify columns are separated (gap > 1% between adjacent columns)
  validColumns.sort(
    (a, b) => Math.min(...a.map((l) => l.x)) - Math.min(...b.map((l) => l.x))
  )
  for (let i = 0; i < validColumns.length - 1; i++) {
    const leftMaxX = Math.max(...validColumns[i].map((l) => l.x + l.width))
    const rightMinX = Math.min(...validColumns[i + 1].map((l) => l.x))
    if (rightMinX - leftMaxX < 1) {
      return [lines] // Not enough gap — keep as one region
    }
  }

  return validColumns
}

/**
 * Cluster nearby annotation lines so that lines directly below each other
 * (within ~2% Y and overlapping X range) form one region.
 * Lines at same Y but different X stay separate (different annotation positions).
 */
function clusterAnnotationLines(
  lines: { y: number; height: number; x: number; width: number; charCount: number; boxIds: string[] }[]
): typeof lines[] {
  if (lines.length === 0) return []

  const sorted = [...lines].sort((a, b) => a.y - b.y || a.x - b.x)
  const used = new Set<number>()
  const clusters: typeof lines[] = []

  for (let i = 0; i < sorted.length; i++) {
    if (used.has(i)) continue
    const cluster = [sorted[i]]
    used.add(i)

    // Find lines directly below this one (similar X, close Y)
    for (let j = i + 1; j < sorted.length; j++) {
      if (used.has(j)) continue
      const line = sorted[j]
      const clusterBottom = Math.max(...cluster.map((l) => l.y + l.height))
      const clusterLeft = Math.min(...cluster.map((l) => l.x))
      const clusterRight = Math.max(...cluster.map((l) => l.x + l.width))

      const yGap = line.y - clusterBottom
      // X overlap: line must overlap with the cluster's X range
      const xOverlap = Math.min(line.x + line.width, clusterRight) - Math.max(line.x, clusterLeft)
      const minWidth = Math.min(line.width, clusterRight - clusterLeft)

      if (yGap < 2 && yGap >= -0.5 && xOverlap > minWidth * 0.3) {
        cluster.push(line)
        used.add(j)
      }
    }

    clusters.push(cluster)
  }

  return clusters
}
