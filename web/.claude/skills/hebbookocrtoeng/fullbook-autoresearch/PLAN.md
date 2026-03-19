# Full-Book Autoresearch Plan

## Overview
Iterative improvement loop: score all 367 pages → take worst 10 → 10 rounds of autoresearch → re-score → repeat until clean.

## Scoring Methodology
For each page, compute:
- **E3 (placement)**: Max illustration overlap (`illust_pct`) across blocks. < 5% = auto-pass, > 5% = needs manual review.
- **E4 (centered)**: Any centered block exists? Binary.
- **E5 (table)**: Table blocks have valid column dividers? Binary.
- **E6/E7 (color/size)**: Assumed PASS (consistently passing in R1-R4).
- **E1/E2 (erasure)**: Optional, scored separately with --erased flag.

## Autoresearch Loop
1. Run `score-all-pages.py` → produces `fullbook-scores/scores.json`
2. Sort pages by worst score (E3 illust_pct descending, then E4/E5 failures)
3. Take bottom 10 pages → create autoresearch round
4. Run 10 experiments (mutate → score → keep/discard)
5. After 10 rounds, apply kept changes
6. Re-run full book scoring (skip step 1)
7. Take next bottom 10 → repeat
8. Stop when no page has E3 > 5% or other failures

## Evals (7 binary per page)
- E1: Hebrew text fully erased
- E2: Erasure matches background color
- E3: English text blocks avoid illustrations
- E4: Centered headers rendered centered
- E5: Table text within columns
- E6: Text color matches Hebrew
- E7: Text size matches Hebrew

## Files
- `fullbook-scores/scores.json` — all page scores
- `fullbook-scores/scores.tsv` — TSV summary
- `fullbook-autoresearch/round-N/` — per-round autoresearch data
