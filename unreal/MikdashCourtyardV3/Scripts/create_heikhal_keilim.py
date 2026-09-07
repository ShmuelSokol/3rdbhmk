"""Original dimensioned keilim study: offline export(); Unreal run_native().

No map/actor changes or engine launch. Root owns reviewed scene placement.
"""
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
FOLDER = ROOT / 'SourceAssets/vessels-review/HeikhalKeilimV1'
SPEC = ROOT / 'SourceAssets/vessels-review/heikhal-keilim-spec.json'
DEST = '/Game/MikdashV3/MaterialReview/HeikhalKeilimV1'


def bevel_box(center, size, radius=0.5):
    """Six subdivided rounded faces; outward triangle winding, centimeters."""
    half = [v/2 for v in size]
    assert 0 < radius < min(half)
    vertices, faces = [], []
    for axis in range(3):
        u, v = (axis+1)%3, (axis+2)%3
        for sign in (-1, 1):
            start = len(vertices)
            for a in (-half[u], -half[u]+radius, half[u]-radius, half[u]):
                for b in (-half[v], -half[v]+radius, half[v]-radius, half[v]):
                    p = [0., 0., 0.]; p[axis] = sign*half[axis]; p[u] = a; p[v] = b
                    q = [max(-half[i]+radius, min(half[i]-radius, p[i])) for i in range(3)]
                    d = [p[i]-q[i] for i in range(3)]; length = math.sqrt(sum(x*x for x in d))
                    vertices.append(tuple(center[i]+q[i]+d[i]*radius/length for i in range(3)))
            for i in range(3):
                for j in range(3):
                    a = start+i*4+j; b = a+4; c = b+1; d = a+1
                    triangles = [(a,b,c),(a,c,d)]
                    faces.extend(triangles if sign == 1 else [(x,z,y) for x,y,z in triangles])
    return vertices, faces


def ring(center, major=3.0, minor=0.7):
    vertices, faces = [], []
    for i in range(32):
        a = i*math.tau/32
        for j in range(12):
            b = j*math.tau/12; r = major+minor*math.cos(b)
            vertices.append((center[0]+r*math.cos(a), center[1]+minor*math.sin(b), center[2]+r*math.sin(a)))
    for i in range(32):
        for j in range(12):
            a=i*12+j; b=((i+1)%32)*12+j; c=((i+1)%32)*12+(j+1)%12; d=i*12+(j+1)%12
            faces.extend([(a,c,b),(a,d,c)])
    return vertices, faces


def geometry():
    altar = [('Body', bevel_box((0,0,45),(50,50,90),0.6))]
    table = [('Top', bevel_box((0,0,72.5),(100,50,5),0.6))]
    for sx in (-1,1):
        for sy in (-1,1):
            altar.append(('Horn',bevel_box((sx*21,sy*21,95),(8,8,10),0.7)))
            table.append(('Leg',bevel_box((sx*43,sy*18,35),(7,7,70),0.8)))
            table.append(('Foot',bevel_box((sx*43,sy*18,2),(9,9,4),0.7)))
            table.append(('Ring',ring((sx*43,sy*25.8,65))))
    # Gold crown rims and the table's one-tefach frame: profiles are artistic.
    for sy in (-1,1):
        altar.append(('CrownLong',bevel_box((0,sy*24,89),(48,2,3),0.35)))
        table.append(('CrownLong',bevel_box((0,sy*24,75),(98,2,2),0.35)))
        table.append(('FrameLong',bevel_box((0,sy*20.5,65.8333333333),(93,2,8.3333333333),0.4)))
        altar.append(('Ring',ring((0,sy*25.8,79))))
    for sx in (-1,1):
        altar.append(('CrownEnd',bevel_box((sx*24,0,89),(2,48,3),0.35)))
        table.append(('CrownEnd',bevel_box((sx*49,0,75),(2,48,2),0.35)))
        table.append(('FrameEnd',bevel_box((sx*44.5,0,65.8333333333),(2,41,8.3333333333),0.4)))
    return {'SM_GoldenIncenseAltarStudy':altar, 'SM_ShulchanStudy':table}


def export():
    if FOLDER.exists():
        raise RuntimeError('Existing source folder preserved; review before versioned regeneration')
    FOLDER.mkdir(parents=True)
    report = dict(status='original_geometry_exported_native_pending', namespace=DEST, meshes=[],
        source_spec_sha256=hashlib.sha256(SPEC.read_bytes()).hexdigest(),
        convention='Canonical XYZ Unreal cm. Import OBJ reflects Y and reverses winding to compensate previously verified legacy OBJ importer reflection. Per-triangle normals and nondegenerate UV charts; no external images.')
    for name, parts in geometry().items():
        lines = ['# Original Heikhal keilim; import adapter in centimeters', 'o '+name]
        index = 1; triangle_count = 0; canonical = []; volumes = []
        for part, (vertices, faces) in parts:
            canonical.extend(vertices); volume = 0.0
            for face in faces:
                a,b,c = [vertices[i] for i in face]
                volume += sum(a[i]*[b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0]][i] for i in range(3))/6
                adapted = [(p[0],-p[1],p[2]) for p in (a,c,b)]
                a1,b1,c1 = adapted; ab=[b1[i]-a1[i] for i in range(3)]; ac=[c1[i]-a1[i] for i in range(3)]
                normal=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
                nlen=math.sqrt(sum(x*x for x in normal)); edge=math.sqrt(sum(x*x for x in ab))
                assert nlen>1e-8 and edge>1e-8
                n=[x/nlen for x in normal]; u=[x/edge for x in ab]
                cu=sum(ac[i]*u[i] for i in range(3))/10; cv=nlen/edge/10
                for p in adapted: lines.append('v %.9f %.9f %.9f'%p)
                for uv in [(0,0),(edge/10,0),(cu,cv)]: lines.append('vt %.9f %.9f'%uv)
                for _ in range(3): lines.append('vn %.9f %.9f %.9f'%tuple(n))
                lines.append('f '+' '.join('%d/%d/%d'%(i,i,i) for i in range(index,index+3)))
                index+=3; triangle_count+=1
            assert volume>0, 'Inverted source part: '+part
            volumes.append(volume)
        path=FOLDER/(name+'.obj');path.write_text('\n'.join(lines)+'\n',encoding='ascii')
        bounds={key:[fn(p[i] for p in canonical) for i in range(3)] for key,fn in [('min',min),('max',max)]}
        report['meshes'].append(dict(name=name,file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            triangles=triangle_count,parts=len(parts),bounds_cm=bounds,minimum_part_signed_volume_cm3=min(volumes)))
    (FOLDER/'geometry-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def run_native():
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve()!=ROOT or ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Use the intended editor project outside gameplay')
    assets=ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if assets.does_directory_exist(DEST):
        raise RuntimeError('Existing native namespace preserved')
    manifest=json.loads((FOLDER/'geometry-manifest.json').read_text())
    if manifest['source_spec_sha256']!=hashlib.sha256(SPEC.read_bytes()).hexdigest():
        raise RuntimeError('Source spec changed after geometry export')
    result=dict(status='started',created=[],checks=[],map_changed=False,assigned=False)
    try:
        tools=ue.AssetToolsHelpers.get_asset_tools(); ml=ue.MaterialEditingLibrary
        gold=tools.create_asset('M_HeikhalKeilim_Gold',DEST,ue.Material,ue.MaterialFactoryNew())
        if not gold: raise RuntimeError('Gold material factory failed')
        color=ml.create_material_expression(gold,ue.MaterialExpressionConstant3Vector,-300,0)
        color.set_editor_property('constant',ue.LinearColor(1.0,0.766,0.336,1))
        assert ml.connect_material_property(color,'',ue.MaterialProperty.MP_BASE_COLOR)
        for value,prop in [(1.0,ue.MaterialProperty.MP_METALLIC),(0.28,ue.MaterialProperty.MP_ROUGHNESS)]:
            node=ml.create_material_expression(gold,ue.MaterialExpressionConstant)
            node.set_editor_property('r',value);assert ml.connect_material_property(node,'',prop)
        ml.recompile_material(gold);assert assets.save_loaded_asset(gold,only_if_is_dirty=False)
        result['created'].append(gold.get_path_name())
        for record in manifest['meshes']:
            path=FOLDER/record['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256']
            ui=ue.FbxImportUI()
            for key,value in dict(automated_import_should_detect_type=False,mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH,
                import_as_skeletal=False,import_mesh=True,import_animations=False,import_materials=False,import_textures=False,create_physics_asset=False).items():ui.set_editor_property(key,value)
            data=ui.get_editor_property('static_mesh_import_data')
            for key,value in dict(combine_meshes=True,transform_vertex_to_absolute=True,bake_pivot_in_vertex=False,
                convert_scene=False,convert_scene_unit=False,force_front_x_axis=False,import_uniform_scale=1.0,
                auto_generate_collision=False,build_nanite=False,generate_lightmap_u_vs=False,remove_degenerates=True,
                normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():data.set_editor_property(key,value)
            task=ue.AssetImportTask()
            for key,value in dict(filename=str(path),destination_path=DEST+'/Meshes',destination_name=record['name'],
                automated=True,async_=False,replace_existing=False,save=False,options=ui,factory=ue.FbxFactory()).items():task.set_editor_property(key,value)
            tools.import_asset_tasks([task]);objects=list(task.get_objects())
            assert len(objects)==1 and isinstance(objects[0],ue.StaticMesh)
            mesh=objects[0];b=mesh.get_bounding_box(); actual={'min':[b.min.x,b.min.y,b.min.z],'max':[b.max.x,b.max.y,b.max.z]}
            error=max(abs(actual[k][i]-record['bounds_cm'][k][i]) for k in actual for i in range(3))
            assert error<0.05 and mesh.get_num_triangles(0)==record['triangles']
            mesh.set_material(0,gold);assert assets.save_loaded_asset(mesh,only_if_is_dirty=False)
            result['created'].append(mesh.get_path_name());result['checks'].append(dict(name=mesh.get_name(),bounds_error_cm=error,triangles=mesh.get_num_triangles(0)))
        result['status']='native_meshes_saved_unassigned_visual_review_pending'
    except Exception as error:
        result.update(status='failed_partial_assets_preserved',error=str(error));raise
    finally:
        (FOLDER/'native-import.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def place_review():
    """Explicit root-run placement in CourtyardGold only; checkpoint/save/reopen.

    Body studies remain incomplete service assemblies. No smoke, access-rule or
    collision behavior is inferred from their presence.
    """
    import unreal as ue
    review = '/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold'
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    world = editor.get_editor_world()
    if Path(ue.Paths.project_dir()).resolve()!=ROOT or editor.get_game_world():
        raise RuntimeError('Use the intended editor outside gameplay')
    if world.get_outermost().get_name()!=review:
        raise RuntimeError('Load saved SanctuaryFinishesV1 CourtyardGold review map first')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Resolve existing dirty work before checkpointed placement')
    spec=json.loads(SPEC.read_text())
    plan=spec['placement_plan']
    manifest=json.loads((FOLDER/'geometry-manifest.json').read_text())
    records={m['name']:m for m in manifest['meshes']}
    native=json.loads((FOLDER/'native-import.json').read_text())
    if native['status']!='native_meshes_saved_unassigned_visual_review_pending':
        raise RuntimeError('Successful native geometry import receipt required')
    api=ue.get_editor_subsystem(ue.EditorActorSubsystem)
    actors=api.get_all_level_actors()
    placements=[('SM_GoldenIncenseAltarStudy',plan['altar_origin_cm']),
                ('SM_ShulchanStudy',plan['table_origin_cm'])]
    labels=['REVIEW_HeikhalKeilim_'+name for name,_ in placements]
    if any(a.get_actor_label() in labels for a in actors):
        raise RuntimeError('Existing vessel review actors preserved; inspect instead of duplicating')
    floors=[]
    # Imported architecture assets carry the original import filename prefix.
    # Match the exact path and all components as build_sanctuary_finishes.py
    # does; manifest assetName alone is not the native mesh name.
    floor_path='/Game/MikdashV3/Architecture/architecture_'+plan['floor_asset']
    for actor in actors:
        for c in actor.get_components_by_class(ue.StaticMeshComponent):
            m=c.get_editor_property('static_mesh')
            if m and m.get_path_name().split('.')[0]==floor_path:floors.append((actor,c,m))
    if len(floors)!=1:raise RuntimeError('Expected exactly one measured Heichal floor')
    floor,floor_component,floor_mesh=floors[0]
    loc=floor_component.get_world_location();rot=floor_component.get_world_rotation();scale=floor_component.get_world_scale()
    if max(abs(v) for v in (loc.x,loc.y,loc.z,rot.pitch,rot.yaw,rot.roll))>0.001 or max(abs(v-1) for v in (scale.x,scale.y,scale.z))>0.001:
        raise RuntimeError('Measured floor component no longer has baked identity transform')
    box=floor_mesh.get_bounding_box()
    actual_floor={'min':[box.min.x,box.min.y,box.min.z],
                  'max':[box.max.x,box.max.y,box.max.z]}
    if max(abs(actual_floor[k][i]-plan['floor_bounds_cm'][k][i]) for k in actual_floor for i in range(3))>0.05:
        raise RuntimeError('Native Heichal floor no longer matches placement basis')
    planned=[]
    for name,position in placements:
        mesh=ue.load_asset(DEST+'/Meshes/'+name)
        if not isinstance(mesh,ue.StaticMesh):raise RuntimeError('Missing reviewed mesh '+name)
        box=mesh.get_bounding_box()
        local={'min':[box.min.x,box.min.y,box.min.z],'max':[box.max.x,box.max.y,box.max.z]}
        if max(abs(local[k][i]-records[name]['bounds_cm'][k][i]) for k in local for i in range(3))>0.05:
            raise RuntimeError('Vessel dimensions differ from imported receipt')
        bounds={k:[local[k][i]+position[i] for i in range(3)] for k in local}
        if any(bounds['min'][i]<=actual_floor['min'][i] or bounds['max'][i]>=actual_floor['max'][i] for i in (0,1)):
            raise RuntimeError('Planned vessel extends outside clear floor')
        if abs(bounds['min'][2]-actual_floor['max'][2])>0.05:
            raise RuntimeError('Vessel does not rest on measured floor')
        # Nine vertical clearance probes use real complex collision, avoiding
        # the enclosing House union's misleading whole-building AABB.
        for fx in (0.05,0.5,0.95):
            for fy in (0.05,0.5,0.95):
                x=bounds['min'][0]+fx*(bounds['max'][0]-bounds['min'][0])
                y=bounds['min'][1]+fy*(bounds['max'][1]-bounds['min'][1])
                hit=ue.SystemLibrary.line_trace_single_by_profile(world_context_object=world,
                    start=ue.Vector(x,y,bounds['min'][2]+0.5),end=ue.Vector(x,y,bounds['max'][2]+0.5),
                    profile_name='Pawn',trace_complex=True,actors_to_ignore=[floor],
                    draw_debug_type=ue.DrawDebugTrace.NONE,ignore_self=False)
                if hit:raise RuntimeError('Existing blocking geometry at planned vessel: '+name)
        planned.append(dict(name=name,position=position,mesh=mesh,bounds=bounds))
    a,b=[p['bounds'] for p in planned]
    if all(a['min'][i]<b['max'][i] and b['min'][i]<a['max'][i] for i in range(3)):
        raise RuntimeError('Vessel review bodies overlap each other')
    original=ROOT/'Content/MikdashV3/Maps/Courtyard.umap'
    review_file=ROOT/'Content/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold.umap'
    before=hashlib.sha256(original.read_bytes()).hexdigest()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint=ROOT.parent/'ReviewCheckpoints'/('HeikhalKeilim-'+stamp)
    checkpoint.mkdir(parents=True,exist_ok=False)
    shutil.copy2(review_file,checkpoint/'CourtyardGold.umap')
    receipt=dict(status='checkpointed_placement_started',review_map=review,checkpoint=str(checkpoint),
        review_map_sha_before=hashlib.sha256(review_file.read_bytes()).hexdigest(),
        original_courtyard_sha_before=before,floor_bounds_cm=actual_floor,actors=[],
        limitations=['Nine vertical collision probes are not exhaustive triangle intersection or player clearance tests',
          'Table bread/supports/bowls and carrying poles remain incomplete',
          'No menorah substitute, service animation, smoke binding or avatar permissions added'])
    receipt_path=FOLDER/('placement-'+stamp+'.json')
    def write():receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
    write()
    try:
        for p,label in zip(planned,labels):
            # The native object factory returned None in Placement03; use the
            # StaticMeshActor path verified by build_sanctuary_finishes.py.
            actor=api.spawn_actor_from_class(ue.StaticMeshActor,ue.Vector(*p['position']),ue.Rotator(),transient=False)
            if not actor:raise RuntimeError('Vessel actor creation failed')
            actor.set_actor_label(label)
            actor.set_folder_path('Review/HeikhalKeilim_IncompleteAssemblies')
            component=actor.get_component_by_class(ue.StaticMeshComponent)
            if not component or not component.set_static_mesh(p['mesh']):
                raise RuntimeError('Vessel mesh assignment failed; partial review actor preserved')
            component.set_collision_profile_name('NoCollision')
            receipt['actors'].append(dict(label=label,asset=p['mesh'].get_path_name(),position_cm=p['position'],
                expected_bounds_cm=p['bounds'],collision='NoCollision review study'))
        levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        if not levels.save_current_level() or not levels.load_level(review):raise RuntimeError('Review save/reopen failed')
        reopened=api.get_all_level_actors()
        for entry in receipt['actors']:
            matching=[a for a in reopened if a.get_actor_label()==entry['label']]
            if len(matching)!=1:raise RuntimeError('Reopened actor count differs')
            actor=matching[0];c=actor.get_component_by_class(ue.StaticMeshComponent)
            if c.get_editor_property('static_mesh').get_path_name()!=entry['asset']:raise RuntimeError('Reopened vessel assignment differs')
            origin,extent=actor.get_actor_bounds(False)
            bounds={'min':[origin.x-extent.x,origin.y-extent.y,origin.z-extent.z],
                    'max':[origin.x+extent.x,origin.y+extent.y,origin.z+extent.z]}
            error=max(abs(bounds[k][i]-entry['expected_bounds_cm'][k][i]) for k in bounds for i in range(3))
            if error>0.05:raise RuntimeError('Reopened placement bounds differ')
            entry['reopened_bounds_error_cm']=error
        after=hashlib.sha256(original.read_bytes()).hexdigest()
        receipt.update(original_courtyard_sha_after=after,original_courtyard_unchanged=before==after)
        if before!=after:raise RuntimeError('Original Courtyard changed during review placement')
        receipt['status']='review_map_saved_reopened_two_vessels_visual_acceptance_pending'
    except Exception as error:
        receipt.update(status='failed_partial_review_state_preserved',error=str(error));raise
    finally:write()
    return receipt


if __name__=='__main__':
    if '--export' in sys.argv: print(json.dumps(export(),indent=2))
    else: raise SystemExit('Explicit --export offline or call run_native() inside Unreal')
