import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { getPageCount } from '@/lib/pdf-utils'
import { writeFile, mkdir } from 'fs/promises'
import path from 'path'

export async function GET() {
  try {
    const books = await prisma.book.findMany({
      orderBy: { createdAt: 'desc' },
      include: {
        _count: { select: { pages: true } },
      },
    })
    return NextResponse.json(books)
  } catch (error) {
    console.error('Error listing books:', error)
    return NextResponse.json(
      { error: 'Failed to list books' },
      { status: 500 }
    )
  }
}

export async function POST(request: Request) {
  try {
    const formData = await request.formData()
    const file = formData.get('file') as File | null
    const name = formData.get('name') as string | null

    if (!file) {
      return NextResponse.json({ error: 'No file provided' }, { status: 400 })
    }
    if (!name) {
      return NextResponse.json({ error: 'No name provided' }, { status: 400 })
    }

    const arrayBuffer = await file.arrayBuffer()
    const buffer = Buffer.from(arrayBuffer)

    // Create a temporary book ID for the storage path
    const bookId = generateId()

    // Save PDF to /tmp so we can count pages
    const tmpDir = path.join('/tmp', 'bhmk', bookId)
    await mkdir(tmpDir, { recursive: true })
    const tmpPath = path.join(tmpDir, file.name)
    await writeFile(tmpPath, buffer)

    // Get page count
    const totalPages = await getPageCount(tmpPath)

    // Upload to Supabase storage
    const supabase = getSupabase()
    const storagePath = `books/${bookId}/${file.name}`
    const { error: uploadError } = await supabase.storage
      .from('bhmk')
      .upload(storagePath, buffer, {
        contentType: 'application/pdf',
        upsert: true,
      })

    if (uploadError) {
      console.error('Supabase upload error:', uploadError)
      return NextResponse.json(
        { error: 'Failed to upload file' },
        { status: 500 }
      )
    }

    // Create Book and Page records in a transaction
    const book = await prisma.book.create({
      data: {
        id: bookId,
        name,
        filename: file.name,
        totalPages,
        pages: {
          create: Array.from({ length: totalPages }, (_, i) => ({
            pageNumber: i + 1,
            status: 'pending',
          })),
        },
      },
      include: {
        pages: {
          orderBy: { pageNumber: 'asc' },
        },
      },
    })

    return NextResponse.json(book, { status: 201 })
  } catch (error) {
    console.error('Error creating book:', error)
    return NextResponse.json(
      { error: 'Failed to create book' },
      { status: 500 }
    )
  }
}

function generateId(): string {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < 25; i++) {
    result += chars[Math.floor(Math.random() * chars.length)]
  }
  return result
}
