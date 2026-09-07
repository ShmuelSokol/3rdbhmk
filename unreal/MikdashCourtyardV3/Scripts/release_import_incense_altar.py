"""Guarded native import of the original IncenseAltarV2 study and its placement in the combined map,
replacing the plain-box REVIEW_HeikhalKeilim_SM_GoldenIncenseAltarStudy (0.8333-scaled).

What it does, in order (every number comes from Scripts/release_import_incense_altar.spec.json,
which was generated from SourceAssets/vessels-review/IncenseAltarV2/geometry-manifest.json,
keilim-scale-20260907T171503Z.json and the doors corridor spec):

  1. Guards: right project, no game world, no dirty packages, target namespace
     /Game/MikdashV3/MaterialReview/IncenseAltarV2 absent (or present for -AltarPlaceOnly),
     the two frozen OBJ hashes and the authoring-script hash intact, manifest status as required.
  2. Imports SM_IncenseAltarV2_Body.obj and SM_IncenseAltarV2_Poles.obj through the reviewed legacy
     OBJ adapter path (FbxFactory, same settings as the keilim/doors/third-party imports,
     build_nanite False), verifies triangle counts and canonical bounds (the OBJs are pre-reflected
     in Y, the importer reflects back), assigns the EXISTING gold material to EVERY slot, sets the
     BodySetup collision_trace_flag to CTF_USE_COMPLEX_AS_SIMPLE (imported OBJs have no simple
     collision) and saves the assets.
  3. Winding check (GeometryScript, needs -EnablePlugins=GeometryScripting): UE signed volume must
     be positive and equal the manifest part-volume sum within 1 %. A negative volume means
     inside-out: the triangle order is reversed via GeometryScript, the asset re-saved and
     re-checked; the flip is recorded.
  4. Loads /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough, refuses if a RELEASE_IncenseAltar_*
     actor exists, checkpoints the .umap to C:/Mikdash/Working-5.8/ReviewCheckpoints/IncenseAltarV2-<stamp>/,
     finds EXACTLY the old study actor (label, folder, mesh, pose) and the Heikhal floor, plans the
     two actors at [-4650, 0, 925] scale 1 yaw 0 (poles east-west), checks room envelope and AABB
     clearance, records the corridor lanes left on each side, destroys the old actor (label/folder/
     mesh/pose/bounds recorded), spawns RELEASE_IncenseAltar_Body and RELEASE_IncenseAltar_Poles with
     BlockAll, saves, reopens, reads back numerically (pose, bounds, collision profile, trace flag,
     materials) and writes SourceAssets/vessels-review/IncenseAltarV2/native-import-<stamp>.json
     (written at start and in finally).

Commandlet invocation (serial; never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_import_incense_altar.py"
      -EnablePlugins=GeometryScripting -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-IncenseAltar-01.log"

Optional switches (read from the engine command line):
  -AltarImportOnly              import + materials + collision + winding check, no map change.
  -AltarPlaceOnly               skip the import; both meshes must already exist (re-verified).
  -AltarAllowUnverifiedWinding  place even if the winding check is unavailable/failed.
  -AltarPolesNoCollision        poles actor NoCollision instead of BlockAll (body stays BlockAll).

Offline (no engine):  python Scripts/release_import_incense_altar.py  -> prints offline_check():
hashes, plain-Python OBJ parse (triangles, bounds round trip, signed volume vs manifest), planned
world AABBs, corridor lanes, materials on disk, map hash state.

Reuses the pure helpers and the Placement snapshot/spawn utilities of Scripts/release_place_assets.py.
"""
import hashlib
import importlib.util
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_import_incense_altar.spec.json'
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
    for name in ('sha256_of', 'disk_path', 'box_from_min_max', 'box_error', 'boxes_overlap_volume',
                 'verify_union_decomposition', 'Placement', '_pose_close', '_actor_bounds', '_actor_pose'):
        if not hasattr(module, name):
            raise RuntimeError('release_place_assets.py lacks helper ' + name)
    return module


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def box_inside(inner, outer, tolerance=0.0):
    return all(inner['min'][i] >= outer['min'][i] - tolerance and inner['max'][i] <= outer['max'][i] + tolerance for i in range(3))


def parse_obj(path):
    """Plain-Python OBJ parse: vertices [(x, y, z)], triangle index triples."""
    vertices = []
    faces = []
    with open(path, 'r', errors='replace') as handle:
        for line in handle:
            if line.startswith('v '):
                parts = line.split()
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif line.startswith('f '):
                indices = [int(token.split('/')[0]) - 1 for token in line.split()[1:]]
                for k in range(1, len(indices) - 1):
                    faces.append((indices[0], indices[k], indices[k + 1]))
    return vertices, faces


def bounds_of(vertices):
    return {'min': [min(v[i] for v in vertices) for i in range(3)], 'max': [max(v[i] for v in vertices) for i in range(3)]}


def reflect_y(box):
    return {'min': [box['min'][0], -box['max'][1], box['min'][2]], 'max': [box['max'][0], -box['min'][1], box['max'][2]]}


def right_handed_signed_volume(vertices, faces):
    total = 0.0
    for a, b, c in faces:
        ax, ay, az = vertices[a]
        bx, by, bz = vertices[b]
        cx, cy, cz = vertices[c]
        ux, uy, uz = bx - ax, by - ay, bz - az
        wx, wy, wz = cx - ax, cy - ay, cz - az
        total += ax * (uy * wz - uz * wy) + ay * (uz * wx - ux * wz) + az * (ux * wy - uy * wx)
    return total / 6.0


def _rotate(local, location, yaw_degrees):
    yaw = math.radians(yaw_degrees)
    cos_yaw, sin_yaw = math.cos(yaw), math.sin(yaw)
    corners = []
    for x in (local['min'][0], local['max'][0]):
        for y in (local['min'][1], local['max'][1]):
            for z in (local['min'][2], local['max'][2]):
                corners.append((location[0] + x * cos_yaw - y * sin_yaw, location[1] + x * sin_yaw + y * cos_yaw, location[2] + z))
    return {'min': [min(c[i] for c in corners) for i in range(3)], 'max': [max(c[i] for c in corners) for i in range(3)]}


def plan_transforms(spec, local_boxes, floor_top, poles_no_collision=False):
    """Actor transforms and planned world AABBs from the (engine or manifest) local boxes."""
    placement = spec['placement']
    collision = spec['collision']
    yaw = float(placement['yaw'])
    scale = float(placement['scale'])
    origin = [placement['origin'][0], placement['origin'][1], floor_top]
    tolerance = spec['source']['boundsToleranceCm']
    body_local = local_boxes['body']
    if abs(body_local['min'][2]) > tolerance:
        raise RuntimeError('Body local min Z is not 0: %r' % body_local['min'])
    if abs(scale - 1.0) > 1e-12:
        raise RuntimeError('This study is authored at scale 1; spec scale %r' % scale)
    body_world = _rotate(body_local, origin, yaw)
    poles_world = _rotate(local_boxes['poles'], origin, yaw)
    poles_profile = collision['poles']['noCollisionSwitchProfile'] if poles_no_collision else collision['poles']['profile']
    corridor = placement['corridor']
    lanes = {}
    for key, world in (('body', body_world), ('poles', poles_world)):
        extent = max(abs(world['min'][1]), abs(world['max'][1]))
        lanes[key] = {'maxAbsYcm': extent, 'freeLaneEachSideCm': corridor['halfWidthCm'] - extent,
                      'insideCorridorX': corridor['xMin'] <= world['min'][0] and world['max'][0] <= corridor['xMax'],
                      'heightAboveFloorCm': world['max'][2] - floor_top}
    return {
        'actors': {
            'body': {'label': placement['bodyLabel'], 'role': 'body', 'location': origin, 'rotation': [0.0, yaw, 0.0], 'scale': [scale] * 3,
                     'collisionProfile': collision['body']['profile'], 'plannedWorldBoundsCm': body_world, 'room': 'heikhal'},
            'poles': {'label': placement['polesLabel'], 'role': 'poles', 'location': origin, 'rotation': [0.0, yaw, 0.0], 'scale': [scale] * 3,
                      'collisionProfile': poles_profile, 'plannedWorldBoundsCm': poles_world, 'room': 'heikhal'},
        },
        'derived': {'yaw': yaw, 'polesAxisWorld': 'X (east-west)' if abs(yaw) < 1e-9 else 'rotated', 'bodySizeCm': [body_world['max'][i] - body_world['min'][i] for i in range(3)],
                    'polesSizeCm': [poles_world['max'][i] - poles_world['min'][i] for i in range(3)], 'bodyTopZ': body_world['max'][2]},
        'corridor': dict(corridor, lanes=lanes, verdict='corridor_passes_around_the_altar'),
    }


def check_rooms(spec, plan):
    envelopes = spec['placement']['roomEnvelope']
    for actor in plan['actors'].values():
        if not box_inside(actor['plannedWorldBoundsCm'], envelopes[actor['room']]):
            raise RuntimeError('%s planned AABB leaves the %s envelope: %r' % (actor['label'], actor['room'], actor['plannedWorldBoundsCm']))


def offline_check(spec=None, namespace_expected=None, poles_no_collision=False):
    """Consistency checks that need no engine. Raises on the first failure.

    namespace_expected: False for a fresh import (folder must be absent), True for -AltarPlaceOnly
    (folder must exist), None to record the state only.
    """
    spec = spec or load_spec()
    helper = load_placement_helper(spec)
    source = spec['source']
    report = {'sourceFiles': [], 'materialsOnDisk': {}}

    manifest_path = ROOT / source['manifest']
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['status'] != source['manifestStatusRequired']:
        raise RuntimeError('Manifest status %s, required %s' % (manifest['status'], source['manifestStatusRequired']))
    if manifest['namespace'] != source['namespace']:
        raise RuntimeError('Manifest namespace differs from spec')
    script_sha = sha256_of(ROOT / source['authoringScript'])
    if script_sha != source['authoringScriptSha256'] or manifest.get('script_sha256') != script_sha:
        raise RuntimeError('Authoring script changed after the spec/manifest were frozen')
    report['manifestSha256'] = sha256_of(manifest_path)
    by_name = {m['name']: m for m in manifest['meshes']}
    if set(by_name) != {m['name'] for m in source['meshes']} or len(source['meshes']) != 2:
        raise RuntimeError('Spec mesh list differs from the manifest')
    local_boxes = {}
    for record in source['meshes']:
        entry = by_name[record['name']]
        path = ROOT / source['folder'] / record['file']
        actual_sha = sha256_of(path)
        if actual_sha != record['sha256'] or entry['sha256'] != record['sha256']:
            raise RuntimeError('Frozen OBJ hash differs for ' + record['name'])
        if entry['triangles'] != record['triangles'] or abs(entry['partVolumeSumCm3'] - record['partVolumeSumCm3']) > 1e-9:
            raise RuntimeError('Manifest triangles/volume differ from spec for ' + record['name'])
        if helper.box_error(entry['bounds_cm'], record['canonicalBoundsCm']) > 1e-9:
            raise RuntimeError('Manifest bounds differ from spec for ' + record['name'])
        if not all(p['closed'] and p['volume_cm3'] > 0 for p in entry['parts']):
            raise RuntimeError('Manifest reports an open or inverted part in ' + record['name'])
        vertices, faces = parse_obj(path)
        if len(faces) != record['triangles']:
            raise RuntimeError('%s parsed %d triangles, spec %d' % (record['name'], len(faces), record['triangles']))
        file_box = bounds_of(vertices)
        error = helper.box_error(reflect_y(file_box), record['canonicalBoundsCm'])
        if error > 1e-6:
            raise RuntimeError('%s file bounds reflected in Y differ from canonical by %.6f' % (record['name'], error))
        volume = right_handed_signed_volume(vertices, faces)
        relative = abs(volume - record['partVolumeSumCm3']) / record['partVolumeSumCm3']
        if volume <= 0 or relative > 1e-6:
            raise RuntimeError('%s file signed volume %.3f differs from manifest %.3f' % (record['name'], volume, record['partVolumeSumCm3']))
        local_boxes[record['role']] = record['canonicalBoundsCm']
        report['sourceFiles'].append({'name': record['name'], 'role': record['role'], 'file': str(path), 'sha256': actual_sha, 'triangles': len(faces),
                                      'vertices': len(vertices), 'fileBounds': file_box, 'canonicalBoundsCm': record['canonicalBoundsCm'],
                                      'fileRightHandedSignedVolumeCm3': volume, 'manifestPartVolumeSumCm3': record['partVolumeSumCm3']})
    total = sum(m['triangles'] for m in source['meshes'])
    if total != source['totalTriangles'] or total >= 60000:
        raise RuntimeError('Triangle total %d differs from spec or exceeds the 60k budget' % total)
    body = local_boxes['body']
    faces_cm = manifest['body_face_to_face_cm']
    if abs(body['max'][2] - manifest['height_to_horn_tops_cm']) > 1e-9 or abs(manifest['height_to_horn_tops_cm'] - 2 * manifest['amah_cm']) > 1e-9:
        raise RuntimeError('Body height differs from two amot')
    if abs(faces_cm[0] - manifest['amah_cm']) > 1e-9 or abs(manifest['amah_cm'] - 5 * manifest['tefach_cm']) > 1e-9:
        raise RuntimeError('Footprint differs from one five-tefach amah')
    report['dimensionsCm'] = {'faceToFace': faces_cm, 'heightToHornTops': manifest['height_to_horn_tops_cm'], 'tefach': manifest['tefach_cm'], 'amah': manifest['amah_cm'],
                              'bodyBoundsIncludingZerAndRings': [body['max'][i] - body['min'][i] for i in range(3)]}

    removal = spec['removal']
    receipt_path = ROOT / 'SourceAssets/vessels-review/keilim-scale-20260907T171503Z.json'
    if receipt_path.exists():
        altar = json.loads(receipt_path.read_text(encoding='utf-8'))['groups']['altar']
        if altar['label'] != removal['label'] or altar['mesh'].split('.')[0] != removal['mesh'] or altar['folder'] != removal['folder']:
            raise RuntimeError('Removal target differs from the keilim-scale receipt')
        close, error = helper._pose_close(altar['after'], removal['location'], removal['rotation'], removal['scale'], removal['poseToleranceCm'])
        if not close:
            raise RuntimeError('Removal pose differs from the keilim-scale receipt by %.4f' % error)
        report['removalCrossCheck'] = 'matches keilim-scale-20260907T171503Z.json'
    old_size = [removal['worldBoundsCm']['max'][i] - removal['worldBoundsCm']['min'][i] for i in range(3)]
    report['oldStudySizeCm'] = old_size

    namespace_dir = ROOT / 'Content' / source['namespace'][len('/Game/'):]
    report['namespaceFolderExistsOnDisk'] = namespace_dir.exists()
    report['savedMeshFilesOnDisk'] = {m['name']: (namespace_dir / 'Meshes' / (m['name'] + '.uasset')).exists() for m in source['meshes']}
    if namespace_expected is False and namespace_dir.exists():
        raise RuntimeError('Target namespace folder already exists on disk: ' + str(namespace_dir))
    if namespace_expected is True and not all(report['savedMeshFilesOnDisk'].values()):
        raise RuntimeError('Place-only needs both saved meshes on disk: %r' % report['savedMeshFilesOnDisk'])

    rows = [{'path': c['path'], 'kind': c['kind'], 'onDisk': helper.disk_path(c['path']).exists()} for c in spec['materials']['gold']['candidates']]
    if not any(r['onDisk'] for r in rows):
        raise RuntimeError('No gold material candidate exists on disk')
    report['materialsOnDisk']['gold'] = rows
    if not (ROOT / spec['targetMapFile']).exists():
        raise RuntimeError('Target map file missing')
    report['mapSha256OnDisk'] = sha256_of(ROOT / spec['targetMapFile'])
    report['mapMatchesLastKnown'] = report['mapSha256OnDisk'] == spec['lastKnownMapSha256']

    floor = spec['placement']['floors']['heikhal']
    architecture = json.loads((ROOT / spec['placement']['clearance']['architectureManifest']).read_text(encoding='utf-8-sig'))
    floor_name = floor['mesh'][len(spec['placement']['clearance']['levelAssetPrefix']):]
    entry = next((e for e in architecture['meshes'] if e['assetName'] == floor_name), None)
    if entry is None or helper.box_error(entry['expectedBoundsUnrealCm'], floor['worldBoundsCm']) > 1e-6:
        raise RuntimeError('Heikhal floor bounds differ from the architecture manifest')
    plan = plan_transforms(spec, local_boxes, floor['topZ'], poles_no_collision)
    check_rooms(spec, plan)
    new_body = plan['actors']['body']['plannedWorldBoundsCm']
    if not (removal['worldBoundsCm']['min'][0] > new_body['min'][0] - 5 and removal['worldBoundsCm']['max'][0] < new_body['max'][0] + 5):
        raise RuntimeError('New body footprint does not cover the old study footprint')
    for actor in plan['actors'].values():
        lane = plan['corridor']['lanes'][actor['role']]
        if lane['freeLaneEachSideCm'] <= 0 or not lane['insideCorridorX']:
            raise RuntimeError('%s blocks the whole corridor width: %r' % (actor['label'], lane))
    report['plan'] = plan
    report['status'] = 'offline_spec_consistent'
    return report


# --------------------------------------------------------------------------
# Engine side: import, materials, collision, winding
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


def _uasset_sha(mesh):
    return sha256_of(ROOT / 'Content' / (_asset_path(mesh)[len('/Game/'):] + '.uasset'))


def pick_material(ue, spec, receipt):
    """First existing MaterialInterface among the gold candidates; records fallbacks."""
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tried = []
    for position, candidate in enumerate(spec['materials']['gold']['candidates']):
        exists = assets.does_asset_exist(candidate['path'])
        material = ue.load_asset(candidate['path']) if exists else None
        ok = isinstance(material, ue.MaterialInterface)
        tried.append({'path': candidate['path'], 'kind': candidate['kind'], 'exists': bool(exists), 'loaded': ok})
        if ok:
            if position > 0:
                receipt['limitations'].append('gold material fell back to %s (%s); preferred candidate missing' % (candidate['path'], candidate['kind']))
            receipt['materials']['gold'] = {'assigned': candidate['path'], 'kind': candidate['kind'], 'tried': tried}
            return material
    raise RuntimeError('No gold material candidate loads: %s' % tried)


def mesh_collision_state(ue, mesh):
    state = {'collisionTraceFlag': None, 'simpleCollisionElements': None}
    body = mesh.get_editor_property('body_setup')
    if body is not None:
        state['collisionTraceFlag'] = str(body.get_editor_property('collision_trace_flag'))
        try:
            agg = body.get_editor_property('agg_geom')
            state['simpleCollisionElements'] = sum(len(agg.get_editor_property(k)) for k in ('convex_elems', 'box_elems', 'sphere_elems', 'sphyl_elems'))
        except Exception as error:  # noqa: BLE001 - informational only
            state['aggGeomError'] = str(error)
    return state


def set_complex_as_simple(ue, spec, mesh):
    """Imported OBJ meshes have no simple collision: trace against the triangles (terrain/buildings pattern)."""
    flag = getattr(ue.CollisionTraceFlag, spec['collision']['traceFlag'])
    body = mesh.get_editor_property('body_setup')
    if body is None:
        body = ue.BodySetup(outer=mesh)
        mesh.set_editor_property('body_setup', body)
    body.set_editor_property('collision_trace_flag', flag)
    if mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag') != flag:
        raise RuntimeError('collision_trace_flag did not take on ' + mesh.get_name())
    return mesh_collision_state(ue, mesh)


def verify_mesh(spec, record, mesh):
    box = _static_mesh_box(mesh)
    tolerance = spec['source']['boundsToleranceCm']
    error = max(abs(box[k][i] - record['canonicalBoundsCm'][k][i]) for k in ('min', 'max') for i in range(3))
    if error > tolerance:
        raise RuntimeError('%s bounds differ from canonical by %.4f cm (Y reflection did not round-trip?): %r' % (record['name'], error, box))
    triangles = mesh.get_num_triangles(0)
    if triangles != record['triangles']:
        raise RuntimeError('%s triangles %d differ from %d' % (record['name'], triangles, record['triangles']))
    return box, error, triangles


def assign_material(ue, mesh, material, record, assign=True):
    slots = len(mesh.get_editor_property('static_materials'))
    if slots < 1:
        raise RuntimeError('%s has no material slots' % record['name'])
    if assign:
        for slot in range(slots):
            mesh.set_material(slot, material)
    expected = _asset_path(material)
    slot_paths = [_asset_path(mesh.get_material(slot)) for slot in range(slots)]
    not_assigned = [slot for slot, path in enumerate(slot_paths) if path != expected]
    if not_assigned:
        raise RuntimeError('Material slots %s on %s: %s' % ('not assigned' if assign else 'do not carry the gold', record['name'], not_assigned))
    return slots, expected


def import_one_mesh(ue, spec, record, material):
    """OBJ -> StaticMesh through the reviewed adapter settings; verifies, gold, collision flag, saves."""
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
                           automated=True, async_=False, replace_existing=False, save=False, options=ui, factory=ue.FbxFactory()).items():
        task.set_editor_property(key, value)
    started = datetime.now(timezone.utc)
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    seconds = (datetime.now(timezone.utc) - started).total_seconds()
    objects = list(task.get_objects())
    if len(objects) != 1 or not isinstance(objects[0], ue.StaticMesh):
        raise RuntimeError('Import of %s produced %s' % (record['file'], [type(o).__name__ for o in objects]))
    mesh = objects[0]
    if mesh.get_name() != record['name']:
        raise RuntimeError('Imported name %s differs from destination_name %s' % (mesh.get_name(), record['name']))
    box, error, triangles = verify_mesh(spec, record, mesh)
    slots, material_path = assign_material(ue, mesh, material, record)
    collision = set_complex_as_simple(ue, spec, mesh)
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + record['name'])
    return mesh, {'asset': _asset_path(mesh), 'file': str(path), 'triangles': triangles, 'vertices': mesh.get_num_vertices(0), 'localBoundsCm': box,
                  'boundsErrorCm': error, 'materialSlots': slots, 'material': material_path, 'meshCollision': collision,
                  'importSeconds': seconds, 'buildNanite': False, 'uassetSha256': _uasset_sha(mesh)}


def load_saved_mesh(ue, spec, record, receipt):
    """-AltarPlaceOnly: load an already imported mesh and re-verify (bounds, triangles, gold, trace flag)."""
    asset_path = spec['source']['meshFolder'] + '/' + record['name']
    mesh = ue.load_asset(asset_path)
    if not isinstance(mesh, ue.StaticMesh):
        raise RuntimeError('Saved mesh missing or not a StaticMesh: ' + asset_path)
    box, error, triangles = verify_mesh(spec, record, mesh)
    allowed = {c['path']: c['kind'] for c in spec['materials']['gold']['candidates']}
    slots = len(mesh.get_editor_property('static_materials'))
    assigned = {_asset_path(mesh.get_material(slot)) for slot in range(slots)}
    wrong = sorted(str(p) for p in assigned if p not in allowed)
    if slots == 0 or wrong or len(assigned) != 1:
        raise RuntimeError('%s has %d slots; materials %s (outside spec: %s)' % (record['name'], slots, sorted(map(str, assigned)), wrong))
    material_path = assigned.pop()
    receipt['materials'].setdefault('gold', {'assigned': material_path, 'kind': allowed[material_path], 'verifiedOnSavedMesh': True})
    collision = mesh_collision_state(ue, mesh)
    if spec['collision']['traceFlag'] not in (collision['collisionTraceFlag'] or ''):
        collision = set_complex_as_simple(ue, spec, mesh)
        if not ue.get_editor_subsystem(ue.EditorAssetSubsystem).save_loaded_asset(mesh, only_if_is_dirty=False):
            raise RuntimeError('save_loaded_asset failed after setting the trace flag on ' + record['name'])
        receipt['limitations'].append('%s lacked the complex-as-simple trace flag; set and re-saved during place-only' % record['name'])
    return mesh, {'asset': _asset_path(mesh), 'file': None, 'triangles': triangles, 'vertices': mesh.get_num_vertices(0), 'localBoundsCm': box,
                  'boundsErrorCm': error, 'materialSlots': slots, 'material': material_path, 'meshCollision': collision, 'reused': True,
                  'uassetSha256': _uasset_sha(mesh)}


def _source_dynamic_mesh(ue, mesh):
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
        raise RuntimeError('copy_mesh_from_static_mesh_v2 failed: ' + str(result))
    return dynamic


def _bulk_triangles(ue, dynamic):
    """(positions, triangles) via the GeometryScript list API, or None if unavailable."""
    query = ue.GeometryScript_MeshQueries
    lists = getattr(ue, 'GeometryScript_List', None)
    if lists is None or not hasattr(query, 'get_all_vertex_positions') or not hasattr(query, 'get_all_triangle_indices'):
        return None
    try:
        position_result = query.get_all_vertex_positions(dynamic, ue.GeometryScriptVectorList(), False)
        triangle_result = query.get_all_triangle_indices(dynamic, ue.GeometryScriptTriangleList(), False)
        position_list = [v for v in position_result if isinstance(v, ue.GeometryScriptVectorList)]
        triangle_list = [t for t in triangle_result if isinstance(t, ue.GeometryScriptTriangleList)]
        if len(position_list) != 1 or len(triangle_list) != 1:
            return None
        positions = [_xyz(v) for v in lists.convert_vector_list_to_array(position_list[0])]
        triangles = [(int(t.x), int(t.y), int(t.z)) for t in lists.convert_triangle_list_to_array(triangle_list[0])]
    except Exception:  # noqa: BLE001 - API shape differs between engine builds; the per-triangle loop is the fallback
        return None
    if len(triangles) != dynamic.get_triangle_count() or len(positions) < dynamic.get_vertex_count():
        return None
    return positions, triangles


def winding_report(ue, mesh, record, spec):
    """UE signed volume must be positive and match the manifest part-volume sum (closed authored parts)."""
    check = spec['windingCheck']
    if not all(hasattr(ue, n) for n in ('GeometryScript_AssetUtils', 'GeometryScript_MeshQueries')):
        return {'status': 'unavailable', 'passed': False, 'signedVolumeUEcm3': None, 'reason': 'GeometryScripting not loaded; launch with -EnablePlugins=GeometryScripting'}
    try:
        dynamic = _source_dynamic_mesh(ue, mesh)
    except RuntimeError as error:
        return {'status': 'copy_failed', 'passed': False, 'signedVolumeUEcm3': None, 'reason': str(error)}
    query = ue.GeometryScript_MeshQueries
    count = dynamic.get_triangle_count()
    flux = 0.0
    disagreements = 0
    sampled = 0
    bulk = _bulk_triangles(ue, dynamic)
    if bulk is not None:
        positions, triangles = bulk
        step = max(1, count // max(1, int(check['faceNormalSampleTriangles'])))
        for tid, (ia, ib, ic) in enumerate(triangles):
            a, b, c = positions[ia], positions[ib], positions[ic]
            ue_cross = _cross(_sub(c, a), _sub(b, a))
            flux += _dot(ue_cross, [(a[i] + b[i] + c[i]) / 3.0 for i in range(3)])
            if tid % step == 0:
                face = query.get_triangle_face_normal(dynamic, tid)
                normals = [_xyz(v) for v in face if isinstance(v, ue.Vector)] if isinstance(face, tuple) else [_xyz(face)]
                if len(normals) == 1:
                    sampled += 1
                    if _dot(ue_cross, normals[0]) < 0:
                        disagreements += 1
        method = 'bulk_lists_plus_sampled_face_normals'
    else:
        for tid in range(count):
            positions = [_xyz(v) for v in query.get_triangle_positions(dynamic, tid) if isinstance(v, ue.Vector)]
            if len(positions) != 3:
                return {'status': 'read_failed', 'passed': False, 'signedVolumeUEcm3': None, 'reason': 'triangle %d has %d corners' % (tid, len(positions))}
            face = query.get_triangle_face_normal(dynamic, tid)
            normals = [_xyz(v) for v in face if isinstance(v, ue.Vector)] if isinstance(face, tuple) else [_xyz(face)]
            if len(normals) != 1:
                return {'status': 'read_failed', 'passed': False, 'signedVolumeUEcm3': None, 'reason': 'no face normal for triangle %d' % tid}
            a, b, c = positions
            ue_cross = _cross(_sub(c, a), _sub(b, a))
            sampled += 1
            if _dot(ue_cross, normals[0]) < 0:
                disagreements += 1
            flux += _dot(ue_cross, [(a[i] + b[i] + c[i]) / 3.0 for i in range(3)])
        method = 'per_triangle_loop'
    signed_volume = flux / 6.0
    expected = record['partVolumeSumCm3']
    relative = abs(signed_volume - expected) / expected
    passed = signed_volume > 0 and disagreements == 0 and sampled > 0 and relative <= check['maxRelativeVolumeError']
    return {'status': 'checked', 'passed': passed, 'method': method, 'triangles': count, 'signedVolumeUEcm3': signed_volume,
            'manifestPartVolumeSumCm3': expected, 'relativeVolumeError': relative, 'faceNormalSamples': sampled,
            'faceNormalVsCrossDisagreements': disagreements,
            'passCriterion': 'signedVolumeUEcm3 > 0, relativeVolumeError <= %s, faceNormalVsCrossDisagreements == 0' % check['maxRelativeVolumeError'],
            'convention': 'UE left-handed face normal cross(C-A, B-A); volume by divergence theorem (asset cm)'}


def flip_winding(ue, mesh, spec):
    """Rebuild LOD0 with reversed triangle order (GeometryScript) and write it back in place."""
    check = spec['windingCheck']
    dynamic = _source_dynamic_mesh(ue, mesh)
    bulk = _bulk_triangles(ue, dynamic)
    query = ue.GeometryScript_MeshQueries
    if bulk is not None:
        positions, triangles = bulk
        vertices = [ue.Vector(*p) for p in positions]
        reversed_triangles = [ue.IntVector(c, b, a) for a, b, c in triangles]
        uv0 = [ue.Vector2D(p[0] / 100.0, p[1] / 100.0) for p in positions]
        method = 'bulk_reversed_indices'
    else:
        vertices, reversed_triangles, uv0 = [], [], []
        for tid in range(dynamic.get_triangle_count()):
            positions = [_xyz(v) for v in query.get_triangle_positions(dynamic, tid) if isinstance(v, ue.Vector)]
            if len(positions) != 3:
                raise RuntimeError('triangle %d has %d corners' % (tid, len(positions)))
            base = len(vertices)
            for corner in (2, 1, 0):
                vertices.append(ue.Vector(*positions[corner]))
                uv0.append(ue.Vector2D(positions[corner][0] / 100.0, positions[corner][1] / 100.0))
            reversed_triangles.append(ue.IntVector(base, base + 1, base + 2))
        method = 'per_triangle_reversed_corners'
    buffers = ue.GeometryScriptSimpleMeshBuffers()
    buffers.set_editor_property('vertices', vertices)
    buffers.set_editor_property('triangles', reversed_triangles)
    buffers.set_editor_property('uv0', uv0)
    rebuilt = ue.DynamicMesh()
    ue.GeometryScript_MeshEdits.append_buffers_to_mesh(rebuilt, buffers)
    if rebuilt.get_triangle_count() != dynamic.get_triangle_count():
        raise RuntimeError('Rebuilt triangle count differs')
    options = ue.GeometryScriptCopyMeshToAssetOptions()
    for key, value in check['rewriteOptions'].items():
        options.set_editor_property(key, value)
    lod = ue.GeometryScriptMeshWriteLOD()
    lod.set_editor_property('write_hi_res_source', False)
    lod.set_editor_property('lod_index', 0)
    result = ue.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(rebuilt, mesh, options, lod)
    if ue.GeometryScriptOutcomePins.SUCCESS not in result:
        raise RuntimeError('copy_mesh_to_static_mesh failed: ' + str(result))
    collision = set_complex_as_simple(ue, spec, mesh)   # the rewrite may reset the body setup
    if not ue.get_editor_subsystem(ue.EditorAssetSubsystem).save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed after winding flip for ' + mesh.get_name())
    return {'method': method, 'rewriteOptions': check['rewriteOptions'], 'triangles': rebuilt.get_triangle_count(), 'meshCollision': collision}


# --------------------------------------------------------------------------
# Engine side: removal and placement
# --------------------------------------------------------------------------

class AltarPlacement:
    """Removes the plain-box study actor and places the two altar actors in the loaded map."""

    def __init__(self, ue, spec, helper, run, receipt):
        self.ue = ue
        self.spec = spec
        self.helper = helper
        self.run = run
        self.receipt = receipt

    def find_floor(self):
        floors = self.spec['placement']['floors']
        rows = self.run.actors_with_mesh(floors['heikhal']['mesh'])
        if len(rows) != 1:
            raise RuntimeError('Expected one Heikhal clear floor actor, found %d' % len(rows))
        floor = rows[0]
        if self.helper.box_error(floor['bounds'], floors['heikhal']['worldBoundsCm']) > floors['boundsToleranceCm']:
            raise RuntimeError('Heikhal floor bounds differ from manifest: %r' % floor['bounds'])
        if abs(floor['bounds']['max'][2] - floors['heikhal']['topZ']) > floors['topToleranceCm']:
            raise RuntimeError('Heikhal floor top %.3f differs from spec %.3f' % (floor['bounds']['max'][2], floors['heikhal']['topZ']))
        return floor

    def find_removal(self):
        """Exactly the old study actor with the expected mesh, folder and pose; else refuse."""
        removal = self.spec['removal']
        rows = [r for r in self.run.snapshot if r['label'] == removal['label']]
        if len(rows) != 1:
            raise RuntimeError('Removal target %s: %d actors with that label' % (removal['label'], len(rows)))
        row = rows[0]
        if row['meshes'] != [removal['mesh']]:
            raise RuntimeError('Removal target carries mesh %s, expected %s' % (row['meshes'], removal['mesh']))
        if row['folder'] != removal['folder']:
            raise RuntimeError('Removal target is in folder %s, expected %s' % (row['folder'], removal['folder']))
        close, error = self.helper._pose_close(row['pose'], removal['location'], removal['rotation'], removal['scale'], removal['poseToleranceCm'])
        if not close:
            raise RuntimeError('Removal target pose differs from the recorded pose by %.4f' % error)
        others = [r['label'] for r in self.run.snapshot if removal['mesh'] in r['meshes'] and r is not row]
        if others:
            raise RuntimeError('The old study mesh is also carried by %s; refusing' % others)
        return row

    def clearance_candidates(self, excluded_labels):
        clearance = self.spec['placement']['clearance']
        manifest = json.loads((ROOT / clearance['architectureManifest']).read_text(encoding='utf-8-sig'))
        entries = {e['assetName']: e for e in manifest['meshes']}
        prefix = clearance['levelAssetPrefix']
        boxes_by_key = {}
        candidates = []
        excluded_terrain = []
        for row in self.run.snapshot:
            if not row['meshes'] or row['label'] in excluded_labels:
                continue
            if any(row['folder'].startswith(f) for f in clearance['terrainFolders']) or \
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
                                     'excludedTerrainTileCount': len(excluded_terrain), 'unionsDecomposed': {k: len(v) for k, v in boxes_by_key.items()}}
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

    def place(self, meshes, poles_no_collision):
        ue = self.ue
        spec = self.spec
        tolerance = spec['verification']['staticBoundsToleranceCm']
        floor = self.find_floor()
        removal = self.find_removal()
        self.receipt['removed'] = [{'label': removal['label'], 'name': removal['name'], 'folder': removal['folder'], 'meshes': removal['meshes'],
                                    'pose': removal['pose'], 'worldBoundsCm': removal['bounds']}]
        local_boxes = {role: info['localBoundsCm'] for role, info in meshes.items()}
        plan = plan_transforms(spec, local_boxes, floor['bounds']['max'][2], poles_no_collision)
        check_rooms(spec, plan)
        self.receipt['plan'] = plan
        excluded = {floor['label'], removal['label']}
        candidates, boxes_by_key = self.clearance_candidates(excluded)
        blockers = {}
        for actor in plan['actors'].values():
            hits = self.blockers_for(actor['plannedWorldBoundsCm'], candidates, boxes_by_key)
            if hits:
                blockers[actor['label']] = hits
        self.receipt['clearance']['blockers'] = blockers
        if blockers:
            raise RuntimeError('Planned altar AABBs intersect existing actors; nothing saved: %s' % blockers)

        # Removal happens in memory only; it persists only if the level is saved at the end.
        if not self.run.actors.destroy_actor(removal['actor']):
            raise RuntimeError('destroy_actor returned False for ' + removal['label'])
        self.receipt['removedCount'] = 1

        records = []
        placed_actors = []
        try:
            for key in ('body', 'poles'):
                actor_plan = plan['actors'][key]
                info = meshes[key]
                tags = ['ReleaseIncenseAltar', key, info['asset'].rsplit('/', 1)[1]]
                actor, component = self.run.spawn_static(info['mesh'], actor_plan['location'], actor_plan['rotation'], actor_plan['label'],
                                                         spec['folder'], actor_plan['collisionProfile'], tags)
                placed_actors.append(actor)
                if actor_plan['collisionProfile'] != 'NoCollision':
                    component.set_collision_enabled(ue.CollisionEnabled.QUERY_AND_PHYSICS)
                actor.set_actor_scale3d(ue.Vector(*actor_plan['scale']))
                pose = self.helper._actor_pose(actor)
                close, error = self.helper._pose_close(pose, actor_plan['location'], actor_plan['rotation'], actor_plan['scale'],
                                                       spec['verification']['transformToleranceCm'])
                if not close:
                    raise RuntimeError('%s pose differs from plan by %.4f' % (actor_plan['label'], error))
                placed_bounds = self.helper._actor_bounds(actor)
                bounds_error = self.helper.box_error(placed_bounds, actor_plan['plannedWorldBoundsCm'])
                if bounds_error > tolerance:
                    raise RuntimeError('%s bounds differ from plan by %.4f: %r' % (actor_plan['label'], bounds_error, placed_bounds))
                profile = str(component.get_collision_profile_name())
                if profile != actor_plan['collisionProfile']:
                    raise RuntimeError('%s collision profile %s differs from plan %s' % (actor_plan['label'], profile, actor_plan['collisionProfile']))
                records.append({'label': actor_plan['label'], 'kind': 'StaticMeshActor', 'role': key, 'mesh': info['asset'],
                                'location': actor_plan['location'], 'rotation': actor_plan['rotation'], 'scale': actor_plan['scale'],
                                'collisionProfile': profile, 'meshCollision': info['meshCollision'],
                                'plannedWorldBoundsCm': actor_plan['plannedWorldBoundsCm'], 'placedWorldBoundsCm': placed_bounds,
                                'boundsErrorCm': bounds_error, 'actor': actor})
        except Exception:
            self.run.destroy_all(placed_actors)
            raise
        return records


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def _strip(record):
    return {k: v for k, v in record.items() if k != 'actor'}


def fresh_receipt_path(spec):
    for _ in range(10):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        path = ROOT / spec['receiptFolder'] / (spec['receiptPrefix'] + stamp + '.json')
        if not path.exists():
            return stamp, path
    raise RuntimeError('Could not allocate a fresh receipt stamp')


def run(import_only=False, allow_unverified_winding=False, place_only=False, poles_no_collision=False):
    """Import (or reuse), collision flag, winding, remove the old study, place. Returns the receipt dict."""
    import unreal as ue
    if import_only and place_only:
        raise RuntimeError('-AltarImportOnly and -AltarPlaceOnly are mutually exclusive')
    spec = load_spec()
    helper = load_placement_helper(spec)
    offline = offline_check(spec, namespace_expected=place_only, poles_no_collision=poles_no_collision)
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
        raise RuntimeError('Existing native namespace preserved (use -AltarPlaceOnly): ' + spec['source']['namespace'])

    stamp, receipt_path = fresh_receipt_path(spec)
    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(helper.disk_path(m, 'umap')) for m in spec['protectedMaps'] if helper.disk_path(m, 'umap').exists()}
    receipt = {
        'status': 'started', 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'mapMatchesLastKnown': map_sha_before == spec['lastKnownMapSha256'], 'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'manifestSha256': offline['manifestSha256'],
        'engineVersion': ue.SystemLibrary.get_engine_version(), 'offlineCheck': offline,
        'switches': {'importOnly': import_only, 'placeOnly': place_only, 'allowUnverifiedWinding': allow_unverified_winding, 'polesNoCollision': poles_no_collision},
        'mode': 'place_only_reusing_saved_meshes' if place_only else 'import_and_place',
        'materials': {}, 'meshes': {}, 'windingCheck': {}, 'windingFlips': {}, 'removed': [], 'placed': [], 'errors': [],
        'mapSaved': False, 'collision': spec['collision'], 'corridor': offline['plan']['corridor'],
        'limitations': list(spec['limitations']),
    }

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()

    saved = False
    try:
        # -- 1. import + materials + collision flag (or reuse the saved meshes) ----------------
        meshes = {}
        material = None if place_only else pick_material(ue, spec, receipt)
        for record in spec['source']['meshes']:
            mesh, info = load_saved_mesh(ue, spec, record, receipt) if place_only else import_one_mesh(ue, spec, record, material)
            info['mesh'] = mesh
            meshes[record['role']] = info
            receipt['meshes'][record['name']] = {k: v for k, v in info.items() if k != 'mesh'}
            write()
        receipt['status'] = 'meshes_verified' if place_only else 'meshes_saved'

        # -- 2. winding (flip if inverted) ---------------------------------------------------
        all_passed = True
        for record in spec['source']['meshes']:
            info = meshes[record['role']]
            report = winding_report(ue, info['mesh'], record, spec)
            if report['status'] == 'checked' and report['signedVolumeUEcm3'] is not None and report['signedVolumeUEcm3'] < 0 and spec['windingCheck']['flipIfNegative']:
                flip = flip_winding(ue, info['mesh'], spec)
                flip['before'] = report
                report = winding_report(ue, info['mesh'], record, spec)
                flip['after'] = report
                info['localBoundsCm'] = _static_mesh_box(info['mesh'])
                info['triangles'] = info['mesh'].get_num_triangles(0)
                info['meshCollision'] = flip['meshCollision']
                info['uassetSha256'] = _uasset_sha(info['mesh'])
                receipt['meshes'][record['name']].update({k: v for k, v in info.items() if k != 'mesh'})
                receipt['windingFlips'][info['asset']] = flip
                receipt['limitations'].append('%s imported inside-out (negative UE signed volume); triangle order reversed via GeometryScript' % info['asset'])
            receipt['windingCheck'][info['asset']] = report
            all_passed = all_passed and report['passed']
        receipt['windingVerifiedOutward'] = all_passed
        write()
        if import_only:
            receipt['status'] = 'meshes_saved_import_only_no_map_change'
            return receipt
        if not all_passed and spec['windingCheck']['requireForPlacement'] and not allow_unverified_winding:
            receipt['status'] = 'meshes_saved_placement_skipped_winding_unverified'
            receipt['limitations'].append('Placement skipped: winding check did not pass or was unavailable; rerun with -EnablePlugins=GeometryScripting '
                                          '(and -AltarPlaceOnly) or inspect before -AltarAllowUnverifiedWinding')
            return receipt
        if not all_passed:
            receipt['limitations'].append('Placed with UNVERIFIED winding by explicit switch')

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
        own_labels = {spec['placement']['bodyLabel'], spec['placement']['polesLabel']}
        clashes = [r['label'] for r in run_state.snapshot if r['label'] in own_labels or r['label'].startswith('RELEASE_IncenseAltar')]
        if clashes:
            raise RuntimeError('Existing altar release actors preserved; refusing duplicate placement: %s' % clashes[:10])
        receipt['preExistingReleaseActors'] = [{'label': r['label'], 'folder': r['folder'], 'meshes': r['meshes']} for r in run_state.snapshot if r['label'].startswith(spec['labelPrefix'])]
        receipt['actorCountBefore'] = len(run_state.snapshot)
        write()

        # -- 4. remove, place, save, reopen, read back ------------------------------------
        placement = AltarPlacement(ue, spec, helper, run_state, receipt)
        records = placement.place(meshes, poles_no_collision)
        receipt['placed'] = [_strip(r) for r in records]
        write()
        removed_names = {r['name'] for r in receipt['removed']}
        current = run_state.numeric_baseline(run_state.take_snapshot())
        changed = [name for name, row in baseline.items() if name not in removed_names and current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:10])
        if [name for name in removed_names if name in current]:
            raise RuntimeError('Removed actor still present before save')
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
        changed = [name for name, row in baseline.items() if name not in removed_names and reopened_numeric.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors differ after reopen: %s' % changed[:10])
        removed_labels = {r['label'] for r in receipt['removed']}
        if [r['label'] for r in reopened if r['label'] in removed_labels]:
            raise RuntimeError('Removed actor reappeared after reopen')
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
            mesh = component.get_editor_property('static_mesh')
            entry = {'label': record['label'], 'folder': row['folder'], 'meshPath': row['meshes'], 'pose': row['pose'], 'worldBoundsCm': row['bounds'],
                     'poseErrorCm': error, 'boundsErrorCm': bounds_error, 'collisionProfile': str(component.get_collision_profile_name()),
                     'collisionEnabled': str(component.get_collision_enabled()), 'meshCollision': mesh_collision_state(ue, mesh),
                     'materials': [_asset_path(component.get_material(i)) for i in range(component.get_num_materials())]}
            readback.append(entry)
            if row['meshes'] != [record['mesh']]:
                raise RuntimeError('Reopened mesh differs for ' + record['label'])
            if not close or bounds_error > verify['staticBoundsToleranceCm']:
                raise RuntimeError('Reopened transform/bounds differ for %s (pose %.4f, bounds %.4f)' % (record['label'], error, bounds_error))
            if entry['collisionProfile'] != record['collisionProfile']:
                raise RuntimeError('Reopened collision profile differs for ' + record['label'])
            if record['collisionProfile'] != 'NoCollision' and spec['collision']['traceFlag'] not in (entry['meshCollision']['collisionTraceFlag'] or ''):
                raise RuntimeError('Reopened mesh lost the complex-as-simple trace flag: ' + record['label'])
        receipt['reopenedReadback'] = readback
        receipt['actorCountAfter'] = len(reopened)
        receipt['status'] = 'altar_saved_reopened_old_study_removed_visual_and_walk_acceptance_pending'
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
        receipt['removedActorCount'] = len(receipt['removed'])
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
    return 'release_import_incense_altar.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    tokens = command_line.split()
    try:
        receipt = run(import_only='-altarimportonly' in tokens, allow_unverified_winding='-altarallowunverifiedwinding' in tokens,
                      place_only='-altarplaceonly' in tokens, poles_no_collision='-altarpolesnocollision' in tokens)
        ue.log('release_import_incense_altar: %s placed %s removed %s winding_ok %s' % (
            receipt['status'], receipt.get('placedActorCount'), receipt.get('removedActorCount'), receipt.get('windingVerifiedOutward')))
    except Exception as error:
        ue.log_error('release_import_incense_altar failed: ' + repr(error))
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
