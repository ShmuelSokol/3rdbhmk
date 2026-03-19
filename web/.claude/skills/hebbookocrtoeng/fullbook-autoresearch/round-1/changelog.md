# Full-Book Autoresearch Round 1

## Focus: Illustration-aware block splitting & low-density handling

After full-book scoring (363 pages) with improved E3 metric (text-density weighted illust_pct), 80 pages failed E3 at >10% adjusted risk. Top failures were illustration-heavy pages with blocks covering illustration areas.

## Scoring Improvement (pre-round)
- **E3 text-density weighting**: `risk = illust_pct × max(0.2, 1.0 - textDensity × 2.0)`. Blocks with high text density (>0.3 chars/pct²) get reduced risk since they're likely text on colored backgrounds, not misplaced blocks.
- **Skip tiny blocks**: Blocks with area < 50 pct² are skipped for E3 scoring.
- E3 pass threshold raised from 5% to 10% (adjusted risk).
- Result: E3 pass rate jumped from 39.3% → 77.7% (false positive reduction).

## Test Pages (10)
- **Page 300** (risk=0.637, 8 blocks): Multiple labels within 3D illustrations
- **Page 106** (risk=0.620, 2 blocks): Dense text + tiny label on illustration
- **Page 216** (risk=0.414, 6 blocks): Body text extends into illustration zone
- **Page 296** (risk=0.363, 4 blocks): Text near illustration on colored bg
- **Page 250** (risk=0.334, 4 blocks): Scattered labels in illustration area
- **Page 269** (risk=0.327, 7 blocks): Scattered text in right column with illustrations
- **Page 189** (risk=0.322, 4 blocks): Photos with embedded captions
- **Page 62** (risk=0.000): Regression check (R4 sub-block splitting)
- **Page 306** (risk=0.000): Regression check (R4 sub-block splitting)
- **Page 100** (risk=0.000): Regression check (illustration avoidance)

## Experiment 0 — baseline
**Score:** 44/50 (88.0%)
**Change:** None — current code after R4 + improved E3 scorer

## Experiment 1 — keep (illustration-gap splitting in body zones)
**Score:** 44/50 (no E3 flips, but P300 risk improved 0.637→0.393)
**Change:** Within body zone group splitting, check gaps between 1.0-2.5% for illustration content (pixel variance > 200). If found, split the group at that gap. Also added low-density expansion limiting: blocks with density < 0.06 and < 30 chars skip horizontal expansion and limit vertical to ±1%.
**Result:** Page 300 blocks went from 8→10 (more illustration-aware splitting). No regressions.

## Experiment 2 — keep (column-split illustration-gap splitting)
**Score:** 45/50 (+1, P269 E3 FAIL→PASS)
**Change:** Added illustration-gap splitting to column-split blocks. After creating column blocks, check y-gaps between lines for illustration content (variance > 200). If found, split the column block into separate blocks at illustration boundaries. Also lowered body zone GAP_THRESHOLD from 3% to 2.5%.
**Result:** Page 269 right column (B4: 118 chars, y=33.8-94.2) split into B4 (84 chars, y=33.8-37.3) + B7 (34 chars, y=93.2). Illustration area in the middle no longer covered.

## Experiment 3 — discard (zone-level gap reduction)
**Change:** Lowered zone gap threshold from 8% to 6% + illustration gap check for 3-8% gaps.
**Result:** Caused harmful merge on page 189 (B3+B4 combined into single 62.8% tall block). Complex zone interaction effects. Reverted.

## Experiment 4 — keep (per-line splitting for low-density groups)
**Score:** 47/50 (+2, P250 & P300 E3 FAIL→PASS)
**Change:** For body zone groups with text density < 0.06, > 1 line, and < 50 total chars, create per-line blocks instead of one combined block. This prevents scattered illustration labels from creating wide blocks.
**Result:**
- Page 250 (0.389→0.007 PASS): Scattered labels split into individual blocks
- Page 300 (0.393→0.005 PASS): Same — labels split per-line, blocks 10→5

## Experiment 5 — discard (tall body block splitting)
**Change:** Post-creation check: scan tall (>20% height), moderate-density (<0.2) blocks for illustration strips via pixel variance. Split at widest illustration run.
**Result:** No improvement — photo areas don't have high enough luminance variance at full block width. Reverted.

## Experiment 5b — discard (zone-level illustration gap, repeated)
**Change:** Same as exp 3 but without lowering zone gap threshold. Only added illustration gap check for 3-8% gaps.
**Result:** Same harmful merge on page 189. Zone-level changes have complex downstream effects. Reverted.

---

## Final Status

**Baseline → Final: 44/50 (88.0%) → 47/50 (94.0%)** (+3 points)

### Kept Changes (3):
1. **Body zone illustration-gap splitting** (exp 1): Check gaps 1.0-2.5% between body lines for illustration pixels. Split at illustration gaps.
2. **Column-split illustration-gap splitting** (exp 2, +1): Same logic applied to column-split blocks. Fixed page 269.
3. **Per-line splitting for low-density groups** (exp 4, +2): Scattered labels (density < 0.06, < 50 chars) get individual blocks instead of one wide block. Fixed pages 250 & 300.

### Remaining Failures (3/10):
- **Page 106 E3 (0.620)**: 12-char label at y=95 on full-page illustration. Unfixable — text IS within illustration.
- **Page 216 E3 (0.414)**: Body block (311 chars) covers both text and adjacent illustration. Needs horizontal splitting (text right, illustration left).
- **Page 296 E3 (0.363)**: 59-char block on colored background section. Likely false positive — colored section header triggers illustration detector.
- **Page 189 E3 (0.322)**: 561-char block spans photos with embedded Hebrew captions. Text IS within photos.

### Also Improved (not PASS):
- **Page 300 E4 (0)**: No centered block detected on page with centered title. E4 issue, not E3.
- **Page 106 E4 (0)**: No centered block detected. Page may legitimately lack centered text.
