#include "CommitGates.h"
#include "RouteContinuityStudy.h"
#include <iostream>
using namespace MikdashCrowd;using namespace MikdashCrowdGroups;
int Checks=0,Failures=0;void Check(bool B){++Checks;if(!B)++Failures;}
struct Agent {AngularWalkingStudy::ScheduledTurn Angular;Vec2 Anchor{};double AnchorTime=0,Yaw=0;MotionReservation Motion{};bool Walking=false;};
struct RejectIndex {
 SpatialIndex Real;bool RejectRelocate=false,RejectReserve=false;int Relocates=0,Reserves=0;
 bool Relocate(int Id,Vec2 A,Vec2 B,double T){++Relocates;return !RejectRelocate&&Real.Relocate(Id,A,B,T);}
 bool Reserve(int Id,Vec2 A,Vec2 B,double T,double H){++Reserves;return !RejectReserve&&Real.Reserve(Id,A,B,T,H);}
};
int main(){
 for(bool Angular:{false,true}){
   Agent A;RejectIndex Index;CadenceRecoveryStudy::Episode Recovery;Check(Index.Real.Insert(7,{0,0}));
   A.Angular.Core.Current.Envelope={50,0,190,true};
   if(Angular){
     Check(!A.Angular.Align(180,0,A.Motion,[&](Vec2,RotatingEnvelopeStudy::Body){
       const double End=2.001;Check(Index.Real.Reserve(7,{0,0},{0,0},0,End));A.Motion={{0,0},{0,0},0,End};return true;
     }));
   }else{
     A.Walking=true;A.Motion={{0,0},{50,0},0,1};Check(Index.Real.Reserve(7,{0,0},{50,0},0,1));
     Recovery.Members[0].Target={50,0};Recovery.Reserved(0);
   }
   Index.RejectRelocate=true;const auto Before=A.Angular.Core;
   const auto Motion=A.Motion;const int Steps=Recovery.Steps,Revision=Recovery.Revision;
   for(int Repeat=0;Repeat<3;++Repeat){
     Check(CommitGatesStudy::CommitArrival(A,Recovery,Index,7,0,1,3+Repeat,true)==CommitGatesStudy::Arrival::Refused);
     Check(A.Anchor.X==0&&A.AnchorTime==0&&A.Yaw==0);
     Check(A.Motion.End==Motion.End&&A.Motion.To.X==Motion.To.X&&A.Walking==!Angular);
     Check(A.Angular.Core.Current.TurnDeltaDegrees==Before.Current.TurnDeltaDegrees&&A.Angular.Commits==0);
     Check(Recovery.Steps==Steps&&Recovery.Revision==Revision);
     Check(!Index.Real.CanReserve(7,A.Anchor,A.Anchor,5,1));
   }
   Index.RejectRelocate=false;
   Check(CommitGatesStudy::CommitArrival(A,Recovery,Index,7,0,1,6,true)==CommitGatesStudy::Arrival::Committed);
   Check(A.Anchor.X==(Angular?0:50)&&A.Motion.End==6);
   Check(Angular?(std::abs(WrapDegrees(A.Yaw-180))<1e-8&&A.Angular.Commits==1):Recovery.Steps==1);
 }
 // A successful fresh CanReserve is not permission to publish until Reserve succeeds.
 for(bool Recovering:{false,true}){
   Agent A;RejectIndex Index;Check(Index.Real.Insert(7,{0,0}));Index.RejectReserve=true;
   CadenceRecoveryStudy::Episode Recovery;int EndpointRevision=9,JourneyUpdates=0;
   for(int Repeat=0;Repeat<3;++Repeat){
     Check(Index.Real.CanReserve(7,{0,0},{50,0},1,1));
     Check(!CommitGatesStudy::ReserveWalk(A,Index,7,{0,0},{50,0},1,1,[&](){
       ++EndpointRevision;if(Recovering)Recovery.Reserved(0);else ++JourneyUpdates;
     }));
     Check(!A.Walking&&A.Motion.End==0&&A.Motion.To.X==0);
     Check(EndpointRevision==9&&!Recovery.WasMoving(0)&&JourneyUpdates==0);
     Check(Index.Real.CanReserve(7,{0,0},{50,0},1,1));
   }
   Index.RejectReserve=false;
   Check(CommitGatesStudy::ReserveWalk(A,Index,7,{0,0},{50,0},1,1,[&](){++EndpointRevision;if(Recovering)Recovery.Reserved(0);else ++JourneyUpdates;}));
   Check(A.Walking&&A.Motion.To.X==50&&A.Motion.End==2&&EndpointRevision==10);
   Check(Recovering?Recovery.WasMoving(0):JourneyUpdates==1);
 }
 // Turn Begin itself also refuses a rejected hold reservation without publishing a turn.
 Agent Turn;Turn.Angular.Core.Current.Envelope={50,0,190,true};RejectIndex Index;Check(Index.Real.Insert(7,{0,0}));Index.RejectReserve=true;
 Check(!Turn.Angular.Align(90,0,Turn.Motion,[&](Vec2,RotatingEnvelopeStudy::Body){return Index.Reserve(7,{0,0},{0,0},0,1.1);}));
 Check(!Turn.Angular.Held&&Turn.Angular.Starts==0&&Turn.Angular.Core.Current.TurnDeltaDegrees==0);
 std::cout<<"commit gate checks="<<Checks<<" failures="<<Failures<<"\n";return Failures?1:0;
}
