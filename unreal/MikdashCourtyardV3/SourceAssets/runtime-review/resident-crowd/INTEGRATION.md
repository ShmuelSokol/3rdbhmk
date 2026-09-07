# Resident crowd runtime handoff

Status: authored, standalone tested; **not embodied, integrated, visually verified, or packaged**.

The production module is `Plugins/MikdashRuntime/Source/MikdashRuntime/Public/ResidentCrowdRuntime.h`. The requested `Source/MikdashCourtyardV3` directory did not exist; the coordinating task explicitly reserved this adjacent plugin header instead. Existing `ResidentSimulation.h`, controller, pawn, Build.cs and Content were not modified.

## What the module provides

`MikdashCrowd::Runtime` owns stable identity IDs, named plans, purpose/action labels, earliest start times, remaining work, confirmed semantic locations, completion timestamps, near/far flags and a paused simulation clock. Plans are configurable, up to 4096 identities and 64 goals each. These are defensive bounds, not measured crowd capacity or a future census. Different plans/start offsets/durations yield distinct actions without randomized synchronized cycles. Test fixtures are authored visitors, not a depiction of actual service choreography. No language model or claim of minds is involved.

`Configure(identities, routes)` validates and replaces a world transactionally. `SetAccess(id, bool)` is a task-specific external review gate, initially false and reset after every completion. `Advance(deltaSeconds)` never completes travel. `Reserve(id, route)` returns a nonzero unique callback token only after schedule, access, origin, destination and resource capacity checks. Opposite routes may share one resource ID so they compete for the same doorway. `Arrive(id, token, destination)` commits only a matching active journey. `AcknowledgeStopped(id, token)` releases a reservation only after the adapter has stopped/removed the body and cleared the passage. Timeouts and access revocation request a stop and **retain capacity** until that acknowledgment. Regranting access cannot resume an unacknowledged stopped journey.

This version reserves one shared resource for a complete route. It does not compute paths or acquire multiple intersection resources. Break complex routes into reviewed intermediate goals or add an independently tested multi-resource coordinator later. Process waiting requests in a rotating FIFO queue; the model intentionally does not fake fairness by reordering caller requests.

## Concrete Unreal adapter contract for the integrating task

Implement an owned world subsystem or actor component, not a second input controller. Keep all model calls and actor operations on the game thread. Proposed members:

```cpp
TSharedPtr<MikdashCrowd::Runtime> Crowd;
TMap<FString, TWeakObjectPtr<ACharacter>> Bodies;
TMap<FString, uint64> MoveTokens;
double FractionalSimulationSeconds = 0.0;
```

1. On begin play, load reviewed `Identity` and `Route` definitions, including stable semantic waypoint IDs mapped to exact native transforms. Fingerprinted configuration must remain identical for snapshot restore. Do not instantiate the test fixture as a reviewed production population.
2. On pause/menu, call `Crowd.SetPaused(true)` and suspend actor path following and animation clocks. Accumulate only unpaused simulation delta, carry fractional seconds locally, and call `Advance(floor(accumulator))`. Do not feed elapsed wall time on resume. No AI requests or arrival acknowledgments should run while paused. Save fractional time separately if subsecond visual phase must survive reload.
3. For each pending goal, use its resident role and source context to review the mapped route and destination. Only then call `SetAccess(id, true)`. For `RouteWait`, require a successful non-partial native navpath, continuous collision/swept capsule clearance and correct source access along the **entire** path. Acquire `Reserve`, store the token, then dispatch native movement. If movement dispatch fails, safely stop/clear before `AcknowledgeStopped`.
4. On native MoveCompleted, require success, matching token, current route/access, grounded destination proximity and no partial-path fallback before `Arrive`. Recheck role/access during movement. A timeout/revocation sets `StopRequested`: abort native navigation, move out of the doorway safely if needed, then acknowledge clearance. Do not release occupancy simply because a timer expired.
5. After failed travel, the model retains the last confirmed waypoint. Before reusing a route, the body must physically return there via a verified recovery path. No live teleport is authorized by this model. Representing a far resident must obey the same route/capacity/arrival validation; `SetNear` alone changes no identity, location, permissions or progress.
6. When `Working`, select an actual reviewed animation using `Plans()[index].Goals[GoalIndex].Action`, with per-identity animation phase derived from a stable ID hash. Read `Remaining` for task progress. Completed goals are remembered exactly once in `Completions`; use `(resident ID, goal ID)` as the deduplication key for downstream effects. Loading must not replay prior rewards or spawn service effects.
7. Store `Save()` UTF-8 text in a SaveGame string or atomic file replacement. Stop/destroy existing bodies and release actual passage occupancy before `Load()`. Restore bodies at the snapshot's confirmed waypoint transforms, validate collision, then reapprove tasks. Access approvals and in-flight reservations deliberately do not survive reload; goals, names/config binding, timestamps, remaining work, near flags and pause state do. Token high-water marks reject stale callbacks even when loading an older save in the same world. Across a new world, cancel all old callbacks before initialization. Validate saved body transforms separately if preserving mid-path poses is desired.

The model's `Save`/`Load` is serialization, not an installed disk persistence service. The tests write and read its exact payload through a real temporary disk file. Storage location, atomic write failure recovery, user save UI and Unreal SaveGame wiring remain adapter work.

### Exact current controller hooks (inspected 2026-09-07)

All paths below are under `Plugins/MikdashRuntime/Source/MikdashRuntime/` and are integration proposals only:

- `Private/MikdashPlayerController.cpp`, `BeginPlay()` line 126: starts local setup and calls `OpenMenu()`. Initialize the subsystem's configuration/load before enabling the first population; begin with its clock paused so the welcome screen does not advance plans.
- `PlayerTick(float)` line 150: calls `UpdateFootsteps`, returns for menu/nonlocal/no-pawn/paused, then lines 155–156 accumulate `ResidentClockSeconds` and call the old `ResidentSimulation.AdvanceTo`. Replace **only those two old-model lines** with a subsystem tick forwarder if the subsystem is controller-driven; otherwise remove their crowd responsibility and let one subsystem tick source own time. Do not tick both. Preserve footstep and player movement code.
- `OpenMenu()` line 209: sets `bMenuOpen` and `SetPause(true)` at 212–213. Notify the crowd adapter here, including any path-following components configured to tick during pause. Window deactivation already calls this method, so this hook covers loss of focus.
- `ResumeWalkthrough()` line 247: `SetPause(false)` at 256 follows the explicit initial Start or later resume path. Unpause the crowd here without wall-clock catch-up. `ToggleWalkthroughMenu()` at 264 already avoids initial Escape starting play; preserve that behavior.
- `Public/MikdashPlayerController.h` line 7 includes `ResidentSimulation.h`; lines 61–62 own the old simulation and double clock. Migrating these fields/includes is integrator-owned. No display currently consumes an embodied crowd; populate the new subsystem and actor registry explicitly.
- `MikdashRuntime.Build.cs` currently includes Core/CoreUObject/Engine/InputCore and Slate/SlateCore only. The standalone header needs no dependency additions. A concrete native AI/nav adapter may need AIModule and NavigationSystem after installed API inspection; those are not added or build-tested here.
- Existing `ToggleSound()` uses `SaveConfig()` for mute only. It is not a resident SaveGame path. Add a distinct save/load entrypoint and world teardown callback cancellation; do not put crowd payload in the mute config setting.

Reservation lifecycle: `AccessReview -> SetAccess(true) -> Schedule/RouteWait -> valid native path -> Reserve(token) -> dispatch movement -> Arrive(token) -> Working -> completion memory -> AccessReview(next goal)`. Failure/revocation/timeout goes to physical stop and passage clearance, then `AcknowledgeStopped(token)`, safe recovery to confirmed waypoint, re-review and fresh token. Native abort completion callbacks must never be treated as successful arrivals.

## Source restrictions

`SourceNpcPointPermitted` ports exactly `life.ts` lines 23–27 in source amot: visitor has two disjoint envelopes, owner the small owner lane, levi the narrow band, kohen the remaining explicit envelope. Nonfinite values and unknown roles reject. Convert native X/Y centimeters to source X/Z by dividing by 50 before calling. It is an NPC **point placement** helper, insufficient for a route or actual service authorization. Endpoints in the two visitor envelopes do not authorize crossing the forbidden gap. Exact rectangle boundaries are covered by tests.

Original source: `C:/Mikdash/Mikdash-Windows-Transfer/Workspace/mikdash-walkthrough/lib/mikdash/life.ts`, SHA256 `2fb6a7bcd19ddfd01711b6aa871ccd8e992f590ef33fbdeccd00e5d9baa45e2c`. Existing reconciliation: `SourceAssets/runtime-review/access-policy-source-reconciliation.json`. `viewer.ts` free exploration uses collision when journey is idle; `journey.ts` pilgrim restrictions differ. Do not substitute this NPC helper for either player mode. Exterior city roles/hosting routes are not covered by `life.ts` Temple envelopes; they require explicit reviewed adapter policy. No inferred halachic eligibility, purification, service permission or census is added.

## Verification and remaining acceptance

Run `python Scripts/check_resident_crowd.py`. It finds an installed MSVC toolchain, builds the actual header in C++14 with `/W4 /WX`, and runs debug plus optimized `/DNDEBUG` tests. Assertions are custom checks that remain enabled in release. The receipt records input hashes and compiler/test output. Build products and disk roundtrip files are temporary; no Unreal process is launched.

Coverage: distinct authored schedules/actions, pause, access revocation and progress preservation, no travel from clock jumps, exactly-once completion memory, shared doorway capacity, timeout occupancy retention, mismatched and stale callbacks, save/load/disk roundtrip, partial-work continuation, malformed/foreign/truncated saves, configuration mismatch, integer overflow, source role boundaries, near-state persistence, equivalent split clock steps, and a 256-identity resource-contention fixture. This is not an RTX2070 crowd benchmark.

Pending: actual dressed bodies and animations, native subsystem/build compilation, reviewed navigation and access mappings, physical recovery, real storage service, visible interactions, native pause/save/reload, crowd performance and packaged testing. Keep the existing small `ResidentSimulation` panel until migration is explicitly wired; running this header alone changes no scene.

Local runner lesson: Windows environment keys must be normalized before combining vcvars output with Python's environment (`Path` versus `PATH`), and locate `cl.exe` through the resulting toolchain PATH explicitly. The runner does this and never downloads a toolchain.

Review correction: loading a reduced remaining-work value originally checked its range but omitted whether enough simulation time had elapsed. A corrupt clock-zero snapshot could claim six seconds worked before the first scheduled start. The actual-header regression reproduced this (`elapsed-work-regression-before-fix.json`). Load now checks consumed work against `snapshot clock - max(goal earliest start, previous goal completion)`, rejecting impossible progress transactionally. Regressions cover clock zero, one second past earliest start, and a later goal whose preceding completion is more restrictive than its schedule. Legitimate partial-work restores still finish at their expected times. Treat range checks alone as insufficient for persisted progress.

An actual new `AMikdashResidentCharacter` adapter source is now authored; see `CHARACTER_ADAPTER.md` for exact binding/lifetime, required NavigationSystem dependency and installed-header inspection. It is uncompiled and unplaced. The portable model's repaired final receipt passes 520 active checks in both configurations.
