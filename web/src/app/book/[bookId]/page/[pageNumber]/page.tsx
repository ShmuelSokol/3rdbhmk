'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';

// ─── Types ──────────────────────────────────────────────────────────────────

interface BoundingBox {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  hebrewText: string;
  editedText: string | null;
  englishText: string | null;
  confidence: number | null;
  lineIndex: number | null;
  wordIndex: number | null;
  isImage: boolean;
  skipTranslation: boolean;
}

interface FlagData {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  type: string;
  note: string | null;
  resolved: boolean;
}

interface TranslationData {
  id: string;
  hebrewInput: string;
  englishOutput: string;
  status: string;
  reviewNotes: string | null;
}

interface PageData {
  id: string;
  pageNumber: number;
  status: string;
  imageUrl: string | null;
  ocrResult: {
    id: string;
    boxes: BoundingBox[];
  } | null;
  translation: TranslationData | null;
  flags: FlagData[];
}

interface BookData {
  id: string;
  name: string;
  totalPages: number;
  pages: { id: string; pageNumber: number; status: string }[];
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: 'Pending', color: '#71717a', bg: 'bg-zinc-500/20 text-zinc-400' },
  ocr_done: { label: 'OCR Done', color: '#3b82f6', bg: 'bg-blue-500/20 text-blue-400' },
  translated: { label: 'Translated', color: '#eab308', bg: 'bg-yellow-500/20 text-yellow-400' },
  reviewed: { label: 'Reviewed', color: '#a855f7', bg: 'bg-purple-500/20 text-purple-400' },
  approved: { label: 'Approved', color: '#22c55e', bg: 'bg-green-500/20 text-green-400' },
};

const FLAG_TYPES = [
  'leave_hebrew',
  'reword',
  'bad_translation',
  'unclear_text',
  'image_region',
  'damaged',
  'marginalia',
  'table',
  'diagram',
  'footnote',
  'custom',
];

const FLAG_TYPE_LABELS: Record<string, string> = {
  leave_hebrew: 'Leave as Hebrew',
  reword: 'Reword',
  bad_translation: 'Bad Translation',
  unclear_text: 'Unclear Text',
  image_region: 'Image Region',
  damaged: 'Damaged',
  marginalia: 'Marginalia',
  table: 'Table',
  diagram: 'Diagram',
  footnote: 'Footnote',
  custom: 'Custom',
  other: 'Other',
};

// ─── Drag types ──────────────────────────────────────────────────────────────

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

// ─── StatusBadge ────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-medium ${config.bg}`}>
      {config.label}
    </span>
  );
}

// ─── Main Page Component ────────────────────────────────────────────────────

export default function EditorPage() {
  const router = useRouter();
  const params = useParams();
  const bookId = params.bookId as string;
  const pageNumber = parseInt(params.pageNumber as string, 10);

  // ─── State ──────────────────────────────────────────────────────────────

  const [book, setBook] = useState<BookData | null>(null);
  const [pageData, setPageData] = useState<PageData | null>(null);
  const [pageId, setPageId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'ocr' | 'translation' | 'flags'>('ocr');
  const [selectedBoxId, setSelectedBoxId] = useState<string | null>(null);
  const [hoveredBoxId, setHoveredBoxId] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Drawing state (for flags)
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [drawCurrent, setDrawCurrent] = useState<{ x: number; y: number } | null>(null);
  const [showFlagMenu, setShowFlagMenu] = useState<{ x: number; y: number; rect: { x: number; y: number; w: number; h: number } } | null>(null);

  // Drag/resize state (for bounding boxes)
  const [dragMode, setDragMode] = useState<DragMode>(null);
  const [dragBoxId, setDragBoxId] = useState<string | null>(null);
  const [dragStartCoords, setDragStartCoords] = useState<{ x: number; y: number } | null>(null);
  const [dragOrigBox, setDragOrigBox] = useState<{ x: number; y: number; width: number; height: number } | null>(null);
  const [localBoxOverrides, setLocalBoxOverrides] = useState<Record<string, { x: number; y: number; width: number; height: number }>>({});

  // Edited text tracking
  const [editedTexts, setEditedTexts] = useState<Record<string, string>>({});
  // Track which boxes have been saved (show green checkmark briefly)
  const [savedBoxIds, setSavedBoxIds] = useState<Set<string>>(new Set());

  const imageContainerRef = useRef<HTMLDivElement>(null);

  // ─── Data Fetching ──────────────────────────────────────────────────────

  const fetchBook = useCallback(async () => {
    try {
      const res = await fetch(`/api/books/${bookId}`);
      if (!res.ok) throw new Error('Failed to fetch book');
      const data: BookData = await res.json();
      setBook(data);

      const currentPage = data.pages.find((p) => p.pageNumber === pageNumber);
      if (!currentPage) throw new Error(`Page ${pageNumber} not found in book`);
      setPageId(currentPage.id);
      return currentPage.id;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load book');
      return null;
    }
  }, [bookId, pageNumber]);

  const fetchPageData = useCallback(
    async (pid: string) => {
      try {
        // Fetch page details: boxes, translation, flags
        const [boxesRes, flagsRes] = await Promise.all([
          fetch(`/api/pages/${pid}/boxes`),
          fetch(`/api/pages/${pid}/flags`),
        ]);

        // We construct page data from multiple endpoints
        // The page basic info comes from the book data
        const bookRes = await fetch(`/api/books/${bookId}`);
        if (!bookRes.ok) throw new Error('Failed to fetch book data');
        const bookData: BookData = await bookRes.json();
        const pageInfo = bookData.pages.find((p) => p.id === pid);

        let boxes: BoundingBox[] = [];
        if (boxesRes.ok) {
          const boxData = await boxesRes.json();
          boxes = Array.isArray(boxData) ? boxData : boxData.boxes || [];
        }

        let flags: FlagData[] = [];
        if (flagsRes.ok) {
          flags = await flagsRes.json();
        }

        // Try to get translation data
        let translation: TranslationData | null = null;
        try {
          const transRes = await fetch(`/api/pages/${pid}/translate`);
          if (transRes.ok) {
            translation = await transRes.json();
          }
        } catch {
          // No translation yet
        }

        const pageData: PageData = {
          id: pid,
          pageNumber: pageInfo?.pageNumber || pageNumber,
          status: pageInfo?.status || 'pending',
          imageUrl: null,
          ocrResult: boxes.length > 0 ? { id: '', boxes } : null,
          translation,
          flags,
        };

        setPageData(pageData);
        setBook(bookData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load page data');
      } finally {
        setLoading(false);
      }
    },
    [bookId, pageNumber]
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      const pid = await fetchBook();
      if (pid && !cancelled) {
        await fetchPageData(pid);
      } else if (!pid && !cancelled) {
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fetchBook, fetchPageData]);

  // ─── Actions ────────────────────────────────────────────────────────────

  const runOCR = async () => {
    if (!pageId) return;
    setActionLoading('ocr');
    setError(null);
    try {
      const res = await fetch(`/api/pages/${pageId}/ocr`, { method: 'POST' });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || 'OCR failed');
      }
      await fetchPageData(pageId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'OCR failed');
    } finally {
      setActionLoading(null);
    }
  };

  const runTranslation = async () => {
    if (!pageId) return;
    setActionLoading('translate');
    setError(null);
    try {
      const res = await fetch(`/api/pages/${pageId}/translate`, { method: 'POST' });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || 'Translation failed');
      }
      await fetchPageData(pageId);
      setActiveTab('translation');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Translation failed');
    } finally {
      setActionLoading(null);
    }
  };

  const reOCRBox = async (boxId: string) => {
    if (!pageId) return;
    setActionLoading(`reocr-${boxId}`);
    setError(null);
    try {
      const res = await fetch(`/api/pages/${pageId}/boxes/${boxId}/reocr`, { method: 'POST' });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || 'Re-OCR failed');
      }
      await fetchPageData(pageId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Re-OCR failed');
    } finally {
      setActionLoading(null);
    }
  };

  const saveBoxText = async (boxId: string, text: string) => {
    if (!pageId) return;
    try {
      const res = await fetch(`/api/pages/${pageId}/boxes`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify([{ id: boxId, editedText: text }]),
      });
      if (!res.ok) throw new Error('Failed to save');
      // Update local state
      setEditedTexts((prev) => {
        const next = { ...prev };
        delete next[boxId];
        return next;
      });
      // Show saved indicator
      setSavedBoxIds((prev) => new Set(prev).add(boxId));
      setTimeout(() => {
        setSavedBoxIds((prev) => {
          const next = new Set(prev);
          next.delete(boxId);
          return next;
        });
      }, 2000);
      await fetchPageData(pageId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save text');
    }
  };

  const saveBoxGeometry = async (boxId: string, geom: { x: number; y: number; width: number; height: number }) => {
    if (!pageId) return;
    try {
      const res = await fetch(`/api/pages/${pageId}/boxes`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify([{ id: boxId, ...geom }]),
      });
      if (!res.ok) throw new Error('Failed to save box position');
      // Clear the local override
      setLocalBoxOverrides((prev) => {
        const next = { ...prev };
        delete next[boxId];
        return next;
      });
      await fetchPageData(pageId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save box position');
    }
  };

  const updatePageStatus = async (newStatus: string) => {
    if (!pageId) return;
    setActionLoading('status');
    try {
      const res = await fetch(`/api/pages/${pageId}/boxes`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (!res.ok) throw new Error('Failed to update status');
      await fetchPageData(pageId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status');
    } finally {
      setActionLoading(null);
    }
  };

  const addFlag = async (rect: { x: number; y: number; w: number; h: number }, type: string) => {
    if (!pageId) return;
    try {
      const res = await fetch(`/api/pages/${pageId}/flags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          x: rect.x,
          y: rect.y,
          width: rect.w,
          height: rect.h,
          type,
        }),
      });
      if (!res.ok) throw new Error('Failed to add flag');
      await fetchPageData(pageId);
      setActiveTab('flags');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add flag');
    }
  };

  const resolveFlag = async (flagId: string, resolved: boolean) => {
    if (!pageId) return;
    try {
      const res = await fetch(`/api/pages/${pageId}/flags`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: flagId, resolved }),
      });
      if (!res.ok) throw new Error('Failed to update flag');
      await fetchPageData(pageId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update flag');
    }
  };

  const deleteFlag = async (flagId: string) => {
    if (!pageId) return;
    try {
      const res = await fetch(`/api/pages/${pageId}/flags?id=${flagId}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error('Failed to delete flag');
      await fetchPageData(pageId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete flag');
    }
  };

  // ─── Coordinate Helpers ────────────────────────────────────────────────

  const getRelativeCoords = (e: React.MouseEvent) => {
    const container = imageContainerRef.current;
    if (!container) return { x: 0, y: 0 };
    const rect = container.getBoundingClientRect();
    return {
      x: ((e.clientX - rect.left) / rect.width) * 100,
      y: ((e.clientY - rect.top) / rect.height) * 100,
    };
  };

  // ─── Box Drag/Resize Handlers ────────────────────────────────────────

  const startBoxDrag = (e: React.MouseEvent, boxId: string, mode: DragMode) => {
    e.stopPropagation();
    e.preventDefault();
    const coords = getRelativeCoords(e);
    const box = boxes.find((b) => b.id === boxId);
    if (!box) return;
    const override = localBoxOverrides[boxId];
    setDragMode(mode);
    setDragBoxId(boxId);
    setDragStartCoords(coords);
    setDragOrigBox({
      x: override?.x ?? box.x,
      y: override?.y ?? box.y,
      width: override?.width ?? box.width,
      height: override?.height ?? box.height,
    });
    setSelectedBoxId(boxId);
  };

  const handleContainerMouseMove = (e: React.MouseEvent) => {
    // Flag drawing
    if (isDrawing) {
      setDrawCurrent(getRelativeCoords(e));
      return;
    }
    // Box drag/resize
    if (dragMode && dragBoxId && dragStartCoords && dragOrigBox) {
      const coords = getRelativeCoords(e);
      const dx = coords.x - dragStartCoords.x;
      const dy = coords.y - dragStartCoords.y;
      let { x, y, width, height } = dragOrigBox;

      switch (dragMode) {
        case 'move':
          x = dragOrigBox.x + dx;
          y = dragOrigBox.y + dy;
          break;
        case 'resize-nw':
          x = dragOrigBox.x + dx;
          y = dragOrigBox.y + dy;
          width = dragOrigBox.width - dx;
          height = dragOrigBox.height - dy;
          break;
        case 'resize-ne':
          y = dragOrigBox.y + dy;
          width = dragOrigBox.width + dx;
          height = dragOrigBox.height - dy;
          break;
        case 'resize-sw':
          x = dragOrigBox.x + dx;
          width = dragOrigBox.width - dx;
          height = dragOrigBox.height + dy;
          break;
        case 'resize-se':
          width = dragOrigBox.width + dx;
          height = dragOrigBox.height + dy;
          break;
        case 'resize-n':
          y = dragOrigBox.y + dy;
          height = dragOrigBox.height - dy;
          break;
        case 'resize-s':
          height = dragOrigBox.height + dy;
          break;
        case 'resize-e':
          width = dragOrigBox.width + dx;
          break;
        case 'resize-w':
          x = dragOrigBox.x + dx;
          width = dragOrigBox.width - dx;
          break;
      }

      // Enforce minimum size
      if (width < 0.5) { width = 0.5; }
      if (height < 0.5) { height = 0.5; }
      // Clamp to image bounds
      if (x < 0) { x = 0; }
      if (y < 0) { y = 0; }
      if (x + width > 100) { width = 100 - x; }
      if (y + height > 100) { height = 100 - y; }

      setLocalBoxOverrides((prev) => ({
        ...prev,
        [dragBoxId]: { x, y, width, height },
      }));
    }
  };

  const handleContainerMouseUp = (e: React.MouseEvent) => {
    // Handle box drag/resize end
    if (dragMode && dragBoxId && localBoxOverrides[dragBoxId]) {
      saveBoxGeometry(dragBoxId, localBoxOverrides[dragBoxId]);
      setDragMode(null);
      setDragBoxId(null);
      setDragStartCoords(null);
      setDragOrigBox(null);
      return;
    }
    if (dragMode) {
      setDragMode(null);
      setDragBoxId(null);
      setDragStartCoords(null);
      setDragOrigBox(null);
      return;
    }

    // Handle flag drawing end
    if (!isDrawing || !drawStart || !drawCurrent) {
      setIsDrawing(false);
      return;
    }

    const x = Math.min(drawStart.x, drawCurrent.x);
    const y = Math.min(drawStart.y, drawCurrent.y);
    const w = Math.abs(drawCurrent.x - drawStart.x);
    const h = Math.abs(drawCurrent.y - drawStart.y);

    setIsDrawing(false);
    setDrawStart(null);
    setDrawCurrent(null);

    // Minimum size check (at least 1% in both dimensions)
    if (w < 1 || h < 1) return;

    // Show the flag type menu at the mouse position
    setShowFlagMenu({
      x: e.clientX,
      y: e.clientY,
      rect: { x, y, w, h },
    });
  };

  // ─── Drawing Handlers (flag mode only) ────────────────────────────────

  const handleContainerMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Left click only
    // Only start flag drawing when in flags tab
    if (activeTab === 'flags') {
      const coords = getRelativeCoords(e);
      setIsDrawing(true);
      setDrawStart(coords);
      setDrawCurrent(coords);
      setShowFlagMenu(null);
    } else {
      // Clicking on the background deselects the selected box
      setSelectedBoxId(null);
    }
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
  };

  // ─── Helpers ────────────────────────────────────────────────────────────

  const boxes = pageData?.ocrResult?.boxes || [];
  const flags = pageData?.flags || [];
  const translation = pageData?.translation;
  const totalPages = book?.totalPages || 0;

  // Group boxes by line
  const lineGroups: Record<number, BoundingBox[]> = {};
  for (const box of boxes) {
    const line = box.lineIndex ?? 0;
    if (!lineGroups[line]) lineGroups[line] = [];
    lineGroups[line].push(box);
  }
  // Sort within each line by wordIndex
  for (const line of Object.values(lineGroups)) {
    line.sort((a, b) => (a.wordIndex ?? 0) - (b.wordIndex ?? 0));
  }
  const sortedLineKeys = Object.keys(lineGroups)
    .map(Number)
    .sort((a, b) => a - b);

  // Assemble full Hebrew text from boxes (RTL, lines separated by newlines)
  const fullHebrew = sortedLineKeys
    .map((lineIdx) =>
      lineGroups[lineIdx]
        .map((b) => b.editedText || b.hebrewText)
        .join(' ')
    )
    .join('\n');

  // ─── Drawing rect computation ───────────────────────────────────────────

  const drawRect =
    isDrawing && drawStart && drawCurrent
      ? {
          left: `${Math.min(drawStart.x, drawCurrent.x)}%`,
          top: `${Math.min(drawStart.y, drawCurrent.y)}%`,
          width: `${Math.abs(drawCurrent.x - drawStart.x)}%`,
          height: `${Math.abs(drawCurrent.y - drawStart.y)}%`,
        }
      : null;

  // ─── Render ─────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-3 text-[#71717a]">
          <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading page...
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Top Nav Bar */}
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
          <span className="text-sm text-[#71717a]">{book?.name}</span>
          <span className="text-[#2e2f3a]">|</span>
          <span className="text-sm font-medium">
            Page {pageNumber} of {totalPages}
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Status badge + change dropdown */}
          <StatusBadge status={pageData?.status || 'pending'} />
          <select
            value={pageData?.status || 'pending'}
            onChange={(e) => updatePageStatus(e.target.value)}
            disabled={actionLoading === 'status'}
            className="bg-[#0f1117] border border-[#2e2f3a] rounded px-2 py-1 text-xs text-[#a1a1aa] focus:outline-none focus:border-[#3b82f6]"
          >
            <option value="pending">Pending</option>
            <option value="ocr_done">OCR Done</option>
            <option value="translated">Translated</option>
            <option value="reviewed">Reviewed</option>
            <option value="approved">Approved</option>
          </select>

          {/* Page navigation */}
          <div className="flex items-center gap-1 ml-2">
            <button
              onClick={() => router.push(`/book/${bookId}/page/${pageNumber - 1}`)}
              disabled={pageNumber <= 1}
              className="p-1.5 rounded hover:bg-[#2e2f3a] text-[#a1a1aa] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title="Previous page"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <button
              onClick={() => router.push(`/book/${bookId}/page/${pageNumber + 1}`)}
              disabled={pageNumber >= totalPages}
              className="p-1.5 rounded hover:bg-[#2e2f3a] text-[#a1a1aa] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title="Next page"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* Error banner */}
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

      {/* Main Split Pane */}
      <div className="flex-1 flex overflow-hidden">
        {/* ─── LEFT SIDE: Image + Bounding Boxes (60%) ─────────────────── */}
        <div className="w-[60%] border-r border-[#2e2f3a] overflow-auto bg-[#0a0a0f] p-4">
          <div
            ref={imageContainerRef}
            className="relative mx-auto select-none"
            style={{ maxWidth: '100%', cursor: activeTab === 'flags' ? 'crosshair' : 'default' }}
            onMouseDown={handleContainerMouseDown}
            onMouseMove={handleContainerMouseMove}
            onMouseUp={handleContainerMouseUp}
            onContextMenu={handleContextMenu}
          >
            {/* Page Image */}
            {pageId && (
              <img
                src={`/api/pages/${pageId}/image`}
                alt={`Page ${pageNumber}`}
                className="w-full h-auto block"
                draggable={false}
              />
            )}

            {/* Bounding Boxes */}
            {boxes.map((box) => {
              const isSelected = selectedBoxId === box.id;
              const isHovered = hoveredBoxId === box.id;
              const isEdited = !!box.editedText;
              const isSkipped = box.skipTranslation;
              const override = localBoxOverrides[box.id];
              const bx = override?.x ?? box.x;
              const by = override?.y ?? box.y;
              const bw = override?.width ?? box.width;
              const bh = override?.height ?? box.height;

              let borderColor = 'rgba(59, 130, 246, 0.6)'; // blue
              let bgColor = 'rgba(59, 130, 246, 0.08)';
              if (isSkipped) {
                borderColor = 'rgba(113, 113, 122, 0.6)';
                bgColor = 'rgba(113, 113, 122, 0.08)';
              } else if (isEdited) {
                borderColor = 'rgba(34, 197, 94, 0.6)';
                bgColor = 'rgba(34, 197, 94, 0.08)';
              }
              if (isSelected) {
                borderColor = '#3b82f6';
                bgColor = 'rgba(59, 130, 246, 0.15)';
              }

              const handleSize = 7;

              return (
                <div
                  key={box.id}
                  className="absolute transition-colors"
                  style={{
                    left: `${bx}%`,
                    top: `${by}%`,
                    width: `${bw}%`,
                    height: `${bh}%`,
                    border: `1.5px solid ${borderColor}`,
                    backgroundColor: bgColor,
                    zIndex: isSelected ? 20 : isHovered ? 15 : 10,
                    cursor: isSelected && activeTab !== 'flags' ? 'move' : 'pointer',
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedBoxId(box.id);
                    setActiveTab('ocr');
                  }}
                  onMouseDown={(e) => {
                    if (isSelected && activeTab !== 'flags') {
                      startBoxDrag(e, box.id, 'move');
                    }
                  }}
                  onMouseEnter={() => setHoveredBoxId(box.id)}
                  onMouseLeave={() => setHoveredBoxId(null)}
                >
                  {/* Hover tooltip */}
                  {isHovered && !isDrawing && !dragMode && (
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-[#1a1b23] border border-[#2e2f3a] rounded text-xs text-[#e4e4e7] whitespace-nowrap z-30 pointer-events-none shadow-lg"
                         dir="rtl">
                      {box.editedText || box.hebrewText}
                    </div>
                  )}
                  {/* Resize handles (visible when selected, not in flags mode) */}
                  {isSelected && activeTab !== 'flags' && (
                    <>
                      {/* Corner handles */}
                      {/* NW */}
                      <div
                        className="absolute bg-white border border-[#3b82f6]"
                        style={{ width: handleSize, height: handleSize, top: -(handleSize/2), left: -(handleSize/2), cursor: 'nw-resize', zIndex: 30 }}
                        onMouseDown={(e) => startBoxDrag(e, box.id, 'resize-nw')}
                      />
                      {/* NE */}
                      <div
                        className="absolute bg-white border border-[#3b82f6]"
                        style={{ width: handleSize, height: handleSize, top: -(handleSize/2), right: -(handleSize/2), cursor: 'ne-resize', zIndex: 30 }}
                        onMouseDown={(e) => startBoxDrag(e, box.id, 'resize-ne')}
                      />
                      {/* SW */}
                      <div
                        className="absolute bg-white border border-[#3b82f6]"
                        style={{ width: handleSize, height: handleSize, bottom: -(handleSize/2), left: -(handleSize/2), cursor: 'sw-resize', zIndex: 30 }}
                        onMouseDown={(e) => startBoxDrag(e, box.id, 'resize-sw')}
                      />
                      {/* SE */}
                      <div
                        className="absolute bg-white border border-[#3b82f6]"
                        style={{ width: handleSize, height: handleSize, bottom: -(handleSize/2), right: -(handleSize/2), cursor: 'se-resize', zIndex: 30 }}
                        onMouseDown={(e) => startBoxDrag(e, box.id, 'resize-se')}
                      />
                      {/* Edge handles */}
                      {/* N */}
                      <div
                        className="absolute bg-white border border-[#3b82f6]"
                        style={{ width: handleSize, height: handleSize, top: -(handleSize/2), left: '50%', marginLeft: -(handleSize/2), cursor: 'n-resize', zIndex: 30 }}
                        onMouseDown={(e) => startBoxDrag(e, box.id, 'resize-n')}
                      />
                      {/* S */}
                      <div
                        className="absolute bg-white border border-[#3b82f6]"
                        style={{ width: handleSize, height: handleSize, bottom: -(handleSize/2), left: '50%', marginLeft: -(handleSize/2), cursor: 's-resize', zIndex: 30 }}
                        onMouseDown={(e) => startBoxDrag(e, box.id, 'resize-s')}
                      />
                      {/* W */}
                      <div
                        className="absolute bg-white border border-[#3b82f6]"
                        style={{ width: handleSize, height: handleSize, top: '50%', marginTop: -(handleSize/2), left: -(handleSize/2), cursor: 'w-resize', zIndex: 30 }}
                        onMouseDown={(e) => startBoxDrag(e, box.id, 'resize-w')}
                      />
                      {/* E */}
                      <div
                        className="absolute bg-white border border-[#3b82f6]"
                        style={{ width: handleSize, height: handleSize, top: '50%', marginTop: -(handleSize/2), right: -(handleSize/2), cursor: 'e-resize', zIndex: 30 }}
                        onMouseDown={(e) => startBoxDrag(e, box.id, 'resize-e')}
                      />
                    </>
                  )}
                </div>
              );
            })}

            {/* Flags as red dashed rectangles */}
            {flags.map((flag) => (
              <div
                key={flag.id}
                className="absolute pointer-events-none"
                style={{
                  left: `${flag.x}%`,
                  top: `${flag.y}%`,
                  width: `${flag.width}%`,
                  height: `${flag.height}%`,
                  border: '2px dashed rgba(239, 68, 68, 0.7)',
                  backgroundColor: 'rgba(239, 68, 68, 0.05)',
                  zIndex: 5,
                }}
              >
                {/* Flag type icon */}
                <div className="absolute -top-3 -left-1 bg-[#ef4444] text-white text-[9px] px-1.5 py-0.5 rounded font-medium shadow">
                  {FLAG_TYPE_LABELS[flag.type] || flag.type}
                </div>
              </div>
            ))}

            {/* Drawing rectangle */}
            {drawRect && (
              <div
                className="absolute border-2 border-dashed border-[#eab308] bg-[#eab308]/10 pointer-events-none"
                style={{
                  left: drawRect.left,
                  top: drawRect.top,
                  width: drawRect.width,
                  height: drawRect.height,
                  zIndex: 25,
                }}
              />
            )}
          </div>

          {/* Flag type popup menu */}
          {showFlagMenu && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setShowFlagMenu(null)}
              />
              <div
                className="fixed z-50 bg-[#1a1b23] border border-[#2e2f3a] rounded-lg shadow-xl py-1 min-w-[160px]"
                style={{
                  left: showFlagMenu.x,
                  top: showFlagMenu.y,
                }}
              >
                <div className="px-3 py-1.5 text-[10px] uppercase tracking-wider text-[#71717a] font-medium">
                  Add Flag
                </div>
                {FLAG_TYPES.map((type) => (
                  <button
                    key={type}
                    className="w-full text-left px-3 py-1.5 text-sm text-[#a1a1aa] hover:text-white hover:bg-[#2e2f3a] transition-colors"
                    onClick={() => {
                      addFlag(showFlagMenu.rect, type);
                      setShowFlagMenu(null);
                    }}
                  >
                    {FLAG_TYPE_LABELS[type]}
                  </button>
                ))}
                <div className="border-t border-[#2e2f3a] mt-1 pt-1">
                  <button
                    className="w-full text-left px-3 py-1.5 text-sm text-[#71717a] hover:text-white hover:bg-[#2e2f3a] transition-colors"
                    onClick={() => setShowFlagMenu(null)}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* ─── RIGHT SIDE: Tabbed Panel (40%) ──────────────────────────── */}
        <div className="w-[40%] flex flex-col bg-[#0f1117]">
          {/* Tabs */}
          <div className="flex-shrink-0 border-b border-[#2e2f3a] flex">
            {(['ocr', 'translation', 'flags'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 px-4 py-2.5 text-sm font-medium transition-colors relative ${
                  activeTab === tab
                    ? 'text-[#e4e4e7]'
                    : 'text-[#71717a] hover:text-[#a1a1aa]'
                }`}
              >
                {tab === 'ocr' && 'OCR'}
                {tab === 'translation' && 'Translation'}
                {tab === 'flags' && `Flags${flags.length > 0 ? ` (${flags.length})` : ''}`}
                {activeTab === tab && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#3b82f6]" />
                )}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-auto">
            {/* ─── OCR Tab ───────────────────────────────────────────── */}
            {activeTab === 'ocr' && (
              <div className="p-4">
                {/* Run OCR button */}
                <button
                  onClick={runOCR}
                  disabled={actionLoading === 'ocr'}
                  className="w-full mb-4 px-4 py-2 rounded-lg bg-[#3b82f6] hover:bg-[#2563eb] text-white text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {actionLoading === 'ocr' ? (
                    <>
                      <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Running OCR...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      Run OCR
                    </>
                  )}
                </button>

                {boxes.length === 0 ? (
                  <div className="text-center py-12 text-[#71717a]">
                    <svg className="w-10 h-10 mx-auto mb-3 text-[#2e2f3a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p className="text-sm">No OCR results yet.</p>
                    <p className="text-xs mt-1">Click &quot;Run OCR&quot; to analyze this page.</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {sortedLineKeys.map((lineIdx) => (
                      <div key={lineIdx}>
                        <div className="text-[10px] uppercase tracking-wider text-[#71717a] mb-1.5 font-medium">
                          Line {lineIdx + 1}
                        </div>
                        <div className="space-y-1.5">
                          {lineGroups[lineIdx].map((box) => {
                            const isSelected = selectedBoxId === box.id;
                            const currentText =
                              editedTexts[box.id] !== undefined
                                ? editedTexts[box.id]
                                : box.editedText || box.hebrewText;
                            const hasUnsavedChanges =
                              editedTexts[box.id] !== undefined &&
                              editedTexts[box.id] !== (box.editedText || box.hebrewText);
                            const isSaved = savedBoxIds.has(box.id);

                            return (
                              <div
                                key={box.id}
                                className={`rounded-lg border p-2.5 transition-colors cursor-pointer ${
                                  isSelected
                                    ? 'border-[#3b82f6] bg-[#3b82f6]/10'
                                    : 'border-[#2e2f3a] bg-[#1a1b23] hover:border-[#3b82f6]/30'
                                }`}
                                onClick={() => setSelectedBoxId(box.id)}
                              >
                                <div className="flex items-start gap-2">
                                  <div className="flex-1">
                                    <div className="relative">
                                      <input
                                        type="text"
                                        value={currentText}
                                        onChange={(e) =>
                                          setEditedTexts((prev) => ({
                                            ...prev,
                                            [box.id]: e.target.value,
                                          }))
                                        }
                                        onBlur={() => {
                                          if (
                                            editedTexts[box.id] !== undefined &&
                                            editedTexts[box.id] !== (box.editedText || box.hebrewText)
                                          ) {
                                            saveBoxText(box.id, editedTexts[box.id]);
                                          }
                                        }}
                                        onKeyDown={(e) => {
                                          if (e.key === 'Enter') {
                                            e.currentTarget.blur();
                                          }
                                        }}
                                        dir="rtl"
                                        className={`w-full bg-[#0f1117] border rounded px-2.5 py-1.5 text-sm text-[#e4e4e7] focus:outline-none focus:border-[#3b82f6] font-serif ${
                                          hasUnsavedChanges
                                            ? 'border-[#eab308]/50'
                                            : isSaved
                                            ? 'border-[#22c55e]/50'
                                            : 'border-[#2e2f3a]'
                                        }`}
                                        onClick={(e) => e.stopPropagation()}
                                      />
                                      {/* Save status indicators */}
                                      {hasUnsavedChanges && (
                                        <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-[#eab308] font-medium">
                                          unsaved
                                        </span>
                                      )}
                                      {isSaved && !hasUnsavedChanges && (
                                        <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[#22c55e]">
                                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                          </svg>
                                        </span>
                                      )}
                                    </div>
                                    {box.confidence !== null && (
                                      <div className="mt-1 flex items-center gap-2">
                                        <div className="flex-1 h-1 rounded-full bg-[#2e2f3a] overflow-hidden">
                                          <div
                                            className="h-full rounded-full transition-all"
                                            style={{
                                              width: `${(box.confidence || 0) * 100}%`,
                                              backgroundColor:
                                                (box.confidence || 0) >= 0.85
                                                  ? '#22c55e'
                                                  : (box.confidence || 0) >= 0.6
                                                  ? '#eab308'
                                                  : '#ef4444',
                                            }}
                                          />
                                        </div>
                                        <span className="text-[10px] text-[#71717a] w-8 text-right">
                                          {Math.round((box.confidence || 0) * 100)}%
                                        </span>
                                      </div>
                                    )}
                                  </div>
                                  <div className="flex flex-col gap-1">
                                    {hasUnsavedChanges && (
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          saveBoxText(box.id, editedTexts[box.id]);
                                        }}
                                        className="p-1 rounded bg-[#22c55e]/20 text-[#22c55e] hover:bg-[#22c55e]/30 transition-colors"
                                        title="Save changes"
                                      >
                                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                        </svg>
                                      </button>
                                    )}
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        reOCRBox(box.id);
                                      }}
                                      disabled={actionLoading === `reocr-${box.id}`}
                                      className="p-1 rounded bg-[#2e2f3a] text-[#71717a] hover:text-white hover:bg-[#3b82f6]/30 transition-colors disabled:opacity-40"
                                      title="Re-OCR this box"
                                    >
                                      {actionLoading === `reocr-${box.id}` ? (
                                        <svg className="animate-spin w-3.5 h-3.5" fill="none" viewBox="0 0 24 24">
                                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                        </svg>
                                      ) : (
                                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                        </svg>
                                      )}
                                    </button>
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* ─── Translation Tab ───────────────────────────────────── */}
            {activeTab === 'translation' && (
              <div className="p-4 flex flex-col h-full">
                {/* Translate button */}
                <button
                  onClick={runTranslation}
                  disabled={actionLoading === 'translate' || boxes.length === 0}
                  className="w-full mb-4 px-4 py-2 rounded-lg bg-[#eab308] hover:bg-[#ca8a04] text-black text-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2 flex-shrink-0"
                >
                  {actionLoading === 'translate' ? (
                    <>
                      <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Translating...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                      </svg>
                      Translate
                    </>
                  )}
                </button>

                {/* Translation status */}
                {translation && (
                  <div className="flex items-center gap-2 mb-3 flex-shrink-0">
                    <span className="text-xs text-[#71717a]">Status:</span>
                    <StatusBadge status={translation.status} />
                  </div>
                )}

                {/* Hebrew text */}
                <div className="mb-4 flex-shrink-0">
                  <label className="block text-xs font-medium text-[#71717a] mb-1.5 uppercase tracking-wider">
                    Hebrew Text
                  </label>
                  <div
                    dir="rtl"
                    className="bg-[#1a1b23] border border-[#2e2f3a] rounded-lg p-3 text-sm text-[#e4e4e7] font-serif max-h-[35vh] overflow-auto whitespace-pre-wrap leading-relaxed"
                  >
                    {fullHebrew || (
                      <span className="text-[#71717a] italic">No OCR text available</span>
                    )}
                  </div>
                </div>

                {/* English translation */}
                <div className="flex-1 min-h-0 flex flex-col">
                  <label className="block text-xs font-medium text-[#71717a] mb-1.5 uppercase tracking-wider flex-shrink-0">
                    English Translation
                  </label>
                  <div className="bg-[#1a1b23] border border-[#2e2f3a] rounded-lg p-3 text-sm text-[#e4e4e7] flex-1 overflow-auto whitespace-pre-wrap leading-relaxed">
                    {translation?.englishOutput || (
                      <span className="text-[#71717a] italic">
                        No translation yet. Click &quot;Translate&quot; to generate one.
                      </span>
                    )}
                  </div>
                </div>

                {/* Review notes */}
                {translation?.reviewNotes && (
                  <div className="mt-3 flex-shrink-0">
                    <label className="block text-xs font-medium text-[#71717a] mb-1.5 uppercase tracking-wider">
                      Review Notes
                    </label>
                    <div className="bg-[#1a1b23] border border-[#eab308]/30 rounded-lg p-3 text-sm text-[#eab308]/80 whitespace-pre-wrap">
                      {translation.reviewNotes}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ─── Flags Tab ─────────────────────────────────────────── */}
            {activeTab === 'flags' && (
              <div className="p-4">
                <div className="mb-4 text-xs text-[#71717a]">
                  Draw a rectangle on the image, then select a flag type from the popup menu.
                </div>

                {flags.length === 0 ? (
                  <div className="text-center py-12 text-[#71717a]">
                    <svg className="w-10 h-10 mx-auto mb-3 text-[#2e2f3a]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
                    </svg>
                    <p className="text-sm">No flags on this page.</p>
                    <p className="text-xs mt-1">Draw a rectangle on the image to add one.</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {flags.map((flag) => (
                      <div
                        key={flag.id}
                        className={`rounded-lg border p-3 ${
                          flag.resolved
                            ? 'border-[#2e2f3a] bg-[#1a1b23]/50 opacity-60'
                            : 'border-[#ef4444]/30 bg-[#ef4444]/5'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-1.5">
                          <div className="flex items-center gap-2">
                            <span
                              className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium ${
                                flag.resolved
                                  ? 'bg-zinc-500/20 text-zinc-400'
                                  : 'bg-red-500/20 text-red-400'
                              }`}
                            >
                              {FLAG_TYPE_LABELS[flag.type] || flag.type}
                            </span>
                            {flag.resolved && (
                              <span className="text-[10px] text-[#22c55e]">Resolved</span>
                            )}
                          </div>
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => resolveFlag(flag.id, !flag.resolved)}
                              className={`p-1 rounded transition-colors ${
                                flag.resolved
                                  ? 'text-[#71717a] hover:text-[#eab308] hover:bg-[#eab308]/10'
                                  : 'text-[#71717a] hover:text-[#22c55e] hover:bg-[#22c55e]/10'
                              }`}
                              title={flag.resolved ? 'Unresolve' : 'Mark resolved'}
                            >
                              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            </button>
                            <button
                              onClick={() => deleteFlag(flag.id)}
                              className="p-1 rounded text-[#71717a] hover:text-[#ef4444] hover:bg-[#ef4444]/10 transition-colors"
                              title="Delete flag"
                            >
                              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          </div>
                        </div>
                        {flag.note && (
                          <p className="text-xs text-[#a1a1aa] mt-1">{flag.note}</p>
                        )}
                        <p className="text-[10px] text-[#71717a] mt-1">
                          Region: ({Math.round(flag.x)}%, {Math.round(flag.y)}%) {Math.round(flag.width)}x{Math.round(flag.height)}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
