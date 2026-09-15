# Physical walk across the K2 excavation edge

15 September 2026. Offline plan only; no native process or code/asset change.
Use the coordinator's serialized packaged NullRHI harness and existing memory
guards. NullRHI can test character collision; it supplies no rendered acceptance.

The current visual closure is NoCollision. Its presence therefore does not make
this 3.62 m retaining edge walkable or prove that a visitor cannot enter it.
Run the same route with closure enabled and with `-MikdashDisableKotelClosure`;
require the initial closure diagnostic to pass and report the requested mode.
Any physical difference needs investigation of state/collision readback, because
the closure itself is not intended to affect character movement.

## Exact edge and approach

Use the boundary hit already measured from K2, but cross perpendicular to the
actual rectilinear boundary rather than following an approximate camera yaw:

```text
inside start XY (-22187.940, 19383.62484)
boundary XY     (-22487.940, 19383.62484)
outside target  (-22787.940, 19383.62484)
direction       west, yaw 180 degrees, pitch 0
```

This is a 600 cm straight path, 300 cm on each side of the union boundary.
`closure-study.json` identifies exterior edge 106, source triangle 279, segment
(-22487.94,19250) to (-22487.94,19500), cavity normal (+1,0,0), canonical
triangles 222/223. At this Y the path crosses inside that segment, away from its
endpoints by at least 116 cm. It is an exterior union edge, not an internal deck
level boundary or stair footprint.

Source-derived heights in centimetres:

- Upper paving top inside: -984.594; cut underside: -1034.594.
- Retained terrain at boundary: -622.593235, a 362.000765 cm rise above paving.
- Retained terrain at outside target: -490.593242.
- Original terrain at inside start: -754.593228; this original surface is cut
  down in V3 and must not be mistaken for the intended inside walking floor.
- Along this segment, source triangle 279 gives
  `groundZ = -622.593235044541 - 0.4399999755859375*(X+22487.94)`.

The exact source triangle has vertices (-24124.515625,19972.431640625,97.5),
(-21624.515625,17472.431640625,-1002.4999389648438), and
(-21624.515625,19972.431640625,-1002.4999389648438). Its Y coefficient is
exactly zero. Its XY domain is the intersection of `X<=-21624.515625`,
`Y<=19972.431640625`, and `X+Y>=-4152.083984375`. The entire rectangle
X[-22900,-22075], Y[19308.62484,19458.62484] lies inside this triangle;
therefore a +/-75 cm Y tolerance is valid across the planned route. Check the
domain before applying this plane to farther samples; do not extrapolate it
indefinitely westward. This coefficient supersedes the earlier tiny slope
transcription error (about 0.000015 cm at a 300 cm offset).

The rise is much larger than the previously logged walker MaxStepHeight=55 cm.
The high side slopes about 23.75 degrees in this travel direction, but that does
not turn its 362 cm vertical boundary into a climbable ramp. Do not jump, fly,
teleport across the edge, or lower the collision threshold to obtain a pass.

Input provenance is pinned in `closure-study.json/sourceHashesSha256`:
566-triangle source terrain SHA256
`abc6152db1d10b80476870ac843bfde232b30ccac90733994e3ecf743579095a`;
959-placement deck plan
`f3483bff589169159bc99200761d90230e4726ec248226c948f0ead6dedca69c`;
saved V3 terrain
`ed26cb8d2710b4a425985fed31c095fe59c13cc1f0068454bc7d53092aa78211`.
Heights were recomputed through `measure_boundary.ground_at` and deck rectangle
coverage, not a smooth terrain approximation. Both snapped and unsnapped deck
unions contain the inside start; neither contains the outside target. The
unsnapped boundary differs slightly from the snapped plane, so do not diagnose
the exact plane's inclusion bit as a physical crack.

## Existing NativeWalkProbe specification

For the previously verified BP_MikdashWalker capsule half-height of 96 cm, use:

```text
label=KotelEdgeOut;state=MODERN;start=-22187.94:19383.62484:-878.594:180:0;wp=-22787.94:19383.62484;delay=10;timeout=12
```

Pass this as the quoted value of `-MikdashWalkProbe=...` in the coordinator's
owned process, together with `-nullrhi -MikdashKotelClosureDiagnostic` and fresh
isolated save/settings prefixes as in `Scripts/Test-KotelStairRuntime.ps1`.
This start Z is capsule centre: paving + 96 cm half-height + 10 cm initial drop.
It is not feet Z or camera Z. Require the native start log to report the same
capsule dimensions (previously radius 34, half-height 96). If dimensions differ,
stop and derive the centre from the actual half-height before a fresh run.

The probe restores character collision, disables cheat flying, teleports once,
enters MOVE_Falling and holds for one second before steering. Its first grounded
samples should have feet near -982.4 cm (deck top plus the normal roughly 2 cm
character-floor clearance), with SM_PlazaV1_DeckTile as the floor or a specifically
identified equivalent deck collision proxy. A practical precondition is feet
within 5 cm of paving and grounded before steering. Landing on PrecinctCut terrain
near -754.6 cm, another actor, or no floor invalidates this as an isolated
deck-to-retained-terrain crossing; record it as a separate collision-layer finding.

## Required evidence and result categories

`MikdashPlayerController.cpp:775–915` provides samples every 0.5 game seconds,
landed events, current-floor component/owner/mesh, and stuck events. A stuck event
requires steering with speed below 10 cm/s for 1.5 s and performs a 150 cm capsule
sweep on ECC_Pawn along the pawn's actual forward vector. Initial yaw 180 aligns
that vector with this straight route. A stuck sweep is not a continuous forward
trace, and a nonblocking sweep is not proof of an unobstructed complete path.

Preserve every raw sample/event and the start/configuration/closure readback.
Classify the observations, rather than returning a generic route pass:

- **Blocked retaining edge:** correct initial deck floor; repeated stuck events
  near the edge; actual X never crosses to the high side; grounded feet remain at
  deck height. Require a blocking sweep with named actor/component/mesh, impact
  point and normal to identify what blocks it. A blocker elsewhere along the
  approach is an obstruction finding, not acceptance of this boundary.
- **Enters beneath high terrain:** actual X crosses west of the plane while feet
  remain below the interpolated terrain surface. Once X is at least one capsule
  radius plus 10 cm west of the plane, this is clear penetration of the intended
  solid hillside region, even if a lower collision surface supports the walker.
  Record the supporting mesh; never call that a walkable terrain transition.
- **Falls off/through:** loss of floor and negative vertical velocity after the
  crossing, followed by landing below the deck or remaining in MOVE_Falling at
  timeout. Retain fall-start/landing events and final mode; longestFallCm updates
  only on landing and can miss an unfinished fall. FallingSamples and grounded
  min/max alone do not bound the lowest falling position.
- **Unexpected climb:** real target reach and sustained grounding near the
  terrain height at the *actual* final XY. Require the recorded floor identity
  and trajectory before attributing this to a ramp, proxy, collision hull or
  depenetration. A 362 cm step is not expected to pass the 55 cm step limit.
- **Inconclusive:** wrong initial floor/state, missing logs, memory abort,
  unidentified blocker, or inadequate trajectory samples. Do not infer collision
  from visual closure acceptance.

The implementation silently advances a waypoint after its fourth stuck event.
Its `done reached=1/1` is therefore not evidence of crossing. Require the actual
`MIKDASH_WALKPROBE reached ... wp=0` event, actual X on the requested side and
correct height/floor for any reach claim. That event itself uses only a 75 cm XY
tolerance and does not test Z. Use the terrain equation at actual XY, allowing
normal floor clearance; do not compare every endpoint to the target's Z alone.
Blocked/time-out is an informative outcome here, not permission to skip ahead.

If needed after this direct test, a separate reverse run can expose an unguarded
drop: start outside at (-22787.94,19383.62484), centre Z=-384.593242
(local terrain+96+10), yaw 0, target (-22187.94,19383.62484). Require actual initial
grounding near source terrain before interpreting it. The expected potential
drop at the lip is approximately 362 cm; this optional reverse test is not an
accessible stair route or a substitute for the primary outward test.

## Stair control with existing native evidence

Reuse the exact, independently replayed ascent in Test-KotelStairRuntime.ps1:

```text
label=KotelClosureStair;state=MODERN;start=-17432.4:16006.8:-1110:175.49:-8;wp=-19027.4:16132.7/-20323.4:16235.0/-21000.0:16287.0;delay=10;timeout=40
```

This travels westward from the lower prayer-plaza side toward the upper deck.
The pinned deck plan has lower top -1234.594 and upper top -984.594; the flight
uses nine 25 cm risers/treads to -1009.594 and the final upper-deck riser, with
a decorative head row at -985.594. The plan contains 100 cm tread runs; these
are qualitatively different from the 362 cm exterior vertical edge.

Actual receipts `stair-20260915T172339339Z.json` (closure enabled) and
`stair-20260915T172448192Z.json` (disabled) passed, with genuine reached events
0,1,2, zero stuck events, and final SM_PlazaV1_DeckTile feet -982.6/-982.4 cm.
Require those same events and final grounded floor/height on a new control.

Important existing limitation: this control starts at capsule-centre Z=-1110,
so initial nominal feet are -1206, not the lower deck. Both receipts first land
at feet -1170.8 on SM_JerusalemTerrain_07_08_FutureMountCut_PrecinctCut, then
drop about 95 cm to the lower deck before ascending. Source terrain at that
start is -1172.700953. Preserve that fact; the old control proves ascent and
final arrival, not an initially clean lower-deck landing or all terrain-layer
collision policies. Its initial drop must not be confused with an edge fall.

Do not change the control route silently to suppress that observation. The
new outward edge probe has its own explicit deck-floor start precondition.
Neither successful stair replay nor unchanged closure-on/off movement alone
certifies collision safety along the whole 562-edge cut perimeter.
