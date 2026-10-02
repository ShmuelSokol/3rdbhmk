# Haram threshold sides â€” isolated study, native execution pending

Only preparation is complete. No Unreal, candidate asset, render, cook or production
adoption is implied by the offline receipt. Raw logs and images remain local.

Owner constraint: preserve the approved paving on every upward horizontal top.
Do not assign ashlar to the whole threshold mesh. The proposed candidate retains
all 180 native source triangles, their exact ordered positions/winding and corner
attributes. Only polygon groups/material slots change: top = original
M_PrecinctPlaza_Paving; vertical sides and downward bottoms = existing
MI_PrecinctPlaza_Ashlar. No geometry, transform, collision or main-map edit.

## Local API decision

UE5.8 local source checked:

- Engine/Classes/Engine/StaticMesh.h:1813â€“1822 exposes GetStaticMeshDescription and
  BuildFromStaticMeshDescriptions. MeshDescriptionBase.h:475 exposes
  SetPolygonPolygonGroup; StaticMeshDescription.h:61 exposes material slot names.
- Engine/Private/StaticMesh.cpp:8885â€“8911 returns the cached source description
  and builds from supplied descriptions. Use a separate unsaved working duplicate
  so the rebuild never overwrites the description it is reading.
- StaticMesh.cpp:8922 sets NeverStream; restore its original value on the candidate.
  Use the editor build (fast_build=False), no new simple collision; preserve and
  compare BodySetup geometry, complex-collision policy, build/Nanite settings,
  render/fallback triangles and both sections' collision/shadow flags.
- GeometryScript MeshAssetFunctions and MeshMaterialFunctions provide source/render
  extraction and material-ID readback. This study uses those read-only. It does NOT
  round-trip geometry through DynamicMesh or reimport the OBJ.
- AssetTools.cpp:2161â€“2220 can save duplicates if SCC is enabled. The wrapper disables
  SCC and the native script refuses enabled SCC before duplication. Save is explicit
  and limited to SM_ThresholdSides in a fresh isolated run namespace.

Python exposure, section rebuild and GPU appearance remain native validation gates.
Every unexpected API shape or mismatch must fail; do not weaken exact checks to
make a run pass. Source winding is Unreal clockwise: upward top has negative
cross-product Z. Offline validation also checks the independent authored OBJ normals.

The initial full-editor threshold-sides01 failed its unchanged 4 GiB guard before
script execution: 4,334,333,952 bytes peak, no native.json, all 48 protected hashes
unchanged. Preserve that failure. Initialized StaticMeshEditorSubsystem is absent
in commandlets here; the five audited getters use no initialized member state.
query-source-evidence.json pins local engine source and exact method/guard lines.

The revised wrapper uses hidden UnrealEditor-Cmd with run=pythonscript, Entry,
AllowCommandletRendering, -nop4, disabled SCC and GeometryScripting. ONE quoted
argument line is passed. Commandlet execution returns normally and propagates
Python failures; no quit_editor call. CDO use is limited to five audited getters;
all candidate mutation remains on the existing mesh/description methods.

Preflight02 failed before queries because the commandlet positional Entry argument
did not load a map. Its receipt/log did not record the actual initial world name;
do not retrospectively invent that value. Failure and protected hashes are retained.
The coordinator-authorized correction explicitly calls LoadMap with the hardcoded
literal /Engine/Maps/Entry once at startup, then requires that exact editor world,
matching non-null return and no PIE. Initial world/package/object path, initial game
world, load return and final world are recorded (initial/load return also logged).
Startup in /Game or PIE is rejected before load. No dynamic path or project map load
is allowed. Existing Kohen CombinedMotion permits a transient world; it is NOT a
precedent for explicitly loading Entry. PythonScriptCommandlet parses -script only.

Read-only Preflight requires exact Entry/no PIE, one LOD/section, nonnegative CDO
counts matching direct BodySetup box/sphere/sphyl/convex counts, strictly TRUE
collision/shadow with numeric 1 readbacks, typed build settings/unit scale/positive
lightmap resolution and the pinned 180 source triangles. It creates no candidate,
actor, save or capture. LogUtils/StaticMeshEditorSubsystem warnings or errors reject
the run. Native query availability and memory fit remain unproven until it passes.

## Coordinator commands â€” serial, NOT launched during preparation

From the project directory, with the native slot coordinated and free:

```powershell
& ./Scripts/run_haram_threshold_study.ps1 -RunId threshold-sides07 -Mode Preflight -CoordinatorNativeRun
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed; retain receipts and stop' }
# Coordinator reviews Preflight before authorizing these later steps:
& ./Scripts/run_haram_threshold_study.ps1 -RunId threshold-sides07 -Mode Build -SaveCandidate -CoordinatorNativeRun
if ($LASTEXITCODE -ne 0) { throw 'Build failed; retain receipts and stop' }
& ./Scripts/run_haram_threshold_study.ps1 -RunId threshold-sides07 -Mode Verify -CoordinatorNativeRun
if ($LASTEXITCODE -ne 0) { throw 'Fresh verification failed; retain receipts and stop' }
```

Run in PowerShell 7. A used RunId/mode cannot be overwritten; choose a fresh ID for
a retry. Omitting SaveCandidate gives an unsaved build/capture study, after which
Verify is intentionally unavailable. Only the explicit coordinator invocation may
create the isolated native candidate:
`/Game/MikdashV3/MaterialReview/HaramThresholdSidesV1/<RunId>/SM_ThresholdSides`.
The working duplicate is never saved. Nothing binds the candidate into a map.
Build/Verify require the SAME run's successful native AND wrapper preflight within
one hour. Three executable-script hashes, manifest/evidence hashes, protected input
hashes, native receipt hash and clean log hash must still match. The offline wrapper
checks before launch; native checks repeat before candidate operations. Each process
repeats the positive query probe. Changed/stale inputs need a fresh run/preflight.
Preflight never automatically starts Build or any other native process.

Guards: 6 GiB free commit at start, 4 GiB owned-editor private cap, 2 GiB reserve,
300-second timeout (maximum 600), one shader worker and bounded asset compilation.
Memory fit is not claimed before measurement. Refuse other native/UBT/UAT workers;
the study lock only serializes this harness, so coordinator ownership is still needed.
Only Engine Entry is allowed. No project level load API exists in the study script.

## Proof and review

source-audit.json pins four owning assets and the OBJ, records all 180 triangles and
the side/top policy, and lists protected maps/material families. Native runs hash
those paths immediately before/after and protect the bounded project asset dependency
closure; the wrapper repeats preservation checks after exit or owned-child termination.
Prepared map hashes are historical observations, not permission to overwrite another
worker's later work. Native source inputs must still match accepted pins.

The build uses the original asset for baseline and a fresh duplicate for candidate.
It verifies exact source geometry/winding, UVs/normals/colors, top material identity,
side/bottom section IDs, build/Nanite/collision policy, full 180-triangle render
geometry and collision/shadow flags. Verify repeats this in a fresh process against
the saved candidate hash. Collision cook bytes/GUIDs are not expected to be identical
between distinct assets; shape/triangles/policy must be identical.

Nine 960x720 images per process: baseline/candidate/baseline-return at the accepted
Mughrabi camera, a closer oblique edge camera and a top view. Both meshes remain at
identity, with the unchanged AccessV4 stair mesh for context; lighting/exposure and
camera are held fixed per trio. There is no terrain/wall or production lighting load.
Review that the edge no longer streaks, horizontal top appearance remains consistent,
stair/apron contact is unchanged, and baseline-return restores the baseline. Image
existence or native success is NOT visual acceptance. No packaged/state-transition
acceptance is claimed.

## Offline checks

`python -B Scripts/haram_threshold_study_common.py` checks the pinned OBJ, classification
against authored normals, and rejects a moved corner or reversed winding. It writes
nothing. The one-time `--prepare` creates source-audit.json and refuses overwrite.
Full project verification is separate from these narrow checks; no UBT is required
or authorized by this study preparation.

## Build03 reflection correction / fresh Preflight04

Preflight03 passed; Build03 failed before duplication because the Python class is
`unreal.SourceControl`, as SourceControlHelpers.h:244 explicitly declares via
ScriptName. Reports for 01/02/03 remain untouched. The disabled-SCC guard now calls
`SourceControl.is_enabled()` and requires exactly False. Preflight04 checks this
query, the precise clone/save/mesh-description callables used by Build, and reads
the original 180-triangle MeshDescription without invoking mutation methods.
Callable availability does not establish mutation signatures or Build behavior.

Cleanup permits an empty namespace on failure before saving. It always rejects
foreign files and requires the candidate on declared save, successful SaveCandidate,
or Verify. A sole authorized candidate left by a failed save is retained as evidence;
it does not turn that run into success. The wrapper and 6/4/2 guards are unchanged.
Fresh matching Preflight04 is required before Build04.

## Build04 correction / Preflight05

Build04 failed before save on VisibleAnywhere imported_material_slot_name. Reports
remain preserved. StaticMesh.cpp:8898 forwards fast_build=False to Build(true);
StaticMeshBuilder.cpp:1619 maps polygon-group imported names through
GetMaterialIndexFromImportedMaterialSlotName, not the displayed MaterialSlotName.
The candidate now receives two writable StaticMaterial records, then SetMaterial
(StaticMesh.cpp:10189-10227) initializes empty imported names with unique asset names.
Both actual imported names are read back, required nonempty/distinct, and assigned
to the working MeshDescription polygon groups before the same slow build. No
constructor guess, import_text, or read-only bypass is used. Preflight checks
set_material availability only. Remaining reflected property writes were reviewed
against headers; fingerprints/evidence are in query-source-evidence.json.

Both wrapper WaitForExit calls are bounded to 5000ms. Cleanup errors do not skip
protected-file checks or receipt writing. Unconfirmed exit records nativeSlotFree=false
and native-slot-blocked.json blocks future study invocations, also under the lock.
Coordinator must confirm process exit before removing that marker. OS lock release
is not native slot clearance. Memory/start/reserve limits remain 6/4/2 GiB.

Render proof now compares normal/UV/color corner attributes with the same cyclic-order
counter as source proof. Simple BodySetup physical material is read back before/after
and must match. Effective per-triangle physical material remains unproven: section
material IDs may change collision surface behavior. No cooked Chaos equivalence or
production actor slot-1 override proof is claimed; adoption remains a later review.

## Build05 memory failure / mapping profile06

05 stopped at 4,473,094,144 private bytes (4.166 GiB), with 2,984,337,408 bytes
free commit. Failed accepted-baseline.png remains zero bytes and is preserved.
The log shows static-mesh builds, actor/capture creation, FloatRGBA scene textures,
and 50 PSO hitches. Startup recorded dynamic GI=1, reflection method=1, VSM=1.
There is no native.json and no saved candidate. These observations locate the
failure near first capture but do not attribute bytes to a specific subsystem.
Kohen commandlet scripts/wrapper contain no GI/reflection/VSM disabling flags;
skeletal success does not prove the same footprint for Nanite static meshes.

06 adds only process-local RendererSettings overrides: dynamic GI=0, reflection
method=0, VSM=0. Readbacks are required in Preflight, Build/Verify and each camera;
r.Nanite must remain 1. The same profile applies to baseline/candidate/return.
Direct sun, 960x720 output, cameras, materials, textures, normals, geometry and
proof gates are unchanged. No texture-quality reduction, nullRHI split, production
config edit, or cap increase. This is mapping review, not production-lighting
acceptance. Fit remains unproven until coordinator measurement under 6/4/2 guards.

## Preflight06 parser failure / revision07

ConfigCacheIni.cpp:2317-2384 tokenizes each -ini:Engine argument, then each setting
must independently contain [Section]:Key. Missing section separators are skipped
(2370-2374), explaining GI=0 but reflections/VSM=1 in 06. The legacy comma form
also has an explicit quoted-value warning. Use one complete -ini:Engine:[Section]:Key=Value
argument per override. Revision07 uses six separate complete arguments: the three
existing DevOptions.Shaders settings (999,999,False) and the three renderer zeros.
DevOptions previously repeated its section correctly; its values/intent are unchanged.
All six remain within the single quoted PowerShell argument-line string. Profile
readbacks still fail closed; no production config edit. Preserve 06 failure reports.

## Render07 pixel audit: export padding, not demonstrated stale rendering

The preserved Build07 and Verify07 files decode to identical corresponding RGBA
pixels. Baseline-return is exactly baseline at every camera. Top baseline/candidate/
return are exactly equal. Accepted baseline/candidate differ in 25,199 RGB channels;
oblique differs in 111,836. All PNG chunk CRCs and recorded whole-file hashes are
checked by Scripts/audit_haram_threshold_png.py; pixel-audit07.json records results.
The accepted baseline on disk contains the full assembly, not an empty frame.

Concrete UE5.8 export defect: ImageUtils.cpp:1281 serializes compressed allocation
size (GetAllocatedSize), not payload Num. These files have trailing allocation bytes
after IEND. Compare decoded pixels or CRC-valid PNG through IEND, not file length or
whole-file hash alone. Keep original receipts and PNGs untouched; do not patch engine.
CaptureScene already calls SendAllEndOfFrameUpdates; FinishLoadingBeforeScreenshot
forces texture streaming and StreamAllResources. Current evidence does not justify
attributing these file differences to cached components/mips. Native scripts remain
unchanged pending coordinator review. No cooked/adoption acceptance is inferred.
Future capture convergence/nonempty gates should use decoded pixels; no nonzero
pixel difference tolerance is needed for 07's baseline-return/top comparisons.

## Final export hardening and scoped visual review

Coordinator confirmed the clean accepted-pair contact sheet: both assemblies are
visible, baseline front stripe becomes candidate ashlar. Scoped visual acceptance
is in scoped-acceptance07.json, pinned to native07 receipts, clean manifest/pixel
audit and contact-sheet hashes. No cached-actor or warmup rewrite is justified.
Original07 PNGs remain local evidence only; do not publish allocation tails.

Future exports go to fresh *.local-export.png staging files. haram_threshold_png.py
checks format, every chunk CRC, bounded zlib decoding and all scanline filters,
then exclusive-creates the final capture using exact bytes through IEND. Only the
sanitized file hash/pixel hash enters the receipt; staging is removed on success.
Interrupted/failed staging files remain local-only and never enter the publish list.
The helper hash is included in future preflight revision matching. Existing native07
receipts retain their original revision and remain valid historical evidence.

publish-allowlist.json names every proposed code/audit/clean-image/JSON file. Nothing
has been published. Raw PNGs, logs, scratch files and all candidate uassets are
excluded. Candidate publication remains held pending coordinator boundaries.
No native08 is required to establish clean07 payload equivalence; future sanitizer
integration has offline tests, not a new native run.

Native-source provenance: native-source07.zip contains exactly the five files named
by Build07 revisionHashes. Every entry was reconstructed/copied in memory and its
SHA256 matched the historical receipt before archiving; every ZIP entry was then
read back and matched again. native-source07-manifest.json pins archive and receipt
hashes. Active source was not overwritten. This snapshot preserves pre-sanitizer
history; use the current hardened scripts for future runs. The new PNG helper is
included in current revision_hashes, so future preflight cannot miss its changes.
