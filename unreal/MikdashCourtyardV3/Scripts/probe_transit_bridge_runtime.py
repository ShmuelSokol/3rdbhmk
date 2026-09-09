"""Bounded real-PIE transit bridge observation. No map/save mutations.

Launch a dedicated editor on the main map with ExecCmds="py <this file>" and
both Game ini save overrides starting AstraProbe_. Observes 180 simulated
seconds (600 wall-second watchdog), then ends PIE and closes its own editor.
It does not manufacture exchange events or accelerate the game clock.
"""
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
MAP = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
STAMP = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = ROOT / 'SourceAssets/transit-review/TransitBridge' / ('runtime-' + STAMP + '.json')
CMD = u.SystemLibrary.get_command_line()
CANDIDATE = bool(re.search(r'(?i)(?:^|\s)-Candidate48(?:\s|$)', CMD))
if CANDIDATE:
    MAP = '/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
    OUT = OUT.with_name('candidate48-runtime-' + STAMP + '.json')
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
          'map': MAP, 'candidate48': CANDIDATE,
          'mapsBefore': maps(), 'savesBefore': saves(),
          'scope': 'Observed natural transit events; separate static bridge figures, not skeletal resident transfer. No visual or full-route acceptance.'}
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
        if u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError('Dirty packages during teardown')
    except Exception as exc:
        report['errors'].append('Shutdown failed: ' + repr(exc))
    finally:
        if report['errors']: report['status'] = 'failed_' + report['status']
        try: write()
        finally:
            try:
                if state['handle'] is not None: u.unregister_slate_post_tick_callback(state['handle'])
            finally: u.SystemLibrary.quit_editor()


def candidate_guard(all_actors):
    """Editor and PIE admission; never change refs, focus, service or positions."""
    def unique(class_name):
        cls = u.load_class(None, '/Script/MikdashRuntime.' + class_name)
        if cls is None: raise RuntimeError('Missing guard class ' + class_name)
        found = [a for a in all_actors if u.MathLibrary.class_is_child_of(a.get_class(), cls)]
        if len(found) != 1: raise RuntimeError('Exactly one ' + class_name + ' required')
        actor = found[0]
        if re.sub(r'UEDPIE_\d+_', '', actor.get_outermost().get_name()) != MAP:
            raise RuntimeError('Actor belongs to another map')
        return actor
    descriptor = unique('MikdashSceneUnits')
    pivot = descriptor.get_editor_property('fixed_architecture_origin_cm')
    if descriptor.get_actor_label() != 'RELEASE_SceneUnits_Selected48_V1' or int(descriptor.get_editor_property('descriptor_schema_version')) != 1 or int(descriptor.get_editor_property('coordinate_revision').value) != 1 or str(descriptor.get_editor_property('scene_revision')) != 'Selected48.v1' or [pivot.x,pivot.y,pivot.z] != [-6200,0,0]:
        raise RuntimeError('Selected48 descriptor version/pivot differs')
    bridge = unique('MikdashTransitBoardingBridge')
    if bridge.get_actor_label() != 'RELEASE_TransitBridge_Selected48_V1': raise RuntimeError('Candidate bridge identity differs')
    for prop, name in [('transit','MikdashTransit'),('crowd_field','MikdashCrowdField')]:
        if bridge.get_editor_property(prop) != unique(name): raise RuntimeError('Bridge reference does not point to unique candidate actor')
    focus = bridge.get_editor_property('mount_focus_cm')
    if [focus.x,focus.y,focus.z] != [-248,0,288]: raise RuntimeError('Candidate photographer focus differs')
    service = unique('MikdashServiceActor')
    if service.get_editor_property('start_on_begin_play') or service.is_service_active(): raise RuntimeError('Service must remain OFF')
    coordinator_cls = u.load_class(None, '/Script/MikdashRuntime.MikdashTransitCrowdCoordinator')
    if coordinator_cls is None: raise RuntimeError('Coordinator guard class missing')
    if any(a.get_editor_property('activate_on_begin_play') for a in all_actors if u.MathLibrary.class_is_child_of(a.get_class(),coordinator_cls)):
        raise RuntimeError('Active coordinator duplicates bridge exchanges')
    state['service'] = service
    return bridge


def sample(bridge, seconds):
    names = ['is_bridge_active', 'get_active_group_count', 'get_active_figure_count',
             'get_groups_started', 'get_groups_refused_by_cap', 'get_groups_refused_by_geometry',
             'get_groups_refused_by_stop', 'get_groups_refused_by_pool', 'get_people_boarded',
             'get_people_alighted', 'get_people_trimmed', 'get_photographer_count',
             'get_overrun_count', 'get_ground_trace_miss_count', 'is_crowd_handover_available']
    row = {name: getattr(bridge, name)() for name in names}
    row.update(seconds=round(seconds, 3), summary=bridge.get_bridge_summary(),
               refusedStops=list(bridge.get_refused_stop_indices()))
    assert row['get_active_group_count'] <= bridge.get_editor_property('max_concurrent_groups'), 'Group cap exceeded'
    assert row['get_active_figure_count'] <= bridge.get_editor_property('max_figures'), 'Figure pool exceeded'
    report['samples'].append(row)
    write()
    return row


def tick(dt):
    if state['busy']:
        return
    state['busy'] = True
    try:
        now = time.monotonic()
        world = ed.get_game_world()
        if state['stopping']:
            if world and now - state['stop_at'] < 20:
                return
            if world:
                report['errors'].append('PIE teardown timeout')
            shutdown()
            return
        if now - state['start'] > 600:
            finish('failed_wall_watchdog')
            return
        if not world:
            return
        controller = u.GameplayStatics.get_player_controller(world, 0)
        if not controller:
            return
        if controller.is_walkthrough_menu_open():
            controller.resume_walkthrough()
            return
        cinematic = u.MikdashCinematics.get(world)
        if cinematic and cinematic.is_playing():
            cinematic.skip_intro()
            return
        if u.GameplayStatics.is_game_paused(world):
            return
        game_time = u.GameplayStatics.get_time_seconds(world)
        if state['sample_start'] is None:
            cls = u.load_class(None, '/Script/MikdashRuntime.MikdashTransitBoardingBridge')
            actors = list(u.GameplayStatics.get_all_actors_of_class(world, cls))
            assert len(actors) == 1, 'Exactly one live bridge required'
            state['bridge'] = actors[0]
            if CANDIDATE:
                guarded = candidate_guard(list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor)))
                if guarded != actors[0]: raise RuntimeError('Candidate bridge discovery differs')
            state['sample_start'] = game_time
            report['status'] = 'observing_natural_transit'
        elapsed = game_time - state['sample_start']
        if CANDIDATE and (state['service'].get_editor_property('start_on_begin_play') or state['service'].is_service_active()):
            raise RuntimeError('Service unexpectedly activated')
        if elapsed - state['last_sample'] >= 10 or elapsed >= 180:
            row = sample(state['bridge'], elapsed)
            state['last_sample'] = elapsed
            if elapsed >= 180:
                passed = row['is_bridge_active'] and row['get_people_boarded'] > 0 and row['get_people_alighted'] > 0 and row['get_overrun_count'] == 0
                finish('observed_boarding_and_alighting_caps_passed_visual_pending' if passed else 'incomplete_exchange_or_runtime_failure')
    except Exception as exc:
        report['errors'].append(repr(exc))
        if state['stopping']:
            shutdown()
        else:
            finish('failed_exception')
    finally:
        state['busy'] = False


try:
    assert Path(u.Paths.project_dir()).resolve() == ROOT
    assert ed.get_game_world() is None
    assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    assert ed.get_editor_world().get_outermost().get_name() == MAP
    assert 'SlotNamePrefix=AstraProbe_' in CMD and 'SaveSlot=AstraProbe_' in CMD
    if CANDIDATE:
        sys.path.insert(0,str(ROOT/'Scripts'))
        from release_surface_soft import inventory
        inventory()
        if '-nullrhi' in CMD.lower() or '-run=pythonscript' in CMD.lower(): raise RuntimeError('Dedicated real-RHI PIE required')
        game_overrides = ' '.join(a or b for a,b in re.findall(r'(?i)-ini:Game:(?:"([^"]+)"|(\S+))',CMD))
        for section,key in [('MikdashSaveSystem','SlotNamePrefix'),('MikdashSettingsSubsystem','SaveSlot')]:
            pattern = r'\[/Script/MikdashRuntime\.' + section + r'\]:' + key + r'=(AstraProbe_[A-Za-z0-9_-]+)(?=[,\s"]|$)'
            found = re.findall(pattern,game_overrides)
            if len(found)!=1 or len(re.findall(r'\b'+key+r'=',CMD))!=1:
                raise RuntimeError('Unique full Game save section override required: '+section)
            for folder in (ROOT/'Saved/SaveGames',Path(os.environ.get('LOCALAPPDATA','C:/nonexistent'))/'MikdashCourtyardV3/Saved/SaveGames'):
                if folder.exists() and any(p.stem.startswith(found[0]) for p in folder.glob('*.sav')):
                    raise RuntimeError('Isolated save prefix already exists')
        candidate_guard(list(u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()))
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
