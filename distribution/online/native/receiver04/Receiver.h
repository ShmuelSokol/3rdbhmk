#pragma once
#include "Authority.h"
#include "../receiver03/FrameBuffer.h"
#include "Sockets.h"
#include "SocketSubsystem.h"

namespace MikdashOnline::Receiver04 {
class Receiver {
    Authority& Service;
    ISocketSubsystem* Sockets=nullptr;
    FSocket* Listener=nullptr;
    FSocket* Peer=nullptr;
    bool Stopping=false,ListenerPoisoned=false,PeerPoisoned=false,Authenticated=false;
    Receiver03::FrameBuffer Input;
    TArray<uint8> Output;
    int32 Sent=0,AcceptedCount=0;
    double AcceptedAt=0,RateStart=0;
    bool CloseSocket(FSocket*& Socket,bool& Poisoned);
    bool Drop(bool AbortPending);
public:
    explicit Receiver(Authority& A):Service(A){}
    ~Receiver(){Shutdown();}
    bool Start(int32 Port);
    void Tick();
    bool Shutdown();
};
}
