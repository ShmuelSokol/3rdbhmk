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
  { params }: { params: { pageId: string; boxId: string } }
) {
  try {
    const { pageId, boxId } = params

    // Get the bounding box
    const box = await prisma.boundingBox.findUnique({
      where: { id: boxId },
      include: {
        ocrResult: {
          include: {
            page: {
              include: { book: true },
            },
          },
        },
      },
    })

    if (!box) {
      return NextResponse.json(
        { error: 'Bounding box not found' },
        { status: 404 }
      )
    }

    // Verify the box belongs to this page
    if (box.ocrResult.pageId !== pageId) {
      return NextResponse.json(
        { error: 'Bounding box does not belong to this page' },
        { status: 400 }
      )
    }

    const page = box.ocrResult.page
    const book = page.book

    // Get the page image
    const cacheDir = path.join('/tmp', 'bhmk', book.id, 'pages')
    const cachedImagePath = path.join(cacheDir, `page-${page.pageNumber}.png`)
    let imageBuffer: Buffer

    if (existsSync(cachedImagePath)) {
      imageBuffer = await readFile(cachedImagePath)
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
      await mkdir(cacheDir, { recursive: true })
      await writeFile(cachedImagePath, imageBuffer)
    }

    // The bounding box coordinates are stored as percentages of the page dimensions.
    // We need to convert them to pixel coordinates based on the actual image size.
    const metadata = await sharp(imageBuffer).metadata()
    const imgWidth = metadata.width!
    const imgHeight = metadata.height!

    const pixelX = Math.round((box.x / 100) * imgWidth)
    const pixelY = Math.round((box.y / 100) * imgHeight)
    const pixelW = Math.round((box.width / 100) * imgWidth)
    const pixelH = Math.round((box.height / 100) * imgHeight)

    // Clamp to image bounds
    const left = Math.max(0, pixelX)
    const top = Math.max(0, pixelY)
    const width = Math.min(pixelW, imgWidth - left)
    const height = Math.min(pixelH, imgHeight - top)

    if (width <= 0 || height <= 0) {
      return NextResponse.json(
        { error: 'Bounding box region is outside the image' },
        { status: 400 }
      )
    }

    // Crop the image to the bounding box region
    const croppedBuffer = await sharp(imageBuffer)
      .extract({ left, top, width, height })
      .png()
      .toBuffer()

    // Run OCR on the cropped region
    const ocrWords = await analyzePageImage(croppedBuffer)

    // Combine all text from the OCR result
    const newText = ocrWords
      .map((w) => w.hebrewText)
      .join(' ')

    // Average confidence
    const avgConfidence = ocrWords.length > 0
      ? ocrWords.reduce((sum, w) => sum + w.confidence, 0) / ocrWords.length
      : box.confidence

    // Update the bounding box with new text
    const updatedBox = await prisma.boundingBox.update({
      where: { id: boxId },
      data: {
        hebrewText: newText || box.hebrewText,
        confidence: avgConfidence,
      },
    })

    return NextResponse.json(updatedBox)
  } catch (error) {
    console.error('Error re-running OCR on box:', error)
    return NextResponse.json(
      { error: 'Failed to re-run OCR on bounding box' },
      { status: 500 }
    )
  }
}
