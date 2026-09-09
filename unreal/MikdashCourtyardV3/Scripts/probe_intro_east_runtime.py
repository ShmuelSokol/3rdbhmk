"""Bounded natural east-intro observation. No teleport, skip, manufactured finish or map writes.

Launch dedicated editor with MIKDASH_INTRO_TARGET=Main50 or Candidate48 on its
matching map and ExecCmds="py <this file>". Both save overrides must use AstraProbe_.
Observe natural playback, up to100simulated seconds/300wall seconds, then autoquit.
Records actual camera and10cm collision/headroom sweeps without moving the camera.
NoCollision gate geometry means no claim of safe passage from clear traces alone.
"""
import hashlib
import json
import os
import struct
import time
from datetime import datetime, timezone
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
MAPS={'Main50':'/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough','Candidate48':'/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'}
TARGET=os.environ.get('MIKDASH_INTRO_TARGET','Main50')
MAP=MAPS[TARGET]
STAMP = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = ROOT / 'SourceAssets/cinematics-review' / ('intro-runtime-' + TARGET + '-' + STAMP + '.json')
CMD = u.SystemLibrary.get_command_line()
CAPTURE_GATES = '-introcapturegates' in CMD.lower()
ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
settings = u.get_default_object(u.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
old_mouse = settings.get_editor_property('GameGetsMouseControl')
old_throttle = u.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def maps():
    return {str(p): sha(p) for p in (ROOT / 'Content').rglob('*.umap')}


def saves():
    roots = [ROOT / 'Saved/SaveGames', Path(os.environ.get('LOCALAPPDATA', 'C:/nonexistent')) / 'MikdashCourtyardV3/Saved/SaveGames']
    return {str(p): sha(p) for folder in roots if folder.exists()
            for p in folder.glob('*.sav') if not p.name.startswith('AstraProbe_')}


report = {'status': 'starting', 'stamp': STAMP, 'samples': [], 'errors': [],
          'mapsBefore': maps(), 'savesBefore': saves(),
          'scope': 'Natural intro camera sampled in PIE;10cm visibility sweeps identify collisions. NoCollision enclosure meshes cannot be cleared by traces: opening/headroom require separate geometry or visual review.'}
state = {'start': time.monotonic(), 'stopping': False, 'busy': False,
         'sample_start': None, 'last_sample': -10.0, 'handle': None}


def write():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


def finish(status):
    report['status'] = status
    state['stopping'] = True
    state['stop_at'] = time.monotonic()
    levels.editor_request_end_play()
    write()


def shutdown():
    try:
        settings.set_editor_property('GameGetsMouseControl', old_mouse)
        u.SystemLibrary.execute_console_command(ed.get_editor_world(), 'Slate.bAllowThrottling ' + str(old_throttle))
        report['mapsUnchanged'] = maps() == report['mapsBefore']
        report['originalSavesUnchanged'] = saves() == report['savesBefore']
        if not report['mapsUnchanged'] or not report['originalSavesUnchanged']:
            report['errors'].append('Persistence guard failed')
        if CAPTURE_GATES:
            shots=report.get('gateScreenshots',[])
            if len(shots)!=2:report['errors'].append('Expected two gate screenshots')
            for shot in shots:
                path=Path(shot['path'])
                if not path.is_file():
                    report['errors'].append('Missing gate screenshot '+str(path));continue
                with path.open('rb') as stream:header=stream.read(24)
                shot['headerValid']=len(header)==24 and header[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',header[16:24])==(1280,720)
                if not shot['headerValid']:report['errors'].append('Invalid gate screenshot header')
                shot['sha256']=sha(path)
        if report['errors']:
            report['status'] = 'failed_' + report['status']
        write()
    finally:
        if state['handle'] is not None:
            u.unregister_slate_post_tick_callback(state['handle'])
        u.SystemLibrary.quit_editor()


def xyz(v): return [float(v.x),float(v.y),float(v.z)]

def trace(world,start,end,ignored):
    hit=u.SystemLibrary.sphere_trace_single(world,start,end,10.0,u.TraceTypeQuery.TRACE_TYPE_QUERY1,
        False,ignored,u.DrawDebugTrace.NONE,True)
    if isinstance(hit,tuple): hit=next((v for v in hit if hasattr(v,'to_dict')),None)
    if hit is None: return None
    d={str(k).lower().replace('_',''):v for k,v in hit.to_dict().items()}
    if not d.get('blockinghit',False): return None
    actor=d.get('hitactor') or d.get('actor')
    return {'actor':actor.get_name() if actor else None,'impactPoint':xyz(d['impactpoint']) if 'impactpoint' in d else None,
            'distance':float(d.get('distance',0))}

def tick(dt):
    if state['busy']: return
    state['busy']=True
    try:
        now=time.monotonic();world=ed.get_game_world()
        if state['stopping']:
            if world and now-state['stop_at']<20:return
            if world:report['errors'].append('PIE teardown timeout')
            shutdown();return
        if now-state['start']>300:finish('failed_wall_watchdog');return
        if not world:return
        pc=u.GameplayStatics.get_player_controller(world,0)
        if not pc:return
        if pc.is_walkthrough_menu_open():pc.resume_walkthrough();return
        cine=u.MikdashCinematics.get(world)
        if not cine:raise RuntimeError('No cinematics subsystem')
        if u.GameplayStatics.is_game_paused(world):return
        gt=u.GameplayStatics.get_time_seconds(world)
        if state['sample_start'] is None:
            state['sample_start']=gt
            descriptors=list(u.GameplayStatics.get_all_actors_of_class(world,u.load_class(None,'/Script/MikdashRuntime.MikdashSceneUnits')))
            report['frames']=[{'sceneRevision':str(a.get_editor_property('scene_revision')),
                'pivot':xyz(a.get_editor_property('fixed_architecture_origin_cm'))} for a in descriptors]
            if TARGET=='Candidate48':
                assert len(descriptors)==1 and report['frames'][0]=={'sceneRevision':'Selected48.v1','pivot':[-6200.0,0.0,0.0]},'Wrong candidate frame'
            report['controlCountInspectionOnly']=len(cine.intro_control_points())
            assert report['controlCountInspectionOnly']==19,'Old binary intro controls'
            report['gateComponents']=[]
            enclosure=u.load_class(None,'/Script/MikdashRuntime.MikdashEnclosure')
            for actor in u.GameplayStatics.get_all_actors_of_class(world,enclosure):
                for c in actor.get_components_by_class(u.InstancedStaticMeshComponent):
                    if 'gate' not in c.get_name().lower():continue
                    transforms=[]
                    for i in range(c.get_instance_count()):
                        tr=c.get_instance_transform(i,world_space=True)
                        if isinstance(tr,tuple):tr=next(v for v in tr if hasattr(v,'translation'))
                        transforms.append({'location':xyz(tr.translation),'scale':xyz(tr.scale3d)})
                    report['gateComponents'].append({'name':c.get_name(),'collision':str(c.get_collision_enabled()),'instances':transforms})
        elapsed=gt-state['sample_start']
        if elapsed>100:finish('failed_simulated_watchdog');return
        playing=cine.is_playing()
        if playing:state['observed_playing']=True
        if elapsed-state['last_sample']>=.1:
            manager=u.GameplayStatics.get_player_camera_manager(world,0)
            if not manager:raise RuntimeError('No player camera manager')
            pos=manager.get_camera_location()
            target=pc.get_view_target();ignored=[v for v in (u.GameplayStatics.get_player_pawn(world,0),target) if v]
            target_name=target.get_name() if target else None
            continuous=playing and state.get('last_playing',False) and target_name==state.get('last_view_target')
            collision=trace(world,state.get('last_position',pos),pos,ignored) if continuous else None
            overhead=trace(world,pos,pos+u.Vector(0,0,100),ignored)
            row={'seconds':elapsed,'introElapsed':cine.get_elapsed_seconds(),'playing':playing,
                'camera':xyz(pos),'viewTarget':target_name,'continuousIntroSegment':continuous,
                'moveIgnored':pc.is_move_input_ignored(),'lookIgnored':pc.is_look_input_ignored(),
                'sweepHit':collision,'headroomHit':overhead}
            report['samples'].append(row);state['last_position']=pos;state['last_sample']=elapsed
            state['last_playing']=playing;state['last_view_target']=target_name
            if CAPTURE_GATES and playing:
                gates=[tr['location'][0] for group in report['gateComponents'] for tr in group['instances']]
                if not gates:raise RuntimeError('No gate geometry for captures')
                east=max(gates)
                shots=report.setdefault('gateScreenshots',[])
                for label,threshold in [('approach',east+2000),('inside',east-1000)]:
                    if pos.x<=threshold and not any(s['label']==label for s in shots):
                        image_path=OUT.parent/('intro-gate-'+TARGET+'-'+STAMP+'-'+label+'.png')
                        if image_path.exists():raise RuntimeError('Capture output already exists')
                        shots.append({'label':label,'path':str(image_path),'camera':xyz(pos),'introElapsed':cine.get_elapsed_seconds(),'visualReview':'pending'})
                        u.SystemLibrary.execute_console_command(world,'HighResShot 1280x720 filename="'+str(image_path)+'"',pc)
                        break
            if len(report['samples'])%30==0:write()
        if state.get('observed_playing') and not playing:
            report['finish']={'hasPlayed':cine.has_played_this_session(),'route':cine.get_playback_route(),
                'refusal':cine.get_last_refusal_reason(),'moveUnlocked':not pc.is_move_input_ignored(),
                'lookUnlocked':not pc.is_look_input_ignored()}
            positions=[r['camera'] for r in report['samples'] if r['playing']]
            playing_samples=[r for r in report['samples'] if r['playing']]
            report['firstObservedIntroSeconds']=playing_samples[0]['introElapsed'] if playing_samples else None
            report['openingObserved']=bool(playing_samples) and report['firstObservedIntroSeconds']<=0.5
            report['observedEastApproach']=bool(positions) and positions[0][0]>100000 and positions[-1][0]<10000
            report['sweepHits']=sum(r['sweepHit'] is not None for r in report['samples'])
            report['headroomHits']=sum(r['headroomHit'] is not None for r in report['samples'])
            passed=report['openingObserved'] and report['observedEastApproach'] and report['finish']['hasPlayed'] and report['finish']['moveUnlocked'] and report['finish']['lookUnlocked']
            if TARGET=='Candidate48':
                passed=passed and report['finish']['route']=='native'
            finish('natural_intro_finished_controls_unlocked_geometry_review_pending' if passed else 'failed_intro_acceptance')
        elif elapsed>12 and not state.get('observed_playing'):
            report['refusal']=cine.get_last_refusal_reason();finish('failed_intro_never_observed')
    except Exception as exc:
        report['errors'].append(repr(exc))
        if state['stopping']:shutdown()
        else:finish('failed_exception')
    finally:state['busy']=False


try:
    assert Path(u.Paths.project_dir()).resolve() == ROOT
    assert ed.get_game_world() is None
    assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    assert ed.get_editor_world().get_outermost().get_name() == MAP
    assert 'SlotNamePrefix=AstraProbe_' in CMD and 'SaveSlot=AstraProbe_' in CMD
    settings.set_editor_property('GameGetsMouseControl', False)
    u.SystemLibrary.execute_console_command(ed.get_editor_world(), 'Slate.bAllowThrottling 0')
    write()
    state['handle'] = u.register_slate_post_tick_callback(tick)
    levels.editor_request_begin_play()
except Exception as exc:
    report['errors'].append(repr(exc))
    report['status'] = 'failed_setup'
    shutdown()
    raise
