# Gate security — sources

What the checkpoint at each gate approach is built from, claim by claim, marked
**certain** / **disputed** / **modern-staging**.

The request was: *"I want security by the gates of the temple with metal detectors and signs
saying take off shoes and no cellphones allowed etc."* Two very different kinds of thing answer
that request, and this file exists so they never get confused with each other.

- The **shoes** rule is halacha. It is on the signs as a **rule of the place**, not a request,
  and it carries its citation on the sign face itself.
- The **metal detectors, bag scanner, stanchions, guard booth, guards and the telephone rule**
  are **modern staging**. They are modelled on the entrance procedure at the Har HaBayit and
  Kotel plaza approaches *today*. No classical source describes anything of the kind, none is
  cited for them, and nothing in this set is a claim about the Temple or its courts.

---

## The source table

| # | Claim as depicted | Status | Source | Where it appears |
|---|---|---|---|---|
| 1 | A person may not enter Har HaBayit wearing shoes. | **certain** | Mishnah **Berachos 9:5**; Rambam, **Hilchos Beis HaBechira 7:2** | `Sign_Shoes` panel, headline band; `Sign_Reverence` third rule |
| 2 | Stockinged feet are the permitted state, so there is somewhere to leave shoes. | **certain** (rule) / **modern-staging** (the rack) | Rule as #1. The *shoe rack* is staging: no source describes furniture for this. | `Sign_Shoes` second rule; `SM_GateSecurityV1_ShoeRack` |
| 3 | The Mount may not be used as a shortcut (*kappandaria*). | **certain** | Same mishnah (**Berachos 9:5**) and same halacha in **Rambam 7:2** | `Sign_Reverence` first rule |
| 4 | One may not spit on the Mount. | **certain** | Same mishnah (**Berachos 9:5**) and **Rambam 7:2** | `Sign_Reverence` second rule |
| 5 | One may not enter with a money belt (*punda*) or with dust on the feet. | **certain** (in the source) | Same mishnah (**Berachos 9:5**); **Rambam 7:2** | **NOT SIGNED.** Two of the four reverences were chosen for signage (#3, #4) because four rules on one panel is unreadable at walking distance. Recorded here so the omission is deliberate and visible. |
| 6 | The approach is a *holy area* and the rules are conditions of entry. | **certain** | The framing of Berachos 9:5 / Rambam 7:2, which state these as prohibitions on the place | `Sign_Shoes` footer band, `Sign_Reverence` headline band |
| 7 | Telephones may not be used. | **modern-staging** | **None.** Modelled on posted conduct rules at the Kotel plaza and Har HaBayit entrances today. | `Sign_Security` first rule; `Sign_Entrance` pictogram row |
| 8 | All bags are searched. | **modern-staging** | **None.** Modelled on the Kotel plaza bag check today. | `Sign_Security` second rule; `SM_GateSecurityV1_BagScanner` |
| 9 | Visitors pass through a walk-through metal detector. | **modern-staging** | **None.** Modelled on the Har HaBayit / Kotel entrance procedure today. | `Sign_Security` third rule; `SM_GateSecurityV1_DetectorArch` |
| 10 | A queue is managed with belt stanchions, and a guard sits in a booth. | **modern-staging** | **None.** Ordinary present-day crowd control. | `SM_GateSecurityV1_Stanchion`, `SM_GateSecurityV1_Booth` |
| 11 | Cameras are permitted. | **modern-staging** | **None.** A wayfinding convenience, shown as a permitted pictogram to balance the prohibitions. | `Sign_Entrance` pictogram row |
| 12 | Signage is trilingual Hebrew / English / Arabic. | **modern-staging** | **None** as a Temple claim. It is how public signage in Jerusalem is actually written today, and that is the only thing it asserts. | Every sign |
| 13 | Every dimension of every object. | **depicted, not asserted** | **None.** There is no measured drawing of a Jerusalem checkpoint in this project and none is claimed. Sizes are ordinary security-equipment sizes chosen so a 175 cm figure walks through an arch without stooping, reaches a table at waist height and reads a sign at eye level. | All nine meshes |
| 14 | The checkpoint stands on the deck outside the first riser of the E / N / S gate stairs. | **depicted** — position derived, not sourced | Gate geometry from this project's own receipts (see below). The *presence of a checkpoint there* is modern staging; only the **gate position** is derived from project data. | `Scripts/release_gate_security.py` |

### Disputed

Nothing in this set is marked **disputed**. The halachic items (#1, #3, #4, #5, #6) are the
plain content of a single mishnah and a single halacha in Rambam that restates it, and this
build takes no position on any of the questions that *are* disputed — who may ascend, where the
permitted areas lie, or whether ascending is permitted at all. Those questions are not depicted
here and no signage in this set touches them. A checkpoint is not a ruling.

---

## Where the gate positions came from

The placement is **not invented**. It is derived from receipts already in this project:

| Fact | Value | File |
|---|---|---|
| Units and axes | cm; X east, +Y south, Z up; measured court centre at the origin; 1 amah = 50 cm | `SourceAssets/FutureMountV1/EnclosureV1/enclosure-design.json` (`coordinateConvention`, `cmPerAhmah`/`cmPerAmah`) |
| East gate stairs, threshold, vestibule | first riser `Outer E stair 1` min `[9150,-250,0]`; threshold centre `[7950,0,300]`; vestibule walls X `7400..7800`, Y `±325..625`, Z `300..2800` | `SourceAssets/architecture-manifest.json` (`expectedBoundsUnrealCm`), `SourceAssets/mount-access/GatewayV3/gateway-approach-audit.json` |
| North gate | first riser `[-400,-9450,0]`; threshold centre `[0,-7950,425]`; vestibule walls Y `-7800..-7400`, Z `425..2925` | same |
| South gate | mirror of North in Y; threshold centre `[0,7950,425]` | same |
| Deck Z at all three approaches | `0` (`bottomPlatformUncoveredAreaCm2: 0.0` for E, N and S) | `SourceAssets/mount-access/GatewayV3/gateway-approach-audit.json` |
| **West: there is no gate** | `"decision": "NO_SOURCE_GATE_DO_NOT_INVENT_OPENING_OR_STAIRS"` | same |

Two consequences recorded so they are not rediscovered the hard way:

1. **No yaw is recorded for any gate anywhere.** Every gate-related record is axis-aligned with
   rotation `[0,0,0]`. The assembly yaw (E `180`, N `90`, S `-90`) is *derived* from the outward
   axis of each gate, not read from a receipt.
2. **`get_actor_location()` on a measured-architecture actor returns `(0,0,0)`.** World position
   is baked into the vertices and every such actor is spawned at the origin with an identity
   transform (`architecture-manifest.json`: `spawnLocationUnrealCm [0,0,0]`,
   `objectTransformIdentity true`). The placement script therefore confirms each gate at run
   time by reading the **static-mesh component world bounds** of the first riser and the
   threshold, matched by **static-mesh asset path** — labels are not unique (ten actors share
   the label `Outer N mount approach terrace`), asset paths are 1:1. A gate whose bounds do not
   match the offline numbers is omitted with evidence rather than placed on a guess.

There is no `Gate_`, `Approach_` or `MountGate` actor in the map, and no spline, queue path or
nav corridor exists anywhere in the project.

---

## The text on the signs

Trilingual, as real Jerusalem signage is. Hebrew strings, as requested:

| Hebrew | Transliteration | English | Sign |
|---|---|---|---|
| הסר נעליך | *hasér na'alékha* | Remove your shoes | Shoes |
| אסור להיכנס בנעליים | *asúr lehikanés bena'aláyim* | Entering in shoes is prohibited | Shoes (band) |
| אין להשתמש בטלפון | *ein lehishtamésh betélefon* | No telephone use | Security |
| אזור קדוש | *azór kadósh* | Holy area | Shoes, Reverence (band) |

Plus: בגרביים בלבד (stockinged feet only), אין לעשותו קפנדריא (no shortcut), ולא ירוק בו (no
spitting), התיקים נבדקים (all bags are searched), כניסה (entrance), ביקורת ביטחון (security
check), עבור דרך המגלה (pass through the detector).

**Pictograms carry the message; text confirms it.** At the distance a sign is actually read from,
the crossed-out shoe, the crossed-out phone, the permitted camera and the direction arrow do the
work. Every prohibition is drawn as a pictogram inside a red prohibition ring, every permission
inside a green ring, in all three of the panel signs and the wayfinding plate.

### The glyph check — what was actually verified

Hebrew and Arabic **do** render correctly. This is not a claim, it is a receipt:
`SourceAssets/security-review/signs/glyph-check.json`, regenerated on every export by
`verify_glyphs()` in `Scripts/create_gate_security.py`, which **raises** rather than shipping
mojibake.

- **Font.** `C:\Windows\Fonts\arialbd.ttf` (bold) and `arial.ttf` (regular). Segoe UI, David,
  Frank Ruehl, Times New Roman and Tahoma were all checked as alternatives. **David and Frank
  Ruehl carry Hebrew but are each missing 29 of the Arabic presentation forms these signs need,
  so they were rejected.** Arial, Segoe UI, Times and Tahoma all pass; Arial Bold was taken for
  weight at distance. A separate agent's Hebrew font research in
  `SourceAssets/localization-review/fonts/` (Noto Sans/Serif Hebrew, David Libre, Frank Ruhl
  Libre, all OFL) was read; those faces are for UI text and none of them carries Arabic, so the
  signs use the system Arial rather than writing into that folder.
- **Coverage.** Every codepoint used by every sign is looked up in the font `cmap`; the glyph id
  and the *contour count read out of the `glyf` table* are recorded. Glyph id `0` is `.notdef`
  (the empty box) and a glyph with zero contours would print blank. Both are refusals, not
  warnings. Result: **150 codepoints checked, 0 missing, 0 empty.**
- **Right-to-left.** A direction probe lays out הסר נעליך and asserts that the **first** logical
  letter (ה) is drawn **furthest right** on the page and the last (ך) furthest left. Recorded
  with the measured pixel centres of both. Result: **PASS.**
- **Arabic contextual shaping.** Arabic is shaped into the Unicode presentation forms of block
  `FE70..FEFF` by a joining table in the script, including the lam-alef ligatures, then reversed.
  **Five** words are checked form by form against hand-verified expected output, covering
  isolated / initial / medial / final, a fully connected four-letter run, and *both* lam-alef
  branches (isolated `FEF7`/`FEFB` and final `FEFC`). Result: **PASS.**

  One correction is worth recording: an earlier expectation for الأحذية listed **seven** forms,
  including both a standalone lam `FEDF` *and* the lam-alef ligature `FEF7`. That was wrong —
  the lam and the following alef-with-hamza fuse into the single ligature, so the correct output
  is **six** forms. The shaper was right and the test was wrong; the test was fixed, not the
  shaper, and two further cases were added to cover the branches the original three missed.

Rendered proof, not just numbers: `signs/preview-on-mesh-<Name>.png` renders each sign face
*through the mesh UVs from the visitor's eye*, which is also what catches a mirrored texture.

---

## The geometry check — what was actually verified

`SourceAssets/security-review/GateSecurityV1/geometry-manifest.json`, regenerated on every
export. 9 meshes, 22,480 triangles. Every part of every mesh is asserted, and the export **raises**
rather than writing a bad mesh:

- **Closed.** Every undirected edge is used by exactly two triangles.
- **Consistently oriented.** Every *directed* edge is used exactly once, so the two faces sharing
  an edge traverse it in opposite directions. This is stronger than "closed" and it is the check
  that matters.
- **Positive volume**, part by part, and the signed volume of the written OBJ equals the sum of
  the authored part volumes exactly.
- **Stored normals** agree with the geometry to within 2.1e-06.

Two real bugs were caught by adding the orientation check, both of which had been passing every
earlier test:

1. **`loft()` wound both end caps inward.** Every rounded box in the file is built on `loft`, so
   every one of them had inside-out caps. It went unnoticed because `closed()` counts *undirected*
   edges and therefore cannot see a reversed face group, and `orient()` only inspects the sign of
   the total volume, which stayed positive. The measurable symptom: a 10 x 20 x 30 box came out at
   **2000 cm3 instead of 6000** — exactly a third, which is what you get when the far cap's
   contribution is subtracted instead of added.
2. **`tube_along_y()` shared a directed edge between the outer skin and the near end cap**, so
   those two surfaces were wound the same way round rather than opposite. This is the conveyor
   roller and the stanchion collar.

Both are fixed and both are now validated against closed-form expectations (a filleted box against
its analytic volume, a tube against the exact polygonal annulus area). `revolve`, `prism`,
`frame_prism` and `box` were checked by the same test and were already correct.

The lesson worth carrying: *a closed-surface test is not an orientation test.* A signed-volume
sign check is not one either. Only the directed-edge test finds a reversed face group.

---

## What is depicted versus asserted, in one line each

- **Asserted:** that entering Har HaBayit in shoes is prohibited, that the Mount may not be used
  as a shortcut, and that one may not spit there. Three statements, one mishnah, one Rambam,
  both cited on the sign face.
- **Depicted, not asserted:** a metal detector, a bag scanner, a guard booth, stanchions, a shoe
  rack, and a rule about telephones — present-day Jerusalem entrance procedure, labelled as such
  *on the sign itself* ("Modern staging… No classical source. Nothing on this notice is a claim
  about the Temple."), not only in this file.
- **Depicted, not asserted:** every dimension, material, colour and position of every object.
