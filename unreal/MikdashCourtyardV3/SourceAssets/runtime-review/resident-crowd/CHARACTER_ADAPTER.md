# Native resident character adapter

Authored source only. **Unreal Header Tool, native compilation, movement, rendering and packaging remain unverified.** Root owns the next combined native build. No existing controller, Build.cs, map, Content or asset was edited.

New files:

- `Plugins/MikdashRuntime/Source/MikdashRuntime/Public/MikdashResidentCharacter.h`
- `Plugins/MikdashRuntime/Source/MikdashRuntime/Private/MikdashResidentCharacter.cpp`

`AMikdashResidentCharacter` is an actual `ACharacter`, not an actor teleport loop. It uses a capsule (34cm radius / 96cm half-height), CharacterMovement with unpossessed physics enabled, authored 180cm/s walking, 45cm step capability matching the current walker, and movement-directed rotation. No mannequin or substitute mesh is loaded. Assign the other team's dressed skeletal mesh, compatible skeleton and in-place animation blueprint; this class alone is invisible apart from debugging collision.

## Shared model binding and integration

The world owner creates **one** `TSharedPtr<MikdashCrowd::Runtime>` using `MakeShared`, configures its reviewed plans/routes, and passes that same pointer to every body with `BindResident`. A shared pointer avoids a dangling borrowed model at teardown. Binding does not approve access or verify spawn placement; owner must map the current semantic location to a collision-safe feet transform before it starts the clock. The character never advances the shared clock, preventing N characters from multiplying simulation speed.

```cpp
// Illustrative call shape; MapWaypoint and ReviewMappedSegment are owner implementations.
auto Crowd = MakeShared<MikdashCrowd::Runtime>();
// Crowd->Configure(reviewedIdentities, reviewedRoutes), then verify spawn transforms.
Body->BindResident(Crowd, TEXT("stable_id"),
    [Owner](const FString& Id, const FVector& FromFeet, const FVector& ToFeet)
    { return Owner->ReviewMappedSegment(Id, FromFeet, ToFeet); });
// After current goal-specific access approval and a reviewed exact semantic mapping:
Body->RequestReviewedRoute(TEXT("route_id"), OriginFeet, DestinationFeet);
```

The mandatory `FMikdashResidentSegmentReview` callback is the integrating owner's continuous route/access review. It must be read-only, live for the bound body lifetime, reject unknown mappings, check source restrictions for the full capsule path and appropriate goal-specific authorization, and not mutate/reconfigure the model from inside a call. Use a weak UObject capture or other lifetime-safe owner capture in production. A callback that always returns true is not an acceptable production binding. Exterior city routes require separate reviewed policy; do not force the Temple NPC envelope onto city residents.

Route start requires the body grounded at the supplied mapped origin (18cm XY / 12cm Z tolerance). Start and end must project to compatible navmesh within those tolerances. `FindPathToLocationSynchronously` must return valid, non-partial path with matching endpoints. Every native segment is reviewed before acquiring a model reservation. The tick rechecks remaining segments from actual feet positions, uses `AddMovementInput` with CharacterMovement collision and acknowledges arrival only grounded within the destination tolerances. Missing navmesh, partial paths, forbidden segments, ungrounded movement or invalid/stale tokens stop safely. There is no direct-transform or no-navmesh fallback.

Those tolerances are authored safeguards, not native-tested acceptance. The owner should test source 25cm stairs and navmesh feet height against them before adjusting. A 2D target coincident with the body but outside the vertical tolerance stops rather than jumping or teleporting. Path projection follows the character's navigation agent properties. Include correct agent dimensions when building the navmesh.

## Reservation and stop handling

Request succeeds only after `Runtime::Reserve` returns a token. `GetRouteToken()` exposes it to the owner. A failed path, policy revocation, timeout, falling or explicit `RequestResidentStop` stops movement, revokes access and sets `NeedsPassageClearance()`. The reservation remains occupied.

The owner must physically clear the doorway, confirm clearance independently, then call `ConfirmPassageCleared(expectedToken)`. The method verifies matching token, stopped velocity and model acknowledgment, but does not claim to know the doorway's geometry. Calling it just because velocity is zero would be incorrect. Recover the body physically to its last confirmed waypoint before requesting another route, or remove the body safely. The adapter intentionally leaves recovery to the world coordinator; it never teleports a live resident.

EndPlay stops and revokes an active route but does not auto-release occupied capacity. The owner records `(ID, token)` before teardown and acknowledges clearance after collision is removed. Before model Load/Configure, cancel/clear all bodies and callbacks; restore reviewed waypoint transforms and bind/reapprove fresh state. A model load while bodies are mid-route violates this contract.

## Pause and presentation

The adapter stops movement while either the shared model or Unreal world is paused and freezes its skeletal animation flag. It retains path/token for normal resume; it does not consume elapsed wall time. Root's controller/subsystem hook still calls `Crowd.SetPaused` and drives the single simulation clock. Use in-place animations; do not use animation root motion to move around CharacterMovement route validation.

Blueprint read-only accessors expose stable ID, display name, current goal, current working action, state and passage-clearance need. `GetResidentAction` returns an action only while working. Distinct schedules and actions are model data; animation selection, phase variety, interactions and finished visuals remain the integrator's job.

## Dependencies and installed API evidence

Root must add **NavigationSystem** to `MikdashRuntime.Build.cs` private dependencies before the combined compile. No AIController/AI move task is used, so this adapter does not directly require AIModule. Existing Engine dependency covers CharacterMovement and capsule. Public headers do not include NavigationSystem, so a private dependency is sufficient for this implementation.

Installed UE5.8 headers inspected:

- `Engine/Source/Runtime/NavigationSystem/Public/NavigationSystem.h`: `FindPathToLocationSynchronously` line 535; `ProjectPointToNavigation` with agent properties line 712; `GetCurrent(UWorld*)` line 1177.
- `Engine/Source/Runtime/NavigationSystem/Public/NavigationPath.h`: `PathPoints` line 29; `IsPartial` line 74; `IsValid` line 77.
- `Engine/Source/Runtime/Engine/Classes/GameFramework/CharacterMovementComponent.h`: `bRunPhysicsWithNoController` line 502; `GetActorFeetLocation` line 1347.
- `Engine/Source/Runtime/Engine/Classes/GameFramework/NavMovementComponent.h`: `GetNavAgentPropertiesRef` line 151.
- `Engine/Source/Runtime/Engine/Classes/Components/SkeletalMeshComponent.h`: `bPauseAnims` line 849.

This is API inspection, not a compile receipt. Portable header tests separately pass 520 active checks in both debug and optimized builds. Native acceptance still requires UHT/build, valid navmesh, two opposite doorway users, stop/recovery, pause/resume, save/load teardown, stairs, source-access gap rejection, dressed movement/idle visuals and performance. No scene placement or runtime success is claimed.
