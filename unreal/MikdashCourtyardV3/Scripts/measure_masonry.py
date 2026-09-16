"""One masonry measurement pipeline, run identically on the Western Wall photo and on any render.

Every number the walls07 pass is judged by lives here, so the photo and the build are never measured by
different code. Everything is scale-invariant (ratios and logs of luminance), so the renderer's exposure
cannot move a single metric.

WHY SOME BARS ARE NOT THE OBVIOUS ONES (see the memory note acceptance-bar-must-pass-the-ideal):

  * STONE-TONE SPREAD IS DETRENDED. The rectified 60 m frame is a 70 m tall strip whose far end is 95 m
    from the camera, so aerial perspective lays a smooth gradient over it; the photo is a 7 m band with
    almost none. Raw stdLog on the frame is 0.107 against the photo's 0.084 largely because of that
    gradient, not because the stones differ. Both are therefore divided by a local 6 m field before the
    spread is taken, and both raw and detrended values are reported.
  * LUMINANCE IS NOT A BAR. The game runs auto-exposure (MikdashTimeOfDay sets AutoExposureBias with
    Min/Max EV100 0..14) and the wall fills the P3 frame, so the face's absolute luminance is pinned near
    the adaptation target whatever albedo is authored. Reaching the photo's luminance by albedo alone
    needs a ~1.9x multiplier - far albedo R ~ 0.99 - which is unphysical and clips the tone encoding.
    The ideal answer cannot pass an absolute-luminance bar, so the bar is on HUE (chromaticity ratios)
    and the luminance is reported as exposure-set.

  python Scripts/measure_masonry.py            # runs the photo, its halves, and prints the bars
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path('C:/Mikdash/Working-5.8/MikdashCourtyardV3')
KOTEL = ROOT / 'SourceAssets/kotel-detail/PhotoSurfaceV1/kotel-wall-cleaned.png'
PHOTO_PX_PER_M = 62.857142857142854          # accept_precinct_cp20.kotel_reference, Herodian course ~1.05 m
PHOTO_BAND = (120, 715)                      # the Herodian courses; late small courses above excluded


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def smooth1(x, n):
    x = np.where(np.isfinite(x), x, np.nanmean(x))
    return np.convolve(np.pad(x, n, mode='edge'), np.ones(2 * n + 1) / (2 * n + 1), mode='valid')


def blur_nan(a, sigma_px):
    """Gaussian blur that ignores NaNs (normalised by the blurred validity mask)."""
    m = np.isfinite(a).astype(np.float32)
    v = np.where(np.isfinite(a), a, 0.0).astype(np.float32)
    n = int(max(3, round(sigma_px * 3)))
    k = np.exp(-0.5 * (np.arange(-n, n + 1) / sigma_px) ** 2).astype(np.float32)
    k /= k.sum()

    def sep(x):
        x = np.apply_along_axis(lambda r: np.convolve(np.pad(r, n, mode='edge'), k, mode='valid'), 1, x)
        return np.apply_along_axis(lambda r: np.convolve(np.pad(r, n, mode='edge'), k, mode='valid'), 0, x)
    num, den = sep(v), sep(m)
    return np.where(den > 1e-3, num / np.maximum(den, 1e-6), np.nan)


# ------------------------------------------------------------------ segmentation
def detect_blocks(lum, cmpp, strip_cm=640.0, min_course_cm=64.0, max_course_cm=190.0,
                  min_joint_cm=56.0, course_win_cm=40.0, inset_cm=14.0):
    """Beds from row-profile minima per strip, vertical joints from column minima inside each course.

    The Western Wall photo's own detector (accept_precinct_cp20.kotel_reference), rewritten in centimetres
    so the identical algorithm runs on a render at any scale.
    """
    H, W = lum.shape
    strip = max(8, int(round(strip_cm / cmpp)))
    win = max(3, int(round(course_win_cm / cmpp)))
    minc = max(3, int(round(min_course_cm / cmpp)))
    minj = max(3, int(round(min_joint_cm / cmpp)))
    ins = max(1, int(round(inset_cm / cmpp)))
    ten = max(1, int(round(10.0 / cmpp)))
    blocks = []
    for sx in range(0, max(1, W - strip + 1), strip):
        col = lum[:, sx:sx + strip]
        ps = smooth1(np.nanmean(col, axis=1), 2)
        mins = []
        for i in range(3, len(ps) - 3):
            if ps[i] == ps[max(0, i - win):i + win + 1].min() and (not mins or i - mins[-1] > minc):
                mins.append(i)
        for a, b in zip(mins, mins[1:]):
            h_cm = (b - a) * cmpp
            if not (min_course_cm <= h_cm <= max_course_cm):
                continue
            cp = smooth1(np.nanmean(lum[a + ten:b - ten, sx:sx + strip], axis=0), 2)
            med = np.nanmedian(cp)
            vj = [0]
            for i in range(5, len(cp) - 5):
                if cp[i] == cp[max(0, i - minj):i + minj + 1].min() and cp[i] < med * 0.93 and i - vj[-1] > minj:
                    vj.append(i)
            vj.append(strip)
            for c0, c1 in zip(vj, vj[1:]):
                if (c1 - c0) * cmpp < 55.0:
                    continue
                r0, r1 = a + ins, b - ins
                q0, q1 = sx + c0 + ins, sx + c1 - ins
                if r1 - r0 < 3 or q1 - q0 < 3 or q1 > W:
                    continue
                blk = lum[r0:r1, q0:q1]
                if np.isnan(blk).mean() > 0.25:
                    continue
                blocks.append({'course': a, 'x_cm': (sx + (c0 + c1) / 2.0) * cmpp, 'z_cm': (a + b) / 2.0 * cmpp,
                               'blk': blk, 'box': (a, b, sx + c0, sx + c1)})
    return blocks


# ------------------------------------------------------------------ metrics
def course_heights(lum, cmpp, strip_cm=200.0):
    """accept_precinct_cp25.beds_detect, kept identical so cp26's numbers stay comparable."""
    sp = max(8, int(round(strip_cm / cmpp)))
    half = int(round(37.0 / cmpp))
    wide = int(round(125.0 / cmpp))
    hs = []
    vz = np.where(np.isfinite(lum), lum, np.nanmean(lum))
    for x0 in range(0, vz.shape[1] - sp + 1, sp):
        pr = np.convolve(vz[:, x0:x0 + sp].mean(axis=1), np.ones(3) / 3, mode='same')
        mins = [i for i in range(half + 1, len(pr) - half - 1)
                if pr[i] == pr[i - half:i + half + 1].min() and pr[i] < 0.97 * np.median(pr[max(0, i - wide):i + wide])]
        hs += list(np.diff(mins) * cmpp)
    hs = np.array(hs, dtype=float)
    if len(hs) < 4:
        return {'n': int(len(hs))}
    med = float(np.median(hs))
    core = hs[(hs > 0.6 * med) & (hs < 1.6 * med)]
    return {'n': int(len(hs)), 'medianCm': round(med, 1), 'cv': round(float(core.std() / med), 3),
            'fracOver1p5xMedian': round(float((hs > 1.5 * med).mean()), 3),
            'p95OverMedian': round(float(np.percentile(hs, 95) / med), 2)}


def bed_joint_dip(lum, cmpp, course_cm=105.0, strip_cm=200.0):
    """accept_precinct_cp20.strip_dip in centimetres: 1 - min/median over each course window, per 2 m strip."""
    vz = np.where(np.isfinite(lum), lum, np.nanmean(lum))
    lagp = max(4, int(round(course_cm / cmpp)))
    strip_px = max(4, int(round(strip_cm / cmpp)))
    dips = []
    for x0 in range(0, max(1, vz.shape[1] - strip_px), strip_px):
        pr = vz[:, x0:x0 + strip_px].mean(axis=1)
        sm = np.convolve(pr, np.ones(3) / 3, mode='same')
        for c0 in range(0, len(pr) - lagp, lagp):
            seg = sm[c0:c0 + lagp]
            dips.append(1 - float(seg.min() / np.median(seg)))
    return round(float(np.median(dips)), 4)


def stone_spread(lum, cmpp, blocks, detrend_cm=600.0):
    """Stone-to-stone tone spread, raw and detrended by a local 6 m field, plus neighbour contrast."""
    if len(blocks) < 20:
        return {'nStones': len(blocks)}
    field = blur_nan(lum, max(2.0, detrend_cm / cmpp))
    raw, det, intra = [], [], []
    for b in blocks:
        m = float(np.nanmean(b['blk']))
        if not np.isfinite(m) or m <= 1e-3:
            continue
        a, bb, c0, c1 = b['box']
        loc = float(np.nanmean(field[a:bb, c0:c1]))
        if not np.isfinite(loc) or loc <= 1e-3:
            continue
        b['mean'] = m
        b['det'] = m / loc
        raw.append(m)
        det.append(m / loc)
        intra.append(float(np.nanstd(np.log(np.clip(b['blk'] / m, 0.05, 20.0)))))
    lr, ld = np.log(raw), np.log(det)
    byc = {}
    for b in blocks:
        if 'det' in b:
            byc.setdefault(b['course'], []).append(b)
    nb = []
    for ss in byc.values():
        ss.sort(key=lambda s: s['x_cm'])
        nb += [abs(math.log(q['det']) - math.log(p['det'])) for p, q in zip(ss, ss[1:]) if q['x_cm'] - p['x_cm'] < 400.0]
    return {'nStones': len(lr), 'stdLogRaw': round(float(lr.std()), 4), 'stdLog': round(float(ld.std()), 4),
            'p05p95Ratio': round(float(np.exp(np.percentile(ld, 95) - np.percentile(ld, 5))), 3),
            'medianNeighbourAbsLog': round(float(np.median(nb)), 4) if nb else None,
            'intraStoneLogStd': round(float(np.median(intra)), 4)}


def margin_profile(lum, cmpp, blocks, reach_cm=30.0):
    """Is a drafted margin visible? Mean inward luminance profile from each stone edge, over all stones.

    A drafted margin is a flat recessed band 5-15 cm wide around a raised boss, so the profile has a STEP
    at the boss edge. 'marginStep' is the largest step in 4-16 cm; 'interiorStep' is the same statistic in
    19-27 cm, i.e. the noise floor of a face with no margin. Visible means marginStep clearly over it.
    """
    nb = int(round(reach_cm / cmpp))
    if nb < 6 or len(blocks) < 20:
        return {'nStones': len(blocks)}
    acc = np.zeros(nb)
    cnt = np.zeros(nb)
    for b in blocks:
        blk = b['blk']
        m = float(np.nanmean(blk))
        if not np.isfinite(m) or m <= 1e-3 or blk.shape[0] < 2 * nb or blk.shape[1] < 2 * nb:
            continue
        h, w = blk.shape
        r0, r1 = int(h * 0.2), int(h * 0.8)
        c0, c1 = int(w * 0.2), int(w * 0.8)
        for prof in (np.nanmean(blk[r0:r1, :nb], axis=0), np.nanmean(blk[r0:r1, w - nb:][:, ::-1], axis=0),
                     np.nanmean(blk[:nb, c0:c1], axis=1), np.nanmean(blk[h - nb:, c0:c1][::-1], axis=1)):
            p = prof / m
            ok = np.isfinite(p)
            acc[ok] += p[ok]
            cnt[ok] += 1
    prof = acc / np.maximum(cnt, 1)
    d_cm = (np.arange(nb) + 0.5) * cmpp

    def step_in(lo, hi):
        best = (0.0, None)
        for i in range(nb):
            if not (lo <= d_cm[i] <= hi):
                continue
            a0 = [j for j in range(nb) if d_cm[i] - 4.5 <= d_cm[j] < d_cm[i] - 0.5]
            a1 = [j for j in range(nb) if d_cm[i] + 0.5 < d_cm[j] <= d_cm[i] + 4.5]
            if len(a0) < 1 or len(a1) < 1:
                continue
            s = abs(float(np.mean(prof[a1]) - np.mean(prof[a0])))
            if s > best[0]:
                best = (s, round(float(d_cm[i]), 1))
        return best
    ms, mpos = step_in(4.0, 16.0)
    ints, ipos = step_in(19.0, 27.0)
    return {'nStones': int(cnt.max()) if cnt.max() else 0, 'marginStep': round(ms, 4), 'marginAtCm': mpos,
            'interiorStep': round(ints, 4), 'interiorAtCm': ipos,
            'ratio': round(ms / ints, 2) if ints > 1e-6 else None,
            'profile': [round(float(x), 4) for x in prof]}


def blotch_repeat(lum, cmpp, band=(50.0, 300.0), min_lag_cm=300.0, max_lag_cm=4000.0):
    """Does the weathering repeat on a lattice? Peak 2-D autocorrelation of the blotch band outside lag 0."""
    v = np.where(np.isfinite(lum), lum, np.nanmean(lum)).astype(np.float32)
    bp = blur_nan(v, band[0] / cmpp) - blur_nan(v, band[1] / cmpp)
    bp = np.nan_to_num(bp - np.nanmean(bp))
    H, W = bp.shape
    F = np.fft.rfft2(bp)
    ac = np.fft.irfft2(F * np.conj(F), s=(H, W)).real
    ac /= max(ac[0, 0], 1e-12)
    ly = int(min(H // 2 - 1, max_lag_cm / cmpp))
    lx = int(min(W // 2 - 1, max_lag_cm / cmpp))
    mlag = min_lag_cm / cmpp
    best = (0.0, None)
    for dy in range(0, ly + 1):
        for dx in range(0, lx + 1):
            if math.hypot(dx, dy) < mlag:
                continue
            for sy in ((dy,) if dy == 0 else (dy, H - dy)):
                val = float(ac[sy, dx])
                if val > best[0]:
                    best = (val, (round(dx * cmpp / 100.0, 1), round(dy * cmpp / 100.0, 1)))
    return {'peak': round(best[0], 4), 'atLagM': best[1]}


def colour(rgb):
    m = np.nanmean(rgb.reshape(-1, 3), axis=0)
    lin = np.nanmean((np.clip(rgb, 0, 1) ** 2.2).reshape(-1, 3), axis=0)
    return {'meanSRGB': [round(float(x), 4) for x in m],
            'lum': round(float(0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2]), 4),
            'srgbGoverR': round(float(m[1] / m[0]), 4), 'srgbBoverR': round(float(m[2] / m[0]), 4),
            'linGoverR': round(float(lin[1] / lin[0]), 4), 'linBoverR': round(float(lin[2] / lin[0]), 4)}


def measure(rgb, cmpp, name, do_blotch=True):
    lum = luma(rgb) if rgb.ndim == 3 else rgb
    blocks = detect_blocks(lum, cmpp)
    out = {'name': name, 'cmPerPx': round(cmpp, 3), 'courses': course_heights(lum, cmpp),
           'bedJointDip': bed_joint_dip(lum, cmpp), 'stones': stone_spread(lum, cmpp, blocks),
           'margins': margin_profile(lum, cmpp, blocks)}
    if do_blotch:
        out['blotchRepeat'] = blotch_repeat(lum, cmpp)
    if rgb.ndim == 3:
        out['colour'] = colour(rgb)
    return out


def photo(cmpp=None, crop=None):
    """The Western Wall photo, optionally resampled to a target cm/px and cropped (for the halves check)."""
    im = Image.open(KOTEL).convert('RGB')
    a = np.asarray(im, dtype=np.float32) / 255.0
    a = a[PHOTO_BAND[0]:PHOTO_BAND[1]]
    native = 100.0 / PHOTO_PX_PER_M
    if cmpp and abs(cmpp - native) > 1e-6:
        s = native / cmpp
        im2 = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize(
            (max(1, int(a.shape[1] * s)), max(1, int(a.shape[0] * s))), Image.BOX)
        a = np.asarray(im2, dtype=np.float32) / 255.0
    else:
        cmpp = native
    if crop == 'left':
        a = a[:, :a.shape[1] // 2]
    elif crop == 'right':
        a = a[:, a.shape[1] // 2:]
    return a, cmpp


def main():
    out = {'photoNativeCmPerPx': round(100.0 / PHOTO_PX_PER_M, 3), 'runs': []}
    for cmpp in (None, 1.76, 3.14):
        for crop in (None, 'left', 'right'):
            a, c = photo(cmpp, crop)
            nm = 'photo@%.2f%s' % (c, '' if crop is None else '-' + crop)
            out['runs'].append(measure(a, c, nm))
    for r in out['runs']:
        r.pop('marginsProfile', None)
        r['margins'] = {k: v for k, v in r['margins'].items() if k != 'profile'}
    print(json.dumps(out, indent=1))
    (ROOT / 'SourceAssets/enclosure-review/PrecinctMacroV1/measure-masonry-photo.json').write_text(
        json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    sys.exit(main())
