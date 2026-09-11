# The precinct plaza — design record, 9 September 2026

What the Yechezkel precinct encloses, and why every number in it is what it is.

Files: arithmetic `Plugins/MikdashRuntime/Source/MikdashRuntime/Public/EnclosureMath.h`
section 6b; generator `Scripts/create_precinct_plaza.py`; placer
`Scripts/release_precinct_plaza.py` (+ `.spec.json`); runtime `AMikdashEnclosure::BuildPlaza`;
test `Plugins/MikdashRuntime/Tests/EnclosureMathTest.cpp::PlazaChecks`; manifest
`plaza-manifest.json`; per-map receipts `plaza-Main50.json` and `plaza-Candidate48.json`;
plan view `plaza-plan-Candidate48.png`.

Every claim below is marked **sourced**, **user decision** or **authored**, on the same
convention as `sources.md`.

---

## 0. The decision

> "that whole expanded area around that we had to, like, take out buildings. I'm not sure if
> I like it because either you put it as a platform, like a flat flat platform that's built
> out into those dimensions to just expand the plaza. Or what you have to do is you have to
> restore the buildings that are there now. I would say make it a flat plaza for the
> dimensions of the the area that has call sets, that expanded area."
>
> — Shmuel, 9 September 2026

Until that morning the YECHEZKEL state hid 270 (Candidate48) or 279 (Main50) modern building
actors inside the ring and left the raw DEM terrain showing. That reads as a bald patch cut
out of Jerusalem, not as a place. The precinct is now a **built flat plaza across its whole
footprint**, with retaining walls down to grade where the ground falls away and a cut where it
rises. **The buildings are still hidden by visibility and are still never deleted; MODERN
still restores every one of them exactly.** The plaza is simply what the visitor sees instead
of bare terrain.

**Sourced:** the extent, and only the extent — Yechezkel 42:15-20 with 40:5, five hundred
reeds of six amot, 3,000 amot a side, measured from outside.
**User decision:** that the enclosed ground is a built flat plaza rather than hidden buildings
or restored ones.
**Authored:** everything else on this page.

---

## 1. Extent

The precinct square, unchanged, from `precinct-<Target>.json`:

| map | amah | west | north | east | south | side |
|---|---|---|---|---|---|---|
| Candidate48 | 48 cm | −31776 | −31824 | 112224 | 112176 | 144,000 cm = **1,440 m** |
| Main50 | 50 cm | −33100 | −33150 | 116900 | 116850 | 150,000 cm = **1,500 m** |

The **paved rectangle is the square inset by one wall thickness (6 amot)** on every side, so
the paving reaches the wall and never overhangs it: Candidate48 −31488 … 111936 by
−31536 … 111888. `EnclosureMathTest.cpp` asserts that inset to 1e-9 cm on all four sides, and
`release_precinct_plaza.py`'s offline check re-derives it from the precinct receipt rather
than trusting the plaza receipt's own copy.

---

## 2. The deck height, and why

**Z 0 — the Temple's own datum. 748.0 m above sea level in this level's frame.**

Not chosen for tidiness. It is the only height at which the deck meets what is already built:

1. **`SM_0127_architecture_Outer_court_supporting_platform`** — the measured outer court
   supporting platform — has its **underside at Z 0 exactly** and rises to Z 299 over
   ±8100 cm (`architecture-manifest.json` `expectedBoundsUnrealCm`). A deck any lower leaves a
   visible gap under a 162 m square platform; any higher buries its plinth. The generator
   re-reads that manifest entry and **refuses to export** if it ever stops being true.
2. **The project's own precedent for a built platform on this site put its deck at Z 0 too.**
   Every surface vertex in `SourceAssets/FutureMountV1/mount-platform.mesh.json` is
   `Z = 0.0`, with a skirt to 40 m depth over 139,716 m². The plaza is that platform continued
   out to the precinct wall — the same idea at precinct scale.
3. That mesh is **not placed in either Walkthrough map** (the Nanite census of 7,519 unique
   meshes, `perf-optimize-analyze-20260908T122328Z.json`, lists no platform category), so
   nothing on the deck plane can z-fight it.

A one-amah offset was considered and rejected: it would have solved a z-fighting problem that
does not exist in these maps, at the cost of a 48 cm gap under the court platform.

Deck slab: **1 amah thick**, underside at Z −48 (Candidate48) / −50 (Main50). *Authored.*

### What that costs in earth

Measured against the OSM terrain grid (`jerusalem.json` `terrain.heights`, the same source the
wall's ring profile was sampled from), one sample at the centre of every paving cell, weighted
by the cell's clipped area:

| | Candidate48 (1,440 m) | Main50 (1,500 m) |
|---|---:|---:|
| paved area | 2.07 km² | 2.25 km² |
| ground under it | 611.6 – 810.5 m a.s.l. | 602 – 811 m a.s.l. |
| **fill** | **76.84 Mm³** over 79.9% of the area, mean 46.8 m | **86.96 Mm³** over 79.7%, mean 48.9 m |
| **cut** | **12.45 Mm³** over 20.1% of the area, mean 30.0 m | **13.72 Mm³** over 20.3%, mean 30.2 m |
| net | +64.4 Mm³ | +73.2 Mm³ |

Per quadrant, Candidate48, in millions of cubic metres:

| quadrant | fill | cut | ground |
|---|---:|---:|---|
| north-west | 13.40 | 0.31 | 665 – 764 m |
| north-east | 2.71 | **12.12** | 696 – 811 m |
| south-west | **32.95** | 0.00 | 611 – 750 m |
| south-east | **27.78** | 0.03 | 612 – 758 m |

**The shape of the intervention, stated plainly:** the plaza is a platform on the south and
west and a quarry in the north-east. Four fifths of it stands on fill, deepest where the
south-west corner reaches the Kidron gorge floor; the remaining fifth is cut out of the Mount
of Olives slope. That is what a flat deck at the Temple's datum means on this ground, and it
is reported rather than tuned away.

---

## 3. Retaining and scarp

*Authored in full. The sources say nothing about what carries a precinct across a valley — see
`sources.md` §4b for the same admission about the wall's own substructure.*

Two faces of one wall, driven by the **same frozen ground profile the wall stands on** (601
stations a side, highest and lowest ground under the footprint), passed into `BuildPlaza`
rather than re-sampled — two independent samplings of the same terrain is exactly how a wall
ends up floating above its own retaining wall.

* Where the ground is **below** the deck: a retaining wall runs down from the deck edge, its
  outer face **coplanar with the precinct's own outer face**, so the 3,000 amot stay measured
  where the wall stands, as Yechezkel 42:15 measures them — from outside.
* Where the ground is **above** the deck: the plaza is a **cut**, and the same bands rise from
  the deck to the outside grade as a revetment facing inward, with the wall on the crest. The
  real analogue is the Temple Mount's northern scarp.
* A single 25-amah module can carry both, when the ground crosses the deck under it.

**The wall now stands on `max(outside grade, deck)`** — `PlazaWallBaseZUnrealCm`. On a fill
side that is the deck and the retaining wall carries it; on a cut side it is the outside grade
and the wall stands on the crest with the plaza a storey below its inner face. With
`bBuildPlaza` false the function is a no-op and the wall grounds exactly as it did before the
plaza existed, which is what makes this a change one boolean can revert.

### Heights, per side

Candidate48 (Main50 in brackets where it differs materially):

| side | retaining (fill) max | fill modules | scarp (cut) max | cut modules | wall base, m a.s.l. |
|---|---:|---:|---:|---:|---|
| north | 48.8 m | 55 / 120 | 57.3 m | 67 | 748.0 – 805.3 |
| east | **134.6 m** (146.7) | 87 | 62.1 m | 34 | 748.0 – 810.1 |
| south | **136.9 m** (147.1) | 120 (all) | — | 0 | 748.0 flat |
| west | 90.0 m | 70 | 16.9 m | 55 | 748.0 – 764.9 |

The south face is retained for its entire 1,440 m, at up to 137 m. For scale, the Herodian
Temple Mount's south-east corner stands about 45 m above bedrock. This is three times that,
and it is not an error: the Kidron gorge floor is 611 m and the Temple datum is 748 m.

### Construction

* **Band:** 25 amot long × **5 amot high** × 3 amot thick, one closed box, 12 triangles.
* **Bands are never scaled in Z.** `MI_HerodianV4_Ashlar` maps `u = world X|Y / 300 cm` and
  `v = world Z / 300 cm`, so its course lines fall on fixed world-Z levels; a stretched band
  would carry courses of a different height from the band above it, which is the one thing a
  viewer standing in the Kidron looking up a 137 m wall would see at once. Facing a drop is
  therefore a **count**, and the lowest band simply over-runs into the ground — free, and what
  a real footing does. The test sweeps the count over four decades of height and asserts the
  stack always reaches past the bottom and never by more than one band.
* **Batter, not setback.** A Herodian retaining wall is widest at its foot. The precinct's
  measured outer face is the face at **deck level**, and every band below it steps **one amah
  further out per five bands — 1 in 25**. On the 137 m south face that is 5.5 m of spread at
  the foot, and a horizontal ledge line every 25 amot of height instead of one unbroken plane.
  The test asserts the batter is monotone and **never negative**: an inward step would put the
  foot of the wall inside the 3,000 amot and an overhanging retaining wall does not stand up.

---

## 4. The paving, and the anti-repetition scheme

The decision was made because a repeating surface reads badly. 1.44 km of a 5 m tile is a grid
from the air, so this is the part of the design that gets the care.

### The materials — what is reused and what had to be authored

`M_JerusalemPaving_500cm` **cannot be varied as it stands.** Its mapping is a frozen,
unparameterised Custom node — `return float2(P.x,P.y)/500.0;` — with **MIRROR** addressing on
both axes, and `release_jerusalem_paving.py` asserts that graph node for node. Over 1.44 km
that is a 5 m tile with a 10 m mirror period and axis-aligned symmetry lines: the strongest
grid cue there is.

So one new material, `M_PrecinctPlaza_Paving`, which **samples the same approved texture**
`T_JerusalemPaving_BaseColor` at the same 500 cm with the same roughness 0.8 and metallic 0,
and adds only a rotation and an origin taken from per-instance custom data. **The approved
material is never edited**, and the release script re-hashes it to prove so.

| use | material | authored? |
|---|---|---|
| field paving | `M_PrecinctPlaza_Paving` — new master, approved texture, rotatable | new |
| processional ways | `MI_PrecinctPlaza_WaySlabs` — instance of the approved `M_JerusalemFloorSlabs_500cm` | reused |
| ribs, kerbs, channels, retaining, scarp, steps | `MI_PrecinctPlaza_Ashlar` — instance of the approved `MI_HerodianV4_Ashlar` | reused |

The two instances exist for one reason: a HISM needs `MATUSAGE_INSTANCED_STATIC_MESHES`, and
setting it on a child leaves the approved parent byte-identical.

### The first version crashed the cook — read this before touching the material

The graph described above compiled clean in the editor (`recompile_material`, zero errors) and
then **crashed ShaderCompileWorker at cook time**: return code `-1073741819`, an access
violation, on `FLocalVertexFactory` base-pass permutations, failing the package with
`Error_UnknownCookFailure`. The cook had otherwise finished all 8,594 packages; the only two
jobs in the crashed worker's batch were this material's. Checkpoint `cp02`,
`Checkpoint-cp02-20260909T235427Z/uat.log` lines 6215–6218, summary at 6560. Not memory —
peak 7,532 MB with 9.1 GB free, and both maps byte-identical before and after.

**Which half was guilty, and it is not the obvious one.** Per-instance custom data is fine:
`M_CrowdFigure_P*`, `M_CrowdGarmentPaletteV1` and `M_VehiclesV3_*` all read it, all with stock
nodes and no `Custom` node between them, and all of them cooked and shipped in Walkthrough-12.
`Custom` nodes alone are fine too — the approved `M_JerusalemPaving_500cm` is one. What was
unique to this material was the **combination**: author-written HLSL taking per-instance custom
data as function arguments, hoisted into the vertex stage where a non-instanced vertex factory
has no instance data to give it.

**So the `Custom` nodes went and the per-instance data stayed, and the whole design survives.**
The rotation is now the same arithmetic in stock nodes:

```
d = worldXY - (U0, V0)
u =  d.x * Cs + d.y * Sn
v =  d.y * Cs - d.x * Sn      then / 500 cm
```

Five `PerInstanceCustomData` reads — Cs, Sn, U0, V0 and the tint — with **identity defaults**
(Cs = 1, everything else 0), so the very permutation that crashed, a non-instanced draw with no
instance data, now degrades to exactly the approved unrotated 500 cm mapping instead of to
nonsense. `paving_graph()` refuses the run if a `Custom` node ever reappears.

Two things were fixed on the way past. The old tint used `saturate(1 + T*0.04)`, which clamped
at 1 and could therefore only ever *darken* — half the tonal range was being silently thrown
away; the stock version has no clamp. And rebuilding the material in place needs the material
**outputs disconnected first**, because `delete_all_material_expressions` will not remove a node
still wired to an output — measured: the bulk call alone left five nodes of eleven.

**Fixed and cooked, 10 September 2026.** The rebuilt material is receipted in
`native-plaza-assets-Candidate48-20260910T003719041028Z.json`: old graph
`[WorldPosition, 5x PerInstanceCustomData, Custom, TextureSample, Custom, 2x Constant]`, new
graph `[WorldPosition, 3x ComponentMask, 5x PerInstanceCustomData, 3x Subtract, 6x Multiply,
2x Add, AppendVector, Divide, TextureSample, 5x Constant]` — **zero `Custom` nodes**,
custom-data defaults `{0:1, 1:0, 2:0, 3:0, 4:0}`, both usages set, zero compiler errors, map
and protected maps byte-identical. `Checkpoint-Build.ps1 -Label cp02b` then cooked clean:
`Checkpoint-cp02b-20260910T003728Z/uat.log` ends `Success - 0 error(s), 0 warning(s)`,
`BUILD SUCCESSFUL`, `AutomationTool exiting with ExitCode=0 (Success)`, with
`M_PrecinctPlaza_Paving` compiling fresh in both SM5 and SM6. Child exe produced, 3.86 GB
archived.

The build is green end to end: `status: checkpoint_playable`, and the bounded startup smoke
passed — window open in 18 s, peak 832 MB, still alive at the end of the window.

That receipt first read `failed`, which is worth keeping on the record because it was not the
cook. `Checkpoint-Build.ps1` used to require the MAIN map to be byte-identical across the
build as well as the cooked one, and another agent saved
`/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough` during the five minutes it ran. Main50
is not the cooked map and the candidate's hash was identical before and after, so the guard was
tripping on unrelated concurrent work; it has since been narrowed to the cooked map only, the
smoke was re-run, and the receipt carries `mainMapChangedDuringCook: true` with a
`statusCorrectionNote`. Nothing about the plaza differed between the two readings.

**Built and receipted, 9 September 2026**
(`native-plaza-assets-Candidate48-20260909T225412198686Z.json`): all three materials created,
the graph read back node for node — one WorldPosition, **five PerInstanceCustomData at slots
0–4**, the two Custom nodes with their code compared as strings, the approved texture sampled
at sRGB, roughness 0.8, metallic 0, opaque, both usages set — zero compiler errors, and both
approved parents re-hashed and unchanged. All seven meshes imported with a bounds error of
**0.0** against canonical; the retaining band, the only module not symmetric about Y, gives an
unreflected error of 150 cm, which is what actually *proves* the Y-reflect adapter rather than
merely being consistent with it. The target map and all four protected maps came out
byte-identical.

The ways need no rotation at all — they run on the world axes, so the approved slab material's
own unrotated world-XY mapping is already aligned with them.

### The seven devices

1. **Irregular super-panels from a frozen recursive binary split** (`PlazaPanelAt`), 3 to 8
   cells a side — 36 m to 96 m. Panel size *and* offset both vary. A jittered lattice is still
   a lattice; a k-d split is not. **713 panels** over 14,641 cells, mean 20.5 cells.
2. **One course direction per panel** from five values: 0°, 22.5°, 45°, 67.5°, 90°. The two
   odd angles are there so the eye cannot find the world axes in the field paving.
3. **A greedy five-colouring against every panel along the west and north joints**, not just
   the one at the corner — a panel eight cells deep can abut four shorter ones. The colouring
   compares neighbours by their own hashed preference rather than their final colour (doing
   otherwise makes each panel depend on the one before it all the way back to the north-west
   corner, a hundred-deep recursion in a function called fourteen thousand times at load), so
   a residual remains and the test **measures** it: **940 of 29,282 cell joints, 3.2%**,
   against 20% for five colours picked at random. Those joints still carry a rib and still
   start their paving at different origins.
4. **A per-panel UV origin** in [0, 25) amot on both axes, so no two panels start the 5 m
   pattern in the same place even when they share a direction.
5. **An ashlar rib on every panel joint**, one amah wide and a quarter proud — **6,166
   modules**. The seam between two differently-laid panels becomes a deliberate line of stone
   rather than a place where two textures fail to meet. The ribs *are* the panel outlines, so
   no separate edge list can go stale.
6. **Five processional ways** in the other approved paving, two cells (50 amot, 24 m) wide,
   from every gate to the court platform, kerbed both sides — **602 way tiles, 602 kerbs**.
   The grid is **set out from the world origin, not from the wall**, so the north, east and
   west gates, which stand on the Temple's own axes, fall exactly on a cell boundary and their
   ways are symmetric about them to the centimetre. The two south gates are at thirds of the
   south wall and do not; their bands are snapped to the nearest boundary and the offset — at
   most half a cell, 576 cm on Candidate48 — is recorded per way in the receipt.
7. **Drainage on a non-periodic stride and a tonal drift far coarser than the tile.** A
   perimeter channel 10 amot inside the deck edge, plus cross channels whose spacing walks the
   sequence 11, 14, 9, 16, 12 cells — it repeats only after 1,550 amot, longer than any run on
   the plaza. **2,616 channel modules**; 46 more are omitted where a channel meets a
   processional way, because a road with an open trench across it is not a road (the culvert
   itself is not modelled). A channel is a two-amah invert half an amah deep with lipped rims
   standing an eighth of an amah **proud** and lapping a fifth of an amah over the invert on
   each side, so the opening is 1.6 amot. The proud rim is not decoration: a channel flush
   with the deck puts two large coplanar surfaces in contact along a kilometre of run, which
   is a seam wherever the two meshes disagree in the last bit of a float. The tonal drift is value noise on a
   **120 m lattice**, ±4% of lightness, which is the slow variation every photograph of a real
   esplanade has and a tiled texture never does.

`plaza-plan-Candidate48.png` is the plan view: one block per cell, tinted by its panel's course
direction, with the ribs, the ways and the channels drawn over it. It is there so a reviewer
can *see* whether it reads as a grid rather than read that it does not.

### Steps between levels

The deck is one level, so the only level changes are at the gates. Where the threshold stands
above the deck — the cut sides — a flight descends: riser half an amah, tread 2 amot, 50 amot
wide, a 10-amah landing every 20 risers.

| gate | outside ground | threshold | inside rise | steps | outside drop |
|---|---:|---:|---:|---:|---:|
| N | 743.6 m | 748.0 | — | 0 | 4.4 m |
| E | 787.4 m | 787.4 | **39.4 m** | 165 + 8 landings | — |
| S1 | 687.4 m | 748.0 | — | 0 | **60.6 m** |
| S2 | 697.6 m | 748.0 | — | 0 | 50.4 m |
| W | 750.2 m | 750.2 | 2.2 m | 10 | — |

(Candidate48. On Main50 the east flight is 141 steps and the south-west drop 64.7 m.)

---

## 5. Cost

Candidate48, and Main50 within 0.3%:

| component | instances | triangles/module | triangles |
|---|---:|---:|---:|
| deck tiles | 14,039 | 12 | 168,468 |
| way tiles | 602 | 12 | 7,224 |
| panel ribs | 6,166 | 12 | 73,992 |
| way kerbs | 602 | 12 | 7,224 |
| drainage channels | 2,616 | 36 | 94,176 |
| retaining bands | 8,600 | 12 | 103,200 |
| scarp bands | 1,813 | 12 | 21,756 |
| gate steps | 215 | 12 | 2,580 |
| **total** | **34,653** | | **478,620** |

**Seven `HierarchicalInstancedStaticMeshComponent`s — seven draw calls** before per-instance
culling, against the 3,140 the whole map issues today. **Zero new actors**: the plaza is
components on the precinct actor that already exists. 478,620 triangles is **14.0%** of the
3,416,580 triangles in the 190-actor Old City facade set the YECHEZKEL state already hides.

Two deliberate choices against `PERFORMANCE-BUDGET.md`:

* **The deck, way and rib components cast no shadow.** A flat ground plane casts nothing, and
  ShadowDepths was the single most expensive pass in this build before the Nanite pass — 8.62
  ms. That keeps about 20,800 instances out of the virtual shadow map every frame.
* **Nanite is on for every plaza module** (`build_nanite: true` at import), unlike the wall
  modules. The plaza is large, static, opaque and instanced, which is the case Nanite exists
  for; 34,000 non-Nanite instances would go straight back into the pass this build was just
  dug out of. Seven meshes at ~31 KB of root pages each is about 220 KB.

Per-instance custom data: five floats on the two paving components (cos, sin, U origin, V
origin, tint) — 14,641 × 5 × 4 bytes ≈ 293 KB. That is what buys five course directions and
14,000 distinct pattern origins from one draw call.

---

## 6. What is deliberately not claimed, and what is not finished

* That the Temple's precinct was paved, or paved like this. **Nothing** in Yechezkel, the
  Mishnah or the book describes the ground inside the 3,000 amot. The extent is sourced; the
  plaza is the user's decision; the design is this project's.
* That 77 million cubic metres of fill is a historical claim. It is the arithmetic consequence
  of a flat deck at the Temple's datum on this terrain, reported so the size of the
  intervention is on the record.

**Open, and named:**

1. ~~**THE TERRAIN IS NOT CUT.**~~ **CUT, 10 September 2026.** `Scripts/release_precinct_terrain_cut.py`,
   receipts `native-terrain-cut-apply-<Target>-*.json`.

   Inside the precinct square the terrain surface is now **clamped to the deck UNDERSIDE**
   (Z −48 on Candidate48, −50 on Main50) — cut to the underside, not the top, so the one-amah
   slab hides the quarry floor and there is no lip. Outside the square nothing moves. Terrain
   already below the underside is untouched, so the operation removes exactly the 12.45 Mm³
   the table above measures and nothing else.

   The **acceptance number, Candidate48: the highest any terrain vertex stands above the deck
   underside anywhere in the precinct interior is 7.1 × 10⁻¹⁵ cm** — floating-point zero — over
   **20,736 stations on a 1,003 cm (10 m) grid** across the paved rectangle, 19,346 of which
   carry terrain and **0 of which are above the underside**. (The 1,390 stations with no
   terrain are the FutureMountV1 platform hole, which predates this pass.) Per tile the twins
   read back 0.0 cm at their vertices and ≤ 1.4 × 10⁻¹⁴ cm on their own 500 cm grids, and the
   surface **outside** the square is unchanged to ≤ 0.001 cm — float32 source-model
   quantisation — over 12,819 stations.

   The mechanism is the FutureMountV1 precedent extended, and the swap is by VISIBILITY:
   eleven `*_PrecinctCut` twin meshes are placed as their own actors tagged `PrecinctCutTwin`,
   and the original tile actors are hidden with `SetActorHiddenInGame` with actor collision
   disabled and tagged `PrecinctCutOriginal`. **Nothing is deleted and no original asset is
   opened for write.** Five of the sixteen tiles needed no cut at all — they stand entirely
   below the underside inside the square — and were left alone. Four of the eleven are cut
   from the `*_FutureMountCut` meshes those actors actually render, not from the pristine
   originals, so the platform hole is preserved.

   **Main50, the same pass:** max **7.1 × 10⁻¹⁵ cm** above the deck underside (Z −50) over
   **22,500 stations on a 1,003 cm grid**, 21,108 with terrain, **0 above**. Outside the square
   the twelve twins are unchanged to ≤ 0.0013 cm over 125,826 stations. `-CutRevert` was
   exercised on Candidate48 and re-applied: 12 actors restored, then all 12 twins reused,
   re-verified corner for corner and the same number measured again.

   **The Western Wall Plaza cut rides the same pass** (`KotelPlazaCutV1`, tile 07_08, driven by
   the 926 deck cells of `SourceAssets/context-review/KotelPlazaV1/kotel-plaza-plan.json` merged
   to 146 rectangles at two levels, undersides Z −1034.594 and −1284.594): **max 5.9 × 10⁻⁶ cm**
   above its deck underside over **5,533 stations at 100 cm**, 0 above, outside the polygon
   unchanged to 0.00036 cm over 116,577 stations. Its twin is placed HIDDEN and tagged
   `KotelPlazaCutTwin`, because that plaza is a MODERN feature sitting 11 m below this deck.

   **What is NOT wired: the state toggle.** `AMikdashEnclosure::GatherModernBuildings` cannot
   see a terrain actor — `BuildingIdentityLabel` (MikdashEnclosure.cpp:22-42) returns an empty
   label for any mesh outside `JerusalemContext/Buildings/` and `OldCityFacadesV1/Meshes/`, and
   an empty label is skipped before the hide list is consulted — so no value in
   `ExplicitHideLabels` can reach one. **The hook is compiled and counted as of 10 September
   2026:** `ApplyStateTaggedActors` drives these actors by TAG, and `Scripts/audit_modern_restore.py`
   counts 11 `PrecinctCutTwin` visible in YECHEZKEL only and 12 `CityDetailZone_Precinct` visible
   in MODERN and OVERLAY only, on both maps, with the building hide list still at 269/0/0 and
   278/0/0.
2. ~~**THE OUTSIDE APPROACHES ARE NOT BUILT.**~~ **BUILT, 10 September 2026.**
   `Scripts/release_precinct_approaches.py`, receipts `native-approach-apply-<Target>-*.json`,
   design record **`APPROACH-DESIGN-20260910.md`**.

   Four raking monumental stairs, one at each gate that needs one, laid entirely from the
   approved PrecinctPlazaV1 modules - `SM_PlazaV1_Step`, `SM_PlazaV1_RetainingBand`,
   `SM_PlazaV1_WayTile`, `SM_PlazaV1_Kerb` - at the frozen 0.5-amah riser and 2-amah tread,
   with a 50-amah square head landing outside every gate, a 10-amah landing every 20 risers and
   a 50-amah terrace every fifth landing. **2,391 instances in four HISM components on one new
   actor** on Candidate48, 2,377 on Main50. Nothing is scaled in Z: the readback measures the
   scale of EVERY instance and the worst deviation from the uniform module scale is **0.0**.

   **The finding that decided the shape.** A stair on this project's tread descends at 1:4, and
   outside the two south gates the ground falls away *faster than that* - 685 m at the wall,
   592 m 384 m further south, against 652 m for the stair. A stair driven straight out from
   either south gate **never meets the ground**. So the approach turns at the gate and rakes
   **along the face of the retaining wall**, which is what Robinson's Arch did on the same hill.
   The direction is not asserted: all three candidates are simulated against the terrain the
   level actually renders, every candidate's run is in the receipt, and the one whose foot lands
   lowest wins.

   **The acceptance numbers, Candidate48**, all measured after save AND reopen against live
   geometry: max unbroken rise between landings **20 risers = 4.80 m** on every approach; head
   landing to live deck **0.00 cm** at all three fill gates, and exactly the built wall base at
   the cut east gate; worst foot residual against the reopened terrain **14.5 cm, under one
   riser**. Total climb against the measured face height: N 6.00 m of 4.67, E 11.76 of 2.13,
   **S1 72.48 of 62.57**, S2 28.80 of 51.16.

   **What it does not solve, and it is in the record rather than smoothed:** the south-east
   approach closes 28.80 m of a 51.16 m face and leaves 22.43 m of natural hillside at 0.279
   grade, because the ground west of that gate rises to a 724 m shoulder and a stair continuing
   past 719 m would be descending into rising ground. The west gate gets no approach at all -
   its threshold stands 11 cm above the grade outside it, which is less than one riser. The
   south-west approach's flanking retaining reaches **112.8 m** where it crosses the Hinnom. And
   the approaches are a new actor — **now wired into the state toggle**, tag `PrecinctApproachV1`
   in `HideWhileModernCityStandsTags`, counted visible in YECHEZKEL only on both maps; see
   `APPROACH-DESIGN-20260910.md` section 6 item 2.
3. **THE FILL IS NOT MODELLED.** Under the deck there is a void closed by the retaining ring —
   no vaults, no cisterns. No viewer can see into it. The real Temple Mount solves the same
   problem with vaults.
4. **DRAINAGE OUTFALLS ARE NOT MODELLED.** The network runs to the perimeter channel; where it
   would discharge through the retaining face there is no opening, because a hole in a 137 m
   ashlar wall is a piece of architecture and none has been designed.
5. **NO VISUAL ACCEPTANCE.** Everything above is geometry and receipts. Nobody has looked at
   it in a frame.

---

## 7. What has actually been run

| step | receipt | result |
|---|---|---|
| offline export, both maps | `plaza-manifest.json`, `plaza-Main50.json`, `plaza-Candidate48.json`, `plaza-plan-Candidate48.png` | 7 modules written, readback re-proves every file's bounds, winding and normals |
| standalone C++ test | `tests.json` (`plaza_*` keys) | PASS. 121x121 cells, 713 panels, 14,039 + 602 tiles, 6,166 ribs, 2,616 channels, panel bounds 3-8 cells, batter monotone and never negative, band stacks always reach past the bottom, channel stride non-periodic |
| `-Candidate48 -PlazaAssets` | `native-plaza-assets-Candidate48-20260909T225412198686Z.json` | 7 meshes imported at bounds error 0.0; 3 materials built and read back node for node; map and all four protected maps byte-identical |
| `-Candidate48 -PlazaApply` | `native-plaza-apply-Candidate48-20260909T225822507573Z.json` | **placed, saved, reopened and read back.** Status `built`, deck Z **0.0**, extent −31488/−31536/111936/111888, **121x121 cells, 713 panels**, all eight instance counts equal to the receipt, per-side retaining and scarp maxima equal to the receipt, **478,620 triangles**. Protected maps unchanged; checkpoint `ReviewCheckpoints/PrecinctPlaza-Candidate48-20260909T225822507573Z` |
| `-Candidate48 -CutApply` | `native-terrain-cut-apply-Candidate48-20260910T003830057450Z.json` | **terrain cut, saved, reopened, measured.** 12 twins, max terrain height above the deck underside **7.1e-15 cm** over 20,736 stations at 1,003 cm; outside the square unchanged to 0.001 cm. Protected maps and all original tile assets byte-identical; checkpoint `ReviewCheckpoints/PrecinctTerrainCut-Candidate48-20260910T003830057450Z` |
| `-Candidate48 -CutRevert` then `-CutApply` | `native-terrain-cut-revert-Candidate48-20260910T003738093004Z.json` | revert restored all 12 actors and removed the twin actors; the re-apply reused and re-verified all 12 twins and reproduced the same number |
| `-Main50 -CutApply` | `native-terrain-cut-apply-Main50-20260910T003556215362Z.json` | **terrain cut, saved, reopened, measured.** max **7.1e-15 cm** over 22,500 stations at 1,003 cm, 0 above; outside unchanged to 0.0013 cm over 125,826 stations |
| `-Main50 -PlazaApply` | `native-plaza-apply-Main50-20260909T230017414502Z.json` | **placed, saved, reopened and read back.** Status `built`, deck Z **0.0**, extent −32800/−32850/116600/116550, **121x121 cells, 713 panels**, counts 14,039 / 602 / 6,166 / 602 / 2,616 / 8,758 / 1,768 / 190, per-side faces equal to the receipt, **479,676 triangles**. Protected maps unchanged; checkpoint `ReviewCheckpoints/PrecinctPlaza-Main50-20260909T230017414502Z` |

**The 713-panel agreement is the load-bearing one.** The generator lays the plaza in Python
and the actor lays it again in C++, both walking the same frozen recursive split from
`EnclosureMath.h`. Producing the same 713 panels and the same 34,653 instances from two
independent implementations is what says the receipt describes the plaza that is actually in
the level, rather than the plaza somebody meant to build.

---

## Addendum 11 September 2026 - far-field macro layer on the retaining faces

**Why the faces were featureless.** Not a fallback: `MI_PrecinctPlaza_Ashlar` resolved exactly to the live
V5b set and the cooked log had no LogMaterial line for it. The close-up tile is 300 cm with nothing larger
than 3 m; at the cp05b-04 aerial (0.5-1.5 m per pixel) the sampler takes mip 9-11 of the 2048 tile and mip 11
is one texel. Receipt: `PrecinctMacroV1/inspect-20260911T032433516183Z.json`.

**What changed (asset-only, no map saved).** `MI_PrecinctPlaza_Ashlar` was REPARENTED from
`MI_HerodianV4_Ashlar` onto `MacroV1/M_PrecinctMacroV1_Triplanar` (M_PBR_Tiled's 61 nodes verbatim + a 43-node
base-colour macro tail, vertical faces only, PixelDepth fade 15 -> 60 m), with explicit overrides equal to the
values it resolved before (parity proved). Tone map `T_PrecinctMacro_ToneV2` (per-stone tone on the close tile's
own joints, course-tone runs 2-8 m), weathering map `T_PrecinctMacro_Weather`, `MacroFarStrength` 1.3.
Generator `Scripts/create_precinct_macro.py`; placer `Scripts/release_precinct_macro.py`.

**CONSEQUENCE FOR FUTURE PASSES: this instance no longer inherits from MI_HerodianV4_Ashlar.** A V4/V5 texture
change on the Herodian instances will NOT reach the plaza stone; copy it onto `MI_PrecinctPlaza_Ashlar`.
It feeds the retaining bands, scarp, ribs, kerbs, channels, steps, the 2,391 approach instances and the
Kotel plaza step/kerb/band modules.

**Revert.** `-PMRevert=<retone receipt>` returns to the V1 tone map; `-PMRevert=<apply receipt>`
(`precinct-macro-apply-20260911T033138556043Z.json`) restores the original parent. Checkpoints in
`ReviewCheckpoints/PrecinctMacro-*`.

**Measured result (cp16 vs cp17b frames).** 60 m: 3 m tile-period autocorrelation 0.675 -> 0.368. 1 km: weathering
and stone-tone variation added (gradient energy +42 %), course banding NOT yet resolved. Not accepted as final.

**Companion change.** `SURFACEWEAR_Wear_Soot_GoldenAltar_Ceiling` (DecalActor, MI_Wear_Soot, 182 x 182 cm over
the golden altar) was the translucent grey card under the Heikhal ceiling; hidden (bHidden) on both maps.
Restore: `-PMDecalRestore=Candidate48` / `=Main50`.

## Addendum 11 September 2026 (cp19, IN PROGRESS) - coordination note for other agents

A cp19 pass on the precinct retaining faces is in flight. What it touches, so nobody overwrites it:

* `MI_PrecinctPlaza_Ashlar` -> reparent onto NEW `MacroV1/M_PrecinctMacroV2_Triplanar` (V1 graph + close-albedo
  distance fade toward a `CloseAlbedoMean` vector parameter). `never_stream` on `T_PrecinctMacro_ToneV2` and
  `T_PrecinctMacro_Weather`. **`MI_HerodianV4_*`, `M_PBR_Tiled` and every V5/V5b Herodian texture are NOT touched.**
  If the Herodian close albedo changes, `CloseAlbedoMean` (linear mean of the close albedo) must be recomputed.
* C++: `EnclosureMath.h` (`PlazaBandIsLedge`, `PlazaLedgeWashDegrees`, `PlazaLedgeWashOriginInsetUnrealCm`),
  `MikdashEnclosure.cpp/.h` (`bPlazaLedgeWash`, a rolled wash band on every batter ledge of the fill ring),
  `Tests/EnclosureMathTest.cpp`. Checkpoint `ReviewCheckpoints/PrecinctLedgeWash-20260911T044947659614Z`.
* `Scripts/release_precinct_approaches.py`: flank retaining keyed to the WORLD band grid + ledge washes, then
  `-ApproachRevert` / `-ApproachApply` on Candidate48 (a map save of the approach actor only). An anti-repeat
  revert that restores map BYTES from a checkpoint taken before this apply would undo it - check first.

### cp19 findings (measured before any build - frames pending)

* **The P2 "staircase of ledges" was the S1 APPROACH, not the precinct ring.** The P2 camera (X 10000) looks straight at
  the S1 flight raking west along the south face (footprint X -29280..18624). `release_precinct_approaches.Plan._stack`
  started every 25-amah flank column at its own tread Z and battered by the band index counted from that tread, and
  `_place_flight` pushed the flank face out by the tread's ledge-ride as well. So each column's joints and ledges sat
  one tread lower than the last. Offline, S1 had 762 of 1,261 flank bands off the ring's band grid, 166 distinct
  ledge levels, and a 48 cm face offset between neighbouring columns at the same level (`approach-band-grid-BEFORE-cp19.json`).
  Fix: stacks keyed to the WORLD grid (band k occupies [deck-(k+1)h, deck-kh], batter = PlazaBandBatterUnrealCm(k)),
  flank face on the un-ridden line. After: 0 off-grid, ledges only at -1200k cm (11 levels on S1), 0 cm spread
  (`approach-band-grid-AFTER-cp19.json`). The top band of each column now stands up to one band above the tread as a
  stepped parapet on the open side of the stair. The ring itself was always continuous (keyed to DeckZ).
* **The "unchanged shaded patch on the east face" was two things.** (1) The cp17 metric box `eastFace`
  (2980,1150)-(3100,1250) projects through the P1 camera to X = 153,579 on the south-face plane - 41 m BEYOND the
  SE corner: it measured terrain and roofs, which is why it never changed. (2) The pale smooth block beside the SE
  corner is the SOUTH face itself between X 71,400 and 110,500 (east of the S2 approach footprint, which ends at
  66,624), seen at 1.8-2.2 km at ~17 degrees grazing; the darker strip left of it is the S2 flank in front of the face.
  It did change slightly between builds (mean luminance 0.481 -> 0.476, std 0.044 -> 0.051).
* **Why courses cannot read at the aerial camera, and where the geometry must go.** Rectified through the P1 camera
  (`Scripts/measure_precinct_face_profile.py`), the faces sit at 0.62 (west), 0.74 and 0.93 (south) m per pixel. A
  course is 0.92-1.06 m, i.e. 1.1-1.7 px per period: below the 2 px Nyquist limit, so NO albedo, normal or geometry
  can resolve individual courses from that camera at 3840 px. A 5-amah band (2.4 m, 2.6-3.9 px) is resolvable, but a
  line on every band cannot be baked into the one band mesh: 240 cm is not a multiple of the 300 cm tile, so four
  band boundaries in five cut through textured stones (lcm 1200 cm = 5 bands). The ONLY band boundary that lands on a
  texture bed is the batter ledge every 5 bands (world Z -1200k on Candidate48), 13-19 px apart at P1. So the
  far-field line is built there: a 45-degree wash (one more instance of the same band mesh, rolled, never scaled) on
  every ledge of the fill ring and the approach flanks. A flat 48 cm shelf seen 19 degrees from above projects to
  16 cm (0.1-0.25 px); the wash shows its full 48 cm (0.5-0.8 px) to every camera.
* **Build sync (coordinator note, 11 Sep 00:5x).** `bPlazaLedgeWash` is a new UPROPERTY on AMikdashEnclosure. The cp19
  compile gate builds the GAME target (`-waitmutex`); the cp19 cook is `Checkpoint-Build.ps1`, whose BuildCookRun
  `-build` runs UBT on `MikdashCourtyardV3Editor` and then the game (confirmed in the cp17 uat.log), so editor DLL and
  game exe come out of one source state. Captures are taken ONLY from that archive. Commandlets that run before the cook
  load the older editor DLL; a missing TAGGED property simply takes the class default (true) - not the untagged
  layout break that gave the crowd captures `Bad export index`. The coordinator's own Game build (EXIT=0) compiled the
  patched MikdashEnclosure.cpp.

### cp19 measured (packaged build `C:\Mikdash\Builds\Checkpoint-cp19-20260911T050158Z`, frames `visual-review/cp19-*`)

Cook attempt 1 died on ANOTHER agent's material (ShaderCompileWorker access violation compiling `M_CrowdVAT_V1`);
attempt 2 passed clean (0 errors, 0 warnings, no LogMaterial line for PrecinctMacro/PrecinctPlaza/Herodian), smoke
`playable`. Numbers: `PrecinctMacroV1/accept-cp19.json`, `face-profile-*.json`.

* **P2 (south face at the S1 rake, 70 m): staircase GONE.** Joints and ledges are continuous across the full frame;
  the ledges show as lit washes. What still steps is the parapet TOP of the flank, which follows the stair.
* **P3 (east face, 60 m):** tile-period autocorrelation 0.675 (cp16) -> 0.368 (cp17b) -> **0.263**; the batter ledges now
  read as lit offset courses instead of thin dark lines.
* **P1 (aerial): courses do NOT read.** Rectified whole-face vertical-profile std: west 0.032 / 0.042 / **0.042**,
  south S1-S2 0.017 / 0.021 / **0.021**, south east-of-S2 0.024 / 0.027 / **0.027** (cp16before / cp17b / cp19).
  The close fade removed the one coursing signal the aerial had - the close tile's bed joints averaged into row
  darkening (west-face 3 m-period power 0.126 -> 0.032) - so cp19 reads marginally LESS coursed at 1 km than cp17b.
  Ledge-period (12 m) power: south 0.054 -> 0.119 and 0.260 -> 0.282, west 0.079 -> 0.054; the washes are not
  visible to the eye at 1 km.
* **07 (plaza stone at walking range) changed 12x the noise floor - GEOMETRY, not material.** The world-grid rule
  raised the short straight-out N flight's flank up to 2.4 m above its treads and walled the stair in.
* **02 (4 m jamb):** mean |diff| vs cp17 0.0028 - unchanged (MI_HerodianV4_Ashlar, untouched).

### cp19b (in flight): two corrections from those frames

* **Close fade becomes band-pass** - `M_PrecinctMacroV3_Triplanar` (new asset; `-PMApplyV3`): fade toward the mean over
  20-60 m (the wallpaper range, keeps the P3 gain), RELEASED again over 400-900 m (`CloseFadeOutStartCm` 40000,
  `CloseFadeOutLengthCm` 50000) so the aerial keeps the close tile's bed-joint striation.
* **World band grid only for flights raking ALONG the face (S1, S2).** Straight-out flights (N, E) and head landings
  are back on the exact pre-cp19 rule; offline N/E counts equal the pre-cp19 plan exactly, S1/S2 keep 0 off-grid and
  0 cm spread, washes 242 (`approach-band-grid-AFTER-cp19-alongwall.json`).

### cp19b measured - the state that stands (build `C:\Mikdash\Builds\Checkpoint-cp19b-20260911T052025Z`, frames `visual-review/cp19b-*`)

Cook first attempt, 0 errors / 0 warnings, smoke `playable`, no precinct material fallback in any capture log.

| metric (rectified, whole face) | cp16before | cp17b | cp19 (V2) | **cp19b (V3)** |
|---|---:|---:|---:|---:|
| P1 west face vertical-profile std | 0.032 | 0.042 | 0.042 | **0.037** |
| P1 south face S1-S2 | 0.017 | 0.021 | 0.021 | **0.021** |
| P1 south face east of S2 | 0.024 | 0.027 | 0.027 | **0.027** |
| P1 west 3 m-period power share (bed-joint striation) | 0.059 | 0.126 | 0.032 | **0.196** |
| P3 (60 m) correlation at the 3 m tile lag | 0.675 | 0.368 | 0.263 | **0.276** |
| 02 jamb mean abs diff vs cp17 (noise floor 0.0057) | - | - | 0.0028 | **0.0028** |
| 07 plaza stone mean abs diff vs cp17b | - | - | 0.069 | **0.0036** |

* **Aerial: courses do not read as courses.** A faint horizontal grain (the close tile's bed joints, restored by the V3
  release) plus weathering; the whole-face profile std is where it was. At 0.62-0.93 m/px a ~1 m course is sub-Nyquist,
  so this is the ceiling for THIS camera at 3840 px - the remaining lever is framing (a longer lens / closer camera),
  not material. The 12 m washes register in the south-face spectrum (0.097 / 0.250) but not to the eye at 1 km.
* **60-70 m: accepted.** P2 staircase gone (continuous joints and washes; only the S1 parapet top steps with the stair);
  P3 wallpaper 0.675 -> 0.276 and the ledges read as lit offset courses.
* **No regression:** 02 jamb and 07 plaza stone within the frame-to-frame noise floor.

Revert, newest first: `-PMRevert=precinct-macro-applyv3-20260911T051820114379Z.json` (back to V2) ->
`-PMRevert=precinct-macro-applyv2-20260911T045714985542Z.json` (back to the V1 master + ToneV2, textures' never_stream
restored). C++: copy `ReviewCheckpoints/PrecinctLedgeWash-20260911T044947659614Z/*` back (or set bPlazaLedgeWash false).
Approaches: `ReviewCheckpoints/PrecinctApproachGrid-script-20260911T045033546716Z/release_precinct_approaches.py` is the
pre-cp19 planner; re-run -ApproachRevert / -ApproachApply with it. `M_PrecinctMacroV2_Triplanar` stays on disk, unreferenced.
