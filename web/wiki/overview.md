# Project Overview

## The Hebrew Book

The source material is a 367-page Hebrew sefer titled **"Lishchno Tidreshu"** (Hebrew: לשכנו תדרשו, "To His Dwelling You Shall Seek"). The book is a comprehensive study of the Third Beis HaMikdash as described in the prophecy of Yechezkel (Ezekiel chapters 40-48). It covers the architectural layout, the avodah (service), the role of the Kohanim and Levi'im, and the halachic underpinnings of the future Temple -- drawing from Gemara, Rishonim, and Acharonim.

The book is richly illustrated with 3D architectural renders, floor plans, cross-section diagrams, and labeled schematics of the various structures: the Heichal, Ulam, Azarah, Lishkos, Mizbeiach, and surrounding walls.

## The English Translation Goal

The goal is to produce a **print-ready English typeset PDF** suitable for publication through print-on-demand services (Lulu, IngramSpark, KDP) and distribution in Judaica bookstores. This is not a word-for-word translation overlaid on the Hebrew pages. It is a **fully separate English book** that:

1. Translates the Hebrew text in ArtScroll style -- scholarly, flowing English prose with inline Hebrew terms and source citations that an Ashkenazi yeshiva-educated reader would expect.
2. Extracts illustrations from the Hebrew source pages (3D renders, diagrams, floor plans) and places them in the corresponding location in the English text.
3. Generates a professional book layout with double-line border frames, running headers, page numbers, a dynamic Table of Contents with 65+ topic entries, and proper typography.
4. Handles mixed RTL/LTR text rendering for inline Hebrew quotes using Chromium's native HarfBuzz engine via Playwright.

## The Pipeline

The system processes the Hebrew book through a multi-stage pipeline:

1. **OCR** -- Azure Computer Vision reads every page, producing bounding boxes with Hebrew text, coordinates, font size estimates, and bold detection.
2. **Region Detection** -- Bounding boxes are grouped into content regions (body, header, footer, table, image) ordered top-to-bottom on each page.
3. **Translation** -- Claude translates each region's Hebrew text to English in ArtScroll style, inserting inline Hebrew quotes with em-dash format and source citations.
4. **Enhancement** -- The `enhance-artscroll.js` script batch-processes 681+ regions to insert Hebrew source text inline, replace spelled-out Hebrew letter names with actual characters, and normalize citation formats.
5. **Illustration Extraction** -- Pixel-level analysis identifies illustration regions in source page images, crops them without Hebrew text, and produces clean image buffers.
6. **Typeset** -- The typeset route assembles all content into `ContentElement[]` and renders to PDF via either Playwright/HTML or pdf-lib.

## Scope of the Book

The Hebrew source contains two versions of the content: a shorter version on pages 3-67 and the full expanded version starting at page 71. The English PDF uses only the expanded version. Pages 3-70 are skipped entirely, and the book begins with the front matter (cover, letter pages 4-12 from the original, foreword) before the expanded content.

The Table of Contents maps 65 topics to their English page numbers, keyed by Perek:Pasuk references from Yechezkel. Topics include "The Wall of Har HaBayis" (40:5), "The Shaar HaElyon" (40:6), "The Lishkos of the Shaarim" (40:7), and so on through the entire Nevuah.

## Current State

The PDF is generated in three parts (to stay under Supabase's 50MB upload limit) and uploaded to `bhmk/exports/`. The HTML renderer (Playwright) handles Hebrew bidi correctly. Open work items include pixel-level illustration extraction (replacing full source page images with cropped illustrations only), TOC gap-filling for non-Perek sections, and print-ready preparation (bleed margins, cover PDF, ISBN).
