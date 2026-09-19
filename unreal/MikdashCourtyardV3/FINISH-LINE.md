# Mikdash finish-line tasks

Owner request, 18 September 2026: work continuously toward a finished project, including thousands of people and an online link where visitors can independently navigate and walk through the actual Mikdash. A screenshot gallery, video, shared spectator camera, or Windows download alone does not satisfy the online requirement.

The persistent Codex goal is active. This file tracks implementation and acceptance; unchecked work remains owed. Read the current handoff, plateau/S5 commit open items, integration queue and production plan. Historical status paragraphs are leads to audit, not current proof. Preserve the full production scope, including interiors, service/learning, sound, atmosphere and transit.

## 1. Establish the current release baseline

- [x] Read current handoff and publication HEAD (2f872366); S5 implementation is 00153f5e.
- [x] Identify accepted local build: Checkpoint-haram-S5-02-20260916T171759Z, with acceptance in SourceAssets/enclosure-review/HaramPrecinctV1/acceptance.json.
- [x] Preserve unrelated publication changes in both codex-entries.json files and untracked files.
- [ ] Audit current source/build hashes and reconcile production-plan/integration-queue items against current evidence.
- [ ] Resolve build headroom: C: had approximately 9.1 GiB free at intake. Owner approved deleting only Checkpoint-cp01-20260909T221426Z, Checkpoint-cp02b-20260910T003728Z and Checkpoint-cp03-20260910T025420Z (11,624,531,036 bytes total). Automatic approval review blocked the validated PowerShell deletion with "blocked by policy" before execution; no files deleted. User was given the exact folders for manual cleanup. Other archives remain protected.

## 2. Remove floating remnants and finish the environment

- [ ] Capture current packaged street, cut-cell, skyline, Kotel and precinct views through all three display states. First C1 attempt on 18 September refused before launch at the existing 9 GiB free-commit guard; no new frames or visual acceptance. Local diagnostics are finish-audit-c1.stdout/stderr in the working parent directory. mc-fw-host measured 10.35 GiB private memory.
- [ ] Identify each visible orphan by actor/component/source geometry, using reversible isolation. Prior roof, road and foundation fixes do not establish the cause of newly reported remnants.
- [ ] Repair owning visibility/geometry/terrain logic locally; preserve outside surfaces and original-state restoration. Require before/after engine images from identical cameras.
- [ ] Finish the thin exposed Haram apron edge without floor-only projection on vertical faces.
- [ ] Repair tree-bark shader fallback and verify foliage, trunks, shadows and scale in the packaged renderer.
- [ ] Pave Old City negative space coherently along the lane network; correct sunken stalls/arches, floating foundations, facade/roof defects and terrain seams.
- [ ] Re-run Kotel preservation, thirteen gate walks, interior/arrival routes and all state transitions after affected changes.

## 3. Finish people and believable activity

- [ ] Kohen Gadol skin normal/cavity, pale neck, then cloth weave/mitznefet/gems. Review actual engine close-ups and motion; preserve the approved Walter head.
  - KohenSkinV2 neck-color source study adjusts 2,139 vertices to the measured jaw tone with a smooth 150-156 cm transition. All non-color accessors and the face are preserved; three tests pass. Not imported, packaged or visually accepted. Normal/cavity skin master remains owed.
  - Extracted Walter's three original 1024x1024 skin maps with PNG CRC checks and reviewed albedo-pixel identity. Normal and RGB-packed cavity inputs are ready under KohenSkinV2/textures; read-only native function inspection identifies G convexity, B micro detail and R concavity (default switch path). Native Study03 material now exists with fresh-process structural readback. Native GPU A/B now succeeds within the same 4 GiB study cap. Swatch calibration proved imported vertex colors already linear; twelve material assets were repaired and freshly verified. Study03 head binding and full-scene/motion acceptance remain owed.
  - Paired offline previews show little visible change under the beard/collar. KG_Hair extends to Z142.165 cm, almost the head's minimum Z142.182 cm; beard_shell.mask lacks a lower-height cutoff. Native beard isolation confirmed the shell causes the strip. Study02 removes the lower coverage and passes source preservation; native front/three-quarter frames improve the neck, with scene/motion review still owed. Preview camera: target (0,0,155), distance 0.65 m, yaw 0.8, 700x700, ss=1, existing render_face_v5; not engine acceptance.
- [ ] Improve all six resident body variants and varied dress; review faces at 2 m and walking at 3-5 m.
- [ ] Optimize clearance measurement to relevant vertices; measure walk, idle and tend without concealing intersections.
  - Current script already limits skinning to garments/legs. Conservative distance pruning cut a three-frame idle profile from 30.5 s to 8.9 s without changing its results; five regression tests pass. Full 97-frame idle results match exactly: original 673.0 s, optimized 249.2 s (2.70x faster), zero measured leg/robe and inner/outer garment intersections. Full 60 Hz tend completed: 601 samples over ten seconds, zero measured leg/robe and inner/outer garment intersections. Full walk measured 288 samples at 240 Hz: zero leg/robe intersection, but inner/outer garments intersect by up to 0.388 cm at t=0.2958 s, rest Z36 cm. This remains an open defect requiring correction and native visual review. Evidence: SourceAssets/characters-review/ClearancePerformanceV1. All 33,312 measured garment/leg triangles match the exported source GLB exactly by float32 position, skin weights, material and winding. Generator geometry/animation-source measurements do not alone certify the shipped native mesh.
- [ ] Audit existing resident behavior work before changing it. Establish movement on the shipping map, identity/state persistence, schedules, interactions, access rules and the transit/crowd handoff.
- [ ] Eliminate doorway blocking, foot sliding, synchronized loops and visibly broken turns; prove with recorded engine motion and runtime routes.

## 4. Populate the scene with thousands

- [ ] Check crowd zones and height placement against S5 paving, stairs, buildings, gates and restricted areas.
- [ ] Test 2,500, 5,000 and 10,000 background people against a same-camera crowd-off baseline on the latest build. Record frame-time distributions, GPU/CPU/memory, visible count and movement quality.
- [ ] Choose the highest convincing sustainable population on the target RTX 2070, retaining detailed nearby characters and preserving identity/state at representation transitions where implemented.
- [ ] Verify dense areas from ground level and above. Historical 1,600-person measurements are not acceptance for this build or higher counts.

## 5. Complete the production experience

- [ ] Audit and close sanctuary/interior/vessel requirements against current source references and engine evidence, preserving guided-view/access distinctions.
- [ ] Verify service/learning interactions, sourcing, role restrictions and pause/save/load behavior; correct incomplete implementation.
- [ ] Audition sound, footsteps and ambience; resolve rejected repetitive loops and verify mute persistence.
- [ ] Audit and finish atmosphere, wind, vegetation and authored transport/boarding requirements from PRODUCTION_PLAN.md and INTEGRATION-QUEUE.md.

## 6. Share an independently navigable online walkthrough

- [x] Correct the delivery requirement: visitors open a link and control their own walkthrough on desktop or phone.
- [x] Initial feasibility: UE 5.8 has PixelStreaming and PixelStreaming2 installed; neither is explicitly enabled in this project's .uproject. No project touch-control implementation found in the initial scoped search.
- [x] Existing publication web/ is a Next.js book/typesetting application, not an existing Mikdash 3D player. Preserve it; do not replace it with the walkthrough.
- [ ] Build a local Pixel Streaming proof using infrastructure matched to UE 5.8; verify the actual packaged scene and browser input rather than a mock stream.
- [ ] Implement usable desktop and mobile controls: move, look, enter, pause/release, reset and appropriate navigation/help.
- [ ] Test independent visitor sessions, session limits/queue, disconnect cleanup and reconnect. Multiple viewers steering one camera fails this requirement.
- [ ] Prepare HTTPS/signalling and authenticated TURN/network traversal; test from an external network including a phone on cellular.
- [ ] Establish hosting capacity and cost before any paid commitment. Existing production constraint is no paid cloud spending. Do not change firewall/router/security settings or disrupt remote access without authorization.
- [ ] Deliver the real public walkthrough URL with tested controls and honest capacity/availability limits. A landing page without a working session is incomplete.

Technical references checked 18 September 2026: Epic's [Pixel Streaming overview](https://dev.epicgames.com/documentation/unreal-engine/overview-of-pixel-streaming-in-unreal-engine) and [hosting/networking guide](https://dev.epicgames.com/documentation/en-us/unreal-engine/hosting-and-networking-guide-for-pixel-streaming-in-unreal-engine). Streaming runs the native application on a GPU host and sends browser input back; independent sessions need capacity management. Cellular access may require TURN. This is an implementation direction, not an enabled service or a performance claim.

## 7. Final release acceptance

- [ ] Fresh cook/package; exact source, map, asset and archive hashes with retained failure evidence.
- [ ] Verify with Scripts/verify.py and the verify agent; run native jobs serially and active/publication gates sequentially.
- [ ] Packaged walking, collision, doors/stairs, interiors, crowds, sound, lighting, input, save/load and performance checks plus actual visual review.
- [ ] Test the online experience independently on desktop and phone, including two separate visitors, errors, queues and reconnection.
- [ ] Publish intended files only, commit and push each verified increment, and provide final build/URL/instructions/credits with limitations.
- [ ] Audit every task and referenced requirement; do not declare the goal complete from green tests alone.

## Owner decisions carried forward

Rock/Temple elevation remains unchanged pending the owner's explicit choice. Paid cloud hosting and archive deletion beyond the three explicitly approved snapshots remain unauthorized. Continue independent work while these decisions are pending; do not silently replace the requested outcome with a smaller one.

Lower-robe candidate in progress: optional 1.2 cm ease below Z60, taper to 0 at Z85; worst walk pose clears, full walk/idle/tend run pending. Default remains 0. Candidate export, native binding and rendered garment review remain owed. See KohenMeilEaseV2 studies.

Candidate run update: walk portion reports zero leg/robe intersection but about 0.41 cm inner/outer intersection at another pose. Candidate fails full-walk clearance and will not be adopted. Tending and idle continue in the same run; exact worst-pose details await its final receipt.

Robe diagnostics: wider skinning bands did not clear the sampled walk poses. Ease 5 cm clears seven targeted poses; full 240 Hz walk is running separately. Full clips, silhouette, outer decorations and native/render review remain required. Default geometry unchanged.

Layered candidate exported with approved face/rig preserved. Offline rest preview rejected the unlayered wider robe for hiding the ephod; revised study carries the ephod/edges with the taper and restores layering in that view. Full motion of all garment layers and native/render acceptance remain owed.

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

Full ease-1.2 measurement completed: walk 288 frames at240Hz fails with 0.411 cm
inner/outer penetration at t0.2708, restZ36; leg/robe zero. Tend601 at60Hz and
idle97 at30Hz both zero. This run used the pre-winding-fix measurement module.
Broader hem bands14/20/30 each fail at least one of eight selected outer-garment
poses. A sparse full-body walk with band20/ease1.2 fails by3.243 cm at the right
shin, t0.6857; outer penetration0.29 cm. Do not trade body clearance for layer
clearance. Receipts retained in KohenMeilEaseV2; production remains unchanged.

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
