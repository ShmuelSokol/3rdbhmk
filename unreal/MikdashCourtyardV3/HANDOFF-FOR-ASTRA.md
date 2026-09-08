# Handoff to Astra — 8 September 2026

Written by Claude (Opus 5) mid-session. Read this, then `AGENTS.md`, then
`INTEGRATION-QUEUE.md`. Last published commit: **558df0b9** on ShmuelSokol/3rdbhmk main.

## The one rule that matters most right now

Shmuel corrected me on pacing today, and it is the difference between shipping and
losing work: **an account-wide 5-hour usage limit killed about fourteen agents mid-write
at once.** That left a UCLASS header with no .cpp and five half-fixed math headers, and
the recovery cost more than the parallelism saved. Run **4 to 6 concurrent agents, not
14 to 20.** Let a wave finish before launching the next. Do cheap coordinator work
yourself between waves. He still wants maximum speed — exhausting the window is not speed.

## Run the gate before you believe anything

```
python scripts/verify.py            # environment, scripts, receipts, 24 math tests
python scripts/verify.py --build    # also UnrealBuildTool; slow, must run serial
```
It was green at handoff: **7/7 checks, 24/24 standalone math tests.** It reports what it
did NOT check rather than passing quietly. Preserved historical failure receipts show as
WARN, not FAIL, deliberately — there are 56 of them and they are evidence, not regressions.

## State of the build

**Compiles and links clean.** The module contains crowd field, gate security, bird flock,
service actor (Kohen Gadol), time of day, weather, transit, settings, menu widgets and the
front end. `MikdashFrontEnd.cpp` was written by hand after its agent was killed.

**Complete in code, NOT yet placed in the map:** essentially everything above. The map is
still Walkthrough-11 content. Placement is `INTEGRATION-QUEUE.md` stage 4, strictly serial.

**Never been through a compiler** (their agents were forbidden to run UBT):
`MikdashTourGuide.cpp`, `MikdashCodex.cpp`, `MikdashWater.cpp`, `MikdashEnclosure.cpp`,
and whatever the in-flight agents land. **Compile before placing.** `release_tour.py` and
`release_enclosure.py` both refuse before mutating if their classes are absent — trust that.

**In flight at handoff** (10 agents; check for their files and receipts before redoing
work): fire and smoke FX, vegetation, photo mode + cinematic intro, surface wear, birds
assets, transit placement, save + Hebrew localisation, pilgrim rig rebuild, soundscape,
and a draw-call optimization pass.

## The most important technical finding today

First real frame-time measurement this project has ever had (`Scripts/perf_probe.py`,
receipt `SourceAssets/perf-review/perf-probe-20260908T102520Z.json`):

- ~24 ms p50, about **40 fps against a 60 fps target**. 8 of 9 stations over budget.
- **7,767 actors, 44,217 instances, 7,520 UNIQUE static meshes, only 190 Nanite meshes.**
- Frame time is **flat**: sealed inside the Heikhal costs the same as the plaza over the
  whole city. A GPU-bound scene never does that. A cost that does not vary with the view
  is per-draw CPU work, and 7,520 unique meshes cannot batch.

So the bottleneck is draw calls, not pixels. `PERFORMANCE-BUDGET.md` apportions a GPU
problem the build does not currently have; its estimated rows stay estimated until the
optimization agent returns before-and-after numbers. Every millisecond freed there is a
millisecond the crowds, water, fire and vegetation can spend — treat it as the unlock.

## Two decisions that are Shmuel's, not ours

1. **The amah.** Two agents independently found that his book's own arithmetic gives
   **48 cm** (p. 359: 3000 amot = 1440 m; p. 116: Naeh 48, Chazon Ish 57.6). The level has
   **50 cm** baked in, so every book-derived length runs ~4.2% large. Rescaling touches
   everything. Do NOT do it unasked; it is raised with him and unanswered.
2. **The enclosure.** The Yechezkel 3000-amot precinct hides **1,911 of 11,437** OSM
   buildings and 485 of the 2,106 Old City facades, which is in tension with his own
   `people-and-city.md` policy. Three states exist (MODERN / YECHEZKEL / OVERLAY) so the
   choice stays his. Buildings are hidden by visibility, never deleted.

## MetaHuman is unblocked — correct the record

An earlier agent reported "MetaHuman Creator Core Data" missing. **It is installed**:
`Engine/Plugins/MetaHuman/MetaHumanCharacter/Content/Optional`, 1,816 files, 5.8 GB,
including Grooms (so beards), Clothing and BodyTextures. Any handoff or note saying that
is blocked is stale. `MetaHumanSDK` and `MetaHumanCharacter` are enabled in the .uproject;
`MetaHumanCrowd` was deliberately removed (its defaults render ~530 people and it drags
Mass/Mover/SmartObjects into the packaged runtime — the instanced crowd owns the crowd).
`Scripts/release_metahuman_enable.py` is written and runs clean offline. The first
auto-rig is an Epic **cloud** call that must be triggered once from the editor GUI; after
that it batches.

## Traps that have each cost this project a day

- A **zombie UnrealEditor.exe** holding the map makes `save_current_level()` return False
  with no other symptom. Check `Get-Process UnrealEditor,UnrealEditor-Cmd` before every job.
- **UBT globs `Source/`** — a `Tests/` folder there gets compiled into the game module.
  Tests now live at `Plugins/MikdashRuntime/Tests/`, outside Source. Keep them there.
- UE builds treat warnings as errors: a local named `Slot` shadows `UWidget::Slot`;
  `UImage::SetBrushSize` is deprecated for `SetDesiredSizeOverride`.
- `FText` has no `operator==`, so `TArray<FText>::AddUnique` will not compile.
- **AABB clearance checks give false blockers.** The 256 FutureMountV1 terrain tiles have
  400-800 m boxes enclosing the whole Temple, and hollow union meshes must be decomposed
  to constituent boxes. The water agent eliminated 14 false blockers this way today.
- Moving a **static-mobility** actor does not dirty its package. Re-spawn instead.
- Material parameter setters return **False even when they succeed**. Verify by readback.
- With Nanite on, `get_num_triangles(0)` returns the **fallback** count.
- Pin names: Desaturation's and Clamp's first input are both `None`; Noise's position pin
  is `World Position`; TextureSampleParameter2D's UV pin is `UVs`.
- Line traces return nothing in commandlets and NullRHI worlds. Only a real PIE traces.
- Several receipt JSONs carry a **UTF-8 BOM**; read with `utf-8-sig`.
- Cooks: **foreground** PowerShell, `cmd /c RunUAT.bat`, `-cookprocesscount=1`. Never from
  Git Bash ("C:\Program" error). Never with a GUI editor open (Live Coding). The packaged
  archive's root exe is a bootstrap that exits — hash the child in `Binaries\Win64`.

## Publishing

`cd C:\Mikdash\Working-5.8\RuntimeBuild-06 && python publish.py --stage` (needs
`PYTHONIOENCODING=utf-8`; Hebrew filenames break cp1252), then commit in
`C:\Mikdash\GitHub\3rdbhmk`. **Never `git add -A`.** Never force-push. Excluded by the
helper: Temple Institute reference photos, the book export, GPL models, vendored tools.
Watch for stray `.bak` files reaching the stage.

## What "done" means here

Shmuel wants Warner Brothers production quality and has said not to stop. The honest
standard we work to: everything present looking deliberate, nothing obviously wrong, and
every claim about the building traceable to a source with an explicit confidence label.
The codex now carries 76 entries — 33 certain, 33 disputed, 10 authored. Keep that
discipline: where commentaries disagree, name them; where we invented, say so. The
menorah lamp order is authored and is flagged in the codex as something that must not be
shown to anyone as the real order of the service. Do not quietly upgrade an authored
claim to a sourced one.

---

# UPDATE — 8 September 2026, later the same day

Everything above still stands. This section supersedes it where they differ.

## In flight from my end, right now

Two agents, unfinished at handoff. Check for their files and receipts before redoing them.

1. **Vegetation** — `ScatterMath.h`, `MikdashFoliageWind.*`, `create_vegetation.py`,
   `release_vegetation.py`, `SourceAssets/vegetation-review/`. Judean species, terraced
   olive groves, instanced placement by slope and altitude band.
2. **Draw-call optimization** — `Scripts/perf_optimize.py`, `perf_probe.py`,
   `PERFORMANCE-BUDGET.md`, `SourceAssets/perf-review/`. The most consequential one. It is
   the only agent permitted to launch Unreal.

## Landed since the first handoff

Surface wear and decals, save and Hebrew localisation, transit, photo mode and cinematic
intro, birds, pilgrim rig V3. Added to the earlier six (water, enclosure, gate security,
tour and codex, fire and smoke, soundscape) and the systems before those.

**None of it is placed in the map.** The map is still Walkthrough-11 content.

## Never been through a compiler

Agents were forbidden to run UnrealBuildTool. Unbuilt C++: `MikdashWater`,
`MikdashEnclosure`, `MikdashTourGuide`, `MikdashCodex`, `MikdashFXDirector`,
`MikdashSoundscape`, `MikdashSurfaceDetail`, `MikdashSaveGame`, `MikdashLocalization`,
`MikdashPhotoMode`, `MikdashCinematics`, plus edits to `MikdashTransit` and
`MikdashBirdFlock`. **One rebuild, fix what UHT complains about, then place.** Several
release scripts refuse before mutating if their class is absent — trust that.

## Coordinator wiring still owed — nobody's agent owns these

1. Transit `OnRequestBoarding` / `OnRequestAlighting` to the crowd field's converge-and-
   despawn and spawn-and-disperse. Honour `SecondsAvailable`; use `BoardingPoint`, not
   `GetStopLocation`. **Cap concurrent boarding groups yourself** — transit does not.
2. `SuggestPhotographerCount` to a standing photograph pose facing the Mount, about 22% of
   each alighting group. This is Shmuel's "lots of people taking pictures".
3. Bird `OnBirdSound` to the soundscape. The soundscape also has its own diffuse bird bed —
   connect them, do not let both play.
4. Swap the 24 residents onto PilgrimRigV3 using the per-variant `recommendedActorScale`
   (0.84–1.04, i.e. 150–187 cm). A crowd of identical heights is the next thing that will
   read wrong.
5. `DefaultGame.ini`: add `Content/Localization/Mikdash` to Additional Non-Asset
   Directories, or `strings.json` will not stage into the cook.
6. MetaHuman: the first auto-rig is an Epic **cloud** call that must be triggered once from
   the editor GUI; `Scripts/release_metahuman_enable.py` then batches the rest.

## Gate bug fixed today

`scripts/verify.py` built every test through one shared temp directory, so concurrent runs
clobbered each other's batch files and reported phantom failures on whichever test lost the
race. Per-process directories now. Three separate agents were misled by this before the
fix; if you see "the batch file cannot be found", that was it.

## Still open with Shmuel, unanswered

- **The amah.** His book's own arithmetic gives 48 cm; the level has 50 cm baked in, so
  book-derived lengths run ~4.2% large. Rescaling touches everything. Do not act unasked.
- **The enclosure** hides 1,911 of 11,437 buildings in the YECHEZKEL state, in tension with
  his own `people-and-city.md`. Three states exist so the choice stays his.
- **24 flagged Hebrew strings** in `needs-author-review.json` need a native speaker. Editing
  `strings.json` is enough — no recompile, no editor.

## One more trap, learned today

Three separate agents independently hit the AABB false-blocker problem in one session. The
enclosure wall is a **single Boolean union whose bounding box is the entire court** — the
surface pass was putting lichen in mid-air until it decomposed the union into its 116
source boxes. The water pass eliminated 14 false blockers the same way. Assume any
"blocker" from a whole-part bounding box is wrong until decomposed.

---

# FINAL STATE AT HANDOFF — commit f4a29ea9

**The "never been through a compiler" section above is now OUT OF DATE.** The editor
target builds green with all thirteen new classes in it. Six real defects were found and
fixed on that first build, listed in the f4a29ea9 commit message; the pattern worth
carrying is that none of them were logic errors — they were UHT and engine-API rules
that only a compiler can enforce, which is why agents forbidden to run UBT could not
have caught them.

## Where Astra picks up

1. **Nothing is placed in the map.** It is still Walkthrough-11 content. The whole point
   of the build being green is that `INTEGRATION-QUEUE.md` stage 4 can now run: the
   release scripts, strictly serial, one commandlet at a time, verifying each receipt
   before starting the next. That is the critical path and it has not started.
2. **The vegetation agent may still be running** when you read this. Check for
   `ScatterMath.h`, `MikdashFoliageWind.*`, `create_vegetation.py` and
   `SourceAssets/vegetation-review/` before redoing its work.
3. **The Nanite pass needs its derived-data rebuild to finish** before any frame time
   means anything — roughly 1,100 of 7,200 done at about 0.5/s. Until then the editor
   reads 24-31 ms and that number is not the steady state.
4. **Nobody has looked at the sanctuary since the Nanite pass.** The probe captured the
   editor viewport rather than the PIE camera, so there is no before/after. This project
   flattened a frieze relief once already. Look before accepting.
5. The six coordinator wiring jobs in the UPDATE section above are still owed.

## Run this first

```
python scripts/verify.py          # green at handoff: 7/7 checks, 24/24 math tests
Build.bat MikdashCourtyardV3Editor Win64 Development -Project=<uproject> -WaitMutex
```

Then place, then capture, then walk-probe, then cook. Commit as each lands — a session
limit killed fourteen agents mid-write this morning and the only reason that cost us
little is that everything since has been pushed as it landed.
