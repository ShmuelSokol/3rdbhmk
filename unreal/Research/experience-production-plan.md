# Arriving at the Third Beis HaMikdash

Research and production plan, 7 September 2026. Work in progress, not a claim of
complete halachic review or a prediction of every detail of the future.

## The experience we are building

The visitor arrives with a purpose. The approach gives time to notice the city,
meet a host, prepare, learn where to go, and see the Mikdash grow in scale. Entry
changes the sound, pace, permitted activities and behavior of people. The world
continues its service schedule when the player stands still. People have families,
work assignments, appointments and memories; they are not decorations waiting
to dispense a quest.

The primary setting is an envisioned functioning Third Mikdash using the existing
measured Yechezkel reconstruction. Historical teaching scenarios are explicitly
identified. Modern Jerusalem context is a comparison layer, not asserted future
urban planning. The current packaged preview is a technical foundation, not this
finished experience.

## Evidence is part of the world model

Every rule, object and placement needs a stable ID, source reference, brief original
paraphrase, evidence category, applicable scenario, interpretation, reviewer status,
and affected tests. Categories:

- **Prophetic text:** what the cited verses explicitly describe; commentary and
  physical mapping still need to be identified separately.
- **Earlier Temple / halachic source:** Mishnah, Talmud or Rambam describing a rule
  or practice. Its application to this Yechezkel layout is a separate decision.
- **Interpretation:** a named reading or reconciliation, with alternatives retained.
- **Historical/material analogy:** archaeology or a modern reconstruction used as
  a reference, not proof of the future.
- **Simulation design:** invented names, personalities, crowd budgets, dialogue,
  travel compression, convenient tutorial locations and visual variation.
- **Unresolved:** must not silently become a factual teaching or scored answer.

An `allow / deny / needs_review` decision is required for learning rules. Unknown
does not mean prohibited by halacha; it means the simulation cannot teach that
answer confidently. Free architectural exploration remains separate from the
role-based educational journey. Do not mistake collision tests for access-law tests.

Rambam explicitly warns that the order and details of certain messianic events are
not definitely known beforehand. That supports transparent interpretation rather
than a promise of prophetic certainty. [Melachim uMilchamot 12:2](https://www.chabad.org/library/article_cdo/aid/1188357/jewish/Melachim-uMilchamot-Chapter-12.htm).

## Spatial layers and the arrival route

Maintain separate graphs for (1) physical walkability, (2) sanctity/access zones,
(3) service logistics and (4) visitor directions. An open doorway does not by itself
authorize entry. Each graph refers to the same coordinate and gate IDs.

The existing architecture remains the measured reference; do not rescale it to fit
NPC animations or recreate it from a generic Second Temple illustration. Preserve
the current 0.5 metre amah convention and record alternate units per reference.
Yechezkel's land allocation needs a dedicated regional map before adding residential
streets: priestly, Levitical and city allocations must not be compressed into the
same courtyard simply for convenience. [Yechezkel 45:1–6](https://www.sefaria.org/Ezekiel.45),
[48:8–22](https://www.sefaria.org/Ezekiel.48).

Gate behavior is scenario-specific. Yechezkel describes the inner eastern gate's
weekday versus Shabbat/Rosh Chodesh pattern, and opposite north/south exit routing
at appointed occasions. Resolve the exact gate mapping and commentaries before
hard-coding these rules; do not reuse the current free-walk east entrance as an
automatically valid pilgrimage entrance. [Yechezkel 46:1–3, 9](https://www.chabad.org/library/bible_cdo/aid/16144/jewish/Chapter-46.htm).

Service chambers have real purposes, not generic furnished rooms. Yechezkel 42:13–14
distinguishes sacred eating/storage/changing uses. Kitchens in 46:19–24 require
their own processing and delivery routes. Neither passage justifies placing a
modern snack market in the Azarah. [Yechezkel 42](https://www.sefaria.org/Ezekiel.42),
[46](https://www.sefaria.org/Ezekiel.46).

First playable arrival sequence (design, locations pending graph review):

1. Arrive at a host/reception area in the surrounding city; choose a fictional
   visitor role and purpose. Notice families, deliveries and people preparing.
2. Receive a modest preparation lesson using the avatar's fictional ritual state.
   Never request the real player's intimate history.
3. Visit a private mikvah preparation area. Fade out for immersion and return to a
   fully dressed avatar. Separate immersion, waiting and other prerequisites.
4. Prepare possessions and attire for the applicable entrance. A companion offers
   explanations in learning mode; recall mode withholds prompts until requested.
5. Follow the reviewed entry route, keeping family/group continuity. Learn from
   purposeful activity and a service event, not a barrage of pop-up quizzes.
6. Complete a small, source-approved task or observation and leave by the appropriate
   route. Review misunderstood rules afterward with source links and retry options.

## A calendar that changes what the visitor sees

Use one authoritative scenario clock. Ordinary weekday, Shabbat, Rosh Chodesh,
Pesach, Shavuot/bikkurim, Sukkot and Yom Kippur are distinct scenarios; do not run
all ceremonies simultaneously. Dawn, sunrise, sunset and halachic time units must
be distinct from compressed simulation minutes. Explicitly label time compression.

The initial authored day should cover preparation, morning service, daytime tasks,
afternoon service and evening closure. Additional festival modules are enabled only
when their sources, participants, routes and event dependencies are complete.
Historical service sequence references include [Temidin uMusafim 1](https://www.chabad.org/library/article_cdo/aid/1013253/jewish/Temidin-uMusafim-Chapter-1.htm)
and [3](https://www.chabad.org/library/article_cdo/aid/1013255/jewish/Temidin-uMusafim-Chapter-3.htm).
Future-specific differences remain research questions, not automatic replacements.

## People with persistent purposes

An NPC identity includes role, household/group, language, personality traits,
knowledge, role permissions, ritual state, possessions, appointment windows,
relationships, remembered encounters, current goal, next action and a short
human-readable explanation of that action. These are authored simulation states,
not claims of consciousness or recovered thoughts of historical people.

An NPC chooses only among legal, reachable actions. Work assignments and service
timing outrank casual conversation. A person may give a short answer, promise to
speak later, direct the visitor to someone knowledgeable, or decline to speculate.
Dialogue may express personality but cannot invent a halachic ruling. Names and
personal backstories are fictional and should not be presented as source facts.

Initial character intentions: a first-time family keeping together; a returning
visitor helping them; a kohen preparing for his assigned service; an off-duty kohen
heading to appropriate lodging; a Levi waiting for a musical or gate assignment;
a host preparing accommodation; a supply worker delivering an authorized item;
a learner looking for an explanation; a bikkurim group leader tracking the group.
Festival-specific actors exist only in that festival scenario.

All population members keep persistent logical IDs and coarse schedules. Nearby
characters receive full navigation/animation; distant activity is simulated at lower
frequency. Rendered population and logical population are different counts. Do not
claim a render budget is the prophesied attendance. Do not run a paid cloud model
for every character. On this RTX2070/16GB PC, benchmark before promising density.

Crowd acceptance includes no wall crossings, no impossible access, no doorway
deadlocks, no endless pacing, plausible group separation/reunion, and persistence
after leaving and returning. A blocked path must produce a wait or alternate route,
not a teleport in the player's view.

## Halacha as meaningful learning

Track curriculum coverage by rule and scenario, with examples, counterexamples and
the player's remembered answers. Avoid claiming that a finite first mission teaches
all halachos. Learning mode explains before a choice; practice mode allows hints;
recall mode asks the player to remember; review mode returns to previous mistakes.

Score understanding and task completion, never a person's holiness, divine favor or
spiritual worth. Do not reward rushing the avodah. Give respectful correction and a
safe retry. Role-specific access is meaningful: a general visitor does not acquire
priestly permissions by answering trivia. An optional educational cutaway can show
otherwise inaccessible vessels without pretending the visitor entered the Heichal.

## Objects, stone, light and sound

The Temple Institute's actual menorah, begadim and keilim are the requested visual
references. Reference selection must distinguish actual manufactured objects from
illustrations and reenactment substitutes. Do not call a model exact from one photo.
Record silhouette, dimensions/units, decorative counts, parts, materials, placement,
handling and unresolved views before commissioning the asset.

Stone must read as maintained natural stone, not uniform beige plastic or an aged
ruin. Use restrained variation by individual block, plausible surface scale, subtle
roughness and pore/chisel information, and joints that remain stable in motion.
Separate monumental dressed stone, paving, ordinary city stone and protected altar
surfaces. Never add random chips to halachically sensitive surfaces for visual drama.
The first native sample is one wall and one paving area, with matched before/after
camera views, oblique sunlight, deep shade and a moving-camera check. No broad
assignment until it visibly improves the packaged build without changing geometry.

Sound follows real actions and spaces: footsteps from displacement and surface,
cloth and objects from handling, water only near water, conversations at believable
distance, song at scheduled service, and silence where appropriate. No constant
white-noise/bird/banging loop. Ancient melodies and pronunciation cannot be certified
by plausibility; label reconstructed music. Keep captions and separate volume controls.

## Integration contracts before implementation agents

Shared data: `SourceId`, `ScenarioId`, `ZoneId`, `GateId`, `ActorId`, `TaskId`,
`RuleId`, `AssetId`, `ServiceEventId`, and a single documented unit/coordinate map.
Each content record must declare evidence status and reviewer status. Workers must
not invent competing clocks, purity booleans, coordinate conversions or save formats.

Build assignments, after research reconciliation:

- **Rules and learning:** structured rule evaluator, fictional preparation state,
  lessons and meaningful counterexamples. Cannot silently approve unresolved rules.
- **Population:** deterministic schedule/goal simulation, local navigation, group
  behavior and persistent identity. Does not own halachic rulings.
- **Calendar and avodah:** event dependencies, assignments, gates and festival modules.
- **Objects and garments:** referenced models, correct units/roles, handling and LODs.
- **City and materials:** arrival route, sourced/designed boundaries, stone and lighting.
- **Audio and presentation:** localized cues, voices/subtitles, mix and accessibility.

Run at most three implementation workers concurrently on non-overlapping files;
the root integrates. Each assignment needs a playable acceptance scene, negative
tests, source references, performance measurements and a rollback checkpoint.
Research agents are active now; production building of disputed details waits for
the relevant dossier to be reconciled. A research document is not a finished feature.

## What “really well” must mean in review

1. A source reviewer can trace every scored religious claim and see alternatives.
2. A new visitor completes the first journey without getting trapped or lost.
3. Different NPC roles visibly accomplish different goals over an extended run.
4. Service participants, gates, audio and crowds follow the same clock.
5. Garments/vessels match the chosen reference across several views, not only a thumbnail.
6. Stone reads naturally both still and moving; no texture swimming or broad color noise.
7. The target PC meets measured frame-time/memory targets at agreed crowd settings.
8. Save/reload preserves learning, settings, NPC identities and scenario time correctly.
9. A fresh packaged build is tested with the editor closed; sharing instructions and
   credits are verified. Source commits alone are not a delivered experience.

## Open decisions that block factual claims, not all useful work

Exact future urban geography and demographics; reconciliation of Yechezkel's service
details with codified earlier service; identification of every gate in the measured
model; exact units for each Temple Institute object; future-specific commerce and
social assumptions; music; full curriculum coverage; model/photo reuse permissions;
and a qualified halachic review of the scored curriculum. Meanwhile we can build
source records, neutral systems, performance tests and reversible visual samples.
