---
name: perfecttoc
description: "Generate a perfect ArtScroll-style Table of Contents for the Lishchno Tidreshu English typeset PDF. Lists only meaningful topics that readers would actually want to navigate to, with correct page numbers that auto-update with every change."
---

# PERFECTTOC — ArtScroll-Style Table of Contents

## Core Job

Generate a clean, useful Table of Contents for the English typeset PDF of Lishchno Tidreshu that:

1. Lists ONLY the topics that the Hebrew book listed in its original TOC
2. Has correct English PDF page numbers (recalculated every time)
3. Follows ArtScroll TOC style — clean, hierarchical, dot-leaders, right-aligned page numbers
4. Fits on 1-3 pages max (not 8 pages of junk entries)

## What Makes a Good TOC Entry

Good entries (include):
- Major section headers: "Introduction — Summary of the History of the Mishkan and the Mikdash"
- Perek/chapter breaks: "Yechezkel Perek 40, Pesukim 1-5"
- Major topics: "The Ulam of the Beis HaMikdash", "The Inner Courtyard"
- Commentary section starts: "Ketz HaYamin", "Be'ur Chai", "Hashlamat Shares"

Bad entries (exclude):
- Short labels: "Or Chai", "10 amos", "North", "South"
- Diagram labels: "Spiritual Beis", "Physical Mishkan"
- Page numbers from Hebrew source: "33", "61"
- Measurement references: "100 amos x 100 amos"
- Generic section markers: "The Completion of Service" (appears on every page)
- Letter/approval page titles
- Repeated entries (same topic shouldn't appear twice)

## ArtScroll TOC Style

```
TABLE OF CONTENTS

Introduction ......................................... 5
The Mishkan in the Desert ........................... 12
  A. The Mishkan in Shiloh .......................... 15
  B. The Mishkan in Nov ............................. 18

YECHEZKEL PEREK 40
  Pesukim 1-4: The Vision of the Beis HaMikdash .... 25
  Pesukim 5-16: The Eastern Gate .................... 32
  Pesukim 17-27: The Outer Courtyard ................ 45
```

Features:
- Hierarchical indentation (major sections vs sub-topics)
- All-caps for Perek headers
- Dot-leaders connecting title to page number
- Right-aligned page numbers
- Clean English titles (no Hebrew, no fragments)

## Page Number Accuracy

Page numbers MUST be:
- Drawn as the LAST step after all pages are finalized
- Recalculated from scratch each time (not patched/corrected)
- Sequential: title=1, TOC=2-N, content=N+1 onwards
- Never overlapping with text content (safe bottom margin)

## Technical Implementation

The TOC is generated in `src/app/api/books/[bookId]/typeset/route.ts`:

1. During content rendering, `renderElements()` tracks all headers with their page numbers
2. After rendering, TOC pages are created and inserted at position 1
3. Page numbers for TOC entries are adjusted by tocPageCount offset
4. Page footer numbers are drawn LAST on all pages

## Text Overflow Prevention

Text must NEVER overlap page numbers or spill outside borders:
- safeMarginBottom = cfg.marginBottom + 20 (generous buffer)
- All page-break checks use safeMarginBottom
- drawBidiLine has maxX parameter to clip at right margin

## Evals

A good TOC:
1. Has 20-60 entries (not 4, not 200)
2. Every entry has a correct, reachable page number
3. Page numbers are monotonically non-decreasing (topics appear in order)
4. No duplicate entries (same title twice)
5. No junk entries (labels, numbers, measurements)
6. Fits on 1-3 pages
7. Has hierarchical structure (at least some indented sub-entries)
8. Major Perek sections are listed
9. Dot-leaders connect titles to page numbers
10. Page numbers match actual content location (±1 page tolerance)
