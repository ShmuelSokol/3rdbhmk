"""AUTHORED_NOT_NATIVE_EXECUTED. Inert UE 5.7 editor importer; no startup hook.
import_instances(DATA_DIR)                 # read-only preflight
import_instances(DATA_DIR, execute=True)   # stage unsaved assets and 5 ISM actors
save_instances_import()                    # separate explicit save
verify_instances_in_current_map(DATA_DIR)  # read-only, also after manual reopen
See README-instances.md for API sources and persistence acceptance gate.
"""
from pathlib import Path
import hashlib, json, math, time, uuid
import unreal
INST_DEST='/Game/MikdashV3/JerusalemContext/DecorativeInstancesV1'
INST_MESH=INST_DEST+'/Meshes'; INST_MAT=INST_DEST+'/Materials'
INST_LEVEL='/Game/MikdashV3/Maps/Courtyard'
INST_FOLDER='Jerusalem context/Decorative instances V1'
INST_TAG='MikdashJerusalemDecorativeInstancesV1'
INST_MANIFEST_SHA='5b80379b80b891dc20809a025bb69a15c5219123d23f6a25e0bc1de81199ec33'
INST_FBX_SHA='0a2bbfd308041fcbbb4d3b71eea77f03b94a9050bd2fdd8cde03a22b70a494da'
if '_INST_STAGE' not in globals(): _INST_STAGE=None

def _inst_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def _inst_data(data_dir):
    root=Path(data_dir)
    if not root.is_absolute() or not root.is_dir():raise ValueError('Use an absolute existing local directory; no drive letter is reserved')
    if not all((root/name).is_file() for name in ('instances-manifest.json','instance-prototypes.fbx')):raise ValueError('Both frozen input files must exist in the selected directory')
    p=root/'instances-manifest.json'
    if _inst_sha(p)!=INST_MANIFEST_SHA:raise ValueError('Manifest differs from independently verified frozen revision')
    data=json.loads(p.read_text(encoding='utf-8-sig'))
    if _inst_sha(root/'instance-prototypes.fbx')!=INST_FBX_SHA or data['fbxSha256']!=INST_FBX_SHA:raise ValueError('Prototype FBX revision mismatch')
    if data['prototypeCount']!=5 or len(data['groups'])!=5 or data['instanceCount']!=44793:raise ValueError('Expected 5 prototypes and 44,793 instances')
    if data['alignment']!={'translationSourceAmos':[17.509700315687695,0,-0.5513496449385334],'degrees':0,'bakedIntoInstanceTranslationOnce':True}:raise ValueError('Unexpected alignment; do not apply another transform')
    for g in data['groups']:
        if len(g['instances'])!=g['instanceCount']:raise ValueError('Instance count mismatch')
        for i,r in enumerate(g['instances']):
            if r['sourceInstanceIndex']!=i:raise ValueError('Source instance order mismatch')
            for k,n in [('translationUnrealCm',3),('quaternionXYZW',4),('scale',3),('matrixUnrealRowMajor',16),('linearTint',3)]:
                if len(r[k])!=n or not all(math.isfinite(v) for v in r[k]):raise ValueError('Invalid numeric transform/tint')
            if abs(sum(v*v for v in r['quaternionXYZW'])-1)>1e-5 or min(r['scale'])<=0:raise ValueError('Nonunit quaternion or nonpositive scale')
    return root,data

def _inst_world():
    s=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    w=s.get_editor_world()
    if s.get_game_world() is not None:raise RuntimeError('Stop PIE before editor authoring')
    if w is None or w.get_path_name().split('.')[0]!=INST_LEVEL:raise RuntimeError('Open the saved Courtyard map; no map switching is performed')
    return w

def _inst_transform(r):
    t=unreal.Transform()
    # Constructor takes Rotator; assign reflected Quat directly to avoid Euler conversion.
    t.set_editor_property('translation',unreal.Vector(*r['translationUnrealCm']))
    t.set_editor_property('rotation',unreal.Quat(*r['quaternionXYZW']))
    t.set_editor_property('scale3d',unreal.Vector(*r['scale']))
    return t

def _inst_transform_error(t,r):
    if t is None:raise RuntimeError('Native instance transform readback failed')
    # Four affinely independent local points test native FTransform against row-major
    # numerical column-vector matrix. 100 cm probes expose axis/scale mistakes.
    m=r['matrixUnrealRowMajor'];error=0.
    for p in [(0.,0.,0.),(100.,0.,0.),(0.,100.,0.),(0.,0.,100.)]:
        out=t.transform_location(unreal.Vector(*p));actual=(out.x,out.y,out.z)
        if not all(math.isfinite(v) for v in actual):raise RuntimeError('Nonfinite native transform probe')
        error=max(error,max(abs(actual[k]-(sum(m[k*4+j]*p[j] for j in range(3))+m[k*4+3])) for k in range(3)))
    if error>.1:raise RuntimeError('Native transform/matrix mismatch >0.1 cm: '+str(error))
    return error

def _inst_scene_references(data):
    """Detect owned actors AND untagged copies by actual component mesh references."""
    names={g['assetName'] for g in data['groups']};actors=[];references=[]
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        found=[]
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            mesh=c.get_editor_property('static_mesh')
            if mesh is not None and (mesh.get_path_name().startswith(INST_MESH+'/') or mesh.get_name() in names):found.append(c)
        if found or INST_TAG in [str(v) for v in a.get_editor_property('tags')] or a.get_actor_label().startswith('JCTX_ISM_') or str(a.get_folder_path()).startswith(INST_FOLDER):actors.append(a)
        references.extend((a,c) for c in found)
    return actors,references

def _inst_mesh_check(mesh,g):
    if mesh.get_path_name().split('.')[0]!=INST_MESH+'/'+g['assetName']:raise RuntimeError('Unexpected mesh destination/name')
    b=mesh.get_bounding_box();expected=g['prototypeExpectedBoundsUnrealCm']
    actual=[getattr(getattr(b,k),axis) for k in ('min','max') for axis in ('x','y','z')]
    if not all(math.isfinite(v) for v in actual):raise RuntimeError('Nonfinite native prototype bounds')
    err=max(abs(getattr(getattr(b,k),axis)-expected[k][i]) for k in ('min','max') for i,axis in enumerate(('x','y','z')))
    if err>.05 or mesh.get_num_triangles(0)!=g['prototypeTriangles']:raise RuntimeError('Prototype bounds/triangle mismatch')
    slots=mesh.get_editor_property('static_materials')
    if len(slots)!=1:raise RuntimeError('Expected exactly one prototype material slot')
    names={str(slots[0].get_editor_property(k)) for k in ('imported_material_slot_name','material_slot_name')}
    if g['fbxMaterialName'] not in names:raise RuntimeError('Prototype material slot name mismatch')
    return {'asset':mesh.get_path_name(),'triangles':int(mesh.get_num_triangles(0)),'boundsErrorCm':err}

def _inst_material(g):
    e=unreal.MaterialEditingLibrary
    m=unreal.AssetToolsHelpers.get_asset_tools().create_asset(g['fbxMaterialName']+'_ISM',INST_MAT,unreal.Material,unreal.MaterialFactoryNew())
    if m is None:raise RuntimeError('Material creation failed')
    p=g['material'];m.set_editor_property('two_sided',p['side']==2)
    if p['transparent'] or p['opacity']!=1 or p['alphaTest']!=0:raise ValueError('Frozen prototypes expected opaque source materials')
    def node(cls,x,y):return e.create_material_expression(m,cls,x,y)
    def wire(a,b,pin,output=''):
        if not e.connect_material_expressions(a,output,b,pin):raise RuntimeError('Material pin connection failed')
    tint=node(unreal.MaterialExpressionConstant3Vector,-800,0);tint.set_editor_property('constant',unreal.LinearColor(*p['color'],1))
    last=tint
    # Frozen source prototype geometry has no per-vertex colors. Only crowns vary
    # per instance. The shader receives linear values directly, with no gamma node.
    if g['sourceCategory']=='Tree crowns':
        channels=[]
        for i in range(3):
            c=node(unreal.MaterialExpressionPerInstanceCustomData,-1100,200+i*100);c.set_editor_property('data_index',i);c.set_editor_property('const_default_value',1.);channels.append(c)
        rg=node(unreal.MaterialExpressionAppendVector,-850,220);wire(channels[0],rg,'A');wire(channels[1],rg,'B')
        rgb=node(unreal.MaterialExpressionAppendVector,-650,250);wire(rg,rgb,'A');wire(channels[2],rgb,'B')
        interp=node(unreal.MaterialExpressionVertexInterpolator,-450,250);wire(rgb,interp,'')
        mul=node(unreal.MaterialExpressionMultiply,-200,0);wire(tint,mul,'A');wire(interp,mul,'B');last=mul
    if not e.connect_material_property(last,'',unreal.MaterialProperty.MP_BASE_COLOR):raise RuntimeError('Base color connection failed')
    for y,value,prop in [(450,p['metalness'],unreal.MaterialProperty.MP_METALLIC),(550,p['roughness'],unreal.MaterialProperty.MP_ROUGHNESS)]:
        c=node(unreal.MaterialExpressionConstant,-200,y);c.set_editor_property('r',value)
        if not e.connect_material_property(c,'',prop):raise RuntimeError('Scalar material connection failed')
    e.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);e.recompile_material(m)
    return m

def _inst_component(actor):
    # Editor subobject creation records an instance-owned component. Merely calling
    # unreal.InstancedStaticMeshComponent(outer=actor) is intentionally not used.
    sub=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem);lib=unreal.SubobjectDataBlueprintFunctionLibrary
    handles=sub.k2_gather_subobject_data_for_instance(actor)
    parent=next((h for h in handles if lib.get_associated_object(lib.get_data(h))==actor),None)
    if parent is None:raise RuntimeError('Editor actor subobject handle missing')
    params=unreal.AddNewSubobjectParams(parent_handle=parent,new_class=unreal.InstancedStaticMeshComponent,blueprint_context=None,conform_transform_to_parent=True)
    handle,reason=sub.add_new_subobject(params)
    if not lib.is_handle_valid(handle):raise RuntimeError('Persistent ISM creation failed: '+str(reason))
    data=lib.get_data(handle);c=lib.get_associated_object(data)
    if not isinstance(c,unreal.InstancedStaticMeshComponent) or c.get_owner()!=actor or not lib.is_instanced_component(data):raise RuntimeError('Editor component ownership/instance creation not verified')
    if c not in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):raise RuntimeError('Component absent from actor component readback')
    return c

def _inst_write(stage):stage['path'].write_text(json.dumps(stage['report'],indent=2)+'\n',encoding='utf-8')

def _inst_verify(data):
    actors,references=_inst_scene_references(data)
    if len(actors)!=5:raise RuntimeError('Expected exactly five owned decorative actors')
    if any(INST_TAG not in [str(v) for v in a.get_editor_property('tags')] for a in actors):raise RuntimeError('Untagged prototype actor detected')
    if len(references)!=5 or len({a.get_path_name() for a,c in references})!=5 or any(not isinstance(c,unreal.InstancedStaticMeshComponent) or c.get_owner()!=a for a,c in references):raise RuntimeError('Prototype references must be exactly five owned ISM components; standalone/duplicate prototypes are forbidden')
    bylabel={a.get_actor_label():a for a in actors};results=[]
    for g in data['groups']:
        label='JCTX_ISM_'+g['assetName'];a=bylabel.get(label)
        if a is None:raise RuntimeError('Missing/duplicate prototype actor label')
        cs=a.get_components_by_class(unreal.InstancedStaticMeshComponent)
        if len(cs)!=1:raise RuntimeError('Expected one ISM per prototype actor')
        c=cs[0];mesh=c.get_editor_property('static_mesh');mc=_inst_mesh_check(mesh,g)
        if not any(owner==a and component==c for owner,component in references):raise RuntimeError('ISM component differs from world prototype-reference scan')
        if c.get_instance_count()!=g['instanceCount']:raise RuntimeError('Native instance count mismatch')
        if c.get_collision_enabled()!=unreal.CollisionEnabled.NO_COLLISION or c.is_query_collision_enabled() or c.is_physics_collision_enabled():raise RuntimeError('Decoration collision must remain disabled')
        if c.get_editor_property('can_ever_affect_navigation') or c.get_editor_property('generate_overlap_events') or c.get_editor_property('is_editor_only'):raise RuntimeError('Navigation/overlap/editor-only flag differs from decorative runtime contract')
        if int(c.get_editor_property('num_custom_data_floats'))!=(3 if g['sourceCategory']=='Tree crowns' else 0):raise RuntimeError('Custom-data stride changed')
        if c.get_material(0) is None or c.get_material(0).get_path_name().split('.')[0]!=INST_MAT+'/'+g['fbxMaterialName']+'_ISM':raise RuntimeError('Unexpected material assignment')
        if c.get_editor_property('mobility')!=unreal.ComponentMobility.STATIC:raise RuntimeError('Decoration should remain static')
        pos=a.get_actor_location();rot=a.get_actor_rotation();scale=a.get_actor_scale3d()
        if not all(math.isfinite(v) for v in (pos.x,pos.y,pos.z,rot.pitch,rot.yaw,rot.roll,scale.x,scale.y,scale.z)):raise RuntimeError('Nonfinite native actor transform')
        if max(abs(v) for v in (pos.x,pos.y,pos.z,rot.pitch,rot.yaw,rot.roll))>1e-5 or max(abs(v-1) for v in (scale.x,scale.y,scale.z))>1e-5:raise RuntimeError('Actor moved; alignment may have been applied twice')
        maxerr=0.
        for i,r in enumerate(g['instances']):
            maxerr=max(maxerr,_inst_transform_error(c.get_instance_transform(i,world_space=True),r))
            if i and i%4096==0:unreal.log('Readback '+g['sourceCategory']+': '+str(i))
        expected=[v for r in g['instances'] for v in r['linearTint']] if g['sourceCategory']=='Tree crowns' else []
        actual=list(c.get_editor_property('per_instance_sm_custom_data'))
        if len(actual)!=len(expected):raise RuntimeError('Custom-data length mismatch')
        if not all(math.isfinite(v) for v in actual):raise RuntimeError('Nonfinite native instance tint')
        colorerr=max((abs(a-b) for a,b in zip(actual,expected)),default=0.)
        if colorerr>1e-6:raise RuntimeError('Linear per-instance tint mismatch')
        results.append(dict(mc,actor=a.get_path_name(),component=c.get_path_name(),instanceCount=c.get_instance_count(),maximumNativeProbeErrorCm=maxerr,customDataFloats=len(actual),maximumLinearTintError=colorerr,collision='NoCollision'))
    return results

def import_instances(data_dir,execute=False):
    global _INST_STAGE
    if _INST_STAGE is not None:raise RuntimeError('Prior stage exists; review/save it, never duplicate it')
    root,data=_inst_data(data_dir);world=_inst_world();assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    for cls,methods in [(unreal.SubobjectDataSubsystem,['add_new_subobject','k2_gather_subobject_data_for_instance']),(unreal.SubobjectDataBlueprintFunctionLibrary,['get_associated_object','is_instanced_component']),(unreal.InstancedStaticMeshComponent,['add_instances','set_num_custom_data_floats','set_custom_data_value','get_instance_transform'])]:
        if any(not hasattr(cls,k) for k in methods):raise RuntimeError('Required documented UE5.7 editor API unavailable; no actor-per-instance fallback')
    disk=Path(unreal.Paths.project_content_dir())/'MikdashV3/JerusalemContext/DecorativeInstancesV1'
    if assets.does_directory_exist(INST_DEST) or disk.exists():raise RuntimeError('Own destination namespace already exists; no overwrite/delete')
    actor_system=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    present,references=_inst_scene_references(data)
    if present or references:raise RuntimeError('Existing tagged, untagged or standalone prototype references; no duplicates')
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Save existing map edits before starting a new isolated stage')
    sample_error=max(_inst_transform_error(_inst_transform(g['instances'][i]),g['instances'][i]) for g in data['groups'] for i in (0,g['instanceCount']//2,g['instanceCount']-1))
    report=dict(status='READ_ONLY_PREFLIGHT_PASSED' if not execute else 'STARTING_EXPLICIT_STAGE',world=world.get_path_name(),manifestSha256=INST_MANIFEST_SHA,fbxSha256=INST_FBX_SHA,prototypes=5,instances=44793,plannedActors=5,componentClass='InstancedStaticMeshComponent',nativePreflightTransformSamples=15,maximumSampleProbeErrorCm=sample_error,destination=INST_DEST,nativeImportExecuted=False,persistenceAfterReopen='PENDING',nativeVisualAcceptance='PENDING',packagedRuntime='PENDING',sourceLimitations=data['limitations'])
    if not execute:unreal.log(str(report));return report
    directory=Path(unreal.Paths.project_dir())/'SourceAssets/context-review';directory.mkdir(parents=True,exist_ok=True)
    stage={'report':report,'path':directory/('instances-import-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:8]+'.json'),'world':world,'data':data,'assets':[],'actors':[]}
    _INST_STAGE=stage;_inst_write(stage)
    try:
        ui=unreal.FbxImportUI()
        for k,v in dict(automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,import_as_skeletal=False,import_mesh=True,import_animations=False,import_materials=False,import_textures=False,create_physics_asset=False).items():ui.set_editor_property(k,v)
        options=ui.get_editor_property('static_mesh_import_data')
        for k,v in dict(combine_meshes=False,transform_vertex_to_absolute=True,bake_pivot_in_vertex=False,convert_scene=True,convert_scene_unit=True,force_front_x_axis=False,import_uniform_scale=1.,auto_generate_collision=False,build_nanite=False,generate_lightmap_u_vs=False,remove_degenerates=True,normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():options.set_editor_property(k,v)
        task=unreal.AssetImportTask()
        for k,v in dict(filename=str(root/'instance-prototypes.fbx'),destination_path=INST_MESH,destination_name='None',automated=True,async_=False,replace_existing=False,save=False,options=ui,factory=unreal.FbxFactory()).items():task.set_editor_property(k,v)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);meshes=list(task.get_objects());stage['assets'].extend(meshes)
        if len(meshes)!=5 or any(not isinstance(m,unreal.StaticMesh) for m in meshes):raise RuntimeError('FBX must import exactly five static meshes')
        byname={m.get_name():m for m in meshes}
        if set(byname)!={g['assetName'] for g in data['groups']}:raise RuntimeError('Unexpected prototype names')
        for g in data['groups']:_inst_mesh_check(byname[g['assetName']],g)
        for g in data['groups']:
            mesh=byname[g['assetName']];mat=_inst_material(g);stage['assets'].append(mat);mesh.set_material(0,mat)
            a=actor_system.spawn_actor_from_class(unreal.Actor,unreal.Vector(0,0,0),unreal.Rotator(),transient=False)
            if a is None:raise RuntimeError('Editor actor creation failed')
            stage['actors'].append(a);a.set_actor_label('JCTX_ISM_'+g['assetName']);a.set_folder_path(INST_FOLDER);a.set_editor_property('tags',[unreal.Name(INST_TAG)])
            c=_inst_component(a);c.set_static_mesh(mesh);c.set_material(0,mat);c.set_mobility(unreal.ComponentMobility.STATIC);c.set_collision_profile_name('NoCollision');c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION);c.set_editor_property('can_ever_affect_navigation',False);c.set_editor_property('generate_overlap_events',False)
            crown=g['sourceCategory']=='Tree crowns';c.set_num_custom_data_floats(3 if crown else 0)
            transforms=[_inst_transform(r) for r in g['instances']]
            indices=list(c.add_instances(transforms,should_return_indices=True,world_space=True,update_navigation=False))
            if indices!=list(range(g['instanceCount'])):raise RuntimeError('Unexpected native instance index/order mapping')
            if crown:
                for i,r in enumerate(g['instances']):
                    for channel,value in enumerate(r['linearTint']):
                        if not c.set_custom_data_value(i,channel,float(value),mark_render_state_dirty=(i==len(indices)-1 and channel==2)):raise RuntimeError('Native custom-data setter failed')
            # Apply editor mobility after all instance/property edits, including the root.
            for scene in a.get_components_by_class(unreal.SceneComponent):
                scene.set_editor_property('mobility',unreal.ComponentMobility.STATIC)
            unreal.log('Staged '+g['sourceCategory']+': '+str(len(indices))+' instances')
        stage['report'].update(status='STAGED_UNSAVED_REQUIRES_EXPLICIT_SAVE',nativeImportExecuted=True,checks=_inst_verify(data));_inst_write(stage);return stage['report']
    except Exception as e:
        stage['report'].update(status='FAILED_PARTIAL_UNSAVED_REQUIRES_REVIEW',error=str(e),createdAssets=[a.get_path_name() for a in stage['assets']],createdActors=[a.get_path_name() for a in stage['actors']],automaticDeletion=False);_inst_write(stage);raise

def save_instances_import():
    stage=_INST_STAGE
    if stage is None or stage['report']['status']!='STAGED_UNSAVED_REQUIRES_EXPLICIT_SAVE':raise RuntimeError('No complete verified unsaved instance stage')
    if _inst_world()!=stage['world']:raise RuntimeError('World changed; refusing save')
    stage['report']['checks']=_inst_verify(stage['data']);assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    try:
        for a in stage['assets']:
            if not assets.save_loaded_asset(a,only_if_is_dirty=False):raise RuntimeError('Asset save failed: '+a.get_path_name())
        if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level():raise RuntimeError('Map save failed')
        stage['report'].update(status='SAVED_PENDING_MANUAL_REOPEN_AND_VISUAL_REVIEW',savedAssets=len(stage['assets']),savedActors=len(stage['actors']))
    except Exception as e:stage['report'].update(status='SAVE_FAILED_PARTIAL_DISK_STATE',error=str(e));raise
    finally:_inst_write(stage)
    return stage['report']

def verify_instances_in_current_map(data_dir):
    """Read-only. Run after manual save/reopen; never reloads the map itself."""
    _,data=_inst_data(data_dir);w=_inst_world();checks=_inst_verify(data)
    result=dict(status='CURRENT_MAP_READBACK_PASSED',world=w.get_path_name(),checks=checks,instances=sum(r['instanceCount'] for r in checks),manualReopenNotAutomaticallyAttested=True,nativeVisualAcceptance='PENDING',packagedRuntime='PENDING')
    unreal.log(str(result));return result
