# OnlineWalkthrough lifecycle core

`session_core.py` is a reusable, transport-independent Python 3.8+ server component.
It owns admission, session leases, attachment credentials, input authorization and
resource disposal. It uses only the standard library and opens no sockets, launches
no processes, and imports no Unreal or hosting libraries. The adapters in
`test_session_core.py` are test doubles; they are not part of the production core.

**Native/process and signaling/stream adapters and the browser client remain
unimplemented. This is not an online walkthrough, streaming proof, native control
acceptance, mobile usability result, or online delivery.** No production project,
package, plugin, security or network configuration is changed. No paid service is used.

## Integration contract

Create one `SessionCore(process_adapter, stream_adapter, limits, clock)` per exclusively
owned worker pool. The injectable clock defaults to `time.monotonic`; persisted wall
times must not be substituted. All public mutations are serialized by an RLock.
Same-thread adapter reentry is rejected. Adapters must not call the core or wait for
another thread to call it: callbacks run under that lock, and such a dependency would
deadlock. Crash notifications must be delivered independently after callbacks return.
Thread safety is within one Python process; this is not a distributed coordinator.

`ProcessAdapter.start(owner)` must acquire a dedicated, isolated process for exactly
`owner.process_key`, with that session's `save_prefix` and `settings_slot`. It must
track its exact owned process handle and partial allocations before doing work.
`stop(owner)` must be idempotent and return only when those resources are gone;
never terminate by executable name or trust a recycled PID alone. The future native
adapter must also isolate writable runtime/log/cache resources as needed: distinct
save names alone do not establish complete native process isolation.

`StreamAdapter.open(owner)` binds `owner.stream_id` exclusively to that process.
`send_input(owner, connection_id, event)` routes only to that owned binding.
`release_inputs(owner, connection_id)` clears held movement/buttons on disconnect;
`None` means clear every input belonging to that owner. `close(owner)` idempotently
revokes access and confirms all of that stream's resources are gone. Cleanup must
accept an ownership key even if start/open failed before acquiring anything.

Adapter methods must complete within a configured finite operational deadline in
the eventual adapter. Returning from start/open means acquisition is complete and
ready; returning from close/stop means disposal is confirmed, not merely queued.
The core cannot interrupt a hung adapter. Future native integration needs bounded
calls and an independent ownership watchdog using `owner.expires_at` (same monotonic
clock domain). Never reuse a core's pool after a crash without reconciling exact
old resource ownership. Recovery/persistence and that watchdog are not implemented.

## Public API and authentication

1. `request()` allocates a `Ticket(session_id, credential)`, or rejects a full queue.
   This creates a fresh identity; the HTTP/server layer must supply admission policy
   and per-client rate limits. Successful immediate provisioning reserves capacity
   before calling adapters. Otherwise admission is FIFO.
2. `status(session_id, credential)` returns state, connection presence, absolute
   expiry and queue position. Polling does not extend any deadline.
3. `connect(session_id, credential)` attaches only an active, disconnected session.
   It returns `Connection(session_id, connection_id, credential)` with a rotated
   credential. The ticket/previous credential is immediately invalid. There is
   no connected-session takeover, and only one concurrent reconnect can win.
4. `submit(connection, InputEvent(...))` checks the session-bound credential and
   current connection identity before dispatch. Old, disconnected and cross-session
   bindings are rejected. All input must traverse this authority: the eventual
   signaling/browser integration must not expose an unauthenticated direct-input
   path around it. The trusted server should bind `Connection` to its authenticated
   transport rather than accept browser-supplied ownership keys.
5. `disconnect(connection)` revokes the live binding before releasing input. Its
   rotated credential permits reconnect within the fixed grace period. Duplicate
   disconnect is rejected and cannot renew grace. A lost connect response is a
   fail-closed attachment: recovery requires expiry/new admission, not replay of
   the old credential.
6. `cancel(session_id, credential)` revokes/disposes or removes a queued request.
   Repeated cancellation is rejected after disposal. `report_crash(owner)` is a
   **trusted-adapter-only** notification with all ownership fields checked; stale
   notifications return false and cannot affect a replacement session.
7. Call `tick()` from a regular server scheduler even when no clients make requests.
   `shutdown()` disables admission and retries outstanding cleanup; repeat safely.
   `cleanup_pending()` reports quarantined slots for operator monitoring.

Credentials are random 256-bit bearer capabilities, bound to their session by
stored SHA-256 digests and constant-time comparison. Treat Ticket/Connection as
secret delivery objects: their repr is suppressed, but explicitly serializing
their fields WILL expose credentials. Return only to the intended authenticated
client over the future secure transport; never put them in logs, URLs or receipts.
The core provides no user identity authentication, HTTP, TLS or signaling service.

## Input semantics

`move(x, y)` and `look(x, y)` accept finite normalized axes in [-1, 1]. A zero move
releases movement. `interact`, `pause`, `reset`, `dove`, and `mute` are discrete
commands with zero axes. Other actions, nonfinite values and malformed payloads
are rejected. Desktop and mobile clients can share this semantic contract, but
the native adapter must implement and validate each mapping (especially reset),
and the browser must implement keyboard/mouse and touch ergonomics. None is
claimed implemented by this core. The core keeps no pending input queue; adapter
and transport backpressure/rate limits are future integration responsibilities.

## Bounds and failure behavior

Defaults: 1 occupied slot, 8 queued requests, 60-second queue wait, 20-second
attachment/reconnect grace, 900-second absolute lifetime and 128 retained events.
Counts are validated (maximum 10,000 each); durations must be finite, positive and
at most 86,400 seconds. Capacity must be set from later measured host limits.
No simultaneous native capacity is inferred from test adapters.

Absolute lifetime starts at admission after initial maintenance, includes queue time and cannot be extended
by activity or reconnect. Expiry is inclusive (`now >= deadline`). Admission,
authentication and input calls sweep expiry first, then check fresh time again
before authorizing the target and immediately before input dispatch/attachment.
Clock values must be in [0, 2**40 - 86400] seconds, nondecreasing; ownership expiry
must be in [0, 2**40]. This allows a full day's deadline headroom. Bounds are
checked with integer-safe comparisons before any floating-point operation;
huge integers, booleans, infinities and NaN are rejected with the API's documented
SessionError (or ValueError for Limits), never an accidental OverflowError.
No background scheduler is created; the host must schedule `tick()`
and enforce native leases independently if its event loop/core can stall.

Provisioning consumes absolute lifetime. Fresh checks before process acquisition,
after start and after stream open prevent expired queued work from starting,
expired processes from acquiring streams, and expired streams from becoming ready.
Initial attachment grace starts at actual readiness. Disconnect grace starts at
the fresh disconnect decision; a slow input-release callback consumes that grace
and cannot renew it. Input authorization is at dispatch time: adapters must still
enforce the owner's deadline at actual I/O if their own work delays delivery.

Sweeps use a fixed number of bounded passes, never a retry-until-stable loop.
The last pass only revokes sessions whose leases elapsed during callbacks.
Those newly CLOSING resources retain capacity and are disposed on the next sweep;
they cannot authenticate or receive input in the meantime. A target expired by a
final authorization check is likewise revoked and quarantined for the next sweep.

An input/release/provision failure revokes the session. Cleanup tries stream and
process disposal independently. A failure retains a noninteractive CLOSING slot,
not reusable capacity; later sweeps retry only unfinished disposal steps. Cleanup
does not silently forget a resource or free capacity just because a retry limit
was reached. Permanently broken adapters can therefore quarantine up to capacity
slots indefinitely; these are revoked ownership records, not renewable live leases.
Confirmed stream AND process destruction is sufficient even if input release failed.

Disposed/expired queue records are removed, not accumulated as unbounded tombstones.
Session/process/stream/save/settings identities use a random per-core namespace plus
a never-reused sequence. `events()` is a bounded diagnostic snapshot, not a durable
audit trail; only identity and fixed event-kind strings are retained. Arbitrary
adapter exception text and credentials are never retained in events.

## Validation and receipt

Run from this directory, without native launches or network access:

```powershell
python -B -m unittest -v test_session_core
python -B validate.py --receipt receipt-new.json
```

`validate.py` refuses to overwrite an existing receipt, pins source/test/document
hashes before and after the suite, and records test identifiers and aggregate
outcomes without exception messages, tokens or adapter state.
`receipt-time-validation-v2.json` is the current validation receipt.
`receipt.json` is preserved unchanged as prior evidence for the initial 38-test
revision; its source hashes are intentionally superseded, not current validation.
Tests cover real core transitions with
adapter doubles: concurrent admission/reconnect, in-flight input versus crash,
disconnect/input ordering, expiry races and boundaries, partial acquisition,
ownership mismatch, cross-session input, quarantine, repeated cleanup and shutdown.

### Review corrections, 2 October 2026

Independent verification found that an unrelated cleanup callback could advance
the injected clock from 100 to 111 while a target expired at 110, yet the original
submit path still dispatched input. Never carry a pre-callback timestamp across
adapter work as authorization. Regression tests now exercise fresh checks for
submit, connect, status, disconnect, queue admission and both provisioning stages,
plus deadline creation after maintenance and grace consumed by slow release.

Verification also found `math.isfinite(10**400)` raises OverflowError before the
intended input rejection. Check type and numeric bounds first, without converting
to float. Focused huge-integer tests cover input axes, all Limits fields, clock
and crash Ownership expiry. The current suite contains 55 tests.

## Publication boundary

This component is published under `distribution/online/`, separate from the book
application at `web/`. Its validation covers the lifecycle core only.
No package/plugin change should follow merely from green core tests. Native and
signaling adapters, browser controls, measured capacity, real independent sessions,
mobile/external-network checks and online delivery remain separate acceptance work.

## Stopped-streamer source checkpoint — 2 October 2026

`runtime_candidate01` through `runtime_candidate04` preserve the reviewed source
progression: owned stopped streamers, expiry handling, child-window rejection and
a process-local registry host. Candidate03 is retained as history; its top-level-only
window check was insufficient. Candidate04 rejects child windows as well.

This checkpoint adds40 exact source/metadata files and retains22 existing online
dependencies unchanged. All62 file hashes and four candidate manifests were checked;
the four `source_checks.py` programs pass42 checks in total. These are source-text
checks, not native execution. To reproduce them, run each candidate's
`python -I -B source_checks.py` from that candidate directory.

The frozen `verify.py` and source-context files retain absolute paths to the audited
workstation. They are historical provenance, not portable clone verification.
Do not report their success as a standalone UE build. Engine implementations,
generated UHT files, binaries, private session payloads and raw logs are excluded.

Seven actual Slate assertions remain uncompiled/unrun. The module is not installed
in the game; authenticated attachment, media activation and browser delivery are
still absent. Candidate05 parsing work is outside this frozen checkpoint. Existing
released maps, builds and network configuration are unchanged.

## Private provisioning source extension — 2 October 2026

`runtime_candidate05` adds bounded private-stdin parsing and stopped admission,
separate from listener or media activation. Its12 source/metadata files are exact;
all57 online dependencies match this publication. The27 external references are
provenance only and are not copied. Frozen absolute-path verifiers remain local
audit tools, not portable native-build evidence.

From this directory, run `python -I -B runtime_candidate05/test_bootstrap_record.py`
and `python -I -B runtime_candidate05/source_checks.py`:15 real Python preflight
tests and12 source checks. Independent source review additionally exercised seven
Windows-QPC Python cases. Ten native UE parser assertions remain uncompiled/unrun.
Python tests do not prove native parser or pipe behavior.

The private inherited handle from the reviewed launcher is the provisioning trust
root; record parsing does not authenticate an arbitrary parent. This revision emits
no ready acknowledgement and starts no listener or media. The existing host will
still time out waiting for readiness. Authenticated route attachment, gameplay and
settings isolation, native compilation and browser delivery remain unfinished.
