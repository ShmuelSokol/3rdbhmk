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
