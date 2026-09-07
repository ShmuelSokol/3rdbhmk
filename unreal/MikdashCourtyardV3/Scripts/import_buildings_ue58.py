"""AUTHORED_NOT_NATIVE_TESTED â€” inert UE5.7 buildings import, no startup hookup.
exec(open(PATH).read()); import_buildings(DATA_DIR) # read-only preflight
import_buildings(DATA_DIR, execute=True)           # stages unsaved assets/actors
save_buildings_import()                           # separate explicit save
"""
from pathlib import Path
import hashlib,json,math,time,uuid
import unreal
BUILDINGS_DEST='/Game/MikdashV3/JerusalemContext'
BUILDINGS_MESH_DEST=BUILDINGS_DEST+'/Buildings'
BUILDINGS_MATERIAL_PATH=BUILDINGS_DEST+'/Materials/M_JerusalemBuildings_VertexColor'
BUILDINGS_LEVEL='/Game/MikdashV3/Maps/Courtyard'
BUILDINGS_FOLDER='Jerusalem context/Buildings'
BUILDINGS_TAG='MikdashJerusalemBuildingsV1'
if '_BUILDINGS_STAGE' not in globals():_BUILDINGS_STAGE=None

def _buildings_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def _buildings_bounds(mesh):
    b=mesh.get_bounding_box()
    return {'min':[float(b.min.x),float(b.min.y),float(b.min.z)],'max':[float(b.max.x),float(b.max.y),float(b.max.z)]}

def _buildings_error(actual,expected):
    return max(abs(actual[k][axis]-expected[k][axis])for k in ('min','max')for axis in range(3))

def _buildings_manifest(data_dir):
    root=Path(data_dir)
    if not root.is_absolute() or str(root).lower().startswith('v:'):raise RuntimeError('Use an absolute local C: data folder, not virtual V: storage')
    path=root/'buildings-manifest.json';fbx=root/'buildings.fbx'
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    expected_name_sha='853915403513b335c6eea39a14e48b671f332ec8a0923089cfb5e80c0b75bd93'
    records=data['meshes'];names=[r['assetName']for r in records]
    if data['meshCount']!=1499 or len(names)!=1499 or len(set(names))!=1499 or hashlib.sha256('\n'.join(sorted(names)).encode()).hexdigest()!=expected_name_sha:raise ValueError('Manifest must contain exactly the 1499 reviewed building mesh names')
    if data['fbxSha256']!='271bc9b4e1297421a33dde0b00172ad6111decabdb683e05267d4b972aca5408':raise ValueError('Not the reviewed buildings FBX revision')
    if data['alignment']['degrees']!=0 or data['alignment']['translationSourceAmos']!=[17.509700315687695,0,-0.5513496449385334] or not data['alignment']['bakedOnce']:raise ValueError('Unexpected world-baked alignment')
    if data['triangles']!=242764 or sum(r['triangles']for r in records)!=242764:raise ValueError('Buildings triangle totals disagree')
    for r in records:
        if not isinstance(r['triangles'],int) or r['triangles']<=0 or r['vertices']!=3*r['triangles']:raise ValueError('Invalid source triangle-soup count')
        if r['semantic']!='buildings' or r['colorAttribute']['colorSpace']!='linear RGB':raise ValueError('Unexpected building semantic/color space')
        if r.get('objectTransformIdentity') is not True or r['spawnLocationUnrealCm']!=[0,0,0] or r['spawnRotationDegrees']!=[0,0,0] or r['spawnScale']!=[1,1,1]:raise ValueError('Buildings coordinates must already be baked; no importer alignment transform')
        for key in ('min','max'):
            v=r['expectedBoundsUnrealCm'][key]
            if len(v)!=3 or not all(math.isfinite(x)for x in v):raise ValueError('Invalid expected bounds')
        if any(r['expectedBoundsUnrealCm']['min'][i]>=r['expectedBoundsUnrealCm']['max'][i]for i in (0,1)):raise ValueError('Invalid building XY extent')
        slots=r['materialSlots']
        if len(slots)!=1 or slots[0]['slot']!=0 or slots[0]['fbxMaterialName']!='M_JerusalemBuildings_VertexColor':raise ValueError('Unexpected buildings material slots')
    aggregate={key:[fn(r['expectedBoundsUnrealCm'][key][i]for r in records)for i in range(3)]for key,fn in [('min',min),('max',max)]}
    if _buildings_error(aggregate,data['expectedBoundsUnrealCm'])>.5:raise ValueError('Manifest aggregate bounds mismatch')
    material=data['material']
    if material['fbxMaterialName']!='M_JerusalemBuildings_VertexColor' or material['colorSpace']!='linear RGB':raise ValueError('Unexpected material/color space')
    if material['color']!=[1,1,1] or material['metalness']!=0 or material['roughness']!=.88:raise ValueError('These reviewed buildings use white source tint, nonmetal, roughness0.88')
    if _buildings_sha(fbx)!=data['fbxSha256']:raise ValueError('buildings.fbx SHA256 mismatch')
    return root,data,_buildings_sha(path)

def _buildings_world():
    editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world=editor.get_editor_world()
    if editor.get_game_world() is not None:raise RuntimeError('Stop PIE before editor import')
    if world is None or world.get_path_name().split('.')[0]!=BUILDINGS_LEVEL:raise RuntimeError('Open the existing saved Courtyard map; importer does not switch/create maps')
    return world

def _buildings_report_write(stage):
    stage['reportPath'].write_text(json.dumps(stage['report'],indent=2)+'\n',encoding='utf-8')

def _buildings_check_mesh(mesh,r,mesh_editor):
    if mesh.get_name()!=r['assetName'] or mesh.get_path_name().split('.')[0]!=BUILDINGS_MESH_DEST+'/'+r['assetName']:raise RuntimeError('Unexpected imported mesh name/path: '+mesh.get_path_name())
    error=_buildings_error(_buildings_bounds(mesh),r['expectedBoundsUnrealCm'])
    if error>.5:raise RuntimeError('Bounds differ by '+str(error)+'cm: '+mesh.get_name())
    triangles=int(mesh.get_num_triangles(0))
    if triangles!=r['triangles']:raise RuntimeError('Imported triangle count mismatch: '+mesh.get_name())
    if not mesh_editor.has_vertex_colors(mesh):raise RuntimeError('Imported vertex colors missing: '+mesh.get_name())
    slots=mesh.get_editor_property('static_materials')
    if len(slots)!=1:raise RuntimeError('Expected single material slot: '+mesh.get_name())
    names={str(slots[0].get_editor_property(k))for k in ('imported_material_slot_name','material_slot_name')}
    if r['materialSlots'][0]['fbxMaterialName'] not in names:raise RuntimeError('Unexpected material slot name: '+mesh.get_name())
    return dict(asset=mesh.get_path_name(),triangles=triangles,renderVertices=int(mesh.get_num_vertices(0)),boundsErrorCm=error,vertexColorsPresent=True)

def _buildings_material(profile):
    mat=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_JerusalemBuildings_VertexColor',BUILDINGS_DEST+'/Materials',unreal.Material,unreal.MaterialFactoryNew())
    if mat is None:raise RuntimeError('Buildings material creation failed')
    edit=unreal.MaterialEditingLibrary
    vertex=edit.create_material_expression(mat,unreal.MaterialExpressionVertexColor,-600,0)
    tint=edit.create_material_expression(mat,unreal.MaterialExpressionConstant3Vector,-600,160)
    tint.set_editor_property('constant',unreal.LinearColor(*profile['color'],1.0))
    multiply=edit.create_material_expression(mat,unreal.MaterialExpressionMultiply,-280,0)
    if not edit.connect_material_expressions(vertex,'',multiply,'A') or not edit.connect_material_expressions(tint,'',multiply,'B') or not edit.connect_material_property(multiply,'',unreal.MaterialProperty.MP_BASE_COLOR):raise RuntimeError('Buildings vertex-color material connections failed')
    for index,(value,prop)in enumerate([(profile['metalness'],unreal.MaterialProperty.MP_METALLIC),(profile['roughness'],unreal.MaterialProperty.MP_ROUGHNESS)]):
        node=edit.create_material_expression(mat,unreal.MaterialExpressionConstant,-280,240+index*100);node.set_editor_property('r',float(value))
        if not edit.connect_material_property(node,'',prop):raise RuntimeError('Buildings scalar connection failed')
    # No power/gamma node: exported RGB is linear; source tint is white.
    edit.recompile_material(mat)
    return mat

def import_buildings(data_dir,execute=False):
    global _BUILDINGS_STAGE
    if _BUILDINGS_STAGE is not None:raise RuntimeError('Previous buildings stage exists; save/review it rather than importing again')
    root,data,manifest_sha=_buildings_manifest(data_dir);world=_buildings_world()
    assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mesh_editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    # Only our Buildings namespace, exact material, and own actor identities are guarded.
    # Existing Terrain assets/actors are valid and must not be touched.
    existing=list(assets.list_assets(BUILDINGS_MESH_DEST,recursive=True,include_folder=False)) if assets.does_directory_exist(BUILDINGS_MESH_DEST) else []
    disk_dest=Path(unreal.Paths.project_content_dir())/'MikdashV3/JerusalemContext/Buildings'
    material_disk=Path(unreal.Paths.project_content_dir())/'MikdashV3/JerusalemContext/Materials/M_JerusalemBuildings_VertexColor.uasset'
    if existing or (disk_dest.exists() and any(disk_dest.rglob('*.uasset'))) or assets.does_asset_exist(BUILDINGS_MATERIAL_PATH) or material_disk.exists():raise RuntimeError('Buildings destination/material is occupied; no overwrite/deletion permitted')
    before=actors.get_all_level_actors()
    for actor in before:
        components=actor.get_components_by_class(unreal.StaticMeshComponent)
        own_mesh=any(c.get_editor_property('static_mesh') and c.get_editor_property('static_mesh').get_path_name().startswith(BUILDINGS_MESH_DEST+'/') for c in components)
        folder=str(actor.get_folder_path())
        if folder==BUILDINGS_FOLDER or folder.startswith(BUILDINGS_FOLDER+'/') or BUILDINGS_TAG in [str(x)for x in actor.get_editor_property('tags')] or actor.get_actor_label().startswith('SM_JerusalemBuildings_') or own_mesh:raise RuntimeError('Existing building-context actor detected; no duplicate import')
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Save existing map edits first; stage should begin from a clean checkpoint')
    preflight=dict(status='authored_not_native_tested',action='read_only_preflight' if not execute else 'starting_explicit_import',meshCount=1499,triangles=242764,manifestSha256=manifest_sha,fbxSha256=data['fbxSha256'],destination=BUILDINGS_MESH_DEST,world=world.get_path_name(),expectedBoundsUnrealCm=data['expectedBoundsUnrealCm'],vertexColor='linear RGB multiplied by linear white source tint',sourceLimitations=data['limitations'],runtimeCollision='pending',nativeVisualAcceptance='pending',vertexColorNumericalVerification='UNVERIFIED: presence checked; no numeric UE color-buffer readback',nativeNormalVerification='UNVERIFIED: import-normals option set; inspect actual lighting/seams')
    if not execute:unreal.log(str(preflight));return preflight
    report_dir=Path(unreal.Paths.project_dir())/'SourceAssets/context-review';report_dir.mkdir(parents=True,exist_ok=True)
    stage=dict(report=preflight,reportPath=report_dir/('buildings-import-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:6]+'.json'),world=world,manifest=data,meshChecks=[],meshes=[],actors=[],material=None)
    _BUILDINGS_STAGE=stage;_buildings_report_write(stage)
    try:
        ui=unreal.FbxImportUI()
        for key,value in dict(automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,import_as_skeletal=False,import_mesh=True,import_animations=False,import_materials=False,import_textures=False,create_physics_asset=False).items():ui.set_editor_property(key,value)
        options=ui.get_editor_property('static_mesh_import_data')
        for key,value in dict(combine_meshes=False,transform_vertex_to_absolute=True,bake_pivot_in_vertex=False,convert_scene=True,convert_scene_unit=True,force_front_x_axis=False,import_uniform_scale=1.0,auto_generate_collision=False,build_nanite=False,generate_lightmap_u_vs=False,remove_degenerates=True,normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,vertex_color_import_option=unreal.VertexColorImportOption.REPLACE).items():options.set_editor_property(key,value)
        task=unreal.AssetImportTask()
        for key,value in dict(filename=str(root/'buildings.fbx'),destination_path=BUILDINGS_MESH_DEST,destination_name='None',automated=True,async_=False,replace_existing=False,save=False,options=ui,factory=unreal.FbxFactory()).items():task.set_editor_property(key,value)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        imported=list(task.get_objects());stage['meshes']=[x for x in imported if isinstance(x,unreal.StaticMesh)]
        if len(imported)!=1499 or len(stage['meshes'])!=1499:raise RuntimeError('Unexpected imported asset/mesh count')
        records={r['assetName']:r for r in data['meshes']}
        if {m.get_name()for m in stage['meshes']}!=set(records):raise RuntimeError('Exact imported mesh names differ; no fuzzy name matching')
        # ALL name/bounds/count/color checks finish before any actor is spawned or asset saved.
        for mesh in stage['meshes']:stage['meshChecks'].append(_buildings_check_mesh(mesh,records[mesh.get_name()],mesh_editor))
        mat=_buildings_material(data['material']);stage['material']=mat
        for mesh in stage['meshes']:
            mesh.set_material(0,mat)
            setup=mesh.get_editor_property('body_setup')
            if setup is None:setup=unreal.BodySetup(outer=mesh);mesh.set_editor_property('body_setup',setup)
            setup.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            mesh.set_editor_property('lod_for_collision',0)
            actor=actors.spawn_actor_from_object(mesh,unreal.Vector(0,0,0),unreal.Rotator(roll=0,pitch=0,yaw=0),transient=False)
            if actor is None:raise RuntimeError('Buildings actor spawn failed')
            stage['actors'].append(actor);actor.set_actor_label(mesh.get_name());actor.set_folder_path(BUILDINGS_FOLDER);actor.set_editor_property('tags',[unreal.Name(BUILDINGS_TAG)])
            component=actor.get_component_by_class(unreal.StaticMeshComponent)
            component.set_mobility(unreal.ComponentMobility.STATIC);component.set_collision_profile_name('BlockAll')
        stage['report'].update(status='staged_unsaved_requires_explicit_save',meshChecks=stage['meshChecks'],actorCount=len(stage['actors']),collisionPolicy='Static mapped buildings: complex-as-simple LOD0; BlockAll; actual traces/cook still pending')
        _buildings_report_write(stage);unreal.log('Buildings staged UNSAVED. Review, then explicitly call save_buildings_import().');return stage['report']
    except Exception as exc:
        stage['report'].update(status='FAILED_PARTIAL_UNSAVED_STATE_REQUIRES_REVIEW',error=str(exc),meshChecks=stage['meshChecks'],createdAssets=[m.get_path_name()for m in stage['meshes']],createdActors=[a.get_path_name()for a in stage['actors']],noAutomaticDeletion=True)
        _buildings_report_write(stage);raise

def save_buildings_import():
    stage=_BUILDINGS_STAGE
    if stage is None or stage['report']['status']!='staged_unsaved_requires_explicit_save':raise RuntimeError('No fully verified unsaved buildings stage')
    if _buildings_world()!=stage['world']:raise RuntimeError('Map/world changed; refusing save')
    assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    mesh_editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    records={r['assetName']:r for r in stage['manifest']['meshes']}
    if len(stage['actors'])!=1499:raise RuntimeError('Actor count changed')
    for mesh in stage['meshes']:_buildings_check_mesh(mesh,records[mesh.get_name()],mesh_editor)
    actor_mesh_names=[]
    for actor in stage['actors']:
        component=actor.get_component_by_class(unreal.StaticMeshComponent)
        mesh=component.get_editor_property('static_mesh') if component else None
        if mesh is None or mesh not in stage['meshes'] or component.get_collision_profile_name()!=unreal.Name('BlockAll'):raise RuntimeError('Buildings actor mesh/collision changed')
        actor_mesh_names.append(mesh.get_name())
        if BUILDINGS_TAG not in [str(x)for x in actor.get_editor_property('tags')] or not component.is_query_collision_enabled():raise RuntimeError('Building actor ownership/query collision changed')
        if mesh.get_material(0)!=stage['material'] or mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')!=unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:raise RuntimeError('Buildings material/collision setup changed')
        pos=actor.get_actor_location();rot=actor.get_actor_rotation();scale=actor.get_actor_scale3d()
        if max(abs(v)for v in [pos.x,pos.y,pos.z,rot.pitch,rot.yaw,rot.roll])>1e-5 or max(abs(v-1)for v in [scale.x,scale.y,scale.z])>1e-5:raise RuntimeError('Buildings actor transform changed; alignment must be applied exactly once')
    if len(set(actor_mesh_names))!=1499 or set(actor_mesh_names)!=set(records):raise RuntimeError('Buildings actor coverage changed')
    try:
        for asset in [stage['material'],*stage['meshes']]:
            if not assets.save_loaded_asset(asset,only_if_is_dirty=False):raise RuntimeError('Asset save failed: '+asset.get_path_name())
        if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level():raise RuntimeError('Courtyard map save failed')
        stage['report'].update(status='saved_requires_native_visual_collision_and_cook_review',savedAssets=1500,savedActors=1499)
    except Exception as exc:stage['report'].update(status='SAVE_FAILED_PARTIAL_DISK_STATE_REQUIRES_REVIEW',error=str(exc));raise
    finally:_buildings_report_write(stage)
    return stage['report']
