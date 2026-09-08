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
// Authored selected48.v1 route repair, not a sourced Temple dimension or a general
// stretch. The exact reviewed 62 m source rectangles become 59.52 m at 48 cm.
// Moving only their outward edge by 25 physical cm yields 60.02 m, retaining the
// 60 m physical brief and staying inside the original 150 cm route corridor.
inline bool TryAuthoredRouteExtension(const MikdashSceneUnits::Frame& Frame,
    const MikdashPeople::Person& Legacy,MikdashPeople::Person& Candidate,std::string& Error)
{
    if(Frame.CoordinateRevision!=MikdashSceneUnits::Revision::Selected48V1) return true;
    Rect Expected;std::string Role;double DeltaY=25.0;std::size_t First=2;
    if(Legacy.Id=="chananel-ben-mattisyahu") { Expected={5600,1650,6800,3550};Role="levite"; }
    else if(Legacy.Id=="rivka-bas-yoezer") { Expected={1550,-3500,2850,-1700};Role="host";DeltaY=-25.0;First=0; }
    else if(Legacy.Id=="nechemya-ben-tzuriel") { Expected={1650,3700,2950,5500};Role="guide"; }
    else return true; // Unknown routes get no extension and still face the full validator.
    auto Fail=[&Error](const char* Why){Error=Why;return false;};
    if(!MikdashSceneUnits::Valid(Frame) || Frame.FixedOrigin.X!=0 || Frame.FixedOrigin.Y!=0 || Frame.FixedOrigin.Z!=0)
        return Fail("authored route extension requires reviewed selected48 origin zero");
    if(Legacy.Where!=MikdashPeople::Zone::OuterCourt || Legacy.Role!=Role
        || Legacy.Route.size()!=4 || Candidate.Route.size()!=4)
        return Fail("authored route extension source identity or shape changed");
    const MikdashRoute::Point2 SourcePoints[]={{Expected.MinX,Expected.MinY},{Expected.MaxX,Expected.MinY},
        {Expected.MaxX,Expected.MaxY},{Expected.MinX,Expected.MaxY}};
    const double Pauses[]={4,3,5,4};
    std::vector<MikdashRoute::Point2> Original;
    for(std::size_t I=0;I<4;++I)
    {
        const auto& S=Legacy.Route[I];const auto& C=Candidate.Route[I];
        const double LookX=(I==3 || (First==0 && I==1))?7800.0:0.0;
        // Exact immutable spatial signature. Narrative text remains the user's data.
        if(S.X!=SourcePoints[I].X || S.Y!=SourcePoints[I].Y || S.Z!=300
            || S.PauseSeconds!=Pauses[I] || S.LookX!=LookX || S.LookY!=0 || S.LookZ!=300)
            return Fail("authored route extension legacy spatial signature changed");
        MikdashUnits::PointCm Converted;
        if(!MikdashSceneUnits::TryLegacyTemplePoint(Frame,{S.X,S.Y,S.Z},Converted)
            || C.X!=Converted.X || C.Y!=Converted.Y || C.Z!=Converted.Z)
            return Fail("authored route extension input already adjusted or not freshly decoded");
        Original.push_back({C.X,C.Y});
    }
    if(std::abs(MikdashRoute::LoopLengthCm(Original)-5952.0)>1e-8)
        return Fail("authored route extension original physical length changed");
    auto Revised=Candidate;
    Revised.Route[First].Y+=DeltaY;Revised.Route[First+1].Y+=DeltaY;
    std::vector<MikdashRoute::Point2> Points;
    std::vector<double> Waits;std::vector<std::string> Labels;
    for(const auto& W:Revised.Route) { Points.push_back({W.X,W.Y});Waits.push_back(W.PauseSeconds);Labels.push_back(W.Label); }
    for(std::size_t I=0;I<Points.size();++I)
    {
        const auto& A=Points[I];const auto& B=Points[(I+1)%Points.size()];
        if(!PointInZone(Frame,Legacy.Where,A) || !MikdashRoute::SegmentWithinCorridor(A,B,Original))
            return Fail("authored route extension escaped original region or corridor");
        // Check the segment's region as well as its endpoints; no cross-gate shortcut.
        const int Samples=std::max(1,static_cast<int>(std::ceil(MikdashRoute::Distance(A,B)/25.0)));
        for(int Sample=0;Sample<=Samples;++Sample)
        {
            const double T=static_cast<double>(Sample)/Samples;
            if(!PointInZone(Frame,Legacy.Where,{A.X+(B.X-A.X)*T,A.Y+(B.Y-A.Y)*T}))
                return Fail("authored route extension segment left reviewed region");
        }
    }
    if(std::abs(MikdashRoute::LoopLengthCm(Points)-6002.0)>1e-8)
        return Fail("authored route extension final physical length changed");
    if(!MikdashRoute::ValidateLoopGeometry(Points,Waits,Labels,&Error)) return false;
    Candidate=std::move(Revised);return true;
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
    }
    if(!TryAuthoredRouteExtension(Frame,Legacy,Candidate,Error)) return false;
    for(const auto& Target:Candidate.Route)
    { Points.push_back({Target.X,Target.Y});Pauses.push_back(Target.PauseSeconds);Labels.push_back(Target.Label); }
    // Physical route length, waypoint spacing and pauses do not shrink with amot.
    if(!MikdashRoute::ValidateLoopGeometry(Points,Pauses,Labels,&Error)) return false;
    Out=std::move(Candidate);Error.clear();return true;
}
}
