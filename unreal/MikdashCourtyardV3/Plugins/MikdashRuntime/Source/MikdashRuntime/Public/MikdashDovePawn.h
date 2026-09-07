#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "MikdashDovePawn.generated.h"
class UFloatingPawnMovement;
class USphereComponent;
class USceneComponent;
/** Original stylized white dove for aerial architectural exploration. */
UCLASS()
class MIKDASHRUNTIME_API AMikdashDovePawn : public APawn
{
    GENERATED_BODY()
public:
    AMikdashDovePawn();
    virtual void Tick(float DeltaSeconds) override;
    UFUNCTION(BlueprintCallable, Category="Dove") void SetFlightBoost(bool bBoost);
    UFUNCTION(BlueprintPure, Category="Dove") float GetFlightSpeed() const;
private:
    UPROPERTY() TObjectPtr<USphereComponent> FlightCollision;
    UPROPERTY() TObjectPtr<UFloatingPawnMovement> FlightMovement;
    UPROPERTY() TObjectPtr<USceneComponent> LeftWing;
    UPROPERTY() TObjectPtr<USceneComponent> RightWing;
    float WingTime = 0.f;
};
