# Local authenticated transport source candidate

This additive candidate composes readiness01, adoption01, possession03, flight01
and the real owned media transport over the published ue_integration02 base.
It is a **local end-to-end source milestone**, not an accepted running stream or
online service. UE/UHT/API compilation, TLS handshakes, sockets, native input,
video, audio and mobile usability have not been executed for this candidate.

The implemented path is:

1. `entry.mjs` POSTs same-origin `/session`. `server.py` invokes the actual
   allocated host, which provisions the owned Windows Job/private bootstrap and
   checks the one-shot stopped-admission event. Stopped admission is not media
   readiness. `FlightAuthority.attach` performs authenticated native open/bind.
2. `gateway.py` allocates one route and sends its one-use native ticket through
   the existing HMAC IPC channel. Owner, process generation, core connection and
   the immutable private deadline remain bound. The browser receives only its
   route/stream IDs and a Secure/HttpOnly/SameSite cookie scoped to that route.
3. The composed `Bootstrap::AttachOwnedMedia` supplies the actual parsed lease
   and Authority to the project-local RTC adapter. It adopts only a stopped,
   factory-proven streamer into a newly created private conference. The native
   WebSocket sends the ticket in an Authorization header, never its URL.
4. The gateway checks the retained child PID/creation/generation and ticket before
   native upgrade. Player/control upgrade requires the matching route cookie and
   exact origin. Only that stream can be listed or subscribed; no default/fallback.
5. Entry opens control before mounting the real pinned Epic frontend. Native
   registration pushes one owned streamer list to an already attached player:
   upstream `WaitForStreamer` does not retry with `MaxReconnectAttempts=0`.
   Controls remain inactive until the frontend connection event.
6. Gameplay uses the direct Python FlightAuthority/SessionCore path and native
   semantic consumption ACKs. A flight transition releases the old binding,
   establishes a fresh binding/generation and ACKs that exact handoff. Old input,
   queued look and held movement are not replayed. Media keeps the same owner and
   immutable lease. Native data-channel gameplay remains gated.

`application.py` constructs the real host and transport, with a required deployment
premise provider and TLS context. It never substitutes an affirmative lease.
Construction/import starts nothing. Future reviewed execution explicitly calls
`server.gateway.host.prepare()` and `server.serve()`, with `server.close()` in a
finally block. No executable default recipe, generated TLS trust, startup script
or implicit launch is supplied.

The additive `integrity.py`/`host-pins.json` replaces only historical author-path
source verification in transport preparation. Gauss confirmed that the settings
publication replay did not supply a portable production prepare/probe path.
The exact published settings02 manifest is restored at its real predicate loader's
relative path; the Win32 predicate, settings03 admission, settings05 lease,
settings06 allocator and process04 cleanup code remain exact Git dependencies.
`TransportProcesses.prepare` verifies that complete portable source set before
delegating to the existing executable verification. This is not a new ownership
premise or an assertion that deployment isolation has been established.

`plugin_recipe.py` pins installed UE 5.8.2 CL56702186. Its private `local_clone`
copies source only, adds the author-owned RTC adapter and references the exact
installed EpicRtc library; it never copies that binary. It changes no installed
engine files or global socket callbacks. Stock factory creation/recreation is
preserved; weak exact-instance provenance does not impose a stock creation cap.
The cap of 64 applies only to owned adoption attempts. Null scope matching refuses
before dereference. Teardown snapshots owned objects before callbacks, refuses new
owned adoption during shutdown, and stops/releases only its exact adopted scope.

`materialize.py` creates a fresh private licensed plugin build tree from an exact
portable export. Generated engine implementation is **not publishable**. The
receiver module explicitly depends on `PixelStreaming2RTC`; existing UHT targets,
real project controller/pawn/movement code, GameMode and isolated Blueprint
validation remain in the composed closure. Guarded compilation still requires
9 GiB free commit, a 4 GiB child cap, a 2 GiB reserve and cleanup within the total
deadline. Inspect the new RTC objects as well as existing production/UHT objects.

## Bounds and acceptance limits

- Host admission and raw-QPC attachment deadlines are separate. Only durations
  are compared across them, with an earlier QPC sample and a 2 ms margin. The
  original native deadline and owner expiry are never renewed. Both bounds are
  rechecked after exchange/authentication callbacks. Frozen bootstrap still
  rejects unproved clock mappings; shifted-clock gateway tests do not claim that
  shifted native bootstrap is supported.
- Five-second attachment window, native lifetime bound, one-use upgrade ticket,
  route count at host capacity; at most `3 * capacity + 4` transport workers.
  HTTP header limit 16 KiB/2 seconds; body exactly `{}`; masked WebSocket text
  frames at most 64 KiB with a shared 0.5-second partial-frame deadline. No binary,
  fragmented, compressed or alternate-subprotocol frames. Native and browser
  stock framing compatibility remains an actual runtime acceptance check.
- Control admission to the host lock is limited to 0.25 seconds. Expired queued
  frames cancel their route, rather than becoming newly authorized after a stall.
  The actual native synchronous consumption adapter still enforces its own bounds.
- Closing/cancellation precedes callbacks. Failed Job, peer or handle cleanup
  retains capacity. A Python socket-close error is quarantined, not portrayed as
  a recoverable retained OS descriptor. Opaque native calls and frame stalls still
  require the owned Job's hard lifetime/cleanup enforcement.
- TLS certificate/trust for `127.0.0.1` must be supplied and verified normally by
  both browser and native UE. There is no certificate-validation bypass. The
  application logs no request headers, bodies, SDP, private bootstrap or tokens.
- The authored look policy remains 0.3 degrees per CSS pixel, not UX-accepted.
  Reset/photo actions have not been guessed from console commands.

## Offline replay

The candidate publication manifest identifies each unchanged dependency by exact
Git commit/path/blob and each additive file by SHA-256. Export to a fresh tree,
then run its `runtime_transport01/replay.py` with an isolated pinned upstream cache
and explicit Node executable. Replay opens no listener and starts no UE or process
host. Its short-lived Python test child uses stdio only, exits after the bounded
byte-adapter flow, and creates no native child or socket. Browser tests use the
actual bundled entry/main and official frontend against actual Python HTTP,
gateway/core/flight code, with explicit DOM, WebSocket byte and native adapters.
They are not WebRTC or rendered-media evidence. Historical standalone C++ evidence
is retained separately and is not reclassified as UE compilation.

## Remaining remote delivery contract

The server, native URL, Host/Origin checks and CSP intentionally bind to
`127.0.0.1`. Independent local routes do **not** establish independent remote phone
visitors. Public HTTPS origin/reverse-proxy routing must preserve exact allocation
and cookie isolation, protect the private native upgrade, and define its trusted
proxy boundary. Real ICE reachability and STUN/TURN policy, credentials, firewall,
bandwidth/admission limits and desktop/mobile media/input acceptance remain to be
reviewed. No hosting service, payment, public port or network exposure is enabled.
