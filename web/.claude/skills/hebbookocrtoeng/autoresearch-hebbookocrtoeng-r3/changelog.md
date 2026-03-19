# Autoresearch Changelog — hebbookocrtoeng (Round 3)

## Test Pages (10)
- **Page 27** (cmmno2m5c000qi9xogxaw5750): Photos with small captions between them
- **Page 36** (cmmno2m5c000zi9xo1q2p7toh): Dense multi-section, colored bars, photo mid-page
- **Page 40** (cmmno2m5c0013i9xoeag5en8o): Large illustration top + technical diagrams bottom
- **Page 50** (cmmno2m5d001di9xo7hzzctx7): Two illustrations + text column on right + bottom section
- **Page 62** (cmmno2m5d001pi9xos36d5f4c): Dense two-column text + photo top-left + colored headers
- **Page 100** (cmmno2m5d002ri9xozs8es17s): Text top + large fire illustration bottom
- **Page 160** (cmmno2m5e004fi9xo4tgatimt): Text top + architectural diagram bottom
- **Page 200** (cmmno2m5f005ji9xoh6kvdxkk): Illustration top + two-column text bottom
- **Page 250** (cmmno2m5f006xi9xod79oksvh): Multiple photos + text interspersed
- **Page 306** (cmmno2m5g008hi9xoouxzdpvf): Dense two-column text + small illustration at bottom

## Experiment 0 — baseline

**Score:** 66/70 (94.3%)
**Change:** None — post round 2 skill
**Result:** Baseline established.

Key failures (5):
- Page 50 E3: B3 (x=21-50, y=18-80) tall block from scattered text annotations overlaps illustration area
- Page 62 E3: Full-page table block covers embedded photos at top-left
- Page 62 E5: Two-column body text misclassified as table (13 dividers from photo edges exceeded ≤10 limit)
- Page 200 E3: B5 (x=6, y=66-95, full width) extends into small illustration at bottom-left
- Page 306 E3: B1 (x=6, y=8-95, full width) covers ornamental illustration at bottom

**Weakest eval:** Placement (6/10)
**Strongest evals:** Erasure (10/10), Color match (10/10), Text color (10/10), Text size (10/10)

## Experiment 1 — keep

**Score:** 67/70 (95.7%)
**Change:** Increased isTwoColumnBook divider count limit from ≤10 to ≤20. Pages with embedded photos/illustrations generate many false dividers from dark edges (Method 1) — page 62 had 13 dividers, mostly from the decorated box photos at top-left. The totalChars > 400, blockWidth > 75, and centerDivider near center checks are sufficient to distinguish two-column body text from real tables.
**Reasoning:** Page 62 had 13 dividers (vs limit of 10), causing isTwoColumnBook to not trigger. The zone stayed as table when it should be body text. 3539 totalChars + center divider at x=51.2 clearly indicate two-column prose.
**Result:** Page 62 E5 flipped FAIL→PASS. Verified: round 1 page 10 (real table) still correctly classified as table. No regressions on any test page.

## Experiment 2 — keep (always-split + edge-out expansion)

**Score:** 67/70 (95.7%)
**Change:** Two sub-changes:
1. **Always split two-column zones**: Removed the `heightDiff > 8` requirement from the column-split condition. Now any isTwoColumnBook zone with ≥3 body lines per column gets split. This produces separate left/right column blocks even when both columns extend to similar heights.
2. **Edge-out expansion for column blocks**: The horizontal expansion algorithm scans from page center (x=50) outward. For column-split blocks, x=50 is at the column gutter — the scan hits the adjacent column's text and immediately fails, producing width=0 blocks. Fixed by using edge-out expansion (scanning from block edges outward) for blocks with column bounds, same as centered text blocks.

**Reasoning:** Pages 200, 306, 62 all have two-column text where both columns extend equally. Without always-split, they get a single full-width block. With always-split, each column gets independent bounds, allowing the left column to not affect the right column's layout.
**Result:** No score change on this test set (remaining failures are within-column illustration overlaps that splitting alone can't fix). But structural improvement — 4 pages (36, 50, 200, 306) gain proper column separation. Page 250's bottom zone now correctly splits (prevented width=0 regression via edge-out expansion fix). Round 1+2 pages verified: page 28 and 352 gain proper column splits, page 10 (real table) unchanged.

## Experiment 3 — discard (bottom illustration trimming)

**Score:** N/A — caused regressions
**Change:** After expansion, scan each block's bottom for high pixel variance (illustration) and trim the block height to stop before it.
**Reasoning:** Pages 200 and 306 have blocks extending past text into illustration areas at the bottom. Variance-based detection should catch the transition from text to illustration.
**Result:** VARIANCE_THRESHOLD * 1.5 was still too low — dense Hebrew body text has enough variance to trigger trimming. Page 200 B2 was trimmed from h=19.9 to h=2.9 (massive regression). Page 306 columns trimmed from h≈87 to h≈60. Pixel variance cannot reliably distinguish text from illustrations. Immediately reverted.

---

## Final Status

**Baseline → Final: 66/70 (94.3%) → 67/70 (95.7%)** (+1 point)

### Kept Changes (2):
1. **Increased isTwoColumnBook divider limit** (exp 1, +1): ≤10 → ≤20. Photo/illustration edges create false dividers that shouldn't prevent two-column body text reclassification.
2. **Always-split + edge-out expansion** (exp 2, +0): Remove heightDiff requirement for column split + fix width=0 bug when column blocks use center-out expansion. Structural improvement for column handling.

### Discarded Changes (1):
- Exp 3: Bottom illustration trimming (pixel variance can't distinguish text from illustrations)

### Remaining Failures (4/70):
- **Page 50 E3**: Scattered annotation block (x=21-50, y=18-80) from labels beside illustrations. Body zone (not table), so two-column detection doesn't apply.
- **Page 62 E3**: Left column block (x=6-50, y=20-97) overlaps photos at top-left. Text wraps around photos — OCR lines exist at same y-positions as photos but different x-positions.
- **Page 200 E3**: Left column block (x=6-50, y=66-94) extends into illustration at bottom-left. Text continues at x=36-48 beside the illustration at x=6-35 in the same y-range.
- **Page 306 E3**: Left column block (x=6-50, y=8-95) covers ornamental illustration at bottom.

### Key Insight:
All 4 remaining failures involve text and illustrations that coexist at the **same y-positions** within a column — text wraps around illustrations rather than being cleanly separated by horizontal boundaries. The current rectangular block approach cannot represent these layouts without either:
1. **Non-rectangular blocks** (L-shaped or polygon-based regions)
2. **Text-wrapping detection** (detecting illustration areas within blocks and splitting around them)
3. **Sub-block layout** (breaking a column block into multiple smaller blocks at illustration boundaries)

These are significant architectural changes beyond the scope of parameter tuning. The 95.7% score represents the practical ceiling for rectangular block-based layout detection on this book.
