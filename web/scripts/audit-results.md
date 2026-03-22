# Full Illustration & OCR Audit — 2026-03-22

## FINDING 1: ~160 pages have MISSING illustrations

Of 201 pages classified as "text-only", approximately 160 actually have significant illustrations (3D renders, floor plans, architectural diagrams, measurement charts) that are NOT included in the English PDF.

### Root cause
The `detectAndCropIllustrations` function uses gap analysis between OCR text regions. It fails when:
- OCR detects text labels ON TOP of illustrations (annotation text within the image)
- Illustrations sit between text lines with < 8% page height gap
- A single OCR region spans both text and illustration areas

### Sample pages with missing illustrations (confirmed visually):
- **Page 110**: Chart of 8 3D Beis HaMikdash models (spiritual/physical hierarchy) + large 3D render
- **Page 133**: 2 large 3D renders of gate chambers + measurement diagram
- **Page 165**: 3D chamber interior render + highlighted floor plan
- **Page 230**: Detailed golden ceiling/wall texture images (Heichal decorations)
- **Page 300**: TWO large 3D models of entire Beis HaMikdash complex with labeled sections (A-Q)

### Estimated scope
- Pages 105-367: ~160 pages have at least 1 illustration missing
- Total missing illustrations: ~200-300 individual images
- Many are critical architectural diagrams essential for understanding the text

## FINDING 2: OCR quality issues

### Missing regions
Some pages have fewer OCR regions than expected. E.g., page 133 has only 1 region in the DB but visually contains 4+ distinct text sections (Rashi, Keitz HaYamin, Be'ur Chai, Hashlamat Shares).

### OCR accuracy
For the regions that DO exist, the Hebrew OCR text generally matches what I see in the images. The main issues are:
- **Linearized spatial content**: Measurement labels, diagram annotations, and chart data get linearized into nonsensical text strings
- **Missing sections**: Commentary layers (Keitz HaYamin, Be'ur Chai, Hashlamat Shares) sometimes not captured as separate regions
- **Garbled handwritten text**: Haskamos/approval letters have poor OCR quality (pages 72-90)

### OCR comparison samples (my reading vs DB):
- Page 133 R0: Pasuk text matches ✓
- Page 165 R0: Pasuk text matches ✓, but Keitz HaYamin and Be'ur Chai sections not in DB
- Page 230 R0/R1: Text matches ✓, but illustration labels not captured
- Page 300 R0: Pasuk text matches ✓, but floor plan labels (A-Q) not in DB

## RECOMMENDATIONS

### For missing illustrations:
1. **Best approach**: Add ALL pages with illustrations to `knownDiagrams` set — renders them as full source images with translated text below (like letter pages). This preserves every illustration.
2. **Alternative**: Improve gap detection with pixel-level image variance analysis instead of relying solely on OCR region gaps.
3. **Quick fix**: Manually curate the list by adding the ~160 page numbers identified here.

### For OCR issues:
1. **Re-run OCR** on pages with missing commentary sections (Azure OCR may need different region detection settings)
2. **For diagram pages rendered as images**: OCR quality matters less since the source image is shown
3. **For text pages**: The existing OCR is generally accurate for the main body text; the gaps are in secondary commentary sections

### Pages to add to knownDiagrams (from visual audit):
All pages with significant illustrations that are currently classified as "text-only":
105, 107, 108, 109, 110, 112, 113, 114, 115, 116, 117, 118, 121, 123, 125, 126, 127, 129, 130, 131, 133, 134, 135, 136, 137, 138, 143, 144, 145, 147, 150, 151, 152, 153, 154, 155, 156, 157, 158, 161, 163, 164, 165, 167, 169, 170, 171, 172, 173, 174, 176, 177, 178, 179, 182, 183, 184, 185, 186, 189, 190, 191, 192, 193, 195, 197, 198, 199, 200, 201, 202, 204, 205, 206, 207, 209, 210, 212, 216, 217, 219, 220, 222, 223, 224, 225, 227, 230, 231, 232, 233, 234, 235, 237, 238, 240, 241, 243, 245, 247, 248, 249, 251, 252, 255, 257, 260, 261, 262, 263, 266, 267, 268, 269, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 297, 298, 299, 300, 301, 302, 303, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 318, 319, 320, 321, 324, 325, 326, 327, 329, 330, 331, 332, 333, 335, 337, 338, 339, 340, 341, 342, 343, 345, 347, 349, 351, 352, 353, 354, 355, 357, 358, 362, 363
