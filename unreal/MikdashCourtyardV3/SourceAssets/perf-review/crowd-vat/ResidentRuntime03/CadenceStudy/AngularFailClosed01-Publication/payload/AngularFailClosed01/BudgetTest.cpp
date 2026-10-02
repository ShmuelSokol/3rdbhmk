#include "BudgetedPlacement.h"
#include "AtomicCohortCommit.h"
#include "TravellingCohortStudy.h"
#include <iostream>
using namespace PlacedActualHorizonStudy;
int Checks=0,Failures=0;
void Check(bool B){++Checks;if(!B)++Failures;}
struct Port {
 int Calls=0,Commits=0;
 bool Sample(int,Vec2& P,double& H){++Calls;P={0,0};H=0;return true;}
 bool Ground(int,Vec2,double& Z){++Calls;Z=0;return true;}
 bool RootAndLink(Vec2,Vec2){++Calls;return true;}
 bool HeldCapsuleSweep(Vec2,double,Vec2,double,Body){++Calls;return true;}
 bool CommittedPeers(Vec2,double,Body){++Calls;return true;}
 bool CommitBatch(const Vec2*,const double*,const Body*,int){++Calls;++Commits;return true;}
};
int main(){
 Vec2 Slots[6];for(int I=0;I<6;++I)Slots[I]=Offset(I,13,47,120);
 for(int FailAfter=0;FailAfter<6;++FailAfter){
   SpatialIndex Index;Check(Index.Insert(99,{800,800}));
   Check(Index.Reserve(99,{800,800},{850,800},0,1));
   int SawWritten=0;
   Check(!CommitCohort(Index,15,Slots,6,[&](int I){
       Check(!Index.SegmentClear(Slots[I],Slots[I],-1));++SawWritten;return I!=FailAfter;
   }));
   Check(SawWritten==FailAfter+1);
   for(int I=0;I<6;++I)Check(Index.SegmentClear(Slots[I],Slots[I],-1));
   // Foreign live reservation still exists and cannot be relocated before expiry.
   Check(!Index.Relocate(99,{800,800},{850,800},.5));
   Check(Index.Relocate(99,{800,800},{850,800},1));
   Check(CommitCohort(Index,15,Slots,6,[](int){return true;}));
 }
 // A real failed insertion must not remove a pre-existing conflicting visitor.
 SpatialIndex Conflict;Check(Conflict.Insert(500,Slots[2]));
 Check(!CommitCohort(Conflict,15,Slots,6,[](int){return true;}));
 Check(Conflict.SegmentClear(Slots[0],Slots[0],-1)&&!Conflict.SegmentClear(Slots[2],Slots[2],-1));
 Body Bodies[6];for(auto& B:Bodies)B={54,0,205.2,true};
 struct AtomicPort:Port {
   SpatialIndex Index;int FailAfter=0;
   bool CommitBatch(const Vec2* Points,const double*,const Body*,int N){
     ++Commits;return CommitCohort(Index,15,Points,N,[&](int I){return I!=FailAfter;});
   }
 };
 for(int Fault=0;Fault<6;++Fault){
   AtomicPort Actual;Actual.FailAfter=Fault;Formation Layout;Layout.Spacing=-1;
   Vec2 Output[6];for(auto& V:Output)V={7777,8888};ActualHorizonReview::Budget Frame;
   Check(Place(6,Bodies,13,47,120,Actual,Output,Layout,Frame)==PlacementStatus::Refused);
   Check(Actual.Commits==1&&Layout.Spacing==-1&&Frame.Queries==111);
   for(int I=0;I<6;++I){Check(Output[I].X==7777&&Output[I].Y==8888);Check(Actual.Index.SegmentClear(Slots[I],Slots[I],-1));}
 }
 Vec2 Published[6];for(auto& P:Published)P={1234,5678};Formation F;F.Spacing=-1;Port P;
 ActualHorizonReview::Budget Work;Work.Queries=402;
 Check(Place(6,Bodies,13,47,120,P,Published,F,Work)==PlacementStatus::Deferred);
 Check(P.Calls==0&&P.Commits==0&&Work.Queries==402&&F.Spacing==-1&&Published[0].X==1234);
 Work.Queries=401;
 Check(Place(6,Bodies,13,47,120,P,Published,F,Work)==PlacementStatus::Placed);
 Check(Work.Queries==512&&P.Commits==1);
 // Several independent admission requests share one frame budget.
 Work={};P={};int Admitted=0,Deferred=0;
 for(int I=0;I<10;++I){auto R=Place(6,Bodies,13,I,120,P,Published,F,Work);if(R==PlacementStatus::Placed)++Admitted;else if(R==PlacementStatus::Deferred)++Deferred;}
 Check(Admitted==4&&Deferred==6&&Work.Queries==444&&P.Commits==4);
 // Transactional formation route discovery survives a deliberately short frame.
 TravellingCohortStudy::Travel Travel;Vec2 Goals[6],Roots[6];
 for(int I=0;I<6;++I)Goals[I]=Roots[I]=Offset(I,13,47,120);
 Travel.Begin(6,Goals);FormationCache Cache;Cache.ObserveGeometry(1);
 Work={};Work.Queries=511;int Queries=0;
 const auto Free=[&](Vec2 A,Vec2 B){++Queries;return Finite(A)&&Finite(B)&&Length(B-A)<=100;};
 Check(!Update(Travel,Roots,Goals,100,Cache,Work,Free));
 Check(Cache.Deferred&&!Travel.Failed&&Travel.Anchors.size()==1&&Travel.GoalUpdates==0&&Goals[0].X==0&&Work.Queries==512);
 const auto Saved=Cache.Entries.size();Check(Saved==1);
 Work={};Check(Update(Travel,Roots,Goals,100,Cache,Work,Free));
 Check(Travel.Active&&!Travel.Failed&&Travel.Anchors.size()==2&&Travel.GoalUpdates==1&&Goals[0].X==100);
 Check(Queries==30&&Work.Queries==29&&Cache.Entries.empty());
 // Geometry invalidation discards only cached static formation checks.
 Cache.Query({0,0},{1,0},Work,Free);Check(Cache.Entries.size()==1);
 Cache.ObserveGeometry(2);Check(Cache.Entries.empty());
 // A real blocked result is not reclassified as budget deferral.
 TravellingCohortStudy::Travel Blocked;Vec2 G[2]={{0,0},{0,120}},R[2]={{0,0},{0,120}};Blocked.Begin(2,G);Work={};
 Check(!Update(Blocked,R,G,100,Cache,Work,[](Vec2,Vec2){return false;}));Check(Blocked.Failed&&!Cache.Deferred);
 // Two actual A* callers compete after placement; totals include that admission.
 Work={};Port P2;Place(6,Bodies,13,47,120,P2,Published,F,Work);
 const auto S=RuntimePortReview::ClipSteps(119.95,1.08,.45,1.55,90,.7);
 ActualHorizonReview::Planner A({0,0},{600,0},S,{},{}),B({0,120},{600,120},S,{},{});
 A.Pump(Work,{},Free);B.Pump(Work,{},Free);
 Check(Work.Calls<=2&&Work.Expanded<=96&&Work.Queries<=512&&Work.Queries>=111);
 std::cout<<"budget checks="<<Checks<<" failures="<<Failures<<"\n";return Failures?1:0;
}
