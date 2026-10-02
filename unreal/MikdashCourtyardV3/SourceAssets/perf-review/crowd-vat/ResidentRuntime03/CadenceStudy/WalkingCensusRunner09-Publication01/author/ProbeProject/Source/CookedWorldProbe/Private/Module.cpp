#include "Modules/ModuleManager.h"
#include "CensusDriver.h"
class FCensusModule : public FDefaultGameModuleImpl {
 void StartupModule() override {StartWalkingCensus09();}
 void ShutdownModule() override {StopWalkingCensus09();}
};
IMPLEMENT_PRIMARY_GAME_MODULE(FCensusModule,CookedWorldProbe,"CookedWorldProbe");
