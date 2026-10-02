#pragma once
#include "CoreMinimal.h"
#include "IPixelStreaming2Module.h"
#include "IPixelStreaming2Streamer.h"
#include "StoppedLease.h"

class UGameViewportClient;

namespace MikdashOnline::RuntimeCandidate01 {
// Concrete installed-engine port. Construction opens/starts nothing. Module and
// Slate must outlive Close; quarantine must retain this owner until process exit.
class FStoppedUEPort final {
    IPixelStreaming2Module& Module;
    TWeakObjectPtr<UGameViewportClient> Viewport;
public:
    using Streamer=TSharedPtr<IPixelStreaming2Streamer>;
    using Producer=TSharedPtr<IPixelStreaming2VideoProducer>;
    FStoppedUEPort(IPixelStreaming2Module& M,UGameViewportClient* V):Module(M),Viewport(V){}
    double Now();
    bool ScopeValid();
    bool CleanupScopeValid();
    template<class T> bool Valid(const TSharedPtr<T>& V)const{return V.IsValid();}
    std::string DefaultId();
    bool Registered(const std::string& Id);
    Streamer Find(const std::string& Id);
    Streamer Create(const std::string& Id);
    std::string Id(const Streamer& S);
    std::string Type(const Streamer& S);
    bool Streaming(const Streamer& S){return S->IsStreaming();}
    bool Connected(const Streamer& S){return S->IsConnected();}
    bool UrlEmpty(const Streamer& S){return S->GetConnectionURL().IsEmpty();}
    void ClearUrl(const Streamer& S){S->SetConnectionURL(FString());}
    Producer GetProducer(const Streamer& S){return S->GetVideoProducer().Pin();}
    void SetProducer(const Streamer& S,const Producer& V){S->SetVideoProducer(V);}
    std::string Url(const Streamer& S){return TCHAR_TO_UTF8(*S->GetConnectionURL());}
    void SetUrl(const Streamer& S,const std::string& U){S->SetConnectionURL(UTF8_TO_TCHAR(U.c_str()));}
    void Start(const Streamer& S){S->StartStreaming();}
    void Stop(const Streamer& S){S->StopStreaming();}
    void Remove(const Streamer& S){Module.DeleteStreamer(S);}
};

class FOwnedStoppedStreamer final {
    FStoppedUEPort Port;
    StoppedLease<FStoppedUEPort> Lease;
public:
    FOwnedStoppedStreamer(IPixelStreaming2Module& M,UGameViewportClient* V):Port(M,V),Lease(Port){}
    bool Prepare(const Owner& Expected,double NativeQpcDeadline){check(IsInGameThread());return Lease.Prepare(Expected,NativeQpcDeadline);}
    TSharedPtr<IPixelStreaming2Streamer> BorrowStopped(const Owner& Expected){check(IsInGameThread());return Lease.BorrowStopped(Expected);}
    bool Matches(const Owner& Parsed){check(IsInGameThread());return Lease.Matches(Parsed);}
    bool StartOwnedMedia(const Owner& O,const std::string& U){check(IsInGameThread());return Lease.StartOwnedMedia(O,U);}
    bool Close(){check(IsInGameThread());return Lease.Close();}
    auto GetState()const{return Lease.GetState();}
    // No destructor-driven virtual calls into a possibly unloaded module. Host
    // must call Close before destroying Slate/module; false retains allocation.
};
}
