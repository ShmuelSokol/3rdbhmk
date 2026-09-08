# SoundscapeV2 — layered morning soundscape source package

Prepared 2026-09-08. **Nobody has listened to any of this.** Not one of the seventeen
recordings below has been auditioned, and `Scripts/release_soundscape_v2.py` has never
been executed against the editor by its author. Everything recorded here is a licence
check, a container check, a signal measurement or a design intention. None of it is a
hearing, and none of it is acceptance.

The previous ambience was rejected as "just a loop of some white noise and birds and
banging". That bed (`/Game/MikdashV3/Runtime/Audio/SW_CourtyardOriginal_Pilot01`) stays
in the level, stays disabled, and is hashed as a protected asset so this pass cannot
touch it.

## What is here

```
SoundscapeV2/
  sources/            17 publisher-original recordings, byte-for-byte
  sources/*.provenance.json    one per file: licence, URL, hash, duration, signal stats
  evidence/           the publisher page snapshot each licence claim rests on
  rejected/           one candidate the transient rule threw out, kept as evidence
  signal-review.json  every measurement in one table
  fetch-report.json   what was downloaded, when, from where
  native-apply-*.json written by the engine run (none exists yet)
```

Reproduce offline with `python Scripts/release_soundscape_v2.py --fetch --analyse --freeze`.
Nothing outside the source table in that script is ever downloaded.

## Sources, licences and why each one is here

Attribution block for `Content/Distribution/CREDITS.txt`:
`python Scripts/release_soundscape_v2.py --credits`.

| File | Title / author | Licence | Length | Role |
|---|---|---|---|---|
| MildWindBackground_Bashar3A.wav | *Mild Wind Background Noise*, Bashar3A ([OGA](https://opengameart.org/content/mild-wind-background-noise)) | CC0 1.0 | 44.5 s | wind bed, base |
| ParkAmbienceWind_Thimras.wav | *Park ambiences (wind)*, Thimras ([OGA](https://opengameart.org/content/park-ambiences)) | CC0 1.0 | 256.8 s | wind bed, air |
| AmbOutdoor1Loop_Kresiek.wav | *AMB Outside 1*, Kresiek The Furry ([OGA](https://opengameart.org/content/amb-outside-1)) | CC0 1.0 | 29.9 s | wind overlay |
| ShortWind_remaxim.wav | *Short wind sound*, remaxim ([OGA](https://opengameart.org/content/short-wind-sound)) | CC0 1.0 | 4.2 s | wind gust |
| Foret_JosephSardin.wav | *Forêt*, Joseph SARDIN ([Commons](https://commons.wikimedia.org/wiki/File:For%C3%AAt_(Joseph_SARDIN).wav)) | CC0 1.0 | 54.4 s | foliage, off the Mount |
| ClothSwing_Vinrax.wav | *Cloth Swing Sounds*, Vinrax ([OGA](https://opengameart.org/content/cloth-swing-sounds)) | **CC BY 3.0** | 9.9 s | cloth detail |
| CityHum_AlexaMallBerlin_thore.ogg | *1 minute at the Alexa mall in Berlin*, thore ([Commons](https://commons.wikimedia.org/wiki/File:1_minute_at_the_alexa_mall_in_berlin.ogg)) | public domain | 60.1 s | city hum |
| CityHum_Restaurant_stephan.ogg | *Restaurant ambience*, stephan ([Commons](https://commons.wikimedia.org/wiki/File:Restaurant_ambience.ogg)) | public domain | 76.3 s | city hum |
| Murmur_ChurchPeopleReverb_stephan.ogg | *Church, people walking, steps with reverb*, stephan ([Commons](https://commons.wikimedia.org/wiki/File:Church_people_walking_steps_with_reverb.ogg)) | public domain | 30.3 s | distant murmur |
| Murmur_FestivalCrowd_stephan.ogg | *Festival concert people crowd*, stephan ([Commons](https://commons.wikimedia.org/wiki/File:Festival_concert_people_crowd.ogg)) | public domain | 61.2 s | distant murmur |
| Bird_HouseSparrowTschilp_JosephSardin.ogg | *Passer domesticus tschilp call*, Joseph Sardin ([Commons](https://commons.wikimedia.org/wiki/File:Joseph_Sardin_-_Passer_domesticus_tschilp_call.oga)) | CC0 1.0 | 6.2 s | bird one-shot |
| Bird_WoodPigeonSong_Raisanen.ogg | *Columba palumbus birdsong*, Oona Räisänen ([Commons](https://commons.wikimedia.org/wiki/File:Columba_palumbus_birdsong.ogg)) | public domain | 11.6 s | bird one-shot |
| Bird_DoveCooing_mary905.ogg | *Dove cooing*, mary905 ([Commons](https://commons.wikimedia.org/wiki/File:Dove_cooing.ogg)) | public domain | 7.9 s | bird one-shot |
| Bird_WoodPigeonCall_Crunchysaviour.ogg | *Wood pigeon call*, Crunchysaviour ([Commons](https://commons.wikimedia.org/wiki/File:Wood_pigeon_call_128.ogg)) | public domain | 3.1 s | bird one-shot |
| Bird_Pigeon_Gasybeaugosse2020.wav | *Pigeon in Antefasy*, Gasybeaugosse2020 ([Commons](https://commons.wikimedia.org/wiki/File:Pigeon_in_Antefasy.wav)) | CC0 1.0 | 1.9 s | bird one-shot |
| Bird_HoodedCrow_Raisanen.ogg | *Corvus cornix*, Oona Räisänen ([Commons](https://commons.wikimedia.org/wiki/File:Corvus_cornix.ogg)) | public domain | 5.2 s | bird one-shot |
| Bird_Swallow_natalie.ogg | *Baby swallow*, natalie ([Commons](https://commons.wikimedia.org/wiki/File:Baby_swallow_up.ogg)) | public domain | 8.0 s | bird one-shot |

110 MB total, against a 250 MB ceiling. Every direct download URL, licence deed URL,
UTC download time, SHA-256 and container header is in the matching `*.provenance.json`.

The CC0 and CC BY entries carry Creative Commons deed URLs. The Wikimedia entries marked
"public domain" use the site's PD-release template, which is an author release rather
than a CC deed, so **no deed URL is claimed for them** — the assertion rests on the file
page, snapshotted in `evidence/`. The CC BY cloth file is the only one whose credit is
legally mandatory in a shipped build.

`.oga` downloads are stored with a `.ogg` extension because the engine importer keys on
extension. No byte was altered. Nothing was trimmed, normalised, EQ'd, faded or looped.

The WAVs are a mix of 16-bit, 24-bit and one 32-bit float master. `USoundFactory` takes
16-bit PCM directly and pushes everything else through libsndfile, so every imported
`SoundWave` becomes 16-bit regardless. That conversion is the engine's and has not been
verified here; an editor build without `WITH_SNDFILE_IO` would refuse the three
non-16-bit files with *"Only 16 bit WAV source files are supported on this editor
platform"*, and they would need converting by hand first.

## How each file was checked

`--analyse` parses the RIFF/WAVE or Ogg container itself (no audio library), decodes the
samples, and computes in pure Python: a 0.25 s RMS envelope, peak, crest factor, DC
offset, full-scale sample count, the count of windows sitting more than 18 dB above the
median, the count of four-fold level jumps, and a windowed FFT spectral centroid,
85 % rolloff and sub-500 Hz energy fraction.

Ogg cannot be decoded by the standard library. Those four files are decoded through
**ffmpeg into a throwaway 16-bit WAV in the system temp directory** purely to be measured;
the shipped bytes remain the publisher originals. Without ffmpeg they would carry a
container check only, and the script says so in the provenance.

**The bed rule.** Any file used as a continuous layer (wind bed, city hum, murmur,
foliage) is rejected if it shows more than 6 transient windows per minute, more than
4 four-fold level jumps per minute, or a crest factor above 30 dB. That is the numeric
form of "no banging". It is not applied to birds or cloth, which are supposed to be
transients.

The rule actually fired: *Shopping mall, less crowded* (public domain, Commons) measured
10.0 transient windows per minute and was thrown out. Its bytes, provenance and
measurement are kept in `rejected/`; it is never imported.

**What the measurements cannot tell you.** A file with zero flagged windows can still
contain a voice, a dog, a car door, a cough or a microphone bump. Statistics are not
ears. Every one of these seventeen files still needs to be heard end to end.

## The layering, and why it should not read as a loop

Coordinates are UE centimetres, +X east, +Y south, +Z up. The sanctuary interior
(X −7100…−3550, Y ±900, Z 900…3050) is a keep-out box: no emitter is inside it, and birds
obey a box 25 m larger again.

| Layer | Emitters | Behaviour |
|---|---|---|
| wind bed, base | Azarah (900, −900, 1300) | 44.5 s take, looping, pitch 0.93 → 47.9 s period |
| wind bed, air | outer court (3800, 1400, 1500) | 256.8 s take, looping, pitch 1.04 → 246.9 s period |
| wind overlay | north (−1200, −5400), east (6200, 800) | silent 34–96 s / 23–71 s, then one of two takes at a random pitch 0.90–1.08 and level 0.55–1.0 |
| doorway wind | Ulam porch (−3250, 0, 1750) | same base take, pitch 0.88, volume 0.16, audible only within ~25 m |
| city hum | four emitters 270–400 m out, W / SW / S / N | continuous, but the take (60 s or 76 s) and its pitch are re-drawn every pass |
| murmur | Kotel plaza (−21000, 13000), city edge (−6000, 26000) | silent 26–84 s / 37–110 s, then one of two takes |
| bird | 5 emitters, north/south court, north/south chambers, east gate | silent 20–62 / 27–74 / 33–88 / 24–69 / 38–90 s, then one of **seven** calls shuffled without replacement, pitch 0.92–1.08, level 0.5–1.0 |
| foliage | west slope (−13500, −4000), south slope (−2000, 13500) | 54.4 s, looping, pitch 0.97 / 1.05, both outside the measured Mount |
| cloth | east gate, Ulam porch | silent 14–46 s / 19–58 s, then one cloth movement at a random pitch |

Four reasons the loop point should not be findable:

1. **Only two layers loop at all.** Everything else is silence plus an event. There is no
   moment when the whole mix restarts, because most of it was not running.
2. **The two looping beds are 47.9 s and 246.9 s after their pitch offsets.** They share
   no common factor at audible resolution, so the combined texture does not recur inside
   any plausible session. (The script's "realign after N hours" figure is a least common
   multiple of millisecond-quantised lengths — an arithmetic artefact, not a claim that a
   listener could not hear the 47.9 s bed on its own.)
3. **Every non-looping event is re-randomised on each pass** — which recording, at what
   pitch, at what level, after what silence. Five bird emitters on five unrelated windows
   between 20 s and 90 s produce a pattern with no period.
4. **The birds are seven distinct one-shots shuffled without replacement**, so the same
   call cannot fire twice in a row. That is the specific failure the user named.

**Interior.** An `AudioVolume` covering the Heikhal and the Kodesh drops everything
outside it to a tenth of its level and low-passes it at 650 Hz over 1.4 s, and applies a
`ReverbEffect` (2.6 s decay, high frequencies dying faster) at 35 %. Standing inside, the
soundscape is a muffled presence and a tail, not an outdoor bed playing indoors. There is
no interior room tone, because no suitable CC0 room tone was found; the quiet is achieved
by subtraction, not by adding a floor.

**City hum is a gradient, not a gate.** It is present but far down in the courts;
occlusion tracing against the court walls removes another 9 dB and pulls the cutoff to
450 Hz, and the AudioVolume ducks it indoors. Nothing hard-switches it.

## How it is built in the engine, and the honest limitation

`USoundCue` graphs are constructed from Python with `unreal.new_object`, setting
`first_node` and `child_nodes` (both `BlueprintReadOnly`, which the Python property layer
allows because it only blocks `CPF_EditConst`). The chains are
`Looping → [Delay] → Random → Modulator → Wave Player`.

**`USoundCue::AllNodes` and `SoundCueGraph` are plain `UPROPERTY()` with neither
`CPF_Edit` nor `CPF_BlueprintVisible`, and `USoundCue` exposes no `UFUNCTION` that would
populate them.** So the cues *play* correctly — playback walks `FirstNode` — but they open
in the Sound Cue Editor showing only the Output node.

> **Do not open these cues in the Sound Cue Editor and save.** `FSoundCueEditor` compiles
> the visible graph back over `FirstNode` and would erase the chain. Re-run the script
> instead.

MetaSound was considered and not used: building a `UMetaSoundSource` through
`UMetaSoundBuilderSubsystem` needs exact node registry and interface names that could not
be verified without launching the editor, which this task is not permitted to do. The
`SoundCueTemplates` plugin (`USoundCueContainer`, which *would* build a proper editor
graph) is not enabled in `MikdashCourtyardV3.uproject` and has no delay node anyway.

The fallback, `-SoundscapeNoCue` or a failed probe, drives every layer from a plain
looping `SoundWave` with no randomisation. **That fallback would read as a loop.** It
exists so a run can complete and be inspected, not as the design; the receipt states
which path was taken.

Before touching the map the script builds one throwaway cue in a scratch package, because
`USoundCue::PostInitProperties` calls `CreateGraph()`, which dereferences the AudioEditor
module's editor interface with no null check — a missing module kills the process rather
than raising. Doing it first means the map is still untouched when that happens.

## Invocation

```
python Scripts/release_soundscape_v2.py                 # offline consistency check
python Scripts/release_soundscape_v2.py --credits       # attribution block

"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" ^
  "C:\Mikdash\Working-5.8\MikdashCourtyardV3\MikdashCourtyardV3.uproject" ^
  -run=pythonscript ^
  -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_soundscape_v2.py" ^
  -unattended -nullrhi ^
  -abslog="C:/Mikdash/Working-5.8/Soundscape-V2-01.log"
```

Switches: `-SoundscapeImportOnly` (assets only, map untouched), `-SoundscapeNoCue`,
`-SoundscapeNoVolume`, `-SoundscapeDryRun`, `-SoundscapeRevert[=receipt.json]`,
`-SoundscapeRevertAssets`. Run strictly serial; never while the GUI editor or another
native job holds the map.

## What a listener has to decide

1. Play each of the seventeen files end to end. Reject anything with an identifiable
   voice, a vehicle, a siren, an impact or a handling bump. The numbers cannot see these.
2. Stand still in the Azarah for **at least ten minutes** — longer than 246.9 s, so the
   long bed wraps at least twice — and say whether a loop is audible.
3. Walk the east gate → outer court → Azarah → Ulam → Heikhal → Kodesh route and judge the
   interior transition: is the drop to near-silence right, is 1.4 s too slow or too fast,
   is the reverb tail plausible or is it a cathedral?
4. Judge whether the city hum and the murmur read as a distant town or as a recognisable
   mall, restaurant and church. If any of them is identifiable, that source is wrong.
5. Judge bird density. Five emitters on 20–90 s timers may still be too many for a
   hilltop precinct at morning; the timers are the easiest thing to lengthen.
6. Check frame time. Twenty new emitters, two occlusion-tracing layers and a reverb submix
   have never been measured.
7. Confirm the old pilot bed is still silent and that nothing else in the level moved.

Until all seven are done, the status is **placed, unheard, and unaccepted**.
