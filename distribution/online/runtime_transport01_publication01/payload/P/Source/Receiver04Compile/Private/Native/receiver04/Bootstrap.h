#pragma once
#include "Receiver.h"
#include "OnlineController.h"
#include "OnlineMovement.h"
#include "../OnlineInputGate.h"
#include "../../runtime_adoption01/AdoptionState.h"
#include "../../runtime_activation01/RouteLifetime.h"
class UPlayerInput;
class UWorld;
namespace MikdashOnline::RuntimeCandidate04 { class FServicedStoppedOwner; }
namespace MikdashOnline::Adoption01 { class FParsedAdmission; }
namespace MikdashOnline::Receiver04 {
// Additive replacement in isolated project only. No stdin reader or Start API.
class Bootstrap : public TSharedFromThis<Bootstrap> {
    TWeakObjectPtr<AReceiver04Controller> Controller;
    TWeakObjectPtr<APawn> Pawn;
    TWeakObjectPtr<UPlayerInput> PlayerInput;
    TWeakObjectPtr<UWorld> World;
    TWeakObjectPtr<UPawnMovementComponent> Movement;
    TSharedPtr<IPixelStreaming2Streamer> Streamer;
    TSharedPtr<FOnlineInputGate> Gate;
    TSharedPtr<Authority> Service;
    TUniquePtr<Receiver> Server; // constructed but never started in this revision
    TSharedPtr<const Adoption01::FParsedAdmission> Admission;
    Adoption01::AdoptionState Lifecycle;
    Activation01::RouteLifetime Route;
    friend class RuntimeCandidate04::FServicedStoppedOwner;
    TWeakPtr<RuntimeCandidate04::FServicedStoppedOwner> MediaOwner;
    bool ConsumersBound=false,MediaStarted=false;
    bool PossessionPending=false;
    Context PossessionBefore{};
    bool BeginOwnedPossession(const TSharedPtr<Authority>& S);
    bool CommitOwnedPossession(const TSharedPtr<Authority>& S);
    bool AuthenticatedLifecycle(const Packet& P);
    bool AttachOwnedMedia(const Packet& P);
    bool Busy=false,Stopping=false;
    FDelegateHandle TickHandle;
    void Poll();
public:
    ~Bootstrap();
    bool AdoptStopped(TSharedRef<const Adoption01::FParsedAdmission> Parsed,
        AReceiver04Controller* C,TSharedPtr<IPixelStreaming2Streamer> S,
        TSharedPtr<FOnlineInputGate> ExistingGate);
    bool IsOwnedRouteLive();
    bool IsReady()const{return Route.IsOpened()&&!Stopping;} // authenticated IPC open, NOT media readiness
    TSharedPtr<Authority> GetAuthority()const{return Service;}
    bool Shutdown();
};
}
