# cp26 review: full recook, 15 Sep 2026 (22:40 UTC)

Reviewer: Claude (frames read by eye plus measurements). Review only: no maps or assets were changed and nothing was committed.

## Verdict

**Yes, cp26 is the build Shmuel should open.** It supersedes cp24 and every patched test copy
(roofruntime01, contextpatch01, edgecollision01).

- It is the first single build that carries all of Codex's runtime fixes plus the saved horizontal-coursing
  materials.
- Each fix was confirmed in real GPU frames or native probes on this archive, and no fix regressed.
- **It is not a production-quality build.** The illusion still breaks badly in the two Kotel views (K1 and
  K2), with the blob trees, and on the retaining walls, which read as brick rather than Herodian ashlar.
  See the defect list.

Archive: `C:\Mikdash\Builds\Checkpoint-cp26-20260915T214343Z`
Launcher: `Windows\MikdashCourtyardV3.exe`

### Build facts

- **Receipt:** `checkpoint_playable`, exit 0.
- **Build step:** UBT reported "Target is up to date"; 0 actions.
- **Game child:** SHA256 `5cc71b343ee48fa89903738a0c63e0d7eac6e6f3fc394ff93e3f6380eb920072`, written
  15 Sep 19:57 UTC.
  - This is NOT the edgecollision01 child `9860531e...`. It is a later compile of the Game target.
  - All the probes below ran on this exact child.
- **Cook:** FULL, not iterative. 8,857 of 8,864 packages cooked; 0 errors and 1 warning (a DNS lookup,
  harmless).
  - The three coursing masters compiled fresh shadermaps during the cook.
  - Cook commandlet peak: 7.35 GB physical, 12.4 GB virtual.
- **Smoke test:** the window opened in 18 s; working set 3.7 GB.
- **Source maps:** Candidate48 and Main hashes unchanged across the cook. All probe receipts report
  `mapsUnchanged=true`.

### Memory headroom

Measured with `\Memory\Committed Bytes` against `\Memory\Commit Limit`.

- **Before captures:** 13.65 of 52.07 GiB committed (38.4 GiB free).
- **Worst point:** 15.54 GiB committed.
- **GPU four-state probe:** 7.40 GiB private peak, with at least 28.96 GiB commit still free.
- **McAfee `mc-fw-host`:** 0.32–0.35 GiB private. The leak has not regrown yet; it held about 16 GB before
  the reboot.

## Fix checklist

| # | Item | Result | Evidence |
|---|------|--------|----------|
| 1 | Floating legacy roof tanks/panels gone in Yechezkel | **PASS** | `city-facade/cp26-A1-west-gate-approach-into-old-city.png`: clean sky. Before: `cfafter-cp24-A1-...png` had about 15 floating tank/panel pairs. `cp26-R1-roof-overview-yechezkel.png`: the hidden-building zone is open ground with no orphan equipment. |
| 2 | Roof equipment returns in Modern/Overlay | **PASS** | `city-facade/cp26-R1-roof-overview-modern.png` and `cp26-R1-roof-overview-overlay.png`: restored blocks carry tanks, panels and domes. The A1 ground-level Modern/Overlay frames land inside a restored alley and cannot show roofs, as Codex noted. From this camera the R1 Modern and Overlay frames look identical. |
| 3 | K2 ground opening / mirrored band closed | **PASS** (with new visual defects, D3) | `city-facade/cp26-K2-kotel-upper-deck-facing-jewish-quarter.png` shows a stone retaining face where `cfafter-cp24-K2-...png` showed the mirrored sky/city band. Native four-state probe `context-review/KotelCutClosureV1/runtime-20260915T221846377Z.json` passed with exit 0: phases Modern, Yechezkel, Overlay, Modern-again, each `passed`. Deck and closure transform error 0; closure visible in Modern/Overlay (phase0/2/3 PNGs) and hidden in Yechezkel (phase1). |
| 4 | Kotel edge collision | **PASS** (one lane, NullRHI) | `KotelCutClosureV1/edge-20260915T222023385Z.json`: `blocked-retaining-edge`, initial floor validated, 4 blocking sweeps on the closure body, final feet -982.4 cm grounded, minimum feet -982.4. Collision mode 1, policy `pawn-only-query-v1`. Not whole-perimeter acceptance. |
| 5 | Kotel stair route (11 Sep fixes) | **PASS** | `KotelCutClosureV1/stair-20260915T222124896Z.json`: waypoints 0,1,2 reached in 9.99 s, `stuckEvents=0`, grounded on `SM_PlazaV1_DeckTile` at feet -982.4. Longest fall 26.4 cm; 1 falling sample out of 1,504. |
| 6 | No rod across photo-mode frames | **PASS** | No rod in any of the 11 city-facade frames, 7 precinct frames or 8 probe frames. The rod was present in cp24 K1/K2, `roofruntime02-R1-*`, `cp20b-P3` and faintly in `cp25-P3`. |
| 7 | Buildings show horizontal courses | **PASS** | `cp26-K2` and `cp26-K1` building faces now course horizontally; in `cfafter-cp24-K2/K1` they ran vertically. `cp26-A1` is horizontal too. |
| 8 | City wall shows horizontal courses | **PASS** | Rendered at Codex's exact CityWall A/B camera (`-78637.449 42766.199 2191.915`, P10 Y1.098) through `Test-KotelClosureRuntime.ps1 -CameraBugItGo`. `KotelCutClosureV1/runtime-20260915T223438036Z-phase0.png` shows horizontal courses. Codex's unpatched cp24 A (`runtime-20260915T180109788Z-phase0.png`) was vertical; patched B (`...180340505Z-phase0.png`) was horizontal. This probe's native state passed. |
| 9 | Plaza retaining-wall macro V6e present | **PRESENT, but not new** | cp26 matches cp25 frame for frame: mean abs diff 0.77 (P2), 0.83 (P3), 0.77 (P4), 0.74 (P5), 0.74 (02), 0.91 (07) per 255. That is about the 0.58/255 repeatability floor, with <0.2 % of pixels over 8. So V6e already shipped in cp25 on 11 Sep. cp26 changes nothing on the retaining faces. P1 differs by 1.73/255, from sky and clouds. |

Frame time (1600x900 windowed, static camera, last half of 700 frames):

- **Median:** 17.8–19.6 ms for most views; D1 23.6 ms (p90 28.9).
- **Peak working set:** about 4.1 GB.

Source: `city-facade/city-facade-frames-cp26.json`.

## Plaza retaining walls: Western Wall / cp20b / cp26

- **Sheets:**
  - `SourceAssets/enclosure-review/PrecinctMacroV1/cp26-P3-westernwall-cp20b-cp26.png` (three panels)
  - `cp26-P3-stone-scale-vs-westernwall.png`
  - `cp26-P4-crossover-cp20b-cp26.png` and `cp26-P5-crossover-cp20b-cp26.png`
- **Frames:** `SourceAssets/visual-review/cp26-{P1,P2,P3,P4,P5,02,07}-*.png`
- **Receipt:** `frame-precinct-macro-cp26.json`. 7 of 7 captured on the first attempt, with no material
  warnings or fallbacks.
- **Measurements:** `accept-cp26.json`, from `Scripts/accept_precinct_cp25.py cp26 cp20b V6e`.
  - The script is unchanged; it takes the label as an argument.
  - It needs a 64-bit Python: the 32-bit default hits a MemoryError, so run it with Anaconda plus its
    `Library\bin` on PATH.
  - For reference, `accept-cp25.json` was also produced; its values are the same within noise.

The table uses the P3 east face at 60 m, rectified to 3.14 cm/px.

| Metric | Western Wall | cp20b | cp26 (close layout) | cp26 (own V6 stones) |
|---|---|---|---|---|
| stone-tone log std | 0.0838 | 0.0914 | 0.0997 | 0.0996 |
| 5–95 % ratio | 1.254 | 1.322 | 1.375 | 1.363 |
| neighbour contrast | 0.0454 | 0.0289 | 0.0483 | 0.0513 |
| bed-joint dip | 0.1444 | 0.0810 | **0.1899** | – |
| course-height CV (visible beds) | 0.194 | 0.248 | **0.542** | – |
| courses >1.5x median (visible beds) | 0.066 | 0.067 | **0.173** | – |
| intra-stone log std | 0.1018 | 0.035 | 0.0914 | 0.0903 |
| hp autocorr @300 cm (repeat) | – | -0.0552 | -0.0294 | – |

Other measurements:

- **Visible course height:** median 101.5 cm in cp26, against 103.6 cm on the Western Wall. The histogram
  has courses at 90/100/110 cm plus 3x 200, 3x 210 and 3x 300 cm. The Western Wall p95 is 1.54x the median.
- **P2 south face at 70 m:** bed-joint dip 0.174 in cp26 against 0.073 in cp20b; autocorr at 300 cm -0.076
  against -0.186.
- **Crossover ghost ratio** (dip at the beds V6 merged ÷ dip at the beds it kept; 0 means invisible):
  - P4 at 22 m: 1.066 (cp20bx control 1.104).
  - P5 at 35 m: 0.976 (control 1.105).
  - The merged beds are fully visible up close.
- **No regression:** 02 jamb 0.0026 and 07 plaza 0.0088, against noise floors of 0.0028 and 0.0057. The
  07 value is slightly over its floor.

**Honest verdict: it does not read as Herodian masonry. At 60 m it reads as brick / tile running bond.**

What improved over cp20b:

- Stone-to-stone tone spread, neighbour contrast and intra-stone texture are now close to the Western Wall,
  so the face is no longer a flat grey card.

What is wrong:

1. **Joints are 1.3x too strong and too uniform.** Every stone is a crisp rectangle with a dark outline.
   There is no marginal drafting, no chipped arris and no weathered joint.
2. **Course heights are almost 3x too irregular.** Isolated 2–3 m bands of big blocks sit in a field of
   uniform 1 m brick-like courses. On the real wall the tall courses are a gradual rhythm.
3. **The merged beds still show.** At 22–35 m the ghost ratio is about 1, so a "tall course" still shows
   its 1 m joints. P4 at 22 m is plainly a brick wall.
4. **Tiling shows.** Weathering blotches and moss decals repeat on a visible grid (P3, P5).
5. **The colour is wrong.** The face is olive-brown; the Western Wall is pale cream limestone (see the
   three-panel sheet).

## New and remaining visible defects, ranked by how badly they break the illusion

1. **D1: untextured white stepped slab over the alley.** A giant flat-white, material-less staircase or ramp
   underside spans the frame overhead. `city-facade/cp26-K1-kotel-plaza-walking-facing-jewish-quarter.png`,
   upper left. Present since cp24; unchanged.
2. **D2: Jewish Quarter buildings float above the hillside.** Box undersides overhang the slope by metres,
   in the hero Kotel view. `cp26-K2-...png`, top half. This is the known OldCityFoundationV1 diagnosis
   (infill1200/1210/1181/1183); unchanged.
3. **D3: the new Kotel closure reads as CG blockout.** `cp26-K2` (crops at 3840 px, left and right of
   y 950–1600).
   - The face is two planes at different depths, with a hard jog near x≈1150 of 3840.
   - The recessed left segment has regular dark vertical shadow stripes every few metres.
   - A tilted strip of plaza paving with a Z-shaped notch lies on the sand slope above the wall top.
   - The grey panelled stone matches neither the Kotel nor the Old City limestone.
   - Above the wall is bare sand with no retaining detail up to the floating houses.
4. **D4: blob trees clip through the steps.** Low-poly two-sphere blob trees appear in `cp26-A1` (hero
   foreground) and `cp26-07`. In 07 the blob trees intersect the north-gate stair, and the stepped
   retaining edge shows a notch where they meet.
5. **D5: retaining faces read as brick.** See the plaza section. `cp26-P3`, `cp26-P4` and `cp26-P5`.
6. **D6: stretched texture bands and a stone-scale mismatch.**
   - Horizontal smeared texture bands appear at the batter ledges: `cp26-P2` at y≈450 and 715 of 1125,
     `cp26-P4` at y≈575, `cp26-P5` at y≈235, 570 and 940.
   - `cp26-P2` also has a stepped top edge where the upper-left band has smaller, darker stones, a
     stone-scale mismatch.
7. **D7: the temple platform reads as a grey slab.** From 1–2 km it is a flat grey slab with sub-pixel
   faces. `city-facade/cp26-P1-...png` and `cp26-D1-...png`. D1 also has a white horizon glare band on the
   right.
8. **D8: the south approach looks unfinished.** The city is plain boxes on bare dune-textured terrain.
   Roads are flat dark-grey ribbons with no kerbs or texture, and black specks mark roof clutter.
   `city-facade/cp26-A2-south-approach-flight-facing-silwan.png`.
9. **D9: the city wall is flat.** It is a uniform brown with light painted joints, no relief, and a visible
   tile repeat. `KotelCutClosureV1/runtime-20260915T223438036Z-phase0.png`. Coursing is correct now; the
   surface is not.
10. **D10: the Herodian jamb close-up is soft.** The mottling is low-resolution and blurry, and every stone
    has the same panel drafting, so it looks like wallpaper. `cp26-02-...png`. Unchanged since cp20b.
11. **Observation, not yet shown to be player-facing: Yechezkel from the Kotel deck.**
    - Switching to Yechezkel from the Kotel deck camera shows a dark curved brick vault over sand. The
      camera is below the precinct surface: `KotelCutClosureV1/runtime-20260915T221846377Z-phase1.png`.
    - Codex's earlier probes show the same, so this is not a cp26 regression.
    - Whether a real player is relocated on the switch is untested.

Capture note: the A1 Modern/Overlay ground cameras spawn inside a restored alley. That comes from the
capture camera, not the game.

## Commands run on cp26

- `Scripts/capture_city_facade.ps1 -Archive <cp26> -Label cp26 -IncludeRoofStateViews` → 11/11
- `Scripts/capture_frame_precinct_macro.ps1 -Archive <cp26> -Label cp26 -Views P1,P2,P3,P4,P5,02,07` → 7/7
- `Scripts/Test-KotelClosureRuntime.ps1 -Archive <cp26> -ExpectedChildSha256 5cc71b34...` → passed
- `Scripts/Test-KotelEdgeRuntime.ps1 -Archive <cp26> -ExpectedChildSha256 5cc71b34...` → blocked-retaining-edge
- `Scripts/Test-KotelStairRuntime.ps1 -Archive <cp26> -ExpectedChildSha256 5cc71b34...` → passed-native-stair-route
- `Scripts/Test-KotelClosureRuntime.ps1 ... -CameraBugItGo '-78637.449 42766.199 2191.915 10 1.098257 0'` → CityWall camera, passed
- `Scripts/accept_precinct_cp25.py cp26 cp20b V6e` (also `cp25 cp20b V6e`)

All runs were serial, one engine at a time, launched from a detached runner.
