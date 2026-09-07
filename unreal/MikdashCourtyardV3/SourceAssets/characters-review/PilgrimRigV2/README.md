# Pilgrim Rig V2: weighted animated source pilot

This deliverable contains a real skinned GLB with an original 27-joint humanoid
and garment rig, normalized weights on 14,774 vertices, and two sampled animation
clips: `A_Pilgrim_Original_Idle` (3.2 seconds) and `A_Pilgrim_Original_Walk`
(1.2 seconds). It is a technical animation pilot with simplified art and gait,
not a finished cinematic resident. No Unreal process was run by this worker.

## Current files and entrypoints

`PilgrimRigV2.glb` embeds geometry, PBR color materials, joint hierarchy, inverse
bind matrices, four-influence skin data and both animations. It has no external
texture dependencies. Open/import it in a glTF-capable DCC to edit the skin and
animation. Its units are meters, Y up, front +Z; author conversion from V1 is
`(X,Z,-Y)/100`. **Do not apply the legacy OBJ reflection adapter to this GLB.**

The source is `Scripts/rig_pilgrim_character.py`. It reads frozen V1 geometry,
adds lower robe ease and removes hidden upper calf shells that pierced the robe
under knee flexion. V1 itself is unchanged. `--export --previews` reproduces the
source in a fresh version directory and refuses to replace an existing GLB.
The rig file and manifest preserve exact joint positions and current hashes.

The integrating root can load that script as a module and call `run_native()`.
This experimental helper submits GLB to the installed Interchange importer under
`/Game/MikdashV3/CharacterReview/PilgrimRigV2` only. It requires one SkeletalMesh
and two AnimSequence results, then saves only returned assets. It verifies the
GLB hash first and refuses an existing namespace. It never creates actors or
saves a map. Partial failures are preserved in `native-import.json`; inspect them
before any versioned retry. Native import/save/reopen and animation playback
have not yet been executed or accepted by this worker.

## Evidence

- `khronos-validation.json`: official Khronos validator, zero errors/warnings.
- `deformation-checks.json`: normalized weights, bind-pose identity, loop closure,
  finite deformed positions and sampled sandal soles on/above ground.
- `glb-decode-checks.json`: independent GLB buffer decoding and matrix skinning
  evaluates the actual delivered weights, inverse bind matrices and animation
  channels; it matches author quaternion skinning within 0.0001cm at nine keys.
- Four BMPs show actual CPU-skinned idle/contact/passing/opposite poses. The
  passing-pose upper-calf protrusion identified in iteration01 is absent in the
  corrected viewed frame. These are source renders, not native screenshots.
- `mannequin-compatibility.json`: actual native-exported reference hash, 89-bone
  hierarchy, local reference transforms, derived positions and checked chain
  endpoints for a future native IK retargeter.

Run `node SourceAssets/characters-review/PilgrimRigV2/validate-gltf.cjs`, then
`python SourceAssets/characters-review/PilgrimRigV2/verify_asset.py`. The included
official validator package is pinned with upstream URL/hash and its license in
`validation-tools`. The scripts write only their owned validation receipts.

## Mannequin findings and retarget boundary

Correction to V1's provisional description: **SK_Mannequin is the Skeleton asset;
SKM_Manny_Simple is the actual SkeletalMesh.** The native-owning root successfully
exported the latter from a rendered editor. Its earlier NullRHI export asserted
`MeshObject`; a successful rendered export does not make that failed method safe.

The actual reference has 89 bones, five spine segments, two neck segments and
nonidentity local rotations. The original pilot has 27 joints and a different
reference hierarchy. Therefore **do not assign the existing mannequin Skeleton
directly to this mesh, or apply its animation rotations as though identical.**
The measured reference also established anatomical left=positiveX and
right=negativeX while facing-Y; the current V2 labels and weights follow it.

Create a separate native IK Rig for each skeletal mesh, using pelvis retarget
roots and the measured six chain mappings in the compatibility JSON. Align
reference poses and verify shoulder/hip/foot placement before retargeting. The
existing blendspace's binary package references include `MM_Idle` and
`Walk/MF_Unarmed_Walk_Fwd`; reference strings identify candidates, but actual
sample parameters and compatibility must be inspected natively. Retarget copies
into the isolated review namespace. The clips in this GLB are original authored
motions, not copies or successful retargets of those Epic clips.

## Remaining limitations

Hands are rigidly weighted to hand joints; there is no finger/facial animation.
Cloth is ordinary weighted geometry with support joints, not simulated fabric.
Materials remain uniform colors without skin/fabric detail or production UVs.
Mantle shoulder joins still require sculpting. Body geometry hidden by the robe
is omitted, so this mesh cannot be used undressed or with shorter clothing.

The walking clip is in-place with analytical leg trajectories and modest arm
swing. Ground-height tests do not establish planted horizontal contact after a
moving actor is added: speed/contact timing, turns, slope IK and foot sliding
still need native work. No root motion, run, navigation, collision, resident
binding, persistence, LOD/crowd budget, cook or package acceptance is included.
Full-cycle cloth self-intersection and native motion review remain required.

## Provenance and reference handling

Geometry, weights, original rig, animation curves and preview pixels were authored
in this task. No downloaded character, external animation or paid generation was
used. The clothes remain an artistic civilian design, not kohen vestments or a
claim about historical/future dress. This work does not determine ritual status.

`MannequinReference.fbx` and `mannequin-reference-export.json` are **root-owned
local technical references**, excluded from the worker's publishing manifest.
They contain existing Epic project resources, not original pilgrim geometry.
Do not infer redistribution authorization from their presence. The worker
inspected skeleton metadata without copying mannequin mesh or animation into the
GLB. The validator is third-party tooling under its included upstream license.

Primary technical references consulted: [glTF 2.0 specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html),
[Khronos validator](https://github.com/KhronosGroup/glTF-Validator), and
[Epic Interchange import reference](https://dev.epicgames.com/documentation/unreal-engine/interchange-import-reference-in-unreal-engine?lang=en-US).
Installed UE 5.8 GLTFReader.cpp also parses skins and animation channels; this is
capability evidence, not proof that this particular import succeeds.

## Preserved iteration evidence and immediate next task

`rejected-iteration01` preserves a format-valid but visually rejected calf/robe
intersection. `rejected-iteration02` preserves corrected clothing with wrong
anatomical side labels discovered through the measured mannequin export. Current
root-level V2 is the corrected version; never import the rejected GLBs.

Next bounded task: after root native import/readback, produce an isolated native
IK retargeter and tested idle/forward-walk copies from the actual existing
blendspace resources, including full-cycle robe/foot-clearance evidence. That
requires the root to serialize Unreal execution; offline authoring can prepare
the helper and expected chain/pose checks meanwhile.
