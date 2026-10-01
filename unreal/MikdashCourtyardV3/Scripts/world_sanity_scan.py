"""World sanity scan: list every leftover, floating, sunk or doubled object in a map.

WHY THIS EXISTS
---------------
The owner keeps finding objects left behind by earlier builds (a floating tank by the
Kotel, stray domes, a slab on the horizon, stalls sunk into new paving). Each was found
by eye, one at a time. This scan checks every placed actor in the shipping map at once
and writes a ranked list, so leftovers are found before a visitor sees them.

READ-ONLY. It loads the map, measures, and writes a report. It never saves an asset or
the map, and it fails if anything in memory became dirty.

WHAT IT FLAGS (rules live in world_sanity_rules.py and are unit-tested offline)
  floating          more than 5 cm of air between the object and the surface below it
  no_ground_below   nothing at all below it (and it is not something meant to fly)
  sunk              a short object (< 6 m) whose base is more than 8 cm under the surface
  duplicate         the same mesh placed twice at the same spot
  legacy_name       label/folder/mesh path uses words like Study, Old, Placeholder, V1
  hidden_in_game    placed with a mesh but hidden in game (may be a runtime hide set:
                    check before removing)

Objects meant to be off the ground (birds, lamps, roofs, arches, beams...) are exempt
from floating checks by whole-word name match; see INTENDED_AIRBORNE.

LIMITS
  * Surfaces come from collision traces down each object's centre. A mesh with no
    collision is invisible to the trace, so the report also says how many traces hit
    nothing; if that is most of them, collision is missing, not the ground.
  * Geometry built at BeginPlay (the runtime plaza deck, display-state hide sets) does
    not exist in the editor world. Objects standing on it can read as floating here.
  * Fully buried objects are not detected: the trace starts just above each object, so
    ground that covers it is never seen. (The rule exists in world_sanity_rules.py for a
    later upward pass.)
  * A hit is a lead to look at, not a verdict. Every finding carries a BugItGo line:
    paste it into the game or editor console (~) to fly the camera to it.

INVOCATION (serial; never while another engine job is running)

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/world_sanity_scan.py"
      -unattended -nullrhi -asyncstaticmeshcompilationmaxconcurrency=1
      -abslog="C:/Mikdash/Working-5.8/World-Sanity-01.log"

  -ScanMap=/Game/...      map to scan (default: GameDefaultMap in Config/DefaultEngine.ini)
  -ScanLimit=N            stop after N actors (smoke test)

Output: SourceAssets/world-sanity/scan-<stamp>.json, .csv and -summary.md
"""
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(__file__).resolve().parent))
import world_sanity_rules as rules  # noqa: E402

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
OUTPUT_DIR = ROOT / "SourceAssets/world-sanity"
TRACE_ABOVE_CM = 5.0
TRACE_DEPTH_CM = 500000.0  # 5 km: below the lowest valley in the context terrain

PRIORITY = {"floating": 0, "no_ground_below": 1, "sunk": 2, "duplicate": 3,
            "buried": 4, "legacy_name": 5, "hidden_in_game": 6}


def switches():
    try:
        raw = unreal.SystemLibrary.get_command_line()
    except Exception:  # noqa: BLE001
        raw = " ".join(sys.argv)
    out = {}
    for key, value in re.findall(r'-([A-Za-z_]+)(?:=("[^"]*"|\S+))?', raw or ""):
        out[key.lower()] = (value or "1").strip('"')
    return out


def default_map():
    ini = ROOT / "Config/DefaultEngine.ini"
    for line in ini.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        if line.strip().startswith("GameDefaultMap="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("GameDefaultMap not found in %s" % ini)


def vec(v):
    return [round(v.x, 2), round(v.y, 2), round(v.z, 2)]


def bugitgo(cx, cy, top_z, extent):
    # Stand back along -X and look slightly down at the object.
    dist = max(400.0, 3.0 * max(extent.x, extent.y, extent.z))
    return "BugItGo %.0f %.0f %.0f -20 0 0" % (cx - dist, cy, top_z + dist * 0.4)


def first_surface_below(world, actor, cx, cy, top_z):
    start = unreal.Vector(cx, cy, top_z + TRACE_ABOVE_CM)
    end = unreal.Vector(cx, cy, top_z - TRACE_DEPTH_CM)
    hits = unreal.SystemLibrary.line_trace_multi(
        world, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [actor],
        unreal.DrawDebugTrace.NONE, True)
    for hit in hits or []:
        t = hit.to_tuple()
        location, hit_actor = t[4], t[9]
        if hit_actor is None or hit_actor == actor:
            continue
        return location.z, hit_actor.get_actor_label()
    return None, None


def main():
    sw = switches()
    target_map = sw.get("scanmap") or default_map()
    limit = int(sw.get("scanlimit") or 0)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()

    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError("dirty map packages before scan; refusing")
    unreal.EditorLoadingAndSavingUtils.load_map(target_map)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    assert world is not None and world.get_path_name().startswith(target_map), "map did not load"

    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    findings, placements = [], []
    traces = traced_hit = 0
    scanned = 0

    for actor in actors:
        comps = actor.get_components_by_class(unreal.StaticMeshComponent) or []
        meshes = []
        for comp in comps:
            if isinstance(comp, unreal.InstancedStaticMeshComponent):
                continue  # instanced decoration is placed by generators, not by hand
            mesh = comp.get_editor_property("static_mesh")
            if mesh is not None:
                meshes.append(mesh.get_path_name())
        if not meshes:
            continue
        scanned += 1
        if limit and scanned > limit:
            break

        label = actor.get_actor_label()
        folder = str(actor.get_folder_path() or "")
        cls = actor.get_class().get_name()
        origin, extent = actor.get_actor_bounds(False)
        bottom_z, top_z = origin.z - extent.z, origin.z + extent.z
        word_set = rules.words(label, folder, cls, *meshes)
        airborne = rules.matched(word_set, rules.INTENDED_AIRBORNE)
        base = {
            "actor": label, "class": cls, "folder": folder, "mesh": meshes[0],
            "meshCount": len(meshes), "boundsOrigin": vec(origin), "boundsExtent": vec(extent),
            "bugItGo": bugitgo(origin.x, origin.y, top_z, extent),
        }

        traces += 1
        surface_z, surface_actor = first_surface_below(world, actor, origin.x, origin.y, top_z)
        if surface_z is not None:
            traced_hit += 1
        verdict = rules.classify_support(bottom_z, top_z, surface_z, bool(airborne))
        if verdict:
            findings.append(dict(base, **verdict, surface=surface_actor, exemptWords=airborne))

        legacy = rules.matched(word_set, rules.LEGACY_WORDS)
        if legacy:
            findings.append(dict(base, kind="legacy_name", words=legacy))

        if actor.get_editor_property("hidden"):
            findings.append(dict(base, kind="hidden_in_game"))

        rot = actor.get_actor_rotation()
        scale = actor.get_actor_scale3d()
        loc = actor.get_actor_location()
        placements.append({"id": len(placements), "actor": label, "mesh": "|".join(meshes),
                           "loc": (loc.x, loc.y, loc.z), "rot": (rot.pitch, rot.yaw, rot.roll),
                           "scale": (scale.x, scale.y, scale.z), "base": base})

    for group in rules.duplicate_groups(placements):
        keep = placements[group[0]]
        for pid in group[1:]:
            findings.append(dict(placements[pid]["base"], kind="duplicate", duplicateOf=keep["actor"]))

    # Biggest visible problems first: by kind, then by object size.
    def rank(f):
        e = f["boundsExtent"]
        return (PRIORITY[f["kind"]], -(e[0] * e[1] * max(e[2], 1.0)))
    findings.sort(key=rank)

    dirty = unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    counts = {}
    for f in findings:
        counts[f["kind"]] = counts.get(f["kind"], 0) + 1
    receipt = {
        "tool": "world_sanity_scan.py", "stamp": stamp, "map": target_map,
        "readOnly": True, "dirtyPackagesAfter": [p.get_name() for p in dirty],
        "actorsWithMeshes": scanned, "traces": traces, "tracesThatHitAnything": traced_hit,
        "seconds": round(time.time() - started, 1), "counts": counts,
        "tolerances": {"floatCm": rules.FLOAT_TOLERANCE_CM, "sinkCm": rules.SINK_TOLERANCE_CM,
                       "sinkMaxHeightCm": rules.SINK_MAX_HEIGHT_CM},
        "findings": findings,
    }
    out = OUTPUT_DIR / ("scan-%s.json" % stamp)
    out.write_text(json.dumps(receipt, indent=1), encoding="utf-8")

    with open(OUTPUT_DIR / ("scan-%s.csv" % stamp), "w", newline="", encoding="utf-8") as fh:
        cols = ["kind", "actor", "gap_cm", "height_cm", "surface", "duplicateOf", "words",
                "folder", "mesh", "bugItGo"]
        writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for f in findings:
            writer.writerow({k: (",".join(f[k]) if isinstance(f.get(k), list) else f.get(k))
                             for k in cols})

    lines = ["# World sanity scan %s" % stamp, "", "Map: `%s`" % target_map,
             "Actors with meshes: %d. Traces that found any surface: %d of %d."
             % (scanned, traced_hit, traces), ""]
    for kind in sorted(counts, key=PRIORITY.get):
        lines.append("- **%s**: %d" % (kind, counts[kind]))
    lines += ["", "## Top 40", ""]
    for f in findings[:40]:
        extra = "gap %s cm" % f.get("gap_cm") if "gap_cm" in f else ""
        lines.append("- %s `%s` %s  `%s`" % (f["kind"], f["actor"], extra, f["bugItGo"]))
    (OUTPUT_DIR / ("scan-%s-summary.md" % stamp)).write_text("\n".join(lines), encoding="utf-8")

    unreal.log("WORLD_SANITY receipt=%s counts=%s" % (out, counts))
    if dirty:
        raise RuntimeError("scan dirtied packages (nothing was saved): %s" % receipt["dirtyPackagesAfter"])


main()
