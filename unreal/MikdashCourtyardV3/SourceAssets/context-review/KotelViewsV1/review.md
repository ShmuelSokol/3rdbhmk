# KotelViewsV1: the two cp26 frame defects at the Kotel

16 September 2026. Written by Claude. Frames read by eye from a cooked build.

**Verdict: D1 (the white staircase) is FIXED. D2 (the closure blockout) is MATERIALLY REPAIRED but
NOT finished work** - the coping profile and the terrace-end seams still read as CG at close range,
and that is written up below rather than glossed. Build: `Checkpoint-kotel01-20260916T003146Z`.

## D1 - the white stepped soffit over the alley (cp26 K1)

**Cause, identified.** `RELEASE_MountAccess_Deck`, `_Guards` and `_Portal`: the illustrative
future access stair built by `Scripts/create_kotel_opening.py` from the V1 stair in
`create_mount_access.py`. Each of its 90 walking segments is a separate 45 cm deep box from
X -18400 to X -12500 at Y 19822..20122, so from below the overlapping boxes read as a stepped
underside. `release_exterior_fixes.spec.json` placed them as `/Game/MikdashV3/ArrivalReview/MountAccessV2`.

Three findings that matter, because each rules out a different guess:

1. **It is not a missing material and not a cook fallback.** The deck carries
   `M_JerusalemStoneV2_PavingReview` and the guards `_WallReview`; the material assigns
   correctly and has `bUsedWithNanite`. The cp26 K1 game log records no material, usage or
   default-material warning, and the cooked default material would draw a grid, not flat white.
   The material is the project's own unaccepted procedural pilot
   (`create_jerusalem_stone_v2.py`, spec `visual-review/jerusalem-stone-v2-spec.json`): base
   colour 0.64/0.63/0.605 linear with +-2.25 % per-block variation and no texture and no joints,
   i.e. a near-white card. The Mount platform was moved off that pilot on 8 September; these
   actors never were.
2. **It has no state tag**, so `ConsiderStateTaggedActor` never sees it: it stands in Yechezkel,
   Modern and Overlay alike. Its only tags are `RELEASE_ExteriorFixesV1` and
   `AUTHORED_INTERPRETATION_NOT_SOURCE_FACT`.
3. **The project had already written it down.** `KotelPlazaV1/kotel-plaza-findings.json`:
   "RELEASE_MountAccess_Deck and _Guards are visible in MODERN ... A faithful present-day Old
   City should not show them". It is an authored illustration, not surveyed infrastructure, and
   no tested route uses it: the verified Kotel stair replay walks the plaza's own flight, and the
   `KotelApproachCorridor` crowd zone is fitted to the surveyed ground route, not to this deck.

**Repair.** `Scripts/release_remove_mount_access.py` destroys the three actors. Applied and then
verified in a separate fresh process on **both** maps, Candidate48 first:

| receipt | status |
|---|---|
| `mount-access-remove-apply-Candidate48-20260915T235722403448Z.json` | `applied_saved_reopened`, 3 destroyed, 8561 -> 8558 actors |
| `mount-access-remove-verify-Candidate48-*.json` | `verified_fresh_process` |
| `mount-access-remove-apply-Main50-*.json` | `applied_saved_reopened` |
| `mount-access-remove-verify-Main50-*.json` | `verified_fresh_process` |

Guards on every run: checkpoint of the .umap into `ReviewCheckpoints/MountAccessRemove-*`,
protected hashes of the other map and of the MountAccessV2 assets before and after, save, reopen,
readback that no `RELEASE_MountAccess_*` actor remains and that the actor count fell by exactly
the number destroyed, and an offline byte-exact revert
(`python Scripts/release_remove_mount_access.py --revert=<apply receipt>`). The imported
MountAccessV2 assets are retained on disk; only the placement is gone.

**Frame verdict (Modern): PASS.**
`city-facade/kotel01-K1-kotel-plaza-walking-facing-jewish-quarter.png` against
`cp26-K1-...png`: the flat-white stepped soffit that spanned the frame overhead is gone. The alley
now opens to sky over the Herodian wall, and a 1800x1000 crop of the upper left - where the stair
filled the frame in cp26, cp24 and cp21c - contains only sky, cloud and stonework.

**Overlay: PASS.** `kotel01-K1O-kotel-plaza-walking-overlay-state.png` is the same clean alley, so
the stair is gone in the state where it previously also stood.

**Yechezkel: not judgeable from this camera, and it does not need to be.**
`kotel01-K1Y-kotel-plaza-walking-yechezkel-state.png` puts the eye below the precinct surface
(vault, sand, one tree), the same condition as K2Y. It does not matter here: the three actors were
DESTROYED from both maps rather than hidden by a state tag, and both maps were read back after
reopening with zero `RELEASE_MountAccess_*` actors remaining. There is no state in which they can
return short of a revert.

## D2 - the closure reading as a rough blockout (cp26 K2)

### What was wrong, measured

KotelCutClosureV1 hung a vertical curtain on every ATOMIC exterior edge of the stepped deck-cell
union. Reading the pinned `closure-study.json` against the plan explains each symptom the review
listed:

* **the regular dark vertical stripes**: the plaza's west boundary is a sawtooth of 250 cm cell
  rows offset 10-50 cm in X, so the curtain carries a short perpendicular return face every
  250 cm, each one shadowed;
* **the hard jog between two planes**: at Y 19972..20000 the boundary steps 308 cm west
  (X -22394 to -22702) - a real plan feature the curtain expressed as a raw corner;
* **grey stone matching neither the Kotel nor the Old City**: the curtain used
  `MI_PrecinctPlaza_Ashlar`, the precinct's own paving/retaining stone.

### The replacement

`Scripts/generate_kotel_retaining_wall.py` -> `retaining-wall-v2.json` (pure offline, no Unreal):

* **one continuous face** on a one-sided simplification of the sawtooth. Every chord joins
  boundary vertices and every skipped vertex lies on the TERRAIN side of it by at most 60 cm, so
  the face always stands on deck paving and never leaves a slot over the cut. Jogs larger than
  that stay honest corners rather than being smoothed away. 248 boundary vertices become 119.
* **a real cross-section**: a footing course whose chamfer is steeper than the walker's 44.77 deg
  walkable limit (so it cannot become a perch), a 1:15 battered face, a proud capping course, a
  coping top sealed back into the hill, and a buried back face.
* **course-aligned stepped tops**: terrain at the replaced boundary plus freeboard, rounded up to
  50 cm courses above the deck, so the top steps with the hill in horizontal runs (42 runs over
  the 378.5 m chain) instead of raking.
* **Old City limestone**: material slot 0 is `M_Context_Building`, the same master the
  neighbouring Jewish Quarter infill uses - triplanar with world height in V, so courses run
  horizontal on every face. A constant 97/255 colour overlay sets the material's vertex-colour
  modulation to exactly 1.0 against its `VCMeanLum` of 0.38, so the wall reads as the same stone
  as the houses behind it rather than 15 % brighter. Confirmed present in the cp26 cooked
  container, so the runtime load resolves in a packaged build.
* **the Kotel's own frontage is untouched**: the 148 V1 triangles within 8 m of the protected
  Western Wall footprint (OSM 817206833) are copied byte-for-byte and keep the plaza ashlar on
  material slot 1.
* **the V1 curtain is retained as a liner** (693 triangles) behind the dressed face. The face
  stands inside the sawtooth, so a sightline running nearly parallel to it can otherwise slip
  through the few-centimetre wedge between chord and boundary; keeping V1 behind makes occlusion
  at least V1 by construction. `generate_kotel_closure_runtime.validate` and the unit tests now
  refuse data where the liner is missing or incomplete.

Totals: 2,899 triangles (148 ashlar + 693 liner + 2,058 dressed wall), 8,697 vertices.

### The stray paving strip

Identified as OSM way 26492734, "Western Wall Plaza" (`highway=pedestrian`), exported by the
context street pipeline as a ~145 cm road-centreline ribbon draped on the original DEM across four
`SM_Jerusalem_StonePaths_*` assets. PlazaV1 already paves that footprint as a real place, so the
ribbon is a duplicate: it lies on the hillside above the retaining face, overhangs the excavation
and pokes up through the deck, and the Z-shaped notch is the way's own vertex jog. Street actors
carry no state tag, which is why it survives every precinct state.
`Scripts/generate_kotel_plaza_way_cut.py` selects 464 triangles (976 kept) whose centroid lies
inside the plaza polygon or within 300 cm of it; `Scripts/release_kotel_plaza_way_cut.py` builds
cut DUPLICATES in a new namespace and swaps the actors, on the
`release_fix_kotel_occlusion.py` precedent.

Applied on Candidate48 (`plaza-way-cut-apply-Candidate48-20260916T002216898984Z.json`,
`applied_saved_reopened`). The four duplicates under
`/Game/MikdashV3/FutureMountV1/KotelApproach/..._PlazaWayCut` deleted 179 + 116 + 101 + 68 = 464
triangles and kept 99 + 288 + 227 + 362 = 976, matching the offline spec exactly, and the native
run refuses any disagreement with it. Originals are unchanged on disk and the map has a byte-exact
revert. Main50 was then applied the same way, and BOTH maps were confirmed in separate fresh
processes (`plaza-way-cut-verify-Candidate48-*.json` and `...-Main50-*.json`,
`verified_fresh_process`): every one of the four street actors points at its cut duplicate after
reopening. **Frame verdict: PENDING.**

All four map-side steps of this pass - the stair removal and the ribbon cut - are therefore
applied and independently verified on both maps, Candidate48 first
(`engine-run-20260916T002158Z.json`, `all_steps_passed_visual_acceptance_pending`).

### Acceptance still owed

* `Scripts/verify_kotel_retaining_wall.py` - void-ray coverage against the frozen terrain: **PASSED**
  (`coverage-v2.json`, `void_rays_passed_native_acceptance_pending`). A void ray is a sightline
  whose nearest hit among {wall, plaza deck, hillside terrain} is the BACK of the one-sided
  hillside surface outside the deck union - the player looking in under the hill, which is the
  defect the closure exists to shut. Over 43 deck-level cameras x 8,280 rays: **V1 268, V2 229**,
  i.e. 39 fewer, and 0 face-foot samples lie off the deck.
  The bar is no regression against the ACCEPTED V1 closure, not zero. The first version of this
  test demanded zero, which V1 itself cannot reach (it excludes the internal level edges and the
  platform hole by design), so that bar was meaningless and was corrected before this run. Two
  earlier framings were also wrong and are recorded here so the number is not overread: comparing
  wall-to-wall hit DISTANCE fails on grazing rays because V2 legitimately stands up to 60 cm inside
  the sawtooth, and sampling cameras at deck-cell centres put some cameras inside the wall body,
  where 80-160 cm sliver cells exist and no player can stand.
* **`Scripts/Test-KotelClosureRuntime.ps1`: PASSED** (`KotelCutClosureV1/runtime-20260916T005030419Z.json`),
  four states, four photos, all 20 maps unchanged. This is the state test the K2Y camera could not
  give, because that camera sits below the precinct surface:

  | state | closure visible | collision mode | source state |
  |---|---|---|---|
  | Modern | yes | 1 (QueryOnly) | pass |
  | **Yechezkel** | **no** | **0 (NoCollision)** | pass |
  | Overlay | yes | 1 | pass |
  | Modern-again | yes | 1 | pass |

  The runtime reads back **2,899 triangles / 8,697 vertices** - the V2 wall, not the old 841-triangle
  curtain - with deck-transform error 0 and position error 0, and material slot 0 resolving to
  `/Game/MikdashV3/JerusalemContext/ContextMaterialsV1/Materials/M_Context_Building`. The Old City
  limestone is therefore confirmed on the wall inside a packaged build, not just on disk.
* **`Scripts/Test-KotelEdgeRuntime.ps1`: PASSED**, category `blocked-retaining-edge`
  (`edge-20260916T005141467Z.json`). The wrapper read the blocking face from the generated geometry
  (`wallFaceSource: retaining-wall-v2.json probeLane.footingFrontXcm`, X -22439.850) rather than
  assuming the old cut boundary: 4 blocking capsule sweeps on the closure body at that face, 0
  penetration samples, initial floor validated, and the pawn ends grounded on `SM_PlazaV1_DeckTile`
  at feet -982.4 having never crossed. The wall blocks where it now actually stands.
* **`Scripts/Test-KotelStairRuntime.ps1`: PASSED** (`stair-20260916T005216123Z.json`),
  `passed-native-stair-route`: waypoints 0, 1 and 2 all reached (3/3) in 10.0 s, zero stuck events,
  final feet -982.6 on the upper deck, all maps unchanged. The new wall does not block the route.
* A cooked build and K1/K2 frames in all three states: **Modern read, other states PENDING.**

### K2 frame verdict (Modern): the blockout reading is gone; the wall is not yet finished

`city-facade/kotel01-K2-kotel-upper-deck-facing-jewish-quarter.png` against `cp26-K2-...png`.

Fixed, and visible in the frame:

* **the two planes with a hard jog are gone.** The face is continuous, and the one remaining step
  reads as a dressed terrace with its own capping, which is the honest-terrace option;
* **the regular dark vertical stripes are gone** - there is no longer a shadowed return face every
  250 cm, because the face no longer follows the deck sawtooth;
* **the courses run horizontal** across the whole face, with a footing course at the paving;
* **the stone matches the Old City.** The wall is the same limestone as the Jewish Quarter houses
  above it, not the grey panelled precinct ashlar;
* **the tilted, Z-notched paving strip on the sand above the wall is gone.**

Not fixed, seen in 1600x800 and 900x500 crops:

* **the capping course reads as thin flat plates, not stone.** Several coping slabs show a bright
  underside flange projecting into the air (clearest at the centre-left terrace end and along the
  top edge left of centre). A real coping needs thickness and a return; mine is a slab with a
  visible soffit;
* **hard vertical seams run down the face at the terrace ends**, consistent with the retained V1
  liner or a coping end meeting the dressed face at a joint that is not mitred;
* **the slope above the wall is still bare sand.** Removing the stray ribbon did not add the
  terracing that a real Jewish Quarter escarpment carries above a retaining wall.

So D3 is materially repaired at the distance the review complained about, and it is NOT finished
work at close range. The coping profile and the terrace-end seams need another pass; that is
recorded here rather than being called done.

### K2 in Yechezkel: the ribbon is gone there too, but this camera cannot judge the wall

`kotel01-K2Y-kotel-upper-deck-yechezkel-state.png` shows sand under a stone vault, because at this
camera Yechezkel puts the eye BELOW the precinct surface. The cp26 review recorded the same thing
as its observation 11, so it is not a regression of this pass - and it means the frame cannot show
whether the wall hides correctly. That state test belongs to the native four-state probe, not to
this view.

### K2 in Overlay: the wall stands

`kotel01-K2O-kotel-upper-deck-overlay-state.png` reads the same as Modern: the dressed face is
present with its horizontal courses, footing and capping, the stone still matches the houses above,
and there is no paving strip on the sand. So the wall is shown in both states that must show it.
The state that must HIDE it, Yechezkel, cannot be judged from this camera (see below) and is tested
by the native four-state probe instead.

What K2Y does prove: the sand here is clean. In cp26's Yechezkel probe frame
(`KotelCutClosureV1/runtime-20260915T221846377Z-phase1.png`) the tilted, Z-notched paving strip lay
across this same sand, which is how it was identified as a state-independent street ribbon rather
than part of the closure. It is absent now, so the ribbon cut holds in Yechezkel as well as Modern.

## Build and schema

The runtime data header is GENERATED. A C++ change that references new fields breaks every
agent's cook until `python Scripts/generate_kotel_closure_runtime.py` is re-run - this happened
here and stalled another agent's build, and it is recorded in AGENTS.md so it does not recur.
Both targets, `MikdashCourtyardV3Editor` and `MikdashCourtyardV3 Win64 Development`, compile
clean at the current header. No new reflected UPROPERTY was added: the new material reference is a
plain weak pointer, so the cooked map's unversioned property schema is unchanged.

`python Scripts/verify.py --build` is green: **11/11 checks**, including `plugin C++ compiles
(editor and game)` and `standalone math tests (32/32)`. The 14 Kotel unit tests
(`Tests/test_kotel_closure_runtime.py`) pass against the regenerated header, and they now also
refuse wall data whose V1 liner is missing or incomplete, so the occlusion guarantee cannot be
dropped silently. The gate's 234 receipt WARNs are pre-existing project-wide evidence files, not
failures from this pass; the gate warns rather than fails on them by design.

## The build these repairs are in

`powershell -File Checkpoint-Build.ps1 -Label kotel01`:

- **Archive:** `C:\Mikdash\Builds\Checkpoint-kotel01-20260916T003146Z`
- **Launcher:** `Windows\MikdashCourtyardV3.exe`
- **Game child SHA256:** `de6dc228c3526d1143dd3389e0a9ccdd56f2c048b5a8dd8d3d972bc42ad22d2b`
- **Receipt:** `SourceAssets/build-review/checkpoint-kotel01-20260916T003146Z.json`, `checkpoint_playable`
- **Smoke:** window opened in 18 s, peak working set 3,651 MB. Bounded startup only - not route,
  audio or interaction acceptance.

This is a full cook of both maps as they now stand, so it carries this pass's two map repairs, the
V2 retaining wall through the rebuilt runtime, and the Old City agent's 96 stone foundations placed
in the same window.

## Limits

Nothing here is a visual acceptance. The offline coverage test is sampled sightlines against the
frozen 566-triangle source terrain, the 959 deck cells and the wall only: it contains no building,
road, tree or the Western Wall stone, and it is not a whole-perimeter proof. The Old City agent
placed 96 stone foundations in both maps in the same window, which changes what K2 shows; the
frames will include that, and this pass neither fights nor claims it.
