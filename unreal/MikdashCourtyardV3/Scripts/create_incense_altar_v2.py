"""Original detailed golden incense altar (mizbach haketoret) study, version 2. Offline only.

    python Scripts/create_incense_altar_v2.py --export     write OBJs + manifest + preview
    python Scripts/create_incense_altar_v2.py --verify     re-read the frozen OBJs, re-render the preview

Replaces the plain-box SM_GoldenIncenseAltarStudy (create_heikhal_keilim.py) with a body that
carries recessed pilaster-framed panels, a projecting crenellated zer, four small corner horns,
two rings with two gold-overlaid carrying poles (east-west, artistic) and a roof slab with a
shallow hearth recess. Two meshes are written so the poles can be handled separately:

    SM_IncenseAltarV2_Body   body, panels, frieze, roof, zer, horns, rings and ring knuckles
    SM_IncenseAltarV2_Poles  two poles with knob ends resting in the rings

Sources (all dimensions in the manifest carry a basis of 'measured' or 'artistic'):
  Shemos 30:1-5  square, one amah by one amah, two amot high, horns of one piece, gold overlay,
                 zer, two rings below the zer on two opposite flanks, poles.
  Lishchno Tidreshu pp. 253-256 (mikdash book/reference-pages/page-253..256.png): the golden
                 altar's amah is five tefachim (p. 255 with Eruvin 4a), so 41.667 x 41.667 x
                 83.333 cm at the project's 8.333 cm tefach. Drawings 24/25 on p. 255 show a
                 tall box with an interlaced knot on each face, a layered crenellated crown,
                 four small corner horns and poles with knob ends passing through side rings.
  Temple Institute photos SourceAssets/reference-ti/incense-altar (dossier.md section 3, reference
                 use only): fluted pilaster strips at both edges of each face, a recessed
                 central panel with a single vertical stem motif, an arch frieze, a pierced
                 crenellated zer rim, four small fluted horns, a plain top with a small hollow.

Geometry helpers follow create_heikhal_keilim.py (bevel_box) and create_sanctuary_doors.py
(closed-part checks, OBJ adapter: canonical Y reflected, winding reversed, per-triangle normals,
non-degenerate UV charts). Every part is a closed solid with positive volume; parts overlap
freely (the same additive convention as the earlier studies). No engine import here.
"""
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/vessels-review/IncenseAltarV2'
DEST = '/Game/MikdashV3/MaterialReview/IncenseAltarV2'
PREVIEW = 'orthographic-preview.png'

TEFACH = 50.0 / 6.0                 # project amah 50 cm = 6 tefachim
AMAH5 = 5 * TEFACH                  # the golden altar's five-tefach amah (book p. 255, Eruvin 4a)
W = AMAH5                           # 41.667 footprint
H_TOTAL = 2 * AMAH5                 # 83.333 to the horn tops
HORN_SIZE = TEFACH / 2              # 4.167 square horn (artistic; book drawing proportion)
Z_ROOF = H_TOTAL - HORN_SIZE        # 79.167 roof top plane (horns counted inside the two amot)
Z_HEARTH = Z_ROOF - TEFACH / 5      # 77.5 hearth recess floor (1.667 deep)
Z_PLATE = 75.0                      # roof plate underside = frieze top
RECESS = TEFACH / 5                 # 1.667 panel recess
CORE = W - 2 * RECESS               # 38.333 recessed core
HALF = W / 2                        # 20.833 outer face plane
POST = 6.0                          # corner pilaster post width (artistic, TI strips)
PLINTH_H = 0.8 * TEFACH             # 6.667 plinth band
FRIEZE_Z0 = Z_PLATE - TEFACH        # 66.667 frieze bottom (one tefach frieze)
ZER_OUT = 1.25                      # zer projection beyond the face plane
ZER_Z0, ZER_Z1 = 77.0, 80.0         # zer band
MERLON_H = 5.0 / 3.0                # 1.667 crenellation
HEARTH = 3 * TEFACH                 # 25.0 hearth recess square
RING_MAJOR, RING_MINOR = 2.6, 0.55
RING_Z = FRIEZE_Z0 + TEFACH / 2     # 70.833 ring/pole axis
RING_Y = HALF + RING_MAJOR + RING_MINOR   # torus tube touches the frieze face
POLE_R, POLE_LEN, KNOB_R = 1.5, 100.0, 2.4


# ---------------------------------------------------------------------------
# closed solids (canonical XYZ Unreal cm, outward winding is enforced by volume sign)
# ---------------------------------------------------------------------------

def bevel_box(center, size, radius=0.4):
    """Six subdivided rounded faces, as create_heikhal_keilim.bevel_box (108 triangles)."""
    half = [v / 2 for v in size]
    assert 0 < radius < min(half), (size, radius)
    vertices, faces = [], []
    for axis in range(3):
        u, v = (axis + 1) % 3, (axis + 2) % 3
        for sign in (-1, 1):
            start = len(vertices)
            for a in (-half[u], -half[u] + radius, half[u] - radius, half[u]):
                for b in (-half[v], -half[v] + radius, half[v] - radius, half[v]):
                    p = [0.0, 0.0, 0.0]
                    p[axis] = sign * half[axis]
                    p[u] = a
                    p[v] = b
                    q = [max(-half[i] + radius, min(half[i] - radius, p[i])) for i in range(3)]
                    d = [p[i] - q[i] for i in range(3)]
                    length = math.sqrt(sum(x * x for x in d))
                    vertices.append(tuple(center[i] + q[i] + d[i] * radius / length for i in range(3)))
            for i in range(3):
                for j in range(3):
                    a = start + i * 4 + j
                    b = a + 4
                    c = b + 1
                    d = a + 1
                    triangles = [(a, b, c), (a, c, d)]
                    faces.extend(triangles if sign == 1 else [(x, z, y) for x, y, z in triangles])
    return vertices, faces


def box(center, size):
    """Plain closed box, 12 triangles (small crenellation blocks)."""
    h = [v / 2 for v in size]
    vertices = [(center[0] + sx * h[0], center[1] + sy * h[1], center[2] + sz * h[2])
                for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    # index = (sx>0)*4 + (sy>0)*2 + (sz>0)
    faces = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5), (0, 4, 5), (0, 5, 1),
             (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return vertices, faces


def cylinder(radius, length, center, axis='z', segments=16):
    """Closed cylinder with fan caps; axis 'x', 'y' or 'z'."""
    ring = []
    for i in range(segments):
        a = i * math.tau / segments
        ring.append((radius * math.cos(a), radius * math.sin(a)))
    vertices = []
    for end in (-length / 2, length / 2):
        for u, v in ring:
            vertices.append(_orient((u, v, end), axis, center))
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.extend([(i, j, segments + j), (i, segments + j, segments + i)])
    for i in range(1, segments - 1):
        faces.extend([(0, i + 1, i), (segments, segments + i, segments + i + 1)])
    return vertices, faces


def torus(center, major, minor, axis='z', segments=24, sides=10):
    """Closed torus; the ring lies in the plane normal to `axis`."""
    vertices = []
    for i in range(segments):
        a = i * math.tau / segments
        for j in range(sides):
            b = j * math.tau / sides
            r = major + minor * math.cos(b)
            vertices.append(_orient((r * math.cos(a), r * math.sin(a), minor * math.sin(b)), axis, center))
    faces = []
    for i in range(segments):
        for j in range(sides):
            a = i * sides + j
            b = ((i + 1) % segments) * sides + j
            c = ((i + 1) % segments) * sides + (j + 1) % sides
            d = i * sides + (j + 1) % sides
            faces.extend([(a, c, b), (a, d, c)])
    return vertices, faces


def sphere(center, radius, segments=16, rings=8):
    """Closed UV sphere with single pole vertices."""
    vertices = [(center[0], center[1], center[2] - radius)]
    for j in range(1, rings):
        phi = -math.pi / 2 + j * math.pi / rings
        for i in range(segments):
            a = i * math.tau / segments
            vertices.append((center[0] + radius * math.cos(phi) * math.cos(a),
                             center[1] + radius * math.cos(phi) * math.sin(a),
                             center[2] + radius * math.sin(phi)))
    vertices.append((center[0], center[1], center[2] + radius))
    top = len(vertices) - 1
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((0, 1 + j, 1 + i))
        base = 1 + (rings - 2) * segments
        faces.append((top, base + i, base + j))
    for r in range(rings - 2):
        for i in range(segments):
            j = (i + 1) % segments
            a = 1 + r * segments + i
            b = 1 + r * segments + j
            c = 1 + (r + 1) * segments + j
            d = 1 + (r + 1) * segments + i
            faces.extend([(a, b, c), (a, c, d)])
    return vertices, faces


def _orient(p, axis, center):
    x, y, z = p
    if axis == 'z':
        q = (x, y, z)
    elif axis == 'x':
        q = (z, x, y)
    elif axis == 'y':
        q = (y, z, x)
    else:
        raise ValueError(axis)
    return (center[0] + q[0], center[1] + q[1], center[2] + q[2])


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def volume(vertices, faces):
    total = 0.0
    for a, b, c in faces:
        p, q, r = vertices[a], vertices[b], vertices[c]
        n = cross([q[i] - p[i] for i in range(3)], [r[i] - p[i] for i in range(3)])
        total += sum(p[i] * n[i] for i in range(3))
    return total / 6.0


def solid(vertices, faces):
    """Outward winding by volume sign; every edge shared by exactly two triangles."""
    if volume(vertices, faces) < 0:
        faces = [(a, c, b) for a, b, c in faces]
    keys = [tuple(round(x, 6) for x in p) for p in vertices]
    edges = {}
    for a, b, c in faces:
        for i, j in ((a, b), (b, c), (c, a)):
            key = tuple(sorted((keys[i], keys[j])))
            edges[key] = edges.get(key, 0) + 1
    assert all(n == 2 for n in edges.values()), 'open or non-manifold part'
    assert volume(vertices, faces) > 0
    return vertices, faces


# ---------------------------------------------------------------------------
# the altar
# ---------------------------------------------------------------------------

def face_frame(face):
    """(normal axis index, sign, tangent axis index) for the four vertical faces."""
    return {'+y': (1, 1, 0), '-y': (1, -1, 0), '+x': (0, 1, 1), '-x': (0, -1, 1)}[face]


def at(face, tangent, depth, z):
    """Point on a vertical face: `depth` measured outward from the altar axis along the face normal."""
    n, sign, t = face_frame(face)
    p = [0.0, 0.0, z]
    p[n] = sign * depth
    p[t] = tangent
    return tuple(p)


def size_on(face, tangent_len, depth_len, height):
    n, _, t = face_frame(face)
    s = [0.0, 0.0, height]
    s[n] = depth_len
    s[t] = tangent_len
    return tuple(s)


def body_parts():
    parts = []
    add = lambda name, geometry: parts.append((name, solid(*geometry)))
    add('Core', bevel_box((0, 0, Z_PLATE / 2), (CORE, CORE, Z_PLATE), 0.5))
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (HALF - POST / 2), sy * (HALF - POST / 2)
            add('Pilaster_%s%s' % ('E' if sx > 0 else 'W', 'S' if sy > 0 else 'N'),
                bevel_box((cx, cy, Z_PLATE / 2), (POST, POST, Z_PLATE), 0.5))
            # Reeded (fluted) pilaster faces: three vertical reeds on each exposed face, half embedded.
            for face in (('+x' if sx > 0 else '-x'), ('+y' if sy > 0 else '-y')):
                n, sign, t = face_frame(face)
                tangent_center = (cy if t == 1 else cx)
                for k, offset in enumerate((-1.7, 0.0, 1.7)):
                    add('Reed_%s_%s%s_%d' % (face, 'E' if sx > 0 else 'W', 'S' if sy > 0 else 'N', k),
                        cylinder(0.45, FRIEZE_Z0 - PLINTH_H - 1.6, at(face, tangent_center + offset, HALF, (FRIEZE_Z0 + PLINTH_H) / 2), 'z', 12))
    panel_len = W - 2 * POST + 1.0
    for face in ('+y', '-y', '+x', '-x'):
        n, sign, t = face_frame(face)
        depth_center = HALF - RECESS / 2
        add('Plinth_' + face, bevel_box(at(face, 0, depth_center, PLINTH_H / 2), size_on(face, panel_len, RECESS, PLINTH_H), 0.4))
        add('Frieze_' + face, bevel_box(at(face, 0, depth_center, (FRIEZE_Z0 + Z_PLATE) / 2), size_on(face, panel_len, RECESS, Z_PLATE - FRIEZE_Z0), 0.4))
        # Arch-frieze stand-ins: four raised discs (TI frieze alternates grape clusters and lilies).
        for k, tangent in enumerate((-11.25, -3.75, 3.75, 11.25)):
            add('FriezeDisc_%s_%d' % (face, k), cylinder(1.5, 0.6, at(face, tangent, HALF + 0.3, (FRIEZE_Z0 + Z_PLATE) / 2), 'xy'[n], 16))
        # Panel motif in the recess (never beyond the face plane): stem, interlaced knot, bud.
        core_face = CORE / 2
        add('Stem_' + face, cylinder(0.55, 44.0, at(face, 0, core_face + 0.3, 36.0), 'z', 12))
        for k, (z, major) in enumerate(((22.0, 3.5), (27.0, 3.5), (44.0, 2.8))):
            add('Knot_%s_%d' % (face, k), torus(at(face, 0, core_face + 0.25, z), major, 0.5, 'xy'[n]))
        add('Bud_' + face, sphere(at(face, 0, core_face + 0.35, 59.5), 1.2))
    # Roof: plate plus a frame leaving a 3 x 3 tefach hearth recess 1.667 deep.
    add('RoofPlate', bevel_box((0, 0, (Z_PLATE + Z_HEARTH) / 2), (W, W, Z_HEARTH - Z_PLATE), 0.4))
    border = (W - HEARTH) / 2
    for sy in (-1, 1):
        add('RoofFrame_%s' % ('S' if sy > 0 else 'N'), bevel_box((0, sy * (HALF - border / 2), (Z_HEARTH + Z_ROOF) / 2), (W, border, Z_ROOF - Z_HEARTH), 0.4))
    for sx in (-1, 1):
        add('RoofFrame_%s' % ('E' if sx > 0 else 'W'), bevel_box((sx * (HALF - border / 2), 0, (Z_HEARTH + Z_ROOF) / 2), (border, HEARTH, Z_ROOF - Z_HEARTH), 0.4))
    # Zer: projecting band with crenellations (closed blocks; a pierced lattice would need thin openings).
    outer = HALF + ZER_OUT
    band_t = ZER_OUT + 0.75
    for face in ('+y', '-y'):
        add('Zer_' + face, bevel_box(at(face, 0, outer - band_t / 2, (ZER_Z0 + ZER_Z1) / 2), size_on(face, 2 * outer, band_t, ZER_Z1 - ZER_Z0), 0.35))
    for face in ('+x', '-x'):
        add('Zer_' + face, bevel_box(at(face, 0, outer - band_t / 2, (ZER_Z0 + ZER_Z1) / 2), size_on(face, 2 * outer - 2 * band_t, band_t, ZER_Z1 - ZER_Z0), 0.35))
    merlon_positions = [-19.5 + 3.0 * k for k in range(14)]
    for face in ('+y', '-y', '+x', '-x'):
        for k, tangent in enumerate(merlon_positions):
            add('Merlon_%s_%02d' % (face, k), box(at(face, tangent, outer - band_t / 2, ZER_Z1 + MERLON_H / 2), size_on(face, 1.6, band_t, MERLON_H)))
    # Four small corner horns rising above the zer to the two-amot line.
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = HALF - HORN_SIZE / 2
            add('Horn_%s%s' % ('E' if sx > 0 else 'W', 'S' if sy > 0 else 'N'),
                bevel_box((sx * c, sy * c, (Z_HEARTH + H_TOTAL) / 2), (HORN_SIZE, HORN_SIZE, H_TOTAL - Z_HEARTH), 0.4))
    # Two rings on the north and south flanks below the zer, with knuckle plates.
    for face in ('+y', '-y'):
        add('Ring_' + face, torus(at(face, 0, RING_Y, RING_Z), RING_MAJOR, RING_MINOR, 'x'))
        add('RingKnuckle_' + face, bevel_box(at(face, 0, HALF + 0.5, RING_Z), size_on(face, 3.0, 1.6, 3.0), 0.3))
    return parts


def pole_parts():
    parts = []
    for face in ('+y', '-y'):
        center = at(face, 0, RING_Y, RING_Z)
        parts.append(('Pole_' + face, solid(*cylinder(POLE_R, POLE_LEN, center, 'x', 24))))
        for sx in (-1, 1):
            parts.append(('Knob_%s_%s' % (face, 'E' if sx > 0 else 'W'),
                          solid(*sphere((center[0] + sx * POLE_LEN / 2, center[1], center[2]), KNOB_R))))
    return parts


def geometry():
    return {'SM_IncenseAltarV2_Body': body_parts(), 'SM_IncenseAltarV2_Poles': pole_parts()}


def dimensions():
    """Dimension table with the basis of every number (cm)."""
    return [
        dict(item='tefach', cm=TEFACH, basis='project convention', source='50 cm amah / 6'),
        dict(item='amah of the golden altar', cm=AMAH5, basis='measured', source='Lishchno Tidreshu p. 255 (Rambam Beit HaBechirah 3:17; Eruvin 4a per Yechezkel 43:13): five tefachim'),
        dict(item='footprint (square)', cm=W, basis='measured', source='Shemos 30:2 one amah by one amah'),
        dict(item='total height to horn tops', cm=H_TOTAL, basis='measured', source='Shemos 30:2 two amot; horns counted inside the height (interpretation, as for the outer altar)'),
        dict(item='roof top plane', cm=Z_ROOF, basis='artistic', source='total height minus horn height'),
        dict(item='horn size (square) and height above roof', cm=HORN_SIZE, basis='artistic', source='book drawing 25 proportion; dossier: opinions from 3/4 finger to one finger'),
        dict(item='panel recess depth', cm=RECESS, basis='artistic', source='TI photos: recessed panel between pilaster strips'),
        dict(item='corner pilaster width', cm=POST, basis='artistic', source='TI photos: fluted strips at both edges'),
        dict(item='plinth band height', cm=PLINTH_H, basis='artistic', source='TI photos'),
        dict(item='frieze height', cm=TEFACH, basis='artistic', source='TI photos: arch frieze below the zer'),
        dict(item='zer projection beyond face', cm=ZER_OUT, basis='artistic', source='Shemos 30:3 zer; kol shehu (dossier)'),
        dict(item='zer band height', cm=ZER_Z1 - ZER_Z0, basis='artistic', source='book drawing 25: layered crown'),
        dict(item='crenellation height', cm=MERLON_H, basis='artistic', source='TI photos: pierced crenellated rim (closed blocks here)'),
        dict(item='hearth recess (square)', cm=HEARTH, basis='artistic', source='TI top hollow; three tefachim chosen for the incense smoke anchor'),
        dict(item='hearth recess depth', cm=Z_ROOF - Z_HEARTH, basis='artistic', source='shallow hollow'),
        dict(item='ring major radius', cm=RING_MAJOR, basis='artistic', source='Shemos 30:4 two rings below the zer on two flanks'),
        dict(item='ring axis height', cm=RING_Z, basis='artistic', source='below the zer, mid-frieze (book drawing 25)'),
        dict(item='pole length', cm=POLE_LEN, basis='artistic', source='Shemos 30:5 poles; length and knob ends after book drawing 25'),
        dict(item='pole radius', cm=POLE_R, basis='artistic', source='fits the ring inner radius %.2f' % (RING_MAJOR - RING_MINOR)),
        dict(item='pole direction', cm=None, basis='artistic', source='east-west along the Heikhal axis so the altar is carried along the house; the Temple altar had no poles in use (dossier), poles shown as in the book drawing'),
    ]


# ---------------------------------------------------------------------------
# export / verify / preview
# ---------------------------------------------------------------------------

def write_obj(path, name, parts):
    lines = ['# Original golden incense altar V2; Unreal legacy OBJ adapter (Y reflected, winding reversed)', 'o ' + name]
    index = 1
    allv = []
    checks = []
    for part, (vertices, faces) in parts:
        allv.extend(vertices)
        for a, b, c in faces:
            p, q, r = [(vertices[i][0], -vertices[i][1], vertices[i][2]) for i in (a, c, b)]
            ab = [q[i] - p[i] for i in range(3)]
            ac = [r[i] - p[i] for i in range(3)]
            n = cross(ab, ac)
            length = math.sqrt(sum(x * x for x in ab))
            nl = math.sqrt(sum(x * x for x in n))
            assert nl > 1e-8 and length > 1e-8, part
            for v in (p, q, r):
                lines.append('v %.9f %.9f %.9f' % v)
            for uv in ((0, 0), (length / 10, 0), (sum(ac[i] * ab[i] / length for i in range(3)) / 10, nl / length / 10)):
                lines.append('vt %.9f %.9f' % uv)
            for _ in range(3):
                lines.append('vn %.9f %.9f %.9f' % tuple(x / nl for x in n))
            lines.append('f ' + ' '.join('%d/%d/%d' % (k, k, k) for k in range(index, index + 3)))
            index += 3
        checks.append(dict(name=part, triangles=len(faces), closed=True, volume_cm3=volume(vertices, faces)))
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    bounds = {k: [fn(p[i] for p in allv) for i in range(3)] for k, fn in [('min', min), ('max', max)]}
    return dict(name=name, file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), triangles=(index - 1) // 3,
                partCount=len(parts), partVolumeSumCm3=sum(c['volume_cm3'] for c in checks), bounds_cm=bounds,
                size_cm=[bounds['max'][i] - bounds['min'][i] for i in range(3)], parts=checks)


def export():
    assert not (OUT / 'geometry-manifest.json').exists(), 'Frozen generation preserved; version the folder instead'
    OUT.mkdir(parents=True, exist_ok=True)
    meshes = [write_obj(OUT / (name + '.obj'), name, parts) for name, parts in geometry().items()]
    total = sum(m['triangles'] for m in meshes)
    assert total < 60000, total
    body = next(m for m in meshes if m['name'].endswith('Body'))
    # Bounds include the projecting zer (X) and the rings (Y); the gold faces themselves are one amah apart.
    for i, expected in enumerate((2 * (HALF + ZER_OUT), 2 * (RING_Y + RING_MAJOR + RING_MINOR), H_TOTAL)):
        assert abs(body['size_cm'][i] - expected) < 1e-6, (i, body['size_cm'], expected)
    assert abs(body['bounds_cm']['min'][2]) < 1e-9
    report = dict(
        status='OFFLINE_SOURCE_EXPORTED_NATIVE_PENDING', namespace=DEST, units='centimeters, canonical Unreal XYZ (X east, Y south, Z up); origin at the floor centre of the altar',
        tefach_cm=TEFACH, amah_cm=AMAH5,
        body_face_to_face_cm=[W, W], height_to_horn_tops_cm=H_TOTAL,
        bounds_note='Body bounds exceed the one-amah faces by the zer projection (%.3f cm each side in X and Y) and the rings (%.3f cm each side in Y); the poles mesh spans %.0f cm in X.' % (ZER_OUT, RING_Y + RING_MAJOR + RING_MINOR - HALF, POLE_LEN),
        convention='Canonical XYZ Unreal cm. Each OBJ is written with Y reflected and triangle winding reversed to compensate the verified legacy OBJ importer reflection (same adapter as create_heikhal_keilim.py / create_sanctuary_doors.py). Per-triangle normals, nondegenerate UV charts, no groups (single material slot), no external images. Every part is a closed solid with positive canonical volume; parts overlap additively.',
        dimensions=dimensions(), meshes=meshes, totalTriangles=total,
        anchors=dict(hearth_recess_centre_local_cm=[0.0, 0.0, Z_HEARTH], hearth_recess_size_cm=[HEARTH, HEARTH, Z_ROOF - Z_HEARTH],
                     roof_top_local_cm=Z_ROOF, ring_axis_local_cm=dict(y=[RING_Y, -RING_Y], z=RING_Z), pole_axis='local X (east-west at yaw 0)'),
        placement_intent=dict(map='/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough', location_cm=[-4650.0, 0.0, 925.0], yaw_degrees=0.0, scale=1.0,
                              replaces='REVIEW_HeikhalKeilim_SM_GoldenIncenseAltarStudy (scale 0.8333 plain box)',
                              handled_by='Scripts/release_import_incense_altar.py'),
        references=['Shemos 30:1-5', 'Lishchno Tidreshu pp. 253-256 (mikdash book/reference-pages/page-253.png, page-255.png, page-256.png)',
                    'SourceAssets/reference-ti/incense-altar/*.jpg (Temple Institute, reference use only, not redistributed)',
                    'SourceAssets/reference-ti/dossier.md section 3'],
        artistic_choices=['Pilaster reeding, disc frieze, stem/knot/bud panel motif, closed crenellations instead of a pierced lattice',
                          'Horn size, zer profile, ring and pole dimensions, knob ends, pole length',
                          'Hearth recess size and depth', 'Gold material is assigned at import, not authored here'],
        not_modeled=['Repousse relief detail of the TI panels (a normal map could carry it later)', 'Coals, incense, smoke (separate study)', 'Wood core (the model is the gold surface)'],
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), preview=PREVIEW,
        preview_note='Software orthographic render of the re-read OBJ files with an illustrative gold shade; not a native render or material acceptance')
    (OUT / 'geometry-manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    verify()
    return report


def read_obj(path):
    verts, uvs, normals, faces = [], [], [], []
    for line in path.read_text().splitlines():
        cols = line.split()
        if not cols:
            continue
        if cols[0] == 'v':
            verts.append(tuple(map(float, cols[1:])))
        elif cols[0] == 'vt':
            uvs.append(tuple(map(float, cols[1:])))
        elif cols[0] == 'vn':
            normals.append(tuple(map(float, cols[1:])))
        elif cols[0] == 'f':
            faces.append([tuple(int(v) - 1 for v in c.split('/')) for c in cols[1:]])
    return verts, uvs, normals, faces


def verify():
    """Independent readback of the exported files (verify_and_preview.py method) plus the preview."""
    manifest = json.loads((OUT / 'geometry-manifest.json').read_text(encoding='utf-8'))
    checks = []
    canonical_meshes = {}
    for r in manifest['meshes']:
        p = OUT / r['file']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == r['sha256'], r['file']
        verts, uvs, normals, faces = read_obj(p)
        assert len(faces) == r['triangles']
        signed = 0.0
        for face in faces:
            assert len(face) == 3
            for v, t, n in face:
                assert 0 <= v < len(verts) and 0 <= t < len(uvs) and 0 <= n < len(normals)
                assert abs(sum(x * x for x in normals[n]) - 1) < 1e-7
            a, b, c = [verts[f[0]] for f in face]
            ab = [b[i] - a[i] for i in range(3)]
            ac = [c[i] - a[i] for i in range(3)]
            cr = cross(ab, ac)
            area = math.sqrt(sum(x * x for x in cr))
            assert area > 1e-8
            assert sum(cr[i] * normals[face[0][2]][i] for i in range(3)) / area > .999999
            signed += sum(a[i] * cr[i] for i in range(3)) / 6
            a, b, c = [uvs[f[1]] for f in face]
            assert abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) > 1e-10
        canonical = [(x, -y, z) for x, y, z in verts]
        bounds = {k: [fn(v[i] for v in canonical) for i in range(3)] for k, fn in [('min', min), ('max', max)]}
        error = max(abs(bounds[k][i] - r['bounds_cm'][k][i]) for k in bounds for i in range(3))
        assert error < 1e-7
        # Reflection plus reversed winding keeps the file's right-handed signed volume positive and
        # equal to the canonical part-volume sum (what the importer's Y reflection then preserves).
        assert abs(signed - r['partVolumeSumCm3']) / r['partVolumeSumCm3'] < 1e-9, (signed, r['partVolumeSumCm3'])
        checks.append(dict(mesh=r['name'], triangles=len(faces), bounds_error_cm=error, file_signed_volume_cm3=signed, normals_and_uvs='PASS'))
        canonical_meshes[r['name']] = (canonical, [[f[0] for f in face] for face in faces])
    render_preview(canonical_meshes, OUT / PREVIEW)
    result = dict(status='PASS_OFFLINE_ONLY', checks=checks, preview=str(OUT / PREVIEW))
    print(json.dumps(result, indent=2))
    return result


def render_preview(meshes, path):
    """Two software orthographic panels (east elevation, oblique) of the re-read OBJ geometry."""
    PW, PH, S = 560, 760, 5.2
    W_, H_ = 2 * PW, PH
    rgb = bytearray([23, 27, 31] * (W_ * H_))
    zbuffer = [-1e9] * (W_ * H_)
    views = []
    # Panel 0: south elevation, seen from +Y looking north: screen right = east (+X), poles seen lengthwise.
    views.append(lambda p: (PW / 2 + p[0] * S, PH - 60 - p[2] * S, p[1]))
    # Panel 1: oblique from the south-east, 35 degrees yaw and 28 degrees elevation.
    ya, el = math.radians(35), math.radians(28)
    def oblique(p):
        x = p[0] * math.cos(ya) - p[1] * math.sin(ya)
        y = p[0] * math.sin(ya) + p[1] * math.cos(ya)
        sx = PW + PW / 2 + x * S
        sy = PH - 140 - (p[2] * math.cos(el) - y * math.sin(el)) * S
        depth = y * math.cos(el) + p[2] * math.sin(el)   # larger = nearer the camera
        return (sx, sy, depth)
    views.append(oblique)
    for name, (verts, faces) in meshes.items():
        base = (205, 153, 74) if 'Body' in name else (222, 176, 96)
        for ids in faces:
            a, b, c = [verts[i] for i in ids]
            ab = [b[i] - a[i] for i in range(3)]
            ac = [c[i] - a[i] for i in range(3)]
            n = cross(ab, ac)
            ln = math.sqrt(sum(x * x for x in n))
            if ln < 1e-9:
                continue
            light = .42 + .58 * max(0, (.55 * n[0] - .45 * n[1] + .7 * n[2]) / ln)
            color = bytes(min(255, int(x * light)) for x in base)
            for view in views:
                pts = [view(p) for p in (a, b, c)]
                x0, y0, d0 = pts[0]
                x1, y1, d1 = pts[1]
                x2, y2, d2 = pts[2]
                det = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
                if abs(det) < 1e-9:
                    continue
                for y in range(max(0, int(min(q[1] for q in pts))), min(H_, int(max(q[1] for q in pts)) + 1)):
                    for x in range(max(0, int(min(q[0] for q in pts))), min(W_, int(max(q[0] for q in pts)) + 1)):
                        w0 = ((y1 - y2) * (x + .5 - x2) + (x2 - x1) * (y + .5 - y2)) / det
                        w1 = ((y2 - y0) * (x + .5 - x2) + (x0 - x2) * (y + .5 - y2)) / det
                        w2 = 1 - w0 - w1
                        if min(w0, w1, w2) < 0:
                            continue
                        depth = w0 * d0 + w1 * d1 + w2 * d2
                        index = y * W_ + x
                        if depth > zbuffer[index]:
                            zbuffer[index] = depth
                            rgb[index * 3:index * 3 + 3] = color
    # Panel divider and a 10 cm scale bar (bottom left of panel 0).
    for y in range(H_):
        rgb[(y * W_ + PW) * 3:(y * W_ + PW) * 3 + 3] = bytes((90, 90, 90))
    for x in range(20, 20 + int(10 * S)):
        for y in (PH - 30, PH - 29, PH - 28):
            rgb[(y * W_ + x) * 3:(y * W_ + x) * 3 + 3] = bytes((230, 230, 230))

    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    scan = b''.join(b'\x00' + rgb[y * W_ * 3:(y + 1) * W_ * 3] for y in range(H_))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', W_, H_, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(scan)) + chunk(b'IEND', b''))


if __name__ == '__main__':
    if '--export' in sys.argv:
        report = export()
        summary = {k: report[k] for k in ('status', 'totalTriangles')}
        summary['meshes'] = [(m['name'], m['triangles'], m['size_cm']) for m in report['meshes']]
        print(json.dumps(summary, indent=2))
    elif '--verify' in sys.argv:
        verify()
    else:
        raise SystemExit('Use --export (fresh folder) or --verify (frozen folder); no engine actions here')
