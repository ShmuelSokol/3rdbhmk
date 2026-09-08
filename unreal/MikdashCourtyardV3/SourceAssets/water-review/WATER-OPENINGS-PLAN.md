# Water openings preparation

Status: source-only audit helper; no cuts, native execution or visual acceptance. Root owns serial engine execution. `Scripts/release_water_openings.py` deliberately refuses `apply()`.

The existing release places water and masonry while preserving existing architecture. Its host exemption is an intersection allowance, not an opening. Flat court water surfaces are 26 cm below paving: priest court 599 vs 625, inner court 474 vs 500, outer court 274 vs 300. Kerbs are also 18 cm below paving. Current all-water placement cannot demonstrate an open stream.

The helper hashes the generator, architecture manifest and decomposed clearance evidence against the frozen geometry manifest. It reads actual COURT_ROUTE literals, including bed and cover flags omitted from exported simplified waypoints, without executing the generator. Host candidates use exact manifest asset names and retain section/contact evidence. Family-level host contacts still overselect repeated stairs; they are candidates, never deletion authority. Optional `audit_native()` inventories their actual component transforms, materials and collision profiles in the already loaded target. It refuses a game world or another map and never loads, saves, imports or changes an actor. Native API execution remains unverified.

## Why no boolean implementation is exposed

`release_fix_kotel_occlusion.py:562–630` demonstrates source DynamicMesh extraction, selected-triangle deletion, compaction and copy back. It is not a demonstrated closed-volume subtraction/capping implementation. Deleting intersecting triangles from a floor can remove huge floor spans and leave uncapped holes. Existing water clearance boxes describe masonry triangles (many zero-thickness bounds), not cavity solids. They must not be unioned into a broad bounding-box cutter.

## Required candidate construction

1. Freeze current main SHA, all source mesh/material hashes and numeric scene snapshot. Checkpoint outside Content. Duplicate main to a unique `WaterOpeningsReview_<timestamp>/Maps/Walkthrough`; create replacement assets only in that namespace. Require exact loaded candidate package before any mutation. No shared original asset writes.
2. Construct closed, watertight swept cavity solids from the actual resampled court cross-sections. Open sections extend through paving to air; covered sections stay below their explicit roof/slab. Preserve the ramp crossing and inner east range cover, gate jambs, stair supports outside the narrow conduit and non-host architecture. Review discontinuities where explicit bed values and coverage flags change; the generator's interpolation is not automatically a valid cutter design.
3. Match live host mesh identity and transform; intersect actual triangles with exact cutters. Subtract only supported intersections. Rebuild caps, normals, UVs and material indices. Verify unchanged triangles outside cutter, positive volume/manifold output and roof thickness. If a source is nonmanifold, refuse rather than widening the cut.
4. Create new collision matching each replacement cavity; retaining old simple convex collision seals the opening. Preserve walkable covered slabs and ledges. Check collision cooking and traces both inside the channel and outside it. Do not disable collision for an entire host.
5. Save/reopen candidate only. Verify source/main hashes unchanged, unrelated scene exact, render geometry and collision synchronized. Capture every court elevation, both covered crossings, stair cascades and mikveh openings; perform grounded walking tests before any adoption.

Far-field terrain is excluded by existing clearance and needs a separate exact terrain audit. The Yom Kippur mikveh surface at Z621 lies below priest-court Z625; its basin void also needs review. Other mikvaot must be checked independently, not assumed buried from this one example.

Current geometry records 50 cm per amah. The user-selected book scale is 48 cm, but the active architecture has not migrated. Do not apply .96 only to water; coordinate all architecture-related positions and cutters with the migration checkpoint while preserving people and metric geographic context.

## Invocation and validation

Offline stdout only: engine Python `Scripts/release_water_openings.py`. In a root-controlled native slot, import the module and call `audit_native()` with main already loaded; caller may store returned report outside protected assets. No automatic native entry runs. Python syntax and offline hash/route/host validation are checked separately; native validation is pending.
