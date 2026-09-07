# Controls and walking audit

Scope: current C++ source plus frozen historical receipts. No native execution, physical-input acceptance, or C++ edits by this worker. Paths below are project-relative and all inspected inputs are frozen in manifest.json.

## Evidence and remaining gaps

- MikdashPlayerController.cpp:143-147 binds P/Escape/M and mouse axes; 157-164 polls WASD/arrows and clamps diagonal input. This establishes source intent only. Walkthrough-05 compiled P, but its receipt explicitly leaves physical P unaccepted. Walkthrough-04 receipt leaves rendered lesson acceptance pending.
- OpenMenu (217 onward) pauses, flushes pressed keys, stops movement, exposes cursor and selects DoNotLock. ResumeWalkthrough flushes keys, unpauses, hides cursor and selects GameOnly. Startup toggle guard prevents P/Escape from starting initially. Cursor visibility does not prove OS pointer release; test moving onto another application.
- Packaged UI first-pass receipt establishes observed Walkthrough-01 welcome Escape, pause/resume, Alt-tab pause and quit behavior. It explicitly does not establish sustained walking, diagonal speed, key repeats or mouse range. Mute persistence later passed in Walkthrough-02; audible mute remains separate.
- Current saved step limit is 55 cm: step55-saved.json and fresh-spawn duchan evidence supersede 45 cm history. ulam-connected-summary.json reports 163.68 m, 249 walking-mode samples, ten waypoints using saved 55 cm. These are synthetic, historical continuous collision tests, not physical control or current-platform acceptance. Do not reduce step height or change geometry based solely on the old no-motion failure: its game clock was frozen.
- Preparation handler SMikdashPreparation.h:108-111 handles Escape but not P. Controller P remains active with GameAndUI. After a walk has started, unhandled P may reach controller ToggleWalkthroughMenu and resume directly from lesson, whereas Escape runs Back. This is an evidenced source-path inconsistency, with actual focus/propagation effect pending native confirmation. Minimal proposed fix for source owner: handle P alongside Escape in preparation OnKeyDown, including the existing repeat guard. Do not disable emergency Escape.

## Coordinator native entry point

Use a clean saved production Courtyard, stopped PIE, foreground user consent/context already resolved by coordinator, no simultaneous native job. Editor Python console:

    import runpy
    control_probe = runpy.run_path(r'C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\runtime-review\control-audit\native_control_probe.py')
    control_probe['start'](90)

This explicitly begins PIE with GameGetsMouseControl false and restores that preference/throttling on completion. It never presses a key, invokes a controller action, moves/teleports a pawn, saves a map, or changes step height. Start button deliberately captures mouse only when operator clicks it. Post-tick deadline is 90 seconds, including startup; startup world failure ends after 20 seconds. A blocked/crashed editor cannot execute Python callbacks: coordinator must independently supervise the wall-clock bound and use ordinary editor Stop if necessary. Record actual PIE destruction from editor state/log after stop request; receipt does not falsely claim it.

Report filename is returned immediately. It samples menu/pause/cursor flags, position, velocity, view rotation, movement mode and capsule/step size at 10 Hz. A completed observation is not a pass. API reflection compatibility is unverified until native run. No telemetry key polling can establish physical keyboard provenance; pair receipt with explicit operator event timestamps and native captures. UI may consume events before controller handling.

## Bounded physical protocols

Run each as a separate <=90 second observed PIE session, using P for normal pause because physical Escape can terminate computer-use tooling. Preserve Escape as an independent operator check. Stop if route contact, focus, or pointer behavior is unexpected.

1. Controls/menu (90 seconds): 0-10 welcome, physically tap P and Escape: neither starts. 10-20 click Start, small mouse look, tap P. Confirm stopped motion, paused clock and pointer movement outside viewport. 20-35 click Resume, hold W for <=1 second on clear spawn lane, release, pause; verify no residual movement. 35-50 resume and briefly test arrows plus opposite keys. 50-65 physically hold P, verify no repeated pause/resume. 65-80 Alt-tab while walking input is released: return must stay paused. Close with editor Stop before deadline. Capture observed events with times, not just method-call logs.
2. Lesson routing (60 seconds): welcome -> preparation -> P, then Escape; record destination and pointer state. Repeat after Start -> P -> preparation. Neither lesson-back action should unexpectedly capture mouse/start walking. Confirm focus on both lesson body and answer button. This specifically resolves the proposed P-handler inconsistency.
3. Movement (90 seconds): coordinator selects reviewed clear route from existing east-gate/duchan/ulam waypoints. Record initial 55 cm step value; physically traverse one stair section and back, no teleport/flying or parameter overrides. Require supported endpoints and continuous traces; falling/stuck triggers review. Separate clear-level forward/diagonal runs can compare speed telemetry with equal hold durations; no numerical pass without observed physical inputs.
4. Packaged confirmation: Python observer is editor-only. Fresh deliberately cooked package requires separate physical P/Escape, cursor release, mouse look, sustained WASD/arrows, stair route, held-key, focus-loss, mute audition and shutdown checks, with package hash and captures/logs. Historical -skipcook Walkthrough05 is not proof of newly changed scene content.

## Offline verification and next task

Run `python Scripts/audit_runtime_controls.py` from project or by absolute path. It parses harness syntax, validates source/receipt contracts, checks passive harness calls and inert import, and writes offline-checks.json plus frozen bytes/SHA256 manifest. Checks do not replace native execution. No Git operation belongs to this worker.

Next bounded owned task after native receipts: review only control-audit observations and classify each physical event, source-method evidence and unresolved gap; prepare a focused fix request to C++ owner if preparation P propagation is reproduced.
