"""Bounded continuous CharacterMovement probe: Duchan stairs up and down.
Synthetic input only, no teleport, flying mode, or architectural changes.
Native run required after scene save/reopen. Not physical keyboard acceptance.
"""
import json, math, time
from pathlib import Path
import unreal
root = Path(unreal.Paths.project_dir()).resolve()
if root != Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3'):
    raise RuntimeError('Wrong project')
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor.get_game_world() or unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Stop PIE and save map first')
if editor.get_editor_world().get_path_name().split('.')[0] != '/Game/MikdashV3/Maps/Courtyard':
    raise RuntimeError('Wrong map')
settings = unreal.get_default_object(unreal.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
old_mouse = settings.get_editor_property('GameGetsMouseControl')
old_throttle = unreal.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')
output = root/'SourceAssets/runtime-review/duchan-step55-trial.json'
output.parent.mkdir(parents=True, exist_ok=True)
report = {'status':'running', 'scope':'Synthetic continuous CharacterMovement up/down Duchan transition; no teleport; not physical keyboard or packaged acceptance', 'samples':[], 'reached':[], 'errors':[]}
started = time.monotonic()
handle = None
finished = False
phase = 0
last_sample = 0
last_progress = started
progress_position = None
pawn_path = None

def finish(status):
    global finished
    finished = True
    report['status'] = status
    try:
        levels.editor_request_end_play()
    finally:
        settings.set_editor_property('GameGetsMouseControl', old_mouse)
        unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), 'Slate.bAllowThrottling '+str(old_throttle))
        unreal.unregister_slate_post_tick_callback(handle)
        report['stopRequested'] = True
        output.write_text(json.dumps(report,indent=2),encoding='utf-8')

def tick(delta):
    global phase, last_sample, last_progress, progress_position, pawn_path
    if finished: return
    try:
        now = time.monotonic()
        elapsed = now-started
        if elapsed > 60:
            finish('failed_timeout'); return
        world = editor.get_game_world()
        pawn = unreal.GameplayStatics.get_player_pawn(world,0) if world else None
        if not pawn:
            if elapsed > 15: finish('failed_no_pawn')
            return
        if not isinstance(pawn,unreal.Character): raise RuntimeError('Not a Character')
        if pawn_path is None: pawn_path = pawn.get_path_name()
        if pawn_path != pawn.get_path_name(): raise RuntimeError('Pawn changed')
        pos = pawn.get_actor_location()
        xyz = [float(pos.x),float(pos.y),float(pos.z)]
        if not all(math.isfinite(v) for v in xyz): raise RuntimeError('Nonfinite location')
        if not (1400 < pos.x < 2300 and abs(pos.y) < 200 and 500 < pos.z < 850):
            raise RuntimeError('Route safety envelope exceeded: '+str(xyz))
        movement = pawn.get_component_by_class(unreal.CharacterMovementComponent)
        movement.set_editor_property('max_step_height',55.0)
        mode = movement.get_editor_property('movement_mode')
        if mode not in (unreal.MovementMode.MOVE_WALKING, unreal.MovementMode.MOVE_FALLING):
            raise RuntimeError('Unexpected locomotion mode: '+str(mode))
        if now-last_sample >= .1:
            velocity = pawn.get_velocity()
            report['samples'].append({'seconds':round(elapsed,3),'positionCm':xyz,'velocityCmPerSecond':[velocity.x,velocity.y,velocity.z],'mode':str(mode),'phase':phase,'gameTimeSeconds':unreal.GameplayStatics.get_time_seconds(world),'gamePaused':unreal.GameplayStatics.is_game_paused(world),'pendingInput':str(pawn.get_pending_movement_input_vector()),'lastInput':str(pawn.get_last_movement_input_vector()),'tickDelta':delta})
            last_sample = now
        if unreal.GameplayStatics.get_time_seconds(world) < .05:
            if elapsed > 15: raise RuntimeError('Play world clock never advanced')
            last_progress = now
            return
        if elapsed < 2: return
        target = 1500 if phase == 0 else 2100
        if abs(pos.x-target) < 30 and abs(pos.y) < 40:
            cap = pawn.get_component_by_class(unreal.CapsuleComponent)
            floor = 625 if phase == 0 else 500
            foot = pos.z-cap.get_scaled_capsule_half_height()
            if abs(foot-floor) > 15 or not movement.is_walking():
                raise RuntimeError('Endpoint not supported at expected source floor')
            report['reached'].append({'phase':phase,'positionCm':xyz,'footHeightCm':foot})
            phase += 1
            last_progress = now
            progress_position = xyz
            if phase == 2:
                finish('completed_down_and_up_requires_visual_review'); return
            target = 2100
        if progress_position is None or math.dist(xyz,progress_position) > 20:
            progress_position = xyz
            last_progress = now
        elif now-last_progress > 6:
            raise RuntimeError('No route progress for six seconds')
        dx,dy = target-pos.x,-pos.y
        length = math.hypot(dx,dy)
        pawn.add_movement_input(unreal.Vector(dx/length,dy/length,0),1.0,True)
    except Exception as exc:
        report['errors'].append(str(exc))
        if not finished: finish('failed')

unreal.SystemLibrary.execute_console_command(editor.get_editor_world(), 'Slate.bAllowThrottling 0')
settings.set_editor_property('GameGetsMouseControl',False)
output.write_text(json.dumps(report),encoding='utf-8')
handle = unreal.register_slate_post_tick_callback(tick)
try: levels.editor_request_begin_play()
except Exception:
    finish('failed_start')
    raise


