'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';

interface OcrLine {
  lineIndex: number;
  x: number;
  y: number;
  width: number;
  height: number;
  text: string;
}

interface TranslatedPage {
  id: string;
  pageNumber: number;
  status: string;
  translation: {
    id: string;
    englishOutput: string;
    status: string;
  } | null;
  lines: OcrLine[];
}

interface BookData {
  id: string;
  name: string;
  totalPages: number;
  pages: TranslatedPage[];
}

/**
 * Strip markdown formatting from text
 */
function stripMarkdown(text: string): string {
  return text
    .replace(/\*\*([^*]+)\*\*/g, '$1')  // **bold**
    .replace(/\*([^*]+)\*/g, '$1')       // *italic*
    .replace(/^#+\s+/gm, '')             // # headers
    .replace(/`([^`]+)`/g, '$1')         // `code`
}

/**
 * Flow English text word-by-word across OCR line positions.
 */
function flowTextToLines(
  englishText: string,
  lines: OcrLine[],
  imgWidth: number,
  imgHeight: number
): Array<{ line: OcrLine; text: string; fontSize: number }> {
  const textLines = lines.filter((l) => l.width > 3 && l.height > 0.5);
  if (textLines.length === 0) return [];

  // Clean the text
  const cleanText = stripMarkdown(englishText);

  // Calculate the full text column boundaries
  const colLeft = Math.min(...textLines.map((l) => l.x));
  const colRight = Math.max(...textLines.map((l) => l.x + l.width));
  const colWidth = colRight - colLeft;

  // Extend each line to span the full text column width for proper LTR flow
  const normalizedLines = textLines.map((l) => ({
    ...l,
    x: colLeft,
    width: colWidth,
  }));

  // Calculate a consistent body font size from the median line height
  const lineHeights = normalizedLines
    .map((l) => (l.height / 100) * imgHeight)
    .sort((a, b) => a - b);
  const medianHeight = lineHeights[Math.floor(lineHeights.length / 2)];
  const bodyFontSize = Math.max(9, Math.min(14, medianHeight * 0.65));

  // Split into paragraphs then words
  const paragraphs = cleanText.split('\n');
  const tokens: Array<{ word: string; paragraphBreak: boolean }> = [];
  for (const para of paragraphs) {
    const trimmed = para.trim();
    if (trimmed === '') {
      if (tokens.length > 0) tokens.push({ word: '', paragraphBreak: true });
      continue;
    }
    for (const w of trimmed.split(/\s+/)) {
      tokens.push({ word: w, paragraphBreak: false });
    }
  }

  const result: Array<{ line: OcrLine; text: string; fontSize: number }> = [];
  let tokenIdx = 0;

  for (const line of normalizedLines) {
    if (tokenIdx >= tokens.length) {
      result.push({ line, text: '', fontSize: bodyFontSize });
      continue;
    }

    const lineWidthPx = (line.width / 100) * imgWidth;

    // Use consistent body font for all lines
    const charWidth = bodyFontSize * 0.48;
    const maxChars = Math.floor(lineWidthPx / charWidth);

    let lineText = '';
    let charCount = 0;

    while (tokenIdx < tokens.length) {
      const token = tokens[tokenIdx];

      if (token.paragraphBreak) {
        tokenIdx++;
        break;
      }

      const addSpace = lineText.length > 0 ? 1 : 0;
      const needed = token.word.length + addSpace;

      if (charCount + needed > maxChars && lineText.length > 0) {
        break;
      }

      lineText += (addSpace ? ' ' : '') + token.word;
      charCount += needed;
      tokenIdx++;
    }

    result.push({ line, text: lineText, fontSize: bodyFontSize });
  }

  return result;
}

function EnglishOverlayPage({ page }: { page: TranslatedPage }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgSize, setImgSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (imgRef.current && imgLoaded) {
      const updateSize = () => {
        if (imgRef.current) {
          setImgSize({
            width: imgRef.current.clientWidth,
            height: imgRef.current.clientHeight,
          });
        }
      };
      updateSize();
      const observer = new ResizeObserver(updateSize);
      observer.observe(imgRef.current);
      return () => observer.disconnect();
    }
  }, [imgLoaded]);

  if (!page.translation || !page.lines.length) return null;

  const flowedLines =
    imgSize.width > 0
      ? flowTextToLines(
          page.translation.englishOutput,
          page.lines,
          imgSize.width,
          imgSize.height
        )
      : [];

  // Sample background color from page image using a canvas
  const [bgColor, setBgColor] = useState('#f0e6d0');
  useEffect(() => {
    if (imgRef.current && imgLoaded) {
      try {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        if (ctx && imgRef.current.naturalWidth > 0) {
          canvas.width = imgRef.current.naturalWidth;
          canvas.height = imgRef.current.naturalHeight;
          ctx.drawImage(imgRef.current, 0, 0);
          // Sample a few points in the margin area to get background color
          const samples: number[][] = [];
          const w = canvas.width;
          const h = canvas.height;
          // Sample from corners and edges (margin areas)
          const points = [
            [w * 0.05, h * 0.05],
            [w * 0.95, h * 0.05],
            [w * 0.05, h * 0.95],
            [w * 0.95, h * 0.95],
            [w * 0.5, h * 0.02],
            [w * 0.02, h * 0.5],
          ];
          for (const [px, py] of points) {
            const data = ctx.getImageData(Math.floor(px), Math.floor(py), 1, 1).data;
            samples.push([data[0], data[1], data[2]]);
          }
          // Average the samples
          const avg = samples.reduce(
            (acc, s) => [acc[0] + s[0], acc[1] + s[1], acc[2] + s[2]],
            [0, 0, 0]
          ).map((v) => Math.round(v / samples.length));
          setBgColor(`rgb(${avg[0]}, ${avg[1]}, ${avg[2]})`);
        }
      } catch {
        // CORS or other error, keep default
      }
    }
  }, [imgLoaded]);

  return (
    <div ref={containerRef} className="relative inline-block w-full">
      {/* Original page image as base */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        ref={imgRef}
        src={`/api/pages/${page.id}/image`}
        alt={`Page ${page.pageNumber}`}
        className="w-full h-auto block"
        crossOrigin="anonymous"
        onLoad={() => setImgLoaded(true)}
      />

      {/* Overlay: cover original Hebrew lines, then render English */}
      {imgLoaded && imgSize.width > 0 && (
        <div className="absolute inset-0" style={{ pointerEvents: 'none' }}>
          {/* First layer: cover all original Hebrew text lines with bg color */}
          {page.lines
            .filter((l) => l.width > 3 && l.height > 0.5)
            .map((line, idx) => (
              <div
                key={`cover-${idx}`}
                style={{
                  position: 'absolute',
                  left: `${line.x - 0.3}%`,
                  top: `${line.y - 0.15}%`,
                  width: `${line.width + 0.6}%`,
                  height: `${line.height + 0.3}%`,
                  backgroundColor: bgColor,
                }}
              />
            ))}
          {/* Second layer: English text at normalized (full-width) positions */}
          {flowedLines.map(({ line, text, fontSize }, idx) => (
            <div
              key={`text-${idx}`}
              style={{
                position: 'absolute',
                left: `${line.x}%`,
                top: `${line.y}%`,
                width: `${line.width}%`,
                height: `${line.height}%`,
                display: 'flex',
                alignItems: 'center',
                overflow: 'hidden',
              }}
            >
              {text && (
                <span
                  style={{
                    fontFamily: 'Georgia, "Times New Roman", "Palatino Linotype", serif',
                    fontSize: `${fontSize}px`,
                    lineHeight: 1.1,
                    color: '#1a1510',
                    whiteSpace: 'nowrap',
                    direction: 'ltr',
                  }}
                >
                  {text}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ComparePage() {
  const router = useRouter();
  const params = useParams();
  const bookId = params.bookId as string;

  const [book, setBook] = useState<BookData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showEnglish, setShowEnglish] = useState<Record<number, boolean>>({});
  const rowRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const fetchBook = useCallback(async () => {
    try {
      const res = await fetch(`/api/books/${bookId}/compare`);
      if (!res.ok) throw new Error('Failed to fetch book data');
      const data = await res.json();
      setBook(data);
      // Default all pages to English view
      const defaults: Record<number, boolean> = {};
      data.pages.forEach((p: TranslatedPage) => {
        if (p.translation) defaults[p.pageNumber] = true;
      });
      setShowEnglish(defaults);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, [bookId]);

  useEffect(() => {
    fetchBook();
  }, [fetchBook]);

  const translatedPages =
    book?.pages.filter((p) => p.translation && p.translation.englishOutput) || [];

  const jumpToPage = (pageNumber: number) => {
    const el = rowRefs.current[pageNumber];
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const togglePage = (pageNumber: number) => {
    setShowEnglish((prev) => ({
      ...prev,
      [pageNumber]: !prev[pageNumber],
    }));
  };

  const toggleAll = () => {
    const allEnglish = translatedPages.every((p) => showEnglish[p.pageNumber]);
    const newState: Record<number, boolean> = {};
    translatedPages.forEach((p) => {
      newState[p.pageNumber] = !allEnglish;
    });
    setShowEnglish(newState);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0f1117]">
        <div className="flex items-center gap-3 text-[#71717a]">
          <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Loading...
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
    <div className="min-h-screen bg-[#2a2520]">
      {/* Sticky header */}
      <header className="sticky top-0 z-50 bg-[#1a1b23] border-b border-[#2e2f3a] shadow-lg">
        <div className="max-w-[900px] mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push(`/book/${bookId}`)}
              className="text-[#71717a] hover:text-[#e4e4e7] transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div>
              <h1 className="text-lg font-semibold text-[#e4e4e7] leading-tight">
                {book.name || 'Book'}
              </h1>
              <p className="text-xs text-[#71717a]">
                {translatedPages.length} translated pages
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleAll}
              className="px-3 py-1.5 rounded-lg bg-[#2e2f3a] border border-[#3e3f4a] text-[#e4e4e7] text-sm hover:bg-[#3e3f4a] transition-colors"
            >
              {translatedPages.every((p) => showEnglish[p.pageNumber])
                ? 'Show All Hebrew'
                : 'Show All English'}
            </button>

            {translatedPages.length > 0 && (
              <select
                onChange={(e) => jumpToPage(Number(e.target.value))}
                defaultValue=""
                className="px-3 py-1.5 rounded-lg bg-[#2e2f3a] border border-[#3e3f4a] text-[#e4e4e7] text-sm focus:outline-none"
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

            <a
              href={`/api/books/${bookId}/export`}
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-lg bg-[#3b82f6] hover:bg-[#2563eb] text-white text-sm font-medium transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              PDF
            </a>
          </div>
        </div>
      </header>

      {/* Pages */}
      <main className="max-w-[900px] mx-auto px-6 py-8 space-y-10">
        {translatedPages.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-[#a8a29e] text-lg">No translated pages yet.</p>
          </div>
        ) : (
          translatedPages.map((page) => (
            <div
              key={page.id}
              ref={(el) => {
                rowRefs.current[page.pageNumber] = el;
              }}
              className="scroll-mt-20"
            >
              {/* Page label + toggle */}
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-[#d6d3d1]">
                  Page {page.pageNumber}
                </span>
                <button
                  onClick={() => togglePage(page.pageNumber)}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                    showEnglish[page.pageNumber]
                      ? 'bg-[#3b82f6] text-white'
                      : 'bg-[#44403c] text-[#d6d3d1]'
                  }`}
                >
                  {showEnglish[page.pageNumber] ? 'English' : 'Hebrew'}
                </button>
              </div>

              {/* Page display */}
              <div className="rounded-lg overflow-hidden shadow-xl border border-[#44403c]">
                {showEnglish[page.pageNumber] ? (
                  <EnglishOverlayPage page={page} />
                ) : (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={`/api/pages/${page.id}/image`}
                    alt={`Original page ${page.pageNumber}`}
                    className="w-full h-auto block"
                    loading="lazy"
                  />
                )}
              </div>
            </div>
          ))
        )}
      </main>
    </div>
  );
}
