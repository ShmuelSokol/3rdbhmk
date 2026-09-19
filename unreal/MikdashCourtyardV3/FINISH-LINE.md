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
