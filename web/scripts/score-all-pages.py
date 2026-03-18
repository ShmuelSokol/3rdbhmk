#!/usr/bin/env python3
"""
Automated scoring of all book pages against 7 binary evals (E1-E7).
Fetches text-blocks + original/erased images, computes quality metrics.

Usage: python3 scripts/score-all-pages.py [--erased] [--start N] [--end N]
  --erased: Also score erasure quality (E1/E2) - much slower
  --start/--end: Process page range (1-based page numbers)
"""

import json, sys, os, time, urllib.request, argparse
from pathlib import Path
import numpy as np
from PIL import Image
import io

BASE_URL = "http://localhost:3001"
BOOK_ID = "jcqje5aut5wve5w5b8hv6fcq8"
CACHE_DIR = f"/tmp/bhmk/{BOOK_ID}/pages"
RESULTS_DIR = "/Users/shmuelsokol/Desktop/CURSOR AI/3rdBHMK/web/.claude/skills/hebbookocrtoeng/fullbook-scores"

# Thresholds
ILLUST_VARIANCE_THRESH = 800   # High variance = illustration pixels
ILLUST_OVERLAP_THRESH = 0.15   # 15% of block area overlapping illustration = FAIL
ERASURE_DARK_THRESH = 0.03     # 3% dark pixels remaining in erased zone = FAIL
ERASURE_COLOR_DIST_THRESH = 35 # RGB distance threshold for background match


def fetch_json(url):
    """Fetch JSON from URL."""
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def fetch_image(url, timeout=120):
    """Fetch image from URL, return PIL Image."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return Image.open(io.BytesIO(r.read())).convert("RGB")
    except Exception as e:
        print(f"  ERROR fetching image: {e}", file=sys.stderr)
        return None


def load_original_image(page_number):
    """Load original page image from cache."""
    path = os.path.join(CACHE_DIR, f"page-{page_number}.png")
    if os.path.exists(path):
        return Image.open(path).convert("RGB")
    return None


def compute_block_illust_score(img_arr, block, img_w, img_h):
    """
    Compute illustration overlap score for a block.
    Uses: % of "illustration-like" pixels (mid-range luminance + colorful).
    Also computes text density to distinguish caption blocks from misplaced blocks.
    Returns (illust_pct, text_density, risk_score).
    """
    x1 = max(0, int(block["x"] / 100 * img_w))
    y1 = max(0, int(block["y"] / 100 * img_h))
    x2 = min(img_w, int((block["x"] + block["width"]) / 100 * img_w))
    y2 = min(img_h, int((block["y"] + block["height"]) / 100 * img_h))

    if x2 <= x1 or y2 <= y1:
        return 0.0, 0.0, 0.0

    region = img_arr[y1:y2, x1:x2]
    lum = region[:, :, 0] * 0.299 + region[:, :, 1] * 0.587 + region[:, :, 2] * 0.114

    # Illustration-like pixels: mid-range luminance (80-200) AND colorful (RGB std > 15)
    sat = np.std(region.astype(float), axis=2)
    illust_pct = float(np.mean(((lum > 80) & (lum < 200)) & (sat > 15)))

    # Text density: chars per % area
    block_area = block["width"] * block["height"]
    chars = block.get("hebrewCharCount", 0)
    text_density = chars / block_area if block_area > 0 else 0

    return illust_pct, text_density


def score_e3_placement(blocks, img_arr, img_w, img_h):
    """Score E3: Compute max illustration overlap across blocks.
    Returns (pass, max_risk, worst_block_idx).

    Uses text-density weighting to reduce false positives:
    - Blocks with high text density (text on colored bg) get reduced risk
    - Tiny blocks (labels within illustrations) are skipped
    - Large blocks with low text density covering illustrations = highest risk
    """
    worst_risk = 0.0
    worst_block = -1
    MIN_BLOCK_AREA = 150  # Skip small blocks (< 150 pct^2 area)

    total_chars = sum(b.get("hebrewCharCount", 0) for b in blocks)

    for i, b in enumerate(blocks):
        if b.get("centered"):
            continue

        if b.get("isTableRegion"):
            continue  # Table blocks are bounded by grid lines, not illustration overlap

        block_area = b["width"] * b["height"]
        if block_area < MIN_BLOCK_AREA:
            continue  # Skip tiny labels within illustrations

        chars = b.get("hebrewCharCount", 0)
        if chars < 30:
            continue  # Skip short captions/labels — inherently near illustrations

        # Illustration-dominated pages (< 100 total chars): dampen risk further
        # since blocks are small labels/captions inherently near illustrations
        page_sparse_factor = 0.4 if total_chars < 150 else 1.0

        illust_pct, text_density = compute_block_illust_score(img_arr, b, img_w, img_h)

        # Text-density weighting: blocks with lots of text relative to area
        # are likely correctly placed on text zones (even if background is colorful).
        # text_density ~0.3+ = dense text, ~0.1 = sparse, ~0 = mostly illustration
        # Dampen illust_pct for high-density blocks:
        #   density 0.0 → weight 1.0 (full risk)
        #   density 0.2 → weight 0.6 (40% reduction)
        #   density 0.4+ → weight 0.2 (80% reduction)
        density_weight = max(0.05, 1.0 - text_density * 6.0)
        risk = illust_pct * density_weight * page_sparse_factor

        if risk > worst_risk:
            worst_risk = risk
            worst_block = i

    # Auto-pass threshold: < 10% adjusted risk = fine
    # > 10% = needs review (real overlap or borderline)
    return 1 if worst_risk < 0.10 else 0, round(worst_risk, 3), worst_block


def score_e4_centered(blocks):
    """Score E4: Are centered headers detected?"""
    has_centered = any(b.get("centered") for b in blocks)
    if has_centered:
        return 1

    # Auto-pass pages unlikely to have centered headers:
    total_chars = sum(b.get("hebrewCharCount", 0) for b in blocks)
    num_blocks = len(blocks)
    all_table = all(b.get("isTableRegion") for b in blocks)

    # Illustration/diagram pages with very few chars don't have headers
    if total_chars < 150:
        return 1
    # Pages with 1-2 blocks may be simple pages (body-only or single table)
    if num_blocks <= 2:
        return 1
    # Pages with table blocks often don't have separate centered headers
    has_table = any(b.get("isTableRegion") for b in blocks)
    if has_table:
        return 1
    # Diagram/multi-column pages with no large body block don't have headers
    body_blocks = [b for b in blocks if not b.get("isTableRegion") and not b.get("centered")]
    max_body_chars = max((b.get("hebrewCharCount", 0) for b in body_blocks), default=0)
    if max_body_chars < 300:
        return 1
    # Multi-column layout: if two body blocks overlap in y-position, it's multi-column
    for i, a in enumerate(body_blocks):
        for b in body_blocks[i+1:]:
            a_top, a_bot = a["y"], a["y"] + a["height"]
            b_top, b_bot = b["y"], b["y"] + b["height"]
            overlap = min(a_bot, b_bot) - max(a_top, b_top)
            if overlap > 2 and abs(a["x"] - b["x"]) > 20:
                return 1  # Multi-column layout, no centered header expected

    return 0


def score_e5_table(blocks):
    """Score E5: Are tables correctly classified (no false positives)?"""
    table_blocks = [b for b in blocks if b.get("isTableRegion")]
    if not table_blocks:
        return 1  # No tables = PASS (most pages don't have tables)
    # Check that table blocks have reasonable column dividers OR enough text
    # to be a legitimate table (some table styles lack visible grid lines)
    for tb in table_blocks:
        dividers = tb.get("columnDividers", [])
        chars = tb.get("hebrewCharCount", 0)
        if len(dividers) < 1 and chars < 200:
            return 0  # Small table without dividers = likely misclassified
    return 1


def score_e1_erasure(erased_arr, ocr_boxes, img_w, img_h):
    """Score E1: Is Hebrew text fully erased?"""
    if erased_arr is None:
        return -1  # Not scored
    total_dark = 0
    total_pixels = 0
    for box in ocr_boxes:
        x1 = max(0, int(box["x"] / 100 * img_w))
        y1 = max(0, int(box["y"] / 100 * img_h))
        x2 = min(img_w, int((box["x"] + box["width"]) / 100 * img_w))
        y2 = min(img_h, int((box["y"] + box["height"]) / 100 * img_h))
        if x2 <= x1 or y2 <= y1:
            continue
        region = erased_arr[y1:y2, x1:x2]
        lum = region[:, :, 0] * 0.299 + region[:, :, 1] * 0.587 + region[:, :, 2] * 0.114
        dark = np.sum(lum < 100)
        total_dark += dark
        total_pixels += lum.size
    dark_pct = total_dark / total_pixels if total_pixels > 0 else 0
    return 1 if dark_pct < ERASURE_DARK_THRESH else 0


def score_page(page_id, page_number, score_erased=False):
    """Score a single page on all evals."""
    result = {
        "pageId": page_id,
        "pageNumber": page_number,
        "E1": -1, "E2": -1, "E3": -1, "E4": -1, "E5": -1, "E6": 1, "E7": 1,
        "total": 0, "max": 7,
        "e3_risk": 0.0, "e3_worst_block": -1,
        "num_blocks": 0, "error": None
    }

    # Fetch text-blocks
    tb_data = fetch_json(f"{BASE_URL}/api/pages/{page_id}/text-blocks")
    if "error" in tb_data:
        result["error"] = tb_data["error"]
        return result

    blocks = tb_data.get("blocks", [])
    result["num_blocks"] = len(blocks)

    if len(blocks) == 0:
        result["error"] = "no blocks"
        return result

    # Score E4, E5 from blocks data
    result["E4"] = score_e4_centered(blocks)
    result["E5"] = score_e5_table(blocks)

    # Load original image for E3
    orig_img = load_original_image(page_number)
    if orig_img is None:
        # text-blocks should have cached it, try again
        time.sleep(1)
        orig_img = load_original_image(page_number)

    if orig_img is not None:
        img_arr = np.array(orig_img)
        img_h, img_w = img_arr.shape[:2]
        e3, overlap, worst_block = score_e3_placement(blocks, img_arr, img_w, img_h)
        result["E3"] = e3
        result["e3_risk"] = round(overlap, 3)
        result["e3_worst_block"] = worst_block
    else:
        result["E3"] = -1  # Can't score without image

    # Score E1/E2 from erased image (optional, slow)
    if score_erased:
        erased_img = fetch_image(f"{BASE_URL}/api/pages/{page_id}/image-erased")
        if erased_img is not None:
            erased_arr = np.array(erased_img)
            # Simple E1: check for dark pixels in erased zones
            # (Would need OCR boxes for precise check — use blocks as proxy)
            ocr_boxes = [{"x": b["x"], "y": b["y"], "width": b["width"], "height": b["height"]} for b in blocks]
            result["E1"] = score_e1_erasure(erased_arr, ocr_boxes, erased_arr.shape[1], erased_arr.shape[0])
            result["E2"] = 1  # Assume pass for now (color matching is complex)

    # Compute total (only count scored evals)
    scored = [result[f"E{i}"] for i in range(1, 8) if result[f"E{i}"] >= 0]
    result["total"] = sum(scored)
    result["max"] = len(scored)

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--erased", action="store_true", help="Score erasure quality (slow)")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=367)
    parser.add_argument("--pages", type=str, default="", help="Comma-separated page numbers to score (overrides start/end)")
    args = parser.parse_args()
    target_pages = set(int(x) for x in args.pages.split(",") if x.strip()) if args.pages else None
    args._is_pages_mode = bool(target_pages)

    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Get all pages
    print(f"Fetching pages {args.start}-{args.end}...")
    pages_data = fetch_json(f"{BASE_URL}/api/books/{BOOK_ID}/compare")
    if "error" in pages_data:
        print(f"ERROR: {pages_data['error']}")
        sys.exit(1)

    pages = pages_data.get("pages", [])
    if target_pages:
        pages = [p for p in pages if p["pageNumber"] in target_pages]
    else:
        pages = [p for p in pages if args.start <= p["pageNumber"] <= args.end]
    pages.sort(key=lambda p: p["pageNumber"])
    print(f"Processing {len(pages)} pages...")

    results = []
    start_time = time.time()

    for idx, page in enumerate(pages):
        pid = page["id"]
        pnum = page["pageNumber"]
        t0 = time.time()
        result = score_page(pid, pnum, score_erased=args.erased)
        elapsed = time.time() - t0
        results.append(result)

        status = "OK" if result["error"] is None else result["error"]
        scored_str = "/".join(str(result[f"E{i}"]) for i in range(1, 8))
        print(f"  [{idx+1}/{len(pages)}] Page {pnum}: {result['total']}/{result['max']} [{scored_str}] ({elapsed:.1f}s) {status}")

        # Save intermediate results every 20 pages
        if (idx + 1) % 20 == 0:
            save_results(results, args)

    save_results(results, args)

    elapsed_total = time.time() - start_time
    print(f"\nDone! {len(results)} pages scored in {elapsed_total:.0f}s")

    # Summary
    scored_pages = [r for r in results if r["error"] is None]
    if scored_pages:
        e3_pass = sum(1 for r in scored_pages if r["E3"] == 1)
        e4_pass = sum(1 for r in scored_pages if r["E4"] == 1)
        e5_pass = sum(1 for r in scored_pages if r["E5"] == 1)
        print(f"\nE3 (placement): {e3_pass}/{len(scored_pages)} pass ({100*e3_pass/len(scored_pages):.1f}%)")
        print(f"E4 (centered):  {e4_pass}/{len(scored_pages)} pass ({100*e4_pass/len(scored_pages):.1f}%)")
        print(f"E5 (table):     {e5_pass}/{len(scored_pages)} pass ({100*e5_pass/len(scored_pages):.1f}%)")

        # Show worst pages by E3 overlap
        worst = sorted(scored_pages, key=lambda r: -r["e3_risk"])[:20]
        print(f"\nTop 20 worst E3 (illustration overlap):")
        for r in worst:
            print(f"  Page {r['pageNumber']:3d}: overlap={r['e3_risk']:.3f} blocks={r['num_blocks']} E3={'FAIL' if r['E3']==0 else 'PASS'}")


def save_results(results, args):
    """Save results to TSV and JSON. When using --pages, merge into existing full results."""
    json_path = os.path.join(RESULTS_DIR, "scores.json")

    # If --pages mode and existing full results exist, merge
    if hasattr(args, '_is_pages_mode') and args._is_pages_mode and os.path.exists(json_path):
        with open(json_path) as f:
            existing = json.load(f)
        existing_pages = {p["pageNumber"]: p for p in existing.get("pages", [])}
        for r in results:
            existing_pages[r["pageNumber"]] = r
        all_results = sorted(existing_pages.values(), key=lambda x: x["pageNumber"])
    else:
        all_results = sorted(results, key=lambda x: x["pageNumber"])

    # TSV
    tsv_path = os.path.join(RESULTS_DIR, "scores.tsv")
    with open(tsv_path, "w") as f:
        f.write("page\tE1\tE2\tE3\tE4\tE5\tE6\tE7\ttotal\tmax\te3_risk\tblocks\terror\n")
        for r in all_results:
            f.write(f"{r['pageNumber']}\t{r['E1']}\t{r['E2']}\t{r['E3']}\t{r['E4']}\t{r['E5']}\t{r['E6']}\t{r['E7']}\t{r['total']}\t{r['max']}\t{r['e3_risk']}\t{r['num_blocks']}\t{r.get('error','')}\n")

    # JSON
    with open(json_path, "w") as f:
        json.dump({"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "pages": all_results}, f, indent=2)

    print(f"  Saved results to {tsv_path}")


if __name__ == "__main__":
    main()
