#pragma once
#include "ExecutableRouteStudy.h"
// OFFLINE ONLY: a single route-following owner per visitor, scheduled by the
// unchanged population window. Separate timed reservations may coexist; none
// is replaced early. Shared goal advancement remains an all-member barrier.
namespace CadenceRecoveryStudy
{
using namespace MikdashCrowd;using namespace MikdashCrowdGroups;
enum class Phase {Normal,Draining,Selecting,Turning,Moving,Blocked};
struct Track
{
    std::vector<Vec2> Path;size_t At=0;Vec2 Target{};
    bool Latched=false,Moving=false;int FailedRevision=-1;
};
struct Episode
{
    Phase State=Phase::Normal;TravelMode Resume=TravelMode::Forward;
    Vec2 Goals[MaxMembers]{},Target{};
    double LastProgress[MaxMembers]{},Entered=0;
    int Owner=-1,Entries=0,Completions=0,Steps=0,MemberSteps[MaxMembers]{};
    int Plans=0,Expanded=0,PeakExpanded=0,Queries=0,Replans=0,Unplayable=0;
    int Revision=0,ForwardLegs=0,PlannerFailures=0,ReservationWaits=0,YawOnly=0,Dwell=0;
    bool Invalid=false;Track Members[MaxMembers];
    void Observe(int I,double Distance,double Now){if(Distance>1e-8)LastProgress[I]=Now;}
    bool Stalled(int Count,double Now,double Watchdog) const
    {for(int I=0;I<Count;++I)if(Now-LastProgress[I]>Watchdog)return true;return false;}
    template<class Valid> void Enter(int Count,const Vec2* Targets,TravelMode Mode,double Now,Valid&& Allowed)
    {
        Resume=Mode;Entered=Now;++Entries;++Revision;State=Phase::Draining;Owner=-1;
        for(int I=0;I<Count;++I)
        {Goals[I]=Targets[I];Members[I]=Track{};if(!Finite(Targets[I])||!Allowed(Targets[I])){Invalid=true;State=Phase::Blocked;}}
    }
    void Advance(int Count,Vec2 Delta)
    {
        if(!Completions)++Completions;else ++ForwardLegs;
        ++Revision;
        for(int I=0;I<Count;++I){Goals[I]=Goals[I]+Delta;Members[I]=Track{};}
    }
    bool WasMoving(int I) const{return Members[I].Moving;}
    bool Complete(int I,Vec2 Root,int)
    {
        auto& T=Members[I];
        if(!T.Moving||Length(Root-T.Target)>1e-6){State=Phase::Blocked;return false;}
        T.Moving=false;T.Latched=false;++Steps;++MemberSteps[I];++Revision;return true;
    }
    void Reserved(int I){Members[I].Moving=true;++Revision;}
    template<class Gate> bool Prepare(int I,Vec2 Root,double Step,Gate&& Allowed)
    {
        auto& T=Members[I];Owner=I;
        if(Length(Goals[I]-Root)<25)return false;
        if(T.Latched)
        {
            if(Allowed(Root,T.Target)){Target=T.Target;return true;}
            T.Latched=false;T.Path.clear();
        }
        if(T.FailedRevision==Revision)return false;
        while(T.At<T.Path.size()&&Length(T.Path[T.At]-Root)<1e-6)++T.At;
        const double Minimum=Step*(119.95*.45/90);
        if(T.At>=T.Path.size()||!Allowed(Root,T.Path[T.At]))
        {
            if(!T.Path.empty())++Replans;
            const auto R=DetourRoutingStudy::Find(Root,Goals[I],Minimum,Allowed);
            ++Plans;Expanded+=R.Expanded;PeakExpanded=std::max(PeakExpanded,R.Expanded);Queries+=R.Queries;
            T.Path=R.Points;T.At=1;
            if(R.Result!=DetourRoutingStudy::Status::Found)
            {++PlannerFailures;T.FailedRevision=Revision;return false;}
        }
        // Bounded visible lookahead along at most99cm of the existing path.
        // Entire shortcut is checked, not just its next animation segment.
        int Best=-1;double Along=0;Vec2 Previous=Root,End{};
        for(size_t K=T.At;K<T.Path.size();++K)
        {
            Along+=Length(T.Path[K]-Previous);Previous=T.Path[K];if(Along>99)break;
            const double D=Length(T.Path[K]-Root);const int Parts=std::max(1,static_cast<int>(std::ceil(D/Step)));
            if(D/Parts<Minimum-1e-7||!Allowed(Root,T.Path[K]))continue;
            Best=static_cast<int>(K);End=Root+(T.Path[K]-Root)*(1.0/Parts);
        }
        if(Best<0){++Unplayable;T.FailedRevision=Revision;return false;}
        T.At=static_cast<size_t>(Best);T.Target=End;T.Latched=true;Target=End;return true;
    }
};
}
