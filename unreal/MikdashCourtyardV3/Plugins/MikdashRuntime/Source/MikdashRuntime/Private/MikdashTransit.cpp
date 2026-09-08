#include "MikdashTransit.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

using namespace MikdashTransit;

namespace
{
/** Vec3 <-> FVector, kept in one place so the double-precision boundary is obvious. */
FORCEINLINE Vec3 ToVec(const FVector& V) { return Vec3{V.X, V.Y, V.Z}; }
FORCEINLINE FVector ToVector(const Vec3& V) { return FVector(V.X, V.Y, V.Z); }

/** Longitudinal parameters for a road vehicle on a route with the given speed limit.
 * Cars run a little over the posted figure and buses a little under, which is what makes
 * a mixed stream look like traffic instead of a convoy. */
FollowParams MakeFollowParams(double SpeedLimit, bool bBus, bool bRail, uint32 Seed, int32 Index)
{
    FollowParams P;
    const double Spread = HashRange(Seed, static_cast<uint32>(Index), 17u, 0.88, 1.08);
    P.DesiredSpeedCmPerSecond = FMath::Max(120.0, SpeedLimit * (bBus ? Spread * 0.86 : Spread));
    P.MinGapCm = bRail ? 3000.0 : (bBus ? 620.0 : 430.0);
    P.TimeHeadwaySeconds = bRail ? 6.0 : (bBus ? 1.7 : HashRange(Seed, static_cast<uint32>(Index), 19u, 1.05, 1.75));
    P.MaxAccelerationCmPerSecond2 = bRail ? 110.0 : (bBus ? 95.0 : 145.0);
    P.ComfortDecelerationCmPerSecond2 = bRail ? 110.0 : (bBus ? 160.0 : 210.0);
    P.EmergencyDecelerationCmPerSecond2 = bRail ? 260.0 : 620.0;
    return P;
}
}  // namespace

AMikdashTransit::AMikdashTransit()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = true;
    RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("TransitRoot"));
    RootComponent->SetMobility(EComponentMobility::Static);
    // A plausible default so an unconfigured actor still reads as traffic rather than a
    // row of identical grey cars.
    PaintPalette = {
        FLinearColor(0.82f, 0.83f, 0.84f), FLinearColor(0.05f, 0.06f, 0.07f),
        FLinearColor(0.28f, 0.30f, 0.33f), FLinearColor(0.62f, 0.63f, 0.64f),
        FLinearColor(0.33f, 0.03f, 0.03f), FLinearColor(0.03f, 0.10f, 0.24f),
        FLinearColor(0.06f, 0.16f, 0.11f), FLinearColor(0.55f, 0.42f, 0.10f),
    };
}

void AMikdashTransit::BeginPlay()
{
    Super::BeginPlay();
    if (bActivateOnBeginPlay)
    {
        InitializeTransit();
    }
}

void AMikdashTransit::EndPlay(const EEndPlayReason::Type Reason)
{
    ShutdownTransit();
    Super::EndPlay(Reason);
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

UHierarchicalInstancedStaticMeshComponent* AMikdashTransit::MakeInstancedComponent(UStaticMesh* Mesh, const FName& Name, int32 CustomDataFloats)
{
    if (!Mesh)
    {
        return nullptr;
    }
    UHierarchicalInstancedStaticMeshComponent* Component =
        NewObject<UHierarchicalInstancedStaticMeshComponent>(this, Name);
    Component->SetupAttachment(RootComponent);
    Component->SetStaticMesh(Mesh);
    // Movable: the instances are rewritten every sweep. Static mobility would be a lie
    // and would also silently drop the transform updates.
    Component->SetMobility(EComponentMobility::Movable);
    Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Component->SetCanEverAffectNavigation(false);
    Component->bCastDynamicShadow = true;
    Component->NumCustomDataFloats = FMath::Max(0, CustomDataFloats);
    Component->InstanceStartCullDistance = static_cast<int32>(FMath::Max(0.f, InstanceCullStartCm));
    Component->InstanceEndCullDistance = static_cast<int32>(FMath::Max(0.f, InstanceCullEndCm));
    Component->RegisterComponent();
    OwnedComponents.Add(Component);
    return Component;
}

bool AMikdashTransit::BuildRouteRuntimes()
{
    RouteRuntimes.Reset();
    StopIndex.Reset();
    RailRouteIndex = INDEX_NONE;
    double WorstStopError = 0.0;
    for (int32 R = 0; R < Routes.Num(); ++R)
    {
        const FMikdashTransitRoute& Route = Routes[R];
        FRouteRuntime Runtime;
        TArray<Vec3> Control;
        Control.Reserve(Route.Points.Num());
        for (const FVector& Point : Route.Points)
        {
            Control.Add(ToVec(Point));
        }
        const int32 Count = DensifiedPointCount(Control.Num(), true, Route.SmoothingPerSegment);
        if (Count < 2)
        {
            Status = FString::Printf(TEXT("route %s has too few points (%d)"), *Route.Id.ToString(), Route.Points.Num());
            return false;
        }
        Runtime.Points.SetNumZeroed(Count);
        Runtime.Cumulative.SetNumZeroed(Count);
        Runtime.LengthCm = BuildArcTable(Control.GetData(), Control.Num(), true, Route.SmoothingPerSegment,
                                         Runtime.Points.GetData(), Runtime.Cumulative.GetData());
        if (!(Runtime.LengthCm > 100.0))
        {
            Status = FString::Printf(TEXT("route %s has no length"), *Route.Id.ToString());
            return false;
        }
        // Authored stops are world positions; bind each to the arc table just built, and
        // keep the residual so a stop authored off its route is visible, not silent.
        for (int32 S = 0; S < Route.Stops.Num(); ++S)
        {
            double Where = 0.0, Error = 0.0;
            if (!ProjectOntoRoute(Runtime.Points.GetData(), Runtime.Cumulative.GetData(), Count,
                                  ToVec(Route.Stops[S].WorldPosition), Where, Error))
            {
                Status = FString::Printf(TEXT("stop %d of route %s could not be projected"), S, *Route.Id.ToString());
                return false;
            }
            Runtime.StopDistances.Add(Where);
            Runtime.StopErrorCm.Add(Error);
            Runtime.GlobalStopIndices.Add(StopIndex.Num());
            StopIndex.Add(FIntPoint(R, S));
            WorstStopError = FMath::Max(WorstStopError, Error);
        }
        if (Route.bRail && RailRouteIndex == INDEX_NONE)
        {
            RailRouteIndex = R;
        }
        RouteRuntimes.Add(MoveTemp(Runtime));
    }
    if (RouteRuntimes.Num() == 0)
    {
        Status = TEXT("no routes authored");
        return false;
    }
    Status = FString::Printf(TEXT("%d routes, %d stops, worst stop projection %.1f cm"),
                             RouteRuntimes.Num(), StopIndex.Num(), WorstStopError);
    return true;
}

bool AMikdashTransit::BuildBodies()
{
    Bodies.Reset();
    BodyComponents.Reset();
    BusBodyIndex = INDEX_NONE;
    FirstTrainBodyIndex = INDEX_NONE;

    for (const FMikdashTransitBody& Body : CarBodies)
    {
        Bodies.Add(Body);
    }
    if (BusBody.Paint)
    {
        BusBodyIndex = Bodies.Num();
        Bodies.Add(BusBody);
    }
    if (TrainBodies.Num() > 0)
    {
        FirstTrainBodyIndex = Bodies.Num();
        for (const FMikdashTransitBody& Body : TrainBodies)
        {
            Bodies.Add(Body);
        }
    }
    if (Bodies.Num() == 0)
    {
        Status = TEXT("no vehicle bodies configured");
        return false;
    }

    for (int32 B = 0; B < Bodies.Num(); ++B)
    {
        const FMikdashTransitBody& Body = Bodies[B];
        FBodyComponents Components;
        Components.LengthCm = FMath::Max(100.f, Body.LengthCm);
        Components.DoorLocalOffsets = Body.DoorLocalOffsets;
        UStaticMesh* const Meshes[4] = {Body.Paint, Body.Glass, Body.Dark, Body.Lens};
        static const TCHAR* const GroupNames[4] = {TEXT("Paint"), TEXT("Glass"), TEXT("Dark"), TEXT("Lens")};
        for (int32 Group = 0; Group < 4; ++Group)
        {
            // Only the Paint group needs per-instance custom data; the others carry none.
            Components.Groups[Group] = MakeInstancedComponent(
                Meshes[Group], FName(*FString::Printf(TEXT("HISM_%s_%s"), *Body.Key.ToString(), GroupNames[Group])),
                Group == 0 ? 3 : 0);
        }
        if (!Components.Groups[0])
        {
            Status = FString::Printf(TEXT("body %s has no Paint mesh"), *Body.Key.ToString());
            return false;
        }
        Components.DoorPaint = MakeInstancedComponent(
            Body.DoorLeafPaint, FName(*FString::Printf(TEXT("HISM_%s_DoorPaint"), *Body.Key.ToString())), 3);
        Components.DoorGlass = MakeInstancedComponent(
            Body.DoorLeafGlass, FName(*FString::Printf(TEXT("HISM_%s_DoorGlass"), *Body.Key.ToString())), 0);
        BodyComponents.Add(Components);
    }
    return true;
}

void AMikdashTransit::SeedRoadVehicles()
{
    Vehicles.Reset();
    const int32 Wanted = ScaledVehicleCount(RoadVehicleCount, DensityMultiplier, MaxRoadVehicles);
    if (Wanted <= 0 || CarBodies.Num() == 0)
    {
        return;
    }
    // Apportion by route weight, skipping the rail line: it is served by consists.
    TArray<double> Weights;
    Weights.SetNumZeroed(Routes.Num());
    for (int32 R = 0; R < Routes.Num(); ++R)
    {
        Weights[R] = Routes[R].bRail ? 0.0 : FMath::Max(0.f, Routes[R].VehicleWeight);
    }
    TArray<int32> Counts;
    Counts.SetNumZeroed(Routes.Num());
    ApportionVehicles(Weights.GetData(), Routes.Num(), Wanted, Counts.GetData());

    const uint32 SeedValue = static_cast<uint32>(Seed);
    for (int32 R = 0; R < Routes.Num(); ++R)
    {
        const int32 OnRoute = Counts[R];
        if (OnRoute <= 0)
        {
            continue;
        }
        const FMikdashTransitRoute& Route = Routes[R];
        FRouteRuntime& Runtime = RouteRuntimes[R];
        const int32 FirstOnRoute = Vehicles.Num();
        const int32 Buses = (BusBodyIndex != INDEX_NONE)
            ? FMath::Clamp(FMath::RoundToInt(OnRoute * FMath::Clamp(Route.BusShare, 0.f, 1.f)), 0, OnRoute) : 0;
        for (int32 I = 0; I < OnRoute; ++I)
        {
            FVehicle Vehicle;
            Vehicle.RouteIndex = R;
            // Buses are the first block on the route so the variant blocking stays
            // contiguous, which is what keeps instance ranges contiguous per component.
            const bool bBus = I < Buses;
            Vehicle.BodyIndex = bBus ? BusBodyIndex
                : VariantIndexForInstance(I - Buses, FMath::Max(1, OnRoute - Buses), CarBodies.Num());
            Vehicle.bServesStops = bBus || Bodies[Vehicle.BodyIndex].bServesStops;
            Vehicle.DistanceCm = SpawnDistanceFor(I, OnRoute, Runtime.LengthCm,
                                                  FMath::Min(900.0, Runtime.LengthCm / (4.0 * OnRoute)),
                                                  SeedValue ^ static_cast<uint32>(R * 977));
            Vehicle.Follow = MakeFollowParams(Route.SpeedLimitCmPerSecond, bBus, false, SeedValue, Vehicles.Num());
            Vehicle.SpeedCmPerSecond = Vehicle.Follow.DesiredSpeedCmPerSecond * 0.6;
            Vehicle.Dwell.MinDwellSeconds = BusDwellMinSeconds;
            Vehicle.Dwell.MaxDwellSeconds = BusDwellMaxSeconds;
            Vehicle.Dwell.DoorOpenSeconds = DoorOpenSeconds;
            Vehicle.Dwell.DoorCloseSeconds = DoorCloseSeconds;
            Vehicle.Dwell.DoorTravelCm = DoorTravelCm;
            Vehicle.Stop.TargetStopIndex = INDEX_NONE;
            Vehicles.Add(Vehicle);
        }
        // SpawnDistanceFor is monotone in the index up to its jitter, so sorting here
        // once establishes the ring order. Vehicles cannot overtake, so that order --
        // and therefore every vehicle's leader -- is fixed for the life of the run.
        TArray<int32> Order;
        for (int32 V = FirstOnRoute; V < Vehicles.Num(); ++V)
        {
            Order.Add(V);
        }
        Order.Sort([this](const int32& A, const int32& B) { return Vehicles[A].DistanceCm < Vehicles[B].DistanceCm; });
        for (int32 K = 0; K < Order.Num(); ++K)
        {
            Vehicles[Order[K]].LeaderVehicle = Order[(K + 1) % Order.Num()];
        }
        Runtime.VehicleIndices = Order;
    }

    // Create the instances, one block per body so per-component ranges stay contiguous.
    for (int32 V = 0; V < Vehicles.Num(); ++V)
    {
        FVehicle& Vehicle = Vehicles[V];
        FBodyComponents& Components = BodyComponents[Vehicle.BodyIndex];
        Vehicle.Follow.MinGapCm = FMath::Max(Vehicle.Follow.MinGapCm, Components.LengthCm * 1.15);
        const FTransform Identity = FTransform(FRotator::ZeroRotator, GetActorLocation(), FVector::OneVector);
        for (int32 Group = 0; Group < 4; ++Group)
        {
            if (Components.Groups[Group])
            {
                Vehicle.InstanceIds[Group] = Components.Groups[Group]->AddInstance(Identity, /*bWorldSpace*/ true);
            }
        }
        ApplyPaintColour(Vehicle.BodyIndex, Vehicle.InstanceIds[0], V);
        if (Components.DoorPaint && Components.DoorLocalOffsets.Num() > 0)
        {
            Vehicle.DoorInstanceStart = INDEX_NONE;
            for (int32 D = 0; D < Components.DoorLocalOffsets.Num(); ++D)
            {
                const int32 Added = Components.DoorPaint->AddInstance(Identity, true);
                if (Vehicle.DoorInstanceStart == INDEX_NONE)
                {
                    Vehicle.DoorInstanceStart = Added;
                }
                if (Components.DoorGlass)
                {
                    Components.DoorGlass->AddInstance(Identity, true);
                }
                ++Vehicle.DoorInstanceCount;
            }
        }
    }
}

void AMikdashTransit::ApplyPaintColour(int32 BodyIdx, int32 InstanceId, int32 VariationIndex)
{
    if (InstanceId == INDEX_NONE || !BodyComponents.IsValidIndex(BodyIdx) || PaintPalette.Num() == 0)
    {
        return;
    }
    TArray<double> Flat;
    Flat.Reserve(PaintPalette.Num() * 3);
    for (const FLinearColor& Colour : PaintPalette)
    {
        Flat.Add(Colour.R);
        Flat.Add(Colour.G);
        Flat.Add(Colour.B);
    }
    double Rgb[3] = {0.5, 0.5, 0.5};
    PaintColourFor(static_cast<uint32>(Seed), VariationIndex, Flat.GetData(), PaintPalette.Num(), Rgb);
    UHierarchicalInstancedStaticMeshComponent* Component = BodyComponents[BodyIdx].Groups[0];
    if (!Component)
    {
        return;
    }
    for (int32 I = 0; I < 3; ++I)
    {
        Component->SetCustomDataValue(InstanceId, I, static_cast<float>(Rgb[I]), /*bMarkRenderStateDirty*/ false);
    }
    Component->MarkRenderStateDirty();
}

void AMikdashTransit::PlaceStopFurniture()
{
    // Furniture never moves, so it is added once and never touched again: one instance
    // per mesh per stop, on a component that is not in the per-frame update at all.
    for (int32 R = 0; R < Routes.Num(); ++R)
    {
        const FMikdashTransitRoute& Route = Routes[R];
        const FRouteRuntime& Runtime = RouteRuntimes[R];
        const TArray<TObjectPtr<UStaticMesh>>& Meshes = Route.bRail ? PlatformMeshes : ShelterMeshes;
        if (Meshes.Num() == 0)
        {
            continue;
        }
        TArray<UHierarchicalInstancedStaticMeshComponent*> Components;
        for (int32 M = 0; M < Meshes.Num(); ++M)
        {
            Components.Add(MakeInstancedComponent(
                Meshes[M].Get(),
                FName(*FString::Printf(TEXT("HISM_Furniture_%s_%d"), *Route.Id.ToString(), M)), 0));
        }
        for (int32 S = 0; S < Route.Stops.Num() && S < Runtime.StopDistances.Num(); ++S)
        {
            Vec3 Position{}, Tangent{};
            if (!SampleRoute(Runtime.Points.GetData(), Runtime.Cumulative.GetData(), Runtime.Points.Num(), true,
                             Runtime.StopDistances[S], Position, Tangent))
            {
                continue;
            }
            const double Yaw = YawDegrees(Tangent);
            // Furniture stands beyond the running lane, facing the road, so its local +Y
            // (toward the road) points back at the centreline: hence the 180 degree turn.
            const Vec3 Placed = ApplyLaneOffset(Position, Tangent, Route.Stops[S].FurnitureOffsetCm, 0.0);
            const FTransform Transform(FRotator(0.0, Yaw + 180.0, 0.0), ToVector(Placed), FVector::OneVector);
            for (UHierarchicalInstancedStaticMeshComponent* Component : Components)
            {
                if (Component)
                {
                    Component->AddInstance(Transform, /*bWorldSpace*/ true);
                }
            }
        }
    }
}

bool AMikdashTransit::InitializeTransit()
{
    ++ExchangeGeneration;
    ShutdownTransit();
    if (!BuildRouteRuntimes())
    {
        return false;
    }
    if (!BuildBodies())
    {
        return false;
    }
    SeedRoadVehicles();
    PlaceStopFurniture();

    Trains.Reset();
    if (RailRouteIndex != INDEX_NONE && FirstTrainBodyIndex != INDEX_NONE)
    {
        Trains.SetNum(FMath::Clamp(MaxActiveTrains, 0, 8));
        const int32 CarCount = TrainBodies.Num();
        // Slot ids first: MakeFollowParams draws its speed spread from the id, so
        // assigning them afterwards would give every consist identical parameters.
        for (int32 T = 0; T < Trains.Num(); ++T)
        {
            Trains[T].Id = T;
        }
        for (FTrain& Train : Trains)
        {
            Train.bActive = false;
            Train.Follow = MakeFollowParams(Routes[RailRouteIndex].SpeedLimitCmPerSecond, false, true,
                                            static_cast<uint32>(Seed), Train.Id);
            Train.Dwell.MinDwellSeconds = TrainDwellMinSeconds;
            Train.Dwell.MaxDwellSeconds = TrainDwellMaxSeconds;
            Train.Dwell.DoorOpenSeconds = DoorOpenSeconds;
            Train.Dwell.DoorCloseSeconds = DoorCloseSeconds;
            Train.Dwell.DoorTravelCm = DoorTravelCm;
            // Rail vehicles are long and heavy: they need a much wider arrival window
            // than a car, and a much gentler brake.
            Train.Dwell.ArrivalToleranceCm = 260.0;
            Train.Dwell.BrakingMarginCm = 2500.0;
            const FTransform Identity(FRotator::ZeroRotator, GetActorLocation(), FVector::OneVector);
            for (int32 C = 0; C < CarCount; ++C)
            {
                FBodyComponents& Components = BodyComponents[FirstTrainBodyIndex + C];
                for (int32 Group = 0; Group < 4; ++Group)
                {
                    Train.CarInstanceIds.Add(Components.Groups[Group]
                                                 ? Components.Groups[Group]->AddInstance(Identity, true) : INDEX_NONE);
                }
                if (Components.DoorPaint)
                {
                    for (int32 D = 0; D < Components.DoorLocalOffsets.Num(); ++D)
                    {
                        Train.DoorInstanceIds.Add(Components.DoorPaint->AddInstance(Identity, true));
                        if (Components.DoorGlass)
                        {
                            Components.DoorGlass->AddInstance(Identity, true);
                        }
                    }
                }
            }
        }
        NextTrainDepartureSeconds = 5.0;
    }

    WorldSeconds = 0.0;
    UpdateCursor = 0;
    NextTrainId = 0;
    bActive = true;
    bPaused = false;
    Status = FString::Printf(TEXT("active: %d road vehicles on %d routes, %d stops, %d train slots, %d frames per sweep"),
                             Vehicles.Num(), RouteRuntimes.Num(), StopIndex.Num(), Trains.Num(), GetFramesPerSweep());
    return true;
}

void AMikdashTransit::ShutdownTransit()
{
    for (TObjectPtr<UHierarchicalInstancedStaticMeshComponent>& Component : OwnedComponents)
    {
        if (Component)
        {
            Component->ClearInstances();
            Component->DestroyComponent();
        }
    }
    OwnedComponents.Reset();
    BodyComponents.Reset();
    Bodies.Reset();
    Vehicles.Reset();
    Trains.Reset();
    RouteRuntimes.Reset();
    StopIndex.Reset();
    TouchedThisFrame.Reset();
    bActive = false;
    Status = TEXT("inactive");
}

void AMikdashTransit::SetTransitPaused(bool bInPaused)
{
    bPaused = bInPaused;
}

// ---------------------------------------------------------------------------
// Tick
// ---------------------------------------------------------------------------

int32 AMikdashTransit::GetFramesPerSweep() const
{
    return MikdashTransit::FramesPerSweep(Vehicles.Num(), FMath::Max(1, UpdateBudget));
}

int32 AMikdashTransit::GetActiveTrainCount() const
{
    int32 Count = 0;
    for (const FTrain& Train : Trains)
    {
        Count += Train.bActive ? 1 : 0;
    }
    return Count;
}

FVector AMikdashTransit::CurrentViewLocation() const
{
    if (const UWorld* World = GetWorld())
    {
        if (const APlayerController* Controller = World->GetFirstPlayerController())
        {
            FVector Location = FVector::ZeroVector;
            FRotator Rotation = FRotator::ZeroRotator;
            Controller->GetPlayerViewPoint(Location, Rotation);
            return Location;
        }
    }
    return GetActorLocation();
}

void AMikdashTransit::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bActive || bPaused || !(DeltaSeconds > 0.f))
    {
        return;
    }
    WorldSeconds += DeltaSeconds;
    const FVector ViewLocation = CurrentViewLocation();
    TouchedThisFrame.Reset();

    // Bounded work: a fixed slice of the vehicle array per frame, each vehicle
    // integrating the whole sweep it slept through.
    const int32 Budget = FMath::Max(1, UpdateBudget);
    const double Dt = CatchUpSeconds(DeltaSeconds, Vehicles.Num(), Budget);
    const UpdateWindow Window = NextUpdateWindow(UpdateCursor, Vehicles.Num(), Budget);
    for (int32 K = 0; K < Window.Total(); ++K)
    {
        const int32 Index = K < Window.FirstCount ? Window.FirstStart + K
                                                  : Window.SecondStart + (K - Window.FirstCount);
        if (Vehicles.IsValidIndex(Index))
        {
            AdvanceVehicle(Vehicles[Index], Index, Dt, ViewLocation);
        }
    }
    UpdateCursor = Window.NextCursor;

    // Trains are few and long; they are advanced every frame at the real delta, because
    // a 30 m consist stepped at a sweep rate would visibly jump.
    AdvanceTrains(FMath::Min<double>(DeltaSeconds, 0.25), ViewLocation);
    MarkTouchedComponentsDirty();
}

void AMikdashTransit::MarkTouchedComponentsDirty()
{
    // One render-state flush per component per frame, not one per instance write.
    for (UHierarchicalInstancedStaticMeshComponent* Component : TouchedThisFrame)
    {
        if (Component)
        {
            Component->MarkRenderStateDirty();
        }
    }
    TouchedThisFrame.Reset();
}

void AMikdashTransit::WriteVehicleTransform(const FVehicle& Vehicle, const FVector& Location, const FRotator& Rotation)
{
    FBodyComponents& Components = BodyComponents[Vehicle.BodyIndex];
    const FTransform Transform(Rotation, Location, FVector::OneVector);
    for (int32 Group = 0; Group < 4; ++Group)
    {
        UHierarchicalInstancedStaticMeshComponent* Component = Components.Groups[Group];
        if (Component && Vehicle.InstanceIds[Group] != INDEX_NONE)
        {
            Component->UpdateInstanceTransform(Vehicle.InstanceIds[Group], Transform, /*bWorldSpace*/ true,
                                               /*bMarkRenderStateDirty*/ false, /*bTeleport*/ true);
            TouchedThisFrame.Add(Component);
        }
    }
    // Door leaves slide backwards along the body's own -X by the smoothstepped offset.
    if (Components.DoorPaint && Vehicle.DoorInstanceCount > 0 && Vehicle.DoorInstanceStart != INDEX_NONE)
    {
        const double Offset = DoorOffsetCm(Vehicle.Stop.DoorFraction, Vehicle.Dwell.DoorTravelCm);
        for (int32 D = 0; D < Vehicle.DoorInstanceCount && D < Components.DoorLocalOffsets.Num(); ++D)
        {
            const FVector Local = Components.DoorLocalOffsets[D] - FVector(Offset, 0.0, 0.0);
            const FTransform Leaf(Rotation, Location + Rotation.RotateVector(Local), FVector::OneVector);
            const int32 Id = Vehicle.DoorInstanceStart + D;
            Components.DoorPaint->UpdateInstanceTransform(Id, Leaf, true, false, true);
            TouchedThisFrame.Add(Components.DoorPaint);
            if (Components.DoorGlass)
            {
                Components.DoorGlass->UpdateInstanceTransform(Id, Leaf, true, false, true);
                TouchedThisFrame.Add(Components.DoorGlass);
            }
        }
    }
}

void AMikdashTransit::AdvanceVehicle(FVehicle& Vehicle, int32 VehicleId, double Dt, const FVector& ViewLocation)
{
    FRouteRuntime& Runtime = RouteRuntimes[Vehicle.RouteIndex];
    const FMikdashTransitRoute& Route = Routes[Vehicle.RouteIndex];
    const int32 Count = Runtime.Points.Num();
    const double Total = Runtime.LengthCm;

    // Gap to the vehicle ahead. The leader is fixed at seeding because no vehicle can
    // ever overtake another on its own route.
    double GapCm = 1e9, LeadSpeed = 0.0;
    if (Vehicles.IsValidIndex(Vehicle.LeaderVehicle) && Vehicle.LeaderVehicle != VehicleId)
    {
        const FVehicle& Leader = Vehicles[Vehicle.LeaderVehicle];
        GapCm = ForwardGap(Vehicle.DistanceCm, Leader.DistanceCm, Total, true)
            - BodyComponents[Leader.BodyIndex].LengthCm;
        LeadSpeed = Leader.SpeedCmPerSecond;
    }

    // Acquire a stop only while Running, then LATCH it: re-querying while braking would
    // hand back the next stop as the gap shrank past the skip window, and the bus would
    // sail through the stop it was braking for. See NextStopAhead in TransitMath.h.
    double DistanceToStop = 1e9;
    if (Vehicle.bServesStops && Runtime.StopDistances.Num() > 0)
    {
        if (Vehicle.Stop.Phase == StopPhase::Running)
        {
            double Nearest = 0.0;
            Vehicle.Stop.TargetStopIndex = NextStopAhead(Runtime.StopDistances.GetData(), Runtime.StopDistances.Num(),
                                                         Vehicle.DistanceCm, Total, true,
                                                         BodyComponents[Vehicle.BodyIndex].LengthCm * 2.0, Nearest);
        }
        if (Runtime.StopDistances.IsValidIndex(Vehicle.Stop.TargetStopIndex))
        {
            DistanceToStop = SignedDistanceAlong(Vehicle.DistanceCm,
                                                 Runtime.StopDistances[Vehicle.Stop.TargetStopIndex], Total, true);
        }
    }

    const double Acceleration = LongitudinalAcceleration(Vehicle.Stop, Vehicle.SpeedCmPerSecond, LeadSpeed,
                                                         GapCm, DistanceToStop, Vehicle.Follow);
    Vehicle.SpeedCmPerSecond = IntegrateSpeed(Vehicle.SpeedCmPerSecond, Acceleration, Dt,
                                              Vehicle.Follow.DesiredSpeedCmPerSecond);
    if (!IsHeldAtStop(Vehicle.Stop))
    {
        Vehicle.DistanceCm = WrapDistance(Vehicle.DistanceCm + Vehicle.SpeedCmPerSecond * Dt, Total, true);
    }

    Vec3 Position{}, Tangent{};
    if (!SampleRoute(Runtime.Points.GetData(), Runtime.Cumulative.GetData(), Count, true,
                     Vehicle.DistanceCm, Position, Tangent))
    {
        return;
    }
    const double Yaw = YawDegrees(Tangent);
    const Vec3 Placed = ApplyLaneOffset(Position, Tangent, Route.LaneOffsetCm, Route.RideHeightCm);
    const FVector Location = ToVector(Placed);

    if (Vehicle.bServesStops)
    {
        const StopEvents Events = AdvanceStopState(Vehicle.Stop, Dt, Vehicle.SpeedCmPerSecond, DistanceToStop,
                                                   Vehicle.Follow, Vehicle.Dwell, static_cast<uint32>(Seed), VehicleId);
        if (Events.bDoorsOpened && Runtime.StopDistances.IsValidIndex(Vehicle.Stop.ServedStopIndex))
        {
            if (BodyComponents.IsValidIndex(Vehicle.BodyIndex) && !BodyComponents[Vehicle.BodyIndex].DoorLocalOffsets.IsEmpty())
            {
                // Ground-level doorway threshold from the actual body transform, not a fraction of shelter offset.
                FVector LocalDoor = BodyComponents[Vehicle.BodyIndex].DoorLocalOffsets[0]; LocalDoor.Z = 0;
                const FVector Door = FTransform(FRotator(0,Yaw,0),Location).TransformPosition(LocalDoor);
                BroadcastBoarding(Vehicle.RouteIndex, Vehicle.Stop.ServedStopIndex, VehicleId, Vehicle.Stop.RunIndex,
                                  Door, static_cast<float>(Vehicle.Stop.DwellSeconds));
            }
        }
    }

    // Far vehicles are still integrated -- it is scalar arithmetic and keeps the stream
    // coherent -- but their instance transform is not rewritten, which is the part that
    // costs. A frozen vehicle simply keeps the transform it had.
    if (FVector::DistSquared2D(Location, ViewLocation) <=
        static_cast<double>(TransformFreezeDistanceCm) * TransformFreezeDistanceCm)
    {
        WriteVehicleTransform(Vehicle, Location, FRotator(0.0, Yaw, 0.0));
    }
}

void AMikdashTransit::AdvanceTrains(double Dt, const FVector& ViewLocation)
{
    if (RailRouteIndex == INDEX_NONE || Trains.Num() == 0 || FirstTrainBodyIndex == INDEX_NONE)
    {
        return;
    }
    FRouteRuntime& Runtime = RouteRuntimes[RailRouteIndex];
    const FMikdashTransitRoute& Route = Routes[RailRouteIndex];
    const int32 Count = Runtime.Points.Num();
    const double Total = Runtime.LengthCm;
    const int32 CarCount = TrainBodies.Num();
    const double ConsistLengthCm = CarCount * (TrainCarLengthCm + TrainCouplingGapCm);

    // Dispatch: when the scheduled departure arrives and the line head is clear, put a
    // free consist into service and draw the next headway.
    if (WorldSeconds >= NextTrainDepartureSeconds)
    {
        bool bHeadClear = true;
        for (const FTrain& Train : Trains)
        {
            if (Train.bActive && Train.TravelledCm < ConsistLengthCm * 1.6)
            {
                bHeadClear = false;
            }
        }
        if (bHeadClear)
        {
            for (FTrain& Train : Trains)
            {
                if (!Train.bActive)
                {
                    Train.bActive = true;
                    Train.DistanceCm = 0.0;
                    Train.TravelledCm = 0.0;
                    Train.SpeedCmPerSecond = 0.0;
                    Train.Stop = StopState();
                    Train.Id = NextTrainId++;
                    NextTrainDepartureSeconds = WorldSeconds
                        + HeadwayForRun(static_cast<uint32>(Seed), static_cast<uint32>(Train.Id),
                                        TrainHeadwayMinSeconds, TrainHeadwayMaxSeconds);
                    break;
                }
            }
        }
    }

    for (FTrain& Train : Trains)
    {
        if (!Train.bActive)
        {
            continue;
        }
        double DistanceToStop = 1e9;
        if (Runtime.StopDistances.Num() > 0)
        {
            if (Train.Stop.Phase == StopPhase::Running)
            {
                double Nearest = 0.0;
                Train.Stop.TargetStopIndex = NextStopAhead(Runtime.StopDistances.GetData(), Runtime.StopDistances.Num(),
                                                           Train.DistanceCm, Total, true, ConsistLengthCm, Nearest);
            }
            if (Runtime.StopDistances.IsValidIndex(Train.Stop.TargetStopIndex))
            {
                DistanceToStop = SignedDistanceAlong(Train.DistanceCm,
                                                     Runtime.StopDistances[Train.Stop.TargetStopIndex], Total, true);
            }
        }
        const double Acceleration = LongitudinalAcceleration(Train.Stop, Train.SpeedCmPerSecond, 0.0, 1e9,
                                                             DistanceToStop, Train.Follow);
        Train.SpeedCmPerSecond = IntegrateSpeed(Train.SpeedCmPerSecond, Acceleration, Dt,
                                                Train.Follow.DesiredSpeedCmPerSecond);
        if (!IsHeldAtStop(Train.Stop))
        {
            const double Step = Train.SpeedCmPerSecond * Dt;
            Train.DistanceCm = WrapDistance(Train.DistanceCm + Step, Total, true);
            Train.TravelledCm += Step;
        }

        const StopEvents Events = AdvanceStopState(Train.Stop, Dt, Train.SpeedCmPerSecond, DistanceToStop,
                                                   Train.Follow, Train.Dwell, static_cast<uint32>(Seed),
                                                   1000 + Train.Id);
        if (Events.bDoorsOpened && Runtime.StopDistances.IsValidIndex(Train.Stop.ServedStopIndex))
        {
            Vec3 CarPosition{}; double DoorYaw=0, DoorPitch=0;
            if (BodyComponents.IsValidIndex(FirstTrainBodyIndex) && !BodyComponents[FirstTrainBodyIndex].DoorLocalOffsets.IsEmpty()
                && SampleCarPose(Runtime.Points.GetData(),Runtime.Cumulative.GetData(),Count,true,
                                 Train.DistanceCm,0,TrainCarLengthCm,TrainCouplingGapCm,TrainBogieInsetCm,
                                 Route.LaneOffsetCm,Route.RideHeightCm,CarPosition,DoorYaw,DoorPitch))
            {
                const FTransform CarTransform(FRotator(DoorPitch,DoorYaw,0),ToVector(CarPosition));
                const int32 GlobalStop=Runtime.GlobalStopIndices[Train.Stop.ServedStopIndex];
                const FVector Furniture=GetStopFurniturePoint(GlobalStop);
                FVector Door=FVector::ZeroVector; double Best=TNumericLimits<double>::Max();
                for (FVector Local : BodyComponents[FirstTrainBodyIndex].DoorLocalOffsets)
                {
                    Local.Z=0; const FVector Candidate=CarTransform.TransformPosition(Local);
                    const double Distance=FVector::DistSquared2D(Candidate,Furniture);
                    if (Distance<Best) { Best=Distance; Door=Candidate; }
                }
                BroadcastBoarding(RailRouteIndex,Train.Stop.ServedStopIndex,1000+Train.Id,Train.Stop.RunIndex,
                                  Door,static_cast<float>(Train.Stop.DwellSeconds));
            }
        }

        // One lap and the consist leaves service, freeing the slot for the next departure.
        if (Train.TravelledCm >= Total - ConsistLengthCm)
        {
            Train.bActive = false;
            const FTransform Parked(FRotator::ZeroRotator, GetActorLocation() - FVector(0, 0, 200000), FVector::OneVector);
            for (int32 C = 0; C < CarCount; ++C)
            {
                FBodyComponents& Components = BodyComponents[FirstTrainBodyIndex + C];
                for (int32 Group = 0; Group < 4; ++Group)
                {
                    const int32 Id = Train.CarInstanceIds[C * 4 + Group];
                    if (Components.Groups[Group] && Id != INDEX_NONE)
                    {
                        Components.Groups[Group]->UpdateInstanceTransform(Id, Parked, true, false, true);
                        TouchedThisFrame.Add(Components.Groups[Group]);
                    }
                }
                // The door leaves are separate instances on separate components. Parking
                // only the car bodies would leave a row of doors hanging in mid-air at
                // the end of the line until the slot was dispatched again.
                for (int32 D = 0; D < Components.DoorLocalOffsets.Num(); ++D)
                {
                    const int32 Id = C * Components.DoorLocalOffsets.Num() + D;
                    if (!Train.DoorInstanceIds.IsValidIndex(Id))
                    {
                        continue;
                    }
                    if (Components.DoorPaint)
                    {
                        Components.DoorPaint->UpdateInstanceTransform(Train.DoorInstanceIds[Id], Parked, true, false, true);
                        TouchedThisFrame.Add(Components.DoorPaint);
                    }
                    if (Components.DoorGlass)
                    {
                        Components.DoorGlass->UpdateInstanceTransform(Train.DoorInstanceIds[Id], Parked, true, false, true);
                        TouchedThisFrame.Add(Components.DoorGlass);
                    }
                }
            }
            continue;
        }

        for (int32 C = 0; C < CarCount; ++C)
        {
            Vec3 CarPosition{};
            double Yaw = 0.0, Pitch = 0.0;
            if (!SampleCarPose(Runtime.Points.GetData(), Runtime.Cumulative.GetData(), Count, true,
                               Train.DistanceCm, C, TrainCarLengthCm, TrainCouplingGapCm, TrainBogieInsetCm,
                               Route.LaneOffsetCm, Route.RideHeightCm, CarPosition, Yaw, Pitch))
            {
                continue;
            }
            // The rear cab faces backwards: same pose, yaw turned through 180.
            const bool bReversed = (CarCount > 1 && C == CarCount - 1);
            const FRotator Rotation(Pitch, bReversed ? Yaw + 180.0 : Yaw, 0.0);
            const FVector Location = ToVector(CarPosition);
            if (FVector::DistSquared2D(Location, ViewLocation) >
                static_cast<double>(InstanceCullEndCm) * InstanceCullEndCm)
            {
                continue;
            }
            FBodyComponents& Components = BodyComponents[FirstTrainBodyIndex + C];
            const FTransform Transform(Rotation, Location, FVector::OneVector);
            for (int32 Group = 0; Group < 4; ++Group)
            {
                const int32 Id = Train.CarInstanceIds[C * 4 + Group];
                if (Components.Groups[Group] && Id != INDEX_NONE)
                {
                    Components.Groups[Group]->UpdateInstanceTransform(Id, Transform, true, false, true);
                    TouchedThisFrame.Add(Components.Groups[Group]);
                }
            }
            if (Components.DoorPaint)
            {
                const double Offset = DoorOffsetCm(Train.Stop.DoorFraction, Train.Dwell.DoorTravelCm);
                for (int32 D = 0; D < Components.DoorLocalOffsets.Num(); ++D)
                {
                    const int32 Id = C * Components.DoorLocalOffsets.Num() + D;
                    if (!Train.DoorInstanceIds.IsValidIndex(Id))
                    {
                        continue;
                    }
                    const FVector Local = Components.DoorLocalOffsets[D] - FVector(Offset, 0.0, 0.0);
                    const FTransform Leaf(Rotation, Location + Rotation.RotateVector(Local), FVector::OneVector);
                    Components.DoorPaint->UpdateInstanceTransform(Train.DoorInstanceIds[Id], Leaf, true, false, true);
                    TouchedThisFrame.Add(Components.DoorPaint);
                    if (Components.DoorGlass)
                    {
                        Components.DoorGlass->UpdateInstanceTransform(Train.DoorInstanceIds[Id], Leaf, true, false, true);
                        TouchedThisFrame.Add(Components.DoorGlass);
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Boarding hook
// ---------------------------------------------------------------------------

void AMikdashTransit::BroadcastBoarding(int32 RouteIdx, int32 LocalStopIdx, int32 VehicleId, int32 RunIndex,
                                        const FVector& DoorPoint, float SecondsAvailable)
{
    if (!RouteRuntimes.IsValidIndex(RouteIdx) || !RouteRuntimes[RouteIdx].GlobalStopIndices.IsValidIndex(LocalStopIdx))
    {
        return;
    }
    const FMikdashTransitStop& Stop = Routes[RouteIdx].Stops[LocalStopIdx];
    const int32 GlobalStop = RouteRuntimes[RouteIdx].GlobalStopIndices[LocalStopIdx];
    const int32 Count = BoardingCountFor(static_cast<uint32>(Seed), VehicleId, GlobalStop, RunIndex,
                                         Stop.BoardingMinPeople, Stop.BoardingMaxPeople, DensityMultiplier);
    if (Count <= 0)
    {
        return;
    }
    if (!FMath::IsFinite(SecondsAvailable) || SecondsAvailable <= 0) return;
    FMikdashPassengerExchange Request;
    Request.RouteId = Routes[RouteIdx].Id; Request.Generation = ExchangeGeneration;
    Request.VehicleId = VehicleId; Request.RunIndex = RunIndex; Request.GlobalStopIndex = GlobalStop;
    Request.Count = Count; Request.BoardingPoint = DoorPoint;
    Request.StartSimulationSeconds = WorldSeconds; Request.SecondsAvailable = SecondsAvailable;
    OnPassengerExchange.Broadcast(Request);
    // Compatibility notifications happen while doors are OPEN, never after departure.
    RequestAlighting(GlobalStop, Count, DoorPoint, SecondsAvailable);
    OnRequestAlighting.Broadcast(GlobalStop, Count, DoorPoint, SecondsAvailable, Request.RouteId);
    RequestBoarding(GlobalStop, Count, DoorPoint, SecondsAvailable);
    OnRequestBoarding.Broadcast(GlobalStop, Count, DoorPoint, SecondsAvailable, Request.RouteId);

}

bool AMikdashTransit::IsPassengerExchangeOpen(const FMikdashPassengerExchange& Request) const
{
    if (!bActive || Request.Generation != ExchangeGeneration) return false;
    const MikdashTransit::StopState* State = nullptr;
    int32 RouteIdx = INDEX_NONE;
    if (Request.VehicleId < 1000 && Vehicles.IsValidIndex(Request.VehicleId))
    {
        State = &Vehicles[Request.VehicleId].Stop; RouteIdx = Vehicles[Request.VehicleId].RouteIndex;
    }
    else for (const FTrain& Train : Trains)
        if (Train.bActive && 1000 + Train.Id == Request.VehicleId) { State = &Train.Stop; RouteIdx = RailRouteIndex; break; }
    if (!State || State->RunIndex != Request.RunIndex || State->Phase != MikdashTransit::StopPhase::Dwelling
        || !Routes.IsValidIndex(RouteIdx) || Routes[RouteIdx].Id != Request.RouteId
        || !RouteRuntimes[RouteIdx].GlobalStopIndices.IsValidIndex(State->ServedStopIndex)) return false;
    return RouteRuntimes[RouteIdx].GlobalStopIndices[State->ServedStopIndex] == Request.GlobalStopIndex;
}

int32 AMikdashTransit::SuggestPhotographerCount(int32 GlobalStopIndex, int32 Count, int32 RunIndex) const
{
    if (!StopIndex.IsValidIndex(GlobalStopIndex))
    {
        return 0;
    }
    return PhotographerCount(static_cast<uint32>(Seed), GlobalStopIndex, RunIndex, Count, PhotographerShare);
}

FVector AMikdashTransit::GetStopLocation(int32 GlobalStopIndex) const
{
    if (!StopIndex.IsValidIndex(GlobalStopIndex))
    {
        return FVector::ZeroVector;
    }
    const FIntPoint Address = StopIndex[GlobalStopIndex];
    return Routes[Address.X].Stops[Address.Y].WorldPosition;
}

FVector AMikdashTransit::GetStopFurniturePoint(int32 GlobalStopIndex) const
{
    if (!StopIndex.IsValidIndex(GlobalStopIndex))
    {
        return FVector::ZeroVector;
    }
    const FIntPoint Address = StopIndex[GlobalStopIndex];
    const FRouteRuntime& Runtime = RouteRuntimes[Address.X];
    Vec3 Position{}, Tangent{};
    if (!Runtime.StopDistances.IsValidIndex(Address.Y)
        || !SampleRoute(Runtime.Points.GetData(), Runtime.Cumulative.GetData(), Runtime.Points.Num(), true,
                        Runtime.StopDistances[Address.Y], Position, Tangent))
    {
        return Routes[Address.X].Stops[Address.Y].WorldPosition;
    }
    return ToVector(ApplyLaneOffset(Position, Tangent,
                                    Routes[Address.X].Stops[Address.Y].FurnitureOffsetCm * 0.6,
                                    Routes[Address.X].RideHeightCm));
}

FName AMikdashTransit::GetStopRouteId(int32 GlobalStopIndex) const
{
    return StopIndex.IsValidIndex(GlobalStopIndex) ? Routes[StopIndex[GlobalStopIndex].X].Id : NAME_None;
}

FString AMikdashTransit::GetStopName(int32 GlobalStopIndex) const
{
    if (!StopIndex.IsValidIndex(GlobalStopIndex))
    {
        return FString();
    }
    const FIntPoint Address = StopIndex[GlobalStopIndex];
    return Routes[Address.X].Stops[Address.Y].Name;
}

float AMikdashTransit::GetStopProjectionErrorCm(int32 GlobalStopIndex) const
{
    if (!StopIndex.IsValidIndex(GlobalStopIndex))
    {
        return -1.f;
    }
    const FIntPoint Address = StopIndex[GlobalStopIndex];
    const FRouteRuntime& Runtime = RouteRuntimes[Address.X];
    return Runtime.StopErrorCm.IsValidIndex(Address.Y) ? static_cast<float>(Runtime.StopErrorCm[Address.Y]) : -1.f;
}
