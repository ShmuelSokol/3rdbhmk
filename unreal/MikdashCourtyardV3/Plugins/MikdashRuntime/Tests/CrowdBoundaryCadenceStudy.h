#pragma once
#include "CrowdGroupMath.h"

// Rejected offline candidate: group progress regresses. Never adopted by runtime.
namespace MikdashCrowdGroups
{
// Predict an upper bound on the next moving replan at a steady frame duration.
// Horizon expiry is frame-quantized, then a budgeted visitor may wait up to
// FramesPerSweep-1 more frames. Do not assume evenly spaced visits when the
// population is not divisible by the budget. Hitches remain a prediction limit.
inline double BoundaryReplanSeconds(double Horizon,double FrameSeconds,int FramesPerSweep)
{
    if(!std::isfinite(Horizon)||Horizon<=0||!std::isfinite(FrameSeconds)||FrameSeconds<=0
        ||FramesPerSweep<1) return 0;
    const double Frames=std::ceil(Horizon/FrameSeconds)+static_cast<double>(FramesPerSweep-1);
    const double Seconds=Frames*FrameSeconds;
    return std::isfinite(Seconds)?Seconds:0;
}
// Guidance distance only: the immediate yaw update still gets its original
// one-frame allowance (including SteerHeading's 0.25s clamp). Preserve the
// original 100..400cm bounds and 0.1rad/s denominator guard. Invalid input
// disables guidance through FindBoundaryRoute, never grants a movement.
inline double BoundaryLookAhead(double Speed,double Horizon,double FrameSeconds,
    double TurnSeconds,double TurnDegreesPerSecond,int FramesPerSweep)
{
    const double Replan=BoundaryReplanSeconds(Horizon,FrameSeconds,FramesPerSweep);
    if(Replan<=0||!std::isfinite(Speed)||Speed<=0||!std::isfinite(TurnSeconds)||TurnSeconds<0
        ||!std::isfinite(TurnDegreesPerSecond)||TurnDegreesPerSecond<0) return 0;
    const double TurnFraction=std::min(1.0,std::min(TurnSeconds,.25)/Replan);
    const double Rate=std::max(.1,(TurnDegreesPerSecond*MikdashCrowd::Pi/180.0)*TurnFraction);
    return MikdashCrowd::Clamp(Speed*(Horizon+2.0/Rate),100.0,400.0);
}

}
