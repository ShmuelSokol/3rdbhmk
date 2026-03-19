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

## Key Decisions (2026-03-19)
- **bidi-js** chosen over Puppeteer for pdf-lib renderer (low migration, fast)
- **Playwright HTML-to-PDF** added as primary renderer for perfect bidi
- **Never increase paragraphSpacing above 10** — caused blank pages at 20
- **Never add middle-dot separators** — visual noise
- **safeMarginBottom = cfg.marginBottom + 20** — text must NEVER touch page numbers
- **Minimum 70% image size** — if doesn't fit at 70%, start new page
- **Letter pages = source pages 4-12** with any letter keyword match
- **Hebrew TOC pages skipped** — dynamic English TOC generated instead
- **isDiagramPage()** requires 2+ markers in short regions, or 1 marker + 30% short labels

## Infrastructure
- Railway project: `5d90489e-8dfb-4a60-8b19-28c9e603c61b`
- Railway service: `a1b9d33c-7764-487b-92f3-11ba1d2a30f2`
- Supabase exports: `bhmk/exports/Lishchno_Tidreshu_*.pdf`

## Critical Rules
- Illustrations can be ANYWHERE — NEVER assume photos are only at bottom
- OCR coordinates are percentages (0-100) of image dimensions
- Prisma v5 required (npx pulls v7 which breaks schema)
- Don't hardcode PORT in Dockerfile (Railway sets it)
- `NEXT_PUBLIC_` env vars must be at build time; use bracket notation for runtime
- Always check for regressions with unified eval after changes
