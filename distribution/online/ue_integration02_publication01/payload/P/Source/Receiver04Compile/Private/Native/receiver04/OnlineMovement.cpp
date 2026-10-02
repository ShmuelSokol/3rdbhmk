#include "OnlineMovement.h"
#include "MikdashPlayerController.h"
#include "GameFramework/Character.h"
#include "Engine/World.h"
#include "CollisionQueryParams.h"
#include "Components/SceneComponent.h"

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
    if(GetClass()!=UReceiver04WalkerMovement::StaticClass())return false;
    if(Remote.IsValid()||!S.IsValid()||!SameOwner(C,CharacterOwner)||CharacterMovementCVars::AsyncCharacterMovement!=0)return false;
    Remote=MoveTemp(S);OwnedController=C;OwnedPawn=CharacterOwner;return true;
}
void UReceiver04WalkerMovement::BuildAsyncInput(){
    // No remote contribution enters asynchronous input preparation/execution.
    if(Remote.IsValid())Remote->Abort();
    Super::BuildAsyncInput(); // normal LOCAL behavior is preserved
}
void UReceiver04WalkerMovement::ControlledCharacterMove(const FVector& Local,float Dt){
    const TSharedPtr<Authority> Service=Remote; // survives synchronous DetachRemote
    if(!Service.IsValid()){Super::ControlledCharacterMove(Local,Dt);return;}
    const TWeakObjectPtr<UReceiver04WalkerMovement> Self(this);
    const auto Controller=OwnedController;
    const auto Pawn=OwnedPawn;
    const TWeakObjectPtr<USceneComponent> Component=UpdatedComponent;
    const TWeakObjectPtr<UWorld> World=GetWorld();
    const Context Incarnation=Service->BoundContext();
    auto SameBinding=[&](){
        auto* M=Self.Get();
        return M && M->Remote==Service && !Service->IsClosed() &&
            Service->BoundContext()==Incarnation && Controller.IsValid() && Pawn.IsValid() &&
            M->OwnedController==Controller && M->OwnedPawn==Pawn &&
            M->CharacterOwner==Pawn.Get() && Component.IsValid() && M->UpdatedComponent==Component.Get() &&
            World.IsValid() && M->GetWorld()==World.Get() && SameOwner(Controller.Get(),Pawn.Get());
    };
    auto Refuse=[&](){Service->Abort();};
    Service->Maintain();
    if(!SameBinding()||!HasValidData()||!FMath::IsFinite(Dt)||Dt<0||Local.ContainsNaN()||
       CharacterMovementCVars::AsyncCharacterMovement!=0){Refuse();return;}
    CharacterOwner->CheckJumpInput(Dt); // OnJumped may UnPossess and reset Remote
    Service->Maintain();
    if(!SameBinding()||!HasValidData()){Refuse();return;}
    bool AccelerationConsumed=false;
    Service->Consumers().ConsumeMovement(Incarnation,Paused(Controller.Get()),
        [&](double X,double Y,double)->Outcome{
            if(!SameBinding()){Refuse();return Outcome::Rejected;}
            const auto Fence=Service->Consumers().CurrentMovementFence();
            const FVector Candidate=(Local+Direction(Controller.Get(),X,Y)).GetClampedToMaxSize(1);
            if(!SameBinding()){Refuse();return Outcome::Rejected;}
            const FVector Constrained=ConstrainInputAcceleration(Candidate);
            if(!SameBinding()){Refuse();return Outcome::Rejected;}
            const FVector Scaled=ScaleInputAcceleration(Constrained);
            if(!SameBinding()){Refuse();return Outcome::Rejected;}
            const float MaxAccel=GetMaxAcceleration();
            // No acceleration write before callback-capable calculations finish.
            if(!SameBinding()){Refuse();return Outcome::Rejected;}
            if(Paused(Controller.Get())||!Service->Consumers().Revalidate(Fence)){
                Service->Consumers().PauseMotion();return Outcome::Rejected;
            }
            if(!SameBinding()){Refuse();return Outcome::Rejected;}
            // Stock ComputeAnalogInputModifier arithmetic, no second virtual call
            // after mutating Acceleration. Custom movement classes are refused.
            const float Analog=(Scaled.SizeSquared()>0.f&&MaxAccel>UE_SMALL_NUMBER)?
                float(FMath::Clamp<FVector::FReal>(Scaled.Size()/MaxAccel,0.f,1.f)):0.f;
            Acceleration=Scaled;AnalogInputModifier=Analog;
            AccelerationConsumed=true;return Outcome::Applied;
        });
    Service->Maintain();
    if(!SameBinding()||!HasValidData()){Refuse();return;}
    if(!AccelerationConsumed){
        const FVector Constrained=ConstrainInputAcceleration(Local);
        if(!SameBinding()){Refuse();return;}
        const FVector Scaled=ScaleInputAcceleration(Constrained);
        if(!SameBinding()){Refuse();return;}
        const float MaxAccel=GetMaxAcceleration();
        if(!SameBinding()){Refuse();return;}
        const float Analog=(Scaled.SizeSquared()>0.f&&MaxAccel>UE_SMALL_NUMBER)?
            float(FMath::Clamp<FVector::FReal>(Scaled.Size()/MaxAccel,0.f,1.f)):0.f;
        Acceleration=Scaled;AnalogInputModifier=Analog;
    }
    Service->Maintain();
    if(!SameBinding()||!HasValidData()){Refuse();return;}
    if(CharacterOwner->GetLocalRole()==ROLE_Authority)PerformMovement(Dt);
    else if(CharacterOwner->GetLocalRole()==ROLE_AutonomousProxy&&IsNetMode(NM_Client))ReplicateMoveToServer(Dt,Acceleration);
    // No member/remote access after these callback-capable physics calls.
}
bool UReceiver04DoveMovement::ValidRemote()const{
    return Remote.IsValid()&&OwnedPawn.Get()==PawnOwner&&SameOwner(OwnedController.Get(),OwnedPawn.Get());
}
bool UReceiver04DoveMovement::ConfigureRemote(TSharedPtr<Authority> S,APlayerController* C){
    if(GetClass()!=UReceiver04DoveMovement::StaticClass())return false;
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
    // Exact native class only. No virtual GetMaxSpeed/IsExceedingMaxSpeed calls:
    // calculate into locals, then commit once without intervening callbacks.
    const FVector Control=Input.Direction.GetClampedToMaxSize(1);
    const double Analog=Control.Size(),Limit=MaxSpeed*Input.Scale*Analog;
    FVector Next=Velocity;
    // Match IsExceedingMaxSpeed's float parameter/threshold rounding as well.
    const float LimitSquared=FMath::Square(FMath::Max(0.f,float(Limit)))*1.01f;
    const bool Overspeed=Next.SizeSquared()>LimitSquared;
    if(Analog>0&&!Overspeed){
        if(Next.SizeSquared()>0)Next=FMath::Lerp(Next,Control*Next.Size(),FMath::Clamp(Dt*TurningBoost,0.f,1.f));
    }else if(Next.SizeSquared()>0){
        const FVector Before=Next;
        Next=Next.GetSafeNormal()*FMath::Max(Next.Size()-FMath::Abs(Deceleration)*Dt,0.0);
        if(Overspeed&&Next.SizeSquared()<Limit*Limit)Next=Before.GetSafeNormal()*Limit;
    }
    const double Ceiling=(Next.SizeSquared()>LimitSquared)?Next.Size():Limit;
    Next=(Next+Control*FMath::Abs(Acceleration)*Dt).GetClampedToMaxSize(Ceiling);
    EvaluatedScale=Input.Scale;EvaluatedSliding=Input.Sliding;Velocity=Next;
}
void UReceiver04DoveMovement::ApplyControlInputToVelocity(float Dt){
    const TSharedPtr<Authority> Service=Remote;
    if(!Service.IsValid()){Super::ApplyControlInputToVelocity(Dt);return;}
    const TWeakObjectPtr<UReceiver04DoveMovement> Self(this);
    const auto Controller=OwnedController;
    const auto Pawn=OwnedPawn;
    const TWeakObjectPtr<USceneComponent> Component=UpdatedComponent;
    const TWeakObjectPtr<UWorld> World=GetWorld();
    const Context Incarnation=Service->BoundContext();
    auto SameBinding=[&](){
        auto* M=Self.Get();
        return M && M->Remote==Service && !Service->IsClosed() &&
            Service->BoundContext()==Incarnation && Controller.IsValid() && Pawn.IsValid() &&
            M->OwnedController==Controller && M->OwnedPawn==Pawn && M->PawnOwner==Pawn.Get() &&
            Component.IsValid() && M->UpdatedComponent==Component.Get() &&
            World.IsValid() && M->GetWorld()==World.Get() && SameOwner(Controller.Get(),Pawn.Get());
    };
    auto Refuse=[&](){Service->Abort();};
    Service->Maintain();
    if(!SameBinding()||!FMath::IsFinite(Dt)||Dt<0){Refuse();return;}
    const FVector Local=UPawnMovementComponent::ConsumeInputVector();
    if(!SameBinding()||Local.ContainsNaN()){Refuse();return;}
    bool Committed=false;
    Service->Consumers().ConsumeMovement(Incarnation,Paused(Controller.Get()),
        [&](double X,double Y,double)->Outcome{
            if(!SameBinding()){Refuse();return Outcome::Rejected;}
            const auto Fence=Service->Consumers().CurrentMovementFence();
            const FVector Input=Local+Direction(Controller.Get(),X,Y);
            if(!SameBinding()){Refuse();return Outcome::Rejected;}
            const Shaped Candidate=Shape(Input); // real sweep may detach/destroy/repossess
            if(!SameBinding()){Refuse();return Outcome::Rejected;}
            if(Paused(Controller.Get())||!Service->Consumers().Revalidate(Fence)){
                Service->Consumers().PauseMotion();return Outcome::Rejected;
            }
            if(!SameBinding()){Refuse();return Outcome::Rejected;}
            Commit(Candidate,Dt); // callback-free arithmetic after the final fence
            Committed=true;return Outcome::Applied;
        });
    Service->Maintain();
    if(!SameBinding()){Refuse();return;}
    if(!Committed){
        const Shaped Fallback=Shape(Local);
        Service->Maintain();
        if(!SameBinding()){Refuse();return;}
        Commit(Fallback,Dt);
    }
}
