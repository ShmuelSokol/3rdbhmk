# The precinct becomes today's Temple Mount — decision record, 15 September 2026

The Third Temple plateau stops being the Yechezkel 42:15-20 square and becomes the outline of
the Haram esh-Sharif esplanade as it stands today. This page records the decision, the
measurement that supports it, and — in full — what it costs.

Files: outline `haram-outline.json` (frozen, 66 points); generator
`Scripts/create_haram_outline.py`; arithmetic
`Plugins/MikdashRuntime/Source/MikdashRuntime/Public/EnclosureMath.h`; earlier decisions
`YECHEZKEL-DEFAULT-20260908.md` (8 Sep) and `PLAZA-DESIGN-20260909.md` (9 Sep);
sourcing `sources.md`.

Every claim below is marked **sourced**, **user decision**, **derived** or **authored**, on the
same convention as `sources.md`.

---

## 0. The decision

> "id like the current modern day temple mount outline be the third temple plateau - meaning
> the huge area we cleared away lets revert it back"
>
> — Shmuel, 15 September 2026

Asked how far the platform should shrink: **exactly today's Temple Mount outline** — every
building hidden or cleared outside those walls stays standing in the Third Temple view too, so
the Temple sits inside the existing city rather than on a cleared expanse.

Asked where the Temple itself should sit: *"isnt it already centered on the rock?? thats what
i want."*

Shown two boundaries with their costs — **A**, the true Haram trapezoid on the four mapped
walls, and **B**, a cheaper axis-aligned box that would still have had a sourced number under
it — he chose **A**, knowing B was cheaper and better-sourced. So the plateau follows the real
walls.

**User decision:** the boundary, and that the modern city outside it stays standing.
**Sourced:** nothing about this outline. See §5 — that is the honest cost.

---

## 1. Is the Temple already centred on the rock? — **yes, the Holy of Holies is; the court is not**

**Measured, not assumed.** The Dome of the Rock is OSM way 4709536, an octagon of 9 points (8
unique, first repeated). Its **area centroid is exactly (−6300.0, 0.0) cm**.

| the point you take as "the Temple's centre" | position | offset from the rock | verdict |
|---|---|---:|---|
| **Kodesh HaKodashim / Aron centre, Main50** | (−6200, 0) | **1.00 m west** | **on the rock** |
| Kodesh HaKodashim / Aron centre, Candidate48 | (−5952, 0) | 3.48 m west | on the rock, but see below |
| court supporting platform centre (world origin) | (0, 0) | **63.00 m east** | not on the rock, and never was |
| measured architecture AABB centre | (550, 0) | 68.50 m east | not on the rock |

**The right point is the Holy of Holies, not the court centre.** The Even HaShetiya is the
floor of the Kodesh HaKodashim (Yoma 5:2), not the middle of the Azarah, so the Aron centre is
the only anchor the question can mean. On that anchor the answer is **yes: 1.00 m on Main50,
inside the 4.24 m uncertainty the evidence supports.** The 63 m figure for the court centre is
not an error — the Temple is deliberately not centred on its own platform.

**Uncertainty, and why it cannot be reduced here: ±4.24 m** (root-sum-square of OSM outline
2.0 m, dome centre vs octagon centroid 0.5 m, rock centre vs dome centre 3.7 m — a 13 m rock
axis inside a 20.4 m drum). No surveyed plan of the rock has been obtainable;
`ARON-ON-EVEN-HASHETIYAH-20260908.md` records that ritmeyer.com and madainproject.com refused
automated fetches. **Nothing in this project can place the rock better than ±4.24 m.**

**Candidate48 carries a systematic error worth removing.** Of its 3.48 m, **2.48 m is not
uncertainty** — it is the .96 amah conversion having been pivoted at the outer altar
(`fixedOriginCm [0,0,0]`), sliding the Aron east by 6200 × 0.04. The re-pivot
`ARON-ON-EVEN-HASHETIYAH-20260908.md` §5 already recommends (translate the converted Temple
set by (−248, 0, 0); set `MikdashSceneUnits.FixedArchitectureOriginCm` to (−6200, 0, 0)) brings
Candidate48 to a 1.00 m residual, identical to Main50. **Folded into this work** so the Holy of
Holies sits on the rock on both maps rather than one.

### The alignment is proved, not asserted

`jerusalem.json` points are **amot at 0.5 m** and the level already carries
`UE_cm = ((x + 17.5097) × 50, (y − 0.55135) × 50)` — applied **exactly once**. Proof: OSM
Western Wall (way 817206833) vertex 0 lands at (−15127.5, 11907.9) cm; the KotelStoneV2 E0 mesh
corner is at (−15138.7, 11908.1). **11.2 cm of error over a 150 m lever.**

---

## 2. The new boundary — **derived**, and how

The OSM export carries **no feature named "Temple Mount" or "Haram"**, so the outline is
derived. Three witnesses existed and they are not of equal quality.

### The witness used: the four mapped retaining walls

Four `kind == "wall"` ways chain end to end, in this order, with **a closure gap of 0.000 cm**:

| order | OSM way | reversed | what it is |
|---|---|---|---|
| 1 | 26554724 | no | north wall, then the west wall down to the Kotel |
| 2 | 137726908 | **yes** | west wall, south part, to the south-west corner |
| 3 | 1080613976 | no | south wall, eastern part |
| 4 | 391433907 | no | east wall, back to the north-east corner |

OSM way 1080613975, named **"Southern Wall"** (البراق الجنوبي), is a 2-point *chord* across the
south wall, not the traced wall. It is recorded because it is the feature that **names** the
wall, and it is **not used** — a chord cannot bound.

### That the ring is the Haram, and not something else — seven checks, all passing

| feature | inside the ring? | expected |
|---|---|---|
| Dome of the Rock | yes | yes |
| Dome of the Chain | yes | yes |
| Al-Aqsa Mosque | yes | yes |
| Dome of the Tablets (Kaufman's candidate) | yes | yes |
| Western Wall (the Kotel stones) | yes | yes |
| **Western Wall Plaza** (the modern prayer plaza) | **no** | **no** |
| Yeshivat HaKotel | no | no |

The last two matter most: the ring correctly puts the **Kotel stones on the boundary and the
prayer plaza outside it**, which is exactly the real relationship and is the check an eyeballed
outline would fail.

### That its size is right — four independent wall runs and the area

| wall | derived | published (secondary) | error |
|---|---:|---:|---:|
| north | 319.2 m | 310 m | +9.2 m (+3.0%) |
| west | 492.6 m | 491 m | **+1.6 m (+0.3%)** |
| south | 281.3 m | 280 m | **+1.3 m (+0.5%)** |
| east | 470.8 m | 466 m | +4.8 m (+1.0%) |
| **area** | **14.24 ha** (142,387 m²) | ~14.4 ha | **−1.1%** |

Five independent quantities, none used to build the ring, all agreeing within 3%. **That is
what makes this derivation defensible rather than eyeballed.**

### The witnesses not used

* **The exporter's Haram terrain edit** — *corroboration only.* The level grid was raised by up
  to 42.7 amot (21.4 m) under the Haram to flatten the esplanade. Only **76–82%** of the raised
  cells fall inside the ring and the raised band sits **offset east** of it, because the edit is
  a 25 m-grid surface treatment of the esplanade, **not the wall line**. It independently says
  "something flat is here" and is too coarse to bound anything.
* **The surrounding street and building rings** — *not used.* They bound the Old City quarters
  around the Haram, not the Haram.

### The outline, in numbers

```
66 points, closure gap 0.000 cm
area          142,387 m²  =  14.24 ha
extents       X (west..east)   −21,434 .. +15,074 cm
              Y (north..south) −25,327 .. +26,107 cm
corners       NE (10,347, −25,327)   NW (−21,434, −22,372)
              SW (−12,680,  26,107)  SE ( 15,074,  21,512)
centroid      (−2,273, −423) cm
```

(Frame: +Y is **south**, so the most negative Y is the north wall.)

---

## 3. Do the Temple's courts fit? — **yes, with room to spare**

| | half-extent | across | fits inside the ring |
|---|---:|---:|---|
| court supporting platform, Main50 | ±8,100 cm | 162.0 m | **yes** |
| court supporting platform, Candidate48 | ±7,776 cm | 155.5 m | **yes** |

Clearance from each platform corner to the nearest Haram wall (Main50): **NW 103.1 m, NE 38.4 m,
SE 55.4 m, SW 76.1 m.** The tightest is the north-east corner at 38 m. Candidate48 is 3–4 m
easier on every corner.

The rock itself stands **106.2 m** from the nearest wall.

### What does *not* fit, and this is the structural finding

Neither sourced reading fits inside today's outline **on the Temple's own axes**:

| reading | side | centred on the rock | centred on the court |
|---|---:|---|---|
| Yechezkel 3000 amot @48 cm | 1,440 m | no | no |
| Yechezkel 3000 amot @50 cm | 1,500 m | no | no |
| Middot 500 amot @48 cm | 240 m | **no** | **no** |
| Middot 500 amot @50 cm | 250 m | **no** | **no** |

Middot's 500-amah square fails only **narrowly** — the largest square that fits centred on the
rock is **186.7 m** (373 amot @50 cm) and centred on the court **232.0 m** (464 amot). A 500-amah
square *does* fit somewhere inside the Haram (the largest axis-aligned square that fits anywhere
is **267 m**, 535 amot), but the nearest feasible centre is **38 m from the rock** — it would
have to be slid off the Holy of Holies to fit, which defeats the point.

**So no square boundary can be both sourced and centred on the rock inside today's walls.**
That is the real reason the outline has to be the trapezoid, and it is worth stating plainly
rather than leaving as an aesthetic preference.

---

## 4. What it costs in earth — **the strongest evidence the decision is right**

The 3,000-amah square required a flat deck pushed out to the Hinnom and the Kidron. Today's
outline does not. Measured on a 5 m grid over the 14.24 ha ring, against a flat deck at Z 0:

| | fill | cut | over |
|---|---:|---:|---|
| **Haram outline**, vs the level's own tiles | **0.65 Mm³** | 0.004 Mm³ | 14.24 ha |
| **Haram outline**, vs the raw OSM DEM | 1.25 Mm³ | 0.004 Mm³ | 14.24 ha |
| 3,000-amah square, Candidate48 | 76.84 Mm³ | 12.45 Mm³ | 207 ha |
| 3,000-amah square, Main50 | 86.96 Mm³ | 13.72 Mm³ | 225 ha |

**The earthwork falls by a factor of about 118** against the level's own terrain. **45.7% of the
new footprint is already within 50 cm of Z 0**, because the exporter had already flattened the
middle of the Haram to very near the Temple datum.

Two consequences, both predicted and both confirmed:

* **The retaining ring largely dissolves.** The square's south face was retained for its entire
  1,440 m at up to **136.9 m**. The deepest ground anywhere inside the new ring is 709.9 m, so
  the deepest retaining is **≈38 m**, at the south-east corner over the Kidron. That is not a
  disappointment — **the real Herodian south-east corner stands about 45 m above bedrock**, so
  the new number lands in the right range for the first time. The 137 m face was an artefact of
  pushing a flat deck to the Hinnom.
* **The approach stairs largely dissolve.** `APPROACH-DESIGN-20260910.md` exists because the
  deck stood 60.6 m above the street at the south-west gate and 50.4 m at the south-east, and a
  1:4 stair driven outward never met the ground. On today's outline there is no 60 m drop to
  bridge, so most of that structure is no longer needed. **Say so when it happens** — it is the
  clearest evidence that this decision was right.

---

## 5. What this costs in sourcing — **stated, not buried**

**The 3,000-amah square is the ONE measurement in the whole precinct that is sourced.**
Yechezkel 42:15-20 with 40:5: five hundred reeds of six amot, measured from outside. The book —
*Lishchno Tidreshu*, קץ הימין — holds that reading explicitly and converts it itself to "a
kilometre and four hundred and forty metres approximately". Everything else in the precinct —
the gate positions, the wall section's substructure, the ground profile, the plaza, the
drainage, the approaches — is authored.

**Replacing that square with today's Haram outline makes the built precinct a deliberate
departure from the book.** Today's Haram is about **1/14.6** of the area of the 3,000-amah
square at the book's own 48 cm amah. That is not a small adjustment; it is a different claim
about what the prophecy describes.

**The sourcing is not deleted, and must never be.** Specifically:

1. `sources.md` §1.1 stands unchanged — Yechezkel 42:15-20, the book's own quotation and its
   own metric conversion, all still recorded as the sourced position.
2. **`EMikdashPrecinctReading::Yechezkel3000` remains implemented and drawable**, as does
   `Middot500`. The 3,000-amah ring can still be shown, and OVERLAY can still draw it, so a
   viewer can see the sourced precinct against the built one.
3. `FPrecinctRing` is added **alongside** `FSquare`, never in place of it. The square keeps
   working.
4. This page is the record that the departure was a decision of 15 September 2026 and whose it
   was.

**What is gained in exchange** is honest and worth naming: the gates stop being authored. The
Haram's real gates are mapped — the Gate of the Tribes, the Golden Gate, the Gate of Darkness,
the Gate of Remission, the Iron Gate, the Gate of the Chain, the Cotton Merchant's Gate, the
Ablution Gate, the Mughrabi Gate, the Council Gate and the Gate of Bani Ghanem are all OSM
features inside this ring. Moving the precinct gates onto them **upgrades them from authored to
sourced**, which is the opposite of what the boundary change does and partly offsets it.

---

## 6. The vertical question — **measured, and it does not resolve the way either option assumed**

The horizontal answer (§1) raised a sharper question: if the Aron is on the rock horizontally,
**is it on it vertically?** It is not, and the reason is structural.

Measured chain (Main50; Z 0 = 748.0 m a.s.l.):

| | Z | m a.s.l. |
|---|---:|---:|
| Kodesh HaKodashim clear floor, top (`SM_0147`) | +925 cm | 757.25 |
| court supporting platform, top (`SM_0127`) | +299 cm | 750.99 |
| **deck / plateau datum** | **0 cm** | **748.00** |
| published rock summit (±1 m, secondary) | −430 cm | **743.70** |
| real Haram esplanade | ≈ −800 cm | ≈ 740 |

**A flat deck at Z 0 stands 4.3 m above the rock — it buries it.** That is a real defect and the
question was right to raise it.

**But dropping the deck does not fix it.** For the Kodesh floor to sit *on* the rock (three
etzbaot under the stone, Yoma 5:2) the whole Temple must drop **13.61 m** (Main50) / **13.24 m**
(Candidate48), putting the deck at **734.39 m** — which is **5.6 m BELOW the real esplanade**.

The constraint is **over-determined**, and by a fixed amount:

* the measured architecture fixes **Kodesh floor − deck = 9.25 m**, and that is imported
  geometry which must not be edited;
* reality fixes **rock − esplanade ≈ 3.7 m** (the Sakhra outcrops ~1.5 m above the Dome's floor,
  itself on the upper platform ~4 m above the main esplanade);
* the gap between them, **5.55 m, cannot be removed by moving the deck.** Any deck height
  satisfies at most two of {deck = esplanade, floor = rock, architecture unedited}.

**Recommendation: keep Z 0 for this pass, and record the conflict as open and named.** Reasons:

1. **The rock elevation is the weakest number in the chain** — 743.7 m is an 1865 Ordnance
   Survey figure reached through a secondary website, ±1 m. Moving an entire Temple 13.6 m on
   that is not justified.
2. **Z 0 is very nearly the level's own Haram esplanade already** (the level grid reads 747.98 m
   flat across the middle of the Haram — 2.5 cm from Z 0), which is why the earthwork in §4
   collapses. Moving the datum throws that away.
3. Dropping 13.6 m would invalidate the Kotel plaza decks (−984 / −1234 cm), the terrain cut,
   the Mount access and **every receipt that records a world Z**.
   `ARON-ON-EVEN-HASHETIYAH-20260908.md` reached the same conclusion independently and rejected
   it for the same reasons.

**The honest long-term answer**, recorded and not acted on: lower the whole Temple **and** deck
to the real esplanade (~740 m) and model the rock as an **outcrop rising through the court
platform into the Kodesh HaKodashim**, which is what Ritmeyer's reconstruction actually shows.
That requires piercing measured architecture and is a separate decision.

### OPEN DECISION — the Even HaShetiya is under the floor, not in it

**Decided 16 September 2026: keep Z 0.** Stated as plainly as it deserves:

> At the deck datum this project builds on, **the published summit of the Even HaShetiya sits
> 4.3 m below the floor of the Kodesh HaKodashim.** The Temple is centred on the rock
> horizontally to 1.00 m — but vertically the rock is *under* the Holy of Holies floor rather
> than *in* it. The stone the Kohen Gadol set the fire-pan on (Yoma 5:2) is, in this model,
> buried beneath the paving.

That is a real and knowingly accepted defect, not an oversight. It is accepted because the
alternative is worse on the evidence available: the rock summit is a ±1 m secondary figure,
Z 0 is within 2.5 cm of the level's own esplanade (which is why the earthwork collapses 118×),
and a 13.6 m drop would invalidate the Kotel decks, the terrain cut and every receipt carrying
a world Z — for a gain no viewer can see.

**The alternative, stated so it can be chosen later:** lower both Temple and deck to about
740 m and let the rock rise as an outcrop through the court platform into the Holy of Holies.
That **pierces measured architecture** and is therefore its own decision, not a side effect of
the boundary change. **It is being put to the owner as a separate question. Nothing in this
pass acts on it either way.**

---

## 7. What changes, per system

| system | change | count |
|---|---|---|
| precinct boundary | `FPrecinctRing` alongside `FSquare`; 66-point ring | 1 new type, 4 consumers |
| wall ring | 467 wall + 4 corner + 5 gate instances re-planned on the trapezoid | ~1,432 → re-planned |
| gates | move onto the real mapped Haram gates | 5 authored → sourced |
| plaza paving | 14,641 cells over 2.07 km² → clipped to 14.24 ha | ~34,653 → far fewer |
| retaining / batter | max 136.9 m → **≈38 m** | 8,600 bands → far fewer |
| terrain cut | 12.45 Mm³ → **0.004 Mm³** | 17 twins → few or none |
| approach stairs | 60 m gate drops largely gone | 696 step instances → far fewer |
| **YECHEZKEL hide set** | **270 → 49 actors** | **221 buildings restored** |
| Kotel plaza, stair, closure | **unchanged** — they are real today and outside the ring | 0 |
| Old City foundations, streets, trees | **unchanged** — all survive | 0 |

### The hide set, exactly

Recomputed from the same frozen partition the shipped receipt uses, and **it reproduces the
shipped 270 exactly** (200 buildings + 41 facades + 29 infill) before being re-run on the ring:

| actor family | 3,000-amah square | Haram ring |
|---|---:|---:|
| `SM_JerusalemBuildings_Grid_*` | 200 | **21** |
| `RELEASE_OldCityFacades_*` | 41 | **18** |
| `RELEASE_OldCityInfill_*` | 29 | **10** |
| **total** | **270** | **49** |

**221 actors are restored to view.** The 49 that remain are the ones genuinely standing inside
today's walls — the Dome of the Rock, the Dome of the Chain, Al-Aqsa, the arcades, the sabils
and the Haram gates. In the Third Temple view they are not there; that is the premise of the
walkthrough, and MODERN restores every one of them exactly as it does today.

### The 100 m cell-batching problem is in scope, not deferred

The context is batched one actor per 100 m cell, so a cell the boundary cuts cannot be half
hidden. On the 1,440 m square that cost 573 collateral components — tolerable, because they sat
in a bare strip outside a 1.44 km wall. **On a 14 ha ring it is not tolerable:**

> **21 cells would hide 59 wanted components and take 150 unwanted ones with them.**

At this scale that reads as **holes punched in the Old City** right where the viewer is looking.
Two cells alone account for 91 of the 150: `Grid_N003_N002` would destroy 45 buildings to hide
2, and `Grid_N003_N003` would destroy 46 to hide 1.

**Done, 16 September 2026, offline** — `Scripts/create_precinct_cell_split.py`, manifest
`CellSplitV1/cell-split-manifest.json`. Of the 21 cells, **10 are wholly inside and need no
split; 11 are cut**, and those 11 are re-batched into 22 meshes — an `_PrecinctIn` half
(40 components, 952 triangles) and a `_PrecinctOut` half (150 components, 3,112 triangles).
YECHEZKEL hides the original and the IN half and shows the OUT half; MODERN shows the original
and hides both. **Nothing is deleted.** Worst readback bounds error **1.8 × 10⁻⁵ cm**.

> **A trap worth recording, because it would have shipped silently.** The obvious way to split
> a cell is to slice its triangle list by the components' triangle counts in
> `sourceComponentIds` order. The counts sum exactly, so it looks right. **It is wrong** — the
> list is not grouped by component. A bounds check written to guard the assumption refused on
> the first cell, where component 7218's slice missed its own recorded bounds by **160.4 amot
> (80 m)**. Without that check the pass would have emitted buildings assembled from other
> buildings' walls, with correct triangle counts, correct vertex counts and correct cell
> bounds — nothing downstream would have caught it. The components are therefore recovered by
> **connected-component analysis over vertex positions** (the source is unwelded, so triangles
> of one building share no vertex *index*), then matched one-to-one to the manifest by bounds.

---

## 7b. Receipt hygiene — the sha drift was already there

**Stated so nobody later reads it as damage this pass caused.** `EnclosureMath.h` had *already*
drifted from the receipts that record it, before any work on the Haram outline began:

| receipt | `enclosureMathSha256` recorded | state |
|---|---|---|
| `plaza-*.json` | `a0518f8d…` | stale before this pass |
| `native-approach-apply-*.json` | `8aff1378…` | stale before this pass, and different again |
| header as found, 15 Sep | `54ae7790…` | matched neither |

Three different values across the audit trail, none of them current, none of them this pass's
doing. That is precisely why the receipts are regenerated in the same pass as a header change
rather than later.

**Now:** `precinct-Main50.json` and `precinct-Candidate48.json` are regenerated and both record
the current header `7b7714fd…`. **Still stale and still to be regenerated by their own
generators:** the plaza receipts (`create_precinct_plaza.py`) and the approach receipts
(`release_precinct_approaches.py`). Both of those describe geometry planned on the *square* and
will need re-planning on the ring regardless, so they are named here as outstanding rather than
quietly refreshed.

---

## 7c. THE FRAMES — what a real-RHI capture shows, 16 September 2026

Five frames from the packaged `Checkpoint-plateau-S4c` build, receipt
`HideSetV1/frame-haram-restore-S4c.json`, captured because **counts cannot answer this**.
Caption on all five: *city restored, boundary not yet rebuilt.*

| # | question | answer |
|---|---|---|
| A1 | Is the Old City standing around the Temple? | **YES** — dense, continuous, right up to the platform |
| C1 | Holes where the 11 cut cells were? | **NO** — rooflines unbroken across the worst two cells |
| C1 | Does a split seam read as a seam? | **NO** — no visible discontinuity at the cut line |
| Q1 | Is Al-Aqsa standing inside the precinct? | **NO** — it is absent entirely; no actor renders it |
| K1 | Is the Kotel view right? | **NO — a real defect, see below** |

**The 221 restored buildings are really there, and the cell split really worked.** C1 is the
frame that mattered: it looks straight at `Grid_N003_N002` and `Grid_N003_N003`, which between
them hold 91 of the 150 preserved components, and the city is continuous. Had the split failed,
that frame is where a hole would have been.

**Al-Aqsa: answered, and the answer is better than feared.** Its label
`SM_JerusalemBuildings_Large_07279` has no actor, so the hide set cannot reach it — but Q1
shows nothing renders it either. There is no mosque standing inside the Third Temple precinct.
The unresolvable label is inert, not a hole in the premise.

### DEFECT FOUND BY THE FRAME — the Kotel plaza is buried in YECHEZKEL

K1 looks east from the Western Wall prayer plaza. The Kotel itself renders correctly, with
worshippers at it. **The plaza they stand on does not exist: it is a bare dirt slope.**

Cause, and it is a consequence of this very change:
`AMikdashEnclosure::HideWhileWallStandsTags` contains **`KotelPlazaCutTwin`**
(`MikdashEnclosure.cpp:247`), with the reasoning written when the square still stood:

> "The Western Wall Plaza cut is a MODERN feature whose decks sit 11 m BELOW the precinct
> deck: buried and pointless in Yechezkel, so it is the opposite sense."

That was right for the 3,000-amah square, whose 2.07 km² deck covered the area. It is **wrong
now**: the Kotel plaza lies OUTSIDE the Haram ring, it is real today, and with `bBuildPlaza`
false there is no deck above it. So in YECHEZKEL the terrain cut twin hides, the uncut terrain
returns, and it buries a plaza that was correctly placed
(`native-kotel-plaza-apply-Candidate48-20260911T123932176280Z.json`, 1,051 instances).

**Fix (S5, not done here):** take `KotelPlazaCutTwin` out of `HideWhileWallStandsTags` — or
move it to the ring-aware rule — so the Kotel plaza stands in every state, as
§7 of this document already says it must ("the Kotel plaza, stair and closure wall, which
stay — they are real today"). One line, but it is a runtime C++ default, so it needs both
Editor and Game targets rebuilt, which is why it is S5 and not a quiet edit tonight.

### Also observed, not yet chased
* **S1 (street level)** — the Temple reads correctly above the Old City roofline, but the
  foreground is heavily shadowed; exposure favours the sky. A better-lit street camera is
  worth authoring for the tour.
* **C1** — a pale blue-grey slab on the north-east horizon does not read as masonry. Not
  identified; possibly a Kotel photo panel or an untextured surface seen edge-on. **Recorded
  as unexplained rather than dismissed.**

---

## 8. What is deliberately not claimed

* That today's Haram outline is the precinct Yechezkel describes. **It is not**, and §5 says so.
  This is the owner's decision about what to build, recorded as such.
* That the Haram walls are surveyed. They are the **OSM trace** of the retaining walls, of
  unstated thickness — treat as ±2 m.
* That the rock is placed better than ±4.24 m, or its summit better than ±1 m.
* That anything here has been seen in a frame. **Nothing in this pass has been rendered,
  walked, cooked or placed.** No map and no asset has been mutated by it.
