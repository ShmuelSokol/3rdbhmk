"""Isolated live crowd review map; no main-map edits or runtime adoption."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,re,math
import unreal as ue

ROOT=Path(__file__).resolve().parents[1]
match=re.search(r'-ResidentRuntimeStudy=(02|03)\b',ue.SystemLibrary.get_command_line())
STUDY=match.group(1) if match else '02'
NS='/Game/MikdashV3/Review/ResidentRuntime'+STUDY
MAP=NS+'/RuntimeReview'
OUT=ROOT/('SourceAssets/perf-review/crowd-vat/ResidentRuntime'+STUDY)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
disk=lambda p:ROOT/('Content/'+p.split('.')[0].removeprefix('/Game/')+'.uasset')

def run():
    build='-ResidentRuntimeBuild' in ue.SystemLibrary.get_command_line()
    OUT.mkdir(parents=True,exist_ok=True)
    output=OUT/('native-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    protected=list((ROOT/'Content').rglob('*.umap'))
    protected=[p for p in protected if p!=ROOT/('Content/MikdashV3/Review/ResidentRuntime'+STUDY+'/RuntimeReview.umap')]
    for folder in ('Characters/ResidentV4','Runtime/CrowdResidentStudy12','Runtime/CrowdResidentStudy13'):
        protected+=list((ROOT/'Content/MikdashV3'/folder).rglob('*.uasset'))
    before={p.relative_to(ROOT).as_posix():sha(p) for p in protected}
    report=dict(status='running',map=MAP,scope='Separate48-person live movement review map with two Study13 variants. No main-map adoption, navigation/visual/performance acceptance.',protectedBefore=before)
    try:
        editor=ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        assert not editor.get_editor_world().get_outermost().get_name().startswith('/Game/')
        assert not editor.get_game_world()
        meshes=[];sources=[]
        for variant in ('Man_Elder','Woman_Young'):
            folder=ROOT/'SourceAssets/perf-review/crowd-vat/ResidentStudy13/Cast'/variant
            p=next(p for p in folder.glob('native-*.json') if json.loads(p.read_text())['status']=='built-needs-fresh-readback-and-render')
            r=json.loads(p.read_text())
            for name,h in r['assets'].items():assert sha(ROOT/name)==h
            mesh=ue.load_asset(r['variants'][0]['mesh']);assert mesh;meshes.append(mesh)
            sources.append(dict(variant=variant,mesh=mesh.get_path_name(),receipt=p.relative_to(ROOT).as_posix(),receiptSha256=sha(p)))
        plane=ue.load_asset('/Engine/BasicShapes/Plane');material=ue.load_asset('/Engine/BasicShapes/BasicShapeMaterial')
        assert plane and material
        report['sources']=sources
        settings_path=ROOT/'Scripts/release_crowd_vat.spec.json'
        runtime_settings=json.loads(settings_path.read_text())['wanted'] if STUDY=='03' else {}
        runtime_settings={**runtime_settings,'crowd_count':48}
        report['releaseSettings']=dict(file=settings_path.relative_to(ROOT).as_posix(),sha256=sha(settings_path),applied=runtime_settings)
        actors=ue.get_editor_subsystem(ue.EditorActorSubsystem)
        if build:
            assert not ue.EditorAssetLibrary.does_directory_exist(NS),'Fresh namespace required'
            assert ue.get_editor_subsystem(ue.LevelEditorSubsystem).new_level(MAP)
            world=editor.get_editor_world()
            world.get_world_settings().set_editor_property('default_game_mode',ue.GameModeBase.static_class())
            def spawn(cls,label,pos,rot=ue.Rotator()):
                a=actors.spawn_actor_from_class(cls,ue.Vector(*pos),rot,transient=False);assert a
                a.set_actor_label(label);return a
            floor=spawn(ue.StaticMeshActor,'ResidentReviewFloor',(0,0,0))
            floor.static_mesh_component.set_static_mesh(plane);floor.static_mesh_component.set_material(0,material)
            floor.static_mesh_component.set_collision_profile_name('BlockAll')
            floor.set_actor_scale3d(ue.Vector(50,50,1))
            for i,(intensity,yaw) in enumerate(((3.,-115.),(1.,-45.))):
                light=spawn(ue.DirectionalLight,'ResidentReviewLight'+str(i),(0,0,1500),ue.Rotator(pitch=-25,yaw=yaw))
                light.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
                light.light_component.set_editor_property('intensity',intensity)
            camera=spawn(ue.CameraActor,'ResidentReviewCamera',(0,-2500,1400),ue.Rotator(pitch=-28,yaw=90))
            camera.set_editor_property('auto_activate_for_player',ue.AutoReceiveInput.PLAYER0)
            camera.get_component_by_class(ue.CameraComponent).set_field_of_view(60.)
            settings=camera.get_component_by_class(ue.CameraComponent).get_editor_property('post_process_settings')
            for name,value in dict(override_auto_exposure_min_brightness=True,override_auto_exposure_max_brightness=True,auto_exposure_min_brightness=1.,auto_exposure_max_brightness=1.,override_auto_exposure_bias=True,auto_exposure_bias=0.,override_bloom_intensity=True,bloom_intensity=0.).items():settings.set_editor_property(name,value)
            camera.get_component_by_class(ue.CameraComponent).set_editor_property('post_process_settings',settings)
            crowd=spawn(ue.MikdashCrowdField,'ResidentReviewCrowd',(0,0,0))
            values=dict(crowd_count=48,pose_meshes=meshes,use_vertex_animation=True,activate_on_begin_play=True,enable_visitor_groups=True,trace_ground_on_seed=True,sweep_group_obstacles=True,figure_scale_min=1.,figure_scale_max=1.,update_budget_per_frame=48)
            values.update(runtime_settings)
            for name,value in values.items():crowd.set_editor_property(name,value)
            zone=ue.MikdashCrowdZone()
            for name,value in dict(name='ResidentReview',polygon_cm=[ue.Vector2D(-1000,-1000),ue.Vector2D(1000,-1000),ue.Vector2D(1000,1000),ue.Vector2D(-1000,1000)],standing_ratio=.15,ground_z_base=0.,goal_cm=ue.Vector2D(800,0),goal_weight=.3,flow_direction_degrees=0.,reseed_edge_a=ue.Vector2D(-850,-700),reseed_edge_b=ue.Vector2D(-850,700),edge_margin_cm=100.).items():zone.set_editor_property(name,value)
            crowd.set_editor_property('zones',[zone])
            assert ue.EditorLoadingAndSavingUtils.save_map(world,MAP)
            report['status']='built-needs-fresh-readback-and-render'
        else:
            prior=[json.loads(p.read_text()) for p in OUT.glob('native-*.json') if p!=output]
            built=next(r for r in prior if r['status']=='built-needs-fresh-readback-and-render')
            assert sha(ROOT/built['mapFile'])==built['mapSha256']
            assert ue.EditorLoadingAndSavingUtils.load_map(MAP)
            world=editor.get_editor_world()
            report['status']='verified-fresh-candidate-not-rendered'
        assert world.get_outermost().get_name()==MAP
        crowd=next(a for a in actors.get_all_level_actors() if isinstance(a,ue.MikdashCrowdField))
        assert crowd.get_editor_property('crowd_count')==48
        for name,value in runtime_settings.items():
            actual=crowd.get_editor_property(name)
            assert math.isclose(actual,value,rel_tol=1e-6,abs_tol=1e-6),(name,actual,value)
        assert list(crowd.get_editor_property('pose_meshes'))==meshes
        for name in ('use_vertex_animation','activate_on_begin_play','enable_visitor_groups','trace_ground_on_seed','sweep_group_obstacles'):assert crowd.get_editor_property(name)
        zones=list(crowd.get_editor_property('zones'));assert len(zones)==1 and zones[0].get_editor_property('ground_z_base')==0.
        assert world.get_world_settings().get_editor_property('default_game_mode')==ue.GameModeBase.static_class()
        cameras=[a for a in actors.get_all_level_actors() if isinstance(a,ue.CameraActor)];assert len(cameras)==1
        assert cameras[0].get_editor_property('auto_activate_for_player')==ue.AutoReceiveInput.PLAYER0
        map_file=ROOT/('Content/MikdashV3/Review/ResidentRuntime'+STUDY+'/RuntimeReview.umap');assert map_file.is_file()
        report.update(mapFile=map_file.relative_to(ROOT).as_posix(),mapSha256=sha(map_file),crowd=crowd.get_path_name(),camera=cameras[0].get_path_name(),actorCount=len(actors.get_all_level_actors()))
    except Exception as error:
        report.update(status='failed',error=repr(error));raise
    finally:
        report['protectedUnchanged']=all(sha(ROOT/name)==h for name,h in before.items())
        if not report['protectedUnchanged']:report['status']='failed-protected-changed'
        output.write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':run()
