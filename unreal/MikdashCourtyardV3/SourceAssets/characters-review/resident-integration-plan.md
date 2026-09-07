# Resident integration: guarded pilot, not released behavior

The five saved `RELEASE_Pilgrims_1` through `_5` actors are skeletal visual actors playing idle. They are not bound to resident runtime state. The existing character adapter accepts native `TSharedPtr` ownership and a `TFunction` segment reviewer; its mutation methods are not reflected to Python. The player controller advances a separate older `ResidentSimulation`. Merely attaching a walk clip would not integrate behavior.

## Deliverables and status

- `Scripts/release_resident_crowd.py`: source preflight and optional read-only native inventory. Read-only by default. Explicit `run(apply=True, allow_review_copy=True)` requires the compiled reflected bridge and creates a unique review-map duplicate; it never edits the source map.
- New `MikdashResidentPopulation.h/.cpp`: an opt-in C++ bridge, **not compiled or run by this worker**. Owns one shared crowd runtime; binds five externally prepared native character bodies; uses fractional simulation seconds, real collision review and existing navigation adapter. Exposes `InitializeReviewedPilot`, `SetPopulationPaused`, activity and status getters.
- Existing `MikdashResidentCharacter.h/.cpp` are unchanged. The population does not replace the saved visual actors automatically or run at BeginPlay.
- No native assets, saved maps, or default game behavior changed by this task.

The preflight originally reported four unreflected mutation methods and zero external binding callers. With the new bridge source present it deliberately reports `SOURCE_CHANGED_REVIEW_NEW_BRIDGE_REQUIRED`; this is not evidence that the bridge is compiled or usable in Python yet.

## Exact visual inventory and safe starting region

Source: `Scripts/release_place_assets.spec.json` and `SourceAssets/IntegratedReviewV2/release-placement-20260907T161402552292Z.json`.

Combined map: `/Game/MikdashV3/IntegratedReviewV2/Maps/Walkthrough`.

Mesh: `/Game/MikdashV3/CharacterReview/PilgrimRigV2/PilgrimRigV2/SkeletalMeshes/PilgrimRigV2`.

The original 27-joint rig has matching `PilgrimRigV2A_Pilgrim_Original_Idle` and `PilgrimRigV2A_Pilgrim_Original_Walk` clips. Manny animation blueprints cannot be assumed compatible. All five saved clips are idle; the walk clip is in place.

Initial feet XY, in native centimeters: `(4900,1000)`, `(5120,1120)`, `(4980,1260)`, `(5240,1330)`, `(4760,1180)`. Floor top is Z300 on `architecture_SM_0129_floor_Outer_court_floor`. Saved origins are Z300.0013. Capsule radius34, half-height96 require character origins near Z396, with mesh relative Z-96. The rig faces local -Y: proposed mesh yaw+90 and character yaw equal old actor yaw-90 preserve the initial pose. These transformations still require native skeletal/bone/feet review.

The prior animated bounds check reported an approximately 11.08cm feet discrepancy. Do not lower the character from an animated AABB alone; inspect actual contact and collision. Existing skeletal actors block collision: staged replacement must remove their duplicate blockers only after checkpointing and verifying the new body visual.

The pilot keeps full capsule footprints inside XY `[4700,900]..[5300,1450]`, in the outer visitor branch of `SourceNpcPointPermitted` (native XY divided by 50). This source placement envelope is not religious eligibility or continuous navigation evidence. No restricted sanctuary, lateral gate corridor, or main east corridor is included.

## What the new bridge actually does

Initialization requires a live game world, exactly five unique previously unbound `AMikdashResidentCharacter` bodies, correct feet locations, unit body scale, capsule34/96, and idle/walk assets matching each mesh skeleton. It creates stable fictional IDs `authored-outer-visitor-01` through `05` and assigns ordinary visitor roles. It refuses before binding if any proposed segment lacks floor or capsule clearance.

Each authored visitor has one nearby meeting-place goal, staggered by four simulation seconds, followed by 30 seconds waiting. Four targets move +80cm X; the fourth moves -80cm X. These are small diagnostic routes, not an authentic timetable or future population claim. A shared capacity-one passage resource serializes motion. Complete goals do not loop or teleport.

Every straight navigation segment must remain in the conservative convex box with capsule inset, within 12cm of the reviewed Z300 floor. Visibility floor traces sample at most25cm apart, require heights within3cm and upward normals >=0.95. Pawn-channel capsule endpoint overlap checks and a continuous capsule sweep reject blockers. The callback ignores only the current body and population owner; other people remain obstacles. Existing character code independently requires grounded movement and a complete navigation path with tightly bounded endpoint projection. Missing traces or missing navigation leave visitors idle. Native RHI/gameplay checks are required; commandlet geometry counts do not establish clearance.

The bridge ticks its shared model once from accumulated delta time, never from each body. World pause and explicit `SetPopulationPaused` pause this clock; root must connect non-world-pausing menus to that reflected setter. The separate controller model remains unchanged and must not be presented as the same residents. Walking clips switch from actual horizontal velocity rather than goal assignment. Gait blending, stride matching, turning and animation pause need native visual validation.

Stopped or timed-out routes retain reservations. The bridge deliberately never calls `ConfirmPassageCleared` without an external physical clearance protocol. Destruction stops the population. A missing body stops every participant conservatively. There is no automatic recovery, rebind, persistence restore, distance virtualization, or offscreen arrival. Runtime Save/Load is available in the core, but atomic world/body persistence remains integration work.

## Required native adoption gates

1. Compile Editor and Game targets; check Unreal reflection and the exact collision/animation APIs. Place a population and five **new native resident bodies** only in a checkpointed scenario; configure the original rig and matching clips. Preserve existing visuals until comparison succeeds.
2. Ensure capsules own locomotion collision; review mesh collision and avoid duplicate old visual blockers. Confirm actual feet/bone contact and forward orientation in idle and walking.
3. Explicitly call `InitializeReviewedPilot` in gameplay. Inspect each native body's ID/name/goal/state; verify all are bound to the one population clock. Do not claim controller inspection UI integration until it reads this model.
4. Demonstrate complete route/arrival, obstacle blocking, no floor response, missing navmesh, menu/world pause, timeout reservation retention, and teardown. Confirm no restricted-region entry or overlap with the player. Absence of motion must report blocked review, not silently start cosmetic walking.
5. Add reviewed passage recovery and atomic save/load before calling residents persistent across launches. Review near/far identity handling before population scaling. Cook and test packaged gameplay separately.

These five clothed visitors are fictional demonstration identities. They do not establish crowd numbers, priest residence, priest status, purity, or permission to serve. No changing clothes, bathing bodies, or immodest mikvah presentation is introduced.

## Verification commands

Offline Python: `python Scripts/release_resident_crowd.py --offline-check`.

Read-only native audit, with the saved combined map already open and no PIE/unsaved work: `runpy.run_path(str(project / 'Scripts/release_resident_crowd.py'))['run'](apply=False)`.

Python AST parsing and offline five-actor/source invariants passed. C++ source was inspected only; compilation, reflected bridge availability, runtime collision, animation, route completion, UI and packaging remain unverified. Root owns native execution and publication.

## Guarded review placement and bounded probe

The prepared script now offers `run(apply=True, allow_review_copy=True)`. It first requires the saved combined map, no PIE/dirty packages and the native reflected population class. It checkpoints and hashes the combined map, hashes the original rig and animation assets, duplicates to a timestamped `/Game/MikdashV3/ResidentCrowdReview/<timestamp>/Walkthrough`, configures five new native characters and one population, then removes only the five copied idle actors. It saves/reopens and checks body poses, references, mesh/animation, collision, capsule and unrelated actor transforms. Original map and source assets are hashed again. Successful placement restores the source editor map. A failed review copy is retained with a failure receipt, never blindly overwritten. No main-map adoption is included.

For root's native probe: load that review map, start PIE explicitly, then call `probe_active_review_game(allow_initialize=True, duration_seconds=20)` from the retained script namespace. It refuses any game outside the review namespace, never starts/stops PIE, calls the real reflected initializer and samples native IDs, goals, states, positions and velocities through a finite Slate callback. It writes a diagnostic receipt and unregisters the callback. Keep the returned module dictionary alive for the callback lifetime. A binding failure or idle route state is diagnostic, not permission to fake motion. The current script cannot distinguish every navmesh rejection from a collision rejection; investigate native navigation if residents remain in route-wait.

This source-only extension has passed Python AST checks. No review map has been generated by this worker and no movement acceptance is asserted.

### Peer review fixes and compile evidence

Placement now requires the editor world package to equal the unique review target before any actor mutation. It compares a single cached scene snapshot before replacement and after save/reopen: exact actor inventory/classes/tags/poses; component identities, relative transforms, visibility, mobility, collision profiles, mesh/material identities, instance transforms, and exposed scalar lighting/postprocess settings. This is a targeted native scene comparison, not serialization of every possible Unreal property. The original saved map hash remains the byte-level protection. Relative mesh yaw+90 and location-96 are checked after reopen. Protection failures write an explicit failed receipt before raising.

The offline record includes Population header/cpp hashes. Placement checks the successful `Astra-Population-Editor-Build.log`, source modification times against that log and the plugin DLL, and records binary/log/source hashes. This passed offline against root's successful native Editor build. Root must use a fresh editor process; disk evidence alone cannot prove a running process has reloaded the DLL.

The probe writes its initial receipt and registers its callback before initialization. Success, exception and callback-registration failure request population pause; normal completion waits up to two extra seconds for zero body velocity and records the result. The probe never stops the user's PIE and never releases passage reservations. Early exceptions can leave zero-velocity readback pending, reported explicitly. No runtime acceptance is claimed from these guards.
