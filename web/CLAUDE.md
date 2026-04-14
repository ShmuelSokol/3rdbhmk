# 3rd Beis HaMikdash Translation (3rdbhmk)

## Project Overview
Hebrew-to-English typeset book of "לשכנו תדרשו" (Lishchno Tidreshu) — 367-page book about the 3rd Beis HaMikdash per Yechezkel's nevuah. Produces a print-ready English PDF with ArtScroll-style inline Hebrew, illustrations, and diagrams.

## Stack
- **Framework**: Next.js 14 (TypeScript, App Router)
- **Database**: Prisma v5 + Supabase (shared with ocr-hebrew, `bhmk_` prefixed tables)
- **Storage**: Supabase bucket `bhmk`
- **Deployment**: Railway (GitHub auto-deploy on push to `main`, root dir: `web/`)
- **Domain**: https://3rdbhmk.ksavyad.com
- **Book ID**: `jcqje5aut5wve5w5b8hv6fcq8`

## Typeset PDF System (`/api/books/[bookId]/typeset`)
Two renderers available via `?renderer=html|pdflib`:

### HTML Renderer (default, Playwright/Chromium)
- `src/lib/html-book-generator.ts` — generates full HTML book
- Playwright converts HTML → PDF with native HarfBuzz bidi
- Perfect Hebrew RTL rendering, no rectangle artifacts
- NotoSerifHebrew fonts embedded as base64 in CSS
- **Status**: Hebrew renders perfectly but needs CSS polish (borders, spacing, TOC page numbers)

### pdf-lib Renderer (fallback)
- `src/app/api/books/[bookId]/typeset/route.ts` — 2000+ lines
- Uses pdf-lib + fontkit + bidi-js for text rendering
- Has all layout features (borders, headers, page numbers, TOC)
- Hebrew bidi partially working (word order issues remain)

### Key Features (both renderers)
- **ArtScroll-style translations**: inline Hebrew chars, Ashkenazi English, source citations
- **681 regions enhanced** with Hebrew quotes via `scripts/enhance-artscroll.js`
- **Dynamic TOC**: 40+ entries with topic descriptions, auto-calculated page numbers
- **Letter pages**: full original image + clean English translation below (pages 4-12)
- **Diagram pages**: full page image + description for pages with many short labels
- **Illustration detection**: gap-based cropping, border trimming, variance filtering
- **Topic breaks**: new pages for new sections, orphan prevention
- **Page design**: double-line border frame, running header, page numbers

### TypesetConfig (tunable parameters)
```
pageWidth: 468 (6.5"), pageHeight: 648 (9"), margins: 54pt
bodyFontSize: 11, headerFontSize: 14, lineHeight: 1.5
paragraphSpacing: 8, firstLineIndent: 18
illustrationMaxWidth: 0.95, illustrationPadding: 10
safeMarginBottom: marginBottom + 20 (NEVER reduce)
```

### Topic Description Map
65 hardcoded Perek:Pasuk → topic descriptions for TOC (e.g., '40:5': 'The Wall of Har HaBayis')

## Eval Framework
- `scripts/autoresearch-eval-v2.js` — 30 layout evals
- `scripts/autoresearch-artscroll-eval.js` — 10 ArtScroll style evals
- `scripts/autoresearch-unified-eval.js` — combined 40 evals with importance weights (3=critical, 2=important, 1=polish)
- `scripts/autoresearch-catalog.js` — persistent experiment tracking (JSONL catalog)
- Results in `autoresearch-results/`

### Eval Weights (critical = 3)
E1 Hebrew chars, E3 completeness, E8 decoration, E10 no blank pages, E30 no empty pages, AS1 inline Hebrew, AS2 Ashkenazi terms, AS4 Hebrew quote format

## Translation Enhancement
- `scripts/enhance-artscroll.js` — batch enhances translations with inline Hebrew
- Inserts Hebrew source text with em-dash format: "Hebrew — English"
- Replaces spelled-out Hebrew letter names with actual characters
- Citation normalization: Chapter→Perek, verse→Pasuk, folio→Daf
- Run with `--force` to re-enhance, only processes eval page ranges by default

## Key Decisions
- **Playwright HTML-to-PDF** is primary renderer for perfect Hebrew bidi
- **pdf-lib** is fallback renderer (Hebrew bidi partially broken)
- **Never add middle-dot separators** — visual noise
- **Letter pages = source pages 4-12** with any letter keyword match
- **Hebrew TOC pages skipped** — dynamic English TOC generated instead
- **Pages 3-70 skipped** — duplicate short version; expanded version at pages 71+ is used

## Infrastructure
- Railway project: `5d90489e-8dfb-4a60-8b19-28c9e603c61b`
- Railway service: `a1b9d33c-7764-487b-92f3-11ba1d2a30f2`
- Supabase exports: `bhmk/exports/Lishchno_Tidreshu_*.pdf`

## Current Methodology (English Typeset PDF)

The workflow is NOT overlay-on-Hebrew-pages. It's a fully separate English book with illustrations extracted from the Hebrew source.

### OCR & Source Analysis
1. OCR the Hebrew book and record: paragraph spacing, text size, centered text, image placement
2. Image placement is its own flow — bounding box detector with user-approved crops (lock pages you like, algorithm improves from your edits via autoresearch)
3. If an image has a header/footer caption explaining it, place that caption directly above/below the image in the English version

### Hebrew Quotes & Translation Style
- When Hebrew text quotes a pasuk from Tanach or Gemara, include the quote in Hebrew with the Perek or Daf reference
- Translate the quote if it helps the flow make sense to an average Ashkenazi frum-from-birth Jew
- ArtScroll em-dash format: "Hebrew — English translation (Source reference)"
- Hebrew text MUST have proper spacing between Hebrew and English (space + em-dash + space)
- When source has numbered items (itemized list), the number should appear ONCE on the correct side (before the English text, not duplicated or placed on wrong side of Hebrew)
- Hebrew and English should flow naturally in the same paragraph — no abrupt joins or missing whitespace
- Translations should be as close to ArtScroll style as possible (scholarly, flowing English with Hebrew terms sprinkled in, proper source citations)

### Image Placement Rules
- Images should be at the BOTTOM of the page when nothing follows the image on that page (image + its accompanying caption text included)
- Illustrations can appear ANYWHERE in the source — never assume they're only at bottom
- Image crops: user locks approved pages, algorithm regenerates remaining pages learning from user edits
- Minimum 70% image size — if doesn't fit at 70%, start new page

### Page Break Rules
- Start a new page wherever the Hebrew version intentionally started a new page with a new topic
- Analyze the Hebrew source to detect intentional page breaks (new section/topic starts)
- Mirror those page breaks in the English version

### Avoiding Blank Pages
- If a page has under 5 lines of text with no images (mostly blank), fit that content on the previous page by slightly decreasing font size
- Never leave near-empty pages

### Text Justification
- Text blocks should be FULLY JUSTIFIED — words hugging both left and right margins with slight margin from page border
- Use variable word spacing to get the right edge of text close to the right margin without overflowing to the next line
- Both left and right margins should look clean and aligned

## Infrastructure Rules
- OCR coordinates are percentages (0-100) of image dimensions
- Prisma v5 required (npx pulls v7 which breaks schema)
- Don't hardcode PORT in Dockerfile (Railway sets it)
- `NEXT_PUBLIC_` env vars must be at build time; use bracket notation for runtime
- Always check for regressions with unified eval after changes
