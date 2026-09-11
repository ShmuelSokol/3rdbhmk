"""cp20 acceptance numbers from packaged-build frames (run after capture_frame_precinct_macro.ps1 -Label cp20).

The question cp20 answers: do the retaining faces read as Herodian ashlar of ONE quarry at 60-70 m, judged against
the Western Wall photo (SourceAssets/kotel-detail/PhotoSurfaceV1/kotel-wall-cleaned.png), without bringing the 3 m
wallpaper back and without touching the close range.

  1. per-stone tone on the rectified 60 m face (P3): stone interiors sampled at the close-tile joints (layout phase
     fitted on cp19b, where all five vertical joints land within 1-3 cm; the same camera and world tiling for cp20),
     std of log(stone mean), p05-p95 ratio, median neighbour contrast; and the same numbers segmented off the
     Western Wall photo
  2. dark outline: bed-joint strip dip (1 - min/median over each 1 m course window, 2 m strips) at the P3 scale
     (3.14 cm/px), the Western Wall photo box-resampled to that scale
  3. repeat: the cp19 tile-lag autocorrelation on the P3 screen box (corrAtLag101 + peak lag), plus the
     rectified autocorrelation high-passed at 6 m, whose value at the 300 cm lag isolates the tile (cp16before 0.75)
  4. aerial: measure_precinct_face_profile.py cp16before cp19b cp20
  5. no-regression: mean |diff| of 02 (4 m jamb) vs cp19b and 07 (plaza stone at walking range) vs cp19b, against
     the cp17 -> cp17b 07 noise floor
  6. sheets: Western Wall | cp19b P3 | cp20 P3 at the same stone scale, and full-frame compares
  python Scripts/accept_precinct_cp20.py [label=cp20]
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path('C:/Mikdash/Working-5.8/MikdashCourtyardV3')
sys.path.insert(0, str(ROOT / 'Scripts'))
import measure_precinct_face_profile as M  # noqa: E402

V = ROOT / 'SourceAssets/visual-review'
OUT = ROOT / 'SourceAssets/enclosure-review/PrecinctMacroV1'
KOTEL = ROOT / 'SourceAssets/kotel-detail/PhotoSurfaceV1/kotel-wall-cleaned.png'
LABEL = sys.argv[1] if len(sys.argv) > 1 else 'cp20'
RUNS = ['cp16before', 'cp19b', LABEL]
LAY = json.loads((OUT / 'manifest-V2.json').read_text())['layoutFromCloseTile']
BEDS, JOINTS = LAY['bedsCm'], LAY['jointsCmPerCourse']
P3_PHASE = (-67.0, 2.0)       # fitted on cp19b P3 (dz, dy): joints verified within 1-3 cm
STEP = 3.0


def L(path):
    a = np.asarray(Image.open(path).convert('RGB'), dtype=np.float32) / 255.0
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def rectify(view, label, plane, fixed, a0, a1, z0=-150.0, z1=-7000.0):
    img = L(V / ('%s-%s.png' % (label, M.VIEWS[view][0])))
    H, W = img.shape
    along = np.arange(a0, a1, STEP); zs = np.arange(z0, z1, -STEP)
    pts, shape = M.strip_points(plane, fixed, along, zs)
    px, py, df = M.project(pts, M.VIEWS[view][1], W, H)
    ok = (df > 0) & (px >= 1) & (px < W - 2) & (py >= 1) & (py < H - 2)
    v = np.where(ok, M.bilinear(img, np.clip(px, 0, W - 2), np.clip(py, 0, H - 2)), np.nan).reshape(shape)
    keep = np.isfinite(v).mean(axis=1) > 0.9
    return v[keep].astype(np.float32), along, zs[keep]


def stone_means(v, along, zs, dz, dy, inset=22.0):
    A = along - dy; Z = zs - dz
    out = []
    for ci in range(int(math.floor(Z.min() / 300)), int(math.floor(Z.max() / 300)) + 1):
        for k in range(3):
            zb, zt = ci * 300 + BEDS[k], ci * 300 + BEDS[k + 1]
            wb, wt = zb + dz, zt + dz
            if min(abs(wb - round(wb / 1200) * 1200), abs(wt - round(wt / 1200) * 1200)) < 60:
                continue                     # courses touching a batter ledge wash
            rows = (Z > zb + inset) & (Z < zt - inset)
            if rows.sum() < 3:
                continue
            js = JOINTS[k]
            for ti in range(int(math.floor(A.min() / 300)) - 1, int(math.floor(A.max() / 300)) + 1):
                xs = [ti * 300 + j for j in js] + [ti * 300 + js[0] + 300]
                for s in range(len(js)):
                    cols = (A > xs[s] + inset) & (A < xs[s + 1] - inset)
                    if cols.sum() < 3:
                        continue
                    blk = v[np.ix_(rows, cols)]
                    if np.isnan(blk).mean() > 0.05 or (blk < 0.12).mean() > 0.02:
                        continue
                    out.append((ci * 3 + k, 0.5 * (xs[s] + xs[s + 1]), float(np.nanmean(blk))))
    return out


def spread(stones):
    lg = np.log([s[2] for s in stones])
    byc = {}
    for s in stones:
        byc.setdefault(s[0], []).append(s)
    nb = []
    for ss in byc.values():
        ss.sort(key=lambda s: s[1])
        nb += [abs(math.log(q[2]) - math.log(p[2])) for p, q in zip(ss, ss[1:]) if q[1] - p[1] < 400]
    return {'nStones': len(lg), 'stdLog': round(float(lg.std()), 4),
            'p05p95Ratio': round(float(np.exp(np.percentile(lg, 95) - np.percentile(lg, 5))), 3),
            'medianNeighbourAbsLog': round(float(np.median(nb)), 4)}


def strip_dip(v, cm_per_px=STEP, course_cm=100.0, strip_px=67):
    vz = np.where(np.isfinite(v), v, np.nanmean(v))
    lagp = int(round(course_cm / cm_per_px))
    dips = []
    for x0 in range(0, vz.shape[1] - strip_px, strip_px):
        pr = vz[:, x0:x0 + strip_px].mean(axis=1)
        sm = np.convolve(pr, np.ones(3) / 3, mode='same')
        for c0 in range(0, len(pr) - lagp, lagp):
            seg = sm[c0:c0 + lagp]
            dips.append(1 - float(seg.min() / np.median(seg)))
    return round(float(np.median(dips)), 4)


def rect_acorr(v, lags, hp_cm=None):
    p = np.nan_to_num(v - np.nanmean(v, axis=1, keepdims=True))
    if hp_cm:
        n = int(hp_cm / STEP) | 1
        k = np.ones(n) / n
        p = p - np.apply_along_axis(lambda r: np.convolve(np.pad(r, n // 2, mode='edge'), k, mode='valid'), 1, p)
    den = float((p * p).sum())
    return {str(l): round(float((p[:, :-int(l / STEP)] * p[:, int(l / STEP):]).sum()) / den, 4) for l in lags}


def screen_acorr(l, box, maxlag=400):
    x0, y0, x1, y1 = box
    p = l[y0:y1, x0:x1]
    p = p - p.mean(axis=1, keepdims=True)
    den = float((p * p).sum())
    ac = np.array([float((p[:, :-k] * p[:, k:]).sum()) / den for k in range(1, maxlag)])
    k = int(np.argmax(ac[40:])) + 41
    return {'peakLagPx': k, 'peakCorr': round(float(ac[k - 1]), 4), 'corrAtLag101': round(float(ac[100]), 4),
            'std': round(float(l[y0:y1, x0:x1].std()), 4)}


def kotel_reference():
    """Western Wall photo: courses from the row profile, vertical joints from column minima, stone = interior median."""
    rgb = np.asarray(Image.open(KOTEL).convert('RGB'), dtype=np.float32) / 255
    lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    Lk = np.where((rgb[..., 1] > rgb[..., 0] * 0.98) | (lum < 0.10), np.nan, lum)   # plants and voids out
    H, W = lum.shape
    y0, y1 = 120, 715                                  # Herodian courses (late small courses above excluded)

    def smooth(x, n):
        x = np.where(np.isnan(x), np.nanmean(x), x)
        return np.convolve(np.pad(x, n, mode='edge'), np.ones(2 * n + 1) / (2 * n + 1), mode='valid')
    stones = []
    for sx in range(0, W - 400 + 1, 400):
        ps = smooth(np.nanmean(Lk[y0:y1, sx:sx + 400], axis=1), 2)
        mins = []
        for i in range(3, len(ps) - 3):
            if ps[i] == ps[max(0, i - 25):i + 26].min() and (not mins or i - mins[-1] > 40):
                mins.append(i)
        beds = [y0 + m for m in mins]
        for a, b in zip(beds, beds[1:]):
            if not 45 <= b - a <= 110:
                continue
            cp = smooth(np.nanmean(Lk[a + 10:b - 10, sx:sx + 400], axis=0), 2)
            vj = [0]
            for i in range(5, len(cp) - 5):
                if cp[i] == cp[max(0, i - 30):i + 31].min() and cp[i] < np.median(cp) * 0.93 and i - vj[-1] > 35:
                    vj.append(i)
            vj.append(400)
            for c0, c1 in zip(vj, vj[1:]):
                if c1 - c0 < 40:
                    continue
                blk = Lk[a + 10:b - 10, sx + c0 + 8:sx + c1 - 8]
                if np.isnan(blk).mean() > 0.3:
                    continue
                stones.append((int((a + b) / 2) // 60, sx + (c0 + c1) / 2, float(np.nanmedian(blk)), b - a))
    ppm = float(np.median([s[3] for s in stones])) / 1.05       # Herodian course ~1.05 m
    ref = spread([(s[0], s[1] / ppm * 100, s[2]) for s in stones])
    # joint dip at the P3 scale: box-resample the photo to 3.14 cm/px
    scale = (100 / 3.14) / ppm
    small = np.asarray(Image.fromarray((np.nan_to_num(Lk, nan=np.nanmean(Lk)) * 255).astype(np.uint8)).resize(
        (int(W * scale), int(H * scale)), Image.BOX), dtype=np.float32)[int(y0 * scale):int(y1 * scale)] / 255
    ref['bedJointDipStrip_atP3scale'] = strip_dip(small, 3.14, 105.0)
    ref['pxPerMetre'] = round(ppm, 1)
    ref['photoWidthM'] = round(W / ppm, 1)
    return ref, ppm


def mad(a, b):
    A, B = L(V / a), L(V / b)
    return round(float(np.abs(A - B).mean()), 5)


def main():
    res = {'script': 'Scripts/accept_precinct_cp20.py', 'label': LABEL}
    kref, kppm = kotel_reference()
    res['westernWallPhoto'] = kref
    res['P3'] = {}
    rect = {}
    for run in RUNS:
        f = V / ('%s-%s.png' % (run, M.VIEWS['P3'][0]))
        if not f.exists():
            res['P3'][run] = {'error': 'no frame'}
            continue
        v, along, zs = rectify('P3', run, 'x', M.XE, 55000, 65000)
        rect[run] = (v, along, zs)
        st = stone_means(v, along, zs, *P3_PHASE)
        res['P3'][run] = {'stones': spread(st), 'bedJointDipStrip': strip_dip(v),
                          'rectAcorr': rect_acorr(v, [150, 300, 600, 1200]),
                          'rectAcorrHighPass6m': rect_acorr(v, [150, 240, 300, 360, 450], hp_cm=600),
                          'screenTileAcorr_cp19def': screen_acorr(L(f), (200, 100, 3700, 1800))}
    res['P2'] = {}
    for run in RUNS:
        f = V / ('%s-%s.png' % (run, M.VIEWS['P2'][0]))
        if f.exists():
            v, along, zs = rectify('P2', run, 'y', M.YS, 4600, 15400)
            res['P2'][run] = {'bedJointDipStrip': strip_dip(v), 'rectAcorrHighPass6m': rect_acorr(v, [150, 300, 450], hp_cm=600),
                              'screenTileAcorr_cp19def': screen_acorr(L(f), (1500, 900, 3800, 1500))}
    prof = subprocess.run([sys.executable, str(ROOT / 'Scripts/measure_precinct_face_profile.py'), 'cp16before', 'cp19b', LABEL,
                           '--overlay'], capture_output=True, text=True)
    res['faceProfileExit'] = prof.returncode
    pj = OUT / ('face-profile-cp16before-cp19b-%s.json' % LABEL)
    if pj.exists():
        d = json.loads(pj.read_text(encoding='utf-8'))
        res['P1faceProfile'] = {run: {face: {k: vals.get(k) for k in ('metresPerPx', 'rawStd', 'hpStd', 'bandPowerShare', 'error')}
                                         for face, vals in views.get('P1', {}).items()}
                                for run, views in d['runs'].items()}
    nr = {}
    j = '%s-02-herodian-ashlar-inner-east-gate-jamb-walkingheight.png'
    s = '%s-07-north-gate-approach-plaza-stone-near.png'
    if (V / (j % LABEL)).exists():
        nr['02_jamb_cp19b_vs_' + LABEL] = mad(j % 'cp19b', j % LABEL)
    if (V / (s % LABEL)).exists():
        nr['07_plaza_cp19b_vs_' + LABEL] = mad(s % 'cp19b', s % LABEL)
    nr['07_noiseFloor_cp17_vs_cp17b'] = mad(s % 'cp17', s % 'cp17b')
    nr['02_noiseFloor_cp17_vs_cp19b'] = mad(j % 'cp17', j % 'cp19b')
    res['noRegression'] = nr
    # ---- sheets
    # (a) same stone scale: 12 m x 7 m of rectified P3 per run, and the Western Wall photo resampled to 3.14 cm/px
    tiles = []
    kim = Image.open(KOTEL).convert('RGB')
    ks = (100 / 3.14) / kppm
    kim = kim.resize((int(kim.width * ks), int(kim.height * ks)), Image.BICUBIC)
    band_h = 230
    kw = min(kim.width, 1100)
    # luminance only for all three rows, so the comparison is tone against tone
    tiles.append(('Western Wall (photo), same cm/px, luminance',
                  kim.crop((0, int(120 * ks), kw, int(120 * ks) + band_h)).convert('L').convert('RGB')))
    for run in ('cp19b', LABEL):
        if run in rect:
            v, along, zs = rect[run]
            r0 = np.searchsorted(-zs, 1500); c0 = np.searchsorted(along, 58000)
            a = np.nan_to_num(v[r0:r0 + band_h, c0:c0 + kw])
            tiles.append(('%s P3 60 m (rectified luminance)' % run, Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGB')))
    w = max(t[1].width for t in tiles)
    sheet = Image.new('RGB', (w, sum(t[1].height + 10 for t in tiles)), (255, 255, 255))
    y = 0
    for _n, t in tiles:
        sheet.paste(t, (0, y)); y += t.height + 10
    sheet.save(OUT / ('%s-P3-stone-scale-vs-westernwall.png' % LABEL))
    res['sheets'] = {'stoneScale': str(OUT / ('%s-P3-stone-scale-vs-westernwall.png' % LABEL)), 'order': [t[0] for t in tiles]}
    # (b) the full 60 m frame beside the Western Wall photo at the same height
    for view in ('P3', 'P2'):
        f20 = V / ('%s-%s.png' % (LABEL, M.VIEWS[view][0]))
        f19 = V / ('cp19b-%s.png' % M.VIEWS[view][0])
        if f20.exists() and f19.exists():
            a = Image.open(f19).convert('RGB').resize((1920, 1080), Image.BOX)
            b = Image.open(f20).convert('RGB').resize((1920, 1080), Image.BOX)
            k2 = Image.open(KOTEL).convert('RGB')
            k2 = k2.resize((1920, int(k2.height * 1920 / k2.width)), Image.BICUBIC)
            sh = Image.new('RGB', (1920, 1080 * 2 + k2.height + 20), (255, 255, 255))
            sh.paste(k2, (0, 0)); sh.paste(a, (0, k2.height + 10)); sh.paste(b, (0, k2.height + 1080 + 20))
            dst = OUT / ('%s-%s-westernwall-cp19b-%s.png' % (LABEL, view, LABEL))
            sh.save(dst)
            res['sheets'][view] = str(dst)
    txt = json.dumps(res, indent=1)
    (OUT / ('accept-%s.json' % LABEL)).write_text(txt, encoding='utf-8')
    print(txt)


if __name__ == '__main__':
    main()
