# Handoff to Claude Fable — overnight takeover after Walkthrough-09

Prepared by Codex/Astra on 7 September 2026 local time (8 September UTC). Read this file, then AGENTS.md, then RELEASE-NOTE-Walkthrough-09.md. This handoff supersedes the starting-state and unapplied-step claims in HANDOFF-FOR-GPT-ASTRA.md and the older HANDOFF-FOR-CLAUDE-CODE.md. Historical receipts remain evidence, not instructions to rerun old creators.

## User intent and overnight outcome

Take over active development. The user values the actual visuals of the Third Beis HaMikdash and surroundings most. They want a convincing cinematic arrival, inspired by film lighting/production and a little Breath of the Wild exploration, while preserving the measured Yechezkel reconstruction and distinguishing source evidence from future-world interpretation. They also requested purposeful people, correct keilim/garments, modest preparation learning, scheduled ketores/maaleh ashan, a white-dove exploration option, and a downloadable game.

The download preview is now delivered. Spend overnight effort on visibly better integrated work, not repeated packaging of unchanged assets or more plans without implementation. Aim for a fresh Walkthrough-10 candidate with compared images, bounded movement tests, packaged controls tested where possible, an honest release note, and verified source committed/pushed. This is an intended next candidate name: confirm it is unused before creating it. Do not promise AAA completion overnight.

Work autonomously on authorized reversible development. Use your available agents for concrete independent tasks with explicit ownership; keep native Unreal edits, renders, tests and cooks SERIAL on this 16 GB machine. Do not keep agents busy with redundant tasks just to inflate their count. End with a concise account of what visibly improved, what was tested, where the latest build is, what remains incomplete, and commit hashes. Do not claim background overnight work is running unless your own session actually stays active.

## Exact locations and current state

- Editable project: `C:\Mikdash\Working-5.8\MikdashCourtyardV3\MikdashCourtyardV3.uproject`.
- Current map: `/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough`.
- Map file: `C:\Mikdash\Working-5.8\MikdashCourtyardV3\Content\MikdashV3\IntegratedReviewV2\Maps\Walkthrough.umap`.
- Rechecked map SHA-256 at handoff: `2edb00afb822cb44e1f528fc03f5783d15d0e7a4faf043456b0060b7d96fc9bd`.
- Engine: `C:\Program Files\Epic Games\UE_5.8`, installed engine verified as 5.8.2.
- Bundled Python: `C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe`.
- Toolchain: MSVC 14.44, Windows SDK 26100, .NET Framework SDK 4.8. Do not restart toolchain installation without a new concrete error.
- Publishing clone: `C:\Mikdash\GitHub\3rdbhmk`, branch `main`, public origin `ShmuelSokol/3rdbhmk`. Unreal project is under `unreal\MikdashCourtyardV3`; retain unrelated `web/` and `distribution/` work.
- Immutable original: `C:\Mikdash\Mikdash-Windows-Transfer\EditorProject\MikdashCourtyardV3`. Never modify it.
- Checkpoints: `C:\Mikdash\Working-5.8\ReviewCheckpoints`.
- Latest packaged build: `C:\Mikdash\Builds\Walkthrough-09\Windows`.
- Launch root bootstrap: `C:\Mikdash\Builds\Walkthrough-09\Windows\MikdashCourtyardV3.exe`.
- Actual game child: `C:\Mikdash\Builds\Walkthrough-09\Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe`, SHA-256 `b20685fc7021cab1cb2728576db025d03404f7515880016f5fa862729de87c11`.
- Latest pre-handoff source/history: `9038e673` game/dove/residents; `bcc8e53d` ZIP distribution; `0438eb3b` successful public download verification. The commit containing this handoff will be newer; use git log, not a hardcoded HEAD assumption.
- At handoff process inventory: bootstrap PID 12764 and game child PID 43340 still existed; no UnrealEditor/UnrealBuildTool/AutomationTool process found. Requery before any process action; these are observations, not permission to kill them. Codex's three agents finished and have no pending writes.
- Publishing tree had an untracked generated `distribution/windows/__pycache__/`; do not stage it or confuse it with application source. Cleanup was not needed for release.

## Work already completed — do not rerun the former three unapplied steps

1. **Kotel occlusion repaired:** scoped duplicate city-wall cuts adopted and visually inspected. The original assets/protected maps were preserved. Receipt `SourceAssets/kotel-detail/KotelStoneV1/occlusion-fix-20260907T212114614138Z.json`.
2. **Lighting applied and regression repaired:** initial EV8 minimum made Kodesh nearly black; EV0 minimum / EV14 maximum restored readability. Aron and relief are visible. Heikhal rear-wall highlights remain too bright. Captures `SourceAssets/visual-review/release-capture-20260907T214622Z`.
3. **Context materials applied:** 4,627 assignments across city/terrain/etc., saved/reopened with zero recorded errors. Receipts in `SourceAssets/materials-context/native-apply-20260907T215013179583Z.json` and `native-apply-20260907T215118571170Z.json`. Shared StaticMesh dependencies changed: unchanged donor map bytes do not imply unchanged appearance.
4. **Bus slots repaired:** 991 effective material-slot mismatches across 13 meshes corrected; ivory/teal body and glazing inspected in `SourceAssets/visual-review/release-capture-20260907T220851Z`. Tire contact/boarding/transit motion remain unverified.
5. **User Kotel photos applied:** four noncolliding cleaned-photo panels adopted; six procedural overlays hidden. Receipt `SourceAssets/kotel-detail/photo-adoption-20260907T225252321046Z.json`; reviewed pictures in `SourceAssets/visual-review/release-capture-20260907T224816Z`. The surface is still soft, flat, warm and stretched. Photo application is not faithful stone reconstruction.
6. **White-dove mode implemented:** menu or F, WASD movement, Space/Ctrl altitude, Shift boost, F returns to original walker/departure point. Stylized original bird model with flapping wings and following camera. Walking pawn retains collision while parked. Initial-menu takeoff waits for grounding up to 3 real-time seconds, then reports failure rather than silently doing nothing. Smaller body collider can permit wing clipping.
7. **Five residents integrated:** authored route-and-goal pilot, with startup enabled only on the configured population actor. All five moved to destinations in PIE, but only 62–68 cm. This is not a lively population or persistent individual minds.
8. **Fresh Walkthrough-09 cooked:** game/editor compilation and fresh UAT succeeded, exit 0, 230 seconds, 8,022 packages; saved map hash unchanged. Log `C:\Mikdash\Working-5.8\RuntimeBuild-09\uat.log`. This cook contains the above work.

## Tests passed versus still pending

Passed current-map native tests:
- Entrance/platform route: `SourceAssets/IntegratedReviewV2/release-walk-20260907T225836Z.json`.
- Sanctuary round trip: `SourceAssets/IntegratedReviewV2/release-sanctuary-walk-20260907T230012Z.json`.
- Dove/residents: `SourceAssets/runtime-review/dove-flight/native-flight-20260907T231003184270Z.json`: 23.30 m forward, 15.94 m ascent, pause drift 0, exact same-walker return/position with collision retained; all five residents arrived; PIE ended; map bytes unchanged.
- Fresh packaged build receipt: `SourceAssets/runtime-review/walkthrough-09/build-receipt.json`.

**First verification task:** inspect the existing Walkthrough-09 standalone game and complete Start, mouse look, ground routes, menu/preparation pause/resume, menu dove takeoff, F/Space/Ctrl/Shift and return, mute, quit, representative lighting and performance checks. The last standalone launch reached the menu but a Windows Firewall security prompt covered it. This was not dismissed by the agent. `SourceAssets/runtime-review/walkthrough-09/launch-receipt.json` honestly leaves interactive checks incomplete. Follow your own platform's UI/security permissions; do not bypass or weaken Windows protections. If user interaction is required and they are asleep, record the blocker and continue independent development. Do not relabel PIE evidence as packaged keyboard testing.

No sustained audio audition is accepted. The user rejected the previous repetitive noise/birds/banging loop; muted or disabled audio is not a completed soundscape.

## Overnight priorities and division of work

Use new isolated review namespaces and checkpointed adoption into the integrated map. Assign file ownership before any parallel work. A practical split is three independent asset/source tasks plus one integrator who alone owns native jobs/map changes. Use actual available concurrency; there is no requirement or authorization to buy compute.

1. **Visual baseline and sanctuary balance first.** Capture comparable current exterior/Kotel/Heikhal/Kodesh views. Fix blown highlights without making the Aron chamber dark again. Reduce obvious repetition, seams and synthetic material response. Compare at walking height and while entering/exiting interiors. Preserve measured dimensions and vessel placements unless source evidence justifies a scoped correction.
2. **Kotel and coherent arrival route.** Preserve the recognizable existing Western Wall/plaza in the selected future scenario. Improve stone scale/aspect, per-stone color/roughness, recessed joints and raking-light relief using the existing photos as reference. Avoid stretching a single flat photo across the wall; do not reintroduce hidden duplicate layers, occluding slabs or sinusoidal bands. Review plaza-to-platform stairs/access and city/terrain seams, roads and bus contact. No trees on the Mount; surrounding vegetation should follow available geographical evidence. Modern buses/rail and future access are authored interpretation, not established future facts. The large EnclosureV1 intersects the modern city and remains held for a design decision: do not bulldoze the city to force it in.
3. **Dove and people presentation.** Improve the bird silhouette, wing motion, following camera and near-obstacle behavior. Expand one resident's useful route/visible purpose with credible walking, obstacle recovery, pause behavior and a readable goal; then reuse a proven pattern carefully. Do not claim every character has a sophisticated mind merely from assigning a string or short waypoint.
4. **Keilim/source fidelity and service if capacity remains.** Review actual current assets before rebuilding missing items: ShulchanV2 (12 loaves, supports/28 rods/bazichin), IncenseAltarV2, patterned paroches, FriezeV2, Aron with separate poles already exist from Claude's prior work. The current Titus-style menorah differs from the user's Temple Institute request. Check the book's keruvim body interpretation and table height against sources. Keep private Temple Institute reference photos private and preserve licenses. A finite timed ordinary ketores event is preferable to perpetual decorative smoke, but only after the plume and officiant/location behavior are visually verified; Yom Kippur is separate. Preparation must remain modest, source-aware and not imply immersion alone resolves every impurity/entry condition.
5. **Integrate, fresh-cook, verify and ship a coherent candidate.** Stop expanding scope early enough to complete integration/testing. Do not leave many isolated studies presented as a playable improvement. Keep the public 09 release intact; use a new tag/build for a tested improvement and carry explicit limitations.

## Visual references and research — reuse what exists

All following source paths are relative to the editable project unless stated otherwise:
- `SourceAssets/visual-reference-handoff/gold-palm-cherub-relief.png` and `gold-relief-prompt.txt` are present. Derived height/normal/pattern images are in `SourceAssets/relief-images/derived/`. These are existing reference assets; do not install Stable Diffusion merely because a historical handoff omitted images.
- `SourceAssets/visual-review/` contains actual native screenshots and receipts. Use the timestamps above for current evidence; older renders can show defects that are already fixed.
- Kotel source/import/adoption work is in `SourceAssets/kotel-detail/`, scripts `Scripts/release_kotel_photo_surface.py` and `Scripts/release_adopt_kotel_photo.py`. Private family photo originals are not release assets. Existing cleaned derivatives are intended for the wall, with their reconstruction limitations recorded.
- No standalone lion/crow image was confirmed in this handoff's filename inventory. Do not claim to possess or have transferred such an image without locating and inspecting it. The confirmed gold palm/keruv relief image above is available now.
- Source hierarchy/gaps: `SourceAssets/research/book-scene-requirements-20260907.md`, `SourceAssets/vessels-review/book-keilim-review-20260907.md`, and local book exports (private/gitignored).
- Research dossiers: `C:\Mikdash\GitHub\3rdbhmk\unreal\Research\halacha-and-service.md`, `people-and-city.md`, `ketores-service-and-smoke.md` and other files in that directory.
- `BUILDOUT-STATUS.md` preserves the broader backlog but its older status bullets are historical; the current-state override and this handoff supersede them.

## Concrete verification commands and constraints

Read the scripts before invocation. These are dedicated processes, not instructions to manipulate a user's open editor. Run one native job at a time; use fresh timestamped logs and ensure watchdog/teardown succeeded. Commands below are examples for PowerShell after verifying no conflicting engine job. No commands have been started by this handoff.

```powershell
$project = 'C:\Mikdash\Working-5.8\MikdashCourtyardV3\MikdashCourtyardV3.uproject'
$editor = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$map = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'
# Dedicated real-RHI capture, then inspect its PNGs, not only its receipt.
& $editor $project $map '-ExecCmds=py C:/Mikdash/Working-5.8/run-release-capture-views.py' -unattended -NoSplash
# Execute the following independently, after the preceding editor exits.
$env:MIKDASH_WALK_QUIT_EDITOR = '1'
& $editor $project $map '-ExecCmds=py C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_walk_probe.py' -unattended -NoSplash
& $editor $project $map '-ExecCmds=py C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_sanctuary_walk_probe.py' -unattended -NoSplash
& $editor $project $map '-ExecCmds=py C:/Mikdash/Working-5.8/run-astra-dove-flight-probe.py' -unattended -NoSplash
```

The capture runner and dove runner exist at the paths above. Walk probes are bounded, and dove probe has a 100-second watchdog plus teardown. Real RHI is needed for meaningful rendered comparison; commandlet/NullRHI traces are not collision proof. Add explicit fresh -abslog paths in the actual run. Capture cameras for multipart buses must derive from actual saved actors, not obsolete BUS_XY/BUS_YAW candidates.

Fresh package to a new unused archive directory via installed `Engine\Build\BatchFiles\RunUAT.bat`, `BuildCookRun -project=<project> -noP4 -platform=Win64 -clientconfig=Development -build -cook -map=<map> -stage -pak -iostore -archive -archivedirectory=<new folder> -utf8output -unattended`, with a single cooker if needed for memory. Run foreground through PowerShell/cmd, not Git Bash. No -skipcook for releases. Never kill the user's editor to make the command succeed.

Preserve failed receipts. Reopen and read back native changes. Checkpoints/hashes cover maps AND changed dependency assets. Stage explicit reviewed files only in the publishing clone. Run relevant tests before commit/push; do not sweep untracked files. Never force-push or skip hooks.

5.8 lessons: fog bool is `enable_volumetric_fog`; enum values do not support int(enum); material setters can return False even when readback succeeds; texture Coordinates pin is `UVs`; actor root component via get_editor_property; get_pawn is not Python reflected here (use GameplayStatics.get_player_pawn); reacquire actors after map reload; cache the full actor inventory once and key by native name; do not make quadratic inventory calls. Re-running creators into existing asset namespaces is prohibited. More detail in AGENTS.md.

## Public distribution is already working

Release: https://github.com/ShmuelSokol/3rdbhmk/releases/tag/walkthrough-09-preview

Two ordinary ZIPs, extracted into exactly the same root, then launch root MikdashCourtyardV3.exe:
- `Mikdash-Walkthrough-09-App.zip`: 173147367 bytes; SHA-256 `8a9a0d6f1db9d022181e2fcdde3e0a477beedbdcbd638e2fb25b1159b8b89911`.
- `Mikdash-Walkthrough-09-Data.zip`: 2104623696 bytes; SHA-256 `32d4a90fe09e88dadf3c46679f85601363a9c6c420865f74b5affcffb6a939c3`.
- Data ZIP contains exactly `MikdashCourtyardV3/Content/Paks/MikdashCourtyardV3-Windows.ucas`, no wrapper. App ZIP has the other files at the same root.
- Both entire public downloads were fetched without authentication, checked against expected archive hashes, extracted, and every one of the 49 original runtime files independently compared with the original Windows build. Distribution has 55 files total, including credits/notices. This does not establish standalone control/visual acceptance.
- Verified receipts and reproducible validator: `C:\Mikdash\GitHub\3rdbhmk\distribution\windows\`, especially `public-download-receipt.json`, `verify_download.py`, `SHA256SUMS.txt` and `RELEASE-NOTES.md`.
- User instructions: `C:\Mikdash\GitHub\3rdbhmk\unreal\DOWNLOAD.md`; root README links the release.
- Local final archives: `C:\Mikdash\Builds\Walkthrough-09-Download`. Re-downloaded/test-extracted copy: `C:\Mikdash\Builds\Walkthrough-09-Public-Download-Test\ExtractedGame`.
- GitHub assets must each be below 2 GiB; the full single ZIP exceeded that limit. Do not upload it or split raw files without clear assembly instructions.
- UAT omitted loose credits from staging; package preparation explicitly supplied CREDITS.txt, NOTICES.txt and ThirdPartyNotices. Preserve these and original third-party license obligations in future builds. Never distribute private photo originals, source books, project Saved logs, PDBs or secrets.
- A trial C# downloader was blocked as virus/potentially unwanted software by Windows during execution. It was NOT allowed, bypassed, signed or published. Rejected source is preserved outside the clone at `C:\Mikdash\Builds\Walkthrough-09-Download\RejectedInstallerSource`. Do not attempt to evade the detection or tell users to disable protections. Ordinary ZIP distribution needs no custom installer.
- Existing .NET/Visual Studio/Unreal tools are not required on the player's PC. The x64 Visual C++ runtime may be needed on a clean PC; the current docs link Microsoft's official installer. No paid cloud host, streaming server or continuously running developer PC is needed for this download approach.

## Morning acceptance report

Give the user the latest launch path and any new verified download link; 3–6 actual before/after images; brief features/defects fixed; tests with receipts; measured performance if tested; unresolved source/visual/runtime issues; and pushed commit hashes. State separately if packaging, Windows prompt interaction, external download, or any route was not tested. Preserve Walkthrough-09 as the known published preview.
