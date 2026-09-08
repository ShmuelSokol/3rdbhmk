"""Jerusalem limestone (meleke) ashlar PBR set V2 (iteration V3) - procedural, tiling, offline (stdlib only).

Why: the lighting-v3 diagnosis (release_lighting_v3.spec.json "diagnosis") measured the CC0
sandstone_blocks_08 stand-in at about 2 % albedo contrast (per-channel std 0.021, R p5-p95
0.62-0.68), a weak normal map (xy deviation p95 0.09) and uniform roughness 0.50. Instance
scalars can only scale what a texture contains; this script authors a set that contains real
per-block variation, real joint depth and real roughness variation.

Iteration V3 (coordinator review of the first render: "tiled kitchen backsplash"): rectangular
running-bond blocks 1.7-3.3 x course height with course heights varying 40-60 cm; plain hewn and
dressed faces with only a soft arris (no drafted-margin "picture frames"); directional chisel
striations (vertical or horizontal per block, never diagonal) instead of comb hatching and
polka-dot pits; a little edge chipping and sparse pores; palette calibrated on the accepted
Kotel photo texture (SourceAssets/kotel-detail/PhotoSurfaceV1/kotel-wall-cleaned.png: sRGB
means 0.728/0.635/0.515, G/R 0.875, B/R 0.71; value varies moderately, hue barely); weathering
darkening/streaking at the lower part of each block face; tight 1.5 cm joints whose mortar is
the adjoining stone at 0.8x, so the joint is a fine shadow line carried by normal + AO.

What it writes (SourceAssets/material-review/LimestoneV2/, same names as before, replaced in place):
  T_LimestoneV2_<Variant>_Albedo.png   sRGB colour               (import: TC_Default, sRGB on)
  T_LimestoneV2_<Variant>_Normal.png   tangent-space normal      (import: TC_Normalmap, sRGB off, no green flip)
  T_LimestoneV2_<Variant>_ARM.png      R ambient occlusion, G roughness, B metallic (0)  (TC_Masks, sRGB off)
  T_LimestoneV2_<Variant>_Roughness.png / _AO.png / _Height.png   review copies, NOT imported
  previews/<name>_1024.png             1024 box-filtered preview of every map (texture orientation)
  previews/Lit_<Variant>_1024.png      software Lambert render in WORLD orientation (rows flipped so
                                       world up is image up; light from the upper left)
  manifest.json                        parameters, hashes, measured statistics (merged per variant)
Variants: Ashlar (wall field, 6 courses) and Trim (lintels, jambs, cornices: 8 courses of 32-44 cm,
finer dressing, 1.0 cm joints). No paving variant: Astra's Jerusalem paving is approved and stays.

Scale: the two limestone instances are triplanar world-space with TilingCm = 300, so one 2048
tile spans 300 x 300 cm (6.83 px/cm); course lines fall on the same world-Z levels on every wall.

Conventions (must match M_PBR_Tiled, release_pbr_architecture.py build_master_material):
  * Texture u = world X (or Y), v = world Z, both / TilingCm; image row 0 is v = 0, so IMAGE
    DOWN IS WORLD UP on vertical faces. Gravity-driven weathering (darkening toward the bottom
    of a block) is therefore drawn toward DECREASING row index within each course.
  * Normal = normalize(-dh/du, -dh/dv, 1) with u = column, v = row index (DirectX / UE
    default green). The master adds decoded (R, G) to the world normal along (u, v) axes, so
    this is the only self-consistent encoding; flip_green_channel must stay False.
  * Heights are centimetres; slopes are physical (cm per cm), no artificial gain.

Statistics (same method as the diagnosis): sRGB albedo per-channel mean / std / p5 / p95 from the
written bytes; normal xy deviation = sqrt(nx^2 + ny^2) of the decoded bytes, p50 / p95 over the
whole map AND over face-only pixels (joint/arris excluded) so face relief and joint lines are
reported separately; roughness min / p5 / p50 / p95 / max; AO min / mean. --baseline decodes the
sandstone_blocks_08 normal PNG with the same code (0.122 p95 / 0.089 mean; the diagnosis's 0.09).

Run (about 3 minutes per variant at 2048; pure Python, no numpy/PIL in the bundled interpreter):
  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\ThirdParty\\Python3\\Win64\\python.exe" Scripts\\create_limestone_textures_v2.py [--size 512] [--variant Ashlar] [--baseline]
Refuses to overwrite once SourceAssets/material-review/LimestoneV2/ holds a native import
receipt (limestone-v2-import-*.json) unless --force is given.
"""
import argparse
import hashlib
import json
import math
import random
import struct
import sys
import time
import zlib
from array import array
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets' / 'material-review' / 'LimestoneV2'
BASELINE_NORMAL = ROOT / 'SourceAssets' / 'materials-pbr' / 'limestone-ashlar' / 'sandstone_blocks_08_normal_2k.png'
TILE_CM = 300.0            # TilingCm of MI_PBR_LimestoneAshlar / MI_PBR_LimestoneTrim (inventory 20260908T183719554035Z)
DEFAULT_SIZE = 2048
ITERATION = 'V3'
DIAGNOSIS_BASELINE = {   # quoted from release_lighting_v3.spec.json diagnosis.textureMeasured (JPEG sources, not re-decoded here)
    'albedoMeanSRGB': [0.647, 0.574, 0.456], 'albedoStdPerChannel': 0.021, 'albedoR_p5_p95': [0.62, 0.68],
    'normalXyDeviationP95': 0.09, 'roughness': '0.50 +- 0.02 (uniform)'}
PHOTO_REFERENCE = {      # measured on SourceAssets/kotel-detail/PhotoSurfaceV1/kotel-wall-cleaned.png with this script's statistics code
    'file': 'SourceAssets/kotel-detail/PhotoSurfaceV1/kotel-wall-cleaned.png', 'meanSRGB': [0.728, 0.635, 0.515], 'medianSRGB': [0.761, 0.663, 0.533],
    'chromaGoverR_p5_p50_p95': [0.788, 0.875, 0.928], 'chromaBoverR_p5_p50_p95': [0.537, 0.71, 0.82], 'luminance_p25_p50_p75': [0.584, 0.671, 0.733],
    'note': 'AI-cleaned photo derivative with lighting partly baked in (PROVENANCE.md); used for warmth and value spread, not copied.'}

VARIANTS = {
    'Ashlar': dict(
        seed=5786, courses=6, course_h_cm=(40.0, 60.0), length_ratio=(1.7, 3.3), min_joint_stagger_cm=18.0,
        joint_cm=1.5, joint_depth_cm=0.6, arris_cm=0.6,
        # dressing: 'chisel' = directional striations, 'fine' = finely dressed (lower amplitude, denser strokes)
        dressing={'chisel': 0.7, 'fine': 0.3}, stroke_dir={'vertical': 0.6, 'horizontal': 0.4}, stroke_wobble_deg=8.0,
        stria_amp_cm={'chisel': (0.21, 0.30), 'fine': (0.08, 0.12)}, stria_across_cm={'chisel': (0.4, 0.6), 'fine': (0.3, 0.42)}, stria_along_cm=(2.5, 6.0), stria_patch_cm=8.0, stroke_angle_var_deg=9.0,
        base_offset_cm=0.20, tilt=0.004, undulation_cm=0.08,
        chip_chance=0.45, chips_per_block=(1, 3), chip_radius_cm=(1.5, 4.0), chip_depth_cm=(0.25, 0.7),
        pore_density_per_cm2=0.0006, pore_radius_cm=(0.15, 0.5),
        weathering=(0.3, 1.0), weather_dark=0.13, weather_band=0.35, streak=0.025,
        # palette: photo-calibrated base (means 0.728/0.635/0.515 after weathering), value jitter moderate, hue jitter small; some paler cream, few deeper ochre
        base_srgb=(0.775, 0.678, 0.551), value_jitter=0.09, gr_jitter=0.01, br_jitter=0.03,
        families=[('base', 0.65, 1.0, 0.0), ('cream', 0.22, 1.09, 0.015), ('ochre', 0.13, 0.92, -0.045)],
        mottle=(0.09, 0.04, 0.015), mortar_factor=0.78, mortar_grey=0.15,
        rough={'chisel': 0.66, 'fine': 0.59, 'mortar': 0.80, 'chip': 0.76, 'pore': 0.80}, rough_jitter=0.03, rough_grain=0.025, rough_clamp=(0.55, 0.85),
        ao_gain=0.7, ao_floor=0.55),
    'Trim': dict(
        seed=5787, courses=8, course_h_cm=(32.0, 44.0), length_ratio=(2.3, 3.6), min_joint_stagger_cm=20.0,
        joint_cm=1.0, joint_depth_cm=0.45, arris_cm=0.45,
        dressing={'chisel': 0.4, 'fine': 0.6}, stroke_dir={'vertical': 0.35, 'horizontal': 0.65}, stroke_wobble_deg=5.0,
        stria_amp_cm={'chisel': (0.12, 0.18), 'fine': (0.05, 0.08)}, stria_across_cm={'chisel': (0.35, 0.5), 'fine': (0.28, 0.4)}, stria_along_cm=(3.0, 8.0), stria_patch_cm=10.0, stroke_angle_var_deg=6.0,
        base_offset_cm=0.10, tilt=0.0025, undulation_cm=0.04,
        chip_chance=0.25, chips_per_block=(1, 2), chip_radius_cm=(1.0, 2.5), chip_depth_cm=(0.15, 0.4),
        pore_density_per_cm2=0.0003, pore_radius_cm=(0.12, 0.35),
        weathering=(0.2, 0.7), weather_dark=0.07, weather_band=0.30, streak=0.015,
        base_srgb=(0.800, 0.707, 0.583), value_jitter=0.06, gr_jitter=0.008, br_jitter=0.02,
        families=[('base', 0.75, 1.0, 0.0), ('cream', 0.20, 1.07, 0.012), ('ochre', 0.05, 0.94, -0.03)],
        mottle=(0.055, 0.028, 0.012), mortar_factor=0.80, mortar_grey=0.15,
        rough={'chisel': 0.62, 'fine': 0.57, 'mortar': 0.78, 'chip': 0.72, 'pore': 0.78}, rough_jitter=0.025, rough_grain=0.02, rough_clamp=(0.55, 0.85),
        ao_gain=0.75, ao_floor=0.6),
}


# ----------------------------------------------------------------------------------------- PNG
def write_png_rgb(path, width, height, rows):
    """rows: list of bytearrays, 3*width bytes each. Same stdlib writer as create_fx_materials.py."""
    raw = bytearray()
    for row in rows:
        raw.append(0)
        raw.extend(row)

    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b''))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return hashlib.sha256(png).hexdigest()


def decode_png_rgb8(path):
    """8-bit RGB/RGBA, non-interlaced, all five filters (create_kotel_stone_v2.py decoder)."""
    data = Path(path).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos, idat, width, height, channels = 8, [], None, None, None
    while pos < len(data):
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        kind, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b'IHDR':
            width, height, depth, color_type, _, _, interlace = struct.unpack('>IIBBBBB', body)
            assert depth == 8 and color_type in (2, 6) and interlace == 0, 'unsupported PNG layout'
            channels = 3 if color_type == 2 else 4
        elif kind == b'IDAT':
            idat.append(body)
        elif kind == b'IEND':
            break
    raw = zlib.decompress(b''.join(idat))
    stride = width * channels
    previous, rows, offset = bytearray(stride), [], 0
    for _ in range(height):
        f = raw[offset]
        line = bytearray(raw[offset + 1:offset + 1 + stride])
        offset += 1 + stride
        if f == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 255
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + previous[i]) & 255
        elif f == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = previous[i]
                c = previous[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if (pa <= pb and pa <= pc) else (b if pb <= pc else c))) & 255
        rows.append(line)
        previous = line
    if channels == 4:
        rows = [bytearray(b for i, b in enumerate(r) if i % 4 != 3) for r in rows]
    return width, height, rows


# ------------------------------------------------------------------------------------- helpers
def smoothstep(t):
    return t * t * (3.0 - 2.0 * t)


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def rel(path):
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)


def choose(rng, weighted):
    r = rng.random() * sum(w for _, w in weighted)
    for item, w in weighted:
        r -= w
        if r <= 0:
            return item
    return weighted[-1][0]


class PeriodicNoise:
    """Seamless value noise: a G x G grid, smoothstep-interpolated, horizontally pre-upsampled to `size`.
    row(y) returns `size` floats in [-1, 1] for output row y; wraps in both axes."""

    def __init__(self, rng, grid, size):
        self.g, self.size = grid, size
        values = [[rng.uniform(-1.0, 1.0) for _ in range(grid)] for _ in range(grid)]
        scale = grid / size
        cols = []
        for x in range(size):
            fx = (x + 0.5) * scale - 0.5
            i0 = math.floor(fx)
            cols.append((i0 % grid, (i0 + 1) % grid, smoothstep(fx - i0)))
        self.rows = [array('f', [v[i0] * (1.0 - w) + v[i1] * w for i0, i1, w in cols]) for v in values]
        self.scale = scale

    def row(self, y):
        fy = (y + 0.5) * self.scale - 0.5
        j0 = math.floor(fy)
        w = smoothstep(fy - j0)
        r0, r1 = self.rows[j0 % self.g], self.rows[(j0 + 1) % self.g]
        if w < 1e-9:
            return list(r0)
        iw = 1.0 - w
        return [a * iw + b * w for a, b in zip(r0, r1)]


class OctaveStack:
    """Octaves at grids 8,16,...: low(y) = octaves 0-2 (blotches), mid(y) = 3-4 (5-20 cm), fine(y) = rest (< 2 cm)."""

    def __init__(self, rng, size, first_grid=8, count=8):
        self.octaves = [PeriodicNoise(rng, min(first_grid << i, size), size) for i in range(count)]

    def bands(self, y):
        rows = [o.row(y) for o in self.octaves]

        def fbm(idx):
            out = [0.0] * len(rows[0])
            total = 0.0
            for k, i in enumerate(idx):
                a = 0.5 ** k
                total += a
                r = rows[i]
                out = [o + a * v for o, v in zip(out, r)]
            return [o / total for o in out]

        return fbm([0, 1, 2]), fbm([3, 4]), fbm(list(range(5, len(rows))))


def vnoise(s, t, seed):
    """Hashed lattice value noise in [-1, 1] at arbitrary (s, t); block-local coordinates keep it continuous across the tile wrap."""
    i = math.floor(s)
    j = math.floor(t)
    fs = s - i
    ft = t - j
    fs = fs * fs * (3.0 - 2.0 * fs)
    ft = ft * ft * (3.0 - 2.0 * ft)

    def h(ix, iy):
        n = (ix * 374761393 + iy * 668265263 + seed * 2246822519) & 0xFFFFFFFF
        n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
        n ^= n >> 16
        return n / 2147483647.5 - 1.0

    a = h(i, j)
    b = h(i + 1, j)
    c = h(i, j + 1)
    d = h(i + 1, j + 1)
    top = a + (b - a) * fs
    return top + ((c + (d - c) * fs) - top) * ft


def box_blur_wrap(rows, radius):
    """Separable wrap-around box blur of a list of float lists. Radius in pixels."""
    n = len(rows[0])
    k = 2 * radius + 1

    def blur_line(line):
        ext = line[-radius:] + line + line[:radius]      # line is a list here
        acc = [0.0]
        s = 0.0
        for v in ext:
            s += v
            acc.append(s)
        return [(acc[i + k] - acc[i]) / k for i in range(n)]

    h = [blur_line(list(r)) for r in rows]
    cols = [blur_line(list(c)) for c in zip(*h)]
    del h
    return [array('f', r) for r in zip(*cols)]


# ------------------------------------------------------------------------------------- layout
def partition(rng, total, count, lo, hi, tries=500):
    for _ in range(tries):
        raw = [rng.uniform(lo, hi) for _ in range(count)]
        f = total / sum(raw)
        vals = [v * f for v in raw]
        if all(lo <= v <= hi for v in vals):
            return vals
    return None


def layout_courses(cfg, rng):
    """Running-bond ashlar for one 300 cm tile: course heights vary inside course_h_cm and sum to TILE_CM exactly;
    each course is partitioned into blocks of length_ratio x its height (so the tile wraps seamlessly); course
    offsets are chosen so vertical joints stagger by at least min_joint_stagger_cm from the course below."""
    heights = partition(rng, TILE_CM, cfg['courses'], *cfg['course_h_cm']) or [TILE_CM / cfg['courses']] * cfg['courses']
    lo_r, hi_r = cfg['length_ratio']
    courses = []
    previous_joints = None
    y0 = 0.0
    for c, H in enumerate(heights):
        feasible = [k for k in range(1, 8) if k * lo_r * H <= TILE_CM <= k * hi_r * H]
        k = rng.choice(feasible) if feasible else max(1, round(TILE_CM / (2.5 * H)))
        lengths = partition(rng, TILE_CM, k, lo_r * H, hi_r * H) or [TILE_CM / k] * k
        rng.shuffle(lengths)
        best = None
        for _ in range(80):
            offset = rng.uniform(0.0, TILE_CM)
            joints, x = [], offset
            for L in lengths:
                joints.append(x % TILE_CM)
                x += L
            score = 1e9 if previous_joints is None else min(min(abs(((a - b + TILE_CM / 2) % TILE_CM) - TILE_CM / 2) for b in previous_joints) for a in joints)
            if best is None or score > best[0]:
                best = (score, offset, joints)
            if score >= cfg['min_joint_stagger_cm']:
                break
        _, offset, joints = best
        previous_joints = joints
        blocks = []
        x = offset
        for L in lengths:
            dressing = choose(rng, list(cfg['dressing'].items()))
            direction = choose(rng, list(cfg['stroke_dir'].items()))
            wobble = math.radians(rng.uniform(-cfg['stroke_wobble_deg'], cfg['stroke_wobble_deg']))
            angle = wobble if direction == 'horizontal' else math.pi / 2 + wobble
            family, _, value_f, br_shift = choose(rng, [((f, w, vf, bs), w) for f, w, vf, bs in cfg['families']])
            br, bg, bb = cfg['base_srgb']
            value = value_f * (1.0 + rng.uniform(-cfg['value_jitter'], cfg['value_jitter']))
            b_r = bb / br + br_shift + rng.uniform(-cfg['br_jitter'], cfg['br_jitter'])
            # hue stays on the cream -> honey axis: G/R follows B/R (less blue = warmer = a little less green too), tiny independent jitter
            gr = bg / br + 0.45 * (b_r - bb / br) + rng.uniform(-cfg['gr_jitter'], cfg['gr_jitter'])
            r = br * value
            tint = (min(0.98, r), min(0.98, r * gr), min(0.98, r * b_r))
            block = dict(x0=x % TILE_CM, L=L, y0=y0, H=H, dressing=dressing, family=family, angle=angle, tint=tint,
                         base=rng.uniform(-cfg['base_offset_cm'], cfg['base_offset_cm']),
                         tilt_u=rng.uniform(-cfg['tilt'], cfg['tilt']), tilt_v=rng.uniform(-cfg['tilt'], cfg['tilt']),
                         stria_amp=rng.uniform(*cfg['stria_amp_cm'][dressing]), stria_across=rng.uniform(*cfg['stria_across_cm'][dressing]),
                         stria_along=rng.uniform(*cfg['stria_along_cm']), stria_seed=rng.randrange(1, 1 << 30), streak_seed=rng.randrange(1, 1 << 30),
                         weathering=rng.uniform(*cfg['weathering']),
                         rough=cfg['rough'][dressing] + rng.uniform(-cfg['rough_jitter'], cfg['rough_jitter']), chips=[], pores=[])
            jw = cfg['joint_cm'] / 2.0
            if rng.random() < cfg['chip_chance']:
                for _ in range(rng.randint(*cfg['chips_per_block'])):
                    R = rng.uniform(*cfg['chip_radius_cm'])
                    edge = rng.choice(['top', 'bottom', 'left', 'right'])
                    if edge in ('top', 'bottom'):
                        pu, pv = rng.uniform(R, L - R), (H if edge == 'top' else 0.0)
                    else:
                        pu, pv = (L if edge == 'right' else 0.0), rng.uniform(R, H - R)
                    block['chips'].append((pu, pv, R, rng.uniform(*cfg['chip_depth_cm'])))
            area = L * H
            for _ in range(int(area * cfg['pore_density_per_cm2'] * rng.uniform(0.5, 1.5))):
                R = rng.uniform(*cfg['pore_radius_cm'])
                m = jw + R + 0.4
                if L - 2 * m > 0 and H - 2 * m > 0:
                    block['pores'].append((rng.uniform(m, L - m), rng.uniform(m, H - m), R, R * rng.uniform(0.4, 0.7)))
            blocks.append(block)
            x += L
        courses.append(blocks)
        y0 += H
    return heights, courses


# ------------------------------------------------------------------------------------- render
def generate(name, cfg, size, log):
    t0 = time.time()
    rng = random.Random(cfg['seed'])
    px = TILE_CM / size                      # cm per pixel
    heights, courses = layout_courses(cfg, rng)
    bounds = []
    acc = 0.0
    for H in heights:
        bounds.append(acc)
        acc += H
    noise = OctaveStack(random.Random(cfg['seed'] * 7 + 1), size)
    flat_blocks = [b for c in courses for b in c]
    for i, b in enumerate(flat_blocks):
        b['id'] = i
    if len(flat_blocks) > 255:
        raise RuntimeError('block ids are stored as bytes; %d blocks exceed 255' % len(flat_blocks))
    log('  layout: %d courses (%s cm), %d blocks, lengths %.0f-%.0f cm, %d chips, %d pores' % (
        len(courses), '/'.join('%.0f' % h for h in heights), len(flat_blocks), min(b['L'] for b in flat_blocks), max(b['L'] for b in flat_blocks),
        sum(len(b['chips']) for b in flat_blocks), sum(len(b['pores']) for b in flat_blocks)))

    jw = cfg['joint_cm'] / 2.0
    arris = cfg['arris_cm']
    depth = cfg['joint_depth_cm']
    und = cfg['undulation_cm']

    def course_of(yc):
        c = len(bounds) - 1
        while c > 0 and yc < bounds[c]:
            c -= 1
        return c

    height, face_rel, block_id, stria_rows = [], [], [], []
    low_rows, mid_rows, fine_rows = [], [], []
    for y in range(size):
        yc = (y + 0.5) * px
        c = course_of(yc)
        H = heights[c]
        v = yc - bounds[c]
        dv = min(v, H - v)
        low, mid, fine = noise.bands(y)
        low_rows.append(array('f', low)); mid_rows.append(array('f', mid)); fine_rows.append(array('f', fine))
        h_row = [0.0] * size
        f_row = [0.0] * size
        id_row = [0] * size
        s_row = [0.0] * size
        for b in courses[c]:
            x0, L = b['x0'], b['L']
            xa = int(math.ceil(x0 / px - 0.5))
            xb = int(math.ceil((x0 + L) / px - 0.5))
            segs = [(xa, xb, x0)] if xb <= size else [(xa, size, x0), (0, xb - size, x0 - TILE_CM)]
            base = b['base'] + b['tilt_v'] * (v - H / 2)
            tu = b['tilt_u']
            angle0 = b['angle']
            amp, across, along, seed = b['stria_amp'], b['stria_across'], b['stria_along'], b['stria_seed']
            patch = cfg['stria_patch_cm']
            angle_var = math.radians(cfg['stroke_angle_var_deg'])
            bid = b['id']
            for xa, xb, xoff in segs:
                for x in range(max(0, xa), min(size, xb)):
                    u = (x + 0.5) * px - xoff
                    d = min(u, L - u, dv)              # distance to the nearest joint centreline
                    id_row[x] = bid
                    if d < jw:
                        h_row[x] = -depth + 0.03 * fine[x]
                        continue
                    # chisel dressing: anisotropic hashed noise, fine across the stroke, long along it; a second octave breaks the strokes up
                    # stroke direction drifts a few degrees across the face (patches of strokes, not one brushed sheet)
                    ang = angle0 + angle_var * vnoise(u / patch + 11.1, v / patch + 7.3, seed + 3)
                    ca, sa = math.cos(ang), math.sin(ang)
                    s = u * ca + v * sa
                    t = -u * sa + v * ca
                    stria = vnoise(s / across, t / along, seed) + 0.45 * vnoise(s / (across * 0.55) + 17.3, t / (along * 0.4) + 5.1, seed + 1)
                    # gaps between strokes and patchy amplitude over ~stria_patch_cm
                    gap = 0.35 + 0.65 * min(1.0, abs(vnoise(s / (across * 3.0) + 2.2, t / (along * 0.7) + 9.4, seed + 4)) * 1.8)
                    stria *= gap * max(0.2, 0.6 + 0.4 * vnoise(u / patch + 3.7, v / patch + 1.9, seed + 2)) * (1.0 + 0.3 * mid[x])
                    s_row[x] = stria
                    face = base + tu * (u - L / 2) + und * low[x] + amp * stria + 0.006 * fine[x]
                    df = d - jw
                    if df < arris:
                        w = smoothstep(df / arris)
                        h_row[x] = -depth * (1.0 - w) + face * w
                        f_row[x] = w
                    else:
                        h_row[x] = face
                        f_row[x] = 1.0
        height.append(array('f', h_row)); face_rel.append(array('f', f_row)); block_id.append(array('B', id_row)); stria_rows.append(array('f', s_row))
    log('  height pass %.1fs' % (time.time() - t0))

    # edge chips (own block only, may eat the arris) and sparse pores: stamped bowls with wrap
    chip_mask = [array('f', bytes(4 * size)) for _ in range(size)]
    pore_mask = [array('f', bytes(4 * size)) for _ in range(size)]

    def stamp(b, cx_cm, cy_cm, R, dep, mask, power, own_only):
        cx, cy, r_px = cx_cm / px, cy_cm / px, R / px
        for yy in range(int(cy - r_px) - 1, int(cy + r_px) + 2):
            dy = (yy + 0.5 - cy) * px
            if abs(dy) >= R:
                continue
            row, mrow, frow, irow = height[yy % size], mask[yy % size], face_rel[yy % size], block_id[yy % size]
            for xx in range(int(cx - r_px) - 1, int(cx + r_px) + 2):
                dx = (xx + 0.5 - cx) * px
                q = (dx * dx + dy * dy) / (R * R)
                if q >= 1.0:
                    continue
                xi = xx % size
                if frow[xi] <= 0.0 or (own_only and irow[xi] != b['id']):
                    continue
                bowl = (1.0 - q) ** power
                row[xi] -= dep * bowl * frow[xi]
                mrow[xi] = max(mrow[xi], bowl)

    for b in flat_blocks:
        for (pu, pv, R, dep) in b['chips']:
            stamp(b, b['x0'] + pu, b['y0'] + pv, R, dep, chip_mask, 1.3, True)
        for (pu, pv, R, dep) in b['pores']:
            stamp(b, b['x0'] + pu, b['y0'] + pv, R, dep, pore_mask, 2.0, False)
    log('  chips/pores %.1fs' % (time.time() - t0))

    # normal from physical slopes (cm/cm), central differences, wrap
    normal_rows = []
    inv2 = 1.0 / (2.0 * px)
    for y in range(size):
        up, dn, row = height[(y - 1) % size], height[(y + 1) % size], height[y]
        out = bytearray(3 * size)
        for x in range(size):
            gx = (row[(x + 1) % size] - row[x - 1]) * inv2
            gy = (dn[x] - up[x]) * inv2
            inv = 1.0 / math.sqrt(gx * gx + gy * gy + 1.0)
            out[3 * x] = int(-gx * inv * 127.5 + 127.5 + 0.5)
            out[3 * x + 1] = int(-gy * inv * 127.5 + 127.5 + 0.5)
            out[3 * x + 2] = min(255, int(inv * 127.5 + 127.5 + 0.5))
        normal_rows.append(out)
    log('  normal %.1fs' % (time.time() - t0))

    # ambient occlusion: cavity term at two radii (joints ~ 2 cm, pores/chips ~ 0.6 cm) plus a little joint darkening
    blur_big = box_blur_wrap(height, max(2, int(round(2.0 / px))))
    blur_small = box_blur_wrap(height, max(1, int(round(0.6 / px))))
    gain, floor_ = cfg['ao_gain'], cfg['ao_floor']
    ao_rows = []
    for y in range(size):
        h, bb, bs, f = height[y], blur_big[y], blur_small[y], face_rel[y]
        ao_rows.append(array('f', [max(floor_, min(1.0, 1.0 - gain * max(0.0, bb[x] - h[x]) - 0.8 * gain * max(0.0, bs[x] - h[x]) - 0.10 * (1.0 - f[x]))) for x in range(size)]))
    del blur_big, blur_small
    log('  ao %.1fs' % (time.time() - t0))

    # albedo / roughness / ARM
    rcl = cfg['rough_clamp']
    rough_c = cfg['rough']
    grain = cfg['rough_grain']
    mot_low, mot_mid, mot_fine = cfg['mottle']
    mortar_f, mortar_grey = cfg['mortar_factor'], cfg['mortar_grey']
    w_dark, w_band, streak_amp = cfg['weather_dark'], cfg['weather_band'], cfg['streak']
    albedo_rows, rough_rows, arm_rows = [], [], []
    for y in range(size):
        yc = (y + 0.5) * px
        c = course_of(yc)
        H = heights[c]
        v = yc - bounds[c]
        # world-down is small v: the lower part of every block darkens (dust, splash, run-off), fading upward over weather_band of the height
        ramp = smoothstep(max(0.0, min(1.0, (w_band * H - v) / (w_band * H))))
        low, mid, fine, f, ids, cm_, pm, ao, st = low_rows[y], mid_rows[y], fine_rows[y], face_rel[y], block_id[y], chip_mask[y], pore_mask[y], ao_rows[y], stria_rows[y]
        a_out = bytearray(3 * size)
        r_out = bytearray(3 * size)
        arm_out = bytearray(3 * size)
        for x in range(size):
            b = flat_blocks[ids[x]]
            face = f[x]
            chip, pore = cm_[x], pm[x]
            u = ((x + 0.5) * px - b['x0']) % TILE_CM
            # faint vertical streaks (long along v, narrow along u), stronger where the block weathers more
            streak = vnoise(u / 3.0, v / 40.0, b['streak_seed'])
            weather = b['weathering'] * (w_dark * ramp * (0.75 + 0.25 * streak) + streak_amp * streak)
            # roughness
            rough = b['rough'] + 0.03 * st[x] + 0.04 * ramp * b['weathering'] + grain * fine[x]
            rough = rough * face + rough_c['mortar'] * (1.0 - face)
            rough += (rough_c['chip'] - rough) * 0.7 * chip + (rough_c['pore'] - rough) * 0.8 * pore
            rough = max(rcl[0], min(rcl[1], rough))
            # albedo (sRGB space): block tint x mottle x weathering; chips a shade fresher; pores a shade darker
            tr, tg, tb = b['tint']
            m = (1.0 + mot_low * low[x] + mot_mid * mid[x] + mot_fine * fine[x] + 0.012 * st[x]) * (1.0 - weather)
            m *= 1.0 + 0.04 * chip - 0.10 * pore
            r, g, bl = tr * m, tg * m, tb * m
            if face < 1.0:
                # mortar: the adjoining stone at mortar_factor, pulled a little toward grey, fine grain; recess reads darker via AO
                lum = 0.2126 * tr + 0.7152 * tg + 0.0722 * tb
                mr, mg, mb = (tr + (lum - tr) * mortar_grey) * mortar_f, (tg + (lum - tg) * mortar_grey) * mortar_f, (tb + (lum - tb) * mortar_grey) * mortar_f
                gr_ = 1.0 + 0.06 * fine[x]
                r = r * face + mr * gr_ * (1.0 - face)
                g = g * face + mg * gr_ * (1.0 - face)
                bl = bl * face + mb * gr_ * (1.0 - face)
            a_out[3 * x] = int(max(0.0, min(1.0, r)) * 255.0 + 0.5)
            a_out[3 * x + 1] = int(max(0.0, min(1.0, g)) * 255.0 + 0.5)
            a_out[3 * x + 2] = int(max(0.0, min(1.0, bl)) * 255.0 + 0.5)
            rv = int(rough * 255.0 + 0.5)
            r_out[3 * x] = r_out[3 * x + 1] = r_out[3 * x + 2] = rv
            arm_out[3 * x] = int(ao[x] * 255.0 + 0.5)
            arm_out[3 * x + 1] = rv
            arm_out[3 * x + 2] = 0
        albedo_rows.append(a_out); rough_rows.append(r_out); arm_rows.append(arm_out)
    log('  albedo/roughness/ARM %.1fs' % (time.time() - t0))

    ao_png = [bytearray(b for v in row for b in (int(v * 255 + 0.5),) * 3) for row in ao_rows]
    hmin = min(min(r) for r in height)
    hmax = max(max(r) for r in height)
    hscale = 255.0 / max(1e-6, hmax - hmin)
    height_png = [bytearray(b for v in row for b in (int((v - hmin) * hscale + 0.5),) * 3) for row in height]
    face_mask = [bytes(1 if v >= 0.999 else 0 for v in row) for row in face_rel]

    maps = {'Albedo': albedo_rows, 'Normal': normal_rows, 'ARM': arm_rows, 'Roughness': rough_rows, 'AO': ao_png, 'Height': height_png}
    lengths = [b['L'] for b in flat_blocks]
    schedule = {'courseHeightsCm': [round(h, 2) for h in heights], 'courses': len(courses), 'blocks': len(flat_blocks),
                'blockLengthCmMinMax': [round(min(lengths), 2), round(max(lengths), 2)], 'blockLengthCmMean': round(sum(lengths) / len(lengths), 2),
                'lengthToHeightMinMax': [round(min(b['L'] / b['H'] for b in flat_blocks), 2), round(max(b['L'] / b['H'] for b in flat_blocks), 2)],
                'dressingCounts': dict(Counter(b['dressing'] for b in flat_blocks)), 'familyCounts': dict(Counter(b['family'] for b in flat_blocks)),
                'chips': sum(len(b['chips']) for b in flat_blocks), 'pores': sum(len(b['pores']) for b in flat_blocks),
                'jointCm': cfg['joint_cm'], 'jointDepthCm': cfg['joint_depth_cm'], 'arrisCm': cfg['arris_cm'], 'heightRangeCm': [round(hmin, 3), round(hmax, 3)],
                'facePixelFraction': round(sum(sum(r) for r in face_mask) / float(size * size), 4)}
    return maps, face_mask, schedule, time.time() - t0


# ------------------------------------------------------------------------------------- stats
def channel_hist(rows, channel, step=3):
    h = Counter()
    for r in rows:
        h.update(r[channel::step])
    return h


def hist_stats(h):
    n = sum(h.values())
    mean = sum(k * c for k, c in h.items()) / n
    var = sum(c * (k - mean) ** 2 for k, c in h.items()) / n
    keys = sorted(h)

    def pct(p):
        target = p / 100.0 * n
        acc = 0
        for k in keys:
            acc += h[k]
            if acc >= target:
                return k
        return keys[-1]

    return {'mean': round(mean / 255.0, 4), 'std': round(math.sqrt(var) / 255.0, 4), 'p5': round(pct(5) / 255.0, 4),
            'p50': round(pct(50) / 255.0, 4), 'p95': round(pct(95) / 255.0, 4), 'min': round(keys[0] / 255.0, 4), 'max': round(keys[-1] / 255.0, 4)}


def _pct(h, p):
    n = sum(h.values())
    target = p / 100.0 * n
    acc = 0
    for k in sorted(h):
        acc += h[k]
        if acc >= target:
            return round(k / 1000.0, 3)
    return None


def normal_stats(rows, mask=None):
    """xy deviation = sqrt(nx^2 + ny^2) of the decoded bytes (1/1000 bins) plus per-channel |n| p95; mask rows (bytes, 1 = keep) optional."""
    mag, absx, absy = Counter(), Counter(), Counter()
    for i, r in enumerate(rows):
        xs, ys = r[0::3], r[1::3]
        if mask is not None:
            m = mask[i]
            xs = bytes(v for v, k in zip(xs, m) if k)
            ys = bytes(v for v, k in zip(ys, m) if k)
        mag.update(int(math.sqrt((x - 127.5) ** 2 + (y - 127.5) ** 2) / 127.5 * 1000.0) for x, y in zip(xs, ys))
        absx.update(int(abs(x - 127.5) / 127.5 * 1000.0) for x in xs)
        absy.update(int(abs(y - 127.5) / 127.5 * 1000.0) for y in ys)
    n = sum(mag.values())
    mean = sum(k * c for k, c in mag.items()) / n / 1000.0
    return {'xyDeviation': {'mean': round(mean, 4), 'p50': _pct(mag, 50), 'p95': _pct(mag, 95), 'p99': _pct(mag, 99), 'max': _pct(mag, 100)},
            'absX_p95': _pct(absx, 95), 'absY_p95': _pct(absy, 95), 'pixels': n}


def measure(maps, face_mask=None):
    alb = {ch: hist_stats(channel_hist(maps['Albedo'], i)) for i, ch in enumerate('RGB')}
    out = {'albedoSRGB': alb, 'albedoStdPerChannelMean': round(sum(alb[c]['std'] for c in 'RGB') / 3.0, 4),
           'albedoChroma': {'GoverR_mean': round(alb['G']['mean'] / alb['R']['mean'], 3), 'BoverR_mean': round(alb['B']['mean'] / alb['R']['mean'], 3)},
           'normal': normal_stats(maps['Normal']), 'roughness': hist_stats(channel_hist(maps['ARM'], 1)), 'ambientOcclusion': hist_stats(channel_hist(maps['ARM'], 0))}
    if face_mask is not None:
        out['normalFaceOnly'] = normal_stats(maps['Normal'], face_mask)
        joint_mask = [bytes(1 - k for k in row) for row in face_mask]
        out['normalJointAndArrisOnly'] = normal_stats(maps['Normal'], joint_mask)
    return out


# ------------------------------------------------------------------------------------- previews
def downsample2(rows):
    size = len(rows)
    out = []
    for y in range(0, size, 2):
        a, b = rows[y], rows[y + 1]
        o = bytearray(3 * (size // 2))
        for x in range(0, size, 2):
            i = 3 * x
            j = 3 * (x // 2)
            o[j] = (a[i] + a[i + 3] + b[i] + b[i + 3] + 2) >> 2
            o[j + 1] = (a[i + 1] + a[i + 4] + b[i + 1] + b[i + 4] + 2) >> 2
            o[j + 2] = (a[i + 2] + a[i + 5] + b[i + 2] + b[i + 5] + 2) >> 2
        out.append(o)
    return out


def lit_preview(albedo, normal, arm, world_orientation=True):
    """Lambert render. world_orientation flips rows so world up is image up (texture v = world Z); the light then comes
    from the upper left of the WORLD view, i.e. from +v / -u in texture terms. 30 % AO ambient + 70 % direct, normalised so
    a flat, unoccluded face shows its albedo unchanged (the render judges relief and colour, not an exposure choice)."""
    lx, ly, lz = -0.55, (0.55 if world_orientation else -0.55), 0.63
    n = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / n, ly / n, lz / n
    lut = [srgb_to_linear(i / 255.0) for i in range(256)]
    out = []
    for a, nr, m in zip(albedo, normal, arm):
        o = bytearray(len(a))
        for x in range(len(a) // 3):
            i = 3 * x
            nx, ny, nz = nr[i] / 127.5 - 1.0, nr[i + 1] / 127.5 - 1.0, nr[i + 2] / 127.5 - 1.0
            ndl = max(0.0, nx * lx + ny * ly + nz * lz)
            shade = 0.30 * (m[i] / 255.0) + 0.70 * ndl / lz
            for k in range(3):
                o[i + k] = int(linear_to_srgb(lut[a[i + k]] * shade) * 255.0 + 0.5)
        out.append(o)
    return out[::-1] if world_orientation else out


# ------------------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--size', type=int, default=DEFAULT_SIZE)
    ap.add_argument('--variant', choices=sorted(VARIANTS), action='append')
    ap.add_argument('--baseline', action='store_true', help='also decode the sandstone_blocks_08 normal PNG and measure it with the same code')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--out', type=Path, default=OUT)
    args = ap.parse_args(argv)
    out = args.out
    receipts = list(out.glob('limestone-v2-import-*.json'))
    if receipts and not args.force:
        raise SystemExit('Refusing to regenerate: native import receipts exist in %s (%s). Use --force only for a new review round.' % (out, [r.name for r in receipts]))
    if args.size & (args.size - 1) or args.size < 64:
        raise SystemExit('size must be a power of two >= 64')
    out.mkdir(parents=True, exist_ok=True)
    started = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    t_start = time.time()

    def log(msg):
        print(msg, flush=True)

    manifest_path = out / ('manifest.json' if args.size == DEFAULT_SIZE else 'manifest-%d.json' % args.size)
    manifest = {'status': 'OFFLINE_GENERATED_NATIVE_IMPORT_PENDING', 'iteration': ITERATION, 'generator': 'Scripts/create_limestone_textures_v2.py',
                'generatorSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'startedUtc': started,
                'tileCm': TILE_CM, 'size': args.size, 'pxPerCm': round(args.size / TILE_CM, 4),
                'conventions': {'uv': 'u = world X|Y / TilingCm, v = world Z / TilingCm; image row 0 = v 0, image down = world up on vertical faces',
                                'normal': 'normalize(-dh/du, -dh/dv, 1), u = column, v = row (DirectX / UE default; flip_green_channel False)',
                                'arm': 'R ambient occlusion, G roughness, B metallic (0)', 'heightsCm': 'physical centimetres, slopes unscaled',
                                'litPreview': 'rows flipped to world orientation (world up = image up), light from the upper left of that view'},
                'importSettings': {'Albedo': {'compression': 'TC_Default', 'srgb': True}, 'Normal': {'compression': 'TC_Normalmap', 'srgb': False, 'flipGreenChannel': False},
                                   'ARM': {'compression': 'TC_Masks', 'srgb': False}, 'notImported': ['Roughness', 'AO', 'Height']},
                'diagnosisBaseline_sandstone_blocks_08': DIAGNOSIS_BASELINE, 'photoReference': PHOTO_REFERENCE, 'variants': {}}
    if manifest_path.exists():      # --variant reruns replace only the regenerated variant; the baseline measurement is kept
        previous = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
        manifest['variants'] = previous.get('variants', {})
        if 'measuredBaselineNormal' in previous:
            manifest['measuredBaselineNormal'] = previous['measuredBaselineNormal']
        manifest['previousRuns'] = previous.get('previousRuns', []) + [{'iteration': previous.get('iteration', 'V2'), 'startedUtc': previous.get('startedUtc'),
                                                                        'finishedUtc': previous.get('finishedUtc'), 'generatorSha256': previous.get('generatorSha256')}]
    if args.baseline:
        t = time.time()
        if BASELINE_NORMAL.exists():
            w, h, rows = decode_png_rgb8(BASELINE_NORMAL)
            manifest['measuredBaselineNormal'] = {'file': rel(BASELINE_NORMAL), 'size': [w, h], **normal_stats(rows),
                                                  'note': 'same statistic code as the V2 maps; compare with diagnosis 0.09', 'seconds': round(time.time() - t, 1)}
            log('baseline normal %s: %s (%.1fs)' % (BASELINE_NORMAL.name, manifest['measuredBaselineNormal']['xyDeviation'], time.time() - t))
        else:
            manifest['measuredBaselineNormal'] = {'missing': str(BASELINE_NORMAL)}
    for name in (args.variant or sorted(VARIANTS)):
        cfg = VARIANTS[name]
        log('generating %s at %d' % (name, args.size))
        maps, face_mask, schedule, seconds = generate(name, cfg, args.size, log)
        record = {'iteration': ITERATION, 'seed': cfg['seed'], 'parameters': cfg, 'schedule': schedule, 'generationSeconds': round(seconds, 1), 'files': {}, 'previews': {}}
        suffix = '' if args.size == DEFAULT_SIZE else '_%d' % args.size
        for kind, rows in maps.items():
            path = out / ('T_LimestoneV2_%s_%s%s.png' % (name, kind, suffix))
            digest = write_png_rgb(path, args.size, args.size, rows)
            record['files'][kind] = {'path': rel(path), 'sha256': digest, 'bytes': path.stat().st_size, 'imported': kind in ('Albedo', 'Normal', 'ARM')}
        log('  wrote maps')
        record['statistics'] = measure(maps, face_mask)
        s = record['statistics']
        log('  stats: albedo std %.4f  mean %.3f/%.3f/%.3f  R p5-p95 %.3f-%.3f  normal p50/p95 %.3f/%.3f  face p50/p95 %.3f/%.3f  rough %.3f-%.3f' % (
            s['albedoStdPerChannelMean'], s['albedoSRGB']['R']['mean'], s['albedoSRGB']['G']['mean'], s['albedoSRGB']['B']['mean'],
            s['albedoSRGB']['R']['p5'], s['albedoSRGB']['R']['p95'], s['normal']['xyDeviation']['p50'], s['normal']['xyDeviation']['p95'],
            s['normalFaceOnly']['xyDeviation']['p50'], s['normalFaceOnly']['xyDeviation']['p95'], s['roughness']['min'], s['roughness']['max']))
        pv = {k: downsample2(v) if args.size > 1024 else v for k, v in maps.items()}
        psize = args.size // 2 if args.size > 1024 else args.size
        for kind, rows in pv.items():
            path = out / 'previews' / ('T_LimestoneV2_%s_%s_%d.png' % (name, kind, psize))
            record['previews'][kind] = {'path': rel(path), 'sha256': write_png_rgb(path, psize, psize, rows)}
        lit = out / 'previews' / ('Lit_%s_%d.png' % (name, psize))
        record['previews']['Lit'] = {'path': rel(lit), 'sha256': write_png_rgb(lit, psize, psize, lit_preview(pv['Albedo'], pv['Normal'], pv['ARM'])), 'orientation': 'world (rows flipped)'}
        log('  previews done, elapsed %.1fs' % (time.time() - t_start))
        manifest['variants'][name] = record
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    manifest['finishedUtc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    log('manifest ' + str(manifest_path))
    return manifest


if __name__ == '__main__':
    main()
