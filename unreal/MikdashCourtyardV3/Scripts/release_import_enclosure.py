"""Guarded native import and placement of the EnclosureV1 study (future Temple Mount wall,
gates, cheil and soreg from Lishchno Tidreshu) as a separate toggleable actor folder in the
combined map.

Every number is read from Scripts/release_import_enclosure.spec.json and the two frozen
offline products of Scripts/create_mount_enclosure.py:
  SourceAssets/FutureMountV1/EnclosureV1/geometry-manifest.json   (OBJ hashes, parts, bounds)
  SourceAssets/FutureMountV1/EnclosureV1/enclosure-design.json    (locations, Z policy, checks)

What it does, in order:
  1. Guards: right project, no game world, no dirty packages, the target namespace
     /Game/MikdashV3/FutureMountV1/EnclosureV1 absent (or present for -EnclosurePlaceOnly),
     frozen hashes intact (spec.frozen vs files on disk), the design's offline platform and
     protected-polygon checks all passed.
  2. Imports the OBJ parts through the reviewed legacy OBJ adapter path (FbxFactory settings of
     release_import_doors / create_heikhal_keilim), verifies triangles and canonical bounds,
     assigns EXISTING canonical materials to every slot, sets BodySetup complex-as-simple
     collision, saves the assets.
  3. Winding check (GeometryScript, needs -EnablePlugins=GeometryScripting): the divergence
     volume with UE face normals must be positive and equal the manifest part-volume sum.
  4. Loads /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough, refuses if any
     RELEASE_Enclosure_* actor or the folder Release/Enclosure exists, checkpoints the .umap
     to C:/Mikdash/Working-5.8/ReviewCheckpoints/Enclosure-<stamp>/, snapshots every actor.
  5. Verifies the future platform deck actor (folder FutureMountV1/Platform, top Z 0) for the
     ring groups, tests every planned AABB against the level (ring groups: no blockers;
     wall/gates: city overlaps recorded, not blocking), spawns StaticMeshActors with the
     BlockAll profile under Release/Enclosure/<group>, checks that no pre-existing actor
     changed, saves, reopens, reads back numerically and writes
     SourceAssets/FutureMountV1/EnclosureV1/native-import-<stamp>.json.
  Nothing existing is deleted, moved or hidden.

Commandlet invocation (serial; never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_import_enclosure.py"
      -EnablePlugins=GeometryScripting -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-Enclosure-01.log"

Optional switches (read from the engine command line):
  -EnclosureImportOnly            import + materials + collision + winding check, no map change.
  -EnclosurePlaceOnly             skip the import; the meshes must already exist and match.
  -EnclosureGroups=wall,gates,cheil,soreg,steps   subset to place (default: spec defaultGroups =
                                  wall,gates,cheil,soreg; steps is a recorded deliberate omission).
  -EnclosureAllowUnverifiedWinding place even if the winding check is unavailable/failed.

Offline (no engine):
  python Scripts/release_import_enclosure.py            -> offline check against the frozen spec.
  python Scripts/release_import_enclosure.py --freeze   -> records the reviewed manifest/design
                                                           hashes and the per-mesh plan in the spec.

Reuses the pure helpers and the Placement snapshot utilities of Scripts/release_place_assets.py.
"""
import hashlib
import importlib.util
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_import_enclosure.spec.json'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
GROUP_ORDER = ('wall', 'gates', 'cheil', 'soreg', 'steps')


# --------------------------------------------------------------------------
# Spec, shared helpers and pure planning (no unreal import)
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
    """Import Scripts/release_place_assets.py as a module without running its main."""
    path = ROOT / spec['placementHelper']
    module_spec = importlib.util.spec_from_file_location('release_place_assets', path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    for name in ('sha256_of', 'disk_path', 'box_error', 'union_constituent_boxes', 'verify_union_decomposition',
                 '_pose_close', '_actor_bounds', 'Placement'):
        if not hasattr(module, name):
            raise RuntimeError('release_place_assets.py lacks helper ' + name)
    return module


def normalise_groups(groups):
    if isinstance(groups, str):
        groups = groups.split(',')
    wanted = [g.strip().lower() for g in groups if g.strip()]
    unknown = [g for g in wanted if g not in GROUP_ORDER]
    if unknown:
        raise RuntimeError('Unknown enclosure groups %s; valid: %s' % (unknown, list(GROUP_ORDER)))
    if not wanted:
        raise RuntimeError('No enclosure groups requested')
    return tuple(g for g in GROUP_ORDER if g in wanted)


def box_error(a, b):
    return max(abs(a[key][i] - b[key][i]) for key in ('min', 'max') for i in range(3))


def boxes_overlap_volume(a, b):
    """Strictly positive overlap on all three axes; touching planes do not count."""
    for i in range(3):
        if min(a['max'][i], b['max'][i]) - max(a['min'][i], b['min'][i]) <= 1e-6:
            return False
    return True


def translate_box(local, location):
    return {'min': [local['min'][i] + location[i] for i in range(3)], 'max': [local['max'][i] + location[i] for i in range(3)]}


def normalise_yaw(yaw):
    while yaw > 180.0:
        yaw -= 360.0
    while yaw <= -180.0:
        yaw += 360.0
    return yaw


def pose_close(pose, location, rotation, scale, tolerance):
    errors = [abs(pose['location'][i] - location[i]) for i in range(3)]
    errors += [abs(normalise_yaw(pose['rotation'][i] - rotation[i])) for i in range(3)]
    errors += [abs(pose['scale'][i] - scale[i]) for i in range(3)]
    return max(errors) <= tolerance, max(errors)


def load_manifest(spec):
    manifest = json.loads((ROOT / spec['source']['manifest']).read_text(encoding='utf-8'))
    if manifest['status'] != spec['source']['manifestStatusRequired']:
        raise RuntimeError('Enclosure manifest status ' + manifest['status'])
    if manifest['namespace'] != spec['source']['namespace'] or manifest['meshFolder'] != spec['source']['meshFolder']:
        raise RuntimeError('Manifest namespace differs from the spec')
    return manifest


def load_design(spec):
    design = json.loads((ROOT / spec['source']['design']).read_text(encoding='utf-8'))
    if design['status'] != spec['source']['designStatusRequired']:
        raise RuntimeError('Enclosure design status ' + design['status'])
    return design


def build_plan(spec, manifest, design):
    """One actor per mesh: location from the design, world AABB = local bounds + location."""
    by_mesh = {p['mesh']: p for p in design['placements']}
    if len(by_mesh) != len(design['placements']):
        raise RuntimeError('Duplicate placement rows in the design')
    checks = {c['mesh']: c for c in design['checks']['perMesh']}
    rows = []
    for index, record in enumerate(manifest['meshes'], start=1):
        placement = by_mesh.get(record['name'])
        check = checks.get(record['name'])
        if placement is None or check is None:
            raise RuntimeError('Design lacks placement/check for ' + record['name'])
        if placement['group'] != record['group'] or placement['group'] not in GROUP_ORDER:
            raise RuntimeError('Group mismatch for ' + record['name'])
        if placement['rotation'] != [0.0, 0.0, 0.0] or placement['scale'] != [1.0, 1.0, 1.0]:
            raise RuntimeError('Enclosure parts are authored axis-aligned; unexpected rotation/scale on ' + record['name'])
        planned = translate_box(record['bounds_cm'], placement['location'])
        if box_error(planned, placement['plannedWorldBoundsCm']) > spec['source']['boundsToleranceCm']:
            raise RuntimeError('Design world bounds differ from local bounds + location for ' + record['name'])
        if not (check['platformCheckPassed'] and check['protectedCheckPassed']):
            raise RuntimeError('Design offline check failed for ' + record['name'])
        short = record['name'].replace('SM_EnclosureV1_', '')
        rows.append({'index': index, 'meshName': record['name'], 'file': record['file'], 'group': record['group'], 'materialRole': record['materialRole'],
                     'location': [float(v) for v in placement['location']], 'rotation': [0.0, 0.0, 0.0], 'scale': [1.0, 1.0, 1.0],
                     'plannedWorldBoundsCm': planned, 'zPolicy': placement['zPolicy'], 'roleTag': short,
                     'label': '%s%s_%s_%s' % (spec['labelPrefix'], spec['group'], record['group'], short),
                     'terrainSampledZcm': placement.get('terrainSampledZcm'), 'partVolumeSumCm3': sum(p['volume_cm3'] for p in record['parts'])})
    return rows


def frozen_signature(spec, manifest, design):
    return {
        'manifestSha256': sha256_of(ROOT / spec['source']['manifest']),
        'designSha256': sha256_of(ROOT / spec['source']['design']),
        'generatorSha256': sha256_of(ROOT / spec['source']['generator']),
        'manifestGeneratorSha256': manifest['generatorSha256'],
        'designGeneratorSha256': design['generatorSha256'],
        'totalTriangles': manifest['totalTriangles'],
        'meshes': [{'name': m['name'], 'file': m['file'], 'sha256': m['sha256'], 'triangles': m['triangles'], 'parts': len(m['parts']),
                    'canonicalBoundsCm': m['bounds_cm'], 'partVolumeSumCm3': sum(p['volume_cm3'] for p in m['parts']),
                    'group': m['group'], 'materialRole': m['materialRole']} for m in manifest['meshes']],
    }


def offline_check(spec=None, freeze=False):
    """Consistency checks that need no engine. Raises on the first failure."""
    spec = spec or load_spec()
    helper = load_placement_helper(spec)
    source = spec['source']
    manifest = load_manifest(spec)
    design = load_design(spec)
    report = {'sourceFiles': [], 'materialsOnDisk': {}, 'namespaceOnDisk': None}
    if manifest['generatorSha256'] != design['generatorSha256']:
        raise RuntimeError('Manifest and design were written by different generator versions')
    if manifest['architectureManifestSha256'] != sha256_of(ROOT / spec['clearance']['architectureManifest']):
        raise RuntimeError('architecture-manifest.json changed since the enclosure was generated')
    total = 0
    roles = set(spec['materials']) - {'rule'}
    for record in manifest['meshes']:
        path = ROOT / source['folder'] / record['file']
        if not path.exists():
            raise RuntimeError('Missing source OBJ ' + str(path))
        actual = sha256_of(path)
        if actual != record['sha256']:
            raise RuntimeError('OBJ hash differs from manifest for ' + record['name'])
        if record['materialRole'] not in roles:
            raise RuntimeError('Unknown material role %s on %s' % (record['materialRole'], record['name']))
        if not record['parts'] or any(not p['closed'] or p['volume_cm3'] <= 0 for p in record['parts']):
            raise RuntimeError('Open or inverted part in ' + record['name'])
        if sum(p['triangles'] for p in record['parts']) != record['triangles']:
            raise RuntimeError('Part triangles do not sum to the mesh triangles for ' + record['name'])
        total += record['triangles']
        report['sourceFiles'].append({'file': record['file'], 'sha256': actual, 'triangles': record['triangles'], 'parts': len(record['parts'])})
    if total != manifest['totalTriangles']:
        raise RuntimeError('Total triangles %d differ from manifest %d' % (total, manifest['totalTriangles']))
    if total > source['maxTotalTriangles']:
        raise RuntimeError('Total triangles %d exceed the budget %d' % (total, source['maxTotalTriangles']))
    if not (design['checks']['allPlatformChecksPassed'] and design['checks']['allProtectedChecksPassed']):
        raise RuntimeError('Design offline platform/protected checks did not all pass')
    plan = build_plan(spec, manifest, design)
    report['plannedActors'] = len(plan)
    report['byGroup'] = {g: sum(1 for r in plan if r['group'] == g) for g in GROUP_ORDER}

    namespace_dir = helper.disk_path(source['namespace'] + '/x').parent
    report['namespaceOnDisk'] = namespace_dir.exists()
    for role in roles:
        entry = spec['materials'][role]
        report['materialsOnDisk'][role] = [{'path': c['path'], 'exists': helper.disk_path(c['path']).exists()} for c in entry['candidates']]
        if not any(c['exists'] for c in report['materialsOnDisk'][role]):
            raise RuntimeError('No %s material candidate exists on disk' % role)
    if not (ROOT / spec['targetMapFile']).exists():
        raise RuntimeError('Target map file missing')
    for key in ('fbxImportUI', 'staticMeshImportData'):
        if key not in spec['importSettings']:
            raise RuntimeError('importSettings lacks ' + key)
    report['defaultGroups'] = list(normalise_groups(spec['defaultGroups']))
    report['deliberateOmissions'] = spec.get('deliberateOmissions', {})
    for group in GROUP_ORDER:
        if group not in report['defaultGroups'] and group not in report['deliberateOmissions']:
            raise RuntimeError('Group %r is excluded from defaultGroups without a deliberateOmissions entry' % group)

    signature = frozen_signature(spec, manifest, design)
    if freeze:
        spec['frozen'] = dict(signature, note='Written by release_import_enclosure.py --freeze after review of the generated files; '
                                               'offline_check() recomputes it and refuses to run if the files differ.',
                              frozenUtc=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                              plan=[{k: v for k, v in row.items()} for row in plan])
        SPEC_PATH.write_text(json.dumps(spec, indent=2) + '\n', encoding='utf-8')
        report['specWritten'] = True
    elif not spec.get('frozen'):
        raise RuntimeError('Spec has no frozen section; review the generated files and run --freeze')
    else:
        stored = {k: v for k, v in spec['frozen'].items() if k not in ('note', 'frozenUtc', 'plan')}
        if json.dumps(stored, sort_keys=True) != json.dumps(signature, sort_keys=True):
            raise RuntimeError('Generated files differ from the frozen spec; review and rerun --freeze')
        stored_plan = [[r['label'], r['meshName'], r['location'], r['plannedWorldBoundsCm']] for r in spec['frozen']['plan']]
        if json.dumps(stored_plan) != json.dumps([[r['label'], r['meshName'], r['location'], r['plannedWorldBoundsCm']] for r in plan]):
            raise RuntimeError('Frozen plan differs from the recomputed plan; rerun --freeze')
    report['totalTriangles'] = total
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


def _enum_name(enum_class, value, candidates):
    for name in candidates:
        if hasattr(enum_class, name) and getattr(enum_class, name) == value:
            return name
    return str(value)


def pick_material(ue, spec, role, receipt):
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if role in receipt['materials']:
        return ue.load_asset(receipt['materials'][role]['assigned'])
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


def apply_collision(ue, spec, mesh):
    setup = mesh.get_editor_property('body_setup')
    if setup is None:
        setup = ue.BodySetup(outer=mesh)
        mesh.set_editor_property('body_setup', setup)
    flag = getattr(ue.CollisionTraceFlag, spec['collision']['meshCollisionTraceFlag'])
    setup.set_editor_property('collision_trace_flag', flag)
    mesh.set_editor_property('lod_for_collision', spec['collision']['lodForCollision'])
    if setup.get_editor_property('collision_trace_flag') != flag:
        raise RuntimeError('collision_trace_flag did not stick on ' + mesh.get_name())


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
        data.set_editor_property(key, value)
    task = ue.AssetImportTask()
    for key, value in dict(filename=str(path), destination_path=source['meshFolder'], destination_name=record['name'],
                           automated=True, async_=False, replace_existing=False, save=False, options=ui, factory=ue.FbxFactory()).items():
        task.set_editor_property(key, value)
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    objects = list(task.get_objects())
    if len(objects) != 1 or not isinstance(objects[0], ue.StaticMesh):
        raise RuntimeError('Import of %s produced %s' % (record['file'], [type(o).__name__ for o in objects]))
    mesh = objects[0]
    if mesh.get_name() != record['name']:
        raise RuntimeError('Imported name %s differs from destination_name %s' % (mesh.get_name(), record['name']))
    apply_collision(ue, spec, mesh)
    info = verify_and_assign(ue, spec, mesh, record, material, assign=True, expected_slots=len(record['parts']))
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if not assets.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('save_loaded_asset failed for ' + record['name'])
    info['uassetSha256'] = sha256_of(ROOT / 'Content' / (_asset_path(mesh)[len('/Game/'):] + '.uasset'))
    return mesh, info


def verify_and_assign(ue, spec, mesh, record, material, assign=True, expected_slots=None):
    box = _static_mesh_box(mesh)
    error = box_error(box, record['bounds_cm'])
    triangles = mesh.get_num_triangles(0)
    if error > spec['source']['boundsToleranceCm']:
        raise RuntimeError('%s bounds differ from canonical by %.4f cm (Y reflection did not round-trip?): %r' % (record['name'], error, box))
    if triangles != record['triangles']:
        raise RuntimeError('%s triangles %d differ from %d' % (record['name'], triangles, record['triangles']))
    slots = len(mesh.get_editor_property('static_materials'))
    if slots < 1:
        raise RuntimeError('%s has no material slots' % record['name'])
    if expected_slots is not None and slots != expected_slots:
        raise RuntimeError('%s has %d material slots, manifest has %d parts' % (record['name'], slots, expected_slots))
    if material is not None and assign:
        for slot in range(slots):
            mesh.set_material(slot, material)
    expected = _asset_path(material) if material is not None else None
    slot_paths = [_asset_path(mesh.get_material(slot)) for slot in range(slots)]
    bad = [slot for slot, path in enumerate(slot_paths) if expected is not None and path != expected]
    if bad:
        raise RuntimeError('Material slots %s on %s do not carry %s' % (bad[:10], record['name'], expected))
    setup = mesh.get_editor_property('body_setup')
    flag = str(setup.get_editor_property('collision_trace_flag')) if setup is not None else None
    wanted = spec['collision']['meshCollisionTraceFlag']
    if setup is None or wanted not in flag:
        raise RuntimeError('%s collision trace flag is %s, expected %s' % (record['name'], flag, wanted))
    return {'asset': _asset_path(mesh), 'file': record['file'], 'triangles': triangles, 'localBoundsCm': box, 'boundsErrorCm': error,
            'materialSlots': slots, 'material': expected, 'collisionTraceFlag': flag}


def winding_report(ue, mesh, record, spec):
    check = spec['windingCheck']
    if not all(hasattr(ue, n) for n in ('GeometryScript_AssetUtils', 'GeometryScript_MeshQueries')):
        return {'status': 'unavailable', 'passed': False, 'reason': 'GeometryScripting not loaded; launch with -EnablePlugins=GeometryScripting'}
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
    flux = 0.0
    disagreements = 0
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
    signed_volume = flux / 3.0
    expected = sum(p['volume_cm3'] for p in record['parts'])
    relative = abs(signed_volume - expected) / expected if expected else None
    passed = signed_volume > 0 and disagreements == 0 and relative is not None and relative <= check['maxRelativeVolumeError']
    return {'status': 'checked', 'passed': passed, 'triangles': count, 'signedVolumeUEcm3': signed_volume, 'manifestPartVolumeSumCm3': expected,
            'relativeVolumeError': relative, 'faceNormalVsCrossDisagreements': disagreements}


# --------------------------------------------------------------------------
# Engine side: placement
# --------------------------------------------------------------------------

class EnclosurePlacement:
    def __init__(self, ue, spec, helper, run_state, receipt):
        self.ue = ue
        self.spec = spec
        self.helper = helper
        self.run = run_state
        self.receipt = receipt
        path = ROOT / spec['clearance']['architectureManifest']
        manifest = json.loads(path.read_text(encoding='utf-8-sig'))
        self.architecture = {entry['assetName']: entry for entry in manifest['meshes']}

    def platform_deck(self, ring_rows):
        """The future platform deck actor(s): top within tolerance of Z 0 and covering every ring footprint."""
        cfg = self.spec['platform']
        rows = [r for r in self.run.snapshot if r['folder'] == cfg['folder'] and r['meshes']]
        decks = []
        for row in rows:
            top = row['bounds']['max'][2]
            covers = all(row['bounds']['min'][0] <= p['plannedWorldBoundsCm']['min'][0] and row['bounds']['max'][0] >= p['plannedWorldBoundsCm']['max'][0]
                         and row['bounds']['min'][1] <= p['plannedWorldBoundsCm']['min'][1] and row['bounds']['max'][1] >= p['plannedWorldBoundsCm']['max'][1]
                         for p in ring_rows)
            decks.append({'label': row['label'], 'meshes': row['meshes'], 'worldBoundsCm': row['bounds'], 'topZcm': top,
                          'topWithinTolerance': abs(top - cfg['deckTopZcm']) <= cfg['deckTopToleranceCm'], 'coversRingFootprints': covers})
        ok = any(d['topWithinTolerance'] and d['coversRingFootprints'] for d in decks)
        return ok, {'folderActors': len(rows), 'decks': decks, 'ringGroupsAllowed': ok}

    def clearance_candidates(self):
        cfg = self.spec['clearance']
        prefix = cfg['levelAssetPrefix']
        boxes_by_key = {}
        candidates = []
        for row in self.run.snapshot:
            if not row['meshes']:
                continue
            key = None
            if row['folder'] == cfg['unionFolder']:
                names = [m[len(prefix):] for m in row['meshes'] if m and m.startswith(prefix)]
                entry = self.architecture.get(names[0]) if len(names) == 1 and len(row['meshes']) == 1 else None
                if entry is not None and entry.get('semantic') == 'union' and self.helper.box_error(row['bounds'], entry['expectedBoundsUnrealCm']) <= cfg['unionBoundsToleranceCm']:
                    key = names[0]
                    boxes_by_key[key] = self.helper.verify_union_decomposition(entry, cfg['unionBoundsToleranceCm'])
            extent = [row['bounds']['max'][i] - row['bounds']['min'][i] for i in range(3)]
            candidates.append({'label': row['label'], 'folder': row['folder'], 'bounds': row['bounds'], 'unionKey': key,
                               'large': max(extent) > cfg['largeActorExtentCm']})
        return candidates, boxes_by_key

    def overlaps_for(self, planned, candidates, boxes_by_key):
        blockers, envelopes = [], []
        for candidate in candidates:
            if not boxes_overlap_volume(planned, candidate['bounds']):
                continue
            boxes = boxes_by_key.get(candidate['unionKey']) if candidate['unionKey'] else None
            if boxes is not None:
                hits = [b['name'] for b in boxes if boxes_overlap_volume(planned, b)]
                if hits:
                    blockers.append({'label': candidate['label'], 'folder': candidate['folder'], 'kind': 'union_constituent_box', 'constituents': hits[:5]})
                else:
                    envelopes.append({'label': candidate['label'], 'kind': 'hollow_union_envelope_aabb_only'})
            elif candidate['large']:
                envelopes.append({'label': candidate['label'], 'folder': candidate['folder'], 'kind': 'large_actor_aabb_only'})
            else:
                blockers.append({'label': candidate['label'], 'folder': candidate['folder'], 'kind': 'actor_aabb'})
        return blockers, envelopes

    def spawn(self, mesh, record):
        ue = self.ue
        spec = self.spec
        actor = self.run.actors.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(*record['location']), ue.Rotator(pitch=0.0, yaw=0.0, roll=0.0), transient=False)
        if actor is None:
            raise RuntimeError('StaticMeshActor spawn returned None for ' + record['label'])
        actor.set_actor_label(record['label'])
        actor.set_folder_path(spec['folder'] + '/' + record['group'])
        actor.set_editor_property('tags', [ue.Name(spec['actorTag']), ue.Name('Release' + spec['group']), ue.Name(record['group'])])
        component = actor.get_component_by_class(ue.StaticMeshComponent)
        if component is None:
            raise RuntimeError('Spawned actor has no StaticMeshComponent: ' + record['label'])
        if not component.set_static_mesh(mesh):
            raise RuntimeError('set_static_mesh returned False for ' + record['label'])
        if _asset_path(component.get_editor_property('static_mesh')) != _asset_path(mesh):
            raise RuntimeError('Static mesh readback differs for ' + record['label'])
        component.set_collision_profile_name(spec['collision']['componentProfile'])
        if str(component.get_collision_profile_name()) != spec['collision']['componentProfile']:
            raise RuntimeError('Collision profile did not stick on ' + record['label'])
        return actor, component

    def place(self, meshes, rows):
        ue = self.ue
        spec = self.spec
        tolerance = spec['verification']['staticBoundsToleranceCm']
        ring_groups = set(spec['clearance']['ringGroups'])
        candidates, boxes_by_key = self.clearance_candidates()
        clearance = {'actorsConsidered': len(candidates), 'unionsDecomposed': sorted(boxes_by_key), 'perActor': [],
                     'cityOverlap': {'actors': 0, 'byFolder': {}, 'sampleLabels': []}}
        placed = []
        records = []
        try:
            for record in rows:
                info = meshes[record['meshName']]
                planned = translate_box(info['localBoundsCm'], record['location'])
                if box_error(planned, record['plannedWorldBoundsCm']) > tolerance:
                    raise RuntimeError('Imported bounds change the plan for %s by %.4f' % (record['roleTag'], box_error(planned, record['plannedWorldBoundsCm'])))
                blockers, envelopes = self.overlaps_for(planned, candidates, boxes_by_key)
                entry = {'label': record['label'], 'group': record['group'], 'blockers': len(blockers), 'envelopesOnly': len(envelopes),
                         'blockerSample': blockers[:8]}
                clearance['perActor'].append(entry)
                if record['group'] in ring_groups and blockers:
                    raise RuntimeError('%s intersects existing actors %s' % (record['roleTag'], blockers[:5]))
                if record['group'] not in ring_groups:
                    city = clearance['cityOverlap']
                    city['actors'] += len(blockers)
                    for b in blockers:
                        city['byFolder'][b['folder']] = city['byFolder'].get(b['folder'], 0) + 1
                    if len(city['sampleLabels']) < 40:
                        city['sampleLabels'].extend(b['label'] for b in blockers[:3])
                actor, component = self.spawn(info['mesh'], record)
                placed.append(actor)
                placed_bounds = self.helper._actor_bounds(actor)
                if box_error(placed_bounds, planned) > tolerance:
                    raise RuntimeError('Placed %s bounds differ from plan by %.4f' % (record['label'], box_error(placed_bounds, planned)))
                records.append(dict(record, mesh=_asset_path(info['mesh']), kind='StaticMeshActor',
                                    collisionProfile=str(component.get_collision_profile_name()),
                                    collisionEnabled=_enum_name(ue.CollisionEnabled, component.get_collision_enabled(),
                                                                ['NO_COLLISION', 'QUERY_ONLY', 'PHYSICS_ONLY', 'QUERY_AND_PHYSICS', 'PROBE_ONLY', 'QUERY_AND_PROBE']),
                                    placedWorldBoundsCm=placed_bounds, actor=actor))
        except Exception:
            clearance['failed'] = True
            self.receipt['clearanceCheck'] = clearance
            self.run.destroy_all(placed)
            raise
        self.receipt['clearanceCheck'] = clearance
        return records


def _strip(record):
    return {key: value for key, value in record.items() if key != 'actor'}


def run(import_only=False, place_only=False, groups=None, allow_unverified_winding=False):
    import unreal as ue
    spec = load_spec()
    groups = normalise_groups(spec['defaultGroups'] if groups is None else groups)
    omitted = {g: spec.get('deliberateOmissions', {}).get(g, 'not requested by -EnclosureGroups') for g in GROUP_ORDER if g not in groups}
    helper = load_placement_helper(spec)
    offline = offline_check(spec)
    manifest = load_manifest(spec)
    design = load_design(spec)
    plan = build_plan(spec, manifest, design)
    if import_only and place_only:
        raise RuntimeError('-EnclosureImportOnly and -EnclosurePlaceOnly exclude each other')
    if Path(ue.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('A game world is active; never mutate during play')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages present before import')
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    namespace_exists = assets.does_directory_exist(spec['source']['namespace'])
    if namespace_exists and not place_only:
        raise RuntimeError('Existing native namespace preserved: ' + spec['source']['namespace'])
    if place_only and not namespace_exists:
        raise RuntimeError('-EnclosurePlaceOnly needs the imported namespace ' + spec['source']['namespace'])

    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    receipt_path = ROOT / spec['receiptFolder'] / (spec['receiptPrefix'] + stamp + '.json')
    if receipt_path.exists():
        raise RuntimeError('Receipt already exists: ' + str(receipt_path))
    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = {m: sha256_of(helper.disk_path(m, 'umap')) for m in spec['protectedMaps'] if helper.disk_path(m, 'umap').exists()}
    receipt = {
        'status': 'started', 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file), 'mapSha256Before': map_sha_before,
        'protectedMapSha256Before': protected, 'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
        'engineVersion': ue.SystemLibrary.get_engine_version(), 'offlineCheck': offline,
        'switches': {'importOnly': import_only, 'placeOnly': place_only, 'groups': list(groups), 'allowUnverifiedWinding': allow_unverified_winding},
        'deliberateOmissions': omitted, 'sourceReference': spec['sourceReference'],
        'materials': {}, 'meshes': {}, 'windingCheck': {}, 'platformDeck': {}, 'plan': {}, 'placed': [], 'errors': [], 'mapSaved': False,
        'limitations': list(spec['limitations']),
    }
    for group, reason in omitted.items():
        receipt['limitations'].append('Group %r deliberately not placed: %s' % (group, reason))

    def write():
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str) + '\n', encoding='utf-8')
    write()

    saved = False
    try:
        # -- 1. import + materials + collision (or verify an existing import) ----------------
        meshes = {}
        for record in manifest['meshes']:
            material = pick_material(ue, spec, record['materialRole'], receipt)
            if place_only:
                asset_path = spec['source']['meshFolder'] + '/' + record['name']
                if not assets.does_asset_exist(asset_path):
                    raise RuntimeError('Missing imported mesh ' + asset_path)
                mesh = ue.load_asset(asset_path)
                if not isinstance(mesh, ue.StaticMesh):
                    raise RuntimeError('Asset is not a StaticMesh: ' + asset_path)
                info = verify_and_assign(ue, spec, mesh, record, material, assign=False, expected_slots=len(record['parts']))
                info['uassetSha256'] = sha256_of(helper.disk_path(asset_path))
                info['verifiedExistingImport'] = True
            else:
                mesh, info = import_one_mesh(ue, spec, record, material)
            info['mesh'] = mesh
            meshes[record['name']] = info
            receipt['meshes'][record['name']] = {k: v for k, v in info.items() if k != 'mesh'}
            write()
        receipt['status'] = 'meshes_verified' if place_only else 'meshes_saved'
        if place_only and (ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
            raise RuntimeError('-EnclosurePlaceOnly verification dirtied packages; nothing may be re-saved in this mode')

        # -- 2. winding -------------------------------------------------------------------
        all_passed = True
        for record in manifest['meshes']:
            report = winding_report(ue, meshes[record['name']]['mesh'], record, spec)
            receipt['windingCheck'][record['name']] = report
            all_passed = all_passed and report['passed']
        receipt['windingVerified'] = all_passed
        write()
        if import_only:
            receipt['status'] = 'meshes_saved_import_only_no_map_change'
            return receipt
        if not all_passed and spec['windingCheck']['requireForPlacement'] and not allow_unverified_winding:
            receipt['status'] = 'meshes_saved_placement_skipped_winding_unverified'
            receipt['limitations'].append('Placement skipped: winding check did not pass or was unavailable; rerun with -EnclosurePlaceOnly '
                                          '-EnablePlugins=GeometryScripting, or inspect before -EnclosureAllowUnverifiedWinding')
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
            raise RuntimeError('Dirty packages present after loading the map; resolve before checkpointed placement')
        checkpoint = Path(spec['checkpointRoot']) / (spec['checkpointPrefix'] + stamp)
        checkpoint.mkdir(parents=True, exist_ok=False)
        shutil.copy2(map_file, checkpoint / map_file.name)
        if sha256_of(checkpoint / map_file.name) != map_sha_before:
            raise RuntimeError('Checkpoint copy hash differs')
        external_copied = []
        for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
            external = ROOT / 'Content' / folder_name / TARGET[len('/Game/'):]
            if external.exists():
                shutil.copytree(external, checkpoint / folder_name / TARGET[len('/Game/'):])
                external_copied.append(str(external))
        receipt['checkpoint'] = str(checkpoint)
        receipt['oneFilePerActorFoldersCopied'] = external_copied

        run_state = helper.Placement(ue, spec)
        run_state.world = world
        run_state.receipt = receipt
        run_state.receipt_path = receipt_path
        run_state.take_snapshot()
        baseline = run_state.numeric_baseline(run_state.snapshot)
        own_prefix = spec['labelPrefix'] + spec['group'] + '_'
        clashes = [r['label'] for r in run_state.snapshot
                   if r['label'].startswith(own_prefix) or r['folder'] == spec['folder'] or r['folder'].startswith(spec['folder'] + '/')]
        if clashes:
            raise RuntimeError('Existing enclosure release actors preserved; refusing duplicate placement: %s' % clashes[:10])
        for mesh_name, info in meshes.items():
            rows = run_state.actors_with_mesh(info['asset'])
            if rows:
                raise RuntimeError('Mesh %s already present in the map: %s' % (mesh_name, [r['label'] for r in rows]))
        receipt['preExistingReleaseActors'] = [{'label': r['label'], 'folder': r['folder']} for r in run_state.snapshot if r['label'].startswith(spec['labelPrefix'])]
        receipt['actorCountBefore'] = len(run_state.snapshot)
        write()

        # -- 4. platform deck, plan subset, clearance, spawn ----------------------------------
        placement = EnclosurePlacement(ue, spec, helper, run_state, receipt)
        ring_groups = set(spec['clearance']['ringGroups'])
        wanted = [r for r in plan if r['group'] in groups]
        ring_rows = [r for r in wanted if r['group'] in ring_groups]
        deck_ok, deck_report = placement.platform_deck(ring_rows) if ring_rows else (True, {'ringGroupsRequested': False})
        receipt['platformDeck'] = deck_report
        if ring_rows and not deck_ok:
            skipped = sorted({r['group'] for r in ring_rows})
            wanted = [r for r in wanted if r['group'] not in ring_groups]
            for g in skipped:
                receipt['deliberateOmissions'][g] = 'future platform deck actor (folder %s, top Z 0) not found or not covering the ring; group omitted' % spec['platform']['folder']
                receipt['limitations'].append('Group %r omitted: platform deck check failed' % g)
        receipt['plan'] = {'groups': list(groups), 'plannedActors': len(wanted), 'actors': wanted}
        write()
        records = placement.place(meshes, wanted)
        receipt['placed'] = [_strip(r) for r in records]
        write()
        if not records:
            receipt['status'] = 'meshes_saved_nothing_placed_map_unchanged'
            return receipt
        current = run_state.numeric_baseline(run_state.take_snapshot())
        changed = [name for name, row in baseline.items() if current.get(name) != row]
        if changed:
            raise RuntimeError('Pre-existing actors changed before save: %s' % changed[:10])

        # -- 5. save, reopen, read back --------------------------------------------------
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
            close, error = pose_close(row['pose'], record['location'], record['rotation'], record['scale'], verify['transformToleranceCm'])
            bounds_error = box_error(row['bounds'], record['plannedWorldBoundsCm'])
            component = row['actor'].get_component_by_class(ue.StaticMeshComponent)
            entry = {'label': record['label'], 'folder': row['folder'], 'meshPath': row['meshes'], 'pose': row['pose'], 'worldBoundsCm': row['bounds'],
                     'poseErrorCm': error, 'boundsErrorCm': bounds_error, 'collisionProfile': str(component.get_collision_profile_name()),
                     'materials': sorted({_asset_path(component.get_material(i)) for i in range(component.get_num_materials())})}
            readback.append(entry)
            if row['meshes'] != [record['mesh']]:
                raise RuntimeError('Reopened mesh differs for ' + record['label'])
            if not close or bounds_error > verify['staticBoundsToleranceCm']:
                raise RuntimeError('Reopened transform/bounds differ for %s (pose %.4f, bounds %.4f)' % (record['label'], error, bounds_error))
            if row['folder'] != spec['folder'] + '/' + record['group']:
                raise RuntimeError('Reopened folder differs for ' + record['label'])
        receipt['reopenedReadback'] = readback
        receipt['actorCountAfter'] = len(reopened)
        receipt['status'] = 'enclosure_saved_reopened_visual_and_walk_acceptance_pending'
        return receipt
    except Exception as error:
        receipt['errors'].append(repr(error))
        if saved:
            receipt['status'] = 'failed_after_save_checkpoint_available'
        elif receipt['meshes'] and not place_only:
            receipt['status'] = 'failed_partial_assets_preserved_map_unchanged'
        else:
            receipt['status'] = 'failed_before_import_nothing_changed' if not place_only else 'failed_before_save_map_unchanged'
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
    return 'release_import_enclosure.py' in command_line and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line)


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    tokens = command_line.split()
    groups = None
    for token in tokens:
        if token.startswith('-enclosuregroups='):
            groups = normalise_groups(token.split('=', 1)[1].strip('"'))
    try:
        receipt = run(import_only='-enclosureimportonly' in tokens, place_only='-enclosureplaceonly' in tokens, groups=groups,
                      allow_unverified_winding='-enclosureallowunverifiedwinding' in tokens)
        ue.log('release_import_enclosure: %s placed %s winding_ok %s' % (receipt['status'], receipt.get('placedActorCount'), receipt.get('windingVerified')))
    except Exception as error:
        ue.log_error('release_import_enclosure failed: ' + repr(error))
        raise
    finally:
        if '-executepythonscript' in command_line and '-run=pythonscript' not in command_line:
            ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        print(json.dumps(offline_check(freeze='--freeze' in sys.argv), indent=2, default=str))
elif _invoked_as_native_script():
    _main()
