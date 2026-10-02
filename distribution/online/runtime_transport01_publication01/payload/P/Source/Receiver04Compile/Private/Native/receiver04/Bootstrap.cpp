#include "Bootstrap.h"
#include "MikdashOwnedRtc.h"
#include "../../runtime_candidate04/ServicedStoppedOwner.h"
#include "../../runtime_interaction01/RemoteResidentInteraction.h"
#include "BootstrapGuards.h"
#include "../../runtime_adoption01/ParsedAdmission.h"
#include "Misc/CoreDelegates.h"
#include "GameFramework/PlayerInput.h"
#include "Engine/World.h"

namespace MikdashOnline::Receiver04 {
Bootstrap::~Bootstrap(){Shutdown();FCoreDelegates::OnBeginFrame.Remove(TickHandle);}
bool Bootstrap::AdoptStopped(TSharedRef<const Adoption01::FParsedAdmission> Parsed,
    AReceiver04Controller* C,TSharedPtr<IPixelStreaming2Streamer> S,TSharedPtr<FOnlineInputGate> ExistingGate) {
    check(IsInGameThread());
    if(Busy||Stopping||Lifecycle.Get()!=Adoption01::AdoptionState::Phase::Empty)return false;
    if(!Parsed->Live()||!Route.Begin(Receiver03::QpcSeconds(),Parsed->StartupDeadline(),Parsed->Deadline(),Parsed->Identity().expires_at,Parsed->Generation())||
       !Lifecycle.Begin(Receiver03::QpcSeconds(),Parsed->StartupDeadline(),Parsed->Identity().expires_at)||
       !IsValid(C)||!C->PlayerInput||!IsValid(C->GetPawn())||!S.IsValid()||!ExistingGate.IsValid()||
       S->GetId()!=UTF8_TO_TCHAR(Parsed->Identity().stream_id.c_str())||S->IsConnected()||S->IsStreaming()||
       S->GetInputHandler().Pin()!=ExistingGate) {Shutdown();return false;}
    Admission=Parsed;Controller=C;Streamer=S;Gate=ExistingGate;
    const TWeakObjectPtr<AReceiver04Controller> ExpectedController=C;
    const TWeakObjectPtr<APawn> ExpectedPawn=C->GetPawn();
    const TWeakObjectPtr<UPlayerInput> ExpectedInput=C->PlayerInput.Get();
    const TWeakObjectPtr<UWorld> ExpectedWorld=C->GetWorld();
    const TWeakObjectPtr<UPawnMovementComponent> ExpectedMovement=ExpectedPawn->GetMovementComponent();
    Pawn=ExpectedPawn;PlayerInput=ExpectedInput;World=ExpectedWorld;Movement=ExpectedMovement;
    const auto RetainedAdmission=Parsed;
    Service=MakeShared<Authority>(Parsed->Config(),1,2,[](){return Receiver03::QpcSeconds();},Parsed->Generation());
    Service->OnLifecycle=[this](const Packet& P){return AuthenticatedLifecycle(P);};
    Service->OnInput=[this](const Packet& P){return ConsumersBound&&Admission.IsValid()&&Admission->LiveLease()&&Route.Input(Receiver03::QpcSeconds(),P.process_generation,P.connection_id);};
    const auto RetainedService=Service; // callback detach/reentry cannot destroy old authority
    auto StillOwned=[&]() {
        return !Stopping&&Admission.Get()==&RetainedAdmission.Get()&&Service==RetainedService&&!RetainedService->IsClosed()&&
            Lifecycle.Check(Receiver03::QpcSeconds())&&RetainedAdmission->Live()&&
            ExpectedController.IsValid()&&ExpectedWorld.IsValid()&&ExpectedMovement.IsValid()&&
            Controller==ExpectedController&&Controller->GetWorld()==ExpectedWorld.Get()&&
            ExpectedPawn.IsValid()&&ExpectedPawn->GetWorld()==ExpectedWorld.Get()&&
            ExpectedPawn->GetMovementComponent()==ExpectedMovement.Get()&&
            BootstrapTargetsValid(ExpectedController,ExpectedPawn,ExpectedInput,S,Parsed->Deadline(),[](){return Receiver03::QpcSeconds();})&&
            !S->IsConnected()&&S->GetInputHandler().Pin()==ExistingGate&&!Stopping&&
            Lifecycle.Check(Receiver03::QpcSeconds());
    };
    Busy=true;
    const bool Bound=[&]() {
        if(!StillOwned())return false;
        auto Settings=Settings05::MakeOwnedSettingsCallback(Parsed->Identity(),C);
        if(!Settings()||!StillOwned())return false; // real lease predicate, then fresh callback fence
        if(!Cast<UReceiver04WalkerMovement>(ExpectedMovement.Get())&&!Cast<UReceiver04DoveMovement>(ExpectedMovement.Get()))return false;
        // Gameplay ConfigureRemote remains behind a future authenticated route
        // activation capability, including its explicitly reviewed look scale.
        // Do not guess a scale or install consumers merely because parsing passed.
        Server=MakeUnique<Receiver>(*RetainedService);
        if(!Server->Start(Parsed->Config().Port)||!StillOwned())return false; // future reviewed game launch only
        return StillOwned()&&Lifecycle.Commit(Receiver03::QpcSeconds());
    }();
    Busy=false;
    if(!Bound||Stopping){RetainedService->Abort();Shutdown();return false;}
    TickHandle=FCoreDelegates::OnBeginFrame.AddRaw(this,&Bootstrap::Poll);
    if(!IsOwnedRouteLive()){Shutdown();return false;}
    return true;
}
bool Bootstrap::IsOwnedRouteLive() {
    check(IsInGameThread());
    return !Stopping&&!Busy&&Lifecycle.Get()==Adoption01::AdoptionState::Phase::Stopped&&
        Route.Live(Receiver03::QpcSeconds())&&Admission.IsValid()&&Admission->LiveLease()&&
        World.IsValid()&&Movement.IsValid()&&Controller.IsValid()&&Pawn.IsValid()&&
        Controller->GetWorld()==World.Get()&&Pawn->GetWorld()==World.Get()&&
        Pawn->GetMovementComponent()==Movement.Get()&&
        PlayerInput.IsValid()&&Controller->PlayerInput==PlayerInput.Get()&&Controller->GetPawn()==Pawn.Get()&&
        Pawn->GetController()==Controller.Get()&&Controller->IsLocalController()&&
        Service.IsValid()&&!Service->IsClosed()&&Streamer.IsValid()&&
        (MediaStarted||(!Streamer->IsStreaming()&&!Streamer->IsConnected()))&&Gate.IsValid()&&Streamer->GetInputHandler().Pin()==Gate;
}
void Bootstrap::Poll() {
    check(IsInGameThread());if(Busy)return;
    if(!IsOwnedRouteLive()){Shutdown();return;}
    const auto Retained=Service;Retained->Maintain();
    if(Stopping||Retained->IsClosed()||!IsOwnedRouteLive())Shutdown();
    if(!Stopping&&Server)Server->Tick(); // real authenticated semantic IPC, no media activation
}
// Inserted into the actual Receiver04::Bootstrap implementation.
bool Bootstrap::AuthenticatedLifecycle(const Packet& P) {
    // Authority invokes this ONLY after request HMAC, exact Owner, generation,
    // sequence and operation/connection-state checks. No external auth predicate.
    if(Stopping||Busy||!Admission.IsValid()||!Admission->LiveLease()||
       P.process_generation!=Admission->Generation()||!(P.owner==Admission->Identity()))return false;
    const auto Retained=Service;
    if(!Retained.IsValid()||Retained->IsClosed()||!IsOwnedRouteLive())return false;
    if(P.operation=="open")return Route.Open(Receiver03::QpcSeconds(),P.process_generation);
    if(P.operation=="release")return Route.Release(Receiver03::QpcSeconds(),P.process_generation,P.connection_id);
    if(P.operation=="close"){Route.Abort();return true;}
    if(P.operation=="stream")return AttachOwnedMedia(P);
    if(P.operation!="bind")return false;
    if(!Route.Bind(Receiver03::QpcSeconds(),P.process_generation,P.connection_id))return false;
    if(ConsumersBound)return Controller.IsValid()&&Controller->RemotePossessionCurrent()&&IsOwnedRouteLive();
    const auto C=Controller;const auto PinnedPawn=Pawn;const auto PinnedMovement=Movement;
    const auto PinnedInput=PlayerInput;const auto PinnedWorld=World;
    auto Current=[&]() {
        return !Stopping&&Admission.IsValid()&&Admission->LiveLease()&&Service==Retained&&!Retained->IsClosed()&&
            C.IsValid()&&PinnedPawn.IsValid()&&PinnedMovement.IsValid()&&PinnedWorld.IsValid()&&
            Controller==C&&Pawn==PinnedPawn&&Movement==PinnedMovement&&PlayerInput==PinnedInput&&World==PinnedWorld&&
            C->GetWorld()==PinnedWorld.Get()&&PinnedPawn->GetWorld()==PinnedWorld.Get()&&
            PinnedPawn->GetMovementComponent()==PinnedMovement.Get()&&
            BootstrapTargetsValid(C,PinnedPawn,PinnedInput,Streamer,Admission->Deadline(),[](){return Receiver03::QpcSeconds();})&&
            Route.Input(Receiver03::QpcSeconds(),P.process_generation,P.connection_id);
    };
    Busy=true;
    const bool Bound=[&]() {
        if(!Current())return false;
        auto Settings=Settings05::MakeOwnedSettingsCallback(P.owner,C.Get());
        if(!Settings()||!Current())return false;
        auto Interact=[C,Retained](const SemanticMailbox::Fence& Fence)->Outcome {
            return C.IsValid()?Interaction01::ConsumeResidentInteraction(*C.Get(),Retained.ToSharedRef(),Fence):Outcome::Rejected;
        };
        if(!C->ConfigureRemote(Retained,Settings,Interact,Activation01::LookDegreesPerNormalizedUnit)||!Current())return false;
        bool MovementBound=false;
        if(auto* W=Cast<UReceiver04WalkerMovement>(PinnedMovement.Get()))MovementBound=W->ConfigureRemote(Retained,C.Get());
        else if(auto* D=Cast<UReceiver04DoveMovement>(PinnedMovement.Get()))MovementBound=D->ConfigureRemote(Retained,C.Get());
        return MovementBound&&Current();
    }();
    Busy=false;
    if(!Bound||Stopping){Retained->Abort();Route.Abort();return false;}
    const TWeakPtr<Bootstrap> WeakSelf=AsShared();
    C->OnOwnedPossessionBegin=[WeakSelf](const TSharedPtr<Authority>& S) {
        const auto Self=WeakSelf.Pin();return Self.IsValid()&&Self->BeginOwnedPossession(S);
    };
    C->OnOwnedPossessionCommit=[WeakSelf](const TSharedPtr<Authority>& S) {
        const auto Self=WeakSelf.Pin();return Self.IsValid()&&Self->CommitOwnedPossession(S);
    };
    ConsumersBound=true;return true;
}

// Executed only by private controller hooks installed for this exact Service.
bool Bootstrap::BeginOwnedPossession(const TSharedPtr<Authority>& S) {
    if(PossessionPending||!ConsumersBound||S!=Service||!IsOwnedRouteLive()||
       !Controller->RemotePossessionCurrent())return false;
    PossessionBefore=S->BoundContext();
    if(!PossessionBefore.pawn||PossessionBefore.generation>=9007199254740990ULL)return false;
    PossessionPending=true;return true;
}
bool Bootstrap::CommitOwnedPossession(const TSharedPtr<Authority>& S) {
    check(IsInGameThread());
    const bool WasPending=PossessionPending;PossessionPending=false; // one-shot, before any validation
    if(!WasPending||Stopping||Busy||!ConsumersBound||S!=Service||!S.IsValid()||S->IsClosed()||
       !Admission.IsValid()||!Admission->LiveLease()||!Route.Live(Receiver03::QpcSeconds())||
       !Controller.IsValid()||!World.IsValid()||!PlayerInput.IsValid()||
       Controller->Remote!=S||!Controller->RemotePossessionCurrent()||
       Controller->GetWorld()!=World.Get()||Controller->PlayerInput.Get()!=PlayerInput.Get())return false;
    const Context After=S->BoundContext();
    if(After.controller!=PossessionBefore.controller||After.generation!=PossessionBefore.generation+1||
       After.pawn!=PossessionBefore.pawn+1)return false;
    // Only EndDoveTransition can commit. Its exact FlightWalker/FlightDove checks
    // and movement binding have already succeeded; never discover arbitrary pawns.
    const auto NextPawn=Controller->OwnedPawn;
    if(!NextPawn.IsValid()||Controller->GetPawn()!=NextPawn.Get()||
       NextPawn->GetController()!=Controller.Get()||NextPawn->GetWorld()!=World.Get())return false;
    const TWeakObjectPtr<UPawnMovementComponent> NextMovement=NextPawn->GetMovementComponent();
    bool Bound=false;
    if(auto* W=Cast<UReceiver04WalkerMovement>(NextMovement.Get()))Bound=W->OwnsRemote(S,Controller.Get(),NextPawn.Get());
    else if(auto* D=Cast<UReceiver04DoveMovement>(NextMovement.Get()))Bound=D->OwnsRemote(S,Controller.Get(),NextPawn.Get());
    if(!Bound)return false;
    // The old movement must have lost the authority even for rollback to walker.
    // A rollback rebinds that same object, so only demand detached state when it differs.
    if(Movement.IsValid()&&Movement!=NextMovement) {
        if(auto* W=Cast<UReceiver04WalkerMovement>(Movement.Get())) {if(W->HasRemote())return false;}
        else if(auto* D=Cast<UReceiver04DoveMovement>(Movement.Get())) {if(D->HasRemote())return false;}
        else return false;
    }
    Pawn=NextPawn;Movement=NextMovement;
    return IsOwnedRouteLive(); // all existing registry/world/input/gate/lease fences still apply
}

namespace {
class FActualRtcLease final : public UE::PixelStreaming2::IMikdashRtcLease {
    const TSharedRef<const Adoption01::FParsedAdmission> Admission;
    const TWeakPtr<Authority> Service;
public:
    FActualRtcLease(TSharedRef<const Adoption01::FParsedAdmission> A,TSharedPtr<Authority> S):Admission(A),Service(S){}
    bool Live()const override {
        const auto S=Service.Pin();
        return S.IsValid()&&!S->IsClosed()&&S->BoundOwner()==Admission->Identity()&&Admission->LiveLease();
    }
};
}
bool Bootstrap::AttachOwnedMedia(const Packet& P) {
    if(MediaStarted||!ConsumersBound||Stopping||Busy||!IsOwnedRouteLive()||
       !Admission.IsValid()||!Admission->LiveLease()||P.process_generation!=Admission->Generation()||
       !(P.owner==Admission->Identity())||!Route.Input(Receiver03::QpcSeconds(),P.process_generation,P.connection_id))return false;
    const auto Owned=MediaOwner.Pin();const auto Retained=Service;
    if(!Owned.IsValid()||!Retained.IsValid()||Retained->IsClosed()||P.action.size()!=64||
       P.y<=Receiver03::QpcSeconds()||P.y>Admission->Deadline())return false;
    UE::PixelStreaming2::FMikdashRtcIdentity I;
    I.Session=UTF8_TO_TCHAR(P.owner.session_id.c_str());I.Process=UTF8_TO_TCHAR(P.owner.process_key.c_str());
    I.Stream=UTF8_TO_TCHAR(P.owner.stream_id.c_str());I.Save=UTF8_TO_TCHAR(P.owner.save_prefix.c_str());
    I.Settings=UTF8_TO_TCHAR(P.owner.settings_slot.c_str());I.ProcessGeneration=UTF8_TO_TCHAR(P.process_generation.c_str());
    I.Connection=UTF8_TO_TCHAR(P.connection_id.c_str());I.QpcEnd=Admission->Deadline();I.OwnerEnd=P.owner.expires_at;
    const TSharedRef<const UE::PixelStreaming2::IMikdashRtcLease> Lease=MakeShared<FActualRtcLease>(Admission.ToSharedRef(),Retained);
    MediaStarted=true; // retain any partial acquisition BEFORE plugin callbacks
    const bool Attached=UE::PixelStreaming2::MikdashAttachOwnedRtc(Streamer,I,uint16(P.x),UTF8_TO_TCHAR(P.action.c_str()),P.y,Lease);
    const bool Current=!Stopping&&Admission.IsValid()&&Admission->LiveLease()&&Service==Retained&&!Retained->IsClosed()&&
        Route.Input(Receiver03::QpcSeconds(),P.process_generation,P.connection_id)&&Gate.IsValid()&&Streamer.IsValid()&&
        Streamer->GetInputHandler().Pin()==Gate;
    if(!Attached||!Current){UE::PixelStreaming2::MikdashRevokeOwnedRtc(Streamer);return false;}
    return Owned->StartAuthenticatedMedia(P.owner,int32(P.x))&&!Stopping&&Admission->LiveLease()&&
        Service==Retained&&!Retained->IsClosed()&&Route.Input(Receiver03::QpcSeconds(),P.process_generation,P.connection_id);
}

bool Bootstrap::Shutdown() {
    check(IsInGameThread());Stopping=true;Lifecycle.Abort();Route.Abort();PossessionPending=false;
    if(Controller.IsValid()&&Controller->Remote==Service) {
        Controller->OnOwnedPossessionBegin=nullptr;Controller->OnOwnedPossessionCommit=nullptr;
    }
    if(Service.IsValid()){Service->Abort();Service->OnLifecycle=nullptr;Service->OnInput=nullptr;}
    if(Busy)return false;
    UE::PixelStreaming2::MikdashRevokeOwnedRtc(Streamer);
    const bool Closed=!Server||Server->Shutdown();
    if(!Closed)return false; // owner retains quarantine, never frees failed server
    FCoreDelegates::OnBeginFrame.Remove(TickHandle);TickHandle.Reset();Server.Reset();
    Admission.Reset(); // copied bootstrap key wiped when final immutable capability releases
    return true; // exact streamer teardown remains with FServicedStoppedOwner
}
}
