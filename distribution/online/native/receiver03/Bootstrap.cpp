#include "Bootstrap.h"
#include "Windows/WindowsHWrapper.h"
#include "Misc/CoreDelegates.h"

namespace MikdashOnline::Receiver03 {
RuntimeBootstrap::~RuntimeBootstrap(){Shutdown();FCoreDelegates::OnBeginFrame.Remove(TickHandle);}
void RuntimeBootstrap::CloseInput(){
    if(InputHandle){::CloseHandle(static_cast<HANDLE>(InputHandle));InputHandle=nullptr;}
    if(Bytes.Num())::SecureZeroMemory(Bytes.GetData(),Bytes.Num());Bytes.Reset();
}
bool RuntimeBootstrap::Start(APlayerController* C,const TSharedPtr<IPixelStreaming2Streamer>& S){
    check(IsInGameThread());
    if(Started||Stopping||!IsValid(C)||!IsValid(C->PlayerInput)||!S.IsValid())return false;
    Started=true;Controller=C;Streamer=S;
    Gate=FOnlineInputGate::Install(S);if(!Gate.IsValid()){Stopping=true;return false;}
    HANDLE H=::GetStdHandle(STD_INPUT_HANDLE);
    if(!H||H==INVALID_HANDLE_VALUE||::GetFileType(H)!=FILE_TYPE_PIPE){Stopping=true;return false;}
    // Only the child's explicitly inherited private STDIN read handle is used.
    // No config/environment/command-line secret fallback and no filesystem key.
    InputHandle=H;Deadline=QpcSeconds()+5;
    if(Deadline<5){Shutdown();return false;}
    TickHandle=FCoreDelegates::OnBeginFrame.AddRaw(this,&RuntimeBootstrap::Poll);
    return true;
}
void RuntimeBootstrap::Poll(){
    check(IsInGameThread());
    if(Stopping){Shutdown();return;}
    if(Server){Server->Tick();if(Authority->IsStopping())Shutdown();return;}
    if(!Started||!InputHandle)return;
    const double Now=QpcSeconds();
    if(Now<0||Now>=Deadline){Shutdown();return;}
    DWORD Available=0;
    if(!::PeekNamedPipe(static_cast<HANDLE>(InputHandle),nullptr,0,nullptr,&Available,nullptr)){Shutdown();return;}
    if(!Available)return;
    // One bounded read of already available bytes: never block the game thread.
    uint8 Buffer[4096];DWORD Read=0;
    const DWORD Want=FMath::Min<DWORD>(Available,FMath::Min<int32>(sizeof(Buffer),Expected-Bytes.Num()));
    if(!Want||!::ReadFile(static_cast<HANDLE>(InputHandle),Buffer,Want,&Read,nullptr)||Read==0){Shutdown();return;}
    Bytes.Append(Buffer,Read);::SecureZeroMemory(Buffer,sizeof(Buffer));
    if(Bytes.Num()==4&&Expected==4){
        const uint32 Size=(uint32(Bytes[0])<<24)|(uint32(Bytes[1])<<16)|(uint32(Bytes[2])<<8)|Bytes[3];
        if(Size<2||Size>4092){Shutdown();return;}Expected=int32(Size)+4;return;
    }
    if(Bytes.Num()!=Expected)return;
    Bootstrap Config;TArray<uint8> Body;Body.Append(Bytes.GetData()+4,Bytes.Num()-4);
    const bool Valid=ParseBootstrap(Body,Config);::SecureZeroMemory(Body.GetData(),Body.Num());CloseInput();
    const double Fresh=QpcSeconds();
    if(!Valid||Fresh<0||Config.Deadline<=Fresh||Config.Deadline>Config.Identity.expires_at||Config.Deadline-Fresh>86400||!Controller.IsValid()||
       !Streamer.IsValid()||Streamer->GetId()!=UTF8_TO_TCHAR(Config.Identity.stream_id.c_str())){Shutdown();return;}
    OwnerVerified=true;
    Sink=MakeUnique<ControllerSink>(Controller.Get());
    if(!Sink->Release()){Shutdown();return;}
    Authority=MakeUnique<Service>(Config,*Sink,[](){return QpcSeconds();});
    Server=MakeUnique<Receiver>(*Authority);
    if(!Server->Start(Config.Port)){Shutdown();return;}
    Ready=true;
}
bool RuntimeBootstrap::Shutdown(){
    check(IsInGameThread());Stopping=true;Ready=false;CloseInput();
    if(OwnerVerified&&Streamer.IsValid()&&!StreamStopRequested){StreamStopRequested=true;Streamer->StopStreaming();}
    if(Server&&!Server->Shutdown())return false;
    if(Authority&&!Authority->Shutdown())return false;
    if(!Authority&&Sink&&!Sink->Release())return false;
    if(OwnerVerified&&Streamer.IsValid()&&Streamer->IsStreaming())return false;
    FCoreDelegates::OnBeginFrame.Remove(TickHandle);TickHandle.Reset();
    Server.Reset();Authority.Reset();Sink.Reset();return true;
}
}
