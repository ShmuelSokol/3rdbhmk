'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'

interface Region {
  id: string
  regionIndex: number
  regionType: string
  origX: number
  origY: number
  origWidth: number
  origHeight: number
  expandedX: number | null
  expandedY: number | null
  expandedWidth: number | null
  expandedHeight: number | null
  manualX: number | null
  manualY: number | null
  manualWidth: number | null
  manualHeight: number | null
  fittedFontSize: number | null
  fittedText: string | null
  hebrewText: string | null
}

interface PipelineStatus {
  id: string
  pageNumber: number
  pipelineStatus: string
  lockedAt: string | null
  ocrBoxCount: number
  regionCount: number
  regions: Region[]
  hasErasedImage: boolean
  hasFittedPage: boolean
  verification: {
    passRate: number
    passed: boolean
    missingCount: number
    extraCount: number
  } | null
}

const STEPS = [
  { num: 1, key: 'step1_ocr', label: 'OCR', desc: 'Extract words with coordinates' },
  { num: 2, key: 'step2_regions', label: 'Regions', desc: 'Detect content blocks' },
  { num: 3, key: 'step3_erased', label: 'Erase', desc: 'Remove Hebrew text' },
  { num: 4, key: 'step4_expanded', label: 'Expand', desc: 'Expand region boundaries' },
  { num: 5, key: 'step5_fitted', label: 'Fit Text', desc: 'Render English text' },
  { num: 6, key: 'step6_verified', label: 'Verify', desc: 'OCR verification check' },
]

const STEP_ORDER = ['pending', 'step1_ocr', 'step2_regions', 'step3_erased', 'step4_expanded', 'step5_fitted', 'step6_verified', 'locked']

function stepIdx(s: string) { return STEP_ORDER.indexOf(s) }

export default function PipelinePageViewer() {
  const params = useParams()
  const router = useRouter()
  const bookId = params.bookId as string
  const pageNumber = parseInt(params.pageNumber as string)

  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [runningStep, setRunningStep] = useState<number | null>(null)
  const [activeView, setActiveView] = useState<'original' | 'erased' | 'fitted' | 'regions'>('original')
  const [editingRegion, setEditingRegion] = useState<string | null>(null)
  const imageRef = useRef<HTMLImageElement>(null)

  const fetchStatus = useCallback(async () => {
    // First get the pageId from book pages
    const bookRes = await fetch(`/api/books/${bookId}/pipeline`)
    const bookData = await bookRes.json()
    const pageInfo = bookData.pages?.find((p: { pageNumber: number }) => p.pageNumber === pageNumber)
    if (!pageInfo) return

    const res = await fetch(`/api/pages/${pageInfo.id}/pipeline`)
    const data = await res.json()
    setStatus(data)
    setLoading(false)
  }, [bookId, pageNumber])

  useEffect(() => { fetchStatus() }, [fetchStatus])

  const runStep = async (stepNum: number) => {
    if (!status) return
    setRunningStep(stepNum)
    try {
      const res = await fetch(`/api/pages/${status.id}/pipeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step: stepNum }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error)
      await fetchStatus()
    } catch (err) {
      alert(`Step ${stepNum} failed: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setRunningStep(null)
    }
  }

  const runAll = async () => {
    if (!status) return
    setRunningStep(-1)
    try {
      const res = await fetch(`/api/pages/${status.id}/pipeline/run-all`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error)
      await fetchStatus()
    } catch (err) {
      alert(`Pipeline failed: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setRunningStep(null)
    }
  }

  const toggleLock = async () => {
    if (!status) return
    const isLocked = status.pipelineStatus === 'locked'
    const res = await fetch(`/api/pages/${status.id}/pipeline/lock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lock: !isLocked }),
    })
    if (res.ok) await fetchStatus()
  }

  const updateRegion = async (regionId: string, coords: { manualX: number; manualY: number; manualWidth: number; manualHeight: number }) => {
    if (!status) return
    await fetch(`/api/pages/${status.id}/pipeline/regions`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ regionId, ...coords }),
    })
    await fetchStatus()
    setEditingRegion(null)
  }

  if (loading) return <div className="p-8 text-center">Loading...</div>
  if (!status) return <div className="p-8 text-center text-red-500">Page not found</div>

  const currentStepIdx = stepIdx(status.pipelineStatus)
  const isLocked = status.pipelineStatus === 'locked'

  const getImageSrc = () => {
    if (activeView === 'erased' && status.hasErasedImage) {
      return `/api/pages/${status.id}/pipeline/image?type=erased`
    }
    if (activeView === 'fitted' && status.hasFittedPage) {
      return `/api/pages/${status.id}/pipeline/image?type=fitted`
    }
    return `/api/pages/${status.id}/image`
  }

  const showRegionOverlay = activeView === 'regions' || activeView === 'original'

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Top bar */}
      <div className="bg-gray-800 p-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push(`/book/${bookId}/pipeline`)}
            className="px-3 py-1 bg-gray-700 rounded hover:bg-gray-600"
          >
            Back
          </button>
          <h1 className="text-lg font-bold">
            Page {pageNumber}
            <span className="ml-2 text-sm font-normal text-gray-400">
              {status.pipelineStatus}
            </span>
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => router.push(`/book/${bookId}/pipeline/${pageNumber - 1}`)}
            disabled={pageNumber <= 1}
            className="px-3 py-1 bg-gray-700 rounded hover:bg-gray-600 disabled:opacity-30"
          >
            Prev
          </button>
          <button
            onClick={() => router.push(`/book/${bookId}/pipeline/${pageNumber + 1}`)}
            className="px-3 py-1 bg-gray-700 rounded hover:bg-gray-600"
          >
            Next
          </button>
        </div>
      </div>

      <div className="flex">
        {/* Left sidebar — steps */}
        <div className="w-72 bg-gray-800 p-4 min-h-[calc(100vh-64px)] space-y-2">
          {/* Step buttons */}
          {STEPS.map((step) => {
            const completed = stepIdx(step.key) <= currentStepIdx
            const isCurrent = step.key === status.pipelineStatus
            const canRun = !isLocked && (stepIdx(step.key) === currentStepIdx + 1 || step.key === 'step1_ocr')

            return (
              <div
                key={step.num}
                className={`rounded-lg p-3 ${
                  isCurrent ? 'bg-blue-600' : completed ? 'bg-green-800' : 'bg-gray-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-bold">
                      {step.num}. {step.label}
                    </span>
                    {completed && <span className="ml-2 text-green-300 text-xs">Done</span>}
                  </div>
                  {(canRun || (step.num === 1 && !isLocked)) && (
                    <button
                      onClick={() => runStep(step.num)}
                      disabled={runningStep !== null}
                      className="px-2 py-1 text-xs bg-blue-500 rounded hover:bg-blue-400 disabled:opacity-50"
                    >
                      {runningStep === step.num ? 'Running...' : completed ? 'Rerun' : 'Run'}
                    </button>
                  )}
                </div>
                <p className="text-xs text-gray-300 mt-1">{step.desc}</p>
                {step.num === 1 && status.ocrBoxCount > 0 && (
                  <p className="text-xs text-gray-400 mt-1">{status.ocrBoxCount} words detected</p>
                )}
                {step.num === 2 && status.regionCount > 0 && (
                  <p className="text-xs text-gray-400 mt-1">{status.regionCount} regions found</p>
                )}
                {step.num === 6 && status.verification && (
                  <p className={`text-xs mt-1 ${status.verification.passed ? 'text-green-400' : 'text-red-400'}`}>
                    {(status.verification.passRate * 100).toFixed(0)}% verified
                    {status.verification.missingCount > 0 && ` (${status.verification.missingCount} missing)`}
                  </p>
                )}
              </div>
            )
          })}

          {/* Run All button */}
          <button
            onClick={runAll}
            disabled={runningStep !== null || isLocked}
            className="w-full py-3 bg-purple-600 rounded-lg hover:bg-purple-500 disabled:opacity-50 font-bold"
          >
            {runningStep === -1 ? 'Running All...' : 'Run All Steps'}
          </button>

          {/* Lock button */}
          {(currentStepIdx >= stepIdx('step6_verified') || isLocked) && (
            <button
              onClick={toggleLock}
              className={`w-full py-3 rounded-lg font-bold ${
                isLocked
                  ? 'bg-red-600 hover:bg-red-500'
                  : 'bg-green-600 hover:bg-green-500'
              }`}
            >
              {isLocked ? 'Unlock Page' : 'Lock for Print'}
            </button>
          )}
        </div>

        {/* Main content — image viewer */}
        <div className="flex-1 p-4">
          {/* View tabs */}
          <div className="flex gap-2 mb-4">
            {[
              { key: 'original' as const, label: 'Original' },
              { key: 'regions' as const, label: 'Regions', disabled: status.regionCount === 0 },
              { key: 'erased' as const, label: 'Erased', disabled: !status.hasErasedImage },
              { key: 'fitted' as const, label: 'Fitted', disabled: !status.hasFittedPage },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveView(tab.key)}
                disabled={tab.disabled}
                className={`px-4 py-2 rounded ${
                  activeView === tab.key
                    ? 'bg-blue-600'
                    : 'bg-gray-700 hover:bg-gray-600'
                } disabled:opacity-30 disabled:cursor-not-allowed`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Image + region overlay */}
          <div className="relative inline-block">
            <img
              ref={imageRef}
              src={getImageSrc()}
              alt={`Page ${pageNumber}`}
              className="max-h-[80vh] w-auto"
            />

            {/* Region overlays */}
            {showRegionOverlay && status.regions.map((region) => {
              const useExpanded = activeView === 'regions' && region.expandedX != null
              const x = region.manualX ?? (useExpanded ? region.expandedX! : region.origX)
              const y = region.manualY ?? (useExpanded ? region.expandedY! : region.origY)
              const w = region.manualWidth ?? (useExpanded ? region.expandedWidth! : region.origWidth)
              const h = region.manualHeight ?? (useExpanded ? region.expandedHeight! : region.origHeight)

              const colors: Record<string, string> = {
                body: 'border-blue-400 bg-blue-400/10',
                header: 'border-yellow-400 bg-yellow-400/10',
                table: 'border-purple-400 bg-purple-400/10',
                footer: 'border-gray-400 bg-gray-400/10',
                image: 'border-red-400 bg-red-400/10',
              }
              const colorClass = colors[region.regionType] || colors.body
              const isEditing = editingRegion === region.id

              return (
                <div
                  key={region.id}
                  className={`absolute border-2 ${colorClass} ${isEditing ? 'border-dashed' : ''} cursor-pointer`}
                  style={{
                    left: `${x}%`,
                    top: `${y}%`,
                    width: `${w}%`,
                    height: `${h}%`,
                  }}
                  onClick={() => {
                    if (activeView === 'regions') {
                      setEditingRegion(isEditing ? null : region.id)
                    }
                  }}
                >
                  <span className="absolute -top-5 left-0 text-xs bg-black/70 px-1 rounded">
                    {region.regionIndex}: {region.regionType}
                  </span>
                </div>
              )
            })}
          </div>

          {/* Region editor panel */}
          {editingRegion && activeView === 'regions' && (() => {
            const region = status.regions.find((r) => r.id === editingRegion)
            if (!region) return null
            const currentX = region.manualX ?? region.expandedX ?? region.origX
            const currentY = region.manualY ?? region.expandedY ?? region.origY
            const currentW = region.manualWidth ?? region.expandedWidth ?? region.origWidth
            const currentH = region.manualHeight ?? region.expandedHeight ?? region.origHeight

            return (
              <div className="mt-4 bg-gray-800 rounded-lg p-4 max-w-lg">
                <h3 className="font-bold mb-3">
                  Edit Region {region.regionIndex} ({region.regionType})
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: 'X (%)', key: 'manualX', val: currentX },
                    { label: 'Y (%)', key: 'manualY', val: currentY },
                    { label: 'Width (%)', key: 'manualWidth', val: currentW },
                    { label: 'Height (%)', key: 'manualHeight', val: currentH },
                  ].map(({ label, key, val }) => (
                    <div key={key}>
                      <label className="text-xs text-gray-400">{label}</label>
                      <input
                        type="number"
                        step="0.5"
                        defaultValue={val.toFixed(1)}
                        className="w-full bg-gray-700 rounded px-2 py-1 text-sm"
                        id={`region-${key}`}
                      />
                    </div>
                  ))}
                </div>
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => {
                      const getVal = (id: string) =>
                        parseFloat((document.getElementById(id) as HTMLInputElement).value)
                      updateRegion(region.id, {
                        manualX: getVal('region-manualX'),
                        manualY: getVal('region-manualY'),
                        manualWidth: getVal('region-manualWidth'),
                        manualHeight: getVal('region-manualHeight'),
                      })
                    }}
                    className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-500"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => {
                      updateRegion(region.id, {
                        manualX: region.origX,
                        manualY: region.origY,
                        manualWidth: region.origWidth,
                        manualHeight: region.origHeight,
                      })
                    }}
                    className="px-4 py-2 bg-gray-600 rounded hover:bg-gray-500"
                  >
                    Reset to Original
                  </button>
                  <button
                    onClick={() => setEditingRegion(null)}
                    className="px-4 py-2 bg-gray-700 rounded hover:bg-gray-600"
                  >
                    Cancel
                  </button>
                </div>
                {region.hebrewText && (
                  <div className="mt-3 text-xs text-gray-400 max-h-20 overflow-auto" dir="rtl">
                    {region.hebrewText}
                  </div>
                )}
                {region.fittedText && (
                  <div className="mt-2 text-xs text-gray-300 max-h-20 overflow-auto">
                    {region.fittedText}
                  </div>
                )}
              </div>
            )
          })()}
        </div>
      </div>
    </div>
  )
}
