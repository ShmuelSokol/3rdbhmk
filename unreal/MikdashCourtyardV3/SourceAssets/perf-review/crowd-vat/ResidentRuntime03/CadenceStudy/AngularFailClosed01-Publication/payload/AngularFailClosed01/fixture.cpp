#include "InjectedReservationIndex.h"
#include "SyntheticVatHistory.h"
#include "CommitGates.h"
#include "ScheduledAngular.h"
#include "BudgetedPlacement.h"
#include "AtomicCohortCommit.h"
#include "RotatingEnvelope.h"
#include <functional>
#include "SharedCohortController.h"
#include "WaitTurnStudy.h"
#include "TravellingCohortStudy.h"
#include "CrowdGroupMath.h"
#include "CrowdBoundaryCadenceStudy.h"
#include <iostream>
#include <limits>
#include <fstream>
#include <iomanip>
int main(int argc,char** argv)
{
    using namespace MikdashCrowd;
    using namespace MikdashCrowdGroups;
    const bool InjectRefusals=argc>2;
    int Checks=0,Failures=0;const int Seconds=argc>1?std::atoi(argv[1]):120;
    auto Expect=[&](bool Okay,const char* Label){++Checks;if(!Okay){++Failures;std::cerr<<Label<<"\n";}};
    const Vec2 Square[]={{-1000,-1000},{1000,-1000},{1000,1000},{-1000,1000}};
    Geometry World;World.Zone=Square;World.ZoneCount=4;World.EdgeMargin=100;
    auto Gate=[&](const Vec2& A,const Vec2& B){return SegmentAllowed(World,A,B);};
    auto Interior=FindBoundaryRoute({0,0},0,200,Gate);
    Expect(Interior.Clear&&Interior.Heading==0&&Interior.Probes==1,"interior preserves authored direction");
    auto Edge=FindBoundaryRoute({800,0},0,200,Gate);
    Expect(Edge.Clear&&Edge.Heading!=0,"turn guidance changes before committed step reaches east edge");
    int Calls=0;
    auto Bounded=FindBoundaryRoute({0,0},0,1e6,[&](const Vec2& A,const Vec2& B)
    {++Calls;Expect(Length(B-A)<=100,"guidance subsegments respect physical gate length");return true;});
    Expect(Bounded.Clear&&Calls==5,"guidance range capped400cm and five short segments");
    Calls=0;
    Expect(!FindBoundaryRoute({0,0},0,std::numeric_limits<double>::quiet_NaN(),
        [&](const Vec2&,const Vec2&){++Calls;return true;}).Clear&&Calls==0,"invalid lookahead refuses without world query");
    // Keep-out lies between endpoints; endpoint-only guidance would miss it.
    const Vec2 Hole[]={{-50,-100},{50,-100},{50,100},{-50,100}};
    const int Start[]={0},Count[]={4};World.Protected=Hole;World.Starts=Start;World.Counts=Count;World.ProtectedCount=1;World.ProtectedMargin=44;
    auto Around=FindBoundaryRoute({-200,0},0,400,Gate);
    Expect(Around.Clear&&Around.Heading!=0,"intermediate keep-out crossing changes guidance");
    World.ProtectedCount=0;
    // Constant eastward flow on a bounded floor: short-step validation alone
    // reaches the edge before turning. Guidance must sustain travel with normal
    // 90deg/s turns and unchanged geometric movement permission for two minutes.
    Vec2 P{700,0};double Heading=0,Travel=0;int Rejections=0;
    for(int Frame=0;Frame<3600;++Frame)
    {
        const auto Guide=FindBoundaryRoute(P,0,200,Gate);
        const double NextHeading=SteerHeading(Heading,Guide.Clear?Guide.Heading:0,1.0/30.0,90);
        Expect(std::abs(WrapDegrees(NextHeading-Heading))<=3.0000001,"anticipation respects turn cap");
        Heading=NextHeading;const Vec2 Next=P+FromDegrees(Heading)*4;
        if(Gate(P,Next)){P=Next;Travel+=4;}else ++Rejections;
        Expect(PointInPolygonWithMargin(Square,4,P,100),"walker remains within original inset");
    }
    Expect(Travel>10000&&Rejections<100,"boundary guidance sustains walking under constant outward flow");

    const double Dt=1.0/30.0,H=.12;
    Expect(std::abs(BoundaryReplanSeconds(H,Dt,1)-4*Dt)<1e-12,"0.12s at30Hz replans at fourth frame");
    Expect(std::abs(BoundaryReplanSeconds(H,1.0/60.0,1)-8.0/60.0)<1e-12,"fractional horizon rounds up at60Hz");
    Expect(std::abs(BoundaryReplanSeconds(.125,.03125,1)-.125)<1e-12,"exact frame-aligned horizon needs no extra frame");
    Expect(std::abs(BoundaryReplanSeconds(H,Dt,3)-6*Dt)<1e-12,"budgeted cadence allows post-expiry visit delay");
    // Unsaturated speed isolates the rate calculation: 3 degrees every4frames
    // gives22.5deg/s, not25deg/s from using the raw horizon as the interval.
    Expect(std::abs(BoundaryLookAhead(30,H,Dt,Dt,90,1)-30*(H+2/(22.5*Pi/180)))<1e-9,
        "guidance uses frame-quantized effective yaw rate");
    Expect(BoundaryLookAhead(120,H,Dt,Dt,90,1)==400,"cadence correction retains400cm ceiling");
    const auto Early=FindBoundaryRoute({600,0},0,BoundaryLookAhead(120,H,Dt,Dt,90,1),Gate);
    const auto Late=FindBoundaryRoute({600,0},0,120*(H+2/(90*Pi/180)),Gate);
    Expect(Early.Clear&&Early.Heading!=0&&Late.Clear&&Late.Heading==0,
        "cadence-aware guidance turns while nominal guidance still points outward");
    Expect(BoundaryLookAhead(1,H,Dt,Dt,90,1)==100,"guidance retains100cm floor");
    Expect(BoundaryLookAhead(120,H,Dt,0,90,1)==400,"zero yaw allowance stays finite and bounded");
    Expect(BoundaryLookAhead(120,H,Dt,Dt,0,1)==400,"zero turn rate stays finite and bounded");
    Expect(BoundaryLookAhead(30,.5,.5,.5,90,1)==BoundaryLookAhead(30,.5,.5,.25,90,1),
        "prediction honors SteerHeading internal time clamp");
    const double Bad[]={std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),-1};
    for(double Value:Bad)
    {
        Expect(BoundaryLookAhead(Value,H,Dt,Dt,90,1)==0,"invalid speed disables guidance");
        Expect(BoundaryLookAhead(120,Value,Dt,Dt,90,1)==0,"invalid horizon disables guidance");
        Expect(BoundaryLookAhead(120,H,Value,Dt,90,1)==0,"invalid frame disables guidance");
        Expect(BoundaryLookAhead(120,H,Dt,Value,90,1)==0,"invalid turn time disables guidance");
        Expect(BoundaryLookAhead(120,H,Dt,Dt,Value,1)==0,"invalid turn rate disables guidance");
    }
    Expect(BoundaryLookAhead(120,H,0,Dt,90,1)==0&&BoundaryLookAhead(120,H,Dt,Dt,90,0)==0,
        "zero frame or missing schedule disables guidance");

    // Independently execute the real round-robin window, including uneven
    // 48/17 visits. Check every agent/phase against the prediction, rather than
    // scheduling visits with the helper being tested.
    for(int Fps:{30,60}) for(int Budget:{48,17,8})
    {
        const double FrameSeconds=static_cast<float>(1.0/Fps);
        const int Sweeps=FramesPerSweep(48,Budget);
        const double Horizon=static_cast<float>(VatHorizonSeconds(Sweeps,FrameSeconds,.12,.7));
        double Last[48];for(double& T:Last) T=-1;
        int Cursor=0,Measured=0;
        for(int Frame=0;Frame<4*Fps;++Frame)
        {
            const double Now=Frame*FrameSeconds;
            const auto Window=NextUpdateWindow(Cursor,48,Budget);Cursor=Window.NextCursor;
            for(int Id=0;Id<48;++Id)
            {
                const bool Visited=(Id>=Window.FirstStart&&Id<Window.FirstStart+Window.FirstCount)
                    ||(Id>=Window.SecondStart&&Id<Window.SecondStart+Window.SecondCount);
                if(!Visited|| (Last[Id]>=0&&Now<Last[Id]+Horizon)) continue;
                if(Last[Id]>=0)
                {
                    Expect(Now-Last[Id]<=BoundaryReplanSeconds(Horizon,FrameSeconds,Sweeps)+1e-10,
                        "scheduled expiry fits cadence prediction");
                    ++Measured;
                }
                Last[Id]=Now;
            }
        }
        Expect(Measured>100,"cadence coverage includes repeated replans for every scheduler phase");
    }

    // Isolated leader with constant outward flow, an actual timed spacing index,
    // float horizon/frame inputs, endpoint-clamped rendering and the runtime's
    // one-second idle restart dwell. No formation, native ground or capsule
    // simulation: these comparisons establish scheduled guidance, not recovery.
    struct Result { double Travel=0;int Rejections=0,Replans=0,Deferred=0,Holds=0,LongestStop=0; };
    auto Scheduled=[&](int Fps,int Budget,bool Cadence)
    {
        Result Out;
        const double FrameSeconds=static_cast<float>(1.0/Fps);
        const int Sweeps=FramesPerSweep(48,Budget),Id=28;
        const double Horizon=static_cast<float>(VatHorizonSeconds(Sweeps,FrameSeconds,.12,.7));
        const double Speed=std::min(120.0,99.0/Horizon);
        Vec2 Anchor{300,0},Rendered=Anchor;
        double Yaw=0,AnchorTime=0,IdleSince=-1;
        MotionReservation Motion{Anchor,Anchor,0,0};
        bool Walking=false;int Cursor=0,Stopped=0;
        SpatialIndex Spacing;
        Expect(Spacing.Insert(Id,Anchor)&&Spacing.Insert(99,{-700,-700}),"fixture seeds separated people");
        for(int Frame=0;Frame<120*Fps;++Frame)
        {
            const double Now=Frame*FrameSeconds;
            const Vec2 Before=Rendered;
            Rendered=Motion.At(Now);
            const double Moved=Length(Rendered-Before);Out.Travel+=Moved;
            Expect(Moved<=Speed*FrameSeconds+1e-8,"rendered travel never jumps past frame displacement");
            Stopped=Moved<1e-8?Stopped+1:0;Out.LongestStop=std::max(Out.LongestStop,Stopped);
            Expect(PointInPolygonWithMargin(Square,4,Rendered,100),"scheduled rendered root stays inside inset");
            Expect(Length(Rendered-Vec2{-700,-700})>=80-1e-8,"scheduled rendered root preserves spacing");
            if(Walking&&Now>Motion.End) { ++Out.Holds;Expect(Length(Rendered-Motion.To)<1e-9,"expired shader segment holds endpoint"); }
            const auto Window=NextUpdateWindow(Cursor,48,Budget);Cursor=Window.NextCursor;
            const bool Visited=(Id>=Window.FirstStart&&Id<Window.FirstStart+Window.FirstCount)
                ||(Id>=Window.SecondStart&&Id<Window.SecondStart+Window.SecondCount);
            if(!Visited) continue;
            if(Walking&&Now<Motion.End)
            {
                ++Out.Deferred;
                Expect(!Spacing.CanReserve(Id,Anchor,Anchor,Now,Horizon),"live reserved segment cannot replan early");
                continue;
            }
            const double Elapsed=Clamp(Now-AnchorTime,0.0,Horizon);
            Anchor=Rendered;
            Expect(Spacing.Relocate(Id,Motion.From,Anchor,Now),"completed segment commits at rendered endpoint");
            AnchorTime=Now;++Out.Replans;
            const double Turn=Clamp(std::max(std::min(Elapsed,FrameSeconds),1.0/120.0),0.0,.5);
            const double Look=Cadence?BoundaryLookAhead(Speed,Horizon,FrameSeconds,Turn,90,Sweeps)
                :Clamp(Speed*(Horizon+2/(90*Pi/180)),100.0,400.0);
            const auto Guide=FindBoundaryRoute(Anchor,0,Look,Gate);
            const auto End=[&](double Angle){return Anchor+FromDegrees(Angle)*(Speed*Horizon);};
            const auto Safe=[&](double Angle){return Gate(Anchor,End(Angle))&&Spacing.CanReserve(Id,Anchor,End(Angle),Now,Horizon);};
            const auto Route=FindLocalRoute(Guide.Clear?Guide.Heading:0,Safe);
            const double NextYaw=SteerHeading(Yaw,Route.Clear?Route.Heading:(Guide.Clear?Guide.Heading:0),Turn,90);
            Expect(std::abs(WrapDegrees(NextYaw-Yaw))<=90*std::min(Turn,.25)+1e-8,"scheduled replan keeps single-frame yaw cap");
            Yaw=NextYaw;
            const bool Allowed=Safe(Yaw);
            if(!Allowed&&Walking) IdleSince=Now;
            Walking=Allowed&&(Walking||Now-IdleSince>=1.0);
            if(Walking)
            {
                Expect(Spacing.Reserve(Id,Anchor,End(Yaw),Now,Horizon),"actual limited-yaw segment receives reservation");
                Motion={Anchor,End(Yaw),Now,Now+Horizon};
            }
            else
            {
                if(!Allowed) ++Out.Rejections;
                Motion={Anchor,Anchor,Now,Now};
                Expect(!Allowed||Now-IdleSince<1.0,"restart holds for minimum idle dwell");
            }
        }
        Expect(Out.Deferred>0&&Out.Holds>0,"fixture exercises reserved waits and post-expiry endpoint holds");
        std::cout<<"scheduled fps="<<Fps<<" budget="<<Budget<<" cadence="<<Cadence
            <<" travel="<<Out.Travel<<" refusals="<<Out.Rejections<<" longestStopFrames="<<Out.LongestStop<<"\n";
        return Out;
    };
    for(int Fps:{30,60}) for(int Budget:{48,17,8})
    {
        const auto Nominal=Scheduled(Fps,Budget,false);
        const auto Cadence=Scheduled(Fps,Budget,true);
        Expect(Cadence.Travel>Nominal.Travel&&Cadence.Rejections<Nominal.Rejections,
            "cadence-aware scheduled guide improves travel and refusals over nominal-rate control");
        if(Fps==30&&Budget==48)
            Expect(Cadence.Travel>10000&&Cadence.Rejections<100&&Cadence.LongestStop<=Fps+1,
                "Runtime03 cadence sustains bounded-floor travel with at most idle-dwell stops");
    }
    std::ofstream Budgets("planner-budgets.csv");Budgets<<"population,fps,scale,members,budget,fault,scenario,recovery,enabled,sharedHold,frames,totalCalls,totalNodes,totalQueries,placementCredit,angularStarts,angularCommits\n";
    std::ofstream Metrics("group-metrics.csv"), MemberMetrics("member-metrics.csv"), Roots("late-roots.csv");
    Metrics<<std::setprecision(17);MemberMetrics<<std::setprecision(17);Roots<<std::setprecision(17);
    Metrics<<"population,fps,scale,members,budget,enabled,sharedHold,recovery,fault,terminal,leaderTravel,lateLeaderTravel,allTravel,lateAllTravel,refusals,waits,minSpacing,maxLag,maxFormation,finalLag,finalFormation,clipHoldVisits,safetyFailures,peakNodes,peakQueries,peakCalls,externalMoves,envelopeRefusals,budgetDeferrals,searchInvalidations,endpointChangesDuringSearch,completedAfterEndpointChange\n";
    MemberMetrics<<"population,fps,scale,members,budget,enabled,sharedHold,recovery,fault,terminal,member,id,totalTravel,late0,late1,late2,longestLateStopFrames,lateZeroSpeedVisits,lateBlockedVisits,lateDwellVisits,clipHoldVisits\n";
    Roots<<"members,budget,enabled,sharedHold,recovery,fault,terminal,frame,member,x,y,yaw,mode,formationYaw,walking,distance\n";
    std::ofstream Motion("motion.csv");Motion<<std::setprecision(17);
    Motion<<"members,budget,terminal,fault,frame,member,distance,cause,x,y,yaw,goalDistance,travelling\n";
    std::ofstream EpisodeTrace("episodes.csv"),RecoveryMetrics("recovery.csv");
    EpisodeTrace<<std::setprecision(17);RecoveryMetrics<<std::setprecision(17);
    EpisodeTrace<<"members,budget,fault,terminal,frame,phase,owner,entries,completions,steps,targetX,targetY\n";
    RecoveryMetrics<<"population,fps,scale,members,budget,fault,terminal,phase,entries,completions,steps,turnVisits,drainVisits,maxYaw,invalid,unfinishedSeconds,steps0,steps1,steps2,steps3,steps4,steps5,plans,expanded,peakExpanded,queries,replans,unplayable,forwardLegs,plannerFailures,reservationWaits,yawOnly,dwell,formationRefusals,maxTravellingFormation,maxTravellingLag,goalUpdates,peerGoalWaitVisits,waitYawVisits\n";
    // Group fixture: common-time follower targets, physical-spread cohesion,
    // real timed reservations and round-robin visits split across cohort members.
    // Two standing neighbours keep their reservations/positions throughout.
    // Native ground/sweeps and authored flow variation are intentionally absent.
    auto ScheduledGroup=[&](int Members,int Budget,bool Enabled,bool SharedHold,bool RecoveryEnabled=false,int Fault=0,int TerminalStart=0,int Population=48,int Fps=30,double Scale=1)
    {
        const int FailuresBefore=Failures;
        constexpr int First=15;const int Frames=Seconds*Fps;const int TerminalBudget=Population==48?Budget:(Budget==500?48:17);
        constexpr uint32_t Seed=13;
        const double FrameSeconds=static_cast<float>(1.0/Fps);
        const int Sweeps=FramesPerSweep(Population,Budget);
        const double Horizon=static_cast<float>(VatHorizonSeconds(Sweeps,FrameSeconds,.12,.7));
        const Vec2 SeedAnchor{400,-100};
        Cohort Party;Party.Count=Members;Party.Identity=47;Party.Speed=90;
        Settings Config;MikdashCrowdGroups::Travel Journey;
        struct Walker
        {
            Vec2 Anchor{},LastRoot{};MotionReservation Motion{};
            double AnchorTime=0,Yaw=0,IdleSince=-1,Distance=0;
            AngularWalkingStudy::ScheduledTurn Angular;SyntheticVatStudy::History Vat;Vec2 LastPosed[4]{};bool HavePose=false;
            bool Walking=false;double Scale=1;RotatingEnvelopeStudy::Body Body;
        };
        Walker People[MaxMembers];CommitGatesStudy::ReservationIndex Spacing;
        bool InjectedRelocate[MaxMembers]{},InjectedReserve[MaxMembers]{};
        CohortPlannerStudy::Episode Recovery;RuntimePortReview::Revisions Stamp;RuntimePortReview::FairPlanningQueue PlanQueue;
        int PeakNodes=0,PeakQueries=0,PeakCalls=0,ExternalMoves=0,EnvelopeRefusals=0;long long TotalCalls=0,TotalNodes=0,TotalQueries=0;
        TravellingCohortStudy::Travel Travel;
        PlacedActualHorizonStudy::FormationCache FormationCache;
        ActualHorizonReview::Budget PlacementWork;
        using Phase=CadenceRecoveryStudy::Phase;
        Vec2 RecoveryGoals[MaxMembers];
        for(int I=0;I<Members;++I) RecoveryGoals[I]=SeedAnchor+Offset(I,Seed,Party.Identity,Config.SpacingCm);
        if(Fault==2) RecoveryGoals[0].X=std::numeric_limits<double>::quiet_NaN();
        if(Fault==3) RecoveryGoals[0]={2000,2000};
        // One fixed90deg/s maximum180-degree angular segment plus one scheduled revisit, a
        // completed horizon and unchanged idle dwell. No parameter search.
        const double Watchdog=2.0+(Sweeps*FrameSeconds)+Horizon+1;
        int TurnVisits=0,DrainVisits=0;double MaxYaw=0;
        CohortPlannerStudy::WaitLatch WaitTurn[MaxMembers];int WaitYawVisits=0,PeerGoalWaitVisits=0;
        int Cause[MaxMembers]{};int Visits[MaxMembers]{},LastVisit[MaxMembers]{},MaximumVisitGap=0;
        double Late[MaxMembers][3]{};
        int Stop[MaxMembers]{},LongestStop[MaxMembers]{},Zero[MaxMembers]{},Blocked[MaxMembers]{},Dwell[MaxMembers]{},ClipHolds[MaxMembers]{};
        for(int I=0;I<Members;++I)
        {
            Party.Members[I]=First+I;
            People[I].Scale=Scale>0?Scale:(I%2?.92:1.08);
            // Synthetic posed-body bounds only; NOT measured resident meshes.
            const Vec2 BodyPoints[]={{50,0},{-50,0},{0,45},{0,-45}};
            People[I].Body=RotatingEnvelopeStudy::FromPosedBounds(BodyPoints,4,0,190,People[I].Scale);
            People[I].Anchor=SeedAnchor+Offset(I,Seed,Party.Identity,Config.SpacingCm);
            if(TerminalStart==1&&Members==2&&TerminalBudget==48&&I==0) {People[I].Anchor={864.46278065540162,452.59594546197394};People[I].Yaw=-84.44125391380669;}
            if(TerminalStart==1&&Members==2&&TerminalBudget==48&&I==1) {People[I].Anchor={878.46298790686126,540.63783535343327};People[I].Yaw=-88.213687213697455;}
            if(TerminalStart==1&&Members==2&&TerminalBudget==17&&I==0) {People[I].Anchor={854.2521943754665,460.67915373000648};People[I].Yaw=-93.000000156462193;}
            if(TerminalStart==1&&Members==2&&TerminalBudget==17&&I==1) {People[I].Anchor={878.87948909459544,543.18002935040249};People[I].Yaw=-179.4682838978288;}
            if(TerminalStart==1&&Members==3&&TerminalBudget==48&&I==0) {People[I].Anchor={866.0184030482659,450.9520904432847};People[I].Yaw=-84.619574652272718;}
            if(TerminalStart==1&&Members==3&&TerminalBudget==48&&I==1) {People[I].Anchor={391.46070914735481,38.111174326725425};People[I].Yaw=-122.68224992078925;}
            if(TerminalStart==1&&Members==3&&TerminalBudget==48&&I==2) {People[I].Anchor={287.88643097387887,-136.49594744523159};People[I].Yaw=-108.64046542041913;}
            if(TerminalStart==1&&Members==3&&TerminalBudget==17&&I==0) {People[I].Anchor={410.78599086880047,-89.821773758782157};People[I].Yaw=-136.66057226527838;}
            if(TerminalStart==1&&Members==3&&TerminalBudget==17&&I==1) {People[I].Anchor={392.96814122439241,36.560109189424232};People[I].Yaw=-129.7333573631158;}
            if(TerminalStart==1&&Members==3&&TerminalBudget==17&&I==2) {People[I].Anchor={862.3038293471825,456.31036344761327};People[I].Yaw=-133.38065078346676;}
            if(TerminalStart==1&&Members==6&&TerminalBudget==48&&I==0) {People[I].Anchor={843.31135972634581,591.87732659553308};People[I].Yaw=-122.64918724785468;}
            if(TerminalStart==1&&Members==6&&TerminalBudget==48&&I==1) {People[I].Anchor={392.83387519558954,40.331771454327303};People[I].Yaw=-122.55897400548338;}
            if(TerminalStart==1&&Members==6&&TerminalBudget==48&&I==2) {People[I].Anchor={290.44587453279172,-145.44045805809222};People[I].Yaw=-125.89151241292066;}
            if(TerminalStart==1&&Members==6&&TerminalBudget==48&&I==3) {People[I].Anchor={270.25302985344956,-17.752390168353593};People[I].Yaw=-125.37153220655807;}
            if(TerminalStart==1&&Members==6&&TerminalBudget==48&&I==4) {People[I].Anchor={177.57377272962091,-157.87240248812279};People[I].Yaw=-141.11035263713316;}
            if(TerminalStart==1&&Members==6&&TerminalBudget==48&&I==5) {People[I].Anchor={151.22620051051547,3.9567110798885814};People[I].Yaw=-123.98595885946403;}
            if(TerminalStart==1&&Members==6&&TerminalBudget==17&&I==0) {People[I].Anchor={865.12068416853776,454.17640070795989};People[I].Yaw=-130.00676239224597;}
            if(TerminalStart==1&&Members==6&&TerminalBudget==17&&I==1) {People[I].Anchor={864.9346925101288,574.36201157432095};People[I].Yaw=-85.487194358473488;}
            if(TerminalStart==1&&Members==6&&TerminalBudget==17&&I==2) {People[I].Anchor={288.93691664069689,-144.64280441121045};People[I].Yaw=-120.40006710761938;}
            if(TerminalStart==1&&Members==6&&TerminalBudget==17&&I==3) {People[I].Anchor={270.75922470439531,-17.701067807939324};People[I].Yaw=-126.87525400367628;}
            if(TerminalStart==1&&Members==6&&TerminalBudget==17&&I==4) {People[I].Anchor={167.45049700860847,-151.85415147993365};People[I].Yaw=-110.25202686125922;}
            if(TerminalStart==1&&Members==6&&TerminalBudget==17&&I==5) {People[I].Anchor={153.53989574997991,7.4521687420803477};People[I].Yaw=-123.88777261618941;}
            People[I].LastRoot=People[I].Anchor;
            People[I].Motion={People[I].Anchor,People[I].Anchor,0,0};

        }

        if(RecoveryEnabled&&TerminalStart!=1)
        {
            struct SpawnPort {
                SpatialIndex& Index;decltype(Gate)& Allowed;Vec2 Anchor;int First;
                bool Sample(int,Vec2& P,double& H){P=Anchor;H=0;return true;}
                bool Ground(int,Vec2,double& Z){Z=0;return true;} // synthetic flat floor only
                bool RootAndLink(Vec2 A,Vec2 B){
                    const int Parts=std::max(1,static_cast<int>(std::ceil(Length(B-A)/80.)));
                    for(int I=0;I<Parts;++I)if(!Allowed(A+(B-A)*(double(I)/Parts),A+(B-A)*(double(I+1)/Parts)))return false;
                    return true;
                }
                bool HeldCapsuleSweep(Vec2 A,double,Vec2 B,double,RotatingEnvelopeStudy::Body Body){
                    // Synthetic square margin only, NOT a native geometry adapter.
                    return Body.Known&&Body.Radius<=100&&Body.MinZ>=0&&Body.MaxZ<=210&&RootAndLink(A,B);
                }
                bool CommittedPeers(Vec2 P,double,RotatingEnvelopeStudy::Body Body){
                    for(Vec2 Q:{Vec2{800,400},Vec2{800,520}})
                        if(!RotatingEnvelopeStudy::Pair({P,P,0,0},Body,{Q,Q,0,0},{50,0,190,true},0))return false;
                    return true;
                }
                bool CommitBatch(const Vec2* P,const double*,const RotatingEnvelopeStudy::Body*,int N){
                    return PlacedActualHorizonStudy::CommitCohort(Index,First,P,N,[](int){return true;});
                }
            } Port{Spacing,Gate,SeedAnchor,First};
            RotatingEnvelopeStudy::Body Bodies[MaxMembers];Vec2 Placed[MaxMembers];
            for(int I=0;I<Members;++I)Bodies[I]=People[I].Body;
            BodyAwarePlacementStudy::Formation Layout;
            const auto Placement=PlacedActualHorizonStudy::Place(Members,Bodies,Seed,Party.Identity,Config.SpacingCm,Port,Placed,Layout,PlacementWork);
            Expect(Placement==PlacedActualHorizonStudy::PlacementStatus::Placed,"whole body-aware cohort admitted before runtime motion");
            if(Placement!=PlacedActualHorizonStudy::PlacementStatus::Placed)return;
            Config.SpacingCm=Layout.Spacing;
            for(int I=0;I<Members;++I){
                Expect(Length(Placed[I]-People[I].Anchor)<1e-8,"already valid baseline spawn preserved");
                People[I].Anchor=People[I].LastRoot=Placed[I];People[I].Motion={Placed[I],Placed[I],0,0};
                if(!Fault)RecoveryGoals[I]=Placed[I];
            }
        }
        else for(int I=0;I<Members;++I)
            Expect(Spacing.Insert(First+I,People[I].Anchor),"preserved control or invalid terminal snapshot");

        for(int I=0;I<Members;++I){auto& T=People[I].Angular;
            T.Core.Current.Yaw=People[I].Yaw;T.Core.Current.Root=People[I].Anchor;T.Core.Current.Envelope=People[I].Body;
            T.Core.Previous=T.Core.Current;T.LastVisible=People[I].Yaw;
        }
        Vec2 Standing[]={{800,400},{800,520}};
        MotionReservation Foreign[2]={{Standing[0],Standing[0],0,0},{Standing[1],Standing[1],0,0}};
        const RotatingEnvelopeStudy::Body ForeignBody{50,0,190,true};
        const auto Envelope=[&](int Member,Vec2 From,Vec2 To,double Now,double H)
        {
            const auto B=People[Member].Body;
            bool Clear=RotatingEnvelopeStudy::World(From,To,B,[&](Vec2 P,Vec2 Q,double Radius,double Z0,double Z1)
            {return Gate(P,Q)&&Radius<=100&&Z0>=0&&Z1<=210;});
            const MotionReservation Proposed{From,To,Now,Now+H};
            for(int I=0;I<Members;++I)if(I!=Member)Clear=Clear&&RotatingEnvelopeStudy::Pair(Proposed,B,People[I].Motion,People[I].Body,Now);
            for(int I=0;I<2;++I)Clear=Clear&&RotatingEnvelopeStudy::Pair(Proposed,B,Foreign[I],ForeignBody,Now);
            if(!Clear)++EnvelopeRefusals;return Clear;
        };
        const auto MakeGate=[&](int Member)->std::function<bool(Vec2,Vec2)>
        {
            std::vector<std::pair<Vec2,RotatingEnvelopeStudy::Body>> Peers;
            for(int I=0;I<Members;++I)if(I!=Member)Peers.push_back({People[I].Motion.To,People[I].Body});
            for(int I=0;I<2;++I)Peers.push_back({Foreign[I].To,ForeignBody});
            const auto Own=People[Member].Body;
            return [&,Peers,Own,Fault](Vec2 P,Vec2 Q)
            {
                if(Fault==1||!Gate(P,Q)||!Own.Known)return false;
                const MotionReservation M{P,Q,0,1};
                for(const auto& Peer:Peers)if(!RotatingEnvelopeStudy::Pair(M,Own,{Peer.first,Peer.first,0,0},Peer.second,0))return false;
                return true;
            };
        };
        for(int I=0;I<2;++I) Expect(Spacing.Insert(40+I,Standing[I]),"standing neighbours seed separately");
        int Cursor=0,LeaderGuides=0,GuidedTurns=0,FollowerPlans=0,Rejected=0,Waits=0,Deferred=0;
        double PausedSince=-1,Minimum=1e9,MaxLag=0,MaxFormation=0,LateLeaderTravel=0;
        if(TerminalStart==1) Recovery.Enter(Members,RecoveryGoals,Journey.Mode,0,
            [&](Vec2 P){return PointInPolygonWithMargin(Square,4,P,100);});
        for(int Frame=0;Frame<Frames;++Frame)
        {
            const double Now=Frame*FrameSeconds;
            ActualHorizonReview::Budget PlanWork=Frame==0?PlacementWork:ActualHorizonReview::Budget{};
            // A foreign endpoint changes during deferred search. Its movement
            // also respects live intervals and every cohort body's envelope.
            if(RecoveryEnabled&&Fault==0&&Population>48&&Now>=Foreign[0].End)
            {
                const Vec2 Old=Standing[0];Standing[0]=Foreign[0].To;
                Expect(Spacing.Relocate(40,Old,Standing[0],Now),"foreign endpoint commits before replacement");
                const Vec2 Goal{760+40*std::cos(Now),400};
                MotionReservation Proposal{Standing[0],Goal,Now,Now+.2};bool Safe=Gate(Standing[0],Goal);
                for(int I=0;I<Members;++I)Safe=Safe&&RotatingEnvelopeStudy::Pair(Proposal,ForeignBody,People[I].Motion,People[I].Body,Now);
                Safe=Safe&&RotatingEnvelopeStudy::Pair(Proposal,ForeignBody,Foreign[1],ForeignBody,Now);
                if(Safe&&Spacing.Reserve(40,Standing[0],Goal,Now,.2))
                {Foreign[0]=Proposal;++Stamp.RelevantEndpoints;++ExternalMoves;}
                else Foreign[0]={Standing[0],Standing[0],Now,Now};
            }
            if(Travel.Active)
            {
                MotionReservation Current[MaxMembers];
                for(int I=0;I<Members;++I)Current[I]=People[I].Motion;
                Expect(Travel.Within(Current,Now,Config.WaitLagCm),"continuous travelling formation bound and endpoint holds");
                const Vec2 Leader=People[0].Motion.At(Now);
                for(int I=1;I<Members;++I)
                {
                    const Vec2 Relative=People[I].Motion.At(Now)-Leader;
                    Travel.MaximumFormationError=std::max(Travel.MaximumFormationError,Length(Relative-Travel.Offset[I]));
                    Travel.MaximumPhysicalLag=std::max(Travel.MaximumPhysicalLag,Length(Relative)-Length(Travel.Offset[I]));
                }
            }
            Expect(Party.Count==Members&&Party.Identity==47,"cohort identity and member count remain unchanged");
            for(int I=0;I<Members;++I) Expect(Party.Members[I]==First+I,"cohort membership remains unchanged");
            // Sample within each frame independently of the continuous-distance
            // reservation implementation, before any current-frame replacement.
            for(int Sub=0;Sub<=4;++Sub)
            {
                const double Time=std::max(0.0,Now-FrameSeconds+FrameSeconds*Sub/4);
                for(int I=0;I<Members;++I)
                {
                    const Vec2 P=People[I].Motion.At(Time);
                    Expect(PointInPolygonWithMargin(Square,4,P,100),"group subframe root stays inside original inset");
                    for(int J=I+1;J<Members+2;++J)
                    {
                        const Vec2 Q=J<Members?People[J].Motion.At(Time):Foreign[J-Members].At(Time);
                        const double Distance=Length(P-Q);Minimum=std::min(Minimum,Distance);
                        Expect(Distance>=80-1e-7,"group subframe spacing including standing neighbours stays80cm");
                    }
                }
            }
            for(int I=0;I<Members;++I)
            {
                auto& A=People[I];const Vec2 Root=A.Motion.At(Now);

                const double Distance=Length(Root-A.LastRoot);A.Distance+=Distance;
                if(I==0&&Frame>=Frames-30*Fps) LateLeaderTravel+=Distance;
                Expect(Distance<=std::min(90*1.15,99.0/Horizon)*FrameSeconds+1e-7,
                    "group rendered root has no unreserved jump");
                if(Frame>=Frames-30*Fps)
                {
                    Late[I][(Frame-(Frames-30*Fps))/(10*Fps)]+=Distance;
                    Stop[I]=Distance<1e-8?Stop[I]+1:0;LongestStop[I]=std::max(LongestStop[I],Stop[I]);
                    if(Population==48) Roots<<Members<<','<<Budget<<','<<Enabled<<','<<SharedHold<<','<<RecoveryEnabled<<','<<Fault<<','<<TerminalStart<<','<<Frame<<','<<I<<','
                        <<Root.X<<','<<Root.Y<<','<<A.Yaw<<','<<static_cast<int>(Journey.Mode)<<','
                        <<Journey.FormationHeading<<','<<A.Walking<<','<<A.Distance<<"\n";
                }
                if(RecoveryEnabled&&Population==48)
                {
                    const int Why=Distance>1e-8?0:(A.Walking&&Now>=A.Motion.End?1:Cause[I]);
                    Motion<<Members<<','<<Budget<<','<<TerminalStart<<','<<Fault<<','<<Frame<<','<<I<<','<<Distance<<','<<Why<<','
                        <<Root.X<<','<<Root.Y<<','<<A.Yaw<<','<<Length(Recovery.Goals[I]-Root)<<','<<(Recovery.Completions>0)<<'\n';
                }
                Recovery.Observe(I,Distance,Now);
                A.LastRoot=Root;
            }
            if(RecoveryEnabled&&Recovery.State==Phase::Normal&&((Fault&&Now>=2)||Recovery.Stalled(Members,Now,Watchdog)))
                Recovery.Enter(Members,RecoveryGoals,Journey.Mode,Now,
                    [&](Vec2 P){return PointInPolygonWithMargin(Square,4,P,100);});
            if(RecoveryEnabled&&Population==48)
                EpisodeTrace<<Members<<','<<Budget<<','<<Fault<<','<<TerminalStart<<','<<Frame<<','<<static_cast<int>(Recovery.State)<<','
                    <<Recovery.Owner<<','<<Recovery.Entries<<','<<Recovery.Completions<<','<<Recovery.Steps<<','
                    <<Recovery.Target.X<<','<<Recovery.Target.Y<<'\n';
            const auto Window=NextUpdateWindow(Cursor,Population,Budget);Cursor=Window.NextCursor;
            const int Starts[]={Window.FirstStart,Window.SecondStart};
            const int Counts[]={Window.FirstCount,Window.SecondCount};
            for(int Slice=0;Slice<2;++Slice) for(int Id=Starts[Slice];Id<Starts[Slice]+Counts[Slice];++Id)
            {
                if(Id<First||Id>=First+Members) continue;
                const int Member=Id-First;auto& A=People[Member];
                if(Visits[Member])MaximumVisitGap=std::max(MaximumVisitGap,Frame-LastVisit[Member]);
                LastVisit[Member]=Frame;++Visits[Member];
                if(A.Walking&&Now<A.Motion.End)Expect(!Spacing.CanReserve(Id,A.Anchor,A.Anchor,Now,Horizon),"group cannot replace live reserved movement");
                if(InjectRefusals&&RecoveryEnabled){
                    if(!InjectedRelocate[Member]&&((A.Walking&&Now>=A.Motion.End)||(A.Angular.Held&&A.Angular.CanCommit(Now,A.Motion)))){
                        Spacing.RefuseRelocation=true;InjectedRelocate[Member]=true;
                    }
                    Spacing.RefuseWalkingReservation=!InjectedReserve[Member];
                    Spacing.WalkingRefusalId=Id;
                }
                const auto BeforeArrival=A;const int BeforeSteps=Recovery.Steps,BeforeRevision=Recovery.Revision;
                const double Elapsed=Clamp(Now-A.AnchorTime,0.0,Horizon);
                const auto Arrival=CommitGatesStudy::CommitArrival(A,Recovery,Spacing,Id,Member,Members,Now,RecoveryEnabled);
                if(Arrival!=CommitGatesStudy::Arrival::Committed){
                    if(Arrival==CommitGatesStudy::Arrival::Deferred)++Deferred;
                    Cause[Member]=Arrival==CommitGatesStudy::Arrival::Deferred?17:18;
                    Expect(Arrival!=CommitGatesStudy::Arrival::Invalid,"arrival state matches retained completed segment");
                    Expect(Arrival!=CommitGatesStudy::Arrival::Refused||InjectRefusals,"unexpected relocation refusal remains explicit without actor publication");
                    if(Arrival==CommitGatesStudy::Arrival::Refused){
                        Expect(A.Anchor.X==BeforeArrival.Anchor.X&&A.Anchor.Y==BeforeArrival.Anchor.Y&&A.AnchorTime==BeforeArrival.AnchorTime&&A.Yaw==BeforeArrival.Yaw&&A.Motion.End==BeforeArrival.Motion.End&&A.Motion.To.X==BeforeArrival.Motion.To.X&&A.Motion.To.Y==BeforeArrival.Motion.To.Y&&A.Walking==BeforeArrival.Walking,
                            "actual scheduled relocation refusal preserves actor and motion");
                        Expect(A.Angular.Held==BeforeArrival.Angular.Held&&A.Angular.Commits==BeforeArrival.Angular.Commits&&Recovery.Steps==BeforeSteps&&Recovery.Revision==BeforeRevision,
                            "actual scheduled relocation refusal publishes neither turn nor recovery completion");
                    }
                    continue;
                }
                const Vec2 From=A.Anchor;
                const auto Idle=[&]() { if(A.Walking) A.IdleSince=Now;A.Walking=false; };
                const auto Align=[&](double Desired){
                    if(!RecoveryEnabled)return true;
                    A.Angular.Core.Current.Root=From;A.Angular.Core.Current.Envelope=A.Body;
                    const bool Ready=A.Angular.Align(Desired,Now,A.Motion,[&](Vec2 Root,RotatingEnvelopeStudy::Body){
                        const float Delta=static_cast<float>(WrapDegrees(Desired-A.Yaw));
                        AngularControllerStudy::State Proposed=A.Angular.Core.Current;
                        Proposed.TurnStartGameTime=static_cast<float>(Now);Proposed.TurnDeltaDegrees=Delta;
                        AngularWalkingStudy::ScheduledTurn Temp;Temp.Core.Current=Proposed;
                        const double Duration=std::max(1e-6,Temp.End(Now)-Now);
                        if(!Envelope(Member,Root,Root,Now,Duration)||!Spacing.CanReserve(Id,Root,Root,Now,Duration))return false;
                        if(!Spacing.Reserve(Id,Root,Root,Now,Duration))return false;
                        A.Motion={Root,Root,Now,Now+Duration};return true;
                    });
                    if(!Ready){Cause[Member]=17;Idle();}
                    return Ready;
                };
                const auto Fresh=[&](Vec2 Target){return A.Angular.Core.Translation(Now,A.Motion,
                    [&](){return A.Body.MinZ>=0&&A.Body.MaxZ<=210;},
                    [&](){return Gate(From,Target)&&Envelope(Member,From,Target,Now,Horizon);},
                    [&](){return Spacing.CanReserve(Id,From,Target,Now,Horizon);});};
                const auto PublishWalk=[&](Vec2 Target,auto&& OnSuccess){
                    const auto BeforeMotion=A.Motion;const bool BeforeWalking=A.Walking;
                    const auto Revision=Stamp.RelevantEndpoints;const bool Moving=Recovery.WasMoving(Member);
                    const int Refusals=Spacing.ReservationRefusals;
                    const bool Reserved=CommitGatesStudy::ReserveWalk(A,Spacing,Id,From,Target,Now,Horizon,OnSuccess);
                    if(Spacing.ReservationRefusals!=Refusals){
                        InjectedReserve[Member]=true;
                        Expect(!Reserved&&A.Walking==BeforeWalking&&A.Motion.To.X==BeforeMotion.To.X&&A.Motion.To.Y==BeforeMotion.To.Y&&A.Motion.End==BeforeMotion.End&&Stamp.RelevantEndpoints==Revision&&Recovery.WasMoving(Member)==Moving,
                            "actual scheduled Reserve refusal preserves motion and episode publication");
                        Expect(Spacing.CanReserve(Id,From,Target,Now,Horizon),"refused Reserve leaves index unreserved despite prior CanReserve success");
                    }
                    return Reserved;
                };
                if(TerminalStart==2&&Recovery.State==Phase::Normal){Cause[Member]=16;Idle();continue;}
                if(RecoveryEnabled&&Recovery.State!=Phase::Normal)
                {
                struct Port {
                    decltype(Recovery)& r_Recovery;
                    decltype(Cause)& r_Cause;
                    decltype(Member)& r_Member;
                    decltype(Idle)& r_Idle;
                    decltype(DrainVisits)& r_DrainVisits;
                    decltype(Members)& r_Members;
                    decltype(People)& r_People;
                    decltype(Now)& r_Now;
                    decltype(Gate)& r_Gate;
                    decltype(Standing)& r_Standing;
                    decltype(Travel)& r_Travel;
                    decltype(Party)& r_Party;
                    decltype(Config)& r_Config;
                    decltype(Seed)& r_Seed;
                    decltype(Journey)& r_Journey;
                    decltype(Fault)& r_Fault;
                    decltype(Horizon)& r_Horizon;
                    decltype(PeerGoalWaitVisits)& r_PeerGoalWaitVisits;
                    decltype(WaitTurn)& r_WaitTurn;
                    decltype(Elapsed)& r_Elapsed;
                    decltype(FrameSeconds)& r_FrameSeconds;
                    decltype(A)& r_A;
                    decltype(MaxYaw)& r_MaxYaw;
                    decltype(WaitYawVisits)& r_WaitYawVisits;
                    decltype(TurnVisits)& r_TurnVisits;
                    decltype(From)& r_From;
                    decltype(Expect)& r_Expect;
                    decltype(Spacing)& r_Spacing;
                    decltype(Id)& r_Id;
                    decltype(Envelope)& r_Envelope;
                    decltype(MakeGate)& r_MakeGate;
                    decltype(FormationCache)& r_FormationCache;
                    decltype(PlanWork)& r_PlanWork;
                    decltype(Stamp)& r_Stamp;
                    decltype(PlanQueue)& r_PlanQueue;
                    decltype(Align)& r_Align;
                    decltype(Fresh)& r_Fresh;
                    decltype(PublishWalk)& r_PublishWalk;
                } Adapter{Recovery,Cause,Member,Idle,DrainVisits,Members,People,Now,Gate,Standing,Travel,Party,Config,Seed,Journey,Fault,Horizon,PeerGoalWaitVisits,WaitTurn,Elapsed,FrameSeconds,A,MaxYaw,WaitYawVisits,TurnVisits,From,Expect,Spacing,Id,Envelope,MakeGate,FormationCache,PlanWork,Stamp,PlanQueue,Align,Fresh,PublishWalk};
                SharedCohortControllerReview::Visit(Adapter);continue;
                }
                Cause[Member]=12;
                if(Member==0&&Journey.Mode==TravelMode::Paused)
                {
                    if(PausedSince<0) PausedSince=Now;
                    else if(Now-PausedSince>=12*(.75+.5*HashUnit(Seed,Party.Identity,83u)))
                    { Journey.Mode=TravelMode::Returning;PausedSince=-1; }
                }
                Vec2 Positions[MaxMembers];
                for(int I=0;I<Members;++I) Positions[I]=People[I].Motion.At(Now);
                const Vec2 Flow=Journey.Mode==TravelMode::Returning?Normalized(SeedAnchor-Positions[0]):Vec2{1,0};
                // Single mechanism: derive the same actionable leader pace for
                // every member from common-time roots. A zero playable leader
                // uses the existing Pace==0 regroup branch; no Journey mutation,
                // clip threshold change, or early reservation replacement.
                const auto LeaderCmd=Steering(Party,0,Positions,Journey.FormationHeading,Flow,Config,Seed,
                    Journey.Mode==TravelMode::Paused);
                const double LeaderPlayable=VatPlayableSpeed(LeaderCmd.Speed,119.95,People[0].Scale,.45,1.55);
                const bool CohesionHold=SharedHold&&LeaderCmd.Valid&&LeaderPlayable<=0;
                if(CohesionHold&&LeaderCmd.Speed>0) ++ClipHolds[Member];
                const auto Cmd=Steering(Party,Member,Positions,Journey.FormationHeading,Flow,Config,Seed,
                    Journey.Mode==TravelMode::Paused||CohesionHold);
                if(CohesionHold) Expect(Cmd.Waiting&&(Member!=0||Cmd.Speed==0),
                    "zero-playable leader gives all members shared regroup semantics");
                Expect(Cmd.Valid,"scheduled cohort steering stays valid");
                MaxLag=std::max(MaxLag,Cmd.MaxLag);MaxFormation=std::max(MaxFormation,Cmd.MaxFormationError);
                if(Cmd.Waiting) ++Waits;
                const double Speed=std::min(VatPlayableSpeed(Cmd.Speed,119.95,A.Scale,.45,1.55),99.0/Horizon);
                if(Speed<=0) { Idle();if(Frame>=Frames-30*Fps) ++Zero[Member];continue; }
                const double Turn=Clamp(std::max(std::min(Elapsed,FrameSeconds),1.0/120.0),0.0,.5);
                const double FormationGoal=YawDegrees(Cmd.Direction);
                double Desired=FormationGoal;
                if(Enabled&&Member==0)
                {
                    ++LeaderGuides;
                    const auto Guide=FindBoundaryRoute(From,Desired,
                        Clamp(Speed*(Horizon+2.0/std::max(.1,90*Pi/180)),100.0,400.0),Gate);
                    if(Guide.Clear) { Desired=Guide.Heading;if(Desired!=FormationGoal) ++GuidedTurns; }
                }
                if(Member!=0)
                {
                    ++FollowerPlans;
                    Expect(Desired==FormationGoal,"boundary guidance preserves follower formation goal");
                }
                const auto End=[&](double Angle){return From+FromDegrees(Angle)*(Speed*Horizon);};
                const auto Safe=[&](double Angle){return Gate(From,End(Angle))&&(!RecoveryEnabled||Envelope(Member,From,End(Angle),Now,Horizon))&&Spacing.CanReserve(Id,From,End(Angle),Now,Horizon);};
                const auto Route=FindLocalRoute(Desired,Safe);
                if(RecoveryEnabled&&!Envelope(Member,From,From,Now,Horizon)){Cause[Member]=14;Idle();continue;}
                if(RecoveryEnabled&&!Align(Route.Clear?Route.Heading:Desired))continue;
                const double Heading=RecoveryEnabled?A.Yaw:SteerHeading(A.Yaw,Route.Clear?Route.Heading:Desired,Turn,90);
                Expect(std::abs(WrapDegrees(Heading-A.Yaw))<=90*std::min(Turn,.25)+1e-8,
                    "leader and follower keep single-frame yaw allowance");
                A.Yaw=Heading;
                if(!(RecoveryEnabled?Fresh(End(Heading)):Safe(Heading)))
                {
                    ++Rejected;Idle();if(Frame>=Frames-30*Fps) ++Blocked[Member];
                    if(Member==0&&!Route.Clear)
                    {
                        const bool WasPaused=Journey.Mode==TravelMode::Paused;
                        RejectedTurningLeaderMove(Journey,Length(From-SeedAnchor),Heading,FormationGoal);
                        if(!WasPaused&&Journey.Mode==TravelMode::Paused) PausedSince=Now;
                    }
                    continue;
                }
                if(!A.Walking&&Now-A.IdleSince<1.0) { if(Frame>=Frames-30*Fps) ++Dwell[Member];continue; }
                if(!PublishWalk(End(Heading),[&](){
                    ++Stamp.RelevantEndpoints;
                    if(Member==0)SuccessfulLeaderMove(Journey,Length(End(Heading)-SeedAnchor),Heading);
                })){Cause[Member]=19;++Rejected;Idle();continue;}
            }
            // Render sampling follows scheduled mutations, as the component upload does.
            // Capturing before mutations wrongly compares the previous post-update material
            // branch at CD25 equality against a pre-update CPU point.
            for(int I=0;I<Members;++I){auto& A=People[I];const Vec2 Root=A.Motion.At(Now);
                if(RecoveryEnabled){
                    const double GameNow=static_cast<float>(Now),Visible=A.Angular.Visible(Now);
                    const double Delta=std::abs(WrapDegrees(Visible-A.Angular.LastVisible));
                    Expect(Delta<=90*(GameNow-A.Angular.LastTime)+1e-7,"render-sampled angular segment never exceeds90deg per game-time second");
                    A.Vat.Observe(A.Angular.Core.HistoryUpdatedAt,A.Walking,GameNow);
                    const Vec2 CurrentDelta=SyntheticVatStudy::Sample(A.Vat.Current,GameNow)*A.Scale;
                    const Vec2 OldDelta=SyntheticVatStudy::Sample(A.Vat.Previous,A.Angular.LastTime)*A.Scale;
                    const Vec2 NewDelta=SyntheticVatStudy::Sample(A.Vat.Current,A.Angular.LastTime)*A.Scale;
                    const Vec2 SamplePose[]={{40*A.Scale,0},{-40*A.Scale,0},{0,40*A.Scale},{0,-40*A.Scale}};
                    for(int P=0;P<4;++P){
                        if(A.HavePose)Expect(Length(A.Angular.PreviousPosed(SamplePose[P],OldDelta,NewDelta,A.Angular.LastTime,A.Motion)-A.LastPosed[P])<1e-7,
                            "sampled previous posed body reconstructs prior frame across linear and angular mutations");
                        A.LastPosed[P]=A.Motion.At(GameNow)+AngularControllerStudy::Rotate(SamplePose[P]+CurrentDelta,Visible);
                        Expect(Length(SamplePose[P]+CurrentDelta)<=A.Body.Radius+1e-7,"varying synthetic VAT pose stays inside unchanged body bounds");
                    }
                    A.HavePose=true;
                    MaxYaw=std::max(MaxYaw,Delta);A.Angular.LastVisible=Visible;A.Angular.LastTime=GameNow;
                    if(A.Angular.Held){
                        Expect(!A.Walking&&Length(Root-A.Angular.Core.Current.Root)<1e-8,"angular held root has no translation");
                        const Vec2 Posed[]={{50,0},{-50,0},{0,45},{0,-45}};
                        for(const auto& P:Posed)Expect(Length(AngularControllerStudy::Rotate(P*A.Scale,Visible))<=A.Body.Radius+1e-7,"sampled posed vertex lies within held rotating envelope");
                    }
                }
            }
            TotalCalls+=PlanWork.Calls;TotalNodes+=PlanWork.Expanded;TotalQueries+=PlanWork.Queries;
            PeakNodes=std::max(PeakNodes,PlanWork.Expanded);PeakQueries=std::max(PeakQueries,PlanWork.Queries);PeakCalls=std::max(PeakCalls,PlanWork.Calls);
            Expect(PlanWork.Expanded<=96&&PlanWork.Queries<=512&&PlanWork.Calls<=2,"shared per-frame node/query/admission limits");
        }
        if(InjectRefusals){
            for(int I=0;I<Members;++I)Expect(InjectedRelocate[I]&&InjectedReserve[I],"actual schedule exercises both refusal types for every member");
            Expect(Spacing.RelocationRefusals==Members&&Spacing.ReservationRefusals==Members,"one real scheduled relocation and Reserve refusal per member");
        }
        int AngularStarts=0,AngularCommits=0;for(int I=0;I<Members;++I){AngularStarts+=People[I].Angular.Starts;AngularCommits+=People[I].Angular.Commits;}
        Budgets<<Population<<','<<Fps<<','<<Scale<<','<<Members<<','<<Budget<<','<<Fault<<','<<TerminalStart<<','<<RecoveryEnabled<<','<<Enabled<<','<<SharedHold<<','<<Frames<<','<<TotalCalls<<','<<TotalNodes<<','<<TotalQueries<<','<<PlacementWork.Queries<<','<<AngularStarts<<','<<AngularCommits<<'\n';
        Expect(Fault||TerminalStart!=0||((Horizon<=Sweeps*FrameSeconds||Deferred>0)&&FollowerPlans>0),"deferred-return coverage when revisit can precede horizon; followers observed");
        for(int I=0;I<Members;++I)Expect(Visits[I]>0,"every cohort member receives scheduled visits");
        Expect(MaximumVisitGap<=Sweeps,"cohort visits remain fair under actual population and budget");
        Expect(Fault||TerminalStart!=0||(Enabled?(LeaderGuides>0&&GuidedTurns>0):LeaderGuides==0),
            "enabled leader anticipates boundary while disabled control never invokes guide");
        double AllTravel=0;for(int I=0;I<Members;++I) AllTravel+=People[I].Distance;
        Expect(Fault||(AllTravel>0&&(TerminalStart||People[0].Distance>0)),"group fixture records real movement");
        if(RecoveryEnabled&&!Fault) {
            bool Walking=true;for(int I=0;I<Members;++I)for(int W=0;W<3;++W)Walking=Walking&&Late[I][W]>80;
            Expect(Walking,TerminalStart==1?"historical invalid input retains rejected walking result":"VALID START every member walks more than80cm in EACH final10s window");
            if(TerminalStart==2)Expect(Recovery.Entries==1,"legal induced stall enters one latched recovery episode");
        }
        if(RecoveryEnabled)
        {
            if(Fault) Expect(Recovery.State==Phase::Blocked&&Recovery.Entries==1&&Recovery.Steps==0,
                "blocked or invalid recovery remains explicit without reset cycles");
            RecoveryMetrics<<Population<<','<<Fps<<','<<Scale<<','<<Members<<','<<Budget<<','<<Fault<<','<<TerminalStart<<','<<static_cast<int>(Recovery.State)<<','
                <<Recovery.Entries<<','<<Recovery.Completions<<','<<Recovery.Steps<<','<<TurnVisits<<','<<DrainVisits<<','
                <<MaxYaw<<','<<Recovery.Invalid<<','<<(Recovery.State==Phase::Normal?0:Frames*FrameSeconds-Recovery.Entered);
            for(int I=0;I<MaxMembers;++I) RecoveryMetrics<<','<<Recovery.MemberSteps[I];
            RecoveryMetrics<<','<<Recovery.Plans<<','<<Recovery.Expanded<<','<<Recovery.PeakExpanded<<','<<Recovery.Queries<<','<<Recovery.Replans<<','<<Recovery.Unplayable<<','<<Recovery.ForwardLegs<<','<<Recovery.PlannerFailures<<','<<Recovery.ReservationWaits<<','<<Recovery.YawOnly<<','<<Recovery.Dwell<<','<<Travel.FormationRefusals<<','<<Travel.MaximumFormationError<<','<<Travel.MaximumPhysicalLag<<','<<Travel.GoalUpdates<<','<<PeerGoalWaitVisits<<','<<WaitYawVisits<<'\n';
        }
        double LateAll=0;int ClipHoldVisits=0;
        Vec2 FinalPositions[MaxMembers];
        for(int I=0;I<Members;++I)
        {
            FinalPositions[I]=People[I].LastRoot;
            LateAll+=Late[I][0]+Late[I][1]+Late[I][2];ClipHoldVisits+=ClipHolds[I];
            MemberMetrics<<Population<<','<<Fps<<','<<Scale<<','<<Members<<','<<Budget<<','<<Enabled<<','<<SharedHold<<','<<RecoveryEnabled<<','<<Fault<<','<<TerminalStart<<','<<I<<','<<Party.Members[I]<<','
                <<People[I].Distance<<','<<Late[I][0]<<','<<Late[I][1]<<','<<Late[I][2]<<','<<LongestStop[I]<<','
                <<Zero[I]<<','<<Blocked[I]<<','<<Dwell[I]<<','<<ClipHolds[I]<<"\n";
        }
        const auto FinalCmd=Steering(Party,0,FinalPositions,Journey.FormationHeading,{1,0},Config,Seed);
        Metrics<<Population<<','<<Fps<<','<<Scale<<','<<Members<<','<<Budget<<','<<Enabled<<','<<SharedHold<<','<<RecoveryEnabled<<','<<Fault<<','<<TerminalStart<<','<<People[0].Distance<<','<<LateLeaderTravel<<','
            <<AllTravel<<','<<LateAll<<','<<Rejected<<','<<Waits<<','<<Minimum<<','<<MaxLag<<','<<MaxFormation<<','
            <<FinalCmd.MaxLag<<','<<FinalCmd.MaxFormationError<<','<<ClipHoldVisits<<','<<(Failures-FailuresBefore)<<','<<PeakNodes<<','<<PeakQueries<<','<<PeakCalls<<','<<ExternalMoves<<','<<EnvelopeRefusals<<','<<Recovery.BudgetDeferrals<<','<<Recovery.Invalidations<<','<<Recovery.EndpointChangesDuringSearch<<','<<Recovery.CompletedAfterEndpointChange<<"\n";
        // Keep whole-cohort outcomes visible even when a leader improves. These
        // measurements are deliberately not assertions of universal recovery.
        std::cout<<"group members="<<Members<<" budget="<<Budget<<" enabled="<<Enabled
            <<" sharedHold="<<SharedHold<<" leaderTravel="<<People[0].Distance<<" lateLeaderTravel="<<LateLeaderTravel
            <<" allTravel="<<AllTravel<<" refusals="<<Rejected<<" waits="<<Waits
            <<" minSpacing="<<Minimum<<" maxLag="<<MaxLag<<" maxFormation="<<MaxFormation<<"\n";
    };
    if(InjectRefusals){
        for(int Members:{2,3,6})for(int Budget:{48,17})ScheduledGroup(Members,Budget,true,false,true);
        for(int Members:{2,3,6})for(int Population:{4000,10000})
            ScheduledGroup(Members,Population==4000?500:125,true,false,true,0,0,Population,30,1);
    }
    else {
    if(Seconds==120)
    for(int Members:{2,3,6}) for(int Budget:{48,17}) for(bool Enabled:{false,true}) for(bool SharedHold:{false,true})
        ScheduledGroup(Members,Budget,Enabled,SharedHold);
    for(int Members:{2,3,6}) for(int Budget:{48,17})
    {
        ScheduledGroup(Members,Budget,true,false,true);
        ScheduledGroup(Members,Budget,true,false,true,0,true);
        ScheduledGroup(Members,Budget,true,false,true,0,2);
        if(Seconds==120)for(int Fault:{1,2,3})ScheduledGroup(Members,Budget,true,false,true,Fault);
    }
    for(int Population:{2500,5000,10000})for(int Budget:{500,125})for(int Fps:{30,60})for(double Scale:{.92,1.08})
    for(int Members:{2,3,6})
    {
        ScheduledGroup(Members,Budget,true,false,true,0,false,Population,Fps,Scale);
        ScheduledGroup(Members,Budget,true,false,true,0,true,Population,Fps,Scale);
        ScheduledGroup(Members,Budget,true,false,true,0,2,Population,Fps,Scale);
        if(Seconds==120)for(int Fault:{1,2,3})ScheduledGroup(Members,Budget,true,false,true,Fault,false,Population,Fps,Scale);
    }
    for(int Members:{2,3,6})for(int Terminal:{0,1,2})ScheduledGroup(Members,500,true,false,true,0,Terminal,4000,30,0);
    }
    {
        TravellingCohortStudy::Travel T;Vec2 Goals[2]={{0,0},{120,0}};T.Begin(2,Goals);
        MotionReservation Good[2]={{{0,0},{10,0},0,1},{{120,0},{130,0},0,1}};
        Expect(T.Within(Good,0,250),"parallel cohort reservations preserve formation");
        MotionReservation Bad[2]={{{0,0},{-100,0},0,1},{{300,0},{300,0},0,0}};
        Expect(!T.Within(Bad,0,250),"safe current pose cannot reserve future formation escape");
        Vec2 Roots[2]={{0,0},{120,0}};Vec2 Next[2];
        auto Free=[](Vec2 A,Vec2 B){return Finite(A)&&Finite(B)&&Length(B-A)<=100;};
        Expect(T.Update(Roots,Next,100,Free)&&Length(Next[0]-Vec2{100,0})<1e-7,
            "travelling frontier uses existing slow-lag distance");
        Roots[0]={50,0};Roots[1]={160,0};
        Expect(T.Update(Roots,Next,100,Free)&&Length(Next[0]-Vec2{140,0})<1e-7,
            "frontier advances before every member reaches a leg endpoint");
        T.Anchors={{0,0},{400,0},{400,-400}};T.Progress[0]=T.Progress[1]=0;
        Roots[0]={380,-60};Roots[1]={490,0};
        Expect(T.Update(Roots,Next,100,Free)&&Length(Next[0]-Vec2{400,0})<1e-7,
            "lookahead cannot bypass an unacknowledged member corner");
        Roots[0]={400,0};Roots[1]={490,0};
        Expect(T.Update(Roots,Next,100,Free)&&Next[0].Y<0&&Next[1].Y==0,
            "one member may round its corner without an all-arrived barrier");
    }
    {
        WaitTurnStudy::Latch L;
        double Y=L.Turn(3,-90,90,1./30);
        Expect(std::abs(WrapDegrees(Y-90))<=3.0000001,"wait alignment does not acquire cadence-sized yaw credit");
        const double Next=L.Turn(3,45,Y,1./30);
        Expect(L.Heading==-90&&Next<Y,"changing blocked-goal suggestion cannot chase a new heading on same leg");
        L.Turn(4,0,Next,1./30);Expect(L.Heading==0,"new absolute route leg changes retained orientation intent");
    }
    std::cout<<"CrowdBoundaryMath: "<<Checks<<" checks, "<<Failures<<" failures\n";
    return Failures?1:0;
}
