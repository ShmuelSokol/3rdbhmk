# Ketores integration readiness — 7 September 2026

**Not ready for production placement.** Existing V4 source/evidence actually lives under `SourceAssets/vessels-review/IncenseRepairV4`; this requested readiness note does not relocate it. At audit time `Content/MikdashV3/MaterialReview/IncenseSmokeV4/NS_FiniteIncenseStudy.uasset` was absent. The generator repair is prepared, not natively accepted. No engine execution was performed here.

## Smallest next native test

Use the existing isolated review workflow before touching RELEASE actors:

1. In a full real-RHI editor with `-EnablePlugins=CascadeToNiagaraConverter`, execute `Scripts/create_incense_smoke_study.py` as a module, then `build()`. Authoring Finalize historically needs Slate; do not use a NullRHI commandlet. Preserve any partial V4 namespace/receipt instead of rerunning blindly.
2. Reopen the saved system, verify accepted module inputs and actual stack order: InitializeParticle → CeilingOriginV4 ShapeLocation → AddVelocity. This specifically tests the failed floor-wisp repair.
3. Load `/Game/MikdashV3/MaterialReview/IncenseSmokeReviewV3/L_IncenseSmokeReview`; execute `Scripts/inspect_incense_particles.py`, call `begin()`, allow readiness frames, then monotonic `sample(1)`, `sample(3)`, `sample(6)`, `sample(9.5)`, `sample(12)`, and `stop()`. Never save transient rig changes. Existing harness checks force-solo and actual cache age; requested age alone is insufficient.
4. At actual age6 verify all eight wisps at local z841..865 cm ±2, plus visible upward shaft and ceiling spread. Inspect real-RHI images. Default last shaft death is9s and last wisp death11s. An invalid/inactive late cache is **incomplete evidence**, not proof of extinction: add a completion-state capture protocol if needed. `LifetimeChecksV1/validate.py` is syntax-only per its handoff, so validate its fixtures before trusting it.
5. Reopen without converter and audit recursive dependencies, then fresh cook. Historical V1/V2 cook receipts do not validate V4.

These entrypoints already exist; an automated editor-tick runner that sequences readiness, samples, images and reliable late completion remains missing. Root should own that bounded runner and serial execution.

## Correct current RELEASE anchor

`SourceAssets/vessels-review/IncenseAltarV2/native-import-20260907T203152827687Z.json` records `RELEASE_IncenseAltar_Body`, asset `/Game/MikdashV3/MaterialReview/IncenseAltarV2/Meshes/SM_IncenseAltarV2_Body`, at **[-4650,0,925.000061]**, identity rotation/scale. Do not reuse the old original-study x=-4500 location.

Its maximum worldZ1008.333397 is the **horn tops**, not the central emission surface. `Scripts/create_incense_altar_v2.py` defines roof top79.166667 local, a central recess and plate geometry. A future transient scene-test helper must inspect that central hearth surface/source before choosing its exact small above-surface offset. Resolve current saved actor by exact label+mesh, verify transform and source/receipt hashes, then transform the local anchor to world. Do not attach at actor origin or use whole-asset AABB max as a hearth contact.

The study assumes a900cm rise measured **from its emission origin**, with wisps at rise−35cm. It has no roof detection. Measure current ceiling underside above the actual altar and subtract the actual hearth origin. Reauthor into a new namespace or add verified exposed runtime parameters; simply moving/scaling the900cm study does not establish a correct ceiling match. Current build arguments bake parameters into module inputs, not a proven User-parameter contract.

Missing smallest scene test: a transient `test_release_incense_once.py` that checks saved RELEASE altar/ceiling, refuses mismatched height, activates one accepted system once, records timed images/counts/completion, stops and restores without saving. Do not place a perpetual auto-activated smoke actor.

## Schedule bridge and source limits

`Plugins/MikdashRuntime/Source/MikdashRuntime/Public/IncenseServiceSchedule.h` supplies named phases and prerequisite checks; it is not currently a verified renderer/calendar bridge. Ordinary morning cue follows its recorded morning blood predecessor; ordinary afternoon cue follows its limbs predecessor. Feed reviewed scenario, golden-Heikhal location, assigned/prepared officiant, garments and completed withdrawal. Unknown facts stay NeedsReview; do not fabricate success booleans merely to show smoke. Use a separately labelled diagnostic preview for the visual test.

Consume only Outcome::Started once per (CycleId, Service); snapshot/restore schedule state, reconstruct remaining visual state without replaying the event, and freeze schedule plus particles during pause. Current default emission6 + rise3 + spread2 implies up to11s visual duration, so a matching scheduler illustration is emission6/residual5, not emission6/residual2. These seconds, speed, sprite size and radial feathering are artistic parameters, not halachic service durations. Real-time clock scheduling remains unimplemented; use reviewed named phases rather than invented8am/4pm assertions.

`C:/Mikdash/GitHub/3rdbhmk/unreal/Research/ketores-service-and-smoke.md` supplies KET-DAILY-SEQUENCE/LOCATION and KET-SMOKE-FORM. The upright-rise/ceiling-spread illustration is inspired by historical descriptions, not a certified future fluid simulation. Yom Kippur inner service requires a separate reviewed profile/location/Kohen Gadol and must not substitute for ordinary daily offerings. Officiant departure, residual smoke and permission to enter are separate states. No plant identification, recipe or live burning instructions are needed.
