# Walkthrough-07 release note

Date: 2026-09-07 (evening). Map: `/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough`. Unreal Engine 5.8.2, Win64, Development.
Second consolidation round after Walkthrough-06 (see RELEASE-NOTE-Walkthrough-06.md). Still a walkable study, not a finished
design or a halachic ruling. Every claim points at a receipt under `SourceAssets\` or `C:\Mikdash\Working-5.8\RuntimeBuild-07\`.

## Package

- FINAL: `C:\Mikdash\Builds\Walkthrough-07\Windows\MikdashCourtyardV3.exe`
  - Fresh cook (no `-skipcook`, `-cookprocesscount=1`): 7,959 packages, 0 errors, 0 warnings, 162 s, peak 8.7 GB.
    Receipt `RuntimeBuild-07\final\receipt.json`, log `RuntimeBuild-07\final\uat.log`. Archive 2,786,110,860 bytes.
  - Root exe SHA-256 `0b1da59da948ed5c27aa0daad3cbb4a9c07872cc684b258a2329a191335a9e0c` (identical to Walkthrough-06: the
    root exe is Unreal's bootstrap launcher; the scene lives in `MikdashCourtyardV3\Content\Paks`).
  - Launch test `RuntimeBuild-07\final\Packaged-Launch-20260907T200227Z.json`: engine and paused menu ready after 20.3 s,
    MENU_OPEN once, no MENU_RESUME, 0 errors, closed by the test's safeguard. Earlier resume events in the 06 and 07-rc1
    tests happened while no input was sent by the test; a 40 s settle test showed the timing was independent of the script,
    consistent with an operator click. Not reproduced here.
  - git commit (`ShmuelSokol/3rdbhmk`, `unreal/MikdashCourtyardV3`): `29cf0195716f689eaebe426637144ce4e056ef2e` (hash recorded in the following commit).
- Release candidate `Walkthrough-07-rc1` (before the frieze and the Aron rotation): 7,958 packages, 0 errors, 179 s,
  peak 8.4 GB; launch smoke `RuntimeBuild-07\rc1\Packaged-Launch-*.json` (menu ready 20 s, 0 errors).

## Changed since Walkthrough-06 (all saved, reopened, read back numerically)

- **Keilim per the book "Lishchno Tidreshu"** (`SourceAssets\vessels-review\book-keilim-review-20260907.md`, pages 241-258;
  Rambam Beit HaBechirah 3:12 and 3:17; Rashi Shemos 26:35; Yoma 33b; Menachos 98b):
  menorah `[-5330, +315, 925]`, scaled to 150 cm (18 tefachim, p. 252), branch tips 125 cm from the south wall;
  shulchan `[-5300, -350, 925]`; incense altar `[-4650, 0, 925]` at the Heikhal midline, scaled to a 5-tefach amah
  (41.7 x 41.7 x 83.3 cm, p. 255). Receipts `keilim-move-*.json`, `keilim-scale-*.json`. Shulchan height (3 amot, p. 241) not changed.
- **Aron and menorah replaced by CC-licensed models** (`SourceAssets\third-party\`, attribution in `Content\Distribution\CREDITS.txt`):
  "Ark of the Covenant Box" by davidgra11 (CC BY-SA 4.0; body with poles and lid with two keruvim, about 1.0 M triangles,
  scale 1.471) as `RELEASE_Aron_Body/Lid` at `[-6200, 0, 925]`, length north-south (Rambam 3:12; rotated after user review,
  `aron-rotate-*.json`); "Menorah based on the Arch of Titus" by Dahan Meir (CC BY 4.0, scale 0.715) as `RELEASE_Menorah`.
  The 16 procedural Aron parts, the procedural keruvim and the menorah study were removed (`native-import-vessels-*.json`).
  Limitation: this Ark model's poles run along its length, so they now run north-south; Yoma 54a's east-west poles need
  separate pole meshes.
- **Kodesh doors and paroches** (`sanctuary-detail\DoorsParochesV1\native-import-*.json`): 12 Kodesh leaf meshes open inward
  (book pp. 60, 261) and the 7 x 6 amot paroches at X -5600 with rod and rings; 15 actors `Release/Doors`. The Heikhal
  folding leaves were deliberately not placed: the measured architecture already carries the four open gold door slabs.
- **Wall reliefs** (Yechezkel 41:18-20; book pp. 235-239, 258): a continuous gold frieze of 196 panels `RELEASE_Frieze_*`,
  250 x 250 cm, on the Heikhal and Kodesh walls, from the AI-generated relief `SourceAssets\visual-reference-handoff\
  gold-palm-cherub-relief.png` (central palm, two winged keruvim, human face toward the central palm and lion face toward the
  edge palms). Real geometry: 133k-triangle Nanite displaced panels from a derived height map (baked lighting removed by
  high-pass; approximate), plus a normal-mapped gold material. The 32 palm-only panels were removed
  (`KeruvFriezeV1\native-import-*.json`). Interpretive: winged lion bodies; the book draws upright bodies with the lion on the right.
- **Bus** (`arrival-review\TransitV2\native-placement-*.json`): 13 meshes `RELEASE_Bus_*` at `[-37951, 46855, 973]` on real
  asphalt at the west end of Batei Mahase road, PIE-traced (5.6 degree crossfall; the eastern half of the road exceeds 8 degrees).
- **Kodesh interior light** `RELEASE_KodeshInteriorLight` (1200 cd, warm), artistic, because the paroches now closes the opening.
- Credits: third-party model attributions added to `Content\Distribution\CREDITS.txt`.

## Verified

- Bounded PIE walks after the bus, reliefs and vessels: `IntegratedReviewV2\release-walk-*.json`, 10/10 checkpoints, 0 errors.
- Native renders `visual-review\release-capture-20260907T194843Z` (after the frieze), reviewed by eye: Kodesh walls read as
  embossed gold with palms and winged keruvim, the Ark faces the entrance with its keruvim lid and poles; Heikhal walls carry
  the same relief around the red paroches, the 150 cm menorah, the midline altar and the shulchan. Panel joints visible at
  close range. Earlier runs in the same folder family: `190508Z` (Ark and paroches before the frieze), `184946Z` (dark Kodesh
  before the interior light), `172401Z` (palm panels), `163722Z` (Walkthrough-06 state).
- Standalone tests: `runtime-review\standalone-tests-20260907.json`, six executables exit 0.

## Known limitations

- Kotel stone overlay is placed but hidden behind an OpenStreetMap city-wall slab 1 m in front of the Kotel face
  (`SM_Jerusalem_CityWalls_04_Grid_N002_P00x`); fix pending (split that mesh or regenerate the overlay at 112 cm offset).
- Frieze: visible joint every 250 cm (horizontal repeat not seamless), vertical repeat of a non-tiling image, approximate height.
- Shulchan lacks rods, trays and bread and is 76 cm tall (book: 3 amot). Incense altar is a plain box. No kiyor, outer altar,
  kohanim or Levites. Five idle pilgrims are placed figures, not AI. Audio is footsteps only. Materials plain outside the sanctuary.
- Book requirements table (`SourceAssets\research\book-scene-requirements-20260907.md`) lists 15 prioritised gaps, notably the
  3000 x 3000 amot Mount enclosure with five gates and the soreg, and the unbuilt chamber blocks.
- Temple Institute reference dossier (`SourceAssets\reference-ti\`, gitignored, used with the owners' permission) maps each
  vessel and garment to a modelling task.

## Controls and how to run

Unchanged from Walkthrough-06: launch opens paused with the pointer free; Start captures the mouse; W A S D or arrows walk;
Escape or P pause and release; M mutes; Alt+F4 quits. Windowed 1280 x 720 by default; Windows 10/11 x64, DX12 GPU.
