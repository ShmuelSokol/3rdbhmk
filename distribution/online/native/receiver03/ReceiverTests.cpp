// Staged UE automation. No listener required even when later compiled/executed.
#if WITH_DEV_AUTOMATION_TESTS
#include "Receiver.h"
#include "FrozenVector.h"
#include "Misc/AutomationTest.h"

using namespace MikdashOnline;
using namespace MikdashOnline::Receiver03;
namespace {
struct SinkProbe : InputSink {
    bool ReleaseWorks=true;int32 Applied=0,Released=0;TFunction<void()> OnApply;
    bool Apply(const std::string&,double,double) override {++Applied;if(OnApply)OnApply();return true;}
    bool Release() override {++Released;return ReleaseWorks;}
};
void Config(Bootstrap& C){C.Identity={"s","p","stream","save","settings",110};C.Deadline=110;C.Port=34567;}
TArray<uint8> Frame(FString Body){
    const uint8 Key[32]={};uint8 Mac[32];FTCHARToUTF8 Text(*Body);
    static const ANSICHAR Domain[]="mikdash-request-v1";
    TArray<uint8> Result;if(!Hmac(Key,Domain,sizeof(Domain),reinterpret_cast<const uint8*>(Text.Get()),Text.Length(),Mac))return Result;
    const uint32 N=Text.Length();Result.Add(uint8(N>>24));Result.Add(uint8(N>>16));Result.Add(uint8(N>>8));Result.Add(uint8(N));
    Result.Append(reinterpret_cast<const uint8*>(Text.Get()),N);Result.Append(Mac,32);return Result;
}
FString Body(uint64 Seq,const TCHAR* Op,const TCHAR* Connection,const TCHAR* Event=TEXT("null"),const TCHAR* Process=TEXT("p")){
    return FString::Printf(TEXT("{\"version\":1,\"owner\":{\"session_id\":\"s\",\"process_key\":\"%s\",\"stream_id\":\"stream\",\"save_prefix\":\"save\",\"settings_slot\":\"settings\",\"expires_at\":110},\"sequence\":%llu,\"operation\":\"%s\",\"connection_id\":\"%s\",\"event\":%s}"),Process,static_cast<unsigned long long>(Seq),Op,Connection,Event);
}
const TCHAR* Move=TEXT("{\"action\":\"move\",\"x\":1,\"y\":0}");
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FReceiver03WireTest,"Mikdash.Online.Receiver03.AuthenticatedWire",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FReceiver03WireTest::RunTest(const FString&){
    const uint8 Key[32]={};Packet P;TArray<uint8> Open;Open.Append(FrozenOpenFrame,UE_ARRAY_COUNT(FrozenOpenFrame));
    TestTrue(TEXT("Frozen Python frame accepted by native CNG HMAC and parser"),DecodeRequest(Open,Key,P));
    TestTrue(TEXT("Exact decoded identity"),P.owner.process_key=="p"&&P.operation=="open"&&P.sequence==1);
    auto Bad=Open;Bad.Last()^=1;TestFalse(TEXT("MAC mutation denied"),DecodeRequest(Bad,Key,P));
    Ack A{1,P.owner,1,"open","","applied"};TArray<uint8> Response;
    TestTrue(TEXT("Response encoded"),EncodeAck(A,Key,Response));
    TestFalse(TEXT("Response MAC domain cannot authenticate a request"),DecodeRequest(Response,Key,P));
    TestFalse(TEXT("Partial frame denied"),DecodeRequest(TArray<uint8>({0,0,0,10}),Key,P));
    TestFalse(TEXT("Oversized frame denied"),DecodeRequest(TArray<uint8>({0,0,16,1}),Key,P));
    FString Duplicate=Body(1,TEXT("open"),TEXT(""));Duplicate.ReplaceInline(TEXT("\"version\":1"),TEXT("\"version\":1,\"version\":1"));
    TestFalse(TEXT("Authenticated duplicate root key denied"),DecodeRequest(Frame(Duplicate),Key,P));
    FString Nested=Body(1,TEXT("open"),TEXT(""));Nested.ReplaceInline(TEXT("\"process_key\":\"p\""),TEXT("\"process_key\":\"p\",\"process_key\":\"other\""));
    TestFalse(TEXT("Authenticated duplicate nested key denied"),DecodeRequest(Frame(Nested),Key,P));
    TestFalse(TEXT("Console input denied"),DecodeRequest(Frame(Body(3,TEXT("input"),TEXT("c"),TEXT("{\"action\":\"console\",\"x\":0,\"y\":0}"))),Key,P));
    FrameBuffer Buffer;Buffer.Begin(100);
    TestTrue(TEXT("Partial header"),Buffer.Append(Open.GetData(),2,100.1));
    TestTrue(TEXT("Rest of header"),Buffer.Append(Open.GetData()+2,2,100.2));
    TestFalse(TEXT("Partial reads do not renew frame deadline"),Buffer.Append(Open.GetData()+4,1,100.5));
    Buffer.Begin(100);const uint8 Oversized[]={0,0,16,1};
    TestFalse(TEXT("Oversized length rejected before body allocation"),Buffer.Append(Oversized,4,100));
    Buffer.Begin(100);TestTrue(TEXT("Header"),Buffer.Append(Open.GetData(),4,100));
    TestTrue(TEXT("Complete bounded body and MAC"),Buffer.Append(Open.GetData()+4,Open.Num()-4,100.1));
    TestTrue(TEXT("Complete frame"),Buffer.Complete());
    TestFalse(TEXT("No pipelined second command"),Buffer.Append(Open.GetData(),1,100.2));
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FReceiver03LifecycleTest,"Mikdash.Online.Receiver03.OwnershipExpiryShutdown",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FReceiver03LifecycleTest::RunTest(const FString&){
    Bootstrap C;Config(C);double Now=100;SinkProbe Sink;Service S(C,Sink,[&](){return Now;});TArray<uint8> Ack;
    TestTrue(TEXT("Open"),S.Dispatch(Frame(Body(1,TEXT("open"),TEXT(""))),Ack));
    TestTrue(TEXT("Bind"),S.Dispatch(Frame(Body(2,TEXT("bind"),TEXT("c"))),Ack));
    TestTrue(TEXT("Input delivered synchronously"),S.Dispatch(Frame(Body(3,TEXT("input"),TEXT("c"),Move)),Ack));
    TestEqual(TEXT("Applied exactly once"),Sink.Applied,1);
    TestFalse(TEXT("Foreign ownership denied before bridge"),S.Dispatch(Frame(Body(4,TEXT("input"),TEXT("c"),Move,TEXT("other"))),Ack));
    S.Dispatch(Frame(Body(3,TEXT("input"),TEXT("c"),Move)),Ack);
    TestEqual(TEXT("Replay has no duplicate input"),Sink.Applied,1);
    Now=102.1;const int32 Before=Sink.Released;S.Tick();TestTrue(TEXT("Stationary stale input released"),Sink.Released>Before);
    Sink.ReleaseWorks=false;TestFalse(TEXT("Shutdown quarantines rejected release"),S.Shutdown());
    TestFalse(TEXT("Stopping authority refuses input"),S.Dispatch(Frame(Body(5,TEXT("input"),TEXT("c"),Move)),Ack));
    Sink.ReleaseWorks=true;TestTrue(TEXT("Shutdown retry completes"),S.Shutdown());
    const int32 After=Sink.Released;TestTrue(TEXT("Double shutdown"),S.Shutdown());TestEqual(TEXT("No double release"),Sink.Released,After);
    Bootstrap Late;Config(Late);Now=111;SinkProbe LateSink;Service Expired(Late,LateSink,[&](){return Now;});
    TestFalse(TEXT("Late startup/queued open cannot renew lease"),Expired.Dispatch(Frame(Body(1,TEXT("open"),TEXT(""))),Ack));
    TestEqual(TEXT("Expired input never applied"),LateSink.Applied,0);
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FReceiver03DelayedAckTest,"Mikdash.Online.Receiver03.NoLateAppliedAck",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FReceiver03DelayedAckTest::RunTest(const FString&){
    Bootstrap C;Config(C);double Now=100;SinkProbe Sink;Service S(C,Sink,[&](){return Now;});TArray<uint8> Ack;
    S.Dispatch(Frame(Body(1,TEXT("open"),TEXT(""))),Ack);S.Dispatch(Frame(Body(2,TEXT("bind"),TEXT("c"))),Ack);
    Sink.OnApply=[&](){Now+=0.6;};
    TestFalse(TEXT("Slow application never gets success ACK"),S.Dispatch(Frame(Body(3,TEXT("input"),TEXT("c"),Move)),Ack));
    TestTrue(TEXT("Failed deadline releases input"),Sink.Released>=3);
    TestTrue(TEXT("No stale ACK buffer"),Ack.IsEmpty());
    return true;
}
#endif
