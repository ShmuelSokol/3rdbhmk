# Somebody finally looked at the people. Verdict and frames.

Generated 2026-09-10 from the packaged build `C:\Mikdash\Builds\Checkpoint-cp11-20260910T080907Z`
(Development, map `/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough`,
cooked 08:12Z, i.e. **after** every walk-v2 apply). No editor was started, no map was written,
no UnrealBuildTool was run, nothing was committed. Two capture scripts were added:
`Scripts/capture_people_walk_frames.ps1` and `Scripts/capture_people_walk_movie.ps1`.

---

## The answer to "I want the people looking real, like, legit real people. not, like, figures stilting along."

**Half of it is done, and it is the half nobody could see until now.**

**The stilting is fixed.** I have it in frames, measured, in a running packaged build: a walking
resident's planted sandal stays on exactly the same flagstones — pixel for pixel, indistinguishable
from the pavement itself — while his body advances past it. That is a real walk. It is not a
skate, it is not a metronome, and the numbers in `WALK-V2-*-RECEIPT.md` survive contact with a
rendered frame.

**They do not look like real people.** At 3 metres they look like **hand-painted wooden
mannequins**. The face is two ink strokes and a blob moustache painted onto a smooth egg — one
dark dash for an eye with no eyeball, no lid, no socket; no ear, no mouth, no chin, no hair, no
skin texture. The only real geometry in the face is a wedge nose. The garments are flat blocks
of untextured colour with no weave, no folds and no wrinkles, and the over-tunic's edge is a
badly aliased alpha cutout that at conversational distance reads as torn paper. The body has no
deltoid, no collarbone, no chest and no waist; the arms are cylinders and the hips are a cone.

**And two things make it worse than "the bodies need art":**

1. **Most of the "crowd" is a field of frozen statues.** `MikdashCrowdField_0` is in the shipped
   level and it is not people — it is `SM_CrowdFigure_P0..P3`, four frozen **static mesh** poses
   in HierarchicalInstancedStaticMesh components, which cannot animate a limb by construction.
   A cluster of seven of them at ~25 m is **pixel-identical 37 s apart**. They are armless,
   faceless, single-colour bell shapes and several of them visibly intersect one another. Only
   the 24 `MikdashResidentCharacter` actors actually walk. The crowd field's own spec says so:
   *"These are instanced background figures... The 24 MikdashResidentCharacter actors remain the
   only individuals."*

2. **The Kohen Gadol is not in the shipped build at all.** See below. Not standing, not walking —
   absent.

**And the cruellest finding: the walk is almost invisible anyway.** Every resident wears an
ankle-length tunic that falls to a closed bell. From every angle where you cannot see below the
hem, the 71.9 cm step, the heel and toe rockers, the 3.99 cm pelvis bob and the real
double-support phase are all hidden under a skirt, and what the viewer sees is a cone gliding.
The one part of the new walk that reads at distance is the 42 cm arm swing.

---

## How the frames were taken, and the trap that cost two runs

**Photo mode pauses the world.** `UMikdashPhotoMode::Enter()` calls
`UGameplayStatics::SetGamePaused(World, true)` (`MikdashPhotoMode.cpp:412`) and `Leave()`
unpauses (`:491`). So the F2/F9 recipe in `Scripts/capture_vegetation_grove_frames.ps1` — which
is correct for architecture and vegetation — **cannot produce a motion sequence**: every
photograph is of a frozen world, and a set of them says nothing about a sliding foot. My first
nine-shot attempt (`cp11-deck-photomode-paused-crowdfield-*.png`) is exactly that mistake,
compounded by having been aimed into the crowd field, whose figures never move anyway.

The instrument that works is **`-dumpmovie -benchmark -fps=10`**: the engine writes every
rendered frame of the *running* world to `Saved/Screenshots/Windows`, and the fixed timestep
makes each frame **exactly 0.1 s of game time** however long it took to encode the PNG. Without
`-benchmark` the PNG encoder throttles the run to ~1.1 fps, so consecutive frames are ~0.9 s
apart — most of a 1.2 s stride, useless for reading a plant.

| run | camera (BugItGo, world cm) | frames | game time |
|---|---|---|---|
| court lane, resident at ~3.5 m | `3300 2434 380 -4 90 0` | 894 | 89.4 s |
| Kohen station 0 at ~4.2 m | `-3020 -300 1008 -6 135 0` | 131 | 13.1 s |
| Kohen, whole Ulam→Heikhal axis | `-2600 0 1050 -3 180 0` | 80 | 8.0 s |

Resident world positions were derived from `Content/Distribution/People/people-candidate48.json`
through the Selected48 decoder (fixed origin `-6200,0,0`, factor 0.96) and cross-checked against
the per-resident `decodedWaypoint0` in
`SourceAssets/runtime-review/people/resident-bodies-v3-verify-Candidate48-20260909T014551106415Z.json`.
One process at a time; the process table was checked before every launch, and one launch was
correctly refused because three `MikdashCourtyardV3` processes had survived a previous run's
cleanup (they were killed before continuing — worth knowing, it is a real leak in the recipe).

---

## 1. Do the feet stay planted, or slide?

**They stay planted. Zero measurable drift.** Method: anchor a 70×44 px patch on the planted
sandal and find its best integer (dx, dy) in the next frames. A planted foot is world-fixed, so
its patch must match at (0, 0) — the same test a bare flagstone must pass.

| anchor | +0.1 s | +0.2 s | +0.3 s |
|---|---|---|---|
| sandal, f0107 (t=10.7 s) | **dx 0, dy 0** (res 9.9) | **dx 0, dy 0** (res 14.3) | lost (foot lifts / hem occludes) |
| sandal, f0120 (t=12.0 s) | **dx 0, dy 0** (res 2.5) | **dx 0, dy 0** (res 5.2) | lost |
| sandal, f0132 (t=13.2 s) | **dx 0, dy 0** (res 4.7) | **dx 0, dy 0** (res 12.8) | lost |
| bare flagstone, same band (control) | dx 0, dy 0 (res 0.3) | dx 0, dy 0 (res 0.5) | dx 0, dy 0 (res 0.6) |

Three independent steps, and the planted foot is as world-fixed as the pavement. The search
resolution is ±1 px ≈ 0.36 cm at this range, so drift is **< ~0.4 cm over the 0.2 s of stance
that stays unoccluded**. The old clip skated **4.40 cm every step**.

`cp11-people-footplant-proof-3frames.png` is the picture of it: the same world-fixed crop at
t = 10.7 / 10.8 / 10.9 s, with fixed reference lines. The sole sits on the same two pebbles and
the same mortar joint in all three; the tunic hem behind it has visibly advanced.

**Honest limits.** The plant is only observable for ~0.2 s per step before the hem or the swing
leg hides it, so I confirmed the foot-flat phase, not the heel and toe rockers. And I never see
the forefoot break over the ball — the sandal is a rigid slab, exactly as the "no weighted toe
joint" limit predicts, but the tunic and the 0.1 s sampling mean I cannot call that a visible
defect either way.

## 2. Step length and cadence, read off the screen

Planted-foot screen positions along one pass: **1076 px** (t=10.3 s), **694** (11.45),
**517** (12.1), **146** (13.3), with two plants occluded in between. Fitting equal steps gives
**186 px per step over five steps, residual ≤10 px (5%)**, and a **0.6 s step interval →
100 steps/min**, which is the authored 1.2 s cycle exactly.

Silhouette height measured over five frames: 490–502 px, median **497 px**.

    step / stature  =  186 / 497  =  0.374   (range 0.371 - 0.384)
    authored        =  71.93 / 179.4 = 0.401
    natural human   =  ~0.41

That ratio is scale-free, so it does not depend on my camera calibration. The on-screen step is
about **7% short of the authored figure and 9% short of natural**. That is consistent with this
particular resident's `CadenceBias` sitting below 1.0 — `MikdashResidentCharacter.cpp:46-57` sets
`CadenceBias = 1 ± 0.07` and `PreferredWalkSpeedCm = ClipGroundSpeedCm * Scale * CadenceBias`,
while `MikdashResidentPopulation.cpp:169` sets `SetPlayRate(CadenceBias)`. **Pace and play rate
scale together, which is why the plant survives the per-person variation** — that is a good
design and it is working.

Converting to centimetres needs a calibration I do not trust to better than ±10% (my derived
camera geometry and the frame's own perspective disagree), so: step ≈ **63–67 cm** and ground
speed ≈ **105–112 cm/s** against the authored 71.97 cm / 119.95 cm/s. I am reporting the ratio
as the finding and the centimetres as an estimate.

## 3. Is the crowd varied, or is everyone the same height, gait and phase?

**The lockstep defect is gone.** Four separate residents crossed the same fixed camera during the
89 s pass. Their gait-phase peaks fall at **different** absolute frames mod one stride
(offsets 6, 8 and 10 of 12), so they are not stepping in unison, and their speed-to-height
ratios differ: **0.616, 0.645, 0.658, 0.856 /s**. The directory itself casts visual scales
**0.84–1.04** across six body variants, and the reopened-map readback confirms 24 of 24 residents
take a variant body, none the default.

**Caveat I have to state:** foot-spread autocorrelation returned a **1.2 s stride period for all
three** residents it could fit (r = 0.87, 0.69, 0.71). At 0.1 s per frame I cannot resolve the
authored ±7% cadence spread (11.2 to 12.9 frames all round to 12), so I am confirming **phase
and pace variety, not cadence variety**. Do not read that 1.2 s as evidence of a shared
metronome; read it as an instrument limit.

**But the variety that survives to the eye is thin.** All six variants wear the same silhouette:
same ankle-length bell tunic, same headcloth, same cream-plus-one-accent-colour palette, same
blank ovoid head. In `cp11-people-group-5-residents-7m-to-25m.png` five residents are in frame
and they read as five copies of one doll at five sizes.

## 4. Does the rig's 6.9 cm short leg show?

**Yes, but not as the crouch the receipt predicted.** The measured step/stature of 0.374 against
a natural 0.41 is the short leg arriving on screen. What a viewer actually notices, though, is
that the figure is **short-legged**: the tunic hem falls to the ankle and below it there is barely
two boot-lengths of leg. The mid-stance knee bend the receipt warns about (~32° against a real
15–20°) is **invisible**, because the tunic hides the knee completely. So the rig limit is real
and it is costing realism, but it is costing it through the silhouette, not through a visible
crouch.

## 5. The Kohen Gadol — the character asked for first

**He is not in the shipped build. There is no body.**

`AMikdashServiceActor::ResolveBody()`, which spawns and dresses his body, is reachable **only**
from `StartService()` (`MikdashServiceActor.cpp:202`). `BeginPlay` calls `StartService()` only
`if (bStartOnBeginPlay && bSequenceEnabled)` (`:95-97`), and otherwise sets
`Status = "Standing by: the sequence is placed but not started."`. **`bStartOnBeginPlay` reads
back `false` on both maps, before and after every walk-v2 apply** (`WALK-V2-FINISH-RECEIPT.md`
and all three `walkv2-finish-apply-*.json`). So nothing spawns him.

Observed, not inferred:

* **131 frames / 13.1 s of game time** from 4.2 m off his authored station 0 (`-3320, 0, 888`):
  empty. `cp11-kohen-EMPTY-station0-at-4m.png`
* **80 frames / 8.0 s** looking straight down the Ulam→Heikhal axis, a cone that contains
  stations 0 (`-3320,0`), 1 (`-3560,0`), 9 (`-4712,0`) and the seven lamp stations at
  `x -5306`: the paroches, the menorah, the incense altar and the shulchan are all there and
  **there is no person anywhere in the sanctuary**. `cp11-kohen-EMPTY-ulam-heikhal-axis.png`

**It cannot be switched on from the command line.** `bStartOnBeginPlay` is `EditAnywhere`, not
`config`, and is serialised per instance, so neither `-ini:` nor `-ExecCmds` reaches it. The
1.49× skate was only ever observable because `Scripts/probe_service_candidate48.py` calls
`StartService()` itself.

**So every Kohen number from tonight is correct in the data and unreachable in play:** the clip
repointed to WalkV2, the speed 90 → 119.95, the 1.49 → 1.000 ratio. The fix is real; the
character is not on screen. Setting `start_on_begin_play = true` (and `sequence_enabled`) on
`RELEASE_KohenGadolService_Selected48_V1` is a map edit and was deliberately not done here.

**What he looks like when he *is* started** — from the 2026-09-09 PIE stills
`SourceAssets/service-review/candidate-service-20260909T070801049654Z-station2.png` and
`-station10.png`, which are still valid for appearance because walk-v2 changed only motion and
left every vertex byte-identical: a **completely featureless white ovoid head with no face at
all**, a sleeve that ends with no visible hand while he tends the menorah, a floor-length robe
that is a rigid untextured shell hiding the feet entirely, and a flat teal rectangle pasted on
the front. He reads as a shop mannequin in a dust sheet. He is markedly worse than the
residents, who at least have a painted face and modelled fingers.

---

## What is genuinely good, stated plainly

* The residents **walk unattended in the packaged build**. No activation flag is needed:
  `spawn_authored_people_on_begin_play` is true on `RELEASE_PeopleV3Population` and
  `AMikdashResidentPopulation::BeginPlay` calls `InitializeAuthoredPeople()`. Eight distinct
  lateral crossings were captured on one camera in 89 s.
* The **plant is exact** and it is exact in a rendered frame, not in a readback.
* **Cadence is right** (0.6 s per step, 100 steps/min, five steps within 5% of each other).
* The **arm swing reads** at distance — it is the only part of the new walk that survives the tunic.
* **Pace and play rate are coupled per person**, so the per-resident variety does not
  re-introduce skating. That was the right way to build it.
* **Nobody marches in lockstep** any more.

## What to fix next, in the order that would buy the most

1. **The heads.** A painted eye-stroke on a smooth ovoid is what makes these read as dolls. This
   is the single biggest gap between what is on screen and "legit real people".
2. **Turn the Kohen Gadol on.** He is the character asked for first and he is not in the build.
   One boolean on one actor, plus `sequence_enabled`.
3. **The crowd field.** Thousands of frozen static-mesh statues standing in clumps, several
   intersecting, is worse than fewer figures. Either animate them (vertex-animation textures on
   the instanced meshes) or thin them hard and keep them far away.
4. **Shorten the tunics, or raise the hem.** The walk that was bought tonight is hidden under a
   floor-length bell. This is cheap and it would make the existing work visible.
5. **Cloth**: any folds, any weave, any normal map. And fix the over-tunic's aliased alpha edge —
   at 3 m it looks torn.
6. **Contact shadow / AO under the sole.** The planted foot is world-perfect and still looks
   pasted on because nothing darkens beneath it.
7. The rig's **6.9 cm short leg** and the **unweighted toe joint** are still worth doing, but they
   are now behind all of the above: they cost a measured 7% of step length, where the heads cost
   the whole illusion.

---

## Frames

All under `SourceAssets/visual-review/`. Every one is from the cp11 packaged build, Candidate48 map.

| file | what it shows |
|---|---|
| `cp11-people-front-3m-face-hands-garment.png` | a resident three-quarter front at **3.0 m**, plus one at 13 m, one at 20 m and crowd-field statues behind. The headline frame. |
| `cp11-people-anatomy-detail-3m.png` | head, both hands and the sandals from that frame at 8-9x: the painted face, the modelled fingers, the aliased over-tunic edge |
| `cp11-people-profile-3m5-midstride.png` | full profile at **3.5 m**, mid-stride, sandals and split stance visible |
| `cp11-people-footplant-proof-3frames.png` | **the plant.** Identical world-fixed crop at t = 10.7 / 10.8 / 10.9 s with fixed reference lines |
| `cp11-people-footplant-t10.7s.png` `-t10.8s.png` `-t10.9s.png` | the three full frames those crops come from |
| `cp11-people-stride-split-stance-t11.2s.png` | widest split stance of the pass |
| `cp11-people-group-5-residents-7m-to-25m.png` | five residents at 7 m to 25 m in one frame — the group / variety frame |
| `cp11-crowdfield-static-background-figures.png` | seven crowd-field figures at ~25 m, t = 0 s and t = +37 s, **pixel-identical** |
| `cp11-kohen-EMPTY-station0-at-4m.png` | 4.2 m from the Kohen Gadol's station 0: empty |
| `cp11-kohen-EMPTY-ulam-heikhal-axis.png` | the whole sanctuary axis, all his stations in frame: empty |
| `movie-cp11-yoav-lane-3m5/` | 80 kept frames at 0.1 s spacing — the filmstrip the plant and stride numbers were measured from |
| `movie-cp11-kohen-gadol-4m/` `movie-cp11-kohen-axis-wide/` | sampled Kohen frames |
| `movie-cp11-court-lane-close/` | sampled real-time-paced frames (~0.9 s apart) from the first pass |
| `cp11-deck-photomode-paused-crowdfield-01.png` `-09.png` | the failed method, kept as the record: two photo-mode shots 48 s apart in which nothing moves because the world is paused **and** the subjects are statues |
| `people-walk-frames-cp11.json`, `-ab40.json`, `-ab100.json`, `movie-*/movie-receipt.json` | per-run receipts |

## Not verified here

* **No frame rate, no performance number.** `-benchmark` deliberately decouples game time from
  wall time, so nothing in this document says anything about how the scene performs.
* **I did not identify which resident** the close pass is. He travels in −X close to a camera set
  on a +X lane, so he is not the resident I aimed at; the numbers are a resident's, not a named
  one's. All 24 share the same clip, so this does not weaken the plant result.
* **Absolute centimetres are ±10%.** The scale-free ratios (step/stature, speed/height, plant
  drift in pixels against a flagstone control) are the trustworthy numbers.
* **Only one camera, one lane, one 89 s window.** The other 16 outer-court residents and all five
  Mount-deck residents were not watched at close range.
* **Idle, and the Idle→Walk transition, were not looked at.** The ~4.6 cm hip drop the re-author
  receipt flags as needing a 0.2–0.3 s cross-blend is still unobserved.
* **No turn was captured close up.** Corner behaviour at 150°/s is unverified visually.
* **Faces were judged at 3.0 m in one lighting condition** (overcast/diffuse court light). They
  may read worse in direct sun and better at dusk.
* **The Main50 map was not captured at all** — only Candidate48, because that is what cp11 cooked.
