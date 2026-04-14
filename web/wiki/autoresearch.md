# Autoresearch

Autoresearch is a systematic parameter optimization methodology inspired by Andrej Karpathy's approach: define binary evals, run experiments that mutate one parameter at a time, score against the evals, keep improvements, discard regressions, and iterate. This project uses autoresearch for two distinct optimization targets: typeset layout quality and illustration crop accuracy.

## Philosophy

The core insight is that optimizing a complex system (like book layout or illustration detection) is really a search problem over a high-dimensional parameter space. Human intuition is bad at this -- a parameter change that seems obviously better might regress five other things. Binary evals make quality objective and reproducible.

Every experiment is logged in a persistent catalog so that work is never lost, even across sessions. The catalog format is JSONL (one JSON object per line) for append-only durability.

## Typeset Layout Autoresearch

### Eval Framework

Three eval scripts exist, each targeting different quality dimensions:

**`scripts/autoresearch-eval-v2.js`** -- 30 layout evals covering:
- E1: Hebrew characters render correctly
- E3: Content completeness (no missing pages/sections)
- E8: Page decoration (borders, headers, page numbers)
- E10: No blank pages
- E30: No empty pages
- Plus 25 other checks for spacing, alignment, font sizing, etc.

**`scripts/autoresearch-artscroll-eval.js`** -- 10 ArtScroll style evals:
- AS1: Inline Hebrew quotes present
- AS2: Ashkenazi terminology used
- AS4: Hebrew quote format (em-dash style)
- Plus 7 other style checks

**`scripts/autoresearch-unified-eval.js`** -- Combines all 40 evals with importance weights:
- Weight 3 (critical): E1, E3, E8, E10, E30, AS1, AS2, AS4
- Weight 2 (important): Most remaining evals
- Weight 1 (polish): Cosmetic refinements

### Experiment Flow

1. **Baseline**: Generate a PDF with current parameters, run all 40 evals, record the score.
2. **Mutate**: Change one parameter (e.g., `bodyFontSize` from 10.5 to 11).
3. **Generate**: Produce a new PDF with the mutated parameter.
4. **Evaluate**: Run all 40 evals on the new PDF.
5. **Decision**: If the score improved, KEEP the change and update the baseline. If it regressed, DISCARD and revert.
6. **Log**: Record the experiment in `autoresearch-results/` with the full score breakdown.

The orchestration scripts (`autoresearch-pipeline.js`, `autoresearch-typeset.js`, `autoresearch-round3.js`) manage this loop automatically.

### Key Results

The typeset parameters were optimized from 83.3% to 100% eval pass rate over 20+ experiments. The winning configuration:
- `bodyFontSize`: 10.5 -> 11 (better readability)
- `lineHeight`: 1.55 -> 1.5 (compensates for larger font)
- `paragraphSpacing`: 8 (visual separation)

Each experiment generates sample PDFs for manual spot-checking, stored in `autoresearch-results/pdfs/exp-{timestamp}-{hash}/`.

## Illustration Crop Autoresearch

### Ground Truth

The ground truth for crop quality comes from user edits in the crop editor UI. When a user locks a page's crops, those crops become the "correct" answer. The autoresearch system compares algorithm-generated crops against these locked crops.

### IoU Scoring

Each crop rectangle is compared against the ground truth using Intersection over Union (IoU):

```
IoU = Area(predicted ∩ ground_truth) / Area(predicted ∪ ground_truth)
```

An IoU above a threshold (typically 0.5) is considered a "hit." The overall score combines hit rate with average IoU across all pages.

### Parameter Sweeps

The V1 (row+column) algorithm has 17 tunable parameters. Autoresearch sweeps one parameter at a time across a range of values:

**Round 1** (25 experiments, `scripts/autoresearch-cropper/results.json`):
- Baseline score: 36.2
- Best score: 50.3
- Key improvements: `sideBySideGap` 0.05 -> 0.1 (+7.8), `minCropHeight` 0.12 -> 0.08 (+6.7), `minBandHeight` 0.035 -> 0.025 (+5.5)

**Round 2** (40 experiments, `scripts/autoresearch-cropper/changelog.md`):
- Baseline score: 65.4 (after round 1 improvements)
- Best score: 71.7
- Key improvements: `rowThreshold` -> 0.03 (+2.7), `minBandHeight` -> 0.03 (+0.5), `minCropHeight` -> 0.04 (+2.3), `colThreshold` -> 0.03 (+0.8)

### Algorithm Racing

Beyond parameter tuning, the system tested 10 fundamentally different algorithms to find the best approach. The race script (`scripts/autoresearch-cropper/race-10-algorithms.js`) evaluated:

1. V1: Row+Column scanning (the original)
2. V2: Blob detection (grid + flood-fill)
3. V3: Sliding window variance
4. V4: Edge detection (gradient-based)
5. V5: HSV saturation analysis
6. V6: Two-pass (coarse scan + fine refinement)
7. V7: Column-first scanning
8. V8: Quadtree subdivision
9. V9: Morphological operations (dilate + flood-fill)
10. V10: Hybrid V1+V7 union

V2 (Blob detection) won at 73.52, beating V1 (Row+Column) at 67.73. The worst performer was V4 (Edge detection) at 21.41 -- text gradients overwhelmed illustration gradients.

### Learning From User Corrections

The feedback loop is:

1. Algorithm generates initial crops for all pages.
2. User reviews pages in the crop editor, correcting bad crops and locking good ones.
3. Autoresearch analyzes the diff between algorithm output and user corrections to understand error patterns (e.g., "threshold too high" -> neutral illustrations missed, "header bars caught" -> header zone needs expansion).
4. Parameters are re-tuned based on the correction patterns.
5. The algorithm re-runs on all UNLOCKED pages with improved parameters.
6. All user-locked pages are preserved untouched.
7. Repeat.

## Experiment Catalog

The `scripts/autoresearch-catalog.js` module provides persistent experiment tracking in JSONL format. Each experiment record includes:
- Unique ID and timestamp
- Parameters used
- Score breakdown (overall, per-eval)
- Status (baseline / keep / discard)
- Description of what changed

This makes it possible to resume optimization across sessions and to review the full history of what was tried.

## File Paths

- Typeset evals: `scripts/autoresearch-eval-v2.js`, `scripts/autoresearch-artscroll-eval.js`, `scripts/autoresearch-unified-eval.js`
- Typeset experiments: `scripts/autoresearch-pipeline.js`, `scripts/autoresearch-typeset.js`, `scripts/autoresearch-round3.js`
- Experiment catalog: `scripts/autoresearch-catalog.js`
- Experiment results: `autoresearch-results/`
- Crop autoresearch runner: `scripts/autoresearch-cropper/run-autoresearch.js`
- Crop algorithm implementations: `scripts/autoresearch-cropper/cropper-skill.js` (V1), `scripts/autoresearch-cropper/cropper-v2-blob.js` (V2)
- Algorithm race: `scripts/autoresearch-cropper/race-10-algorithms.js`
- Race results: `scripts/autoresearch-cropper/race-results.json`
- V1 best params: `scripts/autoresearch-cropper/best-params.json`
- V2 best params: `scripts/autoresearch-cropper/best-params-v2.json`
- Round 1 results: `scripts/autoresearch-cropper/results.json`
- Round 2 changelog: `scripts/autoresearch-cropper/changelog.md`
