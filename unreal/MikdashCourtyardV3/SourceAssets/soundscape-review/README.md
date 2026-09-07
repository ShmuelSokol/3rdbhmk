# Recorded sound production review — 2026-09-07

This is a source and offline signal package. Nothing here has been imported, played,
approved by listening, or packaged. Do not enable the wind candidate automatically.
The rejected 32-second synthetic courtyard bed must remain disabled.

## Rights and provenance

- `sources/park_ambience_wind.wav`: Thimras, **Park ambiences**, published 25 July
  2022. [Original publisher page](https://opengameart.org/content/park-ambiences)
  explicitly marks these recordings CC0. Its wind file is a real open-field
  recording in an Adelaide, South Australia public park in winter, recorded at
  48 kHz / 24 bit. Direct public download:
  https://opengameart.org/sites/default/files/park_ambience_wind.wav
  Bytes are preserved without EQ, trimming, gain, or looping. It is a wind
  **candidate**, not a Jerusalem field recording. Wildlife, voices, traffic,
  handling noise and microphone wind still require uninterrupted audition.
- `mono-footsteps/*.wav`: twelve derived recordings from the already present
  `SourceAssets/audio-review/Fantozzi/Wav/*.wav`. Fantozzi recorded them;
  qubodup edited/uploaded the singles. [Publisher page](https://opengameart.org/content/fantozzis-footsteps-grasssand-stone)
  marks the pack CC0 and identifies the original Freesound pack. The only new
  operation is rounded arithmetic stereo-to-mono downmix at the original 44.1 kHz,
  signed PCM16. No generated sound or processing intended to imitate ceremony.
  Stone is a generic hard-surface recording; Sand may also suggest grass. Neither
  identifies footwear, Jerusalem paving composition, or historical acoustics.
- [CC0 1.0 deed](https://creativecommons.org/publicdomain/zero/1.0/) permits copying,
  modifying and distributing, including commercial use. Courtesy credit above is
  retained. The publisher HTML snapshots in `evidence/` preserve asset-specific
  license assertions. The CC deed was inspected through web browsing; a direct
  Python snapshot returned HTTP 403, so no local deed snapshot is claimed.

`signal-review.json` records original and derivative SHA-256 hashes, source links,
dimensions, PCM peak/RMS/DC/full-scale counts, one-second level histories and
unprocessed endpoint discontinuity. These are measurable signals, not a listening
verdict. A zero full-scale count does not prove absence of recording distortion.

## Current runtime findings

Inspected `Plugins/MikdashRuntime/Source/MikdashRuntime/Private/MikdashPlayerController.cpp`:
`UpdateFootsteps` is driven by actual distance and ground state, alternates feet,
and rejects repeating the previous variation on each side. It calls PlaySound2D.
It selects soft only for Terrain and hard only for Architecture/Streets/Buildings
asset prefixes. New platform and arrival asset families will therefore be silent.
Surface membership needs explicit mapping during integration, not inference from
all unrecognized geometry. Room-dependent reverb and NPC spatial playback are absent
from this function. `ApplySoundVolume` mutes the device; that is not evidence that
future audio buses or serialized preferences work correctly.

## Placement and editing contract for the integrating task

1. Keep the existing player cadence logic. Audition the mono downmix against each
   stereo original first: reject phase cancellation or loss of impact. The dry
   stone recordings can serve both interior and exterior; change room response,
   not the shoe recording. Leave the current stereo references intact until tested.
2. For visible residents, use each actor's displacement or verified foot-contact
   animation events, one event owner only. Place a mono event at the contacting
   foot / traced floor point. Start attenuation at 150 cm, fade to silence by
   1800 cm outdoors; treat these as authored mix starting points. Use wall occlusion
   and a maximum of eight simultaneously audible footstep voices, prioritized by
   listener distance. No time-driven footsteps for standing, paused or distant
   abstract residents. Keep per-resident random state so crowds do not share cycles.
3. Preserve left/right no-repeat selection. Begin gain variation at ±1.5 dB and
   pitch variation at ±2%; these are audition candidates, not required effects.
   Do not turn footsteps into a loop. Add per-surface registration for the actual
   finalized platform, stair and arrival meshes after their paths are frozen.
4. Heikhal/Kodesh interior: use dry steps with a room-volume reverb send, starting
   decay 1.2 s / predelay 15 ms / wet send -18 dB; open colonnade starting 0.4 s /
   -24 dB. These are illustrative initial settings, not measured acoustics.
   Blend sends over approximately 1.5 s at openings. Keep sources behind walls
   attenuated and low-passed. Validate against speech intelligibility before adoption.
5. Wind candidate: audition the entire untouched recording before selecting any
   passages. Reject if distinctive birds, identifiable speech, traffic, banging,
   strong rumble or short recurring signatures conflict with the scene. If useful,
   create at least three approved 45–75 s regions with recorded start/end times;
   use irregular ordering, no immediate region repeat, 6–10 s overlap fades and
   very slow level modulation linked to the same wind state as clouds/vegetation.
   Do not reverse the field recording. If it contains too little clean material,
   reject it; do not manufacture a synthetic replacement.
6. Use a quiet non-spatial exterior bed only after approval. Localize a separate
   rustling layer to actual vegetation **outside** the audited Mount enclosure;
   no tree sound emitters on the tree-free Mount. No such rustling layer is supplied.
   Interior wind leakage should originate at actual openings and fade to near
   silence away from them, rather than applying an exterior bed everywhere.
7. Route all new emitters through the existing mute behavior and pause handling.
   On pause, freeze region timing and suppress new contact events. On resume, do
   not emit catch-up steps. Test save/reload of mute and regional random state.

## Honest source gaps and rejected candidates

No clean interior room-tone recording has been selected. Use quiet interiors with
spatial steps pending an appropriate source, not a generated noise floor.
[The Shop](https://opengameart.org/content/the-shop) is publisher-marked CC0 for its
free subset, but its appliance/drone/shop character is unsuitable; not downloaded.
[Stone stair steps](https://opengameart.org/content/stone-stair-steps) is CC-BY-SA 3.0,
not CC0, and has a baked reverberant stair sequence; not downloaded or relabeled.
The bird/river siblings of Park ambiences were deliberately not acquired because
their stated content does not satisfy this pass. No crowd chatter, ritual/service,
transport or period-authentic sound is supplied or claimed.

## Reproduction and acceptance

Run `python Scripts/create_soundscape_review.py --fetch` to obtain the exact
publisher downloads once, or omit `--fetch` for a fully offline rebuild of derived
steps and signal metrics. Requires numpy, already available in local Python.
The script only writes this package. The sources are retained intact.

The integrating task should listen to full wind and all twelve steps, compare
stereo/mono, then test five uninterrupted minutes of outdoor standing and walking,
interior/outdoor transitions, stair contact, several unsynchronized residents,
occlusion, pause/resume, mute/reload, and packaged playback. Log actual approved
time regions and mix settings. Pending these checks, the status is **review-ready
source candidate**, never completed soundscape.
