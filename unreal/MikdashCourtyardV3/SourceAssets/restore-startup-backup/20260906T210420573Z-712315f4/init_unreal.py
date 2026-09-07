"""One-shot import bootstrap for this fresh standalone pilot project only.

Official mechanisms: Content/Python/init_unreal.py startup discovery,
register_slate_post_tick_callback, LevelEditorSubsystem.new_level/save_current_level.
No remote commands, account configuration or background persistence is installed.
"""
from pathlib import Path
import json
import runpy
import time
import traceback
import unreal

PROJECT = Path(__file__).resolve().parents[2]
ASSETS = PROJECT / "SourceAssets"
SAVED = PROJECT / "Saved"
MARKER = SAVED / "pilot-bootstrap-attempt.json"
LEVEL = "/Game/MikdashV3/Maps/Courtyard"
SAVED.mkdir(exist_ok=True)
_started = time.monotonic()
_ready_since = None
_handle = None


def _record(status, **details):
    MARKER.write_text(json.dumps({"status": status, "timeUtc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **details}, indent=2) + "\n")


def _unregister():
    global _handle
    if _handle is not None:
        unreal.unregister_slate_post_tick_callback(_handle)
        _handle = None


def _execute_once():
    try:
        with MARKER.open("x") as stream: stream.write(json.dumps({"status":"started"}))
    except FileExistsError:
        return
    try:
        import courtyard_v3
        courtyard_v3.run()
        report=json.loads((ASSETS/"unreal-v3-validation.json").read_text())
        _record(report["status"],level=report.get("level"),visualAcceptance="UNTESTED")
    except Exception as error:
        _record("failed",error=str(error),traceback=traceback.format_exc())
        unreal.log_error(traceback.format_exc())


def _tick(delta_seconds):
    global _ready_since
    if MARKER.exists():
        _unregister()
        return
    now = time.monotonic()
    if now - _started > 120:
        _unregister()
        _record("editor_not_ready", error="No usable editor world/viewport became ready within 120 seconds. Import was not attempted.")
        return
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    ready = editor.get_editor_world() is not None and levels.get_current_level() is not None and editor.get_level_viewport_camera_info() is not None and not levels.is_in_play_in_editor()
    if not ready:
        _ready_since = None
        return
    if _ready_since is None:
        _ready_since = now
    # A readiness check plus settled Slate frames, not a blocking editor sleep.
    if now - _ready_since >= 5:
        _unregister()
        _execute_once()


if MARKER.exists():
    unreal.log("Mikdash V3: previous bootstrap attempt found; no automatic rerun. See Saved/pilot-bootstrap-attempt.json.")
else:
    _handle = unreal.register_slate_post_tick_callback(_tick)
    unreal.log("Mikdash V3: waiting for the editor world before importing.")
