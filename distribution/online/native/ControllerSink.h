#pragma once
#include "SessionBridge.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerInput.h"
#include "InputKeyEventArgs.h"
#include "GenericPlatform/GenericPlatformInputDeviceMapper.h"

namespace MikdashOnline {
// Targets exactly one controller; never OS-wide SendInput or console execution.
// Source is staged, NOT compiled/loaded. The future host ticks bridge before
// PlayerTick and while paused. InputKey acceptance is not visual acceptance.
class ControllerSink final : public InputSink {
    TWeakObjectPtr<APlayerController> Controller;
    TWeakObjectPtr<UPlayerInput> OwnedInput;
    bool Held[7]={false,false,false,false,false,false,false};
    const FKey Keys[7]={EKeys::W,EKeys::S,EKeys::A,EKeys::D,EKeys::E,EKeys::P,EKeys::M};
    enum class Delivery { Rejected, Handled, RecordedForPolling };
    bool Available() const {
        return Controller.IsValid() && OwnedInput.IsValid() && Controller->GetWorld() &&
            Controller->PlayerInput==OwnedInput.Get();
    }
    Delivery Deliver(const FKey& K,EInputEvent Event,float Value) {
        if(!Available())return Delivery::Rejected;
        UPlayerInput* Input=OwnedInput.Get();
        const FKeyState* Before=Input->GetKeyState(K);
        const uint8 Samples=Before?Before->SampleCountAccumulator:0;
        if(Samples==255)return Delivery::Rejected;
        const FInputDeviceId Device=IPlatformInputDeviceMapper::Get().GetPrimaryInputDeviceForUser(Controller->GetPlatformUserId());
        const bool bHandled=Controller->InputKey(FInputKeyEventArgs::CreateSimulated(K,Event,Value,1,Device));
        if(!Available())return Delivery::Rejected;
        const FKeyState* After=Input->GetKeyState(K);
        // UE InputKey returns action-consumption status, NOT delivery success:
        // unbound WASD and analog samples can be recorded with a false return.
        if(!After || After->SampleCountAccumulator!=Samples+1)return Delivery::Rejected;
        return bHandled?Delivery::Handled:Delivery::RecordedForPolling;
    }
    bool Key(int Index,bool Down) {
        const EInputEvent Event=Down?(Held[Index]?IE_Repeat:IE_Pressed):IE_Released;
        if(Deliver(Keys[Index],Event,Down?1.f:0.f)==Delivery::Rejected)return false;
        Held[Index]=Down;
        return true;
    }
public:
    explicit ControllerSink(APlayerController* C):Controller(C),OwnedInput(C?C->PlayerInput.Get():nullptr) {}
    bool Release() override {
        check(IsInGameThread());
        if(!Available())return false; // do not ACK an absent/uninitialized/replaced target
        bool bReleased=true;
        for(int I=0; I<7; ++I)if(Held[I] && !Key(I,false))bReleased=false;
        if(!bReleased)return false; // rejected keys remain held for cleanup retry
        // A recorded key-up alone leaves bDown true until UE processes input.
        // Clear ONLY this bridge's whitelisted keys and pending deltas/actions
        // now, so disconnect cannot leave a queued press or look for the next tick.
        for(const FKey& K:Keys)if(FKeyState* State=OwnedInput->GetKeyState(K))*State=FKeyState();
        for(const FKey& K:{EKeys::MouseX,EKeys::MouseY})
            if(FKeyState* State=OwnedInput->GetKeyState(K))*State=FKeyState();
        return true;
    }
    bool Apply(const std::string& Action,double X,double Y) override {
        check(IsInGameThread());
        if(!Available())return false;
        if(Action=="move") {
            const bool Want[4]={Y>0.2,Y< -0.2,X< -0.2,X>0.2};
            for(int I=0;I<4;++I) {
                if((Want[I] || Held[I]) && !Key(I,Want[I]))return false;
                // Movement release must not erase a same-frame E/P/M pulse or look.
                if(!Want[I])if(FKeyState* State=OwnedInput->GetKeyState(Keys[I]))*State=FKeyState();
            }
        } else if(Action=="look") {
            if(Deliver(EKeys::MouseX,IE_Axis,float(X*100))==Delivery::Rejected)return false;
            if(Deliver(EKeys::MouseY,IE_Axis,float(Y*100))==Delivery::Rejected)return false;
        } else {
            int Index;
            if(Action=="interact")Index=4;
            else if(Action=="pause")Index=5;
            else if(Action=="mute")Index=6;
            else return false;
            if(!Key(Index,true) || !Key(Index,false))return false;
        }
        return true;
    }
};
}
