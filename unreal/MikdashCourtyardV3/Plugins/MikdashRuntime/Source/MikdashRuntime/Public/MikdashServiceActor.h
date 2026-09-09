#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ServiceScheduleMath.h"
#include "MikdashServiceActor.generated.h"

class USkeletalMesh;
class USkeletalMeshComponent;
class UAnimSequence;
class UMaterialInterface;

/** Which day this actor is depicting. Ordinary day is the default and the only
 * one that ships enabled. See ServiceScheduleMath.h for the sources. */
UENUM(BlueprintType)
enum class EMikdashServiceScenario : uint8
{
    /** The daily lamp service. The paroches line at X -5600 is a hard boundary. */
    OrdinaryDay UMETA(DisplayName = "Ordinary day"),
    /** Separately reviewed scenario, OFF by default. Adds an entry past the
     * paroches and an exit, and depicts nothing else of that day's service. */
    YomKippur UMETA(DisplayName = "Yom Kippur - separately reviewed and off by default")
};

/** How the body's appearance was resolved at run time. */
UENUM(BlueprintType)
enum class EMikdashServiceBodySource : uint8
{
    NotResolved,
    AuthoredActor      UMETA(DisplayName = "Authored actor already in the map"),
    MetaHuman          UMETA(DisplayName = "MetaHuman found under /Game/MetaHumans"),
    ConfiguredMesh     UMETA(DisplayName = "Mesh set on this actor"),
    PilgrimRigV3       UMETA(DisplayName = "PilgrimRigV3 skeletal mesh"),
    PilgrimRigV2       UMETA(DisplayName = "PilgrimRigV2 skeletal mesh"),
    NoneAvailable      UMETA(DisplayName = "No usable mesh - sequence refused")
};

/**
 * Drives ONE service character along an authored sequence of stations with
 * timed actions: into the Heikhal, onto the three-step stone east of the
 * menorah, tending and kindling the seven lamps in two groups, then a
 * placeholder pause at the golden altar, then out. It repeats on an interval.
 *
 * WHAT IS DEPICTED, AND WHAT IS NOT ASSERTED
 *  - This is an authored depiction, not a rules engine and not rabbinic
 *    approval. Every timing number is a pacing choice.
 *  - The daily lamp service is ordinarily an ordinary kohen's (Rambam, Biat
 *    HaMikdash 2:1). The Kohen Gadol may perform any service he wishes at any
 *    time, and Mishnah Yoma 1:2 (Yoma 14a) names the lamps among the services
 *    he performs; Rambam, Klei HaMikdash 5:12. So depicting him here is
 *    legitimate, and that is what this actor depicts.
 *  - He may walk the Heikhal for service (Klei HaMikdash 5:11), and only for
 *    service (Biat HaMikdash 2:2): this actor has no idle wander behaviour.
 *  - He may not enter the Kodesh HaKodashim except on Yom Kippur (Vayikra
 *    16:2; Biat HaMikdash 2:1). On OrdinaryDay the paroches line at X -5600 is
 *    enforced twice: by ServiceScheduleMath before the sequence starts, and
 *    again on every single move below. A violation stops the sequence.
 *  - The full source register, including the disputed and the merely authored
 *    items, is SourceAssets/runtime-review/kohen-service/sources.md.
 *
 * Movement is the same direct-corridor approach the resident system uses: this
 * map has no NavMesh, so legs are straight lines between stations, each
 * reviewed with a floor trace and a capsule sweep before it is walked. A leg
 * that is blocked HOLDS the body where it stands and is recorded. Nothing is
 * ever teleported through geometry.
 */
UCLASS(BlueprintType)
class MIKDASHRUNTIME_API AMikdashServiceActor : public AActor
{
    GENERATED_BODY()
public:
    AMikdashServiceActor();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

    // ---- controls -------------------------------------------------------
    /** Master switch. When false the actor stands still and does nothing. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service")
    bool bSequenceEnabled = false;

    /** Start the sequence at BeginPlay. Off by default so placement alone
     * never animates anything before a visual review. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service")
    bool bStartOnBeginPlay = false;
    /** Experimental opt-in physical motor; disabled until candidate runtime acceptance. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service")
    bool bUseGroundedMovement = false;

    /** Seconds of standing still between the end of one sequence and the next.
     * 0 restarts immediately. A pacing choice, not a sourced interval. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service", meta = (ClampMin = "0.0"))
    float RepeatIntervalSeconds = 90.0f;

    /** Centimetres per second along a leg. A dignified walk, authored. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service", meta = (ClampMin = "1.0"))
    float WalkSpeedCmPerSec = 90.0f;

    /** OrdinaryDay ships enabled. YomKippur is a separate scenario that must be
     * chosen deliberately; it is the ONLY way any station may pass X -5600. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service")
    EMikdashServiceScenario ServiceScenario = EMikdashServiceScenario::OrdinaryDay;

    // ---- pacing (all authored, none sourced) ----------------------------
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Pacing", meta = (ClampMin = "0.1"))
    float PerLampSeconds = 14.0f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Pacing", meta = (ClampMin = "0.0"))
    float ApproachSeconds = 8.0f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Pacing", meta = (ClampMin = "0.0"))
    float DoorwaySeconds = 4.0f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Pacing", meta = (ClampMin = "0.0"))
    float StoneSeconds = 6.0f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Pacing", meta = (ClampMin = "0.0"))
    float KuzSeconds = 5.0f;
    /** The service that falls between the two groups of lamps happens outside
     * the Heikhal and is not depicted; this is only the wait for it. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Pacing", meta = (ClampMin = "0.0"))
    float WithdrawSeconds = 20.0f;
    /** Placeholder pause at the golden altar. The smoke is another system's. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Pacing", meta = (ClampMin = "0.0"))
    float AltarSeconds = 30.0f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Pacing", meta = (ClampMin = "0.0"))
    float InnerSeconds = 20.0f;

    /** The commissioned three-to-six-minute window. A plan outside it is
     * refused rather than silently accepted. Widened automatically for the
     * Yom Kippur scenario by InnerSeconds plus its extra walking. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Pacing", meta = (ClampMin = "1.0"))
    float MinLoopSeconds = 180.0f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Pacing", meta = (ClampMin = "1.0"))
    float MaxLoopSeconds = 360.0f;

    // ---- station geometry -----------------------------------------------
    /** Leave empty to use the anchors measured from the placed assets
     * (menorah v4 at (-5330, 315.176), golden altar at (-4650, 0), Heikhal
     * floor X -5600..-3600). The release script writes them explicitly so a
     * human can review the numbers in the map. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Stations")
    // Immutable legacy50 authored anchors; runtime decodes once through the world frame.
    // Candidate placement must not pre-convert these properties.
    FVector UlamApproachPoint = FVector(-3200.0, 0.0, 925.0);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Stations")
    FVector DoorwayPoint = FVector(-3450.0, 0.0, 925.0);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Stations")
    FVector TendingStonePoint = FVector(-5239.0, 315.176, 975.0);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Stations")
    FVector GoldenAltarPoint = FVector(-4650.0, 0.0, 925.0);
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Stations")
    FVector MenorahPoint = FVector(-5330.0, 315.176, 925.0);
    /** Yom Kippur scenario only; ignored entirely on an ordinary day. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Stations")
    FVector InnerStandPoint = FVector(-6100.0, 0.0, 925.0);

    // ---- the body -------------------------------------------------------
    /** Optional: a body already placed and dressed in the map. When set it is
     * used as-is and no lookup happens. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category = "Kohen service|Body")
    TObjectPtr<AActor> AuthoredBody;

    /** Optional explicit mesh. Takes priority over automatic MetaHuman/pilgrim discovery. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Body")
    TObjectPtr<USkeletalMesh> ConfiguredMesh;

    /** Extra candidate mesh paths tried before the built-in fallbacks. Another
     * agent enabling the MetaHuman plugins can add one here without a rebuild. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Body")
    TArray<FSoftObjectPath> ExtraMeshCandidates;

    /** Material slots on the body that receive the Kohen Gadol garment variant. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Body")
    TArray<FName> GarmentMaterialSlots;

    /** Kohen Gadol garment variant. The eight golden garments are described in
     * SourceAssets/runtime-review/kohen-service/sources.md against the Temple
     * Institute photographs in SourceAssets/reference-ti/ (gitignored, used
     * with the owners' permission). Until a dedicated variant exists this
     * degrades to GarmentFallbacks and says so in GetBodyStatus(). */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Body")
    TObjectPtr<UMaterialInterface> GarmentMaterial;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Body")
    TArray<FSoftObjectPath> GarmentFallbacks;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Body")
    TObjectPtr<UAnimSequence> IdleAnimation;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Body")
    TObjectPtr<UAnimSequence> WalkAnimation;
    /** Physical visual scale/facing for the explicitly configured body, never amah-scaled. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Body")
    float ConfiguredBodyVisualScale = 1.0f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Kohen service|Body")
    float ConfiguredBodyYawDegrees = 0.0f;

    // ---- runtime control -------------------------------------------------
    UFUNCTION(BlueprintCallable, Category = "Kohen service")
    bool StartService();
    UFUNCTION(BlueprintCallable, Category = "Kohen service")
    void StopService();
    UFUNCTION(BlueprintCallable, Category = "Kohen service")
    void SetServicePaused(bool bPaused);

    // ---- read-back for the dialog / prompt system ------------------------
    /** Plain language: what this figure is doing right now. Never a ruling. */
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    FString GetCurrentActionText() const;

    /** One line naming the scenario, the boundary and what is not depicted. */
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    FString GetScenarioDescription() const;

    UFUNCTION(BlueprintPure, Category = "Kohen service")
    bool IsServiceActive() const { return bActive; }
    /** Versioned placement guard: anchors remain legacy50 and decode once at runtime. */
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    int32 GetServiceSceneFrameAdapterVersion() const { return 1; }
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    int32 GetServiceBodyAdapterVersion() const { return 1; }
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    int32 GetServiceMotorAdapterVersion() const { return 1; }
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    int32 GetServiceGroundedAdapterVersion() const { return 1; }
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    FVector GetServiceFeetLocation() const;
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    bool IsServiceGrounded() const;
    /** Raw movement support diagnostics, distinct from visual-foot floor agreement. */
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    int32 GetServiceMovementMode() const;
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    bool HasServiceWalkableSupport() const;
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    float GetServiceMovementFloorDistance() const;
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    FVector GetServiceMovementFloorImpact() const;
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    bool IsServicePaused() const { return bPaused; }
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    bool IsServiceDwelling() const { return Runner.Where().State == MikdashService::Phase::Dwelling; }
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    float GetServicePhaseSeconds() const { return static_cast<float>(Runner.Where().InPhaseSeconds); }
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    FVector GetServiceStationLocation(int32 Index) const;
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    int32 GetServiceCurrentStationIndex() const { return static_cast<int32>(Runner.Where().Index); }
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    FString GetServiceStatus() const { return Status; }
    /** Which mesh and which garment material were actually used, and why. */
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    FString GetBodyStatus() const { return BodyStatus; }
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    EMikdashServiceBodySource GetBodySource() const { return BodySource; }
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    FString GetResolvedMeshPath() const { return ResolvedMeshPath; }
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    FString GetResolvedGarmentPath() const { return ResolvedGarmentPath; }
    /** 1..7 while a lamp is being tended, otherwise 0. */
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    int32 GetCurrentLamp() const;
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    int32 GetCompletedSequences() const;
    /** How many legs were found blocked. Non-zero means the route needs work. */
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    int32 GetBlockedLegCount() const;
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    float GetPlannedLoopSeconds() const;
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    int32 GetStationCount() const;
    UFUNCTION(BlueprintPure, Category = "Kohen service")
    AActor* GetServiceBody() const { return Body; }

private:
    bool BuildSequence(FString& OutReason);
    bool ResolveBody(FString& OutReason);
    USkeletalMesh* FindBestMesh(EMikdashServiceBodySource& OutSource, FString& OutPath) const;
    USkeletalMesh* FindMetaHumanMesh(FString& OutPath) const;
    bool ApplyGarment(USkeletalMeshComponent* Mesh, FString& OutReason);
    /** Floor trace plus capsule sweep along the straight leg, exactly the
     * review the resident population performs. False means blocked. */
    bool ReviewLeg(const FVector& From, const FVector& To) const;
    /** Second, independent check that this move respects the scenario gate.
     * If it ever fails the sequence stops; it never clamps and continues. */
    bool MoveIsPermitted(const FVector& To, FString& OutReason) const;
    void PlaceBody(const FVector& Feet, const FVector& FaceTarget);
    void UpdateBodyAnimation(bool bMoving);
    void TickGrounded(float DeltaSeconds);
    bool GroundedDestinationPermitted(const FVector& Feet) const;
    bool MotorSegmentPermitted(const FVector& From,const FVector& To) const;
    FVector LastMotorFeet = FVector::ZeroVector;
    double MotorStallSeconds = 0;
    bool bMotorRequestBlocked = false;
    std::size_t MotorBlockedIndex = 0;
    std::uint64_t MotorBlockedGeneration = 0;
    float ActiveBodyYawDegrees = 0.0f;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> PlayingBodyAnimation;
    MikdashService::Scenario NativeScenario() const;

    UPROPERTY(Transient) TObjectPtr<AActor> Body;
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> BodyMesh;
    bool bBodyWasSpawned = false;

    MikdashService::Sequencer Runner;
    MikdashService::Plan Sequence;
    MikdashService::Geometry SceneGeometry;
    bool bActive = false;
    bool bPaused = false;
    /** Cached leg review; refreshed on a new leg and while held. */
    bool bLegBlocked = false;
    int32 ReviewedLegIndex = -1;
    double NextReviewAtSeconds = 0.0;

    FString Status = TEXT("Inactive: the service sequence has not been started.");
    FString BodyStatus = TEXT("No body resolved yet.");
    FString ResolvedMeshPath;
    FString ResolvedGarmentPath;
    EMikdashServiceBodySource BodySource = EMikdashServiceBodySource::NotResolved;
};
