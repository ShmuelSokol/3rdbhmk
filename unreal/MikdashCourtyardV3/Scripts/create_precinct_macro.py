"""Precinct retaining-face MACRO layer: the far-field equivalent of the Herodian ashlar close-up.

WHY THIS EXISTS (measured, 10-11 Sep 2026)
The precinct retaining faces (90-137 m tall, SM_PlazaV1_RetainingBand, MI_PrecinctPlaza_Ashlar ->
MI_HerodianV4_Ashlar -> M_PBR_Tiled) rendered as featureless tan slabs in cp05b-04. The material is
correct: the close-up tile is 300 cm and contains NO structure larger than 3 m. In the aerial frame the
face is ~0.5-1.5 m per screen pixel, so the sampler takes mip 9-11 of the 2048 tile (4, 2, 1 texels per
300 cm); mip 11 has zero variance by construction. Measured on the frame: vertical row-profile std
0.017-0.035 over faces 80-130 px tall, i.e. no course signal at all.

WHAT THIS MAKES
Two linear, tileable multiplier textures (0.5 = x1.0), sampled by M_PrecinctMacro_Triplanar in the SAME
u = world X|Y, v = world Z convention as M_PBR_Tiled:

  T_PrecinctMacro_Tone     4096 x 2048 over 9600 x 4800 cm (2.34 cm/px), i.e. 32 x 16 close-up tiles.
      Every stone of the close-up tile is drawn at its real joints (measured off T_HerodianV5_Ashlar_Height,
      which is the V5b layout), but each REPEAT of that stone gets its own tone: per-stone value and quarry
      family, course tone in runs of 1-4 courses (horizontal banding), a shadowed drafted margin under each
      boss and a dark bed joint. Aligned to the close-up joints, so at mid range the two agree stone for stone.
  T_PrecinctMacro_Weather  1024 x 1024 over 12800 x 12800 cm (12.5 cm/px), periodic FFT noise: broad
      patina, 5-8 m patches and sparse vertical run-off streaks. A different period from the tone map so
      the two never repeat together.

  python Scripts/create_precinct_macro.py        (Python 3.8 with numpy + PIL; NOT the engine's python)
      -> SourceAssets/enclosure-review/PrecinctMacroV1/{T_PrecinctMacro_Tone.png, T_PrecinctMacro_Weather.png,
         manifest.json, preview-*.png}
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path('C:/Mikdash/Working-5.8/MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/enclosure-review/PrecinctMacroV1'
V5 = ROOT / 'SourceAssets/material-review/HerodianAshlarV5'
TILE_CM = 300.0

TONE_W, TONE_H = 4096, 2048
TONE_U_CM, TONE_V_CM = 9600.0, 4800.0
WEATHER_N = 1024
WEATHER_CM = 12800.0

SEED = 17170911
PARAMS = {
    'stoneToneSigma': 0.075,         # log-normal std of per-stone value
    'courseToneSigma': 0.045,        # log-normal std of per-course-run value
    'courseRunLengths': [1, 2, 2, 3, 3, 4],
    'rareDarkChance': 0.05, 'rareDark': 0.84,
    'rareLightChance': 0.05, 'rareLight': 1.10,
    'families': {'base': [0.55, [1.0, 1.0, 1.0]],
                 'honey': [0.25, [1.035, 1.0, 0.94]],
                 'greygold': [0.20, [0.965, 0.985, 1.025]]},
    'stoneGradient': 0.03,           # max per-stone linear tone gradient, either axis
    'marginCm': {'left': 10.0, 'right': 10.0, 'bottom': 10.0, 'top': 13.0},
    'marginFactor': {'bottom': 0.80, 'side': 0.90, 'top': 0.95},
    'jointHalfWidthCm': 1.6, 'jointFactor': 0.62,
    'toneMeanTarget': 0.97,
    'weather': {'broadSigmaCm': [1900, 2500], 'broadStd': 0.040,
                'patchSigmaCm': [500, 750], 'patchStd': 0.045,
                'streakSigmaCm': [40, 1000], 'streakStd': 0.070,
                'streakMaskSigmaCm': 380, 'meanTarget': 1.0},
}


# --variant V2 (11 Sep, after the cp17 frames): V1 added weathering mottle at 1 km but NO course banding - its
# course-tone runs were 1-4 m, i.e. 1-4 px at the aerial camera, and sigma 4.5 % was too weak to survive. V2 keeps
# the same stones and joints (same layout) and makes the far-field structure bigger and stronger. V1 files are
# never overwritten: V2 writes T_PrecinctMacro_ToneV2.png and manifest-V2.json; the weather map is reused.
VARIANT = sys.argv[sys.argv.index('--variant') + 1] if '--variant' in sys.argv else 'V1'
if VARIANT == 'V2':
    SEED += 1
    PARAMS.update({'stoneToneSigma': 0.095, 'courseToneSigma': 0.075, 'courseRunLengths': [2, 3, 4, 5, 6, 8],
                   'rareDarkChance': 0.07, 'rareDark': 0.80, 'jointFactor': 0.55,
                   'marginFactor': {'bottom': 0.72, 'side': 0.88, 'top': 0.95}})
# --variant V4 (cp20, 11 Sep, after the cp19b 60 m frame read as a toy-brick quilt). Measured on the rectified
# cp19b P3 face vs the Western Wall photo (kotel-detail/PhotoSurfaceV1): per-stone log spread 1.4x the Kotel's,
# but every stone a FLAT field (the close albedo is faded 85 % to its mean at 60 m) with a dark continuous outline
# (bed-joint dip 0.235 vs the Kotel's 0.144 at the same 3.14 cm/px) and only two stone lengths. V4 = one quarry:
# per-stone spread cut hard, no rare dark stones, near-neutral families, drafted margin drawn as a thin bevel
# light/shadow instead of a dark band, joints soft, stone-interior mottle so a stone reads as stone not paint,
# and a share of vertical joints MERGED (same tone, no drawn joint) so lengths run 1.4-9 m irregularly.
# Built by build_tone_v4 (separate function; V1/V2 generation is byte-for-byte unchanged).
elif VARIANT in ('V4', 'V5'):
    SEED += 3            # V5 keeps V4's seed: same stones, merges, mottle and batches - only amplitudes differ
    PARAMS.update({
        'stoneToneSigma': 0.045, 'courseToneSigma': 0.016, 'courseRunLengths': [1, 2, 2, 3, 4],
        'rareDarkChance': 0.0, 'rareDark': 1.0, 'rareLightChance': 0.025, 'rareLight': 1.05,
        'families': {'base': [0.60, [1.0, 1.0, 1.0]],
                     'honey': [0.25, [1.012, 1.0, 0.986]],
                     'greygold': [0.15, [0.992, 0.997, 1.008]]},
        'stoneGradient': 0.012,
        'marginCm': {'left': 10.0, 'right': 10.0, 'bottom': 10.0, 'top': 13.0},
        # the drafted margin itself is barely a tone change; its EDGE carries a thin bevel light/shadow
        'marginFactor': {'bottom': 0.975, 'side': 0.985, 'top': 1.0},
        'bevelCm': 2.2, 'bevelShadow': {'bottom': 0.86, 'side': 0.95}, 'bevelLight': {'top': 1.05},
        'jointHalfWidthCm': 1.1, 'jointFactor': 0.80,
        'mergeChance': 0.33, 'mergeMaxRun': 2, 'mergedJointFactor': 0.97,
        'mottle': {'fineSigmaCm': 7.0, 'fineStd': 0.022, 'midSigmaCm': 28.0, 'midStd': 0.030},
        'batch': {'sigmaCm': 450.0, 'std': 0.018},
        'toneMeanTarget': 0.97,
    })
elif VARIANT != 'V1' and not VARIANT.startswith('V6'):
    raise SystemExit('unknown variant ' + VARIANT)
# --variant V5 (cp20b): the cp20 frames showed V4 overshot - the quilt was gone but stones nearly vanished at 60 m
# (bed-joint strip dip 0.042 vs the Western Wall's 0.144 at the same 3.14 cm/px; neighbour contrast 0.025 vs 0.045).
# Dip is linear in (1 - line factor) x line width across cp19b and cp20 (5.5 cm -> 0.235, 1.0 cm -> 0.042), so the bed
# line gets ~2.4 cm of darkness: joint 0.62, a 3 cm bevel shadow 0.72 under each boss, bottom margin 0.93, and a 1.08
# bevel light along each boss top - the drafted margin as a light-and-shadow frame. Vertical joints stay softer (0.75):
# the Western Wall reads in horizontal courses, and bed lines do not feed the horizontal repeat. Per-stone sigma 0.06
# and stronger interior mottle so each block reads as a stone of one quarry, not as paint.
if VARIANT == 'V5':
    PARAMS.update({
        'stoneToneSigma': 0.06, 'courseToneSigma': 0.02,
        'marginFactor': {'bottom': 0.93, 'side': 0.96, 'top': 1.0},
        'bevelCm': 3.0, 'bevelShadow': {'bottom': 0.72, 'side': 0.90}, 'bevelLight': {'top': 1.08},
        'jointHalfWidthCm': 1.1, 'jointFactor': 0.62, 'vertJointFactor': 0.75,
        'mottle': {'fineSigmaCm': 7.0, 'fineStd': 0.03, 'midSigmaCm': 28.0, 'midStd': 0.04},
    })
SUFFIX = '' if VARIANT == 'V1' else VARIANT


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def measure_layout():
    """Bed joints and vertical joints of the live close-up tile, read off its height map."""
    man = json.loads((V5 / 'manifest.json').read_text(encoding='utf-8'))
    sched = man['variants']['Ashlar']['schedule']
    heights = sched['courseHeightsCm']
    per_course = sched['blocksPerCourse']
    h = np.asarray(Image.open(V5 / 'T_HerodianV5_Ashlar_Height.png')).astype(np.float64)
    if h.ndim == 3:
        h = h[..., 0]
    n = h.shape[0]
    cm_per_px = TILE_CM / n
    beds = [0.0]
    for hh in heights[:-1]:
        beds.append(beds[-1] + hh)
    beds.append(TILE_CM)
    # confirm each scheduled bed joint is a height minimum on the map (within 3 cm)
    rows = h.mean(axis=1)
    bed_check = []
    for b in beds[:-1]:
        c = int(round(b / cm_per_px)) % n
        win = [(c + d) % n for d in range(-20, 21)]
        lo = min(win, key=lambda i: rows[i])
        off = ((lo - c + n // 2) % n - n // 2) * cm_per_px
        bed_check.append(round(off, 2))
    joints = []
    for k in range(len(heights)):
        r0 = int((beds[k] + 15.0) / cm_per_px)
        r1 = int((beds[k + 1] - 15.0) / cm_per_px)
        cols = h[r0:r1].mean(axis=0)
        found = []
        order = np.argsort(cols)
        for i in order:
            x = i * cm_per_px
            if all(min(abs(x - f), TILE_CM - abs(x - f)) > 40.0 for f in found):
                found.append(x)
            if len(found) == per_course[k]:
                break
        # refine each joint to the centroid of the lowest 1 % of columns within +-6 cm
        refined = []
        for f in found:
            c = int(round(f / cm_per_px))
            idx = [(c + d) % n for d in range(-40, 41)]
            vals = np.array([cols[i] for i in idx])
            thr = vals.min() + 0.25 * (np.median(vals) - vals.min())
            sel = [d for d, v in zip(range(-40, 41), vals) if v <= thr]
            refined.append(round(((c + float(np.mean(sel))) * cm_per_px) % TILE_CM, 2))
        joints.append(sorted(refined))
    return {'bedsCm': [round(b, 2) for b in beds], 'bedCheckOffsetCm': bed_check,
            'jointsCmPerCourse': joints, 'blocksPerCourse': per_course,
            'heightSha256': sha(V5 / 'T_HerodianV5_Ashlar_Height.png'), 'sourceCmPerPx': cm_per_px}


def periodic_noise(rng, n, sigma_px_xy):
    """Gaussian-filtered white noise on a periodic n x n domain, unit std. sigma in px (x, y)."""
    w = rng.standard_normal((n, n))
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    sx, sy = sigma_px_xy
    g = np.exp(-2.0 * (np.pi ** 2) * ((fx * sx) ** 2 + (fy * sy) ** 2))
    out = np.real(np.fft.ifft2(np.fft.fft2(w) * g))
    out -= out.mean()
    return out / (out.std() + 1e-12)


def build_tone(layout, rng):
    P_ = PARAMS
    beds = layout['bedsCm']
    joints = layout['jointsCmPerCourse']
    ncourse = len(joints)
    tiles_u = int(round(TONE_U_CM / TILE_CM))
    tiles_v = int(round(TONE_V_CM / TILE_CM))
    total_courses = tiles_v * ncourse
    # course-run tone (periodic over the 48 courses of the map)
    course_tone = np.zeros(total_courses)
    i = 0
    while i < total_courses:
        run = int(rng.choice(P_['courseRunLengths']))
        val = float(np.exp(rng.normal(0, P_['courseToneSigma'])))
        for j in range(run):
            if i + j < total_courses:
                course_tone[i + j] = val * float(np.exp(rng.normal(0, 0.008)))
        i += run
    fam_names = list(P_['families'].keys())
    fam_p = np.array([P_['families'][f][0] for f in fam_names])
    fam_rgb = np.array([P_['families'][f][1] for f in fam_names])
    stone_tables = []
    stats = {'families': {f: 0 for f in fam_names}, 'rareDark': 0, 'rareLight': 0, 'stones': 0}
    for gc in range(total_courses):
        ns = tiles_u * len(joints[gc % ncourse])
        tab = np.zeros((ns, 6))
        for s in range(ns):
            v = float(np.exp(rng.normal(0, P_['stoneToneSigma'])))
            roll = rng.random()
            if roll < P_['rareDarkChance']:
                v *= P_['rareDark']
                stats['rareDark'] += 1
            elif roll < P_['rareDarkChance'] + P_['rareLightChance']:
                v *= P_['rareLight']
                stats['rareLight'] += 1
            fi = int(rng.choice(len(fam_names), p=fam_p))
            stats['families'][fam_names[fi]] += 1
            stats['stones'] += 1
            rgb = fam_rgb[fi] * v * course_tone[gc]
            tab[s, 0:3] = rgb
            tab[s, 3] = rng.uniform(-1, 1) * P_['stoneGradient']
            tab[s, 4] = rng.uniform(-1, 1) * P_['stoneGradient']
        stone_tables.append(tab)

    cmpp_u = TONE_U_CM / TONE_W
    cmpp_v = TONE_V_CM / TONE_H
    x = (np.arange(TONE_W) + 0.5) * cmpp_u           # u in cm
    img = np.zeros((TONE_H, TONE_W, 3), dtype=np.float32)
    margin = P_['marginCm']
    mf = P_['marginFactor']
    for row in range(TONE_H):
        z = (row + 0.5) * cmpp_v                      # world Z mod period, image row 0 = v 0 (image down = world up)
        tile_row = int(z // TILE_CM)
        zl = z - tile_row * TILE_CM
        k = 0
        while k < ncourse - 1 and zl >= beds[k + 1]:
            k += 1
        gc = tile_row * ncourse + k
        js = np.array(joints[k])
        nb = len(js)
        # stone index along u: count of joints at or before x (periodic key)
        cnt = np.zeros(TONE_W, dtype=np.int64)
        prev = np.full(TONE_W, -1e9)
        nxt = np.full(TONE_W, 1e9)
        for jx in js:
            q = np.floor((x - jx) / TILE_CM)
            cnt += (q + 1).astype(np.int64)
            last = jx + q * TILE_CM                    # joint at or before x
            prev = np.maximum(prev, last)
            nxt = np.minimum(nxt, last + TILE_CM)
        sid = np.mod(cnt, tiles_u * nb)
        tab = stone_tables[gc]
        rgb = tab[sid, 0:3]
        dl = x - prev
        dr = nxt - x
        L = nxt - prev
        db = zl - beds[k]
        dt = beds[k + 1] - zl
        H = beds[k + 1] - beds[k]
        grad = 1.0 + tab[sid, 3] * ((dl / L) - 0.5) * 2.0 + tab[sid, 4] * ((db / H) - 0.5) * 2.0
        f = np.ones(TONE_W)
        ramp = lambda d, w: np.clip((d - w) / 1.9 + 1.0, 0.0, 1.0)   # 0 inside the margin, 1 on the boss, 1.9 cm bevel
        side = np.minimum(ramp(dl, margin['left']), ramp(dr, margin['right']))
        f = f * (mf['side'] + (1 - mf['side']) * side)
        if db < margin['bottom'] + 1.9:
            f = f * (mf['bottom'] + (1 - mf['bottom']) * float(np.clip((db - margin['bottom']) / 1.9 + 1.0, 0, 1)))
        if dt < margin['top'] + 1.9:
            f = f * (mf['top'] + (1 - mf['top']) * float(np.clip((dt - margin['top']) / 1.9 + 1.0, 0, 1)))
        jw = P_['jointHalfWidthCm']
        jv = np.minimum(dl, dr)
        f = np.where(jv < jw, f * P_['jointFactor'], f)
        if min(db, dt) < jw:
            f = f * P_['jointFactor']
        img[row] = (rgb * (grad * f)[:, None]).astype(np.float32)
    lum = img @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    img *= P_['toneMeanTarget'] / float(lum.mean())
    return img, course_tone, stats


def periodic_noise_rect(rng, h, w, sigma_px_xy):
    """Gaussian-filtered white noise on a periodic h x w domain, unit std. sigma in px (x, y)."""
    n = rng.standard_normal((h, w))
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    sx, sy = sigma_px_xy
    g = np.exp(-2.0 * (np.pi ** 2) * ((fx * sx) ** 2 + (fy * sy) ** 2))
    out = np.real(np.fft.ifft2(np.fft.fft2(n) * g))
    out -= out.mean()
    return (out / (out.std() + 1e-12)).astype(np.float32)


def build_tone_v4(layout, rng):
    """V4 (cp20): one-quarry tone. Same joints as the close tile; small per-stone spread; merged joints; the drafted
    margin as a thin bevel light/shadow; stone-interior mottle; broad quarry-batch patches. See the V4 note above."""
    P_ = PARAMS
    beds = layout['bedsCm']
    joints = layout['jointsCmPerCourse']
    ncourse = len(joints)
    tiles_u = int(round(TONE_U_CM / TILE_CM))
    tiles_v = int(round(TONE_V_CM / TILE_CM))
    total_courses = tiles_v * ncourse
    course_tone = np.zeros(total_courses)
    i = 0
    while i < total_courses:
        run = int(rng.choice(P_['courseRunLengths']))
        val = float(np.exp(rng.normal(0, P_['courseToneSigma'])))
        for j in range(run):
            if i + j < total_courses:
                course_tone[i + j] = val * float(np.exp(rng.normal(0, 0.004)))
        i += run
    fam_names = list(P_['families'].keys())
    fam_p = np.array([P_['families'][f][0] for f in fam_names])
    fam_rgb = np.array([P_['families'][f][1] for f in fam_names])
    stats = {'families': {f: 0 for f in fam_names}, 'rareLight': 0, 'stones': 0, 'mergedJoints': 0, 'joints': 0,
             'lengthCmHistogram': {}}
    tables, merged = [], []
    for gc in range(total_courses):
        k = gc % ncourse
        js = joints[k]
        ns = tiles_u * len(js)
        tab = np.zeros((ns, 5))
        mg = np.zeros(ns, dtype=bool)
        run = 0
        for s in range(ns):
            stats['joints'] += 1
            if s > 0 and run < P_['mergeMaxRun'] and rng.random() < P_['mergeChance']:
                mg[s] = True
                tab[s] = tab[s - 1]
                run += 1
                stats['mergedJoints'] += 1
                continue
            run = 0
            v = float(np.exp(rng.normal(0, P_['stoneToneSigma'])))
            if rng.random() < P_['rareLightChance']:
                v *= P_['rareLight']
                stats['rareLight'] += 1
            fi = int(rng.choice(len(fam_names), p=fam_p))
            stats['families'][fam_names[fi]] += 1
            stats['stones'] += 1
            tab[s, 0:3] = fam_rgb[fi] * v * course_tone[gc]
            tab[s, 3] = 0.0                                           # no along-course gradient (merges stay seamless)
            tab[s, 4] = rng.uniform(-1, 1) * P_['stoneGradient']
        # stone lengths after merging, for the manifest (one course of the period)
        widths = [((js[(s + 1) % len(js)] - js[s % len(js)]) % TILE_CM) or TILE_CM for s in range(ns)]
        cur = None
        for s in range(ns):
            if mg[s] and cur is not None:
                cur += widths[s]
            else:
                if cur is not None:
                    key = str(int(round(cur / 100.0) * 100))
                    stats['lengthCmHistogram'][key] = stats['lengthCmHistogram'].get(key, 0) + 1
                cur = widths[s]
        tables.append(tab)
        merged.append(mg)

    cmpp_u = TONE_U_CM / TONE_W
    cmpp_v = TONE_V_CM / TONE_H
    mo = P_['mottle']
    mottle = np.exp(periodic_noise_rect(rng, TONE_H, TONE_W, (mo['fineSigmaCm'] / cmpp_u, mo['fineSigmaCm'] / cmpp_v)) * mo['fineStd']
                    + periodic_noise_rect(rng, TONE_H, TONE_W, (mo['midSigmaCm'] / cmpp_u, mo['midSigmaCm'] / cmpp_v)) * mo['midStd'])
    ba = P_['batch']
    batch = np.exp(periodic_noise_rect(rng, TONE_H, TONE_W, (ba['sigmaCm'] / cmpp_u, ba['sigmaCm'] / cmpp_v)) * ba['std'])
    x = (np.arange(TONE_W) + 0.5) * cmpp_u
    img = np.zeros((TONE_H, TONE_W, 3), dtype=np.float32)
    margin = P_['marginCm']
    mf = P_['marginFactor']
    bev = P_['bevelCm']
    bs, bl = P_['bevelShadow'], P_['bevelLight']
    jw = P_['jointHalfWidthCm']
    ramp = lambda d, w: np.clip((d - w) / 1.9 + 1.0, 0.0, 1.0)
    for row in range(TONE_H):
        z = (row + 0.5) * cmpp_v
        tile_row = int(z // TILE_CM)
        zl = z - tile_row * TILE_CM
        k = 0
        while k < ncourse - 1 and zl >= beds[k + 1]:
            k += 1
        gc = tile_row * ncourse + k
        js = np.array(joints[k])
        nb = len(js)
        cnt = np.zeros(TONE_W, dtype=np.int64)
        prev = np.full(TONE_W, -1e9)
        nxt = np.full(TONE_W, 1e9)
        for jx in js:
            q = np.floor((x - jx) / TILE_CM)
            cnt += (q + 1).astype(np.int64)
            last = jx + q * TILE_CM
            prev = np.maximum(prev, last)
            nxt = np.minimum(nxt, last + TILE_CM)
        N = tiles_u * nb
        sid = np.mod(cnt, N)
        tab = tables[gc]
        mL = merged[gc][sid]
        mR = merged[gc][np.mod(sid + 1, N)]
        dl = x - prev
        dr = nxt - x
        ldist = np.where(mL, 1e9, dl)
        rdist = np.where(mR, 1e9, dr)
        db = zl - beds[k]
        dt = beds[k + 1] - zl
        H = beds[k + 1] - beds[k]
        grad = 1.0 + tab[sid, 4] * ((db / H) - 0.5) * 2.0
        f = np.ones(TONE_W)
        side = np.minimum(ramp(ldist, margin['left']), ramp(rdist, margin['right']))
        f = f * (mf['side'] + (1 - mf['side']) * side)
        if db < margin['bottom'] + 1.9:
            f = f * (mf['bottom'] + (1 - mf['bottom']) * float(np.clip((db - margin['bottom']) / 1.9 + 1.0, 0, 1)))
        if dt < margin['top'] + 1.9:
            f = f * (mf['top'] + (1 - mf['top']) * float(np.clip((dt - margin['top']) / 1.9 + 1.0, 0, 1)))
        # thin bevel line at the boss edge: light along the top, shadow along the bottom and the sides
        on_boss_h = (ldist > margin['left']) & (rdist > margin['right'])
        on_boss_v = (db > margin['bottom']) and (dt > margin['top'])
        if margin['bottom'] <= db < margin['bottom'] + bev:
            f = np.where(on_boss_h, f * bs['bottom'], f)
        if margin['top'] <= dt < margin['top'] + bev:
            f = np.where(on_boss_h, f * bl['top'], f)
        if on_boss_v:
            sb = ((ldist >= margin['left']) & (ldist < margin['left'] + bev)) | ((rdist >= margin['right']) & (rdist < margin['right'] + bev))
            f = np.where(sb, f * bs['side'], f)
        # joints: tight dry joints, soft; a merged joint is almost invisible
        f = np.where(np.minimum(ldist, rdist) < jw, f * P_.get('vertJointFactor', P_['jointFactor']), f)
        f = np.where((mL & (dl < jw)) | (mR & (dr < jw)), f * P_['mergedJointFactor'], f)
        if min(db, dt) < jw:
            f = f * P_['jointFactor']
        img[row] = (tab[sid, 0:3] * (grad * f * mottle[row] * batch[row])[:, None]).astype(np.float32)
    lum = img @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    img *= P_['toneMeanTarget'] / float(lum.mean())
    return img, course_tone, stats





# ======================================================================================================================
# --variant V6 (cp25, 11 Sep, after the cp20b three-panel against the Western Wall). cp20b's tone sat inside the Western
# Wall's range, but the face still read as an EVEN BRICK GRID. Measured on the Western Wall photo (same segmentation as
# accept_precinct_cp20.kotel_reference): course-height CV 0.136 with 4 % of courses over 1.5x the median; stone
# length/height median 1.04 (p95 2.35) - near-square blocks; intra-stone log std 0.105 at 3.14 cm/px - rough faces.
# Ours: every course 92-106 cm, stones 1.4-9 m long strips (V4/V5 merged a third of vertical joints), smooth fields,
# bed-joint dip 0.081 against 0.144.
# V6 draws its OWN Herodian layout, constrained so the close tile's joints still coincide wherever they exist:
#   * courses: every macro bed is one of the close tile's beds (0 / 101.52 / 193.56 per 300 cm). Tall courses are
#     MERGES of 2 (193.6-208.0 cm) or 3 (300 cm) close courses. No merge crosses a batter-ledge bed (world Z = -1200k,
#     i.e. every 4th tile row). In the crossover band the close tile still draws the merged bed faintly: that ghost is
#     measured in frames (accept_precinct_cp25.py), not assumed hidden.
#   * stones: single courses keep the close joints, merge few, and SPLIT long stones at random positions (macro-only
#     joints) so blocks run near-square as on the Western Wall; tall courses get their own random joint walk, snapped to
#     a close joint when one lies within 25 cm. Random positions also keep the 3 m repeat broken.
#   * relief: a per-stone height field in cm - boss proud on a drafted margin, eroded irregular arrises, pitting and
#     weathered boss faces by stone class, deep joints. From it: T_PrecinctMacro_Relief<variant> (R,G = -dH/du, -dH/dv
#     encoded 0.5 + g/4; B = sky-visibility x cavity AO), sampled by M_PrecinctMacroV4_Triplanar as a far-field normal
#     and AO; and the tone map with that occlusion partly baked in, so the joint shadow reads under any sun. Both are the
#     macro's own fixed textures: nothing depends on a low mip of the close tile.
V6_BASE = {
    'tall': {'doubles': 3, 'triples': 1, 'minSinglesBetween': 2},
    # the repeat: keeping ~90 % of the close tile's joints (drawn dark) brought the 3 m tile back (offline +0.09 at
    # the 300 cm lag vs V5 -0.05). About half are dropped and the long stones re-cut at random positions instead.
    'singleMergeChance': 0.35, 'mergeMaxLenOverHeight': 4.2, 'splitOverHeight': 1.7, 'splitChance': 0.75,
    'splitMidChance': 0.15, 'splitFraction': [0.36, 0.64], 'splitPieceOverHeight': [0.8, 1.7],
    'tallLengthOverHeight': {'2': [1.0, 2.3], '3': [1.1, 2.4]}, 'snapCm': 25.0,
    'stoneToneSigma': 0.062, 'courseToneSigma': 0.010, 'batch': {'sigmaCm': 450.0, 'std': 0.010},
    'rarePale': [0.04, 1.10], 'rareDark': [0.04, 0.89],
    'families': {'base': [0.50, [1.0, 1.0, 1.0]], 'honey': [0.25, [1.045, 1.0, 0.90]],
                 'cream': [0.15, [1.03, 1.025, 0.99]], 'greygold': [0.10, [0.975, 0.99, 1.03]]},
    'warm': [1.02, 1.0, 0.96],
    # stone classes: share, surface relief amplitude cm, arris erosion cm
    'classes': {'dressed': [0.25, 0.30, 0.7], 'weathered': [0.55, 0.85, 1.5], 'eroded': [0.20, 1.9, 3.2]},
    'faceOffsetSigmaCm': 0.8, 'erodedRecessCm': 1.2,
    'bossProudCm': [2.5, 4.5], 'bevelCm': 2.6,
    'marginCm': {'bottom': [7.5, 10.5], 'side': [8.0, 12.0], 'top': [10.0, 14.0]},
    'jointHalfWidthCm': 0.9, 'jointDepthCm': 6.5,
    # rough faces: the Western Wall reads 0.105 intra-stone log std at 3.14 cm/px; the first draft baked 0.040
    'mottle': {'fineSigmaCm': 6.0, 'fineStd': 0.05, 'midSigmaCm': 24.0, 'midStd': 0.045},
    'surfaceToneGain': 0.085,
    'skyOcclusionReachCm': 28.0, 'skyOcclusionGain': 0.75, 'cavitySigmaCm': 8.0, 'cavityGain': 0.10, 'aoFloor': 0.22,
    # baked share of the joint shadow: offline dip ~0.11 so the engine's own normal/AO lighting can carry the rest
    'bakeAO': 0.55, 'bakeDirectional': 0.10, 'jointToneFactor': 0.85,
    'patina': {'sigmaCm': 90.0, 'threshold': 0.7, 'rgb': [1.05, 0.985, 0.90], 'amount': 0.8},
    'plants': {'count': 36, 'radiusCm': [30.0, 65.0], 'rgb': [0.34, 0.40, 0.24], 'bumpCm': 7.0},
    'voids': {'count': 18, 'sizeCm': [12.0, 30.0]},
    'toneMeanTarget': 0.97,
}
# V6/V6b/V6c swept the close-joint keep share (offline 300 cm proxy -0.023 / -0.016 / -0.002; V5 -0.052): not the driver.
# Stones of ~1.4 m made the joint train quasi-periodic (300 cm = two stones). V6d/V6e widen the length spread and make
# vertical joints narrower and less eroded than beds (the Western Wall reads in horizontal courses).
V6_TWEAKS = {'V6': {}, 'V6b': {'singleMergeChance': 0.5}, 'V6c': {'singleMergeChance': 0.2},
             'V6d': {'stoneToneSigma': 0.055, 'splitPieceOverHeight': [0.6, 2.1], 'surfaceToneGain': 0.10,
                     'vertJointHalfWidthCm': 0.6, 'vertArrisFactor': 0.6},
             'V6e': {'stoneToneSigma': 0.055, 'splitPieceOverHeight': [0.6, 2.1], 'surfaceToneGain': 0.10,
                     'vertJointHalfWidthCm': 0.45, 'vertArrisFactor': 0.4, 'tallLengthOverHeight': {'2': [0.9, 2.6], '3': [1.0, 2.8]}}}


def v6_params(variant):
    p = json.loads(json.dumps(V6_BASE))
    for k, v in V6_TWEAKS.get(variant, {}).items():
        if isinstance(v, dict) and isinstance(p.get(k), dict):
            p[k].update(v)
        else:
            p[k] = v
    return p


def _v6_filter(F, shape, sigma_cm):
    c = TONE_U_CM / TONE_W
    fy = np.fft.fftfreq(shape[0])[:, None]
    fx = np.fft.rfftfreq(shape[1])[None, :]
    s = sigma_cm / c
    F *= np.exp(-2.0 * (np.pi ** 2) * (s ** 2) * (fx ** 2 + fy ** 2))
    return F


def v6_noise(rng, sigma_cm):
    """Periodic gaussian-filtered noise over the tone period, unit std, float32 (rfft to spare the 32-bit heap)."""
    n = rng.standard_normal((TONE_H, TONE_W)).astype(np.float32)
    F = _v6_filter(np.fft.rfft2(n), n.shape, sigma_cm)
    del n
    out = np.fft.irfft2(F, s=(TONE_H, TONE_W)).astype(np.float32)
    del F
    out -= out.mean()
    out /= (out.std() + 1e-12)
    return out


def v6_blur(a, sigma_cm):
    F = _v6_filter(np.fft.rfft2(a), a.shape, sigma_cm)
    return np.fft.irfft2(F, s=a.shape).astype(np.float32)


def _pdist(a, b):
    d = abs(a - b) % TONE_U_CM
    return min(d, TONE_U_CM - d)


def v6_layout(layout, rng, P_):
    beds = layout['bedsCm']
    cj = layout['jointsCmPerCourse']
    nc = len(cj)
    tiles_u = int(round(TONE_U_CM / TILE_CM))
    tiles_v = int(round(TONE_V_CM / TILE_CM))
    total = tiles_v * nc
    courses = [(tr * TILE_CM + beds[k], tr * TILE_CM + beds[k + 1], k) for tr in range(tiles_v) for k in range(nc)]
    ledge = {nc * tr for tr in range(0, tiles_v, 4)}        # course whose BOTTOM bed is a batter ledge (world Z -1200k)
    sizes = [3] * P_['tall']['triples'] + [2] * P_['tall']['doubles']
    taken = [False] * total
    starts = {}
    gap = P_['tall']['minSinglesBetween']
    for size in sizes:
        for _try in range(4000):
            g0 = int(rng.integers(0, total - size + 1))
            if any((g0 + i) in ledge for i in range(1, size)):
                continue
            if any(taken[max(0, g0 - gap):min(total, g0 + size + gap)]):
                continue
            for i in range(size):
                taken[g0 + i] = True
            starts[g0] = size
            break
        else:
            raise RuntimeError('could not place a tall course of %d' % size)
    units = []
    g = 0
    while g < total:
        size = starts.get(g, 1)
        units.append({'courses': list(range(g, g + size)), 'z0': courses[g][0], 'z1': courses[g + size - 1][1],
                      'k': [courses[g + i][2] for i in range(size)]})
        g += size
    stats = {'units': len(units), 'tall': {'2': sizes.count(2), '3': sizes.count(3)}, 'closeJoints': 0,
             'macroOnlyJoints': 0, 'mergedCloseJoints': 0}
    for u in units:
        H = u['z1'] - u['z0']
        u['heightCm'] = round(H, 2)
        union = sorted({round(t * TILE_CM + j, 3) for k in u['k'] for t in range(tiles_u) for j in cj[k]})
        js = []
        if len(u['k']) == 1:
            base = [(x, 'close') for x in union]
            kept = []
            prev_dropped = False
            for i, (x, t) in enumerate(base):
                xl = base[i - 1][0] - (TONE_U_CM if i == 0 else 0.0)
                xr = base[(i + 1) % len(base)][0] + (TONE_U_CM if i == len(base) - 1 else 0.0)
                if not prev_dropped and (xr - xl) < P_['mergeMaxLenOverHeight'] * H and rng.random() < P_['singleMergeChance']:
                    prev_dropped = True
                    stats['mergedCloseJoints'] += 1
                    continue
                prev_dropped = False
                kept.append((x, t))
            out = []
            for i, (x, t) in enumerate(kept):
                out.append((x, t))
                xn = kept[(i + 1) % len(kept)][0] + (TONE_U_CM if i == len(kept) - 1 else 0.0)
                L = xn - x
                pch = P_['splitChance'] if L > P_['splitOverHeight'] * H else (P_['splitMidChance'] if L > 1.25 * H else 0.0)
                if pch and rng.random() < pch:
                    # walk the stone in near-square pieces at random positions (macro-only joints)
                    lo, hi = P_['splitPieceOverHeight']
                    p = x
                    while (x + L) - p > (hi + 0.4) * H:
                        p += rng.uniform(lo, hi) * H
                        out.append((p % TONE_U_CM, 'macro'))
                    if (x + L) - p > P_['splitOverHeight'] * H:
                        out.append(((p + ((x + L) - p) * rng.uniform(*P_['splitFraction'])) % TONE_U_CM, 'macro'))
            js = out
        else:
            lo, hi = P_['tallLengthOverHeight'][str(len(u['k']))]
            x0 = float(rng.uniform(0, TONE_U_CM))
            p = x0
            end = x0 + TONE_U_CM
            js.append((x0 % TONE_U_CM, 'macro'))
            while True:
                L = rng.uniform(lo, hi) * H
                rem = end - p
                if rem - L < lo * H:
                    if rem > hi * H * 1.15:
                        L = rem / 2.0
                    else:
                        break
                q = p + L
                near = [c for c in union if _pdist(c, q) < P_['snapCm']]
                if near:
                    c = min(near, key=lambda c: _pdist(c, q))
                    q += ((c - q + TONE_U_CM / 2) % TONE_U_CM) - TONE_U_CM / 2
                    js.append((q % TONE_U_CM, 'close'))
                else:
                    js.append((q % TONE_U_CM, 'macro'))
                p = q
        js.sort()
        u['joints'] = [round(x, 3) for x, _t in js]
        u['jointKind'] = [t for _x, t in js]
        stats['closeJoints'] += u['jointKind'].count('close')
        stats['macroOnlyJoints'] += u['jointKind'].count('macro')
    ratios = []
    for u in units:
        J = u['joints']
        for i in range(len(J)):
            L = (J[(i + 1) % len(J)] - J[i]) % TONE_U_CM or TONE_U_CM
            ratios.append(L / u['heightCm'])
    stats['lengthOverHeight'] = {'p05': round(float(np.percentile(ratios, 5)), 2), 'p50': round(float(np.median(ratios)), 2),
                                 'p95': round(float(np.percentile(ratios, 95)), 2), 'n': len(ratios)}
    uh = np.array([u['heightCm'] for u in units])
    stats['unitHeightCm'] = {'cv': round(float(uh.std() / np.median(uh)), 3),
                             'fracOver1p5xMedian': round(float((uh > 1.5 * np.median(uh)).mean()), 3),
                             'heights': sorted(set(round(float(h), 1) for h in uh))}
    return units, stats


def build_tone_v6(layout, rng, variant):
    """V6 (cp25): own Herodian layout on the close beds, height-field relief, baked sky occlusion. See the V6 note."""
    P_ = v6_params(variant)
    units, lstats = v6_layout(layout, rng, P_)
    c = TONE_U_CM / TONE_W
    X = ((np.arange(TONE_W) + 0.5) * c).astype(np.float64)
    Zr = (np.arange(TONE_H) + 0.5) * c
    sid = np.zeros((TONE_H, TONE_W), dtype=np.int32)
    dl = np.zeros((TONE_H, TONE_W), dtype=np.float32)
    dr = np.zeros_like(dl)
    db = np.zeros_like(dl)
    dt = np.zeros_like(dl)
    offset = 0
    for ui, u in enumerate(units):
        J = np.array(u['joints'], dtype=np.float64)
        n = len(J)
        rows = np.where((Zr >= u['z0']) & (Zr < u['z1']))[0]
        idx = np.searchsorted(J, X, side='right') - 1
        left = np.where(idx >= 0, J[np.clip(idx, 0, n - 1)], J[-1] - TONE_U_CM)
        nxt = idx + 1
        right = np.where(nxt < n, J[np.clip(nxt, 0, n - 1)], J[0] + TONE_U_CM)
        loc = np.mod(idx, n)
        sid[rows] = (offset + loc)[None, :]
        dl[rows] = (X - left)[None, :]
        dr[rows] = (right - X)[None, :]
        db[rows] = (Zr[rows] - u['z0'])[:, None]
        dt[rows] = (u['z1'] - Zr[rows])[:, None]
        u['stoneOffset'] = offset
        offset += n
    ns = offset
    # ---- per-stone attributes
    fam_names = list(P_['families'])
    fam_p = np.array([P_['families'][f][0] for f in fam_names])
    fam_rgb = np.array([P_['families'][f][1] for f in fam_names])
    cls_names = list(P_['classes'])
    cls_p = np.array([P_['classes'][k][0] for k in cls_names])
    course_tone = np.exp(rng.normal(0, P_['courseToneSigma'], len(units)))
    rgb = np.zeros((ns, 3), dtype=np.float32)
    face = np.zeros(ns, dtype=np.float32)
    proud = np.zeros(ns, dtype=np.float32)
    relief = np.zeros(ns, dtype=np.float32)
    arris = np.zeros(ns, dtype=np.float32)
    mL = np.zeros(ns, dtype=np.float32)
    mR = np.zeros_like(mL)
    mB = np.zeros_like(mL)
    mT = np.zeros_like(mL)
    counts = {'families': {f: 0 for f in fam_names}, 'classes': {k: 0 for k in cls_names}, 'pale': 0, 'dark': 0}
    for ui, u in enumerate(units):
        for s in range(u['stoneOffset'], u['stoneOffset'] + len(u['joints'])):
            v = float(np.exp(rng.normal(0, P_['stoneToneSigma'])))
            r = rng.random()
            if r < P_['rarePale'][0]:
                v *= P_['rarePale'][1]
                counts['pale'] += 1
            elif r < P_['rarePale'][0] + P_['rareDark'][0]:
                v *= P_['rareDark'][1]
                counts['dark'] += 1
            fi = int(rng.choice(len(fam_names), p=fam_p))
            counts['families'][fam_names[fi]] += 1
            ci = int(rng.choice(len(cls_names), p=cls_p))
            counts['classes'][cls_names[ci]] += 1
            rgb[s] = fam_rgb[fi] * v * course_tone[ui] * np.array(P_['warm'])
            _share, amp, ar = P_['classes'][cls_names[ci]]
            eroded = cls_names[ci] == 'eroded'
            relief[s] = amp * rng.uniform(0.7, 1.3)
            arris[s] = ar * rng.uniform(0.7, 1.3)
            face[s] = float(np.clip(rng.normal(0, P_['faceOffsetSigmaCm']), -2.0, 2.0)) - (P_['erodedRecessCm'] if eroded else 0.0)
            proud[s] = rng.uniform(*P_['bossProudCm']) * (0.6 if eroded else 1.0)
            mB[s] = rng.uniform(*P_['marginCm']['bottom'])
            mT[s] = rng.uniform(*P_['marginCm']['top'])
            mL[s] = rng.uniform(*P_['marginCm']['side'])
            mR[s] = rng.uniform(*P_['marginCm']['side'])
    # ---- height field (cm, 0 = nominal face plane)
    Nm = v6_noise(rng, 20.0)
    md = np.minimum(np.minimum(dl - mL[sid], dr - mR[sid]), np.minimum(db - mB[sid], dt - mT[sid])) + 0.8 * Nm
    del Nm
    dv_edge = np.minimum(dl, dr)
    dh_edge = np.minimum(db, dt)
    del dl, dr, db, dt
    En = v6_noise(rng, 12.0)
    e = arris[sid] * np.clip(0.45 + 0.55 * En, 0.0, 2.2)
    del En
    # vertical joints may be narrower and less eroded than beds (vertJointHalfWidthCm / vertArrisFactor)
    jwv = P_.get('vertJointHalfWidthCm', P_['jointHalfWidthCm'])
    vaf = P_.get('vertArrisFactor', 1.0)
    de = np.minimum(dh_edge - e, dv_edge - vaf * e + (P_['jointHalfWidthCm'] - jwv))
    del dv_edge, dh_edge
    s = np.clip(md / P_['bevelCm'], 0.0, 1.0)
    del md
    s = s * s * (3.0 - 2.0 * s)
    Nsurf = 0.55 * v6_noise(rng, 4.0)
    Nsurf += 0.8 * v6_noise(rng, 14.0)
    Nsurf += 0.5 * v6_noise(rng, 40.0)
    pit = np.clip(v6_noise(rng, 2.2) - 1.8, 0.0, None) * 2.5
    amp = relief[sid]
    H = face[sid] + proud[sid] * s + amp * (Nsurf * (0.35 + 0.65 * s)) - amp * pit
    del pit, s
    jw = P_['jointHalfWidthCm']
    R = 1.8 + 0.8 * e
    t = np.clip((de - jw) / R, 0.0, 1.0)
    H -= (1.5 + 0.6 * e) * (1.0 - t) ** 2
    del t, R, e
    joint = de < jw
    del de
    H = np.where(joint, np.float32(-P_['jointDepthCm']), H).astype(np.float32)
    # ---- incidental life: plants in joints (dome + dark olive) and a few open voids at joints
    plant_mask = np.zeros((TONE_H, TONE_W), dtype=np.float32)
    Nb = v6_noise(rng, 10.0)
    Nf = v6_noise(rng, 3.0)
    placed = []
    pl = P_['plants']
    vo = P_['voids']
    for kind, count in (('plant', pl['count']), ('void', vo['count'])):
        for _i in range(count):
            u = units[int(rng.integers(1, len(units)))]
            J = u['joints']
            jx = J[int(rng.integers(0, len(J)))]
            cx, cz = jx + rng.uniform(-15, 15), u['z0'] + rng.uniform(-8, 8)
            placed.append([kind, round(float(cx), 1), round(float(cz), 1)])
            rad = rng.uniform(*(pl['radiusCm'] if kind == 'plant' else vo['sizeCm']))
            rp = int(rad * 1.8 / c) + 3
            ci, ri = int(cx / c), int(cz / c)
            rr = np.arange(ri - rp, ri + rp) % TONE_H
            cc = np.arange(ci - rp, ci + rp) % TONE_W
            ix = np.ix_(rr, cc)
            gx = (np.arange(ci - rp, ci + rp) + 0.5) * c - cx
            gz = (np.arange(ri - rp, ri + rp) + 0.5) * c - cz
            GX, GZ = np.meshgrid(gx, gz)
            if kind == 'plant':
                GZs = np.where(GZ < 0, GZ / 1.45, GZ * 1.1)          # tufts hang downward
                dist = np.sqrt(GX ** 2 + GZs ** 2)
                edge = rad * (1.0 + 0.35 * Nb[ix])
                m = np.clip((edge - dist) / 7.0, 0.0, 1.0) * np.clip(0.75 + 0.5 * Nf[ix], 0.0, 1.0)
                plant_mask[ix] = np.maximum(plant_mask[ix], m)
                dome = pl['bumpCm'] * np.clip(1.0 - dist / edge, 0.0, 1.0) ** 0.5 * (0.7 + 0.3 * Nf[ix])
                h0 = H[ix]
                H[ix] = np.where(m > 0.05, np.maximum(h0, h0 + dome), h0)
            else:
                m = (np.abs(GX) < rad * 0.6) & (np.abs(GZ) < rad * 0.45)
                H[ix] = np.where(m, np.float32(-P_['jointDepthCm'] * 1.3), H[ix])
                joint[ix] = joint[ix] | m
    del Nb
    # ---- slopes, sky visibility (upward horizon), cavity AO
    dHdu = (np.roll(H, -1, axis=1) - np.roll(H, 1, axis=1)) / np.float32(2.0 * c)
    dHdv = (np.roll(H, -1, axis=0) - np.roll(H, 1, axis=0)) / np.float32(2.0 * c)     # row + 1 = world up
    horizon = np.zeros_like(H)
    for k in range(1, int(P_['skyOcclusionReachCm'] / c) + 1):
        np.maximum(horizon, (np.roll(H, -k, axis=0) - H) / np.float32(k * c), out=horizon)
    sky = 1.0 - P_['skyOcclusionGain'] * (np.arctan(horizon) / (np.pi / 2.0))
    del horizon
    cav = np.clip(1.0 - P_['cavityGain'] * np.maximum(0.0, v6_blur(H, P_['cavitySigmaCm']) - H), 0.0, 1.0)
    ao = np.clip(sky * cav, P_['aoFloor'], 1.0).astype(np.float32)
    del sky, cav
    # ---- tone
    mo = P_['mottle']
    shade = np.exp(v6_noise(rng, mo['fineSigmaCm']) * mo['fineStd'])
    shade *= np.exp(v6_noise(rng, mo['midSigmaCm']) * mo['midStd'])
    shade *= np.exp(v6_noise(rng, P_['batch']['sigmaCm']) * P_['batch']['std'])
    shade *= np.exp(P_['surfaceToneGain'] * Nsurf * np.clip(amp / 0.85, 0.3, 2.2))
    del Nsurf, amp
    shade *= (1.0 - P_['bakeAO']) + P_['bakeAO'] * ao
    shade *= 1.0 - P_['bakeDirectional'] * np.clip(dHdv, -1.5, 1.5)
    shade = np.where(joint, shade * P_['jointToneFactor'], shade).astype(np.float32)
    img = rgb[sid]
    del sid
    img *= shade[..., None]
    del shade
    pa = P_['patina']
    pm = np.clip((v6_noise(rng, pa['sigmaCm']) - pa['threshold']) / 0.8, 0.0, 1.0) * pa['amount']
    for ch in range(3):
        img[..., ch] *= (1.0 + (pa['rgb'][ch] - 1.0) * pm)
    del pm
    pf = (0.8 + 0.25 * Nf) * (0.55 + 0.45 * ao)
    for ch in range(3):
        img[..., ch] = img[..., ch] * (1.0 - plant_mask) + pl['rgb'][ch] * pf * plant_mask
    del pf, Nf
    lum = img @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    img *= P_['toneMeanTarget'] / float(lum.mean())
    del lum
    rel = np.stack([np.clip(0.5 - dHdu / 4.0, 0, 1), np.clip(0.5 - dHdv / 4.0, 0, 1), ao], axis=-1).astype(np.float32)
    lstats.update(counts)
    lstats['stones'] = ns
    lstats['incidental'] = placed
    lstats['heightCm'] = {'p01': float(np.percentile(H[::4, ::4], 1)), 'p50': float(np.median(H[::4, ::4])),
                          'p99': float(np.percentile(H[::4, ::4], 99))}
    lstats['aoMean'] = float(ao.mean())
    lstats['plantPixelFraction'] = float((plant_mask > 0.5).mean())
    layout_out = [{'z0': round(u['z0'], 3), 'z1': round(u['z1'], 3), 'closeCourses': u['courses'], 'joints': u['joints'],
                   'jointKind': u['jointKind']} for u in units]
    return img, rel, course_tone, lstats, layout_out, P_


def main_v6():
    t0 = time.time()
    rng = np.random.default_rng(SEED + 25)
    layout = measure_layout()
    tone, rel, course_tone, stats, units, P_ = build_tone_v6(layout, rng, VARIANT)
    tone_png = OUT / ('T_PrecinctMacro_Tone%s.png' % VARIANT)
    rel_png = OUT / ('T_PrecinctMacro_Relief%s.png' % VARIANT)
    Image.fromarray(encode(tone)).save(tone_png, optimize=True)
    Image.fromarray(np.clip(np.round(rel * 255.0), 0, 255).astype(np.uint8)).save(rel_png, optimize=True)
    del rel
    weather = np.asarray(Image.open(OUT / 'T_PrecinctMacro_Weather.png').convert('L'), dtype=np.float32) / 255.0 * 2.0
    alb = np.asarray(Image.open(V5 / 'T_HerodianV5_Ashlar_Albedo.png').convert('RGB'), dtype=np.float32) / 255.0
    close_mean = ((alb ** 2.2).reshape(-1, 3).mean(axis=0)).tolist()
    del alb
    pv = preview(tone, weather, close_mean)
    pv.save(OUT / ('preview%s-full-period-9600x4800cm.png' % VARIANT))
    pv.resize((TONE_W // 16, TONE_H // 16), Image.BOX).resize((TONE_W // 4, TONE_H // 4), Image.NEAREST).save(
        OUT / ('preview%s-far-field-37cm-per-px.png' % VARIANT))
    lum = tone @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    man = {
        'status': 'generated', 'generator': 'Scripts/create_precinct_macro.py', 'variant': VARIANT, 'seed': SEED + 25,
        'params': P_,
        'convention': 'u = world X|Y / 9600 cm, v = world Z / 4800 cm; image row 0 is v = 0 (image down = world up); '
                      'tone: value 0.5 = multiplier 1.0, linear (sRGB off); relief: R = 0.5 - dH/du / 4, '
                      'G = 0.5 - dH/dv / 4 (dH/dv along world up), B = ambient occlusion, linear',
        'tone': {'file': tone_png.name, 'size': [TONE_W, TONE_H], 'tileCm': [TONE_U_CM, TONE_V_CM],
                 'cmPerPx': TONE_U_CM / TONE_W, 'sha256': sha(tone_png), 'meanLuminanceMultiplier': float(lum.mean()),
                 'p05p95': [float(np.percentile(lum, 5)), float(np.percentile(lum, 95))],
                 'courseTone': [round(float(x), 4) for x in course_tone]},
        'relief': {'file': rel_png.name, 'size': [TONE_W, TONE_H], 'tileCm': [TONE_U_CM, TONE_V_CM], 'sha256': sha(rel_png),
                   'compression': 'TC_BC7'},
        'stats': stats, 'macroLayout': units, 'layoutFromCloseTile': layout, 'closeTileMeanLinearRgb': close_mean,
        'generationSeconds': round(time.time() - t0, 1),
    }
    (OUT / ('manifest-%s.json' % VARIANT)).write_text(json.dumps(man, indent=1), encoding='utf-8')
    print(json.dumps({k: stats[k] for k in stats if k != 'incidental'}, indent=1))
    print('tone', man['tone']['sha256'][:16], 'relief', man['relief']['sha256'][:16], man['generationSeconds'], 's')


def build_weather(rng):
    W = PARAMS['weather']
    n = WEATHER_N
    cmpp = WEATHER_CM / n
    broad = periodic_noise(rng, n, (W['broadSigmaCm'][0] / cmpp, W['broadSigmaCm'][1] / cmpp)) * W['broadStd']
    patch = periodic_noise(rng, n, (W['patchSigmaCm'][0] / cmpp, W['patchSigmaCm'][1] / cmpp)) * W['patchStd']
    streak = periodic_noise(rng, n, (W['streakSigmaCm'][0] / cmpp, W['streakSigmaCm'][1] / cmpp))
    mask = periodic_noise(rng, n, (W['streakMaskSigmaCm'] / cmpp, W['streakMaskSigmaCm'] / cmpp))
    streak = np.minimum(streak, 0.0) * np.clip(mask - 0.3, 0.0, 1.0) * W['streakStd']
    m = np.exp(broad + patch + streak)
    m *= W['meanTarget'] / m.mean()
    return m.astype(np.float32)


def encode(mult):
    return np.clip(np.round(mult / 2.0 * 255.0), 0, 255).astype(np.uint8)


def preview(tone, weather, close_mean_rgb):
    """What a distant face averages to: close-up mean colour x tone x weather, box-downsampled."""
    h, w, _ = tone.shape
    # tile the weather over one tone period in cm
    wy = (np.arange(h) * (TONE_V_CM / h) / (WEATHER_CM / WEATHER_N)).astype(int) % WEATHER_N
    wx = (np.arange(w) * (TONE_U_CM / w) / (WEATHER_CM / WEATHER_N)).astype(int) % WEATHER_N
    wv = weather[wy][:, wx]
    lin = tone * wv[..., None] * np.array(close_mean_rgb, dtype=np.float32)[None, None, :]
    srgb = np.clip(lin, 0, 1) ** (1 / 2.2)
    img = (srgb * 255).astype(np.uint8)[::-1]      # flip so world up is image up for a human
    return Image.fromarray(img)


def main():
    if VARIANT.startswith('V6'):
        return main_v6()          # cp25: own layout + relief pair
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    layout = measure_layout()
    tone, course_tone, stats = (build_tone_v4 if VARIANT in ('V4', 'V5') else build_tone)(layout, rng)
    tone_png = OUT / ('T_PrecinctMacro_Tone%s.png' % SUFFIX)
    weather_png = OUT / 'T_PrecinctMacro_Weather.png'
    Image.fromarray(encode(tone)).save(tone_png, optimize=True)
    if VARIANT == 'V1':
        weather = build_weather(rng)
        wq = encode(weather)
        Image.fromarray(np.stack([wq, wq, wq], axis=-1)).save(weather_png, optimize=True)
    else:
        # the weather map is shared with V1 and already imported; read it, never rewrite it
        weather = np.asarray(Image.open(weather_png).convert('L'), dtype=np.float32) / 255.0 * 2.0
    alb = np.asarray(Image.open(V5 / 'T_HerodianV5_Ashlar_Albedo.png').convert('RGB'), dtype=np.float32) / 255.0
    close_mean = ((alb ** 2.2).reshape(-1, 3).mean(axis=0)).tolist()
    del alb
    pv = preview(tone, weather, close_mean)
    pv.save(OUT / ('preview%s-full-period-9600x4800cm.png' % SUFFIX))
    pv.resize((TONE_W // 16, TONE_H // 16), Image.BOX).resize((TONE_W // 4, TONE_H // 4), Image.NEAREST).save(
        OUT / ('preview%s-far-field-37cm-per-px.png' % SUFFIX))
    lum = tone @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    # course signal that survives a 1 m/px footprint: row profile of the tone map box-filtered to 100 cm
    f = int(round(100.0 / (TONE_U_CM / TONE_W)))
    small = lum[: (TONE_H // f) * f, : (TONE_W // f) * f].reshape(TONE_H // f, f, TONE_W // f, f).mean(axis=(1, 3))
    man = {
        'status': 'generated', 'generator': 'Scripts/create_precinct_macro.py', 'seed': SEED, 'params': PARAMS,
        'convention': 'u = world X|Y / tileUCm, v = world Z / tileVCm; image row 0 is v = 0 (image down = world up); '
                      'value 0.5 = multiplier 1.0, linear (sRGB off)',
        'tone': {'file': tone_png.name, 'size': [TONE_W, TONE_H], 'tileCm': [TONE_U_CM, TONE_V_CM],
                 'cmPerPx': TONE_U_CM / TONE_W, 'closeTilesPerPeriod': [TONE_U_CM / TILE_CM, TONE_V_CM / TILE_CM],
                 'sha256': sha(tone_png), 'meanLuminanceMultiplier': float(lum.mean()),
                 'p05p95': [float(np.percentile(lum, 5)), float(np.percentile(lum, 95))],
                 'at100cmPerPx': {'std': float(small.std()), 'rowProfileStd': float(small.mean(axis=1).std())},
                 'courseTone': [round(float(c), 4) for c in course_tone], 'stoneStats': stats},
        'weather': {'file': weather_png.name, 'size': [WEATHER_N, WEATHER_N], 'tileCm': [WEATHER_CM, WEATHER_CM],
                    'sha256': sha(weather_png), 'mean': float(weather.mean()), 'std': float(weather.std()),
                    'min': float(weather.min()), 'max': float(weather.max())},
        'layoutFromCloseTile': layout, 'closeTileMeanLinearRgb': close_mean,
        'generationSeconds': round(time.time() - t0, 1),
    }
    man['variant'] = VARIANT
    (OUT / ('manifest.json' if VARIANT == 'V1' else 'manifest-%s.json' % VARIANT)).write_text(json.dumps(man, indent=1), encoding='utf-8')
    print(json.dumps({k: man[k] for k in ('tone', 'weather')}, indent=1)[:3000])
    print('layout', json.dumps(layout))


if __name__ == '__main__':
    sys.exit(main())
