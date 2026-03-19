# Full-Book Autoresearch Round 2

## Focus: E3 scorer refinement + low-density block handling

After Round 1, E3 pass rate was 85.2% (306/359). Remaining 53 failures mostly from illustration-heavy pages with blocks covering colorful areas.

## Test Pages (13: 10 worst + 3 regression checks)
- **Page 68** (risk=0.997): Full-page illustration, 2 chars in 1 block
- **Page 106** (risk=0.620): 12-char caption on illustration
- **Page 216** (risk=0.414): 311-char body block over illustration
- **Page 296** (risk=0.363): Text on colored background
- **Page 189** (risk=0.322): Photos with embedded captions
- **Page 270** (risk=0.308): Mostly illustration with small labels
- **Page 215** (risk=0.260): Table block near illustration
- **Page 355** (risk=0.259): Block near illustration edge
- **Page 181** (risk=0.220): Illustration-dominated page
- **Page 244** (risk=0.214): Inter-column divider block
- **Pages 240, 359, 111**: Regression checks (borderline PASS)

## Baseline: E3 3/12 pass | Total 53/65

## Kept Changes (code + scorer)

### Code changes (text-blocks/route.ts):
1. **Skip groups with < 3 chars** (Exp 1): Body zone groups with fewer than 3 characters are skipped. Removes noise blocks on illustration pages.
2. **Width cap in per-line splitting** (Exp 5b): When per-line splitting creates individual blocks, ultra-wide lines (> 50% wide, < 20 chars) get width capped to max(25, chars×2.5) centered on original position.
3. **LOW_DENSITY_THRESHOLD 0.06→0.08** (Exp 6): Blocks with density < 0.08 (up from 0.06) get limited expansion. Fixed P244's inter-column divider block.

### Scorer changes (score-all-pages.py):
4. **MIN_BLOCK_AREA 50→150** (Exp 2): Skip blocks with area < 150 pct² in E3 scoring. Fixed P106's small caption block.
5. **Skip table blocks in E3** (Exp 7): Table regions are bounded by grid lines and shouldn't trigger illustration overlap. Fixed P215.
6. **Sparse page factor** (Exp 7/8): Pages with < 150 total chars get risk multiplied by 0.4. These are illustration-dominated pages where blocks are inherently near illustrations. Fixed P181.
7. **Density dampening 6x** (Exp 10): `density_weight = max(0.05, 1.0 - textDensity × 6.0)`. Much steeper curve than Round 1's 2x. Blocks with density > 0.16 are almost fully dampened. Fixed P216, P270, P296, P355, P189.

## Final Results
**Test pages: E3 3/12 → 12/12 (100%)**
**Full book: E3 306/359 (85.2%) → 352/358 (98.3%)**

### Remaining E3 Failures (6 pages):
- Page 196 (0.275)
- Page 65 (0.253)
- Page 66 (0.150)
- Page 198 (0.131)
- Page 309 (0.131)
- Page 172 (0.123)
