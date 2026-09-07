"""Load the persistent review module; explicitly call start('wall' or 'paving').

20 s unchanged baseline, then 30 s candidate; auto-restores on the first editor
tick at/after 50 s. A stalled editor can delay callbacks: actual times are logged.
Never saves a map or changes lighting/exposure. stop() is also callable manually.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time

import unreal


ROOT = Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
MODULE = "mikdash_jerusalem_stone_v2_review"
_state = None
PROFILES = {
    "wall": {
        "source": "SM_0138_architecture_Inner_eastern_gate_wall_jamb_1",
        "sourceMaterialKey": "stone",
        "pilot": "M_JerusalemStoneV2_WallReview",
        "camera": [6500, -1800, 468], "rotation": [0, 155, 0],
        "cameraSource": "Scripts/review_exterior_exposure.py",
    },
    "paving": {
        "source": "SM_0130_floor_Inner_court_clear_floor",
        "sourceMaterialKey": "innerPaving",
        "pilot": "M_JerusalemStoneV2_PavingReview",
        "camera": [2100, -1500, 668], "rotation": [0, 170, 0],
        "cameraSource": "Scripts/review_exposure_bounded.py",
    },
}


def _path(obj):
    return obj.get_path_name() if obj else None


def _camera_data(camera):
    loc, rot = camera
    return {"location": [loc.x, loc.y, loc.z],
            "rotationPitchYawRoll": [rot.pitch, rot.yaw, rot.roll]}


def _record(stage):
    state = _state
    state["report"]["events"].append({
        "stage": stage, "seconds": round(time.monotonic()-state["started"], 3)})
    state["receipt"].write_text(json.dumps(state["report"], indent=2)+"\n", encoding="utf-8")


def stop():
    """Restore each captured state independently, retaining failure diagnostics."""
    state = _state
    if not state:
        return
    errors = []
    operations = (
        ("materials", lambda: state["component"].set_editor_property(
            "override_materials", state["overrides"])),
        ("camera", lambda: state["editor"].set_level_viewport_camera_info(*state["camera"])),
        ("throttle", lambda: unreal.SystemLibrary.execute_console_command(
            state["world"], "Slate.bAllowThrottling " + str(state["throttle"]))),
    )
    for name, operation in operations:
        try:
            operation()
        except Exception as error:
            errors.append(name+": "+str(error))
    if state["handle"] is not None:
        try:
            unreal.unregister_slate_post_tick_callback(state["handle"])
            state["handle"] = None
        except Exception as error:
            errors.append("callback: "+str(error))
    state["active"] = False
    report = state["report"]
    try:
        report["overridesRestored"] = list(state["component"].get_editor_property(
            "override_materials")) == state["overrides"]
        report["materialRestored"] = state["component"].get_material(0) == state["original"]
        report["cameraAfter"] = _camera_data(state["editor"].get_level_viewport_camera_info())
        before, after = report["originalCamera"], report["cameraAfter"]
        report["cameraRestored"] = all(abs(a-b) < 0.001 for key in before
                                      for a, b in zip(before[key], after[key]))
        report["throttleRestored"] = unreal.SystemLibrary.get_console_variable_int_value(
            "Slate.bAllowThrottling") == state["throttle"]
        report["exposureBiasUnchanged"] = all(
            float(volume.get_editor_property("settings").get_editor_property(
                "auto_exposure_bias")) == bias for volume, bias in state["exposure"])
        report["dirtyMapPackagesAfter"] = [package.get_name() for package in
            unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    except Exception as error:
        errors.append("readback: "+str(error))
    report["restoreErrors"] = errors
    keys = ("overridesRestored", "materialRestored", "cameraRestored", "throttleRestored")
    report["status"] = "restored" if not errors and all(report.get(k) for k in keys) else "RESTORE_REVIEW_REQUIRED"
    _record(report["status"])
    unreal.log("JERUSALEM_STONE_V2_REVIEW_"+report["status"].upper()+": "+str(state["receipt"]))


def _tick(delta):
    state = _state
    if not state or not state["active"]:
        return
    try:
        elapsed = time.monotonic()-state["started"]
        if elapsed >= 50:
            stop()
        elif elapsed >= 20 and state["phase"] == "baseline":
            state["component"].set_material(0, state["pilot"])
            assert state["component"].get_material(0) == state["pilot"]
            state["phase"] = "candidate"
            _record("candidate_applied")
            unreal.log("JERUSALEM_STONE_V2_CANDIDATE: 30 second review window")
    except Exception as error:
        state["report"]["error"] = str(error)
        stop()
        unreal.log_error("Jerusalem stone review failed: "+str(error))


def start(profile):
    global _state
    assert profile in PROFILES, "Choose wall or paving"
    assert not _state or (not _state["active"] and _state["report"]["status"] == "restored"), "Previous review needs restoration"
    assert Path(unreal.Paths.project_dir()).resolve() == ROOT
    for name in ("mikdash_grain_review", "mikdash_exposure_review", "mikdash_stone_visual"):
        assert not getattr(sys.modules.get(name), "active", False), "Another visual review is active"
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor.get_editor_world()
    assert not editor.get_game_world()
    assert world.get_path_name().split(".")[0] == "/Game/MikdashV3/Maps/Courtyard"
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), "Need a saved baseline; never save candidate overrides"
    chosen = PROFILES[profile]
    manifest_path = ROOT / "SourceAssets/architecture-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    records = [r for r in manifest["meshes"] if r["assetName"] == chosen["source"]]
    assert len(records) == 1
    source = records[0]
    assert len(source["materialSlots"]) == 1
    assert source["materialSlots"][0]["sourceMaterialKey"] == chosen["sourceMaterialKey"]
    components = []
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    for actor in actors:
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = component.get_editor_property("static_mesh")
            if mesh and mesh.get_path_name().startswith("/Game/MikdashV3/Architecture/") and mesh.get_name() == "architecture_"+chosen["source"]:
                components.append(component)
    assert len(components) == 1, "Need exactly the source-matched component"
    component = components[0]
    mesh = component.get_editor_property("static_mesh")
    box = mesh.get_bounding_box()
    bounds = {"min": [box.min.x, box.min.y, box.min.z], "max": [box.max.x, box.max.y, box.max.z]}
    error = max(abs(bounds[k][i]-source["expectedBoundsUnrealCm"][k][i])
                for k in bounds for i in range(3))
    assert math.isfinite(error) and error <= 0.5
    assert mesh.get_num_triangles(0) == source["triangles"]
    transform = component.get_world_transform()
    loc, scale, rot = transform.translation, transform.scale3d, transform.rotation.rotator()
    assert max(abs(v) for v in (loc.x, loc.y, loc.z, scale.x-1, scale.y-1, scale.z-1,
                               rot.pitch, rot.yaw, rot.roll)) <= 0.0001
    assert component.get_num_materials() == 1
    original = component.get_material(0)
    pilot = unreal.load_asset("/Game/MikdashV3/MaterialReview/JerusalemStoneV2/"+chosen["pilot"])
    assert isinstance(pilot, unreal.Material) and original and original != pilot
    if profile == "paving":
        assert original.get_name() == "M_StonePilot_Paving_Pilot01_innerPaving"
    camera = editor.get_level_viewport_camera_info()
    throttle = unreal.SystemLibrary.get_console_variable_int_value("Slate.bAllowThrottling")
    exposure = [(a, float(a.get_editor_property("settings").get_editor_property("auto_exposure_bias")))
                for a in actors if isinstance(a, unreal.PostProcessVolume)]
    receipt = ROOT / "SourceAssets/visual-review" / (
        "jerusalem-stone-v2-"+profile+"-"+time.strftime("%Y%m%dT%H%M%S")+".json")
    assert not receipt.exists(), "Preserve previous receipt"
    overrides = list(component.get_editor_property("override_materials"))
    report = {"status": "running", "profile": profile, "component": component.get_path_name(),
              "sourceMesh": chosen["source"], "sourceBoundsCm": bounds,
              "manifestSha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
              "originalMaterial": _path(original), "originalOverrides": [_path(x) for x in overrides],
              "pilot": _path(pilot), "originalCamera": _camera_data(camera),
              "reviewCamera": chosen["camera"], "reviewRotationPitchYawRoll": chosen["rotation"],
              "cameraSource": chosen["cameraSource"], "originalThrottle": throttle,
              "exposureBiasBefore": [{"actor": _path(a), "bias": b} for a, b in exposure],
              "mapSaved": False, "events": [], "visualAcceptance": "PENDING",
              "scope": "One component; fixed existing camera. Operator must confirm target visibility. No lighting changes, source geometry changes, screenshots or automatic visual judgment.",
              "timing": "20s baseline+30s candidate; restore on first tick >=50s; stalled editor may delay callback"}
    _state = dict(active=True, phase="baseline", started=time.monotonic(), handle=None,
                  component=component, overrides=overrides, original=original, pilot=pilot,
                  camera=camera, throttle=throttle, editor=editor, world=world,
                  exposure=exposure, receipt=receipt, report=report)
    try:
        _state["handle"] = unreal.register_slate_post_tick_callback(_tick)
        unreal.SystemLibrary.execute_console_command(world, "Slate.bAllowThrottling 0")
        pitch, yaw, roll = chosen["rotation"]
        editor.set_level_viewport_camera_info(unreal.Vector(*chosen["camera"]),
            unreal.Rotator(pitch=pitch, yaw=yaw, roll=roll))
        _record("baseline")
        unreal.log("JERUSALEM_STONE_V2_BASELINE: "+profile+"; candidate after 20 seconds")
    except Exception:
        stop()
        raise


if __name__ == "__main__":
    previous = sys.modules.get(MODULE)
    assert not previous or not getattr(previous, "_state", None) or not previous._state["active"]
    if previous and previous._state:
        assert previous._state["report"]["status"] == "restored"
    spec = importlib.util.spec_from_file_location(MODULE, __file__)
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE] = module
    spec.loader.exec_module(module)
    unreal.log("Review loaded. Explicitly call: import mikdash_jerusalem_stone_v2_review as stone_review; stone_review.start('wall') or start('paving'). stop() restores early.")
