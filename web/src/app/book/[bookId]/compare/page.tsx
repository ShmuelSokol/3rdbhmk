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
  avgLineHeightPct?: number;
  centered?: boolean;
  isTableRegion?: boolean;
  columnDividers?: number[];
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

  const rawBlocks = groups.map((group) => {
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

  return rawBlocks;
}

function assignParagraphsToBlocks(
  blocks: TextBlock[],
  paragraphs: Paragraph[]
): Map<number, Paragraph[]> {
  const result = new Map<number, Paragraph[]>();
  if (blocks.length === 0 || paragraphs.length === 0) return result;

  for (let i = 0; i < blocks.length; i++) result.set(i, []);

  const totalHebrew = blocks.reduce((s, b) => s + b.hebrewCharCount, 0);
  if (totalHebrew === 0) {
    const perBlock = Math.ceil(paragraphs.length / blocks.length);
    let pi = 0;
    for (let i = 0; i < blocks.length; i++) {
      result.set(i, paragraphs.slice(pi, pi + perBlock));
      pi += perBlock;
    }
    return result;
  }

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

// --- SECOND PASS: Optimize font sizes per block ---

interface BlockLayout {
  blockIndex: number;
  fontPx: number;
  paras: Paragraph[];
  block: TextBlock;
}

function computeBlockLayouts(
  blocks: TextBlock[],
  paraMap: Map<number, Paragraph[]>,
  containerW: number,
  containerH: number
): BlockLayout[] {
  const layouts: BlockLayout[] = [];

  for (let bi = 0; bi < blocks.length; bi++) {
    const block = blocks[bi];
    const paras = paraMap.get(bi) || [];
    if (paras.length === 0) continue;

    const totalChars = paras.reduce((s, p) => s + p.charCount, 0);
    const blockWPx = (block.width / 100) * containerW;
    const blockHPx = (block.height / 100) * containerH;

    // Upper bound: original Hebrew line height (converted to pixels)
    const hebrewLinePx = block.avgLineHeightPct
      ? (block.avgLineHeightPct / 100) * containerH * 0.75 // line height to font size (~75%)
      : 30;
    const maxFontPx = hebrewLinePx;

    // Binary search for the largest font that fits within the available space
    let lo = 4;
    let hi = maxFontPx;
    let bestFit = lo;

    for (let iter = 0; iter < 15; iter++) {
      const mid = (lo + hi) / 2;
      const charsPerLine = blockWPx / (mid * 0.52);
      const paraGapPx = mid * 0.4 * Math.max(0, paras.length - 1);
      const linesNeeded = totalChars / Math.max(charsPerLine, 1);
      const totalTextH = linesNeeded * (mid * 1.3) + paraGapPx;

      if (totalTextH <= blockHPx * 0.92) {
        bestFit = mid;
        lo = mid;
      } else {
        hi = mid;
      }
    }

    layouts.push({ blockIndex: bi, fontPx: bestFit, paras, block });
  }

  return layouts;
}

// --- ENGLISH OVERLAY PAGE COMPONENT ---

// Render a table region block
function TableRegionOverlay({
  block, rawText, containerW, containerH,
}: {
  block: TextBlock;
  rawText: string;
  containerW: number;
  containerH: number;
}) {
  const lines = rawText.split('\n').map((l) => l.trim()).filter(Boolean);
  const blockWPx = (block.width / 100) * containerW;
  const blockHPx = (block.height / 100) * containerH;

  // Compute column widths from dividers (as percentages of block width)
  const dividers = block.columnDividers || [];
  const blockLeft = block.x;
  const blockRight = block.x + block.width;
  // Column edges: [blockLeft, divider1, divider2, ..., blockRight]
  const edges = [blockLeft, ...dividers, blockRight];
  const colWidths = edges.slice(1).map((e, i) => e - edges[i]);
  const totalColW = colWidths.reduce((s, w) => s + w, 0);

  // Binary search for font size that fits, accounting for line wrapping
  let lo = 4, hi = containerW * 0.016, bestFit = lo;
  for (let iter = 0; iter < 15; iter++) {
    const mid = (lo + hi) / 2;
    const charsPerLine = blockWPx / (mid * 0.55);
    let totalVisualLines = 0;
    for (const line of lines) {
      const cleanLine = line.replace(/\*\*/g, '').replace(/^#+\s+/, '');
      totalVisualLines += Math.max(1, Math.ceil(cleanLine.length / Math.max(charsPerLine, 1)));
    }
    const totalH = totalVisualLines * (mid * 1.35);
    if (totalH <= blockHPx) { bestFit = mid; lo = mid; } else { hi = mid; }
  }
  const fontSize = Math.max(5, bestFit);

  return (
    <div
      className="absolute"
      style={{
        left: `${block.x}%`,
        top: `${block.y}%`,
        width: `${block.width}%`,
        height: `${block.height}%`,
        direction: 'ltr',
        padding: '0.2em',
        overflow: 'hidden',
      }}
    >
      {lines.map((line, li) => {
        const isBold = line.startsWith('**') && line.endsWith('**');
        const cleanLine = line.replace(/\*\*/g, '').replace(/^#+\s+/, '');
        const hasPipe = cleanLine.includes('|');

        if (hasPipe && dividers.length > 0) {
          const cols = cleanLine.split('|').map((c) => c.trim());
          return (
            <div
              key={li}
              style={{
                display: 'flex',
                fontSize: `${fontSize}px`,
                fontFamily: '"Courier New", Courier, monospace',
                color: '#1a1510',
                lineHeight: 1.3,
                marginBottom: '0.1em',
              }}
            >
              {cols.map((col, ci) => {
                // Size each column proportional to the detected grid widths
                const colW = ci < colWidths.length ? colWidths[ci] : colWidths[colWidths.length - 1] || 1;
                const pct = totalColW > 0 ? (colW / totalColW) * 100 : 100 / cols.length;
                return (
                  <span
                    key={ci}
                    style={{
                      width: `${pct}%`,
                      flexShrink: 0,
                      paddingRight: '0.3em',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {col}
                  </span>
                );
              })}
            </div>
          );
        }

        if (hasPipe) {
          // Fallback: no dividers detected, use equal columns
          const cols = cleanLine.split('|').map((c) => c.trim());
          return (
            <div
              key={li}
              style={{
                display: 'flex',
                fontSize: `${fontSize}px`,
                fontFamily: '"Courier New", Courier, monospace',
                color: '#1a1510',
                lineHeight: 1.3,
                marginBottom: '0.1em',
              }}
            >
              {cols.map((col, ci) => (
                <span
                  key={ci}
                  style={{
                    flex: 1,
                    paddingRight: '0.3em',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {col}
                </span>
              ))}
            </div>
          );
        }

        return (
          <p
            key={li}
            style={{
              fontSize: `${isBold ? fontSize * 1.1 : fontSize}px`,
              fontFamily: 'Georgia, "Times New Roman", serif',
              color: '#1a1510',
              fontWeight: isBold ? 700 : 400,
              textAlign: isBold ? 'center' : 'left',
              marginBottom: '0.3em',
              lineHeight: 1.3,
            }}
          >
            {cleanLine}
          </p>
        );
      })}
    </div>
  );
}

function EnglishOverlayPage({ page }: { page: TranslatedPage }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerW, setContainerW] = useState(900);
  const [imgAspect, setImgAspect] = useState(2340 / 1655);
  const [safeBlocks, setSafeBlocks] = useState<TextBlock[] | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) setContainerW(e.contentRect.width);
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!page.translation?.englishOutput || page.lines.length === 0) return;
    let cancelled = false;
    fetch(`/api/pages/${page.id}/text-blocks?v=4`)
      .then((res) => res.json())
      .then((data) => {
        if (cancelled) return;
        if (data.blocks) setSafeBlocks(data.blocks);
      })
      .catch(() => {
        if (!cancelled) setSafeBlocks(groupOcrLinesIntoBlocks(page.lines));
      });
    return () => { cancelled = true; };
  }, [page.id, page.translation, page.lines]);

  const hasContent = !!(page.translation?.englishOutput && page.lines.length > 0);

  const textBlocks = safeBlocks || [];
  const tableBlocks = textBlocks.filter((b) => b.isTableRegion);
  const bodyBlocks = textBlocks.filter((b) => !b.isTableRegion);

  // Split translation between table and body regions
  const { tableText, bodyParagraphs } = useMemo(() => {
    if (!hasContent) return { tableText: '', bodyParagraphs: [] as Paragraph[] };

    const raw = page.translation!.englishOutput;
    const allLines = raw.split('\n');

    // Strip initial header lines that correspond to the top banner (y < 4% area)
    // Only remove known patterns: page numbers and banner text identifiers
    // Keep subtitle text like "B'Or Chai" that belongs to visible text blocks
    let startIdx = 0;
    for (let i = 0; i < Math.min(allLines.length, 10); i++) {
      const clean = allLines[i].replace(/\*\*/g, '').trim();
      if (clean.includes('|')) break;
      if (!clean) { startIdx = i + 1; continue; }
      if (/^\d{1,3}\.?$/.test(clean)) { startIdx = i + 1; continue; }
      if (/^(Yechezkel Perek|Main Topics|Introduction|Summary)/i.test(clean)) { startIdx = i + 1; continue; }
      break;
    }
    const content = allLines.slice(startIdx);

    // Split: table lines (with |) go to table regions, rest to body
    if (tableBlocks.length > 0 && bodyBlocks.length > 0) {
      // Find last pipe-separated line — natural boundary between table and body
      let lastPipe = -1;
      for (let i = 0; i < content.length; i++) {
        if (content[i].includes('|')) lastPipe = i;
      }
      if (lastPipe >= 0) {
        let si = lastPipe + 1;
        while (si < content.length && !content[si].trim()) si++; // skip blank lines
        return {
          tableText: content.slice(0, si).join('\n'),
          bodyParagraphs: parseTranslation(content.slice(si).join('\n')),
        };
      }
      // No pipe lines — proportional fallback
      const tH = tableBlocks.reduce((s, b) => s + b.hebrewCharCount, 0);
      const total = tH + bodyBlocks.reduce((s, b) => s + b.hebrewCharCount, 0);
      const ratio = total > 0 ? tH / total : 0.5;
      const budget = Math.round(content.join('\n').length * ratio);
      let acc = 0, si = content.length;
      for (let i = 0; i < content.length; i++) {
        acc += content[i].length + 1;
        if (acc >= budget) { si = i + 1; break; }
      }
      return {
        tableText: content.slice(0, si).join('\n'),
        bodyParagraphs: parseTranslation(content.slice(si).join('\n')),
      };
    }
    if (tableBlocks.length > 0) {
      return { tableText: content.join('\n'), bodyParagraphs: [] as Paragraph[] };
    }
    return { tableText: '', bodyParagraphs: parseTranslation(content.join('\n')) };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasContent, page.translation, tableBlocks.length, bodyBlocks.length]);

  const paraMap = useMemo(
    () => hasContent && bodyBlocks.length > 0 ? assignParagraphsToBlocks(bodyBlocks, bodyParagraphs) : new Map<number, Paragraph[]>(),
    [bodyBlocks, bodyParagraphs, hasContent]
  );

  const containerH = containerW * imgAspect;

  const blockLayouts = useMemo(
    () => hasContent && bodyBlocks.length > 0 ? computeBlockLayouts(bodyBlocks, paraMap, containerW, containerH) : [],
    [bodyBlocks, paraMap, containerW, containerH, hasContent]
  );

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

  const ready = containerW > 0 && safeBlocks !== null;

  return (
    <div className="w-full relative" ref={containerRef}>
      <div className="relative w-full" style={{ aspectRatio: 'auto' }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`/api/pages/${page.id}/image-erased?v=6`}
          alt={`Page ${page.pageNumber}`}
          className="w-full h-auto block"
          loading="lazy"
          onLoad={(e) => {
            const img = e.currentTarget;
            if (img.naturalWidth > 0) setImgAspect(img.naturalHeight / img.naturalWidth);
          }}
        />

        {ready && (
          <div className="absolute inset-0">
            {/* Table region overlays */}
            {tableBlocks.map((block, ti) => (
              <TableRegionOverlay
                key={`table-${ti}`}
                block={block}
                rawText={tableText}
                containerW={containerW}
                containerH={containerH}
              />
            ))}

            {/* Body text overlays */}
            {blockLayouts.map((layout) => {
              const { block, paras, fontPx, blockIndex } = layout;
              return (
                <div
                  key={`body-${blockIndex}`}
                  className="absolute overflow-hidden"
                  style={{
                    left: `${block.x}%`,
                    top: `${block.y}%`,
                    width: `${block.width}%`,
                    height: `${block.height}%`,
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
                        textAlign: block.centered || para.isAllBold ? 'center' : 'left',
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
  const [pdfFrom, setPdfFrom] = useState('');
  const [pdfTo, setPdfTo] = useState('');
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

            <div className="flex items-center gap-1">
              <input
                type="number"
                placeholder="From"
                value={pdfFrom}
                onChange={(e) => setPdfFrom(e.target.value)}
                className="w-14 px-1.5 py-1.5 rounded-lg bg-[#2e2f3a] border border-[#3e3f4a] text-[#e4e4e7] text-xs focus:outline-none text-center"
              />
              <span className="text-[#71717a] text-xs">-</span>
              <input
                type="number"
                placeholder="To"
                value={pdfTo}
                onChange={(e) => setPdfTo(e.target.value)}
                className="w-14 px-1.5 py-1.5 rounded-lg bg-[#2e2f3a] border border-[#3e3f4a] text-[#e4e4e7] text-xs focus:outline-none text-center"
              />
              <a
                href={`/api/books/${bookId}/export${pdfFrom || pdfTo ? `?${pdfFrom ? `from=${pdfFrom}` : ''}${pdfFrom && pdfTo ? '&' : ''}${pdfTo ? `to=${pdfTo}` : ''}` : ''}`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#3b82f6] hover:bg-[#2563eb] text-white text-xs sm:text-sm font-medium transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                PDF
              </a>
            </div>
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
