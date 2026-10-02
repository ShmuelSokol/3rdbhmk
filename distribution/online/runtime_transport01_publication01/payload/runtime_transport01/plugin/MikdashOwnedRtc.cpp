#include "MikdashOwnedRtcPrivate.h"
#include "PixelStreaming2RTCModule.h"
#include "EpicRtcStreamer.h"
#include "IWebSocket.h"
#include "WebSocketsModule.h"
#include "Misc/CoreDelegates.h"
#include "UtilsString.h"
#include "Windows/WindowsHWrapper.h"

namespace UE::PixelStreaming2 {
namespace {
uint32 OwnedAdoptionAttempts=0; // owned admissions only; never limits stock factory creation
double RawQpc(){LARGE_INTEGER N,F;if(!QueryPerformanceCounter(&N)||!QueryPerformanceFrequency(&F)||F.QuadPart<=0)return -1;return double(N.QuadPart)/double(F.QuadPart);}
bool Token(const FString& S,int32 Exact=0){
    if(S.Len()<1||S.Len()>128||(Exact&&S.Len()!=Exact))return false;
    for(TCHAR C:S)if(!((C>='a'&&C<='z')||(C>='A'&&C<='Z')||(C>='0'&&C<='9')||C=='_'||C=='-'))return false;
    return true;
}
void Wipe(FString& S){if(S.Len())FMemory::Memzero(S.GetCharArray().GetData(),S.GetCharArray().Num()*sizeof(TCHAR));S.Empty();}
}
bool FMikdashOwnedConference::Live(){
    const double N=RawQpc();const auto S=Streamer.Pin();
    if(!IsInGameThread()||Closing||!S.IsValid()||!FMath::IsFinite(N)||N<0||N<Last||
       (Last>=0&&N-Last>0.5)||N>=Identity.QpcEnd||N>=Identity.OwnerEnd||(!Connected&&N>=AttachEnd)||
       S->GetId()!=Identity.Stream||IsEngineExitRequested()||
       (Installed&&!S->MikdashMatchesScope(this)))return false;
    if(!Lease->Live()||Closing)return false;
    const double After=RawQpc();
    if(!FMath::IsFinite(After)||After<N||After>=Identity.QpcEnd||After>=Identity.OwnerEnd||
       (!Connected&&After>=AttachEnd)||!Streamer.IsValid()||Streamer.Pin()!=S)return false;
    Last=After;return true;
}
bool FMikdashOwnedConference::Take(const FString& InUrl,TMap<FString,FString>& Headers){
    if(Taken||InUrl!=Url||!Live())return false;
    Taken=true;Headers.Add(TEXT("Authorization"),TEXT("Bearer ")+Ticket);Wipe(Ticket);return true;
}
bool FMikdashOwnedConference::Initialize(){
    auto* M=FModuleManager::GetModulePtr<FPixelStreaming2RTCModule>(TEXT("PixelStreaming2RTC"));
    if(!M||!M->IsReady()||!Live())return false;
    Platform=M->MikdashPlatform();if(!Platform)return false;
    Factory=MakeRefCount<FMikdashOwnedFactory>(AsShared());
    Name=TEXT("MikdashOwned_")+Identity.ProcessGeneration;
    if(!M->MikdashCreateConference(Name,Factory.GetReference(),Conference))return false;
    // Own frame loop: never use the stock unbounded drain/destructor tick task.
    const auto Self=AsShared();
    Frame=FCoreDelegates::OnBeginFrame.AddLambda([Self](){Self->Tick();});
    Exit=FCoreDelegates::OnEnginePreExit.AddLambda([Self](){Self->Revoke();});
    return Live();
}
void FMikdashOwnedConference::Tick(){
    const auto KeepAlive=AsShared();
    if(Ticking)return;
    if(!Live()){Revoke();return;}
    Ticking=true;
    // Each opaque Tick may itself stall: parent owned Job remains the hard stop.
    for(int32 I=0;I<8&&!Closing&&Live()&&Conference&&Conference->NeedsTick();++I)Conference->Tick();
    Ticking=false;
    if(!Live())Revoke();
}
void FMikdashOwnedConference::Revoke(){
    if(Closing)return;Closing=true;Wipe(Ticket);
    const auto KeepAlive=AsShared();
    if(Factory)Factory->Revoke(); // remove socket callbacks BEFORE streamer callbacks
    if(const auto S=Streamer.Pin();Installed&&S.IsValid()&&S->MikdashMatchesScope(this))S->StopStreaming();
    FCoreDelegates::OnBeginFrame.Remove(Frame);Frame.Reset();
    FCoreDelegates::OnEnginePreExit.Remove(Exit);Exit.Reset();
    // No claim that Stop/Release prove physical close. Scope remains retained by
    // the exact streamer until parent Job cleanup. Never poll a destroyed handle.
}
FMikdashOwnedConference::~FMikdashOwnedConference(){
    Wipe(Ticket);
    if(Platform&&Conference){
        const FUtf8String Id(Name);TRefCountPtr<EpicRtcConferenceInterface> Current;
        if(Platform->GetConference(ToEpicRtcStringView(Id),Current.GetInitReference())==EpicRtcErrorCode::Ok&&
           Current.GetReference()==Conference.GetReference())Platform->ReleaseConference(ToEpicRtcStringView(Id));
    }
    Conference=nullptr;Factory=nullptr;
}
EpicRtcErrorCode FMikdashOwnedFactory::CreateWebsocket(EpicRtcWebsocketInterface** Out){
    if(!Out)return EpicRtcErrorCode::InvalidArgument;*Out=nullptr;
    const auto S=Scope.Pin();
    if(Issued||!S.IsValid()||!S->Live())return EpicRtcErrorCode::GeneralError;
    Issued=true;Socket=MakeRefCount<FMikdashOwnedSocket>(Scope);Socket->AddRef();*Out=Socket.GetReference();
    return EpicRtcErrorCode::Ok;
}
EpicRtcBool FMikdashOwnedSocket::Connect(EpicRtcStringView InUrl,EpicRtcWebsocketObserverInterface* InObserver){
    if(Used||Closed||!IsInGameThread()||!InObserver||!InUrl._ptr||InUrl._length>256)return false;
    const TRefCountPtr<FMikdashOwnedSocket> KeepAlive(this);
    const auto S=Scope.Pin();TMap<FString,FString> Headers;
    if(!S.IsValid()||!S->Take(ToString(InUrl),Headers))return false;
    Used=true;Observer=InObserver;
    Socket=FWebSocketsModule::Get().CreateWebSocket(S->Url,TEXT(""),Headers);
    for(auto& Pair:Headers)Wipe(Pair.Value);Headers.Empty();
    Socket->SetTextMessageMemoryLimit(65536);
    OpenHandle=Socket->OnConnected().AddLambda([this](){
        const TRefCountPtr<FMikdashOwnedSocket> Hold(this);const auto Owner=Scope.Pin();
        if(Closed||!Owner.IsValid()||!Owner->Live()){CloseOwned();return;}
        Owner->Connected=true;const auto O=Observer;if(O)O->OnOpen();
    });
    ErrorHandle=Socket->OnConnectionError().AddLambda([this](const FString&){const TRefCountPtr<FMikdashOwnedSocket> Hold(this);CloseOwned();});
    CloseHandle=Socket->OnClosed().AddLambda([this](int32,const FString&,bool){const TRefCountPtr<FMikdashOwnedSocket> Hold(this);CloseOwned();});
    BinaryHandle=Socket->OnBinaryMessage().AddLambda([this](const void*,SIZE_T,bool){const TRefCountPtr<FMikdashOwnedSocket> Hold(this);CloseOwned();});
    MessageHandle=Socket->OnMessage().AddLambda([this](const FString& Text){
        const TRefCountPtr<FMikdashOwnedSocket> Hold(this);const auto Owner=Scope.Pin();
        if(Closed||Text.Len()>65536||!Owner.IsValid()||!Owner->Live()){CloseOwned();return;}
        const FUtf8String Bytes(Text);const auto O=Observer;
        if(Bytes.Len()>65536){CloseOwned();return;}if(O)O->OnMessage(ToEpicRtcStringView(Bytes));
    });
    if(!S->Live()){CloseOwned();return false;}
    Socket->Connect();return !Closed;
}
void FMikdashOwnedSocket::CloseOwned(){
    if(Closed)return;Closed=true;
    const auto S=Socket;const auto O=Observer;Observer=nullptr;
    if(S){S->OnConnected().Remove(OpenHandle);S->OnConnectionError().Remove(ErrorHandle);
        S->OnClosed().Remove(CloseHandle);S->OnMessage().Remove(MessageHandle);S->OnBinaryMessage().Remove(BinaryHandle);
        S->Close(1000,TEXT("Owned route closed"));}
    if(const auto Owner=Scope.Pin())Owner->Revoke();
    if(O)O->OnClosed(); // one notification; no peer-provided diagnostic logging
}
FMikdashOwnedSocket::~FMikdashOwnedSocket(){Observer=nullptr;CloseOwned();}
void FMikdashOwnedSocket::Disconnect(EpicRtcStringView){const TRefCountPtr<FMikdashOwnedSocket> Hold(this);CloseOwned();}
void FMikdashOwnedSocket::Send(EpicRtcStringView M){
    const TRefCountPtr<FMikdashOwnedSocket> Hold(this);const auto S=Scope.Pin();
    if(Closed||!M._ptr||M._length>65536||!S.IsValid()||!S->Live()||!Socket||!Socket->IsConnected()){CloseOwned();return;}
    Socket->Send(ToString(M));
}
bool MikdashAttachOwnedRtc(const TSharedPtr<IPixelStreaming2Streamer>& S,const FMikdashRtcIdentity& I,
    uint16 Port,FString Ticket,double Until,TSharedRef<const IMikdashRtcLease> Lease){
    auto* M=FModuleManager::GetModulePtr<FPixelStreaming2RTCModule>(TEXT("PixelStreaming2RTC"));
    const double N=RawQpc();
    if(!IsInGameThread()||!M||!M->IsReady()||Port<1024||!S.IsValid()||S->IsStreaming()||S->IsConnected()||
       !Token(I.Session)||!Token(I.Process)||!Token(I.Stream)||!Token(I.Save)||!Token(I.Settings)||
       !Token(I.ProcessGeneration,32)||!Token(I.Connection)||!Token(Ticket,64)||
       !FMath::IsFinite(N)||N<0||!FMath::IsFinite(I.QpcEnd)||!FMath::IsFinite(I.OwnerEnd)||
       !FMath::IsFinite(Until)||Until<=N||Until-N>5||Until>I.QpcEnd||I.QpcEnd>I.OwnerEnd||I.OwnerEnd-N>86400) {Wipe(Ticket);return false;}
    const auto Exact=M->MikdashFindCreated(S);
    if(!Exact.IsValid()||Exact->GetId()!=I.Stream||!Exact->MikdashCanAdopt()){Wipe(Ticket);return false;}
    if(OwnedAdoptionAttempts>=64){Wipe(Ticket);return false;}
    ++OwnedAdoptionAttempts; // no wrap/retry recycling even after partial acquisition
    const FString Url=FString::Printf(TEXT("wss://127.0.0.1:%u/stream/%s"),Port,*I.Stream);
    const auto Scope=MakeShared<FMikdashOwnedConference>(I,Url,MoveTemp(Ticket),Until,Exact,Lease);
    if(!Scope->Initialize()||!Exact->MikdashAdopt(Scope)){Scope->Revoke();return false;}
    Scope->Seal();return Scope->Live(); // caller's existing owned lease sets canonical URL and starts
}
void MikdashRevokeOwnedRtc(const TSharedPtr<IPixelStreaming2Streamer>& S){
    if(auto* M=FModuleManager::GetModulePtr<FPixelStreaming2RTCModule>(TEXT("PixelStreaming2RTC")))
        if(const auto Exact=M->MikdashFindCreated(S))Exact->MikdashRevoke();
}
}
