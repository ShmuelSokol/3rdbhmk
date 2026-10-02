#pragma once
#include <cmath>
#include <cstdint>
namespace MikdashOnline::Flight01 {
// Dedicated receipt for a single dove toggle. Normal mailbox fences stay strict.
class Command final {
    uint64_t Controller=0,Pawn=0,Generation=0,Sequence=0;
    double End=0,Authorized=0,Last=-1;
    enum class Phase { Empty,Queued,Consuming,Ready,Dead } State=Phase::Empty;
    bool Transition=false,BranchArmed=false;
    bool Fresh(double N) {
        if(!std::isfinite(N)||N<0||N<Last||N>=End){State=Phase::Dead;return false;}
        Last=N;return true;
    }
public:
    bool Queue(uint64_t C,uint64_t P,uint64_t G,uint64_t S,double N,double Until) {
        if(State!=Phase::Empty||!C||!P||!G||!S||!std::isfinite(Until)||Until<=N||Until-N>0.5)return false;
        Controller=C;Pawn=P;Generation=G;Sequence=S;End=Until;Transition=false;BranchArmed=false;State=Phase::Queued;
        return Fresh(N);
    }
    bool Consume(uint64_t C,uint64_t P,uint64_t G,double N) {
        if(State!=Phase::Queued||C!=Controller||P!=Pawn||G!=Generation||!Fresh(N))return false;
        State=Phase::Consuming;Authorized=N;return true;
    }
    bool Fence(uint64_t C,uint64_t P,uint64_t G,double N) {
        if(State!=Phase::Consuming||Transition||C!=Controller||P!=Pawn||G!=Generation||!Fresh(N))return false;
        Authorized=N;BranchArmed=true;return true;
    }
    bool Begin(uint64_t C,uint64_t P,uint64_t G,double N) {
        if(!BranchArmed||State!=Phase::Consuming||Transition||C!=Controller||P!=Pawn||G!=Generation||!Fresh(N))return false;
        BranchArmed=false;Transition=true;return true;
    }
    bool Complete(uint64_t C,uint64_t P,uint64_t G,double N,bool ProvenOutcome) {
        if(State!=Phase::Consuming||!ProvenOutcome||!Fresh(N)||C!=Controller||
           P!=Pawn+(Transition?1:0)||G!=Generation+(Transition?1:0)) {State=Phase::Dead;return false;}
        State=Phase::Ready;return true;
    }
    bool Take(uint64_t S,uint64_t C,uint64_t P,uint64_t G,double N,double& At,bool& Handoff) {
        if(State!=Phase::Ready||S!=Sequence||C!=Controller||P!=Pawn+(Transition?1:0)||
           G!=Generation+(Transition?1:0)||!Fresh(N))return false;
        At=Authorized;Handoff=Transition;State=Phase::Empty;return true;
    }
    bool Consuming()const{return State==Phase::Consuming;}
    void Cancel(){State=Phase::Empty;Transition=false;BranchArmed=false;}
    void Abort(){State=Phase::Dead;}
};
}
