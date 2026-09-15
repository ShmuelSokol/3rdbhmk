# ResidentV4: the 24 residents rebuilt to read as people (cp23)

2026-09-11. Not committed. Offline generator + gate results below are final; the ENGINE and FRAMES sections
are filled in only from real receipts and packaged-build frames.

## The goal and the verdict it answers

Shmuel: *"I want the people looking real, like, legit real people. not, like, figures stilting along."*
The cp11 verdict (`visual-review/PEOPLE-IN-FRAME-20260910.md`) was: at 3 m the residents are painted wooden
mannequins. This pass rebuilds the six cast bodies with the procedural generator; MetaHuman stays blocked on
the Epic cloud sign-in.

**Direction: stylised-realistic, not failed photorealism.** True shapes that read at 3-5 m (a real
eyeball with iris, limbal ring and pupil; lids that wrap it; a sculpted nose, lips with a mouth line, ears,
beard and hair as geometry), clean surfaces, age lines only on the elders, a faint pore map. The coordinator
agreed. Honest read of the six faces side by side (`previews/faces-lineup.png`):

| face | reads as |
|---|---|
| Man_Standard | a man with a short dark beard - correct |
| Man_Heavy | a heavy man, full black beard, turban - correct |
| Man_Elder | an old man, long white beard, white brows, lines - correct |
| Woman_Elder | an older veiled woman - correct |
| Woman_Young | a young beardless face in a coloured veil; **the veil carries her sex more than the face does** |
| Youth | a young beardless face under a cap; the lower face is still slightly blocky |

## Files

- `Scripts/create_resident_v4.py` (+ `create_resident_v4_face.py`, `create_resident_v4_body.py`,
  `create_resident_v4_textures.py`, `render_resident_v4_faces.py`). Imports create_pilgrim_v3 and
  create_kohen_gadol_v1 and changes neither.
- `Scripts/release_resident_v4.py` (-RV4Import / -RV4ImportRevert / -RV4Apply / -RV4Revert /
  -RV4RevertAndReapply / -RV4ApplyAll, full guard pattern), `Scripts/run_resident_v4_engine.ps1`
  (detached chain; slot = no editor, no game, no dotnet running UAT or UBT).
- `Scripts/measure_kohen_garment_clearance.py`: additive `--body v4:<variant>` hook; Kohen Gadol defaults
  unchanged (regression: idle 0.00 / 0.00 over 97 samples, identical to the stored receipt).
- C++: `Plugins/MikdashRuntime/Source/MikdashRuntime/Private/MikdashResidentPopulation.cpp` - after the
  single-node animation mode is set, Face0..Face3 morph weights from a hash of the person's stable id, only
  if the mesh carries those targets. No class-layout change.
- Offline evidence: `meshes/` (six GLBs), `resident-v4-manifest.json`, `previews/`, `clearance/final-*.json`,
  `textures/`, `gate-status.json`.

## What changed on the body

- **Face** (one dense sculpted head per variant, front-weighted grid ~0.15 cm at the eyes and mouth): eye
  sockets round a real eyeball; lids that are the more forward of the carved socket and the ball + 0.12 cm,
  so the ball can never show through; a lash line and lid shadow; brows painted flush on a sculpted ridge;
  nose, alae, Cupid's bow, fuller lower lip, mouth line, philtrum, chin, a mandible border with the jaw
  turning under, a narrower neck set back from it; naso-labial folds and lines scaled by age; ears with
  helix, concha and lobe; beard and hair as offset shells of the head with strand clumps.
- **24 faces from 6 meshes:** four face-shape morph targets (nose, jaw, brow, lips), weighted per resident
  by the C++ hook. The build refuses two variants with the same face (6 of 6 distinct fingerprints).
- **Shading:** per-vertex skin tint (cheek, nose and ear flush, lip colour, orbit shadow, beard shadow,
  under-jaw occlusion), baked cavity shading on every part, cm-true UVs on every part for a weave / slub /
  pore / strand texture set (authored offline, tileable). Skin master is Subsurface; every master has
  bUsedWithSkeletalMesh and bUsedWithMorphTargets.

## Dress: sourced vs authored

| item | grade | source / note |
|---|---|---|
| tzitzit on the four corners of the men's mantles, one thread of techelet | S | Numbers 15:38-39; Deuteronomy 22:12. Placement on this draped panel and the string count are authored |
| no tzitzit on the women's mantles | S | Menachot 43a (time-bound precept) |
| married women cover their hair | S | Mishnah Ketubot 7:6. The veil form is authored |
| two coloured clavi on the tunic; notched corner bands on the mantle | R | Yadin, Cave of Letters finds (1963) - cited from general knowledge, NOT re-read in this pass |
| leather sandals with toe and ankle thongs | R | Cave of Letters / Masada - general knowledge, not re-read |
| every face, colour, hem, fold, the bloused belt, all clearance offsets | A | authored |

Hems (rest z of the lowest point): men 32 / 30 / 24 cm (mid-calf; the 72 cm WalkV2 stride now shows), women
18 cm (lower shin), youth 44 cm (below the knee). Mantles end at 52-58 cm; women's at 58 cm (see below).
The women's veil is in the garment slot, so each woman's veil takes her own garment colour.

## Defects fixed, with the measured cause

- **"Torn paper" over-tunic** (cp11): not an alpha edge (the garment instances are opaque). The tunic's folds
  pierced the mantle by up to **6.9 cm at rest**. Fix: the mantle is built as an offset of the tunic surface
  on the tunic's own ring heights, each vertex anchored to the tunic point beneath it (identical weights),
  and it rises over the belt band.
- **Youth's cylinder legs:** anatomical legs (calf, shin, malleoli, knee), foot with heel, arch and toes.
- Found and fixed in offline review before any cook: masculine young woman, floating brow dashes, a pink
  caruncle blotch, a gap at the jaw, staring eyes, belt through the mantle, neck stalks under the chin, and
  **almond holes through the back of the skull** (the lid logic tested only x and z, so back-of-head
  vertices at eye height were pulled through the head - hidden under headcloths, visible under a turban).

## Clearance (the whole cycle, final meshes)

`measure_kohen_garment_clearance.py --body v4:<variant> --clips walk,idle --rate-scale 0.5`: leg vertices
(legs, feet, toes) against the tunic, and tunic vertices against the mantle; two independent tests must both
say outside, above the local hem. Gate `gate-status.json` (v4) passed.

| variant | walk: leg / mantle (144 @ 120 Hz) | idle: leg / mantle (49 @ 15 Hz) |
|---|---|---|
| Man_Standard | 0.00 / 0.00 cm | 0.00 / 0.00 cm |
| Man_Heavy | 0.00 / 0.00 cm | 0.00 / 0.00 cm |
| Man_Elder | 0.00 / 0.00 cm | 0.00 / 0.00 cm |
| Woman_Young | 0.00 / 0.00 cm | 0.00 / 0.00 cm |
| Woman_Elder | 0.00 / 0.00 cm | 0.00 / 0.00 cm |
| Youth (no mantle) | 0.00 cm | 0.00 cm |

What it took (each measured, most were not the first idea):
- Back of the knee: the Kohen Gadol field let back-of-knee cloth follow the thigh while the flexing calf
  came through (0.07-0.40 cm). More ease made it WORSE. Fix: the thigh->calf handover rises behind the knee
  only (57 -> 42 cm instead of 52 -> 30), blended by rest y (+10 cm put back-of-thigh cloth on the calf:
  0.02 cm on Man_Heavy).
- Women's feet: at 12-15 cm hems the swing foot pierced the lowest rings (0.07-0.27 cm); an instep ease made
  it worse and was reverted; toes shortened into the V3 foot envelope; hems to 18 cm (the me'il height).
- Women's mantles: at 46-48 cm the lowest row sat in the knee handover band (82% calf), swung up with the
  knee and crossed the thigh-weighted tunic by **2.3 cm** in the walk - hidden at first because my poll
  printed only the leg figure. Mantle hems to 58 cm (Man_Elder's, which measured 0).
- Youth: a knee-length tunic had put his leg top at rest z 70, above the region the tool measures (its signed
  wall is the tunic below z 60), and it read 11 cm "outside" at rest. Legs capped at z 58 - then 0.00.
- Men's and Youth's GLBs are byte-identical to the build their receipts measured.

**Known limit, not a clip:** at push-off the back of a long hem trails as a flat wedge (linear skinning, no
cloth simulation) - the same limit the Kohen Gadol receipt records.

## Budget

Triangles per resident: Man_Heavy 57,648; Man_Elder 55,528; Man_Standard 55,312; Woman_Young 50,732;
Woman_Elder 50,732; Youth 39,164 (generator ceiling 60,000). Cast: 5 Man_Standard, 4 Man_Heavy,
4 Man_Elder, 5 Woman_Young, 4 Woman_Elder, 2 Youth = **1.26 M skinned triangles if all 24 draw at once**
(V3: 13-20 k each). `PERFORMANCE-BUDGET.md` has no per-character line (characters are non-Nanite by rule;
the scene carried ~30.5 M triangles before Nanite). **No LODs are generated yet** - that is the obvious next
cost cut for residents beyond ~10 m. Frame time with the new bodies: not measured in this pass.

## The crowd (vertex-animation bodies)

**Not re-baked.** The crowd's VAT bodies were baked from the six V3 meshes and are decimated to 2,400
triangles for 30-200 m, where these faces cannot show. The mid-calf hem and the mantle-over-belt silhouette
would show. Cost to re-bake: repoint `create_crowd_vat_v2.spec.json` variants at the V4 meshes (same
skeletons, same WalkV2 clips), one hidden-editor bake (the last one took 26 s of work inside ~5 min with the
editor load), the bounds step, two guarded map applies and verification, then a cook.

## The v4b refine pass (15 Sep): Woman_Young and Youth

The 11 Sep verdict on the six faces kept two honest complaints: the young woman's **veil carried her sex
more than her face did**, and the youth's **lower face was blocky**. Both were fixed offline BEFORE the
import, through one new face parameter, `refine` (`create_resident_v4.py` FACES): **Woman_Young 1.0,
Youth 0.65, absent everywhere else**. Every term reads it through `F.get('refine', 0.0)`, so the other four
faces are untouched code paths, not re-tuned ones.

What it changes (`create_resident_v4_face.py`, constants `JAW_W / JAW_Z / JAW_S / TAPER / MOUTH_IN /
MOUTH_Z / LIP_UP / LIP_LO / CHEEK_FILL / MUZZLE_BACK / BROW_MIN_W / LIPS_BACK`):

- **The jaw is a rounded U, not a shelf with a tab.** The mandible under-turn was a CONSTANT inset that
  grows with |x|, so it squeezed every lower-face vertex into one narrow band: that is what made the chin
  read as a tab hanging under a jaw shelf (measured on the first attempt, which narrowed the jaw and made
  it worse). On a refined face the under-turn is a PROPORTIONAL taper (`-x * TAPER * under_r`), the
  mandible body carries wider toward the gonion, and the width at mouth level comes in, so the widest
  point of the face is the cheekbone.
- **Fuller cheeks, less muzzle.** The hollow beside the mouth is filled (`CHEEK_FILL`), and the mouth block
  is set back level with the cheeks (`MUZZLE_BACK`, `LIPS_BACK`) - the three-quarter view had a snout.
- **A finer brow ridge** (the skull's ridge is undone further on a female refined face), and **continuous
  brows**: the painted brow band is now at least one head-grid row tall (`BROW_MIN_W`, rows are ~0.25 cm at
  the brow), because an arched 0.13 cm band fell BETWEEN rows and broke into dashes.
- **Fuller lips** on the female face (`LIP_UP`, `LIP_LO`, and a wider lip colour band), a lighter mouth line.
- **A narrower neck set back** under the jaw (10% narrower, 0.9 cm back), so the jaw and neck stop reading
  as one slab.

Evidence, all offline and looked at, not just measured:

| file (previews/) | what it is |
|---|---|
| `faces-lineup.png` | the six faces after the refine - the coordinator's gate image |
| `faces-lineup-before-v4b.png` | the same strip before it (same camera, same code except the refine) |
| `faces-lineup-v4a-20260911.png` | the 11 Sep strip, kept |
| `faces-v4b-WomanYoung-Youth-before-over-after-2x.png` | the two faces at 2x, before over after |
| `faces-v4b-heads-front-tq-side-before-over-after.png` | bare heads, front / three-quarter / side, before over after |

**Regression, by hash.** The other four faces are byte-identical, twice over: the head grid, neck and skin
colours hash the same under the original modules and the patched ones (loaded side by side from separate
directories), and all four GLBs were REBUILT from the patched generator to the same sha256 as their 11 Sep
receipts (`Man_Standard db256f23…`, `Man_Heavy ca799b0a…`, `Man_Elder 1de7f12b…`, `Woman_Elder a65ad077…`).
Six face fingerprints are still distinct.

**Clearance re-run on the final meshes** (`--body v4:<variant> --clips walk,idle --rate-scale 0.5`, the same
gate as the table above): **0.00 cm leg-outside-tunic and 0.00 cm tunic-outside-mantle for all six**, over
144 walk frames at 120 Hz and 49 idle frames at 15 Hz. `gate-status.json` = `clearance_zero_v4b_refine`.

**Honest limits of the refine.** Her mouth still sits a little forward of the cheeks in three-quarter view,
and the veil still does part of the work. The eyes and nose were not re-authored in this pass.

## ENGINE (cp/rv4a, 15 Sep - import, both maps, cook)

Runner `Scripts/run_resident_v4_engine.ps1` (Label `rv4a`), started only after the coordinator's
`SLOT-cp26-review-done.txt` appeared, one native process at a time. **`editorbuild` was deliberately
skipped: no C++ was touched in this pass**, and both the Editor DLL and the Game exe (15 Sep 15:57-15:58)
post-date the Face0..Face3 hook in `MikdashResidentPopulation.cpp` (11 Sep 05:21), which was verified
present in the current source. The cook builds the Game target itself, so editor and game stay in sync.

| step | receipt status | exit | what the receipt proves |
|---|---|---|---|
| import | `imported_saved_readback_apply_pending` | 3 (see below) | 4 textures, 2 masters, 6 slot + 8 garment instances, six meshes onto the EXISTING V3 skeletons; **Face0..Face3 present on all six**, bone sets unchanged, GLB sha256 matched the manifest per variant; 328 protected assets unchanged |
| apply48 | `apply_saved_reopened_readback_frame_pending` | 0 | Candidate48: only the population actor changed (`sceneChanges []`), saved, reopened, read back as the six V4 meshes + `RV4_Garment`; Main50 bytes unchanged |
| revert48 | `revert…` then `apply…` | 0 | `-RV4Revert` read back **all six V3 bodies**, the re-apply read back **all six V4 bodies** - the undo works |
| apply50 | `apply_saved_reopened_readback_frame_pending` | 0 | Main50: same, `sceneChanges []`, Candidate48 bytes unchanged |

**The import's exit code 3 is a shutdown crash, not a failed import, and the difference is checked, not
assumed.** The receipt was written at 22:43:17 and every asset was on disk by 22:43:53; the fatal came at
22:43:59-22:44:12, after `quit_editor`, as `Object is not packaged: ModeManagerInteractiveToolsContext
None` (UObjectGlobals.cpp:3302) - an editor-shutdown ensure under `-nullrhi`. The receipt carries
`errors []`, `protectedChanged []`, and the `dirtyPackagesLeftUnsaved` list is exactly the per-variant
Interchange materials the script deletes as unreferenced (no such files exist on disk). The two applies
that followed loaded all six meshes, their skeletons and their slots, which is an independent reopen of
what the import wrote.

**One honest caveat on the revert proof.** A resaved `.umap` is not byte-stable, so the revert did not
return the map to its exact previous bytes (`3f986fb6 -> bb3d29cd -> d570668c -> c1aa90b2`). What is proven
is semantic and is the thing that matters: after the revert the population read back six V3 meshes and the
V3 garment materials, after the re-apply six V4 meshes and the eight `MI_RV4_Garment_*` instances, with
`protectedChangedExcludingThisMap []` every time. Map checkpoints for both maps are in
`C:\Mikdash\Working-5.8\ReviewCheckpoints\ResidentV4-*`.

## FRAMES (packaged rv4a, Candidate48, camera `3300 2434 380 -4 90 0`)

`movie-rv4a-yoav-lane-3m5/`: 219 frames of the RUNNING world, 0.1 s of game time apart
(`-dumpmovie -benchmark -fps=10`, 1920x1080, 21.9 s), `movie-receipt.json` status
`movie_captured_visual_review_pending`, `errors []`. Frame-for-frame comparison with cp11 is NOT possible
here: cp11 ran 894 frames over 89.4 s, this pass 219 over 21.9 s, so frame N is a different moment. The
comparison below is like-for-like by DISTANCE, not by frame number.

| frame (visual-review/) | distance | what it shows |
|---|---|---|
| `rv4a-people-elder-face-2m-4x.png` | ~2 m | Man_Elder's head filling the frame, 4x |
| `rv4a-people-man-turban-face-3m5-6x.png` | ~3.5 m | Man_Heavy, turban, three-quarter, 6x |
| `rv4a-people-youth-walking-4m-4x.png` | ~4 m | the Youth mid-stride: belted tunic, bare shins, sandals |
| `rv4a-people-veiled-woman-4m-5x.png` | ~4 m | a veiled woman walking, mantle over the tunic |
| `rv4a-people-woman-walking-5m-5x.png` | ~5 m | Woman_Young in a madder mantle, mid-stride |
| `rv4a-people-group-3to25m.png` | 3-25 m | the group frame: a dozen residents at reading distance |
| `rv4a-people-near-and-group-2to20m.png` | 2-20 m | a near body and the courtyard behind it |

### The verdict: do they read as real people, or as mannequins?

**At 3-5 m, walking, in a group: they read as people.** This is a real change from cp11. The bodies have
weight and the dress does the work - mid-calf tunics with a belt bloused over them, mantles that hang as
separate cloth, veils on the women, bare shins and sandals on the youth, and no two neighbours in step.
The group frames show a courtyard of individuals walking at different paces, not a rank of statues. The
"torn paper" over-tunic edge of cp11 is gone: no tunic breaks through a mantle in any frame I looked at.

**At 2 m, face-on: they are not real people yet, and the failure is in the face, not the body.**
`rv4a-people-elder-face-2m-4x.png` is the honest one: the cheek is a broad flat plane, the nose reads as a
hard wedge, the beard silhouette is a jagged polygon cut-out with visible shards where the headcloth
crosses the face, and the eye is a dark smear rather than an eye. The turban face at 3.5 m is a flat slab
with dark smudges for the eye and the beard edge. So: **at 3-5 m these are convincingly people; from about
2 m in they read as painted carved figures.** Better than cp11's "painted wooden mannequins at 3 m" -
the failure distance moved from 3 m to about 2 m - but not yet "legit real people" at conversation range.

**What the frames say is still wrong** (each seen, not inferred):
- **Hard shards where the headcloth meets the face and where the beard ends.** The beard and hair shells
  are offset copies of the head, and their boundary is a hard mask edge, so at 2 m the silhouette is a
  saw-tooth. This is the single most mannequin-like thing in the frames.
- **Flat skin shading at close range.** The face carries no visible pore or subsurface break-up at 2 m;
  it reads as matte paint on a plane.
- **Eyes read as dark smears** at 2-4 m: the sculpted eyeball, iris and lash line do not survive the
  resolution they are seen at.
- **The far crowd field is still V3 VAT statues** - untouched by this pass, as recorded above. The
  distant figures along the wall are those, not the six new bodies.
- The refine itself cannot be judged from these frames: at 4-5 m the young woman's jaw and lips are a
  handful of pixels. The refine was judged offline, in the six-face strip and the 2x crops, which is the
  honest place to judge it.

**Next, in the order I would do it:** break the beard/hair shell boundary with a soft alpha or a
strand-level fringe instead of a hard mask edge; give the skin master a visible close-range pore normal;
and re-bake the crowd VAT from the V4 meshes so the far field stops being statues.
