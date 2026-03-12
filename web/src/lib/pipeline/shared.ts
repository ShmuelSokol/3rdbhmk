import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { extractPageAsImage } from '@/lib/pdf-utils'
import { writeFile, mkdir, readFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'

export type PipelineStep =
  | 'pending'
  | 'step1_ocr'
  | 'step2_regions'
  | 'step3_erased'
  | 'step4_expanded'
  | 'step5_fitted'
  | 'step6_verified'
  | 'locked'

const STEP_ORDER: PipelineStep[] = [
  'pending',
  'step1_ocr',
  'step2_regions',
  'step3_erased',
  'step4_expanded',
  'step5_fitted',
  'step6_verified',
  'locked',
]

export function canAdvanceTo(current: string, target: PipelineStep): boolean {
  const curIdx = STEP_ORDER.indexOf(current as PipelineStep)
  const tgtIdx = STEP_ORDER.indexOf(target)
  return curIdx >= 0 && tgtIdx >= 0 && tgtIdx === curIdx + 1
}

export function stepIndex(step: string): number {
  return STEP_ORDER.indexOf(step as PipelineStep)
}

export async function updatePipelineStatus(pageId: string, status: PipelineStep) {
  await prisma.page.update({
    where: { id: pageId },
    data: { pipelineStatus: status },
  })
}

/**
 * Get the page image buffer, downloading PDF from Supabase if needed.
 */
export async function getPageImageBuffer(
  pageId: string
): Promise<{ buffer: Buffer; page: { id: string; pageNumber: number; bookId: string }; imgW: number; imgH: number }> {
  const page = await prisma.page.findUnique({
    where: { id: pageId },
    include: { book: true },
  })
  if (!page) throw new Error('Page not found')

  const book = page.book
  const cacheDir = path.join('/tmp', 'bhmk', book.id, 'pages')
  const cachedPath = path.join(cacheDir, `page-${page.pageNumber}.png`)

  let imageBuffer: Buffer
  if (existsSync(cachedPath)) {
    imageBuffer = await readFile(cachedPath)
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
    await mkdir(cacheDir, { recursive: true })
    await writeFile(cachedPath, imageBuffer)
  }

  const sharp = (await import('sharp')).default
  const metadata = await sharp(imageBuffer).metadata()
  const imgW = metadata.width || 1655
  const imgH = metadata.height || 2340

  return { buffer: imageBuffer, page: { id: page.id, pageNumber: page.pageNumber, bookId: book.id }, imgW, imgH }
}
