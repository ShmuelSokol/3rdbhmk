# Handoff to GPT Astra — 2026-09-07 evening (from Claude Code)

Read this, then AGENTS.md (current state and hard rules) and RELEASE-NOTE-Walkthrough-07.md. Plan for about two hours
of work. Shmuel's standing goal: keep building toward AAA-game graphics, per his book "Lishchno Tidreshu", verify every
step, ship fresh builds, publish source with explicit staging, report hashes. Never claim finished.

## Where things are

- Working project: `C:\Mikdash\Working-5.8\MikdashCourtyardV3` (map `/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough`).
- Publishing clone: `C:\Mikdash\GitHub\3rdbhmk` -> `ShmuelSokol/3rdbhmk` main. Last push `445f72f` (working state, uncooked
  changes included). Publish helper: `set PYTHONIOENCODING=utf-8` then `python C:\Mikdash\Working-5.8\RuntimeBuild-06\publish.py --stage`
  (copies changed publishable files into the clone and stages them by explicit path; excludes GPL models, Temple Institute
  photos, vendored tools, the book export). Then `git commit` and `git push` from the clone. Never `git add -A`.
- Latest build: `C:\Mikdash\Builds\Walkthrough-08\Windows\MikdashCourtyardV3.exe` (cooked 20:5x local, 7,999 packages,
  0 errors, log `C:\Mikdash\Working-5.8\RuntimeBuild-08\uat.log`). No launch test or render was run on it yet.
  Builds 06 and 07 have release notes; 08 has none (write RELEASE-NOTE-Walkthrough-08.md after verifying).
- Engine: `C:\Program Files\Epic Games\UE_5.8`. Python: `Engine\Binaries\ThirdParty\Python3\Win64\python.exe`.
- Machine: RTX 2070, 16 GB RAM. Run engine jobs ONE AT A TIME. Cooks must run in the FOREGROUND from PowerShell
  (`cmd /c "RunUAT.bat" BuildCookRun ... -AdditionalCookerOptions="-cookprocesscount=1"`); background cooks get killed
  for memory. Never call the .bat from Git Bash.

## What is in the working map now (all saved, reopened, read back; receipts under SourceAssets)

Frieze V2: 211 mirrored, staggered Nanite relief panels on all Heikhal/Kodesh walls (`sanctuary-detail/KeruvFriezeV2/`).
PBR triplanar materials on 2,434 architecture slots, seven CC0 Poly Haven sets (`materials-pbr/`). CC BY-SA Ark with
poles cut off and two east-west poles reaching the paroches (`third-party/aron-poles-*.json`). CC BY Titus menorah 150 cm.
ShulchanV2 with 28 rods, supports, 12 loaves, censers (`vessels-review/ShulchanV2/`). IncenseAltarV2 at the midline
(`vessels-review/IncenseAltarV2/`). Kodesh doors open inward, paroches with palm/keruvim pattern
(`sanctuary-detail/ParochesPatternV1/`). Kodesh interior light. Bus on Batei Mahase road. Five idle pilgrims.

## Prepared but NOT yet applied (scripts compiled; patched but unrun since the patch)

1. Kotel occlusion cut (the stone overlay is hidden behind an OSM city-wall slab). Run a diagnose first:
   `UnrealEditor.exe <uproject> /Engine/Maps/Entry -ExecutePythonScript=C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_fix_kotel_occlusion.py -unattended -nosplash -nullrhi -EnablePlugins=GeometryScripting -DiagnoseOnly -abslog=C:/Mikdash/Working-5.8/Release-Kotel-Occlusion-02.log`
   then without `-DiagnoseOnly`. Last failure was a Python binding name (`get_num_triangle_i_ds`), patched.
2. Lighting and post-process polish (morning sun az 110 el 30, height fog, auto exposure EV 8-14, filmic, entrance fill light,
   scattered clouds): `UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_lighting_polish.py -unattended -nullrhi -abslog=C:/Mikdash/Working-5.8/Lighting-Polish-02.log`
   (`-LightingDryRun`, `-LightingRevert`, `-LightingSun=afternoon` exist). Last failure: trusted a setter's bool; patched.
3. City and terrain materials (buildings, roads, paths, city walls, terrain; six CC0 sets in `materials-context/`):
   `... -script=.../Scripts/release_context_materials.py -ContextImportOnly` then `-ContextApply -ContextCategories=walls`
   (58 meshes) as a smoke test, then full `-ContextApply` (4,625 meshes; several minutes). `-ContextRevert` exists.
4. Mount enclosure V1 (3000 x 3000 amot wall, five gates, cheil, soreg; `Scripts/release_import_enclosure.py`): ON HOLD.
   It cuts through the modern city model (see `SourceAssets/FutureMountV1/EnclosureV1/preview-plan.png`). Needs Shmuel's
   decision on treating the surrounding city before placement.

## Verification loop after each change (all scripts exist)

- Render: `UnrealEditor.exe <uproject> /Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough -ExecCmds="py C:/Mikdash/Working-5.8/run-release-capture-views.py" -unattended -NoSplash -abslog=...`
  (real RHI, about 8 min, nine views into `SourceAssets/visual-review/release-capture-<stamp>/`). LOOK at the PNGs.
- Walk: `set MIKDASH_WALK_QUIT_EDITOR=1` then `UnrealEditor.exe <uproject> <map> -ExecCmds="py .../Scripts/release_walk_probe.py" -unattended -NoSplash -nullrhi -abslog=...`
  (10 checkpoints, receipt `IntegratedReviewV2/release-walk-*.json`). Note: the IncenseAltarV2 is BlockAll on the y=0 line;
  the probe routes do not enter the Heikhal.
- Cook to a NEW folder (`Walkthrough-09`), then launch test: `powershell -File C:\Mikdash\Working-5.8\RuntimeBuild-06\packaged-launch-test.ps1 -Exe <exe> -OutputDir <dir>`
  (passive, screenshots, closes the game; a MENU_RESUME with no input would be a bug to investigate).
- Publish (above), report the commit hash, write the release note.

## Pitfalls learned today (also in AGENTS.md)

HitResult fields need `break_hit_result` or `to_dict()` depending on launch mode; traces return nothing in commandlets
and NullRHI editor worlds (only PIE); PIE leaves dirty packages, so place-from-receipt runs in a second commandlet;
GeometryScript `get_triangle_uvs` is not bound; `MaterialEditingLibrary.set_material_instance_*_parameter_value` always
returns False in 5.8 (verify by readback); `MaterialInstanceConstantFactoryNew.initial_parent` is not exposed; UE is
left-handed (generated meshes need a winding check, signed volume > 0); AABB clearance must exclude terrain tiles and
decompose union meshes; the archive-root exe is a bootstrap that exits at once.

## Open decisions for Shmuel

Enclosure vs modern city; GPL-licensed models (unused); Aron keruvim style (lion bodies vs the book's upright bodies);
shulchan height reading (3 amot applied); redistribution of Temple Institute photos (currently private, gitignored).
