#include "PrivateBootstrap.h"
#include "../runtime_settings05/NativeLease.h"
#include "../Native/receiver04/BootstrapGuards.h"
#include "../runtime_candidate04/RegistryHost.h"
#include "Windows/WindowsHWrapper.h"

namespace MikdashOnline::RuntimeCandidate05 {
using FHost=RuntimeCandidate04::FRegistryHost;
bool ValidatePrivateRecord(const TArray<uint8>& Body,double Now,Receiver03::Bootstrap& Out) {
    const bool Good=std::isfinite(Now)&&Now>=0&&Now<=1099511627776.0&&
        Body.Num()>=2&&Body.Num()<=4092&&Receiver03::ParseBootstrap(Body,Out)&&
        Out.Deadline>Now&&Out.Deadline<=Out.Identity.expires_at&&Out.Deadline-Now<=86400;
    if(!Good) FMemory::Memzero(Out.Key,sizeof(Out.Key));
    return Good;
}
bool FPrivateBootstrap::Fresh(double Deadline) {
    const double N=Receiver03::QpcSeconds();
    if(!std::isfinite(N)||N<0||N>1099511627776.0||N<Last||N>=Deadline) return false;
    Last=N;return true;
}
bool FPrivateBootstrap::CloseInput() {
    return Receiver04::CloseBootstrapInput(Input,InputPoisoned,[](void* H) {
        return ::CloseHandle(static_cast<HANDLE>(H))!=0;
    });
}
bool FPrivateBootstrap::Startup() {
    check(IsInGameThread());
    if(Used||Phase!=State::Empty) return false;
    Used=true;
    const double N=Receiver03::QpcSeconds();
    if(!std::isfinite(N)||N<0||N>1099511627771.0) { Phase=State::Closed;return false; }
    Last=N;ReadEnd=N+5;
    HANDLE H=::GetStdHandle(STD_INPUT_HANDLE);
    DWORD Flags=0,PipeFlags=0;
    // Narrow supported launch contract. These checks do NOT identify a trusted
    // parent: only the approved exact-job/handle-list launcher provides that trust.
    if(!H||H==INVALID_HANDLE_VALUE||::GetFileType(H)!=FILE_TYPE_PIPE) { Shutdown();return false; }
    Input=H;
    if(!::GetHandleInformation(H,&Flags)||!(Flags&HANDLE_FLAG_INHERIT)||
       !::GetNamedPipeInfo(H,&PipeFlags,nullptr,nullptr,nullptr)||(PipeFlags&PIPE_TYPE_MESSAGE)) {
        Shutdown();return false;
    }
    HostStarted=FHost::Startup();
    if(!HostStarted) { Shutdown();return false; }
    Phase=State::Reading;return true;
}
void FPrivateBootstrap::PollRead() {
    if(!Fresh(ReadEnd)) { Shutdown();return; }
    DWORD Available=0;
    if(!::PeekNamedPipe(static_cast<HANDLE>(Input),nullptr,0,nullptr,&Available,nullptr)) {
        const DWORD Error=::GetLastError();
        // Accept exactly one frame only after the private writer closes. Late or
        // partial EOF is failure. A trailing record never becomes a second request.
        if(Error==ERROR_BROKEN_PIPE&&Expected>4&&Bytes.Num()==Expected) AcceptClosedRecord();
        else Shutdown();
        return;
    }
    if(Bytes.Num()==Expected&&Expected>4) {
        if(Available) Shutdown(); // extra bytes forbidden, otherwise wait for EOF
        return;
    }
    if(!Available) return;
    const DWORD Want=FMath::Min<DWORD>(Available,Expected-Bytes.Num());
    if(!Want||Want>4096) { Shutdown();return; }
    uint8 Buffer[4096]={};DWORD Read=0;
    const bool Ok=::ReadFile(static_cast<HANDLE>(Input),Buffer,Want,&Read,nullptr)!=0;
    if(Ok&&Read<=Want) Bytes.Append(Buffer,Read);
    ::SecureZeroMemory(Buffer,sizeof(Buffer));
    if(!Ok||Read>Want) { Shutdown();return; }
    // TRUE/zero read is pending; next tick/deadline resolves it, never fake EOF.
    if(Bytes.Num()==4&&Expected==4) {
        const uint32 Size=(uint32(Bytes[0])<<24)|(uint32(Bytes[1])<<16)|(uint32(Bytes[2])<<8)|Bytes[3];
        if(Size<2||Size>4092) { Shutdown();return; }
        Expected=int32(Size)+4;
    }
    if(!Fresh(ReadEnd)) Shutdown();
}
void FPrivateBootstrap::AcceptClosedRecord() {
    if(!Fresh(ReadEnd)||!CloseInput()) { Shutdown();return; }
    TArray<uint8> Body;Body.Append(Bytes.GetData()+4,Bytes.Num()-4);
    Provisioning=MakeUnique<Receiver03::Bootstrap>();
    const bool Valid=Fresh(ReadEnd)&&Settings05::AdmitPrivateV2(Body,Last,*Provisioning);
    FMemory::Memzero(Body.GetData(),Body.Num());Body.Reset();
    FMemory::Memzero(Bytes.GetData(),Bytes.Num());Bytes.Reset();
    if(!Valid||!Settings05::LeaseLive()||!Fresh(ReadEnd)||!Fresh(Provisioning->Deadline)) { Shutdown();return; }
    // Only stopped admission. No listener, port bind, key export, ACK or media.
    Busy=true;
    const bool Admitted=FHost::AdmitStopped(Provisioning->Identity,Provisioning->Deadline);
    Busy=false;
    if(Stopping||!Admitted||!Settings05::LeaseLive()||!Fresh(ReadEnd)||!Fresh(Provisioning->Deadline)) { Shutdown();return; }
    Phase=State::StoppedProvisioned;
}
void FPrivateBootstrap::Tick() {
    check(IsInGameThread());
    if(Busy||Stopping) return;
    if(Phase==State::Reading) { PollRead();return; }
    if(Phase==State::StoppedProvisioned&&(!Settings05::LeaseLive()||!Provisioning||!Fresh(Provisioning->Deadline)||
       FHost::GetState()!=FHost::State::StoppedReady)) Shutdown();
}
bool FPrivateBootstrap::Shutdown() {
    check(IsInGameThread());Stopping=true;
    if(Busy) return false;
    if(Phase==State::Closed) return true;
    if(Phase==State::Quarantined) return false;
    Busy=true;
    const bool LeaseClosed=Settings05::RevokeLease();
    const bool InputClosed=CloseInput();
    if(Bytes.Num()) FMemory::Memzero(Bytes.GetData(),Bytes.Num());Bytes.Reset();
    Provisioning.Reset(); // Bootstrap destructor wipes its retained key
    const bool HostClosed=!HostStarted||FHost::Shutdown();
    Busy=false;Phase=LeaseClosed&&InputClosed&&HostClosed?State::Closed:State::Quarantined;
    return Phase==State::Closed;
}
}
