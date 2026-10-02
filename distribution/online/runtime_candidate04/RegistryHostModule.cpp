#include "RegistryHost.h"
#include "Modules/ModuleManager.h"

// Staged module entry point, NOT registered in any uproject/uplugin/Build.cs.
class FOnlineRegistryHostModule final : public IModuleInterface {
public:
    void StartupModule() override { MikdashOnline::RuntimeCandidate04::FRegistryHost::Startup(); }
    void ShutdownModule() override { MikdashOnline::RuntimeCandidate04::FRegistryHost::Shutdown(); }
    bool SupportsDynamicReloading() override { return false; }
};
IMPLEMENT_MODULE(FOnlineRegistryHostModule, OnlineRegistryHost)
