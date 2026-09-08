#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "ResidentCrowdRuntime.h"
#include "ResidentRouteLoop.h"
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
    // Explicit opt-in permits a flat, physically reviewed direct corridor only when
    // navigation is unavailable: 100 cm by default, or the caller's MaxDirectCorridorCm for
    // an authored straight leg whose whole capsule sweep the reviewer has approved.
    // Authoritative review always remains required.
    bool RequestReviewedRoute(const FString& RouteId, const FVector& OriginFeet, const FVector& DestinationFeet,
        bool bAllowReviewedDirectCorridor = false, double MaxDirectCorridorCm = 100.0);

    // While standing (no active route), turn at 120 deg/s to face a world point, e.g. during a
    // pause at a goal. Purely presentational; never moves the feet.
    void SetStandingFacingTarget(const FVector& WorldTarget, bool bEnabled);

    /** Authored identity, mission and lines for this body. Written once at startup from the
     * staged people directory. Fiction: none of it is a source fact and none of it rules. */
    void SetResidentProfile(const FString& InName, const FString& InRole, const FString& InMission,
        const FString& InOrigin, const FString& InPresence, const FString& InGarmentVariant,
        const TArray<FString>& InDialogLines);

    /** Hold still and turn to face the walker for the length of a conversation, then resume
     * the authored route where it stopped. Never moves the feet and never changes access. */
    UFUNCTION(BlueprintCallable, Category="Residents|Dialog")
    void SetConversationHold(bool bHold, FVector FaceWorldTarget);

    UFUNCTION(BlueprintPure, Category="Residents|Dialog")
    bool IsInConversation() const { return bConversationHold; }

    UFUNCTION(BlueprintPure, Category="Residents|Dialog")
    FString GetResidentDisplayName() const { return DisplayName; }

    UFUNCTION(BlueprintPure, Category="Residents|Dialog")
    FString GetResidentRole() const { return RoleTitle; }

    UFUNCTION(BlueprintPure, Category="Residents|Dialog")
    FString GetResidentMission() const { return Mission; }

    UFUNCTION(BlueprintPure, Category="Residents|Dialog")
    FString GetResidentOrigin() const { return Origin; }

    /** Why a kohen or Levite is walking here at all, when the directory had to state it. */
    UFUNCTION(BlueprintPure, Category="Residents|Dialog")
    FString GetResidentPresenceNote() const { return PresenceNote; }

    UFUNCTION(BlueprintPure, Category="Residents|Dialog")
    FString GetGarmentVariant() const { return GarmentVariant; }

    /** Which registered body this resident was given (empty = the population's default rig),
     * the visual scale applied to its skeletal mesh COMPONENT, and whether that was a fallback.
     * Written once at spawn by the population; read by the PIE verification script. */
    void SetResidentBody(const FString& InVariantId, double InVisualScale, bool bInFallback);

    UFUNCTION(BlueprintPure, Category="Residents|Body")
    FString GetBodyVariantId() const { return BodyVariantId; }

    UFUNCTION(BlueprintPure, Category="Residents|Body")
    double GetBodyVisualScale() const { return BodyVisualScale; }

    UFUNCTION(BlueprintPure, Category="Residents|Body")
    bool IsBodyFallback() const { return bBodyFallback; }

    UFUNCTION(BlueprintPure, Category="Residents|Dialog")
    int32 GetResidentDialogLineCount() const { return DialogLines.Num(); }

    UFUNCTION(BlueprintPure, Category="Residents|Dialog")
    FString GetResidentDialogLine(int32 Index) const { return DialogLines.IsValidIndex(Index) ? DialogLines[Index] : FString(); }

    UFUNCTION(BlueprintPure, Category="Residents|Dialog")
    TArray<FString> GetResidentDialogLines() const { return DialogLines; }

    /** True once an authored profile with at least one line has been written. */
    UFUNCTION(BlueprintPure, Category="Residents|Dialog")
    bool HasResidentProfile() const { return !DisplayName.IsEmpty() && DialogLines.Num() > 0; }

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

    UFUNCTION(BlueprintPure, Category="Residents")
    FString GetRouteDiagnostic() const { return RouteDiagnostic; }

    // Number of two-second blockages answered with a reviewed 100 cm sidestep on the current route.
    UFUNCTION(BlueprintPure, Category="Residents")
    int32 GetSidestepCount() const { return SidestepCount; }

    uint64 GetRouteToken() const { return RouteToken; }

private:
    TSharedPtr<MikdashCrowd::Runtime> Crowd;
    FMikdashResidentSegmentReview ReviewSegment;
    FString ResidentId;
    FString RouteDiagnostic = TEXT("No route requested");
    std::string ResidentKey;
    TArray<FVector> RoutePoints;
    int32 PointIndex = 0;
    uint64 RouteToken = 0;
    FVector MappedDestination = FVector::ZeroVector;
    bool bNeedsPassageClearance = false;
    bool bWasPaused = false;
    MikdashRoute::BlockRecovery Recovery;
    FVector LastFeet = FVector::ZeroVector;
    bool bHasLastFeet = false;
    int32 SidestepCount = 0;
    FVector FacingTarget = FVector::ZeroVector;
    bool bFacingEnabled = false;

    UPROPERTY() FString DisplayName;
    UPROPERTY() FString RoleTitle;   // "Role" is reserved on AActor
    UPROPERTY() FString Mission;
    UPROPERTY() FString Origin;
    UPROPERTY() FString PresenceNote;
    UPROPERTY() FString GarmentVariant;
    UPROPERTY() TArray<FString> DialogLines;
    UPROPERTY() FString BodyVariantId;
    UPROPERTY() double BodyVisualScale = 1.0;
    UPROPERTY() bool bBodyFallback = false;
    bool bConversationHold = false;
    FVector ConversationFacing = FVector::ZeroVector;

    static constexpr double HorizontalTolerance = 18.0;
    static constexpr double VerticalTolerance = 12.0;

    const MikdashCrowd::Person* Resident() const;
    const MikdashCrowd::Identity* Plan() const;
    void StopBody();
    void FailRoute();
    bool TrySidestep(const FVector& Feet, const FVector& Target);
    void UpdateStandingFacing(float DeltaSeconds);
    void UpdateConversationFacing(float DeltaSeconds);
    static bool NearFeet(const FVector& A, const FVector& B);
};
