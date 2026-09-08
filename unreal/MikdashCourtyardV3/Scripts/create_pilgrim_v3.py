"""PilgrimRigV3: original anatomical pilgrim/visitor mesh set, offline only.

Route (3) of SourceAssets/characters-review/PilgrimRigV3/options.md: improve the
project's own original character procedurally, with no third-party asset and no
account login. This script launches nothing; it writes geometry, previews and a
manifest into SourceAssets/characters-review/PilgrimRigV3/ only.

Why this rebuild exists
-----------------------
The first V3 pass fixed the fold geometry but kept a body that still read as a
balloon, and the numbers say why. Measured off the shipped SM_V3_Pilgrim_Man_A:

  head 16.1 cm across x 14.5 cm deep   - wider than deep, i.e. a ball. A real
                                         male head is 15.5 x 19.4.
  fingertips at 81.4 cm on a 179 cm    - 0.454 of stature; a real standing
    figure                               fingertip is at 0.377, mid-thigh. The
                                         upper arm was 23.9 cm against 33.3.
  hand 13.0 cm long, 7.4 cm across     - against 19.3 x 8.5. Mittens.
  foot 19.2 cm long                    - against 27.2. A child's foot.
  tunic shoulder 40.8 cm               - against a 46.4 cm bideltoid breadth.
  hem 117 cm around, 24% wider than    - a pencil skirt. Everything below the
    the hip                              sash was one smooth cone with no legs
                                         in it, which is the balloon.
  and two of the nine "variants" had BYTE-IDENTICAL vertex data.

All of those are fixed here against a cited anthropometric target (see
PROPORTIONS below), the figures are re-measured off the built mesh rather than
trusted, and the export refuses to write if any two variants are the same
person.

Rig compatibility
-----------------
Joint names, hierarchy and order are identical to PilgrimRigV2's 27-joint rig.
The arm and foot bones are deliberately LONGER - that is the fix - but they were
lengthened along their own unchanged rest directions, and the imported
A_Pilgrim_Original_Idle / _Walk clips are rotation curves plus one pelvis
translation track. A joint-local rotation curve does not depend on the child
bone's length, and pelvis did not move, so those clips remain valid motion.
assert_rig_matches_v2() asserts every part of that rather than asserting it.
Two original clips are added for the "people taking pictures" request:
A_Pilgrim_V3_PhotoCamera and A_Pilgrim_V3_PhotoPhone.

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
# Anthropometric target, as fractions of stature H, and where V3-a missed them.
#
# Source for the segment fractions: Drillis & Contini (1966), "Body Segment
# Parameters", reproduced as Figure 4.1 in D. A. Winter, *Biomechanics and Motor
# Control of Human Movement*, 4th ed., Wiley 2009, p. 83; head/hand/foot breadths
# and depths cross-checked against the 50th-percentile male of NASA-STD-3000
# Rev.B (1995) vol. I sec. 3.3. Artistic cross-check: the 7.5-head canon (Loomis,
# *Figure Drawing for All It's Worth*, 1943) and shoulders = 2 head-heights.
#
# Every number below is (fraction of stature, centimetres at H = 179).
PROPORTIONS = {
    'stature':                (1.0000, 179.0),
    'head_height_chin_crown': (0.1325, 23.7),   # 7.55 heads
    'head_breadth_x':         (0.0865, 15.5),
    'head_depth_y':           (0.1085, 19.4),   # V3-a shipped 14.5 -> beach ball
    'neck_diameter':          (0.0680, 12.2),
    'acromion_height':        (0.8180, 146.4),
    'bideltoid_breadth':      (0.2590, 46.4),   # V3-a tunic shoulder 40.8
    'glenohumeral_half_x':    (0.1145, 20.5),
    'upperarm_length':        (0.1860, 33.3),   # V3-a 23.9
    'forearm_length':         (0.1460, 26.1),   # V3-a 27.3 (ok)
    'hand_length':            (0.1080, 19.3),   # V3-a 13.0
    'hand_breadth':           (0.0475, 8.5),    # V3-a 7.4
    'wrist_height_standing':  (0.4850, 86.8),
    'dactylion_height':       (0.3770, 67.5),   # V3-a 81.4 -> doll arms
    'hip_joint_height':       (0.5300, 94.9),
    'knee_height':            (0.2850, 51.0),
    'foot_length':            (0.1520, 27.2),   # V3-a 19.2
    'foot_breadth':           (0.0550, 9.8),
}

# The V3-a figures, measured off SM_V3_Pilgrim_Man_A.obj on 8 Sep 2026 - which is
# the mesh the "balloons" complaint was actually looking at. Kept so the
# regression stays visible in the manifest and not only in a report.
V3A_MEASURED = {
    'stature': 179.4, 'head_height_chin_crown': 23.9, 'head_breadth_x': 16.1,
    'head_depth_y': 14.5, 'tunic_shoulder_breadth': 40.8, 'dactylion_height': 81.4,
    'hand_length': 13.0, 'hand_breadth': 7.4, 'foot_length': 19.2,
    'tunic_hem_breadth': 42.6, 'tunic_hem_circumference': 117.0,
}

# Arm chain. The A-pose direction is deliberately IDENTICAL to PilgrimRigV2's
# unit (0.470588, 0, -0.882353): the already-imported A_Pilgrim_Original_Idle /
# _Walk clips carry a +-24 deg rotation about Y on upperarm_* that was authored
# to bring THAT A-pose down to a relaxed hang. Rotation curves are independent
# of bone length, so lengthening the chain along the same direction keeps those
# clips valid motion while fixing the doll arms.
ARM_DIR = (0.470588235294118, 0.0, -0.882352941176471)
ARM_SHOULDER_X = 20.5
ARM_SHOULDER_Z = 143.0
ARM_UPPER = 32.0            # a shade under 33.3 so the wrist lands at 86 cm
ARM_FORE = 25.2
ARM_HAND = 19.3
ARM_PALM = 10.6             # stylion -> knuckle

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


def loft(rings, segments=32, radial=None, exponent=None, cap=True, zshift=None):
    """Stacked horizontal profiles; `radial(theta, z, level)` carries cloth folds.

    rings: (z, rx, ry, cx, cy). `exponent` < 1 squares the section off for a
    ribcage/shoulder read instead of a balloon ellipse. `zshift(theta, level)`
    breaks a level hem: a real robe rides up over the instep and drags behind.
    """
    vertices, faces = [], []
    for level, ring in enumerate(rings):
        z, rx, ry, cx, cy = ring
        e = exponent(z, level) if exponent else 1.0
        for i in range(segments):
            t = i * math.tau / segments
            f = radial(t, z, level) if radial else 0.0
            dz = zshift(t, level) if zshift else 0.0
            ct, st = math.cos(t), math.sin(t)
            if e != 1.0:
                ct = math.copysign(abs(ct) ** e, ct)
                st = math.copysign(abs(st) ** e, st)
            vertices.append((cx + (rx + f) * ct, cy + (ry + f) * st, z + dz))
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
             'Leather': .78, 'Hair': .88, 'Eyes': .30, 'Trim': .86, 'Prop': .42,
             'PropGlass': .10, 'Denim': .90, 'Iris': .28}

SKIN_TONES = {
    'olive': ((.455, .272, .173), (.070, .036, .020)),
    'tan': ((.520, .330, .215), (.085, .050, .028)),
    'deep': ((.330, .185, .112), (.045, .024, .014)),
    'fair': ((.610, .420, .310), (.140, .085, .045)),
    'olive-grey': ((.440, .268, .175), (.615, .600, .572)),
    'tan-grey': ((.510, .330, .222), (.680, .662, .630)),
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
    # Kohen white. Undyed fine linen (shesh) is an off-white with a warm cast,
    # not paper white; the sash and the migba'at are the same cloth.
    'kohen-white': {'Linen': (.905, .893, .862), 'Mantle': (.860, .848, .818),
                    'Headcloth': (.915, .903, .876), 'Sash': (.878, .866, .834),
                    'Trim': (.822, .806, .770)},
    'visitor-slate': {'Linen': (.585, .625, .662), 'Mantle': (.300, .340, .380),
                      'Headcloth': (.430, .470, .510), 'Sash': (.280, .300, .330),
                      'Trim': (.250, .272, .300), 'Denim': (.185, .215, .275)},
    'visitor-olive': {'Linen': (.700, .688, .630), 'Mantle': (.290, .320, .250),
                      'Headcloth': (.480, .500, .420), 'Sash': (.330, .300, .220),
                      'Trim': (.245, .260, .205), 'Denim': (.300, .285, .250)},
}

PROP_COLOURS = {'Prop': (.055, .058, .062), 'PropGlass': (.030, .045, .060)}


def variant_materials(variant):
    skin, hair = SKIN_TONES[variant['skin_tone']]
    colours = dict(GARMENT_PALETTES[variant['palette']])
    colours.update({'Skin': skin, 'Hair': hair,
                    'Eyes': (.760, .742, .715),          # sclera, never pure white
                    'Iris': (.135, .098, .062),
                    'Leather': (.140, .080, .042)})
    colours.update(PROP_COLOURS)
    colours.setdefault('Denim', tuple(v * .72 for v in colours['Mantle']))
    assert set(colours) >= set(ROUGHNESS), sorted(set(ROUGHNESS) - set(colours))
    return colours


# ---------------------------------------------------------------------------
# variants
#
# Nine genuinely different people, not three bodies in nine colours. V3-a shipped
# V3_Pilgrim_Man_A and V3_Pilgrim_Man_A_Bleached with BYTE-IDENTICAL vertex data
# and V3_Pilgrim_Man_A_Ochre as a second copy of Man_B - exactly the failure the
# crowd system hit earlier. build() now hashes the vertex block and compares
# silhouette signatures, and refuses to export if any two variants are close.
#
# `stance` is applied to the STATIC crowd bake only, never to the GLB clips, so
# every instanced figure stands differently while the skeletal clips stay
# byte-compatible with the imported A_Pilgrim_Original_Idle / _Walk. It never
# touches pelvis or the leg chain, so the feet stay planted on the ground.
# Angles are degrees.
# ---------------------------------------------------------------------------

VARIANTS = [
    dict(id='V3_Pilgrim_Man_Standard', label='Pilgrim man, standard build, short beard',
         dress='robe', girth=1.00, shoulder=1.00, age=.35, beard='short', headwear='cloth',
         mantle=True, mantle_hem=52.0, tunic_hem=7.0, prop=None, palette='linen-warm',
         skin_tone='olive', actor_scale=1.00, fold_seed=11,
         stance=dict(lean=2, bend=-3.0, twist=5, head_yaw=-11, head_tilt=2, sway=3,
                     arm_r=4, arm_l=-2, swing_r=-5, swing_l=4, elbow_r=-11, elbow_l=-5)),
    dict(id='V3_Pilgrim_Man_Heavy', label='Pilgrim man, heavy build, full beard, turban',
         dress='robe', girth=1.17, shoulder=1.07, age=.50, beard='full', headwear='turban',
         mantle=True, mantle_hem=50.0, tunic_hem=6.0, prop=None, palette='wool-umber',
         skin_tone='deep', actor_scale=1.04, fold_seed=23,
         stance=dict(lean=-1, bend=2.5, twist=-6, head_yaw=8, head_tilt=-3, sway=-4,
                     arm_r=9, arm_l=8, swing_r=3, swing_l=-3, elbow_r=-6, elbow_l=-14)),
    dict(id='V3_Pilgrim_Man_Elder', label='Elderly pilgrim man, stooped, long white beard',
         dress='robe', girth=0.89, shoulder=0.95, age=.90, beard='full', headwear='cloth',
         mantle=True, mantle_hem=56.0, tunic_hem=8.5, prop=None, palette='bleached',
         skin_tone='tan-grey', actor_scale=0.97, fold_seed=37,
         stance=dict(lean=11, bend=-1.5, twist=2, head_yaw=4, head_tilt=6, sway=1,
                     arm_r=-3, arm_l=-4, swing_r=8, swing_l=6, elbow_r=-22, elbow_l=-18)),
    dict(id='V3_Pilgrim_Woman_Young', label='Pilgrim woman, long shawl',
         dress='robe', girth=0.91, shoulder=0.89, age=.25, beard='none', headwear='shawl',
         mantle=True, mantle_hem=44.0, tunic_hem=4.5, prop=None, palette='indigo',
         skin_tone='tan', actor_scale=0.93, fold_seed=53,
         stance=dict(lean=1, bend=4.5, twist=-8, head_yaw=13, head_tilt=-4, sway=5,
                     arm_r=-4, arm_l=1, swing_r=2, swing_l=-6, elbow_r=-16, elbow_l=-9)),
    dict(id='V3_Pilgrim_Woman_Elder', label='Elderly pilgrim woman, heavier build, shawl',
         dress='robe', girth=1.05, shoulder=0.93, age=.85, beard='none', headwear='shawl',
         mantle=True, mantle_hem=46.0, tunic_hem=5.5, prop=None, palette='dusty-blue',
         skin_tone='olive-grey', actor_scale=0.90, fold_seed=71,
         stance=dict(lean=8, bend=-4.5, twist=6, head_yaw=-6, head_tilt=5, sway=-3,
                     arm_r=6, arm_l=-5, swing_r=-2, swing_l=7, elbow_r=-19, elbow_l=-24)),
    dict(id='V3_Pilgrim_Youth', label='Youth, knee-length tunic, no mantle',
         dress='robe', girth=0.80, shoulder=0.86, age=.05, beard='none', headwear='cap',
         mantle=False, tunic_hem=44.0, prop=None, palette='ochre',
         skin_tone='tan', actor_scale=0.84, fold_seed=89,
         stance=dict(lean=-3, bend=1.5, twist=-11, head_yaw=17, head_tilt=-6, sway=6,
                     arm_r=-7, arm_l=5, swing_r=-9, swing_l=9, elbow_r=-4, elbow_l=-26)),
    # Ordinary kohen in the white garments. Reference: the garment table in
    # SourceAssets/runtime-review/kohen-service/sources.md section 5, written
    # against the Temple Institute photographs - ketonet of white shesh, full
    # length with long sleeves; avnet, a long band wound at the waist; migba'at,
    # the ordinary kohen's wound white cap (distinct from the Kohen Gadol's
    # mitznefet). The me'il, ephod and choshen are Kohen Gadol garments and are
    # deliberately NOT modelled: sources.md records live disputes on all three.
    # This is an artistic reconstruction and not a halachic or historical ruling.
    dict(id='V3_Kohen_White', label='Ordinary kohen, white ketonet, avnet and migbaat',
         dress='kohen', girth=1.00, shoulder=1.02, age=.40, beard='short', headwear='migbaat',
         mantle=False, tunic_hem=5.0, flare=0.86, barefoot=True, prop=None,
         palette='kohen-white', skin_tone='olive', actor_scale=1.01, fold_seed=97,
         stance=dict(lean=0, bend=0.5, twist=2, head_yaw=-3, head_tilt=-2, sway=-1,
                     arm_r=1, arm_l=1, swing_r=-1, swing_l=-1, elbow_r=-7, elbow_l=-7)),
    dict(id='V3_Visitor_Camera', label='Modern visitor with a camera, short sleeves',
         dress='modern', sleeves='short', girth=0.97, shoulder=1.03, age=.30, beard='short',
         headwear='cap', mantle=False, tunic_hem=84.0, prop='camera', palette='visitor-olive',
         skin_tone='fair', actor_scale=1.02, fold_seed=103,
         stance=dict(lean=4, bend=-2.0, twist=3, head_yaw=-5, head_tilt=-4, sway=2,
                     arm_r=2, arm_l=-6, swing_r=-3, swing_l=5, elbow_r=-12, elbow_l=-30)),
    dict(id='V3_Visitor_Phone', label='Modern visitor with a phone, long sleeves',
         dress='modern', sleeves='long', girth=1.04, shoulder=0.98, age=.20, beard='none',
         headwear='none', mantle=False, tunic_hem=84.0, prop='phone', palette='visitor-slate',
         skin_tone='olive', actor_scale=0.96, fold_seed=109,
         stance=dict(lean=3, bend=3.5, twist=-4, head_yaw=9, head_tilt=-7, sway=-5,
                     arm_r=-2, arm_l=7, swing_r=6, swing_l=-8, elbow_r=-15, elbow_l=-11)),
]


# ---------------------------------------------------------------------------
# skeleton (identical names, hierarchy and rest positions to PilgrimRigV2)
# ---------------------------------------------------------------------------


def arm_frame(s):
    """(origin, along, across, front) for one arm, matching tube()'s own frame.

    `across` lies in the arm's own XZ plane and `front` is +Y, so a hand authored
    in this frame hangs the way a real one does whatever the A-pose angle is.
    """
    d = normalize((s * ARM_DIR[0], 0.0, ARM_DIR[2]))
    across = normalize(cross((0.0, 1.0, 0.0), d))
    front = cross(d, across)
    return (s * ARM_SHOULDER_X, 0.0, ARM_SHOULDER_Z), d, across, front


def arm_point(s, along, across=0.0, front=0.0):
    o, d, a, w = arm_frame(s)
    p = add(o, scale(d, along))
    p = add(p, scale(a, across))
    return add(p, scale(w, front))


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
        elbow = arm_point(s, ARM_UPPER)
        wrist = arm_point(s, ARM_UPPER + ARM_FORE)
        bone('clavicle_' + side, 'chest', (s * 11, 0, 145))
        bone('upperarm_' + side, 'clavicle_' + side, (s * ARM_SHOULDER_X, 0, ARM_SHOULDER_Z))
        bone('lowerarm_' + side, 'upperarm_' + side, (round(elbow[0], 3), -.5, round(elbow[2], 3)))
        bone('hand_' + side, 'lowerarm_' + side, (round(wrist[0], 3), -1., round(wrist[2], 3)))
        bone('thigh_' + side, 'pelvis', (s * 8, 0, 88))
        bone('calf_' + side, 'thigh_' + side, (s * 8, 0, 47))
        bone('foot_' + side, 'calf_' + side, (s * 8, 0, 6))
        bone('ball_' + side, 'foot_' + side, (s * 8, -11.5, 3))
        bone('skirt_' + side, 'pelvis', (s * 8, 0, 88))
    bone('mantle_front', 'chest', (0, -9, 143))
    bone('mantle_back', 'chest', (0, 11, 143))
    lookup = {b['name']: i for i, b in enumerate(bones)}
    for b in bones:
        b['parent_index'] = lookup[b['parent']] if b['parent'] else None
        b['local_translation_cm'] = (sub(b['position_cm'], bones[b['parent_index']]['position_cm'])
                                     if b['parent'] else b['position_cm'])
    return bones


# Joints whose rest position V3 deliberately moves, and why. Every other joint
# must still be byte-identical to PilgrimRigV2.
MOVED_JOINTS = {
    'clavicle_r': 'shoulder shelf raised toward the acromion height',
    'clavicle_l': 'shoulder shelf raised toward the acromion height',
    'upperarm_r': 'glenohumeral joint moved out to 0.1145 H',
    'upperarm_l': 'glenohumeral joint moved out to 0.1145 H',
    'lowerarm_r': 'upper arm lengthened 23.9 -> 32.0 cm along the SAME A-pose direction',
    'lowerarm_l': 'upper arm lengthened 23.9 -> 32.0 cm along the SAME A-pose direction',
    'hand_r': 'wrist put at 0.485 H so the fingertips reach mid-thigh',
    'hand_l': 'wrist put at 0.485 H so the fingertips reach mid-thigh',
    'ball_r': 'foot lengthened 19.2 -> 27.2 cm',
    'ball_l': 'foot lengthened 19.2 -> 27.2 cm',
}


def assert_rig_matches_v2(bones):
    """Prove the already-imported clips still play, and say exactly why.

    Those clips are rotation curves on named joints plus ONE translation track
    (pelvis, in Walk). A joint-local rotation curve is independent of the child
    bone's length, so lengthening a limb along its own rest direction cannot
    invalidate it. What WOULD invalidate it is a renamed joint, a reordered
    hierarchy, a changed rest DIRECTION, or a moved joint that carries a
    translation track. All four are asserted here.
    """
    if not V2_RIG.is_file():
        return {'compared': False, 'reason': 'PilgrimRigV2/rig-definition.json not present'}
    reference = json.loads(V2_RIG.read_text(encoding='utf-8-sig'))['bones']
    assert len(reference) == len(bones), 'joint count differs from PilgrimRigV2'
    moved = []
    for a, b in zip(reference, bones):
        assert a['name'] == b['name'], (a['name'], b['name'])
        assert a['parent'] == b['parent'], a['name']
        assert a['parent_index'] == b['parent_index'], a['name']
        if tuple(a['position_cm']) != tuple(b['position_cm']):
            assert a['name'] in MOVED_JOINTS, 'undeclared joint move: ' + a['name']
            moved.append({'joint': a['name'], 'v2_cm': list(a['position_cm']),
                          'v3_cm': [round(v, 3) for v in b['position_cm']],
                          'reason': MOVED_JOINTS[a['name']]})
    assert {m['joint'] for m in moved} == set(MOVED_JOINTS), 'MOVED_JOINTS table is stale'
    worst = 0.0
    for s, side in ((-1, 'r'), (1, 'l')):
        v2 = [r for r in reference if r['name'] == 'hand_' + side][0]
        v2_dir = normalize(sub(v2['position_cm'], (s * 20, 0, 143)))
        v3 = [r for r in bones if r['name'] == 'hand_' + side][0]
        v3_dir = normalize(sub(v3['position_cm'], (s * ARM_SHOULDER_X, 0, ARM_SHOULDER_Z)))
        angle = math.degrees(math.acos(clamp(dot(v2_dir, v3_dir), -1, 1)))
        assert angle < 1.5, 'arm A-pose direction rotated %.2f deg on %s' % (angle, side)
        worst = max(worst, angle)
    translated = set()
    for clip, duration in CLIPS.items():
        for t in (0.0, duration * .5):
            translated |= set(pose(bones, clip, t)[1])
    assert translated <= {'pelvis'}, translated
    assert 'pelvis' not in MOVED_JOINTS
    return {'compared': True, 'joints': len(bones), 'source': str(V2_RIG.relative_to(ROOT)),
            'identical_rest_pose': False,
            'movedJoints': moved,
            'jointNamesHierarchyAndOrderIdentical': True,
            'armAPoseDirectionDriftDeg': round(worst, 6),
            'clipsAnimateTranslationOnlyOn': sorted(translated),
            'existingClipsRemainValid': True,
            'why': ('Rotation curves are independent of bone length; the only translated '
                    'track is pelvis, which did not move; no joint was renamed, reordered '
                    'or re-aimed. A new Skeleton asset is still created on import because '
                    'UE stores a reference pose per Skeleton - see the release spec.')}


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
    if z > 136:
        return blend('chest', 'upperarm_' + side, (abs(x) - 15) / 10)
    if z > 104:
        return blend('lowerarm_' + side, 'upperarm_' + side, (z - 104) / 22)
    return blend('hand_' + side, 'lowerarm_' + side, (z - 90) / 13)


def forearm_skin(p):
    x, y, z = p
    side = 'r' if x < 0 else 'l'
    return blend('hand_' + side, 'lowerarm_' + side, (z - 89) / 9)


def trouser_skin(p):
    """Modern visitor trouser leg: thigh -> calf -> foot down the whole limb."""
    x, y, z = p
    side = 'r' if x < 0 else 'l'
    if z >= 88:
        return blend('pelvis', 'thigh_' + side, clamp((94 - z) / 6))
    if z >= 47:
        return blend('calf_' + side, 'thigh_' + side, (z - 47) / 41)
    return blend('foot_' + side, 'calf_' + side, (z - 8) / 18)


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


def fold_field(seed, base, harmonics=((6, 1.0), (9, .62), (3, .55), (14, .34))):
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
    """Flat over the chest, compressed under the sash, deepest toward the hem.

    The hem term is what stops the lower half reading as a smooth cone. V3-a
    peaked at ~2.8 cm of fold on a 21 cm radius; this peaks near 6 cm on 27.
    """
    if z > 146:
        return 0.06
    if z > 118:
        return .08 + .34 * smooth((146 - z) / 28)
    if z > 112:
        return .42 + .26 * smooth((118 - z) / 6)
    if z > 99:
        return .68 - .34 * smooth((112 - z) / 13) * smooth((z - 96) / 8)
    below = clamp((99 - z) / max(12.0, 99 - hem))
    return .70 + 1.35 * smooth(below)


# ---------------------------------------------------------------------------
# garment profile
# ---------------------------------------------------------------------------

# Half-width / half-depth of the clothed body, centimetres, at H = 179.
# Shoulder ring 22.2 -> 44.4 cm across under cloth; with the deltoid inside the
# sleeve the silhouette reads 46, which is the 0.259 H bideltoid breadth.
# Hem 27.5/20.2 -> a 150 cm hem circumference. V3-a shipped 117, a pencil skirt,
# which is the single reason the lower half read as one smooth balloon.
GARMENT_ANCHORS = [
    (0.0, 27.5, 20.2), (20.0, 23.8, 17.8), (40.0, 21.2, 15.9), (60.0, 19.4, 14.5),
    (76.0, 18.0, 13.4), (88.0, 17.2, 12.6), (99.0, 15.7, 11.4), (105.5, 14.0, 10.4),
    (111.0, 14.4, 10.7), (119.0, 16.3, 11.6), (127.0, 18.3, 12.4), (135.0, 20.3, 13.0),
    (140.0, 21.5, 13.1), (143.5, 22.2, 12.9), (147.0, 18.5, 11.2), (150.5, 12.1, 8.8),
    (153.0, 8.0, 6.9),
]


def anchor_at(z):
    if z <= GARMENT_ANCHORS[0][0]:
        return GARMENT_ANCHORS[0][1], GARMENT_ANCHORS[0][2]
    for (z0, a0, b0), (z1, a1, b1) in zip(GARMENT_ANCHORS, GARMENT_ANCHORS[1:]):
        if z <= z1:
            t = (z - z0) / (z1 - z0)
            return a0 + (a1 - a0) * t, b0 + (b1 - b0) * t
    return GARMENT_ANCHORS[-1][1], GARMENT_ANCHORS[-1][2]


def garment_rings(hem, girth, shoulder, flare=1.0, straight=False):
    """Rings from the hem up, monotone in z whatever the hem height.

    V3-a spliced fixed rings at z 24 and 42 under a hem list, so a short tunic
    (hem 42) produced a non-monotone stack and a visibly doubled hem on the
    youth. Sampling one analytic profile from the hem upward cannot do that.
    """
    def wh(z):
        rx, ry = anchor_at(z)
        if z < 99.0 and flare != 1.0:                     # kohen ketonet hangs straighter
            base_x, base_y = anchor_at(99.0)
            rx = base_x + (rx - base_x) * flare
            ry = base_y + (ry - base_y) * flare
        if straight and z < 119.0:                        # modern shirt: no hip flare
            ref_x, ref_y = anchor_at(119.0)
            rx = min(rx, ref_x * 1.02)
            ry = min(ry, ref_y * 1.04)
        return rx, ry

    rx0, ry0 = wh(hem)
    rings = [(hem, rx0 * .985, ry0 * .985), (hem + 2.6, rx0 * 1.035, ry0 * 1.035)]
    for z, _, _ in GARMENT_ANCHORS:
        if z > hem + 8.0:
            rings.append((z,) + wh(z))
    if rings[-1][0] < GARMENT_ANCHORS[-1][0] - .01:
        rings.append((GARMENT_ANCHORS[-1][0],) + wh(GARMENT_ANCHORS[-1][0]))
    return [(z, rx * girth * (shoulder if z > 130 else 1.0), ry * girth, 0.0, 0.0)
            for z, rx, ry in rings]


# ---------------------------------------------------------------------------
# head sculpt
# ---------------------------------------------------------------------------


# Head shape, the single loudest "balloon" tell in V3-a. That head measured
# 16.1 cm across and 14.5 cm front-to-back: wider than it was deep, i.e. a ball.
# A real male head is 15.5 across and 19.4 deep (NASA-STD-3000 50th percentile),
# so the fix is mostly one number - HEAD_RY - plus a flatter face plane, a real
# occiput and a jaw that tapers in both axes.
HEAD_RX = 7.75      # breadth 15.5
HEAD_RY = 9.65      # depth 19.3
HEAD_RZ = 11.85     # chin-to-crown 23.7 -> 7.55 heads at H = 179
HEAD_C = (0.0, -0.60, 166.40)


def head_sculpt(p):
    """Local-space skull sculpt. z runs -11.85 (chin) .. +11.85 (crown)."""
    x, y, z = p
    jaw = .68 + .32 * smooth((z + 10.4) / 9.6)
    x *= jaw
    x *= 1 - .06 * gauss(z, 4.8, 3.4)                                  # temple flat
    x *= 1 - .11 * gauss(z, -9.6, 3.0)                                 # chin narrows
    if y > 0:                                                          # cranium
        y *= .98
        y *= 1 - .20 * smooth((-z - 3.5) / 7.0)                        # occiput tucks under
        y -= .70 * gauss(z, 6.6, 4.2) * gauss(abs(x), 0, 6.2)
    else:                                                              # face
        f = -y / HEAD_RY
        y += 1.55 * f * (abs(x) / HEAD_RX) ** 2 * gauss(z, -1.0, 7.5)  # flatten the face plane
        y -= 1.15 * gauss(abs(x), 3.6, 2.4) * gauss(z, 2.6, 1.9)       # brow ridge
        y += 1.35 * gauss(abs(x), 3.3, 1.7) * gauss(z, 0.4, 1.6)       # eye socket
        y -= 1.05 * gauss(abs(x), 4.9, 2.0) * gauss(z, -2.4, 2.1)      # cheekbone
        y += .60 * gauss(abs(x), 3.6, 1.9) * gauss(z, -5.4, 2.2)       # cheek hollow
        y -= .55 * gauss(abs(x), 0, 3.2) * gauss(z, -6.8, 2.5)         # muzzle
        y -= .85 * gauss(abs(x), 0, 2.5) * gauss(z, -9.6, 2.3)         # chin
        y += .40 * gauss(abs(x), 0, 1.5) * gauss(z, -8.0, 1.2)         # sub-lip crease
        y += .28 * gauss(abs(x), 0, .9) * gauss(z, -5.6, 1.0)          # philtrum
    z -= .40 * gauss(abs(x), 0, 3.0) * gauss(z, -11.2, 2.0)
    return x, y, z


def head_front(x, z):
    """Sculpted face-surface local y at local (x, z). Features are hung off this
    rather than off hand-tuned constants, so changing HEAD_RY moves them all."""
    k = 1 - (x / HEAD_RX) ** 2 - (z / HEAD_RZ) ** 2
    if k <= 1e-6:
        return 0.0
    return head_sculpt((x, -HEAD_RY * math.sqrt(k), z))[1]


def face_point(x, z, out=0.0):
    """World point on the face at local (x, z), `out` cm proud of the surface."""
    return (HEAD_C[0] + x, HEAD_C[1] + head_front(x, z) - out, HEAD_C[2] + z)


def face_parts(add, variant):
    g = variant['girth']
    age = variant.get('age', 0.0)              # 0 young .. 1 elderly
    radii = (HEAD_RX * (.96 + .04 * g), HEAD_RY, HEAD_RZ)
    add('Head', 'Skin', ellipsoid(HEAD_C, radii, 40, 26, head_sculpt), head_skin)

    # Neck: a real 12.2 cm column with a visible length. V3-a had the column but
    # buried it under a collar at z 150.6 and a head cloth down to z 145, so the
    # figure read as a head sitting straight on a robe.
    n = 5.9 * (.95 + .05 * g)
    add('Neck', 'Skin', loft([(146.0, n * 1.10, n * 1.02, 0, .5), (150.0, n * .98, n * .90, 0, .2),
                              (154.0, n * .95, n * .88, 0, -.3), (158.0, n * 1.00, n * .94, 0, -.9),
                              (161.5, n * 1.12, n * 1.06, 0, -1.4)], 22), neck_skin)
    for side in (-1, 1):                                    # sternocleidomastoid
        add('SCM%d' % side, 'Skin', tube([(side * 4.6, -3.2, 147.4), (side * 3.2, -4.4, 152.0),
                                          (side * 2.0, -4.6, 156.5)],
                                         [(1.5, 1.2), (1.2, 1.0), (.85, .75)], 8), neck_skin)

    # Nose, hung off the sculpted face plane: root, bridge, ball, wings, columella.
    nose = []
    for zl, rx, ry, out in ((-3.5, 1.05, .70, .70), (-2.8, 1.60, 1.25, 1.45),
                            (-1.9, 1.75, 1.55, 1.85), (-0.6, 1.45, 1.30, 1.30),
                            (1.4, 1.10, .95, .60), (3.2, 1.25, .85, .10)):
        p = face_point(0.0, zl, out)
        nose.append((p[2], rx, ry, 0.0, p[1]))
    add('Nose', 'Skin', loft(nose, 20), head_skin)
    for side in (-1, 1):
        p = face_point(side * 1.55, -2.9, .55)
        add('Nostril%d' % side, 'Skin', ellipsoid((p[0], p[1], p[2]), (.78, .72, .60), 14, 9), head_skin)
        # Ear: long in z, deep in y, thin in x, set behind the head's mid-line.
        add('Ear%d' % side, 'Skin',
            ellipsoid((side * HEAD_RX * .93, HEAD_C[1] + 1.5, HEAD_C[2] - .4), (1.15, 1.85, 3.15), 16, 12,
                      lambda p: (p[0] * (1 - .40 * gauss(p[2], .2, 1.5)), p[1], p[2])), head_skin)
        e = face_point(side * 3.3, 1.1, -.55)               # set back inside the orbit
        add('Eye%d' % side, 'Eyes', ellipsoid(e, (1.28, .52, .44), 16, 10), head_skin)
        iris = (e[0] - side * .10, e[1] - .30, e[2] + .02)
        add('Iris%d' % side, 'Iris', ellipsoid(iris, (.52, .22, .52), 12, 8), head_skin)
        lid = face_point(side * 3.3, 2.05, .10)             # upper lid, breaks the stare
        add('Lid%d' % side, 'Skin', ellipsoid(lid, (1.55, .62, .58), 14, 9), head_skin)
        b0, b1, b2 = (face_point(side * 1.5, 3.0, .25), face_point(side * 3.2, 3.4, .30),
                      face_point(side * 5.0, 2.9, .20))
        add('Brow%d' % side, 'Hair', tube([b0, b1, b2], [.24, .36, .18], 8), head_skin)
        if age > .45:                                       # naso-labial fold
            f0, f1 = face_point(side * 1.9, -3.6, .05), face_point(side * 3.1, -6.4, .05)
            add('Fold%d' % side, 'Skin', tube([f0, f1], [(.34, .30), (.30, .26)], 6), head_skin)
    up = face_point(0.0, -5.0, .35)
    lo = face_point(0.0, -6.2, .30)
    add('UpperLip', 'Skin', ellipsoid(up, (2.50, .58, .46), 18, 10), head_skin)
    add('LowerLip', 'Skin', ellipsoid(lo, (2.25, .58, .50), 18, 10), head_skin)

    style = variant['beard']
    if style == 'none':
        hair_folds = fold_field(variant['fold_seed'] + 5, .34, ((9, 1.0), (17, .5), (5, .6)))
        cy = HEAD_C[1] + .5
        # Pulled inside the skull across the front (sin t < 0 is the face) so the
        # hairline stops at the temples instead of masking the brow and cheeks.
        def hair_radial(t, z, level):
            face = max(0.0, -math.sin(t)) ** 1.4
            return hair_folds(t, z, .8) - 2.6 * face * smooth((HEAD_C[2] + 8.0 - z) / 9.0)
        add('Hair', 'Hair', loft([(HEAD_C[2] - 1.6, 7.95, 9.40, 0, cy + .8),
                                  (HEAD_C[2] + 3.0, 8.30, 9.90, 0, cy + .5),
                                  (HEAD_C[2] + 6.6, 8.25, 9.80, 0, cy + .4),
                                  (HEAD_C[2] + 9.8, 7.05, 8.25, 0, cy + .5),
                                  (HEAD_C[2] + 11.9, 3.70, 4.30, 0, cy + .5)], 26,
                                 radial=hair_radial), head_skin)
        return
    # Beard: wraps the jaw and hangs off it. rx/ry follow the jaw taper so it
    # never floats away from the deeper head.
    beard_folds = fold_field(variant['fold_seed'] + 3, .30, ((11, 1.0), (19, .5), (7, .6)))
    top = HEAD_C[2] - 6.4                                   # jaw line
    bottom = HEAD_C[2] - (10.6 if style == 'short' else 17.2)
    rings = []
    steps = 7 if style == 'short' else 10
    for i in range(steps):
        u = i / (steps - 1)
        z = bottom + (top - bottom) * u
        k = smooth(u ** (1.0 if style == 'short' else .8))
        rings.append((z, 2.1 + 4.6 * k, 2.4 + 5.3 * k, 0.0, HEAD_C[1] + .30 - 1.15 * (1 - k)))
    add('Beard', 'Hair', loft(rings, 26, radial=lambda t, z, l: beard_folds(t, z, .8)), head_skin)
    m = face_point(0.0, -4.2, .45)
    add('Moustache', 'Hair', ellipsoid(m, (2.85, .80, .68), 16, 9), head_skin)
    for side in (-1, 1):
        add('Sideburn%d' % side, 'Hair',
            tube([(side * 7.2, HEAD_C[1] + 1.0, HEAD_C[2] + 1.8),
                  (side * 7.0, HEAD_C[1] + .1, HEAD_C[2] - 2.6),
                  (side * 5.9, HEAD_C[1] - .8, HEAD_C[2] - 6.2)],
                 [(1.05, 1.35), (1.05, 1.45), (1.30, 1.60)], 8), head_skin)


# ---------------------------------------------------------------------------
# garment + body assembly
# ---------------------------------------------------------------------------


def head_covering(add, variant):
    """Head coverings sized to the deeper skull, and cut so the NECK still shows.

    V3-a's drape reached z 145, i.e. down onto the shoulders, which removed the
    neck from the silhouette; the front of these stop at 154-158.
    """
    kind = variant['headwear']
    if kind == 'none':
        return
    folds = fold_field(variant['fold_seed'] + 9, .38, ((11, 1.0), (6, .7), (19, .35)))
    cy = HEAD_C[1] + .40
    if kind in ('turban', 'migbaat'):
        tall = kind == 'migbaat'
        add('TurbanCrown', 'Headcloth',
            ellipsoid((0, cy, HEAD_C[2] + (12.0 if tall else 10.6)),
                      (8.55, 10.45, 6.0 if tall else 5.0), 28, 12), head_skin)
        layers = 4 if tall else 3
        for layer in range(layers):
            pts = [(8.20 * math.cos(i * math.tau / 26), cy + 10.05 * math.sin(i * math.tau / 26),
                    HEAD_C[2] + 7.4 + layer * 2.05 + 1.0 * math.cos(i * math.tau / 26 + .5))
                   for i in range(27)]
            add('TurbanBand%d' % layer, 'Headcloth', tube(pts, [(.86, 1.24)] * 27, 8), head_skin)
        return
    if kind == 'cap':
        add('Cap', 'Headcloth', loft([(HEAD_C[2] + 5.4, 8.05, 9.75, 0, cy),
                                      (HEAD_C[2] + 7.1, 8.20, 9.95, 0, cy + .05),
                                      (HEAD_C[2] + 10.1, 7.30, 8.85, 0, cy + .1),
                                      (HEAD_C[2] + 12.2, 4.10, 4.90, 0, cy + .1)], 24,
                                     radial=lambda t, z, l: folds(t, z, .45)), head_skin)
        return
    long = kind == 'shawl'
    # Rim at +5.0 puts the cloth behind the hairline; V3-a's +2.1 crossed the
    # brow ridge, which is why every face read as a mask.
    add('HeadCap', 'Headcloth', loft([(HEAD_C[2] + 5.0, 8.55, 10.40, 0, cy),
                                      (HEAD_C[2] + 7.4, 8.70, 10.55, 0, cy + .05),
                                      (HEAD_C[2] + 9.1, 8.05, 9.75, 0, cy + .1),
                                      (HEAD_C[2] + 11.9, 5.35, 6.45, 0, cy + .1),
                                      (HEAD_C[2] + 13.0, 2.30, 2.75, 0, cy + .1)], 26,
                                     radial=lambda t, z, l: folds(t, z, .40)), head_skin)
    rows = 15 if long else 12
    cols = 21
    span = math.radians(126 if long else 112)
    grid = []
    for r in range(rows):
        u = r / (rows - 1)
        row = []
        for c in range(cols):
            t = c / (cols - 1)
            a = -span + 2 * span * t              # 0 = straight back, +-span = beside the face
            back = .5 + .5 * math.cos(a)          # 1 behind the head, 0 at the face
            # V3-a hung this to z 145 all the way round, which put cloth over the
            # jaw and deleted the neck. `face` is 1 straight behind the head and
            # 0 at the edge beside the cheek: the drape falls to the shoulder
            # blades behind and tucks up above the jaw at the face, so the jaw,
            # the beard and 6-9 cm of neck stay in the silhouette.
            face = 1.0 - abs(a) / span
            bottom = (124.0 if long else 136.0) + (46.0 if long else 32.0) * (1 - face) ** 1.4
            z = (HEAD_C[2] + 5.4) - ((HEAD_C[2] + 5.4) - bottom) * smooth(u)
            flare = (4.2 if long else 2.4) * smooth(u) * (.45 + .75 * back)
            rx = 8.70 + flare
            ry = 10.55 + flare * 1.10
            ripple = folds(a * 2.2 + u * 1.4, z, .60 + .90 * u)
            x = (rx + ripple) * math.sin(a)
            y = cy + (ry + ripple) * math.cos(a)
            row.append((x, y, z + ripple * .35))
        grid.append(row)
    add('HeadCloth', 'Headcloth', cloth_panel(grid, .34), head_skin)
    band = [(8.50 * math.cos(i * math.tau / 22), cy + 10.35 * math.sin(i * math.tau / 22),
             HEAD_C[2] + 7.4 + .8 * math.cos(i * math.tau / 22)) for i in range(23)]
    add('HeadBand', 'Trim', tube(band, [(.54, .82)] * 23, 8), head_skin)


def prop_parts(add, variant):
    """Camera / phone, rigidly skinned to the right hand.

    Anchored to the actual palm centre of the lengthened arm rather than a hard
    coded (-46.5, -4.6, 95.0), so the prop cannot drift off the hand again when
    the chain changes.
    """
    kind = variant['prop']
    if not kind:
        return
    hx, hy, hz = arm_point(-1, ARM_UPPER + ARM_FORE + ARM_PALM * .5, 0.0, -1.2)
    if kind == 'camera':
        cx, cy, cz = hx + 3.0, hy - 6.2, hz + 3.4
        add('CameraBody', 'Prop', box((cx, cy, cz), (5.6, 3.1, 3.7), 1.0), hand_skin)
        add('CameraLens', 'Prop', tube([(cx, cy - 2.7, cz), (cx, cy - 7.2, cz)],
                                       [(2.35, 2.35), (2.60, 2.60)], 14), hand_skin)
        add('CameraGlass', 'PropGlass', tube([(cx, cy - 7.25, cz), (cx, cy - 7.7, cz)],
                                             [(2.00, 2.00), (1.85, 1.85)], 14), hand_skin)
        add('CameraHump', 'Prop', box((cx, cy + .3, cz + 4.6), (2.0, 1.9, 1.3), .5), hand_skin)
    else:
        add('PhoneBody', 'Prop', box((hx + 1.0, hy - 2.6, hz + 2.6), (3.7, .55, 7.4), .6), hand_skin)
        add('PhoneScreen', 'PropGlass', box((hx + 1.0, hy - 3.25, hz + 2.6), (3.25, .12, 6.8), .4),
            hand_skin)


def arm_parts(add, variant, s):
    """One arm, authored in the arm's own frame.

    Everything is a distance `t` down the limb from the glenohumeral joint, so
    the whole arm scales with the anthropometric chain instead of a table of
    hand-fitted world coordinates. `across` is in the arm's own plane, `front`
    is +Y - which is what makes the hanging hand present its edge to camera and
    its palm to the thigh, the way a real one does.
    """
    g = variant['girth']
    sh = variant['shoulder']
    tag = 'R' if s < 0 else 'L'
    sleeve_folds = fold_field(variant['fold_seed'] + 2, .32, ((5, 1.0), (9, .55), (13, .35)))
    long_sleeve = variant['dress'] != 'modern' or variant.get('sleeves') == 'long'
    cuff_t = 53.0 if long_sleeve else 27.0

    def A(t, across=0.0, front=0.0):
        return arm_point(s, t, across, front)

    # Sleeve: buried in the torso at t=0, deltoid shelf at t=5..11, elbow at 32.
    sleeve = [(0.0, 4.8 * g, 4.6 * g), (5.0, 7.15 * g * sh, 6.85 * g), (11.0, 7.35 * g * sh, 7.05 * g),
              (18.0, 6.65 * g, 6.35 * g), (26.0, 6.05 * g, 5.80 * g), (32.0, 5.75 * g, 5.55 * g),
              (40.0, 5.20 * g, 5.00 * g), (47.0, 4.65 * g, 4.45 * g)]
    sleeve = [r for r in sleeve if r[0] <= cuff_t] + [(cuff_t, 4.35 * g, 4.15 * g)]
    add('Sleeve' + tag, 'Linen',
        tube([A(t) for t, _, _ in sleeve], [(rx, ry) for _, rx, ry in sleeve], 20,
             radial=lambda th, i, k=s: (sleeve_folds(th + k * .8, 140 - i * 8, .70 + .60 * i / 6)
                                        - .30 * math.cos(3 * th + 1.2) * gauss(i, 5.0, 1.2))),
        sleeve_skin)
    add('Cuff' + tag, 'Trim', tube([A(cuff_t - .9), A(cuff_t + 1.4)],
                                   [(4.65 * g, 4.45 * g)] * 2, 20), sleeve_skin)

    # Bare forearm below the cuff. Wrist half-thickness 2.7 = an 17 cm wrist.
    fore = [(cuff_t + .4, 3.55, 3.30), (ARM_UPPER + ARM_FORE - 4.0, 3.05, 2.80),
            (ARM_UPPER + ARM_FORE, 2.85, 2.65)]
    fore = [r for r in fore if r[0] >= cuff_t]
    if len(fore) >= 2:
        add('Forearm' + tag, 'Skin', tube([A(t) for t, _, _ in fore],
                                          [(rx, ry) for _, rx, ry in fore], 16), forearm_skin)

    # Hand. 19.3 cm stylion-to-dactylion, 8.5 cm across, palm edge-on to camera.
    w = ARM_UPPER + ARM_FORE
    knuckle = w + ARM_PALM
    add('Palm' + tag, 'Skin',
        tube([A(w - .6), A(w + 2.4), A(w + 6.6), A(knuckle), A(knuckle + 1.1)],
             [(1.75, 2.95), (1.95, 3.75), (2.10, 4.30), (1.95, 4.30), (1.55, 3.55)], 16),
        hand_skin)
    for i, (spread, flen, curl) in enumerate(((-3.05, 7.9, .5), (-1.05, 8.7, .6),
                                              (1.00, 8.1, .55), (2.90, 6.4, .45))):
        base = A(knuckle - .6, 0.0, spread)
        mid = A(knuckle + flen * .45, -curl * .6, spread * 1.02)
        tip = A(knuckle + flen, -curl * 1.9, spread * 1.05)
        add('Finger%s%d' % (tag, i), 'Skin',
            tube([base, mid, tip], [(.94, .88), (.84, .80), (.62, .58)], 8), hand_skin)
    add('Thumb' + tag, 'Skin',
        tube([A(w + 2.2, -.4, -3.4), A(w + 5.4, -1.2, -5.0), A(w + 8.4, -1.9, -5.6)],
             [(1.05, 1.00), (.94, .90), (.68, .64)], 8), hand_skin)


def leg_parts(add, variant, s):
    """Bare lower leg, foot and sandal - or trousers and a shoe for the moderns.

    Foot length 27.2 cm (0.152 H). V3-a's was 19.2, which is a child's foot on an
    adult and reads as a doll from any distance.
    """
    g = variant['girth']
    dress = variant['dress']
    tag = 'R' if s < 0 else 'L'
    hem = variant['tunic_hem']
    if dress == 'modern':
        trouser_folds = fold_field(variant['fold_seed'] + 13, .30, ((5, 1.0), (8, .5)))
        add('Trouser' + tag, 'Linen', loft([(3.4, 5.15 * g, 5.55 * g, s * 8, -3.4),
                                            (14.0, 5.55 * g, 5.95 * g, s * 8, -1.6),
                                            (30.0, 6.75 * g, 7.15 * g, s * 8, -.6),
                                            (44.0, 6.90 * g, 7.30 * g, s * 8, -.3),
                                            (52.0, 6.55 * g, 6.95 * g, s * 8, -.2),
                                            (70.0, 8.30 * g, 8.75 * g, s * 8, 0),
                                            (86.0, 9.70 * g, 10.15 * g, s * 8, 0),
                                            (97.0, 10.30 * g, 10.60 * g, s * 6, 0)], 24,
                                           radial=lambda t, z, l: trouser_folds(t, z, .45 + .55 * (z < 55))),
            trouser_skin)
        add('Shoe' + tag, 'Leather', ellipsoid((s * 8, -5.2, 3.6), (4.85, 13.2, 3.4), 22, 12,
            lambda p: (p[0] * (1 - .18 * gauss(p[1], -10.5, 4.5)), p[1],
                       p[2] * (1 - .34 * gauss(p[1], -10.0, 5.0)))), foot_skin)
        add('Sole' + tag, 'Leather', loft([(0, 4.55, 12.9, s * 8, -5.2), (.5, 5.00, 13.4, s * 8, -5.2),
                                           (1.6, 5.00, 13.4, s * 8, -5.2), (2.1, 4.70, 12.9, s * 8, -5.2)],
                                          24), foot_skin)
        return

    top = max(22.0, hem + 7.0)
    # Barefoot: the sole of the foot IS the ground plane, so the ankle drops by
    # the thickness of the sandal sole it no longer stands on.
    bare = bool(variant.get('barefoot'))
    ankle_z = 3.65 if bare else 4.70
    add('Shin' + tag, 'Skin', loft([(ankle_z - .9, 3.60 * g, 3.95 * g, s * 8, .4),
                                    (11.0, 4.25 * g, 4.55 * g, s * 8, .4),
                                    (top * .55, 5.20 * g, 5.55 * g, s * 8, .4),
                                    (top, 5.70 * g, 6.00 * g, s * 8, .4)], 20), leg_skin)
    add('Foot' + tag, 'Skin', ellipsoid((s * 8, -5.6, ankle_z), (4.90 * g, 13.60, 3.40), 22, 13,
        lambda p: (p[0] * (1 - .20 * gauss(p[1], -11.0, 4.5)), p[1],
                   p[2] * (1 - .32 * gauss(p[1], -10.5, 5.0)))), foot_skin)
    if bare:
        return
    add('SandalSole' + tag, 'Leather', loft([(0, 4.45 * g, 13.6, s * 8, -5.6),
                                             (.55, 4.95 * g, 14.2, s * 8, -5.6),
                                             (1.7, 4.95 * g, 14.2, s * 8, -5.6),
                                             (2.1, 4.60 * g, 13.6, s * 8, -5.6)], 26), foot_skin)
    for idx, y in enumerate((-13.2, -4.6)):
        add('SandalStrap%s%d' % (tag, idx), 'Leather',
            tube([(s * 8 - 4.3, y, 3.1), (s * 8 - 3.0, y, 6.8), (s * 8, y, 7.9),
                  (s * 8 + 3.0, y, 6.8), (s * 8 + 4.3, y, 3.1)], [(.74, .32)] * 5, 8), foot_skin)


def assembly(variant):
    parts = []
    g = variant['girth']
    sh = variant['shoulder']
    hem = variant['tunic_hem']
    dress = variant['dress']
    folds = fold_field(variant['fold_seed'], 1.30)
    mantle_folds = fold_field(variant['fold_seed'] + 1, .95, ((5, 1.0), (8, .6), (12, .35)))

    def add(name, material, mesh, skin):
        v, f = mesh
        volume = sum(dot(v[a], cross(v[b], v[c])) / 6 for a, b, c in f)
        if volume < 0:
            f = [(a, c, b) for a, b, c in f]
        parts.append({'name': name, 'material': material, 'vertices': v, 'faces': f, 'skin': skin})

    # ---- main garment shell. The load-bearing silhouette.
    flare = variant.get('flare', 1.0)
    body_hem = 88.0 if dress == 'modern' else hem
    rings = garment_rings(body_hem, g, sh, flare, straight=dress == 'modern')

    def tunic_radial(t, z, level):
        f = folds(t, z, tunic_amplitude(z, body_hem) * (.55 if dress == 'modern' else 1.0))
        if dress != 'modern' and z < 74.0:
            # Two columns under the cloth: pushed out over each leg (t = 0, pi)
            # and drawn in front and back between them. Without this the lower
            # half is a cone and reads as one solid volume.
            f += 2.9 * math.cos(2 * t) * smooth((74.0 - z) / 42.0)
        return f

    def tunic_exponent(z, level):
        bump = smooth((z - 92) / 14) * smooth((140 - z) / 16)
        return 1.0 - .17 * bump

    def hem_break(t, level):
        if level > 2 or dress == 'modern':
            return 0.0
        k = (1.0, .85, .35)[level]
        return k * (2.8 * max(0.0, -math.sin(t)) - 1.5 * max(0.0, math.sin(t)))

    add('Tunic', 'Linen', loft(rings, 76, radial=tunic_radial, exponent=tunic_exponent,
                               zshift=hem_break), torso_skin)

    def section(z):
        for (z0, rx0, ry0, _, _), (z1, rx1, ry1, _, _) in zip(rings, rings[1:]):
            if z <= z1:
                t = clamp((z - z0) / (z1 - z0))
                return rx0 + (rx1 - rx0) * t, ry0 + (ry1 - ry0) * t
        return rings[-1][1], rings[-1][2]

    if dress == 'modern':
        seat_folds = fold_field(variant['fold_seed'] + 17, .35, ((4, 1.0), (7, .5)))
        add('Seat', 'Denim', loft([(78.0, 14.6 * g, 11.2 * g, 0, 0), (88.0, 15.9 * g, 11.9 * g, 0, 0),
                                   (96.0, 16.0 * g, 11.9 * g, 0, 0), (101.0, 14.6 * g, 11.0 * g, 0, 0)],
                                  30, radial=lambda t, z, l: seat_folds(t, z, .5)), torso_skin)
        add('Belt', 'Leather', loft([(98.6, 14.8 * g, 11.1 * g, 0, 0), (99.8, 15.3 * g, 11.5 * g, 0, 0),
                                     (102.6, 15.3 * g, 11.5 * g, 0, 0), (103.6, 14.7 * g, 11.0 * g, 0, 0)],
                                    30), sash_skin)
    else:
        # ---- sash / avnet: one continuous band whose turns read as a wrap.
        kohen = dress == 'kohen'
        turns = 8 if kohen else 6
        span = (97.0, 116.0) if kohen else (100.0, 110.4)
        pads = ([1.7, 3.2, 3.9, 4.1, 4.1, 3.9, 3.2, 1.6] if kohen
                else [1.8, 3.4, 3.8, 3.8, 3.4, 1.7])

        def sash_radial(t, z, level):
            return (.42 * math.cos(t - (z - span[0]) * .82) + .22 * math.cos(11 * t + 1.1)
                    + .13 * math.cos(5 * t - 2.2))
        sash_rings = []
        for i in range(turns):
            z = span[0] + (span[1] - span[0]) * i / (turns - 1)
            rx, ry = section(z)
            sash_rings.append((z, rx + pads[i], ry + pads[i] * .82, 0, 0))
        add('Sash', 'Sash', loft(sash_rings, 36, radial=sash_radial), sash_skin)
        rx0, ry0 = section(span[0] + 4)
        add('SashTail', 'Sash', cloth_panel(
            [[(rx0 * .58 + c * .95 + r * .22, -(ry0 * .80 + 2.6) - .55 * math.sin(r * .5) - .30 * c,
               (span[0] + 2.0) - r * 3.2 + .55 * math.sin(c * 1.3 + r * .5)) for c in range(4)]
             for r in range(10)], .26), sash_skin)

    # Collar sits at 148.5 rather than V3-a's 150.6, so a real neck shows.
    add('Collar', 'Trim', loft([(148.2, 12.9 * g, 9.4 * g, 0, 0), (149.2, 13.4 * g, 9.8 * g, 0, 0),
                                (151.4, 8.6 * g, 7.3 * g, 0, 0), (152.2, 7.9 * g, 6.8 * g, 0, 0)],
                               26), torso_skin)

    # ---- over-mantle: ONE cloth over both shoulders, open at the front.
    if variant['mantle']:
        opening = math.radians(17)
        rows, cols = 22, 34
        top_z, bottom_z = 145.5, variant.get('mantle_hem', 52.0)
        grid = []
        for r in range(rows):
            u = r / (rows - 1)
            z = top_z - (top_z - bottom_z) * u
            rx, ry = section(z)
            ease = 1.15 + 2.55 * smooth(u)
            row = []
            for c in range(cols):
                t = c / (cols - 1)
                a = opening + t * (math.tau - 2 * opening)
                sa, ca = math.sin(a), math.cos(a)
                ripple = .75 + mantle_folds(a * 1.9 + u * 1.1, z, .50 + .95 * smooth(u))
                # Pulled hard to the shoulder at the top (u -> 0) so the cloth
                # follows the deltoid instead of standing off it.
                hug = .30 + .70 * smooth(u * 2.2)
                lateral = rx * sh * (1 - .13 * abs(sa)) + ease * (.30 + .70 * ca * ca) * hug
                depth = ry + (ease + .5) * hug
                x = (lateral + ripple * hug) * sa
                y = -(depth + ripple * hug) * ca - .5
                row.append((x, y, z + ripple * .30 - 1.2 * math.exp(-(min(t, 1 - t) / .11) ** 2) * (1 - u)))
            grid.append(row)
        add('Mantle', 'Mantle', cloth_panel(grid, .44),
            lambda p: (mantle_back_skin(p) if p[1] > 0 else mantle_front_skin(p)))
        add('MantleHem', 'Trim', tube(grid[-1], [(.66, .66)] * cols, 6), mantle_back_skin)
        for s, edge_index in ((-1, 0), (1, cols - 1)):
            column = [grid[r][edge_index] for r in range(rows)]
            add('MantleEdge%d' % s, 'Trim', tube(column, [(.50, .50)] * rows, 6), mantle_front_skin)

    for s in (-1, 1):
        arm_parts(add, variant, s)
    for s in (-1, 1):
        leg_parts(add, variant, s)

    face_parts(add, variant)
    head_covering(add, variant)
    prop_parts(add, variant)
    return parts


# ---------------------------------------------------------------------------
# clips (Idle/Walk reproduced from PilgrimRigV2; two original photo clips added)
# ---------------------------------------------------------------------------

CLIPS = {'Idle': 3.2, 'Walk': 1.2, 'PhotoCamera': 4.0, 'PhotoPhone': 3.6}
ARM_CHAIN = {side: (s,
                    tuple(round(v, 4) for v in sub(arm_point(s, ARM_UPPER),
                                                   (s * ARM_SHOULDER_X, 0., ARM_SHOULDER_Z))),
                    tuple(round(v, 4) for v in sub(arm_point(s, ARM_UPPER + ARM_FORE),
                                                   arm_point(s, ARM_UPPER))))
             for s, side in ((-1, 'r'), (1, 'l'))}


def arm_ik(side, target, pole):
    """Two-bone IK returning local upperarm/lowerarm rotations for a hand target.

    Valid because every joint's bind rotation is identity, so a joint's global
    rotation equals the product of the local rotations above it.
    """
    s, upper_vec, lower_vec = ARM_CHAIN[side]
    root = (s * ARM_SHOULDER_X, 0, ARM_SHOULDER_Z)
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


def apply_stance(q, stance):
    """Per-variant standing posture, multiplied on top of a clip's own rotations.

    Deliberately never touches pelvis, thigh_*, calf_* or foot_*: those carry the
    figure's ground contact, and a naive weight shift there floats the feet. The
    lean, side-bend, twist, head direction and per-arm hang are what actually
    separate two figures in a line-up at conversational distance.
    """
    if not stance:
        return q
    r = math.radians

    def mul(name, rot):
        q[name] = qmul(q[name], rot)

    mul('spine_01', qmul(qaxis((1, 0, 0), r(stance.get('lean', 0)) * .55),
                         qaxis((0, 1, 0), r(stance.get('bend', 0)) * .6)))
    mul('spine_02', qmul(qaxis((1, 0, 0), r(stance.get('lean', 0)) * .45),
                         qmul(qaxis((0, 1, 0), r(-stance.get('bend', 0)) * .35),
                              qaxis((0, 0, 1), r(stance.get('twist', 0)) * .5))))
    mul('chest', qaxis((0, 0, 1), r(stance.get('twist', 0)) * .5))
    mul('neck_01', qmul(qaxis((0, 0, 1), r(stance.get('head_yaw', 0)) * .4),
                        qaxis((1, 0, 0), r(-stance.get('lean', 0)) * .5)))
    mul('head', qmul(qaxis((0, 0, 1), r(stance.get('head_yaw', 0)) * .6),
                     qaxis((0, 1, 0), r(stance.get('head_tilt', 0)))))
    for s, side in ((-1, 'r'), (1, 'l')):
        key = 'r' if s < 0 else 'l'
        mul('clavicle_' + side, qaxis((0, 1, 0), r(s * stance.get('sway', 0)) * .3))
        mul('upperarm_' + side, qmul(qaxis((0, 1, 0), r(s * stance.get('arm_' + key, 0))),
                                     qaxis((1, 0, 0), r(stance.get('swing_' + key, 0)))))
        mul('lowerarm_' + side, qaxis((1, 0, 0), r(stance.get('elbow_' + key, 0))))
        mul('skirt_' + side, qaxis((1, 0, 0), r(stance.get('swing_' + key, 0)) * .25))
    mul('mantle_front', qaxis((1, 0, 0), r(stance.get('lean', 0)) * .3))
    mul('mantle_back', qaxis((1, 0, 0), r(-stance.get('lean', 0)) * .2))
    return q


def pose(bones, clip, time, stance=None):
    """Joint-local rotations/translations. Idle and Walk are V2's motion verbatim."""
    q = {b['name']: (0., 0., 0., 1.) for b in bones}
    translations = {}
    if clip == 'Bind':
        return apply_stance(q, stance), translations
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
            return apply_stance(q, stance), translations
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
        return apply_stance(q, stance), translations

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
        # A two-handed grip: the right hand carries the body at eye height and
        # the LEFT crosses under the lens to support it. V3-a mirrored both hands
        # to either cheek, which read as covering the eyes, not photographing.
        right = (-11.5 + sway * .35, -27.0 - bob * .3, 148.0 + bob * .5)
        left = (3.5 - sway * .3, -32.0 - bob * .3, 141.0 + bob * .5)
        pole_r = (-50, 12, 108)
        pole_l = (44, 14, 104)
    else:
        right = (-9.5 + sway * .5, -28.0, 134.0 + bob)
        left = (17.5, -13.0, 110.0)
        pole_r = (-44, 8, 112)
        pole_l = (44, 6, 108)
    for side, target, pole in (('r', right, pole_r), ('l', left, pole_l)):
        qu, ql = arm_ik(side, target, pole)
        q['upperarm_' + side] = qu
        q['lowerarm_' + side] = ql
    # Photo clips drive the arms by IK to the prop; stance must not fight that,
    # so only the spine, neck, head and cloth carry it here.
    photo_stance = {k: v for k, v in (stance or {}).items()
                    if not k.startswith(('arm_', 'swing_', 'elbow_'))}
    return apply_stance(q, photo_stance), translations


def global_pose(bones, clip, time, stance=None):
    rotations, translations = pose(bones, clip, time, stance)
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


def skinned_parts(parts, bones, index, clip, time, stance=None):
    gp = global_pose(bones, clip, time, stance)
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


def measure(parts):
    """Read the anthropometry back off the built mesh, not off the source numbers.

    This is the check that would have caught V3-a: every one of these was wrong
    on the shipped mesh and none of them was ever measured.
    """
    by = {p['name']: p['vertices'] for p in parts}
    allv = [v for p in parts for v in p['vertices']]
    out = {}
    out['stature'] = max(v[2] for v in allv)
    head = by.get('Head', [])
    if head:
        out['head_height_chin_crown'] = max(v[2] for v in head) - min(v[2] for v in head)
        out['head_breadth_x'] = max(v[0] for v in head) - min(v[0] for v in head)
        out['head_depth_y'] = max(v[1] for v in head) - min(v[1] for v in head)
        out['heads_tall'] = out['stature'] / out['head_height_chin_crown']
    band = [v for v in allv if 138.0 < v[2] < 149.0]
    if band:
        out['shoulder_breadth'] = max(v[0] for v in band) - min(v[0] for v in band)
    tips = [v for name, vs in by.items() if name.startswith('Finger') for v in vs]
    if tips:
        out['dactylion_height'] = min(v[2] for v in tips)
    palm = by.get('PalmL') or by.get('PalmR')
    if palm and tips:
        wrist = max(v[2] for v in palm)
        out['hand_length'] = wrist - min(v[2] for v in tips)
        out['hand_breadth'] = max(v[1] for v in palm) - min(v[1] for v in palm)
    foot = by.get('FootL') or by.get('ShoeL')
    if foot:
        out['foot_length'] = max(v[1] for v in foot) - min(v[1] for v in foot)
        out['foot_breadth'] = max(v[0] for v in foot) - min(v[0] for v in foot)
    neck = by.get('Neck')
    if neck:
        out['neck_diameter'] = max(v[0] for v in neck) - min(v[0] for v in neck)
        out['neck_visible_height'] = 0.0
        covered = [v[2] for name, vs in by.items()
                   if name in ('Collar', 'HeadCloth', 'HeadCap', 'Cap', 'TurbanCrown', 'Beard')
                   for v in vs]
        if covered:
            lowest_cover = min(v for v in covered if v > 140.0) if any(v > 140 for v in covered) else 161.0
            out['neck_visible_height'] = max(0.0, min(161.0, lowest_cover) - 149.0)
    hem = [v for v in by.get('Tunic', []) if v[2] < min(x[2] for x in by.get('Tunic', [(0, 0, 0)])) + 4.0]
    if hem:
        a = (max(v[0] for v in hem) - min(v[0] for v in hem)) / 2
        b = (max(v[1] for v in hem) - min(v[1] for v in hem)) / 2
        out['tunic_hem_breadth'] = a * 2
        out['tunic_hem_circumference'] = math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))
    return {k: round(v, 2) for k, v in out.items()}


def silhouette(parts, bands=26):
    """Outline signature: half-width and half-depth in `bands` height slices.

    A hash alone would pass two figures that differ by a micron. This is what
    two variants must differ by in centimetres before the export is allowed.
    """
    allv = [v for p in parts for v in p['vertices']]
    top = max(v[2] for v in allv)
    sig = []
    for i in range(bands):
        lo = top * i / bands
        hi = top * (i + 1) / bands
        slab = [v for v in allv if lo <= v[2] < hi]
        if slab:
            sig.append(max(abs(v[0]) for v in slab))
            sig.append(max(abs(v[1]) for v in slab))
        else:
            sig.extend((0.0, 0.0))
    return sig


def silhouette_distance(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


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
            soles = [v for p in deformed
                     if p['name'].startswith(('SandalSole', 'Sole', 'Shoe', 'Foot'))
                     for v in p['vertices']]
            samples.append({'time_s': round(t, 4), 'bounds_cm': bounds(deformed),
                            'minimum_sole_z_cm': min(v[2] for v in soles)})
            assert min(v[2] for v in soles) > -.05, (clip, t)
        clips.append({'clip': clip, 'duration_s': duration, 'loop_vertex_error_cm': loop, 'samples': samples})
    return {'weight_sum_max_error': weight_error, 'bind_pose_error_cm': bind_error,
            'weighted_vertices': len(weights), 'clips': clips}


MIN_SILHOUETTE_DISTANCE_CM = 0.90


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
                'proportionTarget': {k: {'fractionOfStature': f, 'cm_at_H179': c}
                                     for k, (f, c) in PROPORTIONS.items()},
                'proportionSource': ('Drillis & Contini (1966) segment fractions as reproduced in '
                                     'Winter, Biomechanics and Motor Control of Human Movement, '
                                     '4th ed. 2009, fig. 4.1 p.83; breadths/depths cross-checked '
                                     'against the 50th-percentile male of NASA-STD-3000 Rev.B '
                                     'vol.I sec.3.3; artistic cross-check the 7.5-head canon '
                                     '(Loomis 1943, shoulders = 2 head-heights).'),
                'previousVersionMeasured': V3A_MEASURED,
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
                    'Stylised-realistic, not photoreal: no facial animation, no finger rig, no hair strands, '
                    'no skin shading model. At two metres from camera a MetaHuman will still be obviously better.',
                    'Per-variant stance is baked into the STATIC crowd copy only; the skeletal meshes are '
                    'unposed and play the shared clips.',
                    'The pilgrim clothing is an artistic design and is not kohanic vestments.',
                    'V3_Kohen_White is an artistic reconstruction of the ordinary kohen white garments '
                    '(ketonet, avnet, migbaat) following the garment table in '
                    'SourceAssets/runtime-review/kohen-service/sources.md section 5. The Kohen Gadol '
                    'garments (me il, ephod, choshen, mitznefet, tzitz) are NOT modelled - that file '
                    'records live disputes on their reconstruction. Nothing here is a halachic or '
                    'historical ruling, and no rabbinic review is claimed.',
                    'Bare feet on the kohen variant are an authored design choice flagged for review; '
                    'sources.md does not cover footwear.',
                    'The photo clips are original authored motion; hand/prop contact was checked '
                    'numerically, not visually in engine.']}
    sheet = []
    selected = [v for v in VARIANTS if not only or v['id'] in only]
    fingerprints = {}
    signatures = {}
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
        # Static crowd copy: prop variants baked in their photo pose, everyone
        # else in their own stance, so an instanced crowd is not nine clones.
        static_clip = ('PhotoCamera' if variant['prop'] == 'camera'
                       else 'PhotoPhone' if variant['prop'] == 'phone' else 'Idle')
        static = skinned_parts(parts, bones, index, static_clip, 0.0, variant.get('stance'))
        ground = [v[2] for p in static
                  if p['name'].startswith(('SandalSole', 'Sole', 'Shoe', 'Foot'))
                  for v in p['vertices']]
        assert ground and -0.6 < min(ground) < 0.9, (variant['id'], min(ground) if ground else None)
        measured = measure(static)
        signatures[variant['id']] = silhouette(static)
        fingerprints[variant['id']] = hashlib.sha256(
            b''.join(struct.pack('<3f', *v) for p in static for v in p['vertices'])).hexdigest()
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
            'dress': variant['dress'], 'palette': variant['palette'],
            'skinTone': variant['skin_tone'], 'age': variant.get('age'),
            'girth': variant['girth'], 'shoulder': variant['shoulder'],
            'prop': variant['prop'], 'headwear': variant['headwear'], 'beard': variant['beard'],
            'mantle': variant['mantle'],
            'measuredCm': measured,
            'staticVertexFingerprint': fingerprints[variant['id']],
            'recommendedActorScale': variant['actor_scale'],
            'recommendedIdleClip': ('A_Pilgrim_V3_' + preview_clip) if variant['prop'] else 'A_Pilgrim_Original_Idle',
            'skeletalFile': str(glb.relative_to(OUT)).replace('\\', '/'),
            'skeletalSha256': hashlib.sha256(glb.read_bytes()).hexdigest(),
            'staticFile': str(obj.relative_to(OUT)).replace('\\', '/'),
            'staticSha256': hashlib.sha256(obj.read_bytes()).hexdigest(),
            'staticMaterialFile': mtl.name,
            'staticBakedPose': static_clip,
            'staticBakedStance': variant.get('stance'),
            'boundsCm': bounds(parts),
            'animations': [a['name'] for a in doc['animations']],
            'deformation': checks,
            'glbDecodeChecks': decode,
            'previews': shots,
            'partBreakdown': sorted(report, key=lambda r: -r['triangles'])[:12]})
        print('%-30s %6d tris %5d verts  %.2f heads  shoulder %.1f  fingertip %.1f'
              % (variant['id'], triangles, sum(r['vertices'] for r in report),
                 measured.get('heads_tall', 0), measured.get('shoulder_breadth', 0),
                 measured.get('dactylion_height', 0)), flush=True)

    # ---- distinctness gate -------------------------------------------------
    # V3-a shipped Man_A and Man_A_Bleached with identical vertex data. Fail the
    # export rather than let that reach the crowd again.
    ids = [v['id'] for v in manifest['variants']]
    pairs = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if fingerprints[a] == fingerprints[b]:
                raise AssertionError('identical geometry: %s == %s' % (a, b))
            d = silhouette_distance(signatures[a], signatures[b])
            pairs.append({'a': a, 'b': b, 'silhouetteDistanceCm': round(d, 3)})
    if pairs:
        worst = min(pairs, key=lambda p: p['silhouetteDistanceCm'])
        if worst['silhouetteDistanceCm'] < MIN_SILHOUETTE_DISTANCE_CM:
            raise AssertionError('variants too alike: %s vs %s at %.3f cm (min %.2f)'
                                 % (worst['a'], worst['b'], worst['silhouetteDistanceCm'],
                                    MIN_SILHOUETTE_DISTANCE_CM))
        manifest['distinctness'] = {
            'uniqueVertexFingerprints': len(set(fingerprints.values())) == len(fingerprints),
            'minimumSilhouetteDistanceCm': worst['silhouetteDistanceCm'],
            'thresholdCm': MIN_SILHOUETTE_DISTANCE_CM,
            'closestPair': [worst['a'], worst['b']],
            'method': ('26 height bands per figure, max |x| and max |y| in each, mean absolute '
                       'difference between two figures; plus a sha256 of the packed static '
                       'vertex block. Both must pass or nothing is written.'),
            'pairs': sorted(pairs, key=lambda p: p['silhouetteDistanceCm'])[:12]}

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
