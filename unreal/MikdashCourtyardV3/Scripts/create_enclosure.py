"""EnclosureV2 - the Yechezkel 42:15-20 sacred precinct as INSTANCED modules, plus the
overlay boundary and the modern-city hide set for the three-state MODERN / YECHEZKEL /
OVERLAY toggle.

AUTHORED_OFFLINE_SOURCE. This module never imports `unreal`, never touches Content/, never
opens a map and never launches the editor. It writes OBJ modules, a geometry manifest, a
plan-view PNG and a review JSON under SourceAssets/enclosure-review/. The guarded native
importer/placer is the separate Scripts/release_enclosure.py.

WHY A SECOND ENCLOSURE GENERATOR
--------------------------------
Scripts/create_mount_enclosure.py already exports the same 3000-amah square as 52 CHUNK
meshes (32 wall chunks of 8 sub-boxes each, stepped to follow the current-city DEM) under
SourceAssets/FutureMountV1/EnclosureV1. That set is right for a wall that must sit on
uneven ground and it stays as it is; this module does not modify it and does not replace it.

What it cannot do is be toggled cheaply. A 1.44 km ring as 32 baked chunks is 32 actors with
32 large bounding boxes, no per-segment culling, and no way to fade. This module emits FOUR
module meshes instead - one wall segment, one gate, one corner, one overlay slab - which
AMikdashEnclosure places as HierarchicalInstancedStaticMeshComponent instances. The renderer
then gets one draw call per component with per-instance frustum culling and per-instance LOD,
and a state change is a material scalar rather than a re-import.

    BUDGET, RTX 2070 (8 GB, 1080p) - printed by --report and asserted by --tests
      wall     467 instances x  WALL_TRIS  (13 of 480 segments removed for the five gates)
      gates      5 instances x  GATE_TRIS
      corners    4 instances x  CORNER_TRIS
      overlay  480 instances x  OVERLAY_TRIS
      four HISM components, one draw call each before instance culling.
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

OBJ ADAPTER CONVENTION (project standard, unchanged)
----------------------------------------------------
Canonical vertices are Unreal cm, X east, +Y south, Z up, module-local with the origin at the
centre of the module's footprint on the ground. Every OBJ is written with Y REFLECTED and
triangle winding REVERSED - the legacy importer reflects Y back - exactly as
create_keilim_ti_v1.write_obj, create_sanctuary_doors.export and create_oldcity_facades do,
and as recorded in SourceAssets/sanctuary-detail/DoorsParochesV1/geometry-manifest.json.
Canonical solids are built closed and flipped when needed so the canonical signed volume
(sum dot(A, cross(B, C)) / 6) is POSITIVE; readback() re-parses each file, recomputes the
signed volume in FILE space and reproves the bounds, so an adapter sign flip is caught here
and not three scripts later. One `o` object and NO `g` groups per file: the OBJ importer
creates one material slot per `g` group, which is the SM_KeruvimStudyV1 236-slot lesson.

RUN ORDER
---------
    python Scripts/create_enclosure.py --tests     compile and run the standalone C++ test
    python Scripts/create_enclosure.py --export    write the modules, manifest and preview
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
# The OSM source the whole context was built from, still holding every building as an explicit
# polygon. It lives outside the project tree (create_oldcity_facades.py reads the same file),
# so its absence is handled rather than fatal.
JERUSALEM_SOURCE = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace'
                        r'\mikdash-walkthrough\public\context\jerusalem.json')
# The alignment already baked into every context mesh in the level, recorded in
# SourceAssets/visual-review/mount-platform-design.json `sourceData.alignment`.
# NEVER apply it twice; these coordinates are source amot, not level cm.
SOURCE_TX_AMOT = 17.509700315687695
SOURCE_TZ_AMOT = -0.5513496449385334

VCVARS = Path(r'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC'
              r'\Auxiliary\Build\vcvars64.bat')

CELL_CM = 10000.0                     # the 100 m context grid, shared with create_oldcity_facades


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
    required = ('ProjectCmPerAmah', 'AmotPerReed', 'PrecinctReedsPerSide', 'PrecinctSideAmot',
                'MiddotHarHaBayitAmot', 'CourtPlatformHalfExtentUnrealCm',
                'BookClearWestAmot', 'BookClearNorthAmot',
                'BookDiagramEnvelopeEastWestAmot', 'BookDiagramEnvelopeNorthSouthAmot',
                'BookImpliedAmahRealCm', 'BookStatedPrecinctSideMetres')
    missing = [name for name in required if name not in found]
    if missing:
        raise RuntimeError('EnclosureMath.h no longer defines: ' + ', '.join(missing))
    return found


K = header_constants()
A = K['ProjectCmPerAmah']                     # 50 Unreal cm per amah - the level's baked scale
SIDE_AMOT = K['PrecinctSideAmot']             # 3000
SIDE_CM = SIDE_AMOT * A                       # 150000
HALF_CM = SIDE_CM / 2.0
COURT_HALF = K['CourtPlatformHalfExtentUnrealCm']
CLEAR_W = K['BookClearWestAmot']
CLEAR_N = K['BookClearNorthAmot']

MODULE_LEN_CM = 1250.0                        # 25 amot; 120 modules a side, exactly
WALL_THICK_CM = 6.0 * A                       # Yechezkel 40:5: a reed thick
WALL_HEIGHT_CM = 6.0 * A                      # a reed high (book pp. 115-117)
GATE_OPENING_W_CM = 10.0 * A                  # certain: opening 10 amot wide
GATE_OPENING_H_CM = 50.0 * A                  # certain: opening 50 amot high
GATE_PIER_W_CM = 10.0 * A                     # authored (*): the book gives no pier width
GATE_TOTAL_H_CM = 60.0 * A                    # authored (*)
GATE_DEPTH_CM = 6.0 * A                       # certain: the gate is as thick as the wall
OVERLAY_SPACING_CM = 1250.0
OVERLAY_SLAB_THICK_CM = 12.0                  # a hair, so the band never z-fights a facade

# The five gates, as WORLD coordinates. E, N and W sit on the Temple's own axes; the two
# south gates at a third and two thirds of the south wall. The COUNT per side is the book's
# (five gates, two south - Mishkenei Elyon 196 m.2); the along-wall positions are the
# project's assumption and are carried as such into the manifest.
GATE_RULES = [
    dict(id='N', side=0, world=('x', 0.0), certainty='count certain; position assumed (Temple axis)'),
    dict(id='E', side=1, world=('y', 0.0), certainty='count certain; position assumed (Temple axis, Yechezkel 42:15 measures through it)'),
    dict(id='S1', side=2, world=('x', 16900.0), certainty='count certain; position assumed (one third along)'),
    dict(id='S2', side=2, world=('x', 66900.0), certainty='count certain; position assumed (two thirds along)'),
    dict(id='W', side=3, world=('y', 0.0), certainty='count certain; position assumed (Temple axis)'),
]


# =====================================================================================
# 2. The square, reproduced from the header's rule
# =====================================================================================
def square():
    """West and north OUTER faces at the stated clearances from the platform; the rest falls
    out of the 3000. Identical arithmetic to MakeSquareFromClearances."""
    west = -COURT_HALF - CLEAR_W * A
    north = -COURT_HALF - CLEAR_N * A
    return dict(west=west, north=north, east=west + SIDE_CM, south=north + SIDE_CM,
                centre=[west + HALF_CM, north + HALF_CM])


def corners(sq):
    """NW, NE, SE, SW - clockwise on screen with +Y south. Matches SquareCorners()."""
    return [(sq['west'], sq['north']), (sq['east'], sq['north']),
            (sq['east'], sq['south']), (sq['west'], sq['south'])]


def clearances(sq):
    return dict(west=(-COURT_HALF - sq['west']) / A, north=(-COURT_HALF - sq['north']) / A,
                east=(sq['east'] - COURT_HALF) / A, south=(sq['south'] - COURT_HALF) / A)


def gate_fraction(sq, rule):
    """World coordinate -> fraction 0..1 from the side's start corner. Matches
    FractionAlongSide()."""
    c = corners(sq)
    start = c[rule['side']]
    end = c[(rule['side'] + 1) % 4]
    axis, value = rule['world']
    if axis == 'x':
        span = end[0] - start[0]
        return (value - start[0]) / span
    span = end[1] - start[1]
    return (value - start[1]) / span


def gates(sq):
    out = []
    for rule in GATE_RULES:
        fraction = gate_fraction(sq, rule)
        c = corners(sq)
        start, end = c[rule['side']], c[(rule['side'] + 1) % 4]
        out.append(dict(id=rule['id'], side=rule['side'], fraction=fraction,
                        certainty=rule['certainty'],
                        positionCm=[start[0] + (end[0] - start[0]) * fraction,
                                    start[1] + (end[1] - start[1]) * fraction]))
    return out


def wall_plan(sq):
    """Mirror of PlanWall(): how many modules survive the gate openings."""
    per_side = int(math.floor(SIDE_CM / MODULE_LEN_CM + 0.5))
    seg = SIDE_CM / per_side
    full = GATE_OPENING_W_CM + 2.0 * GATE_PIER_W_CM
    kept, dropped = 0, 0
    gate_list = gates(sq)
    for side in range(4):
        for step in range(per_side):
            lo, hi = seg * step, seg * (step + 1)
            blocked = False
            for gate in gate_list:
                if gate['side'] != side:
                    continue
                centre = SIDE_CM * gate['fraction']
                if hi > centre - full / 2.0 + 1e-6 and lo < centre + full / 2.0 - 1e-6:
                    blocked = True
            if blocked:
                dropped += 1
            else:
                kept += 1
    overlay = per_side * 4
    return dict(segmentsPerSide=per_side, segmentLengthCm=seg, wallInstances=kept,
                droppedForGates=dropped, gateInstances=len(gate_list), cornerInstances=4,
                overlayInstances=overlay)


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
# 4. The four modules
# =====================================================================================
# Every module's origin is the centre of its footprint ON THE GROUND, with local +X running
# ALONG the wall and local +Y pointing OUTWARD. AMikdashEnclosure places an instance with the
# side's outward yaw minus ninety, which is exactly that convention.

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
# 6. How much of the modern city the precinct covers
# =====================================================================================
def cell_bounds(token_x, token_y):
    """`Grid_N010_N002` -> the 100 m cell's world AABB in Unreal cm."""
    def value(token):
        return -int(token[1:]) if token[0] == 'N' else int(token[1:])
    ix, iy = value(token_x), value(token_y)
    return (ix * CELL_CM, iy * CELL_CM, (ix + 1) * CELL_CM, (iy + 1) * CELL_CM)


def classify_cell(sq, aabb):
    x0, y0, x1, y1 = aabb
    inside = (sq['west'] <= x0 and x1 <= sq['east'] and sq['north'] <= y0 and y1 <= sq['south'])
    if inside:
        return 'inside'
    disjoint = (x1 <= sq['west'] or x0 >= sq['east'] or y1 <= sq['north'] or y0 >= sq['south'])
    return 'outside' if disjoint else 'straddling'


def exact_building_coverage(sq):
    """Per-building containment from the OSM source polygons, when they are reachable.

    This is the number that answers "how many modern buildings does the precinct cover", and
    it is exact rather than binned: every `kind == "building"` feature in jerusalem.json is an
    explicit point ring in source amot, so its centroid and its footprint AABB transform
    straight into level centimetres with the alignment the level already baked. A building is
    counted INSIDE when its centroid is inside - the same ESelectionRule::CentroidInside the
    runtime actor uses, so this count and the count the release script reads back agree by
    construction. Footprints the wall line cuts are reported separately and never folded in.
    """
    if not JERUSALEM_SOURCE.exists():
        return None
    # The OSM ids the authored facade set actually decorates, so the exact count can be split
    # into "buildings the facade pass touched" and "the rest of the OSM city".
    facade_ids = set()
    if FACADES_MANIFEST.exists():
        facades = json.loads(FACADES_MANIFEST.read_text(encoding='utf-8-sig'))
        for batch in facades.get('batches', []):
            entry = batch.get('facades')
            if not entry:
                continue
            for building in entry.get('perBuilding', []):
                facade_ids.add(int(building.get('osmId', 0)))
    data = json.loads(JERUSALEM_SOURCE.read_text(encoding='utf-8'))
    inside = straddling = outside = 0
    facade_inside = 0
    inside_ids = []
    for feature in data.get('features', []):
        if feature.get('kind') != 'building':
            continue
        points = feature.get('points') or []
        if len(points) < 3:
            continue
        xs = [(p[0] + SOURCE_TX_AMOT) * A for p in points]
        ys = [(p[1] + SOURCE_TZ_AMOT) * A for p in points]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        centroid_inside = (sq['west'] <= cx <= sq['east'] and sq['north'] <= cy <= sq['south'])
        verdict = classify_cell(sq, (min(xs), min(ys), max(xs), max(ys)))
        if centroid_inside:
            inside += 1
            osm_id = int(feature.get('id', 0))
            inside_ids.append(osm_id)
            if osm_id in facade_ids:
                facade_inside += 1
        elif verdict == 'straddling':
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
        rule='centroid inside (ESelectionRule::CentroidInside)',
        population=('EVERY OSM building feature in the exported city, not only the walled Old '
                    'City. That is why this number is larger than the 100 m cell band below: '
                    'the band counts only the 2106 + 1514 buildings inside the Old City walls '
                    'that OldCityFacadesV1 decorates, while the precinct also covers ground '
                    'east and south of those walls. The two are different populations, not a '
                    'contradiction.'),
        buildingsTotal=inside + straddling + outside,
        buildingsInside=inside,
        footprintsTheWallLineCutsButCentroidOutside=straddling,
        buildingsOutside=outside,
        authoredFacadeBuildingsInside=facade_inside,
        authoredFacadeBuildingsTotal=len(facade_ids),
        insideIdFingerprintFnv1a='%016x' % fingerprint)


def modern_city_coverage(sq):
    """How many modern buildings fall inside the boundary.

    HONESTY ABOUT THE UNIT. There is no per-building world position anywhere in this project:
    the Old City is batched one mesh per 100 m cell and facades-manifest.json records a
    building COUNT and a cell AABB per batch, not a centroid per building. So the answer is
    given as a band - buildings in cells wholly inside, plus buildings in cells the wall line
    cuts - and never as a single false-precision number. A 100 m cell against a 1.44 km side
    makes the band narrow, and the release script narrows it further by reading real actor
    bounds out of the loaded level and writing the exact count into its receipt.
    """
    result = dict(unit='100 m context cell', cellSizeCm=CELL_CM, sets=[])

    if FACADES_MANIFEST.exists():
        data = json.loads(FACADES_MANIFEST.read_text(encoding='utf-8-sig'))
        for role in ('facades', 'infill'):
            inside = straddling = outside = 0
            cells_in = cells_edge = 0
            for batch in data.get('batches', []):
                entry = batch.get(role)
                if not entry:
                    continue
                bounds = entry['canonicalBoundsCm']
                aabb = (bounds['min'][0], bounds['min'][1], bounds['max'][0], bounds['max'][1])
                verdict = classify_cell(sq, aabb)
                count = int(entry.get('buildings', 0))
                if verdict == 'inside':
                    inside += count
                    cells_in += 1
                elif verdict == 'straddling':
                    straddling += count
                    cells_edge += 1
                else:
                    outside += count
            result['sets'].append(dict(
                set='OldCityFacadesV1/' + role,
                actorLabelPrefix='RELEASE_OldCityFacades_' if role == 'facades'
                                 else 'RELEASE_OldCityInfill_',
                buildingsTotal=inside + straddling + outside,
                buildingsInCellsWhollyInside=inside,
                buildingsInCellsTheWallLineCuts=straddling,
                buildingsOutside=outside,
                cellsWhollyInside=cells_in, cellsStraddling=cells_edge))
    else:
        result['sets'].append(dict(set='OldCityFacadesV1', error='facades-manifest.json absent'))

    if BUILDINGS_REOPEN.exists():
        data = json.loads(BUILDINGS_REOPEN.read_text(encoding='utf-8-sig'))
        inside = straddling = outside = 0
        pattern = re.compile(r'SM_JerusalemBuildings_Grid_([NP]\d{3})_([NP]\d{3})')
        for check in data.get('meshChecks', []):
            match = pattern.search(check.get('asset', ''))
            if not match:
                continue
            verdict = classify_cell(sq, cell_bounds(match.group(1), match.group(2)))
            if verdict == 'inside':
                inside += 1
            elif verdict == 'straddling':
                straddling += 1
            else:
                outside += 1
        result['sets'].append(dict(
            set='JerusalemContext/Buildings (imported OSM extrusions)',
            actorLabelPrefix='SM_JerusalemBuildings_',
            note='one actor per 100 m cell, so these are CELL counts, not building counts',
            cellActorsTotal=inside + straddling + outside,
            cellActorsWhollyInside=inside, cellActorsStraddling=straddling,
            cellActorsOutside=outside))

    totals_in = sum(s.get('buildingsInCellsWhollyInside', 0) for s in result['sets'])
    totals_edge = sum(s.get('buildingsInCellsTheWallLineCuts', 0) for s in result['sets'])
    result['authoredBuildingsInsideLow'] = totals_in
    result['authoredBuildingsInsideHigh'] = totals_in + totals_edge
    # The exact answer, when the OSM source is reachable. The cell band above stays in the
    # manifest either way, because it is what a reviewer can recompute from files that are
    # inside this repository.
    result['exact'] = exact_building_coverage(sq)
    return result


# =====================================================================================
# 7. Preview PNG - a plan of the square over the city
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

    rect(-COURT_HALF, -COURT_HALF, COURT_HALF, COURT_HALF, (250, 230, 160))
    half500 = K['MiddotHarHaBayitAmot'] * A / 2.0
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
# 8. Export
# =====================================================================================
def export():
    OUT.mkdir(parents=True, exist_ok=True)
    meshes = (OUT / 'EnclosureV2')
    meshes.mkdir(parents=True, exist_ok=True)
    sq = square()

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
        overlay=plan['overlayInstances'] * by_name['SM_EnclosureV2_OverlaySlab']['triangles'])
    triangles['total'] = sum(triangles.values())
    instances = (plan['wallInstances'] + plan['gateInstances'] + plan['cornerInstances']
                 + plan['overlayInstances'])

    coverage = modern_city_coverage(sq)
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

    manifest = dict(
        status='OFFLINE_SOURCE_EXPORTED_NATIVE_PENDING',
        namespace=DEST,
        meshFolder=DEST + '/Meshes',
        generatorSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        enclosureMathSha256=hashlib.sha256(HEADER.read_bytes()).hexdigest(),
        cmPerAmah=A,
        coordinateConvention=('UE cm: X east, Y south, Z up; measured court centre at the '
                              'origin; module origin at the centre of its footprint on the '
                              'ground with local +X along the wall and +Y outward; OBJ files '
                              'carry Y negated and reversed winding (legacy adapter)'),
        objConvention=('per-face vertices; file Y = -canonical Y and winding reversed; the '
                       'importer reflects Y back, so imported bounds must equal '
                       'canonicalBoundsCm and imported signed volumes must be positive. One '
                       '`o` object and no `g` groups, so one material slot per mesh.'),
        square=dict(sideAmot=SIDE_AMOT, sideReeds=SIDE_AMOT / K['AmotPerReed'], sideCm=SIDE_CM,
                    outerFacesCm=dict(xWest=sq['west'], xEast=sq['east'],
                                      yNorth=sq['north'], ySouth=sq['south']),
                    centreCm=sq['centre'],
                    matchesEnclosureV1=_matches_existing_design(sq)),
        clearancesAmot=clearances(sq),
        clearanceOrder=_clearance_order_note(sq),
        gates=gates(sq),
        gateBlockAmot=dict(openingWidth=GATE_OPENING_W_CM / A, openingHeight=GATE_OPENING_H_CM / A,
                           pierWidth=GATE_PIER_W_CM / A, totalHeight=GATE_TOTAL_H_CM / A,
                           depth=GATE_DEPTH_CM / A),
        wallSectionAmot=dict(thickness=WALL_THICK_CM / A, height=WALL_HEIGHT_CM / A),
        instancing=dict(
            componentType='HierarchicalInstancedStaticMeshComponent',
            components=4, plan=plan, instances=instances, triangles=triangles,
            budgetNote=('RTX 2070, 8 GB, 1080p. %d instances across four HISM components and '
                        '%d triangles for the whole 1.44 km ring, against 3,416,580 triangles '
                        'in the 190-actor Old City facade set the YECHEZKEL state hides - '
                        'about %.1f%% of it. Per-instance frustum culling means the visible '
                        'cost is a small fraction of that again; a single-mesh wall would be '
                        'one 1.44 km bounding box and would cull as all-or-nothing.'
                        % (instances, triangles['total'],
                           100.0 * triangles['total'] / 3416580.0))),
        modernCityCoverage=coverage,
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
            'The wall sits at Z 0 in module space. AMikdashEnclosure places every instance on '
            'the level plane; it does NOT step the wall to follow terrain, which EnclosureV1 '
            'does. Over the Kidron and the Hinnom the ring will float or bury. Fixing that '
            'means per-instance Z from the DEM and is not done here.',
            'Gate along-wall positions are the project assumption, not the book. Only the '
            'count per side and the 10 x 50 amah opening are sourced.',
            'Building counts are per 100 m cell, because no per-building world position exists '
            'in this project. The release script replaces the band with an exact count.',
            'Wall face articulation, corner blocks and gate profiles are AUTHORED. The book '
            'gives the wall a section and the gates an opening, and no elevation.',
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
              'OverlayQuadTriangles': 'SM_EnclosureV2_OverlaySlab'}
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
# 9. The standalone C++ test
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
# 10. Report
# =====================================================================================
def report():
    sq = square()
    plan = wall_plan(sq)
    coverage = modern_city_coverage(sq)
    print('precinct: %g amot (%g reeds) a side = %g Unreal cm at %g cm/amah'
          % (SIDE_AMOT, SIDE_AMOT / K['AmotPerReed'], SIDE_CM, A))
    print('outer faces cm: west %g east %g north %g south %g; centre (%g, %g)'
          % (sq['west'], sq['east'], sq['north'], sq['south'], sq['centre'][0], sq['centre'][1]))
    c = clearances(sq)
    print('clearances amot: west %g north %g east %g south %g (Middot order holds: %s)'
          % (c['west'], c['north'], c['east'], c['south'], _clearance_order_note(sq)['holds']))
    print('side in metres under each amah opinion:')
    for key, cm, who in (('naeh', 48.0, "R' Chaim Naeh - and the book's own implied amah"),
                         ('project', 50.0, 'the level\'s baked world scale'),
                         ('feinstein', 54.0, "R' Moshe Feinstein"),
                         ('chazon-ish', 57.6, 'Chazon Ish'),
                         ('chazon-ish-stringent', 58.0, 'Chazon Ish, stringent rounding')):
        metres = SIDE_AMOT * cm / 100.0
        print('  %-22s %5.1f cm -> %7.1f m a side, %.3f sq km   (%s)'
              % (key, cm, metres, (metres / 1000.0) ** 2, who))
    print('wall plan: %d modules/side of %g cm, %d kept, %d dropped for gates'
          % (plan['segmentsPerSide'], plan['segmentLengthCm'], plan['wallInstances'],
             plan['droppedForGates']))
    exact = coverage.get('exact')
    if exact:
        print('modern buildings inside (exact, centroid rule): %d of %d OSM buildings city-wide; '
              '%d more have footprints the wall line cuts'
              % (exact['buildingsInside'], exact['buildingsTotal'],
                 exact['footprintsTheWallLineCutsButCentroidOutside']))
        print('  of which authored Old City facade buildings: %d of %d'
              % (exact['authoredFacadeBuildingsInside'], exact['authoredFacadeBuildingsTotal']))
    print('modern buildings inside (100 m cell band): %d certain, up to %d counting cut cells'
          % (coverage['authoredBuildingsInsideLow'], coverage['authoredBuildingsInsideHigh']))
    for entry in coverage['sets']:
        print('  ' + json.dumps(entry, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--export', action='store_true', help='write modules, manifest, preview')
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
