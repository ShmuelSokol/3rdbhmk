# Herodian ashlar V4 — sources, and what is measured versus authored

Generator: `Scripts/create_herodian_ashlar_v4.py`. Textures and measured statistics:
`SourceAssets/material-review/HerodianAshlarV4/manifest.json`.

## Why this set exists

Shmuel's instruction, verbatim, 9 September 2026:

> "I want the temple stones used for wall wherever you are using stones to be the large style stones
> used for the 2nd temple outer wall."

The masonry of the Second Temple's outer retaining wall is Herodian ashlar — the stonework the Kotel
(Western Wall) is made of. This **overrides** the earlier V2/V3 decision (`Scripts/create_limestone_textures_v2.py`
docstring, iteration V3) to author "plain hewn and dressed faces with only a soft arris (no drafted-margin
'picture frames')". That judgement was the coordinator's, for a hewn Third Temple wall; the instruction
replaces it. V4 builds the Herodian style. It does not argue the point.

## Status labels used below

- **MEASURED** — a published figure from the cited source, used as given.
- **MEASURED, NARROWED** — the cited range is wider than what V4 uses; V4 picks a band inside it, stated.
- **AUTHORED** — a value chosen by this pass. Either the sources do not fix it, or a tiling texture
  cannot express the real thing and this is the nearest approximation. Never presented as sourced.

---

## 1. Block size — "the blocks must read as big"

| Quantity | Source figure | Status | V4 value |
|---|---|---|---|
| Course height, visible Western Wall courses | "most about a metre high" | MEASURED | 3 courses of 92.0 / 101.5 / 106.4 cm per 300 cm tile |
| Block length | "two to five metres long" (Wikipedia, *Western Wall*); the brief's working range 1.5–3.0 m | MEASURED, NARROWED | 136–300 cm (1 or 2 blocks per course) |
| Typical ashlar height/width | "1–2 metres" | MEASURED | consistent |
| Weight | 2–8 tonnes typical | MEASURED | not modelled (texture only) |
| The Western Stone | 13.55–13.6 m long, ~3.1 m high, 517–570 t | MEASURED | not represented; a single stone longer than the 3 m tile cannot tile |

The 300 cm tile is the binding constraint: it is `TilingCm` on `MI_PBR_LimestoneAshlar` /
`MI_PBR_LimestoneTrim` and on the V4 children, and it is unchanged from V2/V3. At 300 cm the largest
representable stone is exactly 3.00 m long — the upper end of the common Herodian range, and the tile
does contain one. Blocks longer than that (the great course, the Western Stone) are **out of reach of a
tiling texture** and are not claimed.

**AUTHORED:** the number of blocks per course (1 or 2, weighted 0.55/0.45), the running-bond stagger
(≥45 cm), and which stone gets which length. Real coursing is surveyed, not random.

## 2. The drafted margin

| Quantity | Source figure | Status | V4 value |
|---|---|---|---|
| Margin width, Western Temple Mount blocks | 5–10 cm | MEASURED | Ashlar 7.7–13.5 cm, Trim 5.6–10.7 cm |
| Margin width, Tombs of the Patriarchs, Hebron | 5.5–11.5 cm | MEASURED | — |
| Boss projection, Western Temple Mount blocks | 6–14 mm below the margin | MEASURED | Ashlar 1.47–1.95 cm, Trim 1.06–1.45 cm |
| Boss projection, Hebron | 0.9–1.5 cm | MEASURED | — |
| Upper margins wider than lower | stated tendency | MEASURED (qualitative) | top margin ×1.25, bottom ×0.92 of the block's base width |
| Boss finish | flat, smooth, slightly protruding; **not** rusticated | MEASURED (qualitative) | boss normal xy p95 0.240 (Ashlar) versus V3's chiselled face 0.368 |
| The margin-to-boss step | the defining feature of the style | MEASURED (qualitative) | boss-edge normal xy p50/p95 **0.968 / 0.984** — the same order as a joint |

V4's margins run a little wider than the Western Wall's measured 5–10 cm because the coordinator's brief
specified 8–15 cm and because at 300 cm / 2048 px a 6 cm margin is 41 px and survives mip reduction
poorly. **AUTHORED, inside the Hebron range, above the Western Wall range.**

Boss projection is **AUTHORED above both source ranges** (measured: 0.6–1.4 cm at the Western Wall,
0.9–1.5 cm at Hebron; V4: 1.47–1.95 cm on Ashlar, 1.06–1.45 cm on Trim). This is the one dimension raised
deliberately for legibility, and here is the reason. The first V4 iteration used 1.18–1.70 cm over a
0.70 cm bevel; the coordinator's review found that the margin read as *a thin scribed line around the
face* rather than as a recessed band with a raised panel inside it — which is precisely what makes the
Kotel look the way it does. The cause was the bevel, not the height: at 0.70 cm the step is 4.8 px at
6.827 px/cm and about 2 px after one mip, so it aliased away into a line. V4 now uses a **0.40 cm bevel**
(0.28 cm on Trim) with the taller boss, giving a boss-edge slope near 4:1 and a measured boss-edge normal
xy p50/p95 of **0.968 / 0.984** — the same order as the joints (0.968 / 0.994), while the boss surface
itself stays smooth at p95 0.240. The step, not the boss, carries the style.

Crisp arrises are the point. V4's arris (joint-to-margin chamfer) is 0.26 cm — 1.8 px, as sharp as a 2048
map can be without aliasing. **AUTHORED** (a real arris is a knife edge).

Ambient occlusion also had to change for the margin to read as a *band*: the original two cavity radii
(2.0 cm and 0.6 cm) could only darken a 2 cm lip of a 10 cm margin, so a third, wide radius (6.0 cm on
Ashlar, 5.0 cm on Trim) was added and the whole recessed margin now picks up occlusion from the boss
beside it. **AUTHORED**, and it is what turns two flat planes into a panel.

## 3. Courses set back — the batter

| Quantity | Source figure | Status | V4 value |
|---|---|---|---|
| Per-course setback | "each course of ashlars was set back ½ inch" ≈ 1.27 cm | MEASURED | 1.5 cm (Ashlar), 1.05 cm (Trim) |

**AUTHORED — and this is the one real compromise in the set.** A tiling texture cannot carry an
accumulating per-course setback: after three courses the tile wraps, and the accumulated depth would have
to jump forward by 3× the setback at one bed joint in three, which reads as one abnormally proud course
every 3 m. So V4 authors the setback as a **local ledge**: the top of each stone leans out over its bed
joint (rise `setbackCm` over `courseSetbackReachCm` — 18.4 cm on Ashlar, 12.7 cm on Trim), and the course
above starts flush. In raking light that produces exactly the shadow-under-the-upper-course and lit-ledge-
on-the-lower-course that the real setback produces; what it does not reproduce is the wall's cumulative
batter, which belongs to the geometry, not the texture. Recorded in `manifest.json` →
`conventions.courseSetback`.

## 4. Joints

| Quantity | Source | Status | V4 value |
|---|---|---|---|
| Laid dry, no mortar; extremely fine joints | standard description of Herodian retaining-wall masonry | MEASURED (qualitative) | Ashlar 0.8 cm wide × 1.05 cm deep; Trim 0.5 cm × 0.7 cm |
| Joint colour | a shadow line, not a mortar band | MEASURED (qualitative) | adjoining stone × 0.46 (Ashlar) / 0.50 (Trim), pulled 22 % toward its own luminance |

**AUTHORED:** the exact widths. Real Herodian joints are often finer than 0.8 cm; below ~0.7 cm they
disappear into 2048-map mip chains and the wall loses its coursing at distance, which is the failure mode
that matters here.

## 5. Colour

**MEASURED, and it is the project's own accepted measurement, not a new claim.** The palette is
calibrated on the accepted Kotel photo texture
`SourceAssets/kotel-detail/PhotoSurfaceV1/kotel-wall-cleaned.png` (see its `PROVENANCE.md` — it is an
AI-cleaned, perspective-rectified derivative of two photographs Shmuel supplied on 2026-09-07, with
photographic lighting partly baked in; it is not a documentary photograph or a surveyed elevation). Its
sRGB means are 0.728 / 0.635 / 0.515, G/R 0.875, B/R 0.710. V4 Ashlar measures 0.744 / 0.650 / 0.529,
G/R 0.873, B/R 0.711 — the same palette V3 was accepted on.

The stone itself is **meleke** (*malaki*) limestone, quarried locally and slightly uphill of the Temple
Mount: MEASURED (qualitative). Warm cream to honey, weathering to grey-gold: the four colour families
(`base` / `cream` / `honey` / `greygold`) and their weights are **AUTHORED** to span that description.

## 6. Surface and weathering

All **AUTHORED**: fine chisel dressing on the boss, now **isotropic** (amplitude 0.070–0.115 cm at a
0.40–0.90 cm grain in both axes); flat-chisel dressing on the margin running *along* the margin it belongs
to, at a third of the boss amplitude so the margin reads flatter than the boss (margin normal p95 0.176
versus boss 0.240); broad per-stone patina; pitting (499 pores on the Ashlar tile); edge chipping
(20 chips); run-off darkening and streaking toward the bottom of each stone; patchy biological darkening
low on each stone and in the joints.

Two review corrections are recorded here because they are the kind that recur. (1) *Stucco.* The first
version carried 0.26 cm of low-frequency height undulation and put most of its albedo mottle on the
9–37 cm noise band; the boss read as plaster. The height cloud is now 0.10 cm, the mottle energy moved to
the 0.3–1.2 cm stone-grain band, and the intra-stone patina was halved and made finer, with the variation
it lost given back *between* stones (value jitter 0.105 → 0.125) — which is where a real wall carries it.
(2) *Wood grain.* The boss tooling was anisotropic at roughly 4:1 (strokes 1.6–3.6 cm long, 0.45–0.75 cm
apart) and read as grain on the larger stones — the same artefact the V2/V3 pass hit and fixed by slowing
the stroke drift. Here the directional component was dropped from the boss altogether and the tooling is
carried in isotropic fine grain instead; the margin keeps a short directional stroke, which is correct
drafting and cannot read as grain across a 10 cm band.

Biological darkening in reality is a function of **height above the ground and of splash**, which a
world-tiling texture cannot know: every 3 m of wall repeats. V4 applies it per stone instead. If the
coordinator wants true low-on-the-wall darkening it has to come from the material or vertex colour, not
from this texture. **Stated as a limitation, not fixed here.**

Hand-cut wobble on the joint lines and the margin edges (0.13 cm over a 55 cm scale on Ashlar) is
**AUTHORED**, to defeat the CAD look; it is deliberately slow drift, not squiggle, because Herodian
setting-out is straight.

## 7. Where the drafting is NOT applied, and why

Two exclusions, both measured, both recorded per slot in every plan and apply receipt
(`excludedSlots`) and in `Scripts/release_herodian_ashlar_v4.spec.json` -> `excludeSlots`.

**The menorah's stone of three steps (3 slots, `Release/MenorahV4`) - EXCLUDED by default.**
Rambam, *Mishneh Torah, Hilkhot Beit HaBechirah* 3:11: the stone of three steps before the menorah, on
which the kohen stands to dress the lamps. Two reasons. *Idiom:* drafted-margin work is the dressing of a
monumental retaining wall - it is what the Temple Mount's outer faces were given, not what a small dressed
furnishing inside the sanctuary was given, and Shmuel's instruction is about "the temple stones used for
wall". I found no source treating the menorah's step-stone as ashlar work. *Scale:* the Trim margin is
5.6-10.7 cm, so on a tread of roughly 50-60 cm the margin would cover most of the surface and the boss
would be a sliver. Cancel with `-HerodianV4IncludeMenorahStone`.

**Trim mouldings with a face narrower than two margins (136 slots) - REPORTED, included by default.**
Measured from `SourceAssets/architecture-manifest.json` (`expectedBoundsUnrealCm`, slots whose
`sourceMaterialKey` is `trim`). Of the 309 Trim slots in the measured architecture, three members have a
visible face of only 14-15 cm:

| Member | Slots | Bounding box (cm) | Face width |
|---|---|---|---|
| Court string course and cornice | 72 | 8 x 15 x 7850 | 15 cm (some runs to 55) |
| Hearth stone surround | 48 | 8 x 15 x 110 | 15 cm |
| Facade recessed field rail | 16 | 7.5 x 14 x 525 | 14 cm |

Two Trim margins are 11-21 cm, so on a 14-15 cm face the margin can consume the whole member and no boss
ever appears; and because the master is triplanar world-space, such a member samples an arbitrary 15 cm
strip of the 300 cm tile and crosses joints and margins along its length. Every other Trim member is
30 cm or wider and carries the drafting comfortably: splayed high window stone reveal (72, face 30 cm),
high window sill and lintel (72, 40 cm), facade pilaster base and capital (12, 35-70 cm), Ulam nested
stone door frame (6, 30-50 cm), Ulam lintel moulding (6, 50 cm), sanctuary roof stone moulding (6, 50 cm),
layered Ulam roof cornice (4, 30-90 cm), facade pilaster shaft (3, 125 cm). None of the 299 slots in
`Measured architecture/detail` is furniture - in this project "detail" means architectural detail.

They are left IN by default and `-HerodianV4ExcludeNarrowTrim` takes them out, because on the map that
actually ships these 136 slots still carry the original flat stand-in, and a slightly busy 15 cm cornice
seen from the court floor is a smaller defect than a measurably flat one. The proper answer is a
non-drafted fine-limestone moulding variant, which is out of this pass's scope. **AUTHORED judgement,
stated so it can be overruled in one switch.**

## References

- Wikipedia, *Western Wall* — https://en.wikipedia.org/wiki/Western_Wall (course height ~1 m, length 2–5 m, 2–8 t, meleke quarried locally and uphill)
- Wikipedia, *Western Stone* — https://en.wikipedia.org/wiki/Western_Stone (13.55 m × ~3 m, ~517 t)
- Madain Project, *Herodian Stone* — https://madainproject.com/herodian_stone (drafted margin 5–10 cm, boss 6–14 mm proud; upper margins wider)
- *Decorative Drafted-margin Masonry in Jerusalem and Hebron and its Relations* — https://www.academia.edu/40413076/Decorative_Drafted_margin_Masonry_in_Jerusalem_and_Hebron_and_its_Relations (Hebron margins 5.5–11.5 cm, bosses 0.9–1.5 cm)
- Biblical Archaeology Society, *The Temple Mount in the Herodian Period (37 BC–70 A.D.)* — https://www.biblicalarchaeology.org/daily/biblical-sites-places/temple-at-jerusalem/the-temple-mount-in-the-herodian-period/ (each course set back ½ inch)
- Ritmeyer Archaeological Design, Temple Mount — https://www.ritmeyer.com/category/temple-mount/ (Herodian masonry: flat slightly raised centre boss, flat margins)
- Project-internal: `SourceAssets/kotel-detail/PhotoSurfaceV1/PROVENANCE.md`; `SourceAssets/material-review/LimestoneV2/manifest.json` (iteration V3, the set being replaced); `SourceAssets/lighting-review/lighting-v3-inventory-20260908T183719554035Z.json` (slot census).

## What this set does not establish

It is a procedural authored texture, not a photogrammetric scan of meleke. The statistics in
`manifest.json` prove that the drafted margin, the boss projection, the joint depth and the palette are
present at the stated centimetre sizes. They do not establish that the wall looks right — that is the
coordinator's real-RHI capture. Nothing here is archaeological authority for the Third Temple's masonry;
it is the Second Temple outer-wall style Shmuel asked for, applied to a modelled building.
