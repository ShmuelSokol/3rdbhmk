#pragma once
#include "../SessionBridge.h"
#include <algorithm>

namespace MikdashOnline::Receiver04 {
// Opaque native incarnation identifiers, minted by the owned controller hook.
// Never deserialize controller/pawn identities from a network message.
struct Context {
    uint64_t controller=0,pawn=0,generation=0;
    bool operator==(const Context& B)const{return controller==B.controller&&pawn==B.pawn&&generation==B.generation;}
    bool Valid()const{return controller&&pawn&&generation;}
};
enum class Outcome { Applied, NoOp, Rejected, Unknown };
struct Consumption {
    uint64_t sequence=0,generation=0;
    Outcome outcome=Outcome::Unknown;
    double authorized_at=0; // semantic authorization instant, NOT physical completion
};

// One command mailbox, one held movement value, one result. No UPlayerInput,
// AddMovementInput, shared key/axis accumulator, queue, thread or socket.
class SemanticMailbox {
    std::function<double()> Clock;
    const double SessionEnd;
    Context Bound;
    Packet Pending;
    bool Queued=false,HasResult=false,Dead=false;
    double Last=-1,Accept=0,ResponseEnd=0,HeldEnd=0,HeldX=0,HeldY=0,AuthorizationAt=0;
    uint64_t Sequence=0,Epoch=0;
    Consumption Result;
    double Now(){
        const double N=Clock();
        if(!std::isfinite(N)||N<0||N<Last||N>1099511627776.0){Clear();Dead=true;return -1;}
        Last=N;return N;
    }
    bool Fresh(const Context& C,double N){
        if(Dead||N<0||N>=SessionEnd||!(C==Bound)||!C.Valid()){Clear();return false;}
        return true;
    }
    bool PendingFresh(const Context& C,double N){
        if(!Fresh(C,N)||!Queued)return false;
        if(N>=ResponseEnd){Clear();return false;}
        return true;
    }
    void Complete(Outcome O,double Before,uint64_t ExpectedSequence,Context ExpectedContext,uint64_t ExpectedEpoch){
        const double After=Now();
        if(Epoch!=ExpectedEpoch||!(Bound==ExpectedContext)||!Queued||Pending.sequence!=ExpectedSequence){Clear();return;}
        Result={ExpectedSequence,ExpectedContext.generation,O,AuthorizationAt};
        Queued=false;Pending=Packet();
        if(After<0||After>=ResponseEnd||After>=SessionEnd){
            Clear(); // unknown outcome: no ACK and NEVER automatic replay
            return;
        }
        HasResult=true;
    }
public:
    struct Fence { Context context; uint64_t epoch; double until; };
    SemanticMailbox(double End,std::function<double()> C):Clock(C),SessionEnd(End){
        const double N=Now();Dead=N<0||!std::isfinite(End)||End<=N||End-N>86400;
    }
    // Context replacement clears pending, held and completed remote state. A
    // reconnect/pawn switch requires a new generation, never pointer equality alone.
    bool Bind(Context C){
        Clear();
        if(Dead||!C.Valid()||C.generation<=Bound.generation||Now()>=SessionEnd)return false;
        Bound=C;return true;
    }
    void Clear(){++Epoch;Queued=false;HasResult=false;Pending=Packet();HeldX=HeldY=HeldEnd=0;}
    void Invalidate(){Clear();Dead=true;}
    void PauseMotion(){
        HeldX=HeldY=HeldEnd=0;
        if(Queued&&(Pending.action=="move"||Pending.action=="look"))Clear();
    }
    Fence CurrentFence()const{return {Bound,Epoch,std::min(SessionEnd,Queued?ResponseEnd:HeldEnd)};}
    Fence CurrentMovementFence()const{
        double Until=std::min(SessionEnd,HeldEnd);
        if(Queued&&Pending.action=="move")Until=std::min(Until,ResponseEnd);
        return {Bound,Epoch,Until}; // a queued look/button can NEVER renew movement
    }
    bool Revalidate(const Fence& F){
        const double N=Now();
        const bool Good=F.epoch==Epoch&&F.context==Bound&&Fresh(F.context,N)&&N<F.until;
        if(Good)AuthorizationAt=N;
        return Good;
    }
    bool Submit(const Packet& P,Context C,double AcceptedAt){
        const double N=Now();
        if(!Fresh(C,N)||Queued||HasResult||P.operation!="input"||P.sequence<=Sequence||
           P.sequence>9007199254740991ULL||!std::isfinite(AcceptedAt)||AcceptedAt<0||AcceptedAt>N||
           N-AcceptedAt>=0.5||!std::isfinite(P.x)||!std::isfinite(P.y)||std::abs(P.x)>1||std::abs(P.y)>1)return false;
        const bool Axis=P.action=="move"||P.action=="look";
        if(!Axis&&(!(P.action=="interact"||P.action=="pause"||P.action=="mute")||P.x!=0||P.y!=0))return false;
        Sequence=P.sequence;Accept=AcceptedAt;ResponseEnd=std::min(SessionEnd,Accept+0.5);
        Pending=P;Queued=true;return true; // deliberately no Consumption result
    }
    // Call from PostProcessInput, including paused ticks. Action must return an
    // explicit outcome; calling a void handler and blindly returning Applied is
    // not an implementation of this contract. Fresh check is at action dispatch.
    template<class Action> void PostProcessInput(Context C,bool Paused,Action Consume){
        const double N=Now();
        AuthorizationAt=N;
        if(!Fresh(C,N))return;
        if(Paused){
            HeldX=HeldY=HeldEnd=0;
            if(Queued&&(Pending.action=="move"||Pending.action=="look")){
                if(PendingFresh(C,N))Complete(Outcome::Rejected,N,Pending.sequence,Bound,Epoch);
                return;
            }
        }
        if(!PendingFresh(C,N))return;
        if(Pending.action=="move"||Pending.action=="look")return;
        if(Paused&&Pending.action=="interact"){Complete(Outcome::Rejected,N,Pending.sequence,Bound,Epoch);return;}
        // Handler executes here. If it stalls past the response deadline, its
        // effect is unknown to the caller; Complete will suppress the ACK.
        const auto S=Pending.sequence,E=Epoch;const Context B=Bound;const auto A=Pending.action;
        const Outcome O=Consume(A,N);Complete(O,N,S,B,E);
    }
    // UpdateRotation: apply this delta exactly once at the rotation consumer.
    // Callback must consume directly, not AddYawInput/another deferred accumulator.
    template<class Look> void UpdateRotation(Context C,bool Paused,Look Consume){
        const double N=Now();
        AuthorizationAt=N;
        if(!PendingFresh(C,N)||Pending.action!="look")return;
        if(Paused){HeldX=HeldY=HeldEnd=0;Complete(Outcome::Rejected,N,Pending.sequence,Bound,Epoch);return;}
        const auto S=Pending.sequence,E=Epoch;const Context B=Bound;
        const Outcome O=Consume(Pending.x,Pending.y,N);Complete(O,N,S,B,E);
    }
    // Actual movement evaluation boundary: ControlledCharacterMove for walker,
    // ApplyControlInputToVelocity for dove. ConsumeInputVector alone is NOT proof.
    // Callback merges only this fresh contribution with its separately consumed
    // local vector. It must not enqueue with AddMovementInput. No remote state is
    // ever added to the pawn's shared pending vector.
    template<class Move> void ConsumeMovement(Context C,bool Paused,Move Consume){
        const double N=Now();
        AuthorizationAt=N;
        if(!Fresh(C,N))return;
        if(Paused){
            HeldX=HeldY=HeldEnd=0;
            if(Queued&&(Pending.action=="move"||Pending.action=="look")&&PendingFresh(C,N))Complete(Outcome::Rejected,N,Pending.sequence,Bound,Epoch);
            return;
        }
        const bool New=Queued&&Pending.action=="move";
        if(New){
            if(!PendingFresh(C,N))return;
            HeldX=Pending.x;HeldY=Pending.y;
            HeldEnd=std::min(SessionEnd,Accept+2); // immutable from original accept
        }
        if(N>=HeldEnd){HeldX=HeldY=HeldEnd=0;return;}
        if(New||HeldX!=0||HeldY!=0){
            const auto S=Pending.sequence,E=Epoch;const Context B=Bound;
            const Outcome O=Consume(HeldX,HeldY,N);
            if(Epoch!=E||!(Bound==B)){Clear();return;}
            if(O!=Outcome::Applied&&O!=Outcome::NoOp)HeldX=HeldY=HeldEnd=0;
            if(New)Complete(O,N,S,B,E);
        }
    }
    bool Take(Consumption& Out){
        const double N=Now();
        if(!HasResult||Dead||N<0||N>=ResponseEnd||N>=SessionEnd){
            if(N<0||N>=SessionEnd||N>=ResponseEnd)Clear();
            return false;
        }
        Out=Result;HasResult=false;return true;
    }
};
}
