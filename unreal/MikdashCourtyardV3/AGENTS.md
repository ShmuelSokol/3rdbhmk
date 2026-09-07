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
finishes (7 veneers); heikhal keilim moved to the book positions: menorah `[-5330,350]` yaw 90, shulchan `[-5300,-350]`,
incense altar `[-5150,0]`, all Z 925; sixteen Aron parts at origin `[-6200,0,925]` yaw 90 with `RELEASE_Keruvim_1`
(all 100 slots gold) on the kaporet; five idle PilgrimRigV2 figures `RELEASE_Pilgrims_1..5` in the outer court around
`[5000,1180]` on floor Z 300; volumetric clouds; bound wind sequence; +1 stop exposure and interior histogram fields;
compiled MikdashRuntime controller (menu, pause/release, WASD, mouse look, mute persistence, footsteps, P-key fix in the
preparation lesson); 55 cm step height on BP_MikdashWalker. Actor count 7322 (7310 before the release edits).

## Imported but NOT placed

- TransitV2 bus + station (25 meshes). Candidate XY `[-23101.76, 36185.43]`, yaw `-60.0787`, has about 28 degrees of road
  crossfall by offline interpolation; no native trace hit in any commandlet process. Needs a PIE trace or another candidate
  and an explicit `bus_ground_z`. Station unset; no source-proven railway; aisle too narrow for the capsule.

## Source-only (authored, native import/placement NOT run)

- Doors/paroches: `Scripts\create_sanctuary_doors.py`, `SourceAssets\sanctuary-detail\DoorsParochesV1` (9 meshes).
  Paroches at X -5600, 350 x 300 cm; Kodesh doors 2 x (3.5 x 6 amot), modelled open inward.
- Reliefs: `Scripts\create_sanctuary_reliefs.py` makes a palm-only panel. The Yechezkel 41:18-20 keruv-with-two-faces panels
  were never modeled. Highest-priority art item.
- Mount access / Kotel opening: `create_mount_access.py`, `create_kotel_opening.py`, `mount-access\OpeningV2`.
  No source-proven western gate through the sanctuary wall; do not cut protected geometry.
- Resident crowd: `ResidentCrowdRuntime.h` (520/520 checks, debug and release) and the `MikdashResidentCharacter` adapter now
  COMPILE in Editor and Game Development targets, but nothing is bound to a live character. Not an embodied population.
- Audio: CC0 wind candidate not auditioned; synthesized pilot ambience stays autoActivate=false; footsteps live.
  `MikdashSurfaceAudioRouting.h` standalone-tested, not wired.
- Incense: `SourceAssets\IncenseRepairV4` offline only; V1-V3 studies fail visually (wisps at floor level).
- Keilim dimensions still the old studies: shulchan 76 cm high (book: 3 amot = 150), menorah 180 cm (book: 18 tefachim =
  150 at this project's 50 cm amah), incense altar 50 cm square (book: amah of 5 tefachim, about 41.7). Aron lacks luchot.
  Source review: `SourceAssets\vessels-review\book-keilim-review-20260907.md`.
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
