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
elif VARIANT != 'V1':
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
