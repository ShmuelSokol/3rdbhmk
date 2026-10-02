#pragma once
#include "CrowdFieldMath.h"
// OFFLINE ONLY. Orientation intent is latched to an absolute shared route leg,
// not a changing blocked goal. This grants NO translation or reservation.
// Apply only after own prior reservation completes, during peer-goal waiting.
namespace WaitTurnStudy
{
struct Latch
{
    int Leg=-1;double Heading=0;
    double Turn(int AbsoluteLeg,double RouteHeading,double Current,double Seconds)
    {
        if(Leg!=AbsoluteLeg){Leg=AbsoluteLeg;Heading=RouteHeading;}
        return MikdashCrowd::SteerHeading(Current,Heading,Seconds,90);
    }
};
}
