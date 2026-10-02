#include "Receiver.h"
#include "SocketSubsystem.h"
#include "IPAddress.h"

namespace MikdashOnline::Receiver03 {
Service::Service(const Bootstrap& Config,InputSink& Target,TFunction<double()> InClock)
    :Identity(Config.Identity),Sink(Target),Clock(MoveTemp(InClock)),Deadline(Config.Deadline),
     Bridge(Identity,Deadline,Sink,[this](){return Now();}){
    FMemory::Memcpy(Key,Config.Key,sizeof(Key));
    const double N=Now();Stopping=N<0||!FMath::IsFinite(Deadline)||Deadline<=N||Deadline-N>86400;
}
double Service::Now(){
    const double N=Clock();
    if(!FMath::IsFinite(N)||N<0||N<Last||N>1099511627776.0){Stopping=true;return -1;}
    Last=N;return N;
}
bool Service::Dispatch(const TArray<uint8>& Frame,TArray<uint8>& Response){
    check(IsInGameThread());Response.Reset();
    if(Stopping||Disposed||Now()<0)return false;
    Packet P;if(!DecodeRequest(Frame,Key,P)||!(P.owner==Identity))return false;
    const double Before=Now();
    if(Before<0||Before>=Deadline+5)return false;
    // No enqueue acknowledgement: Handle runs right here on the game thread.
    const Ack A=Bridge.Handle(P);
    const double After=Now();
    if(After<0||After-Before>=0.5||After>=Deadline+5){Shutdown();return false;}
    if(P.operation!="release"&&P.operation!="close"&&After>=Deadline){Sink.Release();return false;}
    return EncodeAck(A,Key,Response);
}
void Service::Tick(){
    check(IsInGameThread());
    if(Stopping){Shutdown();return;}
    Bridge.Tick();
    const double N=Now();if(N<0||N>=Deadline+5)Shutdown();
}
bool Service::Shutdown(){
    check(IsInGameThread());Stopping=true;
    if(Disposed)return true;
    if(!Sink.Release())return false;
    Disposed=true;FMemory::Memzero(Key,sizeof(Key));return true;
}
Receiver::~Receiver(){Shutdown();}
bool Receiver::Start(int32 Port){
    check(IsInGameThread());
    if(Stopping||Listener||Port<1024||Port>65535||Authority.IsStopping()||Authority.Now()<0)return false;
    Sockets=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);if(!Sockets)return false;
    Listener=Sockets->CreateSocket(NAME_Stream,TEXT("Mikdash owned native IPC"),ESocketProtocolFamily::IPv4);
    if(!Listener)return false;
    auto Address=Sockets->CreateInternetAddr();bool Valid=false;Address->SetIp(TEXT("127.0.0.1"),Valid);Address->SetPort(Port);
    // No reuse-address and no wildcard/hostname bind. Existing port fails closed.
    if(!Valid||!Listener->SetNonBlocking(true)||!Listener->Bind(*Address)||!Listener->Listen(1)){
        if(Listener->Close()){Sockets->DestroySocket(Listener);Listener=nullptr;}
        else Stopping=true;
        return false;
    }
    return true;
}
bool Receiver::DropPeer(){
    PeerClosing=true;
    if(Peer){if(!Peer->Close())return false;Sockets->DestroySocket(Peer);Peer=nullptr;}
    Input.Reset();Output.Reset();Sent=0;
    PeerClosing=false;return true;
}
void Receiver::Tick(){
    check(IsInGameThread());
    const double N=Authority.Now();
    if(Stopping||N<0||N>=Authority.EndOfCleanupWindow()){Shutdown();return;}
    Authority.Tick();if(Authority.IsStopping()){Shutdown();return;}if(!Listener)return;
    if(PeerClosing){DropPeer();return;}
    if(Peer&&Input.Expired(N)&&!DropPeer())return;
    if(N-RateStart>=1){RateStart=N;Accepted=0;}
    if(!Peer){
        bool Pending=false;
        if(Listener->HasPendingConnection(Pending)&&Pending){
            auto Remote=Sockets->CreateInternetAddr();Peer=Listener->Accept(*Remote,TEXT("Mikdash bounded command"));
            Accepted=FMath::Min(Accepted+1,MaximumAcceptedPerSecond+1);
            if(Peer){
                if(Accepted>MaximumAcceptedPerSecond){DropPeer();return;} // explicit overload close, never queued success
                uint32 Address=0;Remote->GetIp(Address);
                if(Address!=0x7f000001||!Peer->SetNonBlocking(true)){DropPeer();return;}
                Input.Begin(N);
            }
        }
    }
    if(!Peer)return;
    // At most four nonblocking reads / 4096 received bytes per frame.
    for(int32 Pass=0;Pass<4&&Output.Num()==0;++Pass){
        uint32 Pending=0;if(!Peer->HasPendingData(Pending)||Pending==0)break;
        uint8 Buffer[1024];int32 Read=0;
        const int32 Want=Input.Want(Authority.Now());
        if(Want<=0||!Peer->Recv(Buffer,Want,Read)||Read<=0){DropPeer();return;}
        if(!Input.Append(Buffer,Read,Authority.Now())){DropPeer();return;}
        if(Input.Complete()){
            // Fresh read-deadline before auth/dispatch; input never survives this peer.
            if(Input.Expired(Authority.Now())||!Authority.Dispatch(Input.Frame(),Output)){DropPeer();return;}
            break;
        }
    }
    if(Output.Num()){
        if(Input.Expired(Authority.Now())){DropPeer();return;}
        int32 Written=0;
        if(Peer->Send(Output.GetData()+Sent,Output.Num()-Sent,Written)){
            Sent+=Written;if(Sent==Output.Num())DropPeer();
        }else if(Sockets->GetLastErrorCode()!=SE_EWOULDBLOCK)DropPeer();
    }
}
bool Receiver::Shutdown(){
    check(IsInGameThread());Stopping=true;
    bool Closed=true;
    if(Listener){
        if(Listener->Close()){Sockets->DestroySocket(Listener);Listener=nullptr;}
        else Closed=false;
    }
    const bool PeerGone=DropPeer();const bool Released=Authority.Shutdown();
    return Closed&&PeerGone&&Released;
}
}
