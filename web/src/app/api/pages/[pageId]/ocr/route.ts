import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { extractPageAsImage } from '@/lib/pdf-utils'
import { analyzePageImage } from '@/lib/azure-ocr'
import { writeFile, mkdir, readFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'
import sharp from 'sharp'

export async function POST(
  request: Request,
  { params }: { params: { pageId: string } }
) {
  try {
    const { pageId } = params

    const page = await prisma.page.findUnique({
      where: { id: pageId },
      include: { book: true },
    })

    if (!page) {
      return NextResponse.json({ error: 'Page not found' }, { status: 404 })
    }

    const book = page.book

    // Get the page image (same logic as the image endpoint)
    const cacheDir = path.join('/tmp', 'bhmk', book.id, 'pages')
    const cachedImagePath = path.join(cacheDir, `page-${page.pageNumber}.png`)
    let imageBuffer: Buffer

    if (existsSync(cachedImagePath)) {
      imageBuffer = await readFile(cachedImagePath)
    } else {
      // Get the PDF
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
          const pdfBuffer = Buffer.from(await data.arrayBuffer())
          await writeFile(pdfPath, pdfBuffer)
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
          if (chunks.length === 0) {
            return NextResponse.json(
              { error: 'Failed to retrieve PDF' },
              { status: 500 }
            )
          }
          await writeFile(pdfPath, Buffer.concat(chunks))
        }
      }

      imageBuffer = await extractPageAsImage(pdfPath, page.pageNumber)

      // Cache it
      await mkdir(cacheDir, { recursive: true })
      await writeFile(cachedImagePath, imageBuffer)
    }

    // Compress image for Azure (max 4MB)
    let ocrBuffer = imageBuffer
    if (imageBuffer.length > 3 * 1024 * 1024) {
      ocrBuffer = await sharp(imageBuffer)
        .jpeg({ quality: 85 })
        .toBuffer()
    }

    // Run Azure OCR
    const ocrWords = await analyzePageImage(ocrBuffer)

    // Delete existing OCR result if any (cascade deletes boxes)
    const existingResult = await prisma.oCRResult.findUnique({
      where: { pageId },
    })
    if (existingResult) {
      await prisma.oCRResult.delete({ where: { pageId } })
    }

    // Create new OCR result with bounding boxes
    const ocrResult = await prisma.oCRResult.create({
      data: {
        pageId,
        boxes: {
          create: ocrWords.map((word) => ({
            x: word.x,
            y: word.y,
            width: word.width,
            height: word.height,
            hebrewText: word.hebrewText,
            confidence: word.confidence,
            lineIndex: word.lineIndex,
            wordIndex: word.wordIndex,
          })),
        },
      },
      include: {
        boxes: {
          orderBy: [{ lineIndex: 'asc' }, { wordIndex: 'asc' }],
        },
      },
    })

    // Update page status
    await prisma.page.update({
      where: { id: pageId },
      data: { status: 'ocr_done' },
    })

    return NextResponse.json(ocrResult)
  } catch (error) {
    console.error('Error running OCR:', error)
    return NextResponse.json(
      { error: 'Failed to run OCR' },
      { status: 500 }
    )
  }
}
