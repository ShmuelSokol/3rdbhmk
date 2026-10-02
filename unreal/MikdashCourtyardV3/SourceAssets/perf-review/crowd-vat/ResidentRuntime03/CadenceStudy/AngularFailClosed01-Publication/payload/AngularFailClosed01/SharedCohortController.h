#include "CommitGates.h"
#include "BudgetedPlacement.h"
#include "CohortPlannerAdapter.h"
#pragma once
#include "TravellingCohortStudy.h"
#include "WaitTurnStudy.h"
namespace SharedCohortControllerReview {
template<class Port> void Visit(Port& Adapter) {
using namespace MikdashCrowd;using namespace MikdashCrowdGroups;using namespace CadenceRecoveryStudy;
    auto& Recovery=Adapter.r_Recovery;
    auto& Cause=Adapter.r_Cause;
    auto& Member=Adapter.r_Member;
    auto& Idle=Adapter.r_Idle;
    auto& DrainVisits=Adapter.r_DrainVisits;
    auto& Members=Adapter.r_Members;
    auto& People=Adapter.r_People;
    auto& Now=Adapter.r_Now;
    auto& Gate=Adapter.r_Gate;
    auto& Standing=Adapter.r_Standing;
    auto& Travel=Adapter.r_Travel;
    auto& Party=Adapter.r_Party;
    auto& Config=Adapter.r_Config;
    auto& Seed=Adapter.r_Seed;
    auto& Journey=Adapter.r_Journey;
    auto& Fault=Adapter.r_Fault;
    auto& Horizon=Adapter.r_Horizon;
    auto& PeerGoalWaitVisits=Adapter.r_PeerGoalWaitVisits;
    auto& WaitTurn=Adapter.r_WaitTurn;
    auto& Elapsed=Adapter.r_Elapsed;
    auto& FrameSeconds=Adapter.r_FrameSeconds;
    auto& A=Adapter.r_A;
    auto& MaxYaw=Adapter.r_MaxYaw;
    auto& WaitYawVisits=Adapter.r_WaitYawVisits;
    auto& TurnVisits=Adapter.r_TurnVisits;
    auto& From=Adapter.r_From;
    auto& Expect=Adapter.r_Expect;
    auto& Spacing=Adapter.r_Spacing;
    auto& Id=Adapter.r_Id;
    auto& Envelope=Adapter.r_Envelope;
    Adapter.r_FormationCache.ObserveGeometry(Adapter.r_Stamp.Geometry);

                    if(Recovery.State==Phase::Blocked){Cause[Member]=9;Idle();return;}
                    if(Recovery.State==Phase::Draining)
                    {
                        Cause[Member]=8;Idle();++DrainVisits;bool Drained=true;
                        for(int I=0;I<Members;++I)if(People[I].Walking||People[I].Angular.Held)Drained=false;
                        if(!Drained)return;
                        Recovery.State=Phase::Selecting;
                    }
                    bool AllReady=true;Vec2 Common[MaxMembers];
                    for(int I=0;I<Members;++I)
                    {
                        Common[I]=People[I].Motion.At(Now);
                        if(People[I].Walking||Length(Common[I]-Recovery.Goals[I])>=25)AllReady=false;
                    }
                    const auto FormationGate=[&](Vec2 A0,Vec2 B0)
                    {
                        if(!Gate(A0,B0))return false;
                        for(Vec2 S:Standing)if(ReservationDistance({A0,B0,0,1},{S,S,0,0},0)<80)return false;
                        return true;
                    };
                    if(AllReady&&!Travel.Active)
                    {
                        Expect(Steering(Party,0,Common,0,{1,0},Config,Seed).MaxLag<=Config.SlowLagCm,
                            "initial regroup barrier remains before travelling phase");
                        Travel.Begin(Members,Recovery.Goals);++Recovery.Completions;Journey.FormationHeading=0;
                    }
                    if(Travel.Active)
                    {
                        if(!PlacedActualHorizonStudy::Update(Travel,Common,Recovery.Goals,Config.SlowLagCm,Adapter.r_FormationCache,Adapter.r_PlanWork,FormationGate))
                        {
                            if(Adapter.r_FormationCache.Deferred){Cause[Member]=15;++Recovery.BudgetDeferrals;Idle();return;}
                            Cause[Member]=9;Recovery.State=Phase::Blocked;Idle();return;
                        }
                        Recovery.ForwardLegs=Travel.Legs-1;
                        Expect(Travel.Anchors.size()<=3,"travelling route cache bounded to two legs");
                    }
                    const auto FrozenGate=Adapter.r_MakeGate(Member);
                    const int BeforePlans=Recovery.Plans,BeforeUnplayable=Recovery.Unplayable;
                    const bool Prepared=Recovery.PrepareActual(Member,From,RuntimePortReview::ClipSteps(119.95,A.Scale,.45,1.55,90,Horizon),RuntimePortReview::GridFrame{},Adapter.r_PlanWork,Adapter.r_Stamp,Adapter.r_PlanQueue,Id,FrozenGate);
                    Expect(Recovery.Plans-BeforePlans<=1&&Recovery.PeakExpanded<=DetourRoutingStudy::Nodes,
                        "one bounded A-star search per scheduled visitor visit");
                    if(Recovery.Deferred){Cause[Member]=15;Idle();return;}
                    if(!Prepared)
                    {
                        Cause[Member]=Length(Recovery.Goals[Member]-From)<25?(Travel.Active?11:2):(Recovery.Unplayable>BeforeUnplayable?7:6);
                        if(Travel.Active&&Cause[Member]==6&&Adapter.r_PlanWork.Query()&&Gate(Recovery.Goals[Member],Recovery.Goals[Member]))
                        {
                            bool PeerHoldsGoal=false;
                            for(int I=0;I<Members;++I)if(I!=Member&&Length(Recovery.Goals[Member]-People[I].Motion.To)<80)PeerHoldsGoal=true;
                            if(PeerHoldsGoal)
                            {
                                ++PeerGoalWaitVisits;
                                const int S=Travel.Segment[Member];
                                const int AbsoluteLeg=static_cast<int>(Travel.Base/400)+S;
                                const double Desired=YawDegrees(Travel.Anchors[S+1]-Travel.Anchors[S]);
                                const double Intent=WaitTurn[Member].Intent.Target(Party.Identity,Recovery.Entries,AbsoluteLeg,Desired);
                                if(!Adapter.r_Align(Intent)){Cause[Member]=17;++WaitYawVisits;++TurnVisits;}
                                Expect(Length(A.Motion.At(Now)-From)<1e-8,"waiting orientation grants no displacement");
                            }
                        }
                        Idle();bool AllFailed=true;
                        for(int I=0;I<Members;++I)
                            if(Length(Recovery.Goals[I]-Common[I])>=25&&Recovery.Members[I].FailedRevision!=Recovery.Revision)AllFailed=false;
                        // Reached peers may hold; every unfinished peer must
                        // have failed against the same endpoint revision.
                        bool Unfinished=false;
                        for(int I=0;I<Members;++I)if(Length(Recovery.Goals[I]-Common[I])>=25)Unfinished=true;
                        if(Unfinished&&AllFailed&&Fault)Recovery.State=Phase::Blocked;
                        // A frozen-peer failure is cached, not permanent world unreachability.
                        // Relevant endpoint changes may retry in this same latched episode.
                        return;
                    }
                    auto& Track=Recovery.Members[Member];
                    const double Desired=YawDegrees(Track.Target-From);
                    if(!Adapter.r_Align(Desired)){Cause[Member]=17;++Recovery.YawOnly;++TurnVisits;return;}
                    if(!A.Walking&&Now-A.IdleSince<1){Cause[Member]=4;++Recovery.Dwell;return;}
                    if(!Adapter.r_Fresh(Track.Target))
                    {Cause[Member]=5;++Recovery.ReservationWaits;Idle();return;}
                    if(Travel.Active)
                    {
                        MotionReservation Prospective[MaxMembers];
                        for(int I=0;I<Members;++I)Prospective[I]=People[I].Motion;
                        Prospective[Member]={From,Track.Target,Now,Now+Horizon};
                        if(!Travel.Within(Prospective,Now,Config.WaitLagCm))
                        {Cause[Member]=10;++Travel.FormationRefusals;Idle();return;}
                    }
                    const double ActualSpeed=Length(Track.Target-From)/Horizon;
                    Expect(std::abs(VatPlayableSpeed(ActualSpeed,119.95,A.Scale,.45,1.55)-ActualSpeed)<1e-6,
                        "coalesced route uses unchanged clip range and full horizon");
                    if(!Adapter.r_PublishWalk(Track.Target,[&](){
                        Recovery.Reserved(Member);++Adapter.r_Stamp.RelevantEndpoints;
                    })){Cause[Member]=19;++Recovery.ReservationWaits;Idle();return;}
                    Cause[Member]=0;
                    return;
                
}
}
