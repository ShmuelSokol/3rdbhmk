"""Coordinator-owned commandlet only. Compile first; controlled pose render second.
No map saves, asset saves, project code, production mounts, or temporal acceptance.
"""
import hashlib,json,math,os,re,sys,traceback
from pathlib import Path
import unreal as ue
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
import candidate_builder as builder
import png_safe
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def require(ok,message):
    if not ok:raise RuntimeError(message)

def atomic(path,data):
    tmp=path.with_suffix('.tmp')
    with tmp.open('x',encoding='utf-8') as f:
        json.dump(data,f,indent=2);f.flush();os.fsync(f.fileno())
    require(not path.exists(),'Never replace native evidence')
    tmp.rename(path)

def connections(material,node):
    ml=ue.MaterialEditingLibrary
    names=list(map(str,ml.get_material_expression_input_names(node)))
    values=list(ml.get_inputs_for_material_expression(material,node))
    require(len(names)==len(values),'Input reflection lengths differ')
    return dict(zip(names,values))

def deps(material,node):
    seen=set();indices=set()
    def visit(n):
        if n is None or n.get_path_name() in seen:return
        seen.add(n.get_path_name())
        if n.get_class().get_name()=='MaterialExpressionPerInstanceCustomData':indices.add(int(n.get_editor_property('data_index')))
        for v in connections(material,n).values():visit(v)
    visit(node);return sorted(indices)

def compile_graph(material,report,label):
    ml=ue.MaterialEditingLibrary
    errors=list(map(str,ml.recompile_material(material)))
    row={'label':label,'path':material.get_path_name(),'compilerErrors':errors}
    report.setdefault('compilers',[]).append(row)
    require(not errors,'Compiler diagnostics: '+repr(errors))
    # RecompileMaterial can return [] when Resource is NULL. Require positive
    # representative compiled-shader evidence, not merely absence of errors.
    require(callable(getattr(ml,'get_statistics',None)),'GetStatistics unavailable')
    row['statisticsStage']='waiting_for_resource_compilation_under_owned_job_deadline'
    stats=ml.get_statistics(material)
    fields=('num_vertex_shader_instructions','num_pixel_shader_instructions',
            'num_vertex_texture_samples','num_pixel_texture_samples','num_samplers',
            'num_uv_scalars','num_interpolator_scalars','num_virtual_texture_samples')
    row['statistics']={field:int(stats.get_editor_property(field)) for field in fields}
    row['statisticsStage']='returned'
    for field in fields[:5]:
        require(row['statistics'][field]>0,'No positive compiled VAT/surface shader evidence: '+field)
    # Statistics may submit previously missing jobs. Read diagnostics again after
    # it completes; this cached recompile remains within the same total deadline.
    row['compilerErrorsAfterStatistics']=list(map(str,ml.recompile_material(material)))
    require(not row['compilerErrorsAfterStatistics'],'Compiler diagnostics after statistics: '+repr(row['compilerErrorsAfterStatistics']))
    row['positiveResourceShaderEvidence']=True
    row['evidenceScope']='Representative vertex/pixel shaders for requested material resource, not every HISM permutation or rendered acceptance'
    return row

def graph_proof(material,report):
    ml=ue.MaterialEditingLibrary
    expressions=list(ml.get_material_expressions(material));census={};indices=set()
    for n in expressions:
        cls=n.get_class().get_name();census[cls]=census.get(cls,0)+1
        if cls=='MaterialExpressionPerInstanceCustomData':indices.add(int(n.get_editor_property('data_index')))
    require(indices==set(range(30)) and not census.get('MaterialExpressionCustom'),'30-channel stock graph mismatch')
    wpo=ml.get_material_property_input_node(material,ue.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    require(wpo.get_class().get_name()=='MaterialExpressionPreviousFrameSwitch','PreviousFrameSwitch missing')
    switch=connections(material,wpo);current=switch['Current Frame'];previous=switch['Previous Frame']
    select=connections(material,previous)
    require(select['A > B']==current and select['A == B']==current,'History equality/current selector changed')
    require(int(select['B'].get_editor_property('data_index'))==25,'History update boundary changed')
    current_deps=deps(material,current);old_deps=deps(material,select['A < B'])
    normal=deps(material,ml.get_material_property_input_node(material,ue.MaterialProperty.MP_NORMAL))
    require(set(current_deps)=={0,2,3,4,5,6,7,8,9,10,26,27},'Current WPO dependencies differ')
    require(set(old_deps)=={9,*range(11,25),28,29},'Old WPO dependencies differ')
    require({26,27}.issubset(normal) and not {28,29}.intersection(normal),'Normal angular path differs')
    require(not material.get_editor_property('tangent_space_normal'),'World normal flag differs')
    report['graph']={'census':census,'currentWpo':current_deps,'oldWpo':old_deps,'normal':normal,'historyBoundary':25}

def controlled_clock(material):
    # This changes ONLY the newly generated in-memory candidate graph.
    # PreviousFrameSwitch receives explicit scalar previous time in its own pass.
    ml=ue.MaterialEditingLibrary;g=builder.StockGraph(ue,material,{})
    times=[n for n in ml.get_material_expressions(material) if n.get_class().get_name()=='MaterialExpressionTime']
    require(len(times)==1,'Expected one shared stock Time node')
    old=times[0];targets=[]
    for n in ml.get_material_expressions(material):
        for pin,child in connections(material,n).items():
            if child==old:targets.append((n,pin))
    now=g.scalar('ReviewTime',0,0,0);prev=g.scalar('ReviewPreviousTime',0,0,0)
    switch=g.make(ue.MaterialExpressionPreviousFrameSwitch)
    g.link(now,switch,['Current Frame']);g.link(prev,switch,['Previous Frame'])
    for n,pin in targets:g.link(switch,n,[pin])
    return {'mode':'controlled_scalar_current_and_previous','rewiredEdges':len(targets),
            'NOT_proven':['actual GameTime progression','actual PrevFrameGameTime','temporal velocity','frame continuity']}

def main():
    cmd=ue.SystemLibrary.get_command_line()
    require('-nullrhi' not in cmd.lower(),'Real RHI required for positive shader statistics')
    run=re.search(r'-AngularRun=([a-z0-9-]{1,32})',cmd).group(1)
    mode=re.search(r'-AngularMode=(Compile|Render)',cmd).group(1)
    require(mode=='Compile','Frozen revision authorizes Compile only; pose harness requires a new revision')
    out=BASE/'runs'/run/mode.lower();require(out.is_dir(),'Owned wrapper output required')
    report={'status':'starting','mode':mode,'harnessHashesSha256':sha(BASE/'harness-hashes.json'),'captures':[],
            'scope':'isolated Entry shader proof; controlled poses are not temporal or production acceptance'}
    actors=None;spawned=[]
    try:
        require(Path(ue.Paths.project_dir()).resolve()==(BASE/'P').resolve(),'Wrong project mount')
        inputs=json.loads((BASE/'inputs.json').read_text())
        for relative,value in json.loads((BASE/'harness-hashes.json').read_text()).items():require(sha(BASE/relative)==value,'Harness revision mismatch: '+relative)
        # Exactly two audited readonly UFUNCTIONs, both forwarding to global
        # GEditor world contexts; no initialized subsystem members or mutations.
        editor=ue.get_default_object(ue.UnrealEditorSubsystem)
        initial=editor.get_editor_world()
        report['initialWorld']=None if initial is None else initial.get_path_name()
        require(initial is None or not initial.get_outermost().get_name().startswith('/Game/'),'Project world at startup')
        require(editor.get_game_world() is None,'Game/PIE world at startup')
        loaded=ue.EditorLoadingAndSavingUtils.load_map('/Engine/Maps/Entry')
        world=editor.get_editor_world()
        require(world is not None and loaded==world and world.get_outermost().get_name()=='/Engine/Maps/Entry','Explicit Engine Entry load failed')
        require(editor.get_game_world() is None,'PIE/game world after Entry load')
        report['worldGuard']={'initial':report['initialWorld'],'loadReturn':loaded.get_path_name(),'editorWorld':world.get_path_name(),'noPIE':True,
            'readonlyCDOQueries':['UnrealEditorSubsystem.GetEditorWorld','UnrealEditorSubsystem.GetGameWorld'],'mutatingCDOCalls':0}
        # Read package metadata from the tiny copied project, BEFORE mesh/material loads.
        registry=ue.AssetRegistryHelpers.get_asset_registry();registry.search_all_assets(True)
        options=ue.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True,
            include_searchable_names=False,include_soft_management_references=False,include_hard_management_references=False)
        closure={}
        for package,row in inputs['files'].items():
            require(sha(BASE/'P'/row['relative'])==row['sha256'],'Copied dependency hash mismatch')
            dependencies=list(map(str,registry.get_dependencies(package,options)))
            for dep in dependencies:
                require(not dep.startswith('/Game/') or dep in inputs['files'],'Unstaged Game dependency: '+dep)
                require(not dep.startswith('/Script/Mikdash'),'Project module dependency')
            closure[package]=dependencies
        report['nativeDependencyClosure']=closure
        report['reflection']={}
        for name in ('set_num_custom_data_floats','set_custom_data_value','get_instance_transform','update_instance_transform'):
            available=callable(getattr(ue.HierarchicalInstancedStaticMeshComponent,name,None))
            report['reflection'][name]=available
            require(available,'Missing reflected HISM function: '+name)
        report['reflection']['scope']='Callable availability only; no component, actor or mesh load in Compile'
        parms=inputs['parameters']['MI_RV4_Cloth'];defaults={}
        for name in ('WalkPositionTexture','WalkNormalTexture','IdlePositionTexture','IdleNormalTexture'):
            defaults[name]=ue.load_asset(parms[name]);require(isinstance(defaults[name],ue.Texture),'Missing VAT texture')
        for name in ('WalkMinBBox','WalkSizeBBox','IdleMinBBox','IdleSizeBBox'):defaults[name]=parms[name]
        texture=lambda name:ue.load_asset('/Game/MikdashV3/Characters/ResidentV4/Textures/'+name)
        surface={'Mottle':texture('T_RV4_SlubMottle'),'DetailNormal':texture('T_RV4_WeaveN')}
        spec=json.loads((BASE/'vat-spec.json').read_text())
        # Use unchanged generator's graph kernels, under THIS audited world guard.
        # Its public convenience API delegates to an editor subsystem, so is NOT
        # invoked in the commandlet. These kernels create a fresh unsaved material.
        name='M_Angular_'+run.replace('-','_')
        require(not ue.EditorAssetLibrary.does_asset_exist(builder.NAMESPACE+'/Materials/'+name),'Fresh candidate required')
        mat=builder._build(ue,spec,builder.NAMESPACE,name,defaults,report)
        builder._surface(ue,mat,report,surface)
        compile_graph(mat,report,'unaltered_generated_real_Time_graph');graph_proof(mat,report)
        if mode=='Compile':
            report['status']='compile_readback_passed'
        else:
            prior=json.loads((BASE/'runs'/run/'compile/native.json').read_text())
            require(prior['status']=='compile_readback_passed' and prior['harnessHashesSha256']==report['harnessHashesSha256'],'Fresh matching Compile required')
            report['renderClock']=controlled_clock(mat)
            compile_graph(mat,report,'controlled_pose_graph')
            actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
            require(actors is not None,'Render requires initialized EditorActorSubsystem; no CDO mutation')
            def spawn(cls,pos=(0,0,0),rot=None):
                a=actors.spawn_actor_from_class(cls,ue.Vector(*pos),rot or ue.Rotator(),transient=True)
                require(a is not None,'Actor spawn failed');spawned.append(a);return a
            owner=spawn(ue.Actor)
            sub=ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
            require(sub is not None,'SubobjectDataSubsystem unavailable')
            handles=sub.k2_gather_subobject_data_for_instance(owner)
            require(bool(handles),'Actor subobject handle missing')
            params=ue.AddNewSubobjectParams(parent_handle=handles[0],new_class=ue.HierarchicalInstancedStaticMeshComponent)
            handle,reason=sub.add_new_subobject(params)
            bodies=owner.get_components_by_class(ue.HierarchicalInstancedStaticMeshComponent)
            require(len(bodies)==1,'Transient HISM creation failed: '+str(reason));body=bodies[0]
            body.set_mobility(ue.ComponentMobility.MOVABLE);body.set_num_custom_data_floats(30)
            require(body.get_editor_property('num_custom_data_floats')==30,'HISM data stride')
            mesh=ue.load_asset(inputs['mesh']);require(isinstance(mesh,ue.StaticMesh),'Missing staged mesh')
            require(body.set_static_mesh(mesh),'Transient mesh bind failed')
            body.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
            body.set_editor_property('world_position_offset_writes_velocity',True)
            body.set_editor_property('bounds_scale',2.0)
            require(body.add_instance(ue.Transform())==0,'Expected one instance')
            import pose_capture
            pose_capture.run(ue,builder,mat,body,world,inputs,spawn,out,report,png_safe)
            report['status']='controlled_pose_samples_not_temporal_acceptance'
    except Exception as exc:
        report['status']='failed';report['error']=str(exc);report['traceback']=traceback.format_exc()
        raise
    finally:
        if actors:
            for actor in reversed(spawned):
                try:actors.destroy_actor(actor)
                except Exception as exc:report.setdefault('cleanupErrors',[]).append(str(exc))
        try:atomic(out/'native.json',report)
        finally:
            if mode=='Render':ue.SystemLibrary.quit_editor()

if __name__=='__main__':main()
