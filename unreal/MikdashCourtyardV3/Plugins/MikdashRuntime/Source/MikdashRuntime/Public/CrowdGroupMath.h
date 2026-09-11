#pragma once
#include "CrowdFieldMath.h"
#include <array>
#include <unordered_map>
#include <vector>

// Authored background social motion. No identity/kinship/access ruling is inferred.
// All lengths here are physical centimetres, independent of a world's amah.
namespace MikdashCrowdGroups
{
using MikdashCrowd::Vec2;
constexpr int MaxMembers=6;
constexpr double MinSeparationCm=80.0;
constexpr double MaxStepCm=100.0;
struct Settings { double SpacingCm=120.0, SlowLagCm=100.0, WaitLagCm=250.0; };
enum class TravelMode { Forward, Returning, Paused };
struct Travel { TravelMode Mode=TravelMode::Forward;double FormationHeading=0; };
inline void RejectedLeaderMove(Travel& State,double DistanceToAnchor)
{
    // No alternating return/forward goals at an obstructed anchor. A repeated
    // return failure is an explicit pause, not an invented detour through bodies.
    State.Mode=State.Mode!=TravelMode::Forward || !std::isfinite(DistanceToAnchor) || DistanceToAnchor<120
        ?TravelMode::Paused:TravelMode::Returning;
}
inline void SuccessfulLeaderMove(Travel& State,double DistanceToAnchor,double Heading)
{
    if(State.Mode==TravelMode::Paused || !std::isfinite(DistanceToAnchor)||!std::isfinite(Heading)) return;
    State.FormationHeading=Heading;
    if(State.Mode==TravelMode::Returning&&DistanceToAnchor<120) State.Mode=TravelMode::Forward;
}
inline bool FollowPlane(double CurrentTracedZ,double PlaneFromZ,double PlaneToZ,double& OutZ)
{
    if(!std::isfinite(CurrentTracedZ)||!std::isfinite(PlaneFromZ)||!std::isfinite(PlaneToZ)) return false;
    const double Next=CurrentTracedZ+(PlaneToZ-PlaneFromZ);
    if(!std::isfinite(Next)) return false;
    OutZ=Next;return true;
}
struct Cohort
{
    std::array<int,MaxMembers> Members{{-1,-1,-1,-1,-1,-1}};
    int Count=0;
    uint32_t Identity=0;
    double Speed=0;
};
inline int SingleBudget(int Count,double Ratio)
{
    if(Count<=0) return 0;
    const double Safe=std::isfinite(Ratio)?MikdashCrowd::Clamp(Ratio,0.0,1.0):.15;
    int Singles=static_cast<int>(std::round(Count*Safe));
    if(Count-Singles==1) ++Singles;
    return Singles;
}
inline int NextSize(int Remaining,int& Singles,uint32_t Seed,uint32_t Identity)
{
    if(Remaining<=0) return 0;
    Singles=std::max(0,std::min(Remaining,Singles));
    const int Grouped=Remaining-Singles;
    const double Entities=Singles+Grouped/4.0;
    if(Grouped<2 || (Singles>0 && MikdashCrowd::HashUnit(Seed,Identity,801u)<Singles/Entities))
    { Singles=std::max(0,Singles-1);return 1; }
    int Size=std::min(Grouped,2+static_cast<int>(MikdashCrowd::HashUnit(Seed,Identity,802u)*5));
    Size=std::min(Size,MaxMembers);
    if(Grouped-Size==1) { if(Size<MaxMembers) ++Size;else --Size; }
    return Size;
}
inline Vec2 Offset(int Member,uint32_t Seed,uint32_t Identity,double Spacing)
{
    if(Member<=0 || Member>=MaxMembers) return {};
    const Vec2 Layout[]={{0,0},{-.15,1.0},{-1.0,-.55},{-1.15,.65},{-2.0,-.55},{-2.15,.70}};
    const double S=std::max(110.0,std::min(180.0,Spacing));
    const double Jitter=MikdashCrowd::HashRange(Seed,Identity,810u+static_cast<uint32_t>(Member),-.07,.07);
    return {Layout[Member].X*S, (Layout[Member].Y+Jitter)*S};
}
inline Vec2 WorldOffset(const Vec2& Local,double Heading)
{
    const Vec2 Forward=MikdashCrowd::FromDegrees(Heading);
    return {Forward.X*Local.X-Forward.Y*Local.Y,Forward.Y*Local.X+Forward.X*Local.Y};
}
struct Command { Vec2 Direction{};double Speed=0,MaxLag=0;bool Waiting=false,Valid=false; };
inline Command Steering(const Cohort& Group,int Member,const Vec2* Positions,double LeaderHeading,
    const Vec2& LeaderDirection,const Settings& Config,uint32_t Seed,bool PartyPaused=false)
{
    Command Out;
    if(!Positions || Group.Count<2 || Group.Count>MaxMembers || Member<0 || Member>=Group.Count
        || !std::isfinite(Group.Speed) || Group.Speed<0 || !std::isfinite(LeaderHeading)
        || !MikdashCrowd::Finite(LeaderDirection) || !std::isfinite(Config.SpacingCm)
        || !std::isfinite(Config.SlowLagCm) || !std::isfinite(Config.WaitLagCm)) return Out;
    for(int I=0;I<Group.Count;++I) if(!MikdashCrowd::Finite(Positions[I])) return Out;
    for(int I=1;I<Group.Count;++I)
    {
        const Vec2 Target=Positions[0]+WorldOffset(Offset(I,Seed,Group.Identity,Config.SpacingCm),LeaderHeading);
        Out.MaxLag=std::max(Out.MaxLag,MikdashCrowd::Length(Target-Positions[I]));
    }
    const double Soft=std::max(25.0,Config.SlowLagCm),Hard=std::max(Soft+25.0,Config.WaitLagCm);
    const double Pace=PartyPaused||Out.MaxLag>=Hard?0.0:(Out.MaxLag<=Soft?1.0:1.0-.65*(Out.MaxLag-Soft)/(Hard-Soft));
    Out.Waiting=Pace==0;Out.Valid=true;
    if(Member==0) { Out.Direction=LeaderDirection;Out.Speed=Group.Speed*Pace;return Out; }
    const Vec2 Forward=MikdashCrowd::FromDegrees(LeaderHeading);
    const Vec2 Target=Positions[0]+WorldOffset(Offset(Member,Seed,Group.Identity,Config.SpacingCm),LeaderHeading);
    const Vec2 Error=Target-Positions[Member];
    const double Distance=MikdashCrowd::Length(Error);
    if(Pace==0 && Distance<25) { Out.Direction=Forward;return Out; }
    const double Along=Error.X*Forward.X+Error.Y*Forward.Y;
    Out.Direction=MikdashCrowd::Normalized(Error+Forward*(std::max(110.0,Config.SpacingCm)*Pace));
    Out.Speed=Pace==0?std::min(Group.Speed,Distance*.8)
        :MikdashCrowd::Clamp(Group.Speed*Pace+Along*.8,0.0,Group.Speed*1.15);
    return Out;
}

struct Geometry
{
    const Vec2* Zone=nullptr;int ZoneCount=0;
    const Vec2* Protected=nullptr;const int* Starts=nullptr;const int* Counts=nullptr;int ProtectedCount=0;
    double EdgeMargin=100,ProtectedMargin=150;
};
inline bool SegmentAllowed(const Geometry& World,const Vec2& From,const Vec2& To)
{
    using namespace MikdashCrowd;
    if(!Finite(From)||!Finite(To)||Length(To-From)>MaxStepCm+.001
        ||!std::isfinite(World.EdgeMargin)||!std::isfinite(World.ProtectedMargin)) return false;
    const int Samples=std::max(1,static_cast<int>(std::ceil(Length(To-From)/20.0)));
    for(int Sample=0;Sample<=Samples;++Sample)
    {
        const Vec2 P=From+(To-From)*(static_cast<double>(Sample)/Samples);
        // 34cm physical capsule radius + 10cm half sampling interval.
        if(!PointInPolygonWithMargin(World.Zone,World.ZoneCount,P,std::max(44.0,World.EdgeMargin))
            ||PointInAnyProtected(World.Protected,World.Starts,World.Counts,World.ProtectedCount,P,
                std::max(44.0,World.ProtectedMargin))) return false;
    }
    return true;
}

// Bounded spatial hash. No all-agent scan: at most sixteen cells, sixty-four
// occupants each. Full cells refuse insertion/movement rather than lose coverage.
class SpatialIndex
{
    struct Entry { int Id;Vec2 Position; };
    std::unordered_map<uint64_t,std::vector<Entry>> Cells;
    static constexpr double CellCm=200.0;
    static constexpr std::size_t MaxCell=64;
    static int32_t Coord(double Value) { return static_cast<int32_t>(std::floor(Value/CellCm)); }
    static uint64_t Key(int32_t X,int32_t Y)
    { return (static_cast<uint64_t>(static_cast<uint32_t>(X))<<32)|static_cast<uint32_t>(Y); }
    static bool Safe(const Vec2& P)
    { return MikdashCrowd::Finite(P)&&std::abs(P.X)<1e10&&std::abs(P.Y)<1e10; }
public:
    void Clear() { Cells.clear(); }
    bool SegmentClear(const Vec2& From,const Vec2& To,int IgnoreId,double Separation=MinSeparationCm) const
    {
        if(!Safe(From)||!Safe(To)||!std::isfinite(Separation)||Separation<MinSeparationCm||Separation>100
            ||MikdashCrowd::Length(To-From)>MaxStepCm+.001) return false;
        const int32_t MinX=Coord(std::min(From.X,To.X)-Separation),MaxX=Coord(std::max(From.X,To.X)+Separation);
        const int32_t MinY=Coord(std::min(From.Y,To.Y)-Separation),MaxY=Coord(std::max(From.Y,To.Y)+Separation);
        if((MaxX-MinX+1)*(MaxY-MinY+1)>16) return false;
        const Vec2 Delta=To-From;const double Length2=Delta.X*Delta.X+Delta.Y*Delta.Y;
        for(int32_t X=MinX;X<=MaxX;++X) for(int32_t Y=MinY;Y<=MaxY;++Y)
        {
            const auto It=Cells.find(Key(X,Y));if(It==Cells.end()) continue;
            for(const auto& Item:It->second)
            {
                if(Item.Id==IgnoreId) continue;
                const Vec2 Relative=Item.Position-From;
                const double T=Length2>0?MikdashCrowd::Clamp((Relative.X*Delta.X+Relative.Y*Delta.Y)/Length2,0.0,1.0):0;
                if(MikdashCrowd::Length(Item.Position-(From+Delta*T))<Separation) return false;
            }
        }
        return true;
    }
    bool Insert(int Id,const Vec2& P)
    {
        if(!Safe(P)||!SegmentClear(P,P,Id)) return false;
        auto& Bucket=Cells[Key(Coord(P.X),Coord(P.Y))];
        if(Bucket.size()>=MaxCell) return false;
        for(const auto& E:Bucket) if(E.Id==Id) return false;
        Bucket.push_back({Id,P});return true;
    }
    void Remove(int Id,const Vec2& P)
    {
        if(!Safe(P)) return;
        const auto It=Cells.find(Key(Coord(P.X),Coord(P.Y)));if(It==Cells.end()) return;
        auto& Bucket=It->second;
        for(std::size_t I=0;I<Bucket.size();++I) if(Bucket[I].Id==Id)
        { Bucket[I]=Bucket.back();Bucket.pop_back();break; }
        if(Bucket.empty()) Cells.erase(It);
    }
    /** Move an occupant to a point already validated by the caller (a committed vertex-animation
     * segment: SegmentClear was asked when the segment was planned). No clearance test here --
     * refusing would leave the index holding a position the figure is no longer at. */
    bool Relocate(int Id,const Vec2& From,const Vec2& To)
    {
        if(!Safe(From)||!Safe(To)) return false;
        const uint64_t Old=Key(Coord(From.X),Coord(From.Y)),New=Key(Coord(To.X),Coord(To.Y));
        auto It=Cells.find(Old);if(It==Cells.end()) return false;
        if(Old==New)
        { for(auto& E:It->second) if(E.Id==Id){E.Position=To;return true;}return false; }
        bool Found=false;for(const auto& E:It->second) if(E.Id==Id) Found=true;
        if(!Found) return false;
        auto& Destination=Cells[New];if(Destination.size()>=MaxCell) return false;
        Destination.push_back({Id,To});Remove(Id,From);return true;
    }
    bool Move(int Id,const Vec2& From,const Vec2& To)
    {
        if(!SegmentClear(From,To,Id)) return false;
        const uint64_t Old=Key(Coord(From.X),Coord(From.Y)),New=Key(Coord(To.X),Coord(To.Y));
        auto It=Cells.find(Old);if(It==Cells.end()) return false;
        if(Old==New)
        { for(auto& E:It->second) if(E.Id==Id){E.Position=To;return true;}return false; }
        bool Found=false;for(const auto& E:It->second) if(E.Id==Id) Found=true;
        if(!Found) return false;
        auto& Destination=Cells[New];if(Destination.size()>=MaxCell) return false;
        Destination.push_back({Id,To});Remove(Id,From);return true;
    }
};
}
