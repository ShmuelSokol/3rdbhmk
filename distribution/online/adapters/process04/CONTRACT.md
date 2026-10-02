# Process04 integration contract

This is new, unlaunched source. Source02 and Receiver03 remain frozen historical
evidence. Process04 does not make those revisions safe to deploy unchanged.

## Lifecycle and readiness

`host.make_host(recipe, ports, revoke, limits)` creates a NEW QPC-clock pool and
reuses the reviewed core, BridgeStreams input/ACK validation and LoopbackChannel
HMAC framing. It opens nothing. `processes.prepare()` verifies a reviewed local
executable hash; deployment directories must be immutable to untrusted writers.
No executable recipe is supplied or approved by this slice.

The trusted host calls core.request and CoreAuthority.attach. The recipe, port
pool, full Ownership and HMAC key never come from browser JSON. Ports are logical
allocations, not OS reservations. A collision fails authentication and cleans
only the newly owned child, never the process holding that port. Ports remain
allocated through failed cleanup. Saves/settings identities are passed in the
private bootstrap; the approved future game artifact must apply both identities
before accessing saves/settings. Receiver03 alone does not do that.

The child is created suspended with an explicit two-handle inheritance list:
private stdin reader and NUL output. Assign-to-job precedes ResumeThread. The
unnamed job limits active processes to ONE, disables breakaway and kills on job
close. Use the inner game executable, not the package launcher. A CrashReportClient
or any other subprocess is deliberately disallowed. The job has a bounded memory
limit; deployment disk/available-commit admission guards still belong to the
coordinator's launch gate and have not been bypassed or implemented here.

No HMAC key is in argv, inherited environment, files, logs or receipts. Only five
public ownership placeholders can expand into reviewed static argv. Stdout/stderr
are NUL; the artifact must itself avoid logging/serialization of bootstrap secrets.
The child environment is an explicit SystemRoot/WINDIR/TEMP/TMP whitelist. Python
immutable bytes cannot promise zeroization; keys remain private process memory.

Bootstrap uses Receiver03 `make_record`, NOT `PrivateBootstrapPipe`. The <=4096
frame is written AFTER containment/resume by one owned worker. The host never
calls blocking WriteFile itself. A write must be observed complete before the
fixed write deadline (default 2s). Readiness shares a fixed launch deadline
(default 30s, max 60s); owner expiry always wins. Poll loops also have finite
iteration caps. Timeout terminates the exact job, calls CancelSynchronousIo on a
duplicated writer-thread handle, and retains the lease until root signal, zero
job processes, worker exit and handle closes are proved. It neither abandons a
writer nor reuses its slot. OS syscalls/host scheduling cannot provide a hard
real-time guarantee; the bounded guarantee is host waits/retries plus quarantine.

Reachable TCP is only a startup hint. The frozen BridgeStreams.open then performs
exactly one authenticated open exchange, no command replay, before core.request
can succeed. An ACK means authenticated controller readiness only when the
approved artifact implements the corrected consumption contract below. There is
no cached/synthesized ACK. One request per connection matches Receiver03 framing.

`OwnedStreams.close` revokes the exact signalling allocation AND terminates/proves
the exact owned process and writer before dropping its bridge record. A native
close ACK proves input release only and is not used as process-disposal evidence.
Either failed revocation or failed disposal retains capacity. Reentrant close
fails pending without recursion. Process stop is idempotent after confirmed exit.

## Receiver corrections required by independent review

1. The historical preloaded anonymous pipe has no proved bounded write time.
   Process04 replaces that path with an owned cancellable writer. No frozen edit.
2. `ControllerSink::Apply` proves InputKey enqueue, not gameplay consumption.
   NEW `native/receiver04/` implements a one-slot semantic mailbox, authenticated
   authority and staged controller/movement overrides. It keeps remote state out
   of UPlayerInput and normal pawn pending vectors. It retains original accept
   time, immutable QPC expiry, sequence, generation and controller/pawn incarnations.
   There is no ACK on enqueue. PostProcessInput handles P/M and an explicit
   project interaction-outcome callback; absent callback rejects E. UpdateRotation
   commits look once after camera callbacks and a fresh fence. Paused input clears
   remote movement/look and preserves local input; P/M can still be consumed.
   Controller movement polling and ConsumeInputVector are not acceptance points.
   Walker consumes at ControlledCharacterMove, after jump and virtual acceleration
   calculations, with a fresh check before remote acceleration assignment. Async
   character movement is explicitly refused. Dove uses a vector-taking evaluator
   at ApplyControlInputToVelocity: expiry after the sweep discards its complete
   remote steering/speed/sliding result and computes local/coasting once. A queued
   look/button cannot extend held movement's accept+2s cap. An unconfigured dove
   retains the base obstacle speed reduction. Remote diagnostics have a separate
   sliding accessor because the base one is nonvirtual.
   Callback snapshots and epoch checks suppress ACK after reentrant cancellation.
   No claim is made that physical effects finish before expiry: authorization is
   fresh at semantic consumption; a late handler outcome is unknown and never
   automatically replayed. The native headers/overrides are uncompiled and are
   NOT registered in any actual project. The obsolete draft DeferredService was
   removed before receipt creation; it is not part of the deliverable.
3. UE FSocketBSD::Close calls closesocket and then invalidates its stored socket
   even when closesocket fails. Receiver04 `Receiver::CloseSocket` never claims retry can recover
   that handle. A failure permanently poisons that receiver. The external owned
   job is terminated; only confirmed process exit resolves its resource quarantine.
   This correction is wired into the NEW receiver; Receiver03 is unchanged.

The newly inspected current controller uses BindKey for E/P/M, BindAxisKey for
look and IsInputKeyDown in PlayerTick for movement. Prior WasInputKeyJustPressed
tests alone cannot establish correctness for this exact source. Source paths:

- `C:/Mikdash/Working-5.8/MikdashCourtyardV3/Plugins/MikdashRuntime/Source/MikdashRuntime/Private/MikdashPlayerController.cpp`
- `C:/Program Files/Epic Games/UE_5.8/Engine/Source/Runtime/Sockets/Private/BSDSockets/SocketsBSD.cpp`
- `C:/Program Files/Epic Games/UE_5.8/Engine/Source/Runtime/Engine/Private/PlayerController.cpp`

## Admission, authenticated streaming and RPC seam

There is NO network admission/RPC listener here. Browser data cannot construct a
LaunchRecipe, Ownership, port, key or CoreAuthority.Binding. A future authenticated
host mints an opaque admission capability and binds it to exactly one ticket,
connection and stream. Admission is withheld until native open and exact gateway
allocation succeed; allocation failure cancels that owner and waits for cleanup.
No stream-id-only authentication or first-stream fallback is permissible.

The synchronous `revoke(owner)` callback MUST finish exact route/peer revocation
within its own bounded budget and return None. Throw/any other return retains the
lease; it must not call core APIs, enqueue success, or await work under core locks.
The current Node gateway requires synchronous authority completion. An async
Python RPC cannot be attached to it unchanged. The next transport revision must
await a bounded authenticated response, allow one outstanding call per binding,
bind request ID/owner/connection/deadline/direction to authentication, reject
duplicates and late replies, and serialize revocation without lock inversion.
Input success follows consumed-native ACK, never enqueue. Maximum frame 4096,
maximum one pending command per binding, fixed <=1s RPC budget, native peer budget
0.5s; no automatic input retry. Host admission has a separate <=60s budget.

Host scheduling must call core.tick at bounded intervals (target 10ms) even when
no browser messages arrive, and stop all owned jobs on service shutdown. There is
no background service/watchdog installed by this slice. Loss of host process
closes jobs in the kernel; an alive but stalled host requires an external supervisor.

Native response version 2 adds status=consumed, explicit outcome, authorized_at
QPC timestamp and generation. The NEW ConsumptionChannel authenticates through
the frozen LoopbackChannel, verifies exact shape, owner, sequence, generation,
timestamp and <=0.5s response/session bounds, then adapts consumed applied/no_op
results to the frozen BridgeStreams ACK shape. No_op is semantic consumption with
no effect; neither that ACK nor the browser's existing control ACK proves motion.
Legacy enqueue-only ACKs are refused. No core or frozen gateway API was changed.

Receiver04 now has a concrete nonblocking loopback socket pump and private stdin
bootstrap-to-Authority wiring in NEW files. They reuse only Receiver03 frame,
parser, HMAC and QPC helpers. The socket pump retains original accept time and
awaits actual semantic completion. A zero-byte startup hint is dropped on EOF
without spending the full 0.5s peer lifetime. Close failure permanently poisons
the receiver rather than pretending that the native handle can be recovered.
No listener has been opened and this C++ source has not been compiled.

Media StartStreaming, authenticated streamer upgrade/attach, native module/class
registration, save/settings application and browser-to-host admission wiring
are still absent.
Controller setup also requires trusted settings-ownership proof and an explicit
look scale; no guessed default launch recipe is supplied. The existing project
uses void interaction handlers, so a project outcome API remains required for E.
Remote movement/look obey UE ignore-input flags (including cinematics) at entry
and final consumption. Look supports stock non-XR camera management only, with
stock no-op rotation modifiers. It evaluates normal modifiers/FaceRotation once,
then applies a remote control-rotation delta with callback-free stock angle
limits. Remote pawn-facing orientation is left for the normal following update;
that visual behavior has NOT been accepted. Custom camera managers/modifiers and
XR refuse remote look instead of double-running arbitrary callbacks.
The historical receiver must not be launched as a substitute. This is not online
delivery or end-to-end browser/native proof.

## Review/validation boundary

`python -B -m unittest adapters.process04.test_host adapters.process04.test_consumption_channel adapters.process04.test_native_order` uses deterministic adapters
and Win32 call doubles, not child processes, threads, pipes, listeners or sockets.
The actual Windows backend is unexecuted; native headers are uncompiled. A later
coordinated owned harmless-child test must cover: oversized/blocked private stdin,
cancel/write race, late completion, child exit before read, no inherited stray
handle, assignment failure, memory/process limits, root signal and zero active
job count, clean double-stop, and survival of an unrelated control process.

Reviewed ownership reference (read only, not copied wholesale):
`C:/Mikdash/Working-5.8/MikdashCourtyardV3/SourceAssets/characters-review/KohenClothExecutableV1/OwnedChildJob.cs`
and its `OS-JOB-INTEGRATION.json`. Process04 reuses suspended-before-assignment,
exact retained handles, signal-plus-accounting cleanup and kill-on-close rules.
It adds explicit inherited handles and private writer cancellation. No inherited
OS-test acceptance is claimed for this different backend.

Windows API references checked for this revision:
- [CreatePipe](https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-createpipe): buffer size is not a bounded-write guarantee.
- [CancelSynchronousIo](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-cancelsynchronousio): cancellation does not wait for completion; the worker remains owned until exit.
- [UpdateProcThreadAttribute](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute): explicit inherited handle list with inheritable stdin/NUL handles.

## Receipt02 corrections from independent receipt01 review

The historical `receipt-01.json` is preserved byte-for-byte. Its source hashes
describe the prior revision, not the corrected current receiver. The validator
records exact changed paths and checks that historical receipt's pinned hash.

Installed UE `FSocketBSD::Recv` returns true/zero for nonblocking would-block,
and false/zero for stream EOF; EOF may leave a stale subsystem error. Receiver04
now uses `ReadStream`: true/zero waits with its partial frame and original deadline,
false drops without consulting stale GetLastErrorCode. StreamReadTests exercises
the actual native helper with UE-shaped doubles and the actual frozen FrameBuffer.
Its Python counterpart models fragmented prefix/body/tag and bounded polling;
source-control-flow checks prove the production receiver calls that helper.

Authority::Maintain now runs before every Receiver::Tick early return, including
no peer and incomplete frames. Session expiry aborts the authority and shuts down
the native listener; no post-expiry listener grace is retained. Host cleanup uses
exact job termination and never requires a late native cleanup ACK.

Bootstrap stdin close failure now retains identity in a permanent poisoned state,
never retries or treats a possibly reused handle as valid, and never reports clean
shutdown. Server/media cleanup still runs independently; owned process exit is
the external disposal proof. CloseBootstrapInput is the shared production/native
test seam. SettingsProof is followed by BootstrapTargetsValid before configuring
or dereferencing controller/pawn: validity, same pawn/input, world, local control,
stopped streamer and fresh deadline are all required after that callback.

These regressions include checks of actual C++ branch order and call sites plus
staged C++ tests of production seams. Python source checks/models do not compile
or execute C++; that remains exclusively the coordinator's reserved native slot.
