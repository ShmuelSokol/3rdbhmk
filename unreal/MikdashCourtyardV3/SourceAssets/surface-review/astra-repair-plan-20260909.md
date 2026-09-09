# Surface wear V2 bounded repair — 9 September 2026 UTC

Owned changes: release_surface_detail.py and its spec. No native job or asset/map mutation was run by the repair agent.

## Native sequence (coordinator only, strictly serial)

Use the existing real-RHI hidden UnrealEditor invocation with `-ExecutePythonScript="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_surface_detail.py" -SurfaceStages=assets -unattended`. Do not use NullRHI: the new master requires positive compiled pixel instructions. Ensure Scripts is on sys.path in runpy wrappers for the shared snapshot helper.

Inspect the resulting receipt: status must be `assets_created_shader_readback_complete_map_unchanged`, errors and omissions empty, maps/materials unchanged. A failed partially-created V2 namespace is deliberately not reusable: investigate and select a new explicitly reviewed namespace; do not overwrite or remove V1/V2 assets.

Then a new editor process with the same script and `-SurfaceStages=decals,manager`. This requires a successful exact-spec asset receipt, checks saved asset hashes before placing, and requires the compiled manager. Inspect saved/reopened receipt, then run fresh-process PIE and view captures. No visual or performance acceptance is established by offline checks or shader instruction counts.

## What changed

- Fresh SurfaceDetailV2 namespace, all existing texture/master/instance writes refused. Source `surface-detail.json` remains byte-identical SHA f67545c0037406fa7d8f3c897334e88b3658ba8a64beecb3341cb17986dab202. Its V1 namespace is rebased in memory with explicit receipt provenance; source geometry/texture bytes remain pinned.
- Stone is no longer a recognized stage. Current V3 limestone, all PBR materials, reviewed Lighting gold, V1 wear assets, Kotel assets and every other map are hash-protected. No stone retuning or component stone overrides occur.
- Dirty guards precede target load. Shared release_place_assets snapshot rules replace stale raw ISM AABB comparisons; pristine reload churn exclusions are receipted.
- Named pitch/yaw/roll prevents positional Rotator mistakes.
- Installed UE5.8 Engine/Source/Runtime/Engine/Public/Materials/Material.h marks DecalBlendMode deprecated, “No longer used.” Removed that protected setter; master uses DeferredDecal domain, Translucent blend, connected base-color/roughness/opacity, no normal output. Graph links and real-RHI compilation are required.
- Requested stage omissions now refuse map save. Manager configuration is checked after reopen. Legacy label-based revert is disabled; use a reviewed checkpoint recovery.

## Offline result and limits

Offline reconciliation passes all eleven source texture hashes and plan/spec reconciliation. Pure checks confirm V2 remap and stone-stage refusal. Not compiled or launched here. Placement remains authored from earlier geometry: actual surface projection, floating decals, brightness, runtime fade/budget behavior and frame cost need native review. This is a bounded wear layer, not acceptance of all surrounding terrain or stone visuals.
