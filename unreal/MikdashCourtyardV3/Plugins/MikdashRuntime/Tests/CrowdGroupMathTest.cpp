#include "CrowdGroupMath.h"
#include <iostream>
#include <limits>
namespace { int Checks=0,Failures=0;
void Expect(bool Value,const char* Why){++Checks;if(!Value){++Failures;std::cerr<<"FAIL "<<Why<<'\n';}} }
int main()
{
    using namespace MikdashCrowdGroups;
    using namespace MikdashCrowd;
    // Plan independently per zone, including tiny zones and all-solo opt-out.
    for(int Population:{0,1,2,3,6,17,240,10000}) for(double Ratio:{0.0,.15,1.0})
    {
        int Remaining=Population,Singles=SingleBudget(Population,Ratio),ActualSingles=0,Identity=0;
        const int ExpectedSingles=Singles;
        while(Remaining>0)
        {
            int Copy=Singles;
            const int Size=NextSize(Remaining,Singles,20260908u,static_cast<uint32_t>(Identity));
            Expect(Size==NextSize(Remaining,Copy,20260908u,static_cast<uint32_t>(Identity)),"stable seed group plan");
            Expect(Size>=1&&Size<=6&&Size<=Remaining,"cohorts bounded2to6 with singles");
            if(Size==1) ++ActualSingles;
            Remaining-=Size;Identity+=Size;
        }
        Expect(ActualSingles==ExpectedSingles&&Identity==Population,"15percent refers to people; no lost zone tail");
    }
    Expect(SingleBudget(10000,.15)==1500,"large population exactly15percent individuals before geometry refusals");
    for(uint32_t Id=0;Id<100;++Id)
    {
        for(int I=0;I<6;++I) for(int J=I+1;J<6;++J)
            Expect(Length(Offset(I,19,Id,120)-Offset(J,19,Id,120))>=MinSeparationCm,"loose formation preserves physical separation");
    }
    Cohort Group;Group.Count=6;Group.Identity=47;Group.Speed=90;
    Vec2 Positions[6];for(int I=0;I<6;++I) Positions[I]=Offset(I,13,Group.Identity,120);
    Settings Config;
    auto Leader=Steering(Group,0,Positions,0,{1,0},Config,13);
    Expect(Leader.Valid&&Leader.Speed==90&&!Leader.Waiting,"coherent group walks common90cm pace");
    Positions[5].X-=150;
    Leader=Steering(Group,0,Positions,0,{1,0},Config,13);
    Expect(Leader.Speed>0&&Leader.Speed<90&&!Leader.Waiting,"leader slows for moderately lagging member");
    Positions[5].X-=200;
    Leader=Steering(Group,0,Positions,0,{1,0},Config,13);
    const auto Follower=Steering(Group,5,Positions,0,{1,0},Config,13);
    Expect(Leader.Waiting&&Leader.Speed==0&&Follower.Speed>0,"leader waits while laggard can catch up");
    const Vec2 Before=Positions[5];
    Expect(Positions[5].X==Before.X&&Positions[5].Y==Before.Y,"steering never teleports its input");
    // A bounded integration of the exact production steering demonstrates regrouping.
    for(int Tick=0;Tick<1000;++Tick)
    {
        for(int I=0;I<6;++I)
        {
            const auto Cmd=Steering(Group,I,Positions,0,{1,0},Config,13);
            Positions[I]=Positions[I]+Cmd.Direction*(Cmd.Speed*.01);
        }
    }
    Leader=Steering(Group,0,Positions,0,{1,0},Config,13);
    Expect(!Leader.Waiting&&Leader.MaxLag<100,"laggard regroups and shared pace resumes");
    auto BadConfig=Config;BadConfig.SpacingCm=std::numeric_limits<double>::quiet_NaN();
    Expect(!Steering(Group,0,Positions,0,{1,0},BadConfig,13).Valid,"invalid group setting refuses motion");
    auto Broken=Group;Broken.Count=7;
    Expect(!Steering(Broken,0,Positions,0,{1,0},Config,13).Valid,"oversized cohort refuses bounded-array access");

    Travel Journey;Journey.FormationHeading=15;
    RejectedLeaderMove(Journey,500);
    Expect(Journey.Mode==TravelMode::Returning&&Journey.FormationHeading==15,"first distant block returns without rotating formation");
    RejectedLeaderMove(Journey,80);
    Expect(Journey.Mode==TravelMode::Paused,"unsuccessful arrival cannot clear returning state");
    for(int I=0;I<20;++I) { RejectedLeaderMove(Journey,80);SuccessfulLeaderMove(Journey,80,180); }
    Expect(Journey.Mode==TravelMode::Paused&&Journey.FormationHeading==15,"repeated blocked anchor stays paused without opposing-flow spin");
    Journey=Travel{};RejectedLeaderMove(Journey,400);SuccessfulLeaderMove(Journey,200,25);
    Expect(Journey.Mode==TravelMode::Returning&&Journey.FormationHeading==25,"successful return travel updates formation only with movement");
    SuccessfulLeaderMove(Journey,100,30);
    Expect(Journey.Mode==TravelMode::Forward&&Journey.FormationHeading==30,"successful anchor arrival clears returning");
    RejectedLeaderMove(Journey,100);
    Expect(Journey.Mode==TravelMode::Paused,"renewed obstruction near anchor pauses instead of cycling");
    for(int I=0;I<6;++I) Positions[I]=Offset(I,13,Group.Identity,120);
    const auto PausedLeader=Steering(Group,0,Positions,0,{1,0},Config,13,true);
    const auto SettledMember=Steering(Group,3,Positions,0,{1,0},Config,13,true);
    Expect(PausedLeader.Speed==0&&PausedLeader.Waiting&&SettledMember.Speed==0,"paused party stays stopped when formation already settled");
    Positions[3].X-=100;
    Expect(Steering(Group,3,Positions,0,{1,0},Config,13,true).Speed>0,"paused companions may settle without moving leader");
    double Height=0;
    Expect(FollowPlane(555,500,501.5,Height)&&Height==556.5,"first sloped step preserves55cm traced residual");
    Expect(FollowPlane(Height,501.5,499,Height)&&Height==554,"later sloped step preserves residual without accumulating plane correction");
    Height=123;
    const double NaN=std::numeric_limits<double>::quiet_NaN();
    Expect(!FollowPlane(NaN,0,0,Height)&&Height==123,"nonfinite traced support refuses transactionally");
    Expect(!FollowPlane(0,NaN,0,Height)&&Height==123,"nonfinite source plane refuses transactionally");
    Expect(!FollowPlane(0,0,NaN,Height)&&Height==123,"nonfinite target plane refuses transactionally");
    Expect(!FollowPlane(std::numeric_limits<double>::max(),0,std::numeric_limits<double>::max(),Height)
        &&Height==123,"overflowed slope result refuses transactionally");

    SpatialIndex Index;
    Expect(Index.Insert(1,{0,0})&&!Index.Insert(2,{70,0}),"seed separation enforced");
    Expect(Index.Insert(2,{100,0}),"valid spacing seeds");
    Expect(!Index.SegmentClear({0,0},{90,0},1),"swept separation refuses walking through neighbor");
    Expect(Index.Move(1,{0,0},{-100,0}),"bounded move crosses spatial cell");
    Expect(Index.Insert(3,{0,0}),"old spatial cell membership removed after movement");
    Expect(!Index.Move(1,{-100,0},{500,0}),"regroup teleport rejected");
    Index.Remove(3,{0,0});Expect(Index.Move(1,{-100,0},{-20,0}),"remove and continued movement retain index coverage");
    Index.Clear();
    for(int X=0;X<100;++X) for(int Y=0;Y<100;++Y)
        Expect(Index.Insert(X*100+Y,{X*120.0,Y*120.0}),"ten thousand separate agents accepted in bounded hash");
    Expect(!Index.SegmentClear({6000,6000},{6050,6000},5050),"dense neighbor checked without all-agent scan");

    const Vec2 Zone[]={{-1000,-1000},{1000,-1000},{1000,1000},{-1000,1000}};
    const Vec2 Wall[]={{-5,-800},{5,-800},{5,800},{-5,800}};const int Starts[]={0},Counts[]={4};
    Geometry World;World.Zone=Zone;World.ZoneCount=4;World.Protected=Wall;World.Starts=Starts;World.Counts=Counts;
    World.ProtectedCount=1;World.ProtectedMargin=0;World.EdgeMargin=0;
    Expect(!SegmentAllowed(World,{-50,0},{50,0}),"thin wall cannot be tunneled despite legal segment endpoints");
    Expect(SegmentAllowed(World,{-300,0},{-250,0}),"bounded walk clear of wall accepted");
    Expect(!SegmentAllowed(World,{930,0},{980,0}),"physical edge radius preserved even authored marginzero");
    Expect(!SegmentAllowed(World,{-300,0},{-700,0}),"geometry gate refuses long jump");
    // Same physical constraints with an architectural wall at96percent coordinates.
    Vec2 ScaledZone[4],ScaledWall[4];for(int I=0;I<4;++I){ScaledZone[I]=Zone[I]*.96;ScaledWall[I]=Wall[I]*.96;}
    World.Zone=ScaledZone;World.Protected=ScaledWall;
    Expect(!SegmentAllowed(World,{-50,0},{50,0})&&SegmentAllowed(World,{-300,0},{-250,0}),"runtime48 geometry uses unchanged physical group dimensions");
    std::cout<<"CrowdGroupMath: "<<Checks<<" checks, "<<Failures<<" failures\n";
    return Failures?1:0;
}
