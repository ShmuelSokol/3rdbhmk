# The Kohen Gadol in the eight golden garments (KG-V1, cp18)

2026-09-11. Not committed. Frames: see "Acceptance frames" (packaged cp18). Offline evidence:
`SourceAssets/characters-review/KohenGadolV1/`.

## Which garments, and why these

**The golden set.** The scene is the ordinary-day lamp service (`service_scenario` ORDINARY_DAY). Shmuel's book,
PDF p. 350 (printed p. 245), figure 2 is captioned "Kohen Gadol wearing 8 golden garments" and figure 3 "Kohen
Gadol on Yom Kippur with 4 white garments". Rambam Klei HaMikdash 8:1-3 says the same: eight golden garments,
with the four white ones reserved for Yom Kippur. Klei HaMikdash 5:11 has him walking into the Heikhal in the ephod.
`release_kohen_gadol_v1.py` refuses to apply the body to any other scenario.

**What the model takes from where.** The full table is in `runtime-review/kohen-service/sources.md` §8. In short:
- **From the book's figure 2:**
  - a white checkered ketonet with sleeves, to just above the feet;
  - a sleeveless blue me'il to the lower shin (about 18 cm up);
  - the red woven ephod behind and at the sides, from the belt to about 40 cm up, open at the front;
  - the belt knotted at the front with two hanging ends;
  - the choshen above the belt, 4 x 3 stones, with the stone colours sampled off the figure, on gold chains to
    the shoulders;
  - a wound mitznefet, the tzitz on the forehead, and a cord up its front;
  - bare feet.
- **From Rambam (Klei HaMikdash ch. 8-9, read on Sefaria):**
  - the ketonet hem slightly above the heel, and sleeves to the wrist (8:15);
  - the tzitz two fingerbreadths high, ear to ear (9:1);
  - 72 gold bells and 72 closed pomegranates of techelet, argaman and tola'at shani, alternating on the hem (9:4);
  - the choshen a zeret square (9:6; drawn 23 cm);
  - gold in the woven thread (9:5).
- **Authored:** every colour value not sampled from the book, the checker size, the ephod's woven pattern, the
  mitznefet's proportions, all clearance offsets, and the face.
- **Not modelled:** the tzitz inscription (below mesh resolution at 2 m), the tribe engravings, and the avnet and
  michnasayim (the book labels both "under the garments").
- **Open (R):**
  - Rambam 9:9 has the ephod "to the feet", while the book draws it ending about 40 cm up. The model follows the
    book.
  - The avnet's form, the choshen stone identities, and whether the me'il is closed or open at the sides.

## The clipping, measured

`Scripts/measure_kohen_garment_clearance.py` poses each body with the SHIPPED clips (glTF LINEAR) and measures
every leg vertex (shin and foot) against the robe tube:
- It counts a vertex only when two independent tests both say it is outside: closed-volume ray parity, and signed
  distance to the nearest posed triangle.
- It also requires the vertex to sit above the local posed hem. A foot below the hem is simply visible.
- On the single-layer stand-in, the two tests agree to the millimetre.

Sampling: the walk over one full cycle at 120 Hz (every key of the 60 fps clip, twice), the tend clip at 30 Hz (every key of the 30 fps clip), the idle at 30 Hz. The stand-in was also measured at 240 / 60 Hz and gives identical maxima (walk 23.85 cm, tend 2.45 cm).

| clip | stand-in (V3_Pilgrim_Man_Standard) | KG-V1 |
|---|---|---|
| walk, leg outside robe | **23.85 cm** (FootL at heel strike, 51 cm ahead, 15 cm up); 288 / 288 samples clip | **0.00 cm**; 0 / 144 samples clip (120 Hz) |
| tend, leg outside robe | **2.45 cm**; 451 / 601 samples | **0.00 cm**; 0 / 301 samples clip (30 Hz) |
| idle | 0 | **0.00 cm**; 0 / 97 samples clip (30 Hz) |
| ketonet outside me'il (KG only) | n/a | 0.37 cm max (walk 0.37, tend 0.00, idle 0.00; worst at walk t 0.29 s, back of the swing knee, 9 vertices) |

Files: `clearance-BEFORE-standin.json` (and `-walk-half` / `-tend-half`), `clearance-AFTER-kohen-gadol-v1.json` (merged from the per-clip files). Offline before/after renders:
`previews/before-after-walk-t0.5167-side.png`, `previews/before-after-walk-t1.0500-side.png`.

**Why the stand-in clipped.** Its robe followed `skirt_r/_l`, which the walk drives at 0.45 of the hip-ankle angle.

**What fixed it.** No bone was added and no clip was changed; the 72 cm stride stands. The fix is entirely in the
mesh's skin weights. Each lower garment is one weight field:
- pelvis at the hip line, handing to the same-side thigh by z 74 and to the calf below the knee;
- below z 21, the same calf/foot split the shin itself uses;
- a left/right split band 14 cm wide at the thigh and 6 cm at the hem.

The 6 cm hem band was chosen by measurement. At the worst frame, the swing leg adducts past the stance shin. The leg
sat 0.84 cm outside with a 2.2 cm band, 0.25 cm with 3.6, 0.03 cm with 4.4, and 0 with 6.0.

Other rules:
- The outer layers take the weights of the ketonet point beneath them, and share its ring heights and angles.
- The hem is open, because a cap became a membrane between the legs.
- The ketonet is ankle length: the hem sits 4.5 cm up at the back and 7.6 cm at the front, per Rambam 8:15.

## Engine (full guard pattern; receipts in this folder)

- **Import:**
  - `kohen-gadol-import-SK_KohenGadol_V1-20260911T054541375011Z.json`.
  - `/Game/MikdashV3/Characters/KohenGadolV1/Mesh/SK_KohenGadol_V1` is on the EXISTING V3_Pilgrim_Man_Standard
    Skeleton, and the bone set is unchanged (compared as a set).
  - No skeleton and no animation was created.
  - 10 slots `KG_*` are assigned by name to `MI_KG_*_V1` after the import.
  - The master material `M_KohenGadol_Garment_V1` has `bUsedWithSkeletalMesh` set. It multiplies
    pow(VertexColor, 2.2): the skeletal build stores COLOR_0 as sRGB bytes, and GpuSkinVertexFactory reads them raw.
  - 317 protected files are unchanged: every resident body, clip and skeleton under PilgrimRigV3, plus both maps.
- **Re-import in place:**
  - `kohen-gadol-reimport-SK_KohenGadol_V1-20260911T064014415661Z.json`.
  - Final GLB `683354d4...`, same object path, so the maps needed no second edit.
  - Slots re-assigned and read back 10/10; bones unchanged; nothing protected changed.
- **Maps.** Only `configured_mesh` changes. `GarmentMaterialSlots` (Garment, Robe, Cloth, Body) name no slot on this
  mesh, so `ApplyGarment` paints nothing over it.
  - Candidate48 apply `4e699f8c -> e1bbf4ca`.
  - The revert was proven: `-> 1df7c016`, read back as Man_Standard.
  - Re-apply `-> 2ea59e9d`.
  - Main50 apply `b5107135 -> d2251f29`.
  - Every step checkpointed into `ReviewCheckpoints\KohenGadol-*`, reopened and read back; the other map and every
    protected file were unchanged.
  - To undo: `-KohenGadolRevert -KohenTarget=Candidate48|Main50`, then `-KohenGadolImportRevert`.
- **Cook:** `Checkpoint-Build.ps1 -Label cp18`, launched DETACHED through `Scripts/run_kohen_gadol_v1_engine.ps1`: `C:\Mikdash\Builds\Checkpoint-cp18-20260911T064141Z`, status `checkpoint_playable`, exit 0, smoke window after 18 s. The cooked Candidate48 map (`32c2c970...`, saved by another agent at 02:21 after this apply) and Main50 (`77825719...`) both still reference `SK_KohenGadol_V1` (2 references each, 0 to Man_Standard). Cook log and packaged runtime log: no "Default Material will be used" at all; the only KohenGadol lines are the actor's own lookup of the still-absent `MI_Garment_KohenGadolGold` fallback, which names no slot on this mesh and paints nothing.

## Acceptance frames (packaged cp18)

All from the packaged cp18 build, `-dumpmovie -benchmark -fps=10` (frame i = i/10 s of game time from
world start), Candidate48, 1920 x 1080. Movies under `SourceAssets/visual-review/movie-cp18-*`.

- **At 2 m while tending (the brief's view, `BugItGo -5255 60 1045 -6 108 0`):**
  `visual-review/cp18-kohen-gadol-tending-lamp1-2m-t44.8s.png` and `-crop.png`. His right hand is at the first lamp
  as it kindles. Seen from behind his left shoulder: the mitznefet with the tzitz's gold edge at the brow, the white
  beard, the techelet me'il, the red ephod strap and apron with its purple weave, and the checkered ketonet sleeve.
  Also `cp18-kohen-gadol-lamp1-lit-t46.0s-crop.png` (the lamp burning after his hand leaves),
  `cp18-kohen-gadol-kindling-sequence-sheet.png` (44.0-46.0 s) and `cp18-kohen-gadol-tend-approach-sheet.png`
  (33-42.5 s, full length on the step). Movie: 2247 frames (224.7 s).
- **From the front, the view that shows what makes him the Kohen Gadol (`BugItGo -5530 150 1090 -8 36 0`,
  west of the menorah looking east):** `cp18-kohen-gadol-front-at-menorah-t36.0s.png` and `-crop.png`. Visible:
  - the tzitz across his forehead under the mitznefet, with the techelet cord up its front;
  - the choshen, twelve stones in four rows of three, on gold chains to the shoulders;
  - the techelet me'il, the checkered sleeves, and the belt tails with the ephod at his sides.
  He is backlit by the Ulam doorway, so the colours read darker than in the tend view.
  `cp18-kohen-gadol-front-walk-in-sheet.png` (22-28 s) has him walking in toward the camera. Movie: 1427 frames.
- **Close three-quarter as he enters (`BugItGo -5060 30 1005 -6 84 0`):**
  `cp18-kohen-gadol-front-choshen-tzitz-t25.0s-crop.png` (tzitz, choshen, chains and shoham settings) and
  `cp18-kohen-gadol-walk-in-close-sheet.png` (25-29 s: walking to the stone and stepping up). Movie: 1021 frames.
  This camera sat about 2 m off his path and cuts him at the shin, so it does NOT show the hem at push-off.
- **Full length through push-off (`BugItGo -5000 -60 1050 -12 84 0`, about 3.1 m off his path):**
  `cp18-kohen-gadol-walk-full-stride-sheet.png` (26.0-27.0 s, every 0.2 s),
  `cp18-kohen-gadol-walk-full-pushoff-t26.5s-crop.png` and `cp18-kohen-gadol-walk-full-heelstrike-t27.0s-crop.png`.
  - At push-off the rear hem (white ketonet with the bell band) sweeps back along the floor over the trailing foot.
  - At heel strike the leading foot shows only below the front hem.
  - No bare shin shows through the robe in any frame. Movie: 1078 frames.

## Not done / honest limits

- **Not yet seen by Shmuel.** The book's figure 2 is the reference; every colour and proportion not sampled
  from it is authored (sources.md §8).
- **The after number is measured, not assumed.** The legs are at 0 through the walk, tend and idle clips. The
  ketonet shows through the me'il by at most 0.37 cm, at a fold behind the swing knee, a few centimetres below the
  ephod's lower edge. It is visible only from behind, mid-swing.
- **The lower robe at push-off spreads into a wide, flat train on the floor.** It reads as a heavy robe sweeping, but
  it is stiff and sheet-like rather than draping: linear skinning, no cloth simulation.
- **What the tend-view frame does not show.** The brief's 2 m tend camera stands behind his left shoulder, so the
  choshen and tzitz are not visible there. The front view is the frame that shows them, backlit by the Ulam doorway.
- **Not rendered:** the tzitz inscription and the tribe names; the ephod pattern is a vertex-colour weave.
- **Captures ran slow.** The box was loaded, so the movies dumped at about 2.5 frames per real second; the
  fixed-timestep -benchmark -fps=10 keeps game time exact.
- **Out of scope, still open:** Main50 was applied but not cooked or captured. The actor's status text still mentions
  the stand-in fallback (C++, not visible). No git commit was made.
