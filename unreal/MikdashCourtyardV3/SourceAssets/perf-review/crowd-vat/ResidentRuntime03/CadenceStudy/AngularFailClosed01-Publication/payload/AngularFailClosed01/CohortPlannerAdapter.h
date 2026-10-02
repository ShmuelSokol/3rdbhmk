#pragma once
#include "RouteContinuityStudy.h"
#include "BoundedRoutePlanner.h"
#include <memory>
#include <functional>
// New study integration. No production actor or material dependency.
namespace CohortPlannerStudy
{
using namespace ActualHorizonReview;
struct WaitLatch
{
    RuntimePortReview::TurnIntent Intent;
    double Turn(int Cohort,int Episode,int Leg,double Desired,double Current,double Seconds)
    {return MikdashCrowd::SteerHeading(Current,Intent.Target(Cohort,Episode,Leg,Desired),Seconds,90);}
};
struct Episode:CadenceRecoveryStudy::Episode
{
    struct SearchState
    {
        std::unique_ptr<Planner> Search;Revisions Seen{};
        Vec2 Goal{};RuntimePortReview::Steps Limits{};bool Deferred=false;
        std::function<bool(Vec2,Vec2)> FrozenGate;
        bool EndpointChanged=false;
    };
    SearchState Searches[MikdashCrowdGroups::MaxMembers];
    bool Deferred=false;int BudgetDeferrals=0,Invalidations=0;
    int EndpointChangesDuringSearch=0,CompletedAfterEndpointChange=0;
    template<class Gate> void Enter(int Count,const Vec2* Targets,MikdashCrowdGroups::TravelMode Mode,double Now,Gate&& Allowed)
    {
        for(auto& Q:Searches)Q=SearchState{};
        CadenceRecoveryStudy::Episode::Enter(Count,Targets,Mode,Now,Allowed);
    }
    template<class Gate> bool PrepareActual(int I,Vec2 Root,RuntimePortReview::Steps S,GridFrame Grid,Budget& Work,Revisions Stamp,RuntimePortReview::FairPlanningQueue& Queue,int AgentId,Gate&& Allowed)
    {
        auto& T=Members[I];auto& Q=Searches[I];Deferred=false;Owner=I;
        const auto Check=[&](Vec2 A,Vec2 B)
        {
            if(!Work.Query()){Deferred=true;return false;}
            return Allowed(A,B);
        };
        if(Length(Goals[I]-Root)<25)return false;
        if(!S.Valid){++Unplayable;T.FailedRevision=Revision;return false;}
        if(T.Latched)
        {
            const double D=Length(T.Target-Root);
            if(D>=S.Minimum-1e-7&&D<=S.Maximum+1e-7&&Check(Root,T.Target)){Target=T.Target;return true;}
            if(Deferred){++BudgetDeferrals;return false;}
            T.Latched=false;T.Path.clear();Q.Search.reset();
        }
        const bool Changed=Q.Seen.Geometry!=Stamp.Geometry||Q.Seen.RelevantEndpoints!=Stamp.RelevantEndpoints
            ||Length(Q.Goal-Goals[I])>1e-8||Q.Limits.Minimum!=S.Minimum||Q.Limits.Maximum!=S.Maximum;
        if(Changed)
        {
            if(Q.Search&&Q.Seen.Geometry!=Stamp.Geometry){Q.Search.reset();++Invalidations;}
            else if(Q.Search&&Q.Seen.RelevantEndpoints!=Stamp.RelevantEndpoints)
            {Q.EndpointChanged=true;++EndpointChangesDuringSearch;}
            T.FailedRevision=-1;Q.Seen=Stamp;Q.Goal=Goals[I];Q.Limits=S;
        }
        if(T.FailedRevision==Revision&&!Changed)return false;
        while(T.At<T.Path.size()&&Length(T.Path[T.At]-Root)<1e-6)++T.At;
        bool PathClear=T.At<T.Path.size()&&Check(Root,T.Path[T.At]);
        if(Deferred){++BudgetDeferrals;return false;}
        if(!PathClear)
        {
            if(!Queue.Request(AgentId)||!Queue.IsTurn(AgentId)){Deferred=true;++BudgetDeferrals;return false;}
            if(!Q.Search)
            {Q.Search=std::make_unique<Planner>(Root,Goals[I],S,Grid,Stamp);Q.FrozenGate=Allowed;Q.EndpointChanged=false;++Plans;}
            const int Before=Q.Search->TotalExpanded,BeforeQ=Q.Search->TotalQueries,BeforeCalls=Work.Calls;
            // Search graph remains immutable over deferral. Changed endpoints
            // must affect live connector/target checks, not erase A* progress.
            const auto Result=Q.Search->Pump(Work,Q.Search->Revision,Q.FrozenGate);
            if(Result!=Status::Pending){Queue.Retire(AgentId);}
            else if(Work.Calls>BeforeCalls)
            {
                // Rotate only after an admitted call; budget exhaustion alone
                // must not let a repeatedly early visitor steal next admission.
                Queue.Retire(AgentId);Queue.Request(AgentId);
            }
            Expanded+=Q.Search->TotalExpanded-Before;Queries+=Q.Search->TotalQueries-BeforeQ;
            PeakExpanded=std::max(PeakExpanded,Q.Search->TotalExpanded);
            if(Result==Status::Pending){Deferred=true;++BudgetDeferrals;return false;}
            if(Result==Status::Stale){Q.Search.reset();Deferred=true;++Invalidations;return false;}
            if(Result!=Status::Found){++PlannerFailures;T.FailedRevision=Revision;Q.Search.reset();return false;}
            if(!T.Path.empty())++Replans;
            if(Q.EndpointChanged)++CompletedAfterEndpointChange;
            T.Path=Q.Search->Path;T.At=1;Q.Search.reset();
        }
        auto Choice=SelectExecutable(Root,Goals[I],T.Path,T.At,S,Check);
        if(Deferred){++BudgetDeferrals;return false;}
        if(!Choice.Valid){++Unplayable;T.FailedRevision=Revision;return false;}
        T.At=Choice.Cursor;T.Target=Choice.Point;T.Latched=true;Target=T.Target;return true;
    }
};
}
