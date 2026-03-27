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
  | 'draw'
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

  // Drag/resize/draw state — kept in refs for window event listeners
  const dragModeRef = useRef<DragMode>(null);
  const dragCropIdxRef = useRef<number | null>(null);
  const dragStartRef = useRef<{ x: number; y: number } | null>(null);
  const dragOrigCropRef = useRef<CropRect | null>(null);
  // For draw-to-create new crop
  const drawCurrentRef = useRef<{ x: number; y: number } | null>(null);

  // React state mirrors for rendering (updated during drag)
  const [localOverrides, setLocalOverrides] = useState<Record<number, CropRect>>({});
  const [drawRect, setDrawRect] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const [activeDragMode, setActiveDragMode] = useState<DragMode>(null);

  const imageContainerRef = useRef<HTMLDivElement>(null);
  const previewCanvasRefs = useRef<Record<number, HTMLCanvasElement | null>>({});
  const sourceImageRef = useRef<HTMLImageElement | null>(null);
  const [imgDisplaySize, setImgDisplaySize] = useState<{ w: number; h: number } | null>(null);

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

  const updateCropsForPage = useCallback((newCrops: CropRect[]) => {
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
  }, [pageKey]);

  const addCropRect = useCallback((crop: CropRect) => {
    let newIdx = 0;
    setCropsData((prev) => {
      const next = { ...prev };
      const existing = next[pageKey] || [];
      newIdx = existing.length;
      next[pageKey] = [...existing, crop];
      return next;
    });
    setLocalOverrides({});
    setDirty(true);
    // Select the newly added crop after state updates
    setTimeout(() => setSelectedCropIdx(newIdx), 0);
  }, [pageKey]);

  const deleteCrop = useCallback((idx: number) => {
    setCropsData((prev) => {
      const next = { ...prev };
      const existing = next[pageKey] || [];
      const newCrops = existing.filter((_, i) => i !== idx);
      if (newCrops.length === 0) {
        delete next[pageKey];
      } else {
        next[pageKey] = newCrops;
      }
      return next;
    });
    setLocalOverrides({});
    setSelectedCropIdx(null);
    setDirty(true);
  }, [pageKey]);

  const commitOverride = useCallback((idx: number, crop: CropRect) => {
    setCropsData((prev) => {
      const next = { ...prev };
      const existing = [...(next[pageKey] || [])];
      existing[idx] = crop;
      next[pageKey] = existing;
      return next;
    });
    setLocalOverrides({});
    setDirty(true);
  }, [pageKey]);

  // ─── Coordinate Helpers ───────────────────────────────────────────────────

  const getRelativeCoords = useCallback((clientX: number, clientY: number): { x: number; y: number } => {
    const container = imageContainerRef.current;
    if (!container) return { x: 0, y: 0 };
    const rect = container.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(1, (clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (clientY - rect.top) / rect.height)),
    };
  }, []);

  // ─── Hit test: is a point inside a crop? ──────────────────────────────────

  const hitTestCrops = useCallback((px: number, py: number, cropsList: CropRect[]): number | null => {
    // Check in reverse order so topmost (last rendered) crops get priority
    for (let i = cropsList.length - 1; i >= 0; i--) {
      const c = cropsList[i];
      if (
        px >= c.leftPct &&
        px <= c.leftPct + c.widthPct &&
        py >= c.topPct &&
        py <= c.topPct + c.heightPct
      ) {
        return i;
      }
    }
    return null;
  }, []);

  // ─── Window-level mouse handlers (refs avoid stale closures) ──────────────

  const handleWindowMouseMove = useCallback((e: MouseEvent) => {
    const mode = dragModeRef.current;
    if (!mode) return;

    const coords = getRelativeCoords(e.clientX, e.clientY);

    if (mode === 'draw') {
      // Drawing a new crop rectangle
      const start = dragStartRef.current;
      if (!start) return;
      drawCurrentRef.current = coords;

      const x = Math.min(start.x, coords.x);
      const y = Math.min(start.y, coords.y);
      const w = Math.abs(coords.x - start.x);
      const h = Math.abs(coords.y - start.y);

      setDrawRect({ x, y, w, h });
      return;
    }

    // Move or resize
    const idx = dragCropIdxRef.current;
    const startCoords = dragStartRef.current;
    const origCrop = dragOrigCropRef.current;
    if (idx === null || !startCoords || !origCrop) return;

    const dx = coords.x - startCoords.x;
    const dy = coords.y - startCoords.y;

    let top = origCrop.topPct;
    let left = origCrop.leftPct;
    let width = origCrop.widthPct;
    let height = origCrop.heightPct;

    switch (mode) {
      case 'move':
        top = origCrop.topPct + dy;
        left = origCrop.leftPct + dx;
        break;
      case 'resize-nw':
        top = origCrop.topPct + dy;
        left = origCrop.leftPct + dx;
        width = origCrop.widthPct - dx;
        height = origCrop.heightPct - dy;
        break;
      case 'resize-ne':
        top = origCrop.topPct + dy;
        width = origCrop.widthPct + dx;
        height = origCrop.heightPct - dy;
        break;
      case 'resize-sw':
        left = origCrop.leftPct + dx;
        width = origCrop.widthPct - dx;
        height = origCrop.heightPct + dy;
        break;
      case 'resize-se':
        width = origCrop.widthPct + dx;
        height = origCrop.heightPct + dy;
        break;
      case 'resize-n':
        top = origCrop.topPct + dy;
        height = origCrop.heightPct - dy;
        break;
      case 'resize-s':
        height = origCrop.heightPct + dy;
        break;
      case 'resize-e':
        width = origCrop.widthPct + dx;
        break;
      case 'resize-w':
        left = origCrop.leftPct + dx;
        width = origCrop.widthPct - dx;
        break;
    }

    // Enforce minimum size
    if (width < 0.01) width = 0.01;
    if (height < 0.01) height = 0.01;
    // Clamp to image bounds
    if (top < 0) top = 0;
    if (left < 0) left = 0;
    if (top + height > 1) height = 1 - top;
    if (left + width > 1) width = 1 - left;

    setLocalOverrides((prev) => ({
      ...prev,
      [idx]: {
        topPct: Math.round(top * 1000) / 1000,
        leftPct: Math.round(left * 1000) / 1000,
        widthPct: Math.round(width * 1000) / 1000,
        heightPct: Math.round(height * 1000) / 1000,
      },
    }));
  }, [getRelativeCoords]);

  const handleWindowMouseUp = useCallback(() => {
    const mode = dragModeRef.current;
    const idx = dragCropIdxRef.current;

    if (mode === 'draw') {
      // Finish drawing a new crop
      const start = dragStartRef.current;
      const current = drawCurrentRef.current;
      if (start && current) {
        const x = Math.min(start.x, current.x);
        const y = Math.min(start.y, current.y);
        const w = Math.abs(current.x - start.x);
        const h = Math.abs(current.y - start.y);

        // Minimum 1% in both dimensions to avoid accidental tiny crops
        if (w >= 0.01 && h >= 0.01) {
          const newCrop: CropRect = {
            topPct: Math.round(y * 1000) / 1000,
            leftPct: Math.round(x * 1000) / 1000,
            widthPct: Math.round(w * 1000) / 1000,
            heightPct: Math.round(h * 1000) / 1000,
          };
          addCropRect(newCrop);
        }
      }
      setDrawRect(null);
      drawCurrentRef.current = null;
    } else if (mode && idx !== null) {
      // Finish move/resize — commit the override
      setLocalOverrides((prev) => {
        const override = prev[idx];
        if (override) {
          // Use setTimeout to commit after this render cycle
          setTimeout(() => commitOverride(idx, override), 0);
        }
        return prev;
      });
    }

    // Reset all drag state
    dragModeRef.current = null;
    dragCropIdxRef.current = null;
    dragStartRef.current = null;
    dragOrigCropRef.current = null;
    setActiveDragMode(null);
  }, [addCropRect, commitOverride]);

  // Attach window-level listeners for drag
  useEffect(() => {
    window.addEventListener('mousemove', handleWindowMouseMove);
    window.addEventListener('mouseup', handleWindowMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleWindowMouseMove);
      window.removeEventListener('mouseup', handleWindowMouseUp);
    };
  }, [handleWindowMouseMove, handleWindowMouseUp]);

  // ─── Container mousedown: either start drawing or select+move ─────────────

  const handleContainerMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Left click only

    const coords = getRelativeCoords(e.clientX, e.clientY);

    // Check if we clicked on an existing crop
    const hitIdx = hitTestCrops(coords.x, coords.y, crops);

    if (hitIdx !== null) {
      // Clicked on a crop — select it and start moving
      e.preventDefault();
      setSelectedCropIdx(hitIdx);
      const crop = crops[hitIdx];
      dragModeRef.current = 'move';
      dragCropIdxRef.current = hitIdx;
      dragStartRef.current = coords;
      dragOrigCropRef.current = { ...crop };
      setActiveDragMode('move');
    } else {
      // Clicked on empty space — deselect any crop, start drawing a new one
      setSelectedCropIdx(null);
      e.preventDefault();
      dragModeRef.current = 'draw';
      dragStartRef.current = coords;
      drawCurrentRef.current = coords;
      setDrawRect({ x: coords.x, y: coords.y, w: 0, h: 0 });
      setActiveDragMode('draw');
    }
  };

  // ─── Handle mousedown on resize handles ───────────────────────────────────

  const startResize = (e: React.MouseEvent, idx: number, mode: DragMode) => {
    e.stopPropagation();
    e.preventDefault();
    const coords = getRelativeCoords(e.clientX, e.clientY);
    const crop = crops[idx];
    if (!crop) return;
    dragModeRef.current = mode;
    dragCropIdxRef.current = idx;
    dragStartRef.current = coords;
    dragOrigCropRef.current = { ...crop };
    setSelectedCropIdx(idx);
    setActiveDragMode(mode);
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
    const img = sourceImageRef.current;
    if (img) {
      setImgDisplaySize({ w: img.clientWidth, h: img.clientHeight });
    }
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
    setImgDisplaySize(null);
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
      if (e.key === 'Escape') {
        setSelectedCropIdx(null);
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
  }, [selectedCropIdx, currentPage, cropsData, deleteCrop]);

  // ─── Render ───────────────────────────────────────────────────────────────

  const handleSize = 9;
  const hasCrops = crops.length > 0;
  const imageUrl = `/api/books/${bookId}/page-image?page=${currentPage}`;

  // Compute cursor for the container
  const containerCursor = activeDragMode === 'draw'
    ? 'crosshair'
    : activeDragMode === 'move'
    ? 'move'
    : activeDragMode?.startsWith('resize-')
    ? (() => {
        const dir = activeDragMode.replace('resize-', '');
        const cursorMap: Record<string, string> = {
          nw: 'nw-resize', ne: 'ne-resize', sw: 'sw-resize', se: 'se-resize',
          n: 'n-resize', s: 's-resize', e: 'e-resize', w: 'w-resize',
        };
        return cursorMap[dir] || 'default';
      })()
    : 'crosshair';

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
            style={{
              ...(imgDisplaySize ? { width: imgDisplaySize.w, height: imgDisplaySize.h } : { display: 'inline-block' }),
              cursor: containerCursor,
            }}
            onMouseDown={handleContainerMouseDown}
            onContextMenu={(e) => {
              e.preventDefault();
              // Right-click on a crop to delete it
              const coords = getRelativeCoords(e.clientX, e.clientY);
              const hitIdx = hitTestCrops(coords.x, coords.y, crops);
              if (hitIdx !== null) {
                deleteCrop(hitIdx);
              }
            }}
          >
            {/* Source Image */}
            <img
              ref={sourceImageRef}
              src={imageUrl}
              alt={`Page ${currentPage}`}
              className="block max-h-[75vh]"
              style={{ width: 'auto', height: 'auto', maxHeight: '75vh', pointerEvents: 'none' }}
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
                    // Prevent this div from capturing mousedown — the container handler does hit-testing
                    pointerEvents: 'none',
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
                        style={{ width: handleSize, height: handleSize, top: -(handleSize / 2), left: -(handleSize / 2), cursor: 'nw-resize', zIndex: 30, pointerEvents: 'auto' }}
                        onMouseDown={(e) => startResize(e, idx, 'resize-nw')}
                      />
                      <div
                        className="absolute bg-white border-2 border-[#22c55e] rounded-sm"
                        style={{ width: handleSize, height: handleSize, top: -(handleSize / 2), right: -(handleSize / 2), cursor: 'ne-resize', zIndex: 30, pointerEvents: 'auto' }}
                        onMouseDown={(e) => startResize(e, idx, 'resize-ne')}
                      />
                      <div
                        className="absolute bg-white border-2 border-[#22c55e] rounded-sm"
                        style={{ width: handleSize, height: handleSize, bottom: -(handleSize / 2), left: -(handleSize / 2), cursor: 'sw-resize', zIndex: 30, pointerEvents: 'auto' }}
                        onMouseDown={(e) => startResize(e, idx, 'resize-sw')}
                      />
                      <div
                        className="absolute bg-white border-2 border-[#22c55e] rounded-sm"
                        style={{ width: handleSize, height: handleSize, bottom: -(handleSize / 2), right: -(handleSize / 2), cursor: 'se-resize', zIndex: 30, pointerEvents: 'auto' }}
                        onMouseDown={(e) => startResize(e, idx, 'resize-se')}
                      />
                      {/* Edge handles */}
                      <div
                        className="absolute bg-white border-2 border-[#22c55e] rounded-sm"
                        style={{ width: handleSize, height: handleSize, top: -(handleSize / 2), left: '50%', marginLeft: -(handleSize / 2), cursor: 'n-resize', zIndex: 30, pointerEvents: 'auto' }}
                        onMouseDown={(e) => startResize(e, idx, 'resize-n')}
                      />
                      <div
                        className="absolute bg-white border-2 border-[#22c55e] rounded-sm"
                        style={{ width: handleSize, height: handleSize, bottom: -(handleSize / 2), left: '50%', marginLeft: -(handleSize / 2), cursor: 's-resize', zIndex: 30, pointerEvents: 'auto' }}
                        onMouseDown={(e) => startResize(e, idx, 'resize-s')}
                      />
                      <div
                        className="absolute bg-white border-2 border-[#22c55e] rounded-sm"
                        style={{ width: handleSize, height: handleSize, top: '50%', marginTop: -(handleSize / 2), left: -(handleSize / 2), cursor: 'w-resize', zIndex: 30, pointerEvents: 'auto' }}
                        onMouseDown={(e) => startResize(e, idx, 'resize-w')}
                      />
                      <div
                        className="absolute bg-white border-2 border-[#22c55e] rounded-sm"
                        style={{ width: handleSize, height: handleSize, top: '50%', marginTop: -(handleSize / 2), right: -(handleSize / 2), cursor: 'e-resize', zIndex: 30, pointerEvents: 'auto' }}
                        onMouseDown={(e) => startResize(e, idx, 'resize-e')}
                      />
                    </>
                  )}
                </div>
              );
            })}

            {/* Drawing rectangle preview (while drawing a new crop) */}
            {drawRect && drawRect.w > 0.001 && drawRect.h > 0.001 && (
              <div
                className="absolute border-2 border-dashed border-[#22c55e] bg-[#22c55e]/15 pointer-events-none"
                style={{
                  left: `${drawRect.x * 100}%`,
                  top: `${drawRect.y * 100}%`,
                  width: `${drawRect.w * 100}%`,
                  height: `${drawRect.h * 100}%`,
                  zIndex: 25,
                }}
              />
            )}

            {/* Instruction overlay when no crops and no image error */}
            {!imageError && crops.length === 0 && !activeDragMode && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="bg-black/60 text-white/80 text-sm px-4 py-2 rounded-lg">
                  Click and drag to draw a crop region
                </div>
              </div>
            )}
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
              <p className="text-xs text-[#52525b]">Draw on the image to add a crop</p>
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
                    title="Delete crop (or press Delete key)"
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
            <p>Click + drag on image: draw new crop</p>
            <p>Click crop: select, then drag to move</p>
            <p>Drag white handles: resize selected crop</p>
            <p>Delete/Backspace: remove selected crop</p>
            <p>Right-click crop: delete</p>
            <p>Escape: deselect</p>
            <p>Arrow keys: prev/next page</p>
            <p>Cmd/Ctrl+S: save</p>
          </div>
        </div>
      </div>
    </div>
  );
}
