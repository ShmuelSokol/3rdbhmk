# Mikdash — Claude Code handoff

Prepared 2026-09-07. Read this first, then AGENTS.md and the referenced receipts. This describes the last known state, not a claim that the release is complete. Recheck processes and files before continuing.

## Immediate user priority

The user has only about 17% weekly Codex usage remaining and explicitly asked everyone to wrap up and produce one working version encompassing the work already done. Stop expanding research and starting new art projects. Integrate ready assets, fix release blockers, verify, package, and hand over a runnable build. Do not promise Warner Bros quality: that is an aspiration, not achieved evidence.

Original objective: Complete and verify a shareable Unreal Engine Third Beis HaMikdash walkthrough based on the existing measured Yechezkel reconstruction: full architecture, ground walking and collision, reviewed visuals, packaged build, authorized sharing. Track missing realism, source accuracy and runtime features honestly.

## Locations and publishing rules

- ACTIVE EDITABLE PROJECT: `C:\Mikdash\Working-5.8\MikdashCourtyardV3`
- Open `MikdashCourtyardV3.uproject` in that directory.
- Engine: `C:\Program Files\Epic Games\UE_5.8` (installed version previously verified 5.8.2).
- IMMUTABLE ORIGINAL: `C:\Mikdash\Mikdash-Windows-Transfer\EditorProject\MikdashCourtyardV3`. Never overwrite or regenerate it.
- Publishing clone: `C:\Mikdash\GitHub\3rdbhmk`, user-authorized public remote `ShmuelSokol/3rdbhmk`.
- Copy reviewed changes explicitly into publishing `unreal\MikdashCourtyardV3`; research belongs under `unreal\Research`. Preserve the root web/distribution project.
- Existing builds: `C:\Mikdash\Builds\Walkthrough-01` through `Walkthrough-05`.
- Last implementation commit verified on this handoff: `b26d2be` (sixteen Aron parts). Working project contains substantial later work NOT yet published. The commit adding this document may be newer.
- Verify before committing/pushing. Stage explicit named files, NEVER `git add .` or `git add -A`. Never force-push or skip hooks. Report commit hash. Do not sweep in caches, Intermediate, Binaries, node_modules, checkpoints or third-party reference exports.
- Read project AGENTS.md: it contains chronological evidence, including OLD entries superseded by newer receipts. Read `C:\Mikdash\Working-5.8\GIT-HANDOFF.md` if present.

## Best combined map — start here

`/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough`

File: `Content\MikdashV3\IntegratedReviewV2\Maps\Walkthrough.umap`.
Receipt: `SourceAssets\IntegratedReviewV2\native-integration.json`.
Status verified by reading receipt for this handoff: `integrated_review_saved_reopened_visual_runtime_acceptance_pending`.

This combines the future Mount platform, four cut terrain tiles, removal of Mount trees while preserving outside vegetation, sanctuary gold finishes, altar, shulchan, menorah, sixteen Aron parts, volumetric clouds and a newly bound wind sequence. It is NOT yet the final accepted playable release.

Default startup/game/cook settings were still pointing at `/Game/MikdashV3/Maps/Courtyard` at the last implementation checkpoint. Inspect only relevant map settings in Config/DefaultEngine.ini and DefaultGame.ini; do not print all DefaultEngine.ini because it contains a security token. Switch defaults and cook map to the accepted combined map after integration. Opening the project alone may otherwise show the older scene.

Integration helper: `Scripts\integrate_review_scene.py`. V2 is valid; V1 was stopped due to a quadratic verifier. Do not resume V1 blindly. Gold donor was intentionally used, not the unaccepted lighting-polish donor.

## Ready assets not yet placed in the combined map

Native import receipts: `SourceAssets\visual-review\native-original-assets-batch01.json` and `release-import-batch.json`. The latter was read for this handoff and records returned imports for rig, transit and Kotel. Inspect each asset-specific receipt before assuming details.

### Keruvim

Asset `/Game/MikdashV3/MaterialReview/KeruvimStudyV1/Meshes/SM_KeruvimStudyV1` imported (70,848 triangles). Place at the SHARED Aron origin `[-6200, 0, 925]`, yaw 90 degrees. Local geometry already starts at cover height; DO NOT add the cover height a second time. Local bounds approximately [-51.66,-32,83.3333] to [51.66,32,193.6667] cm.

`Scripts\place_keruvim_review.py` is ready but restricts itself to the Gold map, so adapt safely for combined placement or transfer after guarded review. Original geometry is a source-informed study, not exact revealed anatomy. Aron still lacks complete final details/luchot.

### Animated clothed pilgrims

Use PilgrimRigV2 rather than static V1 if native rendering passes.
Mesh `/Game/MikdashV3/CharacterReview/PilgrimRigV2/PilgrimRigV2/SkeletalMeshes/PilgrimRigV2`.
Same folder has `PilgrimRigV2A_Pilgrim_Original_Idle` and `PilgrimRigV2A_Pilgrim_Original_Walk`.
Receipt `SourceAssets\characters-review\PilgrimRigV2\native-import.json`.
Original weighted GLB: 27 joints, 29,336 triangles; validator passed. It is not directly compatible with Manny's skeleton.

For saved animation on SkeletalMeshComponent use `override_animation_data(anim, True, True, phase, rate)`, not transient `play_animation`. Ground every actor by native trace; do not populate prohibited chambers or block routes. A small outer-court group is a useful first acceptance step. Static/idle figures are NOT proof of goal-directed AI.

Do not publish `SourceAssets\characters-review\PilgrimRigV2\MannequinReference.fbx`: it is an exported Epic technical reference, not original authored work.

### Bus and proposed station

TransitV2 assets under `/Game/MikdashV3/ArrivalReview/TransitV2/Bus/` and `/Station/`, 25 material-group meshes total. Bus candidate XY `[-23101.764984,36185.432518]`, yaw `-60.07867649`; Z is UNKNOWN and must be traced. Candidate is mapped Batei Mahase road, outside protected area. Use V2, not the older opaque-glass bus.
Station geometry is authored and placement is unset: do not claim a real or source-proven railway there. No finished train exists. Bus aisle is too narrow for the player capsule; do not claim boarding.

### Kotel detail overlay

Six `SM_KotelFace_Tint0` through `Tint5` meshes under `/Game/MikdashV3/MaterialReview/KotelStoneV1` (inspect exact asset paths). Geometry is baked in world coordinates: identity transform, NoCollision. Preserve the original shared wall mesh/component. Overlay protrusion max about 3.2 cm. Courses/tints are artistic, not a survey-exact reproduction.
`Scripts\place_kotel_detail_review.py` creates a separate review copy and only accepts older source maps; adapt its guards explicitly if using V2. Inspect ground-level appearance before accepting.

## Other completed/source-only work — preserve, do not overclaim

- Doors/paroches: `Scripts\create_sanctuary_doors.py`, `SourceAssets\sanctuary-detail\DoorsParochesV1`. Nine original meshes, 90,588 triangles, exact placement/articulation JSON. Native import not run; helper requires an existing-material mapping. Paroches proposed [-5585,0,928], yaw -90. Heikhal opening is 500 x 2500 cm; Kodesh opening 350 x 300 cm. Do not use wall-veneer height as doorway height.
- Cedar/palm reliefs: `Scripts\create_sanctuary_reliefs.py`; original 120 x 260 cm panel, native import not run. No finished cherub-relief V2.
- Access: `Scripts\create_mount_access.py`, `create_kotel_opening.py`, `SourceAssets\mount-access\OpeningV2`. Offline checks passed; native placement/collision pending. OpeningV2 avoids cutting the Kotel; raised deck clears it. No source-proven western gate through the continuous sanctuary wall. Do not cut protected geometry to invent one.
- Resident logic: `ResidentCrowdRuntime.h` plus `SourceAssets\runtime-review\resident-crowd`, `Scripts\check_resident_crowd.py`. Portable runtime passed 520 debug and 520 release checks. New `MikdashResidentCharacter.h/.cpp` adapter was NOT yet compiled or bound to a live crowd. It needs reviewed routes and shared runtime ownership. Personality/state code alone is not an embodied population.
- Audio: `SourceAssets\soundscape-review\frozen-files.json`, `Scripts\build_soundscape_review.py`. New CC0 wind was not auditioned or adopted. User strongly rejected the old synthesized noise/birds/banging loop; keep that muted. Do not replace it with unauditioned wind. Existing recorded footsteps remain available.
- Incense: `SourceAssets\IncenseRepairV4` (locate exact folder), `Scripts\create_incense_smoke_study.py`, `inspect_incense_particles.py`. V4 offline repair/source checks only; native appearance pending. Do not claim correct timed ketores/maleh ashan yet.
- Controls: `SourceAssets\runtime-review\control-audit`; passive bounded native_control_probe.py prepared. Potential P-key fallthrough in preparation UI remains to confirm physically. Do not claim it fixed from a source check.
- Research, service routes and source-confidence records are in SourceAssets and publishing `unreal\Research`. Preserve distinction between textual evidence, disputed interpretation and authored future scenario. Temple Institute references guide original vessel/garment studies, not exact copied assets or proven future design. Immersion must remain modest. No speculative rule should be presented as definitive halacha.

## Unbuilt root C++ changes

`Plugins\MikdashRuntime\Source\MikdashRuntime\MikdashRuntime.Build.cs` adds NavigationSystem for the new resident adapter.
`Private\MikdashPlayerController.cpp` extends existing footstep routing: FutureMountV1/Terrain is soft ground; exact platform surface is hard ground. New standalone MikdashSurfaceAudioRouting.h was not wired into the controller. Compile and test before publishing these changes.

## Release sequence

1. Inspect live Unreal/UAT processes and unsaved editor state. Run native jobs SERIAL. Gracefully close the editor before a full compile/package; preserve unsaved work, do not blindly kill the user's editor.
2. Checkpoint the combined map, place the ready keruvim, pilgrims, bus and Kotel overlay with guarded transforms/materials; add other work only if it can be verified without derailing release. Save and reopen, record exact contents and omissions.
3. Run `Scripts\audit_future_mount_routes.py` against the combined map. Prepared source plan: `SourceAssets\FutureMountV1\route-review\route-source-plan.json`. Audit source obstacles and actual render/collision data; do not remove streets/buildings just because they overlap a guessed route. Check ground walking, gates/stairs, chamber visibility, pawn collisions and safe mouse release. Tests must be bounded and auto-stop.
4. Render and inspect wide and close views, including sanctuary/vessels, Kotel and pilgrims. Loading barrier must precede warmup; earlier gray first views were a loading issue. Gold-polish variant is not accepted. Cloud/wind serialization does not establish visible wind response; generic foliage does not automatically deform.
5. Set startup/game/cook maps to the accepted scene, compile the plugin, and FRESH COOK/package to a new `C:\Mikdash\Builds\Walkthrough-06` (verify folder not already in use). Walkthrough-05 used skipcook from 04 and does not contain current integration. Do not call it the latest complete build.
6. Launch the newly packaged executable and test actual spawn, walking, looking, pause/mouse release, representative routes, visuals and audio. Record logs/screenshots and limitations. A successful compile or count is not runtime acceptance.
7. Copy explicit reviewed source/assets/receipts to publishing clone, verify, commit and push. Include source-only work with clear status, omit generated caches and reference exports. Deliver exact executable path and a verified authorized sharing method; GitHub source availability is not proof of a downloadable working package.
8. Leave a concise release note of incorporated and pending features. Stop expansion after the handoff. Codex heartbeat `mikdash-three-minute-progress` should be paused by Codex when release handoff finishes; Claude may not have that app tool. Do not create duplicate polling.

## Native invocation and pitfalls

Commandlet: engine `Engine\Binaries\Win64\UnrealEditor-Cmd.exe`, project path, `-run=pythonscript`, `-script=C:/.../helper.py`, `-unattended`, `-nullrhi`, `-abslog=C:/.../unique.log`. GeometryScript helpers need `-EnablePlugins=GeometryScripting`. Bundled Python: `Engine\Binaries\ThirdParty\Python3\Win64\python.exe`.

Packaging entry: `Engine\Build\BatchFiles\RunUAT.bat BuildCookRun -project=<uproject> -noP4 -platform=Win64 -clientconfig=Development -build -cook -stage -pak -archive -archivedirectory=<new folder> -utf8output -unattended`. Check installed project prerequisites and prior packaging logs; do not use skipcook.

- Imported architecture names include `architecture_` prefix. Inspect exact mesh/component paths and bounds, not labels alone.
- Commandlet `spawn_actor_from_object` returned None: use StaticMeshActor class and checked set_static_mesh.
- Geometry is often baked at identity transforms. Component bounds matter.
- Compare numeric transform fields, not str(Transform), which includes memory addresses. Cache actor snapshots once; do not recalculate every actor for every comparison.
- External checkpoint filenames passed to new_map_from_template silently produced current/empty worlds. Use proper package paths and assert actor count; preserve checkpoints.
- Four FutureMount terrain cut assets passed native source color/normal preservation and save/reopen. Actual render LOD and collision-route acceptance remain separate.
- Skeletal FBX export crashes with NullRHI; do not repeat. SK_Mannequin is a skeleton, SKM_Manny_Simple is a mesh.
- Original Courtyard map hash at integration: `d0417e294388e603facc66ab279693ec01464ace5b25da4ea129601dfd08f56c`.

## Communication

User wants action, frequent concise updates and honest results. Do not ask for approvals already covered by project authorization. Do not restart many agents: prior research/art workers were told to stop for budget consolidation. Never equate an imported asset, a mocked test or a polished plan with a finished visible feature.

## Native audit attempt after initial handoff (2026-09-07 15:28 UTC)

The combined-map audit was executed using UnrealEditor-Cmd with NullRHI. It exited 1 at audit_future_mount_routes.py line 182: get_editor_subsystem(StaticMeshEditorSubsystem) returned None, so has_vertex_colors could not run. This is an audit environment/API failure, not proof of broken mesh colors. Map bytes were verified unchanged. Receipt: SourceAssets/FutureMountV1/route-review/native-route-audit-20260907T152823Z.json. Full log: C:\Mikdash\Working-5.8\Release-Route-Audit-01.log. The process exited; do not wait on it. Use an appropriate native editor context or implement a supported commandlet color check without weakening acceptance. Two GUI editor processes (38704 and 39764) were observed before this run; recheck live state before any build or close operation.

## Audit recovery (2026-09-07 15:30 UTC)

Running the same audit in a dedicated hidden UnrealEditor process with -ExecutePythonScript and -nullrhi succeeded; StaticMeshEditorSubsystem was available. The helper quit its own editor in finally, and that process exited. Receipt: SourceAssets/FutureMountV1/route-review/native-route-audit-20260907T153006Z.json; log C:\Mikdash\Working-5.8\Release-Route-Audit-02.log. All four terrain render triangle counts match (429,566,480,454), all report vertex colors, and map bytes remained unchanged. ALL 128 floor/static-clearance probes require review. This is not a walking pass: investigate trace/physics-world readiness and actual collision in bounded PIE before interpreting these results as geometry defects. No map fixes were made by this audit.

## Claude takeover boundary

User asked to hand off to Claude. All three root subagents were confirmed completed, and Codex heartbeat mikdash-three-minute-progress was paused. Do not infer a finished release from this handoff. Final asynchronous PIE floor helper C:\Mikdash\Working-5.8\run-release-pie-floor-probe.py was launched in a dedicated hidden editor PID 44744, but the editor requested exit before a receipt appeared; no PIE result is accepted. Log: C:\Mikdash\Working-5.8\Release-PIE-Floor-01.log. -ExecutePythonScript may close the editor when a script returns before registered tick callbacks finish; use the established persistent editor execution mechanism for asynchronous PIE tests. Recheck that PID has exited before launching another native job. User GUI editors must be preserved. Codex is yielding project ownership to Claude and will not start further work unless asked.
