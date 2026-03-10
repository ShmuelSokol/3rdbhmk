'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';

interface TranslatedPage {
  id: string;
  pageNumber: number;
  status: string;
  translation: {
    id: string;
    englishOutput: string;
    status: string;
  } | null;
}

interface BookData {
  id: string;
  name: string;
  totalPages: number;
  pages: TranslatedPage[];
}

export default function ComparePage() {
  const router = useRouter();
  const params = useParams();
  const bookId = params.bookId as string;

  const [book, setBook] = useState<BookData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const rowRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const fetchBook = useCallback(async () => {
    try {
      const res = await fetch(`/api/books/${bookId}/compare`);
      if (!res.ok) throw new Error('Failed to fetch book data');
      const data = await res.json();
      setBook(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [bookId]);

  useEffect(() => {
    fetchBook();
  }, [fetchBook]);

  const translatedPages = book?.pages.filter(
    (p) => p.translation && p.translation.englishOutput
  ) || [];

  const jumpToPage = (pageNumber: number) => {
    const el = rowRefs.current[pageNumber];
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0f1117]">
        <div className="flex items-center gap-3 text-[#71717a]">
          <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading comparison view...
        </div>
      </div>
    );
  }

  if (!book || error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0f1117]">
        <div className="text-center">
          <p className="text-[#ef4444] mb-4">{error || 'Book not found'}</p>
          <button
            onClick={() => router.push(`/book/${bookId}`)}
            className="px-4 py-2 rounded-lg bg-[#1a1b23] border border-[#2e2f3a] text-[#a1a1aa] hover:text-white transition-colors"
          >
            Back to Book
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f8f6f1]">
      {/* Sticky header */}
      <header className="sticky top-0 z-50 bg-[#1a1b23] border-b border-[#2e2f3a] shadow-lg">
        <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push(`/book/${bookId}`)}
              className="text-[#71717a] hover:text-[#e4e4e7] transition-colors"
              title="Back to book overview"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div>
              <h1 className="text-lg font-semibold text-[#e4e4e7] leading-tight">
                {book.name}
              </h1>
              <p className="text-xs text-[#71717a]">
                Side-by-Side Comparison &middot; {translatedPages.length} translated pages
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Jump to page */}
            {translatedPages.length > 0 && (
              <select
                onChange={(e) => jumpToPage(Number(e.target.value))}
                defaultValue=""
                className="px-3 py-1.5 rounded-lg bg-[#2e2f3a] border border-[#3e3f4a] text-[#e4e4e7] text-sm focus:outline-none focus:ring-2 focus:ring-[#3b82f6]/50"
              >
                <option value="" disabled>
                  Jump to page...
                </option>
                {translatedPages.map((p) => (
                  <option key={p.id} value={p.pageNumber}>
                    Page {p.pageNumber}
                  </option>
                ))}
              </select>
            )}

            {/* Download PDF */}
            <a
              href={`/api/books/${bookId}/export`}
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-lg bg-[#3b82f6] hover:bg-[#2563eb] text-white text-sm font-medium transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Download PDF
            </a>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-[1600px] mx-auto px-6 py-8">
        {translatedPages.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-[#78716c] text-lg">No translated pages yet.</p>
            <p className="text-[#a8a29e] text-sm mt-2">
              Translate pages from the book overview to see them here.
            </p>
          </div>
        ) : (
          <div className="space-y-12">
            {translatedPages.map((page) => (
              <div
                key={page.id}
                ref={(el) => { rowRefs.current[page.pageNumber] = el; }}
                className="scroll-mt-20"
              >
                {/* Page header */}
                <div className="flex items-center gap-3 mb-4">
                  <h2 className="text-xl font-semibold text-[#292524]">
                    Page {page.pageNumber}
                  </h2>
                  <span className="text-xs px-2 py-0.5 rounded bg-[#e7e5e4] text-[#78716c]">
                    {page.translation?.status || page.status}
                  </span>
                </div>

                {/* Two-column layout */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Left: Original image */}
                  <div className="bg-white rounded-xl border border-[#d6d3d1] shadow-sm overflow-hidden">
                    <div className="px-4 py-2 bg-[#fafaf9] border-b border-[#e7e5e4]">
                      <span className="text-xs font-medium text-[#78716c] uppercase tracking-wide">
                        Original Hebrew
                      </span>
                    </div>
                    <div className="p-2 flex items-center justify-center bg-[#f5f5f4] min-h-[400px]">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={`/api/pages/${page.id}/image`}
                        alt={`Original page ${page.pageNumber}`}
                        className="max-w-full h-auto border border-[#e7e5e4] rounded shadow-sm"
                        loading="lazy"
                      />
                    </div>
                  </div>

                  {/* Right: English translation */}
                  <div className="bg-white rounded-xl border border-[#d6d3d1] shadow-sm overflow-hidden">
                    <div className="px-4 py-2 bg-[#fafaf9] border-b border-[#e7e5e4]">
                      <span className="text-xs font-medium text-[#78716c] uppercase tracking-wide">
                        English Translation
                      </span>
                    </div>
                    <div className="p-6 min-h-[400px]">
                      <div
                        className="prose prose-stone max-w-none"
                        style={{
                          fontFamily: 'Georgia, "Times New Roman", Times, serif',
                          fontSize: '16px',
                          lineHeight: '1.8',
                          color: '#1c1917',
                        }}
                      >
                        {page.translation?.englishOutput
                          .split('\n')
                          .map((paragraph, idx) => {
                            const trimmed = paragraph.trim();
                            if (trimmed === '') {
                              return <br key={idx} />;
                            }
                            return (
                              <p
                                key={idx}
                                style={{ marginBottom: '0.75em', textAlign: 'justify' }}
                              >
                                {trimmed}
                              </p>
                            );
                          })}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
