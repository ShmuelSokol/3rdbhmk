import { execFile } from 'child_process'
import { promises as fs } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { randomUUID } from 'crypto'

function exec(
  cmd: string,
  args: string[]
): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    execFile(cmd, args, { maxBuffer: 50 * 1024 * 1024 }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error(`${cmd} failed: ${stderr || error.message}`))
      } else {
        resolve({ stdout, stderr })
      }
    })
  })
}

/**
 * Extract a single page from a PDF as a PNG image buffer.
 * Requires `pdftoppm` (from poppler-utils) to be installed.
 */
export async function extractPageAsImage(
  pdfPath: string,
  pageNumber: number
): Promise<Buffer> {
  const tempDir = tmpdir()
  const outputPrefix = join(tempDir, `pdf-page-${randomUUID()}`)

  await exec('pdftoppm', [
    '-png',
    '-r', '200',
    '-f', String(pageNumber),
    '-l', String(pageNumber),
    '-singlefile',
    pdfPath,
    outputPrefix,
  ])

  const outputPath = `${outputPrefix}.png`

  try {
    const buffer = await fs.readFile(outputPath)
    return buffer
  } finally {
    // Clean up temp file
    await fs.unlink(outputPath).catch(() => {})
  }
}

/**
 * Get the total number of pages in a PDF.
 * Requires `pdfinfo` (from poppler-utils) to be installed.
 */
export async function getPageCount(pdfPath: string): Promise<number> {
  const { stdout } = await exec('pdfinfo', [pdfPath])

  const match = stdout.match(/Pages:\s+(\d+)/)
  if (!match) {
    throw new Error(`Could not determine page count from pdfinfo output`)
  }

  return parseInt(match[1], 10)
}
