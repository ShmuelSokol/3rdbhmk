"""Guarded terrain cut under the precinct plaza - the *_PrecinctCut twins.

THE DEFECT THIS FIXES
---------------------
SourceAssets/enclosure-review/PLAZA-DESIGN-20260909.md section 6, open item 1:

    THE TERRAIN IS NOT CUT. On the fifth of the footprint where the ground stands above the
    deck - the Mount of Olives slope in the north-east, strips on the north and west - the
    existing DEM terrain tiles still rise through the paving.

The plaza deck is a flat slab at Z 0, one amah thick, so its UNDERSIDE is Z -48 (Candidate48)
or Z -50 (Main50). Every terrain vertex inside the precinct square that stands above that
underside pokes through the paving. This script cuts them to it.

THE MECHANISM - the FutureMountV1 precedent, extended
-----------------------------------------------------
Scripts/import_future_mount_terrain.py clips four tiles against a 185-vertex platform polygon
and writes NEW assets, never editing the imported originals. This does the same against a
rectangle, and then swaps by visibility rather than by re-meshing the original actor:

  * `SM_JerusalemTerrain_RR_CC_PrecinctCut` - the twin. Identical to the original everywhere
    OUTSIDE the precinct square, and inside it clamped to the deck underside: every part of
    the surface above Z_cut is replaced by a flat quarry floor at Z_cut exactly. That floor
    sits 48 cm below the deck top, so the slab hides it and there is no lip.
  * The twin is placed as its own actor, VISIBLE.
  * The ORIGINAL tile actor is hidden with SetActorHiddenInGame - the same call, and the same
    never-delete contract, the YECHEZKEL state already uses on 270 modern buildings - and its
    actor collision is disabled so the invisible hillside cannot block a walker on the deck.
    The original ASSET is never opened for write and never changes by a byte; the original
    ACTOR stays in the level with its transform, material and mesh untouched.

So MODERN restores the real hillside by flipping two booleans back on the actors tagged
`PrecinctCutOriginal`, and hiding the ones tagged `PrecinctCutTwin`. THAT FLIP IS NOT WIRED
BY THIS SCRIPT AND CANNOT BE: AMikdashEnclosure::GatherModernBuildings only ever considers
actors whose mesh lives in /Game/MikdashV3/JerusalemContext/Buildings/ or
.../OldCityFacadesV1/Meshes/ (BuildingIdentityLabel, MikdashEnclosure.cpp:22-42), so a terrain
actor cannot enter the hide list at all without a plugin change and a rebuild. The pair is
placed, tagged and receipted here so that wiring is a two-line hook; see the receipt's
`modernRestorationContract`.

Commandlet invocation (serial; never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_precinct_terrain_cut.py"
      -Candidate48 -CutAssets
      -EnablePlugins=GeometryScripting -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Cut-01.log"

ONE TARGET PER RUN: -Candidate48 (the cook map, run first) or -Main50. The precinct square is
a different rectangle on each, so the twins are per-target assets in their own folder.

ONE MODE PER RUN:
  -CutAssets   build and verify the twin meshes. Touches no map.
  -CutApply    place the twins, hide the originals, save, reopen, read back, measure.
  -CutVerify   reopen and measure. Saves nothing.
  -CutRevert   restore the originals and remove the twin actors, from a named apply receipt.

Run with no engine for the offline plan:
  python Scripts/release_precinct_terrain_cut.py -Candidate48
"""
import collections
import hashlib
import itertools
import json
import math
import struct
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
REVIEW = ROOT / 'SourceAssets/enclosure-review'
CHECKPOINT_ROOT = Path(r'C:\Mikdash\Working-5.8\ReviewCheckpoints')
TERRAIN_DIR = '/Game/MikdashV3/JerusalemContext/Terrain/'
TWIN_ROOT = '/Game/MikdashV3/PrecinctCutV1'
TWIN_SUFFIX = '_PrecinctCut'
TWIN_TAG = 'PrecinctCutTwin'
ORIGINAL_TAG = 'PrecinctCutOriginal'
LABEL_PREFIX = 'RELEASE_PrecinctCut_'
# The Western Wall Plaza cut is a different intervention on the same terrain, driven by the
# KotelPlazaV1 plan and not by the precinct, so it gets its own namespace, tags and labels and
# can be reverted on its own.
KOTEL_ROOT = '/Game/MikdashV3/KotelPlazaCutV1'
KOTEL_SUFFIX = '_KotelPlazaCut'
KOTEL_TWIN_TAG = 'KotelPlazaCutTwin'
KOTEL_ORIGINAL_TAG = 'KotelPlazaCutOriginal'
KOTEL_LABEL_PREFIX = 'RELEASE_KotelPlazaCut_'
# The KotelPlazaV1 earthwork measurement used a 100 cm step over 5,589 stations. The same
# step is used here so the before and after numbers are comparable.
KOTEL_SAMPLE_SPACING_CM = 100.0

TARGET_FLAGS = {'-candidate48': 'Candidate48', '-main50': 'Main50'}
MODE_FLAGS = {'-cutassets': 'assets', '-cutapply': 'apply',
              '-cutverify': 'verify', '-cutrevert': 'revert'}

PROTECTED_MAPS = ['/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
                  '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
                  '/Game/MikdashV3/Maps/Courtyard',
                  '/Game/MikdashV3/FutureMountV1/L_FutureMount',
                  '/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold']

TARGETS = {
    'Candidate48': dict(
        map='/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough',
        mapFile='Content/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough.umap',
        amahCm=48.0,
        precinctReceipt='SourceAssets/enclosure-review/precinct-Candidate48.json',
        plazaReceipt='SourceAssets/enclosure-review/plaza-Candidate48.json'),
    'Main50': dict(
        map='/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough',
        mapFile='Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap',
        amahCm=50.0,
        precinctReceipt='SourceAssets/enclosure-review/precinct-Main50.json',
        plazaReceipt='SourceAssets/enclosure-review/plaza-Main50.json'),
}

# Acceptance sampling. 1000 cm = 10 m over a 1.44 km square is 144x144 = 20,736 stations,
# which is dense enough to catch a single 400 m DEM tile's 25 m cell and cheap enough to run
# inside the commandlet. Reported with the number so the number means something.
SAMPLE_SPACING_CM = 1000.0
# Outside-unchanged sampling is finer, because that check is the regression guard.
OUTSIDE_SPACING_CM = 500.0
AREA_EPSILON_CM2 = 1e-4
# StaticMesh source models store float32 positions, so a vertex written at exactly the deck
# underside reads back a fraction of a micrometre either side of it. 0.05 cm is the same
# tolerance Scripts/import_future_mount_terrain.py uses for the same reason, and it is four
# orders of magnitude below anything a viewer could see.
TOLERANCE_CM = 0.05


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def flag_from(command_line, table, what):
    lowered = ' %s ' % command_line.lower()
    chosen = [name for flag, name in table.items()
              if (' %s ' % flag) in lowered or ('%s=' % flag) in lowered]
    if len(chosen) > 1:
        raise RuntimeError('Choose exactly one %s of %s' % (what, list(table)))
    return chosen[0] if chosen else None


# =====================================================================================
# Geometry: the clip-and-clamp, engine-free so it can be reasoned about and tested offline
# =====================================================================================
#
# Every output vertex is carried as BARYCENTRIC weights on its source triangle, never as a
# free position. Position, normal and vertex colour are then all one interpolation of the
# SAME weights, so a clipped corner cannot drift away from the surface it came from, and a
# corner that lands exactly on an original corner reproduces that corner's own attributes.

def bary_point(triangle, weights):
    return [sum(weights[i] * triangle[i][axis] for i in range(3)) for axis in range(3)]


def polygon_area2d(points):
    total = 0.0
    for i in range(len(points)):
        x0, y0 = points[i][0], points[i][1]
        x1, y1 = points[(i + 1) % len(points)][0], points[(i + 1) % len(points)][1]
        total += x0 * y1 - x1 * y0
    return 0.5 * total


def split_polygon(weights_list, value_of, threshold, keep_greater):
    """Split a convex polygon (list of barycentric weight triples) by a LINEAR function.

    `value_of(w)` is linear in the weights - x, y or z - so the crossing parameter is exact
    and the two halves share the crossing vertices exactly. Returns (kept, other) where kept
    is the side satisfying the test.

    A vertex lying EXACTLY on the plane belongs to BOTH halves. Giving it to one only is the
    classic way to lose a sliver of area at every boundary vertex, and this cut runs along a
    1.44 km rectangle whose corners fall on DEM grid lines, so exact hits are the common case,
    not the rare one. `area2dErrorCm2` in the receipt is what proves it did not happen.
    """
    if not weights_list:
        return [], []
    values = [value_of(w) - threshold for w in weights_list]
    if not keep_greater:
        values = [-v for v in values]
    if all(v >= 0.0 for v in values):
        return list(weights_list), []
    if all(v <= 0.0 for v in values):
        return [], list(weights_list)
    kept, other = [], []
    count = len(weights_list)
    for i in range(count):
        j = (i + 1) % count
        wi, wj = weights_list[i], weights_list[j]
        vi, vj = values[i], values[j]
        if vi >= 0.0:
            kept.append(wi)
        if vi <= 0.0:
            other.append(wi)
        if (vi > 0.0 and vj < 0.0) or (vi < 0.0 and vj > 0.0):
            t = vi / (vi - vj)
            crossing = tuple(wi[k] + t * (wj[k] - wi[k]) for k in range(3))
            kept.append(crossing)
            other.append(crossing)
    return kept, other


def partition(triangle, regions):
    """One source triangle -> [(polygon, clamp target Z or None)].

    `regions` is an ordered list of (rect, targetZ). A piece inside more than one region
    takes the LOWEST target, so overlapping cuts compose instead of fighting. A piece in no
    region has target None and is reproduced exactly.
    """
    corners = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
    x_of = lambda w: bary_point(triangle, w)[0]
    y_of = lambda w: bary_point(triangle, w)[1]
    pieces = [(corners, None)]
    for rect, target_z in regions:
        x_min, y_min, x_max, y_max = rect
        following = []
        for polygon, target in pieces:
            points = [bary_point(triangle, w) for w in polygon]
            if (max(p[0] for p in points) <= x_min or min(p[0] for p in points) >= x_max
                    or max(p[1] for p in points) <= y_min or min(p[1] for p in points) >= y_max):
                following.append((polygon, target))
                continue
            remainder = polygon
            for value_of, threshold, keep_greater in ((x_of, x_min, True), (x_of, x_max, False),
                                                      (y_of, y_min, True), (y_of, y_max, False)):
                remainder, outside = split_polygon(remainder, value_of, threshold, keep_greater)
                if len(outside) >= 3:
                    following.append((outside, target))
                if not remainder:
                    break
            if remainder:
                following.append((remainder,
                                  target_z if target is None else min(target, target_z)))
        pieces = following
    return pieces


def clip_and_clamp(triangle, regions):
    """Split every piece that has a clamp target by the plane z = target, so the part that
    stood above it can be laid flat ON it and the part below it kept untouched."""
    kept, flat = [], []
    z_of = lambda w: bary_point(triangle, w)[2]
    for polygon, target in partition(triangle, regions):
        if len(polygon) < 3:
            continue
        if target is None:
            kept.append(polygon)
            continue
        below, above = split_polygon(polygon, z_of, target, False)
        if len(below) >= 3:
            kept.append(below)
        if len(above) >= 3:
            flat.append((above, target))
    return kept, flat


def fan(polygon):
    return [(polygon[0], polygon[i], polygon[i + 1]) for i in range(1, len(polygon) - 1)]


def normalized(vector):
    length = math.sqrt(sum(v * v for v in vector))
    if length < 1e-9:
        return [0.0, 0.0, 1.0]
    return [v / length for v in vector]


def build_twin(triangles, regions):
    """triangles: [{'positions':[[x,y,z]]*3,'normals':...,'colors':...}] straight off the
    original StaticMesh source model. Returns the twin's expanded buffers plus the bookkeeping
    the receipt needs. Vertices are expanded per output triangle, exactly as the FutureMountV1
    adapter does, so every corner's attributes stay explicit."""
    positions, normals, colors = [], [], []
    source_area = kept_area = flat_area = 0.0
    winding_agrees = winding_total = 0
    flattened_source_triangles = 0
    for triangle in triangles:
        corner_positions = triangle['positions']
        source_sign = polygon_area2d(corner_positions)
        source_area += abs(source_sign)
        kept, flat = clip_and_clamp(corner_positions, regions)
        if flat:
            flattened_source_triangles += 1
        for polygon, target in [(p, None) for p in kept] + list(flat):
            points = [bary_point(corner_positions, w) for w in polygon]
            area = polygon_area2d(points)
            if abs(area) <= AREA_EPSILON_CM2:
                continue
            if target is None:
                kept_area += abs(area)
            else:
                flat_area += abs(area)
            for face in fan(polygon):
                face_points = [bary_point(corner_positions, w) for w in face]
                face_area = polygon_area2d(face_points)
                if abs(face_area) <= AREA_EPSILON_CM2:
                    continue
                winding_total += 1
                # UE is left-handed; a generated tile that faces down renders black. The
                # source triangle's own 2D orientation is the reference, not an assumption.
                if (face_area > 0.0) == (source_sign > 0.0):
                    winding_agrees += 1
                for weights, point in zip(face, face_points):
                    if target is None:
                        positions.append(point)
                        normals.append(normalized(bary_point(triangle['normals'], weights)))
                    else:
                        positions.append([point[0], point[1], target])
                        normals.append([0.0, 0.0, 1.0])
                    colors.append([sum(weights[i] * triangle['colors'][i][axis] for i in range(3))
                                   for axis in range(4)])
    return dict(positions=positions, normals=normals, colors=colors,
                triangles=len(positions) // 3,
                sourceTriangles=len(triangles),
                flattenedSourceTriangles=flattened_source_triangles,
                sourceArea2dCm2=source_area,
                keptArea2dCm2=kept_area,
                flattenedArea2dCm2=flat_area,
                area2dErrorCm2=abs((kept_area + flat_area) - source_area),
                windingAgrees=winding_agrees, windingTriangles=winding_total)


# ---------------------------------------------------------------------------
# Height sampling over a triangle soup - the acceptance measurement
# ---------------------------------------------------------------------------

class HeightField(object):
    """Upper-envelope height lookup over a triangle soup, on a uniform bucket grid."""

    CELL_CM = 2000.0

    def __init__(self):
        self.buckets = {}

    def add(self, faces):
        for face in faces:
            xs = [p[0] for p in face]
            ys = [p[1] for p in face]
            i0, i1 = int(math.floor(min(xs) / self.CELL_CM)), int(math.floor(max(xs) / self.CELL_CM))
            j0, j1 = int(math.floor(min(ys) / self.CELL_CM)), int(math.floor(max(ys) / self.CELL_CM))
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    self.buckets.setdefault((i, j), []).append(face)

    def height(self, x, y):
        key = (int(math.floor(x / self.CELL_CM)), int(math.floor(y / self.CELL_CM)))
        best = None
        for a, b, c in self.buckets.get(key, ()):
            den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if den == 0.0:
                continue
            w0 = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / den
            w1 = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / den
            w2 = 1.0 - w0 - w1
            if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
                continue
            z = w0 * a[2] + w1 * b[2] + w2 * c[2]
            if best is None or z > best:
                best = z
        return best


def triangle_key(points):
    """StaticMesh source descriptions store float32 positions, so canonicalise ONLY the hash
    lookup and keep the unrounded coordinates for every numerical claim. Same device, and the
    same reason, as Scripts/import_future_mount_terrain.py."""
    to_f32 = lambda v: struct.unpack('<f', struct.pack('<f', v))[0]
    return tuple(sorted((round(to_f32(p[0])), round(to_f32(p[1]))) for p in points))


def check_corners(actual, expected):
    """Every saved corner against the corner this run intended - position, vertex colour and
    normal - matched by triangle rather than by index, because the asset pipeline is free to
    reorder. This is what proves a REUSED twin is byte-for-byte the twin we would have made."""
    if len(actual) * 3 != len(expected['positions']):
        raise RuntimeError('Twin has %d triangles, expected %d'
                           % (len(actual), len(expected['positions']) // 3))
    buckets = collections.defaultdict(list)
    for start in range(0, len(expected['positions']), 3):
        buckets[triangle_key(expected['positions'][start:start + 3])].append(start)
    max_position = max_color = max_normal = 0.0
    for triangle in actual:
        candidates = buckets[triangle_key(triangle['positions'])]
        if not candidates:
            raise RuntimeError('Saved triangle has no counterpart in the intended twin')
        found = None
        for start in candidates:
            for permutation in itertools.permutations(range(3)):
                pe = max(abs(triangle['positions'][i][k]
                             - expected['positions'][start + permutation[i]][k])
                         for i in range(3) for k in range(3))
                ce = max(abs(triangle['colors'][i][k]
                             - expected['colors'][start + permutation[i]][k])
                         for i in range(3) for k in range(4))
                ne = max(abs(triangle['normals'][i][k]
                             - expected['normals'][start + permutation[i]][k])
                         for i in range(3) for k in range(3))
                if pe < TOLERANCE_CM and ce < 1e-6 and ne < 1e-5:
                    found = (start, pe, ce, ne)
                    break
            if found:
                break
        if not found:
            raise RuntimeError('Saved corner geometry, colour or normal does not match')
        candidates.remove(found[0])
        max_position = max(max_position, found[1])
        max_color = max(max_color, found[2])
        max_normal = max(max_normal, found[3])
    if any(buckets.values()):
        raise RuntimeError('The saved twin is missing triangles the intended twin has')
    return dict(maxPositionErrorCm=max_position, maxLinearColorError=max_color,
                maxNormalError=max_normal)


class RegionIndex(object):
    """Point -> lowest clamp target among the cut regions covering it."""

    CELL_CM = 2000.0

    def __init__(self, regions):
        self.regions = list(regions)
        self.buckets = {}
        for rect, target in self.regions:
            i0, i1 = int(math.floor(rect[0] / self.CELL_CM)), int(math.floor(rect[2] / self.CELL_CM))
            j0, j1 = int(math.floor(rect[1] / self.CELL_CM)), int(math.floor(rect[3] / self.CELL_CM))
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    self.buckets.setdefault((i, j), []).append((rect, target))

    def target(self, x, y, margin=0.0):
        """Lowest clamp target among the regions covering (x, y), inset by `margin`.

        The margin is not cosmetic. A vertex that sits EXACTLY on a cut boundary belongs to
        both the flattened piece and the kept piece, and the kept copy keeps its full original
        height - that is the cut face, and it is correct. Saved source models are float32, so
        at |x| ~ 20,000 cm a boundary coordinate that is not exactly representable reads back
        up to ~0.002 cm to either side. Testing such a vertex as "inside the cut" would report
        the whole height of the hillside as a violation. A margin of one TOLERANCE_CM is four
        orders of magnitude below anything visible and two above that quantisation.
        """
        key = (int(math.floor(x / self.CELL_CM)), int(math.floor(y / self.CELL_CM)))
        best = None
        for rect, target in self.buckets.get(key, ()):
            if not (rect[0] + margin < x < rect[2] - margin
                    and rect[1] + margin < y < rect[3] - margin):
                continue
            if best is None or target < best:
                best = target
        return best


def grid_stations(rect, spacing):
    x_min, y_min, x_max, y_max = rect
    nx = max(2, int(math.floor((x_max - x_min) / spacing)) + 1)
    ny = max(2, int(math.floor((y_max - y_min) / spacing)) + 1)
    dx = (x_max - x_min) / (nx - 1)
    dy = (y_max - y_min) / (ny - 1)
    return [(x_min + i * dx, y_min + j * dy) for i in range(nx) for j in range(ny)], nx, ny, dx, dy


# =====================================================================================
# Offline plan
# =====================================================================================
def merge_rectangles(rectangles):
    """Cells that share a Y band and touch in X become one rectangle. 926 Kotel deck cells
    collapse to a few dozen, which is what keeps the per-triangle clip affordable."""
    merged = []
    for rect, target in sorted(rectangles, key=lambda r: (r[1], round(r[0][1], 6),
                                                          round(r[0][3], 6), r[0][0])):
        if merged:
            last, last_target = merged[-1]
            if (last_target == target and abs(last[1] - rect[1]) < 1e-6
                    and abs(last[3] - rect[3]) < 1e-6 and rect[0] <= last[2] + 1e-6):
                merged[-1] = ([last[0], last[1], max(last[2], rect[2]), last[3]], target)
                continue
        merged.append((list(rect), target))
    return merged


def tile_for(bbox):
    """Which 400 m DEM tile a footprint sits on, and how far it is from the nearest tile edge.
    The tile grid origin is the terrain manifest's own tile 00_00 minimum corner."""
    origin_x, origin_y, size = -319124.51171875, -320027.5634765625, 40000.0
    i = int(math.floor((bbox[0] - origin_x) / size))
    j = int(math.floor((bbox[1] - origin_y) / size))
    x_min, y_min = origin_x + i * size, origin_y + j * size
    if not (x_min <= bbox[0] and bbox[2] <= x_min + size
            and y_min <= bbox[1] and bbox[3] <= y_min + size):
        raise RuntimeError('Footprint %s is not interior to one 400 m tile' % bbox)
    clearance = min(bbox[0] - x_min, x_min + size - bbox[2],
                    bbox[1] - y_min, y_min + size - bbox[3])
    return 'SM_JerusalemTerrain_%02d_%02d' % (i, j), clearance


def kotel_job():
    """The Western Wall Plaza cut. Its polygon, its two deck levels and its 200 cm wall guard
    are all taken from the KotelPlazaV1 receipts rather than re-derived: the cut region IS the
    926 deck cells that generator already clipped to OSM way 26492734 and already pulled back
    from the Kotel, so the cut cannot disagree with the plaza that will stand on it."""
    folder = ROOT / 'SourceAssets/context-review/KotelPlazaV1'
    manifest = json.loads((folder / 'kotel-plaza-manifest.json').read_text(encoding='utf-8-sig'))
    plan = json.loads((folder / 'kotel-plaza-plan.json').read_text(encoding='utf-8-sig'))
    if sha256_of(folder / 'kotel-plaza-plan.json') != manifest['planSha256']:
        raise RuntimeError('kotel-plaza-plan.json does not match the manifest hash')
    # SM_PlazaV1_DeckTile, canonicalBoundsCm from plaza-manifest.json: 1250 cm square about
    # its centre, ONE AMAH (50 cm at the module bake) thick, its origin ON THE DECK PLANE and
    # the slab hanging below it. So the underside is the instance Z minus the thickness.
    plaza_manifest = json.loads((REVIEW / 'plaza-manifest.json').read_text(encoding='utf-8-sig'))
    deck_mesh = next(m for m in plaza_manifest['meshes'] if m['name'] == 'SM_PlazaV1_DeckTile')
    bounds = deck_mesh['canonicalBoundsCm']
    half_x = 0.5 * (bounds['max'][0] - bounds['min'][0])
    half_y = 0.5 * (bounds['max'][1] - bounds['min'][1])
    thickness = bounds['max'][2] - bounds['min'][2]
    if abs(bounds['max'][2]) > 1e-9:
        raise RuntimeError('The deck tile origin is not on the deck plane')
    rectangles = []
    levels = {}
    for instance in plan['deck']:
        location, rotation, scale = instance['loc'], instance['rot'], instance['scale']
        if max(abs(v) for v in rotation) > 1e-9:
            raise RuntimeError('A Kotel deck cell is rotated; the cut assumes axis-aligned cells')
        if abs(scale[2] - 1.0) > 1e-9:
            raise RuntimeError('A Kotel deck cell is scaled in Z; the slab thickness would move')
        underside = location[2] - thickness
        levels[round(location[2], 3)] = round(underside, 3)
        rectangles.append(([location[0] - half_x * scale[0], location[1] - half_y * scale[1],
                            location[0] + half_x * scale[0], location[1] + half_y * scale[1]],
                           underside))
    for key in ('lowerDeckZCm', 'upperDeckZCm'):
        if round(manifest['derived'][key], 3) not in levels:
            raise RuntimeError('The plan carries no deck cell at the manifest %s' % key)
    bbox = [min(r[0][0] for r in rectangles), min(r[0][1] for r in rectangles),
            max(r[0][2] for r in rectangles), max(r[0][3] for r in rectangles)]
    tile, clearance = tile_for(bbox)
    regions = merge_rectangles(rectangles)
    return dict(kind='kotel', tile=tile, folder=KOTEL_ROOT, suffix=KOTEL_SUFFIX,
                regions=regions, sampleSpacingCm=KOTEL_SAMPLE_SPACING_CM,
                twinTag=KOTEL_TWIN_TAG, originalTag=KOTEL_ORIGINAL_TAG,
                labelPrefix=KOTEL_LABEL_PREFIX,
                # The Kotel plaza is a MODERN feature and its decks are 11 m BELOW the
                # precinct deck, so in YECHEZKEL this cut is buried under the plaza slab and
                # its twin must NOT be the visible one. It is placed hidden, tagged, and
                # shown by the same state hook the precinct twins need.
                twinVisible=False, hideOriginal=False,
                summary=dict(osmWay=manifest['source']['plazaOsmId'],
                             plazaAreaM2=manifest['sourced']['plazaAreaM2'],
                             wallGuardCm=manifest['sourced']['wallGuardCm'],
                             deckCells=len(rectangles), mergedRegions=len(regions),
                             deckCellsDroppedForWallGuard=manifest['derived']['deckCellsDroppedForWallGuard'],
                             deckTopToUndersideCm=thickness,
                             deckLevelsTopToUndersideZCm=levels,
                             footprintBboxCm=bbox, tile=tile,
                             clearanceToNearestTileEdgeCm=clearance,
                             manifestSha256=sha256_of(folder / 'kotel-plaza-manifest.json'),
                             planSha256=manifest['planSha256']))


def offline_plan(target):
    config = TARGETS[target]
    precinct = json.loads((ROOT / config['precinctReceipt']).read_text(encoding='utf-8-sig'))
    plaza = json.loads((ROOT / config['plazaReceipt']).read_text(encoding='utf-8-sig'))
    faces = precinct['square']['outerFacesCm']
    rect = [float(faces['xWest']), float(faces['yNorth']),
            float(faces['xEast']), float(faces['ySouth'])]
    paved = [float(plaza['grid']['xMinCm']), float(plaza['grid']['yMinCm']),
             float(plaza['grid']['xMaxCm']), float(plaza['grid']['yMaxCm'])]
    amah = float(config['amahCm'])
    if abs(float(plaza['deck']['slabThicknessCm']) - amah) > 1e-9:
        raise RuntimeError('Deck slab is not one amah on %s' % target)
    if abs(float(plaza['deck']['topZcm'])) > 1e-9:
        raise RuntimeError('Deck top is not Z 0 on %s' % target)
    z_cut = -amah
    # The paved rectangle must be the square inset by one 6-amah wall thickness. Re-derived
    # here rather than trusted, because the cut line and the paving edge have to agree.
    inset = 6.0 * amah
    for value, expected in zip(paved, [rect[0] + inset, rect[1] + inset,
                                       rect[2] - inset, rect[3] - inset]):
        if abs(value - expected) > 1e-6:
            raise RuntimeError('Paved rectangle is not the square inset by 6 amot on ' + target)
    tiles = ['SM_JerusalemTerrain_%02d_%02d' % (i, j)
             for i in range(7, 11) for j in range(7, 11)]
    jobs = [dict(kind='precinct', tile=name, folder='%s/%s' % (TWIN_ROOT, target),
                 suffix=TWIN_SUFFIX, regions=[(list(rect), z_cut)],
                 sampleSpacingCm=OUTSIDE_SPACING_CM, twinTag=TWIN_TAG,
                 originalTag=ORIGINAL_TAG, labelPrefix=LABEL_PREFIX,
                 twinVisible=True, hideOriginal=True) for name in tiles]
    kotel = kotel_job()
    jobs.append(kotel)
    return dict(target=target, map=config['map'], amahCm=amah,
                deckTopZcm=0.0, deckUndersideZcm=z_cut,
                precinctOuterFacesCm=dict(xWest=rect[0], yNorth=rect[1],
                                          xEast=rect[2], ySouth=rect[3]),
                pavedRectCm=dict(xMin=paved[0], yMin=paved[1], xMax=paved[2], yMax=paved[3]),
                precinctTiles=tiles, precinctTwinFolder='%s/%s' % (TWIN_ROOT, target),
                kotelPlazaCut=kotel['summary'],
                jobs=jobs, rect=rect, paved=paved, zCut=z_cut)


# =====================================================================================
# Native
# =====================================================================================
class Native(object):
    def __init__(self, ue, target, mode, stamp):
        self.ue = ue
        self.target = target
        self.mode = mode
        self.stamp = stamp
        for name in ('GeometryScript_MeshEdits', 'GeometryScript_NewAssetUtils',
                     'GeometryScript_AssetUtils', 'GeometryScript_MeshQueries'):
            if not hasattr(ue, name):
                raise RuntimeError('Launch with -EnablePlugins=GeometryScripting: ' + name)
        self.edits = ue.GeometryScript_MeshEdits
        self.creator = ue.GeometryScript_NewAssetUtils
        self.query = ue.GeometryScript_MeshQueries
        self.asset_utils = ue.GeometryScript_AssetUtils
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.receipt = {}
        self.receipt_path = None

    def write_receipt(self):
        self.receipt_path.parent.mkdir(parents=True, exist_ok=True)
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, sort_keys=False) + '\n',
                                     encoding='utf-8')

    # -- mesh IO -----------------------------------------------------------
    def extract(self, mesh):
        ue = self.ue
        dynamic = ue.DynamicMesh()
        options = ue.GeometryScriptCopyMeshFromAssetOptions()
        options.set_editor_property('apply_build_settings', False)
        options.set_editor_property('request_tangents', False)
        options.set_editor_property('use_build_scale', False)
        lod = ue.GeometryScriptMeshReadLOD()
        lod.set_editor_property('lod_type', ue.GeometryScriptLODType.SOURCE_MODEL)
        lod.set_editor_property('lod_index', 0)
        result = self.asset_utils.copy_mesh_from_static_mesh_v2(mesh, dynamic, options, lod)
        if ue.GeometryScriptOutcomePins.SUCCESS not in result:
            raise RuntimeError('Source-mesh extraction failed for ' + mesh.get_path_name())
        triangles = []
        for tid in range(dynamic.get_triangle_count()):
            position_result = self.query.get_triangle_positions(dynamic, tid)
            positions = [[v.x, v.y, v.z] for v in position_result if isinstance(v, ue.Vector)]
            normal_result = self.query.get_triangle_normals(dynamic, tid)
            normals = [[v.x, v.y, v.z] for v in normal_result if isinstance(v, ue.Vector)]
            color_result = self.query.get_triangle_vertex_colors(dynamic, tid)
            colors = [[v.r, v.g, v.b, v.a] for v in color_result if isinstance(v, ue.LinearColor)]
            if len(positions) != 3 or len(normals) != 3 or len(colors) != 3:
                raise RuntimeError('Incomplete triangle readback on ' + mesh.get_path_name())
            triangles.append(dict(positions=positions, normals=normals, colors=colors))
        return triangles

    def create_twin(self, path, buffers, source_mesh):
        ue = self.ue
        simple = ue.GeometryScriptSimpleMeshBuffers()
        simple.set_editor_property('vertices', [ue.Vector(*v) for v in buffers['positions']])
        simple.set_editor_property('normals', [ue.Vector(*v) for v in buffers['normals']])
        simple.set_editor_property('vertex_colors',
                                   [ue.LinearColor(*v) for v in buffers['colors']])
        simple.set_editor_property('triangles', [ue.IntVector(i, i + 1, i + 2)
                                                 for i in range(0, len(buffers['positions']), 3)])
        # Nondegenerate metric UVs so tangents can be generated; the terrain material samples
        # vertex colour, not UVs, so this changes nothing that is rendered.
        simple.set_editor_property('uv0', [ue.Vector2D(v[0] / 100.0, v[1] / 100.0)
                                           for v in buffers['positions']])
        dynamic = ue.DynamicMesh()
        self.edits.append_buffers_to_mesh(dynamic, simple)
        options = ue.GeometryScriptCreateNewStaticMeshAssetOptions()
        for key, value in dict(enable_recompute_normals=False, enable_recompute_tangents=True,
                               enable_nanite=self.nanite_enabled(source_mesh),
                               enable_collision=True,
                               collision_mode=ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,
                               use_original_vertex_order=True).items():
            options.set_editor_property(key, value)
        result = self.creator.create_new_static_mesh_asset_from_mesh(dynamic, path, options)
        meshes = [v for v in result if isinstance(v, ue.StaticMesh)]
        if len(meshes) != 1 or ue.GeometryScriptOutcomePins.SUCCESS not in result:
            raise RuntimeError('create_new_static_mesh_asset_from_mesh failed for ' + path)
        return meshes[0]

    def nanite_enabled(self, mesh):
        try:
            return bool(mesh.get_editor_property('nanite_settings').get_editor_property('enabled'))
        except Exception:                                                        # noqa: BLE001
            return False

    def check_readback(self, mesh, buffers, regions, original_triangles, sample_spacing):
        """What is on disk, not what we asked for: read the saved source model back and
        measure it against the intent AND against the original tile.

        Returns THE NUMBER for this tile - the highest any twin vertex, and any station of a
        sampling grid, stands above the deck underside it was cut to - together with the
        regression guard that the surface OUTSIDE every cut region did not move."""
        actual = self.extract(mesh)
        if len(actual) * 3 != len(buffers['positions']):
            raise RuntimeError('Twin has %d triangles, expected %d'
                               % (len(actual), len(buffers['positions']) // 3))
        corners = check_corners(actual, buffers)
        faces = [t['positions'] for t in actual]
        index = RegionIndex(regions)
        vertex_worst = None
        for face in faces:
            for point in face:
                target = index.target(point[0], point[1], margin=TOLERANCE_CM)
                if target is None:
                    continue
                height = point[2] - target
                if vertex_worst is None or height > vertex_worst:
                    vertex_worst = height
        area = sum(abs(polygon_area2d(face)) for face in faces)
        source_area = sum(abs(polygon_area2d(t['positions'])) for t in original_triangles)
        twin_field = HeightField()
        twin_field.add(faces)
        original_field = HeightField()
        original_field.add([t['positions'] for t in original_triangles])
        tile_rect = [min(p[0] for f in faces for p in f), min(p[1] for f in faces for p in f),
                     max(p[0] for f in faces for p in f), max(p[1] for f in faces for p in f)]
        stations, nx, ny, dx, dy = grid_stations(tile_rect, sample_spacing)
        outside_samples = inside_samples = above_samples = boundary_samples = 0
        outside_max_delta = 0.0
        grid_worst = None
        for x, y in stations:
            target = index.target(x, y, margin=TOLERANCE_CM)
            if target is None and index.target(x, y, margin=-TOLERANCE_CM) is not None:
                # Within a hair of a cut boundary: neither an interior station nor an
                # untouched one. Counted and reported rather than silently assigned.
                boundary_samples += 1
                continue
            twin_z = twin_field.height(x, y)
            if target is not None:
                if twin_z is None:
                    continue
                inside_samples += 1
                height = twin_z - target
                if height > TOLERANCE_CM:
                    above_samples += 1
                if grid_worst is None or height > grid_worst:
                    grid_worst = height
                continue
            # Outside every cut region: the regression guard. A cut that quietly flattened
            # land beyond the boundary shows up here as a non-zero difference.
            original_z = original_field.height(x, y)
            if original_z is None and twin_z is None:
                continue
            if original_z is None or twin_z is None:
                raise RuntimeError('Outside the cut one surface exists and the other does not '
                                   'at (%g, %g)' % (x, y))
            outside_samples += 1
            outside_max_delta = max(outside_max_delta, abs(original_z - twin_z))
        return dict(triangles=len(actual), corners=corners,
                    area2dCm2=area, sourceArea2dCm2=source_area,
                    area2dErrorCm2=abs(area - source_area),
                    maxVertexHeightAboveDeckUndersideCm=vertex_worst,
                    gridSpacingCm=sample_spacing,
                    stationsInsideCut=inside_samples,
                    stationsAboveDeckUnderside=above_samples,
                    maxGridHeightAboveDeckUndersideCm=grid_worst,
                    outsideStations=outside_samples,
                    boundaryStationsSkipped=boundary_samples,
                    boundaryMarginCm=TOLERANCE_CM,
                    outsideMaxHeightDifferenceCm=outside_max_delta)

    # -- actors ------------------------------------------------------------
    def mesh_of(self, actor):
        component = actor.get_component_by_class(self.ue.StaticMeshComponent)
        if component is None:
            return None, None
        return component, component.get_editor_property('static_mesh')

    def terrain_actors(self):
        """Every actor in the loaded level whose single static mesh is a terrain tile, with
        what it actually renders and whether it is currently visible. Recorded in the receipt
        before anything is touched, so a lookup that finds nothing says WHY."""
        rows = []
        for actor in self.actors.get_all_level_actors():
            component, mesh = self.mesh_of(actor)
            if mesh is None:
                continue
            name = mesh.get_name()
            if not name.startswith('SM_JerusalemTerrain_'):
                continue
            rows.append(dict(actor=actor.get_name(), label=actor.get_actor_label(),
                             mesh=name, meshPath=mesh.get_path_name().split('.')[0],
                             hiddenInGame=bool(actor.get_editor_property('hidden')),
                             collision=bool(actor.get_actor_enable_collision()),
                             actor_object=actor, component_object=component))
        return rows

    def tile_actors(self, tiles):
        """Matched by ACTOR LABEL, with the mesh name as a fallback.

        The label is the stable identity of a DEM tile in these levels; the MESH is not. Four
        tiles - 07_07, 07_08, 08_07 and 08_08 - already render the FutureMountV1 platform-cut
        twins here, not the imported originals, because that pass swapped their component
        meshes. Keying off the asset folder would have quietly rebuilt those four from the
        pristine originals and FILLED THE PLATFORM HOLE BACK IN.
        """
        wanted = set(tiles)
        found = {}
        for row in self.terrain_actors():
            key = row['label'] if row['label'] in wanted else (
                row['mesh'] if row['mesh'] in wanted else None)
            if key is not None:
                found.setdefault(key, []).append(row)
        return found


def numeric_transform(ue, transform):
    values = []
    for point in [(0, 0, 0), (100, 0, 0), (0, 100, 0), (0, 0, 100)]:
        location = transform.transform_location(ue.Vector(*point))
        values.extend([location.x, location.y, location.z])
    return tuple(round(v, 6) for v in values)


def run(target, mode, revert_receipt=None):
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    if target is None:
        raise RuntimeError('Choose the target map: %s' % list(TARGET_FLAGS))
    plan = offline_plan(target)
    config = TARGETS[target]
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    native = Native(ue, target, mode, stamp)

    if native.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or \
       ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before checkpointed work')

    target_map = config['map']
    map_file = ROOT / config['mapFile']
    map_sha_before = sha256_of(map_file)
    protected_maps = {m: sha256_of(disk_path(m, 'umap')) for m in PROTECTED_MAPS
                      if disk_path(m, 'umap').exists() and m != target_map}
    protected_tiles = {TERRAIN_DIR + name: sha256_of(disk_path(TERRAIN_DIR + name))
                       for name in plan['precinctTiles']}
    for name in ('07_07', '07_08', '08_07', '08_08'):
        asset = '/Game/MikdashV3/FutureMountV1/Terrain/SM_JerusalemTerrain_%s_FutureMountCut' % name
        if disk_path(asset).exists():
            protected_tiles[asset] = sha256_of(disk_path(asset))

    native.receipt_path = REVIEW / ('native-terrain-cut-%s-%s-%s.json' % (mode, target, stamp))
    if native.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(native.receipt_path))

    checkpoint = None
    if mode in ('apply', 'revert'):
        checkpoint = CHECKPOINT_ROOT / ('PrecinctTerrainCut-%s-%s' % (target, stamp))
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / target_map[6:]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / target_map[6:])

    native.receipt = {
        'status': 'started_' + mode,
        'mode': mode, 'target': target, 'stamp': stamp, 'map': target_map,
        'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'checkpoint': str(checkpoint) if checkpoint else None,
        'protectedMapSha256Before': protected_maps,
        'protectedOriginalTileSha256Before': protected_tiles,
        'scriptSha256': sha256_of(Path(__file__)),
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'plan': dict((k, v) for k, v in plan.items()
                     if k not in ('rect', 'paved', 'jobs')),
        'twins': [], 'actors': [], 'acceptance': None, 'errors': [], 'omissions': [],
        'mapSaved': False,
        'defect': 'PLAZA-DESIGN-20260909.md section 6 item 1: the DEM tiles still rise through '
                  'the paving where the ground stands above the deck.',
        'operation': 'Inside the precinct square only, the terrain surface is clamped to the '
                     'deck UNDERSIDE (Z %g). Outside the square nothing moves. Original assets '
                     'are never opened for write; original actors are never deleted.'
                     % plan['zCut'],
        'modernRestorationContract': {
            'why': 'AMikdashEnclosure cannot hide a terrain actor: BuildingIdentityLabel '
                   '(MikdashEnclosure.cpp:22-42) returns an empty label for any mesh outside '
                   '/Game/MikdashV3/JerusalemContext/Buildings/ and '
                   '/Game/MikdashV3/JerusalemContext/OldCityFacadesV1/Meshes/, and an actor '
                   'with an empty identity label is skipped before the hide list is consulted. '
                   'Wiring the swap therefore needs a plugin property and a rebuild, which '
                   'this run was not permitted to do.',
            'hook': 'In AMikdashEnclosure::ApplyWeights, alongside the plaza components: show '
                    'actors tagged %r and hide actors tagged %r when the wall is shown, and '
                    'the reverse when it is not. SetActorHiddenInGame and '
                    'SetActorEnableCollision only - the same never-delete contract as the '
                    'buildings.' % (TWIN_TAG, ORIGINAL_TAG),
            'stateOnDiskAfterThisRun': 'YECHEZKEL-correct: originals hidden with collision off, '
                                       'twins visible. Until the hook is compiled MODERN and '
                                       'OVERLAY also show the cut hillside.',
        },
        'limitations': [
            'Numeric acceptance only. Nobody has looked at the cut in a frame.',
            'The quarry floor is a flat plane at the deck underside with an upward normal; no '
            'rock face, no strata, no material of its own. It is never visible while the deck '
            'is present, which is the only reason that is acceptable.',
            'Terrain below the deck underside inside the precinct is untouched, so the void '
            'under the fill four fifths of the plaza is still unmodelled (open item 3).',
        ],
    }
    native.write_receipt()

    saved = False
    try:
        if True:
            if not native.levels.load_level(target_map):
                raise RuntimeError('load_level failed for ' + target_map)
            world = native.editor.get_editor_world()
            if world.get_outermost().get_name() != target_map:
                raise RuntimeError('Loaded world is not the target map')

        native.receipt['terrainActorsInLevel'] = [
            dict((k, v) for k, v in row.items()
                 if k not in ('actor_object', 'component_object'))
            for row in native.terrain_actors()]
        native.write_receipt()
        level_tiles = native.tile_actors(sorted(set(j['tile'] for j in plan['jobs'])))
        for job in plan['jobs']:
            rows = level_tiles.get(job['tile'], [])
            if len(rows) != 1:
                raise RuntimeError('Expected exactly one actor for tile %s, found %d; the '
                                   'level holds %d terrain actors, listed in the receipt '
                                   'under terrainActorsInLevel'
                                   % (job['tile'], len(rows),
                                      len(native.receipt['terrainActorsInLevel'])))
            job['sourceMesh'] = rows[0]['meshPath']
            job['sourceMeshName'] = rows[0]['mesh']
            job['twinPath'] = '%s/%s%s' % (job['folder'], rows[0]['mesh'], job['suffix'])
        native.receipt['sourceMeshes'] = [
            dict(kind=j['kind'], tile=j['tile'], sourceMesh=j['sourceMesh'], twin=j['twinPath'])
            for j in plan['jobs']]
        native.write_receipt()

        if mode in ('assets', 'apply'):
            for job in plan['jobs']:
                name = job['tile']
                path = job['twinPath']
                original = ue.load_asset(job['sourceMesh'])
                if not isinstance(original, ue.StaticMesh):
                    raise RuntimeError('Missing source tile mesh ' + job['sourceMesh'])
                source = native.extract(original)
                buffers = build_twin(source, job['regions'])
                entry = dict(kind=job['kind'], tile=name, original=job['sourceMesh'],
                             sourceTriangles=buffers['sourceTriangles'],
                             flattenedSourceTriangles=buffers['flattenedSourceTriangles'],
                             flattenedArea2dCm2=buffers['flattenedArea2dCm2'],
                             area2dErrorCm2=buffers['area2dErrorCm2'],
                             twinTriangles=buffers['triangles'],
                             windingAgrees=buffers['windingAgrees'],
                             windingTriangles=buffers['windingTriangles'])
                if buffers['windingAgrees'] != buffers['windingTriangles']:
                    raise RuntimeError('Winding disagrees with the source on ' + name)
                if buffers['area2dErrorCm2'] > 1.0:
                    raise RuntimeError('Plan area is not conserved on ' + name)
                if buffers['flattenedSourceTriangles'] == 0:
                    entry.update(cutNeeded=False,
                                 note='No part of this tile stands above the deck underside '
                                      'inside the cut region; the original is already correct '
                                      'and nothing is created or changed.')
                    native.receipt['twins'].append(entry)
                    native.write_receipt()
                    continue
                if native.assets.does_asset_exist(path):
                    # Never blind-overwrite a native asset namespace. An existing twin is
                    # REUSED and then re-verified below against buffers computed fresh from
                    # the original this run; a mismatch fails the run rather than silently
                    # replacing somebody else's asset.
                    twin = ue.load_asset(path)
                    entry['reused'] = True
                else:
                    twin = native.create_twin(path, buffers, original)
                    entry['reused'] = False
                material = original.get_material(0)
                if material is None:
                    raise RuntimeError('Original tile has no material: ' + name)
                twin.set_material(0, material)
                setup = twin.get_editor_property('body_setup')
                setup.set_editor_property('collision_trace_flag',
                                          ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                setup.set_editor_property('double_sided_geometry', True)
                twin.set_editor_property('lod_for_collision', 0)
                if not native.assets.save_loaded_asset(twin, only_if_is_dirty=False):
                    raise RuntimeError('save_loaded_asset failed for ' + path)
                entry.update(cutNeeded=True, twin=path, material=material.get_path_name(),
                             nanite=native.nanite_enabled(twin),
                             uassetSha256=sha256_of(disk_path(path)),
                             readback=native.check_readback(twin, buffers, job['regions'],
                                                            source, job['sampleSpacingCm']))
                readback = entry['readback']
                if readback['outsideMaxHeightDifferenceCm'] > TOLERANCE_CM:
                    raise RuntimeError('The twin changed the surface OUTSIDE the cut on %s by '
                                       '%g cm' % (name, readback['outsideMaxHeightDifferenceCm']))
                for key in ('maxVertexHeightAboveDeckUndersideCm',
                            'maxGridHeightAboveDeckUndersideCm'):
                    above = readback[key]
                    if above is not None and above > TOLERANCE_CM:
                        raise RuntimeError('Twin %s still stands %g cm above the deck underside '
                                           '(%s)' % (name, above, key))
                native.receipt['twins'].append(entry)
                native.write_receipt()

        cut_tiles = [t for t in native.receipt['twins'] if t.get('cutNeeded')]
        job_by_key = dict(((j['kind'], j['tile']), j) for j in plan['jobs'])

        if mode == 'apply':
            found = level_tiles
            # One tile can carry more than one cut (07_08 takes both the precinct cut and the
            # Kotel plaza cut), so the original's PRIOR visibility and collision are captured
            # once, before anything is touched. Reading them per row would record this run's
            # own change as the state to revert to.
            priors = {}
            for _tile, rows in found.items():
                for row in rows:
                    priors.setdefault(row['actor'], (row['hiddenInGame'], row['collision']))
            placements = []
            for entry in cut_tiles:
                name = entry['tile']
                job = job_by_key[(entry['kind'], name)]
                matches = found.get(name, [])
                if len(matches) != 1:
                    raise RuntimeError('Expected exactly one actor for tile %s, found %d'
                                       % (name, len(matches)))
                actor = matches[0]['actor_object']
                component = matches[0]['component_object']
                identity = numeric_transform(ue, ue.Transform())
                if numeric_transform(ue, actor.get_actor_transform()) != identity:
                    raise RuntimeError('Tile actor %s is not at identity' % name)
                twin_mesh = ue.load_asset(entry['twin'])
                spawned = native.actors.spawn_actor_from_class(
                    ue.StaticMeshActor, ue.Vector(0.0, 0.0, 0.0),
                    ue.Rotator(pitch=0.0, yaw=0.0, roll=0.0))
                if spawned is None:
                    raise RuntimeError('spawn_actor_from_class returned None for ' + name)
                twin_component = spawned.get_component_by_class(ue.StaticMeshComponent)
                twin_component.set_editor_property('mobility', ue.ComponentMobility.STATIC)
                if not twin_component.set_static_mesh(twin_mesh):
                    raise RuntimeError('set_static_mesh failed for ' + entry['twin'])
                twin_component.set_material(0, ue.load_asset(entry['material'].split('.')[0]))
                twin_component.set_collision_profile_name(
                    component.get_collision_profile_name())
                spawned.set_actor_label(job['labelPrefix'] + name[len('SM_JerusalemTerrain_'):])
                spawned.set_editor_property('tags', [ue.Name(job['twinTag']), ue.Name(name)])
                spawned.set_actor_hidden_in_game(not job['twinVisible'])
                spawned.set_actor_enable_collision(job['twinVisible'])
                # The original: never deleted, mesh untouched. Hidden and non-colliding only
                # when this job's twin takes its place in the state that is on disk.
                prior_hidden, prior_collision = priors[actor.get_name()]
                if job['hideOriginal']:
                    actor.set_actor_hidden_in_game(True)
                    actor.set_actor_enable_collision(False)
                existing = [str(t) for t in actor.get_editor_property('tags')]
                if job['originalTag'] not in existing:
                    actor.set_editor_property(
                        'tags', [ue.Name(t) for t in existing + [job['originalTag']]])
                placements.append(dict(kind=entry['kind'], tile=name, twin=entry['twin'],
                                       twinVisible=job['twinVisible'],
                                       hideOriginal=job['hideOriginal'],
                                       twinActor=spawned.get_name(),
                                       twinActorLabel=spawned.get_actor_label(),
                                       originalActor=actor.get_name(),
                                       originalActorLabel=actor.get_actor_label(),
                                       originalPriorHidden=prior_hidden,
                                       originalPriorCollision=prior_collision,
                                       originalMesh=entry['original'],
                                       originalMeshUnchanged=(
                                           component.get_editor_property('static_mesh')
                                           .get_path_name().split('.')[0] == entry['original'])))
            native.receipt['actors'] = placements
            expected_visible = set()
            for entry in native.receipt['twins']:
                job = job_by_key[(entry['kind'], entry['tile'])]
                if not entry.get('cutNeeded'):
                    # Nothing was placed and nothing was hidden for this tile: it stands
                    # entirely below the deck underside already, so its original stays visible.
                    expected_visible.add(entry['tile'])
                    continue
                if job['twinVisible']:
                    expected_visible.add(entry['twin'].rsplit('/', 1)[-1])
                if not job['hideOriginal']:
                    expected_visible.add(entry['tile'])
            native.receipt['unhandledTerrainOverPrecinct'] = unhandled_terrain(
                native, plan, expected_visible)
            native.write_receipt()
            if native.receipt['unhandledTerrainOverPrecinct']:
                # Refuse BEFORE the save. The FutureMountV1 pass left four *_FutureMountCut
                # duplicate tile actors somewhere in this project; if any of them - or any
                # other terrain actor - stands over the precinct, cutting only the sixteen
                # originals would leave a second uncut surface poking through the paving and
                # the acceptance number would be measured against a level nobody had cut.
                raise RuntimeError('Terrain actors over the precinct that this run does not '
                                   'handle: %s' % native.receipt['unhandledTerrainOverPrecinct'])
            if not native.levels.save_current_level():
                raise RuntimeError('save_current_level returned False')
            saved = True
            native.receipt['mapSaved'] = True
            native.receipt['mapSha256AfterSave'] = sha256_of(map_file)
            native.write_receipt()
            if not native.levels.load_level(target_map):
                raise RuntimeError('Reopen failed')

        if mode == 'revert':
            prior = json.loads(Path(revert_receipt).read_text(encoding='utf-8-sig'))
            if prior['target'] != target or prior['mode'] != 'apply' or not prior['mapSaved']:
                raise RuntimeError('Revert needs a saved apply receipt for this target')
            by_label = {a.get_actor_label(): a for a in native.actors.get_all_level_actors()}
            reverted = []
            for row in prior['actors']:
                original = by_label.get(row['originalActorLabel'])
                if original is None:
                    raise RuntimeError('Original actor missing for revert: '
                                       + row['originalActorLabel'])
                if row.get('hideOriginal', True):
                    original.set_actor_hidden_in_game(row['originalPriorHidden'])
                    original.set_actor_enable_collision(row['originalPriorCollision'])
                original.set_editor_property(
                    'tags', [ue.Name(tag) for tag
                             in [str(x) for x in original.get_editor_property('tags')]
                             if tag not in (ORIGINAL_TAG, KOTEL_ORIGINAL_TAG)])
                twin_actor = by_label.get(row['twinActorLabel'])
                if twin_actor is not None:
                    native.actors.destroy_actor(twin_actor)
                reverted.append(row['tile'])
            native.receipt['reverted'] = reverted
            if not native.levels.save_current_level():
                raise RuntimeError('save_current_level returned False')
            saved = True
            native.receipt['mapSaved'] = True
            native.receipt['mapSha256AfterSave'] = sha256_of(map_file)
            if not native.levels.load_level(target_map):
                raise RuntimeError('Reopen failed')

        if mode in ('apply', 'verify'):
            native.receipt['acceptance'] = measure(native, plan)
            native.receipt['status'] = (
                'terrain_cut_placed_saved_reopened_measured_visual_acceptance_pending'
                if mode == 'apply' else 'terrain_cut_measured_map_unchanged')
        elif mode == 'assets':
            native.receipt['status'] = 'twins_built_and_verified_map_unchanged'
        else:
            native.receipt['status'] = 'terrain_cut_reverted_saved_reopened'
    except Exception as error:                                                   # noqa: BLE001
        native.receipt['errors'].append({'stage': mode, 'error': repr(error)})
        native.receipt['status'] = ('FAILED_AFTER_SAVE_CHECKPOINT_AVAILABLE' if saved
                                    else 'FAILED_BEFORE_SAVE_MAP_UNCHANGED')
        raise
    finally:
        native.receipt['mapSha256After'] = sha256_of(map_file)
        native.receipt['mapBytesChanged'] = \
            native.receipt['mapSha256After'] != map_sha_before
        native.receipt['protectedMapsUnchanged'] = all(
            sha256_of(disk_path(m, 'umap')) == value
            for m, value in protected_maps.items())
        native.receipt['originalTileAssetsUnchanged'] = all(
            sha256_of(disk_path(p)) == value for p, value in protected_tiles.items())
        if mode in ('assets', 'verify') and native.receipt['mapBytesChanged']:
            native.receipt['errors'].append(
                {'stage': 'finally',
                 'error': 'Mode %s must not change the target map, and it did.' % mode})
        native.write_receipt()
    return native.receipt


def unhandled_terrain(native, plan, expected_visible_mesh_names):
    """Every VISIBLE terrain surface standing over the precinct that this run did not author
    or deliberately leave alone. Anything in this list means the cut is incomplete."""
    rows = []
    for actor in native.actors.get_all_level_actors():
        _component, mesh = native.mesh_of(actor)
        if mesh is None:
            continue
        name = mesh.get_name()
        if not name.startswith('SM_JerusalemTerrain_'):
            continue
        if bool(actor.get_editor_property('hidden')):
            continue
        bounds = mesh.get_bounds()
        origin, extent = bounds.origin, bounds.box_extent
        if (origin.x + extent.x <= plan['rect'][0] or origin.x - extent.x >= plan['rect'][2]
                or origin.y + extent.y <= plan['rect'][1] or origin.y - extent.y >= plan['rect'][3]):
            continue
        if name in expected_visible_mesh_names:
            continue
        rows.append(dict(actor=actor.get_name(), label=actor.get_actor_label(), mesh=name))
    return rows


def measure(native, plan):
    """THE NUMBER. Sample the terrain a visitor would actually see across the precinct
    interior and report the highest it stands above the deck underside."""
    ue = native.ue
    field = HeightField()
    visible, hidden = [], []
    for actor in native.actors.get_all_level_actors():
        component, mesh = native.mesh_of(actor)
        if mesh is None:
            continue
        name = mesh.get_name()
        if not name.startswith('SM_JerusalemTerrain_'):
            continue
        bounds = mesh.get_bounds()
        origin, extent = bounds.origin, bounds.box_extent
        if (origin.x + extent.x <= plan['rect'][0] or origin.x - extent.x >= plan['rect'][2]
                or origin.y + extent.y <= plan['rect'][1] or origin.y - extent.y >= plan['rect'][3]):
            continue
        row = dict(actor=actor.get_name(), label=actor.get_actor_label(), mesh=name,
                   hiddenInGame=bool(actor.get_editor_property('hidden')),
                   collision=bool(actor.get_actor_enable_collision()))
        if row['hiddenInGame']:
            hidden.append(row)
            continue
        visible.append(row)
        field.add([t['positions'] for t in native.extract(mesh)])

    stations, nx, ny, dx, dy = grid_stations(plan['paved'], SAMPLE_SPACING_CM)
    z_cut = plan['zCut']
    worst = None
    worst_at = None
    covered = above = 0
    for x, y in stations:
        z = field.height(x, y)
        if z is None:
            continue
        covered += 1
        height = z - z_cut
        if height > 1e-6:
            above += 1
        if worst is None or height > worst:
            worst, worst_at = height, (x, y)
    return dict(
        region='the paved rectangle - the precinct square inset by the 6-amah wall thickness',
        regionCm=dict(xMin=plan['paved'][0], yMin=plan['paved'][1],
                      xMax=plan['paved'][2], yMax=plan['paved'][3]),
        deckTopZcm=0.0, deckUndersideZcm=z_cut,
        gridSpacingCm=SAMPLE_SPACING_CM, gridStationsX=nx, gridStationsY=ny,
        exactSpacingXCm=dx, exactSpacingYCm=dy,
        stationsSampled=len(stations), stationsWithTerrain=covered,
        stationsAboveDeckUnderside=above,
        maxHeightAboveDeckUndersideCm=worst,
        maxHeightAtCm=(list(worst_at) if worst_at else None),
        visibleTerrainActorsOverPrecinct=visible,
        hiddenTerrainActorsOverPrecinct=hidden)


def _unreal_available():
    try:
        import unreal                                                            # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return 'release_precinct_terrain_cut.py' in command_line and (
        '-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line()
    target = flag_from(command_line, TARGET_FLAGS, 'target')
    mode = flag_from(command_line, MODE_FLAGS, 'mode')
    if not mode:
        raise RuntimeError('Choose exactly one mode: %s' % list(MODE_FLAGS))
    revert_receipt = None
    if mode == 'revert':
        import re
        match = re.search(r'-CutRevert=(?:"([^"]+)"|(\S+))', command_line, re.IGNORECASE)
        if not match:
            raise RuntimeError('-CutRevert needs =<apply receipt path>')
        revert_receipt = match.group(1) or match.group(2)
    try:
        receipt = run(target, mode, revert_receipt)
        ue.log('release_precinct_terrain_cut[%s/%s]: %s; twins %d; errors %d'
               % (target, mode, receipt['status'], len(receipt['twins']),
                  len(receipt['errors'])))
    except Exception as error:                                                   # noqa: BLE001
        ue.log_error('release_precinct_terrain_cut failed: ' + repr(error))
        raise
    finally:
        lowered = command_line.lower()
        if '-executepythonscript' in lowered and '-run=pythonscript' not in lowered:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        chosen = flag_from(' '.join(sys.argv[1:]), TARGET_FLAGS, 'target')
        print(json.dumps(dict((name, dict((k, v) for k, v in offline_plan(name).items()
                                          if k not in ('rect', 'paved', 'jobs')))
                              for name in ([chosen] if chosen else list(TARGETS))), indent=2))
elif _invoked_as_native_script():
    _main()
