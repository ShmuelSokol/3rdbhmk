# StreetTreesV1 review — real trees for modern Jerusalem, 15–16 September 2026

Reviewer: Claude. Previews read by eye, geometry read by measurement.
**Offline work only so far — see "Engine status" before trusting anything about materials.**

---

## The defect, and what it actually was

CP26-REVIEW.md **D4**: *"blob trees clip through the steps."*

- `city-facade/cp26-A1-west-gate-approach-into-old-city.png` — one blob fills the hero foreground.
- `cp26-07-north-gate-approach-plaza-stone-near.png` — blobs drive through the north-gate stair
  and notch the stepped retaining edge.

Looking at those two frames: a plain cylinder trunk carrying two or three overlapping ~12-gon
spheres, flat dark green, no branches, no leaves, no LOD.

**The blobs were never `JudeanFloraV1`.** They are the illustrative OSM family imported with the
city — `SM_JerusalemInstance_Tree_trunks` (4,409 instances, **20-triangle** prototype) and
`SM_JerusalemInstance_Tree_crowns` (13,227 instances, **80-triangle** prototype), three crowns
parented to each trunk, which is the "two-sphere" read. Every trunk carries identity rotation and
`scale [1, 1, 4]` — the cylinder is stretched four times in Z, which is most of why it reads as a
lollipop.

That family is **1,146,340 triangles with no LOD ladder and no cull distance**, resident at every
range. It is not a cheap placeholder; it is an expensive one.

This matters because the memory note `frame-defect-traps-20260910` already recorded that
"vegetation" is **two families and only one carries a tag**. A keep-out or an upgrade applied to
the `JudeanFloraV1` tag does nothing to these, which is exactly why the good hillside flora and
the blob street trees have coexisted in every build since cp09.

## What was built

`Scripts/create_street_trees.py` → **`StreetTreesV1`**, a new namespace (AGENTS.md hard rule 4).
`JudeanFloraV1` is not touched: the generator imports create_vegetation.py and re-points its
output paths, so a StreetTreesV1 run cannot write a byte into the shipped family's folder.

Six species, chosen for what actually grows around the Old City:

| species | habit modelled | where |
|---|---|---|
| olive (*Olea europaea*) | no leader, low fork into equals, sinuous flared bole | lanes, walls, terraces |
| Italian cypress (*Cupressus sempervirens*) | one strong leader, short branches hugging the axis | cemeteries, monastery walls, skyline |
| Aleppo pine (*Pinus halepensis*) | long bare bole under a wide flat parasol | afforested slopes, parks |
| carob (*Ceratonia siliqua*) | very short thick bole, heavy low forks, dense dark crown | rocky slopes, Kidron side |
| Judas tree (*Cercis siliquastrum*) | small, multi-stemmed, vase-shaped, cordate leaf | lanes, gardens |
| date palm (*Phoenix dactylifera*) | ringed bole, shuttlecock crown | valley floors, civic planting only |

The date palm is deliberately restricted to low ground and ornamental civic planting: it needs
groundwater and heat and does not belong on the Jerusalem ridges. Nothing is planted on the Temple
Mount — the enclosure ring plus a 15 m margin is a hard keep-out.

**Reference.** `SourceAssets/context-review/OldCityReferenceV2/reference-notes.md` (street planting
and lighting direction). The private photographs at `C:/Mikdash/PrivateReferences/OldCity-20260915`
were used as **visual direction only**; they are not committed, not imported, and no texture here
derives from them. All textures are procedural, stdlib only — no asset store, no download.

### The generator

- **Recursive forking.** Trunk tapers, leans and forks; each fork forks again to a species-dependent
  order. Child radii follow the **da Vinci / Murray rule** (child cross-sections sum to the
  parent's) rather than a fixed fraction, so a limb can never come out thicker than the wood
  carrying it. Apical dominance is one number per species, and it is the single parameter that
  separates a cypress from an olive.
- **No straight segments.** Every branch spine is curved — `curveUp` bends toward vertical (an olive
  reaching for light) or away from it (a pine flattening into its parasol).
- **Foliage on the wood.** Leaf sprays anchor to branch tips *and* to sampled points along each
  branch, then blend toward a species crown envelope.
- **Variation.** 3–4 independent seeds per species (21 tree variants), each with its own bole
  length, fork angle, length falloff and lean — plus per-instance yaw and scale at placement.
- **LODs and a billboard.** Three-step ladder plus an impostor that is an orthographic render of
  that species' own LOD1 mesh. Screen sizes use the engine's real `radius / d` rule, not the
  `2 * radius / d` error that once made every LOD engage at half its intended distance.

---

## Four defects found by looking at the previews

Each was caught offline, before any engine time, by rendering the actual OBJ geometry and looking
at it. Each was a real bug with a measurable cause.

**1. Every tree was a baobab.** The first Olive sheet had a short fat bole. Measured: the tree
reached **432 cm against a 675 cm species height** — 36% short — because a branch chain whose
length falls by `lengthRatio` each order only reaches `L·(1 + q + q² + …)`, while the trunk radius
is set from `trunkDiameterM` and does not depend on length. Height-to-diameter came out **7.5:1
where the species asks for 11.7:1**. Fixed by calibration: every position in the grower is linear
in the starting length and no direction depends on it, so one dry run at length 1.0 measures the
skeleton's reach per unit exactly and the correct trunk length follows by division. No search, no
magic constant. Now 103–106% of species height.

**2. An identical dark "boot" at the foot of every trunk.** The order-0 tube was straight-sided
with flute and twist at full strength, shading as one flat facet. Fixed with a root flare that dies
away within about a diameter, and flute/twist at half strength — bark fissures are the texture's
job at this range. A repeating pattern in the one place the eye always lands.

**3. The cypress was a bare pole with six lollipops.** The worst bug. Canopy width was derived from
`span` — the **leaf-spray** size, 30 cm on a cypress against a 280 cm crown — so the whole crown
collapsed onto the trunk axis; and with only two branch orders a cypress had ~6 tips total, so 172
clusters piled into six balls. The olive had escaped it only because its tips were already spread
wide. Fixed by taking canopy radius from the **species crown**, adding foliage anchors along each
branch, and giving each species an `envelopeBlend` (cypress 0.88 — its outline is the column, not
any branch inside it; olive 0.28 — an olive's outline *is* its limbs).

**4. Bare twigs protruding past the canopy as straight whiskers.** Visible on three of the four
Aleppo pines. The envelope blend pulls each spray inward, so any terminal branch that won no
cluster was left bare and stuck out. Fixed by seeding one cluster per terminal tip before
distributing the rest by weight — removed by construction, not hidden behind more foliage.

Also fixed: the date palm took height and crown straight from the species table, so every palm
was the same height with the same crown — two seeds that read as one tree.

**6. The Aleppo pine was a rounded broadleaf, and the first fix for it was worse.** A pine carries
its foliage in flattened plates on the tops of up-swept limbs; this one had branches bending
*downward* (`curveUp -0.30`, a weeping habit) and sprays that drifted equally in all three axes
with upright cards, which can only ever make a ball. The fix is a `plateFlatten` rule that
squashes a spray's vertical scatter and lays its cards toward horizontal, plus a crown drawn
toward a plane high in the tree, with `curveUp` turned positive so limbs rise.

**The first attempt at it overcorrected badly and the preview is what caught that too.** Pulling
*every* spray onto one plane at 0.82 of tree height gave a 2 m lamina on a 13 m tree — a pancake
floating over stranded bare branches, a mushroom rather than a pine. Terminal sprays are now
exempt from the collapse, so foliage stays on the twig that carries it: **the plate decides where
the mass of the crown sits; it does not get to lift foliage off its own wood.** Crown depth went
212 cm → 550–800 cm and the crown is now wider than deep over a bole half the tree's height.

---

## Placement, and the intersection proof

`Scripts/create_street_tree_placement.py` — offline, no engine, ~2 s.

**The anchors are inherited, not rescattered.** The OSM trunk positions are real data: OSM park,
garden and orchard polygons, Z already sampled onto this project's terrain, and
`remove_mount_trees.py` has already taken the 144 that stood on the Mount. Rescattering would throw
away the one thing the placeholders got right — *where* trees are in Jerusalem — to fix the thing
they got wrong, which is what a tree looks like. 4,409 − 144 = **4,265 retained anchors**.

**Blockers**, each from its authoritative offline source:

| blocker | source | note |
|---|---|---|
| precinct plaza deck | `release_frame_defects.spec.json` analytic rectangle | **cannot** be measured off the .umap — `BuildPlaza` builds 14,641 tiles at runtime and serialises nothing |
| Kotel plaza deck, steps, kerbs, bands | `kotel-plaza-plan.json` | 959 real instance rows on two levels |
| **the approach stairs** | `release_precinct_approaches.Plan`, re-run offline | per-step transforms are on no receipt; the planner is pure Python over the same DEM |
| architecture | `architecture-manifest.json` | 5 hollow unions decomposed into 162 constituent boxes |
| **Old City foundations** | `OldCityFoundationV2` OBJs | 2,994 per-building plinths and stepped footings |
| Mount enclosure | 66-point ring + 15 m margin | nothing inside it, ever |

Two traps honoured explicitly. **Deck order**: the Kotel decks sit inside the precinct rectangle in
XY but 10–12 m below it, so tested against the precinct first every tree on the Kotel plaza looks
buried and is wrongly kept — smallest footprint first. **Union AABBs**: the five derived-union
architecture meshes span the whole outer court; undecomposed they reject every tree in Jerusalem,
and the script refuses to run if the decomposition yields nothing.

**The foundations were added on the coordinator's warning** that `OldCityFoundationV2` had been
applied to both maps after cp26. The manifest's per-mesh bounds are whole ~500 m tiles and useless
as blockers, but each mesh records its footprints as `triangleStart`/`triangleCount` ranges, so the
real per-building box is measured off the geometry: **2,994 boxes, median 854 cm wide and 78 cm
tall** (matching the design's 30 cm plinth + 45 cm footing course), the tallest stepped footings
reaching 697 cm on steep lanes. A stepped footing is exactly the low, thin, ground-hugging geometry
a trunk passes through while never touching the building above it — the blocker that matters most
for a tree in a lane, and the one class the earlier plan had no data for.

A tree is modelled as a **trunk cylinder under a crown cylinder**, not a bounding box: a box around
a 7 m crown is 7 m wide at ground level too and would refuse every tree within 3.5 m of a wall it
never touches. Rotated modules use their world AABB, which is conservative — it can cost a tree but
cannot pass one that intersects.

### The "926 entries" question

The brief asked whether the downstream reader needs re-running. **926 is a stale count.** It is the
Kotel *cell* count (`derived.deckCells`); the plan carries **959 instance rows** (33 were split at
the stair head). AGENTS.md:2001 lists `release_frame_defects.spec.json`'s vegetation keep-out as a
downstream reader **not re-run** after the Kotel plan moved to v2. This pass sidesteps the question
rather than inheriting it: the planner reads `kotel-plaza-plan.json` directly and blocks against all
959 rows, so it does not depend on the 926 figure being current. `release_frame_defects.py` does not
need re-running *for these trees* — their keep-out is enforced at plan time — but its figure remains
stale for anything else that trusts it.

---

## Measured results

*(filled in from the final generation and placement runs — see the receipts named below)*

- Geometry manifest: `SourceAssets/vegetation-review/StreetTreesV1/street-trees-manifest.json`
- Placement plans: `SourceAssets/vegetation-review/StreetTreesV1/placement-plan-{Candidate48,Main50}.json`
- Intersection proofs: `SourceAssets/vegetation-review/StreetTreesV1/intersection-proof-{Candidate48,Main50}.json`
- Previews: `SourceAssets/vegetation-review/StreetTreesV1/previews/`

### Geometry

**138 meshes, 148,936 triangles.** 22 tree variants (4 seeds each for olive, cypress, Aleppo
pine and carob; 3 for Judas tree and date palm), each with three LODs, plus one billboard per
species.

| species | LOD0 | LOD1 | LOD2 | billboard |
|---|---:|---:|---:|---:|
| Aleppo pine | 7,337 | 1,560 | 416 | 2 |
| carob | 7,316 | 1,548 | 408 | 2 |
| cypress | 5,180 | 1,004 | 284 | 2 |
| olive | 5,888 | 1,176 | 320 | 2 |
| Judas tree | 4,748 | 880 | 236 | 2 |
| date palm | 336 | 140 | 52 | 2 |

**Budget: 180,740 triangles per frame against the 3.5 M foliage ceiling — 19.4x headroom**, on
the same arithmetic `create_vegetation.budget_report` uses (`expected_triangles_per_frame`,
VISIBLE_FRACTION 1/3, 3x clumping safety), so it can be added directly to JudeanFloraV1's load.

For comparison, the blob family this replaces is **1,146,340 triangles with no LOD ladder and no
cull distance, resident at every range**. The upgrade is not merely prettier; it is cheaper in the
far field and bounded in the near field.

### Placement

4,409 source trunks − 144 removed on the Mount = **4,265 retained anchors**.
**12,277 blocker boxes plus 960 deck footprints**, per target.

**Both maps are planned**, Candidate48 (the cook map) and Main50:

| reason rejected | Candidate48 | Main50 |
|---|---:|---:|
| inside the precinct deck footprint | 404 | 411 |
| too close to another tree | 140 | 140 |
| intersects an Old City foundation | 56 | 56 |
| inside the Mount enclosure or its margin | 13 | 13 |
| intersects the approach stair | 8 | 6 |
| intersects the precinct plaza edge | — | 1 |
| **placed** | **3,644** | **3,638** |

**`residualIntersectionsAfterPlacement`: 0 on both.**
**`residualInsideDeckFootprintAfterPlacement`: 0 on both.**
An independent re-check straight off the written plan file counts **0 trees inside the precinct
rectangle**.

The two maps differ by six trees because Candidate48 holds the architecture 4 per cent smaller
and 248 cm west, so its blocker set is not Main50's — which is also why **the plan is written per
target**. It was not at first: a single shared `placement-plan.json` meant generating the Main50
plan silently overwrote the Candidate48 one, and Candidate48 is the map that cooks. Caught before
either was applied; the plans are now `placement-plan-Candidate48.json` and
`placement-plan-Main50.json`, with a proof file and a plan-view preview each.

Both pass `release_street_trees.offline_check()`: 138 meshes, no missing or changed source file,
zero residual intersections, and all 22 `(species, seed)` pairs backed by a real mesh.

Species: olive 670, cypress 682, Aleppo pine 1,031, Judas tree 480, carob 688, date palm 93.
Zones: hill slope 2,936, Old City lane 472, plaza approach 373, valley floor 276, wall perimeter
189, cemetery 19.

**The 8 approach-stair rejections are the cp26-07 defect itself**, and the 56 foundation
rejections are the regression the coordinator warned about — both caught by measurement, offline,
before a cook.

### A fifth defect, found by the plan view and not by the intersection test

The first plan that reported "0 residual intersections" was **still wrong**, and only the
plan-view preview showed it: **329 trees stood inside the precinct rectangle, 293 of them below
deck top** — a median 27 m under, down to 115 m. None *intersected* the deck's thin Z −48…0 slab,
so every one passed a correct 3D test. They were buried under 1.43 km of pavement.

This is `frame-defect-traps-20260910` trap 2 seen from the other side: plants that "look buried
under the precinct deck and are kept". **Being clear of the stone in Z is not the same as
belonging there.** The fix is a deck-footprint rule that rejects on XY alone, which is legitimate
precisely because the precinct rectangle is exact rather than conservative — every one of its
14,641 cells is paved, so there is no hole in it for a tree to stand in. It removed 404 trees.

The lesson worth keeping: **a numeric proof that passes is not the same as a correct result.**
The measurement said zero and the picture said otherwise, and the picture was right.

---

## Engine status

**BOTH MAPS ARE APPLIED AND VERIFIED. The cook and the frames are still outstanding.**

| | Candidate48 (cook map) | Main50 |
|---|---|---|
| status | `saved_reopened_readback_ok_visual_acceptance_pending` | same |
| trees placed (bark + leaf components) | 7,288 | 7,276 |
| added vs reopened | 7,288 = 7,288 **MATCH** | 7,276 = 7,276 **MATCH** |
| `readbackProblems` | `[]` | `[]` |
| blob instances cleared | 16,885 → **0** | 16,873 → **0** |
| mesh slots / material instances | 138 / 18 | 138 / 18 |
| `protectedMapsUnchanged` | true | true |
| map sha **at the time of my apply** | `920c2274…` → `650c2b6c…` | `f15e4c8b…` → `9b70ac1f…` |

**Those two hashes are NOT current and must not be published against.** They are what my applies
produced, and a later materials-only pass left them untouched — but `OldCityStreetsV1` then applied
paving to both maps (16 actors each, 8,602 → 8,618) and saved at **22:07:38** and **22:12:01** local.
The live bytes are now `c516fd2679f88cf7…` (Candidate48) and `2b82ae66d7059244…` (Main50). Anyone
publishing must re-hash after every writer has finished, rather than carrying either pair forward.

**The 1.1 M blob triangles no longer DRAW — but they have not left the build, and that is a
requirement I did not meet.** `SM_JerusalemInstance_Tree_crowns` and `_trunks` went to zero
instances on each map (12,658/4,227 and 12,648/4,225), so nothing renders and the per-frame cost
is gone. The actors, components and meshes were deliberately left in place, on the reasoning that
an empty ISM is reversible in a way a deleted actor is not, and that those assets belong to the
city import rather than to this pass.

Measured afterwards, that reasoning does not satisfy the brief. Both maps still reference
`JerusalemInstance_Tree` in their saved bytes, all four assets remain under
`Content/MikdashV3/JerusalemContext/DecorativeInstancesV1/`, and the staged
`MikdashCourtyardV3-Windows.utoc` still carries the family — because the emptied HISM components
keep the meshes alive as references, so they still cook and still ship. **The triangles left the
frame, not the package.** Making them leave the package needs a further guarded map mutation that
deletes the components, followed by a re-cook. That is outstanding work, not done.

All three masters read back off the SAVED assets with their usage flags set:
`used_with_instanced_static_meshes` and `used_with_static_mesh` on all three, plus
`used_with_nanite` on bark.

**The revert works, and was exercised rather than asserted.** `--revert=<receipt> --dry-run` on
each map resolved its checkpoint, confirmed the restore-target sha against the current applied
bytes, returned `revert_dry_run_checkpoint_verified_nothing_written`, and left the map
byte-identical afterwards.

### Two failures on the way, both caught by the guard

**1. The first Candidate48 apply lost every instance.** It reported success in-editor and then
reopened with `0 of 282 instances` on all 44 components. Cause: constructing
`ue.HierarchicalInstancedStaticMeshComponent(actor)` produces a component the level never owns —
UE 5.8 marks `AddComponentByClass` `ScriptNoExport`, so the editor's `SubobjectDataSubsystem` path
is the only route to a component that serialises. `release_vegetation.new_hism` had solved this
already and its docstring says so in as many words. **The save/reopen/numeric-readback guard is
the only reason this was caught**, and it is exactly what that guard exists for. Worse, the blob
clearing had already saved, so the map was briefly left with no trees of either kind.

**2. The documented `--revert` did not work when it was first needed.** `restore_checkpoint()`
reads top-level `map` + `mapSha256Before`; the receipt recorded only a `mapHashesBefore` dict, so
the revert refused and the broken map had to be restored by hand from the checkpoint. Fixed, and
then exercised on both maps. A revert that has never been run is not a revert.

### The cook

Three cooks were needed, all `Checkpoint-Build.ps1 -UseExistingBinaries`, each **8,949 of 8,949
packages, 0 remaining, no `ERROR:` and no `BUILD FAILED`**, each smoke-tested `playable`:

| label | archive | result |
|---|---|---|
| `trees01` | `Checkpoint-trees01-20260916T010931Z` | cardboard — empty material graph |
| `trees01b` | `Checkpoint-trees01b-20260916T014159Z` | cardboard again — atlases never saved to disk |
| `trees01c` | `Checkpoint-trees01c-20260916T021244Z` | graph wired **and** 24 atlases on disk |

`trees01c`: exit 0, 4,248,752,537 bytes, smoke `playable` (window in 18 s, peak 3,752 MB),
`mainMapChangedDuringCook: false`.

**Staged child exe: `de6dc228c3526d1143dd3389e0a9ccdd56f2c048b5a8dd8d3d972bc42ad22d2b`**,
340,167,168 bytes, at `Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe`. That is
the hash of what was actually staged, stated as a fact about this archive; it is a different child
from cp26's `5cc71b34…`, and this note deliberately makes no claim about which C++ it contains.
`-UseExistingBinaries` stages whatever binaries were current, not a compile of this pass's own.

**The material-substitution check is clean.** Zero occurrences in the cook log of
`missing usage flag`, `needs to be recompiled`, `bUsedWithInstancedStaticMeshes` or
`WorldGridMaterial`, with StreetTreesV1 packages present in the cook. That is exactly the
signature that was ABSENT when cp05b shipped cardboard foliage.

**That check was clean for `trees01` and `trees01b` too — and both shipped black cardboard.** This
is worth stating plainly, because it is the single most transferable lesson in this file. A clean
substitution check proves only that the engine found *a* material and did not swap in a fallback.
It cannot see a material whose graph is empty, and it cannot see a material instance pointing at a
texture package that was never written to disk. Both of those compile, cook and run without one
line of complaint. The absence of an error signature is not evidence of a correct frame.

**The RUNTIME log is clean too**, checked separately on the packaged game during capture:
`missing usage flag` 0, `needs to be recompiled` 0. There is exactly one `WorldGridMaterial`
mention and it is benign — line 817, `LogStreaming: Display: Partially loaded package
/Engine/EngineMaterials/WorldGridMaterial (state: WaitingForIo) to avoid deadlock when it was
recursively flushed by /Engine/EngineMaterials/DefaultTextMaterialOpaque`. That is an engine
start-up streaming diagnostic about load ordering, not a material fallback, and it names no tree
material. It is recorded here because a bare grep count of "WorldGridMaterial: 1" looks exactly
like the cp05b cardboard failure until you read the line.

**But this is necessary, not sufficient, and the note in `nullrhi-cannot-verify-materials` still
stands: a cooked log can prove a substitution happened; it can never prove one did not.** Only a
frame settles it.

### The frame found a seventh defect, and it is the most important one in this file

**`trees01-A1-west-gate-approach-into-old-city.png` shows the tree with a correct forked trunk
and a correctly placed crown — and foliage made of large, flat, hard-edged, near-black
RECTANGLES.** The leaf cards are drawing as solid opaque quads, not alpha-cut leaf sprays. The
blob is gone and cardboard has replaced it.

**Cause, and it is mine.** `build_masters()` set blend mode, two-sidedness, shading model,
opacity-mask clip value and the usage flags — and then saved the material **without creating a
single expression**. Measured on the script that shipped it: `create_material_expression` = 0,
`connect_material_property` = 0. A `BLEND_MASKED` material with nothing wired to OpacityMask is
opaque everywhere, and an unconnected BaseColor is black. The `MI_…` instances then set a
`LeafAtlas` texture parameter that **did not exist on the parent**, so the atlas bound to nothing
and failed silently.

**Why every check upstream stayed green, which is the part worth remembering.** There was no
substitution, so the cook log was clean. The material existed and compiled, so there was no
`missing usage flag` and no WorldGridMaterial fallback. The usage flags read back `True` off the
saved assets. The instances were created and the slots assigned, 138 of them. `-nullrhi` cannot
draw a pixel. **Every single guard I had was measuring the material's PROPERTIES, and not one of
them looked at its GRAPH.** This is `nullrhi-cannot-verify-materials` in its purest form:
parameter parity is not visual acceptance, and only the frame found it.

**Fix**: the leaf/bark/billboard graph is now ported from `release_vegetation_materials.py`
(stock nodes only, no Custom). The line that matters is
`to_property(atlas, 'A', 'MP_OPACITY_MASK')`. Two new assertions make the failure unshippable:
the master is refused if it compiles with zero expressions, and refused if it is `BLEND_MASKED`
with nothing connected to OpacityMask. The masters are also **deleted and recreated fresh** rather
than re-authored in place — re-authoring superimposes the old graph on the new one (duplicate
`LeafAtlas` samplers), and that superimposed material is what cp05b cooked.

**Materials were therefore NOT accepted on trees01.** The flags were right, the cook was clean, and
the trees still rendered as cardboard.

### The first fix, and what the receipt proved — which was not the frame

Re-authored with `-StreetTreesMaterialsOnly` on **both** maps
(`release-street-trees-Candidate48-20260916T014040852404Z.json` and the Main50 twin):

| master | expressions | connections | OpacityMask |
|---|---:|---:|---|
| leaf | **10** | 11 | `TextureSampleParameter2D.A -> MP_OPACITY_MASK` |
| billboard | **9** | 10 | `TextureSampleParameter2D.A -> MP_OPACITY_MASK` |
| bark | **5** | 5 | n/a (opaque); `RGB -> MP_BASE_COLOR` |

Previously every one of those numbers was **zero**. 138 mesh slots and 18 material instances
reassigned, `allMapsUnchanged: true`.

**A materials-only mode had to exist first.** Re-running the full apply to fix a material would
have cleared an already-empty blob family and placed a SECOND 7,288 instances on top of the
first — the trees would have silently doubled. The mode rebuilds masters and slots, touches no
map, and asserts every map is byte-identical afterwards.

**Rebuild:** `Checkpoint-Build.ps1 -Label trees01b -UseExistingBinaries` →
`C:\Mikdash\Builds\Checkpoint-trees01b-20260916T014159Z`, **`checkpoint_playable`, exit 0**,
8,949/8,949 packages, smoke `playable` (window in 30 s, peak 3,827 MB), substitution count **0**.
Staged child `de6dc228c3526d1143dd3389e0a9ccdd56f2c048b5a8dd8d3d972bc42ad22d2b` — the same child
as trees01, which is expected: `-UseExistingBinaries` stages the same binaries and only the cooked
content differs.

**Rule added** (AGENTS.md hard rule 11): a material is accepted on its GRAPH, never its flags —
assert a non-zero expression count and a real `MP_OPACITY_MASK` connection, and re-author into a
fresh asset.

One finding worth keeping: **UE 5.8 has no `bUsedWithFoliage`.** Verified against
`Engine/Source/Runtime/Engine/Public/Materials/Material.h`, which declares
`bUsedWithInstancedStaticMeshes`, `bUsedWithStaticMesh` and `bUsedWithNanite` and no foliage flag at
all — foliage is drawn through instanced static mesh components, so the ISM flag *is* the foliage
flag. Setting a flag that does not exist would have raised in the usage-flag checker. Nanite usage
is set on the bark master only; the leaf and billboard masters are alpha-masked, and this project's
own Nanite eligibility rule deliberately excluded the decorative foliage HISMs.

### The eighth defect: the frame did not change, and the cause was a different bug wearing the same face

`trees01b-A1-west-gate-approach-into-old-city.png` is **visually identical to `trees01-A1`**. The
same solid, hard-edged, near-black rectangles. The two files are genuinely different bytes
(11,427,903 vs 11,445,094, different SHA-256), so this is a real new render of a real new cook —
the picture simply did not change.

**Cause, and it is mine again.** The atlas textures were imported with
`AssetImportTask.save = False`, and **nothing ever saved them**. Meshes, masters and material
instances were each saved explicitly; the textures were not. Measured from a fresh process: 21
material assets and 138 mesh assets exist under `Content/MikdashV3/Vegetation/StreetTreesV1/`, and
the `Textures` folder **does not exist at all** — `T_*.uasset` on disk is **0** against 24 expected.
The staged build likewise contains no StreetTrees textures.

**Why every check stayed green a second time.** The textures were live in the session that
imported them, so `EditorAssetLibrary.load_asset` returned them, the CLAMP pass counted
`texturesClamped: 12`, and `set_material_instance_texture_parameter_value` bound them without
complaint. The receipt recorded all of that truthfully. But the packages were never written, so the
saved material instances referenced texture packages that did not exist; the cook resolved them to
nothing and the sampler fell back to the engine default — alpha 1 everywhere, RGB near-black.
**A `BLEND_MASKED` card with a dead atlas looks exactly like a `BLEND_MASKED` card with an empty
graph.** Two unrelated bugs, one appearance — which is exactly why the second survived the fix for
the first, and why the graph assertions I added passed while the frame stayed wrong.

The source art was never at fault: all 12 leaf and billboard atlases are 8-bit RGBA PNGs
(`colortype 6`) carrying a real alpha channel, and the bark maps are correctly alpha-less RGB.

**Fix**: `import_assets()` now saves every imported texture *after* its CLAMP / normal-map / sRGB
settings are applied, then asserts the `.uasset` exists on disk and raises if it does not —
`texturesSaved` must be 24 and `texturesMissing` must be empty or the pass refuses to continue.
**Rule added** (AGENTS.md hard rule 12): an asset that LOADS is not an asset that SAVED. Assert the
bytes on disk from a fresh process, because the session that created an asset is the one witness
that cannot confirm it shipped.

**Verified** on both maps (`release-street-trees-Candidate48-20260916T020939948907Z.json` and
`release-street-trees-Main50-20260916T021005530446Z.json`): `texturesSaved: 24`,
`texturesMissing: []`, `allMapsUnchanged: true`. Counted independently from a fresh process, the
`Textures` folder now holds **24 `T_*.uasset`** — 6 species × leaf atlas, billboard atlas, bark
base colour and bark normal. Because this was a materials-only pass, neither map was touched by
it — though both maps were later changed by `OldCityStreetsV1`, so the hashes quoted above are the
values at apply time and not current bytes.

### The ninth defect, and it is the one that caused all three cardboard cooks

`trees01c-A1` and `trees01c-07` are **again** visually identical to their predecessors. With the
graph wired and all 24 atlases provably on disk and in the package, the frame did not move.

**The meshes were never wearing my materials.** Asked from a separate process, every mesh answers:

```
SM_StreetTreesV1_Olive_S0_L0_Leaf -> /Engine/EngineMaterials/WorldGridMaterial
SM_StreetTreesV1_Olive_S0_L0_Bark -> /Engine/EngineMaterials/WorldGridMaterial
```

**Cause: a UE array property mutated in place.** `get_editor_property('static_materials')` returns
a COPY of the array, and indexing it returns a COPY of the struct, so
`slots[index].set_editor_property('material_interface', material)` wrote to a temporary that was
then discarded. `set_editor_property('static_materials', slots)` stored the ORIGINAL entries back,
`save_asset` saved them faithfully, and `assigned += 1` counted a success. Across three cooks the
receipts reported `meshSlotsAssigned: 138` and `meshSlotErrors: []` while all 138 meshes sat on the
engine default — an opaque grey material with no alpha, which is precisely a flat dark rectangle.

**Everything else was correct the whole time**, which is why this took three cooks to find:

| layer | measured | verdict |
|---|---|---|
| leaf master | 10 expressions, `BLEND_MASKED`, clip 0.5, `MSM_TWO_SIDED_FOLIAGE`, ISM usage | correct |
| material instance | parent `M_StreetTrees_Leaf`, `LeafAtlas` → `T_Olive_Leaf_BCA` | correct |
| atlas art | 512², binary alpha (0/255 only), 43.5% opaque, mean RGB (97,113,74) | correct |
| leaf card UVs | 5,904 `vt`, 16 distinct, range 0.002–0.998, 2×2 atlas grid | correct |
| textures in package | 7 `T_*_Leaf_BCA` in the `trees01c` `.utoc` | correct |
| **mesh material slot** | **`WorldGridMaterial`** | **the defect** |

The atlases even cooked into the package — because the *material instances* reference them, though
no mesh referenced the instances.

**The tell I had in hand from the first frame and misread twice: the leaf cards and the trunk are
the same flat dark tone.** Two different meshes with two different materials cannot match by
coincidence; they matched because both were the engine default. I read that as "dark foliage in
shadow" and went looking at materials instead of at the mesh.

**Fix**: rebuild the slot array from fresh `ue.StaticMaterial()` structs rather than mutating
copies, then RELOAD the saved mesh and assert the slot resolves to the intended instance — the pass
now refuses if any mesh still reports `WorldGridMaterial`. **Rule added** (AGENTS.md hard rule 13):
assert the binding, not the loop counter, and never mutate a UE array property in place.

**Verified from a separate process** (receipts `…Candidate48-20260916T023740103570Z.json` and
`…Main50-20260916T023809174269Z.json`, both carrying `scriptSha256 f32b0dbc…` — the fixed script;
the three cardboard cooks ran `dc15db12…` and `74481c80…`). All 138 mesh assets were re-saved, and
a fresh editor now answers:

```
SM_StreetTreesV1_Olive_S0_L0_Leaf -> MI_StreetTreesV1_Olive_Leaf
SM_StreetTreesV1_Olive_S0_L0_Bark -> MI_StreetTreesV1_Olive_Bark
```

One trap inside the trap, worth recording because it nearly cost a fourth cook: the slot is still
*named* `WorldGridMaterial`, because that is what UE calls a slot imported from an OBJ that carries
no material. The NAME is cosmetic; the `material_interface` is the binding. A `grep -c
WorldGridMaterial` over the diagnostic counts those names and reports failure on a mesh that is
correctly bound — a false negative that would have refused to cook a working build. Read the field,
not the file.

### The tenth defect, which was in the write-up rather than the build: a stale hash

I reported `650c2b6c…` and `9b70ac1f…` as the final map hashes, said they had been "re-verified
byte-for-byte against the live files", and handed them over as **safe to publish against**. They
were none of those things by the time I wrote it.

- My applies produced them at 20:56:55 and 21:00:03. **True.**
- I hashed the live files at about 22:00–22:05 and they matched. **True when taken.**
- `OldCityStreetsV1` saved paving into both maps at **22:07:38** and **22:12:01** — minutes later.
- I went on quoting the old pair until **23:45**, roughly **95 minutes stale**, including in the
  hand-off file other agents read.

**The refutation was in my own output.** My `trees01d` cook receipt recorded
`candidateSha256Before/After: c516fd26…` and `mainSha256Before/After: 2b82ae66…`. I read that block
while checking the cook, quoted `mainSha256After` from it in my own notes, and did not notice it
disagreed with the hash I was still reporting.

This is the same mistake as the three cardboard cooks, wearing different clothes. An empty graph, an
unsaved texture, an unbound mesh slot and a stale hash are four shapes of one error: **a reading that
was true once, carried forward as though it were still true.** The cure is the same in all four
cases — take the measurement again, at the moment you rely on it, from outside the thing that
produced it. On a shared map with several passes in flight, a SHA-256 is a statement about a moment,
not a property of the file. **Rule added** (AGENTS.md hard rule 14): a hash is current only if it was
taken after every other writer finished; print the timestamp beside it so staleness is visible.

## Verdict

**Do they read as real Jerusalem trees, or as game props? In the fourth cook's frames: as real
trees, clearly — and not yet as a finished Warner Brothers frame.**

### What the frames actually show (`trees01d`, the first cook in which my materials were on the geometry)

`trees01d-A1-west-gate-approach-into-old-city.png`, tree at 15 m, eye height 4.2 m:

- **The leaf cards read as leaves.** Individual leaflets break the crown's outline against the
  sky and daylight comes through the gaps. The alpha mask is doing its job; there is no trace of
  the solid rectangle. Against `cp26-A1` (a cylinder with two spheres) and the three cardboard
  frames, this is the defect fixed.
- **The green is wrong for Jerusalem.** It is a fresh, saturated mid-green — nursery green. Real
  foliage here in the dry season is greyer, dustier and duller, especially olive and pine. This is
  a tint problem, not a geometry problem, and it is the single most visible thing still off.
- **The crown is too thin.** You see through it more than you should. At this distance it reads as
  a young sapling rather than an established street tree; it wants more leaf sprays per branch.
- **The near tree is an Aleppo pine and it reads as a broadleaf.** Small rounded leaves, no needle
  character, no tiered plates. The frame confirms the weakness I recorded from the silhouettes
  rather than clearing it — this is the species I most want to redo.

`trees01d-07-north-gate-approach-plaza-stone-near.png`:

- **D4 is fixed.** The ridge tree is finely foliaged instead of blob or black cubes, and it is
  clear of the north-gate stair and the stepped retaining edge. Nothing drives through the steps.

**One honest gap in the acceptance itself.** A1's camera cone contains exactly **one** tree within
200 m (50 within 500 m, 364 within 1 km), so it tests one crown at walking distance well and tests
repetition across a street not at all. I computed a dense viewpoint for that purpose — 29 trees of
5 species within 40 m, centred (−8225, −76350) — but the engine slot was handed back before I
captured it. **Whether the crowns repeat visibly along a street is not yet proven in a frame.**

What can also be claimed, because it was measured or looked at:

- **They are unambiguously trees, not blobs.** Tapering forked trunks with root flare, branch
  structure to three orders, foliage hung on the wood, correct height-to-diameter, LODs and
  impostors. The cp26 blob is a cylinder with two spheres; these are not in the same category.
- **They do not read as clones.** The group shot puts 21 variants side by side under
  per-instance yaw and scale: heights, lean, fork height and crown shape all differ. This was
  fixed deliberately — the first four olives differed only in twig detail and read as one tree
  rotated four ways, which is exactly the repeating pattern the standard refuses.
- **Species are distinguishable at silhouette range**, which is the test that matters in a wide
  city shot: cypress columns against pine and carob crowns against a palm.
- **Nothing intersects built geometry**, proven offline against 12,277 blocker boxes and 960 deck
  footprints, including the north-gate stair in the defect frame and the 96 new Old City
  foundations.

Where they fall short, species by species:

- **Cypress — the best of the six.** Genuinely columnar, right proportion, real variation.
- **Carob — good.** Dense dark rounded crown over a short heavy bole; reads correctly.
- **Olive — good but generic.** Correct slenderness and a lower crown after the fix, but it reads
  as a Mediterranean broadleaf rather than specifically as an olive; a real olive has a greyer,
  more billowing crown over a more sinuous, often hollowed bole.
- **Judas tree — acceptable.** Small, vase-shaped, visibly multi-stemmed. Out of blossom it is
  doing little to distinguish itself; the pink flush that makes this tree recognisable in a
  Jerusalem spring is not modelled at all.
- **Aleppo pine — improved over three attempts, still not right.** It now has the long bare bole
  at about half the tree's height and limbs that leave the trunk and turn up and out, which the
  first two versions did not. But in the silhouette sheet it still reads as a **rounded
  broadleaf**, not as a pine: the crown closes into a dome instead of separating into the flat,
  tiered, horizontally-layered plates that are the whole signature of *Pinus halepensis* against
  a Jerusalem skyline. The dedicated plate rule (`plateFlatten` 0.46, `platePlaneFraction` 0.76)
  moved it partway and then stalled — my first attempt at that rule overcorrected into a 2 m
  pancake on a 13 m tree, and the value that fixed the pancake also gave back most of the dome.
  It is the weakest of the six and I am not claiming otherwise. A few short faint twigs also
  still show at the crown edge.
- **Date palm — adequate.** Three seeds now differ in height, crown and lean, but the crown is
  thin and the bole lacks leaf-base ring relief at close range.

Two honest caveats about the previews themselves. They are **orthographic renders with flat
shading and no ambient occlusion**, so they prove silhouette and structure and say nothing about
how the foliage will read once the two-sided foliage material, alpha test and real lighting are
applied — which historically is where this project's vegetation has both failed badly and
recovered well. And a handful of short faint bare twigs still protrude on the pine and Judas tree;
they are sub-pixel at any real viewing distance but they are real geometry.

**What it cost, stated plainly.** It took four cooks. Three of them — `trees01`, `trees01b`,
`trees01c` — shipped flat near-black cardboard, from three unrelated causes with one identical
appearance: an empty material graph, then atlases that were never saved to disk, then 138 meshes
still wearing the engine default because a UE array property was mutated in place. Every one of
those passed a clean cook, a clean substitution check and a green receipt. The offline previews
could not have caught any of them, because all three failures live between the asset and the
triangle, and a `-nullrhi` run cannot draw a pixel.

**Status.** The blob defect is fixed and shown fixed in a frame. The trees read as trees, do not
intersect anything, and hold their silhouette at walking distance. Three things are still wrong and
I am not claiming otherwise: **the foliage tint is too fresh and green for Jerusalem**, **the crowns
are too sparse**, and **the Aleppo pine still reads as a broadleaf**. One thing is unproven: **street-
level repetition**, because the dense viewpoint was never captured. And one requirement was not met:
**the 1.1 M blob triangles still ship** — see the engine-status section.

## Limitations, stated rather than buried

- Visual acceptance exists now, but it is **two frames from one map** (`trees01d`, cooked from
  Candidate48): A1 at walking distance and 07 at the north gate. No street-level frame with several
  trees in it was ever captured, so repetition along a street is unproven. The offline previews
  remain orthographic renders with flat shading and no ambient occlusion; they prove **shape**, not
  appearance, and they proved nothing at all about the three material failures.
- Old City building **shells** are still not blockers — the repository has no per-building AABB for
  them, only 104 grid-cell boxes of ~130 × 99 m that would reject every tree in the Old City. Their
  **foundations** are blockers, and at ground level that is the stricter test.
- Species habit is a stylised procedural approximation, not a scan or a survey.
- Nothing here is halachic.
