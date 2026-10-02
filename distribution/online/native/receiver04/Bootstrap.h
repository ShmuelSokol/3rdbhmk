#pragma once
#include "Receiver.h"
#include "OnlineController.h"
#include "OnlineMovement.h"
#include "../OnlineInputGate.h"

namespace MikdashOnline::Receiver04 {
// Explicit future module integration operation only. Import/construct starts
// nothing. Requires receiver04 controller AND movement classes already installed.
class Bootstrap {
    TWeakObjectPtr<AReceiver04Controller> Controller;
    TSharedPtr<IPixelStreaming2Streamer> Streamer;
    TSharedPtr<FOnlineInputGate> Gate;
    TSharedPtr<Authority> Service;
    TUniquePtr<Receiver> Server;
    TFunction<bool(const Owner&)> SettingsProof;
    TFunction<Outcome(const SemanticMailbox::Fence&)> Interact;
    TArray<uint8> Bytes;
    int32 Expected=4;
    void* Input=nullptr;
    double ReadEnd=0,LookDegrees=0;
    bool Started=false,Stopping=false,OwnerVerified=false,Ready=false,InputPoisoned=false;
    FDelegateHandle TickHandle;
    bool CloseInput();
    void Poll();
public:
    ~Bootstrap();
    bool Start(AReceiver04Controller* C,TSharedPtr<IPixelStreaming2Streamer> S,
               TFunction<bool(const Owner&)> Settings,TFunction<Outcome(const SemanticMailbox::Fence&)> ConsumeInteract,
               double DegreesPerUnit);
    bool IsReady()const{return Ready&&!Stopping;}
    TSharedPtr<Authority> GetAuthority()const{return Service;}
    bool Shutdown();
};
}
