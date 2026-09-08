#include "MikdashCrowdField.h"

#include "CrowdFieldMath.h"
#include "MikdashSceneUnits.h"
#include "PopulationSceneMath.h"

#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInterface.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

namespace
{
using MikdashCrowd::Vec2;

FORCEINLINE Vec2 ToVec2(const FVector2D& V) { return Vec2{static_cast<double>(V.X), static_cast<double>(V.Y)}; }
FORCEINLINE FVector2D ToFVector2D(const Vec2& V) { return FVector2D(static_cast<FVector2D::FReal>(V.X), static_cast<FVector2D::FReal>(V.Y)); }

MikdashCrowd::FlowZone MakeFlowZone(const FMikdashCrowdZone& Zone)
{
    MikdashCrowd::FlowZone Flow;
    Flow.Goal = ToVec2(Zone.GoalCm);
    Flow.DirectionDegrees = Zone.FlowDirectionDegrees;
    Flow.GoalWeight = Zone.GoalWeight;
    Flow.SwirlDegrees = Zone.SwirlDegrees;
    Flow.MeanderDegrees = Zone.MeanderDegrees;
    Flow.MeanderHz = Zone.MeanderHz;
    return Flow;
}

/** Scale given to an instance whose seed was refused. It is kept in the array so that the
 * global instance index stays aligned with the agent index (the pose blocking depends on it),
 * but it is small enough to be invisible. Refusals are counted, never hidden. */
constexpr float RefusedInstanceScale = 0.0001f;
constexpr int32 SeedAttempts = 48;
}   // namespace

AMikdashCrowdField::AMikdashCrowdField()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = false;   // nothing ticks until BuildCrowd succeeds
    PrimaryActorTick.TickGroup = TG_PrePhysics;

    USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    SetRootComponent(Root);

    PoseComponents.Reserve(MaxPoseComponents);
    for (int32 Index = 0; Index < MaxPoseComponents; ++Index)
    {
        const FName ComponentName(*FString::Printf(TEXT("CrowdPose%d"), Index));
        UHierarchicalInstancedStaticMeshComponent* Component = CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(ComponentName);
        Component->SetupAttachment(Root);
        Component->SetMobility(EComponentMobility::Movable);   // required: instance transforms are rewritten every frame
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Component->SetCollisionProfileName(TEXT("NoCollision"));
        Component->SetGenerateOverlapEvents(false);
        Component->SetCastShadow(false);
        Component->NumCustomDataFloats = 3;   // 0 gait phase offset, 1 garment tint, 2 standing flag
        PoseComponents.Add(Component);
    }
    SetActorEnableCollision(false);
}

int32 AMikdashCrowdField::ParseCrowdCountSwitch(int32 Fallback)
{
    int32 Parsed = 0;
    if (FParse::Value(FCommandLine::Get(), TEXT("CrowdCount="), Parsed) && Parsed >= 0)
    {
        return FMath::Min(Parsed, 60000);
    }
    return Fallback;
}

int32 AMikdashCrowdField::GetEffectiveCrowdCount() const
{
    return ParseCrowdCountSwitch(FMath::Clamp(CrowdCount, 0, 60000));
}

int32 AMikdashCrowdField::GetTotalInstanceCount() const
{
    int32 Total = 0;
    for (const TObjectPtr<UHierarchicalInstancedStaticMeshComponent>& Component : PoseComponents)
    {
        if (Component)
        {
            Total += Component->GetInstanceCount();
        }
    }
    return Total;
}

int32 AMikdashCrowdField::GetFramesPerSweep() const
{
    return MikdashCrowd::FramesPerSweep(Agents.Num(), FMath::Max(1, UpdateBudgetPerFrame));
}

FString AMikdashCrowdField::GetCrowdSummary() const
{
    return FString::Printf(TEXT("%d instances in %d zones across %d pose meshes; %d seeded, %d refused, %d ground-trace misses, %d re-seed fallbacks; %d updates a frame = one sweep every %d frames"),
                           GetTotalInstanceCount(), RuntimeZones.Num(), ActivePoseCount, SeededAgents, RefusedSeeds, GroundTraceMisses,
                           ReseedFallbacks, FMath::Max(1, UpdateBudgetPerFrame), GetFramesPerSweep());
}

bool AMikdashCrowdField::GetRuntimeZone(const FString& Name, FMikdashCrowdZone& Zone) const
{
    for(const auto& Candidate:RuntimeZones) if(Candidate.Name==Name) { Zone=Candidate; return true; }
    return false;
}

bool AMikdashCrowdField::GetRuntimeKeepOut(const FString& Name, FMikdashCrowdKeepOut& KeepOut) const
{
    for(const auto& Candidate:RuntimeProtectedPolygons) if(Candidate.Name==Name) { KeepOut=Candidate; return true; }
    return false;
}

bool AMikdashCrowdField::PrepareRuntimeGeometry()
{
    RuntimeZones.Reset(); RuntimeProtectedPolygons.Reset();
    MikdashSceneUnits::Frame Frame;
    if (!AMikdashSceneUnits::Resolve(GetWorld(),Frame,CoordinateStatus)) return false;
    if (SourceCoordinateRevision != TEXT("Legacy50.v1"))
    { CoordinateStatus=TEXT("Refused: crowd property coordinate revision is not legacy50 input"); return false; }
    TArray<FMikdashCrowdZone> CandidateZones=Zones;
    TArray<FMikdashCrowdKeepOut> CandidateProtected=ProtectedPolygons;
    if (Frame.CoordinateRevision==MikdashSceneUnits::Revision::Selected48V1)
    {
        const auto ConvertXY=[this,&Frame](FVector2D& Point)
        {
            MikdashUnits::PointCm Result;
            if (!MikdashSceneUnits::TryLegacyTemplePoint(Frame,{Point.X,Point.Y,0},Result))
            { CoordinateStatus=TEXT("Refused: non-finite crowd coordinate or conversion overflow");return false; }
            Point=FVector2D(Result.X,Result.Y); return true;
        };
        for (FMikdashCrowdZone& Zone : CandidateZones)
        {
            const auto Scope=MikdashPopulationScene::CrowdZoneScope(TCHAR_TO_UTF8(*Zone.Name));
            if(Scope==MikdashPopulationScene::Scope::Unknown)
            { CoordinateStatus=TEXT("Refused: unclassified crowd zone ")+Zone.Name; return false; }
            if(Scope==MikdashPopulationScene::Scope::Metric) continue;
            const double ExpectedFloor=Zone.Name==TEXT("OuterCourtEast") ? 300.0 : 425.0;
            if(Zone.GroundMode!=EMikdashCrowdGround::Flat || !MikdashPopulationScene::Near(Zone.GroundZBase,ExpectedFloor)
                || !FMath::IsNearlyZero(Zone.GroundSlopeX) || !FMath::IsNearlyZero(Zone.GroundSlopeY))
            { CoordinateStatus=TEXT("Refused: Temple zone is not the reviewed legacy support: ")+Zone.Name; return false; }
            for(FVector2D& Point:Zone.PolygonCm) if(!ConvertXY(Point)) return false;
            if(!ConvertXY(Zone.GoalCm) || !ConvertXY(Zone.ReseedEdgeA) || !ConvertXY(Zone.ReseedEdgeB)) return false;
            MikdashUnits::PointCm Support;
            if(!MikdashSceneUnits::TryLegacyTemplePoint(Frame,{0,0,ExpectedFloor},Support)) return false;
            Zone.GroundZBase=static_cast<float>(Support.Z);
        }
        for(FMikdashCrowdKeepOut& KeepOut:CandidateProtected)
        {
            if(KeepOut.Name==TEXT("KotelWallSlab")) continue;
            MikdashPopulationScene::PaddedFootprint Footprint;
            if(!MikdashPopulationScene::Footprint(TCHAR_TO_UTF8(*KeepOut.Name),Footprint))
            { CoordinateStatus=TEXT("Refused: unclassified keep-out ")+KeepOut.Name; return false; }
            std::vector<MikdashRoute::Point2> Input;
            for(const auto& P:KeepOut.PolygonCm) Input.push_back({P.X,P.Y});
            const auto LegacyBounds=MikdashPopulationScene::Padded(Footprint);
            MikdashPopulationScene::Rect Converted;
            if(!MikdashPopulationScene::IsRect(Input,LegacyBounds)
                || !MikdashPopulationScene::TryFootprint(Frame,Footprint,Converted))
            { CoordinateStatus=TEXT("Refused: keep-out no longer matches its legacy source footprint/pads: ")+KeepOut.Name; return false; }
            // Keep original corner order, while reconstructing unscaled clearance pads.
            for(FVector2D& P:KeepOut.PolygonCm)
            {
                P.X=MikdashPopulationScene::Near(P.X,LegacyBounds.MinX)?Converted.MinX:Converted.MaxX;
                P.Y=MikdashPopulationScene::Near(P.Y,LegacyBounds.MinY)?Converted.MinY:Converted.MaxY;
            }
        }
    }
    RuntimeZones=MoveTemp(CandidateZones);RuntimeProtectedPolygons=MoveTemp(CandidateProtected);
    CoordinateStatus=Frame.CoordinateRevision==MikdashSceneUnits::Revision::Selected48V1
        ? TEXT("Selected48 runtime geometry from immutable legacy50 properties; geographic context and physical padding retained")
        : TEXT("Legacy50 runtime geometry unchanged");
    return true;
}

void AMikdashCrowdField::CacheGeometry()
{
    using MikdashCrowd::Vec2;
    KeepOutPointCache.Reset();
    KeepOutStartCache.Reset();
    KeepOutCountCache.Reset();
    for (const FMikdashCrowdKeepOut& Polygon : RuntimeProtectedPolygons)
    {
        if (Polygon.PolygonCm.Num() < 3)
        {
            continue;   // a degenerate keep-out protects nothing; dropping it is honest, treating it as valid is not
        }
        KeepOutStartCache.Add(KeepOutPointCache.Num());
        KeepOutCountCache.Add(Polygon.PolygonCm.Num());
        for (const FVector2D& Point : Polygon.PolygonCm)
        {
            KeepOutPointCache.Add(ToVec2(Point));
        }
    }

    ZonePointCache.Reset();
    ZoneStartCache.Reset();
    ZoneVertexCountCache.Reset();
    ZoneFlowCache.Reset();
    for (const FMikdashCrowdZone& Zone : RuntimeZones)
    {
        ZoneStartCache.Add(ZonePointCache.Num());
        ZoneVertexCountCache.Add(Zone.PolygonCm.Num());
        ZoneFlowCache.Add(MakeFlowZone(Zone));
        for (const FVector2D& Point : Zone.PolygonCm)
        {
            ZonePointCache.Add(ToVec2(Point));
        }
    }
}

void AMikdashCrowdField::ConfigureComponents()
{
    ActivePoseCount = 0;
    for (int32 Index = 0; Index < PoseComponents.Num(); ++Index)
    {
        UHierarchicalInstancedStaticMeshComponent* Component = PoseComponents[Index];
        if (!Component)
        {
            continue;
        }
        UStaticMesh* Mesh = PoseMeshes.IsValidIndex(Index) ? PoseMeshes[Index].Get() : nullptr;
        Component->SetStaticMesh(Mesh);
        Component->NumCustomDataFloats = 3;
        Component->SetCastShadow(bCastShadows);
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        // The renderer's own distance policy: instances fade out between the two and are not
        // drawn past the end. This is separate from FreezeDistanceCm, which is about CPU.
        Component->InstanceStartCullDistance = FMath::Max(0, InstanceStartCullDistanceCm);
        Component->InstanceEndCullDistance = FMath::Max(Component->InstanceStartCullDistance, InstanceEndCullDistanceCm);
        if (Mesh)
        {
            if (CrowdMaterialOverride)
            {
                const int32 Slots = Component->GetNumMaterials();
                for (int32 Slot = 0; Slot < Slots; ++Slot)
                {
                    Component->SetMaterial(Slot, CrowdMaterialOverride);
                }
            }
            ++ActivePoseCount;
        }
    }
}

float AMikdashCrowdField::ZoneGroundZ(const FMikdashCrowdZone& Zone, const FVector2D& P) const
{
    if (Zone.GroundMode == EMikdashCrowdGround::Plane)
    {
        return Zone.GroundZBase + Zone.GroundSlopeX * static_cast<float>(P.X) + Zone.GroundSlopeY * static_cast<float>(P.Y);
    }
    return Zone.GroundZBase;
}

float AMikdashCrowdField::ResolveGroundZ(const FMikdashCrowdZone& Zone, const FVector2D& P)
{
    const float Fallback = ZoneGroundZ(Zone, P);
    if (!bTraceGroundOnSeed)
    {
        return Fallback;
    }
    UWorld* World = GetWorld();
    if (!World)
    {
        return Fallback;
    }
    const FVector Start(P.X, P.Y, Fallback + GroundTraceStartOffsetCm);
    const FVector End(P.X, P.Y, Fallback - GroundTraceDepthCm);
    FHitResult Hit;
    FCollisionQueryParams Params(TEXT("MikdashCrowdGround"), false, this);
    if (World->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params))
    {
        const float HitZ = static_cast<float>(Hit.ImpactPoint.Z);
        // A hit far from the authored ground is a roof, a passing actor or a stray prop, not
        // the floor this zone was authored against. Prefer the authored number and say so.
        if (FMath::Abs(HitZ - Fallback) <= GroundTraceMaxDeviationCm)
        {
            return HitZ;
        }
    }
    ++GroundTraceMisses;
    return Fallback;
}

FVector2D AMikdashCrowdField::ResolveReseedPoint(const FMikdashCrowdZone& Zone, const MikdashCrowd::Vec2* ZonePolygon, int32 ZoneVertices,
                                                 int32 GlobalIndex, const FVector2D& Fallback)
{
    using namespace MikdashCrowd;
    // Start at a deterministic place along the segment, so the zone does not fountain every
    // returning figure out of one spot, then walk along it until a legal point is found. A
    // segment that crosses a keep-out (a gate corridor, say) is therefore usable for the
    // stretches of it that are clear, instead of being all or nothing.
    const int32 Samples = 24;
    const double Offset = HashUnit(static_cast<uint32>(RandomSeed), static_cast<uint32>(GlobalIndex), 211u);
    const Vec2* KeepOutPtr = KeepOutPointCache.Num() > 0 ? KeepOutPointCache.GetData() : nullptr;
    const int32 KeepOutCount = KeepOutCountCache.Num();
    const int32* KeepOutStartsPtr = KeepOutCount > 0 ? KeepOutStartCache.GetData() : nullptr;
    const int32* KeepOutCountsPtr = KeepOutCount > 0 ? KeepOutCountCache.GetData() : nullptr;
    for (int32 Attempt = 0; Attempt < Samples; ++Attempt)
    {
        double T = Offset + static_cast<double>(Attempt) / Samples;
        T -= FMath::FloorToDouble(T);
        const FVector2D Candidate = FMath::Lerp(Zone.ReseedEdgeA, Zone.ReseedEdgeB, static_cast<FVector2D::FReal>(T));
        const Vec2 Point{static_cast<double>(Candidate.X), static_cast<double>(Candidate.Y)};
        if (!PointInPolygon(ZonePolygon, ZoneVertices, Point))
        {
            continue;
        }
        if (PointInAnyProtected(KeepOutPtr, KeepOutStartsPtr, KeepOutCountsPtr, KeepOutCount, Point, ProtectedMarginCm))
        {
            continue;
        }
        return Candidate;
    }
    // Nowhere on the segment is legal. Returning to its own start point is always safe: it was
    // rejection-sampled inside the zone and clear of every keep-out when the crowd was built.
    ++ReseedFallbacks;
    return Fallback;
}

FVector AMikdashCrowdField::ResolveViewLocation() const
{
    if (const UWorld* World = GetWorld())
    {
        if (APlayerController* Controller = World->GetFirstPlayerController())
        {
            FVector Location = FVector::ZeroVector;
            FRotator Rotation = FRotator::ZeroRotator;
            Controller->GetPlayerViewPoint(Location, Rotation);
            return Location;
        }
    }
    return GetActorLocation();
}

FTransform AMikdashCrowdField::TransformFor(const FMikdashCrowdAgent& Agent) const
{
    if (!Agent.bValid)
    {
        return FTransform(FRotator::ZeroRotator, FVector(Agent.Position.X, Agent.Position.Y, Agent.GroundZCm), FVector(RefusedInstanceScale));
    }
    // Bob and lean go into the transform rather than only into the material, so the crowd
    // still reads as walking if the crowd material fails to build or is overridden with a
    // plain one. They match MikdashCrowd::BobHeightCm / LeanDegrees exactly.
    const float Bob = static_cast<float>(MikdashCrowd::BobHeightCm(Agent.Phase, BobAmplitudeCm));
    const float Lean = static_cast<float>(MikdashCrowd::LeanDegrees(Agent.Phase, LeanAmplitudeDegrees));
    const FRotator Rotation(0.f, Agent.HeadingDegrees, Lean);
    const FVector Location(Agent.Position.X, Agent.Position.Y, Agent.GroundZCm + Bob * Agent.ScaleFactor);
    return FTransform(Rotation, Location, FVector(Agent.ScaleFactor));
}

void AMikdashCrowdField::PushTransforms(int32 GlobalStart, int32 GlobalCount)
{
    if (GlobalCount <= 0 || ActivePoseCount <= 0)
    {
        return;
    }
    const int32 Total = Agents.Num();
    int32 Cursor = GlobalStart;
    const int32 End = GlobalStart + GlobalCount;
    while (Cursor < End)
    {
        const int32 Pose = MikdashCrowd::PoseIndexForInstance(Cursor, Total, ActivePoseCount);
        const int32 BlockStart = MikdashCrowd::PoseBlockStart(Pose, Total, ActivePoseCount);
        const int32 BlockEnd = MikdashCrowd::PoseBlockStart(Pose + 1, Total, ActivePoseCount);
        const int32 RunEnd = FMath::Min(End, BlockEnd);
        const int32 RunCount = RunEnd - Cursor;
        if (RunCount <= 0)
        {
            break;   // defensive: a malformed block mapping must not spin here
        }
        UHierarchicalInstancedStaticMeshComponent* Component = PoseComponents.IsValidIndex(Pose) ? PoseComponents[Pose].Get() : nullptr;
        if (Component && Component->GetInstanceCount() >= RunEnd - BlockStart)
        {
            TransformScratch.Reset(RunCount);
            for (int32 Index = Cursor; Index < RunEnd; ++Index)
            {
                TransformScratch.Add(TransformFor(Agents[Index]));
            }
            Component->BatchUpdateInstancesTransforms(Cursor - BlockStart, TransformScratch, /*bWorldSpace*/ true,
                                                     /*bMarkRenderStateDirty*/ true, /*bTeleport*/ true);
        }
        Cursor = RunEnd;
    }
}

void AMikdashCrowdField::ClearCrowd()
{
    for (const TObjectPtr<UHierarchicalInstancedStaticMeshComponent>& Component : PoseComponents)
    {
        if (Component)
        {
            Component->ClearInstances();
        }
    }
    Agents.Reset();
    RuntimeZones.Reset(); RuntimeProtectedPolygons.Reset();
    ZoneCounts.Reset();
    SeededAgents = 0;
    RefusedSeeds = 0;
    GroundTraceMisses = 0;
    ReseedFallbacks = 0;
    UpdateCursor = 0;
    FrozenLastSweep = 0;
    CulledLastSweep = 0;
    FrozenThisSweep = 0;
    CulledThisSweep = 0;
    bCrowdRunning = false;
    SetActorTickEnabled(false);
}

void AMikdashCrowdField::BuildEditorPreview()
{
    BuildCrowd(FMath::Clamp(EditorPreviewCount, 0, 20000));
}

void AMikdashCrowdField::BuildCrowd(int32 OverrideCount)
{
    using namespace MikdashCrowd;

    ClearCrowd();
    if(!PrepareRuntimeGeometry())
    {
        UE_LOG(LogTemp,Warning,TEXT("%s: %s"),*GetName(),*CoordinateStatus);
        return;
    }
    ConfigureComponents();

    const int32 Total = OverrideCount >= 0 ? FMath::Min(OverrideCount, 60000) : GetEffectiveCrowdCount();
    if (Total <= 0 || RuntimeZones.Num() == 0 || ActivePoseCount <= 0)
    {
        // Nothing to refuse loudly here: an unconfigured actor is the normal state of a freshly
        // placed one. GetCrowdSummary reports zero instances.
        return;
    }

    CacheGeometry();
    const int32 KeepOutCount = KeepOutCountCache.Num();
    const Vec2* KeepOutPtr = KeepOutPointCache.Num() > 0 ? KeepOutPointCache.GetData() : nullptr;
    const int32* KeepOutStartsPtr = KeepOutCount > 0 ? KeepOutStartCache.GetData() : nullptr;
    const int32* KeepOutCountsPtr = KeepOutCount > 0 ? KeepOutCountCache.GetData() : nullptr;

    // Apportion by area * density, largest remainder, so the parts sum to exactly Total and
    // lowering Total thins every zone in proportion rather than emptying the far ones.
    TArray<double> Weights;
    Weights.Reserve(RuntimeZones.Num());
    for (int32 ZoneIndex = 0; ZoneIndex < RuntimeZones.Num(); ++ZoneIndex)
    {
        const double Area = PolygonArea(ZonePointCache.GetData() + ZoneStartCache[ZoneIndex], ZoneVertexCountCache[ZoneIndex]);
        Weights.Add(Area * FMath::Max(0.f, RuntimeZones[ZoneIndex].DensityPerHundredSqM) / 1.0e6);
    }
    ZoneCounts.SetNumZeroed(RuntimeZones.Num());
    ApportionCounts(Weights.GetData(), RuntimeZones.Num(), Total, ZoneCounts.GetData());

    Agents.SetNum(Total);
    const uint32 Seed = static_cast<uint32>(RandomSeed);
    const double MinSpeed = FMath::Max(0.f, MinWalkSpeedCmPerSecond);
    const double MaxSpeed = FMath::Max(static_cast<double>(MinWalkSpeedCmPerSecond), static_cast<double>(MaxWalkSpeedCmPerSecond));

    int32 GlobalIndex = 0;
    for (int32 ZoneIndex = 0; ZoneIndex < RuntimeZones.Num(); ++ZoneIndex)
    {
        const FMikdashCrowdZone& Zone = RuntimeZones[ZoneIndex];
        const Vec2* ZonePolygon = ZonePointCache.GetData() + ZoneStartCache[ZoneIndex];
        const int32 ZoneVertices = ZoneVertexCountCache[ZoneIndex];
        const FlowZone& Flow = ZoneFlowCache[ZoneIndex];
        const int32 ZoneTotal = ZoneCounts[ZoneIndex];
        for (int32 Local = 0; Local < ZoneTotal && GlobalIndex < Total; ++Local, ++GlobalIndex)
        {
            FMikdashCrowdAgent& Agent = Agents[GlobalIndex];
            Agent.ZoneIndex = ZoneIndex;
            Agent.ScaleFactor = static_cast<float>(HeightScaleFor(Seed, static_cast<uint32>(GlobalIndex), FigureScaleMin, FigureScaleMax));
            Vec2 Point{};
            const bool bSeeded = SeedPointInZone(ZonePolygon, ZoneVertices,
                                                 KeepOutPtr, KeepOutStartsPtr, KeepOutCountsPtr, KeepOutCount,
                                                 ProtectedMarginCm, Zone.EdgeMarginCm,
                                                 Seed, static_cast<uint32>(GlobalIndex), SeedAttempts, Point);
            if (!bSeeded)
            {
                // The zone is unusable for this instance (swallowed by a keep-out, or a
                // degenerate polygon). Refuse it rather than dropping a figure in the
                // sanctuary; it keeps its slot so the pose blocking stays aligned.
                Agent.bValid = 0;
                Agent.Position = Zone.PolygonCm.Num() > 0 ? Zone.PolygonCm[0] : FVector2D::ZeroVector;
                Agent.GroundZCm = ZoneGroundZ(Zone, Agent.Position);
                ++RefusedSeeds;
                continue;
            }
            Agent.bValid = 1;
            Agent.Position = ToFVector2D(Point);
            Agent.GroundZCm = ResolveGroundZ(Zone, Agent.Position);
            Agent.bStanding = IsStanding(Seed, static_cast<uint32>(GlobalIndex), Zone.StandingRatio) ? 1 : 0;
            Agent.SpeedCmPerSecond = Agent.bStanding ? 0.f : static_cast<float>(WalkSpeedFor(Seed, static_cast<uint32>(GlobalIndex), MinSpeed, MaxSpeed));
            Agent.Phase = static_cast<float>(HashUnit(Seed, static_cast<uint32>(GlobalIndex), 5u));
            Agent.HeadingDegrees = Agent.bStanding
                ? static_cast<float>(HashRange(Seed, static_cast<uint32>(GlobalIndex), 3u, -180.0, 180.0))
                : static_cast<float>(YawDegrees(SampleFlow(Flow, Point, 0.0, Seed, static_cast<uint32>(GlobalIndex))));
            Agent.ReseedPoint = ResolveReseedPoint(Zone, ZonePolygon, ZoneVertices, GlobalIndex, Agent.Position);
            ++SeededAgents;
        }
    }
    // Any tail left over (a zone list that apportioned fewer than Total because every weight
    // was zero) is refused rather than left uninitialised.
    for (; GlobalIndex < Total; ++GlobalIndex)
    {
        Agents[GlobalIndex].bValid = 0;
        ++RefusedSeeds;
    }

    // Add the instances, pose block by pose block, and set the static per-instance custom data.
    for (int32 Pose = 0; Pose < ActivePoseCount; ++Pose)
    {
        UHierarchicalInstancedStaticMeshComponent* Component = PoseComponents.IsValidIndex(Pose) ? PoseComponents[Pose].Get() : nullptr;
        if (!Component)
        {
            continue;
        }
        const int32 BlockStart = PoseBlockStart(Pose, Total, ActivePoseCount);
        const int32 BlockEnd = PoseBlockStart(Pose + 1, Total, ActivePoseCount);
        if (BlockEnd <= BlockStart)
        {
            continue;
        }
        TransformScratch.Reset(BlockEnd - BlockStart);
        for (int32 Index = BlockStart; Index < BlockEnd; ++Index)
        {
            TransformScratch.Add(TransformFor(Agents[Index]));
        }
        Component->AddInstances(TransformScratch, /*bShouldReturnIndices*/ false, /*bWorldSpace*/ true);
        for (int32 Index = BlockStart; Index < BlockEnd; ++Index)
        {
            const FMikdashCrowdAgent& Agent = Agents[Index];
            const int32 LocalIndex = Index - BlockStart;
            const float Tint = GarmentPaletteSize > 1
                ? static_cast<float>(GarmentIndex(Seed, static_cast<uint32>(Index), GarmentPaletteSize)) / static_cast<float>(GarmentPaletteSize - 1)
                : 0.f;
            // 0: gait phase offset, so the material can run its own sway without the CPU
            //    pushing new custom data every frame.
            // 1: garment tint, 0..1 across the palette.
            // 2: 1 for a standing figure, 0 for a walker.
            Component->SetCustomDataValue(LocalIndex, 0, Agent.Phase, /*bMarkRenderStateDirty*/ false);
            Component->SetCustomDataValue(LocalIndex, 1, Tint, /*bMarkRenderStateDirty*/ false);
            Component->SetCustomDataValue(LocalIndex, 2, Agent.bStanding ? 1.f : 0.f, /*bMarkRenderStateDirty*/ false);
        }
        Component->MarkRenderStateDirty();
    }

    UpdateCursor = 0;
    bCrowdRunning = Agents.Num() > 0;
    SetActorTickEnabled(bCrowdRunning && HasActorBegunPlay());
}

void AMikdashCrowdField::BeginPlay()
{
    Super::BeginPlay();
    if (!bActivateOnBeginPlay)
    {
        // Adopted opt-in, matching the rest of this plugin: placing the actor changes nothing
        // until a release script or a reviewer turns it on.
        return;
    }
    BuildCrowd(-1);
    SetActorTickEnabled(bCrowdRunning);
}

void AMikdashCrowdField::EndPlay(const EEndPlayReason::Type Reason)
{
    bCrowdRunning = false;
    SetActorTickEnabled(false);
    Super::EndPlay(Reason);
}

void AMikdashCrowdField::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);

    using namespace MikdashCrowd;
    const int32 Total = Agents.Num();
    if (!bCrowdRunning || Total <= 0 || ActivePoseCount <= 0)
    {
        return;
    }
    ElapsedSeconds += DeltaSeconds;

    const int32 Budget = FMath::Clamp(UpdateBudgetPerFrame, 1, Total);
    const UpdateWindow Window = NextUpdateWindow(UpdateCursor, Total, Budget);
    UpdateCursor = Window.NextCursor;
    if (Window.Total() <= 0)
    {
        return;
    }
    // Each visited agent integrates the whole sweep it slept through, clamped so a hitch
    // cannot teleport anybody across the court.
    const double Step_ = CatchUpSeconds(DeltaSeconds, Total, Budget);

    const int32 KeepOutCount = KeepOutCountCache.Num();
    const Vec2* KeepOutPtr = KeepOutPointCache.Num() > 0 ? KeepOutPointCache.GetData() : nullptr;
    const int32* KeepOutStartsPtr = KeepOutCount > 0 ? KeepOutStartCache.GetData() : nullptr;
    const int32* KeepOutCountsPtr = KeepOutCount > 0 ? KeepOutCountCache.GetData() : nullptr;

    const FVector ViewLocation = ResolveViewLocation();
    const Vec2 ViewXY{ViewLocation.X, ViewLocation.Y};

    if (Window.FirstStart == 0)
    {
        // A new sweep begins: publish the sweep that just finished and start counting again.
        FrozenLastSweep = FrozenThisSweep;
        CulledLastSweep = CulledThisSweep;
        FrozenThisSweep = 0;
        CulledThisSweep = 0;
    }

    const int32 SliceStarts[2] = {Window.FirstStart, Window.SecondStart};
    const int32 SliceCounts[2] = {Window.FirstCount, Window.SecondCount};
    for (int32 Slice = 0; Slice < 2; ++Slice)
    {
        const int32 Start = SliceStarts[Slice];
        const int32 Count = SliceCounts[Slice];
        for (int32 Index = Start; Index < Start + Count; ++Index)
        {
            FMikdashCrowdAgent& Agent = Agents[Index];
            if (!Agent.bValid || !RuntimeZones.IsValidIndex(Agent.ZoneIndex))
            {
                continue;
            }
            // Distance policy. Freezing and culling skip the simulation -- the flow sample, the
            // polygon tests and the re-seed trace, which is where the time goes. The unchanged
            // transform is still written as part of the contiguous batch below, which costs a
            // memcpy and keeps the batch to one call per pose block.
            const double Distance = FMath::Sqrt(DistanceSquared2D(ToVec2(Agent.Position), ViewXY));
            const InstanceWork Work = ClassifyByDistance(Distance, FreezeDistanceCm, CullDistanceCm);
            if (Work == InstanceWork::Cull)
            {
                ++CulledThisSweep;
                continue;
            }
            if (Work == InstanceWork::Freeze)
            {
                ++FrozenThisSweep;
                continue;
            }

            const FMikdashCrowdZone& Zone = RuntimeZones[Agent.ZoneIndex];
            const Vec2* ZonePolygon = ZonePointCache.GetData() + ZoneStartCache[Agent.ZoneIndex];
            const int32 ZoneVertices = ZoneVertexCountCache[Agent.ZoneIndex];
            const FlowZone& Flow = ZoneFlowCache[Agent.ZoneIndex];

            AgentState State;
            State.Position = ToVec2(Agent.Position);
            State.HeadingDegrees = Agent.HeadingDegrees;
            State.SpeedCmPerSecond = Agent.SpeedCmPerSecond;
            State.Phase = Agent.Phase;
            State.bStanding = Agent.bStanding != 0;

            Step(State, Flow, ZonePolygon, ZoneVertices,
                 KeepOutPtr, KeepOutStartsPtr, KeepOutCountsPtr, KeepOutCount, ProtectedMarginCm,
                 ToVec2(Agent.ReseedPoint), Step_, ElapsedSeconds, static_cast<uint32>(RandomSeed), static_cast<uint32>(Index),
                 MaxTurnDegreesPerSecond);

            Agent.Position = ToFVector2D(State.Position);
            Agent.HeadingDegrees = static_cast<float>(State.HeadingDegrees);
            Agent.Phase = static_cast<float>(State.Phase);
            if (State.bReseeded)
            {
                // Only a re-seed changes which patch of ground a figure is standing on badly
                // enough to be worth another trace; ordinary walking follows the zone surface.
                Agent.GroundZCm = ResolveGroundZ(Zone, Agent.Position);
            }
            else if (Zone.GroundMode == EMikdashCrowdGround::Plane)
            {
                // On a fitted slope the height has to follow the figure across the ground, or
                // it walks into the hill. This is the plane, not a trace: it costs two multiplies.
                Agent.GroundZCm = ZoneGroundZ(Zone, Agent.Position);
            }
        }
    }

    PushTransforms(Window.FirstStart, Window.FirstCount);
    PushTransforms(Window.SecondStart, Window.SecondCount);
}


bool AMikdashCrowdField::IsTransitSegmentAllowed(const FVector& From, const FVector& To, float RadiusCm) const
{
    if (From.ContainsNaN() || To.ContainsNaN() || !FMath::IsFinite(RadiusCm) || RadiusCm < 0 || RuntimeZones.IsEmpty()) return false;
    const double Distance = FVector::Dist2D(From, To);
    if (Distance > 5000.0) return false; // bounded authored transfer, never city-scale teleportation
    const int32 Steps = FMath::Max(1, FMath::CeilToInt(Distance / 25.0));
    const double Margin = RadiusCm + 13.0; // covers <=12.5cm gap to nearest segment sample
    for (int32 Step = 0; Step <= Steps; ++Step)
    {
        const FVector Sample = FMath::Lerp(From, To, static_cast<double>(Step) / Steps);
        const MikdashCrowd::Vec2 Point{Sample.X, Sample.Y};
        bool InZone = false;
        for (const FMikdashCrowdZone& Zone : RuntimeZones)
        {
            TArray<MikdashCrowd::Vec2> Polygon;
            for (const FVector2D& Vertex : Zone.PolygonCm) Polygon.Add({Vertex.X, Vertex.Y});
            if (MikdashCrowd::PointInPolygonWithMargin(Polygon.GetData(), Polygon.Num(), Point, Margin)) { InZone = true; break; }
        }
        if (!InZone) return false;
        for (const FMikdashCrowdKeepOut& KeepOut : RuntimeProtectedPolygons)
        {
            TArray<MikdashCrowd::Vec2> Polygon;
            for (const FVector2D& Vertex : KeepOut.PolygonCm) Polygon.Add({Vertex.X, Vertex.Y});
            if (MikdashCrowd::PointInPolygon(Polygon.GetData(), Polygon.Num(), Point)
                || MikdashCrowd::DistanceToPolygonEdge(Polygon.GetData(), Polygon.Num(), Point) <= FMath::Max(Margin, static_cast<double>(ProtectedMarginCm))) return false;
        }
    }
    return true;
}
