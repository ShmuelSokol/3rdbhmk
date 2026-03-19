---
name: hebbookocrtoeng
description: "Hebrew book OCR to English overlay system. Takes scanned Hebrew book pages, erases Hebrew text from the image, and overlays English translations in the correct positions. Handles colored backgrounds, section headers, two-column layouts, tables, and illustrations. Use when: fix overlay, improve erasure, fix text placement, debug compare view, improve OCR display."
---

# Hebrew Book OCR to English Overlay

## The Core Job

Take a scanned Hebrew sefer page and produce a clean English version:
1. **Erase** the Hebrew text from the page image, replacing it with the local background color
2. **Detect** text regions, illustrations, headers, tables, and section dividers
3. **Place** the English translation text into the correct regions with proper sizing and alignment
4. **Preserve** all non-text elements (illustrations, decorative borders, colored backgrounds) untouched

## Architecture

### Three Server Endpoints

1. **`/api/pages/[pageId]/image-erased`** — Produces a PNG of the page with Hebrew text erased
   - Uses Sharp for pixel-level image manipulation
   - Per-line erasure: finds nearest clean row and copies background pixels
   - Adaptive luminance thresholds based on local background color
   - Per-pixel residual cleanup to remove anti-aliased text edges

2. **`/api/pages/[pageId]/text-blocks`** — Computes safe regions for English text placement
   - Groups OCR bounding boxes into logical blocks
   - Detects table vs body text (multi-column detection)
   - Detects centered section headers
   - Expands blocks using pixel analysis (variance + color distance)
   - Returns blocks with: position, size, centered flag, table flag, column dividers

3. **`/api/books/[bookId]/compare`** — Returns all page data for the compare view

### Client Component (`/book/[bookId]/compare/page.tsx`)

- Renders erased image as background
- Overlays English text in positioned div blocks
- Handles table regions (pipe-separated columns)
- Handles body text (paragraph flow with font size optimization)
- Assigns bold/short paragraphs to centered section headers
- Splits table text between multiple table blocks proportionally

## Key Algorithms

### Hebrew Text Erasure (image-erased)

For each OCR text line:
1. Compute erasure rectangle (OCR bounds + 0.4% pad)
2. Sample local background luminance from left/right strips (same y-level)
3. Set adaptive clean threshold = `localBgLum - 40`
4. For each pixel row in the rectangle, find nearest clean row within 60px
5. Copy that row's pixels as replacement
6. Per-pixel cleanup: blend any pixel darker than `localBgLum - 35` toward local bg color
7. Apply blur(2.0) to smooth patch edges

### Text Block Detection (text-blocks)

1. Filter OCR boxes to skip header area (y < 4%)
2. Group boxes into lines by lineIndex
3. Classify lines as multi-column (table) or single-column (body)
4. Group consecutive same-type lines into zones
5. Protect centered zones (width < 30%, symmetrically placed) from table absorption
6. For body zones: split at centered-to-body transitions (header splitting)
7. Expand blocks horizontally/vertically using pixel variance + color distance
8. For centered blocks: scan from text edges outward (not page center)

### Text Assignment (client)

1. Strip known banner patterns (page numbers, "Main Topics") from translation
2. Split translation between table blocks and body blocks
3. For centered header blocks: assign matching bold/short paragraphs first
4. Distribute remaining paragraphs proportionally by Hebrew char count
5. Binary-search optimal font size per block

## Critical Rules

- **Illustrations can be ANYWHERE** on the page — never assume bottom-only
- **Text blocks must NOT overlap illustrations** or decorative borders
- **No white overlay backgrounds** — erase server-side with locally-sampled color
- **OCR coordinates are percentages (0-100)** of image dimensions
- **Adaptive thresholds** — luminance checks must be relative to local background, not hard-coded
- **Centered text detection** uses absolute width check (<30% of page) AND symmetry check
- **Two-column book pages** are NOT tables — centered section dividers between columns must stay as separate body blocks
- **Multiple table blocks** must get SPLIT text, not duplicated text

## File Locations

- `src/app/api/pages/[pageId]/image-erased/route.ts` — Erasure endpoint
- `src/app/api/pages/[pageId]/text-blocks/route.ts` — Block detection endpoint
- `src/app/book/[bookId]/compare/page.tsx` — Client overlay component
- `src/app/api/pages/[pageId]/layout/route.ts` — Claude Vision layout analysis (deprecated for overlay)

## Known Remaining Issues

1. Black residue on some white backgrounds where text was erased
2. Color mismatch on colored tile backgrounds (yellow/tan/orange) in some cases
3. Two-column pages treated as tables — body text should ideally be single-column English
4. Font sizing can be suboptimal when blocks have very different Hebrew/English char ratios
5. Centered text expansion sometimes blocked by adjacent visual elements
6. Table column count mismatch between translation pipes and detected dividers
