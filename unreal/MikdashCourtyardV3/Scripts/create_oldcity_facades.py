"""OldCityFacadesV1 - original Old City facade detail shells and authored infill massing.

AUTHORED_OFFLINE_SOURCE - this module never imports `unreal`, never touches Content/,
never opens a map. It writes OBJ batches, a manifest and a plan-view PNG under
SourceAssets/context-review/OldCityFacadesV1/. Scripts/release_oldcity_facades.py is the
separate guarded native importer/placer.

WHY
---
The imported Jerusalem context (1499 `SM_JerusalemBuildings_Grid_*` meshes, 11400
connected components, 242764 triangles) is a set of flat-topped extruded OSM footprints
with a triplanar limestone material. At street level and from the air the Old City reads as
untextured boxes. This generator adds:

  * per-building facade DETAIL SHELLS - recessed windows (1.0 x 1.8 m, ~30% arched),
    a recessed street-level door, a cornice, a string band, a roof parapet, corner quoins
    and rooftop clutter (small dome ~8%, water tank / stair head ~30%);
  * authored INFILL buildings (2-3 storeys, block and courtyard plans) in the empty parts
    of the walled city so built coverage per 100 m cell approaches the modern Old City.

Every shell surface starts 6 cm OUTSIDE the existing extruded box (SHELL_STANDOFF_CM), so
no shell face is ever coplanar with an imported face and nothing z-fights. A "recessed"
window is a picture-frame solid standing proud of the wall: the opening looks through the
frame onto the original wall face, i.e. a real 14 cm recess with no boolean on the source.

SOURCE OF THE FOOTPRINTS (no mesh slicing needed)
-------------------------------------------------
Per-building polygons were located rather than derived. The frozen buildings.fbx was
exported by Workspace/output/cloud-unreal-v3/context-review/export_buildings.py from
Workspace/output/architecture-review/jerusalem-meshes.json, which was itself produced by
export-jerusalem.ts from `buildJerusalem()` over
Workspace/mikdash-walkthrough/public/context/jerusalem.json. That JSON still holds every
OSM feature as an explicit polygon: 11437 `kind=="building"` point rings, 5944 roads,
12 wall chains, in amot (0.5 m per amah), axes x=east, y=up, z=south.

This module re-implements `buildJerusalem`'s building pass EXACTLY (hash, terrain
`heightAt`, the market blend, `templeMask`, the 650-amah span cut, the height rule and the
three named overrides), so the reconstructed box for every building is the same box that is
already in the level. The reconstruction is then CHECKED against the frozen
buildings-manifest.json component records: each of the 11400 connected components carries
`sourceBoundsAmos`, and `verify_against_frozen_manifest()` requires that at least
MIN_COMPONENT_MATCH of them are reproduced to <= BOUNDS_TOLERANCE_AMOT. Components that are
unions of touching footprints legitimately fail to match a single polygon and are reported,
not hidden. Mesh slicing is therefore NOT used; that fallback is recorded in `limitations`
only.

ALIGNMENT (already baked in the level; applied here, never applied twice)
------------------------------------------------------------------------
    UE_cm = ((x_amot + 17.509700315687695) * 50,
             (z_amot -  0.5513496449385334) * 50,
             y_amot * 50)

i.e. UE X = east cm, UE Y = south cm, UE Z = up cm. This is the same constant pair
(TX, TZ) that export_buildings.py baked, and the same formula recorded in
SourceAssets/visual-review/mount-platform-design.json `sourceData.alignment`. A 100 m cell
key therefore equals floor(UE_cm / 10000) on both axes, which reproduces the existing
`Grid_<token>_<token>` bucket names exactly, so a facade batch lines up with the bucket
mesh it decorates.

OBJ ADAPTER CONVENTION (project standard)
-----------------------------------------
Canonical vertices are UE cm. Every OBJ is written with Y REFLECTED and triangle winding
REVERSED, the adapter used by create_sanctuary_doors.export /
SourceAssets/sanctuary-detail/DoorsParochesV1/geometry-manifest.json and by the keilim,
keruvim, Aron and relief imports. The legacy OBJ importer reflects Y back, so the imported
StaticMesh must reproduce `canonicalBoundsCm`; the release script asserts that.
Canonical solids are built closed and are flipped when needed so the canonical signed
volume (sum dot(A, cross(B,C))/6) is POSITIVE, exactly as the doors exporter does.
Each OBJ carries a single `o` object and NO `g` groups, because the OBJ importer creates one
material slot per `g` group (the SM_KeruvimStudyV1 236-slot lesson); one group means one
slot per batch.

BATCHING AND RESUME
-------------------
One facade OBJ and (where infill exists) one infill OBJ per 100 m cell, so actor counts stay
in the low hundreds instead of thousands. Cells are balanced into CELL_GROUPS groups by
triangle count; `groups` in the manifest is what release_oldcity_facades.py -FacadesGroups
consumes, so a 16 GB machine can import the set in several runs.

LIMITS (also written into the manifest)
---------------------------------------
Windows, arches, quoins, cornices, roof clutter and every infill building are INVENTED
massing in the style of the modern Old City. They are not surveyed, not photogrammetric and
not a claim about any particular building. Nothing here is halachic. No visual, collision,
cook or packaged acceptance is established by this script.

Usage (no engine needed):
    "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" \
        Scripts/create_oldcity_facades.py [--force] [--no-preview]
"""

import hashlib
import json
import math
import random
import struct
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------- paths
ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
OUT = ROOT / 'SourceAssets' / 'context-review' / 'OldCityFacadesV1'
OBJ_DIR = OUT / 'obj'
MANIFEST_PATH = OUT / 'facades-manifest.json'
PREVIEW_PATH = OUT / 'preview-plan.png'

WORKSPACE = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace')
SOURCE_JSON = WORKSPACE / 'mikdash-walkthrough' / 'public' / 'context' / 'jerusalem.json'
SOURCE_JSON_SHA = '76a2b76c0d97f45db7e532b3adbe8b58c02956fa0d3de73db71e31e097ea6463'
FROZEN_MANIFEST = WORKSPACE / 'output' / 'cloud-unreal-v3' / 'context-review' / 'buildings-manifest.json'
FROZEN_FBX_SHA = '271bc9b4e1297421a33dde0b00172ad6111decabdb683e05267d4b972aca5408'
DESIGN_JSON = ROOT / 'SourceAssets' / 'visual-review' / 'mount-platform-design.json'

# --------------------------------------------------------------- source constants
# Identical to Workspace/mikdash-walkthrough/lib/mikdash/{jerusalem,market}.ts
MARKET_X, MARKET_Z = -1750.0, 400.0
TX = 17.509700315687695
TZ = -0.5513496449385334
AMAH_CM = 50.0                      # 0.5 m per amah, 100 cm per m
METRES_PER_AMAH = 0.5

# Old City wall ring: explicit OSM chain (id, reversed) verified closed at generation time.
OLD_CITY_CHAIN = [(391433907, False), (137726904, False), (391433919, False),
                  (391433915, False), (511655207, False), (391433911, False),
                  (1080613976, False)]
CHAIN_GAP_TOLERANCE_AMOT = 30.0     # one 13.5 m mapped gap at the citadel
OLD_CITY_MARGIN_CM = 6000.0         # 60 m outside the walls still gets facades

# --------------------------------------------------------------- design constants
SHELL_STANDOFF_CM = 6.0             # never closer than this to an imported face
CELL_CM = 10000.0                   # 100 m buckets, same as the imported meshes
CELL_GROUPS = 8

FLOOR_CM = 320.0
WINDOW_W, WINDOW_H = 100.0, 180.0
WINDOW_FRAME_CM = 14.0
WINDOW_PROUD_CM = 14.0              # frame face at standoff + proud => 14 cm reveal
WINDOW_SILL_CM = 90.0               # above each floor line
WINDOW_PITCH_CM = 350.0             # one opening per 3-4 m of facade
WINDOW_PITCH_MAX_CM = 1200.0        # relaxation limit when a building is over budget
ARCH_FRACTION = 0.30
ARCH_SEGMENTS = 3
DOOR_W, DOOR_H = 120.0, 230.0
DOOR_FRAME_CM = 18.0
DOOR_PROUD_CM = 20.0
MIN_WINDOW_EDGE_CM = 260.0
PARTY_WALL_PROBE_CM = 45.0          # outward probe; inside a neighbour => party wall

CORNICE_DROP_CM, CORNICE_HEIGHT_CM, CORNICE_PROUD_CM = 52.0, 28.0, 22.0
BAND_DROP_CM, BAND_HEIGHT_CM, BAND_PROUD_CM = 16.0, 14.0, 12.0
PARAPET_HEIGHT_CM, PARAPET_PROUD_CM, PARAPET_INSET_CM = 70.0, 16.0, 30.0
QUOIN_CORNERS = 4
QUOIN_BLOCKS = 4
QUOIN_RUN_CM, QUOIN_HEIGHT_CM, QUOIN_PROUD_CM = 80.0, 55.0, 10.0
QUOIN_BASE_CM, QUOIN_PITCH_CM = 25.0, 72.0

DOME_FRACTION = 0.08
TANK_FRACTION = 0.30
STAIRHEAD_FRACTION = 0.30

MAX_TRIS_PER_BUILDING = 4000
MAX_TOTAL_TRIS = 6_000_000

# --------------------------------------------------------------- infill constants
INFILL_TARGET_COVERAGE = 0.60
INFILL_MAX_PER_CELL = 120
INFILL_PASSES_PER_CELL = 16         # each pass re-reads the free raster
INFILL_SEEDS_PER_PASS = 2600        # candidate seeds drawn from the free raster per pass
INFILL_MIN_SIDE_CM = 330.0
INFILL_MIN_AREA_CM2 = 160000.0      # 16 m2 minimum floor plate
INFILL_STREET_BUFFER_CM = 600.0     # 6 m clear of every street polyline
INFILL_WALL_BUFFER_CM = 600.0       # clear of the city wall chain itself
INFILL_EXISTING_GAP_CM = 30.0       # Old City houses abut; only real overlap is refused
INFILL_RASTER_MARGIN_CM = 60.0      # half a raster cell, so the raster and the exact test agree
INFILL_PROTECTED_BUFFER_CM = 300.0  # on top of the design's own 200 cm no-edit buffer
INFILL_MIN_CM, INFILL_MAX_CM = 550.0, 2400.0
INFILL_COURTYARD_FRACTION = 0.35
INFILL_COURT_WING_CM = 500.0
INFILL_STOREYS = (2, 3)
INFILL_TAG = 'AUTHORED_INFILL'

BOUNDS_TOLERANCE_AMOT = 0.05
MIN_COMPONENT_MATCH = 0.90

PREVIEW_PX = 1800


# =========================================================================== util
def sha256_of(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def js_hash(n):
    """Exactly the three.js-side `hash` in jerusalem.ts."""
    value = math.sin(n * 127.1 + 311.7) * 43758.5453123
    return value - math.floor(value)


def js_parse_float(text):
    """JS parseFloat: leading numeric prefix, None where JS would give NaN."""
    if text is None:
        return None
    text = str(text).strip()
    index, seen_digit, seen_dot, seen_exp = 0, False, False, False
    if index < len(text) and text[index] in '+-':
        index += 1
    while index < len(text):
        char = text[index]
        if char.isdigit():
            seen_digit = True
        elif char == '.' and not seen_dot and not seen_exp:
            seen_dot = True
        elif char in 'eE' and seen_digit and not seen_exp:
            nxt = text[index + 1] if index + 1 < len(text) else ''
            if nxt.isdigit() or nxt in '+-':
                seen_exp = True
                index += 1
            else:
                break
        elif char in '+-' and index > 0 and text[index - 1] in 'eE':
            pass
        else:
            break
        index += 1
    if not seen_digit:
        return None
    try:
        return float(text[:index])
    except ValueError:
        return None


def clamp(value, low, high):
    return low if value < low else (high if value > high else value)


def smoothstep(x, low, high):
    if x <= low:
        return 0.0
    if x >= high:
        return 1.0
    t = (x - low) / (high - low)
    return t * t * (3.0 - 2.0 * t)


def polygon_area(points):
    total = 0.0
    count = len(points)
    for index in range(count):
        ax, ay = points[index]
        bx, by = points[(index + 1) % count]
        total += ax * by - bx * ay
    return total * 0.5


def point_in_polygon(x, y, points):
    inside = False
    count = len(points)
    j = count - 1
    for i in range(count):
        ax, ay = points[i]
        bx, by = points[j]
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
        j = i
    return inside


def point_segment_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if length2 <= 1e-9:
        return math.hypot(px - ax, py - ay)
    t = clamp(((px - ax) * dx + (py - ay) * dy) / length2, 0.0, 1.0)
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def segments_intersect(p1, p2, p3, p4):
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2 = orient(p3, p4, p1), orient(p3, p4, p2)
    d3, d4 = orient(p1, p2, p3), orient(p1, p2, p4)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def ensure_ccw(points):
    return points if polygon_area(points) > 0 else points[::-1]


def dedupe_ring(points, epsilon=1.0):
    out = []
    for point in points:
        if not out or math.hypot(point[0] - out[-1][0], point[1] - out[-1][1]) > epsilon:
            out.append(point)
    while len(out) > 3 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= epsilon:
        out.pop()
    return out


def _edge_normal(a, b):
    """Outward normal of edge a->b for a CCW ring in the canonical (X, Y) plane."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return (0.0, 0.0)
    return (dy / length, -dx / length)


def offset_ring(points, distance):
    """Outward miter offset of a CCW ring; miters are clamped at sharp corners."""
    count = len(points)
    out = []
    for index in range(count):
        prev = points[index - 1]
        here = points[index]
        nxt = points[(index + 1) % count]
        n1 = _edge_normal(prev, here)
        n2 = _edge_normal(here, nxt)
        bx, by = n1[0] + n2[0], n1[1] + n2[1]
        length = math.hypot(bx, by)
        if length < 1e-6:
            bx, by, length = n2[0], n2[1], 1.0
        bx, by = bx / length, by / length
        cosine = bx * n2[0] + by * n2[1]
        scale = distance / cosine if cosine > 0.25 else distance * 4.0
        out.append((here[0] + bx * scale, here[1] + by * scale))
    return out


class Grid2D:
    """Uniform bucket index for segment / polygon proximity queries."""

    def __init__(self, cell):
        self.cell = float(cell)
        self.buckets = {}

    def _keys(self, minx, miny, maxx, maxy):
        cell = self.cell
        for ix in range(int(math.floor(minx / cell)), int(math.floor(maxx / cell)) + 1):
            for iy in range(int(math.floor(miny / cell)), int(math.floor(maxy / cell)) + 1):
                yield (ix, iy)

    def insert(self, minx, miny, maxx, maxy, payload):
        for key in self._keys(minx, miny, maxx, maxy):
            self.buckets.setdefault(key, []).append(payload)

    def query(self, minx, miny, maxx, maxy):
        seen, out = set(), []
        for key in self._keys(minx, miny, maxx, maxy):
            for payload in self.buckets.get(key, ()):
                marker = id(payload)
                if marker not in seen:
                    seen.add(marker)
                    out.append(payload)
        return out


# ==================================================== source reconstruction (TS parity)
class CitySource:
    """Re-implementation of buildJerusalem()'s terrain and building pass."""

    def __init__(self, data):
        self.data = data
        terrain = data['terrain']
        self.size = int(terrain['size'])
        self.step = float(terrain['step'])
        self.origin = float(terrain['origin'])
        raw = terrain['heights']
        mi = int(round((MARKET_X - self.origin) / self.step))
        mj = int(round((MARKET_Z - self.origin) / self.step))
        market_level = raw[mj * self.size + mi]
        heights = []
        for index, height in enumerate(raw):
            x = self.origin + (index % self.size) * self.step
            z = self.origin + (index // self.size) * self.step
            market_distance = max(abs(x - MARKET_X) / 60.0, abs(z - MARKET_Z) / 48.0)
            if market_distance < 1.6:
                t = smoothstep(market_distance, 1.0, 1.6)
                heights.append(market_level + (height - market_level) * t)
            else:
                heights.append(height * smoothstep(max(abs(x), abs(z)), 260.0, 360.0) - 0.05)
        self.heights = heights

    def height_at(self, x, z):
        """Two-triangle interpolation, matching the terrain mesh (not bilinear)."""
        size, step, origin, heights = self.size, self.step, self.origin, self.heights
        u = clamp((x - origin) / step, 0.0, size - 1.001)
        v = clamp((z - origin) / step, 0.0, size - 1.001)
        i, j = int(u), int(v)
        a, b = u - i, v - j
        h00 = heights[j * size + i]
        h10 = heights[j * size + i + 1]
        h01 = heights[(j + 1) * size + i]
        h11 = heights[(j + 1) * size + i + 1]
        if a + b <= 1.0:
            return h00 + (h10 - h00) * a + (h01 - h00) * b
        return h11 + (h01 - h11) * (1.0 - a) + (h10 - h11) * (1.0 - b)

    @staticmethod
    def temple_mask(x, z, pad=184.0):
        return (abs(x) < pad and abs(z) < pad) or (abs(x - MARKET_X) < 55.0 and abs(z - MARKET_Z) < 40.0)

    def buildings(self):
        """Every footprint that buildJerusalem() actually extrudes, in source amot."""
        kept, skipped = [], 0
        for feature in self.data['features']:
            if feature.get('kind') != 'building':
                continue
            points = feature['points'][:-1]
            if len(points) < 3:
                skipped += 1
                continue
            xs = [p[0] for p in points]
            zs = [p[1] for p in points]
            cx = (min(xs) + max(xs)) / 2.0
            cz = (min(zs) + max(zs)) / 2.0
            if self.temple_mask(cx, cz, 255.0) or any(self.temple_mask(p[0], p[1], 250.0) for p in points):
                skipped += 1
                continue
            span = max(max(xs) - min(xs), max(zs) - min(zs))
            if span > 650.0:
                skipped += 1
                continue
            tags = feature.get('tags') or {}
            name = tags.get('name:en') or tags.get('name') or ''
            is_old_city = -1900.0 < cx < 200.0 and -950.0 < cz < 950.0
            height = js_parse_float(tags.get('height'))
            height = height * 2.0 if height else None
            if not height:
                levels = js_parse_float(tags.get('building:levels'))
                height = levels * 6.0 if levels else None
            if not height:
                height = ((2.0 if is_old_city else 3.0) + math.floor(js_hash(feature['id']) * 2.0)) * 6.0
            if name == 'Hurva Synagogue' or name == 'YMCA':
                height = 28.0
            if 'Brigham Young' in name:
                height = 42.0
            height = clamp(height, 5.0, 180.0)
            base = min(self.height_at(p[0], p[1]) for p in points)
            kept.append({
                'id': feature['id'], 'name': name, 'points': points, 'centre': (cx, cz),
                'span': span, 'height': height, 'base': base, 'isOldCity': is_old_city,
                'tags': tags,
            })
        return kept, skipped

    def polylines(self, kind):
        return [(feature['id'], feature['points']) for feature in self.data['features']
                if feature.get('kind') == kind and len(feature['points']) >= 2]


def ue_xy(x_amot, z_amot):
    return ((x_amot + TX) * AMAH_CM, (z_amot + TZ) * AMAH_CM)


def ue_z(y_amot):
    return y_amot * AMAH_CM


def cell_token(value):
    return ('N' if value < 0 else 'P') + str(abs(int(value))).zfill(3)


def cell_key_of(x_cm, y_cm):
    return (int(math.floor(x_cm / CELL_CM)), int(math.floor(y_cm / CELL_CM)))


def cell_name(key):
    return 'Grid_%s_%s' % (cell_token(key[0]), cell_token(key[1]))


def verify_against_frozen_manifest(records):
    """Prove the reconstruction is the geometry already in the level.

    Each frozen connected component carries `sourceBoundsAmos` in the raw three.js
    order (east, up, south). A reconstructed building's box is
    (min x, base, min z) .. (max x, base + height, max z) in the same order.
    """
    frozen = json.loads(FROZEN_MANIFEST.read_text(encoding='utf-8-sig'))
    if frozen.get('fbxSha256') != FROZEN_FBX_SHA:
        raise RuntimeError('buildings-manifest.json is not the reviewed FBX revision')
    components = frozen['components']
    index = {}
    for component in components:
        box = component['sourceBoundsAmos']
        key = (round(box['min'][0], 1), round(box['min'][2], 1), round(box['max'][0], 1), round(box['max'][2], 1))
        index.setdefault(key, []).append(component)
    matched, unmatched, worst = 0, [], 0.0
    used = set()
    for record in records:
        xs = [p[0] for p in record['points']]
        zs = [p[1] for p in record['points']]
        want = [min(xs), record['base'], min(zs), max(xs), record['base'] + record['height'], max(zs)]
        key = (round(want[0], 1), round(want[2], 1), round(want[3], 1), round(want[5], 1))
        best = None
        for component in index.get(key, ()):
            if component['componentId'] in used:
                continue
            box = component['sourceBoundsAmos']
            have = [box['min'][0], box['min'][1], box['min'][2], box['max'][0], box['max'][1], box['max'][2]]
            error = max(abs(a - b) for a, b in zip(want, have))
            if best is None or error < best[0]:
                best = (error, component)
        if best is not None and best[0] <= BOUNDS_TOLERANCE_AMOT:
            matched += 1
            used.add(best[1]['componentId'])
            worst = max(worst, best[0])
        else:
            unmatched.append(record['id'])
    ratio = matched / float(len(records)) if records else 0.0
    result = {
        'frozenManifest': str(FROZEN_MANIFEST),
        'frozenFbxSha256': frozen['fbxSha256'],
        'frozenComponentCount': len(components),
        'reconstructedBuildings': len(records),
        'exactBoxMatches': matched,
        'matchRatio': round(ratio, 6),
        'worstMatchedBoundsErrorAmot': worst,
        'unmatchedSampleOsmIds': unmatched[:20],
        'unmatchedCount': len(unmatched),
        'note': ('Unmatched footprints are almost all members of a connected component that '
                 'welds two or more touching OSM footprints into one union; the frozen manifest '
                 'stores the union box, not the individual footprint box.'),
    }
    if ratio < MIN_COMPONENT_MATCH:
        raise RuntimeError('Reconstruction matches only %.4f of the frozen components; '
                           'refusing to author detail against an unproven footprint set' % ratio)
    return result


def old_city_ring(source):
    """Closed Old City wall ring in canonical UE cm, chained from the OSM wall ways."""
    walls = {osm_id: points for osm_id, points in source.polylines('wall')}
    ring, gaps = [], []
    for osm_id, reverse in OLD_CITY_CHAIN:
        if osm_id not in walls:
            raise RuntimeError('Old City wall way %d missing from the source' % osm_id)
        points = walls[osm_id][::-1] if reverse else list(walls[osm_id])
        if ring:
            gap = math.hypot(ring[-1][0] - points[0][0], ring[-1][1] - points[0][1])
            if gap > CHAIN_GAP_TOLERANCE_AMOT:
                raise RuntimeError('Wall chain break of %.2f amot before way %d' % (gap, osm_id))
            gaps.append({'osmId': osm_id, 'gapAmot': gap})
            ring.extend(points[1:])
        else:
            ring.extend(points)
    closure = math.hypot(ring[-1][0] - ring[0][0], ring[-1][1] - ring[0][1])
    if closure > 1e-6:
        raise RuntimeError('Old City wall chain does not close (%.4f amot)' % closure)
    ring.pop()
    ring_cm = ensure_ccw([ue_xy(x, z) for x, z in ring])
    area_m2 = abs(polygon_area(ring_cm)) / 10000.0
    if not 700000.0 < area_m2 < 1050000.0:
        raise RuntimeError('Chained ring area %.0f m2 is not the ~0.9 km2 Old City' % area_m2)
    return ring_cm, area_m2, gaps


# ===================================================================== geometry
class Solid:
    """One closed canonical solid; faces are flipped so the signed volume is positive."""

    __slots__ = ('vertices', 'faces')

    def __init__(self):
        self.vertices = []
        self.faces = []

    def add(self, point):
        self.vertices.append(point)
        return len(self.vertices) - 1

    def quad(self, a, b, c, d):
        self.faces.append((a, b, c))
        self.faces.append((a, c, d))

    def fan(self, loop):
        for index in range(1, len(loop) - 1):
            self.faces.append((loop[0], loop[index], loop[index + 1]))

    def volume(self):
        vertices = self.vertices
        total = 0.0
        for a, b, c in self.faces:
            ax, ay, az = vertices[a]
            bx, by, bz = vertices[b]
            cx, cy, cz = vertices[c]
            total += (ax * (by * cz - bz * cy)
                      + ay * (bz * cx - bx * cz)
                      + az * (bx * cy - by * cx))
        return total / 6.0

    def orient(self):
        """Positive canonical volume, like create_sanctuary_doors.export."""
        value = self.volume()
        if value < 0.0:
            self.faces = [(a, c, b) for a, b, c in self.faces]
            value = -value
        return value


def prism(loop_xy, z0, z1):
    """Solid prism over a closed ring (any convexity for sides; caps are fans)."""
    solid = Solid()
    count = len(loop_xy)
    bottom = [solid.add((x, y, z0)) for x, y in loop_xy]
    top = [solid.add((x, y, z1)) for x, y in loop_xy]
    for index in range(count):
        nxt = (index + 1) % count
        solid.quad(bottom[index], bottom[nxt], top[nxt], top[index])
    solid.fan(top)
    solid.fan(bottom[::-1])
    solid.orient()
    return solid


def annulus_prism(outer_xy, inner_xy, z0, z1):
    """Closed band between two corresponding rings; safe for concave footprints."""
    if len(outer_xy) != len(inner_xy):
        raise ValueError('annulus_prism needs matching ring lengths')
    solid = Solid()
    count = len(outer_xy)
    o0 = [solid.add((x, y, z0)) for x, y in outer_xy]
    o1 = [solid.add((x, y, z1)) for x, y in outer_xy]
    i0 = [solid.add((x, y, z0)) for x, y in inner_xy]
    i1 = [solid.add((x, y, z1)) for x, y in inner_xy]
    for index in range(count):
        nxt = (index + 1) % count
        solid.quad(o0[index], o0[nxt], o1[nxt], o1[index])
        solid.quad(i0[nxt], i0[index], i1[index], i1[nxt])
        solid.quad(o1[index], o1[nxt], i1[nxt], i1[index])
        solid.quad(o0[nxt], o0[index], i0[index], i0[nxt])
    solid.orient()
    return solid


class WallFrame:
    """Local frame on one facade edge: s along the wall, d outward, z up (canonical cm)."""

    __slots__ = ('ox', 'oy', 'ux', 'uy', 'nx', 'ny', 'length')

    def __init__(self, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        self.length = math.hypot(dx, dy)
        if self.length < 1e-9:
            raise ValueError('degenerate wall edge')
        self.ux, self.uy = dx / self.length, dy / self.length
        self.nx, self.ny = self.uy, -self.ux      # outward for a CCW ring
        self.ox, self.oy = a[0], a[1]

    def point(self, s, d, z):
        return (self.ox + self.ux * s + self.nx * d,
                self.oy + self.uy * s + self.ny * d,
                z)


def frame_profile_rect(s0, s1, z0, z1, width):
    outer = [(s0, z0), (s1, z0), (s1, z1), (s0, z1)]
    inner = [(s0 + width, z0 + width), (s1 - width, z0 + width),
             (s1 - width, z1 - width), (s0 + width, z1 - width)]
    return outer, inner


def frame_profile_arch(s0, s1, z0, z1, width, segments=ARCH_SEGMENTS):
    """Round-headed opening: straight jambs to the springing, then a semicircular head."""
    cx = (s0 + s1) / 2.0
    radius = (s1 - s0) / 2.0
    spring = z1 - radius
    if spring <= z0 + width * 2.0 or radius <= width * 1.6:
        return frame_profile_rect(s0, s1, z0, z1, width)
    outer = [(s0, z0), (s1, z0)]
    inner = [(s0 + width, z0 + width), (s1 - width, z0 + width)]
    inner_radius = radius - width
    for step in range(segments + 1):
        angle = math.pi * step / segments
        cosine, sine = math.cos(angle), math.sin(angle)
        outer.append((cx + radius * cosine, spring + radius * sine))
        inner.append((cx + inner_radius * cosine, spring + inner_radius * sine))
    return outer, inner


def opening_solid(frame, s0, s1, z0, z1, width, d0, d1, arched):
    """Picture-frame solid standing proud of the wall: the hole reads as a recess."""
    profile_outer, profile_inner = (frame_profile_arch if arched else frame_profile_rect)(
        s0, s1, z0, z1, width)
    solid = Solid()
    count = len(profile_outer)
    o0 = [solid.add(frame.point(s, d0, z)) for s, z in profile_outer]
    o1 = [solid.add(frame.point(s, d1, z)) for s, z in profile_outer]
    i0 = [solid.add(frame.point(s, d0, z)) for s, z in profile_inner]
    i1 = [solid.add(frame.point(s, d1, z)) for s, z in profile_inner]
    for index in range(count):
        nxt = (index + 1) % count
        solid.quad(o0[index], o0[nxt], o1[nxt], o1[index])
        solid.quad(i0[nxt], i0[index], i1[index], i1[nxt])
        solid.quad(o1[index], o1[nxt], i1[nxt], i1[index])
        solid.quad(o0[nxt], o0[index], i0[index], i0[nxt])
    solid.orient()
    return solid


def frame_box(frame, s0, s1, d0, d1, z0, z1):
    solid = Solid()
    bottom = [solid.add(frame.point(s, d, z0)) for s, d in ((s0, d0), (s1, d0), (s1, d1), (s0, d1))]
    top = [solid.add(frame.point(s, d, z1)) for s, d in ((s0, d0), (s1, d0), (s1, d1), (s0, d1))]
    for index in range(4):
        nxt = (index + 1) % 4
        solid.quad(bottom[index], bottom[nxt], top[nxt], top[index])
    solid.fan(top)
    solid.fan(bottom[::-1])
    solid.orient()
    return solid


def regular_ring(cx, cy, radius, sides, phase=0.0):
    return [(cx + radius * math.cos(phase + 2.0 * math.pi * i / sides),
             cy + radius * math.sin(phase + 2.0 * math.pi * i / sides)) for i in range(sides)]


def dome_solid(cx, cy, z_base, drum_radius, drum_height, rings=3, sides=10):
    """Small plastered dome on a low drum: the Old City roofscape signature."""
    solid = Solid()
    base = [solid.add((x, y, z_base)) for x, y in regular_ring(cx, cy, drum_radius, sides)]
    drum = [solid.add((x, y, z_base + drum_height)) for x, y in regular_ring(cx, cy, drum_radius, sides)]
    for index in range(sides):
        nxt = (index + 1) % sides
        solid.quad(base[index], base[nxt], drum[nxt], drum[index])
    solid.fan(base[::-1])
    previous = drum
    for ring in range(1, rings + 1):
        angle = (math.pi / 2.0) * ring / rings
        radius = drum_radius * math.cos(angle)
        z = z_base + drum_height + drum_radius * math.sin(angle)
        if ring == rings:
            apex = solid.add((cx, cy, z))
            for index in range(sides):
                solid.faces.append((previous[index], previous[(index + 1) % sides], apex))
            break
        current = [solid.add((x, y, z)) for x, y in regular_ring(cx, cy, radius, sides)]
        for index in range(sides):
            nxt = (index + 1) % sides
            solid.quad(previous[index], previous[nxt], current[nxt], current[index])
        previous = current
    solid.orient()
    return solid


def cylinder_solid(cx, cy, z0, z1, radius, sides=8):
    solid = Solid()
    bottom = [solid.add((x, y, z0)) for x, y in regular_ring(cx, cy, radius, sides)]
    top = [solid.add((x, y, z1)) for x, y in regular_ring(cx, cy, radius, sides)]
    for index in range(sides):
        nxt = (index + 1) % sides
        solid.quad(bottom[index], bottom[nxt], top[nxt], top[index])
    solid.fan(top)
    solid.fan(bottom[::-1])
    solid.orient()
    return solid


def oriented_box(cx, cy, z0, z1, half_x, half_y, yaw):
    cosine, sine = math.cos(yaw), math.sin(yaw)
    corners = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        lx, ly = sx * half_x, sy * half_y
        corners.append((cx + lx * cosine - ly * sine, cy + lx * sine + ly * cosine))
    return prism(ensure_ccw(corners), z0, z1)


# ============================================================== facade authoring
def approximate_inradius(loop, cx, cy):
    best = None
    count = len(loop)
    for index in range(count):
        a = loop[index]
        b = loop[(index + 1) % count]
        distance = point_segment_distance(cx, cy, a[0], a[1], b[0], b[1])
        if best is None or distance < best:
            best = distance
    return best or 0.0


def edge_is_party_wall(midpoint, normal, neighbours):
    probe = (midpoint[0] + normal[0] * PARTY_WALL_PROBE_CM,
             midpoint[1] + normal[1] * PARTY_WALL_PROBE_CM)
    for neighbour in neighbours:
        box = neighbour['boxCm']
        if box[0] - 1.0 <= probe[0] <= box[2] + 1.0 and box[1] - 1.0 <= probe[1] <= box[3] + 1.0:
            if point_in_polygon(probe[0], probe[1], neighbour['loopCm']):
                return True
    return False


def plan_openings(edges, floors, pitch):
    """How many window openings each edge carries at this pitch."""
    plan = []
    for edge in edges:
        if edge['party'] or edge['length'] < MIN_WINDOW_EDGE_CM:
            plan.append(0)
            continue
        usable = edge['length'] - WINDOW_W - 60.0
        count = 0 if usable <= 0 else int(usable // pitch) + 1
        plan.append(max(0, min(count, int(edge['length'] // (WINDOW_W + 90.0)))))
    return plan, sum(plan) * floors


def estimate_tris(edge_count, openings, arched, floors, quoins, clutter):
    rectangular = openings - arched
    return (rectangular * 32 + arched * (8 * (ARCH_SEGMENTS + 3))
            + edge_count * 8 * 3          # cornice + band + parapet rings
            + quoins * QUOIN_BLOCKS * 12
            + 44                          # street door
            + clutter)


def build_building_detail(record, neighbours, street_index, pitch_cm):
    """All detail solids for one building, in canonical UE cm."""
    loop = record['loopCm']
    count = len(loop)
    offset = offset_ring(loop, SHELL_STANDOFF_CM)
    base_z = record['baseZ']
    roof_z = record['roofZ']
    height = roof_z - base_z
    floors = max(1, int(round(height / FLOOR_CM)))
    seed = record['id']

    edges = []
    for index in range(count):
        a, b = offset[index], offset[(index + 1) % count]
        raw_a, raw_b = loop[index], loop[(index + 1) % count]
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length < 1e-6:
            continue
        normal = _edge_normal(raw_a, raw_b)
        midpoint = ((raw_a[0] + raw_b[0]) / 2.0, (raw_a[1] + raw_b[1]) / 2.0)
        party = edge_is_party_wall(midpoint, normal, neighbours)
        street = None
        if street_index is not None:
            street = nearest_street_distance(street_index, midpoint[0], midpoint[1], 4000.0)
        edges.append({'a': a, 'b': b, 'length': length, 'party': party,
                      'midpoint': midpoint, 'normal': normal, 'street': street,
                      'index': index})
    if not edges:
        return [], 0, {}

    pitch = pitch_cm
    quoin_corners = pick_quoin_corners(loop, offset, edges)
    clutter_tris = 0
    dome = js_hash(seed * 7.0 + 11.0) < DOME_FRACTION
    tank = (not dome) and js_hash(seed * 13.0 + 3.0) < TANK_FRACTION
    stairhead = js_hash(seed * 17.0 + 29.0) < STAIRHEAD_FRACTION
    inradius = approximate_inradius(loop, record['centreCm'][0], record['centreCm'][1])
    if inradius < 250.0:
        dome = tank = stairhead = False
    if dome:
        clutter_tris += 10 * 4 + 10 * 2 * 2 + 10 + 8
    if tank:
        clutter_tris += 8 * 2 + 12
    if stairhead:
        clutter_tris += 12

    for _ in range(12):
        plan, openings = plan_openings(edges, floors, pitch)
        arched = int(round(openings * ARCH_FRACTION))
        estimate = estimate_tris(len(edges), openings, arched, floors, len(quoin_corners), clutter_tris)
        if estimate <= MAX_TRIS_PER_BUILDING or pitch >= WINDOW_PITCH_MAX_CM:
            break
        pitch = min(WINDOW_PITCH_MAX_CM, pitch * 1.35)
    plan, openings = plan_openings(edges, floors, pitch)

    solids = []
    stats = {'floors': floors, 'windowPitchCm': pitch, 'windows': 0, 'arched': 0,
             'doors': 0, 'quoinCorners': len(quoin_corners), 'partyEdges': 0,
             'dome': bool(dome), 'tank': bool(tank), 'stairHead': bool(stairhead)}
    stats['partyEdges'] = sum(1 for edge in edges if edge['party'])

    # street door: the non-party edge closest to a mapped street, longest as tie-break
    door_edge = None
    ranked = [edge for edge in edges if not edge['party'] and edge['length'] > DOOR_W + 90.0]
    if ranked:
        door_edge = min(ranked, key=lambda e: ((e['street'] if e['street'] is not None else 9e9), -e['length']))

    window_counter = 0
    for position, edge in enumerate(edges):
        openings_here = plan[position]
        if openings_here <= 0 and edge is not door_edge:
            continue
        frame = WallFrame(edge['a'], edge['b'])
        if openings_here > 0:
            span = edge['length'] - 60.0
            step = span / openings_here
            for slot in range(openings_here):
                centre = 30.0 + step * (slot + 0.5)
                s0, s1 = centre - WINDOW_W / 2.0, centre + WINDOW_W / 2.0
                for floor in range(floors):
                    z0 = base_z + floor * FLOOR_CM + WINDOW_SILL_CM
                    z1 = z0 + WINDOW_H
                    if z1 > roof_z - CORNICE_DROP_CM - 20.0:
                        continue
                    if (door_edge is edge and floor == 0
                            and abs(centre - edge['length'] / 2.0) < DOOR_W):
                        continue
                    window_counter += 1
                    arched = floor > 0 and js_hash(seed * 3.0 + window_counter * 1.7) < ARCH_FRACTION
                    solids.append(opening_solid(
                        frame, s0, s1, z0, z1, WINDOW_FRAME_CM,
                        SHELL_STANDOFF_CM, SHELL_STANDOFF_CM + WINDOW_PROUD_CM, arched))
                    stats['windows'] += 1
                    stats['arched'] += 1 if arched else 0
        if door_edge is edge:
            centre = edge['length'] / 2.0
            z0 = base_z
            solids.append(opening_solid(
                frame, centre - DOOR_W / 2.0, centre + DOOR_W / 2.0, z0, z0 + DOOR_H,
                DOOR_FRAME_CM, SHELL_STANDOFF_CM, SHELL_STANDOFF_CM + DOOR_PROUD_CM,
                js_hash(seed * 5.0 + 91.0) < 0.45))
            solids.append(frame_box(frame, centre - DOOR_W / 2.0 - 20.0, centre + DOOR_W / 2.0 + 20.0,
                                    SHELL_STANDOFF_CM, SHELL_STANDOFF_CM + DOOR_PROUD_CM + 6.0,
                                    z0 - 4.0, z0 + 12.0))
            stats['doors'] = 1

    # cornice, string band, parapet
    band_outer = offset_ring(loop, SHELL_STANDOFF_CM + BAND_PROUD_CM)
    cornice_outer = offset_ring(loop, SHELL_STANDOFF_CM + CORNICE_PROUD_CM)
    parapet_outer = offset_ring(loop, SHELL_STANDOFF_CM + PARAPET_PROUD_CM)
    # A deep inset would self-intersect on a narrow plan; fall back to a thin coping.
    inset = -PARAPET_INSET_CM if inradius > PARAPET_INSET_CM + 60.0 else SHELL_STANDOFF_CM
    parapet_inner = offset_ring(loop, inset)
    if height > CORNICE_DROP_CM + 120.0:
        solids.append(annulus_prism(band_outer, offset, roof_z - BAND_DROP_CM - BAND_HEIGHT_CM,
                                    roof_z - BAND_DROP_CM))
        solids.append(annulus_prism(cornice_outer, offset,
                                    roof_z - CORNICE_DROP_CM, roof_z - CORNICE_DROP_CM + CORNICE_HEIGHT_CM))
    solids.append(annulus_prism(parapet_outer, parapet_inner,
                                roof_z + SHELL_STANDOFF_CM,
                                roof_z + SHELL_STANDOFF_CM + PARAPET_HEIGHT_CM))

    for corner in quoin_corners:
        solids.extend(quoin_stack(corner, base_z, roof_z))

    cx, cy = record['centreCm']
    if dome:
        solids.append(dome_solid(cx, cy, roof_z + SHELL_STANDOFF_CM,
                                 min(150.0, inradius * 0.45), 55.0))
    if tank:
        tx = cx + min(120.0, inradius * 0.35)
        solids.append(cylinder_solid(tx, cy, roof_z + SHELL_STANDOFF_CM + 30.0,
                                     roof_z + SHELL_STANDOFF_CM + 140.0, 62.0))
        solids.append(oriented_box(tx, cy, roof_z + SHELL_STANDOFF_CM,
                                   roof_z + SHELL_STANDOFF_CM + 30.0, 66.0, 66.0, 0.0))
    if stairhead:
        yaw = js_hash(seed * 23.0) * math.pi
        sx = cx - min(140.0, inradius * 0.4)
        solids.append(oriented_box(sx, cy, roof_z + SHELL_STANDOFF_CM,
                                   roof_z + SHELL_STANDOFF_CM + 220.0, 100.0, 80.0, yaw))

    triangles = sum(len(solid.faces) for solid in solids)
    return solids, triangles, stats


def pick_quoin_corners(loop, offset, edges):
    """Up to QUOIN_CORNERS near-right convex corners whose two edges are both exposed."""
    count = len(loop)
    party = {edge['index']: edge['party'] for edge in edges}
    candidates = []
    for index in range(count):
        previous = (index - 1) % count
        if party.get(previous, True) or party.get(index, True):
            continue
        a, b, c = loop[previous], loop[index], loop[(index + 1) % count]
        v1 = (b[0] - a[0], b[1] - a[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        l1, l2 = math.hypot(*v1), math.hypot(*v2)
        if l1 < 200.0 or l2 < 200.0:
            continue
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        if cross <= 0:                    # reflex corner on a CCW ring
            continue
        cosine = (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)
        turn = math.degrees(math.acos(clamp(cosine, -1.0, 1.0)))
        if not 55.0 < turn < 125.0:
            continue
        candidates.append({
            'score': abs(turn - 90.0),
            'prev': (offset[previous], offset[index], l1),
            'next': (offset[index], offset[(index + 1) % count], l2),
        })
    candidates.sort(key=lambda item: item['score'])
    return candidates[:QUOIN_CORNERS]


def quoin_stack(corner, base_z, roof_z):
    """Alternating ashlar blocks reading around one exposed corner.

    Odd courses sit on the incoming wall (its far end at the corner), even courses on
    the outgoing wall, each built on that wall's own +6 cm offset line so the block is
    always outside the imported box.
    """
    solids = []
    for block in range(QUOIN_BLOCKS):
        z0 = base_z + QUOIN_BASE_CM + block * QUOIN_PITCH_CM
        z1 = z0 + QUOIN_HEIGHT_CM
        if z1 > roof_z - CORNICE_DROP_CM - 30.0:
            break
        a, b, _ = corner['prev'] if block % 2 == 0 else corner['next']
        try:
            frame = WallFrame(a, b)
        except ValueError:
            continue
        if block % 2 == 0:
            run = min(QUOIN_RUN_CM, frame.length * 0.4)
            s0, s1 = frame.length - run, frame.length
        else:
            run = min(QUOIN_RUN_CM * 0.7, frame.length * 0.4)
            s0, s1 = 0.0, run
        if run < 25.0:
            continue
        solids.append(frame_box(frame, s0, s1, 0.0, QUOIN_PROUD_CM, z0, z1))
    return solids


# ================================================================ street helpers
def build_street_index(source, bounds, buffer_cm):
    index = Grid2D(2000.0)
    minx, miny, maxx, maxy = bounds
    segments = []
    for _, points in source.polylines('road'):
        converted = [ue_xy(x, z) for x, z in points]
        for position in range(1, len(converted)):
            a, b = converted[position - 1], converted[position]
            lo_x, hi_x = min(a[0], b[0]), max(a[0], b[0])
            lo_y, hi_y = min(a[1], b[1]), max(a[1], b[1])
            if hi_x < minx - buffer_cm or lo_x > maxx + buffer_cm:
                continue
            if hi_y < miny - buffer_cm or lo_y > maxy + buffer_cm:
                continue
            segment = (a, b)
            index.insert(lo_x, lo_y, hi_x, hi_y, segment)
            segments.append(segment)
    return index, segments


def nearest_street_distance(index, x, y, radius):
    best = None
    for a, b in index.query(x - radius, y - radius, x + radius, y + radius):
        distance = point_segment_distance(x, y, a[0], a[1], b[0], b[1])
        if best is None or distance < best:
            best = distance
    return best


# ================================================================= exclusion zones
def load_exclusions():
    """Mount platform boundary and the protected Kotel / plaza polygons, in UE cm."""
    design = json.loads(DESIGN_JSON.read_text(encoding='utf-8-sig'))
    platform = [(float(x), float(y)) for x, y in design['boundary']['nativeXYcm']]
    if math.hypot(platform[0][0] - platform[-1][0], platform[0][1] - platform[-1][1]) < 1.0:
        platform.pop()
    zones = [{'kind': 'mountPlatform', 'osmId': None, 'name': 'Inferred Mount enclosure ring',
              'polygon': ensure_ccw(platform), 'bufferCm': INFILL_PROTECTED_BUFFER_CM}]
    for entry in design['protected']:
        points = [(float(x), float(y)) for x, y in entry['nativeXYcm']]
        if math.hypot(points[0][0] - points[-1][0], points[0][1] - points[-1][1]) < 1.0:
            points.pop()
        zones.append({'kind': entry['kind'], 'osmId': entry['osmId'], 'name': entry.get('name'),
                      'polygon': ensure_ccw(points),
                      'bufferCm': float(entry['minimumNoEditBufferCm']) + INFILL_PROTECTED_BUFFER_CM})
    return zones, design


def in_excluded(zones, x, y):
    for zone in zones:
        polygon = zone['polygon']
        if point_in_polygon(x, y, polygon):
            return True
        buffer_cm = zone['bufferCm']
        count = len(polygon)
        for index in range(count):
            a, b = polygon[index], polygon[(index + 1) % count]
            if point_segment_distance(x, y, a[0], a[1], b[0], b[1]) <= buffer_cm:
                return True
    return False


def near_polyline(ring, x, y, distance):
    count = len(ring)
    for index in range(count):
        a, b = ring[index], ring[(index + 1) % count]
        if point_segment_distance(x, y, a[0], a[1], b[0], b[1]) <= distance:
            return True
    return False


def polygons_overlap(a, b):
    for point in a:
        if point_in_polygon(point[0], point[1], b):
            return True
    for point in b:
        if point_in_polygon(point[0], point[1], a):
            return True
    for i in range(len(a)):
        a1, a2 = a[i], a[(i + 1) % len(a)]
        for j in range(len(b)):
            b1, b2 = b[j], b[(j + 1) % len(b)]
            if segments_intersect(a1, a2, b1, b2):
                return True
    return False


def ring_bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


# ==================================================================== infill plan
SAMPLE_N = 100                      # 100 x 100 samples per 100 m cell = 1 m spacing
SAMPLE_STEP = CELL_CM / SAMPLE_N

OUTSIDE, AVAILABLE, EXISTING_BUILT, INFILL_BUILT = 0, 1, 2, 3


class MaskGrid:
    """2.5 m coverage raster aligned to the 100 m cells; the coverage ledger for the run."""

    def __init__(self, bounds):
        minx, miny, maxx, maxy = bounds
        self.step = SAMPLE_STEP
        self.ox = math.floor(minx / CELL_CM) * CELL_CM
        self.oy = math.floor(miny / CELL_CM) * CELL_CM
        self.nx = int(math.ceil((maxx - self.ox) / self.step)) + 1
        self.ny = int(math.ceil((maxy - self.oy) / self.step)) + 1
        self.data = bytearray(self.nx * self.ny)
        # Second layer: street and wall corridors that must stay clear of new massing.
        # Kept separate so the coverage denominator stays "inside the walls, not protected".
        self.blocked = bytearray(self.nx * self.ny)

    def sample_xy(self, i, j):
        return (self.ox + (i + 0.5) * self.step, self.oy + (j + 0.5) * self.step)

    def index_range(self, key):
        i0 = int(round((key[0] * CELL_CM - self.ox) / self.step))
        j0 = int(round((key[1] * CELL_CM - self.oy) / self.step))
        return i0, j0

    def free_at(self, x, y):
        i = int((x - self.ox) / self.step - 0.5 + 0.5)
        j = int((y - self.oy) / self.step - 0.5 + 0.5)
        if not (0 <= i < self.nx and 0 <= j < self.ny):
            return False
        offset = j * self.nx + i
        return self.data[offset] == AVAILABLE and not self.blocked[offset]

    def fill(self, points, value, only_over=None, layer=None):
        """Scanline-fill one polygon of canonical cm into the raster."""
        ys = [p[1] for p in points]
        j_lo = max(0, int(math.floor((min(ys) - self.oy) / self.step - 0.5)))
        j_hi = min(self.ny - 1, int(math.ceil((max(ys) - self.oy) / self.step - 0.5)))
        count = len(points)
        data, nx = (self.blocked if layer == 'blocked' else self.data), self.nx
        for j in range(j_lo, j_hi + 1):
            y = self.oy + (j + 0.5) * self.step
            crossings = []
            for index in range(count):
                ax, ay = points[index]
                bx, by = points[(index + 1) % count]
                if (ay > y) != (by > y):
                    crossings.append(ax + (y - ay) * (bx - ax) / (by - ay))
            crossings.sort()
            row = j * nx
            for pair in range(0, len(crossings) - 1, 2):
                i0 = max(0, int(math.ceil((crossings[pair] - self.ox) / self.step - 0.5)))
                i1 = min(nx - 1, int(math.floor((crossings[pair + 1] - self.ox) / self.step - 0.5)))
                for i in range(i0, i1 + 1):
                    if only_over is None or data[row + i] in only_over:
                        data[row + i] = value

    def cell_counts(self, key):
        i0, j0 = self.index_range(key)
        available = existing = infill = 0
        data, nx = self.data, self.nx
        for dj in range(SAMPLE_N):
            j = j0 + dj
            if not 0 <= j < self.ny:
                continue
            row = j * nx
            for di in range(SAMPLE_N):
                i = i0 + di
                if not 0 <= i < nx:
                    continue
                value = data[row + i]
                if value == AVAILABLE:
                    available += 1
                elif value == EXISTING_BUILT:
                    existing += 1
                elif value == INFILL_BUILT:
                    infill += 1
        return available, existing, infill

    def free_samples(self, key):
        i0, j0 = self.index_range(key)
        out = []
        data, blocked, nx = self.data, self.blocked, self.nx
        for dj in range(SAMPLE_N):
            j = j0 + dj
            if not 0 <= j < self.ny:
                continue
            row = j * nx
            for di in range(SAMPLE_N):
                i = i0 + di
                if 0 <= i < nx and data[row + i] == AVAILABLE and not blocked[row + i]:
                    out.append(self.sample_xy(i, j))
        return out

    def free_extent(self, cx, cy, dx, dy, limit):
        """How far the free raster reaches from (cx, cy) along a unit direction."""
        travelled = 0.0
        stride = self.step * 0.5
        while travelled + stride <= limit:
            travelled += stride
            if not self.free_at(cx + dx * travelled, cy + dy * travelled):
                return travelled - stride
        return limit

    def summary(self):
        """Where the walled, unprotected ground actually went, in raster samples."""
        counts = {'existingBuilt': 0, 'infillBuilt': 0, 'blockedByStreetOrWall': 0, 'stillFree': 0}
        for j in range(self.ny):
            row = j * self.nx
            for i in range(self.nx):
                value = self.data[row + i]
                if value == OUTSIDE:
                    continue
                if value == EXISTING_BUILT:
                    counts['existingBuilt'] += 1
                elif value == INFILL_BUILT:
                    counts['infillBuilt'] += 1
                elif self.blocked[row + i]:
                    counts['blockedByStreetOrWall'] += 1
                else:
                    counts['stillFree'] += 1
        total = float(sum(counts.values())) or 1.0
        counts['samples'] = int(total)
        counts['sampleAreaM2'] = (self.step / 100.0) ** 2
        counts['fractions'] = {key: round(counts[key] / total, 4)
                               for key in ('existingBuilt', 'infillBuilt',
                                           'blockedByStreetOrWall', 'stillFree')}
        counts['coverageCeilingIfEveryFreeSampleWereBuilt'] = round(
            (counts['existingBuilt'] + counts['infillBuilt'] + counts['stillFree']) / total, 4)
        return counts

    def rect_is_free(self, polygon):
        minx, miny, maxx, maxy = ring_bbox(polygon)
        i0 = max(0, int((minx - self.ox) / self.step))
        i1 = min(self.nx - 1, int((maxx - self.ox) / self.step) + 1)
        j0 = max(0, int((miny - self.oy) / self.step))
        j1 = min(self.ny - 1, int((maxy - self.oy) / self.step) + 1)
        for j in range(j0, j1 + 1):
            row = j * self.nx
            y = self.oy + (j + 0.5) * self.step
            for i in range(i0, i1 + 1):
                x = self.ox + (i + 0.5) * self.step
                if not point_in_polygon(x, y, polygon):
                    continue
                if self.data[row + i] != AVAILABLE or self.blocked[row + i]:
                    return False
        return True


def build_mask(ring, zones, existing_records, street_segments, wall_ring):
    mask = MaskGrid(ring_bbox(ring))
    mask.fill(ring, AVAILABLE)
    for zone in zones:
        mask.fill(offset_ring(zone['polygon'], zone['bufferCm']), OUTSIDE)
    for record in existing_records:
        mask.fill(record['loopCm'], EXISTING_BUILT, only_over=(AVAILABLE,))
        # Same footprint grown by the abutment gap goes into the blocked layer, so the
        # raster search and the exact polygon test below agree instead of fighting.
        mask.fill(offset_ring(record['loopCm'], INFILL_EXISTING_GAP_CM + INFILL_RASTER_MARGIN_CM),
                  1, layer='blocked')
    # Street and wall corridors: a swept rectangle per segment, plus a square cap per node.
    half = INFILL_STREET_BUFFER_CM
    for a, b in street_segments:
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 1e-6:
            continue
        nx, ny = dy / length * half, -dx / length * half
        mask.fill([(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny),
                   (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)], 1, layer='blocked')
        for point in (a, b):
            mask.fill([(point[0] - half, point[1] - half), (point[0] + half, point[1] - half),
                       (point[0] + half, point[1] + half), (point[0] - half, point[1] + half)],
                      1, layer='blocked')
    count = len(wall_ring)
    half = INFILL_WALL_BUFFER_CM
    for index in range(count):
        a, b = wall_ring[index], wall_ring[(index + 1) % count]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 1e-6:
            continue
        nx, ny = dy / length * half, -dx / length * half
        mask.fill([(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny),
                   (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)], 1, layer='blocked')
    return mask


def cells_overlapping(ring):
    minx, miny, maxx, maxy = ring_bbox(ring)
    keys = []
    for bx in range(int(math.floor(minx / CELL_CM)), int(math.floor(maxx / CELL_CM)) + 1):
        for by in range(int(math.floor(miny / CELL_CM)), int(math.floor(maxy / CELL_CM)) + 1):
            keys.append((bx, by))
    return keys


def street_aligned_yaw(street_index, x, y, fallback):
    best, angle = None, fallback
    for a, b in street_index.query(x - 4000.0, y - 4000.0, x + 4000.0, y + 4000.0):
        distance = point_segment_distance(x, y, a[0], a[1], b[0], b[1])
        if best is None or distance < best:
            best = distance
            angle = math.atan2(b[1] - a[1], b[0] - a[0])
    return angle


def rect_ring(cx, cy, half_x, half_y, yaw):
    cosine, sine = math.cos(yaw), math.sin(yaw)
    corners = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        lx, ly = sx * half_x, sy * half_y
        corners.append((cx + lx * cosine - ly * sine, cy + lx * sine + ly * cosine))
    return ensure_ccw(corners)


def courtyard_wings(cx, cy, half_x, half_y, yaw, wing):
    """Four wings around an open court: the classic Old City courtyard house plan."""
    wings = []
    inner_x, inner_y = half_x - wing, half_y - wing
    if inner_x < 200.0 or inner_y < 200.0:
        return [rect_ring(cx, cy, half_x, half_y, yaw)]
    cosine, sine = math.cos(yaw), math.sin(yaw)

    def place(lx, ly, hx, hy):
        return rect_ring(cx + lx * cosine - ly * sine, cy + lx * sine + ly * cosine, hx, hy, yaw)

    wings.append(place(0.0, -(half_y - wing / 2.0), half_x, wing / 2.0))
    wings.append(place(0.0, +(half_y - wing / 2.0), half_x, wing / 2.0))
    wings.append(place(-(half_x - wing / 2.0), 0.0, wing / 2.0, inner_y))
    wings.append(place(+(half_x - wing / 2.0), 0.0, wing / 2.0, inner_y))
    return wings


def infill_candidate_ok(wings, ring, zones, wall_ring, street_index, existing_index, placed_index):
    for polygon in wings:
        for x, y in polygon:
            if not point_in_polygon(x, y, ring):
                return False
            if in_excluded(zones, x, y):
                return False
            if near_polyline(wall_ring, x, y, INFILL_WALL_BUFFER_CM):
                return False
        count = len(polygon)
        for index in range(count):
            a, b = polygon[index], polygon[(index + 1) % count]
            for point in (a, ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)):
                distance = nearest_street_distance(street_index, point[0], point[1],
                                                   INFILL_STREET_BUFFER_CM * 2.0)
                if distance is not None and distance < INFILL_STREET_BUFFER_CM:
                    return False
    for polygon in wings:
        grown = offset_ring(polygon, INFILL_EXISTING_GAP_CM)
        box = ring_bbox(grown)
        for record in existing_index.query(*box):
            other = record['boxCm']
            if other[2] < box[0] or other[0] > box[2] or other[3] < box[1] or other[1] > box[3]:
                continue
            if polygons_overlap(grown, record['loopCm']):
                return False
        for record in placed_index.query(*box):
            if polygons_overlap(grown, record['loopCm']):
                return False
    return True


def generate_infill(mask, ring, zones, wall_ring, street_index, existing_index, source):
    """Authored 2-3 storey block and courtyard massing in the empty parts of the walls."""
    placed_index = Grid2D(2500.0)
    per_cell = {}
    counter = 0
    for key in sorted(cells_overlapping(ring)):
        available, existing_built, _ = mask.cell_counts(key)
        total = available + existing_built
        if total < 20:                    # essentially no buildable ground in this cell
            continue
        before = existing_built / float(total)
        rng = random.Random((key[0] * 73856093) ^ (key[1] * 19349663) ^ 0x5EED)
        records, attempts, covered = [], 0, existing_built
        for _ in range(INFILL_PASSES_PER_CELL):
            if covered / float(total) >= INFILL_TARGET_COVERAGE or len(records) >= INFILL_MAX_PER_CELL:
                break
            free = mask.free_samples(key)
            if not free:
                break
            rng.shuffle(free)
            # 1 m sampling is for accuracy, not for trying ten thousand seeds per cell.
            free = free[:INFILL_SEEDS_PER_PASS]
            placed_this_pass = 0
            for cx, cy in free:
                if (covered / float(total) >= INFILL_TARGET_COVERAGE
                        or len(records) >= INFILL_MAX_PER_CELL):
                    break
                attempts += 1
                if not mask.free_at(cx, cy):
                    continue
                # Grow the plot into whatever gap the free raster actually offers, rather
                # than guessing a size and failing: walk out along the plot axes, take the
                # symmetric extent, keep the better of the two street-aligned orientations,
                # then shrink until the whole rectangle sits on free ground.
                aligned = street_aligned_yaw(street_index, cx, cy, rng.uniform(0.0, math.pi))
                limit = INFILL_MAX_CM / 2.0
                best = None
                for yaw in (aligned, aligned + math.pi / 2.0):
                    ux, uy = math.cos(yaw), math.sin(yaw)
                    vx, vy = -uy, ux
                    ep = mask.free_extent(cx, cy, ux, uy, limit)
                    em = mask.free_extent(cx, cy, -ux, -uy, limit)
                    fp = mask.free_extent(cx, cy, vx, vy, limit)
                    fm = mask.free_extent(cx, cy, -vx, -vy, limit)
                    # Recentre on the gap rather than on the seed: an off-centre seed would
                    # otherwise throw away twice the shorter ray on both sides.
                    hx, hy = (ep + em) / 2.0, (fp + fm) / 2.0
                    ox = cx + ux * (ep - em) / 2.0 + vx * (fp - fm) / 2.0
                    oy = cy + uy * (ep - em) / 2.0 + vy * (fp - fm) / 2.0
                    if best is None or hx * hy > best[0] * best[1]:
                        best = (hx, hy, yaw, ox, oy)
                base_hx, base_hy, yaw, cx, cy = best
                wings = None
                courtyard = False
                for shrink in (0.94, 0.8, 0.66, 0.52):
                    half_x, half_y = base_hx * shrink, base_hy * shrink
                    if (half_x * 2.0 < INFILL_MIN_SIDE_CM or half_y * 2.0 < INFILL_MIN_SIDE_CM
                            or half_x * half_y * 4.0 < INFILL_MIN_AREA_CM2):
                        break
                    courtyard = (rng.random() < INFILL_COURTYARD_FRACTION
                                 and half_x > INFILL_COURT_WING_CM * 1.6
                                 and half_y > INFILL_COURT_WING_CM * 1.6)
                    candidate = (courtyard_wings(cx, cy, half_x, half_y, yaw, INFILL_COURT_WING_CM)
                                 if courtyard else [rect_ring(cx, cy, half_x, half_y, yaw)])
                    if all(mask.rect_is_free(polygon) for polygon in candidate):
                        wings = candidate
                        break
                if wings is None:
                    continue
                if not infill_candidate_ok(wings, ring, zones, wall_ring, street_index,
                                           existing_index, placed_index):
                    continue
                counter += 1
                storeys = INFILL_STOREYS[counter % len(INFILL_STOREYS)]
                base_z = ue_z(source.height_at(cx / AMAH_CM - TX, cy / AMAH_CM - TZ))
                records.append({
                    'infillId': counter,
                    'id': 900000000 + counter,
                    'cell': key,
                    'storeys': storeys,
                    'plan': 'courtyard' if courtyard else 'block',
                    'yawDegrees': round(math.degrees(yaw) % 180.0, 3),
                    'wings': wings,
                    'baseZ': base_z,
                    'roofZ': base_z + storeys * FLOOR_CM,
                    'tag': INFILL_TAG,
                })
                placed_this_pass += 1
                for polygon in wings:
                    placed_index.insert(*ring_bbox(polygon), {'loopCm': polygon})
                    mask.fill(polygon, INFILL_BUILT, only_over=(AVAILABLE,))
                    mask.fill(offset_ring(polygon, INFILL_EXISTING_GAP_CM + INFILL_RASTER_MARGIN_CM),
                              1, layer='blocked')
                _, existing_built, infill_built = mask.cell_counts(key)
                covered = existing_built + infill_built
            if placed_this_pass == 0:
                break
        available, existing_built, infill_built = mask.cell_counts(key)
        per_cell[key] = {
            'samplesAvailable': total,
            'builtBefore': existing_built,
            'builtAfter': existing_built + infill_built,
            'coverageBefore': round(before, 4),
            'coverageAfter': round((existing_built + infill_built) / float(total), 4),
            'infill': records,
            'attempts': attempts,
        }
    return per_cell


# ================================================================== OBJ writing
OBJ_HEADER_NOTE = ('Unreal legacy OBJ adapter: canonical vertices are UE cm; this file is '
                   'written with Y reflected and triangle winding reversed. One object, no '
                   'g groups, so the importer creates exactly one material slot.')


def write_obj(path, object_name, solids, provenance_lines):
    """Canonical solids -> adapter OBJ. Returns numeric facts for the manifest."""
    vertex_index = {}
    vertex_lines = []
    uv_lines = []
    normal_index = {}
    normal_lines = []
    face_lines = []
    lo = [float('inf')] * 3
    hi = [float('-inf')] * 3
    triangles = 0

    for solid in solids:
        points = solid.vertices
        local = []
        for x, y, z in points:
            key = (round(x, 2), round(y, 2), round(z, 2))
            found = vertex_index.get(key)
            if found is None:
                found = len(vertex_lines) + 1
                vertex_index[key] = found
                vertex_lines.append('v %.2f %.2f %.2f' % (key[0], -key[1], key[2]))
                uv_lines.append('vt %.4f %.4f' % ((key[0] + key[1]) / 400.0, key[2] / 400.0))
                for axis, value in enumerate(key):
                    if value < lo[axis]:
                        lo[axis] = value
                    if value > hi[axis]:
                        hi[axis] = value
            local.append(found)
        for a, b, c in solid.faces:
            ax, ay, az = points[a]
            bx, by, bz = points[b]
            cx, cy, cz = points[c]
            ux, uy, uz = bx - ax, by - ay, bz - az
            vx, vy, vz = cx - ax, cy - ay, cz - az
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            length = math.sqrt(nx * nx + ny * ny + nz * nz)
            if length < 1e-9:
                continue
            key = (round(nx / length, 4), round(-ny / length, 4), round(nz / length, 4))
            found = normal_index.get(key)
            if found is None:
                found = len(normal_lines) + 1
                normal_index[key] = found
                normal_lines.append('vn %.4f %.4f %.4f' % key)
            ia, ib, ic = local[a], local[c], local[b]     # reversed winding
            face_lines.append('f %d/%d/%d %d/%d/%d %d/%d/%d'
                              % (ia, ia, found, ib, ib, found, ic, ic, found))
            triangles += 1

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
        handle.write('\n'.join(face_lines) + '\n')
    return {
        'file': path.name,
        'sha256': sha256_of(path),
        'bytes': path.stat().st_size,
        'triangles': triangles,
        'vertices': len(vertex_lines),
        'normals': len(normal_lines),
        'canonicalBoundsCm': {'min': lo, 'max': hi},
    }


# =========================================================================== PNG
FONT_3X5 = {
    'A': '010101111101101', 'B': '110101110101110', 'C': '011100100100011',
    'D': '110101101101110', 'E': '111100110100111', 'F': '111100110100100',
    'G': '011100101101011', 'H': '101101111101101', 'I': '111010010010111',
    'J': '001001001101010', 'K': '101101110101101', 'L': '100100100100111',
    'M': '101111111101101', 'N': '101111111111101', 'O': '010101101101010',
    'P': '110101110100100', 'Q': '010101101111011', 'R': '110101110101101',
    'S': '011100010001110', 'T': '111010010010010', 'U': '101101101101111',
    'V': '101101101101010', 'W': '101101111111101', 'X': '101101010101101',
    'Y': '101101010010010', 'Z': '111001010100111', '0': '111101101101111',
    '1': '010110010010111', '2': '111001111100111', '3': '111001111001111',
    '4': '101101111001001', '5': '111100111001111', '6': '111100111101111',
    '7': '111001001001001', '8': '111101111101111', '9': '111101111001111',
    ' ': '000000000000000', '.': '000000000000010', '-': '000000111000000',
    '%': '101001010100101', '(': '001010010010001', ')': '100010010010100',
    '/': '001001010100100', ',': '000000000010010', ':': '000010000010000',
    '+': '000010111010000',
}


class Canvas:
    def __init__(self, width, height, background):
        self.width, self.height = width, height
        self.buffer = bytearray(bytes(background) * (width * height))

    def pixel(self, x, y, colour):
        if 0 <= x < self.width and 0 <= y < self.height:
            offset = (y * self.width + x) * 3
            self.buffer[offset:offset + 3] = bytes(colour)

    def line(self, x0, y0, x1, y1, colour):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        error = dx + dy
        while True:
            self.pixel(x0, y0, colour)
            if x0 == x1 and y0 == y1:
                return
            double = 2 * error
            if double >= dy:
                error += dy
                x0 += sx
            if double <= dx:
                error += dx
                y0 += sy

    def polygon(self, points, colour):
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        top = max(0, int(math.floor(min(ys))))
        bottom = min(self.height - 1, int(math.ceil(max(ys))))
        count = len(points)
        for y in range(top, bottom + 1):
            centre = y + 0.5
            crossings = []
            for index in range(count):
                ax, ay = points[index]
                bx, by = points[(index + 1) % count]
                if (ay > centre) != (by > centre):
                    crossings.append(ax + (centre - ay) * (bx - ax) / (by - ay))
            crossings.sort()
            for pair in range(0, len(crossings) - 1, 2):
                x0 = max(0, int(math.ceil(crossings[pair] - 0.5)))
                x1 = min(self.width - 1, int(math.floor(crossings[pair + 1] - 0.5)))
                if x1 < x0:
                    continue
                offset = (y * self.width + x0) * 3
                self.buffer[offset:offset + (x1 - x0 + 1) * 3] = bytes(colour) * (x1 - x0 + 1)

    def rect(self, x0, y0, x1, y1, colour):
        for y in range(int(y0), int(y1)):
            for x in range(int(x0), int(x1)):
                self.pixel(x, y, colour)

    def text(self, x, y, message, colour, scale=2):
        cursor = x
        for character in message.upper():
            glyph = FONT_3X5.get(character)
            if glyph is None:
                cursor += 4 * scale
                continue
            for row in range(5):
                for column in range(3):
                    if glyph[row * 3 + column] == '1':
                        self.rect(cursor + column * scale, y + row * scale,
                                  cursor + (column + 1) * scale, y + (row + 1) * scale, colour)
            cursor += 4 * scale
        return cursor

    def png_bytes(self):
        raw = bytearray()
        stride = self.width * 3
        for y in range(self.height):
            raw.append(0)
            raw += self.buffer[y * stride:(y + 1) * stride]
        def chunk(tag, payload):
            body = tag + payload
            return struct.pack('>I', len(payload)) + body + struct.pack('>I', zlib.crc32(body) & 0xFFFFFFFF)
        header = struct.pack('>IIBBBBB', self.width, self.height, 8, 2, 0, 0, 0)
        return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header)
                + chunk(b'IDAT', zlib.compress(bytes(raw), 6)) + chunk(b'IEND', b''))


def write_preview(path, ring, zones, streets, existing, infill, summary):
    minx, miny, maxx, maxy = ring_bbox(ring)
    pad = 4000.0
    minx, miny, maxx, maxy = minx - pad, miny - pad, maxx + pad, maxy + pad
    legend_h = 120
    scale = (PREVIEW_PX - 40) / max(maxx - minx, maxy - miny)
    width = int((maxx - minx) * scale) + 40
    height = int((maxy - miny) * scale) + 40 + legend_h
    canvas = Canvas(width, height, (247, 244, 236))

    def to_px(point):
        return (20 + (point[0] - minx) * scale, 20 + (point[1] - miny) * scale)

    for zone in zones:
        canvas.polygon([to_px(p) for p in zone['polygon']],
                       (214, 214, 210) if zone['kind'] == 'mountPlatform' else (196, 186, 214))
    for a, b in streets:
        pa, pb = to_px(a), to_px(b)
        canvas.line(pa[0], pa[1], pb[0], pb[1], (176, 170, 160))
    for polygon in existing:
        canvas.polygon([to_px(p) for p in polygon], (150, 116, 78))
    for polygon in infill:
        canvas.polygon([to_px(p) for p in polygon], (44, 122, 138))
    count = len(ring)
    for index in range(count):
        a, b = to_px(ring[index]), to_px(ring[(index + 1) % count])
        canvas.line(a[0], a[1], b[0], b[1], (30, 30, 30))
        canvas.line(a[0] + 1, a[1], b[0] + 1, b[1], (30, 30, 30))

    base = height - legend_h + 16
    canvas.rect(0, height - legend_h, width, height, (247, 244, 236))
    entries = [((150, 116, 78), 'OSM FOOTPRINTS %d' % summary['existingBuildings']),
               ((44, 122, 138), 'AUTHORED INFILL %d' % summary['infillBuildings']),
               ((214, 214, 210), 'MOUNT PLATFORM'),
               ((196, 186, 214), 'PROTECTED KOTEL / PLAZA'),
               ((176, 170, 160), 'STREETS')]
    cursor = 24
    for colour, label in entries:
        canvas.rect(cursor, base, cursor + 22, base + 16, colour)
        cursor = canvas.text(cursor + 30, base + 2, label, (40, 40, 40), 2) + 26
    canvas.text(24, base + 34,
                'OLD CITY WALLS %.2f KM2  COVERAGE %.1f%% TO %.1f%%'
                % (summary['ringAreaM2'] / 1e6, summary['coverageBefore'] * 100.0,
                   summary['coverageAfter'] * 100.0), (40, 40, 40), 2)
    canvas.text(24, base + 60, 'NORTH IS UP  100 M CELL BATCHES  PLAN VIEW', (90, 90, 90), 2)
    path.write_bytes(canvas.png_bytes())
    return {'file': path.name, 'sha256': sha256_of(path), 'bytes': path.stat().st_size,
            'widthPx': width, 'heightPx': height, 'cmPerPixel': 1.0 / scale}


# ================================================================ self test
def self_test():
    """Cheap invariants for the adapter and the primitives, run before any authoring."""
    cube = prism([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)], 0.0, 100.0)
    volume = cube.volume()
    if abs(volume - 1e6) > 1.0:
        raise RuntimeError('prism volume %.3f is not the 100 cm cube' % volume)
    if len(cube.faces) != 12:
        raise RuntimeError('cube should be 12 triangles, got %d' % len(cube.faces))
    edges = {}
    for a, b, c in cube.faces:
        for i, j in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted((i, j)))] = edges.get(tuple(sorted((i, j))), 0) + 1
    if any(count != 2 for count in edges.values()):
        raise RuntimeError('cube is not edge-manifold')
    band = annulus_prism([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)],
                         [(20.0, 20.0), (80.0, 20.0), (80.0, 80.0), (20.0, 80.0)], 0.0, 10.0)
    if abs(band.volume() - (100.0 * 100.0 - 60.0 * 60.0) * 10.0) > 1.0:
        raise RuntimeError('annulus_prism volume is wrong: %.3f' % band.volume())
    frame = WallFrame((0.0, 0.0), (400.0, 0.0))
    opening = opening_solid(frame, 100.0, 200.0, 0.0, 180.0, 14.0, 6.0, 20.0, False)
    if opening.volume() <= 0.0:
        raise RuntimeError('opening_solid failed to orient')
    if abs(js_hash(4709536) - (math.sin(4709536 * 127.1 + 311.7) * 43758.5453123
                               - math.floor(math.sin(4709536 * 127.1 + 311.7) * 43758.5453123))) > 1e-12:
        raise RuntimeError('js_hash parity broken')
    for text, want in (('17', 17.0), ('17 m', 17.0), ('', None), ('abc', None), ('3.5', 3.5)):
        if js_parse_float(text) != want:
            raise RuntimeError('js_parse_float(%r) != %r' % (text, want))
    return {'cubeVolumeCm3': volume, 'bandVolumeCm3': band.volume(),
            'openingVolumeCm3': opening.volume(), 'edgeManifold': True}


# ================================================================== main pipeline
def generate(force=False, preview=True):
    started = time.time()
    if MANIFEST_PATH.exists() and not force:
        raise RuntimeError('Frozen generation preserved: %s already exists (pass --force to re-author)'
                           % MANIFEST_PATH)
    checks = self_test()

    source_sha = sha256_of(SOURCE_JSON)
    if source_sha != SOURCE_JSON_SHA:
        raise RuntimeError('jerusalem.json SHA256 %s is not the reviewed export' % source_sha)
    data = json.loads(SOURCE_JSON.read_text(encoding='utf-8-sig'))
    source = CitySource(data)
    records, source_skipped = source.buildings()
    verification = verify_against_frozen_manifest(records)

    ring, ring_area_m2, chain_gaps = old_city_ring(source)
    ring_box = ring_bbox(ring)
    zones, design = load_exclusions()

    # canonical footprints in UE cm for every extruded building
    for record in records:
        loop = dedupe_ring([ue_xy(x, z) for x, z in record['points']], 1.0)
        if len(loop) < 3:
            record['loopCm'] = None
            continue
        loop = ensure_ccw(loop)
        record['loopCm'] = loop
        record['boxCm'] = ring_bbox(loop)
        record['centreCm'] = ue_xy(record['centre'][0], record['centre'][1])
        record['baseZ'] = ue_z(record['base'])
        record['roofZ'] = ue_z(record['base'] + record['height'])
        record['areaCm2'] = abs(polygon_area(loop))
    records = [record for record in records if record.get('loopCm')]

    def in_scope(record):
        cx, cy = record['centreCm']
        if point_in_polygon(cx, cy, ring):
            return True
        return near_polyline(ring, cx, cy, OLD_CITY_MARGIN_CM)

    scope = [record for record in records if in_scope(record)]
    inside_only = [record for record in records if point_in_polygon(*record['centreCm'], ring)]

    scope_box = ring_bbox([p for record in scope for p in record['loopCm']])
    neighbour_index = Grid2D(2500.0)
    grown = (scope_box[0] - 20000.0, scope_box[1] - 20000.0, scope_box[2] + 20000.0, scope_box[3] + 20000.0)
    for record in records:
        box = record['boxCm']
        if box[2] < grown[0] or box[0] > grown[2] or box[3] < grown[1] or box[1] > grown[3]:
            continue
        neighbour_index.insert(box[0], box[1], box[2], box[3], record)

    street_index, street_segments = build_street_index(
        source, ring_box, OLD_CITY_MARGIN_CM + INFILL_STREET_BUFFER_CM)

    mask = build_mask(ring, zones, inside_only, street_segments, ring)
    infill_by_cell = generate_infill(mask, ring, zones, ring, street_index,
                                     neighbour_index, source)

    # ------------------------------------------------------------------ batching
    facade_cells = {}
    for record in scope:
        key = cell_key_of(record['centreCm'][0], record['centreCm'][1])
        facade_cells.setdefault(key, []).append(record)

    OBJ_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    provenance = [
        'OldCityFacadesV1 %s' % stamp,
        'source jerusalem.json sha256 %s' % source_sha,
        'alignment UEcm = ((x+%.15f)*50, (z%+.15f)*50, y*50) - already baked, never reapplied'
        % (TX, TZ),
        'shell standoff %.1f cm outside every imported face' % SHELL_STANDOFF_CM,
        'AUTHORED detail: invented Old City massing, not survey',
    ]

    batches = []
    total_tris = 0
    detail_stats = {'windows': 0, 'arched': 0, 'doors': 0, 'domes': 0, 'tanks': 0,
                    'stairHeads': 0, 'quoinCorners': 0, 'partyEdges': 0, 'overBudget': 0}
    existing_preview, infill_preview = [], []

    for key in sorted(set(list(facade_cells) + list(infill_by_cell))):
        name = cell_name(key)
        cell_records = facade_cells.get(key, [])
        solids = []
        per_building = []
        for record in cell_records:
            box = record['boxCm']
            neighbours = [other for other in neighbour_index.query(
                box[0] - 300.0, box[1] - 300.0, box[2] + 300.0, box[3] + 300.0)
                if other is not record]
            built, triangles, stats = build_building_detail(
                record, neighbours, street_index, WINDOW_PITCH_CM)
            if triangles > MAX_TRIS_PER_BUILDING:
                detail_stats['overBudget'] += 1
            solids.extend(built)
            detail_stats['windows'] += stats.get('windows', 0)
            detail_stats['arched'] += stats.get('arched', 0)
            detail_stats['doors'] += stats.get('doors', 0)
            detail_stats['quoinCorners'] += stats.get('quoinCorners', 0)
            detail_stats['partyEdges'] += stats.get('partyEdges', 0)
            detail_stats['domes'] += 1 if stats.get('dome') else 0
            detail_stats['tanks'] += 1 if stats.get('tank') else 0
            detail_stats['stairHeads'] += 1 if stats.get('stairHead') else 0
            per_building.append({'osmId': record['id'], 'triangles': triangles,
                                 'floors': stats.get('floors'), 'windows': stats.get('windows'),
                                 'arched': stats.get('arched'),
                                 'windowPitchCm': round(stats.get('windowPitchCm', 0.0), 1)})
            existing_preview.append(record['loopCm'])
        entry = {'cell': list(key), 'name': name, 'facades': None, 'infill': None,
                 'buildings': len(cell_records)}
        if solids:
            info = write_obj(OBJ_DIR / ('SM_OldCityFacades_%s.obj' % name),
                             'SM_OldCityFacades_%s' % name, solids, provenance)
            info['buildings'] = len(cell_records)
            info['perBuildingTriangleMax'] = max((b['triangles'] for b in per_building), default=0)
            info['perBuilding'] = per_building
            entry['facades'] = info
            total_tris += info['triangles']
        del solids

        infill_records = (infill_by_cell.get(key) or {}).get('infill') or []
        if infill_records:
            infill_solids = []
            infill_summary = []
            for record in infill_records:
                triangles = 0
                for index, polygon in enumerate(record['wings']):
                    infill_solids.append(prism(polygon, record['baseZ'], record['roofZ']))
                    triangles += len(infill_solids[-1].faces)
                    siblings = [{'loopCm': other, 'boxCm': ring_bbox(other)}
                                for j, other in enumerate(record['wings']) if j != index]
                    box = ring_bbox(polygon)
                    nearby = [other for other in neighbour_index.query(
                        box[0] - 300.0, box[1] - 300.0, box[2] + 300.0, box[3] + 300.0)]
                    pseudo = {'id': record['id'] * 7 + index, 'loopCm': polygon,
                              'centreCm': ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0),
                              'baseZ': record['baseZ'], 'roofZ': record['roofZ']}
                    built, wing_tris, stats = build_building_detail(
                        pseudo, siblings + nearby, street_index, WINDOW_PITCH_CM)
                    infill_solids.extend(built)
                    triangles += wing_tris
                    detail_stats['windows'] += stats.get('windows', 0)
                    detail_stats['arched'] += stats.get('arched', 0)
                    detail_stats['domes'] += 1 if stats.get('dome') else 0
                    detail_stats['tanks'] += 1 if stats.get('tank') else 0
                    detail_stats['stairHeads'] += 1 if stats.get('stairHead') else 0
                    infill_preview.append(polygon)
                infill_summary.append({'infillId': record['infillId'], 'plan': record['plan'],
                                       'storeys': record['storeys'], 'wings': len(record['wings']),
                                       'yawDegrees': record['yawDegrees'],
                                       'baseZcm': round(record['baseZ'], 2),
                                       'roofZcm': round(record['roofZ'], 2),
                                       'triangles': triangles, 'tag': INFILL_TAG})
            info = write_obj(OBJ_DIR / ('SM_OldCityInfill_%s.obj' % name),
                             'SM_OldCityInfill_%s' % name, infill_solids, provenance)
            info['buildings'] = len(infill_records)
            info['tag'] = INFILL_TAG
            info['perBuilding'] = infill_summary
            entry['infill'] = info
            total_tris += info['triangles']
            del infill_solids
        if entry['facades'] or entry['infill']:
            batches.append(entry)

    if total_tris > MAX_TOTAL_TRIS:
        raise RuntimeError('Generated %d triangles, over the %d budget' % (total_tris, MAX_TOTAL_TRIS))

    # ------------------------------------------------------------------ coverage
    available_total = sum(entry['samplesAvailable'] for entry in infill_by_cell.values())
    before_total = sum(entry['builtBefore'] for entry in infill_by_cell.values())
    after_total = sum(entry['builtAfter'] for entry in infill_by_cell.values())
    coverage_before = before_total / float(available_total) if available_total else 0.0
    coverage_after = after_total / float(available_total) if available_total else 0.0
    cell_coverage = sorted((entry['coverageAfter'] for entry in infill_by_cell.values()))
    infill_count = sum(len(entry['infill']) for entry in infill_by_cell.values())

    # ------------------------------------------------------------------- grouping
    ordered = sorted(batches, key=lambda entry: -((entry['facades'] or {}).get('triangles', 0)
                                                  + (entry['infill'] or {}).get('triangles', 0)))
    groups = [{'group': index, 'cells': [], 'triangles': 0} for index in range(CELL_GROUPS)]
    for entry in ordered:
        target = min(groups, key=lambda group: group['triangles'])
        target['cells'].append(entry['name'])
        target['triangles'] += ((entry['facades'] or {}).get('triangles', 0)
                                + (entry['infill'] or {}).get('triangles', 0))
        entry['group'] = target['group']
    for group in groups:
        group['cells'].sort()

    preview_info = None
    if preview:
        preview_info = write_preview(PREVIEW_PATH, ring, zones, street_segments,
                                     existing_preview, infill_preview,
                                     {'existingBuildings': len(scope), 'infillBuildings': infill_count,
                                      'ringAreaM2': ring_area_m2,
                                      'coverageBefore': coverage_before,
                                      'coverageAfter': coverage_after})

    manifest = {
        'status': 'AUTHORED_OFFLINE_SOURCE_NATIVE_IMPORT_PENDING',
        'version': 'oldcity-facades-v1',
        'stamp': stamp,
        'generatorSha256': sha256_of(Path(__file__)),
        'selfTest': checks,
        'source': {
            'jerusalemJson': str(SOURCE_JSON), 'jerusalemJsonSha256': source_sha,
            'frozenBuildingsManifest': str(FROZEN_MANIFEST),
            'mountPlatformDesign': str(DESIGN_JSON),
            'mountPlatformDesignSha256': sha256_of(DESIGN_JSON),
            'unitsNote': 'source amot (0.5 m per amah), axes x=east y=up z=south',
            'alignmentUnrealCm': 'x_cm=(x+%.15f)*50, y_cm=(z%+.15f)*50, z_cm=y*50' % (TX, TZ),
            'alignmentBakedOnce': True,
            'footprintMethod': ('Per-building OSM polygons read directly from jerusalem.json and '
                                'passed through a byte-exact re-implementation of buildJerusalem(); '
                                'no bucket-mesh slicing was required.'),
            'sliceFallbackNotUsed': ('If the polygons had been unavailable the documented fallback '
                                     'was to slice each 100 m bucket mesh at base + 20 cm and walk '
                                     'the boundary loops of the section; it was not needed and was '
                                     'not implemented.'),
        },
        'reconstructionVerification': verification,
        'oldCity': {
            'wallChainOsmIds': [osm_id for osm_id, _ in OLD_CITY_CHAIN],
            'chainGaps': chain_gaps,
            'ringVertexCount': len(ring),
            'ringAreaM2': ring_area_m2,
            'ringBoundsCm': list(ring_box),
            'marginCm': OLD_CITY_MARGIN_CM,
            'buildingsInsideWalls': len(inside_only),
            'buildingsInScope': len(scope),
            'buildingsExtrudedCityWide': len(records),
            'sourceSkippedFootprints': source_skipped,
        },
        'exclusions': [{'kind': zone['kind'], 'osmId': zone['osmId'], 'name': zone['name'],
                        'vertices': len(zone['polygon']), 'bufferCm': zone['bufferCm']}
                       for zone in zones],
        'streets': {'segmentsIndexed': len(street_segments),
                    'infillBufferCm': INFILL_STREET_BUFFER_CM,
                    'bufferRasterised': True},
        'detail': {
            'shellStandoffCm': SHELL_STANDOFF_CM,
            'windowCm': [WINDOW_W, WINDOW_H], 'windowPitchCm': WINDOW_PITCH_CM,
            'floorCm': FLOOR_CM, 'archFraction': ARCH_FRACTION,
            'domeFraction': DOME_FRACTION, 'tankFraction': TANK_FRACTION,
            'stairHeadFraction': STAIRHEAD_FRACTION,
            'maxTrianglesPerBuilding': MAX_TRIS_PER_BUILDING,
            'counts': detail_stats,
        },
        'infill': {
            'tag': INFILL_TAG,
            'targetCoveragePerCell': INFILL_TARGET_COVERAGE,
            'buildings': infill_count,
            'maxPerCell': INFILL_MAX_PER_CELL,
            'storeys': list(INFILL_STOREYS),
            'coverageSampleSpacingCm': SAMPLE_STEP,
            'coverageBefore': round(coverage_before, 4),
            'coverageAfter': round(coverage_after, 4),
            'cellCoverageMedianAfter': cell_coverage[len(cell_coverage) // 2] if cell_coverage else 0.0,
            'cellsConsidered': len(infill_by_cell),
            'cellsAtOrAboveTarget': sum(1 for value in cell_coverage if value >= INFILL_TARGET_COVERAGE),
            'groundLedger': mask.summary(),
            'targetShortfallReason': (
                'The 6 m street buffer required by the brief blocks about a third of the walled, '
                'unprotected ground, and abutment gaps consume more, so 60 percent per cell is not '
                'geometrically reachable everywhere. groundLedger records exactly where the '
                'ground went; raising coverage further would mean building inside the street '
                'buffer.'),
            'perCell': [{'cell': list(key), 'name': cell_name(key),
                         'samplesAvailable': entry['samplesAvailable'],
                         'coverageBefore': entry['coverageBefore'],
                         'coverageAfter': entry['coverageAfter'],
                         'infillBuildings': len(entry['infill']),
                         'attempts': entry['attempts']}
                        for key, entry in sorted(infill_by_cell.items())],
        },
        'batches': batches,
        'groups': groups,
        'totals': {
            'objFiles': sum(1 for entry in batches for key in ('facades', 'infill') if entry[key]),
            'triangles': total_tris,
            'triangleBudget': MAX_TOTAL_TRIS,
            'cells': len(batches),
            'generationSeconds': round(time.time() - started, 2),
        },
        'preview': preview_info,
        'objConvention': OBJ_HEADER_NOTE,
        'nativePlan': {
            'namespace': '/Game/MikdashV3/JerusalemContext/OldCityFacadesV1',
            'facadeCollision': 'NoCollision (pure decoration over solid, already-colliding boxes)',
            'infillCollision': 'BlockAll, complex-as-simple (authored buildings are new solids)',
            'nanite': True,
            'placement': 'identity transform; every vertex is already world cm',
            'importer': 'Scripts/release_oldcity_facades.py (+ .spec.json)',
        },
        'limitations': [
            'AUTHORED: every window, arch, quoin, cornice, parapet, dome, tank, stair head and '
            'every infill building is invented massing in the style of the modern Old City. None '
            'of it is surveyed, photogrammetric or a claim about a particular building.',
            'Infill is tagged %s in this manifest, in the mesh names and in the actor labels; it '
            'is a density study, not OSM data.' % INFILL_TAG,
            'Coverage is measured on a %.0f cm sample raster clipped to the wall ring minus the '
            'Mount platform and the protected Kotel/plaza polygons; it is not a cadastral figure.'
            % SAMPLE_STEP,
            'Party-wall suppression probes %.0f cm outward from each edge midpoint; abutting '
            'buildings whose OSM polygons do not actually touch will still receive windows.'
            % PARTY_WALL_PROBE_CM,
            'Detail shells carry no vertex colours, so M_Context_Building falls back to white for '
            'its VertexColor input and its per-building hash tint is uniform across a batch.',
            'Generated meshes have placeholder planar UVs only; the context materials are '
            'triplanar and do not read them. No lightmap UVs are generated.',
            'No engine work is performed here: no import, no placement, no collision, no cook, no '
            'visual acceptance. Those belong to Scripts/release_oldcity_facades.py and a review.',
            'Terrain is unchanged: infill sits on the existing DEM height at its centre, so a '
            'building on a steep sample may float or sink at one corner.',
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


def _summary(manifest):
    return {
        'status': manifest['status'],
        'buildingsInScope': manifest['oldCity']['buildingsInScope'],
        'buildingsInsideWalls': manifest['oldCity']['buildingsInsideWalls'],
        'infillBuildings': manifest['infill']['buildings'],
        'coverageBefore': manifest['infill']['coverageBefore'],
        'coverageAfter': manifest['infill']['coverageAfter'],
        'triangles': manifest['totals']['triangles'],
        'objFiles': manifest['totals']['objFiles'],
        'cells': manifest['totals']['cells'],
        'groups': [{'group': group['group'], 'cells': len(group['cells']),
                    'triangles': group['triangles']} for group in manifest['groups']],
        'reconstructionMatchRatio': manifest['reconstructionVerification']['matchRatio'],
        'seconds': manifest['totals']['generationSeconds'],
    }


if __name__ == '__main__':
    manifest = generate(force='--force' in sys.argv, preview='--no-preview' not in sys.argv)
    print(json.dumps(_summary(manifest), indent=2))
