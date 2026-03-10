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

// --- TEXT TOKENIZATION & FLOW ---

type FlowToken =
  | { type: 'word'; word: string; bold: boolean }
  | { type: 'break' };

function tokenizeTranslation(raw: string): FlowToken[] {
  const tokens: FlowToken[] = [];
  const paragraphs = raw.split(/\n\s*\n/);

  for (let i = 0; i < paragraphs.length; i++) {
    if (i > 0) tokens.push({ type: 'break' });
    const para = paragraphs[i].trim();
    if (!para) continue;

    // Split on bold markers **...**
    const parts = para.split(/(\*\*[\s\S]*?\*\*)/);
    for (const part of parts) {
      if (!part.trim()) continue;
      const boldMatch = part.match(/^\*\*([\s\S]*?)\*\*$/);
      const text = (boldMatch ? boldMatch[1] : part)
        .replace(/\n/g, ' ')
        .replace(/^#+\s+/gm, '')
        .replace(/`([^`]+)`/g, '$1')
        .trim();
      const bold = !!boldMatch;
      const words = text.split(/\s+/).filter((w) => w.length > 0);
      for (const word of words) {
        tokens.push({ type: 'word', word, bold });
      }
    }
  }

  return tokens;
}

interface LineSpan {
  text: string;
  bold: boolean;
}

interface FlowLine {
  line: OcrLine;
  spans: LineSpan[];
}

function flowTextToLines(
  ocrLines: OcrLine[],
  tokens: FlowToken[],
  imgWidth: number,
  fontSize: number
): { flowLines: FlowLine[]; overflow: boolean } {
  const CW = 0.55;
  const flowLines: FlowLine[] = [];
  let ti = 0;

  for (const ocrLine of ocrLines) {
    const widthPx = (ocrLine.width / 100) * imgWidth;
    const maxChars = Math.max(1, Math.floor(widthPx / (fontSize * CW)));

    const spans: LineSpan[] = [];
    let chars = 0;
    let curText = '';
    let curBold = false;

    const flush = () => {
      if (curText) {
        spans.push({ text: curText, bold: curBold });
        curText = '';
      }
    };

    while (ti < tokens.length) {
      const tok = tokens[ti];
      if (tok.type === 'break') {
        ti++;
        break;
      }

      const space = chars > 0 ? 1 : 0;
      const needed = tok.word.length + space;
      if (chars + needed > maxChars && chars > 0) break;

      if (curText && curBold !== tok.bold) {
        flush();
        curBold = tok.bold;
      }
      if (!curText) {
        curBold = tok.bold;
        // Preserve space between spans when mid-line
        curText = (chars > 0 ? ' ' : '') + tok.word;
      } else {
        curText += ' ' + tok.word;
      }
      chars += needed;
      ti++;
    }

    flush();
    flowLines.push({ line: ocrLine, spans });
  }

  return { flowLines, overflow: ti < tokens.length };
}

// --- PER-LINE COLOR SAMPLING ---

interface LineColor {
  bg: string;
  textColor: string;
}

function sampleLineColors(
  img: HTMLImageElement,
  lines: OcrLine[]
): Map<number, LineColor> {
  const colors = new Map<number, LineColor>();

  try {
    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx || img.naturalWidth === 0) return colors;

    ctx.drawImage(img, 0, 0);
    const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const pixels = imgData.data;
    const w = canvas.width;
    const h = canvas.height;

    const getPixel = (px: number, py: number): [number, number, number] => {
      const x = Math.max(0, Math.min(w - 1, Math.floor(px)));
      const y = Math.max(0, Math.min(h - 1, Math.floor(py)));
      const idx = (y * w + x) * 4;
      return [pixels[idx], pixels[idx + 1], pixels[idx + 2]];
    };

    const median = (arr: number[]) => {
      const s = [...arr].sort((a, b) => a - b);
      return s[Math.floor(s.length / 2)];
    };

    for (const line of lines) {
      const lx = (line.x / 100) * w;
      const ly = (line.y / 100) * h;
      const lw = (line.width / 100) * w;
      const lh = (line.height / 100) * h;

      // Sample a 5x3 grid across the line region
      const samples: [number, number, number][] = [];
      for (const fx of [0.1, 0.3, 0.5, 0.7, 0.9]) {
        for (const fy of [0.15, 0.5, 0.85]) {
          samples.push(getPixel(lx + fx * lw, ly + fy * lh));
        }
      }

      const r = median(samples.map((s) => s[0]));
      const g = median(samples.map((s) => s[1]));
      const b = median(samples.map((s) => s[2]));

      const bg = `rgb(${r}, ${g}, ${b})`;
      const luminance = 0.299 * r + 0.587 * g + 0.114 * b;
      const textColor = luminance < 185 ? '#ffffff' : '#1a1510';

      colors.set(line.lineIndex, { bg, textColor });
    }
  } catch {
    // Canvas access failed — keep empty map, component will use fallback
  }

  return colors;
}

// --- OVERLAY COMPONENT ---

function EnglishOverlayPage({ page }: { page: TranslatedPage }) {
  const imgRef = useRef<HTMLImageElement>(null);
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgSize, setImgSize] = useState({ width: 0, height: 0 });
  const [lineColors, setLineColors] = useState<Map<number, LineColor>>(
    new Map()
  );

  useEffect(() => {
    if (imgRef.current && imgLoaded) {
      const update = () => {
        if (imgRef.current) {
          setImgSize({
            width: imgRef.current.clientWidth,
            height: imgRef.current.clientHeight,
          });
        }
      };
      update();
      const observer = new ResizeObserver(update);
      observer.observe(imgRef.current);
      return () => observer.disconnect();
    }
  }, [imgLoaded]);

  // Sample bg color per line from canvas once image loads
  useEffect(() => {
    if (imgRef.current && imgLoaded && page.lines.length > 0) {
      const colors = sampleLineColors(imgRef.current, page.lines);
      if (colors.size > 0) setLineColors(colors);
    }
  }, [imgLoaded, page.lines]);

  if (!page.translation || !page.lines.length) return null;

  // Filter and sort OCR lines
  const textLines = page.lines
    .filter((l) => l.width > 1 && l.height > 0.3)
    .sort((a, b) => a.lineIndex - b.lineIndex);

  // Parse translation into flow tokens
  const tokens = tokenizeTranslation(page.translation.englishOutput);

  let flowLines: FlowLine[] = [];
  let computedFontSize = 12;

  if (imgSize.width > 0 && textLines.length > 0) {
    // Base font size from median line height
    const heights = textLines
      .map((l) => (l.height / 100) * imgSize.height)
      .sort((a, b) => a - b);
    const medianH = heights[Math.floor(heights.length / 2)];
    computedFontSize = Math.max(8, medianH * 0.65);

    // Flow text, progressively shrink font if overflow
    let result = flowTextToLines(
      textLines,
      tokens,
      imgSize.width,
      computedFontSize
    );
    let attempts = 0;
    while (result.overflow && attempts < 20) {
      computedFontSize *= 0.88;
      if (computedFontSize < 3) break;
      result = flowTextToLines(
        textLines,
        tokens,
        imgSize.width,
        computedFontSize
      );
      attempts++;
    }
    flowLines = result.flowLines;
  }

  const defaultBg = '#f5ead6';
  const defaultTextColor = '#1a1510';

  return (
    <div className="relative inline-block w-full">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        ref={imgRef}
        src={`/api/pages/${page.id}/image`}
        alt={`Page ${page.pageNumber}`}
        className="w-full h-auto block"
        onLoad={() => setImgLoaded(true)}
      />

      {imgLoaded && imgSize.width > 0 && (
        <div className="absolute inset-0" style={{ pointerEvents: 'none' }}>
          {flowLines.map(({ line, spans }, idx) => {
            const colors = lineColors.get(line.lineIndex);
            const bg = colors?.bg || defaultBg;
            const textColor = colors?.textColor || defaultTextColor;

            return (
              <div
                key={`line-${idx}`}
                style={{
                  position: 'absolute',
                  left: `${line.x}%`,
                  top: `${line.y}%`,
                  width: `${line.width}%`,
                  height: `${line.height}%`,
                  backgroundColor: bg,
                  overflow: 'hidden',
                  display: 'flex',
                  alignItems: 'center',
                  padding: '0 2px',
                }}
              >
                {spans.map((span, si) => (
                  <span
                    key={si}
                    style={{
                      fontFamily:
                        'Georgia, "Times New Roman", "Palatino Linotype", serif',
                      fontSize: `${computedFontSize}px`,
                      fontWeight: span.bold ? 700 : 400,
                      color: textColor,
                      lineHeight: 1.1,
                      whiteSpace: 'pre',
                    }}
                  >
                    {span.text}
                  </span>
                ))}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// --- MAIN PAGE COMPONENT ---

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
    book?.pages.filter((p) => p.translation && p.translation.englishOutput) ||
    [];

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
    const allEnglish = translatedPages.every(
      (p) => showEnglish[p.pageNumber]
    );
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
          <svg
            className="animate-spin w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
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
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 19l-7-7 7-7"
                />
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
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
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
