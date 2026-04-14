# Decisions Log

This page documents the key technical and design decisions made during the project, along with the reasoning behind each one. Understanding WHY decisions were made is critical for anyone continuing the work -- otherwise you will spend time re-investigating paths that were already explored and rejected.

## Playwright HTML-to-PDF over pdf-lib

**Decision**: The Playwright/Chromium HTML renderer is the primary PDF generation path. pdf-lib is kept as a fallback.

**Why**: Hebrew bidirectional text rendering is the single hardest problem in the PDF generation pipeline. The pdf-lib library renders glyphs left-to-right and requires manual bidi reordering via bidi-js. Despite significant effort (implementing `splitBidi()`, `getVisualSegments()`, font-switching segments), complex mixed-direction paragraphs with inline Hebrew quotes still rendered incorrectly -- word order was sometimes reversed, punctuation attached to wrong segments, and em-dashes floated to wrong positions.

Chromium's HarfBuzz engine handles all of this natively and correctly. By generating HTML with `<bdi dir="rtl">` tags for Hebrew segments and letting Playwright's `page.pdf()` produce the output, we get pixel-perfect bidi rendering with zero manual intervention.

The trade-off is that the Dockerfile needs Playwright/Chromium installed (requiring Debian-based image, not Alpine), which increases the container size. The pdf-lib renderer still has all the layout features (borders, headers, page numbers, TOC) and is useful for fast local iteration when bidi correctness is not needed.

## Blob Detection over Row-Column Scanning

**Decision**: V2 blob detection is the primary illustration extraction algorithm.

**Why**: The algorithm race tested 10 different approaches against user-approved ground truth crops. Blob detection scored 73.52, beating the original row+column approach at 67.73. The fundamental advantage is that blob detection considers 2D spatial coherence (connected components) rather than treating rows and columns independently. This catches illustrations that span partial rows or have irregular shapes.

Row+column scanning failed on illustrations that had wide white/cream gaps in the middle (it would split them into two crops) and on neutral-colored diagrams where individual rows did not cross the color density threshold but the area as a whole was clearly an illustration.

## Duplicate Pages 3-70 Skipped

**Decision**: The English PDF renders only pages 71-367 from the Hebrew source, completely skipping pages 3-70.

**Why**: The Hebrew book contains two versions of the same content. Pages 3-67 are a condensed overview, and pages 71 onward are the full expanded treatment. Including both would produce a confusing English book with duplicate content. The expanded version is authoritative and contains all the detail. The crop editor enforces this with `MIN_PAGE = 71`.

## Dynamic English TOC Instead of Hebrew TOC Pages

**Decision**: The Hebrew book's own table of contents pages are skipped, and a dynamically generated English TOC is inserted instead.

**Why**: The Hebrew TOC is, obviously, in Hebrew, and its page numbers reference the Hebrew page layout, not the English one. Since the English book has a completely different page count and layout, the TOC must be regenerated with correct English page numbers every time the book is re-typeset. The 65 topic entries are hardcoded by Perek:Pasuk reference in the `topicDescriptionMap`, and their page numbers are auto-calculated during typeset.

## Three-Part PDF Upload

**Decision**: The exported PDF is split into three parts.

**Why**: Supabase Storage has a 50MB upload limit per file. The full 353-page PDF with embedded illustrations exceeds this. Splitting into three roughly equal parts keeps each under the limit while still being easy to download and concatenate.

## Debian Docker Instead of Alpine

**Decision**: The Railway Dockerfile uses `node:20-slim` (Debian-based) instead of Alpine.

**Why**: Playwright/Chromium requires shared libraries that are difficult to install on Alpine. The Alpine image would need `apk add` for numerous dependencies (libstdc++, nss, freetype, harfbuzz, etc.) and some packages are not available or have version mismatches. Debian slim includes these libraries or makes them trivially installable. The image size increase (~200MB) is acceptable for correct rendering.

## `keepHebrew` Toggle in sanitizeForPdf

**Decision**: The `sanitizeForPdf()` function has a `keepHebrew` parameter that defaults to `false` for pdf-lib and `true` for HTML.

**Why**: When Hebrew bidi is broken (pdf-lib), showing garbled Hebrew is worse than showing no Hebrew. Stripping Hebrew characters from body text in the pdf-lib path produces readable (if incomplete) output. The HTML path keeps all Hebrew because Chromium renders it correctly.

## No Middle-Dot Separators

**Decision**: Middle-dot characters (·) are never used as word separators or decorative elements.

**Why**: The user explicitly rejected them as visual noise. ArtScroll publications do not use them. They were briefly added to some section dividers and immediately removed.

## Source Image Approach for Letter Pages

**Decision**: Pages 4-12 (approbation letters) show the full original Hebrew source image with English translation below, rather than attempting to typeset the letter content.

**Why**: Approbation letters have unique visual formatting (signatures, letterheads, varied layouts) that would be extremely difficult to reproduce in typeset form. Showing the original image preserves the visual authenticity while the English translation provides comprehension.

## Known Diagram Pages as Full-Page Images

**Decision**: 25 specific pages are hardcoded as "diagram pages" that display the full source image rather than attempting crop extraction.

**Why**: These pages are architectural schematics covered in dozens of small Hebrew labels pointing to specific features. Cropping individual "illustrations" from them is meaningless -- the entire page IS the illustration. Showing the full image with an English description is the only reasonable approach.

## IoU for Crop Evaluation

**Decision**: Intersection over Union (IoU) is the scoring metric for illustration crop quality.

**Why**: IoU naturally penalizes both over-cropping (including too much surrounding content) and under-cropping (missing parts of the illustration). A crop that perfectly matches the ground truth scores 1.0, a crop that misses half the illustration scores ~0.5, and a completely wrong crop scores near 0. This aligns with the actual quality concern: does the cropped image show the right thing?

## Eval Weight System (3/2/1)

**Decision**: Unified evals use a 3-tier importance weight: 3 (critical), 2 (important), 1 (polish).

**Why**: Not all quality checks are equally important. Hebrew characters rendering correctly (E1) matters infinitely more than paragraph spacing being 8pt vs 10pt. Without weights, a change that fixes a critical rendering bug but slightly adjusts spacing could score as "no improvement." The weight system ensures critical issues always dominate the score.

## Run PDF Generation Locally, Not on Railway

**Decision**: PDF generation is typically run locally via `npx next dev`, not on the Railway deployment.

**Why**: Generating a 353-page PDF with Playwright takes several minutes and significant memory. Railway has request timeout limits and memory constraints that can cause the generation to fail mid-way. Running locally avoids these limits. The generated PDF parts are then uploaded to Supabase storage.

## `process.env["KEY"]` Bracket Notation

**Decision**: All runtime environment variable access uses bracket notation.

**Why**: Next.js standalone mode (used in the Docker deployment) inlines `process.env.KEY` dot-notation access at BUILD time. This means that if the env var changes on Railway after the build, the app still uses the old value. Bracket notation (`process.env["KEY"]`) is not inlined, so it reads the actual runtime value. This is a project-wide rule that applies to all Shmuel's Next.js projects.
