# Distribution

The end goal is a printed English book available through multiple channels. This page covers the planned distribution strategy and the technical requirements for each channel.

## Print-on-Demand Services

### Lulu

Lulu is the primary target for initial printing. It supports:
- Custom trim sizes (6.5" x 9" is supported)
- PDF upload for interior and cover
- Low minimum order (single copy)
- Direct-to-consumer sales via their storefront

### IngramSpark

IngramSpark provides the broadest distribution reach:
- Access to 40,000+ retailers and libraries worldwide
- Wholesale pricing for bookstores
- Requires an ISBN
- Returns handling built in
- Higher quality printing options

### Amazon KDP (Kindle Direct Publishing)

KDP covers the Amazon marketplace:
- Largest single online bookstore
- Print-on-demand with no inventory
- Also supports Kindle ebook if desired
- Free ISBN option (Amazon-assigned)

### Judaica Stores

Physical Judaica bookstores (Eichler's, Z Berman, Seforim Center, etc.) are the ideal retail channel for this book. Distribution through IngramSpark enables wholesale ordering by these stores. Direct relationships may also be established for consignment or bulk orders.

## Technical Requirements for Print-Ready PDF

The current PDF is not yet print-ready. The following items are needed:

### Bleed Margins

Print-on-demand services require "bleed" -- elements that extend past the trim line so that after cutting, no white strips appear at the edges. Standard bleed is 0.125" (9 points) on all sides. The current PDF has no bleed. To add bleed:
- Increase the PDF page size by 0.25" in each dimension (to 6.75" x 9.25")
- Extend background colors and border decorations into the bleed area
- Keep all text within the "safe zone" (current margins already handle this)

### Cover PDF

A separate cover PDF is required with:
- Front cover (6.5" x 9")
- Spine (width depends on page count and paper weight -- typically 0.5" to 0.8" for a 350-page book)
- Back cover (6.5" x 9")
- Bleed on all outer edges
- The spine width must be calculated from the final page count and the paper stock chosen

### ISBN

An International Standard Book Number is needed for distribution through IngramSpark and traditional bookstores. Options:
- Purchase from Bowker (US ISBN agency) -- $125 for one, $295 for ten
- Use Amazon's free ISBN (but limits distribution to Amazon only)
- Use Lulu's free ISBN (limits to Lulu distribution)

For maximum distribution, a Bowker ISBN is recommended.

### BISAC Categories

BISAC subject codes are required by IngramSpark and Amazon. Relevant categories:
- RELIGION / Judaism / Rituals & Practice
- RELIGION / Judaism / Sacred Writings
- RELIGION / Judaism / General

### Metadata

All services require:
- Book title: "Lishchno Tidreshu" (or an English title like "To His Dwelling You Shall Seek")
- Subtitle: "The Third Beis HaMikdash According to the Prophecy of Yechezkel"
- Author name
- Publisher name
- Publication date
- Page count
- Trim size: 6.5" x 9"
- Interior type: Black and white with color illustrations (affects pricing)
- Paper type: White or cream

## Current State

Print-ready preparation has not started. The current focus is on:
1. Completing illustration extraction (replacing full source page images with cropped illustrations)
2. Filling TOC gaps for non-Perek sections
3. Fixing garbled running headers on ~3 pages
4. CSS polish on borders and spacing in the HTML renderer

Once these are resolved, the print-ready preparation (bleed margins, cover PDF, ISBN) will be the final step before the first proof copies are ordered.
