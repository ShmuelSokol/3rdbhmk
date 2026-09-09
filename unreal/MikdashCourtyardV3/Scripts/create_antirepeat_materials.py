"""Anti-repetition, offline half: author the macro-variation noise texture and MEASURE the repetition.

Shmuel, verbatim, 2026-09-09: "I don't wanna see, like, repeating patterns all over."

The textures themselves are accepted and are NEVER re-authored here: the Herodian ashlar set
(SourceAssets/material-review/HerodianAshlarV4, accepted 2026-09-09) and the Jerusalem paving
(SourceAssets/visual-review/JerusalemPavingV1, accepted earlier) are read only. What this file
produces is (1) one small tiling NOISE texture used as a very-low-frequency macro-variation field,
and (2) numbers: a before/after measurement of how periodic a large wall built from those tiles
actually is, so "less repetitive" is a measurement rather than a claim.

The schemes measured here are exactly the schemes Scripts/release_antirepeat.py compiles into the
HLSL of M_AntiRepeat_Triplanar; the parameters live in ONE place (SCHEME below), are written into
this folder's manifest.json, and release_antirepeat.spec.json is cross-checked against them the way
release_herodian_ashlar_v4.py cross-checks TilingCm.

Metrics (all computed on mean-removed sRGB luminance of a simulated wall, and all reported for every
scheme, so they can be compared against the baseline row):

  combEnergyFraction  fraction of non-DC 2-D spectral power that lands on the harmonic comb of the
                      tile period. A perfectly tiled wall puts ALL of its energy there: 1.0 means
                      "wallpaper". This is the primary number.
  acPeakU / acPeakV   normalized autocorrelation of the wall at a lag of exactly one tile along the
                      wall / up the wall. 1.0 = the pixel one tile away is identical.
  courseProfileStd    standard deviation of the row-mean luminance = how strongly the horizontal bed
                      joints (the coursing) are expressed. This is a QUALITY guard, not a repetition
                      metric: masonry must keep its courses. A scheme that lowers combEnergyFraction
                      by destroying this has broken the wall, not fixed it.
  edgeEnergy          mean gradient magnitude = joint and drafted-margin sharpness. Same role.

Schemes:
  baseline        plain world-tiled sampling, i.e. what the build ships today.
  bandOffset      each 1-tile-high course band is slid sideways by a hash of its OWN band index, so
                  the shift is constant along the wall (no vertical seam exists anywhere) and shows
                  up only across a real bed joint - which is exactly what running bond is. Free.
  mirrorBand      both of the above.
  mirror          per-tile-cell random horizontal mirror of the UV. Free (a few ALU), and seamless:
                  a mirrored cell still matches its neighbours at the cell edge, and mirroring only
                  in u leaves the bed joints, the per-course setback ledge and the downward weather
                  run-off exactly where they were.
  macro           two very-low-frequency noise bands (non-harmonic periods) multiplying albedo
                  brightness with a slight warm/cool shift. Costs 2 texture fetches.
  shipped         mirror + bandOffset + macro. This is what release_antirepeat.py builds.
  stochastic      3-sample hex-tile (Heitz & Neyret 2018) with per-cell random offset, linear blend.
  stochasticVP    the same with the variance-preserving blend.
Both stochastic rows are measured in order to be REJECTED with numbers rather than by assertion:
they remove the grid but they also blend three differently-offset copies of a structured masonry
tile, which triplicates and smears the bed joints. Watch courseProfileStd and edgeEnergy.

Offline only. No engine, no map, no editor. Writes only inside
SourceAssets/material-review/AntiRepeatV1/.

  python Scripts/create_antirepeat_materials.py            # noise texture + full measurement
  python Scripts/create_antirepeat_materials.py --noise    # noise texture only
  python Scripts/create_antirepeat_materials.py --measure  # measurement only (noise must exist)
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/material-review/AntiRepeatV1'
NOISE_PNG = OUT / 'T_AntiRepeat_MacroNoise.png'
MANIFEST = OUT / 'manifest.json'

NOISE_SIZE = 512
NOISE_SEED = 20260909

# ---------------------------------------------------------------------------------------------
# THE SCHEME. One source of truth: the HLSL in release_antirepeat.py is generated from these
# names and release_antirepeat.spec.json is refused if its numbers disagree with the manifest.
# ---------------------------------------------------------------------------------------------
SCHEME = {
    'noise': {
        'size': NOISE_SIZE,
        'seed': NOISE_SEED,
        'channels': {
            'R': 'macro value band, ~2.5 cycles across the texture, rank-transformed to exactly uniform [0,1)',
            'G': 'decorrelated field of the same band, drives the warm/cool shift',
            'B': 'mid band, ~6 cycles across the texture, drives the second (non-harmonic) breakup and roughness',
        },
        'why': 'A rank transform makes every channel exactly uniform, mean 0.5, std 1/sqrt(12) = 0.288675, '
               'so an Amount parameter has an exact meaning: peak-to-peak Amount, std 0.288675 * Amount.',
    },
    'variants': {
        'Ashlar': {
            'tilingCm': 300.0,
            'MacroCm': 3733.0,
            'MacroAmount': 0.13,
            'MacroWarm': 0.045,
            'MidCm': 1063.0,
            'MidAmount': 0.07,
            'MidRoughness': 0.05,
            'MirrorEnable': 1.0,
            'PerInstanceJitter': 0.06,
        },
        'Trim': {
            'tilingCm': 300.0,
            'MacroCm': 3733.0,
            'MacroAmount': 0.10,
            'MacroWarm': 0.035,
            'MidCm': 1063.0,
            'MidAmount': 0.055,
            'MidRoughness': 0.04,
            'MirrorEnable': 1.0,
            'PerInstanceJitter': 0.05,
        },
        'PavingSlabs': {
            'tilingCm': 200.0,
            'MacroCm': 4441.0,
            'MacroAmount': 0.13,
            'MacroWarm': 0.04,
            'MidCm': 1279.0,
            'MidAmount': 0.07,
            'MidRoughness': 0.05,
            'MirrorEnable': 1.0,
            'PerInstanceJitter': 0.06,
        },
        'OldCityFacade': {
            'tilingCm': 400.0,
            'MacroCm': 5171.0,
            'MacroAmount': 0.13,
            'MacroWarm': 0.04,
            'MidCm': 1471.0,
            'MidAmount': 0.07,
            'MidRoughness': 0.05,
            'MirrorEnable': 1.0,
            'PerInstanceJitter': 0.0,
            'reportedNotShipped': 'MEASURED FOR THE RECORD, NOT APPLIED BY THIS PASS. M_Context_Building '
                                  'already carries a per-object hashed tint (4 warm tints from ObjectPositionWS '
                                  'and vertex colour) and a hashed roughness offset, which is the per-object '
                                  'technique - but its UV is a plain 400 cm world triplanar with no mirror, no '
                                  'band offset and no macro noise, so the tile grid inside and across every one '
                                  'of the 1,498 building meshes is identical. The baseline row below is that '
                                  'grid; the shipped row is what the same treatment would buy. Applying it means '
                                  'ASSET-level reassignment on 1,498 building and 2,877 street meshes, which is '
                                  'a much larger mutation than a component slot override and is out of scope here.',
        },
        'JerusalemPaving': {
            'tilingCm': 500.0,
            'MacroCm': 6229.0,
            'MacroAmount': 0.14,
            'MacroWarm': 0.04,
            'MidCm': 1783.0,
            'MidAmount': 0.075,
            'MidRoughness': 0.0,
            'MirrorEnable': 1.0,
            'PerInstanceJitter': 0.0,
        },
    },
    'whyNonHarmonic': 'MacroCm and MidCm are deliberately non-harmonic with the tile and with each other. '
                      'Ashlar: 3733/300 = 12.443, 1063/300 = 3.543, 3733/1063 = 3.512 - every ratio at least '
                      '0.1 away from a whole number, which release_antirepeat.py refuses to ship without. '
                      'A harmonic ratio would not remove the grid, it would build a bigger one.',
    'whyNoStochastic': 'Measured and rejected for these materials: see measurement.schemes.stochastic* in '
                       'this manifest. Texture bombing is for stochastic (noise-like) source images; on a '
                       'structured coursed-ashlar tile it blends three differently-offset copies and the bed '
                       'joints triplicate and smear.',
}

# Measurement grid. 256 px per tile keeps the 0.8 cm joints resolvable (1.17 cm/px on the 300 cm tile).
MEASURE = {'tilesU': 20, 'tilesV': 6, 'tilePx': 256, 'seed': 4242}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


# ------------------------------------------------------------------------------------- noise
def _band(size, cycles, rng):
    """A seamless, periodic band-limited field: white noise shaped in the Fourier domain."""
    white = rng.standard_normal((size, size))
    spectrum = np.fft.fft2(white)
    fy = np.fft.fftfreq(size) * size
    fx = np.fft.fftfreq(size) * size
    radius = np.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)
    # Gaussian bandpass centred on `cycles` cycles per texture width.
    shape = np.exp(-0.5 * ((radius - cycles) / max(cycles * 0.55, 0.75)) ** 2)
    shape[0, 0] = 0.0
    field = np.real(np.fft.ifft2(spectrum * shape))
    return field


def _rank_uniform(field):
    """Monotonic map to exactly uniform [0,1): mean 0.5, std 1/sqrt(12). Smoothness is preserved."""
    flat = field.ravel()
    order = np.argsort(flat, kind='stable')
    ranks = np.empty(flat.size, dtype=np.float64)
    ranks[order] = (np.arange(flat.size) + 0.5) / flat.size
    return ranks.reshape(field.shape)


def make_noise():
    rng = np.random.default_rng(NOISE_SEED)
    r = _rank_uniform(_band(NOISE_SIZE, 2.5, rng))
    g = _rank_uniform(_band(NOISE_SIZE, 2.5, rng))
    b = _rank_uniform(_band(NOISE_SIZE, 6.0, rng))
    rgb = np.stack([r, g, b], axis=-1)
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(np.rint(rgb * 255.0), 0, 255).astype(np.uint8), 'RGB').save(NOISE_PNG)
    quantised = np.asarray(Image.open(NOISE_PNG), dtype=np.float64) / 255.0
    corr = float(np.corrcoef(quantised[..., 0].ravel(), quantised[..., 1].ravel())[0, 1])
    return {
        'path': str(NOISE_PNG.relative_to(ROOT)),
        'sha256': sha(NOISE_PNG),
        'bytes': NOISE_PNG.stat().st_size,
        'size': NOISE_SIZE,
        'seed': NOISE_SEED,
        'seamless': 'periodic by construction (shaped in the Fourier domain of a periodic grid)',
        'measuredMean': [round(float(quantised[..., i].mean()), 5) for i in range(3)],
        'measuredStd': [round(float(quantised[..., i].std()), 5) for i in range(3)],
        'rgCorrelation': round(corr, 5),
        'channels': SCHEME['noise']['channels'],
        'importSettings': {'compression': 'TC_DEFAULT', 'srgb': False, 'lodGroup': 'TEXTUREGROUP_WORLD',
                           'why': 'Linear data, not colour: sRGB off. Small and always sampled at an enormous '
                                  'world scale, so it is one cache-resident fetch.'},
    }


# ------------------------------------------------------------------------------- wall simulation
def _load_tile(png, px):
    img = Image.open(png).convert('RGB')
    if img.size[0] != img.size[1]:
        raise RuntimeError('Tile is not square: %s' % png)
    return np.asarray(img.resize((px, px), Image.BILINEAR), dtype=np.float32) / 255.0


def _luma(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def _cell_hash(i, j, salt):
    """Exactly the shipped HLSL hash, including the fmod.

    frac(sin(fmod(a, 2*pi)) * 43758.5453). The fmod is not cosmetic: without it the argument on a
    cell 1,000 tiles from the origin is ~1e5, where fp32 sin has lost most of its precision and
    neighbouring cells stop being independent. Reducing first costs one instruction and makes the
    hash behave the same everywhere in a 1.44 km scene."""
    a = np.fmod((i + 0.5) * 12.9898 + (j + 0.5) * 78.233 + salt, 2.0 * np.pi)
    x = np.sin(a) * 43758.5453
    return x - np.floor(x)


def _noise_field(noise, u_cm, v_cm, period_cm, channel):
    """Bilinear sample of the tiling noise texture at world (u,v) centimetres."""
    size = noise.shape[0]
    fu = (u_cm / period_cm) * size
    fv = (v_cm / period_cm) * size
    i0 = np.floor(fu).astype(np.int64)
    j0 = np.floor(fv).astype(np.int64)
    du = (fu - i0)[None, :]
    dv = (fv - j0)[:, None]
    i0 %= size
    j0 %= size
    i1 = (i0 + 1) % size
    j1 = (j0 + 1) % size
    c = noise[..., channel]
    top = c[np.ix_(j0, i0)] * (1 - du) + c[np.ix_(j0, i1)] * du
    bot = c[np.ix_(j1, i0)] * (1 - du) + c[np.ix_(j1, i1)] * du
    return top * (1 - dv) + bot * dv


def build_wall(tile, cfg, noise, mirror=False, band_offset=False, macro=False, stochastic=None, seed=None):
    """Simulate a wall of tilesU x tilesV tiles under one scheme. Returns float RGB [0,1].

    Every non-stochastic scheme (the baseline included) goes through the same per-pixel gather, so
    the comparison is not contaminated by two different resamplings."""
    px = MEASURE['tilePx']
    nu, nv = MEASURE['tilesU'], MEASURE['tilesV']
    tile_cm = float(cfg['tilingCm'])
    height, width = nv * px, nu * px

    if stochastic:
        wall = _hex_wall(tile, width, height, px, stochastic, seed)
    else:
        wall = np.empty((height, width, 3), dtype=np.float32)
        for start in range(0, height, 256):
            stop = min(start + 256, height)
            wall[start:stop] = _uv_band(tile, width, start, stop, px, mirror, band_offset)

    if macro:
        cm_per_px = tile_cm / px
        u_cm = (np.arange(width, dtype=np.float64) + 0.5) * cm_per_px
        v_cm = (np.arange(height, dtype=np.float64) + 0.5) * cm_per_px
        m = _noise_field(noise, u_cm, v_cm, float(cfg['MacroCm']), 0)
        w = _noise_field(noise, u_cm, v_cm, float(cfg['MacroCm']), 1)
        d = _noise_field(noise, u_cm, v_cm, float(cfg['MidCm']), 2)
        gain = (1.0 + float(cfg['MacroAmount']) * (m - 0.5) + float(cfg['MidAmount']) * (d - 0.5))
        warm = float(cfg['MacroWarm']) * (w - 0.5)
        wall = wall * gain[..., None].astype(np.float32)
        wall[..., 0] *= (1.0 + warm).astype(np.float32)
        wall[..., 2] *= (1.0 - warm).astype(np.float32)
    return np.clip(wall, 0.0, 1.0)


def _uv_band(tile, width, y0, y1, px, mirror, band_offset):
    """The shipped UV transform, per pixel, exactly as the HLSL does it.

    band_offset: the whole 300 cm course band is slid sideways by a hash of its OWN index only, so
    the shift is constant along the wall (no vertical seam anywhere) and appears only across a real
    bed joint - which is what running bond is. mirror: per cell, and a mirrored cell still meets its
    neighbours edge to edge because the tile is periodic, so no seam either."""
    size = tile.shape[0]
    ys, xs = np.mgrid[y0:y1, 0:width]
    u = xs.astype(np.float64) / px
    v = ys.astype(np.float64) / px
    del xs, ys
    j = np.floor(v)
    if band_offset:
        u = u + _cell_hash(j, np.zeros_like(j), 5.71)
    i = np.floor(u)
    fu = u - i
    if mirror:
        flip = _cell_hash(i, j, 0.0) > 0.5
        fu = np.where(flip, 1.0 - fu, fu)
    fv = v - j
    tu = np.mod(np.rint(fu * size).astype(np.int64), size)
    tv = np.mod(np.rint(fv * size).astype(np.int64), size)
    return tile[tv, tu]


def _hex_wall(tile, width, height, px, mode, seed, band=192):
    """Heitz & Neyret hex-tile sampling: three per-cell-offset taps blended over a triangle grid.

    Evaluated in horizontal bands: the full-resolution intermediates do not fit in the memory this
    machine has free (PERFORMANCE-BUDGET.md: 16 GB, and the editor is the priority consumer)."""
    out = np.empty((height, width, 3), dtype=np.float32)
    for start in range(0, height, band):
        stop = min(start + band, height)
        out[start:stop] = _hex_band(tile, width, start, stop, px, mode)
    return out


def _hex_band(tile, width, y0, y1, px, mode):
    ys, xs = np.mgrid[y0:y1, 0:width]
    u = xs.astype(np.float64) / px
    v = ys.astype(np.float64) / px
    del xs, ys
    height = y1 - y0
    su = (u * 3.464) - (v * 3.464) * 0.57735027
    sv = (v * 3.464) * 1.15470054
    bi = np.floor(su).astype(np.int64)
    bj = np.floor(sv).astype(np.int64)
    fu = su - bi
    fv = sv - bj
    del su, sv
    fz = 1.0 - fu - fv
    upper = fz > 0.0
    w1 = np.where(upper, fz, -fz)
    w2 = np.where(upper, fv, 1.0 - fv)
    w3 = np.where(upper, fu, 1.0 - fu)
    verts = [(np.where(upper, bi, bi + 1), np.where(upper, bj, bj + 1)),
             (bi, np.where(upper, bj + 1, bj)),
             (np.where(upper, bi + 1, bi), bj)]
    del fu, fv, fz, upper, bi, bj

    size = tile.shape[0]
    acc = np.zeros((height, width, 3), dtype=np.float32)
    weights = [w1, w2, w3]
    mean = tile.reshape(-1, 3).mean(axis=0)
    for w, (vi, vj) in zip(weights, verts):
        hu = _cell_hash(vi.astype(np.float64), vj.astype(np.float64), 0.0)
        hv = _cell_hash(vi.astype(np.float64), vj.astype(np.float64), 17.13)
        tu = np.mod(np.rint((u + hu) * size).astype(np.int64), size)
        tv = np.mod(np.rint((v + hv) * size).astype(np.int64), size)
        sample = tile[tv, tu]
        if mode == 'variance_preserving':
            sample = sample - mean.astype(np.float32)
        acc += (w[..., None] * sample).astype(np.float32)
        del hu, hv, tu, tv, sample
    if mode == 'variance_preserving':
        norm = np.sqrt(w1 * w1 + w2 * w2 + w3 * w3)
        acc = acc / norm[..., None].astype(np.float32) + mean.astype(np.float32)
    return acc


# ------------------------------------------------------------------------------------- metrics
def metrics(wall, tile_px):
    lum = _luma(wall).astype(np.float64)
    height, width = lum.shape
    centred = lum - lum.mean()
    power = float((centred * centred).mean())

    spectrum = np.fft.rfft2(centred)
    mag = (np.abs(spectrum) ** 2)
    mag[0, 0] = 0.0
    total = float(mag.sum())
    nu = width // tile_px
    nv = height // tile_px
    comb = np.zeros(mag.shape, dtype=bool)
    comb[::nv, ::nu] = True          # harmonics of the tile fundamental in both axes
    comb[0, 0] = False
    comb_fraction = float(mag[comb].sum() / total) if total > 0 else 0.0

    def autocorr(lag_axis):
        if lag_axis == 1:
            a, b = centred[:, :-tile_px], centred[:, tile_px:]
        else:
            a, b = centred[:-tile_px, :], centred[tile_px:, :]
        return float((a * b).mean() / power) if power > 0 else 0.0

    gy, gx = np.gradient(lum)
    return {
        'combEnergyFraction': round(comb_fraction, 5),
        'acPeakU': round(autocorr(1), 5),
        'acPeakV': round(autocorr(0), 5),
        'courseProfileStd': round(float(lum.mean(axis=1).std()), 6),
        'edgeEnergy': round(float(np.sqrt(gx * gx + gy * gy).mean()), 6),
        'lumaMean': round(float(lum.mean()), 5),
        'lumaStd': round(float(lum.std()), 5),
    }


def measure_variant(name, tile_png, cfg, noise):
    tile = _load_tile(tile_png, MEASURE['tilePx'])
    schemes = {}
    schemes['baseline'] = build_wall(tile, cfg, noise)
    schemes['mirror'] = build_wall(tile, cfg, noise, mirror=True)
    schemes['bandOffset'] = build_wall(tile, cfg, noise, band_offset=True)
    schemes['mirrorBand'] = build_wall(tile, cfg, noise, mirror=True, band_offset=True)
    schemes['macro'] = build_wall(tile, cfg, noise, macro=True)
    schemes['shipped'] = build_wall(tile, cfg, noise, mirror=True, band_offset=True, macro=True)
    schemes['stochastic'] = build_wall(tile, cfg, noise, stochastic='linear', seed=MEASURE['seed'])
    schemes['stochasticVP'] = build_wall(tile, cfg, noise, stochastic='variance_preserving', seed=MEASURE['seed'])

    rows = {}
    base = None
    for scheme, wall in schemes.items():
        row = metrics(wall, MEASURE['tilePx'])
        if scheme == 'baseline':
            base = row
        row['combEnergyVsBaseline'] = round(row['combEnergyFraction'] / base['combEnergyFraction'], 4) if base['combEnergyFraction'] else None
        row['courseProfileVsBaseline'] = round(row['courseProfileStd'] / base['courseProfileStd'], 4) if base['courseProfileStd'] else None
        row['edgeEnergyVsBaseline'] = round(row['edgeEnergy'] / base['edgeEnergy'], 4) if base['edgeEnergy'] else None
        rows[scheme] = row

    previews = {}
    for scheme in ('baseline', 'shipped', 'stochasticVP'):
        small = Image.fromarray(np.clip(np.rint(schemes[scheme] * 255.0), 0, 255).astype(np.uint8), 'RGB')
        small = small.resize((small.size[0] // 4, small.size[1] // 4), Image.BILINEAR)
        path = OUT / 'previews' / ('wall_%s_%s.png' % (name, scheme))
        path.parent.mkdir(parents=True, exist_ok=True)
        small.save(path)
        previews[scheme] = {'path': str(path.relative_to(ROOT)), 'sha256': sha(path)}
    return {'tile': str(Path(tile_png).relative_to(ROOT)), 'tileSha256': sha(tile_png), 'parameters': cfg,
            'regionCm': [MEASURE['tilesU'] * cfg['tilingCm'], MEASURE['tilesV'] * cfg['tilingCm']],
            'schemes': rows, 'previews': previews}


TILES = {
    'Ashlar': 'SourceAssets/material-review/HerodianAshlarV4/T_HerodianV4_Ashlar_Albedo.png',
    'Trim': 'SourceAssets/material-review/HerodianAshlarV4/T_HerodianV4_Trim_Albedo.png',
    'JerusalemPaving': 'SourceAssets/visual-review/JerusalemPavingV1/jerusalem-paving-albedo.png',
    'OldCityFacade': 'SourceAssets/materials-context/facade-limestone/sandstone_blocks_05_diff_2k.png',
    'PavingSlabs': None,   # engine-side texture only (T_PavingSlabs_Albedo.uasset); no PNG to measure
}


def run(do_noise=True, do_measure=True):
    OUT.mkdir(parents=True, exist_ok=True)
    report = {'status': 'OFFLINE_MEASURED_NATIVE_BUILD_PENDING', 'iteration': 'AntiRepeatV1',
              'instruction': 'Shmuel, verbatim, 2026-09-09: "I don\'t wanna see, like, repeating patterns all over."',
              'generator': 'Scripts/create_antirepeat_materials.py',
              'generatorSha256': sha(Path(__file__)),
              'startedUtc': datetime.now(timezone.utc).isoformat(),
              'texturesReAuthored': 'NONE. The Herodian ashlar and Jerusalem paving images are read only; '
                                    'every change is in the material graph.',
              'scheme': SCHEME, 'measurementGrid': dict(MEASURE)}
    if MANIFEST.exists() and not do_noise:
        report['noise'] = json.loads(MANIFEST.read_text(encoding='utf-8-sig')).get('noise')
    if do_noise:
        report['noise'] = make_noise()
    if do_measure:
        if not report.get('noise'):
            raise RuntimeError('Run --noise first: the measurement samples the authored noise texture.')
        noise = np.asarray(Image.open(NOISE_PNG), dtype=np.float64) / 255.0
        report['measurement'] = {}
        for name, rel in TILES.items():
            cfg = SCHEME['variants'][name]
            if rel is None:
                report['measurement'][name] = {'skipped': 'no source PNG in the repository (engine texture only); '
                                                          'the same scheme and the same HLSL are applied'}
                continue
            png = ROOT / rel
            if not png.exists():
                report['measurement'][name] = {'skipped': 'source PNG not found: ' + rel}
                continue
            report['measurement'][name] = measure_variant(name, png, cfg, noise)
    report['finishedUtc'] = datetime.now(timezone.utc).isoformat()
    MANIFEST.write_text(json.dumps(report, indent=2, default=str) + '\n', encoding='utf-8')
    return report


def _summary(report):
    lines = []
    for name, block in report.get('measurement', {}).items():
        if 'schemes' not in block:
            lines.append('%-16s %s' % (name, block.get('skipped')))
            continue
        lines.append('%s  (%.0f x %.0f cm region, %.0f cm tile)' % (
            name, block['regionCm'][0], block['regionCm'][1], block['parameters']['tilingCm']))
        lines.append('  %-14s %10s %8s %8s %10s %10s' % ('scheme', 'comb', 'acU', 'acV', 'course', 'edge'))
        for scheme, row in block['schemes'].items():
            lines.append('  %-14s %10.4f %8.3f %8.3f %9.2fx %9.2fx' % (
                scheme, row['combEnergyFraction'], row['acPeakU'], row['acPeakV'],
                row['courseProfileVsBaseline'], row['edgeEnergyVsBaseline']))
    return '\n'.join(lines)



def measure_from_build(receipt_path):
    """Re-run the measurement using the parameters READ BACK FROM THE BUILT MATERIAL ON DISK.

    This is as close to "measured from the actual shipped material" as is possible without a
    renderer: the numbers below are produced by the same transform the HLSL compiles, driven by the
    scalar values Scripts/release_antirepeat.py read back out of the saved .uasset after save and
    reopen - not by the values written in this file. If the engine had silently dropped or altered a
    parameter, these rows would move. It is still a spectral model of an albedo field, NOT a
    rendered frame; this machine cannot run a real-RHI capture and none is claimed.
    """
    receipt = json.loads(Path(receipt_path).read_text(encoding='utf-8-sig'))
    if receipt.get('status') != 'BUILT_SAVED_READBACK_APPLY_PENDING':
        raise RuntimeError('Build receipt status %r; re-measure needs a completed build' % receipt.get('status'))
    noise = np.asarray(Image.open(NOISE_PNG), dtype=np.float64) / 255.0
    out = {'status': 'REMEASURED_FROM_BUILT_MATERIAL_PARAMETERS',
           'buildReceipt': str(receipt_path),
           'buildReceiptSha256': sha(receipt_path),
           'generatorSha256': sha(Path(__file__)),
           'measuredUtc': datetime.now(timezone.utc).isoformat(),
           'provenance': measure_from_build.__doc__.strip(),
           'measurementGrid': dict(MEASURE),
           'variants': {}}
    for name, block in (receipt.get('repetitionNumbers') or {}).get('variants', {}).items():
        key = block.get('schemeVariant')
        rel = TILES.get(key)
        built = block.get('parametersReadBackFromDisk') or {}
        row = {'schemeVariant': key, 'parametersReadBackFromDisk': built,
               'instance': receipt.get('reloaded', {}).get(name, {}).get('path'),
               'textures': receipt.get('reloaded', {}).get(name, {}).get('textures')}
        if not rel or not (ROOT / rel).exists():
            row['skipped'] = 'no source PNG for scheme %r; the same HLSL and the same parameters apply' % key
            out['variants'][name] = row
            continue
        cfg = dict(SCHEME['variants'][key])
        for spec_key, cfg_key in (('TilingCm', 'tilingCm'), ('MacroCm', 'MacroCm'), ('MacroAmount', 'MacroAmount'),
                                  ('MacroWarm', 'MacroWarm'), ('MidCm', 'MidCm'), ('MidAmount', 'MidAmount'),
                                  ('MirrorEnable', 'MirrorEnable')):
            if spec_key in built:
                cfg[cfg_key] = float(built[spec_key])
        row['parametersUsed'] = {k: v for k, v in cfg.items() if not isinstance(v, str)}
        tile = _load_tile(ROOT / rel, MEASURE['tilePx'])
        base = metrics(build_wall(tile, cfg, noise), MEASURE['tilePx'])
        band = float(built.get('BandOffsetEnable', 1.0)) > 0.5
        mirror = float(built.get('MirrorEnable', 1.0)) > 0.5
        shipped = metrics(build_wall(tile, cfg, noise, mirror=mirror, band_offset=band, macro=True), MEASURE['tilePx'])
        for label, table in (('baseline', base), ('shipped', shipped)):
            table['combEnergyVsBaseline'] = round(table['combEnergyFraction'] / base['combEnergyFraction'], 4)
            table['courseProfileVsBaseline'] = round(table['courseProfileStd'] / base['courseProfileStd'], 4)
            table['edgeEnergyVsBaseline'] = round(table['edgeEnergy'] / base['edgeEnergy'], 4)
        row['schemes'] = {'baseline': base, 'shipped': shipped}
        row['tile'] = rel
        row['tileSha256'] = sha(ROOT / rel)
        out['variants'][name] = row
    path = OUT / ('remeasured-from-build-' + stamp() + '.json')
    path.write_text(json.dumps(out, indent=2, default=str) + '\n', encoding='utf-8')
    out['receipt'] = str(path)
    return out



NORMALS = {
    'Ashlar': 'SourceAssets/material-review/HerodianAshlarV4/T_HerodianV4_Ashlar_Normal.png',
    'Trim': 'SourceAssets/material-review/HerodianAshlarV4/T_HerodianV4_Trim_Normal.png',
    'OldCityFacade': 'SourceAssets/materials-context/facade-limestone/sandstone_blocks_05_nor_dx_2k.png',
}


def measure_relief():
    """Does the anti-repeat UV transform reduce visible RELIEF anywhere? Measured, not argued.

    This project has already had a pass flatten the Keruv frieze and need reverting from a
    checkpoint, so "the normals are fine" is not something to assert. The same wall region is built
    from the APPROVED normal map twice - once plain-tiled, once through the shipped mirror + band
    offset - and the tangent-space deviation magnitude sqrt(x^2 + y^2) is compared over the whole
    region, at the median, the 95th and the 99th percentile. Those are the same statistics
    SourceAssets/material-review/HerodianAshlarV4/manifest.json quotes for the source maps, so the
    rows here can be read against it directly.

    The transform cannot change relief and this says so with numbers: a per-cell mirror negates the
    u component of the sampled normal, and |-x| = |x|, so the deviation magnitude is invariant; a
    band offset only slides which texel is read. Both maps are sampled with Texture2DSampleGrad at
    the pre-warp derivatives, so the mip chain is the same too. Anything other than equality here is
    a bug in the warp, not a stylistic choice. NormalStrength is carried across unchanged and is
    checked separately, per instance, by release_antirepeat.py's parity check."""
    out = {'status': 'RELIEF_PARITY_MEASURED', 'measuredUtc': datetime.now(timezone.utc).isoformat(),
           'generatorSha256': sha(Path(__file__)), 'measurementGrid': dict(MEASURE),
           'method': measure_relief.__doc__.strip(), 'variants': {}}
    noise = np.asarray(Image.open(NOISE_PNG), dtype=np.float64) / 255.0
    for name, rel in NORMALS.items():
        png = ROOT / rel
        if not png.exists():
            out['variants'][name] = {'skipped': 'normal map not found: ' + rel}
            continue
        cfg = SCHEME['variants'][name]
        tile = _load_tile(png, MEASURE['tilePx'])
        rows = {}
        for label, kwargs in (('baseline', {}), ('shipped', {'mirror': True, 'band_offset': True})):
            wall = build_wall(tile, cfg, noise, **kwargs)
            xy = wall[..., :2].astype(np.float64) * 2.0 - 1.0
            mag = np.sqrt(xy[..., 0] ** 2 + xy[..., 1] ** 2)
            rows[label] = {'xyDeviationMean': round(float(mag.mean()), 5),
                           'xyDeviationP50': round(float(np.percentile(mag, 50)), 5),
                           'xyDeviationP95': round(float(np.percentile(mag, 95)), 5),
                           'xyDeviationP99': round(float(np.percentile(mag, 99)), 5),
                           'xyDeviationMax': round(float(mag.max()), 5)}
        deltas = {k: round(rows['shipped'][k] - rows['baseline'][k], 6) for k in rows['baseline']}
        worst = max(abs(v) for v in deltas.values())
        rows['deltaShippedMinusBaseline'] = deltas
        rows['worstAbsoluteDelta'] = worst
        rows['reliefPreserved'] = bool(worst <= 0.002)
        rows['tile'] = rel
        rows['tileSha256'] = sha(png)
        out['variants'][name] = rows
    out['allReliefPreserved'] = all(v.get('reliefPreserved') for v in out['variants'].values() if 'skipped' not in v)
    path = OUT / ('relief-parity-' + stamp() + '.json')
    path.write_text(json.dumps(out, indent=2, default=str) + '\n', encoding='utf-8')
    out['receipt'] = str(path)
    return out


def _main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--noise', action='store_true', help='write the macro-variation noise texture only')
    parser.add_argument('--measure', action='store_true', help='run the repetition measurement only')
    parser.add_argument('--relief', action='store_true',
                        help='measure whether the shipped UV transform changes normal-map relief')
    parser.add_argument('--from-build', metavar='RECEIPT',
                        help='re-run the measurement with the parameters read back out of the built '
                             '.uasset by Scripts/release_antirepeat.py -AntiRepeatBuild')
    args = parser.parse_args()
    if args.relief:
        result = measure_relief()
        for name, row in result['variants'].items():
            if 'skipped' in row:
                print('%-16s %s' % (name, row['skipped']))
                continue
            print('%-16s xy deviation mean %.5f -> %.5f   p95 %.5f -> %.5f   p99 %.5f -> %.5f   worst delta %.6f  preserved=%s'
                  % (name, row['baseline']['xyDeviationMean'], row['shipped']['xyDeviationMean'],
                     row['baseline']['xyDeviationP95'], row['shipped']['xyDeviationP95'],
                     row['baseline']['xyDeviationP99'], row['shipped']['xyDeviationP99'],
                     row['worstAbsoluteDelta'], row['reliefPreserved']))
        print('\nallReliefPreserved: %s\nreceipt: %s' % (result['allReliefPreserved'], result['receipt']))
        return 0 if result['allReliefPreserved'] else 1
    if args.from_build:
        result = measure_from_build(args.from_build)
        for name, row in result['variants'].items():
            if 'schemes' not in row:
                print('%-22s %s' % (name, row.get('skipped')))
                continue
            print('%-22s comb %.4f -> %.4f   acU %.3f -> %.3f   acV %.3f -> %.3f   course %.2fx  edge %.2fx'
                  % (name, row['schemes']['baseline']['combEnergyFraction'],
                     row['schemes']['shipped']['combEnergyFraction'],
                     row['schemes']['baseline']['acPeakU'], row['schemes']['shipped']['acPeakU'],
                     row['schemes']['baseline']['acPeakV'], row['schemes']['shipped']['acPeakV'],
                     row['schemes']['shipped']['courseProfileVsBaseline'],
                     row['schemes']['shipped']['edgeEnergyVsBaseline']))
        print('\nreceipt: %s' % result['receipt'])
        return 0
    both = not (args.noise or args.measure)
    report = run(do_noise=args.noise or both, do_measure=args.measure or both)
    print(_summary(report))
    print('\nmanifest: %s' % MANIFEST)
    return 0


if __name__ == '__main__':
    sys.exit(_main())
