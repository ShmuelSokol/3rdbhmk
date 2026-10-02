#include "CrowdGroupMath.h"
#include "CrowdBoundaryCadenceStudy.h"
#include <iostream>
#include <limits>
int main()
{
    using namespace MikdashCrowd;
    using namespace MikdashCrowdGroups;
    int Checks=0,Failures=0;
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
    // Group fixture: common-time follower targets, physical-spread cohesion,
    // real timed reservations and round-robin visits split across cohort members.
    // Two standing neighbours keep their reservations/positions throughout.
    // Native ground/sweeps and authored flow variation are intentionally absent.
    auto ScheduledGroup=[&](int Members,int Budget,bool Enabled)
    {
        constexpr int First=15,Population=48,Frames=3600;
        constexpr uint32_t Seed=13;
        const double FrameSeconds=static_cast<float>(1.0/30.0);
        const int Sweeps=FramesPerSweep(Population,Budget);
        const double Horizon=static_cast<float>(VatHorizonSeconds(Sweeps,FrameSeconds,.12,.7));
        const Vec2 SeedAnchor{400,-100};
        Cohort Party;Party.Count=Members;Party.Identity=47;Party.Speed=90;
        Settings Config;MikdashCrowdGroups::Travel Journey;
        struct Walker
        {
            Vec2 Anchor{},LastRoot{};MotionReservation Motion{};
            double AnchorTime=0,Yaw=0,IdleSince=-1,Distance=0;
            bool Walking=false;
        };
        Walker People[MaxMembers];SpatialIndex Spacing;
        for(int I=0;I<Members;++I)
        {
            Party.Members[I]=First+I;
            People[I].Anchor=SeedAnchor+Offset(I,Seed,Party.Identity,Config.SpacingCm);
            People[I].LastRoot=People[I].Anchor;
            People[I].Motion={People[I].Anchor,People[I].Anchor,0,0};
            Expect(Spacing.Insert(First+I,People[I].Anchor),"group fixture seeds authored separated slots");
        }
        const Vec2 Standing[]={{800,400},{800,520}};
        for(int I=0;I<2;++I) Expect(Spacing.Insert(40+I,Standing[I]),"standing neighbours seed separately");
        int Cursor=0,LeaderGuides=0,GuidedTurns=0,FollowerPlans=0,Rejected=0,Waits=0,Deferred=0;
        double PausedSince=-1,Minimum=1e9,MaxLag=0,MaxFormation=0,LateLeaderTravel=0;
        for(int Frame=0;Frame<Frames;++Frame)
        {
            const double Now=Frame*FrameSeconds;
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
                        const Vec2 Q=J<Members?People[J].Motion.At(Time):Standing[J-Members];
                        const double Distance=Length(P-Q);Minimum=std::min(Minimum,Distance);
                        Expect(Distance>=80-1e-7,"group subframe spacing including standing neighbours stays80cm");
                    }
                }
            }
            for(int I=0;I<Members;++I)
            {
                auto& A=People[I];const Vec2 Root=A.Motion.At(Now);
                const double Distance=Length(Root-A.LastRoot);A.Distance+=Distance;
                if(I==0&&Frame>=Frames-900) LateLeaderTravel+=Distance;
                Expect(Distance<=std::min(90*1.15,99.0/Horizon)*FrameSeconds+1e-7,
                    "group rendered root has no unreserved jump");
                A.LastRoot=Root;
            }
            const auto Window=NextUpdateWindow(Cursor,Population,Budget);Cursor=Window.NextCursor;
            const int Starts[]={Window.FirstStart,Window.SecondStart};
            const int Counts[]={Window.FirstCount,Window.SecondCount};
            for(int Slice=0;Slice<2;++Slice) for(int Id=Starts[Slice];Id<Starts[Slice]+Counts[Slice];++Id)
            {
                if(Id<First||Id>=First+Members) continue;
                const int Member=Id-First;auto& A=People[Member];
                if(A.Walking&&Now<A.Motion.End)
                {
                    ++Deferred;
                    Expect(!Spacing.CanReserve(Id,A.Anchor,A.Anchor,Now,Horizon),"group cannot replace live reserved movement");
                    continue;
                }
                const double Elapsed=Clamp(Now-A.AnchorTime,0.0,Horizon);
                const Vec2 From=A.Motion.At(Now);
                Expect(Spacing.Relocate(Id,A.Anchor,From,Now),"group commits completed segment at common-time root");
                A.Anchor=From;A.AnchorTime=Now;A.Motion={From,From,Now,Now};
                const auto Idle=[&]() { if(A.Walking) A.IdleSince=Now;A.Walking=false; };
                if(Member==0&&Journey.Mode==TravelMode::Paused)
                {
                    if(PausedSince<0) PausedSince=Now;
                    else if(Now-PausedSince>=12*(.75+.5*HashUnit(Seed,Party.Identity,83u)))
                    { Journey.Mode=TravelMode::Returning;PausedSince=-1; }
                }
                Vec2 Positions[MaxMembers];
                for(int I=0;I<Members;++I) Positions[I]=People[I].Motion.At(Now);
                const Vec2 Flow=Journey.Mode==TravelMode::Returning?Normalized(SeedAnchor-Positions[0]):Vec2{1,0};
                const auto Cmd=Steering(Party,Member,Positions,Journey.FormationHeading,Flow,Config,Seed,
                    Journey.Mode==TravelMode::Paused);
                Expect(Cmd.Valid,"scheduled cohort steering stays valid");
                MaxLag=std::max(MaxLag,Cmd.MaxLag);MaxFormation=std::max(MaxFormation,Cmd.MaxFormationError);
                if(Cmd.Waiting) ++Waits;
                const double Speed=std::min(VatPlayableSpeed(Cmd.Speed,119.95,1,.45,1.55),99.0/Horizon);
                if(Speed<=0) { Idle();continue; }
                const double Turn=Clamp(std::max(std::min(Elapsed,FrameSeconds),1.0/120.0),0.0,.5);
                const double FormationGoal=YawDegrees(Cmd.Direction);
                double Desired=FormationGoal;
                if(Enabled&&Member==0)
                {
                    ++LeaderGuides;
                    const auto Guide=FindBoundaryRoute(From,Desired,
                        BoundaryLookAhead(Speed,Horizon,FrameSeconds,Turn,90,Sweeps),Gate);
                    if(Guide.Clear) { Desired=Guide.Heading;if(Desired!=FormationGoal) ++GuidedTurns; }
                }
                if(Member!=0)
                {
                    ++FollowerPlans;
                    Expect(Desired==FormationGoal,"boundary guidance preserves follower formation goal");
                }
                const auto End=[&](double Angle){return From+FromDegrees(Angle)*(Speed*Horizon);};
                const auto Safe=[&](double Angle){return Gate(From,End(Angle))&&Spacing.CanReserve(Id,From,End(Angle),Now,Horizon);};
                const auto Route=FindLocalRoute(Desired,Safe);
                const double Heading=SteerHeading(A.Yaw,Route.Clear?Route.Heading:Desired,Turn,90);
                Expect(std::abs(WrapDegrees(Heading-A.Yaw))<=90*std::min(Turn,.25)+1e-8,
                    "leader and follower keep single-frame yaw allowance");
                A.Yaw=Heading;
                if(!Safe(Heading))
                {
                    ++Rejected;Idle();
                    if(Member==0&&!Route.Clear)
                    {
                        const bool WasPaused=Journey.Mode==TravelMode::Paused;
                        RejectedTurningLeaderMove(Journey,Length(From-SeedAnchor),Heading,FormationGoal);
                        if(!WasPaused&&Journey.Mode==TravelMode::Paused) PausedSince=Now;
                    }
                    continue;
                }
                if(!A.Walking&&Now-A.IdleSince<1.0) continue;
                Expect(Spacing.Reserve(Id,From,End(Heading),Now,Horizon),"group reserves actual limited-yaw segment");
                A.Walking=true;A.Motion={From,End(Heading),Now,Now+Horizon};
                if(Member==0) SuccessfulLeaderMove(Journey,Length(End(Heading)-SeedAnchor),Heading);
            }
        }
        Expect(Deferred>0&&FollowerPlans>0,"group fixture exercises deferred reservations and followers");
        Expect(Enabled?(LeaderGuides>0&&GuidedTurns>0):LeaderGuides==0,
            "enabled leader anticipates boundary while disabled control never invokes guide");
        double AllTravel=0;for(int I=0;I<Members;++I) AllTravel+=People[I].Distance;
        Expect(AllTravel>0&&People[0].Distance>0,"group fixture records real movement");
        // Keep whole-cohort outcomes visible even when a leader improves. These
        // measurements are deliberately not assertions of universal recovery.
        std::cout<<"group members="<<Members<<" budget="<<Budget<<" enabled="<<Enabled
            <<" leaderTravel="<<People[0].Distance<<" lateLeaderTravel="<<LateLeaderTravel
            <<" allTravel="<<AllTravel<<" refusals="<<Rejected<<" waits="<<Waits
            <<" minSpacing="<<Minimum<<" maxLag="<<MaxLag<<" maxFormation="<<MaxFormation<<"\n";
    };
    for(int Members:{2,3,6}) for(int Budget:{48,17}) for(bool Enabled:{false,true})
        ScheduledGroup(Members,Budget,Enabled);
    std::cout<<"CrowdBoundaryMath: "<<Checks<<" checks, "<<Failures<<" failures\n";
    return Failures?1:0;
}
