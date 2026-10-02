# Runtime candidate02: continuously serviced stopped owner

Review candidate only. The UE adapter and this owner loop are uncompiled and
unexecuted. No receiver, listener, media, process or project integration was started.
Candidate01 and Source02/03/04/Compile02 remain unchanged.

The coordinator reports Herschel independently passed candidate01's actual pure
StoppedLease.h: 14 cases / 46 assertions, plus 8 source checks and stopped-only
installed-UE API review. Those unchanged tests were not rerun here. This is
production policy header evidence, not compiled UE ownership evidence. This
revision's source_checks.py checks control flow text only.

ServicedStoppedOwner.cpp uses the actual candidate01 UE owner and Receiver04
Bootstrap::Shutdown directly. Explicit Create attaches OnBeginFrame and
OnEnginePreExit callbacks. Each frame reauthorizes the full immutable identity,
raw Windows QPC deadline, stopped/disconnected state, registry pointer and producer,
exact initial world/viewport/window and single-window scope. Caller borrowing does
not refresh the frame-service timestamp. Equality at expiry, backward clock and a
service gap over 0.5 seconds revoke borrowing. Deadline cannot exceed the owner's
QPC expiry; original lease also caps admission at 24 hours. No renewal API exists.

Shutdown revokes first, checks for prohibited media activity, shuts down the actual
receiver, then detaches/removes only the owned stopped streamer. Reentrant calls
return pending. Failed receiver cleanup, observed media or failed lease cleanup
permanently quarantine the allocation without repeated attempts. Strong delegate
captures retain the receiver and lease even if the host drops its reference;
successful closure removes both delegates. The outer process/session host must
retain capacity on quarantine until independently proved owned Job exit. No code
here reports process cleanup or returns session capacity.

Host integration contract (not installed):

1. On the game thread, retain the module, Slate, a fresh shared Receiver04 Bootstrap
   and this owner. Exclusively serialize *all* streamer registry mutations; absence
   checks cannot arbitrate foreign writers. Reject any existing/default streamer ID.
2. Explicitly Create with the trusted allocation identity and finite raw QPC bound.
   Require Ready. Borrow only for trusted bootstrap wiring. Receiver bootstrap must
   carry an equal or earlier native deadline. Its existing SettingsProof callback
   should include Matches(full Owner), plus the separate real settings proof.
   Callback ownership must be weak to avoid a receiver-to-owner reference cycle.
   This wrapper does not call Bootstrap::Start or grant media startup.
3. Call Shutdown BEFORE Slate or the PixelStreaming module tears down. The actual
   engine pre-exit hook is a fallback, not a guarantee for arbitrary plugin unload.
   Keep module/Slate valid until close; quarantine requires owned process exit.

OnBeginFrame is independent of gameplay pause, but cannot execute while its engine
thread is stalled. Cleanup occurs at the first subsequent frame or explicit host
shutdown; there is no hard wall-clock cleanup guarantee. A long gap fails closed
when service resumes. Stock backbuffer capture observes all Slate windows: this
poll detects extra/replaced windows, but cannot prevent a render frame between a
window change and the next check. Consequently this remains STOPPED ONLY. Real
media requires a separately reviewed capture boundary and authenticated route.

Required next native review cases (not executed): expiry without any Borrow call;
exact deadline; paused frames; 0.5-second gap boundary; backward QPC; extra/replaced
window; world replacement; external stream activation before shutdown; receiver
shutdown failure; nested Shutdown; caller reference dropped during callback;
explicit teardown before module unload. Verify both delegate retention on failure
and removal on success. No claim that source checks exercise these UE behaviors.

Primary local API locations and hashes are in source-context.json. The additional
module source includes both candidate01's OwnedStoppedStreamer.cpp and this .cpp;
it requires the existing Receiver04 closure and Slate/Engine/PS2 dependencies.
Do not add it to frozen Compile02 or the production project without assignment.
