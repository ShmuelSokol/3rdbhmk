# UE5.8 PBR instance usage repair — native execution pending

Observed source log: `C:\Mikdash\Working-5.8\Astra-Groups-Main01-20260908.log`.
The exact allowlist contains nine `MaterialInstanceConstant` packages in
`/Game/MikdashV3/Materials/PBR/Instances`:

- Runtime missing-usage warnings: `MI_PBR_Marble`, `MI_PBR_GoldHammered`,
  `MI_PBR_CedarPlanks` (log lines2374,2376,2378).
- Editor auto-set displays: `MI_PBR_LimestoneTrim`, `MI_PBR_LimestoneAshlar`,
  `MI_PBR_PavingSlabs`, `MI_PBR_GoldFloor`, `MI_PBR_RoughStone`, `MI_PBR_Plaster`
  (lines2264–2273). Auto-setting in memory is not proof of saved persistence.

## Primary code findings

Installed engine source root: `C:\Program Files\Epic Games\UE_5.8\Engine\Source`.

- `Runtime/Engine/Private/Materials/MaterialInstance.cpp:1740–1838`: instances
  maintain their own usage bitmask and base-property usage overrides. When a usage
  is missing, editor/non-game mode may set it, compile and dirty the package. The
  game/PIE branch logs the warning and returns false; it does not silently fix the
  usage flag during gameplay. This is a real rejected usage check. It does **not**
  prove which pixels in a current screenshot used the fallback: visible section,
  current render resource and later editor activity still matter.
- `Editor/MaterialEditor/Public/MaterialEditingLibrary.h:211–223` exposes
  `HasMaterialUsageOverride` as `UFUNCTION(BlueprintPure)` and
  `SetMaterialUsageOverride(UMaterialInstanceConstant*, Usage, bOverride, bValue)`
  as `UFUNCTION(BlueprintCallable)`. Python calls are
  `has_material_usage_override(instance, MATUSAGE_NANITE)` and
  `set_material_usage_override(instance, MATUSAGE_NANITE, True, True)`.
- Its implementation `.cpp:853–908` modifies only the requested override/value bit
  using a material-instance parameter update context and marks the instance dirty.
  It does not alter the parent. `update_material_instance` at1759 updates its
  static permutation; `get_statistics(instance)` at2116 submits missing shader
  jobs and waits for that interface's resource compilation.
- `Runtime/Engine/Public/Materials/MaterialInstanceBasePropertyOverrides.h:78,142`
  declares the reflected editable uint32 fields `bOverride_UsageFlags` and
  `UsageFlags`. The helper removes only those numeric assignments from its exported
  base-property snapshot; independent per-usage checks protect all other usage bits.
  Scalar/vector/texture parameter arrays and parent identity are compared exactly.
- `release_pbr_architecture.py:520–542` assigns these instances to the shared
  `M_PBR_Tiled` parent and verifies their textures. Its spec fixes the instance root,
  master name, scalar/tint inputs and texture sets. The Nanite optimization script
  enables mesh Nanite settings but does not persist these instance usage overrides.
  The historical `release_nanite_material_usage.py` accepts base materials from an
  older log; it is preserved unchanged and does not handle this instance-only case.

## New helper and safeguards

`Scripts/release_nanite_instance_usage.py` is offline by default:

1. `run()` / normal Python invocation returns the exact nine-package plan and hashes.
2. In a clean **real-RHI**, non-PIE process with a unique `-abslog=...`, call
   `run(apply=True)`. Use an empty editor world so loading the default map has not
   already auto-dirtied materials. All nine original packages are checkpointed
   before any load. Every class, parent and parameter snapshot is checked before
   mutation. Only those nine instances are saved.
3. In a **different process**, call
   `run(verify_only=True, repair_receipt="<successful apply receipt path>")`.
   The helper requires a distinct PID, successful protected-hash receipt and exact
   saved package hashes. It checks usage/override and compilation without saving.

All19 current map packages, Config ini files and every other PBR asset (including
the shared parent and textures) are hash-protected. Each successful save records its
disk hash immediately; failures preserve the original checkpoints and partial-save
receipt. Explicit Nanite override readback must be true. Parameters, parent and
other usage overrides must remain unchanged. No blanket save or map mutation exists.

Compilation evidence requires a positive pixel-instruction resource and no newly
observed compile errors in the job log, after `get_statistics` finishes compilation.
Sampler counts are recorded, not thresholded: shared samplers make a fixed minimum
of three unsound. This compilation check is not visual adoption; fresh-process
usage verification, targeted real-RHI captures and the packaged cook remain pending.

Offline checks: nine exact observed packages and classifications parse successfully;
Python syntax and snapshot-mask normalization checked. No Unreal/UBT or asset mutation
was run by the preparing worker. Python reflection follows the installed UFUNCTION
declarations but still needs the coordinator's native call/readback; any mismatch
must stop with its checkpoint rather than fall back to arbitrary property writes.
# Native follow-through

Follow-up actual scene PIE log `Astra-Groups-Candidate48-01-20260908.log` contains zero missing/auto-set Nanite usage messages. Receipt180131188281 completed with no errors; screenshot180225 inspected. Persistent compatibility repair is supported; broad bright/clipped surfaces remain visually unresolved, and no new package has been cooked.

Root ran the prepared helper in a real-RHI commandlet. Apply receipt `nanite-instance-usage-20260908T173857999122Z.json` saved all nine targeted instances and compiled their resources. A different process then ran `verify_only=True` against that receipt: `nanite-instance-usage-20260908T175937249147Z.json` passed fresh usage/override/resource checks without asset writes. Protected maps, configs, shared parent and other PBR assets remained unchanged. This establishes persisted usage compatibility; scene appearance and packaged cook are separate checks.
