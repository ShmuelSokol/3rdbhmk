"""walls07 acceptance: do the plaza retaining faces read as Herodian masonry beside the Western Wall?

Judged against the Western Wall photo at MATCHED cm/px, by the same code that measures the photo
(Scripts/measure_masonry.py), on the packaged-build frames:

  P4  22 m   rectified at 1.59 cm/px   (the photo's own scale)
  P5  35 m   rectified at 1.59 cm/px
  P3  60 m   rectified at 3.14 cm/px   (the scale cp20b/cp25/cp26 were judged at)
  P2  70 m   rectified at 3.60 cm/px

plus:
  * CROSSOVER: dip at the close tile's own bed levels (300 cm tile: 0 / 101.52 / 193.56) where the macro
    layout has NO bed, against the dip at the macro's beds. cp26 measured a ghost ratio near 1.0 - the
    merged courses still showed the close tile's 1 m joints. With the V5 master fading the close tile off
    the vertical faces this should collapse toward zero.
  * no regression on 02 (the 4 m jamb, which this pass never touches) and 07 (plaza stone at walking
    range), against the cp17 -> cp17b noise floor.
  * the three-panel sheet: Western Wall / cp26 / walls07.

  python Scripts/accept_precinct_walls07.py <label=walls07> <before=cp26> <variant=V7c>
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path('C:/Mikdash/Working-5.8/MikdashCourtyardV3')
sys.path.insert(0, str(ROOT / 'Scripts'))
import measure_precinct_face_profile as M  # noqa: E402
import measure_masonry as MM  # noqa: E402

VR = ROOT / 'SourceAssets/visual-review'
OUT = ROOT / 'SourceAssets/enclosure-review/PrecinctMacroV1'
LABEL = sys.argv[1] if len(sys.argv) > 1 else 'walls07'
BEFORE = sys.argv[2] if len(sys.argv) > 2 else 'cp26'
VARIANT = sys.argv[3] if len(sys.argv) > 3 else 'V7c'
AMAH = 48.0
BAND = 5 * AMAH
CLOSE_TILE_CM = 300.0
CLOSE_BEDS = [0.0, 101.52, 193.56]

# The along/Z window of each view must fit INSIDE that camera's frustum, or every row is part-empty and the
# rectification drops all of them: at 22 m a 90 degree horizontal FOV only spans +-22 m, not +-30 m.
VIEWS = {
    'P4': ('P4-retaining-east-face-22m-crossover', 1.59, (58600, 61400), (-1650, -3200)),
    'P5': ('P5-retaining-east-face-35m-crossover', 1.59, (57800, 62200), (-1300, -3600)),
    'P3': ('P3-retaining-east-face-60m', 3.14, (55000, 65000), (-150, -7000)),
    'P2': ('P2-retaining-south-face-70m', 3.60, (4600, 15400), (-150, -7000)),
}


def face_x(z):
    k = np.maximum(np.floor(-np.asarray(z) / BAND).astype(int), 0)
    return M.XE + AMAH * (k // 5)


def cam_from_receipt(label, view_name):
    f = VR / ('frame-precinct-macro-%s.json' % label)
    if not f.exists():
        return None
    rc = json.loads(f.read_text(encoding='utf-8-sig'))
    for fr in rc['frames']:
        if fr.get('view') == view_name and fr.get('file'):
            return tuple(float(x) for x in fr['bugItGo'].split())
    return None


def rect_rgb(label, view_name, step, along_range, z_range, plane='x'):
    """Rectify a frame onto the battered face (each 5 bands steps out one amah), RGB, at `step` cm/px."""
    f = VR / ('%s-%s.png' % (label, view_name))
    cam = cam_from_receipt(label, view_name)
    if not f.exists() or cam is None:
        return None
    img = np.asarray(Image.open(f).convert('RGB'), dtype=np.float32) / 255.0
    H, W = img.shape[:2]
    along = np.arange(along_range[0], along_range[1], step)
    zs = np.arange(z_range[0], z_range[1], -step)
    out = np.full((len(zs), len(along), 3), np.nan, np.float32)
    for r0 in range(0, len(zs), 200):
        zz = zs[r0:r0 + 200]
        AA, ZZ = np.meshgrid(along, zz)
        if plane == 'x':
            pts = np.stack([face_x(ZZ).astype(float), AA, ZZ], -1).reshape(-1, 3)
        else:
            # the south face's outward normal is +Y (measure_precinct_face_profile.FACES), so its batter
            # steps the face OUT in +Y exactly as the east face steps out in +X
            pts = np.stack([AA, np.full_like(AA, M.YS) + (face_x(ZZ) - M.XE), ZZ], -1).reshape(-1, 3)
        px, py, df = M.project(pts, cam, W, H)
        ok = (df > 0) & (px >= 1) & (px < W - 2) & (py >= 1) & (py < H - 2)
        pxc, pyc = np.clip(px, 0, W - 2), np.clip(py, 0, H - 2)
        for c in range(3):
            out[r0:r0 + len(zz), :, c] = np.where(ok, M.bilinear(img[..., c], pxc, pyc), np.nan).reshape(AA.shape)
    keep = np.isfinite(out[..., 0]).mean(axis=1) > 0.85
    return out[keep], along, zs[keep], cam


def macro_beds(variant):
    man = json.loads((OUT / ('manifest-%s.json' % variant)).read_text(encoding='utf-8'))
    per_v = man['tone']['tileCm'][1]
    return sorted({round(c['z0'], 2) for c in man['macroLayout']}), per_v, man


def bed_dip_at(v, zs, step, z, strip_cm=200.0):
    """Dip of one bed level: the minimum within +-20 cm of it against the median 18-45 cm either side."""
    i = int(round((zs[0] - z) / step))
    ws, w18, w45 = int(round(20 / step)), int(round(18 / step)), int(round(45 / step))
    if i - ws - w45 < 0 or i + ws + w45 >= v.shape[0]:
        return None
    strip = max(4, int(round(strip_cm / step)))
    out = []
    fill = float(np.nanmean(v))
    for x0 in range(0, max(1, v.shape[1] - strip + 1), strip):
        pr = np.convolve(np.nan_to_num(np.nanmean(v[:, x0:x0 + strip], axis=1), nan=fill), np.ones(3) / 3, mode='same')
        j = i - ws + int(np.argmin(pr[i - ws:i + ws + 1]))
        base = np.median(np.concatenate([pr[j - w45:j - w18], pr[j + w18:j + w45]]))
        out.append(1 - pr[j] / base)
    return float(np.median(out)) if out else None


def fit_phase(v, zs, step, beds):
    prof = np.nanmean(v, axis=1)
    best = None
    for d in np.arange(-60.0, 60.1, step):
        idx = [int(round((zs[0] - (b + d)) / step)) for b in beds]
        vals = [prof[i] for i in idx if 0 <= i < len(prof)]
        if len(vals) < 3:
            continue
        sc = float(np.mean(vals))
        if best is None or sc < best[0]:
            best = (sc, float(d))
    return best[1] if best else 0.0


def crossover(v, zs, step, beds, per_v):
    """Is the close tile still drawing its own 1 m beds? Compare dip at close-only beds vs macro beds."""
    zlo, zhi = float(zs.min()), float(zs.max())
    macro_levels, close_only = [], []
    for n in range(int(math.floor(zlo / per_v)) - 1, int(math.floor(zhi / per_v)) + 2):
        for b in beds:
            z = n * per_v + b
            if zlo + 60 < z < zhi - 60:
                macro_levels.append(z)
    for ci in range(int(math.floor(zlo / CLOSE_TILE_CM)) - 1, int(math.floor(zhi / CLOSE_TILE_CM)) + 2):
        for b in CLOSE_BEDS:
            z = ci * CLOSE_TILE_CM + b
            if not (zlo + 60 < z < zhi - 60):
                continue
            if min(abs(z - m) for m in macro_levels) > 25.0:
                close_only.append(z)
    d = fit_phase(v, zs, step, macro_levels)
    md = [x for x in (bed_dip_at(v, zs, step, z + d) for z in macro_levels) if x is not None]
    cd = [x for x in (bed_dip_at(v, zs, step, z + d) for z in close_only) if x is not None]
    res = {'phaseResidualCm': d, 'macroBeds': len(md), 'closeOnlyBeds': len(cd),
           'macroBedDip': round(float(np.median(md)), 4) if md else None,
           'closeOnlyBedDip': round(float(np.median(cd)), 4) if cd else None}
    if md and cd:
        res['ghostRatio'] = round(res['closeOnlyBedDip'] / res['macroBedDip'], 3)
    return res


def mad(a, b):
    def L(p):
        x = np.asarray(Image.open(VR / p).convert('RGB'), dtype=np.float32) / 255.0
        return MM.luma(x)
    return round(float(np.abs(L(a) - L(b)).mean()), 5)


def main():
    beds, per_v, man = macro_beds(VARIANT)
    res = {'script': 'Scripts/accept_precinct_walls07.py', 'label': LABEL, 'before': BEFORE, 'variant': VARIANT,
           'judgedAgainst': 'Western Wall photo at matched cm/px, same code for photo and frame (measure_masonry.py)',
           'farAlbedoLinear': man.get('farAlbedoLinear'), 'grade': man.get('grade'), 'views': {}}
    sheets = {}
    for vk, (view, step, ar, zr) in VIEWS.items():
        row = {}
        for run in (BEFORE, LABEL):
            r = rect_rgb(run, view, step, ar, zr, plane='y' if vk == 'P2' else 'x')
            if r is None:
                row[run] = {'error': 'no frame'}
                continue
            v, along, zs, _cam = r
            m = MM.measure(v, step, '%s-%s' % (run, vk))
            m.pop('margins', None) if False else None
            m['margins'] = {k: x for k, x in m['margins'].items() if k != 'profile'}
            if vk in ('P4', 'P5', 'P3'):
                m['crossover'] = crossover(MM.luma(v), zs, step, beds, per_v)
            row[run] = m
            if run == LABEL:
                sheets[vk] = v
        # the photo at this view's scale, measured by the identical code
        pa, pc = MM.photo(step)
        pm = MM.measure(pa, pc, 'photo@%.2f' % pc)
        pm['margins'] = {k: x for k, x in pm['margins'].items() if k != 'profile'}
        row['westernWall'] = pm
        res['views'][vk] = row

    nr = {}
    j = '%s-02-herodian-ashlar-inner-east-gate-jamb-walkingheight.png'
    s = '%s-07-north-gate-approach-plaza-stone-near.png'
    for key, pat in (('02_jamb', j), ('07_plaza', s)):
        if (VR / (pat % LABEL)).exists() and (VR / (pat % BEFORE)).exists():
            nr['%s_%s_vs_%s' % (key, BEFORE, LABEL)] = mad(pat % BEFORE, pat % LABEL)
    for key, pat in (('07_noiseFloor_cp17_vs_cp17b', s), ('02_noiseFloor_cp17_vs_cp19b', j)):
        a, b = pat % 'cp17', pat % ('cp17b' if '07' in key else 'cp19b')
        if (VR / a).exists() and (VR / b).exists():
            nr[key] = mad(a, b)
    res['noRegression'] = nr

    # ---- three-panel sheet: Western Wall / before / after, P3 frames at equal width
    fa, fb = VR / ('%s-%s.png' % (LABEL, VIEWS['P3'][0])), VR / ('%s-%s.png' % (BEFORE, VIEWS['P3'][0]))
    if fa.exists() and fb.exists():
        k = Image.open(MM.KOTEL).convert('RGB')
        k2 = k.resize((1920, int(k.height * 1920 / k.width)), Image.BICUBIC)
        a = Image.open(fb).convert('RGB').resize((1920, 1080), Image.BOX)
        b = Image.open(fa).convert('RGB').resize((1920, 1080), Image.BOX)
        sh = Image.new('RGB', (1920, 1080 * 2 + k2.height + 20), (255, 255, 255))
        sh.paste(k2, (0, 0))
        sh.paste(a, (0, k2.height + 10))
        sh.paste(b, (0, k2.height + 1080 + 20))
        dst = OUT / ('%s-P3-westernwall-%s-%s.png' % (LABEL, BEFORE, LABEL))
        sh.save(dst)
        res['sheets'] = {'P3_threePanel': str(dst)}
    # ---- matched-scale strip: the photo and the 22 m face at the SAME cm/px and the same size
    if 'P4' in sheets:
        pa, pc = MM.photo(1.59)
        ph = Image.fromarray((np.clip(pa, 0, 1) * 255).astype(np.uint8))
        v = sheets['P4']
        w = min(ph.width, v.shape[1])
        h = min(ph.height, v.shape[0])
        fr = Image.fromarray((np.clip(np.nan_to_num(v[:h, :w]), 0, 1) * 255).astype(np.uint8))
        sh = Image.new('RGB', (w, h * 2 + 10), (255, 255, 255))
        sh.paste(ph.crop((0, 0, w, h)), (0, 0))
        sh.paste(fr, (0, h + 10))
        dst = OUT / ('%s-P4-vs-westernwall-matched-1.59cmpx.png' % LABEL)
        sh.save(dst)
        res.setdefault('sheets', {})['P4_matchedScale'] = str(dst)

    (OUT / ('accept-%s.json' % LABEL)).write_text(json.dumps(res, indent=1, default=float), encoding='utf-8')
    print(json.dumps(res, indent=1, default=float)[:6000])


if __name__ == '__main__':
    main()
