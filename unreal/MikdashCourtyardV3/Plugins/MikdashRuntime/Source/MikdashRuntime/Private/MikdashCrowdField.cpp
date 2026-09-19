#include "MikdashCrowdField.h"

#include "CrowdFieldMath.h"
#include "MikdashSceneUnits.h"
#include "PopulationSceneMath.h"
#include "CrowdKotelGroundData.h"
#include "CrowdStreetGroundData.h"
#include "TimerManager.h"

#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/SceneComponent.h"
#include "CollisionQueryParams.h"
#include "CollisionShape.h"
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
// Native 10000-person validation needs a larger bounded search for whole cohorts.
// Ordinary non-social point seeding retains its original budget.
constexpr int32 SocialSeedAttempts = 1024;
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

int32 AMikdashCrowdField::GetVatWalkingCount() const
{
    if (!bUseVertexAnimation) return 0;
    int32 Walking = 0;
    for (const FMikdashCrowdAgent& Agent : Agents)
    {
        if (Agent.bValid && !Agent.bIdleAnim) ++Walking;
    }
    return Walking;
}

bool AMikdashCrowdField::GetVatAgentState(int32 AgentIndex, FVector& AnchorLocation, FVector& Velocity, float& WalkCyclesPerSecond,
                                          float& Scale, bool& bIdle) const
{
    AnchorLocation = FVector::ZeroVector; Velocity = FVector::ZeroVector; WalkCyclesPerSecond = 0.f; Scale = 1.f; bIdle = true;
    if (!bUseVertexAnimation || !Agents.IsValidIndex(AgentIndex) || !Agents[AgentIndex].bValid) return false;
    const FMikdashCrowdAgent& Agent = Agents[AgentIndex];
    AnchorLocation = FVector(Agent.Position.X, Agent.Position.Y, Agent.GroundZCm);
    Velocity = FVector(Agent.Velocity.X, Agent.Velocity.Y, Agent.VelocityZ);
    WalkCyclesPerSecond = Agent.WalkRate;
    Scale = Agent.ScaleFactor;
    bIdle = Agent.bIdleAnim != 0;
    return true;
}

FString AMikdashCrowdField::GetCrowdSummary() const
{
    const FString Vat = bUseVertexAnimation
        ? FString::Printf(TEXT("; vertex animation ON: %d walking, %d idle-or-standing, %d paused groups resumed"),
                          GetVatWalkingCount(), SeededAgents - GetVatWalkingCount(), ResumedVisitorGroups)
        : FString(TEXT("; vertex animation off (frozen posed meshes)"));
    return FString::Printf(TEXT("%d instances in %d zones across %d pose meshes; %d seeded, %d refused, %d ground-trace misses, %d re-seed fallbacks; %d updates a frame = one sweep every %d frames; %d visitors in %d groups, %d individuals; last frame %d obstacle sweeps, %d rejected moves, %d waiting visits"),
                           GetTotalInstanceCount(), RuntimeZones.Num(), ActivePoseCount, SeededAgents, RefusedSeeds, GroundTraceMisses,
                           ReseedFallbacks, FMath::Max(1, UpdateBudgetPerFrame), GetFramesPerSweep(),GroupedVisitors,VisitorGroups.Num(),
                           IndividualVisitors,GroupSweepsLastFrame,GroupRejectedMovesLastFrame,GroupWaitVisitsLastFrame) + Vat;
}

bool AMikdashCrowdField::GetVisitorSocialState(int32 AgentIndex,int32& GroupIdentity,int32& MemberIndex,FVector& Location,bool& Standing) const
{
    GroupIdentity=INDEX_NONE;MemberIndex=0;Location=FVector::ZeroVector;Standing=false;
    if(!Agents.IsValidIndex(AgentIndex)||!Agents[AgentIndex].bValid) return false;
    const auto& Agent=Agents[AgentIndex];MemberIndex=Agent.GroupMember;Standing=Agent.bStanding!=0;
    Location=FVector(Agent.Position.X,Agent.Position.Y,Agent.GroundZCm);
    if(VisitorGroups.IsValidIndex(Agent.GroupIndex)) GroupIdentity=static_cast<int32>(VisitorGroups[Agent.GroupIndex].Cohort.Identity);
    return true;
}

FString AMikdashCrowdField::GetVisitorGroupState(int32 GroupIdentity) const
{
    if(!Agents.IsValidIndex(GroupIdentity)) return TEXT("Unavailable");
    const int32 Index=Agents[GroupIdentity].GroupIndex;
    if(!VisitorGroups.IsValidIndex(Index)||VisitorGroups[Index].Cohort.Identity!=static_cast<uint32>(GroupIdentity)) return TEXT("Unavailable");
    switch(VisitorGroups[Index].Travel.Mode)
    {
        case MikdashCrowdGroups::TravelMode::Forward:return TEXT("Forward");
        case MikdashCrowdGroups::TravelMode::Returning:return TEXT("Returning");
        case MikdashCrowdGroups::TravelMode::Paused:return TEXT("Paused");
    }
    return TEXT("Unavailable");
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
    bUseKotelGroundModel=false;
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
    const FString GroundMapPrefix=TEXT("/Game/MikdashV3/Amah48Candidate_20260908T144034771385Z/Maps/");
    const FString GroundMap=GetWorld()->GetOutermost()->GetName();
    FString GroundLeaf=GroundMap.RightChop(GroundMapPrefix.Len());
    if(GetWorld()->WorldType==EWorldType::PIE && GroundLeaf.StartsWith(TEXT("UEDPIE_")))
    {
        const int32 Separator=GroundLeaf.Find(TEXT("_"),ESearchCase::CaseSensitive,ESearchDir::FromStart,7);
        if(Separator!=INDEX_NONE) GroundLeaf=GroundLeaf.RightChop(Separator+1);
    }
    bUseKotelGroundModel=Frame.CoordinateRevision==MikdashSceneUnits::Revision::Selected48V1
        && GroundMap.StartsWith(GroundMapPrefix,ESearchCase::CaseSensitive) && GroundLeaf==TEXT("Walkthrough");
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
    bVatMotionHistory = bUseVertexAnimation && FParse::Param(FCommandLine::Get(), TEXT("MikdashCrowdMotionHistory"));
    TArray<TArray<UMaterialInterface*>> HistoryMaterials;
    HistoryMaterials.SetNum(PoseComponents.Num());
    if (bVatMotionHistory)
    {
        // Resolve the entire candidate before changing any component. A partial
        // material set cannot safely consume a different custom-data layout.
        for (int32 Pose = 0; Pose < PoseComponents.Num(); ++Pose)
        {
            UStaticMesh* Mesh = PoseMeshes.IsValidIndex(Pose) ? PoseMeshes[Pose].Get() : nullptr;
            if (!Mesh) continue;
            for (int32 Slot = 0; Slot < Mesh->GetStaticMaterials().Num(); ++Slot)
            {
                UMaterialInterface* Original = Mesh->GetMaterial(Slot);
                const FString Name = Original ? Original->GetName() : FString();
                const FString Path = FString::Printf(TEXT("/Game/MikdashV3/Runtime/CrowdVATV3/Materials/%s.%s"), *Name, *Name);
                UMaterialInterface* Candidate = Name.StartsWith(TEXT("MI_CrowdVAT2_"))
                    ? LoadObject<UMaterialInterface>(nullptr, *Path) : nullptr;
                if (!Candidate)
                {
                    UE_LOG(LogTemp, Error, TEXT("CrowdMotionHistoryV3 refused missing candidate pose=%d slot=%d path=%s"), Pose, Slot, *Path);
                    bVatMotionHistory = false;
                }
                HistoryMaterials[Pose].Add(Candidate);
            }
        }
    }
    VatPreviousAgents.Reset();
    VatHistoryUpdatedAt.Reset();
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
        Component->NumCustomDataFloats = bUseVertexAnimation
            ? (bVatMotionHistory ? VatHistoryCustomDataFloats : VatCustomDataFloats) : 3;
        Component->SetCastShadow(bCastShadows);
        if (bUseVertexAnimation)
        {
            // The VAT material lives on the mesh slots. Per-component overrides (the 8 Sep tint fix
            // left fifteen on every pose component) would replace it with a static material and
            // turn every figure back into a statue.
            Component->EmptyOverrideMaterials();
            if (bVatMotionHistory)
                for (int32 Slot = 0; Slot < HistoryMaterials[Index].Num(); ++Slot)
                    Component->SetMaterial(Slot, HistoryMaterials[Index][Slot]);
            // The distance field, Lumen card and ray-tracing geometry of a VAT mesh are its REST
            // pose; letting them light the scene would draw a ghost standing where the figure is not.
            Component->SetAffectDistanceFieldLighting(false);
            Component->SetAffectDynamicIndirectLighting(false);
            Component->SetVisibleInRayTracing(false);
        }
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        // The renderer's own distance policy: instances fade out between the two and are not
        // drawn past the end. This is separate from FreezeDistanceCm, which is about CPU.
        Component->InstanceStartCullDistance = FMath::Max(0, InstanceStartCullDistanceCm);
        Component->InstanceEndCullDistance = FMath::Max(Component->InstanceStartCullDistance, InstanceEndCullDistanceCm);
        if (Mesh)
        {
            if (CrowdMaterialOverride && !bUseVertexAnimation)
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
    if (bVatMotionHistory)
        UE_LOG(LogTemp, Display, TEXT("CrowdMotionHistoryV3 enabled customFloats=%d poses=%d"), VatHistoryCustomDataFloats, ActivePoseCount);
}

float AMikdashCrowdField::ZoneGroundZ(const FMikdashCrowdZone& Zone, const FVector2D& P) const
{
    if(bUseKotelGroundModel)
    {
        if(Zone.Name==TEXT("KotelPlazaStrip"))
            return static_cast<float>(MikdashCrowdGround::DeckHeight(CrowdKotelGroundData::Plaza,P.X,P.Y));
        if(Zone.Name==TEXT("KotelApproachCorridor"))
            return static_cast<float>(MikdashCrowdGround::TerrainHeight(CrowdKotelGroundData::Approach,P.X,P.Y));
        if(Zone.Name==TEXT("StreetBateiMahase"))
            return static_cast<float>(MikdashCrowdGround::TerrainHeight(CrowdStreetGroundData::Street,P.X,P.Y));
    }
    if (Zone.GroundMode == EMikdashCrowdGround::Plane)
    {
        return Zone.GroundZBase + Zone.GroundSlopeX * static_cast<float>(P.X) + Zone.GroundSlopeY * static_cast<float>(P.Y);
    }
    return Zone.GroundZBase;
}

float AMikdashCrowdField::ResolveGroundZ(const FMikdashCrowdZone& Zone, const FVector2D& P)
{
    const float Fallback = ZoneGroundZ(Zone, P);
    if(!FMath::IsFinite(Fallback)) { ++GroundTraceMisses;return Fallback; }
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
    const bool bHit = World->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params);
    // Opt-in diagnosis only: bounded per process, no extra traces or placement changes.
    if (FParse::Param(FCommandLine::Get(), TEXT("MikdashCrowdGroundAudit")))
    {
        static TMap<FString, int32> Samples;
        int32& Count = Samples.FindOrAdd(Zone.Name);
        if (Count < 32)
        {
            ++Count;
            UE_LOG(LogTemp, Display, TEXT("CrowdGroundAuditV1 zone=\"%s\" sample=%d x=%.6f y=%.6f expected=%.6f hit=%d actual=%.6f normalZ=%.6f actor=\"%s\" component=\"%s\""),
                *Zone.Name, Count, P.X, P.Y, Fallback, bHit ? 1 : 0, Hit.ImpactPoint.Z, Hit.ImpactNormal.Z,
                *GetPathNameSafe(Hit.GetActor()), *GetPathNameSafe(Hit.GetComponent()));
        }
    }
    if (bHit)
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
    if (bUseVertexAnimation)
    {
        // The baked clip carries its own pelvis bob and sway; the transform is the ANCHOR only.
        return FTransform(FRotator(0.f, Agent.HeadingDegrees + MeshYawOffsetDegrees, 0.f),
                          FVector(Agent.Position.X, Agent.Position.Y, Agent.GroundZCm), FVector(Agent.ScaleFactor));
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

double AMikdashCrowdField::VatNow() const
{
    const UWorld* World = GetWorld();
    return World ? World->GetTimeSeconds() : 0.0;
}

void AMikdashCrowdField::AppendVatCustomData(int32 Index, TArray<float>& Out) const
{
    // Layout: Scripts/create_crowd_vat_v2.spec.json customData.layout. M_CrowdVAT_V1 reads these by
    // index; changing one side without the other is exactly the bug the tint fix spent a day on.
    const FMikdashCrowdAgent& Agent = Agents[Index];
    const float Tint = GarmentPaletteSize > 1
        ? static_cast<float>(MikdashCrowd::GarmentIndex(static_cast<uint32>(RandomSeed), static_cast<uint32>(Index), GarmentPaletteSize))
            / static_cast<float>(GarmentPaletteSize - 1)
        : 0.f;
    Out.Add(Agent.WalkPhaseAtAnchor);                       // 0
    Out.Add(Tint);                                          // 1
    Out.Add(Agent.bIdleAnim ? 1.f : 0.f);                   // 2
    Out.Add(static_cast<float>(Agent.AnchorTime));          // 3
    Out.Add(Agent.WalkRate);                                // 4
    Out.Add(static_cast<float>(Agent.Velocity.X));          // 5
    Out.Add(static_cast<float>(Agent.Velocity.Y));          // 6
    Out.Add(Agent.VelocityZ);                               // 7
    Out.Add(static_cast<float>(Agent.SwitchTime));          // 8
    Out.Add(Agent.IdleOffset);                              // 9
    Out.Add(Agent.HorizonSeconds);                          // 10
    if (bVatMotionHistory)
    {
        const FMikdashCrowdAgent& Previous = VatPreviousAgents[Index];
        Out.Add(static_cast<float>(Previous.Position.X - Agent.Position.X)); // 11 world anchor offset
        Out.Add(static_cast<float>(Previous.Position.Y - Agent.Position.Y)); // 12
        Out.Add(Previous.GroundZCm - Agent.GroundZCm);                        // 13
        const float RelativeYaw = FMath::DegreesToRadians(Previous.HeadingDegrees - Agent.HeadingDegrees);
        Out.Add(FMath::Cos(RelativeYaw));                       // 14 previous basis in current local space
        Out.Add(FMath::Sin(RelativeYaw));                       // 15
        Out.Add(Previous.WalkPhaseAtAnchor);                    // 16
        Out.Add(static_cast<float>(Previous.AnchorTime));       // 17
        Out.Add(Previous.WalkRate);                             // 18
        Out.Add(static_cast<float>(Previous.Velocity.X));       // 19 world velocity
        Out.Add(static_cast<float>(Previous.Velocity.Y));       // 20
        Out.Add(Previous.VelocityZ);                            // 21
        Out.Add(Previous.bIdleAnim ? 1.f : 0.f);                // 22
        Out.Add(static_cast<float>(Previous.SwitchTime));       // 23
        Out.Add(Previous.HorizonSeconds);                       // 24
        Out.Add(VatHistoryUpdatedAt[Index]);                    // 25 interval boundary, NOT anchor time
    }
}

void AMikdashCrowdField::PushVat(int32 GlobalStart, int32 GlobalCount)
{
    if (GlobalCount <= 0 || ActivePoseCount <= 0)
    {
        return;
    }
    const int32 Floats = bVatMotionHistory ? VatHistoryCustomDataFloats : VatCustomDataFloats;
    for (int32 Pose = 0; Pose < ActivePoseCount; ++Pose)
    {
        UHierarchicalInstancedStaticMeshComponent* Component = PoseComponents.IsValidIndex(Pose) ? PoseComponents[Pose].Get() : nullptr;
        int32 First = 0, Count = 0;
        MikdashCrowd::InterleavedWindow(GlobalStart, GlobalCount, Pose, ActivePoseCount, First, Count);
        if (!Component || Count <= 0 || Component->GetInstanceCount() < First + Count || Component->NumCustomDataFloats != Floats)
        {
            continue;
        }
        TransformScratch.Reset(Count);
        CustomScratch.Reset(Count * Floats);
        for (int32 K = 0; K < Count; ++K)
        {
            const int32 Global = (First + K) * ActivePoseCount + Pose;
            TransformScratch.Add(TransformFor(Agents[Global]));
            AppendVatCustomData(Global, CustomScratch);
        }
        for (int32 K = 0; K < Count; ++K)
        {
            Component->SetCustomData(First + K, TArrayView<const float>(CustomScratch.GetData() + K * Floats, Floats), false);
        }
        // Transform and custom data land in the same frame: the re-anchored figure is drawn exactly
        // where the old anchor's extrapolation put it, so the re-anchor is invisible.
        // UE 5.8 tracks transform/custom-data changes and flushes them through
        // SendRenderInstanceData_Concurrent. Keep the scene proxy alive between
        // updates instead of requesting its destruction on every crowd tick.
        Component->BatchUpdateInstancesTransforms(First, TransformScratch, /*bWorldSpace*/ true,
                                                 /*bMarkRenderStateDirty*/ false, /*bTeleport*/ true);
    }
}

void AMikdashCrowdField::CommitVat(FMikdashCrowdAgent& Agent, double Now) const
{
    MikdashCrowd::VatAnchor Anchor;
    Anchor.X = Agent.Position.X; Anchor.Y = Agent.Position.Y; Anchor.Z = Agent.GroundZCm;
    Anchor.Time = Agent.AnchorTime;
    Anchor.VelX = Agent.Velocity.X; Anchor.VelY = Agent.Velocity.Y; Anchor.VelZ = Agent.VelocityZ;
    Anchor.Phase = Agent.WalkPhaseAtAnchor; Anchor.Rate = Agent.WalkRate; Anchor.Horizon = Agent.HorizonSeconds;
    MikdashCrowd::VatCommit(Anchor, Now);
    Agent.Position = FVector2D(Anchor.X, Anchor.Y);
    Agent.GroundZCm = static_cast<float>(Anchor.Z);
    Agent.WalkPhaseAtAnchor = static_cast<float>(Anchor.Phase);
    Agent.AnchorTime = Anchor.Time;
}

void AMikdashCrowdField::SetVatIdle(FMikdashCrowdAgent& Agent, double Now) const
{
    // Travel and stride stop together: Rate 0 freezes the walk phase while the material blends
    // it out, so a stopping figure never walks in place.
    Agent.Velocity = FVector2D::ZeroVector;
    Agent.VelocityZ = 0.f;
    Agent.WalkRate = 0.f;
    if (!Agent.bIdleAnim)
    {
        Agent.bIdleAnim = 1;
        Agent.SwitchTime = Now;
    }
}

bool AMikdashCrowdField::SetVatWalk(FMikdashCrowdAgent& Agent, double Now, const FVector2D& Velocity2D, float VelocityZ,
                                    float Horizon, double Speed) const
{
    if (Agent.bIdleAnim)
    {
        if (Now - Agent.SwitchTime < static_cast<double>(VatMinIdleSeconds))
        {
            SetVatIdle(Agent, Now);
            return false;
        }
        Agent.bIdleAnim = 0;
        Agent.SwitchTime = Now;
    }
    Agent.Velocity = Velocity2D;
    Agent.VelocityZ = VelocityZ;
    Agent.HorizonSeconds = Horizon;
    // THE no-slide line: stride rate from the same speed the figure translates at.
    Agent.WalkRate = static_cast<float>(MikdashCrowd::VatCyclesPerSecond(Speed, VatWalkGroundSpeedCmPerSecond,
                                                                        Agent.ScaleFactor, VatWalkCycleSeconds));
    return true;
}

void AMikdashCrowdField::PushTransforms(int32 GlobalStart, int32 GlobalCount)
{
    if (bUseVertexAnimation)
    {
        PushVat(GlobalStart, GlobalCount);
        return;
    }
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
                                                     /*bMarkRenderStateDirty*/ false, /*bTeleport*/ true);
        }
        Cursor = RunEnd;
    }
}

void AMikdashCrowdField::ClearCrowd()
{
    if(GetWorld()) GetWorld()->GetTimerManager().ClearTimer(CrowdStartTimer);
    for (const TObjectPtr<UHierarchicalInstancedStaticMeshComponent>& Component : PoseComponents)
    {
        if (Component)
        {
            Component->ClearInstances();
        }
    }
    Agents.Reset();
    VisitorGroups.Reset();VisitorSpacing.Clear();RefusedCohorts.Reset();
    bSocialRuntime=false;
    GroupedVisitors=0;IndividualVisitors=0;RefusedGroups=0;PausedVisitorGroups=0;
    GroupSweepsLastFrame=0;GroupRejectedMovesLastFrame=0;GroupWaitVisitsLastFrame=0;
    ResumedVisitorGroups=0;
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

bool AMikdashCrowdField::SocialSegmentAllowed(int32 ZoneIndex,const Vec2& From,const Vec2& To) const
{
    using namespace MikdashCrowd;
    if(!RuntimeZones.IsValidIndex(ZoneIndex)||!Finite(From)||!Finite(To)
        ||Length(To-From)>MikdashCrowdGroups::MaxStepCm+.001) return false;
    MikdashCrowdGroups::Geometry Geometry;
    Geometry.Zone=ZonePointCache.GetData()+ZoneStartCache[ZoneIndex];Geometry.ZoneCount=ZoneVertexCountCache[ZoneIndex];
    Geometry.Protected=KeepOutPointCache.GetData();Geometry.Starts=KeepOutStartCache.GetData();Geometry.Counts=KeepOutCountCache.GetData();
    Geometry.ProtectedCount=KeepOutCountCache.Num();Geometry.EdgeMargin=RuntimeZones[ZoneIndex].EdgeMarginCm;
    Geometry.ProtectedMargin=ProtectedMarginCm;
    return MikdashCrowdGroups::SegmentAllowed(Geometry,From,To);
}

void AMikdashCrowdField::SeedSocialZone(int32 ZoneIndex,int32 ZoneTotal,int32& GlobalIndex,
    const MikdashCrowdGroups::SeedBatch* Retry,int32 PreferredZone)
{
    using namespace MikdashCrowd;
    if(Retry)
    {
        if(!RuntimeZones.IsValidIndex(PreferredZone)||Retry->Count<1||Retry->Count>MikdashCrowdGroups::MaxMembers) return;
        for(int32 M=0;M<Retry->Count;++M)
            if(!Agents.IsValidIndex(Retry->First+M)||Agents[Retry->First+M].bValid) return;
    }
    const auto& Zone=RuntimeZones[ZoneIndex];
    const Vec2* Polygon=ZonePointCache.GetData()+ZoneStartCache[ZoneIndex];
    const int32 Vertices=ZoneVertexCountCache[ZoneIndex];
    const uint32 Seed=static_cast<uint32>(RandomSeed);
    // Bounded diagnostic override: measure search exhaustion separately from physical
    // capacity without relaxing any placement constraint or changing the default.
    int32 AttemptBudget=SocialSeedAttempts;
    if(FParse::Value(FCommandLine::Get(),TEXT("CrowdSeedAttempts="),AttemptBudget))
        AttemptBudget=FMath::Clamp(AttemptBudget,1,1024);
    const auto Batches=Retry?std::vector<MikdashCrowdGroups::SeedBatch>{*Retry}
        :MikdashCrowdGroups::PlanSeedBatches(ZoneTotal,GlobalIndex,IndividualVisitorRatio,Seed);
    const double MinSpeed=FMath::Max(0.f,MinWalkSpeedCmPerSecond);
    const double MaxSpeed=FMath::Max(MinSpeed,static_cast<double>(MaxWalkSpeedCmPerSecond));
    // Count the first failing gate per attempt; these are attempts, not refused people.
    // Keep placement decisions and random samples unchanged while diagnosing capacity.
    const int32 SeededBefore=SeededAgents, RefusedBefore=RefusedSeeds;
    int32 Trials=0, Accepted=0, PointReject=0, SegmentReject=0, SpacingReject=0;
    int32 FormationReject=0, LinkReject=0, GroundReject=0, ObstacleReject=0, InsertReject=0;
    for(const auto& Batch:Batches)
    {
        const int32 First=Batch.First;
        const int32 Size=Batch.Count;
        const bool Standing=IsStanding(Seed,static_cast<uint32>(First),
            Retry?RuntimeZones[PreferredZone].StandingRatio:Zone.StandingRatio);
        Vec2 Points[MikdashCrowdGroups::MaxMembers];float Grounds[MikdashCrowdGroups::MaxMembers]{};
        double Heading=0;bool Placed=false;
        for(int32 Attempt=0;Attempt<AttemptBudget&&!Placed;++Attempt)
        {
            ++Trials;
            const uint32 Trial=static_cast<uint32>(First)+static_cast<uint32>(Attempt)*65537u;
            if(!SeedPointInZone(Polygon,Vertices,KeepOutPointCache.GetData(),KeepOutStartCache.GetData(),
                KeepOutCountCache.GetData(),KeepOutCountCache.Num(),FMath::Max(ProtectedMarginCm,44.f),
                FMath::Max(Zone.EdgeMarginCm,34.f),Seed,Trial,1,Points[0])) { ++PointReject;continue; }
            Heading=YawDegrees(SampleFlow(ZoneFlowCache[ZoneIndex],Points[0],0,Seed,static_cast<uint32>(First)));
            bool Okay=true;
            for(int32 Member=0;Member<Size&&Okay;++Member)
            {
                if(Member>0) Points[Member]=Points[0]+MikdashCrowdGroups::WorldOffset(
                    MikdashCrowdGroups::Offset(Member,Seed,static_cast<uint32>(First),GroupSpacingCm),Heading);
                if(!SocialSegmentAllowed(ZoneIndex,Points[Member],Points[Member]))
                    { ++SegmentReject;Okay=false;break; }
                if(!VisitorSpacing.SegmentClear(Points[Member],Points[Member],-1))
                    { ++SpacingReject;Okay=false;break; }
                for(int32 Other=0;Other<Member;++Other)
                    if(Length(Points[Other]-Points[Member])<MikdashCrowdGroups::MinSeparationCm) Okay=false;
                if(!Okay) ++FormationReject;
                // Do not seed companions on opposite sides of a protected wall.
                const int32 Pieces=FMath::Max(1,FMath::CeilToInt(Length(Points[Member]-Points[0])/80.0));
                for(int32 Piece=0;Piece<Pieces&&Okay;++Piece)
                {
                    const Vec2 A=Points[0]+(Points[Member]-Points[0])*(static_cast<double>(Piece)/Pieces);
                    const Vec2 B=Points[0]+(Points[Member]-Points[0])*(static_cast<double>(Piece+1)/Pieces);
                    if(!SocialSegmentAllowed(ZoneIndex,A,B)) { ++LinkReject;Okay=false; }
                }
            }
            if(!Okay) continue;
            double LeaderResidual=0;
            for(int32 Member=0;Member<Size&&Okay;++Member)
            {
                const FVector2D P=ToFVector2D(Points[Member]);
                Grounds[Member]=ResolveGroundZ(Zone,P);
                const double Residual=Grounds[Member]-ZoneGroundZ(Zone,P);
                if(Member==0) LeaderResidual=Residual;
                if(!FMath::IsFinite(Residual) || FMath::Abs(Residual)>55.0 || FMath::Abs(Residual-LeaderResidual)>20.0) { ++GroundReject;Okay=false;break; }
                if(bSweepGroupObstacles && GetWorld())
                {
                    FCollisionQueryParams Query(SCENE_QUERY_STAT(CrowdGroupSeed),false,this);
                    const FCollisionObjectQueryParams Objects(ECC_WorldStatic);
                    const FVector End(P.X,P.Y,Grounds[Member]+99.f);
                    const bool Blocked=Member==0
                        ?GetWorld()->OverlapAnyTestByObjectType(End,FQuat::Identity,Objects,FCollisionShape::MakeCapsule(34.f,96.f),Query)
                        :GetWorld()->SweepTestByObjectType(FVector(Points[0].X,Points[0].Y,Grounds[0]+99.f),End,
                            FQuat::Identity,Objects,FCollisionShape::MakeCapsule(34.f,96.f),Query);
                    if(Blocked) { ++ObstacleReject;Okay=false; }
                }
            }
            if(!Okay) continue;
            int32 Inserted=0;
            for(;Inserted<Size;++Inserted) if(!VisitorSpacing.Insert(First+Inserted,Points[Inserted])) break;
            if(Inserted!=Size)
            { ++InsertReject;for(int32 I=0;I<Inserted;++I) VisitorSpacing.Remove(First+I,Points[I]);continue; }
            Placed=true;++Accepted;
        }
        int32 GroupIndex=INDEX_NONE;
        // Vertex-animated: the natural pace IS the clip's ground speed for this body and cadence,
        // so the walk plays near rate 1 and every figure's pace differs from its neighbour's.
        const float Speed=Standing?0.f:(bUseVertexAnimation
            ? static_cast<float>(VatWalkGroundSpeedCmPerSecond*HeightScaleFor(Seed,static_cast<uint32>(First),FigureScaleMin,FigureScaleMax)
                *CadenceFor(Seed,static_cast<uint32>(First),VatCadenceSpread))
            : static_cast<float>(WalkSpeedFor(Seed,static_cast<uint32>(First),MinSpeed,MaxSpeed)));
        if(Placed&&Size>1)
        {
            FVisitorGroup Group;Group.ZoneIndex=ZoneIndex;Group.SeedAnchor=ToFVector2D(Points[0]);
            Group.Travel.FormationHeading=Heading;
            Group.Cohort.Count=Size;Group.Cohort.Identity=static_cast<uint32>(First);Group.Cohort.Speed=Speed;
            for(int32 Member=0;Member<Size;++Member) Group.Cohort.Members[Member]=First+Member;
            GroupIndex=VisitorGroups.Add(Group);GroupedVisitors+=Size;
        }
        else if(Placed) ++IndividualVisitors;
        else if(!Retry&&Size>1) ++RefusedGroups;
        if(Retry&&!Placed) continue; // Preserve original invalid agents and count each refusal once.
        if(Retry&&Placed)
        {
            RefusedSeeds-=Size;
            if(Size>1) --RefusedGroups;
            UE_LOG(LogTemp,Display,TEXT("CrowdOverflowCohortV1 first=%d count=%d preferred=%d destination=%d"),
                First,Size,PreferredZone,ZoneIndex);
        }
        if(!Retry&&!Placed) RefusedCohorts.Add({ZoneIndex,Batch});
        for(int32 Member=0;Member<Size;++Member)
        {
            const int32 AgentIndex=First+Member;
            auto& Agent=Agents[AgentIndex];Agent.ZoneIndex=ZoneIndex;
            Agent.ScaleFactor=static_cast<float>(HeightScaleFor(Seed,static_cast<uint32>(AgentIndex),FigureScaleMin,FigureScaleMax));
            if(!Placed)
            { Agent.bValid=0;Agent.Position=Zone.PolygonCm.Num()?Zone.PolygonCm[0]:FVector2D::ZeroVector;
              Agent.GroundZCm=ZoneGroundZ(Zone,Agent.Position);
              if(!FMath::IsFinite(Agent.GroundZCm)) Agent.GroundZCm=0;
              ++RefusedSeeds;continue; }
            Agent.bValid=1;Agent.bStanding=Standing?1:0;Agent.Position=ToFVector2D(Points[Member]);
            Agent.ReseedPoint=Agent.Position;Agent.GroundZCm=Grounds[Member];Agent.HeadingDegrees=static_cast<float>(Heading);
            Agent.SpeedCmPerSecond=Speed;Agent.Phase=static_cast<float>(HashUnit(Seed,static_cast<uint32>(AgentIndex),5u));
            Agent.GroupIndex=GroupIndex;Agent.GroupMember=Member;++SeededAgents;
        }
    }
    if(Retry) return;
    GlobalIndex+=ZoneTotal;
    UE_LOG(LogTemp,Display,TEXT("CrowdSeedAuditV1 zone=%d name=\"%s\" requested=%d seeded=%d refused=%d trials=%d accepted=%d point=%d segment=%d spacing=%d formation=%d link=%d ground=%d obstacle=%d insert=%d maxAttempts=%d"),
        ZoneIndex,*Zone.Name,ZoneTotal,SeededAgents-SeededBefore,RefusedSeeds-RefusedBefore,
        Trials,Accepted,PointReject,SegmentReject,SpacingReject,FormationReject,LinkReject,GroundReject,ObstacleReject,InsertReject,AttemptBudget);
}

void AMikdashCrowdField::RetryRefusedCohorts()
{
    std::vector<int> Requested,Initial;
    for(int32 Z=0;Z<RuntimeZones.Num();++Z) {Requested.push_back(ZoneCounts[Z]);Initial.push_back(0);}
    for(const auto& Agent:Agents) if(Agent.bValid) ++Initial[Agent.ZoneIndex];
    const int32 Before=RefusedSeeds;
    // Keep initial successful placements. Retry whole original cohorts, never split
    // them or invent new identities to achieve a population count.
    RefusedCohorts.StableSort([](const FRefusedCohort&A,const FRefusedCohort&B){return A.Batch.Count>B.Batch.Count;});
    for(const auto& Cohort:RefusedCohorts)
    {
        for(const int Destination:MikdashCrowdGroups::FallbackZoneOrder(Cohort.PreferredZone,Requested,Initial))
        {
            int32 UnusedIndex=0;
            SeedSocialZone(Destination,0,UnusedIndex,&Cohort.Batch,Cohort.PreferredZone);
            if(Agents[Cohort.Batch.First].bValid) break;
        }
    }
    TArray<int32> Actual;Actual.SetNumZeroed(RuntimeZones.Num());
    for(const auto& Agent:Agents) if(Agent.bValid) ++Actual[Agent.ZoneIndex];
    for(int32 Z=0;Z<RuntimeZones.Num();++Z)
        UE_LOG(LogTemp,Display,TEXT("CrowdFinalZoneV1 zone=%d name=\"%s\" preferredRequested=%d initialSeeded=%d actualSeeded=%d relocatedIn=%d"),
            Z,*RuntimeZones[Z].Name,Requested[Z],Initial[Z],Actual[Z],Actual[Z]-Initial[Z]);
    UE_LOG(LogTemp,Display,TEXT("CrowdOverflowAuditV1 initialRefused=%d recovered=%d remainingRefused=%d finalSeeded=%d"),
        Before,Before-RefusedSeeds,RefusedSeeds,SeededAgents);
    RefusedCohorts.Reset();
}

void AMikdashCrowdField::StepSocialAgent(int32 Index,double Dt,const MikdashCrowd::FlowZone& Flow)
{
    using namespace MikdashCrowd;
    auto& Agent=Agents[Index];
    if(Agent.bStanding)
    { Agent.Phase=static_cast<float>(AdvancePhase(Agent.Phase,0,Dt,true));return; }
    Vec2 Direction=SampleFlow(Flow,ToVec2(Agent.Position),ElapsedSeconds,static_cast<uint32>(RandomSeed),static_cast<uint32>(Index));
    double Speed=Agent.SpeedCmPerSecond;
    FVisitorGroup* Group=VisitorGroups.IsValidIndex(Agent.GroupIndex)?&VisitorGroups[Agent.GroupIndex]:nullptr;
    if(Group)
    {
        Vec2 Positions[MikdashCrowdGroups::MaxMembers];
        for(int32 Member=0;Member<Group->Cohort.Count;++Member)
        {
            const int32 Id=Group->Cohort.Members[Member];
            // No leader substitution/reseed/teleport when a member disappears.
            if(!Agents.IsValidIndex(Id)||!Agents[Id].bValid||Agents[Id].ZoneIndex!=Group->ZoneIndex)
            { ++GroupWaitVisitsLastFrame;return; }
            Positions[Member]=ToVec2(Agents[Id].Position);
        }
        FlowZone SharedFlow=Flow;
        if(Group->Travel.Mode==MikdashCrowdGroups::TravelMode::Returning)
        { SharedFlow.Goal=ToVec2(Group->SeedAnchor);SharedFlow.GoalWeight=1;SharedFlow.SwirlDegrees=0; }
        const Vec2 SharedDirection=SampleFlow(SharedFlow,Positions[0],ElapsedSeconds,static_cast<uint32>(RandomSeed),Group->Cohort.Identity);
        MikdashCrowdGroups::Settings Config;Config.SpacingCm=GroupSpacingCm;Config.SlowLagCm=GroupSlowLagCm;Config.WaitLagCm=GroupWaitLagCm;
        const auto Command=MikdashCrowdGroups::Steering(Group->Cohort,Agent.GroupMember,Positions,
            Group->Travel.FormationHeading,SharedDirection,Config,static_cast<uint32>(RandomSeed),
            Group->Travel.Mode==MikdashCrowdGroups::TravelMode::Paused);
        if(!Command.Valid) { ++GroupWaitVisitsLastFrame;return; }
        Direction=Command.Direction;Speed=Command.Speed;
        if(Command.Waiting) ++GroupWaitVisitsLastFrame;
    }
    const double SafeDt=Clamp(Dt,0.0,.5);
    const double Heading=SteerHeading(Agent.HeadingDegrees,YawDegrees(Direction),SafeDt,MaxTurnDegreesPerSecond);
    if(Speed<=.01) return;
    Agent.HeadingDegrees=static_cast<float>(Heading);
    const Vec2 From=ToVec2(Agent.Position);
    const Vec2 To=From+FromDegrees(Heading)*std::min(MikdashCrowdGroups::MaxStepCm,std::max(0.0,Speed)*SafeDt);
    bool Allowed=SocialSegmentAllowed(Agent.ZoneIndex,From,To)&&VisitorSpacing.SegmentClear(From,To,Index);
    const auto& Zone=RuntimeZones[Agent.ZoneIndex];
    double NextGround=Agent.GroundZCm;
    if(!FMath::IsFinite(NextGround)||(Zone.GroundMode==EMikdashCrowdGround::Plane
        &&!MikdashCrowdGroups::FollowPlane(Agent.GroundZCm,ZoneGroundZ(Zone,Agent.Position),
            ZoneGroundZ(Zone,ToFVector2D(To)),NextGround))) Allowed=false;
    if(!FMath::IsFinite(static_cast<float>(NextGround))) Allowed=false;
    if(Allowed&&bSweepGroupObstacles&&GetWorld())
    {
        ++GroupSweepsLastFrame;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(CrowdGroupMove),false,this);
        const FCollisionObjectQueryParams Objects(ECC_WorldStatic);
        Allowed=!GetWorld()->SweepTestByObjectType(FVector(From.X,From.Y,Agent.GroundZCm+99.f),
            FVector(To.X,To.Y,NextGround+99.f),FQuat::Identity,Objects,FCollisionShape::MakeCapsule(34.f,96.f),Query);
    }
    if(Allowed) Allowed=VisitorSpacing.Move(Index,From,To);
    if(!Allowed)
    {
        ++GroupRejectedMovesLastFrame;
        // Turn at an edge; never use the old far-edge teleport to regroup visitors.
        if(Group&&Agent.GroupMember==0)
        {
            const bool WasPaused=Group->Travel.Mode==MikdashCrowdGroups::TravelMode::Paused;
            MikdashCrowdGroups::RejectedLeaderMove(Group->Travel,Length(From-ToVec2(Group->SeedAnchor)));
            if(!WasPaused&&Group->Travel.Mode==MikdashCrowdGroups::TravelMode::Paused) ++PausedVisitorGroups;
        }
        else if(!Group) Agent.HeadingDegrees=static_cast<float>(WrapDegrees(Heading+90));
        return;
    }
    Agent.Position=ToFVector2D(To);Agent.GroundZCm=static_cast<float>(NextGround);
    if(Group&&Agent.GroupMember==0)
        MikdashCrowdGroups::SuccessfulLeaderMove(Group->Travel,Length(To-ToVec2(Group->SeedAnchor)),Heading);
    Agent.Phase=static_cast<float>(AdvancePhase(Agent.Phase,Speed,SafeDt,false));
}

void AMikdashCrowdField::StepSocialAgentVat(int32 Index, double Now, float Horizon, const MikdashCrowd::FlowZone& Flow)
{
    using namespace MikdashCrowd;
    auto& Agent = Agents[Index];
    // Neighbor reservations rely on this entire segment. Finish it before
    // replanning or stopping; the material clamps at its reserved endpoint.
    if (!Agent.bIdleAnim && Now < Agent.AnchorTime + Agent.HorizonSeconds) return;
    // 1. Commit: the material has been drawing this figure along the segment validated at the
    //    previous visit; bring the anchor to the same point by the same expression.
    const double Elapsed = FMath::Clamp(Now - Agent.AnchorTime, 0.0, static_cast<double>(FMath::Max(0.f, Agent.HorizonSeconds)));
    const Vec2 Before = ToVec2(Agent.Position);
    CommitVat(Agent, Now);
    const Vec2 From = ToVec2(Agent.Position);
    if (Length(From - Before) > 1e-6)
    {
        ensureMsgf(VisitorSpacing.Relocate(Index, Before, From, Now), TEXT("Completed crowd reservation could not relocate"));
    }
    if (Agent.bStanding)
    {
        SetVatIdle(Agent, Now);
        return;
    }
    // 2. Plan the next Horizon seconds exactly as the historical step decides a move.
    Vec2 Direction = SampleFlow(Flow, From, ElapsedSeconds, static_cast<uint32>(RandomSeed), static_cast<uint32>(Index));
    double Speed = Agent.SpeedCmPerSecond;
    FVisitorGroup* Group = VisitorGroups.IsValidIndex(Agent.GroupIndex) ? &VisitorGroups[Agent.GroupIndex] : nullptr;
    if (Group)
    {
        if (Agent.GroupMember == 0 && PausedGroupResumeSeconds > 0.f && Group->Travel.Mode == MikdashCrowdGroups::TravelMode::Paused)
        {
            if (Group->PausedSince < 0.0)
            {
                Group->PausedSince = Now;
            }
            else if (Now - Group->PausedSince >= PausedGroupResumeSeconds *
                     (0.75 + 0.5 * HashUnit(static_cast<uint32>(RandomSeed), Group->Cohort.Identity, 83u)))
            {
                // A paused party stood forever before: that is a statue cluster. Head back for the
                // anchor it came from, which it reached once and can reach again.
                Group->Travel.Mode = MikdashCrowdGroups::TravelMode::Returning;
                Group->PausedSince = -1.0;
                ++ResumedVisitorGroups;
            }
        }
        Vec2 Positions[MikdashCrowdGroups::MaxMembers];
        for (int32 Member = 0; Member < Group->Cohort.Count; ++Member)
        {
            const int32 Id = Group->Cohort.Members[Member];
            if (!Agents.IsValidIndex(Id) || !Agents[Id].bValid || Agents[Id].ZoneIndex != Group->ZoneIndex)
            {
                ++GroupWaitVisitsLastFrame;
                SetVatIdle(Agent, Now);
                return;
            }
            const auto& Other = Agents[Id];
            const double OtherDt = FMath::Clamp(Now - Other.AnchorTime, 0.0, static_cast<double>(Other.HorizonSeconds));
            Positions[Member] = ToVec2(Other.Position + Other.Velocity * OtherDt);
        }
        FlowZone SharedFlow = Flow;
        if (Group->Travel.Mode == MikdashCrowdGroups::TravelMode::Returning)
        {
            SharedFlow.Goal = ToVec2(Group->SeedAnchor); SharedFlow.GoalWeight = 1; SharedFlow.SwirlDegrees = 0;
        }
        const Vec2 SharedDirection = SampleFlow(SharedFlow, Positions[0], ElapsedSeconds, static_cast<uint32>(RandomSeed), Group->Cohort.Identity);
        MikdashCrowdGroups::Settings Config; Config.SpacingCm = GroupSpacingCm; Config.SlowLagCm = GroupSlowLagCm; Config.WaitLagCm = GroupWaitLagCm;
        const auto Command = MikdashCrowdGroups::Steering(Group->Cohort, Agent.GroupMember, Positions,
            Group->Travel.FormationHeading, SharedDirection, Config, static_cast<uint32>(RandomSeed),
            Group->Travel.Mode == MikdashCrowdGroups::TravelMode::Paused);
        if (!Command.Valid)
        {
            ++GroupWaitVisitsLastFrame;
            SetVatIdle(Agent, Now);
            return;
        }
        Direction = Command.Direction; Speed = Command.Speed;
        if (Command.Waiting) ++GroupWaitVisitsLastFrame;
    }
    const double SafeHorizon = static_cast<double>(FMath::Max(0.02f, Horizon));
    // Heading is an immediate instance update, not shader-interpolated. Even
    // when a reserved segment spans several frames, keep this frame's yaw bound.
    const double TurnSeconds = Clamp(FMath::Max(FMath::Min(Elapsed,
        static_cast<double>(GetWorld()->GetDeltaSeconds())), 1.0 / 120.0), 0.0, 0.5);
    const double Heading = SteerHeading(Agent.HeadingDegrees, YawDegrees(Direction), TurnSeconds,
                                        MaxTurnDegreesPerSecond);
    // Only speeds the clip can play at are walked; the look-ahead stays inside the group step limit.
    double Playable = VatPlayableSpeed(Speed, VatWalkGroundSpeedCmPerSecond, Agent.ScaleFactor, VatMinPlayRate, VatMaxPlayRate);
    Playable = FMath::Min(Playable, (MikdashCrowdGroups::MaxStepCm - 1.0) / SafeHorizon);
    if (Playable <= 0.0)
    {
        SetVatIdle(Agent, Now);
        return;
    }
    const Vec2 To = From + FromDegrees(Heading) * (Playable * SafeHorizon);
    bool Allowed = SocialSegmentAllowed(Agent.ZoneIndex, From, To) && VisitorSpacing.CanReserve(Index, From, To, Now, SafeHorizon);
    const auto& Zone = RuntimeZones[Agent.ZoneIndex];
    double NextGround = Agent.GroundZCm;
    if (!FMath::IsFinite(NextGround) || (Zone.GroundMode == EMikdashCrowdGround::Plane
        && !MikdashCrowdGroups::FollowPlane(Agent.GroundZCm, ZoneGroundZ(Zone, Agent.Position),
            ZoneGroundZ(Zone, ToFVector2D(To)), NextGround))) Allowed = false;
    if (!FMath::IsFinite(static_cast<float>(NextGround))) Allowed = false;
    if (Allowed && bSweepGroupObstacles && GetWorld())
    {
        ++GroupSweepsLastFrame;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(CrowdGroupMove), false, this);
        const FCollisionObjectQueryParams Objects(ECC_WorldStatic);
        Allowed = !GetWorld()->SweepTestByObjectType(FVector(From.X, From.Y, Agent.GroundZCm + 99.f),
            FVector(To.X, To.Y, NextGround + 99.f), FQuat::Identity, Objects, FCollisionShape::MakeCapsule(34.f, 96.f), Query);
    }
    if (!Allowed)
    {
        ++GroupRejectedMovesLastFrame;
        SetVatIdle(Agent, Now);
        // Turn in place even when translation is blocked. Otherwise a returning
        // party repeatedly retries its old forward heading after every pause.
        if (Group) Agent.HeadingDegrees = static_cast<float>(Heading);
        if (Group && Agent.GroupMember == 0)
        {
            const bool WasPaused = Group->Travel.Mode == MikdashCrowdGroups::TravelMode::Paused;
            MikdashCrowdGroups::RejectedTurningLeaderMove(Group->Travel,
                Length(From - ToVec2(Group->SeedAnchor)), Heading, YawDegrees(Direction));
            if (!WasPaused && Group->Travel.Mode == MikdashCrowdGroups::TravelMode::Paused)
            {
                ++PausedVisitorGroups;
                Group->PausedSince = Now;
            }
        }
        else if (!Group)
        {
            // A rejected solo move chooses a sideways escape direction, but the
            // rendered figure must obey the same turn limit as a successful move.
            Agent.HeadingDegrees = static_cast<float>(SteerHeading(
                Agent.HeadingDegrees, Heading + 90, TurnSeconds, MaxTurnDegreesPerSecond));
        }
        return;
    }
    const Vec2 Delta = To - From;
    const FVector2D Velocity2D(Delta.X / SafeHorizon, Delta.Y / SafeHorizon);
    const float VelocityZ = static_cast<float>((NextGround - Agent.GroundZCm) / SafeHorizon);
    Agent.HeadingDegrees = static_cast<float>(Heading);
    if (!SetVatWalk(Agent, Now, Velocity2D, VelocityZ, static_cast<float>(SafeHorizon), Playable))
    {
        return;   // still inside the idle hold: stays put, not a rejected move
    }
    if (!VisitorSpacing.Reserve(Index, From, To, Now, SafeHorizon))
    {
        SetVatIdle(Agent, Now);
        return;
    }
    if (Group && Agent.GroupMember == 0)
    {
        MikdashCrowdGroups::SuccessfulLeaderMove(Group->Travel, Length(To - ToVec2(Group->SeedAnchor)), Heading);
    }
}

void AMikdashCrowdField::BuildCrowd(int32 OverrideCount)
{
    using namespace MikdashCrowd;

    ClearCrowd();
    // Vertex animation needs the social step: its look-ahead segment validation is what keeps an
    // extrapolated figure out of walls and out of its neighbours.
    bSocialRuntime=bEnableVisitorGroups||bUseVertexAnimation;
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
        if(bSocialRuntime) { SeedSocialZone(ZoneIndex,ZoneTotal,GlobalIndex);continue; }
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
                if(!FMath::IsFinite(Agent.GroundZCm)) Agent.GroundZCm=0;
                ++RefusedSeeds;
                continue;
            }
            Agent.bValid = 1;
            Agent.Position = ToFVector2D(Point);
            Agent.GroundZCm = ResolveGroundZ(Zone, Agent.Position);
            if(!FMath::IsFinite(Agent.GroundZCm))
            { Agent.bValid=0;Agent.GroundZCm=0; ++RefusedSeeds;continue; }
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

    if(bSocialRuntime) RetryRefusedCohorts();

    if (bUseVertexAnimation)
    {
        // Every figure starts idle (walkers get their first plan within one sweep, each on its own
        // walk phase and idle offset), then bodies are interleaved over the components.
        const double Now = VatNow();
        for (int32 Index = 0; Index < Total; ++Index)
        {
            FMikdashCrowdAgent& Agent = Agents[Index];
            Agent.AnchorTime = Now;
            Agent.Velocity = FVector2D::ZeroVector;
            Agent.VelocityZ = 0.f;
            Agent.WalkRate = 0.f;
            Agent.HorizonSeconds = 0.f;
            Agent.WalkPhaseAtAnchor = Agent.Phase;
            Agent.IdleOffset = static_cast<float>(HashUnit(Seed, static_cast<uint32>(Index), 71u));
            Agent.bIdleAnim = 1;
            Agent.SwitchTime = -1000.0;
        }
        if (bVatMotionHistory)
        {
            VatPreviousAgents = Agents;
            VatHistoryUpdatedAt.Init(static_cast<float>(Now), Total);
        }
        for (int32 Pose = 0; Pose < ActivePoseCount; ++Pose)
        {
            UHierarchicalInstancedStaticMeshComponent* Component = PoseComponents.IsValidIndex(Pose) ? PoseComponents[Pose].Get() : nullptr;
            const int32 Count = InterleavedCount(Pose, Total, ActivePoseCount);
            if (!Component || Count <= 0)
            {
                continue;
            }
            TransformScratch.Reset(Count);
            for (int32 Local = 0; Local < Count; ++Local)
            {
                TransformScratch.Add(TransformFor(Agents[Local * ActivePoseCount + Pose]));
            }
            Component->AddInstances(TransformScratch, /*bShouldReturnIndices*/ false, /*bWorldSpace*/ true);
            for (int32 Local = 0; Local < Count; ++Local)
            {
                CustomScratch.Reset(VatCustomDataFloats);
                AppendVatCustomData(Local * ActivePoseCount + Pose, CustomScratch);
                Component->SetCustomData(Local, TArrayView<const float>(CustomScratch.GetData(), CustomScratch.Num()), false);
            }
            // BeginPlay seeding is deferred until the world has begun play, so HISM's
            // pre-BeginPlay force-sync guard no longer applies. Finish the initial tree
            // before per-frame transforms can repeatedly invalidate its async build.
            Component->BuildTreeIfOutdated(/*Async*/ false, /*ForceUpdate*/ false);
            UE_LOG(LogTemp, Display, TEXT("CrowdRenderSeedV1 pose=%d instances=%d built=%d render=%d"),
                Pose, Component->GetInstanceCount(), Component->NumBuiltInstances, Component->InstanceCountToRender);
            Component->MarkRenderStateDirty();
        }
        UpdateCursor = 0;
        bCrowdRunning = Agents.Num() > 0;
        SetActorTickEnabled(bCrowdRunning && HasActorBegunPlay());
        return;
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
        // Establish initial render readiness before this actor starts moving instances.
        Component->BuildTreeIfOutdated(/*Async*/ false, /*ForceUpdate*/ false);
        UE_LOG(LogTemp, Display, TEXT("CrowdRenderSeedV1 pose=%d instances=%d built=%d render=%d"),
            Pose, Component->GetInstanceCount(), Component->NumBuiltInstances, Component->InstanceCountToRender);
        Component->MarkRenderStateDirty();
    }

    UpdateCursor = 0;
    bCrowdRunning = Agents.Num() > 0;
    SetActorTickEnabled(bCrowdRunning && HasActorBegunPlay());
}

void AMikdashCrowdField::BeginPlay()
{
    Super::BeginPlay();
    bMotionAudit = FParse::Param(FCommandLine::Get(), TEXT("MikdashCrowdMotionAudit"));
    bReviewAudit = FParse::Param(FCommandLine::Get(), TEXT("MikdashCrowdReviewAudit"));
    if (!bActivateOnBeginPlay)
    {
        // Adopted opt-in, matching the rest of this plugin: placing the actor changes nothing
        // until a release script or a reviewer turns it on.
        return;
    }
    // Enclosure BeginPlay installs the visible state's paving collision. Actor BeginPlay
    // order is unspecified: immediate traces can see terrain buried beneath those slabs.
    CrowdStartTimer=GetWorld()->GetTimerManager().SetTimerForNextTick(this,
        &AMikdashCrowdField::StartCrowdAfterWorldInitialization);
}

void AMikdashCrowdField::StartCrowdAfterWorldInitialization()
{
    if(!HasActorBegunPlay() || !bActivateOnBeginPlay) return;
    BuildCrowd(-1);
    SetActorTickEnabled(bCrowdRunning);
}

void AMikdashCrowdField::EndPlay(const EEndPlayReason::Type Reason)
{
    if(GetWorld()) GetWorld()->GetTimerManager().ClearTimer(CrowdStartTimer);
    bCrowdRunning = false;
    SetActorTickEnabled(false);
    Super::EndPlay(Reason);
}

void AMikdashCrowdField::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    GroupSweepsLastFrame=0;GroupRejectedMovesLastFrame=0;GroupWaitVisitsLastFrame=0;

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
    const double VatTime = bUseVertexAnimation ? VatNow() : 0.0;
    const float VatHorizon = bUseVertexAnimation
        ? static_cast<float>(VatHorizonSeconds(GetFramesPerSweep(), DeltaSeconds, VatMinHorizonSeconds, VatMaxHorizonSeconds))
        : 0.f;

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
            if (bVatMotionHistory)
            {
                // Capture BEFORE every mutation, including freeze/cull stops and
                // idle heading changes. Later frames select the current interval.
                VatPreviousAgents[Index] = Agent;
                VatHistoryUpdatedAt[Index] = static_cast<float>(VatTime);
            }
            // Distance policy. Freezing and culling skip the simulation -- the flow sample, the
            // polygon tests and the re-seed trace, which is where the time goes. The unchanged
            // transform is still written as part of the contiguous batch below, which costs a
            // memcpy and keeps the batch to one call per pose block.
            FVector2D LodPosition=Agent.Position;
            if(bSocialRuntime&&VisitorGroups.IsValidIndex(Agent.GroupIndex))
            {
                const int32 Leader=VisitorGroups[Agent.GroupIndex].Cohort.Members[0];
                if(Agents.IsValidIndex(Leader)) LodPosition=Agents[Leader].Position;
            }
            const double Distance = FMath::Sqrt(DistanceSquared2D(ToVec2(LodPosition), ViewXY));
            const InstanceWork Work = ClassifyByDistance(Distance, FreezeDistanceCm, CullDistanceCm);
            if (Work != InstanceWork::Simulate && bUseVertexAnimation && (!Agent.bIdleAnim || Agent.WalkRate != 0.f))
            {
                // Honor the short reserved movement before distance-based stop.
                // Stopping early could invalidate a following visitor's plan.
                if (VatTime < Agent.AnchorTime + Agent.HorizonSeconds) continue;
                // Leaving the simulated range: stop where the material has it and idle, rather than
                // freeze mid-stride when the anchor goes stale.
                const Vec2 Before = ToVec2(Agent.Position);
                CommitVat(Agent, VatTime);
                if (bSocialRuntime) ensureMsgf(VisitorSpacing.Relocate(Index, Before, ToVec2(Agent.Position), VatTime), TEXT("Frozen crowd reservation could not relocate"));
                SetVatIdle(Agent, VatTime);
            }
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

            if(bSocialRuntime)
            {
                if (bUseVertexAnimation)
                {
                    if (bMotionAudit && ElapsedSeconds >= 2.f && MotionAuditSamples < 4096)
                    {
                        const FMikdashCrowdAgent Before = Agent;
                        StepSocialAgentVat(Index, VatTime, VatHorizon, Flow);
                        AuditVatTransition(Index, Before, Agent, VatTime, DeltaSeconds);
                    }
                    else StepSocialAgentVat(Index, VatTime, VatHorizon, Flow);
                }
                else StepSocialAgent(Index,Step_,Flow);
                continue;
            }

            const FVector2D PreviousPosition=Agent.Position;
            const float PreviousGround=Agent.GroundZCm;
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
                // Follow the authored plane or exact sourced Kotel surface without a new trace.
                Agent.GroundZCm = ZoneGroundZ(Zone, Agent.Position);
            }
            if(!FMath::IsFinite(Agent.GroundZCm))
            {
                Agent.Position=PreviousPosition;
                Agent.GroundZCm=PreviousGround;
            }
        }
    }

    PushTransforms(Window.FirstStart, Window.FirstCount);
    PushTransforms(Window.SecondStart, Window.SecondCount);
    if (bReviewAudit && bUseVertexAnimation && Agents.Num() >= 2 && Agents.Num() <= 64 && ElapsedSeconds <= 65.0)
    {
        double Minimum = 1e30;
        int32 ClosestA = -1, ClosestB = -1;
        FVector2D Roots[64];
        for (int32 I = 0; I < Agents.Num(); ++I)
        {
            const auto& A = Agents[I];
            const double Dt = FMath::Clamp(VatTime - A.AnchorTime, 0.0, static_cast<double>(A.HorizonSeconds));
            Roots[I] = A.Position + A.Velocity * Dt;
        }
        for (int32 A = 0; A < Agents.Num(); ++A) for (int32 B = A + 1; B < Agents.Num(); ++B)
        {
            if (!Agents[A].bValid || !Agents[B].bValid) continue;
            const double Distance = (Roots[A] - Roots[B]).Size();
            if (Distance < Minimum) { Minimum = Distance; ClosestA = A; ClosestB = B; }
        }
        UE_LOG(LogTemp, Display, TEXT("CrowdSpacingV1 time=%.6f minimum=%.9f a=%d b=%d"), VatTime, Minimum, ClosestA, ClosestB);
    }
    if (bReviewAudit && bUseVertexAnimation && Agents.Num() <= 64
        && ReviewAuditSnapshot <= 12 && ElapsedSeconds >= ReviewAuditSnapshot * 5.0)
    {
        AuditReviewState(VatTime);
        ++ReviewAuditSnapshot;
    }
}

void AMikdashCrowdField::AuditReviewState(double Now)
{
    int32 Forward = 0, Returning = 0, Paused = 0;
    for (const auto& Group : VisitorGroups)
    {
        Forward += Group.Travel.Mode == MikdashCrowdGroups::TravelMode::Forward;
        Returning += Group.Travel.Mode == MikdashCrowdGroups::TravelMode::Returning;
        Paused += Group.Travel.Mode == MikdashCrowdGroups::TravelMode::Paused;
    }
    UE_LOG(LogTemp, Display, TEXT("CrowdReviewV1 snapshot=%d time=%.6f seeded=%d walking=%d forward=%d returning=%d paused=%d resumes=%d rejected=%d waits=%d resumeSeconds=%.3f yawOffset=%.3f"),
        ReviewAuditSnapshot, Now, SeededAgents, GetVatWalkingCount(), Forward, Returning, Paused,
        ResumedVisitorGroups, GroupRejectedMovesLastFrame, GroupWaitVisitsLastFrame,
        PausedGroupResumeSeconds, MeshYawOffsetDegrees);
    for (int32 Index = 0; Index < Agents.Num(); ++Index)
    {
        const auto& Agent = Agents[Index];
        if (!Agent.bValid) continue;
        const double Dt = FMath::Clamp(Now - Agent.AnchorTime, 0.0, static_cast<double>(Agent.HorizonSeconds));
        UE_LOG(LogTemp, Display, TEXT("CrowdReviewAgentV1 snapshot=%d agent=%d group=%d member=%d standing=%d idle=%d x=%.6f y=%.6f z=%.6f yaw=%.6f"),
            ReviewAuditSnapshot, Index, Agent.GroupIndex, Agent.GroupMember, Agent.bStanding, Agent.bIdleAnim,
            Agent.Position.X + Agent.Velocity.X * Dt, Agent.Position.Y + Agent.Velocity.Y * Dt,
            Agent.GroundZCm + Agent.VelocityZ * Dt, Agent.HeadingDegrees);
    }
}

void AMikdashCrowdField::AuditVatTransition(int32 Index, const FMikdashCrowdAgent& Before,
                                         const FMikdashCrowdAgent& After, double Now, float FrameSeconds)
{
    // Current material uses a -0.25 second lower clamp. Root reconstruction only:
    // this does not measure VAT deformation, final velocity pixels, or visibility.
    const double PreviousTime = Now - static_cast<double>(FrameSeconds);
    if (FrameSeconds <= 0.f || Before.AnchorTime > PreviousTime + 0.00001) return;
    const auto RootAt = [PreviousTime](const FMikdashCrowdAgent& State)
    {
        const double Dt = FMath::Clamp(PreviousTime - State.AnchorTime, -0.25,
                                      static_cast<double>(State.HorizonSeconds));
        return FVector(State.Position.X, State.Position.Y, State.GroundZCm)
            + FVector(State.Velocity.X, State.Velocity.Y, State.VelocityZ) * Dt;
    };
    const double Error = FVector::Distance(RootAt(Before), RootAt(After));
    const double HeadingChange = FMath::Abs(FMath::FindDeltaAngleDegrees(Before.HeadingDegrees, After.HeadingDegrees));
    ++MotionAuditSamples;
    MotionAuditRootErrors += Error > 0.1 ? 1 : 0;
    MotionAuditHeadingChanges += HeadingChange > 0.1 ? 1 : 0;
    MotionAuditMaxRootError = FMath::Max(MotionAuditMaxRootError, Error);
    MotionAuditMaxHeadingChange = FMath::Max(MotionAuditMaxHeadingChange, HeadingChange);
    if (MotionAuditLogged < 64 && (Error > 0.1 || HeadingChange > 0.1))
    {
        ++MotionAuditLogged;
        UE_LOG(LogTemp, Display, TEXT("CrowdMotionAuditV1 sample=%d agent=%d zone=%d now=%.9f frame=%.9f oldTime=%.9f newTime=%.9f oldPos=(%.6f,%.6f,%.6f) newPos=(%.6f,%.6f,%.6f) oldVel=(%.6f,%.6f,%.6f) newVel=(%.6f,%.6f,%.6f) oldHorizon=%.6f newHorizon=%.6f oldYaw=%.6f newYaw=%.6f oldIdle=%d newIdle=%d rootErrorCm=%.6f headingDelta=%.6f"),
            MotionAuditSamples, Index, Before.ZoneIndex, Now, FrameSeconds, Before.AnchorTime, After.AnchorTime,
            Before.Position.X, Before.Position.Y, Before.GroundZCm, After.Position.X, After.Position.Y, After.GroundZCm,
            Before.Velocity.X, Before.Velocity.Y, Before.VelocityZ, After.Velocity.X, After.Velocity.Y, After.VelocityZ,
            Before.HorizonSeconds, After.HorizonSeconds, Before.HeadingDegrees, After.HeadingDegrees,
            Before.bIdleAnim, After.bIdleAnim, Error, HeadingChange);
    }
    if (MotionAuditSamples == 4096)
    {
        UE_LOG(LogTemp, Display, TEXT("CrowdMotionAuditV1 complete samples=%d rootErrorsOverPointOneCm=%d headingChangesOverPointOneDegree=%d maxRootErrorCm=%.6f logged=%d maxHeadingChangeDegrees=%.6f scope=social-simulated-updates-root-model-not-pixel-velocity"),
            MotionAuditSamples, MotionAuditRootErrors, MotionAuditHeadingChanges, MotionAuditMaxRootError, MotionAuditLogged, MotionAuditMaxHeadingChange);
    }
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
