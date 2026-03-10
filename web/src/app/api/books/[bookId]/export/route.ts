import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib'

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

const hebrewToLatin: Record<string, string> = {
  'א': 'A', 'ב': 'B', 'ג': 'C', 'ד': 'D', 'ה': 'E', 'ו': 'F',
  'ז': 'G', 'ח': 'H', 'ט': 'I', 'י': 'J', 'כ': 'K', 'ל': 'L',
  'מ': 'M', 'נ': 'N', 'ס': 'O', 'ע': 'P', 'פ': 'Q', 'צ': 'R',
  'ק': 'S', 'ר': 'T', 'ש': 'U', 'ת': 'V',
}

function sanitizeForPdf(text: string): string {
  return text.replace(/[\u0590-\u05FF]/g, (ch) => hebrewToLatin[ch] || '')
             .replace(/[^\x00-\x7F]/g, '')
}

export async function GET(
  request: Request,
  { params }: { params: { bookId: string } }
) {
  try {
    const { bookId } = params

    const book = await prisma.book.findUnique({
      where: { id: bookId },
      include: {
        pages: {
          include: {
            translation: true,
          },
          orderBy: { pageNumber: 'asc' },
        },
      },
    })

    if (!book) {
      return NextResponse.json({ error: 'Book not found' }, { status: 404 })
    }

    const translatedPages = book.pages.filter(
      (p) => p.translation && p.translation.englishOutput
    )

    if (translatedPages.length === 0) {
      return NextResponse.json(
        { error: 'No translated pages found' },
        { status: 404 }
      )
    }

    const pdfDoc = await PDFDocument.create()
    const timesRoman = await pdfDoc.embedFont(StandardFonts.TimesRoman)
    const timesRomanBold = await pdfDoc.embedFont(StandardFonts.TimesRomanBold)
    const timesRomanItalic = await pdfDoc.embedFont(StandardFonts.TimesRomanItalic)

    const PAGE_WIDTH = 612 // US Letter
    const PAGE_HEIGHT = 792
    const MARGIN = 72 // 1 inch
    const MAX_TEXT_WIDTH = PAGE_WIDTH - 2 * MARGIN
    const BODY_FONT_SIZE = 12
    const LINE_HEIGHT = BODY_FONT_SIZE * 1.6
    const HEADER_FONT_SIZE = 24
    const SUBTITLE_FONT_SIZE = 14
    const PAGE_HEADER_FONT_SIZE = 16

    // --- Title Page ---
    const titlePage = pdfDoc.addPage([PAGE_WIDTH, PAGE_HEIGHT])
    const titleText = 'Lishchno Tidreshu'
    const titleWidth = timesRomanBold.widthOfTextAtSize(titleText, HEADER_FONT_SIZE)
    titlePage.drawText(titleText, {
      x: (PAGE_WIDTH - titleWidth) / 2,
      y: PAGE_HEIGHT - 200,
      size: HEADER_FONT_SIZE,
      font: timesRomanBold,
      color: rgb(0.1, 0.1, 0.1),
    })

    const subtitleText = 'English Translation'
    const subtitleWidth = timesRomanItalic.widthOfTextAtSize(subtitleText, SUBTITLE_FONT_SIZE)
    titlePage.drawText(subtitleText, {
      x: (PAGE_WIDTH - subtitleWidth) / 2,
      y: PAGE_HEIGHT - 235,
      size: SUBTITLE_FONT_SIZE,
      font: timesRomanItalic,
      color: rgb(0.3, 0.3, 0.3),
    })

    const safePdfName = sanitizeForPdf(book.name)
    const bookNameWidth = timesRoman.widthOfTextAtSize(safePdfName, SUBTITLE_FONT_SIZE)
    titlePage.drawText(safePdfName, {
      x: (PAGE_WIDTH - bookNameWidth) / 2,
      y: PAGE_HEIGHT - 270,
      size: SUBTITLE_FONT_SIZE,
      font: timesRoman,
      color: rgb(0.3, 0.3, 0.3),
    })

    const countText = `${translatedPages.length} translated pages`
    const countWidth = timesRoman.widthOfTextAtSize(countText, 11)
    titlePage.drawText(countText, {
      x: (PAGE_WIDTH - countWidth) / 2,
      y: PAGE_HEIGHT - 310,
      size: 11,
      font: timesRoman,
      color: rgb(0.5, 0.5, 0.5),
    })

    // --- Content Pages ---
    for (const page of translatedPages) {
      const translation = page.translation!
      const englishText = sanitizeForPdf(translation.englishOutput)

      // Split text into paragraphs on newlines, then wrap each paragraph
      const paragraphs = englishText.split(/\n/)
      const allLines: Array<{ text: string; isFirstOfParagraph: boolean }> = []

      for (let pi = 0; pi < paragraphs.length; pi++) {
        const para = paragraphs[pi].trim()
        if (para === '') {
          // Empty line = paragraph break
          allLines.push({ text: '', isFirstOfParagraph: false })
          continue
        }
        const wrapped = wrapText(para, timesRoman, BODY_FONT_SIZE, MAX_TEXT_WIDTH)
        for (let li = 0; li < wrapped.length; li++) {
          allLines.push({
            text: wrapped[li],
            isFirstOfParagraph: li === 0 && pi > 0,
          })
        }
      }

      let currentPdfPage = pdfDoc.addPage([PAGE_WIDTH, PAGE_HEIGHT])
      let yPos = PAGE_HEIGHT - MARGIN

      // Page header
      const headerText = `Page ${page.pageNumber}`
      currentPdfPage.drawText(headerText, {
        x: MARGIN,
        y: yPos,
        size: PAGE_HEADER_FONT_SIZE,
        font: timesRomanBold,
        color: rgb(0.15, 0.15, 0.15),
      })
      yPos -= PAGE_HEADER_FONT_SIZE + 8

      // Separator line
      currentPdfPage.drawLine({
        start: { x: MARGIN, y: yPos },
        end: { x: PAGE_WIDTH - MARGIN, y: yPos },
        thickness: 0.5,
        color: rgb(0.7, 0.7, 0.7),
      })
      yPos -= 20

      // Draw each line of body text
      for (const line of allLines) {
        if (line.text === '') {
          // Paragraph break - add extra spacing
          yPos -= LINE_HEIGHT * 0.5
          continue
        }

        // Check if we need a new PDF page (ran out of vertical space)
        if (yPos < MARGIN + LINE_HEIGHT) {
          currentPdfPage = pdfDoc.addPage([PAGE_WIDTH, PAGE_HEIGHT])
          yPos = PAGE_HEIGHT - MARGIN

          // Continuation header
          const contHeader = `Page ${page.pageNumber} (continued)`
          currentPdfPage.drawText(contHeader, {
            x: MARGIN,
            y: yPos,
            size: 11,
            font: timesRomanItalic,
            color: rgb(0.5, 0.5, 0.5),
          })
          yPos -= 11 + 15
        }

        // Extra spacing before new paragraphs
        if (line.isFirstOfParagraph) {
          yPos -= LINE_HEIGHT * 0.3
        }

        currentPdfPage.drawText(line.text, {
          x: MARGIN,
          y: yPos,
          size: BODY_FONT_SIZE,
          font: timesRoman,
          color: rgb(0.1, 0.1, 0.1),
        })

        yPos -= LINE_HEIGHT
      }
    }

    const pdfBytes = await pdfDoc.save()
    const pdfBuffer = Buffer.from(pdfBytes)

    const safeName = book.name.replace(/[^a-zA-Z0-9_-]/g, '_')
    const filename = `${safeName}_English_Translation.pdf`

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
