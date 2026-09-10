# Herodian ashlar V5 — sources, and what is measured vs authored

V5 is not a new design. It is V4 (`Scripts/create_herodian_ashlar_v4.py`, whose research and layout are
unchanged and still authoritative — see `../HerodianAshlarV4/sources.md`) with three defects corrected,
each of which was diagnosed from a frame rather than from taste.

The frame: `SourceAssets/visual-review/cp05b-02-herodian-ashlar-inner-east-gate-jamb-walkingheight.png`,
4 m from the inner eastern gate wall jamb at eye height, the only walking-height photograph of the wall
that exists. Its control is `cp05b-01-azarah-facing-heichal-spawn.png`, where the approved Jerusalem
paving and the wall appear in ONE frame under ONE light and the paving reads as stone while the wall
does not.

## The measurement that drove every change

`Scripts/measure_stone_grain.py`, both albedos box-downsampled to a common 2.5 px/cm (which is what a
mip does, and without which any high-frequency number is meaningless — the two images are authored at
different px/cm):

| | V4 wall | approved paving | V5 wall |
|---|---|---|---|
| mean sRGB | 0.747 / 0.652 / 0.531 | 0.745 / 0.724 / 0.697 | 0.752 / 0.706 / 0.666 |
| G/R | 0.874 | 0.971 | **0.939** |
| B/R | **0.712** | 0.935 | **0.885** |
| luminance std | 0.062 | 0.122 | **0.098** |
| \|laplacian\| mean | 0.0175 | 0.1367 | 0.0208 |

HONESTY ON THE LAST ROW. An earlier reading of 0.0075 for V4 against 0.1367 for the paving — an
apparent 18x — was taken at each image's NATIVE px/cm and is not a fair comparison; that is exactly the
error `Scripts/measure_stone_grain.py` was written to remove. Matched at 2.5 px/cm the honest V4 gap is
7.8x, and **V5 closes almost none of it: 0.0175 -> 0.0208, still 6.6x below the paving.**

That gap is real and it is structural. A 1-texel laplacian at 2.5 px/cm measures features around
0.4 cm, and the paving is a photograph, so most of its number is pixel-scale photographic tooth. V5's
grit sits at 1.95 and 5.4 cm because that is the finest band that survives the mip actually sampled at
4 m — anything finer averages away before it reaches the screen, which is precisely what happened to
V4's sub-1.2 cm band. Adding per-pixel noise would raise this number without changing the image at 4 m
and would shimmer in motion, so it was NOT done. The number that should move is luminance std, the
structural mid-band contrast, and it moved 0.062 -> 0.098 against the paving's 0.122.

Whether that is enough is a question for the frame, not for this table.

## 1. Colour — CORRECTION OF A CALIBRATION ERROR, not a taste change

V4's palette was calibrated on `SourceAssets/kotel-detail/PhotoSurfaceV1/kotel-wall-cleaned.png`, whose
own PROVENANCE.md states it is an AI-cleaned photo derivative **with lighting partly baked in**. Warm
afternoon sunlight was therefore baked into the albedo and then lit by warm sunlight again in the
engine — the wall is doubly warm, which is why it reads orange next to paving of the same luminance.

Meleke (מלכה), the stone of the Herodian courses and of the Jerusalem stone ordinance, is a pale
cream to light honey. V5 raises B/R from 0.712 to 0.885 and G/R from 0.874 to 0.939 at unchanged
luminance (mean R 0.747 -> 0.752), landing slightly warmer than the paving (0.971 / 0.935) — which is correct: a limestone wall
is warmer than a grey-cream paver, but not orange.

MEASURED: the hue target range for meleke and the paving's own numbers.
AUTHORED: the exact base values, chosen to land the post-weathering mean on that target.

## 2. Micro-grain — COPIED FROM THE PAVING, NOT INVENTED

`M_JerusalemFloorSlabs_500cm` (`Scripts/release_jerusalem_floor_slabs.py:113-131`) is seven nodes: one
world-XY UV, one albedo sample, constant roughness 0.8, constant metallic 0. **It has no normal map at
all.** Its entire rock read lives in the albedo, and it is COARSER than the wall (2.5 px/cm against
6.83) while carrying 2x the luminance spread and, at 0.4 cm, 7.8x the local contrast. So the
mechanism to copy is the albedo.

V4's finest noise band sat below 1.2 cm. At 4 m the mip actually sampled is mip 2 (0.586 cm/texel), so
that band averaged to nothing before it reached the screen; what survived was the 5-20 cm mottle at
±5.5 %, which is exactly the smooth blotchy plaster look in the frame. V5 adds:

* a grit/pitting term in the **1.5-5.5 cm band**, the band that survives that mip;
* a pore field with **power-law radii** (very many tiny, very few large) and **patchy clustering** — a
  uniform-radius even scatter, which is what a first attempt produced, reads as aerated concrete, not
  stone;
* roughness raised from a glossy 0.57 median to 0.78, i.e. into the approved paving's 0.8 neighbourhood.

MEASURED: the paving's contrast statistics and the mip actually selected at 4 m.
AUTHORED: the grit amplitudes, pore density, size exponent and patch scale.

## 3. The boss — WHY IT READ AS ENGRAVED, AND WHAT ACTUALLY FIXES IT

A normal map bends the shading normal. It cannot change a silhouette and it cannot self-shadow at a
grazing angle, which is how an eye tells raised from incised. So on this wall the boss can only be sold
by shading gradients that **survive mipping** — and V4's did not:

* V4 boss-edge bevel 0.40 cm = 2.7 texels at mip 0, **under one texel at mip 2**. Its normal deviation
  was near-vertical (p50 0.968) but it occupied **1.04 % of the tile**. A sub-texel near-vertical ramp
  mips to a flat grey line. That is precisely the "clean incised frame" in the frame.
* V4 boss face was a mathematical plane (dish 0.06 cm), so margin and boss had identical normals and
  the only cue between them was that vanishing ramp.
* V4 AO median was 0.99 — half the tile had no occlusion at all, so nothing darkened the recessed
  margin either.

V5:

| | V4 | V5 | basis |
|---|---|---|---|
| boss proud | 1.4–2.0 cm | 3.2–4.6 cm | brief's 2–5 cm for ashlar; AUTHORED above the 6–14 mm measured on Western Wall blocks, as V4 already did for the course setback |
| boss-edge bevel | 0.40 cm | 1.90 cm | AUTHORED. 3.2 texels at mip 2, still 1.6 at mip 3. Weathered 2000-year arrises really are rounded over |
| joint arris | 0.26 cm | 0.55 cm | same argument |
| boss crown | −0.06 cm (dished) | +0.55 cm (domed) | a wide, gentle dome is a low-frequency gradient that mips CANNOT destroy; real bosses bulge |
| cavity AO gain / floor | 0.70 / 0.52 | 0.95 / 0.42 | light-angle-independent cue that the margin is recessed |
| bevel share of tile | 1.04 % | **4.91 %** | the number that matters |

## What was considered and NOT done, and why

* **Per-block geometry.** Not available. `SM_0138_architecture_Inner_eastern_gate_wall_jamb_1` is one
  box: 8 vertices, 12 triangles, `uvLayers: []` (`SourceAssets/architecture-manifest.json`), and the
  whole 2,633-mesh measured-architecture set averages 20 verts. Nothing is instanced per block; the
  ashlar exists only in the triplanar projection, and even the Blender arris bevel was excluded from
  export. Real bosses would mean building a HISM ashlar system from scratch.
* **Parallax / POM / Nanite displacement.** All need a height input on `M_PBR_Tiled`, which is a
  protected asset, so any of them means a NEW master material. That is a second, riskier change; the
  in-frame control says the albedo does most of the work, and one variable at a time is how this frame
  gets read honestly. Recorded as the next candidate.
* **Anti-repetition.** The 300 cm repeat is real and now photographed, but the anti-repeat pass was
  reverted the same night for dropping detail 3-4 mips on Nanite meshes. Stacking it on top of a full
  texture re-authoring would make the after-frame unreadable. Separate pass.

## Unchanged from V4, deliberately

TilingCm 300.0 (so course lines keep falling on the same world-Z levels on every wall and no other pass
has to be re-derived), the block layout and course schedule, the drafted-margin geometry rules, the
weathering and biological model, the joint treatment, and every instance scalar and the Tint — V5 sets
**only** the three texture parameters. `M_PBR_Tiled`, `MI_PBR_LimestoneAshlar` and `MI_PBR_LimestoneTrim`
are not touched, and no map is opened or saved.

---

## THE VERDICT FROM THE FRAME (cp11c, 10 Sep)

Cooked build `C:\Mikdash\Builds\Checkpoint-cp11c-20260910T085609Z` (`checkpoint_playable`), captured by
`Scripts/capture_frame_ashlar.ps1` from the two cp05b cameras. Receipt
`SourceAssets/visual-review/frame-ashlar-cp11c.json`. Compare:

* `cp11c-02-...walkingheight.png` against `cp05b-02-...walkingheight.png`
* `cp11c-01-azarah-facing-heichal-spawn.png` against `cp05b-01-azarah-facing-heichal-spawn.png`

**WON, and not marginally.**

1. **The boss reads as RAISED.** Every block now carries a lit chamfer along its upper drafted margin
   and a shadowed one along the lower, and the margin reads as a distinct recessed plane rather than a
   scribed line. The before-frame's hairline rectangle is gone. This is the defect the pass existed to
   fix and the frame settles it. Width beat depth: the fix was the 0.4 → 1.9 cm ramp, not the extra
   centimetres of projection.
2. **It reads as rock, not render.** The block faces are mottled and pitted. The before-frame at 1:1 is
   glassy-smooth; this is not.
3. **The orange is gone.** In frame 01 the walls, the twelve steps and the approved paving now sit in
   one stone family under the same light. Before, the wall was a saturated orange-tan against pale
   grey-cream paving and the mismatch was the first thing the eye found.

**STILL WRONG — stated plainly.**

1. **The 300 cm repeat is untouched and plainly visible.** Identical blotch patterns recur along every
   course. Declared out of scope for this pass and it is exactly as visible as before.
2. **The grain is cloudy, not toothy.** It reads closer to travertine or a fine weathered concrete than
   to crisp meleke. This is the laplacian gap in the table above, unhidden: the mid-band (1.5-5 cm)
   contrast is now there, the sub-centimetre tooth is not, and it cannot be added in a texture without
   shimmering in motion.
3. **The wall is still warmer than the paving in-frame.** Better by a long way, in the same family, not
   matched — a sandy cream against the paving's cooler grey-cream.
4. **The drafted margin edges toward "precast panel"** on the larger blocks, because the chamfer that
   makes the boss read is wide. That is the trade and it was worth making.

**A COURSE CORRECTION INSIDE THE PASS.** The first cooked attempt (`cp11b`, frames kept alongside) fixed
the boss, the grain and the colour, and introduced a NEW loudest defect: chocolate-brown blocks beside
cream ones, reading as patchwork rather than one quarry. That came from V4's per-block `weathering`
(0.35-1.0) and `weather_dark` 0.150 becoming far more visible once the base was paler. cp11c halves
them (0.20-0.62 / 0.085), cuts `value_jitter` 0.125 → 0.075 and `bio_amount` 0.24 → 0.12, and raises
green so the taupe moves toward cream-honey (G/R 0.939 → 0.951). Both cooked frames are kept so the
correction is auditable.

**COOKED-BUILD FLAG CHECK.** `frame-ashlar-cp11c.json → ashlarFallback` is empty: no LogMaterial warning
names any Herodian, Limestone or `M_PBR_Tiled` asset, so nothing on this path fell back to the default
material. The three `MI_SanctuaryV2_Gold*` Nanite warnings in that log are pre-existing and belong to
another pass; they are unchanged by this one.
