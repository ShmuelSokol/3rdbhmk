import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib'
import { getSupabase } from '@/lib/supabase'
import { extractPageAsImage } from '@/lib/pdf-utils'
import { writeFile, mkdir, readFile } from 'fs/promises'
import { existsSync } from 'fs'
import path from 'path'
import sharp from 'sharp'

// --- HELPERS ---

interface TextBlock {
  x: number
  y: number
  width: number
  height: number
  hebrewCharCount: number
  avgLineHeightPct: number
}

interface Paragraph {
  text: string
  isAllBold: boolean
  charCount: number
}

function sanitizeForPdf(text: string): string {
  // Remove Hebrew characters and non-ASCII, keep Latin text
  const hebrewToLatin: Record<string, string> = {
    'א': 'A', 'ב': 'B', 'ג': 'C', 'ד': 'D', 'ה': 'E', 'ו': 'F',
    'ז': 'G', 'ח': 'H', 'ט': 'I', 'י': 'J', 'כ': 'K', 'ל': 'L',
    'מ': 'M', 'נ': 'N', 'ס': 'O', 'ע': 'P', 'פ': 'Q', 'צ': 'R',
    'ק': 'S', 'ר': 'T', 'ש': 'U', 'ת': 'V',
  }
  return text.replace(/[\u0590-\u05FF]/g, (ch) => hebrewToLatin[ch] || '')
             .replace(/[^\x00-\x7F]/g, '')
}

function parseTranslation(raw: string): Paragraph[] {
  const paragraphs: Paragraph[] = []
  const rawParas = raw.split(/\r?\n\s*\r?\n/).map((p) => p.trim()).filter(Boolean)

  const isHeaderLine = (s: string) =>
    /^\d{1,3}\.?$/.test(s) ||
    /^(Introduction|Summary|Yechezkel Perek|Main Topics)/i.test(s)

  if (rawParas.length > 0) {
    const lines = rawParas[0].split('\n').map((l) => l.replace(/\*\*/g, '').trim())
    let skipCount = 0
    for (const line of lines) {
      if (!line || isHeaderLine(line)) { skipCount++; continue }
      break
    }
    if (skipCount > 0) {
      const remaining = rawParas[0].split('\n').slice(skipCount).join('\n').trim()
      if (remaining) rawParas[0] = remaining
      else rawParas.shift()
    }
  }
  while (rawParas.length > 0) {
    const line = rawParas[0].replace(/\*\*/g, '').trim()
    if (isHeaderLine(line)) { rawParas.shift(); continue }
    break
  }
  for (const para of rawParas) {
    const text = sanitizeForPdf(
      para
        .replace(/\*\*([\s\S]*?)\*\*/g, '$1')
        .replace(/\n/g, ' ')
        .replace(/^#+\s+/gm, '')
        .replace(/`([^`]+)`/g, '$1')
        .trim()
    )
    if (!text) continue
    const isAllBold = para.startsWith('**') && para.endsWith('**')
    paragraphs.push({ text, isAllBold, charCount: text.length })
  }
  return paragraphs
}

function wrapText(
  text: string,
  font: { widthOfTextAtSize: (text: string, size: number) => number },
  fontSize: number,
  maxWidth: number
): string[] {
  const words = text.split(' ')
  const lines: string[] = []
  let currentLine = ''
  for (const word of words) {
    const testLine = currentLine ? currentLine + ' ' + word : word
    const width = font.widthOfTextAtSize(testLine, fontSize)
    if (width > maxWidth && currentLine) {
      lines.push(currentLine)
      currentLine = word
    } else {
      currentLine = testLine
    }
  }
  if (currentLine) lines.push(currentLine)
  return lines
}

function assignParagraphsToBlocks(
  blocks: TextBlock[],
  paragraphs: Paragraph[]
): Map<number, Paragraph[]> {
  const result = new Map<number, Paragraph[]>()
  if (blocks.length === 0 || paragraphs.length === 0) return result
  for (let i = 0; i < blocks.length; i++) result.set(i, [])

  const totalHebrew = blocks.reduce((s, b) => s + b.hebrewCharCount, 0)
  if (totalHebrew === 0) {
    const perBlock = Math.ceil(paragraphs.length / blocks.length)
    let pi = 0
    for (let i = 0; i < blocks.length; i++) {
      result.set(i, paragraphs.slice(pi, pi + perBlock))
      pi += perBlock
    }
    return result
  }

  const totalEnglish = paragraphs.reduce((s, p) => s + p.charCount, 0)
  const targets: number[] = []
  let cumHebrew = 0
  for (const block of blocks) {
    cumHebrew += block.hebrewCharCount
    targets.push((cumHebrew / totalHebrew) * totalEnglish)
  }

  let bi = 0
  let runEng = 0
  for (const para of paragraphs) {
    while (bi < blocks.length - 1 && runEng > 0 && runEng >= targets[bi]) bi++
    result.get(bi)!.push(para)
    runEng += para.charCount
  }
  return result
}

// --- Get erased image for a page ---

async function getErasedImage(pageId: string, bookId: string, bookFilename: string, pageNumber: number): Promise<Buffer> {
  // Check erased cache
  const cacheDir = path.join('/tmp', 'bhmk', bookId, 'pages-erased-v2')
  const cachedPath = path.join(cacheDir, `page-${pageNumber}.png`)
  if (existsSync(cachedPath)) {
    return readFile(cachedPath)
  }

  // Check original cache
  const origCacheDir = path.join('/tmp', 'bhmk', bookId, 'pages')
  const origPath = path.join(origCacheDir, `page-${pageNumber}.png`)
  let imageBuffer: Buffer
  if (existsSync(origPath)) {
    imageBuffer = await readFile(origPath)
  } else {
    const pdfDir = path.join('/tmp', 'bhmk', bookId)
    const pdfPath = path.join(pdfDir, bookFilename)
    if (!existsSync(pdfPath)) {
      const supabase = getSupabase()
      const storagePath = `books/${bookId}/${bookFilename}`
      const { data, error } = await supabase.storage.from('bhmk').download(storagePath)
      if (error || !data) throw new Error('Failed to download PDF')
      await mkdir(pdfDir, { recursive: true })
      await writeFile(pdfPath, Buffer.from(await data.arrayBuffer()))
    }
    imageBuffer = await extractPageAsImage(pdfPath, pageNumber)
    await mkdir(origCacheDir, { recursive: true })
    await writeFile(origPath, imageBuffer)
  }

  // Erase Hebrew text
  const page = await prisma.page.findFirst({
    where: { bookId, pageNumber },
    include: { ocrResult: { include: { boxes: true } } },
  })

  const boxes = (page?.ocrResult?.boxes || []).filter((b) => !b.skipTranslation && b.y >= 4)
  if (boxes.length === 0) return imageBuffer

  const metadata = await sharp(imageBuffer).metadata()
  const imgW = metadata.width || 1655
  const imgH = metadata.height || 2340
  const channels = metadata.channels || 3
  const rawPixels = await sharp(imageBuffer).raw().toBuffer()

  const lineMap = new Map<number, typeof boxes>()
  for (const box of boxes) {
    const li = box.lineIndex ?? -1
    if (!lineMap.has(li)) lineMap.set(li, [])
    lineMap.get(li)!.push(box)
  }

  const sampleLocalBg = (pxLeft: number, pxTop: number, pxRight: number, pxBottom: number): [number, number, number] => {
    let rSum = 0, gSum = 0, bSum = 0, count = 0
    const stripW = Math.max(3, Math.round((pxRight - pxLeft) * 0.02))
    const regions = [
      { x0: Math.max(0, pxLeft - stripW), y0: pxTop, x1: pxLeft, y1: pxBottom },
      { x0: pxRight, y0: pxTop, x1: Math.min(imgW, pxRight + stripW), y1: pxBottom },
      { x0: pxLeft, y0: Math.max(0, pxTop - 3), x1: pxRight, y1: pxTop },
      { x0: pxLeft, y0: pxBottom, x1: pxRight, y1: Math.min(imgH, pxBottom + 3) },
    ]
    for (const { x0, y0, x1, y1 } of regions) {
      for (let y = y0; y < y1; y += 2) {
        for (let x = x0; x < x1; x += 2) {
          const idx = (y * imgW + x) * channels
          rSum += rawPixels[idx]; gSum += rawPixels[idx + 1]; bSum += rawPixels[idx + 2]
          count++
        }
      }
    }
    if (count === 0) return [255, 255, 255]
    return [Math.round(rSum / count), Math.round(gSum / count), Math.round(bSum / count)]
  }

  const composites: sharp.OverlayOptions[] = []
  lineMap.forEach((lineBoxes) => {
    const minX = Math.min(...lineBoxes.map((b) => b.x))
    const minY = Math.min(...lineBoxes.map((b) => b.y))
    const maxX = Math.max(...lineBoxes.map((b) => b.x + b.width))
    const maxY = Math.max(...lineBoxes.map((b) => b.y + b.height))
    const pad = 0.3
    const pxLeft = Math.max(0, Math.round(((minX - pad) / 100) * imgW))
    const pxTop = Math.max(0, Math.round(((minY - pad) / 100) * imgH))
    const pxRight = Math.min(imgW, Math.round(((maxX + pad) / 100) * imgW))
    const pxBottom = Math.min(imgH, Math.round(((maxY + pad) / 100) * imgH))
    const pxW = pxRight - pxLeft
    const pxH = pxBottom - pxTop
    if (pxW > 0 && pxH > 0) {
      const [r, g, b] = sampleLocalBg(pxLeft, pxTop, pxRight, pxBottom)
      composites.push({
        input: Buffer.from(`<svg width="${pxW}" height="${pxH}"><rect width="${pxW}" height="${pxH}" fill="rgb(${r},${g},${b})" /></svg>`),
        left: pxLeft, top: pxTop,
      })
    }
  })

  const erasedBuffer = await sharp(imageBuffer).composite(composites).png().toBuffer()
  await mkdir(cacheDir, { recursive: true })
  await writeFile(cachedPath, erasedBuffer)
  return erasedBuffer
}

// --- Compute safe text blocks for a page ---

async function computeTextBlocks(pageId: string, bookId: string, bookFilename: string, pageNumber: number): Promise<TextBlock[]> {
  const page = await prisma.page.findFirst({
    where: { bookId, pageNumber },
    include: { ocrResult: { include: { boxes: { orderBy: [{ lineIndex: 'asc' }, { wordIndex: 'asc' }] } } } },
  })

  const boxes = (page?.ocrResult?.boxes || []).filter((b) => !b.skipTranslation && b.y >= 4)
  if (boxes.length === 0) return []

  // Group into lines
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
  if (ocrLines.length === 0) return []

  // Group into blocks
  const GAP_THRESHOLD = 3
  const groups: (typeof ocrLines)[] = []
  let currentGroup = [ocrLines[0]]
  for (let i = 1; i < ocrLines.length; i++) {
    const prev = currentGroup[currentGroup.length - 1]
    if (ocrLines[i].y - (prev.y + prev.height) > GAP_THRESHOLD) {
      groups.push(currentGroup)
      currentGroup = [ocrLines[i]]
    } else {
      currentGroup.push(ocrLines[i])
    }
  }
  groups.push(currentGroup)

  const rawBlocks: TextBlock[] = groups.map((group) => {
    const minX = Math.min(...group.map((l) => l.x))
    const minY = Math.min(...group.map((l) => l.y))
    const maxX = Math.max(...group.map((l) => l.x + l.width))
    const maxY = Math.max(...group.map((l) => l.y + l.height))
    const hebrewCharCount = group.reduce((s, l) => s + l.charCount, 0)
    const avgLineHeightPct = group.reduce((s, l) => s + l.height, 0) / group.length
    return { x: minX, y: minY, width: maxX - minX, height: maxY - minY, hebrewCharCount, avgLineHeightPct }
  })

  // Pixel variance expansion (simplified — just expand vertically a bit)
  // Full pixel analysis is done in the text-blocks endpoint; here we use raw blocks
  // which are good enough for PDF rendering
  return rawBlocks
}

// --- MAIN EXPORT ---

export async function GET(
  request: Request,
  { params }: { params: { bookId: string } }
) {
  try {
    const { bookId } = params
    const url = new URL(request.url)
    const fromPage = url.searchParams.get('from') ? parseInt(url.searchParams.get('from')!) : null
    const toPage = url.searchParams.get('to') ? parseInt(url.searchParams.get('to')!) : null

    const book = await prisma.book.findUnique({
      where: { id: bookId },
      include: {
        pages: {
          include: { translation: true },
          orderBy: { pageNumber: 'asc' },
        },
      },
    })

    if (!book) {
      return NextResponse.json({ error: 'Book not found' }, { status: 404 })
    }

    let translatedPages = book.pages.filter(
      (p) => p.translation && p.translation.englishOutput
    )

    // Apply page range filter
    if (fromPage !== null) {
      translatedPages = translatedPages.filter((p) => p.pageNumber >= fromPage)
    }
    if (toPage !== null) {
      translatedPages = translatedPages.filter((p) => p.pageNumber <= toPage)
    }

    if (translatedPages.length === 0) {
      return NextResponse.json({ error: 'No translated pages in range' }, { status: 404 })
    }

    const pdfDoc = await PDFDocument.create()
    const timesRoman = await pdfDoc.embedFont(StandardFonts.TimesRoman)
    const timesRomanBold = await pdfDoc.embedFont(StandardFonts.TimesRomanBold)

    for (const page of translatedPages) {
      // Get the erased image
      const erasedBuffer = await getErasedImage(page.id, book.id, book.filename, page.pageNumber)

      // Get image dimensions
      const metadata = await sharp(erasedBuffer).metadata()
      const imgW = metadata.width || 1655
      const imgH = metadata.height || 2340

      // Convert to JPEG for smaller PDF size
      const jpegBuffer = await sharp(erasedBuffer).jpeg({ quality: 85 }).toBuffer()

      // Embed image in PDF
      const pdfImage = await pdfDoc.embedJpg(jpegBuffer)

      // Create page matching image aspect ratio, scaled to reasonable size
      const pdfPageWidth = 612 // US Letter width
      const pdfPageHeight = pdfPageWidth * (imgH / imgW)
      const pdfPage = pdfDoc.addPage([pdfPageWidth, pdfPageHeight])

      // Draw the erased page image as full background
      pdfPage.drawImage(pdfImage, {
        x: 0,
        y: 0,
        width: pdfPageWidth,
        height: pdfPageHeight,
      })

      // Get text blocks and draw English text
      const blocks = await computeTextBlocks(page.id, book.id, book.filename, page.pageNumber)
      const paragraphs = parseTranslation(page.translation!.englishOutput)
      const paraMap = assignParagraphsToBlocks(blocks, paragraphs)

      for (let bi = 0; bi < blocks.length; bi++) {
        const block = blocks[bi]
        const paras = paraMap.get(bi) || []
        if (paras.length === 0) continue

        // Convert block coords (percentage) to PDF coords
        // PDF origin is bottom-left, y increases upward
        const blockXPdf = (block.x / 100) * pdfPageWidth
        const blockYTopPdf = pdfPageHeight - (block.y / 100) * pdfPageHeight
        const blockWPdf = (block.width / 100) * pdfPageWidth
        const blockHPdf = (block.height / 100) * pdfPageHeight

        // Compute font size — binary search for largest that fits
        const allText = paras.map((p) => p.text).join(' ')
        const hebrewLinePx = block.avgLineHeightPct
          ? (block.avgLineHeightPct / 100) * pdfPageHeight * 0.75
          : 14
        const maxFont = Math.min(hebrewLinePx, 16)

        let lo = 4
        let hi = maxFont
        let bestSize = lo

        for (let iter = 0; iter < 12; iter++) {
          const mid = (lo + hi) / 2
          const lineH = mid * 1.3
          let totalH = 0

          for (let pi = 0; pi < paras.length; pi++) {
            const wrapped = wrapText(paras[pi].text, timesRoman, mid, blockWPdf)
            totalH += wrapped.length * lineH
            if (pi < paras.length - 1) totalH += mid * 0.4
          }

          if (totalH <= blockHPdf) {
            bestSize = mid
            lo = mid
          } else {
            hi = mid
          }
        }

        // Draw paragraphs
        let yPos = blockYTopPdf - bestSize // start below top edge
        for (let pi = 0; pi < paras.length; pi++) {
          const para = paras[pi]
          const font = para.isAllBold ? timesRomanBold : timesRoman
          const wrapped = wrapText(para.text, font, bestSize, blockWPdf)

          for (const line of wrapped) {
            if (yPos < blockYTopPdf - blockHPdf) break // don't overflow block
            pdfPage.drawText(line, {
              x: blockXPdf,
              y: yPos,
              size: bestSize,
              font,
              color: rgb(0.1, 0.08, 0.06),
            })
            yPos -= bestSize * 1.3
          }
          if (pi < paras.length - 1) yPos -= bestSize * 0.4
        }
      }
    }

    const pdfBytes = await pdfDoc.save()
    const pdfBuffer = Buffer.from(pdfBytes)

    const rangeStr = fromPage || toPage
      ? `_pages_${fromPage || 'start'}-${toPage || 'end'}`
      : ''
    const safeName = book.name.replace(/[^a-zA-Z0-9_-]/g, '_')
    const filename = `${safeName}_English${rangeStr}.pdf`

    return new NextResponse(pdfBuffer, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename="${filename}"`,
        'Cache-Control': 'no-cache',
      },
    })
  } catch (error) {
    console.error('Error generating PDF:', error)
    return NextResponse.json(
      { error: 'Failed to generate PDF' },
      { status: 500 }
    )
  }
}
