#include "TransitCrowdLogic.h"
#include "TransitMath.h"
#include <iostream>
#include <limits>
int Failures=0,Checks=0;
void Expect(bool Condition,const char* Name) { ++Checks; if(!Condition) { ++Failures; std::cerr<<Name<<"\n"; } }
int main()
{
    using namespace MikdashTransitCrowd;
    Expect(Admission(70,140,160,20,32)==12,"per-stop cap wins");
    Expect(Admission(70,155,160,0,32)==5,"global cap wins");
    Expect(Admission(70,160,160,0,32)==0,"saturated pool refuses");
    Expect(Admission(1,161,160,0,32)==0,"over-budget refuses");
    Expect(Admission(-5,0,160,0,32)==0,"invalid request refuses");
    int Active=0; for(int Stop=0;Stop<16;++Stop) Active+=Admission(70,Active,160,0,32);
    Expect(Active==160,"sixteen stops cannot exceed shared cap");
    Expect(Fits(500,110,10),"reachable route fits");
    Expect(!Fits(500,110,4),"deadline rejects long walk");
    Expect(!Fits(500,110,10,6),"stagger time consumes dwell");
    Expect(!Fits(500,0,10),"zero speed refuses");
    Expect(!Fits(500,110,std::numeric_limits<double>::infinity()),"nonfinite deadline refuses");
    Expect(!Fits(5001,110,100),"bounded corridor length");
    const auto W=ExchangeWindow(100,20);
    Expect(W.AlightingEnd==109 && W.BoardingStart==109 && W.Deadline==119,"alight before boarding and close margin");
    Expect(ExchangeWindow(100,-1).Deadline==0,"negative dwell refuses");
    RecentKeys Seen;
    const auto A=Key("bus",1,2,3,4);
    Expect(Seen.Insert(A),"first event accepted"); Expect(!Seen.Insert(A),"repeated event ignored");
    Expect(Seen.Insert(Key("bus",1,3,3,4)),"same-stop different bus not duplicated");
    Expect(Seen.Insert(Key("bus",1,2,4,4)),"next run distinct");
    Expect(Seen.Insert(Key("bus",2,2,3,4)),"restart generation distinct");
    Seen.Clear(); Expect(Seen.Insert(A),"shutdown resets bounded history");
    MikdashTransit::StopState State; State.Phase=MikdashTransit::StopPhase::DoorsOpening;
    State.TargetStopIndex=0; State.DwellSeconds=2;
    MikdashTransit::FollowParams Follow; MikdashTransit::DwellConfig Config;
    Config.DoorOpenSeconds=.5; Config.DoorCloseSeconds=.5;
    auto Event=MikdashTransit::AdvanceStopState(State,.5,0,0,Follow,Config,1,1);
    Expect(Event.bDoorsOpened && State.Phase==MikdashTransit::StopPhase::Dwelling,"exchange trigger enters open window");
    for(int Tick=0;Tick<4;++Tick) Event=MikdashTransit::AdvanceStopState(State,.5,0,0,Follow,Config,1,1);
    Expect(!Event.bDoorsOpened && State.Phase==MikdashTransit::StopPhase::DoorsClosing,"expiry cannot trigger new exchange");
    Event=MikdashTransit::AdvanceStopState(State,.5,0,0,Follow,Config,1,1);
    Expect(Event.bDoorsClosed && !Event.bDoorsOpened,"door-close event never authorizes boarding/alighting");
    std::cout<<"checks="<<Checks<<" failures="<<Failures<<"\n"; return Failures?1:0;
}
