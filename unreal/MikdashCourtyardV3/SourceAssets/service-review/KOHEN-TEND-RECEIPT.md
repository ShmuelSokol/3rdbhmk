# The Kohen Gadol tends the lamps (cp14). The kindling does NOT yet read.

2026-09-11, packaged build `C:\Mikdash\Builds\Checkpoint-cp14-20260911T011747Z` (`checkpoint_playable`,
Candidate48 cooked at `3fb7b767…`). Not committed.

## Result, as seen in frames

**He visibly tends every lamp.** At each lamp station he leans in over the stone, lowers his head into the bowl
and reaches with his right hand to the lamp. The hand makes two slow circles in the bowl, which is the
clearing. He draws back to his left hand at the belt, where the kuz would be; no prop is modelled. He reaches
again and rolls the wrist (fresh wick and oil), holds at the wick, then straightens.
- `visual-review/cp14-kohen-tending-lamp1-2m-t45.0s.png`: the headline. Hand at the lamp, about 2 m from camera.
- `visual-review/cp14-kohen-tend-lamp1-sequence-sheet.png`: t 35.0-49.0 s. He stands, leans in, reaches,
  clears, reaches again, holds, and straightens.
- `visual-review/cp14-kohen-tend-lamps1-5-sheet.png`: the same reach at 45, 59, 73, 87 and 101 s, one lamp
  after another, and the stone empty at 115 s.
- Movie: `visual-review/movie-cp14-kohen-tend-close/`, 1178 frames, `-dumpmovie -benchmark -fps=10`
  (frame i = i/10 s of game time), `BugItGo -5255 60 1045 -6 108 0`.

**A viewer CANNOT see a lamp light.** `visual-review/cp14-lamp-flame-diff-NO-VISIBLE-KINDLING.png` shows
amplified differences of the lamp row: 35 s vs 115 s (five lamps should have been kindled in between) looks
the same as the 25 s vs 35 s control. No flame shape appears above any bowl in any frame, before or after his
station. What reads as "burning" is the gold lids lit by the STATIC point light
`RELEASE_SanctuaryV2_MenorahLamps` (-5367.1, 302.5, 1040). That light is not driven by the FX director, so
it glows from frame 0. cp12's "all seven flames already burn before he arrives" was very likely that same
highlight. Whether the director's 7 cm flame cards render at all on Candidate48 is UNPROVEN. That is the next
job: a real-RHI probe of `AMikdashFXDirector` (card visibility, world position against the lid crown,
`FlameLampMaterial`), then either make the flame read at this distance, or drive the static light from the
same lamp state. The lamp-state logic itself is proven only by the standalone tests below, not in a frame.

## What was built

1. **Geometry, measured and not guessed** (`tend-geometry-probe-20260911T003954381275Z.json`, read-only,
   both maps). Candidate48:
   - Top tread: X -5320.3..-5290 (30 cm deep, 16 cm risers). His feet are at X -5306.33, Z 936.0.
   - Lamp wicks (FX anchors): Z 1028.80 = 140.8 cm above the floor. Bowl tops are at 1032.33 = 144.3 cm,
     which is 18 tefachim at 8 cm.
   - The wick is 58.5 cm ahead of his feet and 92.8 cm above his soles.
   - His shoulder joint is 143 cm above his soles (Z 1079), so the wick is 50 cm below the shoulder, level
     with his hip joint.
   - Feet planted, an unleaned trunk would need 75 cm of reach against 56.4, so the clip leans 22° and
     twists 12° (peak shoulder-to-wrist 51.2 cm, never clamped).
2. **Clip.** `Scripts/pilgrim_tend_v1.py` + `Scripts/retend_pilgrim_v3.py`.
   - `A_Pilgrim_V3_TendLamp`: 10 s at 30 fps, forward-kinematic curves, leg and arm IK. Kindle at 7.6 s.
   - Off the written GLB: fingertips 4.94 cm from the wick at kindling, planted ankle drift 0.0011 cm.
   - Starts and ends on Idle t=0; geometry byte-identical to the shipped GLB.
   - Previews: `characters-review/PilgrimRigV3/tend-v1/previews/`.
3. **Import.** `Scripts/release_kohen_tend.py -KohenTendImport` put the clip in
   `/Game/MikdashV3/Characters/PilgrimRigV3/V3_Pilgrim_Man_Standard/TendV1/V3_Pilgrim_Man_Standard_TendLamp`.
   - The animation-only Interchange import binds to the existing skeleton.
   - `use30_hz_to_bake_bone_animation=False` with custom rate 30 gives 301 keys / 10.0 s.
   - The bone set is unchanged, compared as a set.
   - AnimPose in engine vs the offline FK: 0.0 cm. No protected asset changed.
   - Trap recorded: a lone clip is named after the FILE (first attempt refused before save; receipt
     `kohen-tend-import-…010033…`).
4. **C++** (UBT, editor + game both `Succeeded`):
   - `ServiceScheduleMath.h`: `LampBurning()`. A lamp is dark from sequence start until its own station's
     kindling moment, and burns until the next sequence; five lit and two dark while he waits outside
     (Temidin 3:17).
   - `AMikdashServiceActor`: `TendAnimation`, `TendClipStartSeconds` 1.2, `KindleAtClipSeconds` 7.6,
     `bLampsDarkUntilKindled`, `IsLampBurning`, `GetServiceLampLocation`. The clip plays once per Lamp
     station, and the kindle falls 8.8 s into the 14 s station.
   - `AMikdashFXDirector`: `bLampsFollowService`, `LampKindleRampSeconds` 0.8. Read-only polling that
     matches lamps by POSITION: its flame array runs south to north on Candidate48, the service counts
     north to south.
   - Tests: `ServiceScheduleMathTest` passes 100,330 checks with the new lamp-state cases;
     `Scripts/verify.py` is green (7/7, math 32/32).
   - `kohen-service/sources.md`: new SVC-LAMP-KINDLE entry.
5. **Maps** (full guard pattern; checkpoints in `ReviewCheckpoints\KohenTend-*`). Candidate48 first,
   `db6db904` → `e5805f92`; then Main50, `6f638fb3` → `a34f7286`.
   - Revert proven on Candidate48: read back empty, `b5fa4201`. Note that the reverted bytes are not
     identical to the pre-apply bytes, though the property is restored.
   - Re-apply: `3fb7b767`, the map that was cooked.
   - Scene snapshot unchanged except the kohen actor; the other map unchanged each time.

## Not done / defects recorded

- **Main50:** his stand point is 91 cm from the lamps, not 59, and its step stone has no trace collision.
  The clip is authored to Candidate48, so on Main50 his hand stops about 30 cm short. Main50 is neither
  cooked nor captured.
- **Garments (not fixed):**
  - Trailing shin through the robe: measured offline on the walk, the trailing shin sits up to 23 cm
    outside the tunic surface, 12-17 cm above the sole, at push-off. Likely cause: a 72 cm stride with
    skirt panels that follow only 0.45 of the thigh angle (`pilgrim_walk_v2.py`).
  - Over-tunic edges are still aliased cutouts. The robe back panel swings wide when he leans.
  - `MI_Garment_KohenGadolGold` does not exist (log warning); the stand-in garment is used.
- **Not modelled:** the western lamp's own law. The lamps go dark at the next loop's start while he is in
  the Ulam, which is a cut.
- **Seen in frames but not measured:** the static wall glow and the lid highlights do not change with the
  service at all.


---

# cp15 (2026-09-11): each lamp now visibly lights when he kindles it

Packaged build `C:\Mikdash\Builds\Checkpoint-cp15-20260911T020944Z` (`checkpoint_playable`, Candidate48 cooked
at `9cce6a5b…`). Movie `visual-review/movie-cp15-kohen-tend-close/` has 1246 frames at `-dumpmovie -benchmark
-fps=10`, the same view as cp14 (`BugItGo -5255 60 1045 -6 108 0`). Not committed.

## Result, as seen in frames

- **The lamp-row diff now differs clearly from the control.** See `visual-review/cp15-lamp-row-diff.png`, with
  numbers in the matching `.json` (made by `Scripts/lamp_row_diff.py`, same crop for both builds):

  | Pair | cp14 mean \|d\| | cp14 changed | cp14 new bright px | cp15 mean \|d\| | cp15 changed | cp15 new bright px |
  |---|---|---|---|---|---|---|
  | control, 25 s vs 35 s | 3.14 | 0.10% | 0 | 3.16 | 0.26% | 0 |
  | test, 35 s vs 115 s | 2.73 | 0.06% | 0 | **9.85** | **10.6%** | **209** |

  At 35 s all seven lids are dull gold. At 115 s the five nearest the camera (the north end, where he starts)
  burn: warm pools on lid and bowl, with a bright point at each crown. The two southern lamps are still dark
  (Temidin 3:17).
- **The kindling, 2 m away.**
  - `visual-review/cp15-lamp1-2m-BEFORE-kindling-t44.0s.png`: his hand is at the nearest lamp, which is dark.
  - `visual-review/cp15-lamp1-2m-AFTER-kindling-t48.0s.png`: the same lamp is burning after his hand has left.
  - `visual-review/cp15-lamp1-kindling-sequence-crop.png` covers 38-52 s: dark to 44.0 s, a glow under his
    fingertips at 44.5 s, lit at 45.0 s.
  - The glow falls where the clip puts it: arrival about 36 s, plus 8.8 s.
- **Limit, stated plainly:** at about 2.3 m and 1080p, the 3.2 x 7 cm flame card reads as a bright point at the
  lid crown plus the warm pool from its light. No flame silhouette is resolved. A closer camera has not been
  captured.

## Why nothing lit before, and what changed

1. **The director's lamp lights were ~0.002 cd, not 1.4 cd.** They are made by `NewObject<UPointLightComponent>`,
   and the `ULocalLightComponent` constructor sets `IntensityUnits = Unitless`. Unitless to candela is
   16/10000, so `SetIntensity(1.4)` was about 0.002 cd.
   - They are now built in candelas at `LampLightCandela` = 1.0 cd, about a candle, which is what an olive-oil
     wick gives. Each switches on with its own lamp's kindling.
   - The source radius is 0.8 cm.
   - The same Unitless bug also affects `AltarLight` (90 unitless is about 0.14 cd). It is recorded here and
     NOT changed.
2. **The flame cards did render. They were about three orders too dim.**
   - `M_FX_Flame` is Surface, Additive, Unlit and two-sided, on `/Engine/BasicShapes/Plane`, which is not
     Nanite. It needs no special usage flag.
   - The packaged log (cp14 and cp15 alike) has no warning for any FX material. The only "Default Material
     will be used" lines are the three `MI_SanctuaryV2_Gold*` MIs, which are missing the Nanite usage flag.
     That is pre-existing, out of scope here, and needs its own look.
   - `MI_FX_Flame_Lamp`'s EmissiveScale 9 amounts to about 9 cd/m². The director now writes
     `LampFlameEmissiveScale` = 5000 per card, in the order of a small flame's luminance. That raises the
     look only and adds no light.
3. **The static 90 cd `RELEASE_SanctuaryV2_MenorahLamps` is disabled on both maps** (intensity 0, visible False;
   the actor is kept). `Scripts/release_lamp_light.py`, full guard pattern:
   - Candidate48 apply: `3fb7b767 → 7118afac`.
   - Candidate48 revert: `→ 0988b1c1`, read back as 90 cd and visible. The bytes are not identical to the
     original, but the properties are restored.
   - Candidate48 re-apply: `→ 9cce6a5b`, which is the cooked map.
   - Main50 apply: `a34f7286 → e36210c6`.
   - Every run checkpointed to `ReviewCheckpoints\LampLight-*`, reopened, and read back numerically.
   - Only the light actor changed. The other map and all protected assets were unchanged.
   - The first attempt refused before saving, because the scene guard counted the light itself. The guard
     now allows exactly that actor.
4. **Lit state while he is elsewhere** (`LampBurning(..., ClearAtSeconds)`, `ClearAtClipSeconds` 1.6).
   - The first sequence is the morning: every lamp stays dark until his own kindling.
   - All seven burn after he leaves and through the 90 s interval.
   - In later sequences a lamp stays lit until the clearing moment of its own station (2.8 s in), then is
     kindled again at 8.8 s. That removes the cp14 cut, where all seven went out while he stood in the Ulam.
   - The 115 s movie does not reach a second sequence. That rule is proven only by the test.
5. **Tests:**
   - `ServiceScheduleMathTest` passes 100,347 checks, including the new "cp15" block.
   - `Scripts/verify.py` is green (7/7, math 32/32).
   - UBT editor and game builds succeeded.
