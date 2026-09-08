"""MenorahV4: an original parametric menorah calibrated to a Temple Institute photograph.

Offline, stdlib only. Writes per-part OBJ files, a geometry manifest with every counted ornament,
a software preview PNG, the photograph's extracted silhouette and a model-vs-photo overlay with an
intersection-over-union score into SourceAssets/vessels-review/MenorahV4/. No engine launch, no
Content/ change. Native import and placement live in Scripts/release_import_menorah_v4.py (+ .spec.json).

WHY V4 EXISTS. V3 was built to generic proportions (quarter-ellipse branches, plain circular tubes,
lamp pitch 18 cm chosen by hand, junctions at the Menachos 28b tefachim). The user asked for "an exact
replica of the Machon HaMikdash version". V4 is therefore calibrated: the branch radii, the junction
heights, every ornament group's vertical extent and the plinth tiers are measured as PIXEL ratios in
one Temple Institute photograph and recorded in SourceAssets/vessels-review/MenorahV4/calibration.json.

HONESTY. That calibration is photograph-derived proportion, not a measured survey. The Institute
publishes no measured drawings. Absolute centimetres come only from this project's own halachic height
(150 cm = 18 tefachim at the 50 cm amah, book "Lishchno Tidreshu" p. 252). Depth (front to back) is
uncalibrated - one photograph gives no depth - and every relief motif is authored, not traced. The
reference photographs stay in the gitignored SourceAssets/reference-ti/ folder; nothing is copied,
textured or traced from them, only ratios are read.

Sources: Shemos 25:31-40 (counts); Menachos 28b (the Talmudic vertical breakdown, recorded as the
deviation the photograph overrides); Rambam Beit HaBechirah 3:8 (wick directions), 3:10 (18 tefachim),
3:11 (three-step tending stone), 3:12 (lamps north-south); reference-ti/dossier.md section 1;
SourceAssets/vessels-review/menorah-model-spec.json (count contract and the earlier photo audit).

Canonical frame (Unreal cm): local X = the lamp row (fan axis), local +Y = FRONT (the side the tending
stone is on = east after the placement yaw of -90), Z up, origin at the centre of the base contact
plane on the floor. OBJ files carry Y reflected and reversed winding for the legacy OBJ importer
(same adapter as ShulchanV2 / DoorsParochesV1 / MenorahV3); the importer reflects Y back, so imported
bounds must equal bounds_cm and UE signed volumes must be positive.

Usage:  python Scripts/create_menorah_v4.py --export [--force] [--no-photo]
"""
import hashlib
import json
import math
import os
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets' / 'vessels-review' / 'MenorahV4'
PHOTO = ROOT / 'SourceAssets' / 'reference-ti' / 'menorah' / ('wiki-' + u'\u05de\u05e0\u05d5\u05e8\u05d4' + '.jpg')
CALIBRATION = OUT / 'calibration.json'
DEST = '/Game/MikdashV3/MaterialReview/MenorahV4'
AMAH = 50.0
TEFACH = AMAH / 6.0
TAU = math.tau
H = 18 * TEFACH            # 150.0 cm overall height, floor to the top of the central finial


# ==========================================================================================
# CALIBRATED PARAMETERS.  Every "cal" value is calibration.json normalised_to_H x H (150 cm).
# Every "art" value is authored: depth, relief, facet and petal counts, the tending stone.
# ==========================================================================================
def cal(x):
    return x * H


P = dict(
    total_height=H,
    # --- branches: three concentric semicircles about one point on the shaft axis (calibration) ---
    arc_centre_z=cal(0.7621),
    arc_radii=[cal(0.1100), cal(0.2098), cal(0.3003)],        # inner, middle, outer
    stack_bottom_z=cal(0.7823),
    branch_diameter=[cal(0.0273), cal(0.0254)],               # foot -> tip (calibration, 4.10 -> 3.81 cm)
    branch_depth_ratio=0.82,                                  # art: front-to-back depth / in-plane width
    branch_band=0.34, branch_band_rise=1.055,                 # art: the broad flat front band and its slight proudness
    # --- central shaft (calibration radii) ---
    shaft_r=[cal(0.0235), cal(0.0150), cal(0.0143)],          # above the base, between junctions, under the stack
    shaft_facets=16, shaft_facet_amp=0.030,                   # art: the shaft reads faceted
    # --- upper ornament groups (calibration spans) ---
    goblet_band=[cal(0.7823), cal(0.8631)],                   # four tiers on the shaft, three on each branch
    goblet_tiers_h=[cal(0.7823), cal(0.7979), cal(0.8214), cal(0.8422), cal(0.8631)],
    goblet_dia=cal(0.0456),
    knop_span=[cal(0.8644), cal(0.8983)], knop_dia=cal(0.0691),
    flower_span=[cal(0.8996), cal(0.9283)], flower_dia=cal(0.0378),
    stem_span=[cal(0.9283), cal(0.9478)], stem_dia=cal(0.0157),
    # Iteration 3: the first pass read the lamp as a deep bowl with the rim at its top. The on-axis
    # width profile says otherwise - the widest row is y 64 (h 0.9596) with the silhouette narrowing
    # BOTH above (the domed lid, 51 -> 11 px between y 68 and y 50) and below (26 px at y 73). The lamp
    # is therefore a very shallow saucer whose rim is overhung by a tall lid carrying the finial.
    lamp_span=[cal(0.9478), cal(0.9596)], lamp_dia=cal(0.0743),
    lid_span=[cal(0.9583), cal(0.9778)],
    finial_span=[cal(0.9778), cal(1.0)], finial_dia_ratio=0.30,
    # --- shaft junctions and the lower central group (calibration spans) ---
    junction_span=[[cal(0.4589), cal(0.4941)], [cal(0.5554), cal(0.5920)], [cal(0.6519), cal(0.6897)]],
    junction_dia=cal(0.0626),
    lower_flower_up=[cal(0.3598), cal(0.4081)], lower_flower_up_dia=cal(0.0704),
    lower_knop=[cal(0.3246), cal(0.3559)], lower_knop_dia=cal(0.0587),
    lower_flower_low=[cal(0.2803), cal(0.3233)], lower_flower_low_dia=cal(0.0365),
    # --- base (calibration tiers, hexagon with a vertex to the front) ---
    # Base tier planes use the MID-PLANE rule (iteration 2): the camera sits above the plinth, so each
    # horizontal plane projects as a band between its far edge and its near vertex; its true height is
    # the middle of that band, not the near-vertex row the first pass used. Correcting this made the
    # tiers taller and lifted the bounding-box silhouette score from 0.413 to 0.51 (silhouette-iterations.json).
    foot_span=[0.0, cal(0.0183)],
    tier_lower=[cal(0.0183), cal(0.1253)], tier_lower_R=cal(0.2394), tier_lower_chamfer=0.93,
    tier_lower_cap=[cal(0.1253), cal(0.1343)], tier_lower_cap_R=cal(0.2454),
    tier_upper=[cal(0.1343), cal(0.1825)], tier_upper_R=cal(0.1942),
    ogee=[cal(0.1825), cal(0.2138)], ogee_top_R=cal(0.0235),
    panel_lower=(0.84, 0.66, cal(0.0045)),                    # width frac of face, height frac of tier, relief depth
    panel_upper=(0.88, 0.55, cal(0.0035)),
    panel_cap=(0.90, 0.40, cal(0.0025)),
    # --- authored details ---
    knop_bosses=12, knop_boss_r=0.155, flower_petals=6, goblet_flutes=14,
    nozzle_len=cal(0.030), nozzle_r=cal(0.0075),
    stone=dict(gap=10.0, width=90.0, tread=30.0, rise=2 * TEFACH, steps=3, corner=12.0),
)
SEG = dict(round=40, petal=12, tube=28, hex=6, boss=10, arc=64)

# Lamp x positions: the calibrated semicircle radii, mirrored (Shemos 25:32: three branches a side).
LAMP_X = [-P['arc_radii'][2], -P['arc_radii'][1], -P['arc_radii'][0], 0.0,
          P['arc_radii'][0], P['arc_radii'][1], P['arc_radii'][2]]
STACK_TAGS = ['L3', 'L2', 'L1', 'C', 'R1', 'R2', 'R3']

# Silhouette iterations: appended by hand after each --export run (see the report in the manifest).
SILHOUETTE_LOG = OUT / 'silhouette-iterations.json'


# ---------------------------------------------------------------- vector helpers
def sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def norm(a):
    length = math.sqrt(sum(x * x for x in a)) or 1.0
    return [x / length for x in a]


def volume(vertices, faces):
    total = 0.0
    for a, b, c in faces:
        va, vb, vc = vertices[a], vertices[b], vertices[c]
        total += (va[0] * (vb[1] * vc[2] - vb[2] * vc[1]) + va[1] * (vb[2] * vc[0] - vb[0] * vc[2])
                  + va[2] * (vb[0] * vc[1] - vb[1] * vc[0]))
    return total / 6.0


def orient(vertices, faces):
    if volume(vertices, faces) < 0:
        faces = [(a, c, b) for a, b, c in faces]
    return vertices, faces


def closed(vertices, faces):
    """Every welded position-edge is shared by exactly two triangles (closed 2-manifold)."""
    keys = [tuple(round(x, 5) for x in v) for v in vertices]
    edges = {}
    for a, b, c in faces:
        for i, j in ((a, b), (b, c), (c, a)):
            if keys[i] == keys[j]:
                return False
            edge = (keys[i], keys[j]) if keys[i] < keys[j] else (keys[j], keys[i])
            edges[edge] = edges.get(edge, 0) + 1
    return all(n == 2 for n in edges.values())


# ---------------------------------------------------------------- primitives
def lathe(profile, center=(0.0, 0.0, 0.0), segments=40, lobes=0, amp=0.0, phase=0.0, rotate=0.0):
    """Revolve an (r, z) profile that starts and ends on the axis; optional flute/facet lobes."""
    assert abs(profile[0][0]) < 1e-12 and abs(profile[-1][0]) < 1e-12, 'profile must start and end on the axis'
    vertices, rings, faces = [], [], []
    for radius, z in profile:
        ring = []
        for i in range(1 if radius == 0 else segments):
            angle = rotate + i * TAU / segments
            r = radius * (1 + amp * math.cos(lobes * angle + phase)) if lobes else radius
            ring.append(len(vertices))
            vertices.append((center[0] + r * math.cos(angle), center[1] + r * math.sin(angle), center[2] + z))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            if len(a) == 1 and len(b) > 1:
                faces.append((a[0], b[j], b[i]))
            elif len(b) == 1 and len(a) > 1:
                faces.append((a[i], a[j], b[0]))
            elif len(a) > 1 and len(b) > 1:
                faces.extend([(a[i], a[j], b[j]), (a[i], b[j], b[i])])
    return orient(vertices, faces)


def band_section(n, width, depth, band, rise):
    """Rounded-rectangle tube section with a broad, slightly proud flat FRONT/BACK band.

    Returns (u, v) offsets: u across the branch plane, v front-to-back. This is the calibration's
    'broad reflective front band with narrow rounded edge highlights', not a circular tube.
    """
    pts = []
    for i in range(n):
        a = i * TAU / n
        ca, sa = math.cos(a), math.sin(a)
        u = (width / 2.0) * math.copysign(abs(ca) ** 0.5, ca)      # superellipse exponent 4
        v = (depth / 2.0) * math.copysign(abs(sa) ** 0.5, sa)
        if abs(u) < band * width:
            v *= rise
        pts.append((u, v))
    return pts


def sweep_band(points, widths, section_n, depth_ratio, band, rise):
    """Sweep a band_section along a polyline that lies in the XZ plane (front direction = +Y)."""
    vertices, rings, faces = [], [], []
    n = len(points)
    front = (0.0, 1.0, 0.0)
    for k, p in enumerate(points):
        if k == 0:
            t = sub(points[1], points[0])
        elif k == n - 1:
            t = sub(points[-1], points[-2])
        else:
            t = sub(points[k + 1], points[k - 1])
        t = norm(t)
        inplane = norm(cross(front, t))
        sec = band_section(section_n, widths[k], widths[k] * depth_ratio, band, rise)
        ring = []
        for u, v in sec:
            ring.append(len(vertices))
            vertices.append(tuple(p[i] + u * inplane[i] + v * front[i] for i in range(3)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(section_n):
            j = (i + 1) % section_n
            faces.extend([(a[i], a[j], b[j]), (a[i], b[j], b[i])])
    for ring, point, reverse in ((rings[0], points[0], True), (rings[-1], points[-1], False)):
        c = len(vertices)
        vertices.append(tuple(point))
        for i in range(section_n):
            j = (i + 1) % section_n
            faces.append((ring[j], ring[i], c) if reverse else (ring[i], ring[j], c))
    return orient(vertices, faces)


def prism(polygon, z0, z1):
    """Extruded convex polygon (list of (x, y)), caps as centroid fans."""
    n = len(polygon)
    cx = sum(p[0] for p in polygon) / n
    cy = sum(p[1] for p in polygon) / n
    vertices = [(x, y, z0) for x, y in polygon] + [(x, y, z1) for x, y in polygon] + [(cx, cy, z0), (cx, cy, z1)]
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.extend([(i, j, n + j), (i, n + j, n + i)])
        faces.append((j, i, 2 * n))
        faces.append((n + i, n + j, 2 * n + 1))
    return orient(vertices, faces)


def boss(centre, u_axis, v_axis, n_axis, ru, rv, height, segments=10):
    """A raised almond/teardrop boss on a curved surface (knop cartouches, base bead accents)."""
    vertices, faces = [], []
    rings = []
    for k, (s, hz) in enumerate(((1.0, 0.0), (0.92, 0.45), (0.66, 0.82), (0.30, 0.99))):
        ring = []
        for i in range(segments):
            a = i * TAU / segments
            du, dv = ru * s * math.cos(a), rv * s * math.sin(a)
            ring.append(len(vertices))
            vertices.append(tuple(centre[i] + du * u_axis[i] + dv * v_axis[i] + height * hz * n_axis[i] for i in range(3)))
        rings.append(ring)
    tip = len(vertices)
    vertices.append(tuple(centre[i] + height * 1.06 * n_axis[i] for i in range(3)))
    root = len(vertices)
    vertices.append(tuple(centre[i] - height * 0.10 * n_axis[i] for i in range(3)))
    for a, b in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            faces.extend([(a[i], a[j], b[j]), (a[i], b[j], b[i])])
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((rings[-1][i], rings[-1][j], tip))
        faces.append((rings[0][j], rings[0][i], root))
    return orient(vertices, faces)


def petal(centre, u_axis, v_axis, n_axis, length, halfwidth, thickness, curl, segments=10):
    """A single upturned flower petal: a lens-section leaf swept along a curling radial centreline.

    Built as a closed swept solid so the part is a watertight 2-manifold like every other ornament.
    """
    stations = 7
    points, halfw, halfd = [], [], []
    for k in range(stations):
        t = k / float(stations - 1)
        along = length * t
        lift = curl * length * (t * t)
        w = halfwidth * (0.42 + 0.86 * math.sin(math.pi * (0.20 + 0.68 * t)))
        d = thickness * (0.55 + 0.45 * math.sin(math.pi * min(1.0, 0.25 + 0.75 * t)))
        if k == stations - 1:
            w *= 0.16
            d *= 0.22
        points.append(tuple(centre[i] + along * u_axis[i] + lift * n_axis[i] for i in range(3)))
        halfw.append(max(w, 1e-3))
        halfd.append(max(d, 1e-3))
    vertices, rings, faces = [], [], []
    n = len(points)
    for k, p in enumerate(points):
        if k == 0:
            t = sub(points[1], points[0])
        elif k == n - 1:
            t = sub(points[-1], points[-2])
        else:
            t = sub(points[k + 1], points[k - 1])
        t = norm(t)
        m_axis = norm(cross(v_axis, t))
        ring = []
        for i in range(segments):
            a = i * TAU / segments
            cu = halfw[k] * math.cos(a)
            cv = halfd[k] * math.sin(a)
            ring.append(len(vertices))
            vertices.append(tuple(p[i2] + cu * v_axis[i2] + cv * m_axis[i2] for i2 in range(3)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            faces.extend([(a[i], a[j], b[j]), (a[i], b[j], b[i])])
    for ring, point, reverse in ((rings[0], points[0], True), (rings[-1], points[-1], False)):
        c = len(vertices)
        vertices.append(tuple(point))
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((ring[j], ring[i], c) if reverse else (ring[i], ring[j], c))
    return orient(vertices, faces)


def raised_panel(centre, u_axis, v_axis, n_axis, hw, hh, depth, bevel=0.30):
    """A raised rectangular relief panel with a bevelled border, sitting proud of a flat face."""
    def pt(u, v, n):
        return tuple(centre[i] + u * u_axis[i] + v * v_axis[i] + n * n_axis[i] for i in range(3))
    outer = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    inner = [(-hw * (1 - bevel * hh / hw if False else 1) + 0, 0)]   # placeholder, replaced below
    bu, bv = hw * bevel * 0.5, hh * bevel * 0.5
    field = [(-hw + bu, -hh + bv), (hw - bu, -hh + bv), (hw - bu, hh - bv), (-hw + bu, hh - bv)]
    vertices = [pt(u, v, 0.0) for u, v in outer] + [pt(u, v, depth) for u, v in field] \
        + [pt(u, v, depth * 1.18) for u, v in field]
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces.extend([(i, j, 4 + j), (i, 4 + j, 4 + i)])        # bevel
        faces.extend([(4 + i, 4 + j, 8 + j), (4 + i, 8 + j, 8 + i)])   # field wall
    faces.extend([(8, 9, 10), (8, 10, 11)])                     # field top
    faces.extend([(0, 2, 1), (0, 3, 2)])                        # back
    del inner
    return orient(vertices, faces)


# ---------------------------------------------------------------- calibrated ornament profiles
def goblet_profile(height, dia):
    """Almond/cup goblet: narrow stem foot, swelling body, a defined outward lip and a returned rim."""
    r = dia / 2.0
    h = height
    return [(0, 0), (0.40 * r, 0), (0.44 * r, 0.06 * h), (0.37 * r, 0.14 * h), (0.46 * r, 0.30 * h),
            (0.63 * r, 0.50 * h), (0.80 * r, 0.68 * h), (0.94 * r, 0.83 * h), (1.00 * r, 0.92 * h),
            (0.99 * r, 0.99 * h), (0.86 * r, 1.00 * h), (0.80 * r, 0.93 * h), (0.62 * r, 0.72 * h), (0, 0.68 * h)]


def knop_profile(height, dia):
    """Flattened sphere with a collar ring at its foot and a returned neck at the top."""
    r = dia / 2.0
    h = height
    return [(0, 0), (0.44 * r, 0.0), (0.62 * r, 0.05 * h), (0.86 * r, 0.13 * h), (0.80 * r, 0.20 * h),
            (0.93 * r, 0.31 * h), (1.00 * r, 0.47 * h), (0.98 * r, 0.62 * h), (0.86 * r, 0.76 * h),
            (0.64 * r, 0.88 * h), (0.50 * r, 0.94 * h), (0.44 * r, h), (0, h)]


def flower_cup_profile(height, dia):
    """The flower's central bud and its collar; the flared petals are separate meshes."""
    r = dia / 2.0
    h = height
    return [(0, 0), (0.30 * r, 0.0), (0.42 * r, 0.10 * h), (0.36 * r, 0.20 * h), (0.50 * r, 0.40 * h),
            (0.54 * r, 0.62 * h), (0.44 * r, 0.82 * h), (0.28 * r, 0.95 * h), (0, h)]


def lamp_profile(height, dia):
    """TI lamp: a very shallow saucer with a DISTINCT outward rim at its top (0.46 -> 1.00 of the rim
    radius over the 9 px the photograph gives it) and a returned inner wall."""
    r = dia / 2.0
    h = height
    return [(0, 0), (0.30 * r, 0.0), (0.46 * r, 0.14 * h), (0.66 * r, 0.40 * h), (0.86 * r, 0.66 * h),
            (0.98 * r, 0.84 * h), (1.00 * r, 0.93 * h), (0.98 * r, 1.00 * h), (0.88 * r, 0.98 * h),
            (0.82 * r, 0.86 * h), (0.60 * r, 0.56 * h), (0, 0.48 * h)]


def lid_profile(height, dia):
    """Domed lid overhanging the lamp rim; radii read off the photograph's on-axis widths
    (y 68/60/57/55/53/50 -> 0.90/0.86/0.70/0.54/0.35/0.19 of the rim radius)."""
    r = dia / 2.0
    return [(0, 0), (0.94 * r, 0.0), (0.90 * r, 0.10 * height), (0.86 * r, 0.24 * height),
            (0.70 * r, 0.44 * height), (0.54 * r, 0.60 * height), (0.35 * r, 0.78 * height),
            (0.19 * r, 0.96 * height), (0, height)]


def finial_profile(height, dia):
    r = dia / 2.0
    return [(0, 0), (0.42 * r, 0.0), (0.55 * r, 0.14 * height), (0.36 * r, 0.30 * height),
            (0.50 * r, 0.50 * height), (0.34 * r, 0.68 * height), (0.20 * r, 0.86 * height), (0, height)]


# ---------------------------------------------------------------- assembly
def hexagon(R, rotate=0.0):
    return [(R * math.cos(rotate + k * TAU / 6), R * math.sin(rotate + k * TAU / 6)) for k in range(6)]


def branch_curve(radius, sign, steps):
    """Quarter circle from the shaft axis (bottom of the semicircle) to the vertical tangent, then straight."""
    cz = P['arc_centre_z']
    points, widths = [], []
    w0, w1 = P['branch_diameter']
    for k in range(steps + 1):
        t = (math.pi / 2) * k / steps                     # 0 at the shaft foot, pi/2 at the side
        points.append((sign * radius * math.sin(t), 0.0, cz - radius * math.cos(t)))
        widths.append(w0 + (w1 - w0) * (k / float(steps)))
    top = P['stack_bottom_z']
    for k in range(1, 4):
        points.append((sign * radius, 0.0, cz + (top - cz) * k / 3.0))
        widths.append(w1)
    return points, widths


def geometry():
    """Returns {meshName: [(partId, kind, (vertices, faces))]} and the ornament register."""
    meshes = {name: [] for name in ('SM_MenorahV4_Base', 'SM_MenorahV4_Shaft', 'SM_MenorahV4_BranchesL',
                                    'SM_MenorahV4_BranchesR', 'SM_MenorahV4_Ornaments', 'SM_MenorahV4_Lamps',
                                    'SM_MenorahV4_StepStone')}
    register = []

    def add(mesh, part_id, kind, geo, **meta):
        v, f = geo
        assert closed(v, f), 'open part ' + part_id
        assert volume(v, f) > 0, 'inverted part ' + part_id
        meshes[mesh].append((part_id, kind, (v, f)))
        register.append(dict(id=part_id, kind=kind, mesh=mesh, triangles=len(f), **meta))

    base, orn, lamps = 'SM_MenorahV4_Base', 'SM_MenorahV4_Ornaments', 'SM_MenorahV4_Lamps'

    # ---------------- base: stepped hexagonal plinth, a vertex to the front (+Y), raised panels ----
    rot = math.pi / 2                                        # vertex toward +Y, as the photograph shows
    tiers = [('BasePlinthLower', P['tier_lower'], P['tier_lower_R'], P['tier_lower_chamfer']),
             ('BasePlinthCap', P['tier_lower_cap'], P['tier_lower_cap_R'], 1.0),
             ('BaseTierUpper', P['tier_upper'], P['tier_upper_R'], 1.0)]
    for name, (z0, z1), R, chamfer in tiers:
        b = min(0.9, (z1 - z0) * 0.22)
        c = min(1.4, (z1 - z0) * 0.20)
        profile = [(0, z0), (R * chamfer, z0)]
        if chamfer < 1.0:
            profile.append((R, z0 + c))
        profile += [(R, z1 - b), (R * 0.985, z1), (0, z1)]
        add(base, name, 'base', lathe(profile, segments=SEG['hex'], rotate=rot),
            circumradius_cm=R, z_cm=[z0, z1])
    # ogee moulding up to the round stem collar
    z0, z1 = P['ogee']
    R, rt = P['tier_upper_R'], P['ogee_top_R']
    ogee = [(0, z0)]
    for k in range(9):
        t = k / 8.0
        ogee.append((R + (rt - R) * (0.5 - 0.5 * math.cos(math.pi * t)), z0 + (z1 - z0) * t))
    ogee.append((0, z1))
    add(base, 'BaseOgeeCap', 'base', lathe(ogee, segments=SEG['hex'] * 4, lobes=6, amp=0.022, phase=rot, rotate=rot),
        z_cm=[z0, z1], top_radius_cm=rt)
    add(base, 'BaseStemCollar', 'base',
        lathe([(0, z1 - 0.4), (rt * 1.55, z1 - 0.4), (rt * 1.62, z1 + 0.5), (rt * 1.20, z1 + 1.6),
               (rt * 1.12, z1 + 2.4), (0, z1 + 2.4)], segments=SEG['round']), z_cm=[z1 - 0.4, z1 + 2.4])

    # six feet at the hexagon vertices
    fz0, fz1 = P['foot_span']
    for k in range(6):
        a = rot + k * TAU / 6
        c = (P['tier_lower_R'] * 0.86 * math.cos(a), P['tier_lower_R'] * 0.86 * math.sin(a), fz0)
        add(base, 'BaseFoot_%02d' % (k + 1), 'base_foot',
            lathe([(0, 0), (2.6, 0), (3.0, 0.35 * (fz1 - fz0)), (2.4, 0.75 * (fz1 - fz0)), (2.0, fz1 - fz0), (0, fz1 - fz0)],
                  c, segments=16), z_cm=[fz0, fz1])

    # raised rectangular relief panels: one on every face of every tier (calibration panel_divisions)
    for tag, (z0, z1), R, panel in (('Lower', P['tier_lower'], P['tier_lower_R'], P['panel_lower']),
                                    ('Upper', P['tier_upper'], P['tier_upper_R'], P['panel_upper']),
                                    ('Cap', P['ogee'], P['tier_upper_R'] * 0.94, P['panel_cap'])):
        side = R                                            # hexagon side length equals the circumradius
        wf, hf, depth = panel
        apothem = R * math.cos(math.pi / 6)
        for k in range(6):
            a = rot + math.pi / 6 + k * TAU / 6              # face normals sit between the vertices
            n_axis = (math.cos(a), math.sin(a), 0.0)
            u_axis = (-math.sin(a), math.cos(a), 0.0)
            v_axis = (0.0, 0.0, 1.0)
            zc = (z0 + z1) / 2.0 + (0.0 if tag != 'Cap' else -(z1 - z0) * 0.16)
            centre = (n_axis[0] * apothem * (1.0 if tag != 'Cap' else 0.90),
                      n_axis[1] * apothem * (1.0 if tag != 'Cap' else 0.90), zc)
            add(base, 'BasePanel_%s_%02d' % (tag, k + 1), 'base_panel',
                raised_panel(centre, u_axis, v_axis, n_axis, side * wf / 2.0, (z1 - z0) * hf / 2.0, depth),
                face=k + 1, tier=tag, relief_depth_cm=depth)

    # ---------------- central shaft ----------------
    z_bot = P['ogee'][1] - 1.0
    z_top = P['goblet_tiers_h'][0] + 1.0
    r0, r1, r2 = P['shaft_r']
    shaft = [(0, z_bot)]
    steps = 18
    for k in range(steps + 1):
        t = k / float(steps)
        z = z_bot + (z_top - z_bot) * t
        r = r0 + (r1 - r0) * min(1.0, t / 0.55) if t < 0.55 else r1 + (r2 - r1) * ((t - 0.55) / 0.45)
        shaft.append((r, z))
    shaft.append((0, z_top))
    add('SM_MenorahV4_Shaft', 'Shaft', 'shaft',
        lathe(shaft, segments=P['shaft_facets'], lobes=P['shaft_facets'] // 2, amp=P['shaft_facet_amp']),
        z_cm=[z_bot, z_top], radius_cm=[r0, r1, r2])

    # ---------------- six branches: concentric semicircle quarters ----------------
    for idx, radius in enumerate(P['arc_radii']):            # 0 inner .. 2 outer
        for side, sign in (('L', -1), ('R', 1)):
            pts, widths = branch_curve(radius, sign, SEG['arc'])
            add('SM_MenorahV4_Branches' + side, 'Branch_%s%d' % (side, idx + 1), 'branch',
                sweep_band(pts, widths, SEG['tube'], P['branch_depth_ratio'], P['branch_band'], P['branch_band_rise']),
                arc_radius_cm=radius, arc_centre_z_cm=P['arc_centre_z'], spring_z_cm=P['arc_centre_z'] - radius,
                section='rounded rectangle, broad flat front band, depth/width %.2f' % P['branch_depth_ratio'],
                curve='quarter of a circle concentric with the other two; vertical tangent at the stack')

    # ---------------- shaft junction knops and the lower central group ----------------
    def knop(part_id, span, dia, x=0.0, mesh=None, **meta):
        h = span[1] - span[0]
        add(mesh or orn, part_id, 'knop', lathe(knop_profile(h, dia), (x, 0, span[0]), SEG['round'],
                                                lobes=P['knop_bosses'], amp=0.035), x_cm=x, z_cm=list(span),
            diameter_cm=dia, **meta)
        rb = dia / 2.0
        for k in range(P['knop_bosses']):
            a = k * TAU / P['knop_bosses']
            n_axis = (math.cos(a), math.sin(a), 0.0)
            u_axis = (-math.sin(a), math.cos(a), 0.0)
            centre = (x + rb * 0.93 * math.cos(a), rb * 0.93 * math.sin(a), span[0] + 0.47 * h)
            add(mesh or orn, 'Boss_%s_%02d' % (part_id, k + 1), 'knop_boss',
                boss(centre, u_axis, (0.0, 0.0, 1.0), n_axis, rb * 0.30, h * 0.24, rb * P['knop_boss_r'], SEG['boss']))

    def flower(part_id, span, dia, x=0.0, lift=0.66, **meta):
        """Flared flower: a central bud in a collar with `flower_petals` upturned petals whose tips
        reach the calibrated half-diameter and rise `lift` of the calibrated height band (iteration 3;
        the first pass gave the petals a 2 cm band inside a 7 cm flower, so the silhouette stayed a
        narrow cup instead of the flared rim the photograph shows)."""
        h = span[1] - span[0]
        add(orn, part_id, 'flower', lathe(flower_cup_profile(h, dia * 0.74), (x, 0, span[0]), SEG['round'],
                                          lobes=6, amp=0.05), x_cm=x, z_cm=list(span), diameter_cm=dia, **meta)
        root, length = dia * 0.11, dia * 0.39
        curl = lift * h / length
        for k in range(P['flower_petals']):
            a = k * TAU / P['flower_petals'] + math.pi / P['flower_petals']
            u_axis = (math.cos(a), math.sin(a), 0.0)
            v_axis = (-math.sin(a), math.cos(a), 0.0)
            centre = (x + root * math.cos(a), root * math.sin(a), span[0] + 0.13 * h)
            add(orn, 'Petal_%s_%02d' % (part_id, k + 1), 'flower_petal',
                petal(centre, u_axis, v_axis, (0.0, 0.0, 1.0), length, dia * 0.19, dia * 0.032, curl))

    for k, span in enumerate(P['junction_span'], 1):
        knop('Knop_Junction_%02d' % k, span, P['junction_dia'],
             note='knop from which a pair of branches springs (Shemos 25:35); span from the photograph')
    flower('Flower_Shaft_Lower', P['lower_flower_low'], P['lower_flower_low_dia'], lift=-0.35,
           note='lower central flower, petals turned down (photograph)')
    knop('Knop_Shaft_Lower', P['lower_knop'], P['lower_knop_dia'], note='the single lower central knop')
    flower('Flower_Shaft_Upper', P['lower_flower_up'], P['lower_flower_up_dia'], lift=0.62,
           note='upper central flower of the lower group')

    # ---------------- seven upper groups ----------------
    tiers_h = P['goblet_tiers_h']
    for tag, x in zip(STACK_TAGS, LAMP_X):
        n_gob = 4 if tag == 'C' else 3
        bands = tiers_h[0:5] if n_gob == 4 else [tiers_h[0], tiers_h[1] + (tiers_h[2] - tiers_h[1]) * 0.0,
                                                 tiers_h[2], tiers_h[4]]
        if n_gob == 3:                                       # three equal tiers over the same band
            z0, z1 = tiers_h[0], tiers_h[4]
            bands = [z0 + (z1 - z0) * k / 3.0 for k in range(4)]
        scale = [0.80, 0.88, 0.96, 1.0]
        for j in range(n_gob):
            z0, z1 = bands[j], bands[j + 1]
            add(orn, 'Goblet_%s_%02d' % (tag, j + 1), 'goblet',
                lathe(goblet_profile(z1 - z0, P['goblet_dia'] * scale[j if n_gob == 4 else j + 1]),
                      (x, 0, z0), SEG['round'], lobes=P['goblet_flutes'], amp=0.038),
                x_cm=x, z_cm=[z0, z1], diameter_cm=P['goblet_dia'] * scale[j if n_gob == 4 else j + 1])
        knop('Knop_%s' % tag, P['knop_span'], P['knop_dia'], x=x)
        flower('Flower_%s' % tag, P['flower_span'], P['flower_dia'], x=x, lift=0.66)
        # stem between flower and lamp
        s0, s1 = P['stem_span']
        sh = s1 - s0
        add(orn, 'LampStem_%s' % tag, 'stem',
            lathe([(0, 0.0), (P['stem_dia'] * 0.62, 0.0), (P['stem_dia'] * 0.44, 0.30 * sh),
                   (P['stem_dia'] * 0.50, 0.72 * sh), (P['stem_dia'] * 0.70, sh), (0, sh)],
                  (x, 0, s0), SEG['round'], lobes=6, amp=0.10), x_cm=x, z_cm=[s0, s1])

        # lamp: broad shallow covered bowl, distinct rim, domed lid, finial, wick nozzle to the centre
        l0, l1 = P['lamp_span']
        add(lamps, 'Lamp_%s' % tag, 'lamp', lathe(lamp_profile(l1 - l0, P['lamp_dia']), (x, 0, l0), SEG['round'],
                                                  lobes=P['flower_petals'] * 2, amp=0.026),
            x_cm=x, z_cm=[l0, l1], rim_diameter_cm=P['lamp_dia'])
        d0, d1 = P['lid_span']
        add(lamps, 'LampLid_%s' % tag, 'lamp_lid', lathe(lid_profile(d1 - d0, P['lamp_dia']), (x, 0, d0), SEG['round'],
                                                         lobes=12, amp=0.02), x_cm=x, z_cm=[d0, d1])
        f0, f1 = P['finial_span']
        add(lamps, 'LampFinial_%s' % tag, 'lamp_finial',
            lathe(finial_profile(f1 - f0, P['lamp_dia'] * P['finial_dia_ratio']), (x, 0, f0), 20),
            x_cm=x, z_cm=[f0, f1])
        # side lamps point at the middle lamp; the middle lamp points west = local -Y (Rambam 3:8)
        direction = (0.0, -1.0, 0.0) if x == 0 else (-1.0 if x > 0 else 1.0, 0.0, 0.0)
        rr = P['lamp_dia'] / 2.0
        a = (x + direction[0] * rr * 0.52, direction[1] * rr * 0.52, l0 + 0.66 * (l1 - l0))
        b = (x + direction[0] * (rr + P['nozzle_len']), direction[1] * (rr + P['nozzle_len']), l0 + 0.94 * (l1 - l0))
        add(lamps, 'WickNozzle_%s' % tag, 'wick_nozzle',
            sweep_band([a, b], [P['nozzle_r'] * 2.6, P['nozzle_r'] * 1.05], 12, 0.72, 0.30, 1.0),
            x_cm=x, direction_local=list(direction),
            source='Rambam Beit HaBechirah 3:8 (six toward the middle lamp, the middle lamp toward the west)')

    # ---------------- three-step tending stone in front (local +Y) ----------------
    S = P['stone']
    # The hexagon has a VERTEX toward +Y, so the plinth's nearest point to the stone is its circumradius,
    # not its apothem; measuring the gap from the circumradius keeps the intended clear gap.
    y0 = P['tier_lower_R'] + S['gap']
    for k in range(S['steps']):
        depth = S['tread'] * (S['steps'] - k)
        z0, z1 = k * S['rise'], (k + 1) * S['rise']
        hw = S['width'] / 2
        poly = [(-hw, y0), (hw, y0)]
        rc = S['corner']
        for cx, sgn in ((hw - rc, 1), (-hw + rc, -1)):
            for m in range(0, 7):
                ang = (math.pi / 2) * m / 6
                if sgn > 0:
                    poly.append((cx + rc * math.cos(ang), y0 + depth - rc + rc * math.sin(ang)))
                else:
                    poly.append((cx - rc * math.sin(ang), y0 + depth - rc + rc * math.cos(ang)))
        add('SM_MenorahV4_StepStone', 'Step_%02d' % (k + 1), 'stone_step', prism(poly, z0, z1),
            z_cm=[z0, z1], y_cm=[y0, y0 + depth], width_cm=S['width'])
    return meshes, register


# ---------------------------------------------------------------- OBJ adapter / readback
def write_obj(name, parts, path):
    lines = ['# Original MenorahV4 %s; Unreal legacy OBJ adapter (Y reflected, winding reversed)' % name, 'o ' + name]
    index = 1
    allv = []
    checks = []
    for part_id, kind, (vertices, faces) in parts:
        vol = volume(vertices, faces)
        assert vol > 0 and closed(vertices, faces), part_id
        allv.extend(vertices)
        lines.append('g ' + part_id)
        for a, b, c in faces:
            p, q, r = [(vertices[i][0], -vertices[i][1], vertices[i][2]) for i in (a, c, b)]
            ab = [q[i] - p[i] for i in range(3)]
            ac = [r[i] - p[i] for i in range(3)]
            n = cross(ab, ac)
            length = math.sqrt(sum(x * x for x in ab))
            nl = math.sqrt(sum(x * x for x in n))
            assert nl > 1e-9 and length > 1e-9, 'degenerate triangle in ' + part_id
            for v in (p, q, r):
                lines.append('v %.7f %.7f %.7f' % v)
            for uv in ((0, 0), (length / 10, 0), (sum(ac[i] * ab[i] / length for i in range(3)) / 10, nl / length / 10)):
                lines.append('vt %.7f %.7f' % uv)
            for _ in range(3):
                lines.append('vn %.7f %.7f %.7f' % tuple(x / nl for x in n))
            lines.append('f ' + ' '.join('%d/%d/%d' % (k, k, k) for k in range(index, index + 3)))
            index += 3
        checks.append(dict(name=part_id, kind=kind, triangles=len(faces), closed=True, volume_cm3=vol))
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    bounds = {k: [fn(p[i] for p in allv) for i in range(3)] for k, fn in (('min', min), ('max', max))}
    return dict(name=name, file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                triangles=(index - 1) // 3, parts=len(parts), bounds_cm=bounds,
                minimum_part_signed_volume_cm3=min(c['volume_cm3'] for c in checks), part_checks=checks)


def readback(path, record):
    """Independent OBJ parse: counts, normals, UVs, Y-reflection round trip, file-space signed volume."""
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
    assert len(faces) == record['triangles']
    for face in faces:
        assert len(face) == 3
        a, b, c = [verts[f[0]] for f in face]
        cr = cross([b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)])
        area = math.sqrt(sum(x * x for x in cr))
        assert area > 1e-9
        assert sum(cr[i] * normals[face[0][2]][i] for i in range(3)) / area > .99999
        ua, ub, uc = [uvs[f[1]] for f in face]
        assert abs((ub[0] - ua[0]) * (uc[1] - ua[1]) - (ub[1] - ua[1]) * (uc[0] - ua[0])) > 1e-12
    canonical = [(x, -y, z) for x, y, z in verts]
    bounds = {k: [fn(v[i] for v in canonical) for i in range(3)] for k, fn in (('min', min), ('max', max))}
    error = max(abs(bounds[k][i] - record['bounds_cm'][k][i]) for k in bounds for i in range(3))
    assert error < 1e-4, error
    file_volume = volume(verts, [tuple(f[0] for f in face) for face in faces])
    assert file_volume > 0
    return dict(mesh=record['name'], triangles=len(faces), bounds_error_cm=error,
                file_space_signed_volume_cm3=file_volume, normals_and_uvs='PASS')


# ---------------------------------------------------------------- PNG in / out
def png_write(path, w, h, data, mode='gray'):
    def chunk(kind, payload):
        return struct.pack('!I', len(payload)) + kind + payload + struct.pack('!I', zlib.crc32(kind + payload) & 0xffffffff)
    stride = w if mode == 'gray' else w * 3
    scan = b''.join(b'\x00' + bytes(data[y * stride:(y + 1) * stride]) for y in range(h))
    ihdr = struct.pack('!2I5B', w, h, 8, 0 if mode == 'gray' else 2, 0, 0, 0)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(scan, 9)) + chunk(b'IEND', b''))


def png_read_gray(path):
    d = path.read_bytes()
    assert d[:8] == b'\x89PNG\r\n\x1a\n'
    i = 8
    w = h = None
    idat = b''
    while i < len(d):
        n = struct.unpack('!I', d[i:i + 4])[0]
        kind = d[i + 4:i + 8]
        payload = d[i + 8:i + 8 + n]
        if kind == b'IHDR':
            w, h, depth, colour = struct.unpack('!2I2B', payload[:10])
            assert depth == 8 and colour == 0, 'expected 8-bit grayscale'
        elif kind == b'IDAT':
            idat += payload
        elif kind == b'IEND':
            break
        i += 12 + n
    raw = zlib.decompress(idat)
    out = bytearray(w * h)
    for y in range(h):
        assert raw[y * (w + 1)] == 0, 'expected filter 0 rows'
        out[y * w:(y + 1) * w] = raw[y * (w + 1) + 1:(y + 1) * (w + 1)]
    return w, h, out


# ---------------------------------------------------------------- baseline JPEG luma decoder (pure Python)
ZIGZAG = [0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5,
          12, 19, 26, 33, 40, 48, 41, 34, 27, 20, 13, 6, 7, 14, 21, 28,
          35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37, 44, 51,
          58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63]
_COS = [[math.cos((2 * x + 1) * u * math.pi / 16) * (math.sqrt(0.5) if u == 0 else 1.0) for u in range(8)] for x in range(8)]


def _idct(blk):
    tmp = [0.0] * 64
    for y in range(8):
        row = y * 8
        for x in range(8):
            s = 0.0
            for u in range(8):
                v = blk[row + u]
                if v:
                    s += v * _COS[x][u]
            tmp[row + x] = s * 0.5
    out = [0.0] * 64
    for x in range(8):
        for y in range(8):
            s = 0.0
            for v in range(8):
                t = tmp[v * 8 + x]
                if t:
                    s += t * _COS[y][v]
            out[y * 8 + x] = s * 0.5
    return out


class _Bits(object):
    def __init__(self, d, i):
        self.d, self.i, self.b, self.n = d, i, 0, 0

    def bit(self):
        if self.n == 0:
            if self.i >= len(self.d):
                return 0
            c = self.d[self.i]
            self.i += 1
            if c == 0xFF:
                nxt = self.d[self.i] if self.i < len(self.d) else 0
                if nxt == 0x00:
                    self.i += 1
                elif not (0xD0 <= nxt <= 0xD7):
                    self.i -= 1
                    return 0
            self.b, self.n = c, 8
        self.n -= 1
        return (self.b >> self.n) & 1

    def bits(self, n):
        v = 0
        for _ in range(n):
            v = (v << 1) | self.bit()
        return v

    def decode(self, table):
        code = 0
        for length in range(1, 17):
            code = (code << 1) | self.bit()
            s = table.get((length, code))
            if s is not None:
                return s
        return 0

    def restart(self):
        self.n = 0
        while self.i < len(self.d) - 1:
            if self.d[self.i] == 0xFF and 0xD0 <= self.d[self.i + 1] <= 0xD7:
                self.i += 2
                return
            self.i += 1


def _huff(counts, symbols):
    table = {}
    code = k = 0
    for length in range(1, 17):
        for _ in range(counts[length - 1]):
            table[(length, code)] = symbols[k]
            k += 1
            code += 1
        code <<= 1
    return table


def _extend(v, t):
    if t == 0:
        return 0
    return v if v >= (1 << (t - 1)) else v - (1 << t) + 1


def decode_jpeg_luma(path):
    """Return (W, H, luma bytearray) for a baseline (SOF0/SOF1) JPEG. Chroma blocks are skipped."""
    d = path.read_bytes()
    qt, hdc, hac = {}, {}, {}
    W = Hh = 0
    comps = []
    ri = 0
    i = 2
    while i < len(d) - 1:
        if d[i] != 0xFF:
            i += 1
            continue
        m = d[i + 1]
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            i += 2
            continue
        if m == 0xD9:
            break
        L = struct.unpack('>H', d[i + 2:i + 4])[0]
        seg = d[i + 4:i + 2 + L]
        if m == 0xDB:
            p = 0
            while p < len(seg):
                pq, tq = seg[p] >> 4, seg[p] & 15
                p += 1
                tbl = [0] * 64
                for k in range(64):
                    if pq:
                        tbl[ZIGZAG[k]] = struct.unpack('>H', seg[p:p + 2])[0]
                        p += 2
                    else:
                        tbl[ZIGZAG[k]] = seg[p]
                        p += 1
                qt[tq] = tbl
        elif m == 0xC4:
            p = 0
            while p < len(seg):
                tc, th = seg[p] >> 4, seg[p] & 15
                p += 1
                counts = list(seg[p:p + 16])
                p += 16
                n = sum(counts)
                (hac if tc else hdc)[th] = _huff(counts, list(seg[p:p + n]))
                p += n
        elif m == 0xDD:
            ri = struct.unpack('>H', seg[0:2])[0]
        elif m in (0xC0, 0xC1):
            Hh, W = struct.unpack('>HH', seg[1:5])
            comps = [dict(id=seg[6 + 3 * k], h=seg[7 + 3 * k] >> 4, v=seg[7 + 3 * k] & 15, q=seg[8 + 3 * k])
                     for k in range(seg[5])]
        elif m == 0xC2:
            raise ValueError('progressive JPEG not supported: %s' % path)
        elif m == 0xDA:
            for k in range(seg[0]):
                for c in comps:
                    if c['id'] == seg[1 + 2 * k]:
                        c['dc'], c['ac'] = seg[2 + 2 * k] >> 4, seg[2 + 2 * k] & 15
            return _jpeg_scan(d, i + 2 + L, W, Hh, comps, qt, hdc, hac, ri)
        i += 2 + L
    raise ValueError('no baseline scan found in %s' % path)


def _jpeg_scan(d, pos, W, Hh, comps, qt, hdc, hac, ri):
    hmax = max(c['h'] for c in comps)
    vmax = max(c['v'] for c in comps)
    mcux = (W + 8 * hmax - 1) // (8 * hmax)
    mcuy = (Hh + 8 * vmax - 1) // (8 * vmax)
    yc = comps[0]
    yw, yh = mcux * yc['h'] * 8, mcuy * yc['v'] * 8
    plane = bytearray(yw * yh)
    br = _Bits(d, pos)
    pred = [0] * len(comps)
    n = 0
    for my in range(mcuy):
        for mx in range(mcux):
            if ri and n and n % ri == 0:
                br.restart()
                pred = [0] * len(comps)
            n += 1
            for ci, c in enumerate(comps):
                qtab = qt[c['q']]
                for by in range(c['v']):
                    for bx in range(c['h']):
                        t = br.decode(hdc[c['dc']])
                        pred[ci] += _extend(br.bits(t), t)
                        coef = [0.0] * 64
                        coef[0] = pred[ci] * qtab[0]
                        k = 1
                        while k < 64:
                            rs = br.decode(hac[c['ac']])
                            r, sz = rs >> 4, rs & 15
                            if sz == 0:
                                if r == 15:
                                    k += 16
                                    continue
                                break
                            k += r
                            if k > 63:
                                break
                            z = ZIGZAG[k]
                            coef[z] = _extend(br.bits(sz), sz) * qtab[z]
                            k += 1
                        if ci == 0:
                            px = _idct(coef)
                            ox, oy = (mx * c['h'] + bx) * 8, (my * c['v'] + by) * 8
                            for yy in range(8):
                                base = (oy + yy) * yw + ox
                                row = yy * 8
                                for xx in range(8):
                                    val = int(px[row + xx] + 128.5)
                                    plane[base + xx] = 0 if val < 0 else (255 if val > 255 else val)
    sx, sy = hmax // yc['h'], vmax // yc['v']
    out = bytearray(W * Hh)
    for y in range(Hh):
        rb = min(y // sy, yh - 1) * yw
        ob = y * W
        for x in range(W):
            out[ob + x] = plane[rb + min(x // sx, yw - 1)]
    return W, Hh, out


# ---------------------------------------------------------------- photograph silhouette
PHOTO_THRESHOLD = 95
PHOTO_KEEP_COMPONENTS = 2


def photo_silhouette(cache):
    """Threshold the reference photograph, keep the two largest components (upper structure + plinth),
    fill interior holes. Cached as an 8-bit PNG so a re-run does not repeat the pure-Python decode."""
    if cache.exists():
        w, h, mask = png_read_gray(cache)
        return w, h, bytearray(1 if v else 0 for v in mask)
    W, Hh, Y = decode_jpeg_luma(PHOTO)
    m = bytearray(1 if v >= PHOTO_THRESHOLD else 0 for v in Y)
    lab = [0] * (W * Hh)
    sizes = []
    cur = 0
    for s in range(W * Hh):
        if m[s] and not lab[s]:
            cur += 1
            st = [s]
            lab[s] = cur
            cnt = 0
            while st:
                p = st.pop()
                cnt += 1
                x, y = p % W, p // W
                for q, ok in ((p - 1, x > 0), (p + 1, x < W - 1), (p - W, y > 0), (p + W, y < Hh - 1)):
                    if ok and m[q] and not lab[q]:
                        lab[q] = cur
                        st.append(q)
            sizes.append((cnt, cur))
    sizes.sort(reverse=True)
    keep = set(c for _n, c in sizes[:PHOTO_KEEP_COMPONENTS])
    obj = bytearray(1 if lab[i] in keep else 0 for i in range(W * Hh))
    bg = bytearray(W * Hh)
    st = []
    for x in range(W):
        for y in (0, Hh - 1):
            i = y * W + x
            if not obj[i] and not bg[i]:
                bg[i] = 1
                st.append(i)
    for y in range(Hh):
        for x in (0, W - 1):
            i = y * W + x
            if not obj[i] and not bg[i]:
                bg[i] = 1
                st.append(i)
    while st:
        p = st.pop()
        x, y = p % W, p // W
        for q, ok in ((p - 1, x > 0), (p + 1, x < W - 1), (p - W, y > 0), (p + W, y < Hh - 1)):
            if ok and not obj[q] and not bg[q]:
                bg[q] = 1
                st.append(q)
    for i in range(W * Hh):
        if not bg[i]:
            obj[i] = 1
    png_write(cache, W, Hh, bytearray(255 if v else 0 for v in obj))
    return W, Hh, obj


def bbox_of(mask, W, Hh):
    xs = [x for x in range(W) if any(mask[y * W + x] for y in range(Hh))]
    ys = [y for y in range(Hh) if any(mask[y * W + x] for x in range(W))]
    return xs[0], xs[-1], ys[0], ys[-1]


def model_silhouette(meshes, W, Hh, box, hide=(), theta_deg=0.0, dx=0.0, dy=0.0):
    """Rasterise the model's FRONT elevation (orthographic, looking along -Y) into the photo's
    pixel grid, scaled and translated so the model's bounding box matches the photograph's."""
    pts = []
    for name, parts in meshes.items():
        if name in hide:
            continue
        for _pid, _kind, (v, _f) in parts:
            for p in v:
                pts.append((p[0], p[2]))
    mx0 = min(p[0] for p in pts)
    mx1 = max(p[0] for p in pts)
    mz0 = min(p[1] for p in pts)
    mz1 = max(p[1] for p in pts)
    px0, px1, py0, py1 = box
    sx = (px1 - px0 + 1) / float(mx1 - mx0)
    sy = (py1 - py0 + 1) / float(mz1 - mz0)

    cx, cy = (px0 + px1 + 1) / 2.0, (py0 + py1 + 1) / 2.0
    ct, st = math.cos(math.radians(theta_deg)), math.sin(math.radians(theta_deg))

    def project(p):
        u = px0 + (p[0] - mx0) * sx - cx
        v = py1 - (p[2] - mz0) * sy - cy
        return (cx + u * ct - v * st + dx, cy + u * st + v * ct + dy)

    mask = bytearray(W * Hh)
    for name, parts in meshes.items():
        if name in hide:
            continue
        for _pid, _kind, (v, faces) in parts:
            for a, b, c in faces:
                (ax, ay), (bx, by), (cx, cy) = project(v[a]), project(v[b]), project(v[c])
                det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
                if abs(det) < 1e-9:
                    continue
                ymin, ymax = max(0, int(min(ay, by, cy))), min(Hh - 1, int(max(ay, by, cy)) + 1)
                xmin, xmax = max(0, int(min(ax, bx, cx))), min(W - 1, int(max(ax, bx, cx)) + 1)
                for py in range(ymin, ymax + 1):
                    fy = py + 0.5
                    for pxi in range(xmin, xmax + 1):
                        fx = pxi + 0.5
                        w0 = ((by - cy) * (fx - cx) + (cx - bx) * (fy - cy)) / det
                        if w0 < 0:
                            continue
                        w1 = ((cy - ay) * (fx - cx) + (ax - cx) * (fy - cy)) / det
                        if w1 < 0 or w0 + w1 > 1:
                            continue
                        mask[py * W + pxi] = 1
    return mask, dict(model_box_cm=[mx0, mx1, mz0, mz1], photo_box_px=list(box),
                      roll_deg=theta_deg, shift_px=[dx, dy],
                      px_per_cm=[sx, sy], aspect_model=(mx1 - mx0) / (mz1 - mz0),
                      aspect_photo=(px1 - px0 + 1) / float(py1 - py0 + 1))


def iou(a, b):
    inter = union = 0
    for i in range(len(a)):
        if a[i] or b[i]:
            union += 1
            if a[i] and b[i]:
                inter += 1
    return inter / float(union or 1), inter, union


def downsample(mask, W, Hh, f):
    w, h = W // f, Hh // f
    out = bytearray(w * h)
    for y in range(h):
        base = y * f * W
        ob = y * w
        for x in range(w):
            v = 0
            for j in range(f):
                row = base + j * W + x * f
                for i in range(f):
                    if mask[row + i]:
                        v = 1
                        break
                if v:
                    break
            out[ob + x] = v
    return w, h, out


def shift_rotate(mask, w, h, theta_deg, dx, dy):
    """Inverse-map a binary mask by a rotation about its centre followed by a translation."""
    ct, st = math.cos(math.radians(-theta_deg)), math.sin(math.radians(-theta_deg))
    cx, cy = w / 2.0, h / 2.0
    out = bytearray(w * h)
    for y in range(h):
        v0 = y + 0.5 - cy - dy
        ob = y * w
        for x in range(w):
            u0 = x + 0.5 - cx - dx
            sxx = int(cx + u0 * ct - v0 * st)
            syy = int(cy + u0 * st + v0 * ct)
            if 0 <= sxx < w and 0 <= syy < h and mask[syy * w + sxx]:
                out[ob + x] = 1
    return out


def align_search(photo, model, W, Hh, factor=4, thetas=None, shifts=None):
    """Coarse rigid refinement of the bounding-box alignment on quarter-resolution masks.

    The reference photograph is rolled by about 4 degrees (calibration.json known_distortions), so a
    bounding-box-only overlap under-reports how well the FORM agrees. This reports the extra rigid
    transform and the score it reaches; the bounding-box score is still the headline number.
    """
    w, h, pm = downsample(photo, W, Hh, factor)
    _w, _h, mm = downsample(model, W, Hh, factor)
    best = (0.0, 0.0, 0.0, -1.0)
    for theta in (thetas if thetas is not None else [t * 0.5 for t in range(-14, 15)]):
        for dx in (shifts if shifts is not None else list(range(-8, 9))):
            for dy in (shifts if shifts is not None else list(range(-6, 7))):
                t = shift_rotate(mm, w, h, theta, dx, dy)
                score, _i, _u = iou(pm, t)
                if score > best[3]:
                    best = (theta, dx, dy, score)
    return dict(roll_deg=best[0], shift_px=[best[1] * factor, best[2] * factor],
                coarse_iou=round(best[3], 5), factor=factor)


def write_overlay(path, W, Hh, photo, model, luma=None):
    """Side by side: photograph silhouette | model silhouette | overlay (photo red, model blue, both gold)."""
    panels = 3
    out = bytearray([18, 20, 24] * (W * panels * Hh))
    for y in range(Hh):
        for x in range(W):
            i = y * W + x
            p, m = photo[i], model[i]
            g = luma[i] if luma else (230 if p else 20)
            for k, col in enumerate(((g, g, g) if luma else ((210, 205, 195) if p else (24, 26, 30)),
                                     (120, 170, 235) if m else (24, 26, 30),
                                     (226, 182, 84) if (p and m) else ((208, 78, 70) if p else ((92, 150, 225) if m else (18, 20, 24))))):
                o = (y * W * panels + k * W + x) * 3
                out[o:o + 3] = bytes(col)
    for y in range(Hh):
        for k in (1, 2):
            o = (y * W * panels + k * W) * 3
            out[o:o + 3] = bytes((70, 74, 80))
    png_write(path, W * panels, Hh, out, mode='rgb')


# ---------------------------------------------------------------- shaded software preview
def render_views(meshes, path, views, size=(1800, 900), skip=None):
    W, Hh = size
    rgb = bytearray([24, 28, 33] * (W * Hh))
    zbuf = [-1e18] * (W * Hh)
    panel_w = W // len(views)
    light = norm((-0.35, 0.65, 0.68))
    for k, (yaw, pitch, scale, _label) in enumerate(views):
        hidden = (skip or {}).get(k, ())
        u = (math.sin(math.radians(yaw)), math.cos(math.radians(yaw)))
        cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
        cam = (-u[0] * cp, -u[1] * cp, -sp)
        right = norm(cross((0.0, 0.0, 1.0), cam))
        up = cross(cam, right)
        x0 = k * panel_w + panel_w / 2
        base_y = Hh - 60 if pitch < 60 else Hh / 2
        for mesh, parts in meshes.items():
            if mesh in hidden:
                continue
            colour = (168, 160, 146) if 'Stone' in mesh else (214, 168, 78)
            for _pid, _kind, (v, faces) in parts:
                for a, b, c in faces:
                    pa, pb, pc = v[a], v[b], v[c]
                    n = cross(sub(pb, pa), sub(pc, pa))
                    ln = math.sqrt(sum(x * x for x in n)) or 1.0
                    if sum(n[i] * cam[i] for i in range(3)) > 0:
                        continue
                    shade = 0.38 + 0.62 * max(0.0, sum(n[i] * light[i] for i in range(3)) / ln)
                    col = bytes(min(255, int(x * shade)) for x in colour)
                    pts = []
                    for p in (pa, pb, pc):
                        sxp = sum(p[i] * right[i] for i in range(3))
                        szp = sum(p[i] * up[i] for i in range(3))
                        dd = -sum(p[i] * cam[i] for i in range(3))
                        pts.append((x0 + sxp * scale, base_y - (szp - (55 if pitch >= 60 else 0)) * scale, dd))
                    (ax, ay, ad), (bx, by, bd), (cx_, cy_, cd) = pts
                    det = (by - cy_) * (ax - cx_) + (cx_ - bx) * (ay - cy_)
                    if abs(det) < 1e-9:
                        continue
                    ymin, ymax = max(0, int(min(ay, by, cy_))), min(Hh - 1, int(max(ay, by, cy_)) + 1)
                    xmin, xmax = max(k * panel_w, int(min(ax, bx, cx_))), min((k + 1) * panel_w - 1, int(max(ax, bx, cx_)) + 1)
                    for py in range(ymin, ymax + 1):
                        fy = py + 0.5
                        for px in range(xmin, xmax + 1):
                            fx = px + 0.5
                            w0 = ((by - cy_) * (fx - cx_) + (cx_ - bx) * (fy - cy_)) / det
                            if w0 < 0:
                                continue
                            w1 = ((cy_ - ay) * (fx - cx_) + (ax - cx_) * (fy - cy_)) / det
                            w2 = 1 - w0 - w1
                            if w1 < 0 or w2 < 0:
                                continue
                            depth = w0 * ad + w1 * bd + w2 * cd
                            idx = py * W + px
                            if depth > zbuf[idx]:
                                zbuf[idx] = depth
                                rgb[idx * 3:idx * 3 + 3] = col
        for py in range(Hh):
            idx = py * W + k * panel_w
            rgb[idx * 3:idx * 3 + 3] = bytes((60, 64, 70))
        for px in range(int(k * panel_w + 20), int(k * panel_w + 20 + AMAH * scale)):
            for py in (Hh - 24, Hh - 23, Hh - 22):
                rgb[(py * W + px) * 3:(py * W + px) * 3 + 3] = bytes((230, 230, 230))
    png_write(path, W, Hh, rgb, mode='rgb')
    return [v[3] for v in views]


# ---------------------------------------------------------------- dimension / deviation tables
def dimension_table(records):
    union = {k: [fn(m['bounds_cm'][k][i] for m in records if 'Stone' not in m['name']) for i in range(3)]
             for k, fn in (('min', min), ('max', max))}
    S = P['stone']
    rows = [
        ('overall height, floor to the top of the central finial', union['max'][2], '18 tefachim', 'halachic',
         'Rambam Beit HaBechirah 3:10; book "Lishchno Tidreshu" p. 252; 8.333 cm tefach at the 50 cm amah'),
        ('overall width across the outer lamp rims', union['max'][0] - union['min'][0], None, 'photo-calibrated',
         'calibration.json normalised_to_H.overall.width_over_H_including_lamp_bowls = 0.6749'),
        ('branch semicircle radii (inner, middle, outer)', P['arc_radii'], None, 'photo-calibrated',
         'calibration radii_over_H 0.1100 / 0.2098 / 0.3003; ratio 1 : 1.906 : 2.729, NOT 1:2:3'),
        ('branch semicircle common centre height', P['arc_centre_z'], None, 'photo-calibrated',
         'calibration common_centre_h 0.7621; the three fitted centres scatter 2.3 px'),
        ('branch spring points on the shaft (outer, middle, inner)',
         [P['arc_centre_z'] - r for r in reversed(P['arc_radii'])], 'Menachos 28b would say tefachim 9, 11, 13',
         'photo-calibrated, deviates from the Talmudic breakdown',
         'photograph: h 0.4589 / 0.5554 / 0.6519 = 68.8 / 83.3 / 97.8 cm; Menachos 28b: 75.0 / 91.7 / 108.3 cm'),
        ('branch tube width, foot -> tip', P['branch_diameter'], None, 'photo-calibrated',
         'calibration branch_tube diameters 0.0273 -> 0.0254 H'),
        ('branch section', 'rounded rectangle, depth/width %.2f, broad flat front band' % P['branch_depth_ratio'],
         None, 'form photo-calibrated, depth authored', 'dossier: "rectangular-ish section with a flat decorated front band"; depth is not recoverable from a frontal photograph'),
        ('central shaft radius (above base / between junctions / under the stack)', P['shaft_r'], None, 'photo-calibrated',
         'calibration central_shaft 0.0235 / 0.0150 / 0.0143 H'),
        ('goblets (gevi\'im)', 22, '22 = 6 x 3 + 4', 'halachic count, photo-calibrated band',
         'Shemos 25:33-34; goblet band h 0.7823-0.8631, four tiers on the shaft and three on each branch, same tier height'),
        ('knops (kaftorim)', 11, '11 = 7 upper + 3 junction + 1 lower', 'halachic count, photo-calibrated spans',
         'Shemos 25:33-35; upper knop h 0.8644-0.8983, junctions h 0.4589-0.4941 / 0.5554-0.5920 / 0.6519-0.6897'),
        ('flowers (perachim)', 9, '9 = 7 upper + 2 lower central', 'halachic count, photo-calibrated spans',
         'Shemos 25:31-34; upper flower h 0.8996-0.9283; lower central flowers h 0.3598-0.4081 and 0.2803-0.3233'),
        ('lamps', 7, '7 in one line', 'halachic count, photo-calibrated size',
         'Shemos 25:37; Rambam 3:12 (row north-south); bowl h 0.9478-0.9752, rim diameter 0.0743 H'),
        ('lamp lid, finial, wick nozzle', [P['lid_span'], P['finial_span'], P['nozzle_len']], None,
         'photo-calibrated heights, authored nozzle', 'the TI lamps are covered bowls with a finial; the nozzle direction follows Rambam 3:8, its size is authored'),
        ('base: stepped hexagon, vertex to the front; tiers bottom -> top',
         [P['foot_span'], P['tier_lower'], P['tier_lower_cap'], P['tier_upper'], P['ogee']], None, 'photo-calibrated',
         'calibration base.tiers_bottom_to_top; circumradii 0.2394 / 0.2454 / 0.1889 H'),
        ('base raised relief panels', 18, '6 faces x 3 tiers', 'photo-calibrated divisions, authored motif',
         'calibration base.panel_divisions; the panel FIELDS are modelled, the acanthus/vine motifs inside them are not traced'),
        ('wick directions', 'six toward the middle lamp, the middle lamp toward the west (local -Y)', None, 'halachic',
         'Rambam Beit HaBechirah 3:8'),
        ('tending stone: three steps in front (east)', [S['steps'], S['rise'], S['tread'], S['width']], '3 steps',
         'halachic count/position, authored sizes', 'Rambam 3:11; book p. 252 (2); diagram 22:23b'),
        ('orientation', 'lamp row north-south (placement yaw -90)', None, 'halachic',
         'Rambam Beit HaBechirah 3:12; book diagram 22:23b'),
    ]
    return [dict(item=i, value_cm=v, halachic=h, kind=k, source=s) for i, v, h, k, s in rows]


# ---------------------------------------------------------------- export
def export(force=False, with_photo=True):
    manifest_path = OUT / 'geometry-manifest.json'
    if manifest_path.exists() and not force:
        raise SystemExit('Frozen generation preserved: %s exists (use --force to regenerate)' % manifest_path)
    OUT.mkdir(parents=True, exist_ok=True)
    meshes, register = geometry()

    counts = {}
    for entry in register:
        counts[entry['kind']] = counts.get(entry['kind'], 0) + 1
    expected = dict(goblet=22, knop=11, flower=9, lamp=7, wick_nozzle=7, branch=6, stone_step=3,
                    base_panel=18, base_foot=6, lamp_lid=7, lamp_finial=7, stem=7)
    for kind, n in expected.items():
        assert counts.get(kind) == n, (kind, counts.get(kind), n)

    records, checks = [], []
    for name, parts in meshes.items():
        record = write_obj(name, parts, OUT / (name + '.obj'))
        record['material_role'] = 'stone' if 'Stone' in name else 'gold'
        record['collision'] = 'BlockAll' if name in ('SM_MenorahV4_Base', 'SM_MenorahV4_StepStone') else 'NoCollision'
        checks.append(readback(OUT / record['file'], record))
        records.append(record)
    total = sum(m['triangles'] for m in records)
    assert total < 300000, total
    menorah_records = [m for m in records if 'Stone' not in m['name']]
    union = {k: [fn(m['bounds_cm'][k][i] for m in menorah_records) for i in range(3)] for k, fn in (('min', min), ('max', max))}

    silhouette = dict(status='skipped (--no-photo)')
    if with_photo and PHOTO.exists():
        W, Hh, photo = photo_silhouette(OUT / 'photo-silhouette.png')
        box = bbox_of(photo, W, Hh)
        model, fit = model_silhouette(meshes, W, Hh, box, hide=('SM_MenorahV4_StepStone',))
        score, inter, uni = iou(photo, model)
        png_write(OUT / 'menorah-v4-silhouette.png', W, Hh, bytearray(255 if v else 0 for v in model))
        photo_only = sum(1 for i in range(W * Hh) if photo[i] and not model[i])
        model_only = sum(1 for i in range(W * Hh) if model[i] and not photo[i])
        refine = align_search(photo, model, W, Hh)
        aligned, afit = model_silhouette(meshes, W, Hh, box, hide=('SM_MenorahV4_StepStone',),
                                         theta_deg=refine['roll_deg'], dx=refine['shift_px'][0],
                                         dy=refine['shift_px'][1])
        ascore, ainter, auni = iou(photo, aligned)
        write_overlay(OUT / 'menorah-v4-photo-overlay.png', W, Hh, photo, aligned)
        write_overlay(OUT / 'menorah-v4-photo-overlay-bbox.png', W, Hh, photo, model)
        silhouette = dict(
            status='computed', photograph=str(PHOTO.relative_to(ROOT)).replace(chr(92), '/'),
            photo_pixels=[W, Hh], photo_threshold=PHOTO_THRESHOLD, alignment='bounding box of the model front '
            'elevation scaled and translated onto the bounding box of the thresholded photograph',
            intersection_over_union=round(score, 5), intersection_px=inter, union_px=uni,
            photo_only_px=photo_only, model_only_px=model_only, fit=fit,
            roll_refined=dict(
                note='The photograph is rolled by about 4 degrees (calibration.json known_distortions), so a '
                     'bounding-box-only overlap penalises a perfectly level model. This second score adds ONLY a '
                     'rigid in-plane rotation and translation found by a coarse search on quarter-resolution '
                     'masks - no scaling and no per-part fitting. The headline number above stays the '
                     'bounding-box-aligned one.',
                roll_deg=refine['roll_deg'], shift_px=refine['shift_px'], coarse_iou=refine['coarse_iou'],
                intersection_over_union=round(ascore, 5), intersection_px=ainter, union_px=auni,
                photo_only_px=sum(1 for i in range(W * Hh) if photo[i] and not aligned[i]),
                model_only_px=sum(1 for i in range(W * Hh) if aligned[i] and not photo[i])),
            images=dict(photo_mask='photo-silhouette.png', model_mask='menorah-v4-silhouette.png',
                        side_by_side='menorah-v4-photo-overlay.png (roll-refined model)',
                        side_by_side_bbox='menorah-v4-photo-overlay-bbox.png (bounding-box alignment only)'),
            limit='IoU over one uncorrected photograph that carries roll, a small yaw and glass-case blur. '
                  'A perfect model cannot score 1.0 here.')
        log = []
        if SILHOUETTE_LOG.exists():
            log = json.loads(SILHOUETTE_LOG.read_text(encoding='utf-8'))
        log.append(dict(run=len(log) + 1, iou_bbox=round(score, 5), iou_roll_refined=round(ascore, 5),
                        roll_deg=refine['roll_deg'], photo_only_px=photo_only, model_only_px=model_only,
                        triangles=total,
                        parameters=dict(arc_radii=P['arc_radii'], arc_centre_z=P['arc_centre_z'],
                                        branch_diameter=P['branch_diameter'],
                                        branch_depth_ratio=P['branch_depth_ratio'],
                                        lamp_dia=P['lamp_dia'], knop_dia=P['knop_dia'], goblet_dia=P['goblet_dia'],
                                        flower_dia=P['flower_dia'], junction_dia=P['junction_dia'],
                                        shaft_r=P['shaft_r'], tier_lower_R=P['tier_lower_R'],
                                        tier_upper_R=P['tier_upper_R'], goblet_band=P['goblet_band'])))
        SILHOUETTE_LOG.write_text(json.dumps(log, indent=2) + chr(10), encoding='utf-8')
        silhouette['iterations'] = log

    preview = render_views(meshes, OUT / 'menorah-v4-preview.png', [
        (0, 0, 4.6, 'front elevation: looking west from the east (north on the right); tending stone hidden'),
        (-90, 0, 4.6, 'side elevation: looking north from the south (east and the tending stone on the right)'),
        (-38, 26, 3.6, 'oblique from the south-east above'),
    ], (2100, 900), skip={0: ('SM_MenorahV4_StepStone',)})

    manifest = dict(
        status='OFFLINE_VALIDATED_PHOTO_CALIBRATED_NATIVE_AND_VISUAL_PENDING', namespace=DEST,
        amah_cm=AMAH, tefach_cm=TEFACH,
        script='Scripts/create_menorah_v4.py', script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        calibration='SourceAssets/vessels-review/MenorahV4/calibration.json',
        calibration_sha256=hashlib.sha256(CALIBRATION.read_bytes()).hexdigest() if CALIBRATION.exists() else None,
        reference_spec='SourceAssets/vessels-review/menorah-model-spec.json',
        reference_spec_sha256=hashlib.sha256((ROOT / 'SourceAssets/vessels-review/menorah-model-spec.json').read_bytes()).hexdigest(),
        supersedes='SourceAssets/vessels-review/MenorahV3 (generic proportions; quarter-ellipse branches, circular tubes)',
        convention='Canonical XYZ Unreal cm: local X = lamp row (fan axis; +X = north after the placement yaw -90), '
                   'local +Y = front (east; the tending stone side), Z up, origin at the centre of the base contact '
                   'plane on the floor; every part shares this pivot. OBJ files carry Y reflected and winding reversed '
                   'for the legacy OBJ importer (ShulchanV2 / DoorsParochesV1 / MenorahV3 adapter); the importer '
                   'reflects Y back, so imported bounds must equal bounds_cm and UE signed volumes must be positive. '
                   'Per-triangle normals and non-degenerate planar UV charts; no images, no scanned or traced geometry.',
        claims='Original parametric model whose PROPORTIONS were measured from one Temple Institute photograph '
               '(calibration.json). Photograph-derived proportion, not a measured survey of the vessel, not a '
               'rabbinically certified vessel, and not a verified appearance of the future Temple menorah.',
        parameters={k: v for k, v in P.items()},
        lamp_x_cm=LAMP_X, menorah_bounds_cm=union,
        half_span_x_cm=max(-union['min'][0], union['max'][0]),
        counts=counts,
        count_contract=dict(lamps=7, side_branches=6, goblets_total=22, goblets_each_side_branch=3,
                            goblets_central_shaft=4, knops_total=11, knops_upper_groups=7, knops_branch_junctions=3,
                            knops_lower_central=1, flowers_total=9, flowers_upper_groups=7, flowers_lower_central=2,
                            source='Shemos 25:31-40; menorah-model-spec count_contract; TI states 42 ornaments'),
        ornaments=register,
        dimensions=dimension_table(records),
        silhouette_check=silhouette,
        differences_from_v3=[
            'Branches are quarters of three CONCENTRIC CIRCLES (radii 16.50 / 31.47 / 45.05 cm about one point at '
            'z 114.3), not quarter ellipses. The radii are measured, and their ratio 1 : 1.906 : 2.729 is not 1:2:3.',
            'Branch and shaft sections are rounded rectangles with a broad slightly proud flat front band, not '
            'circular tubes.',
            'Junction heights come from the photograph (68.8 / 83.3 / 97.8 cm), not from the Menachos 28b tefachim '
            '(75.0 / 91.7 / 108.3 cm). The Talmudic values are recorded as the deviation.',
            'Goblets are almond/cup profiles with a defined outward lip and a stem foot; knops are flattened spheres '
            'with a foot collar and twelve raised cartouche bosses; flowers have separately modelled flared petals.',
            'The base is a stepped hexagonal plinth with a vertex to the front, six feet, an ogee cap, a round stem '
            'collar and eighteen raised rectangular relief panels (one per face per tier).',
            'The lamps are broad shallow covered bowls with a distinct outward rim, a domed lid and a finial; the '
            'wick nozzle is a flattened spout turned toward the centre.',
            'Overall width/height is 0.675 (measured) instead of V3\'s hand-chosen 18 cm lamp pitch.',
        ],
        not_modelled=[
            'Relief MOTIFS: the acanthus/vine of the plinth panels, the cartouche and bead ornament of the knops, '
            'the leaf ornament of the goblets and the lamp lids. Only their fields and bounding proportions exist.',
            'Depth (front to back) of every part: one photograph gives no depth. Authored.',
            'The rear of the object, which no available photograph shows.',
            'Flames, oil, wicks, service tools; there is no shamash.',
            'The straight-branch Rambam-sketch variant (dossier records it as kosher and as an authored switch).',
        ],
        total_triangles=total, meshes=records, readback=checks,
        previews={'menorah-v4-preview.png': preview},
        preview_limit='Software orthographic source preview with illustrative gold/stone colours; not a native '
                      'render and not material acceptance.',
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    if '--export' in sys.argv:
        result = export(force='--force' in sys.argv, with_photo='--no-photo' not in sys.argv)
        print(json.dumps(dict(status=result['status'], total_triangles=result['total_triangles'],
                              counts=result['counts'], menorah_bounds_cm=result['menorah_bounds_cm'],
                              half_span_x_cm=result['half_span_x_cm'],
                              silhouette=dict((k, v) for k, v in result['silhouette_check'].items()
                                              if k in ('intersection_over_union', 'photo_only_px', 'model_only_px',
                                                       'roll_refined')),
                              meshes=[(m['name'], m['triangles']) for m in result['meshes']]), indent=2))
    else:
        raise SystemExit('Use --export (offline OBJ + manifest + preview + silhouette check); native import is '
                         'Scripts/release_import_menorah_v4.py')
