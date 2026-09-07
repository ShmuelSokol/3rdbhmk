"""Passive bounded PIE observation. Explicit start() only; never injects input.
Native execution is reserved for the main coordinator. No packaged Python claim.
"""
import json
import math
import time
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
ACTIVE = None


def start(seconds=90):
    import unreal
    global ACTIVE
    if ACTIVE is not None:
        raise RuntimeError('Observer already active')
    if not 5 <= seconds <= 90:
        raise ValueError('Duration must be 5..90 seconds')
    if Path(unreal.Paths.project_dir()).resolve() != ROOT:
        raise RuntimeError('Wrong project')
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = editor.get_editor_world()
    if editor.get_game_world() or unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError('Requires stopped PIE and clean saved map')
    if world.get_path_name().split('.')[0] != '/Game/MikdashV3/Maps/Courtyard':
        raise RuntimeError('Requires saved production Courtyard')
    settings = unreal.get_default_object(unreal.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
    old_mouse = settings.get_editor_property('GameGetsMouseControl')
    old_throttle = unreal.SystemLibrary.get_console_variable_int_value('Slate.bAllowThrottling')
    stamp = str(time.time_ns())
    output = ROOT / 'SourceAssets/runtime-review/control-audit' / ('native-observation-' + stamp + '.json')
    report = {'status': 'running', 'evidence': 'Passive PIE telemetry; operator physical-input attestation required',
              'controllerMethodsInvoked': False, 'inputInjected': False, 'samples': [], 'errors': [],
              'limits': ['Cursor flag does not establish desktop mouse release', 'No packaged acceptance',
                         'Slate/UI may consume keys before controller polling', 'No automatic physical-input pass'],
              'durationLimitSeconds': seconds}
    started = time.monotonic()
    state = {'handle': None, 'done': False, 'last': -1.0, 'seen': False}
    ACTIVE = state

    def finish(status):
        global ACTIVE
        if state['done']:
            return
        state['done'] = True
        report['status'] = status
        for name, action in [
            ('stopPie', levels.editor_request_end_play),
            ('restoreMouseSetting', lambda: settings.set_editor_property('GameGetsMouseControl', old_mouse)),
            ('restoreThrottle', lambda: unreal.SystemLibrary.execute_console_command(world, 'Slate.bAllowThrottling ' + str(old_throttle))),
            ('unregister', lambda: unreal.unregister_slate_post_tick_callback(state['handle']))]:
            try:
                action()
                report[name] = 'requested' if name == 'stopPie' else 'completed'
            except Exception as exc:
                report['errors'].append(name + ': ' + str(exc))
        report['elapsedSeconds'] = time.monotonic() - started
        ACTIVE = None
        output.write_text(json.dumps(report, indent=2), encoding='utf-8')

    def tick(delta):
        try:
            elapsed = time.monotonic() - started
            if elapsed >= seconds:
                finish('observation_finished_requires_operator_review')
                return
            game = editor.get_game_world()
            if not game:
                if state['seen']:
                    finish('operator_ended_pie')
                elif elapsed > 20:
                    finish('failed_no_game_world')
                return
            state['seen'] = True
            controller = unreal.GameplayStatics.get_player_controller(game, 0)
            pawn = unreal.GameplayStatics.get_player_pawn(game, 0)
            if not controller or not pawn:
                return
            if 'MikdashPlayerController' not in controller.get_class().get_name():
                raise RuntimeError('Unexpected controller: ' + controller.get_class().get_name())
            if elapsed - state['last'] < 0.1:
                return
            state['last'] = elapsed
            p = pawn.get_actor_location()
            v = pawn.get_velocity()
            rotation = controller.get_control_rotation()
            xyz = [p.x, p.y, p.z]
            if not all(math.isfinite(x) for x in xyz):
                raise RuntimeError('Nonfinite pawn position')
            movement = pawn.get_component_by_class(unreal.CharacterMovementComponent)
            capsule = pawn.get_component_by_class(unreal.CapsuleComponent)
            if not movement or not capsule:
                raise RuntimeError('Expected walking Character')
            report['samples'].append({'seconds': elapsed, 'gameSeconds': unreal.GameplayStatics.get_time_seconds(game),
                'paused': unreal.GameplayStatics.is_game_paused(game),
                'menuOpen': controller.is_walkthrough_menu_open(),
                'cursorFlag': controller.get_editor_property('show_mouse_cursor'),
                'positionCm': xyz, 'velocityCmPerSecond': [v.x, v.y, v.z],
                'rotation': [rotation.pitch, rotation.yaw, rotation.roll],
                'mode': str(movement.get_editor_property('movement_mode')),
                'stepHeightCm': movement.get_editor_property('max_step_height'),
                'capsuleHalfHeightCm': capsule.get_scaled_capsule_half_height()})
        except Exception as exc:
            report['errors'].append(str(exc))
            finish('failed')

    try:
        output.write_text(json.dumps(report, indent=2), encoding='utf-8')
        settings.set_editor_property('GameGetsMouseControl', False)
        unreal.SystemLibrary.execute_console_command(world, 'Slate.bAllowThrottling 0')
        state['handle'] = unreal.register_slate_post_tick_callback(tick)
        levels.editor_request_begin_play()
    except Exception:
        finish('failed_start')
        raise
    return str(output)
