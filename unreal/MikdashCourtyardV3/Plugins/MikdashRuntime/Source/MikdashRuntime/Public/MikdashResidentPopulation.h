#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ResidentCrowdRuntime.h"
#include "MikdashResidentPopulation.generated.h"

class AMikdashResidentCharacter;
class UAnimSequence;

/** Opt-in, five fictional outer-court visitors. Native integration/visual review required.
 * Does not spawn/replace saved visuals, grant ritual eligibility, or serialize bodies.
 */
UCLASS(BlueprintType)
class MIKDASHRUNTIME_API AMikdashResidentPopulation : public AActor
{
    GENERATED_BODY()
public:
    AMikdashResidentPopulation();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    // Explicit activation in a live game world after visual/collision setup.
    UFUNCTION(BlueprintCallable, Category="Residents") bool InitializeReviewedPilot();
    UFUNCTION(BlueprintCallable, Category="Residents") void SetPopulationPaused(bool Value);
    UFUNCTION(BlueprintPure, Category="Residents") bool IsPopulationActive() const { return bActive; }
    UFUNCTION(BlueprintPure, Category="Residents") FString GetPopulationStatus() const { return Status; }
    // Set only on an explicitly adopted, fully configured authored population.
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") bool bActivateReviewedPilotOnBeginPlay = false;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") TArray<TObjectPtr<AMikdashResidentCharacter>> Bodies;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") TObjectPtr<UAnimSequence> IdleAnimation;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") TObjectPtr<UAnimSequence> WalkAnimation;
private:
    TSharedPtr<MikdashCrowd::Runtime> Crowd;
    TArray<FVector> Origins, Destinations;
    TArray<bool> Walking;
    double FractionalSeconds = 0.0;
    bool bActive = false, bUserPaused = false;
    FString Status = TEXT("Inactive: requires five reviewed native bodies");
    bool ReviewSegment(int32 BodyIndex, const FVector& From, const FVector& To) const;
    void StopPopulation();
};
