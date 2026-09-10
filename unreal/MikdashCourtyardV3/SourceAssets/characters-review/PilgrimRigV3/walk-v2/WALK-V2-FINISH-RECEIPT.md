# walk-v2 finished: the Kohen Gadol, the neutral phase, and the pilot default

Generated 2026-09-10 by `Scripts/release_walk_v2_finish.py`. This closes the three items
`WALK-V2-IMPORT-RECEIPT.md` listed under "Still needing a human" as deliberately not done.
Everything numeric below was read back off the **REOPENED** map or a saved asset, never off a
source GLB. **Nobody has looked at the new walk in a frame** — with one exception, and that
exception is the most useful number in this document.

## What ran

| step | command | receipt |
|---|---|---|
| 1 | `-FinishMeasure` | `walkv2-finish-measure-20260910T013032732487Z.json` |
| 2 | `-FinishApplyAll` (Candidate48) | `walkv2-finish-apply-Candidate48-20260910T013156570573Z.json` |
| 3 | `-FinishApplyAll` (Main50) | `walkv2-finish-apply-Main50-20260910T013405677963Z.json` |
| 4 | `-FinishRevertAndReapply -FinishTarget=Candidate48` (revert) | `walkv2-finish-revert-Candidate48-20260910T013839046285Z.json` |
| 5 | `-FinishRevertAndReapply -FinishTarget=Candidate48` (re-apply) | `walkv2-finish-apply-Candidate48-20260910T014026412337Z.json` |
| 6 | `-FinishApplyAll` again, as an idempotent re-verify | `walkv2-finish-apply-Candidate48-20260910T014953791271Z.json` |
| 7 | `-FinishApplyAll` again, as an idempotent re-verify | `walkv2-finish-apply-Main50-20260910T015131653741Z.json` |

Steps 6 and 7 exist because **another agent was editing both maps concurrently**. Between this
run's Main50 apply and its final Candidate apply, Main50's bytes moved on disk (`039920b7…` ->
`4a32a648…`), and Candidate48's had moved once earlier too (`afefdd97…` -> `d4bb2c3c…`). Both
were someone else's saves, and both were outside the window of any run here -- every guard in
this document reported `otherMapsUnchanged: true`, so nothing here wrote across a map boundary.

Re-running the apply is the cheapest honest verifier, because it is idempotent: it reads the
three actors, finds every value already at the plan, computes `changed = False`, **saves
nothing**, and still performs the full reopen-and-readback. Both targets came back

    status: apply_no_change_needed        mapSaved: false

with the kohen on the WalkV2 clip at 119.95, neutral phase 0.285 on all six, and both
population defaults at 60.48. The other agent's re-serialization did not disturb any of it, and
each map's bytes on disk now match its own latest receipt. This is a stronger confirmation than
the original applies: an independent process reopened both maps from disk and found nothing to
change.

Three engine launches, not five: `-FinishApplyAll` and `-FinishRevertAndReapply` batch two
guarded passes into one process. Neither weakens a guard — each target still checkpoints,
saves, reopens and reads back on its own. The box runs ONE engine and three other jobs queue
behind it; the launcher waits for a fully clear process table (GUI `UnrealEditor` **and**
`UnrealEditor-Cmd` and `AutomationTool`) before starting, and waited out two other agents.

## The one number here that was observed in a frame

The Kohen Gadol's stilt was already measured, in PIE, before this run existed.
`SourceAssets/service-review/candidate-runtime-20260909T070801049654Z.json` is a 290 s PIE run
of his full candidate route. Differencing its **569** timestamped feet samples gives **196**
moving intervals whose median, p90 **and** max 2D speed are all **90.00 cm/s** exactly — he
translates at precisely `WalkSpeedCmPerSec`. The clip he was playing was fitted in engine at
**60.48 cm/s**.

    90.00 / 60.48 = 1.49

His feet slid forward under him by half again their stride, every step, for the whole route.
That is the stilt, observed rather than inferred.

## Acceptance 1: the Kohen Gadol, before and after, on each map

| | Candidate48 `RELEASE_KohenGadolService_Selected48_V1` | Main50 `RELEASE_KohenGadolService` |
|---|---|---|
| walk clip BEFORE | `…/V3_Pilgrim_Man_Standard/V3_Pilgrim_Man_Standard/SkeletalMeshes/V3_Pilgrim_Man_StandardA_Pilgrim_Original_Walk` (the OLD clip) | **null** |
| walk clip AFTER | `…/V3_Pilgrim_Man_Standard/WalkV2/V3_Pilgrim_Man_StandardA_Pilgrim_Original_Walk` | same |
| `walk_speed_cm_per_sec` BEFORE | 90.0 | 90.0 |
| `walk_speed_cm_per_sec` AFTER | **119.94999694824219** | **119.94999694824219** |
| clip / translation ratio BEFORE | 1.49 (skating forward) | 1.49, via the hardcoded fallback below |
| clip / translation ratio AFTER | **1.000** | **1.000** |
| body mesh resolved from | `configured_mesh` | C++ `MeshFallbacks[0]` |
| `use_grounded_movement` | true | false |
| clip on the body's skeleton | **true**, 73 keys, 1.2 s | **true**, 73 keys, 1.2 s |

`119.94999694824219` is 119.95 stored in a float32: `AMikdashServiceActor::WalkSpeedCmPerSec`
is a `float`, not a `double`. The receipt records the raw readback rather than the rounded
plan, and the comparison that accepted it is tolerant to 1e-3 for exactly this reason. 119.95
is the in-engine plant-fitted speed of the clip itself, not the header's round 120.0 — for
this actor the clip's own carried speed is the correct target, because nothing rescales it.

### How his walk is driven, and the one thing that IS hardcoded

`AMikdashServiceActor` shares **nothing** with `AMikdashResidentPopulation`. Grep for
`MikdashGait|ConfigureGait|GaitPhase|SetPlayRate|CadenceBias|WalkClip` across
`MikdashServiceActor.cpp/.h` returns **zero hits**. There is no `WalkClipGroundSpeedCmPerSec`
and no `WalkClipNeutralPhase` on the class. `UpdateBodyAnimation` does
`SetAnimationMode(AnimationSingleNode); SetAnimation(Desired); Play(true)` and **never sets a
play rate**, so the clip always runs at 1.0. `WalkSpeedCmPerSec` — an `EditAnywhere` float,
header default `90.0f`, serialised per instance — is therefore the *entire* lever, and it is
**not hardcoded**. No UnrealBuildTool was run and none was needed.

What *is* hardcoded: in `SpawnBody`, when the body resolves as
`EMikdashServiceBodySource::PilgrimRigV3` — which is what Main50 does, through
`MeshFallbacks[0]`, since its `configured_mesh` is null — a `ResolveClip` lambda loads
`.../V3_Pilgrim_Man_Standard/.../V3_Pilgrim_Man_StandardA_Pilgrim_Original_Walk` **by literal
path** whenever `WalkAnimation` is null or off-skeleton. That is why Main50's kohen, with no
clip set at all, still played the OLD clip. The lambda's *first* branch keeps a clip that is
already valid and on the body's skeleton (`retained compatible <path>`), so setting the
property overrides the hardcoded fallback. Reported rather than worked around, as asked.

### Why both numbers had to move together

    clip only, speed left at 90:   90.00 / 119.95 = 0.75   feet dragging backward
    speed only, old clip:         119.95 /  60.48 = 1.98   worse than today
    both:                         119.95 / 119.95 = 1.00

The script always writes the pair; it cannot write one without the other.

### The cost, stated plainly

He now walks at 120 cm/s instead of 90, so his authored loop shortens from **290.5 s to
266.9 s**. That is still inside the spec's own 180–360 s window
(`Scripts/release_kohen_service.spec.json`, `expectedDerivedPlan.loopSecondsWindow`), but the
spec's `actorProperties.walk_speed_cm_per_sec: 90.0` **no longer describes the actor**. The
spec file is deliberately NOT edited: `configure_service_body_v3.py` hashes it into its
verification receipts and editing it would invalidate them. The divergence is recorded here.

`start_on_begin_play` is **false** on both maps, before and after. He does not walk unless
something calls `StartService()` — `Scripts/probe_service_candidate48.py` does, which is how
the PIE numbers above exist.

## Acceptance 2: the neutral phase, measured IN ENGINE

Method: `WalkClipNeutralPhase` is the phase the walk clip is entered at when a body's own
`GaitPhase01` is 0 (`Phase = Frac(WalkClipNeutralPhase + GetGaitPhase01())`), and the pose it
should enter at is the neutral passing pose — the moment the swinging foot passes the planted
one and the two are level fore-aft. The clip is sampled through
`AnimPoseExtensions.get_anim_pose_at_time` in component space at **240 Hz**, the same call and
the same rate `release_walk_v2.py` fitted its gait numbers with, so these phases are
comparable to those. `d(t) = ball_r.y − ball_l.y` along component +Y; every sign change over
the **cyclic** sample ring is taken, linearly interpolated between bracketing samples.

| clip | keys | fitted speed | crossings | separation |
|---|---|---|---|---|
| **new** WalkV2 (all six cast variants) | 73 | 119.95 cm/s | **0.285034** (0.34204 s) and **0.785033** (0.94204 s) | 0.499999 |
| **old** V3_Pilgrim_Man_Standard | 37 | 60.48 cm/s | 0.250000 (0.300 s) and 0.750000 (0.900 s) | 0.500000 |
| V2 `PilgrimRigV2A_Pilgrim_Original_Walk` | 37 | 60.48 cm/s | 0.250000 and 0.750000 | 0.500000 |

**Written: 0.285**, on all six variants, on both maps, `0.25 -> 0.285`.

Three things make this trustworthy rather than merely produced:

* **The offline claim is confirmed exactly.** The offline GLB measurement said 0.285 / 0.785;
  the engine says 0.285034 / 0.785033. The engine and the offline pass agree, so there was
  nothing to overrule — but the value written is the engine's.
* **The method reproduces the stale number it replaces.** Run on the OLD clip in the same
  session it returns 0.250000 and 0.750000 to six decimals — precisely the 0.25 sitting in
  both maps and the 0.30 s / 0.90 s it was derived from. A method that could not rediscover
  the old value would not be evidence for the new one.
* **It converged and it is unanimous.** Re-measured at 960 Hz (1152 samples) the crossing is
  0.285034 — delta **0.000000**. All six cast variants read 0.285034; spread **0.0**. The
  script refuses if the six disagree by more than 0.01 of a cycle.

One honest note. The new clip's *lower* crossing is `left_passes_right`, where the old clip's
lower crossing was `right_passes_left`, so 0.285 enters on the opposite leg to 0.25. The lower
crossing was chosen because that is the convention the stale 0.25 came from. It is immaterial
either way: `GaitPhase01` is a per-person uniform random offset, so the distribution of entry
phases across the population is uniform regardless of which crossing is used.

## Acceptance 3: the pilot population and the default-body landmine

**What it points at:** `RELEASE_ResidentPopulation` still plays
`PilgrimRigV2A_Pilgrim_Original_Walk`. The V2 GLB was not re-exported by the re-author run, so
there is nothing to repoint it at. The other half of the choice was taken instead: its
per-actor speed is now the speed that clip **actually carries**, measured in engine.

| actor, both maps | `default_walk_clip_ground_speed_cm_per_sec` | `default_walk_clip_neutral_phase` |
|---|---|---|
| `RELEASE_ResidentPopulation` (pilot) | **120.0 -> 60.48** | 0.25 -> 0.25 (unchanged, and correct) |
| `RELEASE_PeopleV3Population` | **120.0 -> 60.48** | 0.25 -> 0.25 (unchanged, and correct) |

**The serialized value was 120.0, not 53.33.** Unlike the per-variant speed — which the import
receipt found pinned at 53.33 in the saved maps and which silently defeated the header change —
this field really did carry the header's new 120.0. So the over-drive was live in the data.

**And the clip carries 60.48 cm/s, not 53.33.** The header comment on
`MikdashGait::BaseWalkSpeedCm` says the old clip was "32.0 cm of step length = 53.33 cm/s";
that is the offline source-file figure. Measured in engine by plant-fitting, the V2 clip and
the old V3 clip are the same motion to the digit — 37 keys, 60.478 cm/s, 36.287 cm step,
4.4025 cm plant drift, crossings at 0.25/0.75. The real over-drive was therefore
**120.0 / 60.48 = 1.98x**, not the 2.25x that 53.33 implies. Both numbers are now the measured
one. The neutral phase 0.25 was already right for this clip and is left alone — measured, not
assumed.

### Evidence: how many bodies actually use it

Zero, today — but one boolean away from five.

`ResolveBody` hands back the default body only when a person's `body.variant` is empty,
unregistered, or registered but unusable. All three conditions were checked, the third in
engine against the reopened actor's own assets:

| | Candidate48 | Main50 |
|---|---|---|
| people in the staged directory | 24 | 24 |
| people with no `body.variant` | **0** | **0** |
| directory variants with no usable registration | **none** | **none** |
| variants refused by `ResolveBody`'s own tests | **none** (all 6 pass) | **none** (all 6 pass) |
| **people that would take the default body** | **0** | **0** |
| people that would take a variant body | **24** | **24** |

Directory census, identical on both maps: Man_Standard 5, Woman_Young 5, Man_Heavy 4,
Woman_Elder 4, Man_Elder 4, Youth 2 — exactly the six registered on the actor. The believed
bodies-V3 outcome is now **observed**, off the directories and the reopened actor, not assumed.

The only bodies that *can* read the default gait numbers are the pilot's five **placed** ones,
because `BindConfiguredBodies` never consults `BodyVariants` at all — it assigns
`Plan.WalkClipGroundSpeedCmPerSec = DefaultWalkClipGroundSpeedCmPerSec` unconditionally
(`MikdashResidentPopulation.cpp:262`). Those five were retired on 2026-09-09: this run reads
back `activate_reviewed_pilot_on_begin_play = **false**` and all five bodies present but hidden
with collision off, on both maps. `spawn_authored_people_on_begin_play` is **true** on
`RELEASE_PeopleV3Population`. So the 1.98x over-drive was unreachable in play — and it is
corrected anyway, because "unreachable" here means one boolean away.

## Guards on every run

* Refuses a wrong project directory, a live PIE world, dirty packages, and more than one live
  `UnrealEditor` process (a zombie makes `save_current_level` return False with no symptom).
* Checkpoints the `.umap` before touching it, hash-verified against the file on disk:
  `ReviewCheckpoints\WalkV2Finish-<target>-<stamp>\BeforeWalkV2Finish.umap`.
* Hashes every pre-existing clip, skeleton, the V2 clip, the kohen's fallback mesh and both
  maps before and after. **`protectedChangedExcludingThisMap` is empty on every run**: this
  touched no `.uasset` at all, no GLB, no old clip, no skeleton.
* Full scene snapshot (every actor, component, mesh, material, transform) before and after;
  refuses if anything outside the three named actors moved. `sceneChanges` is `[]` on every run.
* Hashes the OTHER map and refuses if its bytes move. `otherMapsUnchanged` true on every run.
* Refuses if the kohen has `AuthoredBody` set — `UpdateBodyAnimation` returns early on an
  authored body, so writing the clip would be a cosmetic no-op that reads like a fix. It is
  null on both maps, so the refusal did not fire, but it is in the path.
* Refuses if the kohen's clip is not on his body's skeleton, if a variant is not already on its
  WalkV2 clip, if a population's `walk_animation` is not the V2 clip the default speed was
  measured from, or if the six variants disagree on the neutral phase.
* Save, reopen the map from disk, then read every number back off the reopened actors. Nothing
  is trusted from a setter's return value. Float comparison is tolerant to 1e-3 **only** for
  float32 storage; the raw readback is always what the receipt records.

## -Revert, actually run, not asserted

`-FinishRevertAndReapply -FinishTarget=Candidate48` executed the revert against the applied
candidate map (`walkv2-finish-revert-Candidate48-20260910T013839046285Z.json`). It reads the
newest apply receipt's `before` block, refuses if the variant ids or the kohen's body mesh no
longer match, and restores it exactly. After save **and** reopen the map read back:

    kohen walk  = …/V3_Pilgrim_Man_Standard/V3_Pilgrim_Man_Standard/SkeletalMeshes/…_Walk (old)
    kohen speed = 90.0
    neutral     = 0.25 on all six
    pilot dflt  = 120.0

— the pre-apply state, to the field. The candidate map was then re-applied in the same process
so it is left in the intended state.

Same honest caveat as the import receipt: revert restores property VALUES exactly, not `.umap`
bytes. UE re-serializes on save. The byte-exact original is the checkpoint copy under
`ReviewCheckpoints\WalkV2Finish-Candidate48-20260910T013156570573Z\BeforeWalkV2Finish.umap`.

## Final state, read off the reopened maps

| | Candidate48 | Main50 |
|---|---|---|
| kohen walk clip | `…/WalkV2/V3_Pilgrim_Man_StandardA_Pilgrim_Original_Walk` | same |
| kohen speed | 119.95 | 119.95 |
| variant walk clips | WalkV2 on all 6 | WalkV2 on all 6 |
| variant ground speed | 120.0 on all 6 | 120.0 on all 6 |
| variant neutral phase | **0.285 on all 6** | **0.285 on all 6** |
| population default speed | **60.48** on both actors | **60.48** on both actors |
| population default neutral | 0.25 on both actors | 0.25 on both actors |

To undo either: `-FinishRevert -FinishTarget=<Candidate48|Main50>`.

## Still needing a human, and what is NOT verified

* **Nobody has looked at the new walk in a frame.** Every number above except the 90.00 cm/s
  PIE translation is a static readback off a saved asset or a reopened map. No PIE was run by
  this script, no render, no cook, no frame time.
* **The kohen's fix is unobserved.** The 1.49 ratio was measured in PIE; the 1.00 that replaces
  it is arithmetic over two readbacks. Re-running `Scripts/probe_service_candidate48.py` would
  produce the matching observation — it already emits the timestamped feet samples that the
  1.49 was derived from, so the comparison is a re-run away and would close the loop properly.
* **Main50's kohen has no `idle_animation` set** (`idleClipSkeleton` reads null). At runtime the
  same hardcoded `ResolveClip` lambda loads the OLD idle by literal path. The idle motion was
  not re-authored so this is not a stilt, but Main50's kohen and Candidate48's kohen resolve
  their idle differently and only one of them is explicit. Out of scope here; flagged.
* **The Idle -> Walk height step is still unaddressed.** Idle holds the pelvis at 98.0 cm, the
  new walk at 93.4, so the transition sinks the hips ~4.6 cm. It wants a 0.2–0.3 s cross-blend.
  Nothing in this run touches it, and the corrected neutral phase does not help it.
* **The kohen walking at 120 cm/s is an engineering consequence, not an authored choice.** It
  is a normal adult walk, but it is faster than the 90 someone chose for a Kohen Gadol in
  service. The only ways to make him slower *without* re-introducing the skate are to author a
  slower clip or to give `AMikdashServiceActor` the play-rate matching the resident population
  already has. Both are real work and neither was done here.
* Everything in the re-author receipt's "Honest limits" still stands: the rig's leg is 6.9 cm
  short, there is no weighted toe joint, and 120 cm/s rather than a natural 135 follows from
  that leg length.
