#include "Modules/ModuleManager.h"
#include "Misc/CoreDelegates.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "../runtime_candidate05/PrivateBootstrap.h"

// Real candidate05 startup wiring, opt-in for a separately reviewed GAME launch.
// Editor/commandlet Blueprint validation never acquires stdin or a runtime owner.
class FReceiverIntegrationModule final : public FDefaultGameModuleImpl {
    MikdashOnline::RuntimeCandidate05::FPrivateBootstrap Bootstrap;
    FDelegateHandle Frame,Exit;
    bool Armed=false;
public:
    void StartupModule() override {
        if(!IsRunningGame() || IsRunningCommandlet() ||
           !FParse::Param(FCommandLine::Get(),TEXT("ReceiverIntegrationArmStopped"))) return;
        // This flag is NOT authentication. Candidate05 validates the private
        // inherited bootstrap and only admits a stopped owner; no listener/media.
        Armed=true;
        Exit=FCoreDelegates::OnEnginePreExit.AddLambda([this](){Bootstrap.Shutdown();});
        if(!Bootstrap.Startup()) { Bootstrap.Shutdown();return; }
        Frame=FCoreDelegates::OnBeginFrame.AddLambda([this](){Bootstrap.Tick();});
    }
    void ShutdownModule() override {
        if(Armed) Bootstrap.Shutdown();
        FCoreDelegates::OnBeginFrame.Remove(Frame);
        FCoreDelegates::OnEnginePreExit.Remove(Exit);
    }
    bool SupportsDynamicReloading() override {return false;}
};
IMPLEMENT_PRIMARY_GAME_MODULE(FReceiverIntegrationModule,Receiver04Compile,"Receiver04Compile");
