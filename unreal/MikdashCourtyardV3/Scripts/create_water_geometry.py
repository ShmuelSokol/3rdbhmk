"""MikdashWaterV1: the stream of Yechezkel 47, its channel through the courts, and the mikvaot.

Offline only. --export writes SourceAssets/water-review/MikdashWaterV1/: OBJ parts, a
geometry-manifest.json, a clearance report against the architecture manifest, and a plan
preview. No engine launch, no Content/ change, no map action. Native import and placement
live in Scripts/release_water.py.

WHAT THIS DEPICTS, AND ON WHAT AUTHORITY
----------------------------------------
Every claim, with its status (certain / disputed / authored), is in
SourceAssets/water-review/sources.md. The short version:

  CERTAIN (Yechezkel 47:1-5, plain text)
    - water issues from under the threshold of the House, eastward
    - it comes down from under the right (south) side of the House, SOUTH OF THE ALTAR
    - at the outer east gate it trickles from the right (south) shoulder
    - the man measures FOUR times a thousand amot: ankles, knees, loins, and then a
      river that cannot be crossed

  DISPUTED (recorded, and the divergence is modelled)
    - THE ROUTE. This project's primary source, the user's book "Lishchno Tidreshu"
      (p. 340, on Yechezkel 42:12), reads the stream as issuing from the KODESH
      HAKODASHIM and leaving by the SOUTHERN gate of the inner court -- which is why
      that gate is called Shaar HaMayim. The plain sense of 47:1-2 has it leave by the
      OUTER EAST gate's south shoulder. This script builds the EAST route as the
      primary geometry and emits the south-gate reading as a separate optional branch
      (group 'southgate'), so both can be seen. Neither is asserted over the other.
    - WHETHER THE FOUR STAGES ARE LITERAL DISTANCES. Built here as literal, because
      this is a measured reconstruction; the schematic reading is recorded, not built.

  AUTHORED (this project's invention, no textual source)
    - every WIDTH and every DEPTH in centimetres. The text names body parts, not
      numbers; the depths are anthropometric fractions of an assumed 170 cm stature
      (see WaterFlowMath.h). No source gives a channel width anywhere.
    - the channel's construction: bed, kerbs, cover slabs, cascade steps.
    - all four mikvaot's dimensions. The book gives their LOCATIONS (and marks even
      those with its asterisk, "for study only"); it gives no dimension, no step count
      and no partition. The pools are sized to clear forty se'ah on the most stringent
      opinion by a wide margin and to fit a person.

  NOT DEPICTED, ONLY ASSERTED (Yechezkel 47:8-12; all far outside the map)
    - the descent to the Aravah and into the sea; the healing of the sea's waters;
      fishermen from Ein Gedi to Ein Eglayim; the marshes and swamps left for salt;
      the trees on both banks whose leaf does not wither and whose fruit does not fail,
      bearing new fruit every month, the fruit for food and the leaf for healing.
      The Dead Sea is some 35 km from the Mount; the built channel stops at the fourth
      measurement, 4000 amot (2.0 km at the project amah) east of the outer gate.

WHAT IS NOT MINE TO CUT
-----------------------
The courtyard paving, the Ulam stair, the platforms and the gate thresholds are imported
architecture owned by other work. A channel through a courtyard is by nature a CUT in
that paving, and nothing here can boolean an imported mesh. So the generated channel is
placed where the cut would be, and every architecture mesh it necessarily occupies is
enumerated in the clearance report as a HOST (paving the conduit is cut into, or a stair
it rests on) rather than silently ignored. Anything that is NOT paving -- the altar, its
ramp, the kiyor, gate jambs, chambers, vessels -- is a BLOCKER, and the export fails if
the channel touches one. The numbers are in clearance.json.

Conventions: centimetres, canonical Unreal axes X east, +Y SOUTH, Z up (confirmed against
SourceAssets/architecture-manifest.json: the altar's kevesh, which is on the south, runs
+Y; the inner south threshold is at +Y). Amah 50 cm, as everywhere else in this project.
OBJ files are written for the legacy Unreal OBJ importer adapter proven here (Y reflected,
triangle winding reversed; the importer reflects Y back) - the same adapter as
create_keilim_ti_v1.py and create_oldcity_facades.py.

  python Scripts/create_water_geometry.py --export
  python Scripts/create_water_geometry.py            -> offline summary as JSON
"""
import argparse
import hashlib
import json
import math
import struct
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets/water-review/MikdashWaterV1'
OBJ_DIR = OUT / 'obj'
ARCH_MANIFEST = ROOT / 'SourceAssets/architecture-manifest.json'
DEST = '/Game/MikdashV3/MaterialReview/MikdashWaterV1'

AMAH = 50.0
TEFACH = AMAH / 6.0

TRIANGLE_BUDGET = 220000

# =====================================================================================
# 1. Fixed points read out of SourceAssets/architecture-manifest.json
# =====================================================================================
# Not invented here. Each row is the expectedBoundsUnrealCm of the named source mesh (or
# the union of a named group) in that manifest, which is the authority for where the
# built Temple actually is in this map. verify_anchors() re-reads them at export time and
# fails if the manifest has moved, so this block can never silently go stale.

ANCHORS = {
    # the House and its threshold
    'Ulam nested stone door frame': dict(min=[-2507.5, -457.5, 925.0], max=[-2457.5, 457.5, 3425.0]),
    'Ulam clear floor':             dict(min=[-3300.0, -500.0, 905.0], max=[-2750.0, 500.0, 925.0]),
    'Ulam stair':                   dict(min=[-2500.0, -985.0, 625.0], max=[-1400.0, 985.0, 925.0]),
    'Heichal clear floor':          dict(min=[-5600.0, -500.0, 905.0], max=[-3600.0, 500.0, 925.0]),
    'Kodesh clear floor':           dict(min=[-6700.0, -500.0, 905.0], max=[-5700.0, 500.0, 925.0]),
    # the altar and its ramp
    'Altar yesod':                  dict(min=[-800.0, -800.0, 625.0], max=[800.0, 800.0, 716.7]),
    'Altar upper tier':             dict(min=[-708.3, -708.3, 916.7], max=[708.3, 708.3, 1066.7]),
    'Southern kevesh':              dict(min=[-400.0, 710.1, 625.0], max=[400.0, 2300.0, 1066.7]),
    # the kiyor, already in the map
    'Kiyor basin':                  dict(min=[-2054.0, 1396.0, 690.0], max=[-1846.0, 1604.0, 750.0]),
    # floors the channel runs on
    'Ezras Kohanim floor':          dict(min=[-2500.0, -2500.0, 605.0], max=[1575.0, 2500.0, 625.0]),
    'Duchan rise':                  dict(min=[1575.0, -2500.0, 500.0], max=[1675.0, 2500.0, 625.0]),
    'Inner court clear floor':      dict(min=[1675.0, -2500.0, 480.0], max=[2500.0, 2500.0, 500.0]),
    'Outer court floor':            dict(min=[-7800.0, -7800.0, 280.0], max=[7800.0, 7800.0, 300.0]),
    # the gates
    # Both of these are MIRRORED PAIRS in the manifest (a north and a south member with
    # the same source name). The stream keeps to the right/south side throughout, so the
    # anchor names the south member; without side= the union of the pair spans the whole
    # gate and the check fails by the 3050 cm between the two jambs.
    'Inner eastern gate wall jamb': dict(side='south', min=[2500.0, 250.0, 500.0], max=[2800.0, 2800.0, 3500.0]),
    'Inner E cell supporting plinth': dict(side='south', min=[2800.0, 375.0, 300.0], max=[3600.0, 2275.0, 499.0]),
    'Outer E vestibule floor':      dict(min=[7300.0, -625.0, 280.0], max=[7800.0, 625.0, 300.0]),
    'Outer E threshold':            dict(min=[7800.0, -250.0, 280.0], max=[8100.0, 250.0, 300.0]),
    'Outer E cell access landing':  dict(min=[8100.0, -625.0, 280.0], max=[8600.0, 625.0, 300.0]),
    'Outer E stair':                dict(min=[8600.0, -250.0, 0.0], max=[9200.0, 250.0, 300.0]),
    'Inner S threshold':            dict(min=[-250.0, 2500.0, 605.0], max=[250.0, 2800.0, 625.0]),
    'Outer S threshold':            dict(min=[-250.0, 7800.0, 405.0], max=[250.0, 8100.0, 425.0]),
    # chambers the mikvaot go in
    'Song chamber':                 dict(min=[-2225.0, 1875.0, 605.0], max=[-1675.0, 2425.0, 1075.0]),
    'Priestly chamber precinct':    dict(min=[-7500.0, -5250.0, 405.0], max=[-2500.0, 5250.0, 425.0]),
}

# Which manifest source names are legitimately CUT INTO or RESTED ON by a courtyard
# conduit. Anything not on this list that the channel touches is a blocker and fails.
HOST_MESH_NAMES = (
    'Ulam stair',
    'Ezras Kohanim floor',
    'Raised priest court foundation',
    'Duchan rise',
    'Inner court clear floor',
    'Inner court supporting platform',
    'Inner E cell supporting plinth',
    'Inner E continuous cell doorway floor',
    'Outer court floor',
    'Outer court supporting platform',
    'Western outer court foundation',
    'Outer E vestibule floor',
    'Outer E threshold',
    'Outer E cell access landing',
    'Outer E stair',
    'Outer S threshold',
    'Inner S threshold',
    'Inner S vestibule floor',
    'Inner S stair',
    'Priestly room floor',
    'Priestly chamber precinct',
    'Court string course and cornice',
    'Derived union of source western paving and transition',
)

# Hollow derived-union envelopes whose AABB encloses most of the site; overlapping their
# AABB proves nothing. release_place_assets.py records the same 2026-09-07 false positive.
HOLLOW_UNION_NAMES = (
    'Derived union of source outer envelope walls',
    'Derived union of source House walls and roofs',
    'Derived union of source raised gallery slabs',
    'Derived union of House and Ulam foundations',
)

# =====================================================================================
# 2. The stream: route, section and the four stages
# =====================================================================================
# Depths are the anthropometric figures of WaterFlowMath.h, restated here so the geometry
# and the runtime cannot drift apart; verify_against_header() re-reads the header at
# export time and fails if they do.

STATURE_CM = 170.0
STAGE_DEPTH_CM = [0.6, 0.07 * STATURE_CM, 0.285 * STATURE_CM, 0.53 * STATURE_CM, 1.05 * STATURE_CM]
STAGE_TOP_WIDTH_AMOT = [1.0, 4.0, 10.0, 20.0, 50.0]
STAGE_LABELS = ['trickle at the gate (mefakim, 47:2)', 'to the ankles (afsayim, 47:3)',
                'to the knees (birkayim, 47:4)', 'to the loins (motnayim, 47:4)',
                'a river that could not be passed over (47:5)']
STAGE_SPACING_AMOT = 1000.0

# The datum from which the prophet's thousands are measured: the outer (east) face of the
# outer east gate's threshold, which is where 47:2-3 puts the man before he goes forth.
MEASURE_DATUM_X = 8100.0

BANK_SIDE_SLOPE = 1.2          # horizontal per vertical on the bank faces
KERB_ABOVE_WATER_CM = 8.0      # the kerb stands this proud of the design water surface
BANK_THICKNESS_CM = 22.0       # thickness of the kerb masonry either side
BED_THICKNESS_CM = 14.0        # thickness of the bed slab under the water
COURT_SINK_CM = 35.0           # how far the bed sits below the paving it is cut into
FAR_FIELD_GRADE = 0.025        # 2.5% descent east of the mount: AUTHORED

# The channel through the courts. Each row is (x, y, surface_top_z, note). The bed is
# COURT_SINK_CM below surface_top_z except where 'bed' is given explicitly, and 'cover'
# marks a reach that runs beneath a structure and is closed over with a slab.
COURT_ROUTE = [
    # --- 47:1, from under the threshold of the House, eastward, on its right (south) side
    dict(x=-2478.0, y=400.0, top=925.0, note='under the threshold of the House (miftan habayis), its right/south end'),
    dict(x=-2400.0, y=430.0, top=903.7, note='onto the Ulam stair, resting on the tread'),
    dict(x=-2100.0, y=560.0, top=821.8, note='cascade down the stair, bearing right'),
    dict(x=-1800.0, y=760.0, top=740.0, note='cascade'),
    dict(x=-1500.0, y=940.0, top=658.2, note='cascade, last treads'),
    dict(x=-1400.0, y=1000.0, top=631.0, note='foot of the stair'),
    # --- 47:1, "on the south of the altar" (minegev lamizbeach)
    dict(x=-1000.0, y=1050.0, top=625.0, note='running line across the Ezras Kohanim'),
    dict(x=-600.0, y=1050.0, top=625.0, note='south of the altar; 225 cm clear of the yesod'),
    dict(x=-420.0, y=1050.0, top=625.0, note='enters the covered reach under the kevesh'),
    dict(x=420.0, y=1050.0, top=625.0, cover=True, note='conduit beneath the altar ramp, cover flush at Z 625'),
    dict(x=1000.0, y=1050.0, top=625.0, note='east of the ramp, open again'),
    dict(x=1575.0, y=1050.0, top=625.0, note='at the duchan rise'),
    dict(x=1675.0, y=1050.0, top=500.0, note='down the duchan, onto the inner court floor'),
    dict(x=2400.0, y=1050.0, top=500.0, note='inner court floor'),
    # --- beneath the inner court's east range (the jamb stands from Z 500; bed at 445)
    # The bed levels through the east range are set by CLEARANCE, not by taste. The gate
    # wall jamb, the cell connecting doorways and their lintels all stand from Z 500 up;
    # the cell plinth occupies Z 300-499. The conduit must therefore live wholly inside
    # that 300-499 band. A cover slab stands COURT_WATER_DEPTH_CM + 26 cm above its bed,
    # so a bed of 450 puts the slab top at 485 and leaves 15 cm under the jamb. The
    # earlier 478/460/445 put the slab top at 513/495/480 and drove the slab straight
    # through the jamb footing at the entry; clearance.json now measures the gap.
    dict(x=2500.0, y=1050.0, top=500.0, bed=450.0, cover=True, note='enters the conduit under the inner gate wall (slab top 485, jamb foot 500)'),
    dict(x=3400.0, y=1050.0, top=500.0, bed=446.0, cover=True, note='conduit inside the cell plinth (Z 300-499)'),
    dict(x=3600.0, y=1050.0, top=500.0, bed=442.0, cover=True, note='spout in the east face of the inner range'),
    # --- the fall into the outer court, then the long bearing to the gate's south shoulder
    dict(x=3660.0, y=1050.0, top=300.0, note='falls 145 cm to the outer court floor'),
    dict(x=4400.0, y=1040.0, top=300.0, note='outer court'),
    dict(x=5600.0, y=800.0, top=300.0, note='bearing north-east toward the gate'),
    dict(x=6600.0, y=430.0, top=300.0, note='bearing'),
    dict(x=7200.0, y=180.0, top=300.0, note='onto the gate axis, on its right (south) side'),
    # --- 47:2, "trickling from the right shoulder" of the outer east gate
    dict(x=7300.0, y=180.0, top=300.0, note='into the outer east gate vestibule, right shoulder'),
    dict(x=7800.0, y=180.0, top=300.0, note='under the outer east threshold (47:2)'),
    dict(x=8100.0, y=180.0, top=300.0, note='THE MEASURING DATUM: the outer face of the threshold'),
    dict(x=8600.0, y=180.0, top=300.0, note='across the access landing'),
    dict(x=9200.0, y=180.0, top=0.0, note='down the outer stair, onto the mount apron'),
]

# The south-gate branch, built only when group 'southgate' is requested: the book's
# reading (p. 340), in which the water leaves by the inner court's SOUTH gate. It is
# taken off the running line just west of the altar ramp and carried south.
SOUTHGATE_ROUTE = [
    dict(x=-430.0, y=1050.0, top=625.0, note='branch taken from the running line'),
    dict(x=-300.0, y=1500.0, top=625.0, note='bearing south'),
    dict(x=-200.0, y=2100.0, top=625.0, note='crossing the Ezras Kohanim'),
    dict(x=-150.0, y=2500.0, top=625.0, note='at the inner south threshold'),
    dict(x=-150.0, y=2800.0, top=625.0, bed=590.0, cover=True, note='under the inner south threshold (Shaar HaMayim)'),
    dict(x=-150.0, y=3700.0, top=425.0, note='down the inner south stair into the outer court'),
    dict(x=-150.0, y=6000.0, top=425.0, note='outer court, south'),
    dict(x=-150.0, y=7800.0, top=425.0, note='at the outer south threshold'),
    dict(x=-150.0, y=8100.0, top=425.0, note='out of the outer south gate'),
]


def stage_distance_amot(index):
    return STAGE_SPACING_AMOT * index


def _monotone_tangents(values, spacing):
    """Fritsch-Carlson monotone cubic Hermite tangents; the same construction as
    MikdashWater::MonotoneTangents, so the geometry and the runtime agree exactly."""
    n = len(values)
    secants = [(values[i + 1] - values[i]) / spacing for i in range(n - 1)]
    tangents = [0.0] * n
    tangents[0] = secants[0]
    tangents[-1] = secants[-1]
    for i in range(1, n - 1):
        tangents[i] = 0.5 * (secants[i - 1] + secants[i])
    for i in range(n - 1):
        if abs(secants[i]) < 1e-15:
            tangents[i] = 0.0
            tangents[i + 1] = 0.0
            continue
        a = tangents[i] / secants[i]
        b = tangents[i + 1] / secants[i]
        norm = math.sqrt(a * a + b * b)
        if norm > 3.0:
            scale = 3.0 / norm
            tangents[i] = scale * a * secants[i]
            tangents[i + 1] = scale * b * secants[i]
    return tangents


def _monotone_sample(values, tangents, spacing, x):
    n = len(values)
    span = spacing * (n - 1)
    if x <= 0.0:
        return values[0]
    if x >= span:
        return values[-1]
    index = min(int(x / spacing), n - 2)
    t = (x - spacing * index) / spacing
    t2, t3 = t * t, t * t * t
    return ((2 * t3 - 3 * t2 + 1) * values[index]
            + (t3 - 2 * t2 + t) * spacing * tangents[index]
            + (-2 * t3 + 3 * t2) * values[index + 1]
            + (t3 - t2) * spacing * tangents[index + 1])


class StreamProfile(object):
    """Depth and top width against distance east of the measuring datum, in amot."""

    def __init__(self, amah_cm=AMAH):
        self.amah = amah_cm
        self.depths = list(STAGE_DEPTH_CM)
        self.widths = [w * amah_cm for w in STAGE_TOP_WIDTH_AMOT]
        self.depth_tangents = _monotone_tangents(self.depths, STAGE_SPACING_AMOT)
        self.width_tangents = _monotone_tangents(self.widths, STAGE_SPACING_AMOT)

    def depth(self, amot):
        return _monotone_sample(self.depths, self.depth_tangents, STAGE_SPACING_AMOT, amot)

    def width(self, amot):
        return _monotone_sample(self.widths, self.width_tangents, STAGE_SPACING_AMOT, amot)

    def span_amot(self):
        return STAGE_SPACING_AMOT * (len(self.depths) - 1)


# In the courts the stream is still the trickle of 47:2: it has not been measured yet, so
# the text gives it no depth. The court runnel is sized to carry it and to read as a cut
# channel in the paving, both AUTHORED.
COURT_TOP_WIDTH_CM = 1.0 * AMAH
COURT_WATER_DEPTH_CM = 9.0


# =====================================================================================
# 3. Geometry primitives (all closed, outward-wound; same contract as create_keilim_ti_v1)
# =====================================================================================
def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def volume(v, f):
    total = 0.0
    for a, b, c in f:
        p, q, r = v[a], v[b], v[c]
        n = cross([q[i] - p[i] for i in range(3)], [r[i] - p[i] for i in range(3)])
        total += sum(p[i] * n[i] for i in range(3))
    return total / 6.0


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


def box(center, size):
    hx, hy, hz = [s / 2.0 for s in size]
    cx, cy, cz = center
    v = [(cx + sx * hx, cy + sy * hy, cz + sz * hz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    f = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5),
         (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6),
         (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return orient(v, f)


def box_min_max(lo, hi):
    return box([(lo[i] + hi[i]) / 2.0 for i in range(3)], [hi[i] - lo[i] for i in range(3)])


def sweep(path, sections):
    """Sweep a CLOSED cross-section along a path.

    path      [(x, y, z), ...]   the bed centreline; z is the bed level
    sections  [[(offset, dz), ...], ...]  one closed polygon per path point, all the same
              length. offset is measured along the horizontal normal of the path, dz up
              from the bed. Winding of the section is anticlockwise in (offset, dz).

    Returns a closed solid: a tube of quads with a fan cap at each end. The normal at a
    joint is the average of the two adjacent segment normals, so a bend does not pinch.
    """
    n = len(path)
    m = len(sections[0])
    assert n >= 2 and m >= 3
    assert all(len(s) == m for s in sections)

    normals = []
    for i in range(n):
        acc = [0.0, 0.0]
        for j in (i - 1, i):
            if 0 <= j < n - 1:
                dx = path[j + 1][0] - path[j][0]
                dy = path[j + 1][1] - path[j][1]
                length = math.hypot(dx, dy)
                if length > 1e-9:
                    acc[0] += -dy / length
                    acc[1] += dx / length
        length = math.hypot(acc[0], acc[1])
        assert length > 1e-6, 'degenerate path direction at point %d' % i
        normals.append((acc[0] / length, acc[1] / length))

    verts = []
    for i, (px, py, pz) in enumerate(path):
        nx, ny = normals[i]
        for offset, dz in sections[i]:
            verts.append((px + nx * offset, py + ny * offset, pz + dz))
    faces = []
    for s in range(n - 1):
        a0, b0 = s * m, (s + 1) * m
        for i in range(m):
            j = (i + 1) % m
            faces += [(a0 + i, a0 + j, b0 + j), (a0 + i, b0 + j, b0 + i)]
    last = (n - 1) * m
    for i in range(1, m - 1):
        faces += [(0, i + 1, i), (last, last + i, last + i + 1)]
    return orient(verts, faces)


def trough_section(top_width, depth, kerb=KERB_ABOVE_WATER_CM, thickness=BANK_THICKNESS_CM,
                   bed_thickness=BED_THICKNESS_CM, side_slope=BANK_SIDE_SLOPE):
    """The closed U-profile of the channel masonry, in (offset, dz) from the bed centre.

    The bank faces lean out at side_slope so that the free surface is exactly top_width
    across at the design depth; the kerb stands `kerb` proud of that surface."""
    half_top = top_width / 2.0
    lip = depth + kerb
    half_bed = max(1.0, half_top - side_slope * depth)
    outer = half_top + thickness
    return [(-outer, -bed_thickness), (outer, -bed_thickness), (outer, lip), (half_top + side_slope * kerb, lip),
            (half_bed, 0.0), (-half_bed, 0.0), (-(half_top + side_slope * kerb), lip), (-outer, lip)]


def cover_section(top_width, depth, thickness=BANK_THICKNESS_CM, slab=26.0):
    """The same trough closed over with a slab: the reaches that run beneath a structure."""
    half_top = top_width / 2.0
    outer = half_top + thickness
    return [(-outer, -BED_THICKNESS_CM), (outer, -BED_THICKNESS_CM), (outer, depth + slab),
            (-outer, depth + slab)]


WATER_MIN_THICKNESS_CM = 0.4


def water_section(top_width, depth, side_slope=BANK_SIDE_SLOPE, min_thickness=WATER_MIN_THICKNESS_CM):
    """The wetted cross-section itself: what the water material is drawn on.

    A closed ribbon whose TOP face is the free surface. It is kept at least
    min_thickness thick, which matters at exactly one place and matters absolutely
    there: at Stage::Trickle the design depth is TrickleDepthCm = 0.6 cm, which used to
    equal the fixed 0.6 cm underside, collapsing all four section points onto one plane.
    The sweep then emitted zero-area side quads and write_obj rejected the part as a
    degenerate triangle. The prophet's mefakim IS a film of water; the geometry just has
    to be a solid, so the underside is dropped instead of the surface being raised."""
    top = max(depth, min_thickness)
    bottom = max(0.0, min(0.6, top - min_thickness))
    half_top = top_width / 2.0
    half_bed = max(1.0, half_top - side_slope * top)
    return [(-half_bed, bottom), (half_bed, bottom), (half_top, top), (-half_top, top)]


# =====================================================================================
# 4. Building the court reach
# =====================================================================================
def resample(route, step_cm):
    """Densify a route to at most step_cm between points, interpolating every field."""
    out = []
    for i in range(len(route) - 1):
        a, b = route[i], route[i + 1]
        span = math.hypot(b['x'] - a['x'], b['y'] - a['y'])
        pieces = max(1, int(math.ceil(span / step_cm)))
        for k in range(pieces):
            t = k / float(pieces)
            row = dict(a)
            row['x'] = a['x'] + (b['x'] - a['x']) * t
            row['y'] = a['y'] + (b['y'] - a['y']) * t
            row['top'] = a['top'] + (b['top'] - a['top']) * t
            if 'bed' in a and 'bed' in b:
                row['bed'] = a['bed'] + (b['bed'] - a['bed']) * t
            elif 'bed' in a and t > 0:
                row.pop('bed', None)
            row['cover'] = bool(a.get('cover'))
            out.append(row)
    last = dict(route[-1])
    last['cover'] = bool(route[-1].get('cover'))
    out.append(last)
    return out


def court_path(route, step_cm=90.0):
    """Bed centreline, plus the per-point section width/depth and cover flag."""
    dense = resample(route, step_cm)
    points, covered = [], []
    for row in dense:
        bed = row['bed'] if 'bed' in row else row['top'] - COURT_SINK_CM
        points.append((row['x'], row['y'], bed))
        covered.append(bool(row.get('cover')))
    return points, covered, dense


def split_runs(flags):
    """[(start, end, flag), ...] over consecutive equal flags, sharing the joint index."""
    runs, start = [], 0
    for i in range(1, len(flags)):
        if flags[i] != flags[start]:
            runs.append((start, i, flags[start]))
            start = i
    runs.append((start, len(flags) - 1, flags[start]))
    return [(a, b, f) for a, b, f in runs if b > a]


def build_court_channel(route, name_prefix, step_cm=90.0):
    """The masonry of the court reach: open trough where it is open, covered conduit
    where it runs beneath a structure. Returns [(part_name, (verts, faces)), ...]."""
    points, covered, dense = court_path(route, step_cm)
    parts = []
    open_index = conduit_index = 0
    for a, b, is_cover in split_runs(covered):
        sub = points[a:b + 1]
        if is_cover:
            sections = [cover_section(COURT_TOP_WIDTH_CM, COURT_WATER_DEPTH_CM) for _ in sub]
            conduit_index += 1
            parts.append(('%s_Conduit_%02d' % (name_prefix, conduit_index), sweep(sub, sections)))
        else:
            sections = [trough_section(COURT_TOP_WIDTH_CM, COURT_WATER_DEPTH_CM) for _ in sub]
            open_index += 1
            parts.append(('%s_Trough_%02d' % (name_prefix, open_index), sweep(sub, sections)))
    return parts, points, covered, dense


def build_court_water(route, step_cm=90.0):
    """The free surface of the court reach, as one thin closed ribbon per open run."""
    points, covered, _ = court_path(route, step_cm)
    parts = []
    index = 0
    for a, b, is_cover in split_runs(covered):
        if is_cover:
            continue                       # a covered conduit shows no surface
        sub = points[a:b + 1]
        sections = [water_section(COURT_TOP_WIDTH_CM, COURT_WATER_DEPTH_CM) for _ in sub]
        index += 1
        parts.append(('SM_MikdashWaterV1_CourtWater_%02d' % index, sweep(sub, sections)))
    return parts


# =====================================================================================
# 5. Building the four measured stages
# =====================================================================================
def far_field_path(profile, step_amot=50.0):
    """The channel east of the mount, from the measuring datum to the fourth thousand.

    The bed descends at FAR_FIELD_GRADE from the mount apron. The apron itself is at
    Z 0 at X 9200 (the foot of the outer east stair, from the architecture manifest);
    the first 22 amot between the datum and the apron are part of the court reach."""
    rows = []
    amot = 0.0
    while amot <= profile.span_amot() + 1e-6:
        x = MEASURE_DATUM_X + amot * AMAH
        ground = 0.0 if x <= 9200.0 else -(x - 9200.0) * FAR_FIELD_GRADE
        depth = profile.depth(amot)
        width = profile.width(amot)
        rows.append(dict(amot=amot, x=x, y=180.0, ground=ground,
                         bed=ground - depth - 20.0, depth=depth, width=width))
        amot += step_amot
    return rows


def build_stage_channel(rows, segment_amot=500.0):
    """The far-field channel, cut into segments so a segment that meets terrain trouble
    can be dropped without losing the rest. Bed, banks and the widening are continuous
    across a segment joint because the joint point is shared."""
    parts, waters, markers = [], [], []
    per = max(2, int(round(segment_amot / (rows[1]['amot'] - rows[0]['amot']))))
    index = 0
    for start in range(0, len(rows) - 1, per):
        end = min(start + per, len(rows) - 1)
        sub = rows[start:end + 1]
        if len(sub) < 2:
            continue
        path = [(r['x'], r['y'], r['bed']) for r in sub]
        sections = [trough_section(r['width'], r['depth'], kerb=14.0,
                                   thickness=max(30.0, r['width'] * 0.06),
                                   bed_thickness=20.0) for r in sub]
        index += 1
        parts.append(('SM_MikdashWaterV1_StageChannel_%02d' % index, sweep(path, sections)))
        waters.append(('SM_MikdashWaterV1_StageWater_%02d' % index,
                       sweep(path, [water_section(r['width'], r['depth']) for r in sub])))
    # The four measuring marks: a kerb stone set flush in the south bank, and a slender
    # gauge post standing in the water to the measured depth. Deliberately small.
    for stage in range(1, 5):
        amot = stage_distance_amot(stage)
        row = min(rows, key=lambda r: abs(r['amot'] - amot))
        depth = STAGE_DEPTH_CM[stage]
        half = row['width'] / 2.0
        stone_y = row['y'] + half + max(30.0, row['width'] * 0.06) * 0.5
        stone = box([row['x'], stone_y, row['ground'] + TEFACH * 0.5],
                    [AMAH, AMAH, 2.0 * TEFACH])
        post = box([row['x'], row['y'] + half * 0.5, row['bed'] + 20.0 + depth * 0.5],
                   [6.0, 6.0, depth])
        markers.append(('SM_MikdashWaterV1_StageMark_%d' % stage, stone))
        markers.append(('SM_MikdashWaterV1_StageGauge_%d' % stage, post))
    return parts, waters, markers


# =====================================================================================
# 6. The mikvaot
# =====================================================================================
# Forty se'ah is three cubic amot (Eruvin 4b), so the requirement in centimetres depends
# only on the amah: 331,776 cm3 at R' A. C. Naeh's 48 cm, 573,309 cm3 at the Chazon Ish's
# 57.6 cm, 375,000 cm3 at this project's 50 cm modelling amah. Every pool below clears the
# STRINGENT figure by a wide margin, and the arithmetic is in the manifest.

FORTY_SEAH_CM3 = {
    "R' A. C. Naeh (amah 48 cm)": 3.0 * 48.0 ** 3,
    'Chazon Ish (amah 57.6 cm)': 3.0 * 57.6 ** 3,
    'project modelling amah (50 cm)': 3.0 * 50.0 ** 3,
}

MIKVEH_INNER_LENGTH = 200.0     # AUTHORED: long enough to lie down in
MIKVEH_INNER_WIDTH = 100.0      # AUTHORED
MIKVEH_WATER_DEPTH = 100.0      # AUTHORED
MIKVEH_STEP_COUNT = 4
MIKVEH_STEP_RISE = MIKVEH_WATER_DEPTH / MIKVEH_STEP_COUNT
MIKVEH_STEP_GOING = 25.0
MIKVEH_WALL = 30.0
MIKVEH_FLOOR = 25.0

MIKVAOT = [
    dict(key='KohanimDaily', label='mikveh for the kohanim, daily before service',
         centre=(-4000.0, -4400.0), rim_z=425.0, screen=False,
         source=("Tamid 1:2; Rambam Biat HaMikdash 5:4 (no kohen enters the Azarah for service, "
                 "even when pure, until he immerses). Book p. 325 places it beside Beis HaMoked "
                 "in the north lower chambers, second floor, marked * for study only."),
         departure=('The book\'s north LOWER CHAMBERS are not built in this map (they are gap 6 of '
                    'the research review). Placed instead in the built north priestly chamber block '
                    '(Yechezkel 42), ground storey, so it is reachable on foot.')),
    dict(key='KohenGadolYear', label="mikveh for the Kohen Gadol, year-round (outside the holy area)",
         centre=(-3000.0, -4400.0), rim_z=425.0, screen=False,
         source=('Book p. 326: its place is in the chol, in the lower chambers, separate from the '
                 'other kohanim and next to their beis tevilah, second floor. Marked *.'),
         departure='Same block substitution as the daily mikveh; kept adjacent to it, as the book has it.'),
    dict(key='KohenGadolYomKippur', label="mikveh for the Kohen Gadol on Yom Kippur (in the kodesh)",
         centre=(-1350.0, 2150.0), rim_z=625.0, screen=True,
         source=('Middos 5:3 (on the roof of Beis HaParvah); Yoma 19a and Rambam Beis HaBechirah 5:17 '
                 'place the chamber in the SOUTH -- the sources differ. Yoma 30a: five immersions and '
                 'ten sanctifications, all in the kodesh above Beis HaParvah save the first. Book p. 326 '
                 'puts it in the western of the six southern halls of the inner court, third floor. Marked *.'),
         departure=('The six southern halls are not built in this map. Placed on the inner court floor on '
                    'the SOUTH side, beside the built Song chamber, which keeps the book\'s side and its '
                    '"in the kodesh" requirement but not its storey.')),
    dict(key='Metzoraim', label="mikveh in the chamber of the metzora'im",
         centre=(-7000.0, -4400.0), rim_z=425.0, screen=False,
         source=('Middos 2:5 and Tiferes Yisroel there (the metzora immerses in this chamber before '
                 'inserting his thumbs on the eighth day). Book p. 333: outer court, north lower '
                 'chambers, western side, first floor, near the entrance to the Ezras Yisroel. Marked *.'),
         departure='Placed in the westernmost room of the built north priestly block; the outer-court lower chambers are not built.'),
]


def mikveh_water_volume_cm3():
    """Water actually held: the basin box less the solid of the descending stair."""
    basin = MIKVEH_INNER_LENGTH * MIKVEH_INNER_WIDTH * MIKVEH_WATER_DEPTH
    stair = 0.0
    for i in range(MIKVEH_STEP_COUNT):
        # step i counted from the rim: its tread top stands (MIKVEH_STEP_COUNT-1-i) rises
        # above the floor, and the masonry below it is solid.
        stair += MIKVEH_STEP_GOING * MIKVEH_INNER_WIDTH * (MIKVEH_STEP_RISE * (MIKVEH_STEP_COUNT - 1 - i))
    return basin - stair


def build_mikveh(spec):
    """Basin walls, floor, the descending steps, and (where called for) the screen.

    Parts are separate closed solids, which is how create_keilim_ti_v1 builds a hollow
    vessel: a single manifold with an interior void is not needed, and per-part signed
    volumes are individually checkable."""
    cx, cy = spec['centre']
    rim = spec['rim_z']
    floor_top = rim - MIKVEH_WATER_DEPTH
    hl, hw = MIKVEH_INNER_LENGTH / 2.0, MIKVEH_INNER_WIDTH / 2.0
    key = spec['key']
    parts = []

    parts.append(('SM_MikdashWaterV1_Mikveh_%s_Floor' % key,
                  box_min_max([cx - hl - MIKVEH_WALL, cy - hw - MIKVEH_WALL, floor_top - MIKVEH_FLOOR],
                              [cx + hl + MIKVEH_WALL, cy + hw + MIKVEH_WALL, floor_top])))
    walls = [
        ('WallW', [cx - hl - MIKVEH_WALL, cy - hw - MIKVEH_WALL, floor_top], [cx - hl, cy + hw + MIKVEH_WALL, rim]),
        ('WallE', [cx + hl, cy - hw - MIKVEH_WALL, floor_top], [cx + hl + MIKVEH_WALL, cy + hw + MIKVEH_WALL, rim]),
        ('WallN', [cx - hl, cy - hw - MIKVEH_WALL, floor_top], [cx + hl, cy - hw, rim]),
        ('WallS', [cx - hl, cy + hw, floor_top], [cx + hl, cy + hw + MIKVEH_WALL, rim]),
    ]
    for name, lo, hi in walls:
        parts.append(('SM_MikdashWaterV1_Mikveh_%s_%s' % (key, name), box_min_max(lo, hi)))

    # The stair descends from the rim at the east end, four steps, each a solid block
    # standing on the floor so the water can be seen to shallow toward it.
    # MIKVEH_STEP_COUNT counts RISERS from the rim to the floor, so there is one fewer
    # block than risers: the lowest tread a person stands on is the basin floor itself.
    # Emitting a block for it produced a zero-height solid whose signed volume is 0, and
    # write_obj's winding check rejects that (it cannot tell a flat box from an inverted
    # one). mikveh_water_volume_cm3() already accounts for the last step as zero solid,
    # so the water figure is unchanged by this.
    for i in range(MIKVEH_STEP_COUNT):
        x0 = cx + hl - MIKVEH_STEP_GOING * (i + 1)
        top = rim - MIKVEH_STEP_RISE * (i + 1)
        if top - floor_top <= 1e-6:
            continue
        parts.append(('SM_MikdashWaterV1_Mikveh_%s_Step%d' % (key, i + 1),
                      box_min_max([x0, cy - hw, floor_top], [x0 + MIKVEH_STEP_GOING, cy + hw, top])))

    if spec['screen']:
        # Yoma 3:4: a sheet of fine linen was spread between the Kohen Gadol and the
        # people at his immersion. Modelled as a standing screen on the north side --
        # the side a spectator in the court would be on -- not as a masonry wall.
        parts.append(('SM_MikdashWaterV1_Mikveh_%s_Screen' % key,
                      box_min_max([cx - hl - MIKVEH_WALL, cy - hw - MIKVEH_WALL - 12.0, rim],
                                  [cx + hl + MIKVEH_WALL, cy - hw - MIKVEH_WALL, rim + 250.0])))

    water = [('SM_MikdashWaterV1_MikvehWater_%s' % key,
              box_min_max([cx - hl, cy - hw, floor_top + 0.5], [cx + hl - MIKVEH_STEP_GOING, cy + hw, rim - 4.0]))]
    return parts, water


# =====================================================================================
# 7. Clearance against the architecture manifest
# =====================================================================================
def part_bounds(part):
    verts = part[0]
    return dict(min=[min(v[i] for v in verts) for i in range(3)],
                max=[max(v[i] for v in verts) for i in range(3)])


SUBBOX_MAX_EXTENT_CM = 250.0


def part_subboxes(part, max_extent_cm=SUBBOX_MAX_EXTENT_CM):
    """Decompose one generated solid into tight sub-boxes, for clearance testing.

    THE TRAP THIS EXISTS FOR. A single AABB around a swept, curving channel is a lie: the
    court reach leaves the House at Y 400 and runs east at Y 1050, so its whole-part box
    spans Y 400..1050 across every X it visits, including the X band of the altar -- which
    the water never comes within 250 cm of. Tested that way the altar, its ramp, the chut
    hasikra and half the east gate all read as intersections. Every one of them is false.
    This is the same failure release_place_assets.py records for the FutureMountV1 terrain
    tiles, whose 400-800 m AABBs enclose the entire Temple, and for the hollow derived
    unions; the fix is the same in all three cases -- never test a raw bound, test the
    parts it is made of.

    sweep() emits triangles ring by ring along the path, so consecutive triangles are
    spatially adjacent. Greedily merging them while the running box stays under
    max_extent_cm therefore yields boxes that follow the channel instead of boxing it.
    A plain box merges back into exactly itself; a straight prism longer than the cap is
    split into collinear boxes, which costs nothing and loses no tightness.
    """
    verts, faces = part
    boxes, cur = [], None
    for face in faces:
        pts = [verts[i] for i in face]
        lo = [min(q[i] for q in pts) for i in range(3)]
        hi = [max(q[i] for q in pts) for i in range(3)]
        if cur is None:
            cur = [lo, hi]
            continue
        m = [min(cur[0][i], lo[i]) for i in range(3)]
        x = [max(cur[1][i], hi[i]) for i in range(3)]
        if max(x[i] - m[i] for i in range(3)) <= max_extent_cm:
            cur = [m, x]
        else:
            boxes.append(cur)
            cur = [lo, hi]
    if cur is not None:
        boxes.append(cur)
    return [dict(min=b[0], max=b[1]) for b in boxes]


def boxes_overlap(a, b, tolerance=1e-6):
    for i in range(3):
        if min(a['max'][i], b['max'][i]) - max(a['min'][i], b['min'][i]) <= tolerance:
            return False
    return True


def gap_between(a, b):
    """Smallest overlap on any axis. Positive means the boxes interpenetrate by that much
    on their tightest axis; negative means they are apart on at least one axis."""
    return min(min(a['max'][i], b['max'][i]) - max(a['min'][i], b['min'][i]) for i in range(3))


def separation_cm(a, b):
    """True Euclidean distance between two AABBs. Zero when they touch or interpenetrate.

    gap_between() alone is not a clearance: it is a per-axis quantity, and MINIMISING it
    over a set of pairs finds the FARTHEST pair, not the nearest. Reporting a clearance
    means minimising THIS."""
    d = [max(0.0, a['min'][i] - b['max'][i], b['min'][i] - a['max'][i]) for i in range(3)]
    return math.sqrt(sum(v * v for v in d))


def base_name(source_name):
    return ''.join(c for c in source_name if not c.isdigit()).strip().rstrip('-').strip()


def load_architecture():
    data = json.loads(ARCH_MANIFEST.read_text(encoding='utf-8'))
    rows = []
    for mesh in data['meshes']:
        rows.append(dict(name=base_name(mesh['sourceName']), asset=mesh['assetName'],
                         part=mesh.get('sourcePart'), bounds=mesh['expectedBoundsUnrealCm']))
    return rows, data


def verify_anchors(rows):
    """Fail loudly if the built Temple has moved under us. Every fixed point this script
    uses is re-derived from the manifest and compared with the ANCHORS block above."""
    checks, errors = [], []
    for label, expected in ANCHORS.items():
        key = label.lower()
        if key == 'kiyor basin':
            key = 'hollow basin with inner wall'
        if key == 'southern kevesh':
            key = 'kevesh'
        matched = [r for r in rows if key in r['name'].lower()]
        side = expected.get('side')
        if side == 'south':
            matched = [r for r in matched if r['bounds']['min'][1] >= 0.0]
        elif side == 'north':
            matched = [r for r in matched if r['bounds']['max'][1] <= 0.0]
        if not matched:
            errors.append('anchor mesh not found in the architecture manifest: ' + label)
            continue
        got = dict(min=[min(r['bounds']['min'][i] for r in matched) for i in range(3)],
                   max=[max(r['bounds']['max'][i] for r in matched) for i in range(3)])
        error = max(abs(got[k][i] - expected[k][i]) for k in ('min', 'max') for i in range(3))
        checks.append(dict(anchor=label, meshes=len(matched), maxErrorCm=round(error, 4),
                           bounds=got, matches=error <= 0.2))
        if error > 0.2:
            errors.append('anchor %s moved by %.3f cm' % (label, error))
    return checks, errors


def clearance_report(rows, groups):
    """Classify every architecture mesh the generated geometry meets.

    HOST     paving, platforms, stairs and thresholds a courtyard conduit is necessarily
             cut into or laid on. Expected; reported with the depth of engagement.
    BLOCKER  anything else. The altar, its ramp, the kiyor, gate jambs, chambers and
             vessels are all in this class, and any hit fails the export.
    IGNORED  the hollow derived-union envelopes, whose AABB encloses the whole site.
    """
    hosts, blockers, ignored = {}, [], set()
    naive_hits = 0                     # what a raw whole-part AABB test would have claimed
    tracked = []
    for part_name, part in groups:
        tracked.append((part_name, part_bounds(part), part_subboxes(part)))
    for row in rows:
        if row['name'] in HOLLOW_UNION_NAMES:
            ignored.add(row['name'])
            continue
        for part_name, pb, subs in tracked:
            # Broad phase on the whole part, then the narrow phase that decides. A hit on
            # the whole-part box alone is not a finding; see part_subboxes().
            if not boxes_overlap(pb, row['bounds']):
                continue
            naive_hits += 1
            hit = [b for b in subs if boxes_overlap(b, row['bounds'])]
            if not hit:
                continue
            pb = max(hit, key=lambda b: gap_between(b, row['bounds']))
            if row['name'] in HOST_MESH_NAMES:
                entry = hosts.setdefault(row['name'], dict(mesh=row['name'], parts=set(),
                                                           deepestEngagementCm=0.0, hits=0))
                entry['parts'].add(part_name)
                entry['hits'] += 1
                entry['deepestEngagementCm'] = max(entry['deepestEngagementCm'],
                                                   round(gap_between(pb, row['bounds']), 3))
            else:
                blockers.append(dict(part=part_name, mesh=row['name'], asset=row['asset'],
                                     overlapCm=round(gap_between(pb, row['bounds']), 3),
                                     meshBounds=row['bounds']))
    for entry in hosts.values():
        entry['parts'] = sorted(entry['parts'])
    real_hits = sum(e['hits'] for e in hosts.values()) + len(blockers)
    return dict(hosts=sorted(hosts.values(), key=lambda e: e['mesh']),
                blockers=blockers, hollowUnionsIgnored=sorted(ignored),
                subBoxMaxExtentCm=SUBBOX_MAX_EXTENT_CM,
                wholePartAabbHits=naive_hits, subBoxHits=real_hits,
                falsePositivesEliminated=naive_hits - real_hits,
                method=('Broad phase on the whole-part AABB, narrow phase on decomposed sub-boxes. '
                        'A whole-part test alone reported %d contacts, of which %d were false: the '
                        'AABB of a channel that leaves the House at Y 400 and runs east at Y 1050 '
                        'covers the altar, its ramp and the chut hasikra, none of which the water '
                        'comes near. Hollow derived-union envelopes are excluded by name for the '
                        'same reason.' % (naive_hits, naive_hits - real_hits)))


def named_clearances(rows, groups):
    """The distances a reviewer will ask for, measured rather than asserted.

    Measured sub-box to mesh-bound, and reported as the NEAREST approach over every
    (sub-box, mesh) pair. An earlier version minimised gap_between() over the same pairs,
    which silently reported the most DISTANT pair -- every feature came back "clear by
    99 metres, nearest part Court_Trough_03", which is nonsense for ten different
    features at once. If a clearance number here is ever identical across unrelated
    features, that is the bug returning.
    """
    tracked = [(n, b) for n, p in groups for b in part_subboxes(p)]
    wanted = {
        'altar (yesod, the widest course)': 'altar yesod',
        'altar ramp (kevesh)': 'kevesh',
        'kiyor basin': 'hollow basin with inner wall',
        'kiyor pedestal': 'turned pedestal',
        'inner eastern gate wall jamb': 'inner eastern gate wall jamb',
        'inner E cell connecting doorway': 'inner e connecting doorway',
        'outer east gate vestibule wall': 'outer e vestibule wall',
        'Ulam entrance pillar': 'ulam entrance pillar',
        'duchan rise': 'duchan rise',
        'stone slaughter tables': 'stone slaughter table',
        'Song chamber': 'song chamber',
    }
    out = []
    for label, key in sorted(wanted.items()):
        matched = [r for r in rows if key in r['name'].lower()]
        if not matched:
            out.append(dict(feature=label, found=False))
            continue
        nearest = min((separation_cm(pb, r['bounds']), part_name, r['asset'])
                      for r in matched for part_name, pb in tracked)
        touching = [(gap_between(pb, r['bounds']), part_name, r['asset'])
                    for r in matched for part_name, pb in tracked
                    if boxes_overlap(pb, r['bounds'])]
        deepest = max(touching)[0] if touching else 0.0
        # A HOST feature (paving, a stair, a platform) is one the conduit is by nature cut
        # into; intersects=True there is the intended reading, not a finding. Everything
        # else must show intersects=False, and export() fails if it does not.
        is_host = any(r['name'] in HOST_MESH_NAMES for r in matched)
        out.append(dict(feature=label, found=True, meshCount=len(matched),
                        isHost=is_host,
                        clearanceCm=round(nearest[0], 3),
                        nearestGeneratedPart=nearest[1], nearestArchitectureAsset=nearest[2],
                        intersects=bool(touching),
                        deepestInterpenetrationCm=round(deepest, 3) if touching else 0.0))
    return out


# =====================================================================================
# 8. Cross-check against the runtime header
# =====================================================================================
def verify_against_header():
    """The depths, widths and stage spacing here must equal WaterFlowMath.h's, or the
    generated channel and the actor driving it would describe different rivers."""
    header = (ROOT / 'Plugins/MikdashRuntime/Source/MikdashRuntime/Public/WaterFlowMath.h').read_text(encoding='utf-8')
    wanted = [('StatureCm = %.1f;' % STATURE_CM, 'stature'),
              ('AnkleFraction = 0.07;', 'ankle fraction'),
              ('KneeFraction = 0.285;', 'knee fraction'),
              ('LoinFraction = 0.53;', 'loin fraction'),
              ('SwimFraction = 1.05;', 'swim fraction'),
              ('TrickleDepthCm = 0.6;', 'trickle depth'),
              ('ProjectAmahCm = 50.0;', 'project amah')]
    missing = [label for token, label in wanted if token not in header]
    widths = {1: '4.0', 2: '10.0', 3: '20.0', 4: '50.0'}
    for stage, value in widths.items():
        if 'return %s;' % value not in header:
            missing.append('stage %d top width %s amot' % (stage, value))
    return dict(header='Plugins/MikdashRuntime/Source/MikdashRuntime/Public/WaterFlowMath.h',
                sha256=hashlib.sha256(header.encode('utf-8')).hexdigest(),
                constantsMatched=not missing, missing=missing)


# =====================================================================================
# 9. OBJ export and readback
# =====================================================================================
OBJ_NOTE = ('Unreal legacy OBJ adapter: canonical vertices are UE cm (X east, +Y south, Z up); '
            'this file is written with Y REFLECTED and triangle winding REVERSED. The importer '
            'reflects Y back, so imported bounds must equal canonicalBoundsCm and UE signed '
            'volumes must be positive. Same adapter as create_keilim_ti_v1.py.')


def write_obj(name, parts, path, provenance):
    lines = ['# MikdashWaterV1 %s' % name, '# ' + OBJ_NOTE]
    lines += ['# ' + line for line in provenance]
    lines.append('o ' + name)
    index = 1
    allv = []
    checks = []
    for part, (vertices, faces) in parts:
        vol = volume(vertices, faces)
        assert vol > 0, 'inverted part ' + part
        assert closed(vertices, faces), 'open part ' + part
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
                lines.append('v %.4f %.4f %.4f' % vv)
            # UVs in metres along and across the triangle: the water material scrolls in
            # U, so U must run ALONG the flow. The sweep emits sections in path order, so
            # the triangle's first edge is along the channel for every side quad.
            for uv in ((0.0, 0.0), (length / 100.0, 0.0),
                       (sum(ac[i] * ab[i] / length for i in range(3)) / 100.0, nl / length / 100.0)):
                lines.append('vt %.5f %.5f' % uv)
            for _ in range(3):
                lines.append('vn %.5f %.5f %.5f' % tuple(x / nl for x in n))
            lines.append('f ' + ' '.join('%d/%d/%d' % (k, k, k) for k in range(index, index + 3)))
            index += 3
        checks.append(dict(name=part, triangles=len(faces), closed=True, volumeCm3=round(vol, 3)))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    bounds = {k: [fn(p[i] for p in allv) for i in range(3)] for k, fn in (('min', min), ('max', max))}
    return dict(name=name, file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                bytes=path.stat().st_size, triangles=(index - 1) // 3, parts=len(parts),
                canonicalBoundsCm=bounds,
                minimumPartSignedVolumeCm3=min(c['volumeCm3'] for c in checks),
                totalSignedVolumeCm3=round(sum(c['volumeCm3'] for c in checks), 3),
                partChecks=checks)


def readback(path, record):
    """Re-read the written file and prove the adapter round-trips: normals agree with the
    face winding, the reflected bounds come back to the canonical ones, and the signed
    volume in FILE space is positive (which is what the importer will see)."""
    verts, normals, faces = [], [], []
    for line in path.read_text().splitlines():
        c = line.split()
        if not c or c[0].startswith('#'):
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
        dot = sum(cr[i] * normals[face[0][2]][i] for i in range(3)) / area
        worst = max(worst, abs(1.0 - dot))
    assert worst < 1e-3, worst
    canonical = [(x, -y, z) for x, y, z in verts]
    bounds = {k: [fn(v[i] for v in canonical) for i in range(3)] for k, fn in (('min', min), ('max', max))}
    err = max(abs(bounds[k][i] - record['canonicalBoundsCm'][k][i]) for k in bounds for i in range(3))
    assert err < 1e-3, err
    fv = volume(verts, [tuple(t[0] for t in face) for face in faces])
    assert fv > 0, 'adapter sign unexpected for ' + path.name
    return dict(mesh=record['name'], triangles=len(faces), boundsErrorCm=round(err, 6),
                worstNormalError=round(worst, 9), fileSpaceSignedVolumeCm3=round(fv, 3),
                normalsAndUvs='PASS')


# =====================================================================================
# 10. Plan preview (a small PNG; no library)
# =====================================================================================
def _png(path, rgb, width, height):
    def chunk(kind, data):
        return (struct.pack('>I', len(data)) + kind + data
                + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF))
    raw = b''.join(b'\x00' + bytes(rgb[y * width * 3:(y + 1) * width * 3]) for y in range(height))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'
                     + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def write_plan(path, arch_rows, generated, size=(1500, 760)):
    """Plan of the courts with the generated channel over it: a reviewer's sanity check,
    not a rendering. Architecture in grey, hosts in slate, the channel in blue, the
    mikvaot in teal, the altar and kiyor called out in ochre."""
    width, height = size
    rgb = bytearray([20, 22, 26] * (width * height))
    lo_x, hi_x = -8400.0, 9800.0
    lo_y, hi_y = -8400.0, 8400.0
    sx = (width - 20) / (hi_x - lo_x)
    sy = (height - 20) / (hi_y - lo_y)
    scale = min(sx, sy)
    ox = 10 + (width - 20 - (hi_x - lo_x) * scale) / 2.0
    oy = 10 + (height - 20 - (hi_y - lo_y) * scale) / 2.0

    def put(px, py, colour):
        if 0 <= px < width and 0 <= py < height:
            i = (py * width + px) * 3
            rgb[i:i + 3] = bytes(colour)

    def fill(bounds, colour):
        x0 = int(ox + (bounds['min'][0] - lo_x) * scale)
        x1 = int(ox + (bounds['max'][0] - lo_x) * scale)
        y0 = int(oy + (bounds['min'][1] - lo_y) * scale)
        y1 = int(oy + (bounds['max'][1] - lo_y) * scale)
        for py in range(min(y0, y1), max(y0, y1) + 1):
            for px in range(min(x0, x1), max(x0, x1) + 1):
                put(px, py, colour)

    for row in arch_rows:
        if row['name'] in HOLLOW_UNION_NAMES:
            continue
        colour = (58, 62, 70)
        if row['name'] in HOST_MESH_NAMES:
            colour = (44, 50, 60)
        if 'altar' in row['name'].lower() or 'kevesh' in row['name'].lower() or 'keren' in row['name'].lower():
            colour = (150, 116, 54)
        if 'basin' in row['name'].lower() or 'turned pedestal' in row['name'].lower():
            colour = (168, 140, 70)
        fill(row['bounds'], colour)
    for name, part in generated:
        colour = (64, 148, 210)
        if 'Water' in name:
            colour = (110, 196, 240)
        if 'Mikveh' in name:
            colour = (70, 178, 160)
        if 'StageMark' in name or 'StageGauge' in name:
            colour = (232, 208, 120)
        fill(part_bounds(part), colour)
    _png(path, rgb, width, height)
    return dict(file=path.name, width=width, height=height,
                extentCm=dict(min=[lo_x, lo_y], max=[hi_x, hi_y]),
                legend={'grey': 'imported architecture', 'slate': 'host paving/platform meshes',
                        'ochre': 'altar, ramp and kiyor', 'blue': 'generated channel masonry',
                        'pale blue': 'generated water surfaces', 'teal': 'mikvaot',
                        'yellow': 'the four measuring marks'})


# =====================================================================================
# 11. Export
# =====================================================================================
GROUPS = ('court', 'stages', 'mikvaot', 'southgate')
DEFAULT_GROUPS = ('court', 'stages', 'mikvaot')

MATERIAL_ROLE = {}


def _role(name):
    if 'Water' in name:
        return 'water'
    if 'Screen' in name:
        return 'linen'
    if 'Gauge' in name:
        return 'bronze'
    return 'stone'


def build_all(groups):
    """Every generated part, grouped into the meshes that will be imported."""
    meshes = []          # (mesh_name, [(part_name, solid), ...], role, provenance)
    profile = StreamProfile()
    facts = dict(groups=list(groups))

    if 'court' in groups:
        parts, points, covered, dense = build_court_channel(COURT_ROUTE, 'Court')
        meshes.append(('SM_MikdashWaterV1_CourtChannel',
                       [('%s' % n, p) for n, p in parts], 'stone',
                       ['The channel of Yechezkel 47:1-2 through the courts: from under the threshold of',
                        'the House, down the right (south) side, SOUTH OF THE ALTAR, and out at the right',
                        'shoulder of the outer east gate. Route certain from the text; every centimetre of',
                        'width, depth and construction is AUTHORED.']))
        meshes.append(('SM_MikdashWaterV1_CourtWater', build_court_water(COURT_ROUTE), 'water',
                       ['The free surface of the court reach. Depth %.1f cm, top width %.1f cm: AUTHORED.'
                        % (COURT_WATER_DEPTH_CM, COURT_TOP_WIDTH_CM)]))
        length = sum(math.dist(points[i][:2], points[i + 1][:2]) for i in range(len(points) - 1))
        drop = points[0][2] - points[-1][2]
        facts['court'] = dict(
            routePoints=len(COURT_ROUTE), sampledPoints=len(points),
            plannedLengthCm=round(length, 1), plannedLengthAmot=round(length / AMAH, 1),
            sourceCm=list(points[0]), outletCm=list(points[-1]),
            totalFallCm=round(drop, 1), meanGrade=round(drop / length, 5),
            coveredReaches=sum(1 for a, b, f in split_runs(covered) if f),
            topWidthCm=COURT_TOP_WIDTH_CM, waterDepthCm=COURT_WATER_DEPTH_CM,
            waypoints=[dict(x=r['x'], y=r['y'], surfaceTopZ=r['top'], note=r['note']) for r in COURT_ROUTE])

    if 'stages' in groups:
        rows = far_field_path(profile)
        parts, waters, markers = build_stage_channel(rows)
        meshes.append(('SM_MikdashWaterV1_StageChannel', parts, 'stone',
                       ['The four thousands of Yechezkel 47:3-5, built as literal distances east of the',
                        'outer east gate at the project amah of 50 cm: 4000 amot = 2.000 km. The depths are',
                        'anthropometric fractions of a 170 cm stature (AUTHORED); the widths are AUTHORED',
                        'outright, no source giving any. Bed grade %.1f%%: AUTHORED.' % (FAR_FIELD_GRADE * 100)]))
        meshes.append(('SM_MikdashWaterV1_StageWater', waters, 'water',
                       ['The free surface through the four stages, widening and deepening monotonically',
                        'and passing exactly through each of the prophet\'s four measurements.']))
        meshes.append(('SM_MikdashWaterV1_StageMarks', markers, 'stone',
                       ['One flush kerb stone and one slender gauge post at each thousand-amah mark.']))
        facts['stages'] = dict(
            datumX=MEASURE_DATUM_X, datumNote='outer face of the outer east gate threshold (47:2-3)',
            spacingAmot=STAGE_SPACING_AMOT, spanAmot=profile.span_amot(),
            spanCm=profile.span_amot() * AMAH, gradePercent=FAR_FIELD_GRADE * 100,
            statureAssumedCm=STATURE_CM,
            marks=[dict(stage=i, label=STAGE_LABELS[i], distanceAmot=stage_distance_amot(i),
                        worldX=MEASURE_DATUM_X + stage_distance_amot(i) * AMAH,
                        depthCm=round(STAGE_DEPTH_CM[i], 3),
                        topWidthAmot=STAGE_TOP_WIDTH_AMOT[i],
                        topWidthCm=STAGE_TOP_WIDTH_AMOT[i] * AMAH) for i in range(5)],
            interpolation='Fritsch-Carlson monotone cubic Hermite; identical to MikdashWater::MonotoneSample',
            crossCheck=[dict(amot=a, depthCm=round(profile.depth(a), 4), topWidthCm=round(profile.width(a), 3))
                        for a in (0, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000)])

    if 'mikvaot' in groups:
        volume_cm3 = mikveh_water_volume_cm3()
        pools = []
        for spec in MIKVAOT:
            parts, water = build_mikveh(spec)
            meshes.append(('SM_MikdashWaterV1_Mikveh_%s' % spec['key'], parts, 'stone',
                           ['Mikveh: %s.' % spec['label'], 'Source: ' + spec['source'],
                            'Departure: ' + spec['departure'],
                            'Every dimension is AUTHORED; no source gives one.']))
            meshes.append(('SM_MikdashWaterV1_MikvehWater_%s' % spec['key'], water, 'water',
                           ['Water surface of ' + spec['label']]))
            pools.append(dict(key=spec['key'], label=spec['label'], centreCm=list(spec['centre']),
                              rimZ=spec['rim_z'], hasScreen=spec['screen'],
                              source=spec['source'], departure=spec['departure']))
        facts['mikvaot'] = dict(
            pools=pools,
            innerLengthCm=MIKVEH_INNER_LENGTH, innerWidthCm=MIKVEH_INNER_WIDTH,
            waterDepthCm=MIKVEH_WATER_DEPTH, steps=MIKVEH_STEP_COUNT,
            stepRiseCm=MIKVEH_STEP_RISE, stepGoingCm=MIKVEH_STEP_GOING,
            waterVolumeCm3=round(volume_cm3, 1), waterVolumeLitres=round(volume_cm3 / 1000.0, 2),
            fortySeahRule='forty se\'ah = three cubic amot (Eruvin 4b); the amah is the only free variable',
            fortySeah=[dict(opinion=k, requiredCm3=round(v, 1), requiredLitres=round(v / 1000.0, 3),
                            multipleHeld=round(volume_cm3 / v, 3), sufficient=volume_cm3 >= v)
                       for k, v in sorted(FORTY_SEAH_CM3.items())],
            screenSource='Yoma 3:4: a sheet of fine linen spread between the Kohen Gadol and the people.',
            screenScope=('Modelled only at the Kohen Gadol\'s Yom Kippur mikveh, which is the only '
                         'immersion for which a source calls for a separation. The other three have none.'),
            halachicScope=('These figures are arithmetic on published shiurim, not a ruling. Whether a pool '
                           'is a valid mikveh turns on the provenance of its water and its connection to the '
                           'ground, neither of which is modelled or claimed.'))

    if 'southgate' in groups:
        parts, points, covered, _ = build_court_channel(SOUTHGATE_ROUTE, 'SouthGate')
        meshes.append(('SM_MikdashWaterV1_SouthGateBranch', parts, 'stone',
                       ['THE BOOK\'S ROUTE, built as an alternative and never as the primary geometry:',
                        '"Lishchno Tidreshu" p. 340 (on Yechezkel 42:12) reads the stream as issuing from',
                        'the Kodesh HaKodashim and leaving by the SOUTHERN gate of the inner court, which',
                        'is why the Second Temple\'s Shaar HaMayim bore that name. The plain sense of 47:1-2',
                        'has it leave by the outer EAST gate. Both readings are recorded in sources.md.']))
        meshes.append(('SM_MikdashWaterV1_SouthGateWater', build_court_water(SOUTHGATE_ROUTE), 'water',
                       ['Free surface of the south-gate branch.']))
        facts['southgate'] = dict(
            status='disputed alternative, not the primary geometry',
            claim=('Book p. 340: water goes out from the Kodesh HaKodashim to the southern gate, and that '
                   'is why the Second Temple gate was called Shaar HaMayim.'),
            counterclaim='Yechezkel 47:2 has the water at the right shoulder of the OUTER EAST gate.',
            waypoints=[dict(x=r['x'], y=r['y'], surfaceTopZ=r['top'], note=r['note']) for r in SOUTHGATE_ROUTE])

    for name, parts, role, _ in meshes:
        MATERIAL_ROLE[name] = role
    return meshes, facts


def export(groups=DEFAULT_GROUPS, force=False):
    groups = tuple(g for g in GROUPS if g in groups)
    if not groups:
        raise SystemExit('no known groups requested; choose from ' + ', '.join(GROUPS))
    arch_rows, arch_data = load_architecture()
    anchor_checks, anchor_errors = verify_anchors(arch_rows)
    if anchor_errors and not force:
        raise SystemExit('architecture anchors do not match the manifest:\n  ' + '\n  '.join(anchor_errors))
    header_check = verify_against_header()
    if not header_check['constantsMatched'] and not force:
        raise SystemExit('WaterFlowMath.h constants differ from this script: '
                         + ', '.join(header_check['missing']))

    meshes, facts = build_all(groups)
    flat = [(part_name, solid) for _, parts, _, _ in meshes for part_name, solid in parts]
    total_triangles = sum(len(solid[1]) for _, solid in flat)
    if total_triangles > TRIANGLE_BUDGET and not force:
        raise SystemExit('triangle budget exceeded: %d > %d' % (total_triangles, TRIANGLE_BUDGET))

    # Water surfaces sit inside their own channel by construction, so the clearance check
    # runs on the masonry only; a water ribbon inside its trough is not a finding.
    masonry = [(n, s) for n, s in flat if 'Water' not in n]
    clearance = clearance_report(arch_rows, masonry)
    clearance['namedClearancesCm'] = named_clearances(arch_rows, masonry)
    if clearance['blockers'] and not force:
        summary = sorted({'%s vs %s' % (b['part'], b['mesh']) for b in clearance['blockers']})
        raise SystemExit('the generated channel intersects %d architecture meshes that are not paving:\n  %s'
                         % (len(clearance['blockers']), '\n  '.join(summary[:20])))

    OBJ_DIR.mkdir(parents=True, exist_ok=True)
    records, readbacks = [], []
    for name, parts, role, provenance in meshes:
        record = write_obj(name, parts, OBJ_DIR / (name + '.obj'), provenance)
        record['materialRole'] = role
        record['provenance'] = provenance
        records.append(record)
        readbacks.append(readback(OBJ_DIR / (name + '.obj'), record))

    preview = write_plan(OUT / 'water-plan.png', arch_rows, flat)

    manifest = dict(
        version='MikdashWaterV1',
        generated=datetime.now(timezone.utc).isoformat(),
        script='Scripts/create_water_geometry.py',
        scriptSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope=('Offline geometry export only. No engine launch, no Content/ change, no map action, '
               'no visual, walking or halachic acceptance. Placement is Scripts/release_water.py.'),
        units='centimetres; canonical Unreal axes X east, +Y south, Z up',
        amahCm=AMAH,
        amahNote=('50 cm is this project\'s modelling amah, used by every other geometry script here. '
                  'The book itself converts at 48 cm (R\' A. C. Naeh) and cites the Chazon Ish at 57.6 cm; '
                  'both are carried in the forty-se\'ah arithmetic below.'),
        destination=DEST,
        targetMap='/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
        objAdapter=OBJ_NOTE,
        architectureManifest=dict(file='SourceAssets/architecture-manifest.json',
                                  sha256=hashlib.sha256(ARCH_MANIFEST.read_bytes()).hexdigest(),
                                  meshCount=arch_data['meshCount']),
        anchorChecks=anchor_checks,
        anchorErrors=anchor_errors,
        runtimeHeaderCheck=header_check,
        groups=list(groups),
        totalTriangles=total_triangles,
        triangleBudget=TRIANGLE_BUDGET,
        meshes=records,
        readback=readbacks,
        clearance=clearance,
        preview=preview,
        facts=facts,
        kiyor=dict(
            alreadyPresent=True,
            evidence=('SourceAssets/architecture-manifest.json carries the kiyor as sourcePart "vessel": '
                      '"Turned pedestal", "Hollow basin with inner wall", twelve "Spout" meshes and a '
                      '"Water recessed below rolled rim" mesh whose semantic is already "water".'),
            worldBoundsCm=dict(min=[-2055.3, 1394.6, 625.0], max=[-1844.7, 1605.3, 750.5]),
            position='between the Ulam and the altar, on the south, as Shemos 30:18 and the book (p. 173) require',
            spouts=12,
            existingWaterMaterial='/Game/MikdashV3/Materials/M_Water_e67b7dbe9a',
            action='NOT REBUILT. Nothing here touches it.',
            notBuilt=('The book (p. 173) adds two fittings this map does not have: the BOR into which the '
                      'kiyor is lowered at night so its water is not disqualified, and the MUCHNI (the '
                      'pulley that lowers it), the vessel d\'Oraisa and the pulley d\'Rabbanan. They are '
                      'vessel work, not water work, and are left to whoever owns the keilim.')),
        depicted=[
            'the stream issuing from under the threshold of the House, eastward (47:1)',
            'its descent on the right (south) side of the House and its passage SOUTH OF THE ALTAR (47:1)',
            'its emergence at the right (south) shoulder of the outer east gate (47:2)',
            'the four measured thousands, as literal distances, with the depth at each (47:3-5)',
            'four mikvaot with steps down, and a linen screen at the Kohen Gadol\'s (Yoma 3:4)',
        ],
        assertedNotDepicted=[
            'the descent to the Aravah and into the sea, and the healing of the sea\'s waters (47:8)',
            'the fishermen standing from Ein Gedi to Ein Eglayim (47:10)',
            'the marshes and swamps that are not healed, being given to salt (47:11)',
            'the trees on both banks, leaf unwithering and fruit unfailing, new fruit monthly, '
            'the fruit for food and the leaf for healing, because the water issues from the Mikdash (47:12)',
            'reason: all of these lie tens of kilometres east of the map; the built channel stops at the '
            'fourth measurement, 2.000 km east of the outer gate.',
        ],
        limitations=[
            'A courtyard channel is a CUT in paving this script does not own and cannot boolean. The '
            'generated masonry therefore occupies the paving, platform and stair meshes listed in '
            'clearance.hosts; those are intended, and every non-paving contact is a blocker that fails '
            'the export.',
            'No terrain east of the mount is checked here: the architecture manifest ends at X 9200. The '
            'far-field segments are checked against the live level by Scripts/release_water.py.',
            'Widths, depths, grades and every mikveh dimension are authored. The prophet gives four depths '
            'in body parts and no widths at all.',
            'The forty-se\'ah figures are arithmetic, not a ruling.',
            'The route is disputed: the book takes the stream out by the inner court\'s SOUTH gate, the '
            'plain sense of 47:1-2 by the outer EAST gate. The east route is built; the south is available '
            'as group "southgate". Neither is asserted over the other.',
        ])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'geometry-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    (OUT / 'clearance.json').write_text(json.dumps(clearance, indent=2) + '\n', encoding='utf-8')
    return manifest


def offline_summary(groups=DEFAULT_GROUPS):
    arch_rows, _ = load_architecture()
    checks, errors = verify_anchors(arch_rows)
    return dict(script='Scripts/create_water_geometry.py', groups=list(groups),
                architectureManifestPresent=ARCH_MANIFEST.exists(),
                anchorsVerified=not errors, anchorErrors=errors,
                anchorCount=len(checks),
                runtimeHeaderCheck=verify_against_header(),
                outputFolder=str(OUT),
                note='run with --export to write the OBJs, the manifest, the clearance report and the plan')


def _main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--export', action='store_true', help='write the OBJs and the manifests')
    parser.add_argument('--groups', default=','.join(DEFAULT_GROUPS),
                        help='comma-separated subset of ' + ','.join(GROUPS))
    parser.add_argument('--force', action='store_true',
                        help='write even when an anchor, the header cross-check or a clearance fails')
    args = parser.parse_args()
    groups = tuple(g.strip().lower() for g in args.groups.split(',') if g.strip())
    if args.export:
        manifest = export(groups, force=args.force)
        print(json.dumps(dict(
            wrote=str(OUT), groups=manifest['groups'], totalTriangles=manifest['totalTriangles'],
            meshes=[dict(name=m['name'], triangles=m['triangles'], parts=m['parts'],
                         bounds=m['canonicalBoundsCm']) for m in manifest['meshes']],
            blockers=len(manifest['clearance']['blockers']),
            hosts=[h['mesh'] for h in manifest['clearance']['hosts']],
            namedClearances=manifest['clearance']['namedClearancesCm'],
        ), indent=2))
    else:
        print(json.dumps(offline_summary(groups), indent=2))


if __name__ == '__main__':
    _main()
