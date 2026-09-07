"""Explicit run() in idle UE5.8 editor; only the saved future scenario is edited.

Uses the native-tested keilim OBJ/FbxFactory adapter, not the Blender-meter OBJs.
This is a platform overlay staging pass. Raised terrain/trees/routes remain pending.
Local API references (UE_5.8/Engine/Source):
- Editor/MaterialEditor/Public/MaterialEditingLibrary.h:296 scalar default readback.
- Editor/UnrealEd/Classes/Factories/FbxImportUI.h and FbxStaticMeshImportData.h.
- Editor/UnrealEd/Classes/Factories/FbxFactory.h (verified create_heikhal_keilim.py).
- Editor/UnrealEd/Public/FileHelpers.h save/reopen API.
Native adapter and collision recipe already exercised by keilim and streets importers.
"""
import hashlib
import json
import math
import shutil
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
FOLDER = ROOT / 'SourceAssets/FutureMountV1'
MAP = '/Game/MikdashV3/FutureMountV1/L_FutureMount'
DEST = '/Game/MikdashV3/FutureMountV1/Platform'
MATERIALS = '/Game/MikdashV3/MaterialReview/JerusalemStoneV2/'
REMOVED = {
    '/Game/MikdashV3/JerusalemContext/Streets/SM_Jerusalem_Landmark_09_Whole',
    '/Game/MikdashV3/JerusalemContext/Buildings/SM_JerusalemBuildings_Large_07279',
}
PROTECTED = '/Game/MikdashV3/JerusalemContext/Buildings/SM_JerusalemBuildings_Grid_N002_P001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_adapters():
    """Offline-safe conversion; canonical UE centimeters remain authoritative."""
    source = FOLDER / 'mount-platform.mesh.json'
    manifest = json.loads((FOLDER / 'mount-platform-generation.json').read_text())
    assert sha(source) == manifest['files'][source.name]['sha256'], 'Mesh source changed'
    data = json.loads(source.read_text())
    assert data['anchorAlreadyApplied'] is True
    records = []
    out = FOLDER / 'NativeImportAdapter'
    out.mkdir(exist_ok=True)
    for kind, material in [('surface', 'PavingReview'), ('skirt', 'WallReview')]:
        entry = data[kind]
        vertices, triangles = entry['vertices'], entry['triangles']
        name = 'SM_MountPlatform_' + kind.title()
        lines = ['# Native import adapter: centimeters, reflected Y, reversed winding', 'o ' + name]
        index = 1
        for face in triangles:
            a, b, c = [vertices[i] for i in face]
            adapted = [(p[0], -p[1], p[2]) for p in (a, c, b)]
            first, second, third = adapted
            ab = [second[i]-first[i] for i in range(3)]
            ac = [third[i]-first[i] for i in range(3)]
            normal = [ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0]]
            nlen = math.sqrt(sum(v*v for v in normal))
            edge = math.sqrt(sum(v*v for v in ab))
            assert nlen > 1e-8 and edge > 1e-8
            if kind == 'surface':
                assert normal[2] > 0 and all(abs(p[2]) < 1e-8 for p in adapted)
            unit = [v/edge for v in ab]
            uv = [(0, 0), (edge/100, 0), (sum(ac[i]*unit[i] for i in range(3))/100, nlen/edge/100)]
            lines.extend('v %.9f %.9f %.9f' % p for p in adapted)
            lines.extend('vt %.9f %.9f' % p for p in uv)
            lines.extend(['vn %.12f %.12f %.12f' % tuple(v/nlen for v in normal)]*3)
            lines.append('f ' + ' '.join('%d/%d/%d' % (i, i, i) for i in range(index, index+3)))
            index += 3
        path = out / (name + '.obj')
        path.write_text('\n'.join(lines)+'\n', encoding='ascii')
        records.append(dict(name=name, path=str(path), sha256=sha(path), triangles=len(triangles),
            material=MATERIALS+'M_JerusalemStoneV2_'+material,
            bounds={key: [fn(p[i] for p in vertices) for i in range(3)] for key, fn in [('min', min), ('max', max)]}))
    return records


def run(resume_native01=False):
    import unreal as ue
    assert Path(ue.Paths.project_dir()).resolve() == ROOT
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    assert not editor.get_game_world(), 'Stop play before staging platform'
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Preserve unsaved map work'
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'Preserve unsaved content work'
    assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    assert assets.does_asset_exist(MAP), 'Create the reviewed future scenario first'
    if not resume_native01:
        assert not assets.does_directory_exist(DEST), 'Existing platform namespace preserved; inspect prior run'
    original = ROOT / 'Content/MikdashV3/Maps/Courtyard.umap'
    scenario = ROOT / 'Content/MikdashV3/FutureMountV1/L_FutureMount.umap'
    checkpoint = FOLDER / 'Checkpoints/BeforePlatform/L_FutureMount.umap'
    if resume_native01:
        assert checkpoint.exists() and sha(scenario) == sha(checkpoint) == '60540f658ccfeff733c0f8e1890e9b8f378b05baabd2f6f6402ad779f2f64d30'
        surface_file = ROOT / 'Content/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Surface.uasset'
        assert sha(surface_file) == '734ac858eb884e9bbf81ef45bfd9059103b48ca6e2ba279de4d159c5b8b8001c'
        listed = assets.list_assets(DEST, recursive=True, include_folder=False)
        assert len(listed) == 1 and listed[0].split('.')[0] == DEST+'/SM_MountPlatform_Surface'
        prior_path = FOLDER / 'native-platform-import.json'
        prior = json.loads(prior_path.read_text())
        assert prior['status'] == 'failed_partial_state_preserved_inspect_before_retry'
        attempt = 1
        archive = FOLDER / ('native-platform-import-native%02d-failed.json' % attempt)
        while archive.exists():
            attempt += 1
            archive = FOLDER / ('native-platform-import-native%02d-failed.json' % attempt)
        shutil.copy2(prior_path, archive)
    else:
        assert not checkpoint.exists(), 'Existing checkpoint preserved; review prior run'
    before = sha(original)
    report = dict(status='started', map=MAP, originalMapSha256=before, meshes=[],
        limitations=['Overlay only: raised Mount terrain, old road ribbons and trees remain to be clipped or removed by boundary.',
        'Gateway and Kotel approach stairs are not built by this pass.',
        'Collision configuration readback is not walking or packaged collision acceptance.',
        'World-scale material settings are verified; seams on oblique skirt faces and visuals remain pending.'])
    try:
        records = prepare_adapters()
        spec = json.loads((ROOT / 'SourceAssets/visual-review/jerusalem-stone-v2-spec.json').read_text())
        profiles = {p['assetName']: p for p in spec['profiles']}
        def material_check(path):
            material = assets.load_asset(path)
            assert isinstance(material, ue.Material), path
            profile = profiles[path.rsplit('/', 1)[1]]
            values = {}
            for key, expected in profile['parameters'].items():
                value = ue.MaterialEditingLibrary.get_material_default_scalar_parameter_value(material, key)
                assert abs(value-expected) < 1e-5, (key, value, expected)
                values[key] = value
            assert ue.MaterialEditingLibrary.get_material_property_input_node(material, ue.MaterialProperty.MP_WORLD_POSITION_OFFSET) is None
            return material, values
        for record in records:
            material_check(record['material'])
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        assert levels.load_level(MAP)
        def mesh_path(actor):
            component = actor.get_component_by_class(ue.StaticMeshComponent)
            mesh = component.get_editor_property('static_mesh') if component else None
            return mesh.get_path_name().split('.')[0] if mesh else None
        def snapshot():
            return sorted((a.get_name(), mesh_path(a) or '', str(a.get_actor_transform())) for a in actors.get_all_level_actors())
        baseline = snapshot()
        assert not any(row[1] in REMOVED for row in baseline)
        assert any(row[1] == PROTECTED for row in baseline), 'Protected Western Wall asset missing'
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        if not resume_native01:
            shutil.copy2(scenario, checkpoint)
        assert sha(checkpoint) == sha(scenario)
        report['checkpoint'] = str(checkpoint)
        for record in records:
            reuse = resume_native01 and record['name'] == 'SM_MountPlatform_Surface'
            if reuse:
                mesh = assets.load_asset(DEST+'/'+record['name'])
                assert isinstance(mesh, ue.StaticMesh)
                assert mesh.get_material(0) == material_check(record['material'])[0]
                assert mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag') == ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
            else:
                ui = ue.FbxImportUI()
                for key, value in dict(automated_import_should_detect_type=False, mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH,
                    import_as_skeletal=False, import_mesh=True, import_animations=False, import_materials=False,
                    import_textures=False, create_physics_asset=False).items():
                    ui.set_editor_property(key, value)
                data = ui.get_editor_property('static_mesh_import_data')
                for key, value in dict(combine_meshes=True, transform_vertex_to_absolute=True, bake_pivot_in_vertex=False,
                    convert_scene=False, convert_scene_unit=False, force_front_x_axis=False, import_uniform_scale=1.0,
                    auto_generate_collision=False, build_nanite=False, generate_lightmap_u_vs=False, remove_degenerates=True,
                    normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():
                    data.set_editor_property(key, value)
                task = ue.AssetImportTask()
                for key, value in dict(filename=record['path'], destination_path=DEST, destination_name=record['name'], automated=True,
                    async_=False, replace_existing=False, save=False, options=ui, factory=ue.FbxFactory()).items():
                    task.set_editor_property(key, value)
                ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
                objects = list(task.get_objects())
                assert len(objects) == 1 and isinstance(objects[0], ue.StaticMesh)
                mesh = objects[0]
            imported_bounds = mesh.get_bounding_box()
            actual_bounds = {'min': [imported_bounds.min.x, imported_bounds.min.y, imported_bounds.min.z],
                'max': [imported_bounds.max.x, imported_bounds.max.y, imported_bounds.max.z]}
            assert max(abs(actual_bounds[k][i]-record['bounds'][k][i]) for k in actual_bounds for i in range(3)) < 0.05
            assert mesh.get_num_triangles(0) == record['triangles']
            material, values = material_check(record['material'])
            mesh.set_material(0, material)
            setup = mesh.get_editor_property('body_setup')
            if setup is None:
                setup = ue.BodySetup(outer=mesh)
                mesh.set_editor_property('body_setup', setup)
            setup.set_editor_property('collision_trace_flag', ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            setup.set_editor_property('double_sided_geometry', True)
            mesh.set_editor_property('lod_for_collision', 0)
            assert assets.save_loaded_asset(mesh, only_if_is_dirty=False)
            actor = actors.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(0, 0, 0), ue.Rotator(), transient=False)
            assert actor
            actor.set_actor_label(record['name'])
            actor.set_folder_path('FutureMountV1/Platform')
            component = actor.get_component_by_class(ue.StaticMeshComponent)
            assert component.set_static_mesh(mesh)
            component.set_mobility(ue.ComponentMobility.STATIC)
            component.set_collision_profile_name('BlockAll')
            record['materialParametersCm'] = values
        world = editor.get_editor_world()
        assert world.get_outermost().get_name() == MAP
        assert ue.EditorLoadingAndSavingUtils.save_map(world, MAP)
        assert levels.load_level(MAP)
        current = snapshot()
        assert not any(row[1] in REMOVED for row in current)
        assert [r for r in current if not r[1].startswith(DEST+'/')] == baseline
        for record in records:
            path = DEST+'/'+record['name']
            matches = [a for a in actors.get_all_level_actors() if mesh_path(a) == path]
            assert len(matches) == 1
            actor = matches[0]
            position, scale, rotation = actor.get_actor_location(), actor.get_actor_scale3d(), actor.get_actor_rotation()
            assert max(abs(position.x), abs(position.y), abs(position.z), abs(scale.x-1), abs(scale.y-1), abs(scale.z-1),
                abs(rotation.pitch), abs(rotation.yaw), abs(rotation.roll)) < 1e-6
            component = actor.get_component_by_class(ue.StaticMeshComponent)
            mesh = component.get_editor_property('static_mesh')
            bounds = mesh.get_bounding_box()
            actual = {'min': [bounds.min.x, bounds.min.y, bounds.min.z], 'max': [bounds.max.x, bounds.max.y, bounds.max.z]}
            error = max(abs(actual[k][i]-record['bounds'][k][i]) for k in actual for i in range(3))
            assert error < 0.05 and mesh.get_num_triangles(0) == record['triangles']
            material, values = material_check(record['material'])
            assert mesh.get_material(0) == material and component.get_material(0) == material
            assert str(component.get_collision_profile_name()) == 'BlockAll'
            setup = mesh.get_editor_property('body_setup')
            assert setup.get_editor_property('collision_trace_flag') == ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
            assert setup.get_editor_property('double_sided_geometry')
            assert mesh.get_editor_property('lod_for_collision') == 0
            report['meshes'].append(dict(asset=path, boundsErrorCm=error, triangles=record['triangles'],
                material=record['material'], materialParameters=values, transformIdentity=True, collision='LOD0 complex-as-simple BlockAll double-sided'))
        assert len(current) == len(baseline)+2
        assert sha(original) == before
        report.update(status='overlay_saved_reopened_terrain_clipping_and_visual_acceptance_pending',
            originalMapUnchanged=True, previousScenarioActorsUnchanged=True, removedAlAqsaActorsRemainAbsent=True,
            scenarioSha256=sha(scenario), sourceGeometrySha256=sha(FOLDER/'mount-platform.mesh.json'))
    except Exception as error:
        report.update(status='failed_partial_state_preserved_inspect_before_retry', error=str(error))
        raise
    finally:
        report['originalMapUnchanged'] = sha(original) == before
        (FOLDER / 'native-platform-import.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return report



def verify_existing():
    """Read-only native03 recovery audit; never imports, places or saves anything.

    FileHelpers.h:64 LoadMap accepts an absolute package filename. Load checkpoint
    as a template so its disk copy cannot become an accidental save destination.
    """
    import unreal as ue
    assert Path(ue.Paths.project_dir()).resolve() == ROOT
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    assert not editor.get_game_world()
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    scenario = ROOT/'Content/MikdashV3/FutureMountV1/L_FutureMount.umap'
    original = ROOT/'Content/MikdashV3/Maps/Courtyard.umap'
    checkpoint = FOLDER/'Checkpoints/BeforePlatform/L_FutureMount.umap'
    hashes = {str(p): sha(p) for p in (scenario,original,checkpoint)}
    receipt = FOLDER/'native-platform-existing-verification-03.json'
    assert not receipt.exists(), 'Prior read-only verification receipt preserved'
    report = dict(status='started_read_only',checks=[],hashesBefore=hashes)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    import collections
    def mesh_path(actor):
        component=actor.get_component_by_class(ue.StaticMeshComponent)
        mesh=component.get_editor_property('static_mesh') if component else None
        return mesh.get_path_name().split('.')[0] if mesh else ''
    def numeric(actor):
        p=actor.get_actor_location();r=actor.get_actor_rotation();s=actor.get_actor_scale3d()
        return (p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z)
    def snapshots():
        result=[];old=[]
        for actor in actors.get_all_level_actors():
            result.append((actor.get_actor_label(),actor.get_class().get_path_name(),mesh_path(actor),numeric(actor)))
            old.append((actor.get_name(),mesh_path(actor),str(actor.get_actor_transform())))
        return result,old
    try:
        # Must run in a FRESH commandlet before loading L_FutureMount: the
        # checkpoint retains the same internal package identity. Loading current
        # first can resolve that already-loaded package instead of checkpoint bytes.
        assert editor.get_editor_world().get_outermost().get_name() != MAP, 'Use a fresh commandlet; checkpoint must load first'
        assert sha(ROOT/'Content/MikdashV3/MaterialReview/CheckpointAudit/BeforePlatform.umap') == sha(checkpoint)
        assert levels.load_level('/Game/MikdashV3/MaterialReview/CheckpointAudit/BeforePlatform')
        baseline,old_baseline=snapshots()
        assert len(baseline)>7000, 'Checkpoint did not load complete scene'
        assert not any(row[2].startswith(DEST+'/') for row in baseline), 'Checkpoint template resolved current map; do not trust comparison'
        assert levels.load_level(MAP)
        current,old_current=snapshots()
        filtered=[r for r in current if not r[2].startswith(DEST+'/')]
        expected=collections.Counter(baseline);actual=collections.Counter(filtered)
        missing=list((expected-actual).elements());extra=list((actual-expected).elements())
        report.update(baselineActorCount=len(baseline),savedScenarioActorCount=len(current),
            numericMissing=missing[:30],numericExtra=extra[:30],numericDifferenceCount=len(missing)+len(extra),
            legacyStringSnapshotEqual=collections.Counter(old_baseline)==collections.Counter(r for r in old_current if not r[1].startswith(DEST+'/')),
            legacyStringExamples={'checkpoint':old_baseline[:2],'scenario':old_current[:2]})
        assert not missing and not extra, 'Numeric actor comparison differs; inspect receipt'
        assert len(current)==len(baseline)+2
        assert not any(r[2] in REMOVED for r in current)
        assert any(r[2]==PROTECTED for r in current)
        assert levels.load_level(MAP)
        geometry=json.loads((FOLDER/'mount-platform.mesh.json').read_text())
        spec=json.loads((ROOT/'SourceAssets/visual-review/jerusalem-stone-v2-spec.json').read_text())
        profiles={r['assetName']:r for r in spec['profiles']}
        assets=ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        for kind,suffix in [('surface','PavingReview'),('skirt','WallReview')]:
            name='SM_MountPlatform_'+kind.title();path=DEST+'/'+name
            matches=[a for a in actors.get_all_level_actors() if mesh_path(a)==path]
            assert len(matches)==1
            actor=matches[0];assert numeric(actor)==(0,0,0,0,0,0,1,1,1)
            component=actor.get_component_by_class(ue.StaticMeshComponent)
            mesh=component.get_editor_property('static_mesh');bounds=mesh.get_bounding_box()
            actual_bounds={'min':[bounds.min.x,bounds.min.y,bounds.min.z],'max':[bounds.max.x,bounds.max.y,bounds.max.z]}
            vertices=geometry[kind]['vertices']
            expected_bounds={key:[fn(v[i] for v in vertices) for i in range(3)] for key,fn in [('min',min),('max',max)]}
            error=max(abs(actual_bounds[k][i]-expected_bounds[k][i]) for k in actual_bounds for i in range(3))
            assert error<.05 and mesh.get_num_triangles(0)==len(geometry[kind]['triangles'])
            matname='M_JerusalemStoneV2_'+suffix;material=assets.load_asset(MATERIALS+matname)
            assert material and mesh.get_material(0)==material and component.get_material(0)==material
            values={}
            for key,value in profiles[matname]['parameters'].items():
                readback=ue.MaterialEditingLibrary.get_material_default_scalar_parameter_value(material,key)
                assert abs(readback-value)<1e-5;values[key]=readback
            setup=mesh.get_editor_property('body_setup')
            assert setup.get_editor_property('collision_trace_flag')==ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
            assert setup.get_editor_property('double_sided_geometry') and mesh.get_editor_property('lod_for_collision')==0
            assert str(component.get_collision_profile_name())=='BlockAll'
            report['checks'].append(dict(asset=path,boundsErrorCm=error,triangles=mesh.get_num_triangles(0),
                materialParameters=values,collision='LOD0 complex-as-simple double-sided BlockAll',numericTransformIdentity=True))
        report.update(status='saved_platform_read_only_verified_visual_and_terrain_work_pending',
            existingActorsNumericallyUnchanged=True,aqsaActorsAbsent=True,westernWallPresent=True,
            visualAcceptance='PENDING',terrainClipping='PENDING')
    except Exception as error:
        report.update(status='read_only_verification_failed',error=str(error));raise
    finally:
        assert levels.load_level(MAP), 'Restore saved scenario after audit'
        report['hashesAfter']={path:sha(Path(path)) for path in hashes}
        report['allThreeMapFilesUnchanged']=report['hashesAfter']==hashes
        receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        assert report['allThreeMapFilesUnchanged']
    return report
