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

// --- PARAGRAPH PARSING ---

interface TextSpan {
  text: string;
  bold: boolean;
}

interface Paragraph {
  spans: TextSpan[];
  isAllBold: boolean;
  charCount: number;
}

function parseTranslation(raw: string): Paragraph[] {
  const paragraphs: Paragraph[] = [];
  const rawParas = raw.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);

  for (const para of rawParas) {
    const spans: TextSpan[] = [];
    const parts = para.split(/(\*\*[\s\S]*?\*\*)/);
    for (const part of parts) {
      if (!part.trim()) continue;
      const boldMatch = part.match(/^\*\*([\s\S]*?)\*\*$/);
      const text = (boldMatch ? boldMatch[1] : part)
        .replace(/\n/g, ' ')
        .replace(/^#+\s+/gm, '')
        .replace(/`([^`]+)`/g, '$1')
        .trim();
      if (text) spans.push({ text, bold: !!boldMatch });
    }
    if (spans.length > 0) {
      const isAllBold = spans.every((s) => s.bold);
      const charCount = spans.reduce((s, sp) => s + sp.text.length, 0);
      paragraphs.push({ spans, isAllBold, charCount });
    }
  }
  return paragraphs;
}

// --- ZONE CREATION (natural page sections) ---

interface TextZone {
  ocrLines: OcrLine[];
  hebrewChars: number;
  x: number;
  y: number;
  width: number;
  availableHeight: number; // extends to next zone's top
  isCentered: boolean;
  isHeader: boolean;
  avgLineHeight: number;
}

interface ZoneContent {
  zone: TextZone;
  paragraphs: Paragraph[];
  fontSize: number;
  lineHeight: number;
  textColor: string;
}

// Group OCR lines into natural page sections using conservative criteria.
// Only splits at major visual breaks — NOT one zone per paragraph.
function createNaturalZones(lines: OcrLine[]): TextZone[] {
  const sorted = [...lines]
    .filter((l) => l.width > 0.5 && l.height > 0.2)
    .sort((a, b) => a.y - b.y);

  if (sorted.length === 0) return [];

  const heights = sorted.map((l) => l.height).sort((a, b) => a - b);
  const medianH = heights[Math.floor(heights.length / 2)];

  const groups: OcrLine[][] = [[sorted[0]]];
  for (let i = 1; i < sorted.length; i++) {
    const prev = sorted[i - 1];
    const curr = sorted[i];

    // Never split within header area (y < 5%)
    if (prev.y < 5 && curr.y < 5) {
      groups[groups.length - 1].push(curr);
      continue;
    }

    // Header/body boundary
    const crossesHeader = prev.y + prev.height < 5 && curr.y >= 4;

    // Large size change (title ↔ body, >1.5x median height difference)
    const bigSizeChange =
      Math.abs(curr.height - prev.height) > medianH * 1.5;

    // Large gap (>4% of page)
    const gap = curr.y - (prev.y + prev.height);
    const bigGap = gap > 4;

    // Alignment shift: centered narrow → wide left-aligned (or vice versa)
    const prevCentered =
      Math.abs(prev.x + prev.width / 2 - 50) < 15 && prev.width < 50;
    const currCentered =
      Math.abs(curr.x + curr.width / 2 - 50) < 15 && curr.width < 50;
    const currWide = curr.width > 60;
    const prevWide = prev.width > 60;
    const alignmentShift =
      (prevCentered && currWide) || (currCentered && prevWide);

    if (crossesHeader || bigSizeChange || bigGap || alignmentShift) {
      groups.push([curr]);
    } else {
      groups[groups.length - 1].push(curr);
    }
  }

  // Build zones and extend each zone's height to the next zone's start
  const zones = groups.map((g) => buildZone(g));
  for (let i = 0; i < zones.length - 1; i++) {
    zones[i].availableHeight = zones[i + 1].y - zones[i].y;
  }
  if (zones.length > 0) {
    const last = zones[zones.length - 1];
    last.availableHeight = Math.max(last.availableHeight, 96 - last.y);
  }

  return zones;
}

function buildZone(g: OcrLine[]): TextZone {
  const minX = Math.min(...g.map((l) => l.x));
  const minY = Math.min(...g.map((l) => l.y));
  const maxX = Math.max(...g.map((l) => l.x + l.width));
  const maxY = Math.max(...g.map((l) => l.y + l.height));
  const avgH = g.reduce((s, l) => s + l.height, 0) / g.length;
  const avgW = g.reduce((s, l) => s + l.width, 0) / g.length;
  const avgCx = g.reduce((s, l) => s + l.x + l.width / 2, 0) / g.length;
  const hebrewChars = g.reduce((s, l) => s + l.text.length, 0);

  const isCentered =
    Math.abs(avgCx - 50) < 15 &&
    (avgW < 60 || Math.abs(minX - (100 - maxX)) < 10);
  const isHeader = minY < 5;

  return {
    ocrLines: g,
    hebrewChars,
    x: minX,
    y: minY,
    width: maxX - minX,
    availableHeight: maxY - minY,
    isCentered,
    isHeader,
    avgLineHeight: avgH,
  };
}

// --- ASSIGN PARAGRAPHS TO ZONES (proportional by Hebrew content) ---

// Walk paragraphs in order, assign to zones proportionally based on
// how much Hebrew text each zone contains. This ensures English text
// lands in the same region as the Hebrew it was translated from.
function assignTextToZones(
  zones: TextZone[],
  paragraphs: Paragraph[],
  imgWidth: number,
  imgHeight: number,
  zoneTextColors: Map<number, string>
): ZoneContent[] {
  const CW = 0.48;

  // Calculate proportional targets
  const totalHebrew = zones.reduce((s, z) => s + z.hebrewChars, 0);
  const totalEnglish = paragraphs.reduce((s, p) => s + p.charCount, 0);

  // Build cumulative Hebrew char targets for each zone
  // When we've assigned this many English chars, move to next zone
  const zoneTargets: number[] = [];
  let cumHebrew = 0;
  for (const zone of zones) {
    cumHebrew += zone.hebrewChars;
    const share = totalHebrew > 0 ? cumHebrew / totalHebrew : 1;
    zoneTargets.push(share * totalEnglish);
  }

  // Walk paragraphs and assign to zones proportionally
  const zoneParas: Paragraph[][] = zones.map(() => []);
  let currentZone = 0;
  let runningEnglish = 0;

  for (const para of paragraphs) {
    // Move to next zone if we've exceeded current zone's proportional target
    // (but never skip more than one zone at a time, and always keep at least
    // one paragraph in last zone)
    while (
      currentZone < zones.length - 1 &&
      runningEnglish > 0 &&
      runningEnglish >= zoneTargets[currentZone]
    ) {
      currentZone++;
    }
    zoneParas[currentZone].push(para);
    runningEnglish += para.charCount;
  }

  // Build ZoneContent with font sizing
  const result: ZoneContent[] = [];

  for (let zi = 0; zi < zones.length; zi++) {
    const zone = zones[zi];
    const paras = zoneParas[zi];
    const charCount = paras.reduce((s, p) => s + p.charCount, 0);

    const widthPx = (zone.width / 100) * imgWidth;
    const heightPx = (zone.availableHeight / 100) * imgHeight;

    // Cap font size at Hebrew font size
    const hebrewFontPx = (zone.avgLineHeight / 100) * imgHeight;
    const maxFs = Math.max(8, Math.floor(hebrewFontPx));
    const minFs = zone.isHeader ? 6 : 7;
    let fontSize = Math.min(12, maxFs);
    let lineHeight = 1.25;

    if (charCount > 0 && widthPx > 0 && heightPx > 0) {
      // Add inter-paragraph spacing to char count estimate
      const extraChars = Math.max(0, paras.length - 1) * 10;
      const totalChars = charCount + extraChars;

      fontSize = minFs;
      for (let fs = maxFs; fs >= minFs; fs -= 0.5) {
        const cpl = Math.max(1, Math.floor(widthPx / (fs * CW)));
        const linesNeeded = Math.ceil(totalChars / cpl);
        if (linesNeeded * fs * lineHeight <= heightPx) {
          fontSize = fs;
          break;
        }
      }
      // Tighter line height as fallback
      if (fontSize <= minFs) {
        lineHeight = 1.1;
        for (let fs = maxFs; fs >= minFs; fs -= 0.5) {
          const cpl = Math.max(1, Math.floor(widthPx / (fs * CW)));
          const linesNeeded = Math.ceil(totalChars / cpl);
          if (linesNeeded * fs * lineHeight <= heightPx) {
            fontSize = fs;
            break;
          }
        }
      }
    }

    const textColor = zoneTextColors.get(zi) || '#1a1510';
    result.push({ zone, paragraphs: paras, fontSize, lineHeight, textColor });
  }

  return result;
}

// --- CANVAS: ERASE HEBREW TEXT ---

function eraseHebrewText(
  img: HTMLImageElement,
  ocrLines: OcrLine[],
  zones: TextZone[]
): { dataUrl: string; textColors: Map<number, string> } | null {
  const canvas = document.createElement('canvas');
  const w = img.naturalWidth;
  const h = img.naturalHeight;
  if (w === 0 || h === 0) {
    console.warn('eraseHebrewText: image has zero dimensions');
    return null;
  }
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  if (!ctx) {
    console.warn('eraseHebrewText: failed to get canvas context');
    return null;
  }

  ctx.drawImage(img, 0, 0);

  let imgData: ImageData;
  try {
    imgData = ctx.getImageData(0, 0, w, h);
  } catch (e) {
    console.error('eraseHebrewText: canvas tainted or getImageData failed:', e);
    return null;
  }

  const px = imgData.data;
  const pixLuma = (i: number) =>
    0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2];

  // Erase a rectangle by replacing dark pixels with local background color
  const eraseRect = (ex: number, ey: number, ew: number, eh: number) => {
    const x0 = Math.max(0, Math.floor(ex));
    const y0 = Math.max(0, Math.floor(ey));
    const x1 = Math.min(w, Math.ceil(ex + ew));
    const y1 = Math.min(h, Math.ceil(ey + eh));
    if (x1 <= x0 || y1 <= y0) return;

    // Collect luminances to find background level
    const lumas: number[] = [];
    for (let y = y0; y < y1; y++) {
      for (let x = x0; x < x1; x++) {
        lumas.push(pixLuma((y * w + x) * 4));
      }
    }
    lumas.sort((a, b) => b - a);

    const bgCount = Math.max(5, Math.floor(lumas.length * 0.2));
    const bgLuma = lumas[Math.floor(bgCount / 2)];
    const threshold = bgLuma * 0.93;

    // Compute background color from brightest pixels
    const bgR: number[] = [];
    const bgG: number[] = [];
    const bgB: number[] = [];
    for (let y = y0; y < y1; y++) {
      for (let x = x0; x < x1; x++) {
        const idx = (y * w + x) * 4;
        if (pixLuma(idx) >= bgLuma * 0.95) {
          bgR.push(px[idx]);
          bgG.push(px[idx + 1]);
          bgB.push(px[idx + 2]);
        }
      }
    }
    if (bgR.length === 0) return;
    bgR.sort((a, b) => a - b);
    bgG.sort((a, b) => a - b);
    bgB.sort((a, b) => a - b);
    const midR = bgR[Math.floor(bgR.length / 2)];
    const midG = bgG[Math.floor(bgG.length / 2)];
    const midB = bgB[Math.floor(bgB.length / 2)];

    // Replace dark pixels with background
    for (let y = y0; y < y1; y++) {
      for (let x = x0; x < x1; x++) {
        const idx = (y * w + x) * 4;
        if (pixLuma(idx) < threshold) {
          px[idx] = midR;
          px[idx + 1] = midG;
          px[idx + 2] = midB;
        }
      }
    }
  };

  // Sort lines by y for band-based erasure
  const bodyLines = ocrLines
    .filter((l) => l.width > 0.5 && l.height > 0.2 && l.y >= 5)
    .sort((a, b) => a.y - b.y);

  // Erase each body line with generous padding
  for (const line of bodyLines) {
    const lx = (line.x / 100) * w;
    const ly = (line.y / 100) * h;
    const lw = (line.width / 100) * w;
    const lh = (line.height / 100) * h;

    const padV = lh * 0.5;
    const padH = lw * 0.1;
    eraseRect(lx - padH - 8, ly - padV, lw + padH * 2 + 16, lh + padV * 2);
  }

  // Sweep gaps between consecutive lines on the same band
  // (catches descenders, ascenders, dotted leaders)
  for (let i = 0; i < bodyLines.length - 1; i++) {
    const curr = bodyLines[i];
    const next = bodyLines[i + 1];
    const currBottom = curr.y + curr.height;
    const gapPct = next.y - currBottom;

    // If gap is small (lines are close), erase the gap between them
    if (gapPct > 0 && gapPct < 3) {
      const gapLeft = Math.min(curr.x, next.x);
      const gapRight = Math.max(curr.x + curr.width, next.x + next.width);
      const gx = (gapLeft / 100) * w - 4;
      const gy = (currBottom / 100) * h;
      const gw = ((gapRight - gapLeft) / 100) * w + 8;
      const gh = (gapPct / 100) * h;
      eraseRect(gx, gy, gw, gh);
    }
  }

  // Also erase gaps between segments on same row (multi-column, dotted leaders)
  if (bodyLines.length > 2) {
    const medH = bodyLines.map((l) => l.height).sort((a, b) => a - b)[
      Math.floor(bodyLines.length / 2)
    ];
    const rows: OcrLine[][] = [[bodyLines[0]]];
    for (let i = 1; i < bodyLines.length; i++) {
      const prev = bodyLines[i - 1];
      const curr = bodyLines[i];
      if (Math.abs(curr.y - prev.y) < medH * 1.5) {
        rows[rows.length - 1].push(curr);
      } else {
        rows.push([curr]);
      }
    }
    for (const row of rows) {
      if (row.length < 2) continue;
      const segs = [...row].sort((a, b) => a.x - b.x);
      const bandTop = Math.min(...row.map((l) => l.y));
      const bandBot = Math.max(...row.map((l) => l.y + l.height));
      for (let si = 0; si < segs.length - 1; si++) {
        const gapL = segs[si].x + segs[si].width;
        const gapR = segs[si + 1].x;
        if (gapR - gapL > 2) {
          const gy = (bandTop / 100) * h - 2;
          const gx = (gapL / 100) * w - 2;
          const gw = ((gapR - gapL) / 100) * w + 4;
          const gh = ((bandBot - bandTop) / 100) * h + 4;
          eraseRect(gx, gy, gw, gh);
        }
      }
    }
  }

  ctx.putImageData(imgData, 0, 0);

  // Determine text color per zone from background luminance
  const textColors = new Map<number, string>();
  for (let zi = 0; zi < zones.length; zi++) {
    const zone = zones[zi];
    const zx = (zone.x / 100) * w;
    const zy = (zone.y / 100) * h;
    const zw = (zone.width / 100) * w;
    const zh = (zone.availableHeight / 100) * h;

    const samples: number[] = [];
    for (const fx of [0.2, 0.5, 0.8]) {
      for (const fy of [0.2, 0.5, 0.8]) {
        const sx = Math.max(0, Math.min(w - 1, Math.floor(zx + fx * zw)));
        const sy = Math.max(0, Math.min(h - 1, Math.floor(zy + fy * zh)));
        const cd = ctx.getImageData(sx, sy, 1, 1).data;
        samples.push(0.299 * cd[0] + 0.587 * cd[1] + 0.114 * cd[2]);
      }
    }
    const medLuma = [...samples].sort((a, b) => a - b)[
      Math.floor(samples.length / 2)
    ];
    textColors.set(zi, medLuma < 160 ? '#ffffff' : '#1a1510');
  }

  return { dataUrl: canvas.toDataURL('image/png'), textColors };
}

// --- OVERLAY COMPONENT ---

function EnglishOverlayPage({ page }: { page: TranslatedPage }) {
  const imgRef = useRef<HTMLImageElement>(null);
  const displayRef = useRef<HTMLImageElement>(null);
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgSize, setImgSize] = useState({ width: 0, height: 0 });
  const [cleanedSrc, setCleanedSrc] = useState<string | null>(null);
  const [textColors, setTextColors] = useState<Map<number, string>>(new Map());
  const [zones, setZones] = useState<TextZone[]>([]);
  const [paragraphs, setParagraphs] = useState<Paragraph[]>([]);

  // Parse translation into paragraphs
  useEffect(() => {
    if (page.translation?.englishOutput) {
      setParagraphs(parseTranslation(page.translation.englishOutput));
    }
  }, [page.translation]);

  // Create natural zones from OCR lines (independent of paragraph count)
  useEffect(() => {
    if (page.lines.length > 0) {
      setZones(createNaturalZones(page.lines));
    }
  }, [page.lines]);

  // Track displayed image size
  useEffect(() => {
    const target = displayRef.current || imgRef.current;
    if (target && imgLoaded) {
      const update = () => {
        const el = displayRef.current || imgRef.current;
        if (el) setImgSize({ width: el.clientWidth, height: el.clientHeight });
      };
      update();
      const observer = new ResizeObserver(update);
      observer.observe(target);
      return () => observer.disconnect();
    }
  }, [imgLoaded, cleanedSrc]);

  // Erase Hebrew text from canvas
  useEffect(() => {
    if (imgRef.current && imgLoaded && zones.length > 0) {
      const result = eraseHebrewText(imgRef.current, page.lines, zones);
      if (result) {
        setCleanedSrc(result.dataUrl);
        setTextColors(result.textColors);
      } else {
        console.warn('Hebrew erasure failed for page', page.pageNumber);
      }
    }
  }, [imgLoaded, zones, page.lines, page.pageNumber]);

  if (!page.translation || !page.lines.length) return null;

  let zoneContents: ZoneContent[] = [];
  if (imgSize.width > 0 && zones.length > 0) {
    zoneContents = assignTextToZones(
      zones,
      paragraphs,
      imgSize.width,
      imgSize.height,
      textColors
    );
  }

  return (
    <div className="relative inline-block w-full">
      {/* Hidden original image for canvas processing */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        ref={imgRef}
        crossOrigin="anonymous"
        src={`/api/pages/${page.id}/image`}
        alt={`Page ${page.pageNumber}`}
        style={{
          position: cleanedSrc ? 'absolute' : 'relative',
          width: cleanedSrc ? '1px' : '100%',
          height: cleanedSrc ? '1px' : 'auto',
          opacity: cleanedSrc ? 0 : 1,
          overflow: 'hidden',
          pointerEvents: 'none',
        }}
        onLoad={() => setImgLoaded(true)}
      />

      {/* Cleaned image (Hebrew erased) */}
      {cleanedSrc && (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          ref={displayRef}
          src={cleanedSrc}
          alt={`Page ${page.pageNumber} English`}
          className="w-full h-auto block"
        />
      )}

      {/* English text overlay */}
      {imgSize.width > 0 && (
        <div className="absolute inset-0" style={{ pointerEvents: 'none' }}>
          {zoneContents.map(
            ({ zone, paragraphs: paras, fontSize, lineHeight, textColor }, zi) => {
              if (paras.length === 0) return null;

              return (
                <div
                  key={`zone-${zi}`}
                  style={{
                    position: 'absolute',
                    left: `${zone.x}%`,
                    top: `${zone.y}%`,
                    width: `${zone.width}%`,
                    height: `${zone.availableHeight}%`,
                    overflow: 'hidden',
                    padding: '1px 3px',
                    direction: 'ltr',
                    textAlign: zone.isCentered ? 'center' : 'left',
                  }}
                >
                  {paras.map((para, pi) => (
                    <div
                      key={pi}
                      style={{
                        marginTop: pi > 0 ? `${fontSize * 0.4}px` : 0,
                      }}
                    >
                      {para.spans.map((span, si) => (
                        <span
                          key={si}
                          style={{
                            fontFamily:
                              'Georgia, "Times New Roman", "Palatino Linotype", serif',
                            fontSize: `${fontSize}px`,
                            fontWeight: span.bold ? 700 : 400,
                            color: textColor,
                            lineHeight: lineHeight,
                            wordWrap: 'break-word',
                            overflowWrap: 'break-word',
                          }}
                        >
                          {span.text}{' '}
                        </span>
                      ))}
                    </div>
                  ))}
                </div>
              );
            }
          )}
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
