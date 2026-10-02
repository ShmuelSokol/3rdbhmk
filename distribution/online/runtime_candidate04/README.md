# Candidate04: process-local stopped registry host

Source implementation, not installed or UE-compiled. No native, listener, media,
build or process launch was performed. Candidate01/02/03 and frozen Receiver04
remain byte-identical. Fourteen Python source-control-flow contracts pass; these do
not prove UE delegate ordering or runtime behavior.

RegistryHostModule.cpp contains actual StartupModule/ShutdownModule entry points
and disables dynamic reload. Startup installs real OnBeginFrame, OnEnginePreExit
and OnWorldCleanup delegates, starts a five-second admission window using raw QPC,
and permits only one process-local host incarnation. AdmitStopped is a one-shot
trusted in-process allocation entry point. There is no public streamer getter,
signaling URL setter, media activation, receiver Start, or authenticated-attachment
API. Thus no branch of THIS host accepts a connection before authentication;
authenticated attachment is not implemented and all connections remain unavailable.

Admission requires PS2 already loaded/ready, both InitializeDefaultStreamer and
AutoStartStream CVars present and zero, and an entirely empty registry, including
no stale IDs. It never edits CVars or deletes foreign streamers. It requires the
actual Receiver04 controller, initialized PlayerInput, owned pawn and Receiver04
walker/dove movement component. It constructs a fresh private Receiver04 Bootstrap,
the new child-window-aware serviced stopped owner, then installs the actual deny-input
gate before declaring StoppedReady. Registry, pawn/controller identity and gate
identity are monitored each frame. The new owner reuses unchanged candidate03 ExpiryWatch and continues QPC/window/world/producer
expiry enforcement. Nested shutdown revokes admission before cleanup callbacks.

Shutdown goes through the new serviced owner (receiver first, then owned streamer) and removes
host delegates only after confirmed cleanup. Failure retains the process-local
allocation permanently; admission never reopens. Exact owned-process exit remains
the external proof for releasing quarantined session capacity. Explicit shutdown
must precede Slate/PS2 unload; the pre-exit delegate is fallback only. If PS2 is
already unloaded, this host quarantines without calling its stale module reference.
The serviced owner's own registered callback still requires the same ordered-unload
contract. No host can safely continue after arbitrary module code unload.

Exclusive ownership boundary: the singleton serializes callers using THIS host and
refuses foreign/default registry contents. The engine exposes public CreateStreamer
and StartStreaming APIs to other native modules: this code cannot revoke those APIs
or prevent an arbitrary foreign module from writing between polls. The dedicated
child's module closure must exclude competing startup/Blueprint/console writers.
Violations are detected and fail closed at the next check; this is not a process-wide
engine lock or a render-thread boundary. No capture/media acceptance is claimed.

## Installed startup audit and uncoded integration

- Installed PixelStreaming2Module.cpp registers OnAllModuleLoadingPhasesComplete,
  sets bModuleReady and broadcasts ReadyEvent BEFORE default streamer creation and
  optional AutoStartStream. Therefore OnReady alone does not prove exclusivity.
  This host reads the CVars and checks the registry after readiness on the frame
  loop. Automatic default creation/start must already be disabled by a separately
  reviewed launch profile before module startup; no profile was edited here.
- Active Plugins/MikdashRuntime/Source/MikdashRuntime/Private/MikdashRuntime.cpp
  starts/stops ContextMaterialFixture only. Its opt-in fixture owns its own map,
  ticker and screenshot delegates. It does not install online controller/movement.
  This new module is not yet in any uplugin/uproject/Build.cs or loading phase.
- Receiver04 OnlineController.h/.cpp and OnlineMovement.h/.cpp have actual UCLASS
  consumers but require real UHT/module integration. Walker needs a project pawn
  constructor replacing ACharacter::CharacterMovementComponentName with
  UReceiver04WalkerMovement while preserving the project's actual pawn behavior.
  No project pawn type is guessed or substituted here.
- MikdashDovePawn.cpp constructs the named FlightMovement default subobject as
  UMikdashDoveMovement. A reviewed subclass/default-subobject substitution is still
  needed. MikdashPlayerController.cpp hardcodes SpawnActor<AMikdashDovePawn> with
  AMikdashDovePawn::StaticClass; installing a subclass alone will not route flight
  into it. Possession changes also invalidate current Receiver04 authority and need
  a reviewed new ownership generation. Flight transition remains unsupported.
- Trusted private bootstrap admission remains uncoded: native Receiver04 Bootstrap
  couples stdin parsing to receiver listener startup, whereas this host needs the
  authenticated allocation identity/QPC bound before creating its stopped streamer.
  A reviewed split parser/admission handoff is required; a caller-supplied Owner is
  not authentication. The host deliberately never calls Bootstrap::Start.
- Authenticated allocated signaling route attachment, key/stream/process binding,
  filtered viewport capture, first-frame readiness and eventual StartStreaming are
  absent. No function here turns StoppedReady into connected/online delivery.
- Real settings/save isolation proof and consumed interaction outcome are absent.
  Existing M handling persists settings; do not provide a constant true proof.
- Actual module integration must compile candidate01 OwnedStoppedStreamer.cpp,
  candidate04 ServicedStoppedOwner.cpp, these two host .cpp files, Receiver03 Wire and
  the frozen Receiver04 closure in ONE compatible module (their UCLASS types lack
  cross-DLL export macros). Use the reviewed Core/CoreUObject/Engine/InputCore/
  ApplicationCore/InputDevice/Slate/SlateCore/Json/Sockets/MikdashRuntime/PS2/PS2Core/
  PS2Input dependencies and bcrypt. Add no duplicate startup implementation to
  MikdashRuntime. Module name here is OnlineRegistryHost; generated UHT units and
  its loading order still need compile-only review and resource admission.

Next concrete deliverable: split the existing private bootstrap parser from listener
activation in NEW receiver source, passing its validated one-use allocation and
native QPC bound into AdmitStopped. Keep listener/media activation unreachable until
the authenticated exact-route attachment implementation is reviewed.

See source-context.json for exact local primary source paths/hashes. No engine code
is copied or published. Closure verification is read-only via verify.py.

## Herschel child-window correction

Review receipt C:/Mikdash/Verification/expiry-review-rg2p5n8_/review-summary.json
SHA256 c7cf3b6c673168fa605da01327bb1b9c00c88e7b66d056f425f742f992faae9e
puts frozen candidate03 on HOLD for the top-level-only window claim. This revision
uses actual Slate GetTopLevelWindows plus actual SWindow::GetChildWindows. The
exact root must be the sole root AND have zero children, including hidden children.
Any grandchild necessarily has an immediate ancestor under the root, so refusing
all immediate children rejects the whole subtree without unbounded recursion.
Both pre-creation admission and every subsequent borrow/frame check use this rule.
Candidate01's independent lease still has its original top-level-only limitation;
it is not acceptable as a stand-alone window authority. This host uses the new
wrapper and never exposes the raw lease.

WindowHierarchyTests.cpp stages seven assertions against actual Slate SWindow
hierarchies (no replacement UE types): missing root, exact childless root, wrong
identity, child, grandchild, hidden child and multiple roots. These UE tests are
UNCOMPILED/UNEXECUTED. The 14 passing Python tests check source contracts only.
No MSVC/UE work was run during the coordinator's native compile slot.

This corrects persistent child-window admission, not transient rendering races.
The stock producer remains unfiltered, so media must stay stopped. Engine frame
stalls still postpone enforcement until service resumes; the unchanged expiry
policy refuses a gap over 0.5 seconds. Real media still requires callback-level
exact-window filtering and a separately reviewed authenticated attachment path.
