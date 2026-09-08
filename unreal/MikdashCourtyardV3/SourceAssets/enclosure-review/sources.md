# The sacred precinct: what is measured, what is disputed, what is authored

Review document for `EnclosureV2` — the Yechezkel 42:15-20 precinct and the three-state
MODERN / YECHEZKEL / OVERLAY toggle over modern Jerusalem.

Every claim below is marked **certain**, **disputed**, or **authored**.

* **certain** — stated in the verse, in the Mishnah, or in the book, and quoted here.
* **disputed** — the sources genuinely disagree. Both or all positions are named; this
  project does not adjudicate, and where it can it builds both.
* **authored** — this project invented it because nothing said. Every such choice is a
  study aid, not a claim about the Temple.

Files: geometry `geometry-manifest.json`; test snapshot `tests.json`; plan
`enclosure-plan.png`; generator `Scripts/create_enclosure.py`; placer
`Scripts/release_enclosure.py`; arithmetic
`Plugins/MikdashRuntime/Source/MikdashRuntime/Public/EnclosureMath.h`.

---

## 1. The size of the precinct

### 1.1 Yechezkel 42:15-20 — five hundred, and 40:5 — a reed of six amot — **certain**

Yechezkel measures the precinct from outside, in reeds, and 40:5 defines the reed:
*"a measuring reed of six amot, an amah and a tefach"*. Five hundred reeds is therefore
three thousand amot on a side.

The book — *Lishchno Tidreshu*, whose Third Temple sections are **קץ הימין** — states it
directly, on 40:5 (`mikdash book/Book-Source-Data.json`):

> ואורך החומה **שלושת אלפים אמה על רוחב שלושת אלפים אמה [חמש מאות על חמש מאות קנים]**, ולה חמשה שערים

and again on 42:16, with its own metric conversion:

> החומה המזרחית מבחוץ ארכה חמש מאות קנים, שהם שלושת אלפים אמה, **שהם קילומטר וארבע מאות וארבעים מטר בערך**

So the book holds the 3000-amah reading, and this project follows it. **This is the position
the model is built on.**

### 1.2 Middot 2:1 — five hundred **amot** — **certain as a text, disputed as a reconciliation**

Mishnah Middot 2:1 gives Har HaBayit of the Second Temple as five hundred amot square —
one thirty-sixth of the area of the 3000. The two are not the same measurement, and how they
relate is not settled. At least two positions, presented as equals:

**Position A — two different Temples, related by a factor of thirty-six.**
Rashi on Yechezkel 42:20, reprinted in the book:

> שלשת אלפים על שלשת אלפים אמה שהקנה שש אמה… **כמדה הראשונה שהיה הר הבית ה׳ מאות אמה על ה׳ מאות אמה** — חלוק שלשת אלפים על שלשת אלפים לרצועות של ה׳ מאות אמות שתי וערב ותמצא שם שלשים וששה רבעים של חמש מאות על חמש מאות

The Third Temple's Mount is thirty-six times the Second's in area. The book adopts this, and
says so in a bracketed gloss of its own:

> **[הר הבית בבית שני היה בגודל חמש מאות אמה על חמש מאות אמה]**

**Position B — the five hundred of Yechezkel are themselves amot, not reeds.** A reading
found among commentators who take 42:20's five hundred as continuous with Middot's five
hundred, so that the two prophecies describe one Mount at one size and 40:5's reed governs
only the wall's own section. On this reading there is no thirty-six-fold expansion at all.

This project does not choose. **Both are built.** `EMikdashPrecinctReading` offers
`Yechezkel3000` and `Middot500`, and the OVERLAY state can draw the 500-amah ring inside the
3000 so a viewer sees the 6:1 ratio on the ground rather than being told it.

### 1.3 Yechezkel 45:1-6 and 48 — the terumah — **certain in the verse, absent from the book**

Yechezkel 45:1 and chapter 48 describe a *terumah* of twenty-five thousand on a side, a scale
larger again — the precinct would be one hundred and forty-fourth of its area if the
twenty-five thousand are amot, and one five-thousand-one-hundred-and-eighty-fourth if they are
reeds. **Whether they are amot or reeds is itself disputed**, and the difference is a factor
of six on a side.

**The book does not treat it.** A search of `Book-Source-Data.json` for עשרים וחמשה אלף
and כ״ה אלף returns nothing, and the project's own research index records chapters 45 and 48
as cross-references only. `TerumahSideAmot` exists in `EnclosureMath.h` and is **not drawn**:
at 25,000 amot the ring is 12.5 km a side at the project's scale, four to five times the width
of the whole imported terrain, so there is nothing for it to be drawn over. It is recorded so
the relationship can be quoted, and that is all. Adding it later is a one-line change; adding
it now would be a ring floating past the edge of the world.

---

## 2. How long is an amah? — **disputed, and the dispute is worth 300 m a side**

There is no settled shiur. The table in `EnclosureMath.h` carries the common range and this
project reports the precinct under every entry rather than picking one:

| key | position | amah | precinct side | area |
|---|---|---|---|---|
| `naeh` | R' Avraham Chaim Naeh, *Shiurei Torah* — 6 tefachim × 8 cm | 48.0 cm | **1440 m** | 2.07 km² |
| `project` | the level's baked world scale, a round half-metre | 50.0 cm | **1500 m** | 2.25 km² |
| `feinstein` | R' Moshe Feinstein, *Igros Moshe* OC I:136 — about 21¼ inches | 54.0 cm | **1620 m** | 2.62 km² |
| `chazon-ish` | Chazon Ish, *Kuntres HaShiurim* — 6 tefachim × 9.6 cm | 57.6 cm | **1728 m** | 2.99 km² |
| `chazon-ish-stringent` | Chazon Ish, stringent rounding for de'oraisa shiurim | 58.0 cm | **1740 m** | 3.03 km² |

**Three hundred metres separate the smallest opinion from the largest** on a single side —
more than the width of the Old City's southern quarter. That spread is the point of the table.

### Which one does the book use? — **48 cm, recovered rather than stated**

The book never writes "an amah is N centimetres". It gives two metric conversions, and both
come out at 48:

1. On 42:16, three thousand amot are *"a kilometre and four hundred and forty metres
   approximately"* → 1440 ÷ 3000 = **48.0 cm**.
2. On Middot 2:3, a half-amah step is glossed **[כעשרים וארבע ס״מ]**, "about 24 cm"
   → 2 × 24 = **48.0 cm**.

That coincides with R' Chaim Naeh. `BookImpliedAmahRealCm = 48.0` and
`BookStatedPrecinctSideMetres = 1440.0` are both in the header, and `EnclosureMathTest.cpp`
asserts that the one reproduces the other, so neither can be edited alone.

### Which one is the model built at? — **50 cm, and that is a level fact, not a ruling**

The Jerusalem OSM context, the measured architecture and the FutureMountV1 platform were all
baked at **50 Unreal cm per amah**. Changing it would invalidate every actor transform in the
Walkthrough map. So the geometry is built once at 50, and the metre figure quoted to a viewer
is computed per opinion at run time by `GetPrecinctSideMetresUnderAmah`. The model is not a
claim that an amah is half a metre.

**Reported size, in the three the report asks for and two more:**
at the book's own amah **1440 m** a side; at the project scale **1500 m**; at the Chazon Ish
**1728 m**. Roughly 1.4–1.5 km either way, which is what puts most of the Old City inside it.

---

## 3. Where the square sits

### 3.1 The centre — **certain, and proved rather than assumed**

`architecture-manifest.json` records `"World positions baked in vertices; all object transforms
identity; spawn every imported asset at origin"`, and all 2,633 measured meshes carry
`spawnLocationUnrealCm` `[0, 0, 0]`. The measured court centre is therefore the world origin
by construction. `release_enclosure.py` does not take that on trust: it re-reads
`SM_0127_architecture_Outer_court_supporting_platform` (bounds ±8100 cm on both axes,
error 0.0), requires the four Altar yesod meshes to remain centred on (0, 0), and refuses to
run if either witness has moved.

### 3.2 The anchoring — **certain in the book, and it does not close here**

The book does not place the 3000 by giving a centre. Fig. **ב'2** (p. 113) labels the open
ground on each side, after **Mishkenei Elyon 196 ch. 1 mishnah 1**, which the book quotes in
full and which applies the Middot 2:1 wording to a Mount of *three thousand* amot:

> הר הבית שלושת אלפים אמה על שלושת אלפים אמה, **רובו מן הדרום, שני לו מן המזרח, שלישי לו מן הצפון, מיעוטו מן המערב**

with the book's own gloss: *the Temple stands near the north-west of the Mount, so the largest
open ground is south, then east, less north, and least west.* The diagram's labels are
**500 west, 501 north, 2149 east, 2153 south**.

**Here is the one place the sources and this project's measured geometry do not close, and it
is reported rather than hidden.**

The two stated clearances are west and north; east and south are remainders:

```
West  + EnvelopeEastWest   + East  = 3000
North + EnvelopeNorthSouth + South = 3000
⇒ South − East = (West + EnvelopeEastWest) − (North + EnvelopeNorthSouth)
```

With west 500 strictly less than north 501 — which the stated order itself demands — **south
can exceed east only if the court envelope is wider east-west than it is deep north-south.**
Middot's own Azarah is that shape (187 × 135, Middot 5:1). The book's diagram envelope is that
shape, about 351 × 346, which is exactly why its labels satisfy the order.

This project's measured court supporting platform is **324 × 324 amot — square**. On a square
envelope the identity collapses to `South − East = West − North`, so west 500 with north 501
forces **east 2176, south 2175**: the order inverts, by exactly one amah, 50 cm on a
150,000 cm side. No tolerance, no re-anchoring and no tuning can avoid it; only a
wider-than-deep envelope can. Taking the *full* measured architecture envelope instead
(346 east-west by 378 north-south, from `expectedBoundsUnrealCm`) makes it worse, not better:
west 500, north 474, east 2154, south 2148 — north now falls below west and the order breaks
in two places.

| anchoring | west | north | east | south | Middot order? |
|---|---|---|---|---|---|
| book fig. ב'2, envelope 351 × 346 | 500 | 501 | 2149 | 2153 | **yes** |
| this project, court platform 324 × 324 | 500 | 501 | **2176** | **2175** | no — east and south swap by 1 amah |
| this project, full architecture 346 × 378 | 500 | **474** | 2154 | 2148 | no — north also falls below west |

**Correction to existing project data.**
`SourceAssets/FutureMountV1/EnclosureV1/enclosure-design.json` `offsetRule` currently ends
*"Order south > east > north > west preserved (Mishkenei Elyon 196 m.1)"* while carrying
east 2176 and south 2175 in the same object. That sentence is wrong by its own numbers.
`geometry-manifest.json` `clearanceOrder` is the correction, and
`EnclosureMathTest.cpp::ClearanceChecks` proves the impossibility over 756 swept cases rather
than asserting it. That design file is owned by `create_mount_enclosure.py` and has not been
edited here.

**What the project ships:** the platform anchoring, because it puts the wall at a measured
500 and 501 amot from geometry that actually exists in the level, and because the departure is
one amah. The alternative — reproducing all four of the diagram's numbers by anchoring on an
envelope the level does not contain — would put the wall in a place nothing measures.

### 3.3 Resulting square — **derived**

Outer faces west −33100, east 116900, north −33150, south 116850 Unreal cm; centre
(41900, 41850); side 150000 cm. Identical to the four faces already shipped in
`EnclosureV1/enclosure-design.json`, and `create_enclosure.py` raises if they ever differ.

---

## 4. The wall and the gates

| item | value | status |
|---|---|---|
| wall thickness | one reed, 6 amot (Yechezkel 40:5) | **certain** |
| wall height | 6 amot. Mishkenei Elyon 196 ch.1 m.2, quoted by the book: גובהו של כותל שש ועביו שש | **certain** |
| measured from outside | 42:15-20 measures מבחוץ, so the 3000 are the OUTER faces | **certain** |
| gate count | five: two south, one each east, north, west (Mishkenei Elyon 196 m.2) | **certain** |
| gate opening | 10 amot wide, 50 amot high; כעביו של כותל כך עביו של פתח — the gate is as thick as the wall | **certain** |
| gate positions along each wall | E/N/W on the Temple axes; the two south at a third and two thirds | **authored** — the book gives the count, not the position |
| gate piers 10 amot, overall height 60 amot | | **authored** — and the book marks it so itself: ורוחב החומה של פתח השער לא מוזכר, then two starred (*) conjectures giving 10 and 10, סה״כ גובה השער ששים אמה |
| doors | omitted; the gates stand open, as in the book's figures | **authored** |
| wall face articulation, corner blocks, marker pylons | | **authored** — the book gives a section, never an elevation |

---

## 5. The three states, and what happens to the modern city

| state | wall | overlay band | modern buildings inside |
|---|---|---|---|
| MODERN | — | — | **all visible** |
| YECHEZKEL | solid | — | **hidden by visibility, never deleted** |
| OVERLAY | — | translucent band + ground line of light + markers | **all visible** |

OVERLAY is the state that answers the question, so it is the one that gets the care: the band
is a two-sided slab (a single quad would vanish the moment the viewer crosses the line, which
is when it is most wanted), quads are scaled to bridge exactly to the next sample so no seam
doubles its own opacity, and corner and gate markers carry the ring at a distance where the
band itself is a hair on screen. Transitions are a smoothstep over 2.5 s of four weights, so
no state pair needs a special case.

**The visibility contract.** `AMikdashEnclosure` never calls `Destroy()`, never modifies a
package, never writes to disk, and touches nothing on a building but
`SetActorHiddenInGame`. It records each actor's prior visibility so a building someone else had
already hidden is not "restored" into view, and it restores everything on state change, on
`EndPlay`, and on `RestoreAllModernBuildings()`. A crash mid-transition loses nothing.

### How much of the city is covered — **measured**

Against the OSM source polygons every building is an explicit ring, so the count is exact
rather than binned. By the centroid rule the runtime actor uses:

* **1,911 of 11,437** modern buildings city-wide fall inside the precinct;
* **64 more** have footprints the wall line cuts while their centroid lies outside;
* of the 2,106 authored Old City facade buildings, **485** are inside.

The 100 m cell band computed from files inside this repository alone (599 certain, up to 1,359
counting cells the wall cuts) covers only the 3,620 buildings inside the Old City walls; the
precinct also reaches ground east and south of those walls. The two figures are different
populations, not a contradiction.

---

## 6. Cost — **measured, RTX 2070**

| | instances | triangles |
|---|---|---|
| wall segments | 467 (13 of 480 removed for gates) | 106,476 |
| gates | 5 | 420 |
| corners | 4 | 288 |
| overlay slabs | 480 | 5,760 |
| **total** | **956** | **112,944** |

Four `HierarchicalInstancedStaticMeshComponent`s, one draw call each before per-instance
culling. For scale, the Old City facade set that YECHEZKEL hides is **3,416,580** triangles
across 190 actors — the enclosure is **3.3%** of what it replaces.

A single-mesh 1.44 km wall would be one 1.44 km bounding box: never frustum-culled, never
occlusion-culled, one LOD for the whole ring, and a re-import for any change. The counts above
are asserted in `EnclosureMathTest.cpp` and cross-checked against the generated geometry by
`create_enclosure.py`, so a module that quietly grows fails the test rather than the frame rate.

**Known limitation:** the instanced wall sits on the level plane. It is not stepped to the
terrain the way `EnclosureV1` is, so over the Kidron and the Hinnom it will float or bury until
per-instance ground Z is added. `EnclosureV1` is unchanged and still available for that.

---

## 6b. One open question this work does not settle

The book places the FUTURE city south of and below the Mount — *לעתיד, הבית בצפון ההר
והעיר ירושלים בדרום ההר*, with fig. 160 captioned to match — and says nothing whatever about
today's Old City or about hiding it. The hide behaviour is entirely a project construct.

It is also in tension with this project's own written policy,
`GitHub/3rdbhmk/unreal/Research/people-and-city.md` §6:

> Existing OSM buildings and streets should remain identifiable as modern geographic context.
> They help a visitor orient themselves.

The YECHEZKEL state hides 1,911 of them. That is exactly why the toggle has three states and
why OVERLAY — which hides nothing — is the default answer to "what ground does this cover".
MODERN is the state the level opens in. `BUILDOUT-STATUS.md` still records the
modern-city / future-boundary question as open; **this work builds both sides of it and does
not close it.**

---

## 7. What is deliberately not claimed

* That the amah is 50 cm, or 48, or any other value.
* That the 3000-amah reading is correct and the 500-amah reading is refuted, or the reverse.
* That the terumah of chapter 45/48 is 25,000 amot rather than 25,000 reeds.
* That the wall's face, the gates' elevation, the corners or the gate spacing look like this.
* That today's street network is the future city. The modern buildings are modern geographic
  context; they are hidden, never replaced, and never relabelled.
