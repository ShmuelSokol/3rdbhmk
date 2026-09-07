# Native sound review V2 — prepared, not executed

Owned entrypoint: `Scripts/build_soundscape_review.py`. Import has no Unreal side
effects. Root prepares and opens a SAVED duplicate map beneath
`/Game/MikdashV3/SoundscapeReview/NativeReviewV2/Maps/` using its normal serial map
workflow. This helper never creates or opens another map and refuses dirty maps,
dirty assets, PIE, wrong project or existing import/actor state.

Call `build(map_path, foot_location_cm=[x,y,z], wind_location_cm=[x,y,z])` with
explicit reviewed outdoor positions in Unreal centimetres. All twelve mono
footstep actors share that floor test position; they are alternate emitters, not
twelve people. The wind position is retained for scene organization but its bed is
non-spatial. The caller must use an outdoor test area: this helper does not detect
rooms, invent floor heights or place sound across a sanctuary interior.

The helper hash-checks frozen recorded inputs, imports 13 nonlooping SoundWaves
under the new namespace and saves only its assets and current owned review map.
All AmbientSound actors have autoplay disabled. Wind starts at component gain .12;
steps .18. Mono steps use overridden spatial attenuation (150 cm inner radius,
1650 cm falloff) and occlusion. These are initial authored mix parameters, pending
listening. Original Courtyard and FutureMount map hashes are recorded before/after.
Failure records partial state and never deletes, retries or reverts shared work.
Root must inspect partial namespace state before another invocation.

## Explicit audition

After root's reopen checks, call `audition(map_path, seconds=120, bank='Stone')`.
Choose `Sand` for soft steps, or `Silent` for wind alone. This is a timed editor
demonstration, not a walking test or runtime surface selection. The exact floor
router in RoutingV1 supplies Stone/Soft/Silent in production; this helper never
pretends a manual bank choice is CurrentFloor evidence. Unknown production floors
must remain silent. No interior ambience asset or synthetic noise is added.

Wind plays its original 256.8-second recording once. Preview duration is capped
at 180 seconds, so no loop or wrap occurs. Smooth gain control points over tens
of seconds range .08–.12. The recorded wind has NOT been accepted by listening.
The previous V1 full-source audition requirement still applies before adoption.
Steps alternate left/right with non-repeating per-side variants and irregular
preview cadence. This is intentionally not animation/contact synchronization.

`stop_audition()` is an explicit emergency stop; callback also auto-stops at its
deadline or when the map/PIE guard changes. Its receipt reports elapsed time and
errors, never a listener verdict. Callback progress depends on editor Slate ticks;
an unresponsive editor can delay the stop. Each footstep is a short nonlooping
sample and wind naturally terminates at the source end. The helper restores wind
gain after preview and does not save audition changes. Root should inspect dirty
state before any subsequent operation, preserving unrelated work.

## API evidence and remaining gates

Inspected installed UE5.8 source:

- Engine/Source/Runtime/Engine/Classes/Components/AudioComponent.h:
  SetSound, SetVolumeMultiplier, SetAttenuationOverrides, bOverrideAttenuation,
  AttenuationOverrides, Play, Stop.
- Engine/Source/Runtime/Engine/Classes/Sound/SoundAttenuation.h:
  reflected bAttenuate, bSpatialize, bEnableOcclusion.
- Engine/Source/Runtime/Engine/Classes/Engine/Attenuation.h:
  reflected AttenuationShapeExtents and FalloffDistance.
- Existing Scripts/import_stone_audio.py establishes the local AssetImportTask,
  SoundWave property, AmbientSound/AudioComponent and asset-save idioms.

Python reflected names and authoring behavior still require a native run. No
native API acceptance is claimed from header inspection or syntax checks.
Native root gates: source-hash pass; receipt status; save/reopen all 13 wave and
actor properties; listen to full source and bounded mix; confirm attenuation,
occlusion and channel balance; stop/mute/pause; production routing/cadence adapter;
fresh package. Quiet interior remains an explicit missing source/adapter area.

Frozen V1 and RoutingV1 files are untouched. Current namespace is a review rig,
not packaged production behavior, and Python callbacks do not ship in the game.
