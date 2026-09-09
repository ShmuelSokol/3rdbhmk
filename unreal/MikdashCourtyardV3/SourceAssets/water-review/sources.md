# Water in the Mikdash: what is certain, what is disputed, what this project authored

Referenced by `Plugins/MikdashRuntime/Source/MikdashRuntime/Public/WaterFlowMath.h`,
`Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashWater.h`,
`Scripts/create_water_geometry.py` and `Scripts/release_water.py`. Those files state that
every constant's provenance is here; this is that record.

Three statuses are used, and nothing is left unmarked:

* **CERTAIN** — stated in the text of Yechezkel, or in a Mishnah/Gemara/Rambam that this
  project's primary source itself cites. It may still be *modelled* wrongly; certain means
  the claim, not the geometry.
* **DISPUTED** — the sources genuinely differ, or the primary source differs from the plain
  sense of the navi. Both readings are recorded, and where the geometry can show both, it does.
* **AUTHORED** — this project's invention. No text gives it. Every centimetre of width, every
  depth in centimetres, every mikveh dimension and every bed slope is in this class.

The primary source is the user's book, **"Lishchno Tidreshu"**, read from
`mikdash book/Book-Source-Data.json` (367 page records) and
`mikdash book/Original-Hebrew-Book.pdf`. **PDF page = printed page + 105** throughout
(verified on 319→214, 324→219, 337→232, 340→235). The book's Third Temple material is the
**קץ הימין** / **השלמת שרת** layer.

> **Caveat carried on every book row.** Every English record in the export is marked DRAFT
> (`translationStatuses: {draft: 363}`), and the drafts can silently drop a load-bearing
> sentence — p. 116's statement of the two amah opinions is present in `hebrewInput` and
> **absent from the English**. Rows below are marked *Hebrew confirmed* where the Hebrew was
> read directly, and *English draft only* where it was not.

---

## 1. The stream of Yechezkel 47

### 1.1 The text — CERTAIN

| Claim | Source | Status | Built? |
|---|---|---|---|
| Water issues from **under the threshold of the House**, eastward, the House facing east | Yechezkel 47:1 | CERTAIN | yes — `COURT_ROUTE[0]`, x −2478, y +400, under the Ulam threshold |
| It comes down from **under the right (south) side** of the House | Yechezkel 47:1 | CERTAIN | yes — the route bears to +Y from the start |
| It passes **south of the altar** (מנגב למזבח) | Yechezkel 47:1 | CERTAIN | yes — running line at y +1050; measured clearance to the altar yesod **203.8 cm** |
| At the outer east gate it is **trickling** (מפכים) from the **right (south) shoulder** | Yechezkel 47:2 | CERTAIN | yes — route enters the vestibule at y +180, south of the gate axis |
| The man measures **a thousand amot** and the water is **to the ankles** (אפסים) | Yechezkel 47:3 | CERTAIN | yes — Stage::Ankles, 11.9 cm |
| Again a thousand — **to the knees** (ברכים) | Yechezkel 47:4 | CERTAIN | yes — Stage::Knees, 48.45 cm |
| Again a thousand — **to the loins** (מתנים) | Yechezkel 47:4 | CERTAIN | yes — Stage::Loins, 90.1 cm |
| Afterward a thousand — **a river he could not pass over**, water to swim in | Yechezkel 47:5 | CERTAIN | yes — Stage::River, 178.5 cm, over a 170 cm stature |
| It goes down to the **Aravah** and into **the sea**, and the sea's waters **are healed** | Yechezkel 47:8 | CERTAIN | **no — asserted only** |
| **Fishermen** stand from **Ein Gedi to Ein Eglayim**, fish of the Great Sea, exceeding many | Yechezkel 47:9-10 | CERTAIN | **no — asserted only** |
| The **marshes and swamps are not healed**; they are given to salt | Yechezkel 47:11 | CERTAIN | **no — asserted only** |
| On **both banks**, trees whose **leaf does not wither** and whose **fruit does not fail**; new fruit **every month**, because their water **issues from the Mikdash**; the fruit for **food**, the leaf for **healing** (לתרופה) | Yechezkel 47:12 | CERTAIN | **no — asserted only** |

The last four rows are the reason the receipt separates *depicted* from *asserted*. The Dead
Sea is roughly 35 km east of the Mount; the built channel stops at the fourth measurement,
4000 amot = 2.00 km at the project amah. Nothing east of that is modelled, and the trees of
47:12 are not planted on the built banks either — planting them along a 2 km stub would
depict the verse in the wrong place, which is worse than not depicting it.

**Not found in the book at all** (checked across all 367 records, Hebrew and English):
`אפסים` / `ברכים` / `מתנים` as stage terms, `אלף אמה` in a 47:3-5 sense, Ein Gedi, Ein
Eglayim, ערבה, ים המלח, and the locust-antenna aggadah (Yoma 77b-78a). Part I of the book
covers **Yechezkel 40-42 only**; 43 and 47 appear as cross-references
(`SourceAssets/research/book-scene-requirements-20260907.md`, line 15). So on the stream
itself the book contributes exactly one claim, the next row.

### 1.2 The route — DISPUTED, and the dispute is modelled

**The book's reading.** `Book-Source-Data.json` record **340** (printed **235**), running
header יחזקאל פרק מ״ב פסוק יב׳, layer השלמת שרת §35, "Location of the Gates in the Third
Beis" — *Hebrew confirmed*:

> **שער המים - הוא שער הדרומי בחצר הפנימית, כמבואר לקמן בנביא (מ״ז א׳-ב׳), שעתיד לצאת מקדש הקדשים מים לשער דרום ולכן נקרא כך בבית שני**

("Shaar HaMayim — this is the southern gate in the inner court, as explained further in the
navi (47:1-2), that in the future water will go out from the **Kodesh HaKodashim** to the
**southern gate**, and therefore it was so called in the Second Beis.")

Three claims in one sentence: the source is the **Kodesh HaKodashim**, the exit is the
**southern gate of the inner court**, and that is *why* the Second Temple gate bore the name.
The page reference given in the task brief is confirmed verbatim. `שער המים` occurs on
exactly three pages (315, 327, 340); `מקדש הקדשים מים` and `והנה מים יוצאים` on **340 only**.

The same page quotes Middos 1:4 on the Second Temple's Shaar HaMayim — the Sukkos flask drawn
from the Shiloach for the water libation — and adds *"ויש אומרים"*, "and **some say** it is
named for the future written in Yechezkel 47:1-2". Worth recording precisely: **the book turns
a *some-say* in the commentators into its own positive identification for the Third Temple.**

**The plain sense.** 47:1-2 has the man brought out *by way of the north gate* and led round
to the **outer east gate**, where the water trickles from the right shoulder. The thousands
are then measured from there.

| | Book (p. 340) | Plain sense of 47:1-2 |
|---|---|---|
| Source | Kodesh HaKodashim | under the threshold of the House |
| Exit | inner court **south** gate (Shaar HaMayim) | outer **east** gate, south shoulder |
| Measuring datum | not stated | outside the outer east threshold |

**What is built.** `create_water_geometry.py` builds the **east** route as the primary
geometry (`COURT_ROUTE`, group `court`) and carries the **south** route as an optional branch
(`SOUTHGATE_ROUTE`, group `southgate`), taken off the running line at x −430 and out under
the inner south threshold. Neither is asserted over the other; the east one is primary only
because the four measured stages hang off the outer east threshold and cannot be positioned
without it.

**An asymmetry to record rather than smooth over.** `WaterFlowMath.h` defines
`StageDistanceAmot` as distance *"east of the outer east gate"*. The runtime is therefore
committed to the east reading in a way the geometry script is not. If the south route is ever
promoted to primary, that comment and the datum with it must move.

### 1.3 Are the four stages literal distances? — DISPUTED, and **the book does not address it**

The measurements are certain as text. Whether the prophet is pacing real ground or giving a
schema of increase is a live question in the commentators; a schematic reading takes the
thousands as a figure for continuous growth rather than four surveyed marks.

**The book says nothing about it** — it does not reach chapter 47. So this is *not* a case of
the project departing from its primary source; it is a case of the primary source being
silent and the project having to choose. It chose **literal**, because this is a measured
reconstruction and a schema cannot be built to scale. The alternative is recorded here and in
the geometry manifest rather than hidden, and the choice is reversible: it lives entirely in
`StageDistanceAmot` and `STAGE_SPACING_AMOT`.

### 1.4 Depths, widths and everything hydraulic — AUTHORED

| Quantity | Value | Status |
|---|---|---|
| Assumed stature | 170 cm | AUTHORED |
| Ankle / knee / loin / swim fractions of stature | 0.07 / 0.285 / 0.53 / 1.05 | AUTHORED (anthropometric, not textual) |
| Resulting depths | 11.9 / 48.45 / 90.1 / 178.5 cm | AUTHORED |
| Trickle at the gate (מפכים) | 0.6 cm | AUTHORED |
| Top widths | 1 / 4 / 10 / 20 / 50 amot | **ENTIRELY AUTHORED — no source gives a width anywhere on the stream** |
| Interpolation between the marks | Fritsch–Carlson monotone cubic Hermite, SIAM J. Numer. Anal. 17(2), 1980 | AUTHORED; chosen only because it provably cannot make the water shallow between two marks |
| Bank side slope 1.2 H:V, kerb 8 cm, bank 22 cm, bed slab 14 cm, court sink 35 cm | — | AUTHORED |
| Far-field grade east of the mount | 2.5% | AUTHORED |
| Manning n: 0.015 dressed stone / 0.025 rubble / 0.030 natural earth | — | Standard open-channel engineering values, not a source about the Mikdash |
| Opacity ramp, full at 120 cm depth | — | AUTHORED |

The aggadic tradition that the stream begins as fine as a locust's antenna and swells as it
goes (**Yoma 77b-78a**) is corroboration for the *shape* of the width curve — small at the
threshold, broad at the river — and is **not** a source for any number. It does not appear in
the book.

### 1.5 The conduit levels — AUTHORED, but forced by clearance

The bed levels through the inner court's east range are not a design choice. The gate wall
jamb, the cell connecting doorways and their lintels all stand from Z 500 up and the cell
plinth occupies Z 300–499, so the conduit must lie wholly inside that band. Bed 450 puts the
cover slab top at 485 and leaves **15.0 cm** under the jamb. Recorded because an earlier draft
used 478/460/445, which drove the slab through the jamb footing.

---

## 2. Mikvaot

### 2.1 Forty se'ah

| Claim | Source | Status |
|---|---|---|
| A mikveh must hold forty se'ah | Mishnah Mikvaos 1:7 | CERTAIN |
| Forty se'ah is the volume of a pit one amah by one amah by three amot deep — i.e. **three cubic amot** | Eruvin 4b | CERTAIN |
| Tefach = 9.6 cm (Chazon Ish) → amah 57.6 cm; tefach = 8 cm (R' A. C. Naeh) → amah 48 cm | **Book, PDF p. 116 = printed p. 11**, Yechezkel 40:5, באור חי layer — *Hebrew confirmed; the English draft drops this sentence entirely* | CERTAIN (as a report of the two opinions) |

Arithmetic, three cubic amot at each amah:

| Opinion | Amah | Forty se'ah | One se'ah |
|---|---|---|---|
| R' A. C. Naeh | 48 cm | 331 776 cm³ = **331.8 L** | 8.29 L |
| Chazon Ish (stringent) | 57.6 cm | 573 309 cm³ = **573.3 L** | 14.33 L |
| Project modelling amah | 50 cm | 375 000 cm³ = **375.0 L** | 9.375 L |

Each modelled pool holds **937.5 L** of free water (a 200 × 100 × 100 cm basin less the solid
of its stair), which is **1.635 ×** the most stringent figure. Numbers verified by
`WaterFlowMathTest.cpp` and recorded in `tests.json`.

> **This is arithmetic on published shiurim, not a halachic ruling.** Whether a given pool is
> a kosher mikveh depends on the provenance of the water, its connection to the ground, the
> absence of drawn water and much else that no header can encode. `FortySeahTest()` reports a
> volume comparison and nothing more.

**`סאה` / `se'ah` / `ארבעים סאה` appear nowhere in the book** — checked across all 367 page
records. The forty-se'ah figures are the project's arithmetic on Eruvin 4b and Mikvaos 1:7.

### 2.2 Which chambers — CERTAIN as to the requirement, DISPUTED as to place, AUTHORED as to storey

Every book placement below is in the השלמת שרת layer and carries **the author's own asterisk,
"for study only"** — his marker for a reconstruction he does not assert. *English draft only
unless noted.*

| Mikveh | Requirement (CERTAIN) | Book placement (p.) | What is built, and the departure |
|---|---|---|---|
| **Kohanim, daily before service** | Tamid 1:2; Rambam Biat HaMikdash 5:4 — no kohen enters the Azarah for service, even when pure, until he immerses | **p. 325** (printed 220): next to Beis HaMoked, **north lower chambers, 2nd floor** | Built at (−4000, −4400), rim Z 425, in the built **north priestly chamber block** (Yechezkel 42), ground storey. **The north lower chambers are not built in this map** — research gap 6 — so the storey is lost and the block substituted |
| **Kohen Gadol, year-round** | Same immersion requirement; his own pool, apart from the other kohanim | **p. 326** (printed 221): **outside the holy area** (בחול), lower chambers, north, 2nd floor, **next to** the kohanim's Beis Tevilah | Built at (−3000, −4400), rim Z 425. Same block substitution; **kept adjacent** to the daily mikveh, as the book has it |
| **Kohen Gadol, Yom Kippur** | Yoma 30a: **five immersions and ten sanctifications**, all in the kodesh above Beis HaParvah save the first | **p. 326**: western of the **six southern halls** of the inner court, **3rd floor above Beis HaParvah**. The book records that **the sources differ**: Middos 5:3 puts Beis HaParvah's roof in the **north**, Yoma 19a and Rambam Beis HaBechirah 5:17 in the **south** | Built at (−1350, +2150), rim Z 625, on the inner court floor **on the south**, beside the built Song chamber. Keeps the book's side and its "in the kodesh" requirement; **loses the storey** — the six southern halls are not built |
| **Chamber of the metzora'im** | Middos 2:5 with Tiferes Yisroel — the metzora immerses there before the thumb-blood on the eighth day | **p. 333** (printed 228): outer court, **north lower chambers, western side, 1st floor**, near the entrance to the Ezras Yisroel; "in the chamber there is a mikveh for immersion" | Built at (−7000, −4400), rim Z 425, westernmost room of the built north priestly block. Outer-court lower chambers not built |

Also on p. 325, not modelled: **Beis HaTevilah for a ba'al keri**, reached by the winding path
under the Birah (Middos 1:1), with a fire there. And p. 319 (printed 214), Middos 1:6 on the
Beis HaMoked's north-west chamber: *"there they would descend to the mikveh"* — Second Temple,
in the chol.

### 2.3 Steps, and the separating wall — AUTHORED

**The book gives no dimension, no step count and no partition for any mikveh.** The following
are entirely this project's:

| Item | Value | Status |
|---|---|---|
| Inner basin | 200 × 100 cm, water 100 cm deep | AUTHORED — long enough to lie down in |
| Steps | 4 risers of 25 cm, going 25 cm, descending from the east rim. **Three solid blocks**: the lowest tread is the basin floor itself | AUTHORED |
| Wall 30 cm, floor slab 25 cm | — | AUTHORED |
| **Separating screen** — Kohen Gadol's Yom Kippur mikveh only, 250 cm high on the north side | **Yoma 3:4** — a sheet of fine linen was spread between the Kohen Gadol and the people at his immersion; cf. Rambam Klei HaMikdash 5:3 and book p. 326, "they should not see him naked" | CERTAIN that a screen is called for; AUTHORED in every dimension |

On the brief's phrase "separating wall where the sources call for one": the sources of this
corpus call for a **linen screen at one mikveh**, not a masonry wall at any. It is modelled as
a standing screen, which is what Yoma 3:4 describes. No mikveh here has a dividing wall down
the middle, and none of this project's sources asks for one.

---

## 3. The kiyor — already present; not rebuilt

**Already in the map, so this work does not touch it.** It is part of the imported
architecture FBX, not a keilim import: it appears in **no** keilim receipt (checked
`SourceAssets/third-party/native-import-vessels-*.json`, `vessels-review/KeilimTIV1/`,
`heikhal-keilim-spec.json`, `Scripts/release_import_keilim_ti.spec.json`). Its parts carry
generic modelling names in `SourceAssets/architecture-manifest.json`:

| Part | `sourceName` | Bounds, Unreal cm |
|---|---|---|
| Basin | `Hollow basin with inner wall` | (−2054, +1396, 690) → (−1846, +1604, 750) |
| Base (ken) | `Turned pedestal` | (−2010, +1440, 625) → (−1890, +1560, 696) |
| Spout | `Spout 1` | (−1952.1, +1588.0, 710.0) → (−1948.0, +1605.4, 720.1) |
| Fittings | `Copper fitting` ×4 | within the above |

Diameter ≈ 208 cm ≈ 4.16 amot; between the Ulam and the altar, on the **south**, which is
where the book puts it. `create_water_geometry.py` anchors on the basin bounds and treats the
kiyor as a **blocker**, never a host: the stream fails the export if it touches it. Measured
clearance from the channel to the basin, **422.3 cm**; to the pedestal, **480.9 cm**.

| Claim | Source | Status | Built? |
|---|---|---|---|
| A kiyor and its base, for washing hands and feet, between the Ulam and the altar | Shemos 30:17-21; book **p. 173** (printed 68), Yechezkel 40:47 note 27 — "the Kiyor and its base for washing between the Ulam and the Mizbei'ach — **d'Oraisa**" | CERTAIN | **yes, already** |
| The **pit** into which the kiyor is lowered at night, so its water is not invalidated | Book p. 173, same note | CERTAIN | **no** — listed as gap 11 in `book-scene-requirements-20260907.md` |
| The **muchni** (pulley/wheel) that raises and lowers it — **d'Rabbanan** | Yoma 37a; book p. 173, same note, "the pulley — d'Rabbanan" | CERTAIN | **no** — gap 11 |

So: **the kiyor is present and is not re-created here.** Its pit and pulley are absent, and
that absence is a known gap owned by other work, not by this pass.

---

## 4. Other water in the building, recorded but not built by this pass

| Item | Source | Status | Built? |
|---|---|---|---|
| **Lishkas HaGolah** — a fixed pit with a **wheel** over it, supplying water to the whole Azarah | Middos 5:4; book **p. 337** (printed 232) | CERTAIN | no — the book absorbs it into the lower chambers' first floor, which are not built |
| **Beis Horadas HaMayim** — the roof-water descent on the **south** of the west block, mirroring the Mesibah on the north, **5 amot** wide with a 5-amah wall | Book **p. 210** (printed 105), *Hebrew confirmed*; the book's p. 212 n. 39 is candid: *"in the Navi the Mesibah was not mentioned, nor Beis Horadas HaMayim… but in Mishkenos Elyon (daf 181, 204) he mentions them."* Middos 4:7 gives 3 amot; the book follows Mishkenei Elyon's 5/5 | DISPUTED (a Middos/Mishkenei Elyon completion, **not** from the navi) | present as architecture already |
| **Nisuch HaMayim** — the Sukkos water libation, the flask drawn from the **Shiloach** and brought in through Shaar HaMayim | Middos 1:4, Sukkah 4:9; book p. 340 | CERTAIN for the Second Temple. **The book makes no Third-Temple ruling on how the water arrives** | no — open question, not a claim |

---

## 5. The amah — and a 4% rounding this project should own

| Value | Where | Status |
|---|---|---|
| **50 cm** — the project's modelling amah, used by every geometry script here | `WaterFlowMath.h` `ProjectAmahCm`, `create_water_geometry.py` `AMAH` | AUTHORED. `WaterFlowMath.h` says so in terms: *"a round modelling figure, NOT a claim about the halachic amah"* |
| **48 cm** (R' A. C. Naeh, tefach 8 cm) | Book **p. 116**, *Hebrew confirmed, missing from the English draft* | CERTAIN as a report of the opinion |
| **57.6 cm** (Chazon Ish, tefach 9.6 cm) | Book p. 116, same | CERTAIN as a report of the opinion |

**The book's own working conversion is 48 cm, not 50.** On PDF **p. 359** (printed 254),
Yechezkel 42:16-19, it converts 500 kanim = 3000 amot to *"קילומטר וארבע מאות וארבעים מטר
בערך"*, about **1440 m** — which is 0.48 m per amah exactly. The project's 50 cm is therefore
a rounding **away from** its own primary source, and every book-derived length in this scene
is about **4.2% large** as a result. That is a defensible modelling decision (it keeps this
water consistent with every other script in the repo, which is worth more than 4%), but it is
a decision, and it is recorded here rather than left to be discovered.

The four stages at 4000 amot are 2000 m at the project amah and would be 1920 m at the book's
own 48 cm — a 80 m difference over the built stub.

*(Low confidence, flagged not used: pp. 361/363 give 3000 × 3000 = 9 000 000 sq amot as "432
square kilometres = 432 dunam". Both halves are internally inconsistent and disagree with
48 cm/amah, which gives ≈ 2074 dunam. Not carried into anything here.)*

---

## 5a. Where this water actually sits, on each of the two maps

Released 9 September 2026 onto **both** integrated maps, one target per run
(`release_water.py -Candidate48` / `-Main50`). The geometry is a single set of frozen OBJs
authored once, in the 50 cm modelling amah, in the legacy main map's world centimetres. It
reaches the 48 cm candidate under a **similarity transform**, not by re-export:

| Target | Amah | Placement of every water actor | Receipt |
|---|---|---|---|
| `Amah48Candidate_.../Maps/Walkthrough` — the configured default and the cook map | 48 cm | uniform scale **0.96**, translation **(-248, 0, 0) cm**, no rotation | `native-release-water-Candidate48-20260909T173650147007Z.json` |
| `IntegratedReviewV2/Maps/Walkthrough` — legacy main | 50 cm | the identity | `native-release-water-Main50-20260909T173944440978Z.json` |

The candidate transform is not a choice made here; it is the one its architecture already
carries. `release_amah48_candidate.py` rescaled all 2,633 architecture actors by 48/50 = 0.96
about the world origin, and `release_aron_alignment.py` then translated the temple by
(-248, 0, 0) so that the Aron stands over the rock. The composition is
`p_candidate = 0.96 · p_main50 + (-248, 0, 0)`, and the release **measures it off the live level
before it spawns anything**: every actor whose mesh resolves to the architecture manifest is
compared, in centimetres, with its manifest bounds carried through the declared placement.
On the candidate 2,578 of 2,579 non-vessel actors matched to 0.0000 cm. Placed at the identity
instead, the stream would have been 4% oversized and **2.48 m east of its own channel**.

**Two consequences that are this section's whole reason for existing.**

1. On the candidate the water is 4% *smaller* than the geometry `create_water_geometry.py`
   authored, because it wears the same 0.96 as the building around it. That is the right answer
   visually — but `AMikdashWater` and `WaterFlowMath.h` still compute in the 50 cm frame
   (`ProjectAmahCm = 50.0`). **The depths, velocities and forty-se'ah volumes the driver reports
   describe the authored channel, not the placed one**: lengths high by 1/0.96, volumes by
   1/0.96³ ≈ 13%. Nothing corrects this, and no mikveh verdict on the candidate should be quoted
   until it does.
2. The FutureMountV1 terrain and the metric Jerusalem context were **not** rescaled with the
   architecture. So on the candidate the four measured stages, which are laid out east in
   authored amot, end 4% short against unscaled ground — 1,996 m rather than 2,079 m. This is
   inherited from the candidate itself, not introduced by the water, and it is the same 4%
   rounding §5 already owns, now visible as a physical gap.

### What the live clearance established, and what it did not

On both levels: **0 blockers in the built Temple**, and 42 host engagements — the conduit cut
into Ulam stair, Ezras Kohanim floor, the Raised priest court foundation, the twelve Outer E
stair treads and the rest. The tightest genuine clearance is between `Court_Trough_01` and the
House-and-Ulam foundation union: **5.13 cm on Main50, 4.92 cm on the candidate** — the same
number times 0.96, which is itself a check that the transform landed. Deepest deliberate
engagement into a host: 100.56 cm into the Ulam stair on Main50, 96.53 cm on the candidate.

Three things are **explicitly not cleared** by that number, and are recorded rather than
rounded away:

* **316 terrain tiles** were excluded by name. A heightfield cannot be decomposed into boxes,
  and a conduit sunk into the mount is meant to meet it.
* **3 modern city stone paths** are genuinely intersected — deepest 1.86 m on Main50, 1.95 m on
  the candidate — where the stages run ~2 km east across the metric Jerusalem depiction. The
  stream cannot avoid the city it runs through; nobody has looked at these by eye yet.
* **All 13 instanced static-mesh actors** in the level — the five `JCTX_ISM_` city layers,
  `RELEASE_CrowdField` and the rest — are neither cleared nor blocked. An ISM bounds every
  instance it holds in a single box that encloses the site: on one run six of them reported a
  contact against nearly every one of the 2,307 sub-boxes; on the next, the same six had not
  rebuilt their instances, bounded a point, and never reached the broad phase. Both readings are
  worthless, so the receipt counts every instanced actor in the level (13), how many overlapped
  the water (6) and how many held no instances at all (7), and calls all of them untested.

Geometry and material wiring only. No visual acceptance, no walking, no lighting build, no
cook, no halachic acceptance is established by any of this.

---

## 6. Summary: depicted versus asserted

**Depicted** — geometry exists and can be walked up to: the channel from under the Ulam
threshold, south of the altar, under the altar ramp, through the inner east range, across the
outer court to the south shoulder of the outer east gate; the four measured stages east of it
to 4000 amot with a kerb stone and a gauge post at each mark; four mikvaot with steps and one
screen; the south-gate branch on request.

**Asserted only, never depicted** — the descent to the Aravah; the sea and its healing; the
fishermen from Ein Gedi to Ein Eglayim; the marshes left to salt; and the trees of 47:12 on
both banks, evergreen, monthly-fruiting, fruit for food and leaf for healing. All lie tens of
kilometres beyond the map, and the built channel stops at the fourth measurement.

**Present but owned by other work** — the kiyor. **Known absent** — its pit and muchni,
Lishkas HaGolah, the lower chambers that the book's own mikveh placements depend on.
