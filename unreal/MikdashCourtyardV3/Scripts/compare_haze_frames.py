"""Before/after numbers for the HorizonHazeV1 pass (system Python, PIL + numpy).

near  : mean sRGB colour, mean Rec.709 luminance (linearised), and the worst per-cell change
        on a 16 x 9 grid for each (reference, candidate) pair of close-range frames. A global
        mean can hide a local shift; the grid cannot.
far   : the horizon band's vertical value profile in P1/D1/D2 - per-row mean luminance and
        blue-minus-red across the band region, so value layering (ridges stepping back) and
        colour can be compared build to build instead of eyeballed.

    python Scripts/compare_haze_frames.py near <refLabel> <candLabel> [--out f.json]
    python Scripts/compare_haze_frames.py far <label> [<label> ...] [--out f.json]
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

VR = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\visual-review')
NEAR = ['N1-azarah-spawn-facing-heichal', 'N2-herodian-jamb-walkingheight',
        'N3-kotel-plaza-upper-deck-MODERN', 'N4-heichal-interior']
FAR = ['P1-precinct-plaza-aerial-SW-corner', 'P1M-precinct-plaza-aerial-SW-corner-MODERN',
       'D1-dove-1500m-horizon-west', 'D2-dove-1500m-horizon-east-dead-sea']


def load(label, view):
    p = VR / ('%s-%s.png' % (label, view))
    if not p.exists():
        return None, p
    im = Image.open(p).convert('RGB')
    # 2x box downsample + float32: a 3840x2160 float64 frame is 190 MB per array and this box's
    # Python is 32-bit (MemoryError on the first run). Means and grid-cell means are preserved.
    im = im.resize((im.width // 2, im.height // 2), Image.BOX)
    return np.asarray(im, dtype=np.float32) / 255.0, p


def lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4).astype(np.float32)


def lum(a):
    l = lin(a)
    return 0.2126 * l[..., 0] + 0.7152 * l[..., 1] + 0.0722 * l[..., 2]


def near(ref, cand):
    rows = []
    for v in NEAR:
        a, pa = load(ref, v)
        b, pb = load(cand, v)
        if a is None or b is None:
            rows.append({'view': v, 'missing': [str(p) for p, x in ((pa, a), (pb, b)) if x is None]})
            continue
        la, lb = lum(a), lum(b)
        H, W = la.shape
        worst = 0.0
        worst_cell = None
        for j in range(9):
            for i in range(16):
                ys, ye = j * H // 9, (j + 1) * H // 9
                xs, xe = i * W // 16, (i + 1) * W // 16
                ma, mb = la[ys:ye, xs:xe].mean(), lb[ys:ye, xs:xe].mean()
                rel = abs(mb - ma) / max(ma, 1e-4)
                if rel > worst:
                    worst, worst_cell = float(rel), [i, j, round(float(ma), 5), round(float(mb), 5)]
        rows.append({'view': v,
                     'refMeanSRGB255': [round(float(x) * 255, 2) for x in a.reshape(-1, 3).mean(0)],
                     'candMeanSRGB255': [round(float(x) * 255, 2) for x in b.reshape(-1, 3).mean(0)],
                     'refMeanLumLinear': round(float(la.mean()), 5),
                     'candMeanLumLinear': round(float(lb.mean()), 5),
                     'meanLumChangePct': round(float(100 * (lb.mean() - la.mean()) / max(la.mean(), 1e-6)), 3),
                     'worstCellLumChangePct': round(100 * worst, 2), 'worstCell_i_j_ref_cand': worst_cell})
    return {'mode': 'near', 'reference': ref, 'candidate': cand, 'pairs': rows}


def far(labels):
    out = []
    for v in FAR:
        for label in labels:
            a, p = load(label, v)
            if a is None:
                continue
            H, W = a.shape[:2]
            y0, y1 = int(0.30 * H), int(0.70 * H)
            x0, x1 = int(0.10 * W), int(0.90 * W)
            region = a[y0:y1, x0:x1]
            l = lum(region).mean(axis=1)
            br = (region[..., 2] - region[..., 0]).mean(axis=1) * 255
            step = max(1, (y1 - y0) // 24)
            out.append({'view': v, 'label': label,
                        'rows': '%d..%d of %d (every %d)' % (y0, y1, H, step),
                        'lumProfile': [round(float(x), 4) for x in l[::step]],
                        'blueMinusRedProfile': [round(float(x), 1) for x in br[::step]],
                        # value layering: how much the band's luminance varies row to row
                        'lumRowStdev': round(float(np.std(np.diff(l))), 5)})
    return {'mode': 'far', 'labels': labels, 'profiles': out}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--out')]
    outp = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--out=')), None)
    res = near(args[1], args[2]) if args[0] == 'near' else far(args[1:])
    text = json.dumps(res, indent=1)
    if outp:
        Path(outp).write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
