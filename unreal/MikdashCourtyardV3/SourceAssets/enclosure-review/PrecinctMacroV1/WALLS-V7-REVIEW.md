# walls07: the plaza retaining faces as Herodian masonry (V7g textures + V5 master) - BUILT AND MEASURED

Owner's standard: *"I want the temple stones used for wall wherever you are using stones to be the large
style stones used for the 2nd temple outer wall"*, at *"Warner Brothers style production"*.

Judged against `SourceAssets/kotel-detail/PhotoSurfaceV1/kotel-wall-cleaned.png` (the Western Wall) at
**matched cm/px**, with the **same code measuring the photo and the build** (`Scripts/measure_masonry.py`).

* **Three-panel sheet (Western Wall / cp26 / walls07):** `walls07-P3-westernwall-cp26-walls07.png`
* **22 m against the photo at the photo's own scale:** `walls07-P4-vs-westernwall-matched-1.59cmpx.png`
* **07 before/after:** `walls07-07-cp26-vs-walls07.png`
* Numbers: `accept-walls07.json`. Frames: `SourceAssets/visual-review/walls07-*.png` (7 of 7, first attempt,
  **no material warnings and no fallbacks**). Build: `C:\Mikdash\Builds\Checkpoint-walls07-20260916T010109Z`.

## 1. Honest verdict

**Closer to Herodian masonry than anything before it, and no longer brick - but not yet the Western Wall.**

What is now true, measured on the real frames:

* **The brick read is gone.** Course-height CV at 60 m is **0.201** against the photo's 0.192 (cp26: 0.121),
  and at 22 m 0.169 against 0.208 (cp26: 0.083). Courses vary gently with occasional master courses, and
  every batter ledge falls on a bed.
* **The crossover ghost is gone.** This was the single thing that made 22 m read as brick, and it is the
  clearest win in the pass:

  | ghost ratio (close-only beds / macro beds) | cp26 | walls07 |
  |---|---|---|
  | P4, 22 m | 0.548 | **0.156** |
  | P5, 35 m | 1.041 | **0.129** |
  | P3, 60 m | 1.371 | **0.116** |

* **The repeat lattice is gone.** Blotch repeat at 22 m **0.689 -> 0.283**, against the photo's own 0.288.
* **The colour is right.** At 22 m sRGB G/R **0.8746** and B/R **0.7069** against the photo's 0.8732 / 0.7057
  (cp26: 0.8401 / 0.6244). At 60 m 0.8795 / 0.6892 against 0.8735 / 0.7064.
* **The batter-ledge smear is gone**: the rolled 45 degree wash now carries the same coursing as the wall.
* **The 3 m wallpaper is gone from the aerial view**: P1 tile-3m band power **0.1348 -> 0.0059** (west face),
  0.0221 -> 0.0038 (south S1-S2), 0.1821 -> 0.1055 (south east-of-S2), with rawStd unchanged (0.0384 ->
  0.0388). The ledge rhythm is now the dominant large-scale structure (0.334 -> 0.448).

What is still wrong, and would be the next pass:

1. **Drafted margins do not measure as visible at 22 m.** Margin step / interior = **0.91** against the
   photo's 1.68 (bar >= 1.3). They are there in the geometry and you can see them on individual stones, but
   the face texture swamps them at that range.
2. **Bed joints are too deep at close range**: dip **0.306** at 22 m against the photo's 0.202 (ceiling
   0.253). At 60 m it is fine (0.181, ceiling 0.190).
3. **The faces read dirty.** The pitting is dark speckle rather than the photo's quiet, pale erosion - the
   "coral" weakness carried forward from the offline pass, now confirmed in frames. Intra-stone variation is
   correct in *amount* (22 m: 0.1338 vs the photo's 0.1319) but wrong in *character*.
4. **Intra-stone at 60 m is at the bottom of the band** (0.1004, floor 0.0925) and the face is greyer than
   the photo's honey.
5. **Tall-course fraction** at 60 m 0.042 against a 0.044 floor (photo 0.059).

## 2. Every metric beside the Western Wall's value

Photo and build measured by identical code at the same cm/px. Bars are the photo +-25 %.

### P4, 22 m (1.59 cm/px - the photo's own scale)

| metric | Western Wall | cp26 | walls07 | bar | verdict |
|---|---|---|---|---|---|
| course-height CV | 0.208 | 0.083 | 0.169 | 0.156-0.260 | pass |
| courses > 1.5x median | 0.065 | 0.006 | 0.096 | 0.049-0.081 | over |
| bed-joint dip | 0.2024 | 0.2145 | 0.3056 | 0.152-0.253 | **fail, too deep** |
| stone tone spread (detrended) | 0.0707 | 0.0629 | 0.0771 | 0.053-0.088 | pass |
| neighbour contrast | 0.0489 | 0.0603 | 0.0605 | 0.037-0.061 | pass (edge) |
| intra-stone log std | 0.1319 | 0.0651 | 0.1338 | 0.099-0.165 | pass |
| margin step / interior | 1.68 | 1.88 | 0.91 | >= 1.3 | **fail** |
| blotch repeat | 0.2883 | 0.6888 | 0.2831 | <= 0.44 | pass |
| sRGB G/R, B/R | 0.873 / 0.706 | 0.840 / 0.624 | 0.875 / 0.707 | +-10 % | pass |
| ghost ratio | - | 0.548 | **0.156** | -> 0 | pass |

### P3, 60 m (3.14 cm/px - the scale cp20b/cp25/cp26 were judged at)

| metric | Western Wall | cp26 | walls07 | bar | verdict |
|---|---|---|---|---|---|
| course-height CV | 0.192 | 0.121 | 0.201 | 0.144-0.240 | pass |
| courses > 1.5x median | 0.059 | 0.071 | 0.042 | 0.044-0.074 | just under |
| bed-joint dip | 0.1517 | 0.1900 | 0.1813 | 0.114-0.190 | pass (high) |
| stone tone spread (detrended) | 0.0724 | 0.0577 | 0.0696 | 0.054-0.091 | pass |
| neighbour contrast | 0.0490 | 0.0424 | 0.0497 | 0.037-0.061 | pass |
| intra-stone log std | 0.1233 | 0.0711 | 0.1004 | 0.092-0.154 | pass (low) |
| blotch repeat | 0.2840 | 0.2100 | 0.2003 | <= 0.44 | pass |
| sRGB G/R, B/R | 0.874 / 0.706 | 0.856 / 0.602 | 0.880 / 0.689 | +-10 % | pass |
| ghost ratio | - | 1.371 | **0.116** | -> 0 | pass |

P5 (35 m): CV 0.184, dip 0.249, intra 0.116, blotch 0.125, ghost **0.129**. P2 (70 m south face): CV 0.231,
dip 0.179, intra 0.115; its median course reads 129.6 cm against the photo's 100.8, and B/R runs blue
(0.797) - the south-face rectification is the least trustworthy of the four (cp26 read 140.4 cm on the same
view), so P2 is reported but not leaned on.

**Luminance is not a bar** and is reported as exposure-set: the game runs auto-exposure and the wall fills
the frame, so the face sits at luma ~0.46 in every build while the photo is 0.65. Reaching the photo's
luminance by albedo needs a ~1.9x multiplier (far albedo R ~ 0.99), which is unphysical and clips the tone
encoding - the ideal answer cannot pass such a bar, so hue carries it instead. Stone spread is detrended by a
local 6 m field for the same reason of fairness (the 60 m strip is 70 m tall and carries an aerial-perspective
gradient the 7 m photo band does not). Both corrections were made before any after-frame existed.

## 3. No regression on the shared material

`MI_PrecinctPlaza_Ashlar` is shared with other plaza surfaces **and** with `KotelClosureRuntime.cpp` and
`create_kotel_plaza.py`, so it was checked, not assumed.

* **02, the 4 m Herodian jamb (the control this pass must never touch): 0.00267, BELOW its 0.00281 noise
  floor - unchanged.**
* **07, plaza stone at walking range: 0.03354 against a 0.00572 floor - but that headline is contaminated.**
  cp26 was captured at 18:33 on 15 Sep; the residents (19:14), Old City (19:49) and trees (20:16) passes all
  landed afterwards. **52.6 % of the total difference energy is in vegetation/sky pixels** - the blob trees by
  the gate are gone in my frame and were never mine. Restricted to stone pixels the difference is 0.0253, and
  split by distance:
  * **foreground parapet (walking range, pure plaza stone): 0.0123**, about 2x the noise floor - small;
  * **mid and upper terraces: 0.0453** - this part *is* mine, the macro now reaching 5-30 m where it used to
    start at 12 m, and those terrace faces read darker and more speckled than before.
  Mean stone luminance is unchanged (-0.0032), so it is texture, not a brightness shift.

## 4. What shipped

* `M_PrecinctMacroV5_Triplanar` - new master, built to a new name; no existing master rebuilt in place.
  175 nodes, **core exactly 61, node for node with `M_PBR_Tiled`**, plus 10 weight-snap, 3 close-ARM-fade,
  43 relief and 18 close-fade nodes. Three things V4 could not do with scalars:
  1. **Triplanar weight snap** (w_z 0.90/0.96): anything steeper than ~30 degrees from horizontal takes the
     side projection only, which fixes the 45 degree ledge wash. The deck, ramps and stairs are unaffected.
  2. **Close ARM fade**: V4 faded the close albedo and normal but never the ARM, so the close tile's fixed
     1 m beds survived in AO under any macro layout - the ghost. AO now lerps to 1.0 and roughness to
     `FarRoughness` 0.763 on the same weight.
  3. The 14400 x 7200 cm macro period.
* `T_PrecinctMacro_ToneV7g` / `T_PrecinctMacro_ReliefV7g`, 8192 x 4096 over 14400 x 7200 cm (1.758 cm/px):
  own course layout on the ledge grid, drafted margins as geometry with hairline joints, no baked plants
  (cp26's 36 tufts were the "blotch grid"), calibrated colour grade (1.0, 1.073, 1.225).
* Fades: macro in by 12 m, close tile gone from vertical faces by 14 m, close fade-out pushed past 1 km so
  **no distance re-introduces a low mip of the close texture** - the far target stays the fixed
  `CloseAlbedoMean` vector, as the previous pass required.

Receipts: apply `precinct-macro-applyv5-V7g-20260916T005740078169Z.json` (0 illegal changes, 0 readback
mismatches, maps and named protected assets unchanged), verify
`precinct-macro-verify-20260916T010101719684Z.json` (`verified` in a fresh process, 175 expressions,
never_stream on all three macro textures, Nanite + ISM usage true). Revert:
`-PMRevert=<apply receipt>` restores the instance bytes from
`ReviewCheckpoints\PrecinctMacro-applyv5-20260916T005740078169Z`.

**The build contains no C++ of mine.** It was cooked `-UseExistingBinaries`; the staged child exe SHA256 is
`de6dc228c3526d1143dd3389e0a9ccdd56f2c048b5a8dd8d3d972bc42ad22d2b`, the same exe as the Kotel agent's
Checkpoint-kotel01 archive, i.e. the binaries built at 20:06-20:07 on 15 Sep containing that agent's Kotel
closure C++.

## 5. Two further variants were generated, measured, and NOT shipped

After the frames came back, V7L (tone-darkening of pits cut 0.20 -> 0.09) and V7M (0.14, prouder boss,
crisper 1.6 cm bevel) were generated and previewed through the light model, which is now calibrated twice -
against cp26 *and* against this build (at 22 m the build ran dip x1.11, intra x1.11, neighbour x0.93 and
margin ratio x0.96 versus the preview). Predicted for V7M at 22 m: dip 0.270 (still over the ceiling), intra
0.104, **margin ratio 0.56 - worse than the shipped 0.91** - and at 60 m intra 0.079, *below* the 0.092
floor. The crisper bevel backfires because at 1.758 cm/texel the boss edge is about one texel wide, so
sharpening it loses contrast instead of gaining it. Both were rejected rather than cooked: they would trade
two metrics to half-fix one. The next pass should buy margin visibility from a **finer macro texel** (or a
jointless detail normal at close range), not from a sharper bevel, and should lighten the pits' tone while
keeping their relief.

## 6. Reproduce

```
python Scripts/create_precinct_macro_v7.py --grade 1.0,1.073,1.225 --tag V7g
UnrealEditor-Cmd <uproject> -run=pythonscript -script=Scripts/release_precinct_macro.py -PMApplyV5=V7g \
  -PMSet="MacroFadeStartCm:500,MacroFadeLengthCm:700,CloseFadeStartCm:600,CloseFadeLengthCm:800,\
CloseFadeFarStrength:1.0,CloseFadeOutStartCm:100000,CloseFadeOutLengthCm:100000,\
MacroTileUCm:14400,MacroTileVCm:7200,FarRoughness:0.763" -unattended -nullrhi
UnrealEditor-Cmd ... -PMVerify=<apply receipt> -unattended -nullrhi
powershell -File Checkpoint-Build.ps1 -Label walls07 -UseExistingBinaries
powershell -File Scripts\capture_frame_precinct_macro.ps1 -Archive <archive> -Label walls07 -Views P1,P2,P3,P4,P5,02,07
python Scripts/accept_precinct_walls07.py walls07 cp26 V7g
```
