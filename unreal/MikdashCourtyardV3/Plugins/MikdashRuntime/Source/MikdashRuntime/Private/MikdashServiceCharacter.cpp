#include "MikdashServiceCharacter.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"

bool UMikdashServiceMovement::MoveUpdatedComponentImpl(const FVector& Delta,const FQuat& Rotation,
    bool bSweep,FHitResult* OutHit,ETeleportType Teleport)
{
    if (!UpdatedComponent || !MovementGuard || Delta.ContainsNaN() ||
        !MovementGuard(UpdatedComponent->GetComponentLocation()-FVector(0,0,98),
                       UpdatedComponent->GetComponentLocation()+Delta-FVector(0,0,98)))
    {
        bGuardRefused=true;
        if (OutHit) { *OutHit=FHitResult(); OutHit->bBlockingHit=true; OutHit->Time=0; }
        return false;
    }
    return Super::MoveUpdatedComponentImpl(Delta,Rotation,bSweep,OutHit,Teleport);
}

AMikdashServiceCharacter::AMikdashServiceCharacter(const FObjectInitializer& Initializer)
    : Super(Initializer.SetDefaultSubobjectClass<UMikdashServiceMovement>(ACharacter::CharacterMovementComponentName))
{
    GetCapsuleComponent()->InitCapsuleSize(34,96);
    GetMesh()->SetRelativeLocation(FVector(0,0,-98));
    GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    auto* Movement=GetCharacterMovement();
    Movement->bRunPhysicsWithNoController=true;
    Movement->MaxWalkSpeed=90;
    Movement->MaxStepHeight=45; // physical resident bound; not proof of this stair route
    Movement->SetWalkableFloorZ(0.95f);
    Movement->bOrientRotationToMovement=false;
    bUseControllerRotationYaw=false;
}

void AMikdashServiceCharacter::Halt()
{
    ConsumeMovementInputVector();
    GetCharacterMovement()->StopMovementImmediately();
}

void AMikdashServiceCharacter::SetServiceFrozen(bool Frozen)
{
    if (Frozen == bServiceFrozen) return;
    auto* Movement=GetCharacterMovement();
    if (Frozen)
    {
        SavedMovementMode=Movement->MovementMode;
        SavedCustomMode=Movement->CustomMovementMode;
        Halt();
        Movement->DisableMovement();
    }
    else Movement->SetMovementMode(SavedMovementMode,SavedCustomMode);
    bServiceFrozen=Frozen;
}
