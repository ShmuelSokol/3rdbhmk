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
 * Parse translation text into paragraphs with bold information from markdown.
 */
interface ParsedParagraph {
  text: string;
  isBold: boolean;
}

function parseTranslation(raw: string): ParsedParagraph[] {
  const paragraphs = raw.split(/\n\s*\n/);
  const result: ParsedParagraph[] = [];

  for (const para of paragraphs) {
    const trimmed = para.trim();
    if (!trimmed) continue;

    // Check if entire paragraph is bold (**...**)
    const boldMatch = trimmed.match(/^\*\*([\s\S]+?)\*\*$/);
    if (boldMatch) {
      result.push({ text: boldMatch[1].trim(), isBold: true });
    } else {
      const clean = trimmed
        .replace(/\*\*([^*]+)\*\*/g, '$1')
        .replace(/\*([^*]+)\*/g, '$1')
        .replace(/^#+\s+/gm, '')
        .replace(/`([^`]+)`/g, '$1');
      result.push({ text: clean, isBold: false });
    }
  }

  return result;
}

/**
 * A text block groups consecutive OCR lines of the same type (header or body).
 */
interface TextBlock {
  lines: OcrLine[];
  x: number;
  y: number;
  width: number;
  height: number;
  isHeader: boolean;
  isCentered: boolean;
}

/**
 * Group OCR lines into text blocks.
 * Header lines (large or narrow-centered) form their own blocks.
 * Consecutive body lines merge into body blocks.
 */
function groupLinesIntoBlocks(lines: OcrLine[]): TextBlock[] {
  const textLines = lines.filter(l => l.width > 1 && l.height > 0.3);
  if (textLines.length === 0) return [];

  // Sort by lineIndex to preserve OCR reading order (not y-position)
  const sorted = [...textLines].sort((a, b) => a.lineIndex - b.lineIndex);
  const heights = sorted.map(l => l.height).sort((a, b) => a - b);
  const medianHeight = heights[Math.floor(heights.length / 2)];

  const blocks: TextBlock[] = [];
  let bodyGroup: OcrLine[] = [];

  const flushBody = () => {
    if (bodyGroup.length === 0) return;
    const g = bodyGroup;
    const minX = Math.min(...g.map(l => l.x));
    const minY = Math.min(...g.map(l => l.y));
    const maxX = Math.max(...g.map(l => l.x + l.width));
    const maxY = Math.max(...g.map(l => l.y + l.height));
    const avgCx = g.reduce((s, l) => s + l.x + l.width / 2, 0) / g.length;
    const avgW = g.reduce((s, l) => s + l.width, 0) / g.length;
    blocks.push({
      lines: [...g],
      x: minX, y: minY,
      width: maxX - minX, height: maxY - minY,
      isHeader: false,
      isCentered: Math.abs(avgCx - 50) < 10 && avgW < 60,
    });
    bodyGroup = [];
  };

  for (const line of sorted) {
    const lineCx = line.x + line.width / 2;
    const isCenteredNarrow = Math.abs(lineCx - 50) < 10 && line.width < 35;
    const isLargeText = line.height > medianHeight * 1.2;
    const isHeader = isLargeText || isCenteredNarrow;

    if (isHeader) {
      // Check if this header should merge with previous header block
      const prevBlock = blocks.length > 0 ? blocks[blocks.length - 1] : null;
      const prevIsHeader = prevBlock && prevBlock.isHeader;
      const isContiguous = prevBlock && (line.y - (prevBlock.y + prevBlock.height)) < medianHeight * 2;

      if (bodyGroup.length > 0) flushBody();

      // Only merge headers of similar height (e.g., multi-line title)
      const lastLineInPrev = prevBlock ? prevBlock.lines[prevBlock.lines.length - 1] : null;
      const similarHeight = lastLineInPrev
        ? Math.abs(line.height - lastLineInPrev.height) < medianHeight * 0.8
        : false;

      if (prevIsHeader && isContiguous && similarHeight) {
        // Merge with previous header block
        prevBlock.lines.push(line);
        const minX = Math.min(prevBlock.x, line.x);
        const maxX = Math.max(prevBlock.x + prevBlock.width, line.x + line.width);
        const maxY = line.y + line.height;
        prevBlock.x = minX;
        prevBlock.width = maxX - minX;
        prevBlock.height = maxY - prevBlock.y;
        // Recompute centered
        const allCx = prevBlock.lines.reduce((s, l) => s + l.x + l.width / 2, 0) / prevBlock.lines.length;
        const allW = prevBlock.lines.reduce((s, l) => s + l.width, 0) / prevBlock.lines.length;
        prevBlock.isCentered = Math.abs(allCx - 50) < 10 && allW < 75;
      } else {
        blocks.push({
          lines: [line],
          x: line.x, y: line.y,
          width: line.width, height: line.height,
          isHeader: true,
          isCentered: Math.abs(lineCx - 50) < 10,
        });
      }
    } else {
      // Body line — check for large gap from previous body line
      if (bodyGroup.length > 0) {
        const lastLine = bodyGroup[bodyGroup.length - 1];
        const gap = line.y - (lastLine.y + lastLine.height);
        if (gap > medianHeight * 3) flushBody();
      }
      bodyGroup.push(line);
    }
  }
  flushBody();

  return blocks;
}

/**
 * Assign translation paragraphs to text blocks sequentially.
 * Bold paragraphs go to header blocks; non-bold to body blocks.
 */
interface BlockAssignment {
  block: TextBlock;
  text: string;
  isBold: boolean;
  fontSize: number;
}

function assignTextToBlocks(
  blocks: TextBlock[],
  paragraphs: ParsedParagraph[],
  imgWidth: number,
  imgHeight: number
): BlockAssignment[] {
  const result: BlockAssignment[] = [];
  let paraIdx = 0;

  for (const block of blocks) {
    if (paraIdx >= paragraphs.length) {
      result.push({ block, text: '', isBold: false, fontSize: 12 });
      continue;
    }

    const widthPx = (block.width / 100) * imgWidth;
    const heightPx = (block.height / 100) * imgHeight;
    const avgLineH = block.lines.reduce((s, l) => s + l.height, 0) / block.lines.length;
    const avgLineHPx = (avgLineH / 100) * imgHeight;
    const baseFontSize = Math.max(8, avgLineHPx * 0.72);

    let text: string;
    let isBold: boolean;

    if (block.isHeader) {
      // Header: take one paragraph
      text = paragraphs[paraIdx].text;
      isBold = true; // Headers always bold
      paraIdx++;
    } else {
      // Body: take all remaining non-bold paragraphs (stop before next bold)
      const parts: string[] = [];
      while (paraIdx < paragraphs.length) {
        if (paragraphs[paraIdx].isBold && parts.length > 0) break;
        parts.push(paragraphs[paraIdx].text);
        paraIdx++;
      }
      text = parts.join('\n\n');
      isBold = false;
    }

    // Auto-size font to fit text in the block area
    let fontSize = baseFontSize;
    if (text.length > 0 && widthPx > 0 && heightPx > 0) {
      const CW = 0.55; // char width ratio
      const LH = block.isHeader ? 1.25 : 1.45; // line height ratio

      // How many chars fit at baseFontSize?
      const charsPerLine = widthPx / (baseFontSize * CW);
      const maxLines = Math.max(1, Math.floor(heightPx / (baseFontSize * LH)));
      const capacity = charsPerLine * maxLines;

      if (text.length > capacity) {
        // Shrink: f = sqrt(W * H / (chars * CW * LH)) with safety margin
        const fitted = Math.sqrt((widthPx * heightPx) / (text.length * CW * LH));
        fontSize = Math.max(6, fitted * 0.88);
      }
    }

    result.push({ block, text, isBold, fontSize });
  }

  return result;
}

function EnglishOverlayPage({ page }: { page: TranslatedPage }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgSize, setImgSize] = useState({ width: 0, height: 0 });
  const [bgColor, setBgColor] = useState('#f5ead6');

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

  // Sample background color from gaps between OCR text lines
  useEffect(() => {
    if (imgRef.current && imgLoaded && page.lines.length > 1) {
      try {
        const img = imgRef.current;
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        if (ctx && img.naturalWidth > 0) {
          canvas.width = img.naturalWidth;
          canvas.height = img.naturalHeight;
          ctx.drawImage(img, 0, 0);
          const w = canvas.width;
          const h = canvas.height;

          // Find gaps between consecutive text lines and sample from there
          const textLines = page.lines
            .filter((l) => l.width > 3 && l.height > 0.5)
            .sort((a, b) => a.y - b.y);

          const samples: number[][] = [];
          for (let i = 0; i < textLines.length - 1; i++) {
            const lineBottom = (textLines[i].y + textLines[i].height) / 100;
            const nextLineTop = textLines[i + 1].y / 100;
            const gap = nextLineTop - lineBottom;
            if (gap > 0.002) {
              // Sample the midpoint of the gap, at the horizontal center of the line
              const sampleY = (lineBottom + nextLineTop) / 2;
              const sampleX = (textLines[i].x + textLines[i].width / 2) / 100;
              const px = Math.floor(sampleX * w);
              const py = Math.floor(sampleY * h);
              if (px > 0 && px < w && py > 0 && py < h) {
                const data = ctx.getImageData(px, py, 1, 1).data;
                // Only include light-colored samples (skip dark text remnants)
                if (data[0] > 180 && data[1] > 160 && data[2] > 130) {
                  samples.push([data[0], data[1], data[2]]);
                }
              }
            }
          }

          if (samples.length >= 3) {
            // Use median of each channel
            const getMedian = (arr: number[]) => {
              const sorted = [...arr].sort((a, b) => a - b);
              const mid = Math.floor(sorted.length / 2);
              return sorted.length % 2 ? sorted[mid] : Math.round((sorted[mid - 1] + sorted[mid]) / 2);
            };
            const r = getMedian(samples.map((s) => s[0]));
            const g = getMedian(samples.map((s) => s[1]));
            const b = getMedian(samples.map((s) => s[2]));
            setBgColor(`rgb(${r}, ${g}, ${b})`);
          }
        }
      } catch {
        // CORS or other error, keep fallback color
      }
    }
  }, [imgLoaded, page.lines]);

  if (!page.translation || !page.lines.length) return null;

  // Build text blocks and assign translated text
  const blocks = imgSize.width > 0 ? groupLinesIntoBlocks(page.lines) : [];
  const paragraphs = page.translation ? parseTranslation(page.translation.englishOutput) : [];
  const assignments = imgSize.width > 0
    ? assignTextToBlocks(blocks, paragraphs, imgSize.width, imgSize.height)
    : [];

  return (
    <div ref={containerRef} className="relative inline-block w-full">
      {/* Original page image as base */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        ref={imgRef}
        src={`/api/pages/${page.id}/image`}
        alt={`Page ${page.pageNumber}`}
        className="w-full h-auto block"
        onLoad={() => setImgLoaded(true)}
      />

      {/* Overlay: English text blocks at OCR positions */}
      {imgLoaded && imgSize.width > 0 && (
        <div className="absolute inset-0" style={{ pointerEvents: 'none' }}>
          {assignments.map(({ block, text, isBold, fontSize }, idx) => (
            <div
              key={`block-${idx}`}
              style={{
                position: 'absolute',
                left: `${block.x}%`,
                top: `${block.y}%`,
                width: `${block.width}%`,
                height: `${block.height}%`,
                backgroundColor: bgColor,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: block.isHeader ? 'center' : 'flex-start',
                alignItems: block.isCentered ? 'center' : 'stretch',
                padding: block.isHeader ? '0 2px' : '0',
              }}
            >
              {text && (
                <span
                  style={{
                    fontFamily: 'Georgia, "Times New Roman", "Palatino Linotype", serif',
                    fontSize: `${fontSize}px`,
                    fontWeight: isBold ? 700 : 400,
                    lineHeight: block.isHeader ? 1.25 : 1.45,
                    color: '#1a1510',
                    direction: 'ltr',
                    textAlign: block.isCentered ? 'center' : 'left',
                    wordWrap: 'break-word',
                    overflowWrap: 'break-word',
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
