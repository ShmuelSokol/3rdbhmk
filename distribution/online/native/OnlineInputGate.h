#pragma once
#include "IPixelStreaming2InputHandler.h"
#include "IPixelStreaming2Streamer.h"

// Install BEFORE the first peer connects. Never forward OnMessage or command handlers.
// Keep original handler private for protocol metadata ONLY; no Tick drains its queue.
class FOnlineInputGate final : public IPixelStreaming2InputHandler {
    TSharedPtr<IPixelStreaming2DataProtocol> ToProtocol, FromProtocol;
    explicit FOnlineInputGate(TSharedPtr<IPixelStreaming2DataProtocol> To, TSharedPtr<IPixelStreaming2DataProtocol> From)
        :ToProtocol(To),FromProtocol(From) {}
public:
    static TSharedPtr<FOnlineInputGate> Install(const TSharedPtr<IPixelStreaming2Streamer>& Streamer) {
        check(IsInGameThread());
        if(!Streamer.IsValid() || Streamer->IsStreaming() || Streamer->GetStreamType()!=TEXT("DefaultRtc"))return nullptr;
        auto Original=Streamer->GetInputHandler().Pin();
        if(!Original.IsValid())return nullptr;
        auto To=Original->GetToStreamerProtocol(), From=Original->GetFromStreamerProtocol();
        if(!To.IsValid() || !From.IsValid())return nullptr;
        for(const TCHAR* Name : {TEXT("Multiplexed"),TEXT("ChannelRelayStatus"),TEXT("LatencyTest"),
                TEXT("RequestInitialSettings"),TEXT("IFrameRequest"),TEXT("TestEcho")})
            if(!To->Find(Name).IsValid())return nullptr;
        TSharedPtr<FOnlineInputGate> Gate=MakeShareable(new FOnlineInputGate(To,From));
        Streamer->SetInputHandler(Gate);
        if(Streamer->GetInputHandler().Pin()!=Gate)return nullptr;
        return Gate;
    }
    void OnMessage(FString SourceId, TArray<uint8> Buffer) override {  }
    void SetTargetViewport(TWeakPtr<SViewport> InTargetViewport) override {  }
    TWeakPtr<SViewport> GetTargetViewport() override { return {}; }
    void SetTargetWindow(TWeakPtr<SWindow> InTargetWindow) override {  }
    TWeakPtr<SWindow> GetTargetWindow() override { return {}; }
    void SetTargetScreenRect(TWeakPtr<FIntRect> InTargetScreenRect) override {  }
    TWeakPtr<FIntRect> GetTargetScreenRect() override { return {}; }
    bool IsFakingTouchEvents() const override { return false; }
    void RegisterMessageHandler(const FString& MessageType, const MessageHandlerFn& Handler) override {  }
    void SetCommandHandler(const FString& CommandName, const CommandHandlerFn& Handler) override {  }
    void SetElevatedCheck(const TFunction<bool(FString)>& CheckFn) override {  }
    bool IsElevated(const FString& Id) override { return false; }
    MessageHandlerFn FindMessageHandler(const FString& MessageType) override { return {}; }
    TSharedPtr<IPixelStreaming2DataProtocol> GetToStreamerProtocol() override { return ToProtocol; }
    TSharedPtr<IPixelStreaming2DataProtocol> GetFromStreamerProtocol() override { return FromProtocol; }
    void SetInputType(EPixelStreaming2InputType InputType) override {  }
    bool OnKeyChar(TCHAR Character) override { return false; }
    bool OnKeyDown(FKey Key, bool bIsRepeat) override { return false; }
    bool OnKeyUp(FKey Key) override { return false; }
    bool OnMouseEnter() override { return false; }
    bool OnMouseLeave() override { return false; }
    bool OnMouseDown(EMouseButtons::Type Button, FIntPoint ScreenPosition) override { return false; }
    bool OnMouseUp(EMouseButtons::Type Button) override { return false; }
    bool OnMouseMove(FIntPoint ScreenPosition, FIntPoint Delta) override { return false; }
    bool OnMouseWheel(FIntPoint ScreenPosition, float MouseWheelDelta) override { return false; }
    bool OnMouseDoubleClick(EMouseButtons::Type Button, FIntPoint ScreenPosition) override { return false; }
    bool OnTouchStarted(FIntPoint TouchPosition, int32 TouchIndex, float Force) override { return false; }
    bool OnTouchMoved(FIntPoint TouchPosition, int32 TouchIndex, float Force) override { return false; }
    bool OnTouchEnded(FIntPoint TouchPosition, int32 TouchIndex) override { return false; }
    uint8 OnControllerConnected() override { return 255; }
    bool OnControllerAnalog(uint8 ControllerIndex, FKey Axis, double AxisValue) override { return false; }
    bool OnControllerButtonPressed(uint8 ControllerIndex, FKey Key, bool bIsRepeat) override { return false; }
    bool OnControllerButtonReleased(uint8 ControllerIndex, FKey Key) override { return false; }
    bool OnControllerDisconnected(uint8 ControllerIndex) override { return false; }
    bool OnXREyeViews(FTransform LeftEyeTransform, FMatrix LeftEyeProjectionMatrix, FTransform RightEyeTransform, FMatrix RightEyeProjectionMatrix, FTransform HMDTransform) override { return false; }
    bool OnXRHMDTransform(FTransform HMDTransform) override { return false; }
    bool OnXRControllerTransform(FTransform ControllerTransform, EControllerHand Handedness) override { return false; }
    bool OnXRButtonTouched(EControllerHand Handedness, FKey Key, bool bIsRepeat) override { return false; }
    bool OnXRButtonTouchReleased(EControllerHand Handedness, FKey Key) override { return false; }
    bool OnXRButtonPressed(EControllerHand Handedness, FKey Key, bool bIsRepeat) override { return false; }
    bool OnXRButtonReleased(EControllerHand Handedness, FKey Key) override { return false; }
    bool OnXRAnalog(EControllerHand Handedness, FKey Key, double AnalogValue) override { return false; }
    bool OnXRSystem(EPixelStreaming2XRSystem System) override { return false; }
    void Tick(float) override {}
    void SendControllerEvents() override {}
    void SetMessageHandler(const TSharedRef<FGenericApplicationMessageHandler>&) override {}
    bool Exec(UWorld*, const TCHAR*, FOutputDevice&) override { return false; }
    void SetChannelValue(int32, FForceFeedbackChannelType, float) override {}
    void SetChannelValues(int32, const FForceFeedbackValues&) override {}
};
