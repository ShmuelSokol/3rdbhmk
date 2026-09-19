#include "CrowdGroupMath.h"
#include <iostream>
#include <limits>
int main()
{
    using namespace MikdashCrowd;
    using namespace MikdashCrowdGroups;
    int Checks=0,Failures=0;
    auto Expect=[&](bool Okay,const char* Label){++Checks;if(!Okay){++Failures;std::cerr<<Label<<"\n";}};
    int Calls=0;
    auto Clear=FindLocalRoute(20,[&](double){++Calls;return true;});
    Expect(Clear.Clear&&Clear.Heading==20&&Calls==1,"unobstructed goal uses one probe");
    Calls=0;
    auto Blocked=FindLocalRoute(20,[&](double){++Calls;return false;});
    Expect(!Blocked.Clear&&Calls==8&&Blocked.Probes==8,"fully blocked search is bounded");
    Calls=0;
    auto Invalid=FindLocalRoute(std::numeric_limits<double>::quiet_NaN(),[&](double){++Calls;return true;});
    Expect(!Invalid.Clear&&Calls==0,"invalid heading does not probe world");
    auto Side=FindLocalRoute(170,[](double Yaw){return Yaw==-100||Yaw==80;});
    Expect(Side.Clear&&Side.Heading==-100,"wrapped equal-angle choices have consistent handedness");
    // An actual traveler must get past a stationary person, not merely find a
    // nominal sideways vector. Apply the production turn cap and timed gate at
    // each step; compare dense positions and endpoint progress independently.
    SpatialIndex Index;
    Vec2 Position{-180,0};const Vec2 Goal{180,0};double Heading=0,Minimum=180;
    Expect(Index.Insert(0,Position)&&Index.Insert(1,{0,0}),"walking fixture seeded");
    constexpr double Dt=1.0/30.0,Step=3.0;
    int Moves=0;
    for(int Frame=0;Frame<1800&&Length(Goal-Position)>10;++Frame)
    {
        const double Now=Frame*Dt;
        const auto End=[&](double Yaw){return Position+FromDegrees(Yaw)*Step;};
        const auto Choice=FindLocalRoute(YawDegrees(Goal-Position),[&](double Yaw){return Index.CanReserve(0,Position,End(Yaw),Now,Dt);});
        const double NextHeading=SteerHeading(Heading,Choice.Clear?Choice.Heading:YawDegrees(Goal-Position),Dt,90);
        Expect(std::abs(WrapDegrees(NextHeading-Heading))<=3.0000001,"turn cap holds while avoiding");
        Heading=NextHeading;const Vec2 Next=End(Heading);
        if(Index.Reserve(0,Position,Next,Now,Dt))
        {
            for(int I=0;I<=10;++I)Minimum=std::min(Minimum,Length(Position+(Next-Position)*(I/10.0)));
            Expect(Index.Relocate(0,Position,Next,Now+Dt),"accepted step commits at endpoint");
            Position=Next;++Moves;
        }
    }
    Expect(Minimum>=80.0,"stationary person never breached");
    Expect(Moves>100&&Length(Goal-Position)<=10,"traveler gets around person and reaches goal");
    std::cout<<"CrowdLocalRouteMath: "<<Checks<<" checks, "<<Failures<<" failures\n";
    return Failures?1:0;
}
