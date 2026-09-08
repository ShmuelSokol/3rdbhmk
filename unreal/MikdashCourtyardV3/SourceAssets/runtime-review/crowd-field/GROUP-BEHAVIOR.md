# Background visitor groups — authored behavior, native acceptance pending

User direction: visitors generally arrive/walk together; only a minority walk alone.
This source batch applies to `AMikdashCrowdField` instanced background visitors. The
24 skeletal residents retain their separate roles, missions, dialogue and routes;
this patch does not invent kinship or change a ritual/access rule.

## Implemented

- `bEnableVisitorGroups=true` by default. `IndividualVisitorRatio=.15` means 15% of
  **people**, not 15% of social units. The remaining per-zone population is divided
  deterministically into cohorts of 2–6. Tiny-zone rounding and refused seeds can
  change the achieved percentage; actual group/individual/refusal counts are exposed.
- A cohort has a stable identity derived from its first global instance index for a
  given seed/count/zone allocation, a leader, one zone/support plane, shared walking
  pace and shared standing/walking state. Per-person height, garment tint and idle/
  gait phase remain individual. Loose offsets include deterministic lateral variation.
- Formation spacing defaults to120 physical cm. A leader slows when the worst
  formation error exceeds100cm and waits at250cm. Followers can catch up at up to
  1.15 times the shared pace, then settle back. Distances do not scale with amot.
- Seed placement is transactional per cohort: all its members fit or all its slots
  are counted refused. Members must be in the same decoded zone, clear of protected
  polygons and other visitors, and on compatible sampled support (within55cm of the
  zone surface and within20cm of the leader's surface residual). Connections between
  leader and initial companions are also checked so a group is not seeded across a
  wall. The existing ground fallback/miss counter remains honest about missed traces.
- A spatial hash enforces80cm centre separation between all seeded background figures
  in group mode, including independent visitors and standing figures. Per-query work
  covers at most16 cells, each capped at64 occupants; no whole-population neighbor
  scan is used. Full/invalid entries or motion refuse instead of losing coverage.
- Walking uses continuous segment separation against neighbors, sampled zone/keep-out
  checks with physical capsule radius and sampling allowance, then a static-world
  capsule sweep (34cm radius,96cm half-height,3cm floor clearance). Only a successful
  move updates the hash and figure transform. Each move is at most100cm with the
  existing catch-up/time clamp; default speeds usually yield much smaller steps.
- A first obstruction away from the anchor puts a leader into Returning mode. A
  rejected return, or any obstruction within120cm of the anchor, explicitly pauses
  the party. Returning clears only after a successful arrival move. The formation
  heading changes only with successful leader movement, so an immobile turn cannot
  spin follower targets. Companions may settle into the paused formation through the
  same collision/separation checks; automatic detour/restart is not invented.
  They never jump to catch up. Group mode also
  removes the old far-edge reseeding teleport for independent visitors. If a leader
  or companion becomes invalid, the remaining group waits without identity swapping.
- Simulation still visits only the existing `UpdateBudgetPerFrame` round-robin slice.
  Group coordination scans at most6 members for each visited figure. Static capsule
  sweeps run at most once per permitted moving visit, never in an all-agent tick.
  Cohorts use their leader's LOD distance so members freeze/cull coherently.
- `bEnableVisitorGroups=false` retains the historical independent-flow diagnostic
  path. The mode is captured at rebuild; changing it does not reinterpret live arrays.

## Native inspection

Use a clean isolated candidate and build240 visitors first. Existing component counts
and refusal counters remain available. New reflected getters:

- `GetVisitorGroupCount`, `GetGroupedVisitorCount`, `GetIndividualVisitorCount`,
  `GetRefusedGroupCount` describe achieved placement.
- `GetVisitorSocialState(index)` exposes valid figure position, stable group identity
  (minus1 for an individual), member index and standing state for small sampled probes.
- `GetGroupSweepsLastFrame`, `GetGroupRejectedMovesLastFrame`,
  `GetGroupWaitVisitsLastFrame` report the last tick's work. Waiting visits are agent
  updates, not distinct groups. Each should stay at or below the update budget.
- `GetPausedVisitorGroupCount` and `GetVisitorGroupState(groupIdentity)` expose
  Forward/Returning/Paused state. An unavailable identity returns `Unavailable`.
- `GetCrowdSummary` includes grouping and last-frame counters.

Review ordinary walking, a deliberately delayed companion, wall/edge approach,
standing groups, both legacy50/selected48 geometry, and freeze-boundary behavior.
Record actual frame cost with the240-visitor probe before raising the count. The
original10,000-visitor target is not a measured safe performance setting for this
new query workload. Inspect refusal percentages; do not claim a complete population
from requested instance count when a narrow/dense zone cannot fit the formations.

## Limits and evidence

This remains scripted steering of frozen-pose background meshes. There is no navmesh
path search, animated conversation, skeletal group-role integration, or transfer of
these cohort identities into bus/gate queues. A blocked group may wait/turn or become
stuck; it must never bypass geometry. Static sweeps depend on real collision data and
do not provide dynamic collision with the player or the24 separate skeletal residents.
Walking retains traced flat support and, on slopes, adds only the fitted-plane height
delta to the current traced height. This preserves the initial trace/plane residual
instead of snapping to the plane. Non-finite inputs/results refuse movement. It is
still not fresh floor tracing at every footstep. Gate flow, bottlenecks, stairs, collision meshes,
long-running deadlock behavior and visual quality require native review.

`CrowdGroupMathTest.cpp` uses the production planner, steering, spatial hash and
zone/keep-out segment gate. Installed MSVC `/std:c++17 /W4 /WX`: **44,707 checks,
0 failures**. It covers exact population accounting and15% intent, deterministic
cohorts, varied physical spacing, leader slow/wait/regroup behavior, transactional
spatial moves,10,000 indexed figures, thin-wall/edge rejection and unchanged physical
constraints with48cm architecture. This worker ran no Unreal/UBT; these results do
not establish engine compilation, native obstacle behavior, frame rate or appearance.

The follow-up14 checks exercise successful-arrival-only return transitions, persistent
paused state at an obstructed anchor, frozen formation headings while blocked, safe
companion settling and finite/overflow-safe traced-height residual preservation.

Coordinator build finding: installed UE5.8 `UWorld` has
`OverlapAnyTestByObjectType`, not `OverlapBlockingTestByObjectType`. The seed guard
now uses the installed API (World.h:2385), conservatively refusing any static-object
overlap; per-step motion keeps `SweepTestByObjectType`. The original source receipt
is preserved as historical evidence, and the follow-up receipt supersedes its hashes.

Separate resident evidence reported by the coordinator during this batch:24 authored
profiles pass geometric decoding, but only15 native candidate residents walked and9
were refused by capsule checks. Those results concern the skeletal resident system,
not these unverified instanced cohorts. The candidate remains unpromoted.
