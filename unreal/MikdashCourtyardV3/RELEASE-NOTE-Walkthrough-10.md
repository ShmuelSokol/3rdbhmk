# Walkthrough-10 — overnight visual pass

8 September 2026, early hours. Built by Claude after the Astra/Codex handoff (`HANDOFF-FOR-CLAUDE-FABLE-OVERNIGHT.md`).
Walkthrough-09 and its public preview release remain untouched and are still the published download.
This is a development preview, not a finished experience and not a halachic ruling.

## Package

- `C:\Mikdash\Builds\Walkthrough-10\Windows\MikdashCourtyardV3.exe` (root bootstrap).
- Actual game child: `...\Walkthrough-10\Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe`,
  SHA-256 `29dd0d553e5f094a9f85e005795f2c790fd02574ff3ba637737bfcf037af157a`. Archive 2,964,786,305 bytes.
- Fresh cook, no `-skipcook`: 8,044 packages, 0 errors, 0 warnings, 222 s. Log `RuntimeBuild-10\uat.log`.
- Not published as a download. The public release is still `walkthrough-09-preview`.

## What changed since Walkthrough-09

- **Western Wall rebuilt as real stone.** 1,704 individual ashlar blocks in 29 courses (7 Herodian courses
  110-120 cm with drafted margins, 8 middle, 14 upper), 3 cm recessed joints, per-stone tint and roughness,
  blocks standing 0-6 cm proud with slight tilt. Replaces the four stretched photo panels, which are hidden
  (recorded for restore). Photos remain the colour reference only.
  Receipts: `SourceAssets\kotel-detail\KotelStoneV2\`.
- **Menorah rebuilt in the Temple Institute style** you asked for: rounded nested branches, hexagonal stepped
  plinth, 22 goblets, 11 knops, 9 flowers, 7 lamps with wick nozzles turned toward the centre, 150 cm
  (18 tefachim, book p. 252), branches north-south per Rambam 3:12, with the three-step tending stone
  (Rambam 3:11). Replaces the CC BY Titus-style model, which stays on disk with its attribution.
  Receipts: `SourceAssets\vessels-review\MenorahV3\`.
- **Ark poles now run east-west** toward the paroches (Yoma 54a; book pp. 59-60, 260-261). The purchased model's
  fused poles were cut off the body mesh (85,740 triangles removed) and two 6.8 m poles were placed through the
  rings. Receipt `SourceAssets\third-party\aron-poles-*.json`.
- **Gold rebalanced** on the veneers, vessels and floor: physically plausible gold, roughness raised from 0.28-0.34
  to 0.42-0.50 so the floor stops mirroring like glass. The frieze material was reverted after its own render
  showed the wall relief flattening; the pre-balance frieze look is what shipped.
- **Highlights softened**: entrance fill light 25,000 to 15,000 cd, film white clip 0.04 to 0.02, shoulder 0.26 to
  0.30, auto-exposure high percent 90 to 95. Receipt `SourceAssets\lighting-review\fill-highlight-*.json`.
- **Dove and people**: new dove body and separate wing meshes with a sine flap (4 Hz cruise, 6 Hz climb, glide on
  descent), lagged following camera with bank, forward sphere sweep that slows and slides instead of stopping, and
  a floor/ceiling clamp. One resident (body 04) now walks a 69 m five-goal loop with pauses, look targets and a
  sidestep recovery. Receipts: `SourceAssets\runtime-review\dove-people-v2\`.

## Verified

- Bounded PIE walk on the final map: 10/10 checkpoints, 0 errors, map bytes unchanged
  (`SourceAssets\IntegratedReviewV2\release-walk-20260908T011223Z.json`).
- Packaged launch smoke on Walkthrough-10: engine and paused menu ready, MENU_OPEN once, no MENU_RESUME, 0 errors,
  closed by the test (`RuntimeBuild-10\Packaged-Launch-20260908T011720Z.json`).
- Nine-view native renders before and after: `release-capture-20260908T001321Z` (before) and
  `release-capture-20260908T011842Z` (after), both under `SourceAssets\visual-review\`.
- Standalone C++ tests for the new flight and route maths: 6/6 pass
  (`SourceAssets\runtime-review\dove-people-v2\tests.json`). Editor and game targets compile.

## Not done, and honest limitations

- **Interactive controls on the packaged build are still untested.** The Windows security prompt needs a person at
  the keyboard; I did not bypass it. Start, mouse look, dove takeoff, F/Space/Ctrl/Shift, mute and quit remain
  unconfirmed in the standalone game.
- Exterior fixes (plaza-to-platform access stairs, material tiling repetition, sky tint) were written but not
  applied: the script hit a missing 5.8 Python API and the agent ran out of budget mid-fix.
  Review and script: `SourceAssets\arrival-review\ExteriorReviewV1\`, `Scripts\release_exterior_fixes.py`.
- Old City buildings are still flat extruded boxes and the city is not filled out to modern density. The facade and
  infill task was started and not finished.
- People still have one authored loop each and no dialog. The 24-person mission and dialog system was started and
  not finished. Five figures remain idle placed models.
- The Heikhal rear wall still reads bright. The Kotel is dark in this capture because the sun is on the far side.
- No audio work. The rejected loop stays muted.
- Frieze joints are still visible every 250 cm; the mirrored retile reduced but did not remove them.
