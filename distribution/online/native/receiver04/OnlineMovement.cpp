#include "OnlineMovement.h"
#include "MikdashPlayerController.h"
#include "GameFramework/Character.h"
#include "Engine/World.h"
#include "CollisionQueryParams.h"

using namespace MikdashOnline::Receiver04;
namespace {
bool SameOwner(APlayerController* C,APawn* P){
    return IsValid(C)&&IsValid(P)&&C->GetPawn()==P&&P->GetController()==C&&C->IsLocalController();
}
bool Paused(APlayerController* C){
    const auto* Project=Cast<AMikdashPlayerController>(C);
    return !IsValid(C)||C->IsPaused()||C->IsMoveInputIgnored()||(Project&&Project->IsWalkthroughMenuOpen());
}
FVector Direction(APlayerController* C,double X,double Y){
    const FRotator Heading(0,C->GetControlRotation().Yaw,0);
    return Heading.Vector()*Y+FRotationMatrix(Heading).GetUnitAxis(EAxis::Y)*X;
}
}
bool UReceiver04WalkerMovement::ValidRemote()const{
    return Remote.IsValid()&&OwnedPawn.Get()==CharacterOwner&&SameOwner(OwnedController.Get(),OwnedPawn.Get());
}
bool UReceiver04WalkerMovement::ConfigureRemote(TSharedPtr<Authority> S,APlayerController* C){
    if(Remote.IsValid()||!S.IsValid()||!SameOwner(C,CharacterOwner)||CharacterMovementCVars::AsyncCharacterMovement!=0)return false;
    Remote=MoveTemp(S);OwnedController=C;OwnedPawn=CharacterOwner;return true;
}
void UReceiver04WalkerMovement::BuildAsyncInput(){
    // No remote contribution enters asynchronous input preparation/execution.
    if(Remote.IsValid())Remote->Abort();
    Super::BuildAsyncInput(); // normal LOCAL behavior is preserved
}
void UReceiver04WalkerMovement::ControlledCharacterMove(const FVector& Local,float Dt){
    if(!Remote.IsValid()){Super::ControlledCharacterMove(Local,Dt);return;}
    if(!HasValidData()||!FMath::IsFinite(Dt)||Dt<0){Remote->Abort();return;}
    // Perform jump work BEFORE authorizing remote acceleration; a jump callback
    // can stall or replace possession. This mirrors the engine ordering without
    // passing remote data into the earlier ConsumeInputVector/skipped-tick path.
    CharacterOwner->CheckJumpInput(Dt);
    if(!HasValidData()){Remote->Abort();return;}
    FVector Effective=Local;
    bool AccelerationConsumed=false;
    if(!ValidRemote()||CharacterMovementCVars::AsyncCharacterMovement!=0)Remote->Abort();
    else Remote->Consumers().ConsumeMovement(Remote->BoundContext(),Paused(OwnedController.Get()),
        [&](double X,double Y,double)->Outcome{
            const auto Fence=Remote->Consumers().CurrentMovementFence();
            const FVector Candidate=(Local+Direction(OwnedController.Get(),X,Y)).GetClampedToMaxSize(1);
            const FVector CandidateAcceleration=ScaleInputAcceleration(ConstrainInputAcceleration(Candidate));
            if(!ValidRemote()||Paused(OwnedController.Get())||!Remote->Consumers().Revalidate(Fence)){
                Remote->Consumers().PauseMotion();return Outcome::Rejected;
            }
            // This is semantic acceleration consumption, not a promise that
            // physics/collision completes before expiry.
            Acceleration=CandidateAcceleration;
            AnalogInputModifier=ComputeAnalogInputModifier();
            AccelerationConsumed=true;return Outcome::Applied;
        });
    // The local path must still evaluate if the remote command was not consumed.
    // Local acceleration preserves normal virtual constrain/scale behavior when
    // remote expires or possession becomes invalid.
    if(!AccelerationConsumed){
        Acceleration=ScaleInputAcceleration(ConstrainInputAcceleration(Effective));
        AnalogInputModifier=ComputeAnalogInputModifier();
    }
    if(CharacterOwner->GetLocalRole()==ROLE_Authority)PerformMovement(Dt);
    else if(CharacterOwner->GetLocalRole()==ROLE_AutonomousProxy&&IsNetMode(NM_Client))ReplicateMoveToServer(Dt,Acceleration);
}
bool UReceiver04DoveMovement::ValidRemote()const{
    return Remote.IsValid()&&OwnedPawn.Get()==PawnOwner&&SameOwner(OwnedController.Get(),OwnedPawn.Get());
}
bool UReceiver04DoveMovement::ConfigureRemote(TSharedPtr<Authority> S,APlayerController* C){
    if(Remote.IsValid()||!S.IsValid()||!SameOwner(C,PawnOwner))return false;
    Remote=MoveTemp(S);OwnedController=C;OwnedPawn=PawnOwner;return true;
}
UReceiver04DoveMovement::Shaped UReceiver04DoveMovement::Shape(const FVector& Input)const{
    Shaped Out;Out.Direction=Input;
    FVector Probe=Input;
    if(Probe.IsNearlyZero(1e-3)&&Velocity.SizeSquared()>FMath::Square(50.f))Probe=Velocity;
    if(!UpdatedComponent||!GetWorld()||!PawnOwner||Probe.IsNearlyZero(1e-3)||Probe.ContainsNaN())return Out;
    const FVector Start=UpdatedComponent->GetComponentLocation();
    FCollisionQueryParams Params(SCENE_QUERY_STAT(Receiver04DoveSteer),false,PawnOwner);
    FHitResult Hit;
    if(GetWorld()->SweepSingleByChannel(Hit,Start,Start+Probe.GetSafeNormal()*MikdashDove::ObstacleSweepLengthCm,
       FQuat::Identity,ECC_Pawn,FCollisionShape::MakeSphere(float(MikdashDove::ObstacleSweepRadiusCm)),Params)&&Hit.bBlockingHit){
        const auto S=MikdashDove::SteerAroundObstacle({Input.X,Input.Y,Input.Z},true,
            {Hit.ImpactNormal.X,Hit.ImpactNormal.Y,Hit.ImpactNormal.Z},Hit.bStartPenetrating?0:Hit.Distance);
        Out.Scale=float(S.SpeedScale);Out.Sliding=S.bSliding;
        if(S.bSliding)Out.Direction=FVector(S.Direction.X,S.Direction.Y,S.Direction.Z);
    }
    return Out;
}
void UReceiver04DoveMovement::Commit(const Shaped& Input,float Dt){
    // Vector-taking form of the installed floating-movement acceleration policy:
    // steering boost, braking, analog speed limit, acceleration and overspeed
    // preservation. Never write the remote vector to shared pawn pending input.
    EvaluatedScale=Input.Scale;EvaluatedSliding=Input.Sliding;
    const FVector Control=Input.Direction.GetClampedToMaxSize(1);
    const double Analog=Control.Size(),Limit=GetMaxSpeed()*Analog;
    const bool Overspeed=IsExceedingMaxSpeed(Limit);
    if(Analog>0&&!Overspeed){
        if(Velocity.SizeSquared()>0)Velocity=FMath::Lerp(Velocity,Control*Velocity.Size(),FMath::Clamp(Dt*TurningBoost,0.f,1.f));
    }else if(Velocity.SizeSquared()>0){
        const FVector Before=Velocity;
        Velocity=Velocity.GetSafeNormal()*FMath::Max(Velocity.Size()-FMath::Abs(Deceleration)*Dt,0.0);
        if(Overspeed&&Velocity.SizeSquared()<Limit*Limit)Velocity=Before.GetSafeNormal()*Limit;
    }
    const double Ceiling=IsExceedingMaxSpeed(Limit)?Velocity.Size():Limit;
    Velocity=(Velocity+Control*FMath::Abs(Acceleration)*Dt).GetClampedToMaxSize(Ceiling);
}
void UReceiver04DoveMovement::ApplyControlInputToVelocity(float Dt){
    if(!Remote.IsValid()){Super::ApplyControlInputToVelocity(Dt);return;}
    if(!UpdatedComponent||!PawnOwner||!GetWorld()||!FMath::IsFinite(Dt)||Dt<0){Remote->Abort();return;}
    // Consume normal local bookkeeping ONCE. Its return is local only and is
    // never an acknowledgment point for remote input.
    const FVector Local=UPawnMovementComponent::ConsumeInputVector();
    bool Committed=false;
    if(!ValidRemote())Remote->Abort();
    else Remote->Consumers().ConsumeMovement(Remote->BoundContext(),Paused(OwnedController.Get()),
        [&](double X,double Y,double)->Outcome{
            const auto Fence=Remote->Consumers().CurrentMovementFence();
            const Shaped Candidate=Shape(Local+Direction(OwnedController.Get(),X,Y));
            // Collision sweep may stall. Discard EVERYTHING derived from its
            // remote vector on expiry: direction, speed scale AND sliding state.
            if(!ValidRemote()||Paused(OwnedController.Get())||!Remote->Consumers().Revalidate(Fence)){
                Remote->Consumers().PauseMotion();return Outcome::Rejected;
            }
            Commit(Candidate,Dt);Committed=true;return Outcome::Applied;
        });
    if(!Committed&&UpdatedComponent&&PawnOwner&&GetWorld()){
        // Exactly one bounded local/coasting recomputation, never a retry of the
        // remote command and never reuse Candidate's obstacle/speed information.
        const Shaped Fallback=Shape(Local);
        if(UpdatedComponent&&PawnOwner&&GetWorld())Commit(Fallback,Dt);
    }
}
