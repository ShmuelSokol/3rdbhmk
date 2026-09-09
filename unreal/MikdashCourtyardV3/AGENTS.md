## Current integration — 2026-09-09 04:53 UTC

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
