"""S5 guarded import/apply/fresh verify. Start on Entry with GeometryScripting enabled.

Choose -HaramImport, -HaramApply or -HaramVerify. Preload everything before map
load, cap static-mesh compilation concurrency to one, and save the map once.
Only Candidate48 and newly named planned Haram assets may change.
"""
import collections
import hashlib
import json
import shutil
import sys
import struct
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_precinct_cell_split import FBX_UI, FBX_MESH
from release_precinct_terrain_cut import Native, check_corners

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'SourceAssets/enclosure-review/HaramPrecinctV1'
NS = '/Game/MikdashV3/HaramPrecinctV3'
MAP = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
BASELINES = {
    '2640afae6956b5ae712e09900ba8bad0ebd715158af7bdf126b072bce2307448': 'kotel-restored',
    '030b704651705d46fda2d7e0414619a0025c78dcca85ae3f529e515b77f2f15b': 'first-pilot',
    'fb1d71be1bf880cfaf9131b5825acb1b542c6b5c84c981caeef802c081e535ad': 'second-pilot',
    '7d136738a880b15a4344941ec7ec5d236bfcc2f42d7087e9b10f1faec0d17607': 'third-pilot',
    'bd5985969c45c4e243d6ae3af76302460dc224312b3d3210b9ad17aad1b68dac': 'third-pilot',
    '4a36d0344519d61091015f3a1c84a6abedb0d79045145e5d1409a22c7e419a95': 'third-pilot',
    '94ae4d8789fb45760ba537088313fdf2e38e7f78ccc4fb17d5b7699de9929429': 'wall-pilot',
    '2331c2a4682e74c542197ddf508def4ad7837afd5bddb561ebd334e9e17a1df7': 'platform-pilot',
}
TERRAIN = '/Game/MikdashV3/FutureMountV1/Terrain/SM_JerusalemTerrain_07_07_FutureMountCut'
TWIN = NS + '/SM_Haram_Terrain_07_07'
MATERIALS = {
    'paving': '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Materials/M_PrecinctPlaza_Paving',
    'ashlar': '/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Materials/MI_PrecinctPlaza_Ashlar',
    'limestone': '/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_Building',
    'terrain': '/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_Terrain',
}
PREFIX = 'RELEASE_Haram_'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def disk(package, suffix='.uasset'):
    return ROOT / 'Content' / (package[6:] + suffix)


def position_keys(triangles):
    # Match complete triangles by their three positions; counts and bounds alone
    # cannot detect geometry assigned to the wrong location.
    f32 = lambda value: struct.unpack('<f', struct.pack('<f', value))[0]
    return collections.Counter(tuple(sorted(tuple(round(f32(c), 1) for c in v) for v in tri))
                               for tri in triangles)


def oriented_keys(triangles):
    f32 = lambda value: struct.unpack('<f', struct.pack('<f', value))[0]
    def key(triangle):
        corners = tuple(tuple(round(f32(c),1) for c in p) for p in triangle)
        return min(corners[i:]+corners[:i] for i in range(3))
    return collections.Counter(key(t) for t in triangles)


def obj_triangles(path):
    vertices, triangles = [], []
    for line in path.read_text().splitlines():
        fields = line.split()
        if fields and fields[0] == 'v':
            x, y, z = map(float, fields[1:])
            vertices.append([x, -y, z])
        elif fields and fields[0] == 'f':
            triangles.append([vertices[int(i.split('/')[0])-1] for i in fields[1:]])
    return triangles


def main():
    import unreal as ue
    command = ue.SystemLibrary.get_command_line()
    modes = [m for m in ('Import', 'Apply', 'Verify', 'Audit', 'MapAudit') if '-Haram'+m in command]
    assert len(modes) == 1, 'Choose one Haram mode'
    mode = modes[0]
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    report = dict(status='started', mode=mode, timestampUtc=stamp, scriptSha256=sha(Path(__file__)))
    receipt = OUT / ('native-%s-%s.json' % (mode.lower(), stamp))
    native = Native(ue, 'Candidate48', mode, stamp)
    assets, levels, actors = native.assets, native.levels, native.actors
    map_file = disk(MAP, '.umap')
    protected = sorted(p for p in (ROOT/'Content').rglob('*.umap') if p != map_file)
    protected += [disk(p) for p in [TERRAIN] + list(MATERIALS.values())]
    before = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    report['protectedBefore'] = before
    report['mapSha256Before'] = sha(map_file)
    receipt.write_text(json.dumps(report, indent=2)+'\n')
    try:
        plan = json.loads((OUT/'plan.json').read_text())
        assert plan['namespace'] == NS
        assert plan['generatorSha256'] == sha(ROOT/'Scripts/create_haram_precinct.py')
        assert plan['outlineSha256'] == sha(ROOT/'SourceAssets/enclosure-review/haram-outline.json')
        assert plan['terrain']['buffersSha256'] == sha(OUT/'terrain-buffers.json')
        assert plan['terrain']['sourceSha256'] == sha(ROOT/plan['terrain']['sourceFile'])
        for spec in plan['meshes']:
            assert sha(OUT/spec['file']) == spec['sha256']
        mats = {key: ue.load_asset(path) for key, path in MATERIALS.items()}
        assert all(mats.values())
        source = ue.load_asset(TERRAIN)
        assert source
        if mode == 'MapAudit':
            assert levels.load_level(MAP)
            rows=[]
            for actor in actors.get_all_level_actors():
                label=actor.get_actor_label()
                if actor.get_name()=='StaticMeshActor_6055' or any(s in label for s in ('Street','StonePath','Asphalt')):
                    component=actor.get_component_by_class(ue.StaticMeshComponent)
                    rows.append(dict(name=actor.get_name(),label=label,tags=[str(t) for t in actor.tags],
                                     transform=str(actor.get_actor_transform()),
                                     mesh=component.static_mesh.get_path_name() if component and component.static_mesh else None))
            report['actors']=rows
            report['status']='map-audited'
            return
        if mode == 'Audit':
            (OUT/'native-terrain-source.json').write_text(json.dumps(native.extract(source)))
            sample=ue.load_asset(NS+'/'+plan['meshes'][0]['name'])
            (OUT/'native-solid-sample.json').write_text(json.dumps(native.extract(sample)))
            report['status'] = 'source-extracted'
            return
        assert sha(disk(TERRAIN)) == plan['terrain']['nativeAssetSha256']
        street_meshes={}
        for spec in plan['interiorStreetActors']:
            mesh=ue.load_asset(spec['mesh'])
            assert mesh
            bounds=mesh.get_bounding_box()
            for actual,expected in [(bounds.min,spec['boundsCm']['min']),(bounds.max,spec['boundsCm']['max'])]:
                assert max(abs(a-b) for a,b in zip((actual.x,actual.y,actual.z),expected)) < 1.0, spec['label']+' street bounds'
            street_meshes[spec['label']]=mesh
            file=disk(spec['mesh'])
            protected.append(file)
            before[str(file.relative_to(ROOT))]=sha(file)
        meshes = {}
        report['meshes'] = []
        # Mesh-data access occurs only in the empty Entry world.
        for spec in plan['meshes']:
            path = NS + '/' + spec['name']
            exists = assets.does_asset_exist(path)
            assert exists or mode == 'Import', 'Run import first: '+path
            if exists:
                mesh = ue.load_asset(path)
            else:
                options = ue.FbxImportUI()
                for key, value in FBX_UI.items():
                    options.set_editor_property(key, getattr(ue.FBXImportType, value)
                                                if key == 'mesh_type_to_import' else value)
                data = options.get_editor_property('static_mesh_import_data')
                for key, value in FBX_MESH.items():
                    data.set_editor_property(key, getattr(ue.FBXNormalImportMethod, value)
                                             if key == 'normal_import_method' else value)
                task = ue.AssetImportTask()
                for key, value in dict(filename=str(OUT/spec['file']), destination_path=NS,
                        destination_name=spec['name'], automated=True, async_=False,
                        replace_existing=False, save=False, options=options, factory=ue.FbxFactory()).items():
                    task.set_editor_property(key, value)
                ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
                imported = [obj for obj in task.get_objects() if isinstance(obj, ue.StaticMesh)]
                assert len(imported) == 1
                mesh = imported[0]
                mesh.set_material(0, mats[spec['material']])
                body = mesh.get_editor_property('body_setup')
                body.set_editor_property('collision_trace_flag', ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                nanite = mesh.get_editor_property('nanite_settings')
                nanite.set_editor_property('fallback_target', ue.NaniteFallbackTarget.PERCENT_TRIANGLES)
                nanite.set_editor_property('fallback_percent_triangles', 1.0)
                nanite.set_editor_property('fallback_relative_error', 0.0)
                mesh.set_editor_property('nanite_settings', nanite)
                assert assets.save_loaded_asset(mesh, only_if_is_dirty=False)
            actual = native.extract(mesh)
            assert len(actual) == spec['triangles'], spec['name']+' triangle count'
            assert position_keys(t['positions'] for t in actual) == position_keys(obj_triangles(OUT/spec['file'])), spec['name']+' triangle positions'
            # Unreal's upward terrain faces use clockwise XY winding. The OBJ
            # adapter supplies that reversed face order; cyclic rotation is OK,
            # reversing a face is not. Also prove paving normals point upward.
            assert oriented_keys(t['positions'] for t in actual) == oriented_keys(obj_triangles(OUT/spec['file'])), spec['name']+' triangle winding'
            if spec['name'].startswith('SM_Haram_Deck_'):
                tops=[t for t in actual if all(abs(p[2]-plan['pavingFinishZCm']) < .01 for p in t['positions'])]
                assert tops
                # OBJ contains positions/faces only. Zero source normals are
                # valid only when the saved build settings regenerate them.
                build=ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem).get_lod_build_settings(mesh,0)
                assert build.get_editor_property('recompute_normals') or all(n[2] > .99 for t in tops for n in t['normals']), spec['name']+' paving normal generation'
            assert mesh.get_material(0) == mats[spec['material']]
            assert mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag') == ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
            ns = mesh.get_editor_property('nanite_settings')
            assert ns.get_editor_property('fallback_target') == ue.NaniteFallbackTarget.PERCENT_TRIANGLES
            assert ns.get_editor_property('fallback_relative_error') == 0
            assert ns.get_editor_property('fallback_percent_triangles') == 1
            meshes[spec['name']] = mesh
            report['meshes'].append(dict(name=spec['name'], triangles=len(actual), trianglePositionsMatched=True,
                                        sha256=sha(disk(path)), created=not exists))
            receipt.write_text(json.dumps(report, indent=2)+'\n')
            ue.log('HARAM checked '+spec['name'])
        for spec in plan.get('wallCuts',[]):
            from verify_haram_wall_surfaces import verify as verify_wall_surfaces, rows_with_attributes, Native as WallNative
            assert sha(OUT/'wall-cuts.json')==plan['wallCutsSha256']
            assert sha(disk(spec['mesh']))==spec['sha256']
            protected.append(disk(spec['mesh']));before[str(disk(spec['mesh']).relative_to(ROOT))]=spec['sha256']
            street_meshes[spec['label']]=ue.load_asset(spec['mesh'])
            wall=ue.load_asset(spec['twin']);assert wall
            assert sha(disk(spec['twin']))==spec['twinSha256']
            assert sha(OUT/spec['resultFile'])==spec['resultSha256']
            expected=json.loads((OUT/spec['resultFile']).read_text())
            buffers={key:[v for t in expected for v in t[key]] for key in ('positions','normals','colors')}
            check_corners(native.extract(wall),buffers)
            for i,slot in enumerate(street_meshes[spec['label']].get_editor_property('static_materials')):
                assert wall.get_material(i)==slot.material_interface
            assert wall.get_editor_property('body_setup').get_editor_property('collision_trace_flag')==ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
            ns=wall.get_editor_property('nanite_settings')
            assert ns.get_editor_property('fallback_target')==ue.NaniteFallbackTarget.PERCENT_TRIANGLES and ns.get_editor_property('fallback_percent_triangles')==1
            wall_native=WallNative()
            surface_check=verify_wall_surfaces(
                rows_with_attributes(wall_native,wall_native.source_dynamic_mesh(street_meshes[spec['label']])),
                rows_with_attributes(wall_native,wall_native.source_dynamic_mesh(wall)),
                [g for g in plan['gates'] if g['osmId'] in spec['gateIds']])
            report.setdefault('wallSurfaceChecks',[]).append(dict(label=spec['label'],**surface_check))
            meshes[wall.get_name()]=wall
        # Prove the offline terrain actually corresponds to the native source,
        # including colour and normals, before making a twin from it.
        frozen = json.loads((ROOT/plan['terrain']['sourceFile']).read_text())
        expected = dict(positions=[], normals=[], colors=[])
        for triangle in frozen:
            for key in expected:
                expected[key].extend(triangle[key])
        report['terrainSourceCheck'] = check_corners(native.extract(source), expected)
        buffers = json.loads((OUT/'terrain-buffers.json').read_text())
        if assets.does_asset_exist(TWIN):
            twin = ue.load_asset(TWIN)
        else:
            assert mode == 'Import', 'Terrain import missing'
            twin = native.create_twin(TWIN, buffers, source)
            twin.set_material(0, mats['terrain'])
            ns=twin.get_editor_property('nanite_settings')
            ns.set_editor_property('fallback_target',ue.NaniteFallbackTarget.PERCENT_TRIANGLES)
            ns.set_editor_property('fallback_percent_triangles',1.0)
            ns.set_editor_property('fallback_relative_error',0.0)
            twin.set_editor_property('nanite_settings',ns)
            assert assets.save_loaded_asset(twin, only_if_is_dirty=False)
        report['terrainTwinCheck'] = check_corners(native.extract(twin), buffers)
        assert twin.get_material(0) == mats['terrain']
        ns=twin.get_editor_property('nanite_settings')
        assert ns.get_editor_property('fallback_target') == ue.NaniteFallbackTarget.PERCENT_TRIANGLES
        assert ns.get_editor_property('fallback_percent_triangles') == 1.0
        assert ns.get_editor_property('fallback_relative_error') == 0.0
        assert twin.get_editor_property('body_setup').get_editor_property('collision_trace_flag') == ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
        if mode != 'Import':
            if mode == 'Apply':
                assert sha(map_file) in BASELINES, 'Unreviewed Candidate48 bytes'
            assert levels.load_level(MAP)
            all_actors = list(actors.get_all_level_actors())
            def unique(label):
                found = [a for a in all_actors if a.get_actor_label() == label]
                assert len(found) == 1, (label, len(found))
                return found[0]
            enclosure = unique('RELEASE_EnclosureV2_Precinct')
            original = unique('SM_JerusalemTerrain_07_07')
            street_actors=[unique(spec['label']) for spec in plan['interiorStreetActors']+plan.get('wallCuts',[])]
            for actor in street_actors:
                assert actor.get_component_by_class(ue.StaticMeshComponent).static_mesh == street_meshes[actor.get_actor_label()]
            assert original.get_component_by_class(ue.StaticMeshComponent).static_mesh == source
            assert not enclosure.get_editor_property('build_plaza')
            identity = ue.Transform()
            def at_identity(actor):
                t = actor.get_actor_transform()
                return t.translation == identity.translation and t.rotation == identity.rotation and t.scale3d == identity.scale3d
            def snapshot(actor):
                return dict(transform=str(actor.get_actor_transform()), tags=[str(t) for t in actor.tags],
                            hidden=actor.get_editor_property('hidden'), collision=actor.get_actor_enable_collision())
            untouched = {a.get_path_name(): snapshot(a) for a in all_actors
                         if a not in [enclosure, original]+street_actors and a.get_actor_label() != plan['obsoleteApproachActor']
                         and not a.get_actor_label().startswith(PREFIX)}
            if mode == 'Apply':
                previous=[a for a in all_actors if a.get_actor_label().startswith(PREFIX)]
                pilot = BASELINES[report['mapSha256Before']] != 'kotel-restored'
                platform_pilot=BASELINES[report['mapSha256Before']]=='platform-pilot'
                wall_pilot=BASELINES[report['mapSha256Before']]=='wall-pilot' or platform_pilot
                third=BASELINES[report['mapSha256Before']]=='third-pilot' or wall_pilot
                assert len(previous)==(121 if platform_pilot else 119 if wall_pilot else 110 if third else 109 if pilot else 0), 'Unexpected prior Haram actors'
                for actor in previous:
                    assert at_identity(actor)
                    prior_ns='HaramPrecinctV3' if third else 'HaramPrecinctV1' if BASELINES[report['mapSha256Before']]=='first-pilot' else 'HaramPrecinctV2'
                    allowed=['/Game/MikdashV3/'+prior_ns+'/']
                    if wall_pilot:allowed.append('/Game/MikdashV3/HaramWallPassagesV1/')
                    assert actor.get_component_by_class(ue.StaticMeshComponent).static_mesh.get_path_name().startswith(tuple(allowed))
                checkpoint = ROOT.parent/'ReviewCheckpoints'/('HaramPrecinct-'+stamp)
                checkpoint.mkdir(parents=True)
                shutil.copy2(map_file, checkpoint/'Walkthrough.umap')
                assert sha(checkpoint/'Walkthrough.umap') == report['mapSha256Before']
                report['checkpoint'] = str(checkpoint)
                for actor in previous:
                    assert actors.destroy_actor(actor)
                    all_actors.remove(actor)
                enclosure.set_editor_property('use_haram_outline', True)
                enclosure.set_editor_property('haram_ring_cm', [ue.Vector2D(*p) for p in plan['ringCm']])
                enclosure.set_editor_property('haram_expected_built_actors', len(meshes)+1)
                enclosure.set_editor_property('haram_expected_original_actors', 1+len(street_actors))
                enclosure.set_editor_property('haram_walk_probes', [ue.Vector(*p) for p in plan['walkProbesCm']])
                for field, tag in [('hide_while_modern_city_stands_tags','HaramRingBuilt'),
                                   ('hide_while_wall_stands_tags','HaramRingOriginal')]:
                    tags = list(enclosure.get_editor_property(field))
                    if tag not in [str(t) for t in tags]:
                        enclosure.set_editor_property(field,tags+[ue.Name(tag)])
                if 'HaramRingOriginal' not in [str(t) for t in original.tags]:
                    original.set_editor_property('tags',list(original.tags)+[ue.Name('HaramRingOriginal')])
                original.set_actor_hidden_in_game(True)
                original.set_actor_enable_collision(False)
                for actor in street_actors:
                    assert at_identity(actor)
                    if 'HaramRingOriginal' not in [str(t) for t in actor.tags]:
                        actor.set_editor_property('tags',list(actor.tags)+[ue.Name('HaramRingOriginal')])
                    actor.set_actor_hidden_in_game(True)
                    actor.set_actor_enable_collision(False)
                for name, mesh in list(meshes.items())+[('SM_Haram_Terrain_07_07',twin)]:
                    actor = actors.spawn_actor_from_class(ue.StaticMeshActor, ue.Vector(), ue.Rotator())
                    assert actor
                    actor.set_actor_label(PREFIX+name)
                    actor.set_folder_path('Release/HaramPrecinctV3')
                    actor.set_editor_property('tags',[ue.Name('HaramRingBuilt')])
                    component = actor.get_component_by_class(ue.StaticMeshComponent)
                    component.set_editor_property('mobility',ue.ComponentMobility.STATIC)
                    assert component.set_static_mesh(mesh)
                    for wall_spec in plan.get('wallCuts',[]):
                        if mesh.get_path_name().split('.')[0]==wall_spec['twin']:
                            original_component=unique(wall_spec['label']).get_component_by_class(ue.StaticMeshComponent)
                            for i in range(original_component.get_num_materials()):component.set_material(i,original_component.get_material(i))
                    component.set_collision_profile_name('BlockAll')
                    actor.set_actor_hidden_in_game(False)
                    actor.set_actor_enable_collision(True)
                    all_actors.append(actor)
                if not pilot:
                    old=unique(plan['obsoleteApproachActor'])
                    assert actors.destroy_actor(old)
                    all_actors.remove(old)
            assert enclosure.get_editor_property('use_haram_outline')
            assert 'HaramRingBuilt' in [str(t) for t in enclosure.get_editor_property('hide_while_modern_city_stands_tags')]
            assert 'HaramRingOriginal' in [str(t) for t in enclosure.get_editor_property('hide_while_wall_stands_tags')]
            assert enclosure.get_editor_property('haram_expected_built_actors') == len(meshes)+1
            assert enclosure.get_editor_property('haram_expected_original_actors') == 1+len(street_actors)
            for actor in street_actors:
                assert at_identity(actor) and 'HaramRingOriginal' in [str(t) for t in actor.tags]
                assert actor.get_editor_property('hidden') and not actor.get_actor_enable_collision()
            assert len(enclosure.get_editor_property('haram_ring_cm')) == len(plan['ringCm'])
            for actual, expected in zip(enclosure.get_editor_property('haram_ring_cm'), plan['ringCm']):
                assert abs(actual.x-expected[0]) < .01 and abs(actual.y-expected[1]) < .01
            assert len(enclosure.get_editor_property('haram_walk_probes')) == len(plan['walkProbesCm'])
            for actual, expected in zip(enclosure.get_editor_property('haram_walk_probes'), plan['walkProbesCm']):
                assert max(abs(a-b) for a,b in zip((actual.x,actual.y,actual.z),expected)) < .01
            assert not any(a.get_actor_label() == plan['obsoleteApproachActor'] for a in all_actors)
            assert original.get_editor_property('hidden') and not original.get_actor_enable_collision()
            assert 'HaramRingOriginal' in [str(t) for t in original.tags]
            for name, mesh in list(meshes.items())+[('SM_Haram_Terrain_07_07',twin)]:
                actor = unique(PREFIX+name)
                component = actor.get_component_by_class(ue.StaticMeshComponent)
                assert at_identity(actor) and component.static_mesh == mesh
                assert str(component.get_collision_profile_name()) == 'BlockAll'
                assert component.get_collision_response_to_channel(ue.CollisionChannel.ECC_PAWN) == ue.CollisionResponseType.ECR_BLOCK
                assert actor.get_actor_enable_collision() and not actor.get_editor_property('hidden')
                assert [str(t) for t in actor.tags] == ['HaramRingBuilt']
                for wall_spec in plan.get('wallCuts',[]):
                    if mesh.get_path_name().split('.')[0]==wall_spec['twin']:
                        original_component=unique(wall_spec['label']).get_component_by_class(ue.StaticMeshComponent)
                        assert component.get_num_materials()==original_component.get_num_materials()
                        for i in range(component.get_num_materials()):assert component.get_material(i)==original_component.get_material(i)
            assert untouched == {a.get_path_name():snapshot(a) for a in all_actors if a.get_path_name() in untouched}
            report['unchangedActors'] = len(untouched)
            report['builtActors'] = len(meshes)+1
            if mode == 'Apply':
                assert levels.save_current_level(), 'Map save failed'
        report['status'] = 'passed' if mode != 'Apply' else 'saved-fresh-verify-pending'
    except Exception:
        report['status'] = 'failed'
        report['error'] = traceback.format_exc()
        ue.log_error(report['error'])
    finally:
        report['mapSha256After'] = sha(map_file)
        report['protectedAfter'] = {str(p.relative_to(ROOT)):sha(p) for p in protected}
        if before != report['protectedAfter'] or (mode != 'Apply' and report['mapSha256Before'] != report['mapSha256After']):
            report['status'] = 'failed-hash-guard'
        receipt.write_text(json.dumps(report, indent=2)+'\n')
        ue.SystemLibrary.quit_editor()


if __name__ == '__main__':
    main()
