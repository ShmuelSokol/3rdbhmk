#include "MikdashTransitBoardingBridge.h"

#include "MikdashCrowdField.h"
#include "MikdashTransitCrowdCoordinator.h"

#include "CollisionQueryParams.h"
#include "CollisionShape.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"

namespace
{
using MikdashBoardingBridge::Vec2;

FORCEINLINE Vec2 ToVec2(const FVector& V) { return Vec2{V.X, V.Y}; }
FORCEINLINE FVector ToVector(const Vec2& V, double Z) { return FVector(V.X, V.Y, Z); }

/** Where a hidden instance is parked: far below the world at a scale too small to draw.
 * Scale is not zero because a zero-scaled instance can degenerate the HISM cluster bounds.
 * Function-local so it never depends on static initialisation order across modules. */
const FTransform& HiddenTransform()
{
    static const FTransform Hidden(FRotator::ZeroRotator, FVector(0.0, 0.0, -200000.0), FVector(0.0001));
    return Hidden;
}

/** Nothing about a figure may live longer than the dwell plus a full walk plus a photograph. */
constexpr double GroupLifetimeSlackSeconds = 90.0;
constexpr float FigureCapsuleRadiusCm = 34.f;
constexpr float FigureCapsuleHalfHeightCm = 96.f;
constexpr double BobAmplitudeCm = 3.5;
constexpr double LeanAmplitudeDegrees = 4.0;
constexpr int32 RecentExchangeRing = 64;
}  // namespace

AMikdashTransitBoardingBridge::AMikdashTransitBoardingBridge()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = false;   // nothing ticks until InitializeBridge succeeds
    PrimaryActorTick.TickGroup = TG_PrePhysics;

    USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);

    const auto Configure = [Root](UHierarchicalInstancedStaticMeshComponent* Component)
    {
        Component->SetupAttachment(Root);
        Component->SetMobility(EComponentMobility::Movable);
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Component->SetCollisionProfileName(TEXT("NoCollision"));
        Component->SetGenerateOverlapEvents(false);
        Component->SetCastShadow(false);
        Component->SetCanEverAffectNavigation(false);
        Component->NumCustomDataFloats = 3;   // 0 gait phase, 1 garment tint, 2 standing flag: the crowd's convention
    };
    PoseComponents.Reserve(MaxPoseComponents);
    for (int32 Index = 0; Index < MaxPoseComponents; ++Index)
    {
        UHierarchicalInstancedStaticMeshComponent* Component = CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(
            *FString::Printf(TEXT("BridgePose%d"), Index));
        Configure(Component);
        PoseComponents.Add(Component);
    }
    PhotoComponent = CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(TEXT("BridgePhotographerPose"));
    Configure(PhotoComponent);
    SetActorEnableCollision(false);
}

void AMikdashTransitBoardingBridge::BeginPlay()
{
    Super::BeginPlay();
    if (bActivateOnBeginPlay)
    {
        InitializeBridge();
    }
}

void AMikdashTransitBoardingBridge::EndPlay(const EEndPlayReason::Type Reason)
{
    ShutdownBridge();
    Super::EndPlay(Reason);
}

// ---------------------------------------------------------------------------
// Start / stop
// ---------------------------------------------------------------------------

bool AMikdashTransitBoardingBridge::ResolveActors()
{
    UWorld* World = GetWorld();
    if (!World) { Status = TEXT("Refused: no world"); return false; }
    if (!IsValid(Transit) && bAutoFindActors)
    {
        int32 Found = 0;
        for (TActorIterator<AMikdashTransit> It(World); It; ++It) { Transit = *It; ++Found; }
        if (Found != 1) { Status = FString::Printf(TEXT("Refused: %d AMikdashTransit actors in the level, need exactly one"), Found); Transit = nullptr; return false; }
    }
    if (!IsValid(CrowdField) && bAutoFindActors)
    {
        int32 Found = 0;
        for (TActorIterator<AMikdashCrowdField> It(World); It; ++It) { CrowdField = *It; ++Found; }
        if (Found != 1) { Status = FString::Printf(TEXT("Refused: %d AMikdashCrowdField actors in the level, need exactly one"), Found); CrowdField = nullptr; return false; }
    }
    if (!IsValid(Transit)) { Status = TEXT("Refused: no transit actor"); return false; }
    if (!IsValid(CrowdField)) { Status = TEXT("Refused: no crowd field actor"); return false; }
    if (Transit->GetWorld() != World || CrowdField->GetWorld() != World) { Status = TEXT("Refused: transit or crowd actor is in another world"); return false; }
    return true;
}

bool AMikdashTransitBoardingBridge::CoordinatorIsActive() const
{
    if (UWorld* World = GetWorld())
    {
        for (TActorIterator<AMikdashTransitCrowdCoordinator> It(World); It; ++It)
        {
            if (It->bActivateOnBeginPlay || It->GetActiveTransferCount() > 0) return true;
        }
    }
    return false;
}

bool AMikdashTransitBoardingBridge::InitializeBridge()
{
    if (bRunning) ShutdownBridge();
    UWorld* World = GetWorld();
    if (!World || !World->IsGameWorld()) { Status = TEXT("Refused: not a game world"); return false; }
    if (!ResolveActors()) return false;
    if (bRefuseIfCoordinatorActive && CoordinatorIsActive())
    {
        Status = TEXT("Refused: an AMikdashTransitCrowdCoordinator is active in this level; running both would double every exchange");
        return false;
    }
    if (CrowdField->PoseMeshes.IsEmpty() || !CrowdField->PoseMeshes[0])
    {
        Status = TEXT("Refused: the crowd field has no pose mesh to borrow");
        return false;
    }
    if (!FMath::IsFinite(WalkSpeedMinCmPerSecond) || !FMath::IsFinite(WalkSpeedMaxCmPerSecond)
        || WalkSpeedMinCmPerSecond <= 0.f || WalkSpeedMaxCmPerSecond <= 0.f || MountFocusCm.ContainsNaN())
    {
        Status = TEXT("Refused: non-finite walking speed or Mount focus");
        return false;
    }
    if (GatherFarCm < GatherNearCm || DispersalMaxCm < DispersalMinCm || PhotoSpotMaxCm < PhotoSpotMinCm
        || GatherNearCm - 25.f < DoorClearanceCm || DispersalMinCm * 0.34f < DoorClearanceCm || PhotoSpotMinCm * 0.34f < DoorClearanceCm)
    {
        // The last three are the guarantees BoardingBridgeMathTest proves for the defaults:
        // a lattice point is never nearer than GatherNearCm - 25 and a fan point never nearer
        // than 0.34 * MinRadius. Weakening them would let a plan stand inside the vehicle.
        Status = TEXT("Refused: apron distances would allow a figure inside the vehicle body");
        return false;
    }

    CrowdHost = Cast<IMikdashCrowdPartyHost>(CrowdField.Get());
    CacheCrowdGeometry();
    BuildPool();
    StopAcceptance.Reset();
    StopArrivals.Reset();
    RecentExchanges.Reset();
    Groups.Reset();
    GroupsStarted = GroupsRefusedCap = GroupsRefusedGeometry = GroupsRefusedStop = GroupsRefusedPool = 0;
    PeopleBoarded = PeopleAlighted = PeopleTrimmed = Photographers = Overruns = GroundMisses = 0;
    Cursor = 0;

    // Bind all three hooks. The two legacy hooks are what this bridge acts on; the rich
    // exchange fires first from the same call and supplies RunIndex / VehicleId, which the
    // legacy payload lacks and which the photographer hint and the doors-open check need.
    Transit->OnPassengerExchange.AddUniqueDynamic(this, &AMikdashTransitBoardingBridge::HandleExchange);
    Transit->OnRequestAlighting.AddUniqueDynamic(this, &AMikdashTransitBoardingBridge::HandleAlighting);
    Transit->OnRequestBoarding.AddUniqueDynamic(this, &AMikdashTransitBoardingBridge::HandleBoarding);
    AddTickPrerequisiteActor(Transit);

    // Stops are judged against the route the runtime actually built. When the transit actor
    // has not initialised yet its stop count is zero and every stop is judged lazily at its
    // first arrival instead; StopAccepted() always re-reads the projection error.
    int32 Refused = 0;
    for (int32 StopIndex = 0; StopIndex < Transit->GetStopCount(); ++StopIndex)
    {
        if (!StopAccepted(StopIndex)) ++Refused;
    }
    bRunning = true;
    SetActorTickEnabled(true);
    Status = FString::Printf(TEXT("active: %d figures in %d poses, cap %d groups, %d of %d stops refused for projection error > %.0f cm, crowd hand-over %s"),
                             Figures.Num(), ActivePoseCount, MaxConcurrentGroups, Refused, Transit->GetStopCount(), MaxStopProjectionErrorCm,
                             CrowdHost ? TEXT("available") : TEXT("not implemented by the crowd"));
    return true;
}

void AMikdashTransitBoardingBridge::ShutdownBridge()
{
    if (IsValid(Transit))
    {
        Transit->OnPassengerExchange.RemoveDynamic(this, &AMikdashTransitBoardingBridge::HandleExchange);
        Transit->OnRequestAlighting.RemoveDynamic(this, &AMikdashTransitBoardingBridge::HandleAlighting);
        Transit->OnRequestBoarding.RemoveDynamic(this, &AMikdashTransitBoardingBridge::HandleBoarding);
        RemoveTickPrerequisiteActor(Transit);
    }
    bRunning = false;
    SetActorTickEnabled(false);
    for (const TObjectPtr<UHierarchicalInstancedStaticMeshComponent>& Component : PoseComponents)
    {
        if (Component) Component->ClearInstances();
    }
    if (PhotoComponent) PhotoComponent->ClearInstances();
    Figures.Reset();
    Groups.Reset();
    RecentExchanges.Reset();
    CrowdHost = nullptr;
    ActivePoseCount = 0;
    if (Status.StartsWith(TEXT("active"))) Status = TEXT("inactive");
}

void AMikdashTransitBoardingBridge::BuildPool()
{
    ActivePoseCount = 0;
    for (int32 Index = 0; Index < PoseComponents.Num(); ++Index)
    {
        UHierarchicalInstancedStaticMeshComponent* Component = PoseComponents[Index];
        Component->ClearInstances();
        UStaticMesh* Mesh = CrowdField->PoseMeshes.IsValidIndex(Index) ? CrowdField->PoseMeshes[Index].Get() : nullptr;
        Component->SetStaticMesh(Mesh);
        Component->SetCastShadow(bCastShadows);
        Component->SetCullDistances(CrowdField->InstanceStartCullDistanceCm, CrowdField->InstanceEndCullDistanceCm);
        if (Mesh)
        {
            if (CrowdField->CrowdMaterialOverride)
            {
                for (int32 Slot = 0; Slot < Mesh->GetStaticMaterials().Num(); ++Slot)
                {
                    Component->SetMaterial(Slot, CrowdField->CrowdMaterialOverride);
                }
            }
            ++ActivePoseCount;
        }
    }
    PhotoComponent->ClearInstances();
    PhotoComponent->SetStaticMesh(PhotographerPoseMesh);
    PhotoComponent->SetCastShadow(bCastShadows);
    PhotoComponent->SetCullDistances(CrowdField->InstanceStartCullDistanceCm, CrowdField->InstanceEndCullDistanceCm);
    if (PhotographerPoseMesh && CrowdField->CrowdMaterialOverride)
    {
        for (int32 Slot = 0; Slot < PhotographerPoseMesh->GetStaticMaterials().Num(); ++Slot)
        {
            PhotoComponent->SetMaterial(Slot, CrowdField->CrowdMaterialOverride);
        }
    }

    const int32 Count = FMath::Clamp(MaxFigures, 8, 1024);
    Figures.Reset();
    Figures.SetNum(Count);
    // Figure i draws with pose (i mod poses) as instance (i div poses) of that component.
    for (int32 Index = 0; Index < Count; ++Index)
    {
        Figures[Index].Pose = ActivePoseCount > 0 ? Index % ActivePoseCount : 0;
        UHierarchicalInstancedStaticMeshComponent* Component = PoseComponents[Figures[Index].Pose];
        Component->AddInstance(HiddenTransform(), /*bWorldSpace*/ true);
        if (PhotographerPoseMesh) PhotoComponent->AddInstance(HiddenTransform(), /*bWorldSpace*/ true);
    }
    for (const TObjectPtr<UHierarchicalInstancedStaticMeshComponent>& Component : PoseComponents)
    {
        Component->MarkRenderStateDirty();
    }
    PhotoComponent->MarkRenderStateDirty();
}

void AMikdashTransitBoardingBridge::CacheCrowdGeometry()
{
    // The crowd converts its authored (legacy 50 cm) polygons into the current world's frame
    // at run time and exposes the converted copies only by name, so the names are read from
    // the authored arrays and the geometry from the runtime getters.
    KeepOutPoints.Reset(); KeepOutStarts.Reset(); KeepOutCounts.Reset();
    ZonePoints.Reset(); ZoneStarts.Reset(); ZoneCounts.Reset();
    KeepOutMarginCm = FMath::Max(0.f, CrowdField->ProtectedMarginCm);
    for (const FMikdashCrowdKeepOut& Authored : CrowdField->ProtectedPolygons)
    {
        FMikdashCrowdKeepOut Runtime;
        const FMikdashCrowdKeepOut& Use = CrowdField->GetRuntimeKeepOut(Authored.Name, Runtime) ? Runtime : Authored;
        if (Use.PolygonCm.Num() < 3) continue;
        KeepOutStarts.Add(KeepOutPoints.Num());
        KeepOutCounts.Add(Use.PolygonCm.Num());
        for (const FVector2D& P : Use.PolygonCm) KeepOutPoints.Add(MikdashCrowd::Vec2{P.X, P.Y});
    }
    for (const FMikdashCrowdZone& Authored : CrowdField->Zones)
    {
        FMikdashCrowdZone Runtime;
        const FMikdashCrowdZone& Use = CrowdField->GetRuntimeZone(Authored.Name, Runtime) ? Runtime : Authored;
        if (Use.PolygonCm.Num() < 3) continue;
        ZoneStarts.Add(ZonePoints.Num());
        ZoneCounts.Add(Use.PolygonCm.Num());
        for (const FVector2D& P : Use.PolygonCm) ZonePoints.Add(MikdashCrowd::Vec2{P.X, P.Y});
    }
}

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

double AMikdashTransitBoardingBridge::Now() const
{
    return IsValid(Transit) ? Transit->GetTransitSeconds() : 0.0;
}

bool AMikdashTransitBoardingBridge::StopAccepted(int32 GlobalStopIndex)
{
    if (!IsValid(Transit) || GlobalStopIndex < 0 || GlobalStopIndex >= Transit->GetStopCount()) return false;
    const float Error = Transit->GetStopProjectionErrorCm(GlobalStopIndex);
    const bool bAccepted = FMath::IsFinite(Error) && Error >= 0.f && Error <= MaxStopProjectionErrorCm;
    StopAcceptance.Add(GlobalStopIndex, bAccepted);
    return bAccepted;
}

bool AMikdashTransitBoardingBridge::IsStopAccepted(int32 GlobalStopIndex) const
{
    const bool* Known = StopAcceptance.Find(GlobalStopIndex);
    return Known ? *Known : false;
}

TArray<int32> AMikdashTransitBoardingBridge::GetRefusedStopIndices() const
{
    TArray<int32> Result;
    for (const TPair<int32, bool>& Pair : StopAcceptance)
    {
        if (!Pair.Value) Result.Add(Pair.Key);
    }
    Result.Sort();
    return Result;
}

bool AMikdashTransitBoardingBridge::MatchExchange(int32 GlobalStopIndex, int32 Count, const FVector& BoardingPoint, FMikdashPassengerExchange& Out) const
{
    // The rich request for the same doors-open edge fired immediately before the legacy hook,
    // from the same BroadcastBoarding call, so it is the newest ring entry with these values.
    for (int32 Index = RecentExchanges.Num() - 1; Index >= 0; --Index)
    {
        const FMikdashPassengerExchange& Candidate = RecentExchanges[Index];
        if (Candidate.GlobalStopIndex == GlobalStopIndex && Candidate.Count == Count
            && FVector::DistSquared(Candidate.BoardingPoint, BoardingPoint) < 1.0)
        {
            Out = Candidate;
            return true;
        }
    }
    return false;
}

bool AMikdashTransitBoardingBridge::GroundAt(const FVector& Approximate, FVector& Feet)
{
    Feet = Approximate;
    if (Approximate.ContainsNaN()) return false;
    if (!bTraceGround) return true;
    UWorld* World = GetWorld();
    if (!World) return true;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(BoardingBridgeGround), /*bTraceComplex*/ true);
    Params.AddIgnoredActor(this);
    Params.AddIgnoredActor(Transit);
    Params.AddIgnoredActor(CrowdField);
    FHitResult Hit;
    const FVector Start = Approximate + FVector(0, 0, GroundTraceToleranceCm);
    const FVector End = Approximate - FVector(0, 0, GroundTraceToleranceCm);
    if (World->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params) && Hit.bBlockingHit && Hit.ImpactNormal.Z >= 0.7)
    {
        Feet = Hit.ImpactPoint;
        return true;
    }
    // Where the trace misses (commandlets, NullRHI, a road mesh without collision) the door
    // threshold's own height is used. Counted, never hidden.
    ++GroundMisses;
    return true;
}

bool AMikdashTransitBoardingBridge::PointAllowed(const FVector& Feet) const
{
    if (Feet.ContainsNaN()) return false;
    const MikdashCrowd::Vec2 P{Feet.X, Feet.Y};
    if (MikdashCrowd::PointInAnyProtected(KeepOutPoints.GetData(), KeepOutStarts.GetData(), KeepOutCounts.GetData(),
                                          KeepOutCounts.Num(), P, KeepOutMarginCm))
    {
        return false;
    }
    // Inside an authored crowd zone the crowd's own (stricter) judgement applies as well.
    for (int32 Zone = 0; Zone < ZoneCounts.Num(); ++Zone)
    {
        if (MikdashCrowd::PointInPolygon(ZonePoints.GetData() + ZoneStarts[Zone], ZoneCounts[Zone], P))
        {
            if (!CrowdField->IsTransitSegmentAllowed(Feet, Feet, FigureCapsuleRadiusCm)) return false;
            break;
        }
    }
    if (CrowdHost && !CrowdHost->IsCrowdPointAllowed(Feet, FigureCapsuleRadiusCm)) return false;
    return true;
}

bool AMikdashTransitBoardingBridge::SegmentAllowed(const FVector& From, const FVector& To) const
{
    if (From.ContainsNaN() || To.ContainsNaN()) return false;
    const double Length = FVector::Dist2D(From, To);
    if (Length > MikdashBoardingBridge::MaxWalkCm) return false;
    const int32 Steps = MikdashBoardingBridge::SegmentSampleCount(Length, 25.0);
    for (int32 Step = 0; Step <= Steps; ++Step)
    {
        if (!PointAllowed(FMath::Lerp(From, To, static_cast<double>(Step) / Steps))) return false;
    }
    if (bSweepStaticObstacles && Length > 1.0)
    {
        UWorld* World = GetWorld();
        if (!World) return true;
        FCollisionQueryParams Params(SCENE_QUERY_STAT(BoardingBridgeSweep), false);
        Params.AddIgnoredActor(this);
        Params.AddIgnoredActor(Transit);
        Params.AddIgnoredActor(CrowdField);
        const FVector Lift(0, 0, FigureCapsuleHalfHeightCm + 2.f);
        const FCollisionShape Capsule = FCollisionShape::MakeCapsule(FigureCapsuleRadiusCm, FigureCapsuleHalfHeightCm);
        FHitResult Hit;
        if (World->SweepSingleByChannel(Hit, From + Lift, To + Lift, FQuat::Identity, ECC_Pawn, Capsule, Params) && Hit.bBlockingHit)
        {
            return false;
        }
    }
    return true;
}

int32 AMikdashTransitBoardingBridge::FreeFigure() const
{
    for (int32 Index = 0; Index < Figures.Num(); ++Index)
    {
        if (!Figures[Index].bActive) return Index;
    }
    return INDEX_NONE;
}

int32 AMikdashTransitBoardingBridge::FreeFigureCount() const
{
    int32 Count = 0;
    for (const FMikdashBoardingFigure& Figure : Figures) Count += Figure.bActive ? 0 : 1;
    return Count;
}

int32 AMikdashTransitBoardingBridge::GetActiveGroupCount() const
{
    int32 Count = 0;
    for (const FMikdashBoardingGroup& Group : Groups) Count += Group.bActive ? 1 : 0;
    return Count;
}

int32 AMikdashTransitBoardingBridge::GetActiveFigureCount() const
{
    return Figures.Num() - FreeFigureCount();
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

void AMikdashTransitBoardingBridge::HandleExchange(const FMikdashPassengerExchange& Request)
{
    if (!bRunning) return;
    if (RecentExchanges.Num() >= RecentExchangeRing) RecentExchanges.RemoveAt(0);
    RecentExchanges.Add(Request);
}

void AMikdashTransitBoardingBridge::HandleAlighting(int32 GlobalStopIndex, int32 Count, FVector BoardingPoint, float SecondsAvailable, FName RouteId)
{
    StartGroup(GlobalStopIndex, Count, BoardingPoint, SecondsAvailable, RouteId, /*bAlighting*/ true);
}

void AMikdashTransitBoardingBridge::HandleBoarding(int32 GlobalStopIndex, int32 Count, FVector BoardingPoint, float SecondsAvailable, FName RouteId)
{
    StartGroup(GlobalStopIndex, Count, BoardingPoint, SecondsAvailable, RouteId, /*bAlighting*/ false);
}

void AMikdashTransitBoardingBridge::StartGroup(int32 GlobalStopIndex, int32 Count, const FVector& BoardingPoint, float SecondsAvailable,
                                               FName RouteId, bool bAlighting)
{
    using namespace MikdashBoardingBridge;
    if (!bRunning || !IsValid(Transit) || !Transit->IsTransitActive() || Count <= 0 || BoardingPoint.ContainsNaN()
        || !FMath::IsFinite(SecondsAvailable) || SecondsAvailable <= 0.f)
    {
        return;
    }
    if (!StopAccepted(GlobalStopIndex)) { ++GroupsRefusedStop; return; }

    const Window W = DwellWindow(SecondsAvailable, CloseMarginSeconds);
    if (!W.bUsable) { ++GroupsRefusedGeometry; return; }
    if (!AdmitGroup(GetActiveGroupCount(), MaxConcurrentGroups)) { ++GroupsRefusedCap; return; }

    // The apron: this arrival's door (kerb side) and the stop's platform face.
    const FVector Furniture = Transit->GetStopFurniturePoint(GlobalStopIndex);
    Apron A;
    if (!MakeApron(ToVec2(BoardingPoint), ToVec2(Furniture), A)) { ++GroupsRefusedGeometry; return; }
    FVector DoorFeet;
    GroundAt(BoardingPoint, DoorFeet);
    if (!PointAllowed(DoorFeet)) { ++GroupsRefusedGeometry; return; }

    FMikdashBoardingGroup Group;
    Group.bHasExchange = MatchExchange(GlobalStopIndex, Count, BoardingPoint, Group.Exchange);
    if (Group.bHasExchange && Group.Exchange.RouteId != RouteId) Group.bHasExchange = false;
    int32 RunIndex;
    if (Group.bHasExchange)
    {
        RunIndex = Group.Exchange.RunIndex;
    }
    else
    {
        // Only the legacy hook fired (a Blueprint subclass re-broadcasting, say): count the
        // arrivals at this stop so the plan stays deterministic per arrival.
        int32& Arrivals = StopArrivals.FindOrAdd(GlobalStopIndex);
        RunIndex = Arrivals++;
        Group.Exchange.RouteId = RouteId;
        Group.Exchange.GlobalStopIndex = GlobalStopIndex;
        Group.Exchange.Count = Count;
        Group.Exchange.BoardingPoint = BoardingPoint;
        Group.Exchange.RunIndex = RunIndex;
        Group.Exchange.SecondsAvailable = SecondsAvailable;
        Group.Exchange.StartSimulationSeconds = Now();
    }
    Group.bAlighting = bAlighting;
    Group.Seed = GroupSeed(static_cast<uint32>(Seed), GlobalStopIndex, RunIndex, bAlighting);
    Group.StartAt = Now();
    Group.Deadline = Group.StartAt + W.Deadline;

    const int32 Doors = FMath::Clamp(DoorsPerVehicle, 1, 6);
    const int32 N = GroupSizeForDwell(Count, W, bAlighting, Doors, SecondsPerPersonPerDoor, MaxPeoplePerGroup, FreeFigureCount(), MinPeoplePerGroup);
    if (N <= 0) { ++GroupsRefusedPool; PeopleTrimmed += Count; return; }
    PeopleTrimmed += Count - N;

    // Which alighters photograph: the transit layer's own hint, applied to the animated group.
    TArray<bool> PhotoFlags;
    int32 PhotoCount = 0;
    if (bAlighting)
    {
        PhotoFlags.SetNumZeroed(N);
        PhotoCount = SelectPhotographers(Group.Seed, N, Transit->SuggestPhotographerCount(GlobalStopIndex, N, RunIndex), PhotoFlags.GetData());
    }

    // Boarders drawn from the real waiting crowd, when the crowd can give them up. The
    // radius is bounded so every released figure provably reaches the door in time.
    TArray<FVector> Released;
    if (!bAlighting && CrowdHost)
    {
        const float Radius = static_cast<float>(FMath::Min(MaxWalkCm, W.BoardStart * WalkSpeedMinCmPerSecond));
        CrowdHost->TryReleaseNearest(Furniture, N, Radius, Released);
    }

    const double Threshold = DoorClearanceCm;
    const FVector DoorSide = ToVector(A.Door + A.Out * Threshold, DoorFeet.Z);
    const int32 GroupIndex = Groups.Num();
    int32 Placed = 0, Walkers = 0;
    for (int32 Member = 0; Member < N; ++Member)
    {
        const int32 Slot = FreeFigure();
        if (Slot == INDEX_NONE) break;
        FMikdashBoardingFigure Figure;
        Figure.Speed = static_cast<float>(WalkSpeedFor(Group.Seed, Member, WalkSpeedMinCmPerSecond, WalkSpeedMaxCmPerSecond));
        Figure.Scale = static_cast<float>(FigureScaleFor(Group.Seed, Member, FigureScaleMin, FigureScaleMax));
        const int32 Palette = FMath::Max(1, CrowdField->GarmentPaletteSize);
        Figure.Tint = Palette > 1 ? static_cast<float>(GarmentIndexFor(Group.Seed, Member, Palette)) / static_cast<float>(Palette - 1) : 0.f;
        Figure.Phase = static_cast<float>(HashUnit(Group.Seed, static_cast<uint32>(Member), 67u));
        Figure.Group = GroupIndex;
        Figure.bAlighting = bAlighting ? 1 : 0;

        FVector From, To;
        if (bAlighting)
        {
            // Step off at the threshold, on the kerb side, with a little spread along the door.
            const Vec2 Exit = A.Door + A.Out * Threshold + A.Side * HashRange(Group.Seed, static_cast<uint32>(Member), 71u, -40.0, 40.0);
            const bool bPhoto = PhotoFlags[Member];
            const Vec2 Target = bPhoto ? DispersalPoint(A, Group.Seed, Member, PhotoSpotMinCm, PhotoSpotMaxCm)
                                       : DispersalPoint(A, Group.Seed, Member, DispersalMinCm, DispersalMaxCm);
            FVector TargetFeet;
            GroundAt(ToVector(Target, DoorFeet.Z), TargetFeet);
            From = ToVector(Exit, DoorFeet.Z);
            To = TargetFeet;
            if (!OutsideVehicle(A, Target, Threshold) || !SegmentAllowed(From, To)) { ++PeopleTrimmed; continue; }
            Figure.bPhotographer = bPhoto ? 1 : 0;
            Figure.DepartAt = Group.StartAt + AlightStepOutSeconds(Member, Doors, SecondsPerPersonPerDoor);
            Figure.ArriveAt = Figure.DepartAt + FVector::Dist2D(From, To) / Figure.Speed;
            Figure.HoldUntil = bPhoto ? Figure.ArriveAt + PhotographerHoldSeconds(Group.Seed, Member, PhotographerHoldMinSeconds, PhotographerHoldMaxSeconds) : 0.0;
            if (!bPhoto) ++Walkers;
        }
        else
        {
            Vec2 Gather;
            if (Released.IsValidIndex(Member) && !Released[Member].ContainsNaN()) Gather = ToVec2(Released[Member]);
            else Gather = GatherPoint(A, Group.Seed, Member, GatherNearCm, GatherFarCm, GatherHalfWidthCm);
            if (!OutsideVehicle(A, Gather, Threshold)) { ++PeopleTrimmed; continue; }
            FVector GatherFeet;
            GroundAt(ToVector(Gather, DoorFeet.Z), GatherFeet);
            From = GatherFeet;
            To = DoorSide;
            const ConvergePlan Plan = ConvergeSchedule(Member, FVector::Dist2D(From, To), Figure.Speed, W, Doors, SecondsPerPersonPerDoor);
            if (!Plan.bFits || !SegmentAllowed(From, To)) { ++PeopleTrimmed; continue; }
            Figure.DepartAt = Group.StartAt + Plan.DepartAt;
            Figure.ArriveAt = Group.StartAt + Plan.ArriveAt;
        }
        Figure.From = From;
        Figure.To = To;
        Figure.Position = From;
        Figure.Yaw = static_cast<float>(YawToward(ToVec2(From), ToVec2(To)));
        Figure.Pose = Figures[Slot].Pose;   // the pose is bound to the pool slot
        Figure.bActive = 1;
        Figures[Slot] = Figure;
        ++Placed;
    }
    if (Placed == 0) { ++GroupsRefusedGeometry; return; }

    Group.bActive = true;
    Group.Figures = Placed;
    Group.Remaining = Placed;
    Group.WalkersTotal = Walkers;
    Group.WalkersArrived = 0;
    Photographers += bAlighting ? FMath::Min(PhotoCount, Placed) : 0;
    // Reuse a retired slot so the array never grows past the cap plus a few.
    int32 Reuse = INDEX_NONE;
    for (int32 Index = 0; Index < Groups.Num(); ++Index) if (!Groups[Index].bActive) { Reuse = Index; break; }
    if (Reuse != INDEX_NONE)
    {
        Groups[Reuse] = Group;
        for (FMikdashBoardingFigure& Figure : Figures) if (Figure.bActive && Figure.Group == GroupIndex) Figure.Group = Reuse;
    }
    else
    {
        Groups.Add(Group);
    }
    ++GroupsStarted;
}

// ---------------------------------------------------------------------------
// Per frame
// ---------------------------------------------------------------------------

void AMikdashTransitBoardingBridge::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bRunning || !IsValid(Transit) || Transit->IsTransitPaused() || UGameplayStatics::IsGamePaused(this)) return;
    if (!Transit->IsTransitActive())
    {
        // The transit run was torn down: every figure belongs to a vehicle that no longer exists.
        for (int32 Index = 0; Index < Figures.Num(); ++Index) if (Figures[Index].bActive) FinishFigure(Index);
        return;
    }
    using namespace MikdashBoardingBridge;
    const double T = Now();
    TouchedThisFrame.Reset();

    // Deadlines for EVERY figure every frame, independent of the movement budget: a boarder
    // still walking when the doors close is an overrun, reported and removed.
    for (int32 Index = 0; Index < Figures.Num(); ++Index)
    {
        FMikdashBoardingFigure& Figure = Figures[Index];
        if (!Figure.bActive || !Groups.IsValidIndex(Figure.Group)) continue;
        const FMikdashBoardingGroup& Group = Groups[Figure.Group];
        if (!Figure.bAlighting && T > Group.Deadline) { ++Overruns; FinishFigure(Index); continue; }
        if (T > Group.StartAt + Group.Exchange.SecondsAvailable + GroupLifetimeSlackSeconds || T < Group.StartAt) { FinishFigure(Index); continue; }
    }

    const int32 Budget = FMath::Min(Figures.Num(), FMath::Clamp(UpdateBudget, 1, 1024));
    for (int32 Visited = 0; Visited < Budget && Figures.Num() > 0; ++Visited)
    {
        const int32 Index = Cursor;
        Cursor = (Cursor + 1) % Figures.Num();
        FMikdashBoardingFigure& Figure = Figures[Index];
        if (!Figure.bActive || !Groups.IsValidIndex(Figure.Group)) continue;
        FMikdashBoardingGroup& Group = Groups[Figure.Group];

        if (T < Figure.DepartAt)
        {
            // Boarders wait visibly at their gather point; alighters are still inside the vehicle.
            if (!Figure.bAlighting && !Figure.bVisible) { Figure.bVisible = 1; Figure.Position = Figure.From; Render(Index, /*bStanding*/ true); }
            continue;
        }
        if (Figure.bHolding)
        {
            if (Figure.bPhotographer && T >= Figure.HoldUntil)
            {
                // Done photographing: the crowd may take this person on as an individual.
                if (CrowdHost)
                {
                    FMikdashCrowdPartyRequest Request;
                    Request.AnchorCm = Figure.Position; Request.Count = 1; Request.Seed = static_cast<int32>(Group.Seed);
                    Request.OutwardDirection = (Figure.To - Figure.From).GetSafeNormal2D();
                    Request.GlobalStopIndex = Group.Exchange.GlobalStopIndex;
                    TArray<int32> Adopted;
                    CrowdHost->TryAdoptParty(Request, Adopted);
                }
                ++PeopleAlighted;
                FinishFigure(Index);
            }
            else
            {
                Render(Index, /*bStanding*/ true);
            }
            continue;
        }

        const double Elapsed = T - Figure.DepartAt;
        const Vec2 P = WalkPosition(ToVec2(Figure.From), ToVec2(Figure.To), Figure.Speed, Elapsed);
        const double Total = FVector::Dist2D(Figure.From, Figure.To);
        const double Fraction = Total > 1e-6 ? FMath::Clamp(FVector::Dist2D(Figure.From, ToVector(P, 0.0)) / Total, 0.0, 1.0) : 1.0;
        Figure.Position = ToVector(P, FMath::Lerp(Figure.From.Z, Figure.To.Z, Fraction));
        // A budgeted figure integrates the sweep it slept through, exactly as the crowd does.
        Figure.Phase = static_cast<float>(MikdashCrowd::AdvancePhase(Figure.Phase, Figure.Speed,
                                                                     MikdashCrowd::CatchUpSeconds(DeltaSeconds, Figures.Num(), Budget), false));
        Figure.bVisible = 1;
        const bool bArrived = T >= Figure.ArriveAt || Fraction >= 1.0 - 1e-9;
        if (!bArrived) { Render(Index, /*bStanding*/ false); continue; }

        if (!Figure.bAlighting)
        {
            // Through the door. If the doors have somehow already closed, this is an overrun.
            if (Group.bHasExchange && !Transit->IsPassengerExchangeOpen(Group.Exchange)) ++Overruns;
            else ++PeopleBoarded;
            FinishFigure(Index);
            continue;
        }
        // Alighter arrived: photographers turn to the Mount; walkers wait for their companions.
        Figure.bHolding = 1;
        Figure.Position = Figure.To;
        Figure.Yaw = Figure.bPhotographer
            ? static_cast<float>(YawToward(ToVec2(Figure.Position), ToVec2(MountFocusCm)))
            : Figure.Yaw;
        Render(Index, /*bStanding*/ true);
        if (!Figure.bPhotographer)
        {
            ++Group.WalkersArrived;
            if (Group.WalkersArrived >= Group.WalkersTotal) HandOverWalkers(Figure.Group);
        }
    }

    for (UHierarchicalInstancedStaticMeshComponent* Component : TouchedThisFrame)
    {
        if (Component) Component->MarkRenderStateDirty();
    }
}

void AMikdashTransitBoardingBridge::HandOverWalkers(int32 GroupIndex)
{
    if (!Groups.IsValidIndex(GroupIndex)) return;
    FMikdashBoardingGroup& Group = Groups[GroupIndex];
    TArray<int32> Held;
    FVector Centroid = FVector::ZeroVector;
    for (int32 Index = 0; Index < Figures.Num(); ++Index)
    {
        const FMikdashBoardingFigure& Figure = Figures[Index];
        if (Figure.bActive && Figure.Group == GroupIndex && Figure.bAlighting && Figure.bHolding && !Figure.bPhotographer)
        {
            Held.Add(Index);
            Centroid += Figure.Position;
        }
    }
    if (Held.IsEmpty()) return;
    Centroid /= static_cast<double>(Held.Num());
    if (CrowdHost)
    {
        // The whole party at once, or nothing: the crowd refuses atomically and these figures
        // then simply leave, exactly as they do when no host exists.
        FMikdashCrowdPartyRequest Request;
        Request.AnchorCm = Centroid; Request.Count = Held.Num(); Request.Seed = static_cast<int32>(Group.Seed);
        Request.OutwardDirection = (Centroid - Group.Exchange.BoardingPoint).GetSafeNormal2D();
        Request.SecondsAvailable = static_cast<float>(FMath::Max(0.0, Group.StartAt + Group.Exchange.SecondsAvailable - Now()));
        Request.GlobalStopIndex = Group.Exchange.GlobalStopIndex;
        TArray<int32> Adopted;
        CrowdHost->TryAdoptParty(Request, Adopted);
    }
    for (int32 Index : Held)
    {
        ++PeopleAlighted;
        FinishFigure(Index);
    }
}

void AMikdashTransitBoardingBridge::FinishFigure(int32 FigureIndex)
{
    if (!Figures.IsValidIndex(FigureIndex)) return;
    FMikdashBoardingFigure& Figure = Figures[FigureIndex];
    const int32 GroupIndex = Figure.Group;
    Hide(FigureIndex);
    Figure.bActive = 0; Figure.bVisible = 0; Figure.bHolding = 0; Figure.bPhotographer = 0;
    Figure.Group = INDEX_NONE;
    if (Groups.IsValidIndex(GroupIndex) && Groups[GroupIndex].bActive)
    {
        if (--Groups[GroupIndex].Remaining <= 0) RetireGroup(GroupIndex);
    }
}

void AMikdashTransitBoardingBridge::RetireGroup(int32 GroupIndex)
{
    if (!Groups.IsValidIndex(GroupIndex)) return;
    Groups[GroupIndex].bActive = false;
    Groups[GroupIndex].Remaining = 0;
}

// ---------------------------------------------------------------------------
// Drawing
// ---------------------------------------------------------------------------

void AMikdashTransitBoardingBridge::Render(int32 FigureIndex, bool bStanding)
{
    const FMikdashBoardingFigure& Figure = Figures[FigureIndex];
    if (ActivePoseCount <= 0 || !PoseComponents.IsValidIndex(Figure.Pose)) return;
    UHierarchicalInstancedStaticMeshComponent* Walk = PoseComponents[Figure.Pose];
    const int32 WalkLocal = FigureIndex / ActivePoseCount;
    const bool bUsePhotoPose = Figure.bPhotographer && Figure.bHolding && PhotographerPoseMesh && PhotoComponent->GetInstanceCount() > FigureIndex;

    const double Bob = bStanding ? 0.0 : MikdashCrowd::BobHeightCm(Figure.Phase, BobAmplitudeCm);
    const double Lean = bStanding ? 0.0 : MikdashCrowd::LeanDegrees(Figure.Phase, LeanAmplitudeDegrees);
    const FTransform Transform(FRotator(0.0, Figure.Yaw, Lean), Figure.Position + FVector(0, 0, Bob * Figure.Scale), FVector(Figure.Scale));

    if (Walk->GetInstanceCount() > WalkLocal)
    {
        Walk->UpdateInstanceTransform(WalkLocal, bUsePhotoPose ? HiddenTransform() : Transform, /*bWorldSpace*/ true, /*bMarkRenderStateDirty*/ false, /*bTeleport*/ true);
        Walk->SetCustomDataValue(WalkLocal, 0, Figure.Phase, false);
        Walk->SetCustomDataValue(WalkLocal, 1, Figure.Tint, false);
        Walk->SetCustomDataValue(WalkLocal, 2, bStanding ? 1.f : 0.f, false);
        TouchedThisFrame.Add(Walk);
    }
    if (PhotographerPoseMesh && PhotoComponent->GetInstanceCount() > FigureIndex)
    {
        PhotoComponent->UpdateInstanceTransform(FigureIndex, bUsePhotoPose ? Transform : HiddenTransform(), true, false, true);
        PhotoComponent->SetCustomDataValue(FigureIndex, 0, Figure.Phase, false);
        PhotoComponent->SetCustomDataValue(FigureIndex, 1, Figure.Tint, false);
        PhotoComponent->SetCustomDataValue(FigureIndex, 2, 1.f, false);
        TouchedThisFrame.Add(PhotoComponent.Get());
    }
}

void AMikdashTransitBoardingBridge::Hide(int32 FigureIndex)
{
    const FMikdashBoardingFigure& Figure = Figures[FigureIndex];
    if (ActivePoseCount > 0 && PoseComponents.IsValidIndex(Figure.Pose))
    {
        UHierarchicalInstancedStaticMeshComponent* Walk = PoseComponents[Figure.Pose];
        const int32 WalkLocal = FigureIndex / ActivePoseCount;
        if (Walk->GetInstanceCount() > WalkLocal)
        {
            Walk->UpdateInstanceTransform(WalkLocal, HiddenTransform(), true, false, true);
            TouchedThisFrame.Add(Walk);
        }
    }
    if (PhotographerPoseMesh && PhotoComponent->GetInstanceCount() > FigureIndex)
    {
        PhotoComponent->UpdateInstanceTransform(FigureIndex, HiddenTransform(), true, false, true);
        TouchedThisFrame.Add(PhotoComponent.Get());
    }
}

// ---------------------------------------------------------------------------

FString AMikdashTransitBoardingBridge::GetBridgeSummary() const
{
    return FString::Printf(TEXT("bridge %s; groups active=%d cap=%d started=%d refused(cap=%d geometry=%d stop=%d pool=%d); figures active=%d of %d; boarded=%d alighted=%d trimmed=%d photographers=%d overruns=%d groundMisses=%d; crowdHandover=%s; instanced apron figures, not the crowd field's own instances and not resident AI"),
                           bRunning ? TEXT("active") : TEXT("inactive"), GetActiveGroupCount(), MaxConcurrentGroups, GroupsStarted,
                           GroupsRefusedCap, GroupsRefusedGeometry, GroupsRefusedStop, GroupsRefusedPool,
                           GetActiveFigureCount(), Figures.Num(), PeopleBoarded, PeopleAlighted, PeopleTrimmed, Photographers, Overruns, GroundMisses,
                           CrowdHost ? TEXT("yes") : TEXT("no"));
}
