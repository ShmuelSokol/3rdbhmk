# "Lishchno Tidreshu" (Part I, Yechezkel 40-42) - what the walkthrough must get right

Date 2026-09-07. Read-only research. Companion data: `book-scene-requirements-20260907.json` (129 per-page rows, 15 ranked gaps).
Builds on `SourceAssets/vessels-review/book-keilim-review-20260907.md` (vessel positions; not repeated here).

## How the book was read

- Source: `mikdash book/Book-Source-Data.json`, all 367 page records iterated in order; English `englishOutput` (ALL DRAFT) skimmed page by page,
  clustered by the running header (`יחזקאל פרק מ"א פסוק כב'` etc.) and by the book's three layers: **קץ הימין** (Ketz HaYamin, the Third
  Temple summary per pasuk), **באור חי** (sources/reasoning), **השלמת שרת** (completions from Torah, Middos, Rambam - often Mishkan/First/Second Temple).
- PDF structure (matters for citations): pp. 2-19 front matter; pp. 20-67 a partial early run (Perek 40, 41:1-7); pp. 70-104 front matter again;
  pp. 105-364 the complete main run (Perek 40 = 105-179, Perek 41 = 180-270, Perek 42 = 271-364). Pages 68 and 85 are translation failures
  (front matter, irrelevant); 1 and 365-367 are blank. Rows cite the main run and list the duplicate early-run page in `dup_pages`.
- The Ketz HaYamin paragraph for a pasuk is reprinted on every page of that pasuk (e.g. 41:22 on pp. 241-257) - repetition is not confirmation.
- This volume covers Yechezkel 40-42 only. The altar (43), river (47), city and land (45, 48) appear only as cross-references (see section 9).
- `section` per row: `third_temple` (120 rows), `historical` (6), `comparison` (3). Gaps are ranked from third_temple rows only.
- Verification: 65 rows "Hebrew confirmed" (key words/numbers found in `hebrewInput`; pp. 172, 184, 241, 257 also checked on the page images),
  64 rows "English draft only" (no Hebrew check yet; mostly discursive pages).
- Status vocabulary: **certain** = navi/Rashi/Mishkenei Elyon main line adopted by the author; **opinion** = one view among several;
  **author (\*)** = the author's starred suggestion, usually "for study only". Conversion: 50 cm/amah, tefach 8.33 cm.

## 1. Mount, approach, enclosure (40:2-6; 42:15-20) - third_temple unless marked

| pp. | Claim (amot -> cm at 50) | Source | Status | Scene element |
|---|---|---|---|---|
| 112, 359-363 | Har HaBayis 500 x 500 reeds = **3000 x 3000 amot (1500 m square)**, 36x the Second Temple; wall separates kodesh/chol | Yechezkel 40:5, 42:16-20; Rashi; Kalir | certain | Future Mount platform (~377 m square, no wall) |
| 115-117 | Mount wall **6 thick x 6 high** (300 x 300 cm) all four sides; **five gates** (2 S, 1 E, 1 N, 1 W), opening **10 wide x 50 high**, doors; author: 10 amot of wall above the opening, 60 total | Rashi 40:5 (Middos 2:4); Mishkenei Elyon 170, 196 | 6x6 certain; gates = Mishkenei Elyon completion; 60 = author (\*) | none |
| 112-113, 116 | Sanctuary near the NW of the Mount: open ground largest S, then E, N, least W; Yerushalayim on the slope to the south | Mishkenei Elyon 184, 189, 196; Yechezkel 45, 48 | certain (Mishkenei Elyon) | Mount platform layout, city massing |
| 121-126 | Before the outer court: **soreg** 10 tefachim lattice, then **Cheil** = wall 10 amot high (author: 1 amah thick) + 10 amot open, then **12 steps** (E) or **7 steps** (N, S), each 0.5 rise x 0.5 tread, last step deep | Middos 2:3; Rambam 5:3, 6:1; Meiri; Mishkenei Elyon 191-196 | Middos completion adopted; cheil-as-wall = Rambam view | E 12 stairs, N/S 7 stairs exist; soreg/cheil absent |
| 118 | Enter by the right, circle, exit by the left; mourners the reverse | Middos 2:2 | Middos completion | pilgrim routes |
| 300-305 | Terraces: Even HaShtiya +3 fingers; House 6 amot above inner court; inner court = upper chambers = 20-amot strip; Ezras Yisroel -2.5; outer court gate floors -4 (N/S) / -6.5 (E); Har HaBayis -3.5 (N/S gates) / -6 (E gate); Mount slopes down on all sides | Rashi 42:9; Middos 2:3, 2:6; Mishkenei Elyon 192-193 | steps certain; slopes = author (\*) | scene levels match (E gate Z 300, N/S 425, inner 500/625, House 925) |

## 2. Outer court and its gates (40:6-27)

| pp. | Claim | Source | Status | Scene |
|---|---|---|---|---|
| 121-131 | Court wall 6 thick; gate opening **10 wide x 50 high** with doors; jambs 6; six **cells 6 x 6 interior, walls 5**, outside the gate on the Mount side, projecting 11; cells chain-linked, entered only from the gate passage; **Ulam** 8-amot walls + 2-amot round eilim = 10 into the court, interior 13 x 8, 50 high; **eilim 2 x 2 amot, 60 high**, palm-tree capital (author: palm = 10 of the 60) | Yechezkel 40:6-16; Rashi; Mishkenei Elyon 166-197 | certain | gates/cells/eilim/palms present; eilim 60 amot |
| 130 | Ulam doors between the eilim; author prefers doors swinging outward 90 deg into the court (or inward, or 180 deg) | author (\*) | author | gate leaves exist (20 panels/gate) |
| 133-134, 153 | Gate width 25 (5+2.5+10+2.5+5); author: 5-amot cell walls flanking the passage rise to 50 and a **ceiling spans the cell passage** (continuous Ulam-passage-gate roof) | Rashi 40:13; Metzudas Dovid; author (\*) | author | gate roofs |
| 138-140 | **Narrow (splayed) windows**, narrow inside widening OUT, open (no glass): in cells (author 12 per gate), on the cell door jambs, in the Ulamim, and in the court wall above the cells facing E/N/S only (author 12 per side; none west, none at the corner courts) | Rashi 40:16; Mishkenei Elyon 169 | shape/direction certain; counts author | 72 splayed reveals on the court walls (check for a west set) |
| 141-143 | **30 chambers on a gallery** (gezuztra) whose floor is at 50 amot = gate height: 10 E, 10 S, 10 N, none W, 5 each side of every gate; author: chambers 10 x 5, 10 high, 5-amot slab (top at 60); possibly for women | Rashi 40:17-18; Mishkenei Elyon 185, 197; Radak | 30 at 50 certain; sizes author | 30 chambers at Z 2910 (52 amot) present |
| 143, 276-278 | **Four unroofed corner courts 40 x 30 amot** for cooking kodashim kalim; no piers/gallery there | Yechezkel 46:21-22; Rashi 40:18 | certain | 4 corner kitchens present (44 x 30 in scene) |
| 144-147 | Gate to gate **100 amot**; N and S gates identical to E except **7 steps** | Yechezkel 40:19-27 | certain | matches |
| 137 | E outer gate = gate of entry all year; festivals enter N exit S (or reverse); inner E gate opens only Shabbos/Rosh Chodesh | Yechezkel 46:1, 9; Rambam 7:2 | certain | inner E gate leaves should read closed |

## 3. Inner court, gates, slaughter, service chambers (40:28-47)

| pp. | Claim | Source | Status | Scene |
|---|---|---|---|---|
| 148, 152 | Inner gates = outer gates but **8 steps** (4 amot) and the **Ulam projects OUT into the outer court**, cells behind it; sequence eilim -> Ulam doors -> Ulam (13 x 8, 50 high) -> 8 steps over the 11-amot cells -> gate | Yechezkel 40:28-37; Rashi | certain | 8 stairs, vestibule walls present |
| 150-151, 220-224 | **Six Ulamim (recesses) in the inner court wall**, 25 x 5 amot, one each side of each gate, 0.5 amah of wall left each face; door jambs, splayed windows toward the outer court above the cells (author 6 each), square buttresses (atikim); author: 25 high | Rashi 40:30, 41:15-16; Mishkenei Elyon 188 | 25x5 certain; count/height author | absent |
| 154-164, 339 | **Rinsing chamber = slaughterhouse** at the WEST shoulder of the north inner gate, door toward the gate: four marble tables 1.5 x 1.5 x 1 amot, eight low cedar posts with iron hooks (1 tefach, 3 rows); **eight slaughter tables** at the north gate: 4 in its Ulam (2 E, 2 W) and 4 in the cell passage at gate level; the Ulam is sanctified as inner court | Yechezkel 40:38-43; Rashi; Mishkenei Elyon 177-178, 199, 202 | certain | 8 tables present but clustered in the Azarah (X -1188..-662, Y -2088..-1812); chamber absent |
| 165-169 | **Levites' song chamber** (one outside, two inside, doors S) at the EAST shoulder of the north gate; **kohanim's clothing chamber** (door N) at the NORTH shoulder of the east gate; 96 garment niches per mishmar (historical, author reuses) | Yechezkel 40:44-46; Mishkenei Elyon 178-179, 199 | certain (positions) | "Song chamber" sits in the SW of the court; clothing chamber absent |
| 170-172 | Inner court **100 x 100**; altar (32) exactly central: E-W 17 Yisroel + 17 Kohanim + 32 + **34 to the Ulam**; N-S 4 wall-ramp, 62 ramp+altar, 34; Tapuach in line with the Even HaShtiya and golden altar; House is 13 amot further west than in the Second Temple (34 vs 22, KhK wall 2 vs 1) | Yechezkel 40:47; Mishkenei Elyon 182, 198, 204; Rambam 2:1-3 | certain | altar centre (0,0), facade X -2500 = 50 amot: matches; ramp south present |
| 171, 313, 342 | **Duchan**: 1-amah step + three half-amah steps, Ezras Kohanim **2.5 amot above** Ezras Yisroel; stone; Levites face east; wall 6 thick, author 60 high; three gates only | Middos 2:6; Rashi 42:12; Mishkenei Elyon 198 | Middos completion adopted | duchan rises only 1.25 amot |
| 173 | Torah/Middos items required: **kiyor + base** between Ulam and altar with pit and pulley; **ash place** E of the altar 10 amot N of the ramp start, 3 tefachim E; **shis** at the SW corner; **two tables** W of the ramp (93 vessels; fats); fire pan; libation cups | Torah; Middos; Tamid | d'Oraisa items certain; positions from Middos | kiyor present (X -2054..-1846, Y 1396..1604); rest absent |

## 4. The House: Ulam, Heikhal, Kodesh HaKodashim, side chambers (40:48-41:14)

| pp. | Claim | Source | Status | Scene |
|---|---|---|---|---|
| 174-179 | Ulam interior **20 x 11**, walls 5; entrance jambs project 3 each side so the **opening is 14 amot** (700 cm), 50 high; **12 steps** (6 amot, 21 long with landings); two eilim **2 x 2, 60 high**, palm capitals, "in place of Yachin and Boaz"; **Beis HaChalifos** 15 (N-S) x 10 (E-W) each side, author 1-amah west wall; possible pishpashim | Yechezkel 40:48-49; Rashi; Middos 3:6, 4:7; Mishkenei Elyon 166, 176, 202 | certain; 1-amah wall / pishpashim author | matches (opening 14.3 amot, pillars 60, 12 stairs, wings 4 amot deep) |
| 182-183, 240 | Heikhal **40 x 20**, all walls 6; door **10 wide x 50 high**, square posts, threshold, straight lintel | Yechezkel 41:1-2, 21; Mishkenei Elyon 164, 170 | certain (50 = Mishkenei Elyon) | matches |
| 184-186 | KhK wall **2 amot**; entrance **7 wide x 6 high**, square 4-post; **two doors always open** (author: inward); **paroches exactly the size of the gate**; Aron poles press the paroches | Yechezkel 41:3, 23; Mishkenei Elyon 159-166; Yoma 54a | certain; inward = author | partition matches; doors/paroches source-only |
| 187-192, 306 | KhK **20 x 20**; Even HaShtiya (+3 fingers; west per Rambam, centre per Tosafos Yom Tov; author study option 12 x 12); Aron, poles, kaporet, keruvim (10 tefachim, faces to each other and down; book adds "six wings each"), staff, oil flask, manna; **no upper storey**; possible west window at 6-8 amot | Rambam 4:1; Yoma 53b; Mishkenei Elyon 150, 167, 170 | 20x20 certain; rest opinion/author | Aron and keruvim present; slab, side objects absent |
| 63, 191, 201-204 | House **100 high** (front 100 wide x 100 high incl. Beis HaChalifos); author interior 85 + otem 6 + ceiling 5 + maakeh 3 + kalah orev 1; foundations 6 wide (and author 6 high) | Rashi 41:8 (Middos 4:6); Mishkenei Elyon 170-171 | 100 certain; layers author | roof ~100 amot, anti-bird points present |
| 193-200 | **33 side chambers** (15 N, 15 S, 3 W), 3 storeys, widths **4 / 5 / 6** as the House wall steps 6->5->4->3, chambers **11 long, walls 5**, west chamber 22 long; cedar beams on the steps socketed into the outer wall; winding stone stairs between storeys; author: storey 6 + 5 ceiling = 11 (total 33) | Yechezkel 41:5-7; Rashi (per R' Shemayah); Mishkenei Elyon 180-181, 203-204 | certain; heights author | 33 cells present, storeys 6 amot |
| 205-214 | **Munach** 5 wide (author 20 long) in the NE/SE corners = the ONLY way into the chambers, reached by **pishpashim** in the Ulam (north always open, south always closed, 44:1-2); west block **70 wide**: 32 + ta 4 + wall 5 + **Mesibah** 5 + wall 5 (N) / **Beis Horadas HaMayim** 5 + wall 5 (S); Mesibah climbs to the cell roofs and House roof; 11-amot space behind the House | Yechezkel 41:9-12; Rashi; Middos 4:5, 4:7; Mishkenei Elyon 181, 204 | certain (Mishkenei Elyon split 5/5) | 5-amah passages both sides present |
| 215-219 | Length 100 (5+11+6+40+2+20+6+4+6); front 100 wide (Ulam 20, wall 5 x 43 each side, Beis HaChalifos 15 x 10); knife racks per 24 mishmaros (author) | Yechezkel 41:13-14; Middos 4:7 | certain | matches |

## 5. Wall lining, reliefs, ceiling, doors (41:15-26) - the art brief

| pp. | Claim | Source | Status | Scene |
|---|---|---|---|---|
| 222-234 | KhK and Heikhal walls, jambs, doors, ceiling (and, in the Third Temple, the wall **behind the doors**) lined with thin **cedar boards carved and overlaid with gold**, floor to ceiling; only the window openings stay open; author: floor also carved boards under gold; gold sheets beaten into the carving so the forms stay visible, fixed with gold nails | Yechezkel 41:16-17; Rashi; Melachim I 6:32; Mishkenei Elyon 168 | certain | gold veneers present; no carving |
| 235-239 | **Reliefs: keruv, palm, keruv, palm...** on every wall; each keruv has TWO faces (faces only, not bodies): **young lion's face on the keruv's right looking to the palm on its right, man's face on its left looking to the palm on its left**; lion = right/chesed (Mishkenei Elyon); author speculates six wings | Yechezkel 41:18-20; Rashi; Mishkenei Elyon 168, 190 | certain (two faces, alternation); side = Mishkenei Elyon | palm-only study panel; keruvim never modelled |
| 223-226 | **Atikim** = square buttresses 3 per side (N, S) in the KhK and Heikhal, inside and outside, ~2/3 height; **windows**: author 12 in the KhK (3 per side incl. E above door and W), Heikhal 4 N / 4 S / 4 E, always open | Mishkenei Elyon 169; author (\*) | count author | 16 windows N/S only; no buttresses |
| 259-263 | Heikhal: **two PAIRS** of 5-amot leaves, 50 high: outer pair 1 amah in from the jamb folding onto the 6-amot wall thickness, inner pair folding onto the 5-amot shoulders inside (Tanna Kamma, Rambam 4:7, Ramchal); locked evening/opened morning via the north pishpash; **KhK leaves 3.5 x 6**, cedar, keruvim+palms, gold, always open | Yechezkel 41:23-24; Rashi; Middos 4:1-2; Tamid 3:7 | certain | 4 flat "Open Heichal door" slabs protrude into the Heikhal |
| 264-267 | Doors carved like the walls; **cedar bracing beams from the Heikhal wall to the Ulam wall protrude east through the facade, gold-covered** (author: 10 beams 6 x 2 up to 60 amot, also along the wings); **no exposed wood anywhere**; Second-Temple **miltaros are not carried over** | Yechezkel 41:25; Rashi; Middos 3:8; Mishkenei Elyon 171, 202; Rambam 1:9 | beams certain; sizes author | layered cornice/lintel mouldings (Second-Temple style); no beams |
| 268-270 | Splayed windows both sides of the Ulam entrance (author: along the whole front, 12); **palm reliefs only** on the Ulam jambs; author: Ulam doors with palms; ceiling = 2-amot cedar "ribs" + 1 rafters + 1 carved gold kiyur + 1 maazivah = 5 | Yechezkel 41:26; Rashi; Middos 4:6 | jambs certain; rest author | Ulam has door frames, no palms on jambs |

## 6. Vessels (41:22) - see the keilim review for placement; dimensions only here

Shulchan 2 x 1 x **3 amot** (150 high), gold over wood, 12 loaves on 28 gold rods and 4 uprights to 5 amot (pp. 241-251). Menorah **18 tefachim** (150 cm), one kikar, branches N-S (Rambam), six wicks toward the centre lamp, centre toward the KhK, **three-step stone** before it (pp. 252-254). Golden altar **1 x 1 x 2 amot at a 5-tefach amah** (41.7 x 41.7 x 83), four horns (p. 255). All three in the western half of the Heikhal (pp. 256-258; diagram 22:28 on p. 257 is Third Temple; diagram 22:27 there with ten menorot/tables is **Bayit Rishon** - historical). Hebrew confirmed on the p. 241 image (קץ הימין).

## 7. Priestly chambers, kitchens, lower chambers (42:1-14)

| pp. | Claim | Source | Status | Scene |
|---|---|---|---|---|
| 272-299 | **Upper chambers** NW and SW: 100 x 50, 3 storeys, **20 amot from the House's side building** (15 behind the Beis HaChalifos + 5), floor at the **inner-court level**, doors N (and S into the strip), 50 amot of open court north of them, east wall = 50-amot "fence"; **atikim** fill the 3rd-storey N/S walls and send three pillars down each wall projecting ~1 amah in/out, built top-down, no outside buttresses; author D.M. numbers: 50 high, storeys ~10, pillars ~7 thick | Yechezkel 42:1-8; Rashi; Mishkenei Elyon 186-187, 198 | layout certain; numbers author (\*) | block 98 x 46 at Z 405 (below court), ~24 high, no atikim |
| 276-290 | **20-amot strip** is inner court; its **west end (north side) = priestly kitchen** for chatas/asham/menachos (ovens); entered from the outer court by a **1-amah sloped opening** at the end of the court wall into a 5 x 10 passage; author also proposes an opening from the inner court | Yechezkel 42:3-4, 46:19-20; Rashi; Menachos 96a; Mishkenei Elyon 187 | certain (kitchen, 1-amah way) | strip open; no ovens, no 1-amah opening |
| 300-312, 341 | **Lower chambers** NE and SE: 100 x 50, 3 storeys, no atikim, at outer-court level, from the east end of the gate cells leaving **11 amot** to the east wall, doors N/S and **into Ezras Yisroel** (weekday entrance); function unspecified - author fills them with Sanhedrin, lots, Beis HaMoked, mikvaot, Kohen Gadol's chamber, seals, wood, metzoraim, nazirites, oil and wine, pilgrims' seating (pp. 316-337) | Yechezkel 42:9-12; Rashi; Mishkenei Elyon 187, 197 | existence/size certain; uses author (\*) | absent |
| 345-358 | Kodshei kodashim eaten in the **upper** chambers (inner-court sanctity), in the **four service garments**, then garments left there and ordinary clothes put on before entering the outer court; author: eating standing at **high tables** (doubt), Kohen Gadol alone sits to eat in the south pishpash room; three camps mapped (Cheil stops non-Jews) | Yechezkel 42:13-14, 44:3; Rashi; Chagigah 2:7; Rambam | garments certain; posture author | kohanim figures absent |

## 8. Historical / comparison statements (do not read as Third Temple facts)

- p. 160 (dup 47): Second Temple Azarah slaughter layout (8 amot, 12.5 Beis HaMitbachayim, 24 rings) - context only; Third Temple keeps kodshei kodashim slaughter in the north but adds the north-gate tables.
- p. 169: 96 garment niches for 24 mishmaros - Second Temple (Rambam Klei HaMikdash 8:8); author reuses the idea.
- p. 186: First Temple amah traksin wall with 5-post door; Second Temple two parochos - contrast for the 2-amot Third Temple wall.
- p. 226: two golden crowns on two Heikhal windows - Second Temple only.
- p. 227: gold-beating technique of the First Temple (Melachim I 6:32) - applied by the author to the Third Temple finish.
- p. 265: five stepped olive-wood miltaros above the Ulam entrance - Second Temple; not in the Third Temple description (scene has Second-Temple-style layered lintels).
- p. 257 diagram 22:27: Bayit Rishon with ten menorot and ten tables (Menachos 98b) - Third Temple has one of each.
- comparison: p. 112 (First/Second Temple 23 amot below the summit; future site raised), p. 113 (heights 120 / 100 / 100), p. 172 (House moves 13 amot west because the altar is fixed).

## 9. Chapters 43-48 as they touch the surroundings (cross-references only in this volume)

City south of the Mount on the slope (pp. 112, 305; 45:1-5, 48:10-21); kohanim and Levites dwell around Har HaBayis (p. 326; 45:1-9);
twelve city gates for the tribes (p. 224; 48:30-35); **water flows from the KhK out through the south inner gate** (p. 340; 47:1-2 - the
river's source point for the scene); festival N->S passage and inner east gate open only Shabbos/Rosh Chodesh (pp. 137, 341; 46:1, 9);
corner courts and the priestly kitchen (pp. 143, 276; 46:19-24); altar details deferred to "Perek 43 note 19" (Part 2, not in this export).

## 10. Top 15 gaps (third_temple rows only; scene = AGENTS.md / RELEASE-NOTE-Walkthrough-06 / architecture-manifest bounds)

1. **Wall reliefs** (pp. 235-239, 222, 231): alternating two-faced keruv (lion right, man left) and palm, cedar under gold, on ALL KhK and Heikhal walls, above and behind the doors. Task: model one repeat unit, tile Heikhal X -5600..-3600 and KhK X -6700..-5700 inner faces, Z 925..3025, plus door reveals; then the carved gold ceiling.
2. **Doors and paroches** (pp. 259-264, 184-185): Heikhal two pairs of 5-amot leaves folding into the wall thickness and onto the shoulders; KhK 3.5 x 6 leaves open inward; paroches 7 x 6 at X -5600. Task: import DoorsParochesV1, re-articulate per p. 262, retire the four slabs that protrude 3.8 m into the Heikhal.
3. **Mount enclosure, soreg, cheil** (pp. 115-126, 359-363): 3000 x 3000 amot wall 6 x 6 with five 10 x 50 gates; soreg lattice; 10-amot Cheil wall + 10 amot open before 12/7 steps. Task: scenario-level ring (label as Mishkenei Elyon/Middos completion) or at least wall+gates+soreg+cheil around the present platform.
4. **Keilim sizes and KhK objects** (pp. 241-255, 187-190): shulchan 150 high, menorah 150 with a 3-step stone, incense altar 41.7 square x 83; luchot, staff, manna, oil beside the Aron.
5. **Upper priestly chambers** (pp. 272-297): raise floors to the inner-court level, widen to 50 amot, add 3-pillar atikim and a heavy third storey (~50 amot high).
6. **Lower chambers NE/SE** (pp. 300-313, 341): two 100 x 50 three-storey blocks at outer-court level leaving an 11-amot passage to the east wall, with doors into Ezras Yisroel.
7. **Six 25 x 5 recesses in the inner court wall** (pp. 150-151, 220-226) with splayed windows and buttresses, flanking each inner gate.
8. **Slaughter tables and rinsing chamber** (pp. 154-164): move the 8 tables into the north gate (4 in the Ulam, 4 between the cells); add the closed chamber with 4 marble tables and hook posts at the gate's west shoulder.
9. **Song and clothing chambers** (pp. 165-169, 329-330): song chamber (split in two, doors S) east of the north gate; clothing chamber (door N) north of the east gate; scene song chamber is in the SW.
10. **Priestly kitchen and 1-amah entry** (pp. 276-290, 319-320): ovens at the west end of the north 20-amot strip; 1-amah sloped opening at the NW end of the court wall; strip at inner-court level.
11. **Altar furniture and duchan** (pp. 170-173, 313, 342): kiyor pit/pulley, ash place, shis, two tables W of the ramp, libation cups; duchan to 2.5 amot total rise (scene 1.25).
12. **Ulam facade** (pp. 264-268, 174): gold beam ends protruding east above the door, palm-relief jambs; review the Second-Temple-style layered lintel/cornice against p. 265.
13. **Windows** (pp. 224-226, 138): add KhK E (above door) and W windows and Heikhal E windows; remove any west-wall reveals on the outer court wall.
14. **Even HaShtiya slab and pole tips** (pp. 187-189, 306, 261): 6 cm raised 12 x 12 amot slab (study-only flag); poles touching the paroches.
15. **People and service** (pp. 118, 137, 313, 339, 349-357): kohanim in four white garments, Levites on the duchan facing east, pilgrims N->S with the inner east gate closed on weekdays, women on the gallery, non-Jews stopping at the Cheil.

Already consistent with the book (no action): gate/court measures and step counts, 100-amot gate spacing, 30 gallery chambers at 50 amot, 60-amot eilim with palms, Ulam 20 x 11 with a 14-amot opening and 12 steps, Heikhal/KhK sizes and the 2-amot partition, 33 stepped side cells, 70/100 widths, N/S 5-amot passages, House ~100 high with roof spikes, altar 32 at the court centre 34 amot from the Ulam with the south ramp, kiyor between Ulam and altar, four corner kitchens, Beis HaChalifos wings with a thin west wall, keilim positions after the 2026-09-07 move.

## Files

- `C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\research\book-scene-requirements-20260907.md` (this file)
- `C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\research\book-scene-requirements-20260907.json` (129 rows: page, dup_pages, section_ref, section, topic, claim, source, status, affects, verification; historical list; top_15_gaps)
