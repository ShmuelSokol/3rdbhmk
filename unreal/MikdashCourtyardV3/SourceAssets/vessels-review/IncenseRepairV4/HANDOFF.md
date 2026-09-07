# Incense V4 source repair, native acceptance pending

Only source files and this evidence directory were changed. Historical scripts are preserved as before-v4-*.txt and the historical shared spec hash is checked offline. No native assets created, no editor/GUI/build/Git actions performed by this worker.

## Coordinator entrypoints

1. With full Unreal editor and CascadeToNiagaraConverter already loaded, execute Scripts/create_incense_smoke_study.py as a module, then call build(). It intentionally authors only /Game/MikdashV3/MaterialReview/IncenseSmokeV4. Existing V4 material/system or native-authoring.json causes refusal; preserve partial results before planning recovery. Do not run this authoring under commandlet/NullRHI: historical Finalize required Slate.
2. Reopen/check saved V4 system, compile readiness, and module input acceptance. Confirm actual Niagara stack has InitializeParticle before CeilingOriginV4 before AddVelocity. Converter dependency fixup may influence native ordering; offline creation ordering alone is not proof.
3. Load the existing isolated /Game/MikdashV3/MaterialReview/IncenseSmokeReviewV3/L_IncenseSmokeReview map. Execute Scripts/inspect_incense_particles.py as a module; call begin(), allow editor readiness frames, then sample(6.0). The harness changes the existing review actor transiently and never saves the map. Call stop() afterward and reopen the saved rig without saving transient changes. Do not substitute the production map.
4. Inspect entry origin_check: valid actual age near6, all eight wisp emitters live, positions z841..865cm (+/-2cm), vertical position consistent with particle age. The check assumes build() defaults. Custom dimensions require corresponding checker arguments. Pass is attributes only. Capture visible shaft and ceiling spread with actual-age corroboration, then inspect lifetime end with sample(12.0). Captures, dependency audit, cook and scheduler integration remain separate.

## Source evidence and limits

Installed UE5.8 converter finalization batches direct assignments before ordinary modules, so a direct spawn Particles.Position write would be overwritten. V4 retains the initializer1.0 that produced a shaft, disables its ineffective offset, and adds installed ShapeLocation after initialization for the eight wisps, using sphere radius0.01cm and Local offset(0,0,865). Shape module parameter acceptance and native order are not yet proven. The small radius avoids a zero-radius degenerate shape; this is an artistic point source, not fluid/historical simulation.

Run offline regression: python SourceAssets/vessels-review/IncenseRepairV4/verify_offline.py. Nineteen checks passed, including rejection of the actual V2 floor-wisp receipt, missing emitters, invalid cache, wrong actual age and nonfinite data.

Proposed next owned task: after coordinator provides the V4 native receipt, diagnose only any module/particle mismatch and adjust the owned harness/source in a new preserved attempt; if it passes, prepare finite-lifetime/dependency evidence criteria without taking native execution ownership.
