# Jerusalem paving material review

Prepared import-only; no native execution or visual acceptance from this helper.
The frozen PNG SHA-256 is `d3c9f895f72105e812654550e2fc05c29b0e769ebce6026ecf31fa32a71921f6`.
Its source receipt identifies an authored interpretation of current Old City Jewish Quarter paving. It is not a scan or evidence for future Temple flooring. The original family photograph remains private; root decides whether the generated image may be published after review.

Offline: import `Scripts/release_jerusalem_paving.py` with importlib and call `run()`.
Native, root serial execution only: call `run(import_assets=True)` in the active project with no PIE or dirty packages. This creates the fresh namespace `/Game/MikdashV3/MaterialReview/JerusalemPavingV1` and refuses existing or partially imported folders.

Current review material: `/Game/MikdashV3/MaterialReview/JerusalemPavingV2/M_JerusalemPaving_500cm`. Native V1 was rejected after a checkerboard fallback appeared in the actual PIE view. V2 preserves the same original1254px PNG; Unreal's StretchToPowerOfTwo build setting permits proper mip generation without padding a border into the tile. The PIE probe preloads/recompiles this material and calls GetStatistics, whose installed engine implementation finishes its shader compilation without waiting for the city's unrelated derived data. V1 remains preserved as evidence.
Initial A/B is restricted to the exact flat surface mesh `/Game/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Surface`; this script never assigns any material or loads/saves a map. Do not apply it to the skirt, walls or Temple court floors automatically.

Absolute world XY divided by 500 cm controls physical tiling independently of mesh UVs and actor scale. Mirrored addressing gives a 500 cm tile with a 1000 cm orientation repeat. It prevents opposite edge mismatches but can expose mirrored patterns, which require actual PIE review. Base color uses the unchanged sRGB PNG, metallic is zero, roughness is a constant 0.8, and Nanite material usage is persisted. There is deliberately no normal map or shader-derived height: the albedo is not measured relief. Fine joints and relief remain a visual limitation.

The native-proven Custom node property names `Code`, `OutputType`, `Inputs` and CustomInput `InputName` are used. Installed UE5.8 `Engine/Classes/Engine/TextureDefines.h:500` defines `TA_Mirror`; Python exposes `TextureAddress.TA_MIRROR`. Material graph inspection uses the existing native-proven MaterialEditingLibrary expression/input/property introspection.

The receipt validates the full linked graph, texture identity/sRGB/mirror, constants, Nanite usage, saved asset hashes, all architecture/protected-map hashes from the existing migration preflight, main and currently loaded map hashes, and the unchanged actor/component snapshot. No existing asset is mutated, so the external checkpoint contains the protected-hash record rather than copied map data. A failed import leaves its namespace intact and refuses a blind retry. Saving and load_asset readback do not prove a fresh-process disk reload; root should run `graph_snapshot(unreal, unreal.load_asset(MATERIAL))` in a subsequent editor process, followed by matched PIE A/B. No map is changed by either check.

Acceptance remains pending: brightness/color under the current sky and shadows, tile scale from standing eye height, repetition and mirror seams across the broad deck, and ground-level detail. The script cannot establish those from import/readback alone.
