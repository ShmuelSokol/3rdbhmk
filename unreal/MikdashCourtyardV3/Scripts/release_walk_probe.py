"""Bounded PIE walking probe for the combined IntegratedReviewV2 Walkthrough map.

LIVE EDITOR ONLY. This starts Play-In-Editor from editor Python and drives the
player Character with synthetic add_movement_input; it cannot run under
-run=pythonscript / UnrealEditor-Cmd. Established launch mechanism (Atmosphere-
Capture-01 pattern): a dedicated editor started ON the target map with
-ExecCmds="py <this file>" so the editor stays alive while tick callbacks run,
and the script quits the editor itself when MIKDASH_WALK_QUIT_EDITOR=1.
Do NOT use -ExecutePythonScript: it requests editor exit as soon as this file
returns, before the tick callbacks finish (Release-PIE-Floor-01 failure).

Based on the working Courtyard probes (check_east_gate_walk.py and siblings):
Slate.bAllowThrottling 0 while running (restored on exit), GameGetsMouseControl
False (restored), editor_request_begin_play, slate post-tick callback, hard
wall-clock limit, editor_request_end_play, JSON receipt.

Differences from the Courtyard probes:
- Asserts the loaded editor map is the combined map (optionally loads it first
  when the editor is clean; loading is read-only, nothing is saved).
- The combined map uses BP_MikdashRuntimeGameMode + compiled
  AMikdashPlayerController, which opens the welcome menu and PAUSES at
  BeginPlay. The probe calls controller.resume_walkthrough() (a
  BlueprintCallable UFUNCTION) to start the walk. That is the same call the
  Start button makes; it is not physical input acceptance.
- Route 1: east gate down/up, the known-good Courtyard route
  (spawn ~[2100,0,598] -> outer court ~[4974,0,398] -> back).
- Route 2: east from the outer court to the Mount platform deck using the
  route-source-plan 'Platform to measured outer eastern gate' points, which
  are native cm (outer gate threshold Z300 at x7600..8500, twelve Outer E
  stairs, deck top Z0 at x9300..10000). The plan's 'Kotel plaza to Mount
  approach' candidates are NOT walked: they are ~280 m away at Z about -14 to
  -17 m, flagged stairsPending, and the plan says never infer connectivity.
- Samples every 0.25 s; detects stuck (no progress 6 s), teleport (implausible
  displacement between samples), sustained fall, and envelope exit.
- Auto-stops PIE within MIKDASH_WALK_LIMIT_SECONDS (<= 90).

Configuration is by environment variables so the same file works from the
editor Python console, `py` console command, or -ExecCmds:
  MIKDASH_WALK_LIMIT_SECONDS   hard wall-clock limit, 20..90 (default 90)
  MIKDASH_WALK_SAMPLE_SECONDS  sample interval (default 0.25)
  MIKDASH_WALK_PAWN_TIMEOUT    seconds to wait for the PIE pawn (default 45;
                               hidden nullrhi PIE start took 24.2 s)
  MIKDASH_WALK_ROUTES          comma list from: east_gate, mount_platform
                               (default both, in that order)
  MIKDASH_WALK_ALLOW_LOAD_MAP  1 = load the combined map if another clean map
                               is open (default 1)
  MIKDASH_WALK_QUIT_EDITOR     1 = quit the editor after the receipt is written
                               (default 0; only set for a dedicated editor)
Receipt: SourceAssets/IntegratedReviewV2/release-walk-<UTC stamp>.json

Not physical keyboard, mouse-release, rendering or packaged acceptance.
"""
import hashlib
import json
import math
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import unreal

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
TARGET_MAP = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
MAP_FILE = ROOT / 'Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap'
COMMAND=unreal.SystemLibrary.get_command_line()
CANDIDATE48='-candidate48' in COMMAND.lower().split()
if CANDIDATE48:
    TARGET_MAP='/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough'
    MAP_FILE=ROOT/'Content'/(TARGET_MAP[6:]+'.umap')
PLAN_FILE = ROOT / 'SourceAssets/FutureMountV1/route-review/route-source-plan.json'
OUTPUT_DIR = ROOT / 'SourceAssets/IntegratedReviewV2'
PLAN_ROUTE_NAME = 'Platform to measured outer eastern gate'


def _env_float(name, default, low, high):
    try:
        value = float(os.environ.get(name, default))
    except ValueError:
        value = float(default)
    return min(high, max(low, value))


LIMIT_SECONDS = _env_float('MIKDASH_WALK_LIMIT_SECONDS', 90, 20, 90)
SAMPLE_SECONDS = _env_float('MIKDASH_WALK_SAMPLE_SECONDS', 0.25, 0.05, 1.0)
PAWN_TIMEOUT = _env_float('MIKDASH_WALK_PAWN_TIMEOUT', 45, 5, 80)
ROUTE_NAMES = [r.strip() for r in os.environ.get('MIKDASH_WALK_ROUTES', 'east_gate,mount_platform').split(',') if r.strip()]
ALLOW_LOAD_MAP = os.environ.get('MIKDASH_WALK_ALLOW_LOAD_MAP', '1') == '1'
QUIT_EDITOR = os.environ.get('MIKDASH_WALK_QUIT_EDITOR', '0') == '1'
ENDPOINT_XY_TOLERANCE = 30.0   # cm, same as Courtyard probes
FLOOR_TOLERANCE = 15.0         # cm, same as Courtyard probes
STUCK_SECONDS = 6.0            # same as Courtyard probes
PROGRESS_CM = 20.0
FALL_SECONDS = 1.5
MAX_RESUME_CALLS = 3


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def temple_point(x,y,z):
    return (x*.96-248,y*.96,z*.96) if CANDIDATE48 else (x,y,z)


def original_saves():
    folders=[ROOT/'Saved/SaveGames',Path(os.environ.get('LOCALAPPDATA','C:/absent'))/'MikdashCourtyardV3/Saved/SaveGames']
    return {str(p):sha(p) for folder in folders if folder.exists() for p in folder.glob('*.sav') if not p.name.startswith('AstraProbe_')}


all_maps_before={str(p):sha(p) for p in (ROOT/'Content').rglob('*.umap')}
saves_before=original_saves()
if CANDIDATE48:
    for section,key in [('MikdashSaveSystem','SlotNamePrefix'),('MikdashSettingsSubsystem','SaveSlot')]:
        found=re.findall(r'\[/Script/MikdashRuntime\.'+section+r'\]:'+key+r'=(AstraProbe_[A-Za-z0-9_]+)',COMMAND)
        if len(found)!=1: raise RuntimeError('Unique isolated Game override required: '+key)
        for folder in (ROOT/'Saved/SaveGames',Path(os.environ.get('LOCALAPPDATA','C:/absent'))/'MikdashCourtyardV3/Saved/SaveGames'):
            if folder.exists() and any(p.name.startswith(found[0]) for p in folder.glob('*.sav')):
                raise RuntimeError('Require fresh unused probe save prefix')


def validate_frame(actors):
    if not CANDIDATE48: return
    cls=unreal.load_class(None,'/Script/MikdashRuntime.MikdashSceneUnits')
    if cls is None: raise RuntimeError('Scene descriptor class absent')
    ds=[a for a in actors if unreal.MathLibrary.class_is_child_of(a.get_class(),cls)]
    if len(ds)!=1: raise RuntimeError('Exactly one Selected48 descriptor required')
    d=ds[0];pivot=d.get_editor_property('fixed_architecture_origin_cm')
    if str(d.get_editor_property('scene_revision'))!='Selected48.v1' or int(d.get_editor_property('descriptor_schema_version'))!=1 or int(d.get_editor_property('coordinate_revision').value)!=1 or [pivot.x,pivot.y,pivot.z]!=[-6200,0,0]:
        raise RuntimeError('Selected48 frame/pivot/schema mismatch')


def build_routes():
    """Route legs: (label, x, y, expectedFloorZ, checkpoint?). Checkpoints must be reached
    within ENDPOINT_XY_TOLERANCE with foot height within FLOOR_TOLERANCE of the expected
    floor; pass-through points are recorded when passed but never fail the run."""
    routes = {}
    routes['east_gate'] = dict(
        name='east_gate_down_up',
        source='Known-good Courtyard probe check_east_gate_walk.py: spawn x2100 floor 500 -> x5000 floor 300 -> back',
        envelope=dict(x=(1900, 5200), y=(-200, 200), z=(250, 800)),
        legs=[('outer court east of gate stairs', 5000.0, 0.0, 300.0, True),
              ('return to spawn', 2100.0, 0.0, 500.0, True)])
    if CANDIDATE48:
        r=routes['east_gate']
        r['legs']=[(label,*temple_point(x,y,z),checkpoint) for label,x,y,z,checkpoint in r['legs']]
        r['envelope']={axis:tuple(v*.96+(-248 if axis=='x' else 0) for v in limits) for axis,limits in r['envelope'].items()}
        r['source']+=' Selected48 architectural transform once about fixed Aron pivot; physical tolerances unchanged.'
    plan = json.loads(PLAN_FILE.read_text(encoding='utf-8-sig'))
    plan_route = next(r for r in plan['routes'] if r['name'] == PLAN_ROUTE_NAME)
    # Plan order is platform -> gate; walking order is gate -> platform, so reverse.
    points = list(reversed(plan_route['points']))
    assert all(abs(p['expectedFloorCm'][1]) < 1e-6 for p in points), 'plan route expected on y=0'
    assert all(len(p['expectedFloorCm']) == 3 for p in points)
    legs = []
    for p in points:
        x, y, z = p['expectedFloorCm']
        if CANDIDATE48:
            surface=p['sourceSurface']
            if (surface.startswith('SM_0') and '_architecture_Outer_E_stair_' in surface) or surface=='Measured Outer E floor/threshold Z300':
                x,y,z=temple_point(x,y,z)
            elif surface!='Exact deck top Z0':
                raise RuntimeError('Unclassified route surface '+surface)
        checkpoint = not p.get('staticCapsuleAtStepIsDiagnostic', False)  # stairs are pass-through
        legs.append((p['label'], float(x), float(y), float(z), checkpoint))
    xs = [l[1] for l in legs]
    zs = [l[3] for l in legs]
    routes['mount_platform'] = dict(
        name='outer_court_to_mount_platform_deck',
        source='route-source-plan.json route "%s" (native cm), reversed; stairs pass-through' % PLAN_ROUTE_NAME,
        planSourceHashes=plan['sourceHashes'],
        envelope=dict(x=((1568 if CANDIDATE48 else 1900), max(xs) + 300), y=(-200, 200), z=(min(zs) - 150, 800)),
        legs=legs)
    if CANDIDATE48: routes['mount_platform']['source']+=' Temple floor/stairs transform once; metric FutureMount deck coordinates retained. Join continuity is tested, not assumed.'
    return [routes[n] for n in ROUTE_NAMES]


# ---------------------------------------------------------------- preconditions
if Path(unreal.Paths.project_dir()).resolve() != ROOT:
    raise RuntimeError('Wrong project: ' + unreal.Paths.project_dir())
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor.get_game_world():
    raise RuntimeError('PIE already running; stop it first (user PIE preserved)')
if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages() or unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    raise RuntimeError('Dirty map packages present; save or revert first (nothing is auto-saved)')


def current_map():
    return editor.get_editor_world().get_path_name().split('.')[0]


map_loaded_by_probe = False
if current_map() != TARGET_MAP:
    if not ALLOW_LOAD_MAP:
        raise RuntimeError('Wrong map %s; expected %s' % (current_map(), TARGET_MAP))
    if not levels.load_level(TARGET_MAP):
        raise RuntimeError('load_level failed for ' + TARGET_MAP)
    map_loaded_by_probe = True
if current_map() != TARGET_MAP:
    raise RuntimeError('Map assertion failed after load: ' + current_map())
map_sha_before = sha(MAP_FILE)
validate_frame(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())

ROUTES = build_routes()
if not ROUTES:
    raise RuntimeError('No routes selected')

settings = unreal.get_default_object(unreal.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
old_mouse = settings.get_editor_property('GameGetsMouseControl')
old_throttle = unreal.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')

STAMP = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
output = OUTPUT_DIR / ('release-walk-' + ('Candidate48-' if CANDIDATE48 else '') + STAMP + '.json')

report = {
    'status': 'running',
    'scope': 'Synthetic continuous CharacterMovement in bounded PIE on the combined map; '
             'no teleport, no flying, no map save. Not physical keyboard, mouse-release, '
             'rendering or packaged acceptance.',
    'map': TARGET_MAP, 'mapSha256Before': map_sha_before, 'mapLoadedByProbe': map_loaded_by_probe,
    'candidate48':CANDIDATE48,'allMapHashesBefore':all_maps_before,'originalSavesBefore':saves_before,
    'config': dict(limitSeconds=LIMIT_SECONDS, sampleSeconds=SAMPLE_SECONDS, pawnTimeoutSeconds=PAWN_TIMEOUT,
                   routes=ROUTE_NAMES, quitEditor=QUIT_EDITOR, oldThrottle=old_throttle, oldGameGetsMouseControl=old_mouse),
    'routes': [dict(name=r['name'], source=r['source'], envelope=r['envelope'],
                    legs=[dict(label=l[0], targetCm=[l[1], l[2]], expectedFloorCm=l[3], checkpoint=l[4]) for l in r['legs']])
               for r in ROUTES],
    'pawn': None, 'resumeCalls': 0, 'events': [], 'reached': [], 'passThrough': [], 'samples': [], 'errors': [],
}

started = time.monotonic()
state = dict(handle=None, finished=False, route=0, leg=0, last_sample=0.0, last_progress=started,
             progress_position=None, pawn_path=None, seen_world=False, prev=None, falling_since=None,
             walk_started=None, end_requested_at=None)


def write_report():
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')


def event(kind, **data):
    data.update(kind=kind, seconds=round(time.monotonic() - started, 3))
    report['events'].append(data)


def finish(status):
    if state['finished']:
        return
    state['finished'] = True
    report['status'] = status
    report['elapsedSeconds'] = round(time.monotonic() - started, 3)
    for name, action in [
            ('stopPie', levels.editor_request_end_play),
            ('restoreMouseSetting', lambda: settings.set_editor_property('GameGetsMouseControl', old_mouse)),
            ('restoreThrottle', lambda: unreal.SystemLibrary.execute_console_command(
                editor.get_editor_world(), 'Slate.bAllowThrottling ' + str(old_throttle)))]:
        try:
            action()
            report[name] = 'requested' if name == 'stopPie' else 'completed'
        except Exception as exc:
            report['errors'].append(name + ': ' + str(exc))
    try:
        report['mapBytesUnchanged'] = sha(MAP_FILE) == map_sha_before
    except Exception as exc:
        report['errors'].append('mapHash: ' + str(exc))
    report['stopRequested'] = True
    state['end_requested_at'] = time.monotonic()
    if not QUIT_EDITOR and state['handle'] is not None:
        # Dedicated-editor runs keep the callback alive for quit_tick; otherwise
        # release it now so nothing lingers in a user's editor session.
        try:
            unreal.unregister_slate_post_tick_callback(state['handle'])
            report['unregister'] = 'completed'
        except Exception as exc:
            report['errors'].append('unregister: ' + str(exc))
    write_report()
    unreal.log('release_walk_probe: ' + status + ' -> ' + str(output))


def quit_tick(delta):
    # Only used for a dedicated editor: give PIE teardown two seconds, then quit.
    if state['end_requested_at'] is None or time.monotonic() - state['end_requested_at'] < 2.0:
        return
    if editor.get_game_world() is not None and time.monotonic() - state['end_requested_at'] < 10.0:
        return
    try:
        report['pieTeardownConfirmed']=editor.get_game_world() is None
        report['allMapsUnchanged']={str(p):sha(p) for p in (ROOT/'Content').rglob('*.umap')}==all_maps_before
        report['originalSavesUnchanged']=original_saves()==saves_before
        if not report['pieTeardownConfirmed'] or not report['allMapsUnchanged'] or not report['originalSavesUnchanged']:
            report['errors'].append('PIE teardown or map/save preservation failed')
        if report['errors']: report['status']='failed_cleanup_or_verification'
        write_report()
    finally:
        unreal.unregister_slate_post_tick_callback(state['handle'])
        unreal.SystemLibrary.quit_editor()


def current_leg():
    route = ROUTES[state['route']]
    return route, route['legs'][state['leg']]


def advance_leg(pos, foot, now):
    route, leg = current_leg()
    state['leg'] += 1
    state['last_progress'] = now
    state['progress_position'] = [pos.x, pos.y, pos.z]
    if state['leg'] >= len(route['legs']):
        event('route_completed', route=route['name'])
        state['route'] += 1
        state['leg'] = 0
        if state['route'] >= len(ROUTES):
            finish('completed_all_routes_requires_visual_review')
            return True
        event('route_started', route=ROUTES[state['route']]['name'])
    return False


def tick(delta):
    if state['finished']:
        if QUIT_EDITOR:
            quit_tick(delta)
        return
    try:
        now = time.monotonic()
        elapsed = now - started
        if elapsed > LIMIT_SECONDS:
            finish('failed_timeout')
            return
        world = editor.get_game_world()
        if world is None:
            if state['seen_world']:
                finish('failed_pie_ended_externally')
            elif elapsed > PAWN_TIMEOUT:
                finish('failed_no_game_world')
            return
        state['seen_world'] = True
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        if not pawn:
            if elapsed > PAWN_TIMEOUT:
                finish('failed_no_pawn')
            return
        if not isinstance(pawn, unreal.Character):
            raise RuntimeError('Player pawn is not a Character: ' + pawn.get_class().get_name())
        if CANDIDATE48 and state['pawn_path'] is None:
            pc=unreal.GameplayStatics.get_player_controller(world,0)
            if pc and pc.is_walkthrough_menu_open():
                if report['resumeCalls']>=MAX_RESUME_CALLS: raise RuntimeError('Repeated menu admission')
                report['resumeCalls']+=1;pc.resume_walkthrough();return
            cine=unreal.MikdashCinematics.get(world)
            if cine and cine.is_playing(): cine.skip_intro();return
            if unreal.GameplayStatics.is_game_paused(world): return
            validate_frame(unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor))
            start=pawn.get_actor_location()
            if (start-unreal.Vector(1768,0,578.0001907348633)).length()>3:
                raise RuntimeError('Unexpected natural Selected48 start; no teleport allowed')
        if state['pawn_path'] is None:
            state['pawn_path'] = pawn.get_path_name()
            movement = pawn.get_component_by_class(unreal.CharacterMovementComponent)
            capsule = pawn.get_component_by_class(unreal.CapsuleComponent)
            controller = unreal.GameplayStatics.get_player_controller(world, 0)
            report['pawn'] = dict(
                path=state['pawn_path'], pawnClass=pawn.get_class().get_path_name(),
                controllerClass=controller.get_class().get_path_name() if controller else None,
                maxStepHeightCm=movement.get_editor_property('max_step_height'),
                maxWalkSpeedCmPerSecond=movement.get_editor_property('max_walk_speed'),
                capsuleHalfHeightCm=capsule.get_scaled_capsule_half_height(),
                capsuleRadiusCm=capsule.get_scaled_capsule_radius(),
                pieStartSeconds=round(elapsed, 3))
            event('pawn_found', **report['pawn'])
            event('route_started', route=ROUTES[0]['name'])
        elif state['pawn_path'] != pawn.get_path_name():
            raise RuntimeError('Pawn changed during probe')
        controller = unreal.GameplayStatics.get_player_controller(world, 0)
        movement = pawn.get_component_by_class(unreal.CharacterMovementComponent)
        capsule = pawn.get_component_by_class(unreal.CapsuleComponent)
        pos = pawn.get_actor_location()
        xyz = [float(pos.x), float(pos.y), float(pos.z)]
        if not all(math.isfinite(v) for v in xyz):
            raise RuntimeError('Nonfinite location')
        route, leg = current_leg()
        env = route['envelope']
        if not (env['x'][0] < pos.x < env['x'][1] and env['y'][0] < pos.y < env['y'][1] and env['z'][0] < pos.z < env['z'][1]):
            raise RuntimeError('Route safety envelope exceeded (fall/teleport/off-route): ' + str(xyz))
        mode = movement.get_editor_property('movement_mode')
        if mode not in (unreal.MovementMode.MOVE_WALKING, unreal.MovementMode.MOVE_FALLING):
            raise RuntimeError('Unexpected locomotion mode: ' + str(mode))
        paused = unreal.GameplayStatics.is_game_paused(world)
        game_time = unreal.GameplayStatics.get_time_seconds(world)
        menu_open = None
        if controller and hasattr(controller, 'is_walkthrough_menu_open'):
            menu_open = bool(controller.is_walkthrough_menu_open())

        # ---- sampling + teleport/fall detection
        if now - state['last_sample'] >= SAMPLE_SECONDS:
            velocity = pawn.get_velocity()
            sample = dict(seconds=round(elapsed, 3), gameTimeSeconds=game_time, positionCm=xyz,
                          footHeightCm=pos.z - capsule.get_scaled_capsule_half_height(),
                          velocityCmPerSecond=[velocity.x, velocity.y, velocity.z], mode=str(mode),
                          paused=paused, menuOpen=menu_open, route=route['name'], leg=state['leg'],
                          cursorFlag=controller.get_editor_property('show_mouse_cursor') if controller else None)
            prev = state['prev']
            if prev is not None:
                dt = max(1e-3, sample['seconds'] - prev['seconds'])
                horizontal = math.hypot(xyz[0] - prev['positionCm'][0], xyz[1] - prev['positionCm'][1])
                vertical = abs(xyz[2] - prev['positionCm'][2])
                limit = 2.5 * float(report['pawn']['maxWalkSpeedCmPerSecond']) * dt + 50.0
                if horizontal > limit or vertical > 300.0:
                    raise RuntimeError('Teleport-like displacement %.1f/%.1f cm in %.3f s' % (horizontal, vertical, dt))
            report['samples'].append(sample)
            state['prev'] = sample
            state['last_sample'] = now
        if mode == unreal.MovementMode.MOVE_FALLING and not paused:
            if state['falling_since'] is None:
                state['falling_since'] = now
            elif now - state['falling_since'] > FALL_SECONDS:
                raise RuntimeError('Sustained fall > %.1f s at %s' % (FALL_SECONDS, xyz))
        else:
            state['falling_since'] = None

        # ---- the compiled controller opens the menu and pauses at BeginPlay
        if paused or menu_open:
            state['last_progress'] = now
            if controller and hasattr(controller, 'resume_walkthrough'):
                if report['resumeCalls'] >= MAX_RESUME_CALLS:
                    raise RuntimeError('Menu re-opened/paused repeatedly; not resuming again')
                report['resumeCalls'] += 1
                controller.resume_walkthrough()
                event('resume_walkthrough_called', paused=paused, menuOpen=menu_open, count=report['resumeCalls'])
            elif elapsed > PAWN_TIMEOUT:
                raise RuntimeError('Game paused and controller has no resume_walkthrough()')
            return
        if game_time < 0.05:
            if elapsed > PAWN_TIMEOUT:
                raise RuntimeError('Play world clock never advanced')
            state['last_progress'] = now
            return
        if state['walk_started'] is None:
            state['walk_started'] = now
            state['last_progress'] = now
            event('walking_input_begins', gameTimeSeconds=game_time)
        if now - state['walk_started'] < 0.5:
            return  # let the unpause settle before judging progress

        # ---- checkpoints / pass-through
        label, tx, ty, floor, checkpoint = leg
        if abs(pos.x - tx) < ENDPOINT_XY_TOLERANCE and abs(pos.y - ty) < ENDPOINT_XY_TOLERANCE:
            foot = pos.z - capsule.get_scaled_capsule_half_height()
            record = dict(route=route['name'], label=label, positionCm=xyz, footHeightCm=foot,
                          expectedFloorCm=floor, floorErrorCm=foot - floor, walking=bool(movement.is_walking()),
                          seconds=round(elapsed, 3))
            if checkpoint:
                if abs(foot - floor) > FLOOR_TOLERANCE or not movement.is_walking():
                    raise RuntimeError('Checkpoint not supported at expected floor: ' + json.dumps(record))
                report['reached'].append(record)
            else:
                report['passThrough'].append(record)
            if advance_leg(pos, foot, now):
                return
            route, leg = current_leg()
            label, tx, ty, floor, checkpoint = leg

        # ---- stuck detection
        if state['progress_position'] is None or math.dist(xyz, state['progress_position']) > PROGRESS_CM:
            state['progress_position'] = xyz
            state['last_progress'] = now
        elif now - state['last_progress'] > STUCK_SECONDS:
            raise RuntimeError('No route progress for %.0f seconds toward %s at %s' % (STUCK_SECONDS, label, xyz))

        dx, dy = tx - pos.x, ty - pos.y
        length = math.hypot(dx, dy)
        if length > 1e-3:
            pawn.add_movement_input(unreal.Vector(dx / length, dy / length, 0), 1.0, True)
    except Exception as exc:
        report['errors'].append(str(exc))
        if not state['finished']:
            finish('failed')


# ---------------------------------------------------------------- start
unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), 'Slate.bAllowThrottling 0')
settings.set_editor_property('GameGetsMouseControl', False)
write_report()
state['handle'] = unreal.register_slate_post_tick_callback(tick)
try:
    levels.editor_request_begin_play()
except Exception:
    finish('failed_start')
    raise
unreal.log('release_walk_probe started; receipt ' + str(output))
