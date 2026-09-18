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
  - Extracted Walter's three original 1024x1024 skin maps with PNG CRC checks and reviewed albedo-pixel identity. Normal and RGB-packed cavity inputs are ready under KohenSkinV2/textures; read-only native function inspection identifies G convexity, B micro detail and R concavity (default switch path). Native material creation and rendered review remain owed.
  - Paired offline previews show little visible change under the beard/collar. KG_Hair extends to Z142.165 cm, almost the head's minimum Z142.182 cm; beard_shell.mask lacks a lower-height cutoff. Isolate that shell in engine before treating the full pale neck appearance as an albedo-only defect. Preview camera: target (0,0,155), distance 0.65 m, yaw 0.8, 700x700, ss=1, existing render_face_v5; not engine acceptance.
- [ ] Improve all six resident body variants and varied dress; review faces at 2 m and walking at 3-5 m.
- [ ] Optimize clearance measurement to relevant vertices; measure walk, idle and tend without concealing intersections.
  - Current script already limits skinning to garments/legs. Conservative distance pruning cut a three-frame idle profile from 30.5 s to 8.9 s without changing its results; five regression tests pass. Full 97-frame idle results match exactly: original 673.0 s, optimized 249.2 s (2.70x faster), zero measured leg/robe and inner/outer garment intersections. Full 60 Hz tend completed: 601 samples over ten seconds, zero measured leg/robe and inner/outer garment intersections. Walk is now running at its full 240 Hz sampling. Evidence: SourceAssets/characters-review/ClearancePerformanceV1. All 33,312 measured garment/leg triangles match the exported source GLB exactly by float32 position, skin weights, material and winding. Generator geometry/animation-source measurements do not alone certify the shipped native mesh.
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
