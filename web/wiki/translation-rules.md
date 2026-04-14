# Translation Rules

The English translation follows ArtScroll conventions -- the gold standard for English-language Torah literature. The target audience is an Ashkenazi yeshiva-educated (frum-from-birth) Jewish reader who is comfortable with common Hebrew and Aramaic terms but needs the text in English for comprehension of the full content.

## ArtScroll Style

ArtScroll publications are characterized by:

1. **Flowing scholarly English** that reads naturally while preserving the precision of the original Hebrew.
2. **Hebrew/Aramaic terms sprinkled throughout** where a yeshiva reader would expect them: Beis HaMikdash (not "Holy Temple"), Mishkan (not "Tabernacle"), Shechina (not "Divine Presence"), avodah (not "service"), korbanos (not "sacrifices"), kedusha (not "holiness"), Kohanim (not "priests"), Levi'im (not "Levites").
3. **Inline Hebrew quotes** for direct scriptural and Talmudic citations, presented in the em-dash format.
4. **Source citations in standard yeshiva format**: Gemara tractate + daf (e.g., "Zevachim 118b"), Rashi/Rambam location, Chumash perek:pasuk (e.g., "Devarim 12:13").

## Hebrew Quote Format

When the Hebrew text directly quotes a pasuk from Tanach or a passage from Gemara, the translation must include the original Hebrew. The format is:

```
"Hebrew text — English translation (Source reference)"
```

For example:
> The Gemara (Zevachim 118b) states: "באו לשילה -- נאסרו הבמות" -- They came to Shiloh and the bamos were forbidden.

Rules for inline Hebrew quotes:

- **Short Torah/Gemara quotes**: Always keep the original Hebrew/Aramaic with source reference, then translate to English.
- **Long multi-sentence quotes**: Can be English-only to avoid overwhelming the reader.
- **Spacing**: There MUST be proper spacing between Hebrew and English text -- space + em-dash + space. No `HebrewText—EnglishText` without spaces.
- **Hebrew characters MUST render correctly**: The PDF must embed a Hebrew font (NotoSerifHebrew). The HTML renderer handles this natively; the pdf-lib renderer has known bidi issues.

## Citation Normalization

The `enhance-artscroll.js` script normalizes citation formats:

- "Chapter" -> "Perek"
- "verse" -> "Pasuk"
- "folio" -> "Daf"
- Chapter:Verse references use standard yeshiva formatting

## Hebrew Letter Names

Spelled-out Hebrew letter names in English text are replaced with actual Hebrew characters where appropriate. The enhance script handles this systematically across all 681+ enhanced regions.

## Numbered Items

When the source text contains numbered lists (itemized lists), the number appears ONCE on the correct side -- before the English text. Numbers are never duplicated or placed on the wrong side of inline Hebrew text.

## Text Flow

Hebrew and English must flow naturally within the same paragraph. The translation avoids:
- Abrupt joins between Hebrew quotes and English text
- Missing whitespace between segments
- CamelCase-style joins like "West4Its" (digit-letter joins are caught by regex rules)

## The Enhancement Pipeline

The `enhance-artscroll.js` script (at `scripts/enhance-artscroll.js`) is the main tool for bringing translations up to ArtScroll quality. It:

1. Loads ContentRegion records from the database
2. For each region, identifies where Hebrew source text should be inserted inline
3. Inserts Hebrew with em-dash format
4. Replaces spelled-out Hebrew letter names with actual Hebrew characters
5. Normalizes citation formats
6. Writes enhanced text back to the database

Run with `--force` to re-enhance previously processed regions. By default, only processes eval page ranges (to avoid touching pages that may have been manually refined).

The script has enhanced 681+ regions across the book. The `insert-pesukim-hebrew.js` script handles a related but distinct task: finding specific pasuk references in the text and inserting the original Hebrew text of those pesukim from an OCR source.

## What NOT to Do

- **Never add middle-dot separators** -- they create visual noise and are not part of the ArtScroll style.
- **Never translate standard Hebrew terms**: A yeshiva reader knows what "Kohen Gadol" means. Do not write "High Priest" unless context demands it.
- **Never strip Hebrew from body text** in the HTML renderer -- `keepHebrew` must be `true`. Hebrew stripping is only for the pdf-lib fallback where bidi is broken.
