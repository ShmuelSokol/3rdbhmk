# People, daily rhythms, priestly homes, and the surrounding city

Research date: 2026-09-07. Scope: source-backed requirements for a Third Beis HaMikdash experience based on the existing measured Yechezkel reconstruction. This is a focused research dossier, not an exhaustive halachic ruling or a prediction of every detail of the future. No scene assets or runtime features are implemented by this document.

## Evidence categories that must survive into production

- **P — prophetic text:** an explicit statement in Yechezkel; application still requires the project's chosen interpretation and geometry mapping.
- **H — earlier Temple law/practice:** Mishnah, Gemara, or Rambam on Temple operation. It must not silently become an assertion that the future will reproduce every historical circumstance.
- **I — interpretation:** a named commentator or a reasoned inference; retain alternatives where they affect gameplay.
- **D — design:** invented individual, dialogue, residence interior, arrival count, or task duration. It can be convincing without being advertised as revelation.

Every crowd schedule, room use, interaction, and lesson should store its source category and specific reference. No rule should become a scored halachah merely because it looks plausible in a scene.

## 1. How many people, and when?

**There is no verified exact future population count in these sources.** The number of NPCs rendered is an engineering and art decision. The total number of pilgrims represented is a separate simulation parameter. Neither is a future census.

**P: Gate use changes with the calendar.** Yechezkel 46:1–3 distinguishes ordinary weekdays from Shabbat and Rosh Chodesh at the inner east gate. Verses 9–10 describe people entering through north or south and leaving through the opposite gate at appointed gatherings. These are event-specific routes, not a universal instruction to make every doorway one-way. Verses 13–15 describe the morning offering. Map the named gate and participant roles to the measured model before enabling navigation restrictions. [Yechezkel 46](https://www.sefaria.org/Ezekiel.46)

**H: Daily timing is not an arbitrary animation loop.** Tamid 3:2 describes an actual check that daylight has arrived before slaughter. Pesachim 5:1 gives the afternoon tamid's regular 8.5/9.5-hour sequence and earlier schedules on Erev Pesach, especially when it is Friday. These are halachic hours, not universal modern 2:30/3:30 clock times. The educational scheduler should retain the event ordering and distinguish any accelerated demonstration clock. [Tamid 3:2](https://www.sefaria.org/Mishnah_Tamid.3.2), [Pesachim 5:1](https://www.mishnah.org/learn/pesachim/5/1/)

**H: Festival scale changes workflow.** Pesachim 5:5–7 describes three successive groups for the korban Pesach, door closure for a filled group, coordinated priestly rows, and Hallel. It supplies a procedure, not a usable modern capacity survey. Implement a reviewed Pesach scenario separately from ordinary-day life; do not run it every afternoon. [Pesachim 5:5–7](https://www.sefaria.org/Mishnah_Pesachim.5.5?lang=en)

**H: Large historical figures need context.** Pesachim 64b reports Agrippa's count through offerings and registered participants, with exclusions and discussion of the counting mechanism. It concerns a particular crowded historical Pesach, not a forecast of the Third Temple. Do not translate its large figures into an exact future head count or simultaneously visible people. [Pesachim 64b](https://www.sefaria.org/Pesachim.64b)

**D: Proposed first scenario:** a clearly identified ordinary weekday morning, with a small authored cast and background participants whose arrivals have reasons. Separate presets should later represent Shabbat/Rosh Chodesh, a pilgrimage gathering, Erev Pesach, and a bikkurim procession. Begin performance trials at 24 fully simulated nearby characters; this is a test budget, not a source claim or guaranteed final density. Scale only after profiling the packaged build on the RTX 2070 target. Distant crowd representation must not erase the identity and task state of a named character when that character returns nearby.

**Acceptance:** a character arriving early waits appropriately; a blocked doorway does not make people walk through each other; the crowd's composition and routes change with the selected event; no text claims an exact future number. Test sparse, ordinary, and busiest planned scenes separately, including frame time, navigation stalls, sound masking, and sight lines.

## 2. Where do the kohanim live?

**P: There is explicit residential land.** Yechezkel 45:4 assigns a place for priests' houses within the sacred land allocation. Verse 5 treats the Levites' allocation, and verse 6 the city's holding. Rashi on 45:2–5 distinguishes the Sanctuary area from surrounding priestly residential land and explains measurements using rods. These passages support a priestly residential district; they do not specify each family's address, domestic floor plan, or total households. Do not casually convert every number to the project's 0.5-metre amah without resolving rod-versus-amah interpretation. [Yechezkel 45:1–6 with Rashi](https://www.chabad.org/library/bible_cdo/aid/16143/jewish/Chapter-45.htm)

**H: Duty lodging is different from permanent family housing.** Tamid 1:1 describes priests on duty sleeping in the Beit HaMoked, elders holding courtyard keys, and young priests with bedding. Sacred service clothing is removed before sleeping. The same passage describes a discreet route to immersion and a door arrangement protecting toilet privacy. It does not establish that all priestly families permanently live inside Temple chambers. [Tamid 1:1](https://www.sefaria.org/Mishnah_Tamid.1.1)

**H: Rotations explain movement.** Ta'anit 4:2 describes twenty-four watches and representative ma'amadot, with kohanim and Levi'im going up when their turn arrives. Sukkah 5:6 supplies a festival example of the many watches sharing service assignments. They establish institutional scheduling, not the number of people in each future watch. [Ta'anit 4:2](https://www.sefaria.org/Mishnah_Ta%27anit.4.2?with=Tosefta+Ta%27anit), [Sukkah 5:6](https://www.sefaria.org/Mishnah_Sukkah.5.6)

**D: Build three distinct destinations:** a family home in a clearly marked interpretive residential district; a duty lodging location only where the adopted architectural interpretation supports it; and service preparation/work locations. A kohen can leave home, arrive for a rotation, prepare, perform an assigned task, and return. Do not place bedrooms inside every currently unused chamber to make the building appear occupied. Fictional family names, relationships, furnishings, meal times, and travel durations must remain design records.

**Acceptance:** off-duty and on-duty clothing are distinct states; family members do not inherit service-area access from their relationship; no NPC is simultaneously at home and at service; lodging geometry is reviewed before being labeled a known Yechezkel room.

## 3. Families, pilgrims, hosts, and processions

**H: Obligation and presence are different.** Chagigah 1:1 lists exemptions from the specific re'iyah obligation and discusses a child's ability to ascend with a father. It should not be converted into a blanket claim that all exempt people are prohibited from Jerusalem or excluded from all festival life. Devarim 16:11 explicitly frames festival rejoicing with sons, daughters, household members, Levi'im, and vulnerable community members. [Chagigah 1:1](https://www.mishnah.org/learn/chagigah/1/1/), [Devarim 16:11](https://www.sefaria.org/Deuteronomy.16.11?lang=bi)

**H/I: Hosting is not simply a modern hotel economy.** Yoma 12a discusses Jerusalem's division/ownership and a baraita against charging rent for houses; Rabbi Elazar bar Tzadok extends this to beds. It also discusses gifts to hosts. Preserve this legal context and its differing views before inventing paid lodging quests. The source text was checked through Sefaria's text API because the browser reader returned only its shell. [Yoma 12a](https://www.sefaria.org/Yoma.12a?lang=bi)

**H: Bikkurim is a specific arrival pattern.** Bikkurim 3:2 has participants gather and sleep in the public space of their district's gathering city before the ascent; it does not mean all Jerusalem visitors sleep outdoors. Bikkurim 3:3 describes fruits varying by travel distance, a decorated leading ox, flute accompaniment, and advance notification before entering Jerusalem. This supports a recognizable procession rather than a generic crowd carrying random baskets. [Bikkurim 3:2](https://www.sefaria.org/Mishnah_Bikkurim.3.2), [Bikkurim 3:3](https://www.mishnah.org/learn/bikkurim/3/3/)

**D: Candidate authored characters:** a host preparing a meeting place; an experienced pilgrim helping a first-time visitor find their group; a parent keeping a child near; a procession coordinator checking that the group is ready; a farmer protecting a first-fruits basket. Each has a destination, relationship, memory of completed work, and a reason to decline a distracting conversation. Choose original names and dialogue. Do not impersonate a named historical sage with invented teachings.

## 4. Beggars, tzedakah, and the future economy

**H: Discreet assistance has a Temple source.** Shekalim 5:6 describes a chamber where gifts and support were handled privately. It does not give a public beggar seating plan, authorize begging at a particular gate, or identify this chamber's position in the project's future model. [Shekalim 5:6](https://www.sefaria.org/Mishnah_Shekalim.5.6)

**I: Future poverty cannot be assumed from earlier poverty.** Rambam, Melachim 12:5 describes abundance and the absence of famine, war, envy, and competition, with humanity directed toward knowledge of Hashem. Chapter 12:2 also cautions against certainty about the details and sequence of future events. A future-world depiction full of destitute beggars, desperate scarcity, or predatory sellers would require reconciliation with this account. This does not by itself prove every conceivable form of assistance disappears or settle all opinions about phases of redemption. [Melachim uMilchamot 12:2,5](https://www.chabad.org/library/article_cdo/aid/1188357/jewish/Melachim-uMilchamot-Chapter-12.htm)

**D: Default future scene decision:** do not spawn street beggars as ambient decoration. Include hospitality, assistance finding one's group, sharing knowledge, and practical help. A separately labeled earlier-Temple learning scenario may teach discreet charity after review. Keep its recipient dignified and its purpose educational. Do not display a recipient's private need as a floating label or award points for publicizing it.

**Unresolved:** a qualified reviewer should decide whether the selected future-era interpretation includes material-poverty scenarios, and if so which source supports that specific phase. No reviewed source here supplies an exact beggar location. The answer to “where would they sit?” is therefore presently unknown, not “beside gate X.”

## 5. Vendors, food, supplies, and kitchens

**H: Temple supply administration is documented.** Shekalim 5:3–5 describes seals/tokens for the libations accompanying offerings, payment and collection roles, and reconciliation for lost tokens. These transactions are not evidence for ordinary snack stalls in the courtyard. The listed officials in 5:1 also provide distinct functional jobs rather than interchangeable “merchant” NPCs. [Shekalim 5](https://www.sefaria.org/Mishnah_Shekalim.5)

**H/I: Jerusalem's food supply has source support.** Ma'aser Sheni 5:2 regulates bringing fourth-year vineyard produce toward Jerusalem and changes to redemption arrangements. Bartenura explains the relationship to supplying its fruit markets. This supports city food logistics and a market context, not an exact street address, stall plan, or claim that all food is ordinary non-sacred merchandise. The Mishnah also preserves Rabbi Yose's differing account of the restoration condition. [Ma'aser Sheni 5:2 and Bartenura](https://www.mishnah.org/learn/maaser-sheni/5/2/)

**P: Yechezkel's kitchens are purpose-specific.** Yechezkel 46:19–24 differentiates priestly preparation of sacred portions from the corner kitchens for the people's offerings. Do not repurpose these as cafes, taverns, or public retail counters. Cooking, carrying, handing over, and eating need offering-specific rules, not a single generic food interaction. [Yechezkel 46:19–24](https://www.sefaria.org/Ezekiel.46)

**D: Proposed city-side food scene:** an interpretive provisioning area outside the Temple precinct, pending review of its specific location and selected future economy. It should feel like organized hospitality and supply, with measured portions and purposeful handling. Represent ordinary food, sacred food, and offering ingredients as separate item categories. Do not assign modern prices or implement bargaining until the economy premise has been approved. Food preparation can remain a modest distant activity without graphic sacrifice detail.

**Acceptance:** no retail marker appears in the Azarah without a specific reviewed basis; kitchen animations use the correct room purpose; a generic vendor cannot grant purity, sacrificial eligibility, or unrestricted access; items cannot silently cross their reviewed consumption boundaries.

## 6. Surrounding town versus today's Old City

**P/I: Yechezkel describes a broader planned geography.** Chapter 48:10–20 distinguishes priestly and Levitical allocations from a city area, open land, and provision for those serving the city. Verses 30–35 describe city gates associated with tribes. Rashi explains the scale in rods. This is not a warrant to relabel today's street network as the exact future city. Precise scale, orientation, and relationship to existing geography need a single documented interpretive choice. [Yechezkel 48 with Rashi](https://www.chabad.org/library/bible_cdo/aid/16146/jewish/Chapter-48.htm)

**D: Existing OSM buildings and streets should remain identifiable as modern geographic context.** They help a visitor orient themselves. A future city layer must be separate and explicitly interpretive where no approved source determines it. Do not erase or replace the measured Temple geometry to make a modern street align with a prophetic gateway. Do not call a generated house the actual future home of a named kohen.

## 7. NPC implementation contract

These are simulation requirements, not claims that software contains a human mind. Every named NPC needs persistent identity, role, current task, destination, relationships, permitted areas, possessions relevant to the task, schedule, and remembered completion. Personality should influence pace, manner of greeting, patience, curiosity, and how explanations are offered. It must not silently override reviewed halachic restrictions.

Use a shared world clock and explicit task preconditions. A source-backed activity can have fictional motivations: “I promised to meet my family after this task” is authored characterization; “this law permits me to enter here” must resolve to the reviewed ruleset. An optional short intention display may say “bringing supplies to the kitchen,” but it should not expose private needs or invent religious rulings. Free-form generated conversation must not be the authority that changes eligibility or teaches an unreviewed halachah.

Failed movement should trigger waiting, rerouting, or a clear interruption. It must not trigger teleporting through a closed gate, abandoning sacred items, or crossing a forbidden zone. A character returning from background simulation must retain the same goal and inventory. Conversations should pause or defer tasks sensibly and resume them afterward.

## 8. Build order and review gates

1. **Approve one scenario contract:** date/event, future-era premise, architectural interpretation, participant roles, and which historical procedures are adopted. Keep unreviewed scenarios disabled.
2. **Map rooms and gates:** each semantic destination must point to a verified location in the measured geometry. Record uncertain locations rather than hiding them behind a confident label.
3. **Build a small connected cast:** arrival, preparation, service-related task, reunion, and departure. Demonstrate persistent state and shared timing before increasing population.
4. **Validate rule transitions:** roles, item classes, clock events, access, privacy, and rejected actions. Score only lessons with approved wording and sources.
5. **Review the experience in motion:** quiet and crowded scenes, natural pauses, purposeful gestures, intelligible spatial audio, and modest family presentation. A crowd count alone is no evidence of life or quality.
6. **Verify a fresh packaged run:** no editor dependencies, reproducible cast state, no blocked doors or endless loops, acceptable performance on the target PC, readable sources, and clearly disclosed historical/interpretive layers.

Research remains open on exact future demographics, detailed priestly residential plans, the full chronology of avodah across all festival types, specific market locations, the future economy's phases, and the architectural reconciliation of every historical chamber with Yechezkel. These gaps should guide the next source review; they must not be filled by confident unsourced narration.
