#pragma once
#include "../receiver03/Wire.h"
#include "SemanticMailbox.h"

namespace MikdashOnline::Receiver04 {
// New receiver authority. Reuses ONLY frozen parser/HMAC/QPC, not enqueue-ACK
// Service or ControllerSink. Construction does not start a listener or streamer.
class Authority {
    Owner Identity;
    const double Deadline;
    uint8 Key[32];
    TFunction<double()> Clock;
    double Last=-1,ReplyUntil=0;
    Context NativeContext;
    bool Opened=false,Closed=false,Awaiting=false;
    SemanticMailbox Mailbox;
    std::string Connection;
    uint64_t Sequence=0,Generation=0;
    Packet Waiting;
    double Now();
    bool Encode(const Packet& P,const Consumption& C,TArray<uint8>& Out);
public:
    // C/P are opaque native incarnation IDs with weak-object ownership checked
    // by each consumer hook. Neither may come from a request.
    Authority(const Receiver03::Bootstrap& B,uint64_t C,uint64_t P,TFunction<double()> Clock);
    ~Authority(){FMemory::Memzero(Key,sizeof(Key));}
    // Immediate reply only for lifecycle semantic state changes. Input returns
    // true with EMPTY reply and remains pending until the real consumer runs.
    bool Receive(const TArray<uint8>& Frame,double AcceptedAt,TArray<uint8>& Immediate);
    bool PollReply(TArray<uint8>& Out);
    void Maintain(); // every frame, including idle/no peer; closes at session expiry
    SemanticMailbox& Consumers(){return Mailbox;}
    Context BoundContext()const{return NativeContext;}
    void Abort(){Mailbox.Invalidate();Awaiting=false;Closed=true;Waiting=Packet();}
    bool IsClosed()const{return Closed;}
    bool IsAwaiting()const{return Awaiting;}
};
}
