#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "QueueFlowMath.h"
#include "MikdashGateSecurity.generated.h"

/** Where one person stands inside the checkpoint. Mirrors MikdashQueue::EStage so Blueprint
 * and the crowd systems can read it without seeing the engine-independent header. */
UENUM(BlueprintType)
enum class EMikdashGateStage : uint8
{
    None                UMETA(DisplayName = "None"),
    WaitingAtDetector   UMETA(DisplayName = "Waiting at Detector"),
    AtDetector          UMETA(DisplayName = "At Detector"),
    WaitingAtBagTable   UMETA(DisplayName = "Waiting at Bag Table"),
    AtBagTable          UMETA(DisplayName = "At Bag Table"),
    Cleared             UMETA(DisplayName = "Cleared"),
    Refused             UMETA(DisplayName = "Refused")
};

/** The answer to one request to pass. Returned by RequestToPass alongside the wait time. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashGatePass
{
    GENERATED_BODY()

    /** False when every lane was already at its hard capacity. The caller should send the
     * body to a different gate approach, or make it wait outside and ask again later. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Gate Security")
    bool bAccepted = false;

    /** Handle for every later query. -1 when the request was refused. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Gate Security")
    int32 TicketId = -1;

    /** Detector lane this person was sent to, 0-based. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Gate Security")
    int32 Lane = -1;

    /** Place in that lane at the moment of the request; 0 stands at the arch. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Gate Security")
    int32 SlotIndex = -1;

    /** Predicted seconds from now until this person is clear of the whole checkpoint.
     * A prediction from the current queue state, not a promise. Negative when refused. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Gate Security")
    float EstimatedWaitSeconds = -1.f;

    /** Decided at the moment of the request, so a caller can already aim the body at the
     * bag table. This is the "waved aside" flag. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Gate Security")
    bool bBagCheck = false;

    /** World transform of the spot this person should walk to and stand on. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Gate Security")
    FTransform StandTransform;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FMikdashGateCleared, int32, TicketId, int32, Lane, float, TotalWaitSeconds);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FMikdashGateWavedAside, int32, TicketId, int32, BagTableIndex);

/** A modern security checkpoint standing on one gate approach: walk-through metal detector
 * lanes, a bag-scanner table people are occasionally waved aside to, stanchions with belts,
 * a booth, a shoe rack and signage.
 *
 * PROVENANCE, stated plainly. Two different kinds of thing stand at this gate and the
 * receipt in SourceAssets/security-review/sources.md keeps them apart:
 *  - The rule about FOOTWEAR that the signage carries is halacha: a person may not enter
 *    Har HaBayit in shoes (Mishnah Berachos 9:5; Rambam, Hilchos Beis HaBechira 7:2), and
 *    the same mishnah forbids using the Mount as a shortcut and forbids spitting there.
 *    Those are rules of the place. The sign states them; it does not request them.
 *  - The METAL DETECTORS, the BAG SCANNER, the phone rule, the stanchions and the booth are
 *    MODERN STAGING, modelled on the entrance procedure at the Har HaBayit and Kotel plaza
 *    approaches today. No classical source says anything of the kind and none is cited.
 *
 * WHAT THIS ACTOR DOES: it owns the arithmetic (QueueFlowMath.h) and publishes positions and
 * waiting times. Visitors join the shortest lane, stand, step to the arch, pause, walk
 * through, and a fraction of them are waved aside to the bag table before they are released.
 * Guards hold a post and scan their heads across a fixed arc.
 *
 * WHAT THIS ACTOR DOES NOT DO: it never spawns, moves, animates or possesses a body, and it
 * never touches the crowd, resident, transit or service actors. Those systems drive their own
 * bodies and call in here through RequestToPass / GetQueueLength / GetStandTransform. Nothing
 * in this file writes to any of their state.
 */
UCLASS(BlueprintType, Blueprintable)
class MIKDASHRUNTIME_API AMikdashGateSecurity : public AActor
{
    GENERATED_BODY()

public:
    AMikdashGateSecurity();

    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
#if WITH_EDITOR
    virtual void PostEditChangeProperty(struct FPropertyChangedEvent& Event) override;
#endif

    // -----------------------------------------------------------------------
    // Public API for the crowd and resident systems. None of these touch those
    // systems' own state; they only read and advance this checkpoint.
    // -----------------------------------------------------------------------

    /** A visitor asks to pass this checkpoint.
     * @param OutPass  lane, slot, stand transform, wave-aside flag and ticket handle.
     * @return seconds this person should expect to spend before they are clear, or a
     *         negative number when every lane is full and the request was refused.
     * Safe to call every frame from any number of callers; it is O(lanes). */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Gate Security")
    float RequestToPass(FMikdashGatePass& OutPass);

    /** People standing in one detector lane, not counting the person at the arch.
     * Pass Lane = -1 (the default) for everyone anywhere in the checkpoint, which is the
     * number a crowd system wants when it is deciding whether to send anyone here at all. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    int32 GetQueueLength(int32 Lane = -1) const;

    /** Seconds a person joining right now should expect to spend, without joining. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    float GetEstimatedWaitSeconds(bool bAssumeBagCheck = false) const;

    /** Where a live ticket should be standing at this instant. False once it has cleared. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Gate Security")
    bool GetStandTransform(int32 TicketId, FTransform& OutTransform, EMikdashGateStage& OutStage) const;

    /** Stage of a live ticket. Cleared once the person is no longer tracked. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    EMikdashGateStage GetPassStage(int32 TicketId) const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    int32 GetDetectorLaneCount() const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    int32 GetBagTableCount() const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    int32 GetGuardPostCount() const { return GuardPosts.Num(); }

    /** World transform of a detector arch, a bag table, or a guard post. Identity when the
     * index is out of range; check the count first. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    FTransform GetDetectorTransform(int32 Lane) const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    FTransform GetBagTableTransform(int32 Index) const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    FTransform GetGuardPostTransform(int32 Index) const;

    /** Where a guard on that post is looking right now: the post facing plus a scanning
     * yaw offset. The guard's body does not move; only the head turns. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    FRotator GetGuardLookRotation(int32 Index) const;

    /** Yaw offset alone, degrees, for a caller that drives a head bone directly. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    float GetGuardHeadYawOffset(int32 Index) const;

    // -- statistics, for receipts and for a HUD ------------------------------

    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    int32 GetServedCount() const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    int32 GetRefusedCount() const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    float GetMeanWaitSeconds() const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    float GetLongestWaitSeconds() const;

    /** The bound that makes "nobody waits forever" checkable: with these parameters no
     * accepted person can wait longer than this, because a full lane refuses instead of
     * growing. Compare against GetLongestWaitSeconds(). */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    float GetWorstCaseWaitSeconds() const;

    /** True while every completed wait is inside both the closed-form bound and the authored
     * ceiling, and no lane has served out of join order. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    bool IsFair() const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    FString GetFairnessReport() const;

    /** True when FairnessCapSeconds is at least the closed-form worst case, so the ceiling
     * can actually be honoured. False is a configuration error, not a runtime failure. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    bool IsFairnessCeilingAchievable() const;

    /** The largest QueueCapacityPerLane whose worst case fits inside FairnessCapSeconds. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    int32 GetRecommendedQueueCapacity() const;

    /** People selected for a bag check but passed through because the bag line was full. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    int32 GetBagLineFullCount() const;

    // -- events ---------------------------------------------------------------

    /** Fires the frame a person finishes the whole checkpoint. The caller releases the body. */
    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Gate Security")
    FMikdashGateCleared OnVisitorCleared;

    /** Fires when a person leaves the arch and is sent to a bag table instead of on through. */
    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Gate Security")
    FMikdashGateWavedAside OnVisitorWavedAside;

    // -----------------------------------------------------------------------
    // Authored layout. All distances are centimetres in the actor's local frame:
    // +X is the direction of travel through the checkpoint (towards the gate),
    // +Y is to the traveller's right, +Z is up. Placement rotates the whole actor.
    // -----------------------------------------------------------------------

    /** Walk-through detector arches side by side across the approach. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Layout", meta = (ClampMin = "1", ClampMax = "6"))
    int32 DetectorLanes = 2;

    /** Centre-to-centre spacing of the arches, cm. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Layout", meta = (ClampMin = "80.0"))
    float LaneSpacingCm = 180.f;

    /** Gap between two people standing in the same line, cm. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Layout", meta = (ClampMin = "40.0"))
    float QueuePitchCm = 90.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Layout", meta = (ClampMin = "0", ClampMax = "4"))
    int32 BagTables = 1;

    /** Bag tables stand off to one side, behind the arch line. Local offset of the first. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Layout")
    FVector BagTableOffsetCm = FVector(180.f, 320.f, 0.f);

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Layout", meta = (ClampMin = "60.0"))
    float BagTableSpacingCm = 200.f;

    /** Guard posts in the actor's local frame: XY position and the yaw the guard faces. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Layout")
    TArray<FVector> GuardPosts;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Layout")
    TArray<float> GuardPostFacingYaw;

    // -- flow parameters -------------------------------------------------------

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Flow", meta = (ClampMin = "0.0", ClampMax = "600.0"))
    float ArrivalsPerMinute = 40.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Flow", meta = (ClampMin = "0.2", ClampMax = "120.0"))
    float MeanServiceSeconds = 5.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Flow", meta = (ClampMin = "0.0"))
    float ServiceJitterSeconds = 2.f;

    /** The wave-aside probability. Modern staging; not a source figure and not a measurement
     * of any real checkpoint -- an authored rate chosen so the bag table is visibly in use. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Flow", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float BagCheckProbability = 0.18f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Flow", meta = (ClampMin = "0.2"))
    float BagCheckSeconds = 14.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Flow", meta = (ClampMin = "0.0"))
    float BagCheckJitterSeconds = 5.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Flow", meta = (ClampMin = "1", ClampMax = "64"))
    int32 QueueCapacityPerLane = 20;

    /** Hard cap on the line waiting for a bag table. Past it a selected person is passed
     * through unchecked rather than held; that is what bounds the second half of the wait. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Flow", meta = (ClampMin = "1", ClampMax = "64"))
    int32 BagQueueCapacity = 8;

    /** Design ceiling on the total wait. It is only a wish: if it is smaller than
     * GetWorstCaseWaitSeconds() a busy checkpoint will breach it and IsFair() will say so.
     * Check IsFairnessCeilingAchievable() after any change to the flow parameters. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Flow", meta = (ClampMin = "1.0"))
    float FairnessCapSeconds = 360.f;

    /** Deterministic stream seed. The same seed replays the same checkpoint exactly. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Flow")
    int32 RandomSeed = 20260908;

    /** When true the actor generates its own arrivals from ArrivalsPerMinute so the queue
     * timing runs and can be inspected before any crowd system is wired to it. It advances
     * the ARITHMETIC only: it spawns nothing and moves nothing. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Flow")
    bool bSelfDrivenRehearsal = true;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Guards")
    float GuardSweepDegrees = 55.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Guards", meta = (ClampMin = "0.5"))
    float GuardSweepPeriodSeconds = 9.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Gate Security|Guards", meta = (ClampMin = "0.0", ClampMax = "0.49"))
    float GuardSweepDwellFraction = 0.35f;

    /** Draw the lanes, arches, bag tables and guard posts in the editor and with
     * ShowFlag.Collision-style debug. Off by default; nothing is drawn in a shipping run. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Gate Security|Debug")
    bool bDrawDebug = false;

    /** Rebuild the checkpoint from the current properties. Called by BeginPlay and by an
     * editor property change; safe to call at runtime, but it discards everyone in the queue. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Gate Security")
    void RebuildCheckpoint();

    /** The parameters actually in force after clamping, for a receipt. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Gate Security")
    FString GetEffectiveParameterReport() const;

private:
    FTransform LocalToWorld(const FVector& LocalCm, float LocalYaw) const;
    FVector QueueSlotLocal(int32 Lane, int32 SlotIndex) const;
    FVector DetectorLocal(int32 Lane) const;
    FVector BagTableLocal(int32 Index) const;
    MikdashQueue::FFlowParams BuildParams() const;

    MikdashQueue::FCheckpoint Checkpoint;
    MikdashQueue::FGuardScan Scan;
    double ElapsedSeconds = 0.0;
    /** Carries the fractional arrival left over between frames in rehearsal mode. */
    double ArrivalCarrySeconds = 0.0;
    bool bConfigured = false;
};
