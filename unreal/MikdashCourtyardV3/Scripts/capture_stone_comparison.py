"""Load stone_capture; call start('wall') or start('paving') in an idle editor.

Uses the existing verified 50-second restoration script. Native high-resolution
viewport captures occur during baseline and candidate; no OS capture or map save.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import time

import unreal

ROOT = Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
MODULE = "mikdash_stone_capture"
_state = None


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write():
    _state["receipt"].write_text(json.dumps(_state["report"], indent=2)+"\n", encoding="utf-8")


def stop(reason="manual_stop"):
    state = _state
    if not state or not state["active"]:
        return
    try:
        state["review"].stop()
    finally:
        if state["handle"] is not None:
            unreal.unregister_slate_post_tick_callback(state["handle"])
            state["handle"] = None
        state["active"] = False
        report = state["report"]
        report["stopReason"] = reason
        report["elapsedSeconds"] = round(time.monotonic()-state["started"], 3)
        native = state["review"]._state["report"]
        report["restoration"] = {key: native.get(key) for key in (
            "status", "overridesRestored", "materialRestored", "cameraRestored",
            "throttleRestored", "exposureBiasUnchanged", "restoreErrors")}
        report["reviewReceipt"] = str(state["review"]._state["receipt"])
        complete = len(report["captures"]) == 2 and all(x.get("verifiedFile") for x in report["captures"])
        report["status"] = "captured_and_restored_visual_acceptance_pending" if (
            complete and reason == "complete" and native.get("status") == "restored"
            and native.get("exposureBiasUnchanged")) else "INCOMPLETE_REVIEW_REQUIRED"
        _write()
        unreal.log("STONE_CAPTURE_"+report["status"].upper()+": "+str(state["receipt"]))


def _take(phase):
    state = _state
    review_state = state["review"]._state
    assert review_state["active"] and review_state["phase"] == phase
    for volume, bias in review_state["exposure"]:
        assert float(volume.get_editor_property("settings").get_editor_property("auto_exposure_bias")) == bias
    camera_now = state["review"]._camera_data(review_state["editor"].get_level_viewport_camera_info())
    expected = review_state["report"]
    assert max(abs(a-b) for a,b in zip(camera_now["location"], expected["reviewCamera"])) < .001
    assert max(abs((a-b+180.0)%360.0-180.0) for a,b in zip(
        camera_now["rotationPitchYawRoll"], expected["reviewRotationPitchYawRoll"])) < .001
    path = state["folder"] / (phase+".png")
    assert not path.exists()
    capture = {"phase": phase, "file": str(path), "verifiedFile": False,
               "requestedSeconds": round(time.monotonic()-state["started"],3),
               "camera": camera_now}
    state["report"]["captures"].append(capture)
    # Installed UE5.8 AutomationBlueprintFunctionLibrary.h/cpp confirms these
    # arguments, returned task and its completion methods. No camera actor lock.
    task = unreal.AutomationLibrary.take_high_res_screenshot(
        1280, 720, str(path), camera=None, mask_enabled=False, capture_hdr=False,
        delay=0.0, force_game_view=False)
    assert task and task.is_valid_task(), "Native screenshot task was not scheduled"
    state["pending"] = (task, path, capture)
    _write()


def _tick(delta):
    state = _state
    if not state or not state["active"]:
        return
    try:
        elapsed = time.monotonic()-state["started"]
        review = state["review"]._state
        if elapsed >= 48:
            stop("capture_deadline"); return
        if state["pending"]:
            task, path, capture = state["pending"]
            assert review["active"] and review["phase"] == capture["phase"], "Material phase changed before capture completed"
            if task.is_task_done() and path.exists():
                data = path.read_bytes()
                assert data[:8] == b"\x89PNG\r\n\x1a\n", "Expected native PNG output"
                assert struct.unpack(">II",data[16:24]) == (1280,720)
                capture.update(verifiedFile=True,sha256=hashlib.sha256(data).hexdigest(),
                               completedSeconds=round(elapsed,3),bytes=len(data))
                state["pending"] = None
                _write()
            elif capture["phase"] == "baseline" and elapsed >= 18:
                raise RuntimeError("Baseline capture exceeded its safe phase window")
            return
        count = len(state["report"]["captures"])
        if count == 0 and elapsed >= 8:
            _take("baseline")
        elif count == 1 and elapsed >= 30:
            _take("candidate")
        elif count == 2:
            stop("complete")
    except Exception as error:
        state["report"]["error"] = str(error)
        stop("error")
        unreal.log_error("Stone comparison capture: "+str(error))


def start(profile):
    global _state
    assert profile in ("wall", "paving")
    assert not _state or not _state["active"]
    assert Path(unreal.Paths.project_dir()).resolve() == ROOT
    review_name = "mikdash_jerusalem_stone_v2_review"
    previous = sys.modules.get(review_name)
    if previous and previous._state:
        assert not previous._state["active"] and previous._state["report"]["status"] == "restored"
    review = _load(review_name, ROOT/"Scripts/review_jerusalem_stone_v2.py")
    assert hasattr(review,"_derive_camera"), "Need source-derived close-camera review version"
    folder = ROOT/"SourceAssets/visual-review"/("stone-capture-"+profile+"-"+time.strftime("%Y%m%dT%H%M%S"))
    assert not folder.exists()
    folder.mkdir()
    review.start(profile)
    _state = {"active":True,"review":review,"started":time.monotonic(),"handle":None,
              "folder":folder,"receipt":folder/"capture-receipt.json","pending":None,
              "report":{"status":"running","profile":profile,"captures":[],"mapSaved":False,
                        "renderer":"Unreal native 1280x720 PNG viewport screenshot",
                        "limits":"Material comparison only. File validity is not visual approval. Source-derived face-normal camera still requires occlusion/lighting inspection. Screenshots can include editor overlays because game-view state is preserved."}}
    try:
        _state["handle"] = unreal.register_slate_post_tick_callback(_tick)
        _write()
    except Exception:
        stop("setup_error"); raise


if __name__ == "__main__":
    previous = sys.modules.get(MODULE)
    assert not previous or not previous._state or not previous._state["active"]
    _load(MODULE, __file__)
    unreal.log("Loaded: import mikdash_stone_capture as stone_capture; stone_capture.start('wall') or start('paving'). stop() restores early.")
