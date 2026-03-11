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
  // These are already visible in the original Hebrew banner
  const isHeaderLine = (s: string) =>
    /^\d{1,3}\.?$/.test(s) ||
    /^(Introduction|Summary|Yechezkel Perek|Main Topics)/i.test(s);

  // First paragraph may contain header lines joined by \n — strip them
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
  // Also skip any subsequent standalone header paragraphs
  while (rawParas.length > 0) {
    const line = rawParas[0].replace(/\*\*/g, '').trim();
    if (isHeaderLine(line)) { rawParas.shift(); continue; }
    break;
  }
  for (let i = 0; i < rawParas.length; i++) {
    const para = rawParas[i];
    // Strip markdown formatting for display
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

// --- ASSIGN PARAGRAPHS TO TEXT REGIONS ---

function assignParagraphsToRegions(
  regions: LayoutRegion[],
  paragraphs: Paragraph[],
  ocrLines: OcrLine[]
): Map<number, Paragraph[]> {
  const result = new Map<number, Paragraph[]>();
  const textRegionIndices: number[] = [];

  // Find text regions (skip header, illustration, chart)
  regions.forEach((r, i) => {
    if (r.type === 'text' || r.type === 'table') {
      textRegionIndices.push(i);
    }
  });

  if (textRegionIndices.length === 0 || paragraphs.length === 0) return result;

  // Count Hebrew chars per text region (from OCR lines that fall within it)
  const hebrewCharsPerRegion: number[] = textRegionIndices.map((ri) => {
    const r = regions[ri];
    return ocrLines.filter((l) => {
      const midY = l.y + l.height / 2;
      const midX = l.x + l.width / 2;
      return (
        midY >= r.y && midY <= r.y + r.height &&
        midX >= r.x && midX <= r.x + r.width
      );
    }).reduce((s, l) => s + l.text.length, 0);
  });

  const totalHebrew = hebrewCharsPerRegion.reduce((s, c) => s + c, 0);
  if (totalHebrew === 0) {
    // Fallback: distribute evenly
    const perRegion = Math.ceil(paragraphs.length / textRegionIndices.length);
    let pi = 0;
    for (const ri of textRegionIndices) {
      result.set(ri, paragraphs.slice(pi, pi + perRegion));
      pi += perRegion;
    }
    return result;
  }

  // Proportional distribution with cumulative targets
  const totalEnglish = paragraphs.reduce((s, p) => s + p.charCount, 0);
  const targets: number[] = [];
  let cumHebrew = 0;
  for (const chars of hebrewCharsPerRegion) {
    cumHebrew += chars;
    targets.push((cumHebrew / totalHebrew) * totalEnglish);
  }

  // Initialize empty arrays
  for (const ri of textRegionIndices) result.set(ri, []);

  let tzi = 0;
  let runEng = 0;
  for (const para of paragraphs) {
    while (tzi < textRegionIndices.length - 1 && runEng > 0 && runEng >= targets[tzi]) {
      tzi++;
    }
    result.get(textRegionIndices[tzi])!.push(para);
    runEng += para.charCount;
  }

  return result;
}

// --- FALLBACK: Create text regions from OCR lines (no layout data) ---

function createFallbackRegions(lines: OcrLine[]): LayoutRegion[] {
  const regions: LayoutRegion[] = [];

  // Header: lines in top 5%
  const headerLines = lines.filter((l) => l.y < 5);
  if (headerLines.length > 0) {
    regions.push({ type: 'header', x: 0, y: 0, width: 100, height: 5 });
  }

  // Body: everything else as one text region
  const bodyLines = lines.filter((l) => l.y >= 5);
  if (bodyLines.length > 0) {
    const minX = Math.min(...bodyLines.map((l) => l.x));
    const minY = Math.min(...bodyLines.map((l) => l.y));
    const maxX = Math.max(...bodyLines.map((l) => l.x + l.width));
    const maxY = Math.max(...bodyLines.map((l) => l.y + l.height));
    regions.push({
      type: 'text',
      x: Math.max(2, minX - 2),
      y: minY,
      width: Math.min(96, maxX - minX + 4),
      height: maxY - minY + 2,
    });
  }

  return regions;
}

// --- GAP FILLING: Close gaps between subtitle/header bottom and text top ---

function fillRegionGaps(regions: LayoutRegion[]): LayoutRegion[] {
  if (regions.length === 0) return regions;

  // Sort by y position
  const sorted = [...regions].sort((a, b) => a.y - b.y);
  const result = regions.map((r) => ({ ...r }));

  for (let i = 0; i < sorted.length; i++) {
    const curr = sorted[i];
    if (curr.type !== 'text' && curr.type !== 'table') continue;

    // Find the region immediately above this text region
    let closestAbove: LayoutRegion | null = null;
    let closestAboveBottom = 0;
    for (let j = 0; j < sorted.length; j++) {
      if (j === i) continue;
      const other = sorted[j];
      const otherBottom = other.y + other.height;
      if (otherBottom <= curr.y + 1 && otherBottom > closestAboveBottom) {
        closestAbove = other;
        closestAboveBottom = otherBottom;
      }
    }

    // If there's a gap of 1-5% between the region above and this text region, extend text upward
    if (closestAbove) {
      const gap = curr.y - closestAboveBottom;
      if (gap > 0.2 && gap < 5) {
        // Find the matching region in result array and extend it
        const ri = result.findIndex((r) => r.y === curr.y && r.x === curr.x && r.type === curr.type);
        if (ri >= 0) {
          result[ri].height += result[ri].y - closestAboveBottom;
          result[ri].y = closestAboveBottom;
        }
      }
    }
  }

  return result;
}

// --- ENGLISH OVERLAY PAGE COMPONENT ---

function EnglishOverlayPage({ page }: { page: TranslatedPage }) {
  const [analyzing, setAnalyzing] = useState(false);
  const [regions, setRegions] = useState<LayoutRegion[] | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerW, setContainerW] = useState(900);
  const [imgAspect, setImgAspect] = useState(2340 / 1655); // default, updated on load

  // Measure actual container width for font sizing
  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) setContainerW(e.contentRect.width);
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  // Trigger layout analysis if needed (only when translation exists)
  useEffect(() => {
    if (!page.translation?.englishOutput || page.lines.length === 0) return;
    if (page.layout?.regions) {
      setRegions(page.layout.regions as LayoutRegion[]);
      return;
    }
    let cancelled = false;
    setAnalyzing(true);
    fetch(`/api/pages/${page.id}/layout`, { method: 'POST' })
      .then((res) => res.json())
      .then((data) => {
        if (cancelled) return;
        if (data.regions) setRegions(data.regions as LayoutRegion[]);
        else setRegions(createFallbackRegions(page.lines));
      })
      .catch(() => { if (!cancelled) setRegions(createFallbackRegions(page.lines)); })
      .finally(() => { if (!cancelled) setAnalyzing(false); });
    return () => { cancelled = true; };
  }, [page]);

  const hasContent = !!(page.translation?.englishOutput && page.lines.length > 0);

  const paragraphs = useMemo(
    () => hasContent ? parseTranslation(page.translation!.englishOutput) : [],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [page.translation, hasContent]
  );
  const activeRegions = useMemo(
    () => hasContent ? fillRegionGaps(regions || createFallbackRegions(page.lines)) : [],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [regions, page.lines, hasContent]
  );
  const paraMap = useMemo(
    () => hasContent ? assignParagraphsToRegions(activeRegions, paragraphs, page.lines) : new Map<number, Paragraph[]>(),
    [activeRegions, paragraphs, page.lines, hasContent]
  );

  const containerH = containerW * imgAspect;

  if (!hasContent) {
    // Show Hebrew image as fallback instead of blank
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

  // Don't render overlays until container is measured (prevents NaN font sizes)
  const ready = containerW > 0 && !analyzing;

  return (
    <div className="w-full relative" ref={containerRef}>
      {analyzing && (
        <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none">
          <div className="bg-black/70 text-white text-sm px-4 py-2 rounded-lg flex items-center gap-2">
            <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Analyzing layout...
          </div>
        </div>
      )}

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

        {/* White overlays ONLY on text/table regions — everything else untouched */}
        {ready && (
          <div className="absolute inset-0">
            {activeRegions.map((region, ri) => {
              // Only overlay text and table regions
              if (region.type !== 'text' && region.type !== 'table') return null;

              const paras = paraMap.get(ri);
              if (!paras || paras.length === 0) return null;

              // Font sizing in pixels based on actual container width
              const totalChars = paras.reduce((s, p) => s + p.charCount, 0);
              const regionWPx = (region.width / 100) * containerW;
              const regionHPx = (region.height / 100) * containerH;
              // Target: 15px at 900px container, scale proportionally
              const targetPx = containerW * 0.017;
              // Check if text fits at target size
              const charsPerLine = regionWPx / (targetPx * 0.52);
              const linesNeeded = totalChars / Math.max(charsPerLine, 1);
              const linesAvailable = regionHPx / (targetPx * 1.3);
              // Scale down if needed, but never below 12px
              const fontPx = linesNeeded > linesAvailable
                ? Math.max(12, targetPx * (linesAvailable / linesNeeded))
                : targetPx;

              const isTable = region.type === 'table';

              return (
                <div
                  key={ri}
                  className="absolute overflow-hidden"
                  style={{
                    left: `${Math.max(0, region.x - 1.0)}%`,
                    top: `${Math.max(0, region.y - 0.5)}%`,
                    width: `${Math.min(100, region.width + 2.0)}%`,
                    height: `${region.height + 0.5}%`,
                    backgroundColor: 'white',
                    padding: '0.4em',
                    direction: 'ltr',
                  }}
                >
                  {paras.map((para, pi) => (
                    <p
                      key={pi}
                      style={{
                        fontSize: `${isTable ? Math.max(10, fontPx * 0.85) : fontPx}px`,
                        fontFamily: isTable
                          ? '"Courier New", Courier, monospace'
                          : 'Georgia, "Times New Roman", serif',
                        color: '#1a1510',
                        fontWeight: para.isAllBold ? 700 : 400,
                        textAlign: para.isAllBold ? 'center' : 'left',
                        marginBottom: pi < paras.length - 1 ? (isTable ? '0.2em' : '0.4em') : 0,
                        lineHeight: isTable ? 1.2 : 1.3,
                        whiteSpace: isTable ? 'pre-wrap' : 'normal',
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
