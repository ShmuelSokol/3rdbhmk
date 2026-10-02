#pragma once
#include "RotatingEnvelope.h"
// Offline proposed spawn/formation adapter. Never repairs an occupied snapshot.
namespace BodyAwarePlacementStudy {
using namespace MikdashCrowd; using namespace MikdashCrowdGroups;
using RotatingEnvelopeStudy::Body;
enum class Result { Placed, UnknownBody, FormationUnsupported, AttemptsExhausted };
struct Formation { Vec2 Local[MaxMembers]{}; double Spacing=0; int Count=0; };
inline bool ValidBody(Body B) {
    return B.Known && std::isfinite(B.Radius) && B.Radius>0 &&
        std::isfinite(B.MinZ) && std::isfinite(B.MaxZ) && B.MaxZ>=B.MinZ;
}
inline Result Layout(int Count,const Body* Bodies,uint32_t Seed,uint32_t Identity,
                     double Requested,Formation& Out) {
    if(!Bodies||Count<1||Count>MaxMembers||!std::isfinite(Requested))return Result::FormationUnsupported;
    for(int I=0;I<Count;++I)if(!ValidBody(Bodies[I]))return Result::UnknownBody;
    double Pitch=std::max(110.,std::min(180.,Requested));
    // Offset is linear in pitch within the original [110,180] bounds, including jitter.
    // Solve pair constraints once, rather than sweeping spacing parameters.
    for(int I=0;I<Count;++I)for(int J=0;J<I;++J) {
        const double Unit=Length(Offset(I,Seed,Identity,110)-Offset(J,Seed,Identity,110))/110.;
        if(Unit<=0)return Result::FormationUnsupported;
        const double Needed=std::max(80.,Bodies[I].Radius+Bodies[J].Radius)/Unit;
        if(Needed>Pitch)Pitch=std::nextafter(Needed,INFINITY);
    }
    if(Pitch>180)return Result::FormationUnsupported;
    Formation Candidate;Candidate.Count=Count;Candidate.Spacing=Pitch;
    for(int I=0;I<Count;++I)Candidate.Local[I]=Offset(I,Seed,Identity,Pitch);
    Out=Candidate;return Result::Placed;
}
// Port requirements deliberately expose actual geometry, not a radius<=margin proxy:
// Sample supplies bounded candidate anchors/headings. Ground resolves actual per-root Z
// and enforces existing residual gates. RootAndLink retains existing zone/protected gates.
// HeldCapsuleSweep must overlap each root and sweep leader-to-member using the supplied
// conservative posed body envelope, actual ground endpoints and native world geometry.
// CommittedPeers checks common-time live swept reservations plus indefinite endpoint holds.
// CommitBatch is atomic (or rolls back every insertion), and publishes no partial group.
template<class Port> Result Place(int Count,const Body* Bodies,uint32_t Seed,uint32_t Identity,
    double Requested,int Attempts,Port& P,Vec2* Published,Formation& PublishedLayout) {
    Formation F;const Result R=Layout(Count,Bodies,Seed,Identity,Requested,F);
    if(R!=Result::Placed)return R;
    for(int Attempt=0;Attempt<Attempts;++Attempt) {
        Vec2 Anchor,Points[MaxMembers];double Heading=0,Z[MaxMembers]{};
        if(!P.Sample(Attempt,Anchor,Heading)||!Finite(Anchor)||!std::isfinite(Heading))continue;
        bool Okay=true;
        for(int I=0;I<Count&&Okay;++I) {
            Points[I]=Anchor+WorldOffset(F.Local[I],Heading);
            Okay=P.Ground(I,Points[I],Z[I])&&std::isfinite(Z[I])&&
                P.RootAndLink(Points[0],Points[I])&&
                P.HeldCapsuleSweep(Points[0],Z[0],Points[I],Z[I],Bodies[I])&&
                P.CommittedPeers(Points[I],Z[I],Bodies[I]);
            for(int J=0;J<I&&Okay;++J)
                Okay=RotatingEnvelopeStudy::Pair({Points[I],Points[I],0,0},Bodies[I],
                    {Points[J],Points[J],0,0},Bodies[J],0);
        }
        if(!Okay||!P.CommitBatch(Points,Z,Bodies,Count))continue;
        for(int I=0;I<Count;++I)Published[I]=Points[I];
        PublishedLayout=F;return Result::Placed;
    }
    return Result::AttemptsExhausted;
}
}
