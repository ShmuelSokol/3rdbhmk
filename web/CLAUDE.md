# 3rd Beis HaMikdash Translation (3rdbhmk)

## Project Overview
Hebrew-to-English overlay translation of "לשכנו תדרשו" (Lishchno Tidreshu) — a 367-page book about the 3rd Beis HaMikdash per Yechezkel's nevuah. Scanned pages with text in images, architectural illustrations, and diagrams.

## Stack
- **Framework**: Next.js 14 (TypeScript, App Router)
- **Database**: Prisma v5 + Supabase (shared with ocr-hebrew, `bhmk_` prefixed tables)
- **Storage**: Supabase bucket `bhmk`
- **Deployment**: Railway (GitHub auto-deploy on push to `main`, root dir: `web/`)
- **Domain**: https://3rdbhmk.ksavyad.com

## Pipeline
1. **Azure OCR** (`prebuilt-read`, `locale=he`): word-level bounding boxes + Hebrew text
2. **Hebrew text editing**: Manual corrections in web editor
3. **Text-block detection**: Automated grouping, zone classification, safe expansion (`/api/pages/[pageId]/text-blocks`)
4. **Hebrew erasure**: Server-side compositing with locally-sampled background color (`/api/pages/[pageId]/image-erased`)
5. **Claude translation**: Hebrew → Ashkenazi English (Shabbos, Beis HaMikdash, davening, Hashem)
6. **PDF export**: Erased images + English text overlay (`/api/books/[bookId]/export?from=X&to=Y`)

## Key API Endpoints
- `GET /api/pages/[pageId]/text-blocks` — Computes text blocks with safe expansion, centered detection, table/column classification
- `GET /api/pages/[pageId]/image-erased` — Returns page image with Hebrew text erased
- `GET /api/books/[bookId]/export?from=X&to=Y` — PDF export with English overlay
- `GET /api/books/[bookId]/compare` — All pages for comparison/scoring

## Text-Block Algorithm (route.ts)
OCR coordinates are percentages (0-100) of image dimensions.

### Zone Classification
- Per-line classification: each line checked for y-overlapping neighbors at different x positions
- Table zones: lines with overlapping neighbors → column divider detection
- Body zones: grouped with gap-based splitting (GAP_THRESHOLD=2.5%), header splitting at centered→body transitions
- Sparse/diagram table zones reclassified to body text
- Two-column book pages reclassified from table to body

### Block Creation
- **Illustration-gap splitting**: Check pixel variance in gaps between body lines (>1%, variance>200 → split)
- **Column-split illustration-gap splitting**: Same logic applied within two-column split blocks
- **Per-line splitting**: Low-density groups (density<0.06, >1 line, <50 chars) → individual blocks per line
- **Width cap**: Ultra-wide low-char per-line blocks (>50% wide, <20 chars) capped to max(25, chars×2.5)
- **Skip near-empty groups**: Groups with <3 chars skipped entirely

### Safe Expansion
- Vertical: scan strips above/below using pixel variance + RGB color distance
- Horizontal: scan from page center outward, detect illustrations and borders
- LOW_DENSITY_THRESHOLD=0.08: blocks below this get limited expansion (±1% vertical, no horizontal)
- Table blocks: no horizontal expansion
- Reference background color: sampled from inter-line gaps within the block

## Scoring (scripts/score-all-pages.py)
7 binary evals (E1-E7):
- **E3 (placement)**: Text-density weighted illustration overlap. `risk = illust_pct × density_weight × page_sparse_factor`. Density dampening: `max(0.05, 1.0 - textDensity × 6.0)`. Skip centered, table, <30 char, <150 area blocks.
- **E4 (centered)**: Auto-pass for illustration pages (<150 chars), simple pages (≤2 blocks), table pages, diagram pages (<300 max body chars), multi-column layouts.
- **E5 (table)**: Accept large tables (200+ chars) without column dividers.
- Current score: **1790/1790 (100%)** across 358 pages (as of 2026-03-18)

## Infrastructure IDs
- Railway project: `5d90489e-8dfb-4a60-8b19-28c9e603c61b`
- Railway service: `a1b9d33c-7764-487b-92f3-11ba1d2a30f2`
- Railway environment: `f02ad24d-2304-4532-a4de-a32e31e7a9d1` (production)
- Book ID: `jcqje5aut5wve5w5b8hv6fcq8`

## Critical Rules
- Illustrations can be ANYWHERE on the page — NEVER assume photos are only at bottom
- Text blocks MUST NOT overlap illustrations or border designs
- Use pixel variance AND RGB color distance for border detection (threshold 25)
- No white/colored overlay backgrounds — erase Hebrew server-side
- OCR coordinates are percentages (0-100) of image dimensions
- Prisma v5 required (npx pulls v7 which breaks schema)
- Don't hardcode PORT in Dockerfile (Railway sets it)
- Image erased cache version: `pages-erased-v17` — bump when changing erasure algorithm
