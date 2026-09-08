"""Guarded static-geometry optimisation for the combined Walkthrough map.

WHY THIS EXISTS
---------------
perf-probe-20260908T102520Z.json measured the first real frame times this project has
had: 17.5-24.6 ms p50 against a 16.7 ms budget, over a census of 7,767 actors, 7,742
non-instanced StaticMeshComponents, 7,520 unique static meshes and only 190 Nanite
meshes. This script diagnoses where those meshes come from and applies the one lever
that fits the shape of the problem: Nanite on the static architecture and city.

MODES (switch read from the engine command line, default `analyze`)
------------------------------------------------------------------
  -PerfMode=analyze        Read-only. Loads the map, walks every StaticMeshComponent,
                           classifies every unique mesh by content folder, records
                           triangles, LODs, material blend modes, section counts, cull
                           distances and Nanite state, applies the eligibility rule and
                           writes a receipt plus a full mesh index. Mutates nothing.
  -PerfMode=nanite         Enables Nanite on the meshes the rule admits, in a bounded
                           batch, saving as it goes. Resumable: state is read from the
                           assets themselves, never from a side file.
  -PerfMode=revert_nanite  Reads an `applied` receipt and turns Nanite back off for
                           exactly the meshes that receipt says this tool turned on.
  -PerfMode=cull           Sets a max draw distance on the far-city categories only.
  -PerfMode=revert_cull    Restores the recorded previous draw distances.

  -PerfLimit=N             Stop after N meshes this run. A memory valve: this is a 16 GB
                           machine and a Nanite build is not free.
  -PerfChunk=N             Meshes per set-then-save chunk (default 200). See below.
  -PerfApplyChanges        Force the synchronous rebuild path. Slow; see below.
  -PerfCategories=a,b      Restrict to these categories (see CATEGORY_RULES).
  -PerfReceipt=<path>      Receipt to read for a revert mode.
  -PerfDryRun              Decide and report, write nothing.

COMMANDLET INVOCATION (serial; never while another engine job is running)

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/perf_optimize.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Perf-Optimize-01.log"
      -PerfMode=analyze

The MUTATING modes need StaticMeshEditorSubsystem, which the commandlet does not have.
Launch those through the hidden editor instead:

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -ExecutePythonScript="C:/Mikdash/.../Scripts/perf_optimize.py"
      -unattended -nullrhi -NoSplash
      -abslog="C:/Mikdash/Working-5.8/Perf-Nanite-01.log"
      -PerfMode=nanite -PerfLimit=1500

THE NANITE ELIGIBILITY RULE, IN FULL
------------------------------------
A unique StaticMesh is eligible when ALL of these hold. Every mesh that fails records
which clause rejected it, so the rule is auditable from the receipt.

  E1  It is referenced by at least one StaticMeshComponent in the combined map, so it
      actually costs a draw today.
  E2  Nanite is not already enabled on it. Existing Nanite settings are never touched --
      the frieze panels are Nanite-displaced and a blanket rewrite would flatten them.
      That exact regression has already happened once in this project.
  E3  No material slot resolves to a translucent, additive or modulated blend mode.
      Nanite does not render translucency; enabling it would make those sections
      vanish, which is a LOOK change, not a draw change.
  E4  Its category is on MUTABLE_CATEGORIES, an allowlist of content namespaces that
      have actually been read and reviewed. An allowlist, not a blocklist, because
      about a dozen other agents are writing new assets into new namespaces while this
      runs -- the vegetation agent is generating foliage cards right now -- and a
      blocklist would silently admit whatever it had not heard of yet.
  E5  Neither its path nor its name contains an excluded WORD. Matching is on whole
      snake_case/CamelCase tokens, never substrings. The first version of this rule used
      substrings and rejected all 2,875 street meshes because "S-tree-ts" contains
      "tree", every gate leaf because a door leaf is a "leaf", and the golden roof's
      anti-bird points because they contain "bird". Whole-token matching is not a detail.
  E6  It has at least MIN_TRIANGLES triangles.

Masked materials are ALLOWED: Nanite supports masked, and excluding them would drop most
of the window and grille detail for no reason.

MIN_TRIANGLES is 0 deliberately. The usual advice against Nanite on low-poly meshes is
about cluster memory, and it does not apply here: the census found 2,254 architecture
meshes of 12-23 triangles, each one a separate actor and a separate draw call. Their
triangles are free and their draw calls are the entire problem, so they are exactly the
meshes this pass exists for.

WHY THE NANITE PASS IS CHUNKED
------------------------------
Enabling Nanite invalidates a mesh's derived data, so the engine rebuilds its render
data, its Nanite pages AND its mesh distance field. The obvious loop -- set one mesh,
save one mesh -- serialises all of that: the first attempt at this managed 14 meshes in
nine minutes, because `set_nanite_settings(..., apply_changes=True)` blocks on a
synchronous Build and the save then blocks again on "Waiting for static meshes to be
ready 0/1". At that rate 7,230 meshes is a day.

So the pass runs in chunks: set the property on every mesh in the chunk first, which
hands them all to the asynchronous static mesh compiler at once, and only then save the
chunk, so each save waits on work that has been running in parallel across every core
rather than starting it. `-PerfApplyChanges` restores the old synchronous behaviour for
the rare case where a build must be proven finished before the script returns.

Chunk size is the memory valve. Every mesh in a chunk is resident and compiling at the
same time, and this is a 16 GB machine.

WHAT THIS SCRIPT WILL NOT DO
----------------------------
It does not merge, weld, delete, move or re-author any geometry, and it does not touch
materials. Nanite is a change to how a mesh is drawn, not to what it looks like. If any
receipt in this family ever reports a change to a material, a transform or a vertex, that
is a bug and the run should be reverted.

UE 5.8 PYTHON PITFALLS HANDLED HERE (AGENTS.md)
-----------------------------------------------
  * `StaticMesh.post_edit_change()` DOES NOT EXIST in UE 5.8 Python. The recipe copied
    from release_oldcity_facades.py called it and failed 1500/1500 with
    AttributeError; that call had never actually run there, because the meshes it
    guarded were already Nanite from import and the branch was skipped. The working
    path is StaticMeshEditorSubsystem.set_nanite_settings(mesh, settings, True), which
    also rebuilds the mesh so the Nanite data lands in the DDC here rather than at map
    load. That subsystem is None under -run=pythonscript, so this script is launched
    with `UnrealEditor.exe -ExecutePythonScript` instead; it is fully synchronous and
    has no tick callbacks, so the early-exit hazard that mode has does not apply.
    set_editor_property alone is kept as a fallback and the receipt records which path
    each mesh took.
  * Setters are verified by readback, never trusted.
  * unreal.Rotator needs keyword arguments (not used here, but noted).
  * Receipts are written at start and again in finally so failures are preserved.
"""

import gc
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import unreal

ROOT = Path(r"C:\Mikdash\Working-5.8\MikdashCourtyardV3")
CHECKPOINT_ROOT = Path(r"C:\Mikdash\Working-5.8\ReviewCheckpoints")
TARGET_MAP = "/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough"
MAP_FILE = ROOT / "Content/MikdashV3/IntegratedReviewV2/Maps/Walkthrough.umap"
OUTPUT_DIR = ROOT / "SourceAssets/perf-review"

MIN_TRIANGLES = 0

# Category is decided by the longest matching content-path prefix. Order is longest-first
# at match time, so the order here is documentation, not precedence.
CATEGORY_RULES = [
    ("oldcity_facades", "/Game/MikdashV3/JerusalemContext/OldCityFacadesV1/"),
    ("city_streets", "/Game/MikdashV3/JerusalemContext/Streets/"),
    ("city_buildings", "/Game/MikdashV3/JerusalemContext/Buildings/"),
    ("terrain_tiles", "/Game/MikdashV3/JerusalemContext/Terrain/"),
    ("city_decor", "/Game/MikdashV3/JerusalemContext/DecorativeInstancesV1/"),
    ("jerusalem_other", "/Game/MikdashV3/JerusalemContext/"),
    ("mikdash_architecture", "/Game/MikdashV3/Architecture/"),
    ("material_review", "/Game/MikdashV3/MaterialReview/"),
    ("character_review", "/Game/MikdashV3/CharacterReview/"),
    ("arrival_review", "/Game/MikdashV3/ArrivalReview/"),
    ("third_party", "/Game/MikdashV3/ThirdParty/"),
    ("runtime", "/Game/MikdashV3/Runtime/"),
    ("engine_content", "/Engine/"),
]

# E4. The allowlist. Every one of these was read out of the census before being added:
#   city_streets          2,875 meshes, 305 k triangles TOTAL -- road and path polygons
#   mikdash_architecture  2,633 meshes,  87 k triangles TOTAL -- the Mikdash's own stone
#   city_buildings        1,498 meshes, 243 k triangles TOTAL -- extruded OSM massing
#   terrain_tiles           252 meshes, 129 k triangles TOTAL -- FutureMountV1 tiles
#   material_review          39 meshes,  26.7 M triangles      -- friezes, Kotel, keilim
#   third_party               2 meshes,   0.92 M triangles     -- the Aron
#   other                     8 meshes                         -- mount platform, cuts
# Deliberately NOT here: city_decor (already 5 HISMs, nothing to win, and it holds the
# tree crowns and trunks), arrival_review (the transit agent's moving vehicles),
# character_review and runtime (skeletal and crowd), oldcity_facades (already Nanite).
MUTABLE_CATEGORIES = {
    "city_streets",
    "city_buildings",
    "terrain_tiles",
    "mikdash_architecture",
    "material_review",
    "third_party",
    "other",
}

# E5. Whole-token match, on the object path and on the asset name. Tokens are split on
# non-alphanumerics AND on CamelCase boundaries, so "Streets" yields "streets" and never
# "tree", while "Tree_crowns" yields "tree" and is correctly rejected.
EXCLUDED_TOKENS = {
    # vegetation the foliage pass owns; Nanite is wrong for camera-facing cards
    "vegetation", "foliage", "tree", "trees", "shrub", "grass", "bush", "hedge",
    "canopy", "sapling", "olive", "cypress",
    # anything that is or carries translucency
    "water", "glass", "translucent", "alpha", "lens", "smoke", "plume", "flame",
    "steam", "mist", "haze",
    # cards, decals, cloth: WPO or alpha or both
    "card", "cards", "billboard", "impostor", "decal", "cloth", "fabric", "banner",
    "flag", "curtain", "veil", "paroches", "wpo",
    # other agents live namespaces
    "niagara", "particle", "crowd", "pilgrim", "resident", "bird", "birds",
}

# Tokens that look excluded but are NOT, because in this project they name carved stone
# and metal, not the thing the token usually means. Checked against the census before
# being listed here; each one is a mesh whose look must not change and whose draw call
# is worth collapsing.
#   leaf   -> "Outer_E_open_gate_leaf": a door leaf, 277 meshes
#   frond  -> "Carved_palm_frond": carved stone, 112 meshes
#   fire   -> "Hearth_firebox_opening": a stone opening, 48 meshes
#   bird   -> "Golden_roof_anti_bird_point": a metal spike, 70 meshes
# The first three are absent from EXCLUDED_TOKENS. "bird" IS in it, and whole-token
# matching means "anti_bird_point" still matches it, so those 70 spikes stay non-Nanite.
# That is 70 draw calls left on the table in exchange for never reaching the bird agent.
TOKEN_FALSE_FRIENDS = ["leaf", "leaves", "frond", "palm", "firebox", "hearth", "streets"]

TRANSLUCENT_BLEND_MODES = {"BLEND_TRANSLUCENT", "BLEND_ADDITIVE", "BLEND_MODULATE",
                           "BLEND_ALPHACOMPOSITE", "BLEND_ALPHAHOLDOUT",
                           "BLEND_ALPHA_COMPOSITE", "BLEND_ALPHA_HOLDOUT"}

# Categories the cull mode is allowed to touch, with their max draw distance in cm.
# Nothing inside the Mikdash is ever culled: the building is the subject.
CULL_DISTANCES_CM = {
    "city_streets": 250000.0,
    "city_buildings": 300000.0,
    "oldcity_facades": 300000.0,
}


# --------------------------------------------------------------------------- switches

def command_line_switches():
    try:
        raw = unreal.SystemLibrary.get_command_line()
    except Exception:  # noqa: BLE001
        raw = " ".join(sys.argv)
    out = {}
    for token in re.findall(r'-([A-Za-z_]+)(?:=("[^"]*"|\S+))?', raw or ""):
        key, value = token[0].lower(), (token[1] or "").strip('"')
        out[key] = value if value else "1"
    return out


SWITCHES = command_line_switches()
MODE = (SWITCHES.get("perfmode") or "analyze").lower()
LIMIT = int(SWITCHES.get("perflimit") or 0)
DRY_RUN = SWITCHES.get("perfdryrun", "0") == "1"
ONLY_CATEGORIES = [c for c in (SWITCHES.get("perfcategories") or "").split(",") if c]
RECEIPT_IN = SWITCHES.get("perfreceipt") or ""
CHUNK = max(1, int(SWITCHES.get("perfchunk") or 200))
APPLY_CHANGES = SWITCHES.get("perfapplychanges", "0") == "1"


def stamp_now():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_of(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def categorise(path):
    best = ("other", 0)
    for name, prefix in CATEGORY_RULES:
        if path.startswith(prefix) and len(prefix) > best[1]:
            best = (name, len(prefix))
    return best[0]


TOKEN_SPLIT = re.compile(r"[^A-Za-z0-9]+|(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def tokens_of(text):
    """Whole words, split on non-alphanumerics and on CamelCase boundaries."""
    return {t.lower() for t in TOKEN_SPLIT.split(text) if t}


def blend_mode_name(value):
    """Enum name, upper-cased.

    str(enum) is "<BlendMode.BLEND_OPAQUE: 0>" in UE Python, so the naive
    str().split(".")[-1] yields "BLEND_OPAQUE: 0>" and never compares equal to anything.
    That bug made the translucency guard a silent no-op in the first analyze run. It is
    fixed here, and the guard is now redundant with the token rule rather than replaced
    by it: the two translucent meshes in the map are caught by both.
    """
    try:
        return str(value.name).upper()
    except Exception:  # noqa: BLE001
        pass
    text = str(value)
    match = re.search(r"(BLEND_[A-Za-z_]+)", text)
    return (match.group(1) if match else text).upper()


def material_blend_modes(mesh):
    """Every blend mode this mesh will actually render with, instance overrides included."""
    modes = set()
    try:
        materials = mesh.get_editor_property("static_materials")
    except Exception:  # noqa: BLE001
        return {"BLEND_Unknown"}
    for slot in materials:
        try:
            interface = slot.get_editor_property("material_interface")
        except Exception:  # noqa: BLE001
            interface = None
        if interface is None:
            continue
        override = None
        if isinstance(interface, unreal.MaterialInstance):
            try:
                overrides = interface.get_editor_property("base_property_overrides")
                if overrides.get_editor_property("override_blend_mode"):
                    override = overrides.get_editor_property("blend_mode")
            except Exception:  # noqa: BLE001
                override = None
        if override is not None:
            modes.add(blend_mode_name(override))
            continue
        try:
            base = interface.get_base_material()
            modes.add(blend_mode_name(base.get_editor_property("blend_mode")))
        except Exception:  # noqa: BLE001
            modes.add("BLEND_Unknown")
    return modes or {"BLEND_NoMaterial"}


def excluded_token(path, name):
    hit = EXCLUDED_TOKENS.intersection(tokens_of(path) | tokens_of(name))
    return sorted(hit)[0] if hit else None


# ------------------------------------------------------------------------- the census

class Census:
    """One walk of the level; everything else reads from this."""

    def __init__(self):
        self.meshes = {}          # path -> record
        self.actor_count = 0
        self.component_count = 0
        self.instanced_component_count = 0
        self.instance_count = 0
        self.drawn_sections = 0   # sections x primitives: the draw-call proxy
        self.cull_set = 0

    def run(self):
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actors = subsystem.get_all_level_actors()
        self.actor_count = len(actors)
        for actor in actors:
            for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
                mesh = comp.get_editor_property("static_mesh")
                if mesh is None:
                    continue
                instanced = isinstance(comp, unreal.InstancedStaticMeshComponent)
                per_instance = comp.get_instance_count() if instanced else 1
                if instanced:
                    self.instanced_component_count += 1
                    self.instance_count += per_instance
                else:
                    self.component_count += 1
                record = self.record_for(mesh)
                record["components"] += 1
                record["primitives"] += per_instance
                self.drawn_sections += record["sections"] * (1 if instanced else 1)
                try:
                    cull = float(comp.get_editor_property("ld_max_draw_distance"))
                except Exception:  # noqa: BLE001
                    cull = -1.0
                if cull > 0.0:
                    self.cull_set += 1
                    record["cullDistances"].add(cull)
        return self

    def record_for(self, mesh):
        path = mesh.get_path_name()
        if path in self.meshes:
            return self.meshes[path]
        name = mesh.get_name()
        try:
            triangles = int(mesh.get_num_triangles(0))
        except Exception:  # noqa: BLE001
            triangles = -1
        try:
            vertices = int(mesh.get_num_vertices(0))
        except Exception:  # noqa: BLE001
            vertices = -1
        try:
            lods = int(mesh.get_num_lods())
        except Exception:  # noqa: BLE001
            lods = -1
        try:
            sections = int(mesh.get_num_sections(0))
        except Exception:  # noqa: BLE001
            sections = 1
        try:
            nanite = bool(mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))
        except Exception:  # noqa: BLE001
            nanite = None
        record = {
            "path": path,
            "name": name,
            "category": categorise(path),
            "triangles": triangles,
            "vertices": vertices,
            "lods": lods,
            "sections": sections,
            "nanite": nanite,
            "blendModes": sorted(material_blend_modes(mesh)),
            "components": 0,
            "primitives": 0,
            "cullDistances": set(),
        }
        self.meshes[path] = record
        return record


def eligibility(record):
    """The rule from the module docstring. Returns (eligible, reason)."""
    if record["components"] <= 0:
        return False, "E1_not_drawn"
    if record["nanite"]:
        return False, "E2_already_nanite"
    if record["nanite"] is None:
        return False, "E2_nanite_state_unreadable"
    translucent = TRANSLUCENT_BLEND_MODES.intersection(
        blend.upper() for blend in record["blendModes"])
    if translucent:
        return False, "E3_translucent_%s" % sorted(translucent)[0]
    if record["category"] not in MUTABLE_CATEGORIES:
        return False, "E4_category_not_allowlisted_%s" % record["category"]
    token = excluded_token(record["path"], record["name"])
    if token:
        return False, "E5_token_%s" % token
    if record["triangles"] < MIN_TRIANGLES:
        return False, "E6_below_%d_triangles" % MIN_TRIANGLES
    return True, "eligible"


# --------------------------------------------------------------------------- the run

class Run:
    def __init__(self):
        self.stamp = stamp_now()
        self.receipt = {
            "status": "started",
            "mode": MODE,
            "stamp": self.stamp,
            "map": TARGET_MAP,
            "dryRun": DRY_RUN,
            "limit": LIMIT,
            "onlyCategories": ONLY_CATEGORIES,
            "rule": {
                "minTriangles": MIN_TRIANGLES,
                "mutableCategories": sorted(MUTABLE_CATEGORIES),
                "excludedTokens": sorted(EXCLUDED_TOKENS),
                "tokenFalseFriendsDeliberatelyAllowed": TOKEN_FALSE_FRIENDS,
                "tokenMatching": "whole snake_case/CamelCase words, never substrings",
                "translucentBlendModes": sorted(TRANSLUCENT_BLEND_MODES),
                "maskedAllowed": True,
                "existingNaniteSettingsNeverModified": True,
            },
        }
        self.path = OUTPUT_DIR / ("perf-optimize-%s-%s.json" % (MODE, self.stamp))
        self.index_path = OUTPUT_DIR / ("perf-optimize-meshindex-%s.json" % self.stamp)

    # -- guards ------------------------------------------------------------

    def guard(self):
        assert ROOT.is_dir(), "project directory missing: %s" % ROOT
        assert MAP_FILE.is_file(), "map file missing: %s" % MAP_FILE
        editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        world = editor.get_editor_world()
        if world is None or not world.get_path_name().startswith(TARGET_MAP):
            unreal.EditorLoadingAndSavingUtils.load_map(TARGET_MAP)
            world = editor.get_editor_world()
        assert world is not None and world.get_path_name().startswith(TARGET_MAP), (
            "wrong map open: %s" % (world.get_path_name() if world else "none"))
        dirty = unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
        assert not dirty, "dirty map packages present: %s" % [p.get_name() for p in dirty]
        self.receipt["mapSha256Before"] = sha256_of(MAP_FILE)
        return world

    def checkpoint(self, label):
        """Copy the umap before any mutation, and verify the copy byte-for-byte."""
        target = CHECKPOINT_ROOT / ("%s-%s" % (label, self.stamp))
        target.mkdir(parents=True, exist_ok=True)
        dest = target / MAP_FILE.name
        shutil.copy2(MAP_FILE, dest)
        ok = sha256_of(dest) == self.receipt["mapSha256Before"]
        self.receipt["checkpoint"] = {"dir": str(target), "verified": ok}
        assert ok, "checkpoint copy did not verify"
        return target

    # -- modes -------------------------------------------------------------

    def analyze(self, census):
        by_category = {}
        eligible_records = []
        rejects = {}
        for record in census.meshes.values():
            ok, reason = eligibility(record)
            record["eligible"] = ok
            record["reason"] = reason
            cat = record["category"]
            bucket = by_category.setdefault(cat, {
                "uniqueMeshes": 0, "components": 0, "primitives": 0,
                "triangles": 0, "sections": 0, "naniteAlready": 0,
                "eligible": 0, "rejected": 0, "cullDistancesSeen": set(),
            })
            bucket["uniqueMeshes"] += 1
            bucket["components"] += record["components"]
            bucket["primitives"] += record["primitives"]
            bucket["triangles"] += max(0, record["triangles"]) * record["primitives"]
            bucket["sections"] += record["sections"] * record["components"]
            bucket["cullDistancesSeen"] |= record["cullDistances"]
            if record["nanite"]:
                bucket["naniteAlready"] += 1
            if ok:
                bucket["eligible"] += 1
                eligible_records.append(record)
            else:
                bucket["rejected"] += 1
                rejects[reason] = rejects.get(reason, 0) + 1
        for bucket in by_category.values():
            bucket["cullDistancesSeen"] = sorted(bucket.pop("cullDistancesSeen"))

        self.receipt["census"] = {
            "actorCount": census.actor_count,
            "staticMeshComponents": census.component_count,
            "instancedComponents": census.instanced_component_count,
            "instanceCount": census.instance_count,
            "uniqueMeshes": len(census.meshes),
            "naniteMeshes": sum(1 for r in census.meshes.values() if r["nanite"]),
            "drawnSectionsLowerBound": sum(
                r["sections"] * r["components"] for r in census.meshes.values()),
            "componentsWithCullDistance": census.cull_set,
        }
        self.receipt["byCategory"] = dict(sorted(
            by_category.items(), key=lambda kv: -kv[1]["uniqueMeshes"]))
        self.receipt["eligibleTotal"] = len(eligible_records)
        self.receipt["rejectionReasons"] = dict(sorted(rejects.items(), key=lambda kv: -kv[1]))
        self.receipt["meshIndex"] = str(self.index_path)

        # Duplicate-geometry probe: meshes with identical triangle+vertex+section counts
        # inside one category are candidates for instancing or merging. Reported, never
        # acted on automatically -- identical counts are not proof of identical geometry.
        signatures = {}
        for record in census.meshes.values():
            key = (record["category"], record["triangles"], record["vertices"], record["sections"])
            signatures.setdefault(key, []).append(record["name"])
        duplicate_groups = [
            {"category": k[0], "triangles": k[1], "vertices": k[2], "count": len(v),
             "sample": sorted(v)[:4]}
            for k, v in signatures.items() if len(v) > 4
        ]
        duplicate_groups.sort(key=lambda g: -g["count"])
        self.receipt["possibleInstancingGroups"] = duplicate_groups[:40]
        self.receipt["possibleInstancingMeshTotal"] = sum(
            g["count"] for g in duplicate_groups)

        index = [
            {k: (sorted(v) if isinstance(v, set) else v) for k, v in record.items()}
            for record in census.meshes.values()
        ]
        if not DRY_RUN:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            self.index_path.write_text(json.dumps(index, indent=1), encoding="utf-8")
        return eligible_records

    def world_audit(self, world):
        settings = world.get_world_settings()
        audit = {}
        for key in ("enable_hierarchical_lo_ds", "num_hlod_levels", "bEnableHierarchicalLODSystem"):
            try:
                audit[key] = settings.get_editor_property(key)
            except Exception:  # noqa: BLE001
                pass
        try:
            audit["worldPartition"] = world.get_editor_property("world_partition") is not None
        except Exception:  # noqa: BLE001
            audit["worldPartition"] = None
        try:
            audit["hlodActors"] = len([
                a for a in unreal.get_editor_subsystem(
                    unreal.EditorActorSubsystem).get_all_level_actors()
                if "HLOD" in a.get_class().get_name()])
        except Exception:  # noqa: BLE001
            audit["hlodActors"] = None
        self.receipt["worldAudit"] = audit

    @staticmethod
    def mesh_editor_subsystem():
        try:
            return unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def set_nanite(mesh, enabled, subsystem):
        """Turn Nanite on or off and say which mechanism did it.

        Returns (readback, mechanism). Never trusts a setter: the value is read back off
        the asset afterwards either way. The subsystem path is used only under
        -PerfApplyChanges because it blocks on a synchronous rebuild; the default path
        lets the asynchronous static mesh compiler do the work while the chunk fills.
        """
        settings = mesh.get_editor_property("nanite_settings")
        settings.set_editor_property("enabled", enabled)
        mechanism = "set_editor_property"
        if APPLY_CHANGES and subsystem is not None:
            try:
                subsystem.set_nanite_settings(mesh, settings, True)
                mechanism = "StaticMeshEditorSubsystem.set_nanite_settings"
            except Exception:  # noqa: BLE001
                mesh.set_editor_property("nanite_settings", settings)
        else:
            mesh.set_editor_property("nanite_settings", settings)
        readback = bool(mesh.get_editor_property("nanite_settings")
                        .get_editor_property("enabled"))
        return readback, mechanism

    def apply_nanite(self, eligible_records):
        records = eligible_records
        if ONLY_CATEGORIES:
            records = [r for r in records if r["category"] in ONLY_CATEGORIES]
        records.sort(key=lambda r: (-r["triangles"] * max(1, r["primitives"]), r["path"]))
        if LIMIT > 0:
            records = records[:LIMIT]

        subsystem = self.mesh_editor_subsystem()
        self.receipt["staticMeshEditorSubsystem"] = subsystem is not None
        self.receipt["chunkSize"] = CHUNK
        self.receipt["applyChanges"] = APPLY_CHANGES
        applied, failed, skipped, mechanisms = [], [], 0, {}
        started = time.time()

        for offset in range(0, len(records), CHUNK):
            chunk = records[offset:offset + CHUNK]
            pending = []

            # Phase 1: set the flag on the whole chunk, handing every mesh to the async
            # compiler before waiting on any of them.
            for record in chunk:
                if DRY_RUN:
                    applied.append({"path": record["path"], "dryRun": True})
                    continue
                mesh = unreal.load_asset(record["path"])
                if mesh is None:
                    failed.append({"path": record["path"],
                                   "error": "load_asset returned None"})
                    continue
                try:
                    if mesh.get_editor_property(
                            "nanite_settings").get_editor_property("enabled"):
                        skipped += 1  # an earlier run did it; this mode is resumable
                        continue
                    readback, mechanism = self.set_nanite(mesh, True, subsystem)
                except Exception as error:  # noqa: BLE001
                    failed.append({"path": record["path"], "error": repr(error)})
                    continue
                if not readback:
                    failed.append({"path": record["path"],
                                   "error": "readback said Nanite off"})
                    continue
                mechanisms[mechanism] = mechanisms.get(mechanism, 0) + 1
                pending.append(record)

            # Phase 2: save. Each save blocks on that mesh's build, but the builds have
            # been running in parallel since phase 1 put them in flight.
            for record in pending:
                saved = unreal.EditorAssetLibrary.save_asset(record["path"],
                                                             only_if_is_dirty=False)
                if not saved:
                    failed.append({"path": record["path"],
                                   "error": "save_asset returned False"})
                    continue
                applied.append({"path": record["path"], "triangles": record["triangles"],
                                "category": record["category"], "saved": True})

            gc.collect()
            unreal.log("MIKDASH_PERF_OPTIMIZE progress %d/%d applied=%d failed=%d %.0fs"
                       % (min(offset + CHUNK, len(records)), len(records),
                          len(applied), len(failed), time.time() - started))
            # The receipt is rewritten every chunk so a kill or an out-of-memory leaves
            # an accurate record of what was already changed and saved.
            self.receipt["naniteApplied"] = len(applied)
            self.receipt["appliedPaths"] = [a["path"] for a in applied]
            self.receipt["naniteFailed"] = len(failed)
            self.receipt["status"] = "in_progress"
            self.write()

        self.receipt["naniteAlreadyOn"] = skipped
        self.receipt["mechanisms"] = mechanisms
        self.receipt["naniteApplied"] = len(applied)
        self.receipt["naniteFailed"] = len(failed)
        self.receipt["naniteFailures"] = failed[:50]
        self.receipt["appliedPaths"] = [a["path"] for a in applied]
        self.receipt["appliedByCategory"] = {}
        for entry in applied:
            cat = entry.get("category", "dryRun")
            self.receipt["appliedByCategory"][cat] = \
                self.receipt["appliedByCategory"].get(cat, 0) + 1
        self.receipt["candidatesRemaining"] = len(eligible_records) - len(applied)
        self.receipt["elapsedSeconds"] = round(time.time() - started, 1)

    def revert_nanite(self):
        source = Path(RECEIPT_IN)
        assert source.is_file(), "-PerfReceipt must name an existing applied receipt"
        previous = json.loads(source.read_text(encoding="utf-8-sig"))
        paths = previous.get("appliedPaths") or []
        assert paths, "receipt lists no appliedPaths"
        reverted, failed = [], []
        for path in paths:
            if DRY_RUN:
                reverted.append(path)
                continue
            mesh = unreal.load_asset(path)
            if mesh is None:
                failed.append({"path": path, "error": "load_asset returned None"})
                continue
            try:
                readback, _ = self.set_nanite(mesh, False, self.mesh_editor_subsystem())
                if readback:
                    failed.append({"path": path, "error": "readback said Nanite still on"})
                    continue
                unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
                reverted.append(path)
            except Exception as error:  # noqa: BLE001
                failed.append({"path": path, "error": repr(error)})
        self.receipt["revertedFrom"] = str(source)
        self.receipt["reverted"] = len(reverted)
        self.receipt["revertFailed"] = failed[:50]

    def apply_cull(self, census, world):
        """Max draw distance on far-city categories only. Never inside the Mikdash."""
        changed = []
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        for actor in subsystem.get_all_level_actors():
            for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
                mesh = comp.get_editor_property("static_mesh")
                if mesh is None:
                    continue
                category = categorise(mesh.get_path_name())
                target = CULL_DISTANCES_CM.get(category)
                if not target:
                    continue
                try:
                    before = float(comp.get_editor_property("ld_max_draw_distance"))
                except Exception:  # noqa: BLE001
                    continue
                if abs(before - target) < 1.0:
                    continue
                if DRY_RUN:
                    changed.append({"actor": actor.get_actor_label(), "category": category,
                                    "before": before, "after": target, "dryRun": True})
                    continue
                comp.set_editor_property("ld_max_draw_distance", target)
                comp.set_editor_property("cached_max_draw_distance", target)
                after = float(comp.get_editor_property("ld_max_draw_distance"))
                changed.append({"actor": actor.get_actor_label(), "category": category,
                                "before": before, "after": after})
        self.receipt["cullChanged"] = len(changed)
        self.receipt["cullSample"] = changed[:20]
        self.receipt["cullDistancesCm"] = CULL_DISTANCES_CM

    def save_map(self):
        if DRY_RUN:
            return
        ok = unreal.EditorLoadingAndSavingUtils.save_map(
            unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world(),
            str(MAP_FILE))
        self.receipt["mapSaved"] = bool(ok)
        self.receipt["mapSha256After"] = sha256_of(MAP_FILE)

    # -- driver ------------------------------------------------------------

    def go(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.write()
        try:
            world = self.guard()
            if MODE == "revert_nanite":
                self.revert_nanite()
                self.receipt["status"] = "completed"
                return
            census = Census().run()
            eligible = self.analyze(census)
            self.world_audit(world)
            if MODE == "analyze":
                self.receipt["status"] = "completed"
                return
            if MODE == "nanite":
                if not DRY_RUN:
                    self.checkpoint("PerfNanite")
                self.apply_nanite(eligible)
                self.receipt["status"] = "completed"
                return
            if MODE == "cull":
                if not DRY_RUN:
                    self.checkpoint("PerfCull")
                self.apply_cull(census, world)
                self.save_map()
                self.receipt["status"] = "completed"
                return
            raise RuntimeError("unknown -PerfMode=%s" % MODE)
        except Exception as error:  # noqa: BLE001
            self.receipt["status"] = "failed"
            self.receipt["error"] = repr(error)
            import traceback
            self.receipt["traceback"] = traceback.format_exc()
        finally:
            self.write()

    def write(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.receipt, indent=2, default=str), encoding="utf-8")
        unreal.log("MIKDASH_PERF_OPTIMIZE " + json.dumps({
            "mode": MODE,
            "status": self.receipt["status"],
            "receipt": str(self.path),
            "eligible": self.receipt.get("eligibleTotal"),
            "applied": self.receipt.get("naniteApplied"),
        }))


Run().go()
