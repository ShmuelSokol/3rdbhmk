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
  * Game thread, render thread, RHI thread and GPU times ARE measured, by running the
    engine CSV profiler across the whole walk and slicing its rows back onto the
    stations by elapsed time. This is the number that says whether a frame is CPU-bound
    or GPU-bound, which is the only question that decides what to optimise. Launch with
    -csvGpuStats or the GPU column will be absent and the receipt will say so.
  * Draw calls are read from the CSV too when the build emits them, and reported as
    absent when it does not. They are never estimated. `stat scenerendering` is still
    not parsed: its log format is not stable enough to gate on.
  * Process memory IS measured, through the Win32 API. The first version of this call
    left argtypes unset, GetCurrentProcess returned a truncated pseudo-handle and every
    memory field in perf-probe-20260908T102520Z.json came back null. Fixed here.
  * A WARM-UP is held before the first station. An editor that has just opened this map
    is still compiling shaders and building derived data, and frames measured during
    that are measuring the compiler, not the scene. The 20260908T102520Z receipt shows
    the symptom: five unrelated stations all landing within 24.07-24.58 ms, a spread of
    2% across an enclosed sanctuary and an open city view, plus 553 ms, 244 ms and
    233 ms single-frame spikes. That is a background job, not a scene.
  * Optional reference screenshots at each station, for proving that an optimisation
    changed how the frame is DRAWN and not how it LOOKS.

Configuration by environment variable, so the same file works from the editor console,
the `py` command, or -ExecCmds:
  MIKDASH_PERF_LIMIT_SECONDS   hard wall-clock limit, 30..600 (default 300)
  MIKDASH_PERF_WARMUP_SECONDS  discarded settle after PIE starts, before station 0
                               (default 30.0). Shader and DDC work lands here.
  MIKDASH_PERF_SETTLE_SECONDS  discarded warm-up at each station (default 2.0)
  MIKDASH_PERF_HOLD_SECONDS    sampled dwell at each station (default 4.0)
  MIKDASH_PERF_SHOTS           1 = write a 1920x1080 screenshot per station (default 0)
  MIKDASH_PERF_LABEL           free text recorded in the receipt, e.g. "before-nanite"
  MIKDASH_PERF_QUIT_EDITOR     1 = quit the editor after the receipt (default 0)

Receipt: SourceAssets/perf-review/perf-probe-<UTC stamp>.json
"""

import ctypes
import ctypes.wintypes
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import unreal
except ImportError:  # standalone --merge-csv mode, outside the editor
    unreal = None

ROOT = Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
TARGET_MAP = "/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough"
OUTPUT_DIR = ROOT / "SourceAssets/perf-review"

LIMIT_SECONDS = max(30.0, min(600.0, float(os.environ.get("MIKDASH_PERF_LIMIT_SECONDS", "300"))))
WARMUP_SECONDS = float(os.environ.get("MIKDASH_PERF_WARMUP_SECONDS", "30.0"))
SETTLE_SECONDS = float(os.environ.get("MIKDASH_PERF_SETTLE_SECONDS", "2.0"))
HOLD_SECONDS = float(os.environ.get("MIKDASH_PERF_HOLD_SECONDS", "4.0"))
SHOTS = os.environ.get("MIKDASH_PERF_SHOTS", "0") == "1"
LABEL = os.environ.get("MIKDASH_PERF_LABEL", "")
QUIT_EDITOR = os.environ.get("MIKDASH_PERF_QUIT_EDITOR", "0") == "1"

CSV_DIR = ROOT / "Saved/Profiling/CSV"
SHOT_ROOT = ROOT / "Saved/Screenshots"

# CSV columns worth reporting, in the order they are reported. Whatever the build does
# not emit is listed in the receipt as absent rather than filled in.
CSV_COLUMNS = [
    ("frameTimeMs", ("FrameTime",)),
    ("gameThreadMs", ("GameThreadTime", "Game")),
    ("renderThreadMs", ("RenderThreadTime", "RenderThread")),
    ("rhiThreadMs", ("RHIThreadTime", "RHIThread")),
    ("gpuMs", ("GPUTime", "GPU")),
    ("drawCalls", ("RHI/DrawCalls", "DrawCalls", "RHI/DrawCalls_Total")),
    ("primitivesDrawn", ("RHI/DrawnPrimitives", "PrimitivesDrawn", "RHI/TrianglesDrawn")),
]

# Budget from PERFORMANCE-BUDGET.md. The plaza looks out over the whole modern city and
# is the heaviest view in the build, so it carries its own allowance.
BUDGET_MS = 16.7
BUDGET_MS_PLAZA = 22.0

# Stations are real coordinates taken from release receipts and probe routes, not
# invented. Each is (name, location, look-at yaw, budget).
STATIONS = [
    ("outer_court_east", (4974.0, 0.0, 468.0), 180.0, BUDGET_MS),
    ("court_toward_sanctuary", (2100.0, 0.0, 668.0), 180.0, BUDGET_MS),
    ("altar_approach", (-3200.0, 0.0, 995.0), 180.0, BUDGET_MS),
    ("heikhal_doorway", (-3600.0, 0.0, 995.0), 180.0, BUDGET_MS),
    ("menorah", (-5100.0, 315.0, 995.0), 180.0, BUDGET_MS),
    ("golden_altar", (-4650.0, 0.0, 995.0), 180.0, BUDGET_MS),
    ("paroches", (-5450.0, 0.0, 995.0), 180.0, BUDGET_MS),
    ("mount_platform_deck", (11500.0, -300.0, 70.0), 90.0, BUDGET_MS),
    ("plaza_over_city", (11500.0, -300.0, 400.0), 270.0, BUDGET_MS_PLAZA),
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
    # argtypes/restype are not optional on x64: without them GetCurrentProcess returns a
    # C int and its -1 pseudo-handle is truncated, so the call fails and every field
    # reads back null. That is exactly what happened in perf-probe-20260908T102520Z.
    get_current = ctypes.windll.kernel32.GetCurrentProcess
    get_current.restype = ctypes.c_void_p
    get_current.argtypes = []
    handle = get_current()
    ok = False
    for dll, fn in ((ctypes.windll.kernel32, "K32GetProcessMemoryInfo"),
                    (ctypes.windll.psapi, "GetProcessMemoryInfo")):
        try:
            call = getattr(dll, fn)
            call.restype = ctypes.wintypes.BOOL
            call.argtypes = [ctypes.c_void_p,
                             ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
                             ctypes.wintypes.DWORD]
            ok = bool(call(handle, ctypes.byref(counters), counters.cb))
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


def newest_csv_after(started_at):
    """The CSV the profiler wrote for this run, or None. Never picks up an older file."""
    if not CSV_DIR.is_dir():
        return None
    candidates = [f for f in CSV_DIR.glob("*.csv") if f.stat().st_mtime >= started_at - 2.0]
    return max(candidates, key=lambda f: f.stat().st_mtime) if candidates else None


def read_csv_rows(path):
    """(headers, rows-as-floats). The CSV profiler appends a trailing metadata line
    beginning with '[' which is not a data row; it is dropped."""
    import csv as csv_module
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv_module.reader(handle)
        headers = next(reader, None)
        if not headers:
            return [], []
        rows = []
        for raw in reader:
            if not raw or raw[0].startswith("["):
                continue
            values = []
            for cell in raw:
                try:
                    values.append(float(cell))
                except ValueError:
                    values.append(None)
            rows.append(values)
    return [h.strip() for h in headers], rows


def summarise_csv_window(headers, rows, cumulative, low, high):
    """Statistics for the CSV rows whose cumulative elapsed time lies in [low, high).

    Slicing on the CSV's own accumulated FrameTime rather than on a row index makes the
    alignment self-correcting: it does not matter how many frames the engine rendered
    between the profiler starting and the first station being placed.
    """
    index = {name: position for position, name in enumerate(headers)}
    selected = [row for row, elapsed in zip(rows, cumulative) if low <= elapsed < high]
    if not selected:
        return None
    out = {"csvFrames": len(selected)}
    for key, aliases in CSV_COLUMNS:
        column = next((index[a] for a in aliases if a in index), None)
        if column is None:
            out[key] = None
            continue
        values = sorted(v for row in selected
                        if column < len(row) and (v := row[column]) is not None)
        if not values:
            out[key] = None
            continue
        out[key] = {
            "mean": round(sum(values) / len(values), 2),
            "p50": round(values[len(values) // 2], 2),
            "p95": round(values[min(len(values) - 1, int(len(values) * 0.95))], 2),
        }
    return out


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
            "label": LABEL,
            "warmupSeconds": WARMUP_SECONDS,
            "settleSeconds": SETTLE_SECONDS,
            "holdSeconds": HOLD_SECONDS,
            "notCollected": [
                "`stat scenerendering` is not parsed: its log format is not stable "
                "enough to gate on. Thread and GPU times come from the CSV profiler "
                "instead, and any column the build does not emit is reported as null."
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
        self.warmed = False
        self.warmup_started = None
        self.csv_started_at = None
        self.csv_zero = None
        self.in_tick = False
        self.shot_order = []
        self.shots_from = time.time()
        self.shot_dir = OUTPUT_DIR / f"frames-{stamp}"

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
        # Belt and braces against the re-entrancy that HighResShot's predecessor caused.
        if self.in_tick:
            return
        self.in_tick = True
        try:
            self._tick()
        finally:
            self.in_tick = False

    def _tick(self):
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

            if not self.warmed:
                # An editor that just opened this map is still compiling shaders and
                # cooking derived data. Frames taken now measure the compiler.
                if self.warmup_started is None:
                    self.warmup_started = now
                    unreal.log("MIKDASH_PERF_PROBE warmup %.0fs" % WARMUP_SECONDS)
                if now - self.warmup_started < WARMUP_SECONDS:
                    return
                self.warmed = True
                self.station_started = now
                self.csv_started_at = time.time()
                self.csv_zero = now
                unreal.SystemLibrary.execute_console_command(world, "CsvProfile start")
                return

            if not self.placed:
                # Teleport rather than walk: this probe measures rendering cost at a set
                # of views, not traversal. Walking is what release_walk_probe.py is for.
                # Flagged rather than timed: the pawn may not exist for several seconds
                # after PIE begins, and a time window can close before it appears.
                pawn.set_actor_location(unreal.Vector(*location), False, False)
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
                if SHOTS:
                    self.screenshot(world, name)
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

    def screenshot(self, world, name):
        """A reference frame per station. An optimisation that changes what these look
        like is a regression, however good its numbers are.

        This goes through the console command, NOT AutomationLibrary. The Python
        take_high_res_screenshot call flushes rendering and pumps Slate synchronously,
        which re-enters this very post-tick callback: the first run of this probe with
        screenshots on recorded station 0 three hundred and thirty-two times and died on
        "maximum recursion depth exceeded". HighResShot is queued to end of frame and
        does not re-enter. It names its own files under Saved/Screenshots; the run order
        is recorded here and the files are matched to stations by modification time.
        """
        try:
            unreal.SystemLibrary.execute_console_command(world, "HighResShot 1920x1080")
            self.shot_order.append(name)
        except Exception as exc:  # noqa: BLE001
            self.receipt.setdefault("screenshotErrors", []).append("%s: %s" % (name, exc))

    def collect_screenshots(self):
        """Move whatever HighResShot wrote into the receipt directory, in station order."""
        if not self.shot_order:
            return
        try:
            written = sorted(
                (f for f in SHOT_ROOT.rglob("*.png")
                 if f.stat().st_mtime >= self.shots_from - 2.0),
                key=lambda f: f.stat().st_mtime)
            self.shot_dir.mkdir(parents=True, exist_ok=True)
            paired = []
            for position, source in enumerate(written[:len(self.shot_order)]):
                target = self.shot_dir / ("%02d_%s.png" % (position, self.shot_order[position]))
                shutil.copy2(source, target)
                paired.append(target.name)
            self.receipt["screenshots"] = {
                "dir": str(self.shot_dir),
                "requested": len(self.shot_order),
                "written": len(written),
                "files": paired,
                "note": "Matched to stations by write order. Fewer files than stations "
                        "means some shots did not land; the pairing is then unreliable "
                        "and should not be used for a look comparison.",
                "reliable": len(written) == len(self.shot_order),
            }
        except Exception as exc:  # noqa: BLE001
            self.receipt["screenshots"] = {"error": repr(exc)}

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
            "location": list(location),
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
            # Filled in by attach_csv() once the profiler has flushed its file.
            "csvWindowSeconds": [round(self.station_started - self.csv_zero + SETTLE_SECONDS, 3),
                                 round(self.station_started - self.csv_zero
                                       + SETTLE_SECONDS + HOLD_SECONDS, 3)]
            if self.csv_zero is not None else None,
        })

    def attach_csv(self):
        """Slice the profiler CSV back onto the stations. Reported as unavailable, never
        approximated, when the file does not appear or the columns are absent."""
        if self.csv_started_at is None:
            self.receipt["csv"] = {"available": False, "reason": "profiler never started"}
            return
        # The profiler's writer thread still holds the file open for a moment after
        # `CsvProfile stop`, so the first read raises PermissionError even though the
        # file already has bytes in it. Poll on a successful OPEN, not on a size.
        deadline = time.time() + 45.0
        path, headers, rows, last_error = None, None, None, None
        while time.time() < deadline:
            path = newest_csv_after(self.csv_started_at)
            if path is not None:
                try:
                    headers, rows = read_csv_rows(path)
                    if rows:
                        break
                    last_error = "file readable but empty"
                except Exception as exc:  # noqa: BLE001
                    last_error = repr(exc)
            else:
                last_error = "no CSV written under %s" % CSV_DIR
            time.sleep(1.0)
        if not rows:
            self.receipt["csv"] = {"available": False, "reason": last_error,
                                   "file": str(path) if path else None}
            return
        frame_column = headers.index("FrameTime") if "FrameTime" in headers else None
        if frame_column is None or not rows:
            self.receipt["csv"] = {"available": False, "file": str(path),
                                   "reason": "no FrameTime column",
                                   "headersSample": headers[:40]}
            return
        cumulative, running = [], 0.0
        for row in rows:
            value = row[frame_column] if frame_column < len(row) else None
            running += (value or 0.0) / 1000.0
            cumulative.append(running)
        present = {key: any(a in headers for a in aliases) for key, aliases in CSV_COLUMNS}
        self.receipt["csv"] = {
            "available": True,
            "file": str(path),
            "rows": len(rows),
            "columnsPresent": present,
            "columnsAbsent": sorted(k for k, v in present.items() if not v),
            "note": "GPU time needs the editor launched with -csvGpuStats.",
        }
        for station in self.receipt["stations"]:
            window = station.get("csvWindowSeconds")
            if not window:
                continue
            station["threads"] = summarise_csv_window(
                headers, rows, cumulative, window[0], window[1])

    def finish(self):
        try:
            if self.handle is not None:
                unreal.unregister_slate_post_tick_callback(self.handle)
                self.handle = None
            world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
            if world is not None and self.csv_started_at is not None:
                unreal.SystemLibrary.execute_console_command(world, "CsvProfile stop")
            levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            levels.editor_request_end_play()
            world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
            if world and not self.throttle_restored:
                unreal.SystemLibrary.execute_console_command(world, "Slate.bAllowThrottling 1")
                self.throttle_restored = True
        except Exception as exc:  # noqa: BLE001
            self.receipt.setdefault("teardownError", str(exc))

        try:
            self.attach_csv()
        except Exception as exc:  # noqa: BLE001
            self.receipt["csv"] = {"available": False, "reason": repr(exc)}
        if SHOTS:
            self.collect_screenshots()

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


def merge_csv_into_receipt(receipt_path, csv_path=None):
    """Fill a receipt's per-station thread and GPU times from the profiler CSV.

    Run this AFTER the editor process has exited. The CSV profiler's writer thread keeps
    its file open for the life of the process, so an in-editor read raises PermissionError
    no matter how long it waits -- 45 s of polling was tried and always failed. Nothing
    about the numbers changes; only when they can be read does.

        python Scripts/perf_probe.py --merge-csv <receipt.json> [<profile.csv>]
    """
    receipt_path = Path(receipt_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
    if csv_path is None:
        csv_path = (receipt.get("csv") or {}).get("file")
    if not csv_path:
        candidates = sorted(CSV_DIR.glob("*.csv"), key=lambda f: f.stat().st_mtime)
        csv_path = candidates[-1] if candidates else None
    if not csv_path or not Path(csv_path).is_file():
        receipt["csv"] = {"available": False, "reason": "no CSV file to merge"}
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        return receipt
    headers, rows = read_csv_rows(csv_path)
    frame_column = headers.index("FrameTime") if "FrameTime" in headers else None
    if frame_column is None or not rows:
        receipt["csv"] = {"available": False, "file": str(csv_path),
                          "reason": "no FrameTime column", "headersSample": headers[:60]}
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        return receipt
    cumulative, running = [], 0.0
    for row in rows:
        value = row[frame_column] if frame_column < len(row) else None
        running += (value or 0.0) / 1000.0
        cumulative.append(running)
    present = {key: next((a for a in aliases if a in headers), None)
               for key, aliases in CSV_COLUMNS}
    receipt["csv"] = {
        "available": True,
        "file": str(csv_path),
        "rows": len(rows),
        "columnsUsed": {k: v for k, v in present.items() if v},
        "columnsAbsent": sorted(k for k, v in present.items() if not v),
        "mergedOutOfEditor": True,
        "note": "Sliced onto stations by the CSV's own accumulated FrameTime, so the "
                "alignment does not depend on how many frames passed before station 0.",
    }
    for station in receipt.get("stations", []):
        window = station.get("csvWindowSeconds")
        if not window:
            continue
        station["threads"] = summarise_csv_window(
            headers, rows, cumulative, window[0], window[1])
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


if __name__ == "__main__" and "--merge-csv" in sys.argv:
    position = sys.argv.index("--merge-csv")
    arguments = sys.argv[position + 1:]
    merged = merge_csv_into_receipt(arguments[0], arguments[1] if len(arguments) > 1 else None)
    print(json.dumps(merged.get("csv"), indent=2))
elif unreal is not None:
    Probe().run()
