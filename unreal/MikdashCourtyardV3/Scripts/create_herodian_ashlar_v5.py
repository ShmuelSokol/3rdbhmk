"""Herodian ashlar PBR set V4 - the Second Temple outer retaining wall (the Kotel) - procedural, tiling, offline (stdlib only).

Why V4: Shmuel's instruction, verbatim - "I want the temple stones used for wall wherever you are using
stones to be the large style stones used for the 2nd temple outer wall." That is Herodian ashlar. The
V2/V3 set deliberately omitted drafted margins (the coordinator judged them wrong for a hewn Third
Temple wall); this instruction overrides that judgement. V4 builds the Herodian style properly.

The three qualities that decide whether it reads as Herodian, in order:
  1. THE BLOCKS ARE BIG. At the project's TilingCm = 300 that is 3 courses of about 100 cm, and one or
     two blocks per course (about 130-300 cm long), NOT six courses of six blocks. Measured: Western
     Wall ashlars "most about a metre high and two to five metres long" (Wikipedia, Western Wall).
  2. THE DRAFTED MARGIN. A flat, slightly recessed dressed border around all four edges of the face,
     enclosing a central boss standing slightly proud. Measured on Western Temple Mount blocks: margins
     5-10 cm wide, boss 6-14 mm proud; Hebron comparanda 5.5-11.5 cm and 0.9-1.5 cm (Madain Project;
     "Decorative Drafted-margin Masonry in Jerusalem and Hebron"). Upper margins tend to be wider than
     lower ones - reproduced. The boss is SMOOTH and finely dressed, not rusticated: crisp arrises,
     the finest masonry in the ancient Levant.
  3. THE COURSES STEP BACK. Each course is set back behind the one below (measured: about half an inch,
     ~1.3 cm, Ritmeyer / BAS), giving the wall its batter. In a tiling texture an accumulating setback
     cannot wrap, so it is authored as a LOCAL LEDGE: the top of each stone leans out over the bed joint
     and the course above starts flush, which is exactly the shadow-and-lit-ledge the setback produces in
     raking light. Amount authored at setbackCm (above the measured 1.3 cm) so it survives game viewing
     distance. Marked authored in sources.md.
Joints are dry: a fine dark line (0.5-0.8 cm), no mortar band. Colour is calibrated on the accepted
Kotel photo texture exactly as V3 was (SourceAssets/kotel-detail/PhotoSurfaceV1/kotel-wall-cleaned.png:
sRGB means 0.728/0.635/0.515, G/R 0.875, B/R 0.71) - the project already accepted that palette.

What it writes (SourceAssets/material-review/HerodianAshlarV5/):
  T_HerodianV4_<Variant>_Albedo.png   sRGB colour               (import: TC_Default, sRGB on)
  T_HerodianV4_<Variant>_Normal.png   tangent-space normal      (import: TC_Normalmap, sRGB off, no green flip)
  T_HerodianV4_<Variant>_ARM.png      R ambient occlusion, G roughness, B metallic (0)  (TC_Masks, sRGB off)
  T_HerodianV4_<Variant>_Roughness.png / _AO.png / _Height.png   review copies, NOT imported
  previews/<name>_1024.png            1024 box-filtered preview of every map (texture orientation)
  previews/Lit_<Variant>_1024.png     software Lambert render in WORLD orientation, albedo-preserving
  manifest.json                       parameters, hashes, measured statistics (merged per variant)
Variants: Ashlar (the wall field: 3 courses of ~100 cm, 1-2 blocks each) and Trim (cornices, jambs,
lintels: 5 courses of ~60 cm, 2-3 blocks each, same drafting, finer dressing).

Scale: TilingCm = 300 on both instances (unchanged from V2/V3, and unchanged on the shared parents), so
one 2048 tile spans 300 x 300 cm at 6.827 px/cm and course lines fall on the same world-Z levels on
every wall - which is what coursed masonry does. Block sizes in centimetres are reported in
manifest.json -> variants.<name>.schedule (courseHeightsCm, blockLengthCmMinMax).

Conventions (must match M_PBR_Tiled, release_pbr_architecture.py build_master_material) - identical to V2:
  * Texture u = world X (or Y), v = world Z, both / TilingCm; image row 0 is v = 0, so IMAGE DOWN IS
    WORLD UP on vertical faces. Gravity-driven weathering darkens toward DECREASING row index within a course.
  * Normal = normalize(-dh/du, -dh/dv, 1) with u = column, v = row index (DirectX / UE default green).
    flip_green_channel must stay False.
  * Heights are centimetres; slopes are physical (cm per cm), no artificial gain.
  * Memory: every per-pixel map is stored as array('f')/array('B'), never a list of Python floats. The
    V2/V3 run was killed for RAM before that change; do not undo it.

Statistics (same code and the same fields as the V3 pass, so the comparison is numeric): sRGB albedo
per-channel mean/std/p5/p50/p95, G/R and B/R of the means against the Kotel photo, normal xy deviation
p50/p95 over the WHOLE map and over face-only pixels, and additionally boss-only and margin-only, plus
roughness p5/p50/p95 and AO. --baseline decodes the sandstone_blocks_08 normal PNG with the same code.

Run (about 4 minutes per variant at 2048; pure Python, no numpy/PIL in the bundled interpreter):
  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\ThirdParty\\Python3\\Win64\\python.exe" Scripts\\create_herodian_ashlar_v4.py [--size 512] [--variant Ashlar] [--baseline]
Refuses to overwrite once SourceAssets/material-review/HerodianAshlarV4/ holds a native import receipt
(herodian-v5-import-*.json) unless --force is given.
"""
import argparse
import hashlib
import json
import math
import random
import struct
import time
import zlib
from array import array
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets' / 'material-review' / 'HerodianAshlarV5'
BASELINE_NORMAL = ROOT / 'SourceAssets' / 'materials-pbr' / 'limestone-ashlar' / 'sandstone_blocks_08_normal_2k.png'
TILE_CM = 300.0            # TilingCm of MI_PBR_LimestoneAshlar / MI_PBR_LimestoneTrim and of the V4 children
DEFAULT_SIZE = 2048
ITERATION = 'V5-HerodianGrain'

PHOTO_REFERENCE = {      # measured by the V2/V3 statistics code on the accepted Kotel photo derivative
    'file': 'SourceAssets/kotel-detail/PhotoSurfaceV1/kotel-wall-cleaned.png', 'meanSRGB': [0.728, 0.635, 0.515],
    'medianSRGB': [0.761, 0.663, 0.533], 'chromaGoverR_p5_p50_p95': [0.788, 0.875, 0.928], 'chromaBoverR_p5_p50_p95': [0.537, 0.71, 0.82],
    'luminance_p25_p50_p75': [0.584, 0.671, 0.733],
    'note': 'AI-cleaned photo derivative with lighting partly baked in (PROVENANCE.md); used for warmth and value spread, not copied.'}

V3_COMPARISON = {        # SourceAssets/material-review/LimestoneV2/manifest.json (iteration V3), for the report table
    'Ashlar': {'albedoMeanSRGB': [0.7447, 0.6491, 0.5259], 'albedoStdPerChannelMean': 0.0549, 'albedoR_p5_p95': [0.6196, 0.8314],
               'GoverR': 0.872, 'BoverR': 0.706, 'normalXy_p50_p95': [0.099, 0.451], 'normalFaceXy_p50_p95': [0.099, 0.368],
               'roughness_p5_p50_p95': [0.5882, 0.651, 0.7961], 'courses': 6, 'blocks': 19, 'courseHeightsCm': [41.4, 56.6], 'blockLengthCm': [71.97, 115.54]},
    'Trim': {'albedoMeanSRGB': [0.7896, 0.6971, 0.5743], 'albedoStdPerChannelMean': 0.0466, 'albedoR_p5_p95': [0.6824, 0.851],
             'GoverR': 0.883, 'BoverR': 0.727, 'normalXy_p50_p95': [0.044, 0.278], 'normalFaceXy_p50_p95': [0.043, 0.193],
             'roughness_p5_p50_p95': [0.5529, 0.5922, 0.7176], 'courses': 8, 'blocks': 25, 'courseHeightsCm': [32.17, 41.39], 'blockLengthCm': [75.0, 113.01]}}

DIAGNOSIS_BASELINE = {   # release_lighting_v3.spec.json diagnosis.textureMeasured, the CC0 stand-in V2 replaced
    'albedoMeanSRGB': [0.647, 0.574, 0.456], 'albedoStdPerChannel': 0.021, 'albedoR_p5_p95': [0.62, 0.68],
    'normalXyDeviationP95': 0.09, 'roughness': '0.50 +- 0.02 (uniform)'}

VARIANTS = {
    # ---- Ashlar: the main wall. 3 courses of ~100 cm; 1 block (300 cm) or 2 blocks (~130-170 cm) per course.
    'Ashlar': dict(
        seed=6120, courses=3, course_h_cm=(88.0, 116.0), blocks_per_course={1: 0.55, 2: 0.45},
        length_ratio=(1.25, 3.20), min_joint_stagger_cm=45.0,
        joint_cm=0.8, joint_depth_cm=1.35, arris_cm=0.55,
        # drafted margin: width per edge, top wider than the sides, bottom slightly narrower (measured tendency)
        margin_cm=(8.0, 12.0), margin_top_factor=1.25, margin_bottom_factor=0.92, margin_side_jitter=0.12,
        boss_proud_cm=(3.20, 4.60), boss_edge_cm=1.90,
        setback_cm=1.5, setback_extra_cm=6.0,
        # dressing amplitudes are LOW: the boss is smoothly dressed, not rusticated
        boss_stria_amp_cm=(0.070, 0.115), boss_stria_across_cm=(0.40, 0.70), boss_stria_along_cm=(0.50, 0.90),
        margin_stria_amp_cm=(0.014, 0.026), margin_stria_across_cm=(0.26, 0.42), margin_stria_along_cm=(1.2, 2.2),
        stroke_dir={'vertical': 0.55, 'horizontal': 0.45}, stroke_wobble_deg=5.0, stria_patch_cm=11.0,
        base_offset_cm=0.30, tilt=0.0026, undulation_cm=0.115, boss_dish_cm=-0.55, grain_cm=0.075,
        # hand-cut, not CAD: the joint line and the drafted-margin edge wander a little along each edge
        edge_wobble_cm=0.13, edge_wobble_scale_cm=55.0, margin_wobble_cm=0.42, margin_wobble_scale_cm=48.0,
        chip_chance=0.85, chips_per_block=(2, 5), chip_radius_cm=(1.8, 5.5), chip_depth_cm=(0.25, 0.75),
        pore_density_per_cm2=0.030, pore_radius_cm=(0.11, 1.05), pore_size_shape=2.6,
        pore_patch_cm=17.0, pore_patch_cut=-0.22,
        pore_albedo=0.21, pore_rim=0.018,
        grit=(0.098, 5.4, 0.070, 1.95), grit_rough=0.075,
        weathering=(0.20, 0.62), weather_dark=0.085, weather_band=0.38, streak=0.030,
        bio_amount=0.12, bio_band=0.28, bio_grid=6, bio_tint=(0.74, 0.80, 0.70), bio_rough=0.05,
        # broad patina blotches inside each stone, so a 3 m tile is not four flat panels
        patina=0.040, patina_scale_cm=34.0, patina_fine=0.030, patina_fine_scale_cm=3.2,
        # palette: photo-calibrated (target means 0.728/0.635/0.515, G/R 0.875, B/R 0.71 after weathering)
        base_srgb=(0.7523, 0.7175, 0.6631), value_jitter=0.075, gr_jitter=0.012, br_jitter=0.030,
        families=[('base', 0.44, 1.0, 0.0), ('cream', 0.20, 1.12, 0.016), ('honey', 0.22, 0.900, -0.034), ('greygold', 0.14, 0.950, 0.038)],
        margin_light=0.055, mottle=(0.040, 0.080, 0.052), joint_factor=0.46, joint_grey=0.22,
        rough={'boss': 0.760, 'margin': 0.790, 'joint': 0.88, 'chip': 0.86, 'pore': 0.90}, rough_jitter=0.028, rough_grain=0.030, rough_clamp=(0.62, 0.94),
        ao_gain=0.95, ao_floor=0.42, ao_wide_cm=9.0, ao_wide_gain=0.80),
    # ---- Trim: cornices, jambs, lintels. 5 courses of ~60 cm; 2-3 blocks each (~100-150 cm). Same drafting, finer.
    'Trim': dict(
        seed=6121, courses=5, course_h_cm=(52.0, 68.0), blocks_per_course={2: 0.55, 3: 0.45},
        length_ratio=(1.45, 2.70), min_joint_stagger_cm=26.0,
        joint_cm=0.5, joint_depth_cm=0.95, arris_cm=0.40,
        margin_cm=(6.0, 9.0), margin_top_factor=1.22, margin_bottom_factor=0.94, margin_side_jitter=0.10,
        boss_proud_cm=(2.30, 3.30), boss_edge_cm=1.45,
        setback_cm=1.05, setback_extra_cm=4.0,
        boss_stria_amp_cm=(0.048, 0.082), boss_stria_across_cm=(0.32, 0.54), boss_stria_along_cm=(0.40, 0.72),
        margin_stria_amp_cm=(0.010, 0.020), margin_stria_across_cm=(0.22, 0.34), margin_stria_along_cm=(1.0, 1.9),
        stroke_dir={'vertical': 0.40, 'horizontal': 0.60}, stroke_wobble_deg=4.0, stria_patch_cm=9.0,
        base_offset_cm=0.16, tilt=0.0018, undulation_cm=0.075, boss_dish_cm=-0.38, grain_cm=0.055,
        edge_wobble_cm=0.08, edge_wobble_scale_cm=40.0, margin_wobble_cm=0.26, margin_wobble_scale_cm=34.0,
        chip_chance=0.55, chips_per_block=(1, 3), chip_radius_cm=(1.0, 3.0), chip_depth_cm=(0.16, 0.45),
        pore_density_per_cm2=0.022, pore_radius_cm=(0.09, 0.78), pore_size_shape=2.8,
        pore_patch_cm=13.0, pore_patch_cut=-0.20,
        pore_albedo=0.17, pore_rim=0.014,
        grit=(0.078, 4.4, 0.056, 1.65), grit_rough=0.060,
        weathering=(0.14, 0.52), weather_dark=0.060, weather_band=0.34, streak=0.020,
        bio_amount=0.08, bio_band=0.24, bio_grid=8, bio_tint=(0.76, 0.82, 0.72), bio_rough=0.035,
        patina=0.028, patina_scale_cm=24.0, patina_fine=0.022, patina_fine_scale_cm=2.8,
        base_srgb=(0.7860, 0.7530, 0.7027), value_jitter=0.062, gr_jitter=0.010, br_jitter=0.022,
        families=[('base', 0.54, 1.0, 0.0), ('cream', 0.22, 1.09, 0.012), ('honey', 0.14, 0.925, -0.026), ('greygold', 0.10, 0.955, 0.032)],
        margin_light=0.045, mottle=(0.038, 0.068, 0.040), joint_factor=0.50, joint_grey=0.22,
        rough={'boss': 0.735, 'margin': 0.770, 'joint': 0.86, 'chip': 0.84, 'pore': 0.88}, rough_jitter=0.022, rough_grain=0.026, rough_clamp=(0.60, 0.93),
        ao_gain=1.00, ao_floor=0.46, ao_wide_cm=7.5, ao_wide_gain=0.80),
}

# region codes stored per pixel (byte array)
R_JOINT, R_ARRIS, R_MARGIN, R_BEVEL, R_BOSS = 0, 1, 2, 3, 4


# ----------------------------------------------------------------------------------------- PNG
def write_png_rgb(path, width, height, rows):
    """rows: sequence of bytearrays, 3*width bytes each. Same stdlib writer as create_limestone_textures_v2.py."""
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
    """8-bit RGB/RGBA, non-interlaced, all five filters (create_limestone_textures_v2.py decoder)."""
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
    """Hashed lattice value noise in [-1, 1]; block-local coordinates keep it continuous across the tile wrap."""
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
    """Separable wrap-around box blur of a list of float arrays. Radius in pixels."""
    n = len(rows[0])
    k = 2 * radius + 1

    def blur_line(line):
        ext = line[-radius:] + line + line[:radius]
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
def partition(rng, total, count, lo, hi, tries=800):
    for _ in range(tries):
        raw = [rng.uniform(lo, hi) for _ in range(count)]
        f = total / sum(raw)
        vals = [v * f for v in raw]
        if all(lo <= v <= hi for v in vals):
            return vals
    return None


def draw_block_surface(cfg, rng, L, H, x, y0):
    """Every per-block SURFACE draw of one stone, in exactly the order layout_courses has always made
    them, so the V5 stream (one rng for layout and surface) is unchanged byte for byte.

    Split out 2026-09-10 for the anti-repeat tile variants: layout_courses calls it with the layout rng
    (V5 itself), and reroll_surface calls it again with a separate surface rng for a variant. x0, L,
    y0, H are the stone's position and size (layout, fixed); everything this function draws is surface."""
    mlo, mhi = cfg['margin_cm']
    direction = choose(rng, list(cfg['stroke_dir'].items()))
    wobble = math.radians(rng.uniform(-cfg['stroke_wobble_deg'], cfg['stroke_wobble_deg']))
    angle = wobble if direction == 'horizontal' else math.pi / 2 + wobble
    family, _, value_f, br_shift = choose(rng, [((f, w, vf, bs), w) for f, w, vf, bs in cfg['families']])
    br, bg, bb = cfg['base_srgb']
    value = value_f * (1.0 + rng.uniform(-cfg['value_jitter'], cfg['value_jitter']))
    b_r = bb / br + br_shift + rng.uniform(-cfg['br_jitter'], cfg['br_jitter'])
    # hue stays on the cream -> honey axis: G/R follows B/R, tiny independent jitter
    gr = bg / br + 0.45 * (b_r - bb / br) + rng.uniform(-cfg['gr_jitter'], cfg['gr_jitter'])
    r = br * value
    tint = (min(0.98, r), min(0.98, r * gr), min(0.98, r * b_r))
    jw = cfg['joint_cm'] / 2.0
    m0 = rng.uniform(mlo, mhi)
    j = cfg['margin_side_jitter']
    mw_l = m0 * (1.0 + rng.uniform(-j, j))
    mw_r = m0 * (1.0 + rng.uniform(-j, j))
    mw_t = m0 * cfg['margin_top_factor'] * (1.0 + rng.uniform(-j, j))
    mw_b = m0 * cfg['margin_bottom_factor'] * (1.0 + rng.uniform(-j, j))
    # the boss must survive on small blocks: leave at least 8 cm of boss in each axis
    cap_u = max(2.0, (L / 2.0 - jw - 4.0))
    cap_v = max(2.0, (H / 2.0 - jw - 4.0))
    mw_l, mw_r = min(mw_l, cap_u), min(mw_r, cap_u)
    mw_t, mw_b = min(mw_t, cap_v), min(mw_b, cap_v)
    block = dict(
        x0=x % TILE_CM, L=L, y0=y0, H=H, family=family, angle=angle, tint=tint,
        marginCm=[round(mw_l, 2), round(mw_r, 2), round(mw_b, 2), round(mw_t, 2)],
        mw_l=mw_l, mw_r=mw_r, mw_b=mw_b, mw_t=mw_t,
        boss_proud=rng.uniform(*cfg['boss_proud_cm']),
        base=rng.uniform(-cfg['base_offset_cm'], cfg['base_offset_cm']),
        tilt_u=rng.uniform(-cfg['tilt'], cfg['tilt']), tilt_v=rng.uniform(-cfg['tilt'], cfg['tilt']),
        boss_amp=rng.uniform(*cfg['boss_stria_amp_cm']), boss_across=rng.uniform(*cfg['boss_stria_across_cm']),
        boss_along=rng.uniform(*cfg['boss_stria_along_cm']),
        marg_amp=rng.uniform(*cfg['margin_stria_amp_cm']), marg_across=rng.uniform(*cfg['margin_stria_across_cm']),
        marg_along=rng.uniform(*cfg['margin_stria_along_cm']),
        stria_seed=rng.randrange(1, 1 << 30), streak_seed=rng.randrange(1, 1 << 30), bio_seed=rng.randrange(1, 1 << 30),
        patina_seed=rng.randrange(1, 1 << 30), edge_seed=rng.randrange(1, 1 << 30),
        weathering=rng.uniform(*cfg['weathering']),
        rough_boss=cfg['rough']['boss'] + rng.uniform(-cfg['rough_jitter'], cfg['rough_jitter']),
        rough_margin=cfg['rough']['margin'] + rng.uniform(-cfg['rough_jitter'], cfg['rough_jitter']),
        chips=[], pores=[])
    if rng.random() < cfg['chip_chance']:
        for _ in range(rng.randint(*cfg['chips_per_block'])):
            R = rng.uniform(*cfg['chip_radius_cm'])
            edge = rng.choice(['top', 'bottom', 'left', 'right'])
            if edge in ('top', 'bottom'):
                pu, pv = rng.uniform(R, max(R + 0.1, L - R)), (H if edge == 'top' else 0.0)
            else:
                pu, pv = (L if edge == 'right' else 0.0), rng.uniform(R, max(R + 0.1, H - R))
            block['chips'].append((pu, pv, R, rng.uniform(*cfg['chip_depth_cm'])))
    area = L * H
    # V5: real limestone porosity is power-law (very many tiny, very few large) and PATCHY.
    # V4's rng.uniform radius with an even scatter is what makes a dense pore field read as
    # aerated concrete instead of stone, so both are shaped here.
    lo, hi = cfg['pore_radius_cm']
    shape = cfg.get('pore_size_shape', 2.6)
    patch_cm, patch_cut = cfg.get('pore_patch_cm', 17.0), cfg.get('pore_patch_cut', -0.22)
    for _ in range(int(area * cfg['pore_density_per_cm2'] * rng.uniform(0.5, 1.5))):
        R = lo + (hi - lo) * (rng.random() ** shape)
        m = jw + R + 0.4
        if L - 2 * m > 0 and H - 2 * m > 0:
            pu, pv = rng.uniform(m, L - m), rng.uniform(m, H - m)
            if vnoise(pu / patch_cm, pv / patch_cm, block['patina_seed'] + 71) < patch_cut:
                continue          # leave clean patches, the way weathering actually spares stone
            block['pores'].append((pu, pv, R, R * rng.uniform(0.35, 0.65)))
    return block


def reroll_surface(cfg, courses, surface_rng):
    """A tile VARIANT: the same stones (same x0, L, y0, H, and the same edge_seed, which is the only
    surface-looking draw that moves a JOINT - it wobbles the bed and rising joint lines) with every other
    per-block draw re-rolled from surface_rng: family and tint, value, stroke direction, drafted-margin
    widths, boss projection, dressing, run-off, biology, patina, weathering, roughness, chips and pores.
    The joint mask is therefore identical to the source tile's by construction; generate() writes it out
    so that claim is diffed pixel for pixel rather than trusted."""
    out = []
    for course in courses:
        row = []
        for b in course:
            nb = draw_block_surface(cfg, surface_rng, b['L'], b['H'], b['x0'], b['y0'])
            nb['edge_seed'] = b['edge_seed']
            assert (nb['x0'], nb['L'], nb['y0'], nb['H']) == (b['x0'], b['L'], b['y0'], b['H'])
            row.append(nb)
        out.append(row)
    return out


def layout_courses(cfg, rng):
    """Herodian coursing for one 300 cm tile. Course heights vary inside course_h_cm and sum to TILE_CM
    exactly; each course carries blocks_per_course blocks whose lengths sum to TILE_CM (so the tile wraps);
    course offsets stagger the vertical joints by at least min_joint_stagger_cm from the course below.
    Every block gets its own four drafted-margin widths, boss projection and dressing."""
    heights = partition(rng, TILE_CM, cfg['courses'], *cfg['course_h_cm']) or [TILE_CM / cfg['courses']] * cfg['courses']
    lo_r, hi_r = cfg['length_ratio']
    mlo, mhi = cfg['margin_cm']
    courses = []
    previous_joints = None
    y0 = 0.0
    for _c, H in enumerate(heights):
        want = [(k, w) for k, w in cfg['blocks_per_course'].items() if k * lo_r * H <= TILE_CM <= k * hi_r * H]
        if not want:
            want = [(max(1, int(round(TILE_CM / (2.0 * H)))), 1.0)]
        k = choose(rng, want)
        lengths = partition(rng, TILE_CM, k, lo_r * H, hi_r * H) or [TILE_CM / k] * k
        rng.shuffle(lengths)
        best = None
        for _ in range(120):
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
            block = draw_block_surface(cfg, rng, L, H, x, y0)
            blocks.append(block)
            x += L
        courses.append(blocks)
        y0 += H
    return heights, courses


# ------------------------------------------------------------------------------------- render
def generate(name, cfg, size, log, surface_seed=None):
    t0 = time.time()
    rng = random.Random(cfg['seed'])
    px = TILE_CM / size                      # cm per pixel
    heights, courses = layout_courses(cfg, rng)
    if surface_seed is not None:
        # anti-repeat tile variant: same stones and joints, every surface draw re-rolled (reroll_surface)
        courses = reroll_surface(cfg, courses, random.Random(surface_seed))
    bounds = []
    acc = 0.0
    for H in heights:
        bounds.append(acc)
        acc += H
    # the tile-wide mottle field is surface too, so a variant reseeds it; V5 itself keeps seed * 7 + 1
    noise = OctaveStack(random.Random((cfg['seed'] if surface_seed is None else surface_seed) * 7 + 1), size)
    flat_blocks = [b for c in courses for b in c]
    for i, b in enumerate(flat_blocks):
        b['id'] = i
    if len(flat_blocks) > 255:
        raise RuntimeError('block ids are stored as bytes; %d blocks exceed 255' % len(flat_blocks))
    log('  layout: %d courses (%s cm), %d blocks, lengths %.0f-%.0f cm, margins %.1f-%.1f cm, boss %.2f-%.2f cm proud, %d chips, %d pores' % (
        len(courses), '/'.join('%.0f' % h for h in heights), len(flat_blocks),
        min(b['L'] for b in flat_blocks), max(b['L'] for b in flat_blocks),
        min(min(b['marginCm']) for b in flat_blocks), max(max(b['marginCm']) for b in flat_blocks),
        min(b['boss_proud'] for b in flat_blocks), max(b['boss_proud'] for b in flat_blocks),
        sum(len(b['chips']) for b in flat_blocks), sum(len(b['pores']) for b in flat_blocks)))

    jw = cfg['joint_cm'] / 2.0
    arris = cfg['arris_cm']
    depth = cfg['joint_depth_cm']
    und = cfg['undulation_cm']
    dish = cfg['boss_dish_cm']
    bevel = cfg['boss_edge_cm']
    setback = cfg['setback_cm']
    set_extra = cfg['setback_extra_cm']
    patch = cfg['stria_patch_cm']
    ew, ews = cfg['edge_wobble_cm'], cfg['edge_wobble_scale_cm']
    mwob, mwobs = cfg['margin_wobble_cm'], cfg['margin_wobble_scale_cm']
    grain_h = cfg['grain_cm']

    def course_of(yc):
        c = len(bounds) - 1
        while c > 0 and yc < bounds[c]:
            c -= 1
        return c

    height, face_rel, block_id, stria_rows, region_rows = [], [], [], [], []
    low_rows, mid_rows, fine_rows = [], [], []
    for y in range(size):
        yc = (y + 0.5) * px
        c = course_of(yc)
        H = heights[c]
        v = yc - bounds[c]
        low, mid, fine = noise.bands(y)
        low_rows.append(array('f', low)); mid_rows.append(array('f', mid)); fine_rows.append(array('f', fine))
        h_row = [0.0] * size
        f_row = [0.0] * size
        id_row = [0] * size
        s_row = [0.0] * size
        g_row = [0] * size
        for b in courses[c]:
            x0, L = b['x0'], b['L']
            xa = int(math.ceil(x0 / px - 0.5))
            xb = int(math.ceil((x0 + L) / px - 0.5))
            segs = [(xa, xb, x0)] if xb <= size else [(xa, size, x0), (0, xb - size, x0 - TILE_CM)]
            mw_l, mw_r, mw_b, mw_t = b['mw_l'], b['mw_r'], b['mw_b'], b['mw_t']
            # the stepped batter, authored as a local ledge: the top of the stone leans out over the bed
            # joint and the course above starts flush, which is what the setback looks like in raking light
            reach = mw_t + set_extra
            ledge = setback * smoothstep(max(0.0, min(1.0, (v - (H - reach)) / reach)))
            base_v = b['base'] + b['tilt_v'] * (v - H / 2) + ledge
            tu = b['tilt_u']
            ca, sa = math.cos(b['angle']), math.sin(b['angle'])
            bamp, bacross, balong = b['boss_amp'], b['boss_across'], b['boss_along']
            mamp, macross, malong = b['marg_amp'], b['marg_across'], b['marg_along']
            seed = b['stria_seed']
            bid = b['id']
            eseed = b['edge_seed']
            # hand-cut, not CAD: the bed-joint line wanders along u, the rising joint along v, and each
            # drafted-margin edge wanders independently along the edge it follows
            wob_v = ew * vnoise(v / ews, 3.1, eseed + 31)
            mw_lv = mw_l + mwob * vnoise(v / mwobs, 1.9, eseed + 35)
            mw_rv = mw_r + mwob * vnoise(v / mwobs, 14.2, eseed + 36)
            dv_b, dv_t = v + wob_v, H - v + wob_v
            for xa_, xb_, xoff in segs:
                for x in range(max(0, xa_), min(size, xb_)):
                    u = (x + 0.5) * px - xoff
                    wob_u = ew * vnoise(u / ews, 11.7, eseed + 32)
                    du_l, du_r = u + wob_u, L - u + wob_u
                    dmin = du_l if du_l < du_r else du_r
                    if dv_b < dmin:
                        dmin = dv_b
                    if dv_t < dmin:
                        dmin = dv_t
                    id_row[x] = bid
                    if dmin < jw:
                        h_row[x] = -depth + 0.02 * fine[x]
                        g_row[x] = R_JOINT
                        continue
                    # drafted-margin inset per edge; db > 0 is the boss
                    e_l = du_l - jw - mw_lv
                    e_r = du_r - jw - mw_rv
                    e_b = dv_b - jw - mw_b - mwob * vnoise(u / mwobs, 5.5, eseed + 37)
                    e_t = dv_t - jw - mw_t - mwob * vnoise(u / mwobs, 19.1, eseed + 38)
                    db = e_l if e_l < e_r else e_r
                    if e_b < db:
                        db = e_b
                    if e_t < db:
                        db = e_t
                    plane = base_v + tu * (u - L / 2) + und * low[x]
                    if db <= 0.0:
                        # margin: flat, dressed with fine strokes running ALONG the margin it belongs to
                        horizontal = (dv_b if dv_b < dv_t else dv_t) <= (du_l if du_l < du_r else du_r)
                        if horizontal:
                            s, t = v, u
                        else:
                            s, t = u, v
                        stria = vnoise(s / macross, t / malong, seed + 11) + 0.4 * vnoise(s / (macross * 0.55) + 7.1, t / (malong * 0.45) + 3.3, seed + 12)
                        s_row[x] = stria
                        surf = plane + mamp * stria + 0.30 * grain_h * fine[x]
                        g_row[x] = R_MARGIN
                    else:
                        w_b = smoothstep(db / bevel) if db < bevel else 1.0
                        s = u * ca + v * sa
                        t = -u * sa + v * ca
                        stria = vnoise(s / bacross, t / balong, seed) + 0.45 * vnoise(s / (bacross * 0.55) + 17.3, t / (balong * 0.4) + 5.1, seed + 1)
                        stria *= max(0.05, 0.50 + 0.55 * vnoise(u / patch + 3.7, v / patch + 1.9, seed + 2)) * (1.0 + 0.25 * mid[x])
                        s_row[x] = stria
                        # a barely-there dish so the boss is not a mathematical plane
                        dishing = -dish * smoothstep(min(1.0, db / max(1.0, 0.35 * min(L, H))))
                        surf = plane + w_b * (b['boss_proud'] + bamp * stria + dishing) + grain_h * fine[x]
                        g_row[x] = R_BOSS if db >= bevel else R_BEVEL
                    df = dmin - jw
                    if df < arris:
                        w = smoothstep(df / arris)
                        h_row[x] = -depth * (1.0 - w) + surf * w
                        f_row[x] = w
                        g_row[x] = R_ARRIS
                    else:
                        h_row[x] = surf
                        f_row[x] = 1.0
        height.append(array('f', h_row)); face_rel.append(array('f', f_row)); block_id.append(array('B', id_row))
        stria_rows.append(array('f', s_row)); region_rows.append(array('B', g_row))
    log('  height pass %.1fs' % (time.time() - t0))

    # edge chips (own block only) and sparse pores: stamped bowls with wrap
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

    # ambient occlusion: cavity at two radii (joints/margin step ~ 2 cm, pores/chips ~ 0.6 cm) + joint darkening
    gain, floor_ = cfg['ao_gain'], cfg['ao_floor']
    wide_gain = cfg['ao_wide_gain']
    blur_wide = box_blur_wrap(height, max(3, int(round(cfg['ao_wide_cm'] / px))))
    blur_big = box_blur_wrap(height, max(2, int(round(2.0 / px))))
    blur_small = box_blur_wrap(height, max(1, int(round(0.6 / px))))
    ao_rows = []
    for y in range(size):
        h, bw, bb, bs, f = height[y], blur_wide[y], blur_big[y], blur_small[y], face_rel[y]
        ao_rows.append(array('f', [max(floor_, min(1.0, 1.0
                                                   - wide_gain * gain * max(0.0, bw[x] - h[x])
                                                   - gain * max(0.0, bb[x] - h[x])
                                                   - 0.8 * gain * max(0.0, bs[x] - h[x])
                                                   - 0.10 * (1.0 - f[x]))) for x in range(size)]))
    del blur_wide, blur_big, blur_small
    log('  ao %.1fs' % (time.time() - t0))

    # albedo / roughness / ARM
    rcl = cfg['rough_clamp']
    rough_c = cfg['rough']
    grain = cfg['rough_grain']
    mot_low, mot_mid, mot_fine = cfg['mottle']
    joint_f, joint_grey = cfg['joint_factor'], cfg['joint_grey']
    w_dark, w_band, streak_amp = cfg['weather_dark'], cfg['weather_band'], cfg['streak']
    bio_amount, bio_band, bio_grid, bio_rough = cfg['bio_amount'], cfg['bio_band'], cfg['bio_grid'], cfg['bio_rough']
    bio_r, bio_g, bio_b = cfg['bio_tint']
    margin_light = cfg['margin_light']
    # V5 micro-grain. The approved Jerusalem paving carries its rock read entirely in the albedo
    # (M_JerusalemFloorSlabs_500cm has NO normal map at all); measured |laplacian| 0.137 against the
    # V4 wall's 0.0075. These two terms and the denser pores are the wall's version of that.
    grit_a, grit_as, grit_b, grit_bs = cfg['grit']
    grit_rough = cfg['grit_rough']
    grit_norm = max(1e-6, grit_a + grit_b)
    pore_alb, pore_rim = cfg['pore_albedo'], cfg['pore_rim']
    pat, pats, patf, patfs = cfg['patina'], cfg['patina_scale_cm'], cfg['patina_fine'], cfg['patina_fine_scale_cm']
    albedo_rows, rough_rows, arm_rows = [], [], []
    for y in range(size):
        yc = (y + 0.5) * px
        c = course_of(yc)
        H = heights[c]
        v = yc - bounds[c]
        # world-down is small v: the lower part of every stone darkens (dust, splash, run-off)
        ramp = smoothstep(max(0.0, min(1.0, (w_band * H - v) / (w_band * H))))
        bio_ramp = smoothstep(max(0.0, min(1.0, (bio_band * H - v) / (bio_band * H))))
        low, mid, fine = low_rows[y], mid_rows[y], fine_rows[y]
        f, ids, cm_, pm, ao, st, gg = face_rel[y], block_id[y], chip_mask[y], pore_mask[y], ao_rows[y], stria_rows[y], region_rows[y]
        a_out = bytearray(3 * size)
        r_out = bytearray(3 * size)
        arm_out = bytearray(3 * size)
        for x in range(size):
            b = flat_blocks[ids[x]]
            face = f[x]
            region = gg[x]
            chip, pore = cm_[x], pm[x]
            u = ((x + 0.5) * px - b['x0']) % TILE_CM
            # faint vertical run-off streaks (long along v, narrow along u)
            streak = vnoise(u / 3.0, v / 40.0, b['streak_seed'])
            weather = b['weathering'] * (w_dark * ramp * (0.75 + 0.25 * streak) + streak_amp * streak)
            # patchy biological darkening low on each stone and in the joints
            bio = bio_amount * bio_ramp * max(0.0, vnoise(u / bio_grid, v / bio_grid, b['bio_seed'])) * (1.0 + 0.5 * (1.0 - face))
            # roughness: the boss is the smoothest surface, the drafted margin a touch rougher from the flat chisel
            base_rough = b['rough_margin'] if region == R_MARGIN else b['rough_boss']
            # grain/pitting noise in the 1.5-5 cm band, which is the band that survives the mip the
            # eye actually samples at 4 m (mip 2 = 0.59 cm/texel); the V4 'fine' band was sub-1.2 cm
            # and therefore averaged to nothing before it reached the screen.
            g1 = vnoise(u / grit_as, v / grit_as, b['patina_seed'] + 61)
            g2 = vnoise(u / grit_bs + 8.3, v / grit_bs + 5.9, b['patina_seed'] + 62)
            grit_v = grit_a * g1 * (0.55 + 0.45 * abs(g1)) + grit_b * g2 * (0.55 + 0.45 * abs(g2))
            rough = base_rough + 0.03 * st[x] + 0.04 * ramp * b['weathering'] + bio_rough * (bio / max(1e-6, bio_amount)) + grain * fine[x]
            rough -= grit_rough * grit_v / grit_norm          # pits and hollows read matte
            rough = rough * face + rough_c['joint'] * (1.0 - face)
            rough += (rough_c['chip'] - rough) * 0.7 * chip + (rough_c['pore'] - rough) * 0.8 * pore
            rough = max(rcl[0], min(rcl[1], rough))
            # albedo (sRGB space)
            tr, tg, tb = b['tint']
            # broad patina blotches that belong to THIS stone (block-local, so they never cross a joint)
            patina = pat * vnoise(u / pats, v / pats, b['patina_seed']) + patf * vnoise(u / patfs + 4.4, v / patfs + 2.2, b['patina_seed'] + 3)
            m = (1.0 + mot_low * low[x] + mot_mid * mid[x] + mot_fine * fine[x] + 0.010 * st[x] + patina + grit_v) * (1.0 - weather)
            if region == R_MARGIN or region == R_BEVEL:
                m *= 1.0 + margin_light            # freshly dressed drafted margin reads a shade lighter
            m *= 1.0 + 0.05 * chip - pore_alb * pore + pore_rim * max(0.0, 1.0 - 2.4 * pore) * (1.0 if pore > 0.0 else 0.0)
            r, g, bl = tr * m, tg * m, tb * m
            if bio > 0.0:
                lum = 0.2126 * r + 0.7152 * g + 0.0722 * bl
                r += (lum * bio_r - r) * bio
                g += (lum * bio_g - g) * bio
                bl += (lum * bio_b - bl) * bio
            if face < 1.0:
                # dry joint: a fine dark line, NOT a mortar band - the adjoining stone at joint_factor, pulled toward grey
                lum = 0.2126 * tr + 0.7152 * tg + 0.0722 * tb
                jr, jg, jb = (tr + (lum - tr) * joint_grey) * joint_f, (tg + (lum - tg) * joint_grey) * joint_f, (tb + (lum - tb) * joint_grey) * joint_f
                r = r * face + jr * (1.0 - face)
                g = g * face + jg * (1.0 - face)
                bl = bl * face + jb * (1.0 - face)
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
    boss_mask = [bytes(1 if (g == R_BOSS) else 0 for g in row) for row in region_rows]
    margin_mask = [bytes(1 if (g == R_MARGIN) else 0 for g in row) for row in region_rows]
    boss_edge_mask = [bytes(1 if (g == R_BEVEL) else 0 for g in row) for row in region_rows]

    maps = {'Albedo': albedo_rows, 'Normal': normal_rows, 'ARM': arm_rows, 'Roughness': rough_rows, 'AO': ao_png, 'Height': height_png}
    lengths = [b['L'] for b in flat_blocks]
    margins = [m for b in flat_blocks for m in b['marginCm']]
    total = float(size * size)
    counts = Counter()
    for row in region_rows:
        counts.update(row)
    schedule = {
        'tileCm': TILE_CM,
        'courseHeightsCm': [round(h, 2) for h in heights], 'courses': len(courses), 'blocks': len(flat_blocks),
        'blocksPerCourse': [len(c) for c in courses],
        'blockLengthCmMinMax': [round(min(lengths), 2), round(max(lengths), 2)], 'blockLengthCmMean': round(sum(lengths) / len(lengths), 2),
        'blockSizeCmPerCourse': [[[round(b['L'], 1), round(b['H'], 1)] for b in course] for course in courses],
        'lengthToHeightMinMax': [round(min(b['L'] / b['H'] for b in flat_blocks), 2), round(max(b['L'] / b['H'] for b in flat_blocks), 2)],
        'draftedMarginCmMinMax': [round(min(margins), 2), round(max(margins), 2)], 'draftedMarginCmMean': round(sum(margins) / len(margins), 2),
        'marginOrderLeftRightBottomTop': [b['marginCm'] for b in flat_blocks],
        'bossProudCmMinMax': [round(min(b['boss_proud'] for b in flat_blocks), 2), round(max(b['boss_proud'] for b in flat_blocks), 2)],
        'bossEdgeBevelCm': bevel, 'courseSetbackCm': setback, 'courseSetbackReachCm': round(sum(b['mw_t'] for b in flat_blocks) / len(flat_blocks) + set_extra, 1),
        'familyCounts': dict(Counter(b['family'] for b in flat_blocks)),
        'chips': sum(len(b['chips']) for b in flat_blocks), 'pores': sum(len(b['pores']) for b in flat_blocks),
        'jointCm': cfg['joint_cm'], 'jointDepthCm': cfg['joint_depth_cm'], 'arrisCm': cfg['arris_cm'],
        'heightRangeCm': [round(hmin, 3), round(hmax, 3)],
        'pixelFraction': {'joint': round(counts[R_JOINT] / total, 4), 'arris': round(counts[R_ARRIS] / total, 4),
                          'margin': round(counts[R_MARGIN] / total, 4), 'bossBevel': round(counts[R_BEVEL] / total, 4),
                          'boss': round(counts[R_BOSS] / total, 4)},
        'facePixelFraction': round(sum(sum(r) for r in face_mask) / total, 4)}
    extras = stone_key_and_masks(flat_blocks, block_id, region_rows, size, px)
    return maps, {'face': face_mask, 'boss': boss_mask, 'margin': margin_mask, 'bossEdge': boss_edge_mask}, schedule, time.time() - t0, extras


def stone_key_and_masks(flat_blocks, block_id, region_rows, size, px):
    """Layout-only images for the anti-repeat variants (identical for every variant of one layout).

    StoneKey (sampled NEAREST, no mips, uncompressed): lets the shader pick a variant per STONE rather than
    per 300 cm cell. A per-cell pick would put a tone step through every stone that straddles the cell edge,
    because per-stone tone is exactly what the variants change.
      R = (d + 1) * 127.5 with d = u_unwrapped - anchor, in tile units. u_unwrapped is the pixel's u, plus 1
          for the part of a stone that wraps round to the start of the tile; anchor = floor(stone centre) + 0.5.
          The shader's floor(u_world - d) is then the SAME integer on every pixel of one stone, including
          across the tile edge, and it is robust because frac(anchor) is exactly 0.5.
      G = stone index * 17 (index <= 15), so the pick can differ between stones of one cell.
      B = 0.
    JointMask: 255 on joint pixels, 128 on arris pixels, 0 elsewhere - the geometry that must be identical.
    Regions: region code * 60 (joint 0, arris 60, margin 120, bevel 180, boss 240) - reported, not required equal."""
    for b in flat_blocks:
        centre = (b['x0'] + b['L'] / 2.0) / TILE_CM
        b['anchor'] = math.floor(centre) + 0.5
    if len(flat_blocks) > 15:
        raise RuntimeError('StoneKey stores the stone index * 17 in 8 bits; %d stones exceed 15' % len(flat_blocks))
    key_rows, joint_rows, region_png = [], [], []
    dmax = 0.0
    for y in range(size):
        ids, reg = block_id[y], region_rows[y]
        k = bytearray(3 * size)
        j = bytearray(3 * size)
        g = bytearray(3 * size)
        for x in range(size):
            b = flat_blocks[ids[x]]
            ut = (x + 0.5) * px
            if b['x0'] + b['L'] > TILE_CM and ut < b['x0']:
                ut += TILE_CM                      # the wrapped part of a stone that crosses u = 0
            d = ut / TILE_CM - b['anchor']
            if abs(d) > dmax:
                dmax = abs(d)
            k[3 * x] = int(round((d + 1.0) * 127.5))
            k[3 * x + 1] = b['id'] * 17
            r = reg[x]
            jm = 255 if r == R_JOINT else (128 if r == R_ARRIS else 0)
            j[3 * x] = j[3 * x + 1] = j[3 * x + 2] = jm
            g[3 * x] = g[3 * x + 1] = g[3 * x + 2] = r * 60
        key_rows.append(k)
        joint_rows.append(j)
        region_png.append(g)
    if dmax > 1.0:
        raise RuntimeError('StoneKey offset %.4f exceeds the encodable +-1 tile' % dmax)
    return {'StoneKey': key_rows, 'JointMask': joint_rows, 'Regions': region_png,
            'stones': [{'id': b['id'], 'x0Cm': round(b['x0'], 3), 'LCm': round(b['L'], 3), 'y0Cm': round(b['y0'], 3),
                        'HCm': round(b['H'], 3), 'anchor': b['anchor'], 'family': b['family'],
                        'tint': [round(t, 4) for t in b['tint']], 'weathering': round(b['weathering'], 4),
                        'marginCm': b['marginCm'], 'bossProudCm': round(b['boss_proud'], 3)} for b in flat_blocks],
            'maxAbsOffsetTiles': round(dmax, 4)}


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
    """xy deviation = sqrt(nx^2 + ny^2) of the decoded bytes (1/1000 bins) plus per-channel |n| p95."""
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
    if not n:
        return {'pixels': 0}
    mean = sum(k * c for k, c in mag.items()) / n / 1000.0
    return {'xyDeviation': {'mean': round(mean, 4), 'p50': _pct(mag, 50), 'p95': _pct(mag, 95), 'p99': _pct(mag, 99), 'max': _pct(mag, 100)},
            'absX_p95': _pct(absx, 95), 'absY_p95': _pct(absy, 95), 'pixels': n}


def measure(maps, masks=None):
    alb = {ch: hist_stats(channel_hist(maps['Albedo'], i)) for i, ch in enumerate('RGB')}
    out = {'albedoSRGB': alb, 'albedoStdPerChannelMean': round(sum(alb[c]['std'] for c in 'RGB') / 3.0, 4),
           'albedoChroma': {'GoverR_mean': round(alb['G']['mean'] / alb['R']['mean'], 3), 'BoverR_mean': round(alb['B']['mean'] / alb['R']['mean'], 3)},
           'normal': normal_stats(maps['Normal']), 'roughness': hist_stats(channel_hist(maps['ARM'], 1)),
           'ambientOcclusion': hist_stats(channel_hist(maps['ARM'], 0))}
    if masks:
        out['normalFaceOnly'] = normal_stats(maps['Normal'], masks['face'])
        out['normalBossOnly'] = normal_stats(maps['Normal'], masks['boss'])
        out['normalMarginOnly'] = normal_stats(maps['Normal'], masks['margin'])
        # the drafted margin's defining feature: the step from the recessed margin up onto the boss.
        # It is reported on its own because it is neither of the two flat planes it separates, and
        # averaging it into either one hides exactly the thing that makes the wall read.
        out['normalBossEdgeOnly'] = normal_stats(maps['Normal'], masks['bossEdge'])
        joint_mask = [bytes(1 - k for k in row) for row in masks['face']]
        out['normalJointAndArrisOnly'] = normal_stats(maps['Normal'], joint_mask)
    out['photoDelta'] = {'meanR': round(alb['R']['mean'] - PHOTO_REFERENCE['meanSRGB'][0], 4),
                         'meanG': round(alb['G']['mean'] - PHOTO_REFERENCE['meanSRGB'][1], 4),
                         'meanB': round(alb['B']['mean'] - PHOTO_REFERENCE['meanSRGB'][2], 4),
                         'GoverR': round(out['albedoChroma']['GoverR_mean'] - PHOTO_REFERENCE['chromaGoverR_p5_p50_p95'][1], 4),
                         'BoverR': round(out['albedoChroma']['BoverR_mean'] - PHOTO_REFERENCE['chromaBoverR_p5_p50_p95'][1], 4)}
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
    """Lambert render. world_orientation flips rows so world up is image up (texture v = world Z); the light
    then comes from the upper left of the WORLD view. 30 % AO ambient + 70 % direct, normalised so a flat,
    unoccluded face shows its albedo unchanged (the render judges relief and colour, not an exposure choice).
    Identical to create_limestone_textures_v2.py so V3 and V4 previews are directly comparable."""
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
    ap.add_argument('--surface-seed', type=int, default=None,
                    help='anti-repeat variant: keep the layout (and every joint), re-roll every per-stone surface draw and the mottle from this seed')
    ap.add_argument('--tag', default='', help='file-name tag: T_HerodianV5<tag>_<Variant>_<Map>.png (default: none, the V5 names)')
    ap.add_argument('--extras', action='store_true', help='also write StoneKey, JointMask and Regions PNGs (layout-only)')
    args = ap.parse_args(argv)
    out = args.out
    receipts = list(out.glob('herodian-v5-import-*.json'))
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
    manifest = {'status': 'OFFLINE_GENERATED_NATIVE_IMPORT_PENDING', 'iteration': ITERATION,
                'instruction': 'Shmuel, verbatim: "I want the temple stones used for wall wherever you are using stones to be the large style stones used for the 2nd temple outer wall." = Herodian ashlar, the masonry of the Second Temple outer retaining wall (the Kotel). This overrides the V2/V3 decision to omit drafted margins.',
                'generator': 'Scripts/create_herodian_ashlar_v5.py',
                'generatorSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'startedUtc': started,
                'tileCm': TILE_CM, 'size': args.size, 'pxPerCm': round(args.size / TILE_CM, 4),
                'sources': 'SourceAssets/material-review/HerodianAshlarV5/sources.md (measured vs authored is marked there)',
                'conventions': {'uv': 'u = world X|Y / TilingCm, v = world Z / TilingCm; image row 0 = v 0, image down = world up on vertical faces',
                                'normal': 'normalize(-dh/du, -dh/dv, 1), u = column, v = row (DirectX / UE default; flip_green_channel False)',
                                'arm': 'R ambient occlusion, G roughness, B metallic (0)', 'heightsCm': 'physical centimetres, slopes unscaled',
                                'litPreview': 'rows flipped to world orientation (world up = image up), light from the upper left of that view, albedo-preserving',
                                'courseSetback': 'authored as a local ledge at the top of each stone, because an accumulating per-course setback cannot wrap in a tiling texture; see sources.md'},
                'importSettings': {'Albedo': {'compression': 'TC_Default', 'srgb': True}, 'Normal': {'compression': 'TC_Normalmap', 'srgb': False, 'flipGreenChannel': False},
                                   'ARM': {'compression': 'TC_Masks', 'srgb': False}, 'notImported': ['Roughness', 'AO', 'Height']},
                'diagnosisBaseline_sandstone_blocks_08': DIAGNOSIS_BASELINE, 'photoReference': PHOTO_REFERENCE,
                'previousIterationV3': V3_COMPARISON, 'variants': {}}
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
        manifest['variants'] = previous.get('variants', {})
        if 'measuredBaselineNormal' in previous:
            manifest['measuredBaselineNormal'] = previous['measuredBaselineNormal']
        manifest['previousRuns'] = previous.get('previousRuns', []) + [{'iteration': previous.get('iteration'), 'startedUtc': previous.get('startedUtc'),
                                                                        'finishedUtc': previous.get('finishedUtc'), 'generatorSha256': previous.get('generatorSha256')}]
    if args.baseline:
        t = time.time()
        if BASELINE_NORMAL.exists():
            w, h, rows = decode_png_rgb8(BASELINE_NORMAL)
            manifest['measuredBaselineNormal'] = {'file': rel(BASELINE_NORMAL), 'size': [w, h], **normal_stats(rows),
                                                  'note': 'same statistic code as the V2/V3/V4 maps; compare with diagnosis 0.09', 'seconds': round(time.time() - t, 1)}
            log('baseline normal %s: %s (%.1fs)' % (BASELINE_NORMAL.name, manifest['measuredBaselineNormal']['xyDeviation'], time.time() - t))
        else:
            manifest['measuredBaselineNormal'] = {'missing': str(BASELINE_NORMAL)}
    for name in (args.variant or sorted(VARIANTS)):
        cfg = VARIANTS[name]
        log('generating %s at %d' % (name, args.size))
        maps, masks, schedule, seconds, extras = generate(name, cfg, args.size, log, args.surface_seed)
        record = {'iteration': ITERATION, 'seed': cfg['seed'], 'surfaceSeed': args.surface_seed, 'tag': args.tag,
                  'parameters': cfg, 'schedule': schedule,
                  'generationSeconds': round(seconds, 1), 'files': {}, 'previews': {}}
        suffix = '' if args.size == DEFAULT_SIZE else '_%d' % args.size
        for kind, rows in maps.items():
            path = out / ('T_HerodianV5%s_%s_%s%s.png' % (args.tag, name, kind, suffix))
            digest = write_png_rgb(path, args.size, args.size, rows)
            record['files'][kind] = {'path': rel(path), 'sha256': digest, 'bytes': path.stat().st_size, 'imported': kind in ('Albedo', 'Normal', 'ARM')}
        if args.extras:
            for kind in ('StoneKey', 'JointMask', 'Regions'):
                path = out / ('T_HerodianV5%s_%s_%s%s.png' % (args.tag, name, kind, suffix))
                record['files'][kind] = {'path': rel(path), 'sha256': write_png_rgb(path, args.size, args.size, extras[kind]),
                                         'imported': kind == 'StoneKey'}
            record['stones'] = extras['stones']
            record['stoneKeyMaxAbsOffsetTiles'] = extras['maxAbsOffsetTiles']
        log('  wrote maps')
        record['statistics'] = measure(maps, masks)
        s = record['statistics']
        log('  stats: albedo std %.4f  mean %.3f/%.3f/%.3f  G/R %.3f B/R %.3f  R p5-p95 %.3f-%.3f  normal p50/p95 %.3f/%.3f  face %.3f/%.3f  boss %.3f/%.3f  rough p5/p50/p95 %.3f/%.3f/%.3f' % (
            s['albedoStdPerChannelMean'], s['albedoSRGB']['R']['mean'], s['albedoSRGB']['G']['mean'], s['albedoSRGB']['B']['mean'],
            s['albedoChroma']['GoverR_mean'], s['albedoChroma']['BoverR_mean'],
            s['albedoSRGB']['R']['p5'], s['albedoSRGB']['R']['p95'], s['normal']['xyDeviation']['p50'], s['normal']['xyDeviation']['p95'],
            s['normalFaceOnly']['xyDeviation']['p50'], s['normalFaceOnly']['xyDeviation']['p95'],
            s['normalBossOnly']['xyDeviation']['p50'], s['normalBossOnly']['xyDeviation']['p95'],
            s['roughness']['p5'], s['roughness']['p50'], s['roughness']['p95'])
            + '  bossEdge p50/p95 %.3f/%.3f  margin p50/p95 %.3f/%.3f' % (
                s['normalBossEdgeOnly']['xyDeviation']['p50'], s['normalBossEdgeOnly']['xyDeviation']['p95'],
                s['normalMarginOnly']['xyDeviation']['p50'], s['normalMarginOnly']['xyDeviation']['p95']))
        pv = {k: downsample2(v) if args.size > 1024 else v for k, v in maps.items()}
        psize = args.size // 2 if args.size > 1024 else args.size
        for kind, rows in pv.items():
            path = out / 'previews' / ('T_HerodianV5%s_%s_%s_%d.png' % (args.tag, name, kind, psize))
            record['previews'][kind] = {'path': rel(path), 'sha256': write_png_rgb(path, psize, psize, rows)}
        lit = out / 'previews' / ('Lit%s_%s_%d.png' % (args.tag, name, psize))
        record['previews']['Lit'] = {'path': rel(lit), 'sha256': write_png_rgb(lit, psize, psize, lit_preview(pv['Albedo'], pv['Normal'], pv['ARM'])),
                                     'orientation': 'world (rows flipped)', 'albedoPreserving': True}
        log('  previews done, elapsed %.1fs' % (time.time() - t_start))
        manifest['variants'][name + args.tag] = record
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    manifest['finishedUtc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    log('manifest ' + str(manifest_path))
    return manifest


if __name__ == '__main__':
    main()
