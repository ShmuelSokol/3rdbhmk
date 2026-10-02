// STAGED ONLY: calls the actual native validator and frozen UE JSON parser.
#include "PrivateBootstrap.h"
#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FPrivateRecordRefusal,
    "Mikdash.Online.Candidate05.PrivateRecordRefusal",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FPrivateRecordRefusal::RunTest(const FString&) {
    using namespace MikdashOnline;
    const FString Good=TEXT("{\"version\":1,\"clock_domain\":\"windows-qpc-v1\",\"owner\":{\"session_id\":\"session\",\"process_key\":\"process\",\"stream_id\":\"stream\",\"save_prefix\":\"save\",\"settings_slot\":\"settings\",\"expires_at\":110},\"qpc_deadline\":109,\"port\":49152,\"key_hex\":\"0000000000000000000000000000000000000000000000000000000000000000\"}");
    auto Validate=[](const FString& Text,double Now) {
        TArray<uint8> Bytes;for(TCHAR C:Text)Bytes.Add(uint8(C));
        Receiver03::Bootstrap Out;
        const bool Result=RuntimeCandidate05::ValidatePrivateRecord(Bytes,Now,Out);
        FMemory::Memzero(Bytes.GetData(),Bytes.Num());return Result;
    };
    TestTrue(TEXT("Private record syntax only, not authentication"),Validate(Good,100));
    TestFalse(TEXT("Exact expiry"),Validate(Good,109));
    TestFalse(TEXT("Late queue"),Validate(Good,111));
    TestFalse(TEXT("Clock unavailable"),Validate(Good,-1));
    TestFalse(TEXT("Duplicate key"),Validate(Good.Replace(TEXT("\"version\":1"),TEXT("\"version\":1,\"version\":1")),100));
    TestFalse(TEXT("Unproved clock domain"),Validate(Good.Replace(TEXT("windows-qpc-v1"),TEXT("python-monotonic")),100));
    TestFalse(TEXT("Expiry extension"),Validate(Good.Replace(TEXT("\"qpc_deadline\":109"),TEXT("\"qpc_deadline\":111")),100));
    TestFalse(TEXT("Port type"),Validate(Good.Replace(TEXT("\"port\":49152"),TEXT("\"port\":true")),100));
    TestFalse(TEXT("Extra root"),Validate(Good+TEXT("{}"),100));
    TestFalse(TEXT("Oversized body"),Validate(FString::ChrN(4093,TEXT('x')),100));
    return true;
}
#endif
