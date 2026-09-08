"""BirdsV1 - low-poly pose meshes for the ambient Jerusalem bird layer.

AUTHORED_OFFLINE_SOURCE. This module never imports `unreal`, never touches Content/, never
opens a map. `--export` writes SourceAssets/birds-review/BirdsV1/: one OBJ per species per
wing pose, a geometry-manifest.json with numeric readback, a species.json carrying every size
figure and its citation, and a flat-shaded preview PNG per species.
Native import and placement live in Scripts/release_birds.py.

WHY POSE MESHES AND NOT A SKELETAL RIG
--------------------------------------
At flock scale (a few hundred birds on an RTX 2070) a skeletal mesh costs a per-instance bone
evaluation and cannot ride in a HierarchicalInstancedStaticMeshComponent at all. Four static
pose meshes per species, swapped per bird per update by AMikdashBirdFlock, cost one instance
transform write and render as ordinary instanced geometry. At the distance these birds are
actually seen - a pigeon 30 m up, a swift crossing a wall at 60 m - a four-step wingbeat is
already past the point where more poses add anything visible. The cost is that a bird held
still at two metres would read as a flick-book; nothing places one there.

NO TWO POSES OF ONE SPECIES MAY BE THE SAME MESH, and the export FAILS if they are. This is not
a theoretical guard: the crowd system in this project shipped a naive sine gait that produced two
byte-identical pose meshes, so the figure froze for a quarter of every cycle and nothing reported
it, because each individual mesh was perfectly valid. `_assert_poses_distinct` checks both byte
identity AND geometric separation (symmetric Hausdorff distance of the vertex clouds, which must
exceed 3 per cent of the species wingspan), because two poses can differ in one vertex by a hair
- distinct bytes, identical silhouette. The measured separations are written into the manifest as
`poseDistinctness`, and Scripts/release_birds.py refuses to import geometry that lacks the block.

Pose order is fixed and MUST match MikdashFlock::PoseIndex in FlockMath.h:
    0 up_stroke     wings raised above the back
    1 level         wings extended level; also the glide and the soar pose
    2 down_stroke   wings swept down below the body
    3 perched       wings folded, legs down

THE SPECIES, AND WHY THESE FIVE
-------------------------------
All five are real birds of the Jerusalem skyline (details, and the source of every size
figure, in SPECIES below and in species.json). Sizes are PUBLISHED FIELD-GUIDE RANGES taken
at the mid-point; this project measured no bird. The shapes are authored low-poly silhouettes
in the proportions those figures give - they are not scans, not photogrammetry, and not a
claim about any individual bird's plumage pattern.

The ambient rock dove is deliberately the wild-type blue-bar bird (mid blue-grey, dark head,
darker wing bars) so it never reads as the player's WHITE dove pawn (AMikdashDovePawn, F key).
Plumage colours are RECORDED here as intent; this module applies no material.

OBJ ADAPTER CONVENTION (project standard)
-----------------------------------------
Canonical vertices are centimetres in the bird's own frame: +X forward (bill), +Y the bird's
right, +Z up, origin at the body centre so a HISM instance transform is just the flight pose.
Every OBJ is written with Y REFLECTED and triangle winding REVERSED - the legacy Unreal OBJ
importer adapter proven on this project (create_keilim_ti_v1.write_obj,
create_oldcity_facades.write_obj, SourceAssets/sanctuary-detail/DoorsParochesV1). The importer
reflects Y back, so imported bounds must equal canonicalBoundsCm. Every canonical solid is
built closed and flipped when needed so its signed volume (sum dot(A, cross(B,C))/6) is
POSITIVE; write_obj asserts that, which is the check that catches inside-out meshes.

Each OBJ carries a single `o` object and exactly TWO `g` groups - `plumage_main` (body, wings,
tail, legs) and `plumage_hood` (head and bill) - so the importer creates exactly two material
slots per mesh. Two slots is deliberate: the hooded crow's grey body against its black hood,
and the rock dove's darker head, are the two-tone reading that makes each species
identifiable at distance. (The 236-slot SM_KeruvimStudyV1 lesson is why the count is fixed at
two and asserted, rather than one group per part.)
"""
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/birds-review/BirdsV1'
DEST = '/Game/MikdashV3/BirdsV1'

TRIANGLE_BUDGET = 40000
POSES = ('up_stroke', 'level', 'down_stroke', 'perched')
# Every pair of poses of one species must differ, somewhere on the bird, by at least this
# fraction of that species' wingspan. See _assert_poses_distinct for why this exists.
MIN_POSE_SEPARATION_FRACTION_OF_SPAN = 0.03
GROUP_MAIN = 'plumage_main'
GROUP_HOOD = 'plumage_hood'

OBJ_HEADER_NOTE = ('Unreal legacy OBJ adapter: canonical vertices are centimetres in the bird frame '
                   '(+X forward, +Y right, +Z up, origin at the body centre); this file is written with '
                   'Y reflected and triangle winding reversed. One object, exactly two g groups '
                   '(plumage_main, plumage_hood), so the importer creates exactly two material slots.')


# =====================================================================================
# 1. THE SPECIES TABLE
# =====================================================================================
# wingspan_cm / body_length_cm are the mid-points of the published ranges quoted in `source`.
# Everything else is authored shape in fractions of body_length_cm (L) unless noted.
#
# wing[] stations are (t, x_leading, x_trailing) where t is the fraction of the HALF span from
# the wing root outward and x is in fractions of L, measured from the body centre, +X forward.
# The planform is what makes a species readable in silhouette: a swift's scythe has its whole
# hand swept behind the root, a crow's hand is broad and blunt, a kestrel's tapers to a point.
SPECIES = {
    'rock_dove': dict(
        english='Rock dove (feral pigeon)', latin='Columba livia',
        wingspan_cm=67.0, body_length_cm=33.0,
        size_source=('Collins Bird Guide 2nd ed. (Svensson, Mullarney & Zetterstrom, 2009), Columba livia: '
                     'length 30-35 cm, wingspan 62-72 cm; same range in Cramp (ed.), Birds of the Western '
                     'Palearctic vol. IV. Mid-points used: 33 cm and 67 cm.'),
        jerusalem=('Abundant resident. Nests in crevices in stone walls; the classic bird of the plaza and of '
                   'the Kotel courses and their caper growth. Flocks wheel and settle on ledges.'),
        body_width=0.34, body_depth=0.40, head=0.20, bill=0.075, bill_depth=0.055,
        tail_len=0.36, tail_width=0.32, tail_fork=0.00, tail_lift=0.02,
        wing=[(0.00, 0.26, -0.06), (0.35, 0.25, -0.15), (0.70, 0.17, -0.17),
              (0.90, 0.07, -0.13), (1.00, -0.02, -0.05)],
        wing_thickness=0.016, neck=0.30,
        plumage=dict(
            main_linear=[0.170, 0.196, 0.232], hood_linear=[0.086, 0.098, 0.125],
            described=('wild-type blue-bar: mid blue-grey body and wings with two darker bars across the '
                       'secondaries, a darker slate head and neck, a pale rump. DELIBERATELY NOT WHITE: the '
                       'player dove (AMikdashDovePawn, F key) is the white bird and must stay unmistakable.')),
    ),
    'common_swift': dict(
        english='Common swift', latin='Apus apus',
        wingspan_cm=45.0, body_length_cm=16.5,
        size_source=('Collins Bird Guide 2nd ed., Apus apus: length 16-17 cm, wingspan 42-48 cm. '
                     'Mid-points used: 16.5 cm and 45 cm. (Older guides quote 38-40 cm; that is a '
                     'closed-wing measure and is not the figure used.)'),
        jerusalem=('Spring and early-summer breeding visitor, roughly late February to early July. Nests in '
                   'crevices of the Old City walls INCLUDING the Western Wall; the screaming low-level '
                   'parties scything round the walls at dusk are this bird. It never perches on a ledge - '
                   'a swift on the ground is a swift in trouble - so bPerches is false for this species.'),
        body_width=0.30, body_depth=0.34, head=0.19, bill=0.035, bill_depth=0.030,
        tail_len=0.36, tail_width=0.30, tail_fork=0.45, tail_lift=0.00,
        wing=[(0.00, 0.22, 0.02), (0.35, 0.12, -0.07), (0.70, -0.05, -0.17),
              (0.90, -0.22, -0.31), (1.00, -0.38, -0.42)],
        wing_thickness=0.020, neck=0.20,
        plumage=dict(
            main_linear=[0.045, 0.040, 0.036], hood_linear=[0.055, 0.050, 0.046],
            described='sooty blackish-brown all over with a small pale throat patch; reads as a black anchor shape.'),
    ),
    'hooded_crow': dict(
        english='Hooded crow', latin='Corvus cornix',
        wingspan_cm=98.0, body_length_cm=46.0,
        size_source=('Collins Bird Guide 2nd ed., Corvus cornix: length 45-47 cm, wingspan 93-104 cm. '
                     'Mid-points used: 46 cm and 98 cm.'),
        jerusalem=('Abundant urban resident. Seen in ones, twos and threes on parapets, roofs, walls and '
                   'aerials rather than in wheeling flocks; slower and much bigger than the pigeons.'),
        body_width=0.36, body_depth=0.42, head=0.22, bill=0.13, bill_depth=0.070,
        tail_len=0.38, tail_width=0.36, tail_fork=0.00, tail_lift=0.01,
        wing=[(0.00, 0.30, -0.10), (0.35, 0.29, -0.23), (0.65, 0.21, -0.27),
              (0.85, 0.09, -0.25), (1.00, -0.06, -0.14)],
        wing_thickness=0.014, neck=0.26,
        plumage=dict(
            main_linear=[0.235, 0.228, 0.205], hood_linear=[0.022, 0.022, 0.026],
            described=('ash-grey body and belly against a black hood, throat, wings and tail - the two-tone '
                       'contrast the two material slots exist for.')),
    ),
    'common_kestrel': dict(
        english='Common kestrel', latin='Falco tinnunculus',
        wingspan_cm=75.0, body_length_cm=33.0,
        size_source=('Collins Bird Guide 2nd ed., Falco tinnunculus: length 32-35 cm, wingspan 71-80 cm. '
                     'Mid-points used: 33 cm and 75 cm.'),
        jerusalem=('Resident. Breeds on tall buildings and on cliff and wall ledges; hangs, hovers and rides '
                   'lift over open ground. A single bird high overhead is the scale reference.'),
        body_width=0.32, body_depth=0.38, head=0.20, bill=0.060, bill_depth=0.060,
        tail_len=0.40, tail_width=0.30, tail_fork=0.00, tail_lift=0.00,
        wing=[(0.00, 0.26, -0.04), (0.35, 0.23, -0.15), (0.70, 0.11, -0.21),
              (0.90, -0.04, -0.23), (1.00, -0.19, -0.23)],
        wing_thickness=0.014, neck=0.24,
        plumage=dict(
            main_linear=[0.290, 0.145, 0.070], hood_linear=[0.150, 0.150, 0.170],
            described='rufous back spotted black, blue-grey head and tail with a black terminal band.'),
    ),
    'griffon_vulture': dict(
        english='Griffon vulture', latin='Gyps fulvus',
        wingspan_cm=260.0, body_length_cm=102.0,
        size_source=('Collins Bird Guide 2nd ed., Gyps fulvus: length 95-110 cm, wingspan 240-280 cm. '
                     'Mid-points used: 102 cm and 260 cm.'),
        jerusalem=('GENERATED BUT NOT PLACED BY DEFAULT. The Israeli griffon is now a Judean Desert, Negev '
                   'and Golan bird; it is not a routine sight over the city. A griffon over the Mount would '
                   'be a scale prop, not a Jerusalem observation, so Scripts/release_birds.py places the '
                   'kestrel for the lone-raptor role and records this reason in its receipt. The meshes '
                   'exist so that a reviewer who wants the larger silhouette can switch the species '
                   'property without another offline run.'),
        body_width=0.38, body_depth=0.44, head=0.16, bill=0.085, bill_depth=0.075,
        tail_len=0.26, tail_width=0.34, tail_fork=0.00, tail_lift=0.00,
        wing=[(0.00, 0.34, -0.14), (0.35, 0.33, -0.31), (0.65, 0.27, -0.35),
              (0.85, 0.15, -0.31), (1.00, 0.00, -0.18)],
        wing_thickness=0.012, neck=0.30,
        plumage=dict(
            main_linear=[0.200, 0.160, 0.115], hood_linear=[0.400, 0.385, 0.350],
            described='sandy-buff body and coverts against dark flight feathers; pale, almost white, head and ruff.'),
    ),
}

# Pose shaping. dihedral is the wing root rotation about the bird's X axis in degrees
# (positive raises the tip); sweep rotates the planform about Z (positive sweeps forward);
# twist rotates it about its own span axis so the outer wing is not a flat card.
POSE_SHAPE = {
    'up_stroke':   dict(dihedral=56.0, sweep=6.0, twist=-8.0, span=0.94, body_pitch=2.0, legs=False),
    'level':       dict(dihedral=4.0, sweep=0.0, twist=-3.0, span=1.00, body_pitch=0.0, legs=False),
    'down_stroke': dict(dihedral=-46.0, sweep=-8.0, twist=10.0, span=0.92, body_pitch=-2.0, legs=False),
    'perched':     dict(dihedral=-6.0, sweep=-34.0, twist=0.0, span=0.34, body_pitch=-14.0, legs=True),
}


# =====================================================================================
# 2. Geometry primitives - every solid closed and outward-wound
# =====================================================================================
def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def volume(v, f):
    """Signed volume, sum dot(A, cross(B, C)) / 6. Positive means outward-facing."""
    t = 0.0
    for a, b, c in f:
        p, q, r = v[a], v[b], v[c]
        n = cross([q[i] - p[i] for i in range(3)], [r[i] - p[i] for i in range(3)])
        t += sum(p[i] * n[i] for i in range(3))
    return t / 6.0


def orient(v, f):
    return (v, f) if volume(v, f) > 0 else (v, [(a, c, b) for a, b, c in f])


def closed(v, f):
    keys = [tuple(round(x, 5) for x in p) for p in v]
    edges = {}
    for a, b, c in f:
        for i, j in ((a, b), (b, c), (c, a)):
            k = tuple(sorted((keys[i], keys[j])))
            edges[k] = edges.get(k, 0) + 1
    return all(n == 2 for n in edges.values())


def loft(sections):
    """Closed tube through sections [(x, [(y, z), ...]), ...], all with the same ring size,
    capped with a triangle fan at each end. Degenerate rings (a point) are allowed."""
    n = len(sections[0][1])
    assert all(len(s[1]) == n for s in sections)
    v = []
    for x, ring in sections:
        v += [(x, y, z) for y, z in ring]
    f = []
    for s in range(len(sections) - 1):
        a0, b0 = s * n, (s + 1) * n
        for i in range(n):
            j = (i + 1) % n
            f += [(a0 + i, a0 + j, b0 + j), (a0 + i, b0 + j, b0 + i)]
    back, front = 0, (len(sections) - 1) * n
    for i in range(1, n - 1):
        f += [(back, back + i + 1, back + i), (front, front + i, front + i + 1)]
    return orient(v, dedupe(v, f))


def dedupe(v, f):
    """Drop triangles that collapsed because a ring was a point."""
    out = []
    for a, b, c in f:
        p, q, r = v[a], v[b], v[c]
        n = cross([q[i] - p[i] for i in range(3)], [r[i] - p[i] for i in range(3)])
        if sum(x * x for x in n) > 1e-12:
            out.append((a, b, c))
    return out


def slab(polygon_xy, z_lo, z_hi):
    """Prism over a simple polygon in the XY plane, extruded along Z. Wings and tails."""
    n = len(polygon_xy)
    v = [(x, y, z_lo) for x, y in polygon_xy] + [(x, y, z_hi) for x, y in polygon_xy]
    f = []
    for i in range(n):
        j = (i + 1) % n
        f += [(i, j, n + j), (i, n + j, n + i)]
    for i in range(1, n - 1):
        f += [(0, i, i + 1), (n, n + i + 1, n + i)]
    return orient(v, dedupe(v, f))


def box(center, size):
    hx, hy, hz = [s / 2.0 for s in size]
    cx, cy, cz = center
    v = [(cx + sx * hx, cy + sy * hy, cz + sz * hz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    f = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5),
         (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6),
         (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return orient(v, f)


def ellipse_ring(n, ry, rz, zc=0.0):
    return [(ry * math.cos(2 * math.pi * i / n), zc + rz * math.sin(2 * math.pi * i / n)) for i in range(n)]


def rotate_x(solid, degrees, pivot=(0.0, 0.0, 0.0)):
    a = math.radians(degrees)
    ca, sa = math.cos(a), math.sin(a)
    v, f = solid
    py, pz = pivot[1], pivot[2]
    out = []
    for x, y, z in v:
        dy, dz = y - py, z - pz
        out.append((x, py + dy * ca - dz * sa, pz + dy * sa + dz * ca))
    return orient(out, f)


def rotate_y(solid, degrees, pivot=(0.0, 0.0, 0.0)):
    a = math.radians(degrees)
    ca, sa = math.cos(a), math.sin(a)
    v, f = solid
    px, pz = pivot[0], pivot[2]
    out = []
    for x, y, z in v:
        dx, dz = x - px, z - pz
        out.append((px + dx * ca + dz * sa, y, pz - dx * sa + dz * ca))
    return orient(out, f)


def rotate_z(solid, degrees, pivot=(0.0, 0.0, 0.0)):
    a = math.radians(degrees)
    ca, sa = math.cos(a), math.sin(a)
    v, f = solid
    px, py = pivot[0], pivot[1]
    out = []
    for x, y, z in v:
        dx, dy = x - px, y - py
        out.append((px + dx * ca - dy * sa, py + dx * sa + dy * ca, z))
    return orient(out, f)


def mirror_y(solid):
    v, f = solid
    return orient([(x, -y, z) for x, y, z in v], f)


def translate(solid, offset):
    v, f = solid
    return (([(x + offset[0], y + offset[1], z + offset[2]) for x, y, z in v]), f)


def scale_y(solid, factor, pivot_y=0.0):
    v, f = solid
    return orient([(x, pivot_y + (y - pivot_y) * factor, z) for x, y, z in v], f)


# =====================================================================================
# 3. The bird
# =====================================================================================
# Body profile: fraction of the maximum half-width / half-depth at each station along X.
BODY_STATIONS = [
    (-0.30, 0.06, 0.06, 0.010),
    (-0.20, 0.52, 0.55, 0.012),
    (-0.06, 0.90, 0.94, 0.014),
    (+0.08, 1.00, 1.00, 0.010),
    (+0.20, 0.86, 0.90, 0.004),
    (+0.30, 0.58, 0.64, -0.002),
    (+0.36, 0.20, 0.24, -0.006),
]
RING = 8


def body_solid(spec):
    L = spec['body_length_cm']
    hw = 0.5 * spec['body_width'] * L
    hd = 0.5 * spec['body_depth'] * L
    sections = [(t * L, ellipse_ring(RING, max(1e-3, fw * hw), max(1e-3, fd * hd), zc * L))
                for t, fw, fd, zc in BODY_STATIONS]
    return loft(sections)


def head_solid(spec):
    """Head ball plus the bill, returned as one closed group each (they overlap the body on
    purpose: an ambient bird is never seen from inside)."""
    L = spec['body_length_cm']
    head_r = 0.5 * spec['head'] * L
    neck_x = spec['neck'] * L
    head_x = neck_x + head_r * 0.55
    head_z = 0.030 * L
    rings = [(-0.95, 0.10), (-0.55, 0.66), (0.0, 1.0), (0.55, 0.72), (0.95, 0.18)]
    sections = [(head_x + t * head_r, ellipse_ring(RING, max(1e-3, f * head_r * 0.92),
                                                   max(1e-3, f * head_r), head_z)) for t, f in rings]
    head = loft(sections)
    bill_len = spec['bill'] * L
    bill_d = 0.5 * spec['bill_depth'] * L
    bx = head_x + head_r * 0.80
    bill = loft([(bx, ellipse_ring(6, bill_d, bill_d, head_z - 0.004 * L)),
                 (bx + bill_len * 0.55, ellipse_ring(6, bill_d * 0.62, bill_d * 0.66, head_z - 0.008 * L)),
                 (bx + bill_len, ellipse_ring(6, bill_d * 0.10, bill_d * 0.10, head_z - 0.013 * L))])
    return head, bill


def tail_solid(spec):
    L = spec['body_length_cm']
    length = spec['tail_len'] * L
    half_w = 0.5 * spec['tail_width'] * L
    root_x = -0.24 * L
    tip_x = root_x - length
    fork = spec['tail_fork'] * length
    thickness = 0.010 * L
    if fork > 1e-6:                                  # a swift's deep fork: two prongs
        poly = [(root_x, half_w * 0.22), (tip_x, half_w),
                (tip_x + fork, 0.0), (tip_x, -half_w), (root_x, -half_w * 0.22)]
    else:
        poly = [(root_x, half_w * 0.30), (root_x - length * 0.35, half_w * 0.92),
                (tip_x, half_w * 0.72), (tip_x - length * 0.03, 0.0), (tip_x, -half_w * 0.72),
                (root_x - length * 0.35, -half_w * 0.92), (root_x, -half_w * 0.30)]
    z = spec['tail_lift'] * L
    return slab(poly, z - thickness * 0.5, z + thickness * 0.5)


def wing_solid(spec, pose):
    """The RIGHT wing, in the pose. Planform in XY, extruded in Z, then twisted about the
    span axis, swept about Z and given the pose dihedral about X at the root."""
    L = spec['body_length_cm']
    shape = POSE_SHAPE[pose]
    root_y = 0.5 * spec['body_width'] * L * 0.85
    half_span = 0.5 * spec['wingspan_cm'] * shape['span']
    thickness = spec['wing_thickness'] * L
    stations = spec['wing']
    ys = [root_y + (half_span - root_y) * t for t, _, _ in stations]
    lead = [(x_le * L, y) for (t, x_le, _), y in zip(stations, ys)]
    trail = [(x_te * L, y) for (t, _, x_te), y in zip(stations, ys)]
    poly = lead + list(reversed(trail))
    # remove any duplicate consecutive point (root leading == root trailing would collapse)
    cleaned = []
    for p in poly:
        if not cleaned or (abs(p[0] - cleaned[-1][0]) > 1e-6 or abs(p[1] - cleaned[-1][1]) > 1e-6):
            cleaned.append(p)
    solid = slab(cleaned, -thickness * 0.5, thickness * 0.5)
    # twist about the span axis (Y), progressively: wash-out at the tip
    v, f = solid
    twisted = []
    tw = math.radians(shape['twist'])
    for x, y, z in v:
        t = max(0.0, min(1.0, (y - root_y) / max(1e-6, half_span - root_y)))
        a = tw * t
        twisted.append((x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a)))
    solid = orient(twisted, f)
    solid = rotate_z(solid, shape['sweep'], pivot=(0.0, root_y, 0.0))
    solid = rotate_x(solid, shape['dihedral'], pivot=(0.0, root_y, 0.0))
    shoulder_z = 0.055 * L
    shoulder_x = 0.05 * L
    if pose == 'perched':                            # tuck the folded wing onto the back
        solid = translate(solid, (-0.05 * L, 0.0, 0.020 * L))
    return translate(solid, (shoulder_x, 0.0, shoulder_z))


def leg_solids(spec):
    L = spec['body_length_cm']
    drop = 0.20 * L
    thick = 0.030 * L
    out = []
    for side in (1.0, -1.0):
        y = side * 0.10 * L
        out.append(box((0.02 * L, y, -0.5 * spec['body_depth'] * L - drop * 0.5), (thick, thick, drop)))
        out.append(box((0.05 * L, y, -0.5 * spec['body_depth'] * L - drop), (0.11 * L, thick * 1.4, thick * 0.8)))
    return out


def build_pose(key, pose):
    """Returns (main_solids, hood_solids) in the bird's canonical frame."""
    spec = SPECIES[key]
    shape = POSE_SHAPE[pose]
    main = [body_solid(spec), tail_solid(spec)]
    right = wing_solid(spec, pose)
    main += [right, mirror_y(right)]
    if shape['legs']:
        main += leg_solids(spec)
    head, bill = head_solid(spec)
    hood = [head, bill]
    if abs(shape['body_pitch']) > 1e-9:
        main = [rotate_y(s, shape['body_pitch']) for s in main]
        hood = [rotate_y(s, shape['body_pitch']) for s in hood]
    return main, hood


# =====================================================================================
# 4. OBJ export and readback
# =====================================================================================
def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_obj(path, object_name, groups, provenance_lines):
    """groups: [(group_name, [solid, ...]), ...]. Returns the numeric facts for the manifest."""
    vertex_lines, uv_lines, normal_lines, group_lines = [], [], [], []
    vertex_index, normal_index = {}, {}
    lo = [float('inf')] * 3
    hi = [float('-inf')] * 3
    triangles = 0
    canonical_vertices, canonical_faces = [], []
    per_group = []

    for group_name, solids in groups:
        group_triangles = 0
        face_lines = []
        for solid in solids:
            points, faces = solid
            vol = volume(points, faces)
            assert vol > 0, 'inverted solid in %s / %s (signed volume %.6f)' % (object_name, group_name, vol)
            assert closed(points, faces), 'open solid in %s / %s' % (object_name, group_name)
            base = len(canonical_vertices)
            canonical_vertices.extend(points)
            canonical_faces.extend([(a + base, b + base, c + base) for a, b, c in faces])
            local = []
            for x, y, z in points:
                key = (round(x, 3), round(y, 3), round(z, 3))
                found = vertex_index.get(key)
                if found is None:
                    found = len(vertex_lines) + 1
                    vertex_index[key] = found
                    vertex_lines.append('v %.4f %.4f %.4f' % (key[0], -key[1], key[2]))
                    uv_lines.append('vt %.5f %.5f' % (0.5 + key[0] / 200.0, 0.5 + key[2] / 200.0))
                    for axis, value in enumerate(key):
                        lo[axis] = min(lo[axis], value)
                        hi[axis] = max(hi[axis], value)
                local.append(found)
            for a, b, c in faces:
                ax, ay, az = points[a]
                bx, by, bz = points[b]
                cx, cy, cz = points[c]
                nx, ny, nz = cross([bx - ax, by - ay, bz - az], [cx - ax, cy - ay, cz - az])
                length = math.sqrt(nx * nx + ny * ny + nz * nz)
                if length < 1e-9:
                    continue
                key = (round(nx / length, 4), round(-ny / length, 4), round(nz / length, 4))
                found = normal_index.get(key)
                if found is None:
                    found = len(normal_lines) + 1
                    normal_index[key] = found
                    normal_lines.append('vn %.4f %.4f %.4f' % key)
                ia, ib, ic = local[a], local[c], local[b]        # reversed winding for the adapter
                face_lines.append('f %d/%d/%d %d/%d/%d %d/%d/%d'
                                  % (ia, ia, found, ib, ib, found, ic, ic, found))
                triangles += 1
                group_triangles += 1
        group_lines.append(('g ' + group_name, face_lines))
        per_group.append(dict(group=group_name, triangles=group_triangles, solids=len(solids)))

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='ascii', newline='\n') as handle:
        handle.write('# ' + OBJ_HEADER_NOTE + '\n')
        for line in provenance_lines:
            handle.write('# ' + line + '\n')
        handle.write('o ' + object_name + '\n')
        handle.write('s off\n')
        handle.write('\n'.join(vertex_lines) + '\n')
        handle.write('\n'.join(uv_lines) + '\n')
        handle.write('\n'.join(normal_lines) + '\n')
        for header, faces in group_lines:
            handle.write(header + '\n')
            handle.write('\n'.join(faces) + '\n')

    whole = volume(canonical_vertices, canonical_faces)
    return dict(name=object_name, file=path.name, sha256=sha256_of(path), bytes=path.stat().st_size,
                triangles=triangles, vertices=len(vertex_lines), normals=len(normal_lines),
                groups=per_group, materialSlots=len(per_group),
                canonicalBoundsCm=dict(min=lo, max=hi),
                canonicalSignedVolumeCm3=round(whole, 4))


def readback(path, record):
    """Re-read the written file and prove the adapter: normals agree with the stored winding,
    reflecting Y back reproduces canonicalBoundsCm, and the file-space signed volume is
    positive (the inside-out check)."""
    verts, normals, faces, groups = [], [], [], []
    for line in path.read_text().splitlines():
        c = line.split()
        if not c:
            continue
        if c[0] == 'v':
            verts.append(tuple(map(float, c[1:4])))
        elif c[0] == 'vn':
            normals.append(tuple(map(float, c[1:4])))
        elif c[0] == 'g':
            groups.append(c[1])
        elif c[0] == 'f':
            faces.append([tuple(int(x) - 1 for x in t.split('/')) for t in c[1:]])
    assert len(faces) == record['triangles'], (len(faces), record['triangles'])
    assert groups == [g['group'] for g in record['groups']], groups
    worst = 0.0
    for face in faces:
        assert len(face) == 3
        a, b, c = [verts[t[0]] for t in face]
        cr = cross([b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)])
        area = math.sqrt(sum(x * x for x in cr))
        assert area > 1e-9
        dot = sum(cr[i] * normals[face[0][2]][i] for i in range(3)) / area
        worst = max(worst, abs(1.0 - dot))
    assert worst < 1e-3, worst
    canonical = [(x, -y, z) for x, y, z in verts]
    bounds = {k: [fn(v[i] for v in canonical) for i in range(3)] for k, fn in (('min', min), ('max', max))}
    error = max(abs(bounds[k][i] - record['canonicalBoundsCm'][k][i]) for k in bounds for i in range(3))
    assert error < 1e-3, error
    file_volume = volume(verts, [tuple(t[0] for t in f) for f in faces])
    assert file_volume > 0, 'adapter sign unexpected for ' + path.name
    return dict(mesh=record['name'], triangles=len(faces), groups=groups,
                boundsErrorCm=round(error, 9), worstNormalError=round(worst, 9),
                fileSpaceSignedVolumeCm3=round(file_volume, 3), status='PASS')


# =====================================================================================
# 5. Preview PNG - flat-shaded orthographic, the four poses side by side
# =====================================================================================
def _png(path, rgb, width, height):
    raw = b''.join(b'\x00' + bytes(rgb[y * width * 3:(y + 1) * width * 3]) for y in range(height))
    def chunk(tag, data):
        payload = tag + data
        return struct.pack('>I', len(data)) + payload + struct.pack('>I', zlib.crc32(payload) & 0xffffffff)
    header = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header)
                     + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def render_species(key, path, cell=280, margin=12):
    """Three rows (side, top, front) x four poses. Painter's algorithm, flat shading."""
    spec = SPECIES[key]
    views = [('side', lambda p: (p[0], p[2]), lambda p: -p[1]),
             ('top', lambda p: (p[0], -p[1]), lambda p: p[2]),
             ('front', lambda p: (p[1], p[2]), lambda p: p[0])]
    width, height = cell * len(POSES), cell * len(views)
    rgb = bytearray([26, 28, 32] * width * height)
    extent = max(spec['wingspan_cm'], spec['body_length_cm'] * 1.4) * 0.62
    main_colour = [max(30, min(235, int(c ** 0.4545 * 255))) for c in spec['plumage']['main_linear']]
    hood_colour = [max(20, min(235, int(c ** 0.4545 * 255))) for c in spec['plumage']['hood_linear']]
    for row, (_, project, depth) in enumerate(views):
        for col, pose in enumerate(POSES):
            main, hood = build_pose(key, pose)
            tris = []
            for solids, colour in ((main, main_colour), (hood, hood_colour)):
                for points, faces in solids:
                    for a, b, c in faces:
                        p, q, r = points[a], points[b], points[c]
                        n = cross([q[i] - p[i] for i in range(3)], [r[i] - p[i] for i in range(3)])
                        ln = math.sqrt(sum(x * x for x in n)) or 1.0
                        shade = 0.42 + 0.58 * max(0.0, (0.42 * n[0] - 0.62 * n[1] + 0.66 * n[2]) / ln)
                        tris.append((sum(depth(v) for v in (p, q, r)) / 3.0,
                                     [project(v) for v in (p, q, r)],
                                     [max(0, min(255, int(ch * shade))) for ch in colour]))
            tris.sort(key=lambda t: t[0])
            ox, oy = col * cell, row * cell
            scale = (cell - 2 * margin) / (2 * extent)
            for _, pts, colour in tris:
                sx = [ox + cell * 0.5 + p[0] * scale for p in pts]
                sy = [oy + cell * 0.5 - p[1] * scale for p in pts]
                y0, y1 = int(max(oy, min(sy))), int(min(oy + cell - 1, max(sy)))
                for y in range(y0, y1 + 1):
                    xs = []
                    for i in range(3):
                        j = (i + 1) % 3
                        if (sy[i] <= y < sy[j]) or (sy[j] <= y < sy[i]):
                            t = (y - sy[i]) / (sy[j] - sy[i])
                            xs.append(sx[i] + t * (sx[j] - sx[i]))
                    if len(xs) < 2:
                        continue
                    for x in range(int(max(ox, min(xs))), int(min(ox + cell - 1, max(xs))) + 1):
                        idx = (y * width + x) * 3
                        rgb[idx:idx + 3] = bytes(colour)
    for row in range(1, len(views)):                  # cell separators
        for x in range(width):
            idx = ((row * cell) * width + x) * 3
            rgb[idx:idx + 3] = bytes((70, 74, 82))
    for col in range(1, len(POSES)):
        for y in range(height):
            idx = (y * width + col * cell) * 3
            rgb[idx:idx + 3] = bytes((70, 74, 82))
    _png(path, rgb, width, height)
    return dict(file=path.name, sizePx=[width, height],
                layout='rows: side, top, front; columns: ' + ', '.join(POSES),
                limit=('Software orthographic flat shading with the two recorded plumage colours. '
                       'Not a native render, not a material or lighting acceptance.'))


# =====================================================================================
# 6. Export
# =====================================================================================
def _pose_points(solids_pairs):
    """Every canonical vertex of one built pose, in build order (main solids then hood)."""
    points = []
    for solids in solids_pairs:
        for verts, _faces in solids:
            points.extend(verts)
    return points


def _hausdorff_cm(a, b):
    """Symmetric max-of-nearest-neighbour distance between two point sets, centimetres.

    Used rather than an index-by-index comparison because the perched pose carries extra
    solids (the legs) and so has a different vertex count from the three flight poses.
    A few hundred points per pose makes the O(n*m) loop irrelevant at export time."""
    def one_way(p, q):
        worst = 0.0
        for x, y, z in p:
            best = float('inf')
            for u, v, w in q:
                d = (x - u) ** 2 + (y - v) ** 2 + (z - w) ** 2
                if d < best:
                    best = d
                    if best == 0.0:
                        break
            if best > worst:
                worst = best
        return math.sqrt(worst)
    return max(one_way(a, b), one_way(b, a))


def _assert_poses_distinct(key, points_by_pose, records_by_pose):
    """Fail the export if any two poses of one species are the same mesh.

    THIS CHECK EXISTS BECAUSE OF A REAL BUG IN THIS PROJECT. The crowd system's gait was a
    naive sine of the phase, and at two of the sampled phases it produced byte-identical pose
    meshes - a figure that appeared to walk but froze for a quarter of every cycle, and nothing
    reported it because every individual mesh was valid. A flock is far worse: a few hundred
    birds all skipping the same quarter-beat reads as a stutter across the whole sky.

    Two independent tests, and BOTH must pass:
      1. Byte identity. Two poses that hash the same are the same file, whatever the intent.
      2. Geometric separation. The symmetric Hausdorff distance between the two poses' canonical
         vertex clouds must be at least MIN_POSE_SEPARATION_FRACTION_OF_SPAN of the species
         wingspan. This is the test that actually catches the sine bug, because two poses can
         differ in a single vertex by a hair - distinct bytes, identical silhouette.
    Returns the measured separation for every pair, for the manifest."""
    span = SPECIES[key]['wingspan_cm']
    floor_cm = MIN_POSE_SEPARATION_FRACTION_OF_SPAN * span
    separations = {}
    poses = list(points_by_pose)
    for i in range(len(poses)):
        for j in range(i + 1, len(poses)):
            a, b = poses[i], poses[j]
            if records_by_pose[a]['sha256'] == records_by_pose[b]['sha256']:
                raise AssertionError(
                    'IDENTICAL POSE MESHES: %s poses %r and %r wrote byte-identical OBJs (sha %s). '
                    'Two poses that are the same file make the wingbeat skip; fix POSE_SHAPE.'
                    % (key, a, b, records_by_pose[a]['sha256'][:16]))
            d = _hausdorff_cm(points_by_pose[a], points_by_pose[b])
            separations['%s|%s' % (a, b)] = round(d, 4)
            if d < floor_cm:
                raise AssertionError(
                    'POSES TOO SIMILAR: %s poses %r and %r are only %.3f cm apart; at least %.3f cm '
                    '(%.0f%% of the %.1f cm wingspan) is required for the wingbeat to read. '
                    'Distinct bytes are not enough - fix POSE_SHAPE.'
                    % (key, a, b, d, floor_cm, 100.0 * MIN_POSE_SEPARATION_FRACTION_OF_SPAN, span))
    return dict(minimumRequiredCm=round(floor_cm, 4), pairsCm=separations,
                worstPairCm=round(min(separations.values()), 4) if separations else None)


def mesh_name(key, pose):
    return 'SM_BirdsV1_%s_%s' % (''.join(p.capitalize() for p in key.split('_')),
                                 ''.join(p.capitalize() for p in pose.split('_')))


def export(force=False, species=None):
    keys = tuple(species) if species else tuple(SPECIES)
    for k in keys:
        assert k in SPECIES, k
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / 'geometry-manifest.json'
    if manifest_path.exists() and not force:
        raise SystemExit('%s exists; pass --force to regenerate' % manifest_path)

    meshes, readbacks, previews = [], [], {}
    species_rows = {}
    pose_separation = {}
    for key in keys:
        spec = SPECIES[key]
        points_by_pose, records_by_pose = {}, {}
        for pose in POSES:
            main, hood = build_pose(key, pose)
            points_by_pose[pose] = _pose_points((main, hood))
            name = mesh_name(key, pose)
            record = write_obj(OUT / (name + '.obj'), name,
                               [(GROUP_MAIN, main), (GROUP_HOOD, hood)],
                               ['%s (%s), pose %s' % (spec['english'], spec['latin'], pose),
                                'wingspan %.1f cm, body length %.1f cm; %s'
                                % (spec['wingspan_cm'], spec['body_length_cm'], spec['size_source']),
                                'AUTHORED low-poly silhouette in those published proportions. Not a scan, not '
                                'photogrammetry, not a claim about an individual bird.'])
            record.update(species=key, pose=pose, poseIndex=POSES.index(pose))
            assert record['materialSlots'] == 2, record['materialSlots']
            records_by_pose[pose] = record
            meshes.append(record)
            readbacks.append(readback(OUT / record['file'], record))
        # No two poses of a species may be the same mesh. See _assert_poses_distinct.
        pose_separation[key] = _assert_poses_distinct(key, points_by_pose, records_by_pose)
        previews[key] = render_species(key, OUT / ('preview-%s.png' % key))
        span = [m['canonicalBoundsCm'] for m in meshes if m['species'] == key]
        species_rows[key] = dict(
            english=spec['english'], latin=spec['latin'],
            wingspanCm=spec['wingspan_cm'], bodyLengthCm=spec['body_length_cm'],
            sizeSource=spec['size_source'], jerusalem=spec['jerusalem'],
            plumage=spec['plumage'],
            meshes=[mesh_name(key, p) for p in POSES],
            levelPoseSpanCm=round(max(b['max'][1] for b in span) - min(b['min'][1] for b in span), 3),
            preview=previews[key]['file'])

    total = sum(m['triangles'] for m in meshes)
    assert total < TRIANGLE_BUDGET, (total, TRIANGLE_BUDGET)
    # The generated Level pose must reproduce the published wingspan to within a centimetre;
    # this is the check that the size figures actually reached the geometry.
    span_errors = {}
    for key in keys:
        level = next(m for m in meshes if m['species'] == key and m['pose'] == 'level')
        built = level['canonicalBoundsCm']['max'][1] - level['canonicalBoundsCm']['min'][1]
        span_errors[key] = round(built - SPECIES[key]['wingspan_cm'], 4)
        assert abs(span_errors[key]) < 1.0, (key, built, SPECIES[key]['wingspan_cm'])

    manifest = dict(
        status='OFFLINE_VALIDATED_NATIVE_AND_VISUAL_PENDING',
        namespace=DEST,
        script='Scripts/create_birds.py',
        scriptSha256=sha256_of(Path(__file__)),
        poseOrder=list(POSES),
        poseOrderContract=('Index order MUST match MikdashFlock::PoseIndex in '
                           'Plugins/MikdashRuntime/Source/MikdashRuntime/Public/FlockMath.h: '
                           '0 up_stroke, 1 level (also glide/soar), 2 down_stroke, 3 perched.'),
        poseShaping={k: dict(v) for k, v in POSE_SHAPE.items()},
        poseDistinctness=pose_separation,
        poseDistinctnessContract=(
            'Export FAILS if any two poses of one species hash the same OR are closer than %.0f%% of '
            'that species wingspan by symmetric Hausdorff distance. The crowd system in this project '
            'shipped a naive sine gait that made two poses byte-identical and nothing caught it; a '
            'flock doing that stutters across the whole sky.'
            % (100.0 * MIN_POSE_SEPARATION_FRACTION_OF_SPAN)),
        objConvention=OBJ_HEADER_NOTE,
        materialSlotContract=('Exactly two g groups per mesh -> exactly two material slots: %s then %s. '
                              'This module applies no material; plumage colours below are recorded intent.'
                              % (GROUP_MAIN, GROUP_HOOD)),
        species=species_rows,
        levelPoseSpanErrorCm=span_errors,
        meshes=meshes,
        readback=readbacks,
        previews=previews,
        totalTriangles=total,
        triangleBudget=TRIANGLE_BUDGET,
        nativePlan=dict(
            namespace=DEST,
            collision='NoCollision on every bird mesh and on every HISM component. Ambient birds must '
                      'never block, push or be traced against anything - in particular they must never '
                      'interfere with the player dove pawn spawn (AMikdashDovePawn is spawned at runtime '
                      'with AdjustIfPossibleButDontSpawnIfColliding, so a colliding flock overhead could '
                      'have blocked take-off; with NoCollision it cannot).',
            nanite=False,
            naniteReason='Sub-500-triangle meshes drawn as HISM instances; Nanite would add cluster '
                         'overhead for no triangle saving at this size.',
            placement='HISM instance transforms authored at runtime by AMikdashBirdFlock; the actor '
                      'itself is placed by Scripts/release_birds.py.',
            importer='Scripts/release_birds.py (+ .spec.json)'),
        limitations=[
            'AUTHORED GEOMETRY. Every bird is an invented low-poly silhouette built to published wingspan '
            'and body-length figures. Nothing here is scanned, photogrammetric, or a claim about the '
            'plumage pattern of an individual bird.',
            'Sizes are FIELD-GUIDE RANGES quoted at their mid-point (per-species citation in species[].'
            'sizeSource). This project measured no bird and took no photograph of one.',
            'Four poses per species. A bird held still and viewed close would read as a flick-book; the '
            'flock actor is configured never to place one there, but that is a placement rule, not a '
            'property of the mesh.',
            'Planar placeholder UVs only. No lightmap UVs are generated; the flock is a movable, '
            'dynamically lit HISM.',
            'Plumage is RECORDED, NOT APPLIED: no material, material instance or texture is created or '
            'assigned by this module. Until a material pass runs, the imported meshes carry the '
            'importer default and the rock dove is NOT yet visibly distinct from the white player dove.',
            'No engine work here: no import, no placement, no collision, no cook, no visual acceptance.',
        ],
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (OUT / 'species.json').write_text(json.dumps(
        dict(status='REFERENCE_ONLY', script='Scripts/create_birds.py',
             note=('Size figures are published field-guide ranges quoted at their mid-point; this project '
                   'measured nothing. Occurrence notes describe why each bird belongs on this skyline.'),
             species=species_rows), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return manifest


def _summary(manifest):
    return dict(status=manifest['status'], totalTriangles=manifest['totalTriangles'],
                meshes=len(manifest['meshes']),
                worstPoseSeparationCm={k: v['worstPairCm'] for k, v in manifest['poseDistinctness'].items()},
                species={k: dict(wingspanCm=v['wingspanCm'], meshes=len(v['meshes']))
                         for k, v in manifest['species'].items()},
                levelPoseSpanErrorCm=manifest['levelPoseSpanErrorCm'])


def _main():
    if '--export' not in sys.argv:
        raise SystemExit('Explicit --export [--force] [--species=rock_dove,common_swift]; offline only. '
                         'Native work is in Scripts/release_birds.py')
    species = None
    for a in sys.argv[1:]:
        if a.startswith('--species='):
            species = [x.strip() for x in a.split('=', 1)[1].split(',') if x.strip()]
    manifest = export(force='--force' in sys.argv, species=species)
    for m in manifest['meshes']:
        print('%-44s %5d tris  %d slots  span %7.2f cm'
              % (m['name'], m['triangles'], m['materialSlots'],
                 m['canonicalBoundsCm']['max'][1] - m['canonicalBoundsCm']['min'][1]))
    print(json.dumps(_summary(manifest), indent=2))


if __name__ == '__main__':
    _main()
