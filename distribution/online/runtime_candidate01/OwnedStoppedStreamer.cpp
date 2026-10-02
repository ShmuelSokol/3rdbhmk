#include "OwnedStoppedStreamer.h"
#include "../native/receiver03/Wire.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"

namespace MikdashOnline::RuntimeCandidate01 {
double FStoppedUEPort::Now(){return Receiver03::QpcSeconds();}
bool FStoppedUEPort::CleanupScopeValid(){
    return IsInGameThread()&&Module.IsReady()&&FSlateApplication::IsInitialized()&&!IsEngineExitRequested();
}
bool FStoppedUEPort::ScopeValid(){
    if(!CleanupScopeValid()||!GEngine||!Viewport.IsValid()||GEngine->GameViewport!=Viewport.Get())return false;
    UWorld* World=Viewport->GetWorld();
    if(!IsValid(World)||World->WorldType!=EWorldType::Game||GEngine->GetNumGamePlayers(World)!=1)return false; // no PIE/editor/split-screen sharing
    const auto Window=Viewport->GetWindow();
    const auto Windows=FSlateApplication::Get().GetTopLevelWindows();
    // Engine backbuffer factory observes every Slate window, not a player-only
    // viewport. Restrict this stopped candidate to one owned game window.
    if(!Window.IsValid()||Windows.Num()!=1||Windows[0]!=Window.ToSharedRef())return false;
    return true;
}
std::string FStoppedUEPort::DefaultId(){return TCHAR_TO_UTF8(*Module.GetDefaultStreamerID());}
bool FStoppedUEPort::Registered(const std::string& Id){
    const FString Name=UTF8_TO_TCHAR(Id.c_str());
    // Also reject stale weak registry entries; never silently reuse an old slot.
    return Module.GetStreamerIds().Contains(Name)||Module.FindStreamer(Name).IsValid();
}
FStoppedUEPort::Streamer FStoppedUEPort::Find(const std::string& Id){return Module.FindStreamer(UTF8_TO_TCHAR(Id.c_str()));}
FStoppedUEPort::Streamer FStoppedUEPort::Create(const std::string& Id){
    return Module.CreateStreamer(UTF8_TO_TCHAR(Id.c_str()),TOptional<FString>(FString(TEXT("DefaultRtc"))));
}
std::string FStoppedUEPort::Id(const Streamer& S){return TCHAR_TO_UTF8(*S->GetId());}
std::string FStoppedUEPort::Type(const Streamer& S){return TCHAR_TO_UTF8(*S->GetStreamType());}
}
