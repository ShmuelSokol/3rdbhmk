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
  avgLineHeight: number;
}

function groupIntoZones(lines: OcrLine[]): TextZone[] {
  const textLines = lines
    .filter((l) => l.width > 1 && l.height > 0.3)
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
  if (groups.length > 12) {
    mergedGroups = [groups[0]];
    for (let i = 1; i < groups.length; i++) {
      const prevGroup = mergedGroups[mergedGroups.length - 1];
      const prevMaxY = Math.max(...prevGroup.map((l) => l.y + l.height));
      const currMinY = Math.min(...groups[i].map((l) => l.y));
      const gap = currMinY - prevMaxY;
      const crossesImage = imageRegions.some(
        (r) => r.top < currMinY && r.bottom > prevMaxY
      );
      if (gap < 8 && !crossesImage) {
        mergedGroups[mergedGroups.length - 1] = [
          ...prevGroup,
          ...groups[i],
        ];
      } else {
        mergedGroups.push(groups[i]);
      }
    }
  }

  // Merge tiny zones (<10 chars) into nearest neighbor
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
    const isAtTop = minY < 4 && avgW > 20;

    const zoneX = isAtTop ? 2.5 : minX;
    const zoneW = isAtTop ? 95 : maxX - minX;

    let zoneH = maxY - minY;
    if (isAtTop && zoneH < 7) zoneH = 7; // Header zones need more height for English word-wrap

    // Clamp zone bottom to not extend into image regions
    for (const img of imageRegions) {
      if (minY + zoneH > img.top && minY < img.top) {
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
  textColor: string;
}

function assignTextToZones(
  zones: TextZone[],
  tokens: FlowToken[],
  imgWidth: number,
  imgHeight: number,
  zoneTextColors: Map<number, string>
): ZoneContent[] {
  const CW = 0.48;
  const result: ZoneContent[] = [];

  const totalEnglish = tokens.reduce(
    (s, t) => s + (t.type === 'word' ? t.word.length + 1 : 0),
    0
  );
  const zoneHebrew = zones.map((z) =>
    z.lines.reduce((s, l) => s + l.text.length, 0)
  );
  const totalHebrew = zoneHebrew.reduce((s, c) => s + c, 0);

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

      if (!isLast && charCount >= target * 1.4) break;
    }

    flushParagraph();

    // Cap font size at the Hebrew font size
    let lineHeight = 1.25;
    const hebrewFontPx = (zone.avgLineHeight / 100) * imgHeight;
    const maxFs = Math.max(8, Math.floor(hebrewFontPx));
    // Header running titles can go smaller to fit
    const minFs = zone.isHeader ? 7 : 8;
    let fontSize = 12;

    if (charCount === 0) {
      fontSize = Math.min(12, maxFs);
    } else {
      fontSize = minFs;
      for (let fs = maxFs; fs >= minFs; fs -= 0.5) {
        const cpl = Math.max(1, Math.floor(widthPx / (fs * CW)));
        const linesNeeded = Math.ceil(charCount / cpl);
        if (linesNeeded * fs * lineHeight <= heightPx) {
          fontSize = fs;
          break;
        }
      }
      if (fontSize <= minFs) {
        lineHeight = 1.15;
        for (let fs = maxFs; fs >= minFs; fs -= 0.5) {
          const cpl = Math.max(1, Math.floor(widthPx / (fs * CW)));
          const linesNeeded = Math.ceil(charCount / cpl);
          if (linesNeeded * fs * lineHeight <= heightPx) {
            fontSize = fs;
            break;
          }
        }
      }
    }

    const textColor = zoneTextColors.get(zi) || '#1a1510';
    result.push({ zone, paragraphs, fontSize, lineHeight, textColor });
  }

  return result;
}

// --- CANVAS: ERASE HEBREW TEXT & SAMPLE COLORS ---

function eraseHebrewAndSampleColors(
  img: HTMLImageElement,
  ocrLines: OcrLine[],
  zones: TextZone[]
): { dataUrl: string; textColors: Map<number, string> } | null {
  try {
    const canvas = document.createElement('canvas');
    const w = img.naturalWidth;
    const h = img.naturalHeight;
    if (w === 0 || h === 0) return null;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    ctx.drawImage(img, 0, 0);
    const fullData = ctx.getImageData(0, 0, w, h);
    const pixels = fullData.data;

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

    // For each OCR line, sample the background color from edges/margins
    // then paint over the Hebrew text with that color
    for (const line of ocrLines) {
      if (line.width < 1 || line.height < 0.3) continue;

      const lx = (line.x / 100) * w;
      const ly = (line.y / 100) * h;
      const lw = (line.width / 100) * w;
      const lh = (line.height / 100) * h;

      // Detect if this is a page number (narrow, centered, near top)
      const isPageNum =
        line.width < 5 &&
        line.text.trim().length <= 3 &&
        Math.abs(line.x + line.width / 2 - 50) < 5;

      // Sample background from ABOVE and BELOW the text line
      const samples: [number, number, number][] = [];
      for (const fx of [0.1, 0.3, 0.5, 0.7, 0.9]) {
        samples.push(getPixel(lx + fx * lw, Math.max(0, ly - 3)));
      }
      for (const fx of [0.1, 0.3, 0.5, 0.7, 0.9]) {
        samples.push(getPixel(lx + fx * lw, ly + lh + 3));
      }
      samples.push(getPixel(Math.max(0, lx - 5), ly + lh * 0.5));
      samples.push(getPixel(lx + lw + 5, ly + lh * 0.5));

      const r = median(samples.map((s) => s[0]));
      const g = median(samples.map((s) => s[1]));
      const b = median(samples.map((s) => s[2]));

      ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;

      if (isPageNum) {
        // Erase a wider area to cover decorative circle around page number
        const circleR = Math.max(lw, lh) * 1.5;
        const cx = lx + lw / 2;
        const cy = ly + lh / 2;
        ctx.beginPath();
        ctx.arc(cx, cy, circleR, 0, Math.PI * 2);
        ctx.fill();
      } else {
        // Standard text erasure with generous padding
        const padV = lh * 0.25;
        const padH = lw * 0.05;
        ctx.fillRect(
          Math.max(0, lx - padH - 4),
          Math.max(0, ly - padV),
          lw + padH * 2 + 8,
          lh + padV * 2
        );
      }
    }

    // Second pass: erase dotted leaders on table/TOC pages
    // Group OCR lines into rows (lines at similar Y) and erase full horizontal span
    const sortedLines = [...ocrLines]
      .filter((l) => l.width > 1 && l.height > 0.3)
      .sort((a, b) => a.y - b.y);

    if (sortedLines.length > 15) {
      // Group lines into rows by Y-proximity (within 1.5x median line height)
      const rowGroups: OcrLine[][] = [[sortedLines[0]]];
      const medH = sortedLines.map((l) => l.height).sort((a, b) => a - b)[
        Math.floor(sortedLines.length / 2)
      ];
      for (let i = 1; i < sortedLines.length; i++) {
        const prev = sortedLines[i - 1];
        const curr = sortedLines[i];
        const vertOverlap =
          curr.y < prev.y + prev.height ||
          Math.abs(curr.y - prev.y) < medH * 1.5;
        if (vertOverlap) {
          rowGroups[rowGroups.length - 1].push(curr);
        } else {
          rowGroups.push([curr]);
        }
      }

      // For rows with multiple segments, erase only the GAPS between them (dotted leaders)
      // This avoids creating staircase artifacts on hierarchical/indented layouts
      for (const row of rowGroups) {
        if (row.length < 2) continue;
        // Sort segments left-to-right within the row
        const sorted = [...row].sort((a, b) => a.x - b.x);
        const minY = Math.min(...row.map((l) => l.y));
        const maxYH = Math.max(...row.map((l) => l.y + l.height));
        const bandTop = (minY / 100) * h;
        const bandBottom = (maxYH / 100) * h;
        const bandH = bandBottom - bandTop;
        const padV = bandH * 0.15;

        // Erase each horizontal gap between consecutive segments
        for (let si = 0; si < sorted.length - 1; si++) {
          const leftSeg = sorted[si];
          const rightSeg = sorted[si + 1];
          const gapLeftPct = leftSeg.x + leftSeg.width;
          const gapRightPct = rightSeg.x;
          const gapWidthPct = gapRightPct - gapLeftPct;

          // Only erase if there's a meaningful gap (>3% of page width = likely has dots)
          if (gapWidthPct > 3) {
            const gapLeft = (gapLeftPct / 100) * w;
            const gapRight = (gapRightPct / 100) * w;

            // Sample bg from above and below the gap
            const midX = (gapLeft + gapRight) / 2;
            const bgSamples: [number, number, number][] = [];
            bgSamples.push(getPixel(midX, Math.max(0, bandTop - 5)));
            bgSamples.push(getPixel(midX, Math.min(h - 1, bandBottom + 5)));
            bgSamples.push(getPixel(gapLeft, bandTop + bandH * 0.5));
            bgSamples.push(getPixel(gapRight, bandTop + bandH * 0.5));
            const br = median(bgSamples.map((s) => s[0]));
            const bg = median(bgSamples.map((s) => s[1]));
            const bb = median(bgSamples.map((s) => s[2]));

            ctx.fillStyle = `rgb(${br}, ${bg}, ${bb})`;
            ctx.fillRect(
              gapLeft - 2,
              bandTop - padV,
              gapRight - gapLeft + 4,
              bandH + padV * 2
            );
          }
        }
      }

      // Third pass: full-width sweep for all rows to catch stray dots, decorative lines, vertical bars
      // Use a CONSISTENT content-area width to avoid staircase artifacts
      const allMinX = Math.min(...sortedLines.map((l) => l.x));
      const allMaxXW = Math.max(...sortedLines.map((l) => l.x + l.width));
      const contentLeft = (allMinX / 100) * w;
      const contentRight = (allMaxXW / 100) * w;

      // Sample base page background from far margins (avoiding highlighted zones)
      const marginBgSamples: [number, number, number][] = [];
      for (const fy of [0.2, 0.4, 0.6, 0.8]) {
        marginBgSamples.push(getPixel(w * 0.02, h * fy));
        marginBgSamples.push(getPixel(w * 0.98, h * fy));
      }
      const baseBgR = median(marginBgSamples.map((s) => s[0]));
      const baseBgG = median(marginBgSamples.map((s) => s[1]));
      const baseBgB = median(marginBgSamples.map((s) => s[2]));

      // Erase full content width at each row position AND gaps between rows
      for (let ri = 0; ri < rowGroups.length; ri++) {
        const row = rowGroups[ri];
        const rowMinY = Math.min(...row.map((l) => l.y));
        const rowMaxYH = Math.max(...row.map((l) => l.y + l.height));
        const rowTop = (rowMinY / 100) * h;
        const rowBottom = (rowMaxYH / 100) * h;
        const rowH = rowBottom - rowTop;
        const padV = rowH * 0.2;

        // Use local bg sample at this Y level (blend of margin bg and local sample)
        const localSamples: [number, number, number][] = [];
        localSamples.push(getPixel(contentLeft - 5, rowTop + rowH / 2));
        localSamples.push(getPixel(contentRight + 5, rowTop + rowH / 2));
        const lr = median([baseBgR, ...localSamples.map((s) => s[0])]);
        const lg = median([baseBgG, ...localSamples.map((s) => s[1])]);
        const lb = median([baseBgB, ...localSamples.map((s) => s[2])]);

        ctx.fillStyle = `rgb(${lr}, ${lg}, ${lb})`;
        ctx.fillRect(
          contentLeft - 2,
          rowTop - padV,
          contentRight - contentLeft + 4,
          rowH + padV * 2
        );

        // Also erase the gap between this row and the next
        if (ri < rowGroups.length - 1) {
          const nextRow = rowGroups[ri + 1];
          const nextTop = Math.min(...nextRow.map((l) => l.y));
          const gapPct = nextTop - rowMaxYH;
          if (gapPct > 0 && gapPct < medH * 4) {
            const gapTopPx = (rowMaxYH / 100) * h;
            const gapBottomPx = (nextTop / 100) * h;
            ctx.fillRect(
              contentLeft - 2,
              gapTopPx - 1,
              contentRight - contentLeft + 4,
              gapBottomPx - gapTopPx + 2
            );
          }
        }
      }
    }

    // Determine text color per zone from the background luminance
    const textColors = new Map<number, string>();
    for (let zi = 0; zi < zones.length; zi++) {
      const zone = zones[zi];
      const zx = (zone.x / 100) * w;
      const zy = (zone.y / 100) * h;
      const zw = (zone.width / 100) * w;
      const zh = (zone.height / 100) * h;

      // Sample a 5x5 grid from the cleaned canvas to determine text color
      const zSamples: [number, number, number][] = [];
      for (const fx of [0.1, 0.3, 0.5, 0.7, 0.9]) {
        for (const fy of [0.1, 0.3, 0.5, 0.7, 0.9]) {
          const sx = Math.max(0, Math.min(w - 1, Math.floor(zx + fx * zw)));
          const sy = Math.max(0, Math.min(h - 1, Math.floor(zy + fy * zh)));
          // Read from the current canvas state (after erasure)
          const cd = ctx.getImageData(sx, sy, 1, 1).data;
          zSamples.push([cd[0], cd[1], cd[2]]);
        }
      }
      if (zSamples.length > 0) {
        const mr = median(zSamples.map((s) => s[0]));
        const mg = median(zSamples.map((s) => s[1]));
        const mb = median(zSamples.map((s) => s[2]));
        const luminance = 0.299 * mr + 0.587 * mg + 0.114 * mb;
        textColors.set(zi, luminance < 160 ? '#ffffff' : '#1a1510');
      }
    }

    const dataUrl = canvas.toDataURL('image/png');
    return { dataUrl, textColors };
  } catch {
    return null;
  }
}

// --- OVERLAY COMPONENT ---

function EnglishOverlayPage({ page }: { page: TranslatedPage }) {
  const imgRef = useRef<HTMLImageElement>(null);
  const displayRef = useRef<HTMLImageElement>(null);
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgSize, setImgSize] = useState({ width: 0, height: 0 });
  const [cleanedSrc, setCleanedSrc] = useState<string | null>(null);
  const [textColors, setTextColors] = useState<Map<number, string>>(
    new Map()
  );
  const [zones, setZones] = useState<TextZone[]>([]);

  // Track displayed image size for overlay positioning
  useEffect(() => {
    const target = displayRef.current || imgRef.current;
    if (target && imgLoaded) {
      const update = () => {
        const el = displayRef.current || imgRef.current;
        if (el) {
          setImgSize({
            width: el.clientWidth,
            height: el.clientHeight,
          });
        }
      };
      update();
      const observer = new ResizeObserver(update);
      observer.observe(target);
      return () => observer.disconnect();
    }
  }, [imgLoaded, cleanedSrc]);

  // Compute zones once
  useEffect(() => {
    if (page.lines.length > 0) {
      setZones(groupIntoZones(page.lines));
    }
  }, [page.lines]);

  // Erase Hebrew text from canvas and get cleaned image + text colors
  useEffect(() => {
    if (imgRef.current && imgLoaded && zones.length > 0) {
      const result = eraseHebrewAndSampleColors(
        imgRef.current,
        page.lines,
        zones
      );
      if (result) {
        setCleanedSrc(result.dataUrl);
        setTextColors(result.textColors);
      }
    }
  }, [imgLoaded, zones, page.lines]);

  if (!page.translation || !page.lines.length) return null;

  const tokens = tokenizeTranslation(page.translation.englishOutput);

  let zoneContents: ZoneContent[] = [];
  if (imgSize.width > 0 && zones.length > 0) {
    zoneContents = assignTextToZones(
      zones,
      tokens,
      imgSize.width,
      imgSize.height,
      textColors
    );
  }

  return (
    <div className="relative inline-block w-full">
      {/* Original image — hidden offscreen for canvas processing, not display:none so it loads properly */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        ref={imgRef}
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

      {/* Cleaned image (Hebrew erased, original colors preserved) */}
      {cleanedSrc && (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          ref={displayRef}
          src={cleanedSrc}
          alt={`Page ${page.pageNumber} English`}
          className="w-full h-auto block"
        />
      )}

      {/* English text overlay — transparent backgrounds, text only */}
      {imgSize.width > 0 && (
        <div className="absolute inset-0" style={{ pointerEvents: 'none' }}>
          {zoneContents.map(
            ({ zone, paragraphs, fontSize, lineHeight, textColor }, zi) => {
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
                    overflow: 'hidden',
                    padding: '1px 3px',
                    direction: 'ltr',
                    textAlign: zone.isCentered ? 'center' : 'left',
                  }}
                >
                  {paragraphs.map((para, pi) => (
                    <div
                      key={pi}
                      style={{
                        marginTop: pi > 0 ? `${fontSize * 0.3}px` : 0,
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
