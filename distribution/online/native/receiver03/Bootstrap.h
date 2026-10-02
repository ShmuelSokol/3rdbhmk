#pragma once
#include "Receiver.h"
#include "../ControllerSink.h"
#include "../OnlineInputGate.h"

namespace MikdashOnline::Receiver03 {
// Explicit owner-module lifecycle, not a plugin or auto-start hook. Start and Poll
// must run on game thread, including while paused, before normal input processing.
class RuntimeBootstrap {
    TWeakObjectPtr<APlayerController> Controller;
    TSharedPtr<IPixelStreaming2Streamer> Streamer;
    TSharedPtr<FOnlineInputGate> Gate;
    TUniquePtr<ControllerSink> Sink;
    TUniquePtr<Service> Authority;
    TUniquePtr<Receiver> Server;
    void* InputHandle=nullptr;
    TArray<uint8> Bytes;
    int32 Expected=4;double Deadline=0;
    bool Started=false,Stopping=false,Ready=false;
    bool StreamStopRequested=false,OwnerVerified=false;
    FDelegateHandle TickHandle;
    void CloseInput();
public:
    RuntimeBootstrap()=default;
    ~RuntimeBootstrap();
    bool Start(APlayerController* OwnedController,const TSharedPtr<IPixelStreaming2Streamer>& OwnedStreamer);
    void Poll();
    bool IsReady() const{return Ready&&!Stopping;}
    // Caller must retain this object/quarantine process if false. The gate is
    // never restored to the default input handler, even after shutdown.
    bool Shutdown();
};
}
