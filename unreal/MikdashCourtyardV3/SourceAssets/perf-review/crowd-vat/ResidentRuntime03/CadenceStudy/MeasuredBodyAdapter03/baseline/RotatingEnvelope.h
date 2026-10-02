#pragma once
#include "CrowdGroupMath.h"
namespace RotatingEnvelopeStudy
{
using namespace MikdashCrowd;using namespace MikdashCrowdGroups;
struct Body
{
    double Radius=0,MinZ=0,MaxZ=0;bool Known=false;
};
inline Body FromPosedBounds(const Vec2* Horizontal,int Count,double MinZ,double MaxZ,double Scale)
{
    Body B;if(!Horizontal||Count<1||!std::isfinite(Scale)||Scale<=0||!std::isfinite(MinZ)||!std::isfinite(MaxZ)||MaxZ<MinZ)return B;
    for(int I=0;I<Count;++I){if(!Finite(Horizontal[I]))return {};B.Radius=std::max(B.Radius,Length(Horizontal[I])*Scale);}
    B.MinZ=MinZ*Scale;B.MaxZ=MaxZ*Scale;B.Known=B.Radius>0;return B;
}
inline bool Pair(const MotionReservation& Own,Body A,const MotionReservation& Peer,Body B,double Now)
{
    if(!A.Known||!B.Known)return false;
    // Conservative horizontal cylinders cover every yaw, every posed point in
    // the supplied envelope, full peer segments and indefinite endpoint holds.
    return ReservationDistance(Own,Peer,Now)>=std::max(80.,A.Radius+B.Radius)-1e-7;
}
template<class WorldGate> bool World(Vec2 From,Vec2 To,Body B,WorldGate&& Clear)
{return B.Known&&Clear(From,To,B.Radius,B.MinZ,B.MaxZ);}
}
