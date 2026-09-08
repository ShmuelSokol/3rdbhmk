# UE 5.8 finding: does a Python-spawned AudioVolume actually get a brush?

**Short answer: yes — but only by accident of the placement path, and the failure mode is
silent.** Verified by reading the UE 5.8 engine source on this machine, line by line, with
no editor launched. Every claim below carries a file and line you can open yourself.

The previous agent stopped mid-investigation at exactly this question and left a guard in
`Scripts/release_soundscape_v2.py` that raises `"The AudioVolume brush has a zero extent"`.
That guard is correct and stays. This document says why it almost never fires, when it
would, and what carries the acoustic zones instead so that the answer stops mattering.

---

## The chain, verified

`unreal.EditorActorSubsystem.spawn_actor_from_class(unreal.AudioVolume, Location)` does
**not** call `UWorld::SpawnActor`. It goes through an actor factory:

| Step | File | Line |
|---|---|---|
| `UEditorActorSubsystem::SpawnActorFromClass` forwards to the internal `SpawnActor` | `Editor/UnrealEd/Private/Subsystems/EditorActorSubsystem.cpp` | 521, 536 |
| which calls `FLevelEditorViewportClient::TryPlacingActorFromObject` | same file | 140 |
| which forwards to `TryPlacingAssetObject` | `Editor/UnrealEd/Private/LevelEditorViewport.cpp` | 406, 419 |
| which, for a `UClass` deriving from `AActor`, calls `GEditor->FindActorFactoryForActorClass(ObjectClass)` | same file | 299–305 |
| `FindActorFactoryForActorClass` returns the first factory whose `NewActorClass` **is exactly** the requested class | `Editor/UnrealEd/Private/EditorEngine.cpp` | 5565 |
| `UEditorEngine::InitEditor` creates, for **every concrete `AVolume` subclass**, one instance of **every** `UActorFactoryVolume` subclass, with `NewFactory->NewActorClass` set to that volume class | `Editor/UnrealEd/Private/EditorEngine.cpp` | 1060–1145 |
| Sorted by `MenuPriority`, ties broken on class name, so `UActorFactoryBoxVolume` sorts ahead of `Cylinder` and `Sphere` | same file | 1119–1145 |
| `UActorFactoryBoxVolume::PostSpawnActor` builds a `UCubeBuilder` and calls `CreateBrushForVolumeActor` | `Editor/UnrealEd/Private/Factories/ActorFactory.cpp` | 1905–1914 |
| `UActorFactory::CreateBrushForVolumeActor` allocates the `UModel`, its `UPolys`, assigns `GetBrushComponent()->Brush`, duplicates the builder onto `BrushBuilder`, calls `Build()` and `FBSPOps::csgPrepMovingBrush` | same file | 1841–1878 |

So an `AAudioVolume` spawned this way gets a real `UModel`, real polys, a real
`UBrushBuilder`, and non-zero bounds.

### And it works in a commandlet

The obvious worry is that `ActorFactories` is editor-UI state that a `-run=pythonscript`
commandlet never builds. It is not. `LaunchEngineLoop.cpp` line 4025–4030 takes the
commandlet path and calls **`GEditor->InitEditor(this)` directly** whenever `GIsEditor` is
set, and the volume-factory registration block above lives inside `InitEditor`
(`EditorEngine.cpp` 961 opens the function; the block is at 1060). `UnrealEditor-Cmd.exe
<project> -run=pythonscript` sets `GIsEditor`, so the factories exist. There is no
`FSlateApplication::IsInitialized()` guard on that block — the two guards in `InitEditor`
that *are* Slate-gated are colour-deficiency preview (line 988) and the widget-reflector
delegates (1042), neither of which touches factories. `-nullrhi` and `-unattended` change
nothing here.

## Where it fails, and why the failure is nasty

`TryPlacingAssetObject` has a fallback at `LevelEditorViewport.cpp` 320–333: if
`FindActorFactoryForActorClass` returns null, it calls `GEditor->AddActor(InLevel,
ObjectClass, ...)` instead. **That path spawns the actor and never builds a brush.** You
get a live `AAudioVolume` with `Brush == nullptr`, zero bounds, and — this is the trap —
no error, no warning, and an actor that looks perfectly normal in the outliner. It simply
never encompasses any point, so the reverb and the interior settings never apply and the
level sounds unchanged.

That happens when:

* the actor factory list has not been built (a non-editor engine, or `GIsEditor` false);
* the volume class is `CLASS_Abstract` or was registered after `InitEditor` without
  `CreateVolumeFactoriesForNewClasses` running (`EditorEngine.cpp` 1392–1420 — that is the
  hot-reload path, so a volume class added by a plugin recompile mid-session);
* someone replaces the call with `UWorld::SpawnActor`, `unreal.GameplayStatics`, or any
  other route that bypasses the factory. **Direct `SpawnActor` on a volume never produces
  a brush.**

**Detection, not faith.** `release_soundscape_v2.py` reads `get_actor_bounds(False)`
immediately after spawning and refuses to continue on a zero extent. That check stays and
its measured numbers go into the receipt, so every run records whether the brush actually
materialised rather than assuming it.

## Two further traps in the same area

1. **Scale, not brush size.** The script sizes the volume with `set_actor_scale3d` and
   re-measures, iterating to convergence. It does not try to author `UCubeBuilder.X/Y/Z`
   and re-`Build()`: `UBrushBuilder::Build` is not a `UFUNCTION`, so Python cannot call it,
   and writing the builder's dimensions without rebuilding changes nothing at all. Scaling
   the actor is the only route available from Python and it does work — `UBrushComponent`
   bounds and its collision body both honour component scale.

2. **`FInteriorSettings` only reach sounds whose `SoundClass` opts in.** An `AAudioVolume`
   applies its ambient-zone settings only to sources whose sound class has
   `bApplyAmbientVolumes` set. A volume that builds perfectly and still does nothing is
   usually this, not the brush.

## What actually carries the zones

Given all of the above, the reverb and occlusion zones in this pass are **not** delegated
to the AudioVolume. They live in `AMikdashSoundscape` as a data table of axis-aligned
boxes with a priority and an inward blend margin, evaluated per update against the
listener, and applied as a per-component dry gain, a low-pass corner and a submix send.
Reasons, in order of weight:

* **It works identically in a packaged build.** No BSP, no brush builder, no editor-only
  code path, nothing that depends on an actor factory having been registered.
* **It can be read back as a number.** `GetCurrentDryGain`, `GetCurrentLowPassHz`,
  `GetCurrentReverbSend` and `GetCurrentZoneLabel` are `BlueprintPure`, so the release
  receipt records what the zone actually does rather than that a volume exists.
* **It is testable offline.** `Plugins/MikdashRuntime/Tests/SoundscapeMathTest.cpp`
  asserts containment, priority layering and continuity across 76,000 checks without an
  engine.
* **Layered blending, which the AudioVolume cannot do.** `AAudioVolume` resolves overlap
  by priority, winner takes all. Writing that test found the same bug in the first version
  of this code: stepping into the outer few centimetres of the Heikhal's blend shell threw
  away the court's own figure and snapped the mix back to fully open before it started
  falling again. `EvaluateZones` now blends lowest priority upward, so the Kodesh reads as
  a change on top of the Heikhal, which reads as a change on top of the court.

The AudioVolume is still placed, because it is the thing an audio person opening the level
will look for, and because `FInteriorSettings` do something the submix path does not
(they duck sources *outside* the volume for a listener inside it, in the audio device
rather than per component). It is a second, agreeing mechanism — not the load-bearing one.
`FMikdashAcousticZone::BackingAudioVolume` records which volume, if any, backs each zone,
and `-SoundscapeNoVolume` skips them entirely with no loss of function.

---

*Verified 2026-09-08 against `C:\Program Files\Epic Games\UE_5.8\Engine\Source` by source
reading only. No editor was launched for this finding, per the constraints of the task
that produced it. The runtime half of the claim — that the spawned volume measures
non-zero — is asserted by the release script at run time and recorded in its receipt;
until a run has happened, the source chain above is evidence and the receipt is proof.*
