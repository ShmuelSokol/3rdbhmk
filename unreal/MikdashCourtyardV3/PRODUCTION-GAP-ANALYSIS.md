# What separates this from a full production release

Written 8 September 2026, against the state at Walkthrough-11 (commit 23e9208d).
Honest assessment. Items marked BUILDING are under way as of this writing.

## 1. There is no game around the level
- BUILDING: main menu, pause menu, settings, accessibility options, loading screen, credits.
- BUILDING: a cinematic intro flythrough that hands control to the player.
- BUILDING: photo mode, which is the single highest-value shareability feature here.
- MISSING: save and resume of the visitor's position and progress.
- MISSING: a proper HUD language, compass or orientation aid, and interaction prompt style guide.

## 2. Nothing tells the visitor what they are seeing
- BUILDING: a guided tour of fifteen to twenty stops on the pilgrim's real route.
- BUILDING: a codex of every element with its source citation and a confidence label.
- MISSING: narration. Text first, voice later.
- MISSING: Hebrew localisation of the interface.

## 3. The world does not move or change
- BUILDING: time of day from real Jerusalem solar geometry, with night and moon phase.
- BUILDING: weather, including the summer haze and the khamsin.
- BUILDING: birds, four species, flocking and perching.
- BUILDING: crowds, transit, boarding, a train, and people photographing.
- MISSING: a service calendar. The daily order, shabbat, and the three festivals differ.

## 4. No fire, no smoke, no water
- QUEUED: altar fire, incense plume, lamp flames, dust in the light shafts, heat haze.
- QUEUED behind it: the stream from under the threshold of Yechezkel 47, mikvaot, the laver.
- These two are the largest visual gap. A Mikdash without fire and water reads as a model.

## 5. The people are not yet people
- BUILDING: MetaHuman, which ships inside Unreal 5.8 and needs no download.
- BUILDING: better rigs, cloth, hands and faces for the near-camera characters.
- BUILDING: the Kohen Gadol tending and lighting the menorah.
- MISSING: facial animation and lip sync on the speaking residents.
- MISSING: foot placement that follows the ground, which is very visible on stairs.

## 6. Landscape and detail
- BUILDING: vegetation, real Judean species, terraced groves, scrub and dry grass.
- BUILDING: security at the gates with metal detectors and signage.
- MISSING: surface-aware footsteps, decals, wear, dirt, and the small clutter of a used place.
- MISSING: a materials pass on the terrain itself.

## 7. Engineering a release needs
- MISSING: an automated test and build pipeline. Everything is presently run by hand.
- MISSING: a performance budget with measured frame times per area.
- MISSING: crash reporting and a version stamp visible in the build.
- PARTIAL: the release receipts are good, but there is no single acceptance gate.

## 8. The honest ceiling
A hundred-million-dollar production buys hundreds of artists for years. This will not
match that. What it can match is coherence: everything present looking deliberate,
nothing obviously wrong, and every claim about the building traceable to a source.
That is the standard being worked to.
