"""Dedicated real-RHI PIE: metric Kotel access stair round trip; one initial test placement.
No subsequent teleport, time acceleration, service startup or map save.
Requires unique SlotNamePrefix=AstraProbe_* and SaveSlot=AstraProbe_* overrides.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timezone
import unreal as u

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Scripts'))
from release_surface_soft import inventory

TARGET = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
CMD = u.SystemLibrary.get_command_line()
OUT = ROOT/'SourceAssets/mount-access'/('candidate-kotel-walk-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
state = {'wall':time.monotonic(), 'handle':None, 'busy':False, 'stopping':False, 'last':-1}
report = {'status':'starting','errors':[], 'samples':[], 'pid':os.getpid(),
          'scope':'Lower landing to upperdeck, platform-only endpoint, then back. One initial test placement; normal walking only. No plaza-to-landing approach, accessibility, full Mount connectivity or halachic claim.'}


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def xyz(v): return [float(v.x),float(v.y),float(v.z)]
def maps(): return {str(p):sha(p) for p in (ROOT/'Content').rglob('*.umap')}
def save_roots():
    return [ROOT/'Saved/SaveGames', Path(os.environ.get('LOCALAPPDATA','C:/absent'))/'MikdashCourtyardV3/Saved/SaveGames']
def saves():
    return {str(p):sha(p) for root in save_roots() if root.exists() for p in root.glob('*.sav') if not p.name.startswith('AstraProbe_')}
def write():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def clean():
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages')
def frame(aa):
    cls=u.load_class(None,'/Script/MikdashRuntime.MikdashSceneUnits')
    if cls is None: raise RuntimeError('Frame class missing')
    ds=[a for a in aa if u.MathLibrary.class_is_child_of(a.get_class(),cls)]
    if len(ds)!=1: raise RuntimeError('Exactly one descriptor required')
    d=ds[0];p=d.get_editor_property('fixed_architecture_origin_cm')
    if d.get_actor_label()!='RELEASE_SceneUnits_Selected48_V1' or int(d.get_editor_property('descriptor_schema_version'))!=1 or int(d.get_editor_property('coordinate_revision').value)!=1 or str(d.get_editor_property('scene_revision'))!='Selected48.v1' or xyz(p)!=[-6200,0,0]:
        raise RuntimeError('Wrong Selected48 frame')
Y=19972.432518
MESHES={
 'RELEASE_MountAccess_Deck':'KotelApproach_ElevatedDeck_V2',
 'RELEASE_MountAccess_Guards':'KotelApproach_ElevatedGuards_V2',
 'RELEASE_MountAccess_Portal':'KotelApproach_AboveWallPortal_V2'}
ROUTE=[('upper_deck',-12650.0,2.0),('platform_only',-12350.0,0.0),
       ('upper_deck_return',-12650.0,2.0),('lower_landing_return',-18250.0,-1430.5)]
START=[-18250.0,Y,-1430.5]
def access_guard(aa):
    found={}
    for label,mesh_name in MESHES.items():
        matching=[a for a in aa if a.get_actor_label()==label]
        if len(matching)!=1: raise RuntimeError('Exact access label count differs: '+label)
        a=matching[0];r=a.get_actor_rotation()
        if xyz(a.get_actor_location())!=[0,0,2] or [r.pitch,r.yaw,r.roll]!=[0,0,0] or xyz(a.get_actor_scale3d())!=[1,1,1]:
            raise RuntimeError('Metric access transform differs')
        components=a.get_components_by_class(u.StaticMeshComponent)
        if len(components)!=1: raise RuntimeError('Expected one access mesh component')
        c=components[0];mesh=c.get_editor_property('static_mesh')
        if mesh is None or mesh.get_path_name().split('.')[0]!='/Game/MikdashV3/ArrivalReview/MountAccessV2/'+mesh_name:
            raise RuntimeError('Access mesh identity differs')
        body=mesh.get_editor_property('body_setup')
        if body is None or body.get_editor_property('collision_trace_flag')!=u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
            raise RuntimeError('Access requires actual tread collision')
        if str(c.get_collision_profile_name())!='BlockAll' or c.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION:
            raise RuntimeError('Access collision is not walk-blocking')
        step=c.get_editor_property('can_character_step_up_on')
        if step==u.CanBeCharacterBase.ECB_NO: raise RuntimeError('Access explicitly forbids step-up')
        found[label]={'actor':a.get_name(),'mesh':mesh.get_path_name(),'profile':str(c.get_collision_profile_name()),
                      'stepUp':str(step),'collision':str(c.get_collision_enabled()),'pose':[0,0,2,0,0,0,1,1,1]}
    return found
def service_off(aa):
    cls=u.load_class(None,'/Script/MikdashRuntime.MikdashServiceActor')
    if cls is None: raise RuntimeError('Service class missing')
    for a in aa:
        if u.MathLibrary.class_is_child_of(a.get_class(),cls):
            if a.get_editor_property('start_on_begin_play') or a.is_service_active():
                raise RuntimeError('Service must remain inactive; probe never starts/stops it')
def finish(status):
    if state.get('movement'): state['movement'].stop_movement_immediately()
    report['status']=status;state.update(stopping=True,stopWall=time.monotonic())
    levels.editor_request_end_play();write()
def shutdown():
    try:
        if 'settings' in state:
            state['settings'].set_editor_property('GameGetsMouseControl',state['oldMouse'])
            u.SystemLibrary.execute_console_command(ed.get_editor_world(),'Slate.bAllowThrottling '+str(state['oldThrottle']))
        report['mapsUnchanged']=maps()==report.get('mapsBefore',{})
        report['originalSavesUnchanged']=saves()==report.get('savesBefore',{})
        if not report['mapsUnchanged'] or not report['originalSavesUnchanged']: report['errors'].append('Persistence guard failed')
        clean()
    except Exception as error:
        report['errors'].append('Shutdown failed: '+repr(error))
    finally:
        if report['errors']: report['status']='failed'
        try: write()
        finally:
            try:
                if state['handle'] is not None: u.unregister_slate_post_tick_callback(state['handle'])
            finally: u.SystemLibrary.quit_editor()


def hit_record(hit):
    if hit is None: return None
    if isinstance(hit,tuple):
        records=[v for v in hit if hasattr(v,'to_dict')]
        if records: hit=records[0]
        elif all(v is None or v is False for v in hit): return None
        else: raise RuntimeError('Malformed trace tuple')
    if not hasattr(hit,'to_dict'): raise RuntimeError('Malformed trace result')
    d={str(k).lower().replace('_',''):v for k,v in hit.to_dict().items()}
    if not d.get('blockinghit',False): return None
    if 'impactpoint' not in d or 'impactnormal' not in d: raise RuntimeError('Trace missing geometry')
    actor=d.get('hitactor') or d.get('actor');comp=d.get('hitcomponent') or d.get('component')
    mesh=comp.get_editor_property('static_mesh') if isinstance(comp,u.StaticMeshComponent) else None
    return {'point':xyz(d['impactpoint']),'normal':xyz(d['impactnormal']),
            'actor':actor.get_name() if actor else None,'mesh':mesh.get_path_name().split('.')[0] if mesh else None,
            'actorClass':actor.get_class().get_path_name() if actor else None,
            'component':comp.get_path_name() if comp else None,
            'actorHidden':bool(actor.get_editor_property('hidden')) if actor else None,
            'actorCollision':bool(actor.get_actor_enable_collision()) if actor else None,
            'componentVisible':bool(comp.get_editor_property('visible')) if comp else None,
            'componentHidden':bool(comp.get_editor_property('hidden_in_game')) if comp else None}
def floor_trace(world,p,ignored):
    return hit_record(u.SystemLibrary.line_trace_single_by_profile(world_context_object=world,
        start=u.Vector(p[0],p[1],p[2]+30),end=u.Vector(p[0],p[1],p[2]-60),profile_name='Pawn',
        trace_complex=True,actors_to_ignore=ignored,draw_debug_type=u.DrawDebugTrace.NONE,ignore_self=False))
def expected_floor(x):
    for item in state['segments']:
        if item['xStartCm']<=x<item['xEndCm']: return item['topZcm']+2.0
    return 0.0 if -12500<=x<=-12300 else None


def kotel_visibility(world, pawn):
    # Same metric edge-0 camera as the rejected lighting capture. Diagnose the
    # actual collision surface in front of it without hiding/moving any actor.
    a=(-15127.514984215617,11907.932517753074)
    b=(-14450.014984215613,15836.432517753074)
    normal=(-.9854528733045355,.1699489173129251)
    mid=[(a[i]+b[i])/2 for i in range(2)]
    xy=[mid[i]+normal[i]*1000 for i in range(2)]
    def trace(start,end):
        return hit_record(u.SystemLibrary.line_trace_single_by_profile(
            world_context_object=world,start=u.Vector(*start),end=u.Vector(*end),
            profile_name='Pawn',trace_complex=True,actors_to_ignore=[pawn],
            draw_debug_type=u.DrawDebugTrace.NONE,ignore_self=False))
    ground=trace([*xy,1100],[*xy,-2900])
    if ground is None:
        return {'scope':'Collision diagnostics, not visual acceptance','ground':None,'rays':[]}
    eye=[*xy,ground['point'][2]+168]
    rays=[]
    for height in (eye[2],eye[2]+250,0.0,400.0):
        end=[mid[i]-normal[i]*100 for i in range(2)]+[height]
        rays.append({'start':eye,'end':end,'hit':trace(eye,end)})
    return {'scope':'Metric edge-0 camera; Pawn-profile rays cannot identify non-colliding visual occluders',
            'ground':ground,'eye':eye,'rays':rays}


def tick(dt):
    if state['busy']: return
    state['busy']=True
    try:
        world=ed.get_game_world();now=time.monotonic()
        if state['stopping']:
            if world and now-state['stopWall']<20: return
            if world: report['errors'].append('PIE teardown timeout')
            shutdown();return
        if now-state['wall']>600: finish('failed_wall_watchdog');return
        if world is None: return
        pc=u.GameplayStatics.get_player_controller(world,0)
        if pc is None: return
        if pc.is_walkthrough_menu_open(): pc.resume_walkthrough();return
        cine=u.MikdashCinematics.get(world)
        if cine and cine.is_playing(): cine.skip_intro();return
        if u.GameplayStatics.is_game_paused(world): return
        gt=u.GameplayStatics.get_time_seconds(world)
        pawn=u.GameplayStatics.get_player_pawn(world,0)
        if pawn is None: return
        if 'pawn' not in state:
            aa=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
            service_cls=u.load_class(None,'/Script/MikdashRuntime.MikdashServiceActor')
            if service_cls is None: raise RuntimeError('Service class missing')
            state['services']=[a for a in aa if u.MathLibrary.class_is_child_of(a.get_class(),service_cls)]
            service_off(state['services']);frame(aa)
            report['pieAccess']=access_guard(aa)
            report['kotelVisibility']=kotel_visibility(world,pawn)
            report['kotelSurfaces']=[]
            for actor in aa:
                if actor.get_actor_label().startswith(('RELEASE_Kotel','REVIEW_KotelPhoto','SM_JerusalemBuildings_Grid_N002_P001')):
                    report['kotelSurfaces'].append({
                        'label':actor.get_actor_label(),'actor':actor.get_name(),
                        'hidden':bool(actor.get_editor_property('hidden')),
                        'components':[{'mesh':c.get_editor_property('static_mesh').get_path_name() if c.get_editor_property('static_mesh') else None,
                                       'visible':bool(c.get_editor_property('visible')),'hidden':bool(c.get_editor_property('hidden_in_game')),
                                       'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]}
                                      for c in actor.get_components_by_class(u.StaticMeshComponent)]})
            movement=pawn.get_component_by_class(u.CharacterMovementComponent)
            capsule=pawn.get_component_by_class(u.CapsuleComponent)
            if movement is None or capsule is None: raise RuntimeError('Actual walking character required')
            radius=capsule.get_scaled_capsule_radius();half=capsule.get_scaled_capsule_half_height()
            report['physical']={'radius':radius,'halfHeight':half,'maxStepHeight':movement.get_editor_property('max_step_height'),
                                'walkSpeed':movement.get_editor_property('max_walk_speed'),
                                'collisionProfile':str(capsule.get_collision_profile_name())}
            floor=floor_trace(world,START,[pawn])
            if floor is None or abs(floor['point'][2]-START[2])>1 or floor['normal'][2]<.95:
                raise RuntimeError('Lower landing actual support differs')
            centre=u.Vector(START[0],START[1],START[2]+half+2)
            collision=hit_record(u.SystemLibrary.capsule_trace_single_by_profile(world_context_object=world,
                start=centre+u.Vector(0,0,.1),end=centre,radius=radius,half_height=half,profile_name='Pawn',
                trace_complex=False,actors_to_ignore=[pawn],draw_debug_type=u.DrawDebugTrace.NONE,ignore_self=False))
            if collision is not None: raise RuntimeError('Initial landing capsule blocked: '+repr(collision))
            movement.stop_movement_immediately()
            pawn.set_actor_location(centre,False,True)
            if math.dist(xyz(pawn.get_actor_location()),xyz(centre))>.1: raise RuntimeError('Initial test placement refused')
            report['initialPlacement']={'capsuleCentre':xyz(centre),'floor':floor,'count':1}
            state.update(pawn=pawn,movement=movement,capsule=capsule,start=gt,leg=0,lastProgress=gt,
                         progress=xyz(centre),half=half)
            report['checkpoints']=[];write();return
        service_off(state['services'])
        if pawn!=state['pawn']: raise RuntimeError('Pawn changed')
        movement=state['movement'];capsule=state['capsule'];pos=pawn.get_actor_location()
        if capsule.get_scaled_capsule_half_height()!=state['half'] or capsule.get_scaled_capsule_radius()!=report['physical']['radius'] or movement.get_editor_property('max_step_height')!=report['physical']['maxStepHeight'] or movement.get_editor_property('max_walk_speed')!=report['physical']['walkSpeed']:
            raise RuntimeError('Physical walking settings changed during probe')
        elapsed=gt-state['start'];feet=[pos.x,pos.y,pos.z-state['half']]
        if elapsed>180: finish('failed_simulation_watchdog');return
        if abs(pos.y-Y)>110:
            report['corridorFailure']={'seconds':elapsed,'feet':feet,'velocity':xyz(pawn.get_velocity())}
            raise RuntimeError('Left the authored300cm clear corridor')
        if elapsed-state['last']>=.25:
            floor=floor_trace(world,feet,[pawn]);expected=expected_floor(pos.x)
            direction=1.0 if ROUTE[state['leg']][1]>pos.x else -1.0
            ahead=hit_record(u.SystemLibrary.capsule_trace_single_by_profile(world_context_object=world,
                start=pos,end=pos+u.Vector(direction*120,0,0),
                radius=report['physical']['radius'],half_height=state['half'],profile_name='Pawn',
                trace_complex=False,actors_to_ignore=[pawn],draw_debug_type=u.DrawDebugTrace.NONE,ignore_self=False))
            report['samples'].append({'seconds':elapsed,'feet':feet,'floor':floor,'expectedFloor':expected,
                'walking':movement.is_walking(),'floorDelta':feet[2]-floor['point'][2] if floor else None,
                'aheadCapsule':ahead,'velocity':xyz(pawn.get_velocity())})
            state['last']=elapsed
        label,target_x,target_z=ROUTE[state['leg']]
        if abs(pos.x-target_x)<20 and abs(pos.y-Y)<20:
            movement.stop_movement_immediately()
            floor=floor_trace(world,feet,[pawn])
            good=bool(floor and abs(floor['point'][2]-target_z)<=1 and abs(feet[2]-floor['point'][2])<=5 and floor['normal'][2]>=.95 and movement.is_walking())
            row={'label':label,'feet':feet,'floor':floor,'expectedFloor':target_z,'passed':good,'seconds':elapsed}
            report['checkpoints'].append(row)
            if not good: raise RuntimeError('Checkpoint not grounded at expected surface: '+repr(row))
            state['leg']+=1
            if state['leg']==len(ROUTE):
                report['observedSeconds']=elapsed
                report['airborneSamples']=sum(not r['walking'] for r in report['samples'])
                report['missingSupportSamples']=sum(r['floor'] is None for r in report['samples'])
                finish('roundtrip_checkpoints_passed' if not report['airborneSamples'] and not report['missingSupportSamples'] else 'roundtrip_completed_with_grounding_findings');return
            label,target_x,target_z=ROUTE[state['leg']]
            state['lastProgress']=gt
        if math.dist(xyz(pos),state['progress'])>10:
            state['lastProgress']=gt;state['progress']=xyz(pos)
        elif gt-state['lastProgress']>8:
            raise RuntimeError('Walking stalled before '+label+' at '+repr(feet))
        dx,dy=target_x-pos.x,Y-pos.y;length=math.hypot(dx,dy)
        if length>.01: pawn.add_movement_input(u.Vector(dx/length,dy/length,0),1.0,True)
    except Exception as error:
        report['errors'].append(repr(error))
        if state['stopping']: shutdown()
        else: finish('failed_exception')
    finally: state['busy']=False


try:
    report.update(mapsBefore=maps(),savesBefore=saves())
    inventory();clean()
    world=ed.get_editor_world()
    if Path(u.Paths.project_dir()).resolve()!=ROOT or world is None or world.get_outermost().get_name()!=TARGET or ed.get_game_world(): raise RuntimeError('Wrong project/map or existing PIE')
    if '-nullrhi' in CMD.lower() or '-run=pythonscript' in CMD.lower(): raise RuntimeError('Real-RHI dedicated GUI PIE required')
    for key in ('SlotNamePrefix','SaveSlot'):
        found=re.findall(r'\b'+key+r'=(AstraProbe_[A-Za-z0-9_-]+)',CMD)
        if len(found)!=1 or len(re.findall(r'\b'+key+r'=',CMD))!=1: raise RuntimeError('One unique AstraProbe override required for '+key)
        if any(p.stem.startswith(found[0]) for root in save_roots() if root.exists() for p in root.glob('*.sav')): raise RuntimeError('Probe save override already exists')
    aa=list(actors.get_all_level_actors());frame(aa);service_off(aa)
    report['savedAccess']=access_guard(aa)
    plan_path=ROOT/'SourceAssets/mount-access/OpeningV2/opening-v2-spec.json'
    plan=json.loads(plan_path.read_text(encoding='utf-8-sig'))
    state['segments']=plan['walkingSegments']
    if len(state['segments'])!=90 or sum(s['kind']=='tread' for s in state['segments'])!=82: raise RuntimeError('Authored82step schema differs')
    report['planSha256']=sha(plan_path);report['route']=ROUTE;report['metricY']=Y
    settings=u.get_default_object(u.load_class(None,'/Script/UnrealEd.LevelEditorPlaySettings'))
    state.update(settings=settings,oldMouse=settings.get_editor_property('GameGetsMouseControl'),
                 oldThrottle=u.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling'))
    settings.set_editor_property('GameGetsMouseControl',False)
    u.SystemLibrary.execute_console_command(ed.get_editor_world(),'Slate.bAllowThrottling 0')
    write();state['handle']=u.register_slate_post_tick_callback(tick);levels.editor_request_begin_play()
except Exception as error:
    report['errors'].append(repr(error));report['status']='failed_setup';shutdown();raise
