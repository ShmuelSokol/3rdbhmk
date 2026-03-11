'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useRouter, useParams } from 'next/navigation';

// --- TYPES ---

interface OcrLine {
  lineIndex: number;
  x: number;
  y: number;
  width: number;
  height: number;
  text: string;
}

interface LayoutRegion {
  type: 'text' | 'illustration' | 'header' | 'subtitle' | 'table' | 'chart';
  x: number;
  y: number;
  width: number;
  height: number;
  label?: string;
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
  layout: {
    id: string;
    regions: LayoutRegion[];
  } | null;
  lines: OcrLine[];
}

interface BookData {
  id: string;
  name: string;
  totalPages: number;
  pages: TranslatedPage[];
}

// --- PARAGRAPH PARSING ---

interface Paragraph {
  text: string;
  isAllBold: boolean;
  charCount: number;
}

function parseTranslation(raw: string): Paragraph[] {
  const paragraphs: Paragraph[] = [];
  const rawParas = raw.split(/\r?\n\s*\r?\n/).map((p) => p.trim()).filter(Boolean);

  // Strip leading header lines from first paragraph: page number + running headers
  const isHeaderLine = (s: string) =>
    /^\d{1,3}\.?$/.test(s) ||
    /^(Introduction|Summary|Yechezkel Perek|Main Topics)/i.test(s);

  if (rawParas.length > 0) {
    const lines = rawParas[0].split('\n').map((l) => l.replace(/\*\*/g, '').trim());
    let skipCount = 0;
    for (const line of lines) {
      if (!line || isHeaderLine(line)) { skipCount++; continue; }
      break;
    }
    if (skipCount > 0) {
      const remaining = rawParas[0].split('\n').slice(skipCount).join('\n').trim();
      if (remaining) {
        rawParas[0] = remaining;
      } else {
        rawParas.shift();
      }
    }
  }
  while (rawParas.length > 0) {
    const line = rawParas[0].replace(/\*\*/g, '').trim();
    if (isHeaderLine(line)) { rawParas.shift(); continue; }
    break;
  }
  for (let i = 0; i < rawParas.length; i++) {
    const para = rawParas[i];
    const text = para
      .replace(/\*\*([\s\S]*?)\*\*/g, '$1')
      .replace(/\n/g, ' ')
      .replace(/^#+\s+/gm, '')
      .replace(/`([^`]+)`/g, '$1')
      .trim();
    if (!text) continue;

    const isAllBold = para.startsWith('**') && para.endsWith('**');
    paragraphs.push({ text, isAllBold, charCount: text.length });
  }
  return paragraphs;
}

// --- OCR-BASED TEXT BLOCK GROUPING ---

interface TextBlock {
  x: number;
  y: number;
  width: number;
  height: number;
  hebrewCharCount: number;
}

function groupOcrLinesIntoBlocks(lines: OcrLine[], headerThreshold: number = 4): TextBlock[] {
  // Filter out header lines (top ~4% of page)
  const bodyLines = lines
    .filter((l) => l.y >= headerThreshold)
    .sort((a, b) => a.y - b.y);

  if (bodyLines.length === 0) return [];

  // Group lines into contiguous blocks — a gap > 3% starts a new block
  const GAP_THRESHOLD = 3;
  const groups: OcrLine[][] = [];
  let currentGroup: OcrLine[] = [bodyLines[0]];

  for (let i = 1; i < bodyLines.length; i++) {
    const prev = currentGroup[currentGroup.length - 1];
    const prevBottom = prev.y + prev.height;
    const gap = bodyLines[i].y - prevBottom;

    if (gap > GAP_THRESHOLD) {
      groups.push(currentGroup);
      currentGroup = [bodyLines[i]];
    } else {
      currentGroup.push(bodyLines[i]);
    }
  }
  groups.push(currentGroup);

  // Convert each group into a text block bounding rectangle
  return groups.map((group) => {
    const minX = Math.min(...group.map((l) => l.x));
    const minY = Math.min(...group.map((l) => l.y));
    const maxX = Math.max(...group.map((l) => l.x + l.width));
    const maxY = Math.max(...group.map((l) => l.y + l.height));
    const hebrewCharCount = group.reduce((s, l) => s + l.text.length, 0);

    return {
      x: minX,
      y: minY,
      width: maxX - minX,
      height: maxY - minY,
      hebrewCharCount,
    };
  });
}

function assignParagraphsToBlocks(
  blocks: TextBlock[],
  paragraphs: Paragraph[]
): Map<number, Paragraph[]> {
  const result = new Map<number, Paragraph[]>();
  if (blocks.length === 0 || paragraphs.length === 0) return result;

  // Initialize empty arrays for each block
  for (let i = 0; i < blocks.length; i++) result.set(i, []);

  const totalHebrew = blocks.reduce((s, b) => s + b.hebrewCharCount, 0);
  if (totalHebrew === 0) {
    // Fallback: distribute evenly
    const perBlock = Math.ceil(paragraphs.length / blocks.length);
    let pi = 0;
    for (let i = 0; i < blocks.length; i++) {
      result.set(i, paragraphs.slice(pi, pi + perBlock));
      pi += perBlock;
    }
    return result;
  }

  // Proportional distribution based on Hebrew char counts
  const totalEnglish = paragraphs.reduce((s, p) => s + p.charCount, 0);
  const targets: number[] = [];
  let cumHebrew = 0;
  for (const block of blocks) {
    cumHebrew += block.hebrewCharCount;
    targets.push((cumHebrew / totalHebrew) * totalEnglish);
  }

  let bi = 0;
  let runEng = 0;
  for (const para of paragraphs) {
    while (bi < blocks.length - 1 && runEng > 0 && runEng >= targets[bi]) {
      bi++;
    }
    result.get(bi)!.push(para);
    runEng += para.charCount;
  }

  return result;
}

// --- ENGLISH OVERLAY PAGE COMPONENT ---

function EnglishOverlayPage({ page }: { page: TranslatedPage }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerW, setContainerW] = useState(900);
  const [imgAspect, setImgAspect] = useState(2340 / 1655);

  // Measure actual container width for font sizing
  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) setContainerW(e.contentRect.width);
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const hasContent = !!(page.translation?.englishOutput && page.lines.length > 0);

  const paragraphs = useMemo(
    () => hasContent ? parseTranslation(page.translation!.englishOutput) : [],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [page.translation, hasContent]
  );

  const textBlocks = useMemo(
    () => hasContent ? groupOcrLinesIntoBlocks(page.lines) : [],
    [page.lines, hasContent]
  );

  const paraMap = useMemo(
    () => hasContent ? assignParagraphsToBlocks(textBlocks, paragraphs) : new Map<number, Paragraph[]>(),
    [textBlocks, paragraphs, hasContent]
  );

  const containerH = containerW * imgAspect;

  if (!hasContent) {
    return (
      <div className="w-full relative">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`/api/pages/${page.id}/image`}
          alt={`Page ${page.pageNumber}`}
          className="w-full h-auto block"
          loading="lazy"
        />
      </div>
    );
  }

  const ready = containerW > 0;

  return (
    <div className="w-full relative" ref={containerRef}>
      {/* Original page image — fully visible as base */}
      <div className="relative w-full" style={{ aspectRatio: 'auto' }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`/api/pages/${page.id}/image`}
          alt={`Page ${page.pageNumber}`}
          className="w-full h-auto block"
          loading="lazy"
          onLoad={(e) => {
            const img = e.currentTarget;
            if (img.naturalWidth > 0) {
              setImgAspect(img.naturalHeight / img.naturalWidth);
            }
          }}
        />

        {/* White overlays positioned exactly at OCR text block locations */}
        {ready && (
          <div className="absolute inset-0">
            {textBlocks.map((block, bi) => {
              const paras = paraMap.get(bi);
              if (!paras || paras.length === 0) return null;

              // Font sizing based on container width and available space
              const totalChars = paras.reduce((s, p) => s + p.charCount, 0);
              const blockWPx = (block.width / 100) * containerW;
              const blockHPx = (block.height / 100) * containerH;
              const targetPx = containerW * 0.017;
              const charsPerLine = blockWPx / (targetPx * 0.52);
              const linesNeeded = totalChars / Math.max(charsPerLine, 1);
              const linesAvailable = blockHPx / (targetPx * 1.3);
              const fontPx = linesNeeded > linesAvailable
                ? Math.max(10, targetPx * (linesAvailable / linesNeeded))
                : targetPx;

              return (
                <div
                  key={bi}
                  className="absolute overflow-hidden"
                  style={{
                    left: `${Math.max(0, block.x - 1)}%`,
                    top: `${block.y}%`,
                    width: `${Math.min(100, block.width + 2)}%`,
                    height: `${block.height}%`,
                    backgroundColor: 'white',
                    padding: '0.3em',
                    direction: 'ltr',
                  }}
                >
                  {paras.map((para, pi) => (
                    <p
                      key={pi}
                      style={{
                        fontSize: `${fontPx}px`,
                        fontFamily: 'Georgia, "Times New Roman", serif',
                        color: '#1a1510',
                        fontWeight: para.isAllBold ? 700 : 400,
                        textAlign: para.isAllBold ? 'center' : 'left',
                        marginBottom: pi < paras.length - 1 ? '0.4em' : 0,
                        lineHeight: 1.3,
                      }}
                    >
                      {para.text}
                    </p>
                  ))}
                </div>
              );
            })}
          </div>
        )}
      </div>
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
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const togglePage = (pageNumber: number) => {
    setShowEnglish((prev) => ({ ...prev, [pageNumber]: !prev[pageNumber] }));
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

          <div className="flex items-center gap-2 flex-wrap justify-end">
            <button
              onClick={toggleAll}
              className="px-3 py-1.5 rounded-lg bg-[#2e2f3a] border border-[#3e3f4a] text-[#e4e4e7] text-xs sm:text-sm hover:bg-[#3e3f4a] transition-colors whitespace-nowrap"
            >
              {translatedPages.every((p) => showEnglish[p.pageNumber])
                ? 'Show All Hebrew'
                : 'Show All English'}
            </button>

            {translatedPages.length > 0 && (
              <select
                onChange={(e) => jumpToPage(Number(e.target.value))}
                defaultValue=""
                className="px-2 py-1.5 rounded-lg bg-[#2e2f3a] border border-[#3e3f4a] text-[#e4e4e7] text-xs sm:text-sm focus:outline-none max-w-[130px] sm:max-w-none"
              >
                <option value="" disabled>Jump to page...</option>
                {translatedPages.map((p) => (
                  <option key={p.id} value={p.pageNumber}>
                    Page {p.pageNumber}
                  </option>
                ))}
              </select>
            )}

            <a
              href={`/api/books/${bookId}/export`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#3b82f6] hover:bg-[#2563eb] text-white text-xs sm:text-sm font-medium transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              PDF
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-[900px] mx-auto px-6 py-8 space-y-10">
        {translatedPages.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-[#a8a29e] text-lg">No translated pages yet.</p>
          </div>
        ) : (
          translatedPages.map((page) => (
            <div
              key={page.id}
              ref={(el) => { rowRefs.current[page.pageNumber] = el; }}
              className="scroll-mt-20"
            >
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
