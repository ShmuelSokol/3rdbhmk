# Source-derived CityWall packaged A/B camera

Prepared 15 September 2026, offline only. **Camera not natively inspected by this
author.** The coordinator is running the packaged comparison independently.
Keep this point fixed for baseline/patch/restore; the actual photo-camera pose
recorded by the native probe is authoritative.

## Requested pose

```text
BugItGo -78612.156 42766.684 2125.937 10 1.098256 0
```

Use **MODERN**, horizontal **FOV 90**, 16:9, and the same capture/exposure settings
for A/B/A. FOV 90 is the coordinator's requested match to the verified four-state
photo probe. The target is a west-facing outer city-wall segment well west of
the precinct, not K2's building-shell material.

Important pose distinction: installed
`C:/Program Files/Epic Games/UE_5.8/Engine/Source/Runtime/Engine/Private/CheatManager.cpp`,
`BugItWorker` around lines 1074–1092, calls Ghost and teleports the **pawn** to
BugItGo coordinates, then sets control rotation. It does not promise that the
camera origin equals those coordinates. Project `MikdashPhotoMode.cpp:413–422`
uses `GetPlayerViewPoint` to spawn the photo camera. Therefore record the actual
view origin, rotation and FOV; retain identical poses between runs. The requested
Z is a useful ground-height construction, not a certified final eye height.

## Exact target and material evidence

Target static mesh package:

```text
/Game/MikdashV3/JerusalemContext/Streets/SM_Jerusalem_CityWalls_04_Grid_N008_P004
```

Its full object path appends
`.SM_Jerusalem_CityWalls_04_Grid_N008_P004`. The expected actor label is the same
mesh basename, but a native identity check must use full mesh path rather than
assuming labels survive cooking. Current source `.uasset` SHA256 is
`ab3b6af4983038aa925e89d4e95d59ec9ff99e38e6af660894823f604b3f7350`.

`SourceAssets/materials-context/native-apply-20260907T215118571170Z.json`,
`assignments.walls`, records this exact asset already assigned
`/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_CityWall`.
`SourceAssets/context-review/streets-reopen.json`, `meshChecks`, records 468
triangles and only 0.0082550048828125 cm bounds error for this exact mesh.
These are saved source/native import-assignment receipts, not a current cooked
component override census. The ExteriorV1 child discovered by the dependency
audit is a possible override; an unchanged B result must trigger binding/shader
inspection rather than a declaration that the HLSL correction failed.

Expected world bounds from the frozen streets manifest, centimetres:

```text
min (-78678.582764, 39928.201294, 1929.479980)
max (-76987.213135, 50260.253906, 3223.820114)
```

The imported context geometry uses metric world coordinates at identity. The
Candidate48 manifest `SourceAssets/enclosure-review/precinct-Candidate48.json`
states that city/terrain were not rescaled with the architecture. Its precinct
west face is X=-31776; this camera and wall lie more than 460 m farther west.
Use MODERN and do not apply the architecture's 0.96/-248 conversion here.
The streets mesh identity is outside the runtime enclosure's building families.
Actual actor/component transforms and material overrides are still native
readback checks if this source-derived frame does not match the expected wall.

## Source geometry and camera construction

Source mesh file:
`C:/Mikdash/Mikdash-Windows-Transfer/Workspace/output/architecture-review/jerusalem-meshes.json`,
SHA256 `cec2748be02f7a52616407c6bee12618369b75cbf93c5c8dcd5d4135cdfd52fb`.
Owner manifest:
`C:/Mikdash/Mikdash-Windows-Transfer/Workspace/output/cloud-unreal-v3/context-review/streets-manifest.json`,
pinned SHA256 `cc9eb91e99298565db296ea52a4eef744944e3bac3014829b573e30235aea8da`.
The coordinate conversion matches `Scripts/create_kotel_opening.py:41–43`:

```text
UE X = (source X + 17.509700315687695) * 50
UE Y = (source Z - 0.5513496449385334) * 50
UE Z = source Y * 50
```

Source `meshes[4]`, `Mapped city walls 4`, triangles **20828 and 20829** form the
chosen face. Both triangle IDs belong to the exact target batch in the frozen
manifest. They are part of the twelve-triangle box **20820 through 20831**.
The face's four vertices, in UE world centimetres, are:

```text
(-78059.494984, 40024.517518, 2929.480000)
(-78164.999984, 45528.017518, 2929.480000)
(-78059.494984, 40024.517518, 1929.480000)
(-78164.999984, 45528.017518, 1929.480000)
```

Face centre is `(-78112.247484, 42776.267518, 2429.48)`; horizontal length is
5504.511200 cm and height 1000 cm. Its outward normal, determined from the face
plane and the box centre, is `(-0.9998162961, -0.0191670061, 0)`.
The proposed XY point is face-centre XY plus 500 cm times this normal. Yaw is
`atan2(-normal.Y,-normal.X)` = 1.098255810 degrees; pitch is the deliberate
10-degree upward close-up.

Requested-point ground height is **1955.937377 cm**, sampled from the actual
source `Terrain 0` piecewise triangular grid using the existing
`Scripts/create_mount_access.py:27–43` interpolation. Requested Z is ground+170
=2125.937377 cm. This is a DEM/source-triangle height, not a measured native
collision hit or an assumption about the pawn camera offset.

The selected whole box AABB is:

```text
min (-78164.999984, 40024.517518, 1929.480000)
max (-77859.529984, 45531.852518, 2929.480000)
```

The proposed point's X is about 447.16 cm west of even the box's minimum X, so
it is outside this wall box, not placed inside its volume. The face-normal
distance is 500 cm. This is not a proof that no later decorative actor occupies
the same space.

## Offline sightline and projection checks

A two-sided ray/triangle intersection test used the requested origin, yaw and
pitch, searching the first 700 cm against source meshes 0–4. Results:

- Terrain 0: no centre-ray hit.
- Mapped building extrusions 1: no centre-ray hit.
- Asphalt roads 2: no centre-ray hit.
- Stone paths 3: no centre-ray hit.
- Mapped city walls 4: first hit is target triangle **20829**, at
  **507.713306 cm** along the tilted ray.

This tests the original source centre ray only. It does not test every screen
pixel, the eventual pawn-offset camera, newer foliage/detail meshes, or native
material assignment. Keep the first packaged frame as the decisive visibility
check instead of silently adjusting pose between A and B.

At FOV90/16:9 the vertical FOV is 58.715507 degrees. At the face plane, the
requested-origin vertical screen-centre column spans approximately
Z=1950.273864 to 2536.024964 cm. This covers roughly 5.86 m of the ten-metre wall,
with the source ground close to the bottom edge. A native camera offset changes
these limits, which is why its recorded pose matters.

The material's `pow(abs(normal),4)` triplanar weights give the X projection
**0.999999864937** of the total on this face. Consequently this close-up tests
the exact corrected projection: old `p.zy` sends world height into texture U;
new `p.yz` sends world height into texture V. A primarily Y-facing wall would
be a poor discriminator because its projection was not changed. Compare both
course orientation and normal relief, not just average wall colour.

## Native comparison scope

Baseline A: retained cp24 containers in the isolated test copy, same runtime
child/camera/state/settings. B: the single-master feasibility overlay mounted
with documented priority. Restored A: remove only that overlay bundle and repeat.
The first feasibility cook intentionally remains the single-master route proof;
the master-plus-ExteriorV1 family request in `dependency-audit.md` is the next
coverage step if binding/permutation evidence requires it, not a claim about
what the first container contains.

Required readback: actual view pose/FOV, MODERN state, patch mount evidence,
same target face, and no missing-shader/default-material fallback. The original
cp24 and its base containers must stay unchanged. No native job, screenshot,
code edit or material mutation was performed while preparing this note.
