# OldCityFoundationV2 — floating city bases: census, repair, verdict

15 September 2026, Claude. Offline sections are final and reproducible; the frame sections are
filled in from native captures (`SourceAssets/visual-review/city-facade/oldcity01-*`).

## 1. Frames

| view | before (cp26) | after (oldcity01) |
|---|---|---|
| K2 — upper Kotel deck, MODERN, facing the Jewish Quarter | `oldcity01-before-K2-kotel-upper-deck-facing-jewish-quarter.png` | `oldcity01-after-K2-kotel-upper-deck-facing-jewish-quarter.png` |
| K2Y — same camera, YECHEZKEL (state toggle) | `oldcity01-before-K2Y-kotel-upper-deck-yechezkel-state.png` | `oldcity01-after-K2Y-kotel-upper-deck-yechezkel-state.png` |
| S1 — street level, 12.7 m from infill 1200 (one of the four K2 fronts), MODERN | `oldcity01-before-S1-jewish-quarter-lane-walking-infill1200.png` | `oldcity01-after-S1-jewish-quarter-lane-walking-infill1200.png` |
| S2 — street level, 13.8 m from infill 949 (floated 255 cm), MODERN | `oldcity01-before-S2-jewish-quarter-lane-walking-infill949.png` | `oldcity01-after-S2-jewish-quarter-lane-walking-infill949.png` |

Before K2 (cp26, inspected): the four fronts hang over the hillside with their flat undersides in
full view, exactly as `OldCityFoundationV1/diagnosis.md` measured (0.40-2.64 m).

All eight frames were inspected. What they show:

- **K2 before -> after.** The four fronts that hung over the hillside now meet it. The lit flat
  undersides — the thing that read as "cardboard city" from the Kotel deck — are gone from all four,
  and the right-hand block that previously showed a 1 m shadow gap under its corner now sits on the
  slope. Nothing else in the frame moved: the same buildings, the same windows and doors, the same
  deck and retaining wall.
- **K2Y (YECHEZKEL) before -> after: identical.** Bare hillside under the precinct paving, no stone
  bands, no floating courses. The 16 precinct-class foundation actors hide with the buildings they
  support, which is the state test this pass had to pass.
- **S1 at walking height.** The wall now runs into the ground with a plinth course at its foot
  instead of stopping in mid-air over a 143 cm void; the arched door reads as standing on something.
- **S2 at walking height.** The clearest case: the base steps down the slope in horizontal courses
  under the right-hand block, which before was a 255 cm cantilever over bare earth. This is the
  stepped footing doing exactly the job the reference photographs describe.
- **Frame cost.** Median frame time 18.5-19.6 ms across the four views (GPU 17.9-19.1 ms), i.e. no
  measurable regression from 92,952 extra triangles in 96 Nanite meshes; the before frames on cp26
  are in the same band.

## 2. The count

Gap = the building's floor line minus the game terrain, taken along every exposed wall edge; one
number per footprint (its worst point). Terrain is `jerusalem-meshes.json` mesh 0: its own vertex
heights and its own per-cell diagonal, re-proved on every triangle centroid and edge midpoint
(worst error 1.3e-10 cm). `CitySource.height_at` in the facade generator uses the same grid but
always the anti-diagonal and clamps at the border, which differs by up to 0.47 cm; the census does
not use it. Exposed edges only: for courtyard plans the walls a sibling wing covers are excluded.

| worst gap per footprint | OSM extrusions (11,399) | authored infill (1,514) | all (12,913) | all, after repair |
|---|---:|---:|---:|---:|
| <= 1 cm | 9,883 | 35 | 9,918 | 12,912 |
| 1-10 cm | 895 | 54 | 949 | 0 |
| 10-25 cm | 390 | 274 | 664 | 0 |
| 25-50 cm | 173 | 504 | 677 | 1 (excluded, below) |
| 50-100 cm | 49 | 451 | 500 | 0 |
| 1-2 m | 8 | 164 | 172 | 0 |
| 2-4 m | 0 | 32 | 32 | 0 |
| > 4 m | 1 | 0 | 1 | 0 |
| **over 1 cm** | **1,516** | **1,479** | **2,995** | **1** |
| **over 10 cm** | **621** | **1,425** | **2,046** | **1** |

Worst 20 before repair:

| # | id | owner actor | cell | gap (cm) | most buried (cm) |
|---:|---|---|---|---:|---:|
| 1 | osm04024 | SM_JerusalemBuildings_Large_04022 | Grid_N010_P001 | 639.2 | 979.4 |
| 2 | infill708 | RELEASE_OldCityInfill_Grid_N005_P004 | Grid_N005_P004 | 364.5 | 390.1 |
| 3 | infill944 | RELEASE_OldCityInfill_Grid_N004_P003 | Grid_N004_P003 | 338.7 | 166.3 |
| 4 | infill721 | RELEASE_OldCityInfill_Grid_N005_P005 | Grid_N005_P005 | 319.2 | 286.2 |
| 5 | infill898 | RELEASE_OldCityInfill_Grid_N004_P001 | Grid_N004_P001 | 314.8 | 137.5 |
| 6 | infill1 | RELEASE_OldCityInfill_Grid_N010_N001 | Grid_N010_N001 | 313.9 | 263.2 |
| 7 | infill1240 | RELEASE_OldCityInfill_Grid_N002_N005 | Grid_N002_N005 | 291.9 | 261.4 |
| 8 | infill961 | RELEASE_OldCityInfill_Grid_N004_P004 | Grid_N004_P004 | 289.6 | 302.6 |
| 9 | infill3 | RELEASE_OldCityInfill_Grid_N010_N001 | Grid_N010_N001 | 285.8 | 125.0 |
| 10 | infill292 | RELEASE_OldCityInfill_Grid_N007_P001 | Grid_N007_P001 | 280.4 | 176.5 |
| 11 | infill921 | RELEASE_OldCityInfill_Grid_N004_P002 | Grid_N004_P002 | 276.7 | 165.7 |
| 12 | infill706 | RELEASE_OldCityInfill_Grid_N005_P004 | Grid_N005_P004 | 275.1 | 294.4 |
| 13 | **infill1210** | RELEASE_OldCityInfill_Grid_N003_P002 | Grid_N003_P002 | 264.5 | 222.1 |
| 14 | infill735 | RELEASE_OldCityInfill_Grid_N004_N005 | Grid_N004_N005 | 262.3 | 172.0 |
| 15 | infill949 | RELEASE_OldCityInfill_Grid_N004_P003 | Grid_N004_P003 | 255.3 | 146.6 |
| 16 | infill2 | RELEASE_OldCityInfill_Grid_N010_N001 | Grid_N010_N001 | 252.7 | 231.7 |
| 17 | infill1438 | RELEASE_OldCityInfill_Grid_N001_P003 | Grid_N001_P003 | 249.4 | 220.2 |
| 18 | **infill1181** | RELEASE_OldCityInfill_Grid_N003_P001 | Grid_N003_P001 | 247.0 | 115.2 |
| 19 | infill351 | RELEASE_OldCityInfill_Grid_N007_P005 | Grid_N007_P005 | 246.2 | 387.9 |
| 20 | infill166 | RELEASE_OldCityInfill_Grid_N008_P002 | Grid_N008_P002 | 242.9 | 67.2 |

The four K2 fronts reproduce the V1 diagnosis to 0.01 mm: 1200 143.08, 1210 264.46, 1181 247.00,
1183 107.56 cm. Every row is in `census-before.json`; `check-after.json` carries the same rows with
the after numbers. Both are regenerated byte-identically by
`Scripts/oldcity_foundations_v2.py census|build`.

## 3. Which generator, and the fix at the source

- **Infill (authored massing).** `Scripts/create_oldcity_facades.py` `generate_infill` set
  `base_z` from the terrain sampled at the plot **centre**, so on any slope the downhill walls hang.
  That line now calls `infill_base_z(...)`, selected by the new module constant `INFILL_BASE_RULE`:
  - `centre_v1` (default) exists only so the frozen OldCityFacadesV1 set — and
    `create_shell_openings.py`, which regenerates it to prove its opening list — still reproduce byte
    for byte;
  - `ground_min_v2` takes the exact piecewise-linear minimum of the terrain along the wing
    boundaries. Cross-checked against the census on six buildings: the drop equals the measured gap
    to 0.001 cm (e.g. infill 1210: base -37.06 -> -301.52, gap 264.461).
  Consequence, deliberate: `Scripts/create_oldcity_facades.py` no longer matches
  `authoringScriptSha256` in `release_oldcity_facades.spec.json`, so the V1 import cannot be resumed
  under the old spec. V1 assets must not be rebuilt; the repair is additive.
- **OSM extrusions.** `buildJerusalem()` (frozen FBX, Workspace TypeScript) uses
  `base = min(heightAt(corner))`. That can never float at a corner, but it floats wherever a valley
  crosses a wall between two corners — 1,516 buildings, worst 6.4 m. The frozen export is not
  regenerated here; the V2 foundations carry those too.

## 4. What was built, and why it looks like this

The reference notes (`OldCityReferenceV2/reference-notes.md`) and the owner's photographs show
rough limestone walls standing on the ground, stepped lanes with landings, and, on slopes, visible
stone base courses. Two candidate repairs were on the table. Dropping each prism to the lowest
terrain under its footprint would close the gap, but it leaves plaster wall running into the dirt
and, on the uphill side, sinks the V1 doors. So the choice was the second one, in two courses,
around the whole exposed ring (courtyard inner rings included):

- **Plinth (always).** 8 cm proud of the wall, from 25 cm below the exact terrain up to 30 cm above
  the building's floor line, so the V1 doors sit on a threshold course rather than in mid-air.
- **Stepped footing (where the drop exceeds 65 cm).** 22 cm proud, its top stepping down in 45 cm
  courses so that it always shows 20-65 cm above the ground it stands on, with a riser quad at every
  step and at corners. 526 footprints needed one; 1,778 risers.
- **Material** `MI_OldCityFoundationStone`: a duplicate of `MI_OldCityPlaster` (already proven on the
  Nanite infill, parent `M_Context_Building`, so usage overrides come with it), retinted darker
  honey-grey with a 240 cm tile so the base reads as coarser stone than the wall above.
- **Collision** BlockAll, complex-as-simple: the walkable hollow under a formerly floating wall closes.

96 meshes, 92,952 triangles, 2,994 footprints; one mesh per (precinct class x 500 m tile):
76 Kept, 16 Precinct, 4 PrecinctMainOnly (24,280 triangles hide with the precinct).

## 5. Offline proof (before any engine step)

- **Coverage, measured on the emitted triangles, not on the design.** For every repaired footprint,
  at every terrain breakpoint of the wall line and of the plinth line, at every piece end and at
  least every 50 cm — 96,020 samples — a vertical line cuts the plinth triangles and the covered
  height must run from the terrain at the wall line up to the floor line. Worst uncovered height:
  **0.0 cm**. A self-test that deletes half the plinth triangles must (and does) report a gap.
- **Orientation.** 0 downward-facing triangles; the self-test also proves every vertical face points
  away from its footprint (one-sided rendering).
- **Embedment.** Bottom edges follow the terrain exactly 25 cm below it. The deepest vertex anywhere
  is 32.1 cm (inner ends of top strips where the ground rises across the 8-22 cm proud width);
  507 footprints exceed 26 cm. Nothing is buried deeper by design and nothing pokes out below.
- **Protrusion.** At most 31.1 cm from the wall line (22 cm footing at a 45-degree miter).
- **Kotel.** Exactly one footprint, `osm06965` (owner `SM_JerusalemBuildings_Grid_N002_P001`,
  28.4 cm against the original hillside), would put geometry inside the Kotel plaza deck rectangles.
  It is excluded and reported, not silently patched: the Kotel cut removes that hillside in MODERN and
  `KotelCutClosureV1` owns that edge. It is the single remaining footprint over 1 cm.
- **Determinism.** Two consecutive builds hash identically (manifest, check and all 96 OBJs).
  `release_oldcity_foundations_v2.py` refuses to import if the generator hash, any OBJ hash, the
  manifest status or the offline check changes.

## 6. Visibility and ownership

Actors `RELEASE_OldCityFoundationV2_<class>_<tile>`, identity transform, folder
`Release/OldCityFoundationV2`, tags `OldCityFoundationV2` plus either `CityDetailZone_Precinct`
(in `AMikdashEnclosure::HideWhileWallStandsTags`: hidden in YECHEZKEL, visible in MODERN and OVERLAY,
collision following visibility) or `CityDetailZone_Kept`. The class is decided per map from that map's
own hide-set labels — Main50 hides one infill cell Candidate48 does not (`Grid_N004_N004`) — and a
mesh never mixes classes.

Why separate actors rather than swapping the infill meshes: `BuildingIdentityLabel()` resolves a
building only from `/JerusalemContext/Buildings` and `/OldCityFacadesV1/Meshes`. A mesh in a new
namespace would return an empty label, drop out of the 269-owner explicit hide list and its
fingerprint, and make `LegacyRoofRuntimeV1` refuse with `hide-policy-or-controller-mismatch`. The V1
actors, meshes, materials and collision are untouched, so the roof runtime's grouping by owning
building is unaffected.

## 7. Engine application

Every step ran from `Scripts/run_oldcity_foundation_v2_engine.ps1`, detached, one native process at a
time, only after both `SLOT-cp26-review-done.txt` and `SLOT-residents-done.txt` existed and with
commit headroom measured before each launch (29.9 GiB free of a 52.1 GiB limit at the first launch).

**Candidate48 preflight** `native-preflight-Candidate48-20260915T232323772470Z.json`:
`preflight_ok_nothing_saved` — inputs, manifest, generator hash and all 96 OBJ hashes resolved, map
loaded, nothing written.

**Candidate48 apply** `native-apply-Candidate48-20260915T232453236226Z.json`:
`applied_saved_reopened_read_back_visual_acceptance_pending`.
- 96 meshes imported (all created, all Nanite on, collision `CTF_USE_COMPLEX_AS_SIMPLE`), worst
  canonical-bounds error 0.0075 cm — the OBJ Y-reflection round-trips. Nanite fallback triangle count
  23,439 against 92,952 source triangles, as expected for this import path (it is recorded, not matched).
- `MI_OldCityFoundationStone` created by duplicating `MI_OldCityPlaster`, parent
  `M_Context_Building`, every tint and scalar verified by readback.
- 96 actors placed: 8,465 -> 8,561 actors. After SAVE and REOPEN, all 96 read back with identity
  transform, the right mesh and material chain, `BlockAll`, STATIC mobility, tags
  `OldCityFoundationV2` + `CityDetailZone_Precinct`/`CityDetailZone_Kept`, worst world-bounds error
  0.0075 cm, and every owner actor still present in the map (`ownersMissingInMap` empty).
- Map checkpointed to `ReviewCheckpoints/OldCityFoundationV2-apply-Candidate48-20260915T232453236226Z`
  before mutation; all other maps and the protected source assets hash-identical after
  (`protectedUnchanged: true`). Revert: `-OCF2Revert -OCF2Target=Candidate48`.

**Candidate48 verify (fresh process, read-only)** `native-verify-Candidate48-20260915T232702195757Z.json`:
`verified_read_back_nothing_saved`. 96 actors found and re-read from the saved map in a new editor,
worst world-bounds error 0.0075 cm, all `BlockAll`, map bytes unchanged by the verify itself, all
protected files unchanged. Tag split on Candidate48: **80 `CityDetailZone_Kept` + 16
`CityDetailZone_Precinct`**, exactly the manifest's 76 Kept + 4 PrecinctMainOnly (Kept in this map)
and 16 Precinct.

**Main50 apply** `native-apply-Main50-20260915T232807347215Z.json`:
`applied_saved_reopened_read_back_visual_acceptance_pending`. The same 96 assets were REUSED
(`created: 0`, material `created: false`) — nothing was re-imported or rebuilt — and 96 actors were
placed, 8,465 -> 8,561, saved, reopened and read back at worst 0.0075 cm. Map checkpointed to
`ReviewCheckpoints/OldCityFoundationV2-apply-Main50-20260915T232807347215Z`; all other maps and the
protected assets unchanged; every owner actor present.

The per-map zone decision is visible in the two receipts: the same 96 meshes carry **80 Kept + 16
Precinct on Candidate48** and **76 Kept + 20 Precinct on Main50**, the four `PrecinctMainOnly` tiles
flipping because Main50's hide set contains one infill cell (`Grid_N004_N004`) that Candidate48's
does not. Nothing else about the two maps' hide sets was touched.

**Main50 verify (fresh process, read-only)** `native-verify-Main50-20260915T233030271265Z.json`:
`verified_read_back_nothing_saved`. 96 actors re-read from the saved map, 76 Kept + 20 Precinct,
worst world-bounds error 0.0075 cm, map bytes unchanged by the verify, all protected files unchanged.

Both maps therefore carry the same reviewed geometry, with per-map visibility classes, and both were
proved by reopening the saved map in a new editor rather than by trusting the applying process.

**Cook, attempt 1 — FAILED, and not because of this work.** `Checkpoint-Build.ps1 -Label oldcity01`
(receipt `Checkpoint-oldcity01-20260915T233124Z/checkpoint-receipt.json`, UAT exit code 6 after 89 s,
35.1 GiB commit free, so not a memory guard). Its `-build` step compiles the Game target, and another
agent's in-flight `Plugins/MikdashRuntime/Source/MikdashRuntime/Private/KotelClosureRuntime.cpp`
does not compile: `error C2039: 'MaterialIds': is not a member of 'KotelClosureRuntimeData'` and
`'MaterialCount'` likewise, at lines 371-375, against `KotelClosureRuntimeData.h`. That file is the
Kotel closure rebuild in progress; it was left alone. Both maps stayed byte-identical through the
failed cook (`candidateSha256After` = `...6204ef48`, `mainMapChangedDuringCook: false`).

**Cook, attempt 2 — with the already verified binaries.** This work is content-only (meshes, one
material instance, 96 actors), so the retry uses `-UseExistingBinaries`, which omits the UAT build
step. The archive therefore contains the runtime built at 15:57 UTC, **not** any pending C++; it must
not be described as testing the in-flight Kotel closure work.

Result `Checkpoint-oldcity01-20260915T233541Z/checkpoint-receipt.json`: **`checkpoint_playable`**,
UAT exit 0, archive `C:\Mikdash\Builds\Checkpoint-oldcity01-20260915T233541Z` (3.5 GB), child
`MikdashCourtyardV3.exe` SHA-256 `5cc71b343ee48fa89903738a0c63e0d7eac6e6f3fc394ff93e3f6380eb920072`,
bounded startup smoke `playable` (window in 18 s, 3.7 GB peak working set). Candidate48 stayed
byte-identical across the cook (`...6204ef48` before and after) and Main50 was not touched
(`mainMapChangedDuringCook: false`). `usesExistingBinaries: true` — the archive carries the runtime
built at 15:57 UTC and none of the pending C++.

## 8. Verdict against the reference notes

**The defect is fixed, and the fix is honest architecture rather than a patch — but it is one item on
the reference brief's list, not the brief.**

What passes:
- Buildings stand on the ground. 2,994 of the 2,995 floating footprints are closed, proved offline at
  96,020 sample points and confirmed in four native frames at two distances and in two states.
- The repair reads as building, not as caulk: a proud plinth everywhere, a stepped footing where the
  lane falls away, which is what the photographs show on every sloping street in the Quarter.
- The state machine is intact: MODERN shows them, YECHEZKEL hides the precinct ones with their
  buildings, the audited hide list and the legacy roof owner grouping are untouched, both maps carry
  the same geometry with per-map classes, and the cook is `checkpoint_playable`.

What does not pass, measured against the same brief:
- **The ground is still bare earth.** In S1 and S2 the new foundations meet dirt, not paving. The
  photographs show limestone paving wall to wall. The foundation makes the buildings believable and
  makes the missing floor more obvious, not less.
- **The base stone is too close in value to the wall.** At walking distance the plinth reads as
  "the wall continues down" rather than "this is the footing". The reference bases are visibly coarser
  and darker than the wall above. The tints are one material instance away from being fixed.
- **One footprint is knowingly left floating** (`osm06965`, 28.4 cm, at the Kotel cut).
- Reference item 1 ("fix missing/incorrect ground and unsupported buildings before surface
  decoration") is now half done: unsupported buildings, yes; missing ground, no.

## 9. Next three things that break the Old City illusion at walking height

Ranked after inspecting all eight frames, by how much of a walking-height frame the defect occupies
and how early the eye finds it.

1. **There is no ground in the Old City — the lanes are bare earth.** In S1 and S2 the walker stands
   on a dirt slope that runs up to the wall face; the only paving is a thin ribbon of road mesh in the
   distance. Every reference photograph is rectangular limestone paving wall to wall, with steps,
   landings and a central ramp. Until the lanes are paved surfaces at the right level, foundations and
   facades sit in a desert. This is also what makes the buildings read as dropped onto a hill instead
   of built along a street.
2. **Building massing is one flat box per plot, with no party walls, no arches over the lane and no
   depth at the opening.** The reference lanes are continuous walls, vaulted passages and recessed
   arched doors; here each block stands alone with a 30 cm gap to its neighbour, the doors sit where
   the picture frame puts them (sometimes above the ground), and the lane never passes under anything.
3. **The stone reads as one wallpaper.** One tile, one tint family and one course height across every
   building; the photographs show varied course heights, chipped edges, deep irregular joints and
   localized wear, and different finishes for wall, base and paving. The new foundation course is the
   first place in the city where the stone changes value deliberately; the walls above still repeat.

## 10. Limits of this work

- The census covers building footprints. Facade shells, rooftop clutter, ShellOpenings panels and
  CityDetail instances follow their host building and were not measured separately.
- Projected-overlap audits against mount-access ramps and street ribbons were not run for all 2,994
  footprints (the V1 study audited its four); the Kotel deck and step rectangles were.
- The offline proof is geometric. It is not a claim about shading, texture scale, lightmaps, collision
  behaviour for a walking pawn, or frame cost; those are what the native frames and the cook test.
- Terrain outside the Kotel cut is the original hillside. Where a later agent rebuilds the Kotel
  closure face or the staircase underside in this same view, those pixels are theirs, not this work's.
