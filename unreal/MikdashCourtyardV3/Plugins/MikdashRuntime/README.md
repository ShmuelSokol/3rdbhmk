# Walkthrough runtime — compiled, runtime acceptance pending

The descriptor remains disabled by default, but the working project explicitly enables this plugin. Courtyard now uses a saved and reopened duplicate game mode with MikdashPlayerController and the existing BP_MikdashWalker. It adds a PlayerController using the existing Character and collision, a Slate start/pause menu, Escape release/resume, WASD/arrow walking, mouse look, mute and quit. The controller blocks lower input components so existing first-person template actions cannot double the input. It also supplies distance-driven hard/soft-ground footsteps from imported CC0 recordings. It does not supply a finished ambience mix, journey access zoning, crowds or tours.

## Compilation history (superseded by current result below)

Installed Unreal 5.8.2 Windows_SDK.json prefers MSVC 14.44.35211 or newer in the14.44 family, or supported14.50 versions. Only VS2019 is currently installed. The automatic approval review rejected an unattended VS2022 Build Tools installation; explicit user approval is pending. Do not bypass this rejection. No installer started.

Compile with Unreal AutomationTool BuildPlugin into a separate output directory before enabling. Preserve After-Instances checkpoint. Enable only after the compiler succeeds, restart the editor, then assign /Script/MikdashRuntime.MikdashPlayerController to a duplicate of the current walkthrough GameMode while retaining BP_MikdashWalker and the existing PlayerStart.

## Required acceptance, all still pending

- Initial packaged window opens paused with the pointer visible and free; no automatic mouse trap.
- Start button resumes, captures only the game window, and preserves grounded Character walking.
- W/A/S/D and arrows move once at intended speed; diagonal speed matches axial speed. Mouse axes turn/look correctly. Template jump/fire actions do not run.
- Escape while walking pauses and releases the pointer. Escape and Resume both resume. Repeat at least five cycles without stuck keys, drift or accumulated input.
- Alt-tab releases safely and opens pause; switching back never silently resumes movement.
- Menu buttons work with pointer and keyboard at common window sizes. Escape works with each button focused.
- M and the menu sound control mute/restore only this world's audio device, with state persisting across a fresh launch.
- Quit button and Alt+F4 terminate cleanly. Editor PIE tests remain bounded with a separate automatic stop.
- Re-run source floor/stair/wall checks using this controller; then verify a fresh packaged executable with the editor closed.

Existing scripted movement receipts test the old controller and cannot accept this plugin. The JSON descriptor passed parsing and source API signatures were checked against the installed engine; neither is C++ compilation or runtime proof.

Distance-driven stone footsteps are now authored using six hard-referenced CC0 samples. Native samples saved/reopened; playback code uncompiled. Verify silence while standing, blocked, paused, falling and after teleport; verify left/right variation, walking-speed cadence, mute and actual recording quality. Floor-contact family selection is now authored: terrain uses soft-ground samples; architecture, streets and buildings use hard-surface samples; unknown families are silent. Actual contact switching and listening tests remain pending.

Standalone timing validation: Tests/FootstepCadenceTest.cpp includes the production Public/FootstepCadence.h. MSVC14.28 C++14 /W4 /WX compilation and execution passed. Cadence at30/60/120fps matched:15steps/10s at100cm/s,26 at240cm/s,37 at600cm/s. Rest/wall/pause/air/relocation/reset cases passed. Full Unreal compilation, surface-aware selection and listening tests remain pending.

Startup Escape correction: the welcome screen consumes Escape without starting or capturing. After Start, Escape resumes from pause as before. Slate repeated Escape/M key-down events are consumed without repeated toggles. Source review confirmed FKeyEvent inherits IsRepeat() in installed SlateCore Input/Events.h. Full compile and native keyboard acceptance remain pending; specifically test holding Escape/M and pressing Escape before Start.


## Current verified build, 2026-09-07
Full BuildPlugin succeeded for Editor Development, Game Development and Game Shipping in RuntimeBuild-Full-01. MSVC14.44.35228, WindowsSDK26100, NetFxSDK4.8 installed. Fixed C4458 local-variable shadowing without disabling warnings. Scripts/activate_compiled_runtime.py saved and reopened the copied game mode assignment; SourceAssets/runtime-review/runtime-activation.json records exact classes and checkpoint. BuildCookRun for the actual Windows walkthrough is in progress. Earlier uncompiled/disabled statements above describe prior history; physical input, audio, packaged runtime and sharing remain pending.
