"""Kotel ashlar V2: real block geometry for the four west-facing Western Wall faces.

Offline generator only (stdlib, no engine). Reads the audited face segments from
SourceAssets/kotel-detail/KotelStoneV1/manifest.json (edges 24, 25, 0, 1; wall base
-1399.695 cm, top 600.305 cm) and writes, per face, one OBJ of individual closed stone
blocks plus a 1 cm mortar bed, a manifest and two orthographic software previews into
SourceAssets/kotel-detail/KotelStoneV2/.

Course schedule (bottom -> top, sums to the 2000 cm face height exactly):
  7 Herodian courses 110-120 cm, drafted margin 6-9 cm + raised boss, stones 150-320 cm;
  8 middle courses 62-80 cm, narrow margin, stones 110-220 cm;
 14 upper courses 42-47 cm, chamfered edges, stones 90-160 cm.
Joints 3 cm; the joint bottom is the mortar bed at +2 cm in front of the source face;
block margin planes stand 3 + [0..6] cm in front of the bed with a slight random tilt.

Per-stone attributes travel in UV0 because the legacy OBJ adapter carries no vertex
colour and StaticMeshDescription.SetVertexInstanceColor is not exposed to Python:
  u = 8 * tintIndex   (0..7) + planar local u (0..3.3)
  v = 8 * jitterIndex (0..15) + planar local v (0..1.3)
The release material decodes floor(u/8) / floor(v/8) and samples the limestone PBR set
with world-aligned coordinates; the local planar part keeps import tangents valid.

Winding: canonical UE XYZ cm with algebraic outward normals (cross(B-A, C-A)); the OBJ
reflects Y and reverses winding for the legacy importer, exactly as KotelStoneV1 and
DoorsParochesV1. Every block is checked closed (edge-manifold) with positive signed volume.

Tints: 8 warm limestone albedos derived from the cleaned photo derivative
(PhotoSurfaceV1/kotel-wall-cleaned.png) as a colour reference only: luminance percentiles,
chroma desaturated 45 percent toward neutral and normalised to a 0.52 linear median, since
the photo's lighting is partly baked in. A fixed fallback palette is used if the PNG is absent.

Run:  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\ThirdParty\\Python3\\Win64\\python.exe"
      Scripts/create_kotel_stone_v2.py            (refuses to overwrite once a native receipt exists)
"""
import hashlib
import json
import math
import random
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1_MANIFEST = ROOT / 'SourceAssets/kotel-detail/KotelStoneV1/manifest.json'
PHOTO = ROOT / 'SourceAssets/kotel-detail/PhotoSurfaceV1/kotel-wall-cleaned.png'
FOLDER = ROOT / 'SourceAssets/kotel-detail/KotelStoneV2'
NAMESPACE = '/Game/MikdashV3/MaterialReview/KotelStoneV2'
SEED = 5788
JOINT_CM = 3.0
BED_BACK_CM = 1.0          # mortar bed starts 1 cm in front of the source face
BED_FRONT_CM = 2.0         # joint bottom
BLOCK_BACK_CM = 1.5        # block backs sit inside the bed (closed boxes, no coplanar faces)
PROUD_MAX_CM = 6.0
TILT_MAX = 0.006           # slope of the front plane (cm per cm) ~0.35 degrees
UV_STRIDE = 8.0
TINT_COUNT = 8
JITTER_COUNT = 16
MORTAR_TINT_INDEX = 8
TRIANGLE_BUDGET = 400000

# Bottom -> top. Sums to 2000 exactly (asserted).
COURSES = [
    dict(kind='herodian', heights=[120, 116, 118, 112, 115, 114, 110], lengths=(150, 320), margin=(6.0, 9.0),
         boss=(1.5, 2.5), chamfer=(1.0, 2.0), cap=6),
    dict(kind='middle', heights=[80, 74, 70, 76, 66, 72, 62, 68], lengths=(110, 220), margin=(3.0, 5.0),
         boss=(1.0, 1.5), chamfer=(0.8, 1.4), cap=4),
    dict(kind='upper', heights=[46, 43, 47, 44, 45, 42, 46, 44, 45, 43, 47, 44, 46, 45], lengths=(90, 160),
         margin=(0.0, 0.0), boss=(0.8, 1.2), chamfer=(1.0, 1.5), cap=3),
]
FALLBACK_TINTS = [(0.560, 0.505, 0.430), (0.610, 0.555, 0.470), (0.650, 0.590, 0.505), (0.520, 0.470, 0.400),
                  (0.690, 0.630, 0.545), (0.585, 0.540, 0.475), (0.630, 0.565, 0.470), (0.500, 0.455, 0.395)]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bounds_of(points):
    return {k: [fn(p[i] for p in points) for i in range(3)] for k, fn in (('min', min), ('max', max))}


# ----------------------------------------------------------------------------------------------
# Colour reference from the cleaned photo (stdlib PNG decode; RGB/RGBA 8-bit, non-interlaced)
# ----------------------------------------------------------------------------------------------

def decode_png_rgb(path):
    data = Path(path).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos = 8
    idat = []
    width = height = None
    channels = None
    while pos < len(data):
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
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
    previous = bytearray(stride)
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
                line[i] = (line[i] + previous[i]) & 255
        elif filter_type == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 255
        elif filter_type == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = previous[i]
                c = previous[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 255
        rows.append(line)
        previous = line
    return width, height, channels, rows


def srgb_to_linear(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def photo_reference_tints():
    """8 linear tints from photo luminance percentiles; chroma desaturated, median normalised."""
    if not PHOTO.is_file():
        return FALLBACK_TINTS, dict(source='fallback_palette', reason='cleaned photo missing')
    width, height, channels, rows = decode_png_rgb(PHOTO)
    lut = [srgb_to_linear(i) for i in range(256)]
    samples = []
    for y in range(0, height, 4):
        row = rows[y]
        for x in range(0, width, 4):
            i = x * channels
            r, g, b = lut[row[i]], lut[row[i + 1]], lut[row[i + 2]]
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            if lum > 0.002:
                samples.append((lum, r, g, b))
    samples.sort()
    n = len(samples)
    mean_lum = sum(s[0] for s in samples) / n
    ratios = [sum(s[k] / s[0] for s in samples) / n for k in (1, 2, 3)]      # chroma as r/l, g/l, b/l
    desat = 0.30
    ratios = [r * (1 - desat) + desat for r in ratios]
    median = samples[n // 2][0]
    target_median = 0.52
    # percentiles start at 20 so the photo's dark joints/shadows do not collapse onto the clamp
    percentiles = [20, 30, 40, 50, 60, 72, 85, 95]
    # compress the photo's luminance spread (baked shadows/highlights) around the median: exponent 0.55
    lums = [target_median * (samples[min(n - 1, int(n * p / 100))][0] / median) ** 0.55 for p in percentiles]
    lums = [max(0.42, min(0.74, l)) for l in lums]
    if any(b - a < 0.012 for a, b in zip(lums, lums[1:])):
        lo_l, hi_l = lums[0], lums[-1]
        lums = [lo_l + (hi_l - lo_l) * i / (len(lums) - 1) for i in range(len(lums))]
    tints = [tuple(round(l * r, 4) for r in ratios) for l in lums]
    assert len(set(tints)) == len(tints) and all(b > a for a, b in zip(lums, lums[1:])), 'tint variants must be distinct'
    stats = dict(source=PHOTO.relative_to(ROOT).as_posix(), sha256=sha256(PHOTO), pixels=[width, height],
                 sampledPixels=n, meanLuminanceLinear=round(mean_lum, 4), medianLuminanceLinear=round(median, 4),
                 photoChromaRatios=[round(sum(s[k] / s[0] for s in samples) / n, 4) for k in (1, 2, 3)],
                 usedChromaRatios=[round(r, 4) for r in ratios], desaturation=desat, targetMedianLinear=target_median,
                 percentiles=percentiles,
                 note='Colour/character reference only; photo lighting is partly baked in, so chroma is desaturated and luminance renormalised.')
    return tints, stats


# ----------------------------------------------------------------------------------------------
# Block geometry (local frame: x along the face, y up, z outward; algebraic outward winding)
# ----------------------------------------------------------------------------------------------

def ring(hw, hh, z, inset, tilt):
    ax, ay = tilt
    pts = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x = sx * (hw - inset)
        y = sy * (hh - inset)
        pts.append((x, y, z + ax * x + ay * y))
    return pts


def block_mesh(w, h, z_back, z_margin, margin, boss, chamfer, cap_n, tilt, rng, bump):
    """Closed block. Returns (vertices, triangles) in the local frame centred on the block face."""
    hw, hh = w / 2.0, h / 2.0
    assert margin + chamfer < min(hw, hh) - 1.0
    rings = [ring(hw, hh, z_back, 0.0, (0.0, 0.0)), ring(hw, hh, z_margin, 0.0, tilt)]
    if margin > 0:
        rings.append(ring(hw, hh, z_margin, margin, tilt))
    rings.append(ring(hw, hh, z_margin + boss, margin + chamfer, tilt))
    vertices = []
    triangles = []
    for r in rings:
        vertices.extend(r)
    # back cap (faces -z): ring 0 reversed
    triangles += [(0, 2, 1), (0, 3, 2)]
    for k in range(len(rings) - 1):
        a = 4 * k
        b = 4 * (k + 1)
        for i in range(4):
            j = (i + 1) % 4
            # outward quad between consecutive rings (ring order is CCW seen from +z)
            triangles += [(a + i, a + j, b + j), (a + i, b + j, b + i)]
    # front cap: (cap_n x cap_n) grid on the last ring, interior points bumped
    last = rings[-1]
    x0, y0 = last[0][0], last[0][1]
    x1, y1 = last[2][0], last[2][1]
    ax, ay = tilt
    z_top = z_margin + boss
    grid = {}
    base = len(vertices)
    for iy in range(cap_n + 1):
        for ix in range(cap_n + 1):
            x = x0 + (x1 - x0) * ix / cap_n
            y = y0 + (y1 - y0) * iy / cap_n
            interior = 0 < ix < cap_n and 0 < iy < cap_n
            dz = rng.uniform(-bump, bump) if interior else 0.0
            grid[(ix, iy)] = len(vertices)
            vertices.append((x, y, z_top + ax * x + ay * y + dz))
    # reuse the exact ring corners for the four grid corners so the cap is watertight
    corner_map = {grid[(0, 0)]: base - 4, grid[(cap_n, 0)]: base - 3, grid[(cap_n, cap_n)]: base - 2, grid[(0, cap_n)]: base - 1}
    for iy in range(cap_n):
        for ix in range(cap_n):
            a = grid[(ix, iy)]
            b = grid[(ix + 1, iy)]
            c = grid[(ix + 1, iy + 1)]
            d = grid[(ix, iy + 1)]
            a, b, c, d = (corner_map.get(v, v) for v in (a, b, c, d))
            triangles += [(a, b, c), (a, c, d)]
    # the outer ring edge of the cap must also match the ring vertices, not only the corners:
    # grid boundary points between corners are distinct vertices lying on the ring edge, which
    # leaves T-junctions on the ring quads. Split the ring->cap connection instead: the last
    # side quads were built to the ring corners, so add the boundary grid points as fan splits.
    return _fix_cap_boundary(vertices, triangles, rings, grid, cap_n, base, corner_map)


def _fix_cap_boundary(vertices, triangles, rings, grid, cap_n, base, corner_map):
    """Replace the last ring's side quads so each boundary grid vertex is a real edge vertex."""
    last_ring_start = 4 * (len(rings) - 1)
    prev_ring_start = 4 * (len(rings) - 2)
    # remove the side quads of the last ring pair (8 triangles appended before the cap)
    side_start = 2 + 8 * (len(rings) - 2)
    del triangles[side_start:side_start + 8]
    boundary_edges = [
        [grid[(ix, 0)] for ix in range(cap_n + 1)],                       # bottom: corner0 -> corner1
        [grid[(cap_n, iy)] for iy in range(cap_n + 1)],                   # right: corner1 -> corner2
        [grid[(ix, cap_n)] for ix in range(cap_n, -1, -1)],               # top: corner2 -> corner3
        [grid[(0, iy)] for iy in range(cap_n, -1, -1)],                   # left: corner3 -> corner0
    ]
    for i in range(4):
        j = (i + 1) % 4
        p0 = prev_ring_start + i
        p1 = prev_ring_start + j
        chain = [corner_map.get(v, v) for v in boundary_edges[i]]
        assert chain[0] == last_ring_start + i and chain[-1] == last_ring_start + j
        # fan with the original quad orientation (p0, p1, L_j), (p0, L_j, L_i): walk the chain backwards
        for k in range(len(chain) - 1):
            triangles.append((p0, chain[k + 1], chain[k]))
        triangles.append((p0, p1, chain[-1]))
    return vertices, triangles


def check_closed(vertices, triangles):
    """Edge-manifold check and signed volume (positive = algebraic outward winding)."""
    edges = {}
    volume = 0.0
    for a, b, c in triangles:
        for e in ((a, b), (b, c), (c, a)):
            edges[e] = edges.get(e, 0) + 1
        pa, pb, pc = vertices[a], vertices[b], vertices[c]
        volume += (pa[0] * (pb[1] * pc[2] - pb[2] * pc[1]) - pa[1] * (pb[0] * pc[2] - pb[2] * pc[0]) + pa[2] * (pb[0] * pc[1] - pb[1] * pc[0])) / 6.0
    for (a, b), count in edges.items():
        if count != 1 or edges.get((b, a), 0) != 1:
            return False, volume
    return True, volume


def box_mesh(w, h, d, cx, cy, cz):
    hw, hh, hd = w / 2, h / 2, d / 2
    v = [(cx + sx * hw, cy + sy * hh, cz + sz * hd) for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]
    # indices: bit0 x, bit1 y, bit2 z
    quads = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    t = []
    for a, b, c, d_ in quads:
        t += [(a, b, c), (a, c, d_)]
    return v, t


# ----------------------------------------------------------------------------------------------
# Course layout
# ----------------------------------------------------------------------------------------------

def layout_face(face, rng, lo, hi):
    """Return block records for one face: along start, width, z bottom, height, course params."""
    length = face['lengthCm']
    blocks = []
    z = lo
    previous_joints = []
    course_index = 0
    for group in COURSES:
        for height in group['heights']:
            lo_w, hi_w = group['lengths']
            x = 0.0
            joints = []
            while length - x > 0.01:
                remaining = length - x
                if remaining <= hi_w * 1.05:
                    width = remaining if remaining <= hi_w else remaining / 2.0
                else:
                    width = rng.uniform(lo_w, hi_w)
                    # keep vertical joints at least 15 cm from the joints of the course below
                    for _ in range(4):
                        joint = x + width
                        if any(abs(joint - pj) < 15.0 for pj in previous_joints) and length - joint > lo_w:
                            width = min(hi_w, width + 18.0) if width + 18.0 <= hi_w else max(lo_w, width - 18.0)
                        else:
                            break
                width = min(width, length - x)
                blocks.append(dict(course=course_index, kind=group['kind'], along=x, width=width, z=z, height=height,
                                   tint=rng.randrange(TINT_COUNT), jitter=rng.randrange(JITTER_COUNT),
                                   proud=rng.uniform(0.0, PROUD_MAX_CM),
                                   tilt=(rng.uniform(-TILT_MAX, TILT_MAX), rng.uniform(-TILT_MAX, TILT_MAX)),
                                   margin=rng.uniform(*group['margin']), boss=rng.uniform(*group['boss']),
                                   chamfer=rng.uniform(*group['chamfer']), cap=group['cap']))
                x += width
                if length - x > 0.01:
                    joints.append(x)
            previous_joints = joints
            z += height
            course_index += 1
    assert abs(z - hi) < 1e-6, (z, hi)
    return blocks


# ----------------------------------------------------------------------------------------------
# OBJ writer (legacy adapter: reflect Y, reverse winding; planar UV per triangle + attribute offsets)
# ----------------------------------------------------------------------------------------------

def write_obj(path, name, parts):
    """parts: list of (world_vertices, triangles, tint, jitter). Writes per-triangle vertices."""
    lines = ['# Kotel ashlar V2 (original geometry); UE legacy OBJ adapter, cm, Y reflected, winding reversed', 'o ' + name]
    n = 1
    count = 0
    min_uv_area = 1e30
    all_points = []
    for vertices, triangles, tint, jitter, uv_scale in parts:
        all_points.extend(vertices)
        du = UV_STRIDE * tint
        dv = UV_STRIDE * jitter
        for tri in triangles:
            a, b, c = (vertices[i] for i in tri)
            ab = [b[i] - a[i] for i in range(3)]
            ac = [c[i] - a[i] for i in range(3)]
            normal = [ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0]]
            nl = math.sqrt(sum(v * v for v in normal))
            e1l = math.sqrt(sum(v * v for v in ab))
            assert nl > 1e-9 and e1l > 1e-9, 'degenerate triangle'
            normal = [v / nl for v in normal]
            e1 = [v / e1l for v in ab]
            e2 = [normal[1] * e1[2] - normal[2] * e1[1], normal[2] * e1[0] - normal[0] * e1[2], normal[0] * e1[1] - normal[1] * e1[0]]
            planar = []
            for p in (a, b, c):
                d = [p[i] - a[i] for i in range(3)]
                planar.append((sum(d[i] * e1[i] for i in range(3)) / uv_scale, sum(d[i] * e2[i] for i in range(3)) / uv_scale))
            u_min = min(p[0] for p in planar)
            v_min = min(p[1] for p in planar)
            uvs = []
            for u, v in planar:
                u -= u_min
                v -= v_min
                assert 0.0 <= u < UV_STRIDE - 4.0 and 0.0 <= v < UV_STRIDE - 4.0, (u, v)
                uvs.append((du + u, dv + v))
            uv_area = abs((uvs[1][0] - uvs[0][0]) * (uvs[2][1] - uvs[0][1]) - (uvs[1][1] - uvs[0][1]) * (uvs[2][0] - uvs[0][0])) / 2
            min_uv_area = min(min_uv_area, uv_area)
            # legacy adapter: reflect Y and reverse winding (a, c, b)
            order = (a, c, b)
            uv_order = (uvs[0], uvs[2], uvs[1])
            obj_normal = (normal[0], -normal[1], normal[2])
            for p in order:
                lines.append('v %.5f %.5f %.5f' % (p[0], -p[1], p[2]))
            for uv in uv_order:
                lines.append('vt %.6f %.6f' % uv)
            for _ in range(3):
                lines.append('vn %.6f %.6f %.6f' % obj_normal)
            lines.append('f %d/%d/%d %d/%d/%d %d/%d/%d' % (n, n, n, n + 1, n + 1, n + 1, n + 2, n + 2, n + 2))
            n += 3
            count += 1
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    return dict(name=name, file=path.name, sha256=sha256(path), triangles=count, boundsCm=bounds_of(all_points), minimumUVArea=min_uv_area)


# ----------------------------------------------------------------------------------------------
# Software orthographic preview (method after sanctuary-detail/verify_and_preview.py)
# ----------------------------------------------------------------------------------------------

def render_preview(path, local_parts, tints, x_range, y_range, px_per_cm, light):
    W = int((x_range[1] - x_range[0]) * px_per_cm)
    H = int((y_range[1] - y_range[0]) * px_per_cm)
    rgb = bytearray([28, 30, 34] * (W * H))
    zbuf = [-1e9] * (W * H)
    ll = math.sqrt(sum(v * v for v in light))
    light = [v / ll for v in light]
    for vertices, triangles, tint_index, jitter in local_parts:
        tint = tints[tint_index] if tint_index < len(tints) else (0.26, 0.235, 0.20)
        scale = 1.0 + (jitter / (JITTER_COUNT - 1) - 0.5) * 0.12
        base = [c * scale for c in tint]
        for tri in triangles:
            a, b, c = (vertices[i] for i in tri)
            if max(a[0], b[0], c[0]) < x_range[0] or min(a[0], b[0], c[0]) > x_range[1]:
                continue
            if max(a[1], b[1], c[1]) < y_range[0] or min(a[1], b[1], c[1]) > y_range[1]:
                continue
            ab = [b[i] - a[i] for i in range(3)]
            ac = [c[i] - a[i] for i in range(3)]
            n = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0])
            ln = math.sqrt(sum(v * v for v in n))
            if ln < 1e-9 or n[2] <= 0:
                continue  # back-facing to the orthographic viewer at +z
            lam = max(0.0, sum(n[i] * light[i] for i in range(3)) / ln)
            shade = 0.30 + 0.70 * lam
            color = bytes(int(255 * linear_to_srgb(v * shade)) for v in base)
            pts = [((p[0] - x_range[0]) * px_per_cm, H - (p[1] - y_range[0]) * px_per_cm, p[2]) for p in (a, b, c)]
            (x0, y0, d0), (x1, y1, d1), (x2, y2, d2) = pts
            det = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(det) < 1e-9:
                continue
            ymin = max(0, int(min(y0, y1, y2)))
            ymax = min(H - 1, int(max(y0, y1, y2)) + 1)
            xmin = max(0, int(min(x0, x1, x2)))
            xmax = min(W - 1, int(max(x0, x1, x2)) + 1)
            for y in range(ymin, ymax + 1):
                py = y + 0.5
                for x in range(xmin, xmax + 1):
                    px = x + 0.5
                    w0 = ((y1 - y2) * (px - x2) + (x2 - x1) * (py - y2)) / det
                    w1 = ((y2 - y0) * (px - x2) + (x0 - x2) * (py - y2)) / det
                    w2 = 1 - w0 - w1
                    if w0 < 0 or w1 < 0 or w2 < 0:
                        continue
                    depth = w0 * d0 + w1 * d1 + w2 * d2
                    idx = y * W + x
                    if depth > zbuf[idx]:
                        zbuf[idx] = depth
                        rgb[idx * 3:idx * 3 + 3] = color

    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    scan = b''.join(b'\x00' + bytes(rgb[y * W * 3:(y + 1) * W * 3]) for y in range(H))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', W, H, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(scan, 6)) + chunk(b'IEND', b''))
    return dict(file=path.name, pixels=[W, H], pxPerCm=px_per_cm, sha256=sha256(path))


# ----------------------------------------------------------------------------------------------

def export():
    if FOLDER.exists() and any(FOLDER.glob('native-import-*.json')):
        raise SystemExit('Refusing to regenerate: native import receipts exist in ' + str(FOLDER))
    FOLDER.mkdir(parents=True, exist_ok=True)
    v1 = json.loads(V1_MANIFEST.read_text(encoding='utf-8'))
    faces = sorted(v1['faces'], key=lambda f: f['a'][1])
    assert [f['edge'] for f in faces] == [24, 25, 0, 1], 'unexpected exposed face set'
    for f, g in zip(faces, faces[1:]):
        assert math.dist(f['b'], g['a']) < 1e-3, 'faces are not contiguous'
    for f in faces:
        t, n = f['tangent'], f['normal']
        assert n[0] < -0.8 and abs(t[0] * n[0] + t[1] * n[1]) < 1e-6 and abs(math.hypot(*t) - 1) < 1e-6
    lo = v1['sourceBase']['boundsCm']['min'][2]
    hi = v1['sourceBase']['boundsCm']['max'][2]
    assert abs(hi - lo - 2000) < 1e-3
    assert sum(h for g in COURSES for h in g['heights']) == 2000
    tints, tint_stats = photo_reference_tints()
    mortar = tuple(round(v * 0.42, 4) for v in tints[3])
    rng = random.Random(SEED)
    meshes = []
    face_records = []
    total_triangles = 0
    total_blocks = 0
    preview_parts = None
    for face in faces:
        t, n, a = face['tangent'], face['normal'], face['a']
        det = t[0] * n[1] - t[1] * n[0]   # basis (tangent, up, normal) handedness in UE numbers
        blocks = layout_face(face, rng, lo, hi)

        def to_world(p):
            x, y, z = p
            return (a[0] + t[0] * x + n[0] * z, a[1] + t[1] * x + n[1] * z, y)

        def fix(tris):
            return tris if det > 0 else [(i, k, j) for i, j, k in tris]

        parts_world = []
        parts_local = []
        # mortar bed: closed slab over the whole face at +1..+2 cm
        length = face['lengthCm']
        bed_v, bed_t = box_mesh(length, hi - lo, BED_FRONT_CM - BED_BACK_CM, length / 2, (lo + hi) / 2, (BED_BACK_CM + BED_FRONT_CM) / 2)
        closed, vol = check_closed(bed_v, bed_t)
        assert closed and vol > 0
        parts_local.append((bed_v, bed_t, MORTAR_TINT_INDEX, 0))
        parts_world.append(([to_world(p) for p in bed_v], fix(bed_t), MORTAR_TINT_INDEX, 0, 5000.0))
        block_rows = []
        volumes = []
        for blk in blocks:
            w = blk['width'] - JOINT_CM
            h = blk['height'] - JOINT_CM
            cx = blk['along'] + blk['width'] / 2
            cy = blk['z'] + blk['height'] / 2
            z_margin = BED_FRONT_CM + JOINT_CM + blk['proud']
            bump = 0.45 if blk['kind'] == 'herodian' else 0.3
            lv, lt = block_mesh(w, h, BLOCK_BACK_CM, z_margin, blk['margin'], blk['boss'], blk['chamfer'], blk['cap'], blk['tilt'], rng, bump)
            closed, vol = check_closed(lv, lt)
            assert closed and vol > 0, ('block not closed/outward', face['edge'], blk['course'])
            volumes.append(vol)
            lv = [(p[0] + cx, p[1] + cy, p[2]) for p in lv]
            parts_local.append((lv, lt, blk['tint'], blk['jitter']))
            parts_world.append(([to_world(p) for p in lv], fix(lt), blk['tint'], blk['jitter'], 100.0))
            block_rows.append(dict(course=blk['course'], kind=blk['kind'], alongCm=round(blk['along'], 3), widthCm=round(blk['width'], 3),
                                   zCm=round(blk['z'], 3), heightCm=blk['height'], proudCm=round(blk['proud'], 3), marginCm=round(blk['margin'], 2),
                                   bossCm=round(blk['boss'], 2), tint=blk['tint'], jitter=blk['jitter'], triangles=len(lt)))
        name = 'SM_KotelAshlarV2_E%d' % face['edge']
        record = write_obj(FOLDER / (name + '.obj'), name, parts_world)
        record.update(edge=face['edge'], blocks=len(blocks), closedParts=len(blocks) + 1, allPartsClosedOutward=True,
                      blockVolumeCm3=dict(min=round(min(volumes), 1), max=round(max(volumes), 1)),
                      maxFrontCm=round(max(p[2] for part in parts_local for p in part[0]), 3))
        meshes.append(record)
        total_triangles += record['triangles']
        total_blocks += len(blocks)
        face_records.append(dict(edge=face['edge'], a=face['a'], b=face['b'], tangent=t, normal=n, lengthCm=face['lengthCm'],
                                 basisDeterminant=det, blocks=block_rows))
        if face['edge'] == 0:
            preview_parts = parts_local
    assert total_triangles < TRIANGLE_BUDGET, total_triangles
    light = (-0.80, 0.30, 0.52)   # raking from the upper left along the face
    previews = [
        render_preview(FOLDER / 'preview-elevation-edge0.png', preview_parts, tints, (0.0, faces[2]['lengthCm']), (lo, hi), 0.6, light),
        render_preview(FOLDER / 'preview-detail-edge0.png', preview_parts, tints, (400.0, 1200.0), (lo, lo + 500.0), 3.0, light),
    ]
    schedule = [dict(kind=g['kind'], courses=len(g['heights']), heightsCm=g['heights'], stoneLengthsCm=list(g['lengths']),
                     marginCm=list(g['margin']), bossCm=list(g['boss']), chamferCm=list(g['chamfer']), capGrid=g['cap']) for g in COURSES]
    manifest = dict(
        status='EXPORTED_NATIVE_PENDING', namespace=NAMESPACE, generator='Scripts/create_kotel_stone_v2.py', seed=SEED,
        sourceManifest=V1_MANIFEST.relative_to(ROOT).as_posix(), sourceManifestSha256=sha256(V1_MANIFEST),
        wallBaseZCm=lo, wallTopZCm=hi, courseCount=sum(len(g['heights']) for g in COURSES), courseSchedule=schedule,
        jointCm=JOINT_CM, bedCm=[BED_BACK_CM, BED_FRONT_CM], blockBackCm=BLOCK_BACK_CM, proudRangeCm=[0.0, PROUD_MAX_CM],
        tiltMaxSlope=TILT_MAX, totalBlocks=total_blocks, totalTriangles=total_triangles, triangleBudget=TRIANGLE_BUDGET,
        tintsLinear=[list(t) for t in tints], mortarTintLinear=list(mortar), tintReference=tint_stats,
        uvEncoding=dict(stride=UV_STRIDE, u='stride*tintIndex + planar local u (0..3.3)', v='stride*jitterIndex + planar local v (0..1.3)',
                        tintIndices=TINT_COUNT, jitterIndices=JITTER_COUNT, mortarTintIndex=MORTAR_TINT_INDEX,
                        decode='tint=floor(u/8); jitter=floor(q/8) with q=(v<0.5? 1-v : v) so a V flip on import decodes identically'),
        meshes=meshes, faces=face_records, previews=previews,
        convention='Canonical UE XYZ cm, algebraic outward winding cross(B-A,C-A); OBJ reflects Y and reverses winding for the legacy importer (KotelStoneV1/DoorsParochesV1 adapter). Every block and bed is a closed edge-manifold with positive signed volume.',
        placement='Identity transform (world-baked); NoCollision; base wall keeps collision. Bed starts 1 cm in front of the source face.',
        interpretation='Authored ashlar study with plausible Herodian/medieval/late course proportions; not a stone-by-stone survey of the present Kotel and no claim about the future wall.',
        limitations=['Course heights and stone lengths are randomised within period ranges, not surveyed',
                     'Plaza Z taken from the source model base (-1399.695); native ground review pending',
                     'Faces meet at footprint bends with sub-cm wedge gaps; visual inspection pending',
                     'No LOD/Nanite decision; ~%d triangles across four actors' % total_triangles,
                     'Software preview uses flat tints and a synthetic raking light, not the native material'])
    (FOLDER / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return {k: manifest[k] for k in ('status', 'totalBlocks', 'totalTriangles', 'courseCount')} | dict(
        meshes=[(m['name'], m['triangles'], m['blocks']) for m in meshes], previews=[p['file'] for p in previews])


if __name__ == '__main__':
    print(json.dumps(export(), indent=2))
    sys.exit(0)
