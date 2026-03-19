# Autoresearch Changelog — hebbookocrtoeng (Round 2)

## Test Pages
- **Page 20** (cmmno2m5c000ji9xolnqrwt5i): Body text + large illustration at bottom
- **Page 28** (cmmno2m5c000ri9xozf66l0wz): Photo grid, multi-column text between photos
- **Page 85** (cmmno2m5d002ci9xo0n7niiqu): Handwritten Hebrew on beige/yellow with ruled lines
- **Page 150** (cmmno2m5e0045i9xommkk6m2l): Complex multi-section layout with orange borders + illustration
- **Page 352** (cmmno2m5g009ri9xor7tk80lx): Dense text-heavy page with colored border frame

## Experiment 0 — baseline (corrected)

**Score:** 29/35 (82.9%)
**Change:** None — post round 1 skill, no changes
**Result:** Baseline established. Initial scoring marked pages 28 and 85 eval 2 as FAIL (color mismatch). Pixel analysis revealed both pages have white text backgrounds (RGB 255,255,255) — the yellow/beige is outer frame only. Corrected eval 2 to PASS for both.

Key failures:
- Page 85 (3 failures): Handwritten text not fully erased (OCR misses most handwriting), text blocks don't cover all text areas, centered header not detected
- Page 150 (3 failures): Section headers in colored bars ("קץ הימין", "באור חי") not erased, table block overlaps illustration at bottom, wrong column dividers (5 dividers clustered in left 35%)

**Weakest evals:** Erasure (3/5), Placement (3/5)
**Strongest evals:** Color match (5/5), Text color (5/5), Text size (5/5)

## Experiment 1 — keep

**Score:** 30/35 (85.7%)
**Change:** Added marginal annotations detection. When all column dividers in a table zone are clustered within <50% of the block width, reclassify as body text. This catches pages where verse references on the margin create false multi-column patterns.
**Reasoning:** Page 150's bottom section had 5 column dividers all clustered in the left 35% of the block — verse references ([סא], [סב], etc.) on the left margin, not a real table structure.
**Result:** Page 150 eval 5 (table columns) flipped FAIL→PASS — no table regions remain. Verified: round 1 page 10 (real table) was already non-table in current codebase; no regressions on any test page.
**Failing outputs:** Page 150 eval 3 (placement) still fails — bottom body block still covers y=50.7-95.2 which includes the illustration.

## Experiment 2 — discard

**Score:** 30/35 (85.7%)
**Change:** Color validation on reference rows (isRowColorMatch) + local bg color fallback for no-ref-found case.
**Reasoning:** Thought white erasure patches on yellow backgrounds were caused by reference rows from wrong color zones.
**Result:** Pixel analysis proved both page 28 and 85 have white text backgrounds (RGB 255,255,255). The yellow/beige appearance is the outer page frame only. The erasure correctly matches white. No eval change.

## Experiment 3 — discard (x-shift splitting)

**Score:** N/A — caused regressions
**Change:** Split body text groups when lines shift >25% to the right (detecting illustration boundaries).
**Reasoning:** Page 150's bottom section has text spanning full width at top, then only right side below the illustration.
**Result:** Over-split two-column body text on pages 28 (5→9 blocks), 85 (4→6 blocks), and 20 (1→2 blocks). Two-column Hebrew text alternates between x=5 and x=52, triggering the shift detection. Immediately reverted.

## Experiment 4 — keep

**Score:** 31/35 (88.6%)
**Change:** Increased top erasure padding from 0.4% to 1.2% (asymmetric: padTop=1.2, padBot=0.4, padX=0.4). Cache version v17.
**Reasoning:** Page 150's colored bar headers ("קץ הימין" at y=29.2%) had text positioned ~2% above the OCR-reported y coordinate. The 0.4% top padding didn't reach the actual text.
**Result:** Page 150 eval 1 (erasure) flipped FAIL→PASS. Pixel analysis: bar at y=27% changed from luminance 82 (dark red) to 253 (near-white). All 5 test pages show no visual regressions. File sizes changed: p150 -5.2%, p85 -5.2%, p28 -1.9% (more coverage), p20 -0.6%, p352 -1.5%.
**Failing outputs:** Page 150 eval 3 (placement) still fails. Page 85 evals 1, 3, 4 unchanged (OCR limitations).

## Experiment 5 — discard (bidirectional centered split)

**Score:** 31/35 (88.6%)
**Change:** Split body zones at body→centered AND centered→body transitions (bidirectional). Added width threshold (≥8%) to avoid splitting tiny annotation labels.
**Reasoning:** Page 85's centered header "שער השבט" wasn't getting its own block because the split only happened at centered→body transitions, not body→centered.
**Result:** Split worked correctly but page 85's centered block has empty `englishText` (OCR garbled the handwritten header into "523. ₪23:"). Eval 4 (centered) can't flip without translatable text. No score change on any page.

## Experiment 6 — keep

**Score:** 32/35 (91.4%)
**Change:** Column-split for two-column zones with asymmetric column heights. Three sub-changes:
1. **Method 3 divider detection**: Per-line pair y-overlap gap analysis catches column gutters that Method 2 misses when columns nearly touch (gap < 2%).
2. **Relaxed isTwoColumnBook**: Uses closest-to-center divider instead of requiring exactly 1 divider. Allows up to 10 dividers (illustration grid lines + column gutter). Added off-center check to marginal annotations to prevent false triggers from illustration dark lines.
3. **Column-split with bounds**: When left/right column heights differ by >8%, split into separate blocks with `_columnMaxX`/`_columnMinX` bounds that limit horizontal expansion. Side-by-side blocks skip vertical overlap resolution (xOverlap < 2 check).

**Reasoning:** Page 150's bottom section has two columns — left column ends at y≈63% with an illustration below (y≈73-93%), right column continues to y≈95%. A single full-width block covered both columns AND the illustration.
**Result:** Page 150 eval 3 (placement) flipped FAIL→PASS. Left column block (x=6-44.4, y=50.9-63.6) stops 10% above illustration. Right column block (x=46.4-96, y=50.7-95.2) doesn't overlap illustration horizontally. No regressions on any other test page.

---

## Final Status

**Corrected Baseline → Final: 29/35 (82.9%) → 32/35 (91.4%)** (+3 points)

### Kept Changes (3):
1. **Marginal annotations detection** (exp 1, +1): reclassify clustered-divider table zones as body text
2. **Increased top padding** (exp 4, +1): padTop=1.2% catches OCR coordinate offsets in colored bars
3. **Column-split for asymmetric two-column zones** (exp 6, +1): separate blocks with column bounds prevent illustration overlap

### Discarded Changes (3):
- Exp 2: Color validation + bg fallback (white backgrounds confirmed by pixel analysis)
- Exp 3: X-shift body splitting (over-splits two-column Hebrew text)
- Exp 5: Bidirectional centered split (page 85 centered block has no English text)

### Remaining Failures (3/35):
- **Page 85 eval 1** (erasure): OCR can't read handwritten Hebrew — most text undetected
- **Page 85 eval 3** (placement): Text blocks only cover OCR-detected areas (fraction of page)
- **Page 85 eval 4** (centered): OCR garbles handwritten headers into wide asymmetric lines

### Key Insight:
All 3 remaining failures are on page 85 (handwritten manuscript) and stem from Azure OCR's inability to read handwritten Hebrew. The OCR text is mostly garbage (random strings, numbers, English chars). Server-side improvements can't fix upstream OCR accuracy. No further experiments attempted — remaining failures are structural OCR limitations, not algorithmic issues.
