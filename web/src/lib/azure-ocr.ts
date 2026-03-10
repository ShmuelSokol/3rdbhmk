export interface OcrWord {
  x: number
  y: number
  width: number
  height: number
  hebrewText: string
  confidence: number
  lineIndex: number
  wordIndex: number
}

interface AzureWord {
  content: string
  confidence: number
  polygon: number[]
}

interface AzureLine {
  content: string
  polygon: number[]
}

interface AzurePage {
  width: number
  height: number
  lines: AzureLine[]
  words: AzureWord[]
}

interface AzureAnalyzeResult {
  pages: AzurePage[]
}

interface AzureResponse {
  status: string
  analyzeResult?: AzureAnalyzeResult
}

function polygonToBbox(
  polygon: number[],
  pageWidth: number,
  pageHeight: number
): { x: number; y: number; width: number; height: number } {
  // polygon is [x1,y1, x2,y2, x3,y3, x4,y4] — four corners
  const xs: number[] = []
  const ys: number[] = []
  for (let i = 0; i < polygon.length; i += 2) {
    xs.push(polygon[i])
    ys.push(polygon[i + 1])
  }
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)

  return {
    x: (minX / pageWidth) * 100,
    y: (minY / pageHeight) * 100,
    width: ((maxX - minX) / pageWidth) * 100,
    height: ((maxY - minY) / pageHeight) * 100,
  }
}

function isPointInPolygon(
  px: number,
  py: number,
  polygon: number[]
): boolean {
  // Ray-casting algorithm
  const n = polygon.length / 2
  let inside = false
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const xi = polygon[i * 2],
      yi = polygon[i * 2 + 1]
    const xj = polygon[j * 2],
      yj = polygon[j * 2 + 1]
    if (yi > py !== yj > py && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) {
      inside = !inside
    }
  }
  return inside
}

function wordCenterInLine(word: AzureWord, line: AzureLine): boolean {
  if (!word.polygon || !line.polygon) return false
  const xs: number[] = []
  const ys: number[] = []
  for (let i = 0; i < word.polygon.length; i += 2) {
    xs.push(word.polygon[i])
    ys.push(word.polygon[i + 1])
  }
  const cx = (Math.min(...xs) + Math.max(...xs)) / 2
  const cy = (Math.min(...ys) + Math.max(...ys)) / 2
  return isPointInPolygon(cx, cy, line.polygon)
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function analyzePageImage(imageBuffer: Buffer): Promise<OcrWord[]> {
  const endpoint = process.env["AZURE_DOC_INTELLIGENCE_ENDPOINT"]!
  const apiKey = process.env["AZURE_DOC_INTELLIGENCE_KEY"]!

  const analyzeUrl = `${endpoint}/documentintelligence/documentModels/prebuilt-read:analyze?api-version=2024-11-30&locale=he`

  // POST the image to start analysis
  const postResponse = await fetch(analyzeUrl, {
    method: 'POST',
    headers: {
      'Ocp-Apim-Subscription-Key': apiKey,
      'Content-Type': 'application/octet-stream',
    },
    body: new Uint8Array(imageBuffer),
  })

  if (!postResponse.ok) {
    const errorText = await postResponse.text()
    throw new Error(
      `Azure OCR submit failed (${postResponse.status}): ${errorText}`
    )
  }

  const operationLocation = postResponse.headers.get('Operation-Location')
  if (!operationLocation) {
    throw new Error('Azure OCR response missing Operation-Location header')
  }

  // Poll for results
  let result: AzureResponse | null = null
  const maxAttempts = 60
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    await sleep(1000)

    const pollResponse = await fetch(operationLocation, {
      headers: {
        'Ocp-Apim-Subscription-Key': apiKey,
      },
    })

    if (!pollResponse.ok) {
      const errorText = await pollResponse.text()
      throw new Error(
        `Azure OCR poll failed (${pollResponse.status}): ${errorText}`
      )
    }

    result = (await pollResponse.json()) as AzureResponse

    if (result.status === 'succeeded') {
      break
    } else if (result.status === 'failed') {
      throw new Error('Azure OCR analysis failed')
    }
    // status is "running" — keep polling
  }

  if (!result || result.status !== 'succeeded' || !result.analyzeResult) {
    throw new Error('Azure OCR analysis timed out or returned no result')
  }

  const ocrWords: OcrWord[] = []

  for (const page of result.analyzeResult.pages) {
    const pageWidth = page.width
    const pageHeight = page.height
    const lines = page.lines || []
    const words = page.words || []

    // Build a map of word -> lineIndex by checking which line polygon contains each word center
    const wordLineMap = new Map<number, number>()
    for (let wi = 0; wi < words.length; wi++) {
      for (let li = 0; li < lines.length; li++) {
        if (wordCenterInLine(words[wi], lines[li])) {
          wordLineMap.set(wi, li)
          break
        }
      }
    }

    // Track word index within each line
    const lineWordCounters = new Map<number, number>()

    for (let wi = 0; wi < words.length; wi++) {
      const word = words[wi]
      const lineIndex = wordLineMap.get(wi) ?? -1
      const wordIndex = lineWordCounters.get(lineIndex) ?? 0
      lineWordCounters.set(lineIndex, wordIndex + 1)

      const bbox = polygonToBbox(word.polygon, pageWidth, pageHeight)

      ocrWords.push({
        x: bbox.x,
        y: bbox.y,
        width: bbox.width,
        height: bbox.height,
        hebrewText: word.content,
        confidence: word.confidence,
        lineIndex,
        wordIndex,
      })
    }
  }

  return ocrWords
}
