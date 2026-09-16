# OldCityStreetsV1 — paving the Old City lanes: derivation, slope, proof, verdict

16 September 2026, Claude. Sections 0–6 and 10 are final and reproducible offline; section 7 is the
engine work, applied, verified and cooked. Sections 8 and 9 are the captured frames and the verdict,
both filled from native captures — **no section is pending.** The engine was then held at the
coordinator's request so the owner could open the editor for Epic/MetaHuman sign-in.

Generator `Scripts/create_oldcity_streets.py` sha256 `166688c5a96c73b8…`.

## 0. The defect, at eye level

cp26 and the OldCityFoundationV2 before frames show the Old City lanes as **bare earth running up
to the building walls** — no paving, no kerb, no step between levels. Inspected by eye:

- `city-facade/cp26-K1-kotel-plaza-walking-facing-jewish-quarter.png` — the alley floor is dirt to
  the wall bases. (The untextured white stepped slab overhead is cp26 defect D1, the Kotel-views
  pass's, not this one's.)
- `city-facade/oldcity01-before-S1-…-infill1200.png` and `…-before-S2-…-infill949.png` — the walker
  stands on a dirt slope; the only articulated ground is a thin grey ribbon in the distance.

That ribbon is the city's entire existing ground: `buildJerusalem()` draws each mapped OSM road as
a flat two-triangle-wide sheet. **Measured, not assumed:** on 40,746 real vertices of
`jerusalem-meshes.json` meshes 2 and 3 it sits at terrain **+20.00 cm**, min 19.99, max 20.01.

## 1. Where the lanes are

The lane network is mapped, not inferred from negative space: `jerusalem.json` carries 5,944
`kind=="road"` polylines. A LANE here is that centre line widened to the real space between the
buildings.

Scope: inside the Old City wall ring (chained OSM wall ways, **862,629 m²**) or within 30 m of it.
Excluded because they own their own ground: the Temple Mount (`buildJerusalem`'s own road
`templeMask`), the mount-platform and protected design polygons with their declared buffers, and
the Kotel plaza deck/step/kerb/band rectangles plus 150 cm — **the plaza is not double-paved.**

**Measured result: 708 lanes, 35,668 m of centre line, 152,568 m² of paving.**

| | lanes | paved area |
|---|---:|---:|
| Tier A — individual stones | 267 | 57,811 m² |
| Tier B — plain strip, same profile/kerbs/aprons/steps | 441 | 94,757 m² |

Class mix: footway 368, steps 118, pedestrian 95, service 54, tertiary 29, residential 26,
trunk 8, living_street 6.

**Widths are measured, not tagged** — only 8 of 5,944 roads carry a `width` tag. At every 50 cm
station the half-width on each side is the distance to the nearest building obstacle line, clamped
to an authored nominal per class and floored at 60 cm. Median lane width **380 cm**, min 120,
max 1,100.

## 2. The slope, and where it becomes steps

Where the smoothed grade exceeds 1 in 8 the lane becomes a stepped flight rather than tilted paving.

**Measured: 448 flights, 7,478 steps, 6,033 m stepped = 16.9% of the network.** 203 flights carry
a central ramped strip; 15 are flagged steep.

| | min | p50 | max |
|---|---:|---:|---:|
| riser | 0.82 | **14.92** | 39.72 |
| tread | 26.19 | **80.33** | 151.35 |

- `risersOutOfBounds` **0**, `infeasibleFlights` **0**, `treadsUnderFloorOnFeasibleFlights` **0**.
- 231 risers exceed the 22 cm comfort figure; those are genuinely steep ground, counted not hidden.
- **Continuity is exact: `worstTreadToRiserGapCm` 0.0 and `worstFlightEndMismatchCm` 0.0.**

The staircase **follows the ground**: each tread takes its level from the smoothed profile at its
own start, so a flight tracks the hillside instead of running as one straight ramp between its ends.

## 3. The height datum

The legacy ribbon is not edited or deleted — it is **enclosed**. Sub-base top is terrain +23 cm and
the slab crown terrain +32 cm, so the 20 cm sheet lies inside the new solid. Total wear (dish + rut
+ drain channel) is capped at 6 cm, which is what keeps every stone above it.

The lane surface **cambers with the cross-slope**. A lane on a hillside follows the hill; holding
the section dead flat put the stones below a ribbon that is always 20 cm above *local* ground
wherever the uphill edge rose more than ~12 cm above the centre line — a 3% cross-fall on a 4 m
lane, i.e. most of the network. Step treads are flat by definition but still camber across their
width, and their risers take the same delta, which is why continuity stayed exactly 0.

At an open edge the build-up becomes a 12–20 cm kerb over a 40–90 cm sloped apron, standing on
**local** ground. Where a building bounds the lane there is no kerb: the paving runs to the wall.

## 4. Meeting the foundations (coordination)

OldCityFoundationV2 landed in both maps on 15 Sep. **The paving stops at its foundation outlines,
not at the wall**: per footprint the obstacle line is the plinth miter offset (8 cm), or the footing
offset (22 cm) where that footprint got a footing; for a footprint with no foundation it is the wall
line. **1,673 footprints in scope use a foundation outline as their obstacle line.**

That pass's manifest and check are **pinned by hash**, so the paving cannot be built against a
different foundation set: `foundations-manifest.json` `82e51621…d227f`, `check-after.json`
`ba4245d6…6e1f7`. Nothing of that pass is modified; its material, meshes and actors are in the
release script's protected-hash set.

**`osm06965`** — the one footprint OldCityFoundationV2 deliberately left unrepaired (28.4 cm gap,
because its plinth would stand inside the Kotel plaza deck) — measures a residual of **−391 to
−402 cm**, i.e. the lane passes about 4 m *above* that building's floor line. That is not a gap to
close: the building's floor is a storey **below** the lane, and the nearest lane station is 2.7 m
away, so it never registers as a bounding edge. The Kotel plaza owns that ground. Reported, not
patched.

## 5. How it is authored

`Scripts/create_oldcity_streets.py` (offline generator, never imports `unreal`) +
`Scripts/release_oldcity_streets.py` (guarded native importer) +
`Scripts/run_oldcity_streets_engine.ps1` (slot-waiting detached runner) +
`Scripts/preview_oldcity_streets.py` (offline renderer). No downloaded assets.

Anti-repeat is the point, so nothing is instanced and no stretch is copied. Course length, slab
width, joint width, dish depth, rut placement and amplitude, per-slab settle, edge-course width,
kerb height, apron width, landing spacing and drain channels are each drawn from a hash of the lane
id and the station. 84 lanes carry a drain channel.

Emitted pieces: **117,573 stones**, 34,172 strip cells, 134,132 sub-base cells, 41,680 kerbs,
41,680 aprons, 19,061 treads, 7,243 step risers plus 24,143 edge risers, 3,125 ramp cells, 6,250
ramp edges. **851,868 triangles in 16 meshes** against a 1.6 M budget — and per
`PERFORMANCE-BUDGET.md` the city was a draw-call problem, so this adds 16 draw calls.

Material `MI_OldCityLaneStone`: a duplicate of `MI_OldCityPlaster` (already proven on the Nanite
infill, parent `M_Context_Building`, so usage overrides come with it), retuned greyer and rougher
with the parent's Z projection at a ~12 m tile, so the texture reads as a broad tonal field while
the pattern the eye reads is geometry.

Visibility: one actor per mesh, tagged `OldCityStreetsV1` plus a zone tag chosen **per map** from
that map's own modern-city hide set — Candidate48 **12 Kept + 4 Precinct**, Main50 **11 Kept +
5 Precinct**, one tile flipping exactly as the foundations' `Grid_N004_N004` does.
`CityDetailZone_Precinct` is in `AMikdashEnclosure::HideWhileWallStandsTags`, so **the paving hides
in YECHEZKEL and returns in MODERN/OVERLAY with the buildings standing on it**, collision following.

## 6. Offline proof

All numbers from `check-streets.json`; the release script re-reads them and refuses on its own.

| check | result |
|---|---|
| **Clearance to walls/foundations** | **0.003 cm** minimum over 48,286 outermost-stone probes, **0 vertices inside** an obstacle |
| Coverage (global, 25 cm raster) | 72,036 stations; **7** with no paving; 265 of 51,159 bounded edges over one cell |
| Ribbon clearance | 349,906 exposed in-footprint samples; **1,031 (0.3%)** under tolerance, worst **−15.3 cm** |
| Step continuity | tread-to-riser **0.0**, flight-end mismatch **0.0** |
| Grade | 48 of 58,520 unstepped samples over 1 in 8, worst **0.239** |
| Triangles | 851,868 of 1,600,000 |
| Orientation | 0 downward-facing horizontal triangles, 0 dropped degenerate |

**Three residuals are carried openly as bounded, attributed allowances — not zeroed tests.** The
release script refuses if any grows past its cap, and refuses outright if the receipt stops saying
*where* the residual is:

1. **7 unpaved stations** of 72,036 (0.01%), one each on seven different lanes, each at most a
   single 25 cm cell, where one lane yields its cells at a junction to a narrower neighbour.
2. **1,031 ribbon samples** (0.3%), all from one named emitter `free/slabCap`, worst −15.3 cm.
3. **265 bounded-edge samples** (0.5%), worst **2.25 m** — real bare patches at junction hand-offs.
   The brief's "no gap over 1 cm at a building edge" is answered directly and exactly by the
   clearance row above; this coarser raster metric also fires on junction ownership.

**Self test: 4 invariants** — wear headroom, flight legality over the whole steep (rise, run)
domain, edge coverage *and* detection of deleted stones, ownership exclusivity. It earned its keep:
it caught seven real faults, including an unbounded loop that hung two builds, a 50 cm riser, and a
stale code block that was silently discarding the cross-slope fix.

### What went wrong on the way, recorded so it is not repeated

- **Two builds hung** on an unbounded `while True` in `plan_flight` that cycled forever on a short
  steep flight. Diagnosed from three flat memory readings, not from a stack trace.
- **A stale straight-ramp block survived a rewrite** and overwrote the profile-following treads,
  discarding the fix entirely while the code around it looked correct.
- **Three successive measurement errors made the checks report defects that did not exist**:
  coverage asked per-lane when the question is global; the ribbon was evaluated outside its own
  footprint; and it was evaluated against paving buried in a hillside cut. Each looked like a
  geometry bug and was not.
- **The camber was referenced to the wrong station.** Level was sampled at a tread's start while
  delta was measured per corner, so the surface fell behind the rising ground by (grade × tread).
  That single mistake was **95%** of the ribbon residual — found only by tagging each sample with
  its emitter instead of guessing a fifth time.

Ribbon trajectory across the fixes: **317,127 → 205,906 → 120,626 → 106,934 → 66,396 → 22,838 →
21,352 → 1,031** samples, worst case **−324 cm → −15.3 cm**.

## 7. Engine application

APPLIED, VERIFIED AND COOKED. Launched detached via `run_oldcity_streets_engine.ps1`
(`preflight48,apply48,verify48,apply50,verify50,cook`). It waited ~17 minutes in
`waiting_for_slot` behind another agent's `dotnet(UAT)` cook before taking the slot at 02:02:15Z
with 33.1 GiB commit free — the queue discipline working as intended. Checkpoint + protected
hashes + save + reopen + numeric readback + receipt at every step.

**ENGINE HELD from 16 Sep on the coordinator's instruction** so the owner could open the Unreal
editor to sign in to Epic for MetaHuman; an editor plus a packaged game contend for memory on this
16 GB box. No editor, cook or capture was started after that point. The S2/S3 capture already in
flight was allowed to finish — `capture_city_facade.ps1` blocks on `UnrealEditor` in its own slot
check, so it defers to the owner's editor rather than competing with it.

**`-Revert` is implemented and guarded but NOT exercised, and is therefore not a proven claim.**
`-OCSRevert -OCSTarget=<Candidate48|Main50>` destroys every `RELEASE_OldCityStreetsV1_*` actor,
saves, reopens and proves none remain; the per-run map checkpoints under `ReviewCheckpoints` are the
byte-level fallback. Running it now would destroy the applies just landed and cost another engine
slot to redo, so it stays untested until there is a reason to use it.

**Candidate48 preflight — PASSED.** `native-preflight-Candidate48-20260916T020241846981Z.json`:
`preflight_ok_nothing_saved`.

- Resolved against the live map: 16 meshes, 851,868 manifest triangles, 152,568 m²,
  `offlineChecksPassed: true` — the release script re-reads the acceptance numbers itself, so this
  confirms the manifest status, the generator hash, all 16 OBJ hashes and every check pass against
  the real map rather than against my own run.
- `existingBefore: []` and `actorCountBefore: 8602` — nothing of this pass is already in the map, so
  the apply cannot double-place.
- `mapSha256Before 650c2b6c…f96de`, `mapBytesChanged: false`, `protectedUnchanged: true`,
  `errors: []` — the read-only pass wrote nothing, as designed.

**Candidate48 apply — PASSED.** `native-apply-Candidate48-20260916T020356200602Z.json`:
`applied_saved_reopened_read_back_visual_acceptance_pending`.

- 16 meshes imported (all created, all **Nanite**), `MI_OldCityLaneStone` created by duplicating
  `MI_OldCityPlaster`, parent `M_Context_Building`, every tint and scalar verified by readback.
- 16 actors placed, **8,602 → 8,618**. After SAVE and REOPEN all 16 read back with identity
  transform, the right mesh and material chain, `BlockAll`, STATIC mobility, and worst
  world-bounds error **0.0034 cm** — the OBJ Y-reflection round-trips.
- Tags **12 `CityDetailZone_Kept` + 4 `CityDetailZone_Precinct`**.
- Map checkpointed to `ReviewCheckpoints/OldCityStreetsV1-apply-Candidate48-20260916T020356200602Z`
  before mutation; `protectedUnchanged: true`; `errors: []`.

**Candidate48 verify (fresh process, read-only)** `native-verify-Candidate48-20260916T020843372671Z.json`:
`verified_read_back_nothing_saved`. 16 actors re-read from the saved map in a NEW editor, worst
bounds error 0.0034 cm, same 12/4 tag split, `mapBytesChanged: false`, protected files unchanged.

**Main50 apply — PASSED.** `native-apply-Main50-20260916T021118035559Z.json`. The same 16 assets
were **REUSED** — `material created: false`, `meshes created: 0`, so nothing was re-imported or
rebuilt — and 16 actors placed, 8,602 → 8,618, worst bounds error 0.0034 cm, checkpointed, protected
files unchanged. Tags **11 Kept + 5 Precinct**: one tile flips class between the maps, exactly as the
manifest predicts and mirroring the foundations' `Grid_N004_N004` behaviour.

**Main50 verify** `native-verify-Main50-20260916T022703665942Z.json`:
`verified_read_back_nothing_saved`, 11 Kept + 5 Precinct, map bytes unchanged by the verify.

Both maps therefore carry the same reviewed geometry with per-map visibility classes, and both were
proved by reopening the saved map in a fresh editor rather than by trusting the applying process.

**Corroborated from outside the engine.** Every statement above comes from receipts written by the
same script that did the writing, so it was checked again from a different direction — the raw saved
bytes and the content tree:

- Both `.umap` files contain exactly **16** `RELEASE_OldCityStreetsV1` references, matching the 16
  actors each receipt claims. (`MI_OldCityLaneStone` does not appear in the maps, which is correct:
  the map references the mesh assets and the meshes reference the material.)
- `JerusalemContext/OldCityStreetsV1` holds **16 meshes + `MI_OldCityLaneStone.uasset`**.
- `JerusalemContext/OldCityFoundationV2` still holds **exactly 96 meshes** — the foundations pass is
  untouched, as required.
- Both pre-mutation map checkpoints exist under `ReviewCheckpoints/OldCityStreetsV1-apply-*`.

**Cook — PASSED, playable.** `Checkpoint-Build.ps1 -Label streets01 -UseExistingBinaries`, receipt
`C:\Mikdash\Working-5.8\Checkpoint-streets01-20260916T022910Z\checkpoint-receipt.json`.

- `exitCode: 0`, `childExists: true`, `archiveBytes` **4,248,752,537** (3.96 GB on disk).
- **Smoke: `playable`** — window open in **18 s**, peak working set 3,959 MB, still alive at the end
  of the bounded window. That is startup only, not route, audio or interaction acceptance.
- `usesExistingBinaries: true` — "Existing binaries only; pending C++ changes are NOT included."
- Cooked map hashes after: candidate `c516fd26…`, main `2b82ae66…`; `mainMapChangedDuringCook: false`.
- Archive `C:\Mikdash\Builds\Checkpoint-streets01-20260916T022910Z`.

**Staged child SHA256: `de6dc228c3526d1143dd3389e0a9ccdd56f2c048b5a8dd8d3d972bc42ad22d2b`**
(340,167,168 bytes, written 2026-09-15 20:31:20), read from this pass's own receipt as instructed.
It is neither cp26's `5cc71b34…` nor the `67f3fe64…` child measured at the project path at 20:07:40:
the shared binaries were rebuilt again by another agent between that measurement and this cook,
which is exactly why the staged hash must never be assumed.

*Correction, recorded rather than quietly fixed:* an earlier draft of this section flagged the cook
as "under investigation" because the archive directory held no `checkpoint-receipt.json`. That was
my own lookup error — the receipt is written to the JOB directory, not the archive. The underlying
observation still stands as a real weakness in `run_oldcity_streets_engine.ps1`: its cook step only
asserts "a newer archive directory exists" and records `exitCode: null`, so it would not by itself
have caught a failed cook. The receipt is what proves the build, and it should be the runner's test.

**Queue position matters more than the gate file.** `SLOT-trees-done.txt` exists, but the trees pass
finished its offline work without ever taking the engine, so the engine order is Kotel, walls,
trees, then this pass. `Wait-Slot` therefore requires every slot file, no editor/game/UAT/UBT
process and ≥12 GiB commit headroom, then settles a random 15–40 s and **re-checks** before
launching — two editors at once exhaust commit on this 16 GB box.

**Cook: `-UseExistingBinaries`**, verified at `Checkpoint-Build.ps1:96` to set `$buildOption = ''`,
dropping `-build` so only the cook runs. This work is content-only and that keeps the cook clear of
another agent's in-flight C++.

**Corrected 16 Sep.** An earlier draft claimed the staged child equals cp26's `5cc71b34…`. **That is
withdrawn.** The tree has since been fixed and both targets rebuilt, which I re-checked on disk
rather than on report, because an editor-only rebuild after a class-layout change crashes every
packaged capture:

| artefact | written | size |
|---|---|---:|
| `Plugins\MikdashRuntime\Binaries\Win64\UnrealEditor-MikdashRuntime.dll` | 2026-09-15 20:06:14 | 4,734,976 |
| `Binaries\Win64\MikdashCourtyardV3.exe` | 2026-09-15 20:07:40 | 340,022,784 |

**Game exe is 86 s newer than the plugin DLL — the ordering is correct.** At that moment the project
child measured `67f3fe64…fac8de`, a different hash *and* size from cp26's (`5cc71b34…`,
339,734,528).

**It had changed again by the time the cook ran.** The archived child is
`de6dc228c3526d1143dd3389e0a9ccdd56f2c048b5a8dd8d3d972bc42ad22d2b`, 340,167,168 bytes, written
20:31:20 — a third distinct binary, because another agent rebuilt the shared tree between that
reading and the cook. The table above is therefore a snapshot, not the shipped runtime; the
authoritative value is the one in this pass's own cook receipt, recorded in the cook section above.
That is exactly why a staged hash must be read from a receipt and never carried forward.

## 8. Frames

All three frames captured in one run: `capture_city_facade.ps1 -IncludeFoundationViews
-IncludeStreetViews -Only K1,S2,S3` against `Checkpoint-streets01-20260916T022910Z`, receipt
`city-facade-frames-streets01.json`, status `frames_captured_visual_review_pending`, **3/3**.

| view | before | after | reads as |
|---|---|---|---|
| **S3** — west Old City lane, standing on the paving | *(new camera; no before exists)* | `streets01-S3-west-old-city-lane-paved.png` | **A paved Old City alley** |
| **S2** — Jewish Quarter lane at infill 949 | `oldcity01-before-S2-…png` | `streets01-S2-…png` | Lane paved, open ground beside it bare, hard seam |
| **K1** — Kotel plaza walking, facing the Jewish Quarter | `cp26-K1-…png` | `streets01-K1-…png` (18.49 ms) | No paving in view; no-regression only |
| S1 — Jewish Quarter lane at infill 1200 | `oldcity01-before-S1-…png` | *deliberately not captured* | Nearest paving 24.8 m; nothing within 20 m |

Each is examined below, worst news first.

**K1 (`streets01-K1-…png`, frame time median 18.49 ms) shows NO paving — the alley floor is still
bare earth.** The white untextured staircase that dominated cp26's K1 is gone, but that is the
Kotel-views pass's D1 fix, **not this one's**. Three candidate explanations were tested rather than
assumed:

| test | result |
|---|---|
| Is stone in the horizontal frustum? | **Yes — 2,567 vertices**, nearest 5.4 m |
| Is it also in the vertical frustum? | **Yes — 2,548 of them.** Median elevation +2.2°, inside +7° ± 29° |
| Is it hidden by the precinct state? | **No.** All contributing meshes are precinct-class, which hides only in YECHEZKEL, and the frame plainly shows the modern city, so the `V` press reached MODERN |

So the stone is in frame and in the right state. What the geometry says is that it lies on the
**terrace above and behind the near buildings** — median paving z −760.6 against an eye at −1060,
i.e. about **3 m above the camera** — so it is occluded by them, while the alley floor actually in
view carries no mapped OSM road and therefore gets no lane.

**That is a real limitation of deriving lanes from the road network, not a defect in the paving:**
the Old City's walkable space includes courtyards and gaps between buildings that OSM never maps as
roads, and this pass does not pave them. K1 therefore stands as a **no-regression** view — it proves
the paving does not intrude into the Kotel plaza keep-out — and not as evidence that the lanes are
paved. Proving the occlusion outright would need ray casting and was not spent, because S2 and S3
carry 20,483 and 31,958 in-frustum vertices respectively and are the views that answer the question.

**S3 (`streets01-S3-west-old-city-lane-paved.png`) — the lane reads.** A paved lane runs away
between building walls: large worn limestone slabs in irregular coursing, varied sizes and tonal
variation with no visible repeat, a kerb, and a **drain channel** running down the right-hand side.
The lane curves uphill into the distance still paved. This is the frame that shows the pass doing
what it was asked to do.

Honest criticism of it: the stone reads slightly clean and flat. The dishing and ruts that are in
the geometry do not carry at this camera distance, and the joints read as crisp lines rather than
weathered ones. The paving is convincing as *paving*; it is not yet convincing as *old* paving.

**S2 (`streets01-S2-jewish-quarter-lane-walking-infill949.png`) — paving on one side, bare earth on
the other, with a hard seam between them.** The lane surface and a stepped flight occupy the lower
left. The right two-thirds of the frame is bare dirt running up to the building wall, and the paving
ends against it along a **straight diagonal edge with no transition**. Compared with
`oldcity01-before-S2` the walked strip is transformed, but the open ground beside it is untouched.

**That seam is a new defect this pass introduces, and it is the one to fix next.** Before, the
ground was uniformly bare and read as unfinished terrain. Now a crisp paved edge meets raw dirt in a
straight line, which reads as an authoring boundary — the eye is drawn to it precisely because one
side is finished. The kerb and apron exist along that edge in the geometry, but at this scale they
do not resolve into a believable transition.

**S1 cannot show this pass's work, and that is a measured fact, not an omission.** Scanning all
1,201,038 emitted paving vertices for distance to each acceptance camera:

| camera | nearest paving | vertices within 20 m |
|---|---:|---:|
| **S2** — Jewish Quarter lane | **0.4 cm** | 5,388 |
| **K1** — Kotel plaza walking | **5.4 m** | 2,201 |
| S1 — Jewish Quarter lane at infill 1200 | 24.8 m | **0** |
| A1 — west gate approach | 20.7 m | **0** |

S1 and A1 stand on ground no mapped lane reaches, so their "after" frames would be identical to
their "before" frames. Capturing them as evidence of paving would be misleading. S1 is therefore
reported as unchanged, with the reason, rather than quietly dropped.

**The acceptance set is S2 + K1 + S3.** `S3-west-old-city-lane-paved`
(`-41000 29000 1822 -6 180 0`, MODERN) replaces S1: its position is the densest Tier-A paving
neighbourhood clear of S2 and K1, and its **heading was chosen by eye from offline renders rather
than guessed** — a camera aimed across a lane instead of along it shows nothing. Four candidate
headings were rendered (`preview-C1..C4`):

- **C4 — chosen.** The lane runs away between building walls with a kerb line, step risers ticking
  along the left edge and a drain channel down the right. It reads as an alley.
- C1 — rejected. Reads as a broad open plaza rather than a lane, and its wide dark bands are most
  likely the junction bare patches carried as residual 3 above.

Offline previews at S1 and S2 were also rendered and inspected before any engine time. The pre-fix
pair showed the surface driven metres under the hillside — the ribbon defect made visible — and
stand as this pass's own "before". Capture command:
`capture_city_facade.ps1 -IncludeFoundationViews -IncludeStreetViews -Only K1,S2,S3`.

## 9. Verdict

**Walking a mapped lane reads as the Old City. Walking anywhere else still reads as a game level —
and the boundary between the two now reads worse than the bare ground did before.**

That is the honest answer, and it splits three ways:

1. **On a lane, it works.** S3 is a paved Old City alley: worn limestone in irregular courses
   running wall to wall, a kerb, a drain channel, the lane climbing away between buildings. The
   slope is carried by real stepped flights — 448 of them, 7,478 steps, riser p50 14.9 cm, tread
   p50 80.3 cm — not by tilted paving. Against `oldcity01-before-S2`, the walked strip is
   transformed. The eye-level defect the brief was written about is genuinely fixed **where a lane
   exists**.
2. **Off a lane, nothing changed.** **58.7% of the walkable open space inside the walls is still
   bare earth** (214,132 m² against 150,624 m² paved). K1's alley floor and the right two-thirds of
   S2 are untouched, because lanes come from the OSM road network and OSM does not map the Old
   City's courtyards, yards and the gaps between buildings. This is the single biggest thing
   standing between this work and the owner's bar.
3. **The paved/unpaved seam is a new defect.** Before, the ground was uniformly bare and read as
   unfinished terrain. Now a crisp paved edge meets raw dirt along a straight line in S2, and the
   eye goes straight to it because one side is finished. I introduced that, and it should not be
   left standing.

Secondary, in order of how much they cost the illusion at walking height: the stone reads clean and
flat — the dishing, ruts and per-slab settle that are in the geometry do not resolve at a few metres,
so it looks like paving rather than *old* paving; the 265 junction bare patches (worst 2.25 m) are
real holes at lane crossings; and 282 CityDetailV1 souq fittings now sit 10–45 cm below the surface.

**Would I put this in front of the owner as "the Old City lanes are paved"? No — I would put S3 in
front of him and say the lanes are paved, the spaces between them are not, and here is the number.**
The right next pass is not more detail on these lanes; it is paving the **negative space** between
building footprints, constrained by the foundations and the keep-outs, using this lane network as
its spine. That would close item 2, and closing item 2 would also dissolve item 3.

## 10. Coordination and limits

- **THE BIG ONE: 58.7% of the walkable open space inside the walls is still bare earth.** Measured
  offline, not estimated: the wall-ring interior (862,632 m²) rasterised at 2 m and every cell
  classified.

  | | area | share of the ring |
  |---|---:|---:|
  | buildings | 367,300 m² | 42.6% |
  | keep-out (Mount, protected polygons, Kotel plaza) | 130,576 m² | 15.1% |
  | **paved by this pass** | **150,624 m²** | **17.5%** |
  | **bare open ground** | **214,132 m²** | **24.8%** |

  **Of walkable open space (paved + bare): paved 41.3%, bare 58.7%.** The raster's 150,624 m²
  agrees with the manifest's 152,568 m² to 1.3% (quantisation), so the two measurements corroborate
  each other.

  The cause is structural, not a bug: **lanes are derived from the OSM road network**, and OSM does
  not map the Old City's courtyards, yards, and the gaps between buildings that people actually walk
  through. Those get no centre line, so they get no paving. **This is exactly what K1 shows** — stone
  in frustum and in the right state, but the alley floor in view carries no mapped road.

  Closing it needs a different derivation for the next pass: pave the **negative space** between
  building footprints (constrained by the foundations and the keep-outs) rather than only widened
  road centre lines. The lane network built here would become the spine of that, not the whole of it.

- **CityDetailV1 souq fittings.** That pass stands its arches and stalls on the *terrain* under a
  street station. **200 arches and 82 stalls fall on a paved lane**, and the lane surface is now
  10.1 cm (min) / 30.5 cm (median) / 45.3 cm (max) above the terrain they were placed on, so they
  sit that far below the new paving. Reported for that pass's owner; **not patched here** — it is
  not this pass's asset.
- Where a lane is clipped narrower than the legacy ribbon, the ribbon can still show outside the new
  kerb. It is enclosed within the lane, not deleted.
- Every stone, kerb, apron, step, landing, ramp and channel is authored detail in the style of the
  modern Old City. Nothing is surveyed or photogrammetric, and nothing here is halachic. The owner's
  photographs gave direction only; they are never used as game textures and never committed.
- The offline proof is geometric. It says nothing about shading, texture scale, lightmaps, collision
  for a walking pawn, or frame cost — those are what the native frames and the cook test.
- Deliberately untouched: the Temple, the plaza retaining-wall materials, the Kotel closure face,
  the building foundations, the trees, the residents.
