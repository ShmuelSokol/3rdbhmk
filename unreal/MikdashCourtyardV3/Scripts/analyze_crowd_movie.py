"""Read motion out of a -dumpmovie filmstrip (Scripts/capture_people_walk_movie.ps1).

Subcommands (frames are the kept PNGs, 0.1 s of game time apart at -fps=10):
  diff       mean absolute RGB difference of a crop between two frames. A static figure
             cluster reads ~0 (the cp11 statues were pixel-identical 37 s apart); moving limbs do not.
  composite  stack the same crop from several frames with labels, for the eye.
  track      best integer (dx, dy) of a patch from frame A in each following frame, by sum of
             absolute differences over a +/-R search. A planted foot, like bare paving, must
             match at (0, 0); a sliding foot drifts. Run a bare-paving control patch alongside.

    python Scripts/analyze_crowd_movie.py diff --frames A.png B.png --box x y w h
    python Scripts/analyze_crowd_movie.py composite --frames A.png B.png ... --box x y w h --scale 3 --labels "t=0" "t=37s" --out out.png
    python Scripts/analyze_crowd_movie.py track --frames A.png B.png C.png --box x y w h --radius 12
"""
import argparse
import json

import numpy as np
from PIL import Image, ImageDraw


def load(path):
    return np.asarray(Image.open(path).convert('RGB'), dtype=np.float32)


def crop(img, box):
    x, y, w, h = box
    return img[y:y + h, x:x + w]


def cmd_diff(args):
    a, b = load(args.frames[0]), load(args.frames[1])
    ca, cb = crop(a, args.box), crop(b, args.box)
    d = np.abs(ca - cb)
    changed = float((d.max(axis=2) > args.threshold).mean())
    out = dict(frames=args.frames, box=args.box, meanAbsDiff=round(float(d.mean()), 4),
               maxAbsDiff=round(float(d.max()), 1), fractionPixelsChanged=round(changed, 4), threshold=args.threshold)
    print(json.dumps(out, indent=2))
    return out


def cmd_composite(args):
    tiles = []
    for i, path in enumerate(args.frames):
        img = Image.open(path).convert('RGB')
        x, y, w, h = args.box
        tile = img.crop((x, y, x + w, y + h)).resize((w * args.scale, h * args.scale), Image.NEAREST)
        band = Image.new('RGB', (tile.width, 26), (12, 12, 12))
        label = args.labels[i] if args.labels and i < len(args.labels) else path
        ImageDraw.Draw(band).text((6, 6), label, fill=(240, 220, 120))
        tiles.append((band, tile))
    width = max(t.width for _, t in tiles)
    height = sum(b.height + t.height for b, t in tiles)
    sheet = Image.new('RGB', (width, height), (0, 0, 0))
    y = 0
    for band, tile in tiles:
        sheet.paste(band, (0, y)); y += band.height
        sheet.paste(tile, (0, y)); y += tile.height
    sheet.save(args.out)
    print(args.out)


def cmd_track(args):
    ref = load(args.frames[0])
    x, y, w, h = args.box
    patch = crop(ref, args.box)
    rows = []
    for path in args.frames[1:]:
        img = load(path)
        best = None
        for dy in range(-args.radius, args.radius + 1):
            for dx in range(-args.radius, args.radius + 1):
                yy, xx = y + dy, x + dx
                if yy < 0 or xx < 0 or yy + h > img.shape[0] or xx + w > img.shape[1]:
                    continue
                res = float(np.abs(img[yy:yy + h, xx:xx + w] - patch).mean())
                if best is None or res < best[0]:
                    best = (res, dx, dy)
        zero = float(np.abs(crop(img, args.box) - patch).mean())
        rows.append(dict(frame=path, dx=best[1], dy=best[2], residual=round(best[0], 3), residualAtZero=round(zero, 3)))
    print(json.dumps(dict(reference=args.frames[0], box=args.box, radius=args.radius, matches=rows), indent=2))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('diff'); d.add_argument('--frames', nargs=2, required=True); d.add_argument('--box', nargs=4, type=int, required=True)
    d.add_argument('--threshold', type=float, default=12.0)
    c = sub.add_parser('composite'); c.add_argument('--frames', nargs='+', required=True); c.add_argument('--box', nargs=4, type=int, required=True)
    c.add_argument('--scale', type=int, default=2); c.add_argument('--labels', nargs='*'); c.add_argument('--out', required=True)
    t = sub.add_parser('track'); t.add_argument('--frames', nargs='+', required=True); t.add_argument('--box', nargs=4, type=int, required=True)
    t.add_argument('--radius', type=int, default=10)
    args = p.parse_args()
    {'diff': cmd_diff, 'composite': cmd_composite, 'track': cmd_track}[args.cmd](args)


if __name__ == '__main__':
    main()
