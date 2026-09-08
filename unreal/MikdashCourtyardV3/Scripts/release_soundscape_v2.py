"""Layered morning soundscape (SoundscapeV2) for the combined IntegratedReviewV2 map.

Replaces nothing by force: the rejected pilot ambience
(/Game/MikdashV3/Runtime/Audio/SW_CourtyardOriginal_Pilot01, already
auto_activate=False) stays in the level and stays disabled. This script imports a
set of CC0 / CC-BY / public-domain field recordings, builds SoundCue graphs that
randomise delay, order, pitch and level, creates SoundAttenuation assets, a
SoundClass, a ReverbEffect and an interior AudioVolume, and places the emitters at
recorded coordinates in the courts, the outer court, the Kotel plaza direction and
the city edge -- never inside the Heikhal/Kodesh interior box.

Every number and coordinate comes from Scripts/release_soundscape_v2.spec.json.
The sources, their provenance and their offline signal statistics live in
SourceAssets/soundscape-review/SoundscapeV2/.

NOTHING HERE HAS BEEN HEARD. No audition, walk test, PIE session or packaged run
has happened. The script has never been executed against the editor by its author.

Offline (no engine) entry points:

  python Scripts/release_soundscape_v2.py --fetch
      Download every source once with curl into SoundscapeV2/sources/, verify the
      RIFF/WAVE or Ogg header, hash it, snapshot the publisher page into
      SoundscapeV2/evidence/ and write <name>.provenance.json beside each file.

  python Scripts/release_soundscape_v2.py --analyse
      Decode each source (ffmpeg is used ONLY to make a throwaway analysis WAV for
      Ogg inputs; the shipped bytes are the publisher's originals) and compute the
      RMS envelope, crest factor, transient-window count and spectral centroid in
      pure Python. Writes the statistics into each provenance file and applies the
      bed acceptance rule.

  python Scripts/release_soundscape_v2.py --freeze
      Record the accepted files, hashes and durations into the spec's "frozen"
      block. offline_check() then refuses to run if a source changed on disk.

  python Scripts/release_soundscape_v2.py            (no switch)
      Offline consistency check: spec vs frozen manifest vs files on disk, plus the
      geometry assertions (no emitter inside the sanctuary interior box, every
      emitter inside the world bounds, attenuation radii sane).

Commandlet invocation (serial, never while the GUI editor or another native job
holds the map):

  "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe"
      "C:\\Mikdash\\Working-5.8\\MikdashCourtyardV3\\MikdashCourtyardV3.uproject"
      -run=pythonscript
      -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_soundscape_v2.py"
      -unattended -nullrhi
      -abslog="C:/Mikdash/Working-5.8/Soundscape-V2-01.log"

Engine switches (read from the engine command line):
  -SoundscapeImportOnly   import the SoundWaves, create the attenuation/class/reverb/cue
                          assets and save them; do NOT touch the map at all.
  -SoundscapeNoCue        skip every SoundCue and drive each emitter with a looping
                          SoundWave instead (no randomisation). Use this if the
                          SoundCue probe reports the AudioEditor module is absent.
  -SoundscapeNoVolume     do not create the interior AudioVolume / ReverbEffect.
  -SoundscapeDryRun       guards, discovery and readback only; no mutation.
  -SoundscapeRevert[=<receipt.json>]
                          destroy every actor tagged ReleaseSoundscapeV2, restore the
                          recorded before-values, save, reopen, read back, write
                          native-revert-<stamp>.json. Created assets are NOT deleted
                          by default (they are inert once unreferenced); pass
                          -SoundscapeRevertAssets to delete them too.

Safety model (release_lighting_polish.py / release_place_assets.py pattern):
  * refuses a wrong project directory, a live game world, dirty packages, a loaded
    world that is not the combined map, or actors already carrying the tag;
  * copies Walkthrough.umap (and any One-File-Per-Actor folders) into
    ReviewCheckpoints/SoundscapeV2-<stamp>/ before any mutation and verifies the copy;
  * probes SoundCue construction in a throwaway package BEFORE the checkpoint, so a
    missing AudioEditor module cannot leave the map half-edited;
  * snapshots every unrelated actor and requires it numerically unchanged before the
    save and after the reopen;
  * saves, reopens, reads every asset path and actor transform back, and writes the
    receipt at start, after each stage and in finally.
"""
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as _np
except Exception:                                  # pragma: no cover - numpy optional
    _np = None

ROOT = Path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3')
SPEC_PATH = ROOT / 'Scripts' / 'release_soundscape_v2.spec.json'
PACKAGE = ROOT / 'SourceAssets' / 'soundscape-review' / 'SoundscapeV2'
SOURCES = PACKAGE / 'sources'
EVIDENCE = PACKAGE / 'evidence'
TARGET = '/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough'

APPLIED_STATUS = 'soundscape_v2_placed_saved_reopened_LISTENING_ACCEPTANCE_PENDING'
IMPORT_ONLY_STATUS = 'soundscape_v2_assets_imported_map_untouched_LISTENING_ACCEPTANCE_PENDING'
REVERTED_STATUS = 'soundscape_v2_reverted_saved_reopened'

USER_AGENT = ('MikdashCourtyardV3-soundscape-fetch/1.0 '
              '(+offline research build; contact shmuelsokol@yahoo.com)')

CC0 = ('CC0 1.0 Universal (Public Domain Dedication)',
       'https://creativecommons.org/publicdomain/zero/1.0/')
CCBY3 = ('Creative Commons Attribution 3.0 Unported (CC BY 3.0)',
         'https://creativecommons.org/licenses/by/3.0/')
PD = ('Public domain (Wikimedia Commons public-domain release; the file page uses a '
      'PD-release template, so no Creative Commons deed URL is asserted)',
      'https://commons.wikimedia.org/wiki/Commons:Licensing#Public_domain')


# --------------------------------------------------------------------------
# The source table. Nothing outside this table is ever downloaded.
# --------------------------------------------------------------------------

SOURCE_TABLE = [
    # ---- wind beds -------------------------------------------------------
    dict(role='windBed', key='wind_mild', file='MildWindBackground_Bashar3A.wav',
         url='https://opengameart.org/sites/default/files/wind%20background%20noise%202.wav',
         page='https://opengameart.org/content/mild-wind-background-noise',
         title='Mild Wind Background Noise', author='Bashar3A', licence=CC0,
         why='Publisher describes a mild, continuous wind background rather than gusts; '
             'wanted as the steady primary bed.'),
    dict(role='windBed', key='wind_outdoor', file='AmbOutdoor1Loop_Kresiek.wav',
         url='https://opengameart.org/sites/default/files/amb_outdoor1_loop.wav',
         page='https://opengameart.org/content/amb-outside-1',
         title='AMB Outside 1', author='Kresiek The Furry', licence=CC0,
         why='Published as a seamless outdoor loop, so its own endpoints do not click; '
             'used as the second bed at a different pitch.'),
    dict(role='windBed', key='wind_park', file='ParkAmbienceWind_Thimras.wav',
         url='https://opengameart.org/sites/default/files/park_ambience_wind.wav',
         page='https://opengameart.org/content/park-ambiences',
         title='Park ambiences (wind)', author='Thimras', licence=CC0,
         localCopy='SourceAssets/soundscape-review/sources/park_ambience_wind.wav',
         why='256 s open-field winter wind recorded at 48 kHz / 24 bit. The longest take '
             'available, so it carries the layer whose repetition period must be longest. '
             'Already present in this repository with a recorded hash; copied, not refetched.'),
    dict(role='windGust', key='wind_short', file='ShortWind_remaxim.wav',
         url='https://opengameart.org/sites/default/files/short%20wind%20sound.wav',
         page='https://opengameart.org/content/short-wind-sound',
         title='Short wind sound', author='remaxim', licence=CC0,
         why='Short single gust; fired as an occasional overlay, never looped.'),
    # ---- foliage / cloth -------------------------------------------------
    dict(role='foliage', key='foliage_forest', file='Foret_JosephSardin.wav',
         url='https://upload.wikimedia.org/wikipedia/commons/6/6b/For%C3%AAt_%28Joseph_SARDIN%29.wav',
         page='https://commons.wikimedia.org/wiki/File:For%C3%AAt_(Joseph_SARDIN).wav',
         title='Foret (forest)', author='Joseph SARDIN (LaSonotheque)', licence=CC0,
         why='Wind moving through foliage. Placed strictly OUTSIDE the measured Mount '
             'footprint, because the audited Mount carries no trees.'),
    dict(role='cloth', key='cloth_swing', file='ClothSwing_Vinrax.wav',
         url='https://opengameart.org/sites/default/files/cloth_sounds.wav',
         page='https://opengameart.org/content/cloth-swing-sounds',
         title='Cloth Swing Sounds', author='Vinrax', licence=CCBY3,
         why='Light cloth movement one-shots for the gate awnings and garments; '
             'CC BY, so the credit line is mandatory.'),
    # ---- footsteps by surface -------------------------------------------
    # Twelve one-shots, six per surface, three per foot. The SURFACE DECISION IS NOT
    # MADE HERE and is not duplicated: MikdashSurfaceAudioRouting.h already routes a
    # floor mesh package path to a Stone / Soft / Silent bank, and AMikdashSoundscape
    # only holds the banks and plays what it is told. What this pass adds is that the
    # step is spatialised at the foot, occluded by the court walls and filtered by the
    # zone the walker is standing in, instead of being a flat 2D sound.
    dict(role='footstepStone', key='footstep_stone_l1', file='Fantozzi-StoneL1-mono.wav',
         url='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         page='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         title="Fantozzi's Footsteps (stone) - left foot, take 1",
         author='Fantozzi (recorded), qubodup (edited and uploaded)', licence=CC0,
         localCopy='SourceAssets/soundscape-review/mono-footsteps/Fantozzi-StoneL1-mono.wav',
         evidenceFile='footsteps_fantozzi.page.html',
         why='Already in this repository as a verified arithmetic stereo-to-mono '
             'downmix of the publisher original (SourceAssets/soundscape-review/'
             'offline-verification.json: 12 originals hash-matched, 12 derivatives '
             'exactly match the downmix, zero full-scale samples). Copied, never '
             'refetched. Footsteps are one-shots, so the bed transient rule does not '
             'apply to them.'),
    dict(role='footstepStone', key='footstep_stone_l2', file='Fantozzi-StoneL2-mono.wav',
         url='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         page='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         title="Fantozzi's Footsteps (stone) - left foot, take 2",
         author='Fantozzi (recorded), qubodup (edited and uploaded)', licence=CC0,
         localCopy='SourceAssets/soundscape-review/mono-footsteps/Fantozzi-StoneL2-mono.wav',
         evidenceFile='footsteps_fantozzi.page.html',
         why='Already in this repository as a verified arithmetic stereo-to-mono '
             'downmix of the publisher original (SourceAssets/soundscape-review/'
             'offline-verification.json: 12 originals hash-matched, 12 derivatives '
             'exactly match the downmix, zero full-scale samples). Copied, never '
             'refetched. Footsteps are one-shots, so the bed transient rule does not '
             'apply to them.'),
    dict(role='footstepStone', key='footstep_stone_l3', file='Fantozzi-StoneL3-mono.wav',
         url='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         page='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         title="Fantozzi's Footsteps (stone) - left foot, take 3",
         author='Fantozzi (recorded), qubodup (edited and uploaded)', licence=CC0,
         localCopy='SourceAssets/soundscape-review/mono-footsteps/Fantozzi-StoneL3-mono.wav',
         evidenceFile='footsteps_fantozzi.page.html',
         why='Already in this repository as a verified arithmetic stereo-to-mono '
             'downmix of the publisher original (SourceAssets/soundscape-review/'
             'offline-verification.json: 12 originals hash-matched, 12 derivatives '
             'exactly match the downmix, zero full-scale samples). Copied, never '
             'refetched. Footsteps are one-shots, so the bed transient rule does not '
             'apply to them.'),
    dict(role='footstepStone', key='footstep_stone_r1', file='Fantozzi-StoneR1-mono.wav',
         url='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         page='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         title="Fantozzi's Footsteps (stone) - right foot, take 1",
         author='Fantozzi (recorded), qubodup (edited and uploaded)', licence=CC0,
         localCopy='SourceAssets/soundscape-review/mono-footsteps/Fantozzi-StoneR1-mono.wav',
         evidenceFile='footsteps_fantozzi.page.html',
         why='Already in this repository as a verified arithmetic stereo-to-mono '
             'downmix of the publisher original (SourceAssets/soundscape-review/'
             'offline-verification.json: 12 originals hash-matched, 12 derivatives '
             'exactly match the downmix, zero full-scale samples). Copied, never '
             'refetched. Footsteps are one-shots, so the bed transient rule does not '
             'apply to them.'),
    dict(role='footstepStone', key='footstep_stone_r2', file='Fantozzi-StoneR2-mono.wav',
         url='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         page='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         title="Fantozzi's Footsteps (stone) - right foot, take 2",
         author='Fantozzi (recorded), qubodup (edited and uploaded)', licence=CC0,
         localCopy='SourceAssets/soundscape-review/mono-footsteps/Fantozzi-StoneR2-mono.wav',
         evidenceFile='footsteps_fantozzi.page.html',
         why='Already in this repository as a verified arithmetic stereo-to-mono '
             'downmix of the publisher original (SourceAssets/soundscape-review/'
             'offline-verification.json: 12 originals hash-matched, 12 derivatives '
             'exactly match the downmix, zero full-scale samples). Copied, never '
             'refetched. Footsteps are one-shots, so the bed transient rule does not '
             'apply to them.'),
    dict(role='footstepStone', key='footstep_stone_r3', file='Fantozzi-StoneR3-mono.wav',
         url='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         page='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         title="Fantozzi's Footsteps (stone) - right foot, take 3",
         author='Fantozzi (recorded), qubodup (edited and uploaded)', licence=CC0,
         localCopy='SourceAssets/soundscape-review/mono-footsteps/Fantozzi-StoneR3-mono.wav',
         evidenceFile='footsteps_fantozzi.page.html',
         why='Already in this repository as a verified arithmetic stereo-to-mono '
             'downmix of the publisher original (SourceAssets/soundscape-review/'
             'offline-verification.json: 12 originals hash-matched, 12 derivatives '
             'exactly match the downmix, zero full-scale samples). Copied, never '
             'refetched. Footsteps are one-shots, so the bed transient rule does not '
             'apply to them.'),
    dict(role='footstepSoft', key='footstep_soft_l1', file='Fantozzi-SandL1-mono.wav',
         url='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         page='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         title="Fantozzi's Footsteps (sand or grass) - left foot, take 1",
         author='Fantozzi (recorded), qubodup (edited and uploaded)', licence=CC0,
         localCopy='SourceAssets/soundscape-review/mono-footsteps/Fantozzi-SandL1-mono.wav',
         evidenceFile='footsteps_fantozzi.page.html',
         why='Already in this repository as a verified arithmetic stereo-to-mono '
             'downmix of the publisher original (SourceAssets/soundscape-review/'
             'offline-verification.json: 12 originals hash-matched, 12 derivatives '
             'exactly match the downmix, zero full-scale samples). Copied, never '
             'refetched. Footsteps are one-shots, so the bed transient rule does not '
             'apply to them.'),
    dict(role='footstepSoft', key='footstep_soft_l2', file='Fantozzi-SandL2-mono.wav',
         url='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         page='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         title="Fantozzi's Footsteps (sand or grass) - left foot, take 2",
         author='Fantozzi (recorded), qubodup (edited and uploaded)', licence=CC0,
         localCopy='SourceAssets/soundscape-review/mono-footsteps/Fantozzi-SandL2-mono.wav',
         evidenceFile='footsteps_fantozzi.page.html',
         why='Already in this repository as a verified arithmetic stereo-to-mono '
             'downmix of the publisher original (SourceAssets/soundscape-review/'
             'offline-verification.json: 12 originals hash-matched, 12 derivatives '
             'exactly match the downmix, zero full-scale samples). Copied, never '
             'refetched. Footsteps are one-shots, so the bed transient rule does not '
             'apply to them.'),
    dict(role='footstepSoft', key='footstep_soft_l3', file='Fantozzi-SandL3-mono.wav',
         url='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         page='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         title="Fantozzi's Footsteps (sand or grass) - left foot, take 3",
         author='Fantozzi (recorded), qubodup (edited and uploaded)', licence=CC0,
         localCopy='SourceAssets/soundscape-review/mono-footsteps/Fantozzi-SandL3-mono.wav',
         evidenceFile='footsteps_fantozzi.page.html',
         why='Already in this repository as a verified arithmetic stereo-to-mono '
             'downmix of the publisher original (SourceAssets/soundscape-review/'
             'offline-verification.json: 12 originals hash-matched, 12 derivatives '
             'exactly match the downmix, zero full-scale samples). Copied, never '
             'refetched. Footsteps are one-shots, so the bed transient rule does not '
             'apply to them.'),
    dict(role='footstepSoft', key='footstep_soft_r1', file='Fantozzi-SandR1-mono.wav',
         url='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         page='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         title="Fantozzi's Footsteps (sand or grass) - right foot, take 1",
         author='Fantozzi (recorded), qubodup (edited and uploaded)', licence=CC0,
         localCopy='SourceAssets/soundscape-review/mono-footsteps/Fantozzi-SandR1-mono.wav',
         evidenceFile='footsteps_fantozzi.page.html',
         why='Already in this repository as a verified arithmetic stereo-to-mono '
             'downmix of the publisher original (SourceAssets/soundscape-review/'
             'offline-verification.json: 12 originals hash-matched, 12 derivatives '
             'exactly match the downmix, zero full-scale samples). Copied, never '
             'refetched. Footsteps are one-shots, so the bed transient rule does not '
             'apply to them.'),
    dict(role='footstepSoft', key='footstep_soft_r2', file='Fantozzi-SandR2-mono.wav',
         url='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         page='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         title="Fantozzi's Footsteps (sand or grass) - right foot, take 2",
         author='Fantozzi (recorded), qubodup (edited and uploaded)', licence=CC0,
         localCopy='SourceAssets/soundscape-review/mono-footsteps/Fantozzi-SandR2-mono.wav',
         evidenceFile='footsteps_fantozzi.page.html',
         why='Already in this repository as a verified arithmetic stereo-to-mono '
             'downmix of the publisher original (SourceAssets/soundscape-review/'
             'offline-verification.json: 12 originals hash-matched, 12 derivatives '
             'exactly match the downmix, zero full-scale samples). Copied, never '
             'refetched. Footsteps are one-shots, so the bed transient rule does not '
             'apply to them.'),
    dict(role='footstepSoft', key='footstep_soft_r3', file='Fantozzi-SandR3-mono.wav',
         url='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         page='https://opengameart.org/content/fantozzis-footsteps-grasssand-stone',
         title="Fantozzi's Footsteps (sand or grass) - right foot, take 3",
         author='Fantozzi (recorded), qubodup (edited and uploaded)', licence=CC0,
         localCopy='SourceAssets/soundscape-review/mono-footsteps/Fantozzi-SandR3-mono.wav',
         evidenceFile='footsteps_fantozzi.page.html',
         why='Already in this repository as a verified arithmetic stereo-to-mono '
             'downmix of the publisher original (SourceAssets/soundscape-review/'
             'offline-verification.json: 12 originals hash-matched, 12 derivatives '
             'exactly match the downmix, zero full-scale samples). Copied, never '
             'refetched. Footsteps are one-shots, so the bed transient rule does not '
             'apply to them.'),
    # ---- distant city ----------------------------------------------------
    dict(role='cityHum', key='city_alexa', file='CityHum_AlexaMallBerlin_thore.ogg',
         url='https://upload.wikimedia.org/wikipedia/commons/f/fd/1_minute_at_the_alexa_mall_in_berlin.ogg',
         page='https://commons.wikimedia.org/wiki/File:1_minute_at_the_alexa_mall_in_berlin.ogg',
         title='1 minute at the Alexa mall in Berlin', author='thore (via Wikimedia Commons)',
         licence=PD,
         why='A large reverberant human space with no music, engines or sirens. At 300 m, '
             'behind the distance low-pass and occlusion filter, it reads as a broadband '
             'town hum rather than as a mall.'),
    dict(role='cityHum', key='city_restaurant', file='CityHum_Restaurant_stephan.ogg',
         url='https://upload.wikimedia.org/wikipedia/commons/b/b5/Restaurant_ambience.ogg',
         page='https://commons.wikimedia.org/wiki/File:Restaurant_ambience.ogg',
         title='Restaurant ambience', author='stephan (via Wikimedia Commons)', licence=PD,
         why='Dense unintelligible murmur, 76 s, no music. Second city-hum take so the two '
             'hum layers never align.'),
    dict(role='murmur', key='murmur_church', file='Murmur_ChurchPeopleReverb_stephan.ogg',
         url='https://upload.wikimedia.org/wikipedia/commons/d/d5/Church_people_walking_steps_with_reverb.ogg',
         page='https://commons.wikimedia.org/wiki/File:Church_people_walking_steps_with_reverb.ogg',
         title='Church, people walking, steps with reverb',
         author='stephan (via Wikimedia Commons)', licence=PD,
         why='People moving inside a large stone building. It is the only murmur candidate found '
             'whose reverberation matches masonry rather than a room, and it passed the transient '
             'rule with zero flagged windows. Replaces the shopping-mall take, which the rule '
             'rejected.'),
    dict(role='murmur', key='murmur_festival', file='Murmur_FestivalCrowd_stephan.ogg',
         url='https://upload.wikimedia.org/wikipedia/commons/1/15/Festival_concert_people_crowd.ogg',
         page='https://commons.wikimedia.org/wiki/File:Festival_concert_people_crowd.ogg',
         title='Festival concert people crowd', author='stephan (via Wikimedia Commons)', licence=PD,
         why='A larger gathering wash for the city edge. Must be auditioned for music bleed; '
             'the publisher page describes crowd only.'),
    # ---- birds (one-shots) ----------------------------------------------
    dict(role='bird', key='bird_sparrow', file='Bird_HouseSparrowTschilp_JosephSardin.ogg',
         url='https://upload.wikimedia.org/wikipedia/commons/a/aa/Joseph_Sardin_-_Passer_domesticus_tschilp_call.oga',
         page='https://commons.wikimedia.org/wiki/File:Joseph_Sardin_-_Passer_domesticus_tschilp_call.oga',
         title='Passer domesticus - tschilp call', author='Joseph Sardin (LaSonotheque)', licence=CC0,
         why='House sparrow, resident in Jerusalem. 6 s, a true one-shot. Downloaded as .oga '
             'and stored with the .ogg extension so the engine importer accepts it; the bytes '
             'are unchanged.'),
    dict(role='bird', key='bird_woodpigeon_song', file='Bird_WoodPigeonSong_Raisanen.ogg',
         url='https://upload.wikimedia.org/wikipedia/commons/1/12/Columba_palumbus_birdsong.ogg',
         page='https://commons.wikimedia.org/wiki/File:Columba_palumbus_birdsong.ogg',
         title='Columba palumbus birdsong', author='Oona Raisanen', licence=PD,
         why='Wood pigeon coo - the low, slow call that keeps a courtyard from sounding empty.'),
    dict(role='bird', key='bird_dove_coo', file='Bird_DoveCooing_mary905.ogg',
         url='https://upload.wikimedia.org/wikipedia/commons/0/05/Dove_cooing.ogg',
         page='https://commons.wikimedia.org/wiki/File:Dove_cooing.ogg',
         title='Dove cooing', author='mary905 (via Wikimedia Commons)', licence=PD,
         why='Second dove voice so the same coo never repeats twice running.'),
    dict(role='bird', key='bird_woodpigeon_call', file='Bird_WoodPigeonCall_Crunchysaviour.ogg',
         url='https://upload.wikimedia.org/wikipedia/commons/9/90/Wood_pigeon_call_128.ogg',
         page='https://commons.wikimedia.org/wiki/File:Wood_pigeon_call_128.ogg',
         title='Wood pigeon call', author='Crunchysaviour (via Wikimedia Commons)', licence=PD,
         why='3 s single call - the shortest one-shot in the set.'),
    dict(role='bird', key='bird_pigeon', file='Bird_Pigeon_Gasybeaugosse2020.wav',
         url='https://upload.wikimedia.org/wikipedia/commons/c/cc/Pigeon_in_Antefasy.wav',
         page='https://commons.wikimedia.org/wiki/File:Pigeon_in_Antefasy.wav',
         title='Pigeon in Antefasy', author='Gasybeaugosse2020', licence=CC0,
         why='1.9 s pigeon, and the only bird supplied as a WAV, so its statistics are '
             'computed from the shipped bytes with no external decoder.'),
    dict(role='bird', key='bird_hooded_crow', file='Bird_HoodedCrow_Raisanen.ogg',
         url='https://upload.wikimedia.org/wikipedia/commons/9/91/Corvus_cornix.ogg',
         page='https://commons.wikimedia.org/wiki/File:Corvus_cornix.ogg',
         title='Corvus cornix', author='Oona Raisanen', licence=PD,
         why='Hooded crow. The species is resident in the Levant and its call carries a long '
             'way across open ground, which is what a hilltop needs.'),
    dict(role='bird', key='bird_swallow', file='Bird_Swallow_natalie.ogg',
         url='https://upload.wikimedia.org/wikipedia/commons/4/46/Baby_swallow_up.ogg',
         page='https://commons.wikimedia.org/wiki/File:Baby_swallow_up.ogg',
         title='Baby swallow', author='natalie (via Wikimedia Commons)', licence=PD,
         why='Stand-in for the common swift, whose every Wikimedia recording is CC BY-SA and '
             'therefore outside the licence set allowed for this project.'),
]

REJECTED_CANDIDATES = [
    dict(what='freesound.org (all of it)', why='The host presented an expired TLS certificate '
         'from this machine (schannel SEC_E_CERT_EXPIRED). Nothing was fetched from it, with or '
         'without certificate checking.'),
    dict(what='archive.org aporee_maps field recordings',
         why='The wind material there is almost entirely CC BY-NC-ND 3.0. NonCommercial and '
             'NoDerivatives are both outside the licence set for this project.'),
    dict(what='Xeno-canto bird recordings mirrored on Wikimedia Commons (including every '
              'Apus apus / common swift recording)',
         why='CC BY-SA. ShareAlike was excluded by the task, so no swift is supplied; the '
             'swallow is the substitute and the gap is stated rather than hidden.'),
    dict(what='OpenGameArt "Free General Ambience Sounds" pack',
         why='CC BY-SA 4.0, despite carrying the best city-hum material found.'),
    dict(what='OpenGameArt "Strong Wind Blowing", "Outdoor Ambiance", "Birdsong background loop"',
         why='CC BY and reachable, but all three are lossy MP3/OGG masters of gustier or '
             'more melodic material than the brief asks for; not downloaded.'),
    dict(what='OpenGameArt "Crowd Shouting/Speaking Ambience" (crowd_shouting_0.ogg, CC0)',
         why='Downloaded to a scratch directory and measured: 27.4 s, crest 9.8 dB, no flagged '
             'transient windows, centroid 2768 Hz - it would have passed the numeric rule. '
             'Rejected on the publisher description alone: the brief asks for a sparse distant '
             'murmur and the title says shouting. Not shipped.'),
    dict(what='Wikimedia Commons "Shopping mall, less crowded" (natalie, public domain)',
         why='Downloaded and measured, then REJECTED BY THE TRANSIENT RULE IN THIS SCRIPT: '
             '10.0 flagged windows per minute against a limit of 6.0 (30.1 s, crest 20.9 dB, '
             'centroid 1631 Hz). Something in it hits far above the median level repeatedly - '
             'exactly the impulsive character the user called banging. The bytes, the provenance '
             'and the measurement are kept in SoundscapeV2/rejected/ as evidence; the file is '
             'never imported.'),
    dict(what='OpenGameArt "AMB Morning Sounds (Perfect Loop)" (amb_morning, CC0, 63.2 s)',
         why='Reachable, CC0, and the only other wind-family take over 60 s that was found. It is '
             'a morning bed with birds baked in. The user rejected "a loop of some white noise and '
             'birds"; a 63 s loop of exactly that is the one thing this pass must not ship. Its '
             'WAV master is also 64-bit float, which neither this script nor the engine importer '
             'reads. Not shipped. This is why only one wind take here exceeds 60 s.'),
    dict(what='Wikimedia Commons "Wind willows 01..12" (public domain, 14-19 MB each)',
         why='Search hits for "wind"; they are LibriVox readings of The Wind in the Willows, i.e. '
             'English speech. Not downloaded.'),
    dict(what='Wikimedia Commons "Perseverance rover SuperCam records wind on Mars" (public domain)',
         why='Real wind, correctly licensed, and completely wrong: a thin-atmosphere Martian '
             'recording in a Jerusalem courtyard is a gimmick. Not downloaded.'),
    dict(what='OpenGameArt "JC Sounds - Nature Ambient Pack Vol 1"',
         why='Promising CC0-filtered search hit, but it is a multi-part 7z FLAC archive and the '
             'licence string could not be read out of the page markup. Not downloaded; worth a '
             'human look if more long wind takes are wanted.'),
    dict(what='OpenGameArt "Scifi City - Ambient Loop"',
         why='CC0 and a good low drone, but a science-fiction city bed has no business in a '
             'Second Temple precinct even if no listener could name it.'),
    dict(what='park_ambience_birds.wav (Thimras, CC0)',
         why='86 MB of continuous birdsong. The user rejected a bird loop; a bird loop is '
             'exactly what this file is.'),
]


# --------------------------------------------------------------------------
# Pure helpers
# --------------------------------------------------------------------------

def zombie_editor_processes():
    """Every UnrealEditor process on this machine, as reported by tasklist.

    A second editor holding the map makes save_current_level() return False with no
    other symptom whatsoever -- no exception, no log line, nothing. This project has
    already lost a full session to that once, which is why Scripts/verify.py checks it
    first and why this is consulted before any save failure is believed.
    """
    try:
        proc = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq UnrealEditor*.exe', '/NH'],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        out = proc.stdout.decode('utf-8', 'replace')
    except Exception as error:
        return {'checked': False, 'error': repr(error), 'processes': []}
    rows = [line.split() for line in out.splitlines() if 'UnrealEditor' in line]
    return {'checked': True,
            'processes': [{'image': r[0], 'pid': r[1]} for r in rows if len(r) >= 2],
            'note': ('When this runs inside a commandlet, this process is one of the listed '
                     'ones, so the expected count is 1 and TWO OR MORE means another editor '
                     'holds the map -- that, not a bug in this script, is why a save failed. '
                     'Run offline from a plain Python interpreter the expected count is 0.')}


def sha256_of(path):
    digest = hashlib.sha256()
    with open(str(path), 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def disk_path(asset_path, extension='uasset'):
    if not asset_path.startswith('/Game/'):
        raise ValueError('Only /Game/ assets are expected: ' + asset_path)
    return ROOT / 'Content' / (asset_path[6:] + '.' + extension)


def load_spec():
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    if spec['targetMap'] != TARGET:
        raise RuntimeError('Spec target differs from script target')
    if Path(spec['projectDir']) != ROOT:
        raise RuntimeError('Spec project directory differs from script root')
    return spec


def utc_stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def point_in_box(point, box, margin=0.0):
    return all(box['min'][i] - margin <= point[i] <= box['max'][i] + margin for i in range(3))


# --------------------------------------------------------------------------
# Container verification and signal statistics (no audio library)
# --------------------------------------------------------------------------

def read_riff_wave(path):
    """Parse RIFF/WAVE headers. Returns (info, data_bytes). Raises on anything else."""
    raw = Path(path).read_bytes()
    if len(raw) < 44 or raw[0:4] != b'RIFF' or raw[8:12] != b'WAVE':
        raise ValueError('not a RIFF/WAVE file (first 12 bytes %r)' % raw[0:12])
    declared = struct.unpack('<I', raw[4:8])[0] + 8
    info = {'container': 'RIFF/WAVE', 'fileBytes': len(raw), 'riffDeclaredBytes': declared,
            'riffSizeConsistent': abs(declared - len(raw)) <= 2, 'chunks': []}
    pos, fmt, data = 12, None, None
    while pos + 8 <= len(raw):
        cid = raw[pos:pos + 4]
        csize = struct.unpack('<I', raw[pos + 4:pos + 8])[0]
        body = raw[pos + 8:pos + 8 + csize]
        info['chunks'].append({'id': cid.decode('ascii', 'replace'), 'bytes': csize})
        if cid == b'fmt ' and len(body) >= 16:
            audio_format, channels, rate, _br, block_align, bits = struct.unpack('<HHIIHH', body[:16])
            fmt = {'audioFormat': audio_format, 'channels': channels, 'sampleRate': rate,
                   'blockAlign': block_align, 'bitsPerSample': bits}
            if audio_format == 0xFFFE and len(body) >= 26:
                fmt['audioFormatEffective'] = struct.unpack('<H', body[24:26])[0]
                fmt['extensible'] = True
        elif cid == b'data':
            data = body
        pos += 8 + csize + (csize & 1)
    if fmt is None or data is None:
        raise ValueError('missing fmt or data chunk')
    effective = fmt.get('audioFormatEffective', fmt['audioFormat'])
    if effective not in (1, 3):
        raise ValueError('unsupported WAVE audio format %d (PCM=1, float=3 only)' % effective)
    if fmt['channels'] < 1 or fmt['channels'] > 8 or fmt['sampleRate'] < 8000:
        raise ValueError('implausible fmt chunk %r' % fmt)
    frame_bytes = (fmt['bitsPerSample'] // 8) * fmt['channels']
    if frame_bytes == 0 or len(data) < frame_bytes:
        raise ValueError('empty or malformed data chunk')
    info.update(fmt)
    info['audioFormatEffective'] = effective
    info['dataBytes'] = len(data)
    info['frames'] = len(data) // frame_bytes
    info['durationSeconds'] = round(info['frames'] / float(fmt['sampleRate']), 6)
    return info, data


def read_ogg(path):
    """Parse Ogg page headers far enough to identify codec, rate, channels and length."""
    raw = Path(path).read_bytes()
    if raw[0:4] != b'OggS':
        raise ValueError('not an Ogg stream (first 4 bytes %r)' % raw[0:4])
    info = {'container': 'Ogg', 'fileBytes': len(raw), 'pages': 0, 'codec': None,
            'sampleRate': None, 'channels': None}
    pos, last_granule = 0, 0
    while True:
        idx = raw.find(b'OggS', pos)
        if idx < 0 or idx + 27 > len(raw):
            break
        granule = struct.unpack('<q', raw[idx + 6:idx + 14])[0]
        segments = raw[idx + 26]
        seg_table = raw[idx + 27:idx + 27 + segments]
        body_start = idx + 27 + segments
        if info['codec'] is None:
            head = raw[body_start:body_start + 32]
            if head[1:7] == b'vorbis':
                info['codec'] = 'vorbis'
                info['channels'] = head[11]
                info['sampleRate'] = struct.unpack('<I', head[12:16])[0]
            elif head[0:8] == b'OpusHead':
                info['codec'] = 'opus'
                info['channels'] = head[9]
                info['sampleRate'] = 48000
        if granule > 0:
            last_granule = granule
        info['pages'] += 1
        pos = body_start + sum(seg_table)
    if info['codec'] is None:
        raise ValueError('Ogg stream carries no Vorbis or Opus identification header')
    if info['pages'] < 3:
        raise ValueError('Ogg stream has only %d pages' % info['pages'])
    if info['sampleRate']:
        info['durationSeconds'] = round(last_granule / float(info['sampleRate']), 6)
    return info


def verify_container(path):
    suffix = Path(path).suffix.lower()
    if suffix == '.wav':
        info, _ = read_riff_wave(path)
        info.pop('chunks', None)
        return info
    if suffix in ('.ogg', '.oga', '.opus'):
        return read_ogg(path)
    raise ValueError('unexpected extension for an audio source: ' + suffix)


def _ffmpeg():
    for name in ('ffmpeg',):
        found = shutil.which(name)
        if found:
            return found
    guess = (Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft' / 'WinGet' / 'Packages' /
             'Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe')
    if guess.exists():
        for candidate in guess.glob('*/bin/ffmpeg.exe'):
            return str(candidate)
    return None


def decode_mono(info, data, max_seconds=None):
    """Interleaved PCM/float bytes -> mono float samples in [-1, 1]."""
    bits, channels, rate = info['bitsPerSample'], info['channels'], info['sampleRate']
    frames = info['frames']
    if max_seconds:
        frames = min(frames, int(max_seconds * rate))
    bps = bits // 8
    body = data[:frames * bps * channels]
    if _np is None:
        return _decode_mono_py(body, bits, channels, info['audioFormatEffective']), rate
    if info['audioFormatEffective'] == 3 and bits == 32:
        flat = _np.frombuffer(body, dtype='<f4').astype(_np.float64)
    elif bits == 8:
        flat = (_np.frombuffer(body, dtype=_np.uint8).astype(_np.float64) - 128.0) / 128.0
    elif bits == 16:
        flat = _np.frombuffer(body, dtype='<i2').astype(_np.float64) / 32768.0
    elif bits == 24:
        b = _np.frombuffer(body, dtype=_np.uint8).reshape(-1, 3).astype(_np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        flat = _np.where(v >= (1 << 23), v - (1 << 24), v).astype(_np.float64) / 8388608.0
    elif bits == 32:
        flat = _np.frombuffer(body, dtype='<i4').astype(_np.float64) / 2147483648.0
    else:
        raise ValueError('unsupported bit depth %d' % bits)
    return flat[:frames * channels].reshape(-1, channels).mean(axis=1), rate


def _decode_mono_py(body, bits, channels, audio_format):
    bps = bits // 8
    scale = float(1 << (bits - 1))
    out = []
    step = bps * channels
    for i in range(0, len(body) - step + 1, step):
        total = 0.0
        for c in range(channels):
            chunk = body[i + c * bps:i + (c + 1) * bps]
            if audio_format == 3 and bits == 32:
                total += struct.unpack('<f', chunk)[0]
            elif bits == 8:
                total += (chunk[0] - 128) / 128.0
            else:
                total += int.from_bytes(chunk, 'little', signed=True) / scale
        out.append(total / channels)
    return out


def _fft(values):
    """Iterative radix-2 FFT (pure Python fallback when numpy is absent)."""
    n = len(values)
    data = [complex(v, 0.0) for v in values]
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            data[i], data[j] = data[j], data[i]
    length = 2
    while length <= n:
        angle = -2.0 * math.pi / length
        wl = complex(math.cos(angle), math.sin(angle))
        for i in range(0, n, length):
            w = complex(1.0, 0.0)
            half = length // 2
            for k in range(i, i + half):
                u, v = data[k], data[k + half] * w
                data[k], data[k + half] = u + v, u - v
                w *= wl
        length <<= 1
    return data


def _db(x):
    return round(20.0 * math.log10(x), 3) if x > 1e-9 else -180.0


def spectral_stats(samples, rate, fft_size=2048, hop_seconds=1.0):
    hop = max(fft_size, int(hop_seconds * rate))
    positions = list(range(0, max(1, len(samples) - fft_size), hop))
    if not positions:
        return {'spectralCentroidHz': None, 'spectralFrames': 0}
    hann = [0.5 - 0.5 * math.cos(2.0 * math.pi * i / (fft_size - 1)) for i in range(fft_size)]
    freqs = [k * rate / float(fft_size) for k in range(fft_size // 2 + 1)]
    centroids, rolloffs, low_fraction = [], [], []
    if _np is not None:
        hann_a, freqs_a = _np.asarray(hann), _np.asarray(freqs)
        low_mask = freqs_a <= 500.0
    for p in positions:
        frame = samples[p:p + fft_size]
        if len(frame) < fft_size:
            break
        if _np is not None:
            mag = _np.abs(_np.fft.rfft(_np.asarray(frame) * hann_a))
            total = float(mag.sum())
            if total <= 1e-12:
                continue
            centroids.append(float((mag * freqs_a).sum() / total))
            cumulative = _np.cumsum(mag)
            idx = int(_np.searchsorted(cumulative, 0.85 * cumulative[-1]))
            rolloffs.append(float(freqs_a[min(idx, len(freqs_a) - 1)]))
            low_fraction.append(float(mag[low_mask].sum() / total))
        else:
            spectrum = _fft([frame[i] * hann[i] for i in range(fft_size)])
            mag = [abs(spectrum[k]) for k in range(fft_size // 2 + 1)]
            total = sum(mag)
            if total <= 1e-12:
                continue
            centroids.append(sum(m * f for m, f in zip(mag, freqs)) / total)
            acc, roll = 0.0, freqs[-1]
            for k, m in enumerate(mag):
                acc += m
                if acc >= 0.85 * total:
                    roll = freqs[k]
                    break
            rolloffs.append(roll)
            low_fraction.append(sum(m for m, f in zip(mag, freqs) if f <= 500.0) / total)
    if not centroids:
        return {'spectralCentroidHz': None, 'spectralFrames': 0}
    ordered = sorted(centroids)
    return {
        'spectralFrames': len(centroids),
        'spectralCentroidHz': round(sum(centroids) / len(centroids), 2),
        'spectralCentroidMedianHz': round(ordered[len(ordered) // 2], 2),
        'spectralCentroidMinHz': round(ordered[0], 2),
        'spectralCentroidMaxHz': round(ordered[-1], 2),
        'spectralCentroidSpreadHz': round(ordered[-1] - ordered[0], 2),
        'spectralRolloff85Hz': round(sum(rolloffs) / len(rolloffs), 2),
        'energyBelow500HzFraction': round(sum(low_fraction) / len(low_fraction), 4),
    }


def envelope_stats(samples, rate, window_seconds=None):
    n = len(samples)
    duration = n / float(rate)
    if window_seconds is None:
        window_seconds = 0.25 if duration >= 12.0 else max(0.01, duration / 48.0)
    win = max(8, int(window_seconds * rate))
    count = n // win
    if count < 8:
        raise ValueError('too few analysis windows (%d) for %.3f s at %d Hz' % (count, duration, rate))
    if _np is not None:
        block = _np.asarray(samples[:count * win]).reshape(count, win)
        rms = _np.sqrt((block * block).mean(axis=1))
        rms_list = [float(x) for x in rms]
        peak = float(_np.abs(samples).max())
        dc = float(_np.mean(samples))
        full_scale = int((_np.abs(samples) >= 0.999).sum())
    else:
        rms_list, peak, full_scale, total = [], 0.0, 0, 0.0
        for w in range(count):
            acc = 0.0
            for v in samples[w * win:(w + 1) * win]:
                acc += v * v
                a = abs(v)
                peak = a if a > peak else peak
                full_scale += 1 if a >= 0.999 else 0
                total += v
            rms_list.append(math.sqrt(acc / win))
        dc = total / float(count * win)

    overall = math.sqrt(sum(v * v for v in rms_list) / len(rms_list))
    ordered = sorted(rms_list)
    median = ordered[len(ordered) // 2]
    floor = ordered[max(0, int(0.10 * len(ordered)))]
    transients = sum(1 for v in rms_list if median > 0 and v > median * 8.0)
    jumps = 0
    for i in range(1, len(rms_list)):
        if rms_list[i - 1] > 1e-7 and rms_list[i] / rms_list[i - 1] >= 4.0:
            jumps += 1
    minutes = count * window_seconds / 60.0
    return {
        'analysisWindowSeconds': round(window_seconds, 5),
        'analysisWindowCount': count,
        'analysedSeconds': round(count * window_seconds, 3),
        'peak': round(peak, 6), 'peakDbfs': _db(peak),
        'rmsDbfs': _db(overall),
        'rmsMedianDbfs': _db(median),
        'rmsTenthPercentileDbfs': _db(floor),
        'rmsMaxDbfs': _db(max(rms_list)),
        'crestFactorDb': round(_db(peak) - _db(overall), 3),
        'levelRangeDb': round(_db(max(rms_list)) - _db(floor), 3),
        'dcOffset': round(dc, 9),
        'fullScaleSamples': full_scale,
        'transientWindows': transients,
        'transientWindowsPerMinute': round(transients / minutes, 3) if minutes else None,
        'rmsJumpsFourFold': jumps,
        'rmsJumpsPerMinute': round(jumps / minutes, 3) if minutes else None,
        'rmsEnvelopeDbfs': [_db(v) for v in rms_list],
    }


def analyse_file(path, ffmpeg=None, max_seconds=420.0):
    """Container check plus, where the samples can be reached, signal statistics."""
    path = Path(path)
    result = {'file': path.name, 'sha256': sha256_of(path), 'bytes': path.stat().st_size,
              'header': verify_container(path), 'decoder': None, 'signal': None, 'signalNote': None}
    if path.suffix.lower() == '.wav':
        info, data = read_riff_wave(path)
        samples, rate = decode_mono(info, data, max_seconds=max_seconds)
        result['decoder'] = 'this script (RIFF/WAVE parsed and decoded in Python)'
        result['signal'] = envelope_stats(samples, rate)
        result['signal'].update(spectral_stats(samples, rate))
        return result
    ffmpeg = ffmpeg or _ffmpeg()
    if not ffmpeg:
        result['signalNote'] = ('Ogg Vorbis: no pure standard-library decoder exists and no ffmpeg '
                                'was found, so only the container header was verified. No RMS '
                                'envelope or spectral centroid is claimed for this file.')
        return result
    handle, tmp = tempfile.mkstemp(suffix='.wav', prefix='soundscape-probe-')
    os.close(handle)
    try:
        command = [ffmpeg, '-v', 'error', '-y', '-i', str(path), '-ac', '1',
                   '-t', str(max_seconds), '-c:a', 'pcm_s16le', tmp]
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0 or not os.path.getsize(tmp):
            result['signalNote'] = 'ffmpeg failed to decode: ' + proc.stderr.decode('utf-8', 'replace')[:400]
            return result
        info, data = read_riff_wave(tmp)
        samples, rate = decode_mono(info, data)
        result['decoder'] = ('ffmpeg -> throwaway 16-bit mono WAV in the system temp directory, '
                             'then decoded and measured by this script. The shipped Ogg bytes are '
                             'the publisher original and were not rewritten.')
        result['signal'] = envelope_stats(samples, rate)
        result['signal'].update(spectral_stats(samples, rate))
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    return result


BED_RULE = {
    'appliesToRoles': ['windBed', 'cityHum', 'murmur', 'foliage'],
    'maxTransientWindowsPerMinute': 6.0,
    'maxRmsJumpsPerMinute': 4.0,
    'maxCrestFactorDb': 30.0,
    'minAnalysedSeconds': 25.0,
    'why': 'A bed layer must be continuous. Windows whose short-term RMS sits more than 18 dB '
           'above the median, or that jump 4x above the previous window, are impulsive events: '
           'door bangs, handling noise, close footfalls. The user rejected the previous ambience '
           'for "banging", so any bed candidate that shows repeated sharp transients is refused '
           'here rather than mixed quietly and hoped for.',
}


def apply_bed_rule(role, signal):
    if role not in BED_RULE['appliesToRoles']:
        return {'applies': False, 'verdict': 'not a bed layer; transient rule not applied'}
    if not signal:
        return {'applies': True, 'verdict': 'undetermined', 'reasons': ['no signal statistics available']}
    reasons = []
    if signal.get('transientWindowsPerMinute', 0) > BED_RULE['maxTransientWindowsPerMinute']:
        reasons.append('transientWindowsPerMinute %.3f > %.1f'
                       % (signal['transientWindowsPerMinute'], BED_RULE['maxTransientWindowsPerMinute']))
    if signal.get('rmsJumpsPerMinute', 0) > BED_RULE['maxRmsJumpsPerMinute']:
        reasons.append('rmsJumpsPerMinute %.3f > %.1f'
                       % (signal['rmsJumpsPerMinute'], BED_RULE['maxRmsJumpsPerMinute']))
    if signal.get('crestFactorDb', 0) > BED_RULE['maxCrestFactorDb']:
        reasons.append('crestFactorDb %.3f > %.1f'
                       % (signal['crestFactorDb'], BED_RULE['maxCrestFactorDb']))
    if signal.get('analysedSeconds', 0) < BED_RULE['minAnalysedSeconds']:
        reasons.append('analysedSeconds %.1f < %.1f'
                       % (signal['analysedSeconds'], BED_RULE['minAnalysedSeconds']))
    return {'applies': True, 'verdict': 'rejected' if reasons else 'accepted', 'reasons': reasons}


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------

def _curl(url, destination, referer=None, retries=3):
    command = ['curl', '-sS', '-L', '--fail', '--max-time', '300', '--retry', str(retries),
               '-A', USER_AGENT, '-o', str(destination), url]
    if referer:
        command[-1:-1] = ['-e', referer]
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError('curl failed (%d) for %s: %s'
                           % (proc.returncode, url, proc.stderr.decode('utf-8', 'replace')[:300]))
    return True


def fetch_all(force=False):
    SOURCES.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg()
    report = {'stamp': utc_stamp(), 'userAgent': USER_AGENT, 'ffmpeg': ffmpeg, 'files': [],
              'rejectedCandidates': REJECTED_CANDIDATES}
    for entry in SOURCE_TABLE:
        target = SOURCES / entry['file']
        row = {'key': entry['key'], 'role': entry['role'], 'file': entry['file'],
               'title': entry['title'], 'author': entry['author'],
               'licence': entry['licence'][0], 'licenceUrl': entry['licence'][1],
               'sourceUrl': entry['url'], 'publisherPage': entry['page'], 'why': entry['why']}
        if target.exists() and not force:
            row['action'] = 'already present'
        elif entry.get('localCopy'):
            source = ROOT / entry['localCopy']
            if not source.exists():
                raise RuntimeError('Local copy missing: ' + str(source))
            shutil.copy2(str(source), str(target))
            row['action'] = 'copied from ' + entry['localCopy']
        else:
            _curl(entry['url'], target, referer=entry['page'])
            row['action'] = 'downloaded'
            row['downloadedUtc'] = datetime.now(timezone.utc).isoformat()
        try:
            header = verify_container(target)
        except Exception as error:
            target.unlink()
            raise RuntimeError('Rejected %s: %s' % (entry['file'], error))
        row['sha256'] = sha256_of(target)
        row['bytes'] = target.stat().st_size
        row['header'] = header
        row['durationSeconds'] = header.get('durationSeconds')
        row.setdefault('downloadedUtc', datetime.fromtimestamp(
            target.stat().st_mtime, timezone.utc).isoformat())
        # publisher page snapshot for the licence assertion
        evidence = EVIDENCE / (entry['key'] + '.page.html')
        if not evidence.exists() or force:
            try:
                _curl(entry['page'], evidence)
                row['evidence'] = str(evidence.relative_to(ROOT))
            except Exception as error:
                row['evidenceError'] = str(error)[:200]
        else:
            row['evidence'] = str(evidence.relative_to(ROOT))
        report['files'].append(row)
        _write_provenance(entry, row, ffmpeg=ffmpeg, analyse=False)
    (PACKAGE / 'fetch-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def _known_download_time(entry, path):
    """Keep the recorded fetch time across re-analysis; fall back to the file mtime."""
    provenance = _provenance_path(entry)
    if provenance.exists():
        try:
            previous = json.loads(provenance.read_text(encoding='utf-8')).get('downloadedUtc')
            if previous:
                return previous
        except Exception:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def _provenance_path(entry):
    return SOURCES / (Path(entry['file']).stem + '.provenance.json')


def _write_provenance(entry, row, ffmpeg=None, analyse=True):
    path = _provenance_path(entry)
    record = {
        'file': entry['file'],
        'role': entry['role'],
        'key': entry['key'],
        'title': entry['title'],
        'author': entry['author'],
        'sourceUrl': entry['url'],
        'publisherPage': entry['page'],
        'licence': entry['licence'][0],
        'licenceUrl': entry['licence'][1],
        'licenceAssertedAt': ('the publisher page snapshot in ../evidence/%s.page.html'
                              % entry['key']),
        'downloadedUtc': row.get('downloadedUtc'),
        'sha256': row.get('sha256'),
        'bytes': row.get('bytes'),
        'durationSeconds': row.get('durationSeconds'),
        'container': row.get('header'),
        'whyChosen': entry['why'],
        'modifications': ('none; the publisher bytes are stored verbatim'
                          + (' (the .oga download is stored with a .ogg extension so the engine '
                             'importer accepts it; no byte was changed)'
                             if entry['url'].endswith('.oga') else '')),
        'auditioned': False,
        'auditionNote': 'NOBODY HAS LISTENED TO THIS FILE. The statistics below are numbers, '
                        'not a hearing.',
    }
    if analyse:
        measured = analyse_file(SOURCES / entry['file'], ffmpeg=ffmpeg)
        record['sha256'] = measured['sha256']
        record['bytes'] = measured['bytes']
        record['container'] = measured['header']
        record['durationSeconds'] = measured['header'].get('durationSeconds')
        record['decoder'] = measured['decoder']
        record['signal'] = measured['signal']
        record['signalNote'] = measured['signalNote']
        record['bedRule'] = apply_bed_rule(entry['role'], measured['signal'])
    elif path.exists():
        previous = json.loads(path.read_text(encoding='utf-8'))
        for key in ('decoder', 'signal', 'signalNote', 'bedRule'):
            if key in previous:
                record[key] = previous[key]
    path.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return record


def analyse_all():
    ffmpeg = _ffmpeg()
    summary = {'stamp': utc_stamp(), 'ffmpeg': ffmpeg, 'bedRule': BED_RULE, 'files': []}
    for entry in SOURCE_TABLE:
        path = SOURCES / entry['file']
        if not path.exists():
            raise RuntimeError('Missing source (run --fetch first): ' + str(path))
        row = {'sha256': sha256_of(path), 'bytes': path.stat().st_size,
               'header': verify_container(path),
               'downloadedUtc': _known_download_time(entry, path)}
        record = _write_provenance(entry, row, ffmpeg=ffmpeg, analyse=True)
        signal = record.get('signal') or {}
        summary['files'].append({
            'key': entry['key'], 'role': entry['role'], 'file': entry['file'],
            'durationSeconds': record['durationSeconds'],
            'sampleRate': record['container'].get('sampleRate'),
            'channels': record['container'].get('channels'),
            'rmsDbfs': signal.get('rmsDbfs'), 'peakDbfs': signal.get('peakDbfs'),
            'crestFactorDb': signal.get('crestFactorDb'),
            'transientWindowsPerMinute': signal.get('transientWindowsPerMinute'),
            'rmsJumpsPerMinute': signal.get('rmsJumpsPerMinute'),
            'spectralCentroidHz': signal.get('spectralCentroidHz'),
            'energyBelow500HzFraction': signal.get('energyBelow500HzFraction'),
            'bedRule': record.get('bedRule'),
            'decoder': record.get('decoder'), 'signalNote': record.get('signalNote'),
        })
    (PACKAGE / 'signal-review.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary


def freeze():
    """Write the accepted-file manifest into the spec's frozen block."""
    spec = json.loads(SPEC_PATH.read_text(encoding='utf-8'))
    frozen = {}
    for entry in SOURCE_TABLE:
        path = SOURCES / entry['file']
        provenance = json.loads(_provenance_path(entry).read_text(encoding='utf-8'))
        verdict = (provenance.get('bedRule') or {}).get('verdict')
        if verdict == 'rejected':
            raise RuntimeError('%s failed the bed rule: %s'
                               % (entry['file'], provenance['bedRule']['reasons']))
        frozen[entry['key']] = {
            'file': entry['file'], 'role': entry['role'],
            'sha256': sha256_of(path), 'bytes': path.stat().st_size,
            'durationSeconds': provenance['durationSeconds'],
            'sampleRate': provenance['container'].get('sampleRate'),
            'channels': provenance['container'].get('channels'),
            'container': provenance['container'].get('container'),
            'bedRuleVerdict': verdict,
        }
    spec['frozen'] = {'stamp': utc_stamp(), 'sources': frozen,
                      'totalBytes': sum(v['bytes'] for v in frozen.values())}
    SPEC_PATH.write_text(json.dumps(spec, indent=2) + '\n', encoding='utf-8')
    return spec['frozen']


# --------------------------------------------------------------------------
# Offline consistency check
# --------------------------------------------------------------------------

def offline_check(spec=None):
    spec = spec or load_spec()
    result = {'spec': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
              'sources': [], 'emitters': [], 'problems': []}
    frozen = spec.get('frozen', {}).get('sources')
    if not frozen:
        result['problems'].append('spec has no frozen source manifest; run --freeze')
        frozen = {}
    total = 0
    for entry in SOURCE_TABLE:
        path = SOURCES / entry['file']
        row = {'key': entry['key'], 'role': entry['role'], 'file': entry['file'],
               'present': path.exists()}
        if not path.exists():
            result['problems'].append('missing source ' + entry['file'])
        else:
            row['sha256'] = sha256_of(path)
            row['bytes'] = path.stat().st_size
            total += row['bytes']
            record = frozen.get(entry['key'])
            row['frozenMatch'] = bool(record and record['sha256'] == row['sha256'])
            if record and not row['frozenMatch']:
                result['problems'].append('source changed since --freeze: ' + entry['file'])
            provenance = _provenance_path(entry)
            row['provenance'] = provenance.exists()
            if not provenance.exists():
                result['problems'].append('missing provenance for ' + entry['file'])
        result['sources'].append(row)
    result['totalSourceBytes'] = total
    result['totalSourceMegabytes'] = round(total / (1024.0 * 1024.0), 2)
    if total > spec['budget']['maxSourceBytes']:
        result['problems'].append('source budget exceeded: %d > %d'
                                  % (total, spec['budget']['maxSourceBytes']))

    interior = spec['geometry']['sanctuaryInteriorBox']
    world = spec['geometry']['worldBounds']
    keep_out = spec['geometry']['sanctuaryKeepOutMarginCm']
    for emitter in spec['emitters']:
        location = emitter['location']
        row = {'label': emitter['label'], 'layer': emitter['layer'], 'location': location}
        row['insideSanctuary'] = point_in_box(location, interior, margin=keep_out)
        row['insideWorld'] = point_in_box(location, world, margin=200000.0)
        if row['insideSanctuary']:
            result['problems'].append('emitter %s is inside the sanctuary keep-out box'
                                      % emitter['label'])
        if not row['insideWorld']:
            result['problems'].append('emitter %s is outside the world bounds' % emitter['label'])
        attenuation = spec['attenuations'][emitter['attenuation']]
        row['radiusCm'] = attenuation['radiusCm']
        row['falloffCm'] = attenuation['falloffDistanceCm']
        row['maxAudibleCm'] = attenuation['radiusCm'] + attenuation['falloffDistanceCm']
        if emitter['layer'] == 'bird' and point_in_box(
                location, interior, margin=spec['geometry']['birdKeepOutMarginCm']):
            result['problems'].append('bird emitter %s is inside the wider bird keep-out box'
                                      % emitter['label'])
        result['emitters'].append(row)

    # every layer must reference sources that exist in the table
    keys = {entry['key'] for entry in SOURCE_TABLE}
    for name, layer in spec['layers'].items():
        for key in layer['sources']:
            if key not in keys:
                result['problems'].append('layer %s references unknown source %s' % (name, key))
    for emitter in spec['emitters']:
        if emitter['layer'] not in spec['layers']:
            result['problems'].append('emitter %s references unknown layer %s'
                                      % (emitter['label'], emitter['layer']))
        if emitter['attenuation'] not in spec['attenuations']:
            result['problems'].append('emitter %s references unknown attenuation %s'
                                      % (emitter['label'], emitter['attenuation']))
        mode = spec['layers'].get(emitter['layer'], {}).get('mode')
        delay = emitter.get('delaySeconds')
        if mode == 'randomGap':
            if not delay or len(delay) != 2 or not 0 < delay[0] < delay[1]:
                result['problems'].append('emitter %s needs a valid delaySeconds [min, max]'
                                          % emitter['label'])
        elif delay:
            result['problems'].append('emitter %s carries delaySeconds but its layer mode is %s'
                                      % (emitter['label'], mode))
    bird_delays = [tuple(e['delaySeconds']) for e in spec['emitters'] if e['layer'] == 'bird']
    if len(set(bird_delays)) != len(bird_delays):
        result['problems'].append('two bird emitters share a delay window; their calls would '
                                  'drift into lockstep')
    for low, high in bird_delays:
        if low < 20.0 or high > 90.0:
            result['problems'].append('bird delay window %s-%s is outside the 20-90 s brief'
                                      % (low, high))

    # -- acoustic zones ----------------------------------------------------
    # The runtime evaluates these with MikdashSoundscape::EvaluateZones, whose contract is
    # asserted by Plugins/MikdashRuntime/Tests/SoundscapeMathTest.cpp. What that test
    # cannot see is whether the numbers in THIS file are sane, so they are checked here.
    result['zones'] = []
    seen_zone_labels = set()
    for zone in spec.get('zones', []):
        row = {'label': zone['label'], 'priority': zone['priority']}
        low, high = zone['minCm'], zone['maxCm']
        row['sizeCm'] = [round(high[i] - low[i], 3) for i in range(3)]
        if any(high[i] <= low[i] for i in range(3)):
            result['problems'].append('zone %s has an inverted or degenerate box' % zone['label'])
        if zone['label'] in seen_zone_labels:
            result['problems'].append('duplicate zone label ' + zone['label'])
        seen_zone_labels.add(zone['label'])
        # BoxMembership clamps the margin to half the box, so a margin wider than that is
        # not an error - but it means the zone never reaches full strength anywhere, which
        # is almost always a typo rather than an intention.
        half = min(0.5 * (high[i] - low[i]) for i in range(3))
        row['blendMarginCm'] = zone['blendMarginCm']
        row['reachesFullStrength'] = zone['blendMarginCm'] <= half
        if not row['reachesFullStrength']:
            result['problems'].append(
                'zone %s has a blend margin of %.0f cm against a half-extent of %.0f cm, so it '
                'never reaches full strength anywhere inside itself'
                % (zone['label'], zone['blendMarginCm'], half))
        if not 0.0 <= zone['dryGain'] <= 1.0:
            result['problems'].append('zone %s dryGain outside 0..1' % zone['label'])
        if not 0.0 <= zone['reverbSend'] <= 1.0:
            result['problems'].append('zone %s reverbSend outside 0..1' % zone['label'])
        if not 0.0 <= zone['exposure'] <= 1.0:
            result['problems'].append('zone %s exposure outside 0..1' % zone['label'])
        if zone['lowPassHz'] < 20.0:
            result['problems'].append('zone %s lowPassHz below 20 Hz' % zone['label'])
        row['insideWorld'] = (point_in_box(low, world, margin=200000.0)
                              and point_in_box(high, world, margin=200000.0))
        if not row['insideWorld']:
            result['problems'].append('zone %s is outside the world bounds' % zone['label'])
        result['zones'].append(row)
    # Two zones at the same priority that overlap are ambiguous: EvaluateZones breaks the
    # tie on membership weight, which is stable but is not a decision anyone authored.
    for i, a in enumerate(spec.get('zones', [])):
        for b in spec.get('zones', [])[i + 1:]:
            if a['priority'] != b['priority']:
                continue
            if all(a['minCm'][k] < b['maxCm'][k] and b['minCm'][k] < a['maxCm'][k]
                   for k in range(3)):
                result['problems'].append(
                    'zones %s and %s overlap at the same priority %d; nothing decides which '
                    'wins' % (a['label'], b['label'], a['priority']))

    # -- the runtime actor -------------------------------------------------
    runtime = spec.get('runtimeActor')
    if not runtime:
        result['problems'].append('spec has no runtimeActor block')
    else:
        result['runtimeActor'] = {'class': runtime['class'], 'label': runtime['label'],
                                  'banks': {}}
        for bank in ('birdCallSources', 'birdWingburstSources', 'footstepStoneSources',
                     'footstepSoftSources', 'serviceSources'):
            missing = [k for k in runtime[bank] if k not in keys]
            result['runtimeActor']['banks'][bank] = {'count': len(runtime[bank]),
                                                     'missing': missing}
            if missing:
                result['problems'].append('runtime bank %s references unknown sources %s'
                                          % (bank, missing))
            # An empty bank is allowed, but only when the spec says out loud why.
            if not runtime[bank] and bank not in runtime.get('emptyBanks', {}):
                result['problems'].append(
                    'runtime bank %s is empty and no reason is recorded in emptyBanks. An empty '
                    'bank is a silent layer; it must be a stated decision, not an oversight.'
                    % bank)
        for key in ('birdAttenuation', 'footstepAttenuation', 'serviceAttenuation'):
            if runtime[key] not in spec['attenuations']:
                result['problems'].append('runtime %s references unknown attenuation %s'
                                          % (key, runtime[key]))
        for emitter in spec['emitters']:
            layer = spec['layers'].get(emitter['layer'], {})
            if 'runtimeLayer' not in layer:
                result['problems'].append('layer %s has no runtimeLayer name' % emitter['layer'])
        if spec.get('submix', {}).get('asset') is None:
            result['problems'].append('spec has no submix block')

    result['repetitionPeriods'] = repetition_report(spec)
    result['ok'] = not result['problems']
    return result


def repetition_report(spec):
    """How long before any two bed layers return to the same relative phase."""
    frozen = spec.get('frozen', {}).get('sources', {})
    rows = []
    for emitter in spec['emitters']:
        layer = spec['layers'][emitter['layer']]
        if layer['mode'] == 'randomGap':
            rows.append({'label': emitter['label'], 'mode': layer['mode'],
                         'delayMinSeconds': emitter['delaySeconds'][0],
                         'delayMaxSeconds': emitter['delaySeconds'][1],
                         'sourceCount': len(layer['sources']),
                         'note': 'randomised silent gap plus a random source, pitch and level '
                                 'every pass; there is no fixed period at all'})
            continue
        if layer['mode'] == 'loopRandom':
            durations = [frozen[k]['durationSeconds'] for k in layer['sources']
                         if k in frozen and frozen[k].get('durationSeconds')]
            rows.append({'label': emitter['label'], 'mode': layer['mode'],
                         'sourceCount': len(layer['sources']),
                         'sourceSeconds': durations,
                         'note': 'continuous, but the take and its pitch are re-drawn on every '
                                 'pass, so the sequence never repeats'})
            continue
        key = layer['sources'][0]
        record = frozen.get(key)
        if not record or not record.get('durationSeconds'):
            continue
        pitch = emitter.get('pitch', 1.0)
        rows.append({'label': emitter['label'], 'mode': 'loop', 'source': key,
                     'sourceSeconds': record['durationSeconds'], 'pitch': pitch,
                     'effectiveLoopSeconds': round(record['durationSeconds'] / pitch, 3)})
    loops = [r['effectiveLoopSeconds'] for r in rows if r.get('mode') == 'loop']
    coincidence = None
    if len(loops) >= 2:
        # least common multiple of the loop lengths quantised to 1 ms
        scaled = [int(round(v * 1000)) for v in loops]
        acc = scaled[0]
        for value in scaled[1:]:
            acc = acc * value // math.gcd(acc, value)
            if acc > 10 ** 12:
                break
        coincidence = acc / 1000.0
    return {
        'layers': rows,
        'loopingBedEffectiveSeconds': loops,
        'allBedsRealignAfterSeconds': coincidence,
        'allBedsRealignAfterHours': round(coincidence / 3600.0, 2) if coincidence else None,
        'realignCaveat': 'The realignment figure is the least common multiple of the pitched loop '
                         'lengths quantised to 1 ms, so its exact magnitude is an arithmetic '
                         'artefact and means nothing on its own. The claim it supports is only '
                         'this: the looping beds are 47.9 s, 50.6 s and 246.9 s long after their '
                         'pitch offsets, share no common factor at audible resolution, and '
                         'therefore never present the same combined texture twice inside any '
                         'plausible session. It is not evidence that a listener cannot hear the '
                         'individual 47.9 s bed repeat; only an audition settles that.'}


# --------------------------------------------------------------------------
# Engine-side work (everything below needs `import unreal`)
# --------------------------------------------------------------------------

def encode_value(ue, value):
    """Typed, comparable, JSON-safe snapshot of an editor property value."""
    if value is None:
        return {'type': 'none', 'value': None}
    if isinstance(value, bool):
        return {'type': 'bool', 'value': bool(value)}
    if isinstance(value, int):
        return {'type': 'int', 'value': int(value)}
    if isinstance(value, float):
        return {'type': 'float', 'value': round(float(value), 6)}
    if isinstance(value, str):
        return {'type': 'str', 'value': value}
    if isinstance(value, ue.Vector):
        return {'type': 'Vector', 'value': [round(value.x, 4), round(value.y, 4), round(value.z, 4)]}
    if isinstance(value, ue.Rotator):
        return {'type': 'Rotator',
                'value': [round(value.pitch, 4), round(value.yaw, 4), round(value.roll, 4)]}
    if isinstance(value, ue.Name):
        return {'type': 'str', 'value': str(value)}
    if isinstance(value, ue.Object):
        return {'type': 'object', 'value': value.get_path_name()}
    if isinstance(value, (list, tuple)):
        return {'type': 'array', 'value': [encode_value(ue, v) for v in value]}
    try:                                             # enums expose a numeric value
        return {'type': 'enum', 'value': int(value.value), 'name': str(value)}
    except Exception:
        return {'type': 'opaque', 'value': str(value)}


def values_match(a, b, tolerance=1e-4):
    if a is None or b is None:
        return False
    if a.get('type') != b.get('type'):
        return False
    if a['type'] == 'float':
        return abs(a['value'] - b['value']) <= tolerance * max(1.0, abs(b['value']))
    if a['type'] == 'array':
        return len(a['value']) == len(b['value']) and all(
            values_match(x, y, tolerance) for x, y in zip(a['value'], b['value']))
    if a['type'] == 'object':
        return a['value'].split('.')[0] == b['value'].split('.')[0]
    return a['value'] == b['value']


def upper_snake(name):
    """'NaturalSound' -> 'NATURAL_SOUND', which is how UE names Python enum members."""
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', name).upper()


def snake_variants(name):
    """Plausible Python property names for one engine UPROPERTY spelling."""
    if name.startswith('b_'):
        return [name, name[2:]]
    return [name, 'b_' + name]


class Soundscape(object):
    """Engine handles, created assets and actors, change log and receipt."""

    def __init__(self, ue, spec):
        self.ue = ue
        self.spec = spec
        self.editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.assets = ue.get_editor_subsystem(ue.EditorAssetSubsystem)
        self.tools = ue.AssetToolsHelpers.get_asset_tools()
        self.world = None
        self.receipt = None
        self.receipt_path = None
        self.created_actors = []
        self.created_assets = []
        self.waves = {}
        self.cues = {}
        self.attenuations = {}
        self.sound_class = None
        self.reverb = None
        self.submix = None
        self.runtime_actor = None
        self.use_cues = True

    # -- receipt -----------------------------------------------------------

    def write_receipt(self):
        self.receipt_path.write_text(json.dumps(self.receipt, indent=2, default=str) + '\n',
                                     encoding='utf-8')

    def note(self, text):
        self.receipt['notes'].append(text)

    # -- property helpers --------------------------------------------------

    def read_prop(self, obj, prop):
        try:
            return encode_value(self.ue, obj.get_editor_property(prop))
        except Exception as error:
            return {'type': 'unavailable', 'error': str(error)}

    def set_prop(self, target, obj, prop, value, required=True, aliases=None):
        """Set the first spelling of `prop` this build accepts; record before/after."""
        record = {'target': target, 'property': prop, 'required': required, 'applied': False}
        names = aliases or snake_variants(prop)
        last_error = None
        for name in names:
            before = self.read_prop(obj, name)
            if before['type'] == 'unavailable':
                last_error = before['error']
                continue
            try:
                obj.set_editor_property(name, value)
            except Exception as error:
                last_error = repr(error)
                continue
            record['resolvedName'] = name
            record['before'] = before
            record['desired'] = encode_value(self.ue, value)
            record['after'] = self.read_prop(obj, name)
            record['applied'] = True
            record['matches'] = values_match(record['after'], record['desired'],
                                             self.spec['verification']['floatRelativeTolerance'])
            self.receipt['changes'].append(record)
            if not record['matches'] and required:
                raise RuntimeError('Readback differs for %s.%s: %r vs %r'
                                   % (target, name, record['after'], record['desired']))
            return record
        record['error'] = 'no accepted spelling among %s (last error: %s)' % (names, last_error)
        self.receipt['changes'].append(record)
        if required:
            raise RuntimeError('Required property %s.%s unavailable: %s' % (target, prop, last_error))
        return record

    def enum_value(self, enum_name, member, fallbacks=()):
        enum = getattr(self.ue, enum_name, None)
        if enum is None:
            raise RuntimeError('Enum %s is not exposed in this build' % enum_name)
        for candidate in (member,) + tuple(fallbacks):
            if hasattr(enum, candidate):
                return getattr(enum, candidate)
        raise RuntimeError('Enum %s has no member among %r'
                           % (enum_name, (member,) + tuple(fallbacks)))

    # -- guards ------------------------------------------------------------

    def guard_world(self, load_target, require_target=True):
        """Project, play state and dirty packages always; the map only when it is touched."""
        ue = self.ue
        if Path(ue.Paths.project_dir()).resolve() != ROOT:
            raise RuntimeError('Wrong project directory: ' + ue.Paths.project_dir())
        if self.editor.get_game_world():
            raise RuntimeError('A game world is active; never mutate during play')
        if (ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()
                or ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
            raise RuntimeError('Dirty packages present before loading the target; refusing to '
                               'discard unsaved work')
        if load_target and not self.levels.load_level(TARGET):
            raise RuntimeError('load_level failed for ' + TARGET)
        self.world = self.editor.get_editor_world()
        if not require_target:
            return
        loaded = self.world.get_outermost().get_name()
        if loaded != TARGET:
            raise RuntimeError('Loaded world %s is not the combined map %s' % (loaded, TARGET))

    def guard_namespace(self):
        root = self.spec['namespace']['root']
        if self.assets.does_directory_exist(root):
            raise RuntimeError('Namespace %s already exists; revert (-SoundscapeRevertAssets) or '
                               'remove it before a fresh apply' % root)

    def discover(self, require_clean=True):
        ue = self.ue
        tag = self.spec['actorTag']
        found = {'AmbientSound': [], 'AudioVolume': [], 'tagged': []}
        for actor in self.actors.get_all_level_actors():
            if isinstance(actor, ue.AmbientSound):
                found['AmbientSound'].append(actor)
            if isinstance(actor, ue.AudioVolume):
                found['AudioVolume'].append(actor)
            if tag in [str(t) for t in actor.tags]:
                found['tagged'].append(actor)
        summary = {key: [{'name': a.get_name(), 'label': a.get_actor_label(),
                          'class': a.get_class().get_name()} for a in value]
                   for key, value in found.items()}
        if require_clean:
            if found['tagged']:
                raise RuntimeError('SoundscapeV2 is already applied (tagged actors present); run '
                                   '-SoundscapeRevert first: %s' % summary['tagged'])
            for key, expected in self.spec['expectedActorCountsBefore'].items():
                if len(found[key]) != expected:
                    raise RuntimeError('Expected %d %s actor(s), found %d: %s'
                                       % (expected, key, len(found[key]), summary[key]))
        return found, summary

    def guard_pilot(self, ambient_actors):
        """The rejected pilot must still be present and must still be silent."""
        ue = self.ue
        cfg = self.spec['existingPilot']
        matches = []
        for actor in ambient_actors:
            component = actor.get_component_by_class(ue.AudioComponent)
            sound = component.get_editor_property('sound')
            if sound and sound.get_path_name().split('.')[0] == cfg['assetPath']:
                matches.append((actor, component))
        if len(matches) != 1:
            raise RuntimeError('Expected exactly one AmbientSound referencing %s, found %d'
                               % (cfg['assetPath'], len(matches)))
        actor, component = matches[0]
        before = bool(component.get_editor_property('auto_activate'))
        record = {'actor': actor.get_path_name(), 'label': actor.get_actor_label(),
                  'sound': cfg['assetPath'], 'autoActivateBefore': before,
                  'destroyed': False, 'moved': False, 'repointed': False}
        if before != cfg['requiredAutoActivate']:
            self.set_prop('pilotAmbience', component, 'auto_activate',
                          cfg['requiredAutoActivate'], required=True)
            record['autoActivateForcedFalse'] = True
        record['autoActivateAfter'] = bool(component.get_editor_property('auto_activate'))
        if record['autoActivateAfter']:
            raise RuntimeError('The rejected pilot ambience is still set to auto activate')
        self.receipt['pilotAmbience'] = record
        return actor

    def snapshot_actors(self, exclude_names):
        rows = {}
        for actor in self.actors.get_all_level_actors():
            name = actor.get_name()
            if name in exclude_names:
                continue
            loc = actor.get_actor_location()
            rot = actor.get_actor_rotation()
            scale = actor.get_actor_scale3d()
            rows[name] = (actor.get_actor_label(), round(loc.x, 3), round(loc.y, 3), round(loc.z, 3),
                          round(rot.pitch, 3), round(rot.yaw, 3), round(rot.roll, 3),
                          round(scale.x, 4), round(scale.y, 4), round(scale.z, 4))
        return rows

    # -- SoundCue probe ----------------------------------------------------

    def probe_soundcue(self):
        """Can this process build a SoundCue at all? Runs BEFORE any map mutation.

        USoundCue::PostInitProperties calls CreateGraph(), which dereferences the
        AudioEditor module's editor interface with no null check, so a missing module
        kills the process instead of raising. Doing this first means the map is still
        untouched when that happens.
        """
        ue = self.ue
        report = {'audioEditorClassVisible': hasattr(ue, 'SoundCueGraph'),
                  'factoryVisible': hasattr(ue, 'SoundCueFactoryNew'),
                  'newObjectAvailable': hasattr(ue, 'new_object'),
                  'created': False, 'firstNodeSettable': False, 'childNodesSettable': False,
                  'error': None}
        if not report['audioEditorClassVisible']:
            report['error'] = ('unreal.SoundCueGraph is not exposed, so the AudioEditor module is '
                               'not loaded and USoundCue::CreateGraph() would crash this process')
            self.receipt['soundCueProbe'] = report
            return False
        if not report['newObjectAvailable']:
            report['error'] = 'unreal.new_object is missing from this Python build'
            self.receipt['soundCueProbe'] = report
            return False
        scratch = self.spec['namespace']['support'] + '/Probe'
        try:
            factory = ue.SoundCueFactoryNew() if report['factoryVisible'] else None
            cue = self.tools.create_asset('SC_SSV2_Probe', scratch, ue.SoundCue, factory)
            if cue is None:
                raise RuntimeError('create_asset returned None')
            report['created'] = True
            node = ue.new_object(ue.SoundNodeLooping, cue)
            child = ue.new_object(ue.SoundNodeDelay, cue)
            node.set_editor_property('child_nodes', [child])
            report['childNodesSettable'] = len(node.get_editor_property('child_nodes')) == 1
            cue.set_editor_property('first_node', node)
            report['firstNodeSettable'] = cue.get_editor_property('first_node') is not None
        except Exception as error:
            report['error'] = repr(error)
        finally:
            # guard_namespace() has already proved the namespace did not exist, so the probe is
            # the only thing under it. Delete the whole root, not just the probe folder, or a
            # probe-stage failure would leave an empty namespace behind and block every re-run.
            root = self.spec['namespace']['root']
            try:
                if self.assets.does_directory_exist(scratch):
                    self.assets.delete_directory(scratch)
                if self.assets.does_directory_exist(root):
                    self.assets.delete_directory(root)
                report['scratchRemoved'] = not self.assets.does_directory_exist(root)
            except Exception as error:
                report['scratchRemoveError'] = repr(error)
        report['usable'] = bool(report['created'] and report['firstNodeSettable']
                                and report['childNodesSettable'])
        self.receipt['soundCueProbe'] = report
        return report['usable']

    # -- assets ------------------------------------------------------------

    def _create_asset(self, name, path, cls, factory_name):
        ue = self.ue
        factory = getattr(ue, factory_name)() if (factory_name and hasattr(ue, factory_name)) else None
        asset = self.tools.create_asset(name, path, cls, factory)
        if asset is None:
            raise RuntimeError('create_asset returned None for %s/%s' % (path, name))
        self.created_assets.append(asset.get_path_name())
        return asset

    def looping_sources(self):
        keys = set()
        for layer in self.spec['layers'].values():
            if layer['mode'] == 'loop':
                keys.update(layer['sources'])
        return keys

    def import_waves(self):
        ue = self.ue
        namespace = self.spec['namespace']['waves']
        prefix = self.spec['namespace']['wavePrefix']
        looping = self.looping_sources()
        frozen = self.spec['frozen']['sources']
        for entry in SOURCE_TABLE:
            key = entry['key']
            source = ROOT / self.spec['sourceFolder'] / entry['file']
            if not source.exists():
                raise RuntimeError('Missing source file: ' + str(source))
            digest = sha256_of(source)
            if frozen[key]['sha256'] != digest:
                raise RuntimeError('Source %s differs from the frozen manifest' % entry['file'])
            task = ue.AssetImportTask()
            task.filename = str(source)
            task.destination_path = namespace
            task.destination_name = prefix + key
            task.automated = True
            task.replace_existing = False
            task.save = False
            self.tools.import_asset_tasks([task])
            objects = [o for o in task.get_objects() if isinstance(o, ue.SoundWave)]
            if len(objects) != 1:
                raise RuntimeError('Import of %s produced %d SoundWave(s)'
                                   % (entry['file'], len(objects)))
            wave = objects[0]
            self.created_assets.append(wave.get_path_name())
            self.set_prop('wave:' + key, wave, 'looping', key in looping, required=True)
            if self.sound_class is not None:
                self.set_prop('wave:' + key, wave, 'sound_class_object', self.sound_class,
                              required=False)
            duration = float(wave.get_editor_property('duration'))
            expected = frozen[key]['durationSeconds']
            if expected and abs(duration - expected) > max(0.5, 0.02 * expected):
                raise RuntimeError('Imported duration %.3f s differs from the measured %.3f s for %s'
                                   % (duration, expected, entry['file']))
            if not self.assets.save_loaded_asset(wave, only_if_is_dirty=False):
                raise RuntimeError('Failed to save ' + wave.get_path_name())
            self.waves[key] = wave
            self.receipt['assets']['waves'].append({
                'key': key, 'role': entry['role'], 'file': entry['file'],
                'path': wave.get_path_name(), 'durationSeconds': round(duration, 6),
                'looping': key in looping, 'sourceSha256': digest,
                'licence': entry['licence'][0], 'licenceUrl': entry['licence'][1],
                'author': entry['author'], 'publisherPage': entry['page']})
        self.write_receipt()

    def create_sound_class(self):
        ue = self.ue
        cfg = self.spec['soundClass']
        asset = self._create_asset(cfg['asset'], self.spec['namespace']['support'],
                                   ue.SoundClass, 'SoundClassFactory')
        properties = asset.get_editor_property('properties')
        for prop, value in cfg['properties'].items():
            self.set_prop('soundClass', properties, prop,
                          value if isinstance(value, bool) else float(value), required=False)
        asset.set_editor_property('properties', properties)
        if not self.assets.save_loaded_asset(asset, only_if_is_dirty=False):
            raise RuntimeError('Failed to save the sound class')
        self.sound_class = asset
        self.receipt['assets']['soundClass'] = asset.get_path_name()
        return asset

    def create_reverb(self):
        ue = self.ue
        cfg = self.spec['reverb']
        asset = self._create_asset(cfg['asset'], self.spec['namespace']['support'],
                                   ue.ReverbEffect, 'ReverbEffectFactory')
        for prop, value in cfg['properties'].items():
            self.set_prop('reverb', asset, prop, float(value), required=False)
        if not self.assets.save_loaded_asset(asset, only_if_is_dirty=False):
            raise RuntimeError('Failed to save the reverb effect')
        self.reverb = asset
        self.receipt['assets']['reverb'] = asset.get_path_name()
        return asset

    def _attenuation_pairs(self, cfg):
        ue = self.ue
        pairs = [
            ('attenuate', True, True),
            ('spatialize', bool(cfg['spatialize']), True),
            ('attenuation_shape', self.enum_value('AttenuationShape', 'SPHERE'), True),
            ('distance_algorithm',
             self.enum_value('AttenuationDistanceModel',
                             upper_snake(cfg['distanceAlgorithm']),
                             fallbacks=(cfg['distanceAlgorithm'].upper(),)), True),
            ('attenuation_shape_extents', ue.Vector(float(cfg['radiusCm']), 0.0, 0.0), True),
            ('falloff_distance', float(cfg['falloffDistanceCm']), True),
            ('d_b_attenuation_at_max', float(cfg['dbAttenuationAtMax']), False),
            ('non_spatialized_radius_start', float(cfg.get('nonSpatializedRadiusStartCm', 0.0)), False),
            ('non_spatialized_radius_end', float(cfg.get('nonSpatializedRadiusEndCm', 0.0)), False),
            ('stereo_spread', float(cfg.get('stereoSpread', 0.0)), False),
            ('attenuate_with_lpf', bool(cfg.get('attenuateWithLpf', False)), False),
            ('enable_occlusion', bool(cfg.get('enableOcclusion', False)), False),
            ('enable_reverb_send', bool(cfg.get('enableReverbSend', False)), False),
        ]
        optional = [
            ('lpf_radius_min', 'lpfRadiusMinCm'), ('lpf_radius_max', 'lpfRadiusMaxCm'),
            ('lpf_frequency_at_min', 'lpfFrequencyAtMin'),
            ('lpf_frequency_at_max', 'lpfFrequencyAtMax'),
            ('occlusion_low_pass_filter_frequency', 'occlusionLowPassFilterFrequency'),
            ('occlusion_volume_attenuation', 'occlusionVolumeAttenuation'),
            ('occlusion_interpolation_time', 'occlusionInterpolationTime'),
            ('reverb_wet_level_min', 'reverbWetLevelMin'),
            ('reverb_wet_level_max', 'reverbWetLevelMax'),
            ('reverb_distance_min', 'reverbDistanceMinCm'),
            ('reverb_distance_max', 'reverbDistanceMaxCm'),
        ]
        for prop, key in optional:
            if key in cfg:
                pairs.append((prop, float(cfg[key]), False))
        if cfg.get('occlusionTraceChannel'):
            pairs.append(('occlusion_trace_channel',
                          self.enum_value('CollisionChannel',
                                          'ECC_' + cfg['occlusionTraceChannel'].upper()), False))
        return pairs

    ATTENUATION_ALIASES = {
        'd_b_attenuation_at_max': ['d_b_attenuation_at_max', 'db_attenuation_at_max',
                                   'dbattenuation_at_max'],
        'non_spatialized_radius_start': ['non_spatialized_radius_start', 'omni_radius'],
        'non_spatialized_radius_end': ['non_spatialized_radius_end'],
    }

    def create_attenuations(self):
        ue = self.ue
        for name, cfg in self.spec['attenuations'].items():
            asset = self._create_asset(cfg['asset'], self.spec['namespace']['support'],
                                       ue.SoundAttenuation, 'SoundAttenuationFactory')
            struct = asset.get_editor_property('attenuation')
            for prop, value, required in self._attenuation_pairs(cfg):
                self.set_prop('attenuation:' + name, struct, prop, value, required=required,
                              aliases=self.ATTENUATION_ALIASES.get(prop))
            asset.set_editor_property('attenuation', struct)
            if not self.assets.save_loaded_asset(asset, only_if_is_dirty=False):
                raise RuntimeError('Failed to save attenuation ' + name)
            self.attenuations[name] = asset
            self.receipt['assets']['attenuations'].append(
                {'name': name, 'path': asset.get_path_name(), 'radiusCm': cfg['radiusCm'],
                 'falloffDistanceCm': cfg['falloffDistanceCm'],
                 'enableOcclusion': bool(cfg.get('enableOcclusion', False))})
        self.write_receipt()

    # -- cue construction --------------------------------------------------

    def _wave_chain(self, cue, key, layer):
        """Modulator -> Wave Player for one source. Returns the top node of the pair."""
        ue = self.ue
        player = ue.new_object(ue.SoundNodeWavePlayer, cue)
        # Only the soft pointer is serialised; USoundNodeWavePlayer::SoundWave is transient,
        # so there is deliberately no fallback to it.
        self.set_prop('cue', player, 'sound_wave_asset_ptr', self.waves[key], required=True,
                      aliases=['sound_wave_asset_ptr'])
        self.set_prop('cue', player, 'looping', False, required=False)
        pitch = layer.get('pitchRange')
        volume = layer.get('volumeRange')
        if not pitch and not volume:
            return player
        modulator = ue.new_object(ue.SoundNodeModulator, cue)
        modulator.set_editor_property('pitch_min', float((pitch or [1.0, 1.0])[0]))
        modulator.set_editor_property('pitch_max', float((pitch or [1.0, 1.0])[1]))
        modulator.set_editor_property('volume_min', float((volume or [1.0, 1.0])[0]))
        modulator.set_editor_property('volume_max', float((volume or [1.0, 1.0])[1]))
        modulator.set_editor_property('child_nodes', [player])
        return modulator

    def build_cue(self, emitter, layer_name, layer):
        """Build the SoundCue for one emitter, or fall back to a plain SoundWave."""
        ue = self.ue
        mode = layer['mode']
        if mode == 'loop' or not self.use_cues:
            return self.waves[layer['sources'][0]]
        short = emitter['label'].replace(self.spec['labelPrefix'] + 'SSV2_', '')
        cue = self._create_asset(self.spec['namespace']['cuePrefix'] + short,
                                 self.spec['namespace']['cues'], ue.SoundCue, 'SoundCueFactoryNew')
        children = [self._wave_chain(cue, key, layer) for key in layer['sources']]
        if len(children) > 1:
            selector = ue.new_object(ue.SoundNodeRandom, cue)
            selector.set_editor_property('child_nodes', children)
            # Weights is load-bearing, not cosmetic. USoundNodeRandom::ChooseNodeIndex sums
            # Weights[] to pick a branch; setting child_nodes directly never calls
            # FixWeightsArray(), so an unset array leaves every weight at zero, the running
            # sum never exceeds the random choice, and the node silently returns index 0
            # forever - i.e. the same recording every single time, which is exactly the
            # failure this whole pass exists to avoid. Required, and length-checked.
            self.set_prop('cue', selector, 'weights', [1.0] * len(children), required=True)
            written = selector.get_editor_property('weights')
            if len(written) != len(children) or any(float(w) <= 0.0 for w in written):
                raise RuntimeError('SoundNodeRandom weights did not take on %s: %r'
                                   % (cue.get_path_name(), [float(w) for w in written]))
            self.set_prop('cue', selector, 'randomize_without_replacement',
                          bool(layer.get('randomizeWithoutReplacement', True)), required=False)
            self.set_prop('cue', selector, 'should_exclude_from_branch_culling', True,
                          required=False)
            self.set_prop('cue', selector, 'preselect_at_level_load', 0, required=False)
            top = selector
        else:
            top = children[0]
        if mode == 'randomGap':
            delay = ue.new_object(ue.SoundNodeDelay, cue)
            delay.set_editor_property('delay_min', float(emitter['delaySeconds'][0]))
            delay.set_editor_property('delay_max', float(emitter['delaySeconds'][1]))
            delay.set_editor_property('child_nodes', [top])
            top = delay
        looping = ue.new_object(ue.SoundNodeLooping, cue)
        self.set_prop('cue', looping, 'loop_indefinitely', True, required=True)
        looping.set_editor_property('child_nodes', [top])
        cue.set_editor_property('first_node', looping)
        if cue.get_editor_property('first_node') is None:
            raise RuntimeError('first_node did not stick on ' + cue.get_path_name())
        if self.sound_class is not None:
            self.set_prop('cue', cue, 'sound_class_object', self.sound_class, required=False)
        self.set_prop('cue', cue, 'exclude_from_random_node_branch_culling', True, required=False)
        if not self.assets.save_loaded_asset(cue, only_if_is_dirty=False):
            raise RuntimeError('Failed to save cue ' + cue.get_path_name())
        self.cues[emitter['label']] = cue
        self.receipt['assets']['cues'].append({
            'emitter': emitter['label'], 'layer': layer_name, 'mode': mode,
            'path': cue.get_path_name(), 'sources': list(layer['sources']),
            'delaySeconds': emitter.get('delaySeconds'),
            'pitchRange': layer.get('pitchRange'), 'volumeRange': layer.get('volumeRange'),
            'graph': self.spec['cueGraph'][mode],
            'editorGraphEmpty': True,
            'editorGraphNote': self.spec['cueGraph']['knownLimitation']})
        return cue

    # -- placement ---------------------------------------------------------

    def spawn_emitters(self):
        ue = self.ue
        interior = self.spec['geometry']['sanctuaryInteriorBox']
        for emitter in self.spec['emitters']:
            layer = self.spec['layers'][emitter['layer']]
            location = [float(v) for v in emitter['location']]
            margin = (self.spec['geometry']['birdKeepOutMarginCm'] if emitter['layer'] == 'bird'
                      else self.spec['geometry']['sanctuaryKeepOutMarginCm'])
            if point_in_box(location, interior, margin=margin):
                raise RuntimeError('%s would be placed inside the sanctuary keep-out box'
                                   % emitter['label'])
            sound = self.build_cue(emitter, emitter['layer'], layer)
            actor = self.actors.spawn_actor_from_class(ue.AmbientSound, ue.Vector(*location))
            if actor is None:
                raise RuntimeError('spawn_actor_from_class returned None for ' + emitter['label'])
            actor.set_actor_label(emitter['label'])
            actor.set_folder_path(self.spec['folder'] + '/' + emitter['layer'])
            actor.set_editor_property('tags', [ue.Name(self.spec['actorTag'])])
            self.created_actors.append(actor)
            component = actor.get_component_by_class(ue.AudioComponent)
            self.set_prop(emitter['label'], component, 'sound', sound, required=True)
            self.set_prop(emitter['label'], component, 'volume_multiplier',
                          float(emitter['volume']), required=True)
            self.set_prop(emitter['label'], component, 'pitch_multiplier',
                          float(emitter.get('pitch', 1.0)), required=True)
            self.set_prop(emitter['label'], component, 'attenuation_settings',
                          self.attenuations[emitter['attenuation']], required=True)
            self.set_prop(emitter['label'], component, 'override_attenuation', False, required=False)
            self.set_prop(emitter['label'], component, 'allow_spatialization', True, required=False)
            self.set_prop(emitter['label'], component, 'auto_activate', True, required=True)
            self.receipt['created'].append({
                'label': emitter['label'], 'name': actor.get_name(), 'class': 'AmbientSound',
                'layer': emitter['layer'], 'mode': layer['mode'], 'location': location,
                'volume': emitter['volume'], 'pitch': emitter.get('pitch', 1.0),
                'sound': sound.get_path_name(),
                'attenuation': self.attenuations[emitter['attenuation']].get_path_name(),
                'folder': self.spec['folder'] + '/' + emitter['layer'],
                'place': emitter.get('place')})
            self.write_receipt()

    def create_submix(self):
        """A SoundSubmix carrying one reverb preset built from RE_SanctuaryStone.

        This is what actually gives the Heikhal a tail. It is created whenever the
        reverb effect is, because the runtime actor sends into it per zone and would
        otherwise have nowhere to send. Failure here is not fatal: the dry gain and the
        low-pass still make the hall read as a hall, just without a tail, and the
        receipt says which.
        """
        ue = self.ue
        cfg = self.spec['submix']
        record = {'label': cfg['asset'], 'class': 'SoundSubmix', 'preset': None,
                  'reverbEffect': self.reverb.get_path_name() if self.reverb else None}
        if self.reverb is None:
            record['skipped'] = 'no reverb effect was created'
            self.receipt['submix'] = record
            return None
        submix = self._create_asset(cfg['asset'], self.spec['namespace']['support'],
                                    ue.SoundSubmix, 'SoundSubmixFactory')
        # The preset is a sub-object of the submix package rather than a separate asset:
        # USoundEffectSubmixPreset has no scripted factory, and an inner object
        # referenced by SubmixEffectChain serialises with its owner.
        preset = ue.new_object(ue.SubmixEffectReverbPreset, submix)
        try:
            preset.set_settings_with_reverb_effect(self.reverb, float(cfg['wetLevel']),
                                                   float(cfg['dryLevel']))
            record['presetConfigured'] = True
        except Exception as error:
            # Older or trimmed builds may not expose the helper. Fall back to leaving the
            # preset at its defaults and say so rather than pretending it was configured.
            record['presetConfigured'] = False
            record['presetError'] = repr(error)[:300]
        self.set_prop('submix', submix, 'submix_effect_chain', [preset], required=True)
        if not self.assets.save_loaded_asset(submix, only_if_is_dirty=False):
            raise RuntimeError('Failed to save the reverb submix')
        record['path'] = submix.get_path_name()
        record['preset'] = preset.get_path_name()
        self.submix = submix
        self.receipt['submix'] = record
        self.receipt['assets']['submix'] = record['path']
        return submix

    def _sound_for(self, key):
        """The imported SoundWave for a source key, or None with a recorded note."""
        wave = self.waves.get(key)
        if wave is None:
            self.note('runtime actor: source key %r has no imported wave; that slot is empty '
                      'and the layer is quieter by exactly one take.' % key)
        return wave

    def spawn_soundscape_actor(self):
        """Spawn and configure AMikdashSoundscape: the whole layered mix, in one actor.

        Everything the previous pass put into twenty AmbientSounds and twenty Python-built
        SoundCues lives here instead. The reasons are in MikdashSoundscape.h, but the
        short one is that a cue built from Python opens empty in the Sound Cue Editor and
        is destroyed by anyone who saves it there, whereas this actor's randomisation is
        ordinary C++ that a person can read, test and change.
        """
        ue = self.ue
        cfg = self.spec['runtimeActor']
        cls = getattr(ue, cfg['class'], None)
        if cls is None:
            raise RuntimeError(
                'unreal.%s is not exposed in this process. The MikdashRuntime plugin must be '
                'COMPILED before this script runs. Refusing to fall back to the rejected '
                'AmbientSound path silently; pass -SoundscapeAmbientFallback if a diagnostic '
                'run without the runtime actor is genuinely wanted.' % cfg['class'])

        actor = self.actors.spawn_actor_from_class(
            cls, ue.Vector(*[float(v) for v in cfg['location']]))
        if actor is None:
            raise RuntimeError('spawn_actor_from_class returned None for ' + cfg['class'])
        actor.set_actor_label(cfg['label'])
        actor.set_folder_path(self.spec['folder'])
        actor.set_editor_property('tags', [ue.Name(self.spec['actorTag'])])
        self.created_actors.append(actor)

        for prop, value in cfg['properties'].items():
            self.set_prop(cfg['label'], actor, prop,
                          value if isinstance(value, bool) else (
                              int(value) if isinstance(value, int) else float(value)),
                          required=False)

        emitters = []
        emitter_records = []
        for emitter in self.spec['emitters']:
            layer = self.spec['layers'][emitter['layer']]
            struct = ue.MikdashSoundEmitter()
            sources = [w for w in (self._sound_for(k) for k in layer['sources']) if w is not None]
            if not sources:
                raise RuntimeError('Emitter %s has no imported sources' % emitter['label'])
            delay = emitter.get('delaySeconds') or [0.0, 0.0]
            pitch = layer.get('pitchRange') or [emitter.get('pitch', 1.0),
                                                emitter.get('pitch', 1.0)]
            level = layer.get('volumeRange') or [1.0, 1.0]
            looping = layer['mode'] in ('loop', 'loopRandom')
            fields = [
                ('label', ue.Name(emitter['label'])),
                ('layer', self.enum_value('MikdashSoundLayer', layer['runtimeLayer'])),
                ('location_cm', ue.Vector(*[float(v) for v in emitter['location']])),
                ('sources', sources),
                ('attenuation', self.attenuations[emitter['attenuation']]),
                ('base_volume', float(emitter['volume'])),
                ('b_looping', bool(looping)),
                ('min_gap_seconds', float(delay[0])),
                ('max_gap_seconds', float(delay[1])),
                ('min_pitch', float(pitch[0])),
                ('max_pitch', float(pitch[1])),
                ('min_level', float(level[0])),
                ('max_level', float(level[1])),
                ('b_height_varying', bool(emitter.get('heightVarying', False))),
                ('b_occlude', bool(emitter.get('occlude', False))),
                ('b_crowd_scaled', bool(emitter.get('crowdScaled', False))),
                ('place', str(emitter.get('place', ''))),
            ]
            for name, value in fields:
                self.set_prop(emitter['label'] + ':struct', struct, name, value, required=True)
            emitters.append(struct)
            emitter_records.append({
                'label': emitter['label'], 'layer': layer['runtimeLayer'],
                'location': [float(v) for v in emitter['location']],
                'sourceCount': len(sources),
                'sources': [w.get_path_name() for w in sources],
                'looping': looping, 'gapSeconds': [float(delay[0]), float(delay[1])],
                'pitchRange': [float(pitch[0]), float(pitch[1])],
                'levelRange': [float(level[0]), float(level[1])],
                'baseVolume': float(emitter['volume']),
                'heightVarying': bool(emitter.get('heightVarying', False)),
                'occlude': bool(emitter.get('occlude', False)),
                'crowdScaled': bool(emitter.get('crowdScaled', False))})
        self.set_prop(cfg['label'], actor, 'emitters', emitters, required=True)

        zones = []
        zone_records = []
        for zone in self.spec['zones']:
            struct = ue.MikdashAcousticZone()
            for name, value in (
                    ('label', ue.Name(zone['label'])),
                    ('min_cm', ue.Vector(*[float(v) for v in zone['minCm']])),
                    ('max_cm', ue.Vector(*[float(v) for v in zone['maxCm']])),
                    ('blend_margin_cm', float(zone['blendMarginCm'])),
                    ('priority', int(zone['priority'])),
                    ('dry_gain', float(zone['dryGain'])),
                    ('low_pass_hz', float(zone['lowPassHz'])),
                    ('reverb_send', float(zone['reverbSend'])),
                    ('exposure', float(zone['exposure']))):
                self.set_prop(zone['label'], struct, name, value, required=True)
            zones.append(struct)
            zone_records.append({k: zone[k] for k in
                                 ('label', 'minCm', 'maxCm', 'blendMarginCm', 'priority',
                                  'dryGain', 'lowPassHz', 'reverbSend', 'exposure', 'basis')})
        self.set_prop(cfg['label'], actor, 'zones', zones, required=True)

        banks = {}
        for prop, spec_key in (('bird_call_sounds', 'birdCallSources'),
                               ('bird_wingburst_sounds', 'birdWingburstSources'),
                               ('footstep_stone_sounds', 'footstepStoneSources'),
                               ('footstep_soft_sounds', 'footstepSoftSources'),
                               ('service_sounds', 'serviceSources')):
            waves = [w for w in (self._sound_for(k) for k in cfg[spec_key]) if w is not None]
            self.set_prop(cfg['label'], actor, prop, waves, required=True)
            banks[spec_key] = [w.get_path_name() for w in waves]
            if not waves:
                self.note('runtime actor bank %s is EMPTY. %s'
                          % (spec_key, cfg['emptyBanks'].get(spec_key, 'No reason recorded.')))
        for prop, spec_key in (('bird_attenuation', 'birdAttenuation'),
                               ('footstep_attenuation', 'footstepAttenuation'),
                               ('service_attenuation', 'serviceAttenuation')):
            self.set_prop(cfg['label'], actor, prop, self.attenuations[cfg[spec_key]],
                          required=True)
        if getattr(self, 'submix', None) is not None:
            self.set_prop(cfg['label'], actor, 'reverb_submix', self.submix, required=True)
        else:
            self.note('runtime actor: no reverb submix was created, so the interior zones apply '
                      'their dry-gain drop and low-pass but no reverb tail.')

        record = {'label': cfg['label'], 'name': actor.get_name(), 'class': cfg['class'],
                  'location': [float(v) for v in cfg['location']],
                  'emitterCount': len(emitters), 'zoneCount': len(zones),
                  'emitters': emitter_records, 'zones': zone_records, 'banks': banks,
                  'submix': self.receipt.get('submix', {}).get('path')}
        self.runtime_actor = actor
        self.receipt['created'].append(record)
        self.receipt['runtimeActor'] = record
        self.write_receipt()
        return actor

    def create_audio_volume(self):
        ue = self.ue
        cfg = self.spec['audioVolume']
        target = [float(v) for v in cfg['halfExtentsCm']]
        actor = self.actors.spawn_actor_from_class(
            ue.AudioVolume, ue.Vector(*[float(v) for v in cfg['location']]))
        if actor is None:
            raise RuntimeError('spawn_actor_from_class returned None for the AudioVolume')
        actor.set_actor_label(cfg['label'])
        actor.set_folder_path(self.spec['folder'])
        actor.set_editor_property('tags', [ue.Name(self.spec['actorTag'])])
        self.created_actors.append(actor)
        record = {'label': cfg['label'], 'name': actor.get_name(), 'class': 'AudioVolume',
                  'location': [float(v) for v in cfg['location']],
                  'desiredHalfExtentsCm': target, 'scaleIterations': []}
        tolerance = self.spec['verification']['volumeScaleToleranceCm']
        scale = [1.0, 1.0, 1.0]
        converged = False
        for _ in range(6):
            _origin, extent = actor.get_actor_bounds(False)
            measured = [float(extent.x), float(extent.y), float(extent.z)]
            record['scaleIterations'].append(
                {'scale': [round(v, 6) for v in scale],
                 'measuredHalfExtentsCm': [round(v, 3) for v in measured]})
            if all(abs(measured[i] - target[i]) <= tolerance for i in range(3)):
                converged = True
                break
            if any(measured[i] <= 1e-3 for i in range(3)):
                # THE 5.8 TRAP, caught rather than assumed away. Source chain and failure
                # modes: SourceAssets/soundscape-review/SoundscapeV2/
                # FINDING-AudioVolume-brush.md. Short version: spawn_actor_from_class
                # routes through FLevelEditorViewportClient::TryPlacingActorFromObject,
                # which finds the auto-registered UActorFactoryBoxVolume for this volume
                # class and builds a real cube brush. When that lookup fails the fallback
                # is GEditor->AddActor, which builds NO brush, logs NOTHING, and leaves an
                # actor that looks fine and encompasses no point. Zero bounds is the only
                # visible symptom, so it is checked here.
                record['brushBuilt'] = False
                record['finding'] = ('No brush. FindActorFactoryForActorClass returned nothing '
                                     'for this class, so the AddActor fallback ran. The zones '
                                     'are unaffected: they are carried by AMikdashSoundscape, '
                                     'not by this volume. Re-run with -SoundscapeNoVolume.')
                self.receipt['audioVolumeBrushFinding'] = record['finding']
                raise RuntimeError('The AudioVolume brush has a zero extent; cannot scale it')
            scale = [scale[i] * target[i] / measured[i] for i in range(3)]
            actor.set_actor_scale3d(ue.Vector(*scale))
        if not converged:
            raise RuntimeError('AudioVolume scale did not converge: %r' % record['scaleIterations'])
        record['brushBuilt'] = True
        record['finding'] = ('A brush WAS built. spawn_actor_from_class went through '
                             'UActorFactoryBoxVolume::PostSpawnActor -> CreateBrushForVolumeActor '
                             'with a UCubeBuilder, exactly as the source reading in '
                             'FINDING-AudioVolume-brush.md predicted, and in a -nullrhi '
                             'commandlet. The measured half-extents below are the proof.')
        self.receipt['audioVolumeBrushFinding'] = record['finding']
        record['finalScale'] = [round(v, 6) for v in scale]
        _origin, extent = actor.get_actor_bounds(False)
        record['finalHalfExtentsCm'] = [round(float(extent.x), 3), round(float(extent.y), 3),
                                        round(float(extent.z), 3)]

        self.set_prop(cfg['label'], actor, 'enabled', bool(cfg['enabled']), required=False)
        self.set_prop(cfg['label'], actor, 'priority', float(cfg['priority']), required=False)
        settings = actor.get_editor_property('settings')
        for prop, value in cfg['reverbSettings'].items():
            self.set_prop(cfg['label'] + ':reverb', settings, prop,
                          value if isinstance(value, bool) else float(value), required=False)
        if self.reverb is not None:
            self.set_prop(cfg['label'] + ':reverb', settings, 'reverb_effect', self.reverb,
                          required=True)
        actor.set_editor_property('settings', settings)
        zone = actor.get_editor_property('ambient_zone_settings')
        for prop, value in cfg['interiorSettings'].items():
            self.set_prop(cfg['label'] + ':interior', zone, prop, float(value), required=False)
        actor.set_editor_property('ambient_zone_settings', zone)
        record['reverbEffect'] = self.reverb.get_path_name() if self.reverb else None
        self.receipt['created'].append(record)
        self.receipt['audioVolume'] = record
        self.write_receipt()

    # -- save / reopen / readback -----------------------------------------

    def find_actor(self, name, label):
        candidates = []
        for actor in self.actors.get_all_level_actors():
            if actor.get_name() == name:
                return actor
            if label and actor.get_actor_label() == label:
                candidates.append(actor)
        return candidates[0] if len(candidates) == 1 else None

    def save_and_reopen(self):
        ue = self.ue
        dirty = ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()
        if dirty:
            raise RuntimeError('Dirty content packages before the map save (assets must be saved '
                               'explicitly): %s' % [p.get_name() for p in dirty])
        if not self.levels.save_current_level():
            # Never believe a failed save without checking this first.
            zombies = zombie_editor_processes()
            self.receipt['zombieEditorCheck'] = zombies
            self.write_receipt()
            others = [p for p in zombies.get('processes', [])]
            raise RuntimeError(
                'save_current_level returned False. UnrealEditor processes on this machine: %r. '
                'One of those is this process. If there is more than one, another editor is '
                'holding the map and THAT is the cause -- close it and re-run; the map is '
                'unchanged and the checkpoint is in the receipt. If there is exactly one, the '
                'save failed for another reason and the log is the next place to look.'
                % (others,))
        self.receipt['mapSaved'] = True
        self.write_receipt()
        if ue.EditorLoadingAndSavingUtils.get_dirty_map_packages():
            raise RuntimeError('Map still dirty after save')
        if not self.levels.load_level(TARGET):
            raise RuntimeError('Reopen failed')
        self.world = self.editor.get_editor_world()

    def readback(self):
        """After the reopen: every emitter, its sound, attenuation and levels."""
        ue = self.ue
        failures = []
        for record in self.receipt['created']:
            actor = self.find_actor(record['name'], record['label'])
            record['presentAfterReopen'] = actor is not None
            if actor is None:
                failures.append('missing after reopen: ' + record['label'])
                continue
            record['tagAfterReopen'] = self.spec['actorTag'] in [str(t) for t in actor.tags]
            location = actor.get_actor_location()
            record['locationAfterReopen'] = [round(location.x, 3), round(location.y, 3),
                                             round(location.z, 3)]
            if any(abs(record['locationAfterReopen'][i] - record['location'][i]) > 0.5
                   for i in range(3)):
                failures.append('moved after reopen: ' + record['label'])
            if record['class'] != 'AmbientSound':
                continue
            component = actor.get_component_by_class(ue.AudioComponent)
            sound = component.get_editor_property('sound')
            record['soundAfterReopen'] = sound.get_path_name() if sound else None
            attenuation = component.get_editor_property('attenuation_settings')
            record['attenuationAfterReopen'] = attenuation.get_path_name() if attenuation else None
            record['volumeAfterReopen'] = round(
                float(component.get_editor_property('volume_multiplier')), 6)
            record['pitchAfterReopen'] = round(
                float(component.get_editor_property('pitch_multiplier')), 6)
            record['autoActivateAfterReopen'] = bool(component.get_editor_property('auto_activate'))
            if (not record['soundAfterReopen']
                    or record['soundAfterReopen'].split('.')[0] != record['sound'].split('.')[0]):
                failures.append('sound lost on ' + record['label'])
            if (not record['attenuationAfterReopen']
                    or record['attenuationAfterReopen'].split('.')[0]
                    != record['attenuation'].split('.')[0]):
                failures.append('attenuation lost on ' + record['label'])
            if abs(record['volumeAfterReopen'] - record['volume']) > 1e-4:
                failures.append('volume differs on ' + record['label'])
            if not record['autoActivateAfterReopen']:
                failures.append('auto activate lost on ' + record['label'])
        for cue in self.receipt['assets']['cues']:
            asset = self.assets.load_asset(cue['path'])
            cue['loadsAfterReopen'] = asset is not None
            if asset is None:
                failures.append('cue missing: ' + cue['path'])
                continue
            first = asset.get_editor_property('first_node')
            cue['firstNodeAfterReopen'] = first.get_class().get_name() if first else None
            if first is None:
                failures.append('cue graph empty after reopen: ' + cue['path'])
        for wave in self.receipt['assets']['waves']:
            asset = self.assets.load_asset(wave['path'])
            wave['loadsAfterReopen'] = asset is not None
            if asset is None:
                failures.append('wave missing: ' + wave['path'])
        # the rejected pilot must still be there and still silent
        pilot = self.receipt.get('pilotAmbience')
        if pilot:
            still = None
            for actor in self.actors.get_all_level_actors():
                if not isinstance(actor, ue.AmbientSound):
                    continue
                component = actor.get_component_by_class(ue.AudioComponent)
                sound = component.get_editor_property('sound')
                if sound and sound.get_path_name().split('.')[0] == pilot['sound']:
                    still = bool(component.get_editor_property('auto_activate'))
            pilot['presentAfterReopen'] = still is not None
            pilot['autoActivateAfterReopen'] = still
            if still is None:
                failures.append('the rejected pilot ambience actor disappeared')
            elif still:
                failures.append('the rejected pilot ambience is enabled after reopen')

        # -- the runtime actor: every emitter and zone read back off the reopened
        # -- actor, numerically, not by trusting what was written.
        record = self.receipt.get('runtimeActor')
        if record:
            actor = self.find_actor(record['name'], record['label'])
            record['presentAfterReopen'] = actor is not None
            if actor is None:
                failures.append('runtime soundscape actor missing after reopen')
            else:
                emitters = actor.get_editor_property('emitters')
                zones = actor.get_editor_property('zones')
                record['emitterCountAfterReopen'] = len(emitters)
                record['zoneCountAfterReopen'] = len(zones)
                if len(emitters) != record['emitterCount']:
                    failures.append('runtime actor emitter count changed after reopen')
                if len(zones) != record['zoneCount']:
                    failures.append('runtime actor zone count changed after reopen')
                readback = []
                for index, struct in enumerate(emitters):
                    expected = record['emitters'][index] if index < len(record['emitters']) else {}
                    location = struct.get_editor_property('location_cm')
                    row = {'label': str(struct.get_editor_property('label')),
                           'location': [round(float(location.x), 3), round(float(location.y), 3),
                                        round(float(location.z), 3)],
                           'sourceCount': len(struct.get_editor_property('sources')),
                           'baseVolume': round(float(
                               struct.get_editor_property('base_volume')), 6),
                           'looping': bool(struct.get_editor_property('b_looping')),
                           'minGap': round(float(
                               struct.get_editor_property('min_gap_seconds')), 6),
                           'maxGap': round(float(
                               struct.get_editor_property('max_gap_seconds')), 6),
                           'occlude': bool(struct.get_editor_property('b_occlude')),
                           'heightVarying': bool(
                               struct.get_editor_property('b_height_varying')),
                           'crowdScaled': bool(struct.get_editor_property('b_crowd_scaled'))}
                    readback.append(row)
                    if expected:
                        if row['sourceCount'] != expected['sourceCount']:
                            failures.append('emitter %s lost sources' % row['label'])
                        if abs(row['baseVolume'] - expected['baseVolume']) > 1e-4:
                            failures.append('emitter %s volume differs' % row['label'])
                        if any(abs(row['location'][i] - expected['location'][i]) > 0.5
                               for i in range(3)):
                            failures.append('emitter %s moved' % row['label'])
                        if row['looping'] != expected['looping']:
                            failures.append('emitter %s looping flag differs' % row['label'])
                record['emittersAfterReopen'] = readback
                zone_readback = []
                for index, struct in enumerate(zones):
                    expected = record['zones'][index] if index < len(record['zones']) else {}
                    low = struct.get_editor_property('min_cm')
                    high = struct.get_editor_property('max_cm')
                    row = {'label': str(struct.get_editor_property('label')),
                           'minCm': [round(float(low.x), 3), round(float(low.y), 3),
                                     round(float(low.z), 3)],
                           'maxCm': [round(float(high.x), 3), round(float(high.y), 3),
                                     round(float(high.z), 3)],
                           'priority': int(struct.get_editor_property('priority')),
                           'dryGain': round(float(struct.get_editor_property('dry_gain')), 6),
                           'lowPassHz': round(float(
                               struct.get_editor_property('low_pass_hz')), 3),
                           'reverbSend': round(float(
                               struct.get_editor_property('reverb_send')), 6),
                           'exposure': round(float(struct.get_editor_property('exposure')), 6)}
                    zone_readback.append(row)
                    if expected:
                        for key, field in (('dryGain', 'dryGain'), ('lowPassHz', 'lowPassHz'),
                                           ('reverbSend', 'reverbSend'), ('exposure', 'exposure')):
                            if abs(row[key] - float(expected[field])) > 1e-3:
                                failures.append('zone %s %s differs' % (row['label'], key))
                        if any(abs(row['minCm'][i] - expected['minCm'][i]) > 0.5
                               or abs(row['maxCm'][i] - expected['maxCm'][i]) > 0.5
                               for i in range(3)):
                            failures.append('zone %s bounds moved' % row['label'])
                record['zonesAfterReopen'] = zone_readback
                submix = actor.get_editor_property('reverb_submix')
                record['submixAfterReopen'] = submix.get_path_name() if submix else None
                for prop in ('bird_call_sounds', 'bird_wingburst_sounds', 'footstep_stone_sounds',
                             'footstep_soft_sounds', 'service_sounds'):
                    record.setdefault('banksAfterReopen', {})[prop] = [
                        w.get_path_name() for w in actor.get_editor_property(prop) if w]
                if len(record['banksAfterReopen']['bird_call_sounds']) != len(
                        record['banks']['birdCallSources']):
                    failures.append('bird call bank changed after reopen')
                if len(record['banksAfterReopen']['footstep_stone_sounds']) != len(
                        record['banks']['footstepStoneSources']):
                    failures.append('footstep stone bank changed after reopen')
        return failures


# --------------------------------------------------------------------------
# Checkpoint, receipt, run and revert
# --------------------------------------------------------------------------

def _checkpoint(spec, prefix, stamp, map_file, map_sha_before):
    checkpoint = Path(spec['checkpointRoot']) / (prefix + stamp)
    checkpoint.mkdir(parents=True, exist_ok=False)
    shutil.copy2(str(map_file), str(checkpoint / map_file.name))
    if sha256_of(checkpoint / map_file.name) != map_sha_before:
        raise RuntimeError('Checkpoint copy hash differs')
    copied = []
    for folder_name in ('__ExternalActors__', '__ExternalObjects__'):
        external = ROOT / 'Content' / folder_name / TARGET[6:]
        if external.exists():
            shutil.copytree(str(external), str(checkpoint / folder_name / TARGET[6:]))
            copied.append(str(external))
    return checkpoint, copied


def _protected_hashes(spec):
    hashes = {}
    for asset in spec['protectedMaps']:
        path = disk_path(asset, 'umap')
        if not path.exists():
            raise RuntimeError('Required protected map missing: ' + str(path))
        hashes[asset] = sha256_of(path)
    for asset in spec.get('protectedAssets', []):
        path = disk_path(asset)
        if not path.exists():
            raise RuntimeError('Required protected asset missing: ' + str(path))
        hashes[asset] = sha256_of(path)
    return hashes


def _fresh_receipt_path(spec, prefix, stamp):
    folder = ROOT / spec['receiptFolder']
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (prefix + stamp + '.json')
    if path.exists():
        raise RuntimeError('Receipt already exists: ' + str(path))
    return path


def latest_apply_receipt(spec):
    folder = ROOT / spec['receiptFolder']
    candidates = sorted(folder.glob(spec['receiptPrefix'] + '*.json'))
    for path in reversed(candidates):
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if data.get('mapSaved'):
            return path, data
    raise RuntimeError('No saved apply receipt found in ' + str(folder))


def _credits_lines(spec):
    """Attribution block a human can paste into Content/Distribution/CREDITS.txt."""
    lines = ['SoundscapeV2 recordings (imported into %s):' % spec['namespace']['root']]
    for entry in SOURCE_TABLE:
        lines.append('  %s - "%s" by %s - %s - %s'
                     % (entry['file'], entry['title'], entry['author'],
                        entry['licence'][0], entry['page']))
    lines.append('  CC BY entries above REQUIRE this credit to be shipped with the build.')
    return lines


def run(load_target=True, import_only=False, use_cues=True, make_volume=True, dry_run=False,
        ambient_fallback=False, runtime_actor=True):
    """Import, build, place, save, reopen, read back. Returns the receipt dict."""
    import unreal as ue
    spec = load_spec()
    offline = offline_check(spec)
    if not offline['ok']:
        raise RuntimeError('Offline check failed: %s' % offline['problems'][:8])

    scape = Soundscape(ue, spec)
    # -SoundscapeImportOnly never touches the map, so it neither loads it nor demands that
    # it be the world already open.
    scape.guard_world(load_target and not import_only, require_target=not import_only)
    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = _protected_hashes(spec)
    stamp = utc_stamp()
    scape.receipt_path = _fresh_receipt_path(spec, spec['receiptPrefix'], stamp)
    scape.receipt = {
        'status': 'started', 'stamp': stamp, 'map': TARGET, 'mapFile': str(map_file),
        'mapSha256Before': map_sha_before, 'protectedSha256Before': protected,
        'specFile': str(SPEC_PATH), 'specSha256': sha256_of(SPEC_PATH),
        'engineVersion': ue.SystemLibrary.get_engine_version(),
        'switches': {'importOnly': import_only, 'useCues': use_cues, 'audioVolume': make_volume,
                     'dryRun': dry_run, 'ambientFallback': ambient_fallback,
                     'runtimeActor': runtime_actor},
        'zombieEditorCheckAtStart': zombie_editor_processes(),
        'offlineCheck': offline, 'actorsBefore': {}, 'pilotAmbience': None,
        'assets': {'waves': [], 'cues': [], 'attenuations': [], 'soundClass': None,
                   'reverb': None, 'submix': None},
        'runtimeActor': None, 'submix': None, 'audioVolumeBrushFinding': None,
        'created': [], 'changes': [], 'notes': [], 'errors': [], 'mapSaved': False,
        'checkpoint': None, 'soundCueProbe': None, 'audioVolume': None,
        'creditsBlock': _credits_lines(spec),
        'auditioned': False,
        'auditionStatement': 'NOBODY HAS LISTENED TO THIS. Every check in this receipt is a '
                             'numeric readback of a property or an asset path. No audition, walk '
                             'test, PIE session, voice-count measurement or packaged run has '
                             'happened, and no claim about how this sounds is made anywhere.',
        'limitations': list(spec['limitations']),
    }
    scape.write_receipt()

    try:
        if import_only:
            scape.note('-SoundscapeImportOnly: the map is neither loaded nor inspected, so no '
                       'actor discovery, no pilot-ambience guard and no checkpoint are performed. '
                       'Only assets are created.')
        else:
            found, summary = scape.discover(require_clean=True)
            scape.receipt['actorsBefore'] = summary
            scape.receipt['actorCountBefore'] = len(scape.actors.get_all_level_actors())
            scape.guard_pilot(found['AmbientSound'])
        scape.guard_namespace()

        scape.use_cues = bool(use_cues) and scape.probe_soundcue()
        if use_cues and not scape.use_cues:
            scape.note('SoundCue construction is NOT available in this process (%s). Every layer '
                       'fell back to a plain looping SoundWave, which has no randomisation and '
                       'WOULD read as a loop. Treat this run as diagnostic, not as the design.'
                       % (scape.receipt['soundCueProbe'] or {}).get('error'))
        elif not use_cues:
            scape.note('-SoundscapeNoCue was requested; the randomised cue graphs were skipped and '
                       'every layer is a plain looping SoundWave. This is the fallback, not the '
                       'design.')
        scape.write_receipt()

        if dry_run:
            scape.receipt['status'] = 'dry_run_no_mutation_map_unchanged'
            return scape.receipt

        baseline = None
        if not import_only:
            baseline = scape.snapshot_actors(set())
            scape.receipt['unrelatedActorBaselineCount'] = len(baseline)
            checkpoint, copied = _checkpoint(spec, spec['checkpointPrefix'], stamp, map_file,
                                             map_sha_before)
            scape.receipt['checkpoint'] = str(checkpoint)
            scape.receipt['oneFilePerActorFoldersCopied'] = copied
            scape.receipt['status'] = 'checkpointed_apply_started'
            scape.write_receipt()

        scape.create_sound_class()
        if make_volume or runtime_actor:
            scape.create_reverb()
            scape.create_submix()
        scape.create_attenuations()
        scape.import_waves()
        scape.write_receipt()

        if import_only:
            scape.receipt['status'] = IMPORT_ONLY_STATUS
            scape.receipt['mapBytesChanged'] = sha256_of(map_file) != map_sha_before
            if scape.receipt['mapBytesChanged']:
                raise RuntimeError('-SoundscapeImportOnly changed the map on disk')
            return scape.receipt

        if ambient_fallback:
            scape.note('-SoundscapeAmbientFallback: the rejected AmbientSound-plus-SoundCue path '
                       'was placed as well as, or instead of, the runtime actor. This is a '
                       'diagnostic mode. Running both at once plays every layer twice.')
            scape.spawn_emitters()
        if runtime_actor:
            scape.spawn_soundscape_actor()
        if not ambient_fallback and not runtime_actor:
            raise RuntimeError('Nothing would be placed: the runtime actor is off and the '
                               'ambient fallback is off.')
        if make_volume:
            scape.create_audio_volume()
        scape.write_receipt()

        created_names = set(a.get_name() for a in scape.created_actors)
        current = scape.snapshot_actors(created_names)
        changed = [name for name, row in baseline.items() if current.get(name) != row]
        if changed or len(current) != len(baseline):
            raise RuntimeError('Unrelated actors changed before save: %s'
                               % (changed[:10] or 'count differs'))
        scape.receipt['unrelatedActorsUnchangedBeforeSave'] = True

        scape.save_and_reopen()
        scape.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        scape.write_receipt()

        reopened = scape.snapshot_actors(created_names)
        changed = [name for name, row in baseline.items() if reopened.get(name) != row]
        if changed:
            raise RuntimeError('Unrelated actors differ after reopen: %s' % changed[:10])
        scape.receipt['unrelatedActorsUnchangedAfterReopen'] = True

        failures = scape.readback()
        scape.receipt['reopenReadbackFailures'] = failures
        scape.receipt['actorCountAfter'] = len(scape.actors.get_all_level_actors())
        if failures:
            raise RuntimeError('Reopen readback failed: %s' % failures[:10])
        scape.receipt['status'] = APPLIED_STATUS
        return scape.receipt
    except Exception as error:
        scape.receipt['errors'].append({'stage': 'run', 'error': repr(error)})
        changed_on_disk = sha256_of(map_file) != map_sha_before
        scape.receipt['status'] = ('failed_after_save_checkpoint_available'
                                   if scape.receipt.get('mapSaved') or changed_on_disk
                                   else 'failed_before_save_map_unchanged')
        raise
    finally:
        scape.receipt['mapSha256After'] = sha256_of(map_file)
        scape.receipt['mapBytesChanged'] = scape.receipt['mapSha256After'] != map_sha_before
        scape.receipt['createdAssetPaths'] = list(scape.created_assets)
        scape.receipt['appliedChangeCount'] = sum(
            1 for c in scape.receipt['changes'] if c.get('applied'))
        scape.receipt['skippedChangeCount'] = sum(
            1 for c in scape.receipt['changes'] if not c.get('applied'))
        after = _protected_hashes(spec)
        scape.receipt['protectedUnchanged'] = after == protected
        if not scape.receipt['protectedUnchanged']:
            scape.receipt['status'] = 'failed_protected_hash_guard'
            scape.receipt['errors'].append({'stage': 'verification',
                                            'error': 'A protected map or asset changed'})
        scape.write_receipt()
        if not scape.receipt['protectedUnchanged']:
            raise RuntimeError('A protected map or asset changed')


def revert(receipt_path=None, load_target=True, delete_assets=False):
    """Destroy every tagged actor, restore the recorded before-values, save, reopen."""
    import unreal as ue
    spec = load_spec()
    if receipt_path:
        source_path = Path(receipt_path)
        source = json.loads(source_path.read_text(encoding='utf-8-sig'))
    else:
        source_path, source = latest_apply_receipt(spec)

    scape = Soundscape(ue, spec)
    scape.guard_world(load_target)
    map_file = ROOT / spec['targetMapFile']
    map_sha_before = sha256_of(map_file)
    protected = _protected_hashes(spec)
    stamp = utc_stamp()
    scape.receipt_path = _fresh_receipt_path(spec, spec['revertReceiptPrefix'], stamp)
    scape.receipt = {
        'status': 'started', 'stamp': stamp, 'map': TARGET, 'sourceReceipt': str(source_path),
        'sourceReceiptStatus': source.get('status'), 'mapSha256Before': map_sha_before,
        'protectedSha256Before': protected, 'deleteAssets': bool(delete_assets),
        'destroyed': [], 'restored': [], 'changes': [], 'notes': [], 'errors': [],
        'mapSaved': False, 'checkpoint': None, 'limitations': list(spec['limitations']),
    }
    scape.write_receipt()

    try:
        checkpoint, copied = _checkpoint(spec, spec['revertCheckpointPrefix'], stamp, map_file,
                                         map_sha_before)
        scape.receipt['checkpoint'] = str(checkpoint)
        scape.receipt['oneFilePerActorFoldersCopied'] = copied
        scape.write_receipt()

        tag = spec['actorTag']
        doomed = [a for a in scape.actors.get_all_level_actors()
                  if tag in [str(t) for t in a.tags]]
        for actor in doomed:
            record = {'label': actor.get_actor_label(), 'name': actor.get_name(),
                      'class': actor.get_class().get_name()}
            if not scape.actors.destroy_actor(actor):
                raise RuntimeError('destroy_actor failed for ' + record['label'])
            scape.receipt['destroyed'].append(record)
        scape.write_receipt()

        # restore the pilot ambience if this run had forced it off
        pilot = source.get('pilotAmbience') or {}
        if pilot.get('autoActivateForcedFalse'):
            for actor in scape.actors.get_all_level_actors():
                if not isinstance(actor, ue.AmbientSound):
                    continue
                component = actor.get_component_by_class(ue.AudioComponent)
                sound = component.get_editor_property('sound')
                if sound and sound.get_path_name().split('.')[0] == pilot['sound']:
                    scape.set_prop('pilotAmbience', component, 'auto_activate',
                                   bool(pilot['autoActivateBefore']), required=True)
                    scape.receipt['restored'].append(
                        {'pilotAutoActivate': bool(pilot['autoActivateBefore'])})

        remaining = [a.get_actor_label() for a in scape.actors.get_all_level_actors()
                     if tag in [str(t) for t in a.tags]]
        if remaining:
            raise RuntimeError('Tagged actors survived the revert: %s' % remaining[:10])

        scape.save_and_reopen()
        scape.receipt['mapSha256AfterSave'] = sha256_of(map_file)
        still = [a.get_actor_label() for a in scape.actors.get_all_level_actors()
                 if tag in [str(t) for t in a.tags]]
        scape.receipt['taggedActorsAfterReopen'] = still
        if still:
            raise RuntimeError('Tagged actors are back after the reopen: %s' % still[:10])

        if delete_assets:
            root = spec['namespace']['root']
            if scape.assets.does_directory_exist(root):
                scape.assets.delete_directory(root)
            scape.receipt['assetsDeleted'] = not scape.assets.does_directory_exist(root)
            if not scape.receipt['assetsDeleted']:
                raise RuntimeError('Failed to delete ' + root)
        else:
            scape.receipt['notes'].append(
                'The imported assets under %s were left in place; nothing references them once the '
                'actors are gone. Pass -SoundscapeRevertAssets to delete them too.'
                % spec['namespace']['root'])
        scape.receipt['status'] = REVERTED_STATUS
        return scape.receipt
    except Exception as error:
        scape.receipt['errors'].append({'stage': 'revert', 'error': repr(error)})
        scape.receipt['status'] = 'revert_failed_checkpoint_available'
        raise
    finally:
        scape.receipt['mapSha256After'] = sha256_of(map_file)
        after = _protected_hashes(spec)
        scape.receipt['protectedUnchanged'] = after == protected
        scape.write_receipt()


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------

def _unreal_available():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


def _invoked_as_native_script():
    if not _unreal_available():
        return False
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line().lower()
    return ('release_soundscape_v2.py' in command_line
            and ('-run=pythonscript' in command_line or '-executepythonscript' in command_line))


def parse_switches(tokens):
    lowered = [t.lower() for t in tokens]
    switches = {'import_only': '-soundscapeimportonly' in lowered,
                'use_cues': '-soundscapenocue' not in lowered,
                'make_volume': '-soundscapenovolume' not in lowered,
                'dry_run': '-soundscapedryrun' in lowered,
                'revert': False, 'revert_receipt': None,
                'ambient_fallback': '-soundscapeambientfallback' in lowered,
                'runtime_actor': '-soundscapenoruntimeactor' not in lowered,
                'delete_assets': '-soundscaperevertassets' in lowered}
    if switches['delete_assets']:
        switches['revert'] = True
    for token in tokens:
        low = token.lower()
        if low == '-soundscaperevert':
            switches['revert'] = True
        elif low.startswith('-soundscaperevert='):
            switches['revert'] = True
            switches['revert_receipt'] = token.split('=', 1)[1].strip('"')
    return switches


def _main():
    import unreal as ue
    command_line = ue.SystemLibrary.get_command_line()
    switches = parse_switches(command_line.split())
    try:
        if switches['revert']:
            receipt = revert(receipt_path=switches['revert_receipt'], load_target=True,
                             delete_assets=switches['delete_assets'])
            ue.log('release_soundscape_v2 revert: %s destroyed %d'
                   % (receipt['status'], len(receipt['destroyed'])))
        else:
            receipt = run(load_target=True, import_only=switches['import_only'],
                          use_cues=switches['use_cues'], make_volume=switches['make_volume'],
                          dry_run=switches['dry_run'],
                          ambient_fallback=switches['ambient_fallback'],
                          runtime_actor=switches['runtime_actor'])
            runtime = receipt.get('runtimeActor') or {}
            ue.log('release_soundscape_v2: %s waves %d emitters %d zones %d submix %s '
                   'applied %s skipped %s'
                   % (receipt['status'], len(receipt['assets']['waves']),
                      runtime.get('emitterCount', 0), runtime.get('zoneCount', 0),
                      receipt.get('assets', {}).get('submix'),
                      receipt.get('appliedChangeCount'), receipt.get('skippedChangeCount')))
            if receipt.get('audioVolumeBrushFinding'):
                ue.log('release_soundscape_v2 AudioVolume brush: '
                       + receipt['audioVolumeBrushFinding'])
            ue.log('release_soundscape_v2: NOBODY HAS LISTENED TO THIS YET.')
    except Exception as error:
        ue.log_error('release_soundscape_v2 failed: ' + repr(error))
        raise
    finally:
        if ('-executepythonscript' in command_line.lower()
                and '-run=pythonscript' not in command_line.lower()):
            ue.SystemLibrary.quit_editor()


def _offline_main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Offline half of the SoundscapeV2 release: fetch, measure, freeze, check')
    parser.add_argument('--fetch', action='store_true',
                        help='download every source once and write its provenance')
    parser.add_argument('--force', action='store_true', help='re-download even if present')
    parser.add_argument('--analyse', '--analyze', dest='analyse', action='store_true',
                        help='measure every source and apply the bed transient rule')
    parser.add_argument('--freeze', action='store_true',
                        help='record hashes and durations into the spec')
    parser.add_argument('--credits', action='store_true',
                        help='print the attribution block for Content/Distribution/CREDITS.txt')
    args = parser.parse_args()
    if args.fetch:
        report = fetch_all(force=args.force)
        print(json.dumps({'files': len(report['files']),
                          'totalBytes': sum(f['bytes'] for f in report['files'])}, indent=2))
    if args.analyse:
        summary = analyse_all()
        for row in summary['files']:
            print('%-46s %8.2fs %-10s %s' % (row['file'], row['durationSeconds'] or 0.0,
                                             row['role'], (row['bedRule'] or {}).get('verdict')))
    if args.freeze:
        print(json.dumps(freeze(), indent=2)[:2000])
    if args.credits:
        print('\n'.join(_credits_lines(load_spec())))
    if not (args.fetch or args.analyse or args.freeze or args.credits):
        result = offline_check()
        trimmed = dict(result)
        print(json.dumps(trimmed, indent=2))
        if not result['ok']:
            sys.exit(1)


if __name__ == '__main__':
    if _unreal_available():
        _main()
    else:
        _offline_main()
elif _invoked_as_native_script():
    _main()
