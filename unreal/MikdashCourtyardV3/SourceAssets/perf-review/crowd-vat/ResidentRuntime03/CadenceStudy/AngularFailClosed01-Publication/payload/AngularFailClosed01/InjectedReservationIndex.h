#pragma once
#include "CrowdGroupMath.h"
namespace CommitGatesStudy {
struct ReservationIndex:MikdashCrowdGroups::SpatialIndex {
 bool RefuseRelocation=false,RefuseWalkingReservation=false;
 int WalkingRefusalId=-1;
 int RelocationRefusals=0,ReservationRefusals=0;
 bool Relocate(int Id,MikdashCrowd::Vec2 A,MikdashCrowd::Vec2 B,double Now){
   if(RefuseRelocation){RefuseRelocation=false;++RelocationRefusals;return false;}
   return SpatialIndex::Relocate(Id,A,B,Now);
 }
 bool Reserve(int Id,MikdashCrowd::Vec2 A,MikdashCrowd::Vec2 B,double Now,double Horizon){
   if(RefuseWalkingReservation&&Id==WalkingRefusalId&&MikdashCrowd::Length(B-A)>1e-8&&CanReserve(Id,A,B,Now,Horizon)){
     RefuseWalkingReservation=false;++ReservationRefusals;return false;
   }
   return SpatialIndex::Reserve(Id,A,B,Now,Horizon);
 }
};
}
