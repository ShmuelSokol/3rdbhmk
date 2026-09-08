"""Guarded native import and placement of the KeilimTIV1 vessels (shulchan lechem hapanim and the
golden incense altar, rebuilt to the Machon HaMikdash shapes by Scripts/create_keilim_ti_v1.py).

Modelled on Scripts/release_import_shulchan.py. Every number comes from
Scripts/release_import_keilim_ti.spec.json, which is filled from
SourceAssets/vessels-review/KeilimTIV1/geometry-manifest.json and from the poses recorded in the
ShulchanV2 / IncenseAltarV2 import receipts.

What it does, in order:

  1. Guards: right project, no game world, no dirty packages, target namespace
     /Game/MikdashV3/MaterialReview/KeilimTIV1 absent (or present for -KeilimPlaceOnly), the frozen
     OBJ hashes, the manifest hash and its status intact, triangle budget respected.
  2. Materials. Gold: the first existing candidate MaterialInterface goes to EVERY slot of every
     gold mesh (the SM_KeruvimStudyV1 lesson). Bread: an existing warm matte candidate if one is on
     disk (M_ShulchanV2_Bread), else M_KeilimTIV1_Bread is created by duplicating the gold material
     and re-wiring BaseColor / Metallic / Roughness to warm matte constants.
     UE 5.8 NOTE: MaterialEditingLibrary.connect_material_property can return False on a connection
     that in fact took, and set_editor_property reports nothing. Nothing here trusts a setter's
     return value: every constant and every connected input is READ BACK off the saved material and
     the readback is what decides pass/fail. Both the returned flag and the readback are recorded.
  3. Imports the OBJ parts through the reviewed legacy OBJ adapter path (FbxFactory, same settings
     as the keilim / doors / vessels imports, build_nanite False). The files carry Y reflected and
     winding reversed; the importer reflects Y back, so imported bounds must equal the manifest's
     canonical bounds (tolerance 0.05 cm) and triangle counts must match exactly.
  4. Winding check (GeometryScript; needs -EnablePlugins=GeometryScripting): the signed volume under
     UE's left-handed face-normal convention must be positive for every mesh, and sampled face
     normals must agree with cross(C-A, B-A). A negative mesh is flipped, re-saved and re-checked.
     Without a passing check nothing is placed (override -KeilimAllowUnverifiedWinding, recorded).
  5. Loads the combined map, checkpoints the .umap (plus its external actor folders) to
     ReviewCheckpoints/KeilimTI-<stamp>/, snapshots every actor, then for each requested group finds
     the EXISTING release actors (RELEASE_Shulchan_* / RELEASE_IncenseAltar_*), verifies they carry
     the previous generation's meshes and share one pose, and RECORDS THAT POSE. The new parts are
     planned at exactly that location and yaw, on the measured Heikhal floor top.
  6. Room-envelope and north-wall guards, then a clearance test of every planned AABB against every
     other mesh-bearing actor (release_place_assets rules, hollow unions decomposed). A blocker
     refuses the run BEFORE anything is destroyed or saved.
  7. Destroys the recorded actors, spawns the new RELEASE_* actors at the recorded poses, saves,
     reopens the map, reads every placed actor back numerically (pose, bounds, mesh, collision
     profile, material on every slot) and writes
     SourceAssets/vessels-review/KeilimTIV1/native-import-<stamp>.json (at start and in finally).

Commandlet invocation (serial; never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_import_keilim_ti.py"
      -EnablePlugins=GeometryScripting -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-KeilimTI-01.log"

Switches (read from the engine command line):
  -KeilimGroups=shulchan,altar     which vessels to act on (default both). Each group is
                                   independent: its own removal set, its own placement, and a group
                                   that is not requested is not touched.
  -KeilimImportOnly                materials + import + winding check, no map change.
  -KeilimPlaceOnly                 skip the import; the meshes must already exist (re-verified).
  -KeilimAllowUnverifiedWinding    place even if the winding check is unavailable or failed.

Offline (no engine):
  python Scripts/release_import_keilim_ti.py                 -> offline_check() as JSON
  python Scripts/release_import_keilim_ti.py --writespec      -> regenerate the spec from the manifest
"""
import hashlib
import importlib.util
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_import_keilim_ti.spec.json'
MANIFEST_PATH = ROOT / 'SourceAssets/vessels-review/KeilimTIV1/geometry-manifest.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
GROUPS = ('shulchan', 'altar')


# --------------------------------------------------------------------------
# Spec, shared helpers, pure planning (no unreal import)
# --------------------------------------------------------------------------

def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
    for name in ('sha256_of', 'disk_path', 'box_error', 'boxes_overlap_volume',
                 'verify_union_decomposition', 'Placement', '_pose_close', '_actor_bounds', '_actor_pose'):
        if not hasattr(module, name):
            raise RuntimeError('release_place_assets.py lacks helper ' + name)
    return module


def box_inside(inner, outer, tolerance=0.0):
    return all(inner['min'][i] >= outer['min'][i] - tolerance and inner['max'][i] <= outer['max'][i] + tolerance
               for i in range(3))


def translate(box, location):
    return {'min': [box['min'][i] + location[i] for i in range(3)],
            'max': [box['max'][i] + location[i] for i in range(3)]}


def parse_obj(path):
    vertices, faces = [], []
    with open(path, 'r', errors='replace') as handle:
        for line in handle:
            if line.startswith('v '):
                p = line.split()
                vertices.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith('f '):
                idx = [int(t.split('/')[0]) - 1 for t in line.split()[1:]]
                for k in range(1, len(idx) - 1):
                    faces.append((idx[0], idx[k], idx[k + 1]))
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


def plan_group(spec, group_key, local_boxes, origin):
    """One world AABB per part of a group at the shared origin. Raises on any guard violation:
    the previous generation stood here, so a violation is a real problem, not a fallback."""
    group = spec['groups'][group_key]
    yaw = float(group['placement']['yaw'])
    if yaw != 0.0:
        raise RuntimeError('Plan assumes yaw 0 for %s; spec yaw is %r' % (group_key, yaw))
    parts = {}
    for record in group['meshes']:
        world = translate(local_boxes[record['name']], origin)
        entry = {'label': group['placement']['labelPrefix'] + record['part'], 'part': record['part'],
                 'role': record['role'], 'location': list(origin), 'rotation': [0.0, yaw, 0.0],
                 'scale': [1.0, 1.0, 1.0], 'plannedWorldBoundsCm': world}
        wall = group['placement'].get('northWall')
        if wall:
            entry['northWallClearanceCm'] = world['min'][1] - wall['faceY']
            if entry['northWallClearanceCm'] < wall['minClearanceCm'] - 1e-9:
                raise RuntimeError('%s keeps only %.2f cm from the north wall face (guard %.0f)'
                                   % (entry['label'], entry['northWallClearanceCm'], wall['minClearanceCm']))
        if not box_inside(world, spec['roomEnvelope']):
            raise RuntimeError('%s planned AABB leaves the Heikhal envelope: %r' % (entry['label'], world))
        parts[record['name']] = entry
    union = {'min': [min(p['plannedWorldBoundsCm']['min'][i] for p in parts.values()) for i in range(3)],
             'max': [max(p['plannedWorldBoundsCm']['max'][i] for p in parts.values()) for i in range(3)]}
    return {'group': group_key, 'origin': list(origin), 'yaw': yaw, 'parts': parts,
            'placedParts': [r['name'] for r in group['meshes']], 'assemblyWorldBoundsCm': union}


def offline_check(spec=None, namespace_expected=None, groups=GROUPS, parse_faces=True):
    """Consistency checks that need no engine. Raises on the first failure."""
    spec = spec or load_spec()
    helper = load_placement_helper(spec)
    source = spec['source']
    report = {'groups': list(groups), 'sourceFiles': [], 'materialsOnDisk': {}, 'plans': {}}
    manifest_path = ROOT / source['manifest']
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['status'] != source['manifestStatusRequired']:
        raise RuntimeError('Manifest status ' + manifest['status'])
    if manifest['namespace'] != source['namespace']:
        raise RuntimeError('Manifest namespace differs from spec')
    if sha256_of(manifest_path) != source['manifestSha256']:
        raise RuntimeError('geometry-manifest.json changed after the spec was prepared (rerun --writespec)')
    if sha256_of(ROOT / source['authoringScript']) != source['authoringScriptSha256']:
        raise RuntimeError('The authoring script changed after the spec was prepared (rerun --writespec)')
    by_name = {m['name']: m for m in manifest['meshes']}
    spec_meshes = [r for key in spec['groups'] for r in spec['groups'][key]['meshes']]
    if set(by_name) != {r['name'] for r in spec_meshes}:
        raise RuntimeError('Spec mesh set differs from the manifest')
    if sum(r['triangles'] for r in spec_meshes) != manifest['total_triangles'] \
            or manifest['total_triangles'] >= source['maxTotalTriangles']:
        raise RuntimeError('Total triangle count inconsistent or over budget')
    local_boxes = {}
    for record in spec_meshes:
        entry = by_name[record['name']]
        path = ROOT / source['folder'] / record['file']
        actual = sha256_of(path)
        if actual != record['sha256'] or entry['sha256'] != record['sha256']:
            raise RuntimeError('Frozen OBJ hash differs for ' + record['name'])
        if entry['triangles'] != record['triangles']:
            raise RuntimeError('Triangle count differs from manifest for ' + record['name'])
        if helper.box_error(entry['bounds_cm'], record['canonicalBoundsCm']) > 1e-6:
            raise RuntimeError('Canonical bounds differ from manifest for ' + record['name'])
        if entry['material_role'] != record['role']:
            raise RuntimeError('Material role differs from manifest for ' + record['name'])
        row = {'name': record['name'], 'part': record['part'], 'role': record['role'],
               'sha256': actual, 'triangles': record['triangles']}
        if parse_faces:
            vertices, faces = parse_obj(path)
            if len(faces) != record['triangles']:
                raise RuntimeError('%s parsed %d triangles, spec %d' % (record['name'], len(faces), record['triangles']))
            reflected = {'min': [min(v[0] for v in vertices), -max(v[1] for v in vertices), min(v[2] for v in vertices)],
                         'max': [max(v[0] for v in vertices), -min(v[1] for v in vertices), max(v[2] for v in vertices)]}
            if helper.box_error(reflected, record['canonicalBoundsCm']) > 1e-6:
                raise RuntimeError('%s file bounds (Y reflected) differ from the canonical bounds' % record['name'])
            row['fileRightHandedSignedVolumeCm3'] = right_handed_signed_volume(vertices, faces)
            if row['fileRightHandedSignedVolumeCm3'] <= 0:
                raise RuntimeError('%s file-space signed volume is not positive '
                                   '(the OBJ adapter sign is wrong)' % record['name'])
        local_boxes[record['name']] = record['canonicalBoundsCm']
        report['sourceFiles'].append(row)

    namespace_dir = ROOT / 'Content' / source['namespace'][len('/Game/'):]
    report['namespaceFolderExistsOnDisk'] = namespace_dir.exists()
    report['savedMeshFilesOnDisk'] = {r['name']: (namespace_dir / 'Meshes' / (r['name'] + '.uasset')).exists()
                                      for r in spec_meshes}
    if namespace_expected is False and namespace_dir.exists():
        raise RuntimeError('Target namespace folder already exists on disk: ' + str(namespace_dir))
    if namespace_expected is True:
        wanted = [r['name'] for key in groups for r in spec['groups'][key]['meshes']]
        missing = [n for n in wanted if not report['savedMeshFilesOnDisk'][n]]
        if missing:
            raise RuntimeError('Place-only needs the saved meshes on disk; missing %r' % missing)

    for role in ('gold', 'bread'):
        report['materialsOnDisk'][role] = [{'path': c['path'], 'kind': c['kind'],
                                            'onDisk': helper.disk_path(c['path']).exists()}
                                           for c in spec['materials'][role]['candidates']]
    if not any(r['onDisk'] for r in report['materialsOnDisk']['gold']):
        raise RuntimeError('No gold material candidate exists on disk')
    bread = spec['materials']['bread']
    report['breadMaterialPlan'] = ('reuse existing candidate' if any(r['onDisk'] for r in report['materialsOnDisk']['bread'])
                                   else 'create %s by duplicating %s' % (bread['createPath'], bread['duplicateFrom']))
    if not helper.disk_path(bread['duplicateFrom']).exists():
        raise RuntimeError('Bread duplicate source missing on disk: ' + bread['duplicateFrom'])

    if not (ROOT / spec['targetMapFile']).exists():
        raise RuntimeError('Target map file missing')
    report['mapSha256OnDisk'] = sha256_of(ROOT / spec['targetMapFile'])
    report['mapMatchesLastKnown'] = report['mapSha256OnDisk'] == spec['lastKnownMapSha256']

    for key in groups:
        group = spec['groups'][key]
        origin = list(group['placement']['origin'][:2]) + [spec['floor']['topZ']]
        report['plans'][key] = plan_group(spec, key, local_boxes, origin)
        removal = group['removal']
        if [round(v, 4) for v in removal['expectedLocation'][:2]] != [round(v, 4) for v in origin[:2]] \
                or removal['expectedYaw'] != group['placement']['yaw']:
            raise RuntimeError('Removal pose and placement origin disagree for ' + key)
    report['status'] = 'offline_spec_consistent'
    return report


# --------------------------------------------------------------------------
# Engine side: materials
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


def pick_material(ue, spec, role, receipt):
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    tried = []
    for position, candidate in enumerate(spec['materials'][role]['candidates']):
        exists = assets.does_asset_exist(candidate['path'])
        material = ue.load_asset(candidate['path']) if exists else None
        ok = isinstance(material, ue.MaterialInterface)
        tried.append({'path': candidate['path'], 'kind': candidate['kind'], 'exists': bool(exists), 'loaded': ok})
        if ok:
            if position > 0:
                receipt['limitations'].append('%s material fell back to %s (%s)'
                                              % (role, candidate['path'], candidate['kind']))
            receipt['materials'][role] = {'assigned': candidate['path'], 'kind': candidate['kind'],
                                          'tried': tried, 'created': False}
            return material
    receipt['materials'][role] = {'assigned': None, 'tried': tried, 'created': False}
    return None


def _read_input_expression(ue, material, property_name):
    """Read back one material input. UE 5.8 exposes Material.base_color / .metallic / .roughness as
    *MaterialInput structs; the connected node is the struct's `expression`. Returns the expression
    class name, or None when nothing is connected or the property is not reflected."""
    try:
        holder = material.get_editor_property(property_name)
    except Exception:  # noqa: BLE001 - property not reflected in this build
        return None, 'property_not_reflected'
    if holder is None:
        return None, 'input_is_none'
    for attr in ('expression', 'Expression'):
        try:
            expression = holder.get_editor_property(attr)
        except Exception:  # noqa: BLE001
            expression = getattr(holder, attr, None)
        if expression is not None:
            return type(expression).__name__, 'connected'
    return None, 'not_connected'


def _wire_constants(ue, material, constants, record):
    """Wire warm matte constants and VERIFY BY READBACK. Nothing trusts a setter or
    connect_material_property's return value: in UE 5.8 it can report False on a connection that
    took. The readback of the constants and of the connected inputs decides pass/fail."""
    ml = ue.MaterialEditingLibrary
    colour = constants['baseColor']
    node = ml.create_material_expression(material, ue.MaterialExpressionConstant3Vector, -400, 200)
    node.set_editor_property('constant', ue.LinearColor(colour[0], colour[1], colour[2], 1.0))
    record['connectReturned'] = {}
    record['constantReadback'] = {}
    record['connectReturned']['baseColor'] = bool(ml.connect_material_property(node, '', ue.MaterialProperty.MP_BASE_COLOR))
    back = node.get_editor_property('constant')
    record['constantReadback']['baseColor'] = [round(float(back.r), 6), round(float(back.g), 6), round(float(back.b), 6)]
    scalars = (('metallic', constants['metallic'], ue.MaterialProperty.MP_METALLIC, 400),
               ('roughness', constants['roughness'], ue.MaterialProperty.MP_ROUGHNESS, 500))
    for name, value, prop, y in scalars:
        const = ml.create_material_expression(material, ue.MaterialExpressionConstant, -400, y)
        const.set_editor_property('r', value)
        record['connectReturned'][name] = bool(ml.connect_material_property(const, '', prop))
        record['constantReadback'][name] = round(float(const.get_editor_property('r')), 6)
    ml.recompile_material(material)
    record['inputReadback'] = {}
    for name in ('base_color', 'metallic', 'roughness'):
        expression, state = _read_input_expression(ue, material, name)
        record['inputReadback'][name] = {'expression': expression, 'state': state}
    wrong = [k for k, v in record['constantReadback'].items()
             if (isinstance(v, list) and [round(x, 6) for x in colour] != v)
             or (not isinstance(v, list) and abs(v - dict(metallic=constants['metallic'],
                                                          roughness=constants['roughness'])[k]) > 1e-6)]
    record['constantsVerified'] = not wrong
    if wrong:
        raise RuntimeError('Bread material constants did not read back: %s (%r)' % (wrong, record['constantReadback']))
    connected = [k for k, v in record['inputReadback'].items() if v['state'] == 'connected']
    record['inputsVerified'] = connected
    record['inputsVerifiable'] = [k for k, v in record['inputReadback'].items() if v['state'] != 'property_not_reflected']
    if record['inputsVerifiable'] and 'base_color' not in connected:
        raise RuntimeError('Bread BaseColor did not read back as connected: %r' % record['inputReadback'])
    return record


def bread_material(ue, spec, receipt):
    """An existing warm matte candidate, else one created by duplicating the gold material."""
    existing = pick_material(ue, spec, 'bread', receipt)
    if existing is not None:
        receipt['materials']['bread']['verifiedBy'] = 'existing candidate on disk; constants not rewritten'
        return existing
    bread = spec['materials']['bread']
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if assets.does_asset_exist(bread['createPath']):
        material = ue.load_asset(bread['createPath'])
        if not isinstance(material, ue.MaterialInterface):
            raise RuntimeError('Existing bread asset is not a material: ' + bread['createPath'])
        receipt['materials']['bread'].update({'assigned': bread['createPath'], 'kind': 'bread_constant_reused',
                                              'created': False})
        return material
    material, method = None, None
    try:
        duplicated = assets.duplicate_asset(bread['duplicateFrom'], bread['createPath'])
        if isinstance(duplicated, ue.Material):
            material = duplicated
            method = 'duplicate_asset(%s) + rewired constants' % bread['duplicateFrom']
    except Exception as error:  # noqa: BLE001
        receipt['limitations'].append('duplicate_asset failed for the bread material: %r' % error)
    if material is None:
        folder, name = bread['createPath'].rsplit('/', 1)
        material = ue.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, ue.Material, ue.MaterialFactoryNew())
        if not isinstance(material, ue.Material):
            raise RuntimeError('Bread material creation failed')
        method = 'MaterialFactoryNew (create_heikhal_keilim recipe)'
    record = {'method': method, 'constants': bread['constants']}
    _wire_constants(ue, material, bread['constants'], record)
    if not assets.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for the bread material')
    reloaded = ue.load_asset(bread['createPath'])
    record['savedInputReadback'] = {n: _read_input_expression(ue, reloaded, n)[1]
                                    for n in ('base_color', 'metallic', 'roughness')}
    receipt['materials']['bread'].update({'assigned': _asset_path(material), 'kind': 'bread_constant_created',
                                          'created': True, 'uassetSha256': _uasset_sha(material),
                                          'verifiedBy': 'readback of the constants and of the saved material inputs',
                                          **record})
    receipt['created'].append(_asset_path(material))
    return material


# --------------------------------------------------------------------------
# Engine side: import and winding
# --------------------------------------------------------------------------

def verify_mesh_geometry(spec, record, box, triangles):
    tolerance = spec['source']['boundsToleranceCm']
    canonical = record['canonicalBoundsCm']
    error = max(abs(box[k][i] - canonical[k][i]) for k in ('min', 'max') for i in range(3))
    plain = {'min': [canonical['min'][0], -canonical['max'][1], canonical['min'][2]],
             'max': [canonical['max'][0], -canonical['min'][1], canonical['max'][2]]}
    error_unreflected = max(abs(box[k][i] - plain[k][i]) for k in ('min', 'max') for i in range(3))
    if error > tolerance:
        raise RuntimeError('%s imported bounds differ from the canonical bounds by %.4f cm '
                           '(unreflected error %.4f): %r' % (record['name'], error, error_unreflected, box))
    if triangles != record['triangles']:
        raise RuntimeError('%s imported %d triangles, manifest %d' % (record['name'], triangles, record['triangles']))
    return {'boundsErrorCm': error, 'boundsErrorIfImporterHadNotReflectedY': error_unreflected,
            'importerReflectedYAsExpected': error <= tolerance,
            'ambiguousReflection': error_unreflected <= tolerance}


def import_one_mesh(ue, spec, record, material):
    source, settings = spec['source'], spec['importSettings']
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
    for key, value in dict(filename=str(path), destination_path=source['meshFolder'],
                           destination_name=record['name'], automated=True, async_=False,
                           replace_existing=False, save=False, options=ui, factory=ue.FbxFactory()).items():
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
    not_assigned = [s for s in range(slots) if _asset_path(mesh.get_material(s)) != _asset_path(material)]
    if slots == 0 or not_assigned:
        raise RuntimeError('Material slots not assigned on %s: %s of %d' % (record['name'], not_assigned, slots))
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + record['name'])
    info = {'asset': _asset_path(mesh), 'file': str(path), 'triangles': triangles,
            'vertices': mesh.get_num_vertices(0), 'localBoundsCm': box, 'materialSlots': slots,
            'material': _asset_path(material), 'role': record['role'], 'importSeconds': seconds,
            'buildNanite': False, 'uassetSha256': _uasset_sha(mesh)}
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
    if record['role'] == 'bread':
        allowed.add(spec['materials']['bread']['createPath'])
    slots = len(mesh.get_editor_property('static_materials'))
    assigned = {_asset_path(mesh.get_material(s)) for s in range(slots)}
    wrong = sorted(str(p) for p in assigned if p not in allowed)
    if slots == 0 or wrong or len(assigned) != 1:
        raise RuntimeError('%s has %d slots; materials %s (outside spec: %s)'
                           % (record['name'], slots, sorted(map(str, assigned)), wrong))
    material_path = assigned.pop()
    receipt['materials'].setdefault(record['role'], {'assigned': material_path, 'verifiedOnSavedMesh': True})
    info = {'asset': _asset_path(mesh), 'file': None, 'triangles': triangles, 'vertices': mesh.get_num_vertices(0),
            'localBoundsCm': box, 'materialSlots': slots, 'material': material_path, 'role': record['role'],
            'reused': True, 'uassetSha256': _uasset_sha(mesh)}
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
    except Exception:  # noqa: BLE001 - API shape differs between builds; fall back to the per-triangle loop
        return None
    if len(triangles) != dynamic.get_triangle_count() or len(positions) < dynamic.get_vertex_count():
        return None
    return positions, triangles


def winding_report(ue, mesh, spec):
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
    flux, disagreements, sampled = 0.0, 0, 0
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
                return {'status': 'read_failed', 'passed': False, 'signedVolumeUEcm3': None,
                        'reason': 'triangle %d has %d corners' % (tid, len(positions))}
            face = query.get_triangle_face_normal(dynamic, tid)
            normals = [_xyz(v) for v in face if isinstance(v, ue.Vector)] if isinstance(face, tuple) else [_xyz(face)]
            if len(normals) != 1:
                return {'status': 'read_failed', 'passed': False, 'signedVolumeUEcm3': None,
                        'reason': 'no face normal for triangle %d' % tid}
            a, b, c = positions
            ue_cross = _cross(_sub(c, a), _sub(b, a))
            sampled += 1
            if _dot(ue_cross, normals[0]) < 0:
                disagreements += 1
            flux += _dot(ue_cross, [(a[i] + b[i] + c[i]) / 3.0 for i in range(3)])
        method = 'per_triangle_loop'
    signed_volume = flux / 6.0
    return {'status': 'checked', 'passed': signed_volume > 0 and disagreements == 0 and sampled > 0,
            'method': method, 'triangles': count, 'signedVolumeUEcm3': signed_volume,
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

class KeilimPlacement:
    def __init__(self, ue, spec, helper, run, receipt):
        self.ue, self.spec, self.helper, self.run, self.receipt = ue, spec, helper, run, receipt

    def find_floor(self):
        floor_spec = self.spec['floor']
        rows = self.run.actors_with_mesh(floor_spec['mesh'])
        if len(rows) != 1:
            raise RuntimeError('Expected one Heikhal clear floor actor, found %d' % len(rows))
        floor = rows[0]
        if self.helper.box_error(floor['bounds'], floor_spec['worldBoundsCm']) > floor_spec['boundsToleranceCm']:
            raise RuntimeError('Heikhal floor bounds differ from the spec: %r' % floor['bounds'])
        if abs(floor['bounds']['max'][2] - floor_spec['topZ']) > floor_spec['topToleranceCm']:
            raise RuntimeError('Heikhal floor top %.3f differs from spec %.3f'
                               % (floor['bounds']['max'][2], floor_spec['topZ']))
        return floor

    def find_removals(self, group_key):
        """Every existing release actor of this group, with its recorded pose. All must share one
        location and yaw: that pose is where the replacement goes."""
        removal = self.spec['groups'][group_key]['removal']
        rows = [r for r in self.run.snapshot if r['label'].startswith(removal['labelPrefix'])]
        labels = sorted(r['label'] for r in rows)
        if labels != sorted(removal['expectedLabels']):
            raise RuntimeError('%s removal set is %r, expected %r' % (group_key, labels, sorted(removal['expectedLabels'])))
        recorded = []
        for row in rows:
            if not row['meshes'] or not all((m or '').startswith(removal['expectedMeshPrefix']) for m in row['meshes']):
                raise RuntimeError('%s carries meshes outside %s: %r'
                                   % (row['label'], removal['expectedMeshPrefix'], row['meshes']))
            close, error = self.helper._pose_close(row['pose'], removal['expectedLocation'],
                                                   [0.0, removal['expectedYaw'], 0.0], [1.0, 1.0, 1.0],
                                                   removal['poseToleranceCm'])
            if not close:
                raise RuntimeError('%s pose differs from the recorded pose by %.4f' % (row['label'], error))
            recorded.append({'label': row['label'], 'name': row['name'], 'folder': row['folder'],
                             'meshes': row['meshes'], 'pose': row['pose'], 'worldBoundsCm': row['bounds'],
                             'poseErrorVsSpecCm': error, 'actor': row['actor']})
        return recorded

    def clearance_candidates(self, excluded_labels):
        clearance = self.spec['clearance']
        manifest = json.loads((ROOT / clearance['architectureManifest']).read_text(encoding='utf-8-sig'))
        entries = {e['assetName']: e for e in manifest['meshes']}
        prefix = clearance['levelAssetPrefix']
        boxes_by_key, candidates, excluded_terrain = {}, [], []
        for row in self.run.snapshot:
            if not row['meshes'] or row['label'] in excluded_labels:
                continue
            if any(row['folder'].startswith(f) for f in clearance['terrainFolders']) or \
                    any('/JerusalemContext/Terrain/' in (m or '') or '/FutureMountV1/Terrain/' in (m or '')
                        for m in row['meshes']):
                excluded_terrain.append(row['label'])
                continue
            key = None
            if row['folder'] == clearance['unionFolder'] and len(row['meshes']) == 1 \
                    and (row['meshes'][0] or '').startswith(prefix):
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

    def run_groups(self, groups, meshes):
        ue, spec = self.ue, self.spec
        floor = self.find_floor()
        floor_top = floor['bounds']['max'][2]
        removals, plans = {}, {}
        for key in groups:
            removals[key] = self.find_removals(key)
            origin = list(spec['groups'][key]['placement']['origin'][:2]) + [floor_top]
            recorded_pose = removals[key][0]['pose']['location']
            if abs(recorded_pose[2] - floor_top) > spec['groups'][key]['removal']['poseToleranceCm']:
                raise RuntimeError('%s previous actors sit at Z %.4f, floor top is %.4f'
                                   % (key, recorded_pose[2], floor_top))
            origin = [recorded_pose[0], recorded_pose[1], recorded_pose[2]]
            plans[key] = plan_group(spec, key, {n: meshes[n]['localBoundsCm'] for n in meshes}, origin)
        self.receipt['removed'] = {k: [{kk: vv for kk, vv in r.items() if kk != 'actor'} for r in v]
                                   for k, v in removals.items()}
        self.receipt['plan'] = plans

        excluded = {floor['label']} | {r['label'] for v in removals.values() for r in v}
        candidates, boxes_by_key = self.clearance_candidates(excluded)
        blockers = {}
        for key in groups:
            for name, part in plans[key]['parts'].items():
                hits = self.blockers_for(part['plannedWorldBoundsCm'], candidates, boxes_by_key)
                if hits:
                    blockers[part['label']] = hits
        self.receipt['clearance']['blockers'] = blockers
        if blockers:
            raise RuntimeError('Planned part AABBs intersect existing actors; nothing removed or saved: %s' % blockers)

        destroyed = []
        for key in groups:
            for row in removals[key]:
                if not self.run.actors.destroy_actor(row['actor']):
                    raise RuntimeError('destroy_actor returned False for ' + row['label'])
                destroyed.append(row['label'])
        self.receipt['removedCount'] = len(destroyed)

        records, placed_actors = [], []
        try:
            for key in groups:
                group = spec['groups'][key]
                for name in plans[key]['placedParts']:
                    part = plans[key]['parts'][name]
                    info = meshes[name]
                    tags = [spec['actorTag'], group['actorTag'], part['role'], name]
                    actor, component = self.run.spawn_static(info['mesh'], part['location'], part['rotation'],
                                                             part['label'], group['folder'],
                                                             group['collisionProfile'], tags)
                    placed_actors.append(actor)
                    pose = self.helper._actor_pose(actor)
                    close, error = self.helper._pose_close(pose, part['location'], part['rotation'], part['scale'],
                                                           spec['verification']['transformToleranceCm'])
                    if not close:
                        raise RuntimeError('%s pose differs from plan by %.4f' % (part['label'], error))
                    placed_bounds = self.helper._actor_bounds(actor)
                    bounds_error = self.helper.box_error(placed_bounds, part['plannedWorldBoundsCm'])
                    if bounds_error > spec['verification']['staticBoundsToleranceCm']:
                        raise RuntimeError('%s bounds differ from plan by %.4f: %r'
                                           % (part['label'], bounds_error, placed_bounds))
                    records.append({'group': key, 'label': part['label'], 'kind': 'StaticMeshActor',
                                    'part': part['part'], 'role': part['role'], 'mesh': info['asset'],
                                    'location': part['location'], 'rotation': part['rotation'], 'scale': part['scale'],
                                    'collisionProfile': group['collisionProfile'],
                                    'plannedWorldBoundsCm': part['plannedWorldBoundsCm'],
                                    'placedWorldBoundsCm': placed_bounds, 'boundsErrorCm': bounds_error,
                                    'northWallClearanceCm': part.get('northWallClearanceCm'), 'actor': actor})
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


def run(groups=GROUPS, import_only=False, place_only=False, allow_unverified_winding=False):
    import unreal as ue
    if import_only and place_only:
        raise RuntimeError('-KeilimImportOnly and -KeilimPlaceOnly are mutually exclusive')
    groups = tuple(g for g in GROUPS if g in groups)
    if not groups:
        raise RuntimeError('No known group requested; use -KeilimGroups=shulchan,altar')
    spec = load_spec()
    helper = load_placement_helper(spec)
    offline = offline_check(spec, namespace_expected=place_only, groups=groups)
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
        raise RuntimeError('Existing native namespace preserved (use -KeilimPlaceOnly): ' + spec['source']['namespace'])

    stamp, receipt_path = fresh_receipt_path(spec)
    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(helper.disk_path(m, 'umap')) for m in spec['protectedMaps']
                 if helper.disk_path(m, 'umap').exists()}
    receipt = {
        'status': 'started', 'stamp': stamp, 'groups': list(groups), 'map': TARGET, 'mapFile': str(map_file),
        'mapSha256Before': map_sha_before, 'mapMatchesLastKnown': map_sha_before == spec['lastKnownMapSha256'],
        'protectedMapSha256Before': protected, 'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
        'manifestSha256': sha256_of(ROOT / spec['source']['manifest']),
        'engineVersion': ue.SystemLibrary.get_engine_version(), 'offlineCheck': offline,
        'switches': {'groups': list(groups), 'importOnly': import_only, 'placeOnly': place_only,
                     'allowUnverifiedWinding': allow_unverified_winding},
        'mode': 'place_only_reusing_saved_meshes' if place_only else 'import_and_place',
        'materials': {}, 'created': [], 'meshes': {}, 'windingCheck': {}, 'windingFlips': {},
        'removed': {}, 'placed': [], 'errors': [], 'mapSaved': False,
        'limitations': list(spec['limitations']),
    }

    def write():
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()

    saved = False
    try:
        # -- 1. materials + import (or reuse) --------------------------------------------
        wanted = [r for key in groups for r in spec['groups'][key]['meshes']]
        meshes, materials = {}, {}
        if not place_only:
            materials['gold'] = pick_material(ue, spec, 'gold', receipt)
            if materials['gold'] is None:
                raise RuntimeError('No gold material candidate loads')
            if any(r['role'] == 'bread' for r in wanted):
                materials['bread'] = bread_material(ue, spec, receipt)
            write()
        for record in wanted:
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
            if report['status'] == 'checked' and report['signedVolumeUEcm3'] is not None \
                    and report['signedVolumeUEcm3'] < 0 and spec['windingCheck']['flipIfNegative']:
                flip = flip_winding(ue, info['mesh'], spec)
                flip['before'] = report
                report = winding_report(ue, info['mesh'], spec)
                flip['after'] = report
                info['localBoundsCm'] = _static_mesh_box(info['mesh'])
                info['triangles'] = info['mesh'].get_num_triangles(0)
                info['uassetSha256'] = _uasset_sha(info['mesh'])
                receipt['meshes'][name].update({k: v for k, v in info.items() if k != 'mesh'})
                receipt['windingFlips'][info['asset']] = flip
                receipt['limitations'].append('%s imported inside-out; triangle order reversed via GeometryScript'
                                              % info['asset'])
            receipt['windingCheck'][info['asset']] = report
            all_passed = all_passed and report['passed']
        receipt['windingVerifiedOutward'] = all_passed
        write()
        if import_only:
            receipt['status'] = 'meshes_saved_import_only_no_map_change'
            return receipt
        if not all_passed and spec['windingCheck']['requireForPlacement'] and not allow_unverified_winding:
            receipt['status'] = 'meshes_saved_placement_skipped_winding_unverified'
            receipt['limitations'].append('Placement skipped: winding check did not pass or was unavailable; rerun '
                                          'with -EnablePlugins=GeometryScripting -KeilimPlaceOnly, or inspect before '
                                          '-KeilimAllowUnverifiedWinding')
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
        receipt['actorCountBefore'] = len(run_state.snapshot)
        clashes = [r['label'] for r in run_state.snapshot if r['folder'] == spec['folder']]
        if clashes:
            raise RuntimeError('Existing KeilimTI release folder preserved; refusing duplicate placement: %s'
                               % clashes[:10])
        write()

        # -- 4. remove, place, save, reopen, read back -------------------------------------
        placement = KeilimPlacement(ue, spec, helper, run_state, receipt)
        records = placement.run_groups(groups, meshes)
        receipt['placed'] = [_strip(r) for r in records]
        write()
        removed_names = {r['name'] for rows in receipt['removed'].values() for r in rows}
        removed_labels = {r['label'] for rows in receipt['removed'].values() for r in rows}
        current = run_state.numeric_baseline(run_state.take_snapshot())
        changed = [n for n, row in baseline.items() if n not in removed_names and current.get(n) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:10])
        if any(n in current for n in removed_names):
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
        changed = [n for n, row in baseline.items() if n not in removed_names and reopened_numeric.get(n) != row]
        if changed:
            raise RuntimeError('Pre-existing actors differ after reopen: %s' % changed[:10])
        placed_labels = {r['label'] for r in records}
        lingering = [r['label'] for r in reopened if r['label'] in removed_labels and r['label'] not in placed_labels]
        if lingering:
            raise RuntimeError('Removed actor reappeared after reopen: %s' % lingering)
        verify = spec['verification']
        readback = []
        for record in records:
            matching = [r for r in reopened if r['label'] == record['label']]
            if len(matching) != 1:
                raise RuntimeError('Reopened actor count for %s is %d' % (record['label'], len(matching)))
            row = matching[0]
            close, error = helper._pose_close(row['pose'], record['location'], record['rotation'],
                                              record['scale'], verify['transformToleranceCm'])
            bounds_error = helper.box_error(row['bounds'], record['plannedWorldBoundsCm'])
            component = row['actor'].get_component_by_class(ue.StaticMeshComponent)
            entry = {'group': record['group'], 'label': record['label'], 'folder': row['folder'],
                     'meshPath': row['meshes'], 'pose': row['pose'], 'worldBoundsCm': row['bounds'],
                     'poseErrorCm': error, 'boundsErrorCm': bounds_error,
                     'collisionProfile': str(component.get_collision_profile_name()),
                     'materials': [_asset_path(component.get_material(i)) for i in range(component.get_num_materials())]}
            wall = spec['groups'][record['group']]['placement'].get('northWall')
            if wall:
                entry['northWallClearanceCm'] = row['bounds']['min'][1] - wall['faceY']
                if entry['northWallClearanceCm'] < wall['minClearanceCm'] - 1e-6:
                    raise RuntimeError('Reopened %s violates the north wall guard' % record['label'])
            readback.append(entry)
            if row['meshes'] != [record['mesh']]:
                raise RuntimeError('Reopened mesh differs for ' + record['label'])
            if not close or bounds_error > verify['staticBoundsToleranceCm']:
                raise RuntimeError('Reopened transform/bounds differ for %s (pose %.4f, bounds %.4f)'
                                   % (record['label'], error, bounds_error))
            expected_material = receipt['materials'][record['role']]['assigned']
            wrong = [m for m in entry['materials'] if m != expected_material]
            if not entry['materials'] or wrong:
                raise RuntimeError('Reopened %s carries materials %r, expected only %s'
                                   % (record['label'], entry['materials'], expected_material))
        receipt['reopenedReadback'] = readback
        receipt['actorCountAfter'] = len(reopened)
        receipt['status'] = 'keilim_ti_v1_%s_saved_reopened_previous_release_actors_removed_visual_acceptance_pending' \
                            % '_'.join(groups)
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
        receipt['protectedMapsUnchanged'] = all(sha256_of(helper.disk_path(m, 'umap')) == v
                                                for m, v in protected.items())
        receipt['placedActorCount'] = len(receipt['placed'])
        receipt['removedActorCount'] = sum(len(v) for v in receipt['removed'].values())
        write()


# --------------------------------------------------------------------------
# Spec generation (offline)
# --------------------------------------------------------------------------

SPEC_TEMPLATE_GROUPS = {
    'shulchan': dict(
        actorTag='ReleaseKeilimTIShulchan', folder='Release/KeilimTI/Shulchan', collisionProfile='NoCollision',
        collisionNote='NoCollision, as the ShulchanV2 actors it replaces (the Heikhal is not on the visitor route).',
        labelPrefix='RELEASE_Shulchan_', meshPrefix='SM_KeilimTIV1_Shulchan_',
        origin=[-5300.0, -350.0], yaw=0.0,
        removalPrefix='RELEASE_Shulchan_',
        removalMeshPrefix='/Game/MikdashV3/MaterialReview/ShulchanV2/Meshes/',
        removalLabels=['RELEASE_Shulchan_Table', 'RELEASE_Shulchan_Rings', 'RELEASE_Shulchan_Snifim',
                       'RELEASE_Shulchan_Kanim', 'RELEASE_Shulchan_LoavesWest', 'RELEASE_Shulchan_LoavesEast',
                       'RELEASE_Shulchan_Bazichin'],
        removalLocation=[-5300.0, -350.0, 925.0000610351562], removalYaw=0.0,
        northWall=dict(faceY=-500.0, minClearanceCm=100.0,
                       rule='Every placed AABB must keep min Y >= faceY + minClearanceCm (2 amot; the book\'s '
                            '2.5-amot passage of Rashi Shemos 26:35 measured to the table edge).'),
        basis='Book pp. 241, 250 (book-keilim-review-20260907.md); the pose is READ OFF the RELEASE_Shulchan_* '
              'actors already in the map (native-import-20260907T203842904337Z.json) and reused unchanged.',
    ),
    'altar': dict(
        actorTag='ReleaseKeilimTIAltar', folder='Release/KeilimTI/IncenseAltar', collisionProfile='BlockAll',
        collisionNote='BlockAll with complex-as-simple collision, as the IncenseAltarV2 body it replaces.',
        labelPrefix='RELEASE_IncenseAltar_', meshPrefix='SM_KeilimTIV1_IncenseAltar',
        origin=[-4650.0, 0.0], yaw=0.0,
        removalPrefix='RELEASE_IncenseAltar_',
        removalMeshPrefix='/Game/MikdashV3/MaterialReview/IncenseAltarV2/Meshes/',
        removalLabels=['RELEASE_IncenseAltar_Body', 'RELEASE_IncenseAltar_Poles'],
        removalLocation=[-4650.0, 0.0, 925.0000610351562], removalYaw=0.0,
        northWall=None,
        basis='Book p. 255 (1 x 1 x 2 amot at the five-tefach amah); the pose is READ OFF the RELEASE_IncenseAltar_* '
              'actors already in the map (native-import-20260907T203152827687Z.json) and reused unchanged. '
              'RELEASE_IncenseAltar_Poles is removed WITHOUT a replacement: the Temple\'s golden altar has no rings '
              'and no poles (reference-ti/dossier.md section 3), and the Institute\'s object has none.',
    ),
}


def write_spec():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    by_name = {m['name']: m for m in manifest['meshes']}
    groups = {}
    for key, t in SPEC_TEMPLATE_GROUPS.items():
        records = []
        for name in sorted(n for n in by_name if n.startswith(t['meshPrefix'])):
            entry = by_name[name]
            part = name[len(t['meshPrefix']):] or 'Body'
            records.append(dict(name=name, part=part, file=entry['file'], sha256=entry['sha256'],
                                triangles=entry['triangles'], role=entry['material_role'],
                                canonicalBoundsCm=entry['bounds_cm']))
        if not records:
            raise RuntimeError('No meshes matched prefix %s' % t['meshPrefix'])
        groups[key] = dict(
            vessel=manifest['vessels'][key]['label'], actorTag=t['actorTag'], folder=t['folder'],
            collisionProfile=t['collisionProfile'], collisionNote=t['collisionNote'],
            placement=dict(origin=t['origin'], yaw=t['yaw'], labelPrefix=t['labelPrefix'], basis=t['basis'],
                           **({'northWall': t['northWall']} if t['northWall'] else {})),
            removal=dict(labelPrefix=t['removalPrefix'], expectedLabels=t['removalLabels'],
                         expectedMeshPrefix=t['removalMeshPrefix'], expectedLocation=t['removalLocation'],
                         expectedYaw=t['removalYaw'], poseToleranceCm=0.05,
                         note='These actors are destroyed in memory AFTER the .umap checkpoint and only persist as '
                              'removed when the level is saved at the end. Their poses are recorded in the receipt '
                              'before anything is destroyed. The previous meshes and materials stay on disk.'),
            silhouetteScore=dict(best_iteration=manifest['vessels'][key]['best_iteration'],
                                 as_built_iou=manifest['vessels'][key]['as_built_iou'],
                                 shape_variant_iou=manifest['vessels'][key]['shape_variant_iou'],
                                 calibration=manifest['vessels'][key]['calibration_file']),
            meshes=records,
        )
    shulchan_spec = json.loads((ROOT / 'Scripts/release_import_shulchan.spec.json').read_text(encoding='utf-8'))
    spec = dict(
        specVersion=1, prepared=datetime.now(timezone.utc).strftime('%Y-%m-%d'),
        purpose='Human-reviewable plan consumed by Scripts/release_import_keilim_ti.py: native OBJ import of the '
                'KeilimTIV1 shulchan and golden incense altar, gold on every metal slot and a warm matte bread '
                'material on the loaves, winding check, removal of the previous RELEASE_Shulchan_* and '
                'RELEASE_IncenseAltar_* actors at their recorded poses and placement of the new parts at exactly '
                'those poses, save, reopen, numeric readback, receipt.',
        projectDir=str(ROOT), targetMap=TARGET, targetMapFile=shulchan_spec['targetMapFile'],
        lastKnownMapSha256=sha256_of(ROOT / shulchan_spec['targetMapFile']),
        lastKnownMapSha256Note='Walkthrough.umap on disk when this spec was written. Recorded as matched/not matched '
                               'only, never used as a guard.',
        protectedMaps=shulchan_spec['protectedMaps'],
        checkpointRoot=shulchan_spec['checkpointRoot'], checkpointPrefix='KeilimTI-',
        receiptFolder='SourceAssets/vessels-review/KeilimTIV1', receiptPrefix='native-import-',
        placementHelper=shulchan_spec['placementHelper'], placementHelperSpec=shulchan_spec['placementHelperSpec'],
        actorTag='ReleaseKeilimTIV1', folder='Release/KeilimTI',
        source=dict(
            folder='SourceAssets/vessels-review/KeilimTIV1',
            manifest='SourceAssets/vessels-review/KeilimTIV1/geometry-manifest.json',
            manifestSha256=sha256_of(MANIFEST_PATH),
            manifestStatusRequired=manifest['status'],
            authoringScript='Scripts/create_keilim_ti_v1.py',
            authoringScriptSha256=sha256_of(ROOT / 'Scripts/create_keilim_ti_v1.py'),
            namespace=manifest['namespace'],
            meshFolder=manifest['namespace'] + '/Meshes',
            maxTotalTriangles=manifest['triangle_budget'],
            boundsToleranceCm=0.05,
            objAdapter=manifest['convention'],
        ),
        importSettings=shulchan_spec['importSettings'],
        materials=dict(
            rule=shulchan_spec['materials']['rule'],
            gold=shulchan_spec['materials']['gold'],
            bread=dict(
                candidates=[{'path': '/Game/MikdashV3/MaterialReview/ShulchanV2/M_ShulchanV2_Bread',
                             'kind': 'warm matte bread constant created for ShulchanV2 (reused if present)'}],
                candidatesNote='If the ShulchanV2 bread material is on disk it is reused unchanged; otherwise a new '
                               'one is created in the KeilimTIV1 namespace by duplicating the gold material.',
                createPath=manifest['namespace'] + '/M_KeilimTIV1_Bread',
                duplicateFrom=shulchan_spec['materials']['bread']['duplicateFrom'],
                method='EditorAssetSubsystem.duplicate_asset(duplicateFrom -> createPath), then Constant3Vector and '
                       'Constant expressions connected to BaseColor / Metallic / Roughness. UE 5.8 can return False '
                       'from connect_material_property on a connection that took, so the returned flag is only '
                       'RECORDED: the pass/fail decision is the readback of every constant and of the material '
                       'inputs on the saved asset.',
                constants=shulchan_spec['materials']['bread']['constants'],
                verifyByReadback=True,
            ),
        ),
        windingCheck=dict(shulchan_spec['windingCheck'],
                          expectedOfflineRightHandedVolumeSign='positive for every KeilimTIV1 file '
                                                               '(create_keilim_ti_v1.readback asserts it), so no flip '
                                                               'is expected'),
        verification=shulchan_spec['verification'],
        floor=shulchan_spec['placement']['floor'],
        roomEnvelope=shulchan_spec['placement']['roomEnvelope'],
        clearance=shulchan_spec['placement']['clearance'],
        groups=groups,
        limitations=[
            'Photograph-derived proportion, not a survey: the shapes follow pixel measurements off two Temple '
            'Institute studio photographs (SourceAssets/vessels-review/KeilimTIV1/calibration-*.json). No claim is '
            'made that the Institute\'s vessels are themselves the Temple vessels, and the ornament is drawn fresh '
            'in their vocabulary, not traced from the photographs.',
            'Silhouette overlap is a bounding-box aligned shape score, not a fidelity measure: shulchan %.4f '
            'as built (%.4f with the table rebuilt at the height the Institute actually used), incense altar %.4f.'
            % (manifest['vessels']['shulchan']['as_built_iou'], manifest['vessels']['shulchan']['shape_variant_iou'],
               manifest['vessels']['altar']['as_built_iou']),
            'The shulchan is 3 amot high per the book (p. 241, Yechezkel 41:22); the Institute built the 1.5-amah '
            'table of Shemos 25:23. The legs are therefore about twice as long relative to the top as in the '
            'photograph.',
            'The incense altar body is exactly 2:1 per the book (p. 255); the photographed object is 2.18:1, so the '
            'model is about 9 per cent squatter. Its pierced zer and four horns stand above the 2-amot burning '
            'surface, as in the photograph.',
            'RELEASE_IncenseAltar_Poles is removed without a replacement (no rings or poles on the Temple\'s golden '
            'altar).',
            'Loaf walls are 2 tefachim with a 7-etzbaos karnos gap (Menachos 96a; book p. 241 diagram 22:6), not the '
            '7 tefachim of the brief.',
            'Materials are flat constants: gold on the metalwork, a warm matte constant on the loaves. No textures, '
            'no relief maps, no lighting or visual acceptance - that is a separate native review.',
        ],
    )
    SPEC_PATH.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return spec


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

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
    return 'release_import_keilim_ti.py' in command_line and \
           ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _groups_from(tokens):
    for token in tokens:
        if token.startswith('-keilimgroups=') or token.startswith('--groups='):
            names = [t.strip() for t in token.split('=', 1)[1].split(',') if t.strip()]
            unknown = [n for n in names if n not in GROUPS]
            if unknown:
                raise RuntimeError('Unknown group(s) %r; known: %r' % (unknown, list(GROUPS)))
            return tuple(names)
    return GROUPS


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    tokens = command_line.split()
    try:
        receipt = run(groups=_groups_from(tokens), import_only='-keilimimportonly' in tokens,
                      place_only='-keilimplaceonly' in tokens,
                      allow_unverified_winding='-keilimallowunverifiedwinding' in tokens)
        ue.log('release_import_keilim_ti: %s placed %s removed %s winding_ok %s'
               % (receipt['status'], receipt.get('placedActorCount'), receipt.get('removedActorCount'),
                  receipt.get('windingVerifiedOutward')))
    except Exception as error:
        ue.log_error('release_import_keilim_ti failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _invoked_as_native_script():
        _main()
    elif '--writespec' in sys.argv:
        written = write_spec()
        print('wrote %s (groups %s)' % (SPEC_PATH, list(written['groups'])))
    else:
        print(json.dumps(offline_check(groups=_groups_from([a.lower() for a in sys.argv[1:]])), indent=2, default=str))
