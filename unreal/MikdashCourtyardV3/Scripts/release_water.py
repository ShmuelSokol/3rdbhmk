"""Guarded release of MikdashWaterV1: the stream of Yechezkel 47, its channel and the mikvaot.

Imports the OBJs written by Scripts/create_water_geometry.py, builds the water and channel
materials with MaterialEditingLibrary, places the meshes in the combined IntegratedReviewV2
map, tags every water surface, spawns one AMikdashWater to drive them, then saves, reopens
and reads back every number.

Commandlet invocation (serial; never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_water.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-Water-01.log"

Optional switches, read from the engine command line:
  -WaterGroups=court,stages,mikvaot   subset to place (default: all three).
  -WaterImportOnly                    import and build materials, place nothing, save nothing.
  -WaterSkipActor                     do not spawn AMikdashWater (use when the plugin has not
                                      been rebuilt yet and the class is not registered).

Run with no engine at all to get the offline check as JSON:
  python Scripts/release_water.py

ORDER OF OPERATIONS (nothing here works if these are done out of order)
----------------------------------------------------------------------
  1. python Scripts/create_water_geometry.py --export
  2. rebuild the plugin, so AMikdashWater exists as a class     <- REQUIRED before step 4
  3. python Scripts/release_water.py            (offline check must be green)
  4. the commandlet above

SAFETY MODEL (the same one release_place_assets.py uses, and for the same reasons)
---------------------------------------------------------------------------------
  * Refuses to run with the wrong project directory, a live game world, a loaded world that
    is not the combined map, or any dirty package.
  * Requires the geometry manifest's status to be OFFLINE_VALIDATED_NATIVE_AND_VISUAL_PENDING.
    A manifest written by `create_water_geometry.py --force` carries a different status and is
    refused, so a forced export can never reach a map by accident.
  * Every frozen OBJ is hashed against the manifest before it is imported.
  * Copies Walkthrough.umap and any One-File-Per-Actor folders to a timestamped checkpoint
    and verifies the copy by hash before any mutation.
  * Existing RELEASE_Water_* actors cause a refusal, not a duplicate placement.
  * Saves only if something was placed; then reopens the map and reads back every actor's
    mesh path, transform and world bounds numerically.
  * The receipt is written at start and again in `finally`, so a failure leaves evidence.

THE CLEARANCE TRAP, AND WHY THIS SCRIPT DOES NOT USE RAW ACTOR BOUNDS
---------------------------------------------------------------------
Three separate things in this level have axis-aligned bounds that enclose most of the site,
and testing any of them naively reports the water as blocked by scenery it is nowhere near:

  1. THE 260 FutureMountV1 TERRAIN TILES. Each cut tile spans 400-800 m and its AABB
     encloses the whole Temple. Tested raw they produced 100 per cent false blockers.
  2. THE HOLLOW DERIVED-UNION ENVELOPES. 'Derived union of source outer envelope walls' is a
     Boolean union of 116 wall boxes; its AABB is the entire court. release_place_assets.py
     records the same false positive from 2026-09-07 and decomposes it into its constituent
     boxes from the architecture manifest, which is what this script does too.
  3. THE GENERATED CHANNEL ITSELF. A channel that leaves the House at Y 400 and runs east at
     Y 1050 has a whole-part AABB covering the altar, its ramp and the chut hasikra, none of
     which it comes near. Its narrow phase is the 2307 decomposed sub-boxes published as
     SourceAssets/water-review/MikdashWaterV1/clearance-boxes.json.

So: broad phase on bounds, narrow phase on decomposed boxes, on BOTH sides. Terrain tiles are
excluded by name and counted, because a heightfield cannot be decomposed into boxes and a
conduit sunk into the mount is expected to meet it; the offline clearance against the
architecture manifest (clearance.json, 0 blockers) is the authority for the built Temple.

WHAT THIS DOES NOT ESTABLISH
----------------------------
Geometry and material wiring only. No visual acceptance, no walking, no halachic acceptance,
no lighting build, no cook. What is textual, what is disputed and what this project invented
is in SourceAssets/water-review/sources.md; nothing here asserts any of it.
"""
import hashlib
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_water.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
GROUP_ORDER = ('court', 'stages', 'mikvaot')

# Exact architecture-manifest sourceName values, mirroring HOST_MESH_NAMES and
# HOLLOW_UNION_NAMES in Scripts/create_water_geometry.py. A courtyard conduit is by nature a
# cut in the first list and must never be a cut in anything else; the second list is the
# hollow Boolean unions whose AABB encloses the site and which must be decomposed, not tested.
HOST_SOURCE_NAMES = [
    'Ulam stair', 'Ezras Kohanim floor', 'Raised priest court foundation', 'Duchan rise',
    'Inner court clear floor', 'Inner court supporting platform', 'Inner E cell supporting plinth',
    'Inner E continuous cell doorway floor', 'Outer court floor', 'Outer court supporting platform',
    'Western outer court foundation', 'Outer E vestibule floor', 'Outer E threshold',
    'Outer E cell access landing', 'Outer E stair', 'Outer S threshold', 'Inner S threshold',
    'Inner S vestibule floor', 'Inner S stair', 'Priestly room floor', 'Priestly chamber precinct',
    'Court string course and cornice', 'Derived union of source western paving and transition',
]
HOLLOW_UNION_SOURCE_NAMES = [
    'Derived union of source outer envelope walls',
    'Derived union of source House walls and roofs',
    'Derived union of source raised gallery slabs',
    'Derived union of House and Ulam foundations',
]


# --------------------------------------------------------------------------
# Pure helpers. Nothing below imports unreal, so offline_check() runs anywhere.
# --------------------------------------------------------------------------

def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def base_source_name(source_name):
    """Strip the numeric suffix off a manifest sourceName.

    The manifest names mirrored meshes and repeated courses with a running number: 'Ulam
    stair 6', 'Outer E stair 3', 'Duchan rise 1'. create_water_geometry.py folds those to a
    base name before classifying hosts, and this MUST do the same or 25 stair treads and
    duchan courses that the conduit legitimately rests on are reported as blockers. Identical
    to base_name() in the authoring script, character for character.
    """
    return ''.join(c for c in source_name if not c.isdigit()).strip().rstrip('-').strip()


ASSET_INDEX_TOKEN = re.compile(r'(SM_\d{4}_.+)$')


def manifest_key_for_asset(asset_name):
    """Reduce a LEVEL mesh asset name to the manifest assetName it was imported from.

    THE LIVE FAILURE OF 2026-09-08T22:06Z. The architecture importer prefixes every mesh
    with its import group: the manifest entry 'SM_0000_architecture_Ulam_stair_6' lives in
    the level as '/Game/MikdashV3/Architecture/architecture_SM_0000_architecture_Ulam_stair_6'.
    An exact-key lookup on the bare assetName therefore matched NOTHING -- 531 architecture
    actors came back with no sourceName, no host classification and no union decomposition,
    and 46 stair treads, floors and platforms the conduit is cut into were reported as
    blockers. The manifest's four-digit index token is unique per entry, so the key is
    everything from 'SM_NNNN_' onward, whatever was prepended in front of it.
    """
    if not asset_name:
        return None
    match = ASSET_INDEX_TOKEN.search(asset_name)
    return match.group(1) if match else asset_name


def manifest_entry_for_assets(asset_names, by_key):
    """First manifest entry any of an actor's mesh assets resolves to, or None."""
    for asset in asset_names:
        entry = by_key.get(manifest_key_for_asset(asset))
        if entry is not None:
            return entry
    return None


def classify_source(source_name, host_names, union_names):
    """'host' | 'union' | 'other' for a manifest sourceName, after suffix normalisation."""
    base = base_source_name(source_name) if source_name else None
    if base in union_names:
        return 'union'
    if base in host_names:
        return 'host'
    return 'other'


def self_test_classification(arch, spec):
    """The live names that were misclassified on 2026-09-08, asserted forever.

    Runs inside offline_check(), so the gate the operator runs before the commandlet IS the
    unit test. Every name below is copied verbatim from the failing receipt's
    liveClearance.unmatchedActors / blockers, not typed from memory.
    """
    by_key = {manifest_key_for_asset(e['assetName']): e for e in arch['meshes']}
    hosts = set(spec['clearance']['hostSourceNames'])
    unions = set(spec['clearance']['hollowUnionSourceNames'])
    expect = {
        # live asset name                                                   -> expected class
        'architecture_SM_0000_architecture_Ulam_stair_6': 'host',
        'architecture_SM_0006_architecture_Ulam_stair_12': 'host',
        'architecture_SM_0261_architecture_Outer_E_stair_1': 'host',
        'architecture_SM_1669_architecture_Duchan_rise_1': 'host',
        'architecture_SM_0494_architecture_Inner_E_cell_supporting_plinth': 'host',
        'architecture_SM_0166_architecture_Southern_kevesh_ascend_north': 'other',
        'architecture_SM_0138_architecture_Inner_eastern_gate_wall_jamb_1': 'other',
        'architecture_SM_0073_vessel_Hollow_basin_with_inner_wall': 'other',
    }
    failures, results = [], {}
    for asset, wanted in expect.items():
        entry = manifest_entry_for_assets([asset], by_key)
        got = classify_source(entry['sourceName'], hosts, unions) if entry else 'UNMATCHED'
        results[asset] = {'sourceName': entry['sourceName'] if entry else None, 'class': got}
        if got != wanted:
            failures.append('%s -> %s, expected %s' % (asset, got, wanted))
    # The four hollow unions must be found under the live prefix AND decompose exactly.
    for e in arch['meshes']:
        if base_source_name(e['sourceName']) in unions:
            live_name = 'architecture_' + e['assetName']
            entry = manifest_entry_for_assets([live_name], by_key)
            boxes = union_constituent_boxes(entry) if entry else None
            ok, error = verify_union_decomposition(entry, boxes) if entry else (False, None)
            results[live_name] = {'sourceName': e['sourceName'], 'class': 'union',
                                  'constituentBoxes': len(boxes) if boxes else 0,
                                  'recomposedOk': ok, 'recomposeErrorCm': error}
            if not ok:
                failures.append('%s: union not decomposed live (error %r)' % (live_name, error))
    return {'ok': not failures, 'failures': failures, 'cases': results}


def normalise_groups(groups):
    if isinstance(groups, str):
        groups = [g for g in groups.replace(';', ',').split(',') if g.strip()]
    wanted = [g.strip().lower() for g in groups]
    unknown = [g for g in wanted if g not in GROUP_ORDER]
    if unknown:
        raise ValueError('Unknown water groups: %s (choose from %s)' % (unknown, list(GROUP_ORDER)))
    return tuple(g for g in GROUP_ORDER if g in wanted) or GROUP_ORDER


def box_from_min_max(minimum, maximum):
    return {'min': [float(v) for v in minimum], 'max': [float(v) for v in maximum]}


def box_error(a, b):
    return max(abs(a[key][i] - b[key][i]) for key in ('min', 'max') for i in range(3))


def boxes_overlap(a, b, tolerance=1e-6):
    for i in range(3):
        if min(a['max'][i], b['max'][i]) - max(a['min'][i], b['min'][i]) <= tolerance:
            return False
    return True


def overlap_depth(a, b):
    """Interpenetration on the tightest axis. Positive only when the boxes really overlap."""
    return min(min(a['max'][i], b['max'][i]) - max(a['min'][i], b['min'][i]) for i in range(3))


def separation_cm(a, b):
    """True Euclidean distance between two AABBs; zero when they touch or interpenetrate.

    Not overlap_depth(): that is a per-axis quantity, and minimising it over a set of pairs
    finds the FARTHEST pair rather than the nearest. Clearances are minimised over THIS.
    """
    d = [max(0.0, a['min'][i] - b['max'][i], b['min'][i] - a['max'][i]) for i in range(3)]
    return math.sqrt(sum(v * v for v in d))


def union_constituent_boxes(entry):
    """World AABBs, cm, of the source boxes a hollow derived-union mesh was built from.

    Byte-for-byte the convention proven by Scripts/release_place_assets.py, and it is not
    guessable: source elements are in AMOT with X east, Y UP, Z south, so the manifest's
    expectedSourceToUnrealCm swizzle is [x, z, y] * (metres_per_amah * 100). 'position' is
    the box centre and 'size' the full extent. verify_union_decomposition() proves the
    convention on every entry before any of it is trusted.
    """
    properties = entry.get('sourceProperties') or {}
    if 'source_elements_json' not in properties:
        return None
    scale = float(properties.get('source_metres_per_amah', 0.5)) * 100.0
    boxes = []
    for element in json.loads(properties['source_elements_json']):
        if element.get('shape') != 'box':
            return None                      # a non-box element makes the whole set untrustworthy
        position, size = element['position'], element['size']
        centre = [position[0] * scale, position[2] * scale, position[1] * scale]
        half = [size[0] * scale / 2.0, size[2] * scale / 2.0, size[1] * scale / 2.0]
        boxes.append(box_from_min_max([centre[i] - half[i] for i in range(3)],
                                      [centre[i] + half[i] for i in range(3)]))
    return boxes or None


def verify_union_decomposition(entry, boxes, tolerance=0.05):
    """The decomposition is trusted only if recomposing it reproduces the manifest bounds."""
    if not boxes:
        return False, None
    got = box_from_min_max([min(b['min'][i] for b in boxes) for i in range(3)],
                           [max(b['max'][i] for b in boxes) for i in range(3)])
    error = box_error(got, entry['expectedBoundsUnrealCm'])
    return error <= tolerance, error


def load_geometry(spec):
    folder = ROOT / spec['source']['folder']
    manifest_path = folder / 'geometry-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    boxes_path = folder / manifest['clearanceBoxesFile']
    boxes = json.loads(boxes_path.read_text(encoding='utf-8'))
    return manifest, boxes, manifest_path, boxes_path


def group_of_mesh(name):
    """Which release group a generated mesh belongs to. Mirrors create_water_geometry.py."""
    if 'Mikveh' in name:
        return 'mikvaot'
    if 'Stage' in name:
        return 'stages'
    return 'court'


def offline_check(spec=None):
    """Everything decidable without the engine. Run this before the commandlet, every time."""
    report = {'checkedUtc': datetime.now(timezone.utc).isoformat(), 'errors': [], 'warnings': []}
    try:
        spec = spec or load_spec()
    except Exception as error:  # noqa: BLE001
        report['errors'].append('spec: %r' % error)
        return report
    report['spec'] = str(SPEC_PATH)
    report['specSha256'] = sha256_of(SPEC_PATH)

    # -- geometry manifest ---------------------------------------------------------
    try:
        manifest, boxes, manifest_path, boxes_path = load_geometry(spec)
    except Exception as error:  # noqa: BLE001
        report['errors'].append('geometry manifest: %r' % error)
        return report
    report['geometryManifest'] = str(manifest_path)
    report['geometryManifestSha256'] = sha256_of(manifest_path)
    report['geometryStatus'] = manifest.get('status')
    if manifest.get('status') != spec['source']['manifestStatusRequired']:
        report['errors'].append('geometry manifest status is %r, required %r (a --force export is not releasable)'
                                % (manifest.get('status'), spec['source']['manifestStatusRequired']))
    if manifest.get('anchorErrors'):
        report['errors'].append('geometry manifest records anchor errors: %s' % manifest['anchorErrors'][:3])
    if not (manifest.get('runtimeHeaderCheck') or {}).get('constantsMatched'):
        report['errors'].append('geometry manifest records a WaterFlowMath.h constant mismatch')
    clearance = manifest.get('clearance') or {}
    report['offlineClearance'] = {
        'blockers': len(clearance.get('blockers') or []),
        'hosts': [h['mesh'] for h in clearance.get('hosts') or []],
        'wholePartAabbHits': clearance.get('wholePartAabbHits'),
        'subBoxHits': clearance.get('subBoxHits'),
        'falsePositivesEliminated': clearance.get('falsePositivesEliminated'),
        'namedClearancesCm': clearance.get('namedClearancesCm'),
    }
    if clearance.get('blockers'):
        report['errors'].append('geometry manifest records %d clearance blockers' % len(clearance['blockers']))

    # -- the frozen OBJs -----------------------------------------------------------
    folder = ROOT / spec['source']['folder']
    meshes, total = [], 0
    for record in manifest['meshes']:
        path = folder / 'obj' / record['file']
        row = {'name': record['name'], 'file': record['file'], 'group': group_of_mesh(record['name']),
               'role': record['materialRole'], 'triangles': record['triangles'],
               'exists': path.exists()}
        if not path.exists():
            report['errors'].append('missing OBJ: ' + str(path))
        else:
            row['sha256Matches'] = sha256_of(path) == record['sha256']
            if not row['sha256Matches']:
                report['errors'].append('OBJ hash changed since the manifest was written: ' + record['file'])
        if record['minimumPartSignedVolumeCm3'] <= 0.0:
            report['errors'].append('%s has a non-positive part signed volume; winding is wrong' % record['name'])
        total += record['triangles']
        meshes.append(row)
    report['meshes'] = meshes
    report['totalTriangles'] = total
    if total > spec['source']['maxTotalTriangles']:
        report['errors'].append('triangle budget exceeded: %d > %d' % (total, spec['source']['maxTotalTriangles']))

    # -- the clearance boxes -------------------------------------------------------
    report['clearanceBoxes'] = boxes.get('count')
    if sha256_of(boxes_path) != manifest['clearanceBoxesSha256']:
        report['errors'].append('clearance-boxes.json hash differs from the manifest')
    if not boxes.get('boxes'):
        report['errors'].append('clearance-boxes.json carries no boxes; the narrow phase would be vacuous')

    # -- the runtime contract ------------------------------------------------------
    # Every material parameter this release wires must be a name AMikdashWater actually
    # pushes. A mismatch is invisible at run time: SetScalarParameterValue against a name the
    # material does not have is not an error, it does nothing, and the water just sits still.
    header_path = ROOT / spec['runtime']['actorHeader']
    contract = {'header': spec['runtime']['actorHeader'], 'exists': header_path.exists()}
    if not header_path.exists():
        report['errors'].append('AMikdashWater header missing: ' + str(header_path))
    else:
        text = header_path.read_text(encoding='utf-8')
        missing = [p for p in spec['materials']['water']['scalarParameters'] if ('"%s"' % p) not in text]
        contract['parametersDeclaredInHeader'] = [p for p in spec['materials']['water']['scalarParameters']
                                                  if ('"%s"' % p) in text]
        contract['parametersMissingFromHeader'] = missing
        contract['classDeclared'] = 'class MIKDASHRUNTIME_API AMikdashWater' in text
        if missing:
            report['errors'].append('material parameters not declared in MikdashWater.h: %s' % missing)
        if not contract['classDeclared']:
            report['errors'].append('AMikdashWater is not declared in ' + spec['runtime']['actorHeader'])
        if spec['runtime']['surfaceTag'] not in text:
            report['errors'].append('surface tag %r does not appear in MikdashWater.h'
                                    % spec['runtime']['surfaceTag'])
    source_path = ROOT / spec['runtime']['actorSource']
    contract['sourceExists'] = source_path.exists()
    if not source_path.exists():
        report['errors'].append('AMikdashWater source missing: ' + str(source_path))
    report['runtimeContract'] = contract

    # -- the live-identification self-test -----------------------------------------
    try:
        arch = json.loads((ROOT / spec['clearance']['architectureManifest']).read_text(encoding='utf-8'))
        selftest = self_test_classification(arch, spec)
    except Exception as error:  # noqa: BLE001
        selftest = {'ok': False, 'failures': ['self-test could not run: %r' % error], 'cases': {}}
    report['liveIdentificationSelfTest'] = selftest
    if not selftest['ok']:
        report['errors'].append('live identification self-test failed: %s' % selftest['failures'][:4])

    # -- the sources record --------------------------------------------------------
    sources = ROOT / spec['sourcesRecord']
    report['sourcesRecord'] = {'path': spec['sourcesRecord'], 'exists': sources.exists()}
    if not sources.exists():
        report['errors'].append('sources.md missing; every header in this feature cites it')

    # -- the map -------------------------------------------------------------------
    map_file = disk_path(TARGET, 'umap')
    report['targetMapExists'] = map_file.exists()
    if not map_file.exists():
        report['errors'].append('target map missing: ' + str(map_file))
    else:
        report['targetMapSha256'] = sha256_of(map_file)
        report['targetMapMatchesLastKnown'] = report['targetMapSha256'] == spec.get('lastKnownMapSha256')

    report['ok'] = not report['errors']
    return report


# --------------------------------------------------------------------------
# Engine side
# --------------------------------------------------------------------------

class OmissionError(RuntimeError):
    """A group that cannot be placed, with numeric evidence. Never a silent skip."""

    def __init__(self, message, evidence=None):
        super().__init__(message)
        self.evidence = evidence or {}


def _xyz(v):
    return [float(v.x), float(v.y), float(v.z)]


def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def _static_mesh_box(mesh):
    box = mesh.get_bounding_box()
    return box_from_min_max([box.min.x, box.min.y, box.min.z], [box.max.x, box.max.y, box.max.z])


def _actor_bounds(actor):
    origin, extent = actor.get_actor_bounds(False)
    return box_from_min_max([origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
                            [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z])


def _actor_pose(actor):
    r = actor.get_actor_rotation()
    return {'location': _xyz(actor.get_actor_location()),
            'rotation': [float(r.pitch), float(r.yaw), float(r.roll)],
            'scale': _xyz(actor.get_actor_scale3d())}


class Graph:
    """Node builder bound to one UMaterial, with the pin-name traps handled once.

    THE PIN-NAME TRAP. UE 5.8 exposes several single-input nodes whose input is NOT the empty
    string: Desaturation's and Clamp's first inputs both report as 'None'. A wrong pin name is
    not an exception -- connect_material_expressions simply returns False -- and the setters
    can also return False on a connection that DID take. So wire() tries the plausible names
    in order, records which one worked, and raises with the node's actual input names if none
    did. Nothing here trusts a return value: _verify() reads the graph back off the saved
    asset and that readback is what decides pass or fail.
    """

    CANDIDATE_FIRST_INPUTS = ('', 'None', 'Input', 'A')

    def __init__(self, ue, material, record):
        self.ue = ue
        self.ml = ue.MaterialEditingLibrary
        self.material = material
        self.record = record

    def node(self, cls_name, x, y, **props):
        cls = getattr(self.ue, cls_name, None)
        if cls is None:
            raise RuntimeError('Material expression class not exposed to Python: ' + cls_name)
        expression = self.ml.create_material_expression(self.material, cls, x, y)
        if expression is None:
            raise RuntimeError('create_material_expression failed for ' + cls_name)
        for key, value in props.items():
            expression.set_editor_property(key, value)
        self.record['nodes'].append({'class': cls_name, 'position': [x, y]})
        return expression

    def const(self, value, x, y):
        return self.node('MaterialExpressionConstant', x, y, r=float(value))

    def colour(self, rgb, x, y):
        return self.node('MaterialExpressionConstant3Vector', x, y,
                         constant=self.ue.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))

    def scalar(self, name, value, x, y):
        return self.node('MaterialExpressionScalarParameter', x, y,
                         parameter_name=name, default_value=float(value))

    def vector(self, name, rgb, x, y):
        return self.node('MaterialExpressionVectorParameter', x, y, parameter_name=name,
                         default_value=self.ue.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0))

    def input_names(self, target):
        try:
            return [str(n) for n in self.ml.get_material_expression_input_names(target)]
        except Exception:  # noqa: BLE001
            return []

    def wire(self, source, target, input_name=None, output=''):
        """Connect, trying the documented pin-name variants when input_name is None."""
        names = [input_name] if input_name is not None else list(self.CANDIDATE_FIRST_INPUTS)
        for name in names:
            if self.ml.connect_material_expressions(source, output, target, name):
                self.record['connections'].append('%s -> %s.%r' % (
                    source.get_class().get_name(), target.get_class().get_name(), name))
                return name
        raise RuntimeError('Connection %s -> %s failed for %r; the node reports inputs %s' % (
            source.get_class().get_name(), target.get_class().get_name(), names,
            self.input_names(target)))

    def to_property(self, source, prop_name, output=''):
        prop = getattr(self.ue.MaterialProperty, prop_name, None)
        if prop is None:
            raise RuntimeError('MaterialProperty not exposed: ' + prop_name)
        # The return value is RECORDED, never trusted: UE 5.8 reports False on connections
        # that took. _verify() reads the property back off the saved material instead.
        returned = bool(self.ml.connect_material_property(source, output, prop))
        self.record.setdefault('propertyConnectReturned', {})[prop_name] = returned
        self.record['connections'].append('%s -> %s' % (source.get_class().get_name(), prop_name))


class WaterRelease:
    """Engine handles, the scene snapshot and the receipt for one release run."""

    def __init__(self, ue, spec):
        self.ue = ue
        self.spec = spec
        self.ml = ue.MaterialEditingLibrary
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.world = None
        self.snapshot = None
        self.receipt = None
        self.receipt_path = None

    # -- receipt ---------------------------------------------------------------

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n',
                                     encoding='utf-8')

    # -- scene -----------------------------------------------------------------

    def take_snapshot(self):
        ue = self.ue
        rows = []
        for actor in self.actors.get_all_level_actors():
            meshes = []
            for component in actor.get_components_by_class(ue.StaticMeshComponent):
                meshes.append(_asset_path(component.get_editor_property('static_mesh')))
            rows.append({'actor': actor, 'name': actor.get_name(), 'label': actor.get_actor_label(),
                         'folder': str(actor.get_folder_path()), 'meshes': meshes,
                         'pose': _actor_pose(actor), 'bounds': _actor_bounds(actor)})
        self.snapshot = rows
        return rows

    def numeric_baseline(self, rows):
        return {row['name']: (row['label'], tuple(m or '' for m in row['meshes']),
                              tuple(row['pose']['location'] + row['pose']['rotation'] + row['pose']['scale']))
                for row in rows}

    # -- materials -------------------------------------------------------------

    def pick_existing(self, role):
        """First candidate that exists and loads as a MaterialInterface, or None."""
        tried = []
        for position, candidate in enumerate(self.spec['materials'][role].get('candidates') or []):
            exists = self.assets.does_asset_exist(candidate['path'])
            asset = self.ue.load_asset(candidate['path']) if exists else None
            ok = isinstance(asset, self.ue.MaterialInterface)
            tried.append({'path': candidate['path'], 'kind': candidate['kind'],
                          'exists': bool(exists), 'loaded': ok})
            if ok:
                return asset, tried, position
        return None, tried, -1

    def pick_texture(self, role, key):
        for candidate in self.spec['materials'][role].get(key) or []:
            if self.assets.does_asset_exist(candidate['path']):
                asset = self.ue.load_asset(candidate['path'])
                if isinstance(asset, self.ue.Texture2D):
                    return asset, candidate
        return None, None

    def new_material(self, path, record):
        ue = self.ue
        if self.assets.does_asset_exist(path):
            # The failed run of 2026-09-08 saved this material before refusing. Reusing it and
            # wiring again would stack a second copy of every node and parameter onto the
            # first; the graph is rebuilt from nothing instead, and the receipt says so.
            asset = ue.load_asset(path)
            if not isinstance(asset, ue.Material):
                raise RuntimeError('Existing asset at the material path is not a Material: ' + path)
            # Cleared in place rather than deleted: the meshes saved by the earlier run still
            # reference this asset, and a force-delete would null those references.
            self.ml.delete_all_material_expressions(asset)
            remaining = len(asset.get_editor_property('expressions')) if hasattr(asset, 'get_editor_property') else -1
            record['replacedExisting'] = True
            record['expressionsRemainingAfterClear'] = remaining
            if remaining not in (0, -1):
                raise RuntimeError('%d expressions survived delete_all_material_expressions on %s' % (remaining, path))
            self.receipt['limitations'].append('%s existed from an earlier run; its graph was cleared and rebuilt' % path)
            return asset
        folder, name = path.rsplit('/', 1)
        material = ue.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, ue.Material, ue.MaterialFactoryNew())
        if not isinstance(material, ue.Material):
            raise RuntimeError('Material factory failed for ' + path)
        record['reusedExisting'] = False
        return material

    def build_water_material(self):
        """Flowing translucent water, driven entirely by AMikdashWater's scalar parameters.

        BaseColor  depth-lerped between a shallow and a deep colour, then lerped toward foam
                   white by max(bank-edge mask, the Froude foam term).
        Normal     one or two scrolling samples of a tiling normal map; the scroll offset in
                   tiles comes from the actor, which computes it from the Manning velocity, so
                   the surface moves at the speed the hydraulics say it moves.
        Opacity    the actor's depth-derived ramp: a trickle is nearly clear, the river is not.
        Specular   full; Roughness lerped from glassy to broken by the same foam term.
        Refraction an IOR constant, so what is under the water bends.
        Emissive   a faint shimmer keyed to the scrolling normal and masked to SHALLOW water.
                   This is a cheap stand-in that READS as caustics on the bed; it is not
                   projected caustics, and it is recorded as authored in sources.md terms.
        """
        ue = self.ue
        cfg = self.spec['materials']['water']
        record = {'asset': cfg['path'], 'nodes': [], 'connections': [], 'kind': 'water_translucent',
                  'status': 'started'}
        self.receipt['materials']['water'] = record
        material = self.new_material(cfg['path'], record)
        g = Graph(ue, material, record)
        c = cfg['constants']

        material.set_editor_property('blend_mode', ue.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property('two_sided', bool(cfg['twoSided']))
        for prop, enum_name, value in cfg.get('enumProperties') or []:
            enum_cls = getattr(ue, enum_name, None)
            member = getattr(enum_cls, value, None) if enum_cls else None
            if member is not None:
                try:
                    material.set_editor_property(prop, member)
                    record.setdefault('enumPropertiesSet', {})[prop] = value
                except Exception as error:  # noqa: BLE001 - optional, recorded either way
                    record.setdefault('enumPropertiesSkipped', {})[prop] = repr(error)
            else:
                record.setdefault('enumPropertiesSkipped', {})[prop] = 'enum member not exposed'

        # -- the scrolling UV ---------------------------------------------------
        scroll = g.scalar('WaterScrollTiles', 0.0, -1500, -600)
        zero = g.const(0.0, -1500, -500)
        offset = g.node('MaterialExpressionAppendVector', -1300, -560)
        g.wire(scroll, offset, 'A')
        g.wire(zero, offset, 'B')
        uv = g.node('MaterialExpressionTextureCoordinate', -1500, -400,
                    coordinate_index=0, u_tiling=float(c['uvTiling']), v_tiling=float(c['uvTiling']))
        scrolled = g.node('MaterialExpressionAdd', -1100, -480)
        g.wire(uv, scrolled, 'A')
        g.wire(offset, scrolled, 'B')

        # -- normal -------------------------------------------------------------
        normal_texture, chosen = self.pick_texture('water', 'normalCandidates')
        record['normalTexture'] = chosen['path'] if chosen else None
        record['normalTextureNote'] = (chosen['kind'] if chosen else
                                       'no candidate normal map on disk; a flat normal is used and the '
                                       'water reads as glass rather than as ripple. Add a tiling water '
                                       'normal to the spec candidates and re-run to fix.')
        if normal_texture is not None:
            sample = g.node('MaterialExpressionTextureSampleParameter2D', -800, -480,
                            parameter_name='WaterNormalMap', texture=normal_texture,
                            sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            g.wire(scrolled, sample, 'UVs')     # the UV pin on a TextureSampleParameter2D is 'UVs'
            # A second, faster and finer layer so the surface does not read as one sliding sheet.
            fine_scale = g.const(float(c['secondLayerTiling']), -1100, -260)
            fine_uv = g.node('MaterialExpressionMultiply', -950, -300)
            g.wire(scrolled, fine_uv, 'A')
            g.wire(fine_scale, fine_uv, 'B')
            fine = g.node('MaterialExpressionTextureSampleParameter2D', -800, -220,
                          parameter_name='WaterNormalMapFine', texture=normal_texture,
                          sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            g.wire(fine_uv, fine, 'UVs')
            blended = g.node('MaterialExpressionAdd', -520, -360)
            g.wire(sample, blended, 'A')
            g.wire(fine, blended, 'B')
            half = g.const(0.5, -700, -120)
            normal_out = g.node('MaterialExpressionMultiply', -340, -360)
            g.wire(blended, normal_out, 'A')
            g.wire(half, normal_out, 'B')
            record['normalLayers'] = 2
            shimmer_source = sample
        else:
            normal_out = g.colour([0.0, 0.0, 1.0], -340, -360)
            record['normalLayers'] = 0
            shimmer_source = None
        g.to_property(normal_out, 'MP_NORMAL')

        # -- depth colour -------------------------------------------------------
        depth = g.scalar('WaterDepth', 0.0, -1500, 100)
        full_depth = g.const(float(c['opacityFullDepthCm']), -1500, 200)
        depth_ratio = g.node('MaterialExpressionDivide', -1300, 140)
        g.wire(depth, depth_ratio, 'A')
        g.wire(full_depth, depth_ratio, 'B')
        lo = g.const(0.0, -1300, 260)
        hi = g.const(1.0, -1300, 340)
        depth_clamped = g.node('MaterialExpressionClamp', -1100, 200)
        g.wire(depth_ratio, depth_clamped)      # Clamp's first input reports as 'None'
        g.wire(lo, depth_clamped, 'Min')
        g.wire(hi, depth_clamped, 'Max')

        shallow = g.vector('WaterShallowColor', c['shallowColor'], -1100, 420)
        deep = g.vector('WaterDeepColor', c['deepColor'], -1100, 520)
        water_colour = g.node('MaterialExpressionLinearInterpolate', -800, 460)
        g.wire(shallow, water_colour, 'A')
        g.wire(deep, water_colour, 'B')
        g.wire(depth_clamped, water_colour, 'Alpha')

        # -- foam: at the banks always, and everywhere the flow goes supercritical
        v_coord = g.node('MaterialExpressionComponentMask', -1500, 700, r=False, g=True, b=False, a=False)
        g.wire(uv, v_coord)
        centre = g.const(0.5, -1500, 800)
        from_centre = g.node('MaterialExpressionSubtract', -1300, 720)
        g.wire(v_coord, from_centre, 'A')
        g.wire(centre, from_centre, 'B')
        abs_centre = g.node('MaterialExpressionAbs', -1150, 720)
        g.wire(from_centre, abs_centre)
        # |v-0.5| is 0 mid-channel and 0.5 at each bank; * 2 makes it a clean 0..1 bank mask.
        two = g.const(2.0, -1300, 860)
        bank_mask = g.node('MaterialExpressionMultiply', -980, 760)
        g.wire(abs_centre, bank_mask, 'A')
        g.wire(two, bank_mask, 'B')
        bank_strength = g.const(float(c['bankFoam']), -980, 880)
        bank_foam = g.node('MaterialExpressionMultiply', -820, 800)
        g.wire(bank_mask, bank_foam, 'A')
        g.wire(bank_strength, bank_foam, 'B')

        froude_foam = g.scalar('WaterFoam', 0.0, -980, 980)
        foam = g.node('MaterialExpressionMax', -640, 860)
        g.wire(bank_foam, foam, 'A')
        g.wire(froude_foam, foam, 'B')

        foam_colour = g.vector('WaterFoamColor', c['foamColor'], -640, 620)
        surface_colour = g.node('MaterialExpressionLinearInterpolate', -360, 560)
        g.wire(water_colour, surface_colour, 'A')
        g.wire(foam_colour, surface_colour, 'B')
        g.wire(foam, surface_colour, 'Alpha')
        g.to_property(surface_colour, 'MP_BASE_COLOR')

        # -- opacity, roughness, specular, metallic, refraction -----------------
        opacity = g.scalar('WaterOpacity', 0.0, -1500, 1100)
        min_opacity = g.const(float(c['minimumOpacity']), -1500, 1180)
        opacity_floor = g.node('MaterialExpressionMax', -1200, 1120)
        g.wire(opacity, opacity_floor, 'A')
        g.wire(min_opacity, opacity_floor, 'B')
        # Foam is opaque even where the water under it is not: a standing wave reads wrong
        # if you can see the bed through the white.
        opacity_final = g.node('MaterialExpressionMax', -900, 1120)
        g.wire(opacity_floor, opacity_final, 'A')
        g.wire(foam, opacity_final, 'B')
        g.to_property(opacity_final, 'MP_OPACITY')

        glassy = g.const(float(c['roughnessGlassy']), -900, 1280)
        broken = g.const(float(c['roughnessFoam']), -900, 1360)
        roughness = g.node('MaterialExpressionLinearInterpolate', -640, 1300)
        g.wire(glassy, roughness, 'A')
        g.wire(broken, roughness, 'B')
        g.wire(foam, roughness, 'Alpha')
        g.to_property(roughness, 'MP_ROUGHNESS')

        g.to_property(g.const(float(c['specular']), -640, 1440), 'MP_SPECULAR')
        g.to_property(g.const(0.0, -640, 1520), 'MP_METALLIC')
        refraction = g.scalar('WaterIOR', float(c['indexOfRefraction']), -640, 1600)
        try:
            g.to_property(refraction, 'MP_REFRACTION')
            record['refractionConnected'] = True
        except Exception as error:  # noqa: BLE001 - refraction is optional, not silent
            record['refractionConnected'] = False
            record['refractionNote'] = repr(error)

        # -- surface level and ripple, as world position offset -----------------
        # These two are the reason the actor has a level and a ripple at all. Pushed into a
        # scalar that nothing reads they would be inert; driven through WorldPositionOffset
        # they raise the free surface during a demonstration and let a footfall disturb it.
        rise = g.scalar('WaterSurfaceRise', 0.0, -900, 1900)
        ripple = g.scalar('WaterRipple', 0.0, -900, 1980)
        lift = g.node('MaterialExpressionAdd', -700, 1940)
        g.wire(rise, lift, 'A')
        g.wire(ripple, lift, 'B')
        up = g.colour([0.0, 0.0, 1.0], -700, 2060)
        offset_z = g.node('MaterialExpressionMultiply', -500, 1980)
        g.wire(up, offset_z, 'A')
        g.wire(lift, offset_z, 'B')
        g.to_property(offset_z, 'MP_WORLD_POSITION_OFFSET')

        # -- the cheap caustic shimmer -----------------------------------------
        if shimmer_source is not None and c.get('causticStrength', 0.0) > 0.0:
            bright = g.node('MaterialExpressionComponentMask', -520, 1720,
                            r=False, g=False, b=True, a=False)
            g.wire(shimmer_source, bright)
            shallow_mask = g.node('MaterialExpressionOneMinus', -520, 1820)
            g.wire(depth_clamped, shallow_mask)
            masked = g.node('MaterialExpressionMultiply', -340, 1760)
            g.wire(bright, masked, 'A')
            g.wire(shallow_mask, masked, 'B')
            strength = g.vector('WaterCausticTint', c['causticTint'], -340, 1880)
            caustic = g.node('MaterialExpressionMultiply', -160, 1800)
            g.wire(masked, caustic, 'A')
            g.wire(strength, caustic, 'B')
            g.to_property(caustic, 'MP_EMISSIVE_COLOR')
            record['caustics'] = ('shimmer keyed to the scrolling normal, masked to shallow water; '
                                 'a cheap stand-in that reads as caustics, NOT projected caustics')
        else:
            record['caustics'] = 'omitted: no normal texture to key the shimmer to'

        self.ml.recompile_material(material)
        if not self.assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + cfg['path'])
        self._verify_material(material, cfg, record)
        record['status'] = 'saved'
        self.write_receipt()
        return material

    def build_channel_material(self):
        """The masonry of the channel, its kerbs, the mikveh basins and the measuring marks.

        Reuses an existing project stone material when one is on disk -- the channel is cut
        into the same paving as everything else and should not read as a different stone --
        and only creates a constant material when nothing suitable exists.
        """
        ue = self.ue
        cfg = self.spec['materials']['stone']
        existing, tried, position = self.pick_existing('stone')
        record = {'asset': None, 'nodes': [], 'connections': [], 'kind': 'stone', 'tried': tried,
                  'status': 'started'}
        self.receipt['materials']['stone'] = record
        if existing is not None:
            record['asset'] = _asset_path(existing)
            record['created'] = False
            record['status'] = 'reused_existing'
            if position > 0:
                self.receipt['limitations'].append(
                    'the channel masonry fell past the first stone candidate to %s' % record['asset'])
            return existing
        record['asset'] = cfg['createPath']
        record['created'] = True
        material = self.new_material(cfg['createPath'], record)
        g = Graph(ue, material, record)
        c = cfg['constants']
        g.to_property(g.colour(c['baseColor'], -400, 0), 'MP_BASE_COLOR')
        g.to_property(g.const(c['metallic'], -400, 200), 'MP_METALLIC')
        g.to_property(g.const(c['roughness'], -400, 300), 'MP_ROUGHNESS')
        self.ml.recompile_material(material)
        if not self.assets.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + cfg['createPath'])
        self._verify_material(material, cfg, record)
        record['status'] = 'saved'
        self.write_receipt()
        return material

    def _verify_material(self, material, cfg, record):
        """Read the graph back off the SAVED asset. This, not any setter, decides pass/fail."""
        ue = self.ue
        reloaded = ue.load_asset(_asset_path(material))
        if not isinstance(reloaded, ue.Material):
            raise RuntimeError('Saved material did not reload: ' + _asset_path(material))
        wired = {}
        for prop_name in cfg['verifyProperties']:
            prop = getattr(ue.MaterialProperty, prop_name, None)
            if prop is None:
                wired[prop_name] = 'property_not_exposed'
                continue
            node = self.ml.get_material_property_input_node(reloaded, prop)
            wired[prop_name] = node.get_class().get_name() if node else None
        record['savedInputReadback'] = wired
        missing = [p for p in cfg['requireConnected'] if not wired.get(p)]
        if missing:
            raise RuntimeError('%s: these material inputs did not read back as connected: %s (%r)'
                               % (_asset_path(material), missing, wired))
        record['blendMode'] = str(reloaded.get_editor_property('blend_mode'))
        record['twoSided'] = bool(reloaded.get_editor_property('two_sided'))
        record['uassetSha256'] = sha256_of(disk_path(_asset_path(material)))
        # Scalar parameters actually present on the compiled material, by name. This is the
        # proof that AMikdashWater's pushes will land on something.
        try:
            names = [str(n) for n in ue.MaterialEditingLibrary.get_scalar_parameter_names(reloaded)]
        except Exception:  # noqa: BLE001
            names = []
        record['scalarParameterNames'] = names
        if cfg.get('requiredScalarParameters') and names:
            absent = [p for p in cfg['requiredScalarParameters'] if p not in names]
            record['scalarParametersAbsent'] = absent
            if absent:
                raise RuntimeError('%s does not expose the parameters AMikdashWater pushes: %s'
                                   % (_asset_path(material), absent))
        return record

    # -- import ----------------------------------------------------------------

    def import_mesh(self, mesh_record, material):
        ue = self.ue
        source, settings = self.spec['source'], self.spec['importSettings']
        path = ROOT / source['folder'] / 'obj' / mesh_record['file']
        if sha256_of(path) != mesh_record['sha256']:
            raise RuntimeError('Frozen OBJ hash changed: ' + mesh_record['file'])
        ui = ue.FbxImportUI()
        for key, value in settings['fbxImportUI'].items():
            if key == 'mesh_type_to_import':
                value = getattr(ue.FBXImportType, value)
            ui.set_editor_property(key, value)
        data = ui.get_editor_property('static_mesh_import_data')
        for key, value in settings['staticMeshImportData'].items():
            if key == 'normal_import_method':
                value = getattr(ue.FBXNormalImportMethod, value)
            data.set_editor_property(key, value)
        task = ue.AssetImportTask()
        for key, value in dict(filename=str(path), destination_path=source['meshFolder'],
                               destination_name=mesh_record['name'], automated=True, async_=False,
                               replace_existing=True, save=False, options=ui,
                               factory=ue.FbxFactory()).items():
            task.set_editor_property(key, value)
        ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        objects = list(task.get_objects())
        if len(objects) != 1 or not isinstance(objects[0], ue.StaticMesh):
            raise RuntimeError('Import of %s produced %s'
                               % (mesh_record['file'], [type(o).__name__ for o in objects]))
        mesh = objects[0]

        box = _static_mesh_box(mesh)
        canonical = mesh_record['canonicalBoundsCm']
        error = box_error(box, canonical)
        # If the importer had NOT reflected Y back, the bounds would match this instead. Both
        # numbers go in the receipt so a future reader can tell a passing import from an
        # ambiguous one (a mesh symmetric about Y matches either way and proves nothing).
        plain = {'min': [canonical['min'][0], -canonical['max'][1], canonical['min'][2]],
                 'max': [canonical['max'][0], -canonical['min'][1], canonical['max'][2]]}
        error_unreflected = box_error(box, plain)
        tolerance = self.spec['source']['boundsToleranceCm']
        if error > tolerance:
            raise RuntimeError('%s imported bounds differ from canonical by %.4f cm (unreflected %.4f): %r'
                               % (mesh_record['name'], error, error_unreflected, box))
        triangles = mesh.get_num_triangles(0)
        if triangles != mesh_record['triangles']:
            raise RuntimeError('%s imported %d triangles, manifest says %d'
                               % (mesh_record['name'], triangles, mesh_record['triangles']))

        slots = len(mesh.get_editor_property('static_materials'))
        for slot in range(slots):
            mesh.set_material(slot, material)
        wrong = [s for s in range(slots) if _asset_path(mesh.get_material(s)) != _asset_path(material)]
        if slots == 0 or wrong:
            raise RuntimeError('Material slots not assigned on %s: %s of %d'
                               % (mesh_record['name'], wrong, slots))
        if not self.assets.save_loaded_asset(mesh, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed for ' + mesh_record['name'])
        return mesh, {'asset': _asset_path(mesh), 'name': mesh_record['name'],
                      'group': group_of_mesh(mesh_record['name']), 'role': mesh_record['materialRole'],
                      'triangles': triangles, 'vertices': mesh.get_num_vertices(0),
                      'localBoundsCm': box, 'boundsErrorCm': error,
                      'boundsErrorIfImporterHadNotReflectedY': error_unreflected,
                      'importerReflectedYAsExpected': error <= tolerance,
                      'ambiguousReflection': error_unreflected <= tolerance,
                      'materialSlots': slots, 'material': _asset_path(material),
                      'uassetSha256': sha256_of(disk_path(_asset_path(mesh)))}

    # -- clearance against the live level --------------------------------------

    def live_clearance(self, boxes, placed_labels):
        """Narrow-phase clearance of the generated sub-boxes against every other level actor.

        See the module docstring: three separate classes of enclosing AABB in this level make
        a raw bounds test worthless. Actors are identified by their MESH ASSET NAME, never by
        their editor label -- labels are user-editable and need not match the manifest, and a
        lookup that silently misses would turn a real blocker into a harmless-looking note.
        """
        spec = self.spec['clearance']
        arch = json.loads((ROOT / spec['architectureManifest']).read_text(encoding='utf-8'))
        by_key = {manifest_key_for_asset(entry['assetName']): entry for entry in arch['meshes']}
        union_names = set(spec['hollowUnionSourceNames'])
        host_sources = set(spec['hostSourceNames'])

        sub_boxes = [dict(mesh=b['mesh'], part=b['part'],
                          box=box_from_min_max(b['min'], b['max'])) for b in boxes['boxes']]
        overall = box_from_min_max([min(b['box']['min'][i] for b in sub_boxes) for i in range(3)],
                                   [max(b['box']['max'][i] for b in sub_boxes) for i in range(3)])

        report = {'method': spec['method'], 'subBoxesTested': len(sub_boxes),
                  'generatedOverallBoundsCm': overall,
                  'terrainActorsExcluded': 0, 'unionsDecomposed': 0, 'unionsUndecomposable': [],
                  'actorsBroadPhaseHits': 0, 'actorsNarrowPhaseTested': 0, 'actorsSkippedOwn': 0,
                  'unmatchedActors': [], 'blockers': [], 'hosts': [], 'nearest': []}
        terrain_prefixes = tuple(spec['terrainMeshPrefixes'])

        for row in self.snapshot:
            if row['label'] in placed_labels:
                report['actorsSkippedOwn'] += 1
                continue
            assets = [m.rsplit('/', 1)[-1] for m in row['meshes'] if m]
            if any(a.startswith(terrain_prefixes) for a in assets):
                report['terrainActorsExcluded'] += 1
                continue
            if not boxes_overlap(row['bounds'], overall):
                continue
            report['actorsBroadPhaseHits'] += 1

            entry = manifest_entry_for_assets(assets, by_key)
            source_name = entry['sourceName'] if entry else None
            base_name = base_source_name(source_name) if source_name else None
            kind = classify_source(source_name, host_sources, union_names)
            candidate_boxes = [row['bounds']]
            if kind == 'union':
                decomposed = union_constituent_boxes(entry) if entry else None
                ok, error = verify_union_decomposition(entry, decomposed) if entry else (False, None)
                if ok:
                    candidate_boxes = decomposed
                    report['unionsDecomposed'] += 1
                else:
                    # NOT a blocker on its raw bounds: that is exactly the false positive this
                    # mechanism exists to prevent. Recorded loudly so it cannot be forgotten.
                    report['unionsUndecomposable'].append(
                        {'actor': row['label'], 'assets': assets, 'boundsErrorCm': error,
                         'note': 'hollow union could not be decomposed; its AABB encloses the site '
                                 'and was NOT used as a blocker. Inspect by eye.'})
                    continue
            elif entry is None:
                report['unmatchedActors'].append({'actor': row['label'], 'assets': assets})
                if any('_architecture_' in a or '_vessel_' in a for a in assets):
                    # An architecture mesh that does not resolve to the manifest means the
                    # identification path is broken again, and every classification below it
                    # is meaningless. Refuse rather than report a page of false blockers.
                    raise RuntimeError('architecture actor %r (%s) does not resolve to the manifest; '
                                       'see manifest_key_for_asset()' % (row['label'], assets))

            report['actorsNarrowPhaseTested'] += 1
            hits, nearest = [], None
            is_host = kind == 'host'
            for candidate in candidate_boxes:
                for sub in sub_boxes:
                    gap = separation_cm(sub['box'], candidate)
                    if nearest is None or gap < nearest[0]:
                        nearest = (gap, sub['mesh'], sub['part'])
                    if boxes_overlap(sub['box'], candidate):
                        hits.append({'part': sub['part'],
                                     'depthCm': round(overlap_depth(sub['box'], candidate), 3)})
            if nearest is not None and not hits:
                # Only genuinely separated actors: an actor the conduit is cut into contributes
                # 0.0 and would drown the clearances a reviewer actually wants to read.
                report['nearest'].append({'actor': row['label'], 'sourceName': source_name,
                                          'clearanceCm': round(nearest[0], 3),
                                          'nearestMesh': nearest[1], 'nearestPart': nearest[2]})
            if hits:
                entryrow = {'actor': row['label'], 'sourceName': source_name,
                            'baseSourceName': base_name, 'assets': assets, 'contacts': len(hits),
                            'deepestInterpenetrationCm': max(h['depthCm'] for h in hits)}
                # A HOST is paving, a platform, a stair or a threshold the conduit is by nature
                # cut into. The same list the offline export uses, so the two agree.
                target = report['hosts'] if is_host else report['blockers']
                target.append(entryrow)

        report['nearest'] = sorted(report['nearest'], key=lambda r: r['clearanceCm'])[:spec['reportNearest']]
        return report


# --------------------------------------------------------------------------

def release(load_target=True, groups=GROUP_ORDER, import_only=False, skip_actor=False):
    """Import, build materials, place, save, reopen, read back. Returns the receipt."""
    import unreal as ue
    groups = normalise_groups(groups)
    spec = load_spec()
    offline = offline_check(spec)
    if not offline['ok']:
        raise RuntimeError('offline check failed: %s' % offline['errors'][:5])
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())

    run = WaterRelease(ue, spec)
    if run.editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if load_target:
        if not run.levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
    run.world = run.editor.get_editor_world()
    loaded = run.world.get_outermost().get_name()
    if loaded != TARGET:
        raise RuntimeError('Loaded world %s is not the combined map %s' % (loaded, TARGET))
    if (ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Dirty packages present; resolve before checkpointed placement')

    manifest, boxes, manifest_path, boxes_path = load_geometry(spec)
    map_file = disk_path(TARGET, 'umap')
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(disk_path(m, 'umap')) for m in spec['protectedMaps']
                 if disk_path(m, 'umap').exists()}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')

    checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
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
    run.receipt_path = receipt_folder / (spec['receiptPrefix'] + stamp + '.json')
    if run.receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(run.receipt_path))
    run.receipt = {
        'status': 'water_release_started',
        'stamp': stamp,
        'map': TARGET,
        'mapFile': str(map_file),
        'mapSha256Before': map_sha_before,
        'checkpoint': str(checkpoint),
        'oneFilePerActorFoldersCopied': external_copied,
        'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH),
        'specSha256': sha256_of(SPEC_PATH),
        'geometryManifest': str(manifest_path),
        'geometryManifestSha256': sha256_of(manifest_path),
        'geometryStatus': manifest['status'],
        'offlineCheck': offline,
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'groupsRequested': list(groups),
        'importOnly': bool(import_only),
        'skipActor': bool(skip_actor),
        'sourcesRecord': spec['sourcesRecord'],
        'materials': {},
        'imported': [],
        'placed': [],
        'omissions': {},
        'errors': [],
        'mapSaved': False,
        'depicted': manifest.get('depicted'),
        'assertedNotDepicted': manifest.get('assertedNotDepicted'),
        'limitations': list(manifest.get('limitations') or []) + [
            'Geometry and material wiring only. No visual, walking, lighting, cook or halachic '
            'acceptance is established by this receipt.',
            'The four stages are built as LITERAL distances; the schematic reading is recorded in '
            'SourceAssets/water-review/sources.md and is not built.',
            'The route is disputed: the book (p. 340) takes the water out by the inner court SOUTH '
            'gate, the plain sense of 47:1-2 by the outer EAST gate. The east route is placed.',
            'Every width, depth, grade and mikveh dimension is AUTHORED. The prophet gives four '
            'depths as parts of a body and no widths at all.',
            'Terrain tiles are excluded from the live clearance test by name because a heightfield '
            'cannot be decomposed into boxes; the architecture-manifest clearance is the authority.',
        ],
    }
    run.write_receipt()

    saved = False
    try:
        run.take_snapshot()
        baseline = run.numeric_baseline(run.snapshot)
        pre_existing = [r for r in run.snapshot
                        if r['label'].startswith(spec['labelPrefix'])
                        or str(r['folder']).startswith(spec['folder'])]
        run.receipt['preExistingReleaseActors'] = [
            {'label': r['label'], 'folder': r['folder'], 'meshes': r['meshes'], 'bounds': r['bounds']}
            for r in pre_existing]
        if pre_existing:
            raise RuntimeError('Existing water release actors present; refusing duplicate placement: %s'
                               % [r['label'] for r in pre_existing][:10])

        water_material = run.build_water_material()
        stone_material = run.build_channel_material()

        wanted = [m for m in manifest['meshes'] if group_of_mesh(m['name']) in groups]
        imported = []
        for record in wanted:
            material = water_material if record['materialRole'] == 'water' else stone_material
            mesh, info = run.import_mesh(record, material)
            info['plannedWorldBoundsCm'] = record['canonicalBoundsCm']
            imported.append((mesh, record, info))
            run.receipt['imported'].append(info)
            run.write_receipt()

        if import_only:
            run.receipt['status'] = 'imported_only_map_unchanged'
            return run.receipt

        # -- place ------------------------------------------------------------
        # The OBJ vertices are already absolute world centimetres, so every actor is
        # spawned at the origin with an identity transform and its world bounds must equal
        # canonicalBoundsCm exactly. Any offset would be a silent re-siting of the stream.
        placed = []
        origin = ue.Vector(0.0, 0.0, 0.0)
        rotation = ue.Rotator(0.0, 0.0, 0.0)
        for mesh, record, info in imported:
            actor = run.actors.spawn_actor_from_class(ue.StaticMeshActor, origin, rotation)
            if actor is None:
                raise RuntimeError('spawn_actor_from_class failed for ' + record['name'])
            label = spec['labelPrefix'] + record['name'].replace('SM_MikdashWaterV1_', '')
            actor.set_actor_label(label)
            actor.set_folder_path(spec['folder'])
            component = actor.get_component_by_class(ue.StaticMeshComponent)
            # Mesh first, mobility second: assigning a static mesh to a component that is
            # already STATIC is the ordering the engine complains about.
            component.set_static_mesh(mesh)
            component.set_editor_property('mobility', ue.ComponentMobility.STATIC)
            component.set_collision_profile_name(
                spec['collisionProfile']['water'] if record['materialRole'] == 'water'
                else spec['collisionProfile']['stone'])
            tags = []
            if record['materialRole'] == 'water':
                tags.append(spec['runtime']['surfaceTag'])
            tags.append(spec['actorTag'])
            component.set_editor_property('component_tags', tags)
            actor.set_editor_property('tags', [spec['actorTag']])
            placed.append({'label': label, 'mesh': _asset_path(mesh), 'role': record['materialRole'],
                           'group': group_of_mesh(record['name']),
                           'componentTags': [str(t) for t in component.get_editor_property('component_tags')],
                           'plannedWorldBoundsCm': record['canonicalBoundsCm']})
            run.receipt['placed'] = placed
            run.write_receipt()

        # -- the driver actor --------------------------------------------------
        if not skip_actor:
            water_class = getattr(ue, 'MikdashWater', None)
            if water_class is None:
                water_class = ue.load_class(None, spec['runtime']['classPath'])
            if water_class is None:
                raise OmissionError(
                    'AMikdashWater is not registered. Rebuild the plugin before releasing, or pass '
                    '-WaterSkipActor to place the geometry without its driver.',
                    {'classPath': spec['runtime']['classPath']})
            driver = run.actors.spawn_actor_from_class(water_class, origin, rotation)
            if driver is None:
                raise RuntimeError('spawn_actor_from_class failed for AMikdashWater')
            driver.set_actor_label(spec['labelPrefix'] + 'Driver')
            driver.set_folder_path(spec['folder'])
            driver.set_editor_property('stream_mesh_tag', spec['runtime']['surfaceTag'])
            run.receipt['driver'] = {
                'label': driver.get_actor_label(),
                'class': driver.get_class().get_name(),
                'streamMeshTag': str(driver.get_editor_property('stream_mesh_tag')),
                'sampleDistanceAmot': float(driver.get_editor_property('sample_distance_amot')),
                'bedSlope': float(driver.get_editor_property('bed_slope')),
                'manningN': float(driver.get_editor_property('manning_n')),
            }
            run.write_receipt()

        # -- clearance against the live level ----------------------------------
        run.take_snapshot()
        placed_labels = {p['label'] for p in placed} | {spec['labelPrefix'] + 'Driver'}
        clearance = run.live_clearance(boxes, placed_labels)
        run.receipt['liveClearance'] = clearance
        run.write_receipt()
        if clearance['blockers']:
            raise RuntimeError('the placed water intersects %d non-host actors: %s'
                               % (len(clearance['blockers']),
                                  [b['actor'] for b in clearance['blockers']][:10]))

        current = run.numeric_baseline([r for r in run.snapshot if r['label'] not in placed_labels])
        changed = [name for name, row in baseline.items() if current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:10])

        # -- save, reopen, read back -------------------------------------------
        if not run.levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        run.receipt['mapSaved'] = True
        run.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        run.write_receipt()
        if not run.levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        run.world = run.editor.get_editor_world()
        reopened = run.take_snapshot()

        verify = spec['verification']
        readback = []
        for record in placed:
            matching = [r for r in reopened if r['label'] == record['label']]
            if len(matching) != 1:
                raise RuntimeError('Reopened actor count for %s is %d' % (record['label'], len(matching)))
            row = matching[0]
            if row['meshes'] != [record['mesh']]:
                raise RuntimeError('Reopened mesh differs for %s: %r' % (record['label'], row['meshes']))
            pose_error = max([abs(v) for v in row['pose']['location']]
                             + [abs(v) for v in row['pose']['rotation']]
                             + [abs(v - 1.0) for v in row['pose']['scale']])
            if pose_error > verify['transformToleranceCm']:
                raise RuntimeError('Reopened transform for %s is not identity at the origin (%.5f)'
                                   % (record['label'], pose_error))
            bounds_error = box_error(row['bounds'], record['plannedWorldBoundsCm'])
            if bounds_error > verify['staticBoundsToleranceCm']:
                raise RuntimeError('Reopened bounds for %s differ by %.4f cm'
                                   % (record['label'], bounds_error))
            component = matching[0]['actor'].get_component_by_class(ue.StaticMeshComponent)
            readback.append({'label': record['label'], 'folder': row['folder'],
                             'meshPath': row['meshes'], 'worldBoundsCm': row['bounds'],
                             'boundsErrorCm': bounds_error, 'poseErrorCm': pose_error,
                             'componentTags': [str(t) for t in component.get_editor_property('component_tags')],
                             'collisionProfile': str(component.get_collision_profile_name()),
                             'material': _asset_path(component.get_material(0))})
        run.receipt['reopenedReadback'] = readback

        if not skip_actor:
            drivers = [r for r in reopened if r['label'] == spec['labelPrefix'] + 'Driver']
            if len(drivers) != 1:
                raise RuntimeError('Driver actor count after reopen is %d' % len(drivers))
            driver = drivers[0]['actor']
            surfaces = [r for r in readback if spec['runtime']['surfaceTag'] in r['componentTags']]
            run.receipt['driverAfterReopen'] = {
                'class': driver.get_class().get_name(),
                'streamMeshTag': str(driver.get_editor_property('stream_mesh_tag')),
                'taggedSurfaceComponents': len(surfaces),
            }
            if str(driver.get_editor_property('stream_mesh_tag')) != spec['runtime']['surfaceTag']:
                raise RuntimeError('Driver stream_mesh_tag did not survive the reopen')
            if not surfaces:
                raise RuntimeError('No surface component carries %r after reopen; the driver would '
                                   'find nothing to drive' % spec['runtime']['surfaceTag'])

        run.receipt['status'] = 'water_saved_reopened_visual_and_runtime_acceptance_pending'
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
        run.receipt['placedActorCount'] = len(run.receipt.get('placed') or [])
        run.write_receipt()


# --------------------------------------------------------------------------
# The spec
# --------------------------------------------------------------------------

def write_spec():
    """Regenerate release_water.spec.json. Run offline after changing the geometry."""
    manifest = json.loads((ROOT / 'SourceAssets/water-review/MikdashWaterV1/geometry-manifest.json')
                          .read_text(encoding='utf-8'))
    map_file = disk_path(TARGET, 'umap')
    spec = {
        'specVersion': 'MikdashWaterV1-release-1',
        'prepared': datetime.now(timezone.utc).isoformat(),
        'purpose': ('Import, materialise, place and drive the stream of Yechezkel 47, its channel '
                    'through the courts and the four mikvaot. Every claim behind the geometry is in '
                    'SourceAssets/water-review/sources.md, marked certain / disputed / authored.'),
        'projectDir': str(ROOT),
        'targetMap': TARGET,
        'targetMapFile': str(map_file),
        'lastKnownMapSha256': sha256_of(map_file) if map_file.exists() else None,
        'lastKnownMapSha256Note': ('Recorded, never required: the map legitimately changes between '
                                   'releases. A mismatch is reported, not refused.'),
        'protectedMaps': ['/Game/MikdashV3/Maps/Courtyard',
                          '/Game/MikdashV3/FutureMountV1/L_FutureMount',
                          '/Game/MikdashV3/IntegratedReviewV1/Maps/Walkthrough'],
        'checkpointRoot': r'C:\Mikdash\Working-5.8\ReviewCheckpoints',
        'checkpointPrefix': 'Water-',
        'receiptFolder': 'SourceAssets/water-review',
        'receiptPrefix': 'native-release-water-',
        'sourcesRecord': 'SourceAssets/water-review/sources.md',
        'labelPrefix': 'RELEASE_Water_',
        'folder': 'Release/Water',
        'actorTag': 'ReleaseMikdashWaterV1',
        'collisionProfile': {
            'stone': 'BlockAll',
            'water': 'NoCollision',
            'note': ('The water ribbons must not block a walker: a visitor has to be able to step '
                     'into the stream. The masonry blocks normally.'),
        },
        'runtime': {
            'actorHeader': 'Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashWater.h',
            'actorSource': 'Plugins/MikdashRuntime/Source/MikdashRuntime/Private/MikdashWater.cpp',
            'mathHeader': 'Plugins/MikdashRuntime/Source/MikdashRuntime/Public/WaterFlowMath.h',
            'test': 'Plugins/MikdashRuntime/Tests/WaterFlowMathTest.cpp',
            'classPath': '/Script/MikdashRuntime.MikdashWater',
            'surfaceTag': 'MikdashWaterSurface',
            'note': ('The plugin MUST be rebuilt before the commandlet runs, or AMikdashWater is not '
                     'a registered class and the driver cannot be spawned. -WaterSkipActor places the '
                     'geometry without it.'),
        },
        'source': {
            'folder': 'SourceAssets/water-review/MikdashWaterV1',
            'authoringScript': 'Scripts/create_water_geometry.py',
            'authoringScriptSha256': manifest['scriptSha256'],
            'manifestStatusRequired': 'OFFLINE_VALIDATED_NATIVE_AND_VISUAL_PENDING',
            'namespace': '/Game/MikdashV3/MaterialReview/MikdashWaterV1',
            'meshFolder': '/Game/MikdashV3/MaterialReview/MikdashWaterV1/Meshes',
            'maxTotalTriangles': 250000,
            'boundsToleranceCm': 0.05,
            'objAdapter': manifest['objAdapter'],
        },
        'importSettings': {
            'note': ('Identical to the proven keilim / doors / reliefs OBJ adapter path (FbxFactory). '
                     'Single-mesh OBJ with named groups: destination_name is the exact mesh name and '
                     'combine_meshes merges the groups into one static mesh.'),
            'factory': 'FbxFactory',
            'fbxImportUI': {
                'automated_import_should_detect_type': False,
                'mesh_type_to_import': 'FBXIT_STATIC_MESH',
                'import_as_skeletal': False,
                'import_mesh': True,
                'import_animations': False,
                'import_materials': False,
                'import_textures': False,
                'create_physics_asset': False,
            },
            'staticMeshImportData': {
                'combine_meshes': True,
                'transform_vertex_to_absolute': True,
                'bake_pivot_in_vertex': False,
                'convert_scene': False,
                'convert_scene_unit': False,
                'force_front_x_axis': False,
                'import_uniform_scale': 1.0,
                'auto_generate_collision': False,
                'build_nanite': False,
                'generate_lightmap_u_vs': False,
                'remove_degenerates': True,
                'normal_import_method': 'FBXNIM_IMPORT_NORMALS',
            },
        },
        'materials': {
            'rule': ('Nothing trusts a setter or connect_material_property: UE 5.8 returns False on '
                     'connections that took. Pass or fail is decided by reading the graph back off '
                     'the SAVED asset, and by the compiled scalar parameter names.'),
            'water': {
                'path': '/Game/MikdashV3/MaterialReview/MikdashWaterV1/M_MikdashWaterV1_Water',
                'twoSided': True,
                'enumProperties': [
                    ['translucency_lighting_mode', 'TranslucencyLightingMode',
                     'TLM_SURFACE_PER_PIXEL_LIGHTING'],
                ],
                'normalCandidates': [
                    {'path': '/Game/MikdashV3/MaterialReview/MikdashWaterV1/Textures/T_Water_Normal',
                     'kind': ('authored tiling water normal (create_water_normal.py): 3 swell + 5 wind '
                              'trains + periodic ripple fBm, moderate amplitude; source '
                              'SourceAssets/water-review/textures/T_Water_Normal.png sha256 '
                              '6e29c0471a143057be1dbc39d8c6deba4706a08274c3fb593daec7a14d4ad54b')},
                    {'path': '/Game/MikdashV3/Materials/PBR/Plaster/T_Plaster_Normal',
                     'kind': ('fine isotropic normal used as a STAND-IN ripple map: this project has no '
                              'water normal. Recorded as a limitation; drop a tiling water normal in '
                              'and put it first in this list to replace it.')},
                    {'path': '/Game/MikdashV3/Materials/PBR/RoughStone/T_RoughStone_Normal',
                     'kind': 'coarser stand-in fallback'},
                    {'path': '/Game/MikdashV3/Materials/PBR/Marble/T_Marble_Normal',
                     'kind': 'last-resort stand-in fallback'},
                ],
                'scalarParameters': ['WaterFlowSpeed', 'WaterScrollTiles', 'WaterDepth',
                                     'WaterOpacity', 'WaterFoam', 'WaterFroude', 'WaterSurfaceRise',
                                     'WaterRipple', 'WaterStage', 'WaterDemoProgress'],
                'requiredScalarParameters': ['WaterScrollTiles', 'WaterDepth', 'WaterFoam',
                                             'WaterOpacity', 'WaterSurfaceRise', 'WaterRipple'],
                'scalarParametersNote': ('Every name in scalarParameters is declared in MikdashWater.h '
                                         'in the MikdashWaterParameters namespace, and offline_check() '
                                         'greps the header for all of them. The graph CONSUMES the six '
                                         'in requiredScalarParameters and the save is refused if any is '
                                         'missing from the compiled material. WaterFlowSpeed, '
                                         'WaterFroude, WaterStage and WaterDemoProgress are pushed by '
                                         'the actor but read by nothing in this graph: they are there '
                                         'for material instances and for HUD readouts, and pushing them '
                                         'is harmless. That is stated rather than hidden, because a '
                                         'parameter nothing reads looks identical to a misspelt one.'),
                'constants': {
                    'uvTiling': 1.0,
                    'secondLayerTiling': 2.7,
                    'opacityFullDepthCm': 120.0,
                    'shallowColor': [0.42, 0.62, 0.60],
                    'deepColor': [0.03, 0.13, 0.19],
                    'foamColor': [0.93, 0.96, 0.97],
                    'causticTint': [0.35, 0.45, 0.40],
                    'causticStrength': 1.0,
                    'bankFoam': 0.55,
                    'minimumOpacity': 0.05,
                    'roughnessGlassy': 0.03,
                    'roughnessFoam': 0.55,
                    'specular': 1.0,
                    'indexOfRefraction': 1.333,
                },
                'constantsNote': ('Colours are AUTHORED. Index of refraction 1.333 is water at 20 C. '
                                  'The opacity full depth of 120 cm matches OpacityFullDepthCm in '
                                  'WaterFlowMath.h.'),
                'verifyProperties': ['MP_BASE_COLOR', 'MP_OPACITY', 'MP_ROUGHNESS', 'MP_NORMAL',
                                     'MP_SPECULAR', 'MP_METALLIC', 'MP_REFRACTION',
                                     'MP_EMISSIVE_COLOR', 'MP_WORLD_POSITION_OFFSET'],
                'requireConnected': ['MP_BASE_COLOR', 'MP_OPACITY', 'MP_ROUGHNESS', 'MP_NORMAL',
                                     'MP_WORLD_POSITION_OFFSET'],
            },
            'stone': {
                'candidates': [
                    {'path': '/Game/MikdashV3/MaterialReview/JerusalemStoneV2/M_JerusalemStoneV2_PavingReview',
                     'kind': 'the reviewed paving stone: the channel is cut into this paving'},
                    {'path': '/Game/MikdashV3/MaterialReview/Canonical/Materials/M_Canonical_paving_5b05255363',
                     'kind': 'canonical paving fallback'},
                    {'path': '/Game/MikdashV3/MaterialReview/Canonical/Materials/M_Canonical_stone_60db7e17c6',
                     'kind': 'canonical stone fallback'},
                ],
                'createPath': '/Game/MikdashV3/MaterialReview/MikdashWaterV1/M_MikdashWaterV1_Channel',
                'constants': {'baseColor': [0.62, 0.58, 0.50], 'metallic': 0.0, 'roughness': 0.82},
                'verifyProperties': ['MP_BASE_COLOR', 'MP_METALLIC', 'MP_ROUGHNESS'],
                'requireConnected': ['MP_BASE_COLOR'],
            },
        },
        'clearance': {
            'architectureManifest': 'SourceAssets/architecture-manifest.json',
            'method': ('Broad phase on actor bounds, narrow phase on the 2307 published sub-boxes of '
                       'the generated geometry. Terrain tiles are excluded by mesh-name prefix; '
                       'hollow derived unions are decomposed into their constituent boxes and are '
                       'trusted only when the recomposed union reproduces their manifest bounds.'),
            'terrainMeshPrefixes': ['SM_JerusalemTerrain_', 'SM_MountPlatform_', 'SM_Jerusalem_CityWalls_'],
            'terrainNote': ('260 FutureMountV1 tiles span 400-800 m each and their AABBs enclose the '
                            'whole Temple. Tested raw they gave 100 per cent false blockers. A '
                            'heightfield cannot be decomposed into boxes, so they are excluded and '
                            'counted; clearance.json against the architecture manifest is the '
                            'authority for the built Temple.'),
            'hollowUnionSourceNames': HOLLOW_UNION_SOURCE_NAMES,
            'hostSourceNames': HOST_SOURCE_NAMES,
            'namesNote': ('Exact manifest sourceName values, copied from HOST_MESH_NAMES and '
                          'HOLLOW_UNION_NAMES in Scripts/create_water_geometry.py so the live test '
                          'and the offline export classify the same meshes the same way. Substring '
                          'matching on editor labels was tried first and is wrong: labels are '
                          'user-editable and need not match the manifest at all.'),
            'reportNearest': 25,
        },
        'verification': {
            'transformToleranceCm': 0.001,
            'staticBoundsToleranceCm': 0.05,
            'compareRule': ('Every water actor is spawned at the world origin with an identity '
                            'transform, because the OBJ vertices are already absolute world '
                            'centimetres. Reopened world bounds must therefore equal '
                            'canonicalBoundsCm; any offset is a silent re-siting of the stream.'),
        },
        'limitations': list(manifest.get('limitations') or []),
    }
    SPEC_PATH.write_text(json.dumps(spec, indent=2) + '\n', encoding='utf-8')
    return spec


# --------------------------------------------------------------------------

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
    return 'release_water.py' in command_line and (
        '-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    groups = GROUP_ORDER
    import_only = '-waterimportonly' in command_line
    skip_actor = '-waterskipactor' in command_line
    for token in command_line.split():
        if token.startswith('-watergroups='):
            groups = normalise_groups(token.split('=', 1)[1].strip('"'))
    try:
        receipt = release(load_target=True, groups=groups, import_only=import_only,
                          skip_actor=skip_actor)
        ue.log('release_water: %s groups %s placed %s' % (
            receipt['status'], list(groups), receipt.get('placedActorCount')))
    except Exception as error:
        ue.log_error('release_water failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        import sys
        if '--write-spec' in sys.argv:
            write_spec()
            print(json.dumps({'wrote': str(SPEC_PATH), 'sha256': sha256_of(SPEC_PATH)}, indent=2))
        else:
            print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()
