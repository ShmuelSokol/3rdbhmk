## cp10/cp11: leaf cards are LEAF-SIZED, and the LOD schedule was 2x wrong — 2026-09-10 08:2x UTC

**SHIPPED BUILD: `C:\Mikdash\Builds\Checkpoint-cp11-20260910T080907Z`** (`checkpoint_playable`,
exit 0, 3.92 GB). cp10 is the same fix WITHOUT the palm-crown correction; prefer cp11.

**The frame verdict, first: the cards are fixed and the canopy now reads as canopy.**
`SourceAssets/visual-review/cp11g-veg-grove-*.png` (four views inside a real Kidron grove) show
an olive with a gnarled bole carrying a crown of small leaves, a fig with correctly large leaves,
and dwarf shrubs at dwarf-shrub scale. **No paddles anywhere.** At 7 m the camera is among leaves
instead of inside one. The cp10 cook is `checkpoint_playable`, exit 0,
`C:\Mikdash\Builds\Checkpoint-cp10-20260910T074110Z`, smoke playable at 18 s.

**WATCH OUT — the three standard cameras in `capture_vegetation_frames.ps1` no longer see any
vegetation.** `cp10-veg-*.png` are three frames of an empty plaza. That is NOT a regression: the
Candidate48 map changed under this pass (cp08 `9144cc15` -> cp09 `1e98e257` -> cp10 `7d1e1af6`)
when the plaza keep-out landed, and those cameras were framing exactly the on-deck trees it
removed. Any future vegetation review needs cameras in the groves, not on the deck. The four that
work are in the scratchpad copy; grove centre is about (25491, -43474, -2300) cm, which carries
olive, carob, cypress and date palm together.

### The palm needed a second pass: a crown is a SHUTTLECOCK, not a parasol

The first version of `build_palm` set `droop = -0.16 - 0.62*r**1.6` — always negative — so every
frond pointed out and DOWN. Measured offline: only **25%** of frond vertices sat above the bole
top and the crown was **275 cm** deep. cp10's grove frames caught it as a flat starburst. Now
`rank = hash**1.25; droop = 0.90 - 1.65*rank` spans +0.90 (upright inner fronds) to -0.75 (hanging
outer ones), with `length` tied to the same rank so the hanging fronds are the longest: **51%**
above the bole top, crown **463 cm** deep, mesh top 1556 cm against a 1700 cm species height.
The offline `render_billboard_texture` render of the mesh is the cheap check — it shows a
recognisable date palm, and it costs no engine.

**A leaning striped shaft with a starburst crown in these frames is NOT this palm.** Checked:
DatePalm instance tilt across all 239 is mean 2.9 deg, max 4.9 deg, and the mesh itself leans
3.6 deg. That shaft, and the long thin dark "sticks" crossing the grove frames, are also present
in the cp08 BEFORE frames — they belong to the pre-existing OSM lollipop-tree / fallen-log assets,
not to JudeanFloraV1. Do not chase them here.

### Defect 1: the cards were world-scale, not plant-scale

`create_vegetation.py` sized every leaf card from the CROWN — `cluster_radius = crown * 0.16`, a
**1.92 x 1.63 m** card for an olive — then drew ~7 leaves into it at `LEAF_FIT = 0.62` of the cell
each. A 6 cm olive leaf rendered at roughly a metre; the date-palm card was **4.02 x 1.17 m**
carrying three rotated pinnate shapes stretched across it.

**The rule now: a card is a leaf SPRAY at the size a real spray is, and the atlas cell depicts
exactly that spray.** Three tables drive it:
- `CARD_SPAN_CM` — physical span of one atlas cell. Olive 42, carob 46, terebinth 44, almond 48,
  fig 62, pomegranate 34, pine 55, cypress 30, sage 20, rockrose 18, thorny burnet 13, hyssop 12.
  **Not one global factor** — the species differ by 5x and a single scale would have fixed the
  olive and ruined the fig.
- `LEAF_AREA_INDEX` — `cards_for_crown()` turns it into a card COUNT, so density comes from the
  plant, not from a fixed 90 clusters.
- `CELL_COVERAGE` — needles and thorny twigs cover far less of a cell than a broadleaf spray.

`LEAVES_PER_CELL` (the fixed table of 7) is **gone**; the count is derived by Poisson coverage
against a MEASURED per-shape fill (`shape_fill()` samples `leaf_alpha` rather than asserting a
number). Olive 7 -> 148 leaves per cell, pine -> 373, cypress -> 420, fig -> 18. `build_leaf_masks`
rasterises each leaf over ITS OWN bounding box, which is what makes a 150-leaf spray affordable.

Two traps worth keeping:
- Cards are now SQUARE, because the atlas cell is square. Any other aspect stretches the leaves.
- **A palm is not a spray.** Its card is ONE FROND, so `build_frond_masks()` draws one frond per
  cell in cm — a sagging rachis with 86 pinnae — onto a 375 x 78 cm card (`FROND_WIDTH_RATIO`).

Higher LODs **TILE** the atlas instead of stretching it (`LOD_CARD_MULTIPLE = [1, 2, 4]`), so
leaves stay the same size IN THE WORLD at every LOD. Because `cards_for_crown` falls as 1/span^2,
each LOD needs a quarter as many cards and carries the SAME leaf area.

### Defect 2: the LOD screen sizes were exactly 2x too large

`release_vegetation.py:lod_screen_size()` returned `2 * radius / distance`. The engine computes
`ScreenSize = 2 * (0.5 * P[0][0]) * R / d`, and `P[0][0] = 1/tan(hFOV/2) = 1.0` at 90 degrees — so
**ScreenSize is R/d, half what the script assumed**. A threshold twice too large is crossed at half
the distance: LOD1 at 20 m instead of 40, LOD2 at 60 instead of 120, billboard at 150 instead of
300. That was the whole "faceted low-poly blobs at 15-30 m" complaint. Verified in the receipt:
Olive bark ladder went `[1.0, 0.36199, 0.12066]` -> `[1.0, 0.18099, 0.06033]`,
`lodScreenSizesApplied: true` on all 27 ladders.

**NOT fixed, deliberately:** `set_lod_from_static_mesh(..., bReuseExistingMaterialSlots=True)`
still collapses a ladder onto one material slot, so the billboard rung renders with the leaf
material. Flipping it to `False` appends a slot per LOD and `assign_mesh_slots` would have to name
each new slot's role from an imported slot name that `import_materials=False` never supplies. That
is a separate experiment and was not worth risking cp08's material fix on the same cook.

### Budget: triangles UP, fill DOWN — and fill is the one that matters

Per tree at LOD0: olive 1768 -> 4876 tri, carob/terebinth/pine 1768 -> 5488, almond 1768 -> 2248,
palm 256 -> 336. Asset total 30,894 -> 71,942. Estimated foliage load
**162,020 -> 453,326 triangles per frame against the 3.5 M ceiling; headroom 21.6x -> 7.7x.**

But card AREA per tree — what alpha-tested foliage actually pays for — **falls 4-6x**: carob
1504 -> 254 m2, pine 1152 -> 363, olive 846 -> 184, fig 993 -> 159, almond 476 -> 90.
`budget_report()`'s own docstring says foliage "is fill-bound long before it is triangle-bound", so
this trade spends the resource there is 7.7x of to buy back the scarce one. The old comment
"cards are kept few and large rather than many and small" is the assumption this pass reverses,
and it was wrong: few-and-large is exactly what made a 6 cm leaf render at a metre.

### Pipeline facts paid for on this run

- **Placement did NOT need redoing.** `release_vegetation.py` replays `placement-plan.json`
  transforms verbatim; nothing reads mesh bounds at placement time. The plan stayed byte-identical
  (sha `39b7c15e6ed8b6d0...`), so the 697 batches stand. The ONLY gate a regenerated mesh trips is
  `offline_check()` lines 314-330, which compares each OBJ/PNG against the sha in the manifest.
  `hashParity` and `generatorSha256` are **never read** by the release script — provenance only.
- A re-run of `-VegetationImportOnly` still trips the clash guard at line 1025, so it needs
  `-VegetationResume=<a 697/697 receipt for the same map>`.
- **A re-import puts every mesh slot back on WorldGridMaterial.** Always follow with
  `release_vegetation_materials.py -VegMatAssetsOnly`, or cp08's fix is silently undone. After the
  new ladders it reported **118 mesh slots** assigned, 0 errors, 55 textures unchanged.
- **`UnrealEditor.exe -ExecutePythonScript` exits non-zero even when the script SUCCEEDED**: the
  teardown asserts `Object is not packaged: ModeManagerInteractiveToolsContext` in `quit_editor`.
  Judge these runs by the receipt and the `LogPython:` summary line, NEVER by the exit code — a
  wrapper that trusted exit 3 skipped the material step and nearly shipped grey foliage.
- `create_vegetation.py` had a latent `dict | dict` in `write_manifest` — **3.9+ syntax, and the
  interpreter on PATH here is 3.8.1**. It ran all 14 species (11 minutes) and then died on the last
  line. Validate a long generator's TAIL before spending the wall clock on its body.
- New: **`--reuse-textures-except SPECIES`** re-exports geometry while keeping the PNGs already on
  disk (re-hashing them, so the manifest still states what is there). A geometry-only re-export
  went from 11 minutes to **25 seconds**. Any species whose geometry changed must be listed,
  because its billboard is a render OF the mesh.

## cp08: usage flag fixed for CityDetail too, and the cooked log is now CLEAN — 2026-09-10 06:3x UTC

**`checkpoint_playable`, exit 0, three frames captured, and the packaged build's own log now
reports ZERO usage-flag faults for JudeanFlora and ZERO for CityDetail** (cp05b had five outright
fallbacks plus ~22 recovered-with-a-hitch). Receipt
`vegetation-materials-visual-acceptance-cp08-20260910T063630328255Z.json`, frames
`SourceAssets/visual-review/cp08-veg-*.png`.

**One flag fixed six instances.** All six `MI_CityDetail_*` share the parent
`M_Context_Building`, which was `False`. This is the same parent-level fact as the vegetation and
is worth stating plainly: **`UMaterialInstance` has NO usage-flag property.** Do not go looking for
one on the instance; find the base `UMaterial` and set it there.

**The only usage-flag warning left is `MI_SanctuaryV2_Gold*` missing Nanite**, deliberately
untouched: different flag, the nine protected Nanite-repaired instances, and they render correctly
despite the warning — which is exactly why the warning's PRESENCE is not a valid test. The
FALLBACK is. Test by reading the cooked build's log for "Default Material will be used in game",
and then by looking at a frame.

## THE VEGETATION RENDERS. Root cause was a missing usage flag, and a frame was the only thing that could find it — 2026-09-10 06:2x UTC

**cp05b shipped every leaf card as a solid opaque quad. The cause was not the atlas, the alpha,
the clip value or the graph: `M_JudeanFlora_*` lacked `bUsedWithInstancedStaticMeshes`.** All
225,780 instances live on HISM components, and a material without that flag CANNOT be used on an
instanced static mesh, so the COOKED build silently substituted `WorldGridMaterial` — opaque,
one-sided, no opacity mask, no colour. Fixed, cooked as cp07, and **proven with three frames from
the packaged build**: `SourceAssets/visual-review/cp07-veg-*.png`, receipt
`vegetation-materials-visual-acceptance-20260910T062438179776Z.json`.

**THE FLAG LIVES ON THE PARENT `UMaterial`, NOT ON THE INSTANCE.** `UMaterialInstance` has no such
property; it resolves usage through its base. Setting it on the three `M_JudeanFlora_*` parents
alone fixed all 40 instances and all 225,780 plants — that is measured, not assumed. The same
one-line fix on `M_Context_Building` covers all six `MI_CityDetail_*` instances, which share it.

**WHY EVERY CHECK IN THIS PROJECT STAYED GREEN AND HONEST.** The EDITOR sets a missing usage flag
on the fly when it meets an instanced component and only warns that the asset needs resaving. So
parameter parity, save-and-reopen readbacks and every `-nullrhi` receipt saw a correct material —
because in the editor it WAS correct. **No editor-side check can catch this class of fault.** The
acceptance now reads the flag off the SAVED asset and refuses if it is false, but the real lesson
is that only a frame from a packaged build closes it. Caution: `MI_SanctuaryV2_Gold*` logs the same
warning and renders correctly, so the warning's PRESENCE is not the test — the fallback is.

**What the frames show.** Cut-out foliage: serrated leaf edges, pinnate carob and terebinth
leaflets, cypress needles, straw grass tufts, bark trunks, and clear per-species colour separation.
The precinct deck, city and sky in the same frames are the unchanged control.

**A second, self-inflicted defect found on the way, and the check that now prevents it.**
`MaterialEditingLibrary.delete_all_material_expressions()` DOES NOT empty the graph. The
"rebuild in place" used during the cook-crash diagnosis left `M_JudeanFlora_Leaf` holding **35
expressions where 24 had been created** — two `LeafAtlas` samplers, seven `ScalarParameter`s
instead of four, duplicate parameter names. `build_master()` now deletes and recreates the asset
and asserts that the saved material holds exactly the expressions it created with no repeated
parameter name.

**What was ruled out first, so nobody repeats it:** the source atlases DO carry a correct binary
cutout (`T_Olive_Leaf_BCA` decoded texel by texel: exactly two alpha values, 67.2 per cent fully
transparent, cut texels RGB 0,0,0); the meshes DO have UVs (2160 `vt` for 2160 `v`, card UVs
spanning atlas cell 0); and the graph was correctly wired throughout. No atlas re-authoring was
needed.

**Capture recipe, now a script:** `Scripts/capture_vegetation_frames.ps1`. One trap paid for —
photo mode writes `MikdashPhotos/` under the process WORKING DIRECTORY, not under the exe, so
`Start-Process` must be given `-WorkingDirectory`; without it the run reports "no PNG produced"
while three good frames sit in whatever folder the shell happened to be in.

**Still wrong, and now clearly visible with the right material on screen:**
- **The cards are world-scale, not plant-scale.** A carob leaflet reads as tens of centimetres and
  date-palm fronds fill the frame at 2.4 m. Mesh authoring in `create_vegetation.py`.
- **The LOD ladder collapses**: trees at 15-30 m are faceted low-poly blobs. Needs a re-LOD pass
  with `StaticMeshEditorSubsystem`, which is None in commandlets — use the hidden-editor recipe.
- The overall read is greener and lusher than the authored dry-Judean targets.
- Vegetation stands ON the paved precinct deck: no plaza keep-out. Pre-existing.
- The pre-existing OSM lollipop trees sit alongside the new flora; the two art styles do not match.

## cp05b PASSES: checkpoint_playable, leaf material intact — 2026-09-10 05:14 UTC

**`Checkpoint-Build.ps1 -Label cp05b` -> `status: checkpoint_playable`, `exitCode: 0`.**
Cook 8,708 / 8,708 with no shader error, `BUILD SUCCESSFUL`, `AutomationTool exiting with
ExitCode=0`, 3.92 GB archive at `C:\Mikdash\Builds\Checkpoint-cp05b-20260910T051017Z`, child exe
`432bcbf4558adbae...`. Both maps byte-unchanged across the build
(Candidate48 `9144cc15...`, Main50 `85bb51a1...`). **No vegetation feature was removed to get
this** - the leaf master still carries PerInstanceRandom, ObjectPositionWS, MSM_TWO_SIDED_FOLIAGE
and the subsurface output. See the entry below for why that was the right call.

**NEW AND WORTH ACTING ON: the PACKAGED BUILD starts on this box.** The smoke test launched it for
real, with a real RHI: `windowOpened=True`, `secondsToWindow=18`, `stillAliveAfterWindow=True`,
**`peakWorkingSetMB=2852`**. That is 2.8 GB against the ~19.9 GB a real-RHI EDITOR reserves on this
map - which is why editors have been impossible all night while the shipped exe is not. The
project's standing rule that "a material is not accepted until a rendered frame with an in-frame
control shows it" has therefore been out of reach for the wrong reason: it was inferred from the
editor's footprint. **A frame of the vegetation is now obtainable from the packaged build**, and
that is the cheapest outstanding path to the visual acceptance every vegetation receipt is still
missing. Not attempted here; flagged deliberately.

## cp05's cook crash was NOT the leaf material - and the test that proved it — 2026-09-10 05:1x UTC

**Checkpoint cp05 failed with `Error_UnknownCookFailure`: ShaderCompileWorker return code
-1073741819 (0xC0000005) on `M_JudeanFlora_Leaf` / `FLocalVertexFactory`, no HLSL diagnostic.
Identical signature to the cp02 plaza crash. It was not the graph, and the material was left
intact.** Diagnosis receipt
`SourceAssets/vegetation-review/vegetation-materials-cook-diagnosis-20260910T051144319249Z.json`.

**THE CONTROL, which is the part worth keeping.** `M_JudeanFlora_Leaf` was rebuilt IN PLACE with
a byte-identical 24-node graph. Rebuilding gives every expression a fresh FGuid and therefore a
fresh shader-map DDC key, so the next cook had to recompile from COLD exactly the permutations
that had crashed. Proof it was really cold: the cook logged `Missing cached shadermap ...
PCD3D_SM6` and `... PCD3D_SM5` for it with NEW key hashes `b7...`/`1c...` against cp05's
`d07f4421...`/`efda51f1...`. Result: **8,708 / 8,708 packages, `Success - 0 error(s), 0
warning(s)`, no crash.** PerInstanceRandom, ObjectPositionWS, MSM_TWO_SIDED_FOLIAGE, subsurface,
masked and two-sided all survive.

**Three things that mislead, all cheap to check before amputating a feature:**
1. **`SCW N Queued Jobs, Unknown number of processed jobs!` means the N jobs listed are the
   CONTENTS OF THE DEAD WORKER'S BATCH**, not N independent failures. "Four of five in the vertex
   stage" is that batch's composition and carries no signal about which stage was at fault. It
   does tell you which MATERIAL was in flight.
2. **`Falling back to directly compiling which will be very slow` means the engine recompiled
   those same jobs in process.** A later cook showing NO `Missing cached shadermap` line for that
   material proves every one of its jobs - including the ones printed as Failed - succeeded, since
   a shader map only reaches the DDC complete. cp05 finished all 8,708 packages and returned
   non-zero only because the 5 job errors had already been recorded.
3. **Memory is a CONSTANT here, not a variable.** Free physical memory measured DURING a cook on
   this box: 80 MiB / 529 / 1052 / 1445 in cp05, and 109 MiB in the cook that PASSED. The cook
   drives the box to the floor every run, pass or fail. Free RAM at cook START does not
   discriminate either - the night's two SCW crashes were at 9.1 and 8.2 GB free, three passes at
   5.2, 6.9 and 8.8 GB. So memory explains neither the failures nor the passes on its own.

**THE DISCRIMINATING TEST, one cook:** force a cold shader map for the suspect material (rebuild
its graph in place so the DDC key changes) and cook again. Compiles cold => valid graph, the crash
was a worker process death. Crashes cold => the graph is implicated, bisect. **Do this before
removing features:** the "obvious" fix here would have deleted per-instance colour variation from
225,780 plants to cure a fault that was never in the material.

**`EnclosureMath.h` section 6b now has a `6b-ii`** recording exactly that, because the rule as
written ("no author-written HLSL between per-instance data and the output") is a real rule that
did not apply to this material, and reading `-1073741819` as automatic proof of a graph defect is
what cost the time. The plaza rule STANDS: a Custom node fed by per-instance data is still
forbidden, and rebuilding the plaza without one did fix cp02. What is corrected is the diagnosis -
the compiler DYING is not the compiler REJECTING a graph, and only the cold-recompile test
separates them. The cp02 case has no such control, so it is not relitigated here.

**A bisect ladder now exists even though it was not needed.**
`Scripts/release_vegetation_materials.py` carries `LEAF_VARIANTS` (`full` / `noSpatial` /
`noVariation` / `noFoliage` / `minimal`) and `-VegMatRebuildLeaf -VegMatLeafVariant=<name>`, which
rebuilds the master in place - instances keep their parent and their species colours because the
graph is emptied and refilled rather than the asset replaced. About three minutes per rung.

**Still not established:** no rendered frame of this vegetation exists, and one clean cold compile
does not make an intermittent worker crash impossible.

## The vegetation is no longer grey — 2026-09-10 04:2x UTC

**225,780 instances across 27 components on BOTH maps went from `WorldGridMaterial` to authored
bark and leaf materials. 27/27 slots assigned on each map, 0 left on an engine default.**
`Scripts/release_vegetation_materials.py` + `.spec.json`, three receipts under
`SourceAssets/vegetation-review/`: `vegetation-materials-assets-20260910T042239243857Z.json`
(map-independent), `-Candidate48-20260910T042529067639Z.json`, `-Main50-20260910T042654976146Z.json`.

**The defect was measured, not assumed.** All 105 JudeanFloraV1 static meshes came back with
exactly ONE material slot whose imported name was literally `WorldGridMaterial` — the engine
default — and all 27 placed components carried an EMPTY `override_materials` array. That is the
whole of what the user has been walking through.

**What was built.** Three masters under a NEW namespace
`/Game/MikdashV3/Vegetation/JudeanFloraV1/Materials`, 40 instances (14 leaf, 13 bark, 13
billboard; DryGrass has no bark or billboard part):
- `M_JudeanFlora_Leaf` — **BLEND_MASKED, two-sided, MSM_TWO_SIDED_FOLIAGE, clip 0.5**, subsurface
  transmission wired. A card rendered opaque is a rectangle and rendered one-sided it vanishes
  from half the angles; nothing else about a foliage material matters as much.
- `M_JudeanFlora_Billboard` — masked, two-sided, DEFAULT_LIT (transmission over a picture of a
  trunk makes the far LOD glow).
- `M_JudeanFlora_Bark` — opaque, one-sided, base colour + normal.
All three read back off the SAVED assets after a reload with the right blend mode and two-sided
flag. **Flags are set before the first compile**, so no stale shader map has to be fought after.

**Colour is per species and derived, not eyeballed.** `tint = targetLinear / atlasLinear` per
channel, so the material CORRECTS `create_vegetation.py`'s atlas onto an authored target instead
of tinting an already-coloured texture twice; the round trip is exact (predicted == target on all
14). Cypress leaf lands at sRGB [48,72,54] and DryGrass at [192,174,118] — a 58..161 luma span
across the set, 14 distinct targets and 14 distinct roughnesses. Olive is grey-green [104,116,92]
with a silvery subsurface, date palm yellow-green [128,142,68], sage and hyssop grey and dusty.
Read back off the instances the placed components point at, on both maps, identical.

**Per-instance variation, stock nodes only.** BaseColour = TexRGB * Lerp(TintA, TintB,
**PerInstanceRandom**), TintA/TintB straddling the target in hue as well as value (Olive spans
[96,108,87]..[112,123,97]); the leaf graph adds a second decorrelated
`Frac(dot(ObjectPositionWS.xy, k))` brightness lerp. **No Custom node anywhere** — `Graph.node`
raises if a class name ends in `Custom`, and the offline check fails if that guard is deleted.
EnclosureMath.h 6b, which cost a day of packaging, is honoured by construction.

**Textures: 55 inspected, 27 changed, all `_BCA` atlases WRAP -> CLAMP.** Wrapping an ATLAS bleeds
the neighbouring cell across the alpha edge and puts half a leaf on the far side of a card. The
`_N` normal maps were already `TC_NORMALMAP` + sRGB false — the importer's suffix heuristic had
got them right, which is worth knowing rather than re-fixing.

**Three traps paid for here, all now guarded in code:**
1. `str(enum).split('.')[-1]` leaves the `: 0>` tail of `<TextureCompressionSettings.TC_DEFAULT: 0>`,
   so every flag comparison fails against a plain name. Cost one full assets run. `_enum_name()`.
2. **A prose annotation added beside word lists in a JSON lookup table iterates as CHARACTERS and
   matches everything.** Adding a `"measured"` note next to `"bark": [...]`/`"leaf": [...]` turned
   every slot into a role called `measured` and failed the first Candidate48 apply. The lookup now
   skips any non-list value.
3. **A protected path that does not exist is a spec error, not "nothing to protect."** The spec
   first guessed `/Game/MikdashV3/PBRArchitecture/M_PBR_Tiled`; the real path is
   `/Game/MikdashV3/Materials/PBR/M_PBR_Tiled`, so the `if ...exists()` filter silently left the
   guard watching an empty set. It now raises. (M_PBR_Tiled is untouched — `7a1aaf9db94dd186...`,
   last written 2026-09-07 — and so are the nine Nanite-repaired instances' usage flags.)

**NOT ESTABLISHED: nobody has seen a frame.** A real-RHI editor still cannot start on this box, so
the project's own rule — a material is not accepted until a rendered frame with an in-frame
control shows it — is NOT met. Every receipt is stamped
`..._visual_acceptance_pending`. Applied anyway because the alternative is engine-default grey,
which is a certainty rather than a risk. Also open, and recorded rather than fixed: because
`set_lod_from_static_mesh` collapsed every ladder onto one slot, **the billboard LOD of a leaf
ladder renders with the LEAF material and the leaf atlas**, not the impostor texture — the
standalone `SM_*_Billboard` assets do carry `MI_*_Billboard`. Splitting the far LOD onto its own
slot needs `StaticMeshEditorSubsystem` and a re-LOD pass. There is no wind (no WorldPositionOffset)
and no leaf normal map exists in the set.

**Map hashes.** Candidate48 `d4f0f5e2...` -> `9144cc15...`; Main50 `c23b1618...` -> `85bb51a1...`.
Each run watched the other map and it was byte-unchanged. `--revert=<receipt> --dry-run` verified
both checkpoints against the recorded pre-run hashes.

## Three Main50-only passes now land on the map that ships — 2026-09-10 02:4x UTC

**Gate security, surface wear and vegetation all exist on Candidate48 now.** All three hardcoded
`TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'`, none contained the Amah48Candidate
path anywhere, and Candidate48 is the configured `GameDefaultMap` and the only map cooked into the
download. Everything the user had been shown of these three existed only on the map that does not
ship. All three now take `-Main50` (THE DEFAULT, so no existing invocation is retargeted) or
`-Candidate48`, in the shape `release_reviewed_daylight.py` settled on.

**The switch was the easy half.** Candidate48 holds the same architecture under
`p_candidate = 0.96 * p_main50 + (-248, 0, 0)` while the FutureMountV1 terrain and the metric city
were never rescaled, so a correct port has to move what moved and leave alone what did not. That is
now one file, `Scripts/map_targets.py`: the two maps, the similarity, `prove_placement()` (
`release_water.py`'s method), a terrain fingerprint comparison, an offline checkpoint `--revert`,
and a self-test (`python Scripts/map_targets.py`, 20 checks including that
`0.96 * -6200 - 248 = -6200` — the Aron is the FIXED POINT of the candidate transform, which is
what the -248 is for).

**Nothing trusts the transform; every run measures it.** `Scripts/candidate_placement_proof.py`
(read-only, both maps in one session) and each release run independently: every actor resolving to
`architecture-manifest.json` is compared with its manifest AABB carried through the declared
placement, AND the placement is solved back out of those bounds by least squares.

| map | agree | measured scale | measured translation cm |
|---|---|---|---|
| Main50 | 2626 / 2633 | 1.000000686 | [-0.0004, 0.0067, -0.0054] |
| Candidate48 | 2626 / 2633 | 0.960000659 | [-248.0004, 0.0064, -0.0052] |

The same 7 actors disagree on BOTH maps (turned pedestal, hollow basin — manifest-vs-live AABB
differences that predate all of this), and their worst error is 42.5001 cm on Main50 and 40.8001 on
the candidate: 0.96 times it, exactly. Even the disagreement scales.

**What landed, and how it was shown to be geometrically right rather than merely present:**

- **Gate security, `native-gate-security-Candidate48-20260910T024340862182Z.json`.** 90/90 placed,
  saved, reopened; pose error **0.0 cm on all 90**, worst reopened bounds error 5.9e-06 cm, every
  actor NoCollision. Each gate's live first riser and threshold match their PREDICTED bounds to
  0.0000-0.0015 cm, and the assembly stands **96.00 cm out from the live riser at all three gates,
  exactly 0.96 x the authored 100 cm**. Re-verified read-only from a fresh process, 90/90, zero
  problems, map byte-unchanged (`native-gate-security-verify-Candidate48-20260910T024732210165Z.json`).
  The WHOLE assembly rides the 0.96, so the detectors and signage are 4 per cent under real size —
  deliberate (it keeps the wall plates flush with the measured vestibule wall and the racks off a
  riser that is itself 4 per cent nearer) and recorded as a limitation in every receipt.
- **Surface wear, `native-surface-detail-Candidate48-20260910T024410434756Z.json`.** 460 decals +
  the manager; **all 460 read back after the reopen at 0.0 cm location error and 0.0 cm decal-size
  error**. Origins, projection boxes and the manager all carry the similarity, so a wear patch
  covers the same fraction of the same tread ([0,-2650,625]/60x280x180 -> [-248,-2544,600]/
  57.6x268.8x172.8). The assets stage is map-INDEPENDENT and was not re-run; the 09-09 assets
  receipt's asset SHA-256s were re-checked on disk. New evidence worth keeping: 456 of the 460
  decal origins sit inside a manifest architecture AABB at 60 cm padding; the 4 that do not are the
  outer gate landings.
- **Vegetation, `release-vegetation-Candidate48-20260910T024536144980Z.json`.** 697/697 batches,
  **225,780 instances across 27 components, expected == readback on all 27, 0 errors** — the SAME
  instance total as Main50. **THE PLANTS DO NOT RIDE THE SIMILARITY, and that is the finding.**
  They stand on terrain that was never rescaled, so they are placed at IDENTICAL coordinates, and
  the licence for that is measured: all **256 ground tiles have identical world AABBs on the two
  maps, worst 0.0000 cm**. The eleven-plus-one `*_PrecinctCut`/`KotelPlazaCut` twins legitimately
  differ (up to 502 cm — the precinct square is itself 4 per cent smaller) and are excluded from
  that comparison by name rather than averaged into it. What DOES ride the transform is the
  keep-out: the enclosure ring and the 162 architecture blocker boxes are tested in BOTH frames
  (2 rings, 324 boxes), offline and live, so nothing is planted inside the Mount under either
  interpretation. 2,678 refused by the existing-tree rule. `release_vegetation.py` refuses to place
  on the candidate at all unless `SourceAssets/scale-review/ground-fingerprint-Main50.json` exists.

**A resume receipt is now per MAP.** `-VegetationResume=` refuses a receipt whose target is not this
run's, because skipping the batches the OTHER map completed would leave a hole exactly the shape of
the other map's progress and no count against the plan would ever see it.

**`--revert` works and was exercised for real, not asserted.**
`python Scripts/release_vegetation.py --revert=<receipt>` (offline, no editor open) restored
Candidate48 from `034f8343...` to the checkpoint's `902152739fb9690a...` byte for byte, after a
`--dry-run` that verified the checkpointed bytes still hash to the receipt's `mapSha256Before`. The
map was then restored forward to `034f8343...` from a copy taken first. All three scripts expose it.

**Receipts now carry `target` and are named `<pass>-<Target>-<stamp>.json`**, which is what
`verify.py check_map_parity` buckets on — that is the blind spot the 10 Sep note describes, and
these three passes were 3 of the 351 receipts it could not see. Both targets' maps are now in each
run's protected-hash set, so a Candidate48 run watches Main50 and vice versa; `protectedMapsUnchanged`
true on every run above.

**The paired evidence, on the map that did NOT change.** `-Main50 -GateSecurityVerifyOnly` re-run
after all of this (`native-gate-security-verify-Main50-20260910T024927506500Z.json`): 90/90, zero
problems, map byte-unchanged, standoff **100.00 cm** at all three gates against the candidate's
96.00. Main50 finished the night on **9f5dd4b0230d9de8adafa4b469ed3ada7d07aa57a8fa9a358a0b1d489227bd53**
— the same hash it carried before any of this — and Candidate48 on
**034f83435874be25a3cc82776704e6a95b57a53c4058152f42637beb77be4ae3**.

**Small trap, paid for here: do not put a `target` key in a reference table under SourceAssets/.**
`verify.py check_map_parity` buckets ANY json there carrying `target` as a pass that ran on that
map, so `ground-fingerprint-Main50.json` immediately produced a WARN that a "ground-fingerprint"
pass had run on the legacy map only. The field is `readFromTarget` now. Related and still open: the
per-pass parity buckets still read `native-gate-security` / `native-surface-detail` /
`release-vegetation` as ship-only, because the HISTORICAL Main50 apply receipts carry `map` and no
`target`. That is the 351-receipt blind spot the entry below describes; the new receipts all carry
`target`, and nothing back-fills old ones.

**Not established by any of this:** no visual, collision, cook or performance acceptance on either
map; the 4 unhosted decals are recorded, not fixed. (Vegetation materials WERE unassigned; they
were authored and assigned on both maps a couple of hours later — see the 04:2x entry above.)

## Backlog verification pass — 2026-09-10 02:1x UTC

**Candidate48 real-RHI PIE is not possible on this box right now — that is the headline.**
`release_resident_routes_v2.py -RoutesV2Verify -RoutesV2Target=Candidate48` requires real RHI
(it refuses NullRHI as evidence) and the editor died twice at frames 7 and 17 with
D3D12Util.cpp:815 "Out of video memory". It is NOT video memory: local VRAM budget 7238 MB with
only 4276 MB used, while system Virtual Memory read **65370.78 MB used of 65389.91 MB, 19.13 MB
free**. The Windows COMMIT limit is the wall. Measured with no editor running, baseline commit is
**45,171 MB of 65,390 MB** consumed by non-Unreal processes (`mc-fw-host` PID 4704 alone holds
11,014 MB), leaving ~20 GB; a real-RHI editor on this map reserves ~19.9 GB of process virtual
address space (18,377 MB of it D3D12 "Reserved Buffer Memory (Uncommitted)"). So it fails right at
the edge. Candidate48 .umap verified byte-identical after both crashes (a4337468...). Receipts
resident-routes-v2-verify-Candidate48-20260910T015552005900Z.json and -20260910T015917186399Z.json
were left at 'starting' because the crash skipped the finally-block; their status has been corrected
to failed_editor_crashed_out_of_commit_before_pie so they cannot be misread as a pass.
A -nullrhi commandlet is unaffected: it never takes the D3D12 reserved-buffer path.

**verify.py check_map_parity has a blind spot, and it now reads falsely green.** It buckets receipts
by `target` and counts EXISTENCE, not status, so the two crashed Candidate48 receipts above cleared
the long-standing "resident-routes-v2-verify ran on the LEGACY map only" WARN without the pass ever
having run on the shipping map. Separately it is blind to 351 receipts that record `map` but no
`target` (229 of them Main50-pinned) - which is exactly why gate security, surface detail and
vegetation have never appeared in it.

**Three release scripts are structurally Main50-only.** `release_gate_security.py`,
`release_surface_detail.py` and `release_vegetation.py` all hardcode
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough' with no target switch, and none of
them contains the Amah48Candidate path anywhere. There is no port_candidate_* helper for any of the
three. The shipping/cook map therefore has no gate security, no surface wear and no vegetation, and
cannot get them without adding a target parameter.

**Gate security: already complete, re-verified against the CURRENT map.** The verify helper WAS
re-run after its 03:05 UTC fix (receipt 030841758949Z, 90/90). Re-run now on the post-plaza,
post-terrain-cut Main50: native-gate-security-verify-20260910T020232145559Z.json,
**90/90 actors, east 30/30, north 30/30, south 30/30, zero problems**, map 4a32a648... byte-identical,
mapSaved false.

**Surface detail: complete on Main50, absent on Candidate48, numerically.**
candidate-parity-20260910T020232999990Z.json: Main50 **460 tagged wear decals, all 460 on
SurfaceDetailSoftV1 materials, 1 MikdashSurfaceDetail manager**; Candidate48 **0 and 0**. Both maps
byte-identical during the inventory. Note `verify_surface_saved.py` can no longer be re-run: it
asserts the live map still hashes to the receipt's `mapSha256AfterSave`, which moved on 2026-09-09.

**Vegetation: 697/697 batches placed, and it needed TWO real fixes.** The premise that ~60 batches
had run was wrong - 0 had, and the pass could never have worked:
1. `AActor::AddComponentByClass` is declared `meta=(ScriptNoExport, BlueprintInternalUseOnly)` in
   Actor.h:1973, so it is deliberately absent from the UE 5.8 Python bindings and
   `actor.add_component_by_class` raises AttributeError - the exact failure of receipt
   174529264332Z. `release_city_detail.py` had already hit and solved this; its
   SubobjectDataSubsystem.add_new_subobject recipe (ownership verified three ways) is now ported
   into `release_vegetation.new_hism`.
2. The resume path DUPLICATED actors. `component_for` always spawned a new actor, so a resumed run
   made a second RELEASE_Vegetation_<species>_<role>. Receipt 20260910T020616142404Z failed its own
   reopen readback - "Reopened actor count for RELEASE_Vegetation_Olive_Bark is 2" - AFTER the save.
   Main50 was restored from that run's checkpoint back to c80e2c64 and re-verified by hash.
   `component_for` now ADOPTS an existing labelled actor, checks it carries exactly one HISM with the
   right mesh, and seeds `added` from its current instance count so the post-reopen equality check
   stays exact. place()'s pre-existing clash guard already assumed those actors exist on resume; this
   is the other half of that contract.

Final result release-vegetation-20260910T020948460767Z.json: **697/697 batches, 225,780 instances
across 27 components, 0 remaining, expected == readback on all 27, zero errors**, protected maps
unchanged, 2,426 instances refused by the existing-tree clearance rule. Main50 is now
9f5dd4b0230d9de8adafa4b469ed3ada7d07aa57a8fa9a358a0b1d489227bd53. Geometric placement only: no
visual, collision, cook or performance acceptance, and materials remain unassigned.

`Scripts/run_batch.py` carried gate security + parity inventory in ONE editor session
(batch-20260910T020223433470Z.json, 2 of 2 ran, 9.6 s and 10.4 s after one map load).

Two launch traps paid for here, both mine: PowerShell `Start-Process -ArgumentList <array>` does NOT
preserve the quotes in `-ExecCmds="py <path>"`, so the engine parsed `-ExecCmds=py`, ran a bare `py`,
and an -unattended editor sat idle holding the slot forever - pass ArgumentList as ONE verbatim
string. And `-TestSavePrefix` must match `(AstraProbe|FableProbe)_[A-Za-z0-9_]+`; anything else is
refused by _save_isolation before PIE.

scripts/verify.py 7/7 green, 32/32 math. Nothing committed.

## Published handoff — 2026-09-09

Windows12 is public at ShmuelSokol/3rdbhmk release walkthrough-12-preview.
Anonymous downloads and clean extraction passed63payload/59original files.
Downloadedcopy startup smoke passed, normal exit and original saves unchanged.
Current handoff: HANDOFF-WINDOWS12-PUBLISHED-20260909.md. Heartbeat PAUSED.
User requested publication then handoff/stop; no new feature wave. Broader quality
goal remains incomplete. Final documentation verification and push only.

## Historical distribution in progress — 2026-09-09

User authorized Windows download publication then handoff/stop. Three ordinary
ZIPs prepared in C:/Mikdash/Working-5.8/Walkthrough12-Distribution; CRC/payload
hashes passed. Clean local extraction verification running; no release yet.
Archive source is Attempt4 child329a2d910a53... . After published-download verification,
write final handoff and pause recurring heartbeat; do not start new feature work.

## Safe checkpoint — 2026-09-09 11:31 UTC

Attempt4 cook/staging/strictstartup PASS. Main/Pause preparation text wraps/fits
visually at observed1920x1080; titleBegin/skip/Pause/mouseQuit exercised. Game31484
quit normally, saves unchanged, no native job remains. Child329a2d910a53... .
Handoff HANDOFF-20260909-READY-TO-PAUSE.md records exact continuation. No ZIPs/upload
started; user choosing pause vs distribution. Broader quality goal incomplete.

## Wrap build checkpoint — 2026-09-09 11:25 UTC

Full wrapping gate11/11,32/32math PASS; Editor45.94s/Game53.01s. Same two
pre-existing C4996 deprecations remain. Fresh Attempt4 cook/render next.

## Runtime checkpoint — 2026-09-09 11:18 UTC

Attempt3 cook PASS, startup strict log PASS (six Nanite warnings gone), staging
PASS. Real packaged UI: title visible, Begin/intro skip/Pause/Resume/Fdove/Freturn/
mouseQuit observed. Existing saves unchanged. Preparation label visibly overflows
Main/Pause; fixing wrap before download. Not a full route/settings/audio acceptance.
Source checkpoint432cfa37 pushed; Attempt3 childc2742de9... retained.

## Build checkpoint — 2026-09-09 11:10 UTC

Menu fix passes full11/11 gate and32/32 math. Editor52.85s/Game54.48s both
Succeeded; two existing C4996 menu deprecations retained (font/Virtual_Back).
Fresh six-material usage verified. Next fresh Attempt3 archive still required;
no packaged menu interaction acceptance yet.

## Current verification — 2026-09-09 11:03 UTC

Six old KotelSurfacePolishV2 Nanite flags repaired: apply110127656871 changed
exactly six assets; fresh110252111955 verified persisted flags in distinct process
with zero writes. All19 maps and other Content unchanged; originals checkpointed.
First105939 failure was path-key separator mismatch (Windows str vs slash plan),
no mutation. Use relative_to(...).as_posix() for manifest/hash dictionary keys.
Menu lifecycle fix now builds WidgetTree before Super::RebuildWidget selects its
Slate root; NativeConstruct is too late. Source reviewed; full Editor+Game gate
running, packaged visible controls still pending. Attempt2 archive preserved.

## Current continuation — 2026-09-09 10:59 UTC

Windows12 Attempt2 cooked successfully; staging file/hash gate passed. Startup smoke
failed on six older KotelSurfacePolishV2 Nanite usage flags (photo Cook clones clean).
Reviewed exact-six checkpointed repair running serially. UI game41088 closed normally;
scene rendered but Escape/P showed no menu, so packaged controls remain unverified.
Original recorded saves unchanged. Worker investigating front-end initialization before
next cook. Current archive retained; do not publish it as runtime-verified.

## Current verified state — 2026-09-09 10:38 UTC

Runtime identity fix now passes native103614713103: exact same269actor set as083903,
fingerprintadd1b55da3535d53, hardhide→Modern→Overlay→hardhide→RestoreAll and originally
false fixture all restored; protectedKotel collision retained, maps/saves unchanged.
BothEditor+Game compilation and32math passed (full11/11). Preparing sourcecheckpoint
then Windows12 Attempt2; firstcook failure preserved, no package success yet.

## Historical continuation — 2026-09-09 10:21 UTC

Update10:27: checkpoint423cdce1 pushed. First Windows12 game target FAILED at three
GetActorLabel calls in MikdashEnclosure.cpp (editor-only API). Both map hashes unchanged,
no packaged child exists. RuntimeBuild-12 retains log/failed receipt. Worker fixing actual
runtime building identity; do not just replace labels with arbitrary object names.
verify.py --build now checks Editor AND Game strictly serially; earlier editor-only gate
did not establish packaged compatibility. Also current FrontEnd bypasses legacy MENU_OPEN
logs; startup smoke now checks engine/defaultMap only and requires separate menu UI review.

Update10:33: corrected shared mesh-identity resolver compiles in BOTHtargets. Full gate
11/11,32/32math PASS; logs verify-ubt-MikdashCourtyardV3Editor-uf01hkdw.log and
verify-ubt-MikdashCourtyardV3-au9jdhas.log, no compilerdiagnostics. Exact269actor-set/FNV
parity plus nativecollisionrestore now running. No secondcook until it finishes.

Candidate114a6130cde60efabef34e30d0437fe6f1746d30737295d608245e55ee79ff77
is now configured as game default/editor startup/cook map (Selected48). Main50 is retained.
PhotoCook apply101331272215 and distinct fresh101546517415 pass four independent clones,
saved Nanite usage, exact authored graph/photo identity and unrelated-content preservation.
Original5 photo assets unchanged. RealRHI capture101820 reviewed by root: photo weathering
retained, no missingNanite/defaultmaterial/compile warnings; haze/simplefigures/paving still
unfinished. Capture maps/instances/originalsaves unchanged. Verifier visual review PASS;
quick gate6/6 (241Python,55specs,890receipts,123historicalWARN) and launcher CheckOnly PASS.
Skirt fresh101143434433 PASS, originalfailure095139 preserved; actualwalk100924 PASSbelow.
Preparing Windows12, not yet cooked/packaged/download verified. Last pushed4e8dbc7b.

## Historical continuation — 2026-09-09 10:12 UTC

Kotel walking100924875746 PASSES the unchanged four-checkpoint roundtrip in20.774s:
76samples, zero airborne/missing support, no errors, maps/original saves unchanged.
Scope is lower landing→deck→platform→lower landing, one initial test placement;
not the plaza approach, physical keyboard, full connectivity or ritual permission.
Candidate936f4fbb contains only local skirtV2 notch since dcea5bf8. Fresh persisted
mesh verification is running with reviewed float32 boundary readback. Photo cook
clones remain unapplied; latest source-graph fix is reviewed. Defaults/cook stillMain50.

Update10:09: for asynchronous Slate/PIE probes use -ExecCmds="py SCRIPT", as prior
successful runs do. -ExecutePythonScript auto-quits after registering the callback;
walk100654 exited before any samples and is NOT a collision result. Use one combined
-ini:Game argument with both full class sections, as prior isolated-save runs do.
Fresh100117 scale readback passes public LOD0 [1,1,1], but notch edge failed exact-double
boundary due to persisted float32 Y rounding. Diagnostic100352 proves0.000877375cm shift;
saved-source check now uses exact float32 cut representation, same area threshold.
Reviewer replay passes actual triangle and rejects0.01cm intrusion. Native walk1009 running.

Update09:55: V2 skirt apply095139 saved candidate936f4fbb and clone55860b8c, then failed
a readback at incorrect BodySetup property spelling build_scale3d. Raw BuildScale3D
is declared UPROPERTY in installed BodySetup.h299. Read-only recovery from the exact
SHA-pinned failure receipt is being reviewed; no reapply/overwrite. All protected Content
unchanged. The prior V1 orphan asset is retained, not bound to the map.

Update09:49: skirt093726 passed the strict local geometry/attribute checks but refused
before map save: only target actor7257 bounds differed (Nanite-expanded to tight source
bounds). Original Content and map dcea5bf8 remain unchanged. Investigating a target-only
bounds check; unrelated actor checks remain strict. Photo Nanite clone dry-run diagnostic
is running; no saved clones or new package yet.

Update09:35: four photo materials log missing Nanite usage in real PIE and would fall back
in packaged play. Candidate-only base-material clones with saved usage are being prepared;
original photos/materials remain protected. Skirt remains unapplied. Failed093247 topology
diagnostic shows four unchanged single triangles moved only~1e-12cm, crossing round3 ties.
Guard now permits only same-single-triangle <=1e-6cm fallback, not area-only equivalence or
subdivision; reviewer checking. GeometryScript_Primitives is the actual ScriptName in
MeshPrimitiveFunctions.h; do not infer Python class names from C++ filenames.

Update09:24: skirt attempts091838/092204 refused before duplication/save, map dcea5bf8 and
protected Content unchanged. Diagnostic092204 shows1824/1824 triangles and four lexicographic
ordering mismatches after float conversion (nearest corner error<0.001cm). Source guard now
uses one-to-one residual triangle matching at the SAME0.05cm tolerance; missing/duplicate
geometry still fails. Reviewer checking before rerun. The local trim remains unapplied.

Checkpoint4e8dbc7b is pushed. New exact-height contact probe090736345971 identifies
SM_MountPlatform_Skirt actor7257 at about7cm above the deck, deflecting the return walk.
Do not blame people or the Kotel base. A candidate-only duplicate skirt clearance is
being prepared: local top notch inside the 300cm bridge footprint, original asset retained.
Actual deck slab thickness is45cm (z[-43,2]);110cm is guard height, not deck thickness.
Installed GeometryScript TRIM_INSIDE supports clipping an open sheet; a closed Subtract
would be the wrong operation. No repair mutation or walking acceptance yet.

Performance handoff correction: current PERFORMANCE-BUDGET.md already has Sept8 CSV
thread/GPU evidence and Nanite adoption. The earlier claim that flat frame times prove
per-draw CPU limitation is superseded: render thread measured about3ms, GPU25.7→17.0ms,
cloud plus cloud shadows about6ms after Nanite. Current22–24ms Slate samples do not
replace that thread breakdown. Reprofile the current candidate before further conclusions.

Full gate9/9,32/32math and UBT passed; latest publication quick gate6/6 passes.
Build log verify-ubt-3x8p_4_e.log is clean, including corrected ServiceActor header order.
Native enclosure restoration083903 passes269actors, original-false fixture and protected
Kotel boundary collision. Maps/saves unchanged. Kotel ascent/platform access passes,
but upper-deck return deflects near x=-13585: roundtrip084132/085303 remains failed.
Forward capsule lifted5cm missed the shallow contact; actual-centre tracing identified it above.

Photo A/B084910 was visually reviewed by root and verifier and accepted for limited
weathering improvement. Four candidate V2 slots now use existing PhotoSurfaceV2 materials:
apply090038688444 saved/reopened and separate fresh090248379625 passes unrelated baseline,
protected Content and material identity. Candidate SHA
dcea5bf85498cabd519c182e3665792cbe732d358ebac94cdfcdec0032c0e7e1.
Main remains93483d25; defaults/cook remain Main50. No fresh packaged build yet.
Photo stretch/joint mismatch, haze, sparse simple figures and paving remain unfinished.

Capture084554 verifies18 native BuildCredits names. ThirdPartyFolder is protected in
Python even under its raw name: use observable public BuildCredits output, not property read.
Its two reviewed views retain visual defects. QPC p50/p95: north23.70/27.89ms,
Kotel22.31/25.50ms at1014x550,8seconds; not packaged or1080p game performance.
Next: publish verified checkpoint, diagnose return contact, then continue visual/access
fixes before candidate promotion and fresh downloadable build. Older notes below are history.

## Historical native findings — 2026-09-09 08:28 UTC

Kotel walk081519 and081953 both refused before initial placement. The actual blocker is
OldCityInfill Grid_N002_P001 actor7483; latter receipt proves hidden=true, collision=true.
Enclosure source fix now preserves original actor collision, disables it for fully hidden
selected buildings in game worlds, and restores it on return/cleanup. Protected Kotel
base mesh Grid_N002_P001 keeps its original collision because visible detail has none.
This is a runtime state fix, not geometry deletion; subsequent build/runtime results are above.
The layer diagnostic shows V2 ashlar visible; V1 and photo planes are hidden. Upper rays
hit the intended Kotel base, so the dark close-up does NOT establish an extra wall occluder.
Capture082421 failed at a Config-only property alias; raw ThirdPartyFolder also proved
protected in084353. The public BuildCredits output check supersedes both attempts.
First capture080856 timings were quantized (16/32 ms); use perf_counter plus clock metadata,
not coarse monotonic tick differences, for future frame intervals. Prior raw evidence kept.
Component GetCollisionEnabled is owner-aware (PrimitiveComponentPhysics.cpp1569). To test
component settings preservation under actor collision toggles, read raw BodyInstance
CollisionEnabled; effective collision is expected to change. See current acceptance above.

## Publication detail — 2026-09-09 08:08 UTC

Runtime checkpoint pushed 7741901c; configured-map gate pushed 2a5b00e0.
On this case-insensitive filesystem, use the exact tracked Git spelling
`Scripts/verify.py` when staging. `scripts/verify.py` resolves for file reads/copies
but did not stage the tracked uppercase-directory path. Check staged names against
the explicit manifest, not just command success, before committing.
Native four-view Candidate48 capture with viewport timings is running; no visual or
performance result is claimed until the actual images/receipt are inspected.

## Boarding runtime checkpoint — 2026-09-09 08:06 UTC

Candidate bridge runtime080239102318 completed 180.017 simulated seconds: 45 boarded,
25 alighted, 15 photographer figures, zero overruns; maps/original saves unchanged.
Receipt retains refusal/trimming counters. Static instanced apron figures only, not
skeletal resident handover or visual acceptance. The gate and launcher now validate the
actual configured default/startup/cook map agree and belong to the Main50/Selected48
allowlist. Config defaults remain Main50. Next native jobs: visual/performance captures
and Kotel stair roundtrip. No new package or candidate promotion yet.

## Runtime bird evidence — 2026-09-09 08:04 UTC

Bridge fresh075810825396 passes: candidate references, focus, source config and persisted
unrelated baseline match; protected changes/new Content files empty; map cd3348ec unchanged.
Bird runtime080014618354 passes 45.0076 simulation seconds: motion observed in 70 pigeons,
55 swifts, 9 crows and 1 kestrel. Maps/original saves unchanged. This verifies bounded
activity/counts, not visual species realism, physical perches or audio. Natural bridge
runtime is in progress. Kotel lower-landing stair roundtrip probe is prepared, not run.
Optional capture timings measure settled Slate callback intervals at the reported live
viewport size before HighResShot; they are not GPU timings or packaged performance.

## Boarding connection — 2026-09-09 07:59 UTC

Candidate bridge saved/reopened in receipt075539876162, map SHA
cd3348ec8c0cf6f40291a5f85e338207d22c7d770a7855be0dd443d88964d1a7.
Protected changes/new Content files empty. Fresh process verification is running.
References point to candidate Transit/CrowdField; authored photo focus is [-248,0,288].
Runtime boarding is still pending; these are the bridge's static figures, not an
accepted transfer of the 24 skeletal residents. Transit/bird checkpoint pushed d0daaae0.

## Integration checkpoint — 2026-09-09 07:55 UTC

Four metric bird flocks saved in Candidate48 (074420), independently reloaded in
fresh process (075232): both receipts pass with no protected changes/new Content files.
Candidate SHA b74b4c21dc7633e05644b7a81ffe66cd78f7a8d95410e7b4579b1a7df70805bc.
Main SHA 93483d25ff23e01ee1462845b958d9c2139f2cd2e7177cf5e3e3141dd4ae1432 unchanged.
Bird runtime/perch/visual/audio acceptance is pending; Temple Plaza flock is deferred.
Transit bridge helper is reviewed, not applied. Service remains startupOFF. The candidate
is still not the default/cook map, and no new Windows package is claimed.

CandidateTransit07414660simPASS:15stops/75supportsamplespass;240roadvehicles+1activetrain,
245paintinstancesmoved (NOT245vehicles). Maps/savesunchanged, nofullroute/boarding/perf
acceptance. Fourmetricbirdport nowrunning; PlazaTempleflock stilldeferred.

Transit fresh073717 verifies sourceconfig/15stops and persistedcanonicalcandidatebaseline,
protected/newContentempty, candidate89a68853 unchanged. Runtime60sim probe prepared;
reviewing hiddenPIE throttle/mouse cleanup beforeexecution. No bridge/birds yet.

Transit-only candidateport073522 saved/reopened: all15stop/config/sourceworldcoordinates
unchanged, protecteddifferencesempty/newContentFilesempty. Candidate89a68853eb364d0a02979ff0044fc1b5b434117caf923f3290f07921f30ce868.
Freshprocessverification pending; no movement/roads acceptance yet. Main93483 unchanged.

Candidate platformwalk073330 completedbothroutes46.28wallseconds, no teleport: naturalspawn
→eastgatedown/up→outerthreshold/stairs→unchangedmetricdeck.10checkpointsfloorerrors~2.15cm,
allmaps/originalsaves unchanged. Kotelaccess and physicalkeyboard/visualstairacceptance remain
separate. Nextserialjobtransit-onlyport, candidatehashstill7eda28df.

Sanctuary48 native072820 completed10checkpoints29.09wallseconds, floorerrors1.19–2.15cm;
one explicitinitialPIEplacement thencontinuouswalking, allmaps/originalsaves unchanged.
Architectural review only: currentopen/NoCollisiondoorway isnotritual access orfunctionalcurtain.
Candidate eastgate/platform continuousprobe now prepared, exactdeckpointsstaymetric;
transit-only port prepared, neither applied nor runtimeverified yet.

Sanctuarypreflight072443 safelyrefusedobsoleteIncenseAltarV2assetguard; no walk occurred.
Candidate documentedonepiece KeilimTIV1 altar/vessels163453 replaces oldBody+Poles. Probe
candidate-onlyguard now pins exactTIasset,oneBody/noPoles,framepose andside-lanebounds;
mainhistoricalguard unchanged. Fresh native walk still pending.

Candidatefrontend072223 passes correctedframe: forward2215cm,rise1613cm,pause0,exactwalker
return,18tour/76codexcontrols,24residentswalking; maps/savesunchanged. Tourroutewalking
and physicalkeyboard remain outside scope. Sanctuary48 architecturalroundtrip native pending.
Transit-only candidateport helper preparation underway, noasset/mapmutation yet.

Parityinventory072037 unchangedallmaps: Candidate lacks transit,5birdflocks,boardingbridge,
surfacemanager/460softdecals presentonmain;18tourmarkers andtour/codex actorsalreadyexist.
Do not describe candidate feature parity as complete. Frame-correctedflight rerun pending.
Sanctuary wrapper now supports explicit -SanctuaryWalkProbe to quit onpreflightrefusal.

Candidatefrontend071737: flightforward2131cm/rise1618cm/pause0 andtour18stops76entries
controls passed, then staleSelected48spawnexpect2016 failed. Actual1768 exactly matches
Aron alignment220353 receipt PlayerStart2016→1768; main/candidate/saves preserved.
Probe now asserts pivot[-6200], expected1768 andTemplecrowdX*.96-248 (metriczonesunchanged).
No map correction needed. Fresh regression pending; parityinventory native running.

Full native service070801 naturally completed1cycle290.62s, all18station arrivals pass,
0blockedlegs/endpointPawncapsulehits; pauseflags/phase/feetfreeze+resumepass. Maps/saves
unchanged. Seven centre-foot stair floor misses: rawCMC Walking+walkablesupporttrue at
every miss; capsule support is not visual foot planting. Three closeups reject placeholder
garments/idle servicepose; startupOFF retained. db6435e1 pushed. Nextcandidate promotion
work: inventory bridge/wear parity, actual player/tour/dove/connectivity, broadvisual/perf.

Grounded diagnostics and exact bird-routing fullgate9/9,32math, UBT7actions31.66s PASS
verify-ubt-0rsfzh51.log; finalPythonquick6/6. Full natural service probe with rawCMC support,
arrival/pause/resume assertions and optional stills is running; no fullroute acceptance yet.

Grounded90 runtime065856: reaches lamp4/station6, blockedlegs0, endpointcapsulehits0,
pause2.01s/feetdrift0, maps/saves unchanged. TWO visual-foot floor misses on stair ascent
(11.71cm and15.88cm); partial_findings, not acceptance. Raw CMCsupport diagnostics and
stronger arrival/pause+resume observations prepared; fullbuild running with birdroutingfix.

Grounded fresh-process065701 verified exact saved map hash and protected Content hashes,
plus local reload stability and explicit mode/stance/body guards. Cross-process semantic
snapshot is not persisted; do not overstate that check. Native90sim motor test now running;
startupOFF in saved map. Audio species routing is a separate source-only worker change.

Grounded candidate configuration065445 saved/reopened with unchanged strict snapshot checks;
prior pristine churn did not recur, cause remains unconfirmed. Protected differences empty.
Map7eda28df84b35e45a6e975d39bebc23817798cc2af2db324b0121e09a30255d2.
Motor opted in, top-tread legacyX-5269.09, startupOFF. Fresh verification pending.
Final motor incrementalbuild8/8 passed verify-ubt-zo1g471g.log; source pushed153d88e0.

Grounded configuration064151 refused BEFORE saving: pristine snapshot churn.
Map0d997 and protectedassets unchanged. Helper now records exact changed keys before
refusal; diagnose rather than weaken preservation. Dwell-facing source correction is
under incrementalbuild; no physical motor has been enabled in a saved map yet.

Grounded motor source fullgate9/9,32math, UBT7actions27.98s PASS
verify-ubt-k2l70ygm.log. NOT opted in yet: sticky stalled leg repeatedly reauthorized
then refused, inflating BlockedLegs perframe; small counter/state fix pending incrementalbuild.
Root grounded-config helper prepared (onlymode/top-treadX,startupOFF). Probe now reads
actualfeet, endpointPawn capsules, optional2sim pause and fullnaturalcompletion600sim/900wall.
No native motor or fullroute acceptance yet.

External-motion protocol fullgate9/9,32math suites, UBT6actions22.93s PASS
verify-ubt-4absy7ys.log. API compile-verified only; no native motor wiring yet.
Legacy runtime behavior unchanged. Next phase must use physical arrival, never bool
validation without actual floor/capsule/zone evidence.

Top-tread probe061945: all three authored candidate points have actual floor936.00006,
normal1 and no stationary Pawn-profile capsule hit; centreX-5306.3264. Maps/saves
unchanged. This validates standing samples only, not travel. No anchors changed.
Pure external-motion API100315 focusedchecks passed; fullgate currently running.

Published collision checkpoint6ad4e09b. Next bounded wave: worker prepares pure
external-motion sequencing API/tests (NOT runtime-wired); current DLL remains prior
admission build. Root top-tread proposal probe uses prior binary and read-only geometry
queries. Proposed centre[-5306.3264,302.5689587,936.0000586] is authored from the existing
mesh top tread; no station anchors changed. Native PID47180 owned by root; requery first.

Stair V2 fresh060918 verified; live061102 simple/complex supports agree at all71
sampled positions. Endpoint actual920 vs planned936 remains wrong. Four stationary
Pawn-profile capsule samples blocked; full grounded stair path still unresolved.
Map and original saves unchanged; keep service startupOFF. Collision-only acceptance.

Stair collision V2 apply060704 saved/reopened successfully; protected differences empty.
Candidate map0d997af5802b99fbecfe77f09d94c52b6f62bb3f2900a9b6682b8025be0773cf.
Fresh-process verification running; no real collision acceptance yet. V1 preserved.
Service station anchors and startupOFF unchanged.

Stair helper060240 safely failed before map save; map009908 and protected originals
unchanged. V1 collision clone exists and must remain preserved. snapshot_row meshes
are PACKAGE paths (_asset_path strips object suffix); normalize exact CLONE package to
SOURCE package, not object paths. Retry must use fresh V2 namespace and record compact
snapshot mismatch evidence before refusal. Do not weaken unrelated-state comparison.

Admission runtime055924 now holds exactly at[-3560,0,888] before blocked leg2,
no initial movement into rejected leg. Maps/saves unchanged. Focused tests cover
large dt; live test covers natural transition only. Stair geometry still unresolved.

Admission full gate9/9,32/32math, actual UBT6actions22.76s passed
verify-ubt-axhzasun.log. Native blocked-transition probe running against new DLL.
Stair collision helper preparation is separate and has not mutated assets.

Stair collision diagnosis055245: simple collision is NOT actual tread geometry. At
index69 simple Z925.811 normalZ.721 versus triangle Z904.000 normalZ1; target endpoint
simple936.082 versus actual triangle920.000. Planned936 stands16cm above the real
second tread. Bounding footprint plus maximum Z is not a valid service stance.
Need a preserved duplicate with tread-faithful collision and grounded stance/path repair,
not tolerance relaxation. All maps/saves unchanged; admission build is running separately.

Published checkpoint63563d9c after full9/9+32math+UBT and finalquick6/6.
New per-leg admission repair prepared after that checkpoint: 100256 focused MSVC
checks pass, native build pending. Root stair simple-versus-complex trace diagnostic
is running against the prior binary; do not attribute its findings to unbuilt admission code.

Candidate V3 live probe054619: resolved correct V3 mesh, movement observed, garment
1/1 slot applied/read back. Floor misses0, Visibility capsule hits0, native blocked legs1.
All maps/original saves unchanged. This confirms body resolution and limited movement,
not animation visual quality or full service. Startup stays OFF until grounded route repair.

Candidate saved-gold render054410 reviewed: altar detail and paroches/reliefs readable,
no clipped-white vessel glare in this view. Strong saturated gold, flat floor and vessel
geometry remain unfinished. All maps/material instances/original saves unchanged.
Candidate V3 service live90-second probe is running; route still expected to refuse.

Candidate V3 body fresh process054200 verified all configured fields and unchanged
map0099080d, no protected differences. Fresh candidate interior capture is running next.

Candidate V3 body configuration054004 saved/reopened, protected differences empty,
map0099080da4e350b387e75ad49160976582ed73f26d5d9f29500a097f9ba9e8cb.
Correct V3 mesh, idle/walk clips, Mantle slot, scale1 and yaw-90 are hard references.
Startup remains OFF; garments are explicitly stand-ins. Fresh-process verification running.

Service body V3 full gate PASS9/9,32/32math suites, UBT6actions35.47s
(verify-ubt-gqbx1ndq.log). Candidate configuration is now being applied; not runtime acceptance.

## Current continuation — 2026-09-09 05:36 UTC

Candidate service placement051407 and fresh verification051542 succeeded with startup OFF.
Runtime051751 observed movement but one native blocked leg; no full service acceptance.
Diagnostic052655 confirms the doorway-to-stone linear height interpolation leaves the floor:
index3 planned Z890.057 versus measured887.040; endpoint floor936.082 matches planned936.
Do not relax floor tolerance: grounded path interpolation and pre-movement admission both
need repair. Diagnostic changed no maps or original saves. Body V3 correction is under
full build verification, not yet configured in the map.
Candidate gold apply052235 and fresh052452 verified1113 slots; protected differences empty.
Candidate hash62c825bd16586626b3d765355c394ed190f7689cbefcb29105b7878c61984b47.
Saved candidate gold visual review remains pending.

## Current integration — 2026-09-09 04:53 UTC

Candidate intro051013435717Z also starts at0.0, finishes naturally, restores controls,
and reports zero continuous sweep/headroom hits with unchanged maps/saves. Gate images
reviewed with the same limited two-still acceptance; terrain/road transitions unfinished.
Published edc1fcf5 includes main gold and clock/service compile evidence. Candidate service
placement is now being attempted with startup off; runtime is still pending.

Main intro050722047734Z now observes playback from0.0s through natural completion,
602samples, zero continuous sweep/headroom hits, controls restored, no map/save changes.
Approach/inside gate images reviewed: opening visible and camera emerges inside.
Two stills and NoCollision traces do not certify all intermediate portal clearance.
Candidate48 same-route probe is underway. Gold saved/fresh-verified state is93483d25.

Full gate now9/9,32/32math suites; UHT+8-action UBT succeeded40.48s in
verify-ubt-7w4t65wn.log. Service adapter/version marker and cinematic timing gate
compiled. Main live intro retry with gate screenshots is next; candidate service
placement still pending. Earlier unbuilt labels below are historical.

Gold fresh process050035209417Z verifies1113 slots and unchanged map hash93483d25;
protected content differences empty. Native/orbit timing gate now has17 focused MSVC
checks; full Unreal build pending. Intro probe now requires observing the first0.5s
and never sweeps across a change of view target. Earlier late-start receipt is retained.

Gold main apply045818582514Z saved/reopened1113 slots, zero protected differences;
main SHA93483d25ff23e01ee1462845b958d9c2139f2cd2e7177cf5e3e3141dd4ae1432.
Fresh-process readback is pending. Intro startup gap is a native FTSTicker clock bug:
new callbacks consume the whole startup frame delta. Native/orbit clock correction
is in progress; do not treat the prior natural finish as complete opening playback.

Main intro retry045552785959Z naturally finished and restored movement/look controls;
all maps/saves unchanged. First probe failed on unreflected pc.get_pawn; use
GameplayStatics.get_player_pawn. One sweep hit spans the initial pawn-to-cinematic
camera cut, not a continuous route segment; probe now separates camera cuts. The first
playing sample already reports 22.92 seconds elapsed, so opening timing is under review
and full-route observation remains unproven. Do not hide that gap under a finish result.

Gold vessel A/B045055Z completed without errors, all maps/original saves unchanged.
Both 1920x1080 views reviewed: six vessel components with the existing matte gold
show more altar detail and less Shulchan white glare. Bounded improvement accepted;
map persistence is pending. Intro natural-route runtime probe now being exercised.
Candidate service helper prepared with startup disabled and legacy station anchors;
the reflected adapter version marker and four service adapter files still need UBT.
Public video download verified anonymously HTTP200 with matching SHA; release tag
scene-preview-2026-09-09, video workflow commit38078c4e.

## Movie export lessons — 2026-09-09

V5 capture accepted as a WIP preview: 960 frames at 896x504 avoid the preview downsize,
upscaled to 1280x720 H.264, 40 s, silent, 7,837,110 bytes. Eleven source frames and five
encoded samples reviewed; full decode passed. All maps/original saves unchanged.
Video SHA c44a42486e568a763dc7bb3f9cc655bbfaae94c50021fd1b55425291f4745b41.
Quick gate 6/6. This does not promote candidate48 or accept unfinished scene visuals.

User requested a shareable actual-scene video. Legacy in-editor capture produced 960
valid PNG headers but visually invalid repeated right/bottom borders. Header/count
checks are not visual acceptance. Preserve rejected exports outside Content.
Standalone capture source supports -game and -RenderOffScreen for a hidden window,
but both local standalone attempts produced no frames and were terminated; do not claim
that path verified. Use a saved sequence, isolated
AstraProbe_ saves and process-only frontend/cinematics/settings overrides. Every comma-
separated -ini override MUST repeat [Section]:Key; a bare second Key is silently ignored
by ConfigCacheIni.cpp. Disable bApplyGraphicsToEngine to prevent viewport resizing.
MovieEndFrame is exclusive (960 at 24 fps gives 40 seconds). Do not claim a video ready
until rendered shots are inspected and the encoded MP4 fully decodes.

## Publication checkpoint evidence — 2026-09-09 04:09 UTC

Main saved-scene render 040520Z inspected in both gate views: the softer wear remains
subtle and paver joints remain visible. All maps/material instances/original saves unchanged.
Candidate C applied035717263399Z and fresh-verified035912952876Z, protected differences
empty, map d3c66fea6d550233304bf5b1d5d0ab57de728150b99f47d0fc60bd09207563f3.
Candidate render040128Z: interior paroches/reliefs readable, gold vessels still too bright;
exterior camera blocked by altar, so facade-quality acceptance remains open. All19maps
unchanged during capture. Gold-vessel PIE-only material A/B is being prepared.
The four new service-adapter C++ files have focused 100240-check math coverage but are
NOT in the prior Unreal build and are excluded from the preceding publication batch until
separate build acceptance. Runtime placement on candidate is still pending. No new package.

## Verified continuation — 2026-09-09 03:58 UTC

Full gate 9/9, 31/31 standalone math suites and Unreal compile/link passed (38.69 s).
Intro now shares the 19-point eastern route between live playback and editor tooling;
runtime clearance is still pending. Surface wear was visually rejected at full strength.
Two lower-opacity PIE views reviewed: conspicuous beige overlays are suppressed at 0.12.
Nine new SurfaceDetailSoftV1 child materials preserve V2; all 460 bindings saved/reopened
and independently verified, old assets unchanged. Main hash 478d326fc715e6690272e07043dd1238912d1c53a47066fb18cb432b0027e76c.
This is global attenuation, not a repair of ignored per-entry authored opacity or opaque
mask edges. Candidate48 sky/weather saved/reopened (035500097589Z), all other maps and
protected assets unchanged, hash e3794bc08c8f84e4d81bd20fee57123cebc3b8c59e851311d12fed0d644fbd73.
Candidate map-level lighting C port is underway. No promotion or new packaged release.

## Active update — 2026-09-09 03:43 UTC

Transit bridge observed 45 boarded and 35 alighted over 180 simulated seconds, with 20
photographers. Separate static apron figures; no verified transfer of the 24 residents.
One geometry refusal and 222 trimmed requests remain recorded. Maps and original saves
unchanged. Surface V2: all 23 saved asset hashes checked, and fresh process verified all
460 decals plus manager. The asset job crashed during shutdown after saving; preserved
exit receipt distinguishes this from a clean process exit. Placement readback falsely
rejected equivalent angles differing by 360 degrees; comparisons now wrap angular deltas.
Actual six-image wear comparison was visually REJECTED: beige patches over paving/stairs.
A lower-opacity PIE comparison is underway; do not call surface visual acceptance complete.
Soundscape importer is repaired for create-once V3 import only; no native import or audition.
No new packaged release. Exact 48 cm remains approved but candidate not yet promoted.

# Mikdash native Unreal project â€” current state (2026-09-07, after the Walkthrough-06 release work)

Surface placement032730761405Z refused before save: DecalActor.get_decal is not
Python-reflected. Replaced both placement/readback accessors with
get_component_by_class(DecalComponent). V2assets/maps/protectedmaterials unchanged;
retry only decals,manager, never assets.

Transit fresh PIE032246679066Z observed180simulated seconds:45boarded/35alighted,
5groupsstarted,20photographers,0overruns/groundmisses/caprefusals;1geometryrefusal and
222request-trimmed people explicitly retained. Sampled caps passed; allmaps/originalsaves
unchanged. Separate static apron figures, not24skeletal residents or verifiedcrowd transfer;
no visual/fullroute/packagedacceptance. SurfaceV2 all23asset hashes checked after shutdown
crash; master369pixelinstructions. Separate commandlet decals,manager now running.

Surface V2 assets stage031921348536Z reports saved textures/materials, positive shader
readback and unchanged map/protectedmaterials, but Unreal then crashed at shutdown:
ModeManagerInteractiveToolsContext None not packaged (Astra-Surface-Assets log).
Do not recreate/overwrite V2. Verify saved hashes, then fresh-process placement/readback
separately. Exit evidence astra-asset-exit-20260909.json preserves this distinction.

Transit bridge saved/reopened031750944507Z, errors[], protected maps unchanged; main
ac651b57577aab3791086ee3682d91c3347b5ce1f4831ec9ad38596cca47f62a.
This is actor/reference persistence only. Bounded natural-event PIE probe prepared; no
boarding/alighting acceptance yet. Bridge owns separate staticfigures, not24skeletal
resident transfers. SurfaceDetailV2 assets-only real-RHI import now underway; stone
retuning excluded, map placement requires successful shader/asset receipt first.

Native API correction: UE5.8 Python Object has no is_a method. For loaded UClass
subclass checks use MathLibrary.class_is_child_of(actor.get_class(), cls); a passing
AST/offline check cannot establish reflected API availability. Surface/bridge repairs
under review use this and explicit Scripts import paths; no assets yet adopted.

## Active continuation â€” 2026-09-09 03:00 UTC
Pushed checkpoint dcebc3d4 completes enclosure persistence, reviewed lighting C and 24/24
V3 resident movement on both maps; it is not a stopping point or a new package. User again
explicitly asked for continuous authorized work. Sky/time-of-day integration is now active:
helper guards run before map load, process inventory parses checked CSV, references are
cached as labels before reload, revert checkpoints first, and failure status uses actual
map bytes. Quick gate 6/6 and focused review pass; first native placement refused before saving: Python MikdashWeather resolves to the
actor, shadowing the enum. Resolve the enum from the reflected start_weather property
type instead. Receipt preserves unchanged map/protected assets. Retry saved/reopened successfully: native-place-20260909T030218302603Z, zero errors,
protected maps/assets and existing saved lighting unchanged. Main SHA
4deefbcf1279c9b6bcd93f0b2507d9a5c93940bc6214da647da9094af1cf0922.
Fresh PIE capture030529Z reviewed: one clock/one clear-weather actor, settings retained,
map/materials/saves unchanged. Dark gate backlighting and bright vessels remain.
Gate receipt030841758949Z verifies90/90 anchors/meshes/poses/signs/disabledcollision with
no map write. No package or dusk/night acceptance. Earlier pending statements below are chronological and superseded by newer receipts.


## Astra resumed after Claude limit (2026-09-09 UTC)

Latest native results: enclosure diagnostic native-enclosure-runtime-Main50-20260909T013502474817Z
completed with zero errors and unchanged maps/saves; all five assets persist and limestone
instancing usage is true. Six baseline/C images from lighting-v3-capture-20260909T013656Z
were inspected: gate visible, facade stone/partition detail improved, bright highlights and
terrain/access/detail limitations remain. C saved/reopened014035693311Z and fresh-verified
014209573438Z including the new gold instance hash, parameters and explicit Nanite usage.
When copying a material instance's visual parameters onto a new child, copy its usage
overrides too; a shared parent does not carry an instance's repaired Nanite bits.

Bodies candidate012656713742Z and013228827902Z: all24 correct V3 variants, scales, capsules,
feet/head/garments and static routes;23 moved. Miryam's whole-leg admission was blocked by
old RELEASE_Resident_authored-outer-visitor-01/-02, proved by live dynamic sweeps. The five
pilot actors remain saved but are now hidden/collision-disabled and their old spawner
startup is false on both maps (retire-pilot receipts014311446956Z/014418427990Z). No actors
were deleted. Post-retirement candidate receipt resident-bodies-v3-verify-Candidate48-20260909T014551106415Z
passes all24 spawned/variant/mesh/scale/capsule/feet/head/garment/static-route/movement checks,
with both maps and original saves unchanged. Main final receipt resident-bodies-v3-verify-Main50-20260909T014759299455Z also passes
all24 on the same checks, zero errors, unchanged maps and original saves.


Verification concurrency correction: a user opened the GUI midway through standalone math
tests. The coordinator stopped its own verifier before UBT and preserved the GUI; user
authorized normal closure, and the GUI then exited. verify.py now repeats the editor
inventory immediately before UBT, not just before the multi-minute math phase.


Published checkpoint 9f3b5404 supersedes the historical status below: V15 on both maps,
1490 limestone overrides, nine V3 variants imported, transit/birds/security/service placed.
No fresh package accepted. Six interrupted source/script files were preserved under
ReviewCheckpoints/AstraResume-20260909T010506Z before continuation.
Enclosure imports had save=False: five mesh packages are absent on disk despite same-process
instance readback. Main repair saved/reopened all five packages and actor references, receipt
native-enclosure-Main50-20260909T010837451823Z: zero errors, protected maps unchanged.
Main SHA12f8fe58403c023a8ec0412ce299f328448f758adbecc368072f719f028e2454.
Fresh-process runtime verification and candidate binding remain pending. Never treat same-process readback as persistence.
Resident V3 helper compared marker package paths with native object paths; normalize marker
paths to explicit object paths before skeleton/readback/cast checks. Its old 0-movement
receipt did not resume the initially paused front end. Updated probes explicitly resume/skip
intro and body sampling uses simulated seconds with a separate wall-clock watchdog. These
are verification repairs, not evidence yet that all 24 new bodies walk.
Main body bindings saved/reopened native receipt resident-bodies-v3-apply-Main50-20260909T011239800399Z.
Candidate missing Chananel is a route refusal, not a physical blocker: the approved Aron
re-pivot changed the frame to (-6200,0,0), while the locked 25 cm route extension allowed
only zero origin. The adapter now accepts those two reviewed pivots only and retains its
source-signature, length, region/corridor and no-double-extension guards; new regression
checks cover the exact -248 cm translation. Fresh compilation and native acceptance pending.
Fresh enclosure PIE loaded all five assets and produced 467 wall, 5 gate, 4 corner and
476 foundation instances. Its trace helper then failed on UE5.8's HitResult return shape;
that receipt remains a failure, not full acceptance. Material InstancedStaticMeshes usage
was missing on MI_PBR_LimestoneAshlar. Targeted override saved/compiled in real editor
(material-instancing-20260909T011612069494Z, 389 pixel instructions, protected maps/PBR
assets unchanged). Commandlet without a render resource returned 0 instructions and was
correctly refused without saving. Fresh visual/usage verification remains required.


Latest candidate group/render test180131188281 passes sampled51parties/201grouped+35individuals,4refused,19paused,98movingmembers,minsamplegap80.03cm. Two Temple crowd zones .96/four metric zones unchanged.15/24skeletal residents stillspawn; candidate remainsunpromoted. Real scene log has zero missing/auto-set Nanite usage messages after nine-instance repair. Root inspected180225: bright clipped surfaces, amber candidate lighting and simple figures remain. This is partial runtime acceptance, not final visuals/navigation/package.

Latest material repair: nine exact PBR material instances now persist explicit Nanite usage overrides, saved/compiled receipt173857999122 and verified from different PID175937249147; maps/config/shared parent/other PBR asset hashes unchanged. UE5.8 material instances have independent usage overrides: use MaterialEditingLibrary.set_material_usage_override(instance,MATUSAGE_NANITE,True,True), update_material_instance, get_statistics, save, then fresh-process readback. Do not widen their shared parent or assume a base-material-only repair handles instances. Shared sampler counts do not equal texture counts. New helper release_nanite_instance_usage.py; historical base helper preserved. Render/cook acceptance is separate.

Latest17:33 UTC group first pass: full8/8gate,30mathsuites,actualUBT54.92sec. Native main receipt173130367390 has54stableparties/200grouped+36individuals;4unsafeclusterplacements refused,13partiespaused at10sec.92groupmembers moved>50cm,minimumsampledgap80.04cm,123maxsweeps/budget500. Original saves/maps unchanged; image173221 inspected, simple bodies/overbright surfaces remain. Grouping is on the instanced background field, not the separate24skeletal personalities. Exact allocation accounting explicitly labels partial_safe_refusal; no240-population/long-navigation/60fps/final-visual/package acceptance. Source/readback notes GROUP-NATIVE-20260908.md. UE Python optional-success bool may be consumed, yielding tuple4 or None; don't assume tuple5. Main Nanite instance usage warnings are under targeted investigation.

Latest17:13 UTC: main8e78923f5ffb76c044693f6c74faaedb64648698945bb0ba927f3395be7f21c5 adopts cooler6500K sun and skylight1.3, with sun30000lux/rotation/exposure settings unchanged. All three actual PIE A/B pairs inspected (165802894653,170147884224,170356069458); saved/reopened native-reviewed-daylight-20260908T171157734314Z, protectedtrue. Limited limestone color improvement; Heikhal clipped highlights/Kotel deep shadows remain. Candidate48 now has descriptor+PlayerStart+18tourmarkers+58paving overrides saved/reopened; candidateSHA8dc55f79b3dbcfe0ba7a15c41b3fb2da5be108766aab5a2cf7a9aae46f8a8f89, still baseline lighting and unpromoted. Main same-layout save/load deliberately displaced50cm and restored0cm error in two native probes; cross-layout behavior remains untested.

User crowd direction (2026-09-08): people generally walk in groups, with occasional individuals. Implement stable small visitor parties with shared destinations, matched pace and waiting/regrouping, retaining individual roles. Initial2â€“6 party size/~15%individuals is authored tuning, not a sourced census. Group behavior is in development, not yet built/native-accepted. Existing instanced field was independent seeding with boundary teleports; don't describe it as group-aware until the new runtime passes. Skeletal resident personalities remain a separate system.

Current main (2026-09-08 courtyard paving):480ea53fd3864b7adcaa14a3cc96419768710b8e33bed0dacd90a3731329f1b0. Adds57 exact courtyard/gateway floor component overrides using JerusalemFloorSlabsV1 (same500cm V2 texture on tops, plain limestone edges). Source/geometry/collision/gold floors protected unchanged; saved/reopened receipt native-floor-slabs-20260908T164354150280Z. Actual PIE164034569694 matched all57, shaders ready341pixelinstructions,0errors; root inspected164130/164151. Albedo-only joints, mirror repetition, amber light, side closeup and crowd floating/appearance remain limitations. ExecCmds runpy wrappers must add Scripts to sys.path for sibling helpers; failed setup receipt retained.

Candidate fittings latest: eight TI parts and eleven Aron/menorah parts saved/reopened163453/163553 with protected inputs unchanged. Tour correctly refused absent Selected48 descriptor. New release_amah48_frame.py prepares descriptor+physical-offset-preserving PlayerStart migration, not yet natively run. Do not replay already-applied fitting stages. Candidate has not received the new main paving overrides and is not ready for promotion.

Current main (2026-09-08 Jerusalem paving): dc575d8e731ce1d10de79b4313eaeca3518460fabc022a8d11fb4f17ad3f6c31. Exact platform override now uses JerusalemPavingV2 after actual walking-height A/B162509371982 and checkpointed saved/reopened adoption162815394171, protected unchanged. Pale worn limestone flags are authored from the user's reference. Lighting still amber; other courtyard floors not yet assigned. Native V1 checkerboard trial rejected/preserved. New material assets must be shader-ready in real RHI before visual acceptance; GetStatistics in installed MaterialEditingLibrary finishes only that material's shader compilation. NullRHI import/readback alone does not establish render readiness. Comparison now binds exact material/texture hashes and rejects mixed flags.

48cm candidate fittings progress (2026-09-08):218 panels and12 door parts saved/reopened161252/161350; main/default unchanged by that work. Vessel preflight stopped because optimized Nanite native bounds differ from original import bounds. Helper now matches frozen post-Nanite inventory strictly and separately checks canonical source dimensions; rerun from vessels only, not already applied panels/doors. Save/tour compiled; population adapters source-frozen with144 standalone checks, awaiting full gate and candidate native tests. Three48cm resident loops become59.52m and remain explicitly refused under60m rule.

User paving correction (2026-09-08): floors should resemble contemporary Old City Jewish Quarter pale weathered Jerusalem limestone flags. The brown regular MI_PBR_PavingSlabs is an intermediate trial, not the requested final character. JerusalemPavingV1 is an authored image study based on the user's foreground paving reference; original family photograph stays private. Native import and walking-height review must precede assignment.

Paroches update (2026-09-08): the separate design task relayed explicit user approval of V15 third-temple-handwoven-v15.png. That candidate alone may proceed through fresh-namespace/checkpoint/verification; earlier V1/V7/V9 remain held. Approved art is authored, not a source-certified reconstruction. No V15 integration yet.

Latest active map (2026-09-08 paving adoption): ad80fd54f31eea15a05618d5bc64fcb44b0c37c5e10a13059bdb8481429a2a0e. Only the Mount platform component changed from procedural PavingReview to existing CC0 MI_PBR_PavingSlabs after actual PIE A/B review. Native receipt native-mount-paving-20260908T154639922112Z.json: saved/reopened, protected maps/source geometry/material assets unchanged. Warm palette and daylight/exposure remain under review. Paroches hold is unchanged; historical pre-art restoration84199384 below predates this paving-only edit.

Paroches approval hold (2026-09-08): the user explicitly instructed the separate art task to stop sending candidates until approved and asked this task to continue other work. Do not import, adopt or publish the unapproved V1/V7/V8/V9 artwork. V7 had saved before this notice; exact pre-art main SHA841993842baeea0958a3a969165c1a002b2726c0ae407fd14f855b5fe0d1ee58 was restored from its verified checkpoint. V9 was stopped before native assets or map mutation. The unapproved V7 map/assets and source candidates are preserved locally. Receipts are under SourceAssets/sanctuary-detail; all revised source receipts require explicit user approval. This hold supersedes earlier native-review eligibility. Material expression Python setters must use reflected editor properties (TransformSourceType/TransformType), not direct attributes. Whole-panel object-local mapping is needed because the cloth mesh has per-strip UVs; exact final 48 cm cloth fit remains unverified.

Latest takeover integration (2026-09-08): tour/codex now placed with18 markers, saved/reopened,18 stops and76 entries reloaded from Content/Distribution/Tour. DefaultGame.ini overrides their old development-only SourceAssets paths; the existing Distribution NonUFS rule stages these reviewed JSON copies. release_tour.py refuses missing/stale staged content and any omitted actor group before saving. Receipt native-tour-20260908T142311093415Z.json; main SHA841993842baeea0958a3a969165c1a002b2726c0ae407fd14f855b5fe0d1ee58. Live controls/package verification separate. Placement remains legacy50 pending coordinated48cm migration. Bounded frontend probes must use unique command-line Game ini save-slot prefixes for both save and settings subsystems before PIE and verify original save-file hashes after teardown; normal quit/tour autosaves otherwise risk changing visitor progress.

Short current-state file. Chronological evidence lives in AGENTS-HISTORY.md (old entries are superseded by newer
receipts). HANDOFF-FOR-CLAUDE-CODE.md is Codex's pre-release handoff; RELEASE-NOTE-Walkthrough-06.md lists what shipped,
with receipt names. This file describes the last known state; recheck files and receipts before acting.

## Locations and publishing rules

- ACTIVE EDITABLE PROJECT: `C:\Mikdash\Working-5.8\MikdashCourtyardV3` (open `MikdashCourtyardV3.uproject`).
- Engine: `C:\Program Files\Epic Games\UE_5.8` (verified 5.8.2). Toolchain: MSVC 14.44, Windows SDK 26100, NetFxSDK 4.8.
- IMMUTABLE ORIGINAL: `C:\Mikdash\Mikdash-Windows-Transfer\EditorProject\MikdashCourtyardV3`. Never overwrite or regenerate.
- Publishing clone: `C:\Mikdash\GitHub\3rdbhmk` -> public remote `ShmuelSokol/3rdbhmk`. Project lives at
  `unreal\MikdashCourtyardV3`; research dossiers at `unreal\Research`. Preserve the root `web/` and `distribution/`.
- Publish by copying reviewed files explicitly into the clone at matching paths, verify, stage BY NAME, commit, push,
  report the hash. Never `git add .`/`-A`, never force-push, never skip hooks.
- Never publish: Binaries, Intermediate, Saved, DerivedDataCache, `__pycache__`, logs, node_modules, checkpoints kept
  outside the project (`C:\Mikdash\Working-5.8\ReviewCheckpoints`), vendored tool folders (`SourceAssets/FutureMountV1/.tools`),
  third-party reference exports (`SourceAssets/characters-review/PilgrimRigV2/MannequinReference.fbx`), or the local
  book export `mikdash book/` (605 MB PDF + 86 MB JSON; gitignored).
- Builds: `C:\Mikdash\Builds\Walkthrough-01..05` are old (05 reused 04's cook). `Walkthrough-06-rc1` is the release candidate
  (7929 packages, 0 errors, receipts in `C:\Mikdash\Working-5.8\RuntimeBuild-06\rc1`). The final fresh package is `Walkthrough-06`.
- `Config/DefaultEngine.ini`: AndroidFileServer is disabled and its `SecurityToken` is blank. The old token was public from
  commit `f52c5ff` until the release; never reinstate it. Grep specific keys rather than printing the whole file.

## Accepted map (now the default, startup and cook map)

- `/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough` (`Content\MikdashV3\IntegratedReviewV2\Maps\Walkthrough.umap`) is
  `GameDefaultMap`, `EditorStartupMap` and the only `MapsToCook` entry; `Launch-Courtyard.ps1` verifies it.
  Last saved SHA-256 `683650c441ef1f51d839d9b0b04b8df64fd4cf908188c37b9e731b6f9e402d7d` (after the keilim move).
- Protected maps, unchanged: `/Game/MikdashV3/Maps/Courtyard` (`d0417e29...`), `FutureMountV1/L_FutureMount`,
  `MaterialReview/SanctuaryFinishesV1/Maps/CourtyardGold`. Do not edit them; use them only as donors.
- Integration helper `Scripts\integrate_review_scene.py` (V2 valid; V1 stopped on a quadratic verifier). Placement helper
  `Scripts\release_place_assets.py` + `release_place_assets.spec.json` (guarded, checkpointing, receipt-writing).

## Integrated in the combined map (saved and reopened; visual acceptance still recorded as PENDING)

Future Mount platform; four cut terrain tiles rewound front-face-up on 2026-09-07 (429/566/480/454 tris, vertex colours kept);
Mount trees removed with outside vegetation preserved; two audited Al-Aqsa actors removed only in this future scenario;
Western Wall and plaza unchanged plus six `RELEASE_Kotel_1..6` overlay meshes at identity (NoCollision); sanctuary gold
finishes (7 veneers); heikhal keilim at the book positions and sizes: CC BY Titus-style menorah `RELEASE_Menorah`
`[-5330,315,925]` 150 cm, branches north-south; shulchan study `[-5300,-350,925]` (76 cm, book says 3 amot: open);
incense altar study `[-4650,0,925]` scaled to the 5-tefach amah; CC BY-SA "Ark Box" `RELEASE_Aron_Body/Lid` at
`[-6200,0,925]` yaw 0 (length north-south per Rambam 3:12; this model's poles therefore also north-south, open);
Kodesh doors (open inward) and 7 x 6 amot paroches (`Release/Doors`, 15 actors); 196 `RELEASE_Frieze_*` 250 cm Nanite
displaced gold relief panels on all Heikhal/Kodesh walls from `visual-reference-handoff/gold-palm-cherub-relief.png`
(palm-only panels removed); `RELEASE_KodeshInteriorLight`; bus `RELEASE_Bus_1..13` at `[-37951,46855,973]` on real
asphalt at the west end of Batei Mahase road; five idle PilgrimRigV2 figures `RELEASE_Pilgrims_1..5` in the outer court around
`[5000,1180]` on floor Z 300; volumetric clouds; bound wind sequence; +1 stop exposure and interior histogram fields;
compiled MikdashRuntime controller (menu, pause/release, WASD, mouse look, mute persistence, footsteps, P-key fix in the
preparation lesson); 55 cm step height on BP_MikdashWalker. Actor count 7322 (7310 before the release edits).

## Imported but NOT placed

- TransitV2 station (12 meshes): placement unset; no source-proven railway. Bus aisle too narrow for the capsule (no boarding).
- Heikhal folding door leaves (24 planned actors) deliberately not placed: the measured architecture already carries the
  four open gold door slabs. Reuse `Scripts\release_import_doors.py -DoorsPlaceOnly -DoorsGroups=heichal` only after review.
- Fetched CC models not used: GPL menorah/Aron (license decision pending), CC0 shulchan blockout (no loaves).

## Source-only (authored, native import/placement NOT run)

- Reliefs follow-ups: paroches pattern (book p. 238 shows palm + keruvim on the curtain), doorposts and lintels, seamless
  retile of the frieze image (joint every 250 cm), a sculpted keruv panel as the upgrade path (scratchpad keruv-relief-feasibility.md).
- Mount access / Kotel opening: `create_mount_access.py`, `create_kotel_opening.py`, `mount-access\OpeningV2`.
  No source-proven western gate through the sanctuary wall; do not cut protected geometry.
- Resident crowd: `ResidentCrowdRuntime.h` (520/520 checks, debug and release) and the `MikdashResidentCharacter` adapter now
  COMPILE in Editor and Game Development targets, but nothing is bound to a live character. Not an embodied population.
- Audio: CC0 wind candidate not auditioned; synthesized pilot ambience stays autoActivate=false; footsteps live.
  `MikdashSurfaceAudioRouting.h` standalone-tested, not wired.
- Incense: `SourceAssets\IncenseRepairV4` offline only; V1-V3 studies fail visually (wisps at floor level).
- Keilim still open: shulchan height 3 amot with rods, trays and 12 loaves (book pp. 241, 250); incense altar detail; Aron
  poles east-west (Yoma 54a) as separate meshes; luchot. Reference photos with the owners' permission:
  `SourceAssets\reference-ti\dossier.md` (gitignored). Book requirements table with 15 ranked gaps (Mount enclosure largest):
  `SourceAssets\research\book-scene-requirements-20260907.md`. Source review: `SourceAssets\vessels-review\book-keilim-review-20260907.md`.
- Kotel overlay hidden behind OSM slab `SM_Jerusalem_CityWalls_04_Grid_N002_P00x` 1 m west of the face (scratchpad kotel-visibility.md).
- Controls: P-key fix compiled, not keyboard-tested. `SourceAssets\runtime-review\control-audit`.

## Hard rules

1. Never rerun the one-shot bootstrap/architecture import; never regenerate or overwrite the immutable original.
2. Stage explicit named files only. No `git add .`/`-A`, no force-push, no `--no-verify`.
3. No `-skipcook` for a release package. Fresh cook with the editor closed, then launch and test the exe.
4. Never overwrite existing native asset namespaces (rerunning creators into an existing folder is prohibited).
5. Run native jobs SERIAL. Never kill the user's GUI editor; check live PIDs before build/close operations.
6. PIE/walk tests must be bounded and auto-stop. Preserve failure receipts; do not delete or revert shared work.
7. Do not claim completion from a compile, a count, an import or a mocked test. Visible/runtime acceptance only.
8. Keep measured Yechezkel architecture distinct from interpreted/authored future details. No invented halacha,
   census, railway or Temple Institute copies presented as fact. Immersion stays modest.
9. Keep `Content/Distribution/CREDITS.txt` accurate (OSM/ODbL, Mapzen/SRTM, Fantozzi/qubodup CC0, Thimras CC0 if adopted).
10. Every map or asset edit goes through a checkpoint copy under `ReviewCheckpoints` and a JSON receipt with before/after
    SHA-256 of the map and of every protected file.

## Native pitfalls

- Commandlet: `UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<py> -unattended -nullrhi -abslog=<log>`;
  GeometryScript needs `-EnablePlugins=GeometryScripting`. `StaticMeshEditorSubsystem` is None under `-run=pythonscript`
  but available in a hidden `UnrealEditor.exe -ExecutePythonScript -nullrhi` process; that process may quit before tick
  callbacks finish, so asynchronous PIE needs the persistent editor mechanism (`-ExecCmds="py <runner>"`, real RHI).
- TRACES RETURN NOTHING in commandlets and in NullRHI editor worlds (all 128 route probes and every placement self-test
  were NO_HIT). Only PIE (or a real-RHI editor world after the loading barrier) gives hits. Ground placements from
  component bounds when traces are unavailable and say so in the receipt (`groundSource`).
- `HitResult` fields: `break_hit_result` exists only in some launch modes (missing on `GameplayStatics` in the capture
  editor); `hit.impact_point` attribute access fails there too. In `-ExecCmds` launches use `hit.to_dict()`. Branch on
  what is present rather than assuming one API.
- Generated meshes need a winding check. UE is left-handed and front faces are clockwise when viewed from the front;
  the FutureMount cut tiles rendered black because every triangle faced down while vertex normals pointed up. Check
  `facesUp == triangles` with GeometryScript face normals (`cross(C-A, B-A)`) before saving a generated mesh.
- The archive-root `Windows\MikdashCourtyardV3.exe` is a bootstrap that exits at once; track the child process at
  `Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe` for windows, PIDs and exit codes.
- A hollow union mesh's AABB covers the whole court (`Derived union of source outer envelope walls` spans the enclosure),
  so clearance checks must decompose unions into constituent boxes (116 for the outer envelope) or every placement fails.
- `SM_KeruvimStudyV1` has 100 material slots; setting slot 0 is not enough, loop over all slots and verify `slotsNotGold == []`.
- Package: `RunUAT.bat BuildCookRun -project=<uproject> -noP4 -platform=Win64 -clientconfig=Development -build -cook
  -map=<map> -stage -pak -iostore -archive -archivedirectory=<new> -utf8output -unattended`. Wait for editor exit first.
- `spawn_actor_from_object` returns None in commandlets: use StaticMeshActor/SkeletalMeshActor class + checked `set_*_mesh`.
- Saved skeletal animation: `override_animation_data(anim, True, True, phase, rate)`, not transient `play_animation`.
- Compare numeric transform fields, not `str(Transform)` (contains memory addresses). Cache actor snapshots once.
- `new_map_from_template` with an external filename silently yields the current/empty world; use package paths and assert actor counts.
- A dirty-map guard can fire after asset saves that touch a loaded map's components; read the per-item statuses in the
  receipt before calling the whole job failed (terrain-winding-fix: four tiles fixed, overall status "failed").
- Imported architecture names carry the `architecture_` prefix; inspect exact component paths and bounds.
- Skeletal FBX export crashes under NullRHI. `SK_Mannequin` is a Skeleton; `SKM_Manny_Simple` is the mesh.
- `ActorComponent.set_auto_activate` is ignored after registration; use `deactivate()` + the `auto_activate` property.
- `unreal.Rotator` needs explicit pitch/yaw/roll keywords. `EditorAssetSubsystem.duplicate_asset(src, dst)`.
- `MP_PixelDepthOffset` is hidden in UE 5.8 Python. Multi-mesh FBX import: pass literal `destination_name='None'`.
- Loading barrier must precede warmup; early gray frames were a loading issue, not lighting.
- Receipt JSON written by PowerShell carries a UTF-8 BOM; read with `encoding="utf-8-sig"`.

## Astra takeover baseline (2026-09-07)

Current evidence supersedes the older Walkthrough-06 state above: see RELEASE-NOTE-Walkthrough-08.md and HANDOFF-FOR-GPT-ASTRA.md. Walkthrough-08 packaged launch, Start/P/preparation-P/Quit passed interactive observation; fresh east-gate and Mount-platform synthetic walk completed with zero errors (release-walk-20260907T211526Z.json). Baseline capture release-capture-20260907T210550Z preserves actual visual defects: occluded Kotel, bright gold/rear wall, plain context surfaces. Its bus-labelled image is not bus evidence because the old capture used BUS_XY/BUS_YAW candidate constants. Capture cameras for multipart props must derive from current saved actors and verify their common origin; do not reuse historical placement candidates. The new capture fix affects only the test script, not maps or runtime assets.

## Kotel repair applied after the 08 baseline

The native diagnosis matched the current source meshes (occlusion-diagnostic-20260907T211954286509Z.json). The guarded repair then saved and reopened the combined map with two duplicate city-wall cut meshes; receipt SourceAssets/kotel-detail/KotelStoneV1/occlusion-fix-20260907T212114614138Z.json. No recorded errors; protected map and original wall-asset hashes all unchanged. Combined map now aeb9f7c2998742a6f49b2f6ec5a022ee51f3a6e23950a9c97026fb8d92edebd3. Checkpoint: C:\Mikdash\Working-5.8\ReviewCheckpoints\KotelOcclusion-20260907T212114614138Z. This is an uncooked post-08 change; focused visual review pending. Lighting/context-material steps remain unapplied.

Kotel visual verification completed: SourceAssets/visual-review/release-capture-20260907T212248Z contains two post-repair views, zero capture failures, savedMapUnchanged=true. Both images were inspected: the previously blank occluding slab is gone and the block-course overlay is visible. Acceptance is limited to visibility/occlusion; smooth uniform surfaces and shallow relief still need material/lighting refinement. This remains an uncooked change for the next build.

Lighting native compatibility findings: UE 5.8 EnumBase does not support int(enum); record a verified member name and the numeric repr only when available, preserving named restore. ExponentialHeightFogComponent's editable bool is enable_volumetric_fog (bEnableVolumetricFog in the installed header), not volumetric_fog (the setter is named SetVolumetricFog). Two failed apply attempts preserved the map bytes and their receipts/checkpoints. Do not infer that dry-run discovery exercises setters or newly created components.

Lighting apply succeeded on the third attempt: SourceAssets/lighting-review/native-apply-20260907T213137023951Z.json, lighting_polish_saved_reopened_visual_acceptance_pending, 82 changes applied, zero skipped, protected hashes unchanged. Morning sun/auto exposure/fog/fill are now in the working map; native visual comparison is pending. Earlier failed receipts are preserved.

Interior exposure review: EV8 minimum (raw luminance 256 with extended range off) made the Kodesh nearly black in release-capture-20260907T213307Z. Guarded release_interior_exposure_fix.py restores the prior EV0 minimum (1.0) while retaining EV14 maximum (16384). Initial save succeeded but verification encountered a stale actor reference after level reload; cache actor names before reloading, then reacquire objects. Follow-up fresh commandlet confirmed saved 1/16384 values. New renders pending. Lighting save helpers must persist mapSaved/hash immediately after save, before reopen can fail. Context textures/materials imported successfully with zero map change; assignment remains pending.

Context materials applied and reopened: native-apply-20260907T215013179583Z.json handled walls/Kotel cuts; native-apply-20260907T215118571170Z.json handled 4567 remaining meshes, zero errors, protectedMapsUnchanged=true. Total 4627 meshes across seven categories; both KotelCut duplicates explicitly included. Combined map bytes remain d505aa543a106183d849880ada6a4c38d075c3cde8f08239bea41ecee266ae4b. IMPORTANT: shared StaticMesh material dependencies changed, so donor maps may look different despite unchanged .umap hashes. Context visual acceptance pending. Credits now enumerate all seven architecture and six context CC0 photographic texture sets.
Exposure capture release-capture-20260907T214622Z: three views, zero failures, savedMapUnchanged=true. Heikhal and Kodesh images inspected; Kodesh visibility regression is resolved, Aron/relief readable; Heikhal back-wall highlight remains too bright for final-quality acceptance. Spec now carries EV0 floor for future apply consistency. Public source accuracy/keruvim/model fidelity gaps remain open.

Bus native audit found 991 mismatched effective material slots across the thirteen multipart meshes. Isolated BusVisualAuditV1 repair saved/reopened; capture release-capture-20260907T220851Z inspected: ivory/teal body and transparent glazing now visible. release_adopt_material_reviews.py -AdoptBus adopted only those component materials, saved/reopened with unrelated scene snapshot and protected hashes unchanged; combined map now18b87c00447685f1102858f5344ba8f0e12cc3405064dc479ab69fc682a51155. Tire/road contact remains unverified. KotelSurfacePolishV1 rejected visually for parallel sine bands; V2 uses continuous3D noise, native capture pending.
Resident population Editor C++ build passed (Astra-Population-Editor-Build.log). Isolated review map native-resident-review-20260907T222556423474Z saved/reopened with source map/assets unchanged; behavior NOT tested yet. Whole-scene snapshots must key by actor native name, not editor label: duplicate labels are legitimate. EditorActorSubsystem factory logs can show intermediate placement (Z492) before its final SetActorLocationAndRotation; saved/reopened body Z396 and capsulehalf96 establish feetZ300. Do not lower actors from intermediate spawn logs.

Kotel photograph import: cache whole-scene actor inventory once per verification, never call inventory() inside a per-actor generator (7300 actors causes quadratic native calls). PhotoSurfaceV1 partial import was stopped at that verifier; assets/checkpoint preserved. Corrected rerun uses fresh KotelPhotoSurfaceV2. User photos are private attachments; only cleaned wall derivative belongs in publication, with AI reconstruction/aspect-fit limitations recorded.

Kotel photo-color pass adopted into main: photo-adoption-20260907T225252321046Z.json, saved/reopened with protected hashes and unrelated actor state unchanged; SHA 17ca6fe7ab34a7a5fb56cd99c645b8921a205967f3bb8d9410f0832cf195d7a3. Four noncolliding photo panels cover the audited source faces and six procedural overlays are hidden. Native review release-capture-20260907T224816Z inspected both images, zero failures. Acceptance limited to photograph-color application; softness, flat relief, warm light and stretched stone proportions remain open. This post-08 update is not yet cooked. Python root_component is exposed via get_editor_property, not get_root_component(). TextureSample Coordinates is shortened to UVs by the material editing API.

Dove/resident integration: native Editor build Astra-Dove-Resident-Editor-Build.log succeeded. Five residents adopted into current map with default-off population BeginPlay opt-in explicitly enabled only for the configured actor; source mesh/animation and donor hashes unchanged. Main SHA2edb00afb822cb44e1f528fc03f5783d15d0e7a4faf043456b0060b7d96fc9bd. native-flight-20260907T231003184270Z.json passed live PIE: dove moved23.30m, ascended15.94m, pause drift0, restored same walkingpawn/position with collision, all five residents physically arrived. This is a small authored pilot, not a complete populace. Visual/keyboard acceptance pending. Flight F toggle uses separate original stylized whitebird pawn, Space/Ctrl altitude and Shift boost. The original walking pawn stays collision-enabled at departure. PlayerController get_pawn is not Python reflected here; use GameplayStatics.get_player_pawn.

Walkthrough-09 freshly packaged at C:\Mikdash\Builds\Walkthrough-09 (UAT exit0,230s, mainmapunchanged). ActualchildSHA b20685fc7021cab1cb2728576db025d03404f7515880016f5fa862729de87c11. Menu dove request now queues untilgrounded up to3real-time seconds and shows failurestatus. Game/editor bothcompiled duringcook. Packagedwindow opened and menu visible behind WindowsFirewall prompt; user asked to clickCancel. Do not automate that security prompt. Packagedmenu/F-return/visual/audio checks remain pending in SourceAssets/runtime-review/walkthrough-09/launch-receipt.json. All five residents and dove movement/pause/exactreturn passed mainPIE before packaging. Native walking receipts225836 andsanctuary230012 bothzeroerrors. Currentinteractive game childPID43340, bootstrap12764; requery beforeanyaction.

Download release preparation (2026-09-07): Walkthrough-09's combined ZIP is 2,277,773,468 bytes, above GitHub's per-asset limit of less than 2 GiB. Publish App.zip and Data.zip with the same extraction root; Data contains only MikdashCourtyardV3/Content/Paks/MikdashCourtyardV3-Windows.ucas. UAT did not stage loose Content/Distribution/CREDITS.txt, so distribution preparation explicitly includes credits and third-party notices. Never include private photo originals, project Saved logs or source books. A custom C# downloader was rejected by Windows antivirus during actual launch; it was not allowed, bypassed or distributed. Its source is preserved outside the publishing clone. Use ordinary ZIP distribution. Standalone packaged controls remain unverified behind the existing firewall prompt; native PIE test evidence does not remove that limitation.

Walkthrough-09 download preview published: https://github.com/ShmuelSokol/3rdbhmk/releases/tag/walkthrough-09-preview . Final App ZIP 173147367 bytes SHA256 8a9a0d6f1db9d022181e2fcdde3e0a477beedbdcbd638e2fb25b1159b8b89911; Data ZIP 2104623696 bytes SHA256 32d4a90fe09e88dadf3c46679f85601363a9c6c420865f74b5affcffb6a939c3. Both downloaded fully without authentication, matched expected archive hashes, extracted to a new folder, and all 49 original runtime files matched the original package. Receipt in publishing clone distribution/windows/public-download-receipt.json. Release is an explicit prerelease; packaged interactive checks and broader visual/source-accuracy work remain incomplete. Distribution instructions/source committed as bcc8e53d. No custom setup executable was published.

Claude overnight takeover: read HANDOFF-FOR-CLAUDE-FABLE-OVERNIGHT.md first. It supersedes obsolete unapplied-step claims in earlier handoffs, records the verified 09 public download, and prioritizes visual improvements plus fresh candidate verification. At creation, no Codex agents/native build jobs remained active; existing 09 game processes still existed, so requery before process actions.

Astra resumed 2026-09-08: user handoff says prioritize integration of landed Walkthrough-12 systems, not source-only completion. Maximum four active Codex agents including coordinator (current runtime slots); bounded waves, no overlapping native jobs. Amah stays 50 cm and enclosure scenario stays unchanged pending user's decisions. MetaHuman Core Data is installed; MetaHumanCrowd is absent from .uproject. Tests belong Plugins/MikdashRuntime/Tests outside Source. Localization staging now explicitly includes Localization/Mikdash as UFS (paths relative to Content); packaged readback still requires a fresh cook. PID2316 observed as Claude's bounded perf_probe with 1680-second warmup/1900-second limit; do not terminate it as a zombie.

Verification guard correction (Astra 2026-09-08): tasklist /FI 'IMAGENAME eq UnrealEditor*.exe' fails with an invalid-filter error, but old verify.py ignored its return code and falsely passed while PID2316 was live. Use tasklist /FO CSV /NH, check exit status and nonempty parse, then match editor names. --build now refuses to launch UBT if any pre-build check failed. Passing an old 7/7 receipt does not prove no editor was running.

Source recovery (Astra 2026-09-08): MikdashTourGuide.cpp contained an actual NUL byte inside NewKeys[Row].Add's character literal, which made rg treat it as binary. Replaced with the textual C++ escaped zero terminator. Scan newly recovered source for embedded NUL bytes; successful offline math tests do not compile every Unreal .cpp. UBT verification still required.

Takeover resumed after Claude finished (2026-09-08): latest published source b28b42ec; current offline gate 7/7 and 25/25 math tests, Editor build up to date/succeeded. User has approved the book-selected 48 cm amah; earlier "awaiting user decision" wording is superseded. Active geometry remains legacy 50 cm until a checkpointed migration reconciles all dependent placements and passes native checks. Modern city, Kotel, people and physical eye/capsule offsets must retain metric dimensions. Enclosure scenario/modern-building visibility remains unchanged pending a mapped, sourced decision. Do not overwrite Claude's final source from the earlier Astra checkpoint.

Frontend probe finding (2026-09-08): native-frontend-flight-20260908T132413130117Z passed menu/settings/preparation transitions but measured zero forward flight before a short wall-clock deadline. It is a failure receipt, not flight acceptance. The diagnostic follow-up requires both simulated world time and at least 20 input ticks before measuring motion, and records velocity, pause/menu and ignored-input state; expensive Nanite/startup frames can otherwise consume the deadline before input has been simulated. Keep the real-time watchdog and verify pause using wall time.

Frontend probe diagnosis (same takeover): the repeated zero-motion result has moveInputIgnored=true throughout 60 input ticks with pause/menu false. MikdashCinematics is an automatic GameInstance subsystem and starts its native intro fallback on OnWalkthroughStarted even before a LevelSequence is placed; the intro intentionally locks movement with SetCinematicMode. Flight tests must exercise SkipIntro and verify both move/look input unlock before flight. "Not placed in the map" does not mean a subsystem is inactive. Do not reset input locks blindly to force a test pass.

Post-Nanite render startup (2026-09-08): 24 observed base materials lack saved Nanite usage flags. Editor auto-repair is transient and warns about rendering outside the editor; persist exact observed material flags with checkpointed release_nanite_material_usage.py, then verify in a fresh process/cook. Do not blanket-save all dirty assets or mistake the long initial derived-data barrier for completed captures.

Water integration audit (2026-09-08): release_water.py's HOST exemptions do not perform floor cuts. Generated court water tops are 26 cm below intact paving (599/625, 474/500, 274/300 cm), with submerged kerbs too. The generated manifest already acknowledges the missing boolean. Require exact cavity openings in duplicated host render geometry and collision before calling the stream integrated; raw actor AABBs and a successful placement receipt cannot prove visibility.

Native integration (2026-09-08): FX director/materials and 240-agent crowd saved and reopened successfully; see TAKEOVER-STATUS-20260908.md for receipts. This supersedes "none placed" for those two systems only. Crowd command-line parser must pass the literal 'CrowdCount=' to parse_param_value; using 'CrowdCount' returns '=240' and fails integer conversion. Direct/menu dove flight must finish the cinematic before possession, otherwise cinematic input locks/view handover can conflict with the bird. A fresh C++ build passes; physical controls and visual acceptance remain separate.

Diagnostic camera trap (2026-09-08): the four saved review CameraActors have manual outdoor exposure ISO100/f8/1/125 and post_process_blend_weight=1. Their exposure overrides the adaptive global volume, making indoor screenshots misleadingly dark. This was confirmed by native lighting-inventory and Content/Python/v3_materials.py, not inferred from a frame. For a walking-equivalent PIE diagnostic, set the temporary PIE camera's blend weight to0 and verify actual PlayerCameraManager location; never change room lighting to compensate for that camera override. Menu/direct flight regression uses separate fresh PIE entries because the once-per-session cinematic setting is protected; do not try to rewrite it in Python tests.

Pacing correction (2026-09-08): the user again corrected stopping after a verified checkpoint. A checkpoint is an intermediate result under the standing sustained-build instruction. Continue independent authorized build/test/fix work; only the specifically held paroches designs require approval. Report actual activity honestly rather than implying work continues after a turn ends.

Verification launcher correction: passing an already quoted Build.bat command as a subprocess list element adds literal escaped quotes before Program Files and prevents UBT starting. Scripts/verify.py now invokes its fixed local batch command with shell=True and preserves both stdout and stderr in a unique external verify-ubt log. A launcher failure is not evidence of a C++ compile failure.
## Collision state verification — 2026-09-09 08:41 UTC

Kotel walk084132 now ascends and reaches platform/upper-deck return, but then deflects
south near x=-13585 and leaves the corridor. Preserve failure; forward capsule diagnostics
are added without changing route/capsule/tolerances. Walking roundtrip is NOT accepted.
Capture084353 failed before images: ThirdPartyFolder is protected even under its raw name.
Verify public BuildCredits output coverage instead; do not add an API solely to bypass this.

Full gate passes 9/9 and 32/32 math; UBT succeeded (verify-ubt-5icewpn7.log).
The nonfatal ServiceActor own-header-order diagnostic is corrected in source; rebuild pending.
Native candidate-collision-restore-20260909T083903043338Z passes five instantaneous
state/explicit-restore checks across 269 selected actors, including original-false fixture
and protected Kotel collision. Maps and original saves unchanged. This does not establish
partial-transition, independent EndPlay/rebuild, or walking-route acceptance. Kotel walk is next.
Visible Kotel V2 samples the cleaned photo palette but uses generic sandstone textures;
the retained PhotoSurfaceV2 materials project world-position imagery and are not currently visible.
Do not claim the actual photo is applied to V2. A PIE-only material comparison is being prepared;
photo joints and procedural geometry may mismatch, and the panorama is aspect-fitted.
## Wider visual/credits check — 2026-09-09 08:49 UTC

Capture084554 completes two inspected PNGs with zero errors/failures and all maps,
material instances and original saves unchanged. Native BuildCredits includes all18
reviewed names; screen/package readback remains separate. QPC intervals at1014x550:
north p50/p95 23.70/27.89ms; Kotel22.31/25.50ms, each8seconds. Not packaged FPS.
North entrance is readable but top still cropped; wide Kotel is visible with generic
dark masonry, sparse gray figures and haze. Photo-on-stone A/B is running, not adopted.
## Photo comparison and access finding — 2026-09-09 08:56 UTC

Photo A/B084910 passes four transient assignments, restoration and preservation.
Root and independent verifier accept the photographed weathering as a limited improvement;
explicit visual-acceptance-20260909T0854.json pins the two images/receipt and limitations.
No adoption yet. Photo joints can mismatch V2 geometry; panorama stretch/haze remain.
Kotel return failure085303 repeats, but forward capsule lifted5cm reports no hit near
deflection. Next diagnostic uses the actual capsule centre to detect shallow contact;
do not claim a dynamic actor or platform cause yet. Original maps/saves remain unchanged.
## Clean rebuild — 2026-09-09 09:00 UTC

Full gate9/9,32/32math and UBT4actions16.54s pass in verify-ubt-3x8p_4_e.log;
ServiceActor own-header diagnostic is resolved, log has no warning/error matches.
Candidate-only photo material adoption is now running under the explicit visual receipt.
Fresh process verification is still owed; do not publish a saved-map claim before receipt.
## Candidate photo materials saved — 2026-09-09 09:02 UTC

candidate-photo-depth-20260909T090038688444Z reports saved_reopened, four slots,
zero errors/protected differences/new Content files. Candidate SHA is now
dcea5bf85498cabd519c182e3665792cbe732d358ebac94cdfcdec0032c0e7e1.
Only candidate V2 material overrides changed; photo source assets/Main remain unchanged.
Checkpoint CandidateKotelPhotoDepth-20260909T090038688444Z preserves the old map.
A separate process is verifying persisted scene/material identity now; default/cook remains Main50.
## Photo adoption independently verified — 2026-09-09 09:04 UTC

Fresh process candidate-photo-depth-20260909T090248379625Z passes four saved materials,
canonical unrelated scene baseline and protected-content checks, zero errors/new files.
Candidate dcea5bf8 is ready for the next access diagnostic; visual acceptance stays limited
to weathered photo appearance, not joint alignment/lighting/finished characters.
Source/visual/collision checkpoint is being verified for publication. No fresh package yet.

## A material is not accepted until a frame shows it

Added 10 Sep 2026, after `M_AntiRepeat_Triplanar` shipped onto 1,488 Herodian ashlar slots across
both maps and had to be reverted.

Its acceptance was numeric parameter parity after save and reopen, plus an offline field
simulation. Both were real and both were green. **Neither draws a pixel.** The build ran under
`-nullrhi`, where `get_statistics` returns 0 for every shader counter because no shader map
exists at all — the receipt said so honestly, and it was read as a missing nicety rather than as
the acceptance gap it was.

What it missed: the material selected mips roughly 3–4 levels too coarse on Nanite meshes.
Measured with an in-frame control — same textures, same tiling, same frame, same exposure —
surfaces on stock `M_PBR_Tiled` held gradient energy at ×1.03 while the new master fell to ×0.20.
On the ashlar that predicts colour, coursing and bed joints surviving while the drafted margins
and proud bosses disappear: the precise character the wall exists to show, failing in the way
that still reads as "a stone wall" in a still.

The cause is worth knowing because it is not "Custom nodes are unsafe". Other Custom-node
materials here sample textures perfectly well, because they let the sampler take derivatives
implicitly. This one passed hand-computed derivatives from a **warped** UV into
`Texture2DSampleGrad`, and under Nanite `ddx`/`ddy` are not ordinary quad derivatives.

So, for any material change:

- Parameter parity proves the asset carries what you wrote. It never proves what reaches the
  screen. Say which one you have.
- Acceptance is a real-RHI frame with an **in-frame control** — an unmodified surface on the
  parent material, in the same image, so the comparison shares lighting and exposure. That
  control is what made the gold measurement conclusive and its absence is what let this ship.
- `-nullrhi` is what makes a build possible on this box and what makes it unverifiable. State
  both halves with equal weight.
- If the machine cannot render, the honest status is *unverified*, not green.

---

## Herodian ashlar V5, 10 Sep — four things that cost time, written down so they cost nothing again

**1. A commandlet's flags are NOT in `sys.argv`.** UE consumes them. Read them off
`unreal.SystemLibrary.get_command_line()` and regex for your switch, exactly as
`Scripts/release_herodian_ashlar_v4.py:1017` does. A script that parses `sys.argv` finds no mode, exits
0 in 0.09 s, writes no receipt, and the UAT log says *"Python script executed successfully"*. It looks
exactly like a pass. **If no mode flag matches, raise — never return quietly.**

**2. `release_herodian_ashlar_v4.py`'s importer REUSES an existing asset path** without re-reading the
file (`import_texture`, `does_asset_exist` → `record['reused'] = True`). Regenerating the source PNGs in
place and re-running `-HerodianV4Import` therefore keeps the OLD pixels and still passes every readback
and hash check. To change a texture's content, import to a NEW asset name and repoint the material
instance's texture parameter.

**3. The ashlar blocks are NOT instanced, and no brief should say they are.**
`SM_0138_architecture_Inner_eastern_gate_wall_jamb_1` — the wall the walking-height frame is aimed at —
is one box: **8 vertices, 12 triangles, `uvLayers: []`** (`SourceAssets/architecture-manifest.json`).
The whole 2,633-mesh measured-architecture set averages ~20 verts, carries no UVs at all, and even the
Blender arris bevel is listed under `excludedRenderOnlyModifiers`. Every course, joint, drafted margin
and boss is triplanar texture from `M_PBR_Tiled`. There is no per-block instance array to jitter, and
"make the boss geometry" means building a HISM ashlar system from scratch.

**4. High-frequency texture metrics are meaningless until the images are at the SAME px/cm.** The wall
is authored at 6.83 px/cm and the approved paving at 2.51. Compared natively the micro-grain gap looked
like 18x; box-downsampled to a common 2.5 px/cm by `Scripts/measure_stone_grain.py` the honest gap is
7.8x. Match the resolution first, then quote the number.

**And the design lesson underneath all of it:** a boss fails to read as raised not because the relief is
too shallow but because the *ramp* is too narrow to survive mipping. V4's boss-edge bevel was 0.40 cm =
2.7 texels at mip 0 and under one texel at mip 2, which is the mip actually sampled at 4 m — so a
near-vertical arris (normal deviation p50 0.968) mipped down to a flat grey line and the wall read as
engraved. Width beats depth. Check the ramp against `TilingCm / textureSize × 2^mip`, not against the
measured centimetres alone.
