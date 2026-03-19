# Autoresearch Changelog — hebbookocrtoeng

## Experiment 0 — baseline

**Score:** 20/35 (57.1%)
**Change:** None — original skill, no changes
**Result:** Baseline established. Key failures:
- Erasure quality: Only page 4 (white bg) passes. Pages with colored tiles (10), illustrations (22), complex layouts (33) show visible residue
- Color matching: Pages with yellow/orange backgrounds (10, 22, 33) have erasure artifacts that don't blend
- Text placement: Pages with illustrations (22) and complex diagrams (33) have text blocks overlapping visual elements
- Table detection: Two-column book pages (12) wrongly classified as tables; illustration pages (22) detected as tables
- Text sizing: Pages with mixed illustrations+text (22, 33) get wrong avgLineHeight for font sizing

**Weakest evals:** Erasure (1/5), Color match (2/5), Placement (2/5), Tables (2/5)
**Strongest evals:** Centered headers (5/5), Text color (5/5)

## Experiment 1 — keep

**Score:** 21/35 (60.0%)
**Change:** Added sparse-table detection after zone merging. Calculates unique y-coverage (merging overlapping line ranges) and gap sizes for each merged table zone. Reclassifies as body text if median gap > 3% or any gap > 8%.
**Reasoning:** Pages with illustrations (22) had scattered captions wrongly classified as one huge table zone spanning 87% of the page. Real tables have dense, evenly-spaced rows; illustration pages have large gaps.
**Result:** Page 22 eval 5 (table columns) flipped from FAIL to PASS — no longer wrongly treated as table. Pages 4, 10, 12, 33 unchanged. Briefly regressed page 10 (real table) when density threshold was too aggressive (0.7) — fixed by using only gap-based thresholds.
**Failing outputs:** Page 22 still has 5 zero-width blocks and many tiny blocks. Page 33 still has diagram labels treated as tables. Pages 10, 12 erasure quality unchanged.

## Experiment 2 — discard

**Score:** 21/35 (60.0%)
**Change:** Tightened per-pixel cleanup: floor from localBgLum-35 to -30, blending divisor from 100 to 60.
**Reasoning:** Anti-aliased text edges survive the current cleanup. Tighter floor and more aggressive blending should catch faint residue.
**Result:** No visible improvement. File sizes barely changed (<0.1%). The residue is likely from the reference row itself (copied from adjacent clean row that has its own anti-aliasing), not from the cleanup pass.
**Failing outputs:** Same as experiment 1.

## Experiment 3 — discard

**Score:** 21/35 (60.0%)
**Change:** Two-pass erasure: pass 1 soft blend (same as before), pass 2 hard replace any pixel darker than localBgLum-20 with sampled bg color.
**Reasoning:** The reference row itself contains anti-aliased edges. Soft blending alone can't fully remove them. Hard replacement should catch all remaining dark pixels.
**Result:** Page 12 visually cleaner (fewer scattered dots, -0.6% file size). Other pages marginally improved. But no eval flipped from FAIL to PASS — binary evals too coarse for this incremental improvement. Reverted.
**Failing outputs:** Same as experiment 1. Erasure eval remains at 1/5.

## Experiment 4 — keep (bug fix)

**Score:** 21/35 (60.0%)
**Change:** Added minimum line width (2%) for OCR lines, filter out blocks with width < 3%, height < 0.5%, or < 2 chars.
**Reasoning:** Zero-width blocks from single-point OCR boxes can't display text and waste paragraph assignments.
**Result:** Page 22: 28→23 blocks (5 zero-width removed). Page 33: 7→5 blocks (2 removed). No eval flip but fixes real bugs.

## Experiment 5 — keep

**Score:** 23/35 (65.7%)
**Change:** Two-column book page detection. When a table zone has exactly 1 column divider near the center (±8%), wide block (>75%), and dense text (>400 chars), reclassify as body text. Also fixed hasTableRegions to compute from final blocks.
**Reasoning:** Page 12 has two-column Hebrew book text incorrectly classified as a table. The single centered divider + dense text + full-width block distinguishes it from real tables (page 10: off-center divider, fewer chars, narrower).
**Result:** Page 12 eval 3 (placement) and eval 5 (table columns) both flipped FAIL→PASS. Score 4/7→6/7 (+2 points). Page 10 real table preserved. No regressions.
**Failing outputs:** Page 12 eval 1 (erasure residue) still fails. Pages 22, 33 text placement and sizing still problematic.

## Experiment 6 — keep

**Score:** 24/35 (68.6%)
**Change:** Increased blur radius from 2.0 to 4.0 on erasure patches in image-erased endpoint. Cache version bumped to v13.
**Reasoning:** Previous erasure experiments (2, 3) targeted per-pixel cleanup but the residue comes from the reference row itself containing anti-aliased edges. Stronger blur should smooth out these artifacts post-compositing.
**Result:** Page 12 eval 1 (erasure) flipped FAIL→PASS. File size dropped -33% for page 12 (smoother patches compress better). Pages 22, 33 showed -1.3% and -1.8% file size reduction but no eval flip — residue on colored/illustrated pages is structural, not just anti-aliasing.
**Failing outputs:** Page 10 still shows horizontal line residue in table area. Pages 22, 33 have colored residue patches near illustrations/diagrams.

## Experiment 7 — keep

**Score:** 25/35 (71.4%)
**Change:** Added diagram/illustration detection for table zones using inter-row pixel variance. After computing merged y-ranges, samples pixel variance in horizontal strips between text rows. If median variance > 400, the zone contains colored images/diagrams, not uniform table background — reclassify as body text. Code placed after `computeStripVariance` definition (avoids hoisting issue).
**Reasoning:** Page 33's diagram area (y=6.5-57%) was classified as one massive table block (1543 chars) because its scattered text labels formed multi-column patterns. But the inter-row areas contain colored diagram elements (arrows, blocks), not uniform white table background. Real tables (page 10) have low variance between rows.
**Result:** Page 33 eval 5 (table columns) flipped FAIL→PASS — no more table regions on this page, so no column violations. The 1543-char block split into 5+ body text blocks with better-scoped sizing. Page 10's table preserved (low inter-row variance). Pages 4, 12, 22 unchanged.
**Failing outputs:** Page 33 still fails erasure (1), color match (2), placement (3), text size (7). Page 22 unchanged (4 failing evals). Page 10 erasure still fails.

## Experiment 8a — discard

**Score:** 25/35 (71.4%)
**Change:** X-position clustering for body zones with side-by-side text. When y-overlapping lines have different x positions (separation > 30), split into separate x-clusters with limited horizontal expansion.
**Reasoning:** Page 33's reclassified diagram zone (631 chars) is one big body block. Splitting into left/right halves would reduce diagram overlap.
**Result:** Page 33 split correctly (left ~50% and right ~50% blocks). But page 22 (illustration captions) was over-split from 23→42 blocks. Threshold of 15 and 30 both too aggressive for page 22's layout. Reverted.

## Experiment 8b — discard

**Score:** 25/35 (71.4%)
**Change:** Increased blur from 4.0 to 6.0 on erasure patches. Cache version v14.
**Reasoning:** Stronger blur might smooth out page 10's horizontal line residue.
**Result:** Page 10 marginally different. Page 4 REGRESSION — broader smudges from stronger blur made previously invisible residue visible. blur(6.0) causes over-smoothing. Reverted to blur(4.0)/v13.

## Experiment 9 — discard

**Score:** 25/35 (71.4%)
**Change:** Changed horizontal expansion from "widest safe span" to "median safe span" across scan y-positions. Prevents one y-row with wide whitespace from expanding the block.
**Reasoning:** Page 33's diagram block (w=90) expands to full width because some y-positions have open whitespace. Median would use the typical width, constraining the block.
**Result:** Page 33 diagram block barely changed (w=87.9 vs 90) because OCR text lines genuinely span the full width. Page 22 went from 23→27 blocks (unintended splitting from different expansion widths). Reverted.

---

## Final Summary

**Baseline → Final: 20/35 (57.1%) → 25/35 (71.4%)** (+5 points, +14.3%)

### Kept Changes (5):
1. **Sparse table detection** (+1): gap-based reclassification of illustration pages
2. **Zero-width block fix** (+0): minimum line width, filter tiny blocks
3. **Two-column book detection** (+2): reclassify 1-divider centered dense text
4. **Stronger blur** (+1): blur(4.0) smooths erasure residue on page 12
5. **Diagram detection** (+1): inter-row pixel variance reclassifies diagram pages

### Discarded Changes (5):
- Tighter per-pixel cleanup, two-pass erasure, x-clustering, blur(6.0), median expansion

### Remaining Failures (10/35):
- **Erasure quality** (3 pages): Table grid lines (10), illustration colors (22, 33)
- **Color matching** (3 pages): Tied to erasure quality
- **Text placement** (2 pages): Illustrations/diagrams overlap (22, 33)
- **Text sizing** (2 pages): Mixed content sizing (22, 33)

### Key Insight:
Pages 22 and 33 (illustrations/diagrams) are the hardest. Their failures are structural — text is interspersed with complex visual content that makes erasure, placement, and sizing fundamentally challenging. Significant further improvement would require client-side rendering changes (multi-column body blocks, per-label positioning) rather than server-side text-blocks adjustments.
