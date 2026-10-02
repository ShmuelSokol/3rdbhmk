#pragma once
#include "CrowdGroupMath.h"
namespace PlacedActualHorizonStudy {
// Bounded six-entry journal, not a copy of the population-sized index.
// SpatialIndex::Insert itself is non-mutating on false (audited copied source).
// The injectable post-insert hook may fail AFTER writing: rollback includes it.
// Only successful inserts enter the journal, preserving pre-existing occupants.
template<class AfterInsert> bool CommitCohort(MikdashCrowdGroups::SpatialIndex& Index,
 int First,const MikdashCrowd::Vec2* Points,int Count,AfterInsert&& Accept) {
 if(!Points||Count<1||Count>MikdashCrowdGroups::MaxMembers)return false;
 int Inserted=0;
 for(int I=0;I<Count;++I) {
   if(!Index.Insert(First+I,Points[I]))break;
   ++Inserted;
   if(!Accept(I)){
     for(int J=Inserted-1;J>=0;--J)Index.Remove(First+J,Points[J]);
     return false;
   }
 }
 if(Inserted==Count)return true;
 for(int J=Inserted-1;J>=0;--J)Index.Remove(First+J,Points[J]);
 return false;
}
}
