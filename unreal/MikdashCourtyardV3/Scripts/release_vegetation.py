"""Guarded release placement of JudeanFloraV1 vegetation into the combined map.

Imports the offline OBJ meshes and PNG textures produced by Scripts/create_vegetation.py,
assembles each species' LOD ladder onto one StaticMesh, and places the planned instances as
hierarchical instanced components in
/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.

Every number comes from Scripts/release_vegetation.spec.json and from the placement plan it
hashes, so a human can review the whole plan before an engine is launched.

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_vegetation.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-Vegetation-01.log"

WHICH MAP -- and why the plants do NOT move with the architecture
-----------------------------------------------------------------
  -Main50        the legacy 50 cm map. THE DEFAULT, so no existing invocation is retargeted.
  -Candidate48   the configured GameDefaultMap and the cook map: the one that ships.

Candidate48 holds the same ARCHITECTURE under a 0.96 similarity about the world origin plus the
Aron re-pivot (-248, 0, 0). It holds the same TERRAIN at identical coordinates: the 48 cm
migration never touched FutureMountV1 or the metric city. A tree stands on the terrain, so the
instances are placed at IDENTICAL coordinates on both maps and carrying them through the
architecture transform would be the bug, not the fix. What does ride the transform is the
keep-out: the Mount enclosure ring and the architecture blocker boxes are tested in BOTH frames,
so nothing is planted inside the Mount under either interpretation and the two maps refuse the
same instances. Neither half is taken on trust -- prove_ground() compares every terrain tile's
live world AABB against the same tile read off the live Main50 level by
Scripts/candidate_placement_proof.py (run that first), and prove_placement() measures the
architecture similarity off the level before any keep-out is built from it.

Optional switches (read from the engine command line):
  -VegetationImportOnly          import and assemble the meshes, place nothing.
  -VegetationMaxBatches=<n>      place at most n batches this run (default from the spec).
  -VegetationResume=<receipt>    read a previous receipt and skip every batch it completed.
  -VegetationSpecies=Olive,Fig   restrict this run to the named species.
  -VegetationSkipImport          the meshes are already imported; go straight to placement.

A resume receipt is per MAP: -VegetationResume= refuses a receipt from the other target, because
skipping the batches the other map completed would leave a hole no count against the plan sees.

Revert (OFFLINE, with no editor open):
  python Scripts/release_vegetation.py --revert=<receipt> [--dry-run]

BATCHING AND RESUME - why this is not one big run
-------------------------------------------------
This machine has 16 GB and a previous large import here had to be run in groups to survive it.
So the plan is shipped pre-grouped into batches of at most a few thousand instances each,
keyed by 400 m placement cell; a run places at most -VegetationMaxBatches of them, records
every completed batch id in its receipt, and a following run started with
-VegetationResume=<that receipt> skips exactly what was already done. Re-placing a batch is
refused rather than de-duplicated, because a silent de-duplication would hide a resume that
had not actually resumed.

SAFETY MODEL (the same one release_place_assets.py uses)
--------------------------------------------------------
  * Refuses to run with the wrong project directory, a game world, dirty packages, or a loaded
    world that is not the combined map.
  * Copies Walkthrough.umap and any One-File-Per-Actor folders to
    ReviewCheckpoints/Vegetation-<stamp>/ before any mutation, and verifies the copy by hash.
  * Validates the plan and the manifest by SHA256 against the files on disk, and refuses a plan
    whose recorded status is not the expected one.
  * Every planned instance is re-tested in the editor against the Mount enclosure ring and
    against the existing tree instances before it is spawned. A plan error cannot put a tree
    inside the precinct.
  * Saves only if something was placed, reopens the map, and reads back the instance count of
    every component it created numerically.
  * The receipt JSON is written at start and again in finally, so partial state survives a
    failure.

TWO CLEARANCE TRAPS, BOTH REPEATED HERE ON THE LIVE LEVEL
----------------------------------------------------------
The offline generator already excluded these, but the editor sees the real actors and must not
re-introduce them:
  * The 256 SM_JerusalemTerrain_* tiles have 400-800 m AABBs that enclose the whole Temple.
    They are the GROUND. They are skipped by prefix and the skipped count is recorded, so this
    exclusion cannot silently stop matching after a rename.
  * Hollow derived-union meshes have AABBs that enclose the entire outer court. They are
    decomposed into their constituent boxes from the architecture manifest, and the
    recomposition is verified against the manifest's own bounds before the boxes are trusted.
Using raw bounds for either of these gives 100 per cent false blockers, which is a mistake this
project has already paid a day for.
"""
import hashlib
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_vegetation.spec.json'
sys.path.insert(0, str(ROOT / 'Scripts'))
import map_targets as mt  # noqa: E402

# THE MAP THIS RUNS AGAINST. Defaults to Main50 -- the map this pass has always run against and
# the frame the plan is authored in -- so no existing invocation is silently retargeted. Say
# -Candidate48 (or -Target=Candidate48) for the map that actually ships.
TARGET_KEY = mt.target_from_command_line()
TARGET_CONFIG = mt.target_config(TARGET_KEY)
TARGET = TARGET_CONFIG['map']
TARGET_LABEL = TARGET_CONFIG['key']
AUTHORING_MAP = mt.TARGETS[mt.AUTHORING_TARGET]['map']
# The architecture's similarity -- which the PLANTS DO NOT RIDE. See ground_rule() below.
PLACEMENT_SCALE, PLACEMENT_TRANSLATION = mt.placement_of(TARGET_KEY)
GROUND_REFERENCE = ROOT / 'SourceAssets' / 'scale-review' / 'ground-fingerprint-Main50.json'
GROUND_PARITY_TOLERANCE_CM = 0.5

TARGET_LIMITATIONS = ([] if TARGET_KEY == mt.AUTHORING_TARGET else [
    'On %s the plants stand at IDENTICAL coordinates to Main50, because the FutureMountV1 '
    'terrain they grow out of was never rescaled by the 48 cm migration. What does change is the '
    'keep-out: the enclosure ring and the architecture blockers are tested in BOTH frames, so no '
    'instance lands inside either map interpretation of the Mount.' % TARGET_LABEL,
    'Geometric placement only. No visual, collision, cook or performance acceptance on %s, and '
    'the species materials remain unassigned on both maps.' % TARGET_LABEL,
])


# --------------------------------------------------------------------------
# Pure helpers (no unreal import) so offline_check() runs anywhere, including
# under scripts/verify.py on a machine with no engine open.
# --------------------------------------------------------------------------

def sha256_of(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    # The spec and the placement plan are written in the AUTHORING frame (Main50); the spec's own
    # targetMap stays the authoring map on every run and is never rewritten per target.
    if spec['targetMap'] != AUTHORING_MAP:
        raise RuntimeError('Spec target %r is not the authoring map %r'
                           % (spec['targetMap'], AUTHORING_MAP))
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def load_plan(spec):
    plan = json.loads((ROOT / spec['plan']).read_text(encoding='utf-8'))
    if plan['status'] != spec['planStatusRequired']:
        raise RuntimeError('Placement plan status is %r, expected %r'
                           % (plan['status'], spec['planStatusRequired']))
    return plan


def load_manifest(spec):
    manifest = json.loads((ROOT / spec['manifest']).read_text(encoding='utf-8'))
    if manifest['status'] != spec['manifestStatusRequired']:
        raise RuntimeError('Geometry manifest status is %r, expected %r'
                           % (manifest['status'], spec['manifestStatusRequired']))
    return manifest


def ground_rule():
    """WHY THE PLANTS DO NOT RIDE THE 48 cm SIMILARITY, in one place.

    The 48 cm migration rescaled the ARCHITECTURE 0.96 about the world origin and then
    re-pivoted the temple by (-248, 0, 0). It did not touch the FutureMountV1 terrain or the
    metric city: those stand at identical coordinates on both maps. A tree is planted on the
    terrain, not on the Temple, so carrying it through the architecture's transform would lift
    132,598 plants off the ground they were sampled against and slide them 2.48 m west of the
    slope they belong to. The plants therefore stay exactly where the plan puts them -- and that
    is not taken on trust either: prove_ground() compares every terrain tile's live world AABB
    with the same tile read off Main50 before a single instance is added.

    The KEEP-OUT is the part that does move. The enclosure ring and the architecture blocker
    boxes are architecture, so on the candidate they close in by 4 per cent and shift 248 cm
    west. Both frames are used as blockers, never one: the candidate ring is contained in the
    Main50 ring, so testing both means no instance lands inside the Mount under EITHER
    interpretation, and the refusal geometry stays identical between the two maps.
    """
    return {
        'instances': 'identity: the terrain was never rescaled',
        'keepOut': 'blocked in BOTH the authored and the target frame',
        'placement': {'uniformScale': PLACEMENT_SCALE, 'translationCm': list(PLACEMENT_TRANSLATION)},
    }


def point_in_polygon(x, y, points):
    inside = False
    j = len(points) - 1
    for i in range(len(points)):
        xi, yi = points[i]
        xj, yj = points[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def point_segment_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length = dx * dx + dy * dy
    if length < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length))
    return math.hypot(px - (ax + dx * t), py - (ay + dy * t))


def distance_to_ring(x, y, points):
    best = float('inf')
    j = len(points) - 1
    for i in range(len(points)):
        best = min(best, point_segment_distance(x, y, points[j][0], points[j][1],
                                                points[i][0], points[i][1]))
        j = i
    return best


def union_constituent_boxes(entry):
    """World AABBs of the boxes a hollow derived-union mesh was built from.

    Identical arithmetic to release_place_assets.union_constituent_boxes: source elements are
    in amot with X east, Y up, Z south, and the manifest's mapping is [x*scale, z*scale, y*scale].
    """
    properties = entry.get('sourceProperties') or {}
    if 'source_elements_json' not in properties:
        return None
    scale = float(properties.get('source_metres_per_amah', 0.5)) * 100.0
    boxes = []
    for element in json.loads(properties['source_elements_json']):
        if element.get('shape') != 'box':
            return None
        position, size = element['position'], element['size']
        centre = [position[0] * scale, position[2] * scale, position[1] * scale]
        half = [size[0] * scale / 2.0, size[2] * scale / 2.0, size[1] * scale / 2.0]
        boxes.append({'name': element.get('name'),
                      'min': [centre[i] - half[i] for i in range(3)],
                      'max': [centre[i] + half[i] for i in range(3)]})
    return boxes


def verify_union_decomposition(entry, tolerance):
    boxes = union_constituent_boxes(entry)
    if not boxes:
        raise RuntimeError('Union %s has no box decomposition in the manifest' % entry['assetName'])
    recomposed = {'min': [min(b['min'][i] for b in boxes) for i in range(3)],
                  'max': [max(b['max'][i] for b in boxes) for i in range(3)]}
    expected = entry['expectedBoundsUnrealCm']
    error = max(abs(recomposed[k][i] - expected[k][i]) for k in ('min', 'max') for i in range(3))
    if error > tolerance:
        raise RuntimeError('Union %s decomposition differs from manifest bounds by %.3f cm'
                           % (entry['assetName'], error))
    return boxes


class Grid2D:
    """Uniform bucket grid, so a proximity query touches a handful of points, not 4265."""

    def __init__(self, cell_cm):
        self.cell = float(cell_cm)
        self.buckets = {}

    def insert(self, x, y, payload=None):
        key = (int(math.floor(x / self.cell)), int(math.floor(y / self.cell)))
        self.buckets.setdefault(key, []).append((x, y, payload))

    def within(self, x, y, radius):
        cx, cy = int(math.floor(x / self.cell)), int(math.floor(y / self.cell))
        span = int(math.ceil(radius / self.cell))
        for dy in range(-span, span + 1):
            for dx in range(-span, span + 1):
                for px, py, payload in self.buckets.get((cx + dx, cy + dy), ()):
                    if (px - x) ** 2 + (py - y) ** 2 <= radius * radius:
                        return payload if payload is not None else True
        return None


def species_form(manifest, key):
    for record in manifest['species']:
        if record['key'] == key:
            return record['form']
    raise KeyError(key)


def lod_screen_size(sphere_radius_cm, distance_cm, minimum):
    """UE screen size for a mesh of this radius at this distance.

    2 * radius / distance is the standard small-angle perspective approximation at a 90 degree
    horizontal field of view. It is an approximation, it is recorded as one in the spec, and it
    is a starting point for a visual tune rather than a final answer.
    """
    if distance_cm <= 0.0:
        return 1.0
    return max(minimum, min(1.0, 2.0 * sphere_radius_cm / distance_cm))


def offline_check(spec=None):
    """Consistency checks that need no engine. Raises on the first failure."""
    spec = spec or load_spec()
    plan = load_plan(spec)
    manifest = load_manifest(spec)
    problems = []

    obj_folder = ROOT / spec['objFolder']
    for record in manifest['meshes']:
        path = obj_folder / record['file']
        if not path.exists():
            problems.append('missing OBJ ' + record['file'])
        elif sha256_of(path) != record['sha256']:
            problems.append('OBJ changed since the manifest was written: ' + record['file'])
    texture_folder = ROOT / spec['textureFolder']
    for entry in manifest['textures']:
        for key in ('leafAtlas', 'barkBaseColour', 'barkNormal', 'billboardTexture'):
            name = entry.get(key)
            if not name:
                continue
            path = texture_folder / name
            if not path.exists():
                problems.append('missing texture ' + name)
            elif sha256_of(path) != entry[key + 'Sha256']:
                problems.append('texture changed since the manifest was written: ' + name)

    total = sum(batch['count'] for batch in plan['batches'])
    if total != plan['totalInstances']:
        problems.append('plan batch counts sum to %d, header says %d' % (total, plan['totalInstances']))
    if total > spec['instanceCapTotal']:
        problems.append('plan holds %d instances, cap is %d' % (total, spec['instanceCapTotal']))
    if len(set(batch['batchId'] for batch in plan['batches'])) != len(plan['batches']):
        problems.append('duplicate batch ids in the plan')
    for batch in plan['batches']:
        if len(batch['instances']) != batch['count']:
            problems.append('batch %s count mismatch' % batch['batchId'])
    if len(plan['instanceFormat']) != 9:
        problems.append('unexpected instance format %r' % (plan['instanceFormat'],))

    ring_receipt = json.loads((ROOT / spec['clearance']['mountEnclosureReceipt']).read_text(encoding='utf-8-sig'))
    ring = [(float(p[0]), float(p[1])) for p in ring_receipt['boundaryXYcm']]
    margin = spec['clearance']['mountEnclosureMarginCm']
    # BOTH frames, offline, before an engine is ever launched: the ring as it stands on the
    # authoring map and the ring as it stands on the target. The candidate ring is the Main50
    # ring closed in 4 per cent and shifted 248 cm west, so this is not an argument that one
    # contains the other -- it is the test, run on both.
    rings = {'authored': ring}
    if PLACEMENT_SCALE != 1.0 or PLACEMENT_TRANSLATION != [0.0, 0.0, 0.0]:
        rings[TARGET_LABEL] = [(x * PLACEMENT_SCALE + PLACEMENT_TRANSLATION[0],
                                y * PLACEMENT_SCALE + PLACEMENT_TRANSLATION[1]) for x, y in ring]
    inside = 0
    inside_by_frame = {}
    for name, points in rings.items():
        hits = 0
        for batch in plan['batches']:
            for row in batch['instances']:
                if point_in_polygon(row[0], row[1], points) or                         distance_to_ring(row[0], row[1], points) <= margin:
                    hits += 1
        inside_by_frame[name] = hits
        inside += hits
    if inside:
        problems.append('%d planned instances are inside the Mount enclosure ring or its margin: %s'
                        % (inside, inside_by_frame))

    architecture = json.loads((ROOT / spec['clearance']['architectureManifest']).read_text(encoding='utf-8-sig'))
    unions = [e for e in architecture['meshes'] if (e.get('sourceProperties') or {}).get('source_elements_json')]
    union_boxes = 0
    for entry in unions:
        union_boxes += len(verify_union_decomposition(entry, spec['clearance']['unionDecompositionToleranceCm']))

    if problems:
        raise RuntimeError('offline check failed: ' + '; '.join(problems[:8]))
    return {
        'specSha256': sha256_of(SPEC_PATH),
        'planSha256': sha256_of(ROOT / spec['plan']),
        'manifestSha256': sha256_of(ROOT / spec['manifest']),
        'meshFiles': len(manifest['meshes']),
        'textureSets': len(manifest['textures']),
        'plannedInstances': total,
        'batches': len(plan['batches']),
        'instanceCapTotal': spec['instanceCapTotal'],
        'target': TARGET_LABEL,
        'targetMap': TARGET,
        'placement': {'uniformScale': PLACEMENT_SCALE, 'translationCm': list(PLACEMENT_TRANSLATION)},
        'groundRule': ground_rule(),
        'mountEnclosureRingPoints': len(ring),
        'mountEnclosureFramesTested': sorted(rings),
        'plannedInstancesInsidePrecinct': inside,
        'plannedInstancesInsidePrecinctByFrame': inside_by_frame,
        'hollowUnionsVerified': len(unions),
        'hollowUnionConstituentBoxes': union_boxes,
        'note': ('Every planned instance was re-tested against the Mount enclosure ring here, '
                 'offline, before any engine was launched, and every hollow union decomposition '
                 'was verified against the architecture manifest bounds.'),
    }


# --------------------------------------------------------------------------
# Engine side
# --------------------------------------------------------------------------

def _asset_path(obj):
    return obj.get_path_name() if obj else None


def _vector_list(v):
    return [float(v.x), float(v.y), float(v.z)]


def _actor_bounds(actor):
    origin, extent = actor.get_actor_bounds(False)
    return {'min': [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
            'max': [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]}


# Terrain twins whose cut region legitimately differs between the two maps: the precinct square
# is 4 per cent smaller on the candidate, so its cut is too. They are never compared across maps.
CUT_TWIN_TOKENS = ('PrecinctCut', 'KotelPlazaCut', 'FutureMountCut')


class Release:
    """Engine handles, the cached scene snapshot and the receipt."""

    def __init__(self, ue, spec, plan, manifest):
        self.ue = ue
        self.spec = spec
        self.plan = plan
        self.manifest = manifest
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.world = None
        self.snapshot = None
        self.receipt = None
        self.receipt_path = None
        self.components = {}

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=1, default=str) + '\n',
                                     encoding='utf-8')

    # -- scene -------------------------------------------------------------

    def take_snapshot(self):
        ue = self.ue
        rows = []
        for actor in self.actors.get_all_level_actors():
            meshes = []
            for component in actor.get_components_by_class(ue.StaticMeshComponent):
                meshes.append(_asset_path(component.get_editor_property('static_mesh')))
            rows.append({'actor': actor, 'name': actor.get_name(), 'label': actor.get_actor_label(),
                         'folder': str(actor.get_folder_path()), 'meshes': meshes})
        self.snapshot = rows
        return rows

    def baseline(self, rows):
        return {row['name']: (row['label'], tuple(row['meshes']), str(row['folder'])) for row in rows}

    def prove_placement(self):
        """Where the ARCHITECTURE stands on this map, measured, not assumed.

        Nothing is planted on the architecture, so this is not what decides the instance
        coordinates -- prove_ground() is. It is here because the keep-out IS architecture: the
        enclosure ring and the blocker boxes are carried through this transform, and a transform
        that is not the one the level actually holds would put the Mount keep-out in the wrong
        place. Main50 must measure as the identity, Candidate48 as 0.96 and (-248, 0, 0).
        """
        rows = []
        for row in (self.snapshot or self.take_snapshot()):
            rows.append({'label': row['label'], 'meshes': row['meshes'],
                         'bounds': _actor_bounds(row['actor'])})
        by_key, manifest = mt.architecture_index(ROOT)
        proof = mt.prove_placement(rows, by_key, PLACEMENT_SCALE, PLACEMENT_TRANSLATION)
        proof.update({'target': TARGET_LABEL, 'map': TARGET,
                      'manifestMeshes': len(manifest['meshes']),
                      'usedFor': 'the Mount keep-out, not the instance coordinates'})
        self.receipt['placementProof'] = proof
        self.write_receipt()
        return proof

    def prove_ground(self):
        """The ground has not moved -- which is the whole licence for identity placement.

        The 48 cm migration rescaled the architecture and left the FutureMountV1 terrain alone,
        so the tiles the plants stand on must be byte-for-byte where Main50 holds them. That
        sentence is checked, not believed: every SM_JerusalemTerrain_* actor's live world AABB is
        compared with the same tile read off the live Main50 level by
        Scripts/candidate_placement_proof.py. The eleven *_PrecinctCut twins are excluded on both
        sides, because the precinct square they are cut to is itself 4 per cent smaller here.
        """
        rows = []
        for row in (self.snapshot or self.take_snapshot()):
            rows.append({'label': row['label'], 'meshes': row['meshes'],
                         'bounds': _actor_bounds(row['actor'])})
        live = {k: v for k, v in mt.terrain_fingerprint(rows).items()
                if not any(token in k for token in CUT_TWIN_TOKENS)}
        report = {'target': TARGET_LABEL, 'liveGroundTiles': len(live),
                  'reference': str(GROUND_REFERENCE),
                  'toleranceCm': GROUND_PARITY_TOLERANCE_CM,
                  'cutTwinTokensExcluded': list(CUT_TWIN_TOKENS)}
        if TARGET_KEY == mt.AUTHORING_TARGET:
            report['status'] = 'authoring_frame_is_its_own_reference'
            self.receipt['groundProof'] = report
            return report
        if not GROUND_REFERENCE.is_file():
            raise RuntimeError(
                'No Main50 ground fingerprint at %s. Run Scripts/candidate_placement_proof.py '
                'first: placing on %s at identity coordinates is only correct if the terrain is '
                'proved to be the same terrain, and nothing else in this project proves it.'
                % (GROUND_REFERENCE, TARGET_LABEL))
        reference = json.loads(GROUND_REFERENCE.read_text(encoding='utf-8-sig'))
        comparison = mt.compare_fingerprints(reference['tiles'], live)
        report.update(comparison)
        report['referenceStamp'] = reference.get('stamp')
        report['referenceMapSha256'] = reference.get('mapSha256')
        self.receipt['groundProof'] = report
        self.write_receipt()
        if comparison['matchedLabels'] < min(len(reference['tiles']), len(live)) or not live:
            raise RuntimeError('Ground tiles do not correspond between Main50 and %s: %s'
                               % (TARGET_LABEL, {k: comparison[k] for k in
                                                 ('inFirst', 'inSecond', 'matchedLabels',
                                                  'onlyInFirst', 'onlyInSecond')}))
        if comparison['worstBoundsErrorCm'] > GROUND_PARITY_TOLERANCE_CM:
            raise RuntimeError('The ground is NOT the same on %s: tile %s differs by %.4f cm. '
                               'Identity placement would put %d plants off their slope.'
                               % (TARGET_LABEL, comparison['worstLabel'],
                                  comparison['worstBoundsErrorCm'], self.plan['totalInstances']))
        report['status'] = 'ground_identical_to_main50_identity_placement_is_correct'
        self.write_receipt()
        return report

    def clearance_from_level(self):
        """Blockers read from the live level, with both AABB traps handled explicitly."""
        ue = self.ue
        clearance = self.spec['clearance']
        prefixes = tuple(clearance['terrainMeshPrefixes'])
        boxes = []
        terrain_skipped = 0
        # SUBSTRING, not startswith: the 256 tiles were imported with a `terrain_` prefix
        # normalisation, so the asset is terrain_SM_JerusalemTerrain_07_07 while the manifest
        # calls it SM_JerusalemTerrain_07_07. A startswith test would match nothing, the
        # exclusion would be silently off, and every point in the court would be blocked again.
        for row in self.snapshot:
            names = [n or '' for n in row['meshes']] + [row['label']]
            if any(token in name for name in names for token in prefixes):
                terrain_skipped += 1
                continue
        self.receipt['clearance'] = {
            'terrainActorsSkippedAsGround': terrain_skipped,
            'terrainMeshPrefixes': list(prefixes),
            'terrainNote': clearance['terrainMeshNote'],
        }
        if terrain_skipped == 0:
            raise RuntimeError('No terrain actor matched %r. The prefix has changed and the '
                               'exclusion is silently off, which is exactly how the 100 per cent '
                               'false-blocker result happened before.' % (prefixes,))

        architecture = json.loads((ROOT / clearance['architectureManifest']).read_text(encoding='utf-8-sig'))
        union_boxes = 0
        for entry in architecture['meshes']:
            decomposition = union_constituent_boxes(entry)
            if decomposition:
                for box in verify_union_decomposition(entry, clearance['unionDecompositionToleranceCm']):
                    boxes.append(box)
                    union_boxes += 1
                    # ... and the same box where this map actually holds it. On Main50 the
                    # placement is the identity and this is the same box twice; on the candidate
                    # it is the box 4 per cent smaller and 248 cm west, which is where the stone
                    # really is. Both are blockers, so nothing is planted inside the Mount under
                    # either interpretation and the two maps refuse the same instances.
                    if PLACEMENT_SCALE != 1.0 or PLACEMENT_TRANSLATION != [0.0, 0.0, 0.0]:
                        moved = mt.transform_box(box, PLACEMENT_SCALE, PLACEMENT_TRANSLATION)
                        moved['name'] = str(box.get('name')) + '@' + TARGET_LABEL
                        boxes.append(moved)
        self.receipt['clearance']['hollowUnionConstituentBoxes'] = union_boxes
        self.receipt['clearance']['blockerBoxesTotal'] = len(boxes)
        self.receipt['clearance']['hollowUnionNote'] = clearance['unionNote']
        self.receipt['clearance']['groundRule'] = ground_rule()

        # Existing illustrative trees: read their real instance transforms and keep out of them.
        tree_grid = Grid2D(clearance['existingTreeProximityCm'] * 2.0)
        existing = 0
        substrings = clearance['existingTreeMeshSubstrings']
        for row in self.snapshot:
            actor = row['actor']
            for component in actor.get_components_by_class(ue.InstancedStaticMeshComponent):
                mesh = _asset_path(component.get_editor_property('static_mesh')) or ''
                if not any(token in mesh for token in substrings):
                    continue
                count = int(component.get_instance_count())
                for index in range(count):
                    # 5.8 returns the Transform directly, not the (ok, transform) tuple the
                    # older binding produced; a missing instance raises rather than flagging.
                    try:
                        transform = component.get_instance_transform(index, True)
                    except Exception:  # noqa: BLE001 - skip an instance the component cannot resolve
                        continue
                    if transform is None:
                        continue
                    location = transform.translation
                    tree_grid.insert(float(location.x), float(location.y))
                    existing += 1
        self.receipt['clearance']['existingTreeInstancesRead'] = existing
        self.receipt['clearance']['existingTreeProximityCm'] = clearance['existingTreeProximityCm']
        self.receipt['clearance']['existingTreeNote'] = clearance['existingTreeNote']

        ring_receipt = json.loads((ROOT / clearance['mountEnclosureReceipt']).read_text(encoding='utf-8-sig'))
        ring = [(float(p[0]), float(p[1])) for p in ring_receipt['boundaryXYcm']]
        rings = [ring]
        if PLACEMENT_SCALE != 1.0 or PLACEMENT_TRANSLATION != [0.0, 0.0, 0.0]:
            rings.append([(x * PLACEMENT_SCALE + PLACEMENT_TRANSLATION[0],
                           y * PLACEMENT_SCALE + PLACEMENT_TRANSLATION[1]) for x, y in ring])
        self.receipt['clearance']['mountEnclosureRingPoints'] = len(ring)
        self.receipt['clearance']['mountEnclosureRingsTested'] = len(rings)
        self.receipt['clearance']['mountEnclosureNote'] = clearance['mountEnclosureNote']
        return {'boxes': boxes, 'trees': tree_grid, 'rings': rings,
                'ringMargin': clearance['mountEnclosureMarginCm'],
                'treeRadius': clearance['existingTreeProximityCm']}

    @staticmethod
    def blocked(clearance, x, y):
        for index, ring in enumerate(clearance['rings']):
            if point_in_polygon(x, y, ring):
                return 'inside_mount_enclosure_ring' + ('' if index == 0 else '_target_frame')
            if distance_to_ring(x, y, ring) <= clearance['ringMargin']:
                return 'within_mount_enclosure_margin' + ('' if index == 0 else '_target_frame')
        for box in clearance['boxes']:
            if box['min'][0] <= x <= box['max'][0] and box['min'][1] <= y <= box['max'][1]:
                return 'union_constituent_box:' + str(box.get('name'))
        if clearance['trees'].within(x, y, clearance['treeRadius']):
            return 'existing_tree_instance'
        return None

    # -- import ------------------------------------------------------------

    def import_assets(self):
        """Import every OBJ and PNG, then assemble the LOD ladders."""
        ue = self.ue
        spec = self.spec
        obj_folder = ROOT / spec['objFolder']
        texture_folder = ROOT / spec['textureFolder']
        tasks = []
        for record in self.manifest['meshes']:
            options = ue.FbxImportUI()
            options.set_editor_property('import_mesh', True)
            options.set_editor_property('import_textures', False)
            options.set_editor_property('import_materials', False)
            options.set_editor_property('import_as_skeletal', False)
            options.static_mesh_import_data.set_editor_property('combine_meshes', True)
            options.static_mesh_import_data.set_editor_property('generate_lightmap_u_vs', True)
            options.static_mesh_import_data.set_editor_property('auto_generate_collision', False)
            task = ue.AssetImportTask()
            task.set_editor_property('filename', str(obj_folder / record['file']))
            task.set_editor_property('destination_path', spec['meshFolder'])
            task.set_editor_property('destination_name', record['mesh'])
            task.set_editor_property('replace_existing', True)
            task.set_editor_property('automated', True)
            task.set_editor_property('save', False)
            task.set_editor_property('options', options)
            tasks.append(task)
        for entry in self.manifest['textures']:
            for key in ('leafAtlas', 'barkBaseColour', 'barkNormal', 'billboardTexture'):
                name = entry.get(key)
                if not name:
                    continue
                task = ue.AssetImportTask()
                task.set_editor_property('filename', str(texture_folder / name))
                task.set_editor_property('destination_path', spec['textureAssetFolder'])
                task.set_editor_property('replace_existing', True)
                task.set_editor_property('automated', True)
                task.set_editor_property('save', False)
                tasks.append(task)
        ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

        imported, missing = [], []
        for record in self.manifest['meshes']:
            path = '%s/%s' % (spec['meshFolder'], record['mesh'])
            asset = ue.EditorAssetLibrary.load_asset(path)
            if asset is None:
                missing.append(record['mesh'])
                continue
            imported.append({'mesh': record['mesh'], 'asset': path,
                             'triangles': record['triangles'],
                             'canonicalBoundsCm': record['canonicalBoundsCm']})
        if missing:
            raise RuntimeError('%d meshes failed to import, first: %s' % (len(missing), missing[:5]))
        self.receipt['importedMeshes'] = len(imported)
        self.receipt['importedMeshList'] = imported
        return imported

    def assemble_lods(self):
        """Fold each species' LOD1/LOD2/billboard meshes into the LOD0 mesh as real LODs."""
        ue = self.ue
        spec = self.spec
        subsystem = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem)
        ladders = {}
        for record in self.manifest['meshes']:
            if record.get('variant'):
                continue
            role = record['materialRole']
            key = (record['species'], 'leaf' if role in ('leaf', 'billboard') else 'bark')
            ladders.setdefault(key, []).append(record)
        assembled = []
        for (species, role), records in sorted(ladders.items()):
            records.sort(key=lambda r: r['lodStartDistanceCm'])
            base = records[0]
            base_asset = ue.EditorAssetLibrary.load_asset('%s/%s' % (spec['meshFolder'], base['mesh']))
            radius = 0.5 * math.sqrt(sum((base['canonicalBoundsCm']['max'][i]
                                          - base['canonicalBoundsCm']['min'][i]) ** 2 for i in range(3)))
            screen_sizes = [1.0]
            for index, record in enumerate(records[1:], start=1):
                source = ue.EditorAssetLibrary.load_asset('%s/%s' % (spec['meshFolder'], record['mesh']))
                subsystem.set_lod_from_static_mesh(base_asset, index, source, 0, True)
                screen_sizes.append(lod_screen_size(radius, record['lodStartDistanceCm'],
                                                    spec['lod']['minimumScreenSize']))
            # Apply the screen sizes if the engine exposes it. Recorded either way: a silent
            # fallback to the engine's automatic screen sizes would leave the LOD distances in
            # the plan looking authoritative when nothing had used them.
            applied = False
            try:
                applied = bool(subsystem.set_lod_screen_sizes(base_asset, screen_sizes))
            except Exception as error:                       # noqa: BLE001
                self.receipt.setdefault('lodScreenSizeErrors', []).append(
                    {'mesh': base['mesh'], 'error': str(error)[:200]})
            assembled.append({'species': species, 'role': role, 'mesh': base['mesh'],
                              'lodCount': len(records),
                              'lodStartDistanceCm': [r['lodStartDistanceCm'] for r in records],
                              'lodScreenSizes': [round(s, 5) for s in screen_sizes],
                              'lodScreenSizesApplied': applied,
                              'boundsSphereRadiusCm': round(radius, 2),
                              'screenSizeRule': spec['lod']['screenSizeRule']})
        self.receipt['lodLadders'] = assembled
        return assembled

    # -- placement ---------------------------------------------------------

    def new_hism(self, actor):
        """Instance-owned HISM on a plain editor actor.

        UE 5.8 declares AActor::AddComponentByClass with meta=(ScriptNoExport,
        BlueprintInternalUseOnly), so it is deliberately absent from the Python bindings and
        actor.add_component_by_class raises AttributeError. That is exactly how the placement
        stage of this script failed in receipt release-vegetation-20260909T174529264332Z.json,
        and it is the same failure release_city_detail.py hit and solved; this is that solution,
        the editor's own subobject path, with ownership verified three ways before any instance
        is added. Merely constructing HierarchicalInstancedStaticMeshComponent(outer=actor)
        would produce a component the level never owns.
        """
        ue = self.ue
        subsystem = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
        library = ue.SubobjectDataBlueprintFunctionLibrary
        handles = subsystem.k2_gather_subobject_data_for_instance(actor)
        parent = next((handle for handle in handles
                       if library.get_associated_object(library.get_data(handle)) == actor), None)
        if parent is None:
            raise RuntimeError('Editor actor subobject handle missing')
        params = ue.AddNewSubobjectParams(
            parent_handle=parent,
            new_class=ue.HierarchicalInstancedStaticMeshComponent,
            blueprint_context=None, conform_transform_to_parent=True)
        handle, reason = subsystem.add_new_subobject(params)
        if not library.is_handle_valid(handle):
            raise RuntimeError('Persistent HISM creation failed: ' + str(reason))
        data = library.get_data(handle)
        component = library.get_associated_object(data)
        if not isinstance(component, ue.HierarchicalInstancedStaticMeshComponent):
            raise RuntimeError('Subobject is a %s, not a HISM' % type(component).__name__)
        if component.get_owner() != actor or not library.is_instanced_component(data):
            raise RuntimeError('HISM ownership/instance creation not verified')
        if component not in actor.get_components_by_class(
                ue.HierarchicalInstancedStaticMeshComponent):
            raise RuntimeError('HISM absent from the actor component readback')
        return component

    def component_for(self, species, role):
        """One hierarchical instanced component per species and material role."""
        ue = self.ue
        spec = self.spec
        key = (species, role)
        if key in self.components:
            return self.components[key]
        mesh_name = '%s%s_L0_%s' % (spec['meshPrefix'], species, role.capitalize())
        mesh = ue.EditorAssetLibrary.load_asset('%s/%s' % (spec['meshFolder'], mesh_name))
        if mesh is None:
            raise RuntimeError('Mesh not imported: ' + mesh_name)
        label = '%s%s_%s_%s' % (spec['labelPrefix'], spec['group'], species, role.capitalize())
        form = species_form(self.manifest, species)
        cull = float(spec['lod']['cullDistanceCm'][form])

        # RESUME MUST ADOPT, NOT DUPLICATE. A resumed run meets the actors the previous run
        # saved; spawning a second actor under the same label is what made receipt
        # release-vegetation-20260910T020616142404Z fail its own reopen readback with
        # "Reopened actor count for RELEASE_Vegetation_Olive_Bark is 2" AFTER the save.
        # The clash check in place() already assumes these actors exist on a resume; this is
        # the other half of that contract. `added` starts at the instances already on the
        # component, so the post-reopen count check stays exact rather than being relaxed.
        existing = [row['actor'] for row in (self.snapshot or []) if row['label'] == label]
        if len(existing) > 1:
            raise RuntimeError('%d actors already carry the label %s; refusing to guess'
                               % (len(existing), label))
        if existing:
            actor = existing[0]
            components = actor.get_components_by_class(ue.HierarchicalInstancedStaticMeshComponent)
            if len(components) != 1:
                raise RuntimeError('%s has %d instanced components, expected exactly 1'
                                   % (label, len(components)))
            component = components[0]
            found_mesh = _asset_path(component.get_editor_property('static_mesh')) or ''
            if mesh_name not in found_mesh:
                raise RuntimeError('%s carries mesh %s, not %s' % (label, found_mesh, mesh_name))
            already = int(component.get_instance_count())
            self.components[key] = {'actor': actor, 'component': component, 'label': label,
                                    'mesh': mesh_name, 'species': species, 'role': role,
                                    'added': already, 'preexistingInstances': already,
                                    'adopted': True, 'cullDistanceCm': cull}
            return self.components[key]

        actor = self.actors.spawn_actor_from_class(ue.Actor, ue.Vector(0.0, 0.0, 0.0))
        actor.set_actor_label(label)
        actor.set_folder_path(spec['folder'])
        actor.set_editor_property('tags', [ue.Name(spec['actorTag'])])
        component = self.new_hism(actor)
        component.set_editor_property('static_mesh', mesh)
        component.set_mobility(ue.ComponentMobility.STATIC)
        component.set_collision_profile_name('NoCollision')
        component.set_cull_distances(int(cull * spec['lod']['cullStartFraction']), int(cull))
        self.components[key] = {'actor': actor, 'component': component, 'label': label,
                                'mesh': mesh_name, 'species': species, 'role': role,
                                'added': 0, 'preexistingInstances': 0, 'adopted': False,
                                'cullDistanceCm': cull}
        return self.components[key]

    def place_batches(self, batches, clearance):
        ue = self.ue
        placed_rows = []
        refused = {}
        for batch in batches:
            species = batch['species']
            roles = ['leaf'] if species_form(self.manifest, species) == 'grass' else ['bark', 'leaf']
            accepted = []
            for row in batch['instances']:
                reason = self.blocked(clearance, row[0], row[1])
                if reason:
                    refused[reason] = refused.get(reason, 0) + 1
                    continue
                accepted.append(row)
            transforms = []
            for row in accepted:
                transforms.append(ue.Transform(
                    ue.Vector(row[0], row[1], row[2]),
                    ue.Rotator(row[4], row[3], row[5]),
                    ue.Vector(row[6], row[6], row[7])))
            for role in roles:
                entry = self.component_for(species, role)
                if transforms:
                    entry['component'].add_instances(transforms, False)
                    entry['added'] += len(transforms)
            placed_rows.append({'batchId': batch['batchId'], 'species': species, 'cell': batch['cell'],
                                'planned': batch['count'], 'placed': len(accepted),
                                'roles': roles})
            self.receipt['completedBatchIds'].append(batch['batchId'])
        self.receipt['refusedByClearance'] = refused
        self.receipt['batchesPlaced'] = placed_rows
        return placed_rows

    def readback(self):
        """Numeric instance counts after the reopen. This is the check that matters."""
        ue = self.ue
        rows = []
        for entry in sorted(self.components.values(), key=lambda e: e['label']):
            matching = [row for row in self.snapshot if row['label'] == entry['label']]
            if len(matching) != 1:
                raise RuntimeError('Reopened actor count for %s is %d' % (entry['label'], len(matching)))
            actor = matching[0]['actor']
            components = actor.get_components_by_class(ue.HierarchicalInstancedStaticMeshComponent)
            if len(components) != 1:
                raise RuntimeError('%s has %d instanced components after reopen, expected 1'
                                   % (entry['label'], len(components)))
            component = components[0]
            count = int(component.get_instance_count())
            mesh = _asset_path(component.get_editor_property('static_mesh')) or ''
            bounds = actor.get_actor_bounds(False)
            row = {'label': entry['label'], 'species': entry['species'], 'role': entry['role'],
                   'meshPath': mesh, 'expectedInstances': entry['added'],
                   'readbackInstances': count,
                   'cullDistanceCm': entry['cullDistanceCm'],
                   'worldBoundsCentreCm': _vector_list(bounds[0]),
                   'worldBoundsExtentCm': _vector_list(bounds[1])}
            if count != entry['added']:
                raise RuntimeError('%s: %d instances written, %d read back after reopen. '
                                   'Runtime-added instance components did not persist.'
                                   % (entry['label'], entry['added'], count))
            if entry['mesh'] not in mesh:
                raise RuntimeError('%s: reopened mesh %s is not %s' % (entry['label'], mesh, entry['mesh']))
            rows.append(row)
        self.receipt['reopenedReadback'] = rows
        self.receipt['reopenedInstanceTotal'] = sum(r['readbackInstances'] for r in rows)
        return rows


def place(load_target=True, max_batches=None, resume_receipt=None, species_filter=None,
          import_only=False, skip_import=False):
    """Run the guarded placement. Returns the receipt dict; raises on guard failure."""
    import unreal as ue
    spec = load_spec()
    plan = load_plan(spec)
    manifest = load_manifest(spec)
    offline = offline_check(spec)

    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    run = Release(ue, spec, plan, manifest)
    if run.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if load_target:
        if not run.levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
    run.world = run.editor.get_editor_world()
    loaded = run.world.get_outermost().get_name()
    if loaded != TARGET:
        raise RuntimeError('Loaded world %s is not the combined map %s' % (loaded, TARGET))
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present; resolve before checkpointed placement')

    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha256_of(map_file)
    # The OTHER target is protected too. The spec's list predates the candidate, so on a
    # Candidate48 run it would leave the map that every plan in this project is authored against
    # unwatched -- and a concurrent save of it is exactly what tripped the cp02b build guard.
    protected_paths = list(spec['protectedMaps']) + [
        config['map'] for key, config in mt.TARGETS.items() if config['map'] != TARGET]
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in protected_paths
                 if disk_path(m, 'umap').exists()}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

    checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + TARGET_LABEL
                                                 + '-' + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(map_file, checkpoint / map_file.name)
    if sha256_of(checkpoint / map_file.name) != map_sha_before:
        raise RuntimeError('Checkpoint copy hash differs')
    external_copied = []
    for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
        external = ROOT / 'Content' / folder_name / TARGET[6:]
        if external.exists():
            shutil.copytree(external, checkpoint / folder_name / TARGET[6:])
            external_copied.append(str(external))

    receipt_folder = ROOT / spec['receiptFolder']
    receipt_folder.mkdir(parents=True, exist_ok=True)
    run.receipt_path = receipt_folder / (spec['receiptPrefix'] + TARGET_LABEL + '-'
                                         + stamp + '.json')
    if run.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(run.receipt_path))

    already_done = []
    if resume_receipt:
        previous = json.loads(Path(resume_receipt).read_text(encoding='utf-8'))
        if previous.get('planSha256') != offline['planSha256']:
            raise RuntimeError('Resume receipt was made against a different placement plan')
        # A resume is per MAP. Skipping the batches a Main50 run completed would leave the
        # candidate with a hole exactly the shape of the other map's progress, and the hole
        # would never be visible in a count that only ever compares against the plan.
        previous_target = previous.get('target') or mt.TARGETS[mt.AUTHORING_TARGET]['key']
        if previous_target != TARGET_LABEL or (previous.get('map') or TARGET) != TARGET:
            raise RuntimeError('Resume receipt is for %s (%s), this run is for %s (%s)'
                               % (previous_target, previous.get('map'), TARGET_LABEL, TARGET))
        already_done = list(previous.get('completedBatchIds') or [])

    pending = [b for b in plan['batches'] if b['batchId'] not in set(already_done)]
    if species_filter:
        pending = [b for b in pending if b['species'] in species_filter]
    limit = max_batches if max_batches is not None else spec['batching']['defaultMaxBatchesPerRun']
    selected = pending[:limit] if limit and limit > 0 else pending

    run.receipt = {
        'status': 'checkpointed_vegetation_placement_started',
        'stamp': stamp,
        'target': TARGET_LABEL,
        'targetRole': TARGET_CONFIG['role'],
        'placement': {'uniformScale': PLACEMENT_SCALE,
                      'translationCm': list(PLACEMENT_TRANSLATION),
                      'appliedTo': 'the Mount keep-out only; the instances stand at identity',
                      'derivation': TARGET_CONFIG['derivation']},
        'groundRule': ground_rule(),
        'authoringMap': AUTHORING_MAP,
        'map': TARGET,
        'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'checkpoint': str(checkpoint),
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH),
        'specSha256': offline['specSha256'],
        'planSha256': offline['planSha256'],
        'manifestSha256': offline['manifestSha256'],
        'offlineCheck': offline,
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'seed': plan['seed'],
        'resumeReceipt': str(resume_receipt) if resume_receipt else None,
        'batchesAlreadyComplete': len(already_done),
        'batchesPending': len(pending),
        'batchesSelectedThisRun': len(selected),
        'batchesRemainingAfterThisRun': max(0, len(pending) - len(selected)),
        'speciesFilter': sorted(species_filter) if species_filter else None,
        'completedBatchIds': list(already_done),
        'importOnly': bool(import_only),
        'errors': [],
        'mapSaved': False,
        'limitations': list(spec['limitations']) + list(TARGET_LIMITATIONS),
    }
    run.write_receipt()

    saved = False
    try:
        run.take_snapshot()
        baseline = run.baseline(run.snapshot)
        clashes = [row['label'] for row in run.snapshot
                   if row['label'].startswith(spec['labelPrefix'] + spec['group'] + '_')]
        if clashes and not already_done:
            raise RuntimeError('Vegetation release actors already exist and no resume receipt was '
                               'given; refusing duplicate placement: %s' % clashes[:8])

        if not skip_import:
            run.import_assets()
            run.assemble_lods()
            run.write_receipt()
        if import_only:
            run.receipt['status'] = 'meshes_imported_no_placement'
            if not ue.EditorAssetLibrary.save_directory(spec['assetFolder'], False, True):
                raise RuntimeError('save_directory failed for ' + spec['assetFolder'])
            return run.receipt

        run.prove_placement()
        run.prove_ground()
        clearance = run.clearance_from_level()
        run.write_receipt()
        placed = run.place_batches(selected, clearance)
        total_added = sum(entry['added'] for entry in run.components.values())
        if total_added == 0:
            run.receipt['status'] = 'nothing_placed_map_unchanged'
            return run.receipt

        current = run.baseline(run.take_snapshot())
        changed = [name for name, row in baseline.items() if current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:8])

        if not ue.EditorAssetLibrary.save_directory(spec['assetFolder'], False, True):
            raise RuntimeError('save_directory failed for ' + spec['assetFolder'])
        if not run.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        run.receipt['mapSaved'] = True
        run.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        run.write_receipt()

        if not run.levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        run.world = run.editor.get_editor_world()
        run.take_snapshot()
        reopened_numeric = run.baseline(run.snapshot)
        changed = [name for name, row in baseline.items() if reopened_numeric.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors differ after reopen: %s' % changed[:8])
        run.readback()

        run.receipt['batchesPlacedThisRun'] = len(placed)
        run.receipt['instancesPlacedThisRun'] = total_added
        run.receipt['status'] = ('vegetation_placed_saved_reopened_visual_runtime_acceptance_pending'
                                 if run.receipt['batchesRemainingAfterThisRun'] == 0 else
                                 'vegetation_batch_placed_saved_reopened_resume_required')
        return run.receipt
    except Exception as error:
        run.receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        run.receipt['status'] = ('failed_after_save_checkpoint_available' if saved
                                 else 'failed_before_save_map_unchanged')
        raise
    finally:
        run.receipt['mapSha256After'] = sha256_of(map_file)
        run.receipt['mapBytesChanged'] = run.receipt['mapSha256After'] != map_sha_before
        run.receipt['protectedMapsUnchanged'] = all(
            sha256_of(disk_path(m, 'umap')) == value for m, value in protected.items())
        run.write_receipt()


def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    """True only when the engine itself is executing this file as a script."""
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return 'release_vegetation.py' in command_line and (
        '-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line()
    lowered = command_line.lower()
    max_batches = None
    resume = None
    species = None
    import_only = '-vegetationimportonly' in lowered
    skip_import = '-vegetationskipimport' in lowered
    for token in command_line.split():
        low = token.lower()
        if low.startswith('-vegetationmaxbatches='):
            max_batches = int(token.split('=', 1)[1])
        elif low.startswith('-vegetationresume='):
            resume = token.split('=', 1)[1].strip('"')
        elif low.startswith('-vegetationspecies='):
            species = set(part for part in token.split('=', 1)[1].strip('"').split(',') if part)
    try:
        receipt = place(load_target=True, max_batches=max_batches, resume_receipt=resume,
                        species_filter=species, import_only=import_only, skip_import=skip_import)
        ue.log('release_vegetation [%s]: %s placed %s this run, %s batches remain' % (
            TARGET_LABEL, receipt['status'], receipt.get('instancesPlacedThisRun'),
            receipt.get('batchesRemainingAfterThisRun')))
    except Exception as error:
        ue.log_error('release_vegetation failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in lowered and '-run=pythonscript' not in lowered:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    elif mt.revert_from_command_line():
        _action = mt.revert_from_command_line()
        print(json.dumps(mt.restore_checkpoint(_action['receipt'], dry_run=_action['dryRun']), indent=2))
    else:
        print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()
