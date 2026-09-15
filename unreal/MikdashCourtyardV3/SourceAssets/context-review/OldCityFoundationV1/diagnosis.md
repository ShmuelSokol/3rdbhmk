# Four floating infill fronts in the actual K2 frame

15 September 2026. **Offline source diagnosis only; no repair or native job.**

The four prominent fronts examined in
`../KotelCutClosureV1/runtime-20260915T171947530Z-phase0.png` are authored infill
blocks. Their flat undersides sit above the downhill terrain. This is distinct
from the Kotel excavation closure in the foreground and from an intended arch.
The measured front-edge gaps below the main solid prism are:

- Left broad front: infill **1200**, 40.50–143.08 cm.
- Narrow front just left of centre: infill **1210**, 218.81–264.46 cm.
- Tall central front: infill **1181**, 157.75–247.00 cm.
- Broad front right of centre: infill **1183**, 55.01–107.56 cm.

These are exact piecewise-linear terrain extrema along the selected front
edges, not estimates from screen pixels or extrema of actor AABBs. Decorative
geometry extends at most 4 cm below each prism; it cannot bridge these gaps.
This is a four-building diagnosis, not an exhaustive classification of every
visible front or every building in the city.

## Exact source identities

1200 and 1210 are parts of:
`/Game/MikdashV3/JerusalemContext/OldCityFacadesV1/Meshes/SM_OldCityInfill_Grid_N003_P002`.
Their main prism triangle ranges in the canonical OBJ are respectively
5308–5319 and 12994–13005, zero-based. Native import receipt actor label:
`RELEASE_OldCityInfill_Grid_N003_P002`, historical actor name
`StaticMeshActor_7488`.

1181 and 1183 are parts of:
`/Game/MikdashV3/JerusalemContext/OldCityFacadesV1/Meshes/SM_OldCityInfill_Grid_N003_P001`.
Their prism triangle ranges are 3340–3351 and 5020–5031. Native import receipt
label: `RELEASE_OldCityInfill_Grid_N003_P001`, historical actor name
`StaticMeshActor_7486`.

`../OldCityFacadesV1/native-import-20260908T031832420071Z.json` records identity
placements, BlockAll/complex-as-simple, and MI_OldCityPlaster on both batches.
Current source uasset hashes still match that import receipt exactly:
P001 `9bc21a5c917fe3bf4fbf055f67f8bfe9b364a18c09992dfb6e561d920439be76`;
P002 `c3c11ce93146552eef87ab1c0d2c59d71f118f87cb404da579f34d4ca6fa9164`.
The historical native import reports reduced Nanite fallback triangle counts;
the OBJ triangle numbers above must not be used as runtime collision/render IDs.
No fresh native object-ID pass or current component-name trace was performed.

## Image-to-triangle evidence

The image is **2560 x 1440**. The accompanying native receipt records the actual
camera at (-20711.445,19228.202,-746.418) cm, pitch 6.000002 degrees,
yaw 175.000001 degrees, roll 0.000001 degrees, FOV 90. This is the recorded
photo camera, not the different requested BugItGo pawn position.

Pixel rays through four selected underside points hit downward-facing solid
bottom triangles:

- (375,625): infill1200 triangle5319, underside Z=-236.81, local gap69.55 cm.
- (762.5,547.5): infill1210 triangle13005, Z=-37.06, local gap163.71 cm.
- (1112.5,530): infill1181 triangle3351, Z=87.65, local gap89.05 cm.
- (1625,605): infill1183 triangle5031, Z=-245.08, local gap31.94 cm.

Companion rays above those points hit each prism's front wall. The closest
intersections in the four nearby facade/infill OBJ batches match the four
structures in the screenshot. There are no closer hits from the checked
original building/road/path/city-wall triangles along these ray segments,
retained source terrain outside the deck cut, or the canonical closure mesh.
Other later decoration and native Nanite topology are not part of this ray test;
this is source-supported visual attribution, not a complete native scene trace.

`ray-samples.json` records the pixel coordinates, actual triangle vertices,
normals, camera, intersection points, owner mapping, terrain triangles, front
edge breakpoints, input SHA256s and calculation conventions. Serialized camera
coordinates are rounded to 0.001 cm; the negligible recorded roll was ignored.
OBJ vertices are rounded to 0.01 cm, so report practical gaps to centimetres.

## Why these float, and why these are not arches

`Scripts/create_oldcity_facades.py:1467` selects each infill's flat base from
terrain sampled at the candidate **centre**. Lines1896–1914 emit a solid prism
for every wing, then add facade ornaments. For these four buildings the base
matches terrain at the recovered footprint centre within 0.0041 cm. The
downhill front edge is lower than that central ground level, creating the gap.
The inferred mechanism therefore agrees with both source code and exact mesh
measurements; no modern-city scale or transform adjustment is implicated.

All four manifest records say `plan=block`, `wings=1`, `AUTHORED_INFILL`.
Their first12 triangles form the actual four-sided solid prism: eight side
triangles, two top triangles and two bottom triangles. Every prism mesh edge
is used twice and signed volume is positive. The sampled underside normals
are (0,0,-1). This establishes solid rectangular massing from triangles, not
from treating a batch AABB as occupied volume.

The arched and rectangular opening details are separate picture-frame solids
added to these walls. They do not cut passages through the supporting prism
(`create_oldcity_facades.py` introductory source contract and `prism`, lines608–621).
There are no modeled piers or foundation walls beneath these four flat bottoms.
The visible exposed undersides are therefore unsupported portions of the
authored blocks, not intentional vaulted ground-level openings.

## Relationship to the Kotel cut and next repair study

Each actual convex footprint was clipped against every one of the959 pinned
deck rectangles; each has zero intersection area. Terrain comparison uses the
exact566-triangle FutureMount source and the preserved outside-cut surface,
not a bilinear DEM or a guessed plateau. The affected fronts are behind the
excavation perimeter: extending the Kotel visual closure across their gaps
would conflate two separate geometry problems.

A future isolated repair study can use these **four proven solid infill
footprints** to test terrain-following foundations down from the real bottom
boundary. Before producing geometry it must intersect exact terrain triangles,
preserve streets/access and unrelated buildings, and handle any overlapping
solids. Do not extrapolate this finding to courtyard wings, arches, original
OSM footprints or the entire city. No foundation mesh, collision change,
asset overwrite, map save or production fix is authorized or created here.
