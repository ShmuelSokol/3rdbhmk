"""90 simulated seconds of actual Candidate48 service; 300-second wall watchdog.
Dedicated editor ExecCmds script. Requires isolated AstraProbe_ save overrides.
No map saves, teleports, time acceleration or manufactured service completion.
Visibility capsule observations supplement native Pawn-channel route admission;
they do not certify an entire route or all eighteen stations.
"""
import hashlib
import json
import math
import os
import sys
from pathlib import Path
import time
from datetime import datetime, timezone
import unreal as u

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
from release_surface_soft import inventory
TARGET = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
LABEL = 'RELEASE_KohenGadolService_Selected48_V1'
STAMP = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = ROOT/'SourceAssets/service-review'/('candidate-runtime-'+STAMP+'.json')
CMD = u.SystemLibrary.get_command_line()
LEG_DIAGNOSTIC_ONLY = '-servicelegdiagnosticonly' in CMD.lower()
ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
settings = u.get_default_object(u.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
old_mouse = settings.get_editor_property('GameGetsMouseControl')
old_throttle = u.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def maps():
    return {str(p):sha(p) for p in (ROOT/'Content').rglob('*.umap')}


def saves():
    roots = [ROOT/'Saved/SaveGames', Path(os.environ.get('LOCALAPPDATA','C:/absent'))/'MikdashCourtyardV3/Saved/SaveGames']
    return {str(p):sha(p) for root in roots if root.exists() for p in root.glob('*.sav') if not p.name.startswith('AstraProbe_')}


def xyz(v):
    return [float(v.x),float(v.y),float(v.z)]


report = {'status':'starting','errors':[], 'samples':[], 'mapsBefore':maps(), 'savesBefore':saves(),
          'coverage':'90 seconds only; not full eighteen-station or visual acceptance',
          'capsuleChannel':'Visibility; native service independently checks Pawn channel'}
state = {'wall':time.monotonic(),'busy':False,'stopping':False,'handle':None,'lastSample':-1.0}


def write():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


def finish(status):
    report['status'] = status
    service = state.get('service')
    if service:
        service.stop_service()
    state.update(stopping=True,stopWall=time.monotonic())
    levels.editor_request_end_play()
    write()


def shutdown():
    try:
        settings.set_editor_property('GameGetsMouseControl',old_mouse)
        u.SystemLibrary.execute_console_command(ed.get_editor_world(),'Slate.bAllowThrottling '+str(old_throttle))
        report['mapsUnchanged'] = maps()==report['mapsBefore']
        report['originalSavesUnchanged'] = saves()==report['savesBefore']
        if not report['mapsUnchanged'] or not report['originalSavesUnchanged']:
            report['errors'].append('Persistence guard failed')
        if report['errors']:
            report['status']='failed'
        write()
    finally:
        if state['handle'] is not None:
            u.unregister_slate_post_tick_callback(state['handle'])
        u.SystemLibrary.quit_editor()


def hit_record(hit):
    if hit is None:
        return None
    if isinstance(hit,tuple):
        records=[v for v in hit if hasattr(v,'to_dict')]
        if records:
            hit=records[0]
        elif all(v is None or v is False for v in hit):
            return None
        else:
            raise RuntimeError('Malformed nonempty trace tuple')
    if not hasattr(hit,'to_dict'):
        raise RuntimeError('Unrecognized trace result; cannot certify geometry')
    d={str(k).lower().replace('_',''):v for k,v in hit.to_dict().items()}
    if not d.get('blockinghit',False):
        return None
    actor=d.get('hitactor') or d.get('actor')
    return {'actor':actor.get_name() if actor else None,
            'impact':xyz(d['impactpoint']) if 'impactpoint' in d else None,
            'normal':xyz(d['impactnormal']) if 'impactnormal' in d else None}


def diagnose_stone_leg(world,actor,body):
    # Scene admission above pins Selected48.v1 and its Aron pivot. Station properties
    # remain legacy50, exactly as in native DecodeScene. No movement is performed.
    start=actor.get_editor_property('doorway_point')
    end=actor.get_editor_property('tending_stone_point')
    start=u.Vector(start.x*.96-248,start.y*.96,start.z*.96)
    end=u.Vector(end.x*.96-248,end.y*.96,end.z*.96)
    steps=max(1,math.ceil(math.dist(xyz(start),xyz(end))/25.0))
    rows=[]
    for index in range(steps+1):
        point=start+(end-start)*(index/steps)
        supports={}
        for label,depth,complex_trace in [('nativeRange',30,False),('diagnosticRange',100,False),('complexGeometryRange',100,True)]:
            supports[label]=hit_record(u.SystemLibrary.line_trace_single(world,point+u.Vector(0,0,depth),point-u.Vector(0,0,depth),u.TraceTypeQuery.TRACE_TYPE_QUERY1,complex_trace,[body,actor],u.DrawDebugTrace.NONE,True))
        floor=supports['nativeRange']
        matches=bool(floor and floor['impact'] and floor['normal'] and abs(floor['impact'][2]-point.z)<=3 and floor['normal'][2]>=.95)
        rows.append({'index':index,'plannedFeet':xyz(point),'floorMatchesNative':matches,**supports})
    return {'from':xyz(start),'to':xyz(end),'samples':rows,'firstMismatch':next((r['index'] for r in rows if not r['floorMatchesNative']),None),'scope':'Read-only line-trace support diagnosis; no Pawn-channel capsule or stair traversal acceptance'}


def tick(dt):
    if state['busy']:
        return
    state['busy']=True
    try:
        world=ed.get_game_world()
        now=time.monotonic()
        if state['stopping']:
            if world and now-state['stopWall']<20:
                return
            if world:
                report['errors'].append('PIE teardown timeout')
            shutdown()
            return
        if now-state['wall']>300:
            finish('failed_wall_watchdog')
            return
        if not world:
            return
        pc=u.GameplayStatics.get_player_controller(world,0)
        if not pc:
            return
        if pc.is_walkthrough_menu_open():
            pc.resume_walkthrough()
            return
        cine=u.MikdashCinematics.get(world)
        if cine and cine.is_playing():
            cine.skip_intro()
            return
        if u.GameplayStatics.is_game_paused(world):
            return
        gt=u.GameplayStatics.get_time_seconds(world)
        if 'service' not in state:
            frames=list(u.GameplayStatics.get_all_actors_of_class(world,u.load_class(None,'/Script/MikdashRuntime.MikdashSceneUnits')))
            if len(frames)!=1:
                raise RuntimeError('Scene frame class must be unique')
            frame=frames[0]
            if str(frame.get_editor_property('scene_revision'))!='Selected48.v1' or int(frame.get_editor_property('descriptor_schema_version'))!=1 or int(frame.get_editor_property('coordinate_revision').value)!=1 or xyz(frame.get_editor_property('fixed_architecture_origin_cm'))!=[-6200,0,0]:
                raise RuntimeError('Candidate frame mismatch')
            services=list(u.GameplayStatics.get_all_actors_of_class(world,u.load_class(None,'/Script/MikdashRuntime.MikdashServiceActor')))
            if len(services)!=1:
                raise RuntimeError('Service class must be unique')
            actor=services[0]
            if actor.get_actor_label()!=LABEL or [str(t) for t in actor.tags]!=['ReleaseKohenServiceSelected48V1']:
                raise RuntimeError('Service ownership mismatch')
            if actor.get_service_scene_frame_adapter_version()!=1 or actor.get_editor_property('service_scenario').name!='ORDINARY_DAY' or actor.get_editor_property('start_on_begin_play'):
                raise RuntimeError('Wrong adapter/scenario/startup setting')
            state['service']=actor
            report['started']=bool(actor.start_service())
            report['startStatus']=actor.get_service_status()
            report['plannedSeconds']=actor.get_planned_loop_seconds()
            report['stationCount']=actor.get_station_count()
            if report['stationCount']!=18 or not math.isfinite(report['plannedSeconds']) or report['plannedSeconds']<=0:
                raise RuntimeError('Expected eighteen stations and finite positive native planned duration')
            if not report['started']:
                raise RuntimeError('Native StartService refused: '+report['startStatus'])
            state['simStart']=gt
        actor=state['service']
        elapsed=gt-state['simStart']
        if elapsed-state['lastSample']>=.5:
            body=actor.get_service_body()
            if not body:
                raise RuntimeError('Service body absent')
            feet=body.get_actor_location()
            ignored=[body,actor]
            floor=hit_record(u.SystemLibrary.line_trace_single(world,feet+u.Vector(0,0,25),feet-u.Vector(0,0,25),u.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignored,u.DrawDebugTrace.NONE,True))
            previous=state.get('previousFeet',feet)
            capsule=hit_record(u.SystemLibrary.capsule_trace_single(world,previous+u.Vector(0,0,98),feet+u.Vector(0,0,98),34.0,96.0,u.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignored,u.DrawDebugTrace.NONE,True))
            row={'seconds':elapsed,'feet':xyz(feet),'active':actor.is_service_active(),
                 'action':actor.get_current_action_text(),'status':actor.get_service_status(),
                 'lamp':actor.get_current_lamp(),'completed':actor.get_completed_sequences(),
                 'blockedLegs':actor.get_blocked_leg_count(),'floor':floor,'capsuleHit':capsule}
            row['floorAgreement']=bool(floor and floor['impact'] and abs(floor['impact'][2]-feet.z)<=3.0)
            report['samples'].append(row)
            state.update(previousFeet=feet,lastSample=elapsed)
            if actor.get_blocked_leg_count()>0 and 'stoneLegDiagnostic' not in report:
                report['stoneLegDiagnostic']=diagnose_stone_leg(world,actor,body)
                write()
                if LEG_DIAGNOSTIC_ONLY:
                    finish('leg_diagnostic_captured_service_still_blocked');return
            if len(report['samples'])%10==0:
                write()
        if elapsed>=90:
            rows=report['samples']
            report['observedSeconds']=elapsed
            report['bodyStatus']=actor.get_body_status()
            report['resolvedMesh']=actor.get_resolved_mesh_path()
            report['completedSequences']=actor.get_completed_sequences()
            report['moved']=any(sum((r['feet'][i]-rows[0]['feet'][i])**2 for i in range(3))>100 for r in rows)
            report['floorMisses']=sum(not r['floorAgreement'] for r in rows)
            report['capsuleHits']=sum(r['capsuleHit'] is not None for r in rows)
            report['nativeBlockedLegs']=actor.get_blocked_leg_count()
            report['unexpectedInactiveSamples']=sum(not r['active'] and r['completed']==0 for r in rows)
            passed=report['moved'] and not report['floorMisses'] and not report['capsuleHits'] and not report['nativeBlockedLegs'] and not report['unexpectedInactiveSamples']
            finish('partial_observation_passed_full_route_pending' if passed else 'partial_observation_findings')
    except Exception as error:
        report['errors'].append(repr(error))
        if state['stopping']:
            shutdown()
        else:
            finish('failed_exception')
    finally:
        state['busy']=False


try:
    inventory()
    if Path(u.Paths.project_dir()).resolve()!=ROOT or ed.get_game_world() or ed.get_editor_world().get_outermost().get_name()!=TARGET:
        raise RuntimeError('Wrong project/map or PIE already active')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError('Dirty packages')
    if 'SlotNamePrefix=AstraProbe_' not in CMD or 'SaveSlot=AstraProbe_' not in CMD:
        raise RuntimeError('Isolated save overrides required')
    settings.set_editor_property('GameGetsMouseControl',False)
    u.SystemLibrary.execute_console_command(ed.get_editor_world(),'Slate.bAllowThrottling 0')
    write()
    state['handle']=u.register_slate_post_tick_callback(tick)
    levels.editor_request_begin_play()
except Exception as error:
    report['errors'].append(repr(error))
    report['status']='failed_setup'
    shutdown()
    raise
