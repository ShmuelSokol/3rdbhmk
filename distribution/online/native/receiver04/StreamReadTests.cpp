#include "StreamRead.h"
#include "../receiver03/FrameBuffer.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS
using namespace MikdashOnline::Receiver04;
namespace {
struct StreamDouble {
    bool Success=true;TArray<uint8> Bytes;
    bool Recv(uint8* Out,int32 Want,int32& Read){
        Read=FMath::Min(Want,Bytes.Num());
        if(Read)FMemory::Memcpy(Out,Bytes.GetData(),Read);
        return Success;
    }
};
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FStreamWouldBlock,"Mikdash.Online.Receiver04.StreamWouldBlock",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FStreamWouldBlock::RunTest(const FString&){
    StreamDouble P;uint8 Buffer[1024];int32 Read=99;
    TestTrue(TEXT("true zero waits"),ReadStream(P,Buffer,4,Read)==StreamRead::Wait);
    TestEqual(TEXT("no bytes"),Read,0);return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FStreamEOF,"Mikdash.Online.Receiver04.StreamEOF",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FStreamEOF::RunTest(const FString&){
    StreamDouble P;P.Success=false;uint8 Buffer[1024];int32 Read=99;
    // Double intentionally has no GetLastErrorCode: false/zero MUST drop even
    // when a real subsystem's last error remains SE_EWOULDBLOCK from prior recv.
    TestTrue(TEXT("false zero closes"),ReadStream(P,Buffer,4,Read)==StreamRead::Closed);return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FStreamFragments,"Mikdash.Online.Receiver04.StreamFragments",EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FStreamFragments::RunTest(const FString&){
    MikdashOnline::Receiver03::FrameBuffer Frame;Frame.Begin(10);
    StreamDouble P;uint8 Buffer[1024];int32 Read=0;
    auto Append=[&](double Now){
        const auto R=ReadStream(P,Buffer,Frame.Want(Now),Read);
        return R==StreamRead::Data&&Frame.Append(Buffer,Read,Now);
    };
    P.Bytes={0,0};TestTrue(TEXT("half prefix"),Append(10.01));
    P.Bytes.Reset();TestTrue(TEXT("gap preserves prefix"),ReadStream(P,Buffer,Frame.Want(10.1),Read)==StreamRead::Wait);
    P.Bytes={0,2};TestTrue(TEXT("remaining prefix"),Append(10.2));
    P.Bytes={123};TestTrue(TEXT("partial body"),Append(10.3));
    P.Bytes.Reset();TestTrue(TEXT("body gap"),ReadStream(P,Buffer,Frame.Want(10.4),Read)==StreamRead::Wait);
    P.Bytes.Add(125);P.Bytes.AddZeroed(32);TestTrue(TEXT("body and tag"),Append(10.49));
    TestTrue(TEXT("complete"),Frame.Complete());
    TestTrue(TEXT("original expiry unchanged"),Frame.Expired(10.5));return true;
}
#endif
