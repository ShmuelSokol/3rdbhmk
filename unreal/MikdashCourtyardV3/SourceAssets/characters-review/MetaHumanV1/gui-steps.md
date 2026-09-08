# MetaHuman V1 — what needs the user's clicks in UE 5.8.2

Prepared 2026-09-08. Companion to `Scripts/release_metahuman_enable.py` and
`Scripts/release_metahuman_enable.spec.json`.

Every panel, tool, button and menu name below was read out of the shipped 5.8 plugin source at
`C:\Program Files\Epic Games\UE_5.8\Engine\Plugins\MetaHuman\` (mostly
`MetaHumanCharacterEditorCommands.cpp`, `MetaHumanCharacterEditorToolkit.cpp`, `Config\Editor.ini`
and the asset-definition classes), not from memory or from a different engine version.

Nothing in this file has been executed. It is a plan, not a receipt.

---

## The short version

UE 5.8 ships MetaHuman natively. **No Fab download is needed.** Three things still block a
finished, clothed, bearded character, and only the first one is a hard stop:

| # | Blocker | Who fixes it | Scripted? |
|---|---|---|---|
| 1 | **MetaHuman Creator Core Data** is not installed (no skin synthesis, no presets, **no grooms at all**, no stock clothing) | user, in the Epic Games Launcher | no — launcher GUI |
| 2 | Epic account login for the auto-rig / texture cloud services | user, once, in the editor | no — browser login flow |
| 3 | Period garments (kohen white set, Kohen Gadol eight garments, pilgrim robes) do not exist as meshes yet | modelling work, then step 9 | partly |

Everything else — creating the five characters, setting body shape and gender, varying the faces,
setting skin tone, auto-rigging, downloading textures, and assembling to skeletal meshes — is done
by `Scripts/release_metahuman_enable.py`.

---

## Step 1 — install MetaHuman Creator Core Data (REQUIRED, ~multi-GB)

The plugin checks for `…\MetaHumanCharacter\Content\Optional\` plus `Optional\TextureSynthesis`
(containing at least one `*.ar` file) and `Optional\BodyTextures`
(`FMetaHumanCharacterEditorModule::IsOptionalMetaHumanContentInstalled`). That folder is **absent**
on this machine.

1. Close the Unreal editor.
2. Open the **Epic Games Launcher**.
3. Left rail → **Unreal Engine** → **Library** tab.
4. Find the **5.8.2** engine slot. Click the **dropdown arrow** on its version card.
5. Choose **Options**.
6. In the *Installation Options* dialog, tick **MetaHuman Creator Core Data**.
7. **Apply**, and wait for the download.

Verify with no engine at all:

```
python Scripts\release_metahuman_enable.py
```

The receipt's `optionalCoreData.installed` must flip to `true`.

Until it does, the editor shows a toast reading *"The MetaHuman Creator plugin requires that the
MetaHuman Creator Core Data be installed alongside the Engine. Its functionality will be
significantly limited without it."* with an **Open the Epic Games Launcher** button, and the
MetaHuman Character viewport prints **METAHUMAN CREATOR CORE DATA IS MISSING**.
(`mh.Character.SuppressContentWarnings 1` silences the warning only — it does not restore anything.)

**What you lose without it:** skin texture synthesis (the model is
`Optional/TextureSynthesis/TS-1.3-F_UE_res-1024_nchr-153`; the fallback is a 128×128 placeholder),
the entire preset library, **every groom** — hair, beards, moustaches, eyebrows, eyelashes,
peach fuzz — the stock `WI_*` clothing wardrobe items, the template animations, and the legacy
fixed-compatibility bodies. Two of the five characters are specified as bearded men; **there is no
way to give them beards without this pack.**

---

## Step 2 — rebuild the editor target (coordinator, not the user)

`MikdashCourtyardV3.uproject` now enables `MetaHumanSDK`, `MetaHumanCharacter` and `MetaHumanCrowd`.
All three carry Source modules (7 / 3 / 2), and this project has its own `MikdashRuntime` module, so
the editor **will not open** until the target is rebuilt. See the report for the exact command.

---

## Step 3 — run the scripted pass

Commandlet, serial, with no other native job running:

```
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" ^
  "C:\Mikdash\Working-5.8\MikdashCourtyardV3\MikdashCourtyardV3.uproject" ^
  -run=pythonscript ^
  -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_metahuman_enable.py" ^
  -unattended -nullrhi ^
  -abslog="C:/Mikdash/Working-5.8/Release-MetaHuman-01.log"
```

This creates the five `UMetaHumanCharacter` assets in `/Game/MetaHumans/Source`, sets each one's
body (gender, muscularity, fat, height), jitters each face so they are not identical, sets skin
tone, and writes a receipt to `SourceAssets/characters-review/MetaHumanV1/`.

---

## Step 4 — open one character and confirm it looks like a person

1. **Content Browser** → `/Game/MetaHumans/Source`.
2. Double-click **MH_Kohen_Man_A**.

The **MetaHuman Character Editor** opens. Its left toolbar has six sections, in this order:

`Presets` · `Import` · `Head & Body` · `Materials` · `Hair & Clothing` · `Assembly`

with these tools inside them:

| Section | Tools |
|---|---|
| **Presets** | Edit Presets · Presets Properties · Apply Preset |
| **Import** | From DNA · From Identity · From Template · From Custom Mesh |
| **Head & Body** | Body Params (**Parametric** / **Fixed (Compatibility)** / **Blend**) · Teeth & Eyelashes · Head Transform · Head Sculpt |
| **Materials** | Skin · Eyes · Makeup · Texture & Material Overrides · Teeth & Eyelashes |
| **Hair & Clothing** | Selection · Details · Prepare · Unprepare · Wear · Remove · Accessory Properties |
| **Assembly** | Edit Assembly |

Top toolbar (the `MetaHuman Character` menu): **Create Full Rig** · **Create Joints Only Rig** ·
**Remove Rig** · **Download Texture Sources** · **Refresh Preview** · **Save Thumbnail** ·
**Take High Res Screenshot**, plus the **Authentication Menu** button.

Confirm the body matches the receipt's `bodyConstraintsAfter` in
**Head & Body → Body Params → Parametric** (Global group: `Masculine/Feminine`, `Muscularity`,
`Fat`, `Height`).

---

## Step 5 — sign in to the Epic MetaHuman services (once)

Auto-rigging and high-resolution textures are **Epic cloud calls**
(`FAutoRigServiceRequest`), not local computation.

1. In the open MetaHuman Character Editor, click **Authentication Menu** in the toolbar.
2. If it reports *"No user logged in, please autorig to trigger log-in flow"*, click
   **MetaHuman Character → Create Joints Only Rig**. A browser window opens for the Epic login.
3. Complete the login. The menu should then read *"&lt;name&gt; (ID …) is logged in"*.

**Do this from the GUI, not from a `-unattended` commandlet** — a headless commandlet cannot show
the browser login. Once the account is signed in, the rest can be batched.

Use **Create Joints Only Rig**, not **Create Full Rig**: the editor refuses to auto-rig with blend
shapes below **10 GiB of free memory**, and this machine has 16 GB total.

---

## Step 6 — apply presets to make the faces actually distinct (after step 1)

Without Core Data the script's coefficient jitter is the only face variation available, and it is a
blind perturbation of an undocumented basis. With Core Data installed there is a real preset library
at `/MetaHumanCharacter/Optional/Presets`.

1. Left toolbar → **Presets** → **Edit Presets**.
2. Pick a preset thumbnail. Double-click applies it whole
   (tooltip: *"Double click to apply to MetaHuman."*).
3. Right-click a preset for **Apply Head Only** / **Apply Body Only** — use **Apply Head Only** so
   the scripted body measurements survive.
4. Repeat per character with a different preset. Then re-run step 3 with
   `-MetaHumanNoFaceVariation` if you would rather the script did not jitter on top of a preset.

---

## Step 7 — the older man's skin (Assembly tool, per build)

The Young/Old skin-normal sets ship with the engine
(`/MetaHumanCharacter/Materials/ScalableNormalsParametersMaterials/MI_ScalableNormals_ParamsYoung`
and `…_ParamsOld`, mapped in `Config/DefaultMetaHumanCharacter.ini`). They are chosen by the **build
pipeline**, not stored on the character, and are not exposed as a named Python property in 5.8.

1. Left toolbar → **Assembly** → **Edit Assembly**.
2. In the pipeline details, **Materials** section:
   * tick **Bake Materials**
   * tick **Scalable Normals**
   * set **Scalable Normals Type** = **Old**
3. Build (step 8) with the elder selected.

Because this is a pipeline setting, **build `MH_Elder_Man` in its own pass** with `Old`, and the
other four in a pass with `Young`.

---

## Step 8 — grooms: hair, beards, eyebrows, eyelashes (after step 1)

`Config/Editor.ini` wires six groom slots to six monitored folders:

| Slot (panel label) | Monitored folder | Asset class |
|---|---|---|
| Hair (Grooms) | `/MetaHumanCharacter/Optional/Grooms/Bindings/Hair` | `GroomBindingAsset` |
| Beard (Groom) | `…/Bindings/Beards` | `GroomBindingAsset` |
| Mustache (Groom) | `…/Bindings/Mustaches` | `GroomBindingAsset` |
| Eyebrows (Grooms) | `…/Bindings/Eyebrows` | `GroomBindingAsset` |
| Eyelashes (Groom) | `…/Bindings/Eyelashes` | `GroomBindingAsset` |
| Peachfuzz (Groom) | `…/Bindings/Peachfuzz` | `GroomBindingAsset` |
| Outfit Clothing | `/MetaHumanCharacter/Optional/Clothing` | `ChaosOutfitAsset` |
| Skeletal Clothing | *(none — pick any asset)* | `SkeletalMesh` |

For each of **MH_Kohen_Man_A** and **MH_Kohen_Man_B**:

1. Left toolbar → **Hair & Clothing** → **Selection**.
2. Choose the **Beard (Groom)** category.
3. Click a beard thumbnail, then **Prepare** (it binds the groom to this character's head), then
   **Wear**.
4. **Details** / **Accessory Properties** exposes the groom's instance parameters — `Melanin` is
   the one to darken or grey a beard (Epic's own `example_add_grooms.py` sets exactly that).
5. Repeat with **Hair (Grooms)** and **Eyebrows (Grooms)** for all five characters.

For the elder, set a high `Melanin`-derived grey through **Accessory Properties**.

Once grooms exist on disk, this whole step becomes scriptable —
`try_add_item_from_wardrobe_item("Beard", wardrobe_item)` — because the shipped grooms come as
`UMetaHumanWardrobeItem` assets (`WI_…`). Add them to `spec['wardrobe']['garments']` and run with
`-MetaHumanWardrobe`.

---

## Step 9 — period garments (the real clothing work)

There is **no** kohen / Kohen Gadol / pilgrim garment mesh in this project yet, so this step is
blocked on modelling, not on the engine. When a mesh exists there are two routes, and they differ a
lot:

### Route A — `ChaosOutfitAsset` (recommended for the near-camera dozen)

`UMetaHumanOutfitPipeline` does three things a plain mesh cannot:

* it **resizes the garment to each character's parametric body** (`AvailableSourceSizes` →
  `AutoSelectedSourceSize`), so one tunic fits all five bodies;
* it produces `HeadHiddenFaceMap` and `BodyHiddenFaceMap` so the **skin underneath the garment is
  removed** — no poke-through, and the hidden triangles stop costing anything;
* it runs Chaos cloth simulation, which is what makes a linen tunic read as linen.

1. Model the garment; import it.
2. Content Browser → **Add** → **Chaos Cloth** → **Chaos Outfit Asset** (or open a Chaos Cloth Asset
   and add it to an outfit). Build the panels / wrap the 3D mesh in its Dataflow graph.
3. Content Browser → **Add** → **MetaHuman** → **Advanced** → **MetaHuman Wardrobe Item**.
4. In the wardrobe item's details:
   * **Principal Asset** = your `ChaosOutfitAsset`
   * **Pipeline** = **MetaHuman Outfit Pipeline** (or the shipped Blueprint
     `/MetaHumanCharacter/BuildPipeline/DefaultWardobePipeline/DefaultOutfitPipeline`)
5. Save it into `/Game/MetaHumans/Wardrobe`.
6. Either drag it into **Hair & Clothing → Selection → Outfit Clothing** and **Prepare** → **Wear**,
   or add it to `spec['wardrobe']['garments']` with `"slot": "Outfits"` and run the script with
   `-MetaHumanWardrobe`.

### Route B — plain `SkeletalMesh` (recommended for the far crowd)

Skin the garment to the MetaHuman body skeleton and use the **Skeletal Clothing** slot with
**MetaHuman Default Skeletal Mesh Pipeline**. No sim, no auto-resize, no geometry removal — but
cheap, and it takes per-instance colour through the pipeline's material parameters
`diffuse_color_1` / `diffuse_color_2`, which is how you get many tunic shades from one mesh without
duplicating assets.

Same wardrobe-item recipe as Route A, with **Pipeline** = **MetaHuman Default Skeletal Mesh
Pipeline** and `"slot": "SkeletalMesh"`.

### Note on the eight garments of the Kohen Gadol

The choshen, ephod, me'il with its bells and pomegranates, and the tzitz are **rigid or
semi-rigid accessories**, not cloth. Model them as separate skeletal meshes attached through the
**Skeletal Clothing** slot (or as ordinary attached components on the assembled Blueprint), not as
outfit panels. Keep them out of the cloth solver.

Nothing about the garment shapes, colours or construction is settled by this file; it only says how
a finished mesh reaches a MetaHuman.

---

## Step 10 — assemble, and check what you got

1. Left toolbar → **Assembly** → **Edit Assembly**.
2. Pipeline = **UE Optimized**, Quality = **Medium** (see the cost note in the report).
3. Set the build path to `/Game/MetaHumans` and the common folder to `/Game/MetaHumans/Common`.
4. Build.

Or let the script do it: rerun step 3 adding `-MetaHumanBuild` (after step 5's login has succeeded).

Then, to see one in the level: select the character asset in the Content Browser and use
**Spawn Preview Actor** from its right-click menu. That actor is transient — it is destroyed when
the character editor closes, deliberately, so that no level ever saves a reference to transient
assets. **Do not** save the combined Walkthrough map with a preview actor in it. Placing MetaHumans
in the map for real is a separate, checkpointed placement job, not part of this one.

---

## What is deliberately NOT here

* No map is opened, spawned into or saved by any of this.
* No claim that any character has been visually accepted (AGENTS.md hard rule 7).
* No performance measurement — the numbers in the report are read out of the plugin's own
  configuration, not measured on this GPU.
* These are fictional demonstration figures. They assert nothing about priestly status, purity,
  census, or permission to serve.
