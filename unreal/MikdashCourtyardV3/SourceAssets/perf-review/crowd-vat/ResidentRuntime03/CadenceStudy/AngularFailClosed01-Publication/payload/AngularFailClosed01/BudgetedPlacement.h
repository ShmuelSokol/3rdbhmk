#pragma once
#include "BodyAwarePlacement.h"
#include "BoundedRoutePlanner.h"
namespace PlacedActualHorizonStudy {
using namespace BodyAwarePlacementStudy;
enum class PlacementStatus { Placed, Refused, Deferred };
template<class Port> PlacementStatus Place(int Count,const Body* Bodies,uint32_t Seed,uint32_t Identity,
 double Requested,Port& P,Vec2* Published,Formation& F,ActualHorizonReview::Budget& Work) {
    if(Count<1||Count>MaxMembers)return PlacementStatus::Refused;
    // One sampled attempt per admission. Reserve an upper bound of16 primitive
    // queries per member and each internal pair check; unused credit is not reused.
    // At maximum180cm pitch the farthest slot is<420cm: each of two link
    // validations uses at most6 subsegments; ground +2 external peers +insert
    // consume at most4 more. Ports with greater work must not use this bound.
    // Layout computation is O(MaxMembers^2), no world queries or grid expansions.
    const int Cost=16*Count+Count*(Count-1)/2;
    if(Work.Queries+Cost>512)return PlacementStatus::Deferred;
    Work.Queries+=Cost;
    return BodyAwarePlacementStudy::Place(Count,Bodies,Seed,Identity,Requested,1,P,Published,F)
        ==Result::Placed?PlacementStatus::Placed:PlacementStatus::Refused;
}
struct FormationCache {
    struct Entry {Vec2 A,B;bool Clear;};
    std::vector<Entry> Entries;bool Deferred=false;uint64_t Geometry=std::numeric_limits<uint64_t>::max();
    void ObserveGeometry(uint64_t Revision){if(Revision!=Geometry){Clear();Geometry=Revision;}}
    template<class Gate> bool Query(Vec2 A,Vec2 B,ActualHorizonReview::Budget& Work,Gate&& Allowed) {
        for(const auto& E:Entries)if(E.A.X==A.X&&E.A.Y==A.Y&&E.B.X==B.X&&E.B.Y==B.Y)return E.Clear;
        if(Entries.size()>=4096||!Work.Query()){Deferred=true;return false;}
        const bool Clear=Allowed(A,B);Entries.push_back({A,B,Clear});return Clear;
    }
    void Clear(){Entries.clear();Deferred=false;}
};
// Copy on planning update: exhaustion never publishes partial goals or Failed.
// Cache is valid only for the unchanged static formation world; caller clears on
// geometry change and successful update. Execution always uses fresh live gates.
template<class Travel,class Gate> bool Update(Travel& T,const Vec2* Roots,Vec2* Goals,double Lead,
 FormationCache& Cache,ActualHorizonReview::Budget& Work,Gate&& Allowed) {
    Cache.Deferred=false;Travel Next=T;Vec2 Candidate[MaxMembers];
    for(int I=0;I<T.Count;++I)Candidate[I]=Goals[I];
    const bool Okay=Next.Update(Roots,Candidate,Lead,[&](Vec2 A,Vec2 B){return Cache.Query(A,B,Work,Allowed);});
    if(Cache.Deferred)return false;
    T=std::move(Next);
    if(Okay)for(int I=0;I<T.Count;++I)Goals[I]=Candidate[I];
    Cache.Clear();return Okay;
}
}
