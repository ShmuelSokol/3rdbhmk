#pragma once
#include "Wire.h"
#include "Sockets.h"
#include "SocketSubsystem.h"
#include "FrameBuffer.h"

namespace MikdashOnline::Receiver03 {
constexpr int32 MaximumAcceptedPerSecond=256; // gateway max 240 plus lifecycle headroom
// Testable production dispatcher. No socket is created by this class.
class Service {
    Owner Identity;InputSink& Sink;TFunction<double()> Clock;
    double Deadline,Last=-1;uint8 Key[32];bool Stopping=false,Disposed=false;
    SessionBridge Bridge;
public:
    Service(const Bootstrap& Config,InputSink& Target,TFunction<double()> InClock);
    ~Service(){FMemory::Memzero(Key,sizeof(Key));}
    bool Dispatch(const TArray<uint8>& Frame,TArray<uint8>& Response);
    void Tick();
    // True only after sink release is confirmed. False must remain quarantined.
    bool Shutdown();
    double Now();
    bool IsStopping() const{return Stopping||Disposed;}
    double EndOfCleanupWindow() const{return Deadline+5;}
};

// Poll only from game thread. No background worker or unbounded task queue.
// Constructor opens nothing; Start is an explicit future integration operation.
class Receiver {
    Service& Authority;ISocketSubsystem* Sockets=nullptr;
    FSocket* Listener=nullptr;FSocket* Peer=nullptr;
    FrameBuffer Input;TArray<uint8> Output;int32 Sent=0;
    double RateStart=0;int32 Accepted=0;bool Stopping=false,PeerClosing=false;
    bool DropPeer();
public:
    explicit Receiver(Service& InAuthority):Authority(InAuthority){}
    ~Receiver();
    bool Start(int32 Port);
    void Tick();
    bool Shutdown();
};
}
