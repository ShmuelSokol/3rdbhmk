"""Guarded native import of the original MenorahV3 assembly (hex plinth, shaft, six branches in two
meshes, 42 ornaments, seven lamps, three-step tending stone) and its placement in the combined map,
replacing the CC BY Titus-style RELEASE_Menorah (Dahan Meir) at X -5330 in the south of the Heikhal.

What it does, in order (every number comes from Scripts/release_import_menorah_v3.spec.json, filled
from SourceAssets/vessels-review/MenorahV3/geometry-manifest.json and the vessels receipt):

  1. Guards: right project, no game world, no dirty packages, target namespace
     /Game/MikdashV3/MaterialReview/MenorahV3 absent (or present for -MenorahPlaceOnly), the seven
     frozen OBJ hashes and the manifest status intact.
  2. Materials: the EXISTING gold material (first candidate on disk: M_AronStudyV3_Gold, else
     M_HeikhalKeilim_Gold) goes to every slot of the six gold parts. The step stone gets the first
     existing stone candidate (MI_PBR_LimestoneTrim, ...); only if none exists is M_MenorahV3_Stone
     created inside the namespace (duplicate of the gold material with matte constants). Recorded.
  3. Imports the seven OBJ parts through the reviewed legacy OBJ adapter path (FbxFactory, same
     settings as the keilim/reliefs/doors/vessels/shulchan imports, build_nanite False;
     auto_generate_collision True ONLY for Base and StepStone, which are BlockAll). The files carry Y
     reflected and winding reversed; the importer reflects Y back, so the imported bounds must equal
     the manifest's canonical bounds (tolerance 0.05 cm) and triangle counts must match exactly.
  4. Winding check (GeometryScript, needs -EnablePlugins=GeometryScripting): signed volume under UE's
     left-handed face-normal convention must be positive for every mesh; a negative mesh is flipped
     (append_buffers_to_mesh + copy_mesh_to_static_mesh), re-saved, re-checked and recorded. Without a
     passing check nothing is placed (override -MenorahAllowUnverifiedWinding, recorded).
  5. Loads /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough, refuses if any RELEASE_MenorahV3_*
     actor or the Release/MenorahV3 folder exists, checkpoints the .umap to
     C:/Mikdash/Working-5.8/ReviewCheckpoints/MenorahV3-<stamp>/, finds EXACTLY the old RELEASE_Menorah
     (label, folder, mesh, pose as recorded in native-import-vessels-20260907T190204035803Z.json),
     reads the Heikhal floor, plans one world AABB per part at the shared origin
     [-5330, 500 - 125 - halfSpan, floorTop] yaw -90 (lamp row north-south, local +Y = east), so the
     nearest lamp tip is 125 cm (2.5 amot, book p. 252) from the south wall face Y +500; checks that the
     stone lies east of the plinth and every AABB inside the Heikhal envelope.
  6. Clearance against every other mesh-bearing actor (release_place_assets rules, hollow unions
     decomposed), destroys the old RELEASE_Menorah (pose recorded; the CC BY asset stays on disk), spawns
     RELEASE_MenorahV3_<Part> (BlockAll on Base and StepStone, NoCollision elsewhere, tag
     ReleaseMenorahV3), saves, reopens, reads back numerically and writes
     SourceAssets/vessels-review/MenorahV3/native-import-<stamp>.json (at start and in finally).

Commandlet invocation (serial; never while another native job is running; editor closed):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_import_menorah_v3.py"
      -EnablePlugins=GeometryScripting -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-MenorahV3-01.log"

Optional switches (read from the engine command line):
  -MenorahImportOnly               import + materials + winding check, no map change.
  -MenorahPlaceOnly                skip the import; the seven meshes must already exist (re-verified).
  -MenorahAllowUnverifiedWinding   place even if the winding check is unavailable/failed.

Offline (no engine):  python Scripts/release_import_menorah_v3.py  -> prints offline_check(): hashes,
manifest consistency, materials on disk, the planned world AABBs and the south-wall verdict per part.
"""
import hashlib
import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_import_menorah_v3.spec.json'
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
    path = ROOT / spec['placementHelper']
    module_spec = importlib.util.spec_from_file_location('release_place_assets', path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    for name in ('sha256_of', 'disk_path', 'box_from_min_max', 'box_error', 'rotate_box_yaw',
                 'boxes_overlap_volume', 'verify_union_decomposition', 'Placement', '_pose_close', '_actor_bounds', '_actor_pose'):
        if not hasattr(module, name):
            raise RuntimeError('release_place_assets.py lacks helper ' + name)
    return module


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def box_inside(inner, outer, tolerance=0.0):
    return all(inner['min'][i] >= outer['min'][i] - tolerance and inner['max'][i] <= outer['max'][i] + tolerance for i in range(3))


def parse_obj(path):
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


def plan_parts(spec, helper, local_boxes, floor_top):
    """Shared transform for all seven parts from the imported local boxes; south-wall and stone verdicts.

    local_boxes: {meshName: canonical local box} (manifest offline, imported asset natively).
    """
    placement = spec['placement']
    source = spec['source']
    yaw = float(placement['yaw'])
    half_span = max(max(-local_boxes[n]['min'][0], local_boxes[n]['max'][0]) for n in source['menorahParts'])
    y = float(placement['southWallY']) - float(placement['nearestTipClearanceCm']) - half_span
    min_z = min(local_boxes[n]['min'][2] for n in local_boxes)
    origin = [float(placement['x']), y, floor_top - min_z]
    parts = {}
    for record in source['meshes']:
        name = record['name']
        world = helper.rotate_box_yaw(local_boxes[name], origin, yaw)
        parts[name] = {'label': placement['labelPrefix'] + record['part'], 'part': record['part'], 'role': record['role'],
                       'collisionProfile': record['collisionProfile'], 'location': origin, 'rotation': [0.0, yaw, 0.0], 'scale': [1.0, 1.0, 1.0],
                       'plannedWorldBoundsCm': world, 'southWallClearanceCm': float(placement['southWallY']) - world['max'][1]}
    menorah_union = {'min': [min(parts[n]['plannedWorldBoundsCm']['min'][i] for n in source['menorahParts']) for i in range(3)],
                     'max': [max(parts[n]['plannedWorldBoundsCm']['max'][i] for n in source['menorahParts']) for i in range(3)]}
    nearest_tip = float(placement['southWallY']) - menorah_union['max'][1]
    if abs(nearest_tip - float(placement['nearestTipClearanceCm'])) > 1e-6:
        raise RuntimeError('Nearest-tip clearance arithmetic failed: %.4f' % nearest_tip)
    for name, part in parts.items():
        if part['southWallClearanceCm'] < float(placement['nearestTipClearanceCm']) - 1e-6:
            raise RuntimeError('%s would come closer than %.0f cm to the south wall' % (name, placement['nearestTipClearanceCm']))
    base = parts['SM_MenorahV3_Base']['plannedWorldBoundsCm']
    stone = parts[source['stonePart']]['plannedWorldBoundsCm']
    stone_gap = stone['min'][0] - base['max'][0]
    if stone_gap <= 0:
        raise RuntimeError('Stone is not east of the plinth (gap %.3f cm)' % stone_gap)
    if abs(menorah_union['min'][2] - floor_top) > 1e-6 or abs(stone['min'][2] - floor_top) > 1e-6:
        raise RuntimeError('Plinth or stone is not on the floor')
    envelope = placement['roomEnvelope']
    for name, part in parts.items():
        if not box_inside(part['plannedWorldBoundsCm'], envelope):
            raise RuntimeError('%s planned AABB leaves the Heikhal envelope: %r' % (name, part['plannedWorldBoundsCm']))
    union = {'min': [min(p['plannedWorldBoundsCm']['min'][i] for p in parts.values()) for i in range(3)],
             'max': [max(p['plannedWorldBoundsCm']['max'][i] for p in parts.values()) for i in range(3)]}
    return {'origin': origin, 'yaw': yaw, 'halfSpanCm': half_span, 'parts': parts, 'placedParts': list(parts),
            'menorahWorldBoundsCm': menorah_union, 'nearestTipToSouthWallCm': nearest_tip,
            'menorahHeightCm': menorah_union['max'][2] - menorah_union['min'][2],
            'menorahRowSpanCm': menorah_union['max'][1] - menorah_union['min'][1],
            'stoneEastGapFromPlinthCm': stone_gap, 'assemblyWorldBoundsCm': union,
            'orientation': 'lamp row north-south (Rambam 3:12), tending stone east (Rambam 3:11)'}


def offline_check(spec=None, namespace_expected=None, parse_faces=True):
    """Consistency checks that need no engine. Raises on the first failure."""
    spec = spec or load_spec()
    helper = load_placement_helper(spec)
    source = spec['source']
    report = {'sourceFiles': [], 'materialsOnDisk': {}}
    manifest_path = ROOT / source['manifest']
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['status'] != source['manifestStatusRequired']:
        raise RuntimeError('Manifest status ' + manifest['status'])
    if manifest['namespace'] != source['namespace']:
        raise RuntimeError('Manifest namespace differs from spec')
    if sha256_of(manifest_path) != source['manifestSha256']:
        raise RuntimeError('geometry-manifest.json changed after the spec was prepared')
    if manifest['script_sha256'] != source['authoringScriptSha256']:
        raise RuntimeError('Authoring script hash in the manifest differs from the spec')
    by_name = {m['name']: m for m in manifest['meshes']}
    if set(by_name) != {m['name'] for m in source['meshes']}:
        raise RuntimeError('Spec mesh set differs from the manifest')
    contract = manifest['count_contract']
    counts = manifest['counts']
    if (counts.get('goblet'), counts.get('knop'), counts.get('flower'), counts.get('lamp'), counts.get('branch')) != \
            (contract['goblets_total'], contract['knops_total'], contract['flowers_total'], contract['lamps'], contract['side_branches']):
        raise RuntimeError('Manifest ornament counts do not meet the count contract: %r' % counts)
    report['ornamentCounts'] = counts
    local_boxes = {}
    for record in source['meshes']:
        entry = by_name[record['name']]
        path = ROOT / source['folder'] / record['file']
        actual_sha = sha256_of(path)
        if actual_sha != record['sha256'] or entry['sha256'] != record['sha256']:
            raise RuntimeError('Frozen OBJ hash differs for ' + record['name'])
        if entry['triangles'] != record['triangles']:
            raise RuntimeError('Triangle count differs from manifest for ' + record['name'])
        if helper.box_error(entry['bounds_cm'], record['canonicalBoundsCm']) > 1e-6:
            raise RuntimeError('Canonical bounds differ from manifest for ' + record['name'])
        if entry['material_role'] != record['role'] or entry['collision'] != record['collisionProfile']:
            raise RuntimeError('Material role or collision differs from manifest for ' + record['name'])
        row = {'name': record['name'], 'part': record['part'], 'role': record['role'], 'collisionProfile': record['collisionProfile'],
               'sha256': actual_sha, 'triangles': record['triangles']}
        if parse_faces:
            vertices, faces = parse_obj(path)
            if len(faces) != record['triangles']:
                raise RuntimeError('%s parsed %d triangles, spec %d' % (record['name'], len(faces), record['triangles']))
            reflected = {'min': [min(v[0] for v in vertices), -max(v[1] for v in vertices), min(v[2] for v in vertices)],
                         'max': [max(v[0] for v in vertices), -min(v[1] for v in vertices), max(v[2] for v in vertices)]}
            if helper.box_error(reflected, record['canonicalBoundsCm']) > 1e-4:
                raise RuntimeError('%s file bounds (Y reflected) differ from the canonical bounds' % record['name'])
            row['fileRightHandedSignedVolumeCm3'] = right_handed_signed_volume(vertices, faces)
            if row['fileRightHandedSignedVolumeCm3'] <= 0:
                raise RuntimeError('%s file-space signed volume is not positive' % record['name'])
        local_boxes[record['name']] = record['canonicalBoundsCm']
        report['sourceFiles'].append(row)
    if sum(r['triangles'] for r in source['meshes']) != manifest['total_triangles'] or manifest['total_triangles'] >= source['maxTotalTriangles']:
        raise RuntimeError('Total triangle count inconsistent or over budget')

    namespace_dir = ROOT / 'Content' / source['namespace'][len('/Game/'):]
    report['namespaceFolderExistsOnDisk'] = namespace_dir.exists()
    report['savedMeshFilesOnDisk'] = {m['name']: (namespace_dir / 'Meshes' / (m['name'] + '.uasset')).exists() for m in source['meshes']}
    if namespace_expected is False and namespace_dir.exists():
        raise RuntimeError('Target namespace folder already exists on disk: ' + str(namespace_dir))
    if namespace_expected is True and not all(report['savedMeshFilesOnDisk'].values()):
        raise RuntimeError('Place-only needs all seven saved meshes on disk: %r' % report['savedMeshFilesOnDisk'])

    for role in ('gold', 'stone'):
        rows = [{'path': c['path'], 'kind': c['kind'], 'onDisk': helper.disk_path(c['path']).exists()} for c in spec['materials'][role]['candidates']]
        report['materialsOnDisk'][role] = rows
    if not any(r['onDisk'] for r in report['materialsOnDisk']['gold']):
        raise RuntimeError('No gold material candidate exists on disk')
    stone = spec['materials']['stone']
    report['stoneMaterialPlan'] = ('reuse existing candidate' if any(r['onDisk'] for r in report['materialsOnDisk']['stone'])
                                  else 'create %s by duplicating %s' % (stone['createPath'], stone['duplicateFrom']))
    if not helper.disk_path(stone['duplicateFrom']).exists():
        raise RuntimeError('Stone duplicate source missing on disk: ' + stone['duplicateFrom'])
    if not (ROOT / spec['targetMapFile']).exists():
        raise RuntimeError('Target map file missing')
    report['mapSha256OnDisk'] = sha256_of(ROOT / spec['targetMapFile'])
    report['mapMatchesLastKnown'] = report['mapSha256OnDisk'] == spec['lastKnownMapSha256']
    if spec['removal']['location'][0] != spec['placement']['x']:
        raise RuntimeError('Removal X and placement X disagree; the new assembly replaces the menorah on the same east-west line')
    report['plan'] = plan_parts(spec, helper, local_boxes, spec['placement']['floor']['topZ'])
    report['status'] = 'offline_spec_consistent'
    return report


# --------------------------------------------------------------------------
# Engine side: materials, import, winding
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


def _uasset_sha(asset):
    return sha256_of(ROOT / 'Content' / (_asset_path(asset)[len('/Game/'):] + '.uasset'))


def _simple_collision_summary(ue, mesh):
    """Best-effort readback of importer-generated simple collision; never a guard (API shape varies)."""
    try:
        body = mesh.get_editor_property('body_setup')
        if body is None:
            return {'available': False, 'reason': 'no body_setup'}
        agg = body.get_editor_property('agg_geom')
        summary = {'available': True}
        for key in ('box_elems', 'sphere_elems', 'sphyl_elems', 'convex_elems'):
            try:
                summary[key] = len(agg.get_editor_property(key))
            except Exception as error:  # noqa: BLE001
                summary[key] = 'unreadable: %r' % error
        return summary
    except Exception as error:  # noqa: BLE001
        return {'available': False, 'reason': repr(error)}


def pick_material(ue, spec, role, receipt):
    """First existing MaterialInterface among the role's candidates; None if none exists."""
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tried = []
    for position, candidate in enumerate(spec['materials'][role]['candidates']):
        exists = assets.does_asset_exist(candidate['path'])
        material = ue.load_asset(candidate['path']) if exists else None
        ok = isinstance(material, ue.MaterialInterface)
        tried.append({'path': candidate['path'], 'kind': candidate['kind'], 'exists': bool(exists), 'loaded': ok})
        if ok:
            if position > 0:
                receipt['limitations'].append('%s material fell back to %s (%s)' % (role, candidate['path'], candidate['kind']))
            receipt['materials'][role] = {'assigned': candidate['path'], 'kind': candidate['kind'], 'tried': tried, 'created': False}
            return material
    receipt['materials'][role] = {'assigned': None, 'tried': tried, 'created': False}
    return None


def _wire_constants(ue, material, colour, metallic, roughness):
    ml = ue.MaterialEditingLibrary
    node = ml.create_material_expression(material, ue.MaterialExpressionConstant3Vector, -400, 200)
    node.set_editor_property('constant', ue.LinearColor(colour[0], colour[1], colour[2], 1.0))
    if not ml.connect_material_property(node, '', ue.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('BaseColor connection failed')
    for value, prop in ((metallic, ue.MaterialProperty.MP_METALLIC), (roughness, ue.MaterialProperty.MP_ROUGHNESS)):
        const = ml.create_material_expression(material, ue.MaterialExpressionConstant, -400, 400 if prop == ue.MaterialProperty.MP_METALLIC else 500)
        const.set_editor_property('r', value)
        if not ml.connect_material_property(const, '', prop):
            raise RuntimeError('Constant connection failed for %s' % prop)
    ml.recompile_material(material)


def stone_material(ue, spec, receipt):
    """Existing stone candidate, else a matte constant material duplicated from the gold one."""
    existing = pick_material(ue, spec, 'stone', receipt)
    if existing is not None:
        return existing
    stone = spec['materials']['stone']
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if assets.does_asset_exist(stone['createPath']):
        material = ue.load_asset(stone['createPath'])
        if not isinstance(material, ue.MaterialInterface):
            raise RuntimeError('Existing stone asset is not a material: ' + stone['createPath'])
        receipt['materials']['stone'].update({'assigned': stone['createPath'], 'kind': 'stone_constant_reused', 'created': False})
        return material
    method = None
    material = None
    try:
        duplicated = assets.duplicate_asset(stone['duplicateFrom'], stone['createPath'])
        if isinstance(duplicated, ue.Material):
            material = duplicated
            method = 'duplicate_asset(%s) + rewired constants' % stone['duplicateFrom']
    except Exception as error:  # noqa: BLE001
        receipt['limitations'].append('duplicate_asset failed for the stone material: %r' % error)
    if material is None:
        folder, name = stone['createPath'].rsplit('/', 1)
        material = ue.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, ue.Material, ue.MaterialFactoryNew())
        if not isinstance(material, ue.Material):
            raise RuntimeError('Stone material creation failed')
        method = 'MaterialFactoryNew (create_heikhal_keilim recipe)'
    c = stone['constants']
    _wire_constants(ue, material, c['baseColor'], c['metallic'], c['roughness'])
    if not assets.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for the stone material')
    receipt['materials']['stone'].update({'assigned': _asset_path(material), 'kind': 'stone_constant_created', 'created': True,
                                          'method': method, 'constants': c, 'uassetSha256': _uasset_sha(material)})
    receipt['created'].append(_asset_path(material))
    return material


def verify_mesh_geometry(spec, record, box, triangles):
    tolerance = spec['source']['boundsToleranceCm']
    error = max(abs(box[k][i] - record['canonicalBoundsCm'][k][i]) for k in ('min', 'max') for i in range(3))
    plain = {'min': [record['canonicalBoundsCm']['min'][0], -record['canonicalBoundsCm']['max'][1], record['canonicalBoundsCm']['min'][2]],
             'max': [record['canonicalBoundsCm']['max'][0], -record['canonicalBoundsCm']['min'][1], record['canonicalBoundsCm']['max'][2]]}
    error_unreflected = max(abs(box[k][i] - plain[k][i]) for k in ('min', 'max') for i in range(3))
    if error > tolerance:
        raise RuntimeError('%s imported bounds differ from the canonical bounds by %.4f cm (unreflected error %.4f): %r'
                           % (record['name'], error, error_unreflected, box))
    if triangles != record['triangles']:
        raise RuntimeError('%s imported %d triangles, manifest %d' % (record['name'], triangles, record['triangles']))
    return {'boundsErrorCm': error, 'boundsErrorIfImporterHadNotReflectedY': error_unreflected,
            'importerReflectedYAsExpected': error <= tolerance,
            'ambiguousReflection': error_unreflected <= tolerance}


def import_one_mesh(ue, spec, record, material):
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
        if key == 'auto_generate_collision':
            value = bool(record.get('autoGenerateCollision', False))
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
        raise RuntimeError('Imported name %s differs from %s' % (mesh.get_name(), record['name']))
    box = _static_mesh_box(mesh)
    triangles = mesh.get_num_triangles(0)
    geometry = verify_mesh_geometry(spec, record, box, triangles)
    slots = len(mesh.get_editor_property('static_materials'))
    for slot in range(slots):
        mesh.set_material(slot, material)
    not_assigned = [slot for slot in range(slots) if _asset_path(mesh.get_material(slot)) != _asset_path(material)]
    if slots == 0 or not_assigned:
        raise RuntimeError('Material slots not assigned on %s: %s of %d' % (record['name'], not_assigned, slots))
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + record['name'])
    info = {'asset': _asset_path(mesh), 'file': str(path), 'triangles': triangles, 'vertices': mesh.get_num_vertices(0),
            'localBoundsCm': box, 'materialSlots': slots, 'material': _asset_path(material), 'role': record['role'],
            'collisionProfile': record['collisionProfile'], 'autoGenerateCollision': bool(record.get('autoGenerateCollision', False)),
            'simpleCollision': _simple_collision_summary(ue, mesh),
            'importSeconds': seconds, 'buildNanite': False, 'uassetSha256': _uasset_sha(mesh)}
    info.update(geometry)
    return mesh, info


def load_saved_mesh(ue, spec, record, receipt):
    asset_path = spec['source']['meshFolder'] + '/' + record['name']
    mesh = ue.load_asset(asset_path)
    if not isinstance(mesh, ue.StaticMesh):
        raise RuntimeError('Saved mesh missing or not a StaticMesh: ' + asset_path)
    box = _static_mesh_box(mesh)
    triangles = mesh.get_num_triangles(0)
    geometry = verify_mesh_geometry(spec, record, box, triangles)
    allowed = {c['path'] for c in spec['materials'][record['role']]['candidates']}
    if record['role'] == 'stone':
        allowed.add(spec['materials']['stone']['createPath'])
    slots = len(mesh.get_editor_property('static_materials'))
    assigned = {_asset_path(mesh.get_material(slot)) for slot in range(slots)}
    wrong = sorted(str(p) for p in assigned if p not in allowed)
    if slots == 0 or wrong or len(assigned) != 1:
        raise RuntimeError('%s has %d slots; materials %s (outside spec: %s)' % (record['name'], slots, sorted(map(str, assigned)), wrong))
    material_path = assigned.pop()
    receipt['materials'].setdefault(record['role'], {'assigned': material_path, 'verifiedOnSavedMesh': True})
    info = {'asset': _asset_path(mesh), 'file': None, 'triangles': triangles, 'vertices': mesh.get_num_vertices(0),
            'localBoundsCm': box, 'materialSlots': slots, 'material': material_path, 'role': record['role'],
            'collisionProfile': record['collisionProfile'], 'simpleCollision': _simple_collision_summary(ue, mesh), 'reused': True,
            'uassetSha256': _uasset_sha(mesh)}
    info.update(geometry)
    return mesh, info


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
    except Exception:  # noqa: BLE001 - API shape differs between builds; per-triangle loop is the fallback
        return None
    if len(triangles) != dynamic.get_triangle_count() or len(positions) < dynamic.get_vertex_count():
        return None
    return positions, triangles


def winding_report(ue, mesh, spec):
    """Signed volume under UE's left-handed face-normal convention; positive means outward faces."""
    check = spec['windingCheck']
    if not all(hasattr(ue, n) for n in ('GeometryScript_AssetUtils', 'GeometryScript_MeshQueries')):
        return {'status': 'unavailable', 'passed': False, 'signedVolumeUEcm3': None,
                'reason': 'GeometryScripting not loaded; launch with -EnablePlugins=GeometryScripting'}
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
    passed = signed_volume > 0 and disagreements == 0 and sampled > 0
    return {'status': 'checked', 'passed': passed, 'method': method, 'triangles': count, 'signedVolumeUEcm3': signed_volume,
            'faceNormalSamples': sampled, 'faceNormalVsCrossDisagreements': disagreements,
            'passCriterion': 'signedVolumeUEcm3 > 0 and faceNormalVsCrossDisagreements == 0',
            'convention': 'UE left-handed face normal cross(C-A, B-A); divergence-theorem volume in asset cm'}


def flip_winding(ue, mesh, spec):
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
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed after winding flip for ' + mesh.get_name())
    return {'method': method, 'rewriteOptions': check['rewriteOptions'], 'triangles': rebuilt.get_triangle_count()}


# --------------------------------------------------------------------------
# Engine side: removal and placement
# --------------------------------------------------------------------------

class MenorahPlacement:
    def __init__(self, ue, spec, helper, run, receipt):
        self.ue = ue
        self.spec = spec
        self.helper = helper
        self.run = run
        self.receipt = receipt

    def find_floor(self):
        floor_spec = self.spec['placement']['floor']
        rows = self.run.actors_with_mesh(floor_spec['mesh'])
        if len(rows) != 1:
            raise RuntimeError('Expected one Heikhal clear floor actor, found %d' % len(rows))
        floor = rows[0]
        if self.helper.box_error(floor['bounds'], floor_spec['worldBoundsCm']) > floor_spec['boundsToleranceCm']:
            raise RuntimeError('Heikhal floor bounds differ from manifest: %r' % floor['bounds'])
        if abs(floor['bounds']['max'][2] - floor_spec['topZ']) > floor_spec['topToleranceCm']:
            raise RuntimeError('Heikhal floor top %.3f differs from spec %.3f' % (floor['bounds']['max'][2], floor_spec['topZ']))
        return floor

    def find_removal(self):
        removal = self.spec['removal']
        rows = [r for r in self.run.snapshot if r['label'] == removal['label']]
        if len(rows) != 1:
            raise RuntimeError('Removal target %s: %d actors with that label' % (removal['label'], len(rows)))
        row = rows[0]
        if row['meshes'] != [removal['mesh']]:
            raise RuntimeError('Removal target carries mesh %s, expected %s' % (row['meshes'], removal['mesh']))
        if row['folder'] != removal['folder']:
            raise RuntimeError('Removal target is in folder %s, expected %s' % (row['folder'], removal['folder']))
        close, error = self.helper._pose_close(row['pose'], removal['location'], [0.0, removal['yaw'], 0.0], removal['scale'], removal['poseToleranceCm'])
        if not close:
            raise RuntimeError('Removal target pose differs from the recorded pose by %.4f' % error)
        others = [r['label'] for r in self.run.snapshot if r['meshes'] == [removal['mesh']] and r['label'] != removal['label']]
        if others:
            raise RuntimeError('Unexpected extra actors carrying the CC BY menorah mesh: %s' % others[:10])
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
                                     'excludedTerrainTileCount': len(excluded_terrain),
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
        ue = self.ue
        spec = self.spec
        tolerance = spec['verification']['staticBoundsToleranceCm']
        floor = self.find_floor()
        removal = self.find_removal()
        self.receipt['removed'] = [{'label': removal['label'], 'name': removal['name'], 'folder': removal['folder'], 'meshes': removal['meshes'],
                                    'pose': removal['pose'], 'worldBoundsCm': removal['bounds'],
                                    'note': spec['removal']['assetsLeftInPlace']}]
        local_boxes = {name: info['localBoundsCm'] for name, info in meshes.items()}
        plan = plan_parts(spec, self.helper, local_boxes, floor['bounds']['max'][2])
        self.receipt['plan'] = plan
        self.receipt['southWallGuard'] = {'southWallFaceY': spec['placement']['southWallY'],
                                          'nearestTipClearanceCm': plan['nearestTipToSouthWallCm'],
                                          'perPart': {n: p['southWallClearanceCm'] for n, p in plan['parts'].items()}}
        excluded = {floor['label'], removal['label']}
        candidates, boxes_by_key = self.clearance_candidates(excluded)
        blockers = {}
        for name in plan['placedParts']:
            hits = self.blockers_for(plan['parts'][name]['plannedWorldBoundsCm'], candidates, boxes_by_key)
            if hits:
                blockers[plan['parts'][name]['label']] = hits
        self.receipt['clearance']['blockers'] = blockers
        if blockers:
            raise RuntimeError('Planned part AABBs intersect existing actors; nothing saved: %s' % blockers)

        if not self.run.actors.destroy_actor(removal['actor']):
            raise RuntimeError('destroy_actor returned False for ' + removal['label'])
        self.receipt['removedCount'] = 1

        records = []
        placed_actors = []
        try:
            for name in plan['placedParts']:
                part = plan['parts'][name]
                info = meshes[name]
                tags = ['ReleaseMenorahV3', part['role'], name]
                actor, component = self.run.spawn_static(info['mesh'], part['location'], part['rotation'], part['label'],
                                                         spec['folder'], part['collisionProfile'], tags)
                placed_actors.append(actor)
                pose = self.helper._actor_pose(actor)
                close, error = self.helper._pose_close(pose, part['location'], part['rotation'], part['scale'], spec['verification']['transformToleranceCm'])
                if not close:
                    raise RuntimeError('%s pose differs from plan by %.4f' % (part['label'], error))
                placed_bounds = self.helper._actor_bounds(actor)
                bounds_error = self.helper.box_error(placed_bounds, part['plannedWorldBoundsCm'])
                if bounds_error > tolerance:
                    raise RuntimeError('%s bounds differ from plan by %.4f: %r' % (part['label'], bounds_error, placed_bounds))
                profile = str(component.get_collision_profile_name())
                if profile != part['collisionProfile']:
                    raise RuntimeError('%s collision profile %s, expected %s' % (part['label'], profile, part['collisionProfile']))
                records.append({'label': part['label'], 'kind': 'StaticMeshActor', 'part': part['part'], 'role': part['role'], 'mesh': info['asset'],
                                'location': part['location'], 'rotation': part['rotation'], 'scale': part['scale'],
                                'collisionProfile': part['collisionProfile'], 'plannedWorldBoundsCm': part['plannedWorldBoundsCm'],
                                'placedWorldBoundsCm': placed_bounds, 'boundsErrorCm': bounds_error,
                                'southWallClearanceCm': part['southWallClearanceCm'], 'actor': actor})
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


def run(import_only=False, allow_unverified_winding=False, place_only=False):
    import unreal as ue
    if import_only and place_only:
        raise RuntimeError('-MenorahImportOnly and -MenorahPlaceOnly are mutually exclusive')
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
        raise RuntimeError('Existing native namespace preserved (use -MenorahPlaceOnly): ' + spec['source']['namespace'])

    stamp, receipt_path = fresh_receipt_path(spec)
    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(helper.disk_path(m, 'umap')) for m in spec['protectedMaps'] if helper.disk_path(m, 'umap').exists()}
    receipt = {
        'status': 'started', 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'mapMatchesLastKnown': map_sha_before == spec['lastKnownMapSha256'], 'protectedMapSha256Before': protected,
        'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH), 'engineVersion': ue.SystemLibrary.get_engine_version(),
        'offlineCheck': offline,
        'switches': {'importOnly': import_only, 'placeOnly': place_only, 'allowUnverifiedWinding': allow_unverified_winding},
        'mode': 'place_only_reusing_saved_meshes' if place_only else 'import_and_place',
        'materials': {}, 'created': [], 'meshes': {}, 'windingCheck': {}, 'windingFlips': {}, 'removed': [], 'placed': [], 'errors': [],
        'mapSaved': False, 'collisionNote': spec['collisionNote'],
        'limitations': list(spec['limitations']),
    }

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()

    saved = False
    try:
        # -- 1. materials + import (or reuse) ---------------------------------------------
        meshes = {}
        materials = {}
        if not place_only:
            materials['gold'] = pick_material(ue, spec, 'gold', receipt)
            if materials['gold'] is None:
                raise RuntimeError('No gold material candidate loads')
            materials['stone'] = stone_material(ue, spec, receipt)
            write()
        for record in spec['source']['meshes']:
            if place_only:
                mesh, info = load_saved_mesh(ue, spec, record, receipt)
            else:
                mesh, info = import_one_mesh(ue, spec, record, materials[record['role']])
            info['mesh'] = mesh
            meshes[record['name']] = info
            receipt['meshes'][record['name']] = {k: v for k, v in info.items() if k != 'mesh'}
            write()
        receipt['status'] = 'meshes_verified' if place_only else 'meshes_saved'

        # -- 2. winding ------------------------------------------------------------------
        all_passed = True
        for name, info in meshes.items():
            report = winding_report(ue, info['mesh'], spec)
            if report['status'] == 'checked' and report['signedVolumeUEcm3'] is not None and report['signedVolumeUEcm3'] < 0 \
                    and spec['windingCheck']['flipIfNegative']:
                flip = flip_winding(ue, info['mesh'], spec)
                flip['before'] = report
                report = winding_report(ue, info['mesh'], spec)
                flip['after'] = report
                info['localBoundsCm'] = _static_mesh_box(info['mesh'])
                info['triangles'] = info['mesh'].get_num_triangles(0)
                info['uassetSha256'] = _uasset_sha(info['mesh'])
                receipt['meshes'][name].update({k: v for k, v in info.items() if k != 'mesh'})
                receipt['windingFlips'][info['asset']] = flip
                receipt['limitations'].append('%s imported inside-out; triangle order reversed via GeometryScript' % info['asset'])
            receipt['windingCheck'][info['asset']] = report
            all_passed = all_passed and report['passed']
        receipt['windingVerifiedOutward'] = all_passed
        write()
        if import_only:
            receipt['status'] = 'meshes_saved_import_only_no_map_change'
            return receipt
        if not all_passed and spec['windingCheck']['requireForPlacement'] and not allow_unverified_winding:
            receipt['status'] = 'meshes_saved_placement_skipped_winding_unverified'
            receipt['limitations'].append('Placement skipped: winding check did not pass or was unavailable; rerun with '
                                          '-EnablePlugins=GeometryScripting -MenorahPlaceOnly or inspect before -MenorahAllowUnverifiedWinding')
            return receipt
        if not all_passed:
            receipt['limitations'].append('Placed with UNVERIFIED winding by explicit switch')

        # -- 3. map guards + checkpoint ---------------------------------------------------
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        if not levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != TARGET:
            raise RuntimeError('Loaded world %s is not the combined map' % world.get_outermost().get_name())
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages present after loading the map')
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
        clashes = [r['label'] for r in run_state.snapshot if r['label'].startswith(spec['placement']['labelPrefix']) or r['folder'] == spec['folder']]
        if clashes:
            raise RuntimeError('Existing MenorahV3 release actors preserved; refusing duplicate placement: %s' % clashes[:10])
        receipt['actorCountBefore'] = len(run_state.snapshot)
        write()

        # -- 4. remove, place, save, reopen, read back --------------------------------------
        placement = MenorahPlacement(ue, spec, helper, run_state, receipt)
        records = placement.place(meshes)
        receipt['placed'] = [_strip(r) for r in records]
        write()
        removed_names = {r['name'] for r in receipt['removed']}
        current = run_state.numeric_baseline(run_state.take_snapshot())
        changed = [name for name, row in baseline.items() if name not in removed_names and current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:10])
        if any(name in current for name in removed_names):
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
        lingering = [r['label'] for r in reopened if r['label'] in removed_labels]
        if lingering:
            raise RuntimeError('Removed actor reappeared after reopen: %s' % lingering)
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
                     'southWallClearanceCm': spec['placement']['southWallY'] - row['bounds']['max'][1],
                     'collisionProfile': str(component.get_collision_profile_name()),
                     'materials': [_asset_path(component.get_material(i)) for i in range(component.get_num_materials())]}
            readback.append(entry)
            if row['meshes'] != [record['mesh']]:
                raise RuntimeError('Reopened mesh differs for ' + record['label'])
            if not close or bounds_error > verify['staticBoundsToleranceCm']:
                raise RuntimeError('Reopened transform/bounds differ for %s (pose %.4f, bounds %.4f)' % (record['label'], error, bounds_error))
            if entry['collisionProfile'] != record['collisionProfile']:
                raise RuntimeError('Reopened collision profile differs for %s: %s' % (record['label'], entry['collisionProfile']))
            if entry['southWallClearanceCm'] < spec['placement']['nearestTipClearanceCm'] - 1e-6:
                raise RuntimeError('Reopened %s violates the south wall clearance' % record['label'])
        receipt['reopenedReadback'] = readback
        receipt['actorCountAfter'] = len(reopened)
        receipt['status'] = 'menorah_v3_saved_reopened_cc_by_menorah_removed_visual_acceptance_pending'
        return receipt
    except Exception as error:
        receipt['errors'].append(repr(error))
        if saved:
            receipt['status'] = 'failed_after_save_checkpoint_available'
        elif place_only:
            receipt['status'] = 'failed_place_only_map_unchanged_saved_meshes_untouched'
        elif receipt['meshes'] or receipt['created']:
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
    return 'release_import_menorah_v3.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    tokens = command_line.split()
    try:
        receipt = run(import_only='-menorahimportonly' in tokens, allow_unverified_winding='-menorahallowunverifiedwinding' in tokens,
                      place_only='-menorahplaceonly' in tokens)
        ue.log('release_import_menorah_v3: %s placed %s removed %s winding_ok %s' % (
            receipt['status'], receipt.get('placedActorCount'), receipt.get('removedActorCount'), receipt.get('windingVerifiedOutward')))
    except Exception as error:
        ue.log_error('release_import_menorah_v3 failed: ' + repr(error))
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
