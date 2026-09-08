# Exact Kotel-to-platform review section

Read-only source calculation; no Unreal execution. This section follows a real facade segment, not a whole-actor bounding-box centre.

`SourceAssets/kotel-detail/KotelStoneV1/manifest.json`, longest verified west-facing segment edge0:

- Endpoint A: [-15127.515,11907.933]cm; B: [-14450.015,15836.433]cm.
- Midpoint M: [-14788.765,13872.183]cm; outward/plaza normal N=[−0.9854528733,0.1699489173].
- Section ray: XY=M+tN. Positive t faces the plaza; negative t enters the Mount. Tangent=[0.1699489173,0.9854528733].

Concrete camera framing candidates:

- Plaza XY at t=1000: [-15774.218,14042.131]. Ground-trace here plus168cm for an actual walking-eye view; aim at the facade midpoint at the same height (yaw about−9.79°). Do not guess plaza floor Z from facade bounds.
- Interior deck XY at t=−1500: [-13310.586,13617.259]. Source triangle18 covers this point at Z0. Candidate eye Z168, aiming west toward M (yaw about170.21°). Native capsule/clearance must pass first; source deck coverage does not exclude retained buildings or other obstructions.
- An elevated diagnostic section can use those same XY ends with eye Z1000 and aim toward M,Z0 to inspect retaining top/deck relationship. Label this an elevated inspection, not a walkable visitor viewpoint; validate actual camera clearance before capture.

## Demonstrated source geometry fact

I tested each section point against the **actual triangle vertices** of `SourceAssets/FutureMountV1/mount-platform.mesh.json` using oriented XY edge tests. The deck has no covering triangle at t=0,−100,−300,−600,−1000cm. It does cover t=−1200 and−1500 (triangle18),−2000 (triangle156),−3000 (triangle22). Thus this source deck stops somewhere between10m and12m behind this facade segment; it is not joined directly to the prayer-facing wall plane by the platform surface mesh itself.

This is **not proof of an open hole**: retained Western Wall footprint/thickness, protected buffers, other structure or terrain may occupy that intervening strip. It is a precise candidate section requiring reconciliation. Inspect surface triangle18's boundary against the preserved source component7085, skirt mesh, retained terrain and any Kotel-cut replacements. Do not fill the strip blindly or cover the preserved exterior facade.

The prior native inventory confirms the platform source is placed at identity and Z0, while Kotel overlays are separately placed. That supports these source coordinates but does not establish the latest map's visibility/collision. `Scripts/capture_kotel_detail_review.py:135–163` already uses this same longest-face method and requires three ground traces plus camera sweep; reuse that safety approach. The next useful evidence is one matched plaza view, one interior-deck view and an overhead section showing which actual mesh spans t0..−1200.

No inference about the3000-amah precinct or any future retaining-wall height is made. Current metric context and the book-derived Temple court envelope remain distinct.

## Subsequent native section evidence

Root inspected actual PIE image `SourceAssets/visual-review/runtime-diagnostic-20260908T151842Z.png`, captured at camera[-17000,14254,1800]cm, pitch−25°, yaw−9.79°, FOV70°. Root reports a detailed masonry face, broad stone coping/ledge, a second thin raised rear edge and plain platform behind it. No obvious open void is visible at this section. This supports the earlier caution: absence of the platform surface mesh alone does not demonstrate an unfilled gap. No geometry repair is authorized by that source-only inference.

Root's visual assessment still identifies a very dark broad facade shadow, repeating brown masonry appearance and unfinished plain paving. These are visual review findings, not proof of structural failure. `native-frontend-flight-20260908T151801755484Z.json` records main unchanged and PIE ended. This is one view, not collision testing, a complete retaining-wall survey or full-perimeter acceptance. The worker did not independently run PIE or alter geometry.
