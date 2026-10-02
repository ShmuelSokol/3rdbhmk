#include "ReadyOutput.h"
#include "../runtime_adoption01/ParsedAdmission.h"
#include "ReadyEnvelope.h"
#include "../runtime_candidate04/RegistryHost.h"
#include "Windows/WindowsHWrapper.h"
namespace MikdashOnline::Readiness01 {
namespace { TSharedPtr<const Adoption01::FParsedAdmission> Parsed; HANDLE Output=nullptr;bool Used=false,Signalled=false;Owner Identity;double Last=-1; }
TSharedPtr<const Adoption01::FParsedAdmission> TakeParsedAdmission() {
    check(IsInGameThread());return MoveTemp(Parsed); // exactly one private handoff
}
bool Close() {
    check(IsInGameThread());
    Parsed.Reset();
    if(!Output)return true;
    if(!::CloseHandle(Output))return false; // retain handle; no cleanup success claim
    Output=nullptr;return true;
}
bool Admit(const TArray<uint8>& Body,double Now,Receiver03::Bootstrap& Out,double StartupDeadline) {
    check(IsInGameThread());
    if(Used)return false;Used=true;
    if(!std::isfinite(StartupDeadline)||StartupDeadline<=Now)return false;
    std::vector<uint8_t> V2;Settings05::Descriptor D;uint64_t H=0;
    if(!Envelope(Body.GetData(),Body.Num(),V2,D,H))return false;
    HANDLE Candidate=reinterpret_cast<HANDLE>(static_cast<UPTRINT>(H));DWORD Flags=0;
    if(H!=uint64_t(reinterpret_cast<UPTRINT>(Candidate))||Candidate==INVALID_HANDLE_VALUE||
       Candidate==::GetStdHandle(STD_INPUT_HANDLE)||!::GetHandleInformation(Candidate,&Flags)||(Flags&HANDLE_FLAG_INHERIT)) {
        ::SecureZeroMemory(V2.data(),V2.size());return false;
    }
    Output=Candidate; // transfer capability is from the approved retained child launcher
    TArray<uint8> Nested;Nested.Append(V2.data(),int32(V2.size()));
    const bool Valid=Settings05::AdmitPrivateV2(Nested,Now,Out);
    FMemory::Memzero(Nested.GetData(),Nested.Num());::SecureZeroMemory(V2.data(),V2.size());
    if(!Valid)return false; // enclosing bootstrap Shutdown closes retained output
    const auto ExactLease=Settings05::FindLease(Out.Identity);
    if(!ExactLease.IsValid())return false;
    Parsed=MakeShareable(new Adoption01::FParsedAdmission(Out,D.generation,ExactLease.ToSharedRef(),StartupDeadline));
    Identity=Out.Identity;Last=Now;return true;
}
bool SignalStopped(const Owner& ExactOwner,double AdmissionDeadline,double OwnerDeadline) {
    check(IsInGameThread());
    if(!Output||Signalled||!(Identity==ExactOwner)||
       !std::isfinite(AdmissionDeadline)||!std::isfinite(OwnerDeadline)||
       AdmissionDeadline<0||OwnerDeadline<0||OwnerDeadline>ExactOwner.expires_at||
       !Settings05::FindLease(ExactOwner).IsValid()||
       RuntimeCandidate04::FRegistryHost::GetState()!=RuntimeCandidate04::FRegistryHost::State::StoppedReady)return false;
    const double N=Receiver03::QpcSeconds();
    if(!std::isfinite(N)||N<Last||N<0||N>=AdmissionDeadline||N>=OwnerDeadline||N>=ExactOwner.expires_at)return false;
    Last=N;
    if(!::SetEvent(Output))return false;
    Signalled=true;return true; // ONLY one completed stopped-admission receipt, not a live capability
}
}
