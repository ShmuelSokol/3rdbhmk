#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "ResidentCrowdRuntime.h"
#include "MikdashResidentCharacter.generated.h"

// The integrator supplies continuous, role-specific mapped segment review. This
// callback is intentionally required: a navmesh path alone is not access evidence.
using FMikdashResidentSegmentReview = TFunction<bool(const FString&, const FVector&, const FVector&)>;

/** An unpossessed, collision-driven resident body bound to ONE shared crowd model.
 * Does not create identities, advance simulation time, grant access or load meshes.
 * Dressed skeletal assets and animation blueprints are assigned by the integrator.
 */
UCLASS(BlueprintType)
class MIKDASHRUNTIME_API AMikdashResidentCharacter : public ACharacter
{
    GENERATED_BODY()

public:
    AMikdashResidentCharacter();
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

    bool BindResident(const TSharedPtr<MikdashCrowd::Runtime>& SharedRuntime,
        const FString& StableId, FMikdashResidentSegmentReview SegmentReview);

    // Both feet transforms are reviewed semantic waypoint mappings in native cm.
    // Path projection must stay near them; no partial path or teleport fallback.
    bool RequestReviewedRoute(const FString& RouteId, const FVector& OriginFeet, const FVector& DestinationFeet);

    // Call only after externally confirming body stopped AND passage resource clear.
    // A stopped body inside a doorway is not clear. This adapter never auto-releases.
    bool ConfirmPassageCleared(uint64 ExpectedToken);
    void RequestResidentStop();

    UFUNCTION(BlueprintPure, Category="Residents")
    FString GetResidentId() const { return ResidentId; }

    UFUNCTION(BlueprintPure, Category="Residents")
    FString GetResidentName() const;

    UFUNCTION(BlueprintPure, Category="Residents")
    FString GetResidentGoal() const;

    UFUNCTION(BlueprintPure, Category="Residents")
    FString GetResidentAction() const;

    UFUNCTION(BlueprintPure, Category="Residents")
    FString GetResidentState() const;

    UFUNCTION(BlueprintPure, Category="Residents")
    bool NeedsPassageClearance() const { return bNeedsPassageClearance; }

    uint64 GetRouteToken() const { return RouteToken; }

private:
    TSharedPtr<MikdashCrowd::Runtime> Crowd;
    FMikdashResidentSegmentReview ReviewSegment;
    FString ResidentId;
    std::string ResidentKey;
    TArray<FVector> RoutePoints;
    int32 PointIndex = 0;
    uint64 RouteToken = 0;
    FVector MappedDestination = FVector::ZeroVector;
    bool bNeedsPassageClearance = false;
    bool bWasPaused = false;
    static constexpr double HorizontalTolerance = 18.0;
    static constexpr double VerticalTolerance = 12.0;

    const MikdashCrowd::Person* Resident() const;
    const MikdashCrowd::Identity* Plan() const;
    void StopBody();
    void FailRoute();
    static bool NearFeet(const FVector& A, const FVector& B);
};
