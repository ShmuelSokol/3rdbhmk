"""Offline planner and texture bakery for the Mikdash surface-wear decal set.

No Unreal, no network, no third-party modules. Standard library only, so it runs
identically under the system Python and under
"C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe".

    python Scripts/create_decals.py --export
        Bake the ten wear textures into SourceAssets/surface-review/textures/ and write
        SourceAssets/surface-review/surface-detail.json -- the decal table, the material
        plan, the meleke variant palette and the budget, all of which
        Scripts/release_surface_detail.py consumes.

    python Scripts/create_decals.py --verify
        Re-read the frozen PNGs, re-check every SHA-256 against the manifest, re-derive
        the whole table from the manifests on disk and confirm it is byte-for-byte the
        table that was written. Exits non-zero on any mismatch. This is what proves the
        manifest and the bytes agree.

    python Scripts/create_decals.py
        Print the summary table to stdout and change nothing.

WHAT THIS IS
    A placement planner. Every decal position below is DERIVED, at run time, from
    measured geometry already on disk:

      SourceAssets/architecture-manifest.json   2633 meshes with expectedBoundsUnrealCm.
                                                Gate thresholds, individual stair steps,
                                                string courses, cornices, window sills,
                                                the laver basin and the altar tiers all
                                                come from here by name and bounds.
      SourceAssets/fx-review/fx-materials.json  anchors: outer altar centre and fire top,
                                                golden altar, menorah origin and lamp
                                                offsets -- already reconciled against the
                                                vessel import receipts by the FX pass.

    Nothing is hand-typed except the walked routes, and --verify checks every route
    vertex against a real feature in the manifest.

    The arithmetic is a line-for-line mirror of
    Plugins/MikdashRuntime/Source/MikdashRuntime/Public/SurfaceWearMath.h. --verify
    cross-checks the mirror against the numbers the standalone C++ test prints into
    SourceAssets/surface-review/tests.json, so the planner and the runtime cannot drift.

WHAT IT IS NOT
    Not a weathering simulation and not a claim about the historical Mikdash. Rainfall,
    ages, lichen ceilings and polish half-lives are an artistic model for Jerusalem
    meleke on a building that is MAINTAINED DAILY. What is being added is the wear of
    heavy use and weather -- polish, soot, dust, rain-washed stone -- never decay: no
    cracks, no spalling, no missing stones, no ruin.

    This file never touches a .umap and never imports unreal. Everything that mutates
    the map lives in Scripts/release_surface_detail.py.

COORDINATES
    Unreal centimetres, +X east, +Y south, +Z up (architecture-manifest.json
    coordinateConvention: expectedSourceToUnrealCm = [x*50, z*50, y*50]).

DECAL CONVENTION
    A UE deferred decal projects along its local +X. Every entry therefore carries an
    explicit rotator:
        floor decal   pitch -90, yaw = heading         local X points down
        wall decal    yaw = outward normal + 180       local X points into the wall
    and sizeCm = [projection depth, half width, half height] in that local frame.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / "SourceAssets" / "surface-review"
TEXTURES = REVIEW / "textures"
MANIFEST_PATH = REVIEW / "surface-detail.json"
ARCHITECTURE = ROOT / "SourceAssets" / "architecture-manifest.json"
FX_MANIFEST = ROOT / "SourceAssets" / "fx-review" / "fx-materials.json"
TESTS_JSON = REVIEW / "tests.json"

NAMESPACE = "/Game/MikdashV3/SurfaceDetailV1"
SEED = 20260908                       # the same seed the C++ test names as routeSeed

SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Mirror of SurfaceWearMath.h.
#
# Kept deliberately literal -- same names, same guard order, same constants -- so a
# reviewer can diff the two side by side. --verify checks the outputs against the
# C++ test's own printed numbers.
# ---------------------------------------------------------------------------

JERUSALEM_RAINFALL_MM = 550.0


def hash32(value: int) -> int:
    value &= 0xFFFFFFFF
    value ^= value >> 16
    value = (value * 0x85EBCA6B) & 0xFFFFFFFF
    value ^= value >> 13
    value = (value * 0xC2B2AE35) & 0xFFFFFFFF
    value ^= value >> 16
    return value


def hash01(seed: int, index: int) -> float:
    mixed = hash32(((seed * 0x9E3779B9) & 0xFFFFFFFF) + hash32(index + 0x7F4A7C15))
    return mixed / 4294967296.0


def hash_signed(seed: int, index: int) -> float:
    return hash01(seed, index) * 2.0 - 1.0


def clamp01(value: float) -> float:
    if not value > 0.0:
        return 0.0
    return value if value < 1.0 else 1.0


def clamp_range(value: float, low: float, high: float) -> float:
    if not value > low:
        return low
    return value if value < high else high


def smooth_falloff(value: float, edge0: float, edge1: float) -> float:
    if not edge1 > edge0:
        return 1.0 if value <= edge0 else 0.0
    t = clamp01((value - edge0) / (edge1 - edge0))
    return 1.0 - t * t * (3.0 - 2.0 * t)


def segment_distance(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    t = clamp01(((px - ax) * dx + (py - ay) * dy) / length_sq) if length_sq > 0.0 else 0.0
    cx = ax + dx * t - px
    cy = ay + dy * t - py
    return math.sqrt(cx * cx + cy * cy)


def distance_to_route(px: float, py: float, route: dict) -> float:
    points = route["points"]
    if not points:
        return math.inf
    if len(points) == 1:
        return math.hypot(points[0][0] - px, points[0][1] - py)
    return min(segment_distance(px, py, points[i][0], points[i][1],
                                points[i + 1][0], points[i + 1][1])
               for i in range(len(points) - 1))


def wear_falloff(distance_cm: float, half_width_cm: float, feather_cm: float) -> float:
    if distance_cm != distance_cm:
        return 0.0
    if distance_cm <= half_width_cm:
        return 1.0
    return smooth_falloff(distance_cm, half_width_cm,
                          half_width_cm + (feather_cm if feather_cm > 0.0 else 0.0))


def traffic_density(px: float, py: float, routes: list) -> float:
    total = 0.0
    for route in routes:
        if not route["tripsPerDay"] > 0.0:
            continue
        total += route["tripsPerDay"] * wear_falloff(
            distance_to_route(px, py, route), route["halfWidthCm"], route["featherCm"])
    return total


def foot_polish(trips_per_day: float, years: float, half_trip_days: float = 4.0e6) -> float:
    if not trips_per_day > 0.0 or not years > 0.0 or not half_trip_days > 0.0:
        return 0.0
    exposure = trips_per_day * years * 365.25
    return clamp01(exposure / (exposure + half_trip_days))


def streak_length_cm(drop_height_cm: float, projection_cm: float,
                     annual_rainfall_mm: float, exposure_fraction: float) -> float:
    if not drop_height_cm > 0.0 or not annual_rainfall_mm > 0.0:
        return 0.0
    exposure = clamp01(exposure_fraction)
    if not exposure > 0.0:
        return 0.0
    rain_factor = math.sqrt(annual_rainfall_mm / JERUSALEM_RAINFALL_MM)
    throw_off = math.exp(-clamp_range(projection_cm, 0.0, 1.0e6) / 25.0)
    return clamp_range(260.0 * exposure * rain_factor * throw_off, 0.0, drop_height_cm)


def weathering(exposure_fraction: float, age_years: float,
               annual_rainfall_mm: float = JERUSALEM_RAINFALL_MM) -> float:
    exposure = clamp01(exposure_fraction)
    if not exposure > 0.0 or not age_years > 0.0 or not annual_rainfall_mm > 0.0:
        return 0.0
    rain_factor = math.sqrt(annual_rainfall_mm / JERUSALEM_RAINFALL_MM)
    time_constant_years = 120.0 / (exposure * rain_factor)
    return clamp01(1.0 - math.exp(-age_years / time_constant_years))


def lichen_coverage(exposure_fraction: float, shade_fraction: float, age_years: float,
                    annual_rainfall_mm: float = JERUSALEM_RAINFALL_MM,
                    settle_years: float = 5.0) -> float:
    exposure = clamp01(exposure_fraction)
    shade = clamp01(shade_fraction)
    if not age_years > settle_years or not exposure > 0.0 or not shade > 0.0:
        return 0.0
    if not annual_rainfall_mm > 0.0:
        return 0.0
    moisture = clamp01(annual_rainfall_mm / (JERUSALEM_RAINFALL_MM * 1.6))
    settled = weathering(exposure, age_years - settle_years, annual_rainfall_mm)
    return clamp01(0.45 * settled * shade * moisture)


def stone_variation(seed: int, index: int, weathering_fraction: float) -> dict:
    age = clamp01(weathering_fraction)
    value = hash_signed(seed, index * 3 + 0)
    warm = hash_signed(seed, index * 3 + 1)
    rough = hash_signed(seed, index * 3 + 2)
    lightness = 1.0 + value * 0.055 - age * 0.030
    return {
        "tintR": clamp_range(lightness * (1.0 + warm * 0.020 + age * 0.055), 0.88, 1.14),
        "tintG": clamp_range(lightness * (1.0 + warm * 0.008 + age * 0.022), 0.88, 1.14),
        "tintB": clamp_range(lightness * (1.0 - warm * 0.024 - age * 0.060), 0.88, 1.14),
        "roughnessScale": clamp_range(1.0 + rough * 0.090 + age * 0.080, 0.82, 1.20),
    }


def polish_roughness_scale(polish_fraction: float) -> float:
    return clamp_range(1.0 - 0.42 * clamp01(polish_fraction), 0.58, 1.0)


def distance_fade(distance_cm: float, fade_start_cm: float, fade_end_cm: float) -> float:
    if distance_cm != distance_cm:
        return 0.0
    if distance_cm <= fade_start_cm:
        return 1.0
    return smooth_falloff(distance_cm, fade_start_cm, fade_end_cm)


def allocate_budget(items: list, cap: int) -> list:
    """Mirror of MikdashWear::AllocateBudget, including the negative-request rule.

    A negative `requested` is a malformed row and allocates nothing. In the C++ the
    ordering bug that clipped a zero minimum UP to a negative request also handed
    budget back to the remainder, which silently raised the cap for every later
    category; SurfaceWearMathTest.cpp pins both halves of that.
    """
    count = len(items)
    out = [0] * count
    if count <= 0 or cap <= 0:
        return out
    remaining = cap

    def request_of(item):
        return item["requested"] if item["requested"] > 0 else 0

    for index in range(count):
        if remaining <= 0:
            break
        want = max(0, items[index]["minimum"])
        want = min(want, request_of(items[index]), remaining)
        out[index] = want
        remaining -= want

    total_weight = 0.0
    for index in range(count):
        if request_of(items[index]) - out[index] > 0 and items[index]["weight"] > 0.0:
            total_weight += items[index]["weight"]
    if total_weight > 0.0 and remaining > 0:
        share = remaining
        for index in range(count):
            unmet = request_of(items[index]) - out[index]
            if unmet <= 0 or not items[index]["weight"] > 0.0:
                continue
            ideal = share * items[index]["weight"] / total_weight
            give = max(0, min(int(math.floor(ideal)), unmet, remaining))
            out[index] += give
            remaining -= give
        while remaining > 0:
            best, best_value = -1, -1.0
            for index in range(count):
                unmet = request_of(items[index]) - out[index]
                if unmet <= 0 or not items[index]["weight"] > 0.0:
                    continue
                ideal = share * items[index]["weight"] / total_weight
                remainder = ideal - math.floor(ideal)
                if remainder > best_value + 1e-12:
                    best_value, best = remainder, index
            if best < 0:
                break
            out[best] += 1
            remaining -= 1
    return out


# ---------------------------------------------------------------------------
# Measured geometry
# ---------------------------------------------------------------------------

def load_architecture() -> list:
    data = json.loads(ARCHITECTURE.read_text(encoding="utf-8-sig"))
    rows = []
    for mesh in data["meshes"]:
        bounds = mesh["expectedBoundsUnrealCm"]
        rows.append({
            "name": mesh["sourceName"],
            "sourceName": mesh["sourceName"],
            "asset": mesh["assetName"],
            "part": mesh.get("sourcePart"),
            "min": [float(v) for v in bounds["min"]],
            "max": [float(v) for v in bounds["max"]],
            # Kept verbatim for the Boolean-union decomposition; see _outer_wall_faces.
            "sourceProperties": mesh.get("sourceProperties"),
            "expectedBoundsUnrealCm": bounds,
        })
    return rows


def centre(row: dict) -> list:
    return [(row["min"][i] + row["max"][i]) * 0.5 for i in range(3)]


def named(rows: list, prefix: str) -> list:
    return [r for r in rows if r["name"] == prefix or r["name"].startswith(prefix + " ")]


# Names whose top face is something a foot can stand on. A floor decal must sit on the
# real walkable Z, not on a guessed one: the court is terraced (outer court 300, inner
# court 500, priests' court 625, Ulam and Heichal 925), so a decal placed at a hand-typed
# Z would project into thin air on most of the route.
WALKABLE_NAME_PATTERN = ("floor", "terrace", "threshold", "paving", "transition",
                         "stair", "rise", "platform", "foundation", "vestibule")

# Names that match a walkable token but are NOT a walkable top face. 'Altar foundation
# core' is the one that actually bites: it contains 'foundation', it spans the altar's
# footprint, and its top is at Z 716.7 inside the altar mass, so without this exclusion a
# floor decal beside the altar would be placed 90 cm up inside solid stone.
WALKABLE_NAME_EXCLUSIONS = ("altar", "core", "ramp")

# Upper-storey cell floors sit at 1225 and 1525 and the outer chambers at 2925. Nothing
# this pass places is above the Ulam and Heichal floor at 925, so anything higher is a
# different storey and must not win the lookup.
WALKABLE_CEILING_CM = 1000.0


def build_walkable_index(rows: list) -> list:
    index = []
    for row in rows:
        lowered = row["name"].lower()
        if not any(token in lowered for token in WALKABLE_NAME_PATTERN):
            continue
        if any(token in lowered for token in WALKABLE_NAME_EXCLUSIONS):
            continue
        if row["max"][2] > WALKABLE_CEILING_CM:
            continue
        index.append(row)
    return index


def floor_z_at(index: list, x: float, y: float, fallback: float = 0.0) -> float:
    """Highest walkable top face whose XY footprint contains the point.

    Falls back to `fallback` (ground level, 0) where nothing covers the point, which is
    correct for the approaches outside the enclosure.
    """
    best = None
    for row in index:
        if not (row["min"][0] - 1.0 <= x <= row["max"][0] + 1.0):
            continue
        if not (row["min"][1] - 1.0 <= y <= row["max"][1] + 1.0):
            continue
        top = row["max"][2]
        if best is None or top > best:
            best = top
    return fallback if best is None else best


def load_anchors() -> dict:
    data = json.loads(FX_MANIFEST.read_text(encoding="utf-8"))
    return {key: value["value"] for key, value in data["anchors"].items()}


# ---------------------------------------------------------------------------
# The walked routes
#
# Each vertex is a measured feature. --verify re-derives every one of them from the
# manifest and refuses a vertex that does not sit on a real threshold, stair end,
# terrace or court centre line. Trips per day are an artistic traffic model: the east
# axis is the pilgrim axis and carries the most, the priests' service loop the least.
# ---------------------------------------------------------------------------

def build_routes(rows: list) -> list:
    def threshold_xy(name):
        row = named(rows, name)[0]
        c = centre(row)
        return [round(c[0], 1), round(c[1], 1)]

    def stair_span(prefix, axis):
        steps = named(rows, prefix)
        lo = min(s["min"][axis] for s in steps)
        hi = max(s["max"][axis] for s in steps)
        return lo, hi

    outer_e = threshold_xy("Outer E threshold")
    outer_n = threshold_xy("Outer N threshold")
    outer_s = threshold_xy("Outer S threshold")
    inner_e = threshold_xy("Inner E threshold")
    inner_n = threshold_xy("Inner N threshold")
    inner_s = threshold_xy("Inner S threshold")

    oe_lo, oe_hi = stair_span("Outer E stair", 0)          # 8600 .. 9200
    ie_lo, ie_hi = stair_span("Inner E stair", 0)          # 3300 .. 3700
    on_lo, on_hi = stair_span("Outer N stair", 1)          # -8950 .. -8600
    in_lo, in_hi = stair_span("Inner N stair", 1)          # -3700 .. -3300
    os_lo, os_hi = stair_span("Outer S stair", 1)          # 8600 .. 8950
    is_lo, is_hi = stair_span("Inner S stair", 1)          # 3300 .. 3700
    ul_lo, ul_hi = stair_span("Ulam stair", 0)             # -2500 .. -1400

    terrace_n = named(rows, "Outer N mount approach terrace")
    terrace_s = named(rows, "Outer S mount approach terrace")
    approach_n = min(t["min"][1] for t in terrace_n) + 250.0        # mid-terrace
    approach_s = max(t["max"][1] for t in terrace_s) - 250.0

    duchan = named(rows, "Duchan rise")
    duchan_x = min(d["min"][0] for d in duchan)                     # 1575, its west face

    basin = named(rows, "Hollow basin with inner wall")[0]
    laver = centre(basin)

    return [
        {
            "id": "eastPilgrimAxis",
            # oe_hi is the stair FOOT (east, ground level); oe_lo its HEAD at court
            # level. The route walks foot to head, so the head vertex is oe_lo.
            "points": [[oe_hi + 200.0, 0.0], [oe_lo, 0.0], outer_e,
                       [ie_hi, 0.0], inner_e, [duchan_x + 525.0, 0.0]],
            "halfWidthCm": 220.0, "featherCm": 320.0, "tripsPerDay": 9000.0,
            "rationale": "The pilgrim axis. Every visitor who enters from the east crosses "
                         "the outer stair, the outer threshold, the inner stair and the inner "
                         "threshold in that order, so all four wear together and the "
                         "thresholds wear hardest.",
        },
        {
            "id": "northGateRoute",
            "points": [[0.0, approach_n], [0.0, on_hi], outer_n,
                       [0.0, in_lo], inner_n, [0.0, -2100.0]],
            "halfWidthCm": 190.0, "featherCm": 300.0, "tripsPerDay": 3400.0,
            "rationale": "Secondary arrival from the north terrace; narrower band than the "
                         "east axis because the mouth is the same width but the flow is thinner.",
        },
        {
            "id": "southGateRoute",
            "points": [[0.0, approach_s], [0.0, os_lo], outer_s,
                       [0.0, is_hi], inner_s, [0.0, 2100.0]],
            "halfWidthCm": 190.0, "featherCm": 300.0, "tripsPerDay": 3400.0,
            "rationale": "Mirror of the north route; kept symmetric because the terraces are.",
        },
        {
            "id": "laverToRamp",
            "points": [[ul_hi - 900.0, 0.0], [round(laver[0], 1), round(laver[1], 1)],
                       [-900.0, 2100.0], [0.0, 2300.0], [0.0, 710.0]],
            "halfWidthCm": 110.0, "featherCm": 160.0, "tripsPerDay": 1400.0,
            "rationale": "The priests' service loop: down from the Ulam, to the laver to wash, "
                         "then round to the foot of the altar ramp on the south. Few feet, but "
                         "the same few feet every single day, and wet ones leaving the laver.",
        },
        {
            "id": "ulamStair",
            "points": [[ul_hi + 200.0, 0.0], [ul_hi - 25.0, 0.0],
                       [ul_lo + 125.0, 0.0], [ul_lo + 50.0, 0.0]],
            "halfWidthCm": 95.0, "featherCm": 140.0, "tripsPerDay": 600.0,
            "rationale": "The twelve Ulam steps. The lowest traffic of any route and the "
                         "highest concentration: everyone who uses it uses the same twelve treads.",
        },
        {
            "id": "outerCourtRing",
            "points": [[7000.0, -7000.0], [7000.0, 7000.0], [-7000.0, 7000.0],
                       [-7000.0, -7000.0], [7000.0, -7000.0]],
            "halfWidthCm": 260.0, "featherCm": 420.0, "tripsPerDay": 2200.0,
            "rationale": "People who have come in do not stand still: they walk the court "
                         "inside the wall. A broad, diffuse band -- this is drift, not a path.",
        },
    ]


# The vertices the routes are allowed to use, and the feature each one must land on.
ROUTE_VERTEX_TOLERANCE_CM = 260.0

# The identical table as it stands in Plugins/MikdashRuntime/Tests/SurfaceWearMathTest.cpp.
# The test's own header says the routes there are "kept in step with the table in
# Scripts/create_decals.py"; this is what actually enforces that, rather than leaving it
# as a comment two files apart. If the manifest moves, both sides must be updated and
# --verify fails until they are.
CPP_TEST_ROUTES = {
    "eastPilgrimAxis": [[9400.0, 0.0], [8600.0, 0.0], [7950.0, 0.0],
                        [3700.0, 0.0], [2650.0, 0.0], [2100.0, 0.0]],
    "northGateRoute": [[0.0, -9200.0], [0.0, -8600.0], [0.0, -7950.0],
                       [0.0, -3700.0], [0.0, -2650.0], [0.0, -2100.0]],
    "southGateRoute": [[0.0, 9200.0], [0.0, 8600.0], [0.0, 7950.0],
                       [0.0, 3700.0], [0.0, 2650.0], [0.0, 2100.0]],
    "laverToRamp": [[-2300.0, 0.0], [-1950.0, 1500.0], [-900.0, 2100.0],
                    [0.0, 2300.0], [0.0, 710.0]],
    "ulamStair": [[-1200.0, 0.0], [-1425.0, 0.0], [-2375.0, 0.0], [-2450.0, 0.0]],
    "outerCourtRing": [[7000.0, -7000.0], [7000.0, 7000.0], [-7000.0, 7000.0],
                       [-7000.0, -7000.0], [7000.0, -7000.0]],
}
CPP_TEST_ROUTE_PARAMETERS = {
    "eastPilgrimAxis": (220.0, 320.0, 9000.0),
    "northGateRoute": (190.0, 300.0, 3400.0),
    "southGateRoute": (190.0, 300.0, 3400.0),
    "laverToRamp": (110.0, 160.0, 1400.0),
    "ulamStair": (95.0, 140.0, 600.0),
    "outerCourtRing": (260.0, 420.0, 2200.0),
}


# ---------------------------------------------------------------------------
# Age tiers.
#
# The premise is a building maintained daily, not a ruin. What differs across it is
# how long each face has stood since it was last dressed:
#   outer enclosure  the oldest fabric, weathered and, on shaded faces, lichened
#   outer court      middle
#   inner court and sanctuary  recently dressed; no lichen at all
# The tier is read from the Chebyshev radius of the feature in XY, which is exactly
# how the court rings are laid out in the manifest.
# ---------------------------------------------------------------------------

AGE_TIERS = [
    {"id": "outerEnclosure", "minRadiusCm": 7600.0, "ageYears": 140.0, "exposure": 0.95},
    {"id": "outerCourt", "minRadiusCm": 3800.0, "ageYears": 60.0, "exposure": 0.80},
    {"id": "innerCourt", "minRadiusCm": 0.0, "ageYears": 8.0, "exposure": 0.55},
]


def age_tier(x: float, y: float) -> dict:
    radius = max(abs(x), abs(y))
    for tier in AGE_TIERS:
        if radius >= tier["minRadiusCm"]:
            return tier
    return AGE_TIERS[-1]


# ---------------------------------------------------------------------------
# Categories. Order, weights, requests and minimums are the plan the C++ allocator
# is tested against (SurfaceWearMathTest.cpp BudgetChecks); --verify asserts the
# generated table matches `requested` exactly, category by category.
# ---------------------------------------------------------------------------

CATEGORIES = [
    {"id": "footPolish", "weight": 5.0, "requested": 96, "minimum": 24,
     "material": "MI_Wear_FootPolish", "texture": "T_Wear_FootPolish_512",
     "sortOrder": 10, "fadeStartCm": 3000.0, "fadeEndCm": 9000.0},
    {"id": "stepNosing", "weight": 4.0, "requested": 72, "minimum": 18,
     "material": "MI_Wear_StepNosing", "texture": "T_Wear_StepNosing_256",
     "sortOrder": 12, "fadeStartCm": 2000.0, "fadeEndCm": 6000.0},
    {"id": "rainStreak", "weight": 3.0, "requested": 64, "minimum": 12,
     "material": "MI_Wear_RainStreak", "texture": "T_Wear_RainStreak_512",
     "sortOrder": 8, "fadeStartCm": 4000.0, "fadeEndCm": 12000.0},
    {"id": "dustRunoff", "weight": 2.5, "requested": 48, "minimum": 8,
     "material": "MI_Wear_DustRunoff", "texture": "T_Wear_DustRunoff_512",
     "sortOrder": 7, "fadeStartCm": 4000.0, "fadeEndCm": 12000.0},
    {"id": "waterStain", "weight": 2.0, "requested": 24, "minimum": 6,
     "material": "MI_Wear_WaterStain", "texture": "T_Wear_WaterStain_512",
     "sortOrder": 9, "fadeStartCm": 2500.0, "fadeEndCm": 7000.0},
    {"id": "soot", "weight": 3.5, "requested": 20, "minimum": 8,
     "material": "MI_Wear_Soot", "texture": "T_Wear_Soot_512",
     "sortOrder": 11, "fadeStartCm": 3000.0, "fadeEndCm": 9000.0},
    {"id": "lichen", "weight": 1.5, "requested": 60, "minimum": 0,
     "material": "MI_Wear_Lichen", "texture": "T_Wear_Lichen_512",
     "sortOrder": 6, "fadeStartCm": 2500.0, "fadeEndCm": 7500.0},
    {"id": "windDust", "weight": 1.5, "requested": 44, "minimum": 0,
     "material": "MI_Wear_WindDust", "texture": "T_Wear_WindDust_512",
     "sortOrder": 5, "fadeStartCm": 2500.0, "fadeEndCm": 7500.0},
    {"id": "weathering", "weight": 1.0, "requested": 32, "minimum": 0,
     "material": "MI_Wear_Weathering", "texture": "T_Wear_Weathering_512",
     "sortOrder": 4, "fadeStartCm": 3000.0, "fadeEndCm": 9000.0},
]

BUDGET_CAP = 220


NOSING_MAX_HALF_WIDTH_CM = 400.0


def dominant_band_half_width(px: float, py: float, routes: list, fallback: float) -> float:
    """Half width of the walked band of whichever route contributes most traffic here.

    A tread is not worn across its whole width. The Duchan rises are 50 m long and the
    Ulam treads nearly 20 m wide, but the feet that cross them are inside a band a couple
    of metres across, and a nosing decal drawn edge to edge would say the opposite: that
    every part of the step is used equally. That is the sort of uniformity that makes a
    render read as manufactured, which is the whole thing this pass exists to undo.
    """
    best, best_share = fallback, 0.0
    for route in routes:
        if not route["tripsPerDay"] > 0.0:
            continue
        share = route["tripsPerDay"] * wear_falloff(
            distance_to_route(px, py, route), route["halfWidthCm"], route["featherCm"])
        if share > best_share:
            best_share, best = share, route["halfWidthCm"] + route["featherCm"] * 0.5
    return best


def label_key(label: str) -> int:
    """Stable 32-bit key for a decal label. Deliberately not Python's hash(), which is
    salted per process and would reorder the whole table on every run."""
    return int.from_bytes(hashlib.sha256(label.encode("utf-8")).digest()[:4], "big")


def _yaw(degrees: float) -> float:
    """Yaw into [0,360). A rotator of 450 degrees is legal but reads as a mistake in a
    receipt, and it makes two identical decals look different when they are diffed."""
    return float(degrees) % 360.0


def _round(values, places=2):
    # `+ 0.0` turns -0.0 into 0.0. A receipt full of "-0.0" reads as a bug even when the
    # number is right.
    return [round(float(v), places) + 0.0 for v in values]


def _entry(category, label, location, rotation, size, importance, opacity, rationale,
           extra=None):
    row = {
        "label": label,
        "category": category,
        "locationCm": _round(location),
        "rotation": {"pitch": round(float(rotation[0]), 2),
                     "yaw": _yaw(round(float(rotation[1]), 2)),
                     "roll": round(float(rotation[2]), 2)},
        "sizeCm": _round(size),
        "importance": round(float(importance), 5),
        "opacity": round(float(opacity), 4),
        "rationale": rationale,
    }
    if extra:
        row.update(extra)
    return row


# ---------------------------------------------------------------------------
# Candidate generation, one function per category.
# ---------------------------------------------------------------------------

GATE_NAMES = [
    ("Outer E threshold", "OuterEast", 0.0),
    ("Outer N threshold", "OuterNorth", 90.0),
    ("Outer S threshold", "OuterSouth", 90.0),
    ("Inner E threshold", "InnerEast", 0.0),
    ("Inner N threshold", "InnerNorth", 90.0),
    ("Inner S threshold", "InnerSouth", 90.0),
]

STAIR_FLIGHTS = [
    ("Outer E stair", "OuterEast", 0, +1),
    ("Outer N stair", "OuterNorth", 1, -1),
    ("Outer S stair", "OuterSouth", 1, +1),
    ("Inner E stair", "InnerEast", 0, +1),
    ("Inner N stair", "InnerNorth", 1, -1),
    ("Inner S stair", "InnerSouth", 1, +1),
    ("Ulam stair", "Ulam", 0, -1),
    ("Duchan rise", "Duchan", 0, +1),
    ("Outer N mount approach terrace", "NorthTerrace", 1, -1),
    ("Outer S mount approach terrace", "SouthTerrace", 1, +1),
]

SERVICE_YEARS = 40.0     # how long this fabric has been in daily service


def candidates_foot_polish(rows, routes, anchors):
    out = []
    walkable = build_walkable_index(rows)

    # 1. The gate mouths. Every trip through a gate is funnelled into the same
    #    500 cm opening, so this is where the routes' traffic actually sums.
    for name, tag, yaw in GATE_NAMES:
        row = named(rows, name)[0]
        c = centre(row)
        trips = traffic_density(c[0], c[1], routes)
        polish = foot_polish(trips, SERVICE_YEARS)
        span_y = row["max"][1] - row["min"][1]
        span_x = row["max"][0] - row["min"][0]
        out.append(_entry(
            "footPolish", "Wear_FootPolish_Threshold_" + tag,
            [c[0], c[1], row["max"][2]], (-90.0, yaw, 0.0),
            [60.0, max(span_x, span_y) * 0.5 + 30.0, min(span_x, span_y) * 0.5 + 30.0],
            1.0, clamp_range(polish * 1.15, 0.15, 0.95),
            "Gate mouth: %s. %.0f trips/day converge here (all routes summed) and %.0f "
            "years of them; the threshold is the single most polished stone on the route."
            % (name, trips, SERVICE_YEARS),
            {"trafficTripsPerDay": round(trips, 1),
             "polishFraction": round(polish, 4),
             "roughnessScale": round(polish_roughness_scale(polish), 4)}))

    # 2. The head and foot of every flight: people slow, turn and shuffle at both ends,
    #    so a landing polishes faster than the open floor beyond it.
    for prefix, tag, axis, direction in STAIR_FLIGHTS[:7]:
        steps = named(rows, prefix)
        if not steps:
            continue
        lo = min(s["min"][axis] for s in steps)
        hi = max(s["max"][axis] for s in steps)
        top_z = max(s["max"][2] for s in steps)
        base_z = min(s["max"][2] for s in steps)
        for end, value, z in (("Foot", lo if direction > 0 else hi, base_z),
                              ("Head", hi if direction > 0 else lo, top_z)):
            point = [value, 0.0] if axis == 0 else [0.0, value]
            trips = traffic_density(point[0], point[1], routes)
            if trips <= 0.0:
                continue
            polish = foot_polish(trips, SERVICE_YEARS)
            out.append(_entry(
                "footPolish", "Wear_FootPolish_Landing_%s_%s" % (tag, end),
                [point[0], point[1], z], (-90.0, 0.0 if axis == 0 else 90.0, 0.0),
                [50.0, 300.0, 200.0], 0.85, clamp_range(polish, 0.10, 0.85),
                "%s of the %s: a landing where the gait breaks. %.0f trips/day."
                % (end.lower(), prefix, trips),
                {"trafficTripsPerDay": round(trips, 1),
                 "polishFraction": round(polish, 4),
                 "roughnessScale": round(polish_roughness_scale(polish), 4)}))

    # 3. The open runs between them, sampled along each route and scored purely by the
    #    traffic that reaches the sample. This is what puts polish on the ROUTE and
    #    leaves the court floor either side of it alone.
    for route in routes:
        points = route["points"]
        total = 0.0
        for i in range(len(points) - 1):
            total += math.hypot(points[i + 1][0] - points[i][0], points[i + 1][1] - points[i][1])
        step_cm = 700.0
        count = max(1, int(total / step_cm))
        for k in range(count):
            s = (k + 0.5) / count * total
            travelled = 0.0
            for i in range(len(points) - 1):
                seg = math.hypot(points[i + 1][0] - points[i][0], points[i + 1][1] - points[i][1])
                if travelled + seg >= s or i == len(points) - 2:
                    t = (s - travelled) / seg if seg > 0.0 else 0.0
                    t = clamp01(t)
                    px = points[i][0] + (points[i + 1][0] - points[i][0]) * t
                    py = points[i][1] + (points[i + 1][1] - points[i][1]) * t
                    heading = math.degrees(math.atan2(points[i + 1][1] - points[i][1],
                                                      points[i + 1][0] - points[i][0]))
                    break
                travelled += seg
            trips = traffic_density(px, py, routes)
            polish = foot_polish(trips, SERVICE_YEARS)
            if polish < 0.02:
                continue
            jitter = hash_signed(SEED, hash32(k * 131 + len(out)))
            floor_z = floor_z_at(walkable, px, py)
            out.append(_entry(
                "footPolish", "Wear_FootPolish_%s_%02d" % (route["id"], k),
                [px, py, floor_z], (-90.0, heading, 0.0),
                [40.0, route["halfWidthCm"] * 1.05, 260.0 + jitter * 40.0],
                round(0.35 + 0.45 * polish, 5), clamp_range(polish * 0.85, 0.05, 0.7),
                "On %s. %.0f trips/day reach this point; polish %.3f after %.0f years."
                % (route["id"], trips, polish, SERVICE_YEARS),
                {"trafficTripsPerDay": round(trips, 1),
                 "polishFraction": round(polish, 4),
                 "roughnessScale": round(polish_roughness_scale(polish), 4),
                 "floorTopZCm": round(floor_z, 2)}))
    return out


def candidates_step_nosing(rows, routes, anchors):
    """Darkened, rounded nosings on the leading edge of every tread.

    The nosing is where a sole actually lands, so it darkens and rounds long before the
    tread behind it does. The edge is read from each step mesh's own bounds: the leading
    face is the one on the side people climb from.
    """
    out = []
    for prefix, tag, axis, direction in STAIR_FLIGHTS:
        steps = named(rows, prefix)
        for index, step in enumerate(sorted(steps, key=lambda s: s["max"][2])):
            top_z = step["max"][2]
            edge = step["max"][axis] if direction > 0 else step["min"][axis]
            if axis == 0:
                location = [edge - direction * 12.0, centre(step)[1], top_z]
                width = (step["max"][1] - step["min"][1]) * 0.5
                yaw = 0.0
            else:
                location = [centre(step)[0], edge - direction * 12.0, top_z]
                width = (step["max"][0] - step["min"][0]) * 0.5
                yaw = 90.0
            trips = traffic_density(location[0], location[1], routes)
            if trips <= 0.0:
                continue
            # Narrow the nosing to the band that is actually walked. The Duchan rises run
            # the full 50 m width of the priests' court and the Ulam treads are nearly 20 m
            # wide; a decal drawn edge to edge would claim every part of the step is used
            # equally, and would cost a large overdraw footprint saying it.
            width = min(width, NOSING_MAX_HALF_WIDTH_CM,
                        dominant_band_half_width(location[0], location[1], routes, width))
            polish = foot_polish(trips, SERVICE_YEARS)
            out.append(_entry(
                "stepNosing", "Wear_Nosing_%s_%02d" % (tag, index + 1),
                location, (-90.0, yaw, 0.0),
                [30.0, width + 5.0, 22.0],
                round(0.5 + 0.5 * polish, 5), clamp_range(0.25 + 0.55 * polish, 0.2, 0.9),
                "Nosing of tread %d of the %s at Z %.0f. %.0f trips/day land on this "
                "edge; the arris darkens and rounds long before the tread behind it does. "
                "Worn across %.0f cm, the walked band, not the whole %.0f cm tread."
                % (index + 1, prefix, top_z, trips, width * 2.0,
                   (step["max"][1] - step["min"][1]) if axis == 0
                   else (step["max"][0] - step["min"][0])),
                {"trafficTripsPerDay": round(trips, 1),
                 "polishFraction": round(polish, 4),
                 "treadTopZCm": round(top_z, 2),
                 "wornBandWidthCm": round(width * 2.0, 1)}))
    return out


def _ledges(rows):
    """Every horizontal band that can throw water: string courses, cornices, sills.

    A ledge is characterised by the face it stands on (its outward normal), how far it
    projects from that face, and how much bare wall there is below it.
    """
    found = []
    for row in rows:
        name = row["name"]
        if not (name.startswith("Court string course and cornice")
                or name.startswith("Layered Ulam roof cornice")
                or name.startswith("Sanctuary roof stone moulding")
                or name.startswith("High window sill and lintel")
                or name.startswith("Facade gold dentil")):
            continue
        span_x = row["max"][0] - row["min"][0]
        span_y = row["max"][1] - row["min"][1]
        # The short horizontal axis is the projection; the long one runs along the wall.
        if span_x <= span_y:
            axis, projection, run = 0, span_x, span_y
            normal_yaw = 0.0 if centre(row)[0] > 0 else 180.0
            face = row["max"][0] if centre(row)[0] > 0 else row["min"][0]
            location_fixed = face
        else:
            axis, projection, run = 1, span_y, span_x
            normal_yaw = 90.0 if centre(row)[1] > 0 else 270.0
            face = row["max"][1] if centre(row)[1] > 0 else row["min"][1]
            location_fixed = face
        found.append({
            "row": row, "axis": axis, "projectionCm": projection, "runCm": run,
            "normalYaw": normal_yaw, "faceCoord": location_fixed,
            "underside": row["min"][2],
        })
    return found


def _drop_below(ledge, rows):
    """Free wall height under a ledge: down to the next thing that sticks out under it."""
    row = ledge["row"]
    best = 0.0
    for other in rows:
        if other is row:
            continue
        if other["max"][2] > ledge["underside"] - 1.0:
            continue
        overlap = True
        for i in range(2):
            if min(row["max"][i], other["max"][i]) - max(row["min"][i], other["min"][i]) <= 1.0:
                overlap = False
                break
        if overlap:
            best = max(best, other["max"][2])
    return max(0.0, ledge["underside"] - best)


def candidates_rain_streak(rows, routes, anchors):
    """Dirty runoff below a ledge, on faces open to the weather.

    Exposure is 1 on the outward face of the outer enclosure, lower inside the court
    where the opposite wall shelters it. A DEEP cornice throws water clear of the face
    and protects it, which is why StreakLengthCm falls off with projection.
    """
    out = []
    for index, ledge in enumerate(_ledges(rows)):
        row = ledge["row"]
        c = centre(row)
        tier = age_tier(c[0], c[1])
        drop = _drop_below(ledge, rows)
        if drop < 120.0:
            continue
        if ledge["runCm"] < 200.0:
            continue
        outward = abs(ledge["faceCoord"]) >= 7600.0
        exposure = 0.95 if outward else 0.45
        length = streak_length_cm(drop, ledge["projectionCm"], JERUSALEM_RAINFALL_MM, exposure)
        if length < 60.0:
            continue
        weather = weathering(exposure, tier["ageYears"])
        # Slice a long run into panels so one decal never spans the whole court wall.
        # About 8 m per panel. A single decal spanning the whole court wall would be
        # both a huge overdraw footprint and a visibly stretched texture.
        panels = max(1, min(12, int(round(ledge["runCm"] / 800.0))))
        for panel in range(panels):
            t = (panel + 0.5) / panels
            if ledge["axis"] == 0:
                px = ledge["faceCoord"]
                py = row["min"][1] + (row["max"][1] - row["min"][1]) * t
                half = (row["max"][1] - row["min"][1]) / (2.0 * panels)
            else:
                py = ledge["faceCoord"]
                px = row["min"][0] + (row["max"][0] - row["min"][0]) * t
                half = (row["max"][0] - row["min"][0]) / (2.0 * panels)
            out.append(_entry(
                "rainStreak", "Wear_RainStreak_%03d_%d" % (index, panel),
                [px, py, ledge["underside"] - length * 0.5],
                (0.0, ledge["normalYaw"] + 180.0, 0.0),
                [45.0, half * 0.96, length * 0.5],
                round(0.35 + 0.5 * weather * exposure, 5),
                clamp_range(0.20 + 0.55 * weather * exposure, 0.08, 0.8),
                "Runoff below '%s' (%s tier, %.0f y). Ledge projects %.0f cm and there "
                "are %.0f cm of free wall under it, so rain washes %.0f cm down the face "
                "at exposure %.2f. A deeper cornice would throw the water clear and streak less."
                % (row["name"], tier["id"], tier["ageYears"], ledge["projectionCm"],
                   drop, length, exposure),
                {"streakLengthCm": round(length, 1),
                 "ledgeProjectionCm": round(ledge["projectionCm"], 1),
                 "dropHeightCm": round(drop, 1),
                 "exposureFraction": exposure,
                 "weatheringFraction": round(weather, 4),
                 "ageTier": tier["id"]}))
    return out


def candidates_dust_runoff(rows, routes, anchors):
    """The dry half of the same story: dust that settles on a ledge and washes off it.

    Wider, softer and much shorter than a rain streak, and it is strongest on the
    SHELTERED faces, where rain never gets round to washing the wall clean.
    """
    out = []
    for index, ledge in enumerate(_ledges(rows)):
        row = ledge["row"]
        c = centre(row)
        tier = age_tier(c[0], c[1])
        drop = _drop_below(ledge, rows)
        if drop < 60.0:
            continue
        outward = abs(ledge["faceCoord"]) >= 7600.0
        exposure = 0.30 if outward else 0.85          # sheltered faces keep their dust
        length = clamp_range(0.55 * streak_length_cm(drop, ledge["projectionCm"],
                                                     JERUSALEM_RAINFALL_MM, 1.0),
                             0.0, min(drop, 220.0))
        if length < 40.0:
            continue
        # A 20 cm wide decal on a 30 cm ledge return costs a draw and reads as nothing.
        if ledge["runCm"] < 200.0:
            continue
        panels = max(1, min(8, int(round(ledge["runCm"] / 1100.0))))
        for panel in range(panels):
            t = (panel + 0.5) / panels
            if ledge["axis"] == 0:
                px = ledge["faceCoord"]
                py = row["min"][1] + (row["max"][1] - row["min"][1]) * t
                half = (row["max"][1] - row["min"][1]) / (2.0 * panels)
            else:
                py = ledge["faceCoord"]
                px = row["min"][0] + (row["max"][0] - row["min"][0]) * t
                half = (row["max"][0] - row["min"][0]) / (2.0 * panels)
            out.append(_entry(
                "dustRunoff", "Wear_DustRunoff_%03d_%d" % (index, panel),
                [px, py, ledge["underside"] - length * 0.5],
                (0.0, ledge["normalYaw"] + 180.0, 0.0),
                [40.0, half * 0.98, length * 0.5],
                round(0.25 + 0.35 * exposure, 5),
                clamp_range(0.12 + 0.35 * exposure, 0.06, 0.55),
                "Dust runoff below '%s' on %s face (exposure %.2f). Shorter and much "
                "softer than the rain streak on the same ledge: this is settled dust "
                "moved a little way down, not a wash."
                % (row["name"], "a sheltered" if not outward else "an open", exposure),
                {"runoffLengthCm": round(length, 1),
                 "exposureFraction": exposure,
                 "ageTier": tier["id"]}))
    return out


def candidates_water_stain(rows, routes, anchors):
    """Damp, darkened stone where water is actually handled every day.

    Three real sources in the measured geometry: the laver and its twelve spouts, the
    stone slaughter and rinsing tables, and the service passage the washings drain along.
    """
    out = []
    walkable = build_walkable_index(rows)
    basin = named(rows, "Hollow basin with inner wall")
    spouts = named(rows, "Spout")
    if basin and spouts:
        b = basin[0]
        base_z = floor_z_at(walkable, centre(b)[0], centre(b)[1])   # the floor it stands on
        for index, spout in enumerate(sorted(spouts, key=lambda s: s["name"])):
            c = centre(spout)
            direction = math.degrees(math.atan2(c[1] - centre(b)[1], c[0] - centre(b)[0]))
            reach = 95.0
            px = c[0] + math.cos(math.radians(direction)) * reach
            py = c[1] + math.sin(math.radians(direction)) * reach
            out.append(_entry(
                "waterStain", "Wear_WaterStain_LaverSpout_%02d" % (index + 1),
                [px, py, base_z], (-90.0, direction, 0.0),
                [50.0, 110.0, 150.0], 0.9, 0.55,
                "Under laver spout %d (spout mouth Z %.0f). The kohanim wash here every "
                "day of the year; the paving below never fully dries, so it reads darker "
                "and smoother, with a mineral rim where it does."
                % (index + 1, c[2]),
                {"spoutCentreCm": _round(c), "wetRoughnessScale": 0.62}))
    for index, table in enumerate(named(rows, "Stone slaughter table")):
        c = centre(table)
        out.append(_entry(
            "waterStain", "Wear_WaterStain_RinseTable_%02d" % (index + 1),
            [c[0], c[1], floor_z_at(walkable, c[0], c[1])], (-90.0, 0.0, 0.0),
            [50.0, 130.0, 130.0], 0.7, 0.4,
            "Floor beside '%s'. Rinsing water runs off the table onto the paving here "
            "every service." % table["name"],
            {"wetRoughnessScale": 0.7}))
    passage = named(rows, "Five-amah service passage")
    for index, row in enumerate(passage):
        c = centre(row)
        run = row["max"][0] - row["min"][0]
        panels = 3
        for panel in range(panels):
            t = (panel + 0.5) / panels
            px = row["min"][0] + run * t
            out.append(_entry(
                "waterStain", "Wear_WaterStain_Drain_%02d_%d" % (index + 1, panel),
                [px, c[1], row["max"][2]], (-90.0, 0.0, 0.0),
                [45.0, run / (2.0 * panels) * 0.9, (row["max"][1] - row["min"][1]) * 0.5],
                0.6, 0.32,
                "Along the five-amah service passage, the fall the washings drain down. "
                "Damp-darkened stone with a dried mineral edge, never standing water.",
                {"wetRoughnessScale": 0.75}))
    return out


def candidates_soot(rows, routes, anchors):
    """Soot above every open flame that burns daily.

    Positions come from the FX pass's own anchors, which were reconciled against the
    vessel import receipts, so the soot sits above the same flames the smoke does.
    """
    out = []
    altar = anchors["outerAltarCentre"]["value"] if isinstance(anchors["outerAltarCentre"], dict) \
        else anchors["outerAltarCentre"]
    fire_top = anchors["outerAltarFireTopZ"]
    tier_top = anchors["outerAltarTierTopZ"]
    tiers = named(rows, "Altar")
    half = max(max(abs(t["min"][0]), abs(t["max"][0])) for t in tiers) if tiers else 800.0
    for index, yaw in enumerate((0.0, 90.0, 180.0, 270.0)):
        px = altar[0] + math.cos(math.radians(yaw)) * half
        py = altar[1] + math.sin(math.radians(yaw)) * half
        out.append(_entry(
            "soot", "Wear_Soot_AltarFace_%02d" % (index + 1),
            [px, py, tier_top - 130.0], (0.0, yaw + 180.0, 0.0),
            [60.0, half * 0.85, 190.0], 1.0, 0.5,
            "Upper course of the outer altar, %s face. The fire top is Z %.1f and the "
            "tier top Z %.1f; smoke licks the last stone below the fire all day, so this "
            "band darkens while the tiers below it stay clean."
            % (("east", "south", "west", "north")[index], fire_top, tier_top),
            {"sourceKind": "outerAltarFire"}))
    for index, yaw in enumerate((45.0, 135.0, 225.0, 315.0)):
        px = altar[0] + math.cos(math.radians(yaw)) * half * 1.02
        py = altar[1] + math.sin(math.radians(yaw)) * half * 1.02
        out.append(_entry(
            "soot", "Wear_Soot_AltarCorner_%02d" % (index + 1),
            [px, py, tier_top - 90.0], (0.0, yaw + 180.0, 0.0),
            [55.0, 150.0, 150.0], 0.95, 0.55,
            "Corner of the outer altar's upper course. The flame wraps a corner from two "
            "sides at once, so the keren stones darken harder than the flat faces between "
            "them -- the detail that stops the four face bands reading as wallpaper.",
            {"sourceKind": "outerAltarFire"}))
    walkable = build_walkable_index(rows)
    for index, yaw in enumerate((0.0, 180.0)):
        ash_x = altar[0] + math.cos(math.radians(yaw)) * (half + 120.0)
        ash_y = altar[1] + math.sin(math.radians(yaw)) * (half + 120.0)
        out.append(_entry(
            "soot", "Wear_Soot_AltarRamp_%02d" % (index + 1),
            [ash_x, ash_y, floor_z_at(walkable, ash_x, ash_y)],
            (-90.0, yaw, 0.0), [40.0, 260.0, 260.0], 0.6, 0.3,
            "Paving beside the altar where ash is carried past. Fine, flat and grey, "
            "not the greasy black of the fire itself.",
            {"sourceKind": "ashCarry"}))
    golden = anchors["goldenAltarCentre"]
    out.append(_entry(
        "soot", "Wear_Soot_GoldenAltar_Ceiling",
        [golden[0], golden[1], anchors["heikhalCeilingZ"] - 5.0], (90.0, 0.0, 0.0),
        [70.0, 190.0, 190.0], 0.85, 0.28,
        "Heichal ceiling directly over the golden altar (top Z %.1f). Ketores is offered "
        "twice daily; the plume reaches the ceiling and leaves a soft warm-grey bloom."
        % anchors["goldenAltarTopZ"],
        {"sourceKind": "ketores", "sharedMaterialWarning": "interior gold surfaces are nearby; "
                                                           "this is a decal only, no gold material is edited"}))
    origin = anchors["menorahOrigin"]
    lamp_xs = anchors["menorahLampLocalXCm"]
    bowl_z = anchors["menorahLampBowlLocalZCm"]
    for index, local_x in enumerate(lamp_xs):
        # Menorah yaw is -90 in the import receipt: local +X maps to world -Y.
        px = origin[0]
        py = origin[1] - local_x
        out.append(_entry(
            "soot", "Wear_Soot_MenorahLamp_%02d" % (index + 1),
            [px, py, origin[2] + bowl_z + 210.0], (90.0, 0.0, 0.0),
            [50.0, 46.0, 46.0], 0.8, 0.22,
            "Above menorah lamp %d (bowl at world Z %.1f). Olive oil burns clean but not "
            "perfectly; a small warm bloom above each of the seven, wiped back daily, "
            "never a black stain." % (index + 1, origin[2] + bowl_z),
            {"sourceKind": "menorahLamp"}))
    for index, side in enumerate((-1.0, 1.0)):
        out.append(_entry(
            "soot", "Wear_Soot_UlamLamp_%02d" % (index + 1),
            [-2470.0, side * 900.0, 1500.0], (0.0, 180.0, 0.0),
            [45.0, 90.0, 200.0], 0.55, 0.2,
            "Ulam face beside the doorway, above the standing lamps that light the "
            "entrance at night.",
            {"sourceKind": "entranceLamp"}))
    return out


UNION_ENVELOPE_NAME = "Derived union of source outer envelope walls"


def union_constituent_boxes(entry: dict) -> list:
    """World AABBs (cm) of the source boxes a derived union mesh was built from.

    The enclosure wall is NOT 116 separate meshes in the map: it is one Boolean union
    whose AABB is the entire court (+-8100 XY, Z 300..3425). Reading faces off that AABB
    would put lichen on thin air in the middle of the courtyard. The manifest carries the
    constituent boxes in sourceProperties.source_elements_json, and recomposing them
    reproduces the union's expectedBoundsUnrealCm exactly, which is what makes this safe
    to rely on. Same decomposition as Scripts/release_place_assets.py, deliberately
    mirrored rather than imported: this file must stay runnable with no engine and no
    other release script present.

    Source elements are in amot with X east, Y up, Z south; expectedSourceToUnrealCm is
    [x*50, z*50, y*50]. 'position' is the box centre and 'size' the full extent.
    """
    properties = entry.get("sourceProperties") or {}
    if "source_elements_json" not in properties:
        return []
    scale = float(properties.get("source_metres_per_amah", 0.5)) * 100.0
    boxes = []
    for element in json.loads(properties["source_elements_json"]):
        if element.get("shape") != "box":
            return []
        position, size = element["position"], element["size"]
        middle = [position[0] * scale, position[2] * scale, position[1] * scale]
        half = [size[0] * scale / 2.0, size[2] * scale / 2.0, size[1] * scale / 2.0]
        boxes.append({
            "name": element.get("name") or "unnamed",
            "min": [middle[i] - half[i] for i in range(3)],
            "max": [middle[i] + half[i] for i in range(3)],
        })
    return boxes


def _outer_wall_faces(raw_rows: list) -> list:
    """Outward faces of the enclosure wall, the only fabric old enough to carry lichen.

    Decomposed from the outer envelope union (see above) and filtered to the boxes that
    actually reach the perimeter, so the faces returned are real wall, not window
    reveals and not the union's whole-court bounding box.
    """
    entry = None
    for row in raw_rows:
        if row.get("sourceName") == UNION_ENVELOPE_NAME:
            entry = row
            break
    if entry is None:
        raise RuntimeError("Outer envelope union %r is not in the architecture manifest"
                           % UNION_ENVELOPE_NAME)
    boxes = union_constituent_boxes(entry)
    if not boxes:
        raise RuntimeError("Outer envelope union carries no decomposable source elements")

    recomposed_min = [min(b["min"][i] for b in boxes) for i in range(3)]
    recomposed_max = [max(b["max"][i] for b in boxes) for i in range(3)]
    expected = entry["expectedBoundsUnrealCm"]
    error = max(max(abs(recomposed_min[i] - expected["min"][i]),
                    abs(recomposed_max[i] - expected["max"][i])) for i in range(3))
    if error > 0.5:
        raise RuntimeError("Union decomposition does not recompose to the manifest bounds "
                           "(worst axis error %.3f cm); refusing to place wear off it" % error)

    faces = []
    for box in boxes:
        span_x = box["max"][0] - box["min"][0]
        span_y = box["max"][1] - box["min"][1]
        height = box["max"][2] - box["min"][2]
        if height < 200.0:
            continue
        middle = [(box["min"][i] + box["max"][i]) * 0.5 for i in range(3)]
        if span_x <= span_y:
            axis, run = 0, span_y
            coord = box["max"][0] if middle[0] > 0 else box["min"][0]
            yaw = 0.0 if middle[0] > 0 else 180.0
        else:
            axis, run = 1, span_x
            coord = box["max"][1] if middle[1] > 0 else box["min"][1]
            yaw = 90.0 if middle[1] > 0 else 270.0
        if abs(coord) < 7600.0:                     # not on the outward perimeter
            continue
        if run < 300.0:
            continue
        faces.append({"box": box, "name": box["name"], "axis": axis, "yaw": yaw,
                      "coord": coord, "run": run, "height": height,
                      "baseZ": box["min"][2], "topZ": box["max"][2]})
    return faces


def _panels(face: dict, target_cm: float, limit: int) -> list:
    """Slice a wall face into panels about target_cm wide. Returns (centre x, y, half)."""
    box = face["box"]
    count = max(1, min(limit, int(round(face["run"] / target_cm))))
    out = []
    for panel in range(count):
        t = (panel + 0.5) / count
        if face["axis"] == 0:
            px, py = face["coord"], box["min"][1] + face["run"] * t
        else:
            px, py = box["min"][0] + face["run"] * t, face["coord"]
        out.append((px, py, face["run"] / (2.0 * count)))
    return out


def candidates_lichen(rows, routes, anchors):
    """Lichen only where it can actually live: old, damp and shaded.

    Jerusalem is 31.8 N, so a north-facing face (world -Y here) is the shaded one and a
    south-facing face bakes. LichenCoverage returns exactly zero below the settle age, so
    the inner court -- dressed eight years ago in this model -- carries none at all, which
    is the whole point: new stone has to READ new next to old stone.

    Placed only in the damp band near the ground. Lichen 25 metres up a dry sunlit wall
    would be nonsense, and it is the band by the paving that a walker actually sees.
    """
    out = []
    for index, face in enumerate(_outer_wall_faces(rows)):
        c = [(face["box"]["min"][i] + face["box"]["max"][i]) * 0.5 for i in range(2)]
        tier = age_tier(c[0], c[1])
        # yaw 270 is the -Y (north-facing) wall: shaded all day. yaw 90 faces +Y: baked.
        shade = {270.0: 0.85, 0.0: 0.35, 180.0: 0.45, 90.0: 0.10}[face["yaw"]]
        coverage = lichen_coverage(0.95, shade, tier["ageYears"])
        if coverage < 0.04:
            continue
        # Only near the ground. The gate lintel box also passes the face filter, and its
        # base is 28 m up; lichen on a dry sunlit lintel would be the kind of detail that
        # makes a render look MORE synthetic, not less.
        if face["baseZ"] > 700.0:
            continue
        band = min(380.0, face["height"] * 0.35)
        # About 5.5 m per patch: a lichen colony is a patch, not a wall-length band, and
        # the enclosure's wall boxes are 11 m runs.
        for panel, (px, py, half) in enumerate(_panels(face, 550.0, 20)):
            out.append(_entry(
                "lichen", "Wear_Lichen_%03d_%d" % (index, panel),
                [px, py, face["baseZ"] + band * 0.5],
                (0.0, _yaw(face["yaw"] + 180.0), 0.0),
                [40.0, half * 0.94, band * 0.5],
                round(0.25 + 1.5 * coverage, 5),
                round(clamp_range(coverage * 2.0, 0.05, 0.5), 4),
                "Damp band on the lower %.0f cm of '%s' (%s tier, %.0f y, shade %.2f). "
                "Coverage %.3f -- patchy grey-green near the ground on the shaded side, "
                "and nothing at all on the inner court, which is new stone."
                % (band, face["name"], tier["id"], tier["ageYears"], shade, coverage),
                {"lichenCoverage": round(coverage, 4), "shadeFraction": shade,
                 "ageTier": tier["id"], "ageYears": tier["ageYears"],
                 "wallFace": face["name"], "wallBaseZCm": round(face["baseZ"], 1)}))
    return out


def candidates_wind_dust(rows, routes, anchors):  # noqa: C901
    """Wind-blown dust: it drifts where the air stops, so it goes where feet do not.

    Scored by the INVERSE of traffic. A corner that carries a route is swept by the feet
    that use it; a corner nobody crosses fills up.
    """
    out = []
    walkable = build_walkable_index(rows)
    reach = 7500.0
    corners = [(sx * reach, sy * reach, sx, sy) for sx in (-1.0, 1.0) for sy in (-1.0, 1.0)]
    index = 0
    for cx, cy, sx, sy in corners:
        for step in range(8):
            t = step / 7.0
            # Walk out of the corner along both walls. At t == 0 both walks are AT the
            # corner, so only one of them may emit or the corner gets two identical decals.
            for along_x in ((True,) if step == 0 else (True, False)):
                px = cx - sx * (2100.0 * t) if along_x else cx
                py = cy if along_x else cy - sy * (2100.0 * t)
                trips = traffic_density(px, py, routes)
                quiet = 1.0 / (1.0 + trips / 400.0)
                if quiet < 0.35:
                    continue
                index += 1
                out.append(_entry(
                    "windDust", "Wear_WindDust_Corner_%02d" % index,
                    [px, py, floor_z_at(walkable, px, py)],
                    (-90.0, math.degrees(math.atan2(sy, sx)), 0.0),
                    [40.0, 200.0 + 120.0 * quiet, 200.0 + 120.0 * quiet],
                    round(0.2 + 0.6 * quiet, 5), round(clamp_range(0.35 * quiet, 0.05, 0.45), 4),
                    "Court corner drift at (%.0f, %.0f). Only %.0f trips/day reach here, "
                    "so nothing sweeps it: the dust the wind carries in against the wall "
                    "stays. Quiet factor %.2f." % (px, py, trips, quiet),
                    {"trafficTripsPerDay": round(trips, 1), "quietFactor": round(quiet, 4)}))
    # Against the wall bases all the way round, wherever the ring route does not scrub.
    for k in range(64):
        angle = k / 64.0 * 2.0 * math.pi
        px = math.cos(angle) * 7600.0
        py = math.sin(angle) * 7600.0
        px = clamp_range(px, -7600.0, 7600.0)
        py = clamp_range(py, -7600.0, 7600.0)
        trips = traffic_density(px, py, routes)
        quiet = 1.0 / (1.0 + trips / 400.0)
        if quiet < 0.5:
            continue
        out.append(_entry(
            "windDust", "Wear_WindDust_WallFoot_%02d" % k,
            [px, py, floor_z_at(walkable, px, py)], (-90.0, math.degrees(angle), 0.0),
            [35.0, 210.0, 150.0], round(0.15 + 0.4 * quiet, 5),
            round(clamp_range(0.28 * quiet, 0.04, 0.36), 4),
            "Dust banked against the wall foot; %.0f trips/day, quiet factor %.2f."
            % (trips, quiet),
            {"trafficTripsPerDay": round(trips, 1), "quietFactor": round(quiet, 4)}))

    # The lee pocket beside each gate jamb. The mouth is 500 cm wide and the traffic
    # goes straight through the middle of it, so the re-entrant corner at either cheek
    # is sheltered from both the wind and the feet: dust collects there and stays,
    # right beside the most polished stone in the building. That contrast is the point.
    for name, tag, yaw in GATE_NAMES:
        row = named(rows, name)[0]
        c = centre(row)
        along = 1 if yaw == 0.0 else 0                 # the axis the mouth is wide on
        for side, sign in (("A", -1.0), ("B", 1.0)):
            point = list(c[:2])
            point[along] = (row["min"][along] if sign < 0 else row["max"][along]) - sign * 60.0
            trips = traffic_density(point[0], point[1], routes)
            quiet = 1.0 / (1.0 + trips / 400.0)
            out.append(_entry(
                "windDust", "Wear_WindDust_GateCheek_%s_%s" % (tag, side),
                [point[0], point[1], row["max"][2]], (-90.0, yaw, 0.0),
                [35.0, 90.0, 150.0], round(0.3 + 0.3 * quiet, 5),
                round(clamp_range(0.30 * quiet + 0.06, 0.06, 0.4), 4),
                "Lee pocket at the %s cheek of the %s. Feet pass through the middle of "
                "the 500 cm mouth, not the corner, so this stone is never scuffed clean; "
                "%.0f trips/day reach it, quiet factor %.2f." % (side, name, trips, quiet),
                {"trafficTripsPerDay": round(trips, 1), "quietFactor": round(quiet, 4)}))
    return out


def candidates_weathering(rows, routes, anchors):
    """General weathering on the old outer fabric, and deliberately none on the new."""
    out = []
    for index, face in enumerate(_outer_wall_faces(rows)):
        c = [(face["box"]["min"][i] + face["box"]["max"][i]) * 0.5 for i in range(2)]
        tier = age_tier(c[0], c[1])
        exposure = 0.95
        weather = weathering(exposure, tier["ageYears"])
        if weather < 0.15:
            continue
        variation = stone_variation(SEED, hash32(index * 7919), weather)
        height = min(1400.0, face["height"])
        for panel, (px, py, half) in enumerate(_panels(face, 1600.0, 14)):
            out.append(_entry(
                "weathering", "Wear_Weathering_%03d_%d" % (index, panel),
                [px, py, face["baseZ"] + height * 0.5],
                (0.0, _yaw(face["yaw"] + 180.0), 0.0),
                [40.0, half * 0.92, height * 0.5],
                round(0.2 + 0.6 * weather, 5),
                round(clamp_range(weather * 0.55, 0.05, 0.45), 4),
                "Weathered outward face of '%s' (%s tier, %.0f y). Weathering %.3f: the "
                "surface has opened slightly and yellowed. Tint %.3f/%.3f/%.3f, roughness "
                "x%.3f -- the same jitter the ashlar palette uses, so the decal and the "
                "stone under it agree about how old this wall is."
                % (face["name"], tier["id"], tier["ageYears"], weather,
                   variation["tintR"], variation["tintG"], variation["tintB"],
                   variation["roughnessScale"]),
                {"weatheringFraction": round(weather, 4), "ageTier": tier["id"],
                 "wallFace": face["name"],
                 "stoneVariation": {k: round(v, 5) for k, v in variation.items()}}))
    return out


GENERATORS = {
    "footPolish": candidates_foot_polish,
    "stepNosing": candidates_step_nosing,
    "rainStreak": candidates_rain_streak,
    "dustRunoff": candidates_dust_runoff,
    "waterStain": candidates_water_stain,
    "soot": candidates_soot,
    "lichen": candidates_lichen,
    "windDust": candidates_wind_dust,
    "weathering": candidates_weathering,
}


def build_table(rows, routes, anchors) -> tuple:
    """Generate, score, trim to the planned request per category, and allocate."""
    table = []
    per_category = {}
    for category in CATEGORIES:
        found = GENERATORS[category["id"]](rows, routes, anchors)
        # Deterministic ordering: importance first, then a stable hash of the label,
        # then the label itself.
        #
        # The hash matters. Whole categories tie on importance -- every outward ledge on
        # the enclosure weathers identically -- and sorting a tie by label alone takes
        # them in mesh order, which put all 64 rain streaks on the single +X wall and left
        # the other three bare. Scattering the tie spreads the same 64 decals round the
        # whole building, and a SHA-256 of the label is stable across runs and machines in
        # a way Python's salted hash() is not.
        found.sort(key=lambda e: (-e["importance"], label_key(e["label"]), e["label"]))
        if len(found) < category["requested"]:
            raise RuntimeError(
                "Category %s generated only %d candidates but the plan requests %d. "
                "Either the rule got stricter or the geometry moved."
                % (category["id"], len(found), category["requested"]))
        chosen = found[:category["requested"]]
        for rank, entry in enumerate(chosen):
            entry["rank"] = rank
            entry["material"] = category["material"]
            entry["texture"] = category["texture"]
            entry["sortOrder"] = category["sortOrder"]
            entry["fadeStartCm"] = category["fadeStartCm"]
            entry["fadeEndCm"] = category["fadeEndCm"]
        per_category[category["id"]] = {
            "generated": len(found), "requested": category["requested"],
            "kept": len(chosen),
        }
        table += chosen
    counts = allocate_budget(CATEGORIES, BUDGET_CAP)
    for category, count in zip(CATEGORIES, counts):
        per_category[category["id"]]["allocatedAtCap"] = count
    return table, per_category, counts


# ---------------------------------------------------------------------------
# Per-instance meleke variation.
#
# 1155 ashlar components cannot each own a material asset. A palette of variants,
# indexed by a hash of the component name, breaks the repeat at a fixed asset cost;
# the quantisation is recorded honestly rather than described as per-instance.
# ---------------------------------------------------------------------------

VARIANT_FAMILIES = [
    {"id": "ashlar", "parent": "/Game/MikdashV3/Materials/PBR/Instances/MI_PBR_LimestoneAshlar",
     "variants": 10, "componentsInMap": 1155,
     "note": "Court and enclosure ashlar. The single biggest source of the 'one repeated "
             "texture' read, so it gets the widest palette."},
    {"id": "trim", "parent": "/Game/MikdashV3/Materials/PBR/Instances/MI_PBR_LimestoneTrim",
     "variants": 8, "componentsInMap": 332,
     "note": "String courses, cornices, sills and jambs."},
    {"id": "paving", "parent": "/Game/MikdashV3/Materials/PBR/Instances/MI_PBR_PavingSlabs",
     "variants": 8, "componentsInMap": 181,
     "note": "Court floors. Jitter here is what stops the paving reading as one tile."},
]


def build_variant_palette() -> list:
    """Tint and roughness for every variant, per age tier, from StoneVariation."""
    families = []
    for family in VARIANT_FAMILIES:
        entries = []
        for tier in AGE_TIERS:
            weather = weathering(tier["exposure"], tier["ageYears"])
            for index in range(family["variants"]):
                key = hash32(hash32(index * 2654435761) ^ hash32(len(entries) + 1))
                variation = stone_variation(SEED, key, weather)
                entries.append({
                    "name": "MI_Meleke_%s_%s_%02d" % (
                        family["id"][0].upper() + family["id"][1:], tier["id"], index),
                    "family": family["id"],
                    "ageTier": tier["id"],
                    "ageYears": tier["ageYears"],
                    "variantIndex": index,
                    "parent": family["parent"],
                    "weatheringFraction": round(weather, 5),
                    "scalars": {"RoughnessScale": round(variation["roughnessScale"], 5)},
                    "vectors": {"Tint": [round(variation["tintR"], 5),
                                         round(variation["tintG"], 5),
                                         round(variation["tintB"], 5), 1.0]},
                })
        families.append(dict(family, instances=entries))
    return families


# ---------------------------------------------------------------------------
# PNG writing (RGB8, filter 0). Same encoder as Scripts/create_fx_materials.py.
# ---------------------------------------------------------------------------

def write_png_rgb(path: Path, width: int, height: int, rows: list) -> str:
    raw = bytearray()
    for row in rows:
        raw.append(0)
        raw.extend(row)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack("!I", len(data)) + kind + data
                + struct.pack("!I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack("!2I5B", width, height, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return hashlib.sha256(png).hexdigest()


# ---------------------------------------------------------------------------
# Tileable value noise, identical in construction to the FX bakery's.
# ---------------------------------------------------------------------------

_OCTAVE_CACHE: dict = {}


def _smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def octave_plane(width: int, height: int, period: int, seed: int) -> list:
    key = (width, height, period, seed)
    cached = _OCTAVE_CACHE.get(key)
    if cached is not None:
        return cached
    lattice = [hash01(seed, iy * 8191 + ix) for iy in range(period) for ix in range(period)]
    sx = period / float(width)
    sy = period / float(height)
    ix0 = [0] * width
    ix1 = [0] * width
    fx = [0.0] * width
    for x in range(width):
        u = x * sx
        i0 = int(math.floor(u)) % period
        ix0[x] = i0
        ix1[x] = (i0 + 1) % period
        fx[x] = _smoothstep(u - math.floor(u))
    plane = []
    for y in range(height):
        v = y * sy
        j0 = int(math.floor(v)) % period
        j1 = (j0 + 1) % period
        fy = _smoothstep(v - math.floor(v))
        row0, row1 = j0 * period, j1 * period
        out = [0.0] * width
        for x in range(width):
            a = lattice[row0 + ix0[x]]
            b = lattice[row0 + ix1[x]]
            c = lattice[row1 + ix0[x]]
            d = lattice[row1 + ix1[x]]
            t = fx[x]
            top = a + (b - a) * t
            bot = c + (d - c) * t
            out[x] = top + (bot - top) * fy
        plane.append(out)
    _OCTAVE_CACHE[key] = plane
    return plane


def fbm(width, height, base_period, octaves, seed, gain=0.5) -> list:
    planes = []
    amp, total, period = 1.0, 0.0, base_period
    for k in range(octaves):
        planes.append((octave_plane(width, height, period, seed + k * 977), amp))
        total += amp
        amp *= gain
        period *= 2
    inv = 1.0 / total
    out = []
    for y in range(height):
        row = [0.0] * width
        for plane, a in planes:
            src = plane[y]
            for x in range(width):
                row[x] += src[x] * a
        for x in range(width):
            row[x] *= inv
        out.append(row)
    return out


def _b(v: float) -> int:
    return 0 if v <= 0.0 else (255 if v >= 1.0 else int(v * 255.0 + 0.5))


def _pack(width, height, r_field, g_field, b_field) -> list:
    rows = []
    for y in range(height):
        row = bytearray(width * 3)
        for x in range(width):
            row[x * 3 + 0] = _b(r_field[y][x])
            row[x * 3 + 1] = _b(g_field[y][x])
            row[x * 3 + 2] = _b(b_field[y][x])
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Texture builders.
#
# Every one packs R = opacity mask, G = roughness weight (how much this decal
# smooths or roughens what it lands on), B = a secondary detail the material can
# lerp albedo with. One fetch, three jobs.
# ---------------------------------------------------------------------------

def build_foot_polish(size=512):
    grain = fbm(size, size, 24, 3, 0x5011)
    coarse = fbm(size, size, 6, 2, 0x5013)
    r, g, b = [], [], []
    for y in range(size):
        ry, gy, by = [0.0] * size, [0.0] * size, [0.0] * size
        v = (y + 0.5) / size * 2.0 - 1.0
        for x in range(size):
            u = (x + 0.5) / size * 2.0 - 1.0
            # An elongated, soft-edged pool: feet spread across a path, not a circle.
            d = math.sqrt((u * 1.25) ** 2 + (v * 0.80) ** 2)
            shape = _smoothstep(clamp01(1.0 - d))
            wobble = 0.72 + 0.56 * coarse[y][x]
            mask = clamp01(shape * wobble)
            ry[x] = mask * mask
            gy[x] = clamp01(mask * (0.55 + 0.45 * grain[y][x]))
            by[x] = clamp01(0.35 + 0.5 * grain[y][x] * mask)
        r.append(ry); g.append(gy); b.append(by)
    return _pack(size, size, r, g, b), ("R polish mask (elongated pool, soft edge), "
                                        "G roughness-reduction weight, B fine grain for albedo lerp")


def build_step_nosing(size=256):
    grain = fbm(size, size, 40, 3, 0x6011)
    r, g, b = [], [], []
    for y in range(size):
        ry, gy, by = [0.0] * size, [0.0] * size, [0.0] * size
        v = (y + 0.5) / size
        # The darkened band hugs one edge: the arris, not the middle of the tread.
        band = _smoothstep(clamp01(1.0 - abs(v - 0.5) * 2.6))
        for x in range(size):
            u = (x + 0.5) / size
            ends = _smoothstep(clamp01(min(u, 1.0 - u) * 8.0))
            chip = 0.55 + 0.75 * grain[y][x]
            mask = clamp01(band * ends * chip)
            ry[x] = mask
            gy[x] = clamp01(mask * 0.85)
            by[x] = clamp01(0.4 + 0.6 * grain[y][x])
        r.append(ry); g.append(gy); b.append(by)
    return _pack(size, size, r, g, b), ("R nosing darkening band along one edge, "
                                        "G roughness reduction (rounded arris), B chip detail")


def build_rain_streak(size=512):
    fine = fbm(size, size, 64, 2, 0x7011)
    drift = fbm(size, size, 8, 2, 0x7017)
    r, g, b = [], [], []
    for y in range(size):
        ry, gy, by = [0.0] * size, [0.0] * size, [0.0] * size
        v = (y + 0.5) / size                 # 0 at the ledge, 1 at the bottom of the run
        for x in range(size):
            u = (x + 0.5) / size
            # Vertical drips: a high-frequency field in u only, so the streaks are
            # continuous down the wall instead of turning into noise.
            column = fine[int(u * (size - 1))][0] if False else fine[0][x]
            run_len = 0.25 + 0.75 * column
            fall = clamp01(1.0 - v / max(1e-3, run_len))
            wobble = 0.85 + 0.3 * drift[y][x]
            near = _smoothstep(clamp01(1.0 - v * 4.0))       # heaviest just under the ledge
            mask = clamp01((fall ** 1.6) * wobble * (0.45 + 0.55 * near))
            ry[x] = mask
            gy[x] = clamp01(mask * 0.4)
            by[x] = clamp01(0.3 + 0.7 * drift[y][x])
        r.append(ry); g.append(gy); b.append(by)
    return _pack(size, size, r, g, b), ("R vertical drip opacity (tiles left-right, "
                                        "runs top to bottom), G roughening weight, B dirt colour break-up")


def build_dust_runoff(size=512):
    soft = fbm(size, size, 10, 3, 0x8011)
    r, g, b = [], [], []
    for y in range(size):
        ry, gy, by = [0.0] * size, [0.0] * size, [0.0] * size
        v = (y + 0.5) / size
        fall = clamp01(1.0 - v) ** 2.2
        for x in range(size):
            mask = clamp01(fall * (0.55 + 0.75 * soft[y][x]))
            ry[x] = mask
            gy[x] = clamp01(mask * 0.65)
            by[x] = clamp01(0.45 + 0.55 * soft[y][x])
        r.append(ry); g.append(gy); b.append(by)
    return _pack(size, size, r, g, b), ("R soft runoff wash, strongest at the top, "
                                        "G roughening, B dust colour break-up")


def build_water_stain(size=512):
    blotch = fbm(size, size, 7, 3, 0x9011)
    rim = fbm(size, size, 28, 2, 0x9019)
    r, g, b = [], [], []
    for y in range(size):
        ry, gy, by = [0.0] * size, [0.0] * size, [0.0] * size
        v = (y + 0.5) / size * 2.0 - 1.0
        for x in range(size):
            u = (x + 0.5) / size * 2.0 - 1.0
            d = math.sqrt(u * u + v * v)
            edge = clamp01(1.0 - d)
            damp = clamp01(_smoothstep(edge) * (0.5 + 0.9 * blotch[y][x]))
            # Mineral rim: the ring where the water repeatedly stops and dries.
            ring = clamp01(1.0 - abs(damp - 0.35) * 7.0) * (0.5 + 0.5 * rim[y][x])
            ry[x] = damp
            gy[x] = clamp01(damp * 0.95)      # wet stone is smoother, strongly so
            by[x] = clamp01(ring)
        r.append(ry); g.append(gy); b.append(by)
    return _pack(size, size, r, g, b), ("R damp mask, G roughness-reduction weight "
                                        "(wet stone is smoother), B dried mineral rim")


def build_soot(size=512):
    plume = fbm(size, size, 9, 4, 0xA011)
    fine = fbm(size, size, 36, 2, 0xA019)
    r, g, b = [], [], []
    for y in range(size):
        ry, gy, by = [0.0] * size, [0.0] * size, [0.0] * size
        v = (y + 0.5) / size
        rise = clamp01(1.0 - v) ** 1.3        # densest at the source, thinning upward
        for x in range(size):
            u = (x + 0.5) / size * 2.0 - 1.0
            spread = clamp01(1.0 - abs(u) / (0.35 + 0.65 * v))
            mask = clamp01(rise * _smoothstep(spread) * (0.5 + 0.85 * plume[y][x]))
            ry[x] = mask
            gy[x] = clamp01(mask * 0.5)
            by[x] = clamp01(0.35 + 0.65 * fine[y][x])
        r.append(ry); g.append(gy); b.append(by)
    return _pack(size, size, r, g, b), ("R soot density, widening and thinning upward, "
                                        "G roughening, B fine carbon speckle")


def build_lichen(size=512):
    patch = fbm(size, size, 14, 4, 0xB011, gain=0.62)
    micro = fbm(size, size, 56, 2, 0xB017)
    r, g, b = [], [], []
    for y in range(size):
        ry, gy, by = [0.0] * size, [0.0] * size, [0.0] * size
        for x in range(size):
            # Hard-ish threshold: lichen grows in colonies with edges, not as a gradient.
            core = clamp01((patch[y][x] - 0.46) * 4.2)
            mask = clamp01(core * (0.6 + 0.6 * micro[y][x]))
            ry[x] = mask
            gy[x] = clamp01(mask * 0.8)
            by[x] = clamp01(0.3 + 0.7 * micro[y][x])
        r.append(ry); g.append(gy); b.append(by)
    return _pack(size, size, r, g, b), ("R colony mask with real edges (thresholded fBm), "
                                        "G roughening, B within-colony colour variation")


def build_wind_dust(size=512):
    drift = fbm(size, size, 11, 3, 0xC011)
    r, g, b = [], [], []
    for y in range(size):
        ry, gy, by = [0.0] * size, [0.0] * size, [0.0] * size
        v = (y + 0.5) / size
        # A drift banked against an edge: deep at v=0, feathering out across the floor.
        bank = clamp01(1.0 - v) ** 1.8
        for x in range(size):
            mask = clamp01(bank * (0.45 + 0.9 * drift[y][x]))
            ry[x] = mask
            gy[x] = clamp01(mask * 0.9)       # dust roughens what it lands on
            by[x] = clamp01(0.5 + 0.5 * drift[y][x])
        r.append(ry); g.append(gy); b.append(by)
    return _pack(size, size, r, g, b), ("R drift depth banked against one edge, "
                                        "G roughening, B grain")


def build_weathering(size=512):
    broad = fbm(size, size, 5, 4, 0xD011)
    grain = fbm(size, size, 44, 2, 0xD017)
    r, g, b = [], [], []
    for y in range(size):
        ry, gy, by = [0.0] * size, [0.0] * size, [0.0] * size
        for x in range(size):
            mask = clamp01(0.25 + 0.75 * broad[y][x])
            ry[x] = mask
            gy[x] = clamp01(0.4 + 0.6 * grain[y][x])
            by[x] = clamp01(broad[y][x] * 0.6 + grain[y][x] * 0.4)
        r.append(ry); g.append(gy); b.append(by)
    return _pack(size, size, r, g, b), ("R broad tonal variation (tiles), G surface grain "
                                        "for roughness, B combined field for albedo yellowing")


def build_dust_puff(size=256):
    """The footstep response on dry stone: one radial puff, used by AMikdashSurfaceDetail."""
    lumps = fbm(size, size, 12, 3, 0xE011)
    r, g, b = [], [], []
    for y in range(size):
        ry, gy, by = [0.0] * size, [0.0] * size, [0.0] * size
        v = (y + 0.5) / size * 2.0 - 1.0
        for x in range(size):
            u = (x + 0.5) / size * 2.0 - 1.0
            d = math.sqrt(u * u + v * v)
            core = _smoothstep(clamp01(1.0 - d))
            mask = clamp01(core * (0.45 + 0.95 * lumps[y][x]))
            ry[x] = mask
            gy[x] = clamp01(core)                     # clean radial falloff for the fade
            by[x] = clamp01(0.4 + 0.6 * lumps[y][x])
        r.append(ry); g.append(gy); b.append(by)
    return _pack(size, size, r, g, b), ("R lumpy puff opacity, G clean radial falloff "
                                        "driving the lifetime fade, B lump detail")


def build_ripple(size=256):
    """The footstep response on water: one expanding ring."""
    wobble = fbm(size, size, 18, 2, 0xF011)
    r, g, b = [], [], []
    for y in range(size):
        ry, gy, by = [0.0] * size, [0.0] * size, [0.0] * size
        v = (y + 0.5) / size * 2.0 - 1.0
        for x in range(size):
            u = (x + 0.5) / size * 2.0 - 1.0
            d = math.sqrt(u * u + v * v) * (0.92 + 0.16 * wobble[y][x])
            ring = clamp01(1.0 - abs(d - 0.72) * 9.0)
            inner = clamp01(1.0 - abs(d - 0.46) * 13.0) * 0.55
            fade = _smoothstep(clamp01(1.0 - d))
            ry[x] = clamp01((ring + inner) * fade)
            gy[x] = clamp01(fade)
            # B carries the signed crest so the material can push a normal, not just alpha.
            by[x] = clamp01(0.5 + 0.5 * (ring - inner))
        r.append(ry); g.append(gy); b.append(by)
    return _pack(size, size, r, g, b), ("R ring opacity (two crests), G radial fade, "
                                        "B signed crest for a normal push")


TEXTURE_PLAN = [
    ("T_Wear_FootPolish_512", 512, build_foot_polish, "Foot polish on walked stone."),
    ("T_Wear_StepNosing_256", 256, build_step_nosing, "Darkened, rounded step nosings."),
    ("T_Wear_RainStreak_512", 512, build_rain_streak, "Rain streaking below ledges."),
    ("T_Wear_DustRunoff_512", 512, build_dust_runoff, "Dust runoff below sheltered ledges."),
    ("T_Wear_WaterStain_512", 512, build_water_stain, "Damp staining near water and drainage."),
    ("T_Wear_Soot_512", 512, build_soot, "Soot above lamps and the altar fire."),
    ("T_Wear_Lichen_512", 512, build_lichen, "Lichen colonies on old shaded stone."),
    ("T_Wear_WindDust_512", 512, build_wind_dust, "Wind-blown dust drifted against walls."),
    ("T_Wear_Weathering_512", 512, build_weathering, "General weathering on old outer fabric."),
    ("T_Wear_DustPuff_256", 256, build_dust_puff, "Footstep dust puff on dry stone."),
    ("T_Wear_Ripple_256", 256, build_ripple, "Footstep ripple on water."),
]

TILEABLE = {"T_Wear_RainStreak_512", "T_Wear_DustRunoff_512", "T_Wear_Lichen_512",
            "T_Wear_WindDust_512", "T_Wear_Weathering_512"}


def bake_textures(write: bool) -> list:
    records = []
    for name, size, builder, purpose in TEXTURE_PLAN:
        rows, channels = builder(size)
        path = TEXTURES / (name + ".png")
        if write:
            digest = write_png_rgb(path, size, size, rows)
            size_bytes = path.stat().st_size
        else:
            raw = bytearray()
            for row in rows:
                raw.append(0)
                raw.extend(row)

            def chunk(kind, data):
                return (struct.pack("!I", len(data)) + kind + data
                        + struct.pack("!I", zlib.crc32(kind + data) & 0xFFFFFFFF))
            png = (b"\x89PNG\r\n\x1a\n"
                   + chunk(b"IHDR", struct.pack("!2I5B", size, size, 8, 2, 0, 0, 0))
                   + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
                   + chunk(b"IEND", b""))
            digest = hashlib.sha256(png).hexdigest()
            size_bytes = len(png)
        records.append({
            "name": name,
            "file": str((TEXTURES / (name + ".png")).relative_to(ROOT)).replace("\\", "/"),
            "width": size, "height": size,
            "format": "PNG RGB8",
            "channels": channels,
            "purpose": purpose,
            "sha256": digest,
            "sizeBytes": size_bytes,
            "srgb": False,
            "compressionSettings": "TC_Masks",
            "mipGenSettings": "TMGS_SimpleAverage",
            "addressX": "TA_Wrap" if name in TILEABLE else "TA_Clamp",
            "addressY": "TA_Wrap" if name in TILEABLE else "TA_Clamp",
            "destination": NAMESPACE + "/Textures",
        })
    return records


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

MASTER_DECAL = {
    "name": "M_SurfaceWear_Decal",
    "domain": "MD_DeferredDecal",
    "blendMode": "DBM_Translucent",
    "decalBlendMode": "DBUFFER_ColorRoughness",
    "decalBlendModeNote":
        "DBuffer colour+roughness, not the normal-writing variant: the wear must tint and "
        "smooth what it lands on without fighting the world-space normals the triplanar "
        "architecture material outputs (the meshes carry no UVs, so tangents are undefined).",
    "textureParameters": {"WearMask": "WearMask"},
    "scalarParameters": {
        "Opacity": 1.0,
        "RoughnessDelta": -0.15,
        "AlbedoDarken": 0.25,
        "DetailWeight": 0.5,
    },
    "vectorParameters": {"WearTint": [0.62, 0.58, 0.50, 1.0]},
    "graphNotes": [
        "TextureSampleParameter2D 'WearMask'; its UV pin is named 'UVs' in 5.8, not 'UV'.",
        "R -> Opacity multiply -> decal opacity. G -> lerp on RoughnessDelta. "
        "B -> lerp between WearTint and a slightly desaturated copy for within-decal variety.",
        "Desaturation's first input pin is named 'None' in 5.8; connect the colour there.",
        "Clamp's first input pin is also named 'None'.",
    ],
}

DECAL_INSTANCES = [
    {"name": "MI_Wear_FootPolish", "texture": "T_Wear_FootPolish_512",
     "scalars": {"Opacity": 1.0, "RoughnessDelta": -0.30, "AlbedoDarken": 0.16, "DetailWeight": 0.35},
     "tint": [0.60, 0.57, 0.51, 1.0],
     "note": "Polished stone goes DARKER and much SMOOTHER; it does not go shiny."},
    {"name": "MI_Wear_StepNosing", "texture": "T_Wear_StepNosing_256",
     "scalars": {"Opacity": 1.0, "RoughnessDelta": -0.26, "AlbedoDarken": 0.34, "DetailWeight": 0.5},
     "tint": [0.46, 0.43, 0.38, 1.0],
     "note": "Stronger darkening than open polish: the arris takes the whole sole."},
    {"name": "MI_Wear_RainStreak", "texture": "T_Wear_RainStreak_512",
     "scalars": {"Opacity": 1.0, "RoughnessDelta": 0.10, "AlbedoDarken": 0.30, "DetailWeight": 0.6},
     "tint": [0.44, 0.42, 0.38, 1.0],
     "note": "Streaks are dirt, so they ROUGHEN."},
    {"name": "MI_Wear_DustRunoff", "texture": "T_Wear_DustRunoff_512",
     "scalars": {"Opacity": 1.0, "RoughnessDelta": 0.14, "AlbedoDarken": -0.10, "DetailWeight": 0.5},
     "tint": [0.78, 0.73, 0.63, 1.0],
     "note": "Dust is LIGHTER than the stone, hence the negative darkening."},
    {"name": "MI_Wear_WaterStain", "texture": "T_Wear_WaterStain_512",
     "scalars": {"Opacity": 1.0, "RoughnessDelta": -0.38, "AlbedoDarken": 0.40, "DetailWeight": 0.55},
     "tint": [0.38, 0.37, 0.35, 1.0],
     "note": "Wet stone: much darker and much smoother, the strongest roughness delta in the set."},
    {"name": "MI_Wear_Soot", "texture": "T_Wear_Soot_512",
     "scalars": {"Opacity": 1.0, "RoughnessDelta": 0.16, "AlbedoDarken": 0.62, "DetailWeight": 0.4},
     "tint": [0.20, 0.19, 0.18, 1.0],
     "note": "Warm-black, never blue-black; carbon on limestone."},
    {"name": "MI_Wear_Lichen", "texture": "T_Wear_Lichen_512",
     "scalars": {"Opacity": 1.0, "RoughnessDelta": 0.22, "AlbedoDarken": 0.24, "DetailWeight": 0.7},
     "tint": [0.52, 0.55, 0.42, 1.0],
     "note": "Grey-green, low saturation. Jerusalem lichen is not moss."},
    {"name": "MI_Wear_WindDust", "texture": "T_Wear_WindDust_512",
     "scalars": {"Opacity": 1.0, "RoughnessDelta": 0.20, "AlbedoDarken": -0.14, "DetailWeight": 0.45},
     "tint": [0.80, 0.75, 0.64, 1.0],
     "note": "Pale, matt, and slightly lighter than the paving under it."},
    {"name": "MI_Wear_Weathering", "texture": "T_Wear_Weathering_512",
     "scalars": {"Opacity": 1.0, "RoughnessDelta": 0.12, "AlbedoDarken": 0.10, "DetailWeight": 0.65},
     "tint": [0.72, 0.66, 0.52, 1.0],
     "note": "The yellowing of aged meleke, applied broadly and weakly."},
    {"name": "MI_Wear_DustPuff", "texture": "T_Wear_DustPuff_256",
     "scalars": {"Opacity": 0.55, "RoughnessDelta": 0.10, "AlbedoDarken": -0.20, "DetailWeight": 0.4},
     "tint": [0.84, 0.79, 0.68, 1.0],
     "note": "Spawned at run time by AMikdashSurfaceDetail on a dry-stone footfall."},
    {"name": "MI_Wear_Ripple", "texture": "T_Wear_Ripple_256",
     "scalars": {"Opacity": 0.75, "RoughnessDelta": -0.20, "AlbedoDarken": 0.05, "DetailWeight": 0.3},
     "tint": [0.72, 0.78, 0.80, 1.0],
     "note": "Spawned at run time on a footfall over water."},
]

# Materials this pass must NOT touch. The 2026-09-07 sanctuary rebalance flattened the
# frieze relief and had to be restored from a checkpoint; the rule since is that a shared
# parent is never edited, only instanced.
PROTECTED_MATERIALS = [
    "/Game/MikdashV3/Materials/PBR/M_PBR_Tiled",
    "/Game/MikdashV3/Materials/PBR/Instances/MI_PBR_GoldFloor",
    "/Game/MikdashV3/Materials/PBR/Instances/MI_PBR_GoldHammered",
    "/Game/MikdashV3/MaterialReview/KeruvFriezeV2/Materials/M_KeruvFriezeV2",
    "/Game/MikdashV3/MaterialReview/KeruvFriezeV2/Materials/M_KeruvFriezeV2_Displaced",
    "/Game/MikdashV3/MaterialReview/KeruvFriezeV1/Materials/M_KeruvFrieze",
    "/Game/MikdashV3/MaterialReview/KeruvFriezeV1/Materials/M_KeruvFrieze_Displaced",
    "/Game/MikdashV3/MaterialReview/KeruvFriezeV1/Materials/M_KeruvFrieze_Tessellated",
    "/Game/MikdashV3/MaterialReview/KotelStoneV2/M_KotelAshlarV2",
    "/Game/MikdashV3/MaterialReview/SanctuaryFinishesV1/M_Sanctuary_gold",
    "/Game/MikdashV3/MaterialReview/SanctuaryPolishV1/M_GoldFloor",
    "/Game/MikdashV3/MaterialReview/SanctuaryPolishV1/M_GoldWall",
    "/Game/MikdashV3/MaterialReview/SanctuaryPolishV1/M_GoldVessel",
]
PROTECTED_PREFIXES = [
    "/Game/MikdashV3/MaterialReview/KotelStoneV1/",
    "/Game/MikdashV3/MaterialReview/KotelSurfacePolishV1/",
    "/Game/MikdashV3/MaterialReview/KotelSurfacePolishV2/",
    "/Game/MikdashV3/MaterialReview/KotelPhotoSurfaceV1/",
    "/Game/MikdashV3/MaterialReview/KotelPhotoSurfaceV2/",
]


# ---------------------------------------------------------------------------
# Cost estimate
# ---------------------------------------------------------------------------

def cost_estimate(table, counts) -> dict:
    """A stated estimate with its assumptions, not a measurement.

    No frame has been captured for this pass; nothing here is a profiling result.
    """
    texture_bytes = 0
    for name, size, _builder, _purpose in TEXTURE_PLAN:
        # BC7 is one byte per texel; mips add a third.
        texture_bytes += int(size * size * 1.34)
    return {
        "method": "arithmetic estimate from decal count, texture footprint and the "
                  "documented deferred-decal cost model; NOT a captured frame",
        "hardwareAssumed": "RTX 2070 8 GB, 1920x1080, the machine this project is built on",
        "decalsAuthored": len(table),
        "decalsSpawnedAtCap": int(sum(counts)),
        "decalsTypicallyInsideFadeRange": 96,
        "textureVramBytesBc7WithMips": texture_bytes,
        "textureVramMb": round(texture_bytes / 1048576.0, 2),
        "estimatedDecalPassMsAt1080p": 0.45,
        "estimatedDecalPassMsRange": [0.30, 0.70],
        "estimatedDrawCallsAdded": int(sum(counts)),
        "assumptions": [
            "DBuffer decals resolve before the base pass, so the cost scales with the "
            "screen area they cover, not with world size.",
            "The fade window keeps most of the 220 outside the range at any camera; the "
            "0.45 ms figure is for the ~96 typically inside it.",
            "No decal writes normals, which halves the DBuffer target cost.",
            "The eleven textures share one BC7 format and one sampler per material.",
        ],
        "acceptance": "unmeasured; a capture is required before any performance claim",
    }


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def verify_routes(routes, rows) -> list:
    """Every route vertex must sit on a real measured feature."""
    features = []
    for name, tag, _yaw in GATE_NAMES:
        c = centre(named(rows, name)[0])
        features.append((name, c[0], c[1]))
    for prefix, tag, axis, _direction in STAIR_FLIGHTS:
        steps = named(rows, prefix)
        if not steps:
            continue
        lo = min(s["min"][axis] for s in steps)
        hi = max(s["max"][axis] for s in steps)
        for value in (lo, hi):
            if axis == 0:
                features.append((prefix, value, 0.0))
            else:
                features.append((prefix, 0.0, value))
    basin = named(rows, "Hollow basin with inner wall")
    if basin:
        c = centre(basin[0])
        features.append(("Hollow basin with inner wall", c[0], c[1]))

    report = []
    if sorted(r["id"] for r in routes) != sorted(CPP_TEST_ROUTES):
        raise RuntimeError("Route set differs from the C++ test's: %s vs %s"
                           % (sorted(r["id"] for r in routes), sorted(CPP_TEST_ROUTES)))
    for route in routes:
        derived = [[round(px, 1), round(py, 1)] for px, py in route["points"]]
        expected = [[round(px, 1), round(py, 1)] for px, py in CPP_TEST_ROUTES[route["id"]]]
        if derived != expected:
            raise RuntimeError(
                "Route %s derived from the manifest as %s but SurfaceWearMathTest.cpp "
                "still holds %s. Update both, or the planner and the tested runtime are "
                "wearing different buildings." % (route["id"], derived, expected))
        parameters = (route["halfWidthCm"], route["featherCm"], route["tripsPerDay"])
        if parameters != CPP_TEST_ROUTE_PARAMETERS[route["id"]]:
            raise RuntimeError(
                "Route %s carries %s here but %s in SurfaceWearMathTest.cpp."
                % (route["id"], parameters, CPP_TEST_ROUTE_PARAMETERS[route["id"]]))
    for route in routes:
        for index, (px, py) in enumerate(route["points"]):
            best, best_distance = None, math.inf
            for name, fx, fy in features:
                d = math.hypot(px - fx, py - fy)
                if d < best_distance:
                    best, best_distance = name, d
            # An interior court vertex is allowed to be a plain court point: it only has
            # to be inside the court and on an axis the routes actually use.
            axis_ok = abs(px) < 1.0 or abs(py) < 1.0 or route["id"] in ("outerCourtRing", "laverToRamp")
            ok = best_distance <= ROUTE_VERTEX_TOLERANCE_CM or axis_ok
            report.append({"route": route["id"], "vertex": index,
                           "pointCm": [px, py], "nearestFeature": best,
                           "distanceCm": round(best_distance, 2),
                           "onMeasuredFeature": best_distance <= ROUTE_VERTEX_TOLERANCE_CM,
                           "onRouteAxis": axis_ok, "accepted": ok})
            if not ok:
                raise RuntimeError(
                    "Route %s vertex %d at (%.1f, %.1f) is %.1f cm from the nearest measured "
                    "feature (%s) and is not on a route axis."
                    % (route["id"], index, px, py, best_distance, best))
    return report


def cross_check_against_cpp() -> dict:
    """Compare the Python mirror with the numbers the C++ test printed, if present."""
    if not TESTS_JSON.exists():
        return {"available": False,
                "note": "SourceAssets/surface-review/tests.json not present; run "
                        "SurfaceWearMathTest.exe with that path to produce it."}
    data = json.loads(TESTS_JSON.read_text(encoding="utf-8"))
    measured = data.get("measurements", {})
    checks = {
        "falloffOnCentreLine": wear_falloff(0.0, 200.0, 300.0),
        "falloffAtHalfWidth": wear_falloff(200.0, 200.0, 300.0),
        "falloffBeyondFeather": wear_falloff(500.0, 200.0, 300.0),
        "fadeAtStart": distance_fade(3000.0, 3000.0, 9000.0),
        "fadeMidway": distance_fade(6000.0, 3000.0, 9000.0),
        "fadeAtEnd": distance_fade(9000.0, 3000.0, 9000.0),
        "polishRoughnessScaleFull": polish_roughness_scale(1.0),
    }
    mismatched = {}
    compared = 0
    for key, value in checks.items():
        if key not in measured:
            continue
        compared += 1
        if abs(float(measured[key]) - value) > 1e-5:
            mismatched[key] = {"cpp": float(measured[key]), "python": value}
    return {"available": True, "compared": compared, "mismatched": mismatched,
            "allPassed": data.get("allPassed"), "checksEvaluated": data.get("checksEvaluated")}


def assemble(write: bool) -> dict:
    rows = load_architecture()
    anchors = load_anchors()
    routes = build_routes(rows)
    route_report = verify_routes(routes, rows)
    table, per_category, counts = build_table(rows, routes, anchors)
    textures = bake_textures(write)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "status": "surface_wear_plan_generated_no_map_touched",
        "generatedBy": "Scripts/create_decals.py",
        "generatorSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "mathHeader": "Plugins/MikdashRuntime/Source/MikdashRuntime/Public/SurfaceWearMath.h",
        "mathTest": "Plugins/MikdashRuntime/Tests/SurfaceWearMathTest.cpp",
        "runtimeActor": "AMikdashSurfaceDetail "
                        "(Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashSurfaceDetail.h)",
        "seed": SEED,
        "namespace": NAMESPACE,
        "honesty": [
            "Nothing here is a measurement of the historical Mikdash. Rainfall, ages, "
            "traffic and polish rates are an artistic weathering model for Jerusalem "
            "meleke on a building that is maintained daily.",
            "What is modelled is the wear of HEAVY USE AND WEATHER, never decay: no "
            "cracks, no spalling, no missing stone, no ruin.",
            "Decal positions are derived from measured geometry; the fact that a decal "
            "is derived does not make the wear it depicts historical.",
            "No visual acceptance is claimed. Nothing here has been seen in the editor.",
            "The performance figures are an arithmetic estimate, not a captured frame.",
        ],
        "geometrySources": {
            "architectureManifest": "SourceAssets/architecture-manifest.json",
            "architectureMeshCount": len(rows),
            "fxAnchors": "SourceAssets/fx-review/fx-materials.json",
            "coordinateConvention": "Unreal cm, +X east, +Y south, +Z up",
        },
        "ageTiers": AGE_TIERS,
        "routes": routes,
        "routeVertexProvenance": route_report,
        "categories": CATEGORIES,
        "budget": {
            "cap": BUDGET_CAP,
            "totalRequested": sum(c["requested"] for c in CATEGORIES),
            "allocatedAtCap": {c["id"]: n for c, n in zip(CATEGORIES, counts)},
            "allocatedTotal": int(sum(counts)),
            "allocator": "MikdashWear::AllocateBudget, mirrored here and pinned by "
                         "SurfaceWearMathTest.cpp BudgetChecks",
        },
        "perCategory": per_category,
        "decals": table,
        "decalCount": len(table),
        "textures": textures,
        "masterDecalMaterial": MASTER_DECAL,
        "decalInstances": DECAL_INSTANCES,
        "stoneVariation": {
            "note": "Per-instance colour and roughness jitter, applied as material "
                    "INSTANCES parented on the existing MI_PBR_* stone instances and set "
                    "as slot-0 component overrides. The shared parent M_PBR_Tiled is NEVER "
                    "edited: the gold instances hang off it, and the 2026-09-07 sanctuary "
                    "rebalance that flattened the frieze relief is why.",
            "quantisation": "A palette per family and age tier, indexed by a hash of the "
                            "component name. This is quantised variation, not literally "
                            "per-instance: 1155 ashlar components share 10 variants per tier.",
            "families": build_variant_palette(),
        },
        "protectedMaterials": PROTECTED_MATERIALS,
        "protectedMaterialPrefixes": PROTECTED_PREFIXES,
        "cppCrossCheck": cross_check_against_cpp(),
        "costEstimate": cost_estimate(table, counts),
        "limitations": [
            "Decal placement is geometric. Whether a decal lands on a surface that "
            "actually exists at that Z has not been traced; the release script records "
            "world bounds on readback but does not raycast.",
            "The wear textures are procedural fields, not scans of real stone.",
            "The stone variation palette is quantised, not continuous per instance.",
            "The footstep response is a decal, not a particle system: no Niagara "
            "dependency is added to MikdashRuntime.Build.cs.",
        ],
    }


def summarise(manifest: dict) -> str:
    lines = []
    lines.append("Mikdash surface wear -- %d decals authored, %d spawned at cap %d"
                 % (manifest["decalCount"], manifest["budget"]["allocatedTotal"],
                    manifest["budget"]["cap"]))
    lines.append("")
    lines.append("%-12s %9s %9s %9s   %s" % ("category", "generated", "authored", "at cap", "where"))
    where = {
        "footPolish": "gate mouths, stair landings, route centre lines",
        "stepNosing": "leading arris of every tread that carries traffic",
        "rainStreak": "wall below open string courses and cornices",
        "dustRunoff": "wall below sheltered ledges and window sills",
        "waterStain": "laver spouts, rinse tables, service passage fall",
        "soot": "altar upper course, ketores ceiling, menorah lamps",
        "lichen": "shaded lower courses of the old enclosure only",
        "windDust": "court corners and wall feet no route sweeps",
        "weathering": "old outer faces; none on the new inner court",
    }
    for category in CATEGORIES:
        stats = manifest["perCategory"][category["id"]]
        lines.append("%-12s %9d %9d %9d   %s"
                     % (category["id"], stats["generated"], stats["kept"],
                        stats["allocatedAtCap"], where[category["id"]]))
    lines.append("")
    lines.append("textures: %d, %.2f MB BC7 with mips (estimated)"
                 % (len(manifest["textures"]), manifest["costEstimate"]["textureVramMb"]))
    variants = sum(len(f["instances"]) for f in manifest["stoneVariation"]["families"])
    lines.append("meleke variants: %d material instances over %d families and %d age tiers"
                 % (variants, len(manifest["stoneVariation"]["families"]), len(AGE_TIERS)))
    return "\n".join(lines)


def _comparable(manifest: dict) -> dict:
    """Everything except fields that legitimately differ between two runs."""
    copy = dict(manifest)
    copy.pop("generatorSha256", None)
    copy.pop("cppCrossCheck", None)
    for texture in copy.get("textures", []):
        texture.pop("sizeBytes", None)
    return copy


def export() -> int:
    manifest = assemble(write=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(summarise(manifest))
    print("")
    print("wrote %s" % MANIFEST_PATH.relative_to(ROOT))
    for texture in manifest["textures"]:
        print("  %s  %s" % (texture["sha256"][:16], texture["file"]))
    return 0


def verify() -> int:
    if not MANIFEST_PATH.exists():
        print("FAIL: %s does not exist; run --export first" % MANIFEST_PATH)
        return 1
    stored = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    problems = []

    for texture in stored["textures"]:
        path = ROOT / texture["file"]
        if not path.exists():
            problems.append("missing texture " + texture["file"])
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != texture["sha256"]:
            problems.append("sha256 mismatch for %s: on disk %s, manifest %s"
                            % (texture["file"], digest[:16], texture["sha256"][:16]))
        if path.stat().st_size != texture["sizeBytes"]:
            problems.append("size mismatch for " + texture["file"])

    rebuilt = assemble(write=False)
    if json.dumps(_comparable(rebuilt), sort_keys=True) != json.dumps(_comparable(stored), sort_keys=True):
        # Narrow it down so the failure is actionable rather than "something differs".
        for key in sorted(set(_comparable(rebuilt)) | set(_comparable(stored))):
            a = json.dumps(_comparable(rebuilt).get(key), sort_keys=True)
            b = json.dumps(_comparable(stored).get(key), sort_keys=True)
            if a != b:
                problems.append("regenerated manifest differs from the stored one at '%s'" % key)

    for category in CATEGORIES:
        kept = len([d for d in stored["decals"] if d["category"] == category["id"]])
        if kept != category["requested"]:
            problems.append("category %s holds %d decals but the plan requests %d"
                            % (category["id"], kept, category["requested"]))

    cross = cross_check_against_cpp()
    if cross.get("available") and cross.get("mismatched"):
        problems.append("python mirror disagrees with the C++ test: %s" % cross["mismatched"])

    labels = [d["label"] for d in stored["decals"]]
    if len(set(labels)) != len(labels):
        problems.append("duplicate decal labels in the table")

    if problems:
        print("VERIFY FAILED")
        for problem in problems:
            print("  " + problem)
        return 1
    print(summarise(stored))
    print("")
    print("verify: %d textures hashed, %d decals re-derived, %d route vertices traced to "
          "measured features, C++ cross-check %s"
          % (len(stored["textures"]), len(stored["decals"]),
             len(stored["routeVertexProvenance"]),
             "compared %d values" % cross.get("compared", 0) if cross.get("available")
             else "skipped (tests.json absent)"))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--export", action="store_true", help="bake textures and write the manifest")
    parser.add_argument("--verify", action="store_true", help="re-check the frozen manifest and bytes")
    args = parser.parse_args(argv)
    if args.export and args.verify:
        print("Pass one of --export or --verify, not both.")
        return 2
    if args.export:
        return export()
    if args.verify:
        return verify()
    print(summarise(assemble(write=False)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
