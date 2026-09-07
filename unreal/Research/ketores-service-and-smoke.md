# Ketores service, timing, and maaleh ashan

Research date: 7 September 2026. Status: researched simulation specification, not implemented service, rabbinic approval, or a reconstruction of the incense formula. This document supplies no recipe, chemical claim, or real-burning instruction.

## What the scene should communicate

Ketores belongs to a scheduled service in a specific place, performed by the appropriate kohen. It is not a permanent decorative smoke column over the outer altar. The ordinary morning and afternoon offerings occur on the Golden Altar in the Heikhal. The Kohen Gadol's Yom Kippur offering inside the Kodesh HaKodashim is a separate event, not the ordinary daily location and not permission for visitor entry. Maaleh ashan should inform the smoke's illustrated behavior without presenting an unverified botanical identification as fact.

Evidence classes follow [halacha-and-service.md](halacha-and-service.md): **H** earlier Temple / halachic source, **P** explicit prophetic text, **R** unresolved interpretation or mapping, **D** design. The sources below are H or Torah text; none independently certifies the final spatial or calendrical application to this Third Temple reconstruction.

## Source register

- **KET-TORAH-DAILY — Torah text:** Shemos 30:7–8 associates the daily morning and afternoon incense with tending/kindling the lamps. “Regular” service is not evidence that a visual emitter runs continuously. [Shemos / Exodus 30:7–8](https://www.sefaria.org/Exodus.30.7-8).
- **KET-DAILY-LOCATION — H:** Rambam specifies twice-daily incense on the Golden Altar in the Heikhal. His 3:3 describes withdrawal from the Heikhal and the space between Ulam and outer altar until the officiant leaves; 3:9 gives the overseer's cue before the offering. [Temidin uMusafin 3:1, 3, 9](https://www.chabad.org/library/article_cdo/aid/1013255/jewish/Temidin-uMusafim-Chapter-3.htm).
- **KET-DAILY-SEQUENCE — H:** Morning incense falls between the tamid blood service and offering its limbs; afternoon incense falls between the limbs and libations. These are relative service positions, not specified modern clock minutes. [Mishnah Yoma 3:5](https://www.sefaria.org/Mishnah_Yoma.3.5).
- **KET-OVERSEER — H:** Tamid describes the officiant waiting for the supervisor's instruction, withdrawal, and the officiant's exit. [Mishnah Tamid 6:3](https://www.sefaria.org/Mishnah_Tamid.6.3).
- **KET-YK-TORAH — Torah text:** Vayikra describes the special offering beyond the curtain and the covering cloud. [Vayikra / Leviticus 16:12–13](https://www.sefaria.org/Leviticus.16.12-13).
- **KET-YK-SEQUENCE — H:** Rambam's Yom Kippur sequence includes the regular morning offering in golden garments, the distinct inner service in white garments, and the regular afternoon incense after subsequent transitions. The inner offering follows the bull's slaughter and precedes bringing its blood inside. He distinguishes Ark-era placement from Second Temple placement on the Foundation Stone; one cannot silently mix them. [Avodat Yom HaKippurim 4:1](https://www.chabad.org/library/article_cdo/aid/1062926/jewish/Avodat-Yom-haKippurim-Chapter-4.htm).
- **KET-YK-WITHDRAWAL — H:** In Rambam's account, withdrawal for the special inner incense differs from the daily Heikhal offering. The whole daily withdrawal area must not be reused without checking which event is active. [Avodat Yom HaKippurim 4:2](https://www.chabad.org/library/article_cdo/aid/1062926/jewish/Avodat-Yom-haKippurim-Chapter-4.htm).
- **KET-SMOKE-FORM — H:** The discussion describes a stafflike rising column reaching the ceiling, followed by smoke spreading downward along the walls until the chamber is filled. It also distinguishes putting the incense on the fire inside from bringing an already-produced cloud in. [Yoma 53a:4–5, 11](https://www.sefaria.org/Yoma.53a.4-11).
- **KET-SMOKE-DAILY — H:** The sugya discusses application of maaleh ashan beyond Yom Kippur to other days. Do not transfer every detail of its discussion of indispensability or sanctions into a simplistic gameplay penalty. [Yoma 53a:15–16](https://www.sefaria.org/Yoma.53a.15-16).
- **KET-AVTINAS — H:** The account contrasts the Avtinas family's rising column with the Alexandrians' dispersing smoke; another passage tells of a descendant recognizing the herb but declining to reveal it. These passages do not establish a modern scientific species name. [Yoma 38a:10, 14](https://www.sefaria.org/Yoma.38a.10-14).

## Clock and scene contract

The following event IDs and software behavior are **D**, motivated by the cited order. They are not additional halachos. Each event records the fictional date, service profile, source IDs, officiant, reviewed location, predecessor events, review status, and one execution identity. Use the world's shared simulation clock; pausing a lesson or opening a menu must not secretly advance it.

1. **DAILY_AM_KETORES_READY:** follows the morning blood-service event in the selected reviewed service profile. Assignment, preparation, location, and withdrawal must be satisfied. References KET-DAILY-SEQUENCE and KET-DAILY-LOCATION.
2. **DAILY_AM_KETORES_BEGIN:** the overseer's cue starts the authored kohen sequence and one smoke event at the Golden Altar. References KET-OVERSEER. The subsequent morning limb-service event must respect the selected sequence.
3. **DAILY_PM_KETORES_READY / BEGIN:** separate afternoon instance, positioned after the appropriate limb event and before libations. The offering is not restarted simply because the player returns to the room. References KET-DAILY-SEQUENCE.
4. **YK_INNER_KETORES_READY / BEGIN:** available only in a separately reviewed Yom Kippur profile with its Kohen Gadol and white-garment/service prerequisites. Uses an inner location anchor rather than the daily Golden Altar anchor. References KET-YK-TORAH and KET-YK-SEQUENCE. This event must coexist correctly with that day's daily offerings.
5. **KETORES_OFFICIANT_EXIT / RESIDUAL_SMOKE_END:** separate the service state, the officiant's departure, and an illustrated residual-smoke tail. Particle visibility does not itself decide when entry becomes permissible. References KET-DAILY-LOCATION or KET-YK-WITHDRAWAL according to event type.

If a predecessor, selected interpretation, or sacred location is unknown, the simulation reports `needs_review`; it does not move the service to a convenient courtyard. A fast-forward evaluates event boundaries exactly once. Loading into a completed event restores its state instead of performing it again. Exact modern clock labels, time compression, particle lifetime, and NPC animation durations are design data, displayed as such. Do not invent “ketores at 9:00” from a relative service position.

## Smoke art direction and botanical uncertainty

**D, inspired by KET-SMOKE-FORM:** Show a coherent ascending plume with fine internal motion, then an indoor spread appropriate to the chosen interpretive visualization. Use separate emission, ascent, accumulation, and dissipating-tail phases. It should read as smoke rather than a solid pole, a white beam, an outdoor chimney, or a perpetual fog volume.

**R:** The texts provide qualitative behavior, not measured color, opacity, rise velocity, thickness, particle size, smell range, or persistence in minutes. Those settings are artistic choices. The referenced ceiling behavior does not justify smoke passing through the model's roof, continuously escaping as an exterior column, or filling all Jerusalem. Distinguish incense from the outer altar's fire and smoke in location, scheduling, labeling, and effect identity.

**R:** This research has not established a secure botanical identification of maaleh ashan. Do not label a specific modern plant, chemical mechanism, or recovered sample as the authentic ingredient. Attempts to retrieve the Temple Institute's former incense pages did not yield usable content during this check; a secondary site's attribution to that institution is insufficient verification. A botanical prop may remain absent or be plainly labeled illustrative until a directly checked source and reviewer settle its presentation.

**D:** A visitor views only from the reviewed visitor scene. An optional explanatory cutaway can show hidden service geometry while clearly labeled as an educational diagram; it must not teleport an ordinary avatar into the inner sanctuary. Smoke must not obscure pause/exit controls. Provide a reduced-effects option that preserves the schedule and source explanation.

## Acceptance gates

- Two distinct daily ketores events; the special inner event never appears on an ordinary day.
- A Yom Kippur scenario does not replace both daily offerings with one inner offering.
- Correct reviewed altar/inner anchor, officiant role, clothing, prerequisites, and withdrawal policy for each event.
- No particles before service begins; no repeating emitter after its authored end; independent residual-tail state.
- Pause, resume, reload, re-entry, and fast-forward neither duplicate nor skip required state transitions.
- Indoor smoke stops at architectural boundaries rather than clipping through the roof; the visual never becomes an accidental pillar across the exterior skyline.
- Source-aware text distinguishes a historical account from the future Temple mapping and all measured-from-text facts from artistic parameters.
- Qualified review is still needed for detailed service order, Yom Kippur choreography, sanctuary mapping, garments, and interpretive smoke presentation. No recipe, sanctions minigame, divine-approval score, or practical ritual guidance is necessary.

Verification: Chabad primary-text pages and Sefaria public text API passages were read on the research date. Short paraphrases only; no external endorsement or contact claimed. No engine changes, smoke assets, runtime tests, or publication were performed for this dossier.
