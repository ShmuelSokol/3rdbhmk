#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MikdashTransit.h"
#include "TransitCrowdLogic.h"
#include "MikdashTransitCrowdCoordinator.generated.h"
class AMikdashCrowdField;
class UInstancedStaticMeshComponent;
class UStaticMesh;

// Scenery transfers, not resident identities, religious eligibility or a passenger census.
struct FMikdashTransferFigure
{
    FMikdashPassengerExchange Request;
    FString StableId;
    FVector Position = FVector::ZeroVector, Destination = FVector::ZeroVector;
    double StartAt = 0, Deadline = 0, LastUpdate = 0;
    bool bActive = false, bVisible = false, bAlighting = false, bPhotographer = false;
};
UCLASS(BlueprintType)
class MIKDASHRUNTIME_API AMikdashTransitCrowdCoordinator : public AActor
{
    GENERATED_BODY()
public:
    AMikdashTransitCrowdCoordinator();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;
    UFUNCTION(BlueprintCallable, Category="TransitCrowd") bool InitializeCoordinator();
    UFUNCTION(BlueprintCallable, Category="TransitCrowd") void ShutdownCoordinator();
    UFUNCTION(BlueprintPure, Category="TransitCrowd") FString GetCoordinatorSummary() const;
    UFUNCTION(BlueprintPure, Category="TransitCrowd") int32 GetActiveTransferCount() const;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="TransitCrowd") TObjectPtr<AMikdashTransit> Transit;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="TransitCrowd") TObjectPtr<AMikdashCrowdField> CrowdField;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="TransitCrowd") bool bActivateOnBeginPlay = false;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="TransitCrowd", meta=(ClampMin="1",ClampMax="512")) int32 MaxConcurrentFigures = 160;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="TransitCrowd", meta=(ClampMin="1",ClampMax="64")) int32 MaxFiguresPerStop = 32;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="TransitCrowd", meta=(ClampMin="1",ClampMax="128")) int32 UpdateBudget = 24;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="TransitCrowd") float WalkSpeedCmPerSecond = 110.f;
    // Must be an actual authored standing photography pose. Null means NO photographer rendering.
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="TransitCrowd") TObjectPtr<UStaticMesh> PhotographerPoseMesh;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="TransitCrowd") FVector PhotographerLookAt = FVector(0,0,300);
private:
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> WalkInstances;
    UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> PhotoInstances;
    TArray<FMikdashTransferFigure> Figures;
    MikdashTransitCrowd::RecentKeys Seen;
    int32 Cursor = 0, Boarded = 0, Alighted = 0, Expired = 0, Refused = 0, PhotoRequests = 0;
    bool bRunning = false;
    UFUNCTION() void HandleExchange(const FMikdashPassengerExchange& Request);
    bool GroundPoint(const FVector& Approximate, FVector& Feet) const;
    bool CorridorClear(const FVector& From, const FVector& To, int32 IgnoreSlot = INDEX_NONE) const;
    void Retire(int32 Slot);
    void Render(int32 Slot);
};
