# Long rod crossing K2 and R1: diagnostic branch, not an identified mesh

15 September 2026. No native test or production change performed in this investigation.

The inspected images are cp24
`cfafter-cp24-K2-kotel-upper-deck-facing-jewish-quarter.png` and roofruntime02
`roofruntime02-R1-roof-overview-modern.png` / `roofruntime02-R1-roof-overview-yechezkel.png`,
all in `SourceAssets/visual-review/city-facade`.
They contain a long narrow dark object crossing much of the left/central view. Both R1 states
show it at broadly similar screen positions. The capture receipt requests the same R1 camera,
`-33500 0 6500 -25 180 0`, in separate game launches. The K2 request is
`-20732 19230 -814 6 175 0`.

This proves the object occurs in multiple captures, including both precinct states. It does
**not** prove that it is attached to the camera, that all the images show the same mesh, or
that a legacy tree is its source. Similar screen positions from repeated camera coordinates
cannot establish camera-relative motion.

## Concrete code and asset evidence

- `Content/Python/gameplay.py` creates BP_MikdashWalker as a child of the migrated first-person
  character and deliberately inherits its camera/input unchanged. The current walker asset's
  embedded parent reference is `/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter`.
- The current parent Blueprint contains references/names for `SKM_Manny_Simple`, `FirstPersonMesh`,
  `ABP_FP_Copy`, `FirstPersonPrimitiveType::FirstPerson`,
  `FirstPersonPrimitiveType::WorldSpaceRepresentation`, `bOnlyOwnerSee`, `bOwnerNoSee`,
  `bEnableFirstPersonFieldOfView`, and `bEnableFirstPersonScale`. These were read from asset
  name/reference strings; **their current boolean/numeric values were not decoded or read back**.
- `MikdashPhotoMode.cpp`, `AMikdashPhotoCamera` constructor, creates only a CameraComponent;
  it does not explicitly create a static/skeletal rod mesh. `UMikdashPhotoMode::Enter`
  (approximately lines 359-415) gets the current view, spawns a separate photo camera,
  copies ordinary field of view, switches view target and pauses the game. It does not
  explicitly hide the possessed pawn or its mesh components, and does not copy the source
  camera's first-person FOV/scale options.
- Installed UE5.8 `PrimitiveSceneProxy.cpp` around lines 1582-1592 tests owner visibility
  against the view actor. The changed view target and inherited first-person components
  therefore deserve an actual rendering test. Their visibility outcome cannot be inferred
  solely from Blueprint property names.
- `MikdashDovePawn.cpp` creates a separate bird with static mesh body/wing components and
  a following camera. `MikdashPlayerController::ToggleDoveFlight` is the explicit possession
  path. R1's capture recipe uses Ghost/BugItGo/photo mode, not a recorded dove toggle;
  no evidence in these receipts identifies the bird as the obstruction.

## The correctly imported frozen trunks are a poor match

The frozen `instances-manifest.json` at
`C:/Mikdash/Mikdash-Windows-Transfer/Workspace/output/cloud-unreal-v3/context-review`
has SHA256 `5b80379b80b891dc20809a025bb69a15c5219123d23f6a25e0bc1de81199ec33`.
Its `SM_JerusalemInstance_Tree_trunks` group contains 4,409 instances. Prototype bounds are
(-18.07005,-15.3713,-25) to (18.07005,19,25) cm; the scaled maximum local extent is 200 cm.
The source recipe in `mikdash-walkthrough/lib/mikdash/jerusalem.ts` lines 87-89 likewise
creates the small five-sided trunk cylinder and scales its long axis by four.

For each of the 4,409 frozen transforms, the investigation enclosed all eight scaled
prototype-bound corners in a sphere centred at the instance translation. Its radius is
103.38049 cm. Rotation cannot enlarge that sphere. With centre distance `d` and radius `r`,
the conservative angular diameter is `2 * asin(r / d)` when the camera is outside it.
The largest bound among **all** frozen trunks is:

- K2: **1.34048 degrees**, source instance 1171; centre distance **8837.707 cm**.
- R1: **1.94485 degrees**, source instance 3820; centre distance **6091.521 cm**.

These bounds do not resemble the long object spanning much of the frame at the ordinary
capture FOV. This calculation assumes the saved native prototype and instance transforms
still match the frozen import. It cannot rule out a malformed native mesh, changed transforms,
another asset family, or several collinear objects. The earlier AGENTS note attributing
dark sticks in grove frames to legacy vegetation is not proof about this different object.

## Smallest packaged discrimination, no source build required

Use the same R1 camera/exposure and wait for the game to settle as in the existing capture
recipe. Read the prior console-variable value first and restore it after each branch.

1. Capture baseline. Execute `ShowFlag.SkeletalMeshes 0` and recapture. Restore the prior
   value (`2` is the normal no-override default). If the rod disappears, narrow the next
   probe to the possessed pawn's skeletal components; this flag alone also hides residents,
   so it does not establish pawn identity.
2. If it remains, restore skeletal rendering and execute `ShowFlag.InstancedStaticMeshes 0`.
   Recapture, then restore the prior value. This isolates the broad ISM/HISM branch, including
   legacy trunks, while also affecting other instanced details. A disappearance is not an
   instruction to remove all vegetation.
3. Once the renderer family is known, use a bounded probe that records the possessed pawn,
   view target, camera transform, primitive mesh paths, first-person type, attachment,
   owner-visibility flags and bounds. Hide one candidate component at a time, preserve its
   prior state and restore it immediately after the paired frame. If the first branch points
   to the walker, test the walker's components before searching city geometry.

Both renderer flags are present and always accessible in installed UE5.8
`Engine/Source/Runtime/Engine/Public/ShowFlagsValues.inl` (InstancedStaticMeshes around 187,
SkeletalMeshes around 207). ShowFlag override semantics are 0=force off, 1=force on,
2=no override. **Use 2, not 1, to return an initially default flag to normal behavior.**

A collision trace alone cannot identify this object reliably: the decorative importer
sets instances NoCollision, while first-person rendering may alter apparent position.
Do not broaden the production hide set based on a missed trace.

If needed to establish camera-relative behavior separately, pause in photo mode, record
the pawn and camera transforms, and translate only the photo camera sideways by a known
small amount without rotating it. Compare parallax and log actor transforms. Two pictures
from different teleported pawns are insufficient for that conclusion.

No production fix is selected. A pawn-only photo-mode visibility change may be appropriate
if a component-level A/B confirms it, but exact prior visibility, cancellation, photo exit
and EndPlay restoration would then be required. That is a candidate design, not a verified
cause or an authorization to suppress unrelated meshes.
