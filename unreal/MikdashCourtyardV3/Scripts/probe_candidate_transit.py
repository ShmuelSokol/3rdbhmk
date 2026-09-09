"""Dedicated real-RHI PIE: 15 saved transit stops and 60 natural simulation seconds.
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
from release_transit_v3 import TransitJob
TARGET = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
TRACE = ROOT/'SourceAssets/transit-review/TransitV3/release-transit-v3-trace_stops-20260908T220041937338Z.json'
TRACE_SHA = '93f30fa003405070d46de9aefca132fc5ba0a0c299180a9e1a2f48fd2e558d68'
SPEC = ROOT/'Scripts/release_transit_v3.spec.json'
CMD = u.SystemLibrary.get_command_line()
OUT = ROOT/'SourceAssets/transit-review'/('candidate-transit-runtime-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
state = {'wall':time.monotonic(), 'handle':None, 'busy':False, 'stopping':False, 'last':-1}
report = {'status':'starting','errors':[], 'samples':[], 'stopTraces':[], 'pid':os.getpid(),
          'scope':'15 saved stops, centre/four historical wheel locations; 60 seconds sampled rendered vehicle movement only. No full-route, rail dispatch, bridge, visual or continuous collision acceptance.'}


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
def stop_config(a):
    return [{'route':str(r.get_editor_property('id')), 'name':str(s.get_editor_property('name')),
             'position':xyz(s.get_editor_property('world_position'))}
            for r in a.get_editor_property('routes') for s in r.get_editor_property('stops')]
def transit(aa):
    cls=u.load_class(None,'/Script/MikdashRuntime.MikdashTransit')
    if cls is None: raise RuntimeError('Transit class missing')
    found=[a for a in aa if u.MathLibrary.class_is_child_of(a.get_class(),cls)]
    if len(found)!=1 or found[0].get_class()!=cls or found[0].get_actor_label()!='RELEASE_Transit_Selected48_V1':
        raise RuntimeError('Exactly one adopted native candidate Transit required')
    return found[0]
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


class RoadProbe:
    # Only read-only parsing and road/terrain support methods are borrowed. Never
    # construct TransitJob: its coordinator can checkpoint/import/place assets.
    parse_hit=TransitJob.parse_hit
    is_support=TransitJob.is_support
    is_context_terrain=TransitJob.is_context_terrain
    probe_surface=TransitJob.probe_surface
    def __init__(self,spec):
        self.ue=u;self.spec=spec;self.receipt={'traceErrors':[]}
    def trace_down(self,world,start,end):
        hit=u.SystemLibrary.line_trace_single_by_profile(world_context_object=world,
            start=u.Vector(*start),end=u.Vector(*end),profile_name='Pawn',trace_complex=True,
            actors_to_ignore=[],draw_debug_type=u.DrawDebugTrace.NONE,ignore_self=False)
        if hit is None: return None
        parsed=self.parse_hit(hit)
        if parsed: parsed['method']='profile_Pawn'
        if self.receipt['traceErrors']: raise RuntimeError('Road hit parsing error: '+repr(self.receipt['traceErrors']))
        return parsed


def road_checks(world,a):
    spec=state['spec'];probe=RoadProbe(spec);cfg=spec['groundProbes']
    for i,stop in enumerate(report['savedStops']):
        actual=xyz(a.get_stop_location(i))
        if math.dist(actual,stop['position'])>.01 or str(a.get_stop_name(i))!=stop['name'] or str(a.get_stop_route_id(i))!=stop['route']:
            raise RuntimeError('Runtime stop identity/position differs from saved configuration')
        source=state['historical'][(stop['route'],stop['name'])]
        points={'centre':{'xy':actual[:2],'referenceZ':actual[2]}}
        for key,item in source['probes'].items():
            if not item.get('hit'): raise RuntimeError('Historical accepted wheel has no hit')
            points[key]={'xy':item['xy'],'referenceZ':item['hit']['pointCm'][2]}
        row={'index':i,**stop,'runtimePosition':actual,'probes':{}}
        for key,item in points.items():
            x,y=item['xy'];ref=item['referenceZ']
            fields,z,reason=probe.probe_surface(world,x,y,ref+cfg['traceAboveOfflineZCm'],ref-cfg['traceBelowOfflineZCm'])
            # Require the actual mesh identity; do not accept the legacy label fallback.
            mesh=fields.get('hit',{}).get('mesh') if fields.get('hit') else None
            known_mesh=bool(mesh and any(mesh.startswith(p) for p in cfg['supportMeshPrefixes']))
            passed=bool(reason is None and known_mesh and z is not None and math.isfinite(z) and abs(z-ref)<=cfg['offlineAgreementToleranceCm'])
            row['probes'][key]={'xy':[x,y],'referenceZ':ref,'actualZ':z,'reason':reason,'passed':passed,**fields}
        row['passed']=all(p['passed'] for p in row['probes'].values())
        report['stopTraces'].append(row)
    report['roadTraceMethod']='profile_Pawn, complex=True; existing60cm context-terrain intrusion rule, exact Streets mesh support'
    report['roadSupportPassed']=len(report['stopTraces'])==15 and all(s['passed'] for s in report['stopTraces'])


def positions(a):
    result={}
    for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
        # Body paint only: omit duplicate glass/dark groups and sliding door leaves.
        if not c.get_name().endswith('_Paint'): continue
        for i in range(c.get_instance_count()):
            tr=c.get_instance_transform(i,world_space=True)
            if isinstance(tr,tuple): tr=next((v for v in tr if hasattr(v,'translation')),None)
            if tr is None or not hasattr(tr,'translation'): raise RuntimeError('Malformed instance transform')
            point=xyz(tr.translation)
            if not all(math.isfinite(v) for v in point): raise RuntimeError('Non-finite vehicle position')
            result[c.get_name()+':'+str(i)]=point
    if not result: raise RuntimeError('No actual vehicle paint instances')
    return result


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
        if 'actor' not in state:
            aa=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
            service_cls=u.load_class(None,'/Script/MikdashRuntime.MikdashServiceActor')
            if service_cls is None: raise RuntimeError('Service class missing')
            state['services']=[a for a in aa if u.MathLibrary.class_is_child_of(a.get_class(),service_cls)]
            service_off(state['services'])
            frame(aa);a=transit(aa)
            if not a.is_transit_active() or a.get_stop_count()!=15 or stop_config(a)!=report['savedStops']:
                raise RuntimeError('Transit did not start with15 saved stops')
            road_checks(world,a)
            state.update(actor=a,start=gt,initial=positions(a))
            report['initialPositions']=state['initial'];write()
        service_off(state['services'])
        a=state['actor'];elapsed=gt-state['start']
        if elapsed-state['last']>=2:
            current=positions(a)
            moved={k:math.dist(p,state['initial'][k]) for k,p in current.items() if k in state['initial'] and math.dist(p,state['initial'][k])>10}
            report['samples'].append({'seconds':elapsed,'transitSeconds':a.get_transit_seconds(),
                'active':a.is_transit_active(),'paused':a.is_transit_paused(),'roadVehicles':a.get_road_vehicle_count(),
                'activeTrains':a.get_active_train_count(),'framesPerSweep':a.get_frames_per_sweep(),
                'status':a.get_transit_status(),'movedInstances':len(moved),'positions':current})
            state['last']=elapsed
        if elapsed>=60:
            rows=report['samples']
            report['movedInstancesMax']=max(r['movedInstances'] for r in rows)
            report['observedSeconds']=elapsed
            valid=report['roadSupportPassed'] and report['movedInstancesMax']>0 and all(r['active'] and not r['paused'] and r['roadVehicles']>0 for r in rows) and rows[-1]['transitSeconds']>rows[0]['transitSeconds']
            finish('bounded_observation_passed_full_routes_pending' if valid else 'bounded_observation_findings')
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
    if sha(TRACE)!=TRACE_SHA: raise RuntimeError('Historical road receipt changed')
    historical=json.loads(TRACE.read_text(encoding='utf-8-sig'))
    spec=json.loads(SPEC.read_text(encoding='utf-8-sig'))
    if historical['traceStatus']!='traced_ok' or historical['trace']['method']!='profile_Pawn' or historical['specSha256']!=sha(SPEC): raise RuntimeError('Historical receipt/spec mismatch')
    state['spec']=spec
    state['historical']={(r['route'],r['name']):r for r in historical['stops'] if r['accepted']}
    aa=list(actors.get_all_level_actors());frame(aa);service_off(aa);a=transit(aa)
    report['savedStops']=stop_config(a)
    if len(report['savedStops'])!=15 or len(state['historical'])!=15 or {(s['route'],s['name']) for s in report['savedStops']}!=set(state['historical']): raise RuntimeError('15 saved/historical stop identities required')
    for stop in report['savedStops']:
        historical_stop=state['historical'][(stop['route'],stop['name'])]
        if stop['position']!=historical_stop['worldCm'] or set(historical_stop['probes'])!={'fl','fr','rl','rr'}:
            raise RuntimeError('Saved stop coordinates or historical wheel-key contract differs')
    report.update(traceReceipt=str(TRACE),traceSha256=TRACE_SHA,specSha256=sha(SPEC))
    settings=u.get_default_object(u.load_class(None,'/Script/UnrealEd.LevelEditorPlaySettings'))
    state.update(settings=settings,oldMouse=settings.get_editor_property('GameGetsMouseControl'),
                 oldThrottle=u.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling'))
    settings.set_editor_property('GameGetsMouseControl',False)
    u.SystemLibrary.execute_console_command(ed.get_editor_world(),'Slate.bAllowThrottling 0')
    write();state['handle']=u.register_slate_post_tick_callback(tick);levels.editor_request_begin_play()
except Exception as error:
    report['errors'].append(repr(error));report['status']='failed_setup';shutdown();raise
