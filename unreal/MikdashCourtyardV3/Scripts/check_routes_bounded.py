"""Bounded PIE floor/capsule diagnostics. No input or pawn relocation.
Run only after scene save/reopen, through the editor Python console.
"""
import importlib.util
import json
import time
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
if root != Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3'):
    raise RuntimeError('Wrong project')
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
if editor.get_game_world() or unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Stop PIE and save the map before diagnostics')
if editor.get_editor_world().get_path_name().split('.')[0] != '/Game/MikdashV3/Maps/Courtyard':
    raise RuntimeError('Wrong map')
spec = importlib.util.spec_from_file_location('route_inspection', root/'Scripts/inspect_walking.py')
inspection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspection)
settings = unreal.get_default_object(unreal.load_class(None, '/Script/UnrealEd.LevelEditorPlaySettings'))
old_mouse = settings.get_editor_property('GameGetsMouseControl')
receipt = {'status': 'waiting_for_pie', 'scope': 'Sparse floor and capsule traces only; not continuous movement acceptance', 'errors': []}
output = root/'SourceAssets/runtime-review/bounded-route-check.json'
started = time.monotonic()
handle = None
finished = False

def finish():
    global finished
    finished = True
    try:
        level.editor_request_end_play()
    finally:
        settings.set_editor_property('GameGetsMouseControl', old_mouse)
        unreal.unregister_slate_post_tick_callback(handle)
        receipt['stopRequested'] = True
        output.write_text(json.dumps(receipt, indent=2), encoding='utf-8')

def tick(delta):
    if finished:
        return
    try:
        elapsed = time.monotonic()-started
        world = editor.get_game_world()
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0) if world else None
        if pawn and elapsed >= 2:
            receipt['snapshot'] = inspection.walk_snapshot('saved context route diagnostic')
            receipt['report'] = inspection.diagnose_routes(str(root/'SourceAssets/runtime-review/route-waypoints.json'))
            receipt['status'] = 'traces_recorded_requires_review'
            finish()
        elif elapsed >= 20:
            receipt['status'] = 'failed_pie_start_timeout'
            finish()
    except Exception as exc:
        receipt['errors'].append(str(exc))
        receipt['status'] = 'failed'
        if not finished:
            finish()

settings.set_editor_property('GameGetsMouseControl', False)
output.write_text(json.dumps(receipt), encoding='utf-8')
handle = unreal.register_slate_post_tick_callback(tick)
try:
    level.editor_request_begin_play()
except Exception:
    finish()
    raise
