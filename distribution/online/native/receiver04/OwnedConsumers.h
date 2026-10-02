#pragma once
#include "Authority.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"

namespace MikdashOnline::Receiver04 {
// Glue for NEW controller/movement overrides. Does not alter existing project
// classes, bind delegates, install a tick or start any service by construction.
// Owner IDs are minted once by trusted native bootstrap, never GetUniqueID alone.
class OwnedConsumers {
    Authority& Service;
    TWeakObjectPtr<APlayerController> Controller;
    TWeakObjectPtr<APawn> Pawn;
    bool Valid(){
        if(!Controller.IsValid()||!Pawn.IsValid()||Controller->GetPawn()!=Pawn.Get()||
           Pawn->GetController()!=Controller.Get()||!Controller->IsLocalController()){
            Service.Abort();return false;
        }
        return !Service.IsClosed();
    }
public:
    OwnedConsumers(Authority& S,APlayerController* C,APawn* P):Service(S),Controller(C),Pawn(P){}
    // Invoke from the actual PostProcessInput override AFTER Super; provide a
    // project action dispatcher with explicit Applied/NoOp/Rejected outcomes.
    // It must check exact owner/deadline again at any later state-changing branch
    // if it performs potentially blocking work before that branch.
    template<class Action> void PostProcessInput(bool Paused,Action Consume){
        if(!Valid())return;
        Service.Consumers().PostProcessInput(Service.BoundContext(),Paused,Consume);
    }
    // Invoke at UpdateRotation's final semantic rotation input boundary. Consume
    // must commit once here, not add a future MouseX/Y or RotationInput sample.
    template<class Look> void UpdateRotation(bool Paused,Look Consume){
        if(!Valid())return;
        Service.Consumers().UpdateRotation(Service.BoundContext(),Paused,Consume);
    }
    // CharacterMovement::ControlledCharacterMove: leave the consumed local vector
    // unchanged until this hook merges remote at acceleration evaluation. Heading
    // is sampled by the callback at consumption, never at network dispatch.
    template<class Merge> void WalkerControlledCharacterMove(bool Paused,Merge Consume){
        if(!Valid())return;
        Service.Consumers().ConsumeMovement(Service.BoundContext(),Paused,Consume);
    }
    // IMPORTANT: UFloatingPawnMovement evaluates GetPendingInputVector BEFORE
    // calling ConsumeInputVector merely to clear it. Overriding that clear call
    // would ACK discarded input. The dove override must use this hook in its
    // ApplyControlInputToVelocity evaluation, AFTER any potentially slow obstacle
    // sweep and immediately before evaluating remote acceleration. Keep remote
    // contribution out of AddInputVector and retain the existing steering policy.
    template<class Evaluate> void DoveApplyControlInputToVelocity(bool Paused,Evaluate Consume){
        if(!Valid())return;
        Service.Consumers().ConsumeMovement(Service.BoundContext(),Paused,Consume);
    }
    // Disconnect and unpossess clear remote mailbox only; preserve all local
    // UPlayerInput, RotationInput and pawn pending input contributions.
    void Disconnect(){Service.Abort();}
};
}
