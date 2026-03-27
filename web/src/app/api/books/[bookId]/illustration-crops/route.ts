import { NextResponse } from 'next/server'
import { readFile, writeFile } from 'fs/promises'
import path from 'path'

const CROPS_PATH = path.join(process.cwd(), 'public', 'illustration-crops.json')

export async function GET() {
  try {
    const raw = await readFile(CROPS_PATH, 'utf-8')
    const data = JSON.parse(raw)
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error reading illustration-crops.json:', error)
    return NextResponse.json({}, { status: 200 })
  }
}

export async function PUT(request: Request) {
  try {
    const body = await request.json()
    await writeFile(CROPS_PATH, JSON.stringify(body, null, 2), 'utf-8')
    // Also update the copy in src/lib if it exists
    const srcCopy = path.join(process.cwd(), 'src', 'lib', 'illustration-crops.json')
    try {
      await writeFile(srcCopy, JSON.stringify(body, null, 2), 'utf-8')
    } catch {
      // src/lib copy is optional
    }
    return NextResponse.json({ ok: true })
  } catch (error) {
    console.error('Error writing illustration-crops.json:', error)
    return NextResponse.json(
      { error: 'Failed to save crops' },
      { status: 500 }
    )
  }
}
