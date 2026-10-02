#include "Bootstrap.h"
#include "Windows/WindowsHWrapper.h"
#include "Misc/CoreDelegates.h"
#include "BootstrapGuards.h"
#include "GameFramework/PlayerInput.h"

namespace MikdashOnline::Receiver04 {
Bootstrap::~Bootstrap(){Shutdown();FCoreDelegates::OnBeginFrame.Remove(TickHandle);}
bool Bootstrap::CloseInput(){
    if(Bytes.Num())::SecureZeroMemory(Bytes.GetData(),Bytes.Num());Bytes.Reset();
    const bool Closed=CloseBootstrapInput(Input,InputPoisoned,[](void* H){return ::CloseHandle(static_cast<HANDLE>(H))!=0;});
    if(!Closed)Stopping=true;
    return Closed;
}
bool Bootstrap::Start(AReceiver04Controller* C,TSharedPtr<IPixelStreaming2Streamer> S,
    TFunction<bool(const Owner&)> Settings,TFunction<Outcome(const SemanticMailbox::Fence&)> ConsumeInteract,double Degrees){
    check(IsInGameThread());
    if(Started||Stopping||!IsValid(C)||!C->PlayerInput||!IsValid(C->GetPawn())||!S.IsValid()||!Settings||
       !FMath::IsFinite(Degrees)||Degrees<=0||Degrees>180)return false;
    Started=true;Controller=C;Streamer=S;SettingsProof=MoveTemp(Settings);Interact=MoveTemp(ConsumeInteract);LookDegrees=Degrees;
    Gate=FOnlineInputGate::Install(S);if(!Gate.IsValid()){Stopping=true;return false;}
    HANDLE H=::GetStdHandle(STD_INPUT_HANDLE);
    if(!H||H==INVALID_HANDLE_VALUE||::GetFileType(H)!=FILE_TYPE_PIPE){Stopping=true;return false;}
    Input=H;ReadEnd=Receiver03::QpcSeconds()+5;
    if(ReadEnd<5){Shutdown();return false;}
    TickHandle=FCoreDelegates::OnBeginFrame.AddRaw(this,&Bootstrap::Poll);return true;
}
void Bootstrap::Poll(){
    check(IsInGameThread());
    if(Stopping){Shutdown();return;}
    if(Server){Server->Tick();if(Service->IsClosed())Shutdown();return;}
    if(!Input||!Started)return;
    const double N=Receiver03::QpcSeconds();
    if(N<0||N>=ReadEnd){Shutdown();return;}
    DWORD Available=0;
    if(!::PeekNamedPipe(static_cast<HANDLE>(Input),nullptr,0,nullptr,&Available,nullptr)){Shutdown();return;}
    if(!Available)return;
    uint8 Buffer[4096];DWORD Read=0;
    const DWORD Want=FMath::Min<DWORD>(Available,Expected-Bytes.Num());
    if(Want==0||Want>4096||!::ReadFile(static_cast<HANDLE>(Input),Buffer,Want,&Read,nullptr)||!Read){Shutdown();return;}
    Bytes.Append(Buffer,Read);::SecureZeroMemory(Buffer,sizeof(Buffer));
    if(Bytes.Num()==4&&Expected==4){
        const uint32 Size=(uint32(Bytes[0])<<24)|(uint32(Bytes[1])<<16)|(uint32(Bytes[2])<<8)|Bytes[3];
        if(Size<2||Size>4092){Shutdown();return;}Expected=int32(Size)+4;return;
    }
    if(Bytes.Num()!=Expected)return;
    Receiver03::Bootstrap Config;TArray<uint8> Body;Body.Append(Bytes.GetData()+4,Bytes.Num()-4);
    const bool Parsed=Receiver03::ParseBootstrap(Body,Config);::SecureZeroMemory(Body.GetData(),Body.Num());
    if(!CloseInput()){Shutdown();return;}
    const double Fresh=Receiver03::QpcSeconds();
    if(!Parsed||Fresh<0||Config.Deadline<=Fresh||Config.Deadline>Config.Identity.expires_at||Config.Deadline-Fresh>86400||
       !Controller.IsValid()||!Streamer.IsValid()||Streamer->GetId()!=UTF8_TO_TCHAR(Config.Identity.stream_id.c_str())){Shutdown();return;}
    OwnerVerified=true;
    const TWeakObjectPtr<APawn> ExpectedPawn=Controller->GetPawn();
    const TWeakObjectPtr<UPlayerInput> ExpectedInput=Controller->PlayerInput.Get();
    if(!SettingsProof(Config.Identity)){Shutdown();return;}
    // Trusted callbacks may still destroy/repossess/reinitialize native objects.
    // Recheck before any dereference/configuration, including the same pawn/input.
    if(!BootstrapTargetsValid(Controller,ExpectedPawn,ExpectedInput,Streamer,Config.Deadline,
                             [](){return Receiver03::QpcSeconds();})){Shutdown();return;}
    // One authority per owned Windows process, exact weak objects checked at all
    // consumer boundaries. IDs are native incarnations, never remotely supplied.
    Service=MakeShared<Authority>(Config,1,2,[](){return Receiver03::QpcSeconds();});
    const Owner OwnedIdentity=Config.Identity;
    if(!Controller->ConfigureRemote(Service,[Proof=SettingsProof,OwnedIdentity](){return Proof(OwnedIdentity);},Interact,LookDegrees)){
        Shutdown();return;
    }
    auto* Movement=Controller->GetPawn()->GetMovementComponent();bool Bound=false;
    if(auto* Walker=Cast<UReceiver04WalkerMovement>(Movement))Bound=Walker->ConfigureRemote(Service,Controller.Get());
    else if(auto* Dove=Cast<UReceiver04DoveMovement>(Movement))Bound=Dove->ConfigureRemote(Service,Controller.Get());
    if(!Bound||Service->IsClosed()||Receiver03::QpcSeconds()>=Config.Deadline){Shutdown();return;}
    Server=MakeUnique<Receiver>(*Service);
    if(!Server->Start(Config.Port)){Shutdown();return;}Ready=true;
    // Do NOT start media here: authenticated exact-route streamer attachment is
    // a separate missing integration, never an unauthenticated URL fallback.
}
bool Bootstrap::Shutdown(){
    check(IsInGameThread());Stopping=true;Ready=false;
    const bool InputClosed=CloseInput();
    if(Service.IsValid())Service->Abort();
    if(OwnerVerified&&Streamer.IsValid())Streamer->StopStreaming();
    const bool ServerClosed=!Server||Server->Shutdown();
    const bool StreamClosed=!OwnerVerified||!Streamer.IsValid()||!Streamer->IsStreaming();
    // Failed stdin CloseHandle is permanently quarantined; never retry a numeric
    // handle that might have been invalidated/reused. Exact job exit proves final
    // cleanup externally. Independent server/media cleanup still runs above.
    if(!InputClosed||!ServerClosed||!StreamClosed)return false;
    FCoreDelegates::OnBeginFrame.Remove(TickHandle);TickHandle.Reset();Server.Reset();
    return true;
}
}
