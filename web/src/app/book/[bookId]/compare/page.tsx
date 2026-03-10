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

// --- TEXT TOKENIZATION ---

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

// --- ZONE GROUPING ---

interface TextZone {
  lines: OcrLine[];
  x: number;
  y: number;
  width: number;
  height: number;
  isCentered: boolean;
  isHeader: boolean;
  avgLineHeight: number; // average Hebrew line height as % of page
}

function groupIntoZones(lines: OcrLine[]): TextZone[] {
  const textLines = lines
    .filter((l) => l.width > 1 && l.height > 0.3)
    // Filter decorative header elements (single char, very narrow, not page numbers)
    .filter((l) => !(l.y < 5 && l.width < 1.5 && l.text.trim().length <= 1))
    .sort((a, b) => a.y - b.y);

  if (textLines.length === 0) return [];

  const heights = textLines.map((l) => l.height).sort((a, b) => a - b);
  const medianH = heights[Math.floor(heights.length / 2)];

  // Detect image regions: large gaps (>8%) between consecutive text lines
  const imageRegions: { top: number; bottom: number }[] = [];
  for (let i = 1; i < textLines.length; i++) {
    const prev = textLines[i - 1];
    const curr = textLines[i];
    const gapStart = prev.y + prev.height;
    const gapEnd = curr.y;
    if (gapEnd - gapStart > 8) {
      imageRegions.push({ top: gapStart, bottom: gapEnd });
    }
  }

  const groups: OcrLine[][] = [[textLines[0]]];

  for (let i = 1; i < textLines.length; i++) {
    const prev = textLines[i - 1];
    const curr = textLines[i];
    const gap = curr.y - (prev.y + prev.height);
    const sizeChange = Math.abs(curr.height - prev.height) > medianH * 0.8;
    const minW = Math.min(curr.width, prev.width);
    const maxW = Math.max(curr.width, prev.width);
    const widthChange = maxW > minW * 3;

    if (gap > medianH * 2.5 || sizeChange || widthChange) {
      groups.push([curr]);
    } else {
      groups[groups.length - 1].push(curr);
    }
  }

  // If too many zones (table pages), merge small adjacent zones
  let mergedGroups = groups;
  if (groups.length > 15) {
    mergedGroups = [groups[0]];
    for (let i = 1; i < groups.length; i++) {
      const prevGroup = mergedGroups[mergedGroups.length - 1];
      const prevMaxY = Math.max(...prevGroup.map((l) => l.y + l.height));
      const currMinY = Math.min(...groups[i].map((l) => l.y));
      const gap = currMinY - prevMaxY;
      // Check if an image region separates them
      const crossesImage = imageRegions.some(
        (r) => r.top < currMinY && r.bottom > prevMaxY
      );
      // Merge if gap is small and no image between them
      if (gap < 5 && !crossesImage) {
        mergedGroups[mergedGroups.length - 1] = [
          ...prevGroup,
          ...groups[i],
        ];
      } else {
        mergedGroups.push(groups[i]);
      }
    }
  }

  // Merge tiny zones (very few chars) into nearest neighbor
  const finalGroups: OcrLine[][] = [];
  for (const group of mergedGroups) {
    const totalChars = group.reduce((s, l) => s + l.text.length, 0);
    if (totalChars < 10 && finalGroups.length > 0) {
      const prevGroup = finalGroups[finalGroups.length - 1];
      const prevMaxY = Math.max(...prevGroup.map((l) => l.y + l.height));
      const currMinY = Math.min(...group.map((l) => l.y));
      const crossesImage = imageRegions.some(
        (r) => r.top < currMinY && r.bottom > prevMaxY
      );
      if (!crossesImage && currMinY - prevMaxY < 5) {
        finalGroups[finalGroups.length - 1] = [...prevGroup, ...group];
        continue;
      }
    }
    finalGroups.push(group);
  }

  return finalGroups.map((g) => {
    const minX = Math.min(...g.map((l) => l.x));
    const minY = Math.min(...g.map((l) => l.y));
    const maxX = Math.max(...g.map((l) => l.x + l.width));
    const maxY = Math.max(...g.map((l) => l.y + l.height));
    const avgCx =
      g.reduce((s, l) => s + l.x + l.width / 2, 0) / g.length;
    const avgW = g.reduce((s, l) => s + l.width, 0) / g.length;
    const avgH = g.reduce((s, l) => s + l.height, 0) / g.length;
    // Only extend wide header text at top to full width, not narrow page numbers
    const isAtTop = minY < 4 && avgW > 20;

    const zoneX = isAtTop ? 2.5 : minX;
    const zoneW = isAtTop ? 95 : maxX - minX;

    // Header zones: extend height to cover the full orange bar (~3.5%)
    let zoneH = maxY - minY;
    if (isAtTop && zoneH < 3.5) {
      zoneH = 3.5;
    }

    // Clamp zone bottom to not extend into image regions
    const zoneBottom = minY + zoneH;
    for (const img of imageRegions) {
      if (zoneBottom > img.top && minY < img.top) {
        zoneH = img.top - minY;
      }
    }

    return {
      lines: g,
      x: zoneX,
      y: minY,
      width: zoneW,
      height: zoneH,
      isCentered: Math.abs(avgCx - 50) < 10 && avgW < 50,
      isHeader: isAtTop || avgH > medianH * 1.3,
      avgLineHeight: avgH,
    };
  });
}

// --- ZONE TEXT ASSIGNMENT ---

interface ZoneSpan {
  text: string;
  bold: boolean;
}

interface ZoneParagraph {
  spans: ZoneSpan[];
}

interface ZoneContent {
  zone: TextZone;
  paragraphs: ZoneParagraph[];
  fontSize: number;
  lineHeight: number;
}

function assignTextToZones(
  zones: TextZone[],
  tokens: FlowToken[],
  imgWidth: number,
  imgHeight: number
): ZoneContent[] {
  const CW = 0.55;
  const result: ZoneContent[] = [];

  // Compute total English and Hebrew char counts for proportional distribution
  const totalEnglish = tokens.reduce(
    (s, t) => s + (t.type === 'word' ? t.word.length + 1 : 0),
    0
  );
  const zoneHebrew = zones.map((z) =>
    z.lines.reduce((s, l) => s + l.text.length, 0)
  );
  const totalHebrew = zoneHebrew.reduce((s, c) => s + c, 0);

  // Target chars per zone (proportional to Hebrew text in that zone)
  const targetChars = zones.map((_, i) => {
    const proportion =
      totalHebrew > 0 ? zoneHebrew[i] / totalHebrew : 1 / zones.length;
    return Math.ceil(proportion * totalEnglish);
  });

  let ti = 0;

  for (let zi = 0; zi < zones.length; zi++) {
    const zone = zones[zi];
    const widthPx = (zone.width / 100) * imgWidth;
    const heightPx = (zone.height / 100) * imgHeight;
    const target = targetChars[zi];
    const isLast = zi === zones.length - 1;

    // Collect tokens for this zone
    const paragraphs: ZoneParagraph[] = [];
    let currentSpans: ZoneSpan[] = [];
    let curText = '';
    let curBold = false;
    let charCount = 0;

    const flushSpan = () => {
      if (curText) {
        currentSpans.push({ text: curText, bold: curBold });
        curText = '';
      }
    };

    const flushParagraph = () => {
      flushSpan();
      if (currentSpans.length > 0) {
        paragraphs.push({ spans: currentSpans });
        currentSpans = [];
      }
    };

    while (ti < tokens.length) {
      const tok = tokens[ti];

      if (tok.type === 'break') {
        flushParagraph();
        ti++;
        // Break to next zone at paragraph boundary if past target
        if (!isLast && charCount >= target) break;
        continue;
      }

      charCount += tok.word.length + 1;

      if (curText && curBold !== tok.bold) {
        flushSpan();
        curBold = tok.bold;
      }
      if (!curText) curBold = tok.bold;
      curText += (curText ? ' ' : '') + tok.word;
      ti++;

      // Break if significantly past target (but prefer paragraph boundaries)
      if (!isLast && charCount >= target * 1.4) break;
    }

    flushParagraph();

    // Cap font size at the Hebrew font size — never go larger than original
    let lineHeight = 1.25;
    const hebrewFontPx = (zone.avgLineHeight / 100) * imgHeight;
    const maxFs = Math.max(8, Math.floor(hebrewFontPx));
    let fontSize = 12;

    if (charCount === 0) {
      fontSize = Math.min(12, maxFs);
    } else {
      fontSize = 8; // fallback
      for (let fs = maxFs; fs >= 8; fs -= 0.5) {
        const cpl = Math.max(1, Math.floor(widthPx / (fs * CW)));
        const linesNeeded = Math.ceil(charCount / cpl);
        if (linesNeeded * fs * lineHeight <= heightPx) {
          fontSize = fs;
          break;
        }
      }
      // If still too small at 1.25 line-height, try tighter spacing
      if (fontSize <= 8) {
        lineHeight = 1.15;
        for (let fs = maxFs; fs >= 8; fs -= 0.5) {
          const cpl = Math.max(1, Math.floor(widthPx / (fs * CW)));
          const linesNeeded = Math.ceil(charCount / cpl);
          if (linesNeeded * fs * lineHeight <= heightPx) {
            fontSize = fs;
            break;
          }
        }
      }
    }

    result.push({ zone, paragraphs, fontSize, lineHeight });
  }

  return result;
}

// --- ZONE COLOR SAMPLING ---

interface ZoneColor {
  bg: string;
  textColor: string;
}

function sampleZoneColors(
  img: HTMLImageElement,
  zones: TextZone[]
): Map<number, ZoneColor> {
  const colors = new Map<number, ZoneColor>();

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

    for (let zi = 0; zi < zones.length; zi++) {
      const zone = zones[zi];
      const lx = (zone.x / 100) * w;
      const ly = (zone.y / 100) * h;
      const lw = (zone.width / 100) * w;
      const lh = (zone.height / 100) * h;

      // Sample a grid across the zone
      const samples: [number, number, number][] = [];
      for (const fx of [0.1, 0.3, 0.5, 0.7, 0.9]) {
        for (const fy of [0.1, 0.3, 0.5, 0.7, 0.9]) {
          samples.push(getPixel(lx + fx * lw, ly + fy * lh));
        }
      }

      const r = median(samples.map((s) => s[0]));
      const g = median(samples.map((s) => s[1]));
      const b = median(samples.map((s) => s[2]));

      const bg = `rgb(${r}, ${g}, ${b})`;
      const luminance = 0.299 * r + 0.587 * g + 0.114 * b;
      const textColor = luminance < 185 ? '#ffffff' : '#1a1510';

      colors.set(zi, { bg, textColor });
    }
  } catch {
    // Canvas access failed
  }

  return colors;
}

// --- OVERLAY COMPONENT ---

function EnglishOverlayPage({ page }: { page: TranslatedPage }) {
  const imgRef = useRef<HTMLImageElement>(null);
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgSize, setImgSize] = useState({ width: 0, height: 0 });
  const [zoneColors, setZoneColors] = useState<Map<number, ZoneColor>>(
    new Map()
  );
  const [zones, setZones] = useState<TextZone[]>([]);

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

  // Compute zones once
  useEffect(() => {
    if (page.lines.length > 0) {
      setZones(groupIntoZones(page.lines));
    }
  }, [page.lines]);

  // Sample bg color per zone from canvas
  useEffect(() => {
    if (imgRef.current && imgLoaded && zones.length > 0) {
      const colors = sampleZoneColors(imgRef.current, zones);
      if (colors.size > 0) setZoneColors(colors);
    }
  }, [imgLoaded, zones]);

  if (!page.translation || !page.lines.length) return null;

  const tokens = tokenizeTranslation(page.translation.englishOutput);

  let zoneContents: ZoneContent[] = [];
  if (imgSize.width > 0 && zones.length > 0) {
    zoneContents = assignTextToZones(
      zones,
      tokens,
      imgSize.width,
      imgSize.height
    );
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
          {zoneContents.map(
            ({ zone, paragraphs, fontSize, lineHeight }, zi) => {
              const colors = zoneColors.get(zi);
              const bg = colors?.bg || defaultBg;
              const textColor = colors?.textColor || defaultTextColor;
              const hasContent = paragraphs.some((p) =>
                p.spans.some((s) => s.text.trim())
              );

              if (!hasContent) return null;

              return (
                <div
                  key={`zone-${zi}`}
                  style={{
                    position: 'absolute',
                    left: `${zone.x}%`,
                    top: `${zone.y}%`,
                    width: `${zone.width}%`,
                    height: `${zone.height}%`,
                    backgroundColor: bg,
                    overflow: 'hidden',
                    padding: '2px 4px',
                    direction: 'ltr',
                    textAlign: zone.isCentered ? 'center' : 'left',
                  }}
                >
                  {paragraphs.map((para, pi) => (
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
                          {span.text}
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
