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
    (b) => !b.skipTranslation && b.y >= 4
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

  // Group consecutive lines into zones of same type
  type Zone = { startY: number; endY: number; isTable: boolean; lines: OcrLine[] }
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
      if (!isZoneCentered(zones[i])) zones[i].isTable = true
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
    if (zone.isTable) {
      const tMinX = Math.min(...zone.lines.map((l) => l.x))
      const tMaxX = Math.max(...zone.lines.map((l) => l.x + l.width))
      const allBoxIds = zone.lines.flatMap((l) => l.boxIds)
      const hebrewText = boxes
        .filter((b) => allBoxIds.includes(b.id))
        .map((b) => b.editedText ?? b.hebrewText)
        .join(' ')

      regions.push({
        regionType: 'table',
        origX: tMinX,
        origY: zone.startY,
        origWidth: tMaxX - tMinX,
        origHeight: zone.endY - zone.startY,
        boxIds: allBoxIds,
        hebrewText,
      })
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

    const GAP_THRESHOLD = 3
    const groups: OcrLine[][] = []
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

    // Split centered→body within groups
    const refined: OcrLine[][] = []
    for (const group of groups) {
      if (group.length <= 1) { refined.push(group); continue }
      let splitIdx = -1
      for (let i = 0; i < group.length - 1; i++) {
        if (isCenteredLine(group[i]) && !isCenteredLine(group[i + 1])) {
          splitIdx = i + 1; break
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
