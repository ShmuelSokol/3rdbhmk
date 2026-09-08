# Getting real-looking people into the courtyard

You said: *"I need the people to look like real people. Not balloons"*, and you want
**lots of people taking pictures**.

This is an honest comparison of the three routes that actually exist for this
project, with what each costs in effort, licence and hardware — and what is
blocked on **you** because an agent cannot log into your accounts.

**Status right now:** the figures in the outer court are still `PilgrimRigV2` —
an original 27-joint rig, 29,336 triangles, no facial detail, no cloth folds,
fat cylindrical sleeves. Route 3 below has been built and then rebuilt: the
first pass fixed the cloth but kept doll proportions, so it still read as
balloons and you said so again. The second pass measured the figure, found six
proportions wrong by 20–40%, and fixed them against a cited anthropometric
target. What is in this folder now is that second pass. **Nothing has been
imported into the engine yet** — `Scripts/release_pilgrim_v3.py` is the guarded
importer and it has not been run.

---

## The short answer

**Primary recommendation: MetaHuman (route 1) for the dozen figures that get
close to the camera.** It is free with Unreal, it is by far the most realistic
thing available, and UE 5.8 shipped a MetaHuman Crowd system built for exactly
this scale. It needs about twenty minutes of your time to sign in and enable a
plugin; nothing else in the project changes.

**Fallback, already built: the improved original rig (route 3), `PilgrimRigV3`.**
Nine genuinely different people — men and women, four ages, a kohen in white and
two modern visitors in trousers taking pictures — 12k–20k triangles each, built
to real human measurements rather than to eye. No login, no third-party licence,
no attribution, and the clips you already imported stay valid motion. Use it for
the whole crowd now, and for the distant crowd permanently even if you adopt
MetaHumans for the near dozen.

Route 2 (free CC assets) is a distant third — see below for why.

---

## Route 1 — MetaHuman

**What it is.** Epic's photoreal digital human system. Since **UE 5.6** MetaHuman
Creator runs *inside the Unreal Editor* rather than in a browser: you enable the
**MetaHuman Creator plugin** and tick **"MetaHuman Creator Core Data"** in the
Epic Games Launcher install options for the engine version.
<https://dev.epicgames.com/documentation/en-us/metahuman/metahuman-creator-in-unreal-engine>

**Quixel Bridge is deprecated.** Epic's own page carries a "Deprecated" banner and
says everything Bridge served is now on **Fab** (including the Fab tab in the
Launcher and the Fab window in-editor). Do not plan around Bridge.
<https://dev.epicgames.com/documentation/unreal-engine/quixel-bridge-plugin-for-unreal-engine>

**Licence — this got much better in June 2025.** Epic's licence page now states
MetaHuman is *"free to use for anyone making under $1 million USD in revenue"* and
that *"MetaHumans can be used with any engine or creative software."* The old
"UE-only content" restriction was removed, and you may sell MetaHuman characters
and clothing. One restriction remains: you may not use MetaHumans to **train,
build or test AI/ML models**. <https://www.metahuman.com/license>
*Caveat: the legal EULA pages at unrealengine.com refuse automated fetch, so the
exact clause wording is unverified here. Read it in a browser before you ship.*

**BLOCKED ON YOU — an agent cannot do this part.** The engine and the MetaHuman
Core Data install through the **Epic Games Launcher, which requires your Epic
account**, and enabling the plugin prompts an Epic sign-in so characters sync to
your MetaHuman library. I have no way to authenticate as you, and I will not ask
you for credentials. This is a one-time, few-minute step on your machine.

**Cost in geometry** (Epic publishes *vertices*, not triangles —
<https://dev.epicgames.com/documentation/metahuman/platform-support-and-lod-specifications-for-metahumans>):

| | LOD0 | LOD1 | LOD2 | LOD3 | LOD4 | LOD5 | LOD6 | LOD7 |
|---|---|---|---|---|---|---|---|---|
| Head verts | 24,000 | 12,000 | 6,000 | 2,500 | 1,300 | 560 | 270 | 130 |
| Body verts | 30,500 | 7,600 | 3,350 | 1,507 | — | — | — | — |

So a full **LOD0 MetaHuman is roughly 54,500 verts of head + body**, on the order
of 100k+ triangles before hair and clothing — about **five times** one of our V3
pilgrims. Textures go up to **8192 px on PC** (2048 on mobile); the assembly
pipeline picks "UE Cine" (up to 8K) or "UE Optimized" (up to 2K). Epic publishes
no per-character MB figure; community measurements suggest roughly **1 GB of
source textures per stock character** and **3–6 ms of GPU per LOD0 character with
strand hair** on RTX 3070/4070-class hardware — i.e. only a handful of true hero
characters at 60 fps. *(Those community numbers are unverified.)*

**Which LODs make a dozen near-camera characters viable.** Do not run twelve at
LOD0. Practical split for this courtyard:

- **2–4 hero figures** at LOD0–LOD1 (24k/12k head), card hair not strands.
- **The other 8–10 near figures** at LOD2–LOD3 (6k/2.5k head, 3.3k/1.5k body) —
  still far more convincing than anything we can model procedurally.
- **Everyone beyond ~15 m** at LOD4+, or left as PilgrimRigV3 static instances.

**Crowds.** UE/MetaHuman 5.8 added an experimental **MetaHuman Crowd** plugin and
**MetaHuman Collections**, Mass-compatible, with automatic hand-off between
high-fidelity actors and Instanced Skinned Mesh Components by camera distance.
Epic claims *"hundreds of characters on mobile and thousands on higher-end
platforms."* Your 30 is comfortably inside that envelope; the LOD settings on the
Crowd Visualization trait are the primary performance control, and Epic notes you
can retain higher LOD indices "if your crowd appears at closer range than usual"
— which is exactly our case.
<https://dev.epicgames.com/documentation/metahuman/metahuman-crowds-in-unreal-engine>

**The catch nobody mentions.** MetaHuman ships **modern clothing**. There is no
period tunic, mantle, wound sash or head cloth in the library. Whichever route you
pick, the *garments* still have to be modelled — which is most of what route 3
delivered tonight. A realistic hybrid is: MetaHuman heads/bodies for the near
dozen, our V3 garments fitted over them.

**Effort:** ~20 min for you (sign in, install Core Data, enable plugin), then
1–2 days of work to build 6–10 characters, set up the Collection/Mass spawner and
re-fit garments. **Money: none** under $1M revenue. **Hardware: the real cost** —
budget VRAM and GPU time, and expect to tune LODs.

---

## Route 2 — free CC-BY / CC0 rigged humans

Honest verdict: **weakest of the three for this brief.** Almost nothing free and
rigged exists in robed ancient-Middle-Eastern dress, and every asset arrives on a
different skeleton, so each one costs a retarget. Listed so you can judge for
yourself.

**Sketchfab downloads require a free account login** (Sketchfab's own developer
docs: "Downloading models requires users to be authenticated with a Sketchfab
account" — <https://sketchfab.com/developers/download-api>). Sketchfab is now
under Epic/Fab. So this route is *also* blocked on you, for less payoff.

| Asset | Licence | Size | Rigged | Link |
|---|---|---|---|---|
| **Cultist Mage** — theheheo | **CC-BY** (credit required) | 3,154 faces | Yes, 4 anims | <https://sketchfab.com/3d-models/cultist-mage-62101ed201c34481aa401b4270ba8e1a> |
| **Simple monk animated** — Shiroinu25 | **CC-BY** | 1,706 faces | Yes, 1 anim | <https://sketchfab.com/3d-models/simple-monk-animated-5ca360a55c284ff7bb89717f65b6f437> |
| **Arab Man -RIGGED-** — NABEEL619 | CC-BY **but contested** | 12,586 faces | Yes | <https://sketchfab.com/3d-models/arab-man-rigged-0f87f4c0885346ad8f99ba5ccafd153e> |
| **MakeHuman / MPFB2** (Blender add-on) | **CC0 output meshes** | you choose | Yes, generates rigs | <https://extensions.blender.org/add-ons/mpfb/> |
| **Quaternius Universal Base Characters** | Quaternius Asset Licence (not CC0) | ~13k tris, 6 bases | Yes | <https://quaternius.com/packs/universalbasecharacters.html> |

Notes worth reading before you download anything:

- **Cultist Mage** is the best single silhouette match — a hooded full-length
  robe, tiny at 3.1k faces, already animated. **CC-BY: you must credit the author
  in the build's credits.**
- **"Arab Man -RIGGED-"**: the description says it was made in Ready Player Me,
  whose platform terms may mean the uploader could not legally grant CC-BY.
  **Do not ship this without checking.**
- **MakeHuman / MPFB2 is the real answer in this category.** Output meshes are
  **CC0** — no attribution, commercial fine
  (<https://static.makehumancommunity.org/about/license.html>) — it needs **no
  account at all**, it rigs and clothes the figures, and its 2026 release added
  **mass randomization of humans**: thirty varied bodies on one consistent
  skeleton, so a single animation set drives the whole crowd. Robes would still
  be modelled by us. Requires Blender 4.2 LTS+.
- **Quaternius is not CC0** despite what some of its own pack pages say. Its
  licence page defines a bespoke "Quaternius Asset License v1.0" — royalty-free
  commercial use, **no attribution required**, no reselling of raw assets.
  Fine to use; just don't label it CC0. <https://quaternius.com/license.html>
- **Poly Haven has no human characters at all.** Kenney's are CC0 but blocky.
  Blender Studio's Human Base Meshes are CC0 but unrigged and unclothed.

**Mixamo**, for animation rather than characters: still online, needs a **free
Adobe ID**, licence is *"free, with no licensing or royalty fees, for unlimited
commercial or non commercial use"*, **no credit required** — but you **may not
redistribute the raw character/animation files** as a product. It is in
maintenance mode (Fuse CC discontinued, repeated outages), so if you use it,
**download and archive the FBX clips you need** rather than depending on it live.
<https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html>

**Effort:** 1–3 days of retargeting per skeleton family, plus licence bookkeeping.
**Money: none. Hardware: negligible.** **Blocked on you:** Sketchfab and Adobe
logins (MakeHuman/MPFB2 is the exception — no login).

---

## Route 3 — improve our own rig procedurally  ✅ built, rebuilt

No login, no third party, no attribution, no licence risk, and the Idle and Walk
clips you already imported stay valid motion.

### What was actually wrong — the numbers

The first V3 pass was measured off its own shipped mesh
(`SM_V3_Pilgrim_Man_A.obj`). Six things were wrong, and together they are the
whole "balloon" complaint:

| measure | it shipped | a real 179 cm adult | source |
|---|---|---|---|
| head, across x deep | 16.1 x **14.5** cm | 15.5 x **19.4** cm | NASA-STD-3000 50th %ile male |
| fingertip height standing | **81.4** cm (0.454 H) | **67.5** cm (0.377 H) | Drillis & Contini via Winter fig. 4.1 |
| upper arm length | **23.9** cm | **33.3** cm (0.186 H) | as above |
| hand, long x across | **13.0 x 7.4** cm | **19.3 x 8.5** cm | as above |
| foot length | **19.2** cm | **27.2** cm (0.152 H) | as above |
| shoulder under cloth | **40.8** cm | **46.4** cm (0.259 H bideltoid) | as above |
| robe hem circumference | **117** cm | 150+ on a real robe | — |
| stature in head-heights | 7.50 | 7.5 | Loomis canon — this one was right |

Read that list as a sentence: a ball for a head, arms that stop at the waist,
mitten hands, a child's feet, narrow shoulders, and below the sash a smooth cone
with no legs in it. That is a balloon with a face drawn on it. The head-height
ratio being correct is exactly why it looked *nearly* right and still felt wrong.

And two of the nine "variants" — `Man_A` and `Man_A_Bleached` — had **byte
identical vertex data**. They were one figure in two colours, which is the same
mistake the crowd system had already been bitten by.

### What changed

- **Every number above is now built to the anthropometric target and then
  measured back off the finished mesh**, and written into
  `geometry-manifest.json` under `measuredCm`. The build asserts them; it does
  not take the source numbers on trust, which is what let the first pass ship.
- **The head is 15.5 across and 19.3 deep**, with a flattened face plane, a real
  occiput, a jaw that tapers in both axes, and eyes that are a light sclera with
  a small iris set inside the orbit rather than one dark ellipsoid on the cheek.
- **The arm chain is 32.0 + 25.2 cm** and the hand is 19.3 cm with four fingers
  and a thumb authored in the arm's own frame, so the fingertips reach mid-thigh
  and the hand presents its edge to camera the way a hanging hand does.
- **The robe hem is 150 cm around**, it rides up over the instep at the front and
  drags at the back instead of being a level circle, and below the hip the cloth
  is pushed out over each leg and drawn in between them, so there are two
  columns under it instead of one cone.
- **The neck is visible.** It was always modelled at the right 12.2 cm diameter;
  the collar and the head cloth were simply hung over it. Both were raised.
- **The head cloth sits behind the hairline** rather than across the brow, which
  is most of why the earlier faces read as masks.
- **Nine different people, and the export fails if they are not.** Each figure
  is hashed and each silhouette is signed in 26 height bands; two variants must
  differ by at least 0.9 cm of mean outline. The closest pair currently differs
  by 1.9 cm.
- **Every figure stands differently.** A per-variant stance — lean, side-bend,
  twist, head direction, and a different hang and elbow angle on each arm — is
  baked into the static crowd copy. It never touches the pelvis or the leg chain,
  so the feet stay planted. The skeletal meshes are left unposed and share the
  clips.

### The nine

| variant | who | dress | triangles |
|---|---|---|---|
| `V3_Pilgrim_Man_Standard` | man, standard build, short beard | robe, mantle, head cloth | 19,600 |
| `V3_Pilgrim_Man_Heavy` | man, heavy build, full beard | robe, mantle, turban | 20,084 |
| `V3_Pilgrim_Man_Elder` | elderly man, stooped, white beard | robe, mantle, head cloth | 19,804 |
| `V3_Pilgrim_Woman_Young` | woman, young | robe, mantle, long shawl | 19,396 |
| `V3_Pilgrim_Woman_Elder` | elderly woman, heavier, grey | robe, mantle, long shawl | 19,444 |
| `V3_Pilgrim_Youth` | youth | knee-length tunic, cap | 13,476 |
| `V3_Kohen_White` | ordinary kohen | white ketonet, avnet, migba'at, barefoot | 15,796 |
| `V3_Visitor_Camera` | modern visitor, camera at eye | shirt, trousers, cap | 13,440 |
| `V3_Visitor_Phone` | modern visitor, phone raised | shirt, trousers | 12,920 |

Recommended actor scales run 0.84 to 1.04, i.e. roughly 150 cm to 187 cm. **Use
them** — a crowd of identical heights is the next thing that will read as wrong.

### The kohen variant, and what it does not claim

`V3_Kohen_White` follows the garment table in
`SourceAssets/runtime-review/kohen-service/sources.md` section 5, which was
written against the Temple Institute photographs: **ketonet** of white *shesh*,
full length with long sleeves; **avnet**, a long band wound at the waist;
**migba'at**, the ordinary kohen's wound white cap, distinct from the Kohen
Gadol's mitznefet. That file was read, not rewritten.

The Kohen Gadol garments — **me'il, ephod, choshen, mitznefet, tzitz** — are
deliberately **not** modelled. sources.md records live disputes on the ephod
reconstruction (Rambam vs Rashi), on the pomegranate form, on the identification
of several choshen stones, and on whether the Kohen Gadol's avnet is the same as
an ordinary kohen's. Guessing at those in geometry would present a disputed
reading as settled. The bare feet are an authored design choice flagged for
review; sources.md does not cover footwear. **Nothing here is a halachic or
historical ruling and no rabbinic review is claimed.**

### What it is still not

Stylised-realistic, not photoreal. No UV unwrap, no texture or normal maps, no
skin shading model, no simulated cloth, no facial animation, no finger rig, no
hair strands. Vertex colours and flat PBR factors only. **At two metres from
camera a MetaHuman will still be obviously better and these will still read as
game characters — good ones, but game characters.**

**Effort: spent. Money: none. Hardware: none** — 12k–20k triangles is cheaper
than V2's 29,336, so the crowd gets faster, not slower.

## What I would actually do

1. **Import route 3 now.** The assets are authored and verified offline;
   `Scripts/release_pilgrim_v3.py` imports them under guards in resumable
   batches and reads the numbers back. It deliberately places nothing — the
   twenty-four residents belong to another system, and the receipt prints the
   exact hand-off for their owner.
2. **Then spend twenty minutes on the Epic login** and build 6–10 MetaHumans for
   the figures that come within a few metres of the camera, at LOD1–LOD3, using
   the 5.8 Crowd/Collection system. Keep V3 for everyone further out.
3. **Skip route 2** unless you want MakeHuman/MPFB2 as a body generator — that
   one is genuinely free, CC0, and needs no account.

### What only MetaHuman will fix — the honest ceiling

Proportions, silhouette, stance variety and garment fold geometry are solved
here, and they are what fails at 5–30 m, which is where nearly every figure in
this courtyard is. What procedural geometry **cannot** reach, at any triangle
count:

- **Skin.** No subsurface scattering, no pore or wrinkle normal map, no
  micro-detail. Faces are flat-shaded colour. Inside about 3 m this is the first
  thing that reads as fake, and adding triangles does not fix it.
- **Eyes.** No cornea refraction, no wet specular, no caustic, no eyelash. A
  sclera-plus-iris pair of ellipsoids is a good distant read and a poor close one.
- **Hair and beards.** Modelled shells, not strands or cards. They will never
  catch a rim light correctly.
- **Facial animation.** Nothing blinks, speaks or changes expression. A face that
  never moves reads as a mannequin the moment the camera lingers.
- **Hands in close-up.** The fingers are correctly sized and jointed in
  silhouette but rigidly skinned to one hand bone — they cannot grip and they do
  not deform.
- **Cloth motion.** Folds are modelled once and skinned; there is no solve, so a
  robe will not swing independently of the leg inside it.

MetaHuman fixes all six and UE 5.8 ships it. It needs **"MetaHuman Creator Core
Data" installed from the Epic Games Launcher**, which has not been done on this
machine, and the first auto-rig is a **cloud call that must be triggered from the
GUI** while signed in to an Epic account. An agent can do neither. Until then
this is the best that works today, and it is genuinely good in the middle
distance — which is where the crowd actually lives.

---

### Provenance and limits

Every fact about MetaHuman, Mixamo and the CC assets above was gathered from the
vendors' own pages tonight; items that could not be verified by direct fetch are
marked unverified in place. All PilgrimRigV3 geometry, weights and animation
curves were authored in this project — no downloaded, purchased or generated
character was used. The pilgrim and visitor clothing is an artistic design; the
kohen variant follows the garment table in
`SourceAssets/runtime-review/kohen-service/sources.md` section 5 and models only
the ordinary kohen's white garments. **Nothing here is a halachic or historical
ruling and no rabbinic review is claimed.** No Unreal process was launched, no
map was edited, no actor was placed and nothing was committed while producing
this document or the geometry it describes.
