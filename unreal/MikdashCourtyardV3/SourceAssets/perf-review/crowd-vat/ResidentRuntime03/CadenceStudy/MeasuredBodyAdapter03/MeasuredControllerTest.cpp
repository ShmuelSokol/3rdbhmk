#include "MeasuredControllerPort.h"
#include <iostream>
#include <stdexcept>
using namespace MeasuredBodyStudy;
int Checks=0,Failures=0;
void Check(bool V,const char* Name){++Checks;if(!V){++Failures;std::cerr<<"FAIL "<<Name<<"\n";}}
struct World:WorldPort {
    uint64_t WorldRev=1,BindingRev=1;bool Support=true,Overlap=true,Sweep=true,Complete=true,Footprint=true;
    bool Contact=true,Riser=false,Reject=false,Throw=false,ChangeWorld=false;
    int BeforeCalls=0,RejectCall=0,ThrowCommitCall=0,ChangeCommitCall=0;double Floor=0;Request Seen;
    std::function<void()> Callback;
    uint64_t Version()const override{return WorldRev;}
    uint64_t BindingVersion()const override{return BindingRev;}
    bool Ground(Vec2,double,double& Z)override{Z=Floor;return std::isfinite(Z);}
    WorldEvidence Check(const Request& Q)override {
        Seen=Q;if(Throw)throw std::runtime_error("world fixture");if(Callback)Callback();if(ChangeWorld)++WorldRev;
        return {Q.Serial,Q.WorldVersion,100,7,Support,Footprint,Overlap,Sweep,Complete,"fixture independent support contact",
            {{100,Riser?8:7,Contact}}};
    }
    bool BeforeCommit(const Request&)override{++BeforeCalls;if(BeforeCalls==ThrowCommitCall)throw std::runtime_error("commit fixture");
        if(BeforeCalls==ChangeCommitCall)++WorldRev;return !Reject&&BeforeCalls!=RejectCall;}
};
struct Fixture {
    World W;std::map<int,Binding> Live;
    ReservationIndex Index;
    Fixture():Index(W,[this](int Id){auto I=Live.find(Id);return I==Live.end()?Binding{}:I->second;}){}
    bool Add(int Id,int Profile,Vec2 P,double Z=0){Live[Id]=Measured(Id,1,Profile);return Index.Register(Live[Id],P,Z);}
};
struct Agent {
    AngularWalkingStudy::ScheduledTurn Angular;Vec2 Anchor{};double AnchorTime=0,Yaw=0;
    MotionReservation Motion{};bool Walking=false;
};
Agent MakeAgent(const Binding& B,Vec2 Root={0,0}) {
    Agent A;A.Anchor=Root;A.Motion={Root,Root,0,0};A.Angular.Core.Current.Root=Root;
    A.Angular.Core.Current.Envelope=B.Bounds;A.Angular.Core.Previous=A.Angular.Core.Current;return A;
}
int main(){
    // Six measured fixtures, separate from every historical synthetic matrix.
    for(int P=0;P<6;++P){
        Fixture F;Check(F.Add(1,P,{0,0}),"register measured profile");auto A=MakeAgent(F.Live[1]);
        CadenceRecoveryStudy::Episode E;int Publications=0;
        Check(Walk(A,F.Index,1,{0,0},{50,0},1,1,[&](){++Publications;}),"actual ReserveWalk accepts measured bounds");
        Check(Publications==1&&A.Walking&&A.Motion.To.X==50&&F.Index.Reserved(1),"index precedes actor publication");
        Check(F.W.Seen.Identity.Bounds.MinZ==Profiles[P].MinZ&&F.W.Seen.Identity.Bounds.MinZ<0,"signed minZ unchanged");
        Check(F.W.Seen.CapsuleHalfHeight()==(Profiles[P].MaxZ-Profiles[P].MinZ)/2+Profiles[P].Radius,"enclosing capsule formula");
        Check(Arrival(A,E,F.Index,1,0,1,1.5,false)==CommitGatesStudy::Arrival::Deferred,"live linear cannot relocate");
        Check(Arrival(A,E,F.Index,1,0,1,2,false)==CommitGatesStudy::Arrival::Committed,"actual CommitArrival drains");
        Check(A.Anchor.X==50&&!F.Index.Reserved(1)&&F.Index.Anchor(1).X==50,"arrival state/index same root");
        Check(F.Index.Envelope(1).MinZ==Profiles[P].MinZ,"no clamp after relocation");
    }
    for(int Fault=0;Fault<6;++Fault){
        Fixture F;Check(F.Add(1,1,{0,0}),"fixture registration");auto A=MakeAgent(F.Live[1]);int Published=0;
        if(Fault==0)F.W.Support=false;if(Fault==1)F.W.Footprint=false;if(Fault==2)F.W.Overlap=false;
        if(Fault==3)F.W.Sweep=false;if(Fault==4)F.W.Riser=true;if(Fault==5)F.W.Contact=false;
        const auto Before=F.Index.Revision();
        Check(!Walk(A,F.Index,1,{0,0},{0,0},1,1,[&](){++Published;}),"world refusal through actual ReserveWalk");
        Check(!A.Walking&&Published==0&&!F.Index.Reserved(1)&&F.Index.Revision()==Before,"world refusal atomic");
        if(Fault>=4)Check(F.Index.Reason()==Refusal::PotentialObstacle,"riser/same-face uncertified is potential obstacle not penetration");
    }
    // A true CanReserve never authorizes stale/failed subsequent Reserve.
    {Fixture F;F.Add(1,1,{0,0});auto A=MakeAgent(F.Live[1]);int Published=0;
        Check(F.Index.CanReserve(1,{0,0},{50,0},1,1),"fresh precheck");F.W.Reject=true;
        auto Stamp=F.Index.Revision();Check(!Walk(A,F.Index,1,{0,0},{50,0},1,1,[&](){++Published;}),"final commit refusal");
        Check(Published==0&&!A.Walking&&!F.Index.Reserved(1)&&F.Index.Revision()==Stamp,"no partial actor/history/index commit");
    }
    // Own identity/scale/bounds/hash are copied immutable admission keys.
    for(int Fault=0;Fault<5;++Fault){Fixture F;F.Add(1,1,{0,0});auto& B=F.Live[1];
        if(Fault==0)++B.Incarnation;if(Fault==1)B.Scale=1.08;if(Fault==2)B.Bounds.MinZ=0;
        if(Fault==3)B.Bounds.Radius=50;if(Fault==4)B.EvidenceHash="new";
        Check(!F.Index.Reserve(1,{0,0},{10,0},1,1)&&F.Index.Blocked(),"identity mutation invalidates");
        Check(F.Index.Size()==1&&F.Index.Envelope(1).MinZ==Profiles[1].MinZ,"invalidation retains occupancy/bounds");
    }
    {Fixture F;F.Add(1,0,{0,0});F.Add(2,5,{500,0});
        Check(F.Index.QueryReach(1)==std::max(80.,Profiles[0].Radius+Profiles[5].Radius)+100,"exact max peer query reach");
        ++F.W.BindingRev;Check(!F.Index.Reserve(1,{0,0},{10,0},1,1)&&F.Index.Blocked(),"global rendered mutation invalidates before spatial query");
    }
    // Peer anchor201 is omitted by old[-200,0] cells around candidate x=-20.
    {Fixture F;F.Add(2,5,{201,0});Check(F.Index.Reserve(2,{201,0},{101,0},0,1),"preexisting peer motion");F.Add(1,2,{-20,0});
        Check(F.Index.QueryReach(1)>220,"query reaches missing old cell");
        Check(!F.Index.Reserve(1,{-20,0},{-20,0},0,1)&&F.Index.Reason()==Refusal::Peer,"full measured pair catches projecting peer");
        Check(!F.Index.Reserve(1,{-20,0},{-20,0},100,1),"endpoint hold never expires");
    }
    {Fixture F;F.Add(1,1,{0,0});auto Stamp=F.Index.Revision();F.W.ChangeWorld=true;
        Check(!F.Index.Reserve(1,{0,0},{10,0},1,1)&&F.Index.Reason()==Refusal::Invalidated,"world callback version change");
        Check(F.Index.Revision()==Stamp&&!F.Index.Reserved(1),"stale evidence does not publish");
        F.W.ChangeWorld=false;F.W.Callback=[&](){F.Index.Invalidate();};
        Check(!F.Index.Reserve(1,{0,0},{10,0},1,1)&&F.Index.Blocked(),"callback identity invalidation");
    }
    {Fixture F;F.Add(1,1,{0,0});bool Nested=true;F.W.Callback=[&](){Nested=F.Index.Reserve(1,{0,0},{10,0},1,1);};
        Check(F.Index.Reserve(1,{0,0},{10,0},1,1)&&!Nested,"reentrant reservation refused");
        Check(F.Index.Reason()==Refusal::None,"nested refusal does not leak into successful outcome");
    }
    {Fixture F;F.Add(1,1,{0,0});F.W.Throw=true;bool Threw=false;
        try{F.Index.Reserve(1,{0,0},{10,0},1,1);}catch(const std::runtime_error&){Threw=true;}
        Check(Threw&&!F.Index.Reserved(1),"callback exception no reservation");F.W.Throw=false;
        Check(F.Index.Reserve(1,{0,0},{10,0},1,1),"RAII releases query flag");
    }
    // Actual scheduled turn path uses signed measured envelope and a persistent hold.
    {Fixture F;F.Add(1,2,{0,0});auto A=MakeAgent(F.Live[1]);CadenceRecoveryStudy::Episode E;
        F.W.Reject=true;Align(A,F.Index,1,90,0);
        Check(!A.Angular.Held&&!F.Index.Reserved(1)&&A.Angular.Starts==0,"failed angular hold cannot publish turn");
        F.W.Reject=false;Align(A,F.Index,1,90,0);
        Check(A.Angular.Held&&F.Index.Reserved(1)&&A.Angular.Starts==1,"measured turn admitted");
        Check(Arrival(A,E,F.Index,1,0,1,.5,true)==CommitGatesStudy::Arrival::Deferred,"turn not backdated");
        Check(Arrival(A,E,F.Index,1,0,1,2,true)==CommitGatesStudy::Arrival::Committed,"scheduled turn rebase through actual controller");
        Check(A.Yaw==90&&A.Angular.Commits==1&&!F.Index.Reserved(1),"turn completion index/actor agreement");
    }
    // Relocation capacity failure leaves actor/episode/index at the prior state.
    {Fixture F;F.Add(1,1,{201,0});auto A=MakeAgent(F.Live[1],{201,0});CadenceRecoveryStudy::Episode E;
        Check(Walk(A,F.Index,1,{201,0},{199,0},0,1,[](){}),"cross-cell admitted motion");
        for(int I=0;I<64;++I)Check(F.Add(10+I,1,{0,0}),"fill destination existing snapshot");
        Check(!F.Add(100,1,{0,0}),"cell64 fixed cap");auto Stamp=F.Index.Revision();
        Check(Arrival(A,E,F.Index,1,0,1,2,false)==CommitGatesStudy::Arrival::Refused,"arrival capacity refusal");
        Check(A.Anchor.X==201&&A.Walking&&F.Index.Anchor(1).X==201&&F.Index.Reserved(1)&&F.Index.Revision()==Stamp,"arrival failure atomic");
        Check(F.Index.StorageCells()==2,"refused relocation does not add empty storage");
    }
    // Atomic bounded batch: final member commit denial leaves ALL reservations untouched.
    for(bool Deny:{true,false}){Fixture F;for(int I=0;I<3;++I)F.Add(I,1,{0,I*300.});
        ReservationIndex::BatchMove M[3]={{0,{0,0},{50,0},1,1},{1,{0,300},{50,300},1,1},{2,{0,600},{50,600},1,1}};
        F.W.RejectCall=Deny?3:0;auto Stamp=F.Index.Revision();
        Check(F.Index.ReserveBatch(M,3)==!Deny,"atomic three-body reservation outcome");
        for(int I=0;I<3;++I)Check(F.Index.Reserved(I)==!Deny,"batch no partial reservation");
        Check(F.Index.Revision()==Stamp+(Deny?0:1),"single batch commit revision");
    }
    for(bool Throw:{false,true}){Fixture F;for(int I=0;I<3;++I)F.Add(I,1,{0,I*300.});
        ReservationIndex::BatchMove M[3]={{0,{0,0},{50,0},1,1},{1,{0,300},{50,300},1,1},{2,{0,600},{50,600},1,1}};
        F.W.ThrowCommitCall=Throw?3:0;F.W.ChangeCommitCall=Throw?0:3;const auto Stamp=F.Index.Revision();bool Result=false,Caught=false;
        try{Result=F.Index.ReserveBatch(M,3);}catch(const std::runtime_error&){Caught=true;}
        Check(!Result&&Caught==Throw,"last batch callback throw/world-change rejects");
        for(int I=0;I<3;++I)Check(!F.Index.Reserved(I),"late batch fault publishes no member");
        Check(F.Index.Revision()==Stamp,"late batch fault retains index epoch");
    }
    {Fixture F;F.Add(1,1,{0,0});F.Add(2,1,{190,190});
        Check(F.Index.StorageCells()==1,"two occupants share original bucket");
        Check(F.Index.Reserve(1,{0,0},{-100,0},0,1)&&F.Index.Relocate(1,{0,0},{-100,0},1),"one occupant leaves shared bucket");
        Check(F.Index.StorageCells()==2&&F.Index.Size()==2&&F.Index.Anchor(2).X==190,"prune never erases other occupancy");
    }
    {Fixture F;F.Add(1,1,{0,0});Check(!F.Index.Reserve(1,{0,0},{100.01,0},0,1),"100cm step unchanged");
        Check(!F.Index.Reserve(1,{0,0},{1,0},0,0),"zero-duration teleport refused");
        Binding Synthetic=Measured(2,1,1);Synthetic.Bounds={50,0,190,true};F.Live[2]=Synthetic;
        Check(!F.Index.Register(Synthetic,{500,0},0),"synthetic profile cannot enter measured matrix");
    }
    {Fixture F;F.Add(1,1,{0,0});auto A=MakeAgent(F.Live[1]);CadenceRecoveryStudy::Episode E;
        for(int I=0;I<2000;++I){const Vec2 From{I*100.,0},To{(I+1)*100.,0};const double T=I*2.;
            Check(Walk(A,F.Index,1,From,To,T,1,[](){}),"long traversal reserve");
            Check(F.Index.StorageCells()==1&&F.Index.Anchor(1).X==From.X&&F.Index.Reserved(1),"active reservation retains old anchor cell");
            Check(Arrival(A,E,F.Index,1,0,1,T+1,false)==CommitGatesStudy::Arrival::Committed,"long traversal actual arrival");
            Check(F.Index.StorageCells()==1&&F.Index.Size()==1&&F.Index.Anchor(1).X==To.X,"prune empty bucket; storage bounded by occupied cells");
        }
    }
    // From may straddle a bucket boundary within accepted 1e-6 tolerance.
    // Exercise both axes, negative/zero/positive boundaries and both directions.
    for(int Axis=0;Axis<2;++Axis)for(double Edge:{-400.,-200.,0.,200.,400.})
    for(double Sign:{-1.,1.})for(bool Cross:{false,true}){
        Fixture F;Vec2 Stored{50,50},From{50,50},To{50,50};
        const double A=Edge+(Sign>0?0:-.00000025);
        const double B=Edge+(Sign>0?-.00000025:0);
        if(Axis==0){Stored.X=A;From.X=B;To.X=Cross?B:A;}
        else{Stored.Y=A;From.Y=B;To.Y=Cross?B:A;}
        Check(F.Add(1,1,Stored),"boundary registration");
        const auto Revision=F.Index.Revision();bool Result=false,Threw=false;
        try{Result=F.Index.Relocate(1,From,To,1);}catch(...){Threw=true;}
        Check(Result&&!Threw,"tolerated boundary relocation must not throw");
        Check(F.Index.Revision()==Revision+1&&F.Index.Size()==1&&F.Index.StorageCells()==1,
            "boundary relocation exactly one occupant/cell/revision");
        Check(Length(F.Index.Anchor(1)-To)==0&&!F.Index.Reserved(1),"boundary destination stored exactly");
        for(int Id=2;Id<=64;++Id)Check(F.Add(Id,1,To),"all63 remaining capacity retained");
        const auto FullRevision=F.Index.Revision();
        Check(!F.Add(65,1,To)&&F.Index.Reason()==Refusal::Capacity,"boundary cell cap remains64");
        Check(F.Index.Size()==64&&F.Index.StorageCells()==1&&F.Index.Revision()==FullRevision,
            "capacity refusal preserves occupancy/revision");
        Vec2 Bad=From;Bad.X+=1.;const auto Before=F.Index.Motion(1);
        Check(!F.Index.Relocate(1,Bad,To,2)&&F.Index.Reason()==Refusal::Motion,
            "outside tolerance refused");
        const auto After=F.Index.Motion(1);
        Check(F.Index.Revision()==FullRevision&&Length(F.Index.Anchor(1)-To)==0&&
            Length(Before.From-After.From)==0&&Length(Before.To-After.To)==0&&
            Before.Start==After.Start&&Before.End==After.End,"refusal preserves complete motion");
    }
    std::cout<<"{\"suite\":\"MeasuredController03\",\"checks\":"<<Checks<<",\"failures\":"<<Failures<<",\"profiles\":6,\"longTraversalMoves\":2000,\"historicalSyntheticMatrixRun\":false}\n";
    return Failures?1:0;
}
