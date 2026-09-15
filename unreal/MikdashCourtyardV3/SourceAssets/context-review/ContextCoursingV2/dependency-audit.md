# Entry-only material descendant audit

Prepared 15 September 2026. **The coordinator's native Entry audit completed**:
`dependency-audit-20260915T174543Z-34988.json`, status
`audited_with_explicit_unknowns`, no errors. It is not an exhaustive cooked-package
audit or proof of patch delivery. No cook memory bound is promised. The actual
results and the remaining private-field unknowns are summarized below.

`Scripts/audit_context_patch_dependencies.py` reads all mounted registry MIC
metadata and selects the recursive descendants of the three coursing masters.
It cross-checks a full MIC Parent-tag scan against recursive
`MaterialEditingLibrary.get_child_instances` queries, then loads only those
masters/descendants to compare actual parent pointers. Both discovery methods
use the same registry; agreement is not independent proof of registry completeness.
There is a hard bound of 256 descendants. Missing Parent tags, unavailable source
hashes and inaccessible reflection fields are reported explicitly.

The script does not load a map, call a material setter, recompile, update a
material instance, import, or save an asset/map. Loading a material can still
cause engine post-load work; unexpected dirty `/Game` packages fail the audit.
All project `.umap` hashes and hashes of selected `/Game` source material files
are compared before/after. External/plugin/engine material source hashes are
marked unavailable rather than guessed. It does not hash every dependency or
every project asset. Receipt writes are its only intended file changes.

## Owned native launch

The coordinator must serialize this with cooks/builds/editor/game probes and
apply a process/commit watchdog. Start a fresh owned editor explicitly on Entry;
do not attach the script to a user's editor. This argument vector describes the
owned Entry audit; the coordinator's `Scripts/Test-ContextPatchAudit.ps1` supplies
the bounded native launch and records its actual command:

```text
"C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe"
"C:/Mikdash/Working-5.8/MikdashCourtyardV3/MikdashCourtyardV3.uproject"
/Engine/Maps/Entry -ContextPatchDependencyAudit
-ExecCmds="py C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/audit_context_patch_dependencies.py"
-unattended -nullrhi -NoSplash -abslog="<unique outside-project log>"
```

It requires the explicit marker, exact project root, an already-open
`/Engine/Maps/Entry` editor world and no game/PIE world. Only after all four checks
does it own the process for normal quit. It never quits a wrong-context editor.
No `-run=pythonscript` recipe is offered: that mode may lack the required Entry
editor world. It flushes a unique `dependency-audit-<UTC>-<PID>.json` before
requesting normal quit of a validated owned editor. No automatic process kill,
native subprocess or retry is implemented.

## Reflected evidence and honest limits

Every optional property read has `status: read` with a value, or `status: unknown`
with the actual exception. Missing/private fields are never converted to false
or an empty array. C++ property names and their Python snake-case forms are
tried through read-only `get_editor_property`; no C++ pointer/raw-memory access.

- Actual parent pointers and parent chains must agree with registry edges and
  terminate at one of the three corrected masters; disagreement/cycles fail.
- `bHasStaticPermutationResource` is reflected but not publicly editable. The
  Python property may be inaccessible; a successful read refers to the loaded
  source object, not the resource serialized into cp24.
- `BasePropertyOverrides` reads all 16 override flags in the installed 5.8 header,
  including the new usage-flags mask, with associated values. Nested structs may
  be exported as diagnostic text. No recook conclusion is computed from that text.
- `StaticParametersRuntime` attempts switch arrays, material-layer presence and
  layer data. `EditorOnlyData.StaticParameters` attempts component-mask, terrain
  layer-weight and material-layer evidence. These private/editor fields may be
  unavailable to Python.
- The public static-switch names/value API is included separately. It defaults
  to global parameter association; it is not exhaustive for layer/blend keys,
  and an effective value does not establish a local override.
- Nanite override-material evidence is recorded because it can select another
  rendering material. This audit does not traverse arbitrary non-parent override
  references into a new patch set automatically.
- Master evidence uses the same optional property probes; instance-specific
  fields on a master will correctly report unknown/not exposed.
- No automatic decision that an instance can be omitted from cooking. Every
  material row states `recookDecision: not_decided_by_this_audit`.

## Primary installed API sources

Paths below are relative to
`C:/Program Files/Epic Games/UE_5.8/Engine/Source/`.

- `Runtime/AssetRegistry/Public/AssetRegistry/IAssetRegistry.h:328–335` exposes
  GetAssetsByClass using FTopLevelAssetPath; lines 809–830 expose SearchAllAssets,
  WaitForCompletion and explain that early plugin loading can leave assets
  ungathered. The registry must no longer report IsLoadingAssets afterward.
- `Runtime/AssetRegistry/Public/AssetRegistry/AssetRegistryHelpers.h:120–124`
  exposes GetExportTextName/GetTagValue. The script handles export-text paths and
  the optional string/bool-output shapes without treating a failed read as an edge.
- `Editor/MaterialEditor/Public/MaterialEditingLibrary.h:492–514` exposes direct
  child instances and static-switch names; lines 453–461 expose effective static
  switch values. `Private/MaterialEditingLibrary.cpp:1779–1794` implements direct
  children by exact searchable Parent export-text tag, not a dependency guess.
- `Runtime/Engine/Public/Materials/MaterialInstance.h:617–622` declares the
  editor-only static set; lines 646–681 declare searchable Parent, native-only
  GetStaticParameters/HasStaticParameters, and reflected
  bHasStaticPermutationResource. The script does not call the native-only methods.
  Lines 820–851 declare BasePropertyOverrides and private StaticParametersRuntime.
- `Runtime/Engine/Public/Materials/MaterialInterface.h:355–367` declares the
  reflected protected EditorOnlyData pointer. `Runtime/Engine/Public/StaticParameterSet.h:396–445`
  declares reflected runtime switches/layers and editor masks/terrain weights.
- `Runtime/Engine/Public/Materials/MaterialInstanceBasePropertyOverrides.h:15–153`
  declares the override flags/value fields queried by this script, including
  bOverride_UsageFlags/UsageFlags. Source declarations justify probing; they do
  not promise each field is exposed by the generated Python wrapper.

No installed full `unreal.py`/`.pyi` wrapper stub was available in the inspected
engine/project paths. Headers and implementation supplied the initial API
evidence; the native receipt now records actual Python availability per field.

The first native audit has now resolved that availability question for public
discovery/parent/base-property APIs: they worked. The protected static resource
and parameter-set fields were unavailable, exactly as the script records.

## Offline tests and receipt contract

```text
python -B Scripts/audit_context_patch_dependencies.py --self-test
```

Seven tests pass: exact recursive parent edges (no prefix matches), cycles and
missing roots, chain order, export-text normalization, inaccessible property as
unknown, successful false as false, and AST inspection forbidding production
mutator/map-load calls. These test graph/evidence handling and scope; they do not
mock a native acceptance or certify wrapper signatures.

`dependency-audit.schema.json` describes the receipt's stable top-level contract.
`audited_with_explicit_unknowns` means enumeration/read attempts finished and
disk/dirty checks passed; it does not mean unknown fields were resolved or the
patch is ready. `refused_or_failed` includes guard, registry/load/parent failures
and post-audit disk/dirty failures. Both states retain errors/evidence. A process
crash can leave a partial receipt or no receipt; neither is successful evidence.

## Native result and cook-list consequence

Receipt: `dependency-audit-20260915T174543Z-34988.json`.
Executed script SHA256:
`379c87445600ded87af57532fee67945329ca60fcdb4ace06fea5eb5fa7704ce`.
The audit searched 792 registered MIC assets and found ten descendants by both
queries. All ten loaded parent pointers matched the registry; every chain is
direct (instance, master), with no second-generation child found. Twenty map
hashes and all thirteen selected source-asset hashes stayed unchanged, no source
hash was unavailable, and the final dirty-package/error arrays were empty.

One registry MIC lacks a Parent tag:
`/MetaHumanCharacter/Optional/Clothing/Common/Materials/Crewneckt/Male/M_m_top_crewneckt_nrm`.
It was not loaded. This and unmounted/unregistered content remain limits on an
absolute exhaustive claim; neither discovery method supplies an edge for a
missing tag. The census is the matched descendant set of the inspected mounted
registry, not every possible package or cp24 binding.

The eight previously known instances were confirmed. Two direct children had
been missed by the earlier recipe inventory:

- `/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/ExteriorFixesV1/MI_M_Context_Building_ExteriorV1`
  has parent `M_Context_Building` in the parent materials folder.
- `/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/ExteriorFixesV1/MI_M_Context_CityWall_ExteriorV1`
  has parent `M_Context_CityWall` in the parent materials folder.

These are the fallback parameter instances implemented by
`Scripts/release_exterior_fixes.py:654–703` and configured by
`Scripts/release_exterior_fixes.spec.json` under `tiling.instanceFolder`,
`instancePrefix`, and `instanceSuffix`. Discovery proves the saved chains;
continued visible assignment in cp24 still needs a packaged binding check.

All ten instances have the **same override conclusions**:

- `BasePropertyOverrides` and every one of its 32 queried fields read successfully.
  All fifteen boolean override flags are false and `bOverride_UsageFlags` is zero.
  **No base-property override is enabled on any of the ten instances.** This
  includes blend mode, shading model, two-sidedness, tessellation, displacement,
  LOD dithering, velocity, pixel animation and usage override fields.
- The plain `UsageFlags` value is 4,456,576 on nine instances and 4,456,448 on the
  city-wall ExteriorV1 instance. These populated values are not active overrides:
  the override bitmask is zero on all ten. The numbers are reported without
  inventing a mapping from bits to vertex factories.
- The public static-switch enumeration read successfully and returned zero
  names on each instance and on each of the three masters. This does not expose
  private static component-mask, terrain-weight or material-layer sets.
- `bHasStaticPermutationResource`, `StaticParametersRuntime`, and
  `EditorOnlyData.StaticParameters` were protected/inaccessible for **all ten**.
  They remain unknown, not false or empty. No result proves absence of serialized
  cp24 static permutation resources.
- Every Nanite override struct exports `bEnableOverride=True` with
  `OverrideMaterialEditor=None`, `OverrideMaterial=None`, and
  `OverrideMaterialRef=None`. Thus the enabled flag is true, but this readback
  identifies no bound alternative Nanite material. Do not mistake the enabled
  flag alone for an actual override reference or a base-property override.

Per-instance coverage of those conclusions:

- Building master: `MI_CityDetail_Canvas`, `MI_CityDetail_CityStone`,
  `MI_CityDetail_DarkPlant`, `MI_CityDetail_Laundry`, `MI_CityDetail_Meleke`,
  `MI_CityDetail_Metal` under `CityDetailV1/Materials`; `MI_OldCityPlaster` under
  `OldCityFacadesV1/Materials`; and `MI_M_Context_Building_ExteriorV1` under the
  `ContextMaterialsV1/Materials/ExteriorFixesV1` folder. Eight direct children.
- City-wall master: `MI_M_Context_CityWall_ExteriorV1`, one direct child.
- CityFacade master: `MI_CityFacade_CityStone` under `CityFacadeV1/Materials`, one
  direct child.

For the **first small city-wall experiment**, expand the explicit request to
the master plus its one discovered child, retaining the existing isolated,
inline-shader, no-default-map cook flags:

```text
-Package=/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_CityWall+/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/ExteriorFixesV1/MI_M_Context_CityWall_ExteriorV1
```

This is a conservative two-package request because private resource state remains
unknown; it is not proof the instance strictly requires recooking. It covers
either direct-master or known ExteriorV1 binding for the first image subject.
Do not enlarge the first memory experiment to all thirteen packages merely
because they are now enumerated. After the one-family cook/container/native
A/B/A succeeds, the complete **candidate cook audit list is three masters plus
these ten descendants**; compare source dependencies to the base and verify all
affected material families before staging or dropping any package.

The coordinator reports that the first cook preflight refused below 9 GiB free
commit without launching the engine. That is not a cook attempt, success, failure
inside Unreal, or a reason to lower the gate. This successful Entry audit does
not establish that a cook will fit the current memory headroom.

The receipt conforms to the existing schema contract; no schema or script change
is needed to accommodate these ten descendants. No material/map edits or new
native jobs were performed during this result interpretation.
