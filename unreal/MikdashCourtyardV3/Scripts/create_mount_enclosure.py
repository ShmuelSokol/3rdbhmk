"""Offline generator for the future Temple Mount enclosure (Lishchno Tidreshu, Part I).

Writes SourceAssets/FutureMountV1/EnclosureV1/: OBJ parts, geometry-manifest.json,
enclosure-design.json, preview-plan.png and preview-platform.png. Nothing here touches
the engine or Content/. Run with the engine Python (no third-party modules needed):

  "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe"
      Scripts/create_mount_enclosure.py            # refuses if the manifest exists
  ... create_mount_enclosure.py --force            # regenerate (import script re-freezes)

Book statements modelled (page numbers of mikdash book/Original-Hebrew-Book.pdf, Hebrew
confirmed in Book-Source-Data.json hebrewInput and on the page images):
  * pp. 115-117, 359-363: Har HaBayis wall 500 x 500 reeds = 3000 x 3000 amot, measured
    from outside (42:15-20); wall one reed = 6 amot thick x 6 amot high on all four sides
    (Rashi 40:5 with Middos 2:4; Mishkenei Elyon 196 m.2) - CERTAIN (book main line).
  * pp. 115-117: five gates, 2 south / 1 east / 1 north / 1 west (Mishkenei Elyon 196 m.2,
    as Middos 1:3); opening 50 amot high x 10 wide, gate thickness = wall (6); doors -
    Mishkenei Elyon COMPLETION adopted by the book. Author (*): 10 amot of wall above the
    opening and 10-amot jamb piers, total gate height 60 amot like the eilim (fig. 5'4).
  * pp. 113, 116 (fig. 2'2, 5'3): the Sanctuary sits near the NORTH-WEST of the Mount:
    open ground largest south, then east, then north, least west (Mishkenei Elyon 196
    m.1; Middos 2:1 pattern). Fig. 2'2 gives 500 amot west, 501 north, 2149 east, 2153
    south around a ~351 x 346 amot Temple envelope - author's diagram.
  * pp. 121-126: before the outer court a soreg 10 tefachim high (Middos 2:3; Mishkenei
    Elyon 196 m.3), then the Cheil = a wall 10 amot high (Rambam 5:3, Meiri, Mishkenei
    Elyon 192; author draws it 1 amah thick 'for study'), then 10 amot open (also called
    cheil), then 12 steps east / 7 north and south, rise 0.5 x tread 0.5, last step 4.5
    amot deep (10 amot long, 6 amot rise). Soreg position: Rambam/Rosh/Mishkenei Elyon -
    between the cheil and the Mount wall, exact distance unknown (p. 126: 'at some
    distance from the cheil').
  * pp. 359-363: Rashi 42:20 'crosswise = the cheil wall around the whole mountain';
    author (*): possibly an additional soreg ring of 500 x 500 amot around the Sanctuary.
    NOT generated (checked offline: centred on the court it leaves the platform on the
    north-east); recorded in the design JSON.

Scene conventions: 50 cm per amah, UE cm, X east, Y south, Z up; measured court centre
at the origin, outer court supporting platform +-8100 cm at Z 0..299; future platform
deck top Z 0. Source OBJs follow the reviewed legacy adapter convention (Y negated and
winding reversed in the file; the FBX/OBJ importer reflects Y back).
"""
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets' / 'FutureMountV1' / 'EnclosureV1'
ARCHITECTURE_MANIFEST = ROOT / 'SourceAssets' / 'architecture-manifest.json'
PLATFORM_DESIGN = ROOT / 'SourceAssets' / 'visual-review' / 'mount-platform-design.json'
TERRAIN_SOURCE = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\output\architecture-review\jerusalem-meshes.json')
TERRAIN_SOURCE_SHA256 = 'cec2748be02f7a52616407c6bee12618369b75cbf93c5c8dcd5d4135cdfd52fb'
NAMESPACE = '/Game/MikdashV3/FutureMountV1/EnclosureV1'

A = 50.0                      # cm per amah
TEFACH = A / 6.0              # 8.333 cm
SOURCE_ALIGN_X_AMOT = 17.509700315687695   # source Three amot -> UE cm: ((x+17.5097)*50, (z-0.55135)*50, y*50)
SOURCE_ALIGN_Z_AMOT = 0.5513496449385334
GRID_N = 257
GRID_ORIGIN_AMOT = -6400.0
GRID_STEP_AMOT = 50.0

# --- enclosure dimensions (amot) ---------------------------------------------------
SIDE_AMOT = 3000.0
WALL_THICK_AMOT = 6.0
WALL_HIGH_AMOT = 6.0
CLEAR_WEST_AMOT = 500.0       # fig. 2'2 (p. 113): least open ground west
CLEAR_NORTH_AMOT = 501.0      # fig. 2'2: third = north
GATE_OPEN_W_AMOT = 10.0
GATE_OPEN_H_AMOT = 50.0
GATE_PIER_W_AMOT = 10.0       # author (*) p. 115/117 fig. 5'4: jamb piers 10, wall above 10
GATE_TOTAL_H_AMOT = 60.0
CHUNKS_PER_SIDE = 8
SUBBOX_MAX_CM = 2500.0        # terrain-following sub-boxes (one terrain grid cell)
FOOTING_CM = 100.0            # buried footing below the lowest sampled ground
# --- approach ring around the outer court (cm from the court centre) -------------------
COURT_HALF = 8100.0           # SM_0127 outer court supporting platform (verified from the manifest)
STAIR_FOOT = 9200.0           # measured east stairs end (SM_0261 max X)
CHEIL_OPEN_AMOT = 10.0
CHEIL_WALL_THICK_AMOT = 1.0   # author 'for study' (p. 121)
CHEIL_WALL_HIGH_AMOT = 10.0
SOREG_GAP_AMOT = 10.0         # ASSUMPTION: soreg 10 amot outside the cheil wall (book: unknown distance)
SOREG_THICK_CM = 25.0
SOREG_HIGH_CM = 10 * TEFACH
SLAB_THICK_CM = 5.0
APPROACH_W_CM = 500.0         # 10-amot openings in cheil wall and soreg in front of the E/N/S gates

STONE = 'stone'
PAVING = 'paving'
CEDAR = 'cedar'


# ----------------------------------------------------------------------------------
# small geometry helpers
# ----------------------------------------------------------------------------------

def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def box_tris(lo, hi):
    """12 outward-facing triangles (right-handed CCW) of an axis-aligned box."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 2, 1), (0, 3, 2),            # bottom (-Z)
         (4, 5, 6), (4, 6, 7),            # top (+Z)
         (0, 1, 5), (0, 5, 4),            # -Y
         (2, 3, 7), (2, 7, 6),            # +Y
         (1, 2, 6), (1, 6, 5),            # +X
         (3, 0, 4), (3, 4, 7)]            # -X
    return v, f


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def volume(vertices, faces):
    total = 0.0
    for a, b, c in faces:
        p, q, r = vertices[a], vertices[b], vertices[c]
        n = cross((q[0] - p[0], q[1] - p[1], q[2] - p[2]), (r[0] - p[0], r[1] - p[1], r[2] - p[2]))
        total += (p[0] * n[0] + p[1] * n[1] + p[2] * n[2]) / 6.0
    return total


def point_in_polygon(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xi > x:
                inside = not inside
    return inside


def point_segment_distance(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    ll = dx * dx + dy * dy
    t = 0.0 if ll == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ll))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def segments_intersect(p1, p2, p3, p4):
    def orient(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)
    o1, o2, o3, o4 = orient(p1, p2, p3), orient(p1, p2, p4), orient(p3, p4, p1), orient(p3, p4, p2)
    if o1 != o2 and o3 != o4:
        return True
    return False


def rect_corners(rect):
    x0, y0, x1, y1 = rect
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def rect_polygon_relation(rect, poly):
    """'inside', 'outside' or 'crossing' plus the minimum corner distance to the polygon edges."""
    corners = rect_corners(rect)
    inside = [point_in_polygon(c, poly) for c in corners]
    edges = [(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]
    rect_edges = [(corners[i], corners[(i + 1) % 4]) for i in range(4)]
    crossing = any(segments_intersect(a, b, c, d) for a, b in rect_edges for c, d in edges)
    poly_inside_rect = any(rect[0] < px < rect[2] and rect[1] < py < rect[3] for px, py in poly)
    min_distance = min(point_segment_distance(c, a, b) for c in corners for a, b in edges)
    if crossing or poly_inside_rect or (any(inside) and not all(inside)):
        relation = 'crossing'
    elif all(inside):
        relation = 'inside'
    else:
        relation = 'outside'
    return relation, min_distance


# ----------------------------------------------------------------------------------
# terrain sampling (source DEM grid, exact source triangulation)
# ----------------------------------------------------------------------------------

class Terrain:
    def __init__(self):
        self.heights = None
        self.status = 'unavailable'
        self.detail = None
        if not TERRAIN_SOURCE.exists():
            self.detail = 'terrain source missing: ' + str(TERRAIN_SOURCE)
            return
        actual = sha256_of(TERRAIN_SOURCE)
        if actual != TERRAIN_SOURCE_SHA256:
            self.detail = 'terrain source sha256 %s differs from the frozen platform/terrain-cut value' % actual
            return
        data = json.loads(TERRAIN_SOURCE.read_text(encoding='utf-8'))
        mesh = [m for m in data['meshes'] if m.get('name') == 'Terrain 0' and m.get('category') == 'Terrain']
        if len(mesh) != 1:
            self.detail = 'Terrain 0 mesh not found exactly once'
            return
        positions = mesh[0]['positions']
        if len(positions) != GRID_N * GRID_N * 3:
            self.detail = 'Terrain 0 has %d floats, expected %d' % (len(positions), GRID_N * GRID_N * 3)
            return
        indices = mesh[0]['indices']
        if indices[:6] != [0, 257, 1, 257, 258, 1]:
            self.detail = 'unexpected terrain triangulation order'
            return
        # verify the regular grid layout (x fastest, z rows)
        for k in (0, 1, 257, 258, GRID_N * GRID_N - 1):
            x, _, z = positions[3 * k:3 * k + 3]
            col, row = k % GRID_N, k // GRID_N
            if abs(x - (GRID_ORIGIN_AMOT + col * GRID_STEP_AMOT)) > 1e-6 or abs(z - (GRID_ORIGIN_AMOT + row * GRID_STEP_AMOT)) > 1e-6:
                self.detail = 'terrain grid is not regular at vertex %d' % k
                return
        self.heights = positions[1::3]
        self.status = 'source_grid_exact_triangulation'
        self.detail = {'file': str(TERRAIN_SOURCE), 'sha256': actual, 'vertices': GRID_N * GRID_N,
                       'cellCm': GRID_STEP_AMOT * A, 'triangulation': 'cell (c,r): (v00,v01,v10),(v01,v11,v10) as in source indices'}

    def height_cm(self, x_cm, y_cm):
        """Ground Z (cm) at UE (x, y) from the source triangles; None outside the grid."""
        if self.heights is None:
            return None
        xa = x_cm / A - SOURCE_ALIGN_X_AMOT
        za = y_cm / A + SOURCE_ALIGN_Z_AMOT
        fc = (xa - GRID_ORIGIN_AMOT) / GRID_STEP_AMOT
        fr = (za - GRID_ORIGIN_AMOT) / GRID_STEP_AMOT
        c, r = int(math.floor(fc)), int(math.floor(fr))
        if c < 0 or r < 0 or c >= GRID_N - 1 or r >= GRID_N - 1:
            return None
        u, v = fc - c, fr - r
        h = self.heights
        h00 = h[r * GRID_N + c]
        h10 = h[r * GRID_N + c + 1]
        h01 = h[(r + 1) * GRID_N + c]
        h11 = h[(r + 1) * GRID_N + c + 1]
        if u + v <= 1.0:
            ha = h00 + u * (h10 - h00) + v * (h01 - h00)
        else:
            ha = h11 + (1.0 - u) * (h01 - h11) + (1.0 - v) * (h10 - h11)
        return ha * A

    def sample_rect(self, rect, step=250.0):
        """min/max/mean ground Z over a rectangle footprint (grid of samples incl. edges)."""
        x0, y0, x1, y1 = rect
        nx = max(2, int(math.ceil((x1 - x0) / step)) + 1)
        ny = max(2, int(math.ceil((y1 - y0) / step)) + 1)
        values = []
        for i in range(nx):
            x = x0 + (x1 - x0) * i / (nx - 1)
            for j in range(ny):
                y = y0 + (y1 - y0) * j / (ny - 1)
                z = self.height_cm(x, y)
                if z is not None:
                    values.append(z)
        if not values:
            return None
        return {'min': min(values), 'max': max(values), 'mean': sum(values) / len(values), 'samples': len(values)}


# ----------------------------------------------------------------------------------
# design
# ----------------------------------------------------------------------------------

def load_inputs():
    manifest = json.loads(ARCHITECTURE_MANIFEST.read_text(encoding='utf-8-sig'))
    by_name = {e['assetName']: e for e in manifest['meshes']}
    platform = by_name['SM_0127_architecture_Outer_court_supporting_platform']['expectedBoundsUnrealCm']
    if platform['min'][:2] != [-COURT_HALF, -COURT_HALF] or platform['max'][:2] != [COURT_HALF, COURT_HALF]:
        raise RuntimeError('Outer court supporting platform bounds differ from +-8100: %r' % platform)
    stair = by_name['SM_0261_architecture_Outer_E_stair_1']['expectedBoundsUnrealCm']
    if stair['max'][0] != STAIR_FOOT or stair['min'][2] != 0.0:
        raise RuntimeError('East stair foot differs from X 9200 / Z 0: %r' % stair)
    stairs = {}
    for key, names in (('east', ['SM_%04d_architecture_Outer_E_stair_%d' % (260 + i, i) for i in range(1, 13)]),
                       ('north', ['SM_%04d_architecture_Outer_N_stair_%d' % (356 + i, i) for i in range(1, 8)]),
                       ('south', ['SM_%04d_architecture_Outer_S_stair_%d' % (457 + i, i) for i in range(1, 8)])):
        boxes = [by_name[n]['expectedBoundsUnrealCm'] for n in names]
        stairs[key] = {'assets': names, 'unionMin': [min(b['min'][i] for b in boxes) for i in range(3)],
                       'unionMax': [max(b['max'][i] for b in boxes) for i in range(3)]}
    design = json.loads(PLATFORM_DESIGN.read_text(encoding='utf-8'))
    boundary = [tuple(p) for p in design['boundary']['nativeXYcm']]
    if boundary[0] == boundary[-1]:
        boundary = boundary[:-1]
    protected = [{'name': p['name'], 'kind': p['kind'], 'osmId': p['osmId'], 'bufferCm': p['minimumNoEditBufferCm'],
                  'polygon': [tuple(q) for q in (p['nativeXYcm'][:-1] if p['nativeXYcm'][0] == p['nativeXYcm'][-1] else p['nativeXYcm'])]}
                 for p in design['protected']]
    if design['levels']['platformTopZcm'] != 0:
        raise RuntimeError('Platform deck top is not Z 0')
    return {'architectureManifestSha256': sha256_of(ARCHITECTURE_MANIFEST), 'platformDesignSha256': sha256_of(PLATFORM_DESIGN),
            'courtPlatformBounds': platform, 'stairs': stairs, 'boundary': boundary, 'protected': protected,
            'wallCentrelineInsetCm': 110.0, 'guardBufferCm': 201.0}


def enclosure_frame():
    xw = -COURT_HALF - CLEAR_WEST_AMOT * A            # west outer face
    yn = -COURT_HALF - CLEAR_NORTH_AMOT * A           # north outer face
    xe = xw + SIDE_AMOT * A
    ys = yn + SIDE_AMOT * A
    t = WALL_THICK_AMOT * A
    return {'outer': {'xWest': xw, 'xEast': xe, 'yNorth': yn, 'ySouth': ys}, 'thicknessCm': t, 'heightCm': WALL_HIGH_AMOT * A,
            'clearancesAmot': {'west': CLEAR_WEST_AMOT, 'north': CLEAR_NORTH_AMOT,
                               'east': (xe - COURT_HALF) / A, 'south': (ys - COURT_HALF) / A}}


def gate_positions(frame):
    o = frame['outer']
    return [
        {'id': 'E', 'side': 'E', 'along': 0.0, 'name': 'East gate', 'rule': 'on the Temple east-west axis (Yechezkel 42:15 measures through the east gate)'},
        {'id': 'N', 'side': 'N', 'along': 0.0, 'name': 'North gate (Tadi analogue)', 'rule': 'on the Temple north-south axis (fig. 5\'3 shows gate 5 beside the Sanctuary)'},
        {'id': 'W', 'side': 'W', 'along': 0.0, 'name': 'West gate (Kiponus analogue)', 'rule': 'ASSUMPTION: on the Temple east-west axis; the book gives no position'},
        {'id': 'S1', 'side': 'S', 'along': o['xWest'] + 1000.0 * A, 'name': 'South gate 1 (Chuldah analogue)', 'rule': 'ASSUMPTION: at one third of the south wall (fig. 5\'3 spaces the two gates along the side)'},
        {'id': 'S2', 'side': 'S', 'along': o['xWest'] + 2000.0 * A, 'name': 'South gate 2 (Chuldah analogue)', 'rule': 'ASSUMPTION: at two thirds of the south wall'},
    ]


def side_geometry(frame, side):
    """(fixed axis range across the wall, along range, axis names) for one side."""
    o = frame['outer']
    t = frame['thicknessCm']
    if side == 'W':
        return ('x', (o['xWest'], o['xWest'] + t), (o['yNorth'], o['ySouth']))
    if side == 'E':
        return ('x', (o['xEast'] - t, o['xEast']), (o['yNorth'], o['ySouth']))
    if side == 'N':
        return ('y', (o['yNorth'], o['yNorth'] + t), (o['xWest'] + t, o['xEast'] - t))
    return ('y', (o['ySouth'] - t, o['ySouth']), (o['xWest'] + t, o['xEast'] - t))


def rect_from(axis, across, along):
    if axis == 'x':
        return (across[0], along[0], across[1], along[1])
    return (along[0], across[0], along[1], across[1])


def subtract_intervals(run, cuts):
    pieces = [run]
    for c0, c1 in cuts:
        out = []
        for a0, a1 in pieces:
            if c1 <= a0 or c0 >= a1:
                out.append((a0, a1))
            else:
                if c0 > a0:
                    out.append((a0, c0))
                if c1 < a1:
                    out.append((c1, a1))
        pieces = out
    return [p for p in pieces if p[1] - p[0] > 1e-6]


def ground_policy(terrain, rect, base_height):
    """Base/top Z of a part standing on terrain; falls back to Z 0 when terrain is unavailable."""
    sample = terrain.sample_rect(rect) if terrain.heights is not None else None
    if sample is None:
        return {'baseZ': -FOOTING_CM, 'groundRefZ': 0.0, 'topZ': base_height, 'terrain': None, 'policy': 'z0_fallback'}
    return {'baseZ': sample['min'] - FOOTING_CM, 'groundRefZ': sample['max'], 'topZ': sample['max'] + base_height,
            'terrain': sample, 'policy': 'terrain_min_footing_max_plus_height'}


def build_wall_parts(frame, gates, terrain):
    parts = []
    gate_span = (GATE_PIER_W_AMOT * 2 + GATE_OPEN_W_AMOT) * A / 2.0
    for side in ('W', 'E', 'N', 'S'):
        axis, across, along = side_geometry(frame, side)
        cuts = [(g['along'] - gate_span, g['along'] + gate_span) for g in gates if g['side'] == side]
        length = along[1] - along[0]
        for k in range(CHUNKS_PER_SIDE):
            a0 = along[0] + length * k / CHUNKS_PER_SIDE
            a1 = along[0] + length * (k + 1) / CHUNKS_PER_SIDE
            boxes = []
            for r0, r1 in subtract_intervals((a0, a1), cuts):
                n = max(1, int(math.ceil((r1 - r0) / SUBBOX_MAX_CM)))
                for j in range(n):
                    s0 = r0 + (r1 - r0) * j / n
                    s1 = r0 + (r1 - r0) * (j + 1) / n
                    rect = rect_from(axis, across, (s0, s1))
                    z = ground_policy(terrain, rect, frame['heightCm'])
                    boxes.append({'name': 'wall_%s_%02d_%02d' % (side, k + 1, len(boxes) + 1), 'rect': rect, 'z0': z['baseZ'], 'z1': z['topZ'],
                                  'ground': z})
            parts.append({'name': 'SM_EnclosureV1_Wall_%s_%02d' % (side, k + 1), 'group': 'wall', 'material': STONE, 'boxes': boxes,
                          'side': side, 'chunk': k + 1, 'alongCm': [a0, a1], 'gateCuts': [c for c in cuts if c[1] > a0 and c[0] < a1],
                          'source': {'pages': [115, 116, 117, 359, 361, 362, 363], 'status': 'certain',
                                     'text': 'wall 6 x 6 amot, 3000 x 3000 amot measured from outside (Yechezkel 40:5, 42:15-20; Rashi; Mishkenei Elyon 196)'}})
    return parts


def build_gate_parts(frame, gates, terrain):
    parts = []
    pier = GATE_PIER_W_AMOT * A
    opening = GATE_OPEN_W_AMOT * A
    for g in gates:
        axis, across, _ = side_geometry(frame, g['side'])
        c = g['along']
        footprint = rect_from(axis, across, (c - pier - opening / 2, c + pier + opening / 2))
        z = ground_policy(terrain, footprint, GATE_TOTAL_H_AMOT * A)
        ground = z['groundRefZ']
        boxes = []
        for label, span in (('pier_a', (c - pier - opening / 2, c - opening / 2)), ('pier_b', (c + opening / 2, c + pier + opening / 2))):
            boxes.append({'name': 'gate_%s_%s' % (g['id'], label), 'rect': rect_from(axis, across, span), 'z0': z['baseZ'], 'z1': ground + GATE_TOTAL_H_AMOT * A, 'ground': z})
        boxes.append({'name': 'gate_%s_lintel' % g['id'], 'rect': rect_from(axis, across, (c - opening / 2, c + opening / 2)),
                      'z0': ground + GATE_OPEN_H_AMOT * A, 'z1': ground + GATE_TOTAL_H_AMOT * A, 'ground': z})
        parts.append({'name': 'SM_EnclosureV1_Gate_%s' % g['id'], 'group': 'gates', 'material': STONE, 'boxes': boxes, 'gate': g,
                      'openingCm': {'width': opening, 'height': GATE_OPEN_H_AMOT * A, 'sillZ': ground, 'headZ': ground + GATE_OPEN_H_AMOT * A},
                      'source': {'pages': [115, 116, 117], 'status': 'gates = Mishkenei Elyon completion; 60-amot piers/lintel = author (*)',
                                 'text': 'five gates (2 S, 1 E, 1 N, 1 W), opening 50 high x 10 wide, thickness 6; author: 10 amot of wall above the opening, 60 total (fig. 5\'4); doors not modelled (open)'}})
    return parts


def build_ring_parts(inputs):
    """Cheil slab, cheil wall and soreg around the outer court, on the platform deck (Z 0)."""
    parts = []
    slab_in = STAIR_FOOT
    slab_out = STAIR_FOOT + CHEIL_OPEN_AMOT * A          # 9700
    wall_out = slab_out + CHEIL_WALL_THICK_AMOT * A      # 9750
    soreg_in = wall_out + SOREG_GAP_AMOT * A             # 10250
    soreg_out = soreg_in + SOREG_THICK_CM                # 10275
    gate_sides = {'E': 'x+', 'N': 'y-', 'S': 'y+'}      # no west outer gate in Yechezkel's court

    def ring(name_prefix, group, material, inner, outer, z0, z1, openings, source):
        for side in ('E', 'W', 'N', 'S'):
            boxes = []
            if side in ('E', 'W'):
                x = (inner, outer) if side == 'E' else (-outer, -inner)
                runs = [(-outer, outer)]
                if openings and side == 'E':
                    runs = subtract_intervals(runs[0], [(-APPROACH_W_CM / 2, APPROACH_W_CM / 2)])
                for r in runs:
                    boxes.append({'name': '%s_%s_%02d' % (name_prefix, side, len(boxes) + 1), 'rect': (x[0], r[0], x[1], r[1]), 'z0': z0, 'z1': z1})
            else:
                y = (inner, outer) if side == 'S' else (-outer, -inner)
                runs = [(-inner, inner)]
                if openings:
                    runs = subtract_intervals(runs[0], [(-APPROACH_W_CM / 2, APPROACH_W_CM / 2)])
                for r in runs:
                    boxes.append({'name': '%s_%s_%02d' % (name_prefix, side, len(boxes) + 1), 'rect': (r[0], y[0], r[1], y[1]), 'z0': z0, 'z1': z1})
            parts.append({'name': 'SM_EnclosureV1_%s_%s' % (name_prefix.capitalize(), side), 'group': group, 'material': material,
                          'boxes': boxes, 'side': side, 'source': source})

    ring('cheilslab', 'cheil', PAVING, slab_in, slab_out, 0.0, SLAB_THICK_CM, False,
         {'pages': [121, 122, 123, 125, 126], 'status': 'Middos 2:3 completion adopted by the book',
          'text': '10 amot open space called cheil between the cheil wall and the 12/7 steps (Middos 2:3; Rambam 5:3); modelled as a 5 cm paving slab on the deck'})
    ring('cheilwall', 'cheil', STONE, slab_out, wall_out, 0.0, CHEIL_WALL_HIGH_AMOT * A, True,
         {'pages': [121, 122, 123, 125, 126, 362, 363], 'status': 'cheil-as-wall = Rambam/Meiri/Mishkenei Elyon view adopted; 1 amah thickness = author',
          'text': 'Cheil = wall 10 amot high around the court (Rambam Beis HaBechirah 5:3; Rashi 42:20 "the cheil wall around the whole mountain"); 10-amot openings in front of the E/N/S gates are an assumption'})
    ring('soreg', 'soreg', CEDAR, soreg_in, soreg_out, 0.0, SOREG_HIGH_CM, True,
         {'pages': [121, 122, 125, 126, 362, 363], 'status': 'Middos 2:3 completion; position = assumption (book: unknown distance between cheil and Mount wall)',
          'text': 'soreg lattice 10 tefachim high of wood strips (Middos 2:3; Mishkenei Elyon 191, 196); simplified as a 25 cm solid band 10 amot outside the cheil wall'})
    return parts, {'slabInnerCm': slab_in, 'slabOuterCm': slab_out, 'cheilWallOuterCm': wall_out, 'soregInnerCm': soreg_in, 'soregOuterCm': soreg_out,
                   'approachOpeningCm': APPROACH_W_CM, 'gateSides': gate_sides}


def build_step_parts(inputs):
    """Book steps (0.5 x 0.5 amah, last 4.5 deep) as stacked slabs; duplicates of the measured stairs."""
    parts = []
    half_w = APPROACH_W_CM / 2
    for key, count, base_z in (('E', 12, 0.0), ('N', 7, 250.0), ('S', 7, 250.0)):
        boxes = []
        run = 0.5 * A * (count - 1) + 4.5 * A               # east: 11 x 0.5 + 4.5 = 10 amot; north/south: 6 x 0.5 + 4.5 = 7.5 amot
        for i in range(1, count + 1):                       # i = 1 bottom (outer) ... count top (at the gate threshold)
            inner_edge = COURT_HALF + 500.0                 # 8600: gate threshold plane (measured stair top)
            outer_edge = inner_edge + run - 0.5 * A * (i - 1)   # each higher step is half an amah shorter; the top step keeps 4.5 amot
            z0 = base_z + 25.0 * (i - 1)
            z1 = base_z + 25.0 * i
            if key == 'E':
                rect = (inner_edge, -half_w, outer_edge, half_w)
            elif key == 'N':
                rect = (-half_w, -outer_edge, half_w, -inner_edge)
            else:
                rect = (-half_w, inner_edge, half_w, outer_edge)
            boxes.append({'name': 'step_%s_%02d' % (key, i), 'rect': rect, 'z0': z0, 'z1': z1})
        parts.append({'name': 'SM_EnclosureV1_Steps_%s' % key, 'group': 'steps', 'material': STONE, 'boxes': boxes, 'side': key,
                      'duplicates': inputs['stairs'][{'E': 'east', 'N': 'north', 'S': 'south'}[key]]['assets'],
                      'source': {'pages': [119, 121, 122, 123, 125, 126], 'status': 'Middos 2:3 completion adopted (12 east; 7 north/south)',
                                 'text': '12 steps of 0.5 rise x 0.5 tread, the last 4.5 amot deep, 10 amot long, 6 amot rise from the cheil to the east gate (7 steps north/south). The measured scene already has 12/7 stairs with 1-amah treads (X 8600..9200); these book-proportioned slabs are generated for comparison and are NOT placed by default.'}})
    return parts


def local_frame(part):
    """Pivot = footprint centre at the lowest base Z; local boxes relative to it."""
    xs = [b['rect'][0] for b in part['boxes']] + [b['rect'][2] for b in part['boxes']]
    ys = [b['rect'][1] for b in part['boxes']] + [b['rect'][3] for b in part['boxes']]
    z0 = min(b['z0'] for b in part['boxes'])
    pivot = ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0, z0)
    local = []
    for b in part['boxes']:
        lo = (b['rect'][0] - pivot[0], b['rect'][1] - pivot[1], b['z0'] - pivot[2])
        hi = (b['rect'][2] - pivot[0], b['rect'][3] - pivot[1], b['z1'] - pivot[2])
        local.append((b['name'], lo, hi))
    world = {'min': [min(xs), min(ys), z0], 'max': [max(xs), max(ys), max(b['z1'] for b in part['boxes'])]}
    return pivot, local, world


# ----------------------------------------------------------------------------------
# OBJ export (reviewed legacy adapter convention)
# ----------------------------------------------------------------------------------

def write_obj(path, name, local_boxes):
    lines = ['# Future Mount enclosure part (Lishchno Tidreshu); Unreal legacy OBJ adapter: Y negated, winding reversed', 'o ' + name]
    index = 1
    checks = []
    allv = []
    for part_name, lo, hi in local_boxes:
        vertices, faces = box_tris(lo, hi)
        if volume(vertices, faces) < 0:
            faces = [(a, c, b) for a, b, c in faces]
        keys = [tuple(round(x, 6) for x in p) for p in vertices]
        edges = {}
        allv.extend(vertices)
        lines.append('g ' + part_name)
        for a, b, c in faces:
            for i, j in ((a, b), (b, c), (c, a)):
                key = tuple(sorted((keys[i], keys[j])))
                edges[key] = edges.get(key, 0) + 1
            p, q, r = [(vertices[i][0], -vertices[i][1], vertices[i][2]) for i in (a, c, b)]
            ab = [q[i] - p[i] for i in range(3)]
            ac = [r[i] - p[i] for i in range(3)]
            n = cross(ab, ac)
            length = math.sqrt(sum(x * x for x in ab))
            nl = math.sqrt(sum(x * x for x in n))
            if nl <= 1e-8:
                raise RuntimeError('degenerate triangle in ' + part_name)
            for v in (p, q, r):
                lines.append('v %.6f %.6f %.6f' % v)
            for uv in ((0, 0), (length / 100.0, 0), (sum(ac[i] * ab[i] / length for i in range(3)) / 100.0, nl / length / 100.0)):
                lines.append('vt %.6f %.6f' % uv)
            for _ in range(3):
                lines.append('vn %.6f %.6f %.6f' % tuple(x / nl for x in n))
            lines.append('f ' + ' '.join('%d/%d/%d' % (k, k, k) for k in range(index, index + 3)))
            index += 3
        vol = volume(vertices, faces)
        if not (vol > 0 and all(count == 2 for count in edges.values())):
            raise RuntimeError('part %s is not a closed positive solid' % part_name)
        checks.append({'name': part_name, 'triangles': len(faces), 'closed': True, 'volume_cm3': vol})
    path.write_text('\n'.join(lines) + '\n', encoding='ascii')
    bounds = {'min': [min(p[i] for p in allv) for i in range(3)], 'max': [max(p[i] for p in allv) for i in range(3)]}
    return {'triangles': (index - 1) // 3, 'parts': checks, 'bounds_cm': bounds}


# ----------------------------------------------------------------------------------
# PNG preview (pure python: RGB, zlib) with a 3x5 bitmap font
# ----------------------------------------------------------------------------------

FONT = {
    'A': '010101111101101', 'B': '110101110101110', 'C': '011100100100011', 'D': '110101101101110', 'E': '111100110100111',
    'F': '111100110100100', 'G': '011100101101011', 'H': '101101111101101', 'I': '111010010010111', 'K': '101110100110101',
    'L': '100100100100111', 'M': '101111111101101', 'N': '110101101101101', 'O': '010101101101010', 'P': '110101110100100',
    'R': '110101110110101', 'S': '011100010001110', 'T': '111010010010010', 'U': '101101101101111', 'V': '101101101101010',
    'W': '101101111111101', 'X': '101101010101101', 'Y': '101101010010010', 'Z': '111001010100111', '0': '111101101101111',
    '1': '010110010010111', '2': '111001111100111', '3': '111001111001111', '4': '101101111001001', '5': '111100111001111',
    '6': '111100111101111', '7': '111001001001001', '8': '111101111101111', '9': '111101111001111', ' ': '000000000000000',
    '-': '000000111000000', '.': '000000000000010', '/': '001001010100100', ':': '000010000010000', '(': '010100100100010',
    ')': '010001001001010', '+': '000010111010000', '=': '000111000111000', ',': '000000000010100', '%': '101001010100101',
}


class Canvas:
    def __init__(self, width, height, background=(250, 248, 243)):
        self.w, self.h = width, height
        self.pix = bytearray(background * (width * height))

    def put(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = 3 * (y * self.w + x)
            self.pix[i:i + 3] = bytes(rgb)

    def line(self, x0, y0, x1, y1, rgb, width=1):
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx - dy
        while True:
            for ox in range(-(width // 2), width - width // 2):
                for oy in range(-(width // 2), width - width // 2):
                    self.put(x0 + ox, y0 + oy, rgb)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def polyline(self, points, rgb, width=1, closed=True):
        for i in range(len(points) - (0 if closed else 1)):
            a, b = points[i], points[(i + 1) % len(points)]
            self.line(a[0], a[1], b[0], b[1], rgb, width)

    def fill_rect(self, x0, y0, x1, y1, rgb, alpha=1.0):
        x0, x1 = sorted((int(math.floor(x0)), int(math.ceil(x1))))
        y0, y1 = sorted((int(math.floor(y0)), int(math.ceil(y1))))
        x1, y1 = max(x1, x0 + 1), max(y1, y0 + 1)
        for y in range(max(0, y0), min(self.h, y1)):
            for x in range(max(0, x0), min(self.w, x1)):
                if alpha >= 1.0:
                    self.put(x, y, rgb)
                else:
                    i = 3 * (y * self.w + x)
                    old = self.pix[i:i + 3]
                    self.pix[i:i + 3] = bytes(int(old[k] * (1 - alpha) + rgb[k] * alpha) for k in range(3))

    def fill_polygon(self, points, rgb, alpha=1.0):
        ys = [p[1] for p in points]
        for y in range(max(0, int(math.floor(min(ys)))), min(self.h, int(math.ceil(max(ys))) + 1)):
            xs = []
            n = len(points)
            for i in range(n):
                (x1, y1), (x2, y2) = points[i], points[(i + 1) % n]
                if (y1 <= y < y2) or (y2 <= y < y1):
                    xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                self.fill_rect(xs[j], y, xs[j + 1], y + 1, rgb, alpha)

    def text(self, x, y, string, rgb, scale=2):
        cx = int(x)
        for ch in string.upper():
            glyph = FONT.get(ch, FONT[' '])
            for row in range(5):
                for col in range(3):
                    if glyph[row * 3 + col] == '1':
                        self.fill_rect(cx + col * scale, y + row * scale, cx + (col + 1) * scale, y + (row + 1) * scale, rgb)
            cx += 4 * scale

    def save(self, path):
        raw = b''.join(b'\x00' + bytes(self.pix[3 * y * self.w:3 * (y + 1) * self.w]) for y in range(self.h))

        def chunk(tag, data):
            body = tag + data
            return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xffffffff)
        png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', self.w, self.h, 8, 2, 0, 0, 0))
        png += chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')
        Path(path).write_bytes(png)


def draw_preview(path, view, parts_world, inputs, frame, title, extras):
    """Plan view: X east to the right, Y south downward (north up)."""
    x0, y0, x1, y1 = view
    size = 1600
    margin = 60
    scale = (size - 2 * margin) / max(x1 - x0, y1 - y0)
    canvas = Canvas(size, size + 90)

    def px(x, y):
        return margin + (x - x0) * scale, margin + (y - y0) * scale

    boundary = [px(*p) for p in inputs['boundary']]
    canvas.fill_polygon(boundary, (205, 214, 200), 1.0)
    canvas.polyline(boundary, (60, 90, 60), 2)
    for prot in inputs['protected']:
        poly = [px(*p) for p in prot['polygon']]
        canvas.fill_polygon(poly, (230, 120, 60) if prot['kind'] == 'building' else (240, 190, 120), 1.0)
        canvas.polyline(poly, (150, 50, 20), 2)
    # measured court envelope
    c0, c1 = px(-COURT_HALF, -COURT_HALF), px(COURT_HALF, COURT_HALF)
    canvas.fill_rect(c0[0], c0[1], c1[0], c1[1], (120, 120, 140), 0.35)
    canvas.polyline([c0, (c1[0], c0[1]), c1, (c0[0], c1[1])], (50, 50, 90), 2)
    colours = {'wall': (60, 60, 60), 'gates': (170, 30, 30), 'cheil': (40, 80, 170), 'soreg': (150, 90, 20), 'steps': (20, 130, 80)}
    for part in parts_world:
        for rect in part['worldRects']:
            a, b = px(rect[0], rect[1]), px(rect[2], rect[3])
            canvas.fill_rect(a[0], a[1], max(b[0], a[0] + 1), max(b[1], a[1] + 1), colours[part['group']], 1.0)
    if extras.get('ring500'):
        r = extras['ring500']
        a, b = px(r[0], r[1]), px(r[2], r[3])
        canvas.polyline([a, (b[0], a[1]), b, (a[0], b[1])], (200, 120, 200), 1)
    # scale bar 200 m
    bar = 20000 * scale
    canvas.fill_rect(margin, size + 20, margin + bar, size + 26, (0, 0, 0))
    canvas.text(margin, size + 32, '200 M', (0, 0, 0), 2)
    canvas.text(margin, size + 52, title, (0, 0, 0), 2)
    legend = [('WALL 3000 AMOT', colours['wall']), ('GATES 5', colours['gates']), ('CHEIL', colours['cheil']), ('SOREG', colours['soreg']),
              ('PLATFORM', (205, 214, 200)), ('KOTEL', (230, 120, 60)), ('PLAZA', (240, 190, 120)), ('COURT', (120, 120, 140))]
    lx = margin + 220
    for label, rgb in legend:
        canvas.fill_rect(lx, size + 18, lx + 12, size + 30, rgb)
        canvas.text(lx + 16, size + 22, label, (0, 0, 0), 2)
        lx += 16 + 8 * len(label) + 20
    canvas.text(size - margin - 40, margin - 30, 'N', (0, 0, 0), 3)
    canvas.line(size - margin - 30, margin - 5, size - margin - 30, margin + 40, (0, 0, 0), 2)
    canvas.save(path)


# ----------------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------------

def generate(force=False):
    if (OUT / 'geometry-manifest.json').exists() and not force:
        raise RuntimeError('Frozen generation preserved: %s exists (use --force)' % (OUT / 'geometry-manifest.json'))
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = load_inputs()
    terrain = Terrain()
    frame = enclosure_frame()
    gates = gate_positions(frame)
    ring_parts, ring_dims = build_ring_parts(inputs)
    parts = build_wall_parts(frame, gates, terrain) + build_gate_parts(frame, gates, terrain) + ring_parts + build_step_parts(inputs)

    manifest_meshes = []
    placements = []
    checks = []
    total_triangles = 0
    boundary = inputs['boundary']
    inset_required = inputs['wallCentrelineInsetCm'] + inputs['guardBufferCm']
    for part in parts:
        pivot, local, world = local_frame(part)
        path = OUT / (part['name'] + '.obj')
        info = write_obj(path, part['name'], local)
        total_triangles += info['triangles']
        # world footprint checks
        rects = [b['rect'] for b in part['boxes']]
        relations = [rect_polygon_relation(r, boundary) for r in rects]
        protected_hits = []
        min_protected = None
        for prot in inputs['protected']:
            for r in rects:
                rel, dist = rect_polygon_relation(r, prot['polygon'])
                min_protected = dist if min_protected is None else min(min_protected, dist)
                if rel != 'outside' or dist < prot['bufferCm']:
                    protected_hits.append({'protected': prot['name'], 'box': r, 'relation': rel, 'distanceCm': dist})
        on_platform = part['group'] in ('cheil', 'soreg', 'steps')
        platform_ok = (all(rel == 'inside' and dist >= inset_required for rel, dist in relations) if on_platform
                       else all(rel == 'outside' for rel, dist in relations))
        check = {'mesh': part['name'], 'group': part['group'], 'expectedPlatformRelation': 'inside' if on_platform else 'outside',
                 'platformRelations': [rel for rel, _ in relations], 'minBoundaryDistanceCm': min(d for _, d in relations),
                 'platformCheckPassed': platform_ok, 'protectedPolygonHits': protected_hits, 'minProtectedDistanceCm': min_protected,
                 'protectedCheckPassed': not protected_hits}
        checks.append(check)
        record = {'name': part['name'], 'file': path.name, 'sha256': sha256_of(path), 'triangles': info['triangles'], 'parts': info['parts'],
                  'bounds_cm': info['bounds_cm'], 'group': part['group'], 'materialRole': part['material'], 'source': part['source']}
        manifest_meshes.append(record)
        placement = {'mesh': part['name'], 'group': part['group'], 'materialRole': part['material'], 'location': list(pivot), 'rotation': [0.0, 0.0, 0.0],
                     'scale': [1.0, 1.0, 1.0], 'plannedWorldBoundsCm': world, 'boxesWorldCm': [{'name': b['name'], 'rect': list(b['rect']), 'z0': b['z0'], 'z1': b['z1']} for b in part['boxes']],
                     'zPolicy': ('platform_deck_z0' if on_platform else part['boxes'][0]['ground']['policy']),
                     'placeByDefault': part['group'] != 'steps'}
        if part['group'] in ('wall', 'gates'):
            grounds = [b['ground']['terrain'] for b in part['boxes'] if b['ground']['terrain']]
            placement['terrainSampledZcm'] = ({'min': min(g['min'] for g in grounds), 'max': max(g['max'] for g in grounds)} if grounds else None)
        if part['group'] == 'gates':
            placement['gate'] = part['gate']
            placement['openingCm'] = part['openingCm']
        if part['group'] == 'steps':
            placement['duplicatesMeasuredStairs'] = part['duplicates']
        placements.append(placement)

    # the author's starred 500 x 500 amot soreg ring (p. 363), centred on the court: where would it fall?
    ring500 = (-250 * A, -250 * A, 250 * A, 250 * A)
    ring500_edges = {
        'westEdgeX': ring500[0], 'eastEdgeX': ring500[2], 'northEdgeY': ring500[1], 'southEdgeY': ring500[3],
        'cornersInsidePlatform': [point_in_polygon(c, boundary) for c in rect_corners(ring500)],
        'relationToPlatform': rect_polygon_relation(ring500, boundary)[0],
        'kotelRelation': rect_polygon_relation(ring500, inputs['protected'][0]['polygon'])[0],
    }

    design = {
        'status': 'offline_design_generated_native_pending',
        'generatedBy': 'Scripts/create_mount_enclosure.py',
        'generatorSha256': sha256_of(Path(__file__)),
        'cmPerAmah': A, 'tefachCm': TEFACH,
        'coordinateConvention': 'UE cm: X east, Y south, Z up; measured court centre at the origin; OBJ files carry Y negated and reversed winding (legacy adapter)',
        'inputs': {'architectureManifest': str(ARCHITECTURE_MANIFEST), 'architectureManifestSha256': inputs['architectureManifestSha256'],
                   'platformDesign': str(PLATFORM_DESIGN), 'platformDesignSha256': inputs['platformDesignSha256'],
                   'courtPlatformBoundsCm': inputs['courtPlatformBounds'], 'measuredStairs': inputs['stairs'],
                   'terrain': {'status': terrain.status, 'detail': terrain.detail}},
        'enclosure': {
            'sideAmot': SIDE_AMOT, 'sideCm': SIDE_AMOT * A, 'wallThicknessCm': frame['thicknessCm'], 'wallHeightCm': frame['heightCm'],
            'outerFacesCm': frame['outer'], 'centreCm': [(frame['outer']['xWest'] + frame['outer']['xEast']) / 2, (frame['outer']['yNorth'] + frame['outer']['ySouth']) / 2],
            'orientation': 'axis-aligned with the measured Temple (yaw 0); the book draws the Mount square parallel to the Temple',
            'clearancesAmot': frame['clearancesAmot'],
            'offsetRule': 'West and north clearances 500 / 501 amot from the outer court supporting platform faces (+-8100 cm) per fig. 2\'2 (p. 113); '
                          'east/south follow from the 3000 square (2176 / 2175 instead of the diagram\'s 2149 / 2153 because the measured court '
                          'envelope is 324 amot, the diagram\'s ~351 x 346). Order south > east > north > west preserved (Mishkenei Elyon 196 m.1).',
            'measuredFromOutside': 'Yechezkel 42:15-20 measures the wall from outside (p. 359 "mivachutz"); the 3000 amot are taken as the outer faces',
            'gates': gates,
            'gateBlockAmot': {'pierWidth': GATE_PIER_W_AMOT, 'openingWidth': GATE_OPEN_W_AMOT, 'openingHeight': GATE_OPEN_H_AMOT, 'totalHeight': GATE_TOTAL_H_AMOT, 'depth': WALL_THICK_AMOT},
            'chunksPerSide': CHUNKS_PER_SIDE, 'subBoxMaxCm': SUBBOX_MAX_CM,
            'zPolicyOutsidePlatform': 'Every wall sub-box (<= 25 m) and every gate block: base Z = lowest sampled source-terrain Z - %.0f cm footing, top Z = highest sampled Z + nominal height '
                                      '(stepped wall following the ground; ground read offline from the source DEM triangles, not from native traces). Fallback when the '
                                      'terrain source is absent: base -%.0f, top nominal (recorded).' % (FOOTING_CM, FOOTING_CM),
        },
        'approachRing': dict(ring_dims, cheilWallHeightCm=CHEIL_WALL_HIGH_AMOT * A, soregHeightCm=SOREG_HIGH_CM, slabThicknessCm=SLAB_THICK_CM,
                             zPolicy='on the future platform deck top Z 0 (all footprints verified inside the platform polygon with >= %.0f cm inset)' % inset_required,
                             sequence='gate threshold (X 8600, Z 300) -> measured 12 steps to X 9200 -> 10 amot open cheil (9200..9700) -> cheil wall 1 amah (9700..9750, 10 amot high) -> 10 amot gap (assumption) -> soreg (10250..10275, 10 tefachim)'),
        'ring500Alternative': dict(ring500_edges, note='Author (*) p. 359/363: possibly a soreg ring 500 x 500 amot around the Sanctuary in addition to the 3000 wall. '
                                                       'Not generated: centred on the court it is not contained by the platform polygon (east edge X 12500 lies beyond the '
                                                       'platform edge north of Y -1800); shifting it west would put its west side inside the protected Kotel polygon.'),
        'uncertainties': [
            'Gate positions along the walls are not given by the book (only the count per side); E/N/W gates are set on the Temple axes, the two south gates at thirds.',
            'The 60-amot gate piers and lintel are the author\'s starred suggestion; the book\'s certain data are opening 10 x 50 and thickness 6. Doors are omitted (open).',
            'Soreg distance from the cheil wall is unknown (Rambam/Rosh/Mishkenei Elyon); 10 amot chosen. The soreg is a solid band, not a lattice.',
            'Cheil wall thickness 1 amah is the author\'s study value. Openings in the cheil wall/soreg in front of the E/N/S gates are an assumption (Middos: 13 breaches in the soreg).',
            'West/north clearances are measured from the court supporting platform faces; the book\'s diagram envelope is ~27 amot larger, so east/south clearances differ by ~25 amot.',
            'Wall base follows the current-city DEM (future terrain unknown); the book says the Mount slopes up from all sides to the House (author).',
            'The steps group reproduces the book proportions but duplicates the measured stairs and is not placed by default.',
        ],
        'placements': placements,
        'checks': {'perMesh': checks,
                   'allPlatformChecksPassed': all(c['platformCheckPassed'] for c in checks),
                   'allProtectedChecksPassed': all(c['protectedCheckPassed'] for c in checks),
                   'minProtectedDistanceCmOverAllParts': min(c['minProtectedDistanceCm'] for c in checks),
                   'rule': 'ring parts must lie inside the platform polygon by >= wall inset 110 + guard 201 cm; wall/gate parts must lie entirely outside it (they stand on terrain/city); no part may enter or come within the no-edit buffer of the Western Wall or plaza polygons'},
        'totals': {'meshes': len(parts), 'triangles': total_triangles, 'byGroup': {g: sum(1 for p in parts if p['group'] == g) for g in ('wall', 'gates', 'cheil', 'soreg', 'steps')}},
    }
    manifest = {
        'status': 'OFFLINE_SOURCE_EXPORTED_NATIVE_PENDING', 'namespace': NAMESPACE, 'meshFolder': NAMESPACE + '/Meshes',
        'generatorSha256': design['generatorSha256'], 'architectureManifestSha256': inputs['architectureManifestSha256'],
        'platformDesignSha256': inputs['platformDesignSha256'], 'totalTriangles': total_triangles, 'meshes': manifest_meshes,
        'objConvention': 'per-face vertices; file Y = -canonical Y and winding reversed; FBX/OBJ importer reflects Y back (same as DoorsParochesV1/PalmReliefV1)',
        'materialRoles': {STONE: 'canonical stone of the measured architecture', PAVING: 'canonical paving (cheil slab)', CEDAR: 'canonical cedar (wooden soreg lattice, simplified)'},
    }
    (OUT / 'enclosure-design.json').write_text(json.dumps(design, indent=2) + '\n', encoding='utf-8')
    (OUT / 'geometry-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

    parts_world = [{'group': p['group'], 'worldRects': [b['rect'] for b in p['boxes']]} for p in parts if p['group'] != 'steps']
    o = frame['outer']
    pad = 6000.0
    draw_preview(OUT / 'preview-plan.png', (o['xWest'] - pad, o['yNorth'] - pad, o['xEast'] + pad, o['ySouth'] + pad), parts_world, inputs, frame,
                 'ENCLOSURE 3000 AMOT OVER PLATFORM AND CITY DATUM', {})
    bx = [p[0] for p in boundary]
    by = [p[1] for p in boundary]
    span = max(max(bx) - min(bx), max(by) - min(by)) + 4000
    cx, cy = (max(bx) + min(bx)) / 2, (max(by) + min(by)) / 2
    draw_preview(OUT / 'preview-platform.png', (cx - span / 2, cy - span / 2, cx + span / 2, cy + span / 2), parts_world, inputs, frame,
                 'PLATFORM, KOTEL, CHEIL AND SOREG RING (500 RING DASHED)', {'ring500': ring500})
    return design, manifest


if __name__ == '__main__':
    design, manifest = generate(force='--force' in sys.argv)
    summary = {'meshes': design['totals']['meshes'], 'triangles': design['totals']['triangles'], 'byGroup': design['totals']['byGroup'],
               'terrain': design['inputs']['terrain']['status'], 'platformChecks': design['checks']['allPlatformChecksPassed'],
               'protectedChecks': design['checks']['allProtectedChecksPassed'], 'minProtectedDistanceCm': design['checks']['minProtectedDistanceCmOverAllParts'],
               'outerFacesCm': design['enclosure']['outerFacesCm'], 'clearancesAmot': design['enclosure']['clearancesAmot'],
               'ring500': design['ring500Alternative']['relationToPlatform'], 'output': str(OUT)}
    print(json.dumps(summary, indent=2))
