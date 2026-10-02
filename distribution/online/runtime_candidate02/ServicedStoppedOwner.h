#pragma once
#include "../runtime_candidate01/OwnedStoppedStreamer.h"
#include "../native/receiver04/Bootstrap.h"

class SWindow;
class UWorld;

namespace MikdashOnline::RuntimeCandidate02 {
// Stopped-only owner. Explicit Create registers frame/exit callbacks but starts
// no receiver or media. Host MUST exclusively serialize streamer registry writes.
class FServicedStoppedOwner final : public TSharedFromThis<FServicedStoppedOwner> {
public:
    enum class State { Preparing, Ready, Closing, Closed, Quarantined };
    static TSharedRef<FServicedStoppedOwner> Create(IPixelStreaming2Module& Module,
        UGameViewportClient* Viewport, TSharedRef<Receiver04::Bootstrap> Receiver,
        const Owner& Identity, double NativeQpcDeadline);
    TSharedPtr<IPixelStreaming2Streamer> BorrowStopped(const Owner& Identity);
    bool Matches(const Owner& Identity) { return BorrowStopped(Identity).IsValid(); }
    bool Shutdown(); // call BEFORE Slate/PixelStreaming module teardown
    State GetState() const { return Phase; }
private:
    FServicedStoppedOwner(IPixelStreaming2Module& Module, UGameViewportClient* Viewport,
        TSharedRef<Receiver04::Bootstrap> Receiver);
    RuntimeCandidate01::FOwnedStoppedStreamer Lease;
    TSharedRef<Receiver04::Bootstrap> Receiver;
    TWeakObjectPtr<UGameViewportClient> Viewport;
    TWeakObjectPtr<UWorld> World;
    TWeakPtr<SWindow> Window;
    TSharedPtr<IPixelStreaming2Streamer> Streamer;
    Owner Identity;
    double Deadline=0, LastService=-1;
    State Phase=State::Preparing;
    bool Busy=false, RevokeRequested=false;
    FDelegateHandle FrameHandle, ExitHandle;
    bool ScopeAndTime();
    void ServiceFrame();
    void Arm();
    void Disarm();
};
}
