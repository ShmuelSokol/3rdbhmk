"""UE 5.7 streets + grounded path integration. AUTHORED, NOT NATIVE TESTED.

Import this module from the Unreal Python console after adding this directory
to sys.path. No startup hook, overwrite, automatic save, or cleanup is installed.
"""
from pathlib import Path
import json
import math
import time
import uuid
import unreal
from context_preflight import load_streets

LEVEL = '/Game/MikdashV3/Maps/Courtyard'
DEST = '/Game/MikdashV3/JerusalemContext/Streets'
MATERIAL_DEST = '/Game/MikdashV3/JerusalemContext/StreetMaterials'
FOLDER = 'Jerusalem context/Streets'
TAG = 'MikdashJerusalemStreetsGroundedV3'
FORBIDDEN_LEGACY = {'SM_Jerusalem_StonePaths_03_Grid_P000_N001_ClearanceV2'}
STAGE = None


def _world():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor.get_editor_world()
    if editor.get_game_world() is not None:
        raise RuntimeError('Stop PIE before importing context')
    if world is None or world.get_path_name().split('.')[0] != LEVEL:
        raise RuntimeError('Open the existing Courtyard map; this helper never creates or switches maps')
    return world


def _report(stage):
    stage['report_path'].write_text(json.dumps(stage['report'], indent=2) + '\n', encoding='utf-8')


def _identity(actor):
    p, r, s = actor.get_actor_location(), actor.get_actor_rotation(), actor.get_actor_scale3d()
    if not all(math.isfinite(v) for v in (p.x, p.y, p.z, r.pitch, r.yaw, r.roll, s.x, s.y, s.z)):
        raise RuntimeError('Nonfinite actor transform')
    if max(abs(v) for v in (p.x, p.y, p.z, r.pitch, r.yaw, r.roll)) > 1e-5:
        raise RuntimeError('Actor placement changed; context alignment is already baked')
    if max(abs(v - 1) for v in (s.x, s.y, s.z)) > 1e-5:
        raise RuntimeError('Actor scale changed; FBX already uses calibrated units')


def _component_identity(component):
    p, r, s = component.get_world_location(), component.get_world_rotation(), component.get_world_scale()
    if not all(math.isfinite(v) for v in (p.x, p.y, p.z, r.pitch, r.yaw, r.roll, s.x, s.y, s.z)):
        raise RuntimeError('Nonfinite component transform')
    if max(abs(v) for v in (p.x, p.y, p.z, r.pitch, r.yaw, r.roll)) > 1e-5:
        raise RuntimeError('Component world placement changed; alignment is already baked')
    if max(abs(v - 1) for v in (s.x, s.y, s.z)) > 1e-5:
        raise RuntimeError('Component world scale changed')


def _mesh_check(mesh, record):
    name = record['assetName']
    if mesh.get_path_name().split('.')[0] != DEST + '/' + name:
        raise RuntimeError('Unexpected mesh name or path: ' + mesh.get_path_name())
    if int(mesh.get_num_triangles(0)) != record['triangles']:
        raise RuntimeError('Triangle count changed: ' + name)
    bb = mesh.get_bounding_box()
    actual = {'min': [bb.min.x, bb.min.y, bb.min.z], 'max': [bb.max.x, bb.max.y, bb.max.z]}
    if not all(math.isfinite(v) for values in actual.values() for v in values):
        raise RuntimeError('Nonfinite imported bounds: ' + name)
    error = max(abs(actual[k][i] - record['expectedBoundsUnrealCm'][k][i])
                for k in ('min', 'max') for i in range(3))
    if error > .5:
        raise RuntimeError('Bounds differ by %.6f cm: %s' % (error, name))
    slots = mesh.get_editor_property('static_materials')
    if len(slots) != 1:
        raise RuntimeError('Expected exactly one material slot: ' + name)
    slot_names = {str(slots[0].get_editor_property(k))
                  for k in ('imported_material_slot_name', 'material_slot_name')}
    if record['materialSlots'][0]['fbxMaterialName'] not in slot_names:
        raise RuntimeError('Material slot mismatch: ' + name)
    return {'asset': mesh.get_path_name(), 'triangles': record['triangles'], 'boundsErrorCm': error}


def _material(profile):
    name = profile['fbxMaterialName']
    mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, MATERIAL_DEST, unreal.Material, unreal.MaterialFactoryNew())
    if mat is None:
        raise RuntimeError('Material creation failed: ' + name)
    # These six source materials are opaque, scalar colors; no gamma correction.
    mat.set_editor_property('two_sided', profile['twoSided'])
    edit = unreal.MaterialEditingLibrary
    rgb = edit.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -300, 0)
    rgb.set_editor_property('constant', unreal.LinearColor(*profile['color'], 1.0))
    if not edit.connect_material_property(rgb, '', unreal.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('Base color connection failed: ' + name)
    nodes = []
    for row, (value, prop) in enumerate(((profile['roughness'], unreal.MaterialProperty.MP_ROUGHNESS),
                                       (profile['metalness'], unreal.MaterialProperty.MP_METALLIC))):
        node = edit.create_material_expression(mat, unreal.MaterialExpressionConstant, -300, 140 + row * 100)
        node.set_editor_property('r', float(value))
        if not edit.connect_material_property(node, '', prop):
            raise RuntimeError('Scalar material connection failed: ' + name)
        nodes.append(node)
    edit.recompile_material(mat)
    return {'asset': mat, 'rgb': rgb, 'scalars': nodes, 'profile': profile}


def _material_check(entry):
    mat, profile = entry['asset'], entry['profile']
    if bool(mat.get_editor_property('two_sided')) != profile['twoSided']:
        raise RuntimeError('Material side policy changed')
    color = entry['rgb'].get_editor_property('constant')
    if not all(math.isfinite(v) for v in (color.r, color.g, color.b)) or max(abs(a - b) for a, b in zip((color.r, color.g, color.b), profile['color'])) > 1e-6:
        raise RuntimeError('Linear material color changed')
    for node, value in zip(entry['scalars'], (profile['roughness'], profile['metalness'])):
        actual = node.get_editor_property('r')
        if not math.isfinite(actual) or abs(actual - value) > 1e-6:
            raise RuntimeError('Material roughness/metalness changed')


def _import_fbx(path):
    ui = unreal.FbxImportUI()
    for key, value in dict(automated_import_should_detect_type=False,
                          mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
                          import_as_skeletal=False, import_mesh=True, import_animations=False,
                          import_materials=False, import_textures=False, create_physics_asset=False).items():
        ui.set_editor_property(key, value)
    options = ui.get_editor_property('static_mesh_import_data')
    for key, value in dict(combine_meshes=False, transform_vertex_to_absolute=True,
                          bake_pivot_in_vertex=False, convert_scene=True, convert_scene_unit=True,
                          force_front_x_axis=False, import_uniform_scale=1.0,
                          auto_generate_collision=False, build_nanite=False, generate_lightmap_u_vs=False,
                          remove_degenerates=False,
                          normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():
        options.set_editor_property(key, value)
    task = unreal.AssetImportTask()
    for key, value in dict(filename=str(path), destination_path=DEST, destination_name='None', automated=True,
                          async_=False, replace_existing=False, save=False, options=ui,
                          factory=unreal.FbxFactory()).items():
        task.set_editor_property(key, value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return list(task.get_objects())


def import_streets(context_dir, patch_dir, execute=False):
    """Read-only preflight by default; execute=True stages unsaved assets and actors."""
    global STAGE
    if STAGE is not None:
        raise RuntimeError('A stage already exists; inspect it rather than importing duplicates')
    data, world = load_streets(context_dir, patch_dir), _world()
    assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for dest in (DEST, MATERIAL_DEST):
        found = assets.list_assets(dest, recursive=True, include_folder=False) if assets.does_directory_exist(dest) else []
        disk = Path(unreal.Paths.project_content_dir()) / dest.removeprefix('/Game/')
        if found or (disk.exists() and any(disk.rglob('*.uasset'))):
            raise RuntimeError('Destination already contains assets: ' + dest)
    before = actors.get_all_level_actors()
    source_names = {r['assetName'] for r in [*data['original_records'], data['patch_record']]} | FORBIDDEN_LEGACY
    for actor in before:
        own_mesh = any(c.get_editor_property('static_mesh') and
                       (c.get_editor_property('static_mesh').get_path_name().startswith(DEST + '/') or
                        c.get_editor_property('static_mesh').get_name() in source_names)
                       for c in actor.get_components_by_class(unreal.StaticMeshComponent))
        folder = str(actor.get_folder_path())
        if own_mesh or TAG in [str(t) for t in actor.get_editor_property('tags')] or folder == FOLDER or folder.startswith(FOLDER + '/'):
            raise RuntimeError('Existing street-context actor detected')
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Save existing map edits before starting this stage')
    preflight = {'status': 'read_only_preflight' if not execute else 'starting_import',
                 'nativeExecutionPreviouslyVerified': False, 'summary': data['summary'],
                 'importedMeshCountExpected': 2880, 'enabledActorCountExpected': 2878,
                 'enabledTriangleCountExpected': 306760, 'destination': DEST,
                 'heldOriginalAssetsNeverSpawned': data['original_manifest']['reviewHeldAssets'],
                 'world': world.get_path_name(), 'nativeCollisionAndVisualAcceptance': 'pending',
                 'sourceFiles': data['source_files']}
    if not execute:
        unreal.log(str(preflight))
        return preflight
    report_dir = Path(unreal.Paths.project_dir()) / 'SourceAssets/context-review'
    report_dir.mkdir(parents=True, exist_ok=True)
    stage = {'data': data, 'world': world, 'report': preflight,
             'report_path': report_dir / ('streets-import-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:6] + '.json'),
             'meshes': [], 'actors': [], 'materials': {}, 'checks': []}
    STAGE = stage
    _report(stage)
    try:
        for file, expected_count in ((data['context_dir'] / 'streets.fbx', 2879),
                                     (data['patch_dir'] / 'path-grounded.fbx', 1)):
            imported = _import_fbx(file)
            stage['meshes'].extend(m for m in imported if isinstance(m, unreal.StaticMesh))
            if len(imported) != expected_count or any(not isinstance(m, unreal.StaticMesh) for m in imported):
                raise RuntimeError('Unexpected imported FBX asset count or type: ' + str(file))
        records = {r['assetName']: r for r in [*data['original_records'], data['patch_record']]}
        by_name = {mesh.get_name(): mesh for mesh in stage['meshes']}
        if len(stage['meshes']) != 2880 or set(by_name) != set(records):
            raise RuntimeError('Imported mesh names differ; no fuzzy matching permitted')
        for mesh in stage['meshes']:
            stage['checks'].append(_mesh_check(mesh, records[mesh.get_name()]))
        for profile in data['materials']:
            stage['materials'][profile['fbxMaterialName']] = _material(profile)
        for mesh in stage['meshes']:
            record = records[mesh.get_name()]
            entry = stage['materials'][record['materialSlots'][0]['fbxMaterialName']]
            mesh.set_material(0, entry['asset'])
            setup = mesh.get_editor_property('body_setup')
            if setup is None:
                setup = unreal.BodySetup(outer=mesh)
                mesh.set_editor_property('body_setup', setup)
            setup.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            setup.set_editor_property('double_sided_geometry', entry['profile']['twoSided'])
            mesh.set_editor_property('lod_for_collision', 0)
        for record in data['effective_records']:
            mesh = by_name[record['assetName']]
            actor = actors.spawn_actor_from_object(mesh, unreal.Vector(0, 0, 0), unreal.Rotator(), transient=False)
            if actor is None:
                raise RuntimeError('Street actor spawn failed')
            stage['actors'].append(actor)
            actor.set_actor_label(mesh.get_name())
            actor.set_folder_path(FOLDER)
            actor.set_editor_property('tags', [unreal.Name(TAG)])
            component = actor.get_component_by_class(unreal.StaticMeshComponent)
            component.set_mobility(unreal.ComponentMobility.STATIC)
            component.set_collision_profile_name('BlockAll')
            _identity(actor)
        _verify_stage(stage)
        stage['report'].update(status='staged_unsaved_requires_review_and_save', meshChecks=stage['checks'],
                               actorCount=len(stage['actors']), collisionPolicy='LOD0 complex-as-simple BlockAll; actual walking, route joins and cook unverified')
        _report(stage)
        unreal.log('Street context staged UNSAVED. Inspect it, then call save_streets_import().')
        return stage['report']
    except Exception as exc:
        stage['report'].update(status='FAILED_PARTIAL_UNSAVED_STATE_REQUIRES_REVIEW', error=str(exc),
                               createdAssets=[m.get_path_name() for m in stage['meshes']],
                               createdMaterials=[v['asset'].get_path_name() for v in stage['materials'].values()],
                               createdActors=[a.get_path_name() for a in stage['actors']], meshChecks=stage['checks'],
                               noAutomaticDeletion=True)
        _report(stage)
        raise


def _verify_stage(stage):
    if _world() != stage['world']:
        raise RuntimeError('Map/world changed')
    records = {r['assetName']: r for r in [*stage['data']['original_records'], stage['data']['patch_record']]}
    for mesh in stage['meshes']:
        _mesh_check(mesh, records[mesh.get_name()])
    for entry in stage['materials'].values():
        _material_check(entry)
    names = []
    for actor in stage['actors']:
        _identity(actor)
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        mesh = component.get_editor_property('static_mesh') if component else None
        if mesh is None or mesh not in stage['meshes']:
            raise RuntimeError('Actor mesh changed')
        _component_identity(component)
        names.append(mesh.get_name())
        if TAG not in [str(x) for x in actor.get_editor_property('tags')] or not component.is_query_collision_enabled():
            raise RuntimeError('Actor ownership or collision changed')
        if component.get_collision_profile_name() != unreal.Name('BlockAll'):
            raise RuntimeError('Collision profile changed')
        if component.get_editor_property('mobility') != unreal.ComponentMobility.STATIC or mesh.get_editor_property('lod_for_collision') != 0:
            raise RuntimeError('Static mobility or collision LOD changed')
        record = records[mesh.get_name()]
        entry = stage['materials'][record['materialSlots'][0]['fbxMaterialName']]
        body = mesh.get_editor_property('body_setup')
        if mesh.get_material(0) != entry['asset'] or component.get_material(0) != entry['asset'] or body.get_editor_property('collision_trace_flag') != unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
            raise RuntimeError('Mesh material/collision setup changed')
        if bool(body.get_editor_property('double_sided_geometry')) != entry['profile']['twoSided']:
            raise RuntimeError('Collision sidedness changed')
    expected = {r['assetName'] for r in stage['data']['effective_records']}
    if len(names) != 2878 or len(set(names)) != 2878 or set(names) != expected:
        raise RuntimeError('Enabled actor coverage differs; held source groups must stay unspawned')
    # Cover the current map too: a duplicate added between staging and saving
    # must not silently re-enable either original held path group.
    actual = set()
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = component.get_editor_property('static_mesh')
            if mesh and (mesh.get_path_name().startswith(DEST + '/') or mesh.get_name() in records or mesh.get_name() in FORBIDDEN_LEGACY):
                actual.add((actor.get_path_name(), component.get_path_name()))
    if actual != {(actor.get_path_name(), actor.get_component_by_class(unreal.StaticMeshComponent).get_path_name()) for actor in stage['actors']}:
        raise RuntimeError('Map contains missing or extra street actors, including possibly held source geometry')


def save_streets_import():
    stage = STAGE
    if stage is None or stage['report']['status'] != 'staged_unsaved_requires_review_and_save':
        raise RuntimeError('No complete unsaved street stage')
    _verify_stage(stage)
    assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    try:
        for asset in [*[m['asset'] for m in stage['materials'].values()], *stage['meshes']]:
            if not assets.save_loaded_asset(asset, only_if_is_dirty=False):
                raise RuntimeError('Asset save failed: ' + asset.get_path_name())
        if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level():
            raise RuntimeError('Courtyard map save failed')
        stage['report'].update(status='saved_requires_reload_native_visual_collision_and_cook_review',
                               savedAssets=2886, savedActors=2878)
    except Exception as exc:
        stage['report'].update(status='SAVE_FAILED_PARTIAL_DISK_STATE_REQUIRES_REVIEW', error=str(exc))
        raise
    finally:
        _report(stage)
    return stage['report']
