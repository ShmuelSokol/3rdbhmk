"""StreetTreesV1 placement - offline plan, and the intersection proof that goes with it.

THE JOB. Replace the 4,265 retained illustrative OSM blob trees with StreetTreesV1 trees, and
prove - by measurement, offline, before any engine runs - that not one of them passes through
built geometry. CP26-REVIEW.md D4: in `cp26-07-north-gate-approach-plaza-stone-near.png` the
blob trees drive straight through the north-gate stair and notch the retaining edge.

WHY THE ANCHORS ARE REUSED RATHER THAN RESCATTERED. The OSM trunk anchors are real data: they
come from OpenStreetMap park, garden and orchard polygons around the city, their Z is already
sampled onto this project's own terrain, and `remove_mount_trees.py` has already taken the 144
that stood on the Mount. Rescattering them would throw away the one thing the placeholders got
right - WHERE trees are in Jerusalem - to fix the thing they got wrong, which is what a tree
looks like. So the anchor set is inherited and only the tree standing on it changes.

Measured, not assumed: 4,409 source trunks, 144 removed on the Mount, 4,265 retained. Identity
rotation, uniform tint, `scale [1,1,4]` on every one of them - the blob trunk is a cylinder
stretched four times in Z, which is most of why it reads as a lollipop. Nearest-neighbour
spacing across the set is min 0.2 m, median 8.9 m, so a few anchors are effectively coincident
and the plan has to thin them.

THE INTERSECTION TEST is the point of this file. Every blocker below is real geometry that a
tree could stand in, and each is loaded from the authoritative offline source rather than
guessed:

  precinct plaza deck   analytic rectangle per target. It CANNOT be measured off the .umap -
                        AMikdashEnclosure::BuildPlaza builds all 14,641 tiles at runtime and
                        serialises nothing, so an editor script that tries to measure it finds
                        zero and silently does nothing. release_frame_defects.spec.json.
  Kotel plaza deck      959 serialised tile rows on two levels, -1234.594 and -984.594, plus
                        its steps, kerbs and bands. kotel-plaza-plan.json.
  the approach stairs   THE ONE IN THE DEFECT FRAME. Per-step transforms are not on disk in any
                        receipt - release_precinct_approaches.py regenerates them in-process -
                        so this file re-runs that planner's own `Plan` class offline over the
                        same DEM and gets the 696 (Candidate48) / 714 (Main50) step transforms
                        back. Same code, same constants, no engine.
  architecture          2,633 mesh AABBs, with the five hollow derived-union meshes decomposed
                        into their 162 constituent boxes - their raw AABBs span the whole outer
                        court and would otherwise reject every tree in Jerusalem.
  the Mount enclosure   the 66-point ring, plus a margin. Nothing is planted inside it.

DECK ORDER MATTERS. The Kotel decks lie INSIDE the precinct rectangle in XY but ten to twelve
metres below it. Tested against the precinct first, every tree on the Kotel plaza looks buried
under the precinct deck and is wrongly kept. Smallest and most specific footprint first.

OFFLINE ONLY. No engine, no .umap, nothing written into Content/. Run on the 64-bit
interpreter. The native apply is release_street_trees.py.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SCRIPTS = ROOT / 'Scripts'
FAMILY = 'StreetTreesV1'
OUT = ROOT / 'SourceAssets' / 'vegetation-review' / FAMILY
def plan_path(label):
    """The plan is PER TARGET, and it has to be.

    Candidate48 holds the architecture 4 per cent smaller and 248 cm west of Main50, so the two
    maps get different blocker sets and therefore different plans. A single shared
    `placement-plan.json` meant that generating the Main50 plan silently overwrote the
    Candidate48 one - and Candidate48 is the map that cooks.
    """
    return OUT / ('placement-plan-%s.json' % label)


def proof_path(label):
    return OUT / ('intersection-proof-%s.json' % label)
MANIFEST_PATH = OUT / 'street-trees-manifest.json'

INSTANCES = Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\output\cloud-unreal-v3'
                 r'\context-review\instances-manifest.json')
REMOVAL = ROOT / 'SourceAssets' / 'FutureMountV1' / 'mount-tree-removal-manifest.json'
KOTEL_PLAN = ROOT / 'SourceAssets' / 'context-review' / 'KotelPlazaV1' / 'kotel-plaza-plan.json'
FRAME_SPEC = SCRIPTS / 'release_frame_defects.spec.json'
ARCH_MANIFEST = ROOT / 'SourceAssets' / 'architecture-manifest.json'
FACADES = ROOT / 'SourceAssets' / 'context-review' / 'OldCityFacadesV1' / 'facades-manifest.json'
FOUNDATIONS = ROOT / 'SourceAssets' / 'context-review' / 'OldCityFoundationV2'
FOUNDATIONS_MANIFEST = FOUNDATIONS / 'foundations-manifest.json'

SEED = 20260915
PLACEMENT_CELL_CM = 40000.0

# Clearances. A tree may not merely avoid passing THROUGH built stone - it has to stand clear
# of it, or a crown grazes a parapet and reads as a clip anyway.
BUILT_CLEARANCE_CM = 60.0          # trunk/crown to any built box
MOUNT_RING_MARGIN_CM = 1500.0      # release_vegetation.spec.json uses the same figure
MIN_TREE_SPACING_CM = 260.0        # the source set has pairs 0.2 m apart; thin them

sys.path.insert(0, str(SCRIPTS))


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


import map_targets as mt  # noqa: E402


def sha256_of(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


# =====================================================================================
# 1. HASH - the same integer hash every other placement in this project draws from
# =====================================================================================
MASK32 = 0xFFFFFFFF


def hash_int(v):
    v = int(v) & MASK32
    v = (v ^ 61) ^ (v >> 16)
    v = (v + (v << 3)) & MASK32
    v = v ^ (v >> 4)
    v = (v * 0x27D4EB2D) & MASK32
    return (v ^ (v >> 15)) & MASK32


def hash_unit(seed, index, lane):
    return hash_int(hash_int(seed ^ (index * 2654435761)) ^ (lane * 40503)) / float(MASK32)


def hash_range(seed, index, lane, lo, hi):
    return lo + (hi - lo) * hash_unit(seed, index, lane)


# =====================================================================================
# 2. BLOCKERS
# =====================================================================================
class Box(object):
    """An axis-aligned world box with a name, so a rejection can say what rejected it."""

    __slots__ = ('x0', 'y0', 'z0', 'x1', 'y1', 'z1', 'name', 'kind')

    def __init__(self, x0, y0, z0, x1, y1, z1, name, kind):
        self.x0, self.y0, self.z0 = min(x0, x1), min(y0, y1), min(z0, z1)
        self.x1, self.y1, self.z1 = max(x0, x1), max(y0, y1), max(z0, z1)
        self.name = name
        self.kind = kind

    def xy_distance(self, x, y):
        """Distance in plan from (x, y) to the box; 0 inside."""
        dx = max(self.x0 - x, 0.0, x - self.x1)
        dy = max(self.y0 - y, 0.0, y - self.y1)
        return math.hypot(dx, dy)


def rotated_module_box(x, y, z, yaw_deg, local_min, local_max, scale, name, kind):
    """World AABB of a module box placed at (x,y,z) and turned by yaw about Z.

    The world AABB of a rotated box is CONSERVATIVE - it is never smaller than the stone - so a
    tree this test clears is clear of the real module too. Stated rather than hidden, because a
    conservative blocker can only cost trees, never let one through.
    """
    c = math.cos(math.radians(yaw_deg))
    s = math.sin(math.radians(yaw_deg))
    corners = []
    for lx in (local_min[0] * scale, local_max[0] * scale):
        for ly in (local_min[1] * scale, local_max[1] * scale):
            corners.append((lx * c - ly * s, lx * s + ly * c))
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    return Box(x + min(xs), y + min(ys), z + local_min[2] * scale,
               x + max(xs), y + max(ys), z + local_max[2] * scale, name, kind)


# Plaza module local bounds, from SourceAssets/enclosure-review/plaza-manifest.json.
MODULE_BOUNDS = {
    'DeckTile': ((-625.0, -625.0, -50.0), (625.0, 625.0, 0.0)),
    'WayTile': ((-625.0, -625.0, -50.0), (625.0, 625.0, 0.0)),
    'Kerb': ((-625.0, -25.0, -50.0), (625.0, 25.0, 25.0)),
    'RetainingBand': ((-625.0, -150.0, -250.0), (625.0, 0.0, 0.0)),
    'Step': ((-1250.0, -50.0, -25.0), (1250.0, 50.0, 0.0)),
}


def union_constituent_boxes(entry):
    """Decompose a hollow derived-union mesh into its source element boxes.

    THE TRAP this exists for: five architecture meshes are derived unions whose AABBs span
    +-8100 in XY and Z 300..3425 - the whole outer court. Left as AABBs they reject every tree
    in the city. The constituent boxes come from source_elements_json in amot with Y up and Z
    south, so the axis swap is applied here exactly as release_vegetation.py does it.
    """
    props = entry.get('sourceProperties') or {}
    raw = props.get('source_elements_json')
    if not raw:
        return []
    try:
        elements = json.loads(raw)
    except (ValueError, TypeError):
        return []
    scale = float(props.get('source_metres_per_amah', 0.5)) * 100.0
    boxes = []
    for element in elements:
        if element.get('shape') != 'box':
            continue
        position = element.get('position')
        size = element.get('size')
        if not position or not size:
            continue
        centre = (position[0] * scale, position[2] * scale, position[1] * scale)
        half = (size[0] * scale * 0.5, size[2] * scale * 0.5, size[1] * scale * 0.5)
        boxes.append((centre, half, element.get('name', 'element')))
    return boxes


def foundation_boxes(report):
    """One AABB per BUILDING foundation, measured out of the 96 OldCityFoundationV2 meshes.

    Added after OldCityFoundationV2 was applied to BOTH maps on 15 September: 96 meshes
    carrying 2,994 per-building stone plinths and stepped footings.

    The manifest's per-MESH `canonicalBoundsCm` is a whole ~500 m tile and is worthless as a
    blocker - the same coarseness that makes the 104 facade cell boxes unusable - but every
    mesh records its footprints as triangleStart/triangleCount ranges into its own OBJ, so the
    real per-building box can be MEASURED off the geometry instead of guessed. The whole set is
    92,952 triangles, which is nothing to parse.

    These are the blockers that matter most for a street tree. A stepped footing is low, thin
    and hugs the ground, which is precisely the geometry a trunk passes through while never
    coming near the building above it - and it is what the reviewer sees at walking height.

    All three zone classes are blocked. `Precinct` and `PrecinctMainOnly` foundations disappear
    in the Yechezkel state but exist in the modern one, and a tree has to be clear of them in
    the state where they are there; blocking all of them can only cost trees, never pass one.

    OBJ convention: these files are written with Y REFLECTED, so canonical y = -y_file.
    """
    manifest = read_json(FOUNDATIONS_MANIFEST)
    boxes = []
    zones = {}
    for mesh in manifest['meshes']:
        path = FOUNDATIONS / 'obj' / mesh['file']
        if not path.exists():
            raise RuntimeError('foundation mesh %s is missing; the blocker set would be '
                               'silently short' % mesh['file'])
        vertices = []
        faces = []
        for line in path.read_text(encoding='ascii', errors='ignore').splitlines():
            if line.startswith('v '):
                parts = line.split()
                vertices.append((float(parts[1]), -float(parts[2]), float(parts[3])))
            elif line.startswith('f '):
                faces.append([int(token.split('/')[0]) - 1 for token in line.split()[1:4]])
        zones[mesh['zoneClass']] = zones.get(mesh['zoneClass'], 0) + 1
        for footprint in mesh['footprints']:
            start = int(footprint['triangleStart'])
            count = int(footprint['triangleCount'])
            lo = [1e18, 1e18, 1e18]
            hi = [-1e18, -1e18, -1e18]
            for triangle in faces[start:start + count]:
                for index in triangle:
                    if index < 0 or index >= len(vertices):
                        continue
                    point = vertices[index]
                    for axis in range(3):
                        lo[axis] = min(lo[axis], point[axis])
                        hi[axis] = max(hi[axis], point[axis])
            if lo[0] > 1e17:
                continue
            boxes.append(Box(lo[0], lo[1], lo[2], hi[0], hi[1], hi[2],
                             'foundation:' + str(footprint.get('id')), 'oldcity_foundation'))
    report['foundationFootprintsBlocked'] = len(boxes)
    report['foundationZoneClasses'] = zones
    report['foundationManifestSha256'] = sha256_of(FOUNDATIONS_MANIFEST)
    expected = int(manifest['totals']['footprintsWithFoundation'])
    if len(boxes) < expected * 0.98:
        raise RuntimeError('only %d of %d foundation footprints produced a box; the parse is '
                           'wrong and the keep-out would be silently partial'
                           % (len(boxes), expected))
    return boxes


def build_blockers(target_key, report):
    """Every piece of built geometry a tree could stand in, with its provenance counted."""
    config = mt.target_config(target_key)
    label = config['key']
    scale, translation = mt.placement_of(target_key)
    amah = float(config['amahCm'])
    module_scale = amah / 50.0
    boxes = []
    decks = []
    counts = {}

    # --- 1. Kotel plaza. SMALLEST FOOTPRINT FIRST, and ten metres below the precinct.
    kotel = read_json(KOTEL_PLAN)
    for kind, local in (('deck', MODULE_BOUNDS['DeckTile']), ('step', MODULE_BOUNDS['Step']),
                        ('kerb', MODULE_BOUNDS['Kerb']), ('band', MODULE_BOUNDS['RetainingBand'])):
        rows = kotel.get(kind, [])
        for index, row in enumerate(rows):
            loc = row['loc']
            rot = row.get('rot', [0.0, 0.0, 0.0])
            sc = row.get('scale', [1.0, 1.0, 1.0])
            lo = (local[0][0] * sc[0], local[0][1] * sc[1], local[0][2] * sc[2])
            hi = (local[1][0] * sc[0], local[1][1] * sc[1], local[1][2] * sc[2])
            module = rotated_module_box(loc[0], loc[1], loc[2], rot[2], lo, hi, 1.0,
                                        'kotel_%s_%d' % (kind, index), 'kotel_plaza')
            boxes.append(module)
            if kind == 'deck':
                decks.append(module)
        counts['kotel_' + kind] = len(rows)

    # --- 2. Precinct plaza deck: the analytic rectangle, because it is not in the .umap.
    frame = read_json(FRAME_SPEC)
    host = None
    for entry in frame['vegetation']['deckHosts']:
        if entry['key'] == 'precinct':
            host = entry
            break
    rect = host['footprintRectangleByTarget'][label]
    top = float(host['footprintTopZcm'])
    precinct_deck = Box(rect[0], rect[1], top - 48.0, rect[2], rect[3], top,
                        'precinct_deck_rectangle', 'precinct_plaza')
    boxes.append(precinct_deck)
    decks.append(precinct_deck)
    counts['precinct_deck_rectangle'] = 1
    report['precinctRectangleCm'] = rect
    report['precinctDeckTopZcm'] = top

    # --- 3. The approach stairs. Regenerated offline from the planner that built them.
    approaches = _load('release_precinct_approaches', 'release_precinct_approaches.py')
    height, provenance = approaches.offline_height()
    plan = approaches.Plan(approaches.target_config(label)).build(height)
    report['approachHeightField'] = provenance['kind']
    report['approachScriptSha256'] = sha256_of(SCRIPTS / 'release_precinct_approaches.py')
    for kind, rows, local in (('steps', plan.steps, MODULE_BOUNDS['Step']),
                              ('paving', plan.paving, MODULE_BOUNDS['DeckTile']),
                              ('bands', plan.bands, MODULE_BOUNDS['RetainingBand']),
                              ('kerbs', plan.kerbs, MODULE_BOUNDS['Kerb'])):
        for index, row in enumerate(rows):
            x, y, z, yaw = row[0], row[1], row[2], row[3]
            boxes.append(rotated_module_box(x, y, z, yaw, local[0], local[1], plan.scale,
                                            'approach_%s_%d' % (kind, index), 'approach_stair'))
        counts['approach_' + kind] = len(rows)

    # --- 4. Architecture, unions decomposed.
    architecture = read_json(ARCH_MANIFEST)
    union_boxes = 0
    plain = 0
    for entry in architecture['meshes']:
        pieces = union_constituent_boxes(entry)
        if pieces:
            for centre, half, name in pieces:
                boxes.append(Box(centre[0] - half[0], centre[1] - half[1], centre[2] - half[2],
                                 centre[0] + half[0], centre[1] + half[1], centre[2] + half[2],
                                 'union:' + str(name), 'architecture'))
                union_boxes += 1
            continue
        bounds = entry.get('expectedBoundsUnrealCm')
        if not bounds:
            continue
        lo, hi = bounds['min'], bounds['max']
        boxes.append(Box(lo[0], lo[1], lo[2], hi[0], hi[1], hi[2],
                         entry.get('assetName', 'architecture'), 'architecture'))
        plain += 1
    counts['architecture_meshes'] = plain
    counts['architecture_union_boxes'] = union_boxes
    if union_boxes == 0:
        raise RuntimeError('No architecture union decomposed. The five hollow union meshes span '
                           'the whole outer court as raw AABBs and would reject every tree in '
                           'the city; a decomposition that silently finds nothing is the exact '
                           'failure this check exists for.')

    # Candidate48 holds the architecture 4 per cent smaller and 248 cm west. Both frames are
    # blockers, so no tree lands inside either interpretation of the stone.
    if scale != 1.0 or translation != [0.0, 0.0, 0.0]:
        moved = []
        for box in boxes:
            if box.kind != 'architecture':
                continue
            lo = mt.transform_point((box.x0, box.y0, box.z0), scale, translation)
            hi = mt.transform_point((box.x1, box.y1, box.z1), scale, translation)
            moved.append(Box(lo[0], lo[1], lo[2], hi[0], hi[1], hi[2],
                             box.name + '@' + label, 'architecture_target_frame'))
        boxes.extend(moved)
        counts['architecture_target_frame'] = len(moved)

    # --- 5. Old City foundations, applied to BOTH maps on 15 September. Identity placement in
    # world cm and identical on the two targets, so one set serves both.
    foundations = foundation_boxes(report)
    boxes.extend(foundations)
    counts['oldcity_foundations'] = len(foundations)

    report['blockerCounts'] = counts
    report['blockerBoxesTotal'] = len(boxes)
    report['deckFootprints'] = len(decks)
    report['moduleScale'] = module_scale
    return boxes, decks


class Grid(object):
    """Uniform bucket index over the blocker boxes. 4,265 trees against ~20k boxes."""

    def __init__(self, boxes, cell_cm=2000.0):
        self.cell = cell_cm
        self.buckets = {}
        for box in boxes:
            i0, j0 = int(math.floor(box.x0 / cell_cm)), int(math.floor(box.y0 / cell_cm))
            i1, j1 = int(math.floor(box.x1 / cell_cm)), int(math.floor(box.y1 / cell_cm))
            # A box spanning a huge span would fill the index; those are the decomposed unions
            # and the deck rectangle, so cap the fan-out and keep the big ones in a linear list.
            if (i1 - i0 + 1) * (j1 - j0 + 1) > 4096:
                self.buckets.setdefault('big', []).append(box)
                continue
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    self.buckets.setdefault((i, j), []).append(box)

    def near(self, x, y, radius):
        out = list(self.buckets.get('big', ()))
        i0, j0 = int(math.floor((x - radius) / self.cell)), int(math.floor((y - radius) / self.cell))
        i1, j1 = int(math.floor((x + radius) / self.cell)), int(math.floor((y + radius) / self.cell))
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                out.extend(self.buckets.get((i, j), ()))
        return out


# =====================================================================================
# 3. THE TREE AS A SOLID
# =====================================================================================
class TreeSolid(object):
    """A tree modelled for the test as a trunk cylinder under a crown cylinder.

    Not a bounding box: a box around a 7 m crown is 7 m wide at ground level too, and would
    refuse every tree within 3.5 m of a wall it does not touch. Two stacked cylinders is the
    cheapest model that keeps the trunk thin near the ground, which is where the stair, the
    kerb and the deck edge actually are.
    """

    __slots__ = ('x', 'y', 'z', 'trunk_r', 'crown_r', 'crown_z0', 'top_z')

    def __init__(self, x, y, z, trunk_r, crown_r, crown_z0, top_z):
        self.x, self.y, self.z = x, y, z
        self.trunk_r, self.crown_r = trunk_r, crown_r
        self.crown_z0, self.top_z = crown_z0, top_z

    def hits(self, box, clearance):
        """True if this tree, grown its clearance, meets the box."""
        if box.z1 < self.z - 50.0 or box.z0 > self.z + self.top_z:
            return False
        distance = box.xy_distance(self.x, self.y)
        # trunk section
        trunk_top = self.z + self.crown_z0
        if box.z0 <= trunk_top and box.z1 >= self.z - 50.0:
            if distance <= self.trunk_r + clearance:
                return True
        # crown section
        if box.z1 >= self.z + self.crown_z0 and box.z0 <= self.z + self.top_z:
            if distance <= self.crown_r + clearance:
                return True
        return False


def tree_solid_for(species_record, x, y, z, scale):
    lo = species_record['trunkRadiusCm'] * scale
    return TreeSolid(x, y, z, lo,
                     species_record['crownRadiusCm'] * scale,
                     species_record['crownBaseCm'] * scale,
                     species_record['topCm'] * scale)


def species_geometry(manifest):
    """Measure each species' real solid from the generated LOD0 meshes, not from the table.

    The species table states an INTENDED height and crown; what matters for an intersection
    test is what the mesh actually is, and those differed by a third before the generator's
    length calibration was written. So this reads the exported bounds.
    """
    out = {}
    for record in manifest['meshes']:
        if record.get('lod') != 0:
            continue
        key = record['species']
        bounds = record['canonicalBoundsCm']
        entry = out.setdefault(key, {'topCm': 0.0, 'crownRadiusCm': 0.0,
                                     'trunkRadiusCm': 0.0, 'crownBaseCm': 1e9})
        entry['topCm'] = max(entry['topCm'], bounds['max'][2])
        if record.get('materialRole') == 'leaf':
            reach = max(abs(bounds['min'][0]), abs(bounds['max'][0]),
                        abs(bounds['min'][1]), abs(bounds['max'][1]))
            entry['crownRadiusCm'] = max(entry['crownRadiusCm'], reach)
            entry['crownBaseCm'] = min(entry['crownBaseCm'], bounds['min'][2])
        else:
            reach = max(abs(bounds['min'][0]), abs(bounds['max'][0]),
                        abs(bounds['min'][1]), abs(bounds['max'][1]))
            entry['trunkRadiusCm'] = max(entry['trunkRadiusCm'], min(reach, 120.0))
    for entry in out.values():
        if entry['crownBaseCm'] > 1e8:
            entry['crownBaseCm'] = entry['topCm'] * 0.35
    return out


# =====================================================================================
# 4. ZONES
# =====================================================================================
def build_zoner(report):
    """Decide which part of the city an anchor is in, from data already in the repository."""
    facades = read_json(FACADES)
    ring_bounds = facades['oldCity'].get('ringBoundsCm')
    instances = read_json(INSTANCES)
    groups = dict((g['sourceCategory'], g) for g in groups_of(instances))
    cemetery = groups.get('Cemetery markers')
    cem_cells = {}
    if cemetery:
        for row in cemetery['instances']:
            t = row['translationUnrealCm']
            cem_cells.setdefault((int(t[0] // 4000.0), int(t[1] // 4000.0)), 0)
            cem_cells[(int(t[0] // 4000.0), int(t[1] // 4000.0))] += 1
    report['oldCityRingBoundsCm'] = ring_bounds
    report['cemeteryCells'] = len(cem_cells)

    frame = read_json(FRAME_SPEC)
    rect = None
    for entry in frame['vegetation']['deckHosts']:
        if entry['key'] == 'precinct':
            rect = entry['footprintRectangleByTarget']['Candidate48']

    def zone_for(x, y, z):
        if cem_cells.get((int(x // 4000.0), int(y // 4000.0)), 0) >= 6:
            return 'cemetery'
        if ring_bounds and (ring_bounds[0] <= x <= ring_bounds[2]
                            and ring_bounds[1] <= y <= ring_bounds[3]):
            return 'old_city_lane'
        if ring_bounds:
            margin = 9000.0
            if (ring_bounds[0] - margin <= x <= ring_bounds[2] + margin
                    and ring_bounds[1] - margin <= y <= ring_bounds[3] + margin):
                return 'wall_perimeter'
        if rect:
            margin = 12000.0
            if (rect[0] - margin <= x <= rect[2] + margin
                    and rect[1] - margin <= y <= rect[3] + margin):
                return 'plaza_approach'
        if z < -1500.0:
            return 'valley_floor'
        return 'hill_slope'

    return zone_for


def groups_of(instances):
    return instances['groups']


# =====================================================================================
# 5. THE PLAN
# =====================================================================================
def build_plan(target_key, write_preview=True):
    report = {}
    manifest = read_json(MANIFEST_PATH)
    trees_module = _load('create_street_trees', 'create_street_trees.py')
    species_list = trees_module.SPECIES
    geometry = species_geometry(manifest)

    instances = read_json(INSTANCES)
    groups = dict((g['sourceCategory'], g) for g in groups_of(instances))
    trunks = groups['Tree trunks']
    removal = read_json(REMOVAL)
    removed = set(int(r['trunkSourceIndex']) for r in removal['removals'])
    report['sourceTrunks'] = trunks['instanceCount']
    report['removedOnMount'] = len(removed)
    report['instancesManifestSha256'] = instances.get('fbxSha256')

    anchors = []
    for row in trunks['instances']:
        index = int(row['sourceInstanceIndex'])
        if index in removed:
            continue
        t = row['translationUnrealCm']
        anchors.append((index, float(t[0]), float(t[1]), float(t[2])))
    report['retainedAnchors'] = len(anchors)

    zone_for = build_zoner(report)
    boxes, decks = build_blockers(target_key, report)
    grid = Grid(boxes)

    ring = [(float(p[0]), float(p[1])) for p in removal['boundaryXYcm']]

    placed = []
    rejected = {}
    zone_counts = {}
    species_counts = {}
    spacing_grid = {}

    for order, (index, x, y, z) in enumerate(anchors):
        zone = zone_for(x, y, z)
        zone_counts[zone] = zone_counts.get(zone, 0) + 1

        # --- species from the zone's weights
        weights = []
        for species in species_list:
            weight = float(species.get('zones', {}).get(zone, 0.0))
            if weight > 0.0:
                weights.append((species, weight))
        if not weights:
            rejected['no_species_for_zone'] = rejected.get('no_species_for_zone', 0) + 1
            continue
        total = sum(w for _s, w in weights)
        pick = hash_unit(SEED, index, 101) * total
        chosen = weights[-1][0]
        for species, weight in weights:
            pick -= weight
            if pick <= 0.0:
                chosen = species
                break

        variant = int(hash_unit(SEED, index, 102) * int(chosen.get('seeds', 3)))
        variant = min(variant, int(chosen.get('seeds', 3)) - 1)
        lo, hi = chosen['scaleRange']
        scale = hash_range(SEED, index, 103, lo, hi)
        yaw = hash_range(SEED, index, 104, 0.0, 360.0)
        tilt = float(chosen.get('tiltDegrees', 5.0))
        pitch = hash_range(SEED, index, 105, -tilt, tilt)
        roll = hash_range(SEED, index, 106, -tilt, tilt)

        record = geometry.get(chosen['key'])
        if record is None:
            rejected['species_not_generated'] = rejected.get('species_not_generated', 0) + 1
            continue
        solid = tree_solid_for(record, x, y, z, scale)

        # --- keep out of the Mount enclosure
        if point_in_polygon(x, y, ring) or distance_to_ring(x, y, ring) <= MOUNT_RING_MARGIN_CM:
            rejected['mount_enclosure'] = rejected.get('mount_enclosure', 0) + 1
            continue

        # --- thin coincident anchors
        cell = (int(x // MIN_TREE_SPACING_CM), int(y // MIN_TREE_SPACING_CM))
        clash = False
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for px, py in spacing_grid.get((cell[0] + di, cell[1] + dj), ()):
                    if math.hypot(px - x, py - y) < MIN_TREE_SPACING_CM:
                        clash = True
                        break
                if clash:
                    break
            if clash:
                break
        if clash:
            rejected['too_close_to_another_tree'] = rejected.get('too_close_to_another_tree', 0) + 1
            continue

        # --- NOTHING STANDS ON A PAVED DECK, AND NOTHING IS BURIED UNDER ONE.
        #
        # A 3D intersection test is NOT sufficient here, and the plan-view preview is what
        # showed it: 329 trees sat inside the precinct rectangle, 293 of them a median 27 m
        # BELOW the deck, and not one of them intersected the deck's thin Z -48..0 slab, so
        # every one passed. They are buried under 1.43 km of pavement.
        #
        # This is the trap frame-defect-traps-20260910 already recorded from the other side:
        # plants on the Kotel plaza "look buried under the precinct deck and are kept". Being
        # clear of the stone in Z is not the same as belonging there. The precinct rectangle is
        # exact rather than conservative - 14,039 deck + 602 way tiles = 14,641 = 121 x 121, so
        # every cell of it is paved - which is precisely why an XY test is legitimate: there is
        # no hole in that rectangle for a tree to stand in.
        deck_hit = None
        for deck in decks:
            if deck.x0 <= x <= deck.x1 and deck.y0 <= y <= deck.y1:
                deck_hit = deck
                break
        if deck_hit is not None:
            key = 'inside_deck_footprint_' + deck_hit.kind
            rejected[key] = rejected.get(key, 0) + 1
            continue

        # --- THE INTERSECTION TEST
        radius = max(solid.crown_r, solid.trunk_r) + BUILT_CLEARANCE_CM
        hit = None
        for box in grid.near(x, y, radius):
            if solid.hits(box, BUILT_CLEARANCE_CM):
                hit = box
                break
        if hit is not None:
            key = 'intersects_' + hit.kind
            rejected[key] = rejected.get(key, 0) + 1
            continue

        spacing_grid.setdefault(cell, []).append((x, y))
        species_counts[chosen['key']] = species_counts.get(chosen['key'], 0) + 1
        placed.append({'species': chosen['key'], 'variant': variant, 'zone': zone,
                       'row': [round(x, 3), round(y, 3), round(z - 12.0, 3),
                               round(yaw, 3), round(pitch, 3), round(roll, 3),
                               round(scale, 4), round(scale, 4), variant],
                       'sourceIndex': index})

    report['placed'] = len(placed)
    report['rejected'] = rejected
    report['rejectedTotal'] = sum(rejected.values())
    report['zoneCounts'] = zone_counts
    report['speciesCounts'] = species_counts

    # --- the proof: re-test every PLACED tree and require zero hits.
    residual = 0
    residual_deck = 0
    for entry in placed:
        row = entry['row']
        record = geometry[entry['species']]
        solid = tree_solid_for(record, row[0], row[1], row[2] + 12.0, row[6])
        radius = max(solid.crown_r, solid.trunk_r) + BUILT_CLEARANCE_CM
        for box in grid.near(row[0], row[1], radius):
            if solid.hits(box, BUILT_CLEARANCE_CM):
                residual += 1
                break
        for deck in decks:
            if deck.x0 <= row[0] <= deck.x1 and deck.y0 <= row[1] <= deck.y1:
                residual_deck += 1
                break
    report['residualIntersectionsAfterPlacement'] = residual
    report['residualInsideDeckFootprintAfterPlacement'] = residual_deck
    if residual:
        raise AssertionError('%d placed trees still intersect built geometry; the plan is not '
                             'the proof it claims to be' % residual)
    if residual_deck:
        raise AssertionError('%d placed trees still stand inside a paved deck footprint - on it '
                             'or buried under it; the plan is not the proof it claims to be'
                             % residual_deck)

    batches = {}
    for entry in placed:
        row = entry['row']
        key = '%s_%s%03d_%s%03d' % (entry['species'],
                                    'N' if row[0] < 0 else 'P',
                                    abs(int(row[0] // PLACEMENT_CELL_CM)),
                                    'N' if row[1] < 0 else 'P',
                                    abs(int(row[1] // PLACEMENT_CELL_CM)))
        batches.setdefault(key, []).append(row)

    plan = {
        'status': 'offline_placement_plan_generated_native_pending',
        'version': 1,
        'family': FAMILY,
        'generated': datetime.now(timezone.utc).isoformat(),
        'generator': 'Scripts/create_street_tree_placement.py',
        'generatorSha256': sha256_of(Path(__file__)),
        'target': mt.target_config(target_key)['key'],
        'map': mt.target_config(target_key)['map'],
        'seed': SEED,
        'coordinateConvention': ('UE cm, X east, +Y south, Z up. Z is the OSM anchor height '
                                 'already sampled onto this project terrain, less 12 cm so the '
                                 'trunk flare sinks and no gap shows on a slope.'),
        'instanceFormat': ['xCm', 'yCm', 'zCm', 'yawDeg', 'pitchDeg', 'rollDeg',
                           'scaleXY', 'scaleZ', 'variantSeed'],
        'replaces': {'meshes': ['SM_JerusalemInstance_Tree_trunks',
                                'SM_JerusalemInstance_Tree_crowns'],
                     'retainedAnchorsInherited': report['retainedAnchors']},
        'clearanceCm': {'built': BUILT_CLEARANCE_CM, 'mountRing': MOUNT_RING_MARGIN_CM,
                        'treeToTree': MIN_TREE_SPACING_CM},
        'speciesGeometryMeasuredFromMeshes': geometry,
        'intersectionProof': report,
        'totalInstances': len(placed),
        'batching': {'placementCellCm': PLACEMENT_CELL_CM, 'batchCount': len(batches)},
        'batches': [{'batchId': key, 'species': key.split('_')[0], 'count': len(rows),
                     'instances': rows} for key, rows in sorted(batches.items())],
        'limitations': [
            'Geometric placement only. No visual, collision, cook or packaged acceptance.',
            'Blocker boxes for rotated modules are world AABBs, which are conservative: they '
            'are never smaller than the stone, so this test can cost a tree but cannot pass one '
            'that intersects.',
            'Old City building FOUNDATIONS are blockers: 2,994 per-building plinths and '
            'stepped footings measured out of the OldCityFoundationV2 meshes. The building '
            'SHELLS above them are still not, because the repository has no per-building AABB '
            'for them - only 104 grid-cell boxes of about 130 x 99 m, which would reject every '
            'tree in the Old City. In practice the foundation is the stricter test at ground '
            'level, and the anchors are OSM garden and park polygons that lie outside building '
            'footprints by construction. Stated as a gap rather than claimed as tested.',
            'Nothing here is halachic.',
        ],
    }
    label = mt.target_config(target_key)['key']
    written = plan_path(label)
    written.parent.mkdir(parents=True, exist_ok=True)
    written.write_text(json.dumps(plan, indent=1) + '\n', encoding='utf-8')
    proof_path(label).write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    plan['planFile'] = str(written.relative_to(ROOT))
    if write_preview:
        write_plan_preview(placed, boxes, trees_module, label)
    return plan


def point_in_polygon(x, y, points):
    inside = False
    count = len(points)
    for i in range(count):
        ax, ay = points[i]
        bx, by = points[(i + 1) % count]
        if (ay > y) != (by > y):
            t = (y - ay) / (by - ay) if (by - ay) else 0.0
            if x < ax + t * (bx - ax):
                inside = not inside
    return inside


def distance_to_ring(x, y, points):
    best = float('inf')
    count = len(points)
    for i in range(count):
        ax, ay = points[i]
        bx, by = points[(i + 1) % count]
        dx, dy = bx - ax, by - ay
        length2 = dx * dx + dy * dy
        t = 0.0 if length2 <= 0.0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / length2))
        best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


def write_plan_preview(placed, boxes, trees_module, label='Candidate48', size=1500):
    """Plan view: built geometry in grey, trees in their species colour."""
    xs = [e['row'][0] for e in placed]
    ys = [e['row'][1] for e in placed]
    if not xs:
        return None
    minx, maxx = min(xs) - 5000.0, max(xs) + 5000.0
    miny, maxy = min(ys) - 5000.0, max(ys) + 5000.0
    span = max(maxx - minx, maxy - miny)
    scale = size / span
    data = bytearray(b'\x18\x1a\x1c' * (size * size))
    for box in boxes:
        if box.kind == 'architecture_target_frame':
            continue
        colour = {'kotel_plaza': (86, 96, 108), 'precinct_plaza': (54, 60, 68),
                  'approach_stair': (150, 120, 84), 'architecture': (96, 88, 80)}.get(
                      box.kind, (70, 70, 70))
        x0 = int((box.x0 - minx) * scale)
        x1 = int((box.x1 - minx) * scale)
        y0 = int((box.y0 - miny) * scale)
        y1 = int((box.y1 - miny) * scale)
        if x1 < 0 or y1 < 0 or x0 >= size or y0 >= size:
            continue
        for py in range(max(0, y0), min(size - 1, y1) + 1):
            row = py * size
            for px in range(max(0, x0), min(size - 1, x1) + 1):
                data[(row + px) * 3:(row + px) * 3 + 3] = bytes(colour)
    palette = {'Olive': (150, 168, 118), 'Cypress': (34, 76, 58), 'AleppoPine': (56, 98, 66),
               'Carob': (58, 88, 52), 'JudasTree': (196, 120, 168), 'DatePalm': (120, 176, 96)}
    for entry in placed:
        px = int((entry['row'][0] - minx) * scale)
        py = int((entry['row'][1] - miny) * scale)
        colour = bytes(palette.get(entry['species'], (220, 220, 220)))
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                qx, qy = px + dx, py + dy
                if 0 <= qx < size and 0 <= qy < size:
                    data[(qy * size + qx) * 3:(qy * size + qx) * 3 + 3] = colour
    path = OUT / 'previews' / ('preview-placement-plan-%s.png' % label)
    path.parent.mkdir(parents=True, exist_ok=True)
    trees_module.cv.png_rgb(path, data, size, size)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description='Plan StreetTreesV1 placement offline.')
    parser.add_argument('--target', default='candidate48',
                        help='candidate48 (the cook map) or main50')
    parser.add_argument('--no-preview', action='store_true')
    args = parser.parse_args(argv)

    plan = build_plan(args.target, write_preview=not args.no_preview)
    report = plan['intersectionProof']
    print('StreetTreesV1 placement, target %s' % plan['target'])
    print('  source trunks %d, removed on the Mount %d, retained anchors %d'
          % (report['sourceTrunks'], report['removedOnMount'], report['retainedAnchors']))
    print('  blocker boxes %d' % report['blockerBoxesTotal'])
    for key in sorted(report['blockerCounts']):
        print('      %-28s %7d' % (key, report['blockerCounts'][key]))
    print('  PLACED %d, rejected %d' % (report['placed'], report['rejectedTotal']))
    for key in sorted(report['rejected']):
        print('      %-28s %7d' % (key, report['rejected'][key]))
    print('  zones:   %s' % report['zoneCounts'])
    print('  species: %s' % report['speciesCounts'])
    print('  RESIDUAL INTERSECTIONS AFTER PLACEMENT: %d'
          % report['residualIntersectionsAfterPlacement'])
    print('  -> %s' % plan['planFile'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
