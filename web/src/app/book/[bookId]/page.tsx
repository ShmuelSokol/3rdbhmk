'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';

interface PageInfo {
  id: string;
  pageNumber: number;
  status: string;
  imageUrl?: string;
}

interface Book {
  id: string;
  name: string;
  filename: string;
  totalPages: number;
  createdAt: string;
  pages: PageInfo[];
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: 'Pending', color: '#71717a', bg: 'bg-zinc-500/20' },
  ocr_done: { label: 'OCR Done', color: '#3b82f6', bg: 'bg-blue-500/20' },
  translated: { label: 'Translated', color: '#eab308', bg: 'bg-yellow-500/20' },
  reviewed: { label: 'Reviewed', color: '#a855f7', bg: 'bg-purple-500/20' },
  approved: { label: 'Approved', color: '#22c55e', bg: 'bg-green-500/20' },
};

function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium ${config.bg}`}
      style={{ color: config.color }}
    >
      {config.label}
    </span>
  );
}

export default function BookOverviewPage() {
  const router = useRouter();
  const params = useParams();
  const bookId = params.bookId as string;

  const [book, setBook] = useState<Book | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [batchLoading, setBatchLoading] = useState<string | null>(null);
  const [batchProgress, setBatchProgress] = useState<{ current: number; total: number; pageNumber: number } | null>(null);

  const fetchBook = useCallback(async () => {
    try {
      const res = await fetch(`/api/books/${bookId}`);
      if (!res.ok) throw new Error('Failed to fetch book');
      const data = await res.json();
      setBook(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load book');
    } finally {
      setLoading(false);
    }
  }, [bookId]);

  useEffect(() => {
    fetchBook();
  }, [fetchBook]);

  const handleBatchOCR = async () => {
    if (!book) return;
    setBatchLoading('ocr');
    setError(null);
    try {
      const pendingPages = book.pages
        .filter((p) => p.status === 'pending')
        .sort((a, b) => a.pageNumber - b.pageNumber);
      for (let i = 0; i < pendingPages.length; i++) {
        const page = pendingPages[i];
        setBatchProgress({ current: i + 1, total: pendingPages.length, pageNumber: page.pageNumber });
        const res = await fetch(`/api/pages/${page.id}/ocr`, { method: 'POST' });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error || `OCR failed for page ${page.pageNumber}`);
        }
      }
      await fetchBook();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Batch OCR failed');
    } finally {
      setBatchLoading(null);
      setBatchProgress(null);
    }
  };

  const handleBatchTranslate = async () => {
    if (!book) return;
    setBatchLoading('translate');
    setError(null);
    try {
      const ocrPages = book.pages
        .filter((p) => p.status === 'ocr_done')
        .sort((a, b) => a.pageNumber - b.pageNumber);
      for (let i = 0; i < ocrPages.length; i++) {
        const page = ocrPages[i];
        setBatchProgress({ current: i + 1, total: ocrPages.length, pageNumber: page.pageNumber });
        const res = await fetch(`/api/pages/${page.id}/translate`, { method: 'POST' });
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.error || `Translation failed for page ${page.pageNumber}`);
        }
      }
      await fetchBook();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Batch translation failed');
    } finally {
      setBatchLoading(null);
      setBatchProgress(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-3 text-[#71717a]">
          <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading book...
        </div>
      </div>
    );
  }

  if (!book) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-[#ef4444] mb-4">{error || 'Book not found'}</p>
          <button
            onClick={() => router.push('/')}
            className="px-4 py-2 rounded-lg bg-[#1a1b23] border border-[#2e2f3a] text-[#a1a1aa] hover:text-white transition-colors"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const pendingCount = book.pages.filter((p) => p.status === 'pending').length;
  const ocrCount = book.pages.filter((p) => p.status === 'ocr_done').length;
  const translatedCount = book.pages.filter((p) => p.status === 'translated' || p.status === 'reviewed' || p.status === 'approved').length;

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-[#2e2f3a] bg-[#1a1b23]">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center gap-3 mb-2">
            <button
              onClick={() => router.push('/')}
              className="text-[#71717a] hover:text-[#e4e4e7] transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <h1 className="text-2xl font-semibold tracking-tight">{book.name}</h1>
          </div>
          <div className="flex items-center gap-4 text-sm text-[#71717a]">
            <span>{book.totalPages} pages</span>
            <span>&middot;</span>
            <span>{book.filename}</span>
            <span>&middot;</span>
            <span>{new Date(book.createdAt).toLocaleDateString()}</span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Error banner */}
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 ml-4">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* Batch actions */}
        <div className="flex flex-col gap-3 mb-8">
          <div className="flex gap-3">
            <button
              onClick={handleBatchOCR}
              disabled={pendingCount === 0 || batchLoading !== null}
              className="px-4 py-2 rounded-lg bg-[#3b82f6] hover:bg-[#2563eb] text-white text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {batchLoading === 'ocr' ? (
                <>
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Running OCR...
                </>
              ) : (
                <>OCR All Pending ({pendingCount})</>
              )}
            </button>
            <button
              onClick={handleBatchTranslate}
              disabled={ocrCount === 0 || batchLoading !== null}
              className="px-4 py-2 rounded-lg bg-[#eab308] hover:bg-[#ca8a04] text-black text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {batchLoading === 'translate' ? (
                <>
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Translating...
                </>
              ) : (
                <>Translate All OCR&apos;d ({ocrCount})</>
              )}
            </button>
          </div>

          {/* Compare & Export actions */}
          <div className="flex gap-3">
            <button
              onClick={() => router.push(`/book/${bookId}/compare`)}
              disabled={translatedCount === 0}
              className="px-4 py-2 rounded-lg bg-[#a855f7] hover:bg-[#9333ea] text-white text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7" />
              </svg>
              Compare Side-by-Side
            </button>
            <a
              href={translatedCount > 0 ? `/api/books/${bookId}/export` : undefined}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                translatedCount > 0
                  ? 'bg-[#22c55e] hover:bg-[#16a34a] text-white cursor-pointer'
                  : 'bg-[#22c55e]/40 text-white/50 cursor-not-allowed pointer-events-none'
              }`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Download English PDF
            </a>
          </div>

          {/* Progress bar */}
          {batchProgress && (
            <div className="w-full max-w-md">
              <div className="flex items-center justify-between text-xs text-[#a1a1aa] mb-1.5">
                <span>
                  Processing page {batchProgress.pageNumber} ({batchProgress.current} of {batchProgress.total})
                </span>
                <span>{Math.round((batchProgress.current / batchProgress.total) * 100)}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-[#2e2f3a] overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${(batchProgress.current / batchProgress.total) * 100}%`,
                    backgroundColor: batchLoading === 'ocr' ? '#3b82f6' : '#eab308',
                  }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Page Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {book.pages
            .sort((a, b) => a.pageNumber - b.pageNumber)
            .map((page) => (
              <button
                key={page.id}
                onClick={() => router.push(`/book/${bookId}/page/${page.pageNumber}`)}
                className="bg-[#1a1b23] rounded-lg border border-[#2e2f3a] overflow-hidden hover:border-[#3b82f6]/50 hover:bg-[#22232e] transition-colors group"
              >
                {/* Thumbnail */}
                <div className="aspect-[3/4] bg-[#0f1117] relative overflow-hidden">
                  <img
                    src={`/api/pages/${page.id}/image?thumb=true`}
                    alt={`Page ${page.pageNumber}`}
                    className="w-full h-full object-contain"
                    loading="lazy"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.style.display = 'none';
                    }}
                  />
                  {/* Fallback when image hasn't loaded */}
                  <div className="absolute inset-0 flex items-center justify-center text-[#2e2f3a] pointer-events-none">
                    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                </div>
                {/* Info bar */}
                <div className="px-3 py-2 flex items-center justify-between">
                  <span className="text-xs text-[#a1a1aa] group-hover:text-white transition-colors">
                    Page {page.pageNumber}
                  </span>
                  <StatusBadge status={page.status} />
                </div>
              </button>
            ))}
        </div>
      </main>
    </div>
  );
}
