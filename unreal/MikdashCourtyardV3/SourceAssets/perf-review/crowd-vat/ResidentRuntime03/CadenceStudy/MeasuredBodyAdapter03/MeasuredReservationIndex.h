#pragma once
#include "MeasuredProfiles.h"
#include "baseline/RotatingEnvelope.h"
#include <map>
#include <functional>
#include <string>
#include <utility>

namespace MeasuredBodyStudy {
using MikdashCrowd::Vec2;
using MikdashCrowd::Length;
using MikdashCrowdGroups::MotionReservation;
using RotatingEnvelopeStudy::Body;
struct Binding {
    int Id=-1,ProfileId=-1;uint64_t Incarnation=0;
    double Scale=0;Body Bounds{};std::string EvidenceHash;
};
inline Binding Measured(int Id,uint64_t Incarnation,int ProfileId) {
    if(ProfileId<0||ProfileId>=6)return {};
    const auto& P=Profiles[ProfileId];return {Id,ProfileId,Incarnation,P.Scale,{P.Radius,P.MinZ,P.MaxZ,true},Evidence};
}
inline bool Same(const Binding& A,const Binding& B) {
    return A.Id==B.Id&&A.Incarnation==B.Incarnation&&A.ProfileId==B.ProfileId&&A.Scale==B.Scale&&
        A.Bounds.Known==B.Bounds.Known&&A.Bounds.Radius==B.Bounds.Radius&&A.Bounds.MinZ==B.Bounds.MinZ&&
        A.Bounds.MaxZ==B.Bounds.MaxZ&&A.EvidenceHash==B.EvidenceHash;
}
inline bool Valid(const Binding& A){return A.Id>=0&&A.ProfileId>=0&&A.ProfileId<6&&Same(A,Measured(A.Id,A.Incarnation,A.ProfileId));}
struct Request {
    uint64_t Serial=0,WorldVersion=0;Binding Identity;MotionReservation Motion;
    double FromZ=0,ToZ=0;
    double CapsuleCenterOffset()const{return (Identity.Bounds.MinZ+Identity.Bounds.MaxZ)*.5;}
    double CapsuleHalfHeight()const{return (Identity.Bounds.MaxZ-Identity.Bounds.MinZ)*.5+Identity.Bounds.Radius;}
};
struct Hit {uint64_t Primitive=0;int Face=-1;bool CertifiedSupportContact=false;};
struct WorldEvidence {
    uint64_t RequestSerial=0,WorldVersion=0,SupportPrimitive=0;int SupportFace=-1;
    bool IndependentSupport=false,FullSweptFootprint=false,StationaryOverlap=false,PathSweep=false,Complete=false;
    std::string ContactPolicy;std::vector<Hit> Hits;
};
enum class Refusal {None,Identity,Busy,Motion,Capacity,Budget,Peer,Ground,Support,ObstacleUnknown,PotentialObstacle,Invalidated,Commit};
// Actual UE implementation is deliberately absent. A source fixture supplies
// geometry doubles. Complete support cannot be inferred from signed MinZ alone.
struct WorldPort {
    virtual ~WorldPort()=default;
    virtual uint64_t Version()const=0;
    virtual uint64_t BindingVersion()const=0; // any existing rendered identity/scale/bounds mutation
    virtual bool Ground(Vec2,double,double&)=0;
    virtual WorldEvidence Check(const Request&)=0;
    virtual bool BeforeCommit(const Request&){return true;}
};

class ReservationIndex {
    using Cell=std::pair<int64_t,int64_t>;
    struct Entry {Binding Identity;Vec2 Anchor;double GroundZ=0;MotionReservation Motion;bool Reserved=false;};
    std::map<int,Entry> Entries;
    std::map<Cell,std::vector<int>> Cells;
    std::array<unsigned,6> Counts{};
    WorldPort& World;std::function<Binding(int)> Live;
    uint64_t Epoch=0,Serial=0,BindingStamp=0;bool Invalid=false,Evaluating=false;
    Refusal Last=Refusal::None;
    bool Fail(Refusal R){Last=R;return false;}
    static bool Safe(Vec2 P){return MikdashCrowd::Finite(P)&&std::abs(P.X)<1e10&&std::abs(P.Y)<1e10;}
    static Cell Key(Vec2 P){return {static_cast<int64_t>(std::floor(P.X/200)),static_cast<int64_t>(std::floor(P.Y/200))};}
    bool Matches(int Id) {
        if(World.BindingVersion()!=BindingStamp){Invalidate();return false;}
        auto I=Entries.find(Id);if(I==Entries.end()||Invalid)return false;
        if(!Same(I->second.Identity,Live(Id))){Invalidate();return false;}return true;
    }
    bool Evaluate(int Id,Vec2 From,Vec2 To,double Now,double Duration,Request& Q) {
        Last=Refusal::None;
        if(Evaluating)return Fail(Refusal::Busy);
        if(!Matches(Id))return Fail(Refusal::Identity);
        const Entry E=Entries.at(Id); // never retain iterators across user callbacks
        if(!Safe(From)||!Safe(To)||!std::isfinite(Now)||!std::isfinite(Duration)||Duration<=0||
            !std::isfinite(Now+Duration)||Length(To-From)>100||Length(E.Anchor-From)>1e-6||E.Reserved)return Fail(Refusal::Motion);
        const double Reach=QueryReach(Id);
        const auto Lo=Key({std::min(From.X,To.X)-Reach,std::min(From.Y,To.Y)-Reach});
        const auto Hi=Key({std::max(From.X,To.X)+Reach,std::max(From.Y,To.Y)+Reach});
        if((Hi.first-Lo.first+1)*(Hi.second-Lo.second+1)>16)return Fail(Refusal::Budget);
        const MotionReservation Candidate{From,To,Now,Now+Duration};
        for(auto X=Lo.first;X<=Hi.first;++X)for(auto Y=Lo.second;Y<=Hi.second;++Y) {
            auto C=Cells.find({X,Y});if(C==Cells.end())continue;
            for(int PeerId:C->second){if(PeerId==Id)continue;
                if(!Matches(PeerId))return Fail(Refusal::Identity);
                const auto& P=Entries.at(PeerId);
                const auto M=P.Reserved?P.Motion:MotionReservation{P.Anchor,P.Anchor,Now,Now};
                if(MikdashCrowdGroups::ReservationDistance(Candidate,M,Now)<std::max(80.,E.Identity.Bounds.Radius+P.Identity.Bounds.Radius))return Fail(Refusal::Peer);
            }
        }
        const auto Version=World.Version(),Stamp=Epoch;
        struct Guard {bool& Flag;Guard(bool& F):Flag(F){Flag=true;}~Guard(){Flag=false;}} Guard(Evaluating);
        double Z0=0,Z1=0;
        if(!World.Ground(From,Now,Z0)||!World.Ground(To,Now+Duration,Z1)||!std::isfinite(Z0)||!std::isfinite(Z1)||std::abs(Z0-E.GroundZ)>1e-6)return Fail(Refusal::Ground);
        Q={++Serial,Version,E.Identity,Candidate,Z0,Z1};
        const auto Proof=World.Check(Q);
        if(Stamp!=Epoch||Version!=World.Version()||!Matches(Id))return Fail(Refusal::Invalidated);
        if(Proof.RequestSerial!=Q.Serial||Proof.WorldVersion!=Version||!Proof.IndependentSupport||!Proof.FullSweptFootprint||
            !Proof.SupportPrimitive||Proof.SupportFace<0||Proof.ContactPolicy.empty())return Fail(Refusal::Support);
        if(!Proof.StationaryOverlap||!Proof.PathSweep||!Proof.Complete)return Fail(Refusal::ObstacleUnknown);
        for(const auto& H:Proof.Hits)if(H.Primitive!=Proof.SupportPrimitive||H.Face!=Proof.SupportFace||!H.CertifiedSupportContact)return Fail(Refusal::PotentialObstacle);
        Last=Refusal::None;return true;
    }
public:
    struct BatchMove {int Id;Vec2 From,To;double Now,Horizon;};
    ReservationIndex(WorldPort& W,std::function<Binding(int)> L):World(W),Live(std::move(L)),BindingStamp(W.BindingVersion()){}
    Refusal Reason()const{return Last;}
    uint64_t Revision()const{return Epoch;}
    bool Blocked()const{return Invalid;}
    void Invalidate(){Invalid=true;++Epoch;} // retained occupancy; no clear/remove escape
    Body Envelope(int Id)const{return Entries.at(Id).Identity.Bounds;}
    MotionReservation Motion(int Id)const{return Entries.at(Id).Motion;}
    Vec2 Anchor(int Id)const{return Entries.at(Id).Anchor;}
    bool Reserved(int Id)const{return Entries.at(Id).Reserved;}
    size_t Size()const{return Entries.size();}
    size_t StorageCells()const{return Cells.size();}
    double QueryReach(int Id)const {
        const auto& Own=Entries.at(Id).Identity;double Peer=0;
        for(int P=0;P<6;++P)if(Counts[P]>(P==Own.ProfileId?1u:0u))Peer=std::max(Peer,Profiles[P].Radius);
        return std::max(80.,Own.Bounds.Radius+Peer)+100.;
    }
    // Registers an existing scene snapshot, NOT checked spawn. Immutable identity.
    bool Register(const Binding& B,Vec2 P,double Z) {
        if(Evaluating)return Fail(Refusal::Busy);
        if(World.BindingVersion()!=BindingStamp){Invalidate();return Fail(Refusal::Identity);}
        if(Invalid||!Valid(B)||!Same(B,Live(B.Id))||Entries.count(B.Id)||!Safe(P)||!std::isfinite(Z))return Fail(Refusal::Identity);
        const auto K=Key(P);auto& C=Cells[K];if(C.size()>=64)return Fail(Refusal::Capacity);
        try {
            C.reserve(64); // allocation before occupancy mutation
            Entries.emplace(B.Id,Entry{B,P,Z,{P,P,0,0},false});
        }catch(...){if(C.empty())Cells.erase(K);throw;}
        C.push_back(B.Id);++Counts[B.ProfileId];++Epoch;Last=Refusal::None;return true;
    }
    bool CanReserve(int Id,Vec2 A,Vec2 B,double T,double H){Request Q;return Evaluate(Id,A,B,T,H,Q);}
    bool Reserve(int Id,Vec2 A,Vec2 B,double T,double H) {
        Request Q;if(!Evaluate(Id,A,B,T,H,Q))return false;
        const auto Stamp=Epoch;
        struct Guard {bool& F;Guard(bool& V):F(V){F=true;}~Guard(){F=false;}} Guard(Evaluating);
        if(!World.BeforeCommit(Q))return Fail(Refusal::Commit);
        if(Stamp!=Epoch||Q.WorldVersion!=World.Version()||!Matches(Id))return Fail(Refusal::Invalidated);
        auto& E=Entries.at(Id);E.Motion=Q.Motion;E.Reserved=true;E.GroundZ=Q.ToZ;++Epoch;Last=Refusal::None;return true;
    }
    // At most6 already registered cohort members. No writes until every gate and
    // pair passes; application of POD motion fields cannot allocate or callback.
    bool ReserveBatch(const BatchMove* Moves,int Count) {
        if(!Moves||Count<1||Count>6||Evaluating)return Fail(Refusal::Busy);
        const auto Stamp=Epoch,Version=World.Version();std::array<Request,6> Q;
        for(int I=0;I<Count;++I){
            for(int J=0;J<I;++J)if(Moves[I].Id==Moves[J].Id||Moves[I].Now!=Moves[J].Now)return Fail(Refusal::Motion);
            const auto& M=Moves[I];if(!Evaluate(M.Id,M.From,M.To,M.Now,M.Horizon,Q[I]))return false;
            if(Stamp!=Epoch||Version!=World.Version())return Fail(Refusal::Invalidated);
            for(int J=0;J<I;++J)if(MikdashCrowdGroups::ReservationDistance(Q[I].Motion,Q[J].Motion,M.Now)<
                std::max(80.,Q[I].Identity.Bounds.Radius+Q[J].Identity.Bounds.Radius))return Fail(Refusal::Peer);
        }
        struct Guard {bool& F;Guard(bool& V):F(V){F=true;}~Guard(){F=false;}} Guard(Evaluating);
        for(int I=0;I<Count;++I)if(!World.BeforeCommit(Q[I]))return Fail(Refusal::Commit);
        if(Stamp!=Epoch||Version!=World.Version())return Fail(Refusal::Invalidated);
        for(int I=0;I<Count;++I)if(!Matches(Q[I].Identity.Id))return Fail(Refusal::Invalidated);
        for(int I=0;I<Count;++I){auto& E=Entries.at(Q[I].Identity.Id);E.Motion=Q[I].Motion;E.Reserved=true;E.GroundZ=Q[I].ToZ;}
        ++Epoch;Last=Refusal::None;return true;
    }
    // Drain/arrival of an already admitted segment only. No new collision permission.
    bool Relocate(int Id,Vec2 From,Vec2 To,double Now) {
        if(Evaluating)return Fail(Refusal::Busy);
        if(!Matches(Id))return Fail(Refusal::Identity);
        auto& E=Entries.at(Id);
        if(!Safe(From)||!Safe(To)||!std::isfinite(Now)||Length(E.Anchor-From)>1e-6||
            (E.Reserved?(Now<E.Motion.End||Length(E.Motion.To-To)>1e-6):Length(From-To)>1e-6))return Fail(Refusal::Motion);
        // Caller From is tolerance-checked, not the storage identity: it can
        // round into an adjacent cell. Validate authoritative membership first.
        const auto Old=Key(E.Anchor),New=Key(To);
        auto Was=Cells.find(Old);
        if(Was==Cells.end()||std::count(Was->second.begin(),Was->second.end(),Id)!=1)
            return Fail(Refusal::Invalidated);
        const auto At=std::find(Was->second.begin(),Was->second.end(),Id);
        if(Old!=New){auto& C=Cells[New];if(C.size()>=64)return Fail(Refusal::Capacity);
            try{C.reserve(64);}catch(...){if(C.empty())Cells.erase(New);throw;}
            // std::map insertion preserves Was and its vector iterators.
            C.push_back(Id);Was->second.erase(At);
            if(Was->second.empty())Cells.erase(Was); // prune only AFTER successful destination insertion
        }
        E.Anchor=To;E.Motion={To,To,Now,Now};E.Reserved=false;++Epoch;Last=Refusal::None;return true;
    }
};
}
