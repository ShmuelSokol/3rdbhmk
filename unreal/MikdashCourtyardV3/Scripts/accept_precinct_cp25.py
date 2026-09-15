"""cp25 acceptance: do the retaining faces read as Herodian masonry BESIDE THE WESTERN WALL at matched cm/px?

Judged against the Western Wall photo (SourceAssets/kotel-detail/PhotoSurfaceV1/kotel-wall-cleaned.png), not against the
previous build. Everything accept_precinct_cp20.py reports (same functions, same P3 rectification and phase), with the
Western Wall's value beside each, plus what cp25 set out to change:

  1. per-stone tone on the rectified 60 m face (P3): std log, p05-p95 ratio, neighbour contrast - close-layout
     segmentation exactly as cp20/cp20b (continuity), and for the V6 layout also its OWN stones (the true blocks)
  2. bed-joint strip dip at 3.14 cm/px (Western Wall 0.144)
  3. repeat: rectified autocorrelation high-passed at 6 m, value at the 300 cm tile lag (keep near -0.055)
  4. COURSE HEIGHT: one bed detector run on the photo (box-resampled to 3.14 cm/px) and on every rectified frame:
     CV of course heights, share over 1.5x the median, p95/median
  5. FACE RELIEF: intra-stone log std at 3.14 cm/px, block interiors (photo 0.105)
  6. CROSSOVER (the close tile keeps 1 m courses): at 22 m (P4) and 35 m (P5) the rectified dip at the beds V6 MERGED
     (ghosts) against the dip at the beds it kept; ghost ratio 0 = invisible, 1 = as strong as a real joint.
     The face is battered 1 amah per 5 bands, so P4/P5 are rectified onto the stepped face, not one plane.
  7. no regression: 02 jamb and 07 plaza stone mean |diff| vs the before build, against the cp17 noise floor
  8. sheets: Western Wall / before / after (the cp20b layout), stone-scale strip, crossover pair

  python Scripts/accept_precinct_cp25.py <label=cp25> <before=cp20b> <variant=V6>
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path('C:/Mikdash/Working-5.8/MikdashCourtyardV3')
sys.path.insert(0, str(ROOT / 'Scripts'))
import measure_precinct_face_profile as M  # noqa: E402
import accept_precinct_cp20 as A  # noqa: E402

V = ROOT / 'SourceAssets/visual-review'
OUT = ROOT / 'SourceAssets/enclosure-review/PrecinctMacroV1'
KOTEL = A.KOTEL
LABEL = sys.argv[1] if len(sys.argv) > 1 else 'cp25'
BEFORE = sys.argv[2] if len(sys.argv) > 2 else 'cp20b'
VARIANT = sys.argv[3] if len(sys.argv) > 3 else 'V6'
# the before build's P4/P5 frames are captured under their own label so the before receipt is never overwritten
BEFORE_XO = sys.argv[4] if len(sys.argv) > 4 else BEFORE + 'x'
MAN = json.loads((OUT / ('manifest-%s.json' % VARIANT)).read_text(encoding='utf-8'))
UNITS = MAN['macroLayout']
PER_U, PER_V = 9600.0, 4800.0
AMAH = 48.0
BAND = 5 * AMAH
DZ, DY = A.P3_PHASE
KP = 100 / 3.14                      # photo px per metre after resampling to the P3 scale


# ---------------------------------------------------------------- shared measures
def beds_detect(v, cm_per_px, strip_cm=200.0):
    """One bed detector for photo and frames: per 2 m strip, local row-profile minima at least 37 cm apart and 3 %
    below the local median. Returns course heights in cm."""
    sp = max(8, int(round(strip_cm / cm_per_px)))
    half = int(round(37.0 / cm_per_px))
    wide = int(round(125.0 / cm_per_px))
    hs = []
    vz = np.where(np.isfinite(v), v, np.nanmean(v))
    for x0 in range(0, vz.shape[1] - sp + 1, sp):
        pr = np.convolve(vz[:, x0:x0 + sp].mean(axis=1), np.ones(3) / 3, mode='same')
        mins = [i for i in range(half + 1, len(pr) - half - 1)
                if pr[i] == pr[i - half:i + half + 1].min() and pr[i] < 0.97 * np.median(pr[max(0, i - wide):i + wide])]
        hs += list(np.diff(mins) * cm_per_px)
    hs = np.array(hs, dtype=float)
    med = float(np.median(hs))
    core = hs[(hs > 0.6 * med) & (hs < 1.6 * med)]
    return {'n': int(len(hs)), 'medianCm': round(med, 1), 'cv': round(float(core.std() / med), 3),
            'fracOver1p5xMedian': round(float((hs > 1.5 * med).mean()), 3),
            'p95OverMedian': round(float(np.percentile(hs, 95) / med), 2)}


def block_stats(blocks):
    """blocks: list of (course_key, along_centre, 2-D luminance array). Tone spread + intra-stone log std."""
    st = [(k, a, float(np.nanmean(b))) for k, a, b in blocks]
    out = A.spread(st)
    intra = [float(np.nanstd(np.log(np.clip(b, 0.03, 1.0)))) for _k, _a, b in blocks]
    out['intraStoneLogStd'] = round(float(np.median(intra)), 4)
    return out


def close_blocks(v, along, zs, inset=22.0):
    """cp20 segmentation (close-tile layout), returning the blocks themselves."""
    Aa = along - DY
    Z = zs - DZ
    out = []
    for ci in range(int(math.floor(Z.min() / 300)), int(math.floor(Z.max() / 300)) + 1):
        for k in range(3):
            zb, zt = ci * 300 + A.BEDS[k], ci * 300 + A.BEDS[k + 1]
            wb, wt = zb + DZ, zt + DZ
            if min(abs(wb - round(wb / 1200) * 1200), abs(wt - round(wt / 1200) * 1200)) < 60:
                continue
            rows = (Z > zb + inset) & (Z < zt - inset)
            if rows.sum() < 3:
                continue
            js = A.JOINTS[k]
            for ti in range(int(math.floor(Aa.min() / 300)) - 1, int(math.floor(Aa.max() / 300)) + 1):
                xs = [ti * 300 + j for j in js] + [ti * 300 + js[0] + 300]
                for s in range(len(js)):
                    cols = (Aa > xs[s] + inset) & (Aa < xs[s + 1] - inset)
                    if cols.sum() < 3:
                        continue
                    blk = v[np.ix_(rows, cols)]
                    if np.isnan(blk).mean() > 0.05 or (blk < 0.12).mean() > 0.02:
                        continue
                    out.append((ci * 3 + k, 0.5 * (xs[s] + xs[s + 1]), blk))
    return out


def macro_blocks(v, along, zs, inset=22.0):
    """The V6 layout's own stones (macro beds and joints), same phase as the cp20 segmentation."""
    Aa = along - DY
    Z = zs - DZ
    out = []
    for n in range(int(math.floor(Z.min() / PER_V)), int(math.floor(Z.max() / PER_V)) + 1):
        for ui, u in enumerate(UNITS):
            zb, zt = n * PER_V + u['z0'], n * PER_V + u['z1']
            wb, wt = zb + DZ, zt + DZ
            if min(abs(wb - round(wb / 1200) * 1200), abs(wt - round(wt / 1200) * 1200)) < 60:
                continue
            rows = (Z > zb + inset) & (Z < zt - inset)
            if rows.sum() < 3:
                continue
            J = u['joints']
            for m in range(int(math.floor(Aa.min() / PER_U)) - 1, int(math.floor(Aa.max() / PER_U)) + 1):
                xs = [m * PER_U + j for j in J] + [m * PER_U + J[0] + PER_U]
                for s in range(len(J)):
                    cols = (Aa > xs[s] + inset) & (Aa < xs[s + 1] - inset)
                    if cols.sum() < 3:
                        continue
                    blk = v[np.ix_(rows, cols)]
                    if np.isnan(blk).mean() > 0.05 or (blk < 0.12).mean() > 0.02:
                        continue
                    out.append((n * 1000 + ui, 0.5 * (xs[s] + xs[s + 1]), blk))
    return out


def kotel_blocks_and_small():
    """Western Wall photo at the P3 scale (3.14 cm/px): the Herodian rows, and its blocks (kotel_reference's
    segmentation, run at native resolution, cut from the resampled image)."""
    rgb = np.asarray(Image.open(KOTEL).convert('RGB'), dtype=np.float32) / 255
    lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    Lk = np.where((rgb[..., 1] > rgb[..., 0] * 0.98) | (lum < 0.10), np.nan, lum)
    H, W = lum.shape
    y0, y1 = 120, 715
    _ref, ppm = A.kotel_reference()
    sc = KP / ppm
    fill = np.nan_to_num(Lk, nan=float(np.nanmean(Lk)))
    small = np.asarray(Image.fromarray((fill * 255).astype(np.uint8)).resize((int(W * sc), int(H * sc)), Image.BOX),
                       dtype=np.float32) / 255
    band = small[int(y0 * sc):int(y1 * sc)]

    def smooth(x, n):
        x = np.where(np.isnan(x), np.nanmean(x), x)
        return np.convolve(np.pad(x, n, mode='edge'), np.ones(2 * n + 1) / (2 * n + 1), mode='valid')
    blocks = []
    for sx in range(0, W - 400 + 1, 400):
        ps = smooth(np.nanmean(Lk[y0:y1, sx:sx + 400], axis=1), 2)
        mins = []
        for i in range(3, len(ps) - 3):
            if ps[i] == ps[max(0, i - 25):i + 26].min() and (not mins or i - mins[-1] > 40):
                mins.append(i)
        bedsy = [y0 + m for m in mins]
        for a, b in zip(bedsy, bedsy[1:]):
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
                r0, r1 = int((a + 14) * sc), int((b - 14) * sc)          # ~22 cm inset, as on the frames
                q0, q1 = int((sx + c0 + 14) * sc), int((sx + c1 - 14) * sc)
                if r1 - r0 < 3 or q1 - q0 < 3:
                    continue
                nat = Lk[a + 14:b - 14, sx + c0 + 14:sx + c1 - 14]
                if np.isnan(nat).mean() > 0.3:
                    continue
                blocks.append((int((a + b) / 2) // 60, (sx + (c0 + c1) / 2) / ppm * 100, small[r0:r1, q0:q1]))
    return band, blocks


# ---------------------------------------------------------------- crossover (P4/P5): stepped-face rectification
def face_x(z):
    k = np.floor(-np.asarray(z) / BAND).astype(int)
    k = np.maximum(k, 0)
    return M.XE + AMAH * (k // 5)


def cam_from_receipt(label, view_name):
    f = V / ('frame-precinct-macro-%s.json' % label)
    if not f.exists():
        return None
    rc = json.loads(f.read_text(encoding='utf-8-sig'))
    for f in rc['frames']:
        if f.get('view') == view_name and f.get('file'):
            return tuple(float(x) for x in f['bugItGo'].split())
    return None


def rectify_stepped(label, view_name, a0, a1, z0, z1, step):
    f = V / ('%s-%s.png' % (label, view_name))
    cam = cam_from_receipt(label, view_name)
    if not f.exists() or cam is None:
        return None
    img = A.L(f)
    H, W = img.shape
    along = np.arange(a0, a1, step)
    zs = np.arange(z0, z1, -step)
    AA, ZZ = np.meshgrid(along, zs)
    pts = np.stack([face_x(ZZ).astype(float), AA, ZZ], axis=-1).reshape(-1, 3)
    px, py, df = M.project(pts, cam, W, H)
    ok = (df > 0) & (px >= 1) & (px < W - 2) & (py >= 1) & (py < H - 2)
    v = np.where(ok, M.bilinear(img, np.clip(px, 0, W - 2), np.clip(py, 0, H - 2)), np.nan).reshape(AA.shape)
    keep = np.isfinite(v).mean(axis=1) > 0.9
    return v[keep], along, zs[keep], cam


def bed_sets(zlo, zhi):
    """World Z of every close bed in [zlo, zhi], split into kept (a V6 unit boundary) and ghost (merged by V6)."""
    unit_beds = sorted({round(u['z0'], 2) for u in UNITS})
    kept, ghost = [], []
    for ci in range(int(math.floor(zlo / 300)) - 1, int(math.floor(zhi / 300)) + 2):
        for b in A.BEDS[:-1]:
            z = ci * 300 + b
            if not zlo + 50 < z < zhi - 50:
                continue
            t = round(z % PER_V, 2)
            (kept if any(abs(t - ub) < 0.6 or abs(t - ub - PER_V) < 0.6 or abs(t - ub + PER_V) < 0.6 for ub in unit_beds) else ghost).append(z)
    return kept, ghost


def fit_phase(v, zs, step, beds_all):
    """Residual Z offset of the rendered beds against the layout (the stepped rectification should leave ~0)."""
    prof = np.nanmean(v, axis=1)
    best = None
    for d in np.arange(-40.0, 40.1, step):
        idx = [int(round((zs[0] - (b + d)) / step)) for b in beds_all]
        vals = [prof[i] for i in idx if 0 <= i < len(prof)]
        if len(vals) < 3:
            continue
        sc = float(np.mean(vals))
        if best is None or sc < best[0]:
            best = (sc, float(d))
    return best[1] if best else 0.0


def bed_dip(v, zs, step, z, strip_px):
    """Dip of one bed, per 2 m strip: the minimum within +-20 cm of the expected bed (beds are >= 92 cm apart, and the
    battered-face rectification drifts by up to ~30 cm with height - measured on cp20b), against the median 18-45 cm
    either side of that minimum. Median over strips."""
    out = []
    i = int(round((zs[0] - z) / step))
    ws, w18, w45 = int(round(20 / step)), int(round(18 / step)), int(round(45 / step))
    if i - ws - w45 < 0 or i + ws + w45 >= v.shape[0]:
        return None
    for x0 in range(0, v.shape[1] - strip_px + 1, strip_px):
        pr = np.convolve(np.nan_to_num(np.nanmean(v[:, x0:x0 + strip_px], axis=1), nan=float(np.nanmean(v))),
                         np.ones(3) / 3, mode='same')
        j = i - ws + int(np.argmin(pr[i - ws:i + ws + 1]))
        base = np.median(np.concatenate([pr[j - w45:j - w18], pr[j + w18:j + w45]]))
        out.append(1 - pr[j] / base)
    return float(np.median(out))


def crossover(label, view_name, step=1.5):
    cam = cam_from_receipt(label, view_name)
    if cam is None:
        return {'error': 'no frame'}
    x, y, zc = cam[0], cam[1], cam[2]
    dist = x - M.XE
    half_v = dist * math.tan(math.radians(45.0)) * 9 / 16 * 0.92
    half_a = dist * 0.85
    r = rectify_stepped(label, view_name, y - half_a, y + half_a, zc + half_v, zc - half_v, step)
    if r is None:
        return {'error': 'no frame'}
    v, along, zs, _cam = r
    kept, ghost = bed_sets(zs.min(), zs.max())
    d = fit_phase(v, zs, step, kept + ghost)
    kept = [z + d for z in kept]
    ghost = [z + d for z in ghost]
    strip = int(round(200 / step))
    kd = [x for x in (bed_dip(v, zs, step, z, strip) for z in kept) if x is not None]
    gd = [x for x in (bed_dip(v, zs, step, z, strip) for z in ghost) if x is not None]
    res = {'distanceM': round(dist / 100, 1), 'phaseResidualCm': d, 'keptBeds': len(kd), 'ghostBeds': len(gd),
           'keptBedDip': round(float(np.median(kd)), 4) if kd else None,
           'ghostBedDip': round(float(np.median(gd)), 4) if gd else None}
    if kd and gd:
        res['ghostRatio'] = round(res['ghostBedDip'] / res['keptBedDip'], 3)
    res['ghostBedsWorldZ'] = [round(z) for z in ghost]
    return res, v


def bed_visibility(label, view_name, a0, a1, z0, z1, step=3.0):
    """What the eye sees as courses: rectify onto the stepped face, measure the rendered dip at EVERY close-tile bed,
    call a bed visible when its dip exceeds 40 % of the median dip of the beds V6 keeps, and report the spacings
    between visible beds. The generic detector (beds_detect) misreads weathering and skips weak beds on frames (it gives
    cp20b, which has no tall course, 8 % 'tall courses'), so this is the course-height number to judge by."""
    r = rectify_stepped(label, view_name, a0, a1, z0, z1, step)
    if r is None:
        return {'error': 'no frame'}
    v, _along, zs, _cam = r
    kept, ghost = bed_sets(zs.min(), zs.max())
    d = fit_phase(v, zs, step, kept + ghost)
    strip = int(round(200 / step))
    rows = []
    for z, kind in [(z + d, 'kept') for z in kept] + [(z + d, 'ghost') for z in ghost]:
        dp = bed_dip(v, zs, step, z, strip)
        if dp is not None:
            rows.append((z, kind, dp))
    kd = [x[2] for x in rows if x[1] == 'kept']
    gd = [x[2] for x in rows if x[1] == 'ghost']
    thr = 0.4 * float(np.median(kd))
    vis = sorted(z for z, _k, dp in rows if dp > thr)
    hs = np.diff(vis) if len(vis) > 1 else np.array([0.0])
    # a gap wider than 3.2 m is a bed lost at a batter ledge / wash, not a course
    hs = hs[hs < 320.0]
    med = float(np.median(hs))
    return {'phaseResidualCm': d, 'bedsMeasured': len(rows), 'keptBedDip': round(float(np.median(kd)), 4),
            'ghostBedDip': round(float(np.median(gd)), 4) if gd else None,
            'ghostRatio': round(float(np.median(gd)) / float(np.median(kd)), 3) if gd else None,
            'visibleCourseHeightsCm': {'n': int(len(hs)), 'median': round(med, 1), 'cv': round(float(hs.std() / med), 3),
                                       'fracOver1p5xMedian': round(float((hs > 1.5 * med).mean()), 3),
                                       'max': round(float(hs.max()), 1),
                                       'histogram': {str(int(b)): int(c) for b, c in zip(*np.unique(np.round(hs / 10) * 10, return_counts=True))}}}


# ---------------------------------------------------------------- main
def main():
    res = {'script': 'Scripts/accept_precinct_cp25.py', 'label': LABEL, 'before': BEFORE, 'variant': VARIANT,
           'judgedAgainst': 'Western Wall photo at matched cm/px (3.14 cm/px, the P3 60 m scale)'}
    kref, _ppm = A.kotel_reference()
    band, kblocks = kotel_blocks_and_small()
    ww = {'stdLog': kref['stdLog'], 'p05p95Ratio': kref['p05p95Ratio'], 'medianNeighbourAbsLog': kref['medianNeighbourAbsLog'],
          'bedJointDip': kref['bedJointDipStrip_atP3scale'], 'courses': beds_detect(band, 3.14),
          'intraStoneLogStd': block_stats(kblocks)['intraStoneLogStd'], 'nStones': kref['nStones']}
    res['westernWall'] = ww
    rect = {}
    res['P3'] = {}
    for run in (BEFORE, LABEL):
        f = V / ('%s-%s.png' % (run, M.VIEWS['P3'][0]))
        if not f.exists():
            res['P3'][run] = {'error': 'no frame'}
            continue
        v, along, zs = A.rectify('P3', run, 'x', M.XE, 55000, 65000)
        rect[run] = (v, along, zs)
        cb = close_blocks(v, along, zs)
        row = {'stonesCloseLayout': block_stats(cb), 'bedJointDip': A.strip_dip(v),
               'rectAcorrHighPass6m': A.rect_acorr(v, [150, 240, 300, 360, 450], hp_cm=600),
               'courses': beds_detect(v, A.STEP)}
        if run == LABEL:
            row['stonesOwnLayout'] = block_stats(macro_blocks(v, along, zs))
        row['bedVisibility'] = bed_visibility(run, M.VIEWS['P3'][0], 55000, 65000, -150, -7000)
        res['P3'][run] = row
    res['P2'] = {}
    for run in (BEFORE, LABEL):
        f = V / ('%s-%s.png' % (run, M.VIEWS['P2'][0]))
        if f.exists():
            v, along, zs = A.rectify('P2', run, 'y', M.YS, 4600, 15400)
            res['P2'][run] = {'bedJointDip': A.strip_dip(v), 'rectAcorrHighPass6m': A.rect_acorr(v, [150, 300, 450], hp_cm=600),
                              'courses': beds_detect(v, A.STEP)}
    # ---- the table the brief asks for: metric, Western Wall, before, after
    a3, b3 = res['P3'].get(LABEL, {}), res['P3'].get(BEFORE, {})

    def g(d, *ks):
        for k in ks:
            if not isinstance(d, dict) or k not in d:
                return None
            d = d[k]
        return d
    res['table'] = [
        ['stone-tone log std', ww['stdLog'], g(b3, 'stonesCloseLayout', 'stdLog'), g(a3, 'stonesCloseLayout', 'stdLog'), g(a3, 'stonesOwnLayout', 'stdLog')],
        ['5-95 % ratio', ww['p05p95Ratio'], g(b3, 'stonesCloseLayout', 'p05p95Ratio'), g(a3, 'stonesCloseLayout', 'p05p95Ratio'), g(a3, 'stonesOwnLayout', 'p05p95Ratio')],
        ['neighbour contrast', ww['medianNeighbourAbsLog'], g(b3, 'stonesCloseLayout', 'medianNeighbourAbsLog'), g(a3, 'stonesCloseLayout', 'medianNeighbourAbsLog'), g(a3, 'stonesOwnLayout', 'medianNeighbourAbsLog')],
        ['bed-joint dip', ww['bedJointDip'], g(b3, 'bedJointDip'), g(a3, 'bedJointDip'), None],
        ['course-height CV (visible beds)', ww['courses']['cv'], g(b3, 'bedVisibility', 'visibleCourseHeightsCm', 'cv'), g(a3, 'bedVisibility', 'visibleCourseHeightsCm', 'cv'), None],
        ['courses > 1.5x median (visible beds)', ww['courses']['fracOver1p5xMedian'], g(b3, 'bedVisibility', 'visibleCourseHeightsCm', 'fracOver1p5xMedian'), g(a3, 'bedVisibility', 'visibleCourseHeightsCm', 'fracOver1p5xMedian'), None],
        ['course-height CV (generic detector, noisy)', ww['courses']['cv'], g(b3, 'courses', 'cv'), g(a3, 'courses', 'cv'), None],
        ['intra-stone log std', ww['intraStoneLogStd'], g(b3, 'stonesCloseLayout', 'intraStoneLogStd'), g(a3, 'stonesCloseLayout', 'intraStoneLogStd'), g(a3, 'stonesOwnLayout', 'intraStoneLogStd')],
        ['hp autocorr @300 cm', None, g(b3, 'rectAcorrHighPass6m', '300'), g(a3, 'rectAcorrHighPass6m', '300'), None],
    ]
    res['tableColumns'] = ['metric', 'Western Wall', BEFORE, LABEL + ' (close-layout segmentation)', LABEL + ' (own V6 stones)']
    # ---- crossover
    res['crossover'] = {}
    xo_imgs = {}
    for run in (BEFORE_XO, LABEL):
        for vn in ('P4-retaining-east-face-22m-crossover', 'P5-retaining-east-face-35m-crossover'):
            out = crossover(run, vn)
            if isinstance(out, tuple):
                res['crossover'].setdefault(run, {})[vn[:2]] = out[0]
                xo_imgs[(run, vn[:2])] = out[1]
            else:
                res['crossover'].setdefault(run, {})[vn[:2]] = out
    res['crossoverNote'] = ('ghostRatio = dip at the close beds the V6 layout merged / dip at the beds it kept. In the '
                            'before build every bed is real, so its ratio is the control (~1).')
    # ---- P1 aerial profile (sub-Nyquist at 1 km; reported for continuity)
    prof = subprocess.run([sys.executable, str(ROOT / 'Scripts/measure_precinct_face_profile.py'), BEFORE, LABEL],
                          capture_output=True, text=True)
    res['faceProfileExit'] = prof.returncode
    pj = OUT / ('face-profile-%s-%s.json' % (BEFORE, LABEL))
    if pj.exists():
        d = json.loads(pj.read_text(encoding='utf-8'))
        res['P1faceProfile'] = {run: {face: {k: vals.get(k) for k in ('metresPerPx', 'rawStd', 'hpStd', 'bandPowerShare')}
                                         for face, vals in views.get('P1', {}).items()}
                                for run, views in d['runs'].items()}
    # ---- no regression
    nr = {}
    j = '%s-02-herodian-ashlar-inner-east-gate-jamb-walkingheight.png'
    s = '%s-07-north-gate-approach-plaza-stone-near.png'
    for key, pat in (('02_jamb', j), ('07_plaza', s)):
        if (V / (pat % LABEL)).exists() and (V / (pat % BEFORE)).exists():
            nr['%s_%s_vs_%s' % (key, BEFORE, LABEL)] = A.mad(pat % BEFORE, pat % LABEL)
    nr['07_noiseFloor_cp17_vs_cp17b'] = A.mad(s % 'cp17', s % 'cp17b')
    nr['02_noiseFloor_cp17_vs_cp19b'] = A.mad(j % 'cp17', j % 'cp19b')
    res['noRegression'] = nr
    # ---- sheets
    sheets = {}
    kim = Image.open(KOTEL).convert('RGB')
    f_b = V / ('%s-%s.png' % (BEFORE, M.VIEWS['P3'][0]))
    f_a = V / ('%s-%s.png' % (LABEL, M.VIEWS['P3'][0]))
    if f_a.exists() and f_b.exists():
        a = Image.open(f_b).convert('RGB').resize((1920, 1080), Image.BOX)
        b = Image.open(f_a).convert('RGB').resize((1920, 1080), Image.BOX)
        k2 = kim.resize((1920, int(kim.height * 1920 / kim.width)), Image.BICUBIC)
        sh = Image.new('RGB', (1920, 1080 * 2 + k2.height + 20), (255, 255, 255))
        sh.paste(k2, (0, 0)); sh.paste(a, (0, k2.height + 10)); sh.paste(b, (0, k2.height + 1080 + 20))
        dst = OUT / ('%s-P3-westernwall-%s-%s.png' % (LABEL, BEFORE, LABEL))
        sh.save(dst)
        sheets['P3_threePanel'] = str(dst)
    # stone scale: Western Wall / before / after, 3.14 cm/px, colour
    ks = KP / _ppm
    kimc = kim.resize((int(kim.width * ks), int(kim.height * ks)), Image.BICUBIC)
    band_h, kw = 230, min(kimc.width, 1100)
    tiles = [kimc.crop((0, int(120 * ks), kw, int(120 * ks) + band_h))]
    for run in (BEFORE, LABEL):
        if run in rect:
            v, along, zs = rect[run]
            r0 = int(np.searchsorted(-zs, 1500)); c0 = int(np.searchsorted(along, 58000))
            av = np.nan_to_num(v[r0:r0 + band_h, c0:c0 + kw])
            tiles.append(Image.fromarray((np.clip(av, 0, 1) * 255).astype(np.uint8)).convert('RGB'))
    tiles[0] = tiles[0].convert('L').convert('RGB')
    w = max(t.width for t in tiles)
    sheet = Image.new('RGB', (w, sum(t.height + 10 for t in tiles)), (255, 255, 255))
    y = 0
    for t in tiles:
        sheet.paste(t, (0, y)); y += t.height + 10
    dst = OUT / ('%s-P3-stone-scale-vs-westernwall.png' % LABEL)
    sheet.save(dst)
    sheets['stoneScale'] = str(dst)
    sheets['stoneScaleOrder'] = ['Western Wall (photo), 3.14 cm/px, luminance', BEFORE + ' P3 rectified', LABEL + ' P3 rectified']
    # crossover pairs: before | after at 22 m and 35 m, with the ghost beds marked on the right edge
    for vk in ('P4', 'P5'):
        name = 'P4-retaining-east-face-22m-crossover' if vk == 'P4' else 'P5-retaining-east-face-35m-crossover'
        fa, fb = V / ('%s-%s.png' % (LABEL, name)), V / ('%s-%s.png' % (BEFORE_XO, name))
        if fa.exists() and fb.exists():
            ia = Image.open(fb).convert('RGB').resize((1600, 900), Image.BOX)
            ib = Image.open(fa).convert('RGB').resize((1600, 900), Image.BOX)
            cam = cam_from_receipt(LABEL, name)
            gz = (res['crossover'].get(LABEL, {}).get(vk) or {}).get('ghostBedsWorldZ', [])
            dr = ImageDraw.Draw(ib)
            for z in gz:
                pts = np.array([[face_x(z), cam[1] + 2000 * 0, z]], dtype=float)
                _px, py, _df = M.project(pts, cam, 1600, 900)
                dr.line([(1570, float(py[0])), (1599, float(py[0]))], fill=(255, 40, 40), width=3)
            sh = Image.new('RGB', (1600, 1810), (255, 255, 255))
            sh.paste(ia, (0, 0)); sh.paste(ib, (0, 910))
            dst = OUT / ('%s-%s-crossover-%s-%s.png' % (LABEL, vk, BEFORE, LABEL))
            sh.save(dst)
            sheets[vk + '_crossover'] = str(dst)
    res['sheets'] = sheets
    txt = json.dumps(res, indent=1)
    (OUT / ('accept-%s.json' % LABEL)).write_text(txt, encoding='utf-8')
    print(json.dumps({'westernWall': ww, 'table': res['table'], 'crossover': res['crossover'], 'noRegression': nr}, indent=1))


if __name__ == '__main__':
    main()
