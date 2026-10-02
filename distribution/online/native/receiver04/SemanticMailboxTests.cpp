#include "SemanticMailbox.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS
using namespace MikdashOnline;
using namespace MikdashOnline::Receiver04;
namespace {
struct Fixture {
    double Now=0;
    Context C{1,2,1};
    SemanticMailbox Box{10,[this](){return Now;}};
    Fixture(){Box.Bind(C);}
    bool Input(uint64_t Sequence,const char* Action){
        Packet P;P.sequence=Sequence;P.operation="input";P.action=Action;P.y=Action==std::string("move")?1:0;
        return Box.Submit(P,C,Now);
    }
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMailboxLateConsumer,"Mikdash.Online.Receiver04.LateConsumer",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FMailboxLateConsumer::RunTest(const FString&){
    Fixture F;TestTrue(TEXT("queued"),F.Input(1,"move"));F.Now=.5;int Calls=0;
    F.Box.ConsumeMovement(F.C,false,[&](double,double,double){++Calls;return Outcome::Applied;});
    Consumption C;TestEqual(TEXT("never consumed"),Calls,0);TestFalse(TEXT("no ACK"),F.Box.Take(C));return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMailboxSweepDeadline,"Mikdash.Online.Receiver04.SweepDeadline",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FMailboxSweepDeadline::RunTest(const FString&){
    Fixture F;F.Input(1,"move");F.Now=.49;bool Commit=false;
    F.Box.ConsumeMovement(F.C,false,[&](double,double,double){
        const auto Fence=F.Box.CurrentMovementFence();F.Now=.51;
        Commit=F.Box.Revalidate(Fence);return Commit?Outcome::Applied:Outcome::Rejected;
    });
    Consumption C;TestFalse(TEXT("no velocity commit"),Commit);TestFalse(TEXT("unknown no ACK"),F.Box.Take(C));return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMailboxUnrelatedLook,"Mikdash.Online.Receiver04.LookCannotExtendHold",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FMailboxUnrelatedLook::RunTest(const FString&){
    Fixture F;F.Input(1,"move");F.Box.ConsumeMovement(F.C,false,[](double,double,double){return Outcome::Applied;});
    Consumption C;TestTrue(TEXT("initial consumed"),F.Box.Take(C));F.Now=1.9;F.Input(2,"look");F.Now=1.99;bool Commit=false;
    F.Box.ConsumeMovement(F.C,false,[&](double,double,double){
        const auto Fence=F.Box.CurrentMovementFence();F.Now=2.01;
        Commit=F.Box.Revalidate(Fence);return Commit?Outcome::Applied:Outcome::Rejected;
    });
    TestFalse(TEXT("held TTL wins over look deadline"),Commit);return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMailboxReentrantClear,"Mikdash.Online.Receiver04.ReentrantClear",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FMailboxReentrantClear::RunTest(const FString&){
    Fixture F;F.Input(1,"mute");F.Box.PostProcessInput(F.C,false,[&](const std::string&,double){F.Box.Clear();return Outcome::Applied;});
    Consumption C;TestFalse(TEXT("cancelled callback no ACK"),F.Box.Take(C));return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMailboxReentrantBind,"Mikdash.Online.Receiver04.ReentrantBind",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FMailboxReentrantBind::RunTest(const FString&){
    Fixture F;F.Input(1,"move");F.Box.ConsumeMovement(F.C,false,[&](double,double,double){F.Box.Bind({1,3,2});return Outcome::Applied;});
    Consumption C;TestFalse(TEXT("replacement cannot inherit result"),F.Box.Take(C));return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMailboxNoOp,"Mikdash.Online.Receiver04.NoOpOutcome",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FMailboxNoOp::RunTest(const FString&){
    Fixture F;F.Input(1,"mute");F.Box.PostProcessInput(F.C,true,[](const std::string&,double){return Outcome::NoOp;});
    Consumption C;TestTrue(TEXT("explicit outcome"),F.Box.Take(C));TestTrue(TEXT("not applied"),C.outcome==Outcome::NoOp);return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FMailboxLookOnce,"Mikdash.Online.Receiver04.LookOnce",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FMailboxLookOnce::RunTest(const FString&){
    Fixture F;F.Input(1,"look");int Count=0;
    auto Consume=[&](double,double,double){++Count;return Outcome::Applied;};
    F.Box.UpdateRotation(F.C,false,Consume);F.Box.UpdateRotation(F.C,false,Consume);
    TestEqual(TEXT("one semantic delta"),Count,1);return true;
}
#endif
