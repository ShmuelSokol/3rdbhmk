# Layout Rules

The English typeset PDF must look like a professionally published book. These rules govern how content is arranged on each page.

## Page Dimensions

The book uses a 6.5" x 9" trim size, which is standard for religious/academic trade paperbacks:

- Page width: 468 points (6.5 inches)
- Page height: 648 points (9 inches)
- All margins: 54 points (0.75 inches)
- Usable text area: 360 x 540 points

The `safeMarginBottom` is `marginBottom + 20` points (74 points total). This value must NEVER be reduced -- it prevents text from colliding with page numbers and the bottom border.

## Page Decoration

Every page gets a double-line border frame:
- Outer border at the page margin boundary
- Inner border inset slightly
- Running header at the top with the book title ("Lishchno Tidreshu")
- Page numbers centered at the bottom

In the HTML renderer, left/right borders are CSS `position:fixed` pseudo-elements that automatically repeat on every printed page. Top/bottom borders, the running header, and page numbers are rendered via Playwright's `displayHeaderFooter` option.

## Text Justification

All body text must be FULLY JUSTIFIED:
- Words hug both the left and right margins
- Variable word spacing distributes extra space evenly across each line
- Both left and right margins look clean and aligned
- There should be a slight margin (the `firstLineIndent` of 18 points) from the page border for paragraph first lines

The HTML renderer achieves this with CSS `text-align: justify`. The pdf-lib renderer computes word spacing manually to fill each line.

## Image Placement

Images follow these rules:

1. **Bottom placement**: When nothing follows an image on the source page (the image is the last element), the image should be placed at the BOTTOM of the English page, with its caption text above or below as appropriate.

2. **Anywhere in source**: Illustrations can appear ANYWHERE in the Hebrew source -- at the top, middle, or bottom of a page. Never assume they are only at the bottom.

3. **Minimum 70% size**: If an illustration cannot fit at 70% of its intended size on the current page, start a new page rather than shrinking it further. An illustration at less than 70% is too small to be readable.

4. **Caption proximity**: If a source image has a header or footer caption explaining it, that caption is placed directly above or below the image in the English version.

5. **Maximum width**: Illustrations are scaled to at most 85% (`illustrationMaxWidth`) of the text width, maintaining aspect ratio.

6. **Padding**: 10 points of vertical space (`illustrationPadding`) above and below each illustration.

## Page Breaks

Page breaks in the English version mirror the Hebrew source:

1. **Topic breaks**: Wherever the Hebrew version intentionally starts a new page for a new topic or section, the English version does the same. The typeset route analyzes the Hebrew source to detect these intentional breaks.

2. **No orphans**: A section heading at the bottom of a page with no body text following it is moved to the next page.

3. **Figure grouping**: In the HTML renderer, illustration + caption groups use `page-break-inside: avoid` CSS to prevent awkward splits.

## Blank Page Avoidance

Blank or near-blank pages are strictly forbidden:

1. If a page has fewer than 5 lines of text with no images (mostly blank), that content must be merged onto the previous page by slightly decreasing font size.
2. The unified eval framework includes critical-weight checks for "no blank pages" (E10) and "no empty pages" (E30).
3. This rule applies to content pages only -- structural pages like the title page and TOC are exempt.

## Duplicate Page Handling

The Hebrew source contains the same content twice: a condensed version on pages 3-67 and the full expanded version starting at page 71. Only the expanded version is used. Pages 3-70 are skipped entirely in the English PDF. This is not configurable -- it is a hard rule because the expanded version is the authoritative text.

The crop editor enforces this with `MIN_PAGE = 71`.

## Table of Contents

The dynamic TOC contains 65+ entries organized by Perek:Pasuk reference. Each entry has:
- The Perek:Pasuk reference
- A topic description (e.g., "The Wall of Har HaBayis")
- An auto-calculated page number that updates every time the book is re-typeset

TOC entries are hardcoded in the `topicDescriptionMap` inside the typeset route. Non-Perek sections (Introduction, History of the Mishkan, Shiloh, Givon, First/Second Beis HaMikdash) need additional TOC entries -- this is a known open issue.

The TOC is inserted at page index 2 (after the cover and title page, before content).

## Running Headers

Running headers display the book title at the top of each page. Headers that are recurring section labels (like "Introduction - History of the Mishkan" or "To His dwelling you shall seek") and are under 120 characters are filtered from the body text to avoid repetition. Some headers have been observed to render garbled ("Lishechinoi Tidreshu", "Lishecnno Tidrshhu") on approximately 3 pages -- this is a known open issue.

## Typography

- Body font: 11pt (optimized via autoresearch from 10.5)
- Header font: 14pt
- Subheader font: 12pt
- Line height: 1.5x font size
- Paragraph spacing: 8pt between paragraphs
- Text color: warm near-black [0.12, 0.10, 0.08]
- Header color: darker [0.08, 0.06, 0.04]
- Page number font: 9pt
- Hebrew font: NotoSerifHebrew (embedded)
