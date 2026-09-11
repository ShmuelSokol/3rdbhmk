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
      --sampling implicit --label cp13t [--reference cp11c-02.png] [--visual V.json]

ACCEPTANCE V2 (2026-09-11, coordinator decision on Scripts/prove_combu_floor.py; fixed BEFORE any layout-break
frame existed). The v1 raw-combU bar was unpassable by the ideal answer: with two 300 cm periods in view,
combU = (1 + rho) / 2 exactly, so a wall with no repeat scores x0.87 and x0.75 needs the second period to be the
INVERSE of the first. v2 needs ALL of:
  1. JOINT REPEAT (primary) after/before <= 0.75. Dark thin VERTICAL lines (the rising joints and the drafted-margin
     shadow lines that travel with them): d = max(box_x21(L) - L, 0), box_y41(d), per-row mean removed. For each
     196-row band, the normalized row autocorrelation's maximum within +-40 px of THAT band's tile period, the
     period read off the CONTROL frame (argmax of the band's high-passed luma autocorrelation over 300-1900 px:
     the camera's 5 deg pitch makes it run 1307 -> 1416 px down the wall, so one fixed lag misses thin lines).
     Mean over bands. Control 0.480, attempt 3 0.448 (x0.93).
  2. RHO RATIO (combU - 0.5) after/before <= 0.75 (replaces raw combU; attempt 3 is -0.05).
  3. acU after/before <= 0.75, unchanged.
  4. DETAIL >= 0.85 of the paving-normalised gradient energy (edge, smoothed edge, vertical smoothed).
  plus a --visual JSON, written by the person who looked at the 1:1 crops, with every VISUAL_CHECKS key true.
  Numbers pass without --visual -> verdict PENDING_VISUAL, never PASS.
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
# v1 above is kept for the record (it is reported as verdictV1Superseded); v2 decides the verdict.
ACCEPTANCE_V2 = {
    'version': 'v2-2026-09-11',
    'jointRepeatRatioMax': 0.75, 'rhoRatioMax': 0.75, 'acURatioMax': 0.75, 'detailNormalizedRatioMin': 0.85,
    'detailKeys': ['edgeEnergy', 'edgeEnergySmoothed', 'verticalEnergySmoothed'],
    'jointMap': 'd = max(box_x21(L) - L, 0); box_y41(d); per-row mean removed',
    'jointBandRows': 196, 'jointLagWindowPx': 40,
    'jointBandPeriodSource': 'CONTROL frame: per band argmax of highpass(luma) row autocorrelation over lags 300-1900',
    'rhoRatio': '(combU_after - 0.5) / (combU_before - 0.5); combU = (1 + rho)/2 exactly with 2 periods in view',
    'visualChecks': ['bossRaisedAt1to1', 'noStoneCutAtTileEdge', 'noSliverStones', 'noMidBlockSeam',
                     'noDashedBedJoint', 'noFalseRidge'],
    'decidedBy': 'coordinator, 2026-09-11, on SourceAssets/material-review/AntiRepeatV1/combu-floor-proof-20260911T032018Z.json',
}
JOINT_BAND = ACCEPTANCE_V2['jointBandRows']
JOINT_WINDOW = ACCEPTANCE_V2['jointLagWindowPx']


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


def _box_x(a, k):
    pad = k // 2
    p = np.pad(a, ((0, 0), (pad, pad)), mode='edge')
    c = np.pad(np.cumsum(p, axis=1, dtype=np.float64), ((0, 0), (1, 0)))
    return ((c[:, k:k + a.shape[1]] - c[:, :a.shape[1]]) / k).astype(np.float32)


def joint_map(lum):
    """Dark thin vertical lines: rising joints and the margin shadow lines that travel with them."""
    lum = lum.astype(np.float32)
    d = np.maximum(_box_x(lum, 21) - lum, 0)
    d = _box_x(d.T, 41).T
    return d - d.mean(axis=1, keepdims=True)


def band_periods(wall):
    """Per 196-row band tile period in px, read off the CONTROL frame (perspective moves it down the wall)."""
    hp = highpass(wall)
    out = []
    for y0 in range(0, hp.shape[0] - JOINT_BAND + 1, JOINT_BAND):
        ac = row_acf(hp[y0:y0 + JOINT_BAND])
        out.append(int(300 + np.argmax(ac[300:1900])))
    return out


def joint_repeat(wall, periods):
    j = joint_map(wall)
    peaks, lags = [], []
    for i, y0 in enumerate(range(0, j.shape[0] - JOINT_BAND + 1, JOINT_BAND)):
        ac = row_acf(j[y0:y0 + JOINT_BAND].astype(np.float64))
        lo = periods[i] - JOINT_WINDOW
        k = int(np.argmax(ac[lo:periods[i] + JOINT_WINDOW + 1]))
        peaks.append(float(ac[lo + k]))
        lags.append(lo + k)
    return {'value': float(np.mean(peaks)), 'bandPeaks': [round(p, 4) for p in peaks], 'bandPeakLags': lags,
            'bandPeriodsFromControl': periods}


def frame(path, period=None, bands=None):
    lum, _ = luma(path)
    if lum.shape != (2160, 3840):
        raise SystemExit('%s is %s, expected 3840x2160 from capture_frame_ashlar.ps1' % (path, lum.shape))
    wall, pav = crop(lum, WALL), crop(lum, PAVING)
    row = {'file': str(path), 'sha256': sha(path), 'wall': detail(wall), 'paving': detail(pav)}
    if period is None:
        period, _ = tile_period(highpass(wall))
    if bands is None:
        bands = band_periods(wall)
    row['tilePeriodPx'] = period
    row['wallRepeat'] = repeat(wall, period)
    row['jointRepeat'] = joint_repeat(wall, bands)
    return row, period, bands


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--before', required=True)
    ap.add_argument('--after', required=True)
    ap.add_argument('--reference', help='an older control frame of the same camera, reported only')
    ap.add_argument('--out', required=True)
    ap.add_argument('--sampling', required=True)
    ap.add_argument('--label', required=True)
    ap.add_argument('--visual', help='JSON written after looking at the 1:1 crops: every ACCEPTANCE_V2 visualChecks key true')
    a = ap.parse_args()
    A = ACCEPTANCE_V2

    before, period, bands = frame(a.before)
    after, _, _ = frame(a.after, period, bands)
    ratios, norm = {}, {}
    for k in ('edgeEnergy', 'edgeEnergySmoothed', 'verticalEnergySmoothed', 'fineStd'):
        w = after['wall'][k] / before['wall'][k]
        p = after['paving'][k] / before['paving'][k]
        ratios[k] = {'wall': round(w, 4), 'paving': round(p, 4)}
        norm[k] = round(w / p, 4)
    rep = {k: round(after['wallRepeat'][k] / before['wallRepeat'][k], 4) for k in ('acU', 'combU')}
    cb, ca = before['wallRepeat']['combU'], after['wallRepeat']['combU']
    joint = round(after['jointRepeat']['value'] / before['jointRepeat']['value'], 4)
    rho = round((ca - 0.5) / (cb - 0.5), 4)
    criteria = {
        'jointRepeat': {'ratio': joint, 'max': A['jointRepeatRatioMax'], 'pass': joint <= A['jointRepeatRatioMax']},
        'rhoRatio': {'ratio': rho, 'max': A['rhoRatioMax'], 'pass': rho <= A['rhoRatioMax']},
        'acU': {'ratio': rep['acU'], 'max': A['acURatioMax'], 'pass': rep['acU'] <= A['acURatioMax'],
                'marginToBar': round(A['acURatioMax'] - rep['acU'], 4)},
        'detail': {'normalized': {k: norm[k] for k in A['detailKeys']}, 'min': A['detailNormalizedRatioMin'],
                   'pass': all(norm[k] >= A['detailNormalizedRatioMin'] for k in A['detailKeys'])}}
    numeric_ok = all(c['pass'] for c in criteria.values())
    visual = None
    if a.visual:
        vj = json.loads(Path(a.visual).read_text(encoding='utf-8-sig'))
        checks = vj.get('checks', {})
        visual = {'file': a.visual, 'sha256': sha(a.visual), 'checks': checks, 'by': vj.get('by'), 'crops': vj.get('crops'),
                  'pass': all(checks.get(k) is True for k in A['visualChecks'])}
    failures = ['%s x%s (bar %s)' % (k, c.get('ratio', c.get('normalized')), c.get('max', c.get('min')))
                for k, c in criteria.items() if not c['pass']]
    if visual is not None and not visual['pass']:
        failures.append('VISUAL: %s' % {k: visual['checks'].get(k) for k in A['visualChecks']})
    if not numeric_ok or (visual is not None and not visual['pass']):
        verdict = 'FAIL'
    elif visual is None:
        verdict = 'PENDING_VISUAL'
    else:
        verdict = 'PASS'
    v1_ok = (rep['acU'] <= THRESHOLDS['repeatAcURatioMax'] and rep['combU'] <= THRESHOLDS['repeatCombURatioMax']
             and all(norm[k] >= THRESHOLDS['detailNormalizedRatioMin'] for k in A['detailKeys']))
    out = {'label': a.label, 'samplingMode': a.sampling,
           'utc': datetime.now(timezone.utc).isoformat(), 'script': 'Scripts/measure_antirepeat_frame.py',
           'scriptSha256': sha(__file__), 'regions': {'wall': WALL, 'paving': PAVING},
           'acceptanceVersion': A['version'], 'acceptance': A, 'criteria': criteria, 'visual': visual,
           'before': before, 'after': after,
           'repeatRatioAfterOverBefore': rep, 'detailRatioAfterOverBefore': ratios,
           'detailNormalizedByPavingControl': norm,
           'verdict': verdict, 'failures': failures,
           'thresholdsV1Superseded': THRESHOLDS, 'verdictV1Superseded': 'PASS' if v1_ok else 'FAIL'}
    if a.reference:
        ref, _, _ = frame(a.reference, period, bands)
        out['reference'] = ref
        out['referenceVsBefore'] = {
            'wallEdgeEnergy': round(before['wall']['edgeEnergy'] / ref['wall']['edgeEnergy'], 4),
            'pavingEdgeEnergy': round(before['paving']['edgeEnergy'] / ref['paving']['edgeEnergy'], 4),
            'acU': round(before['wallRepeat']['acU'] / ref['wallRepeat']['acU'], 4)}
    Path(a.out).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('verdict', 'failures', 'criteria')}, indent=1))
    print('tile period px', period, 'joint repeat before/after', before['jointRepeat']['value'], after['jointRepeat']['value'])


if __name__ == '__main__':
    main()
