# Integration queue — Walkthrough-12

Engine jobs run SERIAL and in the FOREGROUND. RTX 2070 / 16 GB will not take two at once.
Kill any stray UnrealEditor.exe before each job: a zombie editor holding the map makes
saves return False with no other symptom.

## Stage 0 — before any engine job
- [ ] All C++ agents reported. Compiling while an agent is mid-write breaks the build.
- [ ] `Get-Process UnrealEditor,UnrealEditor-Cmd` returns nothing.
- [ ] No GUI editor open (UAT refuses with "Live Coding is active").
- [ ] Checkpoint the umap.

## Stage 1 — compile once, not per agent
The editor target must rebuild: MetaHumanSDK, MetaHumanCharacter and MetaHumanCrowd were
added to the .uproject and all three carry Source modules, so the editor will not open
until it is rebuilt. MikdashRuntime.Build.cs gained UMG (public) and RenderCore,
MovieScene, MovieSceneTracks, LevelSequence, AudioMixer, Projects (private).
- [ ] Rebuild MikdashCourtyardV3Editor Win64 Development.
- [ ] Fix whatever fails. Expect name collisions: AActor already defines `Role`, which
      has bitten this project once already.

## Stage 2 — standalone math tests (no engine, can run in parallel)
Discovered under Plugins/MikdashRuntime/Source/MikdashRuntime/Tests/. Each agent compiles
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
 1. [ ] release_enclosure.py        — decides what modern geometry is hidden
 2. [ ] release_water.py            — the stream cuts through the court
 3. [ ] release_vegetation.py       — needs the water and enclosure settled; batch with resume
 4. [ ] release_gate_security.py    — at the gates
 5. [ ] release_crowd_field.py      — reads keep-outs; run after the above change them
 6. [ ] release_birds.py
 7. [ ] release_kohen_service.py
 8. [ ] release_fx.py               — fire, incense, lamps
 9. [ ] release_surface_detail.py   — wear goes on top of everything
10. [ ] release_sky_tod.py          — lighting last so it is tuned against the final scene
11. [ ] release_tour.py             — markers at final positions
12. [ ] release_intro_sequence.py   — camera path against the final scene
13. [ ] release_frontend.py         — may change the startup map; record the previous value
14. [ ] release_localization.py
15. [ ] release_metahuman_enable.py — BLOCKED until the user installs MetaHuman Creator
       Core Data from the Epic launcher, and the first cloud auto-rig is triggered in the GUI

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
