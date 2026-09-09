# PilgrimRigV3 walk cycle re-authored - receipt

Generated 2026-09-09T23:16:30Z by `Scripts/rewalk_pilgrim_v3.py --build`.
Offline: no editor launched, no build run, nothing imported or cooked. Nothing
here is an in-engine acceptance, a render, or a performance result.

## What changed

`A_Pilgrim_Original_Walk` in all 9 PilgrimRigV3 bodies. Same 27 joints,
same 1.2 s cycle, same 100 steps/min cadence, same rest pose, same geometry.
The run asserts it: every position, colour, joint-index, weight, index and
inverse-bind block, plus the rest pose and the joint names, comes out
byte-identical to the shipped GLB, and normals match to 1e-06 (they are
summed over per-vertex face sets and CPython randomises string hashing per
process, so their last bit is not reproducible between runs). The ONLY difference
in these files is the walk animation. Idle, PhotoCamera and PhotoPhone are
untouched. The walk is now exported at 60 fps instead of 30, because its stance
rockers are curved and glTF/UE keys are linear - at 30 the chords cut the corner
off the heel and toe rolls and the planted foot picks up measurable drift.

Authoring: `Scripts/pilgrim_walk_v2.py`, called from `create_pilgrim_v3.pose()`.
The previous motion is kept verbatim as `create_pilgrim_v3.walk_pose_v1()` so the
shipped clip stays reproducible.

## The diagnosis, re-derived rather than trusted

Measured off the shipped `meshes/*.glb` before anything was changed, by the same
tool that measured the new ones. The handed-down numbers reproduce:

| handed down | re-derived here | agrees |
|---|---|---|
| step length 32.0 cm | ankle excursion 32.00 cm, peak foot separation 32.00 cm | yes |
| implied ground speed 53.3 cm/s | 2 x excursion / cycle = 53.33 cm/s | yes |
| pelvis vertical bob 0.50 cm | 0.50 cm | yes |
| foot lift 5 cm | 5.01 cm | yes |
| stance plant: NONE | 4.57 cm of drift with the sole flat on the floor | yes |
| cycle 1.2 s, 100 steps/min | 1.2 s, 100.0 steps/min | yes |

Three ways of asking for the old clip's step length - ankle excursion, peak foot
separation, and the speed implied by its own plant - all return 32 cm, and they
agree only because there is no plant: with both feet on pure counter-phase
sinusoids the foot's travel and the body's travel are the same curve. On a real
gait they separate, which is why the table below carries all three.

## The measurement

Forward kinematics over the GLB joint hierarchy, sampled the way a player samples
it (glTF LINEAR: lerp on translation, slerp on rotation), at 240 Hz.
`Scripts/measure_pilgrim_walk.py`. Identical method and identical definitions for
both columns. All 9 variants measure identically (before: True,
after: True), so one row of numbers describes the whole set.

| measured | before | after | unit | natural human |
|---|---|---|---|---|
| step length | 35.98 | 71.93 | cm | ~73 = 0.41 x stature |
| implied ground speed | 59.97 | 119.89 | cm/s | 130-145 |
| pelvis vertical bob | 0.5 | 3.99 | cm | 4-5, at TWICE stride frequency |
| pelvis lateral sway | 0 | 4.4 | cm | 4-5, at stride frequency |
| foot lift (swing) | 5.01 | 12.01 | cm | ~12 |
| STANCE PLANT: foot-flat drift | 4.572 | 0.019 | cm | 0 - the foot must not move |
| stance plant incl. touchdown/lift-off | 4.572 | 0.786 | cm | 0 |
| arm swing (hand fore-aft) | 12.35 | 42.4 | cm | 30-45 |
| arm-to-leg phase | 90 | 165.9 | deg | 180 = counter-swing |
| shoulder girdle yaw | 0 | 9.96 | deg | 8-12 |
| pelvis yaw | 0 | 8 | deg | 6-10 |
| trunk counter-rotates pelvis | False | True |  | True |
| stance duty factor | 0.566 | 0.618 |  | 0.58-0.62 |
| double support | 0.132 | 0.236 | of cycle | 0.16-0.24 |
| cycle | 1.2 | 1.2 | s | 1.2, keep |
| cadence | 100 | 100 | steps/min | 100, keep |
| - ankle fore-aft excursion | 32 | 78.36 | cm | step length / duty |
| - legacy 2 x excursion / cycle | 53.33 | 130.61 | cm/s | (diagnosis metric) |
| - mean pelvis height | 95.8 | 93.4 | cm | (98.0 standing) |
| - lowest sole point | -0.012 | -0.03 | cm | 0, never below |

## The stance plant, which is the one that matters

"Stilting" is a foot that never stops. The old clip drove both ankles as
counter-phase sinusoids, so at no instant was either foot still: against the
best-fit ground speed the planted foot slid **4.57 cm** while flat on the floor,
i.e. it skated ~9 cm every step no matter what speed the actor was driven at.

The new clip authors the stance foot as a rigid plate whose footprint is fixed
and which rotates only about points that are themselves on the ground (heel
rocker -> foot flat -> toe rocker). Rotating a body about its own contact point
cannot slide it, so the plant is exact by construction and the measurement
confirms it: **0.019 cm** of world-space drift while the sole is flat, against
4.572 cm before. That residual is glTF linear-key chording at 60 fps,
not motion.

Contact thresholds do not rescue the old clip and are not what rescues the new
one - drift is swept over the threshold rather than reported at one value:

| contact threshold (cm) | before: drift | before: fitted speed | after: drift | after: fitted speed |
|---|---|---|---|---|
| 1.00 | 6.464 cm | 53.58 cm/s | 3.485 cm | 119.28 cm/s |
| 0.50 | 5.334 cm | 57.35 cm/s | 1.771 cm | 119.72 cm/s |
| 0.20 | 4.572 cm | 59.97 cm/s | 0.786 cm | 119.89 cm/s |
| 0.10 | 4.04 cm | 61.99 cm/s | 0.602 cm | 119.94 cm/s |
| 0.05 | 3.634 cm | 63.48 cm/s | 0.219 cm | 119.98 cm/s |

Read the last two columns: as the threshold tightens the new clip's drift
collapses toward zero and its fitted speed converges on the authored 120.00 cm/s,
because there is a real plant to find. The old clip's drift bottoms out at 3.6 cm
and its "ground speed" wanders from 53.6 to 63.5 cm/s, because there is no plant
to fit and every window is a different piece of a sinusoid.

## The number to change in C++

    Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashResidentCharacter.h:40
        constexpr double MeasuredWalkClipGroundSpeedCm = 53.33;   ->  120.0

    Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashResidentPopulation.h:40
        double WalkClipGroundSpeedCmPerSec = 53.33;               ->  120.0

    Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashResidentPopulation.h:161
        double DefaultWalkClipGroundSpeedCmPerSec = 53.33;        ->  120.0

NOT EDITED HERE - another agent has changes in flight in
MikdashResidentPopulation.cpp. `MikdashResidentPopulation.cpp` itself carries no
literal; it reads `DefaultWalkClipGroundSpeedCmPerSec` (lines 262, 266, 386, 467)
and the per-variant override (lines 419-421), so the three declarations above are
the whole change. Note line 419-421 gates the per-variant value to
`> 1.0 && < 400.0`; 120.0 passes.

The default (V2) rig plays the same authored motion and therefore needs the same
number, but only once its own GLB is re-exported - the V2 source is not touched
by this run.

## Honest limits

* **The rig's leg is 6.9 cm too short.** `skeleton()` puts `thigh_*` at z = 88
  and the ankle at z = 6, so hip-to-ankle is 82.0 cm on a 179.4 cm figure =
  0.457 H, where `create_pilgrim_v3.PROPORTIONS` itself asks for a 0.53 H hip
  joint. A 72 cm step at 100 spm needs ~78 cm of fore-aft ankle travel and an
  82 cm leg can only reach that by carrying the pelvis lower and the stance knee
  more bent than a real walker: mean pelvis 93.4 cm against 95.8 in the old
  clip and 98.0 standing, mid-stance knee ~32 deg against a real 15-20 deg. Under
  a tunic at crowd distance that reads as a walk. Raising `thigh_*` is the real
  fix and it is a geometry change, out of scope for a clip re-author.
* **That is also why the ground speed is 120 and not 135 cm/s.** At a fixed 1.2 s
  cycle, speed is step length x 2 / 1.2 and nothing else; 135 cm/s would need an
  81 cm step, which this leg cannot reach without a visible crouch.
* **No toe joint in the skin.** The mesh weights the whole sandal sole to
  `foot_*` and gives `ball_*` no weight, so the foot is one rigid plate and the
  forefoot rocker has to pivot on the toe tip instead of rolling over the ball.
  Weighting the toe box to `ball_*` would buy a real MTP break - again a rig job.
* **Idle and Walk no longer stand at the same height.** Idle keeps the pelvis at
  its 98.0 cm rest; the walk carries it at 93.4 cm mean, so an Idle -> Walk
  transition sinks the hips ~4.6 cm where it used to sink ~2.2. Cross-blend it
  (0.2-0.3 s is enough); do not cut.
* **The "before" step length reads 35.98 cm in the table, not 32.0.** Same
  clip, stricter definition: the table's step length is derived from the clip's
  own plant (fitted ground speed x cycle / 2) at a 2 mm contact threshold, and on
  a clip with no plant that fit lands wherever the window happens to sit. The
  32.0 cm of the original diagnosis is the ankle-excursion row, which reproduces
  exactly. Both are in the table; neither flatters the old clip.
* **The old arms were a quarter cycle out.** `armToLegPhaseDeg` was 90 on the old
  clip: the right arm reached its extreme when the right leg was at mid-swing, not
  when it was forward. A metronome, not a walk. It is 166 now - not the textbook
  180 because the new foot track is not a sinusoid and its fundamental phase is
  skewed by the rockers, while the arm is a clean cosine.
* Not measured here: anything in engine. No import, no retarget, no cook, no
  frame time, no visual acceptance. The clip must be RE-IMPORTED for any of this
  to reach the game; the existing `A_Pilgrim_Original_Walk` asset still carries
  the old motion.

## Files

Written under `SourceAssets/characters-review/PilgrimRigV3/walk-v2/`:

* `meshes/*.glb` - 9 re-exported bodies (new walk, identical geometry)
* `walk-measurements.json` - every number above, plus per-variant hashes and the
  full before/after measurement records
* `WALK-V2-RECEIPT.md` - this file

The shipped `meshes/*.glb` are NOT touched; they remain the evidence the before
column was measured from. `create_pilgrim_v3.walk_pose_v1()` still reproduces
their motion - checked this run over 37 samples x 27 joints, worst joint position
error 0 cm, which is float32 export precision. The old walk is therefore
recoverable from code, not only from those files.

| variant | new sha256 | previous sha256 | geometry |
|---|---|---|---|
| V3_Pilgrim_Man_Standard | `e362b72cc2c6f3e4` | `decf5cfebe49e6fc` | identical |
| V3_Pilgrim_Man_Heavy | `8591ab42761c5ba2` | `3114a1eed02f17ae` | identical |
| V3_Pilgrim_Man_Elder | `be5f80a99ea65e69` | `bdba5440feacbb5e` | identical |
| V3_Pilgrim_Woman_Young | `69cd152a92431354` | `2860a95c681e3354` | identical |
| V3_Pilgrim_Woman_Elder | `a8730f2c12c478fb` | `cb697508e8ef5251` | identical |
| V3_Pilgrim_Youth | `da41cc9a00c3aa2a` | `d4d1a5039b48c3b3` | identical |
| V3_Kohen_White | `fdee435d7247740c` | `f8afc7d6d6a6da81` | identical |
| V3_Visitor_Camera | `eef12a8a372ae9a5` | `64e3c84085894968` | identical |
| V3_Visitor_Phone | `791c75af639756e0` | `632399a074e2c734` | identical |
