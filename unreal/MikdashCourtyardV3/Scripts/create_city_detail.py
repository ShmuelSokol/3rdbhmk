"""CityDetailV1 - procedural Jerusalem roofscape, parapets, quarter domes and souq fittings.

AUTHORED_OFFLINE_SOURCE - this module never imports `unreal`, never touches Content/, never
opens a map. It writes twelve small unit OBJs, an instance plan and a plan-view PNG under
SourceAssets/context-review/CityDetailV1/. Scripts/release_city_detail.py is the separate
guarded native importer/placer, which puts every row of the plan into a
HierarchicalInstancedStaticMeshComponent.

WHY
---
The imported Jerusalem context is 11,437 OSM footprints extruded as flat-topped prisms.
From the Mount, from the plaza and from the air the city therefore reads as brown cardboard
boxes: no roof depth, no roof plant, no silhouette. Measured slot counts (lighting-v3
inventory 20260908T183719554035Z): M_Context_Building 1,600 slots, M_Context_Asphalt 1,667,
M_Context_StonePath 1,141, M_Context_Terrain 256. The 2,106 authored facade shells of
OldCityFacadesV1 fix the *walls* of a fifth of the walled city and nothing else.

The roof is the largest surface a visitor ever sees of the modern city, and in Jerusalem it
is the most characteristic one. This module adds, by rule, on the footprints that are
already in the level:

  * ROOF PARAPETS on the outer edge of every large enough roof, so a roof has a rim, an
    inside, and a shadow instead of being a lid;
  * ROOF PLANT - the black solar water heater (dud shemesh: horizontal tank plus tilted
    south-facing collector), the vertical black water tank, split air-conditioning
    condensers, satellite dishes, TV aerials, washing lines and stair houses;
  * SMALL STONE DOMES over the roofs inside the Ottoman wall ring, which is the signature
    of the Muslim and Christian quarters;
  * SOUQ FITTINGS - cross-street barrel vaults, wall awnings and market stalls along the
    narrow mapped streets inside the walls.

Everything is placed as instances of twelve unit meshes, so the whole addition is twelve
StaticMesh assets and twenty-four actors, not 11,437 buildings re-modelled. See the
`budget` block of the manifest for the measured instance and triangle counts against
PERFORMANCE-BUDGET.md.

SOURCED VERSUS AUTHORED
-----------------------
Two facts here are sourced and are the reason the scene should look like this:

  1. THE STONE. Jerusalem has required stone facing on every building since the 1918
     Jerusalem town-planning ordinance issued under Ronald Storrs as military governor,
     carried into the British Mandate planning schemes and re-enacted in Israeli municipal
     building law; it is still enforced by the Jerusalem municipality today. The city is
     therefore faced in the same pale local limestone family (meleke / mizzi) as the
     Herodian ashlar of the Temple Mount retaining walls - it is not brown, and it is not a
     different stone from the Mikdash. `materials` below puts the new geometry on pale
     limestone tints rather than on the brown default, and `RETINT` records the optional,
     switchable component-override that does the same for the extruded prisms themselves.
  2. THE ROOF TANKS. Solar water heating is effectively universal on Israeli housing: it
     has been mandatory in new residential construction since a 1980 amendment to the
     planning and building regulations, and Israel's own reporting puts household coverage
     at roughly 85 per cent. A Jerusalem roof with no black tank and no collector panel is
     the unusual case, not the normal one. `SOLAR_SHARE` is set from that.

Everything else - the exact tank position on a given roof, which roof carries a dish, which
roof carries a dome, where an awning hangs - is AUTHORED massing in the style of the modern
city. None of it is surveyed, photogrammetric or a claim about a particular building, and
none of it is halachic.

FOOTPRINT SOURCE AND PARITY
---------------------------
This module imports Scripts/create_oldcity_facades.py and reuses its CitySource, which is a
verified re-implementation of the TypeScript `buildJerusalem()` building pass. That module's
`verify_against_frozen_manifest()` proves the reconstructed boxes are the boxes already in
the level (>= 90 per cent exact component matches against the frozen buildings-manifest.json
for FBX 271bc9b4e129). This module runs the same check and refuses if it fails, so a plan is
never authored against an unproven footprint set. The alignment constants, the 100 m cell
naming and the OBJ adapter all come from that module too, so nothing is applied twice.

COEXISTENCE WITH THE OTHER TWO JOBS IN THIS WAVE
------------------------------------------------
  * The anti-repeat material job owns /Game/MikdashV3/MaterialReview/AntiRepeatV1/, the
    shared M_PBR_Tiled parent and the nine Nanite-repaired MI_PBR_* instances. Nothing here
    reads, writes or parents on any of those. Every material this job creates is a
    MaterialInstanceConstant under CityDetailV1 whose parent is M_Context_Building, so if
    that job improves the context graph this job inherits it instead of fighting it.
  * The Yechezkel precinct plaza job hides whole 100 m building actors when the precinct is
    shown (policy hide_if_any_inside, 270 actors, recorded in
    SourceAssets/enclosure-review/precinct-Candidate48.json). Every instance here is
    therefore tagged with the zone of the actor it decorates - `kept` or `precinct` - and the
    release script puts the two zones in SEPARATE actors, so hiding the precinct's buildings
    can hide their roof detail with them and nothing is left floating over a plaza.
  * OldCityFacadesV1 already authored parapets, one dome, one tank and one stair head on
    2,106 buildings. This module re-evaluates that module's own hash predicates for those
    buildings and suppresses the duplicates rather than stacking on top of them.

OBJ ADAPTER CONVENTION (project standard)
-----------------------------------------
Canonical vertices are UE cm (X east, Y south, Z up). Every OBJ is written through
create_oldcity_facades.write_obj, i.e. Y REFLECTED and triangle winding REVERSED, one `o`
object and no `g` groups so the importer creates exactly one material slot. Solids are
closed and flipped to a POSITIVE canonical signed volume. Unlike the facade batches these
meshes sit at the origin, so the release script's bounds round-trip can only prove the
reflection on the meshes that are ASYMMETRIC IN Y; `yAsymmetricCm` per mesh records which
ones carry that test, and the manifest refuses if fewer than six do.

Usage (no engine needed):
    "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe" \
        Scripts/create_city_detail.py [--force] [--no-preview]
"""

import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
sys.path.insert(0, str(ROOT / 'Scripts'))

import create_oldcity_facades as F                                    # noqa: E402

OUT = ROOT / 'SourceAssets' / 'context-review' / 'CityDetailV1'
OBJ_DIR = OUT / 'obj'
MANIFEST_PATH = OUT / 'city-detail-manifest.json'
PLAN_PATH = OUT / 'city-detail-plan.json'
PREVIEW_PATH = OUT / 'preview-plan.png'

FACADES_MANIFEST = F.MANIFEST_PATH
PRECINCT_JSON = ROOT / 'SourceAssets' / 'enclosure-review' / 'precinct-Candidate48.json'

STATUS = 'AUTHORED_OFFLINE_SOURCE_NATIVE_IMPORT_PENDING'
VERSION = 1

# --------------------------------------------------------------------- rules
# Roof plant. SOLAR_SHARE is the one placement probability with a source behind it
# (see the module docstring); the rest are authored dressing weights.
SOLAR_SHARE = 0.82                  # share of ordinary roofs carrying a solar water heater
MIN_CLUTTER_AREA_M2 = 22.0          # below this a roof gets nothing but its parapet
CLUTTER_AREA_PER_ITEM_M2 = 56.0
MAX_CLUTTER_PER_ROOF = 5
CLUTTER_EDGE_INSET_CM = 130.0       # keep plant clear of the parapet line
CLUTTER_MIN_SEPARATION_CM = 165.0
CLUTTER_SAMPLE_TRIES = 40
FACADE_CENTRE_KEEPOUT_CM = 260.0    # OldCityFacadesV1 puts its own tank/stair head here

# Weights for the secondary items, evaluated after the solar heater decision.
SECONDARY_WEIGHTS = (
    ('water_tank', 0.16),
    ('aircon', 0.28),
    ('satdish', 0.24),
    ('aerial', 0.13),
    ('washline', 0.14),
    ('water_tank2', 0.05),
)

# Parapets.
PARAPET_MIN_AREA_M2 = 42.0
PARAPET_MIN_EDGE_CM = 300.0
PARAPET_COLLINEAR_DEGREES = 5.0
PARAPET_HEIGHT_CM = (62.0, 108.0)
PARAPET_THICKNESS_CM = (22.0, 30.0)
PARAPET_SINK_CM = 6.0               # base buried in the roof slab so no coplanar face

# Domes inside the Ottoman wall ring.
DOME_SHARE = 0.50
DOME_MIN_INRADIUS_CM = 235.0
DOME_MAX_PER_ROOF = 3
DOME_RADIUS_CM = (110.0, 205.0)

# Stair houses (a roof stair enclosure, the other thing that breaks an Old City skyline).
STAIRHEAD_SHARE = 0.24
STAIRHEAD_MIN_AREA_M2 = 70.0

# Souq fittings along the mapped streets inside the walls.
SOUQ_STATION_CM = 420.0             # spacing of candidate stations along a street
SOUQ_PROBE_MAX_CM = 900.0           # widest gap still treated as an alley
SOUQ_ARCH_MAX_CM = 620.0            # a vault only spans a genuinely narrow alley
SOUQ_ARCH_SHARE = 0.20
SOUQ_AWNING_SHARE = 0.34
SOUQ_STALL_SHARE = 0.22
SOUQ_ARCH_SPRING_CM = 250.0         # springing height above the alley floor
SOUQ_ARCH_RISE_FRACTION = (0.46, 0.60)   # rise as a fraction of the span: round, not stilted
SOUQ_AWNING_HEIGHT_CM = 265.0

BUDGET_MAX_INSTANCES = 130000
BUDGET_MAX_TRIANGLES = 4_300_000
BATCH_ROWS = 3500

PREVIEW_PX = 1700


# ===================================================================== helpers
def sha256_of(path):
    return F.sha256_of(path)


def hash01(*values):
    """Deterministic 0..1 from any key, independent of PYTHONHASHSEED."""
    digest = hashlib.sha256(('|'.join('%.6f' % float(v) if isinstance(v, (int, float)) else str(v)
                                      for v in values)).encode('ascii')).digest()
    return int.from_bytes(digest[:6], 'big') / float(1 << 48)


def lerp(a, b, t):
    return a + (b - a) * t


def pick_weighted(u, weights):
    total = sum(weight for _, weight in weights)
    cursor = 0.0
    for key, weight in weights:
        cursor += weight / total
        if u <= cursor:
            return key
    return weights[-1][0]


# =================================================================== geometry
def transform_solid(solid, translate=(0.0, 0.0, 0.0), pitch=0.0, yaw=0.0):
    """Rotate about +Y (pitch, right-handed in the canonical frame) then +Z, then move."""
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    out = []
    for x, y, z in solid.vertices:
        x1, z1 = x * cp - z * sp, x * sp + z * cp
        x2, y2 = x1 * cy - y * sy, x1 * sy + y * cy
        out.append((x2 + translate[0], y2 + translate[1], z1 + translate[2]))
    solid.vertices = out
    solid.orient()
    return solid


def cylinder_x(x0, x1, cy, cz, radius, sides=8):
    """Closed cylinder whose axis runs east-west; a tank lying on its side."""
    solid = F.Solid()
    ring = [(cy + radius * math.cos(2.0 * math.pi * i / sides),
             cz + radius * math.sin(2.0 * math.pi * i / sides)) for i in range(sides)]
    west = [solid.add((x0, y, z)) for y, z in ring]
    east = [solid.add((x1, y, z)) for y, z in ring]
    for index in range(sides):
        nxt = (index + 1) % sides
        solid.quad(west[index], west[nxt], east[nxt], east[index])
    solid.fan(east)
    solid.fan(west[::-1])
    solid.orient()
    return solid


def slab_from_quad(corners, thickness):
    """Closed slab under a planar quad given in order; thickness runs along -normal."""
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = corners[0], corners[1], corners[2]
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    nx, ny, nz = nx / length * thickness, ny / length * thickness, nz / length * thickness
    solid = F.Solid()
    top = [solid.add(point) for point in corners]
    bottom = [solid.add((p[0] - nx, p[1] - ny, p[2] - nz)) for p in corners]
    for index in range(4):
        nxt = (index + 1) % 4
        solid.quad(top[index], top[nxt], bottom[nxt], bottom[index])
    solid.fan(top)
    solid.fan(bottom[::-1])
    solid.orient()
    return solid


def arch_vault(x_half, z_spring, z_crown, thickness, y0, y1, segments=6):
    """Barrel vault spanning east-west, extruded north-south. Springs from two piers."""
    rise = z_crown - z_spring
    outer, inner = [], []
    for step in range(segments + 1):
        angle = math.pi * step / segments
        outer.append((-x_half * math.cos(angle), z_spring + rise * math.sin(angle)))
        inner.append((-(x_half - thickness) * math.cos(angle),
                      z_spring + (rise - thickness) * math.sin(angle)))
    solid = F.Solid()
    o0 = [solid.add((x, y0, z)) for x, z in outer]
    o1 = [solid.add((x, y1, z)) for x, z in outer]
    i0 = [solid.add((x, y0, z)) for x, z in inner]
    i1 = [solid.add((x, y1, z)) for x, z in inner]
    count = len(outer)
    for index in range(count - 1):
        solid.quad(o0[index], o0[index + 1], o1[index + 1], o1[index])       # extrados
        solid.quad(i0[index + 1], i0[index], i1[index], i1[index + 1])       # intrados
        solid.quad(o0[index + 1], o0[index], i0[index], i0[index + 1])       # near face
        solid.quad(o1[index], o1[index + 1], i1[index + 1], i1[index])       # far face
    for a, b in ((o0[0], i0[0]), (o0[-1], i0[-1])):
        pass
    # Two flat end caps closing the springing.
    solid.quad(o0[0], i0[0], i1[0], o1[0])
    solid.quad(i0[-1], o0[-1], o1[-1], i1[-1])
    solid.orient()
    return solid


# ============================================================== the unit meshes
def mesh_parapet():
    """Unit rail: 100 cm of run along +X, 20 cm thick, 100 cm tall, with a coping ledge."""
    return [F.oriented_box(0.0, 0.0, 0.0, 86.0, 50.0, 10.0, 0.0),
            F.oriented_box(0.0, 0.0, 86.0, 100.0, 50.0, 14.0, 0.0)]


def mesh_solar_tank():
    """Dud shemesh: horizontal tank on legs, north, with the collector sloping to the south.

    Jerusalem is 31.8 N, so a flat-plate collector faces south: its high edge is on the
    north side (canonical -Y) and it falls toward the south (+Y). Strongly Y-asymmetric,
    which is what gives the release script's bounds check its reflection test.
    """
    solids = [cylinder_x(-70.0, 70.0, -130.0, 118.0, 29.0, 8),
              F.oriented_box(-58.0, -130.0, 0.0, 90.0, 7.0, 7.0, 0.0),
              F.oriented_box(58.0, -130.0, 0.0, 90.0, 7.0, 7.0, 0.0),
              slab_from_quad([(-100.0, -100.0, 95.0), (100.0, -100.0, 95.0),
                              (100.0, 62.0, 9.0), (-100.0, 62.0, 9.0)], 9.0)]
    return solids


def mesh_water_tank():
    """Vertical black polyethylene roof tank on a low stand."""
    return [F.cylinder_solid(0.0, 0.0, 0.0, 122.0, 46.0, 10),
            F.cylinder_solid(0.0, 0.0, 122.0, 132.0, 26.0, 8)]


def mesh_aircon():
    """Split-unit condenser on a wall bracket that cantilevers to the north."""
    return [F.oriented_box(0.0, 0.0, 24.0, 86.0, 42.0, 20.0, 0.0),
            F.cylinder_solid(0.0, -21.0, 84.0, 90.0, 26.0, 8),
            F.oriented_box(0.0, 22.0, 0.0, 26.0, 40.0, 6.0, 0.0)]


def mesh_satdish():
    """Post, tilted offset dish and a feed arm reaching south."""
    dish = F.cylinder_solid(0.0, 0.0, -5.0, 5.0, 52.0, 8)
    transform_solid(dish, translate=(0.0, -18.0, 128.0), pitch=math.radians(62.0))
    return [F.oriented_box(0.0, 0.0, 0.0, 120.0, 8.0, 8.0, 0.0),
            F.oriented_box(0.0, 0.0, 0.0, 12.0, 26.0, 26.0, 0.0),
            dish,
            F.oriented_box(0.0, 42.0, 96.0, 106.0, 6.0, 46.0, 0.0)]


def mesh_aerial():
    """Mast with three crossbars and one offset reflector element."""
    return [F.oriented_box(0.0, 0.0, 0.0, 300.0, 7.0, 7.0, 0.0),
            F.oriented_box(0.0, 0.0, 0.0, 18.0, 30.0, 30.0, 0.0),
            F.oriented_box(0.0, 0.0, 224.0, 232.0, 4.0, 78.0, 0.0),
            F.oriented_box(0.0, -34.0, 278.0, 286.0, 4.0, 46.0, 0.0)]


def mesh_washline():
    """Two posts and three hanging cloths of different drops."""
    solids = [F.oriented_box(-150.0, 0.0, 0.0, 175.0, 7.0, 7.0, 0.0),
              F.oriented_box(150.0, 0.0, 0.0, 175.0, 7.0, 7.0, 0.0),
              F.oriented_box(0.0, 0.0, 170.0, 175.0, 152.0, 3.0, 0.0)]
    for offset, drop, half in ((-78.0, 82.0, 30.0), (62.0, 104.0, 36.0)):
        solids.append(F.oriented_box(offset, 0.0, 170.0 - drop, 170.0, half, 2.5, 0.0))
    return solids


def mesh_stairhead():
    """Roof stair house: a small block with a flat slab overhanging to the south."""
    return [F.oriented_box(0.0, 0.0, 0.0, 228.0, 105.0, 82.0, 0.0),
            F.oriented_box(0.0, 34.0, 228.0, 248.0, 118.0, 112.0, 0.0),
            F.oriented_box(0.0, -105.0, 190.0, 226.0, 34.0, 8.0, 0.0)]


def mesh_dome():
    """Small plastered stone dome on a low drum, 100 cm nominal radius."""
    return [F.dome_solid(0.0, 0.0, 0.0, 100.0, 34.0, rings=3, sides=10)]


def mesh_awning():
    """Shop awning cantilevered south from a wall plane at y = 0."""
    canopy = slab_from_quad([(-110.0, 6.0, 40.0), (110.0, 6.0, 40.0),
                             (110.0, 150.0, 0.0), (-110.0, 150.0, 0.0)], 7.0)
    return [canopy,
            F.oriented_box(-104.0, 78.0, -6.0, 40.0, 5.0, 78.0, 0.0),
            F.oriented_box(104.0, 78.0, -6.0, 40.0, 5.0, 78.0, 0.0),
            F.oriented_box(0.0, 150.0, -34.0, 4.0, 110.0, 5.0, 0.0)]


def mesh_arch():
    """Cross-street barrel vault: 100 cm nominal span, 200 cm nominal depth, 100 cm rise."""
    return [arch_vault(50.0, 0.0, 100.0, 9.0, -100.0, 100.0, segments=7)]


def mesh_stall():
    """Souq stall: trestle, stacked goods and a low canvas over it."""
    return [F.oriented_box(0.0, 0.0, 62.0, 76.0, 108.0, 52.0, 0.0),
            F.oriented_box(0.0, 0.0, 0.0, 62.0, 96.0, 44.0, 0.0),
            F.oriented_box(-42.0, -8.0, 76.0, 118.0, 44.0, 34.0, 0.0),
            F.oriented_box(50.0, 6.0, 76.0, 104.0, 34.0, 30.0, 0.0),
            slab_from_quad([(-120.0, -70.0, 214.0), (120.0, -70.0, 214.0),
                            (120.0, 78.0, 196.0), (-120.0, 78.0, 196.0)], 6.0),
            F.oriented_box(-114.0, 70.0, 0.0, 196.0, 5.0, 5.0, 0.0),
            F.oriented_box(114.0, 70.0, 0.0, 196.0, 5.0, 5.0, 0.0)]


# key, asset name, builder, material key, cast shadow, cull distance cm, what it is
MESHES = [
    ('parapet', 'SM_CityDetail_Parapet', mesh_parapet, 'meleke', True, 140000.0,
     'roof parapet rail, 100 cm unit run scaled to each footprint edge'),
    ('solar', 'SM_CityDetail_SolarTank', mesh_solar_tank, 'darkplant', True, 62000.0,
     'solar water heater: horizontal tank plus south-facing collector'),
    ('water_tank', 'SM_CityDetail_WaterTank', mesh_water_tank, 'darkplant', True, 52000.0,
     'vertical black roof water tank on a stand'),
    ('aircon', 'SM_CityDetail_AirCon', mesh_aircon, 'metal', True, 40000.0,
     'split air-conditioning condenser on a bracket'),
    ('satdish', 'SM_CityDetail_SatDish', mesh_satdish, 'metal', False, 34000.0,
     'satellite dish on a roof post'),
    ('aerial', 'SM_CityDetail_Aerial', mesh_aerial, 'metal', False, 34000.0,
     'television aerial mast'),
    ('washline', 'SM_CityDetail_WashLine', mesh_washline, 'laundry', False, 30000.0,
     'washing line with hanging cloths'),
    ('stairhead', 'SM_CityDetail_StairHead', mesh_stairhead, 'meleke', True, 90000.0,
     'roof stair house with an overhanging slab'),
    ('dome', 'SM_CityDetail_Dome', mesh_dome, 'meleke', True, 160000.0,
     'small stone quarter dome on a low drum, 100 cm nominal radius'),
    ('awning', 'SM_CityDetail_Awning', mesh_awning, 'canvas', False, 22000.0,
     'shop awning cantilevered from a street wall'),
    ('arch', 'SM_CityDetail_Arch', mesh_arch, 'meleke', True, 45000.0,
     'cross-street barrel vault, 100 cm nominal span and 100 cm nominal rise; per-instance scale sets the real span, depth and rise, so the ring thickness scales with the span'),
    ('stall', 'SM_CityDetail_Stall', mesh_stall, 'canvas', False, 22000.0,
     'souq market stall with a canvas over it'),
]

# Every material below is a MaterialInstanceConstant the release script creates under
# CityDetailV1 with M_Context_Building as its parent. That parent is the context triplanar
# limestone already on the 1,499 building meshes, so the new geometry is in the same stone
# family as the city and as the Herodian ashlar; the tints move it to the pale meleke read
# the 1918 ordinance produces, and RoofFlatten is turned down so a tank is not lightened
# toward a roof colour just because its top faces up.
MATERIALS = {
    'meleke': {
        'name': 'MI_CityDetail_Meleke',
        'why': 'pale dressed Jerusalem limestone for parapets, domes, stair houses and vaults',
        'vector': {'Tint0': [1.22, 1.18, 1.08], 'Tint1': [1.16, 1.11, 1.00],
                   'Tint2': [1.27, 1.22, 1.11], 'Tint3': [1.19, 1.14, 1.03],
                   'RoofTint': [1.10, 1.07, 0.99]},
        'scalar': {'TileCm': 150.0, 'RoughVar': 0.10, 'VCInfluence': 0.0,
                   'HashVertexColorWeight': 0.0, 'HashObjectWeight': 1.0,
                   'RoofFlatten': 0.25},
    },
    'darkplant': {
        'name': 'MI_CityDetail_DarkPlant',
        'why': 'black solar tank, collector glazing and polyethylene water tank',
        'vector': {'Tint0': [0.10, 0.10, 0.11], 'Tint1': [0.08, 0.08, 0.09],
                   'Tint2': [0.13, 0.13, 0.14], 'Tint3': [0.09, 0.10, 0.12],
                   'RoofTint': [0.11, 0.11, 0.13]},
        'scalar': {'TileCm': 70.0, 'RoughVar': 0.03, 'VCInfluence': 0.0,
                   'HashVertexColorWeight': 0.0, 'HashObjectWeight': 1.0,
                   'RoofFlatten': 0.0},
    },
    'metal': {
        'name': 'MI_CityDetail_Metal',
        'why': 'galvanised and painted metal: condensers, dishes, aerials',
        'vector': {'Tint0': [0.66, 0.67, 0.69], 'Tint1': [0.60, 0.61, 0.63],
                   'Tint2': [0.72, 0.73, 0.75], 'Tint3': [0.63, 0.64, 0.67],
                   'RoofTint': [0.70, 0.71, 0.73]},
        'scalar': {'TileCm': 90.0, 'RoughVar': 0.05, 'VCInfluence': 0.0,
                   'HashVertexColorWeight': 0.0, 'HashObjectWeight': 1.0,
                   'RoofFlatten': 0.0},
    },
    'laundry': {
        'name': 'MI_CityDetail_Laundry',
        'why': 'washing on a line: bright cloth against the stone',
        'vector': {'Tint0': [1.35, 1.33, 1.28], 'Tint1': [1.10, 1.16, 1.30],
                   'Tint2': [1.30, 1.14, 1.06], 'Tint3': [1.18, 1.26, 1.14],
                   'RoofTint': [1.30, 1.28, 1.24]},
        'scalar': {'TileCm': 60.0, 'RoughVar': 0.12, 'VCInfluence': 0.0,
                   'HashVertexColorWeight': 0.0, 'HashObjectWeight': 1.0,
                   'RoofFlatten': 0.0},
    },
    'canvas': {
        'name': 'MI_CityDetail_Canvas',
        'why': 'souq awning and stall canvas',
        'vector': {'Tint0': [1.16, 1.08, 0.92], 'Tint1': [1.02, 0.96, 0.84],
                   'Tint2': [1.10, 1.00, 0.86], 'Tint3': [0.96, 0.94, 0.88],
                   'RoofTint': [1.12, 1.05, 0.92]},
        'scalar': {'TileCm': 110.0, 'RoughVar': 0.10, 'VCInfluence': 0.0,
                   'HashVertexColorWeight': 0.0, 'HashObjectWeight': 1.0,
                   'RoofFlatten': 0.1},
    },
}

# The optional, switchable retint of the extruded prisms themselves. The release script only
# applies this under -CityDetailRetint, as a per-COMPONENT material override on the building
# actors, so the shared M_Context_Building asset and the 1,499 mesh assets are never edited
# and the change is reversible by clearing overrides.
RETINT = {
    'name': 'MI_CityDetail_CityStone',
    'parentIsContextBuilding': True,
    'why': ('Every building in Jerusalem has been required to be faced in local stone since '
            'the 1918 Jerusalem town-planning ordinance under the military governor Ronald '
            'Storrs, carried into the Mandate planning schemes and still enforced by the '
            'municipality. The city should therefore read as the same pale meleke family as '
            'the Temple ashlar, and its flat roofs as pale concrete and whitewash, not as '
            'the brown default the aerial frame shows.'),
    'vector': {'Tint0': [1.20, 1.16, 1.07], 'Tint1': [1.12, 1.06, 0.96],
               'Tint2': [1.26, 1.21, 1.10], 'Tint3': [1.16, 1.12, 1.02],
               'RoofTint': [0.94, 0.93, 0.89]},
    'scalar': {'TileCm': 420.0, 'RoughVar': 0.14, 'RoofFlatten': 0.72,
               'VCInfluence': 0.5, 'HashVertexColorWeight': 1.0, 'HashObjectWeight': 1.0},
    'appliesToActorPrefix': 'SM_JerusalemBuildings_',
}


# ============================================================ source assembly
def load_city():
    data = json.loads(F.SOURCE_JSON.read_text(encoding='utf-8-sig'))
    source = F.CitySource(data)
    records, skipped = source.buildings()
    verification = F.verify_against_frozen_manifest(records)
    return source, records, skipped, verification


def load_facade_state(records_by_id):
    """Which buildings OldCityFacadesV1 already decorated, and with what.

    The facades manifest lists the osmIds it authored but not which of them got a dome,
    tank or stair head, so those three hash predicates are re-evaluated here exactly as
    create_oldcity_facades.build_building_detail evaluates them. Anything this returns True
    for is suppressed below rather than stacked on.
    """
    manifest = json.loads(FACADES_MANIFEST.read_text(encoding='utf-8-sig'))
    ids = set()
    for batch in manifest['batches']:
        entry = batch.get('facades')
        if entry:
            for building in entry.get('perBuilding', []):
                ids.add(int(building['osmId']))
    state = {}
    for osm_id in ids:
        record = records_by_id.get(osm_id)
        if record is None:
            continue
        inradius = record['inradiusCm']
        dome = F.js_hash(osm_id * 7.0 + 11.0) < F.DOME_FRACTION
        tank = (not dome) and F.js_hash(osm_id * 13.0 + 3.0) < F.TANK_FRACTION
        stair = F.js_hash(osm_id * 17.0 + 29.0) < F.STAIRHEAD_FRACTION
        if inradius < 250.0:
            dome = tank = stair = False
        state[osm_id] = {'dome': dome, 'tank': tank, 'stairHead': stair}
    return state, manifest['status'], sha256_of(FACADES_MANIFEST)


def load_precinct_hidden_cells():
    """The 100 m cells the Yechezkel precinct plaza hides, from the precinct receipt."""
    data = json.loads(PRECINCT_JSON.read_text(encoding='utf-8-sig'))
    hide = data['modernCity']['hideSet']
    cells, large = set(), set()
    for label in hide['labels']:
        if not label.startswith('SM_JerusalemBuildings_'):
            continue
        token = label[len('SM_JerusalemBuildings_'):]
        (cells if token.startswith('Grid_') else large).add(token)
    return {
        'policy': hide['policy'],
        'rule': hide['rule'],
        'cells': cells,
        'largeGroups': large,
        'source': str(PRECINCT_JSON),
        'sha256': sha256_of(PRECINCT_JSON),
        'squareOuterFacesCm': data['square']['outerFacesCm'],
    }


def component_groups(records):
    """osmId -> the level actor group (Grid_* or Large_*) that draws that footprint."""
    frozen = json.loads(F.FROZEN_MANIFEST.read_text(encoding='utf-8-sig'))
    index = {}
    for component in frozen['components']:
        box = component['sourceBoundsAmos']
        key = (round(box['min'][0], 1), round(box['min'][2], 1),
               round(box['max'][0], 1), round(box['max'][2], 1))
        index.setdefault(key, []).append(component)
    groups, unmatched = {}, 0
    for record in records:
        xs = [p[0] for p in record['points']]
        zs = [p[1] for p in record['points']]
        key = (round(min(xs), 1), round(min(zs), 1), round(max(xs), 1), round(max(zs), 1))
        hits = index.get(key)
        if hits:
            groups[record['id']] = hits[0]['assignedGroup']
        else:
            unmatched += 1
    return groups, unmatched


def prepare_records(records):
    """Canonical UE-cm view of every extruded footprint, with the facts the rules need."""
    prepared = []
    for record in records:
        loop = F.ensure_ccw(F.dedupe_ring([F.ue_xy(x, z) for x, z in record['points']]))
        if len(loop) < 3:
            continue
        area_cm2 = abs(F.polygon_area(loop))
        xs = [p[0] for p in loop]
        ys = [p[1] for p in loop]
        centre = (sum(xs) / len(xs), sum(ys) / len(ys))
        prepared.append({
            'id': int(record['id']),
            'name': record['name'],
            'loopCm': loop,
            'boxCm': (min(xs), min(ys), max(xs), max(ys)),
            'centreCm': centre,
            'areaCm2': area_cm2,
            'areaM2': area_cm2 / 10000.0,
            'inradiusCm': F.approximate_inradius(loop, centre[0], centre[1]),
            'baseZ': F.ue_z(record['base']),
            'roofZ': F.ue_z(record['base'] + record['height']),
            'cell': F.cell_name(F.cell_key_of(centre[0], centre[1])),
        })
    return prepared


# ======================================================================= rules
def merged_edges(loop):
    """Footprint edges with near-collinear runs merged, so a parapet is one instance."""
    count = len(loop)
    directions = []
    for index in range(count):
        a, b = loop[index], loop[(index + 1) % count]
        directions.append(math.atan2(b[1] - a[1], b[0] - a[0]))
    limit = math.radians(PARAPET_COLLINEAR_DEGREES)
    start = 0
    for index in range(count):
        previous = (index - 1) % count
        delta = abs((directions[index] - directions[previous] + math.pi) % (2.0 * math.pi) - math.pi)
        if delta > limit:
            start = index
            break
    edges = []
    index = start
    for _ in range(count):
        nxt = (index + 1) % count
        run_end = nxt
        while run_end != start:
            delta = abs((directions[run_end] - directions[index] + math.pi) % (2.0 * math.pi) - math.pi)
            if delta > limit:
                break
            run_end = (run_end + 1) % count
        a, b = loop[index], loop[run_end]
        edges.append((a, b))
        if run_end == start:
            break
        index = run_end
    return edges


def roof_points(record, count, keepout_centre_cm, seed_tag):
    """Deterministic scattered points on a roof, inset from the edge and mutually clear."""
    loop = record['loopCm']
    minx, miny, maxx, maxy = record['boxCm']
    inset = CLUTTER_EDGE_INSET_CM
    chosen = []
    tries = 0
    attempt = 0
    while len(chosen) < count and attempt < CLUTTER_SAMPLE_TRIES * max(1, count):
        attempt += 1
        u = hash01(seed_tag, record['id'], attempt, 'x')
        v = hash01(seed_tag, record['id'], attempt, 'y')
        x = lerp(minx, maxx, u)
        y = lerp(miny, maxy, v)
        if not F.point_in_polygon(x, y, loop):
            continue
        near = min(F.point_segment_distance(x, y, loop[i][0], loop[i][1],
                                            loop[(i + 1) % len(loop)][0], loop[(i + 1) % len(loop)][1])
                   for i in range(len(loop)))
        if near < inset:
            continue
        if keepout_centre_cm and math.hypot(x - record['centreCm'][0],
                                            y - record['centreCm'][1]) < keepout_centre_cm:
            continue
        if any(math.hypot(x - px, y - py) < CLUTTER_MIN_SEPARATION_CM for px, py in chosen):
            continue
        chosen.append((x, y))
        tries += attempt
    return chosen


def plan_parapets(record, facade_state, rows):
    if record['areaM2'] < PARAPET_MIN_AREA_M2:
        return 0
    if record['id'] in facade_state:
        return 0                       # OldCityFacadesV1 already crowned this roof
    added = 0
    for a, b in merged_edges(record['loopCm']):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length < PARAPET_MIN_EDGE_CM:
            continue
        u = hash01('parapet', record['id'], a[0], a[1])
        height = lerp(PARAPET_HEIGHT_CM[0], PARAPET_HEIGHT_CM[1], u)
        thickness = lerp(PARAPET_THICKNESS_CM[0], PARAPET_THICKNESS_CM[1],
                         hash01('parapetT', record['id'], a[0]))
        yaw = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        rows.append(('parapet', record, [
            (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0, record['roofZ'] - PARAPET_SINK_CM,
            yaw, 0.0, 0.0,
            length / 100.0, thickness / 20.0, (height + PARAPET_SINK_CM) / 100.0]))
        added += 1
    return added


def plan_roof_plant(record, facade_state, rows):
    """Solar heaters first (the sourced one), then the authored secondary dressing."""
    if record['areaM2'] < MIN_CLUTTER_AREA_M2 or record['inradiusCm'] < CLUTTER_EDGE_INSET_CM + 40.0:
        return 0
    state = facade_state.get(record['id'])
    keepout = FACADE_CENTRE_KEEPOUT_CM if state else 0.0
    budget = max(1, min(MAX_CLUTTER_PER_ROOF,
                        int(round(record['areaM2'] / CLUTTER_AREA_PER_ITEM_M2))))
    wants_solar = hash01('solar', record['id']) < SOLAR_SHARE
    wants_stair = (not (state and state['stairHead'])
                   and record['areaM2'] >= STAIRHEAD_MIN_AREA_M2
                   and hash01('stair', record['id']) < STAIRHEAD_SHARE)
    slots = budget + (1 if wants_stair else 0)
    points = roof_points(record, slots, keepout, 'plant')
    if not points:
        return 0
    added = 0
    for index, (x, y) in enumerate(points):
        if index == 0 and wants_stair:
            key = 'stairhead'
        elif (index == (1 if wants_stair else 0)) and wants_solar:
            key = 'solar'
        else:
            secondary = pick_weighted(hash01('sec', record['id'], index), SECONDARY_WEIGHTS)
            key = 'water_tank' if secondary == 'water_tank2' else secondary
            if key == 'water_tank' and state and state['tank'] and index < 2:
                key = 'aircon'
        yaw = hash01('yaw', record['id'], index) * 360.0
        if key == 'solar':
            yaw = lerp(-24.0, 24.0, hash01('solaryaw', record['id'], index))
        scale = lerp(0.88, 1.14, hash01('scale', record['id'], index))
        rows.append((key, record, [x, y, record['roofZ'], yaw, 0.0, 0.0, scale, scale, scale]))
        added += 1
    return added


def plan_domes(record, inside_walls, facade_state, rows):
    if not inside_walls or record['inradiusCm'] < DOME_MIN_INRADIUS_CM:
        return 0
    state = facade_state.get(record['id'])
    if state and state['dome']:
        return 0
    if hash01('dome', record['id']) >= DOME_SHARE:
        return 0
    count = 1 + int(hash01('domeN', record['id']) * DOME_MAX_PER_ROOF)
    count = min(count, DOME_MAX_PER_ROOF)
    points = roof_points(record, count, 0.0, 'dome')
    added = 0
    for index, (x, y) in enumerate(points):
        radius = lerp(DOME_RADIUS_CM[0], DOME_RADIUS_CM[1], hash01('domeR', record['id'], index))
        radius = min(radius, max(DOME_RADIUS_CM[0], record['inradiusCm'] * 0.45))
        scale = radius / 100.0
        rows.append(('dome', record, [x, y, record['roofZ'] - 8.0,
                                      hash01('domeY', record['id'], index) * 90.0, 0.0, 0.0,
                                      scale, scale, scale * lerp(0.82, 1.05,
                                                                 hash01('domeH', record['id'], index))]))
        added += 1
    return added


def plan_souq(source, ring, building_index, cell_of, rows):
    """Vaults, awnings and stalls along the mapped streets inside the Ottoman walls."""
    counts = {'stations': 0, 'arch': 0, 'awning': 0, 'stall': 0, 'tooWide': 0}
    minx, miny, maxx, maxy = F.ring_bbox(ring)
    for osm_id, points in source.polylines('road'):
        converted = [F.ue_xy(x, z) for x, z in points]
        for index in range(1, len(converted)):
            a, b = converted[index - 1], converted[index]
            length = math.hypot(b[0] - a[0], b[1] - a[1])
            if length < 1.0:
                continue
            steps = max(1, int(length // SOUQ_STATION_CM))
            ux, uy = (b[0] - a[0]) / length, (b[1] - a[1]) / length
            nx, ny = uy, -ux
            for step in range(steps):
                t = (step + 0.5) / steps
                x = a[0] + (b[0] - a[0]) * t
                y = a[1] + (b[1] - a[1]) * t
                if not (minx <= x <= maxx and miny <= y <= maxy):
                    continue
                if not F.point_in_polygon(x, y, ring):
                    continue
                counts['stations'] += 1
                left = probe_wall(building_index, x, y, -nx, -ny)
                right = probe_wall(building_index, x, y, nx, ny)
                if left is None or right is None:
                    continue
                width = left[0] + right[0]
                if width > SOUQ_PROBE_MAX_CM:
                    counts['tooWide'] += 1
                    continue
                ground = F.ue_z(source.height_at(*inverse_ue(x, y)))
                yaw = math.degrees(math.atan2(uy, ux))
                seed = (osm_id, index, step)
                if width <= SOUQ_ARCH_MAX_CM and hash01('arch', *seed) < SOUQ_ARCH_SHARE:
                    span = width + 60.0
                    rise = span * lerp(SOUQ_ARCH_RISE_FRACTION[0], SOUQ_ARCH_RISE_FRACTION[1],
                                       hash01('archH', *seed))
                    spring = SOUQ_ARCH_SPRING_CM + lerp(-20.0, 40.0, hash01('archS', *seed))
                    mid_x = x + nx * (right[0] - left[0]) / 2.0
                    mid_y = y + ny * (right[0] - left[0]) / 2.0
                    rows.append(('arch', cell_of(mid_x, mid_y),
                                 [mid_x, mid_y, ground + spring, yaw + 90.0,
                                  0.0, 0.0, span / 100.0,
                                  lerp(0.7, 1.3, hash01('archD', *seed)), rise / 100.0]))
                    counts['arch'] += 1
                    continue
                if hash01('awn', *seed) < SOUQ_AWNING_SHARE:
                    side = 1.0 if hash01('awnS', *seed) < 0.5 else -1.0
                    distance = right[0] if side > 0 else left[0]
                    ax = x + nx * side * (distance - 6.0)
                    ay = y + ny * side * (distance - 6.0)
                    rows.append(('awning', cell_of(ax, ay),
                                 [ax, ay, ground + SOUQ_AWNING_HEIGHT_CM,
                                  yaw + (90.0 if side < 0 else -90.0), 0.0, 0.0,
                                  lerp(0.85, 1.25, hash01('awnW', *seed)), 1.0, 1.0]))
                    counts['awning'] += 1
                if hash01('stall', *seed) < SOUQ_STALL_SHARE:
                    side = 1.0 if hash01('stallS', *seed) < 0.5 else -1.0
                    distance = (right[0] if side > 0 else left[0]) - 150.0
                    if distance < 60.0:
                        continue
                    sx = x + nx * side * distance
                    sy = y + ny * side * distance
                    rows.append(('stall', cell_of(sx, sy),
                                 [sx, sy, ground, yaw + (90.0 if side < 0 else -90.0), 0.0, 0.0,
                                  1.0, 1.0, lerp(0.9, 1.1, hash01('stallH', *seed))]))
                    counts['stall'] += 1
    return counts


def inverse_ue(x_cm, y_cm):
    """Canonical UE cm back to the source (x, z) amot pair CitySource.height_at expects."""
    return (x_cm / F.AMAH_CM - F.TX, y_cm / F.AMAH_CM - F.TZ)


def probe_wall(index, x, y, dx, dy):
    """March outward until inside a footprint; returns (distance, record) or None."""
    step = 40.0
    distance = step
    while distance <= SOUQ_PROBE_MAX_CM:
        px, py = x + dx * distance, y + dy * distance
        for record in index.query(px - 1.0, py - 1.0, px + 1.0, py + 1.0):
            box = record['boxCm']
            if box[0] <= px <= box[2] and box[1] <= py <= box[3]:
                if F.point_in_polygon(px, py, record['loopCm']):
                    return (distance, record)
        distance += step
    return None


# ==================================================================== assembly
def build_plan(source, prepared, facade_state, hidden, groups, ring):
    building_index = F.Grid2D(1200.0)
    for record in prepared:
        box = record['boxCm']
        building_index.insert(box[0], box[1], box[2], box[3], record)

    def zone_of_group(group):
        if group is None:
            return None
        return 'precinct' if (group in hidden['cells'] or group in hidden['largeGroups']) else 'kept'

    def zone_of_cell_name(cell):
        return 'precinct' if cell in hidden['cells'] else 'kept'

    def cell_of(x, y):
        return F.cell_name(F.cell_key_of(x, y))

    roof_rows = []
    counts = {key: 0 for key, *_ in MESHES}
    inside_walls = 0
    for record in prepared:
        in_ring = F.point_in_polygon(record['centreCm'][0], record['centreCm'][1], ring)
        inside_walls += 1 if in_ring else 0
        plan_parapets(record, facade_state, roof_rows)
        plan_roof_plant(record, facade_state, roof_rows)
        plan_domes(record, in_ring, facade_state, roof_rows)

    souq_rows = []
    souq_counts = plan_souq(source, ring, building_index, cell_of, souq_rows)

    buckets = {}
    for key, record, row in roof_rows:
        zone = zone_of_group(groups.get(record['id'])) or zone_of_cell_name(record['cell'])
        buckets.setdefault((zone, key), []).append([round(v, 3) for v in row])
        counts[key] += 1
    for key, cell, row in souq_rows:
        zone = zone_of_cell_name(cell)
        buckets.setdefault((zone, key), []).append([round(v, 3) for v in row])
        counts[key] += 1

    batches = []
    for (zone, key), rows in sorted(buckets.items()):
        for start in range(0, len(rows), BATCH_ROWS):
            chunk = rows[start:start + BATCH_ROWS]
            batches.append({
                'batchId': '%s_%s_%03d' % (zone, key, start // BATCH_ROWS),
                'zone': zone,
                'meshKey': key,
                'rows': chunk,
                'count': len(chunk),
            })
    return batches, counts, inside_walls, souq_counts


def write_meshes(provenance):
    records = []
    asymmetric = 0
    for key, asset, builder, material, shadow, cull, note in MESHES:
        solids = builder()
        for solid in solids:
            if solid.volume() <= 0.0:
                raise RuntimeError('%s has a non-positive canonical solid' % asset)
        info = F.write_obj(OBJ_DIR / (asset + '.obj'), asset, solids, provenance)
        low, high = info['canonicalBoundsCm']['min'], info['canonicalBoundsCm']['max']
        y_offset = abs(low[1] + high[1])
        info.update({'key': key, 'assetName': asset, 'materialKey': material,
                     'castShadow': shadow, 'cullDistanceCm': cull, 'note': note,
                     'solids': len(solids),
                     'yAsymmetricCm': round(y_offset, 3),
                     'yAsymmetric': y_offset > 5.0})
        if info['yAsymmetric']:
            asymmetric += 1
        records.append(info)
    if asymmetric < 6:
        raise RuntimeError('Only %d unit meshes are asymmetric in Y; the release bounds check '
                           'would not be able to prove the OBJ reflection' % asymmetric)
    return records, asymmetric


def write_preview(path, ring, prepared, batches):
    minx, miny, maxx, maxy = F.ring_bbox(ring)
    pad = 12000.0
    minx, miny, maxx, maxy = minx - pad, miny - pad, maxx + pad, maxy + pad
    scale = (PREVIEW_PX - 40) / max(maxx - minx, maxy - miny)
    width = int((maxx - minx) * scale) + 40
    height = int((maxy - miny) * scale) + 40 + 130
    canvas = F.Canvas(width, height, (246, 243, 235))

    def to_px(point):
        return (20 + (point[0] - minx) * scale, 20 + (point[1] - miny) * scale)

    for record in prepared:
        box = record['boxCm']
        if box[2] < minx or box[0] > maxx or box[3] < miny or box[1] > maxy:
            continue
        canvas.polygon([to_px(p) for p in record['loopCm']], (214, 208, 196))
    ring_px = [to_px(p) for p in ring]
    for index in range(len(ring_px)):
        a, b = ring_px[index], ring_px[(index + 1) % len(ring_px)]
        canvas.line(a[0], a[1], b[0], b[1], (120, 96, 64))

    colours = {'parapet': (150, 140, 120), 'solar': (20, 20, 24), 'water_tank': (40, 40, 46),
               'aircon': (120, 124, 130), 'satdish': (140, 144, 150), 'aerial': (150, 154, 160),
               'washline': (220, 90, 90), 'stairhead': (170, 158, 132), 'dome': (70, 120, 190),
               'awning': (210, 150, 60), 'arch': (150, 70, 160), 'stall': (200, 120, 40)}
    order = ['parapet', 'stairhead', 'aircon', 'satdish', 'aerial', 'washline', 'water_tank',
             'solar', 'dome', 'awning', 'arch', 'stall']
    by_key = {}
    for batch in batches:
        by_key.setdefault(batch['meshKey'], []).extend(batch['rows'])
    for key in order:
        colour = colours.get(key, (0, 0, 0))
        for row in by_key.get(key, ()):
            if not (minx <= row[0] <= maxx and miny <= row[1] <= maxy):
                continue
            px, py = to_px((row[0], row[1]))
            canvas.pixel(int(px), int(py), colour)
            if key in ('dome', 'arch', 'stall', 'awning'):
                canvas.pixel(int(px) + 1, int(py), colour)
                canvas.pixel(int(px), int(py) + 1, colour)

    base = height - 118
    canvas.text(20, base, 'CITYDETAILV1 PLAN - OLD CITY WINDOW', (40, 36, 30), 3)
    line = base + 26
    for chunk in range(0, len(order), 4):
        cursor = 20
        for key in order[chunk:chunk + 4]:
            canvas.rect(cursor, line + 2, cursor + 10, line + 12, colours[key])
            cursor = canvas.text(cursor + 16, line, '%s %d' % (key.upper(), len(by_key.get(key, ()))),
                                 (40, 36, 30), 2) + 20
        line += 22
    path.write_bytes(canvas.png_bytes())
    return {'file': path.name, 'sha256': sha256_of(path), 'bytes': path.stat().st_size,
            'widthPx': width, 'heightPx': height,
            'note': 'Plan window is the Ottoman wall ring plus 120 m; the modern city outside '
                    'it carries the same rules but is not drawn here.'}


def generate(force=False, preview=True):
    started = time.time()
    if MANIFEST_PATH.exists() and not force:
        raise RuntimeError('%s already exists; pass --force to re-author' % MANIFEST_PATH)
    OBJ_DIR.mkdir(parents=True, exist_ok=True)

    source_sha = sha256_of(F.SOURCE_JSON)
    if source_sha != F.SOURCE_JSON_SHA:
        raise RuntimeError('jerusalem.json is not the reviewed revision')

    source, records, skipped, verification = load_city()
    prepared = prepare_records(records)
    by_id = {record['id']: record for record in prepared}
    facade_state, facade_status, facade_sha = load_facade_state(by_id)
    hidden = load_precinct_hidden_cells()
    groups, group_unmatched = component_groups(records)
    ring, ring_area_m2, _ = F.old_city_ring(source)

    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    provenance = [
        'CityDetailV1 unit mesh, authored by Scripts/create_city_detail.py at ' + stamp,
        'Canonical UE cm at the origin; instanced by Scripts/release_city_detail.py.',
        'AUTHORED massing in the style of the modern Jerusalem roofscape; not surveyed.',
    ]
    meshes, asymmetric = write_meshes(provenance)
    mesh_by_key = {record['key']: record for record in meshes}

    batches, counts, inside_walls, souq_counts = build_plan(
        source, prepared, facade_state, hidden, groups, ring)

    instances = sum(batch['count'] for batch in batches)
    triangles = sum(mesh_by_key[batch['meshKey']]['triangles'] * batch['count'] for batch in batches)
    if instances > BUDGET_MAX_INSTANCES:
        raise RuntimeError('Plan carries %d instances, over the %d budget'
                           % (instances, BUDGET_MAX_INSTANCES))
    if triangles > BUDGET_MAX_TRIANGLES:
        raise RuntimeError('Plan carries %d LOD0 triangles, over the %d budget'
                           % (triangles, BUDGET_MAX_TRIANGLES))

    by_zone = {}
    for batch in batches:
        entry = by_zone.setdefault(batch['zone'], {'instances': 0, 'batches': 0, 'byMesh': {}})
        entry['instances'] += batch['count']
        entry['batches'] += 1
        entry['byMesh'][batch['meshKey']] = entry['byMesh'].get(batch['meshKey'], 0) + batch['count']

    components = sorted({(batch['zone'], batch['meshKey']) for batch in batches})
    plan = {
        'status': STATUS,
        'version': VERSION,
        'stamp': stamp,
        'generatorSha256': sha256_of(Path(__file__)),
        'batches': batches,
        'rowFormat': ['xCm', 'yCm', 'zCm', 'yawDeg', 'pitchDeg', 'rollDeg',
                      'scaleX', 'scaleY', 'scaleZ'],
        'rowFormatNote': ('Canonical UE world centimetres, the level frame the buildings are '
                          'already in; the release script applies the transform as-is and never '
                          're-applies the (TX, TZ) alignment.'),
    }
    PLAN_PATH.write_text(json.dumps(plan, separators=(',', ':')) + '\n', encoding='utf-8')

    preview_info = None
    if preview:
        preview_info = write_preview(PREVIEW_PATH, ring, prepared, batches)

    manifest = {
        'status': STATUS,
        'version': VERSION,
        'stamp': stamp,
        'generatorSha256': sha256_of(Path(__file__)),
        'facadesModuleSha256': sha256_of(ROOT / 'Scripts' / 'create_oldcity_facades.py'),
        'source': {
            'jerusalemJson': str(F.SOURCE_JSON),
            'jerusalemJsonSha256': source_sha,
            'frozenBuildingsManifest': str(F.FROZEN_MANIFEST),
            'facadesManifest': str(FACADES_MANIFEST),
            'facadesManifestSha256': facade_sha,
            'facadesManifestStatus': facade_status,
            'precinctReceipt': hidden['source'],
            'precinctReceiptSha256': hidden['sha256'],
            'reuse': ('Footprints, terrain heights, the (TX, TZ) alignment, the 100 m cell '
                      'naming, the wall ring, the exclusion zones and the OBJ adapter are all '
                      'imported from Scripts/create_oldcity_facades.py, not re-derived.'),
        },
        'reconstructionVerification': verification,
        'buildings': {
            'extruded': len(records),
            'skippedBySourceRule': skipped,
            'prepared': len(prepared),
            'insideOttomanWallRing': inside_walls,
            'wallRingAreaM2': round(ring_area_m2),
            'withOldCityFacadeShells': len(facade_state),
            'componentGroupUnmatched': group_unmatched,
            'componentGroupNote': ('Unmatched footprints are members of a welded multi-footprint '
                                   'component; those fall back to their own 100 m cell for the '
                                   'zone decision, which is the same cell the actor lives in.'),
        },
        'precinctZones': {
            'policy': hidden['policy'],
            'rule': hidden['rule'],
            'hiddenCellCount': len(hidden['cells']),
            'hiddenLargeGroupCount': len(hidden['largeGroups']),
            'squareOuterFacesCm': hidden['squareOuterFacesCm'],
            'why': ('The precinct plaza hides whole building actors. Instances are split into a '
                    'kept actor and a precinct actor per mesh so the precinct half can be hidden '
                    'with the buildings it decorates and nothing floats over the plaza.'),
        },
        'meshes': meshes,
        'materials': MATERIALS,
        'retint': RETINT,
        'rules': {
            'solarShare': SOLAR_SHARE,
            'solarShareSource': ('Solar water heating has been mandatory in new Israeli '
                                 'residential construction since the 1980 amendment to the '
                                 'planning and building regulations, and household coverage is '
                                 'reported at about 85 per cent. The black tank and collector '
                                 'are the normal Jerusalem roof, not an ornament.'),
            'stoneSource': RETINT['why'],
            'parapetMinAreaM2': PARAPET_MIN_AREA_M2,
            'parapetMinEdgeCm': PARAPET_MIN_EDGE_CM,
            'clutterAreaPerItemM2': CLUTTER_AREA_PER_ITEM_M2,
            'maxClutterPerRoof': MAX_CLUTTER_PER_ROOF,
            'domeShareInsideWalls': DOME_SHARE,
            'stairHeadShare': STAIRHEAD_SHARE,
            'souq': {'stationSpacingCm': SOUQ_STATION_CM, 'archMaxWidthCm': SOUQ_ARCH_MAX_CM,
                     'archSpringCm': SOUQ_ARCH_SPRING_CM, 'archRiseFraction': list(SOUQ_ARCH_RISE_FRACTION),
                     'probeMaxCm': SOUQ_PROBE_MAX_CM, **souq_counts},
            'sourceConfidence': {
                'level': 'CITED_FROM_GENERAL_KNOWLEDGE_NOT_VERIFIED_AGAINST_A_DOCUMENT',
                'claims': [
                    'The 1918 Jerusalem town-planning ordinance issued under the military '
                    'governor Ronald Storrs required stone facing on buildings; the requirement '
                    'was carried into the British Mandate planning schemes and is still enforced '
                    'by the Jerusalem municipality.',
                    'Solar water heating has been mandatory in new Israeli residential '
                    'construction since a 1980 amendment to the planning and building '
                    'regulations, and household coverage is reported at roughly 85 per cent.',
                ],
                'note': ('Both statements are cited from general knowledge by the agent that '
                         'wrote this generator. Neither was checked against a primary document '
                         'in this pass, and no document is quoted or hashed here. They are the '
                         'REASON the rules look like this, not evidence produced by this '
                         'project. Everything else in `rules` is authored dressing with no '
                         'source claim at all.'),
            },
            'duplicateSuppression': ('OldCityFacadesV1 already authored a parapet on all 2,106 of '
                                     'its buildings and its own dome/tank/stair-head hash '
                                     'predicates are re-evaluated here and honoured.'),
        },
        'totals': {
            'unitMeshes': len(meshes),
            'yAsymmetricMeshes': asymmetric,
            'instances': instances,
            'lod0Triangles': triangles,
            'batches': len(batches),
            'hismComponents': len(components),
            'actors': len(components),
            'byMesh': counts,
            'byZone': by_zone,
            'generationSeconds': round(time.time() - started, 2),
        },
        'budget': {
            'document': 'PERFORMANCE-BUDGET.md (measured 2026-09-08)',
            'sceneActorsBefore': 7789,
            'actorsAdded': len(components),
            'actorsAddedPercent': round(100.0 * len(components) / 7789.0, 3),
            'sceneUniqueMeshesBefore': 7519,
            'uniqueMeshesAdded': len(meshes),
            'drawCallsAdded': ('one per HISM per pass: %d base pass, plus shadow depth for the '
                               '%d shadow-casting components'
                               % (len(components),
                                  len([c for c in components
                                       if mesh_by_key[c[1]]['castShadow']]))),
            'lod0TrianglesAdded': triangles,
            'sceneTrianglesBefore': 30_500_000,
            'trianglesAddedPercent': round(100.0 * triangles / 30_500_000.0, 2),
            'instanceBudget': BUDGET_MAX_INSTANCES,
            'triangleBudget': BUDGET_MAX_TRIANGLES,
            'why': ('The measured bottleneck is the game thread carrying 7,767 actors, not '
                    'triangles: after the Nanite pass the GPU is 17.0 ms against a 28.7 ms game '
                    'thread. HISM is therefore the only acceptable shape for this addition - it '
                    'adds %d actors, not 11,437. Per-instance cull distances keep the small '
                    'plant out of the far city view, and the thin items (dish, aerial, washing '
                    'line, awning, stall) do not cast shadows, so ShadowDepths, which was the '
                    'single largest GPU cost before Nanite, is only asked to carry parapets, '
                    'tanks, stair houses, domes and vaults.' % len(components)),
        },
        'nativePlan': {
            'namespace': '/Game/MikdashV3/JerusalemContext/CityDetailV1',
            'importer': 'Scripts/release_city_detail.py (+ .spec.json)',
            'componentClass': 'HierarchicalInstancedStaticMeshComponent',
            'collision': 'NoCollision on every component',
            'nanite': False,
            'naniteWhy': ('These are 12 to 96 triangle props at up to 130,000 instances. Classic '
                          'HISM gives one draw call per component with per-instance distance '
                          'culling; Nanite would add always-resident root pages per mesh and '
                          'does not honour the cull distances this plan depends on. The Nanite '
                          'pass of 2026-09-08 excluded the existing decorative HISMs for the '
                          'same reason.'),
            'placement': 'per-instance world transforms exactly as written in the plan rows',
        },
        'preview': preview_info,
        'plan': {
            'file': PLAN_PATH.name,
            'sha256': sha256_of(PLAN_PATH),
            'bytes': PLAN_PATH.stat().st_size,
        },
        'limitations': [
            'AUTHORED: every parapet, tank, collector, condenser, dish, aerial, washing line, '
            'stair house, dome, awning, vault and stall placed here is invented massing in the '
            'style of the modern city. Only the stone ordinance and the ubiquity of solar water '
            'heating are sourced claims; nothing else is surveyed, photogrammetric or a claim '
            'about a particular building. Nothing here is halachic.',
            'No engine work is performed by this script: no import, no placement, no material, '
            'no collision, no cook and no visual acceptance. Those belong to '
            'Scripts/release_city_detail.py and to a human looking at the result.',
            'Roof heights come from the same reconstruction the extruded prisms came from, so a '
            'parapet sits on the prism top exactly; but the prisms themselves are OSM extrusions '
            'with invented heights wherever the OSM feature carried none.',
            'Souq fittings stand on the terrain height under the street station, not on the '
            'street mesh, so an awning or stall on a steeply cambered alley can sit a few '
            'centimetres proud of or below the paving.',
            'The alley-width probe marches outward in 40 cm steps and only sees mapped '
            'footprints, so a vault can span a gap that is really a courtyard rather than a '
            'street.',
            'The retint entry is a plan, not an applied change: it is only written to the level '
            'if release_city_detail.py is run with -CityDetailRetint, and it is applied as a '
            'per-component override that leaves M_Context_Building and the 1,499 building mesh '
            'assets untouched.',
            'Instance counts are transforms, not a frame-time measurement. Nothing in this '
            'manifest establishes that the result runs at budget on an RTX 2070.',
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


def _summary(manifest):
    return {
        'status': manifest['status'],
        'unitMeshes': manifest['totals']['unitMeshes'],
        'instances': manifest['totals']['instances'],
        'lod0Triangles': manifest['totals']['lod0Triangles'],
        'actors': manifest['totals']['actors'],
        'byMesh': manifest['totals']['byMesh'],
        'byZone': {zone: entry['instances'] for zone, entry in manifest['totals']['byZone'].items()},
        'insideWalls': manifest['buildings']['insideOttomanWallRing'],
        'souq': {k: v for k, v in manifest['rules']['souq'].items() if isinstance(v, int)},
        'matchRatio': manifest['reconstructionVerification']['matchRatio'],
        'seconds': manifest['totals']['generationSeconds'],
    }


if __name__ == '__main__':
    result = generate(force='--force' in sys.argv, preview='--no-preview' not in sys.argv)
    print(json.dumps(_summary(result), indent=2))
