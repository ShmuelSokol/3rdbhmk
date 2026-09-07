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
# RESTORE_GUARD_V1: SourceAssets survives checkpoints that exclude Saved.
MARKER = ASSETS / "pilot-bootstrap-attempt.json"
LEGACY_MARKER = SAVED / "pilot-bootstrap-attempt.json"
SAVED_MAP = PROJECT / "Content" / "MikdashV3" / "Maps" / "Courtyard.umap"
PRIOR_REPORT = ASSETS / "unreal-v3-validation.json"


def _existing_project_or_attempt():
    # Any prior report/attempt (including failure) requires deliberate review.
    # Do not call the importer and overwrite a durable diagnostic receipt.
    return SAVED_MAP.exists() or PRIOR_REPORT.exists() or MARKER.exists() or LEGACY_MARKER.exists()
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
    if _existing_project_or_attempt():
        return
    ASSETS.mkdir(exist_ok=True)
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
    if _existing_project_or_attempt():
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


if _existing_project_or_attempt():
    unreal.log("Mikdash V3: saved map or prior durable/legacy report found; automatic import skipped. Existing project preserved.")
else:
    _handle = unreal.register_slate_post_tick_callback(_tick)
    unreal.log("Mikdash V3: waiting for the editor world before importing.")
