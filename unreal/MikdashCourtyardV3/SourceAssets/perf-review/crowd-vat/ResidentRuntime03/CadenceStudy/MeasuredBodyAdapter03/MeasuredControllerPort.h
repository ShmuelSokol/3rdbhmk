#pragma once
#include "MeasuredReservationIndex.h"
#include "baseline/CommitGates.h"
#include "baseline/RouteContinuityStudy.h"

namespace MeasuredBodyStudy {
// Actual existing CommitArrival/ReserveWalk and ScheduledTurn templates are
// instantiated with ReservationIndex; no fork of their actor-publication ordering.
// Caller must retain protected-region/route/speed gates BEFORE Walk, as before.
template<class Agent,class Publish> bool Walk(Agent& A,ReservationIndex& Index,int Id,
    Vec2 From,Vec2 To,double Now,double Horizon,Publish&& OnSuccess) {
    return CommitGatesStudy::ReserveWalk(A,Index,Id,From,To,Now,Horizon,std::forward<Publish>(OnSuccess));
}
template<class Agent,class Episode> CommitGatesStudy::Arrival Arrival(Agent& A,Episode& E,
    ReservationIndex& Index,int Id,int Member,int Members,double Now,bool Enabled) {
    return CommitGatesStudy::CommitArrival(A,E,Index,Id,Member,Members,Now,Enabled);
}
template<class Agent> bool Align(Agent& A,ReservationIndex& Index,int Id,double Target,double Now) {
    const Body Expected=Index.Envelope(Id),Given=A.Angular.Core.Current.Envelope;
    if(!Given.Known||Given.Radius!=Expected.Radius||Given.MinZ!=Expected.MinZ||Given.MaxZ!=Expected.MaxZ)return false;
    return A.Angular.Align(Target,Now,A.Motion,[&](Vec2 Root,Body) {
        // Hold includes the float-rounded scheduled rebase boundary. Same90deg/s
        // angular policy; no shape/vertical caps introduced here.
        auto Next=A.Angular.Core.Current;
        double Delta=MikdashCrowd::WrapDegrees(Target-Next.Yaw);if(Delta==-180)Delta=180;
        Next.TurnStartGameTime=static_cast<float>(Now);Next.TurnDeltaDegrees=static_cast<float>(Delta);
        const double Raw=Next.TurnStartGameTime+std::abs(static_cast<double>(Next.TurnDeltaDegrees))/90.;
        float End=static_cast<float>(Raw);if(End<Raw)End=std::nextafter(End,INFINITY);End=std::nextafter(End,INFINITY);
        const double Duration=static_cast<double>(End)-Now;
        if(!Index.Reserve(Id,Root,Root,Now,Duration))return false;
        A.Motion={Root,Root,Now,Now+Duration};return true;
    });
}
}
