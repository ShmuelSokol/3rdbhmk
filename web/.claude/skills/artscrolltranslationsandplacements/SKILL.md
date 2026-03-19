---
name: artscrolltranslationsandplacements
description: "Generate print-ready ArtScroll-style English typeset PDFs from Hebrew religious texts. Handles inline Hebrew characters, illustrations, page decoration, and optimal layout for the Lishchno Tidreshu book about the 3rd Beis HaMikdash."
---

# ArtScroll Translations and Placements

## Core Job

Take Hebrew pages from Lishchno Tidreshu (a 367-page book about the 3rd Beis HaMikdash per Yechezkel's nevuah) and produce a clean, print-ready English typeset PDF with:

1. ArtScroll-style translations with **inline Hebrew characters** for short Torah/Gemara quotes
2. Illustrations and diagrams from source pages displayed alongside their related text
3. Elegant page design with borders, running headers, and decorative elements
4. No wasted space — text and illustrations flow naturally without huge gaps

## Translation Style

Follow ArtScroll conventions:
- Short Hebrew quotes (1-5 words) in **original Hebrew characters** with transliteration context
- Source references: tractate name + daf (e.g., "Zevachim 118b"), Rashi/Rambam location
- Ashkenazi English transliteration: Shabbos, Beis HaMikdash, davening, Hashem, pesukim, halachah
- Longer quotes translated to English only (no Hebrew inline for paragraphs)
- Hebrew terms used throughout: kodshei kodashim, bamos, korbanos, yeri'os, kerashim

## TypesetConfig Parameters

These control the PDF layout. All values in PDF points (72pt = 1 inch) unless noted.

```
pageWidth: 468         # 6.5 inches — standard book trim
pageHeight: 648        # 9 inches
marginTop: 54          # 0.75 inch
marginBottom: 54       # 0.75 inch
marginLeft: 54         # 0.75 inch
marginRight: 54        # 0.75 inch
bodyFontSize: 11       # optimized: larger for readability (autoresearch exp 20)
headerFontSize: 14     # section headers
subheaderFontSize: 12  # bold subheaders
lineHeight: 1.5        # optimized: tighter to compensate for larger font
paragraphSpacing: 8    # optimized: more visual separation between paragraphs
headerSpacingAbove: 14 # points above headers
headerSpacingBelow: 6  # points below headers
illustrationMaxWidth: 0.85    # fraction of text width
illustrationPadding: 10       # points above/below illustrations
textColor: [0.12, 0.10, 0.08]   # near-black warm tone
headerColor: [0.08, 0.06, 0.04] # slightly darker
pageNumberFontSize: 9
firstLineIndent: 18    # paragraph indent
illustrationGapThreshold: 8   # % of page height gap to detect illustration
```

## Page Design

Every content page includes:
- **Double-line border frame**: Outer (0.7pt) and inner (0.3pt) lines around the text area
- **Running header**: "LISHCHNO TIDRESHU — ENGLISH TRANSLATION" centered with flanking lines
- **Page numbers**: Centered in footer with em dashes (— N —)
- **Section dividers**: Diamond shape with flanking lines between topic sections (only when a new header/section starts)

## Topic Breaks & Orphan Prevention

- New topics (pages starting with a header) start on a new page (matches Hebrew book layout)
- Pages that continue the same topic flow continuously (no forced page break)
- **Orphan prevention**: When the last paragraph before a topic break would spill 1-5 lines to the next page, progressively squeeze font (5%, 8%, 10%, 12%) to fit on the current page
- **Line-level orphan prevention**: When page-break rendering detects ≤5 orphan lines before a divider, squeeze line spacing to fit
- Font squeeze range: up to 15% reduction (88% of base size)

## Illustration Handling

- Detect illustration gaps between text regions (gaps > illustrationGapThreshold % of page height)
- Crop illustrations from source page images
- **Border trimming**: Auto-trim yellowish/beige borders from cropped illustrations to maximize image area (pixel-level edge analysis for yellow/beige/white tones)
- Verify content with pixel variance check (skip blank crops)
- Scale illustrations to fit remaining page space instead of forcing page breaks
- Cap illustration height at 50% of text area
- If remaining space >= 20% of page, scale illustration to fit rather than creating a new page
- Center illustrations horizontally

## Table Rendering

- Detect table content: regions with `regionType === 'table'`, pipe-separated text, or numbered lists (3+ items)
- Parse into rows/columns using pipe `|` separators
- Render with aligned columns, header/footer lines, and row separators
- Table font size: 90% of body font

## Caption Rendering

- Short text regions (< 8 words) adjacent to illustrations become captions
- Rendered in smaller font (85% of body), centered, in lighter color
- Preserves diagram labels and annotations in context with their illustrations

## Font Stack

- Body: Times Roman (pdf-lib standard)
- Bold: Times Roman Bold
- Headers: Times Roman Bold
- Hebrew: Noto Serif Hebrew Regular (embedded via fontkit)
- Hebrew Bold: Noto Serif Hebrew Bold (embedded via fontkit)

## Bidi Text Rendering

- Split mixed text into Hebrew/Latin segments
- Draw each segment with appropriate font
- Hebrew characters in logical Unicode order (no reversal)
- Word wrapping accounts for mixed-font width measurement

## Quality Checks (8 Evals — autoresearch round 3: 24/24 = 100%)

A good typeset page:
1. **E1: Hebrew Characters** — actual Hebrew Unicode characters inline (not transliterated)
2. **E2: Words/Page** — ≥100 words per content page (no wasted gap pages)
3. **E3: Illustrations** — illustrations embedded in PDFs with expected images
4. **E4: Text Completeness** — sufficient word count per page range
5. **E5: No Interior Gaps** — no mid-page blank strip > 45% (topic-end trailing blank OK)
6. **E6: Decoration** — running headers and page numbers present
7. **E7: No Orphans** — no pages starting with 1-3 stray lines from previous topic
8. **E8: Topic New Pages** — topic breaks force new pages via code
