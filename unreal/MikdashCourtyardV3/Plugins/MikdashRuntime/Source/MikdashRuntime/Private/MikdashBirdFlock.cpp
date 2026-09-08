#include "MikdashBirdFlock.h"

#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "TimerManager.h"

using namespace MikdashFlock;

namespace
{
FVector ToUnreal(const Vec3& V) { return FVector(V.X, V.Y, V.Z); }
Vec3 ToFlock(const FVector& V) { return Vec3{V.X, V.Y, V.Z}; }

SpeciesId ToSpeciesId(EMikdashBirdSpecies Species)
{
    switch (Species)
    {
    case EMikdashBirdSpecies::CommonSwift:    return SpeciesId::CommonSwift;
    case EMikdashBirdSpecies::HoodedCrow:     return SpeciesId::HoodedCrow;
    case EMikdashBirdSpecies::CommonKestrel:  return SpeciesId::CommonKestrel;
    case EMikdashBirdSpecies::GriffonVulture: return SpeciesId::GriffonVulture;
    case EMikdashBirdSpecies::RockDove:
    default:                                  return SpeciesId::RockDove;
    }
}
}

AMikdashBirdFlock::AMikdashBirdFlock()
{
    // The flock is driven by a timer, never by Tick: a distant flock then costs literally
    // nothing on the game thread instead of costing an empty tick.
    PrimaryActorTick.bCanEverTick = false;
    PrimaryActorTick.bStartWithTickEnabled = false;

    USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("FlockRoot"));
    SetRootComponent(Root);
    Root->SetMobility(EComponentMobility::Static);

    static const TCHAR* PoseNames[PoseCount] = {TEXT("PoseUpStroke"), TEXT("PoseLevel"),
                                                TEXT("PoseDownStroke"), TEXT("PosePerched")};
    PoseComponents.Reserve(PoseCount);
    for (int32 I = 0; I < PoseCount; ++I)
    {
        UHierarchicalInstancedStaticMeshComponent* Component =
            CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(PoseNames[I]);
        Component->SetupAttachment(Root);
        Component->SetMobility(EComponentMobility::Movable);
        // Ambient birds are scenery only. Nothing may ever collide with, trace against or be
        // blocked by them - including the runtime-spawned player dove pawn.
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Component->SetCollisionProfileName(TEXT("NoCollision"));
        Component->SetGenerateOverlapEvents(false);
        Component->CanCharacterStepUpOn = ECB_No;
        Component->SetCastShadow(false);           // hundreds of tiny shadow casters, no benefit
        Component->bDisableCollision = true;
        Component->NumCustomDataFloats = 0;
        PoseComponents.Add(Component);
    }
}

void AMikdashBirdFlock::BeginPlay()
{
    Super::BeginPlay();
    RebuildFlock();
}

void AMikdashBirdFlock::EndPlay(const EEndPlayReason::Type Reason)
{
    if (UWorld* World = GetWorld())
    {
        World->GetTimerManager().ClearTimer(UpdateTimer);
    }
    bSimulating = false;
    Super::EndPlay(Reason);
}

#if WITH_EDITOR
void AMikdashBirdFlock::PostEditChangeProperty(FPropertyChangedEvent& Event)
{
    Super::PostEditChangeProperty(Event);
    if (GetWorld() && GetWorld()->IsGameWorld())
    {
        RebuildFlock();
    }
}
#endif

FName AMikdashBirdFlock::SpeciesName() const
{
    switch (Species)
    {
    case EMikdashBirdSpecies::CommonSwift:    return TEXT("CommonSwift");
    case EMikdashBirdSpecies::HoodedCrow:     return TEXT("HoodedCrow");
    case EMikdashBirdSpecies::CommonKestrel:  return TEXT("CommonKestrel");
    case EMikdashBirdSpecies::GriffonVulture: return TEXT("GriffonVulture");
    case EMikdashBirdSpecies::RockDove:
    default:                                  return TEXT("RockDove");
    }
}

FlockConfig AMikdashBirdFlock::MakeConfig() const
{
    FlockConfig Config;
    Config.Species = Profile(ToSpeciesId(Species));
    Config.Bounds.HomeCm = ToFlock(HomePointCm.IsNearlyZero() ? GetActorLocation() : HomePointCm);
    Config.Bounds.RadiusCm = FMath::Max(100.f, RadiusCm);
    Config.Bounds.FloorZCm = FloorZCm;
    Config.Bounds.CeilingZCm = CeilingZCm;
    Config.Bounds.SoftBandCm = FMath::Max(10.f, SoftBandCm);
    Config.Bounds.RadialSoftBandCm = FMath::Max(10.f, RadialSoftBandCm);
    Config.Seed = static_cast<uint32>(FlockSeed);
    return Config;
}

// ---------------------------------------------------------------------------------- perches
bool AMikdashBirdFlock::ResolvePerches()
{
    Perches.clear();
    TArray<FVector> Points = PerchPointsCm;
    int32 FromTags = 0;
    TArray<FString> TagReport;
    if (PerchActorTags.Num() > 0)
    {
        if (UWorld* World = GetWorld())
        {
            for (const FName& Tag : PerchActorTags)
            {
                int32 Found = 0;
                for (TActorIterator<AActor> It(World); It; ++It)
                {
                    AActor* Actor = *It;
                    if (!Actor || Actor == this || !Actor->ActorHasTag(Tag)) continue;
                    ++Found;
                    FVector Origin, Extent;
                    Actor->GetActorBounds(true, Origin, Extent);
                    if (Extent.IsNearlyZero()) continue;
                    // Spread points along the longer horizontal axis of the actor's bounds,
                    // just above its top: a wall top or a parapet reads as a line of ledges.
                    const bool bAlongX = Extent.X >= Extent.Y;
                    const double Half = bAlongX ? Extent.X : Extent.Y;
                    const int32 N = FMath::Clamp(PerchPointsPerTaggedActor, 1, 64);
                    for (int32 K = 0; K < N; ++K)
                    {
                        const double T = (N == 1) ? 0.0 : (-0.85 + 1.7 * K / static_cast<double>(N - 1));
                        FVector P = Origin;
                        (bAlongX ? P.X : P.Y) += T * Half;
                        P.Z = Origin.Z + Extent.Z + PerchLiftCm;
                        Points.Add(P);
                        ++FromTags;
                    }
                }
                TagReport.Add(FString::Printf(TEXT("%s:%d actors"), *Tag.ToString(), Found));
            }
        }
    }

    // Drop duplicates: two birds must never be able to occupy the same ledge point.
    const double MinimumSpacing = FMath::Max(30.0, Profile(ToSpeciesId(Species)).HardSeparationCm);
    int32 Dropped = 0;
    for (const FVector& P : Points)
    {
        bool bClash = false;
        for (const PerchPoint& Existing : Perches)
        {
            if (LengthSquared(Existing.Position - ToFlock(P)) < MinimumSpacing * MinimumSpacing)
            {
                bClash = true;
                break;
            }
        }
        if (bClash) { ++Dropped; continue; }
        PerchPoint Perch;
        Perch.Position = ToFlock(P);
        const FVector Home = HomePointCm.IsNearlyZero() ? GetActorLocation() : HomePointCm;
        Perch.Facing = Normalized(Vec3{P.X - Home.X, P.Y - Home.Y, 0.0});
        Perch.Occupant = -1;
        Perches.push_back(Perch);
    }

    PerchSourceStatus = FString::Printf(
        TEXT("%d perches (%d authored, %d from tags [%s], %d dropped as closer than %.0f cm)"),
        static_cast<int32>(Perches.size()), PerchPointsCm.Num(), FromTags,
        *FString::Join(TagReport, TEXT(", ")), Dropped, MinimumSpacing);
    return !Perches.empty();
}

// -------------------------------------------------------------------------------- rebuilding
bool AMikdashBirdFlock::RebuildFlock()
{
    UWorld* World = GetWorld();
    if (!World) { Status = TEXT("No world"); return false; }
    World->GetTimerManager().ClearTimer(UpdateTimer);
    bSimulating = false;
    Cursor = 0;
    SimulationTime = 0.0;
    NextCallTime = 0.0;
    AverageUpdateMs = 0.f;
    UpdateSamples = 0;

    for (UHierarchicalInstancedStaticMeshComponent* Component : PoseComponents)
    {
        if (Component)
        {
            Component->ClearInstances();
            Component->SetVisibility(false, true);
        }
    }
    Birds.clear();
    Perches.clear();
    CurrentPose.Reset();

    if (!bFlockEnabled)
    {
        Status = TEXT("Disabled: bFlockEnabled is false");
        return false;
    }
    const int32 Count = FMath::Clamp(BirdCount, 0, FMath::Max(1, MaxBirds));
    if (Count <= 0)
    {
        Status = TEXT("Inactive: BirdCount is zero");
        return false;
    }
    // A pose without a mesh falls back to the level mesh, so a partial import still flies.
    int32 MeshesAssigned = 0;
    UStaticMesh* Fallback = (PoseMeshes.Num() > Pose_Level) ? PoseMeshes[Pose_Level].Get() : nullptr;
    for (int32 I = 0; I < PoseComponents.Num(); ++I)
    {
        UStaticMesh* Mesh = (PoseMeshes.IsValidIndex(I) && PoseMeshes[I]) ? PoseMeshes[I].Get() : Fallback;
        if (!PoseComponents[I]) continue;
        PoseComponents[I]->SetStaticMesh(Mesh);
        // set_static_mesh style setters can report success misleadingly; read it back.
        if (PoseComponents[I]->GetStaticMesh() == Mesh && Mesh != nullptr) ++MeshesAssigned;
    }
    if (MeshesAssigned == 0)
    {
        Status = TEXT("Inactive: no pose meshes assigned (PoseMeshes is empty or failed readback)");
        return false;
    }

    const FlockConfig Config = MakeConfig();
    SeedFlock(Birds, Count, Config);
    ResolvePerches();

    CurrentPose.Init(Pose_Level, Count);
    RebuildInstances();

    ApplyTimer(NearUpdateIntervalSeconds);
    bSimulating = true;
    Status = FString::Printf(TEXT("Flying: %d %s, %d pose meshes, %s"),
                             Count, *SpeciesName().ToString(), MeshesAssigned, *PerchSourceStatus);
    return true;
}

void AMikdashBirdFlock::RebuildInstances()
{
    const FlockConfig Config = MakeConfig();
    const int32 Count = static_cast<int32>(Birds.size());
    for (int32 P = 0; P < PoseComponents.Num(); ++P)
    {
        UHierarchicalInstancedStaticMeshComponent* Component = PoseComponents[P];
        if (!Component) continue;
        TArray<FTransform> Transforms;
        Transforms.Reserve(Count);
        for (int32 I = 0; I < Count; ++I)
        {
            const Bird& B = Birds[static_cast<size_t>(I)];
            const int32 Pose = PoseFor(Config.Species, B);
            const bool bActive = (Pose == P);
            Transforms.Add(FTransform(
                FRotator(PitchDegrees(B.Velocity), YawDegrees(B.Velocity), 0.0),
                ToUnreal(B.Position),
                bActive ? FVector(SizeScale) : FVector::ZeroVector));
            if (P == 0) CurrentPose[I] = Pose;
        }
        Component->AddInstances(Transforms, /*bShouldReturnIndices*/ false, /*bWorldSpace*/ true);
        Component->SetVisibility(true, true);
    }
}

// ------------------------------------------------------------------------------- the update
void AMikdashBirdFlock::ApplyTimer(float IntervalSeconds)
{
    UWorld* World = GetWorld();
    if (!World) return;
    const float Interval = FMath::Max(0.016f, IntervalSeconds);
    if (FMath::IsNearlyEqual(Interval, CurrentInterval) && World->GetTimerManager().IsTimerActive(UpdateTimer))
    {
        return;
    }
    CurrentInterval = Interval;
    World->GetTimerManager().SetTimer(UpdateTimer, this, &AMikdashBirdFlock::UpdateFlock, Interval, true);
}

void AMikdashBirdFlock::StopSimulation(const FString& Reason)
{
    if (UWorld* World = GetWorld())
    {
        World->GetTimerManager().ClearTimer(UpdateTimer);
    }
    CurrentInterval = 0.f;
    bSimulating = false;
    for (UHierarchicalInstancedStaticMeshComponent* Component : PoseComponents)
    {
        if (Component) Component->SetVisibility(false, true);
    }
    Status = Reason;
}

float AMikdashBirdFlock::DistanceToNearestViewerCm() const
{
    const UWorld* World = GetWorld();
    if (!World) return TNumericLimits<float>::Max();
    const FVector Home = HomePointCm.IsNearlyZero() ? GetActorLocation() : HomePointCm;
    double Best = TNumericLimits<double>::Max();
    for (FConstPlayerControllerIterator It = World->GetPlayerControllerIterator(); It; ++It)
    {
        const APlayerController* Controller = It->Get();
        if (!Controller) continue;
        FVector Location = FVector::ZeroVector;
        FRotator Rotation = FRotator::ZeroRotator;
        Controller->GetPlayerViewPoint(Location, Rotation);
        Best = FMath::Min(Best, static_cast<double>(FVector::Dist(Location, Home)));
    }
    // No local viewer at all: treat as very far, so nothing simulates in a headless world.
    return Best == TNumericLimits<double>::Max() ? TNumericLimits<float>::Max() : static_cast<float>(Best);
}

void AMikdashBirdFlock::UpdateFlock()
{
    if (!bFlockEnabled || Birds.empty()) { StopSimulation(TEXT("Disabled")); return; }
    const double Started = FPlatformTime::Seconds();

    const float Distance = DistanceToNearestViewerCm();
    if (Distance > CullRadiusCm)
    {
        // Beyond the view radius: hide, and check again slowly. Nothing is simulated, so a
        // level full of flocks costs one cheap distance test each per second.
        for (UHierarchicalInstancedStaticMeshComponent* Component : PoseComponents)
        {
            if (Component && Component->IsVisible()) Component->SetVisibility(false, true);
        }
        bSimulating = false;
        Status = FString::Printf(TEXT("Dormant: nearest viewer %.0f cm beyond the %.0f cm cull radius"),
                                 Distance, CullRadiusCm);
        ApplyTimer(1.0f);
        return;
    }
    if (!bSimulating)
    {
        for (UHierarchicalInstancedStaticMeshComponent* Component : PoseComponents)
        {
            if (Component) Component->SetVisibility(true, true);
        }
        bSimulating = true;
    }
    const float Interval = (Distance < NearDistanceCm) ? NearUpdateIntervalSeconds
                          : (Distance < MidDistanceCm) ? MidUpdateIntervalSeconds
                                                       : FarUpdateIntervalSeconds;
    ApplyTimer(Interval);

    const FlockConfig Config = MakeConfig();
    const int32 Total = static_cast<int32>(Birds.size());
    const int32 Budget = (BirdsPerUpdate <= 0) ? Total : FMath::Min(BirdsPerUpdate, Total);
    const UpdateWindow Window = NextUpdateWindow(Cursor, Total, Budget);
    SimulationTime += CatchUpSeconds(CurrentInterval, Total, Budget) * Budget / FMath::Max(1, Total);

    const int32 PerchedBefore = PerchedCount(Birds);
    StepStats Stats = Update(Birds, Perches, Config, NeighbourGrid, OverlapGrid, Cursor, Budget,
                             CurrentInterval, SimulationTime, LastStartleOrigin);
    const int32 PerchedAfter = PerchedCount(Birds);

    // Write only the birds this update actually stepped. A bird that was not stepped did not
    // move except for an overlap nudge of a few centimetres, which lands on its own next
    // update; that is invisible and it halves the instance traffic.
    TArray<bool, TInlineAllocator<PoseCount>> Touched;
    Touched.Init(false, PoseCount);
    for (int32 K = 0; K < Window.Count; ++K)
    {
        const int32 I = (Window.Start + K) % Total;
        const Bird& B = Birds[static_cast<size_t>(I)];
        const int32 Pose = FMath::Clamp(PoseFor(Config.Species, B), 0, PoseCount - 1);
        const int32 Previous = CurrentPose.IsValidIndex(I) ? CurrentPose[I] : Pose;
        const FVector Location = ToUnreal(B.Position);
        const FRotator Rotation(PitchDegrees(B.Velocity), YawDegrees(B.Velocity),
                                B.Perched() ? 0.0 : RollDegrees(B.Velocity, B.Velocity, 30.0));
        if (Previous != Pose && PoseComponents.IsValidIndex(Previous) && PoseComponents[Previous])
        {
            PoseComponents[Previous]->UpdateInstanceTransform(
                I, FTransform(Rotation, Location, FVector::ZeroVector), true, false, true);
            Touched[Previous] = true;
        }
        if (PoseComponents.IsValidIndex(Pose) && PoseComponents[Pose])
        {
            PoseComponents[Pose]->UpdateInstanceTransform(
                I, FTransform(Rotation, Location, FVector(SizeScale)), true, false, true);
            Touched[Pose] = true;
        }
        if (CurrentPose.IsValidIndex(I)) CurrentPose[I] = Pose;
    }
    for (int32 P = 0; P < PoseComponents.Num(); ++P)
    {
        if (Touched.IsValidIndex(P) && Touched[P] && PoseComponents[P])
        {
            PoseComponents[P]->MarkRenderStateDirty();
        }
    }

    // ---- sound hook: rate-limited, and only for things that actually happened ----------
    if (bAnnounceBirdSounds)
    {
        const FVector Home = HomePointCm.IsNearlyZero() ? GetActorLocation() : HomePointCm;
        if (Stats.Launched >= 3 || (PerchedBefore - PerchedAfter) >= 3)
        {
            EmitBirdSound(TEXT("Wingburst"), Home, static_cast<float>(FMath::Max(Stats.Launched, PerchedBefore - PerchedAfter)));
        }
        if (Stats.Landed >= 3)
        {
            EmitBirdSound(TEXT("Land"), Home, static_cast<float>(Stats.Landed));
        }
        if (ShouldCall(Config.Seed, SimulationTime, Config.Species.CallMeanIntervalSeconds, NextCallTime))
        {
            // Attribute the call to an actual bird, so a spatialised source has somewhere to be.
            const int32 Index = static_cast<int32>(Hash(Config.Seed, static_cast<uint32>(SimulationTime), 55u) % static_cast<uint32>(Total));
            EmitBirdSound(TEXT("Call"), ToUnreal(Birds[static_cast<size_t>(Index)].Position), 1.f);
        }
    }

    const float Milliseconds = static_cast<float>((FPlatformTime::Seconds() - Started) * 1000.0);
    UpdateSamples = FMath::Min(UpdateSamples + 1, 64);
    AverageUpdateMs += (Milliseconds - AverageUpdateMs) / static_cast<float>(UpdateSamples);
    Status = FString::Printf(TEXT("Flying: %d %s, %d perched, %.0f cm to viewer, %.2f ms/update at %.0f Hz"),
                             Total, *SpeciesName().ToString(), PerchedAfter, Distance,
                             AverageUpdateMs, 1.f / FMath::Max(0.016f, CurrentInterval));
}

// ------------------------------------------------------------------------------- commands
void AMikdashBirdFlock::Startle(FVector OriginCm, float StartleRadiusCm)
{
    if (Birds.empty()) return;
    const FlockConfig Config = MakeConfig();
    LastStartleOrigin = ToFlock(OriginCm);
    const int32 Before = PerchedCount(Birds);
    ApplyStartle(Birds, Perches, Config, LastStartleOrigin, StartleRadiusCm, SimulationTime);
    int32 Affected = 0;
    const double R2 = static_cast<double>(StartleRadiusCm) * StartleRadiusCm;
    for (const Bird& B : Birds)
    {
        if (LengthSquared(B.Position - LastStartleOrigin) <= R2) ++Affected;
    }
    (void)Before;
    EmitBirdSound(TEXT("Startle"), OriginCm, static_cast<float>(Affected));
}

void AMikdashBirdFlock::SetFlockEnabled(bool bEnabled)
{
    if (bFlockEnabled == bEnabled) return;
    bFlockEnabled = bEnabled;
    if (bEnabled) { RebuildFlock(); }
    else { StopSimulation(TEXT("Disabled: SetFlockEnabled(false)")); }
}

void AMikdashBirdFlock::EmitBirdSound(FName EventName, FVector WorldLocationCm, float Intensity)
{
    if (!bAnnounceBirdSounds) return;
    OnBirdSound.Broadcast(EventName, SpeciesName(), WorldLocationCm, Intensity);
}

// --------------------------------------------------------------------------------- status
int32 AMikdashBirdFlock::GetPerchedBirdCount() const
{
    return PerchedCount(Birds);
}

float AMikdashBirdFlock::GetEstimatedMillisecondsPerFrame(float FramesPerSecond) const
{
    if (!bSimulating || CurrentInterval <= 0.f || FramesPerSecond <= 0.f) return 0.f;
    const float UpdatesPerSecond = 1.f / CurrentInterval;
    return AverageUpdateMs * UpdatesPerSecond / FramesPerSecond;
}

float AMikdashBirdFlock::GetWingPhaseCoherence() const
{
    return static_cast<float>(PhaseCoherence(Birds));
}
