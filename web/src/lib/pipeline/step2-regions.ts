import { prisma } from '@/lib/prisma'
import { updatePipelineStatus } from './shared'
import { computeTextBlocks } from '@/lib/compute-text-blocks'

/**
 * Step 2: Region detection — uses the shared text-blocks algorithm
 * (zone classification, illustration-gap splitting, per-line splitting,
 * pixel-based safe expansion) to create ContentRegion records.
 *
 * Writes BOTH origX/Y and expandedX/Y so step 4 can be skipped.
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

  const boxes = page.ocrResult.boxes.filter((b) => !b.skipTranslation)

  if (boxes.length === 0) {
    await prisma.contentRegion.deleteMany({ where: { pageId } })
    await updatePipelineStatus(pageId, 'step2_regions')
    return []
  }

  // Get blocks from shared text-blocks algorithm (includes expansion)
  const { blocks } = await computeTextBlocks(pageId)

  if (blocks.length === 0) {
    await prisma.contentRegion.deleteMany({ where: { pageId } })
    await updatePipelineStatus(pageId, 'step2_regions')
    return []
  }

  // Delete existing content regions for this page
  await prisma.contentRegion.deleteMany({ where: { pageId } })

  // Create ContentRegion records by spatial matching of OCR boxes to blocks
  const created = []
  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i]
    const regionType = block.isTableRegion ? 'table' : block.centered ? 'header' : 'body'

    // Find boxes whose center falls within this block's bounds
    const matchedBoxes = boxes.filter((b) => {
      const bCenterX = b.x + b.width / 2
      const bCenterY = b.y + b.height / 2
      return (
        bCenterX >= block.x &&
        bCenterX <= block.x + block.width &&
        bCenterY >= block.y &&
        bCenterY <= block.y + block.height
      )
    })

    const hebrewText = matchedBoxes
      .sort(
        (a, b) =>
          (a.lineIndex ?? 0) - (b.lineIndex ?? 0) ||
          (a.wordIndex ?? 0) - (b.wordIndex ?? 0)
      )
      .map((b) => b.editedText ?? b.hebrewText)
      .join(' ')

    const region = await prisma.contentRegion.create({
      data: {
        pageId,
        regionIndex: i,
        regionType,
        origX: block.x,
        origY: block.y,
        origWidth: block.width,
        origHeight: block.height,
        // Write expanded coordinates too (text-blocks algorithm includes expansion)
        expandedX: block.x,
        expandedY: block.y,
        expandedWidth: block.width,
        expandedHeight: block.height,
        hebrewText,
      },
    })

    // Link bounding boxes to this region
    if (matchedBoxes.length > 0) {
      await prisma.boundingBox.updateMany({
        where: { id: { in: matchedBoxes.map((b) => b.id) } },
        data: { regionId: region.id },
      })
    }

    created.push(region)
  }

  await updatePipelineStatus(pageId, 'step2_regions')
  return created
}
