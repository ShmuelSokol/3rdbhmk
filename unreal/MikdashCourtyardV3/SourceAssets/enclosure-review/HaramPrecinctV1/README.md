# Haram precinct S5 — packaged acceptance passed

The Candidate48 map opts into the frozen 66-point Haram outline. It retains the
Temple transforms and Z0, the restored Kotel plaza and the outside-city hide split.
Both sourced square readings remain implemented for maps that do not opt in.

The new native namespace is `/Game/MikdashV3/HaramPrecinctV3`. V1 was an unaccepted
pilot with missing OBJ normals; V2 exposed Nanite Auto fallback simplifying the
stair collision despite numeric error=0. Both pilots and checkpoints remain local.
V3 exports explicit flat normals and selects PercentTriangles=1 for collision
fallback. Native winding and upward paving normals are checked on import.
AccessV4 retains the closed AccessV3 stair geometry but uses existing triplanar stone.
The S5-01 close view exposed XY-only paving stretched on vertical risers; that pilot
is retained as failed finish evidence.

`plan.json` records 13 named mapped gate footprints, their derived projections and
offsets, 111,848.53 m² of paving, 586 local access treads and 39.26 m maximum retaining
depth. Gate widths, lintels, wall profiles, steps and paving are authored. These are
not surveyed gate dimensions or claims about current access permissions. The old
square approach actor is retired only in Candidate48. Its assets remain intact.
Entrance slabs bridge the 50 cm wall inset, including where inside terrain is cut
below an uphill gate. Seven old path meshes sit wholly inside the ring and stand
above the new finish; those originals hide with the northwest terrain in the built
state and restore in Modern/Overlay. Native bounds checks prevent outside road loss.

Nine existing city-wall batches crossed the new gate routes. Their originals remain
intact; local boolean passage twins live under `/Game/MikdashV3/HaramWallPassagesV1`.
Fresh verification compares the exterior area of every original triangle, all source
UV sets, normals, colours, material IDs and winding. New cut faces are authored caps
confined to the gate cutter planes. The built state uses twins; Modern/Overlay uses
the existing originals. A character's upward sweep identified this obstruction after
downward floor probes had passed; both kinds of checks are required.
The existing Mount platform surface and skirt also receive corridor-only cut twins,
retaining their surfaces elsewhere, including the accepted court. Their open meshes
use trim-inside rather than solid subtraction. Verification checks disjoint output
fragments and area against the cutter union, so overlaps between extended runouts
are counted once. All twelve twins preserve their source attributes outside cuts. The twelfth is a
street mesh straddling Council Gate: only its gate corridors are trimmed, preserving
the outside road. The packaged Council walk exposed it after 12 other routes passed.

The northwest terrain tile alone receives a new twin. `native-terrain-source.json`
is extracted from its actual saved source description, whose hash is pinned in the
plan. Frozen pre-import JSON differs slightly in position, normal and colour from
that native asset and is not an exact preservation baseline. All other terrain,
including the Kotel cut, is reused without editing.

Import validates each triangle by position and directed cyclic vertex order,
materials, collision mode and full-resolution collision fallback. Terrain readback
matches every source corner and every generated twin corner. Application checkpoints
the map, preloads assets before loading it, preserves unrelated actor fields, and
saves once at the end. Fresh verification runs in a separate editor process.

Offline surface tests sample 320 inside and 72,304 outside terrain stations; outside
height error is below 1e-12 cm. They also check actual paving/tread surfaces at runtime
probe locations and actual lintel headroom at nine stations per gate. Both runtime
targets compile; all 32 existing standalone math suites pass.

Final acceptance is recorded in `acceptance.json`, including container hashes,
three reviewed four-state GPU sessions, all 115 surface probes and all 13 packaged
character routes. Build: `Checkpoint-haram-S5-02-20260916T171759Z`; map SHA starts
`9daa88a1`. Fresh native verification finds 122 built and 20 phase-original actors.
Failed receipts remain alongside successful ones; raw engine logs stay local.

The first packaged build passed 12 routes and exposed the Council Gate street
obstruction plus stretched riser texture. Both were corrected before this final
acceptance. Reviewed views establish scoped S5 behavior, not whole-scene polish.
