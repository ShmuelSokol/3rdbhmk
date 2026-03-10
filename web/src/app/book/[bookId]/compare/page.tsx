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

  // Classify lines by role
  const headerLines: OcrLine[] = []; // y < 4%, running title
  const pageNumLines: OcrLine[] = []; // y < 4%, narrow, centered
  const bodyLines: OcrLine[] = [];

  for (const line of textLines) {
    if (line.y < 4) {
      if (line.width < 6 && line.text.trim().length <= 3 &&
          Math.abs(line.x + line.width / 2 - 50) < 6) {
        pageNumLines.push(line);
      } else {
        headerLines.push(line);
      }
    } else {
      bodyLines.push(line);
    }
  }

  // Group body lines: split on large gaps, large size changes, or image crossings
  // Use relaxed width threshold — only split when BOTH lines are wide (not footnotes)
  const bodyGroups: OcrLine[][] = bodyLines.length > 0 ? [[bodyLines[0]]] : [];
  for (let i = 1; i < bodyLines.length; i++) {
    const prev = bodyLines[i - 1];
    const curr = bodyLines[i];
    const gap = curr.y - (prev.y + prev.height);
    const sizeChange = Math.abs(curr.height - prev.height) > medianH * 1.2;
    // Only split on width change for LARGE text (titles), not narrow footnotes
    const bothWide = curr.width > 30 && prev.width > 30;
    const widthChange = bothWide && Math.max(curr.width, prev.width) > Math.min(curr.width, prev.width) * 3;
    const crossesImage = imageRegions.some(
      (r) => r.top < curr.y && r.bottom > prev.y + prev.height
    );

    if (crossesImage || gap > medianH * 3 || sizeChange || widthChange) {
      bodyGroups.push([curr]);
    } else {
      bodyGroups[bodyGroups.length - 1].push(curr);
    }
  }

  // Merge small body zones (<15 chars) into nearest neighbor
  const mergedBody: OcrLine[][] = [];
  for (const group of bodyGroups) {
    const totalChars = group.reduce((s, l) => s + l.text.length, 0);
    if (totalChars < 15 && mergedBody.length > 0) {
      const prevGroup = mergedBody[mergedBody.length - 1];
      const prevMaxY = Math.max(...prevGroup.map((l) => l.y + l.height));
      const currMinY = Math.min(...group.map((l) => l.y));
      const crossesImage = imageRegions.some(
        (r) => r.top < currMinY && r.bottom > prevMaxY
      );
      if (!crossesImage && currMinY - prevMaxY < 6) {
        mergedBody[mergedBody.length - 1] = [...prevGroup, ...group];
        continue;
      }
    }
    mergedBody.push(group);
  }

  // If still too many zones, merge adjacent small ones
  let finalBody = mergedBody;
  if (mergedBody.length > 8) {
    finalBody = [mergedBody[0]];
    for (let i = 1; i < mergedBody.length; i++) {
      const prevGroup = finalBody[finalBody.length - 1];
      const prevMaxY = Math.max(...prevGroup.map((l) => l.y + l.height));
      const currMinY = Math.min(...mergedBody[i].map((l) => l.y));
      const gap = currMinY - prevMaxY;
      const crossesImage = imageRegions.some(
        (r) => r.top < currMinY && r.bottom > prevMaxY
      );
      if (gap < 8 && !crossesImage) {
        finalBody[finalBody.length - 1] = [...prevGroup, ...mergedBody[i]];
      } else {
        finalBody.push(mergedBody[i]);
      }
    }
  }

  // Build final zone list: header, page number, then body zones
  const finalGroups: OcrLine[][] = [];
  if (headerLines.length > 0) finalGroups.push(headerLines);
  if (pageNumLines.length > 0) finalGroups.push(pageNumLines);
  for (const g of finalBody) finalGroups.push(g);

  return finalGroups.map((g) => {
    const minX = Math.min(...g.map((l) => l.x));
    const minY = Math.min(...g.map((l) => l.y));
    const maxX = Math.max(...g.map((l) => l.x + l.width));
    const maxY = Math.max(...g.map((l) => l.y + l.height));
    const avgCx =
      g.reduce((s, l) => s + l.x + l.width / 2, 0) / g.length;
    const avgW = g.reduce((s, l) => s + l.width, 0) / g.length;
    const avgH = g.reduce((s, l) => s + l.height, 0) / g.length;
    const isInHeader = minY < 4 && avgW > 10;
    const isPageNum = minY < 4 && avgW < 6 &&
      g.every((l) => l.text.trim().length <= 3);

    // Header: use full width of the header bar area
    // Page number: keep at original position, centered
    // Body: use the bounding box of the lines
    const zoneX = isInHeader ? 2.5 : minX;
    const zoneW = isInHeader ? 95 : maxX - minX;
    let zoneH = maxY - minY;

    // Clamp zone bottom to not extend into image regions
    for (const img of imageRegions) {
      if (minY + zoneH > img.top && minY < img.top) {
        zoneH = img.top - minY;
      }
    }

    // Detect centering: line centers near page center
    const centered = Math.abs(avgCx - 50) < 12 &&
      (avgW < 60 || Math.abs(minX - (100 - maxX)) < 10);

    return {
      lines: g,
      x: zoneX,
      y: minY,
      width: zoneW,
      height: zoneH,
      isCentered: centered || isPageNum,
      isHeader: isInHeader || avgH > medianH * 1.5,
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

  // Split tokens into paragraphs (at 'break' tokens)
  const allParagraphs: { spans: ZoneSpan[]; isAllBold: boolean }[] = [];
  {
    let spans: ZoneSpan[] = [];
    let curText = '';
    let curBold = false;

    const flushSpan = () => {
      if (curText) {
        spans.push({ text: curText, bold: curBold });
        curText = '';
      }
    };
    const flushPara = () => {
      flushSpan();
      if (spans.length > 0) {
        const isAllBold = spans.every((s) => s.bold);
        allParagraphs.push({ spans: [...spans], isAllBold });
        spans = [];
      }
    };

    for (const tok of tokens) {
      if (tok.type === 'break') {
        flushPara();
        continue;
      }
      if (curText && curBold !== tok.bold) {
        flushSpan();
        curBold = tok.bold;
      }
      if (!curText) curBold = tok.bold;
      curText += (curText ? ' ' : '') + tok.word;
    }
    flushPara();
  }

  // Assign paragraphs to zones SEQUENTIALLY (in order)
  // Each zone gets the next paragraph(s) that correspond to it
  let pi = 0;
  for (let zi = 0; zi < zones.length; zi++) {
    const zone = zones[zi];
    const isLast = zi === zones.length - 1;
    const paragraphs: ZoneParagraph[] = [];

    if (pi < allParagraphs.length) {
      if (isLast) {
        // Last zone gets ALL remaining paragraphs
        while (pi < allParagraphs.length) {
          paragraphs.push({ spans: allParagraphs[pi].spans });
          pi++;
        }
      } else {
        // Assign at least one paragraph to this zone
        paragraphs.push({ spans: allParagraphs[pi].spans });
        pi++;

        // If this is a large body zone (many Hebrew lines), keep assigning
        // paragraphs until we've used roughly the right share
        const hebrewChars = zone.lines.reduce((s, l) => s + l.text.length, 0);
        const totalHebrew = zones.reduce(
          (s, z) => s + z.lines.reduce((s2, l) => s2 + l.text.length, 0), 0
        );
        const zonesLeft = zones.length - zi - 1;
        const parasLeft = allParagraphs.length - pi;

        // Keep assigning if this zone has proportionally more Hebrew text
        // than the average remaining zone
        if (parasLeft > zonesLeft && hebrewChars > 0) {
          const avgHebrewPerZone = totalHebrew / zones.length;
          const extraParas = Math.floor(hebrewChars / avgHebrewPerZone) - 1;
          for (let ep = 0; ep < extraParas && pi < allParagraphs.length && (allParagraphs.length - pi) > zonesLeft; ep++) {
            paragraphs.push({ spans: allParagraphs[pi].spans });
            pi++;
          }
        }
      }
    }

    // Compute total char count for this zone's assigned paragraphs
    const charCount = paragraphs.reduce(
      (s, p) => s + p.spans.reduce((s2, sp) => s2 + sp.text.length + 1, 0), 0
    );
    const widthPx = (zone.width / 100) * imgWidth;
    const heightPx = (zone.height / 100) * imgHeight;

    // Cap font size at the Hebrew font size
    let lineHeight = 1.25;
    const hebrewFontPx = (zone.avgLineHeight / 100) * imgHeight;
    const maxFs = Math.max(8, Math.floor(hebrewFontPx));
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

// --- CANVAS: ERASE HEBREW TEXT (pixel-level, preserves page colors) ---

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
    const imgData = ctx.getImageData(0, 0, w, h);
    const px = imgData.data;

    const pixLuma = (i: number) => 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2];

    // Erase text in a rectangular region by replacing dark pixels with local background
    const eraseRect = (ex: number, ey: number, ew: number, eh: number) => {
      const x0 = Math.max(0, Math.floor(ex));
      const y0 = Math.max(0, Math.floor(ey));
      const x1 = Math.min(w, Math.ceil(ex + ew));
      const y1 = Math.min(h, Math.ceil(ey + eh));
      if (x1 <= x0 || y1 <= y0) return;

      // Collect all pixel luminances in this region to find the background level
      const lumas: number[] = [];
      for (let y = y0; y < y1; y++) {
        for (let x = x0; x < x1; x++) {
          lumas.push(pixLuma((y * w + x) * 4));
        }
      }
      lumas.sort((a, b) => b - a);

      // Background = brightest 30% of pixels (the gaps between letters)
      const bgCount = Math.max(5, Math.floor(lumas.length * 0.3));
      const bgLuma = lumas[Math.floor(bgCount / 2)]; // median of bright pixels
      // Threshold: anything darker than 85% of background brightness is text
      const threshold = bgLuma * 0.82;

      // Compute the actual background color from the brightest pixels
      const bgR: number[] = [], bgG: number[] = [], bgB: number[] = [];
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

      // Replace dark pixels (text) with the background color
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

    // Erase each OCR line
    for (const line of ocrLines) {
      if (line.width < 1 || line.height < 0.3) continue;

      const lx = (line.x / 100) * w;
      const ly = (line.y / 100) * h;
      const lw = (line.width / 100) * w;
      const lh = (line.height / 100) * h;

      const isPageNum =
        line.y < 4 &&
        line.width < 5 &&
        line.text.trim().length <= 3 &&
        Math.abs(line.x + line.width / 2 - 50) < 5;

      if (isPageNum) {
        // Wider erasure for page number with decorative circle
        const r = Math.max(lw, lh) * 1.8;
        eraseRect(lx + lw / 2 - r, ly + lh / 2 - r, r * 2, r * 2);
      } else {
        const padV = lh * 0.35;
        const padH = lw * 0.06;
        eraseRect(lx - padH - 4, ly - padV, lw + padH * 2 + 8, lh + padV * 2);
      }
    }

    // Second pass: erase gaps between segments on same row (dotted leaders)
    const sortedLines = [...ocrLines]
      .filter((l) => l.width > 1 && l.height > 0.3)
      .sort((a, b) => a.y - b.y);

    if (sortedLines.length > 5) {
      const medH = sortedLines.map((l) => l.height).sort((a, b) => a - b)[
        Math.floor(sortedLines.length / 2)
      ];
      const rowGroups: OcrLine[][] = [[sortedLines[0]]];
      for (let i = 1; i < sortedLines.length; i++) {
        const prev = sortedLines[i - 1];
        const curr = sortedLines[i];
        if (curr.y < prev.y + prev.height || Math.abs(curr.y - prev.y) < medH * 1.5) {
          rowGroups[rowGroups.length - 1].push(curr);
        } else {
          rowGroups.push([curr]);
        }
      }

      for (const row of rowGroups) {
        if (row.length < 2) continue;
        const sorted = [...row].sort((a, b) => a.x - b.x);
        const minY = Math.min(...row.map((l) => l.y));
        const maxYH = Math.max(...row.map((l) => l.y + l.height));
        const bandTop = (minY / 100) * h;
        const bandH = ((maxYH - minY) / 100) * h;

        for (let si = 0; si < sorted.length - 1; si++) {
          const gapLeftPct = sorted[si].x + sorted[si].width;
          const gapRightPct = sorted[si + 1].x;
          if (gapRightPct - gapLeftPct > 3) {
            const gapLeft = (gapLeftPct / 100) * w;
            const gapRight = (gapRightPct / 100) * w;
            eraseRect(gapLeft - 2, bandTop - bandH * 0.15, gapRight - gapLeft + 4, bandH * 1.3);
          }
        }
      }
    }

    // Write modified pixels back to canvas
    ctx.putImageData(imgData, 0, 0);

    // Determine text color per zone from the background luminance
    const median = (arr: number[]) => {
      const s = [...arr].sort((a, b) => a - b);
      return s[Math.floor(s.length / 2)];
    };
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
