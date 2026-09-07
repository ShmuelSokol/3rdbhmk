"""Explicit run() with -EnablePlugins=GeometryScripting; future-map-only cut tiles.

Native APIs inspected in installed UE5.8 GeometryScripting headers:
MeshBasicEditFunctions.h:430 AppendBuffersToMesh (positions/normals/FLinearColor).
CreateNewAssetUtilityFunctions.h:177 CreateNewStaticMeshAssetFromMesh.
MeshAssetFunctions.h:268 CopyMeshFromStaticMeshV2, source-model LOD.
MeshQueryFunctions.h:134/358/429 triangle position/normal/color readback.
No OBJ, FBX or source shared asset overwrite. Native original colors are retained:
FbxStaticMeshImport.cpp:943-952 quantizes/transforms original colors on import.
"""
import collections
import hashlib
import itertools
import json
import math
from pathlib import Path
import shutil
import struct

ROOT=Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
FOLDER=ROOT/'SourceAssets/FutureMountV1/terrain-generated'
MAP='/Game/MikdashV3/FutureMountV1/L_FutureMount'
DEST='/Game/MikdashV3/FutureMountV1/Terrain'
ORIGINAL_DEST='/Game/MikdashV3/JerusalemContext/Terrain/'
SOURCE=Path(r'C:\Mikdash\Mikdash-Windows-Transfer\Workspace\output\architecture-review\jerusalem-meshes.json')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def xyz(v):return [v.x,v.y,v.z]
def rgb(v):return [v.r,v.g,v.b,v.a]
def normalized(v):
    length=math.sqrt(sum(x*x for x in v));assert length>.1
    return [x/length for x in v]
def triangle_key(points):
    # StaticMesh source descriptions store float32 positions. Canonicalize ONLY
    # the hash lookup; keep unrounded coordinates for all numerical acceptance.
    f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
    return tuple(sorted((round(f32(p[0])),round(f32(p[1]))) for p in points))


def run(resume_native02=False,verify_only=False):
    import unreal as ue
    assert Path(ue.Paths.project_dir()).resolve()==ROOT
    for name in ['GeometryScript_MeshEdits','GeometryScript_NewAssetUtils','GeometryScript_AssetUtils','GeometryScript_MeshQueries']:
        assert hasattr(ue,name),'Launch with -EnablePlugins=GeometryScripting: '+name
    edits=ue.GeometryScript_MeshEdits;creator=ue.GeometryScript_NewAssetUtils
    query=ue.GeometryScript_MeshQueries;asset_utils=ue.GeometryScript_AssetUtils
    editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    assets=ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
    levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    assert not editor.get_game_world()
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assert not ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    assert not verify_only or resume_native02
    if not resume_native02:
        assert not assets.does_directory_exist(DEST),'Existing replacement assets preserved; inspect previous run'
    manifest=json.loads((FOLDER/'terrain-cut-manifest.json').read_text())
    assert sha(SOURCE)==manifest['sourceSha256']
    source=json.loads(SOURCE.read_text())['meshes'][0]
    records=manifest['tiles'];assert len(records)==4
    data={r['originalAssetName']:json.loads((FOLDER/r['geometryFile']).read_text()) for r in records}
    assert all(sha(FOLDER/r['geometryFile'])==r['sha256'] for r in records)
    original_map=ROOT/'Content/MikdashV3/Maps/Courtyard.umap'
    scenario_file=ROOT/'Content/MikdashV3/FutureMountV1/L_FutureMount.umap'
    checkpoint=FOLDER/'Checkpoints/BeforeTerrainCut/L_FutureMount.umap'
    receipt=FOLDER/'native-terrain-cut.json'
    if resume_native02:
        assert sha(scenario_file)==sha(checkpoint)=='e6fd3565b80d6ad42286a6a2064f1d4355f894d28c71ed624099d2b035b4ed8c'
        partial=ROOT/'Content/MikdashV3/FutureMountV1/Terrain/SM_JerusalemTerrain_07_07_FutureMountCut.uasset'
        assert sha(partial)=='938740c237d65a6c6742d7d2ddaeac9df1d0977f939eeb38790926b76782820d'
        assert list(partial.parent.glob('*.uasset'))==[partial]
        prior=json.loads(receipt.read_text())
        assert prior['status']=='failed_partial_state_preserved' and prior['originalMapAndAssetsUnchanged']
        assert len(prior['checks'])==1 and len(prior['created'])==2
        if verify_only:
            receipt=FOLDER/'native-terrain-cut-native02-readonly.json'
            assert not receipt.exists()
        else:
            archive=FOLDER/'native-terrain-cut-native02-failed.json'
            assert not archive.exists();shutil.copy2(receipt,archive)
    else:
        assert not checkpoint.exists(),'Prior mutating stage preserved'
        if receipt.exists():
            prior=json.loads(receipt.read_text())
            assert prior['status']=='failed_partial_state_preserved' and not prior['created'] and prior['originalMapAndAssetsUnchanged'], 'Prior mutating failure needs review'
            attempt=1
            archive=FOLDER/('native-terrain-cut-preflight-failed-%02d.json'%attempt)
            while archive.exists():
                attempt+=1;archive=FOLDER/('native-terrain-cut-preflight-failed-%02d.json'%attempt)
            shutil.copy2(receipt,archive)
    protected_files=[original_map]+[ROOT/('Content/MikdashV3/JerusalemContext/Terrain/'+r['originalAssetName']+'.uasset') for r in records]
    original_hashes={str(p):sha(p) for p in protected_files}
    report=dict(status='started',map=MAP,originalHashes=original_hashes,checks=[],created=[],
        limitations=['Native source colors preserved; no claim that original FBX gamma/color decisions were physically correct.',
        'Source-model corner readback is verified; rendered/cooked buffers and walking remain separate checks.',
        'Platform and clipped terrain join, approach stairs and old road ribbons require visual/collision route review.'])
    def numeric(transform):
        values=[]
        for point in [(0,0,0),(100,0,0),(0,100,0),(0,0,100)]:values.extend(xyz(transform.transform_location(ue.Vector(*point))))
        return tuple(values)
    def mesh_path(actor):
        component=actor.get_component_by_class(ue.StaticMeshComponent)
        mesh=component.get_editor_property('static_mesh') if component else None
        return mesh.get_path_name().split('.')[0] if mesh else ''
    def scene_snapshot():
        return {a.get_name():(a.get_actor_label(),mesh_path(a),numeric(a.get_actor_transform())) for a in actors.get_all_level_actors()}
    def extract(mesh):
        dynamic=ue.DynamicMesh()
        options=ue.GeometryScriptCopyMeshFromAssetOptions()
        options.set_editor_property('apply_build_settings',False)
        options.set_editor_property('request_tangents',False)
        options.set_editor_property('use_build_scale',False)
        lod=ue.GeometryScriptMeshReadLOD()
        lod.set_editor_property('lod_type',ue.GeometryScriptLODType.SOURCE_MODEL)
        lod.set_editor_property('lod_index',0)
        result=asset_utils.copy_mesh_from_static_mesh_v2(mesh,dynamic,options,lod)
        assert ue.GeometryScriptOutcomePins.SUCCESS in result,'Source-mesh extraction failed'
        triangles=[]
        for tid in range(dynamic.get_triangle_count()):
            position_result=query.get_triangle_positions(dynamic,tid)
            positions=[xyz(v) for v in position_result if isinstance(v,ue.Vector)]
            assert True in position_result and len(positions)==3
            normal_result=query.get_triangle_normals(dynamic,tid)
            normals=[xyz(v) for v in normal_result if isinstance(v,ue.Vector)]
            color_result=query.get_triangle_vertex_colors(dynamic,tid)
            colors=[rgb(v) for v in color_result if isinstance(v,ue.LinearColor)]
            assert len(normals)==len(colors)==3 and True in normal_result and True in color_result
            triangles.append(dict(positions=positions,normals=normals,colors=colors))
        return triangles
    def check_source(mesh,payload):
        old=extract(mesh);assert len(old)==512
        by_key=collections.defaultdict(list)
        for triangle in old:by_key[triangle_key(triangle['positions'])].append(triangle)
        original_triangles={}
        for tid in payload['sourceOriginalTriangles']:
            ids=source['indices'][3*tid:3*tid+3]
            expected=[]
            for sid in ids:
                x,y,z=source['positions'][3*sid:3*sid+3]
                expected.append([(x+17.509700315687695)*50,(z-.5513496449385334)*50,y*50])
            matches=by_key[triangle_key(expected)];assert len(matches)==1
            triangle=matches[0]
            assert all(min(max(abs(p[k]-v[k]) for k in range(3)) for v in triangle['positions'])<.05 for p in expected)
            original_triangles[tid]=triangle
        return original_triangles
    def adapted(payload,old):
        # Expanded vertices are unique per output triangle, so corner attributes
        # remain explicit even if the original native source contains a seam.
        positions=[];normals=[];colors=[];max_snap=0.
        for face,tid in zip(payload['triangles'],payload['triangleSourceIndices']):
            triangle=old[tid];a,b,c=triangle['positions']
            den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            for vi in face:
                point=payload['vertices'][vi];x,y=point[:2]
                corner=next((i for i,p in enumerate(triangle['positions']) if math.hypot(p[0]-x,p[1]-y)<.01),None)
                if corner is not None:
                    p=list(triangle['positions'][corner]);n=list(triangle['normals'][corner]);color=list(triangle['colors'][corner])
                else:
                    w0=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den
                    w1=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den
                    weights=[w0,w1,1-w0-w1];assert min(weights)>-1e-5 and max(weights)<1.00001
                    p=[x,y,sum(weights[i]*triangle['positions'][i][2] for i in range(3))]
                    n=normalized([sum(weights[i]*triangle['normals'][i][axis] for i in range(3)) for axis in range(3)])
                    color=[sum(weights[i]*triangle['colors'][i][axis] for i in range(3)) for axis in range(4)]
                error=max(abs(p[i]-point[i]) for i in range(3));max_snap=max(max_snap,error);assert error<.05
                positions.append(p);normals.append(n);colors.append(color)
        return dict(positions=positions,normals=normals,colors=colors,maxSourceFloatAdjustmentCm=max_snap)
    def check_new(mesh,expected):
        actual=extract(mesh);assert len(actual)*3==len(expected['positions'])
        buckets=collections.defaultdict(list)
        for start in range(0,len(expected['positions']),3):
            buckets[triangle_key(expected['positions'][start:start+3])].append(start)
        max_pos=max_color=max_normal=0.
        for triangle in actual:
            key=triangle_key(triangle['positions']);candidates=buckets[key];assert candidates
            found=None
            for start in candidates:
                for permutation in itertools.permutations(range(3)):
                    pe=max(abs(triangle['positions'][i][k]-expected['positions'][start+permutation[i]][k]) for i in range(3) for k in range(3))
                    ce=max(abs(triangle['colors'][i][k]-expected['colors'][start+permutation[i]][k]) for i in range(3) for k in range(4))
                    ne=max(abs(triangle['normals'][i][k]-expected['normals'][start+permutation[i]][k]) for i in range(3) for k in range(3))
                    if pe<.05 and ce<1e-6 and ne<1e-5:found=(start,pe,ce,ne);break
                if found:break
            assert found,'Native corner geometry/color/normal mismatch'
            candidates.remove(found[0]);max_pos=max(max_pos,found[1]);max_color=max(max_color,found[2]);max_normal=max(max_normal,found[3])
        assert not any(buckets.values())
        return dict(triangles=len(actual),maxPositionErrorCm=max_pos,maxLinearColorError=max_color,maxNormalError=max_normal)
    try:
        assert levels.load_level(MAP)
        baseline=scene_snapshot();expected_scene=dict(baseline)
        matches={}
        for record in records:
            path=ORIGINAL_DEST+record['originalAssetName']
            candidates=[a for a in actors.get_all_level_actors() if mesh_path(a)==path]
            assert len(candidates)==1,'Expected exactly one original tile actor: '+path
            actor=candidates[0];component=actor.get_component_by_class(ue.StaticMeshComponent)
            assert numeric(actor.get_actor_transform())==numeric(ue.Transform())
            assert numeric(component.get_world_transform())==numeric(ue.Transform())
            assert str(component.get_collision_profile_name())=='BlockAll'
            matches[record['originalAssetName']]=(actor,component,component.get_material(0))
        # Complete original-geometry and native-color preflight before any asset creation.
        prepared={}
        for record in records:
            name=record['originalAssetName'];component=matches[name][1]
            prepared[name]=adapted(data[name],check_source(component.get_editor_property('static_mesh'),data[name]))
        if verify_only:
            saved=assets.load_asset(DEST+'/SM_JerusalemTerrain_07_07_FutureMountCut')
            report['checks'].append(check_new(saved,prepared['SM_JerusalemTerrain_07_07']))
            report.update(status='read_only_saved_first_tile_matches_native_source_attributes',mapSaved=False)
            return report
        checkpoint.parent.mkdir(parents=True,exist_ok=True)
        if not resume_native02:shutil.copy2(scenario_file,checkpoint)
        assert sha(checkpoint)==sha(scenario_file)
        report['checkpoint']=str(checkpoint)
        for record in records:
            name=record['originalAssetName'];expected=prepared[name]
            path=DEST+'/'+record['replacementAssetName']
            if resume_native02 and name=='SM_JerusalemTerrain_07_07':
                mesh=assets.load_asset(path);assert isinstance(mesh,ue.StaticMesh)
                report.setdefault('reusedVerifiedAssets',[]).append(path)
            else:
                buffers=ue.GeometryScriptSimpleMeshBuffers()
                buffers.set_editor_property('vertices',[ue.Vector(*v) for v in expected['positions']])
                buffers.set_editor_property('normals',[ue.Vector(*v) for v in expected['normals']])
                buffers.set_editor_property('vertex_colors',[ue.LinearColor(*v) for v in expected['colors']])
                buffers.set_editor_property('triangles',[ue.IntVector(i,i+1,i+2) for i in range(0,len(expected['positions']),3)])
                # Nondegenerate metric UVs support tangent generation without changing
                # original VertexColor material, which does not sample UVs.
                buffers.set_editor_property('uv0',[ue.Vector2D(v[0]/100,v[1]/100) for v in expected['positions']])
                dynamic=ue.DynamicMesh();edits.append_buffers_to_mesh(dynamic,buffers)
                options=ue.GeometryScriptCreateNewStaticMeshAssetOptions()
                for key,value in dict(enable_recompute_normals=False,enable_recompute_tangents=True,enable_nanite=False,
                    enable_collision=True,collision_mode=ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,use_original_vertex_order=True).items():options.set_editor_property(key,value)
                result=creator.create_new_static_mesh_asset_from_mesh(dynamic,path,options)
                meshes=[v for v in result if isinstance(v,ue.StaticMesh)]
                assert len(meshes)==1 and ue.GeometryScriptOutcomePins.SUCCESS in result
                mesh=meshes[0];report['created'].append(path)
            check=check_new(mesh,expected)
            actor,component,material=matches[name];assert material
            mesh.set_material(0,material)
            setup=mesh.get_editor_property('body_setup');assert setup
            setup.set_editor_property('collision_trace_flag',ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            setup.set_editor_property('double_sided_geometry',True);mesh.set_editor_property('lod_for_collision',0)
            assert assets.save_loaded_asset(mesh,only_if_is_dirty=False)
            component.modify();assert component.set_static_mesh(mesh)
            assert component.get_material(0)==material
            label,_,transform=expected_scene[actor.get_name()]
            expected_scene[actor.get_name()]=(label,path,transform)
            report['checks'].append(dict(check,asset=path,originalAsset=ORIGINAL_DEST+name,material=material.get_path_name(),
                maxSourceFloatAdjustmentCm=expected['maxSourceFloatAdjustmentCm']))
        assert scene_snapshot()==expected_scene
        world=editor.get_editor_world();assert world.get_outermost().get_name()==MAP
        assert ue.EditorLoadingAndSavingUtils.save_map(world,MAP)
        assert levels.load_level(MAP)
        assert scene_snapshot()==expected_scene
        for record in records:
            path=DEST+'/'+record['replacementAssetName'];candidates=[a for a in actors.get_all_level_actors() if mesh_path(a)==path];assert len(candidates)==1
            component=candidates[0].get_component_by_class(ue.StaticMeshComponent);mesh=component.get_editor_property('static_mesh')
            check_new(mesh,prepared[record['originalAssetName']])
            assert str(component.get_collision_profile_name())=='BlockAll'
            assert mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')==ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE
            assert mesh.get_editor_property('lod_for_collision')==0
            expected_material=next(r['material'] for r in report['checks'] if r['asset']==path)
            assert component.get_material(0).get_path_name()==mesh.get_material(0).get_path_name()==expected_material
        assert {path:sha(Path(path)) for path in original_hashes}==original_hashes
        report.update(status='four_tiles_replaced_saved_reopened_native_colors_verified_visual_collision_routes_pending',
            originalMapAndAssetsUnchanged=True,allOtherActorsUnchanged=True,scenarioSha256=sha(scenario_file))
    except Exception as error:
        report.update(status='failed_partial_state_preserved',error=str(error));raise
    finally:
        report['originalMapAndAssetsUnchanged']={path:sha(Path(path)) for path in original_hashes}==original_hashes
        receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report
