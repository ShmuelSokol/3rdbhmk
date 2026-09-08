# PilgrimRigV3 guarded native import — helper state (2026-09-08, Fable)

`Scripts/release_pilgrim_v3_review.py` + `release_pilgrim_v3_review.spec.json` wrap the base importer
`Scripts/release_pilgrim_v3.py` (+ spec). Offline `run()` on 2026-09-08 returned
`PREPARED_NOT_NATIVE`, base source check `READY_FOR_NATIVE_IMPORT` with zero problems, rest-pose proof
`REST_POSE_PROVEN_FROM_GLB` for all nine, swap plan `SWAP_PLAN_ONLY_NOTHING_APPLIED`. No native
execution has occurred; no Unreal was launched to prepare this.

## Namespace and layout

Fresh folders under **`/Game/MikdashV3/Characters/PilgrimRigV3/<variant>/`** (coordinator instruction;
the earlier `/CharacterReview/PilgrimRigV3ReviewV1` idea was never created and is retired).
Interchange puts the SkeletalMesh, its new Skeleton, PhysicsAsset and four clips in `SkeletalMeshes/`,
one material instance per garment part in `Materials/` (Skin, Linen, Mantle, Headcloth, Sash, Leather,
Hair, Eyes, Trim, Iris; Youth has no Mantle; visitors add Prop/PropGlass/Denim), and the OBJ crowd copy
goes to `StaticMeshes/SM_<variant>`. Exact names come from readback and are written to the marker.
V2 under `/CharacterReview/PilgrimRigV2` is hashed before and after every batch and never written.

## Rest-pose proof (from GLB bytes, `rest-pose-proof.json`)

Reference: `PilgrimRigV2/PilgrimRigV2.glb` (matches `rig-definition.json` to 2.8e-14 cm). Every one of
the nine variants: 27 joints, names/parents/order identical to V2, identity rest rotations, 10 declared
moved joints (clavicles +2.0 cm, upperarms 0.5, lowerarms 8.235, hands 5.471, balls 2.5), pelvis moved
0.0 cm, whole-arm A-pose drift **0.1217 deg** (limit 0.13, recorded 0.12174). Segment directions moved
more (elbow 4.96, wrist 4.32, toe 3.81 deg) because the segments were lengthened — that is the
proportion change itself, not an error. Clips in every GLB: `A_Pilgrim_Original_Idle` 3.2 s / 97 keys /
9 rotation targets / no translation; `A_Pilgrim_Original_Walk` 1.2 s / 37 keys / 17 rotation targets /
one translation track on **pelvis** (Z 95.55–96.05 cm author frame); `A_Pilgrim_V3_PhotoCamera` 4.0 s /
121 keys / 10 rotation; `A_Pilgrim_V3_PhotoPhone` 3.6 s / 109 keys / 10 rotation. Idle/Walk targets and
timing are identical to the V2 GLB clips. Nothing animates scale; quaternion norm error < 3e-8.

## What the native gate proves before it saves

Skeleton created inside the variant folder (foreign/V2 skeleton refused — no V2 retarget), 27 bone names
in authored order, rest positions within 0.05 cm in the **Interchange frame** (glTF (X,Y,Z) → UE (X,Z,Y),
so authored (x, y, z) cm reads back at (x, −y, z)), four clips on that skeleton, and each clip
rotation-only except pelvis, evaluated with `AnimPoseExtensions.get_reference_pose` and
`AnimationLibrary.get_bone_poses_for_frame`. Missing API = blocked save, never assumed. Two bugs that
would have made the first batch refuse itself were fixed today in `release_pilgrim_v3.py`: the compare
frame (Y-asymmetric bones read back sign-flipped, ~23 cm) and the unregistered-component bone readout
(identity transforms). The receipt also records the **facing** of the imported mesh from ball_r − foot_r:
offline reasoning predicts it faces UE **+Y**, which would mean the population's current mesh yaw +90
points bodies away from travel; the readback decides, PIE confirms.

## Batches, resume, zombie

`run(import_assets=True, variants=[...])` imports exactly those; `run(import_assets=True, batch=N)`
imports the next N not in `review-native-progress.json`. A variant counts as complete only when its
folder is on disk **and** the marker lists its read-back names. A folder without a marker entry is a
preserved partial import: read its `review-native-<stamp>.json` and the base `native-import-<stamp>.json`,
never rerun over it. More than one `UnrealEditor.exe` alive → refuse (zombie makes saves fail silently).
Recommended split: 1 (Man_Standard) + 4 + 4, each a serial native job in a fresh editor with main loaded.

## Scale policy

0.84–1.04 are skeletal-mesh **component** scales (pivot at the feet, relative location stays (0,0,−96)).
Never the Character actor, its 34/96 capsule or the amah scale; never ×0.96. The base spec key
`recommendedActorScale` is a legacy manifest name; `recommendedVisualComponentScale` repeats the value.

## Ceiling

Stylised, faceted figures with flat PBR colour and static cloth; correct at 5–30 m, not film humans.
MetaHuman Core Data is installed; the first cloud auto-rig still needs the editor GUI. Import success
is not visual acceptance: nobody has seen these in the engine.
