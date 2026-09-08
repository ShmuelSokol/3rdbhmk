# The Aron over the Even HaShetiyah (es-Sakhra): analysis and reviewed plan, 2026-09-08

Instruction: "the position of the aron should be directly on top of the rock in the center of the dome of the rock."
Nothing was applied. Receipts: `aron-alignment-plan-20260908T190909002075Z.json` (this folder), written by
`Scripts/plan_aron_alignment.py`. Apply tool (gated OFF): `Scripts/release_aron_alignment.py` + `.spec.json`.

## 1. Headline finding: the Temple is already aligned on the Dome

The stated "facts" carried a units error. In `jerusalem.json` the feature `points` and terrain heights are in
**amot (0.5 m)**, not metres, and the native context meshes carry the alignment
`UE_cm = ((x + 17.5097) * 50, (y - 0.5513) * 50)` (constants `SOURCE_ALIGN_X_AMOT` / `SOURCE_ALIGN_Z_AMOT` in
`Scripts/create_mount_enclosure.py`; `mount-platform-design.json` says "alignment already baked in native
meshes; NEVER apply twice"). Proof: OSM Western Wall (building 817206833) vertex (-320.06, 238.71) amot maps to
(-15127.5, 11907.9) cm, the KotelStoneV2 E0 mesh corner in its manifest is (-15138.7, 11908.1): 11 cm error over
a 150 m lever.

With that alignment the **Dome of the Rock polygon (OSM 4709536, 9 vertices, octagon ~53 m across) has its
centroid at exactly (-6300.0, 0.0) cm**. The exporter's "hypothetical temple alignment" (provenance note) was made
on the Dome. The main-map Aron body centre is (-6200.0, 0.0, 925) (receipt `third-party/aron-poles-centre-20260908T022034Z.json`).

So the "(-142, -5) m" centroid in the brief was amot without the offset; the Kotel face is NOT at -148 m; the
platform's west edge does NOT pass west of it (section 4).

## 2. The rock

| item | value | status |
|---|---|---|
| Sakhra plan size | about 18 x 13 m, up to ~1.5 m above the floor | secondary (Wikipedia, Foundation Stone) |
| dome inner drum | about 20 m diameter | secondary (Wikipedia / Britannica) |
| rock offset from the dome centre | **UNVERIFIED** - ritmeyer.com and madainproject.com refused automated fetches; no plan with coordinates was obtainable. Bound: the 13 m axis inside a 20.4 m drum limits the offset to (20.4 - 13)/2 = 3.7 m | authored bound |
| Ritmeyer's Ark depression | rectangular cutting ~2.5 x 1.5 cubits (4 ft 4 in x 2 ft 7 in) at the centre of his Holy of Holies; its position on the rock not retrieved, NOT used numerically | secondary (biblearchaeology.org summary of Ritmeyer) |
| rock summit elevation | **743.7 m** (2,440 ft "above the Mediterranean", the 1865 Ordnance Survey figure quoted by lifeintheholyland.com); Temple Mount ~740 m (Wikipedia). Uncertainty +-1 m | secondary |
| project datum | Z 0 = 748 m (`referenceElevationMetres`); rock summit = **Z -430 cm**; DEM at the Dome centroid reads -85 cm (747.2 m) because the DEM is a surface model biased by the dome itself | derived |

**Target for the Aron centre: (-6300, 0) cm with an uncertainty radius of 4.2 m**
(root-sum-square of OSM outline 2.0 m, dome centre vs octagon centroid 0.5 m, rock centre vs dome centre 3.7 m).
Nothing in this project can place the rock better than that without a surveyed plan.

## 3. Translation per map

| map | Aron centre now | delta to Dome centroid | verdict |
|---|---|---|---|
| Main, 50 cm | (-6200, 0) | **(-100, 0) cm = -1.0 m west**, uncertainty +-424 cm | within uncertainty; already aligned |
| Candidate, 48 cm | (-5952, 0) | **(-348, 0) cm = -3.5 m west**, uncertainty +-424 cm | 248 cm of it is a systematic drift: the .96 conversion was pivoted at the outer altar (`fixedOriginCm [0,0,0]`), so the Aron slid east by 6200 x 0.04 |

Candidate re-pivot alternative (frame-representable): translate the converted Temple set by **(-248, 0, 0)** and set
`MikdashSceneUnits.FixedArchitectureOriginCm` from (0,0,0) to **(-6200, 0, 0)**. Scaling about pivot Q by r equals scaling about
the origin plus a translation Q(1 - r); every runtime adapter that goes through `TryLegacyTemplePoint` then follows with no C++
edit. Aron lands at -6200 (residual 100 cm to the centroid, identical to main).

Vertical (separate decision, not applied): the Aron floor is 13.55 m (main) / 13.18 m (candidate) above the published rock summit.
Mishnah Yoma 5:2 / Rambam 4:1 put the stone three etzbaot above the Kodesh HaKodashim floor; resting the Aron on the rock would
mean a Kodesh floor at Z about -436 cm, i.e. lowering the Temple ~13.6 m, putting the court platform top near 734-735 m - below the
present esplanade (~740 m) and invalidating the Mount deck, terrain cut and Kotel joins. Recorded, not recommended now.

## 4. Consequences (numbers from the receipt)

Court platform SM_0127 = +-8100 cm (main) / +-7776 cm (candidate), sitting on the Mount deck at Z 0.

* **Kotel**: the prayer face (KotelStoneV2 E0, OSM 817206833) runs from (-15127, 11908) to (-14450, 15836) cm - it is
  south-west of the court, Y +119..+158 m. The platform's Y range (+-81 m) does not overlap it. West edge minus Kotel face X:
  main as built +7027 cm, main after -100 cm +6928 cm, candidate re-pivot +7104 cm - the platform edge stays **~70 m EAST** of
  the Kotel face in every option (nearest edge-to-face distance 79-84 m). The premise "it will likely pass west of it" is wrong.
* **Under the platform** (unchanged by any option): OSM buildings 4709536 Dome of the Rock, 45099263 Dome of the Chain,
  291836728/291841772/291841778/748953252/748953265 (arcades and small domes of the raised Haram platform); 14-17 Haram paths;
  7-8 green patches. The Kotel plaza (OSM 26492734, centroid (-19,185, +16,957) cm) and Al-Aqsa (OSM 280309331, centroid
  (-3,569, +21,027) cm) lie well outside every option.
* **East edge over the Kidron slope**: DEM ground along X = +8100 is Z -635 to -1067 cm (737-741.6 m), i.e. the deck at Z 0
  already stands 6-11 m above natural ground there; a 1-3.5 m westward move changes that by 4-12 cm. No terrain consequence: the
  cut was made for the Mount deck ring (X -213..+150 m, Y -252..+260 m), not for the court platform.
* **Yechezkel 3000-amot precinct** (courts 500 amot from the west face, 501 from the north, `enclosure-review/geometry-manifest.json`,
  status still offline/native pending): main as built faces X -33100..116900, Y -33150..116850, **1914** OSM buildings inside by
  centroid; main after -100 cm: X -33200..116800, 1917 inside. Candidate (1440 m side): as built X -31776..112224, Y -31824..112176,
  1700 inside; re-pivot X -32024..111976, 1701 inside. Any precinct build should take its faces from the map it targets.

## 5. Routes

**A - translate the Temple.** Main-map inventory (2026-09-08T13:31Z, 7767 actors; later work added paroches, tour markers, crowd
field, service and transit actors): Temple set = 2633 architecture + 211 friezes + 15 door parts + 7 menorah + 7 shulchan + 4 Aron +
1 incense altar + 7 SanctuaryFinishes review panels (2885 StaticMeshActors, re-spawned) plus PlayerStart, 4 cameras, Kodesh point light,
Heikhal rect light, ambient sound, 5 residents (12 moved by modify+move). Files that hardcode Temple coordinates (-6200/-5600/-5330/-4650):
17 scripts, 22 specs, 11 C++ files (runtime: MikdashCinematics.cpp, MikdashFXDirector.h/.cpp, MikdashServiceActor.h/.cpp,
ServiceScheduleMath.h; tests: CameraPathMathTest, SaveMigrationMathTest, ServiceScheduleMathTest, SurfaceWearMathTest, TourMathTest),
7 data files (tour-stops.json, codex-entries.json, aron-placement-spec.json, heikhal-keilim-spec.json, sanctuary-finishes-spec.json,
fx-materials.json, surface-detail.json). Full list in the receipt `routes.A_translateTemple.hardcodedTempleCoordinates`.
Does not break the terrain cut. On the candidate the hardcodes are already routed through the Selected48 frame, so a re-pivot
costs the actor pass plus one descriptor property.

**B - translate city, terrain and georeference.** 4858 context actors (2877 streets, 1498 buildings, 256 terrain tiles, 102 facades,
88 infill, 13 bus, 14 Kotel actors, 3 mount access, 2 platform, 5 ISM) plus 4 metric crowd zones, transit stops, bird perches, and
re-origining `SOURCE_ALIGN_X_AMOT` in the generators and `mount-platform-design.json`. Preserves every Temple hardcode and receipt,
keeps deck and terrain together, but breaks the baked-alignment invariant, the Kotel scripts' identity guards (they refuse a base wall
not at identity) and stales every Kotel/terrain receipt that records world bounds.

**Recommendation.** Main: **do not move** - 100 cm is below the 424 cm the evidence supports. Candidate: **Route A as a re-pivot
(-248, 0, 0) + descriptor pivot (-6200, 0, 0)**, when the candidate is next touched, because it removes a systematic error and keeps
the runtime frame consistent; do not chase the residual 100 cm on either map. Route B rejected.

## 6. Sources (certain / disputed / authored)

* **Certain (text)**: Mishnah Yoma 5:2 - after the Aron was taken away a stone from the days of the early prophets, called Shetiyah,
  three etzbaot above the ground, stood there and the Kohen Gadol placed the fire-pan on it. Yoma 53b-54b - the Gemara on Shetiyah
  (the world founded from it), the Aron's hiding (Yoshiyahu) and the poles pressing into the paroches (54a).
* **Certain (text)**: Rambam, Hilchot Beit HaBechirah 4:1 - "a stone was in the WEST of the Kodesh HaKodashim on which the Aron was
  placed, and before it the jar of manna and Aharon's staff"; Shlomo prepared a hiding place below. Note for the book review: the
  build centres the Aron on the Kodesh clear floor (-6700..-5700, centre -6200: `vessels-review/aron-placement-spec.json`, authored);
  Rambam's "in the west" is not modelled and should be checked against the user's book before any move.
* **Certain (source), disputed (identification)**: Radbaz, Responsa 2:691 identifies the rock under the Dome with the Even HaShetiyah;
  followed by R. Y. M. Tucazinsky (Ir HaKodesh VeHaMikdash), R. Shlomo Goren, and archaeologically by L. Ritmeyer.
* **Disputed - dissenters named fairly**: (i) the rock as the site of the ALTAR rather than the Aron - one of the four positions listed
  in the modern literature (Wikipedia, Foundation Stone); it leans on Rambam 2:2 (altar site = Akeidah site) and the Muslim/medieval
  Christian association of the Sakhra with Avraham's sacrifice; named rabbinic proponents were not verified here; (ii) Asher Kaufman -
  Temple north of the Dome, Even HaShetiyah under the Dome of the Spirits/Tablets (OSM 291836681 at (-230, -165) amot = (-10,640,
  -8,270) cm, i.e. 43 m NW of the Dome centroid); (iii) Tuvia Sagiv - Temple south, near the El-Kas fountain; (iv) a view attributed
  to the Arizal and Maharsha that the Temple stood between the Dome and the Western Wall (as cited by Wikipedia; not checked in the
  primary sources).
* **Authored**: the OSM polygon centroid as the dome centre; the 4.2 m uncertainty budget; the 743.7 m summit figure taken from a
  19th-century survey via a secondary site; the re-pivot choice; keeping the vertical datum.

Web sources consulted: Wikipedia "Foundation Stone" (dimensions, Yoma/Rambam/Radbaz, four positions, Kaufman/Sagiv);
biblearchaeology.org "The Ark of the Covenant: Where Has It Been?" (Ritmeyer's depression 4 ft 4 in x 2 ft 7 in);
lifeintheholyland.com "Dome of the Rock, Exterior" (2,440 ft summit); Wikipedia "Temple Mount" (~740 m).

## 7. Dry-run command (no mutation; does NOT run while another native job holds the editor)

```
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "C:\Mikdash\Working-5.8\MikdashCourtyardV3\MikdashCourtyardV3.uproject" -run=pythonscript -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_aron_alignment.py" -unattended -nullrhi -AronAlignTarget=Candidate48 -AronAlignDryRun -abslog="C:/Mikdash/Working-5.8/Release-AronAlignment-DryRun-01.log"
```

Apply is `-AronAlignApply` (default OFF; Main50 additionally needs `-AronAlignAllowNotRecommended`). Offline preview without Unreal:
`python Scripts/release_aron_alignment.py --target Candidate48 --dry-run` (classifies the read-only inventory: 2885 re-spawn,
12 modify+move, 4858 context, 10 global, 2 frame, 0 unclassified). Not run against any map; no editor launched; nothing committed.
