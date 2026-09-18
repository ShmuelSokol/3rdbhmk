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
