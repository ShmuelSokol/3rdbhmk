#include "AngularControllerPort.h"
#include <iostream>
using namespace AngularControllerStudy;
int main()
{
    int Checks=0,Failures=0;auto Check=[&](bool V){++Checks;if(!V)++Failures;};
    const Vec2 Posed[]={{50,0},{-50,0},{0,45},{0,-45}};
    const auto B=FromPosedBounds(Posed,4,0,190,1);
    Check(B.Known&&B.Radius==50);
    const MotionReservation Held{{0,0},{0,0},0,0};
    Check(!Pair(Held,B,{{90,0},{90,0},0,0},B,0)); // root80 passes; bodies do not
    Check(Pair(Held,B,{{110,0},{110,0},0,0},B,0));
    Check(!Pair(Held,B,{{150,0},{90,0},0,2},B,0)); // future foreign sweep
    Check(!Pair(Held,{},Held,B,0));
    int WorldCalls=0;
    auto Obstacle=[&](Vec2 F,Vec2 T,double Radius,double,double)
    {++WorldCalls;return ReservationDistance({F,T,0,1},{{90,0},{90,0},0,0},0)>=Radius+50;};
    Check(!World({0,0},{0,0},B,Obstacle));Check(WorldCalls==1);
    Check(!World({0,0},{0,0},{},Obstacle));Check(WorldCalls==1);
    Port A;A.Current.Envelope=B;
    int Holds=0;auto Hold=[&](Vec2 Root,Body Body_){++Holds;return Pair({Root,Root,0,0},Body_,{{110,0},{110,0},0,0},B,0);};
    Check(!A.Begin(180,0,{{0,0},{10,0},0,1},Hold));Check(Holds==0);
    Check(A.Begin(180,0,Held,Hold));Check(Holds==1);
    const auto Original=A.Current;
    for(int F=0;F<60;++F)
    {
        const double Time=F/30.;int Gates=0;
        Check(!A.Translation(Time,Held,[&](){++Gates;return true;},[](){return true;},[](){return true;}));Check(Gates==0);
        Check(A.Current.Yaw==Original.Yaw&&A.Current.TurnStartGameTime==Original.TurnStartGameTime&&A.Current.TurnDeltaDegrees==Original.TurnDeltaDegrees);
        Check(Length(A.Current.Root)==0);
        Check(std::abs(Angle(A.Current,Time+1./30)-Angle(A.Current,Time))<=3.0000001);
        const Vec2 V=PreviousPosedWorld(A,{20,5},{2,1},{2,1},Time);
        Check(Length(V-Rotate(Vec2{22,6},90*Time))<1e-8);
    }
    Check(!A.Rebase(2));Check(A.Rebase(2.1));Check(A.Current.TurnDeltaDegrees==0);
    Check(Length(PreviousPosedWorld(A,{20,5},{2,1},{2,1},2.09)-Rotate(Vec2{22,6},180))<1e-8);
    const auto CD=Channels(A.Current,A.Previous);Check(CD[1]==0&&CD[3]==180);
    Check(!A.Translation(2.1,Held,[](){return false;},[](){return true;},[](){return true;}));
    Check(A.Translation(2.1,Held,[](){return true;},[](){return true;},[](){return true;}));
    Check(Length(A.Current.Root)==0); // translation permission is not a move
    Port Denied;Denied.Current.Envelope=B;
    Check(!Denied.Begin(90,0,Held,[&](Vec2 R,Body E){return Pair({R,R,0,0},E,{{90,0},{90,0},0,0},B,0);}));
    Check(Denied.Current.TurnDeltaDegrees==0);
    std::cout<<"EnvelopePort: "<<Checks<<" checks, "<<Failures<<" failures\n";return Failures?1:0;
}
