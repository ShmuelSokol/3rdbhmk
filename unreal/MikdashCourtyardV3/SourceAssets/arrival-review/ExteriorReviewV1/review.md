# Exterior review V1 — Kotel plaza, Mount platform, city, roads, bus (2026-09-08)

Scope: exterior of the combined map `/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough` (saved SHA-256
`2edb00af...96fc9bd`), reviewed from the latest native real-RHI stills and the receipts listed at the end.
Nothing here was rendered or changed by this review; the Kotel stone surface itself is owned elsewhere and
is not graded. Structured data: `exterior-review-data.json`. Fix script: `Scripts/release_exterior_fixes.py`.

Renders inspected (1920x1080, 75 deg): `release-capture-20260908T001321Z/a_exterior_wide_arrival.png`
(newest), `20260907T220013Z/{a_exterior_wide_arrival, g_mount_platform_approach, h_bus_street_level,
i_overhead_city}.png`, `20260907T220851Z/h_bus_street_level.png` (post bus-material repair),
`20260907T210550Z/{a_exterior_wide_arrival, c_outer_court_pilgrims}.png` (pre-lighting baseline for comparison).
Camera poses are in each folder's `receipt.json`.

## Ranked defects

| # | Defect | Evidence (render, where in frame) | Scripted fix (no protected geometry deleted) | Effort |
|---|--------|-----------------------------------|----------------------------------------------|--------|
| 1 | **No walkable route from the Kotel plaza (Z -1432.5) to the platform deck (Z 0).** The only stairs in the scene are the measured Outer E/N/S gateway stairs on the deck; nothing connects plaza level to the deck. | `001321Z a_exterior`: west edge of the platform, lower-left quadrant, a sheer 14-38 m skirt drops straight to the plaza/Old City with no stair, ramp or portal anywhere on the perimeter. `Content/MikdashV3/FutureMountV1/KotelApproach/` holds only the two `*_KotelCut` wall duplicates; `route-source-plan.json` and both walk probes (`release-walk-20260907T225836Z.json`) start at [10000,0,0] on the deck. `create_mount_access.py` / `create_kotel_opening.py` are source-only (`nativeExecuted: false`). | `release_exterior_fixes.py` fix `access`: import the three frozen OpeningV2 meshes (deck 1080 tris, guards 2160, portal 60; 82 risers, 6 rest landings, 300 cm clear, 320 cm portal headroom) through the platform's OBJ adapter convention into `/Game/MikdashV3/ArrivalReview/MountAccessV2`, spawn `RELEASE_MountAccess_{Deck,Guards,Portal}` at identity +2 cm (avoids the 11 m coplanar overlap with the deck at Z 0 east of x -13597), BlockAll, complex-as-simple, PavingReview/WallReview stone. Offline re-check: 0 samples inside or within 200 cm of the Kotel wall / plaza polygons; adapted signed volumes +79.7/+54.9/+22.4 m3, all top faces +Z. Recorded as authored interpretation (tag `AUTHORED_INTERPRETATION_NOT_SOURCE_FACT`). | 25 min native + 15 min walk probe (add a `plaza_to_deck` route x -18400 -> -12500 at y 19972) + 10 min capture |
| 2 | **Sky renders as a black/dark-brown wall along the horizon in every exterior view since the lighting apply.** | `220013Z` and `001321Z a_exterior`: top ~4% of frame (above the far terrain edge) is black; `220013Z/220851Z h_bus`: the entire sky is dark brown-grey with soft cloud underside. Same camera in `210550Z a_exterior` (before `native-apply-20260907T213137023951Z`) shows a blue horizon. Cause: `VolumetricCloud` material swapped to `MI_Cloud_Scattered` (coverage 0.35); seen edge-on near the horizon the deck becomes continuous and unlit from below; fog max opacity 0.85 then tints it brown. | fix `sky` (**opt-in**, lighting is the sanctuary-balance task's domain): `Cloud_GlobalCoverage` 0.35 -> 0.15 on `MI_Cloud_Scattered` via MaterialEditingLibrary, before value recorded, revertable. Alternative for the lighting owner: raise the cloud layer bottom altitude or restore `MI_Cloud`. | 5 min + 10 min capture |
| 3 | **Platform deck and skirt read as one untextured light-grey slab** that dominates the arrival frame. | `001321Z a_exterior` centre-left (deck) and lower-left (skirt); `220013Z i_overhead` centre. `M_JerusalemStoneV2_PavingReview` (60 cm blocks, 4.5% variation) and `WallReview` are invisible beyond ~50 m; no paving joints, no macro tint. | Not scripted tonight (shared review material, design choice). Recommended: a MaterialInstance of PavingReview for the two `FutureMountV1/Platform` actors only (component override, no asset overwrite) with `BlockWidthCm/BlockHeightCm` 240 and `BlockVariation` 0.15, or a world-aligned paving with 6-8 m macro noise; skirt gets a coursed ashlar with 2 m macro darkening toward the base. | 30 min + capture |
| 4 | **Terrain tiling repetition**: the dry-ground set repeats as a regular grid of light specks. | `001321Z a_exterior` right third (Kidron slopes east of the platform, y 600-1000 px); `220013Z i_overhead` lower-right. `M_Context_Terrain` TileCm 400 with 6000 cm macro at 12% is not enough at 200-800 m. | fix `tiling`: `M_Context_Terrain` TileCm 400->650, ScrubTileCm 250->380, MacroCm 6000->2700, MacroAmp 0.12->0.28 (default parameter values, recompile, save, before values recorded). | 5 min + capture |
| 5 | **City reads as uniform beige boxes** with almost no contrast against the terrain. | `001321Z a_exterior` and `220013Z i_overhead`: whole upper half. The four building tints differ by <10%; roofs fade to plaster. | fix `tiling`: widen `Tint1..3` on `M_Context_Building` (spread ~20%), `RoughVar` 0.12->0.2. Deeper (not tonight): floor-line darkening per building needs per-building bounds, not 100 m buckets. | 5 min |
| 6 | **City-wall blocks are ~1 m Lego blocks.** | `220851Z h_bus`: wall at right edge (x 1500-1920 px). `stone_block_wall` is 2.1 m real size, tiled at 3.5 m. | fix `tiling`: `M_Context_CityWall` TileCm 350->240. | 2 min |
| 7 | **Bus: apparent wheel float and hard road edge.** | `220851Z h_bus`: daylight is visible under the front-axle tyres (x 600-760, y 660-700 px); the rear axle by the wall sits closer. The asphalt ribbon meets the foreground terrain as a straight lip (y ~620 px, left). Receipt `native-placement-20260907T173334153872Z.json` records `planePoseMaxWheelFloatCm` 0.10 against a 4-point PIE trace plane (pitch -3.14, roll 5.64); the capture's camera ground trace hit terrain at Z 641.8 on `SM_JerusalemTerrain_07_09` 14.5 m from the bus origin on asphalt at Z 973 (3.3 m step). | Not scriptable without PIE traces (commandlet/NullRHI traces return nothing). Recommended: per-wheel PIE trace at the four saved tyre contact points, lower the 13 `RELEASE_Bus_*` actors by the max gap (expected 5-20 cm) and re-capture at wheel height. | 20 min PIE + capture |
| 8 | **Terrain-to-road seams**: asphalt/path ribbons stand proud of the terrain with vertical edges on slopes. | `220851Z h_bus` foreground; `220013Z i_overhead` roads on the Kidron slope read as ribbons laid on the surface. Ribbons are 100 m buckets baked to DEM height (`streets-import-20260907T035800Z`); per-actor Z nudging would move whole districts. | Not tonight. Options: (a) re-export with a terrain-following 20 cm skirt per ribbon like `path-grounded-v3`; (b) blend the asphalt edge in the material with a distance-to-edge mask (needs UVs the source lacks). | 60+ min |
| 9 | **Trees on the Mount**: none visible; vegetation plausibility low-medium. | `001321Z a_exterior`, `220013Z i_overhead`: deck is clear. Live ISM counts (`native-apply-20260907T215118571170Z`) trunks 4265 / crowns 12795 match the 144-tree removal. Crowns are identical dark-green spheres; Kidron/Mount of Olives slopes are bare with sparse blobs. | fix `trees`: point-in-polygon verification of every trunk/crown against the inferred enclosure (66 pts) and removal of any inside (expected 0, cap 200, transforms + custom data recorded). Later: per-instance scale/tint jitter on crowns. | 5 min |
| 10 | **Terrain-to-platform seams**: no cracks at this range; the skirt base shows a dark band and the north edge slices Old City buildings. | `001321Z a_exterior` lower-left (skirt base shadow); `220013Z i_overhead` upper-centre (buildings meeting the north skirt). Cut tiles no longer render black (winding fix). | Needs a plaza-level capture (add view `j_plaza_kotel_skirt` at [-17500, 16000, -1264], yaw ~+15) before any change. | 10 min capture |
| 11 | **Floating / sunken buildings**: none obvious from the overhead; half-buried blocks along the platform's north edge are expected (deck above DEM). | `220013Z i_overhead` upper-centre. | None tonight; recheck in the plaza-level capture. | - |
| 12 | **Dark or uniform terrain**: everything outside the walls is one bright beige; mapped green areas barely tint. | `001321Z a_exterior` whole lower right; `210550Z` shows the same before materials. Scrub mask thresholds (lum 0.40-0.50) leave most green land use as bare ground. | Partly covered by fix `tiling` (macro). Follow-up: `MaskLumHigh` 0.5->0.56 and `ScrubTint` greener once a capture confirms the mask reads. | 5 min |
| 13 | **Horizon**: the far terrain edge is a straight cut against the sky (3.2 km tiles end). | `001321Z a_exterior` top edge. | After the sky fix, raise aerial perspective/fog start beyond 2.5 km or add a distant horizon ring; not tonight. | 15 min |

Also seen: `220013Z g_mount_platform_approach` (Outer E gate) is fine geometrically; the gate interior is black
from exposure (interior task). `210550Z c_outer_court_pilgrims` has a blue sky and readable court; not an exterior
context issue.

## What `Scripts/release_exterior_fixes.py` does tonight

Default `-ExteriorFixes=access,tiling,trees` (add `sky` explicitly). Guards, checkpoint and receipt follow
`release_place_assets.py`: wrong project / game world / dirty packages / wrong map refused; map + One-File-Per-Actor
folders + every touched `.uasset` copied to `ReviewCheckpoints/ExteriorFixes-<stamp>/` and hash-verified; one actor
snapshot keyed by native name, refusal if any unrelated actor changes before save or after reopen; protected map
hashes before/after; receipt `native-exterior-fixes-<stamp>.json` in this folder written at start, per step and in
`finally`. `-ExteriorDryRun` plans everything (including the inside-polygon tree count and current material values)
and writes nothing. `-ExteriorRevert[=<receipt>]` destroys the access actors (assets kept and listed), restores the
recorded material defaults and cloud coverage, and re-adds removed instances.

```
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" ^
  "C:\Mikdash\Working-5.8\MikdashCourtyardV3\MikdashCourtyardV3.uproject" -run=pythonscript ^
  -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_exterior_fixes.py" ^
  -ExteriorDryRun -unattended -nullrhi -abslog="C:/Mikdash/Working-5.8/Release-ExteriorFixes-DryRun-01.log"
```
Then the same line without `-ExteriorDryRun` (optionally `-ExteriorFixes=access,tiling,trees,sky`), then a real-RHI
capture and a walk probe before any acceptance claim. Offline: `python Scripts/release_exterior_fixes.py`
(py_compile and `offline_check()` pass with the bundled 3.11.8 interpreter; adapter OBJs land in `adapter/`).

## Risks and limits

- The stair is an authored future interpretation over the OpeningV2 corridor (y 19972, x -18400 -> -12500). It was
  checked against 1,952 retained wall boxes and both protected polygons only; buildings and terrain along the
  corridor were never clipped or tested. Expect the deck to pass through the platform skirt (hidden) and possibly
  through Jewish-Quarter building buckets near x -18400..-16000: inspect the plaza-level capture and walk it.
- Material default changes alter shared StaticMesh dependencies; donor maps look different with unchanged `.umap`
  bytes (same disclosure as the context-material apply).
- The sky fix touches a lighting asset; coordinate with the lighting owner before running it.
- No fix here claims visual acceptance; the receipts record geometry and parameter readback only.

## Receipts and sources consulted

`SourceAssets/visual-review/mount-platform-design.json` (platform boundary 66 pts, protected Kotel wall + plaza,
levels), `FutureMountV1/mount-platform.mesh.json` (deck ring: west edge x -13597.4 at y 19972),
`FutureMountV1/route-review/route-source-plan.json`, `IntegratedReviewV2/release-walk-20260907T{225836,211526}Z.json`,
`materials-context/native-apply-20260907T2150{13,118}*.json` (4,627 assignments; live ISM counts),
`arrival-review/TransitV2/native-placement-20260907T1733{34,20}*.json` (bus pose, wheel-plane float 0.10 cm),
`context-review/{terrain,streets,instances,buildings}-import-*.json`, `FutureMountV1/terrain-generated/terrain-cut-manifest.json`,
`FutureMountV1/native-mount-tree-removal.json`, `mount-access/OpeningV2/{opening-v2-spec,opening-v2-checks,README}`,
`lighting-review/native-apply-20260907T213137023951Z.json` (cloud material swap, fog values), Poly Haven real sizes in
`Scripts/release_context_materials.spec.json`.
