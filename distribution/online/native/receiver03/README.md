# Receiver03 — new source, Source02 preserved

Matching receiver and private bootstrap source now exist. They have **not been
compiled or executed in Unreal**. No sockets/listeners, native process, UBT,
production config, plugin build file, hosting service, commit or publication copy
was used for this work. Source02's complete 26-file receipt hash set is unchanged.

## Concrete implementation

`Wire.cpp/.h` accepts the frozen `adapters/loopback_channel.py` wire format exactly:
4-byte big-endian body length, 2–4096 ASCII JSON bytes, 32-byte HMAC-SHA256. Windows
CNG computes HMAC; the request/response domains include their terminating NUL:
`mikdash-request-v1\0` and `mikdash-response-v1\0`. MAC comparison has no early-exit
byte loop. Authentication precedes JSON parsing. Token scanning refuses duplicate
keys at every object depth, arrays, extra roots, depth >3, >128 tokens, nonfinite
numbers, oversized strings, unknown fields and wrong field types. Core-generated
identities must be ASCII letters/digits/underscore/hyphen, length 1–128.

`Receiver.cpp/.h` provides the actual FSocket listener/connection/read/write source,
not a receiver mock. Constructor opens nothing. Explicit `Start` binds IPv4
127.0.0.1 only, without address reuse, backlog one. All sockets are nonblocking.
`FrameBuffer.h` enforces a fixed 0.5-second deadline from accept through ACK send;
partial reads never renew it. Each frame/tick permits at most four <=1024-byte
reads, one command dispatch and one send. One peer and one request are retained;
there is no worker input queue, pipelining, retry or enqueue-success ACK.

The admission cap is 256 connections/second, above the frozen gateway's 240 total
messages/second with lifecycle headroom. Overload closes the accepted transport
explicitly; it never waits behind a saturated application queue. A single game
tick can still apply only one command. Slow game frames therefore reduce throughput;
browser ACK pacing/coalescing handles normal 30/60 fps rates, not arbitrary stalls.
The immutable lease expires normally, with at most five seconds of cleanup-only
receiver availability afterward. Native process lifetime is still the process
manager's responsibility.

`Service` authenticates the full exact ownership before invoking the frozen
`SessionBridge` on the game thread. Sequences, connection generation, input actions,
expiry and held-input watchdog use the frozen bridge. ACK is generated only after
Handle returns, and late/over-budget application produces no ACK and initiates
shutdown. Rejected commands carry only fixed `rejected` status. Receiver shutdown
first stops admissions/closes transports, independently attempts input release,
and returns false while any close/release remains unconfirmed. Failed socket close
retains its exact handle for retry. No process-name or recycled-PID cleanup.

`Bootstrap.cpp/.h` wires the controller sink, deny-all PixelStreaming2 input gate,
service, listener and OnBeginFrame polling (including paused gameplay). Explicit
Start requires the owned, initialized controller and a stopped DefaultRtc streamer.
The private inherited stdin must be a pipe; there is no environment/argument/file
secret fallback. Bootstrap has a five-second total read budget and <=4096-byte
record. It validates the exact streamer ID, key, owner, clock-domain tag and deadline
before opening the listener. It does not start media signalling: gateway admission
must be ready before the future owner module starts that exact streamer. Shutdown
requests StopStreaming only after verified ownership and never restores the unsafe
default input handler. `IsReady` is only receiver readiness, not first-frame proof.

Callers must keep a bootstrap object alive and retry Shutdown when it returns false;
destructors are best-effort cleanup, **not** disposal receipts. A hung game thread
cannot execute its watchdog. The external owned-process watchdog/Windows job and
reconciliation remain necessary and are not implemented by Receiver03. An ACK for
native `close` confirms the frozen bridge's input release, **not complete WebRTC or
process destruction**. The future stream adapter must also close/reconcile signalling
and prove exact process/resource disposal before freeing core capacity. Do not treat
this receiver alone as that complete StreamAdapter.close implementation.

## Clock contract: new QPC sessions only

Do not feed an already-running default-clock core into this bootstrap.
`adapters/receiver03_bootstrap.py:create_qpc_core` constructs a NEW core and frozen
BridgeStreams using the existing injectable-clock API, with raw Windows
QueryPerformanceCounter / QueryPerformanceFrequency seconds for both. Native
`QpcSeconds()` uses those same APIs on the same Windows system/boot. It does not use
FPlatformTime::Seconds(), whose inspected UE implementation adds 16,777,216 seconds.
No frozen core API or file was changed, and no existing deadline is migrated.

Microsoft documents QPC consistency across processes, boot-fixed frequency, and a
one-tick cross-thread ordering ambiguity in its [primary QPC guidance](https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps).
The helper requires frequency >=1000 Hz. It brackets the host clock sample with
raw QPC samples, refuses offsets/drift outside that bracket, backwards samples,
or brackets >50ms, and subtracts a further 2ms uncertainty margin. The native deadline
is `min(owner.expires_at, first_qpc + remaining_at_core_sample) - 0.002`, so it cannot
extend the QPC owner's lifetime. The native parser checks the explicit domain tag;
bootstrap also rejects any deadline greater than the owner's QPC expiry. Startup,
pipe delay and late input consume the already-fixed deadline. The bracket is a
consistency check, not a claim that arbitrary clocks can be calibrated from three
samples. Other host clock domains are unsupported and must not be relabelled as QPC.

## Host-side private bootstrap wiring

`adapters/receiver03_bootstrap.py` implements bounded record generation and a
single-use anonymous stdin pipe. Its imports create no handles/processes. The owner
launcher should generate a per-process 32-byte key in memory, use `make_record`
with an owner from `create_qpc_core`, preload `PrivateBootstrapPipe`, and pass that
pipe's read_fd as stdin to the exact child with close_fds=True and shell=False.
Close the parent's read copy immediately after spawn. Never place record/key bytes
in args, environment, saved receipts, files or logs. The record writer uses one
<=4096-byte preload into the empty Windows anonymous pipe, no write retry loop.
Keep the key only in the corresponding frozen LoopbackChannel instance/registry.

The child owner module must call RuntimeBootstrap.Start after PlayerInput exists,
before exposing the streamer. OnBeginFrame drives pipe/receiver polling. The host
then uses the unchanged channel `exchange` and exact bridge ACK schema. Service is
synchronous on UE's game thread; do not bind the JS gateway authority seam directly
to an async/queued completion. Node/Python bounded RPC, browser admission/upgrades,
owned native process launch/job control and module/package integration remain the
next host integration work. No such code is claimed delivered here.

## Verification and exact limits

Run from OnlineWalkthrough:

```powershell
python -B -m unittest -v adapters.test_receiver03_bootstrap
node --test native/receiver03/offered_rate.test.mjs
python -B adapters/validate_receiver03.py --receipt native/receiver03/receipt-01.json
```

Ten Python tests execute real host bootstrap/frame functions with pipe operations
replaced, plus explicit source/boundary assertions. Three JS tests execute frozen
browser Controls/ControlPort against a deterministic native scheduling model. They
reproduce the old 16/s failure, conserve accepted look deltas at 60/30 fps, and keep
the existing bounded queue. These are **not** end-to-end native throughput tests.
No pipe or socket is opened by these tests.

`ReceiverTests.cpp` stages three native automation tests against the actual CNG
decoder, production Service and FrameBuffer: public frozen-Python frame compatibility,
MAC/direction tampering, duplicate JSON, partial/oversized/late framing, ownership,
replay, delivery, watchdog, late application ACK refusal and failed/double shutdown.
They require a later explicitly approved native build/run and are not counted as
passed now. `public-test-vectors.json` and `FrozenVector.h` use a public all-zero
test key, never a generated/deployed secret. The receipt contains hashes/counts and
limitations, not frame payloads or key material.

Future compilation needs existing UE Core, Engine, InputCore, ApplicationCore,
Json, Sockets, PixelStreaming2Core and PixelStreaming2Input module dependencies plus
Windows bcrypt.lib (the source follows the engine's own CNG linkage pattern).
No Build.cs, uplugin or project file has been changed. C++ compilation, actual
paused-frame ordering, real first-frame/input delivery and shutdown/resource proof
remain unverified. Source02 should be published independently of this new slice.
