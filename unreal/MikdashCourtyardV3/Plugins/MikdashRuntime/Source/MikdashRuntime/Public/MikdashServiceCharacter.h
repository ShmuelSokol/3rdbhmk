#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "MikdashServiceCharacter.generated.h"

UCLASS()
class MIKDASHRUNTIME_API UMikdashServiceMovement : public UCharacterMovementComponent
{
    GENERATED_BODY()
public:
    TFunction<bool(const FVector&,const FVector&)> MovementGuard;
    bool bGuardRefused = false;
    virtual bool MoveUpdatedComponentImpl(const FVector& Delta,const FQuat& Rotation,bool bSweep,
        FHitResult* OutHit=nullptr,ETeleportType Teleport=ETeleportType::None) override;
};

UCLASS()
class MIKDASHRUNTIME_API AMikdashServiceCharacter : public ACharacter
{
    GENERATED_BODY()
public:
    AMikdashServiceCharacter(const FObjectInitializer& Initializer);
    FVector ServiceFeet() const { return GetActorLocation()-FVector(0,0,98); }
    void Halt();
    void SetServiceFrozen(bool Frozen);
private:
    bool bServiceFrozen = false;
    EMovementMode SavedMovementMode = MOVE_Walking;
    uint8 SavedCustomMode = 0;
};
