#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "ResidentCrowdRuntime.h"
#include "ResidentRouteLoop.h"
#include "MikdashResidentCharacter.generated.h"

// The integrator supplies continuous, role-specific mapped segment review. This
// callback is intentionally required: a navmesh path alone is not access evidence.
using FMikdashResidentSegmentReview = TFunction<bool(const FString&, const FVector&, const FVector&)>;

/** Presentational gait tuning shared by the resident body and the population that drives its
 * clips. NOTHING in this namespace touches the 34/96 capsule, the authored route, the
 * authoritative segment review, access, the amah frame or any save. It only changes how a
 * body accelerates, turns, and plays the two clips it already has.
 *
 * Why these numbers exist at all: before this wave every resident walked at a uniform
 * 180 cm/s, reached that speed in 0.09 s, stopped dead in 0.09 s, turned at 240 deg/s, and
 * played one shared 1.2 s walk clip at rate 1.0 starting from time 0. That combination is
 * what reads as "stilting along": the stride does not match the translation (foot slide),
 * every body is in identical phase (marching), and every start, stop and corner is a step
 * function.
 *
 * Free adult walking speed is roughly 1.2-1.45 m/s (Bohannon & Williams Andrews, "Normal
 * walking speed: a descriptive meta-analytic study", Physiotherapy 97(3) 2011, 182-189).
 * 1.8 m/s is close to the walk/run transition, which is why the old pace looked driven.
 */
namespace MikdashGait
{
/** MEASURED, not assumed. Forward kinematics over the source GLBs, identically for all nine
 * variants, on a 1.200 s A_Pilgrim_Original_Walk clip at play rate 1.0 and mesh scale 1.0.
 *
 * The clip was re-authored on 9 Sep 2026 (Scripts/pilgrim_walk_v2.py) and this number moved
 * with it. The old clip carried 32.0 cm of step length = 53.33 cm/s, and THAT WAS THE
 * STILTING: the population drove every body at 180 cm/s, so the feet slid backwards at about
 * 127 cm/s. The v2 clip carries 71.93 cm of step = 119.89 cm/s, authored to 120.0.
 *
 * What makes it a walk rather than a glide is the stance plant. The stance foot is now a rigid
 * plate that only rotates about points already on the ground - heel rocker, foot flat, toe
 * rocker - and rotating a body about its own contact point cannot slide it, so the plant is
 * exact by construction rather than by tuning. Measured world drift of the planted foot fell
 * from 4.572 cm to 0.019 cm; two counter-phase sinusoids, which is what the old clip was,
 * cannot produce a plant at all.
 *
 * 120 and not the anthropometric 130-145 because the rig's leg is short: hip-to-ankle is
 * 82.0 cm on a 179.4 cm figure (0.457 H against the 0.53 H the generator's own PROPORTIONS
 * asks for), and at a fixed 1.2 s cycle 135 cm/s would need an 81 cm step this leg cannot
 * reach. Raising thigh_* is the real fix and is a geometry change, not a number change. */
constexpr double MeasuredWalkClipGroundSpeedCm = 120.0;

/** Anthropometric target, kept as the fallback pace and as the number the source clip should
 * be re-authored to support. Free adult walking speed is roughly 1.2-1.45 m/s (Bohannon &
 * Williams Andrews, "Normal walking speed: a descriptive meta-analytic study", Physiotherapy
 * 97(3) 2011, 182-189) at a step length near 0.41 x stature. The V3 clip's step is 32.0 cm at
 * 179.4 cm stature = 0.178 x stature: a shuffle, 44% of a natural step. Until the clip is
 * re-authored, honouring this number is exactly what causes the slide, so the derived pace
 * below wins by default. */
constexpr double BaseWalkSpeedCm = 132.0;
/** Half-width of the per-person pace spread, cm/s, drawn from that person's own seed. */
constexpr double WalkSpeedSpreadCm = 15.0;
/** Wide enough to hold both the clip-derived amble and a re-authored natural pace. */
constexpr double MinWalkSpeedCm = 40.0, MaxWalkSpeedCm = 190.0;
/** Half-width of the per-person cadence bias, so no two bodies step or breathe together.
 * When the pace is derived from the clip this bias IS the play rate, so keeping it small
 * keeps every body near rate 1.0 and therefore near zero foot slide. */
constexpr double CadenceSpread = 0.07;

/** ~0.45 s from standing to walking pace, ~0.35 s back down. Engine defaults are 2048 both
 * ways, i.e. 0.09 s, which makes the walk clip snap on at full stride. */
constexpr double MaxAccelerationCm = 300.0;
constexpr double BrakingDecelerationCm = 400.0;

/** Yaw rate while walking (was 240 deg/s: a body pivoted 90 deg in 0.4 s while translating,
 * scrubbing the feet sideways). Scaled per body with that body's pace. */
constexpr double WalkTurnRateDegPerSec = 150.0;
/** Yaw rate while standing still. There is no turn-in-place clip, so a standing turn is a
 * frozen-feet pivot however fast it is; at 70 deg/s a 90 deg turn takes 1.3 s and reads as a
 * weight shift rather than a turret. This is a MITIGATION, not a cure - see the handoff. */
constexpr double StandingTurnRateDegPerSec = 70.0;
/** Below this yaw error a standing body simply does not turn, so it cannot micro-jitter. */
constexpr double StandingTurnDeadZoneDeg = 6.0;

/** Distance over which the final leg eases its input down to a stop, cm. */
constexpr double ArrivalEaseCm = 70.0;
constexpr double MinInputScale = 0.25;
/** No easing may drop a body below the speed MikdashRoute::BlockRecovery reads as stuck
 * (15 cm/s sustained for two seconds), or slowing for a corner would spend the body own
 * sidestep budget and log a false blockage. This multiplier keeps a margin above it. */
constexpr double BlockWatchdogMargin = 1.5;
/** Corner easing: below this speed there is no heading to compare against. */
constexpr double CornerSlowSpeedCm = 12.0;
/** cos(angle) between current velocity and the wanted heading: 0.87 is ~30 deg, -0.2 ~102 deg. */
constexpr double CornerSoftCos = 0.87, CornerHardCos = -0.2;
constexpr double CornerMinScale = 0.45;

/** Walk/idle switch hysteresis, cm/s. The old code used one 5 cm/s threshold in both
 * directions, so a decelerating body could flip clips on consecutive frames. */
constexpr double WalkEnterSpeedCm = 22.0;
constexpr double WalkExitSpeedCm = 9.0;

/** Bounds on the walk clip's play rate when it is driven from ground speed. */
constexpr double MinWalkPlayRate = 0.45, MaxWalkPlayRate = 1.55;
}

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

    /** Give this body its own walking personality, derived deterministically from its stable
     * resident id, so the same person always walks the same way and no two neighbours share a
     * pace or a gait phase. Purely presentational; see the MikdashGait note above. */
    void ConfigureGait(uint32 Seed, double InVisualScale, double ClipGroundSpeedCmPerSec);

    /** Free-walking pace chosen for this body, cm/s (also written to MaxWalkSpeed). */
    UFUNCTION(BlueprintPure, Category="Residents|Gait")
    double GetPreferredWalkSpeed() const { return PreferredWalkSpeedCm; }

    /** This body's entry point into a looping clip, 0..1. */
    UFUNCTION(BlueprintPure, Category="Residents|Gait")
    double GetGaitPhase01() const { return GaitPhase01; }

    /** This body's own cadence multiplier, ~0.93..1.07. */
    UFUNCTION(BlueprintPure, Category="Residents|Gait")
    double GetCadenceBias() const { return CadenceBias; }

    /** Horizontal ground speed, cm/s. Exposed so a future locomotion Animation Blueprint can
     * read it directly instead of the population pushing clips. */
    UFUNCTION(BlueprintPure, Category="Residents|Gait")
    double GetGroundSpeed() const { return GetVelocity().Size2D(); }

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
    double PreferredWalkSpeedCm = MikdashGait::BaseWalkSpeedCm;
    double GaitPhase01 = 0.0;
    double CadenceBias = 1.0;

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
