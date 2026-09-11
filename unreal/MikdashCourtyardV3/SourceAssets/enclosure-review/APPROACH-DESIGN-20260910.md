# The outside approaches — design record, 10 September 2026

How a visitor arriving from modern Jerusalem gets **up** onto the precinct plaza, and why
every number in it is what it is.

Files: planner and placer `Scripts/release_precinct_approaches.py` (one file: the plan is a
pure function of a height field, so the offline pass and the native pass run the same code
over two independent measurements of the same ground); per-map receipts
`native-approach-apply-Candidate48-*.json` and `native-approach-apply-Main50-*.json`;
arithmetic reused unchanged from
`Plugins/MikdashRuntime/Source/MikdashRuntime/Public/EnclosureMath.h` section 6b.

Every claim below is marked **sourced**, **derived from measured geometry**, or **authored**,
on the same convention as `sources.md`.

> **NOBODY HAS SEEN ANY OF THIS IN A FRAME.** Everything on this page is geometry and
> receipts. There has been no visual, walking, collision or navigation acceptance of the
> approaches, and none of the plaza either — `PLAZA-DESIGN-20260909.md` section 6 item 5 is
> still open and this pass does not close it.

---

## 0. The defect

`PLAZA-DESIGN-20260909.md` section 6, open item 2, in full:

> **THE OUTSIDE APPROACHES ARE NOT BUILT.** Where the deck stands above the ground outside the
> wall — 60.6 m at the south-west gate, 50.4 m at the south-east — a visitor arriving from the
> modern street has no way up. The real precedent is a monumental stair (the Huldah stairway)
> or a bridge on arches (Robinson's Arch); both would be large authored structures standing
> over modern buildings this project deliberately leaves visible.

The deck is flat at Z 0 (748.0 m a.s.l.) across 1,440 m a side, the retaining ring reaches
137 m on the south face, and until this pass the precinct could not be entered on foot at all.

**Sourced:** the gate COUNT and side only — Mishkenei Elyon 196 m.2, two south, one each
north, east and west — and the precinct extent, Yechezkel 42:15-20 with 40:5.
**Nothing in Yechezkel, the Mishnah or the book describes an approach to the precinct from
outside.** Everything below except the gate positions and the ground is authored.

---

## 1. The finding that decided the architecture

A stair on the project's frozen tread — `PlazaStepRiserAmot` 0.5, `PlazaStepTreadAmot` 2.0 —
descends at **1:4**. Outside the two south gates the ground falls away *faster than that*.

Measured on the level's own terrain, straight south of the south-west gate:

| distance out | ground | a 1:4 stair would be at |
|---:|---:|---:|
| 0 m (the wall face) | 685.4 m | 748.0 m |
| 96 m | 670.2 m | 724.0 m |
| 192 m | 637.5 m | 700.0 m |
| 384 m | 592.0 m | 652.0 m |

The gap **widens** from 63 m to 60 m to 62 m to 60 m and never closes. A stair driven straight
out from either south gate never meets the ground: it would end as a viaduct hanging sixty
metres over the Hinnom. The planner reports this as a hard result, not a judgement — the
`outward` candidate at S1 and S2 runs the full 576 m cap and is recorded `converged: false,
"diverges: the ground falls away faster than a 1:4 stair descends"`.

Along the same wall the ground **rises**. So the answer is the one Robinson's Arch gave to the
same problem on the same hill: **the approach turns at the gate and rakes along the face of
the retaining wall**, where 1:4 plus the grade converges on the ground and lands on it.

That is not asserted. All three directions — straight out, and both ways along the face — are
simulated against the measured height field for every gate, every candidate's run is written
into the receipt, and one is chosen by a stated rule.

---

## 2. The rule that chooses a direction — *authored*

> Among the directions that reach the ground within 1,200 amot, take the one whose **foot lands
> lowest**. Straight out through the gate wins wherever it lands within **10 amot (4.8 m)** of
> the lowest foot any direction reaches.

The second clause keeps the head-on entry: a gate should be entered on its own axis, and a
turn is a concession to the ground, not a flourish. The first clause is the one that matters,
and it was written after the obvious alternative — *take the shortest run* — was tried and
rejected on its own numbers. At the south-west gate the shortest converging rake is 153.6 m
eastward and it lands at **720.4 m a.s.l., thirty-five metres above the grade at the gate's own
foot, on a 46 per cent slope.** That is a stair that stops short. The westward rake is 419.5 m
and lands at **675.5 m** — *below* the grade at the gate — and that is an approach.

Applied to Candidate48:

| gate | straight out | along the face, one way | the other | chosen |
|---|---|---|---|---|
| N | converges, 28.8 m | east, 34.6 m | west, 14.4 m | **out (north)** — within 10 amot of the lowest |
| E | converges, 56.6 m | south: **diverges** | north, 1.0 m | **out (east)** |
| S1 | **diverges** | west, 419.5 m, foot 675.5 m | east, 153.6 m, foot 720.4 m | **west** — the lower foot |
| S2 | **diverges** | west, 163.2 m, foot 719.2 m | east: **diverges** | **west** — the only one |
| W | — | — | — | **none built** |

The west gate gets nothing, and that is a measured result rather than an omission: its
threshold is 750.23 m and the ground immediately outside it is 750.12 m, **11 cm below**, less
than one riser. A visitor already walks in at grade there.

---

## 3. What an approach is made of — *authored, from approved parts only*

**No new mesh and no new material.** Everything is laid from the seven approved
`PrecinctPlazaV1` modules with the approved `MI_PrecinctPlaza_Ashlar` and
`MI_PrecinctPlaza_WaySlabs`.

* **Head landing.** A **50 amah square** platform at the threshold, immediately outside the
  gate, of four 25-amah `SM_PlazaV1_WayTile` — the same processional slabs the ways inside use,
  so the way runs through the gate and out. A tile is laid only where the natural grade is
  *below* the threshold; at the east gate two of the four are omitted because the hillside
  stands higher there and no terrain is cut outside the precinct square by this pass.
* **The flight.** `SM_PlazaV1_Step`, 50 amot wide, **riser 0.5 amah, tread 2 amot** — the
  frozen constants, unchanged, so the approaches and the inside gate flights are the same
  stair. A **10-amah landing every 20 risers** and a **50-amah terrace every fifth landing**.
* **Flanking retaining.** `SM_PlazaV1_RetainingBand` stacked from the tread down past the
  measured ground on every exposed flank — both flanks of a flight driven straight out, the
  outer one only where the rake is against the precinct's own wall.
* **Kerbs.** `SM_PlazaV1_Kerb` along every exposed edge.

### The one rule that must not be broken

**The bands are never scaled in Z.** `MI_HerodianV4_Ashlar` maps `u = world X|Y / 300` and
`v = world Z / 300`, so its course lines fall on fixed world-Z levels; a band stretched to fit
a drop would carry courses of a different height from the band above it. Facing a drop is a
**count** of fixed 5-amah bands and the lowest band over-runs into the ground, exactly as on
the plaza's own retaining ring. The batter is the same too: **one amah further out per five
bands, 1 in 25, never negative.**

Every instance in this pass carries the **uniform** module scale `ModuleScaleFor(cmPerAmah)` —
0.96 on the 48 cm candidate, 1.0 on Main50 — and nothing else. The readback measures the scale
of **every one of the 2,391 instances**, not a sample, and the worst deviation from uniform is
**0.0**.

### Riding the ledges

A rake against the face has to deal with a wall that gets wider as it goes down. The precinct's
retaining wall batters out one amah every five bands, so its face is a series of horizontal
ledges 25 amot of height apart. Each step of an approach is pushed outward by
`PlazaBandBatterUnrealCm` of the band its tread sits in — the wall's own number, not a
re-derivation — so the flight steps out onto each ledge in turn instead of being buried in a
wall that widens beneath it.

---

## 4. The acceptance numbers

**Candidate48**, receipt `native-approach-apply-Candidate48-20260910T035136804361Z.json`.
Placed, **saved, reopened**, and every number below measured off the reopened level — the
terrain height field rebuilt from the visible tiles a second time after the reopen, the deck
read off the `AMikdashEnclosure` actor's own `GetPlazaDeckTopZCm`, and the instance transforms
read out of the components.

### Instances placed, per component

| component | mesh | instances | shadow |
|---|---|---:|---|
| `ApproachStepInstances` | `SM_PlazaV1_Step` | **696** | yes |
| `ApproachPavingInstances` | `SM_PlazaV1_WayTile` | **14** | no |
| `ApproachRetainingInstances` | `SM_PlazaV1_RetainingBand` | **1,599** | yes |
| `ApproachKerbInstances` | `SM_PlazaV1_Kerb` | **82** | yes |
| **total** | | **2,391** | 28,692 triangles |

**One new actor, four HierarchicalInstancedStaticMesh components, four draw calls.** Against
the plaza's 34,653 instances in seven components this is 6.9% more instances and 6.0% more
triangles.

### The maximum single unbroken rise between landings

**20 risers = 4.80 m**, on every one of the four approaches, recomputed from the **placed step
instance Z values** rather than from the plan: the run is broken wherever a level repeats,
which is what a landing is. `PlazaStepsPerFlight` is 20 and the run refuses if the placed
flights ever exceed it. (They did on the first attempt — 29 — because a single pass over the
shared component ran the east gate's foot into the south-west gate's head; the count is now
taken per approach over that approach's own instance range.)

### The total climb against the measured face height

| gate | face height, **measured** | total climb | difference | run | risers | landings | terraces |
|---|---:|---:|---:|---:|---:|---:|---:|
| N | 4.67 m | **6.00 m** | +1.33 | 28.8 m | 25 | 1 | 0 |
| E | 2.13 m | **11.76 m** | +9.63 | 56.6 m | 49 | 2 | 0 |
| S1 | **62.57 m** | **72.48 m** | +9.91 | 419.5 m | 302 | 15 | 3 |
| S2 | **51.16 m** | **28.80 m** | −22.36 | 163.2 m | 120 | 6 | 1 |

"Face height" is the live-measured drop from the gate's threshold to the ground at the wall
face at that gate. A **positive** difference means the stair descends past the grade at the
gate's own foot and lands lower still — it has more than closed the drop. **S2 is the one that
does not**, and it is stated rather than smoothed: see section 5.

### That each approach meets the deck above

| gate | head landing top | live deck (`GetPlazaDeckTopZCm`) | difference | nearest placed deck tile | difference |
|---|---:|---:|---:|---|---:|
| N | Z 0.0 | Z 0.0 | **0.00 cm** | (−1800, −31368, 0.0), 18.6 m away | **0.00 cm** |
| S1 | Z 0.0 | Z 0.0 | **0.00 cm** | (15000, 111000, 0.0), 17.0 m away | **0.00 cm** |
| S2 | Z 0.0 | Z 0.0 | **0.00 cm** | (63000, 111744, 0.0), 13.0 m away | **0.00 cm** |
| E | Z 3940.0 | Z 0.0 | +39.40 m | — | — |

The east gate is on a **cut** side: its threshold is not the deck but the wall base
`PlazaWallBaseZUnrealCm` = the outside grade, 787.40 m a.s.l., and the plaza's own 165-step
inside flight already carries that gate down to the deck. The head landing meets **that**
threshold exactly, because the threshold is not re-derived here — it is read out of
`plaza-<Target>.json`, the receipt the placed actor was verified against. An earlier version
re-sampled the ground over the head landing instead and produced a threshold **1.7 m above**
the built one at the east gate, which would have put a step **up** out of the gate: the same
"stops short" failure upside down.

### That each approach meets the street below

Measured against the terrain height field rebuilt **after** the reopen, at the foot of each
flight:

| gate | foot tread | live ground there | residual | across the 24 m width |
|---|---:|---:|---:|---|
| N | Z −600.0 (742.00 m) | Z −602.51 | **+2.51 cm** | +2.5 / +2.5 / +2.5 / +2.5 / +2.5 |
| E | Z 2764.0 (775.64 m) | Z 2759.42 | **+4.58 cm** | −5.26 / −2.62 / +0.05 / +3.17 / +5.81 m |
| S1 | Z −7248.0 (675.52 m) | Z −7233.51 | **−14.49 cm** | +1.95 / +1.06 / −0.14 / −1.34 / −2.54 m |
| S2 | Z −2880.0 (719.20 m) | Z −2872.78 | **−7.23 cm** | −1.83 / −1.03 / −0.07 / +0.89 / +1.62 m |

**Worst residual on the centre line: 14.5 cm — less than one riser (24 cm).** Positive means
the last tread stands above the ground; negative means it runs into it. The run refuses if any
foot is more than two risers from the ground.

The fifth column is the honest one: the ground has a **cross-fall** under a 24 m wide stair,
and at the foot of the south-west flight it varies ±2.5 m across the width. The last tread
therefore meets grade on its centre line and is buried at one edge and standing clear at the
other. **No cross-fall is graded out and no terrain is cut outside the precinct square by this
pass** — that is section 6, item 3.

### Cross-check: two independent measurements of the same ground

The plan is a pure function of a height field. Run offline over the OSM DEM
(`jerusalem.json terrain.heights`) it produces **2,385** instances; run in the editor over the
**54 visible terrain tiles the level actually renders**, 28,613 triangles extracted through
GeometryScripting, it produces **2,391**. The two differ by 0.25%, all of it in the last band
of a flank stack, and no approach changes direction between them. Both plans are in the
receipt.

### Main50, the same pass

Receipt `native-approach-apply-Main50-20260910T035257844953Z.json`. Same four approaches, same
directions, same "west gate needs nothing" result; the amah is 50 cm so every module is at
scale 1.0 and the riser is 25 cm.

| | steps | way tiles | bands | kerbs | total |
|---|---:|---:|---:|---:|---:|
| instances | 714 | 14 | 1,562 | 87 | **2,377** (28,524 triangles) |

| gate | face height | climb | difference | run | risers | landings | terraces | head landing − live deck | foot residual |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N | 4.92 m | 5.25 m | +0.33 | 26.0 m | 21 | 1 | 0 | **0.00 cm** | −30.08 cm |
| E | 2.82 m | 17.50 m | +14.68 | 85.0 m | 70 | 3 | 0 | +35.01 m (cut side) | +1.47 cm |
| S1 | **65.89 m** | **72.50 m** | +6.61 | 400.0 m | 290 | 14 | 2 | **0.00 cm** | +19.10 cm |
| S2 | **55.73 m** | 37.00 m | −18.73 | 203.0 m | 148 | 7 | 1 | **0.00 cm** | +9.92 cm |

Max unbroken rise **20 risers = 5.00 m**, worst scale deviation from uniform **0.0**, worst
foot residual **30.08 cm** — over one riser (25 cm) at the north gate, under two. Live deck
Z 0.0, plaza status `built`, protected maps unchanged. The offline DEM plan and the live plan
agree on the instance count **exactly** here: 2,377 against 2,377.

Tallest flanking retaining, both maps: **112.5–112.8 m** at the south-west approach where it
crosses the Hinnom, 60.0 m at the south-east, 15.0 m at the east, 7.5 m at the north.

---

## 5. What this does NOT solve, stated plainly

**At the south-east gate the approach closes 28.80 m of a 51.16 m face.** Its foot is at
719.20 m and the grade at the gate's own foot is 696.86 m, so **22.43 m of fall remains**, over
175 m of natural hillside at a worst grade of **0.279 — 1.12 times the stair's own 1:4 rake**.
It is a slope, not a cliff, and it is walkable, but it is not built.

That is not a shortcut taken to save work. The ground west of the south-east gate rises to a
**724 m shoulder** in the middle of the south face and then falls away in every direction; a
stair continuing past 719 m would be descending into rising ground and would be in a cutting
within a few treads. Reaching 696 m there needs either a terrain cut outside the precinct
square or a stair on vaults, and both are larger interventions than this pass is.

For scale, the other three approaches all land **below** the grade at their own gate's foot:
N by 1.35 m, E by 9.67 m, S1 by 9.76 m. Main50 reads the same shape: S2 leaves 18.63 m over
215 m at 0.262, and N, E and S1 land 0.03 m, 14.7 m and 6.8 m below their own gate's grade.

---

## 6. Open, and named

1. **NO VISUAL ACCEPTANCE.** Nobody has looked at the approaches, or the plaza, in a frame.
2. ~~**THE APPROACHES ARE NOT WIRED INTO THE STATE TOGGLE.**~~ **WIRED, 10 September 2026.**
   `PrecinctApproachV1` now stands in `HideWhileModernCityStandsTags` alongside
   `PrecinctCutTwin`, so `ApplyStateTaggedActors` drives the whole actor by TAG exactly as it
   drives the terrain twins and the roofscape zones. `BuildingIdentityLabel` was deliberately
   **not** widened — its narrowness is what keeps the audited building hide list from drifting,
   and the hide list still reads 269/0/0 on Candidate48 and 278/0/0 on Main50 afterwards.

   Counted, not read off the source, by `Scripts/audit_modern_restore.py` switching the state
   in a `-nullrhi` editor and counting what carries the tag:

   | | YECHEZKEL | MODERN | OVERLAY |
   |---|---|---|---|
   | before | 1 visible | **1 visible (the defect)** | **1 visible (the defect)** |
   | after, Candidate48 | **1 visible** | 0 visible / 1 hidden | 0 visible / 1 hidden |
   | after, Main50 | **1 visible** | 0 visible / 1 hidden | 0 visible / 1 hidden |

   Receipts `modern-restore-audit-Candidate48-20260910T040825871835Z.json` and
   `modern-restore-audit-Main50-20260910T040850078133Z.json`, both
   `acceptance.passed: true`, `mapBytesChanged: false`.
3. **NO TERRAIN IS CUT OUTSIDE THE PRECINCT SQUARE.** Where the natural cross-fall runs above a
   tread the hillside still rises through the stair; the worst case measured is 2.5 m at one
   edge of the south-west flight's last tread. Head-landing tiles under higher ground are
   omitted rather than buried (two of four at the east gate).
4. **THE WEDGE UNDER EACH STAIR IS VOID**, closed by its flanking retaining. No vaults, no
   substructure — the same decision as under the deck, and the same reason: no viewer can see
   into it.
5. **THE APPROACHES CROSS GROUND THAT STILL CARRIES VISIBLE MODERN BUILDINGS.** Twenty-five
   visible building actors overlap the four footprint boxes on Candidate48. Nothing outside the
   precinct ring is hidden by this pass and nothing is ever deleted; the labels are listed in
   the receipt under `buildingsUnderApproach`. The south-west flank retaining reaches **112.8 m**
   where it crosses the Hinnom, which is a wall the size of the precinct's own and is reported
   rather than tuned away.
6. ~~**NO COLLISION OR NAVMESH PASS.**~~ **WALKED, 11 September 2026.** The PrecinctPlazaV1 modules
   had no simple collision at all; `Scripts/release_plaza_mesh_collision.py` gave Step, WayTile, DeckTile,
   Kerb and RetainingBand one exact box each. In the packaged cp22 build a walking character dropped onto
   the S2 flight, climbed it tread by tread to the head landing, crossed the gate and stood on the deck
   (`SourceAssets/visual-review/movie-cp22-s2-approach-climb/`, 3/3 waypoints, 0 stuck). In MODERN the
   hidden plaza does not collide. No navmesh: neither map has one and nothing in the project paths on one.
   See `AGENTS.md`, 11 Sep 2026 collision pass.

---

## 7. A defect found in the runtime while doing this — **FIXED, 10 September 2026**

`MikdashEnclosure.cpp:1186` yawed the **inside** gate flights by
`SideOutwardYawDegrees(Side)` while advancing them along `-Out`. The step module is 50 amot
along local X and 2 amot along local Y, and a UE yaw *t* maps local +Y to `(-sin t, cos t)`, so
that yaw lays the **50-amah width along the direction of travel** and the 2-amah tread across
it — at the south side, yaw 90 with travel along −Y. The retaining bands four lines earlier use
`SideOutwardYawDegrees - 90`, which is the correct convention and the one the approaches
follow. On Candidate48 this affects the **205 step modules of the east gate's inside flight and
the 10 of the west**.

**Found by reading, not seen in a frame** — consistent with the plaza's own "nobody has looked
at it" note. Nothing in the approaches depended on it: they are placed from Python with the band
convention, and the receipt carries the original observation under `runtimeDefectsObserved`.

### The fix, and the numbers that show it

The line now reads `SideOutwardYawDegrees(Square, Gate.Side) - 90.0`, the bands' own convention.

`Scripts/audit_modern_restore.py` was extended with `step_orientation()`, which reads
`PlazaStepInstances` back out of the built actor — **not** out of the source — splits it into
runs of consecutive instances sharing a yaw, and reports two dot products per flight:
`widthDotTravel`, the |cos| between the module's 50-amah local +X and the direction the flight
travels (**0 is correct, 1 is the defect**), and `ascentDotUphill`, the cos between local +Y and
uphill (**+1 is correct**).

| map | flight | modules | yaw before | yaw after | travel | widthDotTravel before → after | ascentDotUphill before → after |
|---|---|---:|---:|---:|---|---|---|
| Candidate48 | east gate | **205** | 0.0 | **−90.0** | (−1, 0) | **1.0 → 0.0** | **−0.0 → 1.0** |
| Candidate48 | west gate | **10** | 180.0 | **90.0** | (+1, 0) | **1.0 → 0.0** | **−0.0 → 1.0** |
| Main50 | east gate | **176** | — | **−90.0** | (−1, 0) | — → **0.0** | — → **1.0** |
| Main50 | west gate | **14** | — | **90.0** | (+1, 0) | — → **0.0** | — → **1.0** |

Read the east gate row straight: the flight travels along −X; before the fix the module's
fifty-amah width axis was (1, 0) — parallel to travel — and after it is (0, −1), square across
it, with the tread axis (1, 0) pointing uphill toward the gate. Step spacing is 96.0 cm on both
maps' east flights, one 2-amah tread at the target's own amah, before and after: the fix rotates
the modules and moves nothing.

Before receipt `modern-restore-audit-Candidate48-20260910T040644982957Z.json`
(`stepOrientation.ok: false`), after
`...-20260910T040825871835Z.json` and `modern-restore-audit-Main50-20260910T040850078133Z.json`
(`stepOrientation.ok: true`). **Still not seen in a frame.**

---

## 8. What has actually been run

| step | receipt | result |
|---|---|---|
| offline plan, Candidate48 | `python Scripts/release_precinct_approaches.py -Candidate48` | 4 approaches, 2,385 instances, over the OSM DEM |
| `-Candidate48 -ApproachApply` (first) | `native-approach-apply-Candidate48-20260910T034834290903Z.json` | placed and saved; **FAILED at readback** on this script's own per-approach run counter (29 risers reported across an approach boundary). Kept as evidence. |
| `-Candidate48 -ApproachRevert` | `native-approach-revert-Candidate48-20260910T035039704274Z.json` | actor found, destroyed, saved, reopened, **absent**; protected maps unchanged |
| `-Candidate48 -ApproachApply` | `native-approach-apply-Candidate48-20260910T035136804361Z.json` | **placed, saved, reopened, measured.** All four counts read back, worst scale deviation 0.0, max unbroken rise 20 risers, worst foot residual 14.5 cm, protected maps unchanged. Checkpoint `ReviewCheckpoints/PrecinctApproach-Candidate48-20260910T035136804361Z` |
| `-Main50 -ApproachApply` | `native-approach-apply-Main50-20260910T035257844953Z.json` | **placed, saved, reopened, measured.** 2,377 instances, worst scale deviation 0.0, max unbroken rise 20 risers, worst foot residual 30.1 cm, protected maps unchanged. Checkpoint `ReviewCheckpoints/PrecinctApproach-Main50-20260910T035257844953Z` |
| `-Candidate48 -ApproachVerify` | `native-approach-verify-Candidate48-20260910T040044282151Z.json` | **a fresh process reopened the saved map, re-extracted the terrain, re-derived the whole plan from scratch and matched the saved instances exactly** — 696 / 14 / 1,599 / 82, max unbroken rise 4.80 m, worst foot residual 14.489 cm, worst scale deviation 0.0 — with `mapBytesChanged: false`. |

`-ApproachVerify` saves nothing. It is the strongest statement available without a frame: the
instances in the level are not merely *recorded* as matching the measurement, they are
re-derived from the measurement in a separate process and found to be the same.

`python scripts/verify.py`: **7/7 checks passed, `verify: green`** (32/32 standalone C++ math
tests, 269 scripts parse, 1,112 receipts parse).
