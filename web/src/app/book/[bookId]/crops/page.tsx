'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';

// ─── Types ──────────────────────────────────────────────────────────────────

interface CropRect {
  topPct: number;
  leftPct: number;
  widthPct: number;
  heightPct: number;
}

type CropsData = Record<string, CropRect[]>;

type DragMode =
  | null
  | 'move'
  | 'resize-nw'
  | 'resize-ne'
  | 'resize-sw'
  | 'resize-se'
  | 'resize-n'
  | 'resize-s'
  | 'resize-e'
  | 'resize-w';

const MIN_PAGE = 71;
const MAX_PAGE = 367;

// ─── Main Component ─────────────────────────────────────────────────────────

export default function CropsEditorPage() {
  const router = useRouter();
  const params = useParams();
  const bookId = params.bookId as string;

  // ─── State ────────────────────────────────────────────────────────────────

  const [cropsData, setCropsData] = useState<CropsData>({});
  const [currentPage, setCurrentPage] = useState(MIN_PAGE);
  const [pageInput, setPageInput] = useState(String(MIN_PAGE));
  const [selectedCropIdx, setSelectedCropIdx] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saved' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);
  const [imageError, setImageError] = useState(false);
  const [dirty, setDirty] = useState(false);

  // Drag/resize state
  const [dragMode, setDragMode] = useState<DragMode>(null);
  const [dragCropIdx, setDragCropIdx] = useState<number | null>(null);
  const [dragStartCoords, setDragStartCoords] = useState<{ x: number; y: number } | null>(null);
  const [dragOrigCrop, setDragOrigCrop] = useState<CropRect | null>(null);
  const [localOverrides, setLocalOverrides] = useState<Record<number, CropRect>>({});

  const imageContainerRef = useRef<HTMLDivElement>(null);
  const previewCanvasRefs = useRef<Record<number, HTMLCanvasElement | null>>({});
  const sourceImageRef = useRef<HTMLImageElement | null>(null);

  // ─── Data Loading ─────────────────────────────────────────────────────────

  const fetchCrops = useCallback(async () => {
    try {
      const res = await fetch(`/api/books/${bookId}/illustration-crops`);
      if (!res.ok) throw new Error('Failed to fetch crops');
      const data: CropsData = await res.json();
      setCropsData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load crops');
    } finally {
      setLoading(false);
    }
  }, [bookId]);

  useEffect(() => {
    fetchCrops();
  }, [fetchCrops]);

  // ─── Current page crops (with local overrides applied) ────────────────────

  const pageKey = String(currentPage);
  const rawCrops = cropsData[pageKey] || [];
  const crops: CropRect[] = rawCrops.map((c, i) => localOverrides[i] ?? c);

  // ─── Save ─────────────────────────────────────────────────────────────────

  const handleSave = async () => {
    setSaving(true);
    setSaveStatus('idle');
    try {
      const res = await fetch(`/api/books/${bookId}/illustration-crops`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cropsData),
      });
      if (!res.ok) throw new Error('Failed to save');
      setSaveStatus('saved');
      setDirty(false);
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (err) {
      setSaveStatus('error');
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  // ─── Crop CRUD ────────────────────────────────────────────────────────────

  const updateCropsForPage = (newCrops: CropRect[]) => {
    setCropsData((prev) => {
      const next = { ...prev };
      if (newCrops.length === 0) {
        delete next[pageKey];
      } else {
        next[pageKey] = newCrops;
      }
      return next;
    });
    setLocalOverrides({});
    setDirty(true);
  };

  const addCrop = () => {
    const newCrop: CropRect = {
      topPct: 0.3,
      leftPct: 0.1,
      widthPct: 0.8,
      heightPct: 0.4,
    };
    updateCropsForPage([...rawCrops, newCrop]);
    setSelectedCropIdx(rawCrops.length);
  };

  const deleteCrop = (idx: number) => {
    const newCrops = rawCrops.filter((_, i) => i !== idx);
    updateCropsForPage(newCrops);
    setSelectedCropIdx(null);
  };

  const commitOverride = (idx: number, crop: CropRect) => {
    const newCrops = [...rawCrops];
    newCrops[idx] = crop;
    updateCropsForPage(newCrops);
  };

  // ─── Coordinate Helpers ───────────────────────────────────────────────────

  const getRelativeCoords = (e: React.MouseEvent): { x: number; y: number } => {
    const container = imageContainerRef.current;
    if (!container) return { x: 0, y: 0 };
    const rect = container.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) / rect.width, // 0-1 range
      y: (e.clientY - rect.top) / rect.height,  // 0-1 range
    };
  };

  // ─── Drag/Resize Handlers ────────────────────────────────────────────────

  const startDrag = (e: React.MouseEvent, idx: number, mode: DragMode) => {
    e.stopPropagation();
    e.preventDefault();
    const coords = getRelativeCoords(e);
    const crop = crops[idx];
    if (!crop) return;
    setDragMode(mode);
    setDragCropIdx(idx);
    setDragStartCoords(coords);
    setDragOrigCrop({ ...crop });
    setSelectedCropIdx(idx);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragMode || dragCropIdx === null || !dragStartCoords || !dragOrigCrop) return;
    const coords = getRelativeCoords(e);
    const dx = coords.x - dragStartCoords.x;
    const dy = coords.y - dragStartCoords.y;

    let top = dragOrigCrop.topPct;
    let left = dragOrigCrop.leftPct;
    let width = dragOrigCrop.widthPct;
    let height = dragOrigCrop.heightPct;

    switch (dragMode) {
      case 'move':
        top = dragOrigCrop.topPct + dy;
        left = dragOrigCrop.leftPct + dx;
        break;
      case 'resize-nw':
        top = dragOrigCrop.topPct + dy;
        left = dragOrigCrop.leftPct + dx;
        width = dragOrigCrop.widthPct - dx;
        height = dragOrigCrop.heightPct - dy;
        break;
      case 'resize-ne':
        top = dragOrigCrop.topPct + dy;
        width = dragOrigCrop.widthPct + dx;
        height = dragOrigCrop.heightPct - dy;
        break;
      case 'resize-sw':
        left = dragOrigCrop.leftPct + dx;
        width = dragOrigCrop.widthPct - dx;
        height = dragOrigCrop.heightPct + dy;
        break;
      case 'resize-se':
        width = dragOrigCrop.widthPct + dx;
        height = dragOrigCrop.heightPct + dy;
        break;
      case 'resize-n':
        top = dragOrigCrop.topPct + dy;
        height = dragOrigCrop.heightPct - dy;
        break;
      case 'resize-s':
        height = dragOrigCrop.heightPct + dy;
        break;
      case 'resize-e':
        width = dragOrigCrop.widthPct + dx;
        break;
      case 'resize-w':
        left = dragOrigCrop.leftPct + dx;
        width = dragOrigCrop.widthPct - dx;
        break;
    }

    // Enforce minimum size (1% of image in 0-1 range = 0.01)
    if (width < 0.01) width = 0.01;
    if (height < 0.01) height = 0.01;
    // Clamp to image bounds (0-1)
    if (top < 0) top = 0;
    if (left < 0) left = 0;
    if (top + height > 1) height = 1 - top;
    if (left + width > 1) width = 1 - left;

    setLocalOverrides((prev) => ({
      ...prev,
      [dragCropIdx]: {
        topPct: Math.round(top * 1000) / 1000,
        leftPct: Math.round(left * 1000) / 1000,
        widthPct: Math.round(width * 1000) / 1000,
        heightPct: Math.round(height * 1000) / 1000,
      },
    }));
  };

  const handleMouseUp = () => {
    if (dragMode && dragCropIdx !== null && localOverrides[dragCropIdx]) {
      commitOverride(dragCropIdx, localOverrides[dragCropIdx]);
    }
    setDragMode(null);
    setDragCropIdx(null);
    setDragStartCoords(null);
    setDragOrigCrop(null);
  };

  const handleBackgroundClick = () => {
    if (!dragMode) {
      setSelectedCropIdx(null);
    }
  };

  // ─── Preview rendering ───────────────────────────────────────────────────

  const drawPreview = useCallback((idx: number, crop: CropRect) => {
    const canvas = previewCanvasRefs.current[idx];
    const img = sourceImageRef.current;
    if (!canvas || !img || !img.naturalWidth) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const sx = crop.leftPct * img.naturalWidth;
    const sy = crop.topPct * img.naturalHeight;
    const sw = crop.widthPct * img.naturalWidth;
    const sh = crop.heightPct * img.naturalHeight;

    // Set canvas size to match crop aspect ratio, max 300px wide
    const maxW = 300;
    const scale = Math.min(maxW / sw, 1);
    canvas.width = Math.round(sw * scale);
    canvas.height = Math.round(sh * scale);

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
  }, []);

  // Redraw previews when crops change
  useEffect(() => {
    if (!sourceImageRef.current?.naturalWidth) return;
    crops.forEach((crop, idx) => {
      drawPreview(idx, crop);
    });
  }, [crops, drawPreview, currentPage]);

  const handleImageLoad = () => {
    setImageError(false);
    // Draw all previews once the image is loaded
    crops.forEach((crop, idx) => {
      drawPreview(idx, crop);
    });
  };

  // ─── Page Navigation ─────────────────────────────────────────────────────

  const goToPage = (p: number) => {
    const clamped = Math.max(MIN_PAGE, Math.min(MAX_PAGE, p));
    setCurrentPage(clamped);
    setPageInput(String(clamped));
    setSelectedCropIdx(null);
    setLocalOverrides({});
    setImageError(false);
  };

  const handlePageInputSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const p = parseInt(pageInput, 10);
    if (!isNaN(p)) goToPage(p);
  };

  // Find next/prev page that has crops
  const findNextCropPage = (direction: 1 | -1): number | null => {
    const allPages = Object.keys(cropsData).map(Number).sort((a, b) => a - b);
    if (direction === 1) {
      return allPages.find((p) => p > currentPage) ?? null;
    } else {
      return [...allPages].reverse().find((p) => p < currentPage) ?? null;
    }
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Delete' || e.key === 'Backspace') {
        if (selectedCropIdx !== null && document.activeElement?.tagName !== 'INPUT') {
          e.preventDefault();
          deleteCrop(selectedCropIdx);
        }
      }
      if (e.key === 'ArrowLeft') {
        if (document.activeElement?.tagName !== 'INPUT') {
          e.preventDefault();
          goToPage(currentPage - 1);
        }
      }
      if (e.key === 'ArrowRight') {
        if (document.activeElement?.tagName !== 'INPUT') {
          e.preventDefault();
          goToPage(currentPage + 1);
        }
      }
      if (e.key === 's' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCropIdx, currentPage, cropsData]);

  // ─── Render ───────────────────────────────────────────────────────────────

  const handleSize = 8;
  const hasCrops = crops.length > 0;
  const imageUrl = `/api/books/${bookId}/page-image?page=${currentPage}`;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0f1117]">
        <div className="flex items-center gap-3 text-[#71717a]">
          <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading crops data...
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-[#0f1117] text-[#e4e4e7]">
      {/* ─── Top Nav Bar ──────────────────────────────────────────────────── */}
      <header className="flex-shrink-0 border-b border-[#2e2f3a] bg-[#1a1b23] px-4 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push(`/book/${bookId}`)}
            className="text-[#71717a] hover:text-[#e4e4e7] transition-colors"
            title="Back to book"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h1 className="text-sm font-semibold">Illustration Crop Editor</h1>
        </div>

        {/* Page Navigation */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              const prev = findNextCropPage(-1);
              if (prev !== null) goToPage(prev);
            }}
            className="px-2 py-1 text-xs rounded bg-[#2e2f3a] hover:bg-[#3e3f4a] text-[#a1a1aa] hover:text-white transition-colors"
            title="Previous page with crops"
          >
            Prev Crop
          </button>
          <button
            onClick={() => goToPage(currentPage - 1)}
            disabled={currentPage <= MIN_PAGE}
            className="p-1.5 rounded hover:bg-[#2e2f3a] text-[#a1a1aa] hover:text-white disabled:opacity-30 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          <form onSubmit={handlePageInputSubmit} className="flex items-center gap-1">
            <span className="text-xs text-[#71717a]">Page</span>
            <input
              type="text"
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value)}
              className="w-14 px-2 py-1 text-xs text-center bg-[#0f1117] border border-[#2e2f3a] rounded focus:outline-none focus:border-[#3b82f6]"
            />
            <span className="text-xs text-[#71717a]">/ {MAX_PAGE}</span>
          </form>

          <button
            onClick={() => goToPage(currentPage + 1)}
            disabled={currentPage >= MAX_PAGE}
            className="p-1.5 rounded hover:bg-[#2e2f3a] text-[#a1a1aa] hover:text-white disabled:opacity-30 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
          <button
            onClick={() => {
              const next = findNextCropPage(1);
              if (next !== null) goToPage(next);
            }}
            className="px-2 py-1 text-xs rounded bg-[#2e2f3a] hover:bg-[#3e3f4a] text-[#a1a1aa] hover:text-white transition-colors"
            title="Next page with crops"
          >
            Next Crop
          </button>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          {hasCrops && (
            <span className="text-xs text-[#22c55e] font-medium">
              {crops.length} crop{crops.length !== 1 ? 's' : ''}
            </span>
          )}
          <button
            onClick={addCrop}
            className="px-3 py-1.5 text-xs rounded bg-[#22c55e] hover:bg-[#16a34a] text-white font-medium transition-colors"
          >
            + Add Crop
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !dirty}
            className={`px-4 py-1.5 text-xs rounded font-medium transition-colors flex items-center gap-1.5 ${
              dirty
                ? 'bg-[#3b82f6] hover:bg-[#2563eb] text-white'
                : 'bg-[#2e2f3a] text-[#71717a] cursor-not-allowed'
            }`}
          >
            {saving ? (
              <>
                <svg className="animate-spin w-3 h-3" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Saving...
              </>
            ) : saveStatus === 'saved' ? (
              'Saved!'
            ) : (
              'Save All'
            )}
          </button>
          {dirty && <span className="text-xs text-[#eab308]">Unsaved changes</span>}
        </div>
      </header>

      {/* ─── Error Banner ─────────────────────────────────────────────────── */}
      {error && (
        <div className="flex-shrink-0 px-4 py-2 bg-red-500/10 border-b border-red-500/30 text-red-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 ml-4">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* ─── Main Content ─────────────────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">
        {/* ─── LEFT: Source Image + Crop Overlays ─────────────────────────── */}
        <div className="w-[60%] border-r border-[#2e2f3a] overflow-auto p-4 flex justify-center">
          <div
            ref={imageContainerRef}
            className="relative select-none"
            style={{ maxHeight: '100%', width: 'fit-content' }}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onClick={handleBackgroundClick}
          >
            {/* Source Image */}
            <img
              ref={sourceImageRef}
              src={imageUrl}
              alt={`Page ${currentPage}`}
              className="block"
              style={{ height: '600px', width: 'auto' }}
              draggable={false}
              onLoad={handleImageLoad}
              onError={() => setImageError(true)}
              crossOrigin="anonymous"
            />

            {/* "No image" overlay */}
            {imageError && (
              <div className="absolute inset-0 flex items-center justify-center bg-[#1a1b23] rounded">
                <div className="text-center text-[#71717a]">
                  <svg className="w-12 h-12 mx-auto mb-2 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <p className="text-sm">No cached image for page {currentPage}</p>
                  <p className="text-xs mt-1">Run OCR on this page first</p>
                </div>
              </div>
            )}

            {/* Crop Rectangles */}
            {!imageError && crops.map((crop, idx) => {
              const isSelected = selectedCropIdx === idx;
              const borderColor = isSelected ? '#22c55e' : 'rgba(34, 197, 94, 0.7)';

              return (
                <div
                  key={idx}
                  className="absolute"
                  style={{
                    left: `${crop.leftPct * 100}%`,
                    top: `${crop.topPct * 100}%`,
                    width: `${crop.widthPct * 100}%`,
                    height: `${crop.heightPct * 100}%`,
                    border: `2px solid ${borderColor}`,
                    backgroundColor: isSelected ? 'rgba(34, 197, 94, 0.2)' : 'rgba(34, 197, 94, 0.12)',
                    zIndex: isSelected ? 20 : 10,
                    cursor: isSelected ? 'move' : 'pointer',
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedCropIdx(idx);
                  }}
                  onMouseDown={(e) => {
                    if (isSelected) {
                      startDrag(e, idx, 'move');
                    }
                  }}
                  onContextMenu={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    deleteCrop(idx);
                  }}
                >
                  {/* Crop label */}
                  <div className="absolute -top-5 left-0 text-[10px] font-mono px-1 py-0.5 rounded bg-[#22c55e] text-white whitespace-nowrap">
                    Crop {idx + 1}
                  </div>

                  {/* Resize Handles (only when selected) */}
                  {isSelected && (
                    <>
                      {/* Corner handles */}
                      <div
                        className="absolute bg-white border-2 border-[#22c55e] rounded-sm"
                        style={{ width: handleSize, height: handleSize, top: -(handleSize / 2), left: -(handleSize / 2), cursor: 'nw-resize', zIndex: 30 }}
                        onMouseDown={(e) => startDrag(e, idx, 'resize-nw')}
                      />
                      <div
                        className="absolute bg-white border-2 border-[#22c55e] rounded-sm"
                        style={{ width: handleSize, height: handleSize, top: -(handleSize / 2), right: -(handleSize / 2), cursor: 'ne-resize', zIndex: 30 }}
                        onMouseDown={(e) => startDrag(e, idx, 'resize-ne')}
                      />
                      <div
                        className="absolute bg-white border-2 border-[#22c55e] rounded-sm"
                        style={{ width: handleSize, height: handleSize, bottom: -(handleSize / 2), left: -(handleSize / 2), cursor: 'sw-resize', zIndex: 30 }}
                        onMouseDown={(e) => startDrag(e, idx, 'resize-sw')}
                      />
                      <div
                        className="absolute bg-white border-2 border-[#22c55e] rounded-sm"
                        style={{ width: handleSize, height: handleSize, bottom: -(handleSize / 2), right: -(handleSize / 2), cursor: 'se-resize', zIndex: 30 }}
                        onMouseDown={(e) => startDrag(e, idx, 'resize-se')}
                      />
                      {/* Edge handles */}
                      <div
                        className="absolute bg-white border-2 border-[#22c55e] rounded-sm"
                        style={{ width: handleSize, height: handleSize, top: -(handleSize / 2), left: '50%', marginLeft: -(handleSize / 2), cursor: 'n-resize', zIndex: 30 }}
                        onMouseDown={(e) => startDrag(e, idx, 'resize-n')}
                      />
                      <div
                        className="absolute bg-white border-2 border-[#22c55e] rounded-sm"
                        style={{ width: handleSize, height: handleSize, bottom: -(handleSize / 2), left: '50%', marginLeft: -(handleSize / 2), cursor: 's-resize', zIndex: 30 }}
                        onMouseDown={(e) => startDrag(e, idx, 'resize-s')}
                      />
                      <div
                        className="absolute bg-white border-2 border-[#22c55e] rounded-sm"
                        style={{ width: handleSize, height: handleSize, top: '50%', marginTop: -(handleSize / 2), left: -(handleSize / 2), cursor: 'w-resize', zIndex: 30 }}
                        onMouseDown={(e) => startDrag(e, idx, 'resize-w')}
                      />
                      <div
                        className="absolute bg-white border-2 border-[#22c55e] rounded-sm"
                        style={{ width: handleSize, height: handleSize, top: '50%', marginTop: -(handleSize / 2), right: -(handleSize / 2), cursor: 'e-resize', zIndex: 30 }}
                        onMouseDown={(e) => startDrag(e, idx, 'resize-e')}
                      />
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ─── RIGHT: Crop Previews + Details ─────────────────────────────── */}
        <div className="w-[40%] overflow-auto p-4 bg-[#0f1117]">
          <h2 className="text-sm font-semibold mb-3 text-[#a1a1aa]">
            Page {currentPage} — {crops.length} Crop{crops.length !== 1 ? 's' : ''}
          </h2>

          {crops.length === 0 && (
            <div className="text-center text-[#71717a] py-12">
              <p className="text-sm mb-2">No crops on this page</p>
              <button
                onClick={addCrop}
                className="px-3 py-1.5 text-xs rounded bg-[#22c55e] hover:bg-[#16a34a] text-white font-medium transition-colors"
              >
                + Add Crop
              </button>
            </div>
          )}

          <div className="space-y-4">
            {crops.map((crop, idx) => (
              <div
                key={idx}
                className={`rounded-lg border p-3 transition-colors cursor-pointer ${
                  selectedCropIdx === idx
                    ? 'border-[#22c55e] bg-[#22c55e]/5'
                    : 'border-[#2e2f3a] bg-[#1a1b23] hover:border-[#3e3f4a]'
                }`}
                onClick={() => setSelectedCropIdx(idx)}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-[#22c55e]">Crop {idx + 1}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteCrop(idx);
                    }}
                    className="text-[#71717a] hover:text-[#ef4444] transition-colors"
                    title="Delete crop"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>

                {/* Coordinates display */}
                <div className="grid grid-cols-4 gap-1 text-[10px] font-mono text-[#71717a] mb-2">
                  <div>T: {(crop.topPct * 100).toFixed(1)}%</div>
                  <div>L: {(crop.leftPct * 100).toFixed(1)}%</div>
                  <div>W: {(crop.widthPct * 100).toFixed(1)}%</div>
                  <div>H: {(crop.heightPct * 100).toFixed(1)}%</div>
                </div>

                {/* Preview Canvas */}
                <div className="bg-[#0f1117] rounded border border-[#2e2f3a] p-1">
                  <canvas
                    ref={(el) => {
                      previewCanvasRefs.current[idx] = el;
                    }}
                    className="max-w-full h-auto"
                    style={{ imageRendering: 'auto' }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Quick jump to pages with crops */}
          <div className="mt-6 pt-4 border-t border-[#2e2f3a]">
            <h3 className="text-xs font-semibold text-[#71717a] mb-2">Pages with crops ({Object.keys(cropsData).length})</h3>
            <div className="flex flex-wrap gap-1 max-h-32 overflow-auto">
              {Object.keys(cropsData)
                .map(Number)
                .sort((a, b) => a - b)
                .map((p) => (
                  <button
                    key={p}
                    onClick={() => goToPage(p)}
                    className={`px-1.5 py-0.5 text-[10px] rounded font-mono transition-colors ${
                      p === currentPage
                        ? 'bg-[#3b82f6] text-white'
                        : 'bg-[#2e2f3a] text-[#a1a1aa] hover:bg-[#3e3f4a] hover:text-white'
                    }`}
                  >
                    {p}
                  </button>
                ))}
            </div>
          </div>

          {/* Keyboard shortcuts help */}
          <div className="mt-4 pt-3 border-t border-[#2e2f3a] text-[10px] text-[#52525b]">
            <p>Arrow keys: prev/next page</p>
            <p>Delete/Backspace: remove selected crop</p>
            <p>Right-click crop: delete</p>
            <p>Cmd/Ctrl+S: save</p>
          </div>
        </div>
      </div>
    </div>
  );
}
