#pragma once
#include "../native/receiver04/OnlineController.h"
#include "../native/receiver04/Authority.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerInput.h"

namespace MikdashOnline::Interaction01 {
inline Receiver04::Outcome ConsumeResidentInteraction(AReceiver04Controller& Controller,
    TSharedRef<Receiver04::Authority> Service,const Receiver04::SemanticMailbox::Fence& Fence) {
    check(IsInGameThread());
    using Receiver04::Outcome;
    const TWeakObjectPtr<AReceiver04Controller> Weak=&Controller;
    const TWeakObjectPtr<APawn> Pawn=Controller.GetPawn();
    const TWeakObjectPtr<UPlayerInput> Input=Controller.PlayerInput.Get();
    const TWeakObjectPtr<UWorld> World=Controller.GetWorld();
    auto StillOwned=[&]() {
        if(!Weak.IsValid()||!Pawn.IsValid()||!Input.IsValid()||!World.IsValid()) return false;
        auto* C=Weak.Get();
        if(C->GetPawn()!=Pawn.Get()||Pawn->GetController()!=C||C->PlayerInput!=Input.Get()||
           C->GetWorld()!=World.Get()||Pawn->GetWorld()!=World.Get()||!C->IsLocalController()||
           C->IsPaused()||C->IsWalkthroughMenuOpen()||C->IsDoveFlightActive()||Service->IsClosed()) return false;
        const auto Current=Service->Consumers().CurrentFence();
        return Service->BoundContext()==Fence.context&&Current.context==Fence.context&&
            Current.epoch==Fence.epoch&&Current.until==Fence.until;
    };
    if(!StillOwned()) return Outcome::Rejected;
    const auto Result=Controller.TryTalkToNearbyResident([&]() {
        // The project calls this AFTER its resident scan, at the last branch.
        return StillOwned()&&Service->Consumers().Revalidate(Fence);
    });
    // Revalidate identity/pause/possession after the callback WITHOUT refreshing
    // AuthorizationAt after the effect. Mailbox::Complete owns final deadline/ACK.
    if(!StillOwned()) {
        Service->Abort();
        return Result==MikdashDialog::TalkOutcome::Applied||Result==MikdashDialog::TalkOutcome::Unknown
            ?Outcome::Unknown:Outcome::Rejected;
    }
    switch(Result) {
        case MikdashDialog::TalkOutcome::Applied:return Outcome::Applied;
        case MikdashDialog::TalkOutcome::NoOp:return Outcome::NoOp;
        case MikdashDialog::TalkOutcome::Rejected:return Outcome::Rejected;
        default:return Outcome::Unknown;
    }
}
}
