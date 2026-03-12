'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'

interface PageStatus {
  id: string
  pageNumber: number
  pipelineStatus: string
  lockedAt: string | null
  status: string
}

interface PipelineOverview {
  id: string
  name: string
  totalPages: number
  stepCounts: Record<string, number>
  pages: PageStatus[]
}

const STEP_LABELS: Record<string, string> = {
  pending: 'Pending',
  step1_ocr: 'OCR Done',
  step2_regions: 'Regions',
  step3_erased: 'Erased',
  step4_expanded: 'Expanded',
  step5_fitted: 'Fitted',
  step6_verified: 'Verified',
  locked: 'Locked',
}

const STEP_COLORS: Record<string, string> = {
  pending: 'bg-gray-200 text-gray-700',
  step1_ocr: 'bg-blue-200 text-blue-800',
  step2_regions: 'bg-indigo-200 text-indigo-800',
  step3_erased: 'bg-purple-200 text-purple-800',
  step4_expanded: 'bg-yellow-200 text-yellow-800',
  step5_fitted: 'bg-orange-200 text-orange-800',
  step6_verified: 'bg-green-200 text-green-800',
  locked: 'bg-green-500 text-white',
}

export default function PipelineDashboard() {
  const params = useParams()
  const router = useRouter()
  const bookId = params.bookId as string
  const [data, setData] = useState<PipelineOverview | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`/api/books/${bookId}/pipeline`)
      .then((r) => r.json())
      .then(setData)
      .finally(() => setLoading(false))
  }, [bookId])

  if (loading) return <div className="p-8 text-center">Loading pipeline...</div>
  if (!data) return <div className="p-8 text-center text-red-500">Failed to load</div>

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">{data.name} — Pipeline</h1>
            <p className="text-gray-500">{data.totalPages} pages</p>
          </div>
          <Link
            href={`/book/${bookId}`}
            className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
          >
            Back to Book
          </Link>
        </div>

        {/* Step counts summary */}
        <div className="grid grid-cols-4 md:grid-cols-8 gap-2 mb-8">
          {Object.entries(STEP_LABELS).map(([key, label]) => (
            <div key={key} className={`rounded-lg p-3 text-center ${STEP_COLORS[key]}`}>
              <div className="text-2xl font-bold">{data.stepCounts[key] || 0}</div>
              <div className="text-xs">{label}</div>
            </div>
          ))}
        </div>

        {/* Page grid */}
        <div className="grid grid-cols-5 sm:grid-cols-8 md:grid-cols-10 lg:grid-cols-12 gap-2">
          {data.pages.map((page) => (
            <button
              key={page.id}
              onClick={() => router.push(`/book/${bookId}/pipeline/${page.pageNumber}`)}
              className={`rounded-lg p-2 text-center cursor-pointer hover:ring-2 hover:ring-blue-400 transition-all ${STEP_COLORS[page.pipelineStatus] || 'bg-gray-100'}`}
            >
              <div className="text-sm font-bold">{page.pageNumber}</div>
              <div className="text-[10px]">{STEP_LABELS[page.pipelineStatus] || page.pipelineStatus}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
