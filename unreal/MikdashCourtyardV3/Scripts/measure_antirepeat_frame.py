"""Judge the anti-repeat material on RENDERED frames: is the repeat broken, and did the detail survive?

Shmuel, verbatim: "I don't wanna see, like, repeating patterns all over."

The 2026-09-09 pass broke the repeat and flattened the surface (gradient energy x0.20 against an
in-frame M_PBR_Tiled control at x1.03). Offline numbers could see neither half. This script reads
only pixels, from frames taken by Scripts/capture_frame_ashlar.ps1 view 02 (1752,1200,580 pitch 5
yaw 0: 4 m from the inner eastern gate wall jamb at eye height), and answers both questions against
thresholds fixed HERE, before any after-frame existed:

  REPEAT BROKEN   the normalized autocorrelation of the wall one tile across (acU), after/before
                  <= 0.75, AND the horizontal tile-comb energy fraction, after/before <= 0.75.
  DETAIL SURVIVED wall gradient energy after/before, divided by the SAME ratio on the unmodified
                  paving strip in the same frames (the in-frame exposure/lighting control), >= 0.80
                  for raw gradient energy, 5-px-smoothed gradient energy (the chamfer/bevel scale)
                  and vertical gradient energy (the lit/shadowed horizontal drafted-margin chamfers
                  that make the boss read as raised). The failure being guarded against is x0.20.

Both must hold for verdict PASS. A frame that breaks the repeat and flattens the wall is a FAIL, and
the receipt says which half failed.

  python Scripts/measure_antirepeat_frame.py --before B.png --after A.png --out X.json \
      --sampling implicit --label cp13t [--reference cp11c-02.png]
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_antirepeat_materials as car  # noqa: E402

# Regions at 3840x2160, read off cp11c-02: the wall fills the frame down to its lowest course; the
# paving is the strip below it. The bottom-left watermark is excluded from the paving.
WALL = (0, 0, 3840, 1960)
PAVING = (400, 2072, 3840, 2160)
THRESHOLDS = {'repeatAcURatioMax': 0.75, 'repeatCombURatioMax': 0.75, 'detailNormalizedRatioMin': 0.80,
              'regressionReference': 'x0.20 = the 2026-09-09 grad master on Nanite'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def luma(path):
    rgb = np.asarray(Image.open(path).convert('RGB'), dtype=np.float64)
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2], rgb


def box(img, k):
    """k x k box blur via an integral image, edge-replicated."""
    pad = k // 2
    p = np.pad(img, pad, mode='edge')
    c = np.cumsum(np.cumsum(p, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = img.shape
    return (c[k:k + h, k:k + w] - c[:h, k:k + w] - c[k:k + h, :w] + c[:h, :w]) / (k * k)


def crop(a, b):
    x0, y0, x1, y1 = b
    return a[y0:y1, x0:x1]


def detail(lum):
    gy, gx = np.gradient(lum)
    sm = box(lum, 5)
    sgy, sgx = np.gradient(sm)
    return {'edgeEnergy': float(np.sqrt(gx * gx + gy * gy).mean()),
            'edgeEnergySmoothed': float(np.sqrt(sgx * sgx + sgy * sgy).mean()),
            'verticalEnergySmoothed': float(np.abs(sgy).mean()),
            'fineStd': float((lum - sm).std()),
            'lumaMean': float(lum.mean()), 'lumaStd': float(lum.std())}


def highpass(lum, k=151):
    """Remove the lighting gradient across the wall; keep everything up to about a block."""
    return lum - box(lum, k)


def row_acf(c):
    """Mean horizontal autocorrelation over rows, unbiased, normalized to 1 at lag 0."""
    h, w = c.shape
    f = np.fft.rfft(c, n=2 * w, axis=1)
    ac = np.fft.irfft(np.abs(f) ** 2, axis=1)[:, :w].mean(axis=0)
    ac = ac / (w - np.arange(w))
    return ac / ac[0]


def tile_period(c, lo=300, hi=1900):
    ac = row_acf(c)
    lag = int(lo + np.argmax(ac[lo:hi]))
    return lag, ac


def comb_u(c, period):
    """Fraction of non-DC horizontal spectral power on the harmonics of the tile period, per row, averaged."""
    n = (c.shape[1] // period) * period
    x = c[:, :n] - c[:, :n].mean(axis=1, keepdims=True)
    p = np.abs(np.fft.rfft(x, axis=1)) ** 2
    p[:, 0] = 0.0
    nu = n // period
    comb = np.zeros(p.shape[1], dtype=bool)
    comb[nu::nu] = True
    return float(p[:, comb].sum() / p.sum())


def repeat(lum_wall, period):
    c = highpass(lum_wall)
    ac = row_acf(c)
    out = {'acU': float(ac[period]), 'combU': comb_u(c, period)}
    n = (c.shape[1] // period) * period
    m = (c.shape[0] // period) * period
    if m >= period:
        rgb = np.repeat(c[:m, :n, None].astype(np.float32), 3, axis=2)
        out['comb2D_car'] = car.metrics(rgb - rgb.min(), period)['combEnergyFraction']
    lo = max(300, period // 2)
    hi = min(len(ac) - 1, int(period * 1.5))
    out['acPeakNearTile'] = {'lag': int(lo + np.argmax(ac[lo:hi])), 'value': float(ac[lo:hi].max())}
    return out


def frame(path, period=None):
    lum, _ = luma(path)
    if lum.shape != (2160, 3840):
        raise SystemExit('%s is %s, expected 3840x2160 from capture_frame_ashlar.ps1' % (path, lum.shape))
    wall, pav = crop(lum, WALL), crop(lum, PAVING)
    row = {'file': str(path), 'sha256': sha(path), 'wall': detail(wall), 'paving': detail(pav)}
    if period is None:
        period, _ = tile_period(highpass(wall))
    row['tilePeriodPx'] = period
    row['wallRepeat'] = repeat(wall, period)
    return row, period


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--before', required=True)
    ap.add_argument('--after', required=True)
    ap.add_argument('--reference', help='an older control frame of the same camera, reported only')
    ap.add_argument('--out', required=True)
    ap.add_argument('--sampling', required=True)
    ap.add_argument('--label', required=True)
    a = ap.parse_args()

    before, period = frame(a.before)
    after, _ = frame(a.after, period)
    ratios, norm = {}, {}
    for k in ('edgeEnergy', 'edgeEnergySmoothed', 'verticalEnergySmoothed', 'fineStd'):
        w = after['wall'][k] / before['wall'][k]
        p = after['paving'][k] / before['paving'][k]
        ratios[k] = {'wall': round(w, 4), 'paving': round(p, 4)}
        norm[k] = round(w / p, 4)
    rep = {k: round(after['wallRepeat'][k] / before['wallRepeat'][k], 4) for k in ('acU', 'combU')}
    repeat_ok = rep['acU'] <= THRESHOLDS['repeatAcURatioMax'] and rep['combU'] <= THRESHOLDS['repeatCombURatioMax']
    detail_keys = ('edgeEnergy', 'edgeEnergySmoothed', 'verticalEnergySmoothed')
    detail_ok = all(norm[k] >= THRESHOLDS['detailNormalizedRatioMin'] for k in detail_keys)
    failures = []
    if not detail_ok:
        failures.append('DETAIL LOST: normalized wall gradient ratios %s (need >= %.2f; the old failure was x0.20)'
                        % ({k: norm[k] for k in detail_keys}, THRESHOLDS['detailNormalizedRatioMin']))
    if not repeat_ok:
        failures.append('REPEAT NOT BROKEN: acU x%.3f, combU x%.3f (need <= %.2f)'
                        % (rep['acU'], rep['combU'], THRESHOLDS['repeatAcURatioMax']))
    out = {'label': a.label, 'samplingMode': a.sampling,
           'utc': datetime.now(timezone.utc).isoformat(), 'script': 'Scripts/measure_antirepeat_frame.py',
           'scriptSha256': sha(__file__), 'regions': {'wall': WALL, 'paving': PAVING}, 'thresholds': THRESHOLDS,
           'before': before, 'after': after,
           'repeatRatioAfterOverBefore': rep, 'detailRatioAfterOverBefore': ratios,
           'detailNormalizedByPavingControl': norm,
           'repeatBroken': repeat_ok, 'detailSurvived': detail_ok,
           'verdict': 'PASS' if (repeat_ok and detail_ok) else 'FAIL', 'failures': failures,
           'notJudgedHere': 'Whether the boss reads as raised is also checked by eye on 1:1 crops; '
                            'verticalEnergySmoothed is the numeric proxy for the lit/shadowed chamfers.'}
    if a.reference:
        ref, _ = frame(a.reference, period)
        out['reference'] = ref
        out['referenceVsBefore'] = {
            'wallEdgeEnergy': round(before['wall']['edgeEnergy'] / ref['wall']['edgeEnergy'], 4),
            'pavingEdgeEnergy': round(before['paving']['edgeEnergy'] / ref['paving']['edgeEnergy'], 4),
            'acU': round(before['wallRepeat']['acU'] / ref['wallRepeat']['acU'], 4)}
    Path(a.out).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('verdict', 'failures', 'repeatRatioAfterOverBefore',
                                           'detailNormalizedByPavingControl')}, indent=1))
    print('tile period px', period, 'acU before/after', before['wallRepeat']['acU'], after['wallRepeat']['acU'])


if __name__ == '__main__':
    main()
