#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "UObject/Interface.h"
#include "BoardingBridgeMath.h"
#include "CrowdFieldMath.h"
#include "MikdashTransit.h"
#include "MikdashTransitBoardingBridge.generated.h"

class AMikdashCrowdField;
class UHierarchicalInstancedStaticMeshComponent;
class UStaticMesh;

// ---------------------------------------------------------------------------
// The contract the crowd owner may implement. The bridge PROBES for it with Cast<> and
// works without it; AMikdashCrowdField does not implement it today and this header does
// not ask it to. See SourceAssets/transit-review/BRIDGE-20260908.md, "What the crowd owner
// must expose", for the exact semantics each method must honour.
// ---------------------------------------------------------------------------

/** One request from the bridge to the background crowd: take over (or hand over) a party
 * of figures at a world point. Everything is world centimetres; Seed is the bridge's
 * deterministic (stop, run) seed so the crowd's own hashing stays reproducible. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashCrowdPartyRequest
{
    GENERATED_BODY()

    /** Where the party is right now (alighting hand-over) or where it should gather from (boarding). */
    UPROPERTY(BlueprintReadOnly, Category="Crowd") FVector AnchorCm = FVector::ZeroVector;
    /** Unit vector pointing away from the vehicle; the crowd must never place anyone on the other side of the door plane. */
    UPROPERTY(BlueprintReadOnly, Category="Crowd") FVector OutwardDirection = FVector::ForwardVector;
    /** People in the party; 1 is a legitimate individual. */
    UPROPERTY(BlueprintReadOnly, Category="Crowd") int32 Count = 0;
    /** Deterministic seed for this (stop, run, direction). */
    UPROPERTY(BlueprintReadOnly, Category="Crowd") int32 Seed = 0;
    /** Seconds the bridge can wait for the answer to take effect (the remaining dwell). */
    UPROPERTY(BlueprintReadOnly, Category="Crowd") float SecondsAvailable = 0.f;
    /** True when the party should stand rather than walk on. */
    UPROPERTY(BlueprintReadOnly, Category="Crowd") bool bStanding = false;
    /** Where standing members face (the Mount). */
    UPROPERTY(BlueprintReadOnly, Category="Crowd") FVector FacingTarget = FVector::ZeroVector;
    /** The transit stop this concerns, for the crowd's own bookkeeping. */
    UPROPERTY(BlueprintReadOnly, Category="Crowd") int32 GlobalStopIndex = INDEX_NONE;
};

UINTERFACE(MinimalAPI, meta=(CannotImplementInterfaceInBlueprint))
class UMikdashCrowdPartyHost : public UInterface
{
    GENERATED_BODY()
};

/** Implemented by a crowd that can absorb and release parties at arbitrary world points.
 * All three must refuse atomically: either the whole party is handled or nothing changed. */
class MIKDASHRUNTIME_API IMikdashCrowdPartyHost
{
    GENERATED_BODY()
public:
    /** Adopt Count figures standing at/around Request.AnchorCm as one stable party (or an
     * individual when Count is 1) of the zone containing the anchor. Returns false, changing
     * nothing, when the anchor is in no zone, inside a keep-out skirt, or the crowd is full. */
    virtual bool TryAdoptParty(const FMikdashCrowdPartyRequest& Request, TArray<int32>& OutAgentIndices) = 0;
    /** Remove up to Count valid agents nearest Point (within MaxRadiusCm, same zone as Point)
     * and return their positions, so the bridge can walk them to the door. Returns how many
     * were released; 0 changes nothing. */
    virtual int32 TryReleaseNearest(const FVector& Point, int32 Count, float MaxRadiusCm, TArray<FVector>& OutPositions) = 0;
    /** Keep-out-only legality of a point (NO zone requirement), for stop aprons that sit
     * outside every authored crowd zone. */
    virtual bool IsCrowdPointAllowed(const FVector& Point, float RadiusCm) const = 0;
};

// ---------------------------------------------------------------------------
// Plain C++ runtime state. Never reflected, never serialized, rebuilt every start.
// ---------------------------------------------------------------------------

/** One animated figure in one group. */
struct FMikdashBoardingFigure
{
    FVector From = FVector::ZeroVector;      // feet, world
    FVector To = FVector::ZeroVector;        // feet, world
    FVector Position = FVector::ZeroVector;
    double DepartAt = 0.0;                   // transit seconds
    double ArriveAt = 0.0;
    double HoldUntil = 0.0;                  // photographers: when they stop photographing
    float Speed = 100.f;
    float Yaw = 0.f;
    float Scale = 1.f;
    float Tint = 0.f;
    float Phase = 0.f;
    int32 Group = INDEX_NONE;
    int32 Pose = 0;
    uint8 bActive : 1;
    uint8 bVisible : 1;
    uint8 bAlighting : 1;
    uint8 bPhotographer : 1;
    uint8 bHolding : 1;
    FMikdashBoardingFigure() : bActive(0), bVisible(0), bAlighting(0), bPhotographer(0), bHolding(0) {}
};

/** One admitted boarding or alighting group. Groups are what the concurrency cap counts. */
struct FMikdashBoardingGroup
{
    FMikdashPassengerExchange Exchange;      // identity, or a synthesised one when only the legacy hook fired
    bool bHasExchange = false;
    bool bAlighting = false;
    bool bActive = false;
    double StartAt = 0.0;                    // transit seconds when the doors opened
    double Deadline = 0.0;                   // transit seconds by which every boarder is through the door
    int32 Figures = 0;
    int32 Remaining = 0;
    /** Alighting only: non-photographers wait for their companions at the dispersal spot and
     * are handed to the crowd (or leave) together, as one party. */
    int32 WalkersTotal = 0;
    int32 WalkersArrived = 0;
    uint32 Seed = 0;
};

/**
 * Bridges AMikdashTransit's boarding hooks to background figures at each stop.
 *
 * WHAT IT DOES. When a bus or tram opens its doors, the transit actor fires
 * OnRequestAlighting and OnRequestBoarding with (stop, count, door point, dwell seconds).
 * This actor turns the alighting request into figures that step off at the door, walk onto
 * the kerb-side apron and disperse, with SuggestPhotographerCount of them standing to
 * photograph the Mount for a few seconds first; and the boarding request into figures
 * waiting on the apron who converge on the door, timed so the last one is through it before
 * the doors close, and vanish into the vehicle. Group count is capped (MaxConcurrentGroups),
 * group size is bounded by what the doors can pass in the dwell and by the free figure pool,
 * and the plan is deterministic in (stop, run).
 *
 * WHAT IT IS NOT. It is not the crowd. AMikdashCrowdField exposes no way to add, remove or
 * relocate an instance, and no authored crowd zone contains a transit stop, so the figures
 * here are the bridge's OWN instances (the crowd's pose meshes, the crowd's custom-data
 * convention) that appear on the apron and disappear into the vehicle or the street. If the
 * crowd owner implements IMikdashCrowdPartyHost, alighters are handed over as real parties
 * and boarders are drawn from the real waiting crowd; the bridge probes for it at start.
 * No figure ever crosses a keep-out, stands inside the vehicle body, or teleports.
 *
 * WHY AN ACTOR. Every runtime system in this plugin is an opt-in placed actor with
 * bActivateOnBeginPlay false, placed by a guarded, checkpointed release script and read
 * back from the saved map. A world subsystem would activate in every world (the protected
 * maps, the 48 cm candidate, editor previews), could not be checkpointed or read back, and
 * could not carry per-map configuration such as the Mount focus point.
 *
 * COEXISTENCE. AMikdashTransitCrowdCoordinator is an earlier transfer renderer bound to
 * OnPassengerExchange. Running both would double every exchange, so this actor refuses to
 * start while a coordinator with bActivateOnBeginPlay is in the level (bRefuseIfCoordinatorActive).
 */
UCLASS(BlueprintType, meta=(DisplayName="Mikdash Transit Boarding Bridge"))
class MIKDASHRUNTIME_API AMikdashTransitBoardingBridge : public AActor
{
    GENERATED_BODY()
public:
    AMikdashTransitBoardingBridge();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;

    /** Fixed number of pose components, one per crowd pose mesh, plus one for the photographer pose. */
    static constexpr int32 MaxPoseComponents = 6;

    // -- api ---------------------------------------------------------------

    /** Find (or use) the transit and crowd actors, build the figure pool, bind the hooks.
     * Returns false and sets the status string when the level is not usable. Safe to call again. */
    UFUNCTION(BlueprintCallable, Category="Transit|Bridge") bool InitializeBridge();
    UFUNCTION(BlueprintCallable, Category="Transit|Bridge") void ShutdownBridge();

    UFUNCTION(BlueprintPure, Category="Transit|Bridge") bool IsBridgeActive() const { return bRunning; }
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") FString GetBridgeStatus() const { return Status; }
    /** One line a receipt can quote. */
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") FString GetBridgeSummary() const;
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") int32 GetActiveGroupCount() const;
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") int32 GetActiveFigureCount() const;
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") int32 GetGroupsStarted() const { return GroupsStarted; }
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") int32 GetGroupsRefusedByCap() const { return GroupsRefusedCap; }
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") int32 GetGroupsRefusedByGeometry() const { return GroupsRefusedGeometry; }
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") int32 GetGroupsRefusedByStop() const { return GroupsRefusedStop; }
    /** Groups refused because the figure pool was too thin to show even MinPeoplePerGroup. */
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") int32 GetGroupsRefusedByPool() const { return GroupsRefusedPool; }
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") int32 GetPeopleBoarded() const { return PeopleBoarded; }
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") int32 GetPeopleAlighted() const { return PeopleAlighted; }
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") int32 GetPeopleTrimmed() const { return PeopleTrimmed; }
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") int32 GetPhotographerCount() const { return Photographers; }
    /** Boarders that were still walking when the doors closed. Zero by construction; reported, not hidden. */
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") int32 GetOverrunCount() const { return Overruns; }
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") int32 GetGroundTraceMissCount() const { return GroundMisses; }
    /** True when the crowd actor implements IMikdashCrowdPartyHost and hand-over is live. */
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") bool IsCrowdHandoverAvailable() const { return CrowdHost != nullptr; }
    /** Stops refused because GetStopProjectionErrorCm exceeded MaxStopProjectionErrorCm. */
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") TArray<int32> GetRefusedStopIndices() const;
    UFUNCTION(BlueprintPure, Category="Transit|Bridge") bool IsStopAccepted(int32 GlobalStopIndex) const;

    // -- wiring ------------------------------------------------------------

    /** The transit and crowd actors. Left unset, BeginPlay finds exactly one of each in the
     * level when bAutoFindActors is true and refuses when it finds none or several. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge") TObjectPtr<AMikdashTransit> Transit;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge") TObjectPtr<AMikdashCrowdField> CrowdField;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge") bool bAutoFindActors = true;
    /** Project convention: placing the actor changes nothing until a release script turns it on. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge") bool bActivateOnBeginPlay = false;
    /** Refuse to start while an AMikdashTransitCrowdCoordinator with bActivateOnBeginPlay is present. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge") bool bRefuseIfCoordinatorActive = true;

    // -- limits ------------------------------------------------------------

    /** Boarding and alighting groups animated at once, across every stop. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Limits", meta=(ClampMin="1", ClampMax="32"))
    int32 MaxConcurrentGroups = 6;
    /** Figure pool: HISM instances allocated once at start, shared by every group. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Limits", meta=(ClampMin="8", ClampMax="1024"))
    int32 MaxFigures = 240;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Limits", meta=(ClampMin="1", ClampMax="200"))
    int32 MaxPeoplePerGroup = 40;
    /** A group sized below this is refused whole rather than shown as a straggler. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Limits", meta=(ClampMin="1", ClampMax="10"))
    int32 MinPeoplePerGroup = 1;
    /** Figures advanced per frame, round robin. Deadlines are checked for every figure every frame. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Limits", meta=(ClampMin="1", ClampMax="1024"))
    int32 UpdateBudget = 64;

    // -- timing ------------------------------------------------------------

    /** Doorways the figures may use. The authored bus has one door leaf set, the tram several;
     * this is a pacing parameter, not a claim about a vehicle model. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Timing", meta=(ClampMin="1", ClampMax="6"))
    int32 DoorsPerVehicle = 2;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Timing", meta=(ClampMin="0.2", ClampMax="5.0"))
    float SecondsPerPersonPerDoor = 0.8f;
    /** The last boarder is through the door this long before the dwell ends. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Timing", meta=(ClampMin="0.0", ClampMax="5.0"))
    float CloseMarginSeconds = 1.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Timing", meta=(ClampMin="30.0"))
    float WalkSpeedMinCmPerSecond = 90.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Timing", meta=(ClampMin="30.0"))
    float WalkSpeedMaxCmPerSecond = 130.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Timing", meta=(ClampMin="1.0"))
    float PhotographerHoldMinSeconds = 4.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Timing", meta=(ClampMin="1.0"))
    float PhotographerHoldMaxSeconds = 9.f;

    // -- geometry ----------------------------------------------------------

    /** A stop whose authored position sits further than this from the route the runtime
     * built is refused: its door point and platform face cannot be trusted. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Geometry", meta=(ClampMin="0.0"))
    float MaxStopProjectionErrorCm = 250.f;
    /** No figure stands closer than this to the door plane on the kerb side; the vehicle body is on the other side. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Geometry", meta=(ClampMin="20.0"))
    float DoorClearanceCm = 60.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Geometry", meta=(ClampMin="60.0")) float GatherNearCm = 110.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Geometry", meta=(ClampMin="100.0")) float GatherFarCm = 520.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Geometry", meta=(ClampMin="90.0")) float GatherHalfWidthCm = 450.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Geometry", meta=(ClampMin="200.0")) float DispersalMinCm = 600.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Geometry", meta=(ClampMin="200.0")) float DispersalMaxCm = 1400.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Geometry", meta=(ClampMin="150.0")) float PhotoSpotMinCm = 300.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Geometry", meta=(ClampMin="150.0")) float PhotoSpotMaxCm = 520.f;
    /** What photographers face: the Mount. World centimetres; the release script sets it per map. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Geometry") FVector MountFocusCm = FVector(0.0, 0.0, 300.0);
    /** Trace down for the ground under each figure; fall back to the door's height where the
     * trace misses (commandlets, NullRHI) and count the miss. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Geometry") bool bTraceGround = true;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Geometry", meta=(ClampMin="10.0")) float GroundTraceToleranceCm = 150.f;
    /** One 34/96 capsule sweep per planned walk against static blockers (the crowd groups'
     * own convention). Vehicles are NoCollision instances, so the door plane, not this sweep,
     * is what keeps figures out of them. Sweeps return nothing in NullRHI; that is permissive, not proof. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Geometry") bool bSweepStaticObstacles = true;

    // -- look --------------------------------------------------------------

    /** Optional standing pose for photographers. Left unset, they hold the walk pose still with
     * the crowd material's standing flag, which is what the crowd's own standers do. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Look") TObjectPtr<UStaticMesh> PhotographerPoseMesh;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Look", meta=(ClampMin="0.5", ClampMax="1.5")) float FigureScaleMin = 0.92f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Look", meta=(ClampMin="0.5", ClampMax="1.5")) float FigureScaleMax = 1.08f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge|Look") bool bCastShadows = false;

    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Bridge") int32 Seed = 20260908;

private:
    UPROPERTY(Transient) TArray<TObjectPtr<UHierarchicalInstancedStaticMeshComponent>> PoseComponents;
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> PhotoComponent;

    TArray<FMikdashBoardingFigure> Figures;
    TArray<FMikdashBoardingGroup> Groups;
    TArray<FMikdashPassengerExchange> RecentExchanges;   // ring of the rich requests, matched by the legacy hooks
    TMap<int32, bool> StopAcceptance;                    // GlobalStopIndex -> accepted
    TMap<int32, int32> StopArrivals;                     // fallback run counter when no rich request matched
    TSet<UHierarchicalInstancedStaticMeshComponent*> TouchedThisFrame;

    // Keep-outs and zones flattened from the crowd's runtime geometry, in the layout CrowdFieldMath takes.
    TArray<MikdashCrowd::Vec2> KeepOutPoints;
    TArray<int32> KeepOutStarts;
    TArray<int32> KeepOutCounts;
    TArray<MikdashCrowd::Vec2> ZonePoints;
    TArray<int32> ZoneStarts;
    TArray<int32> ZoneCounts;
    float KeepOutMarginCm = 150.f;

    IMikdashCrowdPartyHost* CrowdHost = nullptr;
    int32 ActivePoseCount = 0;
    int32 Cursor = 0;
    bool bRunning = false;
    FString Status = TEXT("inactive");

    int32 GroupsStarted = 0, GroupsRefusedCap = 0, GroupsRefusedGeometry = 0, GroupsRefusedStop = 0, GroupsRefusedPool = 0;
    int32 PeopleBoarded = 0, PeopleAlighted = 0, PeopleTrimmed = 0, Photographers = 0, Overruns = 0, GroundMisses = 0;

    UFUNCTION() void HandleExchange(const FMikdashPassengerExchange& Request);
    UFUNCTION() void HandleBoarding(int32 GlobalStopIndex, int32 Count, FVector BoardingPoint, float SecondsAvailable, FName RouteId);
    UFUNCTION() void HandleAlighting(int32 GlobalStopIndex, int32 Count, FVector BoardingPoint, float SecondsAvailable, FName RouteId);

    bool ResolveActors();
    bool CoordinatorIsActive() const;
    void BuildPool();
    void CacheCrowdGeometry();
    bool StopAccepted(int32 GlobalStopIndex);
    bool MatchExchange(int32 GlobalStopIndex, int32 Count, const FVector& BoardingPoint, FMikdashPassengerExchange& Out) const;
    void StartGroup(int32 GlobalStopIndex, int32 Count, const FVector& BoardingPoint, float SecondsAvailable, FName RouteId, bool bAlighting);
    double Now() const;
    bool GroundAt(const FVector& Approximate, FVector& Feet);
    bool PointAllowed(const FVector& Feet) const;
    bool SegmentAllowed(const FVector& From, const FVector& To) const;
    int32 FreeFigure() const;
    int32 FreeFigureCount() const;
    void Render(int32 FigureIndex, bool bStanding);
    void Hide(int32 FigureIndex);
    void FinishFigure(int32 FigureIndex);
    void HandOverWalkers(int32 GroupIndex);
    void RetireGroup(int32 GroupIndex);
};
