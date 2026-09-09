"""90 simulated seconds of actual Candidate48 service; 300-second wall watchdog.
Optional -ServiceFullRoute stops at one natural completion (600sim/900wall limit).
-ServiceMotorPauseProbe checks two simulated seconds of service-only pause.
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
FULL_ROUTE = '-servicefullroute' in CMD.lower()
PAUSE_PROBE = '-servicemotorpauseprobe' in CMD.lower()
SIM_LIMIT = 600 if FULL_ROUTE else 90
WALL_LIMIT = 900 if FULL_ROUTE else 300
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
          'coverage':'One natural completed sequence, bounded at 600 simulated seconds' if FULL_ROUTE else '90 seconds only; not full eighteen-station or visual acceptance',
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
        actual = supports['complexGeometryRange']
        if actual and actual['impact'] and actual['normal'] and actual['normal'][2] >= .95:
            center = u.Vector(*actual['impact']) + u.Vector(0,0,98)
            supports['groundedPawnProfileCapsule'] = hit_record(u.SystemLibrary.capsule_trace_single_by_profile(
                world_context_object=world,start=center+u.Vector(0,0,.1),end=center,
                radius=34.0,half_height=96.0,profile_name='Pawn',trace_complex=False,
                actors_to_ignore=[body,actor],draw_debug_type=u.DrawDebugTrace.NONE,ignore_self=True))
            supports['groundedPawnProfileCapsuleTested'] = True
        else:
            supports['groundedPawnProfileCapsuleTested'] = False
        floor=supports['nativeRange']
        matches=bool(floor and floor['impact'] and floor['normal'] and abs(floor['impact'][2]-point.z)<=3 and floor['normal'][2]>=.95)
        rows.append({'index':index,'plannedFeet':xyz(point),'floorMatchesNative':matches,**supports})
    # Authored stance proposals only; never move the figure or rewrite its anchors.
    manifest_path = ROOT/'SourceAssets/vessels-review/MenorahV4/geometry-manifest.json'
    placement_path = ROOT/'Scripts/release_import_menorah_v4.spec.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    placement = json.loads(placement_path.read_text(encoding='utf-8-sig'))['placement']
    stone = manifest['parameters']['stone']
    part = next(m for m in manifest['meshes'] if m['name']=='SM_MenorahV4_StepStone')
    if stone['steps'] != 3 or placement['yaw'] != -90.0:
        raise RuntimeError('Unsupported top-tread proposal source geometry')
    origin = placement['fixedOrigin']
    local_y = part['bounds_cm']['min'][1] + stone['tread']/2
    proposal = u.Vector((origin[0]+local_y)*.96-248,origin[1]*.96,(origin[2]+stone['steps']*stone['rise'])*.96)
    proposals = []
    for offset in (-20.0,0.0,20.0):
        point = proposal + u.Vector(0,offset,0)
        floor = hit_record(u.SystemLibrary.line_trace_single(world,point+u.Vector(0,0,30),point-u.Vector(0,0,30),u.TraceTypeQuery.TRACE_TYPE_QUERY1,False,[body,actor],u.DrawDebugTrace.NONE,True))
        center = point+u.Vector(0,0,98)
        capsule = hit_record(u.SystemLibrary.capsule_trace_single_by_profile(
            world_context_object=world,start=center+u.Vector(0,0,.1),end=center,
            radius=34.0,half_height=96.0,profile_name='Pawn',trace_complex=False,
            actors_to_ignore=[body,actor],draw_debug_type=u.DrawDebugTrace.NONE,ignore_self=True))
        proposals.append({'proposedFeet':xyz(point),'floor':floor,'pawnProfileCapsule':capsule,
                          'floorAgreement':bool(floor and floor['impact'] and floor['normal'] and abs(floor['impact'][2]-point.z)<=3 and floor['normal'][2]>=.95)})
    return {'from':xyz(start),'to':xyz(end),'samples':rows,'firstMismatch':next((r['index'] for r in rows if not r['floorMatchesNative']),None),
            'topTreadProposals':proposals,'proposalSourceHashes':{str(manifest_path):sha(manifest_path),str(placement_path):sha(placement_path)},
            'scope':'Read-only support traces and stationary physical capsule samples using Pawn profile; top-tread points are authored proposals, no anchor edits or continuous step traversal acceptance'}


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
        if now-state['wall']>WALL_LIMIT:
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
            report['groundedMode']=bool(actor.get_editor_property('use_grounded_movement')) if hasattr(actor,'get_service_grounded_adapter_version') else False
            if report['stationCount']!=18 or not math.isfinite(report['plannedSeconds']) or report['plannedSeconds']<=0:
                raise RuntimeError('Expected eighteen stations and finite positive native planned duration')
            if not report['started']:
                raise RuntimeError('Native StartService refused: '+report['startStatus'])
            state['simStart']=gt
        actor=state['service']
        elapsed=gt-state['simStart']
        if PAUSE_PROBE and report.get('groundedMode') and not state.get('pauseDone'):
            if 'pauseAt' not in state and elapsed>12 and actor.get_service_current_station_index()==2:
                state.update(pauseAt=gt,pauseFeet=xyz(actor.get_service_feet_location()),pauseMaxDrift=0.0)
                actor.set_service_paused(True)
            elif 'pauseAt' in state:
                state['pauseMaxDrift']=max(state['pauseMaxDrift'],math.dist(state['pauseFeet'],xyz(actor.get_service_feet_location())))
                if gt-state['pauseAt']>=2.0:
                    actor.set_service_paused(False)
                    report['motorPause']={'seconds':gt-state['pauseAt'],'maximumFeetDriftCm':state['pauseMaxDrift'],'passed':state['pauseMaxDrift']<.01}
                    state['pauseDone']=True
        if elapsed-state['lastSample']>=.5:
            body=actor.get_service_body()
            if not body:
                raise RuntimeError('Service body absent')
            # Character actor location is capsule centre; the adapter exposes
            # the physical visual-foot frame and preserves the legacy body frame.
            feet=actor.get_service_feet_location() if hasattr(actor,'get_service_feet_location') else body.get_actor_location()
            ignored=[body,actor]
            floor=hit_record(u.SystemLibrary.line_trace_single(world,feet+u.Vector(0,0,25),feet-u.Vector(0,0,25),u.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignored,u.DrawDebugTrace.NONE,True))
            previous=state.get('previousFeet',feet)
            capsule=hit_record(u.SystemLibrary.capsule_trace_single(world,previous+u.Vector(0,0,98),feet+u.Vector(0,0,98),34.0,96.0,u.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignored,u.DrawDebugTrace.NONE,True))
            row={'seconds':elapsed,'feet':xyz(feet),'active':actor.is_service_active(),
                 'action':actor.get_current_action_text(),'status':actor.get_service_status(),
                 'lamp':actor.get_current_lamp(),'completed':actor.get_completed_sequences(),
                 'blockedLegs':actor.get_blocked_leg_count(),'floor':floor,'capsuleHit':capsule}
            if report.get('groundedMode'):
                center=feet+u.Vector(0,0,98)
                row['endpointPawnCapsule']=hit_record(u.SystemLibrary.capsule_trace_single_by_profile(
                    world_context_object=world,start=center+u.Vector(0,0,.1),end=center,radius=34.0,half_height=96.0,
                    profile_name='Pawn',trace_complex=False,actors_to_ignore=ignored,draw_debug_type=u.DrawDebugTrace.NONE,ignore_self=True))
                row['stationIndex']=actor.get_service_current_station_index()
                row['stationTarget']=xyz(actor.get_service_station_location(row['stationIndex']))
                row['nativeGrounded']=actor.is_service_grounded()
                row['probePaused']=bool(PAUSE_PROBE and 'pauseAt' in state and not state.get('pauseDone'))
                report['bodyClass']=body.get_class().get_name()
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
        if elapsed>=SIM_LIMIT or (FULL_ROUTE and actor.get_completed_sequences()>0):
            rows=report['samples']
            report['observedSeconds']=elapsed
            report['bodyStatus']=actor.get_body_status()
            report['resolvedMesh']=actor.get_resolved_mesh_path()
            report['completedSequences']=actor.get_completed_sequences()
            report['moved']=any(sum((r['feet'][i]-rows[0]['feet'][i])**2 for i in range(3))>100 for r in rows)
            report['floorMisses']=sum(not r['floorAgreement'] for r in rows)
            report['capsuleHits']=sum(r['capsuleHit'] is not None for r in rows)
            report['endpointPawnCapsuleHits']=sum(r.get('endpointPawnCapsule') is not None for r in rows)
            report['nonGroundedSamplesOutsideProbePause']=sum(r.get('nativeGrounded') is False and not r.get('probePaused',False) for r in rows)
            report['floorNormalMisses']=sum(not r['floor'] or not r['floor']['normal'] or r['floor']['normal'][2]<.95 for r in rows)
            report['groundingScope']='Native grounded state logged separately; transient descent can be airborne and requires review, not an automatic continuous-grounding claim.'
            report['nativeBlockedLegs']=actor.get_blocked_leg_count()
            report['unexpectedInactiveSamples']=sum(not r['active'] and r['completed']==0 for r in rows)
            collision_hits=report['endpointPawnCapsuleHits'] if report.get('groundedMode') else report['capsuleHits']
            report['capsuleObservationScope']='Endpoint Pawn-profile samples; coarse Visibility chords can intersect a curved StepUp path and are not actual motor sweeps' if report.get('groundedMode') else 'Coarse Visibility chords supplement legacy native Pawn sweeps'
            pause_ok=not PAUSE_PROBE or report.get('motorPause',{}).get('passed',False)
            passed=report['moved'] and not report['floorMisses'] and not collision_hits and not report['nativeBlockedLegs'] and not report['unexpectedInactiveSamples'] and pause_ok
            if FULL_ROUTE:
                finish('natural_sequence_completed_sampled_checks_passed' if passed and report['completedSequences']>0 else 'full_route_findings_or_timeout')
            else:
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
