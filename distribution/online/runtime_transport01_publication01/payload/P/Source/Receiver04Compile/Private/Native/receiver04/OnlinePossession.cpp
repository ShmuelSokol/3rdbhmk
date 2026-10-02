#include "OnlineController.h"
#include "OnlineMovement.h"
#include "GameFramework/PlayerInput.h"
#include "Engine/World.h"
#include "../../runtime_possession01/OnlinePawnBases.h"

using namespace MikdashOnline::Receiver04;
namespace {
bool RealWalker(APawn* P) {
    return IsValid(P) && P->GetClass()->GetPathName()==
        TEXT("/Game/MikdashV3/Gameplay/BP_MikdashWalker.BP_MikdashWalker_C") &&
        Cast<ACharacter>(P) && Cast<UReceiver04WalkerMovement>(P->GetMovementComponent());
}
}
UClass* AReceiver04Controller::DoveClassForFlight() const {
    return AReceiverPossessionDove::StaticClass();
}
bool AReceiver04Controller::SupportedInitialWalker() const { return RealWalker(GetPawn()); }
bool AReceiver04Controller::AcceptDoveSpawn(AMikdashDovePawn* P) {
    if(!Remote.IsValid()) return true;
    if(!FlightTransition || !IsValid(P) || P->GetOwner()!=this ||
       P->GetClass()!=AReceiverPossessionDove::StaticClass() || FlightDove.IsValid()) {
        Remote->Abort();return false;
    }
    FlightDove=P;return true;
}
bool AReceiver04Controller::RemotePossessionCurrent() const {
    return IsValid(this) && Remote.IsValid() && !Remote->IsClosed() && !FlightTransition &&
        OwnedPawn.IsValid() && GetPawn()==OwnedPawn.Get() && OwnedPawn->GetController()==this &&
        IsLocalController() && IsValid(PlayerInput.Get()) &&
        (RealWalker(OwnedPawn.Get()) ||
         (OwnedPawn->GetClass()==AReceiverPossessionDove::StaticClass() &&
          OwnedPawn->GetOwner()==this && Cast<UReceiver04DoveMovement>(OwnedPawn->GetMovementComponent())));
}
void AReceiver04Controller::DetachRemoteMovement() {
    if(OwnedPawn.IsValid()) {
        auto* M=OwnedPawn->GetMovementComponent();
        if(auto* W=Cast<UReceiver04WalkerMovement>(M)) W->DetachRemote();
        else if(auto* D=Cast<UReceiver04DoveMovement>(M)) D->DetachRemote();
    }
    OwnedPawn.Reset();
}
bool AReceiver04Controller::BeginDoveTransition() {
    if(FlightTransition) return false;
    // Local project play before authenticated bootstrap retains its normal path.
    if(!Remote.IsValid()) return true;
    if(!RemotePossessionCurrent()) { Remote->Abort();return false; }
    if(!IsDoveFlightActive()) {
        if(!RealWalker(GetPawn())) { Remote->Abort();return false; }
        FlightWalker=GetPawn();
        FlightDove.Reset();
    } else if(!FlightWalker.IsValid()) { Remote->Abort();return false; }
    // Before spawn/Possess/callbacks: invalidate old fences and require release
    // followed by fresh bind. An in-flight unknown outcome closes the authority.
    const TSharedPtr<Authority> S=Remote;
    const TWeakObjectPtr<AReceiver04Controller> Self(this);
    const auto OldPawn=OwnedPawn;
    const auto Begin=OnOwnedPossessionBegin;
    if(!Begin||!Begin(S)||!Self.IsValid()||Remote!=S||S->IsClosed()||
       !RemotePossessionCurrent()||OwnedPawn!=OldPawn) {S->Abort();return false;}
    if(!S->BeginPossession()||!Self.IsValid()||Remote!=S||S->IsClosed()) {S->Abort();return false;}
    FlightTransition=true;
    DetachRemoteMovement();
    if(!Self.IsValid()||Remote!=S||S->IsClosed()||!FlightTransition){S->Abort();return false;}
    return true;
}
void AReceiver04Controller::OnUnPossess() {
    if(Remote.IsValid()) {
        if(!FlightTransition) Remote->Abort();
        DetachRemoteMovement();
    }
    Super::OnUnPossess();
}
void AReceiver04Controller::OnPossess(APawn* P) {
    // Unexpected possession is not a way to acquire authenticated input.
    if(Remote.IsValid() && !FlightTransition) { Remote->Abort();DetachRemoteMovement(); }
    if(Remote.IsValid() && FlightTransition &&
       (!IsValid(P) || (P!=FlightWalker.Get() && P!=FlightDove.Get()))) Remote->Abort();
    Super::OnPossess(P);
    // The project completes restoration/rollback AFTER Possess. Binding here
    // would admit input before that work, or before a nested possession callback.
}
void AReceiver04Controller::EndDoveTransition() {
    if(!FlightTransition)return;
    const TSharedPtr<Authority> S=Remote;
    const TWeakObjectPtr<AReceiver04Controller> Self(this);
    const TWeakObjectPtr<APawn> P=GetPawn();
    const TWeakObjectPtr<UWorld> W=GetWorld();
    const TWeakObjectPtr<UPlayerInput> I=PlayerInput.Get();
    const TWeakObjectPtr<UPawnMovementComponent> M=P.IsValid()?P->GetMovementComponent():nullptr;
    auto Current=[&]() {
        return Self.IsValid()&&S.IsValid()&&Remote==S&&!S->IsClosed()&&FlightTransition&&
            P.IsValid()&&W.IsValid()&&I.IsValid()&&M.IsValid()&&IsLocalController()&&
            GetWorld()==W.Get()&&GetPawn()==P.Get()&&P->GetWorld()==W.Get()&&
            P->GetController()==this&&PlayerInput.Get()==I.Get()&&P->GetMovementComponent()==M.Get();
    };
    auto Fail=[&]() {
        if(S.IsValid())S->Abort();
        if(Self.IsValid()&&Remote==S) {
            if(auto* Old=Cast<UReceiver04WalkerMovement>(M.Get())) {
                if(Old->OwnsRemote(S,this,P.Get()))Old->DetachRemote();
            } else if(auto* Old=Cast<UReceiver04DoveMovement>(M.Get())) {
                if(Old->OwnsRemote(S,this,P.Get()))Old->DetachRemote();
            }
            DetachRemoteMovement();FlightTransition=false;
        }
    };
    if(!Current()){Fail();return;}
    const bool Walker=P.Get()==FlightWalker.Get()&&RealWalker(P.Get());
    const bool Dove=P.Get()==FlightDove.Get()&&P->GetClass()==AReceiverPossessionDove::StaticClass()&&
        P->GetOwner()==this&&Cast<UReceiver04DoveMovement>(M.Get());
    if(!(IsDoveFlightActive()?Dove:Walker)||!S->FinishPossession()||!Current()){Fail();return;}
    bool Bound=false;
    if(Walker)Bound=Cast<UReceiver04WalkerMovement>(M.Get())->ConfigureRemote(S,this);
    else Bound=Cast<UReceiver04DoveMovement>(M.Get())->ConfigureRemote(S,this);
    if(!Bound||!Current()){Fail();return;}
    OwnedPawn=P;FlightTransition=false;
    const auto Commit=OnOwnedPossessionCommit; // callback may revoke/detach
    if(!Commit||!Commit(S)||!Self.IsValid()||Remote!=S||S->IsClosed()||
       !RemotePossessionCurrent()||GetPawn()!=P.Get()||GetWorld()!=W.Get()||
       PlayerInput.Get()!=I.Get()||P->GetMovementComponent()!=M.Get()) {Fail();return;}
}
