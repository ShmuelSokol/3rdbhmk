# Surface routing V1

Portable adapter: `Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashSurfaceAudioRouting.h`.
No controller, asset, map or frozen sound V1 file was changed. Run `run_tests.cmd`
from this directory; it compiles the actual production header with installed MSVC
2019 in C++14 mode, /W4 /WX. This does not establish Unreal compiler acceptance.

## Evidence and behavior

- Existing controller uses actual CurrentFloor mesh plus walking cadence. Retain
  those requirements. Terrain selects existing SoftSteps; Architecture, Streets
  and Buildings select existing StoneSteps. These legacy family assignments are
  illustrative, not surveyed material claims. They require a blocking walkable hit.
- `SourceAssets/FutureMountV1/native-platform-existing-verification-03.json`
  identifies the exact saved top mesh package
  `/Game/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Surface`, BlockAll,
  complex-as-simple. Route this exact surface to existing RecordedStone.
  Its sibling skirt stays unknown/silent. No blanket FutureMount prefix rule.
- `Scripts/build_sanctuary_finishes.py` assigns finishes to original Architecture
  meshes, so existing measured indoor floors keep their hard-surface bank.
  Surface selection does not determine interior acoustics. Palm relief meshes in
  MaterialReview are decoration and stay silent without explicit floor registration.
- `Scripts/create_mount_access.py` authors stair, apron, plaza and parapet source
  meshes but has no native import destination. Do not guess a /Game path or match
  object names globally. After native integration, add exact package registrations
  for checked WALKABLE stairs/apron/infill using RecordedStone. Do not register
  parapets. Held review-only plaza/apron proposals are not already accepted floors.
- `Scripts/create_arrival_assets.py` produces bus material meshes, not accepted
  walkable paving. They stay silent. Future cobblestone and station paving need
  their own verified paths and floor-contact checks.

The adapter accepts canonical package paths or Unreal `package.object` strings
only when object name equals the package basename. Null, malformed, traversal,
directory-only, near-prefix and unknown paths stay silent. Explicit registrations
override legacy/default behavior; Silent is a valid exclusion. Conflicting duplicate
registrations fail silent. Registry storage/lifetime belongs to caller.

## Proposed controller patch (not applied)

Add `#include "MikdashSurfaceAudioRouting.h"`. After obtaining `Floor` and
`FloorAsset` in UpdateFootsteps, replace only the current prefix-selection block:

```cpp
const FFindFloorResult& Hit = WalkingCharacter->GetCharacterMovement()->CurrentFloor;
const auto Bank = MikdashSurfaceAudio::Route(
    *FloorAsset,
    WalkingCharacter->GetCharacterMovement()->IsMovingOnGround(),
    Hit.bBlockingHit && Hit.IsWalkableFloor());
if (Bank == MikdashSurfaceAudio::Bank::Silent) return;
const bool SoftGround = Bank == MikdashSurfaceAudio::Bank::RecordedSoft;
const TArray<TObjectPtr<USoundBase>>& Samples = SoftGround ? SoftSteps : StoneSteps;
```

The existing Samples declaration is replaced, not duplicated. Retain variation,
mute, cadence and logging below. The header uses wchar_t, compatible with the
current Windows TCHAR build; other-platform TCHAR representations need a tested
conversion before reuse. No plugin Build.cs changes are needed for standard C++.

For later access import, pass an array of `Registration` and its count to Route.
Each entry must record the exact package, source receipt, verified blocking walkable
contact and bank. Do not paste the fictional /Game/Test fixture from tests into
production. This router does not implement spatial playback: preserve current
player playback until audition; use frozen V1 mono recordings for a separate NPC
spatial adapter after import. It never starts audio itself.

## Interior source follow-up

[1800's Church Room Tone by composingatnight](https://freesound.org/people/composingatnight/sounds/697579/)
was checked at the publisher on 2026-09-07. It is marked CC0 and describes a room
without air conditioning, 61.354 s, mono 48 kHz, lossy M4A at 67 kbps. The original
download requires login; no authenticated download session was provided. Nothing
was downloaded or accepted by audition. Its building sounds and recording noise
may still conflict with the intended quiet interior. It is not Temple acoustic
evidence. Keep the clean interior ambience gap open; no synthesized noise supplied.

## Integration gates

Compile the plugin on supported Unreal toolchain, test original terrain and stone,
new platform, stair ascent/descent after explicit registration, blocked contact,
falling, standing, unknown prop, interior floor and mute/pause. Verify no extra
step when changing surface. Native audition and packaged runtime remain pending.
