#include "OnlineController.h"
#include "../../runtime_settings05/NativeLease.h"
#include "../../runtime_interaction01/RemoteResidentInteraction.h"
#include "Camera/PlayerCameraManager.h"
#include "Camera/CameraModifier.h"
#include "Camera/CameraModifier_CameraShake.h"
#include "Engine/Engine.h"
#include "GameFramework/Pawn.h"

using namespace MikdashOnline::Receiver04;
bool AReceiver04Controller::ValidRemote(){
    if(!Remote.IsValid())return false;
    if(FlightTransition)return false;
    if(!OwnedPawn.IsValid()||GetPawn()!=OwnedPawn.Get()||OwnedPawn->GetController()!=this||!IsLocalController()){
        Remote->Abort();return false;
    }
    return !Remote->IsClosed();
}
bool AReceiver04Controller::ConfigureRemote(TSharedPtr<Authority> S,TFunction<bool()> Settings,
    TFunction<Outcome(const SemanticMailbox::Fence&)> Interact,double Degrees){
    if(!SupportedInitialWalker()||Remote.IsValid()||!S.IsValid()||!IsValid(GetPawn())||!IsLocalController()||!PlayerInput||
       !Settings||!FMath::IsFinite(Degrees)||Degrees<=0||Degrees>180)return false;
    // Real private-v2 lease overrides any caller-supplied settings predicate.
    // No configured input authority without the exact authenticated process owner.
    if(S->IsClosed()||!MikdashOnline::Settings05::FindLease(S->BoundOwner()).IsValid())return false;
    Settings=MikdashOnline::Settings05::MakeOwnedSettingsCallback(S->BoundOwner(),this);
    Remote=MoveTemp(S);OwnedPawn=GetPawn();SettingsOwned=MoveTemp(Settings);
    ConsumeInteract=MoveTemp(Interact);LookDegrees=Degrees;return true;
}
void AReceiver04Controller::PostProcessInput(float Dt,bool GamePaused){
    Super::PostProcessInput(Dt,GamePaused);
    if(!ValidRemote())return;
    Remote->Consumers().PostProcessInput(Remote->BoundContext(),GamePaused||IsWalkthroughMenuOpen(),
        [&](const std::string& Action,double AuthorizedAt)->Outcome{
            const auto Fence=Remote->Consumers().CurrentFence();
            if(!ValidRemote()||!Remote->Consumers().Revalidate(Fence))return Outcome::Rejected;
            if(Action=="pause"){
                const bool Before=IsWalkthroughMenuOpen();ToggleWalkthroughMenu();
                if(IsWalkthroughMenuOpen()||IsPaused())Remote->Consumers().PauseMotion();
                return Before!=IsWalkthroughMenuOpen()?Outcome::Applied:Outcome::NoOp;
            }
            if(Action=="mute"){
                if(!SettingsOwned()||!ValidRemote()||!Remote->Consumers().Revalidate(Fence))return Outcome::Rejected;
                const bool Before=IsSoundMuted();ToggleSound();
                return Before!=IsSoundMuted()?Outcome::Applied:Outcome::NoOp;
            }
            if(Action=="interact"){
                // Explicit project consumption API; never infer Applied from void.
                return MikdashOnline::Interaction01::ConsumeResidentInteraction(*this,Remote.ToSharedRef(),Fence);
            }
            return Outcome::Rejected;
        });
}
void AReceiver04Controller::UpdateRotation(float Dt){
    Super::UpdateRotation(Dt); // exactly ONE modifier evaluation and FaceRotation
    if(!ValidRemote())return;
    auto StockCamera=[&](){
        if(!PlayerCameraManager||PlayerCameraManager->GetClass()!=APlayerCameraManager::StaticClass()||
           !GEngine||GEngine->XRSystem.IsValid())return false;
        bool Supported=true;
        PlayerCameraManager->ForEachCameraModifier([&](UCameraModifier* M){
            // Both exact stock classes inherit the no-op ProcessViewRotation.
            // Custom/Blueprint modifiers and custom managers are unsupported.
            if(M&&!M->IsDisabled()&&M->GetClass()!=UCameraModifier::StaticClass()&&
               M->GetClass()!=UCameraModifier_CameraShake::StaticClass())Supported=false;
            return Supported;
        });
        return Supported;
    };
    Remote->Consumers().UpdateRotation(Remote->BoundContext(),IsPaused()||IsWalkthroughMenuOpen()||IsLookInputIgnored()||!StockCamera(),
        [&](double X,double Y,double)->Outcome{
            const auto Fence=Remote->Consumers().CurrentFence();
            FRotator View=GetControlRotation()+FRotator(-Y*LookDegrees,X*LookDegrees,0);
            // Callback-free stock view limits, never evaluate modifiers twice.
            View.Pitch=FMath::ClampAngle<double>(View.Pitch,PlayerCameraManager->ViewPitchMin,PlayerCameraManager->ViewPitchMax);
            View.Yaw=FMath::ClampAngle<double>(View.Yaw,PlayerCameraManager->ViewYawMin,PlayerCameraManager->ViewYawMax);
            View.Roll=FMath::ClampAngle<double>(View.Roll,PlayerCameraManager->ViewRollMin,PlayerCameraManager->ViewRollMax);
            if(!ValidRemote()||IsPaused()||IsWalkthroughMenuOpen()||IsLookInputIgnored()||!StockCamera()||
               !Remote->Consumers().Revalidate(Fence))return Outcome::Rejected;
            SetControlRotation(View);
            // No second FaceRotation: normal pawn-facing update remains once per
            // tick. The remote control rotation is the consumed semantic result.
            return Outcome::Applied;
        });
}
void AReceiver04Controller::EndPlay(const EEndPlayReason::Type Reason){
    if(Remote.IsValid())Remote->Abort();
    DetachRemoteMovement();Remote.Reset();Super::EndPlay(Reason);
}
