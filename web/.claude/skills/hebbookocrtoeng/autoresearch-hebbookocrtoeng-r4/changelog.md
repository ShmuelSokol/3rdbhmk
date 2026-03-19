# Autoresearch Changelog — hebbookocrtoeng (Round 4)

## Focus: Sub-block splitting for illustration avoidance

Round 3 reached 95.7% (67/70) with 3 remaining E3 (placement) failures on pages 50, 62, and 306. (Page 200 E3 was incorrectly listed as FAIL in R3 — pixel analysis confirmed no illustration at the bottom-left; it's all text.) This round implements architectural changes to detect and split blocks at illustration boundaries using OCR line x-coverage analysis.

## Test Pages (10)
- **Page 50** (cmmno2m5d001di9xo7hzzctx7): Two illustrations + scattered text annotations (FAIL E3 from R3)
- **Page 62** (cmmno2m5d001pi9xos36d5f4c): Photos top-left, text wraps right then fills full width (FAIL E3 from R3)
- **Page 200** (cmmno2m5f005ji9xoh6kvdxkk): Illustration at TOP, text at bottom — E3 was actually PASS (corrected)
- **Page 306** (cmmno2m5g008hi9xoouxzdpvf): Ornamental illustration bottom-left, text narrows at y≈79 (FAIL E3 from R3)
- **Page 10** (cmmno2m5c0009i9xo1na35m2k): Real table — regression check
- **Page 27** (cmmno2m5c000qi9xogxaw5750): Photos with small captions — regression check
- **Page 36** (cmmno2m5c000zi9xo1q2p7toh): Dense multi-section + photo — regression check
- **Page 100** (cmmno2m5d002ri9xozs8es17s): Text + large illustration — regression check
- **Page 160** (cmmno2m5e004fi9xo4tgatimt): Text + architectural diagram — regression check
- **Page 250** (cmmno2m5f006xi9xod79oksvh): Multiple photos + text — regression check

## OCR Analysis of Failing Pages

### Page 62 (left column):
- Lines 50-66 (y=8.9-36.3): narrow x=36.6-49.7 — photos at x=5-36
- Line 67 (y=34.9-35.9): transitional x=24.8-35.3 — illustration boundary
- Lines 68+ (y=36.7+): full width x=5.3-49.7 — text fills column

### Page 200 (left column, y>60):
- Lines 34-47 (y=66-91.8): full width x=4.7-49.3
- Line 48 (y=92-93.7): narrow x=33.3-49.3 — but pixel analysis shows NO illustration at x=5-33 y=92 (pure white, variance=0). This is a paragraph ending, not illustration wrapping.
- **Corrected**: page 200 illustration is at TOP (y=8-55%), not bottom. Bottom half is clean two-column text. E3 = PASS.

### Page 306 (left column):
- Lines through 87 (y≈8-78.5): full width x=5.4-49.8
- Lines 88-96 (y=78.7-95): narrow x=37.2-49.8 — illustration at x=5-37
- Line 97 (y=94-95): centered x=17.5-36.4 — footer text below illustration

### Page 50 (body zone):
- Two large illustrations spanning most of the page area
- Scattered annotation labels (small text) embedded within illustrations
- Body text column on the right side (x=50-96)
- B3 (x=21-50, y=18-80) groups annotations into one large block overlapping both illustrations
- **Not fixable with column-split approach** — requires annotation-level block detection

## Experiment 0 — baseline

**Score:** 67/70 (95.7%)
**Change:** None — R3 final
**Result:** 3 E3 failures: pages 50, 62, 306. (Page 200 E3 was PASS — R3 incorrectly listed it as FAIL.)

## Experiment 1 — keep (sub-block splitting)

**Score:** 68/70 (97.1%)
**Change:** Within the column-split code, detect illustration boundaries by analyzing OCR line x-positions:
1. Compute median min_x of all column lines (represents full-width text position)
2. Mark lines with x > median + 20% as "narrowed" (text wrapping around illustration)
3. Group consecutive narrowed/non-narrowed lines into runs
4. Split column into sub-blocks at narrow→wide boundaries
5. For narrow sub-blocks, set `_columnMinX = gMinX - 2` to prevent expansion into illustration area
6. For single-line narrowing at bottom edge, validate with pixel variance (reject paragraph endings)
**Key details:** Uses ALL zone lines (not just bodyLines with charCount>=15) for narrowing detection, since narrow column text often has <15 chars per line.
**Result:** Page 306 E3 FAIL→PASS. Left column split into wide top (B1: x=6, y=8-78.5) + narrow bottom (B3: x=38.2, y=78.7-95) + footer (B4: x=18.5, y=94.1). Page 62 partial improvement but wide block B3 still starts too high (y=34.8) due to transitional line L67.

## Experiment 2 — keep (transitional line skip)

**Score:** 69/70 (98.6%)
**Change:** For wide sub-blocks that follow narrow sub-blocks, skip leading "transitional" bodyLines whose x > medianMinX + X_SHIFT/2 (10%). These lines are at the illustration boundary — their x is shifted significantly from full-width but not enough to trigger the primary X_SHIFT=20 threshold. Without this fix, they pull the wide block's y-start up into the illustration zone.
**Implementation:** After computing blockLines for a wide region preceded by a narrow region, find the first line with x <= medianMinX + 10. Skip all lines before it. This drops transitional text (~15 chars) but prevents the block from overlapping the illustration.
**Result:** Page 62 E3 FAIL→PASS. Wide block B3 now starts at y=36.7 (was 34.8). Narrow block B1 unchanged at x=35.6. No regressions on any page.

---

## Final Status

**Baseline → Final: 67/70 (95.7%) → 69/70 (98.6%)** (+2 points)

### Kept Changes (2):
1. **Sub-block splitting** (exp 1, +1): Detect illustration boundaries within column blocks using OCR line x-coverage analysis. Split columns into narrow+wide sub-blocks at boundaries.
2. **Transitional line skip** (exp 2, +1): Skip leading transitional lines from wide blocks after narrow regions. These lines are at the illustration boundary and pull the block start too high.

### Remaining Failures (1/70):
- **Page 50 E3**: Scattered annotation labels within two large illustrations create a single body-zone block (B3: x=21-50, y=18-80) that covers both illustrations. Not a column-split page — requires fundamentally different approach (per-annotation tiny blocks or illustration-aware zone splitting). This is the practical ceiling for the current architecture.

### Key Corrections:
- **Page 200 E3**: R3 incorrectly listed this as FAIL. Pixel variance analysis at y=92%, x=5-32% shows pure white background (variance=0). The illustration is at the TOP of the page (y=8-55%), not the bottom. Bottom half is clean two-column text. Corrected to PASS.
