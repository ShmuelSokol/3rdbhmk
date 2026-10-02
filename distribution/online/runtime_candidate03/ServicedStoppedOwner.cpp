#include "ServicedStoppedOwner.h"
#include "../native/receiver03/Wire.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "Misc/CoreDelegates.h"
#include "Templates/UnrealTemplate.h"

namespace MikdashOnline::RuntimeCandidate03 {
FServicedStoppedOwner::FServicedStoppedOwner(IPixelStreaming2Module& M,
    UGameViewportClient* V,TSharedRef<Receiver04::Bootstrap> R)
    :Lease(M,V),Receiver(R),Viewport(V) {}

TSharedRef<FServicedStoppedOwner> FServicedStoppedOwner::Create(IPixelStreaming2Module& M,
    UGameViewportClient* V,TSharedRef<Receiver04::Bootstrap> R,const Owner& O,double D) {
    check(IsInGameThread());
    TSharedRef<FServicedStoppedOwner> Self=MakeShareable(new FServicedStoppedOwner(M,V,R));
    Self->Identity=O;
    if(IsValid(V)) { Self->World=V->GetWorld(); Self->Window=V->GetWindow(); }
    // Native raw QPC deadline only; never Python monotonic or FPlatformTime.
    // Receiver04's private bootstrap must use an equal or earlier deadline.
    const bool ValidDeadline=Self->Expiry.Begin(Receiver03::QpcSeconds(),D,O.expires_at);
    if(ValidDeadline&&Self->ScopeAndTime()&&Self->Lease.Prepare(O,D)) {
        Self->Streamer=Self->Lease.BorrowStopped(O);
        if(Self->Streamer.IsValid()&&Self->ScopeAndTime()) Self->Phase=State::Ready;
    }
    if(Self->Phase!=State::Ready) Self->Shutdown();
    Self->Arm(); // pins quarantine too, even if caller drops returned reference
    return Self;
}

bool FServicedStoppedOwner::ScopeAndTime() {
    const double N=Receiver03::QpcSeconds();
    // No catch-up/retry. A stalled frame loop invalidates the lease on resumption.
    if(!Expiry.Observe(N)) return false;
    if(!Viewport.IsValid()||!World.IsValid()||!Window.IsValid()||!GEngine||
       GEngine->GameViewport!=Viewport.Get()||Viewport->GetWorld()!=World.Get()||
       Viewport->GetWindow()!=Window.Pin()||!FSlateApplication::IsInitialized()||
       IsEngineExitRequested()) return false;
    const auto& Windows=FSlateApplication::Get().GetTopLevelWindows();
    return Windows.Num()==1&&Windows[0]==Window.Pin().ToSharedRef();
}

TSharedPtr<IPixelStreaming2Streamer> FServicedStoppedOwner::BorrowStopped(const Owner& O) {
    check(IsInGameThread());
    if(Busy||Phase!=State::Ready||RevokeRequested||!(Identity==O)) return {};
    TSharedPtr<IPixelStreaming2Streamer> Result;
    {
        TGuardValue<bool> Guard(Busy,true);
        if(ScopeAndTime()) Result=Lease.BorrowStopped(O);
        // Callbacks may revoke or consume the deadline. Never hand out that result.
        if(RevokeRequested||!ScopeAndTime()) Result.Reset();
    }
    if(!Result.IsValid()) Shutdown();
    return Result;
}

void FServicedStoppedOwner::ServiceFrame() {
    check(IsInGameThread());
    if(Phase!=State::Ready||Busy) return;
    if(!BorrowStopped(Identity).IsValid()) return; // shutdown already attempted
    // Only the real owner frame loop may complete a successful service interval.
    if(!Expiry.CompleteFrame(Receiver03::QpcSeconds())) Shutdown();
}

bool FServicedStoppedOwner::Shutdown() {
    check(IsInGameThread());
    RevokeRequested=true; // revoke before ANY receiver/streamer callback
    Expiry.Revoke();
    if(Busy) return false;
    if(Phase==State::Closed) return true;
    if(Phase==State::Quarantined) return false;
    TGuardValue<bool> Guard(Busy,true); Phase=State::Closing;
    // Observe prohibited media activity BEFORE Shutdown can clear status flags.
    const bool MediaObserved=Streamer.IsValid()&&(Streamer->IsStreaming()||Streamer->IsConnected());
    const bool ReceiverClosed=Receiver->Shutdown();
    if(!ReceiverClosed||MediaObserved) { Phase=State::Quarantined; return false; }
    if(!Lease.Close()) { Phase=State::Quarantined; return false; }
    Streamer.Reset(); Phase=State::Closed; Disarm(); return true;
}

void FServicedStoppedOwner::Arm() {
    if(Phase==State::Closed) return;
    // Strong captures intentionally retain failed cleanup until owned process exit.
    // Each invocation makes a local pin before possibly removing its own delegate.
    const auto Self=AsShared();
    FrameHandle=FCoreDelegates::OnBeginFrame.AddLambda([Self]() {
        const auto KeepAlive=Self; KeepAlive->ServiceFrame();
    });
    ExitHandle=FCoreDelegates::OnEnginePreExit.AddLambda([Self]() {
        const auto KeepAlive=Self; KeepAlive->Shutdown();
    });
}
void FServicedStoppedOwner::Disarm() {
    FCoreDelegates::OnBeginFrame.Remove(FrameHandle); FrameHandle.Reset();
    FCoreDelegates::OnEnginePreExit.Remove(ExitHandle); ExitHandle.Reset();
}
}
