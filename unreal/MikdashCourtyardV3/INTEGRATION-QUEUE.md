# Integration queue — Walkthrough-12

## Latest progress — 2026-09-09 UTC (supersedes historical unchecked rows)
- Enclosure main/candidate persistence repaired; main gate visible in PIE. NoCollision
  enclosure segments are a depiction, not a walkability pass.
- Lighting C adopted; all 24 V3 residents spawn and move on both maps (dcebc3d4).
- Sky/time-of-day and weather saved/reopened on main, native-place-20260909T030218302603Z.
  Fresh PIE sees one of each, clear weather, 30000 lux/6500 K, sky 1.3, fog 0.0015 and
  local-exposure C settings retained. Three-view capture030529Z inspected: preserved detail, dark backlit gate and bright
  vessel highlights remain. Native functions accepted only for morning; dusk/night unreviewed.
- Gate-security read-only verification030841758949Z passed90/90, including disabled
  collision plus NoCollision profile; map unchanged.
- 48 cm candidate remains isolated; no new cook or release from this continuation yet.


Engine jobs run SERIAL and in the FOREGROUND. RTX 2070 / 16 GB will not take two at once.
Inspect any existing UnrealEditor process and establish ownership before each job. Never kill the user's editor or an active colleague job. An abandoned editor holding the map makes
saves return False with no other symptom.

## Stage 0 — before any engine job
- [ ] All C++ agents reported. Compiling while an agent is mid-write breaks the build.
- [ ] `Get-Process UnrealEditor,UnrealEditor-Cmd` returns nothing.
- [ ] No GUI editor open (UAT refuses with "Live Coding is active").
- [ ] Checkpoint the umap.

## Stage 1 — compile once, not per agent
The editor target must rebuild: MetaHumanSDK and MetaHumanCharacter were
added to the .uproject and carry Source modules (MetaHumanCrowd was removed), so the editor will not open
until it is rebuilt. MikdashRuntime.Build.cs gained UMG (public) and RenderCore,
MovieScene, MovieSceneTracks, LevelSequence, AudioMixer, Projects (private).
- [ ] Rebuild MikdashCourtyardV3Editor Win64 Development.
- [ ] Fix whatever fails. Expect name collisions: AActor already defines `Role`, which
      has bitten this project once already.

## Stage 2 — standalone math tests (no engine, can run in parallel)
Discovered under Plugins/MikdashRuntime/Tests/. Each agent compiles
and runs its own with cl.exe, but the acceptance gate re-runs them all together.
- [ ] scripts/verify.py green.

## Stage 3 — content generation (offline python, parallel-safe)
Meshes and textures generated outside the engine. Order does not matter.
- [ ] create_* scripts for crowd figures, birds, gate security, water, vegetation,
      enclosure, decals, FX textures.

## Stage 4 — engine placement, STRICTLY SERIAL, one at a time
Each is a `-run=pythonscript` commandlet with its own -abslog. Verify the receipt before
starting the next. If a receipt records failure, stop and fix rather than continuing.
Order chosen so that anything reading positions from the map runs after what it reads.
 1. [ ] release_enclosure.py        — HOLD changed scenario selection; user approved book-selected 48 cm. Keep active legacy geometry coherent until the checkpointed migration and dependent placements pass. See SourceAssets/scale-review/AMAH-MIGRATION-PLAN.md.
 2. [ ] release_water.py            — HOLD full adoption until host floor/foundation openings exist; current placement alone leaves water 26 cm below intact paving. See takeover water audit.
 3. [ ] release_vegetation.py       — needs the water and enclosure settled; batch with resume
 4. [ ] release_gate_security.py    — at the gates
 5. [x] release_crowd_field.py      — 240 runtime agents saved/reopened, six zones/keep-outs. Reconcile with future water/48 cm migration; live/visual/performance checks separate.
 6. [ ] release_birds.py
 7. [ ] release_kohen_service.py
 8. [x] release_fx.py               — director/materials saved/reopened; live/visual review pending. Service cue wiring remains dependent on service adoption.
 9. [ ] release_surface_detail.py   — wear goes on top of everything
10. [ ] release_sky_tod.py          — lighting last so it is tuned against the final scene
11. [x] release_tour.py             — guide/codex plus18 markers saved/reopened on legacy50 geometry;18/76 entries reload from staged Content/Distribution/Tour. Runtime interaction and48cm relocation remain separate.
12. [ ] release_intro_sequence.py   — camera path against the final scene
13. [ ] Front-end subsystem/controller integration — automatic GameInstance subsystem; no separate release_frontend.py or startup-map change
14. [ ] release_localization.py
15. [ ] release_metahuman_enable.py — Core Data is installed; first Epic cloud auto-rig still requires the editor GUI.

## Stage 5 — verify
- [ ] perf_probe.py against PERFORMANCE-BUDGET.md
- [ ] Nine-view capture, compared by eye against the previous release
- [ ] Bounded walk probe and the sanctuary round trip
- [ ] scripts/verify.py green again

## Stage 6 — ship
- [ ] Foreground cook: cmd /c RunUAT.bat ... -AdditionalCookerOptions="-cookprocesscount=1"
      Never from Git Bash. Never with a GUI editor open.
- [ ] Launch smoke test; hash the CHILD exe in Binaries\Win64, not the bootstrap at the root.
- [ ] publish.py --stage with explicit paths. Never `git add -A`.
- [ ] Release note, commit, push, report the hash.
