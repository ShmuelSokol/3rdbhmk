# Walkthrough-06 release note

Date: 2026-09-07. Map: `/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough`. Unreal Engine 5.8.2, Win64, Development config.
This is a walkable study of the measured Yechezkel reconstruction with an authored future-Mount scenario. It is not a
finished future-Temple design and not a halachic ruling. Every claim below points at a receipt file under
`SourceAssets\` or `C:\Mikdash\Working-5.8\RuntimeBuild-06\`.

## Package

- FINAL: `C:\Mikdash\Builds\Walkthrough-06\Windows\MikdashCourtyardV3.exe`
  - exe SHA-256: `0b1da59da948ed5c27aa0daad3cbb4a9c07872cc684b258a2329a191335a9e0c` (archive 2,733,528,566 bytes;
    paks: global.ucas/.utoc, MikdashCourtyardV3-Windows.pak/.ucas/.utoc)
  - cook/package wall time: `164 s`, 7,941 packages, 0 errors, 0 warnings (fresh cook, no `-skipcook`, `-cookprocesscount=1`;
    receipt `RuntimeBuild-06\final\receipt.json`, log `RuntimeBuild-06\final\uat.log`). Two earlier attempts of the same cook
    were killed for low system memory (ShaderCompileWorker crash) and left no archive; the third, run with one cook process, succeeded.
  - Packaged launch test `RuntimeBuild-06\final\Packaged-Launch-20260907T165414Z.json`: engine and menu ready after 20.3 s,
    0 errors, closed via WM_CLOSE. One MENU_RESUME event 9 s after launch that the passive test did not send (an operator
    click on Start is suspected); the menu reopened on focus loss 0.35 s later, which exercises auto-pause and mouse release.
  - git commit (publishing clone `ShmuelSokol/3rdbhmk`, `unreal/MikdashCourtyardV3`): `b6caf1c36d19a889ad2651698485b7b875654252` (this note's hash line added in the following commit)
- Release candidate rc1 (superseded by the final build, kept as evidence): `C:\Mikdash\Builds\Walkthrough-06-rc1\`,
  cooked 7929/7929 packages, 0 cook errors, BuildCookRun exit 0 in 260 s (16:03:59-16:08:19 UTC), iostore pak,
  archive 2,733,244,796 bytes, exe SHA-256 `0B1DA59DA948ED5C27AA0DAAD3CBB4A9C07872CC684B258A2329A191335A9E0C`.
  Receipts: `RuntimeBuild-06\rc1\receipt.json`, `uat.log`.
- Earlier builds `Walkthrough-01..05` are not current (05 reused 04's cook).

## Verified (what was actually run)

- Packaged launch smoke, rc1: `RuntimeBuild-06\rc1\Packaged-Launch-20260907T161254Z.{json,log,png}`. Map loaded in 1.40 s,
  paused start menu visible 5.7 s after launch (`MIKDASH_MENU_OPEN cursor=visible pause=1`, once), no `MENU_RESUME`,
  window title `MikdashCourtyardV3 (64-bit Development PCD3D_SM6)`, closed by WM_CLOSE in 1.9 s, log ends `LogExit: Exiting.`
  Passive: no keyboard or mouse input was sent. The probe's `noFatal=false` flag was tripped by the ordinary
  crash-reporter registration lines, not by a crash; the process exit code was not captured.
- Bounded PIE walking, two runs, 10/10 checkpoints each, 0 errors: `SourceAssets\IntegratedReviewV2\release-walk-20260907T155105Z.json`
  (map before placement) and `release-walk-20260907T160235Z.json` (after keruvim and Kotel overlay). Routes: spawn
  x2100 -> outer court x5000 -> back (floors 500/300 cm, error 2.15 cm), and outer court -> east gate -> 12 gateway
  stairs -> Mount platform deck. Synthetic CharacterMovement input; not physical keyboard. NOTE: no PIE walk was
  rerun after the pilgrim placement, keilim move or terrain fix; those changed no floors or routes but are unproven at runtime.
- Map inventory before release edits: `release-inventory-20260907T154720Z.json` (7310 actors; 7322 after placement).
- Placement, saved and reopened: `release-placement-20260907T160101911633Z.json` (keruvim + 6 Kotel overlays; bus and
  pilgrims omitted, see below) and `release-placement-20260907T161402552292Z.json` (5 pilgrims; pose error 0 on reopen).
- Keruvim material: `vessels-review\KeruvimStudyV1\material-assignment-20260907T162320Z.json` (100 slots, 99 non-gold -> all gold).
- Keilim move, saved and reopened, reopen error 0.0 cm: `vessels-review\keilim-move-20260907T163327Z.json`.
- Terrain winding: `FutureMountV1\terrain-winding-diagnostic-20260907T163436996157Z.json` (inversion confirmed: all four
  cut tiles front-facing down), `terrain-winding-fix-20260907T163436996157Z.json` (all four tiles `fixed_and_verified`,
  saved, reloaded from disk, position/normal/colour error 0.0; the receipt's overall status is
  `failed_partial_state_preserved` only because a dirty-map guard fired after the saves; protected originals and the map
  were byte-identical), `terrain-winding-diagnostic-20260907T163551051478Z.json` (facesUp == triangles: 429/566/480/454).
- Ambient audio: `release-ambient-check.json` (one AmbientSound, old synthesized pilot, autoActivate false, volume 0.28).
- Native stills, 9/9 views, `visual-review\release-capture-20260907T163722Z` (after the keilim move and terrain fix).
  Reviewed by eye: exterior and overhead ground renders pale (black-terrain defect gone); Heikhal shows menorah south,
  shulchan north, altar centred in the western half, keruvim visible over the Aron through the Kodesh opening; five clothed
  pilgrims stand grounded in the outer court with shadows; Mount approach and spawn views read correctly. The Kotel
  close-up (`f_kotel_ground_detail.png`) shows only a flat beige face: the stone-course overlay is placed (six actors,
  identity transform, readback exact) but NOT visually confirmed. Bus view shows the empty street by design.
- Bounded PIE walk on the FINAL map (after all placements, moves and the terrain fix): `release-walk-20260907T164553Z`,
  10/10 checkpoints on both routes, 0 errors, map bytes unchanged.
- Standalone tests: `runtime-review\standalone-tests-20260907.json`, six executables (FootstepCadence, IncenseServiceSchedule,
  PreparationJourney, ResidentSimulation, crowd debug, crowd release) all exit 0.
- Code: `RuntimeBuild-06\editor-build-02.log` and `game-build-02.log` both `Result: Succeeded` (Editor and Game Development
  targets, including the previously uncompiled `MikdashResidentCharacter.cpp`). Resident crowd standalone module:
  `runtime-review\resident-crowd\standalone-tests.json` PASS 520 checks in debug and release (`/W4 /WX`).

## Changed in this release

- Keruvim `SM_KeruvimStudyV1` (70,848 tris) placed as `RELEASE_Keruvim_1` at `[-6200, 0, 925]`, yaw 90, NoCollision, on the
  shared Aron origin; world bounds Z 1008.3-1118.7 rest on the kaporet top (1008.3); cover height not added twice.
  All 100 material slots set to `M_KeruvimStudyGold`.
- Five PilgrimRigV2 idle figures (`RELEASE_Pilgrims_1..5`, outer court floor Z 300.0, idle clip, phases 0/0.7/1.4/2.1/2.8 s):
  `[4900,1000]` yaw 150; `[5120,1120]` yaw -115; `[4980,1260]` yaw 15; `[5240,1330]` yaw -60; `[4760,1180]` yaw 90.
  Min pairwise spacing 198 cm; clearance checked against 2633 architecture boxes with union meshes decomposed.
  Grounded from the floor component bounds (traces return nothing in the placement process), feet at floor +0.
- Kotel stone-detail overlay `SM_KotelFace_Tint0..5` as `RELEASE_Kotel_1..6` at identity, NoCollision; original wall intact.
- Heikhal keilim moved per `vessels-review\book-keilim-review-20260907.md` (Lishchno Tidreshu pp. 241-258, Rashi Shemos
  26:35, Yoma 33b, Menachos 98b, Rambam Beit HaBechirah 3:12 and 3:17), Z 925 unchanged:
  menorah `[-4900, 300]` -> `[-5330, 350]` (branches north-south, Rambam 3:12); shulchan `[-4900, -300]` -> `[-5300, -350]`
  (5 amot from the Kodesh wall, 2.5 from the north wall); incense altar `[-4500, 0]` -> `[-5150, 0]` (western half of the
  40-amah Heikhal, read as Rambam 3:17's "third" of the 60-amah house). Aron stays at `[-6200, 0, 925]` yaw 90.
- Four FutureMount cut terrain tiles rewound front-face-up (black-terrain defect fixed); tri counts, vertex colours,
  positions and normals unchanged.
- P key in the preparation lesson now returns to the menu like Escape (`SMikdashPreparation.h` OnKeyDown) instead of
  falling through to the controller's paused-P binding, which resumed play and captured the mouse. Compiled, not keyboard-tested.
- Config: `GameDefaultMap`, `EditorStartupMap` and `MapsToCook` switched to the combined map; `Launch-Courtyard.ps1` verifies
  the combined map. AndroidFileServer disabled (`bEnablePlugin=False`, network off) and its `SecurityToken` blanked.
  Past exposure: the old token was public in the repository from commit `f52c5ff` until this change; treat it as burned.
- `mikdash book/` (605 MB PDF + 86 MB JSON reference export) is gitignored and never published.

## Known limitations

- Bus omitted: the placement process had no ground trace (`traceSelfTest` NO_HIT), and offline interpolation of the
  candidate Batei Mahase road at XY `[-23101.76, 36185.43]` shows about 28 degrees of crossfall across the wheel track.
  Station not placed. No boarding (aisle narrower than the capsule). No source-proven railway.
- Sanctuary doors/paroches (9 source meshes) and cedar/palm reliefs not imported. The Yechezkel 41:18-20 keruvim panels with
  man and lion faces were never modeled; only a palm-only panel exists as a source OBJ.
- Incense (ketores / maaleh ashan) not integrated; smoke studies V1-V3 fail visually, V4 is offline only.
- No embodied AI population. The five pilgrims are placed idle figures. The resident crowd runtime is compiled and
  standalone-tested but not bound to any character in the map.
- Audio: recorded CC0 footsteps only. Synthesized ambience stays off. CC0 wind not auditioned, not in the build.
- Materials plain: flat stone/paving, uniform terrain texturing, plain city massing; JerusalemStoneV2 pilot unassigned.
- Keilim dimensions not yet changed to the book's: shulchan height 3 amot (150 cm, scene 76), menorah 18 tefachim (150 cm,
  scene 180), incense altar amah of 5 tefachim (about 41.7 cm, scene 50). Aron lacks luchot; keruvim are a study.
- Visual acceptance of the post-fix stills is pending; walking after the final edits is unproven in PIE and unproven in the
  packaged exe (launch smoke only). Cloud/wind serialization does not make foliage move.
- Free exploration with collision only; no access-zone enforcement. Temple alignment to the modern city is hypothetical.

## Controls

- Launch opens paused with the pointer free. `Start` begins and captures the mouse.
- Move: W/A/S/D or arrows. Look: mouse. Step height 55 cm.
- Pause / release mouse: `Escape` or `P`. Resume: `Escape`, `P`, or the Resume button. In the preparation lesson,
  `Escape` or `P` returns to the menu.
- `M` or the menu sound control: mute/unmute (persists). Alt-Tab pauses and stays paused. `Quit` or Alt+F4 exits.
- In-editor PIE: Shift+F1 releases the mouse; Escape stops play.

## How to run

- Packaged: run `Windows\MikdashCourtyardV3.exe` from the build folder. That exe is a bootstrap; the game process is
  `Windows\MikdashCourtyardV3\Binaries\Win64\MikdashCourtyardV3.exe`. Windowed 1280x720 by default, VSync, 60 fps cap.
  Windows 10/11 x64, DX12 (SM6) GPU; tested on an RTX 2070 class card. Optional: `-windowed -ResX=1920 -ResY=1080 -log`.
- From source: open `MikdashCourtyardV3.uproject` with UE 5.8.2 (the editor opens the combined map) and press Play, or run
  `Launch-Courtyard.ps1`. Building `Plugins\MikdashRuntime` needs MSVC 14.44, Windows SDK 26100, NetFxSDK 4.8.
- Never run the one-shot bootstrap import against an existing project.

## Source distinctions

- MEASURED / SOURCED: Temple architecture from the Yechezkel reconstruction, 0.5 m per amah (source revision
  `41265f719bbea940f980a74aaed655a05552e489`); OSM buildings and streets (ODbL, 2026-05-06); Mapzen/SRTM terrain (66,049
  heights matched to SRTM N31E035; 748 m project datum, leveled, not a survey); keilim positions from the cited book and
  Gemara/Rambam passages; Fantozzi/qubodup CC0 footsteps. Credits: `Content\Distribution\CREDITS.txt`.
- INTERPRETED / AUTHORED: vessel and keruvim forms (studies guided by Temple Institute references, not copies); gold veneers,
  Kotel courses and tints; the Mount platform, tree and building removal, bus road and station (future scenario);
  pilgrim clothing and rig; where the book is silent (edge-vs-centre for the 2.5/5 amot offsets, Aron offset inside the
  Kodesh) the scene takes one reading and records it in `book-keilim-review-20260907.md`.
- REJECTED / NOT CLAIMED: synthesized ambience; incense studies V1-V4; gold lighting-polish donor; mannequin population;
  any western gate through the sanctuary wall; the bus at the untraced candidate.

## Next steps (priority order)

1. Model and import the Yechezkel 41:18-20 wall reliefs: keruv with man's face and lion's face alternating with palms.
2. Import and place doors/paroches (`create_sanctuary_doors.py`, paroches at X -5600, 350 x 300 cm, doors 2 x 3.5 x 6 amot).
3. Bus placement via a PIE ground trace (or an explicit `bus_ground_z`), choosing a candidate with acceptable crossfall.
4. Keilim dimensions: shulchan 150 cm high, menorah 150 cm, incense altar 41.7 cm square; add the menorah tending stone.
5. Incense: a smoke study that reads at eye level, timed to the schedule; only then integrate.
6. Embodied residents: bind `MikdashResidentCharacter` to reviewed routes; replace idle figures.
7. Materials: assign the stone pilots, texture the terrain, then revisit city massing.
