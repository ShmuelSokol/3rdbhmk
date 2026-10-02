#include "Authority.h"
#include "OnlineController.h"
#include "GameFramework/PlayerInput.h"
#include "Engine/World.h"

namespace MikdashOnline::Receiver04 {
Authority::Authority(const Receiver03::Bootstrap& B,uint64_t C,uint64_t P,TFunction<double()> InClock,const std::string& InProcessGeneration)
    :Identity(B.Identity),ProcessGeneration(InProcessGeneration),Deadline(B.Deadline),Clock(MoveTemp(InClock)),
     NativeContext{C,P,0},Mailbox(Deadline,[this](){return Now();}){
    PawnSerial=P;
    FMemory::Memcpy(Key,B.Key,sizeof(Key));
    const double N=Now();Closed=!C||!P||N<0||!FMath::IsFinite(Deadline)||Deadline<=N||Deadline-N>86400||
        !FMath::IsFinite(Identity.expires_at)||Deadline>Identity.expires_at;
}
double Authority::Now(){
    const double N=Clock();
    if(!FMath::IsFinite(N)||N<0||N<Last||N>1099511627776.0){Closed=true;return -1;}
    Last=N;return N;
}
bool Authority::Receive(const TArray<uint8>& Frame,double AcceptedAt,TArray<uint8>& Immediate){
    check(IsInGameThread());Immediate.Reset();
    const double N=Now();
    if(Possessing||Closed||N<0||!FMath::IsFinite(AcceptedAt)||AcceptedAt<0||AcceptedAt>N||N>=AcceptedAt+0.5)return false;
    Packet P;if(!Receiver03::DecodeRequest(Frame,Key,P)||!(P.owner==Identity)||P.process_generation!=ProcessGeneration||P.sequence<=Sequence)return false;
    const bool Cleanup=P.operation=="release"||P.operation=="close";
    if(Awaiting&&!Cleanup)return false;
    if(NeedsRelease && !Cleanup)return false;
    if(Generation>=9007199254740990ULL || NativeContext.generation>=9007199254740990ULL) { Abort();return false; }
    ReplyUntil=FMath::Min(AcceptedAt+0.5,Deadline+(Cleanup?5:0));
    const double Fresh=Now();if(Fresh<0||Fresh>=ReplyUntil)return false;
    Sequence=P.sequence;
    if(P.operation=="input"){
        if(!Opened||Connection.empty()||P.connection_id!=Connection||!OnInput||!OnInput(P)||
           (P.action!="dove"&&!Mailbox.Submit(P,NativeContext,AcceptedAt)))return false;
        if(P.action=="dove"&&!Flight.Queue(NativeContext.controller,NativeContext.pawn,
            NativeContext.generation,P.sequence,Now(),ReplyUntil))return false;
        if(P.action=="dove")Mailbox.PauseMotion();
        Waiting=P;Awaiting=true;return true;
    }
    if(P.operation=="open"&&!Opened&&P.connection_id.empty()){
        const auto Hook=OnLifecycle;
        if(!Hook||!Hook(P)||Closed||Now()>=ReplyUntil){Abort();return false;}
        Mailbox.Clear();Opened=true;
    }else if(P.operation=="bind"&&Opened&&Connection.empty()&&!P.connection_id.empty()){
        const auto Hook=OnLifecycle;
        if(!Hook||!Hook(P)||Closed||Now()>=ReplyUntil){Abort();return false;}
        if(UsedConnections.size()>=256 || UsedConnections.count(P.connection_id)) { Abort();return false; }
        UsedConnections.insert(P.connection_id);
        ++Generation;++NativeContext.generation;
        if(!Mailbox.Bind(NativeContext)){Abort();return false;}
        Connection=P.connection_id;
    }else if(P.operation=="stream"&&Opened&&!Connection.empty()&&P.connection_id==Connection){
        const auto Hook=OnLifecycle;
        if(!Hook||!Hook(P)||Closed||Now()>=ReplyUntil){Abort();return false;}
    }else if(P.operation=="release"&&(Connection.empty()||P.connection_id==Connection)){
        const auto Hook=OnLifecycle;
        if(!Hook||!Hook(P)||Closed||Now()>=ReplyUntil){Abort();return false;}
        Flight.Cancel();FlightHandoff=false;Mailbox.Clear();Connection.clear();++Generation;++NativeContext.generation;NeedsRelease=false;Awaiting=false;Waiting=Packet();
    }else if(P.operation=="close"){
        const auto Hook=OnLifecycle;
        if(!Hook||!Hook(P)||Closed||Now()>=ReplyUntil){Abort();return false;}
        Mailbox.Invalidate();Connection.clear();++Generation;++NativeContext.generation;Closed=true;Awaiting=false;Waiting=Packet();
    }else{return false;}
    const Consumption C{P.sequence,Generation,Outcome::Applied,Fresh};
    return Encode(P,C,Immediate);
}
bool Authority::PollReply(TArray<uint8>& Out){
    check(IsInGameThread());Out.Reset();
    Maintain();if(Closed)return false;
    if(!Awaiting)return false;
    Consumption C;
    if(Waiting.action=="dove") {
        double At=0;bool Handoff=false;
        if(!Flight.Take(Waiting.sequence,NativeContext.controller,NativeContext.pawn,
            NativeContext.generation,Now(),At,Handoff))return false;
        C={Waiting.sequence,NativeContext.generation,FlightOutcome,At};FlightHandoff=Handoff;
    } else if(!Mailbox.Take(C))return false;
    Awaiting=false;
    const bool NativeValid=C.sequence==Waiting.sequence&&C.generation==NativeContext.generation;
    C.generation=Generation; // wire ACK contract remains release/bind/close +1 only
    const bool Valid=NativeValid&&Encode(Waiting,C,Out);
    Waiting=Packet();FlightHandoff=false;if(!Valid)Abort();return Valid;
}
// Actual controller input-consumption hook; this is not a receive/enqueue ACK.
bool Authority::ConsumeFlight(AReceiver04Controller& C) {
    if(!Awaiting||Waiting.action!="dove")return false;
    const TSharedPtr<Authority> S=C.Remote;
    const TWeakObjectPtr<AReceiver04Controller> Self(&C);
    const TWeakObjectPtr<UWorld> World=C.GetWorld();
    const TWeakObjectPtr<UPlayerInput> Input=C.PlayerInput.Get();
    auto Owned=[&]() {
        return Self.IsValid()&&S.Get()==this&&C.Remote==S&&!Closed&&C.RemotePossessionCurrent()&&
            World.IsValid()&&Input.IsValid()&&C.GetWorld()==World.Get()&&C.PlayerInput.Get()==Input.Get()&&Now()<ReplyUntil;
    };
    if(!Owned()||!Flight.Consume(NativeContext.controller,NativeContext.pawn,NativeContext.generation,Now())){Abort();return true;}
    const bool Before=C.IsDoveFlightActive();
    auto Fence=[&]() {
        return Owned()&&Flight.Fence(NativeContext.controller,NativeContext.pawn,NativeContext.generation,Now());
    };
    // Project wrapper checks this fence immediately before BeginDoveTransition,
    // AFTER cinematic/callback-capable work. Its existing scope-exit performs
    // the real EndDoveTransition / Bootstrap commit before returning here.
    if(!Owned()){Abort();return true;}
    C.ToggleDoveFlightGuarded(Fence);
    if(!Owned()){Abort();return true;}
    FlightOutcome=Before!=C.IsDoveFlightActive()?Outcome::Applied:Outcome::NoOp;
    if(!Flight.Complete(NativeContext.controller,NativeContext.pawn,NativeContext.generation,Now(),true))Abort();
    return true;
}

void Authority::Maintain(){
    check(IsInGameThread());
    const double N=Now();
    if(Closed||N<0||N>=Deadline||(Awaiting&&N>=ReplyUntil))Abort();
    // No post-expiry listener grace. Host cleanup is exact-job disposal; it does
    // not depend on a final native release/close ACK. Never extend session lease.
}
bool Authority::Encode(const Packet& P,const Consumption& C,TArray<uint8>& Out){
    const double N=Now();
    if(N<0||N>=ReplyUntil||C.authorized_at>N||C.outcome==Outcome::Unknown)return false;
    const TCHAR* Result=C.outcome==Outcome::Applied?TEXT("applied"):
                        C.outcome==Outcome::NoOp?TEXT("no_op"):TEXT("rejected");
    const Owner& O=Identity;
    const FString Body=FString::Printf(TEXT("{\"version\":4,\"handoff\":%s,\"process_generation\":\"%s\",\"owner\":{\"session_id\":\"%s\",\"process_key\":\"%s\",\"stream_id\":\"%s\",\"save_prefix\":\"%s\",\"settings_slot\":\"%s\",\"expires_at\":%.17g},\"sequence\":%llu,\"operation\":\"%s\",\"connection_id\":\"%s\",\"status\":\"consumed\",\"outcome\":\"%s\",\"authorized_at\":%.17g,\"generation\":%llu}"),
        FlightHandoff?TEXT("true"):TEXT("false"),UTF8_TO_TCHAR(ProcessGeneration.c_str()),UTF8_TO_TCHAR(O.session_id.c_str()),UTF8_TO_TCHAR(O.process_key.c_str()),UTF8_TO_TCHAR(O.stream_id.c_str()),
        UTF8_TO_TCHAR(O.save_prefix.c_str()),UTF8_TO_TCHAR(O.settings_slot.c_str()),O.expires_at,
        static_cast<unsigned long long>(P.sequence),UTF8_TO_TCHAR(P.operation.c_str()),UTF8_TO_TCHAR(P.connection_id.c_str()),
        Result,C.authorized_at,static_cast<unsigned long long>(C.generation));
    FTCHARToUTF8 Bytes(*Body);const int32 Size=Bytes.Length();if(Size<2||Size>Receiver03::MaxBody)return false;
    static const ANSICHAR Domain[]="mikdash-response-v1";uint8 Mac[32];
    if(!Receiver03::Hmac(Key,Domain,sizeof(Domain),reinterpret_cast<const uint8*>(Bytes.Get()),Size,Mac))return false;
    Out.Reset();Out.Add(uint8(Size>>24));Out.Add(uint8(Size>>16));Out.Add(uint8(Size>>8));Out.Add(uint8(Size));
    Out.Append(reinterpret_cast<const uint8*>(Bytes.Get()),Size);Out.Append(Mac,32);FMemory::Memzero(Mac,sizeof(Mac));return true;
}
}
