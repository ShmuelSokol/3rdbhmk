#pragma once
#include "CrowdGroupMath.h"
#include <cstdint>
#include <deque>
namespace RuntimePortReview
{
using namespace MikdashCrowd;
struct Steps
{
    double Minimum=0,Maximum=0;bool Valid=false;
};
inline Steps ClipSteps(double GroundSpeed,double Scale,double MinRate,double MaxRate,double RouteSpeed,double Horizon)
{
    Steps S;
    if(!std::isfinite(GroundSpeed)||!std::isfinite(Scale)||!std::isfinite(MinRate)||!std::isfinite(MaxRate)
        ||!std::isfinite(RouteSpeed)||!std::isfinite(Horizon)||GroundSpeed<=0||Scale<=0||MinRate<=0
        ||MaxRate<MinRate||RouteSpeed<=0||Horizon<=0)return S;
    S.Minimum=GroundSpeed*Scale*MinRate*Horizon;
    S.Maximum=std::min(99.0,std::min(RouteSpeed,GroundSpeed*Scale*MaxRate)*Horizon);
    S.Valid=S.Minimum<=S.Maximum&&std::isfinite(S.Minimum)&&std::isfinite(S.Maximum);
    return S;
}
inline int Parts(double Distance,const Steps& S)
{
    if(!S.Valid||!std::isfinite(Distance)||Distance<=0)return 0;
    const double N=std::ceil(Distance/S.Maximum);
    if(N>1000000)return 0;
    const int Count=std::max(1,static_cast<int>(N));
    return Distance/Count>=S.Minimum-1e-7?Count:0;
}
struct Target { bool Valid=false;Vec2 Point{};std::size_t Cursor=0; };
template<class Gate> Target ExecutableTarget(Vec2 Root,const std::vector<Vec2>& Path,std::size_t Cursor,const Steps& S,Gate&& Allowed)
{
    Target Out;double Along=0;Vec2 Previous=Root;
    for(std::size_t K=Cursor;K<Path.size();++K)
    {
        Along+=Length(Path[K]-Previous);Previous=Path[K];if(Along>99)break;
        const int Count=Parts(Length(Path[K]-Root),S);
        if(!Count||!Allowed(Root,Path[K]))continue;
        Out={true,Root+(Path[K]-Root)*(1.0/Count),K};
    }
    return Out;
}
struct GridFrame
{
    Vec2 Origin{}; // world cm after scene-coordinate conversion; translation ONLY
    Vec2 Local(Vec2 World)const{return World-Origin;}
    Vec2 World(Vec2 LocalPoint)const{return LocalPoint+Origin;}
    bool Contains(Vec2 P)const
    {P=Local(P);return Finite(P)&&P.X>=-900&&P.X<=900&&P.Y>=-900&&P.Y<=900;}
};
struct FrameBudget
{
    std::uint64_t Frame=0;bool Started=false;int Left=0,Used=0,Cap=0;
    explicit FrameBudget(int Limit):Cap(std::max(0,Limit)){}
    void Begin(std::uint64_t Id)
    {if(!Started||Id>Frame){Frame=Id;Started=true;Left=Cap;Used=0;}}
    bool Take(){if(!Started||Left<=0)return false;--Left;++Used;return true;}
};
struct Revisions
{
    std::uint64_t Geometry=0,RelevantEndpoints=0;
    void GeometryChanged(){++Geometry;}
    void RelevantEndpointChanged(){++RelevantEndpoints;}
    void ObserveEndpoint(bool Relevant,Vec2 Before,Vec2 After)
    {if(Relevant&&(Before.X!=After.X||Before.Y!=After.Y))RelevantEndpointChanged();}
};
struct FairPlanningQueue
{
    std::deque<int> Pending;
    bool Request(int Id)
    {
        if(std::find(Pending.begin(),Pending.end(),Id)!=Pending.end())return true;
        if(Pending.size()>=4096)return false;
        Pending.push_back(Id);return true;
    }
    bool IsTurn(int Id)const{return !Pending.empty()&&Pending.front()==Id;}
    void Retire(int Id){auto I=std::find(Pending.begin(),Pending.end(),Id);if(I!=Pending.end())Pending.erase(I);}
    // Actor may plan only when this ID is also in the normal scheduled window.
    // Suspended/destroyed requests must retire, otherwise the queue can block.
};
struct FailureCache
{
    bool Valid=false;Revisions Seen{};
    void Remember(Revisions R){Seen=R;Valid=true;}
    bool Matches(Revisions R)const
    {return Valid&&Seen.Geometry==R.Geometry&&Seen.RelevantEndpoints==R.RelevantEndpoints;}
};
struct TurnIntent
{
    bool Valid=false;std::uint64_t Cohort=0,Episode=0,Leg=0;double Heading=0;
    void Reset(){Valid=false;}
    double Target(std::uint64_t C,std::uint64_t E,std::uint64_t L,double Desired)
    {
        if(!Valid||C!=Cohort||E!=Episode||L!=Leg)
        {Valid=true;Cohort=C;Episode=E;Leg=L;Heading=Desired;}
        return Heading;
    }
};
}
