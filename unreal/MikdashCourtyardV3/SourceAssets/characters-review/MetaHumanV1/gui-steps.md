# MetaHuman V1 — what needs the user's clicks in UE 5.8.2

> ### SUPERSEDING UPDATE — 2026-09-09
>
> **Steps 1, 2 and the summary table below are STALE. Read this box first.**
>
> * **MetaHuman Creator Core Data IS installed.** `Engine/Plugins/MetaHuman/MetaHumanCharacter/Content/Optional`
>   exists with 1,816 files / 5.8 GB, including `Presets` (29), `Grooms` (95 wardrobe items:
>   **16 beards**, 16 mustaches, 38 hair, 18 eyebrows, 6 eyelashes, 1 peachfuzz), `Clothing`,
>   `BodyTextures`, `TextureSynthesis` and `Animation`. Step 1 below is DONE; ignore it.
> * **`MetaHumanCrowd` was deliberately removed** from the .uproject. Step 2's plugin list is stale;
>   the two enabled are `MetaHumanSDK` and `MetaHumanCharacter`. The rebuild it demands is still real.
> * **The cloud is no longer on the critical path.** See "Step 0" immediately below.
> * The garment situation is worse than step 9 implies, and it is now measured: see
>   "What actually ships as clothing".

---

## Step 0 (NEW, and it replaces steps 3, 5, 6 and 8) — build from the shipped presets, no cloud at all

The 29 assets under `/MetaHumanCharacter/Optional/Presets` **are themselves `UMetaHumanCharacter`
assets, and they ship already auto-rigged and already carrying high-resolution textures.** Each
package serialises `bHasHighResolutionTextures` and `SynthesizedFaceTexturesInfo`; that flag
defaults to `false` (`MetaHumanCharacter.h:402`) and UE only serialises non-default tagged
properties, so its presence means `true`. They are 8.9–10.0 MB each on disk, which is that
texture payload.

`CanBuildMetaHuman()` only needs `GetRiggingState()==Rigged` **and** `HasHighResolutionTextures()`
(`MetaHumanCharacterEditorSubsystem.cpp:2238-2274`). A duplicated preset satisfies both. **So the
auto-rig and texture-download cloud calls — the entire reason a sign-in was needed — can be
skipped.**

`Scripts/release_metahuman_build.py` does this, headless, one character per invocation:

```
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" ^
  "C:\Mikdash\Working-5.8\MikdashCourtyardV3\MikdashCourtyardV3.uproject" ^
  -run=pythonscript ^
  -script="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_metahuman_build.py" ^
  -MetaHumanBuildRun -unattended -nullrhi ^
  -NoMetaHumanAccountPortalLoginFallback ^
  -abslog="C:/Mikdash/Working-5.8/Release-MetaHumanBuild-01.log"
```

Re-run the same line once per character; `build-progress.json` decides what is next. The script
**reads `has_high_resolution_textures` and `can_build_meta_human` back and refuses to build**
rather than trusting the inference above, so if the presets turn out not to be pre-textured the
receipt says so per character instead of quietly calling a cloud service.

**Never omit `-NoMetaHumanAccountPortalLoginFallback`.** There is no `FApp::IsUnattended()` or
`IsRunningCommandlet()` guard anywhere in the MetaHuman auth path, so a headless run that does
touch a service will still try to raise the EOS account-portal window and block on something
nobody can see. That switch (`MetaHumanCloudAuthentication.cpp:262`) makes it fail loudly instead.

## If the cloud is ever needed — the one-time sign-in, exactly

You are **not** signed in. Checked, not assumed: the Windows Credential Manager holds no
Epic/EOS/MetaHuman entry, `HKCU\Software\Epic Games\EOS\MainService` is empty, and no
`EOS_Auth_Login` / `PersistentAuth` / `AccountPortal` line appears anywhere in the editor logs —
the editor has never once attempted a MetaHuman login. Your Epic Games **Launcher** is signed in,
but that does not help: `EOSSDKManager.cpp:503-510` disables integrated-platform auth under
`IsRunningCommandlet()`, so a commandlet cannot borrow the Launcher session.

The mechanism is the **EOS SDK** (`EOS_Auth_Login`), not a browser login flow. It tries
`EOS_LCT_PersistentAuth` first and escalates to `EOS_LCT_AccountPortal` — a UI inside the closed
EOS SDK — when there is no stored token. A headless commandlet cannot complete that. **So yes: if
the cloud route is ever needed, one GUI sign-in is genuinely unavoidable.** Once per Windows user,
because the EOS SDK then keeps a refresh token in that user's Windows Credential Manager.

1. Launch the **full editor** (`UnrealEditor.exe`, not `-Cmd`) and open this project.
2. **Content Browser** → `/Game/MetaHumans/Source` → double-click any `UMetaHumanCharacter`.
3. Top toolbar → **MetaHuman Character** → **Create Joints Only Rig**.
   *Not* **Create Full Rig**: the toolkit refuses a blend-shape auto-rig below 10 GiB free memory,
   and this machine has 16 GB total.
4. The EOS account-portal sign-in appears. Complete it with your Epic account.
5. Toolbar → **Authentication Menu**. It must now read *"&lt;name&gt; (ID …) is logged in"*.
   Before sign-in it reads *"No user logged in, please autorig to trigger log-in flow"* —
   **there is no separate Sign In button; attempting an auto-rig IS the sign-in trigger.**
6. From then on, headless runs work as the same Windows user.

**Do not trust `UMetaHumanIdentity::IsLoggedInToService()`** — it is a dead stub that
unconditionally returns `true` (`MetaHumanIdentity.cpp:488-494`). There is no honest
Python-reachable login probe in 5.8.

## What actually ships as clothing — one T-shirt, and that is all

A search of the entire MetaHuman plugin tree for a non-groom `WI_*` wardrobe item returns
**exactly one hit: `WI_DefaultGarment`**, and it is a **modern crewneck T-shirt and shorts**
(meshes `DG_bodyShapeB_LOD3_shirt` / `_shorts`, materials under `Clothing/Common/Materials/Crewneckt`).
Searching case-insensitively for robe / tunic / gown / cloak / coat across every MetaHuman plugin
returns only UI icons. **No period garment ships, at any quality, in any pipeline.**

**Every one of the 29 presets selects `WI_DefaultGarment`.** A duplicated preset that is not
cleared walks the courtyard in streetwear. `release_metahuman_build.py` clears the `Outfits`
slot first, unconditionally, before anything else:

```python
character.internal_collection.default_instance.set_single_slot_selection(
    slot_name="Outfits", item_key=unreal.MetaHumanPaletteItemKey())
```

So step 9 below still stands as the real clothing work, with one addition: besides
`ChaosOutfitAsset` (route A) and the skeletal-mesh pipeline (route B), `Config/Editor.ini`
declares a wardrobe slot `SlotName="SkeletalMesh"` (shown as **Skeletal Clothing**) with
`ClassesToFilter=("/Script/Engine.SkeletalMesh")`, which takes any skinned robe mesh through the
same `try_add_item_from_wardrobe_item` / `try_add_slot_selection` calls with no Chaos authoring.

## Beards: 16 ship, and three presets already wear the longest one

`WI_Beard_L_Full` + `WI_Mustache_L_Full` is the fullest pairing available. Presets **Aoi**,
**Isaiah** and **Omari** ship with that combination already selected; **Walter** ships a wavy
goatee and mustache, a distinctly mature styling. Those four are the roster's bearded men.

**Age and gender are recorded NOWHERE** in the preset assets — not in source, not in metadata.
Every age/gender claim in the roster is a guess from the preset's given name, except where the
preset's own pre-selected facial hair proves the figure is bearded. **Confirm by eye.**

---

## Step L (NEW) — the locomotion Animation Blueprint. This is the stilting cure, and it is a GUI job.

MetaHuman fixes skin, eyes, grooms and the facial rig. **It does not fix how anyone walks.** The
residents are driven by `USkeletalMeshComponent::PlayAnimation` in `AnimationSingleNode` mode,
which **cannot cross-fade, cannot foot-IK and cannot head-look-at** — those are anim-graph nodes,
and 5.8 exposes no way to author an anim graph from Python. Everything reachable from C++ has been
done in `MikdashResidentPopulation` / `MikdashResidentCharacter`; the rest is this file.

**Easy to miss: Epic ships a full locomotion set with the Core Data.**
`Optional/Animation/UEFNAnimPreset/Locomotion/` holds **25 AnimSequences on the MetaHuman
skeleton** — `AS_MH_Neutral_Stand_Idle_Loop`, twelve Walk clips and twelve Run clips, each family
carrying `Loop_{F,B,LR,RL}` plus **foot-phased `Start_*` and `Stop_*` clips**
(`Start_F_Rfoot`, `Stop_F_Lfoot`, …). Those start/stop clips are exactly what removes the
"snaps into full stride" read. They are referenced **only** by the UEFN export pipeline
(`MetaHumanDefaultEditorPipelineUEFN.cpp:806-896`), so nothing in the normal build wires them up —
but they are plain `AS_` sequences and can be used directly.

Author **one** `ABP_MikdashLocomotion` and set the resident mesh to
`EAnimationMode::AnimationBlueprint`:

1. Content Browser → **Add** → **Animation** → **Animation Blueprint**; parent `AnimInstance`,
   skeleton = the target skeleton (one per PilgrimRigV3 variant, or the MetaHuman skeleton).
2. **Event Blueprint Update Animation** → `Try Get Pawn Owner` → cast to
   `MikdashResidentCharacter` → read **`Get Ground Speed`** and **`Get Cadence Bias`**
   (both already exist as `BlueprintPure` for exactly this purpose) into two float variables.
3. **BlendSpace 1D** on `Speed` (0 → idle, clip ground speed → walk), used in the AnimGraph in
   place of the two hard-switched sequences. This alone removes the idle↔walk pop.
4. **State machine** Idle → Start → Loop → Stop, using the foot-phased `Start_*` / `Stop_*` clips
   where the skeleton has them.
5. **Foot IK**: two-bone IK on `foot_l` / `foot_r` driven by a downward line trace, or a Control
   Rig node in a **post-process AnimBP** on the SkeletalMesh asset (post-process ABPs evaluate
   even in single-node mode — that is how MetaHuman's own `ABP_Face_PostProcess` and
   `ABP_Body_PostProcess` work).
6. **Head look-at**: `Look At` skeletal control on `head`, target = the player camera, clamped
   cone. Nothing in C++ can do this — `USkeletalMeshComponent` in 5.8 exposes no
   `SetBoneRotationByName`.
7. Then change `SetAnimationMode(EAnimationMode::AnimationSingleNode)` to `AnimationBlueprint`
   plus `SetAnimInstanceClass` in `SpawnAuthoredBody`, and delete the `PlayAnimation` /
   `SetPlayRate` block in `Tick`. That is a small, named C++ change.

### The PilgrimRigV3 walk clip is measurably wrong, and no AnimBP hides it

Forward kinematics over the source GLBs (all nine variants, byte-identical motion) gives:

| measured | value | natural target |
|---|---|---|
| walk cycle | 1.200 s (= 100 steps/min cadence) | 100–120 spm — **the cadence is fine** |
| step length | **32.0 cm** = 0.178 × stature | ~0.41 × stature ≈ **73 cm** |
| stride per cycle | 64.0 cm | ~146 cm |
| **implied ground speed** | **53.3 cm/s** | 130–145 cm/s |
| pelvis vertical bob | **0.50 cm** | ~4–5 cm |
| foot lift | 5.0 cm | 10–15 cm |
| stance plant | **none** — both ball tracks are pure counter-phase sinusoids, so no foot is ever stationary | a real stance hold |

The population was driving these bodies at **180 cm/s**, i.e. **3.375× faster than the clip's own
stride**. That is the skating. The C++ now derives each body's pace from the clip instead, which
removes the slide — at the cost that they walk at ~53 cm/s, an amble.

**The real fix is to re-author `A_Pilgrim_Original_Walk` in the PilgrimRigV3 generator** (not a
file this note owns): raise the ball-joint swing amplitude from 0.16 m to ~0.365 m (step 32 →
73 cm), the pelvis bob from 0.5 cm to ~4 cm, the foot lift from 5 cm to ~12 cm, and flatten the
stance half of each foot's curve so the planted foot actually holds still. Keep the 1.200 s cycle.
Then set `WalkClipGroundSpeedCmPerSec` on the body variants to the new measured value (~122 cm/s)
— **one number, and every resident walks at a natural pace with no other edit.**

---

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
