# Handoff to Claude Fable — 8 September 2026

## Start here

Read this file, then `AGENTS.md`, `TAKEOVER-STATUS-20260908.md`, and `INTEGRATION-QUEUE.md` in this project. The newest dated entries supersede older history. The queue still has stale unchecked steps: inspect receipts and the current scene before repeating any placement.

The verified implementation checkpoint is **150c9be32952bf47c78f76aac18c71187573f938**, pushed to `ShmuelSokol/3rdbhmk` main. This handoff is a subsequent documentation change. There were no active Unreal/editor/build/shader jobs at the stopping point. Worker deliverables are saved; no worker is mid-write. A stale `halacha_research` pending-init entry was not doing active research. Do not assume old agent status messages represent current activity.

Shmuel wants a convincing, source-grounded Third Beis HaMikdash experience people can download and play. He prioritizes visuals, the keilim, believable people and surroundings. He explicitly approved the **48 cm amah**, requested contemporary Old City Jewish Quarter paving, and corrected the crowd: people usually travel in groups, occasionally alone. Keep authored future details distinct from sourced measurements and halachic claims. He wants initiative and progress without repeated permission questions, but also asked for this safe handoff. Do not promise film-production quality from a compile or a screenshot.

## Exact locations

- Working project: `C:\Mikdash\Working-5.8\MikdashCourtyardV3`
- Project file: `C:\Mikdash\Working-5.8\MikdashCourtyardV3\MikdashCourtyardV3.uproject`
- Unreal 5.8.2: `C:\Program Files\Epic Games\UE_5.8`
- Bundled Python: `C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe`
- Publishing clone: `C:\Mikdash\GitHub\3rdbhmk`; project prefix there is `unreal\MikdashCourtyardV3`.
- Immutable original: `C:\Mikdash\Mikdash-Windows-Transfer\EditorProject\MikdashCourtyardV3`. Never modify it.
- External checkpoints: `C:\Mikdash\Working-5.8\ReviewCheckpoints`
- External logs and coordinator runners: `C:\Mikdash\Working-5.8`

**Current main/default/startup/cook map:**
`/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough`

Its `.umap` SHA-256 is `8e78923f5ffb76c044693f6c74faaedb64648698945bb0ba927f3395be7f21c5`.

**Isolated 48 cm candidate, NOT promoted:**
`/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough`

Its `.umap` SHA-256 is `8dc55f79b3dbcfe0ba7a15c41b3fb2da5be108766aab5a2cf7a9aae46f8a8f89`.

Map hashes do not cover shared material dependencies. Nine shared material instances were deliberately repaired after those map saves; their hashes are in the Nanite receipts below.

## What was actually completed and verified

### Paving and daylight

Main has Jerusalem-style limestone paving on the Mount platform plus **57 exact courtyard/gateway floor slabs**. The slab shader puts the pattern on top faces and plain limestone on thin edges; golden sanctuary floors were excluded. The authored texture derives from Shmuel's paving reference; his original family photograph remains private. It is not a photographic scan. The 500 cm world-space tile is a physical dimension, independent of the amah. Joints are still albedo-only, with visible repetition.

Materials: `MaterialReview/JerusalemPavingV2/M_JerusalemPaving_500cm` and `MaterialReview/JerusalemFloorSlabsV1/M_JerusalemFloorSlabs_500cm`, below `/Game/MikdashV3/`.

Main daylight was reviewed in three real PIE before/after pairs, then saved/reopened: sun **6500 K / 30,000 lux**, unchanged rotation approximately pitch -30 / yaw -160; skylight **1.3**. Exposure settings stayed unchanged. This modestly reduces the orange cast; it does **not** fix all bright/clipped surfaces. Candidate still has the older 5000 K / skylight 1.0 lighting.

### Visitor groups

`MikdashCrowdField` now seeds stable parties of **2–6**, with about **15% individuals** as authored tuning. Parties share pace and direction, slow/wait for companions, and preserve physical spacing. Bounded spatial hashing and static capsule sweeps guard movement. Groups are refused atomically when placement is unsafe. They no longer teleport across zone boundaries to regroup.

Main native test: **200 people in 54 parties + 36 individuals**, 236 seeded of 240 allocated; one four-person party refused. Ten samples across 9.145 game seconds showed 92 group members moving more than 50 cm and minimum sampled spacing 80.04 cm. **13 parties were paused** at the end.

Candidate native test: **201 people in 51 parties + 35 individuals**, again 236 seeded / 4 refused; 98 group members moved more than 50 cm; minimum sampled spacing 80.03 cm; **19 parties paused**.

These are first-pass background crowd behaviors, not complete navigation. A blocked party can remain safely paused; it has no reliable detour/recovery solver. The maximum observed 123 sweeps is a sampled-frame count, not an every-frame measurement or a 60 fps result. Separate skeletal residents retain their own behavior; they were not converted into these groups.

Details and preserved failures: `SourceAssets/runtime-review/crowd-field/GROUP-NATIVE-20260908.md` and `GROUP-BEHAVIOR.md`. Do not relabel earlier failed receipts: one was a Python result-shape mismatch; another used the old all-240-seeded assertion. Current group tests require exact allocation accounting and explicitly label `partial_safe_refusal`.

### 48 cm candidate

Already saved/reopened: 2,633 architecture actors; 218 veneer/frieze panels; 12 door parts; eight Temple Institute vessel-study parts; eleven Aron/menorah parts; a Selected48 scene descriptor; PlayerStart; 18 tour markers; and all 58 paving overrides. Do not replay those applied stages.

Runtime frame, save identity, tour and population adapters compile. Two Temple crowd zones convert by .96; four geographic context zones remain metric. Physical people/capsules/eye heights/hardware offsets remain physical centimetres. Candidate walking start is approximately `[2016, 0, 578.00019]`.

Frontend, intro-to-dove flight, ascent, pause, walking return, tour/codex API interactions, and same-layout save/load were exercised in actual PIE. Save tests used isolated slots, deliberately displaced the pawn 50 cm, then restored with 0 cm error. Original saves remained unchanged. This does not establish physical keyboard coverage, all routes, cross-layout save recovery, navmesh, doorway clearance or vessel fit.

**24 resident profiles decode geometrically, but only 15 spawn physically in the candidate.** Nine capsule refusals: Yoav, Miryam, Tzipporah, Gad, Techiya, Pinchas, Uriel, Rivka, Nechemya. The other population actor's old extended route refuses unclassified converted points and remains stopped. Diagnose real capsule hits; do not identify blockers from a whole-building AABB. See `SourceAssets/scale-review/AMAH48-NATIVE-20260908.md` and `AMAH48-RUNTIME-DEPENDENCIES.md`.

### Nanite material repair

Nine PBR material instances now persist explicit Nanite usage overrides: CedarPlanks, GoldFloor, GoldHammered, LimestoneAshlar, LimestoneTrim, Marble, PavingSlabs, Plaster, RoughStone (`MI_PBR_` prefix).

They were checkpointed, saved, compiled and verified in a different process. Parent, texture parameters, other usage flags, maps/configs and unrelated PBR assets stayed unchanged. A subsequent real scene log had zero missing/auto-set Nanite usage messages. Broad bright/clipped surfaces remain; compatibility repair is not final visual acceptance.

Helper: `Scripts/release_nanite_instance_usage.py`. Do not blindly rerun apply; use the successful receipt and its fresh-process verify mode. Historical base-material-only helper was preserved.

## Verification evidence

Full gate: **8/8**, **30/30 standalone math suites**, actual UnrealBuildTool compiled/linked six actions in **54.92 seconds**. Group math alone has 44,707 checks. Final quick gate **6/6**, 191 Python scripts, 44 specs, 669 receipts. Sixty explicit published files matched the working copies; C++ hashes stayed unchanged since the full build. Historical failures remain warnings, not erased evidence.

External logs:
- `Astra-Groups-Fixed-FullGate-20260908.log`, `verify-ubt-64wqzaoc.log`
- `Astra-Groups-Final-QuickGate-20260908.log`
- `Astra-Groups-Main03-20260908.log`
- `Astra-Groups-Candidate48-01-20260908.log`
- `Astra-NaniteInstances-01-20260908.log`, `Astra-NaniteInstances-Verify01-20260908.log`

Key project receipts:
- `SourceAssets/runtime-review/frontend-flight/native-frontend-flight-20260908T173130367390Z.json` — main groups.
- Same folder, `native-frontend-flight-20260908T180131188281Z.json` — candidate groups/frame/render.
- `SourceAssets/perf-review/nanite-instance-usage-20260908T173857999122Z.json` — nine-instance apply.
- Same folder, `nanite-instance-usage-20260908T175937249147Z.json` — different-process verification.
- `SourceAssets/lighting-review/native-reviewed-daylight-20260908T171157734314Z.json` — main daylight adoption.

Actual images: `SourceAssets/visual-review/runtime-diagnostic-20260908T173221Z.png` (main) and `runtime-diagnostic-20260908T180225Z.png` (candidate). Inspect them: paving and groups are present, but figures are simple and large surfaces remain overbright. They are evidence, not marketing renders.

## Approved paroches — do not lose this asset

Shmuel explicitly approved **V15** in the separate design task. That task relayed the approval; Astra acknowledged it. **V15 is NOT integrated yet.** The old red curtain in the scene is not this artwork.

Approved file on this same computer:
`C:\Users\shmue\Documents\Codex\2026-09-08\what-color-is-the-paroches-of\output\paroches\third-temple-handwoven-v15.png`

Approved PNG SHA-256: `f48ccf055c8f051ccf9bc2702c003d84d1b74eeda54231d2be9ced157232df89`.

Related design note beside it: `PRIVATE-REVIEW-v15.md`; its preapproval wording was superseded by the explicit approval. The approved PNG was checked to exist when writing this handoff. Read the actual image before importing; do not substitute an earlier version or start another image-generation project.

Design: one central keruv between two palms, upward arched wings, youthful human face on the back of the shared lion skull, one lion ear/no extra human ear, feathers conceal feet, blue/purple/scarlet/ivory woven fabric, subtle central blood detail. These exact artistic choices are authored, not certified reconstruction. Target curtain size at 48 cm amah: **336 × 288 cm**. Use a fresh namespace, checkpoint and whole-panel mapping; the old curtain mesh has per-strip UVs.

Earlier V1/V7/V9 candidates remain held and must not be adopted or published. Preserve the old local `release_paroches_fabric.py`/ParochesFabricV1 work rather than assuming it is the approved implementation.

## Prepared work worth preserving

- **PilgrimRigV3:** nine variants exist as source, but have not been natively imported. Current residents share a V2 body. Read `SourceAssets/characters-review/PILGRIM-V3-NEXT.md`, `PilgrimRigV3/REVIEW-HELPER.md`, and `Scripts/release_pilgrim_v3_review.py` plus its spec. `run()` is the offline check. A guarded first native batch is `run(import_assets=True, variants=['V3_Pilgrim_Man_Standard'])`. It requires fresh variant folders, new compatible skeleton/clips and rest-pose proof. No unsafe V2 retargeting. Recommended visual scales .84–1.04 belong on skeletal visual components, never the whole capsule or the amah scale. These variants remain stylized, not film-quality humans.
- **Water:** existing water is around 26 cm below intact floors. Real host openings and collision work precede full adoption.
- **Audio:** the old white-noise/birds/banging loop was rejected. Prepared soundscape work needs listening and event-wiring review; do not silently re-enable the rejected loop.
- **MetaHuman:** Core Data is installed. First Epic cloud auto-rig still needs the editor GUI; do not report missing data again.
- **Source confidence:** the codex has 76 entries (33 certain, 33 disputed, 10 authored). Do not turn authored details into sourced assertions.

## Suggested next bounded wave

1. Recheck current hashes/process ownership and run the gate. Do not rebuild before workers have frozen their source.
2. In parallel, assign distinct ownership for candidate collision diagnosis, approved V15 import preparation, and V3 character review preparation. Coordinator alone owns native jobs. Use at most three workers plus coordinator in this Codex environment; never launch a large wave just to fill an agent count.
3. Resolve the nine resident spawn refusals and old population route, group obstacle recovery, and remaining 48 cm system dependencies. Preserve metric city context. Integrate approved V15 and reviewed character variants only after their native checks.
4. Review lighting from multiple walking-height views, then audio and actual routes; measure performance. Do not promote the candidate just because it compiles.
5. Only after the complete candidate passes, update the default/cook map deliberately, fresh-cook to a new release folder, launch the packaged child executable and test controls/walking/flight/save/quit. Publish a release note stating remaining limitations and an actual download.

No fresh package was produced in this checkpoint. The existing family download is older than this working scene. The estimate given to Shmuel was roughly 1–2 focused workdays for a dependable preview, conditional on collision/package checks; the complete cinematic scope is weeks to months. Treat this as an estimate, not a promised finish date.

## Commands and rules that prevent lost work

PowerShell gate from the working project:

```powershell
Set-Location 'C:\Mikdash\Working-5.8\MikdashCourtyardV3'
Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe' 'Scripts\verify.py'
# After C++ changes, with no editor/cook/other UBT running:
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe' 'Scripts\verify.py' --build
```

- Native editor, commandlet, UBT and cook jobs are **strictly serial**. Never kill the user's editor. A shell launch returning exit 0 does not prove the GUI has exited: check PID, log and receipt.
- Native changes require checkpoints and before/after hashes. Never regenerate original architecture or rerun creators over existing namespaces. Preserve partial failed imports and resume only from unapplied steps.
- Existing bounded probe: `Scripts/release_frontend_probe_entry.py`, with `-Candidate48` for the isolated map, `-TestVisitorGroups`, `-TestIntegratedSystems`, `-TestTour`, `-DirectIntroFlight`, `-TakeDiagnosticStill`, `-DiagnosticFloors`. Copy the exact unique save-slot override pattern from the successful log or probe source; **never use normal user save slots**. Each run needs a unique `AstraProbe_...` prefix and unique `-abslog`.
- Line traces in NullRHI/commandlets are not physical evidence. Use actual PIE. Whole-part AABBs of hollow unions and large terrain tiles are false-blocker traps; inspect component/source boxes and real capsule hits.
- Python optional-success wrappers may return the output struct/tuple directly or None, rather than returning a separate bool. Read receipts with `utf-8-sig`. Sibling imports from `runpy` wrappers need `Scripts` on `sys.path`.
- UE5.8 material instances have their own Nanite overrides. `set_material_usage_override`, `update_material_instance`, targeted `get_statistics`, save, then fresh-process readback are required. Sampler counts are not texture counts.
- UBT globs `Source/`; standalone tests belong in `Plugins/MikdashRuntime/Tests/`. Do not put test executables or test source under the module Source tree.
- Cooks: foreground PowerShell, `cmd /c RunUAT.bat`, one cooker process; never Git Bash or with a GUI editor/Live Coding open. Do not reuse an old cook. Hash/test the child under `Binaries\Win64`, not the bootstrap executable at archive root.
- Copy only reviewed files into the publishing clone, verify them, stage **explicit filenames**, commit and push, report the hash. Never `git add .`, `git add -A`, force-push or bypass hooks. `publish-astra-groups.py` and `astra-groups-files.json` outside the project record this checkpoint's 60-file set; do not blindly replay that list after unrelated changes.
- Unrelated local clone changes were deliberately left alone: the two `codex-entries.json` copies, `Scripts/release_paroches_fabric.py`, `SourceAssets/sanctuary-detail/ParochesFabricV1/`, `tests.json`, and `distribution/windows/__pycache__/`. Some are held artwork/work; others generated files. Inspect rather than sweeping them into a commit.
- Never publish private family photos, Temple Institute reference photos, book exports, GPL reference models, vendored tools, Binaries/Intermediate/Saved/DDC or checkpoints. For mobile review, use a verified public HTTPS image/file link; a Windows path alone will not render on Shmuel's phone.
