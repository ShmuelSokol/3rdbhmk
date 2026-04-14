# Typeset System

The typeset system is the heart of the project. It takes the translated content, illustration crops, and layout rules and produces a print-ready PDF. The main endpoint is `/api/books/[bookId]/typeset` and the implementation lives in two files:

- `src/app/api/books/[bookId]/typeset/route.ts` -- The pdf-lib renderer (~2000+ lines) and the orchestration logic that builds `ContentElement[]`
- `src/lib/html-book-generator.ts` -- The HTML/Playwright renderer

## Two Renderers

The system supports two rendering backends, selectable via the `?renderer=html|pdflib` query parameter.

### HTML Renderer (Playwright/Chromium) -- Primary

The HTML renderer is the primary path because Chromium's native HarfBuzz engine handles Hebrew bidirectional text correctly with zero manual intervention. The flow is:

1. `generateHtmlBook(elements, config, tocEntries)` in `html-book-generator.ts` converts `ContentElement[]` into a single HTML document with embedded CSS.
2. NotoSerifHebrew fonts are embedded as base64 data URIs in the CSS, so no external font loading is needed.
3. Inline Hebrew text is wrapped in `<bdi dir="rtl" class="hebrew">` tags by the `markupBidi()` function, which walks through text character by character detecting Hebrew Unicode ranges (U+0590-U+05FF, U+FB1D-U+FB4F).
4. `htmlToPdf()` launches Playwright, loads the HTML, and calls `page.pdf()` with configured page size, margins, and `displayHeaderFooter` for running headers and page numbers.
5. The border strategy uses CSS `position:fixed` pseudo-elements for left/right borders (which repeat on every printed page) while top/bottom borders, running headers, and page numbers go through Playwright's `displayHeaderFooter` option.

**Status**: Hebrew renders perfectly. Some CSS polish needed for borders, spacing, and TOC page numbers.

### pdf-lib Renderer -- Fallback

The pdf-lib renderer is the original implementation and has all layout features fully built (borders, headers, page numbers, TOC), but Hebrew bidi is partially broken -- word order can be incorrect because pdf-lib renders glyphs left-to-right and the manual `bidi-js` integration does not perfectly handle all edge cases. The code uses `splitBidi()` and `getVisualSegments()` functions to split text into Hebrew/Latin segments for font switching, but complex mixed-direction paragraphs sometimes render incorrectly.

**When `keepHebrew=false`**: Hebrew characters are stripped entirely from body text via `sanitizeForPdf()`, which removes all characters in the U+0590-U+05FF range. This is the default for pdf-lib to avoid garbled output.

**When `keepHebrew=true`**: Hebrew is preserved, bidi marks are stripped, and the renderer attempts font-switching between NotoSerifHebrew and the Latin font. Used only with the HTML renderer where HarfBuzz handles everything.

## ContentElement

The `ContentElement` interface is the universal intermediate representation that both renderers consume:

```typescript
interface ContentElement {
  type: 'header' | 'body' | 'illustration' | 'divider' | 'table' | 'caption'
  text?: string            // For header, body, caption
  isAllBold?: boolean      // Bold rendering hint
  imageData?: Buffer       // PNG buffer for illustrations
  imageWidth?: number      // Pixel dimensions
  imageHeight?: number
  pageNumber?: number      // Source page number (for illustration tracking)
  rows?: string[][]        // For table elements
}
```

The typeset route constructs this array by iterating through all source pages (71-367, skipping 3-70), querying each page's ContentRegion records from the database, and converting them:

- `header` regions become `ContentElement` with `type: 'header'`
- `body` regions become `type: 'body'` with the translated text
- `image` regions or pages with illustration crops become `type: 'illustration'` with the cropped image buffer
- Tables detected in the source become `type: 'table'` with row data
- Dividers between major sections become `type: 'divider'`
- Image captions become `type: 'caption'`

## TypesetConfig

All layout parameters are tunable and were optimized via autoresearch experiments:

```
pageWidth: 468 points (6.5 inches) -- book trim size
pageHeight: 648 points (9 inches)
marginTop: 54 points (0.75 inch)
marginBottom: 54 points
marginLeft: 54 points
marginRight: 54 points
bodyFontSize: 11 -- optimized from 10.5 (better readability)
headerFontSize: 14
subheaderFontSize: 12
lineHeight: 1.5 -- optimized from 1.55 (compensates for larger font)
paragraphSpacing: 8 points
headerSpacingAbove: 14
headerSpacingBelow: 6
illustrationMaxWidth: 0.85 (fraction of text width)
illustrationPadding: 10 points
textColor: [0.12, 0.10, 0.08] -- near-black, warm
headerColor: [0.08, 0.06, 0.04] -- darker
pageNumberFontSize: 9
firstLineIndent: 18 points
illustrationGapThreshold: 8 (% of page height)
safeMarginBottom: marginBottom + 20 (NEVER reduce this)
```

The comment in the source says "Optimized via autoresearch (20 experiments, 83.3% -> 100%)" for the best combo of bodyFontSize 11, paragraphSpacing 8, and lineHeight 1.5.

## Page Assembly Flow

The typeset route follows this sequence:

1. **Load all pages** from the database for the given book ID, ordered by page number.
2. **Skip pages 3-70** (duplicate short version).
3. **Build front matter**: cover page, letter pages (source pages 4-12 rendered as full image + clean English translation), foreword.
4. **Build content elements**: For each page 71-367, load ContentRegion records, convert translated text to body elements, detect topic breaks, insert illustrations.
5. **Generate dynamic TOC**: 65 hardcoded Perek:Pasuk topic descriptions (e.g., `'40:5': 'The Wall of Har HaBayis'`), page numbers calculated from the assembled content.
6. **Insert TOC** at page index 2 (after cover and title page, before content).
7. **Move back cover** to the end.
8. **Apply page break rules**: new pages for new sections, orphan prevention, blank page avoidance.
9. **Render**: Pass `ContentElement[]` to the selected renderer.

## Special Page Types

### Letter Pages (Source Pages 4-12)

Any page whose text matches letter-related keywords is rendered as a "letter page": the full original source image displayed at the top, with a clean English translation typeset below. This preserves the visual character of approbation letters and introductory material.

### Diagram Pages

Pages with many short labeled elements (architectural diagrams with Hebrew labels) are rendered as "diagram pages": the full source image is displayed at full page width with a brief English description beneath. The `knownDiagrams` list hardcodes which source pages receive this treatment: pages 22, 24, 26, 36, 38, 40, 41, 47, 48, 57, 64, 132, 160, 166, 188, 196, 203, 215, 221, 270, 271, 284, 295, 296, 348.

### Hebrew TOC Pages

The Hebrew source book's own table of contents is skipped entirely. A dynamic English TOC is generated instead, with auto-calculated page numbers that update every time the book is re-typeset.

## Text Cleaning

Before text reaches the renderer, it passes through several cleaning functions:

- `cleanTranslationText()` -- removes `[THIS IS TABLE]`, `[DIAGRAM:]`, `[END TABLE]`, `[Note:...]` markers, fixes camelCase joins like `westIts` -> `west Its`
- `sanitizeForPdf(text, keepHebrew)` -- strips control characters, bidi marks, zero-width characters; optionally strips all Hebrew for the pdf-lib path
- Recurring running header filtering -- headers under 120 characters that repeat across pages (like "Introduction - History of the Mishkan" or "To His dwelling you shall seek") are filtered out

## Chunked Generation

The full 353-page PDF exceeds Supabase's 50MB upload limit, so the export process splits the output into three parts (Part1, Part2, Part3) and uploads each separately. The `nocover` parameter allows generating chunks without the cover page.
