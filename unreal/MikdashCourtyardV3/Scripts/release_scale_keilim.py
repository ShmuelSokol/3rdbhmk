"""Rescale the three Heikhal vessel studies to the dimensions given in Lishchno Tidreshu.

Book review 2026-09-07 item 8 (SourceAssets/vessels-review/book-keilim-review-20260907.md):
  shulchan  2 x 1 amot, 3 amot high  -> 100 x 50 x 150 cm      (p. 241; alt. p. 246 bread included)
  menorah   18 tefachim              -> 150 cm at 50 cm/amah   (p. 252; model is 180 = TI conversion)
  altar     1 x 1 x 2 amot at a 5-tefach amah -> 41.7 x 41.7 x 83.3 cm (p. 255, Eruvin 4a)

Every number comes from Scripts/release_scale_keilim.spec.json so a human can review the plan
before running. Actors are identified by their current XY cluster inside the Heikhal AND their
label (same rule as C:\\Mikdash\\Working-5.8\\run-release-move-keilim.py), then guarded on mesh
path, pre-scale bounds, scale (1,1,1) and yaw.

Commandlet invocation (serial, never while another native job is running):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_scale_keilim.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Release-KeilimScale-01.log"

Optional switches (read from the engine command line):
  -KeilimInspect                 read-only listing: identification, current dimensions, predicted
                                 post-scale bounds and clearances. No checkpoint, no save.
  -KeilimGroups=menorah,altar    comma-separated subset of menorah,shulchan,altar. A group named
                                 here runs even if its spec enabledByDefault is false (shulchan).
                                 Without the switch the enabledByDefault groups run.
  -KeilimWallClearanceCm=<cm>    override wallClearance.minCm (default 100).

Offline (plain Python, no Unreal):  python Scripts/release_scale_keilim.py
  prints the predicted plan computed from the spec's expectedBoundsBefore.

Safety model:
  * Refuses to run with the wrong project directory, a game world, dirty packages, or a loaded
    world that is not the combined map.
  * Every Heikhal cluster must contain exactly one static-mesh actor with the expected label,
    mesh path, pre-scale bounds and scale (1,1,1); a menorah yaw other than 90 refuses.
  * Pre-mutation prediction: a group whose scaled AABB would leave the Heikhal margin or come
    closer than the wall-clearance threshold to the Y=+-500 walls is OMITTED with numeric
    evidence. Nothing is moved to make room; the receipt says why.
  * Copies Walkthrough.umap to ReviewCheckpoints/KeilimScale-<stamp>/ (sha-verified) before
    any mutation. Scales about the actor location; if the pivot is not at the base the actor Z
    is compensated so the AABB bottom stays on the floor at Z 925 (XY never changes).
  * Saves only if at least one group was scaled, reopens the map and reads back scale,
    location, yaw and bounds numerically.
  * The receipt JSON (SourceAssets/vessels-review/keilim-scale-<stamp>.json) is written at
    start and again in finally, preserving partial state on failure.
"""
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE / "release_scale_keilim.spec.json"
GROUP_ORDER = ("menorah", "shulchan", "altar")


# --------------------------------------------------------------------------- pure helpers

def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if spec.get("specVersion") != 1:
        raise RuntimeError("unsupported specVersion in " + str(SPEC_PATH))
    for name in GROUP_ORDER:
        if name not in spec["groups"]:
            raise RuntimeError("spec missing group " + name)
    return spec


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def predict_bounds(location, bounds, scale):
    """AABB after scaling about the actor location (rotation unchanged, scale in world axes
    of an axis-aligned actor: the three actors have yaw 0 or 90, so a uniform scale or a
    Z-only scale keeps the AABB aligned)."""
    out = {}
    for key in ("min", "max"):
        out[key] = [location[i] + (bounds[key][i] - location[i]) * scale[i] for i in range(3)]
    return out


def size_of(bounds):
    return [bounds["max"][i] - bounds["min"][i] for i in range(3)]


def wall_clearance(bounds, heikhal):
    return {"north": bounds["min"][1] - heikhal["ymin"], "south": heikhal["ymax"] - bounds["max"][1],
            "west": bounds["min"][0] - heikhal["xmin"], "east": heikhal["xmax"] - bounds["max"][0]}


def heikhal_violation(bounds, heikhal, margin):
    problems = []
    if bounds["min"][0] < heikhal["xmin"] + margin:
        problems.append("west margin")
    if bounds["max"][0] > heikhal["xmax"]:
        problems.append("east face")
    if bounds["min"][1] < heikhal["ymin"] + margin:
        problems.append("north margin")
    if bounds["max"][1] > heikhal["ymax"] - margin:
        problems.append("south margin")
    return problems


def evaluate_group(spec, name, location, bounds_before, wall_min_cm):
    """Numeric plan for one group. Returns a dict with predicted bounds, clearances and the
    omission reasons (empty list = clear to scale)."""
    group = spec["groups"][name]
    heikhal = spec["heikhal"]
    scale = group["scale"]
    predicted = predict_bounds(location, bounds_before, scale)
    clear_before = wall_clearance(bounds_before, heikhal)
    clear_after = wall_clearance(predicted, heikhal)
    reasons = []
    hv = heikhal_violation(predicted, heikhal, spec["heikhalWallMarginCm"])
    if hv:
        reasons.append("scaled AABB leaves Heikhal clearance: " + ", ".join(hv))
    ns_after = min(clear_after["north"], clear_after["south"])
    if ns_after < wall_min_cm:
        reasons.append("scaled AABB is %.2f cm from the nearest N/S wall (threshold %.2f cm; before scaling %.2f cm)"
                       % (ns_after, wall_min_cm, min(clear_before["north"], clear_before["south"])))
    return {
        "scale": scale, "scaleKind": group["scaleKind"],
        "sizeBefore": size_of(bounds_before), "sizeAfterPredicted": size_of(predicted),
        "predictedBoundsAfter": predicted,
        "wallClearanceBeforeCm": clear_before, "wallClearanceAfterCm": clear_after,
        "wallClearanceMinCm": wall_min_cm,
        "pivotAtBase": abs(bounds_before["min"][2] - location[2]) <= spec["reopenToleranceCm"],
        "baseZOffsetBefore": bounds_before["min"][2] - location[2],
        "omissionReasons": reasons,
    }


def offline_plan(spec, wall_min_cm=None):
    """Plan from the spec alone (expectedBoundsBefore), for review without Unreal."""
    wall_min_cm = spec["wallClearance"]["minCm"] if wall_min_cm is None else wall_min_cm
    plan = {"spec": str(SPEC_PATH), "wallClearanceMinCm": wall_min_cm, "groups": {}}
    for name in GROUP_ORDER:
        g = spec["groups"][name]
        loc = [g["currentXY"][0], g["currentXY"][1], spec["heikhal"]["floorZ"]]
        ev = evaluate_group(spec, name, loc, g["expectedBoundsBefore"], wall_min_cm)
        ev["enabledByDefault"] = g["enabledByDefault"]
        ev["book"] = g["book"]
        plan["groups"][name] = ev
    return plan


def parse_switches(command_line):
    inspect = "-keiliminspect" in command_line.lower()
    groups = None
    wall = None
    for token in command_line.split():
        low = token.lower()
        if low.startswith("-keilimgroups="):
            groups = [t.strip().lower() for t in token.split("=", 1)[1].strip('"').split(",") if t.strip()]
        elif low.startswith("-keilimwallclearancecm="):
            wall = float(token.split("=", 1)[1].strip('"'))
    return inspect, groups, wall


# --------------------------------------------------------------------------- Unreal run

def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return "release_scale_keilim.py" in command_line and ("-run=pythonscript" in command_line or "-executepythonscript" in command_line)


def _main():
    import unreal as ue

    spec = load_spec()
    ROOT = Path(spec["projectDir"])
    MAP = spec["targetMap"]
    MAP_FILE = ROOT / spec["targetMapFile"]
    OUT = ROOT / spec["receiptFolder"]
    heikhal = spec["heikhal"]
    FLOOR_Z = heikhal["floorZ"]
    TOL_B = spec["boundsToleranceCm"]
    TOL_R = spec["reopenToleranceCm"]
    TOL_S = spec["scaleTolerance"]
    TOL_Y = spec["yawToleranceDeg"]
    ident = spec["identification"]

    command_line = ue.SystemLibrary.get_command_line()
    INSPECT, requested, wall_override = parse_switches(command_line)
    wall_min_cm = spec["wallClearance"]["minCm"] if wall_override is None else wall_override
    if requested is not None:
        bad = [g for g in requested if g not in spec["groups"]]
        if bad:
            raise RuntimeError("unknown -KeilimGroups entries: " + ",".join(bad))
        enabled = [g for g in GROUP_ORDER if g in requested]
    else:
        enabled = [g for g in GROUP_ORDER if spec["groups"][g]["enabledByDefault"]]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT.mkdir(parents=True, exist_ok=True)
    receipt_path = OUT / f"{spec['receiptPrefix']}{stamp}.json"
    receipt = {
        "status": "started", "mode": "inspect" if INSPECT else "apply", "map": MAP, "stamp": stamp,
        "spec": str(SPEC_PATH), "specSha256": sha256_file(SPEC_PATH),
        "enabledGroups": enabled, "groupsSwitch": requested, "wallClearanceMinCm": wall_min_cm,
        "wallClearanceOverride": wall_override is not None,
        "mapSha256Before": sha256_file(MAP_FILE) if MAP_FILE.exists() else None,
        "groups": {}, "omitted": {}, "source": spec["source"],
    }
    before_sha = receipt["mapSha256Before"]

    def write_receipt():
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    write_receipt()

    def pose(actor):
        loc = actor.get_actor_location()
        rot = actor.get_actor_rotation()
        scl = actor.get_actor_scale3d()
        return {"location": [loc.x, loc.y, loc.z], "rotation": [rot.pitch, rot.yaw, rot.roll], "scale": [scl.x, scl.y, scl.z]}

    def bounds(actor):
        origin, extent = actor.get_actor_bounds(False)
        return {"min": [origin.x - extent.x, origin.y - extent.y, origin.z - extent.z],
                "max": [origin.x + extent.x, origin.y + extent.y, origin.z + extent.z]}

    def mesh_path(actor):
        comps = actor.get_components_by_class(ue.StaticMeshComponent)
        paths = sorted({c.static_mesh.get_path_name() for c in comps if c.static_mesh})
        return paths

    def bounds_close(a, b, tol):
        return max(abs(a[k][i] - b[k][i]) for k in ("min", "max") for i in range(3)) <= tol

    def yaw_close(a, b):
        d = abs(((a - b) + 180.0) % 360.0 - 180.0)
        return d <= TOL_Y

    scaled = []
    try:
        if not (ROOT / "MikdashCourtyardV3.uproject").exists():
            raise RuntimeError("project dir mismatch: " + str(ROOT))
        if not MAP_FILE.exists():
            raise RuntimeError("target map file missing: " + str(MAP_FILE))
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        if editor.get_game_world():
            raise RuntimeError("game world active")
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages() or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages():
            raise RuntimeError("dirty packages present before load; refusing")
        if not levels.load_level(MAP):
            raise RuntimeError("load_level failed")
        world = editor.get_editor_world()
        if world.get_outermost().get_name() != MAP:
            raise RuntimeError("wrong map loaded: " + str(world.get_outermost().get_name()))
        actors_api = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        actors = actors_api.get_all_level_actors()

        # Candidate vessels: static-mesh actors inside the Heikhal floor rectangle, above the
        # floor, excluding measured architecture / context folders.
        zlo, zhi = ident["candidateZRange"]
        candidates = []
        for a in actors:
            folder = str(a.get_folder_path())
            if any(folder.startswith(p) for p in ident["excludedFolderPrefixes"]):
                continue
            if not a.get_components_by_class(ue.StaticMeshComponent):
                continue
            loc = a.get_actor_location()
            if heikhal["xmin"] <= loc.x <= heikhal["xmax"] and heikhal["ymin"] <= loc.y <= heikhal["ymax"] and zlo <= loc.z <= zhi:
                candidates.append(a)
        receipt["heikhalCandidates"] = [{"label": a.get_actor_label(), "folder": str(a.get_folder_path()), **pose(a)} for a in candidates]

        # Cluster by current XY, then require label agreement (both directions).
        cluster_cm = ident["clusterCm"]
        matched = {name: [] for name in GROUP_ORDER}
        for a in candidates:
            loc = a.get_actor_location()
            hits = [n for n in GROUP_ORDER if abs(loc.x - spec["groups"][n]["currentXY"][0]) <= cluster_cm
                    and abs(loc.y - spec["groups"][n]["currentXY"][1]) <= cluster_cm]
            if len(hits) > 1:
                raise RuntimeError("actor matches two clusters: " + a.get_actor_label())
            if hits:
                matched[hits[0]].append(a)
            for n in GROUP_ORDER:
                if a.get_actor_label() == spec["groups"][n]["label"] and hits != [n]:
                    raise RuntimeError("actor %s carries the %s label but is not in its XY cluster (%s)"
                                       % (a.get_actor_label(), n, json.dumps([loc.x, loc.y])))
        receipt["unmatchedHeikhalCandidates"] = [a.get_actor_label() for a in candidates if not any(a in v for v in matched.values())]

        actor_of = {}
        for name in GROUP_ORDER:
            g = spec["groups"][name]
            found = matched[name]
            if len(found) != 1:
                raise RuntimeError("cluster %s expected exactly one actor, found %d: %s"
                                   % (name, len(found), json.dumps([a.get_actor_label() for a in found])))
            a = found[0]
            if a.get_actor_label() != g["label"]:
                raise RuntimeError("cluster %s label mismatch: %s" % (name, a.get_actor_label()))
            paths = mesh_path(a)
            if paths != [g["mesh"]]:
                raise RuntimeError("cluster %s mesh mismatch: %s" % (name, json.dumps(paths)))
            p = pose(a)
            b = bounds(a)
            entry = {"label": a.get_actor_label(), "folder": str(a.get_folder_path()), "mesh": paths[0],
                     "enabled": name in enabled, "before": p, "boundsBefore": b, "sizeBefore": size_of(b),
                     "book": g["book"], "scaleDerivation": g["scaleDerivation"]}
            receipt["groups"][name] = entry
            if not yaw_close(p["rotation"][1], g["expectedYaw"]):
                raise RuntimeError("cluster %s yaw %.3f differs from expected %.3f" % (name, p["rotation"][1], g["expectedYaw"]))
            already = all(abs(p["scale"][i] - g["scale"][i]) <= TOL_S for i in range(3))
            unit = all(abs(p["scale"][i] - 1.0) <= TOL_S for i in range(3))
            if already and not unit:
                entry["alreadyScaled"] = True
                entry["plan"] = {"omissionReasons": ["already at target scale"]}
                continue
            if not unit:
                raise RuntimeError("cluster %s has unexpected scale %s" % (name, json.dumps(p["scale"])))
            if not bounds_close(b, g["expectedBoundsBefore"], TOL_B):
                raise RuntimeError("cluster %s bounds differ from expectedBoundsBefore: %s" % (name, json.dumps(b)))
            plan = evaluate_group(spec, name, p["location"], b, wall_min_cm)
            entry["plan"] = plan
            actor_of[name] = a
            if name in enabled and plan["omissionReasons"]:
                receipt["omitted"][name] = plan["omissionReasons"]
        write_receipt()

        to_apply = [n for n in enabled if n in actor_of and not receipt["groups"][n]["plan"]["omissionReasons"]]
        receipt["groupsToApply"] = to_apply

        if INSPECT:
            receipt["status"] = "inspected_read_only"
        elif not to_apply:
            receipt["status"] = "nothing_to_apply_all_enabled_groups_omitted_or_already_scaled"
        else:
            checkpoint = Path(spec["checkpointRoot"]) / f"{spec['checkpointPrefix']}{stamp}"
            checkpoint.mkdir(parents=True, exist_ok=False)
            shutil.copy2(MAP_FILE, checkpoint / MAP_FILE.name)
            if sha256_file(checkpoint / MAP_FILE.name) != before_sha:
                raise RuntimeError("checkpoint copy sha mismatch")
            receipt["checkpoint"] = str(checkpoint)

            for name in to_apply:
                a = actor_of[name]
                g = spec["groups"][name]
                entry = receipt["groups"][name]
                plan = entry["plan"]
                sx, sy, sz = g["scale"]
                a.set_actor_scale3d(ue.Vector(sx, sy, sz))
                b = bounds(a)
                # Keep the base on the floor: compensate Z only if the pivot is not at the base.
                dz = FLOOR_Z - b["min"][2]
                entry["baseCompensationZ"] = dz
                if abs(dz) > TOL_R:
                    loc = a.get_actor_location()
                    if not a.set_actor_location(ue.Vector(loc.x, loc.y, loc.z + dz), False, False):
                        raise RuntimeError("Z compensation failed for " + name)
                    b = bounds(a)
                    if abs(b["min"][2] - FLOOR_Z) > TOL_R:
                        raise RuntimeError("base still off the floor after compensation for %s: %s" % (name, json.dumps(b)))
                p = pose(a)
                if abs(p["location"][0] - entry["before"]["location"][0]) > TOL_R or abs(p["location"][1] - entry["before"]["location"][1]) > TOL_R:
                    raise RuntimeError("XY changed during scaling for " + name)
                if g["yawMustNotChange"] and not yaw_close(p["rotation"][1], entry["before"]["rotation"][1]):
                    raise RuntimeError("yaw changed during scaling for " + name)
                predicted = plan["predictedBoundsAfter"]
                if abs(dz) > TOL_R:  # prediction assumed no Z compensation; shift it by the applied dz
                    predicted = {k: [v[0], v[1], v[2] + dz] for k, v in predicted.items()}
                if not bounds_close(b, predicted, TOL_B):
                    raise RuntimeError("scaled bounds differ from prediction for %s: %s" % (name, json.dumps(b)))
                post_clear = wall_clearance(b, heikhal)
                post_violation = heikhal_violation(b, heikhal, spec["heikhalWallMarginCm"])
                ns = min(post_clear["north"], post_clear["south"])
                if post_violation or ns < wall_min_cm:
                    raise RuntimeError("post-scale clearance check failed for %s: %s / %.2f cm" % (name, json.dumps(post_violation), ns))
                entry["appliedPose"] = p
                entry["appliedBounds"] = b
                entry["appliedSize"] = size_of(b)
                entry["appliedWallClearanceCm"] = post_clear
                scaled.append((name, a.get_actor_label(), p, b))
            receipt["scaledCount"] = len(scaled)
            write_receipt()

            if not levels.save_current_level():
                raise RuntimeError("save failed")
            receipt["mapSaved"] = True
            if not levels.load_level(MAP):
                raise RuntimeError("reopen failed")
            reopened = {a.get_actor_label(): a for a in ue.get_editor_subsystem(ue.EditorActorSubsystem).get_all_level_actors()}
            for name, label, p_applied, b_applied in scaled:
                a = reopened.get(label)
                if a is None:
                    raise RuntimeError("reopened actor missing: " + label)
                p = pose(a)
                b = bounds(a)
                entry = receipt["groups"][name]
                entry["after"] = p
                entry["boundsAfter"] = b
                entry["sizeAfter"] = size_of(b)
                err_loc = max(abs(p["location"][i] - p_applied["location"][i]) for i in range(3))
                err_scale = max(abs(p["scale"][i] - p_applied["scale"][i]) for i in range(3))
                err_b = max(abs(b[k][i] - b_applied[k][i]) for k in ("min", "max") for i in range(3))
                entry["reopenErrorCm"] = max(err_loc, err_b)
                entry["reopenScaleError"] = err_scale
                entry["reopenYawOk"] = yaw_close(p["rotation"][1], p_applied["rotation"][1])
                if err_loc > TOL_R or err_b > TOL_B or err_scale > TOL_S or not entry["reopenYawOk"]:
                    raise RuntimeError("reopened pose differs for " + label)
                if abs(b["min"][2] - FLOOR_Z) > TOL_R:
                    raise RuntimeError("reopened base not on floor for " + label)
            receipt["status"] = ("keilim_scaled_saved_reopened_visual_review_pending"
                                 + ("_with_omissions" if receipt["omitted"] else ""))
    except Exception as exc:  # noqa: BLE001
        receipt.update(status="failed", error=str(exc))
    finally:
        receipt["mapSha256After"] = sha256_file(MAP_FILE) if MAP_FILE.exists() else None
        receipt["mapBytesChanged"] = receipt["mapSha256After"] != before_sha
        write_receipt()
        summary = {k: receipt.get(k) for k in ("status", "mode", "mapBytesChanged", "groupsToApply", "omitted", "error")}
        ue.log(spec["logTag"] + " " + json.dumps(summary))


if __name__ == "__main__":
    if _unreal_available():
        _main()
    else:
        wall = None
        for arg in sys.argv[1:]:
            if arg.lower().startswith("-keilimwallclearancecm="):
                wall = float(arg.split("=", 1)[1])
        print(json.dumps(offline_plan(load_spec(), wall), indent=2))
elif _invoked_as_native_script():
    _main()
