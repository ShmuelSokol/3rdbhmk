# YECHEZKEL as the default view — what changed, 8 September 2026

Decision (Shmuel): build the precinct EXACTLY as Yechezkel 42:15-20 states — 500 reeds x 6 amot
= 3,000 amot a side — as the DEFAULT view; modern buildings inside hidden by visibility, never
deleted; MODERN and OVERLAY reachable by the existing cycle. Offline work only: no editor
launched, no UBT run, nothing committed. Receipts: `precinct-Main50.json`,
`precinct-Candidate48.json`, `geometry-manifest.json`, `tests.json` (this folder).

## 1. C++ for the coordinator to compile (MikdashCourtyardV3Editor)

`Public/EnclosureMath.h` (engine-free, shared by generator, placer, actor, test)
* new §5b: `FGroundProfile`, `GroundProfileValid`, `SampleGroundHighZ/LowZ`, `FGrounding`,
  `GroundSpan` (plinth on the highest ground a span crosses; substructure to the lowest less a
  footing), `GroundProfileSideRange`, `ModuleScaleFor`; `Candidate48CmPerAmah = 48`.
* `FModuleBudget::FoundationTriangles = 12`; `FWallPlan` gains `FoundationInstances` /
  `FoundationTriangles` (476 / 5,712); totals 1,432 instances, 118,656 triangles.

`Tests/EnclosureMathTest.cpp` — updated totals; new `GroundChecks()` (480 modules over a
synthetic Kidron: plinth never below grade, substructure never above it; interpolation exact;
malformed profiles refused); the 48 cm square asserted at −31776/−31824/112224/112176 with the
same plan. Compiled and run standalone (cl /W4 /O2): PASS. Snapshot `tests.json` regenerated.

`Public/MikdashEnclosure.h` / `Private/MikdashEnclosure.cpp` (`AMikdashEnclosure`)
* `InitialState` default **Yechezkel**; `CyclePrecinctState` order YECHEZKEL → MODERN → OVERLAY.
* `WorldCmPerAmah` (50 / 48): square, clearances, heights and a uniform module scale (.96 on
  the candidate) all derive from it; `WallModuleLengthAmot`, `OverlaySpacingAmot` replace the
  cm properties.
* Terrain-following: `GroundProfileStepsPerSide`, `GroundProfileHighZCm[]`,
  `GroundProfileLowZCm[]` baked by the release script; every wall/gate/corner instance at its
  own Z from `GroundSpan`; new `FoundationModuleMesh` + `FoundationInstances` HISM (one box per
  module, scaled in Z to the substructure depth); overlay band and marker lights follow the
  ground too. Malformed/empty profile → level plane, logged, reported by
  `GetGroundProfileStatus()`.
* Exact hide set: `ExplicitHideLabels[]` and `ExplicitHideMeshNames[]` (labels can be empty in
  a cooked build; the mesh an actor renders cannot). A label matched by more than one actor is
  refused (all copies stay visible) and counted. When both lists are empty the old geometric
  centroid rule remains as the fallback. `GetHideListResolution`, `GetHideSetFingerprint`.
* Readback API (numbers, not screenshots): `MeasureWithoutHiding()` (gathers + builds the ring
  without touching any building's visibility — the commandlet readback), `GetOuterFacesCm`,
  `GetWallBaseZRangeCm(side)`, `GetDeepestFoundationCm(side)`, `GetInstanceCounts`,
  `GetOverlayInstanceCount`.
* Written against the 5.8 headers (`AddInstance(FTransform, bWorldSpace)`, `GetInstanceCount`,
  `GetActorLabel` is unguarded in 5.8 Actor.h) but NOT compiled here — the coordinator holds
  the editor/UBT. Verify with `python Scripts\verify.py --build` when nothing native is running.

## 2. Ground Z along each side (Main50, cm; Z 0 = 748 m a.s.l.)

Sources: `jerusalem.json` terrain grid (amot, 257 x 257, step 50 amot, origin −6400; UE =
((x+17.5097)·50, (y−0.5513)·50), Z = h·50), the frozen level grid (`jerusalem-meshes.json`
Terrain 0, sha `cec2748b…`, the source of the 256 tiles), and the four FutureMountCut tile
receipts (the west and north walls pass through them: 1,767 of 7,212 samples). Grids agree to
2 cm along the whole ring; the Haram edit band does not reach the wall line.

| side | ground under wall (m a.s.l.) | plinth Z range | deepest substructure | largest step between plinths |
|---|---|---|---|---|
| north | −4933..+5680 cm (698.7–804.8) | −4861..+5680 | 656 cm, module 119 (NE, Olives) | 450 cm |
| east | −14668..+6061 (601.3–808.6) | −14628..+6059 | 691 cm, module 35 | 632 cm |
| south | −14712..−2906 (600.9–718.9) | −14670..−2906 | **1043 cm, module 85** (Kidron gorge bank) | 950 cm |
| west | −8978..+1691 (658.2–764.9) | −8852..+1691 | 852 cm, module 20 (Hinnom head) | 773 cm |

Candidate48: north −4832..+5733, east −13185..+6213, south −13634..−1950, west −8763..+1691
(plinths); deepest 948 cm (east, module 31). The Kidron crossings (east and south) drop
100–200 m; the sources say nothing about foundations there — the substructure is AUTHORED and
labelled so in every receipt.

## 3. Gates (count certain, Mishkenei Elyon 196 m.2; opening 10 x 50, thickness = wall, certain, book pp. 115-117; positions AUTHORED)

| gate | rule | Main50 (cm) | threshold m a.s.l. | Candidate48 (cm) |
|---|---|---|---|---|
| E | Temple E-W axis, world Y 0 — the axis of the court east gate (X 8600) and the walking start [2016, 0]; Yechezkel 42:15 measures out through it | (116900, 0) | 783.6 | (112224, 0) |
| N | Temple N-S axis, world X 0 | (0, −33150) | 743.5 | (0, −31824) |
| W | Temple E-W axis, world Y 0 | (−33100, 0) | 751.3 | (−31776, 0) |
| S1 | one third from the SW corner | (16900, 116850) | 683.5 | (16224, 112176) |
| S2 | two thirds from the SW corner | (66900, 116850) | 694.3 | (64224, 112176) |

The E gate is on the Temple axis by construction (`GetSquare` + `FractionAlongSide(TempleAxis)`)
on both maps. Note for the cinematic owner: the CURRENT legacy intro path
(`MikdashSceneUnitsMath.h LegacyIntroPoints`) enters from the WEST — it crosses the west wall
near Y ≈ +420 m at Z 42–51 m, well above the 3 m wall and the 25 m gate opening — so it neither
passes through a gate nor collides with the ring; an approach through the east gate from the
Olives (784 m, descending into the Kidron and up to the Mount) would be a new path.

## 4. Hidden actors (exact, per actor; policy `hide_if_any_inside`, recorded)

| set | Main50 | Candidate48 |
|---|---|---|
| `SM_JerusalemBuildings_*` (OSM cells, from frozen `buildings-manifest.json` components → cells) | 207 | 200 |
| `RELEASE_OldCityFacades_*` (facades-manifest per-building OSM ids) | 42 | 41 |
| `RELEASE_OldCityInfill_*` (follows its cell) | 30 | 29 |
| **total actors hidden** | **279** | **270** |
| OSM buildings inside by area centroid (of 11,437) | 1,914 | 1,700 |
| cut cells hidden / collateral outside the wall | 61 cells; 429 OSM components + 314 facade buildings | 53; 573 + 345 |
| label fingerprint (FNV-1a) | `259b9b496efe8f3d` | `e21f16f70c7a8dc7` |

Cut-cell decision: HIDE if any building in the cell is inside (nothing modern stands inside
the precinct); alternatives computed and recorded (majority: 239 / 208; keep: 213 / 208).
Recommended follow-up: SPLIT the cut cells at the wall line (native re-batch) or MASK the
context materials by world position; both recover the collateral. Never delete.

## 5. Exact commandlets (serial; never while another native job runs; coordinator only)

Main map:
```
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\Mikdash\Working-5.8\MikdashCourtyardV3\MikdashCourtyardV3.uproject" -run=pythonscript -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_enclosure.py" -unattended -nullrhi -EnclosureTarget=Main50 -abslog="C:/Mikdash/Working-5.8/Release-Enclosure-Main50-01.log"
```
Candidate:
```
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\Mikdash\Working-5.8\MikdashCourtyardV3\MikdashCourtyardV3.uproject" -run=pythonscript -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_enclosure.py" -unattended -nullrhi -EnclosureTarget=Candidate48 -abslog="C:/Mikdash/Working-5.8/Release-Enclosure-Candidate48-01.log"
```
Add `-EnclosureCountOnly=1` for a measurement-only pass (map untouched). Default state is
`yechezkel`; `-EnclosureState=modern|overlay` overrides. Requires the plugin rebuilt first;
otherwise the meshes import and the actor is recorded as an omission. Offline preview without
Unreal: `python Scripts\release_enclosure.py` (both targets; passed).

## 6. Needs a human / the coordinator

1. Compile (`verify.py --build`) — the actor and header were written against the 5.8 headers,
   not built here.
2. Bind the cycle key: `CyclePrecinctState` is BlueprintCallable; no C++/Config binding exists
   in MikdashRuntime (only Escape/F2/photo-mode keys are bound). Suggest one key in the front end.
3. Overlay material: none exists with `Opacity`/`Emissive` scalars; the band renders with the
   mesh default until one is authored and set in the spec. Wall uses `MI_PBR_LimestoneAshlar`
   (no `DissolveAmount`, so it cuts rather than dissolves).
4. Cut-cell collateral: decide between split (native re-import of 61 + 12 cells) and a
   world-position mask on the context materials.
5. Intro path through the east gate (§3) is a cinematic-owner decision.
6. Candidate48 hide list was computed from the frozen partition; the release script proves each
   label resolves in the candidate map at run time (refuses otherwise).
