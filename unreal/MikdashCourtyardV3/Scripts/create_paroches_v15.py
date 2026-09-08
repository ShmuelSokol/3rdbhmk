"""ParochesV15: the approved V15 paroches artwork as a hanging cloth panel (offline creator).

Offline only. Writes SourceAssets/sanctuary-detail/ParochesV15/:
  third-temple-handwoven-v15.png          frozen copy of the APPROVED artwork (hash-checked)
  third-temple-handwoven-v15_normal.png   AUTHORED soft fabric normal (from luminance, low amplitude)
  SM_ParochesV15_Cloth_50.obj / _48.obj   350 x 300 cm / 336 x 288 cm hanging panel
  SM_ParochesV15_Fixings_50.obj / _48.obj rod, rings, brackets, finials (authored fixings)
  geometry-manifest.json                  hashes, triangles, bounds, volumes, drape/normal parameters
No engine launch, no Content/ change, no map action. Native import and placement live in
Scripts/release_paroches_v15.py.

APPROVAL
  The ONLY artwork this creator accepts is the user-approved V15 PNG, SHA-256
  f48ccf055c8f051ccf9bc2702c003d84d1b74eeda54231d2be9ced157232df89 (HANDOFF-FOR-FABLE-20260908.md,
  "Approved paroches"). Any other hash refuses. Earlier V1/V7/V9 candidates are held and never read.

SIZE (7 x 6 amot; SourceAssets/research/book-scene-requirements-20260907.md pp. 184-186:
  "entrance 7 wide x 6 high ... paroches exactly the size of the gate", Yechezkel 41:3,
  Mishkenei Elyon 159-166; Lishchno Tidreshu pp. 59-60 "paroches the size of the gate on the Heichal side")
  48 cm amah -> 336 x 288 cm (the handoff figure; agrees)      50 cm amah (current main) -> 350 x 300 cm

SOURCED vs AUTHORED: see SourceAssets/sanctuary-detail/ParochesV15/sources.md. Everything numeric in
the drape, the rings, the rod and the normal map below is an artistic choice.

Conventions: centimetres. Mesh-local canonical axes: +X across the width (image right), +Z up,
+Y toward the viewer (front face). Pivot at the bottom centre of the hanging plane (rod plane y = 0).
Placed with yaw -90 the local +X becomes world -Y (north, the east-facing viewer's right) and local +Y
becomes world +X (east, into the Heichal). OBJ files are written for the legacy Unreal OBJ importer
adapter proven on this project (Y reflected, triangle winding reversed; the importer reflects Y back),
same as create_keilim_ti_v1 / create_sanctuary_doors. Vertices are shared and carry smooth normals and
ONE whole-panel UV chart (u = arc length across the cloth 0..1, v = height 0..1 with v = 1 at the top,
so the importer's V flip puts image row 0 at the cloth top).
"""
import argparse
import hashlib
import json
import math
import shutil
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/sanctuary-detail/ParochesV15'
APPROVED_SOURCE = Path(r'C:\Users\shmue\Documents\Codex\2026-09-08\what-color-is-the-paroches-of\output\paroches\third-temple-handwoven-v15.png')
APPROVED_SHA256 = 'f48ccf055c8f051ccf9bc2702c003d84d1b74eeda54231d2be9ced157232df89'
APPROVED_NAME = 'third-temple-handwoven-v15.png'
NORMAL_NAME = 'third-temple-handwoven-v15_normal.png'

AMOT_WIDE, AMOT_HIGH = 7, 6           # Yechezkel 41:3 gate; paroches exactly the size of the gate
TARGETS = {
    '50': dict(amahCm=50.0, note='current main map (legacy 50 cm architecture)'),
    '48': dict(amahCm=48.0, note='approved 48 cm amah (isolated candidate map)'),
}

# ---- authored drape / fixings parameters (artistic choices, not sourced) -------------------
DRAPE = dict(
    folds=6,                      # S-curves between 7 rings, one full sine period per ring spacing
    amplitudeTopCm=4.0,           # +-4 cm at the rod, where the rings set the folds
    amplitudeBottomCm=2.0,        # softened by the hem weight
    irregularityCm=0.8,           # second, incommensurate sine so the folds are not machine-perfect
    irregularityCycles=2.5,
    irregularityPhase=0.7,
    thicknessCm=0.8,              # closed slab: front sheet, back sheet, rim
    gridX=60, gridZ=40,           # 10 columns per fold
)
FIXINGS = dict(
    rodRadiusCm=1.75, rodOverhangCm=10.0, rodAboveClothCm=5.5,
    ringMajorCm=5.0, ringMinorCm=0.6, ringSegments=(20, 8),
    bracketSizeCm=(3.0, 12.25, 3.5), standoffCm=12.0,   # bracket runs from the rod plane back into the wall face
    finialRadiusCm=3.0,
    material_role='gold',
)
NORMAL = dict(
    highPassRadiusPx=3,           # luma minus a 7x7 box blur: yarn structure, not the colour fields
    slopeScale=2.5,               # tangent-space tilt per unit high-passed luma gradient (low amplitude)
    maxTilt=0.35,
    convention='DirectX (green = -V, image down); import with flip_green_channel False',
)


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# =====================================================================================
# 1. Geometry helpers (canonical, closed, outward-wound)
# =====================================================================================
def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def volume(v, f):
    t = 0.0
    for a, b, c in f:
        p, q, r = v[a], v[b], v[c]
        n = cross([q[i] - p[i] for i in range(3)], [r[i] - p[i] for i in range(3)])
        t += sum(p[i] * n[i] for i in range(3))
    return t / 6.0


def orient(v, f):
    return (v, f) if volume(v, f) > 0 else (v, [(a, c, b) for a, b, c in f])


def closed(v, f):
    keys = [tuple(round(x, 6) for x in p) for p in v]
    e = {}
    for a, b, c in f:
        for i, j in ((a, b), (b, c), (c, a)):
            k = tuple(sorted((keys[i], keys[j])))
            e[k] = e.get(k, 0) + 1
    return all(n == 2 for n in e.values())


def normalize(n):
    l = math.sqrt(sum(x * x for x in n))
    return [x / l for x in n]


def box(center, size):
    cx, cy, cz = center
    hx, hy, hz = [s / 2.0 for s in size]
    v = [(cx + sx * hx, cy + sy * hy, cz + sz * hz) for sz in (-1, 1) for sy in (-1, 1) for sx in (-1, 1)]
    f = [(0, 2, 3), (0, 3, 1), (4, 5, 7), (4, 7, 6), (0, 1, 5), (0, 5, 4), (2, 6, 7), (2, 7, 3), (0, 4, 6), (0, 6, 2), (1, 3, 7), (1, 7, 5)]
    return orient(v, f)


def _grid_faces(rows, cols, wrap_rows=False, wrap_cols=False):
    faces = []
    r_n = rows if wrap_rows else rows - 1
    c_n = cols if wrap_cols else cols - 1
    for i in range(r_n):
        i1 = (i + 1) % rows
        for j in range(c_n):
            j1 = (j + 1) % cols
            a, b, c, d = i * cols + j, i * cols + j1, i1 * cols + j1, i1 * cols + j
            faces.append((a, b, c))
            faces.append((a, c, d))
    return faces


def torus_x(center, major, minor, sm, sn):
    """Torus whose axis is +X (ring plane = YZ)."""
    cx, cy, cz = center
    v = []
    for i in range(sm):
        u = 2 * math.pi * i / sm
        ry, rz = math.cos(u), math.sin(u)
        for j in range(sn):
            w = 2 * math.pi * j / sn
            r = major + minor * math.cos(w)
            v.append((cx + minor * math.sin(w), cy + r * ry, cz + r * rz))
    return orient(v, _grid_faces(sm, sn, True, True))


def cylinder_x(x0, x1, cy, cz, radius, segments=16):
    v = []
    for x in (x0, x1):
        for j in range(segments):
            w = 2 * math.pi * j / segments
            v.append((x, cy + radius * math.cos(w), cz + radius * math.sin(w)))
    faces = _grid_faces(2, segments, False, True)
    c0, c1 = len(v), len(v) + 1
    v.append((x0, cy, cz))
    v.append((x1, cy, cz))
    for j in range(segments):
        j1 = (j + 1) % segments
        faces.append((c0, j1, j))
        faces.append((c1, segments + j, segments + j1))
    return orient(v, faces)


def sphere(center, r, sm=10, sn=6):
    cx, cy, cz = center
    v = [(cx, cy, cz + r)]
    for i in range(1, sn):
        t = math.pi * i / sn
        for j in range(sm):
            p = 2 * math.pi * j / sm
            v.append((cx + r * math.sin(t) * math.cos(p), cy + r * math.sin(t) * math.sin(p), cz + r * math.cos(t)))
    v.append((cx, cy, cz - r))
    faces = []
    for j in range(sm):
        faces.append((0, 1 + j, 1 + (j + 1) % sm))
    for i in range(sn - 2):
        for j in range(sm):
            a = 1 + i * sm + j
            b = 1 + i * sm + (j + 1) % sm
            faces.append((a, a + sm, b + sm))
            faces.append((a, b + sm, b))
    last = len(v) - 1
    base = 1 + (sn - 2) * sm
    for j in range(sm):
        faces.append((last, base + (j + 1) % sm, base + j))
    return orient(v, faces)


# =====================================================================================
# 2. The cloth panel
# =====================================================================================
def drape(x, z, W, H):
    """Displacement of the cloth mid-plane toward the viewer (+Y) at (x, z). Authored."""
    d = DRAPE
    amp = d['amplitudeBottomCm'] + (d['amplitudeTopCm'] - d['amplitudeBottomCm']) * (z / H)
    lam = W / d['folds']
    s = (x + W / 2.0)
    main = amp * math.sin(2 * math.pi * s / lam)
    irregular = d['irregularityCm'] * (z / H) * math.sin(2 * math.pi * s * d['irregularityCycles'] / W + d['irregularityPhase'])
    return main + irregular


def drape_gradient(x, z, W, H, eps=0.05):
    dx = (drape(x + eps, z, W, H) - drape(x - eps, z, W, H)) / (2 * eps)
    dz = (drape(x, min(H, z + eps), W, H) - drape(x, max(0.0, z - eps), W, H)) / (min(H, z + eps) - max(0.0, z - eps))
    return dx, dz


def ring_positions(W):
    lam = W / DRAPE['folds']
    return [round(-W / 2.0 + i * lam, 6) for i in range(DRAPE['folds'] + 1)]


def cloth_geometry(W, H):
    """Returns dict(vertices, normals, uvs, faces_v, faces_n) in canonical space; closed slab."""
    nx, nz = DRAPE['gridX'], DRAPE['gridZ']
    t = DRAPE['thicknessCm']
    cols, rows = nx + 1, nz + 1
    positions_mid, grads = [], []
    for i in range(rows):
        z = H * i / nz
        for j in range(cols):
            x = -W / 2.0 + W * j / nx
            positions_mid.append((x, z, drape(x, z, W, H)))
            grads.append(drape_gradient(x, z, W, H))
    # arc-length u per row (whole panel 0..1), v = z / H
    uvs_row = []
    for i in range(rows):
        s = [0.0]
        for j in range(1, cols):
            x0, z0, y0 = positions_mid[i * cols + j - 1]
            x1, z1, y1 = positions_mid[i * cols + j]
            s.append(s[-1] + math.hypot(x1 - x0, y1 - y0))
        total = s[-1]
        uvs_row.append([(sj / total, positions_mid[i * cols][1] / H) for sj in s])
    verts, normals, uvs = [], [], []
    # front sheet (index 0 .. rows*cols-1) then back sheet
    for sheet, sign in (('front', 1.0), ('back', -1.0)):
        for i in range(rows):
            for j in range(cols):
                x, z, d = positions_mid[i * cols + j]
                gx, gz = grads[i * cols + j]
                verts.append((x, d + sign * t / 2.0, z))
                normals.append(normalize([-gx * sign, sign, -gz * sign]))
                uvs.append(uvs_row[i][j])
    n_sheet = rows * cols
    faces = []
    front = _grid_faces(rows, cols)
    # front sheet must face +Y: grid faces (a,b,c) with a=(i,j), b=(i,j+1), c=(i+1,j+1): (b-a) x (c-a) ~ +X x +Z = -Y -> reverse
    faces.extend([(a, c, b) for a, b, c in front])
    faces.extend([(a + n_sheet, b + n_sheet, c + n_sheet) for a, b, c in front])
    face_normals = [None] * len(faces)          # None = use per-vertex smooth normals
    # rim: bottom (i=0), top (i=rows-1), left (j=0), right (j=cols-1); flat normals
    rim_normal_index = {}

    def rim_n(vec):
        key = tuple(round(x, 6) for x in vec)
        if key not in rim_normal_index:
            rim_normal_index[key] = len(normals)
            normals.append(list(key))
        return rim_normal_index[key]

    def quad(f0, f1, b1, b0, nvec):
        # f0,f1 on the front sheet, b0,b1 the matching back vertices; wound to face nvec
        for tri in ((f0, f1, b1), (f0, b1, b0)):
            p, q, r = verts[tri[0]], verts[tri[1]], verts[tri[2]]
            n = cross([q[k] - p[k] for k in range(3)], [r[k] - p[k] for k in range(3)])
            if sum(n[k] * nvec[k] for k in range(3)) < 0:
                tri = (tri[0], tri[2], tri[1])
            faces.append(tri)
            face_normals.append(rim_n(nvec))

    for j in range(cols - 1):                       # bottom edge, normal -Z
        f0, f1 = j, j + 1
        quad(f0, f1, f1 + n_sheet, f0 + n_sheet, (0.0, 0.0, -1.0))
    for j in range(cols - 1):                       # top edge, normal +Z
        f0, f1 = (rows - 1) * cols + j, (rows - 1) * cols + j + 1
        quad(f0, f1, f1 + n_sheet, f0 + n_sheet, (0.0, 0.0, 1.0))
    for i in range(rows - 1):                       # left edge x = -W/2, normal -X
        f0, f1 = i * cols, (i + 1) * cols
        quad(f0, f1, f1 + n_sheet, f0 + n_sheet, (-1.0, 0.0, 0.0))
    for i in range(rows - 1):                       # right edge, normal +X
        f0, f1 = i * cols + cols - 1, (i + 1) * cols + cols - 1
        quad(f0, f1, f1 + n_sheet, f0 + n_sheet, (1.0, 0.0, 0.0))
    vol = volume(verts, faces)
    assert vol > 0, 'cloth slab inverted'
    assert abs(vol - W * H * t) < 1e-6 * W * H * t, 'cloth slab volume %.4f != W*H*t %.4f (mixed winding)' % (vol, W * H * t)
    assert closed(verts, faces), 'cloth slab not closed'
    return dict(vertices=verts, normals=normals, uvs=uvs, faces=faces, face_normals=face_normals,
                expected_volume=W * H * t)


def fixings_parts(W, H):
    f = FIXINGS
    z_rod = H + f['rodAboveClothCm']
    half = W / 2.0 + f['rodOverhangCm']
    parts = [('rod', cylinder_x(-half, half, 0.0, z_rod, f['rodRadiusCm']))]
    for k, x in enumerate(ring_positions(W)):
        parts.append(('ring_%d' % k, torus_x((x, 0.0, z_rod), f['ringMajorCm'], f['ringMinorCm'], *f['ringSegments'])))
    bx, by, bz = f['bracketSizeCm']
    for side in (-1, 1):
        x = side * (W / 2.0 + f['rodOverhangCm'] - 2.0)
        parts.append(('bracket_%s' % ('n' if side < 0 else 's'), box((x, -by / 2.0, z_rod), (bx, by, bz))))
        parts.append(('finial_%s' % ('n' if side < 0 else 's'), sphere((side * half, 0.0, z_rod), f['finialRadiusCm'])))
    return parts


# =====================================================================================
# 3. OBJ writers (legacy adapter: Y reflected, winding reversed)
# =====================================================================================
def write_cloth_obj(name, geo, path):
    v, n, uv, faces, fn = geo['vertices'], geo['normals'], geo['uvs'], geo['faces'], geo['face_normals']
    lines = ['# ParochesV15 %s; Unreal legacy OBJ adapter (Y reflected, winding reversed); whole-panel UV chart' % name, 'o ' + name, 'g cloth']
    for x, y, z in v:
        lines.append('v %.6f %.6f %.6f' % (x, -y, z))
    for u_, v_ in uv:
        lines.append('vt %.6f %.6f' % (u_, v_))
    for nx_, ny_, nz_ in n:
        lines.append('vn %.6f %.6f %.6f' % (nx_, -ny_, nz_))
    n_uv = len(uv)
    for (a, b, c), fnormal in zip(faces, fn):
        # reversed winding: (a, c, b); uv index = vertex index (both sheets carry their own uvs); rim uses flat normals
        corners = []
        for idx in (a, c, b):
            ni = idx if fnormal is None else fnormal
            ti = idx if idx < n_uv else (idx % n_uv)
            corners.append('%d/%d/%d' % (idx + 1, ti + 1, ni + 1))
        lines.append('f ' + ' '.join(corners))
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    bounds = {k: [fn_(p[i] for p in v) for i in range(3)] for k, fn_ in (('min', min), ('max', max))}
    vol = volume(v, faces)
    return dict(name=name, file=path.name, sha256=sha256_of(path), triangles=len(faces), parts=1,
                material_role='paroches_v15_fabric', bounds_cm=bounds, uv_range=[[0.0, 1.0], [0.0, 1.0]],
                part_volume_sum_cm3=round(vol, 4), expected_volume_cm3=round(geo['expected_volume'], 4),
                closed=True, vertices=len(v))


def write_parts_obj(name, parts, path, role):
    lines = ['# ParochesV15 %s; Unreal legacy OBJ adapter (Y reflected, winding reversed)' % name, 'o ' + name]
    index = 1
    allv = []
    vol_sum = 0.0
    for part, (vertices, faces) in parts:
        vol = volume(vertices, faces)
        assert vol > 0, 'inverted part ' + part
        assert closed(vertices, faces), 'open part ' + part
        vol_sum += vol
        allv.extend(vertices)
        lines.append('g ' + part)
        for a, b, c in faces:
            p, q, r = [(vertices[i][0], -vertices[i][1], vertices[i][2]) for i in (a, c, b)]
            ab = [q[i] - p[i] for i in range(3)]
            ac = [r[i] - p[i] for i in range(3)]
            n = cross(ab, ac)
            length = math.sqrt(sum(x * x for x in ab))
            nl = math.sqrt(sum(x * x for x in n))
            assert nl > 1e-8 and length > 1e-8, 'degenerate triangle in ' + part
            for vv in (p, q, r):
                lines.append('v %.6f %.6f %.6f' % vv)
            for uv in ((0, 0), (length / 10, 0), (sum(ac[i] * ab[i] / length for i in range(3)) / 10, nl / length / 10)):
                lines.append('vt %.6f %.6f' % uv)
            for _ in range(3):
                lines.append('vn %.6f %.6f %.6f' % tuple(x / nl for x in n))
            lines.append('f ' + ' '.join('%d/%d/%d' % (k, k, k) for k in range(index, index + 3)))
            index += 3
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    bounds = {k: [fn_(p[i] for p in allv) for i in range(3)] for k, fn_ in (('min', min), ('max', max))}
    return dict(name=name, file=path.name, sha256=sha256_of(path), triangles=(index - 1) // 3, parts=len(parts),
                material_role=role, bounds_cm=bounds, part_volume_sum_cm3=round(vol_sum, 4), closed=True)


def readback(path, record):
    """Independent parse of the written OBJ: normals agree with winding, bounds equal, file-space volume positive."""
    verts, normals, faces = [], [], []
    for line in path.read_text().splitlines():
        c = line.split()
        if not c:
            continue
        if c[0] == 'v':
            verts.append(tuple(map(float, c[1:])))
        elif c[0] == 'vn':
            normals.append(tuple(map(float, c[1:])))
        elif c[0] == 'f':
            faces.append([tuple(int(x) - 1 for x in t.split('/')) for t in c[1:]])
    assert len(faces) == record['triangles'], (len(faces), record['triangles'])
    worst = 0.0
    for face in faces:
        assert len(face) == 3
        a, b, c = [verts[t[0]] for t in face]
        ab = [b[i] - a[i] for i in range(3)]
        ac = [c[i] - a[i] for i in range(3)]
        cr = cross(ab, ac)
        area = math.sqrt(sum(x * x for x in cr))
        assert area > 1e-9
        # smooth-shaded corners may lean away from the face normal on the drape; require the same hemisphere
        for corner in face:
            dot = sum(cr[i] * normals[corner[2]][i] for i in range(3)) / area
            worst = max(worst, 1.0 - dot)
            assert dot > 0.0, 'vertex normal opposes face winding in ' + path.name
    canonical = [(x, -y, z) for x, y, z in verts]
    bounds = {k: [fn_(v[i] for v in canonical) for i in range(3)] for k, fn_ in (('min', min), ('max', max))}
    err = max(abs(bounds[k][i] - record['bounds_cm'][k][i]) for k in bounds for i in range(3))
    assert err < 1e-4, err
    fv = volume(verts, [tuple(t[0] for t in face) for face in faces])
    assert fv > 0, 'adapter sign unexpected for ' + path.name
    assert abs(fv - record['part_volume_sum_cm3']) / record['part_volume_sum_cm3'] < 1e-6
    return dict(mesh=record['name'], triangles=len(faces), bounds_error_cm=round(err, 9),
                worst_normal_deviation=round(worst, 6), file_space_signed_volume_cm3=round(fv, 3), normals_and_winding='PASS')


# =====================================================================================
# 4. PNG codec (pure Python; the bundled UE python has no PIL/numpy)
# =====================================================================================
def decode_png(path):
    data = Path(path).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', 'not a PNG'
    pos, chunks, idat = 8, {}, []
    while pos < len(data):
        length = struct.unpack('!I', data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b'IHDR':
            chunks['ihdr'] = struct.unpack('!2I5B', body)
        elif kind == b'IDAT':
            idat.append(body)
        elif kind == b'IEND':
            break
    W, H, depth, ctype, _, _, interlace = chunks['ihdr']
    assert depth == 8 and interlace == 0 and ctype in (2, 6), 'expected 8-bit RGB/RGBA non-interlaced PNG, got depth %d type %d' % (depth, ctype)
    ch = 3 if ctype == 2 else 4
    raw = zlib.decompress(b''.join(idat))
    stride = W * ch
    rows, prev = [], bytearray(stride)
    p = 0
    for _ in range(H):
        ftype = raw[p]
        cur = bytearray(raw[p + 1:p + 1 + stride])
        p += 1 + stride
        if ftype == 1:
            for i in range(ch, stride):
                cur[i] = (cur[i] + cur[i - ch]) & 255
        elif ftype == 2:
            for i in range(stride):
                cur[i] = (cur[i] + prev[i]) & 255
        elif ftype == 3:
            for i in range(stride):
                left = cur[i - ch] if i >= ch else 0
                cur[i] = (cur[i] + ((left + prev[i]) >> 1)) & 255
        elif ftype == 4:
            for i in range(stride):
                a = cur[i - ch] if i >= ch else 0
                b = prev[i]
                c = prev[i - ch] if i >= ch else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur[i] = (cur[i] + pred) & 255
        rows.append(bytes(cur))
        prev = cur
    return dict(width=W, height=H, channels=ch, rows=rows)


def encode_png_rgb(path, W, H, rows):
    def chunk(kind, body):
        return struct.pack('!I', len(body)) + kind + body + struct.pack('!I', zlib.crc32(kind + body) & 0xffffffff)
    scan = b''.join(b'\x00' + r for r in rows)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', W, H, 8, 2, 0, 0, 0))
                           + chunk(b'IDAT', zlib.compress(scan, 9)) + chunk(b'IEND', b''))
    return sha256_of(path)


def luma_rows(img):
    W, ch = img['width'], img['channels']
    out = []
    for row in img['rows']:
        out.append([(0.299 * row[i] + 0.587 * row[i + 1] + 0.114 * row[i + 2]) / 255.0 for i in range(0, W * ch, ch)])
    return out


def box_blur(rows, radius):
    """Separable box blur with edge clamping (prefix sums)."""
    H, W = len(rows), len(rows[0])
    k = 2 * radius + 1
    tmp = []
    for row in rows:
        pre = [0.0]
        for v in row:
            pre.append(pre[-1] + v)
        out = []
        for x in range(W):
            lo, hi = max(0, x - radius), min(W - 1, x + radius)
            out.append((pre[hi + 1] - pre[lo]) / (hi - lo + 1))
        tmp.append(out)
    cols = list(zip(*tmp))
    res = [[0.0] * W for _ in range(H)]
    for x in range(W):
        col = cols[x]
        pre = [0.0]
        for v in col:
            pre.append(pre[-1] + v)
        for y in range(H):
            lo, hi = max(0, y - radius), min(H - 1, y + radius)
            res[y][x] = (pre[hi + 1] - pre[lo]) / (hi - lo + 1)
    del k
    return res


def fabric_normal(img):
    """AUTHORED soft fabric normal from the artwork's luminance (high-passed), DirectX green, low amplitude."""
    luma = luma_rows(img)
    blurred = box_blur(luma, NORMAL['highPassRadiusPx'])
    H, W = len(luma), len(luma[0])
    hp = [[luma[y][x] - blurred[y][x] for x in range(W)] for y in range(H)]
    del blurred
    k, cap = NORMAL['slopeScale'], NORMAL['maxTilt']
    rows = []
    stats = dict(maxAbsHighPass=0.0, meanAbsTiltX=0.0, meanAbsTiltY=0.0)
    acc_x = acc_y = 0.0
    for y in range(H):
        up, dn, cur = hp[max(0, y - 1)], hp[min(H - 1, y + 1)], hp[y]
        row = bytearray(W * 3)
        for x in range(W):
            dx = (cur[min(W - 1, x + 1)] - cur[max(0, x - 1)]) * 0.5
            dy = (dn[x] - up[x]) * 0.5
            nx_ = max(-cap, min(cap, -k * dx))
            ny_ = max(-cap, min(cap, -k * dy))          # DirectX: green follows image-down gradient sign
            nz_ = math.sqrt(max(1e-6, 1.0 - nx_ * nx_ - ny_ * ny_))
            row[3 * x] = int(round((nx_ + 1.0) * 127.5))
            row[3 * x + 1] = int(round((ny_ + 1.0) * 127.5))
            row[3 * x + 2] = int(round((nz_ + 1.0) * 127.5))
            acc_x += abs(nx_)
            acc_y += abs(ny_)
            if abs(cur[x]) > stats['maxAbsHighPass']:
                stats['maxAbsHighPass'] = abs(cur[x])
        rows.append(bytes(row))
    stats['meanAbsTiltX'] = acc_x / (W * H)
    stats['meanAbsTiltY'] = acc_y / (W * H)
    return rows, stats


def is_power_of_two(n):
    return n > 0 and (n & (n - 1)) == 0


# =====================================================================================
# 5. Export
# =====================================================================================
def target_size(amah_cm):
    return AMOT_WIDE * amah_cm, AMOT_HIGH * amah_cm


def export(force=False, skip_normal=False):
    manifest_path = OUT / 'geometry-manifest.json'
    if manifest_path.exists() and not force:
        raise SystemExit('Refusing to regenerate: %s exists (use --force to overwrite the offline source set)' % manifest_path)
    if not APPROVED_SOURCE.exists():
        raise SystemExit('Approved artwork missing: %s' % APPROVED_SOURCE)
    source_sha = sha256_of(APPROVED_SOURCE)
    if source_sha != APPROVED_SHA256:
        raise SystemExit('Approved artwork hash mismatch: %s != %s. STOP: not the approved V15.' % (source_sha, APPROVED_SHA256))
    OUT.mkdir(parents=True, exist_ok=True)
    frozen = OUT / APPROVED_NAME
    if not frozen.exists() or sha256_of(frozen) != APPROVED_SHA256:
        shutil.copy2(APPROVED_SOURCE, frozen)
    assert sha256_of(frozen) == APPROVED_SHA256
    img = decode_png(frozen)
    W_px, H_px = img['width'], img['height']
    image = dict(file=APPROVED_NAME, sha256=APPROVED_SHA256, approvedSource=str(APPROVED_SOURCE), sizePx=[W_px, H_px],
                 channels=img['channels'], aspect=round(W_px / H_px, 6), targetAspect=round(AMOT_WIDE / AMOT_HIGH, 6),
                 aspectErrorPercent=round((W_px / H_px / (AMOT_WIDE / AMOT_HIGH) - 1.0) * 100.0, 3),
                 powerOfTwo=is_power_of_two(W_px) and is_power_of_two(H_px),
                 importNote=('1355 x 1161 is not a power of two: Unreal keeps the source pixels but disables mip maps and '
                             'streaming unless power_of_two_mode is set. release_paroches_v15 sets STRETCH_TO_POWER_OF_TWO '
                             '(-> 2048 x 2048, whole image, UV 0..1 unchanged) so the weave has mips; -ParochesV15KeepNPOT keeps it as-is.'))
    normal = None
    normal_path = OUT / NORMAL_NAME
    if not skip_normal:
        rows, stats = fabric_normal(img)
        sha = encode_png_rgb(normal_path, W_px, H_px, rows)
        normal = dict(file=NORMAL_NAME, sha256=sha, sizePx=[W_px, H_px], authored=True, parameters=NORMAL, stats=stats,
                      rule='normal = normalize(-k * d(hp)/dcol, -k * d(hp)/drow, 1), hp = luma - box7(luma); tilt clamped; DirectX green')
    elif normal_path.exists():
        normal = dict(file=NORMAL_NAME, sha256=sha256_of(normal_path), sizePx=[W_px, H_px], authored=True, parameters=NORMAL, reused=True)
    del img
    meshes, readbacks, targets = [], [], {}
    for key, tcfg in TARGETS.items():
        W, H = target_size(tcfg['amahCm'])
        geo = cloth_geometry(W, H)
        cloth_name = 'SM_ParochesV15_Cloth_%s' % key
        rec = write_cloth_obj(cloth_name, geo, OUT / (cloth_name + '.obj'))
        rec['drape'] = dict(DRAPE, ringXcm=ring_positions(W), midPlaneYRangeCm=[round(rec['bounds_cm']['min'][1], 4), round(rec['bounds_cm']['max'][1], 4)])
        meshes.append(rec)
        readbacks.append(readback(OUT / rec['file'], rec))
        fix_name = 'SM_ParochesV15_Fixings_%s' % key
        rec2 = write_parts_obj(fix_name, fixings_parts(W, H), OUT / (fix_name + '.obj'), FIXINGS['material_role'])
        rec2['fixings'] = dict(FIXINGS, ringXcm=ring_positions(W), rodZcm=H + FIXINGS['rodAboveClothCm'])
        meshes.append(rec2)
        readbacks.append(readback(OUT / rec2['file'], rec2))
        targets[key] = dict(amahCm=tcfg['amahCm'], note=tcfg['note'], widthCm=W, heightCm=H,
                            arithmetic='%d amot x %.0f cm = %.0f cm wide; %d amot x %.0f cm = %.0f cm high' % (AMOT_WIDE, tcfg['amahCm'], W, AMOT_HIGH, tcfg['amahCm'], H),
                            cloth=cloth_name, fixings=fix_name)
    manifest = dict(
        status='OFFLINE_SOURCE_SET_WRITTEN_NATIVE_PENDING',
        creator='Scripts/create_paroches_v15.py', creatorSha256=sha256_of(Path(__file__)),
        approval=dict(approvedPngSha256=APPROVED_SHA256, approvedSource=str(APPROVED_SOURCE),
                      basis='HANDOFF-FOR-FABLE-20260908.md "Approved paroches"; explicit user approval of V15; V1/V7/V9 held'),
        image=image, normal=normal, targets=targets, meshes=meshes, readback=readbacks,
        sizeSource=dict(amot=[AMOT_WIDE, AMOT_HIGH],
                        citation='SourceAssets/research/book-scene-requirements-20260907.md pp. 184-186: KhK entrance 7 wide x 6 high, '
                                 'paroches exactly the size of the gate (Yechezkel 41:3; Mishkenei Elyon 159-166); Lishchno Tidreshu pp. 59-60 '
                                 '(paroches the size of the gate on the Heichal side). 48 cm amah -> 336 x 288 (handoff figure agrees); 50 cm -> 350 x 300.'),
        conventions=dict(
            axes='mesh-local +X across width (image right), +Y toward the viewer (front), +Z up; pivot bottom centre of the rod plane',
            placement='yaw -90: local +X -> world -Y (north = east-facing viewer\'s right), local +Y -> world +X (east, Heichal side)',
            obj='Y reflected and triangle winding reversed for the legacy importer; importer reflects Y back; imported bounds must equal bounds_cm',
            uv='one chart over the whole panel: u = arc length across the cloth 0..1 (image left -> right), v = z/H with v = 1 at the top; '
               'the FBX/OBJ importer maps V_ue = 1 - v_obj so image row 0 lands at the cloth top. Both sheets share the chart (the back reads mirrored, as a woven back does).',
            backFace='closed 0.8 cm slab: the back sheet faces -Y so the panel reads from inside the Kodesh HaKodashim; material is also two-sided',
        ),
        authored=['drape folds and amplitudes', 'ring count/positions, rod, brackets, finials', 'cloth thickness', 'fabric normal map', 'hanging standoff from the wall (release spec)'],
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


def _main():
    parser = argparse.ArgumentParser(description='Offline ParochesV15 source set (OBJ panels, fabric normal, manifest)')
    parser.add_argument('--export', action='store_true')
    parser.add_argument('--force', action='store_true', help='overwrite an existing geometry-manifest.json and its files')
    parser.add_argument('--skip-normal', action='store_true', help='reuse an existing normal PNG (faster re-export of geometry)')
    parser.add_argument('--check-hash', action='store_true', help='only verify the approved artwork hash')
    args = parser.parse_args()
    if args.check_hash:
        ok = APPROVED_SOURCE.exists() and sha256_of(APPROVED_SOURCE) == APPROVED_SHA256
        print(json.dumps(dict(approvedSource=str(APPROVED_SOURCE), exists=APPROVED_SOURCE.exists(), hashMatches=ok), indent=2))
        sys.exit(0 if ok else 2)
    if args.export:
        manifest = export(force=args.force, skip_normal=args.skip_normal)
        print(json.dumps({k: manifest[k] for k in ('status', 'image', 'normal', 'targets', 'readback')}, indent=2))
    else:
        parser.print_help()


if __name__ == '__main__':
    _main()
