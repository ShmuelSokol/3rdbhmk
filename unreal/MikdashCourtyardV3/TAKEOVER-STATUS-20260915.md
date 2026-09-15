# Astra takeover checkpoint — 15 September 2026
## Verified Kotel edge collision checkpoint — 15 September, 19:17 UTC

Latest native-tested copy:
`C:/Mikdash/Builds/Checkpoint-edgecollision01-20260915/Windows/MikdashCourtyardV3.exe`.
Child SHA256 `9860531e11415b304c185479b18ab0ac08a34032feba61c565ab19ad00baa435`.
The prior contextpatch01, edgeprobe01 and original cp24 copies are preserved.
This copy has the same six cp24 base containers and the same verified CityWall-only
three-file patch. It has NOT received the full13 material candidate.

The retaining face now blocks Pawn queries when its source terrain is visible.
It retains the same841 triangles,2523 vertices,959 deck transforms and material;
no reflected fields were added. Native ON190805233Z blocks the player at edge106
(four exact closure-body capsule hits; grounded feet -982.4cm); OFF190930828Z
reproduces the fall with a valid deck start. Headless state runs191037452Z and
191154185Z passed Modern/Yechezkel/Overlay/Modern-again and normal exit. Enabled
collision modes are1/0/1/1; the hidden state has no live body. Both stair replays
191326473Z/191423070Z reached all three actual waypoints, zero stuck events,
finished grounded on the upper deck. All20 source maps and all9 archive containers
were verified unchanged. `KotelCutClosureV1/collision-acceptance.json` records it.

Verification: first full diagnostic gate11/11 including32/32 math; final collision
build retry10/10, Editor and Game both compiled/linked without warnings. The first
collision link failure is preserved in collision-build-attempt1.json. All raw logs
stay local. A localized edge test is NOT whole-perimeter or GPU acceptance. No new
render was performed for this collision-only binary; its visual geometry is unchanged.

Next work: full13 material A/B renders when the existing8.75GiB free-commit GPU guard
permits; preserve the verified CityWall-only files transactionally. Do not lower the
GPU guard, retry full cooks under16GiB, or restart/change AnyDesk/security services.
The three-minute heartbeat remains ACTIVE; this is an intermediate checkpoint.
## Headless family-patch checkpoint — 15 September, 18:33 UTC

The full 13-material candidate mounted at Order203 and completed the real
three-waypoint Kotel stair replay in NullRHI. The transaction restored all three
verified CityWall-only patch files afterward; all six base containers, the child
executable and all 20 source maps remain hash-identical. Receipt:
`SourceAssets/context-review/ContextCoursingV2/family-headless-20260915T183251292Z.json`.
This proves loading and the tested movement route, NOT rendered material quality.
The playable copy remains CityWall-only; the other family materials await GPU A/B.

The physics-only constrained probe has its own measured budget: 6.5 GiB initial
headroom, 2.5 GiB child cap, 3.5 GiB reserve. This run peaked at about 1.12 GiB.
It stops its owned child after completed diagnostic events and does not claim a
normal game exit. GPU guards and the 16 GiB full-cook guard are unchanged.
The first ON/OFF edge runs (184111081Z and 184210020Z) are inconclusive: the diagnostic switched to MODERN and immediately dropped the pawn while the plaza collision stayed disabled for its 2.5-second transition. Exact start placement is inside deck instance106, not a plan gap. Both runs fell before steering; neither establishes a production floor or retaining-wall collision defect. The diagnostic-only instant-state setup fix compiled with gate11/11 and math32/32 for edgeprobe01 (child6deeb50d...). Corrected ON185132894Z/OFF185225086Z both land on the deck, then cross the edge and fall below terrain. This establishes a localized collision gap. Pawn-only collision for the generated retaining face and a four-state headless readback are now in preparation; native acceptance pending.

## Current material-patch checkpoint — 15 September, 18:15 UTC

Latest pushed commit before this batch is **20ae3fe4** (Kotel runtime closure).
The new tested playable copy is:
`C:/Mikdash/Builds/Checkpoint-contextpatch01-20260915/Windows/MikdashCourtyardV3.exe`.
It preserves cp24 base containers and the current runtime child
`3aee6ac4d129e6327a7077d59d83557a50c10ecb731aa94744e1eb612d02f087`.
It now also carries the **native-tested CityWall-master-only asset patch**.
The earlier roofruntime copy and original cp24 remain intact.

**Proved:** CityWall close-up A/B/A, all three runs normal exit with four state
readbacks each, identical actual cameras and all 20 source maps unchanged.
Root inspected vertical courses before, horizontal courses with the patch, and
vertical courses restored after removing it. The same verified patch bytes were
then copied back. See `ContextCoursingV2/citywall-patch-aba.json` and
`current-playable-patch.json` under `SourceAssets/context-review`.
The patch mounts at Order203 and is 198,999 bytes across its three files.
The restored A differs from initial A by 0.576/255 mean channel value in the
fixed wall ROI, versus 4.757/255 for the patch. These are repeatability metrics,
not production-quality scores. Flat relief and repeated texture remain visible.

**Also completed, NOT mounted or visually accepted:** all three corrected
masters plus their ten actual MIC descendants cooked successfully in a small,
isolated filesystem cook. Nineteen packages including six texture dependencies,
52 outputs, zero errors/warnings, 2.462 GiB aggregate private peak. The resulting
13-package candidate patch is 793,964 bytes. Its cook and container receipts are
`ContextCoursingV2/cook-families-20260915T180845.json` and
`containers-families-20260915T181141.json`. Actual bundle/recipe directory:
`C:/Mikdash/Working-5.8/ContextPatchStudies/AllCoursingFamilies-20260915T180845462Z-51ac6460/ContainerRecipeV1-20260915T181041867043Z-a4dde6b3`.
Never substitute it for the verified CityWall-only patch without runtime tests.

Next native step: capture a no-patch K2 baseline in the separate contextpatch
copy, then test the 13-package bundle at the same camera and the source-derived
CityFacade camera. Preserve existing patch files outside Content/Paks before
switching; these bundles deliberately have the same stem and must not coexist.
Use `Test-KotelClosureRuntime.ps1 -Constrained` for the four-state photo probe.
It requires 8.75 GiB free commit, keeps 1.5 GiB reserve and caps the owned game at
7 GiB; High/77%, 960x540 viewport, synchronous loading. A passed run came within
3.26 MiB of the cap: do not call that ample margin. The latest K2 preflight
refused at approximately 8.62 GiB, launching nothing. Do not lower the guard or
repeat full-scene cooks. Continue non-native work until headroom recovers.

The Entry dependency audit found 10 direct instances among 792 registered MICs,
including both ExteriorFixesV1 children missed by the earlier offline inventory.
All exposed base override flags were false/zero; private static resources remain
unknown. Include the audited instances in the cook rather than inferring no
static permutation. `Test-ContextMaterialCook.ps1 -AllCoursingFamilies -Constrained
-DependencyAuditReceipt <dependency-audit-20260915T174543Z-34988.json>` and the
offline `prepare_context_iostore_patch.py` now guard the exact 13-source set.
No maps, global containers, asset registries or shared shader libraries are
replaced. Raw logs and cooked binaries stay local, outside Git.

No restart, UAC, paging, security-service, network or AnyDesk changes were made.
The Kotel closure still has no collision; direct edge-walking remains a separate
open item. This is a verified local patch checkpoint, not a full new game release.

## Current verified Kotel visual repair — 15 September, 17:29 UTC

The local playable copy now includes the Kotel cut closure, alongside the prior
rooftop and photo-body repairs. Launcher:
`C:\Mikdash\Builds\Checkpoint-roofruntime01-20260915\Windows\MikdashCourtyardV3.exe`.
Current child SHA256:
`3aee6ac4d129e6327a7077d59d83557a50c10ecb731aa94744e1eb612d02f087`.

Native enabled/disabled four-state probes passed and images were inspected: the
missing strip under the Jewish Quarter becomes a stone retaining surface in the
Kotel view. Modern/Overlay show it; Yechezkel hides it. All 959 deck transforms,
841 closure triangles and normals read back correctly. Both stair replays reached
all three waypoints, zero stuck events, grounded on the upper deck. Final gate10/10:
Editor compiled/linked; Game hash remained the exact native-tested binary.
See `SourceAssets/context-review/KotelCutClosureV1/runtime-acceptance.json`.
All20 maps and all6 original/test-copy base containers are hash-unchanged.

Important limits: the added face is an authored VISUAL treatment with NoCollision;
direct edge walking and a physical barrier remain unverified. The tested stair
route is unchanged. This is still cp24 cooked content plus a replacement executable,
not a full recook/public release; the saved ContextCoursingV2 materials are absent.
Next priorities: probe the new boundary directly, then deliver the saved horizontal
stone courses through a small tested asset patch. The source-supported but UNTESTED
recipe/inventory is `ContextCoursingV2/asset-patch-plan.md`. Do not run a full cook
at unchanged headroom. Facade shape/detail and terrain-edge steps still need work.

The initial incompatible child and both watchdog stops are preserved. Five new
reflected transient fields were removed; all70 existing property declarations/order
match the last working code. Weak closure references use actor OwnedComponents for
GC retention. Do not reintroduce schema changes into an older unversioned cook.
The 1280x720 GPU probe measured7.36GiB private peak and1.80GiB minimum free commit.
Its measured startup required a1.25GiB reserve/8GiB child cap; Entry/full-cook guards
remain unchanged. No restart, administrator-consent bypass or security-service change.

## In progress — 15 September, 16:49 UTC

17:08 UTC update: Editor/Game compiled, but the first packaged trial failed before
BeginPlay during unversioned AActor serialization. New reflected transient fields
were inserted ahead of existing Enclosure properties, shifting cooked schema
indices. Runtime-only schema-preserving correction is underway. The test archive
has been restored to the previous working child `c1f56f30...` recorded below;
failed binary is checkpointed under `ReviewCheckpoints/KotelRuntime-20260915T1658`.
Native failure receipt: `KotelCutClosureV1/runtime-20260915T170601943Z.json`.

Integrating the verified Kotel excavation closure as a guarded transient runtime mesh,
without saving maps or cooking. Code and generated data are being prepared; this is
NOT yet compiled or present in the playable copy. The original cp24 archive remains
untouched. The current test child is still the photo-fix SHA recorded below.

The closure follows only the exact KotelPlazaCutV3 terrain component: Modern/Overlay
visible, Yechezkel hidden. `KotelPlazaCutTwin` alone is ambiguous because the deck
actor shares it. Validate full mesh identity, identity world transform and all 959
deck transforms. Use the loaded enclosure's PlazaAshlarMaterial; cp24's cooked parent
is MacroV3 although the active instance now points at MacroV4. No collision/navigation
on this visual shell; original deck, treads, protected Kotel wall collision stay intact.
Separate native four-state photo and existing three-waypoint stair probes are prepared.

## Current photo fix and Kotel study — 15 September, 16:31 UTC

Photo-mode camera obstruction is now fixed in the local test copy. Its current game
child SHA256 is `c1f56f30d0eacc819e9ba7f6f8681e5ddcf9cd199121a5d25d0ffd29ee0f22fc`.
The launcher path below is unchanged. Both Editor/Game compiled and linked; the
production-policy GPU probe `CameraObstructionV1/probe-20260915T161445204Z.json`
passed 18 phases including repeated Enter, active Enter and both exits. Native pixels
were inspected: the rods are absent. Only the possessed player's skeletal
WorldSpaceRepresentation body is hidden while photographing. Original component
flags and pawn camera restore; other primitives and all 20 maps remain unchanged.
Earlier broad and single-component diagnostic A/Bs establish the body as the cause.
See `CameraObstructionV1/production-acceptance.json`. This retains the rooftop fix
and existing cp24 cooked assets; it still is not a full recook or public release.

The Kotel Entry-only A/B/A now passes the cavity-facing visual test:
`KotelCutClosureV1/native-study-20260915T162720Z-4144.json`. The one-sided magenta
closure fills the blue gap; hiding it restores the gap. All production assets and
maps remain unchanged. The first B frame exposed incorrect native triangle facing
and remains rejected. The import now reverses canonical indices only, preserving
positions and cavity normals. Next: opposite-side culling, suitable vertical stone
material, collision and integration in a new namespace, then main-scene comparison.
No production Kotel repair has been placed yet. GPU editor startup uses more
memory than the earlier 2 GiB study target: measured peak was about 6.14 GiB private.
Current wrapper requires 9 GiB headroom and stops at 6.5 GiB private or below 2 GiB
free commit. This does not authorize a full-scene cook at unchanged headroom.

## Current verified state — 15 September, 15:40 UTC (supersedes older steps below)

The legacy floating rooftop equipment is repaired in a local playable test copy:
`C:\Mikdash\Builds\Checkpoint-roofruntime01-20260915\Windows\MikdashCourtyardV3.exe`.
This contains cp24 cooked content plus a newly compiled game child, SHA256
`f5e973d2693578c29da54163088aa340ec2e143dada07f897cf1a90c5ad4b2a6`.
It is NOT a full recook or a newly published download; the saved horizontal-coursing
material fix is still absent from these older cooked assets.

- Editor and Game compiled and linked successfully. Full math gate: 32/32; runtime
  roof tests: 9/9. Ten native state transitions passed twice, most recently
  `LegacyRoofRuntimeV1/packaged-20260915T153939Z.json`, with normal exit and all 20 map
  hashes unchanged. Originals remain intact; 1,263 tank/panel pairs disappear with
  their hidden building owners, leaving 4,744 pairs. Modern/Overlay restore all 6,007.
- Six native GPU frames were inspected. A1 confirms removal of the floating fixtures;
  elevated R1 confirms equipment returns on restored roofs in Modern and Overlay.
  See `SourceAssets/context-review/LegacyRoofRuntimeV1/visual-acceptance.json`.
- Missing Hebrew fonts were copied with their existing SIL OFL license into this
  test archive, and DefaultGame.ini now stages that folder for future cooks. Native
  logs find NotoSansHebrew. This does not certify translation, glyph coverage or RTL.
- Two corrected low-memory cook recipes still exhausted commit. Do not repeat full
  cooks on the same baseline. The helper now refuses below 16 GiB commit headroom;
  that is a conservative reserve, not a proven sufficient peak. Preserve AnyDesk,
  security services and the user's no-restart constraint.
- The existing three-minute continuation was PAUSED and is now confirmed ACTIVE,
  targeting this thread. No duplicate automation was created.

Next: verify a small native A/B for the missing Kotel excavation closure, documented
in `SourceAssets/context-review/KotelCutClosureV1/diagnosis.md`. Seven analytic
boundary samples reproduce the gap; native pixel attribution and a production repair
are still owed. Also isolate the rod crossing some camera views using the reversible
show-flag tests in `CameraObstructionV1/diagnosis.md`. Neither defect is fixed yet.
Use serial native jobs and low-memory studies; do not resume the older full-map
save recipe below at unchanged memory pressure.

Full filesystem access works. The active project is
`C:\Mikdash\Working-5.8\MikdashCourtyardV3`. The publication clone is
`C:\Mikdash\GitHub\3rdbhmk`. Claude's recent session entries are weekly-limit notices.
No editor, game, commandlet or cook remains running at this checkpoint.

Latest completed material work: horizontal coursing correction is applied to
M_Context_Building, M_Context_CityWall, and M_CityFacadeV1. Native before/after cube
renders were visually inspected, all three original masters saved, and a separate
fresh Unreal process verified the corrected code. All20 project maps remain unchanged.
See SourceAssets/context-review/ContextCoursingV2/review.md for evidence, backup,
rejected captures and limits. This change fits memory without a full map load.
It is not in the old packaged cp24/download; no new cook has been made.

## Verified and preserved

- Full gate: 11/11, including 32/32 standalone C++ math suites. Editor and Game UBT
  succeeded incrementally with zero compile actions; this was not a clean rebuild.
- Eight offline ownership/visibility guards pass. Exact frozen-geometry ownership:
  6,007 rooftop tank/panel pairs, 1,263 in hidden-building groups and 4,744 retained.
- Native read-only preflight verified all 12,014 original transforms. The persistent
  component trial created all four groups and passed counts, transform and render
  property checks BEFORE SAVE. It did not save the map.
- Candidate48 remains SHA256
  `3f986fb62e889db59b01d956d4ab63718f58366874e7e64b7ec4fd0fa62e3df1`.
  Backups and failed attempt receipts are in `..\ReviewCheckpoints\LegacyRoofZones-*`.
- User's new Old City photographs are private references outside the repository.
  See `SourceAssets/context-review/OldCityReferenceV2/reference-notes.md` for the
  street, paving, stonework, arches, ramps and lighting direction.

## Actual blocker, not a permissions issue

Windows reported 57.4 GB committed against a 68.6 GB limit before Unreal. Repeated
native attempts exhausted commit and reported that the paging file was too small.
All attempts left the saved map unchanged. No new cook or packaged build was made.
The user is connected from a phone through AnyDesk: DO NOT restart Windows, sign
out, or stop AnyDesk, networking or security services to recover memory. Clear
memory only through actions that preserve the active remote connection, then measure
again. Do not repeat identical crashing runs. The current shell lacks the privilege
needed for live page-file changes. See the live-memory recovery update below before
assuming that a paging change was applied.

`EditorActorSubsystem.duplicate_actor` crashed under the commandlet before save.
Full editor retries exceeded memory, even with an empty startup map and serialized
asset preparation. The CURRENT repair instead uses the original importer's persistent
ISM component creation, copies render settings, and verifies every transform.
Use the current code, not the older duplicate-actor recipe recorded in historical notes.

## Resume after memory is available

1. Read AGENTS.md, verify no competing native jobs, run `Scripts/verify.py --build`.
2. Run a fresh read-only native preflight with UnrealEditor-Cmd and
   `-run=pythonscript -script=<project>\Scripts\release_legacy_roof_zones.py`
   `-LegacyRoofPlan=<project>\SourceAssets\context-review\LegacyRoofZonesV1\legacy-roof-zones.json`
   `-unattended -nullrhi` and a unique absolute log path. Quote paths containing spaces.
3. If preflight passes, repeat with `-LegacyRoofApply`. It checkpoints before mutation.
   Require a successful save/reopen receipt and unchanged protected maps, not just
   process exit or pre-save groups. Preserve any failure evidence.
4. Run a SEPARATE fresh process with `-LegacyRoofVerify`. Compare its groups/settings
   to the successful apply receipt: this fresh process cannot infer original settings.
5. Run `Checkpoint-Build.ps1 -Label roofzones01`, including smoke test. Then run
   `Scripts/capture_city_facade.ps1 -Archive <new archive> -Label roofzones01 -Only A1 -IncludeRoofStateViews`.
   Inspect Yechezkel, Modern and Overlay frames for removal AND restoration.
6. Verify and explicitly publish the changed map plus its unpublished dependencies,
   without sweeping unrelated clone files or raw movie-frame folders.

The current city still needs major visual correction. cp24's six frames completed;
they were not interrupted. A1 has floating legacy fixtures, K2 has an apparent
ground opening/mirrored band, and a thin camera-relative object appears in several
views. Their causes/acceptance must be tested, not assumed fixed by this repair.

Publication at this checkpoint covers the tested repair scripts, plan, tests and notes.
Claude's prior unpublished assets/maps remain intact locally. The generic publish
helper would select roughly 64 GB including raw capture frames, so it was not run.
Two unrelated codex-entries.json edits and ParochesFabricV1 in the clone stay untouched.

## Live-memory recovery helper, 15 September

Stopped only the verified idle, weekly-limited Claude CLI process (PID 22832), freeing
about 0.9 GB of system commit. AnyDesk remained running. Page file still measured
49,152 MB, system commit limit 63.86 GiB, usage about 51.3 GiB before elevation.

`Scripts/Expand-PagefileLive.ps1` prepares a live-only increase of the existing C:
page file to 65,536 MB. It requires normal Windows administrator elevation; it does
not bypass UAC, change services or registry settings, or restart. It retains at least
30 GiB of disk space. `-CheckOnly` compiles the interop without making a change.
Automatic management remains in effect, so the size after a future boot is not pinned.

An ordinary RunAs request was launched, waited at Windows administrator consent,
then returned "The operation was canceled by the user." The helper never launched;
fresh readback still showed 49,152 MB. **The increase was not applied.** Do not infer
whether the user dismissed it or Windows timed it out from that error alone.
Read `C:\Mikdash\Working-5.8\MemoryRecovery\pagefile-*.json` and fresh Windows counters
for the outcome. Require both the allocated page-file size and live commit limit to
increase. A failed verification can follow an actual change if counters lag; inspect
the current state before any retry. Do not approve Windows security prompts by automation.

Verification: helper CheckOnly passed; project gate 7/7 and standalone math suites
32/32 passed. Log: LegacyRoofZonesV1/verify-pagefile-helper-20260915T134150Z.log.
