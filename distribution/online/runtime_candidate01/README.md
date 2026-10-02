# Owned stopped PixelStreaming2 candidate01

New source only. No native/compiler/listener/media/engine launch; no modifications
to source04, Compile02, active project/plugin config or published online files.
This candidate is not yet compiled or wired into a module. The eight offline
source-contract checks are not C++ execution proof. Fourteen focused C++ ownership
cases instantiate the actual production StoppedLease policy but remain unexecuted.

## Actual implementation

OwnedStoppedStreamer.cpp/.h implements the installed UE port, not a mock streamer.
StoppedLease.h is its shared production lifecycle. Given an already-ready
IPixelStreaming2Module and owned UGameViewportClient, explicit Prepare:

1. Requires game-thread serialization, one non-PIE Game world/player/window and
   an immutable raw-QPC deadline within24h. All five Owner IDs are bounded ASCII.
   Owner.expires_at is compared for identity only, never treated as UE clock time.
2. Rejects the module default ID and any existing registry entry (including stale
   weak entries) BEFORE CreateStreamer. The module's CreateStreamer otherwise
   returns an existing object; it does not establish ownership by itself.
3. Calls CreateStreamer with explicit DefaultRtc, retains the returned exact
   pointer, verifies registry identity/type/stopped state, clears any inherited
   connection URL, and rechecks after callbacks with a fresh clock.
4. Retains the exact backbuffer producer already installed by the DefaultRtc
   factory. It does not create a duplicate capture callback. A missing producer
   fails preparation. BorrowStopped and Matches recheck identity, producer, scope,
   expiry and cancellation before returning the pointer/full-owner match.
5. Close detaches only its owned producer and calls DeleteStreamer(pointer), never
   DeleteStreamer(id). A replacement mapping survives. Reentrant Close requests
   return pending without recursion. Producer substitution, failed detachment or
   unresolved registry removal quarantines the lease. If observed active/connected,
   stop is requested only on its exact streamer and cleanup remains quarantined;
   asynchronous signaling teardown is not proved by public status booleans.

There is NO StartStreaming call and no module-wide start/stop. This is a stopped
setup lease; no authenticated route or media-start authority is granted. Engine
factory creation nevertheless registers real backbuffer callbacks, so Prepare is
a native/media-resource operation requiring later explicit launch authorization.
Constructor alone performs no engine operation.

## Preconditions and limits

All registry creation/removal must be exclusively serialized on the game thread
through the trusted process owner. This is not atomic reservation against arbitrary
third-party threads mutating the module registry. The pinned built-in DefaultRtc
factory must remain installed; the type string is not authentication of a plugin
that replaces that factory. This design does not defend against hostile in-process
code. Do not pass browser-supplied owners or return the borrowed pointer to clients.

The host must keep the module, Slate and lease alive until Close succeeds. On false,
retain the allocation/capacity until exact owned-process exit; do not destroy a
quarantined lease and claim native cleanup. There is intentionally no destructor
calling into an unloaded module. Bootstrap owns an additional streamer reference,
so shutdown order must be receiver Bootstrap.Shutdown first, then lease Close,
then discard aliases. Close proves detach/registry removal of the stopped resource,
not destruction of every external shared reference or all render-thread callbacks.

Stock backbuffer capture observes ALL Slate windows. The one-window check is made
at preparation/borrow, not continuously on the render thread. A future media-start
integration must enforce the scope continuously or use a window-filtered producer.
The candidate must never be promoted to multi-window/PIE or shared-process visitor
isolation based on these checks. Unexpected external StartStreaming is outside the
borrow contract; IsStreaming/IsConnected are not complete signaling-state proofs.
Setup expiry has no autonomous timer: the future host must tick/revalidate and
perform ordered receiver/lease shutdown. There is no new listener or tick hook here.

## Existing receiver interfaces and exact missing integration

- native/SessionBridge.h: Owner is session_id/process_key/stream_id/save_prefix/
  settings_slot/expires_at. Expected equality covers every field.
- native/receiver03/Wire.h: Bootstrap contains Identity, private Key, raw-QPC
  Deadline and Port. QpcSeconds is the clock used by this concrete port.
- native/receiver04/Bootstrap.h: Start takes an already-created stopped streamer,
  controller, SettingsProof(Owner), interaction outcome callback and look scale.
  It installs the frozen deny-all gameplay input gate, reads private stdin,
  compares streamer ID and calls SettingsProof with parsed full Owner.
- native/receiver04/Authority.h: owns the private identity/deadline/key; there is
  no public owner accessor. GetAuthority/IsReady are not streamer-route grants.

Future source wiring can prepare the lease from trusted host provisioning, obtain
BorrowStopped(Expected), and pass it to Bootstrap.Start. Its SettingsProof must
first call lease.Matches(ParsedOwner), then prove REAL settings ownership. A true
constant is forbidden: current project ToggleSound calls SaveConfig. The current
callback exposes Owner, not parsed native Deadline; setup deadline agreement and
ordered expiry must be specified in that future host/bootstrap revision. This
candidate does not silently extend the frozen bootstrap API or claim that seam is
already implemented. Bootstrap.Start itself opens the receiver later; never call
it in these offline checks. Missing next work also includes controller/movement
registration, interaction outcomes, authenticated streamer attach, signaling/RPC
host wiring and browser media. No URI credential or URL logging is introduced.

## Primary installed-engine evidence (UE5.8.2 CL56702186)

Paths below are relative to `C:/Program Files/Epic Games/UE_5.8/Engine/` and their
whole-file hashes are in source-context.json. Engine files are NOT copied.

- Plugins/Media/PixelStreaming2/Source/PixelStreaming2/Private/PixelStreaming2Module.cpp
  lines191–211: existing-ID return, Initialize, inherited connection URL, registry
  insertion; lines238–276: lookup and pointer-specific DeleteStreamer implementation.
- Plugins/Media/PixelStreaming2/Source/PixelStreaming2RTC/Private/EpicRtcStreamer.cpp
  lines2183–2189: DefaultRtc factory creates RTC input handler AND real backbuffer
  producer; lines48–75: Initialize does not start streaming; lines149–152 URL setter;
  lines225–250: StopStreaming is asynchronous when not already disconnected.
- Plugins/Media/PixelStreaming2/Source/PixelStreaming2/Private/VideoProducerBackBuffer.cpp
  lines13–34: Slate check and callback registration; lines37–48 cleanup;
  lines50–53: frame push for the provided Slate window, with no ownership filter.
- Plugins/Media/PixelStreaming2/Source/PixelStreaming2/Private/VideoCapturer.cpp
  lines56–69: producer replacement removes/adds the exact frame delegate.
- Plugins/Media/PixelStreaming2/Source/PixelStreaming2Core/Public/IPixelStreaming2Streamer.h:
  SetVideoProducer/GetVideoProducer, SetConnectionURL and per-stream stop interfaces.
- Source/Runtime/Engine/Classes/Engine/Engine.h:2702 and GameViewportClient.h:362;
  Source/Runtime/Slate/Public/Framework/Application/SlateApplication.h:1688:
  actual viewport/player/window APIs used by this candidate.

## Focused checks

`python -I -B source_checks.py -q` performs eight source-contract checks only.
OwnershipTests.cpp contains14 staged cases: existing/stale/default IDs, exact
producer retention, idempotent close, foreign replacement survival, synchronous
creation/removal reentry, missing producer, expiry inside callback, producer
substitution, external activation quarantine, full-owner refusal, failed detach,
and oversized identity/deadline refusal. They exercise the same template instantiated
by FOwnedStoppedStreamer; the fake port is only the test adapter. No UE behavior is
inferred from them, and no C++ tests have run. Later coordinator-approved compile
review may add these new files to a NEW isolated revision; Compile02 is untouched.
