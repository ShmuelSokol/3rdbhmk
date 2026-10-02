#include "RegistryHost.h"
#include "ServicedStoppedOwner.h"
#include "../native/OnlineInputGate.h"
#include "../native/receiver03/Wire.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"
#include "Misc/CoreDelegates.h"
#include "Modules/ModuleManager.h"

namespace MikdashOnline::RuntimeCandidate04 {
namespace {
using FOwner=FServicedStoppedOwner;
struct FHost {
    FRegistryHost::State Phase=FRegistryHost::State::WaitingForModule;
    bool AdmissionUsed=false,Busy=false,Closing=false;
    double AdmissionEnd=0,Last=-1;
    uint64_t PossessionGeneration=0;
    Owner Identity;
    IPixelStreaming2Module* Module=nullptr;
    TSharedPtr<FOwner> Owned;
    TSharedPtr<FOnlineInputGate> Gate;
    TWeakObjectPtr<AReceiver04Controller> Controller;
    TWeakObjectPtr<APawn> Pawn;
    TWeakObjectPtr<UWorld> World;
    FDelegateHandle Frame,Exit,Cleanup;
};
// One image/module instance per process; no hot reload or second host permitted.
TUniquePtr<FHost> Host;
bool EverStarted=false;
bool AutoStartDisabled() {
    auto& Console=IConsoleManager::Get();
    auto* Default=Console.FindConsoleVariable(TEXT("PixelStreaming2.InitializeDefaultStreamer"));
    auto* Auto=Console.FindConsoleVariable(TEXT("PixelStreaming2.AutoStartStream"));
    return Default&&Auto&&Default->GetInt()==0&&Auto->GetInt()==0;
}
IPixelStreaming2Module* LoadedModule() {
    return FModuleManager::GetModulePtr<IPixelStreaming2Module>(TEXT("PixelStreaming2"));
}
bool RegistryExclusive() {
    if(!Host||!Host->Module||LoadedModule()!=Host->Module||!Host->Module->IsReady()||!AutoStartDisabled()) return false;
    const auto Ids=Host->Module->GetStreamerIds();
    if(!Host->Owned.IsValid()) return Ids.Num()==0;
    const FString Id=UTF8_TO_TCHAR(Host->Identity.stream_id.c_str());
    return Id!=Host->Module->GetDefaultStreamerID()&&Ids.Num()==1&&Ids[0]==Id;
}
void Tick() {
    check(IsInGameThread());
    if(!Host||Host->Busy||Host->Closing) return;
    const double N=Receiver03::QpcSeconds();
    if(!std::isfinite(N)||N<0||N>1099511627776.0||N<Host->Last) { FRegistryHost::Shutdown(); return; }
    Host->Last=N;
    if(Host->Phase==FRegistryHost::State::WaitingForModule||Host->Phase==FRegistryHost::State::AwaitingAllocation) {
        if(N>=Host->AdmissionEnd) { FRegistryHost::Shutdown(); return; }
        auto* M=LoadedModule();
        if(!M||!M->IsReady()) return;
        Host->Module=M;
        if(!RegistryExclusive()) { FRegistryHost::Shutdown(); return; }
        Host->Phase=FRegistryHost::State::AwaitingAllocation;
        return;
    }
    if(Host->Phase!=FRegistryHost::State::StoppedReady) return;
    // Only the authenticated controller may advance a real flight incarnation.
    // Stopped/unattached local possession still shuts down as before.
    if(Host->Controller.IsValid() && Host->Controller->GetPawn()!=Host->Pawn.Get() &&
       Host->Controller->RemotePossessionCurrent() &&
       Host->Controller->RemotePossessionGeneration()>Host->PossessionGeneration) {
        Host->Pawn=Host->Controller->GetPawn();
        Host->PossessionGeneration=Host->Controller->RemotePossessionGeneration();
    }
    // Observe each frame without mutating any foreign registry entry or streamer.
    if(!RegistryExclusive()||!Host->Controller.IsValid()||!Host->Pawn.IsValid()||
       Host->Controller->GetPawn()!=Host->Pawn.Get()||!Host->Controller->PlayerInput||
       Host->Controller->GetWorld()!=Host->World.Get()||
       (Host->Controller->RemotePossessionGeneration()!=0 && !Host->Controller->RemotePossessionCurrent())) {
        FRegistryHost::Shutdown(); return;
    }
    Host->Busy=true;
    const auto Owned=Host->Owned; // callbacks may request shutdown; retain exact owner
    const auto S=Owned->BorrowStopped(Host->Identity);
    const bool GateIntact=S.IsValid()&&S->GetInputHandler().Pin()==Host->Gate;
    Host->Busy=false;
    if(Host->Closing||!GateIntact) FRegistryHost::Shutdown();
}
}

bool FRegistryHost::Startup() {
    check(IsInGameThread());
    if(EverStarted) return false;
    EverStarted=true; Host=MakeUnique<FHost>();
    const double N=Receiver03::QpcSeconds();
    if(!std::isfinite(N)||N<0||N>1099511627771.0) { Host->Phase=State::Closed;return false; }
    Host->Last=N;Host->AdmissionEnd=N+5; // bounded startup, no indefinite idle owner
    Host->Frame=FCoreDelegates::OnBeginFrame.AddStatic(&Tick);
    Host->Exit=FCoreDelegates::OnEnginePreExit.AddLambda([](){FRegistryHost::Shutdown();});
    Host->Cleanup=FWorldDelegates::OnWorldCleanup.AddLambda([](UWorld* W,bool,bool){
        if(Host&&Host->World.Get()==W) FRegistryHost::Shutdown();
    });
    Tick();return Host->Phase!=State::Closed;
}

bool FRegistryHost::AdmitStopped(const Owner& O,double D) {
    check(IsInGameThread());
    if(!Host||Host->Busy||Host->Closing||Host->AdmissionUsed) return false;
    Host->AdmissionUsed=true;
    Tick();
    if(Host->Phase!=State::AwaitingAllocation||!RegistryExclusive()||!GEngine||!GEngine->GameViewport) {
        Shutdown();return false;
    }
    auto* V=GEngine->GameViewport;
    UWorld* W=V->GetWorld();
    auto* C=IsValid(W)?Cast<AReceiver04Controller>(W->GetFirstPlayerController()):nullptr;
    APawn* P=IsValid(C)?C->GetPawn():nullptr;
    auto* Movement=IsValid(P)?P->GetMovementComponent():nullptr;
    if(!IsValid(C)||!C->IsLocalController()||!C->PlayerInput||!IsValid(P)||P->GetController()!=C||
       (!Cast<UReceiver04WalkerMovement>(Movement)&&!Cast<UReceiver04DoveMovement>(Movement))) { Shutdown();return false; }
    Host->Busy=true;Host->Identity=O;Host->Controller=C;Host->Pawn=P;Host->World=W;
    // A fresh receiver is private to this owner; never accept an injected running one.
    auto Receiver=MakeShared<Receiver04::Bootstrap>();
    Host->Owned=FOwner::Create(*Host->Module,V,Receiver,O,D);
    if(!Host->Closing&&Host->Owned->GetState()==FOwner::State::Ready&&RegistryExclusive()) {
        auto S=Host->Owned->BorrowStopped(O);
        if(S.IsValid()&&!S->IsConnected()) Host->Gate=FOnlineInputGate::Install(S);
    }
    const bool Valid=!Host->Closing&&Host->Gate.IsValid()&&Host->Owned->Matches(O)&&RegistryExclusive()&&
        Host->Controller.IsValid()&&Host->Pawn.IsValid()&&Host->Controller->GetPawn()==Host->Pawn.Get()&&Host->Controller->PlayerInput;
    Host->Busy=false;
    if(Host->Closing||!Valid) { Shutdown();return false; }
    Host->Phase=State::StoppedReady;return true;
    // No Bootstrap::Start: authenticated allocation/attachment handoff not implemented.
}

bool FRegistryHost::Shutdown() {
    check(IsInGameThread());
    if(!Host) return true;
    Host->Closing=true;
    if(Host->Busy) return false;
    if(Host->Phase==State::Closed) return true;
    if(Host->Phase==State::Quarantined) return false;
    // Late module unload cannot be repaired by dereferencing candidate03's module ref.
    if(Host->Owned.IsValid()&&LoadedModule()!=Host->Module) { Host->Phase=State::Quarantined;return false; }
    Host->Busy=true;
    const bool Clean=!Host->Owned.IsValid()||Host->Owned->Shutdown();
    Host->Busy=false;
    if(!Clean) { Host->Phase=State::Quarantined;return false; }
    Host->Gate.Reset();Host->Owned.Reset();Host->Phase=State::Closed;
    FCoreDelegates::OnBeginFrame.Remove(Host->Frame);
    FCoreDelegates::OnEnginePreExit.Remove(Host->Exit);
    FWorldDelegates::OnWorldCleanup.Remove(Host->Cleanup);
    // Never reopen AdmissionUsed/EverStarted. Owned-process exit ends quarantine.
    return true;
}
FRegistryHost::State FRegistryHost::GetState() { check(IsInGameThread());return Host?Host->Phase:State::Closed; }
}
