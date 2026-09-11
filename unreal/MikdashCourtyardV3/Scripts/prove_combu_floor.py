"""Anti-repeat attempt 4, evaluated BEFORE building: can ANY layout break pass combU <= x0.75?

Shmuel, verbatim: "I don't wanna see, like, repeating patterns all over."

Reads only the rendered attempt-3 frames (arv3c before/after, camera 02) with measure_antirepeat_frame.py's
own functions, so lighting, perspective and joint sharpening are real, not modelled.

What it proves:
  1. IDENTITY. The wall is 3840 px and the tile period 1322 px, so comb_u's FFT is 2 x 1322 px long and the
     comb is every EVEN bin. Even bins carry |a+b|^2 and odd bins |a-b|^2 for the two 300 cm halves a, b,
     so combU = (1 + rho) / 2 EXACTLY, rho = the power-weighted correlation of the two halves (per-row mean
     removed). A wall whose halves are unrelated sits at 0.500; white noise gives 0.500.
  2. THE BAR. x0.75 of the control (0.577) is 0.433, i.e. rho(300 cm) <= -0.134: the halves must be
     ANTI-correlated. No non-repeating wall does that. Only a deliberately complementary tile pair would,
     which is itself a 600 cm pattern.
  3. SURROGATES from rendered pixels: a 600 cm period, a layout with no repeat in frame, attempt-3 pixels
     with different head joints per tile, and different head joints per course band. None passes combU.
  4. acU: after attempt 3 it is almost all per-row-mean power (bed joints and course-wide tone, which every
     coursed wall keeps); with the row mean removed it is -0.008.

  python Scripts/prove_combu_floor.py [--out <json>]
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import measure_antirepeat_frame as m  # noqa: E402

ROOT = HERE.parent
VR = ROOT / 'SourceAssets' / 'visual-review'
FRAME = 'arv3c-%s-02-herodian-ashlar-inner-east-gate-jamb-walkingheight.png'
P = 1322


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def wall_lum(n):
    lum, _ = m.luma(VR / (FRAME % n))
    return m.crop(lum, m.WALL)


def rho_halves(c):
    mu = c[:, :2 * P].mean(axis=1, keepdims=True)
    a, b = c[:, :P] - mu, c[:, P:2 * P] - mu
    return float(2 * (a * b).sum() / ((a * a).sum() + (b * b).sum()))


def acu(c):
    return float(m.row_acf(c)[P])


def headjoint_map(lum):
    """Rising-joint evidence: |d/dx| of a 3-px blur, high-passed, per-row mean removed (bed joints run the
    whole course in real masonry, so they are not a repeat)."""
    s = m.box(lum, 3)
    gx = np.abs(np.gradient(s, axis=1))
    g = gx - m.box(gx, 151)
    return g - g.mean(axis=1, keepdims=True)


def stats(v):
    v = np.asarray(v)
    return {'n': int(v.size), 'min': round(float(v.min()), 4), 'p10': round(float(np.percentile(v, 10)), 4),
            'median': round(float(np.median(v)), 4), 'p90': round(float(np.percentile(v, 90)), 4),
            'max': round(float(v.max()), 4), 'fracAtOrBelow0_75': round(float((v <= 0.75).mean()), 4)}


def main():
    ap = argparse.ArgumentParser()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    ap.add_argument('--out', default=str(ROOT / 'SourceAssets' / 'material-review' / 'AntiRepeatV1' /
                                         ('combu-floor-proof-%s.json' % stamp)))
    a = ap.parse_args()
    lum = {n: wall_lum(n) for n in ('before', 'after')}
    hp = {n: m.highpass(l) for n, l in lum.items()}
    cb, ab = m.comb_u(hp['before'], P), acu(hp['before'])
    out = {'script': 'Scripts/prove_combu_floor.py', 'scriptSha256': sha(__file__),
           'metricScriptSha256': sha(m.__file__), 'utc': datetime.now(timezone.utc).isoformat(),
           'frames': {n: {'file': 'SourceAssets/visual-review/' + FRAME % n, 'sha256': sha(VR / (FRAME % n))}
                      for n in ('before', 'after')},
           'tilePeriodPx': P, 'wallWidthPx': int(hp['before'].shape[1]), 'combWindowPx': 2 * P,
           'identity': {}, 'surrogates': {}}
    for n, c in hp.items():
        r = rho_halves(c)
        rm = c.mean(axis=1, keepdims=True)
        out['identity'][n] = {'combU': round(m.comb_u(c, P), 5), 'onePlusRhoOver2': round((1 + r) / 2, 5),
                              'rhoHalves300cm': round(r, 5), 'acU': round(acu(c), 5),
                              'rowMeanPowerFraction': round(float((rm ** 2).mean() / (c ** 2).mean()), 5),
                              'acURowMeanRemoved': round(acu(c - rm), 5),
                              'headJointAcf300cm': round(float(m.row_acf(headjoint_map(lum[n]))[P]), 5)}
    noise = m.highpass(np.random.default_rng(1).standard_normal(hp['before'].shape) * 20)
    out['identity']['whiteNoiseCombU'] = round(m.comb_u(noise, P), 5)
    out['bar'] = {'combUMax': round(0.75 * cb, 5), 'equivalentRho300cmMax': round(2 * 0.75 * cb - 1, 5),
                  'noRepeatFloorCombU': 0.5, 'noRepeatFloorRatio': round(0.5 / cb, 4)}

    b, af = hp['before'], hp['after']
    tile = b[:, :P]
    c600, a600 = [], []
    for s in range(60, P - 59, 20):
        w = np.concatenate([tile, np.roll(tile, -s, axis=1)] * 2, axis=1)[:, :3840]
        c600.append(m.comb_u(w, P) / cb)
        a600.append(acu(w) / ab)
    out['surrogates']['period600cm_controlPixels'] = {'combURatio': stats(c600), 'acURatio': stats(a600)}
    cn, an = [], []
    for s1 in range(100, P, 150):
        for s2 in range(175, P, 150):
            w = np.concatenate([tile, np.roll(tile, -s1, axis=1), np.roll(tile, -s2, axis=1)], axis=1)[:, :3840]
            cn.append(m.comb_u(w, P) / cb)
            an.append(acu(w) / ab)
    out['surrogates']['noRepeatInFrame_controlPixels'] = {'combURatio': stats(cn), 'acURatio': stats(an)}
    A, B, C = af[:, :P], af[:, P:2 * P], af[:, 3840 - P:]
    hj = headjoint_map(lum['after'])
    hA, hB, hC = hj[:, :P], hj[:, P:2 * P], hj[:, 3840 - P:]
    cv, av, hv = [], [], []
    for s1 in range(80, P - 79, 60):
        for s2 in range(130, P - 129, 60):
            w = np.concatenate([A, np.roll(B, -s1, axis=1), np.roll(C, -s2, axis=1)], axis=1)[:, :3840]
            cv.append(m.comb_u(w, P) / cb)
            av.append(acu(w) / ab)
            h = np.concatenate([hA, np.roll(hB, -s1, axis=1), np.roll(hC, -s2, axis=1)], axis=1)[:, :3840]
            hv.append(float(m.row_acf(h)[P]))
    out['surrogates']['attempt3PixelsNewHeadJointsPerTile'] = {
        'combURatio': stats(cv), 'acURatio': stats(av), 'headJointAcf300cm': stats(hv),
        'models': 'the 600 x 300 cm proposal and any per-cell layout choice: per-stone variants ON, bed joints kept, head joints differ'}
    rng = np.random.default_rng(7)
    cc, ac_ = [], []
    for _ in range(60):
        segs = [A]
        for T in (B, C):
            T2 = T.copy()
            for y0 in range(0, T.shape[0], 441):
                T2[y0:y0 + 441] = np.roll(T[y0:y0 + 441], -int(rng.integers(80, P - 80)), axis=1)
            segs.append(T2)
        w = np.concatenate(segs, axis=1)[:, :3840]
        cc.append(m.comb_u(w, P) / cb)
        ac_.append(acu(w) / ab)
    out['surrogates']['attempt3PixelsNewHeadJointsPerCourseBand'] = {'combURatio': stats(cc), 'acURatio': stats(ac_)}
    passes = any(v['combURatio']['fracAtOrBelow0_75'] > 0 for v in out['surrogates'].values())
    out['verdict'] = ('SOME_LAYOUT_BREAK_CAN_PASS' if passes else
                      'NO_LAYOUT_BREAK_CAN_PASS_COMBU: the x0.75 combU bar needs anti-correlated 300 cm halves; '
                      'every non-repeating surrogate sits at x0.81-0.93. Not built; the bar needs a decision from Shmuel.')
    Path(a.out).write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: out[k] for k in ('identity', 'bar', 'verdict')}, indent=1))
    for k, v in out['surrogates'].items():
        print(k, 'combU', v['combURatio'], 'acU', v['acURatio'])
    print('wrote', a.out)


if __name__ == '__main__':
    main()
