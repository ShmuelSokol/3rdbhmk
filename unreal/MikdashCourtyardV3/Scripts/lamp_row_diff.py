"""Lamp-row before/after diff from a -dumpmovie filmstrip (Scripts/capture_people_walk_movie.ps1).

Reproduces the comparison KOHEN-TEND-RECEIPT.md made for cp14, with numbers so "differs" is
measured and not eyeballed:
  control   25 s vs 35 s   nothing is kindled between them
  test      35 s vs 115 s  five lamps are kindled between them
Frame i of a -benchmark -fps=10 run is i/10 s of game time.

For each pair: the lamp-row crop of both frames, and |A-B| amplified x4. Metrics over the
crop: mean |diff| (0-255), fraction of pixels whose luminance changed by more than 24 levels,
and the number of pixels that went from below 200 to above 235 luminance ("new bright points",
which is what a flame appearing does and a moving arm mostly does not).

  python Scripts/lamp_row_diff.py <movie-folder> <out.png> [--crop x0 y0 x1 y1] [--pairs 250:350 350:1150]
"""
import argparse, json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


def frame(folder, index):
    hits = sorted(Path(folder).glob('*-%04d.png' % index))
    if not hits:
        raise SystemExit('no frame %04d in %s' % (index, folder))
    return Image.open(hits[0]).convert('RGB')


def lum(im):
    return im.convert('L')


def metrics(a, b):
    d = ImageChops.difference(a, b)
    la, lb, ld = lum(a), lum(b), lum(d)
    px = la.width * la.height
    hist = ld.histogram()
    mean = sum(i * n for i, n in enumerate(hist)) / px
    changed = sum(hist[25:]) / px
    pa, pb = la.load(), lb.load()
    appeared = disappeared = 0
    for y in range(la.height):
        for x in range(la.width):
            if pa[x, y] < 200 and pb[x, y] > 235:
                appeared += 1
            elif pa[x, y] > 235 and pb[x, y] < 200:
                disappeared += 1
    return dict(meanAbsDiff=round(mean, 3), fracLumChangedOver24=round(changed, 5),
                newBrightPixels=appeared, lostBrightPixels=disappeared)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('out')
    ap.add_argument('--crop', type=int, nargs=4, default=[940, 620, 1240, 860])
    ap.add_argument('--pairs', nargs='*', default=['250:350', '350:1150'])
    ap.add_argument('--scale', type=int, default=2)
    ap.add_argument('--fps', type=float, default=10.0)
    a = ap.parse_args()
    rows, report = [], []
    for spec in a.pairs:
        i, j = (int(v) for v in spec.split(':'))
        A, B = frame(a.folder, i).crop(tuple(a.crop)), frame(a.folder, j).crop(tuple(a.crop))
        m = metrics(A, B)
        m.update(pair='%.1fs vs %.1fs' % (i / a.fps, j / a.fps), frames=[i, j])
        report.append(m)
        D = ImageChops.difference(A, B).point(lambda v: min(255, v * 4))
        w, h = A.width * a.scale, A.height * a.scale
        tiles = [t.resize((w, h), Image.NEAREST) for t in (A, B, D)]
        row = Image.new('RGB', (3 * w, h))
        for k, t in enumerate(tiles):
            row.paste(t, (k * w, 0))
        dr = ImageDraw.Draw(row)
        text = '%s   mean|d| %.2f   changed>24 %.2f%%   new bright px %d' % (
            m['pair'], m['meanAbsDiff'], 100 * m['fracLumChangedOver24'], m['newBrightPixels'])
        dr.rectangle((0, 0, 8 + 7 * len(text), 16), fill=(0, 0, 0))
        dr.text((4, 2), text, fill=(255, 255, 0))
        rows.append(row)
    sheet = Image.new('RGB', (rows[0].width, sum(r.height for r in rows)))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    sheet.save(a.out)
    out_json = Path(a.out).with_suffix('.json')
    out_json.write_text(json.dumps(dict(folder=str(a.folder), crop=a.crop, pairs=report), indent=2) + '\n',
                        encoding='utf-8')
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
