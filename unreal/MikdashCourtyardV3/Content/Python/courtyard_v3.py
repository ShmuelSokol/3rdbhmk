"""Measured architecture import and native renderer checkpoint for Unreal 5.7.
Editor authoring only. Runtime controls are supplied by cooked template Blueprints.
"""
from pathlib import Path
import json, math, re, time
import unreal
import v3_materials as shading

PROJECT=Path(__file__).resolve().parents[2]
ASSETS=PROJECT/'SourceAssets'
DEST='/Game/MikdashV3'
LEVEL=DEST+'/Maps/Courtyard'
REPORT=ASSETS/'unreal-v3-validation.json'

def write(report):
    REPORT.write_text(json.dumps(report,indent=2)+'\n')

def imported_meshes(file,destination,combine=False):
    ui=unreal.FbxImportUI()
    for key,value in dict(automated_import_should_detect_type=False,mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,import_as_skeletal=False,import_mesh=True,import_animations=False,import_materials=False,import_textures=False,create_physics_asset=False).items():ui.set_editor_property(key,value)
    data=ui.get_editor_property('static_mesh_import_data')
    for key,value in dict(combine_meshes=combine,transform_vertex_to_absolute=True,bake_pivot_in_vertex=False,convert_scene=True,convert_scene_unit=True,force_front_x_axis=False,import_uniform_scale=1.0,auto_generate_collision=False,build_nanite=False,generate_lightmap_u_vs=False,remove_degenerates=True,normal_import_method=unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():data.set_editor_property(key,value)
    task=unreal.AssetImportTask()
    for key,value in dict(filename=str(ASSETS/file),destination_path=DEST+'/'+destination,automated=True,async_=False,replace_existing=False,save=False,options=ui,factory=unreal.FbxFactory()).items():task.set_editor_property(key,value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    meshes=[o for o in task.get_objects() if isinstance(o,unreal.StaticMesh)]
    if not meshes:raise RuntimeError('No static meshes imported: '+file)
    return meshes

def bounds(mesh):
    box=mesh.get_bounding_box()
    return {'min':[box.min.x,box.min.y,box.min.z],'max':[box.max.x,box.max.y,box.max.z]}

def point(p):return unreal.Vector(p[0]*50,p[2]*50,p[1]*50)

def camera(actors,label,eye,look,fov=60):
    actor=actors.spawn_actor_from_class(unreal.CameraActor,point(eye),unreal.MathLibrary.find_look_at_rotation(point(eye),point(look)))
    actor.set_actor_label(label);comp=actor.get_component_by_class(unreal.CameraComponent)
    comp.set_field_of_view(fov);comp.set_editor_property('post_process_settings',shading.physical_exposure());comp.set_editor_property('post_process_blend_weight',1.0)
    return actor

def run():
    r={'status':'started','version':'v3','engine':unreal.SystemLibrary.get_engine_version(),'visualAcceptance':'UNTESTED','startedUtc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    try:
        manifest=json.loads((ASSETS/'architecture-manifest.json').read_text())
        r['expectedMeshes']=manifest['meshCount'];write(r)
        assets=unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
        if assets.does_asset_exist(LEVEL):raise RuntimeError('Existing V3 map is preserved. Inspect previous result before rerunning.')
        calibration=imported_meshes('calibration.fbx','Calibration',True)[0]
        b=bounds(calibration);dimensions=[b['max'][i]-b['min'][i] for i in range(3)]
        if any(abs(v-100)>.1 for v in dimensions):raise RuntimeError('Calibration failed: '+str(dimensions))
        probe=imported_meshes('axis-probe.fbx','Calibration',True)[0];b=bounds(probe);center=[(b['min'][i]+b['max'][i])/2 for i in range(3)]
        if any(abs(a-b)>.1 for a,b in zip(center,[50,150,100])):raise RuntimeError('Axis conversion failed: '+str(center))
        r.update(calibrationCm=dimensions,axisProbeCenterCm=center,status='importing_architecture');write(r)
        meshes=imported_meshes('architecture.fbx','Architecture')
        if len(meshes)!=manifest['meshCount']:raise RuntimeError('Architecture count mismatch: '+str(len(meshes)))
        records={item['assetName']:item for item in manifest['meshes']}
        mats=json.loads((ASSETS/'material-manifest.json').read_text());native={}
        for record in mats:
            p=record['material'];metal=p.get('metalness',0);water=p.get('transmission',0)>.1
            profile={'kind':'Water' if water else 'Metal' if metal>.5 else 'Stone','color':p['color'],'metalness':metal,'roughness':p.get('roughness',.85),'specular':.5 if metal>.5 else .3}
            if water:profile.update(opacity=.16,ior=1.333,roughness=.07)
            native[shading.normalize(record['fbxMaterialName'])]=shading.create_native_material(profile)
        levels=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if not levels.new_level(LEVEL,False):raise RuntimeError('Map creation failed')
        actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        r.update(status='placing_and_saving',importedMeshes=len(meshes),materialCount=len(native),meshChecks=[]);write(r)
        for i,mesh in enumerate(meshes):
            name=mesh.get_name();record=records.get(name) or next((v for k,v in records.items() if name.endswith(k)),None)
            if record is None:raise RuntimeError('Unmatched mesh name: '+name)
            actual=bounds(mesh);expected=record['expectedBoundsUnrealCm']
            error=max(abs(actual[k][a]-expected[k][a]) for k in ['min','max'] for a in range(3))
            if error>.5:raise RuntimeError('Bounds mismatch '+name+': '+str(error)+' cm')
            for n,slot in enumerate(mesh.get_editor_property('static_materials')):
                names=[str(slot.get_editor_property(k)) for k in ['imported_material_slot_name','material_slot_name']]
                mat=next((native[shading.normalize(v)] for v in names if shading.normalize(v) in native),None)
                if mat is None:raise RuntimeError('Unmatched material on '+name+': '+str(names))
                mesh.set_material(n,mat)
            setup=mesh.get_editor_property('body_setup')
            if setup is None:setup=unreal.BodySetup(outer=mesh);mesh.set_editor_property('body_setup',setup)
            setup.set_editor_property('collision_trace_flag',unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
            actor=actors.spawn_actor_from_object(mesh,unreal.Vector(0,0,0),unreal.Rotator(0,0,0))
            actor.set_actor_label(record['sourceName']);actor.set_folder_path('Measured architecture/'+record.get('semantic','Architecture'))
            component=actor.get_component_by_class(unreal.StaticMeshComponent);component.set_collision_profile_name('NoCollision' if record.get('semantic') in ['water','detail'] else 'BlockAll')
            assets.save_loaded_asset(mesh)
            r['meshChecks'].append({'asset':mesh.get_path_name(),'source':record['sourceName'],'boundsErrorCm':error})
            if i%100==0:r['placedMeshes']=i+1;write(r);unreal.log('V3 architecture '+str(i+1)+' / '+str(len(meshes)))
        r['lighting']=shading.setup_lighting(actors)
        views=[('01 Courtyard arrival',[42,15.7,0],[-50,37,0],70),('02 Altar and southern ramp',[26,16,42],[-14,25,8],65),('03 Ulam facade',[-28,16,25],[-52,35,0],65),('04 Entire Temple',[310,230,290],[-25,25,0],65)]
        cams=[camera(actors,*v) for v in views]
        world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        world.set_level_viewport_camera_info(cams[0].get_actor_location(),cams[0].get_actor_rotation());levels.pilot_level_actor(cams[0]);levels.editor_set_viewport_realtime(True);levels.editor_set_game_view(True)
        gameplay_config=ASSETS/'gameplay-config.json'
        if gameplay_config.exists():
            import gameplay
            cfg=json.loads(gameplay_config.read_text(encoding='utf-8-sig'));r['gameplay']=gameplay.prepare_gameplay(cfg['character'],cfg['gameMode'],[2100,0,590],180)
        else:r['gameplay']={'status':'TEMPLATE_NOT_ATTACHED','next':'Attach working first-person template Blueprint dependencies'}
        keys=['r.DynamicGlobalIlluminationMethod','r.ReflectionMethod','r.GenerateMeshDistanceFields','r.ForwardShading']
        r['rendererReadback']={k:unreal.SystemLibrary.get_console_variable_int_value(k) for k in keys}
        if not levels.save_current_level():raise RuntimeError('Could not save map')
        assets.save_directory(DEST,only_if_is_dirty=True,recursive=True)
        config=PROJECT/'Config'/'DefaultEngine.ini'
        text=config.read_text()
        if 'EditorStartupMap=' not in text:config.write_text(text.replace('GameDefaultMap='+LEVEL,'GameDefaultMap='+LEVEL+'\nEditorStartupMap='+LEVEL))
        r.update(status='saved_requires_runtime_and_visual_review',level=LEVEL,placedMeshes=len(meshes),limitations=['No public streaming service','No complete ceremony/crowd simulation','Source and material interpretations remain','Lumen cache and playable build require live review'])
    except Exception as e:r.update(status='failed',error=str(e));raise
    finally:write(r)
