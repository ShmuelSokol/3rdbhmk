"""Dedicated real-RHI PIE: enclosure actor collision restoration and protected Kotel.
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

TARGET = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
CMD = u.SystemLibrary.get_command_line()
OUT = ROOT/'SourceAssets/enclosure-review'/('candidate-collision-restore-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
ed = u.get_editor_subsystem(u.UnrealEditorSubsystem)
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
state = {'wall':time.monotonic(), 'handle':None, 'busy':False, 'stopping':False, 'last':-1}
report = {'status':'starting','errors':[], 'samples':[], 'pid':os.getpid(),
          'scope':'Real PIE state roundtrip and explicit RestoreAllModernBuildings; actor collision only, no component edits. A temporary false fixture is restored before exit. No geometry or route acceptance.'}


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
def service_off(aa):
    cls=u.load_class(None,'/Script/MikdashRuntime.MikdashServiceActor')
    if cls is None: raise RuntimeError('Service class missing')
    for a in aa:
        if u.MathLibrary.class_is_child_of(a.get_class(),cls):
            if a.get_editor_property('start_on_begin_play') or a.is_service_active():
                raise RuntimeError('Service must remain inactive; probe never starts/stops it')
def finish(status):
    try: restore_fixture()
    except Exception as error:
        report['errors'].append('Fixture restoration failed: '+repr(error))
        status='failed_fixture_restoration'
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


BLOCKER='/Game/MikdashV3/JerusalemContext/OldCityFacadesV1/Meshes/SM_OldCityInfill_Grid_N002_P001'
KOTEL='/Game/MikdashV3/JerusalemContext/Buildings/SM_JerusalemBuildings_Grid_N002_P001'

def restore_fixture():
    fixture=state.get('fixture')
    if fixture is not None and not state.get('fixtureRestored'):
        state['enclosure'].restore_all_modern_buildings()
        fixture.set_actor_enable_collision(state['fixtureOriginal'])
        if fixture.get_actor_enable_collision()!=state['fixtureOriginal']:
            raise RuntimeError('Could not restore original fixture collision')
        state['fixtureRestored']=True
        report['fixtureRestored']=True

def component_snapshot(a):
    # GetCollisionEnabled() is effective/owner-aware and correctly becomes NoCollision
    # when the actor is disabled. Compare the reflected raw configuration instead.
    return {c.get_name():{'profile':str(c.get_collision_profile_name()),
                        'configuredEnabled':str(c.get_editor_property('body_instance').get_editor_property('collision_enabled')),
                        'stepUp':str(c.get_editor_property('can_character_step_up_on'))}
            for c in a.get_components_by_class(u.PrimitiveComponent)}

def actor_state(a):
    return {'hidden':bool(a.get_editor_property('hidden')),'collision':a.get_actor_enable_collision(),'components':component_snapshot(a)}

def exact_mesh_actor(aa,path):
    found=[a for a in aa if any(c.get_editor_property('static_mesh') and c.get_editor_property('static_mesh').get_path_name().split('.')[0]==path
                              for c in a.get_components_by_class(u.StaticMeshComponent))]
    if len(found)!=1:raise RuntimeError('Exact mesh actor count differs: '+path)
    return found[0]

def verify_state(hard):
    rows={};baseline=state['baseline']
    for a in state['selected']:
        name=a.get_name();current=actor_state(a);old=baseline[name]
        original=state['fixtureOriginal'] if a==state.get('fixture') else old['collision']
        expected_collision=False if a==state.get('fixture') else original
        if hard and a!=state['kotel']:expected_collision=False
        expected_hidden=True if hard else old['hidden']
        passed=current['hidden']==expected_hidden and current['collision']==expected_collision and current['components']==old['components']
        rows[name]={'hidden':current['hidden'],'collision':current['collision'],'passed':passed}
        if not passed:raise RuntimeError('State restoration mismatch '+name+' '+repr(current))
    report['states'].append({'phase':state['phase'],'hardHidden':hard,'actors':rows,'passed':True})

def tick(dt):
    if state['busy']:return
    state['busy']=True
    try:
        world=ed.get_game_world();now=time.monotonic()
        if state['stopping']:
            if world and now-state['stopWall']<20:return
            if world:report['errors'].append('PIE teardown timeout')
            shutdown();return
        if now-state['wall']>180:finish('failed_wall_watchdog');return
        if not world:return
        pc=u.GameplayStatics.get_player_controller(world,0)
        if not pc:return
        if pc.is_walkthrough_menu_open():pc.resume_walkthrough();return
        cine=u.MikdashCinematics.get(world)
        if cine and cine.is_playing():cine.skip_intro();return
        if u.GameplayStatics.is_game_paused(world):return
        gt=u.GameplayStatics.get_time_seconds(world)
        if 'enclosure' not in state:
            aa=list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor));frame(aa)
            service_cls=u.load_class(None,'/Script/MikdashRuntime.MikdashServiceActor')
            if service_cls is None:raise RuntimeError('Service class absent')
            state['services']=[a for a in aa if u.MathLibrary.class_is_child_of(a.get_class(),service_cls)];service_off(state['services'])
            cls=u.load_class(None,'/Script/MikdashRuntime.MikdashEnclosure')
            if cls is None:raise RuntimeError('Enclosure class absent')
            found=[a for a in aa if u.MathLibrary.class_is_child_of(a.get_class(),cls)]
            if len(found)!=1:raise RuntimeError('Exactly one enclosure required')
            state['enclosure']=found[0]
            state['blocker']=exact_mesh_actor(aa,BLOCKER);state['kotel']=exact_mesh_actor(aa,KOTEL)
            state['initialHidden']={a.get_name():a for a in aa if bool(a.get_editor_property('hidden')) and a.get_components_by_class(u.StaticMeshComponent)}
            state['enclosure'].set_precinct_state_over(u.MikdashPrecinctState.MODERN,0.0)
            state.update(phase='baseline_modern',at=gt);return
        service_off(state['services'])
        if gt-state['at']<2:return
        e=state['enclosure'];phase=state['phase']
        if phase=='baseline_modern':
            selected=[a for a in state['initialHidden'].values() if not bool(a.get_editor_property('hidden'))]
            if state['blocker'] not in selected or state['kotel'] not in selected:raise RuntimeError('Expected blocker/Kotel were not selected by original state')
            state['selected']=selected;state['baseline']={a.get_name():actor_state(a) for a in selected}
            if not state['blocker'].get_actor_enable_collision():raise RuntimeError('Known blocker did not restore original true collision')
            fixtures=[a for a in selected if a not in (state['blocker'],state['kotel']) and a.get_actor_enable_collision()]
            if not fixtures:raise RuntimeError('No selected nonprotected true-collision fixture')
            fixture=fixtures[0];state.update(fixture=fixture,fixtureOriginal=fixture.get_actor_enable_collision())
            fixture.set_actor_enable_collision(False)
            if fixture.get_actor_enable_collision():raise RuntimeError('PIE false fixture refused')
            report['fixture']={'actor':fixture.get_name(),'originalCollision':state['fixtureOriginal'],'temporaryCollision':False}
            report['baseline']=state['baseline'];report['states']=[]
            e.set_precinct_state_over(u.MikdashPrecinctState.YECHEZKEL,0.0);state.update(phase='hard_hidden',at=gt)
        elif phase=='hard_hidden':
            verify_state(True);e.set_precinct_state_over(u.MikdashPrecinctState.MODERN,0.0);state.update(phase='restored_modern',at=gt)
        elif phase=='restored_modern':
            verify_state(False);e.set_precinct_state_over(u.MikdashPrecinctState.OVERLAY,0.0);state.update(phase='restored_overlay',at=gt)
        elif phase=='restored_overlay':
            verify_state(False);e.set_precinct_state_over(u.MikdashPrecinctState.YECHEZKEL,0.0);state.update(phase='second_hard_hidden',at=gt)
        elif phase=='second_hard_hidden':
            verify_state(True);e.restore_all_modern_buildings();state.update(phase='explicit_restore',at=gt)
        elif phase=='explicit_restore':
            verify_state(False);restore_fixture()
            if actor_state(state['fixture'])!=state['baseline'][state['fixture'].get_name()]:raise RuntimeError('Fixture not fully restored')
            report['selectedActorsChecked']=len(state['selected'])
            finish('state_roundtrip_and_false_fixture_restoration_passed')
        write()
    except Exception as error:
        report['errors'].append(repr(error))
        if state['stopping']:shutdown()
        else:finish('failed_exception')
    finally:state['busy']=False

try:
    report.update(mapsBefore=maps(),savesBefore=saves());inventory();clean()
    world=ed.get_editor_world()
    if Path(u.Paths.project_dir()).resolve()!=ROOT or world is None or world.get_outermost().get_name()!=TARGET or ed.get_game_world():raise RuntimeError('Wrong project/map or existing PIE')
    if '-nullrhi' in CMD.lower() or '-run=pythonscript' in CMD.lower():raise RuntimeError('Dedicated real-RHI PIE required')
    for key in ('SlotNamePrefix','SaveSlot'):
        found=re.findall(r'\b'+key+r'=(AstraProbe_[A-Za-z0-9_-]+)',CMD)
        if len(found)!=1 or len(re.findall(r'\b'+key+r'=',CMD))!=1:raise RuntimeError('One unique AstraProbe override required')
        if any(p.stem.startswith(found[0]) for root in save_roots() if root.exists() for p in root.glob('*.sav')):raise RuntimeError('Probe save exists')
    aa=list(actors.get_all_level_actors());frame(aa);service_off(aa)
    settings=u.get_default_object(u.load_class(None,'/Script/UnrealEd.LevelEditorPlaySettings'))
    state.update(settings=settings,oldMouse=settings.get_editor_property('GameGetsMouseControl'),oldThrottle=u.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling'))
    settings.set_editor_property('GameGetsMouseControl',False);u.SystemLibrary.execute_console_command(world,'Slate.bAllowThrottling 0')
    write();state['handle']=u.register_slate_post_tick_callback(tick);levels.editor_request_begin_play()
except Exception as error:
    report['errors'].append(repr(error));report['status']='failed_setup';shutdown();raise
