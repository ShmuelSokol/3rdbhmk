# Kohen Gadol lamp service — source register

Research and verification date: 8 September 2026.
Status: researched, primary texts reopened and quoted below in short paraphrase.
**Not rabbinically approved. Not a rules engine. Not practical guidance.**

What we were asked to build: the Kohen Gadol lighting the menorah and walking
in the holy areas. What we built: `AMikdashServiceActor`, which walks one
figure through an authored sequence of stations in the Heikhal, tends and
kindles the seven lamps in two groups, pauses at the golden altar, and leaves.

Evidence classes follow the project's existing contract in
`C:\Mikdash\GitHub\3rdbhmk\unreal\Research\halacha-and-service.md`:

| class | meaning |
|---|---|
| **H** | Earlier-Temple / halachic source, with the precise passage named. Evidence for the described institution, not automatic proof of every detail of the future Temple. |
| **P** | Explicit prophetic text (Yechezkel). |
| **R** | Review needed: competing readings, a fact the sources do not supply, or an unresolved mapping to this reconstruction. |
| **D** | Design. Authored pacing, geometry-fitting and presentation. Never displayed as revealed detail. |

Verification method: each passage below was read on 8 September 2026 through
Sefaria's public texts API (`/api/v3/texts/...`), Hebrew where a Hebrew version
exists and the Moznaim/Touger English where it does not. Short paraphrases
only; no long copied translations. No rabbinic contact or endorsement is
claimed, and no external party has reviewed this file.

---

## 1. Is it legitimate to depict the Kohen Gadol lighting the menorah?

**Yes. That is the claim this build rests on, and it verified.**

### SVC-ORDINARY-KOHEN — H — certain
Rambam, **Biat HaMikdash 2:1**: "The High Priest enters the Holy of Holies each
year only on Yom Kippur. An ordinary priest may enter the Sanctuary for service
every day" — the Moznaim note glosses that daily service as offering incense,
kindling the menorah, or bowing.
→ So the daily lamp service is **ordinarily an ordinary kohen's**, and the
lottery in Temidin uMusafin ch. 4 assigns it. We say so in the actor's own
scenario text rather than letting the depiction imply otherwise.
Sefaria ref: `Mishneh Torah, Admission into the Sanctuary 2:1`.

### SVC-KG-MAY-SERVE — H — certain
**Mishnah Yoma 1:2, printed on Yoma 14a** (segment 3 of that daf, checked):
during the seven days of sequestering the Kohen Gadol "sprinkles the blood of
the daily burnt-offering, and he burns the incense, and **he removes the ashes
of the lamps of the candelabrum**, and he sacrifices the head and hind leg";
and "on all the other days of the year, if the High Priest wishes to sacrifice
any of the offerings, he sacrifices them, as the High Priest sacrifices any
portion that he chooses first."
Rambam, **Klei HaMikdash 5:12**: "On any day he desires, he may offer the
incense offering… **He does not seek to be chosen for service by lot.** Instead,
whenever he desires to offer a sacrifice, he may offer it."
→ **A Kohen Gadol lighting the menorah is legitimate.** That is what we depict.

> **Citation correction.** The commissioning brief cited *Klei HaMikdash 5:11*
> for this. 5:11 is a different halachah — it describes the Kohen Gadol
> entering the Heikhal to prostrate, supported by three attendants, one of whom
> holds the jewels of the choshen so it does not shift from the ephod. The
> "any service he wishes, no lottery" ruling is **5:12**. Both are cited in the
> code, each for what it actually says. (5:11 is independently useful to us: it
> is direct evidence that the Kohen Gadol walks into the Heikhal wearing the
> golden garments.)

### SVC-KG-IN-HEIKHAL — H — certain
Rambam, **Klei HaMikdash 5:11** (above) has him entering the Heikhal in the
ephod. Rambam, **Biat HaMikdash 2:2**: all priests are warned not to enter the
Heikhal or the Kodesh HaKodashim **when they are not in the midst of service**
(Vayikra 16:2, "he shall not come at all time" → the Kodesh HaKodashim;
"within the curtain" → extended by Rambam to the whole House; the Kessef
Mishneh questions that reading — see SVC-R-BIAT-2-2).
→ Design consequence, and it is enforced in code: **this actor has no idle
wander state.** It only ever walks the Heikhal inside a service sequence, and
it stands in the Ulam between sequences.

---

## 2. The boundary

### SVC-KODESH-BOUNDARY — H + Torah text — certain
**Vayikra 16:2**: God tells Moshe to tell Aharon "that he is not to come at
will" — literally *at any time* — "into the Shrine behind the curtain, in front
of the cover that is upon the ark, lest he die."
Rambam, **Biat HaMikdash 2:1**: the Kohen Gadol enters the Kodesh HaKodashim
only on Yom Kippur.
→ In this model the paroches line is **X = -5600 cm**, the west limit of
`SM_0146_floor_Heichal_clear_floor` and the east face of the partition band
(`X -5700..-5600`). On the OrdinaryDay scenario this is a **hard boundary**,
enforced in three independent places:
1. `ServiceScheduleMath::ZoneOf` classifies anything at or west of it as a
   separate zone that the ordinary-day gate refuses.
2. `ValidatePlan` refuses the whole sequence before it starts if any station or
   any sampled point of any straight leg reaches it.
3. `AMikdashServiceActor::MoveIsPermitted` re-checks **every single move**; a
   violation stops the sequence and leaves the figure standing, and never
   clamps-and-continues.
Two standalone tests sweep 20,000 simulated steps asserting the runner never
reports a position at or west of the line on an ordinary day.

### SVC-YK-SCENARIO — H — certain that it is a separate day; D for everything we show of it
The `YomKippur` scenario flag is **OFF by default** and must be chosen
deliberately. When on, it adds exactly two stations — an entry past the
paroches and an exit — and **nothing else**. We do not simulate the inner
service, the white garments, the bull, the lots, the blood, the ketores cloud,
or the confession. The commissioning brief said not to go beyond entry and
exit unless it was easy; it is not easy and it should not be guessed at. The
standalone test asserts that the identical Yom Kippur plan is refused the
moment the scenario flag is off.
Geometry note: the entry passes through the real gap in the partition band,
which is clear only for |Y| < 175 cm below Z 1225; the test asserts that even
the Yom Kippur scenario cannot walk through the wall either side of it.

---

## 3. The lamp service itself

### SVC-STONE — H — certain
Rambam, **Beit HaBechirah 3:11**: "A stone with three steps was placed before
the Menorah… The priest stood on it and kindled the lamps." (The Sifri links
*he'alah* / *ma'aleh*; Bartenura on Tamid 3:9 explains why three.) The Moznaim
note adds the practical reason: the menorah is eighteen handbreadths high.
→ Modelled: `SM_MenorahV4_StepStone` is part of the placed menorah asset, local
Y 45.91..135.91 → world X **-5284.1 .. -5194.1** (east of the plinth, as
`release_import_menorah_v4.spec.json` requires), local X ±45 → world Y
270.2..360.2, top at **Z 975**. The figure stands on it at (-5239, 315.176,
975) and shuffles along its top to face each lamp. It never walks between
lamps in mid-air.

### SVC-HATAVAH — H — certain as Rambam; **the meaning of the word is disputed**
Rambam, **Temidin uMusafin 3:12**: "Every lamp that has burnt out should have
its wick and its remaining oil removed and it should be cleaned. The priest
should place another wick and other oil in it, using the half-log measure…
He should kindle any lamp that was extinguished. **Kindling the lamps is what
is meant by the term hatavah.**"
Rambam, **Temidin uMusafin 3:11**: half a log of oil per lamp.
→ This is exactly the per-lamp action text the actor reports: clearing the
spent wick and oil, setting a fresh wick and oil, kindling it.
**R:** the Moznaim note records that *other authorities interpret hatavah as
referring only to the cleaning of the lamps.* We depict Rambam's reading.

### SVC-FIVE-THEN-TWO — H — certain, and it is why the sequence has two visits
Rambam, **Temidin uMusafin 3:17**: the priest who merited the lamp service
enters carrying a golden vessel called a **kuz**, places the extinguished wicks
and leftover oil in it, "would then kindle five lamps and **leave the kuz on
the second step of the three steps** positioned before the Menorah, and depart.
Afterwards he would re-enter and kindle two lamps, take the kuz in his hand,
prostrate himself, and depart."
→ Modelled literally, and this is why the loop leaves the Heikhal in the
middle: five lamps → kuz on the second step → out → wait → back in → two lamps
→ take the kuz → golden altar → out. Tested.

### SVC-LAMPS-FACE-CENTRE — H — Rambam adopted
Rambam, **Beit HaBechirah 3:8**: "The six lamps affixed in the six branches…
all faced the central lamp which was above the central shaft," from Bamidbar
8:2. On Rambam's north–south orientation the central lamp is the one facing the
Kodesh HaKodashim (Rambam, **Temidin uMusafin 3:13** and the note there).
> **Citation correction.** The brief cited "Rambam 3:12" for the lamps facing
> the centre. In *Beit HaBechirah* 3:12 is the Shulchan; the lamps-facing-centre
> halachah is **Beit HaBechirah 3:8**. (*Temidin uMusafin* 3:12 is the
> definition of hatavah, cited above under SVC-HATAVAH — both 3:12s are real
> and both are cited here, for the right things.)
→ Modelled: the seven lamp points run along world **Y** at X = -5330 (branches
north–south), evenly across the branch span ±46.95 cm, centre lamp at
Y = 315.176 on the menorah axis, lamp height Z = 1075 (150 cm = 18 tefachim at
50 cm/amah, per the book's row on p. 241).

---

## 4. Open review items — the honest list

### SVC-R-ORDER — **R** — the biggest one
**Which** five and **which** two is not stated in any passage read here.
Rambam 3:17 says five, then two; it does not name them. The sequence therefore
walks the seven **north to south, lamps 0–4 then 5–6**, and that ordering is an
**authored placeholder (D)**, chosen only because it reads cleanly on screen.
It must not be presented to a user as the order of the service. It is a
single edit to change (the two group sizes are already `LampSchedule` fields).

### SVC-R-ORIENTATION — **R**
Rambam holds the menorah is oriented north–south; Rashi holds east–west, and
the book records the Rashi reading as a drawn alternative (22:23a). We depict
Rambam **because the placed asset was built to Rambam** — this is a
consistency decision with `release_import_menorah_v4.spec.json`, not an
independent ruling. If the asset is ever rebuilt to Rashi, `Anchors::LampAt`
must be rebuilt with it.

### SVC-R-KETORES-POSITION — **R**
The golden-altar station sits after the last lamp, following Abaye's *seder
ha-ma'arachah* order (five lamps, blood of the tamid, two lamps, then ketores;
Yoma 33a). Rambam's own footnote at Temidin 3:17 places the re-entry after the
limbs were brought up, which is not quite the same cue. **We did not verify
Yoma 33a directly in this pass** — it is asserted here from the structure of
Temidin 3:17 and the project's existing incense dossier (`KET-DAILY-SEQUENCE`,
Mishnah Yoma 3:5), not from a reopened Yoma 33a page. Treat the relative
position as unsettled.

### SVC-R-BIAT-2-2 — **R**
Rambam extends "within the curtain" in Vayikra 16:2 to warn against
unwarranted entry into the whole House; the Kessef Mishneh questions that
reading. Our design consequence (no idle wandering) is conservative under
either reading, so nothing turns on it here.

### SVC-FX-CONTRACT — D — cross-agent coupling, pinned
`AMikdashFXDirector` (Astra's, already in the map) starts and ends the ketores
plume by matching the substring **"golden altar for the incense"** in this
actor's `GetCurrentActionText()`. The coupling is deliberately on the director's
side; this actor stays a pure pause and exposes no dispatcher. The phrase lives
only on the GoldenAltar station and only while dwelling there, so the plume
cannot start early or outlive the figure's presence. Pinned by
`ServiceScheduleMathTest.cpp`; do not reword that station's text.

### SVC-LAMP-KINDLE — H (order) / D (timing) — lamps dark until he kindles them (added 2026-09-11)
Per SVC-HATAVAH and the lamp station's own action text, every lamp station is:
clear the spent wick and oil, set a fresh wick and oil, kindle. Through cp12 all
seven flames burned from BeginPlay, so nothing was kindled on screen.
`MikdashService::LampBurning` (ServiceScheduleMath.h) now derives which lamps burn
from the runner's position ONLY: a lamp is dark from the start of a sequence until
the kindling moment of its own station, and burns from then until the next sequence
starts; while he waits outside, five burn and two are dark (Temidin uMusafin 3:17).
`AMikdashFXDirector` reads `AMikdashServiceActor::IsLampBurning` each frame. That
is read-only and on the director's side, like the ketores cue above. It matches
flames to lamps by POSITION, because on Candidate48 the director's flame array runs
south to north while the service counts north to south. The kindling moment is
`TendClipStartSeconds` 1.2 + `KindleAtClipSeconds` 7.6 = 8.8 s into the 14 s station
(D), which is when the authored hand (`Scripts/pilgrim_tend_v1.py`) is at the wick.
Not modelled: the western lamp's own law (every lamp is treated as found spent).
**cp15 amendment (D), 2026-09-11:** the lamps no longer all go out at the start of the
next sequence while he stands in the Ulam. Only the FIRST sequence is the morning, with
every lamp dark until his own kindling. In every later sequence a lamp that is still
burning stays lit while he is elsewhere and goes out at the CLEARING moment of its own
station (`TendClipStartSeconds` 1.2 + `ClearAtClipSeconds` 1.6 = 2.8 s, when the
authored hand reaches the bowl to remove the spent wick), then is kindled again at 8.8 s.
`LampBurning(..., ClearAtSeconds)`; a negative value keeps the cp14 rule. Pinned by
`ServiceScheduleMathTest.cpp` (the "cp15" block).
**cp15 light:** each lamp's light is the director's own point light, switched on at its
lamp's kindling, at 1 cd (`LampLightCandela`, about a candle; the cp14 value was built
UNITLESS and was ~0.002 cd). The static 90 cd `RELEASE_SanctuaryV2_MenorahLamps`
"cheat" that lit the lids from frame 0 is disabled on both maps (`Scripts/release_lamp_light.py`).
The flame card's emissive is raised to flame luminance (`LampFlameEmissiveScale` 5000)
so the flame reads; that adds no light.
Off switches: `bLampsDarkUntilKindled` on the service actor and `bLampsFollowService`
on the director. With either off, or with no running sequence in the map, all seven
lamps burn as before.

### SVC-R-WITHDRAWAL — **R**
The 20-second pause outside between the two groups of lamps stands in for a
service that happens elsewhere and is **not depicted**. Its action text says so
in plain language. Whether the withdrawal geometry for the daily incense (the
Heikhal and the Ulam-to-altar area, `KET-DAILY-LOCATION`) should also apply to
this figure's golden-altar station is unresolved and belongs to whoever owns
the incense system.

### SVC-R-GARMENTS — **R**, and currently **not depicted at all**
See §5.

### SVC-D-PACING — **D**
Every number: 14 s per lamp, 8 s in the Ulam, 4 s at the doorway, 6 s on the
stone, 5 s for the kuz, 20 s waiting outside, 30 s at the golden altar, 90 cm/s
walking, 90 s between sequences. **Nothing in the sources fixes any of them.**
They were chosen to land the loop at **290.5 seconds (4 min 50 s)**, inside the
commissioned 3–6 minutes. The Yom Kippur variant runs 346.7 s.

---

## 5. Garments — described, not modelled

**There is currently no Kohen Gadol garment asset in the project.** The actor's
lookup tries `MI_Garment_KohenGadolGold` first, and when it is absent falls
back to an existing pilgrim garment material and **says so in
`GetBodyStatus()`**, in those words: *"this is a STAND-IN, not the eight golden
garments."* Nothing in this build should be described as the eight garments.

Reference photographs: `SourceAssets/reference-ti/` holds the Temple
Institute's garment set, used with the owners' permission and **gitignored**
(`garments-kohen-gadol/`, `ephod/`, `choshen/`, `meil/`, `tzitz-mitznefet/`,
plus `garments-kohen-white/` for the Yom Kippur set). Notes for whoever builds
the variant, from those images and Rambam Klei HaMikdash ch. 9:

| element | colours and elements to reproduce |
|---|---|
| **Ketonet** (tunic) | white *shesh*, fine twisted linen, woven in a boxlike/checker weave, full length, long sleeves. |
| **Michnasayim** (trousers) | white linen, hip to thigh, worn beneath and not visible. |
| **Avnet** (sash) | long band, wound at the waist; **R** — the Kohen Gadol's sash is one of the points where Rambam and others differ on whether it is the same as an ordinary kohen's. Do not silently pick one. |
| **Me'il** (robe) | solid **techelet** (deep blue) beneath the ephod, sleeveless, with a reinforced neck opening; its hem carries alternating **gold bells** (*pa'amonim*) and woollen **pomegranates** (*rimonim*) in techelet, argaman and tolaat shani. The TI images (`meil/bells-and-pomegranates-gallery.jpg`, `rimon-large.jpg`) show the pomegranate form; note the wiki plate `צורת_הרימון_שפיו_פתוח_או_סגור` records the open-mouthed vs closed dispute — **R**. |
| **Ephod** | apron-like, worn at the back and tied in front, woven of gold thread with techelet, argaman, tolaat shani and shesh; two **shoham** (onyx/sardonyx) shoulder stones engraved with the twelve tribes, six per stone, in gold settings. TI has both the Rambam and Rashi reconstructions (`ephod/מראה_האפוד_לשיטת_הרמבם.jpg` vs `…לפי_שיטת_רשי.jpg`) — **R**, they differ in how the ephod sits. |
| **Choshen** | square breastplate, doubled, same five materials as the ephod, **twelve stones in four rows of three**, each engraved with a tribe, held to the ephod by gold chains and techelet cords so it never shifts (the reason for the third attendant in Klei HaMikdash 5:11). TI carries `12-tribal-stones-small.jpg` and `wiki-חקר_אבני_החושן.jpg`; the modern identification of several stones is **R** and must not be presented as settled. |
| **Mitznefet** | white linen turban, wound; TI shows the Kohen Gadol's form distinct from the ordinary kohen's migba'at. |
| **Tzitz** | gold plate across the forehead, tied with a techelet cord, engraved *kodesh la-Hashem*. TI's own plate `ציץ_שיטות` shows that the arrangement of those words across one or two lines is itself disputed — **R**. |

Practical note for the material author: the actor applies its garment material
to the slots named in `GarmentMaterialSlots` and then **reads each slot back**
to confirm, because in UE 5.8 a material setter can report failure on an
assignment that actually took. The verified count appears in `GetBodyStatus()`.

---

## 6. Consistency with the project's own research

- `Research/halacha-and-service.md` (item 9, *Clothes match the duty*):
  ordinary, high-priest and Yom Kippur sets are distinct and costume selection
  must follow role and current service. Honoured: the garment is chosen by the
  actor, recorded, and labelled a stand-in when it is one.
- `Research/halacha-and-service.md` (item 6, *the innermost chamber is not a
  reward*): nothing in this actor can grant an ordinary avatar entry past the
  paroches; the scenario flag is an authoring decision, not a player reward.
- `Research/ketores-service-and-smoke.md`: the golden-altar station is a
  **pause only**. No particles, no emitter, no smoke lifetime. That dossier's
  acceptance gate ("no particles before service begins; no repeating emitter
  after its authored end") is another system's to satisfy, and this actor does
  not pre-empt it.
- `SourceAssets/research/book-scene-requirements-20260907.json` p. 241
  (*Menorah*, verification: "Hebrew confirmed"): position certain — south of
  the Heikhal opposite the shulchan, 2.5 amot from the south wall, 5 amot from
  the KhK wall; branches north–south per Rambam with Rashi east–west as a drawn
  alternative; six wicks toward the middle lamp, middle lamp toward the KhK;
  height 18 tefachim; **"a three-step stone before it for the kohen"**; lit even
  on Shabbos. Every one of those that we model, we model as stated.
- Same file, p. 241 (*Golden incense altar*, "certain"): on the Heikhal centre
  line, between shulchan and menorah, slightly east. Our altar station at
  (-4650, 0) matches `release_scale_keilim.spec.json`, which cites the book's
  diagrams 22:28/22:29.
- Same file, p. 160 (*Items not mentioned by the navi*, "certain (book's
  method)"): the Menorah and golden altar are certainly present in the Third
  Temple though Yechezkel does not mention them. This is what licenses the
  scene existing at all in a Yechezkel-based reconstruction.

---

## 7. What is depicted versus what is asserted

**Depicted:** a figure in the Heikhal, walking a fixed route, standing on the
three-step stone, tending seven lamps in a group of five and a group of two
with a departure between them, pausing at the golden altar, and leaving —
repeating on a timer.

**Asserted as sourced:** that the Kohen Gadol may perform this service and does
walk in the Heikhal; that the lamp service is ordinarily an ordinary kohen's;
that a three-step stone stands before the menorah and the kohen stands on it;
that the service is five lamps, a departure, then two, with the kuz left on the
second step; that hatavah means clearing, refilling with a half-log, and
kindling (on Rambam's reading); that the six lamps face the centre; and that
the Kodesh HaKodashim is entered only on Yom Kippur.

**Asserted as nothing at all:** the order of the seven lamps; the identity of
the five and the two; every duration and speed; the garment appearance; the
figure's face, build and animation; the relative position of the incense; and
the entire content of the Yom Kippur inner service.

**Still required before any of this is taught as settled:** review by a
qualified person of the source hierarchy, the sacred-zone mapping onto this
mesh, the lamp order, the garment reconstruction, and the Yom Kippur module —
per the six review items already listed at the end of
`Research/halacha-and-service.md`. This build does not discharge any of them.
