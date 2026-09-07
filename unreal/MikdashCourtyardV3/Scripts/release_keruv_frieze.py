"""Guarded keruv/palm frieze: image -> height/normal maps -> gold relief panels tiled on the inner walls.

What it does, in order (every number comes from Scripts/release_keruv_frieze.spec.json):

  1. Offline image stage (plain Python, PIL optional): decode the finished relief render
     SourceAssets/visual-reference-handoff/gold-palm-cherub-relief.png (frozen hash), luma,
     large-radius high-pass to remove the baked lighting, median + small blur, background
     level from the histogram mode of the hammered ground, clamp/normalise -> APPROXIMATE
     height; 16-bit height PNG and Sobel tangent-space normal PNG at 2048 x 2048 in
     SourceAssets/relief-images/derived/ (the only folder written there). The horizontal
     repeat seam (rightmost vs leftmost column) is measured and recorded.
  2. Engine stage: import both PNGs as textures (normal TC_Normalmap, height TC_Grayscale,
     both sRGB off), build M_KeruvFrieze (gold constant, metallic 1, roughness lerped by
     height, normal map) and M_KeruvFrieze_Displaced (same without the normal map), plus the
     optional UNASSIGNED M_KeruvFrieze_Tessellated (MakeMaterialAttributes.Displacement,
     enable_tessellation) when the 5.8 Python API exposes it. Create SM_KeruvFriezePanelV1
     (250 x 250 x 6 cm box, 12 triangles) and SM_KeruvFriezePanelDisplacedV1 (front face a
     256 x 256 grid displaced by height * 3 cm, Nanite) from explicit buffers; read back the
     +Y face UVs and the winding (signed volume > 0, matches the offline value).
  3. Placement in /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough: refuse if any
     RELEASE_Frieze_* exists; checkpoint; remove the 32 RELEASE_Reliefs_* palm actors
     (recorded for restore); read the veneer actors listed in the PalmReliefV1 receipt and
     tile every enabled wall with 250 cm panels, 1.5 cm in front of the veneer face, rows
     from the floor top to the veneer top (8 x 8 per Heikhal long wall, 4 x 8 per Kodesh
     wall and rear). Any panel whose AABB intersects an existing actor (doors, paroches,
     vessels, walls; terrain tiles excluded, hollow unions decomposed) is skipped and recorded.
  4. Save, reopen, numeric readback of every placed actor and of the palms' absence, receipt
     SourceAssets/sanctuary-detail/KeruvFriezeV1/native-import-<stamp>.json.

Commandlet invocation (serial; never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_keruv_frieze.py"
      -EnablePlugins=GeometryScripting -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-KeruvFrieze-01.log"

Optional switches (read from the engine command line):
  -FriezeImagesOnly            offline image stage only (derived PNGs + derived-manifest.json).
  -FriezeAssetsOnly            image stage + textures + materials + meshes; no map change.
  -FriezePlaceOnly             assets already saved in the namespace: load, re-verify, place.
  -FriezeImage=<stem|path>     another PNG (stem looked up in SourceAssets/relief-images).
  -FriezeKeepPalms             do not remove the palm actors (their slots then fail clearance).
  -FriezeAllowUnverifiedWinding  place even if the winding/UV readback is unavailable.

Offline (no engine):
  python Scripts/release_keruv_frieze.py                       -> offline consistency check
  python Scripts/release_keruv_frieze.py --derive [--image P] [--derived-dir D] [--size N]
                                                               -> image stage only

Reuses release_place_assets.py (AABB maths, union decomposition, Placement snapshot/spawn)
and release_import_reliefs.py (winding_report, ReliefRow.clearance_candidates/blockers_for).
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import re
import shutil
import struct
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_keruv_frieze.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
AXIS = {'x': 0, 'y': 1, 'z': 2}


# --------------------------------------------------------------------------
# Spec and shared helpers (no unreal import)
# --------------------------------------------------------------------------

def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def _load_module(relative, name, required):
    path = ROOT / relative
    module_spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    for attr in required:
        if not hasattr(module, attr):
            raise RuntimeError('%s lacks helper %s' % (relative, attr))
    return module


def load_placement_helper(spec):
    return _load_module(spec['placementHelper'], 'release_place_assets',
                        ('sha256_of', 'disk_path', 'box_from_min_max', 'box_error', 'rotate_box_yaw',
                         'boxes_overlap_volume', 'verify_union_decomposition', 'Placement', '_actor_bounds', '_pose_close'))


def load_reliefs_module(spec):
    return _load_module(spec['reliefsScript'], 'release_import_reliefs', ('winding_report', 'ReliefRow', 'fresh_receipt_path'))


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def latest_reliefs_receipt(spec):
    folder = ROOT / spec['reliefsReceiptFolder']
    prefix = spec['reliefsReceiptStatusPrefix']
    rows = []
    for path in sorted(folder.glob('native-import-*.json')):
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if str(data.get('status', '')).startswith(prefix):
            rows.append((path, data))
    if not rows:
        raise RuntimeError('No PalmReliefV1 receipt with status %s* in %s' % (prefix, folder))
    return rows[-1]


# --------------------------------------------------------------------------
# PNG decode / encode (pure Python; PIL used for decoding when importable)
# --------------------------------------------------------------------------

def _decode_png_pure(data):
    """8-bit RGB/RGBA non-interlaced PNG -> (width, height, channels, rows). Filters 0-4."""
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise RuntimeError('Not a PNG')
    pos, width, height, depth, color, interlace, idat = 8, None, None, None, None, None, []
    while pos + 8 <= len(data):
        length, kind = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b'IHDR':
            width, height, depth, color, _, _, interlace = struct.unpack('>IIBBBBB', body)
        elif kind == b'IDAT':
            idat.append(body)
        elif kind == b'IEND':
            break
        pos += 12 + length
    if depth != 8 or color not in (2, 6) or interlace != 0:
        raise RuntimeError('Unsupported PNG layout: depth %s colour type %s interlace %s (need 8-bit RGB/RGBA, non-interlaced)' % (depth, color, interlace))
    channels = 3 if color == 2 else 4
    stride = width * channels
    raw = zlib.decompress(b''.join(idat))
    if len(raw) != height * (stride + 1):
        raise RuntimeError('PNG payload length %d differs from %d' % (len(raw), height * (stride + 1)))
    prev = bytearray(stride)
    rows = []
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        line = bytearray(raw[offset + 1:offset + 1 + stride])
        offset += 1 + stride
        if filter_type == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 255
        elif filter_type == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif filter_type == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif filter_type == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 255
        elif filter_type != 0:
            raise RuntimeError('Unknown PNG filter %d' % filter_type)
        rows.append(bytes(line))
        prev = line
    return width, height, channels, rows


def decode_png(path):
    """Returns dict(width, height, channels, rows, decoder). rows are bytes of 8-bit samples."""
    data = Path(path).read_bytes()
    try:
        from PIL import Image  # noqa: F401
        pil = True
    except ImportError:
        pil = False
    if pil:
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(data))
        if image.mode not in ('RGB', 'RGBA'):
            image = image.convert('RGB')
        width, height = image.size
        channels = len(image.mode)
        flat = image.tobytes()
        stride = width * channels
        rows = [flat[i * stride:(i + 1) * stride] for i in range(height)]
        decoder = 'PIL ' + getattr(Image, '__version__', '')
    else:
        width, height, channels, rows = _decode_png_pure(data)
        decoder = 'pure_python_zlib'
    return {'width': width, 'height': height, 'channels': channels, 'rows': rows, 'decoder': decoder, 'sha256': hashlib.sha256(data).hexdigest()}


def _png_chunk(kind, body):
    return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)


def encode_png(path, width, height, rows, color_type, bit_depth=8, filter_type=0):
    """rows: list of bytes, each already packed (big-endian for 16-bit). Filters 0/1/2 supported."""
    channels = {0: 1, 2: 3, 6: 4}[color_type]
    bpp = channels * bit_depth // 8
    stride = width * bpp
    out = bytearray()
    prev = bytes(stride)
    for row in rows:
        if len(row) != stride:
            raise RuntimeError('Row length %d differs from stride %d' % (len(row), stride))
        if filter_type == 0:
            out.append(0)
            out += row
        elif filter_type == 1:
            out.append(1)
            out += bytes(((row[i] - (row[i - bpp] if i >= bpp else 0)) & 255) for i in range(stride))
        elif filter_type == 2:
            out.append(2)
            out += bytes(((row[i] - prev[i]) & 255) for i in range(stride))
        else:
            raise RuntimeError('encode_png supports filters 0, 1, 2')
        prev = row
    header = struct.pack('>IIBBBBB', width, height, bit_depth, color_type, 0, 0, 0)
    data = b'\x89PNG\r\n\x1a\n' + _png_chunk(b'IHDR', header) + _png_chunk(b'IDAT', zlib.compress(bytes(out), 6)) + _png_chunk(b'IEND', b'')
    Path(path).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------
# Image maths on lists of rows of floats
# --------------------------------------------------------------------------

def luma_rows(decoded, weights):
    wr, wg, wb = weights
    channels = decoded['channels']
    out = []
    for row in decoded['rows']:
        r, g, b = row[0::channels], row[1::channels], row[2::channels]
        out.append([(wr * x + wg * y + wb * z) / 255.0 for x, y, z in zip(r, g, b)])
    return out


def _blur_rows_1d(img, radius):
    width = len(img[0])
    lo = [max(0, x - radius) for x in range(width)]
    hi = [min(width, x + radius + 1) for x in range(width)]
    inv = [1.0 / (h - l) for l, h in zip(lo, hi)]
    out = []
    for row in img:
        prefix = [0.0] + list(itertools.accumulate(row))
        out.append([(prefix[h] - prefix[l]) * k for l, h, k in zip(lo, hi, inv)])
    return out


def box_blur(img, radius, passes=1):
    if radius <= 0:
        return [list(r) for r in img]
    current = img
    for _ in range(passes):
        horizontal = _blur_rows_1d(current, radius)
        transposed = [list(c) for c in zip(*horizontal)]
        vertical = _blur_rows_1d(transposed, radius)
        current = [list(c) for c in zip(*vertical)]
    return current


def _pad_row(row):
    return [row[0]] + list(row) + [row[-1]]


def median3(img):
    height = len(img)
    padded = [_pad_row(r) for r in img]
    out = []
    for y in range(height):
        u = padded[max(0, y - 1)]
        m = padded[y]
        d = padded[min(height - 1, y + 1)]
        out.append([sorted((a0, a1, a2, b0, b1, b2, c0, c1, c2))[4]
                    for a0, a1, a2, b0, b1, b2, c0, c1, c2 in zip(u, u[1:], u[2:], m, m[1:], m[2:], d, d[1:], d[2:])])
    return out


def resample_bilinear(img, width2, height2):
    height, width = len(img), len(img[0])
    def axis(n_src, n_dst):
        i0, i1, frac = [], [], []
        for i in range(n_dst):
            s = (i + 0.5) * n_src / n_dst - 0.5
            a = int(math.floor(s))
            f = s - a
            a0 = min(max(a, 0), n_src - 1)
            a1 = min(max(a + 1, 0), n_src - 1)
            i0.append(a0)
            i1.append(a1)
            frac.append(f if 0 <= a < n_src - 1 else (0.0 if a < 0 else 0.0))
        return i0, i1, frac
    x0, x1, fx = axis(width, width2)
    gx = [1.0 - f for f in fx]
    y0, y1, fy = axis(height, height2)
    cache = {}
    def hrow(y):
        if y not in cache:
            r = img[y]
            cache[y] = [r[a] * g + r[b] * f for a, b, g, f in zip(x0, x1, gx, fx)]
        return cache[y]
    out = []
    for y in range(height2):
        a, b, f = y0[y], y1[y], fy[y]
        ra = hrow(a)
        if f <= 0.0 or a == b:
            out.append(list(ra))
        else:
            rb = hrow(b)
            g = 1.0 - f
            out.append([p * g + q * f for p, q in zip(ra, rb)])
        for key in [k for k in cache if k < a]:
            del cache[key]
    return out


def flat_sorted(img):
    values = [v for row in img for v in row]
    values.sort()
    return values


def percentile_sorted(values, pct):
    if not values:
        raise RuntimeError('percentile of empty list')
    k = (len(values) - 1) * pct / 100.0
    lo = int(math.floor(k))
    hi = min(lo + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def background_level(sorted_values, bins, sigma_multiplier):
    """Histogram mode + k * robust sigma of the values below the mode."""
    lo, hi = sorted_values[0], sorted_values[-1]
    if hi <= lo:
        raise RuntimeError('Constant image; no relief to derive')
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in sorted_values:
        counts[min(bins - 1, int((v - lo) / width))] += 1
    mode_bin = max(range(bins), key=lambda i: counts[i])
    mode = lo + (mode_bin + 0.5) * width
    below = [mode - v for v in sorted_values if v <= mode]
    below.sort()
    mad = percentile_sorted(below, 50.0) if below else 0.0
    sigma = 1.4826 * mad
    return {'mode': mode, 'madBelowMode': mad, 'robustSigma': sigma, 'level': mode + sigma_multiplier * sigma,
            'modeBinFraction': counts[mode_bin] / float(len(sorted_values)), 'bins': bins, 'sigmaMultiplier': sigma_multiplier}


def seam_report(luma):
    height, width = len(luma), len(luma[0])
    def col(i):
        return [row[i] for row in luma]
    def mad(a, b):
        return sum(abs(x - y) for x, y in zip(a, b)) / len(a)
    def corr(a, b):
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
        return num / den if den > 0 else None
    left, right = col(0), col(width - 1)
    seam = mad(right, left)
    adjacent = 0.5 * (mad(col(0), col(1)) + mad(col(width - 2), col(width - 1)))
    interior = sum(mad(col(x), col(x + 1)) for x in range(0, width - 1, max(1, width // 64))) / len(range(0, width - 1, max(1, width // 64)))
    top, bottom = list(luma[0]), list(luma[height - 1])
    vertical_seam = mad(bottom, top)
    vertical_adjacent = 0.5 * (mad(luma[0], luma[1]) + mad(luma[height - 2], luma[height - 1]))
    return {'horizontal': {'rightVsLeftMeanAbsDiff': seam, 'edgeAdjacentColumnMeanAbsDiff': adjacent,
                           'interiorAdjacentColumnMeanAbsDiff': interior,
                           'ratioSeamOverAdjacent': seam / adjacent if adjacent > 0 else None,
                           'ratioSeamOverInterior': seam / interior if interior > 0 else None,
                           'correlationRightLeft': corr(right, left)},
            'vertical': {'bottomVsTopMeanAbsDiff': vertical_seam, 'edgeAdjacentRowMeanAbsDiff': vertical_adjacent,
                         'ratioSeamOverAdjacent': vertical_seam / vertical_adjacent if vertical_adjacent > 0 else None,
                         'correlationBottomTop': corr(bottom, top)},
            'unit': 'luma 0..1', 'rule': 'ratio near 1 = the repeat joint is as smooth as neighbouring columns; >> 1 = visible seam'}


def corner_patch_stats(img, fraction):
    height, width = len(img), len(img[0])
    ph, pw = max(1, int(height * fraction)), max(1, int(width * fraction))
    out = {}
    for name, (y0, x0) in {'topLeft': (0, 0), 'topRight': (0, width - pw), 'bottomLeft': (height - ph, 0), 'bottomRight': (height - ph, width - pw)}.items():
        values = [img[y][x] for y in range(y0, y0 + ph) for x in range(x0, x0 + pw)]
        mean = sum(values) / len(values)
        out[name] = {'mean': mean, 'stdev': math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))}
    return out


def height_rows_16(img):
    width = len(img[0])
    fmt = '>%dH' % width
    return [struct.pack(fmt, *[int(round(min(max(v, 0.0), 1.0) * 65535)) for v in row]) for row in img]


def normal_rows_rgb8(height_img, slope_factor, flip_green):
    """Sobel of a 0..1 height field -> DirectX-style tangent-space normal rows (RGB8 bytes)."""
    height = len(height_img)
    padded = [_pad_row(r) for r in height_img]
    green_sign = -1.0 if flip_green else 1.0
    k = slope_factor / 8.0
    out = []
    for y in range(height):
        u = padded[max(0, y - 1)]
        m = padded[y]
        d = padded[min(height - 1, y + 1)]
        s = [a + 2.0 * b + c for a, b, c in zip(u, m, d)]
        gx = [(s2 - s0) * k for s0, s2 in zip(s, s[2:])]
        dd = [a + 2.0 * b + c for a, b, c in zip(d, d[1:], d[2:])]
        uu = [a + 2.0 * b + c for a, b, c in zip(u, u[1:], u[2:])]
        gy = [(p - q) * k for p, q in zip(dd, uu)]          # > 0 when height grows downward (+V)
        row = bytearray()
        for sx, sy in zip(gx, gy):
            nx, nv = -sx, -sy                                # normal tilts against the slope
            inv = 1.0 / math.sqrt(nx * nx + nv * nv + 1.0)
            nx *= inv
            nv *= inv * green_sign
            nz = inv
            row += bytes((int(round((nx * 0.5 + 0.5) * 255)), int(round((nv * 0.5 + 0.5) * 255)), int(round((nz * 0.5 + 0.5) * 255))))
        out.append(bytes(row))
    return out


def sample_bilinear(img, u, v):
    """img rows indexed [row][col]; u, v in 0..1 with v = 0 at the top row."""
    height, width = len(img), len(img[0])
    x = min(max(u * width - 0.5, 0.0), width - 1.0)
    y = min(max(v * height - 0.5, 0.0), height - 1.0)
    x0, y0 = int(math.floor(x)), int(math.floor(y))
    x1, y1 = min(x0 + 1, width - 1), min(y0 + 1, height - 1)
    fx, fy = x - x0, y - y0
    top = img[y0][x0] * (1 - fx) + img[y0][x1] * fx
    bottom = img[y1][x0] * (1 - fx) + img[y1][x1] * fx
    return top * (1 - fy) + bottom * fy


# --------------------------------------------------------------------------
# Image stage
# --------------------------------------------------------------------------

def resolve_image(spec, image=None):
    """Default frozen image, or a stem/path passed by -FriezeImage / --image."""
    cfg = spec['image']
    if not image:
        path = ROOT / cfg['defaultSource']
        return path, True
    candidate = Path(image)
    if candidate.suffix.lower() == '.png' and candidate.exists():
        return candidate.resolve(), False
    if (ROOT / image).exists():
        return (ROOT / image).resolve(), False
    folder = ROOT / cfg['alternativeFolder']
    for name in (image, image + '.png'):
        if (folder / name).exists():
            return (folder / name).resolve(), False
    raise RuntimeError('Image not found: %s (looked in %s)' % (image, folder))


def derive_relief(spec, source_path, derived_dir, size=None, is_default=True):
    """Height + normal derivation. Returns the record (also carries the float height rows)."""
    cfg = spec['image']
    panel = spec['panel']
    started = time.monotonic()
    timings = {}
    derived_dir = Path(derived_dir)
    derived_dir.mkdir(parents=True, exist_ok=True)
    source_sha = sha256_of(source_path)
    if is_default and source_sha != cfg['defaultSourceSha256']:
        raise RuntimeError('Frozen relief image hash differs: ' + str(source_path))

    decoded = decode_png(source_path)
    width, height = decoded['width'], decoded['height']
    timings['decodeS'] = time.monotonic() - started
    record = {'source': str(source_path), 'sourceSha256': source_sha, 'stem': Path(source_path).stem, 'width': width, 'height': height,
              'channels': decoded['channels'], 'decoder': decoded['decoder'], 'isDefaultSource': is_default,
              'aspectWidthOverHeight': width / float(height)}
    luma = luma_rows(decoded, cfg['lumaWeights'])
    del decoded
    record['seam'] = seam_report(luma)
    record['cornerPatchesLuma'] = corner_patch_stats(luma, cfg['cornerPatchFraction'])
    t = time.monotonic()

    radius = max(1, int(round(cfg['lowFrequencyRadiusFraction'] * width)))
    low = box_blur(luma, radius, cfg['lowFrequencyBlurPasses'])
    high = [[a - b for a, b in zip(ra, rb)] for ra, rb in zip(luma, low)]
    del low
    timings['highPassS'] = time.monotonic() - t
    t = time.monotonic()
    smooth = high
    for _ in range(int(cfg['medianPasses'])):
        smooth = median3(smooth)
    if cfg['smoothRadiusPx'] > 0:
        smooth = box_blur(smooth, int(cfg['smoothRadiusPx']), 1)
    timings['smoothS'] = time.monotonic() - t
    t = time.monotonic()
    values = flat_sorted(smooth)
    background = background_level(values, int(cfg['backgroundHistogramBins']), float(cfg['backgroundSigmaMultiplier']))
    top = percentile_sorted(values, float(cfg['topPercentile']))
    if top <= background['level']:
        raise RuntimeError('Top percentile %.5f not above background %.5f' % (top, background['level']))
    scale = 1.0 / (top - background['level'])
    gamma = float(cfg['heightGamma'])
    level = background['level']
    def norm(v):
        h = (v - level) * scale
        h = 0.0 if h < 0.0 else (1.0 if h > 1.0 else h)
        return h ** gamma if gamma != 1.0 else h
    detail = [[norm(v) for v in row] for row in smooth]
    # Mass layer: a plain high-pass keeps only lit edges, so body, wing and trunk surfaces would stay at
    # ground level. Relief edges (highlights AND shadows) cluster densely on the figures and are sparse on
    # the hammered ground, so blurred |high-pass| above the ground noise floor marks the raised masses.
    magnitude = [[abs(v) for v in row] for row in smooth]
    del smooth
    mag_sorted = flat_sorted(magnitude)
    noise_floor = percentile_sorted(mag_sorted, float(cfg['massNoiseFloorPercentile']))
    activity = [[(v - noise_floor) if v > noise_floor else 0.0 for v in row] for row in magnitude]
    del magnitude, mag_sorted
    mass_radius = max(1, int(round(cfg['massBlurRadiusFraction'] * width)))
    mass = box_blur(activity, mass_radius, int(cfg['massBlurPasses']))
    del activity
    mass_sorted = flat_sorted(mass)
    mass_top = percentile_sorted(mass_sorted, float(cfg['massTopPercentile']))
    del mass_sorted
    if mass_top <= 0:
        raise RuntimeError('Mass layer is empty')
    mass_gamma = float(cfg['massGamma'])
    w_mass, w_detail = float(cfg['massWeight']), float(cfg['detailWeight'])
    base_cut = float(cfg['massBaseCut'])
    def combine(m, d):
        m = (m / mass_top - base_cut) / (1.0 - base_cut)
        m = 0.0 if m < 0.0 else ((1.0 if m > 1.0 else m) ** mass_gamma)
        h = w_mass * m + w_detail * d
        return 0.0 if h < 0.0 else (1.0 if h > 1.0 else h)
    height_src = [[combine(m, d) for m, d in zip(mrow, drow)] for mrow, drow in zip(mass, detail)]
    mass_stats = {'noiseFloor': noise_floor, 'noiseFloorPercentile': cfg['massNoiseFloorPercentile'], 'blurRadiusPx': mass_radius,
                  'blurPasses': cfg['massBlurPasses'], 'topPercentile': cfg['massTopPercentile'], 'topValue': mass_top, 'baseCut': base_cut, 'gamma': mass_gamma,
                  'massWeight': w_mass, 'detailWeight': w_detail}
    del mass, detail, values
    covered = sum(1 for row in height_src for v in row if v > 0.0) / float(width * height)
    mean_height = sum(sum(row) for row in height_src) / float(width * height)
    record['cornerPatchesHeight'] = corner_patch_stats(height_src, cfg['cornerPatchFraction'])
    timings['normaliseS'] = time.monotonic() - t
    t = time.monotonic()

    out_w, out_h = size or cfg['derivedSize']
    height_out = resample_bilinear(height_src, out_w, out_h) if (out_w, out_h) != (width, height) else height_src
    timings['resampleS'] = time.monotonic() - t
    t = time.monotonic()
    height_path = derived_dir / (record['stem'] + cfg['outputs']['heightSuffix'])
    height_sha = encode_png(height_path, out_w, out_h, height_rows_16(height_out), cfg['outputs']['heightPngColorType'], bit_depth=cfg['outputs']['heightBitDepth'])
    timings['writeHeightS'] = time.monotonic() - t
    t = time.monotonic()
    slope_factor = panel['displacementCm'] * out_w / panel['sizeCm'][0] * float(cfg['normalStrengthMultiplier'])
    normal_path = derived_dir / (record['stem'] + cfg['outputs']['normalSuffix'])
    normal_sha = encode_png(normal_path, out_w, out_h, normal_rows_rgb8(height_out, slope_factor, bool(cfg['flipGreen'])), cfg['outputs']['normalPngColorType'])
    timings['normalS'] = time.monotonic() - t
    timings['totalS'] = time.monotonic() - started

    record.update({
        'parameters': {'lumaWeights': cfg['lumaWeights'], 'lowFrequencyRadiusPx': radius, 'lowFrequencyBlurPasses': cfg['lowFrequencyBlurPasses'],
                       'medianPasses': cfg['medianPasses'], 'smoothRadiusPx': cfg['smoothRadiusPx'], 'topPercentile': cfg['topPercentile'],
                       'topValue': top, 'heightGamma': gamma, 'background': background, 'massLayer': mass_stats, 'derivedSize': [out_w, out_h], 'resample': cfg['resample'],
                       'normalSlopeFactorPerTexel': slope_factor, 'normalStrengthMultiplier': cfg['normalStrengthMultiplier'],
                       'normalGreenConvention': cfg['normalGreenConvention'], 'flipGreen': cfg['flipGreen'], 'displacementCm': panel['displacementCm']},
        'heightStatistics': {'fractionAboveBackground': covered, 'meanHeight': mean_height},
        'heightIsApproximate': cfg['heightIsApproximate'],
        'outputs': {'height': {'path': str(height_path), 'sha256': height_sha, 'bitDepth': cfg['outputs']['heightBitDepth'], 'size': [out_w, out_h]},
                    'normal': {'path': str(normal_path), 'sha256': normal_sha, 'bitDepth': 8, 'size': [out_w, out_h]}},
        'timingsSeconds': timings,
        '_heightRows': height_out,
    })
    return record


def image_stage(spec, image=None, derived_dir=None, size=None):
    """Runs derive_relief and writes derived-manifest.json. Returns the record (with height rows)."""
    cfg = spec['image']
    source, is_default = resolve_image(spec, image)
    derived = Path(derived_dir) if derived_dir else ROOT / cfg['derivedFolder']
    record = derive_relief(spec, source, derived, size=size, is_default=is_default)
    manifest_path = derived / cfg['derivedManifest']
    manifest = {'images': []}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
        except ValueError:
            manifest = {'images': []}
    manifest['images'] = [m for m in manifest.get('images', []) if m.get('stem') != record['stem']]
    manifest['images'].append({k: v for k, v in record.items() if not k.startswith('_')})
    manifest['updated'] = datetime.now(timezone.utc).isoformat()
    manifest['specSha256'] = sha256_of(SPEC_PATH)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    record['manifest'] = str(manifest_path)
    return record


# --------------------------------------------------------------------------
# Panel geometry (pure Python buffers; UE winding by construction)
# --------------------------------------------------------------------------

def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def _normalised(v):
    length = math.sqrt(_dot(v, v))
    return [x / length for x in v]


class Buffers:
    def __init__(self):
        self.positions = []
        self.normals = []
        self.uv0 = []
        self.triangles = []

    def add_triangle(self, a, b, c, outward):
        """Append (a, b, c) with UE's face normal cross(C-A, B-A) along outward."""
        p = self.positions
        if _dot(_cross(_sub(p[c], p[a]), _sub(p[b], p[a])), outward) < 0:
            b, c = c, b
        self.triangles.append((a, b, c))

    def add_quad(self, corners, normal, uvs):
        """corners in perimeter order; normal outward; uvs per corner."""
        base = len(self.positions)
        self.positions.extend([list(c) for c in corners])
        self.normals.extend([list(normal) for _ in corners])
        self.uv0.extend([list(uv) for uv in uvs])
        self.add_triangle(base, base + 1, base + 2, normal)
        self.add_triangle(base, base + 2, base + 3, normal)

    def summary(self):
        return {'vertices': len(self.positions), 'triangles': len(self.triangles)}


def signed_volume_ue(positions, triangles):
    """Divergence-theorem volume with UE's face normal convention cross(C-A, B-A)."""
    flux = 0.0
    for a, b, c in triangles:
        pa, pb, pc = positions[a], positions[b], positions[c]
        n = _cross(_sub(pc, pa), _sub(pb, pa))
        flux += _dot(n, [(pa[i] + pb[i] + pc[i]) / 3.0 for i in range(3)])
    return flux / 6.0


def bounds_of(positions):
    return {'min': [min(p[i] for p in positions) for i in range(3)], 'max': [max(p[i] for p in positions) for i in range(3)]}


def _box_sides(buffers, hw, thickness, hh, front_border=None):
    """Back, left, right, bottom, top faces of the panel box (front handled by the caller)."""
    t = thickness
    # back (-Y) planar UV so the image would read correctly through the wall (irrelevant, non-degenerate)
    buffers.add_quad([(-hw, 0, 0), (-hw, 0, hh), (hw, 0, hh), (hw, 0, 0)], (0, -1, 0),
                     [(1, 1), (1, 0), (0, 0), (0, 1)])
    if front_border is None:
        buffers.add_quad([(-hw, 0, 0), (-hw, t, 0), (-hw, t, hh), (-hw, 0, hh)], (-1, 0, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
        buffers.add_quad([(hw, 0, 0), (hw, 0, hh), (hw, t, hh), (hw, t, 0)], (1, 0, 0), [(1, 1), (1, 0), (0, 0), (0, 1)])
        buffers.add_quad([(-hw, 0, 0), (hw, 0, 0), (hw, t, 0), (-hw, t, 0)], (0, 0, -1), [(0, 1), (1, 1), (1, 0), (0, 0)])
        buffers.add_quad([(-hw, 0, hh), (-hw, t, hh), (hw, t, hh), (hw, 0, hh)], (0, 0, 1), [(0, 1), (0, 0), (1, 0), (1, 1)])
        return
    # Strips along the (flat, h = 0) front border so the displaced grid stays watertight against the sides.
    xs, zs = front_border
    n = len(xs) - 1
    for i in range(n):
        x0, x1 = xs[i], xs[i + 1]
        u0, u1 = i / float(n), (i + 1) / float(n)
        buffers.add_quad([(x0, 0, 0), (x1, 0, 0), (x1, t, 0), (x0, t, 0)], (0, 0, -1), [(u0, 1), (u1, 1), (u1, 0), (u0, 0)])
        buffers.add_quad([(x0, 0, hh), (x0, t, hh), (x1, t, hh), (x1, 0, hh)], (0, 0, 1), [(u0, 1), (u0, 0), (u1, 0), (u1, 1)])
    for j in range(n):
        z0, z1 = zs[j], zs[j + 1]
        v0, v1 = 1 - j / float(n), 1 - (j + 1) / float(n)
        buffers.add_quad([(-hw, 0, z0), (-hw, t, z0), (-hw, t, z1), (-hw, 0, z1)], (-1, 0, 0), [(0, v0), (1, v0), (1, v1), (0, v1)])
        buffers.add_quad([(hw, 0, z0), (hw, 0, z1), (hw, t, z1), (hw, t, z0)], (1, 0, 0), [(1, v0), (1, v1), (0, v1), (0, v0)])


def flat_panel_buffers(spec):
    panel = spec['panel']
    hw, hh, t = panel['sizeCm'][0] / 2.0, panel['sizeCm'][1], panel['thicknessCm']
    buffers = Buffers()
    # Front (+Y): U grows with +X, V grows downward (UE UV origin top-left) -> upright, not mirrored.
    buffers.add_quad([(-hw, t, 0), (hw, t, 0), (hw, t, hh), (-hw, t, hh)], (0, 1, 0), [(0, 1), (1, 1), (1, 0), (0, 0)])
    _box_sides(buffers, hw, t, hh)
    return buffers


def displaced_panel_buffers(spec, height_rows):
    """Front face = (grid+1)^2 vertices displaced along +Y by height * displacementCm, analytic normals."""
    panel = spec['panel']
    hw, hh, t = panel['sizeCm'][0] / 2.0, panel['sizeCm'][1], panel['thicknessCm']
    depth = float(panel['displacementCm'])
    n = int(panel['displacedGrid'])
    feather = int(panel['displacedBorderFeatherCells'])
    cell_x, cell_z = 2.0 * hw / n, hh / n
    xs = [-hw + 2.0 * hw * i / n for i in range(n + 1)]
    zs = [hh * j / n for j in range(n + 1)]
    # h[j][i]: j along +Z (bottom row j = 0 is the image bottom, v = 1), i along +X (u = i / n)
    h = []
    for j in range(n + 1):
        v = 1.0 - j / float(n)
        row = []
        for i in range(n + 1):
            border = min(i, n - i, j, n - j)
            weight = 0.0 if border == 0 else min(1.0, border / float(feather)) if feather > 0 else 1.0
            row.append(sample_bilinear(height_rows, i / float(n), v) * weight)
        h.append(row)
    buffers = Buffers()
    index = {}
    for j in range(n + 1):
        for i in range(n + 1):
            dhdx = ((h[j][min(i + 1, n)] - h[j][max(i - 1, 0)]) * depth) / ((min(i + 1, n) - max(i - 1, 0)) * cell_x)
            dhdz = ((h[min(j + 1, n)][i] - h[max(j - 1, 0)][i]) * depth) / ((min(j + 1, n) - max(j - 1, 0)) * cell_z)
            index[(i, j)] = len(buffers.positions)
            buffers.positions.append([xs[i], t + h[j][i] * depth, zs[j]])
            buffers.normals.append(_normalised([-dhdx, 1.0, -dhdz]))
            buffers.uv0.append([i / float(n), 1.0 - j / float(n)])
    for j in range(n):
        for i in range(n):
            a, b, c, d = index[(i, j)], index[(i + 1, j)], index[(i + 1, j + 1)], index[(i, j + 1)]
            buffers.add_triangle(a, b, c, (0, 1, 0))
            buffers.add_triangle(a, c, d, (0, 1, 0))
    _box_sides(buffers, hw, t, hh, front_border=(xs, zs))
    mean_h = sum(sum(r) for r in h) / float((n + 1) * (n + 1))
    return buffers, {'grid': n, 'borderFeatherCells': feather, 'meanDisplacementCm': mean_h * depth, 'maxDisplacementCm': max(max(r) for r in h) * depth}


def check_buffers(buffers, expected_bounds, budget=None):
    volume = signed_volume_ue(buffers.positions, buffers.triangles)
    disagreements = 0
    bounds = bounds_of(buffers.positions)
    if volume <= 0:
        raise RuntimeError('Panel buffers have negative signed volume %.3f' % volume)
    if budget is not None and len(buffers.triangles) > budget:
        raise RuntimeError('Panel has %d triangles, over the budget %d' % (len(buffers.triangles), budget))
    if expected_bounds is not None:
        error = max(abs(bounds[k][i] - expected_bounds[k][i]) for k in ('min', 'max') for i in range(3))
        if error > 1e-6:
            raise RuntimeError('Panel bounds %r differ from %r' % (bounds, expected_bounds))
    degenerate = [uv for a, b, c in buffers.triangles for uv in [(buffers.uv0[a], buffers.uv0[b], buffers.uv0[c])]
                  if abs((uv[1][0] - uv[0][0]) * (uv[2][1] - uv[0][1]) - (uv[2][0] - uv[0][0]) * (uv[1][1] - uv[0][1])) < 1e-12]
    if degenerate:
        raise RuntimeError('%d triangles have degenerate UVs' % len(degenerate))
    return {'signedVolumeUEcm3': volume, 'faceNormalVsCrossDisagreements': disagreements, 'localBoundsCm': bounds, **buffers.summary()}


# --------------------------------------------------------------------------
# Wall layout (pure) shared by offline check and placement
# --------------------------------------------------------------------------

def yaw_frame(yaw_degrees):
    """(local +X, local +Y) in world XY after yaw."""
    yaw = math.radians(yaw_degrees)
    return ([math.cos(yaw), math.sin(yaw)], [-math.sin(yaw), math.cos(yaw)])


def plan_wall(spec, wall, veneer_bounds, floor_top, local_box):
    """Panels for one wall from the live veneer bounds and floor top. Returns (wall report, panel plans)."""
    frieze = spec['frieze']
    module = float(frieze['moduleCm'])
    n_axis, a_axis = AXIS[wall['normalAxis']], AXIS[wall['alongAxis']]
    sign = int(wall['sign'])
    face = veneer_bounds['max'][n_axis] if sign < 0 else veneer_bounds['min'][n_axis]
    back_plane = face - sign * frieze['standoffCm']
    standoff = abs(back_plane - face)
    lo, hi = frieze['standoffWindowCm']
    room_dir = [0.0, 0.0]
    room_dir[n_axis] = -float(sign)
    local_x, local_y = yaw_frame(wall['yawDegrees'])
    report = {'wall': wall['name'], 'veneerLabel': wall.get('veneerLabel'), 'normalAxis': wall['normalAxis'], 'sign': sign, 'yawDegrees': wall['yawDegrees'],
              'veneerWorldBoundsCm': veneer_bounds, 'veneerRoomFace': face, 'panelBackPlane': back_plane, 'standoffCm': standoff,
              'roomDirectionWorldXY': room_dir, 'localPlusYWorldXY': local_y, 'localPlusXWorldXY': local_x, 'floorTopZ': floor_top, 'panels': []}
    if not lo <= standoff <= hi or (back_plane - face) * room_dir[n_axis] <= 0:
        report['conflict'] = 'standoff %.3f cm outside [%s, %s] or not toward the room; wall skipped' % (standoff, lo, hi)
        return report, []
    if local_y[0] * room_dir[0] + local_y[1] * room_dir[1] < 0.999:
        report['conflict'] = 'yaw %.1f does not point local +Y into the room; wall skipped' % wall['yawDegrees']
        return report, []
    # Viewer facing the wall (forward = room_dir reversed) has right = up x forward (UE left-handed frame).
    forward = [-room_dir[0], -room_dir[1], 0.0]
    right = _cross([0.0, 0.0, 1.0], forward)
    if local_x[0] * right[0] + local_x[1] * right[1] < 0.999:
        report['conflict'] = 'local +X is not the viewer\'s right; the image would be mirrored; wall skipped'
        return report, []
    a_min, a_max = wall['alongRangeCm']
    v_min, v_max = veneer_bounds['min'][a_axis], veneer_bounds['max'][a_axis]
    if a_min < v_min - 0.2 or a_max > v_max + 0.2:
        report['conflict'] = 'spec along range %r leaves the veneer extent [%s, %s]; wall skipped' % (wall['alongRangeCm'], v_min, v_max)
        return report, []
    cols = int(math.floor((a_max - a_min) / module + 1e-9))
    margin = ((a_max - a_min) - cols * module) / 2.0
    rows = min(int(frieze['maxRows']), int(math.floor((veneer_bounds['max'][2] - floor_top) / module + 1e-9)))
    report.update(columns=cols, rows=rows, alongMarginCm=margin, veneerTopZ=veneer_bounds['max'][2])
    plans = []
    for row in range(rows):
        for col in range(cols):
            location = [0.0, 0.0, floor_top + row * module]
            location[a_axis] = a_min + margin + module * (col + 0.5)
            location[n_axis] = back_plane
            rotation = [0.0, float(wall['yawDegrees']), 0.0]
            plans.append({'wall': wall['name'], 'row': row, 'column': col, 'location': location, 'rotation': rotation,
                          'plannedWorldBoundsCm': _rotate_box_yaw(local_box, location, rotation[1])})
    return report, plans


def _rotate_box_yaw(local, location, yaw_degrees):
    yaw = math.radians(yaw_degrees)
    cos_yaw, sin_yaw = math.cos(yaw), math.sin(yaw)
    corners = []
    for x in (local['min'][0], local['max'][0]):
        for y in (local['min'][1], local['max'][1]):
            for z in (local['min'][2], local['max'][2]):
                corners.append((location[0] + x * cos_yaw - y * sin_yaw, location[1] + x * sin_yaw + y * cos_yaw, location[2] + z))
    return {'min': [min(c[i] for c in corners) for i in range(3)], 'max': [max(c[i] for c in corners) for i in range(3)]}


def _overlap(a, b):
    for i in range(3):
        if min(a['max'][i], b['max'][i]) - max(a['min'][i], b['min'][i]) <= 1e-6:
            return False
    return True


def offline_check(spec=None, namespace_expected=None):
    """Consistency checks that need no engine. Raises on the first failure."""
    spec = spec or load_spec()
    helper = load_placement_helper(spec)
    reliefs = load_reliefs_module(spec)
    report = {}
    image_path = ROOT / spec['image']['defaultSource']
    if not image_path.exists():
        raise RuntimeError('Default relief image missing: ' + str(image_path))
    report['defaultImage'] = {'path': str(image_path), 'sha256': sha256_of(image_path), 'frozenHashMatches': sha256_of(image_path) == spec['image']['defaultSourceSha256']}
    if not report['defaultImage']['frozenHashMatches']:
        raise RuntimeError('Frozen relief image hash differs')
    prompt = ROOT / spec['image']['promptFile']
    report['promptFile'] = {'path': str(prompt), 'exists': prompt.exists(), 'sha256': sha256_of(prompt) if prompt.exists() else None}

    receipt_path, receipt = latest_reliefs_receipt(spec)
    veneers = {v['label']: v['worldBoundsCm'] for v in receipt['veneers']['all']}
    palms = [p['label'] for p in receipt['placed']]
    report['reliefsReceipt'] = {'path': str(receipt_path), 'status': receipt['status'], 'veneerLabels': sorted(veneers), 'palmActorCount': len(palms)}
    if len(palms) != receipt['placedActorCount'] or not palms:
        raise RuntimeError('Reliefs receipt placed list inconsistent')
    if any(not label.startswith(spec['palms']['labelPrefix']) for label in palms):
        raise RuntimeError('Reliefs receipt has non-palm labels')

    flat = flat_panel_buffers(spec)
    report['flatPanel'] = check_buffers(flat, spec['panel']['flatLocalBoundsCm'])
    if report['flatPanel']['triangles'] != spec['panel']['flatTriangles']:
        raise RuntimeError('Flat panel triangle count %d' % report['flatPanel']['triangles'])
    expected_volume = spec['panel']['sizeCm'][0] * spec['panel']['sizeCm'][1] * spec['panel']['thicknessCm']
    if abs(report['flatPanel']['signedVolumeUEcm3'] - expected_volume) > 1e-6:
        raise RuntimeError('Flat panel signed volume %.3f differs from %.3f' % (report['flatPanel']['signedVolumeUEcm3'], expected_volume))
    n = spec['panel']['displacedGrid']
    report['displacedPanelTriangleEstimate'] = 2 * n * n + 8 * n + 2
    if report['displacedPanelTriangleEstimate'] > spec['panel']['displacedTriangleBudget']:
        raise RuntimeError('Displaced grid %d exceeds the triangle budget' % n)

    local_box = {'min': spec['panel']['flatLocalBoundsCm']['min'], 'max': [spec['panel']['flatLocalBoundsCm']['max'][0], spec['panel']['displacedLocalBoundsMaxYCm'], spec['panel']['flatLocalBoundsCm']['max'][2]]}
    walls = []
    total = 0
    for wall in spec['frieze']['walls']:
        floor_top = spec['frieze']['floors'][wall['floor']]['topZ']
        bounds = veneers.get(wall.get('veneerLabel')) if wall.get('veneerLabel') else None
        if bounds is None and wall.get('veneerSearchBoundsCm'):
            matches = [b for b in veneers.values() if helper.box_error(b, wall['veneerSearchBoundsCm']) <= spec['frieze']['veneerBoundsToleranceCm']]
            bounds = matches[0] if len(matches) == 1 else None
        if bounds is None:
            walls.append({'wall': wall['name'], 'enabled': wall['enabled'], 'veneer': 'absent_in_receipt', 'planned': 0})
            continue
        wall_report, plans = plan_wall(spec, wall, bounds, floor_top, local_box)
        walls.append({'wall': wall['name'], 'enabled': wall['enabled'], 'veneer': 'present', 'columns': wall_report.get('columns'), 'rows': wall_report.get('rows'),
                      'conflict': wall_report.get('conflict'), 'planned': len(plans) if wall['enabled'] else 0})
        if wall['enabled'] and wall_report.get('conflict'):
            raise RuntimeError('%s: %s' % (wall['name'], wall_report['conflict']))
        if wall['enabled']:
            total += len(plans)
    report['walls'] = walls
    report['plannedPanelsFromReceiptGeometry'] = total
    report['plannedTrianglesIfDisplaced'] = total * report['displacedPanelTriangleEstimate']

    namespace_dir = ROOT / 'Content' / spec['panel']['namespace'][len('/Game/'):]
    report['namespaceFolderExistsOnDisk'] = namespace_dir.exists()
    if namespace_expected is False and namespace_dir.exists():
        raise RuntimeError('Target namespace folder already exists on disk: ' + str(namespace_dir))
    if namespace_expected is True and not namespace_dir.exists():
        raise RuntimeError('Place-only needs the saved namespace on disk: ' + str(namespace_dir))
    gold = helper.disk_path(spec['material']['goldSource'])
    report['goldSourceOnDisk'] = gold.exists()
    derived = ROOT / spec['image']['derivedFolder']
    report['derivedOnDisk'] = {k: (derived / (image_path.stem + spec['image']['outputs'][k + 'Suffix'])).exists() for k in ('height', 'normal')}
    report['status'] = 'offline_spec_consistent'
    return report


# --------------------------------------------------------------------------
# Engine side: textures, materials, meshes
# --------------------------------------------------------------------------

def _xyz(v):
    return [float(v.x), float(v.y), float(v.z)]


def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def _enum(ue, enum_name, *candidates):
    enum = getattr(ue, enum_name)
    for name in candidates:
        if hasattr(enum, name):
            return getattr(enum, name), name
    raise RuntimeError('%s has none of %s' % (enum_name, candidates))


def import_texture(ue, spec, kind, png_path, stem, receipt):
    cfg = spec['textures']
    tex_spec = cfg[kind]
    name = cfg['namePrefix'] + re.sub(r'[^A-Za-z0-9_]', '_', stem) + tex_spec['suffix']
    task = ue.AssetImportTask()
    for key, value in dict(filename=str(png_path), destination_path=cfg['folder'], destination_name=name, automated=True,
                           replace_existing=False, save=False).items():
        task.set_editor_property(key, value)
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    objects = list(task.get_objects())
    if len(objects) != 1 or not isinstance(objects[0], ue.Texture2D):
        raise RuntimeError('Texture import of %s produced %s' % (png_path, [type(o).__name__ for o in objects]))
    tex = objects[0]
    compression, compression_name = _enum(ue, 'TextureCompressionSettings', tex_spec['compression'], tex_spec.get('compressionFallback', tex_spec['compression']))
    tex.set_editor_property('compression_settings', compression)
    tex.set_editor_property('srgb', bool(tex_spec['srgb']))
    if kind == 'normal':
        tex.set_editor_property('flip_green_channel', bool(tex_spec['flipGreenChannel']))
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if not assets.save_loaded_asset(tex, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + name)
    size = None
    for getter in ('blueprint_get_size_x', 'get_size_x'):
        if hasattr(tex, getter):
            try:
                size = [int(getattr(tex, getter)()), int(getattr(tex, getter.replace('_x', '_y'))())]
            except Exception:
                size = None
            break
    info = {'asset': _asset_path(tex), 'sourcePng': str(png_path), 'sourceSha256': sha256_of(png_path), 'compression': compression_name,
            'srgb': bool(tex.get_editor_property('srgb')), 'size': size,
            'uassetSha256': sha256_of(ROOT / 'Content' / (_asset_path(tex)[len('/Game/'):] + '.uasset'))}
    if kind == 'normal':
        info['flipGreenChannel'] = bool(tex.get_editor_property('flip_green_channel'))
    receipt['textures'][kind] = info
    return tex


def read_gold(ue, spec, receipt):
    cfg = spec['material']
    ml = ue.MaterialEditingLibrary
    result = {'source': cfg['goldSource'], 'read': False, 'linear': list(cfg['goldFallbackLinear']), 'note': cfg['goldFallbackNote']}
    try:
        gold = ue.load_asset(cfg['goldSource'])
        if isinstance(gold, ue.Material):
            node = ml.get_material_property_input_node(gold, ue.MaterialProperty.MP_BASE_COLOR)
            if isinstance(node, ue.MaterialExpressionConstant3Vector):
                colour = node.get_editor_property('constant')
                result.update(read=True, linear=[float(colour.r), float(colour.g), float(colour.b)], nodeClass=node.get_class().get_name())
                rough = ml.get_material_property_input_node(gold, ue.MaterialProperty.MP_ROUGHNESS)
                if isinstance(rough, ue.MaterialExpressionConstant):
                    result['sourceRoughness'] = float(rough.get_editor_property('r'))
            else:
                result['note'] = 'BaseColor input of the gold source is %s, not a Constant3Vector; fallback used' % (node.get_class().get_name() if node else None)
        else:
            result['note'] = 'gold source did not load as a Material; fallback used'
    except Exception as error:
        result['note'] = 'gold source unreadable (%r); fallback used' % (error,)
    receipt['gold'] = result
    return result['linear']


def build_material(ue, spec, variant, gold, height_tex, normal_tex, receipt):
    """variant: 'flat' | 'displaced' | 'tessellated'. Returns the Material or None (tessellated only)."""
    cfg = spec['material']
    ml = ue.MaterialEditingLibrary
    name = cfg['names'][variant]
    path = cfg['folder'] + '/' + name
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tools = ue.AssetToolsHelpers.get_asset_tools()
    record = {'asset': path, 'variant': variant, 'nodes': [], 'connections': [], 'status': 'started'}
    receipt['materials'][variant] = record
    material = tools.create_asset(name, cfg['folder'], ue.Material, ue.MaterialFactoryNew())
    if not isinstance(material, ue.Material):
        raise RuntimeError('Material factory failed for ' + path)

    def node(cls, x, y, **props):
        expression = ml.create_material_expression(material, cls, x, y)
        if expression is None:
            raise RuntimeError('create_material_expression failed for %s' % cls.__name__)
        for key, value in props.items():
            expression.set_editor_property(key, value)
        record['nodes'].append({'class': cls.__name__, 'position': [x, y], 'properties': {k: (str(v) if not isinstance(v, (int, float, bool)) else v) for k, v in props.items()}})
        return expression

    def input_name(expression, wanted):
        names = [str(n) for n in ml.get_material_expression_input_names(expression)]
        for candidate in names:
            if candidate.lower() == wanted.lower():
                return candidate
        raise RuntimeError('%s has no input %r (inputs %s)' % (expression.get_class().get_name(), wanted, names))

    def wire(source, output, target, wanted):
        pin = input_name(target, wanted)
        if not ml.connect_material_expressions(source, output, target, pin):
            raise RuntimeError('Connection %s[%r] -> %s[%r] failed; outputs=%s' % (source.get_class().get_name(), output, target.get_class().get_name(), pin,
                                                                                  [str(n) for n in ml.get_material_expression_output_names(source)]))
        record['connections'].append('%s.%s -> %s.%s' % (source.get_class().get_name(), output or 'RGB', target.get_class().get_name(), pin))

    def to_property(source, output, prop_name):
        prop = getattr(ue.MaterialProperty, prop_name)
        if not ml.connect_material_property(source, output, prop):
            raise RuntimeError('connect_material_property %s -> %s failed' % (source.get_class().get_name(), prop_name))
        record['connections'].append('%s.%s -> %s' % (source.get_class().get_name(), output or 'RGB', prop_name))

    colour = node(ue.MaterialExpressionConstant3Vector, -700, -300, constant=ue.LinearColor(gold[0], gold[1], gold[2], 1.0))
    metallic = node(ue.MaterialExpressionConstant, -700, -100, r=float(cfg['metallic']))
    grayscale, sampler_name = _enum(ue, 'MaterialSamplerType', spec['textures']['height']['samplerType'], spec['textures']['height']['samplerTypeFallback'])
    height_sample = node(ue.MaterialExpressionTextureSample, -1000, 100, texture=height_tex, sampler_type=grayscale)
    rough = node(ue.MaterialExpressionLinearInterpolate, -700, 100, const_a=float(cfg['roughness']['atHeight0']), const_b=float(cfg['roughness']['atHeight1']))
    wire(height_sample, 'R', rough, 'Alpha')
    normal_sample = None
    if variant in ('flat', 'tessellated'):
        normal_sampler, _ = _enum(ue, 'MaterialSamplerType', spec['textures']['normal']['samplerType'])
        normal_sample = node(ue.MaterialExpressionTextureSample, -700, 350, texture=normal_tex, sampler_type=normal_sampler)
    record['heightSamplerType'] = sampler_name

    if variant == 'tessellated':
        # MP_Displacement is Hidden in 5.8 Python; reach the pin through MakeMaterialAttributes.
        material.set_editor_property('use_material_attributes', True)
        material.set_editor_property('enable_tessellation', True)
        scaling = material.get_editor_property('displacement_scaling')
        scaling.set_editor_property('magnitude', float(spec['panel']['displacementCm']))
        scaling.set_editor_property('center', 0.0)
        material.set_editor_property('displacement_scaling', scaling)
        attributes = node(ue.MaterialExpressionMakeMaterialAttributes, -300, 0)
        wire(colour, '', attributes, 'BaseColor')
        wire(metallic, '', attributes, 'Metallic')
        wire(rough, '', attributes, 'Roughness')
        wire(normal_sample, '', attributes, 'Normal')
        wire(height_sample, 'R', attributes, 'Displacement')
        to_property(attributes, '', 'MP_MATERIAL_ATTRIBUTES')
        record['displacementScaling'] = {'magnitude': float(spec['panel']['displacementCm']), 'center': 0.0}
    else:
        to_property(colour, '', 'MP_BASE_COLOR')
        to_property(metallic, '', 'MP_METALLIC')
        to_property(rough, '', 'MP_ROUGHNESS')
        if normal_sample is not None:
            to_property(normal_sample, '', 'MP_NORMAL')
        if ml.get_material_property_input_node(material, ue.MaterialProperty.MP_WORLD_POSITION_OFFSET) is not None:
            raise RuntimeError('WorldPositionOffset unexpectedly connected')
    ml.recompile_material(material)
    if not assets.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + path)
    record['inputsWired'] = {}
    for prop_name in ('MP_BASE_COLOR', 'MP_METALLIC', 'MP_ROUGHNESS', 'MP_NORMAL', 'MP_WORLD_POSITION_OFFSET', 'MP_MATERIAL_ATTRIBUTES'):
        if hasattr(ue.MaterialProperty, prop_name):
            wired = ml.get_material_property_input_node(material, getattr(ue.MaterialProperty, prop_name))
            record['inputsWired'][prop_name] = wired.get_class().get_name() if wired else None
    record['pixelDepthOffsetExposed'] = hasattr(ue.MaterialProperty, 'MP_PIXEL_DEPTH_OFFSET')
    record['displacementPropertyExposed'] = hasattr(ue.MaterialProperty, 'MP_DISPLACEMENT')
    record['uassetSha256'] = sha256_of(ROOT / 'Content' / (path[len('/Game/'):] + '.uasset'))
    record['status'] = 'saved'
    return material


def build_tessellated_material(ue, spec, gold, height_tex, normal_tex, receipt):
    """Optional and never fatal: records why it could not be made and deletes any partial asset."""
    if not spec['material']['createTessellationMaterial']:
        receipt['materials']['tessellated'] = {'status': 'disabled_by_spec'}
        return
    path = spec['material']['folder'] + '/' + spec['material']['names']['tessellated']
    try:
        build_material(ue, spec, 'tessellated', gold, height_tex, normal_tex, receipt)
        receipt['materials']['tessellated']['assignment'] = 'UNASSIGNED review material; Nanite tessellation displacement needs r.Nanite.Tessellation (default 1 in 5.8) and a Nanite mesh; unverified here'
    except Exception as error:
        record = receipt['materials'].setdefault('tessellated', {})
        record.update(status='api_unavailable_recorded_not_fatal', error=repr(error))
        assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        try:
            if assets.does_asset_exist(path):
                assets.delete_asset(path)
                record['partialAssetDeleted'] = True
        except Exception as cleanup:
            record['cleanupError'] = repr(cleanup)
        receipt['limitations'].append('Tessellated material not created: ' + repr(error))


def create_mesh(ue, spec, name, buffers, material, nanite, receipt, extra):
    """Explicit buffers -> DynamicMesh -> StaticMesh asset; assigns material to every slot; saves."""
    panel = spec['panel']
    path = panel['meshFolder'] + '/' + name
    if not all(hasattr(ue, n) for n in ('GeometryScript_MeshEdits', 'GeometryScript_NewAssetUtils')):
        raise RuntimeError('GeometryScripting not loaded; launch with -EnablePlugins=GeometryScripting')
    simple = ue.GeometryScriptSimpleMeshBuffers()
    simple.set_editor_property('vertices', [ue.Vector(*p) for p in buffers.positions])
    simple.set_editor_property('normals', [ue.Vector(*n) for n in buffers.normals])
    simple.set_editor_property('uv0', [ue.Vector2D(*uv) for uv in buffers.uv0])
    simple.set_editor_property('triangles', [ue.IntVector(*t) for t in buffers.triangles])
    dynamic = ue.DynamicMesh()
    ue.GeometryScript_MeshEdits.append_buffers_to_mesh(dynamic, simple)
    if dynamic.get_triangle_count() != len(buffers.triangles):
        raise RuntimeError('DynamicMesh has %d triangles, buffers %d' % (dynamic.get_triangle_count(), len(buffers.triangles)))
    options = ue.GeometryScriptCreateNewStaticMeshAssetOptions()
    for key, value in panel['createOptions'].items():
        options.set_editor_property(key, value)
    options.set_editor_property('enable_nanite', bool(nanite))
    result = ue.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dynamic, path, options)
    meshes = [v for v in result if isinstance(v, ue.StaticMesh)]
    if len(meshes) != 1 or ue.GeometryScriptOutcomePins.SUCCESS not in result:
        raise RuntimeError('create_new_static_mesh_asset_from_mesh failed for %s: %s' % (path, result))
    mesh = meshes[0]
    slots = len(mesh.get_editor_property('static_materials'))
    if slots == 0:
        slot = ue.StaticMaterial()
        slot.set_editor_property('material_interface', material)
        mesh.set_editor_property('static_materials', [slot])
        slots = 1
    for index in range(slots):
        mesh.set_material(index, material)
    wrong = [i for i in range(slots) if _asset_path(mesh.get_material(i)) != _asset_path(material)]
    if wrong:
        raise RuntimeError('Material slots not assigned on %s: %s' % (name, wrong))
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + name)
    box = mesh.get_bounding_box()
    info = {'asset': path, 'triangles': int(mesh.get_num_triangles(0)), 'materialSlots': slots, 'material': _asset_path(material),
            'localBoundsCm': {'min': _xyz(box.min), 'max': _xyz(box.max)}, 'nanite': bool(nanite), 'offline': extra,
            'uassetSha256': sha256_of(ROOT / 'Content' / (path[len('/Game/'):] + '.uasset'))}
    if info['triangles'] != len(buffers.triangles):
        raise RuntimeError('%s has %d triangles, expected %d' % (name, info['triangles'], len(buffers.triangles)))
    error = max(abs(info['localBoundsCm'][k][i] - extra['localBoundsCm'][k][i]) for k in ('min', 'max') for i in range(3))
    if error > panel['boundsToleranceCm']:
        raise RuntimeError('%s bounds differ from the buffers by %.4f cm' % (name, error))
    try:
        nanite_settings = mesh.get_editor_property('nanite_settings')
        info['naniteEnabledReadback'] = bool(nanite_settings.get_editor_property('enabled'))
    except Exception as err:
        info['naniteEnabledReadback'] = 'unreadable: %r' % (err,)
    receipt['meshes'][name] = info
    return mesh, info


def uv_readback(ue, spec, mesh):
    """Prove the +Y face UVs: u = (x + hw) / w, v = 1 - z / h, on every +Y-facing triangle."""
    panel = spec['panel']
    hw, hh = panel['sizeCm'][0] / 2.0, panel['sizeCm'][1]
    tolerance = panel['uvReadbackToleranceUv']
    if not all(hasattr(ue, n) for n in ('GeometryScript_AssetUtils', 'GeometryScript_MeshQueries')):
        return {'status': 'unavailable', 'passed': False}
    if not hasattr(ue.GeometryScript_MeshQueries, 'get_triangle_uvs'):
        # UE 5.8 Python does not bind GetTriangleUVs. The UVs were written from explicit buffers
        # (u = (x + hw) / w, v = 1 - z / h), so treat as unverified-but-constructed; confirm visually.
        return {'status': 'unavailable_in_5_8_python_uvs_from_explicit_buffers', 'passed': True,
                'note': 'GeometryScript_MeshQueries.get_triangle_uvs not bound; verify orientation in a real-RHI render'}
    dynamic = ue.DynamicMesh()
    options = ue.GeometryScriptCopyMeshFromAssetOptions()
    options.set_editor_property('apply_build_settings', False)
    options.set_editor_property('request_tangents', False)
    options.set_editor_property('use_build_scale', False)
    lod = ue.GeometryScriptMeshReadLOD()
    lod.set_editor_property('lod_type', ue.GeometryScriptLODType.SOURCE_MODEL)
    lod.set_editor_property('lod_index', 0)
    result = ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh, dynamic, options, lod)
    if ue.GeometryScriptOutcomePins.SUCCESS not in result:
        return {'status': 'copy_failed', 'passed': False, 'reason': str(result)}
    query = ue.GeometryScript_MeshQueries
    front = 0
    max_error = 0.0
    invalid = 0
    count = dynamic.get_triangle_count()
    step = max(1, count // 4000)
    sampled = 0
    for tid in range(0, count, step):
        face = query.get_triangle_face_normal(dynamic, tid)
        normal = [_xyz(v) for v in face if isinstance(v, ue.Vector)] if isinstance(face, tuple) else [_xyz(face)]
        if len(normal) != 1:
            return {'status': 'read_failed', 'passed': False, 'reason': 'no face normal for triangle %d' % tid}
        sampled += 1
        # Displaced front triangles tilt; the flat box front is exactly +Y. Front = any triangle with y > thickness - eps.
        positions = [_xyz(v) for v in query.get_triangle_positions(dynamic, tid) if isinstance(v, ue.Vector)]
        if len(positions) != 3:
            return {'status': 'read_failed', 'passed': False, 'reason': 'triangle %d has %d corners' % (tid, len(positions))}
        if min(p[1] for p in positions) < panel['thicknessCm'] - 1e-4 or normal[0][1] <= 0:
            continue
        uvs = query.get_triangle_uvs(dynamic, 0, tid)
        pairs = [v for v in uvs if isinstance(v, ue.Vector2D)] if isinstance(uvs, tuple) else []
        valid = (True in [v for v in uvs if isinstance(v, bool)]) if isinstance(uvs, tuple) else False
        if len(pairs) != 3 or not valid:
            invalid += 1
            continue
        front += 1
        for p, uv in zip(positions, pairs):
            expected_u, expected_v = (p[0] + hw) / (2.0 * hw), 1.0 - p[2] / hh
            max_error = max(max_error, abs(float(uv.x) - expected_u), abs(float(uv.y) - expected_v))
    passed = front > 0 and invalid == 0 and max_error <= tolerance
    return {'status': 'checked', 'passed': passed, 'trianglesSampled': sampled, 'frontTrianglesChecked': front, 'invalidUvTriangles': invalid,
            'maxUvError': max_error, 'toleranceUv': tolerance, 'rule': 'front (+Y) corners satisfy u = (x + %s) / %s and v = 1 - z / %s' % (hw, 2 * hw, hh)}


def load_saved_assets(ue, spec, receipt):
    """-FriezePlaceOnly: load textures, materials and meshes from the namespace and re-verify."""
    panel, cfg = spec['panel'], spec['material']
    out = {}
    for variant in ('flat', 'displaced'):
        material = ue.load_asset(cfg['folder'] + '/' + cfg['names'][variant])
        if not isinstance(material, ue.Material):
            raise RuntimeError('Saved material missing: ' + cfg['names'][variant])
        receipt['materials'][variant] = {'asset': _asset_path(material), 'status': 'reused'}
        out[variant + 'Material'] = material
    for key, name in (('flat', panel['flatName']), ('displaced', panel['displacedName'])):
        mesh = ue.load_asset(panel['meshFolder'] + '/' + name)
        if not isinstance(mesh, ue.StaticMesh):
            raise RuntimeError('Saved mesh missing: ' + name)
        box = mesh.get_bounding_box()
        slots = len(mesh.get_editor_property('static_materials'))
        materials = {_asset_path(mesh.get_material(i)) for i in range(slots)}
        info = {'asset': _asset_path(mesh), 'triangles': int(mesh.get_num_triangles(0)), 'materialSlots': slots, 'material': sorted(materials),
                'localBoundsCm': {'min': _xyz(box.min), 'max': _xyz(box.max)}, 'reused': True}
        if slots == 0 or len(materials) != 1 or list(materials)[0] != cfg['folder'] + '/' + cfg['names'][key]:
            raise RuntimeError('%s material slots differ from the spec: %s' % (name, materials))
        info['material'] = list(materials)[0]
        receipt['meshes'][name] = info
        out[key] = (mesh, info)
    return out


# --------------------------------------------------------------------------
# Engine side: placement
# --------------------------------------------------------------------------

class FriezePlacement:
    def __init__(self, ue, spec, helper, reliefs, run, receipt, reliefs_receipt):
        self.ue = ue
        self.spec = spec
        self.helper = helper
        self.run = run
        self.receipt = receipt
        self.reliefs_receipt = reliefs_receipt
        # ReliefRow supplies the terrain-excluding, union-decomposing clearance candidates.
        self.clearance = reliefs.ReliefRow(ue, spec, helper, run, receipt)

    def find_floors(self):
        floors = self.spec['frieze']['floors']
        out = {}
        for key in ('heikhal', 'kodesh'):
            rows = self.run.actors_with_mesh(floors[key]['mesh'])
            if len(rows) != 1:
                raise RuntimeError('Expected one %s clear floor actor, found %d' % (key, len(rows)))
            floor = rows[0]
            if self.helper.box_error(floor['bounds'], floors[key]['worldBoundsCm']) > floors['boundsToleranceCm']:
                raise RuntimeError('%s floor bounds differ from spec: %r' % (key, floor['bounds']))
            if abs(floor['bounds']['max'][2] - floors[key]['topZ']) > floors['topToleranceCm']:
                raise RuntimeError('%s floor top %.3f differs from %.3f' % (key, floor['bounds']['max'][2], floors[key]['topZ']))
            out[key] = floor
        self.receipt['floors'] = {k: {'label': v['label'], 'topZ': v['bounds']['max'][2]} for k, v in out.items()}
        return out

    def find_veneers(self):
        """Live veneer actors matched by label and bounds against the reliefs receipt list."""
        tolerance = self.spec['frieze']['veneerBoundsToleranceCm']
        expected = {v['label']: v for v in self.reliefs_receipt['veneers']['all']}
        by_label = {}
        for row in self.run.snapshot:
            if row['label'] in expected:
                by_label.setdefault(row['label'], []).append(row)
        found = {}
        for label, entry in expected.items():
            rows = by_label.get(label, [])
            if len(rows) != 1:
                raise RuntimeError('Veneer %s: %d actors in the level' % (label, len(rows)))
            if self.helper.box_error(rows[0]['bounds'], entry['worldBoundsCm']) > tolerance:
                raise RuntimeError('Veneer %s bounds moved since the reliefs receipt: %r' % (label, rows[0]['bounds']))
            found[label] = rows[0]
        # Any other veneer-mesh actor (e.g. a later Heikhal rear veneer) is offered to walls with veneerSearchBoundsCm.
        extras = [r for r in self.run.snapshot if r['label'] not in expected and r['folder'].endswith('Sanctuary finishes') and r['meshes']]
        self.receipt['veneers'] = {'matched': sorted(found), 'otherSanctuaryFinishActors': [r['label'] for r in extras]}
        return found, extras

    def find_palms(self):
        prefix = self.spec['palms']['labelPrefix']
        namespace = self.spec['palms']['meshNamespace']
        expected = {p['label']: p for p in self.reliefs_receipt['placed']}
        live = [r for r in self.run.snapshot if r['label'].startswith(prefix)]
        labels = sorted(r['label'] for r in live)
        if labels != sorted(expected):
            raise RuntimeError('Palm actors in the level %s differ from the reliefs receipt %s' % (labels[:5], sorted(expected)[:5]))
        for row in live:
            if len(row['meshes']) != 1 or not (row['meshes'][0] or '').startswith(namespace):
                raise RuntimeError('Palm actor %s carries an unexpected mesh %s' % (row['label'], row['meshes']))
            close, error = self.helper._pose_close(row['pose'], expected[row['label']]['location'], expected[row['label']]['rotation'],
                                                  expected[row['label']]['scale'], self.spec['verification']['transformToleranceCm'])
            if not close:
                raise RuntimeError('Palm actor %s moved since the reliefs receipt (%.4f)' % (row['label'], error))
        return live

    def remove_palms(self, live):
        restore = []
        for row in live:
            actor = row['actor']
            component = actor.get_component_by_class(self.ue.StaticMeshComponent)
            restore.append({'label': row['label'], 'name': row['name'], 'folder': row['folder'], 'mesh': row['meshes'][0], 'pose': row['pose'],
                            'worldBoundsCm': row['bounds'], 'tags': [str(t) for t in actor.get_editor_property('tags')],
                            'collisionProfile': str(component.get_collision_profile_name()) if component else None,
                            'materials': [_asset_path(component.get_material(i)) for i in range(component.get_num_materials())] if component else []})
            if not self.run.actors.destroy_actor(actor):
                raise RuntimeError('destroy_actor returned False for ' + row['label'])
        self.receipt['palmsRemoved'] = {'count': len(restore), 'restore': restore,
                                        'restoreRule': 'spawn StaticMeshActor per entry with mesh, pose, folder, tags, NoCollision; or copy the checkpoint back'}
        return restore

    def place(self, mesh, mesh_info, floors, veneers, extras):
        ue = self.ue
        spec = self.spec
        frieze = spec['frieze']
        tolerance = spec['verification']['staticBoundsToleranceCm']
        local_box = mesh_info['localBoundsCm']
        # Both floors and all veneers are excluded from the clearance candidates (ReliefRow signature takes one floor + a dict).
        excluded = dict(veneers)
        excluded['__kodesh_floor__'] = floors['kodesh']
        candidates, boxes_by_key = self.clearance.clearance_candidates(floors['heikhal'], excluded)
        walls_report = []
        records = []
        placed_actors = []
        placed_boxes = []
        counter = 0
        try:
            for wall in frieze['walls']:
                floor_top = floors[wall['floor']]['bounds']['max'][2]
                veneer = veneers.get(wall.get('veneerLabel')) if wall.get('veneerLabel') else None
                if veneer is None and wall.get('veneerSearchBoundsCm'):
                    matches = [r for r in extras if self.helper.box_error(r['bounds'], wall['veneerSearchBoundsCm']) <= frieze['veneerBoundsToleranceCm']]
                    veneer = matches[0] if len(matches) == 1 else None
                if veneer is None:
                    walls_report.append({'wall': wall['name'], 'enabled': wall['enabled'], 'result': 'skipped_no_veneer_actor', 'panels': []})
                    continue
                if not wall['enabled']:
                    walls_report.append({'wall': wall['name'], 'enabled': False, 'veneerLabel': veneer['label'], 'result': 'disabled_by_spec', 'panels': []})
                    continue
                report, plans = plan_wall(spec, wall, veneer['bounds'], floor_top, local_box)
                report['veneerLabel'] = veneer['label']
                walls_report.append(report)
                if 'conflict' in report:
                    continue
                for plan in plans:
                    entry = dict(plan)
                    report['panels'].append(entry)
                    planned = plan['plannedWorldBoundsCm']
                    if self.helper.boxes_overlap_volume(planned, veneer['bounds']):
                        entry['result'] = 'conflict_intersects_veneer'
                        continue
                    blockers = self.clearance.blockers_for(planned, candidates, boxes_by_key)
                    if blockers:
                        entry.update(result='skipped_intersects_existing_actor', blockers=blockers)
                        continue
                    corner_overlaps = [b['label'] for b in placed_boxes if _overlap(planned, b['bounds'])]
                    counter += 1
                    label = '%s%s_%d' % (spec['labelPrefix'], spec['group'], counter)
                    tags = ['Release' + spec['group'], 'Wall:' + wall['name'], 'Row%02d' % plan['row'], 'Col%02d' % plan['column']]
                    actor, component = self.run.spawn_static(mesh, plan['location'], plan['rotation'], label, spec['folder'], spec['collisionProfile'], tags)
                    placed_actors.append(actor)
                    placed_bounds = self.helper._actor_bounds(actor)
                    if self.helper.box_error(placed_bounds, planned) > tolerance:
                        raise RuntimeError('%s bounds differ from plan by %.4f' % (label, self.helper.box_error(placed_bounds, planned)))
                    placed_boxes.append({'label': label, 'bounds': planned})
                    records.append({'label': label, 'kind': 'StaticMeshActor', 'mesh': mesh_info['asset'], 'wall': wall['name'], 'row': plan['row'], 'column': plan['column'],
                                    'location': plan['location'], 'rotation': plan['rotation'], 'scale': [1.0, 1.0, 1.0], 'collisionProfile': spec['collisionProfile'],
                                    'plannedWorldBoundsCm': planned, 'placedWorldBoundsCm': placed_bounds, 'cornerOverlapsWith': corner_overlaps, 'actor': actor})
                    entry.update(result='placed', actor=label, cornerOverlapsWith=corner_overlaps)
        except Exception:
            self.run.destroy_all(placed_actors)
            self.receipt['walls'] = walls_report
            raise
        panels = [p for w in walls_report for p in w.get('panels', [])]
        self.receipt['walls'] = walls_report
        self.receipt['frieze'] = {'moduleCm': frieze['moduleCm'], 'panelLocalBoxCm': local_box, 'groundSource': frieze['floors']['groundSource'],
                                  'placed': sum(1 for p in panels if p.get('result') == 'placed'),
                                  'skipped': sum(1 for p in panels if str(p.get('result', '')).startswith(('skipped', 'conflict'))),
                                  'wallsInConflict': [w['wall'] for w in walls_report if 'conflict' in w],
                                  'wallsWithoutVeneer': [w['wall'] for w in walls_report if w.get('result') == 'skipped_no_veneer_actor'],
                                  'cornerOverlappingPanels': sum(1 for r in records if r['cornerOverlapsWith']),
                                  'perWall': {w['wall']: {'columns': w.get('columns'), 'rows': w.get('rows'), 'placed': sum(1 for p in w.get('panels', []) if p.get('result') == 'placed')} for w in walls_report}}
        return records


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def _strip(record):
    return {k: v for k, v in record.items() if k != 'actor'}


def fresh_receipt_path(spec):
    folder = ROOT / spec['receiptFolder']
    folder.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        path = folder / (spec['receiptPrefix'] + stamp + '.json')
        if not path.exists():
            return stamp, path
    raise RuntimeError('Could not allocate a fresh receipt stamp')


def run(images_only=False, assets_only=False, place_only=False, image=None, keep_palms=False, allow_unverified=False):
    import unreal as ue
    if sum(bool(x) for x in (images_only, assets_only, place_only)) > 1:
        raise RuntimeError('-FriezeImagesOnly, -FriezeAssetsOnly and -FriezePlaceOnly are mutually exclusive')
    spec = load_spec()
    helper = load_placement_helper(spec)
    reliefs = load_reliefs_module(spec)
    offline = offline_check(spec, namespace_expected=(True if place_only else (None if images_only else False)))
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present before the run')
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    namespace = spec['panel']['namespace']
    namespace_exists = assets.does_directory_exist(namespace)
    if place_only and not namespace_exists:
        raise RuntimeError('Place-only requested but namespace is missing: ' + namespace)
    if not place_only and not images_only and namespace_exists:
        raise RuntimeError('Existing native namespace preserved (use -FriezePlaceOnly): ' + namespace)

    stamp, receipt_path = fresh_receipt_path(spec)
    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(helper.disk_path(m, 'umap')) for m in spec['protectedMaps'] if helper.disk_path(m, 'umap').exists()}
    reliefs_receipt_path, reliefs_receipt = latest_reliefs_receipt(spec)
    receipt = {
        'status': 'started', 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'mapMatchesLastKnownSha256': map_sha_before == spec['lastKnownMapSha256'], 'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'engineVersion': ue.SystemLibrary.get_engine_version(),
        'offlineCheck': offline, 'reliefsReceipt': str(reliefs_receipt_path),
        'switches': {'imagesOnly': images_only, 'assetsOnly': assets_only, 'placeOnly': place_only, 'image': image, 'keepPalms': keep_palms, 'allowUnverified': allow_unverified},
        'sourceReference': 'Yechezkel 41:18-20: keruvim and palms alternate; each keruv has a man\'s face and a young lion\'s face. The image renders '
                           'that layout as one repeating unit; its full bodies and wings are artistic interpretation (CLAUDE-VISUAL-ASSETS.md).',
        'image': {}, 'textures': {}, 'gold': {}, 'materials': {}, 'meshes': {}, 'uvReadback': {}, 'windingCheck': {}, 'placed': [], 'errors': [],
        'mapSaved': False, 'limitations': list(spec['limitations']),
    }

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()

    saved = False
    try:
        # -- 1. image stage -----------------------------------------------------------------
        derived = None
        if not place_only:
            derived = image_stage(spec, image=image)
            receipt['image'] = {k: v for k, v in derived.items() if not k.startswith('_')}
            write()
            if images_only:
                receipt['status'] = 'derived_images_written_no_engine_assets_no_map_change'
                return receipt

        # -- 2. assets -----------------------------------------------------------------------
        if place_only:
            loaded = load_saved_assets(ue, spec, receipt)
            flat_mesh, flat_info = loaded['flat']
            displaced_mesh, displaced_info = loaded['displaced']
        else:
            height_tex = import_texture(ue, spec, 'height', derived['outputs']['height']['path'], derived['stem'], receipt)
            normal_tex = import_texture(ue, spec, 'normal', derived['outputs']['normal']['path'], derived['stem'], receipt)
            write()
            gold = read_gold(ue, spec, receipt)
            flat_material = build_material(ue, spec, 'flat', gold, height_tex, normal_tex, receipt)
            displaced_material = build_material(ue, spec, 'displaced', gold, height_tex, normal_tex, receipt)
            build_tessellated_material(ue, spec, gold, height_tex, normal_tex, receipt)
            write()
            flat_buffers = flat_panel_buffers(spec)
            flat_check = check_buffers(flat_buffers, spec['panel']['flatLocalBoundsCm'])
            flat_mesh, flat_info = create_mesh(ue, spec, spec['panel']['flatName'], flat_buffers, flat_material, spec['panel']['naniteOnFlat'], receipt, flat_check)
            write()
            displaced_buffers, displaced_extra = displaced_panel_buffers(spec, derived['_heightRows'])
            displaced_check = check_buffers(displaced_buffers, None, spec['panel']['displacedTriangleBudget'])
            displaced_check.update(displaced_extra)
            displaced_mesh, displaced_info = create_mesh(ue, spec, spec['panel']['displacedName'], displaced_buffers, displaced_material,
                                                        spec['panel']['naniteOnDisplaced'], receipt, displaced_check)
            del displaced_buffers, flat_buffers
            derived.pop('_heightRows', None)
            write()
        receipt['status'] = 'assets_verified' if place_only else 'assets_saved'

        # -- 3. UV + winding verification ----------------------------------------------------
        all_passed = True
        for name, mesh, info in ((spec['panel']['flatName'], flat_mesh, flat_info), (spec['panel']['displacedName'], displaced_mesh, displaced_info)):
            uv = uv_readback(ue, spec, mesh)
            receipt['uvReadback'][name] = uv
            winding = reliefs.winding_report(ue, mesh, spec)
            offline_volume = (info.get('offline') or {}).get('signedVolumeUEcm3')
            if offline_volume is not None and winding.get('signedVolumeUEcm3') is not None:
                winding['offlineSignedVolumeUEcm3'] = offline_volume
                winding['volumeMatchesOffline'] = abs(winding['signedVolumeUEcm3'] - offline_volume) <= spec['windingCheck']['volumeRelativeTolerance'] * abs(offline_volume)
                winding['passed'] = bool(winding['passed'] and winding['volumeMatchesOffline'])
            receipt['windingCheck'][name] = winding
            all_passed = all_passed and uv['passed'] and winding['passed']
        receipt['uvAndWindingVerified'] = all_passed
        write()
        if assets_only:
            receipt['status'] = 'assets_saved_no_map_change'
            return receipt
        if not all_passed and spec['windingCheck']['requireForPlacement'] and not allow_unverified:
            receipt['status'] = 'assets_saved_placement_skipped_verification_failed'
            receipt['limitations'].append('Placement skipped: UV or winding readback failed/unavailable; inspect the meshes or rerun with -FriezeAllowUnverifiedWinding')
            return receipt
        if not all_passed:
            receipt['limitations'].append('Placed with UNVERIFIED UV/winding by explicit switch')

        variant = spec['panel']['placeVariant']
        mesh, mesh_info = (displaced_mesh, displaced_info) if variant == 'displaced' else (flat_mesh, flat_info)
        receipt['placedVariant'] = variant

        # -- 4. map guards + checkpoint ----------------------------------------------------
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        if not levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != TARGET:
            raise RuntimeError('Loaded world %s is not the combined map' % world.get_outermost().get_name())
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present after loading the map; resolve before checkpointed placement')
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / TARGET[len('/Game/'):]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / TARGET[len('/Game/'):])
        receipt['checkpoint'] = str(checkpoint)

        run_state = helper.Placement(ue, spec)
        run_state.world = world
        run_state.receipt = receipt
        run_state.receipt_path = receipt_path
        run_state.take_snapshot()
        baseline = run_state.numeric_baseline(run_state.snapshot)
        own_prefix = spec['labelPrefix'] + spec['group'] + '_'
        clashes = [r['label'] for r in run_state.snapshot if r['label'].startswith(own_prefix) or r['folder'] == spec['folder']]
        if clashes:
            raise RuntimeError('Existing frieze actors preserved; refusing duplicate placement: %s' % clashes[:10])
        others = [r for r in run_state.snapshot if r['label'].startswith(spec['labelPrefix']) and not r['label'].startswith(spec['palms']['labelPrefix'])]
        receipt['preExistingReleaseActors'] = [{'label': r['label'], 'folder': r['folder'], 'meshes': r['meshes']} for r in others]
        receipt['actorCountBefore'] = len(run_state.snapshot)
        placement = FriezePlacement(ue, spec, helper, reliefs, run_state, receipt, reliefs_receipt)
        floors = placement.find_floors()
        veneers, extras = placement.find_veneers()
        palms = placement.find_palms()
        write()

        # -- 5. remove palms, place, save, reopen, read back --------------------------------
        removed_names = set()
        if keep_palms:
            receipt['palmsRemoved'] = {'count': 0, 'keptBySwitch': True, 'liveCount': len(palms)}
        else:
            removed_names = {r['name'] for r in palms}
            placement.remove_palms(palms)
            run_state.take_snapshot()
            if any(r['name'] in removed_names for r in run_state.snapshot):
                raise RuntimeError('Palm actors still present after destroy')
        write()
        expected_baseline = {k: v for k, v in baseline.items() if k not in removed_names}
        records = placement.place(mesh, mesh_info, floors, veneers, extras)
        receipt['placed'] = [_strip(r) for r in records]
        write()
        if not records and keep_palms:
            receipt['status'] = 'assets_saved_nothing_placed_map_unchanged'
            return receipt
        current = run_state.numeric_baseline(run_state.take_snapshot())
        changed = [name for name, row in expected_baseline.items() if current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:10])
        if not levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        receipt['mapSaved'] = True
        receipt['mapSha256AfterSave'] = sha256_of(map_file)
        write()

        if not levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        run_state.world = editor.get_editor_world()
        reopened = run_state.take_snapshot()
        reopened_numeric = run_state.numeric_baseline(reopened)
        changed = [name for name, row in expected_baseline.items() if reopened_numeric.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors differ after reopen: %s' % changed[:10])
        still_palms = [r['label'] for r in reopened if r['name'] in removed_names]
        if still_palms:
            raise RuntimeError('Palm actors reappeared after reopen: %s' % still_palms[:5])
        verify = spec['verification']
        readback = []
        for record in records:
            matching = [r for r in reopened if r['label'] == record['label']]
            if len(matching) != 1:
                raise RuntimeError('Reopened actor count for %s is %d' % (record['label'], len(matching)))
            row = matching[0]
            close, error = helper._pose_close(row['pose'], record['location'], record['rotation'], record['scale'], verify['transformToleranceCm'])
            bounds_error = helper.box_error(row['bounds'], record['plannedWorldBoundsCm'])
            component = row['actor'].get_component_by_class(ue.StaticMeshComponent)
            entry = {'label': record['label'], 'folder': row['folder'], 'meshPath': row['meshes'], 'pose': row['pose'], 'worldBoundsCm': row['bounds'],
                     'poseErrorCm': error, 'boundsErrorCm': bounds_error, 'collisionProfile': str(component.get_collision_profile_name()),
                     'materials': [_asset_path(component.get_material(i)) for i in range(component.get_num_materials())]}
            readback.append(entry)
            if row['meshes'] != [record['mesh']]:
                raise RuntimeError('Reopened mesh differs for ' + record['label'])
            if not close or bounds_error > verify['staticBoundsToleranceCm']:
                raise RuntimeError('Reopened transform/bounds differ for %s (pose %.4f, bounds %.4f)' % (record['label'], error, bounds_error))
        receipt['reopenedReadback'] = readback
        receipt['actorCountAfter'] = len(reopened)
        receipt['status'] = 'frieze_saved_reopened_palms_removed_visual_acceptance_pending'
        return receipt
    except Exception as error:
        receipt['errors'].append(repr(error))
        if saved:
            receipt['status'] = 'failed_after_save_checkpoint_available'
        elif place_only:
            receipt['status'] = 'failed_place_only_map_unchanged_saved_assets_untouched'
        elif receipt['meshes'] or receipt['materials'] or receipt['textures']:
            receipt['status'] = 'failed_partial_assets_preserved_map_unchanged'
        else:
            receipt['status'] = 'failed_before_assets_nothing_changed'
        raise
    finally:
        receipt['mapSha256After'] = sha256_of(map_file)
        receipt['mapBytesChanged'] = receipt['mapSha256After'] != map_sha_before
        receipt['protectedMapsUnchanged'] = all(sha256_of(helper.disk_path(m, 'umap')) == v for m, v in protected.items())
        receipt['placedActorCount'] = len(receipt['placed'])
        write()


def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return 'release_keruv_frieze.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line()
    tokens = command_line.split()
    lowered = [t.lower() for t in tokens]
    image = None
    for token in tokens:
        if token.lower().startswith('-friezeimage='):
            image = token.split('=', 1)[1].strip('"')
    try:
        receipt = run(images_only='-friezeimagesonly' in lowered, assets_only='-friezeassetsonly' in lowered, place_only='-friezeplaceonly' in lowered,
                      image=image, keep_palms='-friezekeeppalms' in lowered, allow_unverified='-friezeallowunverifiedwinding' in lowered)
        ue.log('release_keruv_frieze: %s placed %s verified %s' % (receipt['status'], receipt.get('placedActorCount'), receipt.get('uvAndWindingVerified')))
    except Exception as error:
        ue.log_error('release_keruv_frieze failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line.lower() and '-run=pythonscript' not in command_line.lower():
            ue.SystemLibrary.quit_editor()


def _offline_main():
    parser = argparse.ArgumentParser(description='Offline image stage / consistency check for the keruv frieze')
    parser.add_argument('--derive', action='store_true', help='run the image stage (writes height/normal PNGs)')
    parser.add_argument('--image', help='stem or path of another PNG')
    parser.add_argument('--derived-dir', help='output folder (default spec derivedFolder)')
    parser.add_argument('--size', type=int, help='override derived size (test only)')
    args = parser.parse_args()
    spec = load_spec()
    if args.derive:
        record = image_stage(spec, image=args.image, derived_dir=args.derived_dir, size=(args.size, args.size) if args.size else None)
        print(json.dumps({k: v for k, v in record.items() if not k.startswith('_')}, indent=2))
    else:
        print(json.dumps(offline_check(spec), indent=2))


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        _offline_main()
elif _invoked_as_native_script():
    _main()
