# walk-v2 imported into the engine and the residents repointed at it

Generated 2026-09-09 by `Scripts/release_walk_v2.py`. Everything numeric below was read
back off the SAVED asset or the REOPENED map, never off the source GLB. Nothing here is a
visual, PIE, cook or performance acceptance: **nobody has looked at the new walk in a frame.**

## What ran

| step | command | receipt |
|---|---|---|
| 1 | `-WalkV2Import` (first attempt) | `walkv2-import-20260909T233411922402Z.json` |
| 2 | `-WalkV2Import -WalkV2Reimport` (60 fps fix) | `walkv2-import-20260909T233726325326Z.json` |
| 3 | `-WalkV2Apply -WalkV2Target=Candidate48` | `walkv2-apply-Candidate48-20260909T233909161279Z.json` |
| 4 | `-WalkV2Apply -WalkV2Target=Main50` | `walkv2-apply-Main50-20260909T234151803348Z.json` |

Launch recipe, one engine at a time:

```
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"
    "C:\Mikdash\Working-5.8\MikdashCourtyardV3\MikdashCourtyardV3.uproject"
    <map> -ExecutePythonScript="C:/Mikdash/Working-5.8/MikdashCourtyardV3/Scripts/release_walk_v2.py"
    <mode flags> -unattended -nullrhi -NoSplash -abslog=<unique>
```

## The trap this run paid for: Interchange re-bakes bone tracks at 30 Hz

The first import came back **37 keys / 36 frames** — 30 fps — on a source that carries
**73 keys / 72 frames** at 60 fps. `InterchangeGenericAnimationPipeline` inherits the
FBX-era default `bUse30HzToBakeBoneAnimation = true` and resamples every bone track. That
is precisely the linear chording across the heel and toe rockers that the 60 fps export
exists to avoid, so the first import was thrown away (`-WalkV2Reimport` deletes only the
`WalkV2/` folders this script itself created) and re-run with

```
animation_pipeline.use30_hz_to_bake_bone_animation  = False
animation_pipeline.custom_bone_animation_sample_rate = 60
```

The key count is now asserted off the saved asset: an import that does not carry the
source's 73 keys refuses. `snap_to_closest_frame_boundary` does not exist on this build
and was optional.

## Where the new clips live

Animation-only Interchange import bound to each variant's EXISTING Skeleton
(`common_skeletal_meshes_and_animations_properties.skeleton` = the existing asset,
`import_only_animations = True`). No SkeletalMesh and **no Skeleton** was created; the
import refuses if either appears. All four clips travel in each GLB, so Idle / PhotoCamera /
PhotoPhone came along too and are byte-for-byte the same motion as the shipped ones; only
the walk is repointed.

    /Game/MikdashV3/Characters/PilgrimRigV3/<variant>/WalkV2/<variant>A_Pilgrim_Original_Walk

The nine shipped GLBs, the nine imported SkeletalMeshes, the nine Skeletons and the nine
old clips are untouched: 56 pre-existing `.uasset` files plus both `.umap` files were
hashed before and after the import and **none changed**.

## Acceptance 1 and 2: measured off the IMPORTED asset

Method, so it can be argued with. The clip is authored in place, so during stance the
planted foot travels BACKWARD through component space at exactly the ground speed the clip
implies. `AnimPoseExtensions.get_anim_pose_at_time` is sampled at 240 Hz over the whole
cycle; for each foot the longest cyclic run of samples whose `ball_*` height is within
0.2 cm of that foot's lowest point is taken as the plant, its forward (component +Y)
position is least-squares fitted against time, |slope| is the ground speed and the worst
residual is how far the planted foot slides against its own straight line. Step length is
speed x cycle / 2. Component +Y is forward because Interchange maps glTF (X, Y, Z) to UE
(X, Z, Y), which puts `ball_r` at y = +11.5 in the reference pose — the same fact that
gives the population `MeshRelativeYaw = -90`.

The identical routine was run in the same session on the OLD imported clip, so the two
columns are one method, in engine, off saved assets — not a source-file number quoted back.

| read off the imported asset | old clip | new clip | offline claim |
|---|---|---|---|
| sequence length (s) | 1.2000000476837158 | 1.2000000476837158 | 1.200 |
| frames / keys | 36 / 37 | **72 / 73** | 72 / 73 at 60 fps |
| step length (cm) | 36.29 | **71.97** | 71.93 |
| fitted ground speed (cm/s) | 60.48 | **119.95** | 119.89 |
| planted-foot drift (cm) | 4.40 | **0.053** | 0.019 (foot-flat) / 0.786 (incl. rockers) |
| foot lift (cm) | 5.01 | 12.01 | 12.01 |
| pelvis vertical bob (cm) | 0.50 | 3.99 | 3.99 |
| pelvis lateral sway (cm) | 0.00 | 4.40 | 4.4 |
| arm swing, hand fore-aft (cm) | 12.35 | 42.40 | 42.40 |
| ankle fore-aft excursion (cm) | 32.00 | 78.36 | 78.36 |
| mean pelvis height (cm) | 95.8 | 93.4 | 93.4 |

All nine variants read identically, to the digit, on every row. The drift number is the one
place the in-engine figure sits between the two offline ones: this measurement watches the
single `ball_*` joint across the whole contact window (heel rocker, foot flat and toe
rocker together) rather than five sole markers over the flat phase only, so 0.053 cm is
the honest comparable to the offline 0.786 cm, and it is better, not worse. The old clip
reads 4.40 cm against the offline 4.572 cm by the same argument.

The 1.2000000476837158 s is float32 export precision, not a defect: it is the same value
on the old clip, and 1.2 s to seven digits.

## Acceptance 3: variants repointed versus variants present

Counted off the actor after the map was saved AND reopened, on both maps.

| map | population actor | variants present | repointed | already pointed | not imported |
|---|---|---|---|---|---|
| Candidate48 `/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/Walkthrough` | `RELEASE_PeopleV3Population` | 6 | **6** | 0 | 0 |
| Main50 `/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough` | `RELEASE_PeopleV3Population` | 6 | **6** | 0 | 0 |

Six is the whole cast: `resident-swap-plan.json` casts the 24 residents onto six of the nine
variants (Man_Standard, Man_Heavy, Man_Elder, Woman_Young, Woman_Elder, Youth). Kohen_White,
Visitor_Camera and Visitor_Phone are not cast on any resident; their new clips were imported
anyway so the nine stay in step, and they sit unreferenced until something casts them.

## The number that would have broken this if it had been left alone

The per-variant `WalkClipGroundSpeedCmPerSec` **serialized in both maps was 53.33**, not 0
and not the header's new 120.0. `MikdashResidentPopulation.cpp` prefers the per-variant
value over `DefaultWalkClipGroundSpeedCmPerSec` whenever it is in (1.0, 400.0), so the
C++ default going to 120.0 never reached these residents: the saved map kept overriding it
back to 53.33. Repointing the clip alone would therefore have driven a 120 cm/s walk at
53.33 cm/s — the original skating defect, doubled. The apply sets the per-variant value to
120.0 alongside the clip, and the reopened map reads back 120.0 on all six, on both maps.

    V3_Pilgrim_Man_Elder     53.33 -> 120.0     V3_Pilgrim_Woman_Elder   53.33 -> 120.0
    V3_Pilgrim_Man_Heavy     53.33 -> 120.0     V3_Pilgrim_Woman_Young   53.33 -> 120.0
    V3_Pilgrim_Man_Standard  53.33 -> 120.0     V3_Pilgrim_Youth         53.33 -> 120.0

## Acceptance 4: the skeleton is unchanged; this is an animation swap and nothing else

* No Skeleton and no SkeletalMesh was created by the import — the importer is refused if it
  produces either. Only four AnimSequences per variant came out.
* Every new clip binds to the variant's existing Skeleton, compared by object path after
  normalising package-vs-object paths (`_object_path`). This is the exact compare that
  refused the bodies apply on 2026-09-08; that refusal was a real defect in
  `release_resident_bodies_v3.py` and it is already fixed there — the marker stores
  `/Game/…/X` and the native readback returns `/Game/…/X.X`. That queue item is closed.
* Each variant Skeleton's reference-pose bone names were read through
  `AnimPoseExtensions.get_reference_pose` before and after the import and compared as a
  SET, never by authored order (UE stores the reference skeleton depth-first, so the order
  legitimately differs from the generator's). 27 bones, set unchanged, on all nine.
* Read again off the REOPENED map: all six cast variants report 27 bones with the identical
  bone-set digest `31affbc0771998fe`, and every walk clip is on its own mesh's skeleton.
* 56 pre-existing `.uasset` files hashed before and after the import: zero changed.

## Guards on every native run

* Refuses a wrong project directory, a live PIE world, dirty packages, and more than one
  live `UnrealEditor` process (a zombie makes `save_loaded_asset` return False silently).
* Checkpoints before touching anything: the import copies BOTH `.umap` files, each apply
  copies its own, into `C:\Mikdash\Working-5.8\ReviewCheckpoints\WalkV2-*`, hash-verified
  against the file on disk.
* The import hashes 56 pre-existing `.uasset` files and both maps before and after.
* Each apply takes a full scene snapshot (every actor, every component, meshes, materials,
  transforms) before and after and refuses if any actor other than the population changed;
  it also hashes the OTHER map and refuses if its bytes move.
* Save, then reopen the map from disk, then read the array back off the reopened actor and
  compare it to the plan. Nothing is trusted from a setter's return value.

## Still needing a human, and what is NOT verified

* **Nobody has looked at the new walk in a frame.** No PIE, no render, no cook, no frame
  time. Every number above is a static readback off an asset or a map.
* **The Kohen Gadol service body still plays the old walk.** On Candidate48,
  `RELEASE_KohenGadolService_Selected48_V1` (`MikdashServiceActor`) points at
  `…/V3_Pilgrim_Man_Standard/V3_Pilgrim_Man_Standard/SkeletalMeshes/V3_Pilgrim_Man_StandardA_Pilgrim_Original_Walk`;
  on Main50 `RELEASE_KohenGadolService` has no walk clip set at all. That actor belongs to
  another system (`Scripts/configure_service_body_v3.py`) and was deliberately not touched.
  If he walks in the candidate map, he still stilts.
* **The V2 pilot population still plays the V2 walk.** `RELEASE_ResidentPopulation` on both
  maps points at `PilgrimRigV2A_Pilgrim_Original_Walk`. The V2 GLB was not re-exported by
  the re-author run, so there is nothing to repoint it at. Note that
  `DefaultWalkClipGroundSpeedCmPerSec` in the header is now 120.0 while the default (V2)
  body's clip still carries 53.33 — any resident that falls back to the default body would
  be driven at more than twice its clip speed. The bodies-V3 apply put all 24 residents on
  variant bodies, so nothing should be taking that path, but it has not been observed in PIE.
* **`WalkClipNeutralPhase` is stale by 0.035 of a cycle and was NOT changed.** It is 0.25 on
  every variant, measured from the old clip's counter-phase sinusoids crossing at 0.30 s
  and 0.90 s. On the new clip the `ball_r`/`ball_l` fore-aft tracks cross at 0.285 and
  0.785 (measured offline over the GLB at 2400 samples, not in engine). That is 42 ms of
  error in the pose the clip is entered at from Idle — cosmetic, and changing it from a
  source-file measurement rather than an engine readback would be guessing, so it is left
  alone and reported here instead.
* **The Idle -> Walk height step is now larger.** The re-author receipt already flags it:
  Idle holds the pelvis at 98.0 cm, the new walk carries it at 93.4, so the transition
  sinks the hips ~4.6 cm where it used to sink ~2.2. It wants a 0.2-0.3 s cross-blend.
  Nothing in this run addresses that.
* Everything in the re-author receipt's own "Honest limits" still stands: the rig's leg is
  6.9 cm short, there is no weighted toe joint, and 120 cm/s rather than a natural 135 is a
  consequence of that leg length.

## -Revert, actually run, not asserted

`-WalkV2Revert -WalkV2Target=Candidate48` was executed against the applied candidate map
(`walkv2-revert-Candidate48-20260909T234414850410Z.json`). It reads the newest apply
receipt's `bodyVariantsBefore`, refuses if the variant ids on the actor no longer match,
and restores the array exactly. After save and reopen all six read back on the shipped
clips at 53.33 cm/s — the pre-apply state, to the field. The candidate map was then
re-applied so it is left in the intended state.

One honest caveat: revert restores the property VALUES exactly, not the `.umap` bytes.
UE re-serializes on save, so the reverted map hashes differently from the file that
existed before the apply. The byte-exact original is the checkpoint copy under
`ReviewCheckpoints\WalkV2-<target>-<stamp>\BeforeWalkV2.umap`.

## Final state

| map | walk clip | per-variant ground speed | receipt |
|---|---|---|---|
| Candidate48 | `…/<variant>/WalkV2/<variant>A_Pilgrim_Original_Walk` on all 6 | 120.0 on all 6 | `walkv2-apply-Candidate48-20260909T234634735658Z.json` |
| Main50 | `…/<variant>/WalkV2/<variant>A_Pilgrim_Original_Walk` on all 6 | 120.0 on all 6 | `walkv2-apply-Main50-20260909T234151803348Z.json` |

To undo either: `-WalkV2Revert -WalkV2Target=<Candidate48|Main50>` with the same launch line.
