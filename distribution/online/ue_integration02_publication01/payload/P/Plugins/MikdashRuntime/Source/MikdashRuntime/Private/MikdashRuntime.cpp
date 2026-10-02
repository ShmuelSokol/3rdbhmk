#include "Modules/ModuleManager.h"
#include "ContextMaterialFixture.h"

class FMikdashRuntimeModule : public IModuleInterface
{
public:
    virtual void StartupModule() override { ContextMaterialFixture::Startup(); }
    virtual void ShutdownModule() override { ContextMaterialFixture::Shutdown(); }
};

IMPLEMENT_MODULE(FMikdashRuntimeModule, MikdashRuntime)
