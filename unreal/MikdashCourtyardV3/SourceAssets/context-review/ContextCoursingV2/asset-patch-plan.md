# Proposed small material cook and isolated cp24 overlay

Prepared 15 September 2026 by reading the installed UE 5.8.2 source and project
receipts. **UNTESTED: no small cook, container creation, mount, or packaged shader
acceptance has been performed for this route.** This is a proposed experiment,
not a release recipe already proved to work. It predicts no memory bound. The
recent full Candidate48 cooks exhausted Windows commit; this plan does not
recommend retrying them at the same headroom.

The saved ContextCoursingV2 edits affect these three masters:

- `/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_Building`
- `/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_CityWall`
- `/Game/MikdashV3/JerusalemContext/CityFacadeV1/Materials/M_CityFacadeV1`

Native apply/verify evidence is in `native-apply-20260915T140838780528Z.json` and
`native-verify-20260915T140917908097Z.json` beside this document. Those receipts
prove saved source assets, not patched cp24 content. Do not copy editor `.uasset`
files directly into a packaged game.

## Installed-source evidence

All engine paths below are relative to
`C:/Program Files/Epic Games/UE_5.8/Engine/Source/`. Line numbers refer to the
installed source inspected for this plan.

- `Editor/UnrealEd/Private/Commandlets/CookCommandlet.cpp:365–367` accepts
  `-Package=<long package name>` as well as `-Map=`, with repeated arguments or
  `+`-separated lists. No `-CookPackages` parser was found in this commandlet.
- The same file, lines 198–200 and 461–474, implements `-CookSinglePackage`:
  disable always-cook maps, default maps, game always-cook requests, input packages,
  global-shader saving and soft-reference traversal; retain hard dependencies.
  `-CookSinglePackageNoRefs` also skips hard references and is not the proposed
  first experiment. `-CookSkipRequests` additionally disables startup requests.
- Lines 334–335 accept `-OutputDir=`. Lines 425–427 implement `-SkipZenStore`.
  `Editor/UnrealEd/Private/CookOnTheFlyServer.cpp:7285–7321` documents the
  `[Platform]` output-directory token.
- `CookOnTheFlyServer.cpp:8625–8750` gates configured/always-cook maps behind the
  disabled request flags and still processes explicit package requests.
  Directory enumeration is gated by soft-reference traversal. Therefore use
  explicit `-Package`, not `-CookDir`, with this single-package recipe.
- `Editor/UnrealEd/Private/Cooker/ShaderLibraryCooking.cpp:73–76` uses
  `ProjectPackagingSettings.bShareMaterialShaderCode` to enable the cook's shader
  library. `Runtime/RenderCore/Private/ShaderMap.cpp:310–375` serializes a
  `bShareCode` flag per shader map; when false, it writes shader code into the
  package and loads `FShaderMapResource_InlineCode` at runtime. The source thus
  supports mixing new inline-code shader maps with the base game's shared ones.
- `Runtime/Core/Private/Misc/ConfigCacheIni.cpp:1716` and `2322–2324` document
  command-line configuration overrides of the form
  `-ini:Game:[Section]:Key=Value`.
- `Runtime/Engine/Private/Materials/MaterialInstance.cpp:2422` sets
  `bHasStaticPermutationResource` for instances with static parameters or
  overridden base properties. Its resource selection around lines 1390–1396
  can choose an instance shader resource instead of the base material's.
  Cooking only the masters is therefore insufficient without a descendant audit.
- `Developer/IoStoreUtilities/Private/IoStoreUtilities.cpp:9787–9844` accepts a
  commands file with per-container `-Output=`, `-ContainerName=`, and
  `-ResponseFile=`. Lines 10163–10265 cover global-container creation, cooked
  directory and package-store inputs. The supported UAT construction appears in
  `Programs/AutomationTool/Scripts/CopyBuildToStagingDirectory.Automation.cs:5328–5353`:
  fresh package-store manifest, cooked directory, commands file and script-object
  descriptor are supplied together for a filesystem cook.
- `Runtime/PakFile/Private/IPlatformFilePak.cpp:6039–6064` increases priority for
  `_P.pak`. Lines 6139–6171 mount its paired IoStore container and package-store
  records with the same priority. A pak containing legacy loose package files is
  not an established replacement for a package already present in cp24 IoStore.

## First cook experiment

Run only in a coordinator-owned serialized native slot with fresh commit
headroom and a bounded watchdog. Keep the existing default map configuration
unchanged. Use a unique output directory outside existing cooked/staged outputs.
Do not invoke the full-map BuildCookRun helper. The following is a proposed
argument vector, not an executed command; replace `<unique study>` with a new
absolute directory and capture a unique absolute log.

```text
"C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
"C:/Mikdash/Working-5.8/MikdashCourtyardV3/MikdashCourtyardV3.uproject"
-run=Cook -TargetPlatform=Windows
-Package=/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_CityWall
-CookSinglePackage -CookSkipRequests -SkipZenStore
-OutputDir="<unique study>/Cooked/[Platform]"
-ini:Game:[/Script/UnrealEd.ProjectPackagingSettings]:bShareMaterialShaderCode=False
-cookprocesscount=1 -unattended -abslog="<unique study>/cook.log"
```

Keep the same engine, project shader/compiler configuration and target shader
formats as the base. cp24's original cook log contains both PCD3D_SM5 and SM6
library work; do not assume that one visible D3D12 setting describes every
permutation required by the packaged build. Global-shader files are deliberately
not replaced by this experiment. No new renderer/global-shader feature belongs
in the patch.

The first pass asks for one master with its hard dependencies. Inspect the
requested/cooked package list and reject any project map request or unexpected
dependency expansion. A package list or successful shader compilation is not
visual acceptance. The source proves suppression of normal map request paths,
not that every project/plugin startup hook is incapable of loading a map.

Before expanding to all three masters, use asset-registry metadata to enumerate
their material-instance descendants without opening Candidate48. Include every
relevant descendant with a static permutation or overridden base property as
an explicit package request. Verify which instances the packaged scene actually
uses. Parent references point upward; cooking a master does not automatically
discover all its dependent instances. Audit dependencies against the base before
including them: the active project contains unrelated changes, so broadly
shipping every newly cooked dependency could introduce changes outside coursing.

## Container experiment

Preserve the original archive:
`C:/Mikdash/Builds/Checkpoint-cp24-20260911T124738Z`.
Also preserve the current playable runtime-fix copy. Make a separate experiment
copy and record executable/base-container hashes. No in-place edits or hardlink
writes to either retained archive.

Use the fresh isolated cook's own `packagestore.manifest` and `scriptobjects.bin`.
Do not borrow manifests from an interrupted full cook or from shared
`Saved/Cooked`. Their exact locations must be read from the successful output.
The source-supported IoStore invocation has this shape; it is not yet a tested
packaging recipe for these materials:

```text
"C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealPak.exe"
"C:/Mikdash/Working-5.8/MikdashCourtyardV3/MikdashCourtyardV3.uproject"
-CreateGlobalContainer="<unique study>/Containers/global.utoc"
-PackageStoreManifest="<fresh cook metadata>/packagestore.manifest"
-ScriptObjects="<fresh cook metadata>/scriptobjects.bin"
-CookedDirectory="<unique study>/Cooked/Windows"
-Commands="<unique study>/IoStoreCommands.txt" -platform=Windows -unattended
```

One commands-file row:

```text
-Output="<unique study>/Containers/ContextCoursingV2_1_P.utoc" -ContainerName=ContextCoursingV2_1_P -ResponseFile="<unique study>/IoStoreResponse.txt"
```

Construct the response file with the supported cooked source/destination mount
paths for the reviewed material packages and required cooked segments/bulk data.
Use UAT's response-file construction as authority rather than guessing extension
handling. Build a valid same-stem companion `.pak` through UnrealPak; retain only
appropriate non-package patch files there. The deployable unit is the complete
**`ContextCoursingV2_1_P.pak`, `.utoc`, `.ucas` bundle**, including any additional
data partitions if produced. Validate container listings and package IDs before
mounting. A partial bundle or a pak-only asset copy is not sufficient.

The generated `global.*` above belongs only to the isolated staging experiment.
**Do not deploy it. Do not replace cp24's `global.*`, shared project/global shader
libraries, or `AssetRegistry.bin` with partial-cook versions.** The original
registry already knows these existing package paths. Keep unchanged dependencies
in the base and ensure the new package metadata resolves against that base;
this compatibility still needs the native mount/load test.

cp24's original log
`C:/Mikdash/Working-5.8/Checkpoint-cp24-20260911T124738Z/uat.log:1420`
reports `Container signing - DISABLED`, and the inspected archive has no `.sig`
companion. Confirm actual base and patch encryption/signing flags before mount;
absence of signing is not proof that all contents are unencrypted. Do not print
or publish crypto-key values. This plan does not require changing signing policy.
The ordinary UAT differential-patch route expects release-version metadata;
cp24's recorded command did not create a named release version. Do not claim a
working `-GeneratePatch -BasedOnReleaseVersion` route from that receipt.

## Acceptance and limits

1. Keep the original archives and all production maps/assets hash-identical.
   Record command, engine version, source asset hashes, package census, actual
   cook/packaging outputs and peak process/system commit usage.
2. Launch the isolated packaged executable with baseline A, patch B, then patch
   removed A again, using identical camera, state, exposure and capture timing.
   Confirm logs show the distinct patch IoStore container mounted with priority.
3. Inspect actual rendered walls: corrected horizontal courses and normal detail,
   no default-material fallback, missing shader-resource/hash messages, checker
   surfaces or unrelated material changes. Test every affected master and
   material-instance family, including the Nanite paths the scene uses.
4. Confirm the restored A matches baseline and base hashes never changed. Keep
   failed experiment receipts and images. A valid container, zero cooker errors,
   shader compilation, or source-asset readback alone does not prove delivery.

Unresolved until tested: actual cook memory, descendant/permutation coverage,
package-store/script-object compatibility with retained cp24 containers, complete
dependency resolution, and visible packaged shader behavior. Inline shaders avoid
replacing a partial shared library in principle; the mixed inline/base-shared
route still requires native evidence before release.

## Offline dependency inventory, 15 September follow-up

This inventory uses existing recipes, saved native receipts, manifests and file
hashes only. No Unreal load or asset-registry job was run. It is **not exhaustive**
and does not assert that every listed instance owns a static shader permutation.
At least **three masters and eight named instances** belong in the dependency
audit. These are candidates to inspect, not an instruction to ship eleven files
blindly.

### M_Context_Building chains

The full master path is
`/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_Building`.
The following six direct children have native parent readback in
`SourceAssets/context-review/CityDetailV1/native-city-detail-candidate-20260909T223929718568Z.json`,
under `materials`. Their common folder is
`/Game/MikdashV3/JerusalemContext/CityDetailV1/Materials/`:

- `MI_CityDetail_Meleke`: parapet, stair-head, dome and arch meshes.
- `MI_CityDetail_DarkPlant`: solar-tank and water-tank meshes.
- `MI_CityDetail_Metal`: air-conditioner, satellite-dish and aerial meshes.
- `MI_CityDetail_Laundry`: washing-line mesh.
- `MI_CityDetail_Canvas`: awning and stall meshes.
- `MI_CityDetail_CityStone`: the earlier building retint, superseded on the
  measured 1,498 building components by the CityFacade instance described below.

The mesh-to-material mapping above comes from `meshes[].assetName/materialKey` in
`SourceAssets/context-review/CityDetailV1/city-detail-manifest.json`.
`Scripts/release_city_detail.py:363–409` creates/reuses the instances, sets their
parent, and writes scalar/vector parameters. The native receipt reads those
parameters back. None of those code paths sets static switches or instance
base-property overrides, but neither does that receipt enumerate those fields
on reused assets. Do not equate a recipe's absence of assignments with proved
absence of saved overrides.

The usage-flag receipt
`SourceAssets/visual-review/citydetail-usage-flags-20260910T062625637031Z.json`
independently reads all six parents as `M_Context_Building`. It sets the master's
`used_with_instanced_static_meshes` flag, records the resulting SHA256
`cebfd36d95292f2b9df53634d48c31a8cdaeacbab2fdef1ee4f8e0b986732c2a`, and reports no
such property on the instances. This is a master usage flag, not evidence of
static-switch or base-property override state. Preserve this HISM usage support
in any cook. The newer props are separate from the legacy rooftop pair meshes.

Seventh known direct child:
`/Game/MikdashV3/JerusalemContext/OldCityFacadesV1/Materials/MI_OldCityPlaster`.
`SourceAssets/context-review/OldCityFacadesV1/native-import-20260908T032216366023Z.json`,
`materials.infill`, records that exact parent and scalar/vector readback.
`Scripts/release_oldcity_facades.spec.json:70–90` and
`Scripts/release_oldcity_facades.py:294–331` describe the same relationship.
Infill uses this instance; the imported facade shells use `M_Context_Building`
directly. The import spec assigns every mesh slot, which is one slot per source
OBJ. That import receipt covers its batch, not a fresh whole-scene census.

Historical asset-level building assignment is separately recorded by
`SourceAssets/materials-context/native-apply-20260907T215118571170Z.json`:
`savedMeshCounts.buildings` is 1,499. This is not the visible material count in
cp24: later component overrides take precedence over those static-mesh slots.
Any asset-only patch must respect that distinction when choosing image subjects.

### M_CityFacadeV1 chain and cp24 building slots

The full master path is
`/Game/MikdashV3/JerusalemContext/CityFacadeV1/Materials/M_CityFacadeV1`.
Its known direct child is
`/Game/MikdashV3/JerusalemContext/CityFacadeV1/Materials/MI_CityFacade_CityStone`.
**M_CityFacadeV1 is a separate Material, not a material-instance descendant of
M_Context_Building.** `Scripts/release_city_facade.py:480–488` copies the context
surface and normal Custom-node code into this independent graph; patching only
M_Context_Building cannot repair the CityFacade graph's old copied HLSL.

`SourceAssets/context-review/CityFacadeV1/native-city-facade-apply-candidate-20260911T123627216048Z.json`
records `assetReadback.instanceParent` as that CityFacade master and
`overrideCensusBefore` as **1,498 components using MI_CityFacade_CityStone**.
The script's `census/retarget` methods around lines 580–608 restrict this count
to `SM_JerusalemBuildings_` actors and their component override slot zero. It
does not include every city mesh family or every material slot.

That receipt's mode is `nothing_to_do_map_unchanged`; its map hash is
`8c9f58d1f5cf7ac2f0dbc106fc76b4b9f9ace0628c8056856c99b9488cd82f52`, preceding the
final plaza update/current `3f986fb6...` map. Thus the receipt is a pre-cp24
assignment measurement, not a direct readback of cp24's cooked package. The
later cp24 cook receipt/log supplies chronology; cooked bindings still need
verification during the patch experiment.

The native instance hash is
`71a34a549439aeaa9566cc59e587f7b18f4833ec41c9294c30d45b1b1e15a884`.
An offline hash of the current instance file on 15 September matches exactly.
Its measured parent relationship and parameters therefore have not changed in
the current source bytes since that receipt. The master changed from the
pre-coursing `6a887def02af36b772b6a1f53e69a11aed56f3dbd37050860c03849ba7b81353`
to `80fc721af27e81665ceebcea11dc7e02f1c60b92e7ef43ba15798ddf3a2837a4` in the
coursing verify receipt. The instance builder at
`Scripts/release_city_facade.py:520–535` sets parent, scalars and vectors only;
`readback_assets:539–578` proves Nanite/HISM master usage, parent, wiring and
those parameters, but does not read static/base-property override fields.

### M_Context_CityWall chain

The full master path is
`/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_CityWall`.
No named instance child was established by the inspected recipes/receipts.
This is **unknown descendant coverage**, not proof that it has no children.
The historical context native-apply receipt cited above contains 58 `walls`
assignment records, already carrying this master, such as
`/Game/MikdashV3/JerusalemContext/Streets/SM_Jerusalem_CityWalls_04_Grid_N001_N003`.
`SourceAssets/lighting-review/lighting-v3-inventory-20260908T183719554035Z.json:470`
also records 58 slots using the master. These are historical scene/asset counts,
not a current packaged census. They provide potential direct-master image
subjects for the smallest patch test, subject to live binding confirmation.

The current coursing verify receipt records the building master's hash as
`c83a1064ba18ef7f4309a803fb8ad7d447bfede5d10d989cb345d10af212076a` and city-wall
master's hash as `e4272a60834f1200bd3ceabc8aa2519335eb59691f12c96abedca03c41b0e23b`.
Their pre-edit hashes in the apply receipt are respectively `cebfd36d...` and
`7b07fb41...`. These describe source bytes, not extracted cp24 material bytes.

### What remains to establish before the cook list is final

- Enumerate recursive descendant instances anywhere in the project, not only
  these three material folders. The eight names above are a minimum audit set.
- Read each instance's effective parent chain, static parameter sets,
  base-property override flags/values and static-permutation resource state.
  No inspected receipt certifies those fields. Recipes suggest ordinary
  scalar/vector instances; this is an inference, not a verified zero-permutation
  result. Do not omit instances solely on that inference.
- Determine exact cooked and active component/material-slot bindings. Distinguish
  static-mesh asset defaults from component overrides and runtime dynamic
  instances. Existing building retint evidence was superseded by CityFacade;
  `MI_CityDetail_CityStone` still exists on disk but its continued visible use
  elsewhere is unproved.
- Compare included instances/dependencies to the base before staging. An unchanged
  ordinary parameter instance may use the newly patched parent without its own
  package override; a static-permutation instance can require a new cook. The
  material's actual serialized resource and rendered result decide, not its name.
- Keep standalone ContextCoursing study copies outside the production patch.
  They are review assets, not additional scene consumers of the corrected masters.
