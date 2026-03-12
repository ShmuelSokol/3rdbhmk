import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { updatePipelineStatus } from './shared'
import { execFile } from 'child_process'
import { writeFile, mkdir, unlink } from 'fs/promises'
import path from 'path'
import { randomUUID } from 'crypto'
import { tmpdir } from 'os'

function exec(cmd: string, args: string[]): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    execFile(cmd, args, { maxBuffer: 10 * 1024 * 1024 }, (error, stdout, stderr) => {
      if (error) reject(new Error(`${cmd} failed: ${stderr || error.message}`))
      else resolve({ stdout, stderr })
    })
  })
}

/**
 * Step 6: Verification OCR — re-OCR the English fitted page using Tesseract (local, free),
 * compare all words, mark complete when verified.
 */
export async function runStep6(pageId: string) {
  // Get the fitted page image from Supabase
  const fittedRecord = await prisma.fittedPage.findUnique({ where: { pageId } })
  if (!fittedRecord) throw new Error('Fitted page not found (step 5 required)')

  const supabase = getSupabase()
  const { data, error } = await supabase.storage
    .from('bhmk')
    .download(fittedRecord.storagePath)
  if (error || !data) throw new Error('Failed to download fitted page image')

  const fittedBuffer = Buffer.from(await data.arrayBuffer())

  // Write to temp file for Tesseract
  const tmpPath = path.join(tmpdir(), `verify-${randomUUID()}.png`)
  await writeFile(tmpPath, fittedBuffer)

  let ocrText = ''
  try {
    // Run Tesseract locally — fast, free, no API limits
    const { stdout } = await exec('tesseract', [tmpPath, 'stdout', '-l', 'eng', '--psm', '6'])
    ocrText = stdout
  } finally {
    await unlink(tmpPath).catch(() => {})
  }

  const foundWords = ocrText
    .replace(/[^a-zA-Z\s]/g, '')
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)

  // Get expected words from all regions' fitted text
  const regions = await prisma.contentRegion.findMany({
    where: { pageId },
    orderBy: { regionIndex: 'asc' },
  })

  const expectedWords = regions
    .map((r) => r.fittedText || '')
    .join(' ')
    .replace(/\*\*/g, '') // strip bold markers
    .replace(/[^a-zA-Z\s]/g, '')
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)

  // Compare: find missing and extra words
  const expectedSet = new Map<string, number>()
  for (const w of expectedWords) {
    expectedSet.set(w, (expectedSet.get(w) || 0) + 1)
  }

  const foundSet = new Map<string, number>()
  for (const w of foundWords) {
    foundSet.set(w, (foundSet.get(w) || 0) + 1)
  }

  const missing: string[] = []
  expectedSet.forEach((count, word) => {
    const foundCount = foundSet.get(word) || 0
    if (foundCount < count) {
      for (let i = 0; i < count - foundCount; i++) {
        missing.push(word)
      }
    }
  })

  const extra: string[] = []
  foundSet.forEach((count, word) => {
    const expectedCount = expectedSet.get(word) || 0
    if (count > expectedCount) {
      for (let i = 0; i < count - expectedCount; i++) {
        extra.push(word)
      }
    }
  })

  // Pass rate: percentage of expected words found
  const passRate = expectedWords.length > 0
    ? Math.max(0, 1 - (missing.length / expectedWords.length))
    : 1
  const passed = passRate >= 0.85 // 85% threshold

  // Upsert verification record
  const existing = await prisma.verificationOcr.findUnique({ where: { pageId } })
  const verData = {
    expectedWords,
    foundWords,
    missingWords: missing,
    extraWords: extra,
    passRate,
    passed,
    ocrRawJson: { engine: 'tesseract', text: ocrText },
  }

  if (existing) {
    await prisma.verificationOcr.update({
      where: { pageId },
      data: verData,
    })
  } else {
    await prisma.verificationOcr.create({
      data: { pageId, ...verData },
    })
  }

  await updatePipelineStatus(pageId, 'step6_verified')

  return {
    passRate,
    passed,
    expectedCount: expectedWords.length,
    foundCount: foundWords.length,
    missingCount: missing.length,
    extraCount: extra.length,
  }
}
