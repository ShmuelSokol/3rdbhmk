#pragma once
#include "MikdashSceneUnitsMath.h"
#include "MikdashPeopleDirectory.h"

namespace MikdashPopulationScene
{
enum class Scope { Temple, Metric, Unknown };
inline Scope CrowdZoneScope(const std::string& Name)
{
    if (Name=="OuterCourtEast" || Name=="OuterCourtWestTerrace") return Scope::Temple;
    if (Name=="MountPlatformDeck" || Name=="KotelPlazaStrip" || Name=="StreetBateiMahase" || Name=="KotelApproachCorridor") return Scope::Metric;
    return Scope::Unknown;
}
struct Rect { double MinX=0, MinY=0, MaxX=0, MaxY=0; };
struct PaddedFootprint { Rect Source; double PadX=0, PadY=0; };
inline bool Footprint(const std::string& Name, PaddedFootprint& Out)
{
    if (Name=="SanctuaryBlockAndFoundations") Out={{-7500,-2500,-2500,2500},100,100};
    else if (Name=="InnerCourtPlatform") Out={{-2800,-2800,2800,2800},100,100};
    else if (Name=="EastGateCorridor") Out={{2500,-700,8600,700},100,50};
    else if (Name=="NorthLateralGateCorridor") Out={{-700,2500,700,8100},50,100};
    else if (Name=="SouthLateralGateCorridor") Out={{-700,-8100,700,-2500},50,100};
    else return false;
    return true;
}
inline Rect Padded(const PaddedFootprint& F)
{ return {F.Source.MinX-F.PadX,F.Source.MinY-F.PadY,F.Source.MaxX+F.PadX,F.Source.MaxY+F.PadY}; }
inline bool TryFootprint(const MikdashSceneUnits::Frame& Frame, const PaddedFootprint& Input, Rect& Out)
{
    MikdashUnits::PointCm Lo,Hi;
    if (!MikdashSceneUnits::TryLegacyTemplePoint(Frame,{Input.Source.MinX,Input.Source.MinY,0},Lo)
        || !MikdashSceneUnits::TryLegacyTemplePoint(Frame,{Input.Source.MaxX,Input.Source.MaxY,0},Hi)) return false;
    Out={Lo.X-Input.PadX,Lo.Y-Input.PadY,Hi.X+Input.PadX,Hi.Y+Input.PadY}; return true;
}
inline bool Near(double A,double B) { return std::abs(A-B)<.01; }
inline bool IsRect(const std::vector<MikdashRoute::Point2>& Points,const Rect& R)
{
    if (Points.size()!=4) return false;
    unsigned Mask=0;
    for(const auto& P:Points)
    {
        const int X=Near(P.X,R.MinX)?0:(Near(P.X,R.MaxX)?1:-1);
        const int Y=Near(P.Y,R.MinY)?0:(Near(P.Y,R.MaxY)?1:-1);
        if(X<0 || Y<0) return false;
        const unsigned Bit=1u<<static_cast<unsigned>(X+2*Y);
        if(Mask&Bit) return false;
        Mask|=Bit;
    }
    return Mask==15;
}
inline bool PointInZone(const MikdashSceneUnits::Frame& Frame,MikdashPeople::Zone Zone,const MikdashRoute::Point2& Point)
{
    if(!MikdashSceneUnits::Valid(Frame) || !MikdashRoute::Finite(Point)) return false;
    if(Zone==MikdashPeople::Zone::MountDeck) return MikdashPeople::PointInZone(Zone,Point);
    if(Zone!=MikdashPeople::Zone::OuterCourt) return false;
    MikdashUnits::PointCm Lo,Hi,InnerLo,InnerHi;
    if(!MikdashSceneUnits::TryLegacyTemplePoint(Frame,{1500,-6000,0},Lo)
        || !MikdashSceneUnits::TryLegacyTemplePoint(Frame,{7000,6000,0},Hi)
        || !MikdashSceneUnits::TryLegacyTemplePoint(Frame,{0,-900,0},InnerLo)
        || !MikdashSceneUnits::TryLegacyTemplePoint(Frame,{0,900,0},InnerHi)) return false;
    return Point.X>=Lo.X && Point.X<=Hi.X && Point.Y>Lo.Y && Point.Y<Hi.Y
        && (Point.Y<=InnerLo.Y || Point.Y>=InnerHi.Y);
}
inline bool TryFloor(const MikdashSceneUnits::Frame& Frame,MikdashPeople::Zone Zone,double& Floor)
{
    if(!MikdashSceneUnits::Valid(Frame)) return false;
    if(Zone==MikdashPeople::Zone::MountDeck) { Floor=0; return true; }
    if(Zone!=MikdashPeople::Zone::OuterCourt) return false;
    MikdashUnits::PointCm P;
    if(!MikdashSceneUnits::TryLegacyTemplePoint(Frame,{0,0,300},P)) return false;
    Floor=P.Z; return true;
}
// The reviewed people-v3 file uses exactly these named-by-coordinate gaze anchors.
// This is an explicit source allowlist, never a magnitude-based scope inference.
inline bool TryLook(const MikdashSceneUnits::Frame& Frame,const MikdashUnits::PointCm& Legacy,MikdashUnits::PointCm& Out)
{
    if(Frame.CoordinateRevision==MikdashSceneUnits::Revision::Legacy50V1)
        return MikdashSceneUnits::TryMetricPoint(Frame,Legacy,Out);
    if(Near(Legacy.X,11500) && Near(Legacy.Y,0) && Near(Legacy.Z,0))
        return MikdashSceneUnits::TryMetricPoint(Frame,Legacy,Out);
    if((Near(Legacy.X,0)||Near(Legacy.X,7800)) && Near(Legacy.Y,0) && Near(Legacy.Z,300))
        return MikdashSceneUnits::TryLegacyTemplePoint(Frame,Legacy,Out);
    if(Near(Legacy.X,8600) && Near(Legacy.Y,0) && Near(Legacy.Z,0))
        return MikdashSceneUnits::TryLegacyTemplePoint(Frame,Legacy,Out);
    return false;
}
inline bool TryPerson(const MikdashSceneUnits::Frame& Frame,const MikdashPeople::Person& Legacy,
                      MikdashPeople::Person& Out,std::string& Error)
{
    if(!MikdashSceneUnits::Valid(Frame)) { Error="invalid scene units"; return false; }
    if(Legacy.Where!=MikdashPeople::Zone::OuterCourt && Legacy.Where!=MikdashPeople::Zone::MountDeck)
    { Error="unknown resident coordinate scope"; return false; }
    MikdashPeople::Person Candidate=Legacy;
    double Floor=0;
    if(!TryFloor(Frame,Legacy.Where,Floor)) return false;
    std::vector<MikdashRoute::Point2> Points;
    std::vector<double> Pauses; std::vector<std::string> Labels;
    for(std::size_t I=0;I<Legacy.Route.size();++I)
    {
        const auto& Source=Legacy.Route[I]; auto& Target=Candidate.Route[I];
        if(Frame.CoordinateRevision==MikdashSceneUnits::Revision::Selected48V1
            && !Near(Source.Z,MikdashPeople::ZoneFloorZ(Legacy.Where)))
        { Error="source support is not exact legacy floor; possible prior conversion"; return false; }
        MikdashUnits::PointCm Feet,Look;
        const bool Okay=Legacy.Where==MikdashPeople::Zone::OuterCourt
            ? MikdashSceneUnits::TryLegacyTemplePoint(Frame,{Source.X,Source.Y,Source.Z},Feet)
            : MikdashSceneUnits::TryMetricPoint(Frame,{Source.X,Source.Y,Source.Z},Feet);
        if(!Okay || !TryLook(Frame,{Source.LookX,Source.LookY,Source.LookZ},Look))
        { Error="invalid support or unclassified gaze anchor"; return false; }
        if(!PointInZone(Frame,Legacy.Where,{Feet.X,Feet.Y}) || std::abs(Feet.Z-Floor)>MikdashRoute::FloorToleranceCm)
        { Error="converted feet outside current authored zone/floor"; return false; }
        Target.X=Feet.X;Target.Y=Feet.Y;Target.Z=Feet.Z;
        Target.LookX=Look.X;Target.LookY=Look.Y;Target.LookZ=Look.Z;
        Points.push_back({Feet.X,Feet.Y});Pauses.push_back(Source.PauseSeconds);Labels.push_back(Source.Label);
    }
    // Physical route length, waypoint spacing and pauses do not shrink with amot.
    if(!MikdashRoute::ValidateLoopGeometry(Points,Pauses,Labels,&Error)) return false;
    Out=std::move(Candidate);Error.clear();return true;
}
}
