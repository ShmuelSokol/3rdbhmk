#!/usr/bin/env node
/**
 * Upload the full book PDF to Supabase and create DB records.
 * Usage: node scripts/upload-full-book.js
 */

const { PrismaClient } = require('@prisma/client')
const { createClient } = require('@supabase/supabase-js')
const { readFileSync } = require('fs')
const { execSync } = require('child_process')
const path = require('path')

const PDF_PATH = path.resolve(__dirname, '../../Binder2-2.pdf')
const BOOK_NAME = 'Lishchno Tidreshu (Full)'

async function main() {
  // Load env from .env.local
  const envContent = readFileSync(path.join(__dirname, '../.env.local'), 'utf-8')
  for (const line of envContent.split('\n')) {
    const match = line.match(/^([^#=]+)=(.*)$/)
    if (match) process.env[match[1].trim()] = match[2].trim()
  }

  const prisma = new PrismaClient()
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.SUPABASE_SERVICE_ROLE_KEY
  )

  // Get page count
  const pdfInfo = execSync(`pdfinfo "${PDF_PATH}"`).toString()
  const pageMatch = pdfInfo.match(/Pages:\s+(\d+)/)
  const totalPages = parseInt(pageMatch[1])
  console.log(`PDF: ${path.basename(PDF_PATH)} | ${totalPages} pages`)

  // Generate book ID
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
  let bookId = ''
  for (let i = 0; i < 25; i++) bookId += chars[Math.floor(Math.random() * chars.length)]

  const filename = path.basename(PDF_PATH)

  // Copy PDF to /tmp cache dir (too large for Supabase upload — 605MB)
  // The pipeline reads PDFs from /tmp/bhmk/{bookId}/{filename}
  const { mkdirSync, copyFileSync } = require('fs')
  const tmpDir = path.join('/tmp', 'bhmk', bookId)
  mkdirSync(tmpDir, { recursive: true })
  const tmpPath = path.join(tmpDir, filename)
  console.log(`Copying ${filename} to ${tmpPath}...`)
  copyFileSync(PDF_PATH, tmpPath)
  console.log('Copy complete!')

  // Also upload to Supabase in 50MB chunks for Railway deployment
  // Split PDF isn't needed — the pipeline extracts page images individually
  // and stores those in Supabase. We just need the PDF accessible locally.
  // On Railway, we'll need to download it — let's upload as chunks.
  const buffer = readFileSync(PDF_PATH)
  const CHUNK_SIZE = 45 * 1024 * 1024 // 45MB chunks
  const totalChunks = Math.ceil(buffer.length / CHUNK_SIZE)
  console.log(`Uploading ${totalChunks} chunks to Supabase...`)
  for (let i = 0; i < totalChunks; i++) {
    const chunk = buffer.subarray(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE)
    const chunkPath = `books/${bookId}/chunks/${filename}.part${i}`
    const { error: uploadError } = await supabase.storage
      .from('bhmk')
      .upload(chunkPath, chunk, {
        contentType: 'application/octet-stream',
        upsert: true,
      })
    if (uploadError) {
      console.error(`Chunk ${i} upload error:`, uploadError)
      process.exit(1)
    }
    console.log(`  Chunk ${i + 1}/${totalChunks} uploaded`)
  }
  console.log('All chunks uploaded!')

  // Create book and page records
  console.log(`Creating book record with ${totalPages} pages...`)
  const book = await prisma.book.create({
    data: {
      id: bookId,
      name: BOOK_NAME,
      filename,
      totalPages,
      pages: {
        create: Array.from({ length: totalPages }, (_, i) => ({
          pageNumber: i + 1,
          status: 'pending',
        })),
      },
    },
  })

  console.log(`Book created: ${book.id}`)
  console.log(`Name: ${book.name}`)
  console.log(`Total pages: ${totalPages}`)
  console.log(`\nTo run the pipeline:\n  Update BOOK_ID in scripts/run-pipeline.js to '${bookId}'`)
  console.log(`  Then: node scripts/run-pipeline.js`)

  await prisma.$disconnect()
}

main().catch(e => { console.error(e); process.exit(1) })
