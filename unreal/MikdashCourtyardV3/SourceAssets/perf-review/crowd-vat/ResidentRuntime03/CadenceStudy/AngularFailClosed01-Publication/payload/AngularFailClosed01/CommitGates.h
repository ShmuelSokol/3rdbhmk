#pragma once
#include "ScheduledAngular.h"
namespace CommitGatesStudy {
using namespace MikdashCrowd;using namespace MikdashCrowdGroups;
enum class Arrival {Committed,Deferred,Refused,Invalid};
template<class Agent,class Episode,class Index> Arrival CommitArrival(Agent& A,Episode& E,Index& Spacing,
 int Id,int Member,int Members,double Now,bool Enabled) {
    if(A.Walking&&Now<A.Motion.End)return Arrival::Deferred;
    if(Enabled&&A.Angular.Held&&!A.Angular.CanCommit(Now,A.Motion))return Arrival::Deferred;
    const Vec2 From=A.Motion.At(Now);
    const bool Completed=Enabled&&E.WasMoving(Member)&&A.Walking;
    if(Completed&&(!E.Members[Member].Moving||Length(From-E.Members[Member].Target)>1e-6))return Arrival::Invalid;
    // Stage turn rebase/history; no agent or episode publication on relocation failure.
    auto Turn=A.Angular;const bool Held=Enabled&&Turn.Held;
    if(Held&&!Turn.Commit(Now,A.Motion))return Arrival::Invalid;
    if(!Spacing.Relocate(Id,A.Anchor,From,Now))return Arrival::Refused;
    // Complete preconditions were checked without mutation before Relocate.
    // Single-threaded fixture: no concurrency/exception guarantee is claimed.
    if(Completed)E.Complete(Member,From,Members);
    if(Enabled){A.Angular=Turn;if(Held)A.Yaw=Turn.Core.Current.Yaw;A.Angular.SnapshotLinear(Now,A.Motion);}
    A.Anchor=From;A.AnchorTime=Now;A.Motion={From,From,Now,Now};
    return Arrival::Committed;
}
template<class Agent,class Index,class Publish> bool ReserveWalk(Agent& A,Index& Spacing,int Id,
 Vec2 From,Vec2 To,double Now,double Horizon,Publish&& OnSuccess) {
    if(!Spacing.Reserve(Id,From,To,Now,Horizon))return false;
    A.Walking=true;A.Motion={From,To,Now,Now+Horizon};OnSuccess();return true;
}
}
