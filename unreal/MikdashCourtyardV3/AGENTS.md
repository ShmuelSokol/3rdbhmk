## Walter skin texture inputs — 18 September 2026

extract_walter_skin_maps.py extracts three embedded PNGs from the installed Walter
preset without loading Unreal, validates every chunk CRC and dimensions, and pins
the reviewed albedo RGB-pixel hash. This avoids relying on an unpublished reference
PNG in the clone. Fresh extraction matches all three saved maps. Destination must
be fresh; no existing texture can be overwritten. KohenSkinV2/textures has albedo,
normal and cavity plus hashes. The normal visibly carries wrinkles/pores; the cavity
texture is RGB-packed, NOT a grayscale AO image. Native audit resolved the packed
paths; Study03 now imports these maps and builds a skin material with fresh-process
readback. No head binding or rendered acceptance yet; the released build is unchanged.

## Kohen neck color study — 18 September 2026

build_kohen_neck_tone_study.py reads the hash-pinned approved Walter GLB and writes
a FRESH color-only study (KohenSkinV2). The lower-neck/jaw RGB ratio is measured
in linear space; smoothstep blends between author Z150 and Z156 cm. It preserves
local variation rather than replacing the neck with a flat color. Exactly 2,139
vertices are affected; tests read both GLBs and prove all non-color accessors and
the face/alpha remain unchanged. This is NOT native import or visual acceptance;
normal/cavity skin master and in-engine review remain required before adoption.
Offline paired previews show the color-only change is visually subtle because the
beard/collar cover most of this region. The exported KG_Hair reaches author Z142.165
cm (head minimum Z142.182); beard_shell.mask has no lower-height cutoff. Investigate
this neck-covering shell before attributing the whole pale area to the face atlas.
This is source/offline evidence, not a new engine diagnosis or approved beard edit.

## Garment measurement profiling — 18 September 2026

The current measure_kohen_garment_clearance.py skins only robe, leg and outer garment
parts (17,016 Kohen vertices), not the head/beard described in the older handoff.
Short idle profiling measured 28.07 s in distance/parity tests versus 0.0183 s skinning.
Conservative triangle AABB pruning reduces the same three-frame run from 30.5 s to
8.9 s with unchanged measurements. Sampled surface vertices bound distance above;
triangle boxes bound it below, with retained order preserving nearest-face ties.
Full optimized idle now passes 97 frames at 30 Hz, zero measured intersections in
249.2 s. Full original comparison finished at 673.0 s and every reported idle
measurement matches exactly (2.70x faster). Full 60 Hz tend completed: 601 samples over ten seconds, zero measured leg/robe and inner/outer garment intersections. Full walk measured 288 samples at 240 Hz: zero leg/robe intersection, but inner/outer garments intersect by up to 0.388 cm at t=0.2958 s, rest Z36 cm. This remains an open defect requiring correction and native visual review. Source checker
verify_kohen_clearance_source.py matches all 33,312 garment/leg triangles in the
exported Kohen GLB by exact float32 position/weight, material and winding. Clone
was missing this generated source mesh; copy the exact 7,939,512-byte GLB with SHA
173a0971089f20e9685a4c80b5c55c0ea214e2b55f4bf910b91e3a916685a09c.
Five differential/regression tests cover actual posed garments, random geometry,
degenerate faces, skinning parity and per-body policy reset. Full clips and native
visual clearance remain separate acceptance work; short profiles are not clip gates.
Reset LEG_PREFIXES/outer garment policy on every body_parts call: resident settings
previously leaked into subsequent Kohen/stand-in runs in the same process.

## Finish-line continuation and online walkthrough — 18 September 2026

The owner has explicitly resumed continuous work toward the finish line; historical
stop/pause entries in INTEGRATION-QUEUE.md are superseded by this request. Track work
and acceptance in FINISH-LINE.md. Online sharing means visitors independently WALK
and NAVIGATE the actual scene from a browser, including phones. A gallery, video,
download-only page or multiple spectators sharing one camera is not the deliverable.
Pixel Streaming is an initial implementation direction, not a deployed service.
No paid cloud spending or rock/Temple elevation change is authorized. The owner approved
deleting only Checkpoint-cp01-20260909T221426Z, Checkpoint-cp02b-20260910T003728Z,
and Checkpoint-cp03-20260910T025420Z. Automatic approval review blocked that deletion
with "blocked by policy"; no files were deleted. Other archives remain protected.

Initial runtime audit refused safely before launching: less than 9 GiB free commit.
mc-fw-host measured 10.35 GiB private memory and C: approximately 9.1 GiB free disk.
Do not bypass the established memory guard, stop security services, restart the user's
remote machine or delete archives to force progress. Continue source/offline work;
request a specific cleanup decision and arrange a user-controlled restart if needed.

## S5 Haram precinct accepted — 16 September 2026

Verification runner: run active-tree and publication-tree verify.py sequentially.
Its Python compile checks share temporary .pyc names; parallel gates can collide
on Windows atomic rename even when both source trees are valid.


Candidate48 now uses the mapped Haram perimeter, 13 derived gate positions,
111,848.53 m2 of paving and 586 authored access treads. Temple transforms and Z0
remain fixed; Kotel paving and retaining closure survive every precinct state.
Both sourced square readings remain implemented for maps that do not opt in.

Final map: 9daa88a181a44009467ab6a3f296dcff3ed9ff8b93500ddee593adc84ff0367e.
Build: C:/Mikdash/Builds/Checkpoint-haram-S5-02-20260916T171759Z.
Acceptance: SourceAssets/enclosure-review/HaramPrecinctV1/acceptance.json.
All 13 packaged character routes pass with actual waypoint events, zero stalls and
grounded paving endpoints. Three GPU views pass the Modern / Yechezkel / Overlay /
Modern-again round trip, all 115 floor/step probes, and normal process exit.
Fresh native verification: 122 built actors, 20 phase originals, 12 exterior-surface
proofs. Quick gate 6/6, Haram tests 7/7 in active and publication trees, math suites
32/32; both C++ targets compiled. Main50 and outside surfaces are preserved.

AccessV4 uses triplanar stone; AccessV3's XY paving stretched on vertical risers.
The Council route also needed a corridor-only street cut. S5-01 failed these two
acceptance points; its evidence and all earlier checkpoints are retained.
Raw diagnostic logs remain local. Gate dimensions/access are authored, mapped
locations derived; no current access permissions or surveyed profiles are claimed.

Next: Kohen Gadol skin/pale neck, then garments, then six residents; idle/tend
clearance and its measurement tool; Old City negative-space paving. Rock elevation
and archive pruning still need the owner's decisions. No lowering or deletion done.
Visual polish: the thin exposed apron edge retains floor-only texture mapping;
AccessV4 fixes the stair shell, not this separate threshold slab edge.

The entries below are historical implementation notes, including superseded counts
and pending-work statements. The acceptance receipt above is the current status.

## S5 final source verification — 2026-09-16 17:16 UTC

Candidate48 is now 9daa88a181a44009467ab6a3f296dcff3ed9ff8b93500ddee593adc84ff0367e.
Fresh native verify 20260916T171415824824Z passed: 122 built / 20 original actors,
12 full exterior-surface proofs, 8,596 other actors unchanged. Main50 remains unchanged.
AccessV4 changes the stair finish only; all vertex/normal/face records equal AccessV3.
Council source replay stair-20260916T171518660Z.json reached all three waypoints,
zero stalls, grounded at feet Z 2.6 cm on the +0.5 cm paving. Source replay is not
packaged acceptance. Replacement cook and final rendered/packaged replay remain owed.
## S5 Council Gate obstruction — 2026-09-16

The S5-01 packaged batch passed 12/13 routes. Council Gate failed with five stuck
samples: SM_Jerusalem_StonePaths_03_Grid_N002_N002 crosses the descending flight.
This street straddles the ring, so hiding its entire actor would remove outside road.
Use a corridor-only TRIM_INSIDE twin with the same full-surface preservation proof
as the open platform twins. Keep the failed route/batch receipts. The walk probe can
advance its index after repeated stalls: a final reached=3/3 is not acceptance;
require three actual reached events, zero stuck events and a grounded deck endpoint.
## S5 stair finish correction — 2026-09-16

Packaged S5-01 G1 view revealed stretched stripes on vertical stair risers: the
M_PrecinctPlaza_Paving shader projects only world XY. Do not use that floor-only
shader on closed stair shells. AccessV4 keeps AccessV3 geometry and collision but
uses the existing triplanar MI_PrecinctPlaza_Ashlar stone finish. It is a fresh asset;
S5-01 and AccessV3 remain preserved. New import/apply/cook and visual check are owed.
S5-01 passed three four-state GPU probes (overview, Kotel plaza, Mughrabi), all 115
floor probes and normal exits. Kotel paving survives in every state. These checks
establish geometry/state behavior but do not accept the stretched stair finish.
## S5 Haram precinct — packaged acceptance underway, 2026-09-16

Fresh native verification passed for Candidate48 2331c2a4...a1df7: 121 built actors,
19 phase originals, and all eleven wall/platform passage twins preserve exterior
source surfaces/attributes. Main50 remains 2b82ae66...d4c6; Temple transforms and Z0
remain unchanged. Mughrabi and Bani Ghanem source character routes reached all three
waypoints with zero stuck events after local wall/platform corridor cuts.
Fresh filesystem cook Checkpoint-haram-S5-01-20260916T162935Z succeeded (9,113 packages).
Packaged GPU state/photo checks and all thirteen character routes are still required.
The entries below record superseded failures and intermediate counts chronologically;
they are not current acceptance claims.
## S5 Haram precinct — implementation history, 2026-09-16

Publication audit found HEAD's KotelClosureRuntime.cpp already references
KotelClosureLimestone, while its header declaration existed only in the active tree.
Include that non-reflected weak-pointer member with the S5 header; it is required
for the published source to compile and is present in both verified build targets.

Map bd598596 passed fresh native verification and all 115 downward surface probes
in the four-state source replay. Actual Mughrabi character walking then stalled on
the second riser (stair-20260916T154114841Z.json). A downward trace is NOT stair
acceptance. AccessV3 replaces adjacent tread boxes with one closed shell per flight,
removing buried shared faces; this hypothesis still requires a fresh character replay.
The independent shell check requires one reversed partner per welded directed edge.
AccessV3 shell still stalls at the same riser (stair-20260916T154947392Z.json), so
shared faces were not the cause. The HaramAccess diagnostic now logs read-only
up/forward/down capsule sweeps, floor distance and step policy to isolate rejection.
The diagnostic replay 155702782Z identifies the actual blocker: the upward sweep
starts penetrating CityWalls_04_Grid_N002_P002 while the forward trace hits the new
stair. Step policy/base are allowed. Existing wall batches must receive local gate
passages; hiding entire batches would damage surrounding city walls. Nine actual
map wall actors overlap the corridors. Wall twins are being made in a fresh namespace,
with originals retained for Modern/Overlay and preservation guards before any save.
Wall twins passed fresh per-triangle surface verification: source UV sets, normals,
colours, material IDs and winding retained; exterior fragment area equals original
area minus the exact gate-box intersection. New caps are confined to cutter planes.
Use keyword arguments for unreal.Rotator (pitch/yaw/roll), never positional ordering;
measure the actual native cutter bounds before boolean work. The position guard
rejected the earlier wrong orientation before any twin was saved.
The next replay 161316271Z cleared the city wall but exposed the old Mount platform
skirt. Its top also spans the access routes. Preserve these open source surfaces via
TRIM_INSIDE corridor twins, not a whole-platform hide. Full eleven-mesh verification
passes source attributes/winding, disjoint fragment coverage and exact cutter UNION
area (expanded runouts can overlap). On thin fan triangles a fixed barycentric epsilon
is not a fixed distance: use the declared 0.02 cm plane/edge tolerance via altitude.
One rejected point was only about 0.001 cm outside an edge after float32 persistence.

Runtime V2 probing found 35 stair surface failures from Nanite's AUTO fallback and
one paving obstruction from StonePaths_03_Grid_N001_N002 (+17 cm). NaniteHelper.cpp
CorrectFallbackSettings overrides numeric fallback values in Auto mode: use explicit
NaniteFallbackTarget.PERCENT_TRIANGLES with 1.0, not just relative_error=0. V3 is the
fresh corrected namespace. Seven existing path meshes whose complete bounds are
inside the ring join HaramRingOriginal; their outside counterparts are untouched.
Expected original count becomes eight (seven paths and the northwest terrain tile).

Uncooked GPU preview exceeded its 16 GiB private cap. The wrapper's owned-child cleanup
also compared slash variants; normalize exe paths with Resolve-Path before comparison.
Root stopped that owned process after inspection. Preserve the failed receipt. Use
headless source checks and packaged GPU acceptance rather than raising preview limits.

The first pilot's OBJ normals were genuinely missing (source zero AND recompute off).
HaramPrecinctV2 is the corrected native namespace: explicit per-face vn records,
clockwise native winding and upward deck normals verified on import. V1 assets and
map checkpoints remain preserved; do not reuse V1 or overwrite it. Review artifacts
remain under enclosure-review/HaramPrecinctV1, with superseded-source-v1 retained.

Native import guard found that FutureMount's frozen JSON is pre-import precision:
native height differs by up to 0.0066 cm, normals 0.000573, colours 0.003912.
Generate the new cut from an extracted, hash-pinned native source instead. Preserve
the actually rendered attributes outside the ring; do not relax corner checks.
Compare OBJ/native triangle positions after float32 conversion on both sides:
rounding doubles against floats at decimal bucket boundaries falsely failed gates.
Both runtime targets and all 32 math suites pass after the explicit TObjectPtr loop
type fix. Native terrain import, placement and packaged acceptance remain pending.

S5 native solids and terrain import passed; independent surface tests checked 320
inside / 72,304 outside stations, outside height error below 1e-12 cm. For Pawn
readback use CollisionResponseType.ECR_BLOCK: EngineTypes.h gives ECollisionResponse
the ScriptName CollisionResponseType. CollisionResponse is a different exposed type.
Two placement checks refused before save while resolving this; original map unchanged.

Candidate48 S5 save completed at 030b7046...f15b: 109 new actors, 8,615 other
actors compared unchanged, old approach actor retired. Fresh verify/visual acceptance
still pending. OBJ-only source descriptions have zero normals; inspect saved LOD
recompute_normals before treating this as a render defect. UE clockwise winding is
the adapter's reversed face order, distinct from the generator's positive-volume order.

create_haram_precinct.py plans inside the frozen 66-point ring: 13 named OSM gate
footprints, 111,848.5 m2 of paving outside the accepted court, 586 local access treads,
maximum retaining 39.26 m. Gate profiles/access are AUTHORED; footprint projections are
DERIVED, and the plan records every offset. Modern access permissions are not inferred.
Temple transforms and Z0 remain fixed (0.5 cm paving finish avoids coplanar ground).
Only the northwest FutureMount terrain tile needs a new cut twin; Kotel V3 is untouched.
HaramRingBuilt actors hide in Modern/Overlay; HaramRingOriginal hides in the built state.
UseHaramOutline replaces the square renderer only on the opted-in Candidate48 map;
FSquare/readings remain implemented. Old PrecinctApproachV1 is retired only in that map.

Status: OFFLINE CHECKS, native import/placement and visual acceptance pending. Never claim
this plan is shipped. Python generation needs shapely==2.1.2; local wheel is in ../S5Deps.
A tiny disconnected inset pocket (0.247 m2) becomes masonry. Gates must fit a real wall
span; snapping a 4.8 m opening onto a centimetre-long OSM notch fails containment.
## Kotel restore acceptance — 2026-09-16

Fresh filesystem cook kotel-restore02 succeeded; native Modern / Yechezkel / Overlay /
Modern-again visibility and collision passed. K1 PNGs show paving instead of the S4c dirt
slope and the retaining closure remains visible. Candidate48 is 2640afae...7448; all other
maps and reused assets unchanged. M_StreetTrees_Bark still falls back in SM6 (also in S4c);
this is not a whole-scene visual acceptance. See the acceptance receipt for exact hashes.

Kotel restore cook01 completed cooking but staging failed with HTTP NotFound for Zen
oplog attachments. Checkpoint-Build.ps1 now accepts opt-in -SkipZenStore, verified in
UE5.8 CookCommandlet.cpp, to recook to filesystem output without changing global config.
Use the bundled pwsh for checkpoint scripts: Windows PowerShell in the Codex environment
failed before cook because Get-FileHash was unavailable. Raw failure logs remain local.
## Kotel plaza after the plateau deck removal — 2026-09-16

With bBuildPlaza=false, ApplyStateTaggedActors must keep KotelPlazaCutTwin actors
visible and collidable in every precinct state. Apply this at runtime, not by removing
the constructor tag: saved maps carry the tag lists and KotelClosureRuntime validates
them. The retaining wall follows the cut terrain visibility. Preserve the old hide
behavior when bBuildPlaza=true. Both native probe paths now expect this conditional
policy. Both targets compile and 32/32 math suites pass. Packaged four-state native and visual acceptance passed: see SourceAssets/enclosure-review/HideSetV1/kotel-restore-acceptance.json.
Native inspection confirmed S4 also deleted RELEASE_KotelPlazaCut_07_08 and stripped
both phase tags from its original tile. The one-line runtime fix alone is insufficient.
restore_kotel_cut_after_plateau.py restores the existing V3 asset at identity, checkpoints
Candidate48, and hides the original in both phases. Never revert the Kotel cut with the
obsolete square precinct cut; their placement receipt shares tile 07_08 twice.
## ASSET ACCESS AFTER A MAP LOAD FLUSHES THE WHOLE LEVEL — 2026-09-16 06:xx UTC

**The rule: load the assets you need BEFORE you load the map, and cap static-mesh compile
concurrency.** `load_asset` on a static mesh while a big map is resident does not fetch one
mesh — it blocks on `FStaticMeshCompilingManager` and pulls the level's entire mesh set
through compilation at once. On this 16 GB box that is an instant OOM kill.

Measured on the precinct cell-split apply (Candidate48, 72 MB map, 8,606 actors, 7,860 meshes):

| run | sequence | flush lines | outcome |
|---|---|---:|---|
| preflight | `load_level`, then actor LABELS only | 0 | lived |
| probe | `load_asset`, **no map loaded** | 0 | lived |
| apply | `load_level`, **then** `load_asset` | 74–110 | **killed ×5** |
| apply (reordered) | preload assets, **then** `load_level` | 618 | lived, saved |
| verify | `-asyncstaticmeshcompilationmaxconcurrency=1` | **0** | lived |

Two independent levers, both confirmed:

1. **Order.** Resolve every material and mesh BEFORE `load_level`. The apply went from dying
   on entry to placing all 11 actors and saving. Do not enumerate level actors twice either —
   build one label→actor map and derive from it.
2. **Concurrency cap.** `-asyncstaticmeshcompilationmaxconcurrency=1` took the verify run from
   618 flush lines to **zero**. The flag form is parsed in
   `Engine/Source/Runtime/Engine/Private/AsyncCompilationHelpers.cpp:306` as
   `-async<Name>compilationmaxconcurrency=`, and `StaticMeshCompiler.cpp` registers the name
   as `staticmesh`. **Confirm the registered name in engine source before using it for another
   asset type — do not guess the flag.** A serial flush is slow, not fatal.

The flush itself is survivable: the terrain-cut revert ran 915 flush lines to completion. What
kills is entering the flush already carrying something.

**And the guard pattern earned its keep.** The script saves the map ONCE, at the end. Seven
kills, every one of them after the work had succeeded and before the write — and the map stayed
byte-identical at `8e8e1064…` throughout. Save once, at the end, always.

---

## A COUNT THAT MATCHES IS NOT A THING THAT MATCHES — 2026-09-16 04:xx UTC

**Hard rule, paid for on the precinct cell-split.** When you slice a batch apart — triangles
into buildings, instances into zones, rows into groups — **never accept a count as proof that
you sliced it in the right place.** Verify by POSITION, or by identity, or by something the
data itself can contradict. A matching count is the single most convincing wrong answer in
this codebase.

What happened. Each `SM_JerusalemBuildings_Grid_*` cell records `sourceComponentIds` and
`sourceTriangleIndices` into `jerusalem-meshes.json`. The components' triangle counts sum
**exactly** to the mesh's triangle count. The obvious split is therefore to walk
`sourceTriangleIndices` and cut it at each component's triangle count, in order. It runs
clean. It produces the right number of meshes, the right number of triangles in each, the
right vertex counts, and cell bounds that still match the manifest.

**It is wrong. The triangle list is not grouped by component.** A bounds check written to
guard the assumption refused on the first cut cell: component 7218 of
`SM_JerusalemBuildings_Grid_N001_N003` missed its own recorded `sourceBoundsAmos` by
**160.4 amot — 80 metres**.

Had the guard not been there, the pass would have shipped **buildings assembled out of other
buildings' walls**, and every downstream number would have agreed with it. Nothing in a
receipt, a triangle budget or a cook log would ever have caught it. Only a frame would have,
and only if someone happened to look at the right rooftop.

The fix, and the general shape of the fix: recover the grouping from the GEOMETRY rather than
from the ordering. The source is unwelded (`sourceVertexIndexRule` = `3*sourceTriangleIndex+corner`),
so triangles of one building share no vertex *index* — they share vertex *positions*. Union-find
over quantised positions recovers the islands; each island is then matched **one-to-one** to a
recorded component by bounds, with both the island count and the bijection asserted. Measured:
every island matched to better than 1e-4 amot, files read back to 1.8e-05 cm.

Generalise it: `Scripts/create_precinct_cell_split.py` is the worked example, but the rule is
not about that file. **If a slice can be checked against something independent of the way you
sliced it, check it, and make the check a refusal rather than a warning.**

---

## CityFacadeV1: stone facades with recessed openings on the 11,405 city buildings (material, not geometry) — 2026-09-11 10:5x UTC

**Measured first, then built.** `Scripts/measure_city_visibility.py` (offline 2.5D viewshed: exact
CitySource footprints and DEM, 4 m DSM, precinct deck + 6-amah wall and the YECHEZKEL hide set for
the deck, gates and approach flights, the whole modern city for the Kotel plaza; 2,880 rays x
1.5 km from 299 viewpoints). Receipt `SourceAssets/context-review/CityFacadeV1/visibility-latest.json`.
- Seen within 300 m of where a visitor walks: **901** buildings. **340** already carry
  OldCityFacadesV1 geometric shells; **561 are plain boxes**. Seen 300-800 m: 1,648. Beyond: 730.
  **Never seen from the ground: 8,126.** Within the dove's 1.5 km: 8,811.
- From the Kotel plaza: 110 seen within 300 m, **98 of them already shelled**. The plain boxes a
  visitor meets up close are mostly on the approaches (394) and over the deck wall (253).

**Built:** `M_CityFacadeV1` + `MI_CityFacade_CityStone` (`Scripts/release_city_facade.py`). The
M_Context_Building triplanar Custom nodes verbatim, then two procedural Custom nodes: ashlar
coursing with per-stone tone, windows / arched windows / doors / balcony doors on a per-wall grid,
a VIEW-DEPENDENT recess (back plane found along the camera vector, so reveals, soffit and sill
move with the viewer and carry their own world normals), shutters (some half open), iron
grilles, balcony rails, a few lattice screens, lintels / voussoirs / sills, rain stains, per-roof
tone. Variation per building from the per-building vertex colour, per wall from dot(P.xy, n.xy),
per roof from roof Z. No per-instance data, no texture sampling, no derivatives in the new code
(AA is analytic from PixelDepth; openings average out 220-800 m). Why a material: PERFORMANCE-BUDGET.md.

**Applied** on both maps as a retarget of exactly the components carrying the CityDetail retint:
Candidate48 **1,498/1,498** (receipt `native-city-facade-apply-candidate-20260911T094504048555Z.json`,
checkpoint `ReviewCheckpoints/CityFacade-apply-candidate-20260911T094504048555Z`), Main50 **1,498/1,498**
(`...-apply-main-20260911T104246240346Z.json`). Census after reopen exact; retint colour copied and
read back parameter-for-parameter; `used_with_nanite` and `used_with_instanced_static_meshes` read
back from disk; protected maps unchanged. Revert: `-CityFacadeRevert -CityFacadeTarget=<candidate|main>`.
Note: `release_city_detail.py -CityDetailRetintClear` clears ALL overrides on those components,
this one included.

**MODERN restore re-audited after the change:** Candidate48 hide list **269/0/0**, Main50 **278/0/0**,
`passed: true` on both, every tag ok (PrecinctCutOriginal unjudged in MODERN/OVERLAY by design).

**Cook evidence (cp21d, cooked by another agent from my post-apply Candidate48 c09d6a89...):** the
UAT log (UTF-16 - grep finds nothing until decoded) shows `Missing cached shadermap` for
M_CityFacadeV1 in SM6 and SM5, no SCW crash, no fallback, `Success - 0 error(s), 0 warning(s)`,
8,851 packages. cp22b was cooked from the same bytes.


**Frames, cp21c (before) vs cp21d (after, cooked from my post-apply map), same packaged cameras**
(`Scripts/capture_city_facade.ps1`, receipts `SourceAssets/visual-review/city-facade/city-facade-frames-*.json`,
metrics `metrics-cfbefore-cp21c-vs-cfafter-cp21d.json`; band = lower 60 % of frame):
- A2 Silwan approach: building-band detail x1.091, spread 103.7 -> 106.3, mean unchanged. Windows,
  shutters and roof tones now read on the plain-box slope. **The material's clear win.**
- A1 West gate x1.027, D1 dove 100 m x1.024, P1 aerial x1.009 (openings fade out by 800 m by
  design), K1 x0.997: little or nothing, because those views are dominated by shelled buildings.
- Frame time (static camera, median of last half of 700 frames): K1 18.81 -> 19.56, A1 18.31 -> 17.57,
  A2 18.38 -> 17.72, D1 24.27 -> 23.15, P1 17.95 -> 16.80 ms: inside run-to-run noise. The perf
  agent's long P1 captures (5,301 / 4,694 frames) on the same two builds: frame 17.47 -> 18.47 ms,
  GPU 16.62 -> 17.75 ms (+1.1 ms). Answered with an EARLY-OUT (fade == 0 on roofs and walls past
  800 m skips the opening maths): `-CityFacadeRebuild`, rebuilt in place 12:10Z, both .uassets
  checkpointed (`ReviewCheckpoints/CityFacade-rebuild-20260911T121040728100Z`), usage flags read back.
- K1 camera (-15500 19500 -1060) landed in an alley between shelled buildings, not on the deck. K2 is
  the PROVEN cp05b-08/N3 deck position turned west (-20732 19230 -814 6 175 0, V pre-key).

**The real reason the Kotel / Jewish Quarter view reads blind:** every OldCityFacadesV1 "opening" is
a picture-frame solid standing proud of the wall; nothing is cut, so each frame shows the box wall
(cropped K1). 98 of 110 buildings seen from the Kotel are shelled, so the box material cannot reach
them. Fix: **ShellOpeningsV1** (`Scripts/create_shell_openings.py` + `release_shell_openings.py`):
63,853 flat panels (53,344 rect + 6,858 arched windows, 2,000 rect + 1,651 arched doors), 144,724
triangles, 8 HISM actors, 2 cm off the box wall (24 cm reveal), stock-node PerInstanceRandom
glass / shutter / door material, no shadows, no collision, 700 m cull. Positions come from RE-RUNNING
the frozen generation and PROVING it matched (all 190 OBJs: triangles, vertices, bounds; window and
arched totals) - under UE's Python 3.11 only (system 32-bit Python flips js_hash arches). Zones from
`create_enclosure.hide_set` itself (41/29). Precinct-zone actors carry CityDetailZone_Precinct.
First candidate apply failed before save on `unreal.Transform(translation=)` TypeError (fixed, same
fallback as CityDetail); map unchanged.

**Pre-existing defect seen in A1 (NOT this pass):** CityDetail roof plant floats over bare ground just
outside the West gate in YECHEZKEL (solar heaters in cfbefore-cp21c-A1 AND cfafter-cp21d-A1). Up to
113 kept-zone CityDetail instances lie in 100 m cells the precinct hides (68 parapets, 12 solar,
9 tanks, 9 condensers, ...; an upper bound - binned by instance position, not by decorated building).
Recommended fix: re-zone CityDetail by the hide_set labels of the building actor each instance sits on.

**Landed (12:3x-12:5x UTC):** ShellOpeningsV1 on Candidate48 (`native-shell-openings-apply-candidate-20260911T123240206770Z.json`)
and Main50 (`...-apply-main-20260911T123440623805Z.json`): 63,853 placed = 63,853 read back after reopen,
8 actors, 0.0 cm transform error, shadows off, material chain resolved from disk, protected maps unchanged.
Audits AFTER the panels: Candidate48 hide list **269/0/0**, Main50 **278/0/0**, `passed: true`, every tag ok;
CityDetailZone_Precinct now counts 16 actors (12 CityDetail + 4 panel), hidden in YECHEZKEL, visible in
MODERN/OVERLAY. Census re-check: 1,498/1,498 components still on MI_CityFacade_CityStone after another
agent's Kotel plaza re-apply. Early-out proven in a real cook by cp22d (another agent, cooked after my
rebuild): cold SM6+SM5 shadermaps for M_CityFacadeV1, `Success - 0 error(s)`, checkpoint_playable.
**cp24** (`C:/Mikdash/Builds/Checkpoint-cp24-20260911T124738Z`): try 1 died on the documented first-cook
trap - SCW 0xC0000005 on the NEW M_ShellOpeningV1 (stock nodes, no Custom node), 1 queued job, fallback
compile, UAT exit 25; maps untouched. Try 2: `Success - 0 error(s), 0 warning(s)`, 8,857 packages, no
missing shadermap (served from the DDC the fallback wrote = its HLSL compiled). Status stays
`cook_archive_passed_smoke_pending`: Checkpoint-Build's smoke refused because a sibling agent's game was
running ("A build is already running"); the cp24 frame captures are the playability evidence.

## cp10/cp11: leaf cards are LEAF-SIZED, and the LOD schedule was 2x wrong — 2026-09-10 08:2x UTC

**SHIPPED BUILD: `C:\Mikdash\Builds\Checkpoint-cp11-20260910T080907Z`** (`checkpoint_playable`,
exit 0, 3.92 GB). cp10 is the same fix WITHOUT the palm-crown correction; prefer cp11.

**The frame verdict, first: the cards are fixed and the canopy now reads as canopy.**
`SourceAssets/visual-review/cp11g-veg-grove-*.png` (four views inside a real Kidron grove) show
an olive with a gnarled bole carrying a crown of small leaves, a fig with correctly large leaves,
and dwarf shrubs at dwarf-shrub scale. **No paddles anywhere.** At 7 m the camera is among leaves
instead of inside one. The cp10 cook is `checkpoint_playable`, exit 0,
`C:\Mikdash\Builds\Checkpoint-cp10-20260910T074110Z`, smoke playable at 18 s.

**WATCH OUT — the three standard cameras in `capture_vegetation_frames.ps1` no longer see any
vegetation.** `cp10-veg-*.png` are three frames of an empty plaza. That is NOT a regression: the
Candidate48 map changed under this pass (cp08 `9144cc15` -> cp09 `1e98e257` -> cp10 `7d1e1af6`)
when the plaza keep-out landed, and those cameras were framing exactly the on-deck trees it
removed. Any future vegetation review needs cameras in the groves, not on the deck. The four that
work are in the scratchpad copy; grove centre is about (25491, -43474, -2300) cm, which carries
olive, carob, cypress and date palm together.

### The palm needed a second pass: a crown is a SHUTTLECOCK, not a parasol

The first version of `build_palm` set `droop = -0.16 - 0.62*r**1.6` — always negative — so every
frond pointed out and DOWN. Measured offline: only **25%** of frond vertices sat above the bole
top and the crown was **275 cm** deep. cp10's grove frames caught it as a flat starburst. Now
`rank = hash**1.25; droop = 0.90 - 1.65*rank` spans +0.90 (upright inner fronds) to -0.75 (hanging
outer ones), with `length` tied to the same rank so the hanging fronds are the longest: **51%**
above the bole top, crown **463 cm** deep, mesh top 1556 cm against a 1700 cm species height.
The offline `render_billboard_texture` render of the mesh is the cheap check — it shows a
recognisable date palm, and it costs no engine.

**A leaning striped shaft with a starburst crown in these frames is NOT this palm.** Checked:
DatePalm instance tilt across all 239 is mean 2.9 deg, max 4.9 deg, and the mesh itself leans
3.6 deg. That shaft, and the long thin dark "sticks" crossing the grove frames, are also present
in the cp08 BEFORE frames — they belong to the pre-existing OSM lollipop-tree / fallen-log assets,
not to JudeanFloraV1. Do not chase them here.

### Defect 1: the cards were world-scale, not plant-scale

`create_vegetation.py` sized every leaf card from the CROWN — `cluster_radius = crown * 0.16`, a
**1.92 x 1.63 m** card for an olive — then drew ~7 leaves into it at `LEAF_FIT = 0.62` of the cell
each. A 6 cm olive leaf rendered at roughly a metre; the date-palm card was **4.02 x 1.17 m**
carrying three rotated pinnate shapes stretched across it.

**The rule now: a card is a leaf SPRAY at the size a real spray is, and the atlas cell depicts
exactly that spray.** Three tables drive it:
- `CARD_SPAN_CM` — physical span of one atlas cell. Olive 42, carob 46, terebinth 44, almond 48,
  fig 62, pomegranate 34, pine 55, cypress 30, sage 20, rockrose 18, thorny burnet 13, hyssop 12.
  **Not one global factor** — the species differ by 5x and a single scale would have fixed the
  olive and ruined the fig.
- `LEAF_AREA_INDEX` — `cards_for_crown()` turns it into a card COUNT, so density comes from the
  plant, not from a fixed 90 clusters.
- `CELL_COVERAGE` — needles and thorny twigs cover far less of a cell than a broadleaf spray.

`LEAVES_PER_CELL` (the fixed table of 7) is **gone**; the count is derived by Poisson coverage
against a MEASURED per-shape fill (`shape_fill()` samples `leaf_alpha` rather than asserting a
number). Olive 7 -> 148 leaves per cell, pine -> 373, cypress -> 420, fig -> 18. `build_leaf_masks`
rasterises each leaf over ITS OWN bounding box, which is what makes a 150-leaf spray affordable.

Two traps worth keeping:
- Cards are now SQUARE, because the atlas cell is square. Any other aspect stretches the leaves.
- **A palm is not a spray.** Its card is ONE FROND, so `build_frond_masks()` draws one frond per
  cell in cm — a sagging rachis with 86 pinnae — onto a 375 x 78 cm card (`FROND_WIDTH_RATIO`).

Higher LODs **TILE** the atlas instead of stretching it (`LOD_CARD_MULTIPLE = [1, 2, 4]`), so
leaves stay the same size IN THE WORLD at every LOD. Because `cards_for_crown` falls as 1/span^2,
each LOD needs a quarter as many cards and carries the SAME leaf area.

### Defect 2: the LOD screen sizes were exactly 2x too large

`release_vegetation.py:lod_screen_size()` returned `2 * radius / distance`. The engine computes
`ScreenSize = 2 * (0.5 * P[0][0]) * R / d`, and `P[0][0] = 1/tan(hFOV/2) = 1.0` at 90 degrees — so
**ScreenSize is R/d, half what the script assumed**. A threshold twice too large is crossed at half
the distance: LOD1 at 20 m instead of 40, LOD2 at 60 instead of 120, billboard at 150 instead of
300. That was the whole "faceted low-poly blobs at 15-30 m" complaint. Verified in the receipt:
Olive bark ladder went `[1.0, 0.36199, 0.12066]` -> `[1.0, 0.18099, 0.06033]`,
`lodScreenSizesApplied: true` on all 27 ladders.

**NOT fixed, deliberately:** `set_lod_from_static_mesh(..., bReuseExistingMaterialSlots=True)`
still collapses a ladder onto one material slot, so the billboard rung renders with the leaf
material. Flipping it to `False` appends a slot per LOD and `assign_mesh_slots` would have to name
each new slot's role from an imported slot name that `import_materials=False` never supplies. That
is a separate experiment and was not worth risking cp08's material fix on the same cook.

### Budget: triangles UP, fill DOWN — and fill is the one that matters

Per tree at LOD0: olive 1768 -> 4876 tri, carob/terebinth/pine 1768 -> 5488, almond 1768 -> 2248,
palm 256 -> 336. Asset total 30,894 -> 71,942. Estimated foliage load
**162,020 -> 453,326 triangles per frame against the 3.5 M ceiling; headroom 21.6x -> 7.7x.**

But card AREA per tree — what alpha-tested foliage actually pays for — **falls 4-6x**: carob
1504 -> 254 m2, pine 1152 -> 363, olive 846 -> 184, fig 993 -> 159, almond 476 -> 90.
`budget_report()`'s own docstring says foliage "is fill-bound long before it is triangle-bound", so
this trade spends the resource there is 7.7x of to buy back the scarce one. The old comment
"cards are kept few and large rather than many and small" is the assumption this pass reverses,
and it was wrong: few-and-large is exactly what made a 6 cm leaf render at a metre.

### Pipeline facts paid for on this run

- **Placement did NOT need redoing.** `release_vegetation.py` replays `placement-plan.json`
  transforms verbatim; nothing reads mesh bounds at placement time. The plan stayed byte-identical
  (sha `39b7c15e6ed8b6d0...`), so the 697 batches stand. The ONLY gate a regenerated mesh trips is
  `offline_check()` lines 314-330, which compares each OBJ/PNG against the sha in the manifest.
  `hashParity` and `generatorSha256` are **never read** by the release script — provenance only.
- A re-run of `-VegetationImportOnly` still trips the clash guard at line 1025, so it needs
  `-VegetationResume=<a 697/697 receipt for the same map>`.
- **A re-import puts every mesh slot back on WorldGridMaterial.** Always follow with
  `release_vegetation_materials.py -VegMatAssetsOnly`, or cp08's fix is silently undone. After the
  new ladders it reported **118 mesh slots** assigned, 0 errors, 55 textures unchanged.
- **`UnrealEditor.exe -ExecutePythonScript` exits non-zero even when the script SUCCEEDED**: the
  teardown asserts `Object is not packaged: ModeManagerInteractiveToolsContext` in `quit_editor`.
  Judge these runs by the receipt and the `LogPython:` summary line, NEVER by the exit code — a
  wrapper that trusted exit 3 skipped the material step and nearly shipped grey foliage.
- `create_vegetation.py` had a latent `dict | dict` in `write_manifest` — **3.9+ syntax, and the
  interpreter on PATH here is 3.8.1**. It ran all 14 species (11 minutes) and then died on the last
  line. Validate a long generator's TAIL before spending the wall clock on its body.
- New: **`--reuse-textures-except SPECIES`** re-exports geometry while keeping the PNGs already on
  disk (re-hashing them, so the manifest still states what is there). A geometry-only re-export
  went from 11 minutes to **25 seconds**. Any species whose geometry changed must be listed,
  because its billboard is a render OF the mesh.

## cp08: usage flag fixed for CityDetail too, and the cooked log is now CLEAN — 2026-09-10 06:3x UTC

**`checkpoint_playable`, exit 0, three frames captured, and the packaged build's own log now
reports ZERO usage-flag faults for JudeanFlora and ZERO for CityDetail** (cp05b had five outright
fallbacks plus ~22 recovered-with-a-hitch). Receipt
`vegetation-materials-visual-acceptance-cp08-20260910T063630328255Z.json`, frames
`SourceAssets/visual-review/cp08-veg-*.png`.

**One flag fixed six instances.** All six `MI_CityDetail_*` share the parent
`M_Context_Building`, which was `False`. This is the same parent-level fact as the vegetation and
is worth stating plainly: **CORRECTED 2026-09-11: in UE 5.8 a `UMaterialInstance` DOES carry usage flags** - its
`UsageFlags` are the parent's, plus `BasePropertyOverrides.bOverride_UsageFlags` bits it sets or clears
(MaterialInstance.cpp ~2673; `MaterialEditingLibrary.set_material_usage_override`). The nine protected
`MI_PBR_*` instances carry their Nanite repair THAT way; `M_PBR_Tiled` itself has no `bUsedWithNanite`.
So: a flag on the parent covers every child; a flag missing on a protected parent can be supplied
per instance, and a NEW child of `M_PBR_Tiled` does NOT inherit a sibling's override.

**`MI_SanctuaryV2_Gold*` Nanite warning - SETTLED 2026-09-11 with packaged frames.** The warning was
genuine and the "Default Material will be used" text was NOT what happened. For a Nanite STATIC mesh a
failed Nanite material audit makes `ShouldCreateNaniteProxy()` false (NaniteResourcesHelper.h), and the
component renders through a classic `FStaticMeshSceneProxy` WITH ITS REAL MI - no grid. cp15 frames
`SourceAssets/visual-review/cp15shell-*.png` (floor, ceiling, veneer strip, entrance jambs) match cp05b-09
and the editor V2 reference. Cost was 10 shell components off Nanite (boxes; negligible), plus log noise.
Cause: `release_sanctuary_finish_v2.py` copied `MI_PBR_GoldHammered`'s textures but not its instance
Nanite override. Fixed by `Scripts/repair_sanctuary_v2_nanite_usage.py` (instance override only, M_PBR_Tiled
and maps byte-identical; receipts `sanctuary-v2-nanite-usage-{apply,verify}-20260911T02*.json`, checkpoint
`ReviewCheckpoints/SanctuaryV2NaniteUsage-20260911T024615634328Z`, `--revert <apply receipt>`), cooked as cp16.
Contrast: an ISM/HISM usage miss (the vegetation) DOES substitute the default material. Same log line,
different consequence - which is why the frame, not the log, is the test.

(Superseded:) **The only usage-flag warning left is `MI_SanctuaryV2_Gold*` missing Nanite**, deliberately
untouched: different flag, the nine protected Nanite-repaired instances, and they render correctly
despite the warning — which is exactly why the warning's PRESENCE is not a valid test. The
FALLBACK is. Test by reading the cooked build's log for "Default Material will be used in game",
and then by looking at a frame.

## THE VEGETATION RENDERS. Root cause was a missing usage flag, and a frame was the only thing that could find it — 2026-09-10 06:2x UTC

**cp05b shipped every leaf card as a solid opaque quad. The cause was not the atlas, the alpha,
the clip value or the graph: `M_JudeanFlora_*` lacked `bUsedWithInstancedStaticMeshes`.** All
225,780 instances live on HISM components, and a material without that flag CANNOT be used on an
instanced static mesh, so the COOKED build silently substituted `WorldGridMaterial` — opaque,
one-sided, no opacity mask, no colour. Fixed, cooked as cp07, and **proven with three frames from
the packaged build**: `SourceAssets/visual-review/cp07-veg-*.png`, receipt
`vegetation-materials-visual-acceptance-20260910T062438179776Z.json`.

**THE FLAG LIVES ON THE PARENT `UMaterial`, NOT ON THE INSTANCE.** `UMaterialInstance` has no such
property; it resolves usage through its base. Setting it on the three `M_JudeanFlora_*` parents
alone fixed all 40 instances and all 225,780 plants — that is measured, not assumed. The same
one-line fix on `M_Context_Building` covers all six `MI_CityDetail_*` instances, which share it.

**WHY EVERY CHECK IN THIS PROJECT STAYED GREEN AND HONEST.** The EDITOR sets a missing usage flag
on the fly when it meets an instanced component and only warns that the asset needs resaving. So
parameter parity, save-and-reopen readbacks and every `-nullrhi` receipt saw a correct material —
because in the editor it WAS correct. **No editor-side check can catch this class of fault.** The
acceptance now reads the flag off the SAVED asset and refuses if it is false, but the real lesson
is that only a frame from a packaged build closes it. Caution: `MI_SanctuaryV2_Gold*` logs the same
warning and renders correctly, so the warning's PRESENCE is not the test — the fallback is.

**What the frames show.** Cut-out foliage: serrated leaf edges, pinnate carob and terebinth
leaflets, cypress needles, straw grass tufts, bark trunks, and clear per-species colour separation.
The precinct deck, city and sky in the same frames are the unchanged control.

**A second, self-inflicted defect found on the way, and the check that now prevents it.**
`MaterialEditingLibrary.delete_all_material_expressions()` DOES NOT empty the graph. The
"rebuild in place" used during the cook-crash diagnosis left `M_JudeanFlora_Leaf` holding **35
expressions where 24 had been created** — two `LeafAtlas` samplers, seven `ScalarParameter`s
instead of four, duplicate parameter names. `build_master()` now deletes and recreates the asset
and asserts that the saved material holds exactly the expressions it created with no repeated
parameter name.

**What was ruled out first, so nobody repeats it:** the source atlases DO carry a correct binary
cutout (`T_Olive_Leaf_BCA` decoded texel by texel: exactly two alpha values, 67.2 per cent fully
transparent, cut texels RGB 0,0,0); the meshes DO have UVs (2160 `vt` for 2160 `v`, card UVs
spanning atlas cell 0); and the graph was correctly wired throughout. No atlas re-authoring was
needed.

**Capture recipe, now a script:** `Scripts/capture_vegetation_frames.ps1`. One trap paid for —
photo mode writes `MikdashPhotos/` under the process WORKING DIRECTORY, not under the exe, so
`Start-Process` must be given `-WorkingDirectory`; without it the run reports "no PNG produced"
while three good frames sit in whatever folder the shell happened to be in.

**Still wrong, and now clearly visible with the right material on screen:**
- **The cards are world-scale, not plant-scale.** A carob leaflet reads as tens of centimetres and
  date-palm fronds fill the frame at 2.4 m. Mesh authoring in `create_vegetation.py`.
- **The LOD ladder collapses**: trees at 15-30 m are faceted low-poly blobs. Needs a re-LOD pass
  with `StaticMeshEditorSubsystem`, which is None in commandlets — use the hidden-editor recipe.
- The overall read is greener and lusher than the authored dry-Judean targets.
- Vegetation stands ON the paved precinct deck: no plaza keep-out. Pre-existing.
- The pre-existing OSM lollipop trees sit alongside the new flora; the two art styles do not match.

## cp05b PASSES: checkpoint_playable, leaf material intact — 2026-09-10 05:14 UTC

**`Checkpoint-Build.ps1 -Label cp05b` -> `status: checkpoint_playable`, `exitCode: 0`.**
Cook 8,708 / 8,708 with no shader error, `BUILD SUCCESSFUL`, `AutomationTool exiting with
ExitCode=0`, 3.92 GB archive at `C:\Mikdash\Builds\Checkpoint-cp05b-20260910T051017Z`, child exe
`432bcbf4558adbae...`. Both maps byte-unchanged across the build
(Candidate48 `9144cc15...`, Main50 `85bb51a1...`). **No vegetation feature was removed to get
this** - the leaf master still carries PerInstanceRandom, ObjectPositionWS, MSM_TWO_SIDED_FOLIAGE
and the subsurface output. See the entry below for why that was the right call.

**NEW AND WORTH ACTING ON: the PACKAGED BUILD starts on this box.** The smoke test launched it for
real, with a real RHI: `windowOpened=True`, `secondsToWindow=18`, `stillAliveAfterWindow=True`,
**`peakWorkingSetMB=2852`**. That is 2.8 GB against the ~19.9 GB a real-RHI EDITOR reserves on this
map - which is why editors have been impossible all night while the shipped exe is not. The
project's standing rule that "a material is not accepted until a rendered frame with an in-frame
control shows it" has therefore been out of reach for the wrong reason: it was inferred from the
editor's footprint. **A frame of the vegetation is now obtainable from the packaged build**, and
that is the cheapest outstanding path to the visual acceptance every vegetation receipt is still
missing. Not attempted here; flagged deliberately.

## cp05's cook crash was NOT the leaf material - and the test that proved it — 2026-09-10 05:1x UTC

**Checkpoint cp05 failed with `Error_UnknownCookFailure`: ShaderCompileWorker return code
-1073741819 (0xC0000005) on `M_JudeanFlora_Leaf` / `FLocalVertexFactory`, no HLSL diagnostic.
Identical signature to the cp02 plaza crash. It was not the graph, and the material was left
intact.** Diagnosis receipt
`SourceAssets/vegetation-review/vegetation-materials-cook-diagnosis-20260910T051144319249Z.json`.

**THE CONTROL, which is the part worth keeping.** `M_JudeanFlora_Leaf` was rebuilt IN PLACE with
a byte-identical 24-node graph. Rebuilding gives every expression a fresh FGuid and therefore a
fresh shader-map DDC key, so the next cook had to recompile from COLD exactly the permutations
that had crashed. Proof it was really cold: the cook logged `Missing cached shadermap ...
PCD3D_SM6` and `... PCD3D_SM5` for it with NEW key hashes `b7...`/`1c...` against cp05's
`d07f4421...`/`efda51f1...`. Result: **8,708 / 8,708 packages, `Success - 0 error(s), 0
warning(s)`, no crash.** PerInstanceRandom, ObjectPositionWS, MSM_TWO_SIDED_FOLIAGE, subsurface,
masked and two-sided all survive.

**Three things that mislead, all cheap to check before amputating a feature:**
1. **`SCW N Queued Jobs, Unknown number of processed jobs!` means the N jobs listed are the
   CONTENTS OF THE DEAD WORKER'S BATCH**, not N independent failures. "Four of five in the vertex
   stage" is that batch's composition and carries no signal about which stage was at fault. It
   does tell you which MATERIAL was in flight.
2. **`Falling back to directly compiling which will be very slow` means the engine recompiled
   those same jobs in process.** A later cook showing NO `Missing cached shadermap` line for that
   material proves every one of its jobs - including the ones printed as Failed - succeeded, since
   a shader map only reaches the DDC complete. cp05 finished all 8,708 packages and returned
   non-zero only because the 5 job errors had already been recorded.
3. **Memory is a CONSTANT here, not a variable.** Free physical memory measured DURING a cook on
   this box: 80 MiB / 529 / 1052 / 1445 in cp05, and 109 MiB in the cook that PASSED. The cook
   drives the box to the floor every run, pass or fail. Free RAM at cook START does not
   discriminate either - the night's two SCW crashes were at 9.1 and 8.2 GB free, three passes at
   5.2, 6.9 and 8.8 GB. So memory explains neither the failures nor the passes on its own.

**THE DISCRIMINATING TEST, one cook:** force a cold shader map for the suspect material (rebuild
its graph in place so the DDC key changes) and cook again. Compiles cold => valid graph, the crash
was a worker process death. Crashes cold => the graph is implicated, bisect. **Do this before
removing features:** the "obvious" fix here would have deleted per-instance colour variation from
225,780 plants to cure a fault that was never in the material.

**`EnclosureMath.h` section 6b now has a `6b-ii`** recording exactly that, because the rule as
written ("no author-written HLSL between per-instance data and the output") is a real rule that
did not apply to this material, and reading `-1073741819` as automatic proof of a graph defect is
what cost the time. The plaza rule STANDS: a Custom node fed by per-instance data is still
forbidden, and rebuilding the plaza without one did fix cp02. What is corrected is the diagnosis -
the compiler DYING is not the compiler REJECTING a graph, and only the cold-recompile test
separates them. The cp02 case has no such control, so it is not relitigated here.

**A bisect ladder now exists even though it was not needed.**
`Scripts/release_vegetation_materials.py` carries `LEAF_VARIANTS` (`full` / `noSpatial` /
`noVariation` / `noFoliage` / `minimal`) and `-VegMatRebuildLeaf -VegMatLeafVariant=<name>`, which
rebuilds the master in place - instances keep their parent and their species colours because the
graph is emptied and refilled rather than the asset replaced. About three minutes per rung.

**Still not established:** no rendered frame of this vegetation exists, and one clean cold compile
does not make an intermittent worker crash impossible.

## The vegetation is no longer grey — 2026-09-10 04:2x UTC

**225,780 instances across 27 components on BOTH maps went from `WorldGridMaterial` to authored
bark and leaf materials. 27/27 slots assigned on each map, 0 left on an engine default.**
`Scripts/release_vegetation_materials.py` + `.spec.json`, three receipts under
`SourceAssets/vegetation-review/`: `vegetation-materials-assets-20260910T042239243857Z.json`
(map-independent), `-Candidate48-20260910T042529067639Z.json`, `-Main50-20260910T042654976146Z.json`.

**The defect was measured, not assumed.** All 105 JudeanFloraV1 static meshes came back with
exactly ONE material slot whose imported name was literally `WorldGridMaterial` — the engine
default — and all 27 placed components carried an EMPTY `override_materials` array. That is the
whole of what the user has been walking through.

**What was built.** Three masters under a NEW namespace
`/Game/MikdashV3/Vegetation/JudeanFloraV1/Materials`, 40 instances (14 leaf, 13 bark, 13
billboard; DryGrass has no bark or billboard part):
- `M_JudeanFlora_Leaf` — **BLEND_MASKED, two-sided, MSM_TWO_SIDED_FOLIAGE, clip 0.5**, subsurface
  transmission wired. A card rendered opaque is a rectangle and rendered one-sided it vanishes
  from half the angles; nothing else about a foliage material matters as much.
- `M_JudeanFlora_Billboard` — masked, two-sided, DEFAULT_LIT (transmission over a picture of a
  trunk makes the far LOD glow).
- `M_JudeanFlora_Bark` — opaque, one-sided, base colour + normal.
All three read back off the SAVED assets after a reload with the right blend mode and two-sided
flag. **Flags are set before the first compile**, so no stale shader map has to be fought after.

**Colour is per species and derived, not eyeballed.** `tint = targetLinear / atlasLinear` per
channel, so the material CORRECTS `create_vegetation.py`'s atlas onto an authored target instead
of tinting an already-coloured texture twice; the round trip is exact (predicted == target on all
14). Cypress leaf lands at sRGB [48,72,54] and DryGrass at [192,174,118] — a 58..161 luma span
across the set, 14 distinct targets and 14 distinct roughnesses. Olive is grey-green [104,116,92]
with a silvery subsurface, date palm yellow-green [128,142,68], sage and hyssop grey and dusty.
Read back off the instances the placed components point at, on both maps, identical.

**Per-instance variation, stock nodes only.** BaseColour = TexRGB * Lerp(TintA, TintB,
**PerInstanceRandom**), TintA/TintB straddling the target in hue as well as value (Olive spans
[96,108,87]..[112,123,97]); the leaf graph adds a second decorrelated
`Frac(dot(ObjectPositionWS.xy, k))` brightness lerp. **No Custom node anywhere** — `Graph.node`
raises if a class name ends in `Custom`, and the offline check fails if that guard is deleted.
EnclosureMath.h 6b, which cost a day of packaging, is honoured by construction.

**Textures: 55 inspected, 27 changed, all `_BCA` atlases WRAP -> CLAMP.** Wrapping an ATLAS bleeds
the neighbouring cell across the alpha edge and puts half a leaf on the far side of a card. The
`_N` normal maps were already `TC_NORMALMAP` + sRGB false — the importer's suffix heuristic had
got them right, which is worth knowing rather than re-fixing.

**Three traps paid for here, all now guarded in code:**
1. `str(enum).split('.')[-1]` leaves the `: 0>` tail of `<TextureCompressionSettings.TC_DEFAULT: 0>`,
   so every flag comparison fails against a plain name. Cost one full assets run. `_enum_name()`.
2. **A prose annotation added beside word lists in a JSON lookup table iterates as CHARACTERS and
   matches everything.** Adding a `"measured"` note next to `"bark": [...]`/`"leaf": [...]` turned
   every slot into a role called `measured` and failed the first Candidate48 apply. The lookup now
   skips any non-list value.
3. **A protected path that does not exist is a spec error, not "nothing to protect."** The spec
   first guessed `/Game/MikdashV3/PBRArchitecture/M_PBR_Tiled`; the real path is
   `/Game/MikdashV3/Materials/PBR/M_PBR_Tiled`, so the `if ...exists()` filter silently left the
   guard watching an empty set. It now raises. (M_PBR_Tiled is untouched — `7a1aaf9db94dd186...`,
   last written 2026-09-07 — and so are the nine Nanite-repaired instances' usage flags.)

**NOT ESTABLISHED: nobody has seen a frame.** A real-RHI editor still cannot start on this box, so
the project's own rule — a material is not accepted until a rendered frame with an in-frame
control shows it — is NOT met. Every receipt is stamped
`..._visual_acceptance_pending`. Applied anyway because the alternative is engine-default grey,
which is a certainty rather than a risk. Also open, and recorded rather than fixed: because
`set_lod_from_static_mesh` collapsed every ladder onto one slot, **the billboard LOD of a leaf
ladder renders with the LEAF material and the leaf atlas**, not the impostor texture — the
standalone `SM_*_Billboard` assets do carry `MI_*_Billboard`. Splitting the far LOD onto its own
slot needs `StaticMeshEditorSubsystem` and a re-LOD pass. There is no wind (no WorldPositionOffset)
and no leaf normal map exists in the set.

**Map hashes.** Candidate48 `d4f0f5e2...` -> `9144cc15...`; Main50 `c23b1618...` -> `85bb51a1...`.
Each run watched the other map and it was byte-unchanged. `--revert=<receipt> --dry-run` verified
both checkpoints against the recorded pre-run hashes.

## Three Main50-only passes now land on the map that ships — 2026-09-10 02:4x UTC

**Gate security, surface wear and vegetation all exist on Candidate48 now.** All three hardcoded
`TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'`, none contained the Amah48Candidate
path anywhere, and Candidate48 is the configured `GameDefaultMap` and the only map cooked into the
download. Everything the user had been shown of these three existed only on the map that does not
ship. All three now take `-Main50` (THE DEFAULT, so no existing invocation is retargeted) or
`-Candidate48`, in the shape `release_reviewed_daylight.py` settled on.

**The switch was the easy half.** Candidate48 holds the same architecture under
`p_candidate = 0.96 * p_main50 + (-248, 0, 0)` while the FutureMountV1 terrain and the metric city
were never rescaled, so a correct port has to move what moved and leave alone what did not. That is
now one file, `Scripts/map_targets.py`: the two maps, the similarity, `prove_placement()` (
`release_water.py`'s method), a terrain fingerprint comparison, an offline checkpoint `--revert`,
and a self-test (`python Scripts/map_targets.py`, 20 checks including that
`0.96 * -6200 - 248 = -6200` — the Aron is the FIXED POINT of the candidate transform, which is
what the -248 is for).

**Nothing trusts the transform; every run measures it.** `Scripts/candidate_placement_proof.py`
(read-only, both maps in one session) and each release run independently: every actor resolving to
`architecture-manifest.json` is compared with its manifest AABB carried through the declared
placement, AND the placement is solved back out of those bounds by least squares.

| map | agree | measured scale | measured translation cm |
|---|---|---|---|
| Main50 | 2626 / 2633 | 1.000000686 | [-0.0004, 0.0067, -0.0054] |
| Candidate48 | 2626 / 2633 | 0.960000659 | [-248.0004, 0.0064, -0.0052] |

The same 7 actors disagree on BOTH maps (turned pedestal, hollow basin — manifest-vs-live AABB
differences that predate all of this), and their worst error is 42.5001 cm on Main50 and 40.8001 on
the candidate: 0.96 times it, exactly. Even the disagreement scales.

**What landed, and how it was shown to be geometrically right rather than merely present:**

- **Gate security, `native-gate-security-Candidate48-20260910T024340862182Z.json`.** 90/90 placed,
  saved, reopened; pose error **0.0 cm on all 90**, worst reopened bounds error 5.9e-06 cm, every
  actor NoCollision. Each gate's live first riser and threshold match their PREDICTED bounds to
  0.0000-0.0015 cm, and the assembly stands **96.00 cm out from the live riser at all three gates,
  exactly 0.96 x the authored 100 cm**. Re-verified read-only from a fresh process, 90/90, zero
  problems, map byte-unchanged (`native-gate-security-verify-Candidate48-20260910T024732210165Z.json`).
  The WHOLE assembly rides the 0.96, so the detectors and signage are 4 per cent under real size —
  deliberate (it keeps the wall plates flush with the measured vestibule wall and the racks off a
  riser that is itself 4 per cent nearer) and recorded as a limitation in every receipt.
- **Surface wear, `native-surface-detail-Candidate48-20260910T024410434756Z.json`.** 460 decals +
  the manager; **all 460 read back after the reopen at 0.0 cm location error and 0.0 cm decal-size
  error**. Origins, projection boxes and the manager all carry the similarity, so a wear patch
  covers the same fraction of the same tread ([0,-2650,625]/60x280x180 -> [-248,-2544,600]/
  57.6x268.8x172.8). The assets stage is map-INDEPENDENT and was not re-run; the 09-09 assets
  receipt's asset SHA-256s were re-checked on disk. New evidence worth keeping: 456 of the 460
  decal origins sit inside a manifest architecture AABB at 60 cm padding; the 4 that do not are the
  outer gate landings.
- **Vegetation, `release-vegetation-Candidate48-20260910T024536144980Z.json`.** 697/697 batches,
  **225,780 instances across 27 components, expected == readback on all 27, 0 errors** — the SAME
  instance total as Main50. **THE PLANTS DO NOT RIDE THE SIMILARITY, and that is the finding.**
  They stand on terrain that was never rescaled, so they are placed at IDENTICAL coordinates, and
  the licence for that is measured: all **256 ground tiles have identical world AABBs on the two
  maps, worst 0.0000 cm**. The eleven-plus-one `*_PrecinctCut`/`KotelPlazaCut` twins legitimately
  differ (up to 502 cm — the precinct square is itself 4 per cent smaller) and are excluded from
  that comparison by name rather than averaged into it. What DOES ride the transform is the
  keep-out: the enclosure ring and the 162 architecture blocker boxes are tested in BOTH frames
  (2 rings, 324 boxes), offline and live, so nothing is planted inside the Mount under either
  interpretation. 2,678 refused by the existing-tree rule. `release_vegetation.py` refuses to place
  on the candidate at all unless `SourceAssets/scale-review/ground-fingerprint-Main50.json` exists.

**A resume receipt is now per MAP.** `-VegetationResume=` refuses a receipt whose target is not this
run's, because skipping the batches the OTHER map completed would leave a hole exactly the shape of
the other map's progress and no count against the plan would ever see it.

**`--revert` works and was exercised for real, not asserted.**
`python Scripts/release_vegetation.py --revert=<receipt>` (offline, no editor open) restored
Candidate48 from `034f8343...` to the checkpoint's `902152739fb9690a...` byte for byte, after a
`--dry-run` that verified the checkpointed bytes still hash to the receipt's `mapSha256Before`. The
map was then restored forward to `034f8343...` from a copy taken first. All three scripts expose it.

**Receipts now carry `target` and are named `<pass>-<Target>-<stamp>.json`**, which is what
`verify.py check_map_parity` buckets on — that is the blind spot the 10 Sep note describes, and
these three passes were 3 of the 351 receipts it could not see. Both targets' maps are now in each
run's protected-hash set, so a Candidate48 run watches Main50 and vice versa; `protectedMapsUnchanged`
true on every run above.

**The paired evidence, on the map that did NOT change.** `-Main50 -GateSecurityVerifyOnly` re-run
after all of this (`native-gate-security-verify-Main50-20260910T024927506500Z.json`): 90/90, zero
problems, map byte-unchanged, standoff **100.00 cm** at all three gates against the candidate's
96.00. Main50 finished the night on **9f5dd4b0230d9de8adafa4b469ed3ada7d07aa57a8fa9a358a0b1d489227bd53**
— the same hash it carried before any of this — and Candidate48 on
**034f83435874be25a3cc82776704e6a95b57a53c4058152f42637beb77be4ae3**.

**Small trap, paid for here: do not put a `target` key in a reference table under SourceAssets/.**
`verify.py check_map_parity` buckets ANY json there carrying `target` as a pass that ran on that
map, so `ground-fingerprint-Main50.json` immediately produced a WARN that a "ground-fingerprint"
pass had run on the legacy map only. The field is `readFromTarget` now. Related and still open: the
per-pass parity buckets still read `native-gate-security` / `native-surface-detail` /
`release-vegetation` as ship-only, because the HISTORICAL Main50 apply receipts carry `map` and no
`target`. That is the 351-receipt blind spot the entry below describes; the new receipts all carry
`target`, and nothing back-fills old ones.

**Not established by any of this:** no visual, collision, cook or performance acceptance on either
map; the 4 unhosted decals are recorded, not fixed. (Vegetation materials WERE unassigned; they
were authored and assigned on both maps a couple of hours later — see the 04:2x entry above.)

## Backlog verification pass — 2026-09-10 02:1x UTC

**Candidate48 real-RHI PIE is not possible on this box right now — that is the headline.**
`release_resident_routes_v2.py -RoutesV2Verify -RoutesV2Target=Candidate48` requires real RHI
(it refuses NullRHI as evidence) and the editor died twice at frames 7 and 17 with
D3D12Util.cpp:815 "Out of video memory". It is NOT video memory: local VRAM budget 7238 MB with
only 4276 MB used, while system Virtual Memory read **65370.78 MB used of 65389.91 MB, 19.13 MB
free**. The Windows COMMIT limit is the wall. Measured with no editor running, baseline commit is
**45,171 MB of 65,390 MB** consumed by non-Unreal processes (`mc-fw-host` PID 4704 alone holds
11,014 MB), leaving ~20 GB; a real-RHI editor on this map reserves ~19.9 GB of process virtual
address space (18,377 MB of it D3D12 "Reserved Buffer Memory (Uncommitted)"). So it fails right at
the edge. Candidate48 .umap verified byte-identical after both crashes (a4337468...). Receipts
resident-routes-v2-verify-Candidate48-20260910T015552005900Z.json and -20260910T015917186399Z.json
were left at 'starting' because the crash skipped the finally-block; their status has been corrected
to failed_editor_crashed_out_of_commit_before_pie so they cannot be misread as a pass.
A -nullrhi commandlet is unaffected: it never takes the D3D12 reserved-buffer path.

**verify.py check_map_parity has a blind spot, and it now reads falsely green.** It buckets receipts
by `target` and counts EXISTENCE, not status, so the two crashed Candidate48 receipts above cleared
the long-standing "resident-routes-v2-verify ran on the LEGACY map only" WARN without the pass ever
having run on the shipping map. Separately it is blind to 351 receipts that record `map` but no
`target` (229 of them Main50-pinned) - which is exactly why gate security, surface detail and
vegetation have never appeared in it.

**Three release scripts are structurally Main50-only.** `release_gate_security.py`,
`release_surface_detail.py` and `release_vegetation.py` all hardcode
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough' with no target switch, and none of
them contains the Amah48Candidate path anywhere. There is no port_candidate_* helper for any of the
three. The shipping/cook map therefore has no gate security, no surface wear and no vegetation, and
cannot get them without adding a target parameter.

**Gate security: already complete, re-verified against the CURRENT map.** The verify helper WAS
re-run after its 03:05 UTC fix (receipt 030841758949Z, 90/90). Re-run now on the post-plaza,
post-terrain-cut Main50: native-gate-security-verify-20260910T020232145559Z.json,
**90/90 actors, east 30/30, north 30/30, south 30/30, zero problems**, map 4a32a648... byte-identical,
mapSaved false.

**Surface detail: complete on Main50, absent on Candidate48, numerically.**
candidate-parity-20260910T020232999990Z.json: Main50 **460 tagged wear decals, all 460 on
SurfaceDetailSoftV1 materials, 1 MikdashSurfaceDetail manager**; Candidate48 **0 and 0**. Both maps
byte-identical during the inventory. Note `verify_surface_saved.py` can no longer be re-run: it
asserts the live map still hashes to the receipt's `mapSha256AfterSave`, which moved on 2026-09-09.

**Vegetation: 697/697 batches placed, and it needed TWO real fixes.** The premise that ~60 batches
had run was wrong - 0 had, and the pass could never have worked:
1. `AActor::AddComponentByClass` is declared `meta=(ScriptNoExport, BlueprintInternalUseOnly)` in
   Actor.h:1973, so it is deliberately absent from the UE 5.8 Python bindings and
   `actor.add_component_by_class` raises AttributeError - the exact failure of receipt
   174529264332Z. `release_city_detail.py` had already hit and solved this; its
   SubobjectDataSubsystem.add_new_subobject recipe (ownership verified three ways) is now ported
   into `release_vegetation.new_hism`.
2. The resume path DUPLICATED actors. `component_for` always spawned a new actor, so a resumed run
   made a second RELEASE_Vegetation_<species>_<role>. Receipt 20260910T020616142404Z failed its own
   reopen readback - "Reopened actor count for RELEASE_Vegetation_Olive_Bark is 2" - AFTER the save.
   Main50 was restored from that run's checkpoint back to c80e2c64 and re-verified by hash.
   `component_for` now ADOPTS an existing labelled actor, checks it carries exactly one HISM with the
   right mesh, and seeds `added` from its current instance count so the post-reopen equality check
   stays exact. place()'s pre-existing clash guard already assumed those actors exist on resume; this
   is the other half of that contract.

Final result release-vegetation-20260910T020948460767Z.json: **697/697 batches, 225,780 instances
across 27 components, 0 remaining, expected == readback on all 27, zero errors**, protected maps
unchanged, 2,426 instances refused by the existing-tree clearance rule. Main50 is now
9f5dd4b0230d9de8adafa4b469ed3ada7d07aa57a8fa9a358a0b1d489227bd53. Geometric placement only: no
visual, collision, cook or performance acceptance, and materials remain unassigned.

`Scripts/run_batch.py` carried gate security + parity inventory in ONE editor session
(batch-20260910T020223433470Z.json, 2 of 2 ran, 9.6 s and 10.4 s after one map load).

Two launch traps paid for here, both mine: PowerShell `Start-Process -ArgumentList <array>` does NOT
preserve the quotes in `-ExecCmds="py <path>"`, so the engine parsed `-ExecCmds=py`, ran a bare `py`,
and an -unattended editor sat idle holding the slot forever - pass ArgumentList as ONE verbatim
string. And `-TestSavePrefix` must match `(AstraProbe|FableProbe)_[A-Za-z0-9_]+`; anything else is
refused by _save_isolation before PIE.

scripts/verify.py 7/7 green, 32/32 math. Nothing committed.

## Published handoff — 2026-09-09

Windows12 is public at ShmuelSokol/3rdbhmk release walkthrough-12-preview.
Anonymous downloads and clean extraction passed63payload/59original files.
Downloadedcopy startup smoke passed, normal exit and original saves unchanged.
Current handoff: HANDOFF-WINDOWS12-PUBLISHED-20260909.md. Heartbeat PAUSED.
User requested publication then handoff/stop; no new feature wave. Broader quality
goal remains incomplete. Final documentation verification and push only.

## Historical distribution in progress — 2026-09-09

User authorized Windows download publication then handoff/stop. Three ordinary
ZIPs prepared in C:/Mikdash/Working-5.8/Walkthrough12-Distribution; CRC/payload
hashes passed. Clean local extraction verification running; no release yet.
Archive source is Attempt4 child329a2d910a53... . After published-download verification,
write final handoff and pause recurring heartbeat; do not start new feature work.

## Safe checkpoint — 2026-09-09 11:31 UTC

Attempt4 cook/staging/strictstartup PASS. Main/Pause preparation text wraps/fits
visually at observed1920x1080; titleBegin/skip/Pause/mouseQuit exercised. Game31484
quit normally, saves unchanged, no native job remains. Child329a2d910a53... .
Handoff HANDOFF-20260909-READY-TO-PAUSE.md records exact continuation. No ZIPs/upload
started; user choosing pause vs distribution. Broader quality goal incomplete.

## Wrap build checkpoint — 2026-09-09 11:25 UTC

Full wrapping gate11/11,32/32math PASS; Editor45.94s/Game53.01s. Same two
pre-existing C4996 deprecations remain. Fresh Attempt4 cook/render next.

## Runtime checkpoint — 2026-09-09 11:18 UTC

Attempt3 cook PASS, startup strict log PASS (six Nanite warnings gone), staging
PASS. Real packaged UI: title visible, Begin/intro skip/Pause/Resume/Fdove/Freturn/
mouseQuit observed. Existing saves unchanged. Preparation label visibly overflows
Main/Pause; fixing wrap before download. Not a full route/settings/audio acceptance.
Source checkpoint432cfa37 pushed; Attempt3 childc2742de9... retained.

## Build checkpoint — 2026-09-09 11:10 UTC

Menu fix passes full11/11 gate and32/32 math. Editor52.85s/Game54.48s both
Succeeded; two existing C4996 menu deprecations retained (font/Virtual_Back).
Fresh six-material usage verified. Next fresh Attempt3 archive still required;
no packaged menu interaction acceptance yet.

## Current verification — 2026-09-09 11:03 UTC

Six old KotelSurfacePolishV2 Nanite flags repaired: apply110127656871 changed
exactly six assets; fresh110252111955 verified persisted flags in distinct process
with zero writes. All19 maps and other Content unchanged; originals checkpointed.
First105939 failure was path-key separator mismatch (Windows str vs slash plan),
no mutation. Use relative_to(...).as_posix() for manifest/hash dictionary keys.
Menu lifecycle fix now builds WidgetTree before Super::RebuildWidget selects its
Slate root; NativeConstruct is too late. Source reviewed; full Editor+Game gate
running, packaged visible controls still pending. Attempt2 archive preserved.

## Current continuation — 2026-09-09 10:59 UTC

Windows12 Attempt2 cooked successfully; staging file/hash gate passed. Startup smoke
failed on six older KotelSurfacePolishV2 Nanite usage flags (photo Cook clones clean).
Reviewed exact-six checkpointed repair running serially. UI game41088 closed normally;
scene rendered but Escape/P showed no menu, so packaged controls remain unverified.
Original recorded saves unchanged. Worker investigating front-end initialization before
next cook. Current archive retained; do not publish it as runtime-verified.

## Current verified state — 2026-09-09 10:38 UTC

Runtime identity fix now passes native103614713103: exact same269actor set as083903,
fingerprintadd1b55da3535d53, hardhide→Modern→Overlay→hardhide→RestoreAll and originally
false fixture all restored; protectedKotel collision retained, maps/saves unchanged.
BothEditor+Game compilation and32math passed (full11/11). Preparing sourcecheckpoint
then Windows12 Attempt2; firstcook failure preserved, no package success yet.

## Historical continuation — 2026-09-09 10:21 UTC

Update10:27: checkpoint423cdce1 pushed. First Windows12 game target FAILED at three
GetActorLabel calls in MikdashEnclosure.cpp (editor-only API). Both map hashes unchanged,
no packaged child exists. RuntimeBuild-12 retains log/failed receipt. Worker fixing actual
runtime building identity; do not just replace labels with arbitrary object names.
verify.py --build now checks Editor AND Game strictly serially; earlier editor-only gate
did not establish packaged compatibility. Also current FrontEnd bypasses legacy MENU_OPEN
logs; startup smoke now checks engine/defaultMap only and requires separate menu UI review.

Update10:33: corrected shared mesh-identity resolver compiles in BOTHtargets. Full gate
11/11,32/32math PASS; logs verify-ubt-MikdashCourtyardV3Editor-uf01hkdw.log and
verify-ubt-MikdashCourtyardV3-au9jdhas.log, no compilerdiagnostics. Exact269actor-set/FNV
parity plus nativecollisionrestore now running. No secondcook until it finishes.

Candidate114a6130cde60efabef34e30d0437fe6f1746d30737295d608245e55ee79ff77
is now configured as game default/editor startup/cook map (Selected48). Main50 is retained.
PhotoCook apply101331272215 and distinct fresh101546517415 pass four independent clones,
saved Nanite usage, exact authored graph/photo identity and unrelated-content preservation.
Original5 photo assets unchanged. RealRHI capture101820 reviewed by root: photo weathering
retained, no missingNanite/defaultmaterial/compile warnings; haze/simplefigures/paving still
unfinished. Capture maps/instances/originalsaves unchanged. Verifier visual review PASS;
quick gate6/6 (241Python,55specs,890receipts,123historicalWARN) and launcher CheckOnly PASS.
Skirt fresh101143434433 PASS, originalfailure095139 preserved; actualwalk100924 PASSbelow.
Preparing Windows12, not yet cooked/packaged/download verified. Last pushed4e8dbc7b.

## Historical continuation — 2026-09-09 10:12 UTC

Kotel walking100924875746 PASSES the unchanged four-checkpoint roundtrip in20.774s:
76samples, zero airborne/missing support, no errors, maps/original saves unchanged.
Scope is lower landing→deck→platform→lower landing, one initial test placement;
not the plaza approach, physical keyboard, full connectivity or ritual permission.
Candidate936f4fbb contains only local skirtV2 notch since dcea5bf8. Fresh persisted
mesh verification is running with reviewed float32 boundary readback. Photo cook
clones remain unapplied; latest source-graph fix is reviewed. Defaults/cook stillMain50.

Update10:09: for asynchronous Slate/PIE probes use -ExecCmds="py SCRIPT", as prior
successful runs do. -ExecutePythonScript auto-quits after registering the callback;
walk100654 exited before any samples and is NOT a collision result. Use one combined
-ini:Game argument with both full class sections, as prior isolated-save runs do.
Fresh100117 scale readback passes public LOD0 [1,1,1], but notch edge failed exact-double
boundary due to persisted float32 Y rounding. Diagnostic100352 proves0.000877375cm shift;
saved-source check now uses exact float32 cut representation, same area threshold.
Reviewer replay passes actual triangle and rejects0.01cm intrusion. Native walk1009 running.

Update09:55: V2 skirt apply095139 saved candidate936f4fbb and clone55860b8c, then failed
a readback at incorrect BodySetup property spelling build_scale3d. Raw BuildScale3D
is declared UPROPERTY in installed BodySetup.h299. Read-only recovery from the exact
SHA-pinned failure receipt is being reviewed; no reapply/overwrite. All protected Content
unchanged. The prior V1 orphan asset is retained, not bound to the map.

Update09:49: skirt093726 passed the strict local geometry/attribute checks but refused
before map save: only target actor7257 bounds differed (Nanite-expanded to tight source
bounds). Original Content and map dcea5bf8 remain unchanged. Investigating a target-only
bounds check; unrelated actor checks remain strict. Photo Nanite clone dry-run diagnostic
is running; no saved clones or new package yet.

Update09:35: four photo materials log missing Nanite usage in real PIE and would fall back
in packaged play. Candidate-only base-material clones with saved usage are being prepared;
original photos/materials remain protected. Skirt remains unapplied. Failed093247 topology
diagnostic shows four unchanged single triangles moved only~1e-12cm, crossing round3 ties.
Guard now permits only same-single-triangle <=1e-6cm fallback, not area-only equivalence or
subdivision; reviewer checking. GeometryScript_Primitives is the actual ScriptName in
MeshPrimitiveFunctions.h; do not infer Python class names from C++ filenames.

Update09:24: skirt attempts091838/092204 refused before duplication/save, map dcea5bf8 and
protected Content unchanged. Diagnostic092204 shows1824/1824 triangles and four lexicographic
ordering mismatches after float conversion (nearest corner error<0.001cm). Source guard now
uses one-to-one residual triangle matching at the SAME0.05cm tolerance; missing/duplicate
geometry still fails. Reviewer checking before rerun. The local trim remains unapplied.

Checkpoint4e8dbc7b is pushed. New exact-height contact probe090736345971 identifies
SM_MountPlatform_Skirt actor7257 at about7cm above the deck, deflecting the return walk.
Do not blame people or the Kotel base. A candidate-only duplicate skirt clearance is
being prepared: local top notch inside the 300cm bridge footprint, original asset retained.
Actual deck slab thickness is45cm (z[-43,2]);110cm is guard height, not deck thickness.
Installed GeometryScript TRIM_INSIDE supports clipping an open sheet; a closed Subtract
would be the wrong operation. No repair mutation or walking acceptance yet.

Performance handoff correction: current PERFORMANCE-BUDGET.md already has Sept8 CSV
thread/GPU evidence and Nanite adoption. The earlier claim that flat frame times prove
per-draw CPU limitation is superseded: render thread measured about3ms, GPU25.7→17.0ms,
cloud plus cloud shadows about6ms after Nanite. Current22–24ms Slate samples do not
replace that thread breakdown. Reprofile the current candidate before further conclusions.

Full gate9/9,32/32math and UBT passed; latest publication quick gate6/6 passes.
Build log verify-ubt-3x8p_4_e.log is clean, including corrected ServiceActor header order.
Native enclosure restoration083903 passes269actors, original-false fixture and protected
Kotel boundary collision. Maps/saves unchanged. Kotel ascent/platform access passes,
but upper-deck return deflects near x=-13585: roundtrip084132/085303 remains failed.
Forward capsule lifted5cm missed the shallow contact; actual-centre tracing identified it above.

Photo A/B084910 was visually reviewed by root and verifier and accepted for limited
weathering improvement. Four candidate V2 slots now use existing PhotoSurfaceV2 materials:
apply090038688444 saved/reopened and separate fresh090248379625 passes unrelated baseline,
protected Content and material identity. Candidate SHA
dcea5bf85498cabd519c182e3665792cbe732d358ebac94cdfcdec0032c0e7e1.
Main remains93483d25; defaults/cook remain Main50. No fresh packaged build yet.
Photo stretch/joint mismatch, haze, sparse simple figures and paving remain unfinished.

Capture084554 verifies18 native BuildCredits names. ThirdPartyFolder is protected in
Python even under its raw name: use observable public BuildCredits output, not property read.
Its two reviewed views retain visual defects. QPC p50/p95: north23.70/27.89ms,
Kotel22.31/25.50ms at1014x550,8seconds; not packaged or1080p game performance.
Next: publish verified checkpoint, diagnose return contact, then continue visual/access
fixes before candidate promotion and fresh downloadable build. Older notes below are history.

## Historical native findings — 2026-09-09 08:28 UTC

Kotel walk081519 and081953 both refused before initial placement. The actual blocker is
OldCityInfill Grid_N002_P001 actor7483; latter receipt proves hidden=true, collision=true.
Enclosure source fix now preserves original actor collision, disables it for fully hidden
selected buildings in game worlds, and restores it on return/cleanup. Protected Kotel
base mesh Grid_N002_P001 keeps its original collision because visible detail has none.
This is a runtime state fix, not geometry deletion; subsequent build/runtime results are above.
The layer diagnostic shows V2 ashlar visible; V1 and photo planes are hidden. Upper rays
hit the intended Kotel base, so the dark close-up does NOT establish an extra wall occluder.
Capture082421 failed at a Config-only property alias; raw ThirdPartyFolder also proved
protected in084353. The public BuildCredits output check supersedes both attempts.
First capture080856 timings were quantized (16/32 ms); use perf_counter plus clock metadata,
not coarse monotonic tick differences, for future frame intervals. Prior raw evidence kept.
Component GetCollisionEnabled is owner-aware (PrimitiveComponentPhysics.cpp1569). To test
component settings preservation under actor collision toggles, read raw BodyInstance
CollisionEnabled; effective collision is expected to change. See current acceptance above.

## Publication detail — 2026-09-09 08:08 UTC

Runtime checkpoint pushed 7741901c; configured-map gate pushed 2a5b00e0.
On this case-insensitive filesystem, use the exact tracked Git spelling
`Scripts/verify.py` when staging. `scripts/verify.py` resolves for file reads/copies
but did not stage the tracked uppercase-directory path. Check staged names against
the explicit manifest, not just command success, before committing.
Native four-view Candidate48 capture with viewport timings is running; no visual or
performance result is claimed until the actual images/receipt are inspected.

## Boarding runtime checkpoint — 2026-09-09 08:06 UTC

Candidate bridge runtime080239102318 completed 180.017 simulated seconds: 45 boarded,
25 alighted, 15 photographer figures, zero overruns; maps/original saves unchanged.
Receipt retains refusal/trimming counters. Static instanced apron figures only, not
skeletal resident handover or visual acceptance. The gate and launcher now validate the
actual configured default/startup/cook map agree and belong to the Main50/Selected48
allowlist. Config defaults remain Main50. Next native jobs: visual/performance captures
and Kotel stair roundtrip. No new package or candidate promotion yet.

## Runtime bird evidence — 2026-09-09 08:04 UTC

Bridge fresh075810825396 passes: candidate references, focus, source config and persisted
unrelated baseline match; protected changes/new Content files empty; map cd3348ec unchanged.
Bird runtime080014618354 passes 45.0076 simulation seconds: motion observed in 70 pigeons,
55 swifts, 9 crows and 1 kestrel. Maps/original saves unchanged. This verifies bounded
activity/counts, not visual species realism, physical perches or audio. Natural bridge
runtime is in progress. Kotel lower-landing stair roundtrip probe is prepared, not run.
Optional capture timings measure settled Slate callback intervals at the reported live
viewport size before HighResShot; they are not GPU timings or packaged performance.

## Boarding connection — 2026-09-09 07:59 UTC

Candidate bridge saved/reopened in receipt075539876162, map SHA
cd3348ec8c0cf6f40291a5f85e338207d22c7d770a7855be0dd443d88964d1a7.
Protected changes/new Content files empty. Fresh process verification is running.
References point to candidate Transit/CrowdField; authored photo focus is [-248,0,288].
Runtime boarding is still pending; these are the bridge's static figures, not an
accepted transfer of the 24 skeletal residents. Transit/bird checkpoint pushed d0daaae0.

## Integration checkpoint — 2026-09-09 07:55 UTC

Four metric bird flocks saved in Candidate48 (074420), independently reloaded in
fresh process (075232): both receipts pass with no protected changes/new Content files.
Candidate SHA b74b4c21dc7633e05644b7a81ffe66cd78f7a8d95410e7b4579b1a7df70805bc.
Main SHA 93483d25ff23e01ee1462845b958d9c2139f2cd2e7177cf5e3e3141dd4ae1432 unchanged.
Bird runtime/perch/visual/audio acceptance is pending; Temple Plaza flock is deferred.
Transit bridge helper is reviewed, not applied. Service remains startupOFF. The candidate
is still not the default/cook map, and no new Windows package is claimed.

CandidateTransit07414660simPASS:15stops/75supportsamplespass;240roadvehicles+1activetrain,
245paintinstancesmoved (NOT245vehicles). Maps/savesunchanged, nofullroute/boarding/perf
acceptance. Fourmetricbirdport nowrunning; PlazaTempleflock stilldeferred.

Transit fresh073717 verifies sourceconfig/15stops and persistedcanonicalcandidatebaseline,
protected/newContentempty, candidate89a68853 unchanged. Runtime60sim probe prepared;
reviewing hiddenPIE throttle/mouse cleanup beforeexecution. No bridge/birds yet.

Transit-only candidateport073522 saved/reopened: all15stop/config/sourceworldcoordinates
unchanged, protecteddifferencesempty/newContentFilesempty. Candidate89a68853eb364d0a02979ff0044fc1b5b434117caf923f3290f07921f30ce868.
Freshprocessverification pending; no movement/roads acceptance yet. Main93483 unchanged.

Candidate platformwalk073330 completedbothroutes46.28wallseconds, no teleport: naturalspawn
→eastgatedown/up→outerthreshold/stairs→unchangedmetricdeck.10checkpointsfloorerrors~2.15cm,
allmaps/originalsaves unchanged. Kotelaccess and physicalkeyboard/visualstairacceptance remain
separate. Nextserialjobtransit-onlyport, candidatehashstill7eda28df.

Sanctuary48 native072820 completed10checkpoints29.09wallseconds, floorerrors1.19–2.15cm;
one explicitinitialPIEplacement thencontinuouswalking, allmaps/originalsaves unchanged.
Architectural review only: currentopen/NoCollisiondoorway isnotritual access orfunctionalcurtain.
Candidate eastgate/platform continuousprobe now prepared, exactdeckpointsstaymetric;
transit-only port prepared, neither applied nor runtimeverified yet.

Sanctuarypreflight072443 safelyrefusedobsoleteIncenseAltarV2assetguard; no walk occurred.
Candidate documentedonepiece KeilimTIV1 altar/vessels163453 replaces oldBody+Poles. Probe
candidate-onlyguard now pins exactTIasset,oneBody/noPoles,framepose andside-lanebounds;
mainhistoricalguard unchanged. Fresh native walk still pending.

Candidatefrontend072223 passes correctedframe: forward2215cm,rise1613cm,pause0,exactwalker
return,18tour/76codexcontrols,24residentswalking; maps/savesunchanged. Tourroutewalking
and physicalkeyboard remain outside scope. Sanctuary48 architecturalroundtrip native pending.
Transit-only candidateport helper preparation underway, noasset/mapmutation yet.

Parityinventory072037 unchangedallmaps: Candidate lacks transit,5birdflocks,boardingbridge,
surfacemanager/460softdecals presentonmain;18tourmarkers andtour/codex actorsalreadyexist.
Do not describe candidate feature parity as complete. Frame-correctedflight rerun pending.
Sanctuary wrapper now supports explicit -SanctuaryWalkProbe to quit onpreflightrefusal.

Candidatefrontend071737: flightforward2131cm/rise1618cm/pause0 andtour18stops76entries
controls passed, then staleSelected48spawnexpect2016 failed. Actual1768 exactly matches
Aron alignment220353 receipt PlayerStart2016→1768; main/candidate/saves preserved.
Probe now asserts pivot[-6200], expected1768 andTemplecrowdX*.96-248 (metriczonesunchanged).
No map correction needed. Fresh regression pending; parityinventory native running.

Full native service070801 naturally completed1cycle290.62s, all18station arrivals pass,
0blockedlegs/endpointPawncapsulehits; pauseflags/phase/feetfreeze+resumepass. Maps/saves
unchanged. Seven centre-foot stair floor misses: rawCMC Walking+walkablesupporttrue at
every miss; capsule support is not visual foot planting. Three closeups reject placeholder
garments/idle servicepose; startupOFF retained. db6435e1 pushed. Nextcandidate promotion
work: inventory bridge/wear parity, actual player/tour/dove/connectivity, broadvisual/perf.

Grounded diagnostics and exact bird-routing fullgate9/9,32math, UBT7actions31.66s PASS
verify-ubt-0rsfzh51.log; finalPythonquick6/6. Full natural service probe with rawCMC support,
arrival/pause/resume assertions and optional stills is running; no fullroute acceptance yet.

Grounded90 runtime065856: reaches lamp4/station6, blockedlegs0, endpointcapsulehits0,
pause2.01s/feetdrift0, maps/saves unchanged. TWO visual-foot floor misses on stair ascent
(11.71cm and15.88cm); partial_findings, not acceptance. Raw CMCsupport diagnostics and
stronger arrival/pause+resume observations prepared; fullbuild running with birdroutingfix.

Grounded fresh-process065701 verified exact saved map hash and protected Content hashes,
plus local reload stability and explicit mode/stance/body guards. Cross-process semantic
snapshot is not persisted; do not overstate that check. Native90sim motor test now running;
startupOFF in saved map. Audio species routing is a separate source-only worker change.

Grounded candidate configuration065445 saved/reopened with unchanged strict snapshot checks;
prior pristine churn did not recur, cause remains unconfirmed. Protected differences empty.
Map7eda28df84b35e45a6e975d39bebc23817798cc2af2db324b0121e09a30255d2.
Motor opted in, top-tread legacyX-5269.09, startupOFF. Fresh verification pending.
Final motor incrementalbuild8/8 passed verify-ubt-zo1g471g.log; source pushed153d88e0.

Grounded configuration064151 refused BEFORE saving: pristine snapshot churn.
Map0d997 and protectedassets unchanged. Helper now records exact changed keys before
refusal; diagnose rather than weaken preservation. Dwell-facing source correction is
under incrementalbuild; no physical motor has been enabled in a saved map yet.

Grounded motor source fullgate9/9,32math, UBT7actions27.98s PASS
verify-ubt-k2l70ygm.log. NOT opted in yet: sticky stalled leg repeatedly reauthorized
then refused, inflating BlockedLegs perframe; small counter/state fix pending incrementalbuild.
Root grounded-config helper prepared (onlymode/top-treadX,startupOFF). Probe now reads
actualfeet, endpointPawn capsules, optional2sim pause and fullnaturalcompletion600sim/900wall.
No native motor or fullroute acceptance yet.

External-motion protocol fullgate9/9,32math suites, UBT6actions22.93s PASS
verify-ubt-4absy7ys.log. API compile-verified only; no native motor wiring yet.
Legacy runtime behavior unchanged. Next phase must use physical arrival, never bool
validation without actual floor/capsule/zone evidence.

Top-tread probe061945: all three authored candidate points have actual floor936.00006,
normal1 and no stationary Pawn-profile capsule hit; centreX-5306.3264. Maps/saves
unchanged. This validates standing samples only, not travel. No anchors changed.
Pure external-motion API100315 focusedchecks passed; fullgate currently running.

Published collision checkpoint6ad4e09b. Next bounded wave: worker prepares pure
external-motion sequencing API/tests (NOT runtime-wired); current DLL remains prior
admission build. Root top-tread proposal probe uses prior binary and read-only geometry
queries. Proposed centre[-5306.3264,302.5689587,936.0000586] is authored from the existing
mesh top tread; no station anchors changed. Native PID47180 owned by root; requery first.

Stair V2 fresh060918 verified; live061102 simple/complex supports agree at all71
sampled positions. Endpoint actual920 vs planned936 remains wrong. Four stationary
Pawn-profile capsule samples blocked; full grounded stair path still unresolved.
Map and original saves unchanged; keep service startupOFF. Collision-only acceptance.

Stair collision V2 apply060704 saved/reopened successfully; protected differences empty.
Candidate map0d997af5802b99fbecfe77f09d94c52b6f62bb3f2900a9b6682b8025be0773cf.
Fresh-process verification running; no real collision acceptance yet. V1 preserved.
Service station anchors and startupOFF unchanged.

Stair helper060240 safely failed before map save; map009908 and protected originals
unchanged. V1 collision clone exists and must remain preserved. snapshot_row meshes
are PACKAGE paths (_asset_path strips object suffix); normalize exact CLONE package to
SOURCE package, not object paths. Retry must use fresh V2 namespace and record compact
snapshot mismatch evidence before refusal. Do not weaken unrelated-state comparison.

Admission runtime055924 now holds exactly at[-3560,0,888] before blocked leg2,
no initial movement into rejected leg. Maps/saves unchanged. Focused tests cover
large dt; live test covers natural transition only. Stair geometry still unresolved.

Admission full gate9/9,32/32math, actual UBT6actions22.76s passed
verify-ubt-axhzasun.log. Native blocked-transition probe running against new DLL.
Stair collision helper preparation is separate and has not mutated assets.

Stair collision diagnosis055245: simple collision is NOT actual tread geometry. At
index69 simple Z925.811 normalZ.721 versus triangle Z904.000 normalZ1; target endpoint
simple936.082 versus actual triangle920.000. Planned936 stands16cm above the real
second tread. Bounding footprint plus maximum Z is not a valid service stance.
Need a preserved duplicate with tread-faithful collision and grounded stance/path repair,
not tolerance relaxation. All maps/saves unchanged; admission build is running separately.

Published checkpoint63563d9c after full9/9+32math+UBT and finalquick6/6.
New per-leg admission repair prepared after that checkpoint: 100256 focused MSVC
checks pass, native build pending. Root stair simple-versus-complex trace diagnostic
is running against the prior binary; do not attribute its findings to unbuilt admission code.

Candidate V3 live probe054619: resolved correct V3 mesh, movement observed, garment
1/1 slot applied/read back. Floor misses0, Visibility capsule hits0, native blocked legs1.
All maps/original saves unchanged. This confirms body resolution and limited movement,
not animation visual quality or full service. Startup stays OFF until grounded route repair.

Candidate saved-gold render054410 reviewed: altar detail and paroches/reliefs readable,
no clipped-white vessel glare in this view. Strong saturated gold, flat floor and vessel
geometry remain unfinished. All maps/material instances/original saves unchanged.
Candidate V3 service live90-second probe is running; route still expected to refuse.

Candidate V3 body fresh process054200 verified all configured fields and unchanged
map0099080d, no protected differences. Fresh candidate interior capture is running next.

Candidate V3 body configuration054004 saved/reopened, protected differences empty,
map0099080da4e350b387e75ad49160976582ed73f26d5d9f29500a097f9ba9e8cb.
Correct V3 mesh, idle/walk clips, Mantle slot, scale1 and yaw-90 are hard references.
Startup remains OFF; garments are explicitly stand-ins. Fresh-process verification running.

Service body V3 full gate PASS9/9,32/32math suites, UBT6actions35.47s
(verify-ubt-gqbx1ndq.log). Candidate configuration is now being applied; not runtime acceptance.

## Current continuation — 2026-09-09 05:36 UTC

Candidate service placement051407 and fresh verification051542 succeeded with startup OFF.
Runtime051751 observed movement but one native blocked leg; no full service acceptance.
Diagnostic052655 confirms the doorway-to-stone linear height interpolation leaves the floor:
index3 planned Z890.057 versus measured887.040; endpoint floor936.082 matches planned936.
Do not relax floor tolerance: grounded path interpolation and pre-movement admission both
need repair. Diagnostic changed no maps or original saves. Body V3 correction is under
full build verification, not yet configured in the map.
Candidate gold apply052235 and fresh052452 verified1113 slots; protected differences empty.
Candidate hash62c825bd16586626b3d765355c394ed190f7689cbefcb29105b7878c61984b47.
Saved candidate gold visual review remains pending.

## Current integration — 2026-09-09 04:53 UTC

Candidate intro051013435717Z also starts at0.0, finishes naturally, restores controls,
and reports zero continuous sweep/headroom hits with unchanged maps/saves. Gate images
reviewed with the same limited two-still acceptance; terrain/road transitions unfinished.
Published edc1fcf5 includes main gold and clock/service compile evidence. Candidate service
placement is now being attempted with startup off; runtime is still pending.

Main intro050722047734Z now observes playback from0.0s through natural completion,
602samples, zero continuous sweep/headroom hits, controls restored, no map/save changes.
Approach/inside gate images reviewed: opening visible and camera emerges inside.
Two stills and NoCollision traces do not certify all intermediate portal clearance.
Candidate48 same-route probe is underway. Gold saved/fresh-verified state is93483d25.

Full gate now9/9,32/32math suites; UHT+8-action UBT succeeded40.48s in
verify-ubt-7w4t65wn.log. Service adapter/version marker and cinematic timing gate
compiled. Main live intro retry with gate screenshots is next; candidate service
placement still pending. Earlier unbuilt labels below are historical.

Gold fresh process050035209417Z verifies1113 slots and unchanged map hash93483d25;
protected content differences empty. Native/orbit timing gate now has17 focused MSVC
checks; full Unreal build pending. Intro probe now requires observing the first0.5s
and never sweeps across a change of view target. Earlier late-start receipt is retained.

Gold main apply045818582514Z saved/reopened1113 slots, zero protected differences;
main SHA93483d25ff23e01ee1462845b958d9c2139f2cd2e7177cf5e3e3141dd4ae1432.
Fresh-process readback is pending. Intro startup gap is a native FTSTicker clock bug:
new callbacks consume the whole startup frame delta. Native/orbit clock correction
is in progress; do not treat the prior natural finish as complete opening playback.

Main intro retry045552785959Z naturally finished and restored movement/look controls;
all maps/saves unchanged. First probe failed on unreflected pc.get_pawn; use
GameplayStatics.get_player_pawn. One sweep hit spans the initial pawn-to-cinematic
camera cut, not a continuous route segment; probe now separates camera cuts. The first
playing sample already reports 22.92 seconds elapsed, so opening timing is under review
and full-route observation remains unproven. Do not hide that gap under a finish result.

Gold vessel A/B045055Z completed without errors, all maps/original saves unchanged.
Both 1920x1080 views reviewed: six vessel components with the existing matte gold
show more altar detail and less Shulchan white glare. Bounded improvement accepted;
map persistence is pending. Intro natural-route runtime probe now being exercised.
Candidate service helper prepared with startup disabled and legacy station anchors;
the reflected adapter version marker and four service adapter files still need UBT.
Public video download verified anonymously HTTP200 with matching SHA; release tag
scene-preview-2026-09-09, video workflow commit38078c4e.

## Movie export lessons — 2026-09-09

V5 capture accepted as a WIP preview: 960 frames at 896x504 avoid the preview downsize,
upscaled to 1280x720 H.264, 40 s, silent, 7,837,110 bytes. Eleven source frames and five
encoded samples reviewed; full decode passed. All maps/original saves unchanged.
Video SHA c44a42486e568a763dc7bb3f9cc655bbfaae94c50021fd1b55425291f4745b41.
Quick gate 6/6. This does not promote candidate48 or accept unfinished scene visuals.

User requested a shareable actual-scene video. Legacy in-editor capture produced 960
valid PNG headers but visually invalid repeated right/bottom borders. Header/count
checks are not visual acceptance. Preserve rejected exports outside Content.
Standalone capture source supports -game and -RenderOffScreen for a hidden window,
but both local standalone attempts produced no frames and were terminated; do not claim
that path verified. Use a saved sequence, isolated
AstraProbe_ saves and process-only frontend/cinematics/settings overrides. Every comma-
separated -ini override MUST repeat [Section]:Key; a bare second Key is silently ignored
by ConfigCacheIni.cpp. Disable bApplyGraphicsToEngine to prevent viewport resizing.
MovieEndFrame is exclusive (960 at 24 fps gives 40 seconds). Do not claim a video ready
until rendered shots are inspected and the encoded MP4 fully decodes.

## Publication checkpoint evidence — 2026-09-09 04:09 UTC

Main saved-scene render 040520Z inspected in both gate views: the softer wear remains
subtle and paver joints remain visible. All maps/material instances/original saves unchanged.
Candidate C applied035717263399Z and fresh-verified035912952876Z, protected differences
empty, map d3c66fea6d550233304bf5b1d5d0ab57de728150b99f47d0fc60bd09207563f3.
Candidate render040128Z: interior paroches/reliefs readable, gold vessels still too bright;
exterior camera blocked by altar, so facade-quality acceptance remains open. All19maps
unchanged during capture. Gold-vessel PIE-only material A/B is being prepared.
The four new service-adapter C++ files have focused 100240-check math coverage but are
NOT in the prior Unreal build and are excluded from the preceding publication batch until
separate build acceptance. Runtime placement on candidate is still pending. No new package.

## Verified continuation — 2026-09-09 03:58 UTC

Full gate 9/9, 31/31 standalone math suites and Unreal compile/link passed (38.69 s).
Intro now shares the 19-point eastern route between live playback and editor tooling;
runtime clearance is still pending. Surface wear was visually rejected at full strength.
Two lower-opacity PIE views reviewed: conspicuous beige overlays are suppressed at 0.12.
Nine new SurfaceDetailSoftV1 child materials preserve V2; all 460 bindings saved/reopened
and independently verified, old assets unchanged. Main hash 478d326fc715e6690272e07043dd1238912d1c53a47066fb18cb432b0027e76c.
This is global attenuation, not a repair of ignored per-entry authored opacity or opaque
mask edges. Candidate48 sky/weather saved/reopened (035500097589Z), all other maps and
protected assets unchanged, hash e3794bc08c8f84e4d81bd20fee57123cebc3b8c59e851311d12fed0d644fbd73.
Candidate map-level lighting C port is underway. No promotion or new packaged release.

## Active update — 2026-09-09 03:43 UTC

Transit bridge observed 45 boarded and 35 alighted over 180 simulated seconds, with 20
photographers. Separate static apron figures; no verified transfer of the 24 residents.
One geometry refusal and 222 trimmed requests remain recorded. Maps and original saves
unchanged. Surface V2: all 23 saved asset hashes checked, and fresh process verified all
460 decals plus manager. The asset job crashed during shutdown after saving; preserved
exit receipt distinguishes this from a clean process exit. Placement readback falsely
rejected equivalent angles differing by 360 degrees; comparisons now wrap angular deltas.
Actual six-image wear comparison was visually REJECTED: beige patches over paving/stairs.
A lower-opacity PIE comparison is underway; do not call surface visual acceptance complete.
Soundscape importer is repaired for create-once V3 import only; no native import or audition.
No new packaged release. Exact 48 cm remains approved but candidate not yet promoted.

# Mikdash native Unreal project â€” current state (2026-09-07, after the Walkthrough-06 release work)

Surface placement032730761405Z refused before save: DecalActor.get_decal is not
Python-reflected. Replaced both placement/readback accessors with
get_component_by_class(DecalComponent). V2assets/maps/protectedmaterials unchanged;
retry only decals,manager, never assets.

Transit fresh PIE032246679066Z observed180simulated seconds:45boarded/35alighted,
5groupsstarted,20photographers,0overruns/groundmisses/caprefusals;1geometryrefusal and
222request-trimmed people explicitly retained. Sampled caps passed; allmaps/originalsaves
unchanged. Separate static apron figures, not24skeletal residents or verifiedcrowd transfer;
no visual/fullroute/packagedacceptance. SurfaceV2 all23asset hashes checked after shutdown
crash; master369pixelinstructions. Separate commandlet decals,manager now running.

Surface V2 assets stage031921348536Z reports saved textures/materials, positive shader
readback and unchanged map/protectedmaterials, but Unreal then crashed at shutdown:
ModeManagerInteractiveToolsContext None not packaged (Astra-Surface-Assets log).
Do not recreate/overwrite V2. Verify saved hashes, then fresh-process placement/readback
separately. Exit evidence astra-asset-exit-20260909.json preserves this distinction.

Transit bridge saved/reopened031750944507Z, errors[], protected maps unchanged; main
ac651b57577aab3791086ee3682d91c3347b5ce1f4831ec9ad38596cca47f62a.
This is actor/reference persistence only. Bounded natural-event PIE probe prepared; no
boarding/alighting acceptance yet. Bridge owns separate staticfigures, not24skeletal
resident transfers. SurfaceDetailV2 assets-only real-RHI import now underway; stone
retuning excluded, map placement requires successful shader/asset receipt first.

Native API correction: UE5.8 Python Object has no is_a method. For loaded UClass
subclass checks use MathLibrary.class_is_child_of(actor.get_class(), cls); a passing
AST/offline check cannot establish reflected API availability. Surface/bridge repairs
under review use this and explicit Scripts import paths; no assets yet adopted.

## Active continuation â€” 2026-09-09 03:00 UTC
Pushed checkpoint dcebc3d4 completes enclosure persistence, reviewed lighting C and 24/24
V3 resident movement on both maps; it is not a stopping point or a new package. User again
explicitly asked for continuous authorized work. Sky/time-of-day integration is now active:
helper guards run before map load, process inventory parses checked CSV, references are
cached as labels before reload, revert checkpoints first, and failure status uses actual
map bytes. Quick gate 6/6 and focused review pass; first native placement refused before saving: Python MikdashWeather resolves to the
actor, shadowing the enum. Resolve the enum from the reflected start_weather property
type instead. Receipt preserves unchanged map/protected assets. Retry saved/reopened successfully: native-place-20260909T030218302603Z, zero errors,
protected maps/assets and existing saved lighting unchanged. Main SHA
4deefbcf1279c9b6bcd93f0b2507d9a5c93940bc6214da647da9094af1cf0922.
Fresh PIE capture030529Z reviewed: one clock/one clear-weather actor, settings retained,
map/materials/saves unchanged. Dark gate backlighting and bright vessels remain.
Gate receipt030841758949Z verifies90/90 anchors/meshes/poses/signs/disabledcollision with
no map write. No package or dusk/night acceptance. Earlier pending statements below are chronological and superseded by newer receipts.


## Astra resumed after Claude limit (2026-09-09 UTC)

Latest native results: enclosure diagnostic native-enclosure-runtime-Main50-20260909T013502474817Z
completed with zero errors and unchanged maps/saves; all five assets persist and limestone
instancing usage is true. Six baseline/C images from lighting-v3-capture-20260909T013656Z
were inspected: gate visible, facade stone/partition detail improved, bright highlights and
terrain/access/detail limitations remain. C saved/reopened014035693311Z and fresh-verified
014209573438Z including the new gold instance hash, parameters and explicit Nanite usage.
When copying a material instance's visual parameters onto a new child, copy its usage
overrides too; a shared parent does not carry an instance's repaired Nanite bits.

Bodies candidate012656713742Z and013228827902Z: all24 correct V3 variants, scales, capsules,
feet/head/garments and static routes;23 moved. Miryam's whole-leg admission was blocked by
old RELEASE_Resident_authored-outer-visitor-01/-02, proved by live dynamic sweeps. The five
pilot actors remain saved but are now hidden/collision-disabled and their old spawner
startup is false on both maps (retire-pilot receipts014311446956Z/014418427990Z). No actors
were deleted. Post-retirement candidate receipt resident-bodies-v3-verify-Candidate48-20260909T014551106415Z
passes all24 spawned/variant/mesh/scale/capsule/feet/head/garment/static-route/movement checks,
with both maps and original saves unchanged. Main final receipt resident-bodies-v3-verify-Main50-20260909T014759299455Z also passes
all24 on the same checks, zero errors, unchanged maps and original saves.


Verification concurrency correction: a user opened the GUI midway through standalone math
tests. The coordinator stopped its own verifier before UBT and preserved the GUI; user
authorized normal closure, and the GUI then exited. verify.py now repeats the editor
inventory immediately before UBT, not just before the multi-minute math phase.


Published checkpoint 9f3b5404 supersedes the historical status below: V15 on both maps,
1490 limestone overrides, nine V3 variants imported, transit/birds/security/service placed.
No fresh package accepted. Six interrupted source/script files were preserved under
ReviewCheckpoints/AstraResume-20260909T010506Z before continuation.
Enclosure imports had save=False: five mesh packages are absent on disk despite same-process
instance readback. Main repair saved/reopened all five packages and actor references, receipt
native-enclosure-Main50-20260909T010837451823Z: zero errors, protected maps unchanged.
Main SHA12f8fe58403c023a8ec0412ce299f328448f758adbecc368072f719f028e2454.
Fresh-process runtime verification and candidate binding remain pending. Never treat same-process readback as persistence.
Resident V3 helper compared marker package paths with native object paths; normalize marker
paths to explicit object paths before skeleton/readback/cast checks. Its old 0-movement
receipt did not resume the initially paused front end. Updated probes explicitly resume/skip
intro and body sampling uses simulated seconds with a separate wall-clock watchdog. These
are verification repairs, not evidence yet that all 24 new bodies walk.
Main body bindings saved/reopened native receipt resident-bodies-v3-apply-Main50-20260909T011239800399Z.
Candidate missing Chananel is a route refusal, not a physical blocker: the approved Aron
re-pivot changed the frame to (-6200,0,0), while the locked 25 cm route extension allowed
only zero origin. The adapter now accepts those two reviewed pivots only and retains its
source-signature, length, region/corridor and no-double-extension guards; new regression
checks cover the exact -248 cm translation. Fresh compilation and native acceptance pending.
Fresh enclosure PIE loaded all five assets and produced 467 wall, 5 gate, 4 corner and
476 foundation instances. Its trace helper then failed on UE5.8's HitResult return shape;
that receipt remains a failure, not full acceptance. Material InstancedStaticMeshes usage
was missing on MI_PBR_LimestoneAshlar. Targeted override saved/compiled in real editor
(material-instancing-20260909T011612069494Z, 389 pixel instructions, protected maps/PBR
assets unchanged). Commandlet without a render resource returned 0 instructions and was
correctly refused without saving. Fresh visual/usage verification remains required.


Latest candidate group/render test180131188281 passes sampled51parties/201grouped+35individuals,4refused,19paused,98movingmembers,minsamplegap80.03cm. Two Temple crowd zones .96/four metric zones unchanged.15/24skeletal residents stillspawn; candidate remainsunpromoted. Real scene log has zero missing/auto-set Nanite usage messages after nine-instance repair. Root inspected180225: bright clipped surfaces, amber candidate lighting and simple figures remain. This is partial runtime acceptance, not final visuals/navigation/package.

Latest material repair: nine exact PBR material instances now persist explicit Nanite usage overrides, saved/compiled receipt173857999122 and verified from different PID175937249147; maps/config/shared parent/other PBR asset hashes unchanged. UE5.8 material instances have independent usage overrides: use MaterialEditingLibrary.set_material_usage_override(instance,MATUSAGE_NANITE,True,True), update_material_instance, get_statistics, save, then fresh-process readback. Do not widen their shared parent or assume a base-material-only repair handles instances. Shared sampler counts do not equal texture counts. New helper release_nanite_instance_usage.py; historical base helper preserved. Render/cook acceptance is separate.

Latest17:33 UTC group first pass: full8/8gate,30mathsuites,actualUBT54.92sec. Native main receipt173130367390 has54stableparties/200grouped+36individuals;4unsafeclusterplacements refused,13partiespaused at10sec.92groupmembers moved>50cm,minimumsampledgap80.04cm,123maxsweeps/budget500. Original saves/maps unchanged; image173221 inspected, simple bodies/overbright surfaces remain. Grouping is on the instanced background field, not the separate24skeletal personalities. Exact allocation accounting explicitly labels partial_safe_refusal; no240-population/long-navigation/60fps/final-visual/package acceptance. Source/readback notes GROUP-NATIVE-20260908.md. UE Python optional-success bool may be consumed, yielding tuple4 or None; don't assume tuple5. Main Nanite instance usage warnings are under targeted investigation.

Latest17:13 UTC: main8e78923f5ffb76c044693f6c74faaedb64648698945bb0ba927f3395be7f21c5 adopts cooler6500K sun and skylight1.3, with sun30000lux/rotation/exposure settings unchanged. All three actual PIE A/B pairs inspected (165802894653,170147884224,170356069458); saved/reopened native-reviewed-daylight-20260908T171157734314Z, protectedtrue. Limited limestone color improvement; Heikhal clipped highlights/Kotel deep shadows remain. Candidate48 now has descriptor+PlayerStart+18tourmarkers+58paving overrides saved/reopened; candidateSHA8dc55f79b3dbcfe0ba7a15c41b3fb2da5be108766aab5a2cf7a9aae46f8a8f89, still baseline lighting and unpromoted. Main same-layout save/load deliberately displaced50cm and restored0cm error in two native probes; cross-layout behavior remains untested.

User crowd direction (2026-09-08): people generally walk in groups, with occasional individuals. Implement stable small visitor parties with shared destinations, matched pace and waiting/regrouping, retaining individual roles. Initial2â€“6 party size/~15%individuals is authored tuning, not a sourced census. Group behavior is in development, not yet built/native-accepted. Existing instanced field was independent seeding with boundary teleports; don't describe it as group-aware until the new runtime passes. Skeletal resident personalities remain a separate system.

Current main (2026-09-08 courtyard paving):480ea53fd3864b7adcaa14a3cc96419768710b8e33bed0dacd90a3731329f1b0. Adds57 exact courtyard/gateway floor component overrides using JerusalemFloorSlabsV1 (same500cm V2 texture on tops, plain limestone edges). Source/geometry/collision/gold floors protected unchanged; saved/reopened receipt native-floor-slabs-20260908T164354150280Z. Actual PIE164034569694 matched all57, shaders ready341pixelinstructions,0errors; root inspected164130/164151. Albedo-only joints, mirror repetition, amber light, side closeup and crowd floating/appearance remain limitations. ExecCmds runpy wrappers must add Scripts to sys.path for sibling helpers; failed setup receipt retained.

Candidate fittings latest: eight TI parts and eleven Aron/menorah parts saved/reopened163453/163553 with protected inputs unchanged. Tour correctly refused absent Selected48 descriptor. New release_amah48_frame.py prepares descriptor+physical-offset-preserving PlayerStart migration, not yet natively run. Do not replay already-applied fitting stages. Candidate has not received the new main paving overrides and is not ready for promotion.

Current main (2026-09-08 Jerusalem paving): dc575d8e731ce1d10de79b4313eaeca3518460fabc022a8d11fb4f17ad3f6c31. Exact platform override now uses JerusalemPavingV2 after actual walking-height A/B162509371982 and checkpointed saved/reopened adoption162815394171, protected unchanged. Pale worn limestone flags are authored from the user's reference. Lighting still amber; other courtyard floors not yet assigned. Native V1 checkerboard trial rejected/preserved. New material assets must be shader-ready in real RHI before visual acceptance; GetStatistics in installed MaterialEditingLibrary finishes only that material's shader compilation. NullRHI import/readback alone does not establish render readiness. Comparison now binds exact material/texture hashes and rejects mixed flags.

48cm candidate fittings progress (2026-09-08):218 panels and12 door parts saved/reopened161252/161350; main/default unchanged by that work. Vessel preflight stopped because optimized Nanite native bounds differ from original import bounds. Helper now matches frozen post-Nanite inventory strictly and separately checks canonical source dimensions; rerun from vessels only, not already applied panels/doors. Save/tour compiled; population adapters source-frozen with144 standalone checks, awaiting full gate and candidate native tests. Three48cm resident loops become59.52m and remain explicitly refused under60m rule.

User paving correction (2026-09-08): floors should resemble contemporary Old City Jewish Quarter pale weathered Jerusalem limestone flags. The brown regular MI_PBR_PavingSlabs is an intermediate trial, not the requested final character. JerusalemPavingV1 is an authored image study based on the user's foreground paving reference; original family photograph stays private. Native import and walking-height review must precede assignment.

Paroches update (2026-09-08): the separate design task relayed explicit user approval of V15 third-temple-handwoven-v15.png. That candidate alone may proceed through fresh-namespace/checkpoint/verification; earlier V1/V7/V9 remain held. Approved art is authored, not a source-certified reconstruction. No V15 integration yet.

Latest active map (2026-09-08 paving adoption): ad80fd54f31eea15a05618d5bc64fcb44b0c37c5e10a13059bdb8481429a2a0e. Only the Mount platform component changed from procedural PavingReview to existing CC0 MI_PBR_PavingSlabs after actual PIE A/B review. Native receipt native-mount-paving-20260908T154639922112Z.json: saved/reopened, protected maps/source geometry/material assets unchanged. Warm palette and daylight/exposure remain under review. Paroches hold is unchanged; historical pre-art restoration84199384 below predates this paving-only edit.

Paroches approval hold (2026-09-08): the user explicitly instructed the separate art task to stop sending candidates until approved and asked this task to continue other work. Do not import, adopt or publish the unapproved V1/V7/V8/V9 artwork. V7 had saved before this notice; exact pre-art main SHA841993842baeea0958a3a969165c1a002b2726c0ae407fd14f855b5fe0d1ee58 was restored from its verified checkpoint. V9 was stopped before native assets or map mutation. The unapproved V7 map/assets and source candidates are preserved locally. Receipts are under SourceAssets/sanctuary-detail; all revised source receipts require explicit user approval. This hold supersedes earlier native-review eligibility. Material expression Python setters must use reflected editor properties (TransformSourceType/TransformType), not direct attributes. Whole-panel object-local mapping is needed because the cloth mesh has per-strip UVs; exact final 48 cm cloth fit remains unverified.

Latest takeover integration (2026-09-08): tour/codex now placed with18 markers, saved/reopened,18 stops and76 entries reloaded from Content/Distribution/Tour. DefaultGame.ini overrides their old development-only SourceAssets paths; the existing Distribution NonUFS rule stages these reviewed JSON copies. release_tour.py refuses missing/stale staged content and any omitted actor group before saving. Receipt native-tour-20260908T142311093415Z.json; main SHA841993842baeea0958a3a969165c1a002b2726c0ae407fd14f855b5fe0d1ee58. Live controls/package verification separate. Placement remains legacy50 pending coordinated48cm migration. Bounded frontend probes must use unique command-line Game ini save-slot prefixes for both save and settings subsystems before PIE and verify original save-file hashes after teardown; normal quit/tour autosaves otherwise risk changing visitor progress.

Short current-state file. Chronological evidence lives in AGENTS-HISTORY.md (old entries are superseded by newer
receipts). HANDOFF-FOR-CLAUDE-CODE.md is Codex's pre-release handoff; RELEASE-NOTE-Walkthrough-06.md lists what shipped,
with receipt names. This file describes the last known state; recheck files and receipts before acting.

## Locations and publishing rules

- ACTIVE EDITABLE PROJECT: `C:\Mikdash\Working-5.8\MikdashCourtyardV3` (open `MikdashCourtyardV3.uproject`).
- Engine: `C:\Program Files\Epic Games\UE_5.8` (verified 5.8.2). Toolchain: MSVC 14.44, Windows SDK 26100, NetFxSDK 4.8.
- IMMUTABLE ORIGINAL: `C:\Mikdash\Mikdash-Windows-Transfer\EditorProject\MikdashCourtyardV3`. Never overwrite or regenerate.
- Publishing clone: `C:\Mikdash\GitHub\3rdbhmk` -> public remote `ShmuelSokol/3rdbhmk`. Project lives at
  `unreal\MikdashCourtyardV3`; research dossiers at `unreal\Research`. Preserve the root `web/` and `distribution/`.
- Publish by copying reviewed files explicitly into the clone at matching paths, verify, stage BY NAME, commit, push,
  report the hash. Never `git add .`/`-A`, never force-push, never skip hooks.
- Never publish: Binaries, Intermediate, Saved, DerivedDataCache, `__pycache__`, logs, node_modules, checkpoints kept
  outside the project (`C:\Mikdash\Working-5.8\ReviewCheckpoints`), vendored tool folders (`SourceAssets/FutureMountV1/.tools`),
  third-party reference exports (`SourceAssets/characters-review/PilgrimRigV2/MannequinReference.fbx`), or the local
  book export `mikdash book/` (605 MB PDF + 86 MB JSON; gitignored).
- Builds: `C:\Mikdash\Builds\Walkthrough-01..05` are old (05 reused 04's cook). `Walkthrough-06-rc1` is the release candidate
  (7929 packages, 0 errors, receipts in `C:\Mikdash\Working-5.8\RuntimeBuild-06\rc1`). The final fresh package is `Walkthrough-06`.
- `Config/DefaultEngine.ini`: AndroidFileServer is disabled and its `SecurityToken` is blank. The old token was public from
  commit `f52c5ff` until the release; never reinstate it. Grep specific keys rather than printing the whole file.

## Accepted map (now the default, startup and cook map)

- `/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough` (`Content\MikdashV3\IntegratedReviewV2\Maps\Walkthrough.umap`) is
  `GameDefaultMap`, `EditorStartupMap` and the only `MapsToCook` entry; `Launch-Courtyard.ps1` verifies it.
  Last saved SHA-256 `683650c441ef1f51d839d9b0b04b8df64fd4cf908188c37b9e731b6f9e402d7d` (after the keilim move).
- Protected maps, unchanged: `/Game/MikdashV3/Maps/Courtyard` (`d0417e29...`), `FutureMountV1/L_FutureMount`,
  `MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold`. Do not edit them; use them only as donors.
- Integration helper `Scripts\integrate_review_scene.py` (V2 valid; V1 stopped on a quadratic verifier). Placement helper
  `Scripts\release_place_assets.py` + `release_place_assets.spec.json` (guarded, checkpointing, receipt-writing).

## Integrated in the combined map (saved and reopened; visual acceptance still recorded as PENDING)

Future Mount platform; four cut terrain tiles rewound front-face-up on 2026-09-07 (429/566/480/454 tris, vertex colours kept);
Mount trees removed with outside vegetation preserved; two audited Al-Aqsa actors removed only in this future scenario;
Western Wall and plaza unchanged plus six `RELEASE_Kotel_1..6` overlay meshes at identity (NoCollision); sanctuary gold
finishes (7 veneers); heikhal keilim at the book positions and sizes: CC BY Titus-style menorah `RELEASE_Menorah`
`[-5330,315,925]` 150 cm, branches north-south; shulchan study `[-5300,-350,925]` (76 cm, book says 3 amot: open);
incense altar study `[-4650,0,925]` scaled to the 5-tefach amah; CC BY-SA "Ark Box" `RELEASE_Aron_Body/Lid` at
`[-6200,0,925]` yaw 0 (length north-south per Rambam 3:12; this model's poles therefore also north-south, open);
Kodesh doors (open inward) and 7 x 6 amot paroches (`Release/Doors`, 15 actors); 196 `RELEASE_Frieze_*` 250 cm Nanite
displaced gold relief panels on all Heikhal/Kodesh walls from `visual-reference-handoff/gold-palm-cherub-relief.png`
(palm-only panels removed); `RELEASE_KodeshInteriorLight`; bus `RELEASE_Bus_1..13` at `[-37951,46855,973]` on real
asphalt at the west end of Batei Mahase road; five idle PilgrimRigV2 figures `RELEASE_Pilgrims_1..5` in the outer court around
`[5000,1180]` on floor Z 300; volumetric clouds; bound wind sequence; +1 stop exposure and interior histogram fields;
compiled MikdashRuntime controller (menu, pause/release, WASD, mouse look, mute persistence, footsteps, P-key fix in the
preparation lesson); 55 cm step height on BP_MikdashWalker. Actor count 7322 (7310 before the release edits).

## Imported but NOT placed

- TransitV2 station (12 meshes): placement unset; no source-proven railway. Bus aisle too narrow for the capsule (no boarding).
- Heikhal folding door leaves (24 planned actors) deliberately not placed: the measured architecture already carries the
  four open gold door slabs. Reuse `Scripts\release_import_doors.py -DoorsPlaceOnly -DoorsGroups=heichal` only after review.
- Fetched CC models not used: GPL menorah/Aron (license decision pending), CC0 shulchan blockout (no loaves).

## Source-only (authored, native import/placement NOT run)

- Reliefs follow-ups: paroches pattern (book p. 238 shows palm + keruvim on the curtain), doorposts and lintels, seamless
  retile of the frieze image (joint every 250 cm), a sculpted keruv panel as the upgrade path (scratchpad keruv-relief-feasibility.md).
- Mount access / Kotel opening: `create_mount_access.py`, `create_kotel_opening.py`, `mount-access\OpeningV2`.
  No source-proven western gate through the sanctuary wall; do not cut protected geometry.
- Resident crowd: `ResidentCrowdRuntime.h` (520/520 checks, debug and release) and the `MikdashResidentCharacter` adapter now
  COMPILE in Editor and Game Development targets, but nothing is bound to a live character. Not an embodied population.
- Audio: CC0 wind candidate not auditioned; synthesized pilot ambience stays autoActivate=false; footsteps live.
  `MikdashSurfaceAudioRouting.h` standalone-tested, not wired.
- Incense: `SourceAssets\IncenseRepairV4` offline only; V1-V3 studies fail visually (wisps at floor level).
- Keilim still open: shulchan height 3 amot with rods, trays and 12 loaves (book pp. 241, 250); incense altar detail; Aron
  poles east-west (Yoma 54a) as separate meshes; luchot. Reference photos with the owners' permission:
  `SourceAssets\reference-ti\dossier.md` (gitignored). Book requirements table with 15 ranked gaps (Mount enclosure largest):
  `SourceAssets\research\book-scene-requirements-20260907.md`. Source review: `SourceAssets\vessels-review\book-keilim-review-20260907.md`.
- Kotel overlay hidden behind OSM slab `SM_Jerusalem_CityWalls_04_Grid_N002_P00x` 1 m west of the face (scratchpad kotel-visibility.md).
- Controls: P-key fix compiled, not keyboard-tested. `SourceAssets\runtime-review\control-audit`.

## Hard rules

1. Never rerun the one-shot bootstrap/architecture import; never regenerate or overwrite the immutable original.
2. Stage explicit named files only. No `git add .`/`-A`, no force-push, no `--no-verify`.
3. No `-skipcook` for a release package. Fresh cook with the editor closed, then launch and test the exe.
4. Never overwrite existing native asset namespaces (rerunning creators into an existing folder is prohibited).
5. Run native jobs SERIAL. Never kill the user's GUI editor; check live PIDs before build/close operations.
6. PIE/walk tests must be bounded and auto-stop. Preserve failure receipts; do not delete or revert shared work.
7. Do not claim completion from a compile, a count, an import or a mocked test. Visible/runtime acceptance only.
8. Keep measured Yechezkel architecture distinct from interpreted/authored future details. No invented halacha,
   census, railway or Temple Institute copies presented as fact. Immersion stays modest.
9. Keep `Content/Distribution/CREDITS.txt` accurate (OSM/ODbL, Mapzen/SRTM, Fantozzi/qubodup CC0, Thimras CC0 if adopted).
10. Every map or asset edit goes through a checkpoint copy under `ReviewCheckpoints` and a JSON receipt with before/after
    SHA-256 of the map and of every protected file.
11. **A material is accepted on its GRAPH, never on its flags.** Any pass that authors a master must assert, in its
    receipt: a non-zero expression count, and — for any `BLEND_MASKED` material — an actual connection into
    `MP_OPACITY_MASK`. Re-author into a FRESH asset (delete and recreate); re-authoring in place superimposes the old
    graph on the new one and yields duplicate samplers.
    *This project has been bitten twice.* cp05b cooked a superimposed graph; trees01 cooked a master whose flags were all
    correct and whose graph was **empty** (`create_material_expression` = 0), so every leaf card drew as a solid
    near-black rectangle while the usage flags read back `True`, the cook log showed no substitution, and the instances
    bound a `LeafAtlas` parameter the parent did not have. Property parity is not visual acceptance, and `-nullrhi`
    cannot draw a pixel — see `nullrhi-cannot-verify-materials`. Only a frame closes it.
12. **An asset that LOADS is not an asset that SAVED.** Any pass that imports or authors assets must save every one of
    them and then assert the `.uasset` exists ON DISK — counted from a fresh process — not merely that `load_asset`
    returns non-None. `AssetImportTask.save = False` leaves the imported asset live in the importing session only.
    *trees01b, and it cost a second cook and a second set of frames.* The leaf and billboard atlases imported, took
    their CLAMP address mode (`texturesClamped` = 12) and bound cleanly into the material instances — all inside one
    session — and were never written to disk. Meshes, masters and instances were each saved explicitly; the textures
    were not. The saved instances therefore referenced texture packages that did not exist, the cook resolved them to
    nothing, and the re-cooked frame was **indistinguishable** from the empty-graph frame of rule 11: the same solid
    near-black cards, from an unrelated cause. Two different bugs with one appearance is the reason the assertion has
    to be on the bytes, not on the handle. The session that created an asset is the one witness that cannot confirm it
    shipped.
13. **Assert the BINDING, not the loop counter — and never mutate a UE array property in place.**
    `get_editor_property('static_materials')` (and every other array property) returns a COPY, and
    indexing it returns a COPY of the struct. `slots[i].set_editor_property('material_interface', m)`
    therefore changes nothing that survives; writing the array back stores the ORIGINAL entries,
    `save_asset` saves them faithfully, and a `assigned += 1` counter records a success that never
    happened. Rebuild the array from fresh structs (`ue.StaticMaterial()`), then RELOAD the asset and
    assert the slot resolves to the intended material.
    *trees01/01b/01c — three cooks of cardboard.* The receipts said `meshSlotsAssigned: 138`,
    `meshSlotErrors: []` every time, while all 138 meshes sat on
    `/Engine/EngineMaterials/WorldGridMaterial`. The masters were right (10 expressions,
    `BLEND_MASKED`, clip 0.5, `MSM_TWO_SIDED_FOLIAGE`), the instances were right (correct parent,
    correct atlas bound), the atlases were right (binary alpha, 43% coverage) and the UVs were right
    — and none of it reached a triangle. The visible tell was that **the leaf cards and the trunk
    were the same flat dark tone**, because both were the same engine default. Rules 11 and 12 assert
    the material and the texture; this rule exists because neither of them asks the MESH what it is
    actually wearing.
14. **A hash is current only if it was taken after every other writer finished.** On a shared map
    with several passes in flight, a SHA-256 is a statement about a moment, not a property of the
    file. Re-hash immediately before quoting one, and say *when* it was taken and *what produced it*
    — never hand a hash to anyone as "safe to publish against" unless nothing has written since.
    *trees01:* my applies produced `650c2b6c…`/`9b70ac1f…`, I verified them against the live files at
    about 22:00, `OldCityStreetsV1` saved paving into both maps at 22:07:38 and 22:12:01, and I went
    on reporting the old pair for 95 minutes — including in a hand-off file that called them "safe to
    publish against". My own `trees01d` cook receipt had already recorded the real current values
    (`candidateSha256 c516fd26…`, `mainSha256 2b82ae66…`); the refutation was in my own output and I
    read past it. This is the same failure as rules 11–13 in a different costume: **a reading that was
    true once, carried forward as if still true.** State the timestamp beside the hash so staleness is
    visible rather than invisible.
15. **Identical binaries do NOT mean identical content — compare the ARCHIVE, not the exe.** A cook
    whose C++ did not change produces a byte-identical packaged exe, so the exe SHA-256 is silent
    about whether the thing you actually changed reached the build. Quoting it as evidence that two
    builds differ, or that a re-cook "took", is a category error.
    *FaceV5/people01 vs people02:* both archives carry `MikdashCourtyardV3.exe` at
    `c968b67b670e4f7d…` — the same bytes, because only a skeletal mesh changed. The honest evidence
    that the re-cook landed is the **archive size delta**, 4,250,409,929 → 4,250,436,553 bytes, which
    is the re-cooked Kohen Gadol mesh, plus the asset's own `.uasset` hash from the import receipt
    (`b732bb6d06…` → `d61a191a49…`). Cite the changed asset and the archive, and say explicitly when
    the exe is expected to be unchanged — otherwise an unchanged exe reads as a failed cook.
16. **An offline previewer that does not back-face cull cannot find an inside-out mesh.**
    *FaceV5:* the baked MetaHuman head was exported wound opposite to UE's convention. Every offline
    render looked plausible — the renderer draws both faces — so the defect shipped. The packaged
    frame showed it instantly: a see-through skull with both eyeballs visible through the back of the
    head. It had also been quietly dimming every offline render, because the face was lit by normals
    pointing away from the lights, and a brightness "correction" was added that was really
    compensating for it. Assert orientation numerically on the mesh (a nose-tip normal must point out
    of the face, a crown normal must point up) rather than trusting that a render looks right — and
    remember that a previewer's disagreements with the engine are silent, not loud.

## Native pitfalls

- Commandlet: `UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<py> -unattended -nullrhi -abslog=<log>`;
  GeometryScript needs `-EnablePlugins=GeometryScripting`. `StaticMeshEditorSubsystem` is None under `-run=pythonscript`
  but available in a hidden `UnrealEditor.exe -ExecutePythonScript -nullrhi` process; that process may quit before tick
  callbacks finish, so asynchronous PIE needs the persistent editor mechanism (`-ExecCmds="py <runner>"`, real RHI).
- TRACES RETURN NOTHING in commandlets and in NullRHI editor worlds (all 128 route probes and every placement self-test
  were NO_HIT). Only PIE (or a real-RHI editor world after the loading barrier) gives hits. Ground placements from
  component bounds when traces are unavailable and say so in the receipt (`groundSource`).
- `HitResult` fields: `break_hit_result` exists only in some launch modes (missing on `GameplayStatics` in the capture
  editor); `hit.impact_point` attribute access fails there too. In `-ExecCmds` launches use `hit.to_dict()`. Branch on
  what is present rather than assuming one API.
- Generated meshes need a winding check. UE is left-handed and front faces are clockwise when viewed from the front;
  the FutureMount cut tiles rendered black because every triangle faced down while vertex normals pointed up. Check
  `facesUp == triangles` with GeometryScript face normals (`cross(C-A, B-A)`) before saving a generated mesh.
- The archive-root `Windows\MikdashCourtyardV3.exe` is a bootstrap that exits at once; track the child process at
  `Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe` for windows, PIDs and exit codes.
- A hollow union mesh's AABB covers the whole court (`Derived union of source outer envelope walls` spans the enclosure),
  so clearance checks must decompose unions into constituent boxes (116 for the outer envelope) or every placement fails.
- `SM_KeruvimStudyV1` has 100 material slots; setting slot 0 is not enough, loop over all slots and verify `slotsNotGold == []`.
- Package: `RunUAT.bat BuildCookRun -project=<uproject> -noP4 -platform=Win64 -clientconfig=Development -build -cook
  -map=<map> -stage -pak -iostore -archive -archivedirectory=<new> -utf8output -unattended`. Wait for editor exit first.
- `spawn_actor_from_object` returns None in commandlets: use StaticMeshActor/SkeletalMeshActor class + checked `set_*_mesh`.
- Saved skeletal animation: `override_animation_data(anim, True, True, phase, rate)`, not transient `play_animation`.
- Compare numeric transform fields, not `str(Transform)` (contains memory addresses). Cache actor snapshots once.
- `new_map_from_template` with an external filename silently yields the current/empty world; use package paths and assert actor counts.
- A dirty-map guard can fire after asset saves that touch a loaded map's components; read the per-item statuses in the
  receipt before calling the whole job failed (terrain-winding-fix: four tiles fixed, overall status "failed").
- Imported architecture names carry the `architecture_` prefix; inspect exact component paths and bounds.
- Skeletal FBX export crashes under NullRHI. `SK_Mannequin` is a Skeleton; `SKM_Manny_Simple` is the mesh.
- `ActorComponent.set_auto_activate` is ignored after registration; use `deactivate()` + the `auto_activate` property.
- `unreal.Rotator` needs explicit pitch/yaw/roll keywords. `EditorAssetSubsystem.duplicate_asset(src, dst)`.
- `MP_PixelDepthOffset` is hidden in UE 5.8 Python. Multi-mesh FBX import: pass literal `destination_name='None'`.
- Loading barrier must precede warmup; early gray frames were a loading issue, not lighting.
- Receipt JSON written by PowerShell carries a UTF-8 BOM; read with `encoding="utf-8-sig"`.

## Astra takeover baseline (2026-09-07)

Current evidence supersedes the older Walkthrough-06 state above: see RELEASE-NOTE-Walkthrough-08.md and HANDOFF-FOR-GPT-ASTRA.md. Walkthrough-08 packaged launch, Start/P/preparation-P/Quit passed interactive observation; fresh east-gate and Mount-platform synthetic walk completed with zero errors (release-walk-20260907T211526Z.json). Baseline capture release-capture-20260907T210550Z preserves actual visual defects: occluded Kotel, bright gold/rear wall, plain context surfaces. Its bus-labelled image is not bus evidence because the old capture used BUS_XY/BUS_YAW candidate constants. Capture cameras for multipart props must derive from current saved actors and verify their common origin; do not reuse historical placement candidates. The new capture fix affects only the test script, not maps or runtime assets.

## Kotel repair applied after the 08 baseline

The native diagnosis matched the current source meshes (occlusion-diagnostic-20260907T211954286509Z.json). The guarded repair then saved and reopened the combined map with two duplicate city-wall cut meshes; receipt SourceAssets/kotel-detail/KotelStoneV1/occlusion-fix-20260907T212114614138Z.json. No recorded errors; protected map and original wall-asset hashes all unchanged. Combined map now aeb9f7c2998742a6f49b2f6ec5a022ee51f3a6e23950a9c97026fb8d92edebd3. Checkpoint: C:\Mikdash\Working-5.8\ReviewCheckpoints\KotelOcclusion-20260907T212114614138Z. This is an uncooked post-08 change; focused visual review pending. Lighting/context-material steps remain unapplied.

Kotel visual verification completed: SourceAssets/visual-review/release-capture-20260907T212248Z contains two post-repair views, zero capture failures, savedMapUnchanged=true. Both images were inspected: the previously blank occluding slab is gone and the block-course overlay is visible. Acceptance is limited to visibility/occlusion; smooth uniform surfaces and shallow relief still need material/lighting refinement. This remains an uncooked change for the next build.

Lighting native compatibility findings: UE 5.8 EnumBase does not support int(enum); record a verified member name and the numeric repr only when available, preserving named restore. ExponentialHeightFogComponent's editable bool is enable_volumetric_fog (bEnableVolumetricFog in the installed header), not volumetric_fog (the setter is named SetVolumetricFog). Two failed apply attempts preserved the map bytes and their receipts/checkpoints. Do not infer that dry-run discovery exercises setters or newly created components.

Lighting apply succeeded on the third attempt: SourceAssets/lighting-review/native-apply-20260907T213137023951Z.json, lighting_polish_saved_reopened_visual_acceptance_pending, 82 changes applied, zero skipped, protected hashes unchanged. Morning sun/auto exposure/fog/fill are now in the working map; native visual comparison is pending. Earlier failed receipts are preserved.

Interior exposure review: EV8 minimum (raw luminance 256 with extended range off) made the Kodesh nearly black in release-capture-20260907T213307Z. Guarded release_interior_exposure_fix.py restores the prior EV0 minimum (1.0) while retaining EV14 maximum (16384). Initial save succeeded but verification encountered a stale actor reference after level reload; cache actor names before reloading, then reacquire objects. Follow-up fresh commandlet confirmed saved 1/16384 values. New renders pending. Lighting save helpers must persist mapSaved/hash immediately after save, before reopen can fail. Context textures/materials imported successfully with zero map change; assignment remains pending.

Context materials applied and reopened: native-apply-20260907T215013179583Z.json handled walls/Kotel cuts; native-apply-20260907T215118571170Z.json handled 4567 remaining meshes, zero errors, protectedMapsUnchanged=true. Total 4627 meshes across seven categories; both KotelCut duplicates explicitly included. Combined map bytes remain d505aa543a106183d849880ada6a4c38d075c3cde8f08239bea41ecee266ae4b. IMPORTANT: shared StaticMesh material dependencies changed, so donor maps may look different despite unchanged .umap hashes. Context visual acceptance pending. Credits now enumerate all seven architecture and six context CC0 photographic texture sets.
Exposure capture release-capture-20260907T214622Z: three views, zero failures, savedMapUnchanged=true. Heikhal and Kodesh images inspected; Kodesh visibility regression is resolved, Aron/relief readable; Heikhal back-wall highlight remains too bright for final-quality acceptance. Spec now carries EV0 floor for future apply consistency. Public source accuracy/keruvim/model fidelity gaps remain open.

Bus native audit found 991 mismatched effective material slots across the thirteen multipart meshes. Isolated BusVisualAuditV1 repair saved/reopened; capture release-capture-20260907T220851Z inspected: ivory/teal body and transparent glazing now visible. release_adopt_material_reviews.py -AdoptBus adopted only those component materials, saved/reopened with unrelated scene snapshot and protected hashes unchanged; combined map now18b87c00447685f1102858f5344ba8f0e12cc3405064dc479ab69fc682a51155. Tire/road contact remains unverified. KotelSurfacePolishV1 rejected visually for parallel sine bands; V2 uses continuous3D noise, native capture pending.
Resident population Editor C++ build passed (Astra-Population-Editor-Build.log). Isolated review map native-resident-review-20260907T222556423474Z saved/reopened with source map/assets unchanged; behavior NOT tested yet. Whole-scene snapshots must key by actor native name, not editor label: duplicate labels are legitimate. EditorActorSubsystem factory logs can show intermediate placement (Z492) before its final SetActorLocationAndRotation; saved/reopened body Z396 and capsulehalf96 establish feetZ300. Do not lower actors from intermediate spawn logs.

Kotel photograph import: cache whole-scene actor inventory once per verification, never call inventory() inside a per-actor generator (7300 actors causes quadratic native calls). PhotoSurfaceV1 partial import was stopped at that verifier; assets/checkpoint preserved. Corrected rerun uses fresh KotelPhotoSurfaceV2. User photos are private attachments; only cleaned wall derivative belongs in publication, with AI reconstruction/aspect-fit limitations recorded.

Kotel photo-color pass adopted into main: photo-adoption-20260907T225252321046Z.json, saved/reopened with protected hashes and unrelated actor state unchanged; SHA 17ca6fe7ab34a7a5fb56cd99c645b8921a205967f3bb8d9410f0832cf195d7a3. Four noncolliding photo panels cover the audited source faces and six procedural overlays are hidden. Native review release-capture-20260907T224816Z inspected both images, zero failures. Acceptance limited to photograph-color application; softness, flat relief, warm light and stretched stone proportions remain open. This post-08 update is not yet cooked. Python root_component is exposed via get_editor_property, not get_root_component(). TextureSample Coordinates is shortened to UVs by the material editing API.

Dove/resident integration: native Editor build Astra-Dove-Resident-Editor-Build.log succeeded. Five residents adopted into current map with default-off population BeginPlay opt-in explicitly enabled only for the configured actor; source mesh/animation and donor hashes unchanged. Main SHA2edb00afb822cb44e1f528fc03f5783d15d0e7a4faf043456b0060b7d96fc9bd. native-flight-20260907T231003184270Z.json passed live PIE: dove moved23.30m, ascended15.94m, pause drift0, restored same walkingpawn/position with collision, all five residents physically arrived. This is a small authored pilot, not a complete populace. Visual/keyboard acceptance pending. Flight F toggle uses separate original stylized whitebird pawn, Space/Ctrl altitude and Shift boost. The original walking pawn stays collision-enabled at departure. PlayerController get_pawn is not Python reflected here; use GameplayStatics.get_player_pawn.

Walkthrough-09 freshly packaged at C:\Mikdash\Builds\Walkthrough-09 (UAT exit0,230s, mainmapunchanged). ActualchildSHA b20685fc7021cab1cb2728576db025d03404f7515880016f5fa862729de87c11. Menu dove request now queues untilgrounded up to3real-time seconds and shows failurestatus. Game/editor bothcompiled duringcook. Packagedwindow opened and menu visible behind WindowsFirewall prompt; user asked to clickCancel. Do not automate that security prompt. Packagedmenu/F-return/visual/audio checks remain pending in SourceAssets/runtime-review/walkthrough-09/launch-receipt.json. All five residents and dove movement/pause/exactreturn passed mainPIE before packaging. Native walking receipts225836 andsanctuary230012 bothzeroerrors. Currentinteractive game childPID43340, bootstrap12764; requery beforeanyaction.

Download release preparation (2026-09-07): Walkthrough-09's combined ZIP is 2,277,773,468 bytes, above GitHub's per-asset limit of less than 2 GiB. Publish App.zip and Data.zip with the same extraction root; Data contains only MikdashCourtyardV3/Content/Paks/MikdashCourtyardV3-Windows.ucas. UAT did not stage loose Content/Distribution/CREDITS.txt, so distribution preparation explicitly includes credits and third-party notices. Never include private photo originals, project Saved logs or source books. A custom C# downloader was rejected by Windows antivirus during actual launch; it was not allowed, bypassed or distributed. Its source is preserved outside the publishing clone. Use ordinary ZIP distribution. Standalone packaged controls remain unverified behind the existing firewall prompt; native PIE test evidence does not remove that limitation.

Walkthrough-09 download preview published: https://github.com/ShmuelSokol/3rdbhmk/releases/tag/walkthrough-09-preview . Final App ZIP 173147367 bytes SHA256 8a9a0d6f1db9d022181e2fcdde3e0a477beedbdcbd638e2fb25b1159b8b89911; Data ZIP 2104623696 bytes SHA256 32d4a90fe09e88dadf3c46679f85601363a9c6c420865f74b5affcffb6a939c3. Both downloaded fully without authentication, matched expected archive hashes, extracted to a new folder, and all 49 original runtime files matched the original package. Receipt in publishing clone distribution/windows/public-download-receipt.json. Release is an explicit prerelease; packaged interactive checks and broader visual/source-accuracy work remain incomplete. Distribution instructions/source committed as bcc8e53d. No custom setup executable was published.

Claude overnight takeover: read HANDOFF-FOR-CLAUDE-FABLE-OVERNIGHT.md first. It supersedes obsolete unapplied-step claims in earlier handoffs, records the verified 09 public download, and prioritizes visual improvements plus fresh candidate verification. At creation, no Codex agents/native build jobs remained active; existing 09 game processes still existed, so requery before process actions.

Astra resumed 2026-09-08: user handoff says prioritize integration of landed Walkthrough-12 systems, not source-only completion. Maximum four active Codex agents including coordinator (current runtime slots); bounded waves, no overlapping native jobs. Amah stays 50 cm and enclosure scenario stays unchanged pending user's decisions. MetaHuman Core Data is installed; MetaHumanCrowd is absent from .uproject. Tests belong Plugins/MikdashRuntime/Tests outside Source. Localization staging now explicitly includes Localization/Mikdash as UFS (paths relative to Content); packaged readback still requires a fresh cook. PID2316 observed as Claude's bounded perf_probe with 1680-second warmup/1900-second limit; do not terminate it as a zombie.

Verification guard correction (Astra 2026-09-08): tasklist /FI 'IMAGENAME eq UnrealEditor*.exe' fails with an invalid-filter error, but old verify.py ignored its return code and falsely passed while PID2316 was live. Use tasklist /FO CSV /NH, check exit status and nonempty parse, then match editor names. --build now refuses to launch UBT if any pre-build check failed. Passing an old 7/7 receipt does not prove no editor was running.

Source recovery (Astra 2026-09-08): MikdashTourGuide.cpp contained an actual NUL byte inside NewKeys[Row].Add's character literal, which made rg treat it as binary. Replaced with the textual C++ escaped zero terminator. Scan newly recovered source for embedded NUL bytes; successful offline math tests do not compile every Unreal .cpp. UBT verification still required.

Takeover resumed after Claude finished (2026-09-08): latest published source b28b42ec; current offline gate 7/7 and 25/25 math tests, Editor build up to date/succeeded. User has approved the book-selected 48 cm amah; earlier "awaiting user decision" wording is superseded. Active geometry remains legacy 50 cm until a checkpointed migration reconciles all dependent placements and passes native checks. Modern city, Kotel, people and physical eye/capsule offsets must retain metric dimensions. Enclosure scenario/modern-building visibility remains unchanged pending a mapped, sourced decision. Do not overwrite Claude's final source from the earlier Astra checkpoint.

Frontend probe finding (2026-09-08): native-frontend-flight-20260908T132413130117Z passed menu/settings/preparation transitions but measured zero forward flight before a short wall-clock deadline. It is a failure receipt, not flight acceptance. The diagnostic follow-up requires both simulated world time and at least 20 input ticks before measuring motion, and records velocity, pause/menu and ignored-input state; expensive Nanite/startup frames can otherwise consume the deadline before input has been simulated. Keep the real-time watchdog and verify pause using wall time.

Frontend probe diagnosis (same takeover): the repeated zero-motion result has moveInputIgnored=true throughout 60 input ticks with pause/menu false. MikdashCinematics is an automatic GameInstance subsystem and starts its native intro fallback on OnWalkthroughStarted even before a LevelSequence is placed; the intro intentionally locks movement with SetCinematicMode. Flight tests must exercise SkipIntro and verify both move/look input unlock before flight. "Not placed in the map" does not mean a subsystem is inactive. Do not reset input locks blindly to force a test pass.

Post-Nanite render startup (2026-09-08): 24 observed base materials lack saved Nanite usage flags. Editor auto-repair is transient and warns about rendering outside the editor; persist exact observed material flags with checkpointed release_nanite_material_usage.py, then verify in a fresh process/cook. Do not blanket-save all dirty assets or mistake the long initial derived-data barrier for completed captures.

Water integration audit (2026-09-08): release_water.py's HOST exemptions do not perform floor cuts. Generated court water tops are 26 cm below intact paving (599/625, 474/500, 274/300 cm), with submerged kerbs too. The generated manifest already acknowledges the missing boolean. Require exact cavity openings in duplicated host render geometry and collision before calling the stream integrated; raw actor AABBs and a successful placement receipt cannot prove visibility.

Native integration (2026-09-08): FX director/materials and 240-agent crowd saved and reopened successfully; see TAKEOVER-STATUS-20260908.md for receipts. This supersedes "none placed" for those two systems only. Crowd command-line parser must pass the literal 'CrowdCount=' to parse_param_value; using 'CrowdCount' returns '=240' and fails integer conversion. Direct/menu dove flight must finish the cinematic before possession, otherwise cinematic input locks/view handover can conflict with the bird. A fresh C++ build passes; physical controls and visual acceptance remain separate.

Diagnostic camera trap (2026-09-08): the four saved review CameraActors have manual outdoor exposure ISO100/f8/1/125 and post_process_blend_weight=1. Their exposure overrides the adaptive global volume, making indoor screenshots misleadingly dark. This was confirmed by native lighting-inventory and Content/Python/v3_materials.py, not inferred from a frame. For a walking-equivalent PIE diagnostic, set the temporary PIE camera's blend weight to0 and verify actual PlayerCameraManager location; never change room lighting to compensate for that camera override. Menu/direct flight regression uses separate fresh PIE entries because the once-per-session cinematic setting is protected; do not try to rewrite it in Python tests.

Pacing correction (2026-09-08): the user again corrected stopping after a verified checkpoint. A checkpoint is an intermediate result under the standing sustained-build instruction. Continue independent authorized build/test/fix work; only the specifically held paroches designs require approval. Report actual activity honestly rather than implying work continues after a turn ends.

Verification launcher correction: passing an already quoted Build.bat command as a subprocess list element adds literal escaped quotes before Program Files and prevents UBT starting. Scripts/verify.py now invokes its fixed local batch command with shell=True and preserves both stdout and stderr in a unique external verify-ubt log. A launcher failure is not evidence of a C++ compile failure.
## Collision state verification — 2026-09-09 08:41 UTC

Kotel walk084132 now ascends and reaches platform/upper-deck return, but then deflects
south near x=-13585 and leaves the corridor. Preserve failure; forward capsule diagnostics
are added without changing route/capsule/tolerances. Walking roundtrip is NOT accepted.
Capture084353 failed before images: ThirdPartyFolder is protected even under its raw name.
Verify public BuildCredits output coverage instead; do not add an API solely to bypass this.

Full gate passes 9/9 and 32/32 math; UBT succeeded (verify-ubt-5icewpn7.log).
The nonfatal ServiceActor own-header-order diagnostic is corrected in source; rebuild pending.
Native candidate-collision-restore-20260909T083903043338Z passes five instantaneous
state/explicit-restore checks across 269 selected actors, including original-false fixture
and protected Kotel collision. Maps and original saves unchanged. This does not establish
partial-transition, independent EndPlay/rebuild, or walking-route acceptance. Kotel walk is next.
Visible Kotel V2 samples the cleaned photo palette but uses generic sandstone textures;
the retained PhotoSurfaceV2 materials project world-position imagery and are not currently visible.
Do not claim the actual photo is applied to V2. A PIE-only material comparison is being prepared;
photo joints and procedural geometry may mismatch, and the panorama is aspect-fitted.
## Wider visual/credits check — 2026-09-09 08:49 UTC

Capture084554 completes two inspected PNGs with zero errors/failures and all maps,
material instances and original saves unchanged. Native BuildCredits includes all18
reviewed names; screen/package readback remains separate. QPC intervals at1014x550:
north p50/p95 23.70/27.89ms; Kotel22.31/25.50ms, each8seconds. Not packaged FPS.
North entrance is readable but top still cropped; wide Kotel is visible with generic
dark masonry, sparse gray figures and haze. Photo-on-stone A/B is running, not adopted.
## Photo comparison and access finding — 2026-09-09 08:56 UTC

Photo A/B084910 passes four transient assignments, restoration and preservation.
Root and independent verifier accept the photographed weathering as a limited improvement;
explicit visual-acceptance-20260909T0854.json pins the two images/receipt and limitations.
No adoption yet. Photo joints can mismatch V2 geometry; panorama stretch/haze remain.
Kotel return failure085303 repeats, but forward capsule lifted5cm reports no hit near
deflection. Next diagnostic uses the actual capsule centre to detect shallow contact;
do not claim a dynamic actor or platform cause yet. Original maps/saves remain unchanged.
## Clean rebuild — 2026-09-09 09:00 UTC

Full gate9/9,32/32math and UBT4actions16.54s pass in verify-ubt-3x8p_4_e.log;
ServiceActor own-header diagnostic is resolved, log has no warning/error matches.
Candidate-only photo material adoption is now running under the explicit visual receipt.
Fresh process verification is still owed; do not publish a saved-map claim before receipt.
## Candidate photo materials saved — 2026-09-09 09:02 UTC

candidate-photo-depth-20260909T090038688444Z reports saved_reopened, four slots,
zero errors/protected differences/new Content files. Candidate SHA is now
dcea5bf85498cabd519c182e3665792cbe732d358ebac94cdfcdec0032c0e7e1.
Only candidate V2 material overrides changed; photo source assets/Main remain unchanged.
Checkpoint CandidateKotelPhotoDepth-20260909T090038688444Z preserves the old map.
A separate process is verifying persisted scene/material identity now; default/cook remains Main50.
## Photo adoption independently verified — 2026-09-09 09:04 UTC

Fresh process candidate-photo-depth-20260909T090248379625Z passes four saved materials,
canonical unrelated scene baseline and protected-content checks, zero errors/new files.
Candidate dcea5bf8 is ready for the next access diagnostic; visual acceptance stays limited
to weathered photo appearance, not joint alignment/lighting/finished characters.
Source/visual/collision checkpoint is being verified for publication. No fresh package yet.

## A material is not accepted until a frame shows it

Added 10 Sep 2026, after `M_AntiRepeat_Triplanar` shipped onto 1,488 Herodian ashlar slots across
both maps and had to be reverted.

Its acceptance was numeric parameter parity after save and reopen, plus an offline field
simulation. Both were real and both were green. **Neither draws a pixel.** The build ran under
`-nullrhi`, where `get_statistics` returns 0 for every shader counter because no shader map
exists at all — the receipt said so honestly, and it was read as a missing nicety rather than as
the acceptance gap it was.

What it missed: the material selected mips roughly 3–4 levels too coarse on Nanite meshes.
Measured with an in-frame control — same textures, same tiling, same frame, same exposure —
surfaces on stock `M_PBR_Tiled` held gradient energy at ×1.03 while the new master fell to ×0.20.
On the ashlar that predicts colour, coursing and bed joints surviving while the drafted margins
and proud bosses disappear: the precise character the wall exists to show, failing in the way
that still reads as "a stone wall" in a still.

The cause is worth knowing because it is not "Custom nodes are unsafe". Other Custom-node
materials here sample textures perfectly well, because they let the sampler take derivatives
implicitly. This one passed hand-computed derivatives from a **warped** UV into
`Texture2DSampleGrad`, and under Nanite `ddx`/`ddy` are not ordinary quad derivatives.

So, for any material change:

- Parameter parity proves the asset carries what you wrote. It never proves what reaches the
  screen. Say which one you have.
- Acceptance is a real-RHI frame with an **in-frame control** — an unmodified surface on the
  parent material, in the same image, so the comparison shares lighting and exposure. That
  control is what made the gold measurement conclusive and its absence is what let this ship.
- `-nullrhi` is what makes a build possible on this box and what makes it unverifiable. State
  both halves with equal weight.
- If the machine cannot render, the honest status is *unverified*, not green.

---

## Herodian ashlar V5, 10 Sep — four things that cost time, written down so they cost nothing again

**1. A commandlet's flags are NOT in `sys.argv`.** UE consumes them. Read them off
`unreal.SystemLibrary.get_command_line()` and regex for your switch, exactly as
`Scripts/release_herodian_ashlar_v4.py:1017` does. A script that parses `sys.argv` finds no mode, exits
0 in 0.09 s, writes no receipt, and the UAT log says *"Python script executed successfully"*. It looks
exactly like a pass. **If no mode flag matches, raise — never return quietly.**

**2. `release_herodian_ashlar_v4.py`'s importer REUSES an existing asset path** without re-reading the
file (`import_texture`, `does_asset_exist` → `record['reused'] = True`). Regenerating the source PNGs in
place and re-running `-HerodianV4Import` therefore keeps the OLD pixels and still passes every readback
and hash check. To change a texture's content, import to a NEW asset name and repoint the material
instance's texture parameter.

**3. The ashlar blocks are NOT instanced, and no brief should say they are.**
`SM_0138_architecture_Inner_eastern_gate_wall_jamb_1` — the wall the walking-height frame is aimed at —
is one box: **8 vertices, 12 triangles, `uvLayers: []`** (`SourceAssets/architecture-manifest.json`).
The whole 2,633-mesh measured-architecture set averages ~20 verts, carries no UVs at all, and even the
Blender arris bevel is listed under `excludedRenderOnlyModifiers`. Every course, joint, drafted margin
and boss is triplanar texture from `M_PBR_Tiled`. There is no per-block instance array to jitter, and
"make the boss geometry" means building a HISM ashlar system from scratch.

**4. High-frequency texture metrics are meaningless until the images are at the SAME px/cm.** The wall
is authored at 6.83 px/cm and the approved paving at 2.51. Compared natively the micro-grain gap looked
like 18x; box-downsampled to a common 2.5 px/cm by `Scripts/measure_stone_grain.py` the honest gap is
7.8x. Match the resolution first, then quote the number.

**And the design lesson underneath all of it:** a boss fails to read as raised not because the relief is
too shallow but because the *ramp* is too narrow to survive mipping. V4's boss-edge bevel was 0.40 cm =
2.7 texels at mip 0 and under one texel at mip 2, which is the mip actually sampled at 4 m — so a
near-vertical arris (normal deviation p50 0.968) mipped down to a flat grey line and the wall read as
engraved. Width beats depth. Check the ramp against `TilingCm / textureSize × 2^mip`, not against the
measured centimetres alone.

**Outcome of that pass, for the record:** the boss fix worked in the cooked frame — see
`SourceAssets/material-review/HerodianAshlarV5/sources.md` → "THE VERDICT FROM THE FRAME". Two cooks
were needed: `cp11b` fixed boss/grain/colour and introduced an extreme per-block value spread
(chocolate blocks beside cream), which `cp11c` corrected by halving V4's `weathering` and
`weather_dark`. **A paler base makes an existing weathering spread look far stronger** — when you
lighten a palette, re-check the per-block darkening in the same move.

---

## Anti-repeat, implicit sampling on the V5 stone, 11 Sep 2026 00:40-01:00Z — detail fixed, repeat not

Result in `Scripts/release_antirepeat.spec.json` → `status2026_09_10.implicitV5FrameTrial2026_09_11`,
evidence `SourceAssets/material-review/AntiRepeatV1/frame-evidence-cp13t-implicit.json` (verdict FAIL).
Nothing reached Candidate48 or Main50.

**The mip fix works.** `-AntiRepeatSampling=implicit` held wall gradient energy at x0.88-0.90 of the
stock wall (normalized by the unmodified paving in the same frames, which moved x1.006), against the
old x0.20, and the boss still reads raised at 1:1. So explicit gradients from a Custom node really were
the 09-09 defect.

**The scheme does not break the repeat on this tile, and it cuts stones.** One-tile autocorrelation
x0.84, comb x0.94. Mirror and band offset act on the 300 cm CELL; the ashlar's stones straddle the cell
edge, so "seamless at the texel" is not "seamless at the masonry": mirror flips put a false ridge through
the middle of a boss and make ~14 cm sliver stones, and the lost seam guard dashes the bed joints. Do not
re-propose UV mirror/offset for a structured coursed tile. Break the repeat with several layout-identical
tile variants (different blotch seeds) chosen per cell instead.

**How to get a frame when the gate is circular.** The only box that renders is a cooked Candidate48, and
the gate refuses Candidate48 without a frame. Make a frame-trial COPY (`-AntiRepeatMakeTrialMap`, then
`-AntiRepeatCensusTrial` in a fresh process), apply there, cook both maps into one archive with
`Scripts/cook_antirepeat_frame_trial.ps1`, and capture both with `capture_frame_ashlar.ps1 -Map`. Same build,
same camera, same exposure, unmodified control in frame. Measure with `Scripts/measure_antirepeat_frame.py`
(thresholds fixed in the file before any after-frame exists).

**Traps paid for this pass:**
1. 5.8 Python renders enums as `<TextureAddress.TA_WRAP: 0>`; `str(e).endswith('TA_WRAP')` is always False.
   Parse the member name. (It refused six textures that were in fact TA_WRAP.)
2. `load_level` of a World you just made with `duplicate_asset`, in the same process, dies in
   `EditorServer.cpp:2544` "World Memory Leaks" (exit 3, receipt left STARTED). Duplicate in one process,
   load in another.
3. A cook compiling a NEW master can lose a ShaderCompileWorker (0xC0000005, jobs "Failed" with no HLSL
   message). No diagnostic means a dead worker, not a syntax error: retry once before debugging HLSL.
4. `build_master -AntiRepeatRebuild` used `delete_all_material_expressions`; now refused. New sampling modes
   build to new asset names (`spec.samplingAssets`), resolved from the receipt.

---

## Anti-repeat attempt 3, 11 Sep 2026 02:47-02:56Z: layout-identical V5 variants picked per stone. Repeat reduced, NOT broken; NOT applied

Evidence `SourceAssets/material-review/AntiRepeatV1/frame-evidence-arv3c-variants.json`, verdict **FAIL**. Frames
`SourceAssets/visual-review/arv3c-{before,after}-0{1,2}-*.png`, one build `C:/Mikdash/Builds/FrameTrial-arv3c-20260911T024717Z`.
Candidate48 and Main50 were never touched; the do_apply gate refuses this evidence.

| camera 02, same build | acU x | combU x | detail (norm. by paving, which moved x1.00) |
|---|---|---|---|
| attempt 2 (mirror + band offset) | 0.837 | 0.939 | 0.88-0.90 |
| **attempt 3 (per-stone variants)** | **0.731** (bar 0.75: passes) | **0.860** (bar 0.75: FAILS) | **0.98-0.99** |

What the eye sees: the course-by-course dark/light alternation that recurred every 300 cm is gone; stones now vary in tone
like one quarry (a few read reddish-honey, one reads pale cream). The boss still reads raised at 1:1. None of attempt 2's
defects: no mid-stone ridge, no sliver, no dashed bed joint. **But the stone LAYOUT still repeats every 300 cm and stays visible.**

**Why combU fails, measured:** per tile harmonic, k = 1-3 (>= 100 cm: stone tone, blotches) fell x0.69; k >= 4 (joints, drafted
margins, bevels, ~70 % of the comb power) held x0.92. The joints are identical by construction, so no number of surface variants
can pass this bar (the offline model gave 4 variants barely better than 3). **Next step: break the layout period itself**, e.g. a
600 x 300 cm layout tile (4096 x 2048 at the same 6.83 px/cm) that keeps the per-stone variant pick. Band-row layout choice does
NOT help: combU is measured along the rows.

**Design facts, proved, so nobody re-derives them:**
1. **Per stone, not per cell.** Every course of both V5 layouts has a stone crossing u = 0 (3 of 5 Ashlar stones, 5 of 12 Trim), so
   a per-cell pick puts a tone step through them. `T_HerodianV5v_<Layout>_StoneKey` (nearest, no mips, uncompressed, layout only):
   R = offset d to the stone's anchor (floor(centre) + 0.5), G = stone index * 17. `floor(u - d)` is the stone's home cell on every
   pixel of the stone, across the tile edge: 0 mismatches on all 2,048 rows, still exact 479 tiles out (1.44 km).
2. **Generator:** `create_herodian_ashlar_v5.py --surface-seed N --tag vX --extras`. With no seed it is byte-identical to V5b (all 12
   Ashlar/Trim maps hashed). Seeds: Ashlar 18 (vB) / 28 (vC), Trim 15 / 13, chosen so the 3-tile pool averages V5's colour
   (Ashlar R 0.752, B/R 0.886). `Scripts/prove_ashlar_variants.py` -> `HerodianAshlarV5Variants/joint-proof.json`: JointMask and
   StoneKey 0 pixels different, every generator parameter equal (1.9 cm bevel, grain, palette).
3. **Master** `M_AntiRepeat_TriplanarVariants`: M_PBR_Tiled's triplanar graph in stock nodes (234, 0 Custom, implicit samplers),
   30 texture fetches per pixel against 9. VariantEnable = 0 is M_PBR_Tiled. Built by `Scripts/release_antirepeat_variants.py`;
   apply/verify/revert are release_antirepeat.py's with `samplingAssets.variants`.

**Traps paid for this pass:**
1. **A new `MaterialExpressionComponentMask` in 5.8 starts with R, G and B ticked.** Setting only the channels you want gives float3.
   The -nullrhi editor compile reported 0 errors; the COOK failed ("Cannot cast from larger type LWCVector3 to smaller type
   LWCVector2") and silently used the Default Material. Set all four channels, and read the cook log for
   `Failed to compile Material` before capturing anything (the capture chain now refuses a cook that has one).
2. The ShaderCompileWorker 0xC0000005 on the first cook of a new master happened AGAIN (arv3b, exit 25, 3 jobs "Failed", no HLSL
   message); the identical retry (arv3c) cooked clean.
3. `check_parity` compared the whole texture dict against the three the live instance sets; it now compares only the live keys.
4. In the Bash tool, `( job1 ) & ( job2 ) & wait` ran ONLY the first subshell, twice. Launch each background job on its own.
5. The box's default Python is 32-bit (`Python38-32`): big FFTs die with MemoryError. Chunk them.
6. The offline wall model predicted combU x0.71; the frame gave x0.86. Lighting and perspective sharpen joint lines, which carry
   the fine harmonics. Trust the model for acU, not for combU.

**Left in place as evidence:** the trial map carries the variants (`antirepeat-apply-Candidate48FrameTrial-20260911T024224984387Z.json`);
the assets are under `/Game/MikdashV3/MaterialReview/AntiRepeatV1/Variants` (build `antirepeat-variantsbuild-20260911T023748988488Z.json`).
To remove them: `release_antirepeat.py -AntiRepeatRevert=<that apply receipt> -Candidate48FrameTrial`, then
`release_antirepeat_variants.py -ARVariantsRevert=<that build receipt>` (that revert path was exercised and works: `antirepeat-variantsrevert-20260911T023705716077Z.json`).

## Anti-repeat attempt 4, 11 Sep 2026: evaluated offline BEFORE building. The combU bar cannot be passed by ANY layout break; nothing built, nothing applied

Evidence `SourceAssets/material-review/AntiRepeatV1/combu-floor-proof-20260911T032018Z.json`, from `Scripts/prove_combu_floor.py`. It reads only the
rendered arv3c frames, using measure_antirepeat_frame.py's own functions. No engine process ran, and no asset or map was touched.

**The metric identity, exact to 4 decimals on both frames.** WALL is 3840 px and the tile period 1322 px, so `comb_u` runs its FFT over
2 x 1322 px and the comb is every EVEN bin. Even bins carry |a+b|^2 and odd bins |a-b|^2 for the two 300 cm halves a and b, so
**combU = (1 + rho) / 2**, where rho is the correlation of the two halves. Control: rho 0.154, combU 0.577. Attempt 3: rho -0.008,
combU 0.496. White noise: 0.500. The bar, x0.75 of 0.577 = 0.433, therefore needs **rho(300 cm) <= -0.134: ANTI-correlated halves.** Any
wall whose halves are unrelated, including a real non-repeating one, sits at combU 0.50, which is x0.87. **Attempt 3 already reached that
floor.** Its "x0.860 FAIL" was not repeat left in the luma; it was the best any non-repeating wall can score.

| surrogate, rendered pixels | combU x (bar 0.75) | acU x (bar 0.75) |
|---|---|---|
| 600 cm period (control tile + the tile shifted), 60 shifts | 0.81-0.91, 0 pass | median 0.79 |
| no repeat anywhere in frame, 81 cases | median 0.87, 0 pass | median 0.79 |
| attempt-3 pixels + different head joints per 300 cm tile (= the 600 x 300 proposal), 360 cases | 0.83-0.85, 0 pass | median 0.73, 89 % pass |
| attempt-3 pixels + different head joints per course band, 60 cases | 0.82-0.85, 0 pass | median 0.73, 90 % pass |

**acU also has a floor.** After attempt 3, 0.374 of the wall's power is per-row mean: bed joints and course-wide tone. Every coursed
wall keeps that, because courses hold their height along the whole wall. acU is 0.379; with the row mean removed it is -0.008.

**Does the layout still repeat? Yes, to the eye.** In both arv3c frames the rising joints of every course fall at the same x every
300 cm (551 px on a 1600-wide view), and the 300 cm stone of course 3 repeats at identical length. The luma metrics barely see it,
because thin joints carry little power. A rising-joint map (|d/dx|, row mean removed) gives acf 0.044 on the control and 0.039 on
attempt 3; head joints that differ per tile model at 0.000.

**Next, a DECISION for Shmuel, not an agent:** the combU <= x0.75 bar as written is satisfiable only by a deliberately complementary tile
pair, which is itself a repeat. No agent may build to game it, and no agent may relax it unasked. A correctly posed replacement would be,
for example, (combU - 0.5) after / before <= 0.75, which is rho after/before; attempt 3 is -0.05. Or the same x0.75 bar on the
rising-joint acf, which is the thing the eye sees repeating. If a bar is accepted, the build is **course-band layout tiles with matched
bed joints** (head joints differ, no stone cut at a tile edge, no stone under the V5 minimum length, per-stone variants kept on top).
Model: acU x0.73, rising-joint acf about 0.

### The acceptance bar changed ONCE, 11 Sep 2026, and was fixed before any layout-break frame existed

The coordinator's decision on the proof above. It corrects a broken metric and does not relax a standard: raw combU <= x0.75 was
unpassable by the ideal answer, a wall with no repeat. The spec holds it at `status2026_09_10.acceptanceV2_2026_09_11`, written
before any layout-break asset was generated. `measure_antirepeat_frame.py` implements it as `ACCEPTANCE_V2`, and `do_apply` gates on it.
ALL of these are required:
1. **Joint repeat <= x0.75 (primary).** This measures the repeat the eye sees: dark thin vertical lines, `max(box_x21(L) - L, 0)` then
   `box_y41`, with the per-row mean removed. For each 196-row band, take the autocorrelation peak within +-40 px of that band's period
   as read off the CONTROL frame, then average over the bands. **The per-band period is needed because the camera's 5 deg pitch makes the
   period run 1307 -> 1416 px down the wall.** At one fixed lag the thin lines decorrelate: 0.06 on the control, which is noise. With
   per-band periods the control reads 0.538 and attempt 3 reads 0.503, i.e. **attempt 3 FAILS at x0.934**, as the eye does.
2. **rho ratio = (combU - 0.5) after / before <= x0.75.** It replaces raw combU. Attempt 3 is -0.05.
3. **acU <= x0.75**, unchanged. Attempt 3 is x0.731, only 0.019 under the bar: report the margin, and never tune to it.
4. **Detail >= x0.85**, paving-normalised (raised from 0.80).
5. **A visual JSON (`--visual`)** with every check true: boss raised at 1:1, no stone cut at a tile edge, no sliver, no mid-block seam,
   no dashed bed joint, no false ridge. If the numbers pass and no visual file is given, the verdict is `PENDING_VISUAL`, never PASS.
Attempt 3 re-measured under v2: `frame-evidence-arv3c-variants-v2recheck.json`, verdict FAIL on joint repeat only.

## Anti-repeat attempt 4, 11 Sep 2026: break the Ashlar LAYOUT with Wang-edge slices in Texture2DArrays (IN PROGRESS)

**Design.** Per course, 1-D Wang tiles; bed joints are V5's own, `layout_courses(Random(6120))`, identical in every slice.
- **Boundary types.** Every 300 cm boundary (texture u = 0, one line for all 3 courses) carries 1 of 3 boundary-stone types, hashed
  per (boundary k, cell row cy) and shared by that row's courses.
- **Slices.** Slice S(a,b) holds, per course, the type-a stone's right part, ONE interior stone and the type-b stone's left part. That is
  9 slices, plus 2 extra surfaces of each diagonal S(x,x): 15 slices, stacked into 3 Texture2DArrays.
- **Rendering.** Interior pixels come from S(a,b). Boundary-stone pixels come from a DIAGONAL slice of their type, where the stone
  wraps inside one texture, so no stone is ever cut at a tile edge. The slice switches only at analytic joint lines
  (LayoutQ/LayoutP/CourseBounds vector params), never inside a stone.
- **Cost and scope.** 9 texture fetches per pixel, as M_PBR_Tiled. The Trim keeps attempt 3's per-stone variants instance.

Files: `Scripts/create_herodian_ashlar_layouts.py` (slices, seed screen, `--prove`), `create_herodian_ashlar_v5.py`'s new
`explicit_courses` / `generate(layout=...)` (V5 output byte-identical without it: Albedo/Normal/ARM/Height hashes equal at 128 px),
`Scripts/release_antirepeat_layouts.py` (-ARLayoutsBuild / Verify / Revert), spec `samplingAssets.layouts`.

**Layout numbers** are in `SourceAssets/material-review/HerodianAshlarV5Layouts/layout.json`, from an exact search:
- **Constraints.** Every stone in [1.25 H, 3.2 H] (V5's rule). Stagger >= 30 cm within a cell row over all 81 type sequences, and
  >= 35.9 cm across the cell-row bed joint over every independent pair.
- **Result.** Jitter 30 cm (types 15 cm apart). Boundary stones are 127-133 cm, interiors 137-203 cm.
- **Hard-won:** with 300 cm segments every segment holds a boundary stone plus >= 1 interior stone, so the jitter is bounded by
  **w <= 300 - 2 x 1.25 H (34 cm on course 2)**. Random search found nothing; the exact solver did, because an ALIGNED grid makes every
  cross-boundary joint pair >= 127 cm apart automatically. Only same-boundary stagger matters.
- **Colour.** Surface seeds were screened at 128 px so the pool keeps V5b's colour: pool R 0.7521, B/R 0.886.
- **Offline prediction** of the joint-repeat ratio: median x0.43, worst x0.67 over 8 hash seeds.

**Traps paid for in this pass:**
1. **Texture2DArray creation is behind `r.AllowTexture2DArrayCreation`** (Texture2DArrayFactory.cpp:40). The factory's
   `InitialTextures` is not Python-visible. `set_editor_property('source_textures', [one])` then `(..., all)` drives
   PostEditChangeProperty -> UpdateSourceFromSourceTextures. **The create path forces MipGenSettings = NoMipmaps and
   NeverStream**, so mips must be turned back on and read back. `SourceTextures` is editor-only, so the slice textures do not cook.
2. The Bash tool turned a Python `'\n'` inside a heredoc into a real newline: a SyntaxError in the written file. Write Python with
   the Write tool.
3. The acceptance metric at a fixed lag misses thin joint lines: the camera's 5 deg pitch moves the period 1307 -> 1416 px down
   the wall. The joint metric uses a per-band period read off the control frame.
4. 32-bit Python generates a 2048 slice in about 5 min. UE's bundled 64-bit Python 3.11 runs the stdlib generator faster and has no
   2 GB limit: run parallel workers on it, 3 at a time (RAM).
- 04:24-04:33Z: 15 slices PROVED (`HerodianAshlarV5Layouts/layout-proof.json`). Build `antirepeat-layoutsbuild-20260911T043003676054Z.json`
  BUILT, with 50 new assets under `/Game/MikdashV3/MaterialReview/AntiRepeatV1/Layouts`. Fresh verify passed. The Trim's 9 reused
  attempt-3 assets are unchanged. On the TRIAL copy, the attempt-3 apply was reverted (`...revert-Candidate48FrameTrial-20260911T040517062924Z.json`),
  then the layouts build was applied (`...apply-Candidate48FrameTrial-20260911T043107033892Z.json`, 1,488 slots) and verified.
  Candidate48 and Main50 are untouched. Frame-trial cook `arv4a` is running.
- **04:37-04:41Z BLOCKED, not by this work.** Cook `arv4a` (`C:/Mikdash/Builds/FrameTrial-arv4a-20260911T043414Z`) was CLEAN: 0 material
  or shader failures, and the Candidate48, trial and Main50 hashes were unchanged. But every capture, BEFORE and AFTER, crashed on load:
  `ObjectSerializationError ... MikdashCrowdField_0: Bad export index 277503/16970` (AsyncLoading2.cpp:3087). That includes the
  untouched Candidate48.
  **Cause:** at 04:29Z the crowd-VAT pass rebuilt the `MikdashRuntime` EDITOR plugin after changing `MikdashCrowdField.h/.cpp`.
  The staged game exe is still the 09-10 22:10 build. The cooker serializes with the new class layout and the old exe cannot read it.
  **TRAP for every agent: after a C++ change, a cook without a matching Game-target build produces a build that crashes on load.**
  Fix: a Game-target build (UBT; not this agent's to run). Then rerun the cook + capture only:
  `scratchpad/chain_v4_cook_capture.ps1 -Label arv4c -RetryLabel arv4d`. A detached watcher (`watch_exe_then_capture.ps1`) does this
  automatically when the exe is newer than the plugin DLL. Then measure with v2
  (`measure_antirepeat_frame.py --sampling layouts --visual <json>`). Candidate48 and Main50 are NOT touched and must not be until
  that evidence reads PASS.
  The trial map carries the layouts apply as evidence. To remove it: `release_antirepeat.py
  -AntiRepeatRevert=<...apply-Candidate48FrameTrial-20260911T043107033892Z.json> -Candidate48FrameTrial`, then
  `release_antirepeat_layouts.py -ARLayoutsRevert=<...layoutsbuild-20260911T043003676054Z.json>`.


### 2026-09-11 ~04:30-05:00Z - Crowd VAT: the instanced crowd is now vertex-animated (both maps), frame acceptance pending

* **TRAP (from the coordinator, recorded here as asked): after ANY class-layout change in MikdashRuntime
  (UPROPERTY added, removed or reordered), build BOTH targets.** Editor: `Build.bat MikdashCourtyardV3Editor Win64
  Development -Project=<uproject> -WaitMutex -NoHotReload`; Game: `Build.bat MikdashCourtyardV3 Win64 Development
  -Project=<uproject> -WaitMutex`. Always from a generated .bat calling Build.bat by FULL PATH (this box sets
  `NoDefaultCurrentDirectoryInExePath=1`). Otherwise the cooker serialises the NEW layout while the staged game exe
  is the OLD one, and every packaged capture crashes on load: `MikdashCrowdField_0: Bad export index 277503/16970`
  (AsyncLoading2.cpp), even on an untouched map. My editor-only rebuild at 04:29Z (new AMikdashCrowdField
  UPROPERTYs) did exactly that. `Checkpoint-Build.ps1` passes `-build`, so checkpoint cooks rebuild the game
  themselves; frame-trial cooks and bare captures do NOT.
* **What changed.** `AMikdashCrowdField` gained an opt-in `bUseVertexAnimation` (default false = the historical
  frozen posed meshes, code path unchanged). On: PoseMeshes are six VAT-baked PilgrimRigV3 bodies
  (`/Game/MikdashV3/Runtime/CrowdVATV1`, 2,400 tris each, WalkV2 walk 72 frames + idle 192 frames at 60 Hz,
  16-bit), material `M_CrowdVAT_V1` + 58 MIs, 11 per-instance custom floats (layout in
  `Scripts/create_crowd_vat_v2.spec.json`). Bodies are interleaved over the components (a party is no longer six
  copies of one person), paused parties idle and resume after ~9-15 s instead of standing forever.
* **No-slide contract** (`MikdashCrowd::VatCommit`, tests in `Plugins/MikdashRuntime/Tests/CrowdFieldMathTest.cpp`
  VatChecks): the material draws a figure at Anchor + Velocity*(t-T0) and advances its walk phase at
  Rate = speed / (119.95 cm/s * scale) / 1.2 s from the same anchor and clamp; the CPU commits the identical
  expression at each budgeted visit and validates the NEXT segment before the figure walks it. A figure that cannot
  move plays the idle; it never walks in place.
* **Maps.** `Scripts/release_crowd_vat.py -CrowdVatApplyAll` (full guard pattern, checkpoints
  `ReviewCheckpoints/CrowdVAT-*`): Candidate48 then Main50, 240 -> 1,600 figures, only `MikdashCrowdField_0`
  changed, readback after reopen clean. Main50 also lost the 8 Sep tint fix's 15 per-component override materials
  (they would have replaced the VAT material). Revert PROVEN on Candidate48 (`-CrowdVatRevertAndReapply`): back to
  the static 240 crowd, then reapplied. Receipts: `SourceAssets/runtime-review/crowd-field/vat-v2/`.
* **NOT yet accepted:** M_CrowdVAT_V1 has only ever been built under -nullrhi. Acceptance is a packaged-build
  -dumpmovie filmstrip (`Scripts/capture_people_walk_movie.ps1 -FixedFps 10`, `-ExtraArgs -CrowdCount=240`
  re-seeds exactly the cp11 statue cluster) plus frame time (`Scripts/capture_crowd_frametime.ps1`,
  `Scripts/analyze_crowd_frametime.py`). If the first cook shows the default material on the crowd (bind pose,
  arms out, gliding), revert both maps with `release_crowd_vat.py -CrowdVatRevert -CrowdVatTarget=<map>`.
* **TRAP, measured 2026-09-11 05:00Z: in UE 5.8 UAT runs as `dotnet.exe AutomationTool.dll`, so
  `Get-Process AutomationTool` NEVER sees another agent's cook.** Checkpoint-Build.ps1's slot gate passed while a
  BuildCookRun (dotnet PID 12276) held the UAT mutex, and RunUAT died in 0 s with "A conflicting instance of
  AutomationTool is already running" (job Checkpoint-cpcrowdvat-20260911T045915Z; maps untouched). Any slot gate must
  also match a `dotnet` process whose command line contains `AutomationTool` (Get-CimInstance Win32_Process).
* **M_CrowdVAT_V1 crashed a cook (2026-09-11 ~05:01Z) and is being replaced by a stock-node V2.** The retaining-wall
  agent's cp19 attempt 1 (`Checkpoint-cp19-20260911T045925Z`) died on ShaderCompileWorker -1073741819 with three
  `M_CrowdVAT_V1` jobs in the dead batch (LightMapDensity PS x2, ShadowDepth PS; FLocalVertexFactory), 5 errors, exit 25.
  The same crash is in my own `Fable-CrowdVat-Bake-02.log`. Attempt 2 (`Checkpoint-cp19-20260911T050158Z`) cooked
  8,794 packages with 0 errors, `checkpoint_playable` - so per EnclosureMath.h 6b-ii the V1 HLSL compiled and the
  first failure was the worker dying. BUT V1 is exactly the pattern 6b forbids: author-written HLSL in Custom nodes,
  fed by PerInstanceCustomData, driving WPO and vertex interpolators - and it sampled textures in the vertex stage.
  I read 6b/6b-ii too late; the rule applies to every VAT material. Fix: `create_crowd_vat_v2.py -CrowdVatMaterialV2`
  builds `M_CrowdVAT_V2` with STOCK NODES ONLY (TextureSampleParameter2D in MipLevel mode, level 0, for the vertex
  stage; frame interpolation by Wrap addressing on V; the crossfade and 8-colour palette as stock arithmetic; the run
  refuses if a Custom node exists), re-points the six mesh slots to `MI_CrowdVAT2_*`, and DELETES the V1 master and
  its 58 instances from Content (copies in `ReviewCheckpoints/CrowdVATMatV1-*`) so no cook compiles V1 again. Maps are
  not touched (materials live on the meshes). The next cook compiles V2 cold: that cook is the acceptance test.
* **M_CrowdVAT_V2 (stock nodes) PASSED a cold cook, 2026-09-11 05:20-05:25Z.** The retaining-wall agent's
  `Checkpoint-cp19b-20260911T052025Z` cooked after the six crowd meshes were re-pointed to `MI_CrowdVAT2_*`: its log
  shows "Missing cached shadermap for .../M_CrowdVAT_V2 in PCD3D_SM6 ... compiling" and the same for SM5 (fresh DDC
  keys, i.e. a genuine cold compile), ZERO ShaderCompileWorker terminations, 8,794 packages, "Success - 0 error(s),
  0 warning(s)", `checkpoint_playable`. V1 removal is still pending: the saved mesh packages still NAME every V1
  instance even with every slot on V2, so `-CrowdVatMaterialV2` refused the delete (correctly);
  `create_crowd_vat_v2.py -CrowdVatRemoveV1` finds the property that holds them and deletes V1 only when the saved
  bytes are clean. V1 copies: `ReviewCheckpoints/CrowdVATMatV1-20260911T051456863013Z`.
* **Frame time, measured (packaged, court camera `3300 2434 380 -4 90 0`, 1280x720, vsync off, ~57 s recorded
  per run, CSV profiler; `SourceAssets/perf-review/crowd-vat/crowd-vat-frametime-summary.json`).** Before = cp17,
  240 STATIC statues: frame median 19.61 ms (51.0 fps), game 7.16, GPU 19.34; crowd cost vs `-CrowdCount=0`
  +0.07 ms frame / +0.45 ms game / +0.01 ms GPU. After = cp19b, 1,600 VAT figures on M_CrowdVAT_V2: frame 19.80 ms
  (50.5 fps), game 8.03, GPU 19.67; crowd cost +0.02 ms frame / +0.47 ms game / +0.17 ms GPU. A crowd ~7x larger and
  animated costs the same game-thread time and ~0.2 ms GPU on this GPU-bound (~20 ms) frame. Caveats: one camera,
  which sees only part of the crowd; the two builds also differ by other agents' work, which is why each is compared
  only with its own crowd-off run; `analyze_crowd_frametime.py` needs `csv.field_size_limit` raised (the profiler's
  EVENTS column overflows the default).
* **Movie acceptance (cp19b, -dumpmovie -benchmark -fps=10, court camera; frames in
  `SourceAssets/visual-review/movie-cp19vat-court-cluster240/` and `-crowd1600/`, sheets `crowdvat-cp19b-*.png`).**
  The crowd MOVES: at 1,600, figures walk mid-stride with alternating legs and counter-swinging arms, six bodies and
  varied garments, neighbours out of phase. The cp11 statue cluster (re-seeded exactly with `-CrowdCount=240`) now
  idles: frames 40 vs 84 differ in 2.05% of the cluster's pixels (>12 levels, mean 2.74) against 0% on a bare-wall
  control, where cp11 was pixel-identical. Foot plant: a standing figure's sandals match at (0,0) for 0.4 s
  (residual 2.0-3.7) like the paving control (0.2-0.4); ONE walking figure's planted sandal matched (0,0) for 0.1 s
  before lifting - a one-step visual confirmation only; the no-slide property otherwise rests on the tested anchor
  identity. Limits seen: the capture script keeps only frames after a wall-clock settle, so each movie holds 8.4 s,
  not 37 s; the Ghost camera can sit inside a crowd figure (no collision); the Youth body's short tunic shows
  cylinder legs; turns step at each CPU visit (up to MaxTurn x sweep time).
* **RESOLVED 2026-09-11 ~06:30Z: M_CrowdVAT_V1 and all 59 V1 instances are deleted; a cook passes with no V1.**
  The "hidden reference" was NOT a reference. An offline read of the saved mesh name tables showed V1 only as bare
  FNames with NO package path (V2 appears as full import paths, V1 never did), i.e. not an import. Readback proved
  what they are: each slot's `ImportedMaterialSlotName`, which UE filled from the first material assigned (V1, in the
  bake) and which is READ-ONLY from 5.8 Python (set_editor_property raises; the StaticMaterial constructor rejects
  the keyword). They stay as harmless reimport-matching names. My earlier byte-regex guard mistook them for
  references; the guard is now the engine's own `find_package_referencers_for_asset` in a fresh process (only V1
  referenced V1) plus "the re-saved package imports no V1 package path". `-CrowdVatRemoveV1`
  (`crowd-vat-removev1-20260911T062450773138Z.json`) deleted 60 assets, maps byte-identical; copies in
  `ReviewCheckpoints/CrowdVATMatV1-remove-*`. Then: V2 bake verify `verified_after_reopen`, map verify
  `read_only_verify_complete`, and `Checkpoint-cpvatv1gone-20260911T062936Z`: 8,825 packages, "Success - 0 error(s),
  0 warning(s)", `checkpoint_playable`, and ZERO `M_CrowdVAT_V1` / V1-instance lines in its cook log.
* Stale note corrected: "VAT impossible, AnimToTexture not installed" (`Scripts/create_crowd_vat.py`) was wrong;
  the plugin ships with 5.8 and bakes from Python (`-EnablePlugins=AnimToTexture,GeometryScripting`, hidden
  editor). Its own skeletal->static converter returns None under -nullrhi with no log line; use GeometryScript.
- **06:20Z FRAME TRIAL PASS (acceptance v2).** Evidence `frame-evidence-arv4e-layouts.json`, visual `visual-check-arv4e-layouts.json`,
  build `C:/Mikdash/Builds/FrameTrial-arv4e-20260911T053312Z`. Joint repeat x0.356, rho ratio -0.28, acU x0.631 (0.119 under the bar),
  detail x0.918/0.949/0.925. By eye: the rising joints no longer recur at a fixed 300 cm pitch, but a regular short/long coursing
  rhythm of similar-size stones remains. The boss reads raised; no cut stone, sliver, seam, ridge or dashed bed joint.
  **TRAP:** UAT in 5.8 runs as `dotnet ... AutomationTool.dll`, so a process-NAME slot check misses it. Two UATs collide on the shared
  `%LOCALAPPDATA%/UnrealEngine/Programs/AutomationTool/Saved/Logs/ErrorLog.txt` and the second dies in seconds (arv4c/arv4d).
  Check dotnet command lines too, require the slot free for 60 s, and treat an ErrorLog.txt lock as "slot busy", not a failure.
  Applying to Candidate48, then Main50, via the detached chain (`ARLayoutRuns/chain-v4-apply.log`).
- **06:21-06:35Z APPLIED.** Candidate48 (`antirepeat-apply-Candidate48-20260911T062104306714Z.json`, 1,488 slots, protected unchanged)
  passed a fresh verify (`antirepeat-verify-Candidate48-20260911T062307252879Z.json`). Then Main50 (`antirepeat-apply-Main50-20260911T062655840708Z.json`)
  passed its fresh verify (`antirepeat-verify-Main50-20260911T063428000110Z.json`). do_apply's v2 gate accepted `frame-evidence-arv4e-layouts.json`.
  Ashlar -> `MI_AntiRepeat_Ashlar_V5Layouts`; Trim -> attempt 3's `MI_AntiRepeat_Trim_V5Variants`.
  Revert: `release_antirepeat.py -AntiRepeatRevert=<that apply receipt> -Candidate48|-Main50`. The layouts assets can be deleted
  (`-ARLayoutsRevert`) only after BOTH maps and the trial copy are reverted.
  Still to do: look at the next Candidate48 checkpoint build's walls at walking height. The evidence came from the frame-trial copy
  in one build.

## 11 Sep 2026 - plaza, approaches and Kotel plaza made walkable (collision pass)

- **Facts found first.** The walker is `BP_MikdashWalker_C` (a BP_FirstPersonCharacter child): capsule 34/96, **MaxStepHeight 55**,
  walkable 44.77 deg, 600 cm/s, measured in the packaged build. The approach riser is 24 cm (0.5 amah at 48 cm), a real step, so no ramp
  proxy was needed. **No NavMesh exists in either map** (zero NavMeshBoundsVolume/RecastNavMesh names in the umaps): the residents'
  `FindPathToLocationSynchronously` always fails and they walk their reviewed direct corridor; the crowd field uses zones + traces +
  capsule sweeps. No navmesh was built - it would change nothing.
- **Root cause 1: the PrecinctPlazaV1 meshes had NO simple collision** (imported `auto_generate_collision False`), so the Kotel plaza's
  BlockAll HISMs and the approach HISMs gave a capsule nothing to stand on. `Scripts/release_plaza_mesh_collision.py` added ONE box
  (from MeshDescription bounds, exact) to DeckTile, WayTile, Step, Kerb, RetainingBand; Rib and Channel deliberately none. Apply
  `plaza-mesh-collision-apply-20260911T073501303208Z.json` (box == bounds on all five, 9,203 protected files and both maps unchanged,
  checkpoint `ReviewCheckpoints/PlazaMeshCollision-20260911T073501303208Z`), fresh verify `plaza-mesh-collision-verify-20260911T083819071033Z.json`.
  Revert: `python Scripts/release_plaza_mesh_collision.py --revert=<apply receipt>` (byte-exact).
- **Root cause 2: the runtime deck was NoCollision by construction.** EnclosureMath.h section 6c + AMikdashEnclosure: 144 transient
  `UBoxComponent` deck proxies whose top is 1 cm UNDER deck Z 0 (the mount platform, the residents' mount-deck floor and the
  MountPlatformDeck crowd zone are all at exactly Z 0, so they keep winning every floor sweep/trace), 5 gate-bridge boxes (the deck stops
  at the wall's inner face and the wall has no collision), and HISM instance bodies on the inside gate flights (215), retaining (10,105)
  and scarp (1,813). Ribs/kerbs/channels get none (they cross the crowd's east-way zone; crowd WorldStatic sweeps start 3 cm above
  ground). Game worlds only; switches with visibility in ApplyWeights; `-MikdashNoPlazaCollision` builds none of it. EnclosureMathTest
  `PlazaCollisionChecks` (144 boxes tile the grid exactly; each bridge spans one tread outside to half a tread inside). verify.py green.
- **Walk probe** `-MikdashWalkProbe=label=..;state=..;start=X:Y:Z:Yaw:Pitch;wp=X:Y/X:Y;delay=..;timeout=..` (development builds; logs
  `MIKDASH_WALKPROBE` with the floor component per sample). Footsteps: proxies tagged `MikdashPlazaFloor` route to stone.
- **Packaged acceptance, cp22 (`C:/Mikdash/Builds/Checkpoint-cp22-20260911T083910Z`, checkpoint_playable):**
  S2 approach climb (`SourceAssets/visual-review/movie-cp22-s2-approach-climb/`, frames 0040/0070/0125/0175): dropped onto an
  SM_PlazaV1_Step tread at feet Z -622.6, climbed tread by tread to the head landing (WayTile, feet Z 2.2), through the S2 gate on the
  bridge, onto the deck proxy (feet Z 1.2); 3/3 waypoints, 0 stuck, no fall after the initial drop.
  MODERN (`movie-cp22-modern-no-deck-v2/`): with MODERN in place before the drop (plaza collision on=0), the walker fell 54.1 m through
  where the deck stands and landed on modern asphalt at Z -5309.5; it never touched a plaza surface. The v1 run caught the switch live:
  on the deck proxy during the 2.5 s dissolve, falling in the next 0.5 s sample after it completed.
- **Defect found: the Kotel plaza did NOT collide in MODERN** although it rendered (`movie-cp22-kotel-upper-lower-v3/` frame 0076): the
  walker stood on the terrain twin 50 cm under each paving level. The actor is saved with actor collision OFF and switched on at runtime;
  its HISM instance bodies never blocked afterwards (the approach actor, same modules, collision on at load, works). Fix in
  `SetTaggedActorCollision` (MikdashEnclosure.cpp): on an off-to-on switch, `RecreatePhysicsState()` on the actor's instanced
  components. Built into cp22b; verification pending (Kotel walk, S2 after a Y-M-O-Y round trip, MODERN drop onto the approach).
- **Also in the plan, not fixed (changes the look):** in `kotel-plaza-plan.json` the upper-deck cells cover the 10-riser flight between
  the levels (slab underside 175 cm over the first tread < the 192 cm capsule), so the Kotel levels connect by a 2.5 m drop, not the stair.
- **Traps:** (1) two capture chains share one archive's `Saved/Screenshots/Windows`; the next run's cleanup deleted frames mid-copy - run
  captures on one archive from ONE chain. (2) The CSV profiler writes in 512 KB chunks: a run that renders ~100 frames leaves a 0-byte
  CSV (cp20 run at 1.7 fps during a concurrent 1,000-PNG copy). (3) A precinct-state switch dissolves for 2.5 s and tagged actors/plaza
  collision switch only at its END: a probe that sets MODERN and drops at once lands on the still-colliding deck.
- **Kotel fix VERIFIED in cp22b** (`C:/Mikdash/Builds/Checkpoint-cp22b-20260911T103748Z`, cook BUILD SUCCESSFUL; in-script smoke was
  refused by another agent's game, then `Smoke-Build.ps1 -Archive` returned `playable`; receipt
  `build-review/checkpoint-cp22b-20260911T103748Z.json`). In MODERN the walker landed on the Kotel plaza's own `SM_PlazaV1_DeckTile` at
  feet Z -982.4 (upper level, paving -984.6), walked off the upper edge and landed on the lower level at feet Z -1232.4 (paving -1234.6),
  3/3 waypoints, 0 stuck (`movie-cp22b-kotel-upper-lower/`, frames 0076 upper, 0120 lower). Log: `MIKDASH_STATE_COLLISION Actor_56:
  collision on, rebuilt instance bodies of 4 instanced component(s)`.
- **Round trip:** after YECHEZKEL -> OVERLAY -> YECHEZKEL the approach actor was rebuilt the same way (`Actor_57`) and the S2 climb repeated
  exactly (landed on SM_PlazaV1_Step -622.6, head landing 2.2, deck proxy 1.2, 3/3, 0 stuck; `movie-cp22b-s2-roundtrip-v2/`).
- **MODERN over the approach** (`movie-cp22b-modern-no-approach/`): dropped at the S2 stair's own location with MODERN in place, fell
  42.9 m straight through and landed on modern asphalt at Z -4281.4; never grounded on anything hidden.
- **Frame time at a plaza camera** (`BugItGo 64224 100000 300 -3 -123 0`, CSV profiler, real time, 45 s settle,
  `perf-review/plaza-collision/`): cp20 before 20.80 ms median frame / 8.68 game / 19.93 GPU (only 227 frames flushed - indicative);
  cp22 with collision 20.53 / 8.45 / 19.64 (2,757 frames, p95 23.98); cp22 `-MikdashNoPlazaCollision` 19.98 / 8.13 / 19.30 (2,847
  frames, p95 22.78). Collision on vs off, same build: +0.55 ms median frame, +0.32 ms game thread; the GPU moved +0.34 ms with no
  collision work on it, so the whole delta is at run-to-run noise level.

## 11 Sep 2026 - Kotel plaza stair un-buried (generator fix, plan version 2)

- **Cause** (`Scripts/create_kotel_plaza.py` build()): every deck cell whose CENTRE lay behind the 40 m split was laid at the
  upper level, and the flight runs from the split 10 m further in, so the upper paving covered nine of its ten treads - slab
  underside 175 cm over the first tread against a 192 cm capsule. The same generator also laid every tread row across
  min..max of the polygon crossings at the split: the OSM outline is concave there, so rows 1-4 crossed a 20-40 m notch
  outside the plaza, and the rear rows hung up to 3.3 m past its narrowing west edge. And the terrain twin, cut to the plan's
  deck undersides, stood at the UPPER underside under the flight (the DEM there is 2.7-4.6 m above the tread undersides).
- **Fix, in the generator (plan version 2):** nine treads, the upper deck's front edge is the tenth riser (stair head at
  depth 4900); a cell is upper only where every point is behind the head, a straddling cell splits into an upper piece and a
  lower remainder (33 cells); the whole flight footprint is paved at the LOWER level under the treads (132 cells), so the
  terrain cut - which reads the deck cells - clamps the band below every tread; each tread row is the intersection of the
  polygon's INSIDE intervals at the tread's front and back edges (rows 1-4 split in two around the notch, slivers < 1.5 m
  dropped); the perimeter follows the tread height beside the flight. Offline proof: 0 of 21,315 tread sample points
  outside the OSM polygon, 28 (0.13 %) over no cell (all within ~20 cm of the plaza edge), upper paving over a tread only at
  tread 9's back edge (max 10 cm).
- **Kept:** 926 cells, 27 wall-guard cells, both deck levels, 4 mechitza + 21 parapet. Coverage by area 99.22 % -> 99.227 %
  (the hidden lower cells count), by station 97.8 % -> 97.772 %; visible paving 83.93 % of the polygon (the flight covers
  854.9 m2). Terrain above the deck underside: 0 of 5,473 stations, worst 5.9e-06 cm, both maps. Instances 959/41/25/22.
- **Terrain:** `release_precinct_terrain_cut.py` Kotel namespace moved to `/Game/MikdashV3/KotelPlazaCutV2` (a twin is never
  overwritten in place); `-CutAssets -Candidate48` built it; the new `Scripts/release_kotel_twin_v2.py` swapped the placed
  `RELEASE_KotelPlazaCut_07_08` actor to it (checkpoint, protected hashes, save, reopen, field-by-field readback; revert
  `python Scripts/release_kotel_twin_v2.py --revert=<apply receipt>`, byte-exact). V1 stays on disk.
- **Receipts, Candidate48 first:** `kotel-twin-v2-apply-Candidate48-20260911T113803624706Z.json`,
  `native-kotel-plaza-apply-Candidate48-20260911T113906097549Z.json`, then Main50 `kotel-twin-v2-apply-Main50-20260911T114014161991Z.json`,
  `native-kotel-plaza-apply-Main50-20260911T114114275385Z.json`; fresh verifies `kotel-twin-v2-verify-*-20260911T1151*`
  (verified_fresh_process) and `native-kotel-plaza-verify-*-20260911T115[2]*` (kotel_plaza_measured_map_unchanged).
  Checkpoints `ReviewCheckpoints/KotelStairFix-20260911T112702Z` (scripts + v1 plan/manifest) and `KotelTwinV2-*`.
- **Downstream readers of the plan, NOT re-run:** `release_frame_defects.spec.json` (vegetation keep-out records "926 entries")
  and `measure_city_visibility.py`.
- **Same day, two follow-ups the walking probe found (plan and cut stay version 2 in structure):**
  (1) **Seam fins.** The plan stores cell centres to 3 decimals and scales to 6, so touching cell edges rebuilt from it
  missed each other by up to 0.00075 cm at 74 seams. The terrain cut keeps ORIGINAL ground in any gap between regions,
  so each seam was a hair-thin, full-height hillside fin standing through the paving - a 100 cm station grid cannot see it;
  the cp22c climb (`movie-cp22c-kotel-stair-climb/`) was held 8 s by one at x -20250 on the upper level. Fix:
  `release_precinct_terrain_cut.py` snaps every Kotel region edge to a 0.01 cm lattice (`KOTEL_EDGE_SNAP_CM`); offline scan
  of the merged regions: 0 gaps (131 regions, was 185). New twin `/Game/MikdashV3/KotelPlazaCutV3/...` (a twin is never
  rebuilt in place), swapped V2->V3 with `release_kotel_twin_v2.py -TwinFrom=... -TwinTo=...` on Candidate48 then Main50
  (`kotel-twin-v2-apply-*-20260911T121[35]*`, fresh verifies `...-verify-*-20260911T1217*`), cut receipt
  `native-terrain-cut-assets-Candidate48-20260911T121133563106Z.json` (worst vertex 5.9e-06 cm above the underside, surface
  outside the cut moved 0.0003 cm). The cp22d climb crossed x -20250 without a stop.
  (2) **The tenth riser.** The riser at the stair head was the upper slab's own side face, and the paving material projects
  from above, so it rendered as vertical streaks. A tenth row of SM_PlazaV1_Step now stands in front of it, its top 1 cm under
  the paving; it is advanced by the straddling upper pieces' measured overhang (19.68 cm) plus 1 cm, so its ashlar face is in
  front of every slab edge and tread 9 keeps 79.3 cm. Only step positions changed (45 steps), so the V3 cut stands; the plaza
  was rebuilt and re-verified on both maps and cooked as cp22e.
- **Seen outside this pass, not investigated:** looking west from the Kotel plaza, a mirror-image band of the city appears
  beyond the upper deck (frames `movie-cp22c/cp22d-kotel-stair-climb-*`). It is not the plaza geometry.

## Astra project access restored — 15 September 2026

Write/readback verified in the active project. The idle Unreal project-browser window was closed normally; no editor or commandlet remains. Claude's last session entries are weekly-limit notices, not active native work. Latest publication remains 8fe78604; preserve unpublished local maps and unrelated clone changes.

The cp24 city-facade capture finished all six views on 11 Sep 13:11:47 UTC. They were inspected during recovery: A1 has floating ORIGINAL decorative rooftop tanks/panels; K2 has a severe ground opening beneath the Jewish Quarter; scene visual acceptance fails. Do not mistake these legacy pale vertical tanks for the newer CityDetail dark horizontal roof plant.

Prepared Scripts/audit_legacy_roof_zones.py and release_legacy_roof_zones.py are now copied into the active project. The exact frozen connectivity audit verifies 11,400 building components / 242,764 triangles and maps all 6,007 original roof pairs. Candidate48 partition: 1,263 precinct pairs / 4,744 kept. Plan and offline review: SourceAssets/context-review/LegacyRoofZonesV1. Eight guard tests under Tests/test_roof_recovery.py passed offline; no native application yet. The release defaults to read-only preflight; apply is explicit and checkpointed, Candidate48-only. Full project gate and native readback/visual state restoration still owed.

15 Sep native follow-up: full gate 11/11, 32/32 math suites, 8/8 roof tests PASS. Native read-only preflight verified all 12,014 transforms. Commandlet apply crashed in UnrealEd before save; Candidate48 hash stayed 3f986fb6... and checkpoint is LegacyRoofZones-20260915T124545432297Z. Actor duplication must use hidden editor -ExecutePythonScript -nullrhi rather than -run=pythonscript for this pass; receipt phase markers added. Never count the crash as an application.

Editor retry duplicated and partitioned all four groups successfully (<0.000001 cm error), then exhausted Windows commit memory before map save. Disk map remains unchanged. Avoid loading the already-open Candidate48 a second time; start the editor on Engine/Maps/Entry and cap async asset compilation concurrency at 1 (supported Engine AsyncCompilationHelpers command-line flag), rather than changing system paging settings.

15 Sep final recovery evidence: commandlet actor creation through import_instances_ue58._inst_component supersedes the earlier duplicate_actor/editor recipe. It created all four groups with exact counts/transforms and copied render properties, but saving still hit Windows commit exhaustion; synchronous commandlet loading also OOMed. All attempts left Candidate48 byte-identical at 3f986fb6... . Full Windows usage was 57.4 GB committed against a 68.6 GB limit before Unreal. See SourceAssets/context-review/LegacyRoofZonesV1/native-recovery-20260915.json. No new packaged build or native application is claimed. Clear memory pressure before further native jobs; do not repeat identical crashing runs. Fresh verification groups must be compared against the apply receipt because the separate verify process has no original-component baseline.
User supplied Old City photo grids on 15 Sep: private copies at C:/Mikdash/PrivateReferences/OldCity-20260915. Visual direction and walking-view acceptance are in SourceAssets/context-review/OldCityReferenceV2/reference-notes.md. Keep family photos out of Git and game textures; use their worn rectangular paving, rough limestone, narrow lanes, arches, ramps/steps and grouped pedestrians as reference, not surveyed measurements.

Pinned-plan publishing: legacy-roof-zones.json was authored with CRLF; Git autocrlf initially changed its staged SHA. Its local .gitattributes now preserves raw bytes (-text) and recognizes CR-at-EOL for whitespace checks. Staged blob SHA must equal the native PLAN_SHA, not merely the working-copy hash. The final pre-push gate passed 7/7, 32/32 math suites and 8/8 roof tests.

Remote-access constraint, 15 Sep: Shmuel is on his phone connected by AnyDesk and rejected restarting because it would disconnect him. Do not restart, sign out, stop AnyDesk, or change networking/security services to free memory. This supersedes earlier restart suggestions. Read-only follow-up found McAfee Framework Host holding about 16.3 GB private memory; leave that service alone. The shell lacks SeCreatePagefilePrivilege. Continue work that fits available memory and preserve the connection; native save remains unverified until memory headroom is sufficient.

Live-memory helper, 15 Sep: Scripts/Expand-PagefileLive.ps1 requires ordinary administrator elevation and expands only the existing C: page file to 64 GiB, without persistent configuration changes or restart. -CheckOnly compiles interop without mutation. Normal RunAs waited at consent then returned operation canceled; helper never launched and fresh page-file readback remained 49,152 MB. Check MemoryRecovery/pagefile-*.json outside the project and fresh live counters before claiming success or retrying. Never automate UAC consent. Closing the verified idle, weekly-limited Claude CLI freed about 0.9 GB; AnyDesk was preserved. Helper compile and project gate (7/7, 32/32 math) passed.

Context coursing work, 15 Sep: native material-only audit/study uses ~1.6 GiB and fits current memory; full map saves still do not. Existing stone sources have horizontal courses, but context X walls sampled p.zy (height in U), while Y walls sampled p.xz. Scripts/release_context_materials.py now uses p.yz together with n.yz and tX.zxy normal reorientation; Y/Z unchanged. Scripts/release_context_coursing.py audits/studies/applies/verifies only the three context/CityFacade masters with byte checkpoints and all20 map hashes; do not treat review-copy creation as live application. CityFacade has disconnected old graph fragments after its earlier rebuild: traverse live output connections instead of assuming one matching Custom node in the whole expression array. Never rebuild/delete its graph just to fix UVs.

Capture lesson, 15 Sep: always construct unreal.Rotator with named pitch/yaw/roll. Positional (-19,225,0) produced a normalized camera pitch=-45,yaw=180,roll=161 in UE5.8 Python. Screenshot file creation alone is not visual acceptance: reject black/misaimed frames, read back the camera, and review native pixels. The coursing study uses an explicitly piloted camera in an owned Engine Entry editor and saves no map.

Context coursing applied at14:08Z and verified fresh at14:09Z: native-apply-20260915T140838780528Z.json and native-verify-20260915T140917908097Z.json in ContextCoursingV2. All three masters saved; exactly two connected code nodes changed each; all20 maps untouched. Three native140516Z before/after frames and a141449Z repeat visually confirm horizontal courses. Backup ReviewCheckpoints/ContextCoursing-20260915T140838780528Z. No new cook/download; cp24 still has old materials. Study exposure uses equal positive bounds (1/1); zero bounds blew out this scene. Installed UE source confirms EditorSetViewportRealtime(True) REMOVES a named override; it ensures if no such override was added. That unnecessary call caused the study's nonfatal warning and is removed; viewport invalidation plus screenshot camera locking suffice. Gate7/7, math32/32, coursing5/5 passed.

Final capture-helper cleanup was GPU-smoke-tested with -CoursingSingle at14:18Z (capture-20260915T141809Z): inspected native building comparison, correct camera, all20 maps unchanged, normal editor exit and no realtime ensure/Python error/material compile failure. Full three-material comparisons remain in140516Z and141449Z captures. All native jobs ended before publication.

Packaging continuation, 15 Sep: Checkpoint-Build.ps1 -LowMemory is an opt-in cook profile, not a Windows setting change or a hard memory cap. It requires >=8 GiB commit headroom and keeps one cook process; command-line GEditorIni overrides trigger GC at 4 GiB virtual free, bound shader queues (64 concurrent/8 precache), and allow periodic soft GC every 5 seconds within a 15% budget. EVERY comma-separated -ini override must repeat [CookSettings]:, per ConfigCacheIni.cpp. First coursing01 cook was deliberately stopped after 25 seconds when review caught bare later keys; receipt exit25 is a canceled attempt, not an asset regression. Corrected profile requires a fresh cook and live verification of logged settings. Never change security services or disconnect AnyDesk to make a cook pass.
15 Sep cook diagnosis: corrected coursing02 loaded the requested INI overrides (4GiB virtual trigger, 0.15/5s softGC) but exhausted commit at 2059/8864 packages in47seconds. CookGarbageCollect.cpp has a hardcoded60second cooldown after full memory-triggered GC; the log explicitly reports collection suppressed during that minute. LowMemory now also uses PackagesPerGC=100 (earlier independent path in PollGarbageCollection) and NoAsyncLoadingThread (cook preload cap256->32). This is a distinct bounded recipe, not proof of success. UseExistingBinaries explicitly omits UAT build for material-only previews while C++ work is in flight; it MUST NOT be described as containing uncompiled runtime work.
15 Sep revised cook result: coursing03 also exhausted commit (~10.18GiB process peak) in57seconds; it is failed, no new playable archive. Memory recovered after engine exited. Stop full-scene cook retries on this baseline. Old cp24 archive is intact; an isolated Checkpoint-roofruntime01-20260915 copy is being prepared for compiled runtime diagnostics only, retaining cp24 cooked assets. Neither the saved material changes nor pending roof C++ are in that copy until explicitly replaced/verified. Runtime diagnostics are not a substitute for a complete recook or release acceptance.
LowMemory preflight now refuses below16GiB commit headroom (the original8GiB guard was insufficient);16GiB is a conservative retry reserve, NOT a measured successful peak. Both native profile attempts failed; the option is not a verified memory fix. KotelCutClosureV1/diagnosis.md and boundary-samples.json document a separate proven missing vertical cut seam: K2 yaw175 exits the upperdeck at17.62647m with3.62001m uncovered hillside above paving, source triangle279. Native A/B is still needed to attribute every apparent mirrored pixel. Do not overwrite V3 terrain assets in place; preserve the new-namespace rule.

15 Sep packaged runtime: isolated cp24-copy plus verified game child f5e973d2693578c29da54163088aa340ec2e143dada07f897cf1a90c5ad4b2a6 passed10/10 native roof-state phases with -nullrhi, zero position error, all original transforms/materials/render settings intact, normal exit, all20maps unchanged. Receipt LegacyRoofRuntimeV1/packaged-20260915T152649Z.json. First real A1 GPU capture visually removes floating legacy tanks/panels; Modern/Overlay captures are still being reviewed. This is not a full recook; old stone shader remains in this copy.

Hebrew packaging defect found in the same game log: UMikdashLocalization searches Content/MikdashV3/Fonts but packaging staged only Localization/Mikdash and Distribution, so the two TTFs were absent. DefaultGame.ini now stages MikdashV3/Fonts as NonUFS (only regular/bold TTF and their SIL OFL license). Source files already existed; do not download replacement fonts or silently omit the license. Native readback subsequently found NotoSansHebrew in both GPU and NullRHI launches after copying those three licensed files into the isolated test archive (LegacyRoofRuntimeV1/font-native-readback.json); this does not certify Hebrew translation/RTL or glyph coverage.

15 Sep final roof acceptance: all six A1/R1 frames inspected; elevated R1 is required because ground Modern/Overlay hides roofs behind restored buildings. Yechezkel removes the floating legacy equipment; Modern/Overlay restore it on restored roofs. Latest ten-state native run packaged-20260915T153939Z.json passed with normal exit and all20 maps unchanged. The local test copy retains cp24 cooked assets: do not describe the separate saved coursing material fix as present. CameraObstructionV1 has a hypothesis and reversible show-flag tests, not a diagnosed or fixed cause. KotelCutClosureV1 proves a missing vertical geometric seam but still needs native A/B and production repair.

Continuation audit, 15 Sep: existing mikdash-three-minute-progress heartbeat was PAUSED. Updated the same automation to ACTIVE on the user's standing continuous-work/three-minute instruction, with no-restart/AnyDesk protections and no repeated same-headroom full cooks. Keep current takeover status accurate so resumed turns start from receipts, not historical pending steps.

15 Sep camera obstruction: fresh R1 GPU control rod-control01 shows the long rod (plus a smaller right-hand rod); rod-skeletal01 removes it with ShowFlag.SkeletalMeshes queried2 then forced0. This identifies skeletal rendering, not yet a particular actor. Do not remove trees or city geometry based on the earlier hypothesis. Pawn-only opt-in diagnostic is pending native verification. Capture helper now uses a unique absolute log and rejects existing receipt/PNG/log paths BEFORE writing, preserving prior failed attempts. Reused-label refusal was tested with receipt hash unchanged and no native launch.

Camera attribution resolved at16:07Z: probe-20260915T160700832Z hides ONLY the possessed walker's CharacterMesh0 (WorldSpaceRepresentation/type2) and removes both rods in the R1 frame. FirstPersonMesh stays visible; all original flags restore on Exit, cached pawn camera returns, maps20 unchanged. Earlier full-pawn probe160532280Z also passed. Production policy is now being narrowed to owned WorldSpaceRepresentation skeletal components during photo mode, not a global skeletal-render flag and not city geometry removal. Keep diagnostics explicit; normal photos should not write large diagnostic JSONs. Missing-pawn diagnostic must record failed selection rather than silently passing. Native acceptance of the default policy is still required after compilation.

Final photo policy accepted at16:15Z: Editor/Game compile+link and18 native probe phases passed, including re-entry, active Enter and both exit restorations. R1 PNG inspected without rods; onlyCharacterMesh0 selected, unselected primitives unchanged, all20maps unchanged. Receipt CameraObstructionV1/probe-20260915T161445204Z.json, childc1f56f30... . Normal photos use this narrow policy without diagnostic flags; JSON/probe/optional explicit component override remain opt-in. The isolated test archive now contains this child, rooftop repair and cp24 cooked assets, not the newer saved coursing shader.

Kotel study launcher lessons: PowerShell Math.Max/Min need explicit [long] operands for process counters above 2 GiB; the first launch was stopped by an Int32 conversion failure, not OOM. GPU Entry startup exceeded the initial4GiB watchdog with5.13GiB still free; adjusted bounded study requires9GiB headroom and preserves2GiB free, max6.5GiB private. First completed unsaved A/B/A at162119Z preserved all production assets/maps but showed only thin closure strips and a culled backdrop, so native visual acceptance failed despite passing buffer mathematics. Canonical cross-product normals do not establish Unreal front-face winding; verify the native import convention with one-sided pixels. Do not enable two-sided materials to conceal this error.

Corrected Kotel study at162720Z passed cavity-facing A/B/A: native import reverses canonical indices (a,c,b) for both closure and backdrop, preserving positions/normals/UVs. One-sided magenta surface now fills the blue opening and hiding it restores that opening. All20maps/allproductionassets unchanged and no dirty /Game packages. Visual-acceptance.json records175723magenta pixels,174147previouslyblue; A0/A1 mean channel difference0.194/255, only38pixels above8. This proves the isolated seam, not main-map integration/collision/material quality. Opposite-side culling test remains pending. Keep canonical generator/JSON bytes unchanged, and preserve its eol=lf gitattributes because geometry pins generatorSHA.

## Kotel runtime closure integration identity — 15 Sep 2026, 16:49 UTC (in progress)

The isolated cavity-facing Entry study passed; runtime integration is being prepared,
not yet compiled/verified. KotelPlazaCutTwin identifies TWO actors (terrain + deck),
so a guard must require the full KotelPlazaCutV3 static mesh object path and identity
actor/component world transforms. The closure follows the terrain owner's actual
visibility after ApplyStateTaggedActors: Modern/Overlay visible, Yechezkel hidden.
The source original terrain has both PrecinctCutOriginal and KotelPlazaCutOriginal;
it stays hidden in all three modes and must not be used as the runtime owner.
Canonical geometry winding needs (a,c,b) for native one-sided rendering; keep its
cavity normals unchanged. The loaded PlazaAshlarMaterial has correct vertical YZ/XZ
projection. cp24 still uses MacroV3, while the active asset was reparented to MacroV4
AFTER cp24 cooked. Do not misdescribe current disk materials as the packaged version.
The Kotel walk probe counts skipped waypoints in its done summary: acceptance must
require each actual reached event (0,1,2), zero stuck events, correct grounded endpoint.

15 Sep 17:08 UTC — Runtime/cooked schema trap: UPROPERTY(Transient) STILL occupies
an unversioned property schema index. The first Kotel runtime trial inserted five
reflected transient fields before older Enclosure fields; compilation passed but
cp24 crashed during AActor::Serialize with InvalidSerialize outside the export
buffer, before BeginPlay. The previous executable has been restored in the test
archive; all maps and original cp24 remain intact. Installed CoreUObject
UnversionedPropertySerialization.cpp375-387 includes all PropertyLink fields;
saving excludes transient values while advancing indices. Do not insert new
reflected fields ahead of existing fields when using an older cooked map.
Preserve the old reflected schema for runtime-only updates; Transient alone is
not serialization compatibility. Trial binary/log are preserved, not accepted.

15 Sep 17:29 UTC — Kotel closure accepted in isolated playable copy, childSHA
3aee6ac4d129e6327a7077d59d83557a50c10ecb731aa94744e1eb612d02f087.
Native ON/OFF four-state probes passed; enabled images close the K2 visual gap,
disabled control restores it. 841triangles/2523vertices/959deck transforms match;
Modern/Overlay visible, Yechezkel hidden, source collision configurations intact.
Paired NullRHI stair replays both reach0,1,2 in9.99s with0stuck; final grounded
feet-982.6/-982.4cm. Initialfalls95.2/95.4cm match each other, not historic fixed-FPS
26.4cm; do not substitute historical runtime numbers for current measured evidence.
Final gate10/10, corrected Editor/Game built; all20maps and6base containers unchanged.
The new thin face is NoCollision: direct edge walking/barrier acceptance still owed.

The schema repair preserves all70 reflected properties exactly; new references are
nonreflected weak pointers, component explicitly retained by actor OwnedComponents.
Native load after this change confirms compatibility. The GPU probe's bApplyGraphicsToEngine=False
is an EXISTING Config option; otherwise settings overwrite ResX with1920borderless.
Enforced1280x720 High/77% probe measured7.36GiBprivate peak,1.80GiBfreecommit minimum.
Two old2GiBwatchdog stops were NOT OOMs. The game probe now retains1.25GiBfree/8GiBprivate
limits; Entry/full-cook limits stand. See KotelCutClosureV1/runtime-acceptance.json.

15 Sep publication check: closure-study.json includes one final CRLF and its native-tested SHA is pinned by runtime generation. Its exact .gitattributes entry uses -text to preserve raw bytes; compare the indexed blob, not only the Windows working file. Keep diagnostic .log files local under the no-log publication rule; reviewed JSON receipts and native PNG evidence are published explicitly.
15 Sep material patch route: read-only Entry audit dependency-audit-20260915T174543Z-34988 found 10 direct MIC descendants (8 Building, 1 CityWall, 1 CityFacade) among 792 registered MICs, including two ExteriorFixesV1 instances absent from the offline plan. All override flags read false/zero and exposed global switches empty; private static-resource fields remain unknown, so recook inclusion must not rely on guessing those fields false. All20 maps and13 source hashes unchanged, normal exit.

Single-material filesystem cook now PROVEN: ContextPatchStudies/M_Context_CityWall-20260915T174959787Z-5363d21c, four packages/master+three textures, normal exit0, zero errors/warnings, 2.439GiB aggregate private peak, 6.414GiB free minimum. New opt-in Constrained cook profile is SMALLER (5.5GiB aggregate cap/2.5GiB free reserve/8.5GiB initial); original9/6.5/2 profile remains. Two prior preflight refusals launched no engine. CookSinglePackage+CookSkipRequests+SkipZenStore with explicit Package and inline material shader code produced fresh filesystem metadata. Full-map cook remains blocked by its separate16GiB guard; this success does not justify repeating full cooks.

A paired .pak/.utoc/.ucas asset-only overlay was built in an isolated study from this cook's own manifest/scriptobjects. The initial CityWall-only package is ~200KB and uses unchanged base textures; no global.*, registry or shader-library replacement. Native B180340505Z mounted it at Order203 and the inspected fixed-camera wall changed from vertical to horizontal courses. A-return and full-family coverage remain pending at this entry. Keep raw .log files local; reviewed receipts and screenshots may publish explicitly.

15 Sep 18:15 UTC: CityWall asset patch passed complete native A/B/A (runtime180109788Z,180340505Z,180619560Z); exact-tested three-file patch restored in separate Checkpoint-contextpatch01-20260915 copy. Full13-family cook/container also passed but its GPU test preflight refused below8.75GiB; bundle remains unmounted in ContextPatchStudies. Do not report all13materials visually accepted or in the playable copy. ConstrainedGPU test retains7GiBprivate/1.5GiBreserve at960x540High77 plusNoAsyncLoadingThread; firstsuccessfulA came within3.26MiB of cap. No further guard relaxation or full-map cook retries. Read TAKEOVER-STATUS-20260915.md leading section and current-playable-patch.json before resuming. Never publish .log files; keep raw diagnostics local.

Publication verification for material patch: final quick gate6/6 passes (329 Python files,1662 receipts). Preserve ContextCoursingV2 JSON raw bytes with -text, the audit Python with eol=lf, and the executed builder with -text. Native dependency-audit receipt is CRLF and its091504... SHA is required by the 13-family validator; Windows working-copy success alone is insufficient. Compare indexed SHA before pushing.

Material dependency publication: clone lacked only MI_CityFacade_CityStone.uasset among the13 audited sources. Copied this exact15,941-byte pre-existing native asset explicitly (SHA71a34a549439aeaa9566cc59e587f7b18f4833ec41c9294c30d45b1b1e15a884); remaining12cloneasset hashes already matched. Runtime audit validation should be run from the publication clone as well as the active project to catch missing assets.

15 Sep 18:33 UTC: full13 material candidate passed transactional NullRHI mount
(Order203) and actual three-waypoint stair replay; all3 verified CityWall-only
patch files restored and all6 base containers/child/all20 maps unchanged.
See ContextCoursingV2/family-headless-20260915T183251292Z.json. Headless loading
is not GPU shader/material acceptance. Physics-only Constrained profile keeps
6.5GiB initial/2.5GiB child cap/3.5GiB reserve; measured1.12GiB child peak.
GPU8.75GiB initial and full-cook16GiB guards remain unchanged. The walk probe
has no exit command; owned-child shutdown after completed evidence is not a
normal-exit claim. Keep raw .log files local.

15 Sep 18:42 UTC: edge ON/OFF receipts184111081Z/184210020Z are INCONCLUSIVE,
not a retaining-wall failure. WalkProbe switched to MODERN then immediately
teleported/dropped. Actor66 deck collision enabled2.524/2.525s later, after pawn
was already below the slab. SetPrecinctState uses TransitionSeconds=2.5; its
logical state is not physical readiness. StartXY is inside deckinstance106 with
28cm capsule margin. Diagnostic setup must complete its requested state BEFORE
teleport/falling (SetPrecinctStateOver(...,0) available). Do not change ordinary
user transitions or raise startingZ arbitrarily to conceal this test flaw.

15 Sep 18:52 UTC: after diagnostic instant-state fix compiled (11/11 gate,
32/32 math; child6deeb50d...), ON185132894Z/OFF185225086Z both land correctly
on deckinstance106 atfeet-982.4 beforesteering, then cross the cutedge and fall
belowterrain (finalfeet-6413.1/-6407.2,grounded0). This is now a localized
collisiongap, independent of the visualface toggle. All20 mapsunchanged. A
Pawn-only query collision repair for the generated841triangleclosure is being
prepared; do not claim physical repair until native blocking/stairs/state tests.

15 Sep collision compile finding: calling UBodySetupCore::GetCollisionTraceFlag
from the runtime plugin introduces a PhysicsCore link dependency and failed the
Editor target with LNK2019. For a guard checking our explicitly configured
CTF_UseComplexAsSimple value, read the public CollisionTraceFlag field instead
of a helper that also resolves engine defaults. UE5.8 deprecates ChaosTriMeshes
in favor of TriMeshGeometries. Preserve failed compiler logs and rebuild both
targets before runtime acceptance; do not edit source during an owned build.

Edge-wrapper versioning: Test-KotelEdgeRuntime.ps1 now defaults to
-ExpectedCollisionMode PawnBlocking and requires the new physics readback plus
exact dynamic component/actor identity (dynamic meshes legitimately report
mesh='-' in a sweep). To replay pre-repair binaries, pass
-ExpectedCollisionMode VisualOnly explicitly. Never loosen the initial deck
landing or use the walk-probe done counter as successful traversal evidence.

15 Sep19:17UTC: localizedKotel edge collision accepted in separate
Checkpoint-edgecollision01-20260915, child9860531e11415b304c185479b18ab0ac08a34032feba61c565ab19ad00baa435.
ON190805233Z blocks at exactclosurebody (4sweeps,groundedfeet-982.4);
OFF190930828Z restoresfall. Bothheadless4state runs191037452Z/191154185Z
normalexit0, enabledmodes1/0/1/1, hiddenbodyabsent. Bothstairs191326473Z/
191423070Z actual0/1/2,0stuck,finalDeckgrounded. Same841tris/2523verts/
959decktransforms/material;20maps+9archivecontainersunchanged. SameCityWall-only
patch, notfull13. CollisionQueryOnly/Pawn-only,double-sidedphysics only,navoff.
Physicsbody synchronous,TriMeshGeometries actualdata/readback; no reflectedfields.
Finalbuildretry10/10 bothtargets,no warnings;priorunchangedmath32/32.
Read collision-acceptance.json and leadingTAKEOVER status. Localedge acceptance
is not wholeperimeter/GPU/publicrelease. Oldplayablecopies andfailures preserved.

## OldCityFoundationV2 — floating city bases (Claude, 15 Sep 2026)

Flat building bases float wherever terrain drops below them along an edge. Two generators cause it:
`create_oldcity_facades.generate_infill` (centre sample; INFILL_BASE_RULE now documents it and offers
ground_min_v2 for any NEW generation) and buildJerusalem's OSM min-of-vertices rule (valley edges).
Measure against the GAME terrain mesh (jerusalem-meshes.json mesh 0 heights + its per-cell diagonals),
not a centre sample or AABB: `Scripts/oldcity_foundations_v2.py census|build|selftest`. Foundations are
separate actors (one mesh per precinct class x 500 m tile) because BuildingIdentityLabel only resolves
the two audited folders: swapping a V1 infill mesh to a new namespace would silently drop it from the
269-owner hide list and the LegacyRoofRuntimeV1 owner guard. Use CityDetailZone_Precinct/Kept tags, and
recompute the class per map (Main50 hides one more infill cell, N004_N004). Footprints touching Kotel deck
rectangles are excluded (osm06965). Ring tracing must snap endpoints within 0.05 cm and merge sub-0.01 cm
terrain breakpoints, or T-junctions and edge-end slivers open gaps.

## KotelViewsV1 — the two cp26 Kotel frame defects (Claude, 16 Sep 2026)

- **A GENERATED header breaks every agent's cook.** `KotelClosureRuntimeData.h` is written by
  `Scripts/generate_kotel_closure_runtime.py`. C++ that references new fields compiles only after
  the header is regenerated, and until then EVERY cook with `-build` fails (it cost the Old City
  agent a cook: `Data::MaterialIds` undeclared). Regenerate the header in the same step as the
  code change, rebuild BOTH targets, and only then say the tree is clean. Renaming a header
  constant (`ClosureSha256` -> `WallSha256`) breaks call sites the compiler finds one at a time.
- **K1's white stepped soffit was never a material bug.** It is `RELEASE_MountAccess_Deck/_Guards/_Portal`
  (`create_kotel_opening.py`): 45 cm slab segments from X -18400 to -12500 at Y 19822..20122, so
  from below they read as a stair underside. The material assigns fine and has `bUsedWithNanite`;
  it is the unaccepted near-white `M_JerusalemStoneV2_*Review` pilot (no textures, no joints), and
  the actors carry NO state tag, so they stood in all three states. The cooked default material
  draws a grid, so flat white is never a cook fallback - check the pilot materials first.
  Removed from both maps with `Scripts/release_remove_mount_access.py` (assets retained).
- **An acceptance bar must be one the accepted answer can pass.** The V2 wall's coverage test first
  demanded zero "void rays" (sightlines that leave the plaza UNDER the one-sided hillside surface).
  The accepted V1 closure scores 268, because it excludes internal level edges and the platform
  hole by design. The honest bar is no regression against V1; V2 now scores 229, i.e. it occludes
  more. Comparing wall-to-wall DISTANCE was also the wrong test: V2 stands up to 60 cm inside the
  sawtooth, so grazing rays legitimately run alongside it.
- **A wall built inside the boundary needs the old curtain as a liner.** The dressed face is a
  one-sided simplification of the 250 cm deck sawtooth, so a sightline nearly parallel to it can
  slip through the wedge between chord and boundary. Keeping all 841 V1 triangles behind the face
  makes occlusion >= V1 by construction; `validate()` and the unit tests now refuse data without it.
- **GeometryScript from Python returns out-params as tuples.** `CopyMeshFromStaticMesh` (not
  `copy_static_mesh_to_dynamic_mesh`) returns `(mesh, outcome)`; `ConvertIndexArrayToMeshSelection`
  returns `(mesh, selection)` - passing that tuple on fails to nativize as
  `FGeometryScriptMeshSelection`; `GetTrianglePositions` returns `(bIsValid, v1, v2, v3)` with the
  FLAG FIRST, so slicing `[:3]` silently averages a bool with two vertices.
- **The stray paving strip above the Kotel wall is OSM way 26492734** ("Western Wall Plaza",
  highway=pedestrian) exported as a ~145 cm road-centreline ribbon draped on the DEM across four
  `SM_Jerusalem_StonePaths_*` assets. PlazaV1 already paves that footprint, so the ribbon is a
  duplicate that overhangs the cut and pokes through the deck; its Z-notch is the way's own vertex
  jog. Street actors carry no state tag, so it survives every precinct state.
- **Do not run a build while another agent's map job holds the editor**, and do not run the map
  runner while UBT runs: `Run-KotelViewsEngine.ps1` treats a `dotnet` UBT/UAT process as a busy
  slot and now WAITS instead of aborting, and it resumes with `-StartAtStep` so applied steps are
  never repeated.

Cook trap, same day: `Checkpoint-Build.ps1` passes `-build`, so a cook compiles the Game target and dies
with UAT exit 6 on ANY agent's uncompiled C++ in the shared tree — here `KotelClosureRuntime.cpp`
referencing `Data::MaterialIds`/`MaterialCount` that `KotelClosureRuntimeData.h` does not declare. Do not
edit the other agent's source to get your cook through. If your own work is content-only, cook with
`-UseExistingBinaries` (no build step) and state in the receipt and review that the archive carries the
last verified runtime and none of the pending C++. Maps stay byte-identical through a failed cook.

## For a behaviour/AI pass on the people (16 Sep 2026)

See section 8 of `HANDOFF-20260916-FOR-CODEX.md`. In short, and all receipt-backed: there is NO navmesh
in either map and the plaza deck is built at BeginPlay (144 proxy boxes 1 cm under Z 0), so an editor-baked
navmesh will not see it; the ~1,600 distant crowd are VAT statues with no skeleton to attach a controller
to, while only the six ResidentV4 bodies and the Kohen Gadol are skeletal; the transit/crowd bridge has a
documented gap (no stop inside a crowd zone, coordinator cannot render, `IMikdashCrowdPartyHost`); walk
speed has six per-variant overrides stored in the MAP that beat the 120 cm/s C++ default; and
`resident-routes-v2-verify` has only ever run on the legacy map. Use `-MikdashWalkProbe` for reachability
and a rendered movie for whether they look alive - a receipt cannot show stilting.

## Read-only skin function evidence — 18 September 2026

Three asset-only commandlets exited zero, peaking below 1.6 GB private memory.
Epic MF_skin_cavity separates Concavity, Convexity and Micro paths modifying base
color, specular and roughness. The final audit uses the installed engine API
get_input_node_output_name_for_material_expression: G feeds Convexity, B feeds
Micro, and R feeds the concavity switch (R on false/default; 1-R on true).
Named-reroute declaration references are not exposed by get_editor_property, so
retain the graph receipt rather than inventing missing links. This is not AO.
No scene load, native asset mutation or visual acceptance occurred. Evidence is
KohenSkinV2/cavity-function-20260918T194328Z.json and audit-run receipts.

## UE 5.8 material pin names — 18 September 2026

Native skin-study creation caught two failed connections because it checks every
MaterialEditingLibrary return value. VertexColor's first output is unnamed (use
an explicit RGB mask); Power's Exponent input is shortened to Exp by
MaterialGraphNode::GetShortenPinName. Existing builders using Exponent without
checking success need native audits before attributing color to texture content.
Do not assume their published 2.2 parameter is connected. Initial two skin attempts
saved only fresh textures; no approved mesh/material binding changed. Retain their
failure receipts. The third study uses /Game/Characters/KohenSkinV2Study03.

## Kohen skin native study — 18 September 2026

release_kohen_skin_v2.py creates only a fresh asset namespace and refuses overwrite.
Study03 contains original Walter albedo/normal/cavity textures and a skin master:
existing vertex-color base decode, original normal, R/G/B roughness detail,
R specular attenuation and subsurface shading. Albedo is retained as a reference;
base color stays vertex-driven so a reviewed neck color edit can ride along.
All connections are checked. Fresh-process readback verifies texture settings,
material properties, exponent wiring and cavity blend channels. Values remain
study defaults requiring rendered tuning; no native head binding or scene edit.
NullRHI checks do not prove GPU shader compilation or visual quality. Next: isolate
head/beard, review native rendered A/B closeups and motion before adopting it.

## Kohen lower-robe clearance study — 18 September 2026

Full baseline walk exposed 0.388 cm inner/outer intersection near rest Z36 at
71/240 seconds, toward the rear. Single-pose diagnostic reproduces 0.3878326 cm.
Global outer offset 2.2/2.8/3.4 cm yields 0.38783/0.16574/0 cm. To avoid expanding
the upper garment, a candidate adds 1.2 cm only below Z60 and tapers smoothly to
zero at Z85. Worst-pose result is zero. Earlier tapers from Z40 to65 still intersect
and are retained as failed studies. MEIL_LOWER_EASE_CM defaults to 0: production
geometry is unchanged. study_kohen_meil_clearance.py --full --lower-ease 1.2 runs
all three clips with the same unchanged measurement rules; full result pending.
No candidate export/native adoption/render acceptance yet. Evidence folder:
SourceAssets/characters-review/KohenMeilEaseV2. Keep torso/ephod/bells visual review
in the adoption gate, not just the two measured garment surfaces.

## Isolated head GPU attempt — 18 September 2026

capture_kohen_skin_study.py prepares transient before/after head material captures
in /Engine/Maps/Entry; no world/material save is requested. Attempts produced NO
images. First launcher stopped at a PowerShell Math.Max Int32 overflow above 2 GiB;
fix both arguments to Int64. Second reached 5,025,628,160 bytes private memory in
editor startup and the existing 4 GiB study cap stopped its owned process before
capture setup completed. Do not raise guards/relabel this as visual acceptance.
Receipts gpu-head-run-20260918T200308Z and 200419Z retained in KohenSkinV2.
run_kohen_skin_study.ps1 preserves 6 GiB start/4 GiB private/2 GiB reserve/300 s deadline
and checks the native slot; full-scene 9 GiB guard unchanged. Capture helper remains
unproven until sufficient headroom permits native frames. Full lower-robe candidate
measurement continues separately in the offline Python process.

Candidate run update: walk portion reports zero leg/robe intersection but about 0.41 cm inner/outer intersection at another pose. Candidate fails full-walk clearance and will not be adopted. Tending and idle continue in the same run; exact worst-pose details await its final receipt.

## Follow-up robe deformation diagnostics — 18 September 2026

Ten walk poses compared hem skinning bands 6/8/10 cm; none cleared them all and
larger bands worsened some poses. Keep production band 6. Lower ease 3 cm still
clips in the seven stride poses; lower ease 5 cm clears all seven. This candidate
has full ease below Z60, smooth taper to zero at Z85 and unchanged torso/weights.
A separate full 240 Hz walk is now running for ease 5; no adoption or visual acceptance.
The rejected ease 1.2 all-clip run continues for its final worst-pose receipt.
The diagnostic helper supports pose/band lists and explicit full clip subsets;
all globals restore in finally. Study files are under KohenMeilEaseV2. Seven
zero poses do not establish full-cycle clearance or acceptable silhouette, and
all production geometry remains at default ease 0.

## Layered robe source studies — 18 September 2026

build_kohen_meil_study.py writes a FRESH GLB from the hash-pinned approved Walter
source. It matches generated robe/hem vertices by material, float32 position,
normal, joints and weights; only position/normal bytes and their bounds change.
Two cap-normal components around 1e-17 differ in the source; matching canonicalizes
only components below 1e-12 to zero, preserving exact nonzero float32 components.
Without --follow-ephod, ease 5 hides the lower ephod in an offline rest preview:
REJECT that unlayered study. --follow-ephod carries the ephod and gold edges with
the robe taper; layered preview restores the visible outer layer. Its 18,074 matched
vertices include 12,903 changed vertices. Head, rig, weights, colors, UVs, indices
and all unrelated geometry are preserved. Full-motion ephod/robe clearance still
owed; the ongoing core robe walk test does not cover it. Native adoption/rendering
remain pending. See KohenMeilEaseV2/layered-study-offline-review.json and paired PNGs.

## Full-walk rejection of wider robe — 18 September 2026

Ease 5 fails the full 288-sample, 240 Hz walk: zero leg/robe intersection, but
0.4022897 cm inner/outer intersection at t=1.1666667 s, rest Z36. A separate
single-pose replay reproduces it at vertices 4258/4260/4262. Seven previously
clear poses were insufficient. Do not adopt either ease-5 source variant.
Posed offline previews now use the shipped animation and verify joint order;
receipts pin mesh, animation and image hashes. Rear views at 0.2958333 and
1.1666667 s show a pronounced slanted/bent lower hem. Inspect deformation and
layering before further widening; these images are not native visual acceptance.
Production ease remains zero. Evidence: KohenMeilEaseV2/ease5-walk-full.json,
ease5-late-worst-pose.json and silhouette-layered-candidate-walk-* files.

## Signed-distance winding correction — 18 September 2026

nearest_signed previously used the outward-corrected face normal for triangle
containment. With sign -1 this rejects an interior projection and measures an
edge instead: a point 1 cm above triangle (0,0,0)/(10,0,0)/(0,10,0) at XY(2,2)
was reported sqrt(5) cm away. Containment now uses the vertex-winding normal;
the returned distance still uses the outward sign. Analytical tests cover both
normal signs, reversed winding, both sides and an exterior edge projection.
All 12,672 Kohen outer-wall faces have sign +1, so this does not erase the
reported robe defect. Existing long-running offline studies loaded the earlier
measurement module; preserve that provenance when collecting their receipts.

Full ease-1.2 measurement completed: walk 288 frames at240Hz fails with 0.411 cm
inner/outer penetration at t0.2708, restZ36; leg/robe zero. Tend601 at60Hz and
idle97 at30Hz both zero. This run used the pre-winding-fix measurement module.
Broader hem bands14/20/30 each fail at least one of eight selected outer-garment
poses. A sparse full-body walk with band20/ease1.2 fails by3.243 cm at the right
shin, t0.6857; outer penetration0.29 cm. Do not trade body clearance for layer
clearance. Receipts retained in KohenMeilEaseV2; production remains unchanged.

## Bound Kohen decode graph confirmed — 18 September 2026

Read-only native audit bound-materials-20260918T204907Z verifies the approved
KG_MHHead slot inherits M_KohenGadol_Garment_V1. Its VCDecodeExponent scalar is
2.2 but Power Exp is disconnected, so const_exponent 2.0 is effective. All bound
slots share that master. The audit preserves mesh/material and map hashes.
release_kohen_gadol_v1.py now uses Exp and checks the connection result for future
builds. This source correction does NOT repair the already-saved master or prove
appearance; a native repair and rendered acceptance are still required.

Isolated preview attempts omit MetaHumanCharacter/MetaHumanSDK authoring plugins
only on the command line, preserve HairStrands and the project configuration, and
limit static/skinned/texture compilation concurrency to one. The 6 GiB start,
4 GiB private and 2 GiB reserve guards remain unchanged. Viewport attempts reached
capture setup but exceeded private memory before images. Render-target commandlet
mode avoids editor viewport overhead; treat its outputs as isolated material
review, not full-scene acceptance. PowerShell dynamic argument concatenations must
be parenthesized inside arrays: otherwise commas can become part of a concatenated
array expression, breaking filtering and introducing spaces into the script path.

## First bounded native skin frames — 18 September 2026

Render-target commandlet succeeded below the existing 4 GiB guard after shaders
compiled. Use run_kohen_skin_study.ps1 -RenderTarget. SceneCapture2D's native getter
is not exposed to Python; use get_component_by_class(SceneCaptureComponent2D).
The final front three-quarter view is camera(70,150,162), yaw-115.0169; negative Y
is the rear of this imported asset. Final images: render-target-20260918T210140Z.
Baseline is dark/red; Study03 adds visible facial detail but is too orange in this
isolated lighting. A transient Study03 instance with VCDecodeExponent1 looks more
natural. Do NOT blindly repair the saved master to2.2: first calibrate actual
imported vertex colors against known swatches. The pin-name correction only makes
the future builder honor its parameter; it is not appearance acceptance.
The pale lower-jaw/neck region remains with all head materials and matches the
beard-shell coverage diagnosed offline. Review beard isolation next. Turban bands,
dark background/shadows and still captures are not sufficient to approve garments
or temporal rendering. No mesh/material/map was saved or rebound in production.
The full-scene, motion and final lighting gates remain open. Protected bytes can
be checked against the bound-material audit's33-file snapshot after native exit.

Color-path follow-up: installed UE5.8 GLTFMeshFactory.cpp lines720-723 and784-787
explicitly apply SRGBToLinear to counter the engine's later conversion, with the
stated goal that final vertex colors remain linear. InterchangeSkeletalMeshFactory.cpp
lines672-687 applies ToFColor(true) to undo that extra linearization. This is
consistent with the exponent1 native study and contradicts the old blanket claim
that this import's shader must decode raw sRGB bytes. Verify with a known-color
native swatch before repairing/adopting the saved master and all affected slots.

## Calibrated and repaired Kohen linear colors — 18 September 2026

Native skeletal GLB swatch calibration color-calibration-20260918T210959Z returns
RGB(0.25,0.49609375,0.74609375) for source(0.25,0.5,0.75): maximum error0.00390625,
versus0.28710 against sRGB encoding. No native calibration assets were saved.
Imported vertex colors are already linear; exponent1 is required, not2.2.
repair_kohen_linear_colors.py backed up twelve assets, connected Exp and set the
Kohen garment master, Study03 master and ten BOUND instances to1. Native apply
211431Z and fresh-process verify211538Z passed. Only those twelve material files
changed; mesh, bindings, maps and other protected assets remain unchanged. The
unused iris instance was preserved. Future builders now use1.0. The historical
head-bake comment claiming shader sRGB decode is superseded by this calibration.

Native render-target-20260918T211648Z confirms improved blue cloth and skin color.
Study03 still is NOT bound to the production head; normal/cavity adoption and
full-scene/motion review remain open. Isolating KG_Hair section7 in native frame
render-target-20260918T210747Z-skin-linear-no-beard.png removes the pale jaw/neck
strip, confirming beard-shell coverage as its cause. Keep the grey beard; correct
its lower coverage rather than changing the skin underneath. No beard edit yet.
The Windows packaged build is unchanged until a verified recook.

## Beard neck coverage study — 18 September 2026

Study01 cut below Z152 cm but nearest-head-vertex snapping collapsed three normals
and left visible neck coverage. It is rejected; retain its source/native evidence.
Study02 cuts below Z154 and blends to the unchanged beard at Z156, projecting onto
local skin tangent planes to preserve rim spacing and submerge it by0.06 cm. The
read-back verifier proves original binary/non-beard primitives/rig unchanged,
retained beard colors/UVs/weights identical and all normals nondegenerate.
Native render-target-20260918T213810Z front and three-quarter images show a clear
skin-colored lower neck while preserving the grey chin/cheek beard. Both bounded
native jobs exited0, maps unchanged, no imported study assets saved.
This is an isolated visual improvement, NOT production adoption: a thick side-jaw
patch and the silhouette need scene lighting/motion review. Fresh import also shows
other shading differences despite preserved source geometry; control the importer
and shared production skeleton before adoption. Study03 skin remains unbound.
Evidence and rejection details: KohenSkinV2/beard-neck-review-20260918.json.

Restart on18September cleared the memory blocker: approximately25GiB free virtual
memory measured afterward. Full-scene9GiB and isolated6/4/2GiB guards are unchanged.

## Post-restart packaged environment inspection — 18 September 2026

C1 northwest cut-cell camera (-50000,-45000,6000; pitch-15,yaw45) now runs on the
accepted S5-02 package with unchanged9GiB start/8GiB child guards. Four states and
normal exit pass; peak private7.18GiB, minimum free commit17.30GiB, maps unchanged.
All four images were viewed: city roofs/buildings remain present, no large cut-cell
void apparent. This distant view does NOT identify the reported floating remnants
or prove ground contact. Continue street/boundary cameras and actor isolation.
Evidence: KotelCutClosureV1/runtime-20260918T214141915Z.json and
finish-c1-review-20260918.json. This existing package excludes recent character
changes. C: now has approximately86GiB free; no archive deletion was performed here.

The same C1 runtime log confirms M_StreetTrees_Bark has an invalid cooked shader
map on PCD3D_SM6 and uses the default material. This remains an actual packaged
defect, not just an old warning. Exact lines/log hash are in finish-c1-review.

## Street-tree bark sampler repair — 18 September 2026

Native audit reproduces the packaged defect: M_StreetTrees_Bark's normal sampler
uses EngineResources/DefaultTexture (a COLOR texture), inherited by all six bark
instances. The compiler explicitly reports Normal should be Color for that texture.
The source importer never assigned BarkNormal despite importing/compressing each
species normal map. Fix both master defaults and six instance normal overrides.
Backed-up apply215051Z changed exactly seven material assets; all tree geometry,
textures and20maps unchanged. Fresh-process/GPU cook/package checks follow; this
source repair does not yet update the playable archive.

UE5.8 MaterialEditingLibrary.cpp:1507 SetMaterialInstanceTextureParameterValue
always returns its initial false even after applying. Do not treat that return as
a failure: verify with GetMaterialInstanceTextureParameterValue. The first repair
attempt stopped on that false with no saved changes; its failure receipt remains.

Fresh-process verify215134Z passes all six species bindings with no asset changes
and no shader errors. Isolated Windows cook215159Z passes all seven requested
materials with zero errors, one shader worker, no map requests/outputs, and unchanged
Content metadata/maps/material hashes. Packaged rendering remains owed; see
StreetTreesV1/bark-cook-20260918T215159Z.json. All memory guards remain unchanged.

## Crowd benchmark capture safeguards — 18 September 2026

The packaged CSV harness now preserves existing captures, requires a fresh output
label, tracks its owned child only, launches hidden, checks9GiB free commit and
enforces8GiB private/1.25GiB reserve during recording. It records executable/CSV
hashes and fails on forced termination, premature exit or ambiguous/missing CSV.
Source preparation only; actual0/2500/5000/10000 performance is still owed.
## Packaged bark repair and Kotel preservation — 18 September 2026

Checkpoint-finish-bark01-20260918T215607Z cooked successfully (9,120 packages).
Two packaged GPU probes exit normally and preserve all source maps. All eight
images were reviewed: bark now renders textured wood; Kotel paving/retaining
closure remain across Modern, Yechezkel, Overlay and Modern-again. Evidence:
StreetTreesV1/finish-bark01-review.json and finish-bark01-archive.json.
This accepts the bark shader repair and plaza preservation only. Tree branch
junctions/unsupported-looking foliage still need inspection. Kotel phase1 image
runtime-20260918T220932917Z-phase1.png exposes an apparently detached small block
above the right wall (approximately x2054,y398 in the 2560x1440 image), visible in
Yechezkel and absent in the other reviewed states. Identify its owner and phase
handling before removal. This is a concrete floating-remnant lead, not a diagnosis.
New build includes the linear material fix; beard Study02 remains unadopted.
Crowd harness pins High scalability2, screen percentage77 and resolution while
turning saved graphics overrides off; actual crowd matrix remains owed.
## Crowd capture finalization — 18 September 2026

The first guarded packaged baseline (finish-bark01-a, crowd0) required forced
owned-process termination because CloseMainWindow did not close the hidden game.
Its receipt remains failed_capture; its partial CSV must not support performance
claims. Use Unreal's source-confirmed -ExitAfterCsvProfiling with csv.ForceExit0;
require one CSV finalization and normal exit, retaining the existing memory guards.
Capture a bounded frame count then analyze a fixed45-second settle/60-second window.
The analyzer now rejects short/malformed/nonfinite recordings and insufficient
complete-frame coverage. Tests cover boundary-crossing stalls and later slow frames.
Finalization success and actual crowd counts/visible placement are separate gates.
Crowd baseline b finalized its CSV through the engine and logged normal teardown,
but the child returned777003 (ECrashExitCodes::CrashReporterCrashed). Keep this run
failed; do not use its analyzed frame rates as accepted evidence. Both failed
receipts are published; large CSV/logs stay local. Exact shutdown cause remains
unresolved. Latest source quick gates6/6 and analyzer regression tests5/5 pass in
both trees. Next: resolve/reproduce shutdown, then complete the crowd matrix with
actual count/placement proof; continue the identified Yechezkel floating-block audit.
## Crowd shutdown reproduction and count proof — 18 September 2026

Unchanged baseline c reproduces b: CSV finalizes and game logs full shutdown, but
child returns777003. Both are failed, not accepted benchmarks. The harness now
uses the engine's frame-scheduled csvExecCmds to read SeededAgents, RefusedSeeds,
GroundTraceMisses, ActivePoseCount and bUseVertexAnimation, plus a viewport PNG.
It requires exactly one live field with the requested seeded count and a saved
photo. These late inspections must lie beyond the analyzed timing window.
The optional CsvOnGameThread switch uses the engine's csvNoProcessingThread flag
for a controlled worker-thread shutdown experiment; timing overhead changes and
must be declared if used. It does not disable crashes or relax nonzero-exit checks.
## Native crowd pilot and floating-roof cause — 18 September 2026

Two worker-thread CSV runs ended777003 after finalization; game-thread pilots for
0 and2500 requested both exited0. The empty baseline passed native capture and
30/30 analysis. The2500request seeded2376 and refused124, with zero ground misses,
sixpose meshes and vertex animation enabled. Keep its receipt failed: this proves
visible thousands but not exact2500 acceptance. PNGs show dense courtyard figures;
angular silhouettes/clothing artifacts remain visible. Do not equate requested
counts with actual placement or compare different profiler modes. Full45/60 matrix
and placement-refusal diagnosis remain owed. See crowd-vat/finish-bark01-d-review.json.

Kotel logline960 proves LegacyRoofRuntimeV1 refuses the current scene's hide policy:
it still demands269 buildings/add1b55da3535d53, while the verified Haram map has
48/ef8a333d75a7daad. Legacy pair2096 belongs to selected owner
SM_JerusalemBuildings_Grid_N002_P001. Its tank/panel origins project within6pixels
of the detached block in phase1. Current owner-based repartition is118 hidden pairs,
5889kept and18hidden roof owners, preserving all6007 original pairs. Retarget the
exact table/policy and prove modern restoration plus same-camera native removal;
do not loosen the guard or hide all old-square roof decorations. Diagnosis:
LegacyRoofZonesV1/haram-remnant-diagnosis-20260918.json. Native isolation still owed.
## Haram roof visibility repair in source — 18 September 2026

The runtime table now derives membership from the hash-pinned Haram hide source,
matching native48-label fingerprint ef8a333d75a7daad. The generator first validates
the original pinned6007-pair ownership/transform plan, then repartitions118hidden
pairs and5889kept pairs across18hidden owners. All6007 transform rows remain
byte-identical;1145old-square pairs now remain visible with their buildings.
Runtime guards retain exact identity/fingerprint, source transforms/materials and
component settings; diagnostic counts derive from generated constants. Four tests
cover full geometry/ownership preservation, membership, surrounding-city restoration
and rejection of wrong policy. Compile, native10-state and same-camera packaged
visual acceptance remain owed. The old roof probe wrapper now enforces9/8/1.25GiB
start/private/reserve guards and describes the specified archive accurately.
Fresh active-tree verification compiled bothEditor andGame targets successfully;
verify --quick --build reports10/10. Both trees also pass generator --check,
four roof tests and quick6/6. All6007 generated translation rows match priorHEAD
exactly. Native package/state/image acceptance remains pending; do not equate
source compilation with removal of the visible remnant.
## Haram roof repair accepted in packaged runtime — 18 September 2026

Source 03f2acd9 compiled both targets and passed checks. Fresh isolated archive
Checkpoint-haram-roofs01-20260918T225143Z uses unchanged bark01 cooked assets plus
new child 3fe6bcb177b88eaeaf0ef143cdd3d3c7f2cf7d3fe2d7fd68cd58939ff30e265c.
This is a verified runtime update, not a recook. Ten native states pass, including
transitions/restore/rebuild: 12,014 original instances, 11,778 kept, zero position error.
Both native and four-state GPU probes exit 0; all 20 maps unchanged. All four same-camera
Kotel images were viewed: the floating tank/panel by the right wall is gone in
Yechezkel, paving and retaining closure remain, and Modern restores. See
LegacyRoofZonesV1/haram-roof-acceptance-20260918.json for bounded acceptance.
Other scene defects, exact crowd counts, placement and appearance, characters, final
full release validation and independent online walkthrough remain on FINISH-LINE.

## Crowd placement diagnosis — 18 September 2026

The 2500-person pilot rendered 2376, with 124 refused and zero ground trace misses.
SeedSocialZone now logs per-zone requested/seeded/refused totals and the first
failing gate of every placement attempt (point, segment, neighbor spacing,
formation, protected link, ground residual, static obstacle, or insertion).
Attempt counts must sum to accepted groups plus rejected attempts; they are not
counts of refused people. Random samples, 48-attempt budget, group formation and
all ground/wall/spacing thresholds remain unchanged. Native diagnosis is pending;
do not treat this instrumentation as a capacity fix or accepted crowd matrix.

## Crowd shortfall localized natively — 18 September 2026

Diagnostic source 1e8fc09d compiles both targets (10/10 active, 6/6 clone).
Fresh isolated audit package reproduces 2376/2500, exit 0. The failed capture is
retained. KotelPlazaStrip refuses all 68; KotelApproachCorridor refuses 56 of 73;
the other four zones fill completely. All plaza attempts reaching the ground gate
fail it. Each zone conserves attempt and requested-person totals. Existing old
terrain-plane assumptions require comparison against actual paving contacts;
obtain contact coordinates, heights and support identity before changing policy.
See crowd-vat/crowd-audit01-diagnosis.json. No count fix or benchmark acceptance yet.

CrowdGroundAudit is an opt-in diagnostic launch flag. It records the first 32
existing ground trace results per zone per process, including XY, expected/hit Z,
normal and support actor/component. It adds no traces and changes no placement
thresholds. The capture harness records GroundAudit explicitly; diagnostic runs
are not clean performance baselines. Actual paving/contact diagnosis remains open.

Ground audit finds all sampled Kotel-strip traces hit StaticMeshActor_24, the
Kotel terrain cut, at -1284.594 cm: 50 cm below the authored lower paving top.
Crowd seeding precedes enclosure preparation in the log. Do not adopt that buried
terrain as the crowd floor. DeferredSpawnAudit starts with zero people and calls
BuildCrowd at frame 120 via the engine KE command, requiring one successful class
instance call; this isolates post-initialization support using the same executable.
The flag requires GroundAudit and explicit count and is not performance acceptance.

## Crowd ground/startup cause proven — 18 September 2026

Both native ground audits exit 0 and correctly fail exact crowd counts. Immediate
seeding: 2376; deferred frame120: 2375 (68 plaza, 52 approach, 5 street refused).
All32 plaza samples switch from cut terrain -1284.594 to Actor_66 paving
-1234.552579 after initialization. The old expected slope still rejects them.
Startup approach32samples match pinned FutureMountCut source terrain triangles
within 0.003348 cm; use this precise surface, not another approximate plane.
Next correction needs initialized collision plus sourced deck/terrain references;
retain spacing/wall/ground guards and verify moving feet as well as spawn counts.
Evidence: crowd-ground01-{startup,deferred,package}.json. Diagnostic flags and
CSV game-thread mode mean these runs are not accepted performance baselines.

## Crowd ground correction in source — 18 September 2026

BeginPlay schedules crowd creation for the next world tick, after enclosure actors
install their state's collision. Manual BuildCrowd cancels pending startup; EndPlay
clears it. This is initialization ordering, not a timed spawn-count workaround.
The Candidate48 shipping map (including its PIE prefix) now uses generated pinned
Kotel surfaces: actual overlapping deck rectangles and 16 approach terrain triangles.
No fitted slopes, buried terrain floor, increased attempts, or relaxed thresholds.
Missing surface coverage returns non-finite and refuses the seed/move; invalid
hidden instance transforms remain finite. Movement uses the same surface difference
as seeding. Native population, feet-in-motion and state-transition acceptance remain
pending. Other maps retain their existing ground models.
Review correction: ClearCrowd itself cancels deferred startup, so a caller can
clear before the next tick without later repopulation. Non-social movement also
restores its previous finite position/height when surface coverage is missing;
NaN refusal must never reach a rendered instance, including when VAT/groups are off.

## Kotel crowd floor correction proven in package — 18 September 2026

Source 6d2c3698 passes full active11/11 including33/33math and both targets;
clone quick6/6 and both generated-header checks pass. Isolated floor01 package
uses unchanged cooked files and new child. Native capture exits0, seeds2485/2500:
plaza68/68, approach63/73, street47/52; other zones complete. Both Kotel zones now
have zero ground rejections. The same-camera PNG shows visitors on plaza paving;
root viewed it. Keep capture failed for missing15. See crowd-floor01-review.json.
This proves the ground/startup correction, not exact population, all-frame moving
feet, transition stability, appearance or benchmark acceptance. Approach bounding-box
sampling wastes many attempts outside its narrow rotated zone; investigate candidate
sampling while retaining48attempts and all spacing/obstacle protections. Street ground
reference/spacing still needs separate review. Full finish-line scope stays open.

## Direct sampling of crowd-zone interiors — 18 September 2026

SeedPointInZone now recognizes nondegenerate parallelograms and draws uniformly
inside their inset parallelogram, rather than the larger axis-aligned bounding box.
Insets use perpendicular distances, including skewed quads. Every candidate still
passes the original polygon margin and protected-area checks; concave/arbitrary
polygons retain rejection sampling. The 48 group-attempt limit, member spacing,
ground tolerances and static sweeps are unchanged. Both windings, a real rotated
approach, deterministic broad coverage, empty insets, protected regions, nonfinite
margins and concave fallback are covered. Native count/placement acceptance pending;
this changes deterministic seed positions and must be measured on a fresh package.

## Crowd sampler native acceptance at 2500 — 18 September 2026

Source 6fd54c0f passes active11/11, math33/33 and Editor/Game; clone quick6/6.
Fresh sampler01 package retains all six cooked file hashes. Native late-frame
readback confirms2500/2500, zero refused across all six zones; child exits0.
Plaza68/68, approach73/73 and street52/52 now complete with unchanged48attempts
and safety thresholds. Both Kotel zones have zero ground rejections. Root viewed
the late-frame image: visitors stand on restored plaza paving. See
SourceAssets/perf-review/crowd-vat/crowd-sampler01-review.json for raw-log-derived
counts and192ground contacts. Diagnostic30/30 CSV validates capture integrity,
not the final performance matrix. Larger populations, clean45/60 benchmarks,
all-frame feet/movement and state-transition acceptance remain pending.

## Crowd formation placement order — 18 September 2026

The sampler01 native5000 run initially seeds4818: west terrace911/1030,
plaza114/135, street78/104, approach130/146; east1391 and deck2194 complete.
Spacing dominates the small-zone failures; west also has protected-area and ground
refusals. New source plans the exact same cohorts and global person identities
first, then seeds larger formations before smaller groups and individuals. Stable
ties preserve reproducibility. Agents still occupy their original index ranges;
appearance, hash identity, requested zone allocations and group membership are
unchanged. All48attempts,80cm minimum separation, ground and obstacle gates remain.
Tests compare reordered membership against the original planner through60000people.
This is pending verification/native evidence, not claimed5000/10000 acceptance.

Sampler01 clean5000 capture is now terminal: childexit0, wrapper correctlyfails
for4818/5000. Raw six-zone counts and182refusals match late-frame readback.
45/60 analysis covers2576frames (median21.494ms,p9537.504ms), but is evidence for
4818actual people only. Root viewed final PNG. See crowd-sampler01-5000-review.json
and matching receipt/timing; larger-first source remains unaccepted until native.

West-terrace diagnostic follow-up: sampler01 ground sample1 hits
StaticMeshActor_9208 at792.000610cm against expected408cm. Existing Candidate48
birds receipt candidate-metric-birds-20260909T075232116207Z.json identifies that
actor as Priestly room floor, architecture_SM_1450_floor_Priestly_room_floor,
bounds[-7400,2736,772.8]..[-6536,4944,792.0]. This is elevated interior geometry,
not evidence to raise the ordinary visitor ground plane or relax its55cm check.
Other west samples return the ordinary paving at408cm. Keep height refusal.

## Largest-first crowd placement native result — 18 September 2026

Source8ec430e0 passes active11/11,33/33math,Editor/Game and clonequick6/6.
Fresh packing01 child with unchanged cooked hashes improves5000-request placement
from4818 to4970; child exits0, wrapper correctlyfails for30missing. Plaza135/135
complete; west1024/1030,street86/104,approach140/146 remain incomplete. Root viewed
late-frame PNG. The45/60 sample has2939frames,median19.052ms,p9530.4ms for4970actual
people; cross-run timing is not an isolated optimization claim. See
crowd-packing01-5000-review.json. Same-binary10000 capture is next; movement,
state transitions, fullcount benchmark matrix and final appearance remain open.

## Bounded crowd search-budget diagnostic — 18 September 2026

Packing01 initial10000 counters show9320seeded and680refused. Next source adds
optional -CrowdSeedAttempts=N for social placement, clamped1..1024, logged perzone
as maxAttempts. Default remains48. The capture wrapper accepts GroupSeedAttempts
0..1024, where0 omits the override, and records it in the receipt. This permits
measuring finite-search exhaustion versus physical zone capacity on one binary.
No spacing, support, protected-area, group-membership or obstacle check is relaxed.
Pending verification; no larger-budget result or production-default adoption yet.

Packing01 10000-request capture is terminal:9320placed,680refused,childexit0,
wrapper correctlyfails population. Refusals east26/west418/deck3/plaza56/street85/
approach92. Root viewed final PNG. Clean45/60 analysis retains2534frames covering
59.94s,median21.797ms,p9537.303ms for9320actual people only. See
crowd-packing01-10000-review.json. This does not close the10000target or movement/
state/appearance acceptance. Source diagnostic budget experiment is still pending.
Future runtime-only test archives may NTFS-hardlink the six unchanged immutable
Paks files to their base to conserve disk; child binaries remain separate copies.
Never recook into or modify any checkpoint's linked Paks files; verify their hashes.

Performance scope reminder: PERFORMANCE-BUDGET.md targets RTX2070/16GB RAM/8GB
VRAM at1080p,16.7ms courts/sanctuary and22ms city-facing plaza. Current crowd
capacity captures use1280x720 at77percent internal scale and game-thread CSV mode.
They cannot establish that1080p release budget. Final benchmark matrix must also
use the intended release resolution and representative courts/city views.

## Bounded search diagnostic native result — 18 September 2026

Source52a0c9da passes active11/11,math33/33,Editor/Game,clonequick6/6. Search01
package retains all six cooked hashes through immutable NTFS hardlinks; its child
is a separate verified copy. Native10000 request with1024attempts seeds9817,
refuses183; six engine budget readbacks match, childexit0, wrapper correctlyfails.
East/deck complete; west41/plaza32/street59/approach51remain refused. Root viewed
finalPNG. The45/60 sample retains3487frames,59.99s,median16.928ms,p9521.331ms at
720p/77percent for9817actual people. No1080p or causal timing claim. Default48
remains unchanged. See crowd-search1024-10000-review.json;5000same-budget test next.
Read-only street source/renderLOD0 audit scripts are prepared to compare the two
reviewed identity-transform assets with32hash-pinned packaged contacts. Their
syntax and input parse pass; native extraction is still pending. No asset saves.

Audit-runner review correction: guard owned-child Refresh/Stop-Process in a nested
try/catch inside finally, and save the receipt afterward even when cleanup throws.
Do not let a cleanup exception erase the original diagnostic/failure record.

Search1024 5000-request capture is terminal:4997seeded,3refused allinStreetBateiMahase
(101/104); otherzones complete. Sixbudgetreadbacks1024verified; childexit0, wrapper
correctlyfails. Root viewed finalPNG.45/60analysis retains1604frames59.96s,
median31.923ms,p9577.769ms. Concurrent verification read multi-GiB cooked data
during the run; this is NOT an isolated performance benchmark. The cause of the
slowdown versus other captures is unproven. Future release benchmarks must keep
owned heavy hashing, compilation and unrelated work out of measured windows.
Keep counts/evidence; do not attribute timing changes solely to crowd population.
See crowd-search1024-5000-review.json. Read-only native street audit is next.

## Street terrain collision audit — 18 September 2026

Read-only native audit street-native-mesh-20260919T010523238528Z.json completed
with child exit0 and peak1.443GiB private memory. Both asset hashes stayed unchanged.
Identity-transform terrain07_09 (actor2754) has512source triangles but255renderLOD0
triangles, Nanite enabled, fallbackRelativeError1, complex-as-simple collisionLOD0.
Its22packaged contacts match renderLOD0 within0.000001cm, but sit1.25..18.82cm
above source geometry. Asphalt02GridN004P004 (actor4503) has74triangles in both
representations; all10contacts match both within0.000001cm. This implicates reduced
terrain fallback geometry; it is evidence for investigation, not a repaired asset.
Next: preserve source geometry and other settings while testing full-fidelity
terrain fallback, then replace the approximate street ground plane with audited
surfaces. Changing expected heights alone before collision agrees risks overlap.
No asset saves, placement-rule changes or new cooked release occurred in this audit.
Both tree quick gates pass6/6; native audit and5000evidence independently verified.
UE5.8 MeshBuilderCommon/Private/NaniteHelper.cpp CorrectFallbackSettings confirms
Auto can replace fallback_relative_error during build; setting that number alone
is insufficient. Explicit PercentTriangles with fraction1 sets effective error0.
Use that explicit target for the backed-up single-terrain fidelity experiment;
retain the rest of the existing settings struct, then verify fresh native geometry.

## Street fallback fidelity repair — 18 September 2026

repair_crowd_street_fallback.py changes only terrain07_09 Nanite fallback target
from Auto to PercentTriangles with100percent retained, using its existing struct.
Original SHA043684bd...48e7 is backed up under ReviewCheckpoints/street-fallback-
20260919T011657361835Z; repaired SHAbd73bd26acbdfea670ba6a68df8ac2ee6908d5cb5dba9f37102689ff8c674ab0.
Apply and fresh native verification both exit0. Source/render now512/512triangles;
1558source-corner/contact checks have zero height difference. Source positions and
triangles match the pinned original audit exactly. Complete settings/materials
survive save/reload; collision mode/LOD unchanged. No map or asphalt asset edits.
Receipts street-fallback-20260919T011657361835Z and20260919T011719681520Z preserve
apply and fresh evidence. This is source-asset acceptance, not a newly cooked
collision/contact proof or completed street placement fix. Exact street model and
full recook/runtime testing remain next; old checkpoints retain old collision.

Commandlet lesson: insert the script directory into sys.path before sibling imports.
StaticMeshEditorSubsystem can be absent in commandlets; direct set_editor_property
sends change notifications and rebuilt this mesh, verified through native extraction.
Do not instantiate an uninitialized subsystem. First two attempts failed before
saving any asset (import path, then missing subsystem); receipts retained locally.
Fresh verification must compare persisted materials and complete settings against
the successful apply receipt plus original hash-verified backup, not against itself.

## Exact street crowd ground model — 18 September 2026

StreetBateiMahase now uses highest source terrain/asphalt triangles (8+18faces)
on the selected48 shipping map, through the same exact-surface path as Kotel.
The generator pins the native source audit, fresh fallback repair proof, zone file
and current terrain/asphalt asset hashes. It refuses drift; verify.py checks the
header against the generator. No old native contact is used to fit a new plane.
The math test covers repaired terrain height, unchanged asphalt native contact,
101x101 zone support coverage and missing distant support. Existing support,
spacing, protected-area and capsule checks stay intact; default search budget48.
Runtime walking uses existing exact-surface height deltas. Source/runtime gate and
new full cook/packaged contact/population acceptance remain pending for this change.
Never reuse the old checkpoint Paks: terrain fallback changed in03896243.
Source verification now passes active12/12 (including33/33math and Editor/Game),
publicationquick7/7 and seven-file parity. Packaged collision/contact and crowd
counts remain unverified until the new full cook is tested.

## Packaged exact street ground result — 18 September 2026

Source7eb95a1a full cook completed at20260919T014906Z, archivecrowd-street01-
20260919T012805Z, childSHA12e118429cea92fcb71a8d8f4636c06c3fe0e3212f9e46b471c9aea3e6775fc1.
Both map hashes unchanged. Cook took21minutes under physical-memory pressure but
completed each stage and exit0; do not restart a still-live cook just for slowness.
Fresh package hashes recorded before runtime measurement; no competing owned heavy
hash/build work during measurement. New5000diagnostic with1024attempts placesall5000,
zero refusals in everyzone, late-frame count5000/0, childexit0 and CSV finalized.
Street104/104, groundrefusals0;32street contacts maxabsolute residual0.000029cm.
All192zone contacts retained. Root viewed PNG: Kotel crowd/paving remain visible.
Diagnostic30/30 has1943frames,median15.334ms,p9518.073ms at720p77percent, not final
1080p performance acceptance. Default48attempts,10000counts, all-frame movement,
state transitions and final appearance remain open. See crowd-street01-5000-review,
matching timing, package manifest and frametime receipt. Next test default5000 or
same-budget10000; do not claim diagnostic1024budget as the production default.

Street01 10000-request diagnostic completed normally with9847placed/153refused,
childexit0; wrapper correctlyfails population. Refusals west41/plaza32/street29/
approach51. Street improves149->179with same1024budget; east/deck already complete.
192contacts retained;32street maximumresidual0.000030cm, so preserve exact ground
and existing support guards. Spacing dominates smaller-zone first-failure counters.
30/30analysis1858frames,median16.062ms,p9518.496ms at720p77percent is diagnostic,
not final1080p or causal performance proof. Root viewed finalPNG. See
crowd-street01-10000-review.json and timing/receipt. Next investigate packing of
unchanged cohorts/identities within existing zones; do not reduce separation,
force missing groups into individuals or move them onto priestly/interior floors.

## Whole-cohort placement fallback — 18 September 2026

Offline geometry-only packing study reproduces native plaza239/271 and15264trials;
refused cohorts are eight triples and two fours, no singles. Sorting the same1024
candidate points along the strip improves some zones but fills none completely.
Study source/fixture/results are retained in Scripts/study_crowd_packing.cpp and
crowd-vat/packing-study01. It omits native ground/obstacles and is not a capacity bound.

New runtime treats authored zone weights as preferred initial distribution. After
that unchanged first pass, intact refused cohorts try other enabled visitor zones,
ordered by initial placement success with stable ties. This intentionally permits
final zone counts to differ from preferred allocation; it preserves all identities,
cohort sizes/membership, original standing decision, existing successful placements,
80cm minimum separation,120cm group spacing, exactground55/20checks and34/96capsules.
No group is split or moved after initialization. Only already-refused identities can
be retried; each enabled destination is tried once with existing48/default or the
same diagnostic override. Still-unsafe groups remain counted as refused. Logs retain
six initial audits plus each recovered cohort, six final zone counts and totals.
This changes the earlier allocation-preservation choice to complete the requested
population in permitted areas without cramming whole groups into preferred strips.
Pending source verification and packaged evidence; no10000acceptance claimed yet.
Source fallback gate now passes active12/12,33/33math, Editor/Game and clonequick7/7.
Independent study rebuild matches all nine saved rows; ten-file parity and accounting
review pass. Native fallback counts/distribution/visuals still need validation.

## Whole-cohort fallback native result and default adoption — 18 September 2026

Source09b27654 overflow01 child1ad8ce80e88d67a6aa878d05f007ce6e84e4aeefc4316c659df3da4c73512ba8
retains six verified street01 cooked hashes through immutable hardlinks. Native48
initiallyrefuses660;94cohorts recover264, final9604/10000. Childexit0 and wrapper
correctlyfails. Samebinary1024 initiallyrefuses153;44intactcohorts recoverall153,
final10000/10000,0refused, normalexit and CSVfinalized. Finalzones east2921,west2018,
deck4402,plaza239,street179,approach241.139people fallbacktoeast,14todeck. Recovered
IDranges are unique, remainwithinoriginalpreferred-zone cohort ranges, destinations
enabled; summaries reconcile initial/final counts. Original standing choices retained.
Root viewedbothPNGs. Default48diagnostic1650frames median17.950ms,p9523.052;
1024diagnostic1815frames median16.351ms,p9519.577.30/30 at720p77percent, no final
1080p or causal speed claim.192groundcontacts each; fullmotion/state/appearance open.
See crowd-overflow01 and crowd-overflow1024 10000-review, combinedtiming andreceipts.

Newsource adopts1024 as SocialSeedAttempts after this nativecomparison; non-social
SeedAttempts remains48. Same bounded loop/checks/fallback, now no override needed.
This source default change still requires its own build and no-override native run;
full10000 is proven only for the tested09b27654 binary with1024override so far.

Default adoption source verification passes active12/12, math33/33, Editor/Game
and publicationquick7/7. Independent review verified both native evidence sets,
exact original cohort membership, final accounting, all hashes and11-file parity.
Logs: verify-social-default-20260918T222811.stdout.log, Editor-rh59b_9o.log,
Game-n5zv6qfa.log and verify-social-default-publication.log in Working-5.8.
Native slot confirmed empty after owner's restart-complete message. The new binary
still needs packaged10000 without GroupSeedAttempts override; normal map default
population and final1080p performance remain separate unverified acceptance items.

Production search default native proof: bd075bd3 default01 archive20260919T023531Z,
child0086af4dca0d888bc8abeddd1191859e91a547fbbd45ce386c0dee6a5e388c26.
Explicit10000 with NO CrowdSeedAttempts override places10000/refused0 and exits0.
Six native budgets1024; initial9847 plus153 recovered, final zones match prior
diagnostic exactly. PNG reviewed: Kotel crowd and paving visible.30/30diagnostic
1870frames median15.960ms p9518.137ms at720p77percent, not final1080p acceptance.
Normal map-default population, crowd appearance/movement and state checks remain.
See crowd-default01 package/review/timing and capture receipt/PNG. Native slot free.

Packaged map-default audit now confirms1600/0refused, no CrowdCount or
CrowdSeedAttempts override, childexit0. Header10000 is overridden by savedmap1600.
This uses isolated saves/menu bypass; it is not full ordinary-menu/save acceptance.
Kotel PNG visibly sparser, paving intact.30/30 diagnostic2039frames median14.648ms
p9516.818ms at720p77percent. Keep1600 fact distinct from proven10000 capacity.
See crowd-default-map01-review/timing and capture receipt/PNG. Release default
still needs selection against1080p performance and actual behavior acceptance.

1080p outercourt performance pair (bd075bd3/default01) misses16.7ms target.
High77percent internal, camera4974 0 468 0 180 0,45settle30record, normalexits.
10000/0refused:1516frames median19.315 p9522.847 GPUmedian19.013ms.
No crowd:1768frames median17.055 p9518.805 GPUmedian16.803ms. Paired median
delta2.260ms is a single-run comparison, not repeated causal proof. Base scene
already exceeds target; optimize scene GPU work as well as crowd.2500/5000,city
and other views remain. BothPNGs reviewed; pale leaning slab left of stairs
persists without crowd, actor/intent not identified, add to geometry investigation.
See crowd-1080court01 review/comparison and both capture receipts/PNGs.

1080court01 countmatrix complete for0/2500/5000/10000 atHigh77percent,45/30.
New2500 and5000 runs reach fullcounts,0refused,exit0.2500:1714frames,median17.425
p9519.839;5000:1653frames,median18.045 p9520.509ms. Allfour medians miss16.7ms.
BothPNGs reviewed; centerstairs lane open. Single serial runs, not repeated causal
estimates; cityviews, motion/state/appearance and releasepopulation still open.
See crowd-1080court01-matrix/midcounts-review and2500/5000receipts/PNGs.
PowerShell batch lesson: capture script does not set LASTEXITCODE on success when
invoked in-process. A stale value stopped the wrapper after successful2500. Check
terminal receipt status,errors,childexit andCSVfinalized; do not rerun validcapture.
5000 was launched separately after verifying2500 evidence, no duplicate native job.

Cloud-shadow diagnostic: capture_crowd_frametime now accepts bounded optional
CloudShadowSampleCap (0unchanged;4/8/16/32/64/128), logs override and requires
native console readback. Production settings/assets unchanged. UE5.8 source uses
base16*lightscale capped by RaySampleMaxCount(default128), then horizonfactor.
Cap8 native10000/0refused exit0,1661frames45/30:median17.899 p9520.871ms;
GPU16.820 vs19.013baseline. Cloudshadowpass2.064 vs3.989medianms; TSR3.350vs3.341.
Single diagnostic improvement, still misses16.7ms, noadoption. Root courtPNGreview
finds noobviouslightingregression; city/open-sky/movingcloudshadow checks owed.
See crowd-cloud8-01 review/comparison/gpu-passes and capturereceipt/PNG.

Historical plaza_over_city station11500 -300 400 yaw270 now shows a denseouter
corridor, sky and narrowcitystrip, NOT fullcitypanorama. Do not acceptfullcity
budget from thiscamera. Nativepair10000/0refused bothnormalexit,1080pHigh77%,45/30:
baseline1449frames median18.682 p9542.255;cap8 1680frames median16.821 p9527.489.
Median improves1.861ms but frame-time tails remainopen. BothPNGs reviewed; noobvious
static sky/wall lighting regression. Motion/cloudshadows and correctedpanorama
required beforeadoption. See crowd-citycloud8-01-review/comparison and bothcaptures.

Filmstriptool repaired: no screenshotdeletion or evidenceoverwrite, freshlabel/view,
fixed-step simulatedframe windows instead ofwalltime, contiguousnumeric sourceframes,
CSV-controlled normalexit, hiddenownedprocess,9/8/1.25GiB memoryguards,diskreserve,
receipts/frameshashes andlatepopulationreadback. ExtraArgs nowbounded CrowdCountonly.
Defaults10secsettle3secrecord30fps; not a performanceinstrument. Failed acquisition
cannot report success merelybecause anyPNGexists. Oldframes retained acrossruns.
Three native smoke acquisitions exit0,63/393/93dumpedframes with30/90/30retained.
BUT renderedcrowd is absent despite10000placement. Rootviewedrepresentativeframes.
Warmup1->10sec didnotfix; explicitHigh77percent/noShowHUD didnotfix. Thus initial
warmuphypothesis rejected. No movementacceptance; investigatefixedstep/dumpmovie
visibility beforemore acceptancecaptures. Review+receipts+samplePNGspublished;
allretained frameshashpinned andkeptlocal. Do not confuse acquiredframes with visualpass.

Crowdvisibility diagnosis advanced: ordinary scheduledShot fixedstep04 stillempty;
normalclock/noBenchmark05 alsoempty. Thus notspecific toDumpMovie orfixedstep.
Real05 sixactiveCrowdPose components report total10000 InstanceCountToRender but
NumBuiltInstances0; placementalone isnotrenderreadiness. EngineHISM initialforceSync
onlyappliesbeforeWorldHasBegunPlay; oursseedsnexttick afterBeginPlay. Concurrent
instancechanges invalidateasyncbuildresults andcanrestartinitialtree indefinitely.
Newsource callsBuildTreeIfOutdated(false,false) onceperinitialpose aftercustomdata,
beforemovementtick, VAT/nonVAT; logsCrowdRenderSeedV1. Nativeproofpending, nofix
acceptanceyet. Capturetooladds boundedScheduledShots(120frames/30kcmd) andnormal
clockdiagnostic(nullsimulatedtimestamps). Bothfailedruns preserved; do not call
this fixedstep-onlyfailure. See crowd-render-readiness-review and04/05receipts/PNG.

Initialrenderreadiness source48275a33 now native-proven. Fullgate12/12 math33/33
Editor/Game andclone7/7 passed. Runtimearchive renderseed01-20260919T035419Z child
ee8ccc0355651d1c0adaeec0e295970f57805f446dc536158a5e70dd06970479 usesverified
siximmutable street01 cookedhashes. Sixinitialtrees1667/1667/1667/1667/1666/1666
built=instances=render, total10000.1280x720partialframe60 nowshowscrowd butrun
hit8GiBguard(8642469888bytes), stoppedownedgame; retainedasFAILED, nooverride.
Repeat640x360same10000/fixed30fps acquires90frames,retains30,exit0,peak7872077824,
late10000/0refused andtreesstill10000built. Rootframes60/89 showcrowdandmotion,
but visiblesmearing; NOTfootcontact/appearanceacceptance. Initialinvisibilityfixed;
newbinaryperformance andlongerclosemotionstillowed. See renderseedpackage/review
andfailed/successfulreceipts/PNGs. Allretainedframeshashpinnedlocal.

Newrender-readybinary48275a33 real-time1080court10000 runnormalexit0,all10000/0
refused,sixinitialtreesbuilt. High77%,45settle30record,nocloudcapoverride:
1520frames median19.150 p9524.242 p9944.339 GPUmedian18.918ms. Medianclose
tooldbinary19.315,notrepeatedcausalproof;16.7mscourtbudgetandframetailstillfail.
RootPNGviewedcrowdvisible/centerlaneopen; motionandappearancepending. See
crowd-renderperf01-review/timing andreceipt/PNG. Nextclosemotiondiagnostic.

Capture-only UnfilteredMotionDiagnostic requests screen100, AA0 plus AntiAliasing
showflag0, motionblur0; saves receipt flag, never production settings. Native
crowd-unfiltered01 corridor640x360 fixed30fps2+1s:10000/0refused,exit0,30retained,
peak7900708864 under8GiBguard. All retained hashes verified. Rootframes60/89 have
sharper silhouettes but jagged edges/stippled paving. Combined diagnostic supports
rendering contribution to smearing, not isolation of individual setting or motion/
footcontact acceptance. No adoption; close motion and temporal velocity remain.
See crowd-unfiltered01-review and receipt/samples. Six cooked hashes verified.

Temporal isolation01: optional capture switches DisableMotionBlurDiagnostic and
DisableTemporalAADiagnostic retain77percent; no production change. Blur-off and
AA-off corridor captures plus close camera11500 -300 200 -10 270 0 all finish
10000/0refused,exit0,30retained each under8GiBguard. All90 retained hashes checked.
Root reviewed blur/AA frame60 and close60/89: blur-off no clear improvement; AA-off
harder outlines with pixelation. Temporal reconstruction contribution supported,
not fixed. Close view reveals crude proxies; motion visible, footcontact unproven.
UE Time node supplies PrevFrameGameTime automatically; absence of PreviousFrameSwitch
alone is not a bug. HISM bTeleport changes physics, not a justified render fix.
Investigate per-instance anchor history and near detail. See crowd-temporal01-review.

Crowd proxy-lifetime candidate: PushVat and nonVAT transform batches now pass
bMarkRenderStateDirty=false. UE5.8 TransformChanged/CustomDataChanged mark instance
data dirty; inherited SendRenderInstanceData_Concurrent flushes changes and updates
bounds without explicitly destroying the scene proxy. Initial synchronous HISM tree
seed and initial MarkRenderStateDirty remain. This is a source candidate, NOT a
native smearing fix claim: compile, visible moving instances, count/tree integrity,
performance and culling after movement must pass before acceptance. bTeleport remains
unchanged (physics flag); no asset/material/placement changes.

Incremental instance candidate2d5e0c24 passed active12/12 math33/33 Editor/Game,
clone7/7. Archive incremental01-20260919T042349Z child69b200f479581165efba57a01d1cf9c0822514134a652c56c3a61978f77053f2.
Six immutable cooked hashes verified. Close640x360 fixed2+1s:10000/0refused,
exit0,30retained,all6 latebuilt total10000. Rootframes60/89 showmovement, no clear
smearing improvement. 1080pHigh77percent court45/30 exit0 full10000:
1640frames median17.856 p9521.208 p9940.374 GPU17.551ms; old19.150median.
Single-run improvement, not repeated causal proof; still misses16.7ms and tails.
RootcourtPNG reviewed, centerstairs open, pale slab unresolved. No visualfinish
claim. See incremental01 package/review, incrementalperf01 timing and receipts.

Scene defect identification: InspectScenePixel U V is an opt-in read-only console
command. Validates normalizedviewport coordinates, deprojects currentview, traces
visibility simple/complex to100m and reports up to24 nearest staticmesh bounding
candidates (including noncolliding meshes). Bounds are NOT triangleidentification.
No actor/asset/state mutation. capture_people_walk_movie supports bounded InspectPixel
and requires one native completion marker. Needed because oldSep9 snapshot didnot
identify current pale slab left of courtstairs. Native identification remains pending;
do not hide/delete guessed geometry. Earlier NE-horizon slab is a separate report.

Court pale slab IDENTIFIED by packaged complex pixeltrace and exactactorreadback:
StaticMeshActor_0 owns SM_MikdashWaterV1_CourtChannel, transform0.96/(-248,0,0).
The exposed X3600->3660 canonicalfall remains cover=True, producing solidconduit
and suppressing water surface. Do NOT delete the channel as orphangeometry.
New offline build_court_outlet_v2.py opens only thisfall in freshCourtOutletV2:
route/bed unchanged, frozenV1 triangles reconstructed exactly;2196/2228stone and
1010/1020water triangles preserved, all changed geometry confinedX3500..3750,
Y950..1150. Closedpositive solids andOBJreadback pass. Nativeimport/materials/map/
collision/render acceptance still owed; originalV1 untouched. See ScenePixelV1
identification and CourtOutletV2/candidate.json. NE-horizon slab remainsseparate.
Capture lesson: UE FCommandLine max16384, NOT Windows32767.16552char actorquery
failedpreinit (receipt retained); no successclaim fromexit0. ScheduledShot basenames
useGameScreenshotSaveDirectory (GameEngine defaultsScreenShotDir);6360charretry
succeeds. New15000charconservative guard and boundedInspectActorPath readback.
Pixelprobe127aggregatebounds are NOT identity; vegetation filledfirst24 candidates.
Exactcomplexcollisionactor thengetall OUTER mesh query established ownership.

## Court outlet native candidate — 19 September 2026
CourtOutletV2 now has two fresh imported assets, verified in a separate native
process: stone 2236 and water 1028 triangles. Every float32 triangle position and
winding matches both source and render LOD0. Native winding is reversed from the
canonical authoring convention; the same exact adapter is independently proved
on BOTH frozen V1 assets. Do not infer an import bug from canonical winding alone.
All existing maps and V1 asset hashes remain unchanged. Materials match V1 slots.
The first strict canonical-winding assertion failed and its receipts are retained.

Native inspection uncovered a separate collision defect: V1 uses one generated
convex hull across the entire roughly 117 m route. V2 imports have no simple hulls.
Copying V1's hull would preserve phantom blocking space. Backed-up V2-only settings
now use CTF_USE_COMPLEX_AS_SIMPLE, verified in a fresh process. Existing V1 assets
remain untouched; source and render geometry match exactly. This is asset-level
verification, NOT physics traversal or visual acceptance. The water actor must
retain its existing NoCollision profile when integrated.

Scripts/import_court_outlet_v2.py and run_court_outlet_v2.ps1 use isolated 6/4/2 GiB
limits. Import resumes only missing siblings, validates existing candidates, and
never replaces them. Collision mode backs up candidates before changing policy.
Final receipt: SourceAssets/water-review/CourtOutletV2/native-20260919T050825803318Z.json.
Next: guarded Candidate48 map integration with verified backup, exact actor/material/
transform/profile preservation, fresh map readback, fresh cook, same-camera image
and actual character walking tests. No public walkthrough or scene-fix acceptance yet.

## Court outlet map integration prepared — 19 September 2026
integrate_court_outlet_v2.py prepares an exact two-binding Candidate48 update.
It pins the accepted map and verified V2 assets, backs up the map, preserves actor
and static-mesh component transforms/material overrides/visibility/collision/tags,
and requires a matching fresh-process snapshot before acceptance. Existing maps
and V1 meshes are protected. Water retains NoCollision; masonry retains BlockAll.
The source-map wrapper enforces 20/16/4 GiB commit/private/reserve limits.
Its first apply attempt refused BEFORE launching because free commit was below
20 GiB (approximately 19 GiB observed). No map was loaded or saved. Native testing
of this new integration script remains pending; do not claim map adoption from
source review. Continuing packaged performance work within its 9/8/1.25 GiB guard.

Current binary1332e820 court2500 capture currentmatrix01 exited0 with all2500,
zero refused seeds, six rendered seed groups, and no guard errors.1080pHigh77%,
45s settle/30s record:1604frames median17.925ms,p95 27.651,p99 39.312,GPU17.462.
Still misses16.7ms court target. Root inspected late PNG:people visible, center
stairs clear; old slab remains because map adoption is pending. Single-run evidence,
not motion/footcontact acceptance. Current-binary0/5000/10000 still owed. See
SourceAssets/perf-review/crowd-vat/currentmatrix01-court2500-review.json.

## Current crowd count matrix — 19 September 2026
Same source1332e820/scenePixel01 binary and immutable cooked scene now have
0/2500/5000/10000 court captures, all exit0, exact requested counts, zero refused.
1080pHigh77%,45s settle/30s record, no cloud-cap override. Frame medians in count
order:17.144/17.925/18.495/18.030ms; GPU16.780/17.462/18.042/17.677ms.
Game-thread medians7.102/8.796/8.970/9.707ms. Every run misses16.7ms court target;
nonmonotonic frame/GPU results require repeated matched trials for causal claims.
Root reviewed all late PNGs:people visible, center stairs open, V1 slab remains.
No motion/footcontact/appearance acceptance. This closes the current-binary count
measurement task only; performance, scene finish and public walkthrough are open.
See SourceAssets/perf-review/crowd-vat/currentmatrix01-review.json and count timings.
Raw CSVs/logs retained locally and hash-pinned; receipts and PNGs published.

## Crowd motion history diagnosis — 19 September 2026
Read-only InspectMotionState capture option requests LIST ISM and velocity/AA cvars,
requires native readbacks, and changes no rendering settings. motion-state01 close
capture finished10000/0refused,exit0,30retainedframes. All six11-floatVATgroups have
previousTransform=0,dynamicData=0. Velocity.EnableVertexDeformation=2 Auto with
VelocityOutputPass=0 means vertex-deformation velocity IS enabled; AA=4 TSR.
Do not attribute smearing to a globally disabled velocity switch.
UE HISM explicitly clears dynamic data; SceneData falls back to current instance
transform, MaterialTemplate reads current custom data. A synthetic analytical model
shows constant-motion reanchors remain correct, while turns/stops reconstruct wrong
previous positions. This is NOT measured live-transition frequency or a visualfix.
Frame89 reviewed:near proxies still coarse. Need bounded live old/new anchor samples
before changing the versioned CPU/material custom-data contract; keep normal AA.
Evidence: SourceAssets/perf-review/crowd-vat/MotionHistoryV1. Source-map integration
still awaiting20GiB free commit; latest observation belowthreshold, no map changes.

## Bounded live crowd transition audit prepared — 19 September 2026
Opt-in -MikdashCrowdMotionAudit records4096 social VAT simulation updates after
2s warmup, with at most64 detailed changed rows and one summary. It snapshots each
agent before/after the normal StepSocialAgentVat call, reconstructs the root at
Now-DeltaSeconds with old/current anchor state, and counts heading changes. No
movement, placement, collision, material or instance-data mutation is introduced.
Ordinary runs skip all copies/calculations/logs. Scope excludes distance-frozen/
culled transitions and VAT vertex deformation; root error is a shader-model estimate,
NOT measured velocity-buffer pixels or visible-smear attribution. Lower dt clamp
assumes the authored NegativeDtSeconds0.25 contract. Capture AuditMotionTransitions
requires exactly one4096-update completion marker. Compile and native evidence pending.

## Live crowd history audit complete — 19 September 2026
Source608ea4c2 passed active12/12,33math,Editor48.87s/Game51.74s,clonequick7/7.
Runtime-only motionaudit01-20260919T054907Z uses six hash-verified immutable Paks;
child9e5c7298c00c5c1c4d853255082370c8efb564e652bdf432d5e7cbe139d77a6d.
Native fixed30fps closecapture exits0 with10000/0refused and30retainedframes.
Audit completes4096 eligible social updates after2s:358 root errors>0.1cm,
511 heading changes>0.1degree, maxrooterror4.714286cm,64detailedchangedrows.
Independent analyzer recomputes everylogged root/heading result;maximum root
residual0.000001347cm. Frame89 reviewed:crowd visible,near proxies still coarse.
This supports a previous-state contract correction, NOT a visualsmearingfix or
long-run frequency claim. Rootmodel excludesVATdeformation/pixelvelocity and
assumes authoredNegativeDtSeconds0.25. Next freshversioned CPU/materialhistory
candidate must preserve current-frame behavior and pass native motion/perf review.
See SourceAssets/perf-review/crowd-vat/MotionHistoryV1/live-review.json.
Analyzer review lesson: reject NaN/Infinity in EVERY parsed scalar before numeric
mismatch comparisons; abs(NaN)>tolerance is false. Motion audit reader now checks
finite times/horizons/yaw/errors, nonnegative horizons/errors, heading0..180 and
bounded summary counters. Current native data is finite; malformed-log rejection
is verified separately and must not weaken the native evidence requirements.

## Crowd motion history candidate implemented — 19 September 2026
Opt-in -MikdashCrowdMotionHistory uses the new 26-float CrowdVATV3 contract.
The released 11-float path remains default. Each visited agent snapshots its old
state BEFORE any freeze/cull stop or simulated mutation. A separate visit-time
boundary matters: an idle heading change need not change its anchor time.
PreviousFrameSwitch preserves current WPO; previous-frame evaluation selects old
phase/rate/velocity/idle/blend/horizon only before the visit boundary. Compensation
includes the REST vertex plus VAT displacement, relative yaw, world anchor offset
and world drift; body scale and idle offset remain constant. Later frames use the
current interval. No changes to placement, steering, collision, AA or map bindings.

Native builder created one fresh master and 59 material instances for all six
meshes. Every candidate preserves all resolved original scalar/vector/texture
parameters; no original mesh/material/map bytes changed. Fresh-process readback
verifies saved WPO switch/interval wiring, custom-data dependency sets, indices
0..25, zero Custom nodes, usage and exact material parameters. Guards6/4/2GiB,
both processes exit0. Evidence: SourceAssets/perf-review/crowd-vat/MotionHistoryV3.
Candidate directory is explicitly cooked for runtime name loading; ordinary
runs remain unchanged. Missing candidate material makes opt-in refuse with error.

Active full gate12/12,33math,Editor44.70s/Game49.76s. Four tests evaluate the actual
stock-node callback against independent world-vertex trajectories, including
150random transitions, turns/stops/starts, idle heading-only changes, initial
history, later frames, body scale and float32 payloads. They use synthetic VAT
clips and do not prove native texture/velocity output. Native fresh cook, actual
activation, current-frame A/B, velocity/motion and performance acceptance remain
required. This is a concrete opt-in correction candidate, NOT an accepted smear
fix. Capture -UseMotionHistoryCandidate requires one full activation marker.

Crowd history checkpoint a7acc552 is pushed. Fresh cook crowd-history01 started
20260919T061743Z with 19.08GiB free commit/6.8GiB physical, existing 16/4 start
guards, LowMemory/SkipZenStore, new unlinked archive. Wrapper PID33152 owns this
job; inspect its actual process and UAT log before any retry. Cook/visual acceptance
is pending. First launch PID26728 was terminal before cooking: Windows PowerShell
5.1 could not resolve Get-FileHash in the inherited environment. Use the same
bundled pwsh returned by Get-Command pwsh, not System32 powershell.exe. Its retry
is live; do not launch a second cook. Logs/launch records: Working-5.8/cook-historyv3-*.

## Crowd motion diagnostic capture prepared — 19 September 2026
Capture now accepts MotionVisualization=Velocity or Reprojection (defaultNone).
These use Unreal global renderer showflags, not BufferVisualization material
assets that are absent from the current packaged cook. Velocity uses HSV direction/
magnitude (r.MotionBlur.Visualize1), debug overlay off. Reprojection compares
current colour with previous colour warped by the rendered velocity texture.
See engine PostProcessMotionBlur.cpp, VisualizeMotionVectors.cpp/.usf and
PostProcessing.cpp; actual packaged activation/images remain to be tested.

Readback review lesson: an ANY-match search for the expected console value can
pass on a startup echo even when the later value is wrong. Capture requires the
LAST numeric exact-variable readback and records its line/value/count. Tests of
the actual PowerShell block pass last-good, and reject startup-good/last-bad,
wrong numeric10, missing, and prefixed-lookalike variables. No render acceptance
is implied by parser/source tests. Fresh cook still owns the native slot.

## Crowd history packaged evidence — 19 September 2026
Fresh crowd-history01-20260919T061743Z cook/archive exited0 in19m4s, no shader
compile errors; both maps unchanged. ChildSHA c8c628021a9e38355916566bd494581c9e304bfaa7245938f394b56bf6ca9d23. Wrapper33152/UAT/cooker are terminal; native slot released.
Normal/HSVvelocity/reprojection control and candidate captures all exit0 with
10000/0refused,30retained frames each,640x360/77%,fixed30fps,2ssettle/1srecord.
Candidate activation confirms26floats/sixposes. All65 logged original-model
audit payloads match between normal control/candidate (simulation unchanged).
This audit still models the OLD reconstruction; its nonzero errors are NOT a
failure of the candidate shader and cannot measure the candidate's pixel error.

Repeated original velocity captures:28/30pixel-identical, other two differ by
at most4pixels. Candidate A/B changes0..4465pixels/frame. Root sees substantial
rotation vectors near pixel(150,210) atframe75 where the original barely showed
rotation. This proves a native velocity-output change, not numerical accuracy
or visually resolved smearing. Root reviewed normal/velocity/reprojection pairs;
close crowd proxies remain coarse. Higher-resolution/moving-camera review,
longer transition/freeze coverage and candidate frame-time/GPU cost remain.
Default remains original11float path; no adoption or crowd-finish claim.
Evidence: SourceAssets/perf-review/crowd-vat/MotionHistoryV3/packaged-review01.json.

Native diagnostic parser correction: UE bool console variables print true/false,
not numeric0/1. First velocity-old01 receipt remains FAILED (nativeexit0), because
readback rejected false. Last-value parser now accepts bool/integer, rejects an
invalid or empty LAST value (cannot fall back to a valid startup echo), and stores
the raw token. Nine actual-block regressions and fresh old02/new01 captures pass.
All failed evidence is retained; raw old01 frames are only repeatability evidence.

## Crowd history performance comparison started — 19 September 2026
capture_crowd_frametime.ps1 now has explicit UseMotionHistoryCandidate, recorded
in the receipt and requiring one26-float/six-pose activation with no refusal.
No fixed-step/movie flags are introduced into the real-time profiler. Guards
remain9/8/1.25GiB. First control off01 began before this tool extension, so its
receipt lacks the new boolean field; command line and absence of activation
confirm the original path. All runs use the same fresh history01 childc8c62802.

Control off01:10000,1080pHigh77%,court4974 0 468 0 180 0,45ssettle/30srecord.
1579frames/30.01s:frame median17.865ms,p95 31.279;GPU17.559,game9.707.
Still misses16.7ms target. Root reviewed late1080pPNG:people visible at sides,
central stairs clear, unchangedV1water slab still present. Candidate on01 is
collecting; do not infer cost from a single run. Matched repeated trials needed.

## Boarding bridge crowd ownership resolved — 19 September 2026
The six extra 40-instance/3-custom-float HISM groups in the packaged motion
inspection belong to MikdashTransitBoardingBridge_0.BridgePose0 through
BridgePose5, not MikdashCrowdField_0. Existing movie-historyv3-candidate01-corridor
runtime.log contains the full reflected component paths (NumBuiltInstances).
MikdashTransitBoardingBridge.cpp independently configures three custom floats.
Do not classify these 240 bridge figures as orphan crowd instances or remove them.
The motion-history candidate targets the main crowd field; bridge motion needs
its own review if a defect is observed.

## Crowd history performance ABBA completed — 19 September 2026
All four same-child 10000-person real-time captures passed acquisition, native
exit0, finalized CSV, 45ssettle/30sanalysis, 1080pHigh77% at the same court camera.
Order:off01,on01,on02,off02. Frame medians respectively17.865/18.263/18.339/18.202ms;
GPU17.559/17.865/18.570/18.222ms; game9.707/9.944/10.115/9.767ms.
Mean of run medians:control18.0335 vs candidate18.301ms(frame),17.8905 vs
18.2175ms(GPU),9.737 vs10.0295ms(game). Observed differences +0.2675/+0.327/
+0.2925ms are descriptive; two runs per setting and drifting controls cannot
establish a precise causal cost. All runs miss16.7ms and frame p95 reaches40.911ms.
No performance acceptance or default adoption. Root reviewed all four late PNGs:
crowds visible, central stairs clear; old water slab remains. Moving-camera and
higher-resolution motion-quality acceptance remain open. Evidence and raw-file
hashes: SourceAssets/perf-review/crowd-vat/MotionHistoryV3/performance-abba01.json.

## Grounded crowd walking capture — 19 September 2026
capture_people_walk_movie.ps1 now accepts optional WalkTo XY. Go XYZ then denotes
capsule-center start; existing packaged MikdashWalkProbe restores collision and
uses ordinary movement. No C++ or crowd behavior changes. Requires fixed-step,
three settle seconds, unique native start, no stall events, at least two grounded
moving samples inside the retained window and100cm displacement. Scheduled
screenshot limit240frames (formerly120); existing15000-character command limit,
9/8/1.25GiB memory and disk guards remain. Default stationary capture unchanged.
Control historyv3-walk-old01:1280x720,normalHigh77%,10000,3ssettle/3srecord at30Hz,
90retainedframes,exit0; five grounded600cm/s samples span1200cm, z98.7. Root sees
coarse close proxies and a modern dark gloved first-person hand atframe120.
Do not call people visually finished. Hand ownership/replacement needs separate
inspection. Candidate same-route capture is collecting; no comparative claim yet.

## Matched moving-camera crowd pair — 19 September 2026
historyv3-walk-old01/new01 both pass acquisition:90retained720pframes,10000people,
exit0, same c8c62802 child. All walking log payloads identical; five retained-window
grounded600cm/s samples span1200cm. All180retained hashes match. Root reviewed
frames105/120/150 in both. Coarse angular close figures, noisy distant edges and
modern gloved visitor hand remain. Corresponding stills do not establish a clear
motion-quality improvement; continuous playback/turn-stop review remains owed.
No default adoption. SourceAssets/perf-review/crowd-vat/MotionHistoryV3/walking-review01.json
pins evidence. This is moving-camera acquisition and sampled visual review, not
full route acceptance, collision avoidance acceptance or crowd completion.

Visitor-hand source lead: printable package references show BP_MikdashWalker
inherits /Game/FirstPerson/Blueprints/BP_FirstPersonCharacter. That parent references
FirstPersonMesh, SKM_Manny_Simple, ABP_Unarmed and ABP_FP_Copy. This is a source
ownership lead, not a native component/material binding audit. Inspect the live
pawn or isolated blueprint before changing visibility or replacing the hand.

## Visitor template hand correction — 19 September 2026
Walking movie evidence exposes the modern mannequin glove in ordinary visitor view.
Earlier native CameraObstructionV1/PhotoPawn-639250857235150000-000.json confirms
BP_MikdashWalker owns FirstPersonMesh/type1 and CharacterMesh0/type2, both bound
to SKM_Manny_Simple. HideVisitorTemplateHands now selects ONLY the exact local
BP_MikdashWalker class, owned FirstPersonMesh, FirstPerson primitive type and
exact Manny asset. SetHiddenInGame(true,false) runs after possession and BeginPlay;
world-space body, child visibility, collision and animation remain unchanged.
Future authored hand assets do not match this template-specific policy. PhotoMode
only restores its world-space representation selection, so it should not restore
the hidden hands. Build and fresh packaged walking acceptance are pending; do not
claim a finished visitor avatar or hide unrelated skeletal components.

Visitor-hand build gate passed12/12,33/33math, Editor and Game compiled. Fresh
runtime-only archive Checkpoint-visitor-hands01-20260919T072356Z uses identical
history01 cooked scene (six immutable linked Paks, never cook/write here) and
new child6a26468a4294de812cf37440f7cbe75abd1376ff4badabf43337a2bd8cad53dd.
Build receipt SourceAssets/build-review/visitor-hands-runtime01.json pins source
and package hashes. New capture RequireTemplateHandsHidden queries late owned
FirstPersonMesh/CharacterMesh0 hidden flags and requires true/false respectively.
Native walking/render/readback acceptance is currently collecting.

Visitor-hand walking acceptance passed: movie-visitor-hands01-corridor,90retained
720pframes,10000people,nativeexit0. Root reviewed before/after105/120/150; modern
glove in control105/120 is absent. Late native FirstPersonMesh.hidden=True and
CharacterMesh0.hidden=False. All15walking events exactly match old01 control;
five grounded600cm/s samples span1200cm with no stalls. Both source map hashes
unchanged. Acceptance SourceAssets/visual-review/VisitorHandsV1/acceptance01.json.
This accepts narrow glove removal in walking, not a finished visitor avatar/crowd.
Photo/dove return regression stays on broader release acceptance; source lifecycle
review preserves existing photo world-space-only visibility restoration.

## Near-crowd candidate and source limitations — 19 September 2026
Walking evidence shows 2400triangle distant proxies at arm's length; source spec
explicitly intended30-200m. New isolated CrowdNearV1 candidate retains Man_Standard's
19600source triangles (9924vertices,10slots), with72walk/192idle frames. Native
AnimToTexture packs3rows/frame:width3308,walkheight216,idleheight576. New optional
allow_multiple_rows preserves default single-row restriction in existing bake.
Actual stock-node clip AST test spans1536float32 cases (72/192frames,1/2/3/6/11/21
rows,width3308/4096,vertex-row/frame-loop boundaries). Formula remains UV.v+f/N:
installed AnimToTextureBPLibrary.cpp encodes vertex row/height and WriteVectorsToTexture
starts each frame at rows*width*frame. No live mesh/material/map binding changed.

build_crowd_near_v1.py creates16fresh assets under CrowdNearV1; default only verifies.
Build/fresh-readback passed under6/4/2GiB isolated guards; buildpeak~2.98GiB.
First attempt failed BEFORE asset creation: AnimSequence.skeleton is not a direct
Python property; use get_editor_property('skeleton'). Failure receipt retained.
Protected original CrowdVATV1 assets, source body/clips and all maps hash unchanged.

Native isolated GPU comparison: full-source head/hat/silhouette smoother than2400
proxy, but torn-looking clothing/layer breaks remain. Full-detail alone is NOT an
accepted fix. Native skeleton reference pose also shows collar/mantle breaks.
SetPosition(0) changes single-node time but DOES NOT evaluate bones in this GPU
commandlet; the first skeleton comparison is NOT pose-matched. Engine source
confirms UAnimSingleNodeInstance::SetPosition only updates proxy time. Capture tool
now labels skeleton reference pose explicitly; prior receipts/images retained.
Need actual same-pose deformation/garment clearance analysis before attribution.

Candidate is NOT cooked/adopted. Still needs production bounds expansion (old VAT
uses +/-110cm XY to cover motion/extrapolation), same-pose animation validation,
source garment repair as indicated, six-variant near/far transitions and performance.
Do not replace all10000 figures with full-detail meshes. Render-target images use
transient actors and native materials at static walkframe0, not HISM movement.

## Crowd mantle source repair — 19 September 2026
Native NearV1 reference rendering showed actual garment overlap, not merely a
low-poly VAT problem. Exact source-GLB positions/weights/indices match the procedural
Man_Standard generator. Original reference mantle penetrates tunic by3.824cm and
sash by4.985cm at sampled vertices/triangle centres. Simple reference-only outward
projection failed walk poses; projecting front/back separately also collapsed
cloth thickness. Never use independent envelope projection on both cloth sides.
New build_crowd_mantle_study.py fits coherent paired cloth vertices across reference
and eight walk/eight idle poses from the shipped animation GLB. Edge trim takes the
adjacent cloth displacement AND weights: original entire hem used mantle_back
weights even at front. Body/cloth weights and all animation bytes stay unchanged.
Only mantle/trim positions/normals and trim joints/weights may change; verifier
compares GLB JSON, exact permitted binary-byte ranges, bounds and normalized weights.
Study03 still had0.183cm sampled overlap; Study04 fit poses passed but independent
halfway walk0.825s found0.034cm overlap. Both rejected for clearance. Study04 native
reference A/B clearly removes jagged cloth breaks; candidate is broader, with lower
mantle displacement up to11.918cm, so side/back silhouette review remains necessary.
Study05 raises target clearance from2 to2.5cm; full walk240Hz/idle30Hz verification
and new native comparison are collecting. No released mesh/material/map bindings
changed. Tests cover mantle vs tunic/sash, NOT sleeve/collar/skin/SashTail clearance,
continuous collision, cloth self-intersection, animated native VAT or all variants.

Study05 full source clearance passed384poses (walk288at240Hz, idle96at30Hz,
endpoints excluded): zero sampled mantle/tunic or mantle/sash intersections.
Candidate GLB c25c435c64cd30bf8e80c96bfe7689a36ebea3ec007c349bc1bdcda702f0527b;
exact31153changed binary bytes stay within permitted attributes. Original source
positions, weights, indices, joint translations and inverse-bind matrices match.
Native three-view before/after reference capture20260919T080803175867Z passed,
exit0,peak3.21GiB,protected maps/crowd assets unchanged. Root inspected all6images:
jagged tunic/sash breaks disappear front/side/back. Lower mantle is broader by
up to12.420cm; stylized shoulder/garment shape still needs final art judgment.
Rotate review lights with camera: previous rear views were too dark to evaluate.
Acceptance record CrowdMantleStudy05/acceptance01.json pins source,384pose audit,
native receipts/images/logs. Only source candidate, NOT production adoption.
Next import/bake fresh native crowd candidate and verify actual animated poses.

## Repaired mantle native crowd candidate — 19 September 2026
CrowdNearV2b holds 33 fresh assets (25,316,463 bytes), imported from the hash-pinned
CrowdMantleStudy05 GLB. Full-detail mesh remains 19,600 triangles/9,924 vertices,
10 slots/3 UV sets. Walk/idle bake72/192frames, 3rows/frame at width3308. Bounds
extensions now match production policy: positive(110,110,25), negative(110,110,15).
No live actor/material binding or cook inclusion changed.
First CrowdNearV2 import failed the key-count gate: Interchange defaults did not
preserve60Hz. Use pipeline animation.use30_hz_to_bake_bone_animation=False and
custom_bone_animation_sample_rate=60 with readbacks, as release_walk_v2 already
requires. Fresh V2b import then returned73walk/193idle keys and correct lengths.
The editor saved the complete V2b bake but exited3 during shutdown with
'Object is not packaged: ModeManagerInteractiveToolsContext None'. This is NOT a
successful normal build exit. All failure receipts and partial V2 assets remain.
Fresh commandlet readback exited0 and validates every V2b asset hash, mesh stats,
material slot, texture dimensions/settings and bounds. Commandlets have no
StaticMeshEditorSubsystem; obtain UV count from GeometryScript source-model copy
and get_num_uv_sets instead of dropping the UV invariant. New wrapper uses
UnrealEditor-Cmd and no quit_editor; that readback route passed. A fresh build via
this revised commandlet route has not yet been exercised.
Native capture cannot call Actor.add_component_by_class (not Python-exposed;
this was already documented by import_instances_ue58). For this crowd test spawn
transient MikdashCrowdField and use its owned default CrowdPose0 HISM, initially
empty. Set11custom floats before adding one instance; read back each phase.
Capture082122191777 uses four frozen walk phases0/18/36/54 with zero rate/horizon,
not a running movie. Native AnimPoseExtensions raw pose comparisons match all27
bones exactly between original/candidate imports at all4times. This proves pose
correspondence between those imported clips, not exact VAT vertex reconstruction.
Root reviewed all8native before/after PNGs: cloak/tunic/sash breaks are removed at
all4poses. Lower legs still visibly protrude through the unchanged tunic in both
versions. Source leg/robe clearance audit is running; this remains a distinct
release blocker. Cloth shoulders, other variants, real-time motion and near/far
transitions/performance also remain open. All native processes are terminal.

Source lower-leg audit finished: original V3 Man_Standard walk has leg/robe
protrusion in all288samples at240Hz, maximum23.848cm (FootL,t0.5167s). Source
positions/weights were already proven identical in CrowdMantleStudy05; V2b did
not alter the tunic or legs. This independently confirms the old source defect.
Before authoring another V3 repair, evaluate EXISTING create_resident_v4.py and
ResidentV4 assets for near crowd: they already implement higher hems, thigh/calf
cloth weights, mantle attached to tunic motion, richer faces/UVs/vertex colours.
Do not assume V4 is accepted: native rendering/clearance and VAT material support
must be checked, especially preserving its six-slot vertex-colour shading. V3
was intended as a distant proxy; further close-art work should reuse the newer
resident source where valid. NearV2/review01.json records the narrowed candidate
result, normal-exit readback/render, abnormal builder shutdown and lower-leg
blocker. Frozen HISM pose capture is reusable for the newer source.

## ResidentV4 close review — 19 September 2026
Read-only native review captured six existing ResidentV4 meshes, body and face.
First attempt083008 had ShaderCompileWorker access violation -1073741819, exit1;
this is NOT a confirmed skin shader source error. Unchanged rerun083434 exited0.
All12 baseline images reviewed: orange skin, crushed black beards, layered elder
beard, collar slits and shoulder gaps (especially youth) block close-art acceptance.
Some feet are cropped by the fixed body camera; do not claim complete silhouettes.
Transient VCDecodeExponent=1 study083602 exited0 but faces remain visually very similar;
2/12 image hashes are identical. No color-space diagnosis follows until effective
material values/updates and pixel differences are measured.
Follow-up083706 confirms all six native source material slots expose this parameter.
Protected maps/crowd/ResidentV4 assets unchanged in every run. No source edits,
new assets, bindings or adoption. NearResidentV4/review01.json pins the evidence.
Older September15 clearance receipts were inspected, not rerun here. Next: audit
native parameter values/update and source shoulder joins before near-crowd baking.

## Resident vertex-colour repair — 19 September 2026
Native graph audit084121 found BOTH ResidentV4 masters' Power.Exp unconnected:
release_resident_v4 used invalid pin name Exponent and ignored connection return.
Actual const exponent2 squared the already-linear COLOR_0. This also explains why
transient parameter1 read back correctly yet all six face RGB images were unchanged.
Use Exp, check connection return AND native graph readback. Builder now defaults1.
Source create_resident_v4 declares linear vertex colours; native skeletal import
calibration color-calibration-20260918T210959Z preserves linear RGB within2/255.
Transient corrected graph+exponent1 capture084216 visibly reduces orange skin.
Backed-up repair084445 saved two masters and14 instances (six slots/eight garment
variants); no meshes/maps/bindings changed. First apply084355 stopped before any
mutation on a wrong expected count13; retained failure receipt. Native fresh
readback and post-save GPU acceptance must complete before shipping this repair.
Beard darkness/shape, shoulder gaps and collar slits remain separate open defects.

Resident linear repair acceptance: fresh readback084511 and post-save GPU084546
both exited0. All12 post-save RGB images EXACTLY match the transient corrected
graph study, linking six reviewed faces and six reviewed post-save bodies. Native
material repair accepted; close character art and packaged/in-scene review remain
open. Two masters+14instances changed with verified checkpoints; all protected
meshes/maps/crowd assets unchanged. linear-repair-review01.json pins evidence.

## Resident youth shoulder candidate — 19 September 2026
ResidentShoulderStudy05 closes detached youth sleeves by tucking proximal rings
10.75/10.5cm inward and smoothing displacement/torso-weight influence over18cm.
Source-only candidate; no live meshes/maps/materials replaced. Native transient
front/side/back reference capture085451259597 exited0, protected files unchanged.
Root inspected all after views: gaps closed; Study04 abrupt angular root rejected.
Independent binary audit permits only sleeve position/normal/joint/weight bytes
(5129 changed); all original morph data, topology, UVs, colours and non-sleeve bytes
preserved. Build from finalize(assembly(...)), not raw assembly. Rest attributes,
indices and inverse binds match source; regenerated morph normals differ, so retain
original binary outside allowed ranges rather than silently re-exporting the mesh.
Motion root check:384poses (walk288at240Hz,idle96at30Hz,endpoints excluded).
Worst nearest outward upper-tunic signed root distance drops9.2626cm to-0.6273cm.
This verifies sampled proximal attachment only, not whole-sleeve collision or
continuous/native animation. Candidate SHA60f43e3995850bcb9bf84595ce231408d513b1210f55b057d45857274180d4e6.
Native animated review and other five variants remain required before adoption.

## Native resident pose review — 19 September 2026
MikdashAnimationReviewLibrary evaluates a skeletal component's single-node clip
with TickAnimation(0) and RefreshBoneTransforms; SetPosition alone does not update
bones in the capture commandlet. Helper refuses non-commandlet use, game worlds,
non-transient actors, mismatched skeletons and invalid/out-of-range time; packaged
builds return false. No runtime caller. Editor target compiled successfully.
Youth native four walk phases0/.3/.6/.9 (three views, before/after) passed090543:
five tracked bone positions match source/candidate, hand positions vary across
phases, protected assets unchanged, normal exit0. Root inspected all12after views;
shoulder attachments survive these discrete native poses. Not a real-time movie.
Capture now imports transient candidates onto each existing variant skeleton via
release_resident_v4._mesh_pipeline; it creates no new animation and saves nothing.
All other five source candidates passed384 root samples each. Man_Heavy baseline
already stays inside (-0.447cm worst), so do not adopt its optional geometry edit
without visual benefit. Builder tolerates only1e-12 regenerated-normal differences
(two near-zero Man_Standard normals differ1.21e-17); final byte patch still preserves
ALL original non-sleeve bytes including morphs. Native cast review is underway.

Native cast capture batch finished: all six commandlets exit0,24PNGs each (four
walk phases,three views,before/after), five tracked bone positions equal across
source/candidate, moving hand confirmed, protected assets unchanged. Cast02
review01.json lists root visual inspection scope exactly; some adult side/rear
and intermediate views remain to inspect. No live adoption or real-time claim.

## Resident shoulder integration — 19 September 2026
All adult after views reviewed as 480px contact tiles (four walk phases, three
views), supplementing prior full-resolution images. Five candidates accepted for
shoulder attachment; Man_Heavy original retained because it was already attached.
Backed-up native adoption091820 exited0, changing ONLY five existing ResidentV4
mesh files. Six material slots, each matching skeleton, and Face0..3 preserved.
Fresh-process091942 readback exited0 and verified saved file hashes and bindings.
SourceAssets/characters-review/ResidentShoulderAdopt01 contains the selected GLBs
and adoption receipts; use these sleeve sources after any ResidentV4 regeneration.
Original generator/manifest remain historical inputs; do not regenerate over the
accepted repair without reapplying this source patch and its checks. No maps or
crowd VAT assets changed. Fresh GPU comparisons underway. Collar gaps, beard art,
garment silhouettes, whole-body collision and in-scene/package review remain open.

Saved-mesh GPU acceptance: all five fresh commandlets exited0 (092002 through
092157), protected files unchanged, five tracked bones match candidate at each
phase. Of60 saved-mesh views,55 are RGB-exact to previously reviewed candidates.
Only first front/t0 frames differ; root inspected five side-by-side contact pairs
and Standard at full resolution. Shoulder shape/attachment match; small shading
and edge differences remain, cause unproven. This accepts saved shoulder repairs
for discrete native poses, not complete character art or a packaged release.

## ResidentV4 crowd pilot — 19 September 2026
CrowdResidentStudy01 converts the repaired Man_Standard into 8000/2400 triangle
VAT candidates, preserving six material slots and UV0 plus walk/idle UV1/2.
Successful isolated build093046 exited0:24 assets,8000tri4599verts (two rows/frame)
and2400tri1442verts(one row/frame). Existing maps, ResidentV4, PilgrimRigV3 and
CrowdVATV1 unchanged. Native source .skeleton attribute is absent on AnimSequence;
use get_editor_property('skeleton'). First build092923 failed before creating
assets on that API mistake; failure receipt retained.
Pilot shader adds linear vertex colors and UV0 mottle onto the existing stock-node
VAT shader. Source six slots/roughness/specular/tint/mottle retained, per-instance
brightness still active; palette/skin variation disabled for this comparison.
Fine pore/weave normal detail and skin subsurface are not yet implemented: this
is NOT a complete near-character material or a default crowd adoption. Fresh
readback/color/texture checks and GPU source-versus-two-level comparison pending.

ResidentStudy01 GPU093255 normal0 rejected for washed-out source colors.
Engine source MeshDescriptionToDynamicMesh.h default bTransformVertexColorsLinearToSRGB
and CopyMeshFromSkeletalMesh source-model route confirm an implicit linear-to-sRGB
transform. Opt-in _convert(linear_source_colors=True) reverses it via GeometryScript
VertexColors BEFORE simplification, preserving linear-space color averaging.
Default conversion remains unchanged for existing crowd workflows. Study02 is a
fresh namespace using this correction; do not fix this by changing the accepted
ResidentV4 skeletal material exponent. Shader fine-normal/subsurface gaps remain.

Study02 fresh build093601/readback093746/GPU093802 all normal exit0 and protected
assets unchanged.24saved assets;7999tri/2399tri, six slots/three UVchannels. Native
color readback now2767/1086 uniqueRGB, minR.0231/.0289 vs Study01.1662/.1961.
Root inspected both frame0 levels full-resolution and all12 source/candidate
frames in480px tiles. Warm colors restored and four sampled poses follow source.
Skin remains darker (surface mismatch unresolved); collar/face/narrow trim lose
detail under decimation, especially2400. Neither candidate adopted. Next: complete
material match and detail policy, remaining variants, real-time/distance/perf.

## Resident crowd surface parity pilot — 19 September 2026
Study03 adds source pore/weave/strand detail texture/tiling/strength per slot and
MSM_SUBSURFACE skin (.62,.20,.11 color, .38 amount). Stock-node cotangent frame
uses pixel DDX/DDY of WPO-including world position and UV0, so detail follows VAT
deformation instead of the static rest tangent. VAT world-space normal remains
the base; max tangent-length normalization has a1e-12 degeneracy guard.
Native build094544, fresh parameter readback094712, GPU094727 all normal exit0.
Root inspected both frame0 levels full-resolution plus all12 source/candidate
images as480px tiles. Skin shading now visibly closer to source and cloth detail
present across four poses. Face/eye/collar/trim decimation defects persist; neither
mesh is accepted for close viewing/default adoption. No scene/crowd changes.
Saved graph connectivity verification added after bounded verifier review:
checks Normal upstream derivative/detail/world-position chain, linear vertex
color and source subsurface pins plus source parameters. Fresh check underway.

Study03 saved graph readback094928 normalexit0: all four masters preserve connected
VAT normal interpolation, exactly twoDDX/twoDDY nodes, WPO-including worldposition,
normal sampler, vertexcolor and subsurface values. All12 MIs match recorded
texture/vector/scalar values; skin parents/models match; protected files unchanged.
This closes the pilot surface-wiring gap, not remaining crowd acceptance.

## Crowd distance and full cast candidate pass — 19 September 2026
Standard distance captures095346/095408 exited0, no protected changes. At45degree
FOV/960square,source height~100px at20m/~50px at40m. ThresholdRGB>8 foreground
silhouette IoU min:8000target .9522/.9700;2400target .9306/.9521 at20/40m.
Root inspected all24 native-size crops.50px is a provisional visual reference for
in-scene distance policy, NOT a universal pass threshold or adopted cutoff.
Wrappers/capture support bounded100..10000cm explicit distance; omitting it keeps
the exact original80,240,105 camera. Added validated cast selector for five more
variants under isolated Cast/<name> folders; selected skeleton/WalkV2/idle stay
matched. Serial build/fresh readback/close+40m captures underway for all five.

## Full cast crowd review checkpoint — 19 September 2026
All five additional Study03 variants completed build, fresh readback, close and40m
GPU captures:20 native processes exited0;130 saved assets and120 PNG hashes match.
Post-interruption checks revalidated protected hashes and saved evidence. Root
reviewed all close contacts and all five40m contacts. Elder man2400 is rejected
for new skin-through-robe patches in poses0/18/54. Both women show altered dark
lower-skirt shading; cause unproven. Face/cap/collar/trim losses remain, strongest
at2400. Youth/Heavy broadly follow the four sampled source poses. No cast level
is adopted; frozen frontal poses do not establish continuous clearance, side/rear
quality, live distance transitions or performance. See Study03/cast-review.json.
Next: investigate simplification/deformation transfer for robe artifacts, then
continuous multi-view checks and measured runtime integration. Distance alone
must not be used to declare these defects resolved.

## Crowd deformation isolation — 19 September 2026
Study04 opt-in constrains GeometryScript simplification to existing vertex
positions (preserve_vertex_positions=True, setter/readback required). Study03
remains default. Source colors, surface shaders, driver count and animation
clips remain the same to isolate this factor. Testing Elder and Woman_Young in
fresh namespaces before considering adoption; no quality claim yet.

Study04 Elder native comparison retains lower-skirt skin protrusions; preserving
positions alone is not a fix. Woman_Young still has dark lower-skirt patches and
severe2400 face collapse. Study05 isolates one driver triangle (instead of stock
count) atop04. Study06 returns to03 positions/drivers and tests AttributeAwareV2
with scale_correction100 (cm-to-meter metric), color_attribute_weight16. Engine
Runtime/GeometryScripting/.../GeometryScript/MeshSimplifyFunctions.h documents
that default AttributeAware optimizes normals only; V2 adds colors/UVs/seams.
This is evidence for a color-loss hypothesis, not proof that the patches are
caused by vertex-color simplification. All studies remain opt-in, default03.

Study05 Elder and Woman_Young rendered all12 poses each: one driver does not
remove observed robe protrusions/dark patches. Study06 Elder retains more trim
but produces major pointed silhouette artifacts and clipping: reject adoption.
Study07 combines06's color-aware metric with preserved vertex positions to
constrain off-surface relocation; fresh isolated test pending. Do not confuse
source setter/readback success with visual acceptance.

Study04/05/06/07 complete:24 guarded native processes exit0,208 assets,96 GPU
captures. Root reviewed all eight close contacts; current450 protected hashes
rechecked.04 and05 do not resolve defects.06 causes major sharp projections,
rejected.07 combines color-aware metric with existing vertex positions: prior
visible Elder robe skin patches and06 spikes are absent in four sampled front
poses; Woman_Young trim better preserved without06 projections.2400 face/belt
and skirt-shading defects remain.07 is a promising candidate, NOT a close-view
or runtime adoption. Next: broader phase/side/rear validation, investigate
remaining skirt shading, improve detail allocation, then other cast and measured
runtime integration. Per-study review.json records hashes and limited findings.

## Resident crowd multi-view phase review — 19 September 2026
Capture wrapper adds explicit Front/Right/Rear/Left and opt-in Sweep (12 frozen
walk phases, stride6 at60Hz). Original default camera, light yaws and four phases
are preserved. Key/fill lighting rotates with selected view for readable sides.
Study07 Elder/Woman_Young eight guarded native captures underway. This expands
visual sampling; it is not a continuous clearance or real-time performance test.

Expanded Study07 review correction: eight native12-phase/four-view captures
exited0 (288 PNGs); two Study03 right-view baselines exited0 (24 PNGs). Root
inspected24 sweep contacts plus2 baseline contacts.07 is rejected for adoption:
Elder2400 frontframe60 exposes orange skin (small54patch also visible on closer
review); Right view reveals strongly thinned/open-looking2400legs in both cast
variants and new Elder8000 robe skin exposure. Rear/side layered intersections
and jagged hems persist. Earlier four-front-pose observations were insufficient
and must not be promoted into a clearance claim.03 also has robe intersections
but its2400leg silhouette is much less degraded than07. Color/trim improvement
therefore trades away geometry quality. Next: measure geometry allocation and
protect limb volume/layered garment clearance via per-part budgets or source
topology reduction; do not keep escalating global color weighting. No adoption.
Evidence: ResidentStudy07/sweep-review.json; defaults still four front phases.

## Resident per-material detail allocation — 19 September 2026
Study08 reserves explicit triangle budgets for six material groups. Body/eye/hair/leather use the original normals-aware simplifier; cloth/garment use07's color-aware existing-position metric. Extraction must preserve every material ID and triangle accounting. Isolated Elder/Woman_Young candidates only; source repairs/default03/runtime remain unchanged. Native readback and side/rear phase review are required before any quality claim.

Study08 first native attempt failed before asset creation: MeshBasicEditFunctions.h's Python ScriptName is GeometryScript_MeshEdits (not GeometryScript_MeshBasicEdit). Corrected to engine declaration; retry built Elder successfully. All six material IDs and triangle counts checked before append. Elder four-view review shows fuller legs but robe skin exposure persists at8000, severe mantle/belt intersections and new skin patches at2400. Do not adopt. Remaining female validation pending.

Study08 complete:12 successful guarded native processes (2build,2fresh readback,
8four-view sweeps),52 assets,288 GPU PNGs and24 inspected contacts. One initial
API-name failure occurred before assets and is recorded separately. Current450
protected files unchanged. Legs retain fuller side silhouettes than07 in both
variants, but8000 still exposes skin through right-view robes (Woman notably
throughout sweep).2400 severe mantle/belt layer intersections, angular hems and
Woman headcover collapse remain. Both levels rejected; no adoption/default change.
Separate material budgets are insufficient to preserve garment clearance. Next:
inspect source garment topology and deformation correspondence, then constrain
shape/clearance rather than repeat unconstrained metric/budget sweeps.
Evidence: SourceAssets/perf-review/crowd-vat/ResidentStudy08/review.json.

## Full source topology crowd control — 19 September 2026
Study09 bypasses simplification entirely and retains source dynamic triangle count. One full-source VAT mesh per variant, same driver count and shaders as03/08. This isolates reduction from animation-transfer errors; it is a diagnostic, not a feasible thousands-of-people replacement or an adoption. Elder/Woman_Young side/rear checks pending.

Study09 capture exposed a harness assumption: set_static_mesh returnsFalse when the sole candidate is already bound on the next phase. Capture now skips redundant assignment and verifies the bound mesh. First partial capture is retained as failed evidence; retry required. Memory guards unchanged.

Study09 full-source control complete:8 successful guarded native processes
(2build,2fresh,4right/rear12phase captures),26 assets,96 successful PNGs,12
root-reviewed contacts. Initial redundant-set_static_mesh capture failure and
3partial PNGs retained separately.450 protected files unchanged. Static triangle
counts retain55528 Elder/50732 Woman; this is not full exported topology proof.
Both controls avoid the obvious new robe skin slits and belt-through-mantle
patches that rejected08 in these sampled poses. Inference: reduction contributes
to clipping, not necessarily the sole cause. Lower/inner robe and rear garment
shading still differs from skeletal source. No continuous-clearance, runtime or
performance acceptance. Next: preserve authored garment ring layout and layered
clearance during reduction; investigate full-source shading separately.
Engine mapping ranks all triangles without material partition; zero-distance
match takes weight1, otherwise inverse-distance. Do not assume shader parity or
complete skinning fidelity from a source triangle-count match.
Evidence: SourceAssets/perf-review/crowd-vat/ResidentStudy09/review.json.

## Structured resident garment reduction — 19 September 2026
Offline experiment in measure_resident_structured_reduction.py changes only
Tunic/Mantle indices on the original source grids. Preserve all source positions
and skin anchors; keep hem-shaping rows and waist/shoulder rows. Keep dense
original leg/tunic probes even when target faces are reduced, and use retained
hem vertices for the virtual cap. Verifier confirmed stride1/1 exact source face
identity for Elder/Woman_Young. Initial12-phase checks pass; full288-phase results are recorded below. No compact GLB/native import or accepted-shoulder changes. Existing
generator clearance excludes whole-body collisions, native VAT and visual quality.

## Structured resident garment reduction results — 19 September 2026
Four offline walk runs completed (288 poses each,1152 total):
- Man_Elder rows1/columns1: 15356 garment triangles; max leg outside 0.0cm, max tunic outside mantle 0.0cm.
- Man_Elder rows2/columns2: 5572 garment triangles; max leg outside 0.0cm, max tunic outside mantle 0.0cm.
- Woman_Young rows1/columns1: 16476 garment triangles; max leg outside 0.0cm, max tunic outside mantle 0.0cm.
- Woman_Young rows2/columns2: 5908 garment triangles; max leg outside 0.0cm, max tunic outside mantle 0.0cm.
Dense source probes and authored skin anchors retained. Stride1 reproduces source faces exactly (independent verifier). These measurements exclude belt/headcover/whole-body and native rendering; no adoption. Next: isolated compact export preserving accepted shoulder bytes, then native VAT and multi-view checks. Evidence: SourceAssets/perf-review/crowd-vat/ResidentStructured01/review.json.
