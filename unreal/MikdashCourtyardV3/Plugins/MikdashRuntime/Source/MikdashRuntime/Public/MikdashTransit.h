#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TransitMath.h"
#include "MikdashTransit.generated.h"

class UHierarchicalInstancedStaticMeshComponent;
class UStaticMesh;

/** One authored stop or station on a route. Positions are WORLD centimetres: the actor
 * projects each onto the arc table it builds itself, so nothing depends on the generator
 * and the runtime densifying the polyline identically. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashTransitStop
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") FString Name;
    /** World position on the route centreline. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") FVector WorldPosition = FVector::ZeroVector;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") float DwellMinSeconds = 20.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") float DwellMaxSeconds = 40.f;
    /** How many pedestrians one call asks the crowd system for, before the density multiplier. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") int32 BoardingMinPeople = 5;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") int32 BoardingMaxPeople = 20;
    /** Lateral offset from the centreline to the shelter/platform face, driver's right positive. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") float FurnitureOffsetCm = 560.f;
};

/** One authored route: a closed out-and-back circuit in world centimetres.
 *
 * Because a lane offset is always applied to the driver's right, the outbound half of the
 * circuit runs down one side of the road and the return half down the other. That IS the
 * two-way traffic; there is no second route and no opposing-direction logic. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashTransitRoute
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") FName Id;
    /** True for the authored light-rail line, which is served by consists on a headway
     * rather than by free-running road traffic. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") bool bRail = false;
    /** Control points of the closed circuit. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") TArray<FVector> Points;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") TArray<FMikdashTransitStop> Stops;
    /** Catmull-Rom samples per control segment. 1 reproduces the polyline exactly. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") int32 SmoothingPerSegment = 4;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") float LaneOffsetCm = 340.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") float RideHeightCm = 6.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") float SpeedLimitCmPerSecond = 830.f;
    /** Share of the road-vehicle budget this route receives. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") float VehicleWeight = 1.f;
    /** Share of this route's vehicles that are buses rather than cars. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") float BusShare = 0.2f;
};

/** The four material-group meshes of one vehicle body, plus its physical size.
 *
 * Four groups and not more: every group is another HISM component and another transform
 * write per vehicle per update. Only Paint varies per instance, through per-instance
 * custom data floats 0..2. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashTransitBody
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") FName Key;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") TObjectPtr<UStaticMesh> Paint;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") TObjectPtr<UStaticMesh> Glass;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") TObjectPtr<UStaticMesh> Dark;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") TObjectPtr<UStaticMesh> Lens;
    /** Bumper-to-bumper length, used as the following clearance. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") float LengthCm = 460.f;
    /** True for a body that serves stops. Cars do not. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") bool bServesStops = false;
    /** Sliding door leaf mesh set, empty for cars. Leaves are instanced separately so
     * the actor can offset them; DoorLocalOffsets gives one entry per doorway. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") TObjectPtr<UStaticMesh> DoorLeafPaint;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") TObjectPtr<UStaticMesh> DoorLeafGlass;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Transit") TArray<FVector> DoorLocalOffsets;
};

/** Broadcast when a vehicle's doors finish opening (boarding) or begin to shut (alighting).
 *
 * RouteIndex/StopIndex address the authored stop; GlobalStopIndex is a flat index the
 * crowd system can key on directly. BoardingPoint is the world point at the vehicle's
 * door on the kerb side -- the point the pedestrians should converge on -- and
 * SecondsAvailable is how long the doors will remain open. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_FiveParams(FMikdashTransitBoardingSignature,
    int32, GlobalStopIndex, int32, Count, FVector, BoardingPoint, float, SecondsAvailable, FName, RouteId);

// ---------------------------------------------------------------------------
// Plain C++ runtime state. Rebuilt at every start from the authored properties above,
// never reflected and never serialized. Declared at file scope rather than nested in
// the UCLASS so Unreal Header Tool never has to parse them.
// ---------------------------------------------------------------------------

/** One route's densified arc table and the stop distances projected onto it. */
struct FMikdashTransitRouteRuntime
{
    TArray<MikdashTransit::Vec3> Points;
    TArray<double> Cumulative;
    double LengthCm = 0.0;
    TArray<double> StopDistances;      // parallel to the route's Stops
    TArray<double> StopErrorCm;        // planar residual of each authored stop position
    TArray<int32> GlobalStopIndices;
    TArray<int32> VehicleIndices;      // ring order by start distance
};

/** One road vehicle. Four instance ids, a scalar position along its route, and a stop
 * cycle. No actor, no component, no physics. */
struct FMikdashTransitVehicle
{
    int32 RouteIndex = 0;
    int32 BodyIndex = 0;
    /** Fixed for the life of the run: no vehicle can overtake another on its own route,
     * so the ring order established at seeding never changes. */
    int32 LeaderVehicle = INDEX_NONE;
    int32 InstanceIds[4] = {INDEX_NONE, INDEX_NONE, INDEX_NONE, INDEX_NONE};
    int32 DoorInstanceStart = INDEX_NONE;
    int32 DoorInstanceCount = 0;
    double DistanceCm = 0.0;
    double SpeedCmPerSecond = 0.0;
    MikdashTransit::StopState Stop;
    MikdashTransit::FollowParams Follow;
    MikdashTransit::DwellConfig Dwell;
    bool bServesStops = false;
};

/** One light-rail consist. Slots are pre-allocated; dispatch only flips bActive. */
struct FMikdashTransitTrain
{
    bool bActive = false;
    double DistanceCm = 0.0;
    double SpeedCmPerSecond = 0.0;
    double TravelledCm = 0.0;
    int32 Id = 0;
    TArray<int32> CarInstanceIds;      // four per car, in body order
    TArray<int32> DoorInstanceIds;
    MikdashTransit::StopState Stop;
    MikdashTransit::FollowParams Follow;
    MikdashTransit::DwellConfig Dwell;
};

/** One vehicle body's four HISM components plus its door leaves. The components are
 * owned (and kept alive) by AMikdashTransit::OwnedComponents. */
struct FMikdashTransitBodyComponents
{
    UHierarchicalInstancedStaticMeshComponent* Groups[4] = {nullptr, nullptr, nullptr, nullptr};
    UHierarchicalInstancedStaticMeshComponent* DoorPaint = nullptr;
    UHierarchicalInstancedStaticMeshComponent* DoorGlass = nullptr;
    TArray<FVector> DoorLocalOffsets;
    double LengthCm = 460.0;
};

/**
 * Instanced road and rail traffic for the arrival approaches.
 *
 * ONE actor drives everything. Cars, buses and trams are HISM instances, never actors:
 * a vehicle costs four instance transforms (Paint, Glass, Dark, Lens) and a few dozen
 * bytes of plain C++ state. Per-frame work is bounded by a round-robin window exactly
 * like AMikdashCrowdField's, so the cost does not grow with the vehicle count.
 *
 * The arithmetic lives in TransitMath.h and is covered by a standalone test
 * (SourceAssets/runtime-review/transit/tests.json). This class is the engine shell:
 * component setup, arc tables, instance bookkeeping and the boarding broadcast.
 *
 * WHAT THIS IS NOT. It is not a traffic simulation. There are no junctions, no signals,
 * no right of way, no lane changes, no overtaking, no collision and no interaction
 * between routes or with the player. A vehicle follows the vehicle ahead of it on its
 * own route and does nothing else. Vehicles pass through anything not on their route.
 *
 * THE RAIL LINE IS AUTHORED FUTURE INTERPRETATION. The light-rail route, its stations
 * and its platforms are an illustrative proposal laid along an existing road corridor.
 * They are not surveyed infrastructure, not an approved alignment and not a real service.
 *
 * WIRING BOARDING TO THE CROWD. This class defines the hook and never touches the crowd:
 *   1. Blueprint subclass: override the RequestBoarding / RequestAlighting events.
 *   2. C++ or Blueprint binding without subclassing: bind to OnRequestBoarding /
 *      OnRequestAlighting, which carry the same payload.
 * Both fire for every doors-open and doors-close edge. The coordinator binds the crowd
 * field's own "converge on point and despawn" entry point to OnRequestBoarding and its
 * "spawn at point and disperse" entry point to OnRequestAlighting. AMikdashCrowdField is
 * not referenced, included or edited here.
 */
UCLASS(BlueprintType)
class MIKDASHRUNTIME_API AMikdashTransit : public AActor
{
    GENERATED_BODY()
public:
    AMikdashTransit();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

    /** Build the arc tables, create the HISM components and seed the traffic. Safe to
     * call again: it tears the previous run down first. Returns false and sets the status
     * string when the configuration is unusable. */
    UFUNCTION(BlueprintCallable, Category="Transit") bool InitializeTransit();
    UFUNCTION(BlueprintCallable, Category="Transit") void ShutdownTransit();
    UFUNCTION(BlueprintCallable, Category="Transit") void SetTransitPaused(bool bPaused);

    UFUNCTION(BlueprintPure, Category="Transit") bool IsTransitActive() const { return bActive; }
    UFUNCTION(BlueprintPure, Category="Transit") FString GetTransitStatus() const { return Status; }
    UFUNCTION(BlueprintPure, Category="Transit") int32 GetRoadVehicleCount() const { return Vehicles.Num(); }
    UFUNCTION(BlueprintPure, Category="Transit") int32 GetActiveTrainCount() const;
    /** Vehicles visited per frame, and how many frames a full sweep takes. */
    UFUNCTION(BlueprintPure, Category="Transit") int32 GetFramesPerSweep() const;

    // -- stop queries, for whatever binds to the boarding hook ------------------
    UFUNCTION(BlueprintPure, Category="Transit|Boarding") int32 GetStopCount() const { return StopIndex.Num(); }
    UFUNCTION(BlueprintPure, Category="Transit|Boarding") FVector GetStopLocation(int32 GlobalStopIndex) const;
    /** Where the crowd should converge: the kerb/platform face beside the stop line. */
    UFUNCTION(BlueprintPure, Category="Transit|Boarding") FVector GetStopFurniturePoint(int32 GlobalStopIndex) const;
    UFUNCTION(BlueprintPure, Category="Transit|Boarding") FName GetStopRouteId(int32 GlobalStopIndex) const;
    UFUNCTION(BlueprintPure, Category="Transit|Boarding") FString GetStopName(int32 GlobalStopIndex) const;
    /** How far the authored stop position sat from the route the runtime actually built.
     * A large value means the stop was authored off its route; it is reported, not hidden. */
    UFUNCTION(BlueprintPure, Category="Transit|Boarding") float GetStopProjectionErrorCm(int32 GlobalStopIndex) const;

    /** Doors have finished opening at a stop: N pedestrians should converge and vanish
     * into the vehicle. Override in a Blueprint subclass, or bind OnRequestBoarding. */
    UFUNCTION(BlueprintImplementableEvent, Category="Transit|Boarding")
    void RequestBoarding(int32 GlobalStopIndex, int32 Count, FVector BoardingPoint, float SecondsAvailable);
    /** Doors are about to shut: N pedestrians should appear from the vehicle and disperse. */
    UFUNCTION(BlueprintImplementableEvent, Category="Transit|Boarding")
    void RequestAlighting(int32 GlobalStopIndex, int32 Count, FVector BoardingPoint, float SecondsAvailable);

    UPROPERTY(BlueprintAssignable, Category="Transit|Boarding") FMikdashTransitBoardingSignature OnRequestBoarding;
    UPROPERTY(BlueprintAssignable, Category="Transit|Boarding") FMikdashTransitBoardingSignature OnRequestAlighting;

    /** How many of a boarding or alighting group should stop and photograph the place
     * instead of walking straight on. A HINT for whatever drives the crowd; this class
     * owns no pedestrian and implements no behaviour. Deterministic in the stop and the
     * run, so the same stop on the same run always answers the same number. Call it from
     * the boarding handler with the Count it was just given. */
    UFUNCTION(BlueprintPure, Category="Transit|Boarding")
    int32 SuggestPhotographerCount(int32 GlobalStopIndex, int32 Count, int32 RunIndex) const;

    // -- configuration ---------------------------------------------------------

    /** Set only on an explicitly adopted, fully configured actor. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit") bool bActivateOnBeginPlay = false;
    /** Authored routes, written by Scripts/release_transit.py from routes.json. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit") TArray<FMikdashTransitRoute> Routes;
    /** Car bodies, in the order the variant blocks are apportioned. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit") TArray<FMikdashTransitBody> CarBodies;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit") FMikdashTransitBody BusBody;
    /** Consist bodies, head first. The last car is posed with a 180 degree yaw. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit") TArray<FMikdashTransitBody> TrainBodies;
    /** Static furniture placed once at each stop: shelters on road routes, platforms on rail. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit") TArray<TObjectPtr<UStaticMesh>> ShelterMeshes;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit") TArray<TObjectPtr<UStaticMesh>> PlatformMeshes;

    /** Road vehicles across ALL routes, before the density multiplier. Apportioned by
     * each route's VehicleWeight. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Counts", meta=(ClampMin="0", ClampMax="2000"))
    int32 RoadVehicleCount = 220;
    /** Multiplies every count and every boarding request. Clamped to 8 by the math, and
     * again by MaxRoadVehicles, so a mis-typed value cannot allocate without bound. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Counts", meta=(ClampMin="0.0", ClampMax="8.0"))
    float DensityMultiplier = 1.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Counts", meta=(ClampMin="0", ClampMax="4000"))
    int32 MaxRoadVehicles = 900;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Counts", meta=(ClampMin="0", ClampMax="8"))
    int32 MaxActiveTrains = 3;

    /** Randomised service headway for the rail line, seconds. 2 to 5 minutes by default. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Rail", meta=(ClampMin="10.0"))
    float TrainHeadwayMinSeconds = 120.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Rail", meta=(ClampMin="10.0"))
    float TrainHeadwayMaxSeconds = 300.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Rail", meta=(ClampMin="0.0"))
    float TrainDwellMinSeconds = 20.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Rail", meta=(ClampMin="0.0"))
    float TrainDwellMaxSeconds = 40.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Rail") float TrainCarLengthCm = 1020.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Rail") float TrainCouplingGapCm = 40.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Rail") float TrainBogieInsetCm = 280.f;

    /** Bus dwell window, seconds. Rail stations use the Train values above. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Dwell") float BusDwellMinSeconds = 14.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Dwell") float BusDwellMaxSeconds = 28.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Dwell") float DoorOpenSeconds = 1.6f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Dwell") float DoorCloseSeconds = 1.8f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Dwell") float DoorTravelCm = 55.f;

    /** Vehicles advanced per frame. The rest keep the transform they had; every vehicle
     * is visited once per ceil(Count / Budget) frames and integrates the whole sweep. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Budget", meta=(ClampMin="1"))
    int32 UpdateBudget = 48;
    /** Beyond this distance from the view a vehicle is still simulated (it is scalar
     * arithmetic and keeps the traffic coherent) but its instance transform is NOT
     * rewritten, which is the part that costs. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Budget") float TransformFreezeDistanceCm = 45000.f;
    /** HISM per-instance cull distance handed to the renderer. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Budget") float InstanceCullStartCm = 60000.f;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Budget") float InstanceCullEndCm = 120000.f;

    /** Share of each boarding group SuggestPhotographerCount hands back. The stop is a
     * view of the Mount; people photograph it. Nothing here makes them do so. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit|Boarding", meta=(ClampMin="0.0", ClampMax="1.0"))
    float PhotographerShare = 0.22f;

    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit") int32 Seed = 20260908;
    /** Body colours the paint variation draws from, one per instance. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Transit") TArray<FLinearColor> PaintPalette;

private:
    // -- plain C++ runtime state: rebuilt at every start, never serialized -------
    //
    // The types themselves are declared ABOVE, at file scope, and only aliased here.
    // Unreal Header Tool parses the whole UCLASS body looking for reflected members; a
    // nested struct declaration inside it is one more thing for UHT to get wrong for no
    // benefit, and these types carry MikdashTransit::Vec3 and std::-backed doubles that
    // must never be reflected. Aliases keep the member declarations and the .cpp
    // unchanged while the definitions stay where UHT never has to look at them.

    using FRouteRuntime = FMikdashTransitRouteRuntime;
    using FVehicle = FMikdashTransitVehicle;
    using FTrain = FMikdashTransitTrain;
    using FBodyComponents = FMikdashTransitBodyComponents;

    UPROPERTY(Transient) TArray<TObjectPtr<UHierarchicalInstancedStaticMeshComponent>> OwnedComponents;

    TArray<FRouteRuntime> RouteRuntimes;
    TArray<FBodyComponents> BodyComponents;   // parallel to Bodies
    TArray<FMikdashTransitBody> Bodies;       // cars, then bus, then train cars
    TArray<FVehicle> Vehicles;
    TArray<FTrain> Trains;
    /** Flat (route, stop) addressing for the boarding hook. */
    TArray<FIntPoint> StopIndex;

    int32 RailRouteIndex = INDEX_NONE;
    int32 BusBodyIndex = INDEX_NONE;
    int32 FirstTrainBodyIndex = INDEX_NONE;
    int32 UpdateCursor = 0;
    int32 NextTrainId = 0;
    double WorldSeconds = 0.0;
    double NextTrainDepartureSeconds = 0.0;
    bool bActive = false;
    bool bPaused = false;
    FString Status = TEXT("inactive");

    UHierarchicalInstancedStaticMeshComponent* MakeInstancedComponent(UStaticMesh* Mesh, const FName& Name, int32 CustomDataFloats);
    bool BuildRouteRuntimes();
    bool BuildBodies();
    void SeedRoadVehicles();
    void PlaceStopFurniture();
    void AdvanceVehicle(FVehicle& Vehicle, int32 VehicleId, double Dt, const FVector& ViewLocation);
    void AdvanceTrains(double Dt, const FVector& ViewLocation);
    void WriteVehicleTransform(const FVehicle& Vehicle, const FVector& Location, const FRotator& Rotation);
    void ApplyPaintColour(int32 BodyIdx, int32 InstanceId, int32 VariationIndex);
    void BroadcastBoarding(int32 RouteIdx, int32 LocalStopIdx, int32 VehicleId, int32 RunIndex,
                           const FVector& DoorPoint, float SecondsAvailable, bool bAlighting);
    void MarkTouchedComponentsDirty();
    FVector CurrentViewLocation() const;

    TSet<UHierarchicalInstancedStaticMeshComponent*> TouchedThisFrame;
};
