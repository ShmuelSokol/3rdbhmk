# Getting real-looking people into the courtyard

You said: *"I need the people to look like real people. Not balloons"*, and you want
**lots of people taking pictures**.

This is an honest comparison of the three routes that actually exist for this
project, with what each costs in effort, licence and hardware — and what is
blocked on **you** because an agent cannot log into your accounts.

**Status right now:** the figures in the outer court are `PilgrimRigV2` — an
original 27-joint rig, 29,336 triangles, no facial detail, no cloth folds, fat
cylindrical sleeves. You are right that they read as balloons. Route 3 below has
already been done tonight and is sitting in this folder for you to look at.

---

## The short answer

**Primary recommendation: MetaHuman (route 1) for the dozen figures that get
close to the camera.** It is free with Unreal, it is by far the most realistic
thing available, and UE 5.8 shipped a MetaHuman Crowd system built for exactly
this scale. It needs about twenty minutes of your time to sign in and enable a
plugin; nothing else in the project changes.

**Fallback, already built: the improved original rig (route 3), `PilgrimRigV3`.**
Nine variants, 13k–19k triangles each, real shoulders, tapered limbs, a sculpted
head and cloth folds modelled as geometry — plus a camera visitor and a phone
visitor with new "taking a picture" clips. No login, no third-party licence, no
attribution, and it drops straight onto the existing skeleton. Use it for the
whole crowd now, and for the distant crowd permanently even if you adopt
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

## Route 3 — improve our own rig procedurally  ✅ done tonight

No login, no third party, no attribution, no licence risk, and it keeps the
existing skeleton so the Idle and Walk clips you already imported keep working.

**Delivered:** `Scripts/create_pilgrim_v3.py` and this folder. Nine variants,
each well under the 25,000-triangle budget, with:

- 7.5-head proportions, a defined shoulder shelf, a real waist and ribcage,
  tapered sleeves (V2's were near-cylindrical — that was most of the balloon
  look), visible hands with fingers and shaped feet in sandals;
- a sculpted head: brow ridge, eye sockets, cheekbones, cheek hollows, a real
  nose with nostril wings, ears, jaw taper and chin, with full-beard, short-beard
  and clean-shaven variants;
- **layered garments**: tunic with fitted sleeves and a collar, a wound sash
  whose turns are modelled, an over-mantle draped over both shoulders with a
  trimmed hem and open front, and a draped head cloth / turban / cap / shawl;
- **cloth folds carried in the geometry** — vertical creases that gather under
  the sash and deepen toward the hem, phase-drifting per variant so no two
  figures fold alike. This is the actual answer to "not balloons": V2 was a
  smooth shell, V3 has silhouette.
- **a camera visitor and a phone visitor**, with two new original clips
  (`A_Pilgrim_V3_PhotoCamera`, `A_Pilgrim_V3_PhotoPhone`) that lift the arms so
  the figure is genuinely taking a picture, and static copies baked in that pose
  for the instanced crowd.

**What it is not.** These are stylised-realistic, not photoreal. There is no UV
unwrap, no texture or normal maps, no simulated cloth, no facial animation and no
fingers-level rig. Vertex colours and flat PBR factors only. Next to a MetaHuman
they will still look like game characters — good ones, but game characters.

**Effort: already spent. Money: none. Hardware: none** — 13k–19k triangles is
cheaper than V2's 29k, so the crowd gets *faster*, not slower.

---

## What I would actually do

1. **Ship route 3 now.** It is done, it costs nothing, and it fixes the balloon
   complaint immediately for all 29 figures including the photographers.
2. **Then spend twenty minutes on the Epic login** and build 6–10 MetaHumans for
   the figures that come within a few metres of the camera, at LOD1–LOD3, using
   the 5.8 Crowd/Collection system. Keep V3 for everyone further out.
3. **Skip route 2** unless you want MakeHuman/MPFB2 as a body generator — that
   one is genuinely free, CC0, and needs no account.

---

### Provenance and limits

Every fact about MetaHuman, Mixamo and the CC assets above was gathered from the
vendors' own pages tonight; items that could not be verified by direct fetch are
marked unverified in place. All PilgrimRigV3 geometry, weights and animation
curves were authored in this project — no downloaded, purchased or generated
character was used. The clothing is an artistic pilgrim/visitor design informed
by the Temple Institute reference set; **it is not kohanic vestments and nothing
here is a halachic or historical ruling.** No Unreal process was launched, no map
was edited and nothing was committed while producing this document.
