"""Guarded native import and row placement of the PalmReliefV1 panels in the combined map.

What it does, in order (every number comes from Scripts/release_import_reliefs.spec.json):

  1. Guards: right project, no game world, no dirty packages, target namespace
     /Game/MikdashV3/MaterialReview/SanctuaryPalmReliefV1 absent, frozen OBJ hashes intact.
  2. Imports SM_CedarPalmBackingV1.obj and SM_PalmCarvingV1.obj through the reviewed
     legacy OBJ adapter path (FbxFactory, same settings as the keilim/keruvim imports),
     verifies triangle counts and canonical bounds, assigns EXISTING materials to every
     slot (backing -> canonical cedar, carving -> HeikhalKeilim gold) and saves the assets.
  3. Winding check (GeometryScript, needs -EnablePlugins=GeometryScripting): the source OBJ
     was written with Y reflected and winding reversed to compensate the importer. The
     bounds check proves the Y reflection round-trips; the winding check proves the front
     faces point along local +Y, which becomes the room direction after placement.
     Without a passing check the meshes stay saved but nothing is placed (override with
     -ReliefsAllowUnverifiedWinding, recorded in the receipt).
  4. Loads /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough, refuses if any
     RELEASE_Reliefs_* actor exists, checkpoints the .umap, reads the seven gold veneer
     panels and places a REPEATING 120 cm row along both long inner Heikhal walls
     (X -5600..-3600, |Y| 500, floor Z 925): 16 slots per wall, palms in even slots,
     odd slots left EMPTY as "keruv panel pending" (Yechezkel 41:18-20 alternation).
     Panels sit 1.5 cm in front of the veneer face read from the level. Any slot whose
     planned AABB intersects an existing actor is skipped and recorded.
  5. Saves, reopens, reads back every placed actor numerically, verifies pre-existing
     actors are unchanged, writes
     SourceAssets/sanctuary-detail/PalmReliefV1/native-import-<stamp>.json.

Commandlet invocation (serial; never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_import_reliefs.py"
      -EnablePlugins=GeometryScripting -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-Reliefs-01.log"

Optional switches (read from the engine command line):
  -ReliefsImportOnly               import + materials + winding check, no map change.
  -ReliefsPlaceOnly                namespace already holds the two saved meshes (first run
                                   2026-09-07, receipt native-import-20260907T171620931487Z):
                                   skip import, load them, re-verify triangles/bounds/materials,
                                   re-run the winding diagnostic, then place exactly as above.
  -ReliefsAllowUnverifiedWinding   place even if the winding check is unavailable/failed.

Winding pass criterion: signed volume under UE's face-normal convention > 0 with zero
face-normal/cross-product disagreements (every part is a closed solid, so this is decisive).
Band statistics near the front/back planes are recorded as information only; they include
bevel and moulding side faces and failed the first run while the volumes were positive.

Offline (no engine):  python Scripts/release_import_reliefs.py   -> prints the offline check.

Reuses the pure helpers and the Placement snapshot/spawn utilities of
Scripts/release_place_assets.py (AABB maths, union-of-boxes clearance, numeric readback)
so the two release scripts share one set of rules.
"""
import hashlib
import importlib.util
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_import_reliefs.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'


# --------------------------------------------------------------------------
# Spec, shared helpers and pure planning (no unreal import)
# --------------------------------------------------------------------------

def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']).resolve() != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def load_placement_helper(spec):
    """Import Scripts/release_place_assets.py as a module without running its main."""
    path = ROOT / spec['placementHelper']
    module_spec = importlib.util.spec_from_file_location('release_place_assets', path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    for name in ('sha256_of', 'disk_path', 'box_from_min_max', 'box_error', 'rotate_box_yaw',
                 'boxes_overlap_volume', 'verify_union_decomposition', 'Placement'):
        if not hasattr(module, name):
            raise RuntimeError('release_place_assets.py lacks helper ' + name)
    return module


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def union_boxes(boxes):
    return {'min': [min(b['min'][i] for b in boxes) for i in range(3)],
            'max': [max(b['max'][i] for b in boxes) for i in range(3)]}


def plan_slots(spec):
    """Centred 120 cm slots along X for one wall: [{index, centerX, role}]."""
    row = spec['row']
    x_min, x_max = row['xRangeCm']
    module = float(row['moduleCm'])
    count = int(math.floor((x_max - x_min) / module + 1e-9))
    if count < 2:
        raise RuntimeError('Row too short for an alternating scheme')
    margin = ((x_max - x_min) - count * module) / 2.0
    slots = []
    for index in range(count):
        role = 'palm' if index % 2 == row['palmSlotParity'] else 'keruv_panel_pending'
        slots.append({'index': index, 'centerX': x_min + margin + module * (index + 0.5), 'role': role})
    return slots, margin


def slot_transform(spec, wall, slot, back_plane_y, base_z):
    """Actor location/rotation for a slot; the mesh pivot is bottom-centre with +Y front."""
    return ([slot['centerX'], back_plane_y, base_z], [0.0, float(wall['yawDegrees']), 0.0])


def offline_check(spec=None, namespace_expected=None):
    """Consistency checks that need no engine. Raises on the first failure.

    namespace_expected: False for a fresh import (folder must be absent), True for
    -ReliefsPlaceOnly (folder must exist), None to record the state only.
    """
    spec = spec or load_spec()
    helper = load_placement_helper(spec)
    source = spec['source']
    report = {'sourceFiles': [], 'materialsOnDisk': {}}

    manifest_path = ROOT / source['manifest']
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['status'] != source['manifestStatusRequired']:
        raise RuntimeError('Relief manifest status ' + manifest['status'])
    if manifest['namespace'] != source['namespace']:
        raise RuntimeError('Relief manifest namespace differs from spec')
    by_name = {m['name']: m for m in manifest['meshes']}
    for record in source['meshes']:
        entry = by_name.get(record['name'])
        if entry is None:
            raise RuntimeError('Manifest lacks ' + record['name'])
        path = ROOT / source['folder'] / record['file']
        actual_sha = sha256_of(path)
        if actual_sha != record['sha256'] or entry['sha256'] != record['sha256']:
            raise RuntimeError('Frozen OBJ hash differs for ' + record['name'])
        if entry['triangles'] != record['triangles']:
            raise RuntimeError('Triangle count differs from manifest for ' + record['name'])
        if helper.box_error(entry['bounds_cm'], record['canonicalBoundsCm']) > 1e-6:
            raise RuntimeError('Canonical bounds differ from manifest for ' + record['name'])
        report['sourceFiles'].append({'name': record['name'], 'sha256': actual_sha, 'triangles': record['triangles']})

    namespace_dir = ROOT / 'Content' / source['namespace'][len('/Game/'):]
    report['namespaceFolderExistsOnDisk'] = namespace_dir.exists()
    report['savedMeshFilesOnDisk'] = {m['name']: (namespace_dir / 'Meshes' / (m['name'] + '.uasset')).exists() for m in source['meshes']}
    if namespace_expected is False and namespace_dir.exists():
        raise RuntimeError('Target namespace folder already exists on disk: ' + str(namespace_dir))
    if namespace_expected is True and not all(report['savedMeshFilesOnDisk'].values()):
        raise RuntimeError('Place-only needs both saved meshes on disk: %r' % report['savedMeshFilesOnDisk'])

    for role in ('backing', 'carving'):
        rows = []
        for candidate in spec['materials'][role]['candidates']:
            rows.append({'path': candidate['path'], 'kind': candidate['kind'],
                         'onDisk': helper.disk_path(candidate['path']).exists()})
        if not any(r['onDisk'] for r in rows):
            raise RuntimeError('No %s material candidate exists on disk' % role)
        report['materialsOnDisk'][role] = rows

    slots, margin = plan_slots(spec)
    module = spec['row']['moduleCm']
    edges = [(s['centerX'] - module / 2.0, s['centerX'] + module / 2.0) for s in slots]
    x_min, x_max = spec['row']['xRangeCm']
    if edges[0][0] < x_min - 1e-6 or edges[-1][1] > x_max + 1e-6:
        raise RuntimeError('Slots leave the wall X range')
    for (a0, a1), (b0, b1) in zip(edges, edges[1:]):
        if b0 < a1 - 1e-6:
            raise RuntimeError('Slots overlap')
    palms = [s for s in slots if s['role'] == 'palm']
    if len(palms) != len(slots) - len(palms):
        raise RuntimeError('Alternation must give equal palm and keruv slots for an even count')
    local = union_boxes([m['canonicalBoundsCm'] for m in source['meshes']])
    if local['min'][2] < -1e-6 or local['min'][1] < -1e-6:
        raise RuntimeError('Relief local box must start at Z 0 and Y 0 (bottom-centre pivot, +Y front)')
    veneer = spec['row']['veneer']
    lo, hi = veneer['standoffWindowCm']
    if not lo <= veneer['standoffCm'] <= hi:
        raise RuntimeError('Spec standoff outside the allowed window')
    report.update(slotsPerWall=len(slots), palmSlotsPerWall=len(palms), keruvPendingSlotsPerWall=len(slots) - len(palms),
                  rowMarginCm=margin, slotCentersX=[s['centerX'] for s in slots], reliefLocalBoxCm=local,
                  plannedBackPlaneAbsY=abs(veneer['heikhalSideExpectedBoundsCm']['-1']['max'][1]) - veneer['standoffCm'],
                  plannedFrontAbsY=abs(veneer['heikhalSideExpectedBoundsCm']['-1']['max'][1]) - veneer['standoffCm'] - local['max'][1],
                  status='offline_spec_consistent')
    return report


# --------------------------------------------------------------------------
# Engine side: import, materials, winding
# --------------------------------------------------------------------------

def _xyz(v):
    return [float(v.x), float(v.y), float(v.z)]


def _asset_path(obj):
    return obj.get_path_name().split('.')[0] if obj else None


def _static_mesh_box(mesh):
    box = mesh.get_bounding_box()
    return {'min': _xyz(box.min), 'max': _xyz(box.max)}


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def pick_material(ue, spec, role, receipt):
    """First existing MaterialInterface among the spec candidates; records fallbacks."""
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tried = []
    for position, candidate in enumerate(spec['materials'][role]['candidates']):
        exists = assets.does_asset_exist(candidate['path'])
        material = ue.load_asset(candidate['path']) if exists else None
        ok = isinstance(material, ue.MaterialInterface)
        tried.append({'path': candidate['path'], 'kind': candidate['kind'], 'exists': bool(exists), 'loaded': ok})
        if ok:
            if position > 0:
                receipt['limitations'].append('%s material fell back to %s (%s); preferred candidate missing' % (role, candidate['path'], candidate['kind']))
            receipt['materials'][role] = {'assigned': candidate['path'], 'kind': candidate['kind'], 'tried': tried}
            return material
    raise RuntimeError('No %s material candidate loads: %s' % (role, tried))


def import_one_mesh(ue, spec, record, material):
    """OBJ -> StaticMesh through the reviewed adapter settings; verifies and saves."""
    source = spec['source']
    settings = spec['importSettings']
    path = ROOT / source['folder'] / record['file']
    if sha256_of(path) != record['sha256']:
        raise RuntimeError('Frozen OBJ hash changed: ' + record['file'])

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
    for key, value in dict(filename=str(path), destination_path=source['meshFolder'], destination_name=record['name'],
                           automated=True, async_=False, replace_existing=False, save=False, options=ui,
                           factory=ue.FbxFactory()).items():
        task.set_editor_property(key, value)
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    objects = list(task.get_objects())
    if len(objects) != 1 or not isinstance(objects[0], ue.StaticMesh):
        raise RuntimeError('Import of %s produced %s' % (record['file'], [type(o).__name__ for o in objects]))
    mesh = objects[0]
    if mesh.get_name() != record['name']:
        raise RuntimeError('Imported name %s differs from destination_name %s' % (mesh.get_name(), record['name']))

    box = _static_mesh_box(mesh)
    error = max(abs(box[k][i] - record['canonicalBoundsCm'][k][i]) for k in ('min', 'max') for i in range(3))
    triangles = mesh.get_num_triangles(0)
    if error > source['boundsToleranceCm']:
        raise RuntimeError('%s bounds differ from canonical by %.4f cm (Y reflection did not round-trip?): %r' % (record['name'], error, box))
    if triangles != record['triangles']:
        raise RuntimeError('%s triangles %d differ from %d' % (record['name'], triangles, record['triangles']))

    slots = len(mesh.get_editor_property('static_materials'))
    for slot in range(slots):
        mesh.set_material(slot, material)
    not_assigned = [slot for slot in range(slots) if _asset_path(mesh.get_material(slot)) != _asset_path(material)]
    if not_assigned:
        raise RuntimeError('Material slots not assigned on %s: %s' % (record['name'], not_assigned))
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + record['name'])
    return mesh, {'asset': _asset_path(mesh), 'file': str(path), 'triangles': triangles, 'localBoundsCm': box,
                  'boundsErrorCm': error, 'materialSlots': slots, 'material': _asset_path(material),
                  'uassetSha256': sha256_of(ROOT / 'Content' / (_asset_path(mesh)[len('/Game/'):] + '.uasset'))}


def load_saved_mesh(ue, spec, record, receipt):
    """-ReliefsPlaceOnly: load an already imported mesh and re-verify it instead of importing."""
    source = spec['source']
    asset_path = source['meshFolder'] + '/' + record['name']
    mesh = ue.load_asset(asset_path)
    if not isinstance(mesh, ue.StaticMesh):
        raise RuntimeError('Saved mesh missing or not a StaticMesh: ' + asset_path)
    box = _static_mesh_box(mesh)
    error = max(abs(box[k][i] - record['canonicalBoundsCm'][k][i]) for k in ('min', 'max') for i in range(3))
    triangles = mesh.get_num_triangles(0)
    if error > source['boundsToleranceCm']:
        raise RuntimeError('%s saved bounds differ from canonical by %.4f cm: %r' % (record['name'], error, box))
    if triangles != record['triangles']:
        raise RuntimeError('%s saved triangles %d differ from %d' % (record['name'], triangles, record['triangles']))

    allowed = {c['path']: c['kind'] for c in spec['materials'][record['role']]['candidates']}
    slots = len(mesh.get_editor_property('static_materials'))
    assigned = {_asset_path(mesh.get_material(slot)) for slot in range(slots)}
    wrong = sorted(str(p) for p in assigned if p not in allowed)
    if slots == 0 or wrong:
        raise RuntimeError('%s has %d slots; materials outside the spec candidates: %s' % (record['name'], slots, wrong))
    if len(assigned) != 1:
        raise RuntimeError('%s slots carry mixed materials: %s' % (record['name'], sorted(assigned)))
    material_path = assigned.pop()
    receipt['materials'][record['role']] = {'assigned': material_path, 'kind': allowed[material_path], 'verifiedOnSavedMesh': True}
    return mesh, {'asset': _asset_path(mesh), 'file': None, 'triangles': triangles, 'localBoundsCm': box,
                  'boundsErrorCm': error, 'materialSlots': slots, 'material': material_path, 'reused': True,
                  'uassetSha256': sha256_of(ROOT / 'Content' / (_asset_path(mesh)[len('/Game/'):] + '.uasset'))}


def winding_report(ue, mesh, spec):
    """Prove the imported front faces point along local +Y (the room after placement).

    Reads LOD0 source triangles with GeometryScript and computes, per triangle, UE's
    face normal (FDynamicMesh3::GetTriNormal, left-handed cross(C-A, B-A)) plus an
    independent cross product with the same convention. Criteria are in the spec.
    """
    check = spec['windingCheck']
    needed = ('GeometryScript_AssetUtils', 'GeometryScript_MeshQueries')
    if not all(hasattr(ue, n) for n in needed):
        return {'status': 'unavailable', 'passed': False,
                'reason': 'GeometryScripting not loaded; launch with -EnablePlugins=GeometryScripting'}
    dynamic = ue.DynamicMesh()
    options = ue.GeometryScriptCopyMeshFromAssetOptions()
    options.set_editor_property('apply_build_settings', False)
    options.set_editor_property('request_tangents', False)
    options.set_editor_property('use_build_scale', False)
    lod = ue.GeometryScriptMeshReadLOD()
    lod.set_editor_property('lod_type', ue.GeometryScriptLODType.SOURCE_MODEL)
    lod.set_editor_property('lod_index', 0)
    result = ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(mesh, dynamic, options, lod)
    if ue.GeometryScriptOutcomePins.SUCCESS not in result:
        return {'status': 'copy_failed', 'passed': False, 'reason': str(result)}

    query = ue.GeometryScript_MeshQueries
    bounds = _static_mesh_box(mesh)
    cosine = check['facingCosine']
    tolerance = check['planeToleranceCm']
    flux = 0.0
    disagreements = 0
    front_band = {'total': 0, 'facingPlusY': 0}
    back_band = {'total': 0, 'facingMinusY': 0}
    plus_y_max_centroid = None
    minus_y_min_centroid = None
    count = dynamic.get_triangle_count()
    for tid in range(count):
        positions = [_xyz(v) for v in query.get_triangle_positions(dynamic, tid) if isinstance(v, ue.Vector)]
        if len(positions) != 3:
            return {'status': 'read_failed', 'passed': False, 'reason': 'triangle %d has %d corners' % (tid, len(positions))}
        face = query.get_triangle_face_normal(dynamic, tid)
        normals = [_xyz(v) for v in face if isinstance(v, ue.Vector)] if isinstance(face, tuple) else [_xyz(face)]
        if len(normals) != 1:
            return {'status': 'read_failed', 'passed': False, 'reason': 'no face normal for triangle %d' % tid}
        normal = normals[0]
        a, b, c = positions
        ue_cross = _cross(_sub(c, a), _sub(b, a))
        if _dot(ue_cross, normal) < 0:
            disagreements += 1
        area = 0.5 * math.sqrt(_dot(ue_cross, ue_cross))
        centroid = [(a[i] + b[i] + c[i]) / 3.0 for i in range(3)]
        flux += _dot(normal, centroid) * area
        if normal[1] > cosine:
            plus_y_max_centroid = centroid[1] if plus_y_max_centroid is None else max(plus_y_max_centroid, centroid[1])
        if normal[1] < -cosine:
            minus_y_min_centroid = centroid[1] if minus_y_min_centroid is None else min(minus_y_min_centroid, centroid[1])
        if centroid[1] >= bounds['max'][1] - tolerance:
            front_band['total'] += 1
            front_band['facingPlusY'] += 1 if normal[1] > cosine else 0
        if centroid[1] <= bounds['min'][1] + tolerance:
            back_band['total'] += 1
            back_band['facingMinusY'] += 1 if normal[1] < -cosine else 0

    signed_volume = flux / 3.0
    # Decisive test: every part is a closed solid (offline_validation: closed edges, positive
    # canonical volume), so a positive signed volume under UE's face-normal convention means
    # every front face points outward, i.e. the relief front points along local +Y.
    passed = signed_volume > 0 and disagreements == 0
    # Informational only (first run, 2026-09-07): the +-0.5 cm bands also contain bevel and
    # moulding side faces that legitimately face sideways, so a band fraction is not a criterion.
    front_ok = front_band['total'] > 0 and front_band['facingPlusY'] >= check['minFrontBandAgreement'] * front_band['total']
    back_ok = back_band['total'] > 0 and back_band['facingMinusY'] >= check['minFrontBandAgreement'] * back_band['total']
    plus_reaches_front = plus_y_max_centroid is not None and abs(plus_y_max_centroid - bounds['max'][1]) <= tolerance
    minus_reaches_back = minus_y_min_centroid is not None and abs(minus_y_min_centroid - bounds['min'][1]) <= tolerance
    return {'status': 'checked', 'passed': passed, 'triangles': count, 'signedVolumeUEcm3': signed_volume,
            'faceNormalVsCrossDisagreements': disagreements,
            'passCriterion': 'signedVolumeUEcm3 > 0 and faceNormalVsCrossDisagreements == 0',
            'informational': {'frontBand': front_band, 'backBand': back_band,
                              'frontBandMostlyPlusY': front_ok, 'backBandMostlyMinusY': back_ok,
                              'plusYFacingMaxCentroidY': plus_y_max_centroid, 'plusYFacingReachesFrontPlane': plus_reaches_front,
                              'minusYFacingMinCentroidY': minus_y_min_centroid, 'minusYFacingReachesBackPlane': minus_reaches_back},
            'localBoundsCm': bounds,
            'convention': 'UE left-handed face normal cross(C-A, B-A); local +Y is the room direction after placement '
                          '(yaw 0 on the -Y wall, yaw 180 on the +Y wall)'}


# --------------------------------------------------------------------------
# Engine side: row placement
# --------------------------------------------------------------------------

class ReliefRow:
    """Places the alternating palm row in the loaded combined map."""

    def __init__(self, ue, spec, helper, run, receipt):
        self.ue = ue
        self.spec = spec
        self.helper = helper
        self.run = run            # release_place_assets.Placement (snapshot, spawn, destroy)
        self.receipt = receipt

    def find_floor(self):
        row = self.spec['row']
        rows = self.run.actors_with_mesh(row['floorMesh'])
        if len(rows) != 1:
            raise RuntimeError('Expected one Heikhal clear floor actor, found %d' % len(rows))
        floor = rows[0]
        if self.helper.box_error(floor['bounds'], row['floorWorldBoundsCm']) > 1.0:
            raise RuntimeError('Heikhal floor bounds differ from manifest: %r' % (floor['bounds'],))
        if abs(floor['bounds']['max'][2] - row['floorTopZ']) > 0.05:
            raise RuntimeError('Heikhal floor top %.3f differs from spec %.3f' % (floor['bounds']['max'][2], row['floorTopZ']))
        return floor

    def find_veneers(self):
        """All veneer actors plus the two Heikhal side panels keyed by wall sign."""
        veneer = self.spec['row']['veneer']
        all_rows = [r for r in self.run.snapshot if veneer['mesh'] in r['meshes'] and r['folder'].endswith(veneer['folderSuffix'])]
        if len(all_rows) != veneer['expectedCount']:
            raise RuntimeError('Expected %d veneer actors, found %d' % (veneer['expectedCount'], len(all_rows)))
        sides = {}
        for sign, expected in veneer['heikhalSideExpectedBoundsCm'].items():
            matches = [r for r in all_rows if self.helper.box_error(r['bounds'], expected) <= veneer['boundsToleranceCm']]
            if len(matches) != 1:
                raise RuntimeError('Heikhal side veneer for wall %s: %d matches' % (sign, len(matches)))
            sides[int(sign)] = matches[0]
        self.receipt['veneers'] = {'all': [{'label': r['label'], 'folder': r['folder'], 'worldBoundsCm': r['bounds']} for r in all_rows],
                                   'heikhalSides': {str(k): v['label'] for k, v in sides.items()}}
        return sides

    def clearance_candidates(self, floor, veneers):
        """Snapshot actors as AABB candidates; hollow unions get a verified box decomposition."""
        clearance = self.spec['row']['clearance']
        manifest = json.loads((ROOT / clearance['architectureManifest']).read_text(encoding='utf-8-sig'))
        entries = {e['assetName']: e for e in manifest['meshes']}
        prefix = clearance['levelAssetPrefix']
        boxes_by_key = {}
        candidates = []
        excluded_labels = {floor['label']} | {v['label'] for v in veneers.values()}
        # Terrain tiles are 400 to 800 m wide non-convex surfaces far below the sanctuary floor;
        # their AABBs enclose the whole Heikhal and produced 32/32 false blockers on the first run.
        terrain_folders = ('Jerusalem context/Terrain', 'FutureMountV1/Terrain', 'Future Mount/Terrain')
        excluded_terrain = []
        for row in self.run.snapshot:
            if not row['meshes'] or row['label'] in excluded_labels:
                continue
            if any(row['folder'].startswith(f) for f in terrain_folders) or \
                    any('/JerusalemContext/Terrain/' in (m or '') or '/FutureMountV1/Terrain/' in (m or '') for m in row['meshes']):
                excluded_terrain.append(row['label'])
                continue
            key = None
            if row['folder'] == clearance['unionFolder'] and len(row['meshes']) == 1 and (row['meshes'][0] or '').startswith(prefix):
                name = row['meshes'][0][len(prefix):]
                entry = entries.get(name)
                if entry is not None and entry.get('semantic') == 'union' and \
                        self.helper.box_error(row['bounds'], entry['expectedBoundsUnrealCm']) <= clearance['unionBoundsToleranceCm']:
                    boxes_by_key[name] = self.helper.verify_union_decomposition(entry, clearance['unionBoundsToleranceCm'])
                    key = name
            candidates.append({'label': row['label'], 'bounds': row['bounds'], 'unionKey': key})
        self.receipt['clearance'] = {'actorsConsidered': len(candidates), 'excludedActors': sorted(excluded_labels),
                                     'excludedTerrainTileCount': len(excluded_terrain),
                                     'excludedTerrainRule': 'terrain tile AABBs (400-800 m) enclose the Heikhal; surfaces lie far below Z 925',
                                     'unionsDecomposed': {k: len(v) for k, v in boxes_by_key.items()}}
        return candidates, boxes_by_key

    def blockers_for(self, planned, candidates, boxes_by_key):
        blockers = []
        for candidate in candidates:
            if not self.helper.boxes_overlap_volume(planned, candidate['bounds']):
                continue
            boxes = boxes_by_key.get(candidate['unionKey']) if candidate['unionKey'] else None
            if boxes is None:
                blockers.append({'label': candidate['label'], 'kind': 'actor_aabb'})
                continue
            hits = [b['name'] for b in boxes if self.helper.boxes_overlap_volume(planned, b)]
            if hits:
                blockers.append({'label': candidate['label'], 'kind': 'union_constituent_box', 'constituents': hits})
        return blockers

    def place(self, meshes):
        """Spawn palms in even slots of both walls; returns (records, slot report)."""
        ue = self.ue
        spec = self.spec
        row_spec = spec['row']
        veneer_spec = row_spec['veneer']
        tolerance = spec['verification']['staticBoundsToleranceCm']
        floor = self.find_floor()
        veneers = self.find_veneers()
        candidates, boxes_by_key = self.clearance_candidates(floor, veneers)
        local = union_boxes([m['localBoundsCm'] for m in meshes.values()])
        base_z = floor['bounds']['max'][2] + row_spec['baseLiftCm']
        slots, margin = plan_slots(spec)

        walls_report = []
        records = []
        placed_actors = []
        counter = 0
        try:
            for wall in row_spec['walls']:
                sign = wall['sign']
                veneer = veneers[sign]
                # Room-facing veneer face: max Y on the -Y wall, min Y on the +Y wall.
                face_y = veneer['bounds']['max'][1] if sign < 0 else veneer['bounds']['min'][1]
                back_plane_y = face_y - sign * veneer_spec['standoffCm']
                standoff = abs(back_plane_y - face_y)
                lo, hi = veneer_spec['standoffWindowCm']
                wall_report = {'wall': wall['name'], 'sign': sign, 'yawDegrees': wall['yawDegrees'], 'veneerLabel': veneer['label'],
                               'veneerWorldBoundsCm': veneer['bounds'], 'veneerRoomFaceY': face_y, 'reliefBackPlaneY': back_plane_y,
                               'standoffCm': standoff, 'roomDirectionWorldY': wall['roomDirectionWorldY'], 'slots': []}
                walls_report.append(wall_report)
                if not lo <= standoff <= hi or (back_plane_y - face_y) * wall['roomDirectionWorldY'] <= 0:
                    wall_report['conflict'] = 'standoff %.3f cm outside [%s, %s] or not toward the room; wall skipped' % (standoff, lo, hi)
                    continue
                for slot in slots:
                    location, rotation = slot_transform(spec, wall, slot, back_plane_y, base_z)
                    planned = self.helper.rotate_box_yaw(local, location, rotation[1])
                    entry = {'index': slot['index'], 'role': slot['role'], 'location': location, 'rotation': rotation,
                             'plannedWorldBoundsCm': planned}
                    wall_report['slots'].append(entry)
                    if self.helper.boxes_overlap_volume(planned, veneer['bounds']):
                        entry['result'] = 'conflict_intersects_veneer'
                        continue
                    blockers = self.blockers_for(planned, candidates, boxes_by_key)
                    if blockers:
                        entry.update(result='skipped_intersects_existing_actor', blockers=blockers)
                        continue
                    if slot['role'] != 'palm':
                        entry['result'] = 'keruv_panel_pending_left_empty'
                        continue
                    labels = []
                    for role in ('backing', 'carving'):
                        mesh_info = meshes[role]
                        counter += 1
                        label = '%s%s_%d' % (spec['labelPrefix'], spec['group'], counter)
                        tags = ['Release' + spec['group'], 'Wall%+d' % sign, 'Slot%02d' % slot['index'], role]
                        actor, component = self.run.spawn_static(mesh_info['mesh'], location, rotation, label, spec['folder'],
                                                                 spec['collisionProfile'], tags)
                        placed_actors.append(actor)
                        mesh_planned = self.helper.rotate_box_yaw(mesh_info['localBoundsCm'], location, rotation[1])
                        placed_bounds = self.helper._actor_bounds(actor)
                        if self.helper.box_error(placed_bounds, mesh_planned) > tolerance:
                            raise RuntimeError('%s bounds differ from plan by %.4f' % (label, self.helper.box_error(placed_bounds, mesh_planned)))
                        records.append({'label': label, 'kind': 'StaticMeshActor', 'role': role, 'mesh': mesh_info['asset'],
                                        'wallSign': sign, 'slotIndex': slot['index'], 'location': location, 'rotation': rotation,
                                        'scale': [1.0, 1.0, 1.0], 'collisionProfile': spec['collisionProfile'],
                                        'plannedWorldBoundsCm': mesh_planned, 'placedWorldBoundsCm': placed_bounds, 'actor': actor})
                        labels.append(label)
                    entry.update(result='palm_placed', actors=labels)
        except Exception:
            self.run.destroy_all(placed_actors)
            self.receipt['walls'] = walls_report
            raise

        summary = {'slotsPerWall': len(slots), 'rowMarginCm': margin, 'moduleCm': row_spec['moduleCm'], 'baseZ': base_z,
                   'reliefLocalBoxCm': local, 'floorActor': floor['label'], 'groundSource': 'floor_component_bounds',
                   'palmsPlaced': sum(1 for w in walls_report for s in w['slots'] if s['result'] == 'palm_placed'),
                   'keruvPanelsPending': sum(1 for w in walls_report for s in w['slots'] if s['result'] == 'keruv_panel_pending_left_empty'),
                   'slotsSkipped': sum(1 for w in walls_report for s in w['slots'] if s['result'].startswith('skipped') or s['result'].startswith('conflict')),
                   'wallsInConflict': [w['wall'] for w in walls_report if 'conflict' in w]}
        self.receipt['walls'] = walls_report
        self.receipt['row'] = summary
        return records


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def _strip(record):
    return {k: v for k, v in record.items() if k != 'actor'}


def fresh_receipt_path(spec):
    """Stamped receipt path that does not exist yet (retries with a fresh stamp)."""
    for _ in range(10):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        path = ROOT / spec['receiptFolder'] / (spec['receiptPrefix'] + stamp + '.json')
        if not path.exists():
            return stamp, path
    raise RuntimeError('Could not allocate a fresh receipt stamp')


def run(import_only=False, allow_unverified_winding=False, place_only=False):
    """Import (or reuse), check, place. Returns the receipt dict; raises on guard failure.

    place_only: the namespace must already hold both saved meshes (first run
    2026-09-07); they are loaded and re-verified instead of imported, then the
    winding diagnostic and the placement run exactly as in a full run.
    """
    import unreal as ue
    if import_only and place_only:
        raise RuntimeError('-ReliefsImportOnly and -ReliefsPlaceOnly are mutually exclusive')
    spec = load_spec()
    helper = load_placement_helper(spec)
    offline = offline_check(spec, namespace_expected=place_only)
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present before import')
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    namespace_exists = assets.does_directory_exist(spec['source']['namespace'])
    if place_only and not namespace_exists:
        raise RuntimeError('Place-only requested but namespace is missing: ' + spec['source']['namespace'])
    if not place_only and namespace_exists:
        raise RuntimeError('Existing native namespace preserved (use -ReliefsPlaceOnly): ' + spec['source']['namespace'])

    stamp, receipt_path = fresh_receipt_path(spec)
    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(helper.disk_path(m, 'umap')) for m in spec['protectedMaps'] if helper.disk_path(m, 'umap').exists()}
    receipt = {
        'status': 'started', 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'mapMatchesAgentsMdLastSaved': map_sha_before == spec['lastKnownMapSha256'],
        'protectedMapSha256Before': protected, 'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
        'engineVersion': ue.SystemLibrary.get_engine_version(), 'offlineCheck': offline,
        'switches': {'importOnly': import_only, 'placeOnly': place_only, 'allowUnverifiedWinding': allow_unverified_winding},
        'mode': 'place_only_reusing_saved_meshes' if place_only else 'import_and_place',
        'sourceReference': 'Yechezkel 41:18-20: keruvim and palms alternate; each keruv has a man\'s face and a young lion\'s face. '
                           'Only the palm panel exists; keruv slots are recorded as pending.',
        'materials': {}, 'meshes': {}, 'windingCheck': {}, 'placed': [], 'errors': [], 'mapSaved': False,
        'limitations': list(spec['limitations']),
    }

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()

    saved = False
    try:
        # -- 1. import + materials (or reuse the saved meshes) ------------------------------
        meshes = {}
        for record in spec['source']['meshes']:
            if place_only:
                mesh, info = load_saved_mesh(ue, spec, record, receipt)
            else:
                material = pick_material(ue, spec, record['role'], receipt)
                mesh, info = import_one_mesh(ue, spec, record, material)
            info['mesh'] = mesh
            meshes[record['role']] = info
            receipt['meshes'][record['name']] = {k: v for k, v in info.items() if k != 'mesh'}
            write()
        receipt['status'] = 'meshes_verified' if place_only else 'meshes_saved'

        # -- 2. winding ------------------------------------------------------------------
        all_passed = True
        for role, info in meshes.items():
            report = winding_report(ue, info['mesh'], spec)
            receipt['windingCheck'][info['asset']] = report
            all_passed = all_passed and report['passed']
        receipt['windingVerifiedFrontTowardRoom'] = all_passed
        write()
        if import_only:
            receipt['status'] = 'meshes_saved_import_only_no_map_change'
            return receipt
        if not all_passed and spec['windingCheck']['requireForPlacement'] and not allow_unverified_winding:
            receipt['status'] = 'meshes_saved_placement_skipped_winding_unverified'
            receipt['limitations'].append('Placement skipped: winding check did not pass or was unavailable; rerun with '
                                          '-EnablePlugins=GeometryScripting or inspect the meshes before -ReliefsAllowUnverifiedWinding')
            return receipt
        if not all_passed:
            receipt['limitations'].append('Placed with UNVERIFIED winding by explicit switch; front faces may point into the wall')

        # -- 3. map guards + checkpoint -------------------------------------------------
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        if not levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != TARGET:
            raise RuntimeError('Loaded world %s is not the combined map' % world.get_outermost().get_name())
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present after loading the map; resolve before checkpointed placement')
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / TARGET[len('/Game/'):]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / TARGET[len('/Game/'):])
        receipt['checkpoint'] = str(checkpoint)

        run_state = helper.Placement(ue, spec)
        run_state.world = world
        run_state.receipt = receipt
        run_state.receipt_path = receipt_path
        run_state.take_snapshot()
        baseline = run_state.numeric_baseline(run_state.snapshot)
        own_prefix = spec['labelPrefix'] + spec['group'] + '_'
        clashes = [r['label'] for r in run_state.snapshot if r['label'].startswith(own_prefix) or r['folder'] == spec['folder']]
        if clashes:
            raise RuntimeError('Existing relief release actors preserved; refusing duplicate placement: %s' % clashes[:10])
        others = [r for r in run_state.snapshot if r['label'].startswith(spec['labelPrefix'])]
        receipt['preExistingReleaseActors'] = [{'label': r['label'], 'folder': r['folder'], 'meshes': r['meshes']} for r in others]
        write()

        # -- 4. place, save, reopen, read back ------------------------------------------
        records = ReliefRow(ue, spec, helper, run_state, receipt).place(meshes)
        receipt['placed'] = [_strip(r) for r in records]
        write()
        if not records:
            receipt['status'] = 'meshes_saved_nothing_placed_map_unchanged'
            return receipt
        current = run_state.numeric_baseline(run_state.take_snapshot())
        changed = [name for name, row in baseline.items() if current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:10])
        if not levels.save_current_level():
            raise RuntimeError('save_current_level returned False')
        saved = True
        receipt['mapSaved'] = True
        receipt['mapSha256AfterSave'] = sha256_of(map_file)
        write()

        if not levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        run_state.world = editor.get_editor_world()
        reopened = run_state.take_snapshot()
        reopened_numeric = run_state.numeric_baseline(reopened)
        changed = [name for name, row in baseline.items() if reopened_numeric.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors differ after reopen: %s' % changed[:10])
        verify = spec['verification']
        readback = []
        for record in records:
            matching = [r for r in reopened if r['label'] == record['label']]
            if len(matching) != 1:
                raise RuntimeError('Reopened actor count for %s is %d' % (record['label'], len(matching)))
            row = matching[0]
            close, error = helper._pose_close(row['pose'], record['location'], record['rotation'], record['scale'], verify['transformToleranceCm'])
            bounds_error = helper.box_error(row['bounds'], record['plannedWorldBoundsCm'])
            component = row['actor'].get_component_by_class(ue.StaticMeshComponent)
            entry = {'label': record['label'], 'folder': row['folder'], 'meshPath': row['meshes'], 'pose': row['pose'],
                     'worldBoundsCm': row['bounds'], 'poseErrorCm': error, 'boundsErrorCm': bounds_error,
                     'collisionProfile': str(component.get_collision_profile_name()),
                     'materials': [_asset_path(component.get_material(i)) for i in range(component.get_num_materials())]}
            readback.append(entry)
            if row['meshes'] != [record['mesh']]:
                raise RuntimeError('Reopened mesh differs for ' + record['label'])
            if not close or bounds_error > verify['staticBoundsToleranceCm']:
                raise RuntimeError('Reopened transform/bounds differ for %s (pose %.4f, bounds %.4f)' % (record['label'], error, bounds_error))
        receipt['reopenedReadback'] = readback
        receipt['status'] = 'reliefs_saved_reopened_visual_acceptance_pending_keruv_panels_pending'
        return receipt
    except Exception as error:
        receipt['errors'].append(repr(error))
        if saved:
            receipt['status'] = 'failed_after_save_checkpoint_available'
        elif place_only:
            receipt['status'] = 'failed_place_only_map_unchanged_saved_meshes_untouched'
        elif receipt['meshes']:
            receipt['status'] = 'failed_partial_assets_preserved_map_unchanged'
        else:
            receipt['status'] = 'failed_before_import_nothing_changed'
        raise
    finally:
        receipt['mapSha256After'] = sha256_of(map_file)
        receipt['mapBytesChanged'] = receipt['mapSha256After'] != map_sha_before
        receipt['protectedMapsUnchanged'] = all(sha256_of(helper.disk_path(m, 'umap')) == v for m, v in protected.items())
        receipt['placedActorCount'] = len(receipt['placed'])
        write()


def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return 'release_import_reliefs.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    tokens = command_line.split()
    try:
        receipt = run(import_only='-reliefsimportonly' in tokens, allow_unverified_winding='-reliefsallowunverifiedwinding' in tokens,
                      place_only='-reliefsplaceonly' in tokens)
        ue.log('release_import_reliefs: %s placed %s winding_ok %s' % (receipt['status'], receipt.get('placedActorCount'),
                                                                        receipt.get('windingVerifiedFrontTowardRoom')))
    except Exception as error:
        ue.log_error('release_import_reliefs failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(), indent=2))
elif _invoked_as_native_script():
    _main()
