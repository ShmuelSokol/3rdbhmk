# Mikdash native Unreal project — current state (2026-09-07, after the Walkthrough-06 release work)

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
