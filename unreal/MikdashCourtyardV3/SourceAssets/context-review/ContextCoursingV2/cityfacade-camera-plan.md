# Source-derived CityFacadeV1 packaged A/B camera

Prepared 15 September 2026 by offline measurement only. **Proposed camera; no
native capture or cooked material binding inspection performed by this author.**
The coordinator owns the native slot and the existing memory guards.

## Requested pose

```text
BugItGo -126006.873 29199.165 4092.206 10 -171.606849 0
```

Use MODERN, horizontal FOV 90, 16:9, and identical exposure/capture settings in
baseline, family-patch and restored-baseline runs. This camera is 5 m east of a
long, approximately X-facing plain source building wall, outside the Old City
facade-shell extent. It tests the independent third master M_CityFacadeV1.

BugItGo teleports the pawn, not a guaranteed camera origin: installed
`Engine/Source/Runtime/Engine/Private/CheatManager.cpp`, BugItWorker around
1074–1092, uses Ghost, TeleportTo and SetControlRotation. Project
`MikdashPhotoMode.cpp:413–422` obtains GetPlayerViewPoint to create the photo
camera. Therefore actual view origin, rotation and FOV from the native probe
are authoritative. The requested Z is source terrain plus 170 cm; it is not a
claim about final native eye height. Preserve the recorded pose across A/B/A.

## Mesh and material evidence

```text
/Game/MikdashV3/JerusalemContext/Buildings/SM_JerusalemBuildings_Grid_N013_P002
/Game/MikdashV3/JerusalemContext/CityFacadeV1/Materials/MI_CityFacade_CityStone
/Game/MikdashV3/JerusalemContext/CityFacadeV1/Materials/M_CityFacadeV1
```

The full mesh object path appends its basename after a period. Expected actor
label equals that basename, but cooked identity should use the full mesh path.
The frozen building manifest assigns source triangle 11430 to this asset,
with identity spawn transform, 100 triangles and source components 3514/3561.
The target wall belongs to the bounds of component 3561. Current source mesh
uasset SHA256:
`66e2b0e03880bc8262f0ca0d5b382823e50a1de94cd02eb0617132a11242c093`.

`Scripts/release_city_facade.py:90–104,580–608` retargets slot-zero component
overrides on SM_JerusalemBuildings_ actors from the CityDetail retint to the
CityFacade instance. Native Candidate48 reopen receipt
`SourceAssets/context-review/CityFacadeV1/native-city-facade-apply-candidate-20260911T123627216048Z.json`
records all 1,498 components on MI_CityFacade_CityStone and its parent as
M_CityFacadeV1. This is a census, not a per-label assignment row; the expected
target binding follows from that census and prefix-based retarget rule. It has
not been inspected in the current running package. Do not call an unchanged B
frame a failed shader correction before confirming the actual slot and mounted
shader payload.

M_CityFacadeV1 copies the context HLSL into its own master
(`release_city_facade.py:480–488`); it does not inherit M_Context_Building.
The current source instance SHA is
`71a34a549439aeaa9566cc59e587f7b18f4833ec41c9294c30d45b1b1e15a884`;
the corrected third-master SHA is
`80fc721af27e81665ceebcea11dc7e02f1c60b92e7ef43ba15798ddf3a2837a4`.

## Exact source geometry and centre-ray check

Source:
`C:/Mikdash/Mikdash-Windows-Transfer/Workspace/output/architecture-review/jerusalem-meshes.json`,
SHA256 `cec2748be02f7a52616407c6bee12618369b75cbf93c5c8dcd5d4135cdfd52fb`.
Building manifest:
`C:/Mikdash/Mikdash-Windows-Transfer/Workspace/output/cloud-unreal-v3/context-review/buildings-manifest.json`,
SHA256 `777598ca54e98c8be79a8a498fa4b3209d22a4525821087e58904e5bf13c5063`.

Convert source positions using the existing metric-city convention:
`UE X=(sourceX+17.509700315687695)*50`,
`UE Y=(sourceZ-0.5513496449385334)*50`, `UE Z=sourceY*50`.
Do not apply the architectural 0.96 scale or -248 cm translation.

Source mesh 1, zero-based triangle 11430 has world vertices in centimetres:

```text
A (-126860.014984216, 31555.932517753, 3793.700000000)
B (-126143.019984216, 26696.432517753, 3793.700000000)
C (-126860.014984216, 31555.932517753, 4993.700000000)
```

The wall's horizontal edge spans 4912.109738 cm, height 1200 cm. The exterior
horizontal normal used for the camera is (0.989289788, 0.145964776, 0).
Its midpoint XY is (-126501.517484216, 29126.182517753), so moving 500 cm
along that normal gives the unrounded camera XY above. Component 3561's
source bounding box is min(-2625.3799,75.874,524.05),
max(-2540.3701,99.874,656.57). The requested camera is 136.147394 cm east of
the component's complete world AABB, proving it is exterior to that building.

Terrain at the camera XY is 3922.205696 cm using mesh 0's exact 50-source-unit
grid triangles, with the a+b<=1 diagonal convention from
`Scripts/create_mount_access.py:27–43`. Requested Z=terrain+170 cm.

Using the unrounded camera (-126006.872590371,29199.164905995,4092.205695754),
pitch 10 degrees, yaw -171.606848756 degrees, the normalized UE forward ray is
`(cos(pitch)*cos(yaw), cos(pitch)*sin(yaw), sin(pitch))`.
An offline double-precision Moller–Trumbore test of every triangle in source
meshes 0–4, with a 700 cm ray and axis-aligned segment broad phase, finds:

- Terrain (0), asphalt roads (2), stone paths (3), mapped city walls (4): no hits.
- Buildings (1): only triangle 11430, first distance 507.713305943 cm.
- Hit point (-126501.517484216,29126.182517753,4180.369186108).
- Barycentric weights (A,B,C)=(0.177775678243321,0.500000000000000,
  0.322224321756679), strictly inside the triangle.

This confirms a face hit rather than an edge/vertex ambiguity and no foreground
source city wall on the centre ray. At 90-degree horizontal FOV and 16:9, the
requested camera's vertical centre column intersects the wall plane from about
Z=3916.542 to 4502.293 cm, wholly within its vertical face span. A normal-facing
view emphasizes the X projection affected by the zy-to-yz coordinate correction.

`SourceAssets/context-review/OldCityFacadesV1/facades-manifest.json` contains
190 facade/infill output bounds; their global minimum X is -102478.56 cm.
The complete 700 cm test segment is west of X=-126006 cm, so none of these
authored facade/infill batches can occlude this target. The target owner cell
does not occur in that manifest. This is materially stronger than merely
assuming a far-west building is unshelled.

## Native acceptance and limits

Capture the proposed MODERN frame first, then inspect whether the centre region
contains the intended wall and readable coursing/openings. Use exactly the
same actual recorded camera for patched and restored runs. The face covers the
requested centre column; ground may occupy some lower peripheral pixels.
Require baseline restoration to reproduce baseline appearance before attributing
differences to the patch. Record build/container hashes alongside image evidence.

Offline source rays exclude only meshes 0–4, not all later vegetation, decorative
actors, collision shapes or runtime-generated geometry. Facade/infill absence is
bounds-proven, but complete packaged occlusion and current material binding still
need the native frame/probe. No engine, cook, map load, source asset mutation or
memory-guard change was performed for this plan.
