"""Finite nine-view native release capture of the combined Walkthrough map; no map/material/light changes.

Recipe (proven by Codex captures on 2026-09-07, see receipts under SourceAssets/visual-review/
sanctuary-polish-capture-8a38633655, atmosphere-comparison-3b69314abc and logs
C:/Mikdash/Working-5.8/Sanctuary-Polish-Capture-02.log, Atmosphere-Capture-01.log):
  * Process: dedicated GUI UnrealEditor.exe with the real D3D12 RHI (NOT UnrealEditor-Cmd,
    NOT -nullrhi), target map on the command line, -ExecCmds="py <runner>" -unattended -NoSplash.
    -ExecCmds keeps the editor alive until quit_editor(); -ExecutePythonScript may quit before
    Slate tick callbacks finish (HANDOFF-FOR-CLAUDE-CODE.md, takeover boundary).
  * API: LevelEditorSubsystem (FOV 75, game view on, EditorInvalidateViewports each tick),
    UnrealEditorSubsystem.Set/GetLevelViewportCameraInfo, Slate.bAllowThrottling 0,
    AutomationLibrary.finish_loading_before_screenshot() as the LOADING BARRIER, then a rendered
    warmup of >=45 s and >=120 Slate ticks, then AutomationLibrary.take_high_res_screenshot
    (1920x1080, camera=None, force_game_view=False) polled through UAutomationEditorTask.is_task_done.
  * Ordering matters: the barrier ran AFTER camera placement and BEFORE the warmup clock. The
    first barrier took 20.75 s (texture/shader compilation); earlier gray first views happened
    when the warmup started before loading finished (HANDOFF release sequence step 4).

Additions for release review (this script only):
  * Per-view failures are RECORDED, not fatal: the run continues to the next view and the
    receipt (receipt.json) is rewritten after every event so partial output survives.
  * A global barrier runs once after map load, then a per-view barrier after each camera move.
  * Each PNG is decoded (pure Python) and sampled; a near-uniform frame (luma stdev < 4) is
    flagged flatFrameSuspect and retried once after another barrier + warmup.
  * Ground-dependent views (outer court, Kotel, Mount approach, bus) trace the actual floor with
    the Pawn profile; a failed trace is recorded and a documented fallback Z is used, or the
    view is skipped when no honest fallback exists (bus).

Run only in a separate capture editor, never the user's play editor. Explicit
start(dedicated_editor=True). Total watchdog 1800 s. Technical viewpoints, not access authorizations.
"""
import hashlib
import importlib.util
import json
import math
import struct
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

import unreal


MODULE_NAME = "mikdash_release_capture_views"
ROOT = Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
MAP = "/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough"
RESOLUTION = (1920, 1080)
FOV_DEGREES = 75.0
WARMUP_SECONDS = 45.0
MIN_SLATE_TICKS = 120
CAPTURE_TIMEOUT_SECONDS = 90.0
WATCHDOG_SECONDS = 1800.0
FLAT_FRAME_LUMA_STDEV = 4.0
MAX_FLAT_RETRIES = 1
EYE_HEIGHT_CM = 168.0

# Known coordinates (cm, Unreal). Sources noted per view in build_views().
ARON_ORIGIN = (-6200.0, 0.0, 925.0)          # shared Aron origin, yaw 90 (HANDOFF keruvim section)
KERUVIM_COVER_TOP_LOCAL = 83.3333            # vessels-review/KeruvimStudyV1/placement-spec.json
KERUVIM_TOP_LOCAL = 193.6667                 # HANDOFF local bounds max Z
SPAWN_XY = (2100.0, 0.0)                     # Mikdash_PlayerStart; inner court floor top 500
INNER_COURT_FLOOR_TOP = 500.0                # SM_0130_floor_Inner_court_clear_floor
OUTER_COURT_XY = (4974.0, 0.0)               # requested outer court position (pawn centre Z 398)
OUTER_COURT_FLOOR_TOP = 300.0                # SM_0129_floor_Outer_court_floor
HEIKHAL_WEST = (-4000.0, 0.0, 1093.0)        # proven Gold/Polish baseline camera, yaw 180
PLATFORM_TOP_Z = 0.0                         # mount-platform-design.json levels.platformTopZcm
OUTER_E_THRESHOLD_X = 8100.0                 # SM_0177_architecture_Outer_E_threshold max X
BUS_XY = (-23101.764984, 36185.432518)       # HANDOFF bus candidate; Z UNKNOWN, must be traced
BUS_YAW = -60.07867649
EXTERIOR_WIDE = ((30000.0, 30000.0, 20000.0), -25.0, -135.0)   # previously used exterior wide
OVERHEAD_CITY = ((37550.0, 28350.0, 34479.999923706055), (550.0, 0.0, 3064.9999618530273))
# Kotel: longest west-facing face (edge 0) from kotel-detail/KotelStoneV1/manifest.json
KOTEL_FACE_A = (-15127.514984215617, 11907.932517753074)
KOTEL_FACE_B = (-14450.014984215613, 15836.432517753074)
KOTEL_FACE_NORMAL = (-0.9854528733045355, 0.1699489173129251)
KOTEL_WALL_Z = (-1399.695, 600.305)          # sourceBase boundsCm Z range
KOTEL_PLAZA_FALLBACK_Z = -1079.42            # mount-platform-design.json levels.plazaCentre
KOTEL_OVERLAY_TAG = "KotelStoneV1OverlayReview"


def map_file(asset):
    assert asset.startswith("/Game/")
    return ROOT / "Content" / (asset[len("/Game/"):] + ".umap")


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def look_at(position, target):
    dx, dy, dz = [target[i] - position[i] for i in range(3)]
    return (math.degrees(math.atan2(dz, math.hypot(dx, dy))), math.degrees(math.atan2(dy, dx)))


def png_luma_stats(data, max_seconds=40.0):
    """Decode an 8-bit non-interlaced RGB/RGBA PNG and sample luma on a grid.

    Returns a dict with mean/stdev or a 'skipped' reason. Pure Python; bounded by max_seconds.
    """
    started = time.monotonic()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return {"skipped": "not_png"}
    pos, width, height, depth, color, interlace, idat = 8, None, None, None, None, None, []
    while pos + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height, depth, color, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
        pos += 12 + length
    if depth != 8 or color not in (2, 6) or interlace != 0:
        return {"skipped": "unsupported_png_layout", "depth": depth, "colorType": color, "interlace": interlace}
    channels = 3 if color == 2 else 4
    stride = width * channels
    raw = zlib.decompress(b"".join(idat))
    prev = bytearray(stride)
    rows = []
    offset = 0
    for _ in range(height):
        if time.monotonic() - started > max_seconds:
            return {"skipped": "decode_time_budget_exceeded", "rowsDecoded": len(rows)}
        filter_type = raw[offset]
        line = bytearray(raw[offset + 1:offset + 1 + stride])
        offset += 1 + stride
        if filter_type == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 255
        elif filter_type == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif filter_type == 3:
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif filter_type == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                b = prev[i]
                c = prev[i - channels] if i >= channels else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 255
        elif filter_type != 0:
            return {"skipped": "unknown_png_filter", "filter": filter_type}
        rows.append(line)
        prev = line
    samples = []
    step_x, step_y = max(1, width // 64), max(1, height // 36)
    for y in range(0, height, step_y):
        row = rows[y]
        for x in range(0, width, step_x):
            i = x * channels
            samples.append(0.299 * row[i] + 0.587 * row[i + 1] + 0.114 * row[i + 2])
    mean = sum(samples) / len(samples)
    stdev = math.sqrt(sum((s - mean) ** 2 for s in samples) / len(samples))
    return {"sampleCount": len(samples), "lumaMean": round(mean, 2), "lumaStdev": round(stdev, 2),
            "lumaMin": round(min(samples), 1), "lumaMax": round(max(samples), 1),
            "decodeSeconds": round(time.monotonic() - started, 2)}


class ReleaseCapture:
    def __init__(self):
        self.editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        self.level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        self.actors_api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.handle = None
        self.active = False
        self.busy = False
        self.task = None
        self.index = -1
        self.phase = "initializing"
        self.started = time.monotonic()
        self.phase_started = self.started
        self.ticks = 0
        self.retry_count = 0

    # ------------------------------------------------------------------ receipt
    def write(self):
        self.report_path.write_text(json.dumps(self.report, indent=2, default=str) + "\n", encoding="utf-8")

    def event(self, label, **extra):
        entry = {"event": label, "elapsedSeconds": round(time.monotonic() - self.started, 2)}
        entry.update(extra)
        self.report["events"].append(entry)
        self.write()

    def failure(self, view_id, stage, message):
        self.report["failures"].append({"view": view_id, "stage": stage, "error": str(message),
                                        "elapsedSeconds": round(time.monotonic() - self.started, 2)})
        unreal.log_warning("RELEASE_CAPTURE_VIEW_FAILURE %s/%s: %s" % (view_id, stage, message))
        self.write()

    # ------------------------------------------------------------------ world helpers
    def world(self):
        return self.editor.get_editor_world()

    def trace_ground(self, x, y, z_top, z_bottom, ignore=()):
        hit = unreal.SystemLibrary.line_trace_single_by_profile(
            world_context_object=self.world(), start=unreal.Vector(x, y, z_top), end=unreal.Vector(x, y, z_bottom),
            profile_name="Pawn", trace_complex=True, actors_to_ignore=list(ignore),
            draw_debug_type=unreal.DrawDebugTrace.NONE, ignore_self=False)
        if not hit:
            return None
        # HitResult fields are not exposed as properties in UE 5.8 Python; use
        # BreakHitResult: [0] blocking, [4] location, [5] impact point,
        # [7] impact normal, [9] hit actor (same layout run-release-pie-floor-probe.py used).
        # In -ExecCmds launches GameplayStatics.break_hit_result is not bound; the
        # struct's to_dict() is. Try both.
        point = normal = None
        actor = "unavailable"
        if hasattr(unreal.GameplayStatics, "break_hit_result"):
            split = unreal.GameplayStatics.break_hit_result(hit)
            point, normal = split[5], split[7]
            try:
                actor = split[9].get_actor_label() if split[9] else None
            except Exception:
                pass
        else:
            data = hit.to_dict()
            lowered = {str(k).lower(): v for k, v in data.items()}
            point = lowered.get("impact_point") or lowered.get("impactpoint") or lowered.get("location")
            normal = lowered.get("impact_normal") or lowered.get("impactnormal") or lowered.get("normal")
            hit_actor = lowered.get("hit_actor") or lowered.get("actor") or lowered.get("hitactor")
            try:
                actor = hit_actor.get_actor_label() if hit_actor else None
            except Exception:
                pass
            if point is None:
                raise RuntimeError("HitResult.to_dict keys: " + ",".join(sorted(str(k) for k in data.keys())))
        return {"point": [point.x, point.y, point.z], "normalZ": round(normal.z, 4) if normal is not None else None, "actor": actor}

    def sightline_blocked(self, position, target, ignore=()):
        hit = unreal.SystemLibrary.line_trace_single_by_profile(
            world_context_object=self.world(), start=unreal.Vector(*position), end=unreal.Vector(*target),
            profile_name="Pawn", trace_complex=True, actors_to_ignore=list(ignore),
            draw_debug_type=unreal.DrawDebugTrace.NONE, ignore_self=False)
        return hit is not None

    def camera_clearance(self, position, ignore=()):
        location = unreal.Vector(*position)
        hit = unreal.SystemLibrary.sphere_trace_single_by_profile(
            world_context_object=self.world(), start=location, end=location + unreal.Vector(0, 0, 1),
            radius=10.0, profile_name="Pawn", trace_complex=False, actors_to_ignore=list(ignore),
            draw_debug_type=unreal.DrawDebugTrace.NONE, ignore_self=True)
        return hit is None

    def inventory(self):
        """Snapshot actors once (labels, tags, mesh paths, locations); never recompute per comparison."""
        snapshot = []
        for actor in self.actors_api.get_all_level_actors():
            try:
                label = actor.get_actor_label()
                tags = [str(t) for t in actor.get_editor_property("tags")]
                loc = actor.get_actor_location()
                meshes = []
                for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
                    mesh = comp.static_mesh
                    if mesh:
                        meshes.append(mesh.get_path_name().split(".")[0])
                for comp in actor.get_components_by_class(unreal.SkeletalMeshComponent):
                    mesh = comp.get_editor_property("skeletal_mesh_asset")
                    if mesh:
                        meshes.append(mesh.get_path_name().split(".")[0])
                snapshot.append({"actor": actor, "label": label, "tags": tags,
                                 "location": [loc.x, loc.y, loc.z], "meshes": meshes})
            except Exception as error:  # a single odd actor must not abort the inventory
                self.failure("inventory", "actor_snapshot", error)
        return snapshot

    # ------------------------------------------------------------------ view planning
    def build_views(self):
        inv = self.inventory()

        def find(predicate):
            return [item for item in inv if predicate(item)]

        aron_items = find(lambda i: i["label"].startswith("REVIEW_AronIncomplete_") or any("AronStudyV1" in m for m in i["meshes"]))
        keruvim_items = find(lambda i: any("KeruvimStudyV1" in m for m in i["meshes"]))
        pilgrim_items = find(lambda i: any("/PilgrimRig" in m or "Pilgrim" in m for m in i["meshes"]) or any("ilgrim" in t for t in i["tags"]))
        bus_items = find(lambda i: any("/ArrivalReview/TransitV2/Bus/" in m for m in i["meshes"]))
        kotel_overlay_items = find(lambda i: KOTEL_OVERLAY_TAG in i["tags"] or any("/KotelStoneV1/" in m and "SM_KotelFace_Tint" in m for m in i["meshes"]))
        self.report["sceneInventory"] = {
            "actorCount": len(inv),
            "aronParts": len(aron_items), "keruvimActors": len(keruvim_items),
            "pilgrimActors": len(pilgrim_items), "busActors": len(bus_items),
            "kotelOverlayActors": len(kotel_overlay_items),
            "pilgrimLocations": [i["location"] for i in pilgrim_items][:40],
            "busLocations": [i["location"] for i in bus_items][:40],
            "note": "Counts are what the saved map contains at capture time. Zero pilgrims/keruvim/bus/overlay means release step 2 placement had not been done in this map; the view is still captured.",
        }

        # (a) exterior wide arrival: previously used exterior wide camera.
        def view_a():
            (pos, pitch, yaw) = EXTERIOR_WIDE
            return {"id": "a_exterior_wide_arrival", "position": list(pos), "pitch": pitch, "yaw": yaw,
                    "basis": "Previously used exterior wide camera [30000,30000,20000] pitch -25 yaw -135 toward the courtyard origin."}

        # (b) courtyard from spawn looking west at eye height.
        def view_b():
            return {"id": "b_courtyard_spawn_west", "position": [SPAWN_XY[0], SPAWN_XY[1], INNER_COURT_FLOOR_TOP + EYE_HEIGHT_CM],
                    "pitch": 0.0, "yaw": 180.0,
                    "basis": "Mikdash_PlayerStart [2100,0] (pawn centre Z 598); inner court floor top 500 + 168 eye height; west is UE -X."}

        # (c) outer court with pilgrims at eye height; trace the real floor, aim at pilgrims if any.
        def view_c():
            view_id = "c_outer_court_pilgrims"
            ground = self.trace_ground(OUTER_COURT_XY[0], OUTER_COURT_XY[1], 900.0, -200.0)
            floor_z = ground["point"][2] if ground else OUTER_COURT_FLOOR_TOP
            position = [OUTER_COURT_XY[0], OUTER_COURT_XY[1], floor_z + EYE_HEIGHT_CM]
            view = {"id": view_id, "position": position, "groundTrace": ground,
                    "basis": "Requested outer court point [4974,0] (pawn centre Z 398); outer court floor top 300 + 168 eye height."}
            if ground is None:
                self.failure(view_id, "ground_trace", "No Pawn-profile floor hit at outer court point; used manifest floor 300.")
            if pilgrim_items:
                centroid = [sum(i["location"][k] for i in pilgrim_items) / len(pilgrim_items) for k in range(3)]
                target = [centroid[0], centroid[1], floor_z + 120.0]
                view["target"] = target
                view["pitch"], view["yaw"] = look_at(position, target)
                view["aim"] = "centroid of %d pilgrim actors" % len(pilgrim_items)
            else:
                view.update(pitch=0.0, yaw=180.0, aim="no pilgrim actors found; looking west toward the inner court east gate")
            return view

        # (d) Heikhal interior looking west (proven camera).
        def view_d():
            return {"id": "d_heikhal_west_vessels", "position": list(HEIKHAL_WEST), "pitch": 0.0, "yaw": 180.0,
                    "basis": "Proven Gold/Polish baseline: Heichal floor top 925 + 168, 400 cm inside the eastern floor edge; menorah [-4900,300], shulchan [-4900,-300], incense altar [-4500,0]."}

        # (e) Kodesh close on Aron and keruvim.
        def view_e():
            view_id = "e_kodesh_aron_keruvim"
            position = [ARON_ORIGIN[0] + 350.0, ARON_ORIGIN[1] - 140.0, ARON_ORIGIN[2] + EYE_HEIGHT_CM]
            target = [ARON_ORIGIN[0], ARON_ORIGIN[1], ARON_ORIGIN[2] + (KERUVIM_COVER_TOP_LOCAL + KERUVIM_TOP_LOCAL) / 2.0]
            pitch, yaw = look_at(position, target)
            ignore = [i["actor"] for i in aron_items + keruvim_items]
            view = {"id": view_id, "position": position, "target": target, "pitch": pitch, "yaw": yaw,
                    "basis": "Aron origin [-6200,0,925] yaw 90; camera 350 cm east/140 cm north inside Kodesh floor X[-6700,-5700]; target mid-height of keruvim (cover top +83.3 to +193.7 local).",
                    "sightlineBlocked": self.sightline_blocked(position, target, ignore)}
            if view["sightlineBlocked"]:
                self.failure(view_id, "sightline", "Kodesh sightline to Aron blocked by scene collision (not Aron/keruvim); captured anyway for review.")
            return view

        # (f) Kotel ground-level detail: longest west-facing face, outward normal offset, real ground trace.
        def view_f():
            view_id = "f_kotel_ground_detail"
            mid = [(KOTEL_FACE_A[0] + KOTEL_FACE_B[0]) / 2.0, (KOTEL_FACE_A[1] + KOTEL_FACE_B[1]) / 2.0]
            distance = 1000.0   # kotel-detail review-workflow.json basis: outward normal offset 1000 cm
            xy = [mid[0] + KOTEL_FACE_NORMAL[0] * distance, mid[1] + KOTEL_FACE_NORMAL[1] * distance]
            ignore = [i["actor"] for i in kotel_overlay_items]
            ground = self.trace_ground(xy[0], xy[1], KOTEL_WALL_Z[1] + 500.0, KOTEL_WALL_Z[0] - 1500.0, ignore)
            floor_z = ground["point"][2] if ground else KOTEL_PLAZA_FALLBACK_Z
            position = [xy[0], xy[1], floor_z + EYE_HEIGHT_CM]
            target = [mid[0] + KOTEL_FACE_NORMAL[0] * 5.0, mid[1] + KOTEL_FACE_NORMAL[1] * 5.0, position[2] + 250.0]
            pitch, yaw = look_at(position, target)
            view = {"id": view_id, "position": position, "target": target, "pitch": pitch, "yaw": yaw,
                    "groundTrace": ground, "faceMidpoint": mid, "faceNormal": list(KOTEL_FACE_NORMAL),
                    "basis": "kotel-detail manifest edge 0 (3986 cm, west-facing) midpoint + outward normal x 600 cm; eye = traced ground + 168; slight upward pitch to include courses."}
            if ground is None:
                self.failure(view_id, "ground_trace", "No floor west of the Kotel face; used plaza-centre terrain fallback Z %.2f." % KOTEL_PLAZA_FALLBACK_Z)
            elif ground["normalZ"] < 0.9:
                self.failure(view_id, "ground_slope", "Ground normal Z %.3f is sloped; eye height may be off." % ground["normalZ"])
            if not (KOTEL_WALL_Z[0] + 20 < position[2] < KOTEL_WALL_Z[1] - 20):
                self.failure(view_id, "eye_height_outside_face", "Eye Z %.1f outside modeled Kotel face Z range %s." % (position[2], KOTEL_WALL_Z))
            return view

        # (g) Mount platform approach toward the outer eastern gate.
        def view_g():
            view_id = "g_mount_platform_approach"
            approach_xy = (11500.0, -300.0)
            ground = self.trace_ground(approach_xy[0], approach_xy[1], PLATFORM_TOP_Z + 800.0, PLATFORM_TOP_Z - 3000.0)
            floor_z = ground["point"][2] if ground else PLATFORM_TOP_Z
            position = [approach_xy[0], approach_xy[1], floor_z + EYE_HEIGHT_CM]
            target = [OUTER_E_THRESHOLD_X, 0.0, floor_z + 1100.0]
            pitch, yaw = look_at(position, target)
            view = {"id": view_id, "position": position, "target": target, "pitch": pitch, "yaw": yaw,
                    "groundTrace": ground,
                    "basis": "Future Mount platform deck top Z 0 (mount-platform-design.json); route 'Platform to measured outer eastern gate' begins at [10000,0,0]; camera 34 m east of the Outer E threshold looking west up the 12 gateway stairs."}
            if ground is None:
                self.failure(view_id, "ground_trace", "No platform deck hit at approach point; used design deck Z 0.")
            return view

        # (h) bus at street level: Z unknown, trace it; skip honestly if nothing is there.
        def view_h():
            view_id = "h_bus_street_level"
            heading = math.radians(BUS_YAW)
            forward = (math.cos(heading), math.sin(heading))
            door_side = (-math.sin(heading), math.cos(heading))   # bus local +Y is the door side
            cam_xy = [BUS_XY[0] + door_side[0] * 1400.0 + forward[0] * 400.0,
                      BUS_XY[1] + door_side[1] * 1400.0 + forward[1] * 400.0]
            ignore = [i["actor"] for i in bus_items]
            bus_ground = self.trace_ground(BUS_XY[0], BUS_XY[1], 6000.0, -9000.0, ignore)
            cam_ground = self.trace_ground(cam_xy[0], cam_xy[1], 6000.0, -9000.0, ignore)
            view = {"id": view_id, "busCandidateXY": list(BUS_XY), "busYaw": BUS_YAW,
                    "busGroundTrace": bus_ground, "cameraGroundTrace": cam_ground, "busActorsFound": len(bus_items),
                    "basis": "HANDOFF TransitV2 bus candidate XY on mapped Batei Mahase road, yaw -60.08; camera 14 m off the door side, 4 m forward, at traced street level + 168."}
            if cam_ground is None and bus_items:
                cam_ground = {"point": [cam_xy[0], cam_xy[1], bus_items[0]["location"][2]], "normalZ": None, "actor": "fallback: bus actor Z"}
                self.failure(view_id, "ground_trace", "No street hit at camera point; fell back to placed bus actor Z.")
            if cam_ground is None:
                self.failure(view_id, "ground_trace", "No street surface at bus site and no bus actor: Z unknown, view skipped rather than invented.")
                view.update(skipped=True, position=None, pitch=None, yaw=None)
                return view
            position = [cam_xy[0], cam_xy[1], cam_ground["point"][2] + EYE_HEIGHT_CM]
            if bus_items:
                bus_z = bus_items[0]["location"][2]
            elif bus_ground:
                bus_z = bus_ground["point"][2]
            else:
                bus_z = cam_ground["point"][2]
            target = [BUS_XY[0], BUS_XY[1], bus_z + 180.0]
            pitch, yaw = look_at(position, target)
            view.update(position=position, target=target, pitch=pitch, yaw=yaw)
            return view

        # (i) overhead city: proven Jerusalem-context 'overall' camera (produced a PNG on 2026-09-07).
        def view_i():
            pos, target = OVERHEAD_CITY
            pitch, yaw = look_at(pos, target)
            return {"id": "i_overhead_city", "position": list(pos), "target": list(target), "pitch": pitch, "yaw": yaw,
                    "basis": "capture_jerusalem_context.py 'overall': architecture bounds max + 1.5/1.0/1.5 spans, looking at the architecture centre."}

        planners = [("a_exterior_wide_arrival", view_a), ("b_courtyard_spawn_west", view_b),
                    ("c_outer_court_pilgrims", view_c), ("d_heikhal_west_vessels", view_d),
                    ("e_kodesh_aron_keruvim", view_e), ("f_kotel_ground_detail", view_f),
                    ("g_mount_platform_approach", view_g), ("h_bus_street_level", view_h),
                    ("i_overhead_city", view_i)]
        views = []
        for view_id, builder in planners:
            try:
                view = builder()
                assert view["id"] == view_id
                if not view.get("skipped"):
                    assert view.get("position") is not None and view.get("pitch") is not None and view.get("yaw") is not None
                views.append(view)
            except Exception as error:   # one bad plan must not cost the other eight captures
                self.failure(view_id, "plan_view", error)
                views.append({"id": view_id, "skipped": True, "planError": str(error)})
        return views

    # ------------------------------------------------------------------ lifecycle
    def begin(self, dedicated_editor=False):
        assert dedicated_editor is True, "Root must explicitly confirm this is the separate capture editor"
        assert Path(unreal.Paths.project_dir()).resolve() == ROOT
        assert not self.editor.get_game_world(), "Stop PIE before capture"
        assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), "Preserve unsaved maps first"
        assert map_file(MAP).exists(), "Combined map file missing"
        self.map_hash = file_hash(map_file(MAP))
        self.old_map = self.world().get_path_name().split(".")[0]
        self.old_camera = self.editor.get_level_viewport_camera_info()
        assert self.old_camera, "No usable GUI level viewport (was the editor started with -nullrhi or as a commandlet?)"
        self.viewport = self.level.get_active_viewport_config_key()
        self.old_fov = self.level.get_level_viewport_fov(self.viewport)
        assert self.old_fov is not None
        self.old_game_view = self.level.editor_get_game_view(self.viewport)
        self.old_throttle = unreal.SystemLibrary.get_console_variable_int_value("Slate.bAllowThrottling")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.folder = ROOT / "SourceAssets/visual-review" / ("release-capture-" + stamp)
        self.folder.mkdir(exist_ok=False)
        self.report_path = self.folder / "receipt.json"
        self.report = {
            "status": "running", "map": MAP, "mapSha256": self.map_hash, "startedUtc": stamp,
            "engineVersion": unreal.SystemLibrary.get_engine_version(),
            "process": "dedicated GUI UnrealEditor.exe, real RHI (no -nullrhi), -ExecCmds py runner",
            "resolution": RESOLUTION, "fovDegrees": FOV_DEGREES,
            "warmupSecondsPerView": WARMUP_SECONDS, "minimumSlateTicksPerView": MIN_SLATE_TICKS,
            "captureTimeoutSeconds": CAPTURE_TIMEOUT_SECONDS, "watchdogSeconds": WATCHDOG_SECONDS,
            "readinessPolicy": "Global finish_loading_before_screenshot after map load; per view: set camera, finish_loading_before_screenshot (loading barrier), then >=45 s and >=120 Slate ticks rendered warmup, then take_high_res_screenshot. Flat frames (luma stdev < %.1f) retried once." % FLAT_FRAME_LUMA_STDEV,
            "streamingPoolSizeMB": unreal.SystemLibrary.get_console_variable_int_value("r.Streaming.PoolSize"),
            "views": [], "viewTiming": [], "captures": [], "failures": [], "events": [],
            "mapSaved": False, "visualAcceptance": "PENDING",
            "limits": "Native technical stills of the saved combined map. No access authorization, no automatic image-quality approval, no motion/wind/packaged proof. Zero-count inventory entries mean those assets were not yet placed in this map.",
        }
        self.write()
        self.active = True
        try:
            unreal.SystemLibrary.execute_console_command(self.world(), "Slate.bAllowThrottling 0")
            if self.old_map != MAP:
                self.event("loading_map")
                assert self.level.load_level(MAP), "Map load failed"
            assert self.world().get_path_name().split(".")[0] == MAP
            assert not self.editor.get_game_world()
            assert self.level.get_active_viewport_config_key() == self.viewport, "Active viewport changed"
            self.level.set_level_viewport_fov(FOV_DEGREES, self.viewport)
            self.level.editor_set_game_view(True, self.viewport)
            self.event("global_barrier_started")
            barrier_started = time.monotonic()
            unreal.AutomationLibrary.finish_loading_before_screenshot()
            self.report["globalBarrierSeconds"] = round(time.monotonic() - barrier_started, 3)
            self.event("global_barrier_finished", seconds=self.report["globalBarrierSeconds"])
            self.views = self.build_views()
            self.report["views"] = self.views
            self.write()
            self.handle = unreal.register_slate_post_tick_callback(self.tick)
            self.next_view()
        except Exception as error:
            self.finish("failed_before_first_view", str(error))
            raise

    def next_view(self):
        self.index += 1
        self.retry_count = 0
        if self.index >= len(self.views):
            self.finish("captured_restored_requires_visual_review")
            return
        self.view = self.views[self.index]
        if self.view.get("skipped"):
            self.event("skipped_" + self.view["id"])
            self.next_view()
            return
        self.filename = self.folder / (self.view["id"] + ".png")
        self.arm_view()

    def arm_view(self):
        """Place camera, run the loading barrier, then start the warmup clock. Per-view errors are recorded."""
        previous_busy = self.busy
        self.busy = True   # loading can pump Slate; block reentrant ticks
        try:
            assert not self.editor.get_game_world(), "PIE started during capture"
            assert self.level.get_active_viewport_config_key() == self.viewport, "Active viewport changed"
            self.level.set_level_viewport_fov(FOV_DEGREES, self.viewport)
            self.level.editor_set_game_view(True, self.viewport)
            position = self.view["position"]
            self.view["cameraClearance"] = self.camera_clearance(position)
            if not self.view["cameraClearance"]:
                self.failure(self.view["id"], "camera_clearance", "10 cm Pawn sphere at camera hits collision; frame may be inside geometry.")
            self.editor.set_level_viewport_camera_info(
                unreal.Vector(*position), unreal.Rotator(pitch=self.view["pitch"], yaw=self.view["yaw"], roll=0.0))
            assert not self.filename.exists(), "Output file already exists: " + str(self.filename)
            self.phase = "readiness"
            barrier_started = time.monotonic()
            self.view_timing = {"view": self.view["id"], "file": self.filename.name, "attempt": self.retry_count + 1,
                                "barrierStartedSeconds": round(barrier_started - self.started, 3)}
            self.report["viewTiming"].append(self.view_timing)
            self.event("readiness_" + self.filename.stem)
            unreal.AutomationLibrary.finish_loading_before_screenshot()
            self.view_timing["barrierElapsedSeconds"] = round(time.monotonic() - barrier_started, 3)
            self.phase = "warming"
            self.phase_started = time.monotonic()
            self.view_timing["warmupStartedSeconds"] = round(self.phase_started - self.started, 3)
            self.ticks = 0
            self.task = None
            self.event("warming_" + self.filename.stem)
        except Exception as error:
            self.failure(self.view["id"], "arm_view", error)
            self.phase = "advance"
        finally:
            self.busy = previous_busy

    def tick(self, delta_seconds):
        if not self.active or self.busy:
            return
        self.busy = True
        try:
            now = time.monotonic()
            assert now - self.started < WATCHDOG_SECONDS, "Capture watchdog expired"
            assert not self.editor.get_game_world(), "PIE started during capture"
            assert self.level.get_active_viewport_config_key() == self.viewport, "Active viewport changed"
            assert self.world().get_path_name().split(".")[0] == MAP, "Map changed outside capture"
            self.level.editor_invalidate_viewports()   # force redraws; realtime setting untouched
            self.ticks += 1
            if self.phase == "advance":
                self.next_view()
            elif self.phase == "warming" and now - self.phase_started >= WARMUP_SECONDS and self.ticks >= MIN_SLATE_TICKS:
                self.request_screenshot(now)
            elif self.phase == "capturing":
                self.poll_screenshot(now)
        except Exception as error:
            self.finish("failed", str(error))
            unreal.log_error("RELEASE_CAPTURE_VIEWS_FAILED: " + str(error))
        finally:
            self.busy = False

    def request_screenshot(self, now):
        try:
            camera = self.editor.get_level_viewport_camera_info()
            assert camera and (camera[0] - unreal.Vector(*self.view["position"])).length() < 0.1, "Camera moved during warmup"
            yaw_error = (camera[1].yaw - self.view["yaw"] + 180.0) % 360.0 - 180.0
            assert abs(yaw_error) < 0.1 and abs(camera[1].pitch - self.view["pitch"]) < 0.1 and abs(camera[1].roll) < 0.1, "Camera rotation changed"
            self.view_timing["warmupElapsedSeconds"] = round(now - self.phase_started, 3)
            self.view_timing["warmupSlateTicks"] = self.ticks
            call_started = time.monotonic()
            self.task = unreal.AutomationLibrary.take_high_res_screenshot(
                RESOLUTION[0], RESOLUTION[1], str(self.filename), camera=None,
                mask_enabled=False, capture_hdr=False, delay=0.0, force_game_view=False)
            self.view_timing["screenshotCallElapsedSeconds"] = round(time.monotonic() - call_started, 3)
            assert self.task and self.task.is_valid_task(), "Screenshot task was not configured"
            self.phase = "capturing"
            self.phase_started = time.monotonic()
            self.event("requested_" + self.filename.stem)
        except Exception as error:
            self.failure(self.view["id"], "request_screenshot", error)
            self.phase = "advance"

    def poll_screenshot(self, now):
        if now - self.phase_started >= CAPTURE_TIMEOUT_SECONDS:
            self.failure(self.view["id"], "capture_timeout", "Screenshot task/file did not complete within %.0f s" % CAPTURE_TIMEOUT_SECONDS)
            self.phase = "advance"
            return
        if not (self.task.is_task_done() and self.filename.exists()):
            return
        data = self.filename.read_bytes()
        record = {"view": self.view["id"], "file": str(self.filename), "bytes": len(data),
                  "sha256": hashlib.sha256(data).hexdigest(), "nativeTaskDone": True,
                  "attempt": self.retry_count + 1, "camera": {k: self.view.get(k) for k in ("position", "pitch", "yaw", "target")},
                  "timing": dict(self.view_timing)}
        try:
            assert data[:8] == b"\x89PNG\r\n\x1a\n", "Native screenshot is not PNG"
            width, height = struct.unpack(">II", data[16:24])
            record["dimensions"] = [width, height]
            assert (width, height) == RESOLUTION, "Screenshot resolution mismatch %sx%s" % (width, height)
            record["verifiedFile"] = True
        except Exception as error:
            record["verifiedFile"] = False
            self.failure(self.view["id"], "verify_png", error)
        try:
            stats = png_luma_stats(data)
        except Exception as error:
            stats = {"skipped": "decode_error: " + str(error)}
        record["lumaSample"] = stats
        flat = bool(stats.get("lumaStdev") is not None and stats["lumaStdev"] < FLAT_FRAME_LUMA_STDEV)
        record["flatFrameSuspect"] = flat
        self.report["captures"].append(record)
        self.event("captured_" + self.filename.stem, flatFrameSuspect=flat)
        if flat and self.retry_count < MAX_FLAT_RETRIES:
            self.failure(self.view["id"], "flat_frame", "Luma stdev %.2f < %.1f (gray/uniform frame suspected); retrying after another barrier and warmup." % (stats["lumaStdev"], FLAT_FRAME_LUMA_STDEV))
            self.retry_count += 1
            self.filename = self.folder / ("%s_retry%d.png" % (self.view["id"], self.retry_count))
            self.arm_view()
            return
        self.next_view()

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
        verified = [c for c in self.report["captures"] if c.get("verifiedFile") and not c.get("flatFrameSuspect")]
        planned = [v for v in self.report["views"] if not v.get("skipped")]
        self.report["summary"] = {"viewsPlanned": len(planned), "viewsSkipped": len(self.report["views"]) - len(planned),
                                  "filesVerifiedNotFlat": len(verified), "failureCount": len(self.report["failures"])}
        if status.startswith("captured") and len(verified) < len(planned):
            self.report["status"] = "partial_captures_requires_review"
        restore_errors = []
        try:
            if self.old_map != MAP:
                assert self.level.load_level(self.old_map), "Original view map reload failed"
            self.editor.set_level_viewport_camera_info(self.old_camera[0], self.old_camera[1])
            self.level.set_level_viewport_fov(self.old_fov, self.viewport)
            self.level.editor_set_game_view(self.old_game_view, self.viewport)
            self.report["originalCameraRestored"] = True
        except Exception as restore_error:
            restore_errors.append(str(restore_error))
        try:
            unreal.SystemLibrary.execute_console_command(self.world(), "Slate.bAllowThrottling " + str(self.old_throttle))
            self.report["throttleRestored"] = unreal.SystemLibrary.get_console_variable_int_value("Slate.bAllowThrottling") == self.old_throttle
            self.report["savedMapUnchanged"] = file_hash(map_file(MAP)) == self.map_hash
            assert self.report["savedMapUnchanged"], "The saved combined map changed during capture"
        except Exception as restore_error:
            restore_errors.append(str(restore_error))
        if restore_errors:
            self.report["status"] = "failed_restoration_requires_review"
            self.report["restoreErrors"] = restore_errors
        self.event("finished")
        unreal.log("RELEASE_CAPTURE_VIEWS_FINISHED %s status=%s" % (self.report_path, self.report["status"]))


# Explicit opt-in avoids changing any viewport when merely importing this file.
capture = None


def start(dedicated_editor=False):
    global capture
    assert not capture or not capture.active, "Capture already active"
    capture = ReleaseCapture()
    capture.begin(dedicated_editor=dedicated_editor)
    return str(capture.report_path)


def _finish_tick_quit(module):
    """Runner helper: quit the dedicated editor once the capture is inactive (receipt already written)."""
    state = {"handle": None}

    def finish_tick(delta):
        if module.capture is not None and not module.capture.active:
            unreal.unregister_slate_post_tick_callback(state["handle"])
            unreal.SystemLibrary.quit_editor()
    state["handle"] = unreal.register_slate_post_tick_callback(finish_tick)


if __name__ == "__main__":
    previous = sys.modules.get(MODULE_NAME)
    assert not previous or not getattr(getattr(previous, "capture", None), "active", False)
    module_spec = importlib.util.spec_from_file_location(MODULE_NAME, __file__)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[MODULE_NAME] = module
    module_spec.loader.exec_module(module)
    if "--dedicated-editor-run" in sys.argv[1:]:
        # Self-starting mode for: -ExecCmds="py <this file> --dedicated-editor-run" in a dedicated editor.
        try:
            module.start(dedicated_editor=True)
            module._finish_tick_quit(module)
        except Exception:
            unreal.SystemLibrary.quit_editor()
            raise
    else:
        unreal.log("Loaded release capture. Separate editor only: import mikdash_release_capture_views as r; r.start(dedicated_editor=True)")
