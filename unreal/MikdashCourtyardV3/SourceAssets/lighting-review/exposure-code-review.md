# Exposure code review — offline independent check

Reviewed `Scripts/release_lighting_polish.py` and `Scripts/release_interior_exposure_fix.py`, plus native exposure receipts ending214322332925Z and214522053469Z. No native execution or shared-file edits performed.

## Verified behavior

The local installed UE5.8 renderer source, `Engine/Source/Runtime/Renderer/Private/PostProcess/PostProcessEyeAdaptation.cpp`, lines376 and651 onward, uses luminance scale1 when extended luminance range is disabled. It interprets the brightness fields directly as luminance in that mode and converts them from EV100 when extended range is enabled. The latest native receipt reports `r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange=0`. Therefore EV0 maps to1.0, EV8 to256.0, EV14 to16384.0. The helper conversion follows this branch correctly. Changing the minimum from256 to1 permits up to eight additional stops of brightening in a sufficiently dark metered scene; it does not force an eight-stop increase everywhere. Keeping the maximum16384 preserves the bright-scene upper adaptation bound. This is a grounded response to the near-black interior capture; visual acceptance still depends on settled interior and outdoor renders.

Native receipt214322332925Z shows that the correction saved and read back the exposure property and label, then failed on an invalidated actor object. The current script stores `actor_name` before reopening and uses that stable string afterward, resolving that exact stale-object error. The shared `save_and_reopen()` now writes mapSaved and the saved SHA immediately after successful save, before reopen can fail. The later receipt214522053469Z loaded the existing corrected map, verified minimum1.0 and maximum16384.0, made no further mutation and retained identical map SHA and protected hashes. This demonstrates the already-corrected branch against the actual saved state.

The interior helper accepts only exactly one PP volume and EV14 maximum. It changes only the minimum and label after checkpointing, retains the prior EV8 guard for the mutation branch, and checks protected hashes in finally with a raised error if changed. Dry run exits before checkpoint and changes. Already-corrected status may take precedence over dry-run status, but remains read-only. The full lighting helper blocks repeat apply when tagged polish actors exist; it is one-shot with explicit revert, not silent repeat application.

## Follow-up verification after root corrections

Rechecked the current files after root's fixes. The authoritative polish spec, numeric settings and label now consistently use EV0..14. The offline report confirms raw brightness1..16384 and extended-range0..14. A dirty-package check now precedes load_level, retaining the original post-load check. Apply now changes the receipt to failed_protected_hash_guard and raises if protected hashes differ. These three prior findings are resolved in the current source.

The older native receipt214522053469Z still contains historical spec metadata EV8/256; its verifiedMinBrightness1.0 remains the actual readback. New calls use the corrected spec, so this numerical mismatch will not recur for the current default. The metadata field exposureBoundsWritten is still spec-derived rather than a property readback, which matters if the current map differs from the spec.

## Remaining limitations

- **P2 — revert guard:** the full-polish revert finally block still only records protectedUnchanged, without failed status or an exception. Apply and the interior helper now enforce the guard. Revert is outside the current capture path but should use the same failure behavior before future reuse.
- **Required-file guard:** `_protected_hashes` still skips missing files. Assert required protected files exist rather than accepting an absence before and after.
- **Verification scope:** snapshot_unrelated compares labels and numeric transforms, not every light/material/PP property. It catches actor movement or labels, not arbitrary asset/property changes. The small explicit interior edit supports the intended scope, but the receipt must not be described as proof that every unrelated property was compared.
- **Idempotence edge:** a map with the corrected minimum but a different label fails the EV8 guard rather than repairing the label. This is a conservative stop, not an unsafe mutation. The idempotent branch verifies min/max/label only; it does not freshly certify all postprocess override flags or exposure method.

## Material issues remain independent

The bus image's default-looking grid and gray glazing suggest missing material assignments, while source OBJ normals/UVs pass. Audit actual bus slots before normals or additional exposure edits. Gold surfaces can still look pale under direct/reflected illumination and highly metallic shading. The new EV floor is not proof of correct gold roughness, reflection, or source color. Use the current root matched views after loading/adaptation barriers to judge readable gold, direct-sun clipping, glazing, and exterior brightness; do not infer completion from an exposure readback.

## Offline checks

Both scripts parse successfully. `release_lighting_polish.py` offline consistency check passed, including sun direction and HDRI provenance. Explicit numeric checks passed EV0/8/14 for both extended-range branches and the nonextended luminance scale. These checks do not execute native API branches.

## Explicit publication files from bus lane

Copy and stage only these source files to their matching `unreal/MikdashCourtyardV3/` paths in the publishing clone:

- `Scripts/release_bus_visual_audit.py`
- `SourceAssets/transit-review/bus-visual-audit.md`

This review may additionally be published as `SourceAssets/lighting-review/exposure-code-review.md`. Native receipts/maps from a future root-run bus audit must be reviewed separately; no speculative receipt, native review map, checkpoint directory, or cache belongs in this publication list.
