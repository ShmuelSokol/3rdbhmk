#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ResidentCrowdRuntime.h"
#include "ResidentRouteLoop.h"
#include <vector>
#include "MikdashResidentPopulation.generated.h"

class AMikdashResidentCharacter;
class UAnimSequence;

/** Opt-in, five fictional outer-court visitors. Native integration/visual review required.
 * Does not spawn/replace saved visuals, grant ritual eligibility, or serialize bodies.
 * One body may additionally follow an authored 4..6 point loop (60..120 m) with pauses,
 * pause-facing and reviewed sidestep recovery. That is scripted waypoint behavior with a
 * readable goal label, not a mind.
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
    UFUNCTION(BlueprintPure, Category="Residents") bool IsExtendedRouteActive() const { return bExtendedRoute; }
    UFUNCTION(BlueprintPure, Category="Residents") FString GetExtendedRouteStatus() const { return ExtendedStatus; }
    // Set only on an explicitly adopted, fully configured authored population.
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") bool bActivateReviewedPilotOnBeginPlay = false;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") TArray<TObjectPtr<AMikdashResidentCharacter>> Bodies;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") TObjectPtr<UAnimSequence> IdleAnimation;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") TObjectPtr<UAnimSequence> WalkAnimation;

    // Optional authored loop for ONE body (index into Bodies), written by
    // Scripts/release_dove_people_v2.py and validated by ResidentRouteLoop.h at startup.
    // Waypoint 0 must be that body's reviewed start. When the configuration is invalid the
    // population still starts with the five short routes and GetExtendedRouteStatus says why.
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Route") int32 ExtendedRouteBodyIndex = -1;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Route") TArray<FVector> ExtendedRouteWaypoints;
    /** Goal label shown while walking TOWARD waypoint i (GetResidentGoal). */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Route") TArray<FString> ExtendedRouteLabels;
    /** What the resident does during the pause at waypoint i (GetResidentAction). */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Route") TArray<FString> ExtendedRouteActions;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Route") TArray<float> ExtendedRoutePauseSeconds;
    /** World point faced during the pause at waypoint i. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Route") TArray<FVector> ExtendedRouteLookTargets;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Route") int32 ExtendedRouteLaps = 3;
private:
    TSharedPtr<MikdashCrowd::Runtime> Crowd;
    TArray<FVector> Origins, Destinations;
    TArray<bool> Walking;
    double FractionalSeconds = 0.0;
    bool bActive = false, bUserPaused = false;
    bool bExtendedRoute = false;
    FString Status = TEXT("Inactive: requires five reviewed native bodies");
    FString ExtendedStatus = TEXT("No extended route configured");
    std::vector<MikdashRoute::Point2> LoopPoints;
    static constexpr double ExtendedLegCorridorCm = 3000.0;
    bool ReviewSegment(int32 BodyIndex, const FVector& From, const FVector& To) const;
    bool ValidateExtendedRoute(const FVector& BodyStart, FString& Reason) const;
    bool IsExtendedBody(int32 BodyIndex) const { return bExtendedRoute && BodyIndex == ExtendedRouteBodyIndex; }
    FString WaypointName(const std::string& Key, std::size_t Index) const;
    void StopPopulation();
};
