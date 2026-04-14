# Illustration System

The illustration system is responsible for extracting clean illustration images from the Hebrew source pages and inserting them into the English PDF at the correct locations. This is one of the most technically challenging parts of the project because illustrations in the Hebrew book appear inline with Hebrew text, in colored header bars, on cream-colored backgrounds, and in varying sizes and positions.

## The Problem

The Hebrew source pages contain a mix of:
- Body text in Hebrew
- Colored section header bars (green, blue, etc.)
- 3D architectural renders of the Beis HaMikdash
- Floor plan diagrams with labeled rooms
- Cross-section schematics
- Tables with text

The goal is to extract ONLY the illustrations (renders, diagrams, floor plans) without Hebrew text, header bars, or page chrome. Simply showing the full Hebrew source page in the English book is unacceptable -- readers would see Hebrew text they cannot read alongside the English translation.

## The Pipeline

The illustration pipeline has evolved through multiple approaches:

### Stage 1: Full Page Images (Initial)

The first version simply inserted the full Hebrew source page image wherever an illustration was detected. This was shipped as the MVP but was clearly wrong -- 188 pages showed full Hebrew source images, and many "illustration pages" were actually text-only pages that happened to have colored section headers.

### Stage 2: Row-Based Color Density Analysis (V1)

The first algorithmic approach analyzed each source page image row by row:

1. For each row of pixels, compute the "color density" -- the fraction of pixels that are not white/cream (background) and not black (text).
2. Rows with color density above `rowThreshold` (tuned to 0.045) are marked as "illustration rows."
3. Adjacent illustration rows are merged into vertical bands, with a `mergeGap` parameter controlling how far apart bands can be and still merge.
4. Bands shorter than `minBandHeight` (3% of page height) are discarded.
5. Within each band, column analysis finds the horizontal extent of the illustration using a similar threshold (`colThreshold` = 0.03).
6. Header bars in the top portion of the page (controlled by `headerMaxY` and `headerMaxH`) are filtered out.
7. Final crop rectangles are validated against `minCropHeight` and `minCropWidth`.

This approach worked well for large, colorful illustrations but struggled with:
- Neutral-colored illustrations (grayscale diagrams on cream backgrounds)
- Small illustrations scattered across the page
- Side-by-side illustration pairs

The V1 parameters, after 40 autoresearch experiments across 8 parameter dimensions, achieved a best score of 71.7.

### Stage 3: Blob Detection (V2)

The second algorithmic generation replaced row-column scanning with a proper blob detection approach:

1. Divide the page image into a grid (375 columns x 315 rows).
2. For each cell, compute whether it contains "interesting" pixels -- those outside the background brightness range (`brightnessMin` to `brightnessMax`), with sufficient color range (`minColorRange`), and not matching the cream page color (`creamR/G/B` with `creamRange` tolerance).
3. Cells exceeding `cellThreshold` (10%) interest are marked active.
4. Connected components (blobs) are found via flood-fill on the active cell grid.
5. Blobs smaller than `minBlobCells` (180 cells) or narrower than `minBlobWidth` (20% of page) or shorter than `minBlobHeight` (9.6% of page) are discarded.
6. Header zone filtering removes blobs in the top `headerZone` (21%) that are shorter than `headerMaxHeight` (21.4%).
7. Remaining blobs are padded by `padding` (0.7%) on all sides to produce final crop rectangles.

The V2 blob detection scored 73.52 in the algorithm race -- the best of all 10 algorithms tested.

### Stage 4: User Corrections via Crop Editor

No algorithm is perfect for all 297 illustration pages. The crop editor UI (see [crop-editor.md](crop-editor.md)) allows the user to manually adjust, add, or remove crop rectangles. These manual edits are saved and the algorithm learns from them via autoresearch (see [autoresearch.md](autoresearch.md)).

## Algorithm Race: 10 Algorithms Tested

A head-to-head tournament was run across all illustration pages, scoring each algorithm against user-approved ground truth crops using IoU (Intersection over Union). The results:

| Rank | Algorithm | Score | Time |
|------|-----------|-------|------|
| 1 | V2: Blob detection | 73.52 | 0.7s |
| 2 | V10: Hybrid V1+V7 union | 68.06 | 1.4s |
| 3 | V1: Row+Column (original) | 67.73 | 0.9s |
| 4 | V6: Two-pass (coarse+fine) | 67.17 | 1.1s |
| 5 | V7: Column-first | 65.27 | 0.7s |
| 6 | V5: HSV saturation | 62.41 | 0.7s |
| 7 | V8: Quadtree subdivision | 48.85 | 0.6s |
| 8 | V9: Morphological (dilate+flood) | 47.26 | 0.6s |
| 9 | V3: Sliding window variance | 46.46 | 0.7s |
| 10 | V4: Edge detection (gradient) | 21.41 | 0.7s |

The blob detection algorithm won decisively. Edge detection performed worst because the Hebrew text itself creates strong gradients that the algorithm cannot distinguish from illustration edges.

## Autoresearch Parameter Optimization

After the algorithm race selected V2 blob detection, extensive parameter sweeps were run. See [autoresearch.md](autoresearch.md) for the full methodology. Key results:

**V1 Parameters (40 experiments, round 2):**
- Baseline score: 65.4
- Best score: 71.7 (after sweeping `rowThreshold`, `minBandHeight`, `mergeGap`, `headerMaxY`, `headerMaxH`, `minCropHeight`, `colThreshold`)
- Four parameters improved: `rowThreshold` -> 0.03, `minBandHeight` -> 0.03, `minCropHeight` -> 0.04, `colThreshold` -> 0.03

**V1 Parameters (25 experiments, round 1):**
- Baseline score: 36.2
- Best score: 50.3 (after `sideBySideGap`, `minCropHeight`, `minBandHeight`, `colThreshold`, `rowThreshold` improvements)

**V2 Parameters (best-params-v2.json):**
- `gridCols`: 375, `gridRows`: 315
- `cellThreshold`: 0.1
- `minBlobCells`: 180
- `minBlobWidth`: 0.2, `minBlobHeight`: 0.096
- `headerZone`: 0.21, `headerMaxHeight`: 0.214
- `padding`: 0.007
- `brightnessMax`: 215, `brightnessMin`: 15
- `minColorRange`: 3.825
- `creamR/G/B`: 195/180/174, `creamRange`: 31.5

## Known Diagram Pages

25 pages are hardcoded as "known diagram pages" that receive full-page treatment (the entire source image is shown with an English caption): pages 22, 24, 26, 36, 38, 40, 41, 47, 48, 57, 64, 132, 160, 166, 188, 196, 203, 215, 221, 270, 271, 284, 295, 296, 348. These pages contain architectural schematics with so many small labels that cropping individual illustrations would be meaningless -- the entire page IS the illustration.

## Image Processing

Crop rectangles are defined as percentages of the source image dimensions (`topPct`, `leftPct`, `widthPct`, `heightPct`). When the typeset route encounters an illustration element, it:

1. Loads the source page image from Supabase storage
2. Applies the crop rectangle using `sharp` to extract the illustration region
3. Scales the result to fit within `illustrationMaxWidth` (85% of text width) while maintaining aspect ratio
4. Enforces a minimum 70% image size -- if an illustration cannot fit at 70% of its intended size on the current page, a page break is inserted first
5. Converts to PNG buffer and creates a `ContentElement` with `type: 'illustration'`

## File Paths

- Crop data: `src/lib/illustration-crops.json` (algorithm output), `public/illustration-crops.json` (user overrides)
- Crop API: `src/app/api/books/[bookId]/illustration-crops/route.ts`
- Crop editor: `src/app/book/[bookId]/crops/page.tsx`
- V1 algorithm: `scripts/autoresearch-cropper/cropper-skill.js`
- V2 algorithm: `scripts/autoresearch-cropper/cropper-v2-blob.js`
- Algorithm race: `scripts/autoresearch-cropper/race-10-algorithms.js`
- Autoresearch runner: `scripts/autoresearch-cropper/run-autoresearch.js`
- Best parameters: `scripts/autoresearch-cropper/best-params.json` (V1), `scripts/autoresearch-cropper/best-params-v2.json` (V2)
