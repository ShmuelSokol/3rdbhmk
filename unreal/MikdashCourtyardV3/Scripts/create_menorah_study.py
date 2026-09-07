"""Original TI-photo-guided menorah study. Offline --export only by default.

Physical calibration is illustrative. No engine launch, map changes or claim of
an exact manufactured-object replica. Native importer is explicit run_native().
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone

ROOT=Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
FOLDER=ROOT/'SourceAssets/vessels-review/MenorahStudyV1'
SPEC=ROOT/'SourceAssets/vessels-review/menorah-model-spec.json'
DEST='/Game/MikdashV3/MaterialReview/TempleInstituteMenorahStudyV1'
H=180.0  # Explicit illustrative calibration, NOT measured artifact height.


def lathe(profile, center=(0,0,0), segments=48, lobes=0, amplitude=0):
    """Closed profile from lower axis to upper axis; distinct pole vertices."""
    vertices=[]; rings=[]; faces=[]
    for radius,z in profile:
        ring=[]
        for i in range(1 if radius==0 else segments):
            angle=i*math.tau/segments
            r=radius*(1+amplitude*math.cos(lobes*angle))
            ring.append(len(vertices))
            vertices.append((center[0]+r*math.cos(angle),center[1]+r*math.sin(angle),center[2]+z))
        rings.append(ring)
    for a,b in zip(rings,rings[1:]):
        for i in range(segments):
            j=(i+1)%segments
            if len(a)==1 and len(b)>1:faces.append((a[0],b[j],b[i]))
            elif len(b)==1 and len(a)>1:faces.append((a[i],a[j],b[0]))
            elif len(a)>1 and len(b)>1:faces.extend([(a[i],a[j],b[j]),(a[i],b[j],b[i])])
    return vertices,faces


def band(sign, reach, root_z, terminal_z):
    vertices=[];faces=[]
    # Bevelled rectangle: broad front surface, deliberately not a round pipe.
    section=[(-.5,-.35),(-.35,-.5),(.35,-.5),(.5,-.35),(.5,.35),(.35,.5),(-.35,.5),(-.5,.35)]
    for i in range(65):
        a=i*math.pi/128
        x=sign*reach*math.sin(a);z=root_z+(terminal_z-root_z)*(1-math.cos(a))
        dx=sign*reach*math.cos(a);dz=(terminal_z-root_z)*math.sin(a);length=math.hypot(dx,dz)
        nx=-dz/length;nz=dx/length
        for cross,depth in section:vertices.append((x+nx*cross*H*.023,depth*H*.017,z+nz*cross*H*.023))
    for i in range(64):
        for j in range(8):
            a=i*8+j;b=i*8+(j+1)%8;c=(i+1)*8+(j+1)%8;d=(i+1)*8+j
            faces.extend([(a,b,c),(a,c,d)])
    for ring,reverse in [(0,True),(64*8,False)]:
        for j in range(1,7):
            triangle=(ring,ring+j,ring+j+1)
            faces.append(tuple(reversed(triangle)) if reverse else triangle)
    return orient((vertices,faces))


def orient(mesh):
    v,f=mesh
    volume=sum((v[a][0]*(v[b][1]*v[c][2]-v[b][2]*v[c][1])+v[a][1]*(v[b][2]*v[c][0]-v[b][0]*v[c][2])+v[a][2]*(v[b][0]*v[c][1]-v[b][1]*v[c][0]))/6 for a,b,c in f)
    if volume<0:f=[(a,c,b) for a,b,c in f]
    return v,f


def assembly():
    helper_path=ROOT/'Scripts/create_heikhal_keilim.py'
    module_spec=importlib.util.spec_from_file_location('_keilim_geometry_helpers',helper_path)
    helper=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(helper)
    parts=[]
    def add(name,kind,mesh):parts.append(dict(name=name,kind=kind,mesh=orient(mesh)))
    def turned(name,kind,profile,x=0,z=0,segments=48,lobes=0,amp=0):
        add(name,kind,lathe([(r*H,h*H) for r,h in profile],(x*H,0,z*H),segments,lobes,amp))
    # Two six-sided stepped tiers are an explicit provisional base plan.
    turned('BaseLower','base',[(0,0),(.25,0),(.25,.013),(.235,.02),(.235,.063),(.25,.07),(0,.07)],segments=6)
    turned('BaseUpper','base',[(0,.07),(.20,.07),(.20,.083),(.185,.09),(.185,.126),(.20,.135),(0,.135)],segments=6)
    turned('BaseCollar','base',[(0,.13),(.083,.13),(.083,.141),(.052,.15),(.04,.163),(0,.163)])
    add('CentralFacetedShaft','shaft',helper.bevel_box((0,0,H*.462),(H*.043,H*.032,H*.60),H*.004))
    for i,(root_z,reach) in enumerate([(.45,.35),(.55,.235),(.65,.12)],1):
        for sign in (-1,1):add('Branch_%d_%s'%(i,'L' if sign<0 else 'R'),'branch',band(sign,H*reach,H*root_z,H*.775))
        turned('Knop_Junction_%02d'%i,'knop',[(0,-.025),(.029,-.023),(.038,-.012),(.042,0),(.038,.014),(.03,.025),(0,.025)],z=root_z,lobes=12,amp=.06)
    lamp_x=[-.35,-.235,-.12,0,.12,.235,.35]
    for i,x in enumerate(lamp_x,1):
        for j in range(3):
            turned('Cup_Upper_%02d_%02d'%(i,j+1),'cup',[(0,0),(.012,0),(.014,.005),(.024,.020),(.026,.023),(.026,.026),(.011,.026),(0,.003)],x=x,z=.768+j*.028,lobes=12,amp=.04)
        turned('Knop_Upper_%02d'%i,'knop',[(0,0),(.023,0),(.036,.012),(.038,.024),(.035,.036),(.023,.046),(0,.046)],x=x,z=.852,lobes=12,amp=.08)
        turned('Flower_Upper_%02d'%i,'flower',[(0,0),(.013,0),(.020,.008),(.027,.020),(.020,.040),(0,.043)],x=x,z=.901,lobes=6,amp=.27)
        # Separate lamps have readable bowl rims and display-cap silhouettes.
        # No flame, wick orientation or service fitting certification implied.
        turned('Lamp_%02d'%i,'lamp',[(0,0),(.015,0),(.029,.009),(.040,.018),(.043,.027),(.040,.031),(.034,.025),(.012,.009),(0,.009)],x=x,z=.941)
        turned('LampDisplayCap_%02d'%i,'lamp_cap',[(0,0),(.042,0),(.042,.005),(.026,.011),(.009,.017),(.005,.026),(0,.032)],x=x,z=.968,lobes=12,amp=.025)
    turned('Cup_LowerCentral','cup',[(0,0),(.013,0),(.025,.022),(.029,.029),(.026,.035),(0,.035)],z=.259,lobes=12,amp=.06)
    turned('Knop_LowerCentral','knop',[(0,0),(.024,0),(.036,.009),(.039,.019),(.032,.031),(0,.038)],z=.292,lobes=12,amp=.06)
    for name,z in [('LowerBase',.164),('LowerStem',.332)]:
        turned('Flower_'+name,'flower',[(0,0),(.013,0),(.028,.012),(.023,.027),(.014,.045),(0,.049)],z=z,lobes=6,amp=.25)
    return parts


def export():
    if FOLDER.exists():raise RuntimeError('Existing original study preserved; create a new version for changes')
    parts=assembly()
    counts={kind:sum(p['kind']==kind for p in parts) for kind in ['cup','knop','flower','lamp','branch']}
    assert counts==dict(cup=22,knop=11,flower=9,lamp=7,branch=6)
    FOLDER.mkdir(parents=True)
    report=dict(status='original_photo_guided_assembly_exported_native_pending',height_calibration_cm=H,
        dimension_status='180cm is illustrative study calibration only; manufactured-object exact dimensions unknown',
        source_spec_sha256=hashlib.sha256(SPEC.read_bytes()).hexdigest(),
        helper_sha256=hashlib.sha256((ROOT/'Scripts/create_heikhal_keilim.py').read_bytes()).hexdigest(),
        source_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),namespace=DEST,
        counts=counts,parts=[],triangles=0,
        artistic_choices=['Symmetric normalized photo-fit curves; branch section/depth unmeasured',
            'Provisional six-sided two-tier base; no invented figurative base relief',
            'Original fluted/petalled ornaments approximate silhouette, not copied exact relief',
            'Separate display cap interpretation requires lamp close-up confirmation'],
        incomplete=['Exact physical calibration','Base panel relief motifs','Rear and side-reference match','Wick fittings and oil-service detail','Native import/render/collision/performance acceptance'],
        import_convention='Unreal XYZ cm; OBJ Y reflected and winding reversed for verified legacy importer; per-face normals and nondegenerate planar UV charts')
    lines=['# Original TI-photo-guided menorah study, illustrative 180cm calibration','o SM_MenorahStudyV1'];index=1;all_vertices=[]
    for part in parts:
        vertices,faces=part['mesh'];all_vertices.extend(vertices)
        # Welded position-edge incidence check catches open seams in each part.
        keys=[tuple(round(x,6) for x in v) for v in vertices];edges={};volume=0
        for a,b,c in faces:
            va,vb,vc=vertices[a],vertices[b],vertices[c]
            volume+=sum(va[i]*[vb[1]*vc[2]-vb[2]*vc[1],vb[2]*vc[0]-vb[0]*vc[2],vb[0]*vc[1]-vb[1]*vc[0]][i] for i in range(3))/6
            for i,j in [(a,b),(b,c),(c,a)]:
                edge=tuple(sorted([keys[i],keys[j]]));edges[edge]=edges.get(edge,0)+1
            adapted=[(v[0],-v[1],v[2]) for v in (va,vc,vb)]
            a1,b1,c1=adapted;ab=[b1[i]-a1[i] for i in range(3)];ac=[c1[i]-a1[i] for i in range(3)]
            n=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
            nlen=math.sqrt(sum(x*x for x in n));edge=math.sqrt(sum(x*x for x in ab));assert nlen>1e-8
            normal=[x/nlen for x in n];cu=sum(ac[i]*ab[i]/edge for i in range(3))/10;cv=nlen/edge/10
            for v in adapted:lines.append('v %.9f %.9f %.9f'%v)
            for uv in [(0,0),(edge/10,0),(cu,cv)]:lines.append('vt %.9f %.9f'%uv)
            for _ in range(3):lines.append('vn %.9f %.9f %.9f'%tuple(normal))
            lines.append('f '+' '.join('%d/%d/%d'%(i,i,i) for i in range(index,index+3)));index+=3
        assert volume>0 and all(n==2 for n in edges.values()), 'Part topology failure: '+part['name']
        report['parts'].append(dict(name=part['name'],kind=part['kind'],first_triangle=report['triangles'],triangles=len(faces),signed_volume_cm3=volume,closed_welded_edges=True))
        report['triangles']+=len(faces)
    path=FOLDER/'SM_MenorahStudyV1.obj';path.write_text('\n'.join(lines)+'\n',encoding='ascii')
    report['file']=path.name;report['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    report['bounds_cm']={key:[fn(p[i] for p in all_vertices) for i in range(3)] for key,fn in [('min',min),('max',max)]}
    (FOLDER/'geometry-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def run_native():
    """Root-run asset import only; reviewed keilim OBJ adapter settings."""
    import unreal as ue
    if Path(ue.Paths.project_dir()).resolve()!=ROOT or ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Use the intended editor outside gameplay')
    assets=ue.get_editor_subsystem(ue.EditorAssetSubsystem)
    if assets.does_directory_exist(DEST):raise RuntimeError('Existing native namespace preserved')
    report=json.loads((FOLDER/'geometry-manifest.json').read_text())
    path=FOLDER/report['file']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=report['sha256']:raise RuntimeError('Geometry hash changed')
    if hashlib.sha256(SPEC.read_bytes()).hexdigest()!=report['source_spec_sha256']:raise RuntimeError('Reference spec changed')
    receipt=dict(status='import_started',created=[],assigned=False,map_saved=False,dimension_status=report['dimension_status'])
    try:
        tools=ue.AssetToolsHelpers.get_asset_tools();ml=ue.MaterialEditingLibrary
        gold=tools.create_asset('M_MenorahStudyGold',DEST,ue.Material,ue.MaterialFactoryNew())
        if not gold:raise RuntimeError('Material factory failed')
        color=ml.create_material_expression(gold,ue.MaterialExpressionConstant3Vector)
        color.set_editor_property('constant',ue.LinearColor(1.0,.766,.336,1))
        assert ml.connect_material_property(color,'',ue.MaterialProperty.MP_BASE_COLOR)
        for value,prop in [(1.0,ue.MaterialProperty.MP_METALLIC),(.28,ue.MaterialProperty.MP_ROUGHNESS)]:
            node=ml.create_material_expression(gold,ue.MaterialExpressionConstant);node.set_editor_property('r',value)
            assert ml.connect_material_property(node,'',prop)
        ml.recompile_material(gold);assert assets.save_loaded_asset(gold,only_if_is_dirty=False)
        receipt['created'].append(gold.get_path_name())
        ui=ue.FbxImportUI()
        for key,value in dict(automated_import_should_detect_type=False,mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH,
            import_as_skeletal=False,import_mesh=True,import_animations=False,import_materials=False,import_textures=False,create_physics_asset=False).items():ui.set_editor_property(key,value)
        data=ui.get_editor_property('static_mesh_import_data')
        for key,value in dict(combine_meshes=True,transform_vertex_to_absolute=True,bake_pivot_in_vertex=False,
            convert_scene=False,convert_scene_unit=False,force_front_x_axis=False,import_uniform_scale=1.0,
            auto_generate_collision=False,build_nanite=False,generate_lightmap_u_vs=False,remove_degenerates=True,
            normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS).items():data.set_editor_property(key,value)
        task=ue.AssetImportTask()
        for key,value in dict(filename=str(path),destination_path=DEST+'/Meshes',destination_name='SM_MenorahStudyV1',
            automated=True,async_=False,replace_existing=False,save=False,options=ui,factory=ue.FbxFactory()).items():task.set_editor_property(key,value)
        tools.import_asset_tasks([task]);objects=list(task.get_objects())
        assert len(objects)==1 and isinstance(objects[0],ue.StaticMesh)
        mesh=objects[0];box=mesh.get_bounding_box()
        actual={'min':[box.min.x,box.min.y,box.min.z],'max':[box.max.x,box.max.y,box.max.z]}
        error=max(abs(actual[k][i]-report['bounds_cm'][k][i]) for k in actual for i in range(3))
        assert error<.05 and mesh.get_num_triangles(0)==report['triangles']
        mesh.set_material(0,gold);assert assets.save_loaded_asset(mesh,only_if_is_dirty=False)
        receipt['created'].append(mesh.get_path_name())
        receipt.update(status='native_asset_saved_unassigned_visual_review_pending',bounds_cm=actual,bounds_error_cm=error,triangles=mesh.get_num_triangles(0))
    except Exception as error:
        receipt.update(status='failed_partial_assets_preserved',error=str(error));raise
    finally:(FOLDER/'native-import.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def place_menorah_review():
    """Place original study only in checkpointed CourtyardGold; no access rules.

    Yaw90 maps local lamp-row X to north/south world Y, explicitly selecting
    Rambam Beit HaBechirah3:12 orientation, not resolving the competing view.
    """
    import unreal as ue
    review='/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold'
    editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    world=editor.get_editor_world()
    if Path(ue.Paths.project_dir()).resolve()!=ROOT or editor.get_game_world():
        raise RuntimeError('Use the intended editor outside gameplay')
    if world.get_outermost().get_name()!=review:raise RuntimeError('Load CourtyardGold review map first')
    if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Resolve dirty work before checkpointed placement')
    native=json.loads((FOLDER/'native-import.json').read_text())
    if native['status']!='native_asset_saved_unassigned_visual_review_pending':raise RuntimeError('Successful native import required')
    api=ue.get_editor_subsystem(ue.EditorActorSubsystem);actors=api.get_all_level_actors()
    label='REVIEW_TempleInstituteMenorahStudyV1'
    if any(a.get_actor_label()==label for a in actors):raise RuntimeError('Existing menorah preserved; do not duplicate')
    floor_path='/Game/MikdashV3/Architecture/architecture_SM_0146_floor_Heichal_clear_floor'
    floors=[]
    for actor in actors:
        for component in actor.get_components_by_class(ue.StaticMeshComponent):
            mesh=component.get_editor_property('static_mesh')
            if mesh and mesh.get_path_name().split('.')[0]==floor_path:floors.append((actor,component,mesh))
    if len(floors)!=1:raise RuntimeError('Expected exactly one measured Heichal floor component')
    floor,component,floor_mesh=floors[0]
    location=component.get_world_location();rotation=component.get_world_rotation();scale=component.get_world_scale()
    if max(abs(v) for v in (location.x,location.y,location.z,rotation.pitch,rotation.yaw,rotation.roll))>.001 or max(abs(v-1) for v in (scale.x,scale.y,scale.z))>.001:
        raise RuntimeError('Floor baked identity transform changed')
    box=floor_mesh.get_bounding_box()
    actual_floor={'min':[box.min.x,box.min.y,box.min.z],'max':[box.max.x,box.max.y,box.max.z]}
    expected_floor={'min':[-5600,-500,904.9999237060547],'max':[-3600,500,925]}
    if max(abs(actual_floor[k][i]-expected_floor[k][i]) for k in actual_floor for i in range(3))>.05:raise RuntimeError('Floor basis changed')
    mesh=ue.load_asset(DEST+'/Meshes/SM_MenorahStudyV1')
    if not isinstance(mesh,ue.StaticMesh):raise RuntimeError('Native menorah mesh missing')
    b=mesh.get_bounding_box();local={'min':[b.min.x,b.min.y,b.min.z],'max':[b.max.x,b.max.y,b.max.z]}
    if max(abs(local[k][i]-native['bounds_cm'][k][i]) for k in local for i in range(3))>.05 or mesh.get_num_triangles(0)!=36012:
        raise RuntimeError('Native menorah dimensions or topology changed')
    position=[-4900,300,925]
    bounds={'min':[position[0]-local['max'][1],position[1]+local['min'][0],position[2]+local['min'][2]],
            'max':[position[0]-local['min'][1],position[1]+local['max'][0],position[2]+local['max'][2]]}
    if any(bounds['min'][i]<=actual_floor['min'][i] or bounds['max'][i]>=actual_floor['max'][i] for i in (0,1)) or abs(bounds['min'][2]-925)>.05:
        raise RuntimeError('Rotated menorah does not fit measured floor')
    vessel_labels=['REVIEW_HeikhalKeilim_SM_GoldenIncenseAltarStudy','REVIEW_HeikhalKeilim_SM_ShulchanStudy']
    for vessel_label in vessel_labels:
        matching=[a for a in actors if a.get_actor_label()==vessel_label]
        if len(matching)!=1:raise RuntimeError('Expected existing altar/table review: '+vessel_label)
        o,e=matching[0].get_actor_bounds(False);lo=[o.x-e.x,o.y-e.y,o.z-e.z];hi=[o.x+e.x,o.y+e.y,o.z+e.z]
        if all(bounds['min'][i]<hi[i] and lo[i]<bounds['max'][i] for i in range(3)):raise RuntimeError('Menorah overlaps existing vessel bounds')
    for fx in (.05,.5,.95):
        for fy in (.05,.5,.95):
            x=bounds['min'][0]+fx*(bounds['max'][0]-bounds['min'][0]);y=bounds['min'][1]+fy*(bounds['max'][1]-bounds['min'][1])
            hit=ue.SystemLibrary.line_trace_single_by_profile(world_context_object=world,start=ue.Vector(x,y,925.5),
                end=ue.Vector(x,y,bounds['max'][2]+.5),profile_name='Pawn',trace_complex=True,
                actors_to_ignore=[floor],draw_debug_type=ue.DrawDebugTrace.NONE,ignore_self=False)
            if hit:raise RuntimeError('Existing blocking geometry at menorah placement probe')
    original=ROOT/'Content/MikdashV3/Maps/Courtyard.umap'
    review_file=ROOT/'Content/MikdashV3/MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold.umap'
    before=hashlib.sha256(original.read_bytes()).hexdigest()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    checkpoint=ROOT.parent/'ReviewCheckpoints'/('Menorah-'+stamp);checkpoint.mkdir(parents=True,exist_ok=False)
    shutil.copy2(review_file,checkpoint/'CourtyardGold.umap')
    receipt=dict(status='checkpointed_placement_started',review_map=review,checkpoint=str(checkpoint),
        original_courtyard_sha_before=before,review_sha_before=hashlib.sha256(review_file.read_bytes()).hexdigest(),
        position_cm=position,yaw_degrees=90,expected_bounds_cm=bounds,
        orientation_source='Rambam Beit HaBechirah3:12: lamps north-south; explicit selected interpretation',
        orientation_url='https://www.chabad.org/library/article_cdo/aid/1007196/jewish/Beit-Habechirah-Chapter-3.htm',
        limitations=['TI illustrated tour notes competing north-south/east-west orientations; placement does not settle dispute',
                    '180cm scale and detailed base/ornament profiles remain illustrative, not measured TI replica',
                    'Nine vertical collision probes are not exhaustive overlap or player-clearance verification',
                    'No tending steps, oil or flame service, or ordinary visitor access permission added'])
    receipt_path=FOLDER/('placement-'+stamp+'.json')
    def write():receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
    write()
    try:
        actor=api.spawn_actor_from_class(ue.StaticMeshActor,ue.Vector(*position),ue.Rotator(pitch=0,yaw=90,roll=0),transient=False)
        if not actor:raise RuntimeError('Menorah actor creation failed')
        actor.set_actor_label(label);actor.set_folder_path('Review/HeikhalKeilim_IncompleteAssemblies')
        component=actor.get_component_by_class(ue.StaticMeshComponent)
        if not component.set_static_mesh(mesh):raise RuntimeError('Menorah mesh assignment failed')
        component.set_collision_profile_name('NoCollision')
        levels=ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        if not levels.save_current_level() or not levels.load_level(review):raise RuntimeError('Review save/reopen failed')
        matching=[a for a in api.get_all_level_actors() if a.get_actor_label()==label]
        if len(matching)!=1:raise RuntimeError('Reopened menorah actor count differs')
        actor=matching[0];component=actor.get_component_by_class(ue.StaticMeshComponent)
        if component.get_editor_property('static_mesh').get_path_name()!=mesh.get_path_name():raise RuntimeError('Reopened menorah mesh differs')
        o,e=actor.get_actor_bounds(False);actual={'min':[o.x-e.x,o.y-e.y,o.z-e.z],'max':[o.x+e.x,o.y+e.y,o.z+e.z]}
        error=max(abs(actual[k][i]-bounds[k][i]) for k in actual for i in range(3))
        if error>.05:raise RuntimeError('Reopened rotated bounds differ')
        after=hashlib.sha256(original.read_bytes()).hexdigest()
        receipt.update(actual_bounds_cm=actual,bounds_error_cm=error,original_courtyard_sha_after=after,original_courtyard_unchanged=before==after)
        if before!=after:raise RuntimeError('Original Courtyard changed')
        receipt['status']='menorah_saved_reopened_in_review_visual_acceptance_pending'
    except Exception as error:
        receipt.update(status='failed_partial_review_state_preserved',error=str(error));raise
    finally:write()
    return receipt


if __name__=='__main__':
    if '--export' in sys.argv:
        result=export();print(json.dumps({k:result[k] for k in ['status','counts','triangles','bounds_cm']},indent=2))
    else:raise SystemExit('Use --export offline; native import is root-owned separately')
