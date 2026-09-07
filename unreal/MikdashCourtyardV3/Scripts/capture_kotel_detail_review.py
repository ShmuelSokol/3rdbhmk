"""Finite grounded Kotel facade/detail native capture; no map/material/light changes or adoption.

API basis (installed UE5.8 source):
  FunctionalTesting/Public/AutomationBlueprintFunctionLibrary.h: TakeHighResScreenshot,
    UAutomationEditorTask.IsValidTask/IsTaskDone; implementation .cpp:1223 onwards
    targets the first active level viewport and finishes loading before capture.
  LevelEditor/Public/LevelEditorSubsystem.h: LoadLevel, EditorInvalidateViewports,
    GetActiveViewportConfigKey, EditorGet/SetGameView, Get/SetLevelViewportFOV.
  UnrealEd/Public/Subsystems/UnrealEditorSubsystem.h: Get/SetLevelViewportCameraInfo.
  PythonScriptPlugin/Private/PySlate.cpp: register/unregister_slate_post_tick_callback.
  Engine/Classes/Kismet/KismetSystemLibrary.h: SphereTraceSingleByProfile.

Run only in a separate GUI capture editor, never the user play editor.
Explicit start(dedicated_editor=True), with no PIE or other automation.
Root serializes execution. Source file derived from proven exposure capture script.
Each view gets >=45 seconds and >=120 Slate ticks before capture. Total watchdog600s.
These are technical interior viewpoints, not visitor-access authorizations.
"""
import hashlib
import importlib.util
import json
import math
import struct
import sys
import time
import uuid
from pathlib import Path

import unreal


MODULE_NAME = "mikdash_kotel_detail_capture"
ROOT = Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
ALLOWED=frozenset(("/Game/MikdashV3/MaterialReview/KotelStoneV1/Maps/FutureMountDetail",
                   "/Game/MikdashV3/MaterialReview/KotelStoneV1/Maps/IntegratedDetail"))
DETAIL_FOLDER=ROOT/"SourceAssets/kotel-detail/KotelStoneV1"
RESOLUTION = (1920, 1080)



def map_file(asset):
    assert asset.startswith("/Game/")
    return ROOT / "Content" / (asset[len("/Game/"):] + ".umap")


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Comparison:
    def __init__(self):
        self.editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        self.level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        self.handle = None
        self.active = False
        self.task = None
        self.busy = False
        self.index = -1
        self.phase = "initializing"
        self.started = time.monotonic()
        self.phase_started = self.started
        self.ticks = 0

    def write(self):
        self.report_path.write_text(json.dumps(self.report, indent=2) + "\n", encoding="utf-8")

    def event(self, label):
        self.report["events"].append({"event": label, "elapsedSeconds": round(time.monotonic() - self.started, 2)})
        self.write()

    def begin(self, review_map_path, dedicated_editor=False):
        assert dedicated_editor is True, "Root must explicitly confirm this is the separate capture editor"
        assert Path(unreal.Paths.project_dir()).resolve() == ROOT
        assert not self.editor.get_game_world(), "Stop PIE before comparison"
        assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), "Preserve unsaved maps first"
        assert review_map_path in ALLOWED and map_file(review_map_path).exists()
        self.review_map = review_map_path
        self.hashes = {review_map_path:file_hash(map_file(review_map_path))}
        self.detail=json.loads((DETAIL_FOLDER/"manifest.json").read_text())
        matches=[]
        for receipt in DETAIL_FOLDER.glob("placement-*.json"):
            record=json.loads(receipt.read_text())
            if record.get("status")=="SAVED_REOPENED_BASE_PRESERVED_VISUAL_PENDING" and record.get("map")==review_map_path and record.get("mapSha256")==self.hashes[review_map_path]:matches.append(str(receipt))
        assert len(matches)==1,"Need verified unchanged Kotel placement map receipt"
        self.placement_receipt=matches[0]
        self.views=[None,None]
        self.old_map = self.editor.get_editor_world().get_path_name().split(".")[0]
        assert self.old_map.startswith("/Game/") and map_file(self.old_map).exists(), "Start from a saved map"
        self.old_camera = self.editor.get_level_viewport_camera_info()
        assert self.old_camera, "No usable GUI level viewport"
        self.viewport = self.level.get_active_viewport_config_key()
        self.old_fov = self.level.get_level_viewport_fov(self.viewport)
        assert self.old_fov is not None
        self.old_game_view = self.level.editor_get_game_view(self.viewport)
        self.old_throttle = unreal.SystemLibrary.get_console_variable_int_value("Slate.bAllowThrottling")
        self.folder = ROOT / "SourceAssets/visual-review" / ("kotel-detail-capture-" + uuid.uuid4().hex[:10])
        self.folder.mkdir(exist_ok=False)
        self.report_path = self.folder / "comparison.json"
        self.report = {
            "status": "running", "maps": self.hashes, "resolution": RESOLUTION,
            "placementReceipt":self.placement_receipt,
            "detailManifestSha256":file_hash(DETAIL_FOLDER/"manifest.json"),
            "comparisonScope": "Grounded Kotel face views from actual western facade segment. No architectural accuracy, performance or visual acceptance implied.",
            "fovDegrees": 75, "warmupSecondsPerView": 45, "minimumSlateTicksPerView": 120,
            "readinessPolicy":"After camera placement finish_loading_before_screenshot, then start rendered warmup; 10m facade view then2m detail view. No material/light changes.",
            "viewTiming":[],
            "watchdogSeconds": 600, "sourceManifestSha256": file_hash(ROOT / "SourceAssets/architecture-manifest.json"),
            "sourceWallBoundsCm": self.detail["sourceBase"]["boundsCm"], "views": self.views, "events": [], "captures": [],
            "mapSaved": False, "adopted": False, "visualAcceptance": "PENDING",
            "limits": "Native technical comparison stills. No access authorization, automatic image quality approval, transition/motion acceptance or packaged proof. Screenshots retain native renderer pixels.",
        }
        self.active = True
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
        try:
            unreal.SystemLibrary.execute_console_command(self.editor.get_editor_world(), "Slate.bAllowThrottling 0")
            self.next_view()
        except Exception as error:
            self.finish("failed", str(error))
            raise

    def next_view(self):
        self.index += 1
        if self.index == 2:
            self.finish("captured_restored_requires_visual_review")
            return
        asset = self.review_map
        self.asset = asset
        if self.editor.get_editor_world().get_path_name().split(".")[0] != asset:
            assert self.level.load_level(asset), "Map load failed"
        assert not self.editor.get_game_world()
        actor_api=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        all_actors=actor_api.get_all_level_actors()
        overlays=[a for a in all_actors if "KotelStoneV1OverlayReview" in [str(t) for t in a.tags]]
        assert len(overlays)==6
        face=max(self.detail["faces"],key=lambda f:f["lengthCm"])
        distance=(1000.0,200.0)[self.index]
        mid=[(face["a"][i]+face["b"][i])/2 for i in (0,1)]
        xy=[mid[i]+face["normal"][i]*distance for i in (0,1)]
        wall=self.detail["sourceBase"]["boundsCm"]
        floor_points=[]
        # Trace three points along the face tangent to reject obvious step/ledge placement.
        for offset in (-15,0,15):
            x,y=[xy[i]+face["tangent"][i]*offset for i in (0,1)]
            hit=unreal.SystemLibrary.line_trace_single_by_profile(world_context_object=self.editor.get_editor_world(),
                start=unreal.Vector(x,y,wall["max"][2]+500),end=unreal.Vector(x,y,wall["min"][2]-1500),
                profile_name="Pawn",trace_complex=True,actors_to_ignore=overlays,
                draw_debug_type=unreal.DrawDebugTrace.NONE,ignore_self=False)
            assert hit,"No actual ground contact west of Kotel face"
            contact=hit.get_editor_property("impact_point");normal=hit.get_editor_property("impact_normal")
            assert normal.z>.9,"Ground slope unsuitable for eyelevel reference"
            floor_points.append([contact.x,contact.y,contact.z])
        assert max(v[2] for v in floor_points)-min(v[2] for v in floor_points)<30,"Ground trace straddles a ledge"
        position=[xy[0],xy[1],floor_points[1][2]+168]
        assert wall["min"][2]+20<position[2]<wall["max"][2]-20,"Ground eyeheight outside modeled Kotel face; inspect alignment"
        target=[mid[0]+face["normal"][0]*5,mid[1]+face["normal"][1]*5,position[2]]
        blocked=unreal.SystemLibrary.line_trace_single_by_profile(world_context_object=self.editor.get_editor_world(),
            start=unreal.Vector(*position),end=unreal.Vector(*target),profile_name="Pawn",trace_complex=True,
            actors_to_ignore=overlays,draw_debug_type=unreal.DrawDebugTrace.NONE,ignore_self=False)
        assert blocked is None,"Plaza face sightline blocked"
        yaw=math.degrees(math.atan2(target[1]-position[1],target[0]-position[0]))
        self.view={"id":("kotel_facade_10m","kotel_detail_2m")[self.index],"position":position,"yaw":yaw,"pitch":0,
            "target":target,"sourceEdge":face["edge"],"groundContactsCm":floor_points,
            "basis":"Longest verified west-facing footprint segment midpoint; outward normal offset; actual groundtrace+168cm eyeheight. Not whole-building bbox."}
        self.views[self.index]=self.view;self.report["views"]=self.views
        assert self.level.get_active_viewport_config_key() == self.viewport, "Active viewport changed"
        self.level.set_level_viewport_fov(75.0, self.viewport)
        self.level.editor_set_game_view(True, self.viewport)
        location = unreal.Vector(*self.view["position"])
        # A short10cm sphere sweep verifies camera clearance against Pawn collision.
        # It does not establish path clearance or a person's permission to be here.
        hit = unreal.SystemLibrary.sphere_trace_single_by_profile(
            world_context_object=self.editor.get_editor_world(), start=location,
            end=location + unreal.Vector(0, 0, 1), radius=10.0, profile_name="Pawn",
            trace_complex=False, actors_to_ignore=[], draw_debug_type=unreal.DrawDebugTrace.NONE,
            ignore_self=True)
        assert hit is None, "Camera collision clearance failed: " + self.view["id"]
        self.editor.set_level_viewport_camera_info(location, unreal.Rotator(pitch=self.view["pitch"], yaw=self.view["yaw"], roll=0))
        self.filename = self.folder / (self.view["id"] + ".png")
        assert not self.filename.exists()
        # Loading can pump Slate. Prevent a reentrant tick from touching state.
        previous_busy = self.busy
        self.busy = True
        self.phase = "readiness"
        barrier_started = time.monotonic()
        self.view_timing = {"view":self.view["id"], "barrierStartedSeconds":round(barrier_started-self.started,3)}
        self.report["viewTiming"].append(self.view_timing)
        self.event("readiness_"+self.filename.stem)
        try:
            unreal.AutomationLibrary.finish_loading_before_screenshot()
            self.view_timing["barrierElapsedSeconds"] = round(time.monotonic()-barrier_started,3)
            self.phase = "warming"
            self.phase_started = time.monotonic()
            self.view_timing["warmupStartedSeconds"] = round(self.phase_started-self.started,3)
            self.ticks = 0
            self.task = None
            self.event("warming_" + self.filename.stem)
        finally:
            self.busy = previous_busy

    def tick(self, delta_seconds):
        if not self.active or self.busy:
            return
        self.busy = True
        try:
            now = time.monotonic()
            assert now - self.started < 600, "Comparison watchdog expired"
            assert not self.editor.get_game_world(), "PIE started during comparison"
            assert self.level.get_active_viewport_config_key() == self.viewport, "Active viewport changed"
            assert self.editor.get_editor_world().get_path_name().split(".")[0] == self.asset, "Map changed outside comparison"
            # Force redraws without changing the user's persistent realtime setting.
            self.level.editor_invalidate_viewports()
            self.ticks += 1
            if self.phase == "warming" and now - self.phase_started >= 45 and self.ticks >= 120:
                camera = self.editor.get_level_viewport_camera_info()
                assert camera and (camera[0] - unreal.Vector(*self.view["position"])).length() < 0.1, "Camera moved during warmup"
                yaw_error = (camera[1].yaw - self.view["yaw"] + 180.0) % 360.0 - 180.0
                assert abs(yaw_error) < 0.1 and abs(camera[1].pitch-self.view["pitch"]) < 0.1 and abs(camera[1].roll) < 0.1, "Camera rotation changed"
                self.view_timing["warmupElapsedSeconds"] = round(now-self.phase_started,3)
                self.view_timing["warmupSlateTicks"] = self.ticks
                screenshot_call_started = time.monotonic()
                self.task = unreal.AutomationLibrary.take_high_res_screenshot(
                    RESOLUTION[0], RESOLUTION[1], str(self.filename), camera=None,
                    mask_enabled=False, capture_hdr=False, delay=0.0, force_game_view=False)
                self.view_timing["screenshotCallElapsedSeconds"] = round(time.monotonic()-screenshot_call_started,3)
                assert self.task and self.task.is_valid_task(), "Screenshot task was not configured"
                self.phase = "capturing"
                self.phase_started = time.monotonic()
                self.event("requested_" + self.filename.stem)
            elif self.phase == "capturing":
                assert now - self.phase_started < 90, "Screenshot task/file timeout"
                if self.task.is_task_done() and self.filename.exists():
                    data = self.filename.read_bytes()
                    assert data[:8] == b"\x89PNG\r\n\x1a\n", "Native screenshot is not PNG"
                    width, height = struct.unpack(">II", data[16:24])
                    assert (width, height) == RESOLUTION, "Screenshot resolution mismatch"
                    self.report["captures"].append({"map": self.asset, "view": self.view["id"],
                        "file": str(self.filename), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                        "nativeTaskDone": True, "cameraClearanceChecked": True,
                        "camera":self.view,"timing":dict(self.view_timing)})
                    self.event("captured_" + self.filename.stem)
                    self.next_view()
        except Exception as error:
            self.finish("failed", str(error))
            unreal.log_error("KOTEL_DETAIL_CAPTURE_FAILED: " + str(error))
        finally:
            self.busy = False

    def finish(self, status, error=None):
        if not self.active:
            return
        self.active = False
        if self.handle is not None:
            unreal.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        self.report["status"] = status
        if error:
            self.report["error"] = error
        restore_errors = []
        try:
            assert self.level.load_level(self.old_map), "Original view map reload failed"
            self.editor.set_level_viewport_camera_info(self.old_camera[0], self.old_camera[1])
            self.level.set_level_viewport_fov(self.old_fov, self.viewport)
            self.level.editor_set_game_view(self.old_game_view, self.viewport)
            self.report["originalMapAndCameraRestored"] = True
        except Exception as restore_error:
            restore_errors.append(str(restore_error))
        try:
            unreal.SystemLibrary.execute_console_command(self.editor.get_editor_world(), "Slate.bAllowThrottling " + str(self.old_throttle))
            self.report["throttleRestored"] = unreal.SystemLibrary.get_console_variable_int_value("Slate.bAllowThrottling") == self.old_throttle
            self.report["savedMapsUnchanged"] = all(file_hash(map_file(asset)) == value for asset, value in self.hashes.items())
            assert self.report["savedMapsUnchanged"], "A saved map changed during capture"
        except Exception as restore_error:
            restore_errors.append(str(restore_error))
        if restore_errors:
            self.report["status"] = "failed_restoration_requires_review"
            self.report["restoreErrors"] = restore_errors
        self.event("finished")
        unreal.log("KOTEL_DETAIL_CAPTURE_FINISHED " + str(self.report_path))


# Explicit opt-in avoids changing any viewport when merely importing this file.
comparison = None

def start(review_map_path, dedicated_editor=False):
    global comparison
    assert not comparison or not comparison.active, "Capture already active"
    comparison = Comparison()
    comparison.begin(review_map_path,dedicated_editor=dedicated_editor)
    return str(comparison.report_path)

if __name__ == "__main__":
    previous = sys.modules.get(MODULE_NAME)
    assert not previous or not getattr(getattr(previous, "comparison", None), "active", False)
    module_spec = importlib.util.spec_from_file_location(MODULE_NAME, __file__)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[MODULE_NAME] = module
    module_spec.loader.exec_module(module)
    unreal.log("Loaded Kotel detail capture. Separate editor only: import mikdash_kotel_detail_capture as p; p.start(review_map_path, dedicated_editor=True)")
