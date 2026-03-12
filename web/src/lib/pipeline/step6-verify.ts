import { prisma } from '@/lib/prisma'
import { getSupabase } from '@/lib/supabase'
import { updatePipelineStatus } from './shared'
import sharp from 'sharp'

/**
 * Step 6: Verification OCR — re-OCR the English fitted page,
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

  // Compress for Azure if needed
  let ocrBuffer: Buffer = fittedBuffer
  if (fittedBuffer.length > 3 * 1024 * 1024) {
    ocrBuffer = await sharp(fittedBuffer).jpeg({ quality: 85 }).toBuffer() as Buffer
  }

  // Run Azure OCR on the fitted English page (no locale for English)
  const endpoint = process.env["AZURE_DOC_INTELLIGENCE_ENDPOINT"]!
  const apiKey = process.env["AZURE_DOC_INTELLIGENCE_KEY"]!
  const analyzeUrl = `${endpoint}/documentintelligence/documentModels/prebuilt-read:analyze?api-version=2024-11-30`

  const postResponse = await fetch(analyzeUrl, {
    method: 'POST',
    headers: {
      'Ocp-Apim-Subscription-Key': apiKey,
      'Content-Type': 'application/octet-stream',
    },
    body: new Uint8Array(ocrBuffer),
  })

  if (!postResponse.ok) throw new Error(`Azure OCR failed: ${postResponse.status}`)

  const operationLocation = postResponse.headers.get('Operation-Location')
  if (!operationLocation) throw new Error('Missing Operation-Location')

  // Poll for results
  let result: { status: string; analyzeResult?: { content?: string } } | null = null
  for (let attempt = 0; attempt < 60; attempt++) {
    await new Promise((r) => setTimeout(r, 1000))
    const poll = await fetch(operationLocation, {
      headers: { 'Ocp-Apim-Subscription-Key': apiKey },
    })
    if (!poll.ok) throw new Error(`Poll failed: ${poll.status}`)
    result = await poll.json()
    if (result!.status === 'succeeded') break
    if (result!.status === 'failed') throw new Error('OCR failed')
  }

  if (!result || result.status !== 'succeeded') throw new Error('OCR timed out')

  const ocrText = result.analyzeResult?.content || ''
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
    ocrRawJson: result,
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
