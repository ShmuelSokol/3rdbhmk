// Independent standalone SemanticMailbox execution. No Unreal headers or substitutions.
// The first seven cases translate the corresponding UE automation test bodies.
#include "receiver04/SemanticMailbox.h"
#include <iostream>
#include <stdexcept>
#include <limits>
using namespace MikdashOnline;
using namespace MikdashOnline::Receiver04;
static int Checks=0, Failures=0, Cases=0;
#define CHECK(expr) do { ++Checks; if (!(expr)) { ++Failures; std::cerr << "FAIL line " << __LINE__ << ": " << #expr << '\n'; } } while(false)
struct Fixture {
    double Now=0;
    Context C{1,2,1};
    SemanticMailbox Box;
    explicit Fixture(double End=10):Box(End,[this](){return Now;}) { CHECK(Box.Bind(C)); }
    bool Input(uint64_t Sequence,const char* Action) {
        Packet P; P.sequence=Sequence; P.operation="input"; P.action=Action;
        P.y=Action==std::string("move")?1:0;
        return Box.Submit(P,C,Now);
    }
};
template<class F> void Case(const char* Name,F Run) {
    ++Cases; const int Before=Failures;
    try { Run(); } catch(const std::exception& E) { ++Failures; std::cerr << E.what() << '\n'; }
    catch(...) { ++Failures; std::cerr << "Unexpected exception\n"; }
    std::cout << (Failures==Before?"PASS ":"FAIL ") << Name << '\n';
}
int main() {
    Case("original.LateConsumer",[](){
        Fixture F; CHECK(F.Input(1,"move")); F.Now=.5; int Calls=0;
        F.Box.ConsumeMovement(F.C,false,[&](double,double,double){++Calls;return Outcome::Applied;});
        Consumption C; CHECK(Calls==0); CHECK(!F.Box.Take(C));
    });
    Case("original.SweepDeadline",[](){
        Fixture F; CHECK(F.Input(1,"move")); F.Now=.49; bool Commit=false;
        F.Box.ConsumeMovement(F.C,false,[&](double,double,double){
            const auto Fence=F.Box.CurrentMovementFence(); F.Now=.51;
            Commit=F.Box.Revalidate(Fence); return Commit?Outcome::Applied:Outcome::Rejected;
        });
        Consumption C; CHECK(!Commit); CHECK(!F.Box.Take(C));
    });
    Case("original.LookCannotExtendHold",[](){
        Fixture F; CHECK(F.Input(1,"move"));
        F.Box.ConsumeMovement(F.C,false,[](double,double,double){return Outcome::Applied;});
        Consumption C; CHECK(F.Box.Take(C)); F.Now=1.9; CHECK(F.Input(2,"look")); F.Now=1.99; bool Commit=false;
        F.Box.ConsumeMovement(F.C,false,[&](double,double,double){
            const auto Fence=F.Box.CurrentMovementFence(); F.Now=2.01;
            Commit=F.Box.Revalidate(Fence);return Commit?Outcome::Applied:Outcome::Rejected;
        }); CHECK(!Commit);
    });
    Case("original.ReentrantClear",[](){
        Fixture F; CHECK(F.Input(1,"mute"));
        F.Box.PostProcessInput(F.C,false,[&](const std::string&,double){F.Box.Clear();return Outcome::Applied;});
        Consumption C; CHECK(!F.Box.Take(C));
    });
    Case("original.ReentrantBind",[](){
        Fixture F; CHECK(F.Input(1,"move"));
        F.Box.ConsumeMovement(F.C,false,[&](double,double,double){CHECK(F.Box.Bind({1,3,2}));return Outcome::Applied;});
        Consumption C; CHECK(!F.Box.Take(C));
    });
    Case("original.NoOpOutcome",[](){
        Fixture F; CHECK(F.Input(1,"mute"));
        F.Box.PostProcessInput(F.C,true,[](const std::string&,double){return Outcome::NoOp;});
        Consumption C; CHECK(F.Box.Take(C)); CHECK(C.outcome==Outcome::NoOp);
    });
    Case("original.LookOnce",[](){
        Fixture F; CHECK(F.Input(1,"look")); int Count=0;
        auto Consume=[&](double,double,double){++Count;return Outcome::Applied;};
        F.Box.UpdateRotation(F.C,false,Consume); F.Box.UpdateRotation(F.C,false,Consume);
        CHECK(Count==1);
    });
    Case("boundary.ResponseDeadline",[](){
        for(bool AtBoundary:{false,true}) {
            Fixture F; CHECK(F.Input(1,"look"));
            F.Now=AtBoundary?.5:std::nextafter(.5,0.0); int Calls=0;
            F.Box.UpdateRotation(F.C,false,[&](double,double,double){++Calls;return Outcome::Applied;});
            Consumption C; CHECK(Calls==(AtBoundary?0:1)); CHECK(F.Box.Take(C)==!AtBoundary);
        }
    });
    Case("boundary.SessionDeadline",[](){
        for(bool AtBoundary:{false,true}) {
            Fixture F; F.Now=9.75; CHECK(F.Input(1,"mute"));
            F.Now=AtBoundary?10:std::nextafter(10.0,0.0); int Calls=0;
            F.Box.PostProcessInput(F.C,false,[&](const std::string&,double){++Calls;return Outcome::Applied;});
            Consumption C; CHECK(Calls==(AtBoundary?0:1)); CHECK(F.Box.Take(C)==!AtBoundary);
            F.Now=10; CHECK(!F.Input(2,"mute"));
        }
    });
    Case("boundary.HeldMovementTTL",[](){
        Fixture F; CHECK(F.Input(1,"move")); int Calls=0;
        auto Consume=[&](double,double,double){++Calls;return Outcome::Applied;};
        F.Box.ConsumeMovement(F.C,false,Consume); Consumption C; CHECK(F.Box.Take(C));
        F.Now=std::nextafter(2.0,0.0); F.Box.ConsumeMovement(F.C,false,Consume); CHECK(Calls==2);
        F.Now=2; F.Box.ConsumeMovement(F.C,false,Consume); CHECK(Calls==2);
        CHECK(!F.Box.Take(C));
    });
    Case("late.CallbackSuppressesACK",[](){
        Fixture F; CHECK(F.Input(1,"mute")); F.Now=.49; int Effects=0;
        F.Box.PostProcessInput(F.C,false,[&](const std::string&,double){++Effects;F.Now=.5;return Outcome::Applied;});
        Consumption C; CHECK(Effects==1); CHECK(!F.Box.Take(C));
        F.Box.PostProcessInput(F.C,false,[&](const std::string&,double){++Effects;return Outcome::Applied;});
        CHECK(Effects==1); CHECK(!F.Input(1,"mute")); CHECK(F.Input(2,"mute"));
    });
    Case("late.SessionFenceBeforeCommit",[](){
        Fixture F; F.Now=9.75; CHECK(F.Input(1,"move")); F.Now=9.99; int Effects=0;
        F.Box.ConsumeMovement(F.C,false,[&](double,double,double){
            const auto Fence=F.Box.CurrentMovementFence(); CHECK(F.Box.Revalidate(Fence)); F.Now=10;
            const bool Fresh=F.Box.Revalidate(Fence); CHECK(!Fresh); if(Fresh) ++Effects;
            return Fresh?Outcome::Applied:Outcome::Rejected;
        });
        Consumption C; CHECK(Effects==0); CHECK(!F.Box.Take(C));
    });
    std::cout << "SemanticMailboxStandalone: " << Cases << " cases, " << Checks << " checks, " << Failures << " failures\n";
    return Failures?1:0;
}
