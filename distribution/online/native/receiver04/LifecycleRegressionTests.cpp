#include "Authority.h"
#include "BootstrapGuards.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS
using namespace MikdashOnline::Receiver04;
namespace {
struct TestController;
struct TestPawn { TestController* Controller=nullptr; TestController* GetController()const{return Controller;} };
struct TestController {
    TestPawn* Pawn=nullptr;void* PlayerInput=nullptr;
    TestPawn* GetPawn()const{return Pawn;}
    void* GetWorld()const{return reinterpret_cast<void*>(1);}
    bool IsLocalController()const{return true;}
};
struct TestStream {bool IsStreaming()const{return false;}};
template<class T> struct Ref {
    T* Ptr=nullptr;bool IsValid()const{return Ptr!=nullptr;}
    T* Get()const{return Ptr;}T* operator->()const{return Ptr;}
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FIdleAuthorityExpiry,"Mikdash.Online.Receiver04.IdleExpiry",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FIdleAuthorityExpiry::RunTest(const FString&){
    MikdashOnline::Receiver03::Bootstrap B;
    B.Identity={"s","p","stream","save","settings",11};B.Deadline=10;
    double Now=9;Authority A(B,1,2,[&](){return Now;});
    A.Maintain();TestFalse(TEXT("live without any peer"),A.IsClosed());
    Now=10;A.Maintain();TestTrue(TEXT("expiry without PollReply/request"),A.IsClosed());return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FBootstrapCloseFailure,"Mikdash.Online.Receiver04.BootstrapCloseFailure",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FBootstrapCloseFailure::RunTest(const FString&){
    void* Handle=reinterpret_cast<void*>(123);bool Poisoned=false;int Calls=0;
    auto Fail=[&](void*){++Calls;return false;};
    TestFalse(TEXT("failed close not clean"),CloseBootstrapInput(Handle,Poisoned,Fail));
    TestTrue(TEXT("identity retained"),Handle==reinterpret_cast<void*>(123));
    TestFalse(TEXT("cannot retry even with a succeeding closer"),CloseBootstrapInput(Handle,Poisoned,[&](void*){++Calls;return true;}));
    TestEqual(TEXT("one native close attempt"),Calls,1);return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FBootstrapCloseSuccess,"Mikdash.Online.Receiver04.BootstrapCloseSuccess",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FBootstrapCloseSuccess::RunTest(const FString&){
    void* Handle=reinterpret_cast<void*>(123);bool Poisoned=false;int Calls=0;
    auto Close=[&](void*){++Calls;return true;};
    TestTrue(TEXT("closed"),CloseBootstrapInput(Handle,Poisoned,Close));
    TestTrue(TEXT("idempotent"),CloseBootstrapInput(Handle,Poisoned,Close));
    TestEqual(TEXT("only once"),Calls,1);TestTrue(TEXT("cleared after proof"),Handle==nullptr);return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FBootstrapCallbackInvalidation,"Mikdash.Online.Receiver04.SettingsCallbackInvalidation",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FBootstrapCallbackInvalidation::RunTest(const FString&){
    int Input=0;TestController C;TestPawn P,Q;TestStream S;C.Pawn=&P;C.PlayerInput=&Input;P.Controller=&C;
    Ref<TestController> CR{&C};Ref<TestPawn> PR{&P};Ref<int> IR{&Input};Ref<TestStream> SR{&S};
    auto Check=[&](){return BootstrapTargetsValid(CR,PR,IR,SR,10,[](){return 9.;});};
    TestTrue(TEXT("initial owned targets"),Check());
    CR.Ptr=nullptr;TestFalse(TEXT("controller destroyed by proof callback"),Check());CR.Ptr=&C;
    PR.Ptr=nullptr;TestFalse(TEXT("pawn destroyed by callback"),Check());PR.Ptr=&P;
    C.Pawn=&Q;TestFalse(TEXT("repossessed pawn"),Check());C.Pawn=&P;
    C.PlayerInput=nullptr;TestFalse(TEXT("reinitialized input"),Check());return true;
}
#endif
