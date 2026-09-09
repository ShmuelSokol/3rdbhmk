## Current continuation — 2026-09-09 07:14 UTC

Candidate48 grounded service completes all18stations naturally, physical destination checks pass.
Visual foot planting on stairs and authentic garments/service animation remain unaccepted; startupOFF.
Candidate map7eda28df84b35e45a6e975d39bebc23817798cc2af2db324b0121e09a30255d2.
Next: inventory candidate transit-bridge/soft-wear parity; native player/tour/dove connections;
broader visual/performance review, then explicit default/cook map promotion and fresh Windows build.
Sound species routing compiled; V3 recordings still unimported/unauditioned. Prepared fresh importer
verifier is read-only; do not treat it as completed import. Video preview already shared.

## Verified continuation — 2026-09-09 06:13 UTC

Main gold and intro clock fixes are published; candidate intro opening and finish tested.
Candidate48 has saved/fresh-verified gold materials and V3 service body, with native
limited movement evidence. Service stays startupOFF: its stair path and stance are invalid.
Per-leg admission now prevents initial movement into rejected legs (34c8b3ad).
Candidate stair collision V2 matches visible geometry in71 native floor samples; four
stationary capsule positions still block and endpoint is16cm above actual tread.
No full service acceptance, candidate promotion, or new package. Latest exact receipts
and map hashes are at the top of AGENTS.md; historical unchecked rows below are not current state.

## Publication checkpoint evidence — 2026-09-09 04:09 UTC

Main saved-scene render 040520Z inspected in both gate views: the softer wear remains
subtle and paver joints remain visible. All maps/material instances/original saves unchanged.
Candidate C applied035717263399Z and fresh-verified035912952876Z, protected differences
empty, map d3c66fea6d550233304bf5b1d5d0ab57de728150b99f47d0fc60bd09207563f3.
Candidate render040128Z: interior paroches/reliefs readable, gold vessels still too bright;
exterior camera blocked by altar, so facade-quality acceptance remains open. All19maps
unchanged during capture. Gold-vessel PIE-only material A/B is being prepared.
The four new service-adapter C++ files have focused 100240-check math coverage but are
NOT in the prior Unreal build and are excluded from the preceding publication batch until
separate build acceptance. Runtime placement on candidate is still pending. No new package.

## Verified continuation — 2026-09-09 03:58 UTC

Full gate 9/9, 31/31 standalone math suites and Unreal compile/link passed (38.69 s).
Intro now shares the 19-point eastern route between live playback and editor tooling;
runtime clearance is still pending. Surface wear was visually rejected at full strength.
Two lower-opacity PIE views reviewed: conspicuous beige overlays are suppressed at 0.12.
Nine new SurfaceDetailSoftV1 child materials preserve V2; all 460 bindings saved/reopened
and independently verified, old assets unchanged. Main hash 478d326fc715e6690272e07043dd1238912d1c53a47066fb18cb432b0027e76c.
This is global attenuation, not a repair of ignored per-entry authored opacity or opaque
mask edges. Candidate48 sky/weather saved/reopened (035500097589Z), all other maps and
protected assets unchanged, hash e3794bc08c8f84e4d81bd20fee57123cebc3b8c59e851311d12fed0d644fbd73.
Candidate map-level lighting C port is underway. No promotion or new packaged release.

## Active update — 2026-09-09 03:43 UTC

Transit bridge observed 45 boarded and 35 alighted over 180 simulated seconds, with 20
photographers. Separate static apron figures; no verified transfer of the 24 residents.
One geometry refusal and 222 trimmed requests remain recorded. Maps and original saves
unchanged. Surface V2: all 23 saved asset hashes checked, and fresh process verified all
460 decals plus manager. The asset job crashed during shutdown after saving; preserved
exit receipt distinguishes this from a clean process exit. Placement readback falsely
rejected equivalent angles differing by 360 degrees; comparisons now wrap angular deltas.
Actual six-image wear comparison was visually REJECTED: beige patches over paving/stairs.
A lower-opacity PIE comparison is underway; do not call surface visual acceptance complete.
Soundscape importer is repaired for create-once V3 import only; no native import or audition.
No new packaged release. Exact 48 cm remains approved but candidate not yet promoted.

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
