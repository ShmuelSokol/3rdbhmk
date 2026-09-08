"""PilgrimRigV3: original anatomical pilgrim/visitor mesh set, offline only.

Route (3) of SourceAssets/characters-review/PilgrimRigV3/options.md: improve the
project's own original character procedurally, with no third-party asset and no
account login. This script launches nothing; it writes geometry, previews and a
manifest into SourceAssets/characters-review/PilgrimRigV3/ only.

Why V3 exists
-------------
V2 read as a smooth balloon: fat cylindrical sleeves, a conical robe with no
folds, an unsculpted egg head and no shoulder structure. V3 rebuilds the same
character with 7.5-head proportions, a defined shoulder shelf, tapered limbs,
a sculpted head (brow, nose, cheekbones, ears, jaw, beard variants), layered
garments (tunic + over-mantle with a hem band + wound sash + head covering) and
cloth folds carried in the geometry rather than faked by shading.

Rig compatibility
-----------------
The joint names, hierarchy and rest positions are byte-identical to
SourceAssets/characters-review/PilgrimRigV2/rig-definition.json (27 joints), and
the Idle/Walk clip authoring is reproduced unchanged, so the already-imported
A_Pilgrim_Original_Idle / _Walk assets remain valid motion for this mesh once the
mesh is bound to the same Skeleton. Two new original clips are added for the
"people taking pictures" request: A_Pilgrim_V3_PhotoCamera and _PhotoPhone.

Nothing here is a native import, a visual acceptance, a cook, a performance
result, or a halachic/historical certification of the clothing.
"""
import argparse
import colorsys
import hashlib
import json
import math
import random
import struct
import sys
import zlib
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'SourceAssets/characters-review/PilgrimRigV3'
DEST = '/Game/MikdashV3/CharacterReview/PilgrimRigV3'
V2_RIG = ROOT / 'SourceAssets/characters-review/PilgrimRigV2/rig-definition.json'

TRIANGLE_BUDGET = 25000

# ---------------------------------------------------------------------------
# vector / quaternion helpers
# ---------------------------------------------------------------------------


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def add(a, b):
    return tuple(a[i] + b[i] for i in range(3))


def scale(a, k):
    return tuple(v * k for v in a)


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def length(a):
    return math.sqrt(dot(a, a))


def normalize(a):
    n = length(a)
    if n < 1e-12:
        return (0.0, 0.0, 1.0)
    return (a[0] / n, a[1] / n, a[2] / n)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def gauss(v, mu, sigma):
    t = (v - mu) / sigma
    if abs(t) > 4:
        return 0.0
    return math.exp(-t * t)


def qaxis(axis, angle):
    return tuple(axis[i] * math.sin(angle / 2) for i in range(3)) + (math.cos(angle / 2),)


def qmul(a, b):
    x, y, z, w = a
    X, Y, Z, W = b
    return (w * X + x * W + y * Z - z * Y, w * Y - x * Z + y * W + z * X,
            w * Z + x * Y - y * X + z * W, w * W - x * X - y * Y - z * Z)


def qconj(q):
    return (-q[0], -q[1], -q[2], q[3])


def qrotate(q, p):
    return qmul(qmul(q, tuple(p) + (0,)), qconj(q))[:3]


def shortest_arc(a, b):
    """Unit quaternion rotating direction a onto direction b (arbitrary twist)."""
    a = normalize(a)
    b = normalize(b)
    d = clamp(dot(a, b), -1.0, 1.0)
    if d > 1 - 1e-9:
        return (0.0, 0.0, 0.0, 1.0)
    if d < -1 + 1e-9:
        axis = cross(a, (1, 0, 0))
        if length(axis) < 1e-6:
            axis = cross(a, (0, 1, 0))
        axis = normalize(axis)
        return (axis[0], axis[1], axis[2], 0.0)
    axis = cross(a, b)
    s = math.sqrt((1 + d) * 2)
    return (axis[0] / s, axis[1] / s, axis[2] / s, s / 2)


def gltf_vec(p):
    return [p[0] / 100, p[2] / 100, -p[1] / 100]


def gltf_quat(q):
    return [q[0], q[2], -q[1], q[3]]


# ---------------------------------------------------------------------------
# closed-shell primitives (every part is a closed, positively oriented manifold)
# ---------------------------------------------------------------------------


def loft(rings, segments=32, radial=None, exponent=None, cap=True):
    """Stacked horizontal profiles; `radial(theta, z, level)` carries cloth folds.

    rings: (z, rx, ry, cx, cy). `exponent` < 1 squares the section off for a
    ribcage/shoulder read instead of a balloon ellipse.
    """
    vertices, faces = [], []
    for level, ring in enumerate(rings):
        z, rx, ry, cx, cy = ring
        e = exponent(z, level) if exponent else 1.0
        for i in range(segments):
            t = i * math.tau / segments
            f = radial(t, z, level) if radial else 0.0
            ct, st = math.cos(t), math.sin(t)
            if e != 1.0:
                ct = math.copysign(abs(ct) ** e, ct)
                st = math.copysign(abs(st) ** e, st)
            vertices.append((cx + (rx + f) * ct, cy + (ry + f) * st, z))
    for j in range(len(rings) - 1):
        for i in range(segments):
            a = j * segments + i
            b = j * segments + (i + 1) % segments
            faces.extend([(a, b, b + segments), (a, b + segments, a + segments)])
    if cap:
        for ring, reverse in [(0, True), (len(rings) - 1, False)]:
            z, rx, ry, cx, cy = rings[ring]
            centre = len(vertices)
            vertices.append((cx, cy, z))
            for i in range(segments):
                tri = (centre, ring * segments + i, ring * segments + (i + 1) % segments)
                faces.append(tuple(reversed(tri)) if reverse else tri)
    return vertices, faces


def ellipsoid(centre, radii, segments=32, levels=20, sculpt=None):
    v = [(centre[0], centre[1], centre[2] - radii[2])]
    f = []
    for j in range(1, levels):
        lat = -math.pi / 2 + j * math.pi / levels
        for i in range(segments):
            t = i * math.tau / segments
            p = (radii[0] * math.cos(lat) * math.cos(t),
                 radii[1] * math.cos(lat) * math.sin(t),
                 radii[2] * math.sin(lat))
            if sculpt:
                p = sculpt(p)
            v.append(tuple(centre[k] + p[k] for k in range(3)))
    top = len(v)
    v.append((centre[0], centre[1], centre[2] + radii[2]))
    for i in range(segments):
        f.append((0, 1 + (i + 1) % segments, 1 + i))
        f.append((top, 1 + (levels - 2) * segments + i, 1 + (levels - 2) * segments + (i + 1) % segments))
    for j in range(levels - 2):
        for i in range(segments):
            a = 1 + j * segments + i
            b = 1 + j * segments + (i + 1) % segments
            f.extend([(a, b, b + segments), (a, b + segments, a + segments)])
    return v, f


def tube(points, radii, segments=12, radial=None):
    """Swept closed tube; `radial(theta, i)` adds sleeve/cloth ripple."""
    v, f = [], []
    for i, p in enumerate(points):
        tangent = normalize(sub(points[min(i + 1, len(points) - 1)], points[max(i - 1, 0)]))
        ref = (0, 1, 0) if abs(tangent[1]) < .9 else (1, 0, 0)
        u = normalize(cross(ref, tangent))
        w = cross(tangent, u)
        rx, ry = radii[i] if isinstance(radii[i], tuple) else (radii[i], radii[i])
        for j in range(segments):
            t = j * math.tau / segments
            g = radial(t, i) if radial else 0.0
            v.append(tuple(p[k] + (rx + g) * math.cos(t) * u[k] + (ry + g) * math.sin(t) * w[k] for k in range(3)))
    for i in range(len(points) - 1):
        for j in range(segments):
            a = i * segments + j
            b = i * segments + (j + 1) % segments
            f.extend([(a, b, b + segments), (a, b + segments, a + segments)])
    for i, rev in [(0, True), (len(points) - 1, False)]:
        c = len(v)
        v.append(points[i])
        for j in range(segments):
            tri = (c, i * segments + j, i * segments + (j + 1) % segments)
            f.append(tuple(reversed(tri)) if rev else tri)
    return v, f


def cloth_panel(grid, thickness=.35):
    """Closed thin cloth shell with hem edges, for open-front mantle panels.

    The back face is offset along each vertex's own surface normal rather than a
    fixed axis: a fixed axis collapses the boundary quads wherever the panel runs
    parallel to it (the shoulder cape and the head cloth both do).
    """
    rows = len(grid)
    cols = len(grid[0])

    def vertex_normal(r, c):
        du = sub(grid[r][min(c + 1, cols - 1)], grid[r][max(c - 1, 0)])
        dv = sub(grid[min(r + 1, rows - 1)][c], grid[max(r - 1, 0)][c])
        n = cross(du, dv)
        return normalize(n) if length(n) > 1e-9 else (0.0, 1.0, 0.0)

    front = [p for row in grid for p in row]
    offsets = [vertex_normal(r, c) for r in range(rows) for c in range(cols)]
    v = front + [add(front[i], scale(offsets[i], thickness)) for i in range(len(front))]
    n = len(front)
    f = []
    for r in range(rows - 1):
        for c in range(cols - 1):
            a = r * cols + c
            b = a + 1
            d = a + cols
            e = d + 1
            f.extend([(a, d, e), (a, e, b), (a + n, e + n, d + n), (a + n, b + n, e + n)])
    boundary = (list(range(cols)) + [r * cols + cols - 1 for r in range(1, rows)]
                + list(range(rows * cols - 2, (rows - 1) * cols - 1, -1))
                + [r * cols for r in range(rows - 2, 0, -1)])
    for a, b in zip(boundary, boundary[1:] + boundary[:1]):
        f.extend([(a, b, b + n), (a, b + n, a + n)])
    return v, f


def box(centre, half, rounding=0.0):
    """Rounded rectangular solid for the camera/phone props."""
    hx, hy, hz = half
    r = rounding
    v, f = [], []
    rings = [(-hz, hx - r, hy - r), (-hz + r, hx, hy), (hz - r, hx, hy), (hz, hx - r, hy - r)]
    seg = 12
    for z, ax, ay in rings:
        for i in range(seg):
            t = i * math.tau / seg
            ct, st = math.cos(t), math.sin(t)
            ct = math.copysign(abs(ct) ** .35, ct)
            st = math.copysign(abs(st) ** .35, st)
            v.append((centre[0] + ax * ct, centre[1] + ay * st, centre[2] + z))
    for j in range(len(rings) - 1):
        for i in range(seg):
            a = j * seg + i
            b = j * seg + (i + 1) % seg
            f.extend([(a, b, b + seg), (a, b + seg, a + seg)])
    for ring, reverse in [(0, True), (len(rings) - 1, False)]:
        c = len(v)
        v.append((centre[0], centre[1], centre[2] + rings[ring][0]))
        for i in range(seg):
            tri = (c, ring * seg + i, ring * seg + (i + 1) % seg)
            f.append(tuple(reversed(tri)) if reverse else tri)
    return v, f


# ---------------------------------------------------------------------------
# materials, palettes and variants
# ---------------------------------------------------------------------------

ROUGHNESS = {'Skin': .70, 'Linen': .93, 'Mantle': .95, 'Headcloth': .94, 'Sash': .89,
             'Leather': .78, 'Hair': .88, 'Eyes': .30, 'Trim': .86, 'Prop': .42, 'PropGlass': .10}

SKIN_TONES = {
    'olive': ((.455, .272, .173), (.070, .036, .020)),
    'tan': ((.520, .330, .215), (.085, .050, .028)),
    'deep': ((.330, .185, .112), (.045, .024, .014)),
    'fair': ((.610, .420, .310), (.140, .085, .045)),
}

GARMENT_PALETTES = {
    'linen-warm': {'Linen': (.700, .630, .480), 'Mantle': (.285, .320, .268),
                   'Headcloth': (.740, .700, .580), 'Sash': (.470, .300, .150), 'Trim': (.360, .255, .120)},
    'wool-umber': {'Linen': (.510, .420, .300), 'Mantle': (.245, .180, .125),
                   'Headcloth': (.560, .470, .350), 'Sash': (.330, .140, .105), 'Trim': (.200, .140, .085)},
    'bleached': {'Linen': (.855, .830, .760), 'Mantle': (.640, .615, .545),
                 'Headcloth': (.880, .860, .800), 'Sash': (.560, .180, .150), 'Trim': (.500, .430, .300)},
    'indigo': {'Linen': (.620, .600, .540), 'Mantle': (.140, .190, .300),
               'Headcloth': (.640, .625, .570), 'Sash': (.220, .250, .380), 'Trim': (.320, .300, .220)},
    'ochre': {'Linen': (.720, .545, .285), 'Mantle': (.420, .330, .200),
              'Headcloth': (.760, .620, .400), 'Sash': (.330, .240, .140), 'Trim': (.290, .200, .105)},
    'dusty-blue': {'Linen': (.560, .590, .600), 'Mantle': (.270, .330, .360),
                   'Headcloth': (.640, .660, .655), 'Sash': (.360, .300, .230), 'Trim': (.240, .240, .215)},
    'sand-teal': {'Linen': (.760, .690, .545), 'Mantle': (.190, .330, .320),
                  'Headcloth': (.790, .740, .630), 'Sash': (.400, .280, .160), 'Trim': (.260, .225, .140)},
}

PROP_COLOURS = {'Prop': (.055, .058, .062), 'PropGlass': (.030, .045, .060)}


def variant_materials(variant):
    skin, hair = SKIN_TONES[variant['skin_tone']]
    colours = dict(GARMENT_PALETTES[variant['palette']])
    colours.update({'Skin': skin, 'Hair': hair, 'Eyes': (.180, .130, .080), 'Leather': (.140, .080, .042)})
    colours.update(PROP_COLOURS)
    return colours


VARIANTS = [
    dict(id='V3_Pilgrim_Man_A', label='Pilgrim man, standard build',
         girth=1.00, shoulder=1.00, beard='short', headwear='cloth', mantle=True,
         tunic_hem=8.0, prop=None, palette='linen-warm', skin_tone='olive',
         actor_scale=1.00, fold_seed=11),
    dict(id='V3_Pilgrim_Man_B', label='Pilgrim man, heavy build, full beard',
         girth=1.13, shoulder=1.06, beard='full', headwear='turban', mantle=True,
         tunic_hem=7.0, prop=None, palette='wool-umber', skin_tone='deep',
         actor_scale=1.03, fold_seed=23),
    dict(id='V3_Pilgrim_Woman_A', label='Pilgrim woman, long shawl',
         girth=0.93, shoulder=0.90, beard='none', headwear='shawl', mantle=True,
         tunic_hem=5.5, prop=None, palette='indigo', skin_tone='tan',
         actor_scale=0.94, fold_seed=37),
    dict(id='V3_Pilgrim_Youth', label='Youth, short tunic, no mantle',
         girth=0.84, shoulder=0.88, beard='none', headwear='cap', mantle=False,
         tunic_hem=42.0, prop=None, palette='ochre', skin_tone='tan',
         actor_scale=0.86, fold_seed=53),
    dict(id='V3_Visitor_Camera', label='Visitor with a camera (photo clip)',
         girth=0.98, shoulder=1.02, beard='short', headwear='cap', mantle=False,
         tunic_hem=9.0, prop='camera', palette='sand-teal', skin_tone='fair',
         actor_scale=1.01, fold_seed=67),
    dict(id='V3_Visitor_Phone', label='Visitor with a phone (photo clip)',
         girth=1.02, shoulder=0.98, beard='none', headwear='none', mantle=True,
         tunic_hem=8.5, prop='phone', palette='dusty-blue', skin_tone='olive',
         actor_scale=0.99, fold_seed=71),
    dict(id='V3_Pilgrim_Man_A_Bleached', label='Colour variant of Man A, bleached linen',
         girth=1.00, shoulder=1.00, beard='short', headwear='cloth', mantle=True,
         tunic_hem=8.0, prop=None, palette='bleached', skin_tone='tan',
         actor_scale=0.98, fold_seed=11),
    dict(id='V3_Pilgrim_Man_A_Ochre', label='Colour variant of Man A, ochre',
         girth=1.00, shoulder=1.00, beard='full', headwear='turban', mantle=True,
         tunic_hem=8.0, prop=None, palette='ochre', skin_tone='deep',
         actor_scale=1.02, fold_seed=11),
    dict(id='V3_Visitor_Camera_Umber', label='Colour variant of the camera visitor',
         girth=0.98, shoulder=1.02, beard='none', headwear='cloth', mantle=True,
         tunic_hem=9.0, prop='camera', palette='wool-umber', skin_tone='tan',
         actor_scale=0.97, fold_seed=67),
]


# ---------------------------------------------------------------------------
# skeleton (identical names, hierarchy and rest positions to PilgrimRigV2)
# ---------------------------------------------------------------------------


def skeleton():
    bones = []

    def bone(name, parent, pos):
        bones.append({'name': name, 'parent': parent, 'position_cm': pos})

    bone('root', None, (0, 0, 0))
    bone('pelvis', 'root', (0, 0, 98))
    bone('spine_01', 'pelvis', (0, 0, 114))
    bone('spine_02', 'spine_01', (0, 0, 132))
    bone('chest', 'spine_02', (0, 0, 143))
    bone('neck_01', 'chest', (0, 0, 153))
    bone('head', 'neck_01', (0, 0, 166))
    for s, side in [(-1, 'r'), (1, 'l')]:
        bone('clavicle_' + side, 'chest', (s * 10, 0, 143))
        bone('upperarm_' + side, 'clavicle_' + side, (s * 20, 0, 143))
        bone('lowerarm_' + side, 'upperarm_' + side, (s * 33, -.5, 123))
        bone('hand_' + side, 'lowerarm_' + side, (s * 44, -1, 98))
        bone('thigh_' + side, 'pelvis', (s * 8, 0, 88))
        bone('calf_' + side, 'thigh_' + side, (s * 8, 0, 47))
        bone('foot_' + side, 'calf_' + side, (s * 8, 0, 6))
        bone('ball_' + side, 'foot_' + side, (s * 8, -9, 3))
        bone('skirt_' + side, 'pelvis', (s * 8, 0, 88))
    bone('mantle_front', 'chest', (0, -9, 143))
    bone('mantle_back', 'chest', (0, 11, 143))
    lookup = {b['name']: i for i, b in enumerate(bones)}
    for b in bones:
        b['parent_index'] = lookup[b['parent']] if b['parent'] else None
        b['local_translation_cm'] = (sub(b['position_cm'], bones[b['parent_index']]['position_cm'])
                                     if b['parent'] else b['position_cm'])
    return bones


def assert_rig_matches_v2(bones):
    """Refuse to ship a mesh whose rest pose would invalidate the existing clips."""
    if not V2_RIG.is_file():
        return {'compared': False, 'reason': 'PilgrimRigV2/rig-definition.json not present'}
    reference = json.loads(V2_RIG.read_text(encoding='utf-8-sig'))['bones']
    assert len(reference) == len(bones), 'joint count differs from PilgrimRigV2'
    for a, b in zip(reference, bones):
        assert a['name'] == b['name'], (a['name'], b['name'])
        assert a['parent'] == b['parent'], a['name']
        assert a['parent_index'] == b['parent_index'], a['name']
        assert tuple(a['position_cm']) == tuple(b['position_cm']), a['name']
        assert tuple(a['local_translation_cm']) == tuple(b['local_translation_cm']), a['name']
    return {'compared': True, 'joints': len(bones), 'identical_rest_pose': True,
            'source': str(V2_RIG.relative_to(ROOT))}


# ---------------------------------------------------------------------------
# skin weight policies (declared per part, never inferred from a name)
# ---------------------------------------------------------------------------


def blend(a, b, t):
    t = clamp(t)
    return {a: 1 - t, b: t}


def head_skin(p):
    return {'head': 1.0}


def neck_skin(p):
    return blend('neck_01', 'head', (p[2] - 150) / 11)


def torso_skin(p):
    x, y, z = p
    if z >= 143:
        return blend('chest', 'neck_01', (z - 145) / 8)
    if z >= 128:
        return blend('spine_02', 'chest', (z - 128) / 15)
    if z >= 110:
        return blend('spine_01', 'spine_02', (z - 110) / 18)
    if z >= 92:
        return blend('pelvis', 'spine_01', (z - 99) / 15)
    t = clamp((92 - z) / 34)
    right = clamp((x + 7) / 14)
    return {'pelvis': 1 - t, 'skirt_r': t * (1 - right), 'skirt_l': t * right}


def sash_skin(p):
    return {'pelvis': 1.0}


def sleeve_skin(p):
    x, y, z = p
    side = 'r' if x < 0 else 'l'
    if z > 137:
        return blend('chest', 'upperarm_' + side, (abs(x) - 14) / 9)
    if z > 112:
        return blend('lowerarm_' + side, 'upperarm_' + side, (z - 112) / 20)
    return blend('hand_' + side, 'lowerarm_' + side, (z - 99) / 12)


def forearm_skin(p):
    x, y, z = p
    side = 'r' if x < 0 else 'l'
    return blend('hand_' + side, 'lowerarm_' + side, (z - 97) / 9)


def hand_skin(p):
    return {'hand_r' if p[0] < 0 else 'hand_l': 1.0}


def leg_skin(p):
    x, y, z = p
    side = 'r' if x < 0 else 'l'
    return blend('foot_' + side, 'calf_' + side, (z - 5) / 16)


def foot_skin(p):
    return {'foot_r' if p[0] < 0 else 'foot_l': 1.0}


def mantle_front_skin(p):
    return blend('chest', 'mantle_front', (143 - p[2]) / 36)


def mantle_back_skin(p):
    return blend('chest', 'mantle_back', (143 - p[2]) / 36)


def mantle_shoulder_skin(p):
    return blend('chest', 'clavicle_r' if p[0] < 0 else 'clavicle_l', (abs(p[0]) - 6) / 17)


def influence(part, p, index):
    weights = part['skin'](p)
    entries = sorted([(index[k], w) for k, w in weights.items() if w > 1e-9], key=lambda a: -a[1])
    assert 1 <= len(entries) <= 4, (part['name'], entries)
    total = sum(w for _, w in entries)
    entries = [(j, w / total) for j, w in entries]
    return entries + [(0, 0.0)] * (4 - len(entries))


# ---------------------------------------------------------------------------
# cloth fold fields
# ---------------------------------------------------------------------------


def fold_field(seed, base, harmonics=((13, 1.0), (7, .55), (23, .28), (5, .34))):
    """Deterministic periodic cloth-fold offset, phase-drifting with height."""
    rng = random.Random(seed)
    terms = [(f, a * rng.uniform(.7, 1.25), rng.uniform(0, math.tau), rng.uniform(-.045, .045))
             for f, a in harmonics]

    def field(theta, z, amplitude):
        if amplitude <= 0:
            return 0.0
        total = sum(a * math.cos(f * theta + ph + drift * z) for f, a, ph, drift in terms)
        return base * amplitude * total
    return field


def tunic_amplitude(z, hem):
    """Flat over the chest, compressed under the sash, deepest toward the hem."""
    if z > 146:
        return 0.06
    if z > 118:
        return .06 + .30 * smooth((146 - z) / 28)
    if z > 112:
        return .36 + .22 * smooth((118 - z) / 6)
    if z > 99:
        return .58 - .30 * smooth((112 - z) / 13) * smooth((z - 96) / 8)
    below = clamp((99 - z) / max(12.0, 99 - hem))
    return .55 + .80 * smooth(below)


# ---------------------------------------------------------------------------
# head sculpt
# ---------------------------------------------------------------------------


def head_sculpt(p):
    x, y, z = p
    jaw = .70 + .30 * smooth((z + 10.6) / 10.2)
    x *= jaw
    temple = 1 - .07 * gauss(z, 4.6, 3.4)
    x *= temple
    if y > 0:
        y *= .965
        y -= .55 * gauss(z, 6.0, 4.0) * gauss(abs(x), 0, 6.5)
    else:
        y -= .95 * gauss(abs(x), 3.5, 2.5) * gauss(z, 2.7, 1.9)       # brow ridge
        y += 1.05 * gauss(abs(x), 3.2, 1.7) * gauss(z, 0.6, 1.5)      # eye socket
        y -= .80 * gauss(abs(x), 4.7, 2.0) * gauss(z, -2.1, 2.1)      # cheekbone
        y += .42 * gauss(abs(x), 3.4, 1.9) * gauss(z, -5.2, 2.1)      # cheek hollow
        y -= .38 * gauss(abs(x), 0, 3.3) * gauss(z, -6.6, 2.5)        # muzzle
        y -= .62 * gauss(abs(x), 0, 2.6) * gauss(z, -9.4, 2.3)        # chin
        y += .30 * gauss(abs(x), 0, 1.6) * gauss(z, -7.8, 1.2)        # sub-lip crease
    z -= .35 * gauss(abs(x), 0, 3.0) * gauss(z, -11.0, 2.0)
    return x, y, z


def face_parts(add, variant):
    g = variant['girth']
    head_centre = (0, -.4, 166.4)
    head_radii = (8.15 * (.97 + .03 * g), 7.35, 11.85)
    add('Head', 'Skin', ellipsoid(head_centre, head_radii, 40, 26, head_sculpt), head_skin)
    add('Neck', 'Skin', loft([(147.5, 5.9 * g, 5.2 * g, 0, .3), (152, 5.3 * g, 4.7 * g, 0, 0),
                              (157, 5.5 * g, 5.0 * g, 0, -.3), (161, 6.2 * g, 5.6 * g, 0, -.6)], 22), neck_skin)
    # Nose: bridge, tip and nostril wings rather than one smooth cone.
    add('Nose', 'Skin', loft([
        (161.4, 1.30, .95, 0, -7.05), (163.2, 1.05, .95, 0, -7.55),
        (164.6, 1.45, 1.55, 0, -8.35), (165.6, 1.55, 1.60, 0, -8.55),
        (167.2, 1.15, 1.05, 0, -8.00), (169.4, .78, .58, 0, -7.35),
        (171.0, .60, .34, 0, -7.05)], 20), head_skin)
    for side in (-1, 1):
        add('Nostril%d' % side, 'Skin', ellipsoid((side * 1.35, -7.85, 164.5), (.72, .68, .55), 14, 9), head_skin)
        add('Ear%d' % side, 'Skin', ellipsoid((side * 7.6, .35, 165.9), (1.25, 1.15, 3.05), 16, 11,
                                              lambda p: (p[0] * (1 - .35 * gauss(p[2], .3, 1.4)), p[1], p[2])), head_skin)
        add('Eye%d' % side, 'Eyes', ellipsoid((side * 3.15, -6.95, 167.9), (1.05, .30, .42), 16, 9), head_skin)
        add('Brow%d' % side, 'Hair', tube([(side * 1.7, -7.30, 169.5), (side * 3.1, -7.55, 169.9),
                                           (side * 4.7, -7.10, 169.4)], [.22, .32, .16], 8), head_skin)
    add('UpperLip', 'Skin', ellipsoid((0, -7.30, 161.9), (2.25, .48, .40), 18, 10), head_skin)
    add('LowerLip', 'Skin', ellipsoid((0, -7.25, 161.0), (2.00, .45, .38), 18, 10), head_skin)
    if variant['beard'] == 'none':
        hair_folds = fold_field(variant['fold_seed'] + 5, .32, ((9, 1.0), (17, .5), (5, .6)))
        add('Hair', 'Hair', loft([(162.5, 8.0, 7.3, 0, .4), (167, 8.6, 7.8, 0, .5),
                                  (171.5, 8.5, 7.7, 0, .6), (175.5, 7.4, 6.7, 0, .6),
                                  (178.2, 3.9, 3.5, 0, .5)], 26,
                                 radial=lambda t, z, l: hair_folds(t, z, .8)), head_skin)
        return
    style = variant['beard']
    top = 158.6 if style == 'short' else 159.4
    bottom = 154.2 if style == 'short' else 149.6
    beard_folds = fold_field(variant['fold_seed'] + 3, .26, ((11, 1.0), (19, .5), (7, .6)))
    rings = []
    n = 6 if style == 'short' else 8
    for i in range(n):
        u = i / (n - 1)
        z = bottom + (top - bottom) * u
        w = (2.0 + 4.6 * smooth(u)) if style == 'short' else (1.4 + 5.2 * smooth(u ** .8))
        rings.append((z, w, w * .84, 0, -2.4 - 1.1 * (1 - u)))
    add('Beard', 'Hair', loft(rings, 26, radial=lambda t, z, l: beard_folds(t, z, .8)), head_skin)
    add('Moustache', 'Hair', ellipsoid((0, -7.15, 162.9), (2.7, .70, .60), 16, 9), head_skin)
    add('Sideburn-1', 'Hair', tube([(-7.4, -1.2, 168.0), (-7.6, -2.0, 163.5), (-6.4, -2.6, 159.8)],
                                   [(1.0, 1.1), (1.0, 1.2), (1.3, 1.4)], 8), head_skin)
    add('Sideburn1', 'Hair', tube([(7.4, -1.2, 168.0), (7.6, -2.0, 163.5), (6.4, -2.6, 159.8)],
                                  [(1.0, 1.1), (1.0, 1.2), (1.3, 1.4)], 8), head_skin)


# ---------------------------------------------------------------------------
# garment + body assembly
# ---------------------------------------------------------------------------


def head_covering(add, variant):
    kind = variant['headwear']
    if kind == 'none':
        return
    folds = fold_field(variant['fold_seed'] + 9, .34, ((11, 1.0), (6, .7), (19, .35)))
    if kind == 'turban':
        add('TurbanCrown', 'Headcloth', ellipsoid((0, .3, 176.0), (8.9, 8.3, 5.4), 28, 12), head_skin)
        for layer in range(3):
            pts = [(8.5 * math.cos(i * math.tau / 26), .3 + 8.0 * math.sin(i * math.tau / 26),
                    172.4 + layer * 1.95 + 1.0 * math.cos(i * math.tau / 26 + .5)) for i in range(27)]
            add('TurbanBand%d' % layer, 'Headcloth', tube(pts, [(.82, 1.20)] * 27, 8), head_skin)
        return
    if kind == 'cap':
        add('Cap', 'Headcloth', loft([(170.0, 8.7, 8.0, 0, .3), (173.5, 8.6, 7.9, 0, .35),
                                      (176.5, 7.6, 7.0, 0, .4), (178.6, 4.3, 3.9, 0, .4)], 24,
                                     radial=lambda t, z, l: folds(t, z, .45)), head_skin)
        return
    # 'cloth' and 'shawl': a skull cap plus a drape hanging from its rim around
    # the back and both sides, open at the face. Built as an arc in the lateral
    # angle so the face stays clear and the cloth never reads as a flat plate.
    long = kind == 'shawl'
    add('HeadCap', 'Headcloth', loft([(168.5, 9.0, 8.3, 0, .4), (172.0, 9.1, 8.4, 0, .45),
                                      (175.5, 8.4, 7.7, 0, .5), (178.3, 5.6, 5.1, 0, .5),
                                      (179.4, 2.4, 2.2, 0, .5)], 26,
                                     radial=lambda t, z, l: folds(t, z, .40)), head_skin)
    rows = 15 if long else 12
    cols = 21
    span = math.radians(126 if not long else 138)
    grid = []
    for r in range(rows):
        u = r / (rows - 1)
        row = []
        for c in range(cols):
            t = c / (cols - 1)
            a = -span + 2 * span * t              # 0 = straight back, +-span = beside the face
            back = .5 + .5 * math.cos(a)          # 1 behind the head, 0 at the face
            bottom = (132.0 if long else 145.0) + (14.0 if long else 8.0) * (1 - back)
            z = 169.0 - (169.0 - bottom) * smooth(u)
            flare = (3.6 if long else 2.0) * smooth(u) * (.45 + .75 * back)
            rx = 9.1 + flare
            ry = 8.4 + flare * 1.15
            ripple = folds(a * 2.2 + u * 1.4, z, .55 + .8 * u)
            x = (rx + ripple) * math.sin(a)
            y = .45 + (ry + ripple) * math.cos(a)
            row.append((x, y, z + ripple * .35))
        grid.append(row)
    add('HeadCloth', 'Headcloth', cloth_panel(grid, .34), head_skin)
    band = [(8.9 * math.cos(i * math.tau / 22), .45 + 8.3 * math.sin(i * math.tau / 22),
             171.6 + .8 * math.cos(i * math.tau / 22)) for i in range(23)]
    add('HeadBand', 'Trim', tube(band, [(.52, .80)] * 23, 8), head_skin)


def prop_parts(add, variant):
    kind = variant['prop']
    if not kind:
        return
    # Skinned rigidly to the right hand: in the photo clips the arm lifts it to
    # eye/chest height, which is what "people taking pictures" needs.
    hx, hy, hz = -46.5, -4.6, 95.0
    if kind == 'camera':
        cx, cy, cz = hx, hy - 2.6, hz + 2.4
        add('CameraBody', 'Prop', box((cx, cy, cz), (5.4, 3.0, 3.6), 1.0), hand_skin)
        add('CameraLens', 'Prop', tube([(cx, cy - 2.6, cz), (cx, cy - 7.0, cz)],
                                       [(2.30, 2.30), (2.55, 2.55)], 14), hand_skin)
        add('CameraGlass', 'PropGlass', tube([(cx, cy - 7.05, cz), (cx, cy - 7.5, cz)],
                                             [(1.95, 1.95), (1.80, 1.80)], 14), hand_skin)
        add('CameraHump', 'Prop', box((cx, cy + .3, cz + 4.5), (2.0, 1.9, 1.3), .5), hand_skin)
    else:
        add('PhoneBody', 'Prop', box((hx, hy - .8, hz + 2.0), (3.6, .55, 7.2), .6), hand_skin)
        add('PhoneScreen', 'PropGlass', box((hx, hy - 1.45, hz + 2.0), (3.15, .12, 6.6), .4), hand_skin)


def assembly(variant):
    parts = []
    g = variant['girth']
    sh = variant['shoulder']
    hem = variant['tunic_hem']
    folds = fold_field(variant['fold_seed'], .95)
    mantle_folds = fold_field(variant['fold_seed'] + 1, .70, ((9, 1.0), (5, .6), (15, .35)))

    def add(name, material, mesh, skin):
        v, f = mesh
        volume = sum(dot(v[a], cross(v[b], v[c])) / 6 for a, b, c in f)
        if volume < 0:
            f = [(a, c, b) for a, b, c in f]
        parts.append({'name': name, 'material': material, 'vertices': v, 'faces': f, 'skin': skin})

    # ---- tunic: the load-bearing silhouette. Real waist, ribcage and shoulder
    # shelf, superelliptic sections, and vertical fold geometry in the cloth.
    profile = [
        (hem, 19.6, 14.0), (hem + 2.1, 20.3, 14.6), (hem + 8.0, 19.3, 13.9),
        (24, 18.5, 13.4), (42, 17.7, 12.8), (60, 17.0, 12.3), (76, 16.4, 11.9),
        (90, 15.8, 11.4), (99, 15.0, 10.9), (105.5, 13.5, 10.1), (111, 13.8, 10.3),
        (119, 15.6, 11.1), (127, 17.4, 11.7), (135, 19.0, 12.2), (140, 19.9, 12.3),
        (143.5, 20.4, 12.2), (147, 17.4, 10.8), (150.5, 11.6, 8.4), (153.5, 7.6, 6.6),
    ]
    rings = [(z, rx * g * (sh if z > 130 else 1.0), ry * g, 0, 0) for z, rx, ry in profile]

    def tunic_radial(t, z, level):
        return folds(t, z, tunic_amplitude(z, hem))

    def tunic_exponent(z, level):
        # Ramped, never stepped: a hard change of section between two rings put
        # a visible spike on V2-era shoulders.
        bump = smooth((z - 92) / 14) * smooth((140 - z) / 16)
        return 1.0 - .15 * bump

    add('Tunic', 'Linen', loft(rings, 60, radial=tunic_radial, exponent=tunic_exponent), torso_skin)

    def section(z):
        """Interpolated tunic half-width/depth, so the mantle can follow the body."""
        if z <= rings[0][0]:
            return rings[0][1], rings[0][2]
        for (z0, rx0, ry0, _, _), (z1, rx1, ry1, _, _) in zip(rings, rings[1:]):
            if z <= z1:
                t = (z - z0) / (z1 - z0)
                return rx0 + (rx1 - rx0) * t, ry0 + (ry1 - ry0) * t
        return rings[-1][1], rings[-1][2]

    # ---- wound sash: one continuous band whose turns read as a diagonal wrap.
    def sash_radial(t, z, level):
        return (.38 * math.cos(t - (z - 100.5) * .82) + .20 * math.cos(11 * t + 1.1)
                + .12 * math.cos(5 * t - 2.2))
    sash_rings = []
    for z, pad in ((100.0, 1.8), (101.2, 3.4), (103.6, 3.8), (106.6, 3.8), (109.2, 3.4), (110.4, 1.7)):
        rx, ry = section(z)
        sash_rings.append((z, rx + pad, ry + pad * .82, 0, 0))
    add('Sash', 'Sash', loft(sash_rings, 36, radial=sash_radial), sash_skin)
    rx0, ry0 = section(104)
    add('SashTail', 'Sash', cloth_panel(
        [[(2.8 + c * .95 + r * .16, -(ry0 + 2.9) - .55 * math.sin(r * .55) - .22 * c,
           103.0 - r * 3.4 + .55 * math.sin(c * 1.4 + r * .5)) for c in range(5)]
         for r in range(11)], .26), sash_skin)
    add('Collar', 'Trim', loft([(150.6, 11.9 * g, 8.6 * g, 0, 0), (151.4, 12.4 * g, 9.0 * g, 0, 0),
                                (153.0, 8.0 * g, 6.9 * g, 0, 0), (153.6, 7.4 * g, 6.4 * g, 0, 0)],
                               26), torso_skin)

    # ---- over-mantle: ONE cloth draped over both shoulders and open at the
    # front, standing off the chest and back while pulling tight at the sides so
    # the arms pass outside it. V2's separate flat boards read as cardboard.
    if variant['mantle']:
        opening = math.radians(14)
        rows, cols = 22, 34
        top_z, bottom_z = 149.0, 54.0
        grid = []
        for r in range(rows):
            u = r / (rows - 1)
            z = top_z - (top_z - bottom_z) * u
            rx, ry = section(z)
            ease = 2.6 + 4.4 * smooth(u)
            row = []
            for c in range(cols):
                t = c / (cols - 1)
                a = opening + t * (math.tau - 2 * opening)     # 0 = front, pi = back
                sa, ca = math.sin(a), math.cos(a)
                ripple = .95 + mantle_folds(a * 1.9 + u * 1.1, z, .40 + .70 * smooth(u))
                # Tight at the sides (|sin a| -> 1), standing proud front and back.
                lateral = rx * sh * (1 - .17 * abs(sa)) + ease * (.30 + .70 * ca * ca)
                depth = ry + ease + .8
                x = (lateral + ripple) * sa
                y = -(depth + ripple) * ca - .5
                row.append((x, y, z + ripple * .30 - 2.6 * math.exp(-(min(t, 1 - t) / .13) ** 2) * (1 - u)))
            grid.append(row)
        add('Mantle', 'Mantle', cloth_panel(grid, .42),
            lambda p: (mantle_back_skin(p) if p[1] > 0 else mantle_front_skin(p)))
        add('MantleHem', 'Trim', tube(grid[-1], [(.62, .62)] * cols, 6), mantle_back_skin)
        for s, edge_index in ((-1, 0), (1, cols - 1)):
            column = [grid[r][edge_index] for r in range(rows)]
            add('MantleEdge%d' % s, 'Trim', tube(column, [(.48, .48)] * rows, 6),
                mantle_front_skin)

    # ---- arms: tapered sleeve, bare forearm, hand with fingers.
    sleeve_folds = fold_field(variant['fold_seed'] + 2, .30, ((8, 1.0), (13, .55)))
    for s in (-1, 1):
        tag = 'R' if s < 0 else 'L'
        axis = [(s * 9.6 * sh, .3, 149.4), (s * 15.4 * sh, .3, 145.0), (s * 18.9 * sh, .1, 140.6), (s * 24.4, -.2, 132.6),
                (s * 29.6, -.4, 126.0), (s * 32.6, -.5, 122.6), (s * 37.6, -.8, 112.4),
                (s * 42.4, -1.0, 101.4)]
        radii = [(4.1 * g, 3.9 * g), (6.5 * g, 6.1 * g), (6.4 * g, 6.1 * g), (5.9 * g, 5.6 * g),
                 (5.2 * g, 5.0 * g), (4.9 * g, 4.7 * g), (4.4 * g, 4.2 * g), (3.9 * g, 3.7 * g)]
        add('Sleeve' + tag, 'Linen', tube(axis, radii, 20,
            radial=lambda t, i, k=s: (sleeve_folds(t + k * .8, 140 - i * 7, .75 + .55 * i / 6)
                                      - .34 * math.cos(3 * t + 1.2) * gauss(i, 5.0, 1.1))), sleeve_skin)
        add('Cuff' + tag, 'Trim', tube([(s * 41.6, -1, 103.0), (s * 42.7, -1, 100.6)],
                                       [(4.30 * g, 4.10 * g)] * 2, 20), sleeve_skin)
        add('Forearm' + tag, 'Skin', tube([(s * 42.5, -1, 101.6), (s * 43.6, -1, 98.6)],
                                          [(3.05, 2.55), (3.00, 2.30)], 16), forearm_skin)
        add('Palm' + tag, 'Skin', ellipsoid((s * 44.9, -1.3, 95.4), (3.35, 1.95, 5.20), 18, 13), hand_skin)
        for i, flen in enumerate((4.9, 5.7, 5.3, 4.2)):
            x = s * (42.5 + i * 1.62)
            add('Finger%s%d' % (tag, i), 'Skin',
                tube([(x, -1.2, 92.2), (x + s * .22, -1.6, 90.4), (x + s * .30, -2.35, 92.6 - flen)],
                     [(.68, .74), (.64, .70), (.48, .56)], 8), hand_skin)
        add('Thumb' + tag, 'Skin',
            tube([(s * 42.6, -1.3, 96.6), (s * 40.8, -1.9, 94.4), (s * 40.2, -2.7, 92.7)],
                 [(.92, .88), (.86, .82), (.62, .62)], 8), hand_skin)

    # ---- legs and feet.
    for s in (-1, 1):
        tag = 'R' if s < 0 else 'L'
        top = max(20.0, hem + 6.0)
        add('Shin' + tag, 'Skin', loft([(3.6, 3.3 * g, 3.6 * g, s * 8, .4),
                                        (10, 3.6 * g, 4.0 * g, s * 8, .4),
                                        (top * .55, 4.4 * g, 4.7 * g, s * 8, .4),
                                        (top, 4.9 * g, 5.2 * g, s * 8, .4)], 20), leg_skin)
        add('Foot' + tag, 'Skin', ellipsoid((s * 8, -4.0, 4.4), (3.85 * g, 9.6, 3.1), 20, 12,
            lambda p: (p[0], p[1], p[2] * (1 - .30 * gauss(p[1], -8.0, 4.0)))), foot_skin)
        add('SandalSole' + tag, 'Leather', loft([(0, 3.7 * g, 10.2, s * 8, -4.0),
                                                 (.55, 4.25 * g, 10.7, s * 8, -4.0),
                                                 (1.7, 4.25 * g, 10.7, s * 8, -4.0),
                                                 (2.1, 3.95 * g, 10.2, s * 8, -4.0)], 26), foot_skin)
        for idx, y in enumerate((-8.2, -3.4)):
            add('SandalStrap%s%d' % (tag, idx), 'Leather',
                tube([(s * 8 - 3.6, y, 3.0), (s * 8 - 2.5, y, 6.2), (s * 8, y, 7.2),
                      (s * 8 + 2.5, y, 6.2), (s * 8 + 3.6, y, 3.0)], [(.72, .30)] * 5, 8), foot_skin)

    face_parts(add, variant)
    head_covering(add, variant)
    prop_parts(add, variant)
    return parts


# ---------------------------------------------------------------------------
# clips (Idle/Walk reproduced from PilgrimRigV2; two original photo clips added)
# ---------------------------------------------------------------------------

CLIPS = {'Idle': 3.2, 'Walk': 1.2, 'PhotoCamera': 4.0, 'PhotoPhone': 3.6}
ARM_CHAIN = {'r': (-1, (-13, -.5, -20), (-11, -.5, -25)), 'l': (1, (13, -.5, -20), (11, -.5, -25))}


def arm_ik(side, target, pole):
    """Two-bone IK returning local upperarm/lowerarm rotations for a hand target.

    Valid because every joint's bind rotation is identity, so a joint's global
    rotation equals the product of the local rotations above it.
    """
    s, upper_vec, lower_vec = ARM_CHAIN[side]
    root = (s * 20, 0, 143)
    l1 = length(upper_vec)
    l2 = length(lower_vec)
    delta = sub(target, root)
    d = clamp(length(delta), abs(l1 - l2) + .8, l1 + l2 - .8)
    u = normalize(delta)
    ref = sub(pole, root)
    n = cross(u, ref)
    if length(n) < 1e-6:
        n = cross(u, (0, 0, 1))
    n = normalize(n)
    v = cross(n, u)
    cosa = clamp((l1 * l1 + d * d - l2 * l2) / (2 * l1 * d), -1, 1)
    a = math.acos(cosa)
    elbow = add(root, scale(add(scale(u, math.cos(a)), scale(v, math.sin(a))), l1))
    q_upper = shortest_arc(upper_vec, sub(elbow, root))
    q_lower_global = shortest_arc(lower_vec, sub(add(root, scale(u, d)), elbow))
    return q_upper, qmul(qconj(q_upper), q_lower_global)


def pose(bones, clip, time):
    """Joint-local rotations/translations. Idle and Walk are V2's motion verbatim."""
    q = {b['name']: (0., 0., 0., 1.) for b in bones}
    translations = {}
    if clip == 'Bind':
        return q, translations
    if clip in ('Idle', 'Walk'):
        period = 3.2 if clip == 'Idle' else 1.2
        phase = math.tau * time / period
        breathing = math.sin(phase) * (.007 if clip == 'Idle' else .003)
        q['spine_02'] = qaxis((1, 0, 0), breathing)
        q['neck_01'] = qaxis((0, 0, 1), math.sin(phase) * .009)
        q['head'] = qaxis((1, 0, 0), -breathing * .6)
        for s, side in [(-1, 'r'), (1, 'l')]:
            swing = math.sin(phase + (math.pi if s > 0 else 0)) * .12 if clip == 'Walk' else .02 * math.sin(phase)
            q['upperarm_' + side] = qmul(qaxis((0, 1, 0), s * math.radians(24)), qaxis((1, 0, 0), swing))
            q['lowerarm_' + side] = qaxis((1, 0, 0), -.045)
        if clip == 'Idle':
            q['mantle_front'] = qaxis((1, 0, 0), breathing * .25)
            q['mantle_back'] = qaxis((1, 0, 0), -breathing * .25)
            return q, translations
        pelvis_z = 95.8 - .25 * math.cos(phase * 2)
        translations['pelvis'] = (0, 0, pelvis_z)
        for s, side in [(-1, 'r'), (1, 'l')]:
            a = phase + (math.pi if s > 0 else 0)
            target_y = 16 * math.cos(a)
            lift = 5 * max(0, math.sin(a)) ** 2
            drop = (pelvis_z - 10) - (6 + lift)
            distance = math.hypot(target_y, drop)
            assert distance < 82
            angle = math.atan2(target_y, drop)
            knee = math.acos(distance / 82)
            thigh = angle - knee
            q['thigh_' + side] = qaxis((1, 0, 0), thigh)
            q['calf_' + side] = qaxis((1, 0, 0), 2 * knee)
            q['foot_' + side] = qaxis((1, 0, 0), -angle - knee)
            q['skirt_' + side] = qaxis((1, 0, 0), thigh * .25)
        q['mantle_front'] = qaxis((1, 0, 0), math.sin(phase) * .015)
        q['mantle_back'] = qaxis((1, 0, 0), math.sin(phase + .3) * .012)
        return q, translations

    # Original "taking a picture" clips: settle, hold, small hand-held drift.
    period = CLIPS[clip]
    phase = math.tau * time / period
    sway = math.sin(phase) * .9
    bob = math.sin(phase * 2 + .7) * .5
    q['spine_02'] = qaxis((1, 0, 0), .030 + .004 * math.sin(phase))
    q['spine_01'] = qaxis((1, 0, 0), .020)
    q['neck_01'] = qaxis((1, 0, 0), -.055 + .006 * math.sin(phase + .4))
    q['head'] = qaxis((1, 0, 0), -.075 + .005 * math.sin(phase))
    q['mantle_front'] = qaxis((1, 0, 0), .010 * math.sin(phase))
    q['mantle_back'] = qaxis((1, 0, 0), -.008 * math.sin(phase + .3))
    if clip == 'PhotoCamera':
        right = (-10.5 + sway * .35, -19.5 - bob * .3, 156.5 + bob * .5)
        left = (11.5 - sway * .35, -18.0 - bob * .3, 154.5 + bob * .5)
        pole_r = (-46, 6, 118)
        pole_l = (46, 6, 118)
    else:
        right = (-8.5 + sway * .5, -25.0, 137.0 + bob)
        left = (16.0, -12.0, 112.0)
        pole_r = (-44, 8, 112)
        pole_l = (44, 6, 108)
    for side, target, pole in (('r', right, pole_r), ('l', left, pole_l)):
        qu, ql = arm_ik(side, target, pole)
        q['upperarm_' + side] = qu
        q['lowerarm_' + side] = ql
    return q, translations


def global_pose(bones, clip, time):
    rotations, translations = pose(bones, clip, time)
    result = []
    for b in bones:
        localq = rotations[b['name']]
        localt = translations.get(b['name'], b['local_translation_cm'])
        if b['parent_index'] is None:
            result.append((localq, localt))
        else:
            pq, pt = result[b['parent_index']]
            result.append((qmul(pq, localq), add(pt, qrotate(pq, localt))))
    return result


def skinned_parts(parts, bones, index, clip, time):
    gp = global_pose(bones, clip, time)
    result = []
    for part in parts:
        vertices = []
        for p in part['vertices']:
            out = [0., 0., 0.]
            for j, w in influence(part, p, index):
                if w:
                    q, t = gp[j]
                    v = add(t, qrotate(q, sub(p, bones[j]['position_cm'])))
                    for k in range(3):
                        out[k] += v[k] * w
            vertices.append(tuple(out))
        result.append(dict(part, vertices=vertices))
    return result


# ---------------------------------------------------------------------------
# validation, normals, bounds
# ---------------------------------------------------------------------------


def normals(part):
    acc = [[0., 0., 0.] for _ in part['vertices']]
    v = part['vertices']
    for a, b, c in part['faces']:
        n = cross(sub(v[b], v[a]), sub(v[c], v[a]))
        for idx in (a, b, c):
            for k in range(3):
                acc[idx][k] += n[k]
    return [normalize(n) for n in acc]


def check(parts):
    import collections
    report = []
    for p in parts:
        v = p['vertices']
        edges = collections.Counter()
        volume = 0.0
        min_area = float('inf')
        assert all(math.isfinite(x) for a in v for x in a), p['name']
        for a, b, c in p['faces']:
            n = cross(sub(v[b], v[a]), sub(v[c], v[a]))
            area = length(n) / 2
            assert area > 1e-7, (p['name'], area)
            min_area = min(min_area, area)
            volume += dot(v[a], cross(v[b], v[c])) / 6
            for e in ((a, b), (b, c), (c, a)):
                edges[tuple(sorted(e))] += 1
        assert all(count == 2 for count in edges.values()), p['name']
        assert volume > 0, p['name']
        report.append({'name': p['name'], 'material': p['material'], 'vertices': len(v),
                       'triangles': len(p['faces']), 'closed_index_topology': True,
                       'min_triangle_area_cm2': min_area, 'signed_volume_cm3': volume})
    return report


def bounds(parts):
    v = [a for p in parts for a in p['vertices']]
    return {key: [fn(a[i] for a in v) for i in range(3)] for key, fn in [('min', min), ('max', max)]}


# ---------------------------------------------------------------------------
# GLB export (skinned, vertex-coloured, four clips)
# ---------------------------------------------------------------------------


class GLB:
    def __init__(self, generator):
        self.buffer = bytearray()
        self.doc = {'asset': {'version': '2.0', 'generator': generator}, 'buffers': [], 'bufferViews': [],
                    'accessors': [], 'nodes': [], 'meshes': [], 'skins': [], 'materials': [],
                    'animations': [], 'scenes': [], 'scene': 0}

    def accessor(self, rows, typ, component=5126, target=None, bounds_=False, normalized=False):
        sizes = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
        n = sizes[typ]
        flat = [x for row in rows for x in row] if n > 1 else rows
        while len(self.buffer) % 4:
            self.buffer.append(0)
        offset = len(self.buffer)
        fmt = {5126: 'f', 5123: 'H', 5125: 'I'}[component]
        self.buffer.extend(struct.pack('<' + fmt * len(flat), *flat))
        view = {'buffer': 0, 'byteOffset': offset, 'byteLength': len(self.buffer) - offset}
        if target:
            view['target'] = target
        vi = len(self.doc['bufferViews'])
        self.doc['bufferViews'].append(view)
        entry = {'bufferView': vi, 'componentType': component, 'count': len(rows), 'type': typ}
        if normalized:
            entry['normalized'] = True
        if bounds_:
            values = struct.unpack('<' + fmt * len(flat), self.buffer[offset:])
            entry['min'] = [min(values[k::n]) for k in range(n)]
            entry['max'] = [max(values[k::n]) for k in range(n)]
        ai = len(self.doc['accessors'])
        self.doc['accessors'].append(entry)
        return ai

    def save(self, path):
        self.doc['buffers'] = [{'byteLength': len(self.buffer)}]
        js = json.dumps(self.doc, separators=(',', ':')).encode('utf8')
        js += b' ' * ((-len(js)) % 4)
        binary = bytes(self.buffer) + b'\0' * ((-len(self.buffer)) % 4)
        path.write_bytes(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(js) + 8 + len(binary))
                         + struct.pack('<I4s', len(js), b'JSON') + js
                         + struct.pack('<I4s', len(binary), b'BIN\0') + binary)


def export_glb(path, variant, parts, bones, index, colours):
    asset = GLB('Original PilgrimRigV3 Python author (' + variant['id'] + ')')
    doc = asset.doc
    for i, b in enumerate(bones):
        node = {'name': b['name'], 'translation': gltf_vec(b['local_translation_cm'])}
        children = [j for j, k in enumerate(bones) if k['parent_index'] == i]
        if children:
            node['children'] = children
        doc['nodes'].append(node)
    matrices = []
    for b in bones:
        x, y, z = gltf_vec(b['position_cm'])
        matrices.append([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -x, -y, -z, 1])
    doc['skins'] = [{'name': 'OriginalPilgrimHumanoid', 'joints': list(range(len(bones))), 'skeleton': 0,
                     'inverseBindMatrices': asset.accessor(matrices, 'MAT4')}]
    primitives = []
    used = [m for m in ROUGHNESS if any(p['material'] == m for p in parts)]
    for mat in used:
        rgb = colours[mat]
        mi = len(doc['materials'])
        doc['materials'].append({'name': mat, 'pbrMetallicRoughness': {
            'baseColorFactor': list(rgb) + [1.], 'metallicFactor': 0., 'roughnessFactor': ROUGHNESS[mat]}})
        positions, norms, joints, weights, vcolours, indices = [], [], [], [], [], []
        for p in parts:
            if p['material'] != mat:
                continue
            offset = len(positions)
            positions.extend(gltf_vec(a) for a in p['vertices'])
            norms.extend([n[0], n[2], -n[1]] for n in normals(p))
            for point in p['vertices']:
                inf = influence(p, point, index)
                joints.append([j for j, _ in inf])
                weights.append([w for _, w in inf])
                vcolours.append(list(rgb) + [1.0])
            indices.extend(offset + i for face in p['faces'] for i in face)
        attrs = {'POSITION': asset.accessor(positions, 'VEC3', target=34962, bounds_=True),
                 'NORMAL': asset.accessor(norms, 'VEC3', target=34962),
                 'COLOR_0': asset.accessor(vcolours, 'VEC4', target=34962),
                 'JOINTS_0': asset.accessor(joints, 'VEC4', 5123, target=34962),
                 'WEIGHTS_0': asset.accessor(weights, 'VEC4', target=34962)}
        primitives.append({'attributes': attrs, 'indices': asset.accessor(indices, 'SCALAR', 5125, 34963),
                           'material': mi, 'mode': 4})
    doc['meshes'] = [{'name': 'SK_' + variant['id'], 'primitives': primitives}]
    doc['nodes'].append({'name': variant['id'] + '_Mesh', 'mesh': 0, 'skin': 0})
    doc['scenes'] = [{'name': 'PilgrimRigV3', 'nodes': [0, len(bones)]}]
    for clip, duration in CLIPS.items():
        count = round(duration * 30) + 1
        times = [i * duration / (count - 1) for i in range(count)]
        time_accessor = asset.accessor(times, 'SCALAR', bounds_=True)
        anim = {'name': ('A_Pilgrim_Original_' + clip) if clip in ('Idle', 'Walk') else ('A_Pilgrim_V3_' + clip),
                'samplers': [], 'channels': []}
        for j, b in enumerate(bones):
            values = [gltf_quat(pose(bones, clip, t)[0][b['name']]) for t in times]
            if all(v == [0., 0., 0., 1.] for v in values):
                continue
            si = len(anim['samplers'])
            anim['samplers'].append({'input': time_accessor, 'output': asset.accessor(values, 'VEC4'),
                                     'interpolation': 'LINEAR'})
            anim['channels'].append({'sampler': si, 'target': {'node': j, 'path': 'rotation'}})
        if clip == 'Walk':
            values = [gltf_vec(pose(bones, clip, t)[1]['pelvis']) for t in times]
            si = len(anim['samplers'])
            anim['samplers'].append({'input': time_accessor, 'output': asset.accessor(values, 'VEC3'),
                                     'interpolation': 'LINEAR'})
            anim['channels'].append({'sampler': si, 'target': {'node': 1, 'path': 'translation'}})
        doc['animations'].append(anim)
    doc['extras'] = {
        'variant': variant['id'],
        'provenance': 'Original geometry, weights and clips authored in this project; no downloaded or generated character.',
        'rig': 'Joint names, hierarchy and rest pose identical to PilgrimRigV2; existing Idle/Walk assets remain valid.',
        'coordinates': 'Author centimetres XYZ, front -Y, Z up; glTF metres X,Z,-Y.',
        'colour': 'Per-material baseColorFactor and matching COLOR_0 vertex colour carry the variant palette.'}
    asset.save(path)
    return doc


# ---------------------------------------------------------------------------
# OBJ export for the static crowd path
# ---------------------------------------------------------------------------


def write_obj(path, parts, colours, mtl_name, adapter=True):
    lines = ['# PilgrimRigV3 static crowd variant; centimetres, front -Y, Z up.',
             'mtllib ' + mtl_name]
    offset = 1
    for p in parts:
        lines += ['o ' + p['name'], 'usemtl ' + p['material'], 's 1']
        for x, y, z in p['vertices']:
            lines.append('v %.5f %.5f %.5f' % (x, -y if adapter else y, z))
        for x, y, z in normals(p):
            lines.append('vn %.6f %.6f %.6f' % (x, -y if adapter else y, z))
        for tri in p['faces']:
            order = (0, 2, 1) if adapter else (0, 1, 2)
            lines.append('f ' + ' '.join('%d//%d' % (offset + tri[k], offset + tri[k]) for k in order))
        offset += len(p['vertices'])
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')


def write_mtl(path, colours):
    out = []
    for name, rough in ROUGHNESS.items():
        rgb = colours[name]
        out += ['newmtl ' + name, 'Kd %.5f %.5f %.5f' % tuple(rgb), 'Ka 0 0 0',
                'Ks %.3f %.3f %.3f' % (((1 - rough) * .12,) * 3), 'Ns %.1f' % (4 + (1 - rough) * 90),
                'd 1', 'illum 2', '']
    path.write_text('\n'.join(out), encoding='ascii')


# ---------------------------------------------------------------------------
# preview renderer (dependency-free supersampled PNG)
# ---------------------------------------------------------------------------


def write_png(path, width, height, pixels):
    raw = b''.join(b'\0' + bytes(pixels[y * width * 3:(y + 1) * width * 3]) for y in range(height))

    def chunk(tag, data):
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xffffffff)
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))
    path.write_bytes(png)


def render(parts, colours, path, yaw, width=440, height=760, ss=2, top=176, scale=3.72):
    """Three-light shaded Z-buffer render; shows fold geometry, not a shader."""
    W, H = width * ss, height * ss
    bg = (26, 28, 31)
    pixels = bytearray(bg * (W * H))
    depth = [-1e9] * (W * H)
    key = normalize((-.45, -.78, .62))
    fill = normalize((.72, -.35, .18))
    rim = normalize((.15, .85, .35))
    cy = math.cos(yaw)
    sy = math.sin(yaw)
    sc = scale * ss
    for p in parts:
        v = p['vertices']
        ns = normals(p)
        projected = []
        for x, y, z in v:
            xx = x * cy - y * sy
            yy = x * sy + y * cy
            projected.append((W / 2 + xx * sc, (top - z) * sc + 24 * ss, -yy))
        rgb = colours[p['material']]
        shades = []
        for n in ns:
            nx = n[0] * cy - n[1] * sy
            ny = n[0] * sy + n[1] * cy
            nn = (nx, ny, n[2])
            s = (.26 + .84 * max(0, dot(nn, key)) + .28 * max(0, dot(nn, fill))
                 + .30 * max(0, dot(nn, rim)) ** 3)
            shades.append(s)
        for tri in p['faces']:
            a, b, c = [projected[i] for i in tri]
            area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if abs(area) < 1e-9:
                continue
            x0 = max(0, int(min(a[0], b[0], c[0])))
            x1 = min(W - 1, int(max(a[0], b[0], c[0])) + 1)
            y0 = max(0, int(min(a[1], b[1], c[1])))
            y1 = min(H - 1, int(max(a[1], b[1], c[1])) + 1)
            if x1 < x0 or y1 < y0:
                continue
            sh = [shades[i] for i in tri]
            for y in range(y0, y1 + 1):
                base = y * W
                for x in range(x0, x1 + 1):
                    u = ((b[0] - x) * (c[1] - y) - (b[1] - y) * (c[0] - x)) / area
                    if u < 0:
                        continue
                    vv = ((c[0] - x) * (a[1] - y) - (c[1] - y) * (a[0] - x)) / area
                    if vv < 0:
                        continue
                    w = 1 - u - vv
                    if w < 0:
                        continue
                    d = u * a[2] + vv * b[2] + w * c[2]
                    idx = base + x
                    if d <= depth[idx]:
                        continue
                    depth[idx] = d
                    shade = u * sh[0] + vv * sh[1] + w * sh[2]
                    o = idx * 3
                    for k in range(3):
                        pixels[o + k] = int(255 * min(1.0, rgb[k] * shade) ** (1 / 2.2))
    if ss == 1:
        write_png(path, W, H, pixels)
        return
    out = bytearray(width * height * 3)
    for y in range(height):
        for x in range(width):
            o = (y * width + x) * 3
            for k in range(3):
                total = 0
                for dy in range(ss):
                    row = (y * ss + dy) * W
                    for dx in range(ss):
                        total += pixels[(row + x * ss + dx) * 3 + k]
                out[o + k] = total // (ss * ss)
    write_png(path, width, height, out)


def lineup(entries, path, width=1620, height=560):
    """One contact sheet so the whole cast can be judged side by side."""
    cell = width // len(entries)
    ss = 2
    W, H = width * ss, height * ss
    pixels = bytearray((22, 24, 27) * (W * H))
    depth = [-1e9] * (W * H)
    key = normalize((-.45, -.78, .62))
    fill = normalize((.72, -.35, .18))
    for n, (parts, colours) in enumerate(entries):
        cx = (n + .5) * cell * ss
        sc = 2.72 * ss
        for p in parts:
            v = p['vertices']
            ns = normals(p)
            proj = [(cx + x * sc, (182 - z) * sc + 18 * ss, -y) for x, y, z in v]
            rgb = colours[p['material']]
            shades = [.20 + .86 * max(0, dot(nn, key)) + .26 * max(0, dot(nn, fill)) for nn in ns]
            for tri in p['faces']:
                a, b, c = [proj[i] for i in tri]
                area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                if abs(area) < 1e-9:
                    continue
                x0 = max(0, int(min(a[0], b[0], c[0])))
                x1 = min(W - 1, int(max(a[0], b[0], c[0])) + 1)
                y0 = max(0, int(min(a[1], b[1], c[1])))
                y1 = min(H - 1, int(max(a[1], b[1], c[1])) + 1)
                if x1 < x0 or y1 < y0:
                    continue
                sh = [shades[i] for i in tri]
                for y in range(y0, y1 + 1):
                    base = y * W
                    for x in range(x0, x1 + 1):
                        u = ((b[0] - x) * (c[1] - y) - (b[1] - y) * (c[0] - x)) / area
                        if u < 0:
                            continue
                        vv = ((c[0] - x) * (a[1] - y) - (c[1] - y) * (a[0] - x)) / area
                        if vv < 0:
                            continue
                        w = 1 - u - vv
                        if w < 0:
                            continue
                        d = u * a[2] + vv * b[2] + w * c[2]
                        idx = base + x
                        if d <= depth[idx]:
                            continue
                        depth[idx] = d
                        shade = u * sh[0] + vv * sh[1] + w * sh[2]
                        o = idx * 3
                        for k in range(3):
                            pixels[o + k] = int(255 * min(1.0, rgb[k] * shade) ** (1 / 2.2))
    out = bytearray(width * height * 3)
    for y in range(height):
        for x in range(width):
            o = (y * width + x) * 3
            for k in range(3):
                total = 0
                for dy in range(ss):
                    row = (y * ss + dy) * W
                    for dx in range(ss):
                        total += pixels[(row + x * ss + dx) * 3 + k]
                out[o + k] = total // (ss * ss)
    write_png(path, width, height, out)


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------


def decode_glb(path):
    """Independent reader: re-parse the file we just wrote, trusting nothing."""
    data = path.read_bytes()
    magic, version, total = struct.unpack_from('<4sII', data, 0)
    assert magic == b'glTF' and version == 2 and total == len(data), path.name
    offset = 12
    chunks = {}
    while offset < len(data):
        clen, ctype = struct.unpack_from('<I4s', data, offset)
        chunks[ctype] = data[offset + 8:offset + 8 + clen]
        offset += 8 + clen + (-clen) % 4
    doc = json.loads(chunks[b'JSON'].decode('utf8'))
    binary = chunks[b'BIN\0']
    assert len(doc['buffers']) == 1 and doc['buffers'][0]['byteLength'] <= len(binary)

    def read(ai):
        acc = doc['accessors'][ai]
        view = doc['bufferViews'][acc['bufferView']]
        fmt = {5126: 'f', 5123: 'H', 5125: 'I'}[acc['componentType']]
        n = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[acc['type']]
        base = view['byteOffset']
        values = struct.unpack_from('<' + fmt * (acc['count'] * n), binary, base)
        rows = [values[i * n:(i + 1) * n] for i in range(acc['count'])]
        if 'min' in acc:
            for k in range(n):
                column = [r[k] for r in rows]
                assert abs(min(column) - acc['min'][k]) < 1e-9, 'accessor min mismatch'
                assert abs(max(column) - acc['max'][k]) < 1e-9, 'accessor max mismatch'
        return rows
    return doc, read


def glb_decode_checks(path, bones, expected_triangles):
    """Verify the delivered bytes, not the in-memory model, before shipping."""
    doc, read = decode_glb(path)
    joint_count = len(doc['skins'][0]['joints'])
    assert joint_count == len(bones)
    assert [doc['nodes'][j]['name'] for j in doc['skins'][0]['joints']] == [b['name'] for b in bones]
    ibm = read(doc['skins'][0]['inverseBindMatrices'])
    for b, m in zip(bones, ibm):
        expected = gltf_vec(b['position_cm'])
        assert max(abs(m[12 + k] + expected[k]) for k in range(3)) < 1e-6, b['name']
    triangles = 0
    vertices = 0
    max_weight_error = 0.0
    for prim in doc['meshes'][0]['primitives']:
        positions = read(prim['attributes']['POSITION'])
        indices = [i[0] for i in read(prim['indices'])]
        assert len(indices) % 3 == 0 and max(indices) < len(positions)
        triangles += len(indices) // 3
        vertices += len(positions)
        joints = read(prim['attributes']['JOINTS_0'])
        weights = read(prim['attributes']['WEIGHTS_0'])
        colours = read(prim['attributes']['COLOR_0'])
        assert len(joints) == len(weights) == len(colours) == len(positions)
        assert max(max(j) for j in joints) < joint_count
        max_weight_error = max(max_weight_error, max(abs(sum(w) - 1.0) for w in weights))
    assert triangles == expected_triangles, (triangles, expected_triangles)
    assert max_weight_error < 1e-6
    animations = []
    for anim in doc['animations']:
        for channel in anim['channels']:
            sampler = anim['samplers'][channel['sampler']]
            assert (doc['accessors'][sampler['input']]['count']
                    == doc['accessors'][sampler['output']]['count'])
        animations.append({'name': anim['name'], 'channels': len(anim['channels']),
                           'samplers': len(anim['samplers'])})
    return {'file': path.name, 'bytes': path.stat().st_size, 'decodedTriangles': triangles,
            'decodedVertices': vertices, 'joints': joint_count,
            'jointNamesMatchRig': True, 'inverseBindMatricesMatchRestPose': True,
            'accessorBoundsVerified': True, 'maxWeightSumError': max_weight_error,
            'animations': animations,
            'limitation': 'Structural decode of the delivered bytes only; not the Khronos validator '
                          '(node.js is not installed here) and not a native Unreal import.'}


def deformation_checks(parts, bones, index):
    weights = [influence(p, v, index) for p in parts for v in p['vertices']]
    weight_error = max(abs(sum(w for _, w in inf) - 1) for inf in weights)
    assert weight_error < 1e-9
    bind = skinned_parts(parts, bones, index, 'Bind', 0)
    bind_error = max(abs(v[k] - w[k]) for p, q in zip(parts, bind)
                     for v, w in zip(p['vertices'], q['vertices']) for k in range(3))
    assert bind_error < 1e-9
    clips = []
    for clip, duration in CLIPS.items():
        first = skinned_parts(parts, bones, index, clip, 0)
        last = skinned_parts(parts, bones, index, clip, duration)
        loop = max(abs(v[k] - w[k]) for p, q in zip(first, last)
                   for v, w in zip(p['vertices'], q['vertices']) for k in range(3))
        samples = []
        for t in (0, duration * .25, duration * .5, duration * .75):
            deformed = skinned_parts(parts, bones, index, clip, t)
            assert all(math.isfinite(v) for p in deformed for a in p['vertices'] for v in a)
            soles = [v for p in deformed if p['name'].startswith('SandalSole') for v in p['vertices']]
            samples.append({'time_s': round(t, 4), 'bounds_cm': bounds(deformed),
                            'minimum_sole_z_cm': min(v[2] for v in soles)})
            assert min(v[2] for v in soles) > -.05, (clip, t)
        clips.append({'clip': clip, 'duration_s': duration, 'loop_vertex_error_cm': loop, 'samples': samples})
    return {'weight_sum_max_error': weight_error, 'bind_pose_error_cm': bind_error,
            'weighted_vertices': len(weights), 'clips': clips}


def build(previews=True, only=None):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'previews').mkdir(exist_ok=True)
    (OUT / 'meshes').mkdir(exist_ok=True)
    bones = skeleton()
    index = {b['name']: i for i, b in enumerate(bones)}
    rig_match = assert_rig_matches_v2(bones)
    manifest = {'status': 'offline_geometry_and_rig_validated_native_import_pending',
                'namespace': DEST, 'units': 'centimetres', 'front': '-Y', 'up': 'Z',
                'triangleBudgetPerCharacter': TRIANGLE_BUDGET,
                'rigCompatibility': rig_match,
                'clips': [{'name': ('A_Pilgrim_Original_' + c) if c in ('Idle', 'Walk') else ('A_Pilgrim_V3_' + c),
                           'duration_s': d,
                           'origin': 'reproduced from PilgrimRigV2 verbatim' if c in ('Idle', 'Walk')
                                     else 'new original clip authored for the photo request'}
                          for c, d in CLIPS.items()],
                'variants': [],
                'limits': [
                    'Offline authoring only: no Unreal launch, import, render, cook or performance result.',
                    'Vertex colours and flat PBR factors only; no UV unwrap, texture maps or normal maps.',
                    'Cloth folds are static modelled geometry, not simulation; no per-frame cloth solve.',
                    'Separate intersecting closed shells per part; the character is not a watertight union.',
                    'Clothing is an artistic pilgrim/visitor design, not kohanic vestments and not a halachic or historical ruling.',
                    'The photo clips are original authored motion; hand/prop contact was checked numerically, not visually in engine.']}
    sheet = []
    selected = [v for v in VARIANTS if not only or v['id'] in only]
    for variant in selected:
        parts = assembly(variant)
        colours = variant_materials(variant)
        report = check(parts)
        triangles = sum(r['triangles'] for r in report)
        assert triangles <= TRIANGLE_BUDGET, (variant['id'], triangles)
        checks = deformation_checks(parts, bones, index)
        glb = OUT / 'meshes' / (variant['id'] + '.glb')
        doc = export_glb(glb, variant, parts, bones, index, colours)
        decode = glb_decode_checks(glb, bones, triangles)
        # Static crowd copy: prop variants are baked in their photo pose so a
        # non-skeletal instance still reads as somebody taking a picture.
        static_clip = ('PhotoCamera' if variant['prop'] == 'camera'
                       else 'PhotoPhone' if variant['prop'] == 'phone' else 'Idle')
        static = skinned_parts(parts, bones, index, static_clip, 0.0)
        obj = OUT / 'meshes' / ('SM_' + variant['id'] + '.obj')
        mtl = OUT / 'meshes' / ('SM_' + variant['id'] + '.mtl')
        write_mtl(mtl, colours)
        write_obj(obj, static, colours, mtl.name)
        preview_clip = static_clip
        posed = static
        shots = []
        if previews:
            for name, yaw in (('front', 0.0), ('three-quarter', 0.62), ('side', math.pi / 2)):
                p = OUT / 'previews' / ('%s-%s.png' % (variant['id'], name))
                render(posed, colours, p, yaw)
                shots.append(str(p.relative_to(OUT)).replace('\\', '/'))
        sheet.append((posed, colours))
        manifest['variants'].append({
            'id': variant['id'], 'label': variant['label'], 'triangles': triangles,
            'vertices': sum(r['vertices'] for r in report), 'parts': len(report),
            'materials': sorted({r['material'] for r in report}),
            'palette': variant['palette'], 'skinTone': variant['skin_tone'],
            'prop': variant['prop'], 'headwear': variant['headwear'], 'beard': variant['beard'],
            'mantle': variant['mantle'],
            'recommendedActorScale': variant['actor_scale'],
            'recommendedIdleClip': ('A_Pilgrim_V3_' + preview_clip) if variant['prop'] else 'A_Pilgrim_Original_Idle',
            'skeletalFile': str(glb.relative_to(OUT)).replace('\\', '/'),
            'skeletalSha256': hashlib.sha256(glb.read_bytes()).hexdigest(),
            'staticFile': str(obj.relative_to(OUT)).replace('\\', '/'),
            'staticSha256': hashlib.sha256(obj.read_bytes()).hexdigest(),
            'staticMaterialFile': mtl.name,
            'staticBakedPose': static_clip,
            'boundsCm': bounds(parts),
            'animations': [a['name'] for a in doc['animations']],
            'deformation': checks,
            'glbDecodeChecks': decode,
            'previews': shots,
            'partBreakdown': sorted(report, key=lambda r: -r['triangles'])[:12]})
        print('%-32s %6d tris  %5d verts  %s' % (variant['id'], triangles,
              sum(r['vertices'] for r in report), glb.name), flush=True)
    if previews and len(sheet) > 1:
        lineup(sheet, OUT / 'previews' / 'lineup.png', width=190 * len(sheet))
        manifest['lineup'] = 'previews/lineup.png'
    manifest['totalTriangles'] = sum(v['triangles'] for v in manifest['variants'])
    manifest['scriptSha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (OUT / 'geometry-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true', help='author every variant')
    parser.add_argument('--no-previews', action='store_true')
    parser.add_argument('--only', nargs='*', help='restrict to named variant ids')
    args = parser.parse_args()
    if args.build:
        report = build(previews=not args.no_previews, only=set(args.only) if args.only else None)
        print(json.dumps({'variants': len(report['variants']),
                          'maxTriangles': max(v['triangles'] for v in report['variants']),
                          'output': str(OUT)}, indent=2))
    else:
        parser.print_help()
