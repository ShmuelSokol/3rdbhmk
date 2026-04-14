# System Architecture

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 14, TypeScript, App Router |
| Database | PostgreSQL via Supabase (shared instance with ocr-hebrew project) |
| ORM | Prisma v5 (v7 breaks schema syntax -- always pin to v5) |
| Storage | Supabase Storage, bucket `bhmk` |
| Deployment | Railway, GitHub auto-deploy on push to `main` |
| PDF Rendering | Playwright/Chromium (primary), pdf-lib (fallback) |
| OCR | Azure Computer Vision |
| Translation | Claude (Anthropic) |
| Image Processing | sharp |

## Directory Structure

```
web/
  src/
    app/
      api/
        books/[bookId]/
          typeset/route.ts      -- Main PDF generation endpoint
          illustration-crops/route.ts -- Crop data API
          export/route.ts       -- PDF export/upload to Supabase
          compare/route.ts      -- Side-by-side comparison
          page-image/route.ts   -- Source page image serving
          pipeline/route.ts     -- Pipeline status/trigger
        pages/[pageId]/
          ocr/route.ts          -- OCR trigger
          translate/route.ts    -- Translation trigger
          pipeline/route.ts     -- Per-page pipeline
          text-blocks/route.ts  -- Text block extraction
          boxes/route.ts        -- Bounding box management
          flags/route.ts        -- QA flags
      book/[bookId]/
        page.tsx               -- Book overview page
        crops/page.tsx         -- Crop editor UI
        compare/page.tsx       -- Side-by-side compare
        pipeline/page.tsx      -- Pipeline dashboard
        page/[pageNumber]/page.tsx -- Per-page view
    lib/
      html-book-generator.ts   -- HTML renderer (Playwright path)
      prisma.ts               -- Prisma client singleton
      supabase.ts             -- Supabase client
      azure-ocr.ts            -- Azure OCR integration
      translate.ts            -- Claude translation
      pdf-utils.ts            -- Shared PDF utilities
      compute-text-blocks.ts  -- Text block computation
      illustration-crops.json -- Cached crop coordinates
      pipeline/
        config.ts             -- Pipeline configuration
        shared.ts             -- Shared pipeline utilities
        step1-ocr.ts          -- OCR via Azure
        step2-regions.ts      -- Region detection/grouping
        step3-erase.ts        -- Hebrew text erasure from images
        step4-expand.ts       -- Region coordinate expansion
        step5-fit.ts          -- English text fitting
        step6-verify.ts       -- Verification OCR
  scripts/
    enhance-artscroll.js      -- Batch ArtScroll enhancement
    insert-pesukim-hebrew.js  -- Hebrew pasuk insertion
    autoresearch-eval-v2.js   -- 30 layout evals
    autoresearch-artscroll-eval.js -- 10 ArtScroll evals
    autoresearch-unified-eval.js   -- Combined 40 evals
    autoresearch-catalog.js   -- Experiment tracking (JSONL)
    autoresearch-pipeline.js  -- Autoresearch orchestrator
    autoresearch-typeset.js   -- Typeset parameter optimization
    autoresearch-round3.js    -- Round 3 experiments
    autoresearch-cropper/     -- Illustration crop optimization
      run-autoresearch.js     -- Crop parameter sweeps
      cropper-skill.js        -- V1 row+column algorithm
      cropper-v2-blob.js      -- V2 blob detection algorithm
      race-10-algorithms.js   -- Algorithm tournament
      best-params.json        -- V1 optimized parameters
      best-params-v2.json     -- V2 optimized parameters
      race-results.json       -- Tournament results
    batch-translate.js        -- Bulk translation runner
    proofread-book.js         -- Proofreading script
    audit-illustrations.js    -- Illustration audit
    audit-translations.js     -- Translation quality audit
  autoresearch-results/       -- Experiment PDFs and baselines
  public/
    illustration-crops.json   -- User-edited crop overrides
  prisma/
    schema.prisma             -- Database schema
```

## Database Schema

All tables are prefixed with `bhmk_` because the Supabase instance is shared with the ocr-hebrew project. The schema is defined in `prisma/schema.prisma`.

### Core Models

**Book** -- Top-level entity. The project has a single book with ID `jcqje5aut5wve5w5b8hv6fcq8`. Contains `name`, `filename`, `totalPages`, and a relation to all pages.

**Page** -- One row per source page (367 total). Tracks `pageNumber`, `imageUrl` (Supabase storage path), `status`, and `pipelineStatus` which progresses through: `pending` -> `step1_ocr` -> `step2_regions` -> `step3_erased` -> `step4_expanded` -> `step5_fitted` -> `step6_verified` -> `locked`. A `lockedAt` timestamp indicates user-approved pages.

**OCRResult** -- Azure OCR output for each page, stored as raw JSON. Links to BoundingBox records.

**BoundingBox** -- Individual text detection: coordinates (x, y, width, height as percentages of image dimensions), `hebrewText`, optional `editedText` and `englishText`, `confidence`, `lineIndex`, `wordIndex`, `isImage` flag, `textPixelSize`, `isBold`, and a `regionId` link to ContentRegion after step 2.

**ContentRegion** -- Grouped content areas on a page, typed as `body`, `header`, `footer`, `table`, or `image`. Has three sets of coordinates: `orig*` (from detection), `expanded*` (after step 4 expansion), and `manual*` (user overrides). Stores `hebrewText` and `translatedText` for each region, plus `fittedFontSize` and `fittedText` from step 5.

**Translation** -- Page-level translation record with `hebrewInput`, `englishOutput`, `status` (draft/reviewed), and `reviewNotes`.

**Flag** -- QA markers placed on specific page coordinates, typed and optionally noted.

**ErasedImage** -- The source page image with Hebrew text removed, stored in Supabase.

**FittedPage** -- The final fitted page output after step 5.

**VerificationOcr** -- OCR results from step 6 verification pass.

## Supabase Storage

The `bhmk` bucket stores:
- Source page images (uploaded from the Hebrew PDF)
- Erased images (Hebrew text removed)
- Exported PDFs at `bhmk/exports/Lishchno_Tidreshu_*.pdf`
- The Hebrew original PDF parts (19 parts)

## Railway Deployment

The app deploys to Railway from the `web/` root directory. The Dockerfile uses `node:20-slim` (Debian-based, not Alpine) to support Playwright/Chromium. Key environment variables:

- `DATABASE_URL` -- Supabase pooler connection string (always `aws-1-us-east-1.pooler.supabase.com`)
- `DIRECT_URL` -- Supabase direct connection for migrations
- `PLAYWRIGHT_BROWSERS_PATH` -- Must be set for Chromium to be found
- `HOME=/home/nextjs` -- Required for Playwright on Railway
- `PORT` -- Set by Railway, never hardcode

Critical: use `process.env["KEY"]` bracket notation for runtime env vars. Next.js standalone mode inlines `process.env.KEY` dot notation at build time.

## Health Check

A `/api/health` endpoint is present on all Railway services, returning a simple 200 OK for uptime monitoring.
