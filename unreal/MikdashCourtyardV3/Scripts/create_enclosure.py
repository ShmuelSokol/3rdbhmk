"""EnclosureV2 - the Yechezkel 42:15-20 sacred precinct as INSTANCED modules, plus the
overlay boundary, the terrain-following ground profile and the exact modern-city hide set for
the three-state YECHEZKEL / MODERN / OVERLAY toggle.

AUTHORED_OFFLINE_SOURCE. This module never imports `unreal`, never touches Content/, never
opens a map and never launches the editor. It writes OBJ modules, a geometry manifest, a
plan-view PNG, per-target precinct receipts and a review JSON under
SourceAssets/enclosure-review/. The guarded native importer/placer is the separate
Scripts/release_enclosure.py.

WHY A SECOND ENCLOSURE GENERATOR
--------------------------------
Scripts/create_mount_enclosure.py already exports the same 3000-amah square as 52 CHUNK
meshes (32 wall chunks of 8 sub-boxes each, stepped to follow the current-city DEM) under
SourceAssets/FutureMountV1/EnclosureV1. That set stays as it is; this module does not modify
it and does not replace it.

What it cannot do is be toggled cheaply. A 1.44 km ring as 32 baked chunks is 32 actors with
32 large bounding boxes, no per-segment culling, and no way to fade. This module emits FIVE
module meshes instead - one wall segment, one gate, one corner, one overlay slab and one
foundation box - which AMikdashEnclosure places as HierarchicalInstancedStaticMeshComponent
instances, each at its own ground Z. The renderer then gets one draw call per component with
per-instance frustum culling and per-instance LOD, and a state change is a material scalar
rather than a re-import.

    BUDGET, RTX 2070 (8 GB, 1080p) - printed by --report and asserted by --tests
      wall        467 instances x  WALL_TRIS  (13 of 480 segments removed for the five gates)
      gates         5 instances x  GATE_TRIS
      corners       4 instances x  CORNER_TRIS
      overlay     480 instances x  OVERLAY_TRIS
      foundation  476 instances x  FOUNDATION_TRIS (one under every wall, gate and corner)
      five HISM components, one draw call each before instance culling.
    For scale, the Old City facade set the YECHEZKEL state hides is 3,416,580 triangles
    across 190 actors, so the enclosure costs a few per cent of what it replaces.

WHERE THE SQUARE IS
-------------------
Nowhere in this file. Every position comes from
Plugins/MikdashRuntime/Source/MikdashRuntime/Public/EnclosureMath.h, which is parsed here for
its constants and is the single authority shared by the runtime actor, the release script and
the standalone C++ test. If those four ever disagree about where the square is, the bug is in
that header and only there.

The anchoring, and the one place the sources do not close, is documented at length in the
header and in SourceAssets/enclosure-review/sources.md. In short: Lishchno Tidreshu fig. 2'2
(p. 113) gives 500 amot clear west and 501 clear north, and states the Middot 2:1 order
(largest south, then east, then north, least west) after Mishkenei Elyon 196 ch.1 m.1. That
order needs a court envelope WIDER east-west than north-south. The book's diagram envelope is
about 351 x 346 and satisfies it (2149 east, 2153 south). This project's measured court
supporting platform is 324 x 324 - square - so the order inverts by exactly one amah
(east 2176, south 2175). That is reported, not hidden.

TWO TARGETS
-----------
The main map is baked at 50 Unreal cm per amah; the isolated candidate at the book's own
48 cm. The city, the terrain and the OSM alignment are METRIC in both and do not move; only
the Temple (and so the court platform half-extent, 8100 -> 7776) and the precinct scale.
Every number below is therefore computed per target and written to
SourceAssets/enclosure-review/precinct-<Target>.json, and the release script refuses to
place against a receipt whose square it cannot reproduce from the header.

UNITS OF THE OSM EXPORT (the finding that corrected an earlier count)
---------------------------------------------------------------------
jerusalem.json `points` and `terrain.heights` are in AMOT at 0.5 m, not metres, and the level
already carries the alignment UE_cm = ((x + 17.5097) * 50, (y - 0.5513) * 50). The constants
are SOURCE_ALIGN_X_AMOT / SOURCE_ALIGN_Z_AMOT in Scripts/create_mount_enclosure.py and are
NEVER applied twice. Heights are relative to referenceElevationMetres 748 (Z 0 = 748 m) and
are always converted at 50 cm per amah - the terrain is metric context in both maps.

OBJ ADAPTER CONVENTION (project standard, unchanged)
----------------------------------------------------
Canonical vertices are Unreal cm, X east, +Y south, Z up, module-local with the origin at the
centre of the module's footprint on the ground. Every OBJ is written with Y REFLECTED and
triangle winding REVERSED - the legacy importer reflects Y back - exactly as
create_keilim_ti_v1.write_obj, create_sanctuary_doors.export and create_oldcity_facades do.
Canonical solids are built closed and flipped when needed so the canonical signed volume is
POSITIVE; readback() re-parses each file, recomputes the signed volume in FILE space and
reproves the bounds. One `o` object and NO `g` groups per file.

RUN ORDER
---------
    python Scripts/create_enclosure.py --tests     compile and run the standalone C++ test
    python Scripts/create_enclosure.py --export    write modules, manifest, preview, receipts
    python Scripts/create_enclosure.py --report    the numbers for the review document
then, separately and never while another native job is running,
    UnrealEditor-Cmd ... -run=pythonscript -script=".../Scripts/release_enclosure.py"
"""
import argparse
import hashlib
import json
import math
import re
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
HEADER = ROOT / 'Plugins/MikdashRuntime/Source/MikdashRuntime/Public/EnclosureMath.h'
TEST_SOURCE = ROOT / 'Plugins/MikdashRuntime/Tests/EnclosureMathTest.cpp'
OUT = ROOT / 'SourceAssets/enclosure-review'
DEST = '/Game/MikdashV3/FutureMountV1/EnclosureV2'
FACADES_MANIFEST = ROOT / 'SourceAssets/context-review/OldCityFacadesV1/facades-manifest.json'
BUILDINGS_REOPEN = ROOT / 'SourceAssets/context-review/buildings-reopen.json'
EXISTING_DESIGN = ROOT / 'SourceAssets/FutureMountV1/EnclosureV1/enclosure-design.json'
TERRAIN_CUT_FOLDER = ROOT / 'SourceAssets/FutureMountV1/terrain-generated'
TERRAIN_CUT_MANIFEST = TERRAIN_CUT_FOLDER / 'terrain-cut-manifest.json'
WORKSPACE = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace')
# The OSM source the whole context was built from, still holding every building as an explicit
# polygon and the terrain as a 257 x 257 height grid. It lives outside the project tree
# (create_oldcity_facades.py reads the same file), so its absence is handled rather than fatal.
JERUSALEM_SOURCE = WORKSPACE / 'mikdash-walkthrough' / 'public' / 'context' / 'jerusalem.json'
# The frozen mesh export the 256 level terrain tiles were built from (terrain-import receipt
# manifestSha256 chain -> terrain-cut-manifest sourceSha256). Same DEM at 0.05 amot precision,
# plus the exporter's edit of the Haram esplanade; the level's tiles ARE this grid.
LEVEL_TERRAIN_SOURCE = WORKSPACE / 'output' / 'architecture-review' / 'jerusalem-meshes.json'
LEVEL_TERRAIN_SHA256 = 'cec2748be02f7a52616407c6bee12618369b75cbf93c5c8dcd5d4135cdfd52fb'
# The frozen partition of the OSM buildings into the 1499 SM_JerusalemBuildings_Grid_* meshes:
# 11,400 connected components, each with its source box and its assigned 100 m cell. This is
# the level-true membership; the OSM polygons alone cannot say which actor a building is in.
BUILDINGS_FROZEN_MANIFEST = WORKSPACE / 'output' / 'cloud-unreal-v3' / 'context-review' / 'buildings-manifest.json'
BUILDINGS_FROZEN_FBX_SHA256 = '271bc9b4e1297421a33dde0b00172ad6111decabdb683e05267d4b972aca5408'
# The alignment already baked into every context mesh in the level, recorded in
# SourceAssets/visual-review/mount-platform-design.json `sourceData.alignment`.
# NEVER apply it twice; these coordinates are source amot, not level cm.
SOURCE_TX_AMOT = 17.509700315687695
SOURCE_TZ_AMOT = -0.5513496449385334
CONTEXT_CM_PER_AMOT = 50.0            # the city and terrain are metric in BOTH maps
GRID_N = 257
GRID_ORIGIN_AMOT = -6400.0
GRID_STEP_AMOT = 50.0

VCVARS = Path(r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC'
              r'\Auxiliary\Build\vcvars64.bat')

CELL_CM = 10000.0                     # the 100 m context grid, shared with create_oldcity_facades
STEPS_PER_SIDE = 600                  # ground profile stations: 601 per side, one every 250 cm at 50
FOOTING_AMOT = 1.0                    # authored: the substructure reaches one amah below the lowest ground
DEM_ROUNDING_CM = 25.0                # jerusalem.json heights are whole amot; half an amah is rounding, not disagreement


# =====================================================================================
# 1. Constants, read from the header rather than restated
# =====================================================================================
def header_constants():
    """Parse the `constexpr double NAME = VALUE;` lines out of EnclosureMath.h.

    Restating any of these here would create exactly the drift the header exists to prevent,
    so they are read. A missing name is a hard error, never a default.
    """
    text = HEADER.read_text(encoding='utf-8')
    found = {}
    for name, value in re.findall(r'constexpr\s+double\s+(\w+)\s*=\s*([^;]+);', text):
        value = value.strip()
        if re.fullmatch(r'-?\d+(\.\d+)?', value):
            found[name] = float(value)
    # PrecinctSideAmot is written as a product of two other constants.
    if 'PrecinctReedsPerSide' in found and 'AmotPerReed' in found:
        found['PrecinctSideAmot'] = found['PrecinctReedsPerSide'] * found['AmotPerReed']
    required = ('ProjectCmPerAmah', 'Candidate48CmPerAmah', 'AmotPerReed', 'PrecinctReedsPerSide',
                'PrecinctSideAmot', 'MiddotHarHaBayitAmot', 'CourtPlatformHalfExtentUnrealCm',
                'BookClearWestAmot', 'BookClearNorthAmot',
                'BookDiagramEnvelopeEastWestAmot', 'BookDiagramEnvelopeNorthSouthAmot',
                'BookImpliedAmahRealCm', 'BookStatedPrecinctSideMetres')
    missing = [name for name in required if name not in found]
    if missing:
        raise RuntimeError('EnclosureMath.h no longer defines: ' + ', '.join(missing))
    return found


K = header_constants()
A = K['ProjectCmPerAmah']                     # 50 Unreal cm per amah - the main map's baked scale
SIDE_AMOT = K['PrecinctSideAmot']             # 3000
COURT_HALF = K['CourtPlatformHalfExtentUnrealCm']
CLEAR_W = K['BookClearWestAmot']
CLEAR_N = K['BookClearNorthAmot']

# The two maps. Court half-extent scales with the amah (the Temple was converted by .96 about
# the origin); the city does not. Candidate map name from HANDOFF-FOR-FABLE-20260908.md.
TARGETS = {
    'Main50': dict(
        map='/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
        cmPerAmah=A, courtHalfCm=COURT_HALF,
        note='Main/default/startup map, baked at 50 Unreal cm per amah.'),
    'Candidate48': dict(
        map='/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
        cmPerAmah=K['Candidate48CmPerAmah'],
        courtHalfCm=COURT_HALF * K['Candidate48CmPerAmah'] / A,
        note='Isolated 48 cm candidate (the approved amah), NOT promoted; Temple converted by .96 '
             'about the origin, city and terrain metric and unmoved.'),
}

MODULE_LEN_AMOT = 25.0                        # 120 modules a side, exactly
WALL_THICK_AMOT = 6.0                         # Yechezkel 40:5: a reed thick
WALL_HEIGHT_AMOT = 6.0                        # a reed high (book pp. 115-117)
GATE_OPENING_W_AMOT = 10.0                    # certain: opening 10 amot wide
GATE_OPENING_H_AMOT = 50.0                    # certain: opening 50 amot high
GATE_PIER_W_AMOT = 10.0                       # authored (*): the book gives no pier width
GATE_TOTAL_H_AMOT = 60.0                      # authored (*)
GATE_DEPTH_AMOT = 6.0                         # certain: the gate is as thick as the wall
FOUNDATION_WIDTH_FACTOR = 1.20                # authored: the substructure is a fifth wider than the wall
FOUNDATION_UNIT_H_CM = 100.0                  # the foundation box is 100 cm tall and scaled in Z per instance

# Module dimensions at the BAKED scale (50). The candidate scales every instance by .96.
MODULE_LEN_CM = MODULE_LEN_AMOT * A
WALL_THICK_CM = WALL_THICK_AMOT * A
WALL_HEIGHT_CM = WALL_HEIGHT_AMOT * A
GATE_OPENING_W_CM = GATE_OPENING_W_AMOT * A
GATE_OPENING_H_CM = GATE_OPENING_H_AMOT * A
GATE_PIER_W_CM = GATE_PIER_W_AMOT * A
GATE_TOTAL_H_CM = GATE_TOTAL_H_AMOT * A
GATE_DEPTH_CM = GATE_DEPTH_AMOT * A
OVERLAY_SPACING_CM = 1250.0
OVERLAY_SLAB_THICK_CM = 12.0                  # a hair, so the band never z-fights a facade

# The five gates. E, N and W sit on the Temple's own axes (world X = 0 / world Y = 0, which
# is the axis of the court's east gate and of the walking start [2016, 0]); the two south
# gates at a third and two thirds along the south wall FROM THE CORNERS, so the same rule
# serves both targets. The COUNT per side is the book's (five gates, two south - Mishkenei
# Elyon 196 m.2); the along-wall positions are the project's assumption.
GATE_RULES = [
    dict(id='N', side=0, rule=('world_x', 0.0),
         source='count: Mishkenei Elyon 196 m.2 (one north); position AUTHORED - the Temple north-south axis (world X 0)'),
    dict(id='E', side=1, rule=('world_y', 0.0),
         source='count: Mishkenei Elyon 196 m.2 (one east); Yechezkel 42:15 measures out through the east gate; '
                'position AUTHORED - the Temple east-west axis (world Y 0), the axis of the court east gate at X 8600 '
                'and of the walking start [2016, 0], so the tour approach passes through it'),
    dict(id='S1', side=2, rule=('fraction_from_west', 1.0 / 3.0),
         source='count: Mishkenei Elyon 196 m.2 (two south); position AUTHORED - one third along the south wall from the SW corner'),
    dict(id='S2', side=2, rule=('fraction_from_west', 2.0 / 3.0),
         source='count: Mishkenei Elyon 196 m.2 (two south); position AUTHORED - two thirds along the south wall from the SW corner'),
    dict(id='W', side=3, rule=('world_y', 0.0),
         source='count: Mishkenei Elyon 196 m.2 (one west); position AUTHORED - the Temple east-west axis (world Y 0)'),
]


# =====================================================================================
# 2. The square, reproduced from the header's rule, per target
# =====================================================================================
def square(a=A, court_half=COURT_HALF):
    """West and north OUTER faces at the stated clearances from the platform; the rest falls
    out of the 3000. Identical arithmetic to MakeSquareFromClearances."""
    side = SIDE_AMOT * a
    west = -court_half - CLEAR_W * a
    north = -court_half - CLEAR_N * a
    return dict(west=west, north=north, east=west + side, south=north + side, sideCm=side,
                cmPerAmah=a, courtHalfCm=court_half,
                centre=[west + side / 2.0, north + side / 2.0])


def target_square(name):
    t = TARGETS[name]
    return square(t['cmPerAmah'], t['courtHalfCm'])


def corners(sq):
    """NW, NE, SE, SW - clockwise on screen with +Y south. Matches SquareCorners()."""
    return [(sq['west'], sq['north']), (sq['east'], sq['north']),
            (sq['east'], sq['south']), (sq['west'], sq['south'])]


def clearances(sq):
    a, h = sq['cmPerAmah'], sq['courtHalfCm']
    return dict(west=(-h - sq['west']) / a, north=(-h - sq['north']) / a,
                east=(sq['east'] - h) / a, south=(sq['south'] - h) / a)


def gate_fraction(sq, rule):
    """Gate rule -> fraction 0..1 from the side's start corner. Matches FractionAlongSide()."""
    c = corners(sq)
    start = c[rule['side']]
    end = c[(rule['side'] + 1) % 4]
    kind, value = rule['rule']
    if kind == 'world_x':
        return (value - start[0]) / (end[0] - start[0])
    if kind == 'world_y':
        return (value - start[1]) / (end[1] - start[1])
    if kind == 'fraction_from_west':
        # The south side runs SE -> SW (clockwise), so "from the west" is from its END corner.
        return 1.0 - value if rule['side'] == 2 else value
    raise ValueError(kind)


def gates(sq):
    out = []
    c = corners(sq)
    for rule in GATE_RULES:
        fraction = gate_fraction(sq, rule)
        start, end = c[rule['side']], c[(rule['side'] + 1) % 4]
        out.append(dict(id=rule['id'], side=rule['side'], fraction=fraction,
                        source=rule['source'],
                        certainty='count certain; position authored',
                        positionCm=[start[0] + (end[0] - start[0]) * fraction,
                                    start[1] + (end[1] - start[1]) * fraction],
                        openingAmot=dict(width=GATE_OPENING_W_AMOT, height=GATE_OPENING_H_AMOT,
                                         depth=GATE_DEPTH_AMOT),
                        openingCm=dict(width=GATE_OPENING_W_AMOT * sq['cmPerAmah'],
                                       height=GATE_OPENING_H_AMOT * sq['cmPerAmah'],
                                       depth=GATE_DEPTH_AMOT * sq['cmPerAmah'])))
    return out


def wall_segments(sq):
    """Mirror of PlanWall(): (side, step, lo, hi, kept) for every segment."""
    a = sq['cmPerAmah']
    side_cm = sq['sideCm']
    module = MODULE_LEN_AMOT * a
    per_side = int(math.floor(side_cm / module + 0.5))
    seg = side_cm / per_side
    full = (GATE_OPENING_W_AMOT + 2.0 * GATE_PIER_W_AMOT) * a
    gate_list = gates(sq)
    rows = []
    for side in range(4):
        for step in range(per_side):
            lo, hi = seg * step, seg * (step + 1)
            blocked = False
            for gate in gate_list:
                if gate['side'] != side:
                    continue
                centre = side_cm * gate['fraction']
                if hi > centre - full / 2.0 + 1e-6 and lo < centre + full / 2.0 - 1e-6:
                    blocked = True
            rows.append(dict(side=side, step=step, lo=lo, hi=hi, kept=not blocked))
    return per_side, seg, rows


def wall_plan(sq):
    per_side, seg, rows = wall_segments(sq)
    kept = sum(1 for r in rows if r['kept'])
    dropped = len(rows) - kept
    gate_count = len(GATE_RULES)
    return dict(segmentsPerSide=per_side, segmentLengthCm=seg, wallInstances=kept,
                droppedForGates=dropped, gateInstances=gate_count, cornerInstances=4,
                overlayInstances=per_side * 4, foundationInstances=kept + gate_count + 4)


# =====================================================================================
# 3. Geometry primitives - identical conventions to create_keilim_ti_v1
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
    """Flip the winding if the signed volume came out negative, so every canonical solid is
    outward-wound before the adapter reverses it again on the way to file."""
    return (v, f) if volume(v, f) > 0 else (v, [(a, c, b) for a, b, c in f])


def closed(v, f):
    keys = [tuple(round(x, 6) for x in p) for p in v]
    edges = {}
    for a, b, c in f:
        for i, j in ((a, b), (b, c), (c, a)):
            key = tuple(sorted((keys[i], keys[j])))
            edges[key] = edges.get(key, 0) + 1
    return all(count == 2 for count in edges.values())


def box(centre, size):
    hx, hy, hz = [s / 2.0 for s in size]
    cx, cy, cz = centre
    v = [(cx + sx * hx, cy + sy * hy, cz + sz * hz)
         for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    f = [(0, 1, 3), (0, 3, 2), (4, 6, 7), (4, 7, 5),
         (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6),
         (0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3)]
    return orient(v, f)


def merge(parts):
    """Concatenate closed solids into one mesh, keeping each solid's own winding."""
    vertices, faces = [], []
    for pv, pf in parts:
        offset = len(vertices)
        vertices.extend(pv)
        faces.extend([(a + offset, b + offset, c + offset) for a, b, c in pf])
    return vertices, faces


# =====================================================================================
# 4. The five modules
# =====================================================================================
# Every module's origin is the centre of its footprint ON THE GROUND, with local +X running
# ALONG the wall and local +Y pointing OUTWARD. AMikdashEnclosure places an instance with the
# side's outward yaw minus ninety, which is exactly that convention, at the module's own
# ground Z from the baked profile.

def wall_module():
    """One 25-amah length of the outer wall: a battered body with a plinth, a coping, and a
    shallow pilaster rhythm on both faces.

    The pilasters are NOT ornament for its own sake. A 1.44 km run of flat stone reads as a
    grey band with no scale at any distance; a repeating vertical at a fixed pitch is what
    lets a viewer judge how far away the far wall is. The book describes the wall's section
    (a reed thick, a reed high - Yechezkel 40:5) and says nothing about its face, so the
    articulation is marked AUTHORED in the manifest.
    """
    length = MODULE_LEN_CM
    thick = WALL_THICK_CM
    height = WALL_HEIGHT_CM
    parts = []
    # plinth, slightly proud, then the body, then a coping proud again
    parts.append(box((0.0, 0.0, height * 0.06), (length, thick * 1.10, height * 0.12)))
    parts.append(box((0.0, 0.0, height * 0.53), (length, thick, height * 0.82)))
    parts.append(box((0.0, 0.0, height * 0.97), (length, thick * 1.14, height * 0.06)))
    # pilasters, eight to a module (one every 156.25 cm ~ 3 amot), both faces
    count = 8
    pitch = length / count
    for index in range(count):
        x = -length / 2.0 + pitch * (index + 0.5)
        for sign in (-1.0, 1.0):
            parts.append(box((x, sign * (thick * 0.5 + thick * 0.05), height * 0.50),
                             (pitch * 0.34, thick * 0.10, height * 0.76)))
    return merge(parts)


def gate_module():
    """A gate block: two piers, a lintel over the opening, and a cornice.

    CERTAIN from the book (pp. 115-117, after Yechezkel 40): the opening is 10 amot wide and
    50 amot high, and the gate is six amot deep, the thickness of the wall itself.
    AUTHORED (*): the 10-amah piers, the 60-amah overall height and every profile. Doors are
    omitted - the gate stands open, as in the book's own figures.
    """
    opening_w = GATE_OPENING_W_CM
    opening_h = GATE_OPENING_H_CM
    pier = GATE_PIER_W_CM
    depth = GATE_DEPTH_CM
    total_w = opening_w + 2.0 * pier
    total_h = GATE_TOTAL_H_CM
    parts = []
    for sign in (-1.0, 1.0):
        cx = sign * (opening_w + pier) / 2.0
        parts.append(box((cx, 0.0, opening_h / 2.0), (pier, depth, opening_h)))
        # a shallow jamb order on the outward face
        parts.append(box((cx, depth * 0.55, opening_h / 2.0), (pier * 0.55, depth * 0.10, opening_h * 0.94)))
    # lintel over the opening, then the mass above it, then the cornice
    lintel_h = total_h * 0.06
    parts.append(box((0.0, 0.0, opening_h + lintel_h / 2.0), (total_w, depth * 1.08, lintel_h)))
    upper = total_h - opening_h - lintel_h
    parts.append(box((0.0, 0.0, opening_h + lintel_h + upper / 2.0), (total_w, depth, upper)))
    parts.append(box((0.0, 0.0, total_h - total_h * 0.02), (total_w * 1.04, depth * 1.14, total_h * 0.04)))
    return merge(parts)


def corner_module():
    """A corner: the two wall ends returned into a square block, with a low pylon that carries
    the marker light AMikdashEnclosure attaches at each corner.

    Yechezkel measures the four sides and says nothing about the corners; the block is the
    minimum that closes the ring without a mitred seam, and is AUTHORED.
    """
    thick = WALL_THICK_CM
    height = WALL_HEIGHT_CM
    size = thick * 1.6
    parts = [box((0.0, 0.0, height * 0.06), (size * 1.12, size * 1.12, height * 0.12)),
             box((0.0, 0.0, height * 0.53), (size, size, height * 0.82)),
             box((0.0, 0.0, height * 0.97), (size * 1.16, size * 1.16, height * 0.06))]
    # the pylon, four faces stepped in
    for step, (scale, z0, z1) in enumerate([(0.62, 1.00, 1.34), (0.44, 1.34, 1.58),
                                            (0.28, 1.58, 1.74)]):
        parts.append(box((0.0, 0.0, height * (z0 + z1) / 2.0),
                         (size * scale, size * scale, height * (z1 - z0))))
    return merge(parts)


def overlay_slab():
    """One segment of the translucent boundary band, as a very thin closed slab rather than a
    single quad.

    A bare quad is one-sided in the default translucent material and disappears when the
    viewer crosses the line, which is precisely the moment the overlay is most useful. A thin
    slab is two-sided by construction, still costs twelve triangles, and never z-fights the
    facade behind it because it stands 12 cm proud of nothing at all.
    """
    return box((0.0, 0.0, 0.5), (1.0, OVERLAY_SLAB_THICK_CM / max(1.0, WALL_HEIGHT_CM), 1.0))


def foundation_module():
    """The authored substructure: a plain closed box one module long, a fifth wider than the
    wall, 100 cm tall, scaled in Z per instance to the depth GroundSpan() computes.

    The sources say nothing about foundations - Yechezkel gives the wall a section and the
    book a height - so this is AUTHORED, and is what lets the wall stand at its full six amot
    on the Kidron slopes instead of floating over them or burying into them. The plain box
    reads as bedding/retaining masonry under the plinth; it carries the wall material.
    """
    return box((0.0, 0.0, FOUNDATION_UNIT_H_CM / 2.0),
               (MODULE_LEN_CM, WALL_THICK_CM * FOUNDATION_WIDTH_FACTOR, FOUNDATION_UNIT_H_CM))


MODULES = [
    ('SM_EnclosureV2_WallSegment', wall_module, 'stone',
     'One 25-amah run of the outer wall. Section certain (a reed thick, a reed high, '
     'Yechezkel 40:5); face articulation AUTHORED.'),
    ('SM_EnclosureV2_Gate', gate_module, 'stone',
     'Gate block. Opening 10 x 50 amot and depth 6 amot certain (book pp. 115-117); '
     'piers, 60-amah height and all profiles AUTHORED. Doors omitted - the gate stands open.'),
    ('SM_EnclosureV2_Corner', corner_module, 'stone',
     'Corner block and marker pylon. AUTHORED; Yechezkel measures sides, not corners.'),
    ('SM_EnclosureV2_OverlaySlab', overlay_slab, 'overlay',
     'Unit slab for the OVERLAY band, scaled per instance to the sample step and the wall '
     'height. Not architecture - a reading aid.'),
    ('SM_EnclosureV2_Foundation', foundation_module, 'stone',
     'Substructure box under every wall, gate and corner module, scaled in Z to the depth '
     'between the highest and lowest ground the module crosses plus a one-amah footing. '
     'AUTHORED - the sources say nothing about foundations.'),
]


# =====================================================================================
# 5. OBJ write and readback (project adapter)
# =====================================================================================
def write_obj(name, mesh, path):
    vertices, faces = mesh
    vol = volume(vertices, faces)
    if not vol > 0:
        raise RuntimeError('inverted canonical solid: ' + name)
    if not closed(vertices, faces):
        raise RuntimeError('open canonical solid: ' + name)
    lines = ['# EnclosureV2 %s; Unreal legacy OBJ adapter (Y reflected, winding reversed)' % name,
             'o ' + name]
    index = 1
    for a, b, c in faces:
        # Y reflected AND winding reversed; the importer reflects Y back.
        p, q, r = [(vertices[i][0], -vertices[i][1], vertices[i][2]) for i in (a, c, b)]
        ab = [q[i] - p[i] for i in range(3)]
        ac = [r[i] - p[i] for i in range(3)]
        n = cross(ab, ac)
        length = math.sqrt(sum(x * x for x in ab))
        nl = math.sqrt(sum(x * x for x in n))
        if not (nl > 1e-8 and length > 1e-8):
            raise RuntimeError('degenerate triangle in ' + name)
        for vertex in (p, q, r):
            lines.append('v %.6f %.6f %.6f' % vertex)
        for uv in ((0.0, 0.0), (length / 100.0, 0.0),
                   (sum(ac[i] * ab[i] / length for i in range(3)) / 100.0, nl / length / 100.0)):
            lines.append('vt %.6f %.6f' % uv)
        for _ in range(3):
            lines.append('vn %.6f %.6f %.6f' % tuple(x / nl for x in n))
        lines.append('f ' + ' '.join('%d/%d/%d' % (k, k, k) for k in range(index, index + 3)))
        index += 3
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    bounds = {key: [fn(p[i] for p in vertices) for i in range(3)]
              for key, fn in (('min', min), ('max', max))}
    return dict(name=name, file=path.name,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                triangles=len(faces), canonicalBoundsCm=bounds,
                canonicalSignedVolumeCm3=round(vol, 4))


def readback(path, record):
    """Re-parse the written file and reprove it, so an adapter mistake fails here."""
    verts, normals, faces = [], [], []
    for line in path.read_text(encoding='ascii').splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == 'v':
            verts.append(tuple(map(float, parts[1:])))
        elif parts[0] == 'vn':
            normals.append(tuple(map(float, parts[1:])))
        elif parts[0] == 'f':
            faces.append([tuple(int(x) - 1 for x in t.split('/')) for t in parts[1:]])
    if len(faces) != record['triangles']:
        raise RuntimeError('triangle count changed on readback for ' + path.name)
    worst = 0.0
    for face in faces:
        a, b, c = [verts[t[0]] for t in face]
        ab = [b[i] - a[i] for i in range(3)]
        ac = [c[i] - a[i] for i in range(3)]
        cr = cross(ab, ac)
        area = math.sqrt(sum(x * x for x in cr))
        if not area > 1e-9:
            raise RuntimeError('degenerate face on readback in ' + path.name)
        worst = max(worst, abs(1.0 - sum(cr[i] * normals[face[0][2]][i] for i in range(3)) / area))
    if not worst < 1e-4:
        raise RuntimeError('normals disagree with winding in %s (%g)' % (path.name, worst))
    canonical = [(x, -y, z) for x, y, z in verts]
    bounds = {key: [fn(v[i] for v in canonical) for i in range(3)]
              for key, fn in (('min', min), ('max', max))}
    err = max(abs(bounds[key][i] - record['canonicalBoundsCm'][key][i])
              for key in bounds for i in range(3))
    if not err < 1e-4:
        raise RuntimeError('bounds changed on readback for %s (%g cm)' % (path.name, err))
    file_volume = volume(verts, [tuple(t[0] for t in face) for face in faces])
    if not file_volume > 0:
        raise RuntimeError('adapter sign unexpected for ' + path.name)
    return dict(mesh=record['name'], triangles=len(faces), boundsErrorCm=round(err, 9),
                worstNormalError=round(worst, 9),
                fileSpaceSignedVolumeCm3=round(file_volume, 3), normalsAndUvs='PASS')


# =====================================================================================
# 6. The ground under the wall
# =====================================================================================
def source_to_ue(x_amot, z_amot):
    """Source amot (east, south) -> level cm, with the alignment the level already baked."""
    return (x_amot + SOURCE_TX_AMOT) * CONTEXT_CM_PER_AMOT, (z_amot + SOURCE_TZ_AMOT) * CONTEXT_CM_PER_AMOT


def ue_to_source(x_cm, y_cm):
    return x_cm / CONTEXT_CM_PER_AMOT - SOURCE_TX_AMOT, y_cm / CONTEXT_CM_PER_AMOT - SOURCE_TZ_AMOT


class HeightGrid(object):
    """A 257 x 257 height grid in source amot, sampled with the source triangulation
    (cell (c, r): (v00, v01, v10), (v01, v11, v10)), exactly as create_mount_enclosure.Terrain."""

    def __init__(self, heights, label, sha256=None, precision_amot=None):
        if len(heights) != GRID_N * GRID_N:
            raise RuntimeError('%s: %d heights, expected %d' % (label, len(heights), GRID_N * GRID_N))
        self.h = heights
        self.label = label
        self.sha256 = sha256
        self.precision_amot = precision_amot

    def height_cm(self, x_cm, y_cm):
        xa, za = ue_to_source(x_cm, y_cm)
        fc = (xa - GRID_ORIGIN_AMOT) / GRID_STEP_AMOT
        fr = (za - GRID_ORIGIN_AMOT) / GRID_STEP_AMOT
        c, r = int(math.floor(fc)), int(math.floor(fr))
        if c < 0 or r < 0 or c >= GRID_N - 1 or r >= GRID_N - 1:
            return None
        u, v = fc - c, fr - r
        h = self.h
        h00 = h[r * GRID_N + c]
        h10 = h[r * GRID_N + c + 1]
        h01 = h[(r + 1) * GRID_N + c]
        h11 = h[(r + 1) * GRID_N + c + 1]
        if u + v <= 1.0:
            ha = h00 + u * (h10 - h00) + v * (h01 - h00)
        else:
            ha = h11 + (1.0 - u) * (h01 - h11) + (1.0 - v) * (h10 - h11)
        return ha * CONTEXT_CM_PER_AMOT


class CutTiles(object):
    """The four FutureMountV1 replacement tiles, as the triangles the level actually holds
    (UE cm, anchor already applied). Sampled by point-in-triangle; None outside them."""

    def __init__(self):
        self.tiles = []
        self.status = 'absent'
        if not TERRAIN_CUT_MANIFEST.exists():
            return
        manifest = json.loads(TERRAIN_CUT_MANIFEST.read_text(encoding='utf-8-sig'))
        for tile in manifest.get('tiles', []):
            path = TERRAIN_CUT_FOLDER / tile['geometryFile']
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            if not data.get('anchorAlreadyApplied'):
                raise RuntimeError('%s does not state anchorAlreadyApplied' % path.name)
            verts = data['vertices']
            tris = data['triangles']
            xs = [v[0] for v in verts]
            ys = [v[1] for v in verts]
            self.tiles.append(dict(name=data['assetName'], original=data['originalAssetName'],
                                   file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                   verts=verts, tris=tris,
                                   bounds=(min(xs), min(ys), max(xs), max(ys)),
                                   removedTriangles=len(data.get('sourceOriginalTriangles', [])) - len(tris)))
        self.status = 'loaded %d tiles' % len(self.tiles) if self.tiles else 'manifest present, no tile geometry'

    def height_cm(self, x, y):
        """(z, tile name) from the tile triangles, or (None, None). A point inside a tile's
        bounds but on removed ground (the platform footprint) returns (None, tile)."""
        for tile in self.tiles:
            x0, y0, x1, y1 = tile['bounds']
            if not (x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6):
                continue
            verts = tile['verts']
            for a, b, c in tile['tris']:
                p, q, r = verts[a], verts[b], verts[c]
                d = (q[1] - r[1]) * (p[0] - r[0]) + (r[0] - q[0]) * (p[1] - r[1])
                if abs(d) < 1e-9:
                    continue
                l1 = ((q[1] - r[1]) * (x - r[0]) + (r[0] - q[0]) * (y - r[1])) / d
                l2 = ((r[1] - p[1]) * (x - r[0]) + (p[0] - r[0]) * (y - r[1])) / d
                l3 = 1.0 - l1 - l2
                if l1 >= -1e-9 and l2 >= -1e-9 and l3 >= -1e-9:
                    return l1 * p[2] + l2 * q[2] + l3 * r[2], tile['name']
            return None, tile['name']
        return None, None


class Ground(object):
    """Three witnesses for the ground under the wall, and the rule that chooses between them.

    1. `dem`  - jerusalem.json terrain.heights: the OSM export's grid, whole amot.
    2. `level` - jerusalem-meshes.json 'Terrain 0': the grid the 256 level tiles were built
       from (sha256 frozen by the terrain import and the FutureMountV1 cut), 0.05 amot.
    3. `tile` - the four SM_JerusalemTerrain_0x_0x_FutureMountCut receipts: the triangles
       actually in the level where the west and north walls pass the Mount.

    The two grids agree to their rounding everywhere except a band under the Haram where the
    level grid was edited upward by the exporter (up to 42.7 amot); there the wall must meet
    the tiles that exist, so the LEVEL value is used and the disagreement is recorded. Inside
    a cut tile the tile receipt wins outright. If the level grid is missing, the DEM is used
    alone and the receipt says so.
    """

    def __init__(self):
        self.dem = None
        self.level = None
        self.tiles = CutTiles()
        self.sources = {}
        if JERUSALEM_SOURCE.exists():
            data = json.loads(JERUSALEM_SOURCE.read_text(encoding='utf-8-sig'))
            terrain = data['terrain']
            if int(terrain['size']) != GRID_N or float(terrain['step']) != GRID_STEP_AMOT \
                    or float(terrain['origin']) != GRID_ORIGIN_AMOT:
                raise RuntimeError('jerusalem.json terrain grid is not 257 x 50 amot from -6400')
            sha = hashlib.sha256(JERUSALEM_SOURCE.read_bytes()).hexdigest()
            self.dem = HeightGrid(terrain['heights'], 'jerusalem.json terrain.heights', sha, 1.0)
            self.sources['dem'] = dict(file=str(JERUSALEM_SOURCE), sha256=sha, unit='amot (0.5 m), whole numbers',
                                       grid='%d x %d, step %g amot, origin %g amot' % (GRID_N, GRID_N, GRID_STEP_AMOT, GRID_ORIGIN_AMOT),
                                       referenceElevationMetres=data.get('provenance', {}).get('referenceElevationMetres'),
                                       conversion='UE cm = ((x + %.10f) * 50, (z - %.10f) * 50); Z cm = h * 50'
                                                  % (SOURCE_TX_AMOT, -SOURCE_TZ_AMOT))
        if LEVEL_TERRAIN_SOURCE.exists():
            sha = hashlib.sha256(LEVEL_TERRAIN_SOURCE.read_bytes()).hexdigest()
            if sha == LEVEL_TERRAIN_SHA256:
                data = json.loads(LEVEL_TERRAIN_SOURCE.read_text(encoding='utf-8'))
                mesh = [m for m in data['meshes'] if m.get('name') == 'Terrain 0' and m.get('category') == 'Terrain']
                if len(mesh) == 1 and len(mesh[0]['positions']) == GRID_N * GRID_N * 3:
                    positions = mesh[0]['positions']
                    self.level = HeightGrid(positions[1::3], "jerusalem-meshes.json 'Terrain 0'", sha, 0.05)
                    self.sources['level'] = dict(file=str(LEVEL_TERRAIN_SOURCE), sha256=sha,
                                                 role='the grid the 256 level terrain tiles were built from '
                                                      '(terrain-import manifest chain; terrain-cut-manifest sourceSha256)')
            else:
                self.sources['level'] = dict(file=str(LEVEL_TERRAIN_SOURCE), sha256=sha,
                                             error='sha256 differs from the frozen value; not used')
        self.sources['tiles'] = dict(status=self.tiles.status,
                                     tiles=[dict(name=t['name'], file=t['file'], sha256=t['sha256'],
                                                 boundsCm=list(t['bounds']), removedTriangles=t['removedTriangles'])
                                            for t in self.tiles.tiles])

    @property
    def available(self):
        return self.dem is not None or self.level is not None

    def sample(self, x, y):
        """dict(z, source, dem, level, tile, disagreementCm) or None when nothing covers (x, y)."""
        dem = self.dem.height_cm(x, y) if self.dem else None
        level = self.level.height_cm(x, y) if self.level else None
        tile_z, tile_name = self.tiles.height_cm(x, y)
        disagreement = (abs(dem - level) if dem is not None and level is not None else None)
        if tile_z is not None:
            z, source = tile_z, 'tile:' + tile_name
        elif level is not None:
            z, source = level, 'level'
        elif dem is not None:
            z, source = dem, 'dem'
        else:
            return None
        return dict(z=z, source=source, dem=dem, level=level, tile=tile_z, tileName=tile_name,
                    disagreementCm=disagreement,
                    beyondRounding=(disagreement is not None and disagreement > DEM_ROUNDING_CM))


def ground_profile(sq, ground):
    """The profile AMikdashEnclosure bakes: for each of the 601 stations per side, the highest
    and lowest ground under the wall footprint across its thickness (three lines: the
    centreline and both faces of the foundation). Plus the per-side witness statistics."""
    a = sq['cmPerAmah']
    c = corners(sq)
    across = WALL_THICK_AMOT * a * FOUNDATION_WIDTH_FACTOR / 2.0
    outward = [(0.0, -1.0), (1.0, 0.0), (0.0, 1.0), (-1.0, 0.0)]
    high, low = [], []
    sides = []
    source_counts = {}
    for side in range(4):
        start, end = c[side], c[(side + 1) % 4]
        nx, ny = outward[side]
        side_stats = dict(side=side, name=['north', 'east', 'south', 'west'][side],
                          stations=STEPS_PER_SIDE + 1, lowZcm=1e300, highZcm=-1e300,
                          lowAt=None, highAt=None, maxDemLevelDisagreementCm=0.0,
                          stationsBeyondRounding=0, stationsOutsideGrid=0, sources={})
        for k in range(STEPS_PER_SIDE + 1):
            t = k / float(STEPS_PER_SIDE)
            x = start[0] + (end[0] - start[0]) * t
            y = start[1] + (end[1] - start[1]) * t
            values = []
            for offset in (-across, 0.0, across):
                s = ground.sample(x + nx * offset, y + ny * offset)
                if s is None:
                    continue
                values.append(s['z'])
                side_stats['sources'][s['source'].split(':')[0]] = side_stats['sources'].get(s['source'].split(':')[0], 0) + 1
                source_counts[s['source']] = source_counts.get(s['source'], 0) + 1
                if s['disagreementCm'] is not None:
                    side_stats['maxDemLevelDisagreementCm'] = max(side_stats['maxDemLevelDisagreementCm'], s['disagreementCm'])
                    if s['beyondRounding']:
                        side_stats['stationsBeyondRounding'] += 1
            if not values:
                side_stats['stationsOutsideGrid'] += 1
                values = [0.0]
            hi, lo = max(values), min(values)
            high.append(hi)
            low.append(lo)
            if lo < side_stats['lowZcm']:
                side_stats['lowZcm'], side_stats['lowAt'] = lo, [round(x, 1), round(y, 1)]
            if hi > side_stats['highZcm']:
                side_stats['highZcm'], side_stats['highAt'] = hi, [round(x, 1), round(y, 1)]
        side_stats['lowZcm'] = round(side_stats['lowZcm'], 2)
        side_stats['highZcm'] = round(side_stats['highZcm'], 2)
        side_stats['lowMetresAsl'] = round(748.0 + side_stats['lowZcm'] / 100.0, 2)
        side_stats['highMetresAsl'] = round(748.0 + side_stats['highZcm'] / 100.0, 2)
        side_stats['dropMetres'] = round((side_stats['highZcm'] - side_stats['lowZcm']) / 100.0, 2)
        side_stats['maxDemLevelDisagreementCm'] = round(side_stats['maxDemLevelDisagreementCm'], 2)
        sides.append(side_stats)
    return dict(stepsPerSide=STEPS_PER_SIDE, stationsPerSide=STEPS_PER_SIDE + 1,
                stationSpacingCm=sq['sideCm'] / STEPS_PER_SIDE,
                acrossOffsetsCm=[-across, 0.0, across],
                highZcm=[round(v, 3) for v in high], lowZcm=[round(v, 3) for v in low],
                sides=sides, sourceUse=source_counts, groundSources=ground.sources,
                policy=('AUTHORED. A module stands with its plinth on the HIGHEST ground under its footprint '
                        '(so the six-amah section is never buried) and a substructure box fills from the LOWEST '
                        'ground under it, less a one-amah footing, up to the plinth (so no gap shows). Yechezkel '
                        '40:5 gives the section, the book the height; neither says anything about foundations, '
                        'and where the wall drops into the Kidron the substructure is this project\'s invention.'),
                chooserRule=('tile receipt where the station lies in one of the four FutureMountV1 cut tiles; '
                             'otherwise the level grid (jerusalem-meshes.json Terrain 0, the source of the 252 '
                             'other tiles); otherwise jerusalem.json. The DEM/level disagreement is recorded per '
                             'side; beyond %g cm it is the exporter\'s Haram edit, not rounding.' % DEM_ROUNDING_CM))


def _interp(values, steps, side, fraction):
    """Mirror of SampleProfileArray()."""
    f = min(1.0, max(0.0, fraction))
    position = f * steps
    k = int(math.floor(position))
    k = max(0, min(steps - 1, k))
    t = position - k
    base = side * (steps + 1)
    return values[base + k] + (values[base + k + 1] - values[base + k]) * t


def ground_span(profile, side, f0, f1, footing_cm, subsamples=9):
    """Mirror of GroundSpan()."""
    lo, hi = min(f0, f1), max(f0, f1)
    high = -1e300
    low = 1e300
    for i in range(subsamples):
        f = lo + (hi - lo) * i / float(subsamples - 1)
        high = max(high, _interp(profile['highZcm'], profile['stepsPerSide'], side, f))
        low = min(low, _interp(profile['lowZcm'], profile['stepsPerSide'], side, f))
    return dict(baseZ=high, foundationBottomZ=low - footing_cm, depth=high - (low - footing_cm),
                groundHigh=high, groundLow=low)


def instance_groundings(sq, profile):
    """Every wall, gate and corner instance grounded exactly as the actor will ground it, so
    the receipt carries the numbers the level will show."""
    a = sq['cmPerAmah']
    footing = FOOTING_AMOT * a
    per_side, seg, rows = wall_segments(sq)
    side_cm = sq['sideCm']
    names = ['north', 'east', 'south', 'west']
    walls = []
    per_side_stats = []
    for side in range(4):
        bases = []
        depths = []
        steps_between = []
        previous = None
        for row in rows:
            if row['side'] != side or not row['kept']:
                continue
            g = ground_span(profile, side, row['lo'] / side_cm, row['hi'] / side_cm, footing)
            walls.append(dict(side=side, step=row['step'], baseZ=round(g['baseZ'], 2),
                              foundationBottomZ=round(g['foundationBottomZ'], 2), depth=round(g['depth'], 2)))
            bases.append(g['baseZ'])
            depths.append(g['depth'])
            if previous is not None and row['step'] == previous[0] + 1:
                steps_between.append(abs(g['baseZ'] - previous[1]))
            previous = (row['step'], g['baseZ'])
        deepest = max(range(len(depths)), key=lambda i: depths[i])
        per_side_stats.append(dict(
            side=side, name=names[side], wallInstances=len(bases),
            baseZminCm=round(min(bases), 2), baseZmaxCm=round(max(bases), 2),
            baseZminMetresAsl=round(748.0 + min(bases) / 100.0, 2),
            baseZmaxMetresAsl=round(748.0 + max(bases) / 100.0, 2),
            foundationDepthMaxCm=round(max(depths), 2), foundationDepthMeanCm=round(sum(depths) / len(depths), 2),
            deepestFoundationAtStep=[w['step'] for w in walls if w['side'] == side][deepest],
            largestStepBetweenNeighbouringPlinthsCm=round(max(steps_between) if steps_between else 0.0, 2)))
    gate_rows = []
    gate_half = (GATE_OPENING_W_AMOT + 2.0 * GATE_PIER_W_AMOT) * a * 1.04 / 2.0
    for gate in gates(sq):
        f = gate['fraction']
        g = ground_span(profile, gate['side'], f - gate_half / side_cm, f + gate_half / side_cm, footing)
        gate_rows.append(dict(id=gate['id'], side=gate['side'], positionCm=gate['positionCm'],
                              baseZ=round(g['baseZ'], 2), foundationBottomZ=round(g['foundationBottomZ'], 2),
                              depth=round(g['depth'], 2), thresholdMetresAsl=round(748.0 + g['baseZ'] / 100.0, 2)))
    corner_rows = []
    corner_half = WALL_THICK_AMOT * a * 1.6 * 1.16 / 2.0
    for index in range(4):
        # the corner is station 0 of side `index` and station 1.0 of the side before it
        g1 = ground_span(profile, index, 0.0, corner_half / side_cm, footing)
        g0 = ground_span(profile, (index + 3) % 4, 1.0 - corner_half / side_cm, 1.0, footing)
        base = max(g0['baseZ'], g1['baseZ'])
        bottom = min(g0['foundationBottomZ'], g1['foundationBottomZ'])
        corner_rows.append(dict(corner=['NW', 'NE', 'SE', 'SW'][index], positionCm=list(corners(sq)[index]),
                                baseZ=round(base, 2), foundationBottomZ=round(bottom, 2), depth=round(base - bottom, 2)))
    return dict(footingCm=footing, segmentsPerSide=per_side, segmentLengthCm=seg,
                perSide=per_side_stats, gates=gate_rows, corners=corner_rows, wallInstances=walls)


# =====================================================================================
# 7. Which modern buildings the YECHEZKEL state hides - exact, per actor
# =====================================================================================
def polygon_centroid_ue(points):
    """Area centroid of an OSM ring in level cm (closing duplicate dropped). Degenerate rings
    fall back to the vertex mean."""
    ring = points[:-1] if len(points) > 1 and points[0] == points[-1] else points
    xy = [source_to_ue(p[0], p[1]) for p in ring]
    n = len(xy)
    area2 = 0.0
    cx = cy = 0.0
    for i in range(n):
        j = (i + 1) % n
        cr = xy[i][0] * xy[j][1] - xy[j][0] * xy[i][1]
        area2 += cr
        cx += (xy[i][0] + xy[j][0]) * cr
        cy += (xy[i][1] + xy[j][1]) * cr
    if abs(area2) > 1e-9:
        return cx / (3.0 * area2), cy / (3.0 * area2), xy
    return sum(p[0] for p in xy) / n, sum(p[1] for p in xy) / n, xy


def inside(sq, x, y):
    return sq['west'] <= x <= sq['east'] and sq['north'] <= y <= sq['south']


def classify_box(sq, aabb):
    x0, y0, x1, y1 = aabb
    if sq['west'] <= x0 and x1 <= sq['east'] and sq['north'] <= y0 and y1 <= sq['south']:
        return 'inside'
    if x1 <= sq['west'] or x0 >= sq['east'] or y1 <= sq['north'] or y0 >= sq['south']:
        return 'outside'
    return 'straddling'


classify_cell = classify_box   # kept under its old name for the preview


def cell_bounds(token_x, token_y):
    """`Grid_N010_N002` -> the 100 m cell's world AABB in Unreal cm."""
    def value(token):
        return -int(token[1:]) if token[0] == 'N' else int(token[1:])
    ix, iy = value(token_x), value(token_y)
    return (ix * CELL_CM, iy * CELL_CM, (ix + 1) * CELL_CM, (iy + 1) * CELL_CM)


def osm_buildings():
    """Every `kind == building` feature as (osmId, centroid, aabb) in level cm, or None."""
    if not JERUSALEM_SOURCE.exists():
        return None
    data = json.loads(JERUSALEM_SOURCE.read_text(encoding='utf-8-sig'))
    out = {}
    for feature in data.get('features', []):
        if feature.get('kind') != 'building':
            continue
        points = feature.get('points') or []
        if len(points) < 3:
            continue
        cx, cy, xy = polygon_centroid_ue(points)
        aabb = (min(p[0] for p in xy), min(p[1] for p in xy), max(p[0] for p in xy), max(p[1] for p in xy))
        out[int(feature.get('id', 0))] = dict(centroid=(cx, cy), aabb=aabb)
    return out


def exact_building_coverage(sq, buildings=None):
    """Per-building containment from the OSM source polygons, by AREA centroid. This is the
    count that answers "how many modern buildings does the precinct cover"; footprints the
    wall line cuts are reported separately and never folded in."""
    buildings = buildings if buildings is not None else osm_buildings()
    if buildings is None:
        return None
    facade_ids = set()
    if FACADES_MANIFEST.exists():
        facades = json.loads(FACADES_MANIFEST.read_text(encoding='utf-8-sig'))
        for batch in facades.get('batches', []):
            entry = batch.get('facades')
            if not entry:
                continue
            for building in entry.get('perBuilding', []):
                facade_ids.add(int(building.get('osmId', 0)))
    inside_ids, straddling, outside, facade_inside = [], 0, 0, 0
    for osm_id, b in buildings.items():
        if inside(sq, *b['centroid']):
            inside_ids.append(osm_id)
            if osm_id in facade_ids:
                facade_inside += 1
        elif classify_box(sq, b['aabb']) == 'straddling':
            straddling += 1
        else:
            outside += 1
    inside_ids.sort()
    fingerprint = 1469598103934665603
    for value in inside_ids:
        for byte in range(8):
            fingerprint ^= (value >> (byte * 8)) & 0xFF
            fingerprint = (fingerprint * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return dict(
        source=str(JERUSALEM_SOURCE),
        rule='area centroid inside (ESelectionRule::CentroidInside); points are AMOT and carry the baked alignment',
        population=('EVERY OSM building feature in the exported city, not only the walled Old City. The '
                    'precinct also covers ground east and south of those walls.'),
        buildingsTotal=len(buildings), buildingsInside=len(inside_ids),
        footprintsTheWallLineCutsButCentroidOutside=straddling, buildingsOutside=outside,
        authoredFacadeBuildingsInside=facade_inside, authoredFacadeBuildingsTotal=len(facade_ids),
        insideIdFingerprintFnv1a='%016x' % fingerprint)


def hide_set(sq, policy='hide_if_any_inside', buildings=None):
    """The exact set of ACTORS the YECHEZKEL state hides, by label, with every decision recorded.

    Three actor families carry the modern city, all batched one actor per 100 m cell:
      SM_JerusalemBuildings_Grid_*  - the 1499 imported OSM extrusions. Membership comes from
                                      the frozen buildings-manifest.json (11,400 connected
                                      components, each with its source box and assigned cell).
      RELEASE_OldCityFacades_Grid_* - the authored facade batches; facades-manifest.json lists
                                      the OSM ids each cell decorates.
      RELEASE_OldCityInfill_Grid_*  - authored infill with no OSM identity; follows its cell.

    A cell the wall line CUTS needs a decision, because a batched mesh cannot be half hidden:
      hide_if_any_inside       hide the cell if ANY of its buildings has its centroid inside.
                               Nothing modern stands inside the precinct; the price is that
                               buildings up to ~100 m OUTSIDE the wall in the same cell vanish
                               too (counted below as `collateral`). RECOMMENDED for the default
                               YECHEZKEL view, because a modern block standing inside the holy
                               precinct contradicts the view outright while a bare strip just
                               outside the wall does not.
      hide_if_majority_inside  hide the cell if at least half its buildings are inside.
      keep_straddling          hide only cells wholly inside the wall line.
    `split` - re-batching the cut cells at the wall line, or a world-position opacity mask on
    the context materials - is the correct long-term fix and is recorded as a recommendation,
    not done here (it is a native re-import or a material edit).
    """
    buildings = buildings if buildings is not None else osm_buildings()
    result = dict(policy=policy, rule='component/building centroid inside the outer wall faces',
                  sets=[], labels=[], counts={}, straddlingCells=[], collateral={})

    def decide(n_inside, n_total):
        if n_inside == 0:
            return False
        if policy == 'hide_if_any_inside':
            return True
        if policy == 'hide_if_majority_inside':
            return n_inside * 2 >= n_total
        if policy == 'keep_straddling':
            return n_inside == n_total
        raise ValueError(policy)

    # -- the imported OSM extrusions, from the frozen partition --------------------------
    if BUILDINGS_FROZEN_MANIFEST.exists():
        frozen = json.loads(BUILDINGS_FROZEN_MANIFEST.read_text(encoding='utf-8-sig'))
        if frozen.get('fbxSha256') != BUILDINGS_FROZEN_FBX_SHA256:
            raise RuntimeError('buildings-manifest.json is not the reviewed FBX revision')
        cells = {}
        for component in frozen['components']:
            b = component['sourceBoundsAmos']
            x0, y0 = source_to_ue(b['min'][0], b['min'][2])
            x1, y1 = source_to_ue(b['max'][0], b['max'][2])
            cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            cell = cells.setdefault(component['assignedGroup'],
                                    dict(inside=0, straddling=0, outside=0, ids=[], box=[1e300, 1e300, -1e300, -1e300]))
            cell['box'] = [min(cell['box'][0], x0), min(cell['box'][1], y0), max(cell['box'][2], x1), max(cell['box'][3], y1)]
            if inside(sq, cx, cy):
                cell['inside'] += 1
                cell['ids'].append(component['componentId'])
            elif classify_box(sq, (x0, y0, x1, y1)) == 'straddling':
                cell['straddling'] += 1
            else:
                cell['outside'] += 1
        mesh_groups = {m['group'] for m in frozen['meshes']}
        hidden, kept_with_inside, collateral_components = [], [], 0
        cells_wholly_inside = cells_cut = 0
        for group, cell in sorted(cells.items()):
            if group not in mesh_groups:
                continue
            total = cell['inside'] + cell['straddling'] + cell['outside']
            # 76 `Large_NNNNN` groups are single components spanning more than 100 m, each its
            # own mesh; they have no cell box, so their own box stands in for it.
            grid = re.match(r'^Grid_([NP]\d{3})_([NP]\d{3})$', group)
            cell_box = cell_bounds(grid.group(1), grid.group(2)) if grid else tuple(cell['box'])
            verdict = classify_box(sq, cell_box)
            if verdict == 'inside':
                cells_wholly_inside += 1
            elif verdict == 'straddling':
                cells_cut += 1
            hide = decide(cell['inside'], total)
            label = 'SM_JerusalemBuildings_' + group
            if hide:
                hidden.append(label)
                if verdict == 'straddling':
                    collateral_components += cell['outside'] + cell['straddling']
                    result['straddlingCells'].append(dict(label=label, componentsInside=cell['inside'],
                                                          componentsWallCuts=cell['straddling'],
                                                          componentsOutside=cell['outside'], decision='hide'))
            elif cell['inside'] > 0:
                kept_with_inside.append(dict(label=label, componentsInside=cell['inside'], componentsTotal=total))
                result['straddlingCells'].append(dict(label=label, componentsInside=cell['inside'],
                                                      componentsWallCuts=cell['straddling'],
                                                      componentsOutside=cell['outside'], decision='keep'))
        result['sets'].append(dict(
            set='JerusalemContext/Buildings (imported OSM extrusions)', actorLabelPrefix='SM_JerusalemBuildings_',
            membership='buildings-manifest.json components -> assignedGroup (fbx %s)' % BUILDINGS_FROZEN_FBX_SHA256[:12],
            cellActorsTotal=len(mesh_groups), cellActorsHidden=len(hidden),
            cellActorsWhollyInsideWallLine=cells_wholly_inside, cellActorsTheWallLineCuts=cells_cut,
            componentsInsideCityWide=sum(c['inside'] for c in cells.values()),
            componentsOutsideButHiddenWithTheirCell=collateral_components,
            cellsKeptDespiteInsideComponents=kept_with_inside))
        result['labels'].extend(hidden)
        result['collateral']['osmComponentsOutsideTheWallButHidden'] = collateral_components
    else:
        result['sets'].append(dict(set='JerusalemContext/Buildings', error='frozen buildings-manifest.json absent'))

    # -- the authored Old City facades and infill ----------------------------------------
    if FACADES_MANIFEST.exists() and buildings is not None:
        data = json.loads(FACADES_MANIFEST.read_text(encoding='utf-8-sig'))
        f_hidden, i_hidden, f_total, i_total = [], [], 0, 0
        f_collateral = 0
        for batch in data.get('batches', []):
            cell_name = batch['name']
            facades = batch.get('facades')
            infill = batch.get('infill')
            ids = [int(b['osmId']) for b in (facades or {}).get('perBuilding', [])]
            n_inside = sum(1 for osm_id in ids if osm_id in buildings and inside(sq, *buildings[osm_id]['centroid']))
            total = len(ids)
            if facades:
                f_total += 1
            if infill:
                i_total += 1
            if total == 0:
                # infill-only cell: decide on the cell box
                aabb = infill['canonicalBoundsCm'] if infill else None
                hide = bool(aabb) and inside(sq, (aabb['min'][0] + aabb['max'][0]) / 2.0, (aabb['min'][1] + aabb['max'][1]) / 2.0)
            else:
                hide = decide(n_inside, total)
            if hide:
                if facades:
                    f_hidden.append('RELEASE_OldCityFacades_' + cell_name)
                    f_collateral += total - n_inside
                if infill:
                    i_hidden.append('RELEASE_OldCityInfill_' + cell_name)
                if 0 < n_inside < total:
                    result['straddlingCells'].append(dict(label='RELEASE_OldCityFacades_' + cell_name,
                                                          buildingsInside=n_inside, buildingsOutside=total - n_inside,
                                                          infillFollows=bool(infill), decision='hide'))
            elif n_inside > 0:
                result['straddlingCells'].append(dict(label='RELEASE_OldCityFacades_' + cell_name,
                                                      buildingsInside=n_inside, buildingsOutside=total - n_inside,
                                                      infillFollows=bool(infill), decision='keep'))
        result['sets'].append(dict(set='OldCityFacadesV1/facades', actorLabelPrefix='RELEASE_OldCityFacades_',
                                   membership='facades-manifest.json batches[].facades.perBuilding[].osmId',
                                   cellActorsTotal=f_total, cellActorsHidden=len(f_hidden),
                                   facadeBuildingsOutsideButHiddenWithTheirCell=f_collateral))
        result['sets'].append(dict(set='OldCityFacadesV1/infill', actorLabelPrefix='RELEASE_OldCityInfill_',
                                   membership='authored infill has no OSM identity; follows its cell\'s facade decision',
                                   cellActorsTotal=i_total, cellActorsHidden=len(i_hidden)))
        result['labels'].extend(f_hidden)
        result['labels'].extend(i_hidden)
        result['collateral']['facadeBuildingsOutsideTheWallButHidden'] = f_collateral
    else:
        result['sets'].append(dict(set='OldCityFacadesV1', error='facades-manifest.json or OSM source absent'))

    result['labels'] = sorted(set(result['labels']))
    fingerprint = 1469598103934665603
    for label in result['labels']:
        for byte in label.encode('utf-8'):
            fingerprint ^= byte
            fingerprint = (fingerprint * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    result['labelFingerprintFnv1a'] = '%016x' % fingerprint
    result['counts'] = dict(
        totalActorsHidden=len(result['labels']),
        SM_JerusalemBuildings_=sum(1 for l in result['labels'] if l.startswith('SM_JerusalemBuildings_')),
        RELEASE_OldCityFacades_=sum(1 for l in result['labels'] if l.startswith('RELEASE_OldCityFacades_')),
        RELEASE_OldCityInfill_=sum(1 for l in result['labels'] if l.startswith('RELEASE_OldCityInfill_')),
        straddlingCellsHidden=sum(1 for c in result['straddlingCells'] if c['decision'] == 'hide'),
        straddlingCellsKept=sum(1 for c in result['straddlingCells'] if c['decision'] == 'keep'))
    result['recommendation'] = (
        'hide_if_any_inside for the default YECHEZKEL view (nothing modern stands inside the wall). The '
        'collateral - buildings just outside the wall hidden with their cell - is listed above per cell. '
        'To recover it, SPLIT the cut cells at the wall line (re-batch those cells as inside/outside meshes; '
        'a native re-import) or mask the context materials by world position. Never delete.')
    return result


def modern_city_coverage(sq, buildings=None):
    """The exact per-building coverage plus the per-actor hide set under the three policies."""
    buildings = buildings if buildings is not None else osm_buildings()
    result = dict(exact=exact_building_coverage(sq, buildings),
                  hideSets={policy: hide_set(sq, policy, buildings)['counts']
                            for policy in ('hide_if_any_inside', 'hide_if_majority_inside', 'keep_straddling')})
    result['hideSet'] = hide_set(sq, 'hide_if_any_inside', buildings)
    return result


# =====================================================================================
# 8. Preview PNG - a plan of the square over the city
# =====================================================================================
def png(path, rgb, width, height):
    def chunk(kind, data):
        return (struct.pack('>I', len(data)) + kind + data
                + struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF))
    raw = b''.join(b'\x00' + bytes(rgb[y * width * 3:(y + 1) * width * 3]) for y in range(height))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'
                     + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(raw, 9))
                     + chunk(b'IEND', b''))


def write_preview(path, sq, coverage_cells):
    """Plan view: the precinct, the 500-amah Middot ring, the court platform and every context
    cell, so the reviewer can see which ground is covered rather than read that it is."""
    width = height = 900
    margin = 40
    lo_x, hi_x = sq['west'] - 40000.0, sq['east'] + 40000.0
    lo_y, hi_y = sq['north'] - 40000.0, sq['south'] + 40000.0
    span = max(hi_x - lo_x, hi_y - lo_y)
    pixels = bytearray([18, 18, 22] * width * height)

    def to_px(x, y):
        return (int(margin + (x - lo_x) / span * (width - 2 * margin)),
                int(margin + (y - lo_y) / span * (height - 2 * margin)))

    def dot(px, py, colour):
        if 0 <= px < width and 0 <= py < height:
            offset = (py * width + px) * 3
            pixels[offset:offset + 3] = bytes(colour)

    def rect(x0, y0, x1, y1, colour, fill=None):
        a, b = to_px(x0, y0)
        c, d = to_px(x1, y1)
        if fill is not None:
            for py in range(max(0, b), min(height, d)):
                for px in range(max(0, a), min(width, c)):
                    offset = (py * width + px) * 3
                    old = pixels[offset:offset + 3]
                    pixels[offset:offset + 3] = bytes(
                        [(old[i] + fill[i]) // 2 for i in range(3)])
        for px in range(max(0, a), min(width, c)):
            dot(px, b, colour)
            dot(px, d - 1, colour)
        for py in range(max(0, b), min(height, d)):
            dot(a, py, colour)
            dot(c - 1, py, colour)

    for cell in coverage_cells:
        x0, y0, x1, y1 = cell['aabb']
        colour = {'inside': (120, 70, 60), 'straddling': (120, 110, 50),
                  'outside': (52, 56, 62)}[cell['verdict']]
        rect(x0, y0, x1, y1, colour, fill=colour)

    half = sq['courtHalfCm']
    rect(-half, -half, half, half, (250, 230, 160))
    half500 = K['MiddotHarHaBayitAmot'] * sq['cmPerAmah'] / 2.0
    rect(-half500, -half500, half500, half500, (150, 200, 255))
    rect(sq['west'], sq['north'], sq['east'], sq['south'], (255, 205, 120))
    for gate in gates(sq):
        px, py = to_px(gate['positionCm'][0], gate['positionCm'][1])
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx * dx + dy * dy <= 9:
                    dot(px + dx, py + dy, (255, 120, 90))
    png(path, pixels, width, height)


# =====================================================================================
# 9. Export
# =====================================================================================
def target_receipt(name, ground, buildings):
    """Everything the release script needs for one map, computed from the header rule."""
    sq = target_square(name)
    t = TARGETS[name]
    profile = ground_profile(sq, ground) if ground.available else None
    groundings = instance_groundings(sq, profile) if profile else None
    coverage = modern_city_coverage(sq, buildings)
    plan = wall_plan(sq)
    return dict(
        target=name, map=t['map'], note=t['note'],
        cmPerAmah=t['cmPerAmah'], courtPlatformHalfExtentCm=t['courtHalfCm'],
        moduleScale=t['cmPerAmah'] / A,
        generatorSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        enclosureMathSha256=hashlib.sha256(HEADER.read_bytes()).hexdigest(),
        square=dict(sideAmot=SIDE_AMOT, sideReeds=SIDE_AMOT / K['AmotPerReed'], sideCm=sq['sideCm'],
                    sideMetresAtThisAmah=sq['sideCm'] / 100.0,
                    outerFacesCm=dict(xWest=sq['west'], xEast=sq['east'], yNorth=sq['north'], ySouth=sq['south']),
                    centreCm=sq['centre']),
        clearancesAmot=clearances(sq),
        gates=gates(sq),
        wallPlan=plan,
        wallSectionAmot=dict(thickness=WALL_THICK_AMOT, height=WALL_HEIGHT_AMOT),
        groundProfile=profile,
        groundings=groundings,
        modernCity=coverage,
        defaultState='yechezkel',
        stateCycle='YECHEZKEL -> MODERN -> OVERLAY -> YECHEZKEL (CyclePrecinctState); OVERLAY and MODERN stay reachable',
        limitations=[
            'The ground profile, the substructure and the gate positions along each wall are AUTHORED; only the '
            'square, the wall section, the gate count and the 10 x 50 opening are sourced.',
            'The hide set is exact per ACTOR; a 100 m cell the wall line cuts is hidden whole under the recorded '
            'policy, so some buildings just outside the wall vanish with it (collateral listed). Split or mask to fix.',
            'Nothing is deleted. Hidden means SetActorHiddenInGame at run time; MODERN restores every actor.',
        ])


def export():
    OUT.mkdir(parents=True, exist_ok=True)
    meshes = (OUT / 'EnclosureV2')
    meshes.mkdir(parents=True, exist_ok=True)
    sq = target_square('Main50')

    records, readbacks = [], []
    for name, build, role, note in MODULES:
        record = write_obj(name, build(), meshes / (name + '.obj'))
        record['materialRole'] = role
        record['note'] = note
        records.append(record)
        readbacks.append(readback(meshes / (name + '.obj'), record))

    by_name = {r['name']: r for r in records}
    _assert_matches_module_budget(by_name)
    plan = wall_plan(sq)
    triangles = dict(
        wall=plan['wallInstances'] * by_name['SM_EnclosureV2_WallSegment']['triangles'],
        gate=plan['gateInstances'] * by_name['SM_EnclosureV2_Gate']['triangles'],
        corner=plan['cornerInstances'] * by_name['SM_EnclosureV2_Corner']['triangles'],
        overlay=plan['overlayInstances'] * by_name['SM_EnclosureV2_OverlaySlab']['triangles'],
        foundation=plan['foundationInstances'] * by_name['SM_EnclosureV2_Foundation']['triangles'])
    triangles['total'] = sum(triangles.values())
    instances = (plan['wallInstances'] + plan['gateInstances'] + plan['cornerInstances']
                 + plan['overlayInstances'] + plan['foundationInstances'])

    ground = Ground()
    buildings = osm_buildings()
    receipts = {}
    for name in TARGETS:
        receipt = target_receipt(name, ground, buildings)
        (OUT / ('precinct-%s.json' % name)).write_text(json.dumps(receipt, indent=1, ensure_ascii=False),
                                                        encoding='utf-8')
        receipts[name] = receipt

    coverage_cells = []
    if FACADES_MANIFEST.exists():
        data = json.loads(FACADES_MANIFEST.read_text(encoding='utf-8-sig'))
        for batch in data.get('batches', []):
            entry = batch.get('facades') or batch.get('infill')
            if not entry:
                continue
            bounds = entry['canonicalBoundsCm']
            aabb = (bounds['min'][0], bounds['min'][1], bounds['max'][0], bounds['max'][1])
            coverage_cells.append(dict(aabb=aabb, verdict=classify_cell(sq, aabb)))
    write_preview(OUT / 'enclosure-plan.png', sq, coverage_cells)

    main = receipts['Main50']
    manifest = dict(
        status='OFFLINE_SOURCE_EXPORTED_NATIVE_PENDING',
        namespace=DEST,
        meshFolder=DEST + '/Meshes',
        generatorSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        enclosureMathSha256=hashlib.sha256(HEADER.read_bytes()).hexdigest(),
        cmPerAmah=A,
        defaultState='yechezkel',
        coordinateConvention=('UE cm: X east, Y south, Z up; measured court centre at the '
                              'origin; module origin at the centre of its footprint on the '
                              'ground with local +X along the wall and +Y outward; OBJ files '
                              'carry Y negated and reversed winding (legacy adapter)'),
        objConvention=('per-face vertices; file Y = -canonical Y and winding reversed; the '
                       'importer reflects Y back, so imported bounds must equal '
                       'canonicalBoundsCm and imported signed volumes must be positive. One '
                       '`o` object and no `g` groups, so one material slot per mesh.'),
        square=dict(sideAmot=SIDE_AMOT, sideReeds=SIDE_AMOT / K['AmotPerReed'], sideCm=sq['sideCm'],
                    outerFacesCm=dict(xWest=sq['west'], xEast=sq['east'],
                                      yNorth=sq['north'], ySouth=sq['south']),
                    centreCm=sq['centre'],
                    matchesEnclosureV1=_matches_existing_design(sq)),
        targets={name: dict(map=TARGETS[name]['map'], cmPerAmah=TARGETS[name]['cmPerAmah'],
                            courtPlatformHalfExtentCm=TARGETS[name]['courtHalfCm'],
                            sideCm=receipts[name]['square']['sideCm'],
                            outerFacesCm=receipts[name]['square']['outerFacesCm'],
                            receipt='precinct-%s.json' % name,
                            actorsHidden=receipts[name]['modernCity']['hideSet']['counts'],
                            osmBuildingsInsideByCentroid=(receipts[name]['modernCity']['exact'] or {}).get('buildingsInside'),
                            groundPerSide=[dict(side=s['name'], baseZminCm=s['baseZminCm'], baseZmaxCm=s['baseZmaxCm'],
                                                foundationDepthMaxCm=s['foundationDepthMaxCm'])
                                           for s in (receipts[name]['groundings'] or {}).get('perSide', [])])
                 for name in TARGETS},
        clearancesAmot=clearances(sq),
        clearanceOrder=_clearance_order_note(sq),
        gates=gates(sq),
        gateBlockAmot=dict(openingWidth=GATE_OPENING_W_AMOT, openingHeight=GATE_OPENING_H_AMOT,
                           pierWidth=GATE_PIER_W_AMOT, totalHeight=GATE_TOTAL_H_AMOT, depth=GATE_DEPTH_AMOT),
        wallSectionAmot=dict(thickness=WALL_THICK_AMOT, height=WALL_HEIGHT_AMOT),
        foundation=dict(footingAmot=FOOTING_AMOT, widthFactor=FOUNDATION_WIDTH_FACTOR, unitHeightCm=FOUNDATION_UNIT_H_CM,
                        policy=(main['groundProfile'] or {}).get('policy', 'ground sources absent')),
        instancing=dict(
            componentType='HierarchicalInstancedStaticMeshComponent',
            components=5, plan=plan, instances=instances, triangles=triangles,
            budgetNote=('RTX 2070, 8 GB, 1080p. %d instances across five HISM components and '
                        '%d triangles for the whole 1.44 km ring including the terrain-following '
                        'substructure, against 3,416,580 triangles in the 190-actor Old City '
                        'facade set the YECHEZKEL state hides - about %.1f%% of it. Per-instance '
                        'frustum culling means the visible cost is a small fraction of that again.'
                        % (instances, triangles['total'], 100.0 * triangles['total'] / 3416580.0))),
        modernCityCoverage=dict(exact=main['modernCity']['exact'],
                                hideSetCountsByPolicy=main['modernCity']['hideSets'],
                                recommendedPolicy='hide_if_any_inside',
                                note='Per-actor hide sets and per-cell decisions are in precinct-<Target>.json modernCity.hideSet'),
        groundProfileSummary=dict(sides=(main['groundProfile'] or {}).get('sides'),
                                  sourceUse=(main['groundProfile'] or {}).get('sourceUse'),
                                  groundSources=(main['groundProfile'] or {}).get('groundSources')),
        meshes=records,
        readback=readbacks,
        preview='enclosure-plan.png',
        relationToEnclosureV1=(
            'SourceAssets/FutureMountV1/EnclosureV1 (Scripts/create_mount_enclosure.py) exports '
            'the SAME square as 52 chunk meshes stepped to the current-city DEM and is NOT '
            'modified by this generator. EnclosureV2 is the instanced, toggleable form; the two '
            'share the square through EnclosureMath.h and are asserted equal in `square.'
            'matchesEnclosureV1` above.'),
        limitations=[
            'The wall follows a BAKED ground profile (this generator, from the OSM grid, the level grid and '
            'the FutureMountV1 tile receipts), not a run-time trace. If the terrain tiles are edited again '
            'the profile must be regenerated and the actor re-placed; the receipt carries the source hashes.',
            'Foundations/substructure are AUTHORED. The sources give the wall a section and a height and say '
            'nothing about what carries it down the Kidron slope.',
            'Gate along-wall positions are the project assumption, not the book. Only the count per side and '
            'the 10 x 50 amah opening are sourced. The east gate is on the Temple east-west axis (world Y 0).',
            'The hide set is exact per ACTOR (100 m cells). Cells the wall line cuts are hidden whole under the '
            'recorded policy; the collateral is listed per cell. Split or mask to recover it. Never delete.',
            'Wall face articulation, corner blocks and gate profiles are AUTHORED. The book gives the wall a '
            'section and the gates an opening, and no elevation.',
        ])
    (OUT / 'geometry-manifest.json').write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False), encoding='utf-8')
    return manifest


def _assert_matches_module_budget(by_name):
    """The header's FModuleBudget must equal what was just written, or the C++ test is proving
    a budget nothing generates. Parsed rather than restated, same as the constants."""
    text = HEADER.read_text(encoding='utf-8')
    wanted = {'WallSegmentTriangles': 'SM_EnclosureV2_WallSegment',
              'GateTriangles': 'SM_EnclosureV2_Gate',
              'CornerTriangles': 'SM_EnclosureV2_Corner',
              'OverlayQuadTriangles': 'SM_EnclosureV2_OverlaySlab',
              'FoundationTriangles': 'SM_EnclosureV2_Foundation'}
    for field, mesh in wanted.items():
        match = re.search(r'int\s+%s\s*=\s*(\d+)\s*;' % field, text)
        if not match:
            raise RuntimeError('EnclosureMath.h FModuleBudget no longer declares ' + field)
        declared = int(match.group(1))
        actual = by_name[mesh]['triangles']
        if declared != actual:
            raise RuntimeError(
                'FModuleBudget::%s is %d but %s generates %d triangles. Update the header (and '
                'the totals asserted in EnclosureMathTest.cpp) rather than the manifest.'
                % (field, declared, mesh, actual))


def _matches_existing_design(sq):
    """Cross-check against the already-shipped EnclosureV1 design, if it is present."""
    if not EXISTING_DESIGN.exists():
        return 'enclosure-design.json absent'
    data = json.loads(EXISTING_DESIGN.read_text(encoding='utf-8-sig'))
    faces = data.get('enclosure', {}).get('outerFacesCm', {})
    worst = max(abs(faces.get('xWest', 0.0) - sq['west']), abs(faces.get('xEast', 0.0) - sq['east']),
                abs(faces.get('yNorth', 0.0) - sq['north']), abs(faces.get('ySouth', 0.0) - sq['south']))
    if worst > 1e-6:
        raise RuntimeError('EnclosureV2 square differs from EnclosureV1 by %g cm' % worst)
    return 'identical to 1e-6 cm on all four outer faces'


def _clearance_order_note(sq):
    c = clearances(sq)
    order = sorted(('west', 'north', 'east', 'south'), key=lambda k: -c[k])
    return dict(
        measured=order,
        middotOrder=['south', 'east', 'north', 'west'],
        holds=order == ['south', 'east', 'north', 'west'],
        marginAmot=c['south'] - c['east'],
        note=('Mishkenei Elyon 196 ch.1 m.1, quoted in full by the book, states the Middot 2:1 '
              'order for the 3000-amah Mount: largest south, then east, then north, least west. '
              'It cannot hold on this project\'s measured court envelope, which is SQUARE '
              '(324 x 324 amot): with the two stated clearances west 500 and north 501, the '
              'remainders satisfy south - east = west - north = -1 amah identically. The book\'s '
              'own fig. 2\'2 envelope is about 351 x 346 - wider than deep - which is why its '
              'labelled remainders (2149 east, 2153 south) do satisfy the order. The departure '
              'here is one amah, 50 cm on a 150,000 cm side. NOTE: '
              'SourceAssets/FutureMountV1/EnclosureV1/enclosure-design.json currently states '
              '"Order south > east > north > west preserved" while carrying east 2176 and south '
              '2175; that sentence is wrong and this field is the correction.'))


# =====================================================================================
# 10. The standalone C++ test
# =====================================================================================
def run_tests():
    """Compile and run Tests/EnclosureMathTest.cpp with cl /W4 /O2 and keep its JSON snapshot.

    Driven through a batch file rather than `cmd /c "call ... && cl ..."`: the vcvars path
    contains spaces and parentheses and cmd mangles it. Same recipe as scripts/verify.py.
    """
    if not VCVARS.exists():
        raise RuntimeError('vcvars64 not found at %s' % VCVARS)
    OUT.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.gettempdir()) / 'mikdash-enclosure'
    work.mkdir(parents=True, exist_ok=True)
    exe = work / 'EnclosureMathTest.exe'
    bat = work / 'build_enclosure_test.bat'
    include = HEADER.parent
    bat.write_text(
        '@echo off\r\n'
        'call "%s" >nul\r\n' % VCVARS +
        'cd /d "%s"\r\n' % work +
        'cl /nologo /std:c++17 /EHsc /W4 /O2 /I"%s" "%s" /Fe:"%s" /link /SUBSYSTEM:CONSOLE\r\n'
        % (include, TEST_SOURCE, exe), encoding='ascii')
    build = subprocess.run(['cmd', '/c', str(bat)], capture_output=True, text=True, cwd=str(work))
    if build.returncode != 0:
        tail = (build.stdout or '') + (build.stderr or '')
        raise RuntimeError('EnclosureMathTest did not compile:\n' + tail[-2000:])
    snapshot = OUT / 'tests.json'
    run = subprocess.run([str(exe), str(snapshot)], capture_output=True, text=True, timeout=300)
    sys.stdout.write(run.stdout or '')
    if run.returncode != 0:
        sys.stderr.write(run.stderr or '')
        raise RuntimeError('EnclosureMathTest FAILED (exit %d)' % run.returncode)
    return json.loads(snapshot.read_text(encoding='utf-8'))


# =====================================================================================
# 11. Report
# =====================================================================================
def report():
    ground = Ground()
    buildings = osm_buildings()
    for name in TARGETS:
        sq = target_square(name)
        print('== %s  (%s)' % (name, TARGETS[name]['map']))
        print('precinct: %g amot (%g reeds) a side = %g Unreal cm at %g cm/amah = %.0f m'
              % (SIDE_AMOT, SIDE_AMOT / K['AmotPerReed'], sq['sideCm'], sq['cmPerAmah'], sq['sideCm'] / 100.0))
        print('outer faces cm: west %g east %g north %g south %g; centre (%g, %g)'
              % (sq['west'], sq['east'], sq['north'], sq['south'], sq['centre'][0], sq['centre'][1]))
        c = clearances(sq)
        print('clearances amot: west %g north %g east %g south %g (Middot order holds: %s)'
              % (c['west'], c['north'], c['east'], c['south'], _clearance_order_note(sq)['holds']))
        plan = wall_plan(sq)
        print('wall plan: %d modules/side of %g cm, %d kept, %d dropped for gates, %d foundations'
              % (plan['segmentsPerSide'], plan['segmentLengthCm'], plan['wallInstances'],
                 plan['droppedForGates'], plan['foundationInstances']))
        for gate in gates(sq):
            print('  gate %-2s side %d at (%.0f, %.0f) cm  fraction %.4f  - %s'
                  % (gate['id'], gate['side'], gate['positionCm'][0], gate['positionCm'][1], gate['fraction'], gate['source']))
        if ground.available:
            profile = ground_profile(sq, ground)
            groundings = instance_groundings(sq, profile)
            for s in groundings['perSide']:
                g = profile['sides'][s['side']]
                print('  %-5s ground Z %8.1f .. %8.1f cm (%.1f .. %.1f m asl, drop %.1f m); plinths %8.1f .. %8.1f cm; '
                      'deepest substructure %.0f cm at step %d; DEM/level disagreement max %.0f cm (%d stations beyond rounding); sources %s'
                      % (s['name'], g['lowZcm'], g['highZcm'], g['lowMetresAsl'], g['highMetresAsl'], g['dropMetres'],
                         s['baseZminCm'], s['baseZmaxCm'], s['foundationDepthMaxCm'], s['deepestFoundationAtStep'],
                         g['maxDemLevelDisagreementCm'], g['stationsBeyondRounding'], g['sources']))
            for gate in groundings['gates']:
                print('  gate %-2s threshold Z %.0f cm (%.1f m asl), substructure %.0f cm'
                      % (gate['id'], gate['baseZ'], gate['thresholdMetresAsl'], gate['depth']))
        else:
            print('  ground sources absent; profile not computed')
        coverage = modern_city_coverage(sq, buildings)
        exact = coverage['exact']
        if exact:
            print('modern buildings inside (exact, area-centroid rule): %d of %d OSM buildings city-wide; '
                  '%d more have footprints the wall line cuts; %d of %d facade buildings'
                  % (exact['buildingsInside'], exact['buildingsTotal'],
                     exact['footprintsTheWallLineCutsButCentroidOutside'],
                     exact['authoredFacadeBuildingsInside'], exact['authoredFacadeBuildingsTotal']))
        for policy, counts in coverage['hideSets'].items():
            print('  hide set %-24s %s' % (policy, json.dumps(counts)))
        hs = coverage['hideSet']
        print('  collateral under hide_if_any_inside: %s' % json.dumps(hs['collateral']))
        print('  label fingerprint %s' % hs['labelFingerprintFnv1a'])
    print('side in metres under each amah opinion (3000 amot):')
    for key, cm, who in (('naeh', 48.0, "R' Chaim Naeh - and the book's own implied amah"),
                         ('project', 50.0, 'the main map\'s baked world scale'),
                         ('feinstein', 54.0, "R' Moshe Feinstein"),
                         ('chazon-ish', 57.6, 'Chazon Ish'),
                         ('chazon-ish-stringent', 58.0, 'Chazon Ish, stringent rounding')):
        metres = SIDE_AMOT * cm / 100.0
        print('  %-22s %5.1f cm -> %7.1f m a side, %.3f sq km   (%s)'
              % (key, cm, metres, (metres / 1000.0) ** 2, who))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--export', action='store_true', help='write modules, manifest, preview, receipts')
    parser.add_argument('--tests', action='store_true', help='compile and run the C++ math test')
    parser.add_argument('--report', action='store_true', help='print the review numbers')
    args = parser.parse_args()
    if not (args.export or args.tests or args.report):
        parser.print_help()
        return 0
    if args.tests:
        run_tests()
    if args.export:
        manifest = export()
        print('exported %d modules, %d instances, %d triangles -> %s'
              % (len(manifest['meshes']), manifest['instancing']['instances'],
                 manifest['instancing']['triangles']['total'], OUT))
    if args.report:
        report()
    return 0


if __name__ == '__main__':
    sys.exit(main())
