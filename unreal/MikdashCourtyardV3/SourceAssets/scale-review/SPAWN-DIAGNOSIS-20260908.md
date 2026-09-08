# Resident spawn refusals on the 48 cm candidate — real-RHI PIE diagnosis (2026-09-08)

Map: `/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough` (SHA-256 before any change `8dc55f79b3dbcfe0ba7a15c41b3fb2da5be108766aab5a2cf7a9aae46f8a8f89`). Main was never opened for writing.

Evidence receipt: `SourceAssets/scale-review/spawn-diagnosis-20260908T184544564223Z.json`, external log `C:\Mikdash\Working-5.8\Fable-SpawnDiag-03-20260908.log` (D3D12 / RTX 2070, actual PIE, `mapBytesUnchanged` and `mainBytesUnchanged` true, no user save touched, isolated prefix `FableProbe_SpawnDiag_03`). Two earlier receipts (`...184033974271Z`, `...184241124382Z`) are preserved API-failure receipts (`break_hit_result` not exposed to Python; HitResult must be read with `to_dict()`).

Method: for every people-v3 profile the script `Scripts/diagnose_candidate_spawns.py` recomputed the selected48 waypoint 0 exactly as `PopulationSceneMath.h` does (outer-court x 0.96, mount-deck metric, the three signature-locked +25 cm extensions) and ran the spawner's own query: a 34 x 96 capsule on the **Pawn** profile centred at feet + 96 (`capsule_trace_multi_by_profile`, 1 cm vertical sweep, so initial overlaps are reported with their component). Floor (Visibility, ±30 cm), ceiling (Pawn, up 500 cm), 12 horizontal Pawn probes, a sweep of every route leg and floor samples every 100 cm were added. Hits whose only contact is the Z 288 floor itself are not blockers. Result: the capsule verdict agreed with the spawner for **24 of 24** profiles (15 clear/spawned, 9 blocked/refused). PIE reproduced `24 authored, 15 walking, 9 skipped`.

## The real mechanism (not the AABB trap)

All 2,633 architecture meshes use `CTF_USE_COMPLEX_AS_SIMPLE` with no simple primitives, so a capsule collides only where it **crosses a face**. The inner-court supporting platform (`SM_0128`, 12 triangles, box ±2688 x ±2688, Z 288..479.04 at 48 cm) and the cell plinths are closed hollow shells: a body whose feet stand on the Z 288 outer-court floor *inside* the shell footprint spawns as long as its head (feet + 192 = 480) stays below the shell top. At legacy 50 cm the platform top was 499 and the plinth tops 499, leaving 7 cm; at 48 cm the tops are 479.04, **0.96 cm below the capsule top**, so every profile standing under a shell now penetrates its top face. Everything else that blocks is a genuine face: the Inner court clear floor underside (460.8), footings/jambs whose undersides sit exactly at 480, the west terrace step treads/risers (paving union, tread at Z 312 for X ≤ 1608), and the western outer-court foundation face (X 1512).

Seven of the nine were **already refused in the main 50 cm map** (`Astra-Groups-Main03-20260908.log`: 17 walking, 7 skipped). Only Miryam and Gad are new at 48; both are the 0.96 cm head-through-shell-top case.

## Per-resident findings (selected48 feet; legacy feet in brackets)

| Resident | Waypoint 0 at 48 (legacy) | What the capsule actually hits | Also blocked in main? | Fix class |
|---|---|---|---|---|
| Yoav ben Shimi | (1608, 1008, 288) [(1675,1050,300)] | Inner court clear floor underside Z 460.8 (ceiling 170.8 cm, box X 1608..2400, ±2400); Inner court supporting platform top 479.04; Duchan rise 1 underside 480. Whole loop 1608..3000 x 1008..2640 inside the platform shell and E cell plinth; 4/4 legs blocked | yes | genuine conflict — route redesign (human decision) |
| Miryam bas Elyakim | (3384, 1008, 288) [(3525,1050,300)] | Inner E cell supporting plinth top 479.04 (shell X 2688..3456, Y 360..2184); doorway front underside at 480 (ceiling 190). West edge of loop inside the plinth; legs 0 and 3 blocked | no (spawned, 7 cm head clearance) | data — move loop east (applied) |
| Tzipporah bas Menachem | (1608, 3408, 288) [(1675,3550,300)] | West terrace bottom step tread Z 312 (paving/transition union, X ≤ 1608); ceiling 120 cm under Inner S cell plinth (X 360..2184, Y 2688..3456, underside 408). Legs 0, 2, 3 blocked | yes | data — loop must move east of X 2218 (S plinth) — *not applied*, see below |
| Gad ben Peleth | (1608, -2640, 288) [(1675,-2750,300)] | Inner court supporting platform top 479.04; East strip wall footing underside 480 (X 1608..2400, Y -2688..-2400). Whole loop inside platform shell and E cell plinth; 4/4 legs blocked | no (spawned; loops blocked) | genuine conflict — route redesign |
| Techiya bas Nadav | (1608, -5040, 288) [(1675,-5250,300)] | West terrace bottom step tread Z 312 (X ≤ 1608). Leg 2/3 also run under the Inner N cell plinth overhang (X ≤ 2184, Y -3456..-2688, underside 408) | yes | data — move loop east/south (applied) |
| Pinchas ben Achituv | (2352, 2016, 288) [(2450,2100,300)] | Inner court clear floor underside 460.8; platform top 479.04. West edge inside platform and E cell plinth; legs 0 and 3 blocked | yes | data — move west edge east (applied) |
| Uriel ben Shemaya | (2400, 1680, 288) [(2500,1750,300)] | Inner court clear floor underside 460.8; platform top 479.04; Inner eastern gate wall jamb 1 underside 480 (X 2400..2688) — he stands under the inner east gate jamb | yes | data — move west edge east (applied) |
| Rivka bas Yoezer | (1488, -3385, 288) [(1550,-3500,300)] | Western outer court foundation east face X 1512 (normal +X, Z 288..407) and paving union face X 1488: she stands in the terrace riser; ceiling 120 cm under Inner N cell plinth. 4/4 legs blocked (foundation, N and E plinths) | yes | genuine conflict **and** C++: route signature-locked by `TryAuthoredRouteExtension` |
| Nechemya ben Tzuriel | (1584, 3552, 288) [(1650,3700,300)] | Standing on the bottom terrace step: floor trace hits the paving union at Z 312 (feet 288); capsule side hits the next riser at X 1584. Leg 3 (X = 1584) fails 19/19 floor samples | yes | data (+150 cm X shift would clear it) **but** C++: signature-locked |

Nearest-clear-spot search (25 cm grid to 400 cm, floor + capsule, inside the zone) found **no** clear spot for any of the nine: each sits well inside a shell, under an overhang, or on the steps.

Residents that spawn but cannot walk their loop (legs swept, not previously reported): Devorah (legs 2/3, E cell plinth), Yedidya (legs 2/3, E cell plinth), Assaf (legs 2/3, plinth and platform). Their west edges (X 3384 / 2688 / 2448 at 48) are inside or against the same shells. The 15 "walking" residents are therefore not 15 free loops.

## Other population actor (`RELEASE_ResidentPopulation`, five pilot bodies)

Two independent refusals, both measured:

1. `ExtendedRouteLookTargets[0]` and `[4]` are `(5000, 1180, 300)` ("rejoin the visiting group"). `PopulationSceneMath.h::TryLook` only classifies `(11500,0,0)` metric and `(0|7800,0,300)`, `(8600,0,0)` Temple, so the extended route is refused as "unclassified converted points". All five extended waypoints convert to clear floor at 48 (probed). Fix is C++ (add the group anchor to the Temple allowlist) or an authored gaze change — **not applied**.
2. The five placed bodies still stand at legacy feet (4900,1000,300.001) etc. — 196–217 cm from their converted supports (4704,960,288)… — so `InitializeReviewedPilot` fails its 3 cm start check and the population "remains stopped". Converted supports and first 80 cm legs are clear with the floor at 288. Fix is data (move five actors) — applied by `release_candidate_spawn_fix.py`.

## Fix applied (candidate only) — see `candidate-spawn-fix-*.json`

`Scripts/release_candidate_spawn_fix.py` (+ spec) stages `Content/Distribution/People/people-candidate48.json` (people-v3, same roles/dialogue/pauses/gaze, four routes moved in legacy source coordinates), repoints only the candidate's `RELEASE_PeopleV3Population.people_directory_file`, moves the five pilot bodies to converted supports, checkpoints to `C:\Mikdash\Working-5.8\ReviewCheckpoints\SpawnFix48-<stamp>\`, saves, hashes, reopens, then runs PIE and records what actually spawned. The shared `people.json` and the main map are untouched.

Route edits (legacy cm, Z 300):
- Miryam: 3700..5150 x 1050..2750 (whole loop +175 X; 96 cm beyond radius from the E plinth face at 48).
- Techiya: 1775..3375 x -5250..-3700 (96 cm from the step edge and the N plinth face at 48).
- Pinchas: west edge 2450 → 4000 (loop 4000..6050 x 2100..4300).
- Uriel: west edge 2500 → 4000 (loop 4000..5700 x 1750..4350).

Not applied and why: Yoav and Gad need entirely new loops (theirs lie inside the inner-court platform/plinth shells — the authored pilgrim envelope `x 1500..7000, 900 <= |y| < 6000` is wrong for |Y| < 2800, where X < 2800 (legacy) is the raised inner-court platform); Tzipporah's loop would have to move ≥ 700 cm east to clear the S cell plinth overhang, overlapping Elchanan's loop — a layout decision; Rivka and Nechemya cannot be changed in data without a C++ change because `TryAuthoredRouteExtension` refuses any deviation from their reviewed source signature. Suggested C++ (not mine to make): let the extension helper return `true` without extending when a locked ID's signature no longer matches, so the general validator decides; add `(5000,1180,300)` to the `TryLook` Temple allowlist.

## Result of the applied fix (actual PIE, `candidate-spawn-fix-20260908T192321112132Z.json`, log `Fable-SpawnFix-02-20260908.log`)

- Candidate `.umap` SHA-256 before `8dc55f79b3dbcfe0ba7a15c41b3fb2da5be108766aab5a2cf7a9aae46f8a8f89`, after save `20e8903694e5d61c8b47c8303f37fe0825b359d94b5ba73543c5c6700c4d0a1a`, unchanged by the PIE run. Checkpoint `C:\Mikdash\Working-5.8\ReviewCheckpoints\SpawnFix48-20260908T192321112132Z\BeforeSpawnFix.umap` (+ reference `people.json`). Main `8e78923f…` and staged `people.json` `88d6de22…` unchanged; no user save file touched (isolated prefix `FableProbe_SpawnFix_02`).
- `people-candidate48.json` SHA-256 `29f4ac2ca7a1bb6e7a9d2135c7dcea615d45c305aed488020d502bbcbee987ae`; `RELEASE_PeopleV3Population.people_directory_file` read back after reopen as `Distribution/People/people-candidate48.json`. Five pilot bodies read back at actor Z 384 over converted feet (4704,960,288), (4915.2,1075.2,288), (4780.8,1209.6,288), (5030.4,1276.8,288), (4569.6,1132.8,288). The scene-snapshot helper does not diff string properties, so `sceneChanges` lists only the five bodies; the actor repoint is proven by readback.
- Observed: `Directory 'people-v3': 24 authored, 19 walking, 5 skipped` (was 15/9). Miryam, Techiya, Pinchas and Uriel spawned with **0 blocked legs and 0 floor failures** on their new loops. Still refused, for the reasons above: Yoav, Tzipporah, Gad, Rivka, Nechemya. Capsule verdict again matched the spawner 24/24.
- Pilot population: `is_population_active` true, 5 living, all five converted supports clear with floor at 288; extended route still "ignored: unclassified converted points" (C++ allowlist), so the five bodies run the short 80 cm pilot.
- Preserved failure receipts: `candidate-spawn-fix-20260908T192108563019Z.json` + `candidate-spawn-fix-setup-failure-20260908T192141062885Z.json` (first apply refused itself on a staged-file hash mismatch caused by CRLF text-mode writing; map untouched, checkpoint `SpawnFix48-20260908T192108563019Z` contains only the unchanged before-copy).

Not established: navmesh, visual acceptance, whether residents actually complete laps over time, or any main-map behaviour. The candidate remains unpromoted.
