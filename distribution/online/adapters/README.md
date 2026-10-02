# Real-stream source slice — offline verification only

This slice stages a restricted UE signalling router, an Epic WebRTC browser client,
semantic controls, native input gate and bridge source. It contains no demo video.
It is **not an end-to-end walkthrough or a finished production adapter**. The
matching native IPC receiver, owned-process bootstrap, authenticated browser
admission/upgrade service and Node/Python RPC wiring remain unimplemented. Nothing
here starts itself. No listener, native executable, UBT, project/plugin change,
cloud service, publication copy or commit was used to verify this slice.

`session_core.py`, its tests, original README/validator and prior receipts remain
unchanged. Core public APIs were not extended. This directory is eventual
`distribution/online/` source, separate from `web/` book content. The root README
describes the independently accepted core revision; this file describes the new slice.

## Executable source and boundaries

- `../signalling/gateway.mjs` implements UE JSON signalling version 1.3.0: config,
  identify/endpointId confirmation, private list, explicit subscription, offer,
  answer, ICE and disconnect. One allocated streamer, player and control transport
  per core binding. No first-stream fallback, arbitrary subscription, stream rename,
  cross-player delivery, SFU, quality-control commands or unknown message forwarding.
  Host authentication must precede `allocate` and `attach`; those are trusted host
  methods, not public JSON endpoints. Maximum 65,536-character frames and 240 inbound
  messages per second per allocation. Every send rechecks expiry after callbacks.
- `../signalling/websocket_peer.mjs` wraps an **already accepted/authenticated** `ws`
  socket, with frame and buffered-send bounds. It creates no WebSocket server.
  `Gateway` requires synchronous bounded authority methods: `validate` returns
  exactly `true`; `submit`, `release`, `disconnect` return `undefined` only on actual
  completion and throw on failure. A returned queued status/boolean is not success.
  Do not pass async functions/Promises. Future RPC wiring must satisfy this contract
  using a bounded worker bridge or deliberately revise/test the router for async RPC.
- `../browser/main.mjs` bundles the pinned Epic frontend, builds the native video
  element, disables URL settings and direct keyboard/mouse/touch/gamepad/XR input,
  and retains actual WebRTC video/audio and media data-channel messages. Host calls
  `mountWalkthrough` only with an authenticated open control socket and an allocation-
  bound same-origin signalling URL. No credentials in URLs or local storage. The
  initial HTML waits for host attachment; it is not a mock playable scene.
  Controls start inactive; only `webRtcConnected` (after subscription/negotiation)
  enables them. Connecting input is discarded, not queued for later playback.
- `../browser/controls.mjs` sends semantic input over the control connection. One
  request in flight, at most eight queued events; adjacent movement replaces state,
  adjacent look accumulates deltas (bounded to eight normalized units per axis),
  and ACK pacing emits chunks at most one unit per axis. Release discards unsent
  input. A 1.5-second ACK deadline, excessive backlog or malformed ACK closes control.
  Blur, hidden page, pointer cancel/capture loss and disconnect release input.
  A server-observed close must independently release even if browser delivery fails.
  The ACK handler also checks its deadline, so a delayed timer cannot accept a late
  ACK and send queued input. Visibility/focus loss immediately clears local movement
  and queues release; no held state is restored when focus returns. The 200ms state
  heartbeat supports stationary touch without depending on pointer movement or OS
  keyboard repeat. A deterministic five-second/100ms-RTT test verifies bounded state
  refresh and release. This is transport/control validation, not executed UE movement.
- `bridge.py` adapts the stable core to versioned native commands/ACKs. Exact owner,
  connection, sequence, operation and applied status must match. Enqueue is not ACK.
  Failed/late input is rejected; failed cleanup retains records/capacity. `core_host.py`
  binds core connections to stream ownership, translates blur to a core-authorized
  move-zero and makes confirmed disconnect idempotent. Tests run the real core with
  this seam, but the test channel/process manager are doubles.
- `loopback_channel.py` is a concrete stdlib TCP **client source**, with a literal
  `127.0.0.1` destination, one request per connection, absolute connect/read/write
  timeout, <=4,096-byte frames, per-process HMAC-SHA256 capability, direction-separated
  request/response authentication and monotonic sequence refusal. Its tests patch
  socket creation; no socket was opened. It is not a working native transport until
  the matching UE receiver/bootstrap below exists.
- `../native/OnlineInputGate.h`, `SessionBridge.h`, `ControllerSink.h` are uncompiled
  C++ source. Factory installation refuses null metadata, missing media protocol
  entries, an already-streaming instance or any stream type other than `DefaultRtc`.
  Every direct gameplay input method, `OnMessage`, handler registration and `Exec`
  refuses input. No raw command/console forwarding. The separate typed bridge checks
  full ownership, binding, sequence and a fresh native deadline at game-thread apply,
  releases on expiry, and has a two-second held-input watchdog. ACK means the game-
  thread sink received input, not that a frame or gameplay result was observed.
  The future host must tick this watchdog while paused; an external process watchdog
  must dispose a hung UE process. Native source checks are not native execution tests.
  `ControllerSinkTests.cpp` stages UE automation cases for missing PlayerInput,
  unbound/polled input, rejected/retried release and same-frame button pulses. These
  tests have NOT been compiled or run and are not counted among passing tests.

Gateway cleanup marks closing before callbacks and blocks reentrant cleanup. A
synchronous transport-close callback cannot recursively dispose the same peer;
failed close remains quarantined and only unfinished work is retried on `tick`.
Late callbacks cannot delete a replacement allocation with the same stream ID.
Host scheduling of core/gateway tick is required even with zero traffic. It must
bound unauthenticated connections separately and never log raw URLs/frames/secrets.

## Supported controller mapping

Desktop WASD/arrows and the touch walk pad map to quantized move axes (right X,
forward Y). Left-button drag and the touch look pad map to MouseX/MouseY deltas;
the current controller performs its existing pitch inversion. E / Talk calls the
existing talk/next binding, P / Menu the menu binding, M / Mute the sound binding.
Buttons repeat only on a fresh press. Movement heartbeats refresh the held-input
watchdog, never the session lifetime.

Reset, console, Escape conversation/menu semantics, V precinct switching, dove F,
vertical/boost controls, gamepad and XR are unsupported in this slice. In particular,
core support for a `reset` action does not imply any native implementation. The
browser cannot navigate arbitrary native UI widgets yet. Mouse look sensitivity,
touch ergonomics, input delivery while paused and first real video frame are not
accepted by offline source tests.

## Pin and media gate evidence

`../upstream-lock.json` pins Epic's UE5.8 commit
`6b8cfb460bda09703e85178f1f77aa6faec9e890`, the archive digest and all 79 Common/frontend
TypeScript source files. The npm frontend 0.1.2 package reported a different gitHead,
so the build uses **source from the exact commit**, not that published package.
No upstream code is copied into the deliverable. The archive, extracted upstream,
dependencies and generated bundle live outside publication at
`C:/Mikdash/OnlineWalkthrough-cache/real-stream-6b8cfb/`.

`build-deps-lock.json` records exact npm dependencies and integrity: TypeScript 5.9.3,
esbuild 0.25.10, sdp 3.2.2, ws 8.21.0, protobuf runtime 2.11.1 and type packages.
Official npm 10.9.2 was used with `--ignore-scripts --no-audit --no-fund`; no Epic
bootstrap was executed. `build.mjs` verifies archive/source/dependency-lock hashes
and bundles offline via esbuild. This is bundling/syntax validation, not TypeScript
type-check acceptance or proof of UE interoperability.

Installed evidence is UE 5.8.2 CL56702186, under
`C:/Program Files/Epic Games/UE_5.8/Engine/Plugins/Media/PixelStreaming2/Source/`:

- `PixelStreaming2RTC/Private/EpicRtcStreamer.cpp`, `OnDataTrackMessage`: keyframe
  request 0, latency 6, initial settings 7 and echo 8 are handled **before** the
  input-handler dispatch. Relay 198/multiplex 199 are streamer envelope handling;
  this slice exposes no SFU routing. The native input gate never forwards envelopes.
- `PixelStreaming2RTC/Private/RTCInputHandler.cpp`: RequestQualityControl 1 is
  explicitly a no-op in this installed version. Dropping it at the gate does not
  remove a video-start operation. Legacy FPS/bitrate/start/stop IDs reaching the
  input handler are denied; arbitrary command-based encoder changes are denied.
- `PixelStreaming2Input/Private/PixelStreaming2DefaultDataProtocol.cpp`: IDs and
  metadata. To/from protocol objects are preserved for UE's media message handling.
- Pinned [frontend controller](https://github.com/EpicGames/PixelStreamingInfrastructure/blob/6b8cfb460bda09703e85178f1f77aa6faec9e890/Frontend/library/src/WebRtcPlayer/WebRtcPlayerController.ts)
  registers media handlers independently of input flags and sends initial settings
  and quality-control requests after receiving the protocol. It also sends I-frame
  requests. The new browser does not disable the data channel itself.

This explains why the source gate should preserve media setup; it is **not** a
first-frame acceptance claim. A later native smoke must verify it, without adding
blanket forwarding to fix any missing message.

Native delivery review also inspected
`Engine/Source/Runtime/Engine/Private/PlayerController.cpp` and
`Engine/Source/Runtime/Engine/Private/UserInterface/PlayerInput.cpp` from the same
installed engine. APlayerController can reject before PlayerInput on device-user
filtering. UPlayerInput can record a digital sample and return whether a mapped
action handled it; analog input normally records and returns false. Therefore the
sink requires its original valid PlayerInput and observes the sample accumulator
change; it does not mistake the consumption boolean for delivery. Failed release
retains held bookkeeping and cannot return an applied ACK. Successful disconnect
clears only bridge-owned key state and pending deltas/events before ACK, while
ordinary move-zero preserves unrelated E/P/M pulses.

UE stores pressed/released event accumulators separately, copies both into event
counts during ProcessInputStack, and WasJustPressed checks the pressed count rather
than the final held state. The project's `MikdashCinematics.cpp` polls
`WasInputKeyJustPressed(EKeys::AnyKey)` for intro skip. An E press/release within one
frame therefore remains visible to that poll after input processing; the staged
native test explicitly exercises this path. Native host tick ordering before input
processing and actual project runtime behavior remain pending native acceptance.

Review corrections are retained in source and regression tests: synchronous close
callback reentry, stale close versus replacement allocation, high-rate pointer
coalescing, input before readiness, late ACK before timer dispatch, missing native
PlayerInput, release bookkeeping, and stationary-touch heartbeat. Receipt 01 is
preserved as prior evidence; receipt 02 supersedes its changed source hashes.

## One next deliverable: authenticated local host-to-native vertical path

Complete the matching loopback UE IPC receiver and process/bootstrap/host wiring,
then separately authorize a native build and local real-video acceptance. The
receiver must bind only literal loopback, authenticate a per-process 32-byte key
delivered through a private bootstrap channel (never command line/URL/log), verify
length and HMAC before JSON decoding, reject duplicate JSON fields and nonfinite
numbers, and restrict one outstanding command per owned process. Wire layout is
4-byte big-endian body length, canonical ASCII JSON bytes, 32-byte HMAC; MAC domain
is `mikdash-request-v1\0` or `mikdash-response-v1\0` followed by exact body bytes.
ACK JSON exactly echoes version, full owner, sequence, operation, connection_id and
`status: applied`, with no event, credential or free-text error.

Install `FOnlineInputGate` before exposing signalling. Establish a conservative,
immutable native deadline by authenticated clock-domain handshake; do not compare
Python monotonic values directly with FPlatformTime. Bind the typed SessionBridge
only after that handshake. Use bounded game-thread work (including paused state),
ACK after application, retry cleanup only with new sequence, and preserve failed
cleanup capacity until stream release/process disposal is proven. The source slice
does not implement this receiver/handshake, Windows owned-process acquisition,
crash recovery, native packaging, Node/Python RPC or authenticated browser upgrades.

## Offline verification

From `OnlineWalkthrough`, using the already populated isolated cache:

```powershell
node adapters/build.mjs C:/Mikdash/OnlineWalkthrough-cache/real-stream-6b8cfb
node --test signalling/gateway.test.mjs browser/controls.test.mjs
python -B -m unittest -v test_session_core adapters.test_bridge adapters.test_loopback_channel native.test_source_contract
python -B adapters/validate_slice.py --cache C:/Mikdash/OnlineWalkthrough-cache/real-stream-6b8cfb --receipt adapters/receipt-real-stream-source-02.json
```

The receipt command refuses overwrite and records source hashes, aggregate results
and limitations, not test payloads or secret material. All previous core receipts
are preserved. Native source checks require the inspected installed UE headers.
