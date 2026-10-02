#include "PrivateBootstrap.h"
#include "Misc/CoreDelegates.h"
#include "Modules/ModuleManager.h"

// Alternative module entry point; never compile RegistryHostModule.cpp alongside
// this entry point. RegistryHost.cpp remains the actual process-local owner.
class FPrivateBootstrapModule final : public IModuleInterface {
    MikdashOnline::RuntimeCandidate05::FPrivateBootstrap Bootstrap;
    FDelegateHandle Frame,Exit;
public:
    void StartupModule() override {
        if(!Bootstrap.Startup()) return;
        Frame=FCoreDelegates::OnBeginFrame.AddLambda([this](){Bootstrap.Tick();});
        Exit=FCoreDelegates::OnEnginePreExit.AddLambda([this](){Bootstrap.Shutdown();});
    }
    void ShutdownModule() override {
        Bootstrap.Shutdown(); // explicit pre-Slate/PS2 shutdown is still required
        FCoreDelegates::OnBeginFrame.Remove(Frame);
        FCoreDelegates::OnEnginePreExit.Remove(Exit);
    }
    bool SupportsDynamicReloading() override { return false; }
};
IMPLEMENT_MODULE(FPrivateBootstrapModule, OnlinePrivateBootstrap)
