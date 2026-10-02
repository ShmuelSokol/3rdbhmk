#pragma once
#include "RotatingEnvelope.h"
#include <array>
#include <limits>
// CPU port for AngularVATStudy01's exact proposed channels. Not yet connected
// to the cohort visit loop; no material or actor edits in this study.
namespace AngularControllerStudy
{
using namespace RotatingEnvelopeStudy;
struct State
{
    double Yaw=0;
    float TurnStartGameTime=0,TurnDeltaDegrees=0;
    Vec2 Root{};Body Envelope{};
};
inline double Angle(const State& S,double Time)
{
    const double D=S.TurnDeltaDegrees;
    return (D<0?-1:1)*std::min(std::max(0.,Time-S.TurnStartGameTime)*90.,std::abs(D));
}
inline bool Complete(const State& S,double Now)
{
    if(S.TurnDeltaDegrees==0)return true;
    const double End=static_cast<double>(S.TurnStartGameTime)+std::abs(static_cast<double>(S.TurnDeltaDegrees))/90.;
    float Ceiling=static_cast<float>(End);
    if(Ceiling<End)Ceiling=std::nextafter(Ceiling,std::numeric_limits<float>::infinity());
    Ceiling=std::nextafter(Ceiling,std::numeric_limits<float>::infinity());
    return static_cast<float>(Now)>=Ceiling;
}
inline std::array<float,4> Channels(const State& Current,const State& Old)
{return {{Current.TurnStartGameTime,Current.TurnDeltaDegrees,Old.TurnStartGameTime,Old.TurnDeltaDegrees}};}
struct Port
{
    State Current{},Previous{};float HistoryUpdatedAt=0;
    void Snapshot(double Now){Previous=Current;HistoryUpdatedAt=static_cast<float>(Now);}
    template<class ReserveEnvelope> bool Begin(double Target,double Now,const MotionReservation& Linear,ReserveEnvelope&& Hold)
    {
        if(!std::isfinite(Target)||!std::isfinite(Now)||Now<0||Now<Linear.End||Current.TurnDeltaDegrees!=0||!Current.Envelope.Known)return false;
        const float Start=static_cast<float>(Now);double Delta=WrapDegrees(Target-Current.Yaw);if(Delta==-180)Delta=180;
        if(!Hold(Current.Root,Current.Envelope))return false;
        Snapshot(Now);Current.TurnStartGameTime=Start;Current.TurnDeltaDegrees=static_cast<float>(Delta);return true;
    }
    bool Rebase(double Now)
    {
        if(!Complete(Current,Now))return false;
        if(Current.TurnDeltaDegrees!=0){Snapshot(Now);Current.Yaw=WrapDegrees(Current.Yaw+Current.TurnDeltaDegrees);Current.TurnDeltaDegrees=0;}
        return true;
    }
    template<class Ground,class Sweep,class CanReserve> bool Translation(double Now,const MotionReservation& Linear,Ground&& G,Sweep&& S,CanReserve&& R)const
    {
        // Successful completion is not enough: rebase at a scheduled visit
        // first, then call the fresh gates. No backdated movement.
        return Now>=Linear.End&&Current.TurnDeltaDegrees==0&&G()&&S()&&R();
    }
};
inline Vec2 Rotate(Vec2 P,double Degrees)
{const auto D=FromDegrees(Degrees);return {D.X*P.X-D.Y*P.Y,D.Y*P.X+D.X*P.Y};}
inline Vec2 PreviousPosedWorld(const Port& P,Vec2 Rest,Vec2 OldDelta,Vec2 NewDelta,double PreviousTime)
{
    if(PreviousTime<P.HistoryUpdatedAt)
    {
        const Vec2 OldPosed=Rotate(Rest+OldDelta,Angle(P.Previous,PreviousTime));
        return P.Previous.Root+Rotate(Rotate(OldPosed,P.Previous.Yaw-P.Current.Yaw),P.Current.Yaw);
    }
    return P.Current.Root+Rotate(Rest+NewDelta,P.Current.Yaw+Angle(P.Current,PreviousTime));
}
}
