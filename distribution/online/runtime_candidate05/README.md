# Candidate05: private provisioning separated from activation

Implemented source, not installed in a project. Candidate04 remains unchanged for
Herschel review. No native/MSVC/UE, listener, media or child-process launch occurred.

PrivateBootstrapModule.cpp is a concrete alternative module entry point. It starts
the actual candidate04 registry host and polls the private input reader from the
engine frame loop. Compile RegistryHost.cpp but NOT RegistryHostModule.cpp alongside
this new entry point. No production module/config or approved compile closure was
changed. Required source dependencies and hashes are in source-context.json.

## What is authenticated, and what is not

The existing process04 protocol supplies a plaintext bootstrap through a private
inherited stdin capability. Its reviewed WindowsChild creates the pipe, marks only
the reader and NUL as inherited handles, creates the child suspended, assigns its
exact owned Job, closes parent reader copies, then resumes and performs a bounded
owned write. That reviewed launch chain is the trust root. Syntax parsing, pipe
type, inheritance flags, membership in some Job, or an HMAC made with a key inside
the same record cannot independently authenticate a parent. No such success is
invented here. Arbitrary-parent/direct/manual launches are outside this trust root.

The reader obtains only STD_INPUT_HANDLE; there is no public raw-byte admission
API. It requires a byte pipe with an inherited handle. These are structural checks,
not evidence of parent identity. State is named StoppedProvisioned, never
Authenticated/Connected/Ready-to-stream. No HMAC-ready ACK, listener, port bind,
streaming URL or StartStreaming operation exists. The frozen process04 host will
therefore still time out waiting for its authenticated ready response and clean up;
this revision does NOT satisfy end-to-end host/browser delivery.

## Implemented flow

- At most one startup; shutdown prevents reuse. Five-second raw-QPC read deadline,
  finite/backward-clock refusal, one read per frame, max 4092-byte body / 4096 frame.
  Header/body partial reads wait within that same bound. TRUE/zero read is pending.
- A full frame must be followed by writer EOF. Extra/trailing frames are refused.
  EOF before completion is failure. Successful CloseHandle is required BEFORE
  parsing/admission. A failed close retains and poisons the original handle via the
  reviewed Receiver04 CloseBootstrapInput helper; it is never retried or recycled.
- ValidatePrivateRecord calls the actual frozen Receiver03 ParseBootstrap, which
  rejects duplicate JSON keys, malformed shapes/types and invalid QPC domain. It
  adds fresh lifetime limits: now < deadline <= owner expiry, at most 24 hours.
  After parser/close/admission callbacks, fresh QPC checks reject late results.
- Only then is candidate04 AdmitStopped called with the parsed exact identity and
  deadline. Its registry/window/controller/movement/input-gate checks remain real.
  The private key/port remain in a private Bootstrap object until expiry/shutdown;
  there is no key accessor or activation consumer yet. Buffers and retained key are
  wiped on teardown. Frozen UE JSON parser temporaries are not guaranteed scrubbed;
  no comprehensive heap-secret-erasure claim is made.
- Shutdown revokes before callbacks, shuts down only a host successfully started
  by this instance, and retains failed-close quarantine. The outer owned-process
  host must retain capacity until exact process cleanup is proved. No retry/replay.

Native module startup currently has a five-second provisioning/admission budget
starting at module load. If the real controller, pawn, UHT classes or window are not
ready, stopped admission fails; it does not queue unboundedly or extend the record.
Choosing a supported loading phase/prepared world remains explicit integration work.

bootstrap_record.py is an additive production host preflight. make_private_record
calls the existing make_record and then checks the exact frame against the existing
allocation identity with a fresh clock sample. Use its output only with the reviewed
process04 WindowsChild.resume_and_write, never the obsolete synchronous preloaded
PrivateBootstrapPipe. It returns the same wire format and opens nothing. Existing
frozen host.py is not edited or automatically switched to it. inspect_private_record
returns metadata without a key or authentication flag; it is not a native trust API.

## Verification and limits

15 executed Python tests exercise the actual new host preflight and existing record
builder. 12 executed source checks inspect native branch/order contracts. Ten
native assertions in PrivateRecordTests.cpp call the actual UE parser/validator,
but are UNCOMPILED/UNEXECUTED. Native pipe EOF, inherited flags, close failures and
frame ordering have NOT been proved by these Python checks. No mock transport is
presented as native execution. Failed tests expose fixed errors, never record/key
contents; receipts contain hashes and counts only.

Preserved limits: stopped only; game-thread stalls postpone cleanup; stock capture
still needs exact-window filtering at the callback; foreign native modules cannot
be locked out of public PS2 APIs; explicit shutdown must precede Slate/module unload.
Hot reload is disabled. Quarantined module state must remain loaded until owned
process exit; the module shutdown hook cannot make arbitrary unload safe.

Next uncoded deliverable is a reviewed one-use authenticated attachment/activation
capability bound to this parsed process/session/stream/key and native deadline. It
must coordinate the actual authority/controller/movement and settings isolation,
authenticate the allocated signaling route, then activate only the exact receiver
and streamer. Neither parse success nor StoppedProvisioned can substitute for that
proof. Listener/media activation deliberately remains absent in this revision.
