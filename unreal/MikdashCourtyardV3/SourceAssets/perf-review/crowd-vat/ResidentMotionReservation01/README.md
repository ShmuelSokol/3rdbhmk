# Crowd movement reservation defect

This is a source-level defect reproduction, not runtime acceptance or a fix.
`reproduce.cpp` calls the production `SpatialIndex` directly. Exit zero means
the unsafe sequence was reproduced. It is intentionally outside the acceptance
test directory: future corrected behavior must not preserve this failure.

Two visitors start at (0,0) and (80,80) cm. Each plans a 99 cm straight segment:
the first toward (99,0), the second toward (80,-19). Both plans pass the existing
80 cm point-against-segment spacing test. At the same fraction 80/99 of their
movement interval, both rendered roots occupy (80,0). Committing their accepted
endpoints leaves them about 26.87 cm apart. The existing test then rejects both
90 cm moves directly away because it includes the already-overlapping start.

This establishes that accepted asynchronous paths can collide and become trapped.
It does not establish the exact trajectory of Runtime03 agents 10/47: the saved
five-second snapshots cannot reconstruct that trajectory. Their persistent
79.86437 cm separation is consistent with this failure mechanism, not proof that
this particular synthetic crossing happened in the game. Formation routing is
still an independent open defect.

The native VAT step currently commits the rendered root, relocates its spatial
index anchor, and checks a new look-ahead segment against other stored anchors.
`Relocate` deliberately omits another clearance test because refusing the commit
would leave the index behind the visible root. Adding a check there would conceal
the collision rather than prevent it. Lowering the separation limit, allowing an
unchecked escape, or snapping the root would also fail the release requirement.

A replacement must account for the neighbors' future motion and their stopped
endpoints. Merely comparing two velocities is insufficient: this tick loop can
replace a plan early, enter an idle hold, or immediately stop on freeze/cull.
Previously accepted neighboring plans must remain safe when that happens.
Follower steering also currently reads stored anchors rather than all members'
rendered positions at a common time.

Next implementation/acceptance requirements:

- Reserve movement over its actual lifetime; keep the spatial query bounded for
  10,000 visitors, including paths spanning spatial cells.
- Handle early replanning, rejected plans, idle holds, freeze/cull, and expired
  intervals without silently invalidating another visitor's clearance.
- Verify head-on, crossing, following, stationary, staggered-update, and stop
  cases against continuous relative-distance minima, including endpoint holds.
- Preserve the 80 cm spacing and world/ground/sweep gates. Do not replace a
  collision with universal paralysis: ordinary following must continue moving.
- Repeat Runtime03 and measure pairwise separation more frequently than five
  seconds; demonstrate sustained group travel, then test production populations
  and frame time before release adoption.

Compiler output, reproduction output, source hashes and verification results are
retained alongside this document. Native behavior and the packaged release have
not changed in this diagnostic step.
