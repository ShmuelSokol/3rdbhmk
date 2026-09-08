# SoundscapeV2 — the layered soundscape

Prepared 2026-09-08. **Nobody has listened to any of this.** Not one of the twenty-nine
recordings below has been auditioned, and neither
`Scripts/release_soundscape_v2.py` nor the actor it places has ever been run against the
editor. Everything here is a licence check, a container check, a signal measurement, an
arithmetic proof or a design intention. None of it is a hearing, and none of it is
acceptance.

The previous ambience was rejected as *"just a loop of some white noise and birds and
banging"*. That bed (`/Game/MikdashV3/Runtime/Audio/SW_CourtyardOriginal_Pilot01`) stays
in the level, stays disabled, and is hashed as a protected asset so this pass cannot touch
it.

---

## What changed since the first attempt, and why

The first attempt tried to fix "it reads as a loop" with `USoundCue` graphs built from
Python. That could not work honestly. `USoundCue::AllNodes` and `SoundCueGraph` are plain
`UPROPERTY()` with neither `CPF_Edit` nor `CPF_BlueprintVisible`, so a Python-built cue
*plays* but opens **empty** in the Sound Cue Editor and is destroyed the moment anyone
saves it there. Shipping a soundscape whose logic nobody can open is not shipping a
soundscape.

**All of the randomisation now lives in C++**, in `AMikdashSoundscape`
(`Plugins/MikdashRuntime/.../MikdashSoundscape.h` and `.cpp`). One actor holds every
emitter, decides on every pass which take plays, after what silence, at what pitch and at
what level, and applies the zone acoustic. There is no cue graph to corrupt, no fixed
period to find, and the whole judgement is ordinary code that a person can read, test and
change. The old `AmbientSound` + `SoundCue` path is still in the script behind
`-SoundscapeAmbientFallback` for diagnosis; it is not the design.

The engine-free half of that header is compiled and asserted by
`Plugins/MikdashRuntime/Tests/SoundscapeMathTest.cpp` — **76,981 checks, no engine
required** — and `Scripts/create_soundscape_v2.py` re-implements the same arithmetic in
Python and then **proves the two are bit-identical** by comparing 128 golden vectors
before it reports a single number.

---

## The layers

Twenty-three emitters, ten layers, all spatialised, none a stereo bed. Coordinates are UE
centimetres, +X east, +Y south, +Z up. Day gains are for 8 September in Jerusalem at the
real solar anchors that `AMikdashTimeOfDay` reports for that date.

| Layer | Runtime layer | Mode | Takes | Emitters | Dawn | Noon | Night | Height | Occl. | Crowd |
|---|---|---|---|---|---|---|---|---|---|---|
| windBedBase | WindBed | continuous | 1 | 1 | 0.62 | 0.72 | **0.88** | yes | – | – |
| windBedAir | WindBed | continuous | 1 | 1 | 0.62 | 0.72 | **0.88** | yes | – | – |
| windOverlay | WindGust | gap + event | 2 | 2 | 0.55 | 0.70 | **0.95** | yes | – | – |
| doorwayWind | WindBed | continuous | 1 | 1 | 0.62 | 0.72 | 0.88 | – | – | – |
| cityHum | City | continuous, take re-drawn | 2 | 4 | 0.34 | **1.00** | 0.30 | **yes** | yes | – |
| murmur | CrowdDistant | gap + event | 2 | 2 | 0.10 | 0.90 | 0.05 | – | yes | – |
| **crowdCourt** | CrowdCourt | continuous, take re-drawn | 2 | 3 | **0.06** | **1.00** | **0.02** | – | yes | **yes** |
| bird | Bird | flock hook + gap | 7 | 5 | **0.85** | 0.34 | 0.04 | – | yes | – |
| foliage | Foliage | continuous | 1 | 2 | 0.60 | 0.75 | 0.85 | – | – | – |
| cloth | Cloth | gap + event | 1 | 2 | 0.55 | 1.00 | 0.70 | – | yes | – |
| footstep | Footstep | on request | 12 | – | 1.00 | 1.00 | 1.00 | – | zone | – |
| service | Service | on request | **0** | – | 0.45 | 0.70 | 0.00 | – | zone | – |

Reproduce the table with `python Scripts/create_soundscape_v2.py --table`.

### What each layer is doing

**Wind over the Mount, varying with height and exposure.** Three continuous emitters and
two gust emitters. `WindGainFromHeight` raises the level with height on a log-shaped curve
that flattens, so the highest step is windier than the court without the bed swelling
absurdly, and interpolates that against a sheltered floor by the listener's **exposure**,
which comes from the same zone table that drives reverb — so the two can never disagree.
Standing in the Ulam porch (exposure 0.25) is sheltered without anything switching off.

**The murmur of the crowd in the courts.** New in this pass, and the largest gap in the
first one. The project instances thousands of figures plus 24 speaking residents, and a
full court that made no sound was the loudest wrong note there was. Three emitters — inner
court, outer court, inside the east gate — whose level follows the live head count through
`CrowdMurmurGain`: the square root of the count, the standard incoherent-sum rule for many
uncorrelated voices, saturating so that past a few thousand a court gets denser rather
than louder. **An empty court is silent, not quiet**, which is what dawn is.

**The modern city below, fading as you climb.** Four emitters 270–400 m out. A plain
attenuation asset cannot express the fade, because those emitters are hundreds of metres
away horizontally and climbing 40 m barely changes that distance; `CityGainFromHeight`
does it explicitly — 1.00 on the plaza, ~0.55 in the courts, 0.34 at the summit, never
zero. The city is still there; it is below you.

**Birds, through the flock agent's hook.** `AMikdashBirdFlock` broadcasts `Call`,
`Wingburst`, `Startle` and `Land` and deliberately plays no audio itself.
`AMikdashSoundscape::HandleBirdSound` is bound to all four — **reflectively, by looking the
`OnBirdSound` delegate up by name and checking its signature**, so this module never
includes their header and cannot break their build or be broken by it. Calls draw from the
seven verified bird one-shots, rate-limited across all flocks, gated by the Bird day curve
so the flock still flies at night and simply is not heard. Five timer-driven bird emitters
remain as a floor for the parts of the precinct no flock reaches.

**Footsteps by surface.** Twelve one-shots, six stone and six sand, three per foot. **The
surface decision is not made here and is not duplicated**: `MikdashSurfaceAudioRouting.h`
already routes a floor mesh package path to a Stone / Soft / Silent bank, and
`AMikdashSoundscape::PlayFootstep(bank, location, level)` only holds the banks and plays
what it is told. What this pass adds is that the step is spatialised at the foot, occluded
by the court walls and filtered by the zone the walker is standing in, instead of being a
flat 2D sound. The locomotion owner adopts it by calling one function; no file of theirs
is edited.

**The service.** `PlayServiceSound` is wired, the Service day curve is authored, and
`AMikdashServiceActor` can drive it without either file being edited. **The bank is empty
and that is deliberate.** No recording of the service exists and none can be sourced —
there is nothing to record. What belongs there is authored or performed material, which is
the user's decision, not a search result. Until then the layer is silent and says so, in
the spec, in the receipt and here.

---

## Why this should not read as a loop

Four mechanisms, each of them measured rather than asserted:

1. **No emitter can play the same take twice in a row.** `PickSource` draws uniformly over
   the *N−1* takes that are not the previous one, so an immediate repeat is impossible
   rather than merely unlikely. A plain uniform draw over seven bird calls repeats
   immediately about one time in seven — exactly often enough to be heard as a loop, and
   exactly the failure the user named. Asserted over 20,000 draws, and again over the
   whole placed set by `create_soundscape_v2.py`.
2. **The continuous beds do not loop either.** A bed plays a take, then **crossfades over
   2.5 s into a different take at a different pitch**, on two voices per emitter. There is
   no seam and no return to the top. After their pitch offsets the beds run 47.9 s,
   50.6 s and 246.9 s, which beat against each other rather than realigning.
3. **Every event is re-randomised on each pass** — which take, at what pitch, at what
   level, after what silence. Gaps are drawn from a *triangular* distribution rather than
   a flat one, because a flat draw produces runs of near-minimum gaps that sound like a
   stutter.
4. **The combined pattern has no beat.** Simulating an hour of the placed set gives 578
   events spread over 173 distinct inter-event interval buckets, the largest holding
   **2.2 %**. A periodic mix piles up in one bucket.

What is **not** claimed: that a 47.9 s wind recording is unrecognisable on its own. Only
an audition settles that. What the numbers show is that nothing in the mix returns to the
same state on a period, and that the specific repetition the user heard is now impossible.

---

## Time of day

`AMikdashSoundscape` binds `AMikdashTimeOfDay::OnTimeOfDayChanged` and reads its
`GetCivilDawnHours` / `GetSunriseHours` / `GetSolarNoonHours` / `GetSunsetHours` /
`GetCivilDuskHours` getters. It never writes to that actor and never recomputes astronomy;
it is a consumer of it. Curves are anchored to those **real solar times**, not to clock
hours, so dawn in December is 06:07 and in June 04:32 and the soundscape follows the sun.

Gain alone is not enough: a bird call at 4 % volume at midnight is still a bird call every
40 seconds. So `LayerIntervalScaleAtTime` also **stretches the silence** by the inverse of
the day gain — at night the bird gap is more than 5× longer, which is what "almost no
birds" actually sounds like.

The brief, as numbers: crowd 0.06 at civil dawn → 1.00 at noon → 0.02 at night; wind bed
0.88 at night, near its highest; city 0.30 at night — present, but a third of its noon
level. Asserted in both the C++ test and the offline gate.

---

## Reverb and occlusion zones

Three zones, evaluated per update against the listener, applied as a dry gain, a low-pass
corner and a submix send:

| Zone | Bounds (cm) | Priority | Dry | Low-pass | Reverb send | Exposure |
|---|---|---|---|---|---|---|
| Heikhal | X −7100…−3550, Y ±900, Z 900…3050 | 10 | 0.10 | 650 Hz | 0.35 | 0.00 |
| Kodesh | X −7100…−5920, Y ±900, Z 900…3050 | 20 | 0.04 | 420 Hz | 0.45 | 0.00 |
| Ulam porch | X −3300…−1400, Y ±2540, Z 625…5915 | 6 | 0.55 | 3200 Hz | 0.18 | 0.25 |

Every bound comes from measured geometry already in the spec
(`geometry.sanctuaryInteriorBox`, `geometry.ulamPorchBounds`, and the manifest's own
59.2 cm amah for the Kodesh's 20-of-60 span). **Only three zones are declared because only
three interior envelopes are measured.** The gate chambers and the colonnades have no
audited bounds, so they read as court; inventing a box for them would be a guess wearing a
number's clothes.

**The blend is layered, not winner-takes-all.** Zones are applied lowest priority first,
so the Kodesh reads as a change on top of the Heikhal, which reads as a change on top of
the court. Writing the test found the bug that makes this necessary: the first version
masked lower zones, and stepping into the outer few centimetres of the Heikhal's blend
shell threw away the court's figure and snapped the mix back to fully open before it
started falling. The margin is measured **inward** from each face, so a zone can never
affect a listener outside its own bounds — the Heikhal's acoustic does not leak into the
court. Filters interpolate in log-frequency, because a linear blend from 20 kHz to 650 Hz
spends almost all its travel where nobody can hear it move.

Occlusion is a single ray per emitter per visit, spread across updates, smoothed into a
fraction; up to 12 dB of attenuation and a pull down to 900 Hz.

### The AudioVolume question

Resolved, in full, in **[`FINDING-AudioVolume-brush.md`](FINDING-AudioVolume-brush.md)**,
with engine file and line numbers for every step. Short version:

> **A Python-spawned `AAudioVolume` DOES get a real cube brush in UE 5.8** —
> `spawn_actor_from_class` routes through `TryPlacingActorFromObject` →
> `FindActorFactoryForActorClass` → the auto-registered `UActorFactoryBoxVolume` for that
> volume class → `CreateBrushForVolumeActor` with a `UCubeBuilder`. It works in a
> `-run=pythonscript -nullrhi` commandlet too, because `LaunchEngineLoop.cpp` calls
> `GEditor->InitEditor` on the commandlet path and that is where the volume factories are
> registered.
>
> **But the failure mode is silent.** If the factory lookup fails, the fallback is
> `GEditor->AddActor`, which builds no brush, logs nothing, and leaves an actor that looks
> perfectly normal and encompasses no point. Direct `UWorld::SpawnActor` on a volume never
> gets a brush at all.

So the zones are **not** delegated to the volume. They live in the actor's data table:
works identically in a packaged build, needs no BSP, reads back as a number, is testable
offline, and does layered blending that `AAudioVolume` cannot. The volume is still placed
as a second, agreeing mechanism, and the release script measures its bounds and records
`audioVolumeBrushFinding` in the receipt on every run — so the claim above stops being a
source reading and becomes a measurement the first time anyone runs it.
`-SoundscapeNoVolume` skips it entirely with no loss of function.

---

## Licences

**Twenty-nine files, twenty-nine verified.** Each verdict rests on an exact quoted
substring from the publisher page snapshot in `evidence/`; the full table with hashes,
quotes and evidence sizes is in `licence-verification.json` and, in the shape the credits
screen reads, in `SourceAssets/third-party/soundscape-v2-audio-manifest.json`.

* 17 ambience and bird recordings: 8 CC0 1.0, 9 Wikimedia author public-domain releases,
  1 CC BY 3.0.
* 12 footstep one-shots: CC0 1.0, one publisher pack, mono downmixes verified in
  `SourceAssets/soundscape-review/offline-verification.json`.
* All 29 hashes on disk match their provenance. All 29 evidence pages are real captures
  (20.9–99.8 KB) with the expected titles and authors, not stubs or error pages.

**Exactly one credit is legally mandatory:** *Cloth Swing Sounds* by **Vinrax**, CC BY 3.0.
Everything else is CC0 or an explicit author dedication and needs none. All are credited
anyway, through `SourceAssets/third-party/`, which
`UMikdashFrontEnd::ReadThirdPartyCredits` reads at run time.

Two honest caveats. The nine Wikimedia "public domain" entries rest on that site's
**author-release template, which is a dedication by a named author and not a Creative
Commons instrument**; no deed URL is claimed for them and the assertion rests on the
captured file page. And all of it is a check of snapshots taken 2026-09-07/08 — no network
call has re-confirmed any page since.

One file was rejected and is kept as evidence of the check: see
[`rejected/WHY-REJECTED.md`](rejected/WHY-REJECTED.md). Its licence was fine; its transient
count was not.

---

## Invocation

```
python Scripts/create_soundscape_v2.py --tests     # offline gate: licences, schedule, C++
python Scripts/create_soundscape_v2.py --table     # the layer table
python Scripts/create_soundscape_v2.py --credits   # the attribution block
python Scripts/release_soundscape_v2.py            # offline consistency check only

# then, and only after MikdashRuntime has been compiled:
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" ^
  "C:\Mikdash\Working-5.8\MikdashCourtyardV3\MikdashCourtyardV3.uproject" ^
  -run=pythonscript ^
  -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_soundscape_v2.py" ^
  -unattended -nullrhi ^
  -abslog="C:/Mikdash/Working-5.8/Soundscape-V2-01.log"
```

Switches: `-SoundscapeImportOnly`, `-SoundscapeNoVolume`, `-SoundscapeNoRuntimeActor`,
`-SoundscapeAmbientFallback`, `-SoundscapeNoCue`, `-SoundscapeDryRun`,
`-SoundscapeRevert[=receipt.json]`, `-SoundscapeRevertAssets`. Run strictly serial; never
while the GUI editor or another native job holds the map. **`AMikdashSoundscape` must be
compiled first** — the script refuses to run without it rather than falling back silently
to the rejected path.

If a save ever returns False, the script now runs `tasklist` first and puts the answer in
the receipt: more than one `UnrealEditor` process means another editor is holding the map,
and that is the cause, not a bug.

---

## What a listener still has to decide

1. **Play all twenty-nine files end to end.** Reject anything with an identifiable voice, a
   vehicle, a siren, an impact or a handling bump. No check in this project can hear those.
2. Stand still in the Azarah for at least ten minutes — longer than the 246.9 s bed — and
   say whether a loop is audible.
3. Walk east gate → outer court → Azarah → Ulam → Heikhal → Kodesh and judge the interior
   transitions. Is 1.4 s too slow or too fast? Is the tail plausible or is it a cathedral?
   Does the Kodesh read as different from the Heikhal, or only as quieter?
4. Judge whether the city hum and the distant murmur read as a town, or as a recognisable
   mall, restaurant and church. If any is identifiable, that source is wrong.
5. Judge crowd density against what is actually on screen. `CrowdHeadCount` is set by
   whoever owns the crowd; if nothing sets it the murmur sits at its authored level, which
   is a fallback, not a design.
6. Decide what the service should sound like. That bank is empty and cannot be filled by
   searching.
7. Check frame time. Twenty-three emitters at two voices each, one occlusion ray per
   update, a reverb submix and a per-update zone evaluation have never been measured.
8. Confirm the old pilot bed is still silent and that nothing else in the level moved.

Until all eight are done, the status is **placed, unheard, and unaccepted**.
