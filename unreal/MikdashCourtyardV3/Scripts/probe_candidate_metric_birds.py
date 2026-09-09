"""Dedicated real-RHI PIE: four metric bird flocks for45 natural simulation seconds.
No teleport, time acceleration, service startup, bridge expectation or map save.
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
from port_candidate_metric_birds import LABELS
from release_birds import _species_enum
TARGET = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
CMD = u.SystemLibrary.get_command_line()
OUT = ROOT/'SourceAssets/birds-review'/('candidate-metric-birds-runtime-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
state = {'wall':time.monotonic(), 'handle':None, 'busy':False, 'stopping':False, 'last':-1}
report = {'status':'starting','errors':[], 'samples':[], 'pid':os.getpid(),
          'scope':'Four metric flocks only; Temple Plaza deferred.45 seconds public counters and actual pose-instance movement. No visual, audio, perch-support or species-realism acceptance.'}


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
def flock_config(a):
    keys=('bird_count','max_birds','flock_enabled','home_point_cm','floor_z_cm','ceiling_z_cm','radius_cm','size_scale')
    return {k:xyz(a.get_editor_property(k)) if k=='home_point_cm' else a.get_editor_property(k) for k in keys}
def flocks(aa):
    cls=u.load_class(None,'/Script/MikdashRuntime.MikdashBirdFlock')
    if cls is None: raise RuntimeError('Bird flock class missing')
    found=[a for a in aa if u.MathLibrary.class_is_child_of(a.get_class(),cls)]
    if len(found)!=4 or {a.get_actor_label() for a in found}!=set(LABELS):
        raise RuntimeError('Require exactly4 metric flocks; no Temple Plaza flock')
    for a in found:
        if a.get_class()!=cls or a.get_editor_property('species')!=_species_enum(u,LABELS[a.get_actor_label()]):
            raise RuntimeError('Flock exact native class/species mismatch')
    return {a.get_actor_label():a for a in found}
def service_off(aa):
    cls=u.load_class(None,'/Script/MikdashRuntime.MikdashServiceActor')
    if cls is None: raise RuntimeError('Service class missing')
    for a in aa:
        if u.MathLibrary.class_is_child_of(a.get_class(),cls):
            if a.get_editor_property('start_on_begin_play') or a.is_service_active():
                raise RuntimeError('Service must remain inactive; probe never starts/stops it')
def finish(status):
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
            if state['handle'] is not None: u.unregister_slate_post_tick_callback(state['handle'])
            u.SystemLibrary.quit_editor()


def observe(a):
    live=a.get_live_bird_count();config=flock_config(a)
    expected=min(max(0,config['bird_count']),max(1,config['max_birds']))
    if not config['flock_enabled'] or live!=expected or not 0<live<=600:
        raise RuntimeError('Live bird count differs from bounded saved count')
    visible={};components=[]
    for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
        count=c.get_instance_count()
        if count!=live: raise RuntimeError('Pose component instance count differs')
        components.append({'name':c.get_name(),'count':count})
        for i in range(count):
            tr=c.get_instance_transform(i,world_space=True)
            if isinstance(tr,tuple): tr=next((v for v in tr if hasattr(v,'translation')),None)
            if tr is None or not hasattr(tr,'translation'): raise RuntimeError('Malformed pose transform')
            scale=xyz(tr.scale3d);point=xyz(tr.translation)
            if not all(math.isfinite(v) for v in scale+point): raise RuntimeError('Nonfinite bird transform')
            if max(abs(v) for v in scale)<=.00001: continue
            if str(i) in visible: raise RuntimeError('Two visible poses for one bird')
            visible[str(i)]=point
    if len(components)!=4: raise RuntimeError('Expected four pose components')
    if len(visible)!=live: raise RuntimeError('Visible pose count differs from live birds')
    perched=a.get_perched_bird_count()
    if not 0<=perched<=live: raise RuntimeError('Perched count outside live count')
    return {'live':live,'perched':perched,'resolvedPerches':a.get_resolved_perch_count(),
            'simulating':a.is_flock_simulating(),'status':a.get_flock_status(),
            'perchStatus':a.get_perch_source_status(),'interval':a.get_current_update_interval_seconds(),
            'averageUpdateMilliseconds':a.get_average_update_milliseconds(),
            'wingPhaseCoherence':a.get_wing_phase_coherence(),
            'components':components,'positions':visible}


def tick(dt):
    if state['busy']: return
    state['busy']=True
    try:
        world=ed.get_game_world();now=time.monotonic()
        if state['stopping']:
            if world and now-state['stopWall']<20: return
            if world: report['errors'].append('PIE teardown timeout')
            shutdown();return
        if now-state['wall']>300: finish('failed_wall_watchdog');return
        if world is None: return
        pc=u.GameplayStatics.get_player_controller(world,0)
        if pc is None: return
        if pc.is_walkthrough_menu_open(): pc.resume_walkthrough();return
        cine=u.MikdashCinematics.get(world)
        if cine and cine.is_playing(): cine.skip_intro();return
        if u.GameplayStatics.is_game_paused(world): return
        gt=u.GameplayStatics.get_time_seconds(world)
        if 'flocks' not in state:
            aa=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
            service_cls=u.load_class(None,'/Script/MikdashRuntime.MikdashServiceActor')
            if service_cls is None: raise RuntimeError('Service class missing')
            state['services']=[a for a in aa if u.MathLibrary.class_is_child_of(a.get_class(),service_cls)]
            service_off(state['services']);frame(aa);found=flocks(aa)
            if {k:flock_config(a) for k,a in found.items()}!=report['savedFlocks']:
                raise RuntimeError('PIE flock properties differ from saved map')
            initial={k:observe(a) for k,a in found.items()}
            state.update(flocks=found,start=gt,initial=initial)
            report['initial']=initial;write()
        service_off(state['services']);elapsed=gt-state['start']
        if elapsed-state['last']>=2:
            row={'seconds':elapsed,'flocks':{}}
            for label,a in state['flocks'].items():
                data=observe(a);initial=state['initial'][label]['positions']
                data['movedBirds']=sum(math.dist(p,initial[k])>1 for k,p in data['positions'].items() if k in initial)
                row['flocks'][label]=data
            report['samples'].append(row);state['last']=elapsed
        if elapsed>=45:
            report['observedSeconds']=elapsed
            report['movementByFlock']={label:max(r['flocks'][label]['movedBirds'] for r in report['samples']) for label in LABELS}
            report['simulationObserved']={label:any(r['flocks'][label]['simulating'] for r in report['samples']) for label in LABELS}
            passed=all(report['movementByFlock'].values()) and all(report['simulationObserved'].values())
            finish('bounded_motion_counts_passed_visual_audio_perches_pending' if passed else 'bounded_observation_findings')
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
    found=flocks(aa);report['savedFlocks']={k:flock_config(a) for k,a in found.items()}
    settings=u.get_default_object(u.load_class(None,'/Script/UnrealEd.LevelEditorPlaySettings'))
    state.update(settings=settings,oldMouse=settings.get_editor_property('GameGetsMouseControl'),
                 oldThrottle=u.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling'))
    settings.set_editor_property('GameGetsMouseControl',False)
    u.SystemLibrary.execute_console_command(ed.get_editor_world(),'Slate.bAllowThrottling 0')
    write();state['handle']=u.register_slate_post_tick_callback(tick);levels.editor_request_begin_play()
except Exception as error:
    report['errors'].append(repr(error));report['status']='failed_setup';shutdown();raise
