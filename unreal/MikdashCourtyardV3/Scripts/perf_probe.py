"""Bounded PIE performance probe for the combined Walkthrough map.

LIVE EDITOR WITH A REAL RHI ONLY. Frame timings are meaningless under -nullrhi and
nothing renders in a commandlet, so this follows the same launch mechanism the walking
probes use: a dedicated editor started ON the target map with -ExecCmds="py <this file>"
so the editor stays alive while the tick callbacks run, and the script quits the editor
itself when MIKDASH_PERF_QUIT_EDITOR=1. Do NOT use -ExecutePythonScript: it requests
editor exit as soon as this file returns, before the callbacks finish.

    "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough
      -ExecCmds="py C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/perf_probe.py"
      -unattended -NoSplash
      -abslog="C:/Mikdash/Working-5.8/Perf-Probe-01.log"

Run it SERIAL. This machine is an RTX 2070 with 16 GB and will not take two engine jobs.

What is actually measured, and what is not:
  * Frame time IS measured, from wall-clock deltas between slate post-tick callbacks
    while PIE is running with throttling disabled. That is the number the budget cares
    about.
  * Geometry counts are computed by walking the level, not sampled from the renderer.
    With Nanite enabled get_num_triangles(0) returns the FALLBACK count, so the triangle
    figure is a lower bound and is labelled as such in the receipt.
  * Draw calls and primitive counts are NOT measured. The engine exposes them through
    `stat scenerendering`, which writes to the log in a format that is not stable enough
    to parse into a pass/fail gate. The receipt records that they were not collected
    rather than reporting a fabricated number.
  * Process memory IS measured, through the Win32 API.

Configuration by environment variable, so the same file works from the editor console,
the `py` command, or -ExecCmds:
  MIKDASH_PERF_LIMIT_SECONDS   hard wall-clock limit, 30..180 (default 150)
  MIKDASH_PERF_SETTLE_SECONDS  discarded warm-up at each station (default 2.0)
  MIKDASH_PERF_HOLD_SECONDS    sampled dwell at each station (default 4.0)
  MIKDASH_PERF_QUIT_EDITOR     1 = quit the editor after the receipt (default 0)

Receipt: SourceAssets/perf-review/perf-probe-<UTC stamp>.json
"""

import ctypes
import ctypes.wintypes
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import unreal

ROOT = Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
TARGET_MAP = "/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough"
OUTPUT_DIR = ROOT / "SourceAssets/perf-review"

LIMIT_SECONDS = max(30.0, min(180.0, float(os.environ.get("MIKDASH_PERF_LIMIT_SECONDS", "150"))))
SETTLE_SECONDS = float(os.environ.get("MIKDASH_PERF_SETTLE_SECONDS", "2.0"))
HOLD_SECONDS = float(os.environ.get("MIKDASH_PERF_HOLD_SECONDS", "4.0"))
QUIT_EDITOR = os.environ.get("MIKDASH_PERF_QUIT_EDITOR", "0") == "1"

# Budget from PERFORMANCE-BUDGET.md. The plaza looks out over the whole modern city and
# is the heaviest view in the build, so it carries its own allowance.
BUDGET_MS = 16.7
BUDGET_MS_PLAZA = 22.0

# Stations are real coordinates taken from release receipts and probe routes, not
# invented. Each is (name, location, look-at yaw, budget).
STATIONS = [
    ("outer_court_east", unreal.Vector(4974.0, 0.0, 468.0), 180.0, BUDGET_MS),
    ("court_toward_sanctuary", unreal.Vector(2100.0, 0.0, 668.0), 180.0, BUDGET_MS),
    ("altar_approach", unreal.Vector(-3200.0, 0.0, 995.0), 180.0, BUDGET_MS),
    ("heikhal_doorway", unreal.Vector(-3600.0, 0.0, 995.0), 180.0, BUDGET_MS),
    ("menorah", unreal.Vector(-5100.0, 315.0, 995.0), 180.0, BUDGET_MS),
    ("golden_altar", unreal.Vector(-4650.0, 0.0, 995.0), 180.0, BUDGET_MS),
    ("paroches", unreal.Vector(-5450.0, 0.0, 995.0), 180.0, BUDGET_MS),
    ("mount_platform_deck", unreal.Vector(11500.0, -300.0, 70.0), 90.0, BUDGET_MS),
    ("plaza_over_city", unreal.Vector(11500.0, -300.0, 400.0), 270.0, BUDGET_MS_PLAZA),
]


def process_memory_mb():
    """Working set and private bytes of this process, through the Win32 API."""
    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.wintypes.DWORD),
            ("PageFaultCount", ctypes.wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]
    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(counters)
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    ok = False
    for dll, fn in ((ctypes.windll.kernel32, "K32GetProcessMemoryInfo"),
                    (ctypes.windll.psapi, "GetProcessMemoryInfo")):
        try:
            ok = bool(getattr(dll, fn)(handle, ctypes.byref(counters), counters.cb))
        except Exception:  # noqa: BLE001
            continue
        if ok:
            break
    if not ok:
        return {"workingSetMb": None, "privateMb": None, "peakWorkingSetMb": None}
    return {
        "workingSetMb": round(counters.WorkingSetSize / 1048576.0, 1),
        "privateMb": round(counters.PrivateUsage / 1048576.0, 1),
        "peakWorkingSetMb": round(counters.PeakWorkingSetSize / 1048576.0, 1),
    }


def count_geometry():
    """Static geometry census. A lower bound on triangles where Nanite is on."""
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    triangles = 0
    instances = 0
    static_meshes = 0
    hisms = 0
    nanite_meshes = 0
    seen = set()
    for actor in actors:
        for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = comp.get_editor_property("static_mesh")
            if not mesh:
                continue
            per_instance = 1
            if isinstance(comp, unreal.InstancedStaticMeshComponent):
                per_instance = comp.get_instance_count()
                hisms += 1
                instances += per_instance
            else:
                static_meshes += 1
            path = mesh.get_path_name()
            try:
                tris = mesh.get_num_triangles(0)
            except Exception:  # noqa: BLE001
                tris = 0
            if path not in seen:
                seen.add(path)
                try:
                    if mesh.get_editor_property("nanite_settings").enabled:
                        nanite_meshes += 1
                except Exception:  # noqa: BLE001
                    pass
            triangles += tris * per_instance
    return {
        "actorCount": len(actors),
        "staticMeshComponents": static_meshes,
        "instancedComponents": hisms,
        "instanceCount": instances,
        "uniqueMeshes": len(seen),
        "naniteMeshes": nanite_meshes,
        "triangleLowerBound": triangles,
        "triangleNote": "Lower bound: with Nanite enabled get_num_triangles(0) returns the fallback count.",
    }


class Probe:
    def __init__(self):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.receipt = {
            "status": "started",
            "stamp": stamp,
            "map": TARGET_MAP,
            "budgetMs": BUDGET_MS,
            "budgetMsPlaza": BUDGET_MS_PLAZA,
            "stations": [],
            "notCollected": [
                "draw calls and primitive counts: exposed only through `stat scenerendering`, "
                "whose log format is not stable enough to gate on. Not fabricated."
            ],
        }
        self.path = OUTPUT_DIR / f"perf-probe-{stamp}.json"
        self.index = 0
        self.samples = []
        self.station_started = 0.0
        self.placed = False
        self.last_tick = None
        self.started = time.time()
        self.handle = None
        self.throttle_restored = False

    # -- lifecycle ---------------------------------------------------------

    def run(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
            world = editor.get_editor_world()
            assert world and world.get_path_name().startswith(TARGET_MAP), (
                "wrong map open: %s" % (world.get_path_name() if world else "none"))
            assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(), "dirty maps present"

            self.receipt["geometry"] = count_geometry()
            self.receipt["memoryAtStart"] = process_memory_mb()

            # PIE is throttled unless this is off. Restored in finish().
            unreal.SystemLibrary.execute_console_command(world, "Slate.bAllowThrottling 0")
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()

            self.station_started = time.time()
            self.handle = unreal.register_slate_post_tick_callback(self.tick)
        except Exception as exc:  # noqa: BLE001
            self.receipt.update(status="failed", error=str(exc) or repr(exc))
            self.write()

    def tick(self, delta_seconds):
        now = time.time()
        try:
            if now - self.started > LIMIT_SECONDS:
                self.receipt["status"] = "stopped_at_wall_clock_limit"
                self.finish()
                return

            world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            if not world:
                return  # PIE not up yet

            name, location, yaw, budget = STATIONS[self.index]
            controller = unreal.GameplayStatics.get_player_controller(world, 0)
            pawn = controller.get_controlled_pawn() if controller else None
            if not pawn:
                return

            if not self.placed:
                # Teleport rather than walk: this probe measures rendering cost at a set
                # of views, not traversal. Walking is what release_walk_probe.py is for.
                # Flagged rather than timed: the pawn may not exist for several seconds
                # after PIE begins, and a time window can close before it appears.
                pawn.set_actor_location(location, False, False)
                controller.set_control_rotation(unreal.Rotator(0.0, yaw, 0.0))
                self.placed = True
                self.station_started = now
                self.last_tick = None
                return

            elapsed = now - self.station_started

            if elapsed < SETTLE_SECONDS:
                self.last_tick = now  # discard warm-up frames
                return

            if self.last_tick is not None:
                self.samples.append((now - self.last_tick) * 1000.0)
            self.last_tick = now

            if elapsed >= SETTLE_SECONDS + HOLD_SECONDS:
                self.record_station(name, location, yaw, budget)
                self.index += 1
                self.samples = []
                self.last_tick = None
                self.station_started = now
                self.placed = False
                if self.index >= len(STATIONS):
                    self.receipt["status"] = "completed"
                    self.finish()
        except Exception as exc:  # noqa: BLE001
            self.receipt.update(status="failed", error=str(exc) or repr(exc))
            self.finish()

    # -- results -----------------------------------------------------------

    def record_station(self, name, location, yaw, budget):
        ordered = sorted(self.samples)
        count = len(ordered)
        if count == 0:
            self.receipt["stations"].append(
                {"station": name, "status": "no_samples",
                 "note": "no frames captured in the hold window"})
            return
        mean = sum(ordered) / count
        p50 = ordered[count // 2]
        p95 = ordered[min(count - 1, int(count * 0.95))]
        worst = ordered[-1]
        self.receipt["stations"].append({
            "station": name,
            "location": [location.x, location.y, location.z],
            "yaw": yaw,
            "budgetMs": budget,
            "frames": count,
            "meanMs": round(mean, 2),
            "p50Ms": round(p50, 2),
            "p95Ms": round(p95, 2),
            "worstMs": round(worst, 2),
            "impliedFps": round(1000.0 / mean, 1) if mean > 0 else None,
            # p95 is the gate, not the mean: a view that hitches is a view that reads
            # as broken even when its average looks fine.
            "withinBudget": p95 <= budget,
            "memory": process_memory_mb(),
        })

    def finish(self):
        try:
            if self.handle is not None:
                unreal.unregister_slate_post_tick_callback(self.handle)
                self.handle = None
            levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            levels.editor_request_end_play()
            world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            if world and not self.throttle_restored:
                unreal.SystemLibrary.execute_console_command(world, "Slate.bAllowThrottling 1")
                self.throttle_restored = True
        except Exception as exc:  # noqa: BLE001
            self.receipt.setdefault("teardownError", str(exc))

        measured = [s for s in self.receipt["stations"] if "p95Ms" in s]
        over = [s["station"] for s in measured if not s["withinBudget"]]
        self.receipt["stationsMeasured"] = len(measured)
        self.receipt["stationsOverBudget"] = over
        self.receipt["pass"] = bool(measured) and not over
        self.receipt["memoryAtEnd"] = process_memory_mb()
        if measured:
            self.receipt["worstStation"] = max(measured, key=lambda s: s["p95Ms"])["station"]
        self.write()
        if QUIT_EDITOR:
            unreal.SystemLibrary.quit_editor()

    def write(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.receipt, indent=2), encoding="utf-8")
        unreal.log("MIKDASH_PERF_PROBE " + json.dumps({
            "status": self.receipt["status"],
            "pass": self.receipt.get("pass"),
            "over": self.receipt.get("stationsOverBudget"),
            "receipt": str(self.path),
        }))


Probe().run()
