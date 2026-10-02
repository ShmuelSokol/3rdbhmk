#include "Receiver.h"
#include "IPAddress.h"
#include "StreamRead.h"

namespace MikdashOnline::Receiver04 {
bool Receiver::CloseSocket(FSocket*& Socket,bool& Poisoned){
    if(Poisoned)return false; // UE invalidated its handle; retry cannot recover it
    if(!Socket)return true;
    if(!Socket->Close()){Poisoned=true;Stopping=true;Service.Abort();return false;}
    Sockets->DestroySocket(Socket);Socket=nullptr;return true;
}
bool Receiver::Drop(bool AbortPending){
    if(AbortPending&&Authenticated&&Service.IsAwaiting())Service.Abort();
    if(!CloseSocket(Peer,PeerPoisoned))return false;
    Input.Reset();Output.Reset();Sent=0;Authenticated=false;return true;
}
bool Receiver::Start(int32 Port){
    check(IsInGameThread());
    if(Stopping||Listener||Port<1024||Port>65535||Service.IsClosed())return false;
    Sockets=ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);if(!Sockets)return false;
    Listener=Sockets->CreateSocket(NAME_Stream,TEXT("Mikdash receiver04 owned IPC"),ESocketProtocolFamily::IPv4);
    if(!Listener)return false;
    auto Address=Sockets->CreateInternetAddr();bool Valid=false;
    Address->SetIp(TEXT("127.0.0.1"),Valid);Address->SetPort(Port);
    if(!Valid||!Listener->SetNonBlocking(true)||!Listener->Bind(*Address)||!Listener->Listen(1)){
        Shutdown();return false;
    }
    return true;
}
void Receiver::Tick(){
    check(IsInGameThread());
    Service.Maintain(); // MUST precede all no-peer/partial-frame early returns
    const double Now=Receiver03::QpcSeconds();
    if(Stopping||Now<0||Service.IsClosed()){Shutdown();return;}
    if(Peer&&Input.Expired(Now)){Drop(true);return;}
    if(Now-RateStart>=1){RateStart=Now;AcceptedCount=0;}
    if(!Peer&&Listener){
        bool Pending=false;
        if(Listener->HasPendingConnection(Pending)&&Pending){
            auto Remote=Sockets->CreateInternetAddr();Peer=Listener->Accept(*Remote,TEXT("Mikdash one command"));
            if(Peer){
                ++AcceptedCount;AcceptedAt=Receiver03::QpcSeconds();
                uint32 IP=0;Remote->GetIp(IP);
                if(AcceptedCount>256||IP!=0x7f000001||!Peer->SetNonBlocking(true)){Drop(false);return;}
                Input.Begin(AcceptedAt);
            }
        }
    }
    if(!Peer)return;
    if(!Input.Complete()){
        for(int Pass=0;Pass<4;++Pass){
            const int Want=Input.Want(Receiver03::QpcSeconds());
            if(Want<=0){Drop(true);return;}
            uint8 Buffer[1024];int32 Read=0;
            // Nonblocking Recv even when no pending bytes: promptly observes EOF
            // from a zero-byte startup hint instead of occupying the slot for .5s.
            const StreamRead Result=ReadStream(*Peer,Buffer,Want,Read);
            if(Result==StreamRead::Wait)break; // retain frame and ORIGINAL deadline
            if(Result==StreamRead::Closed){Drop(true);return;}
            if(!Input.Append(Buffer,Read,Receiver03::QpcSeconds())){Drop(true);return;}
            if(Input.Complete()){
                if(!Service.Receive(Input.Frame(),AcceptedAt,Output)){Drop(true);return;}
                Authenticated=true;break;
            }
        }
    }
    if(Input.Complete()&&Output.IsEmpty())Service.PollReply(Output);
    if(Service.IsClosed()&&Output.IsEmpty()){Shutdown();return;}
    if(!Output.IsEmpty()){
        if(Input.Expired(Receiver03::QpcSeconds())){Drop(true);return;}
        int32 Wrote=0;
        if(Peer->Send(Output.GetData()+Sent,Output.Num()-Sent,Wrote)){
            Sent+=Wrote;if(Sent==Output.Num())Drop(false);
        }else if(Sockets->GetLastErrorCode()!=SE_EWOULDBLOCK)Drop(true);
    }
}
bool Receiver::Shutdown(){
    check(IsInGameThread());Stopping=true;Service.Abort();
    const bool A=CloseSocket(Listener,ListenerPoisoned);
    const bool B=Drop(true);
    return A&&B; // false permanently quarantines poisoned sockets until job exit
}
}
