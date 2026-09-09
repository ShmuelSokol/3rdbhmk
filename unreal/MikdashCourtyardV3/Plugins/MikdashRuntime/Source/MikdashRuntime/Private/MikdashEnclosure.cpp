#include "MikdashEnclosure.h"

#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

using namespace MikdashEnclosure;

namespace
{
/** The visible Kotel detail layers do not collide. This retained source batch supplies
 * that boundary; keep the entire batch colliding until a selective geometry audit.
 * Full asset identity survives cooking, unlike actor labels. No assets are changed. */
bool ContainsProtectedKotelCollision(const AActor* Actor)
{
    TInlineComponentArray<UStaticMeshComponent*> Components;
    Actor->GetComponents(Components);
    for (const UStaticMeshComponent* Component : Components)
    {
        const UStaticMesh* Mesh = Component->GetStaticMesh();
        if (Mesh != nullptr && Mesh->GetPathName() == TEXT("/Game/MikdashV3/JerusalemContext/Buildings/SM_JerusalemBuildings_Grid_N002_P001.SM_JerusalemBuildings_Grid_N002_P001"))
        {
            return true;
        }
    }
    return false;
}

/** The engine-free enum is the authority; this is the only place the two are related. */
EPrecinctState ToMath(EMikdashPrecinctState State)
{
    switch (State)
    {
    case EMikdashPrecinctState::Yechezkel: return EPrecinctState::Yechezkel;
    case EMikdashPrecinctState::Overlay:   return EPrecinctState::Overlay;
    case EMikdashPrecinctState::Modern:
    default:                               return EPrecinctState::Modern;
    }
}

FVec2 ToVec2(const FVector2D& V) { return FVec2{V.X, V.Y}; }

/** A stable id for an actor, so the hide-set is reproducible run to run. The label is what
 *  the offline receipts key on, so the label is what is hashed - FNV-1a over its UTF-8. */
long long StableIdFromLabel(const FString& Label)
{
    unsigned long long Hash = 1469598103934665603ULL;
    const FTCHARToUTF8 Utf8(*Label);
    const char* Bytes = Utf8.Get();
    for (int32 Index = 0; Index < Utf8.Length(); ++Index)
    {
        Hash ^= static_cast<unsigned char>(Bytes[Index]);
        Hash *= 1099511628211ULL;
    }
    // Keep it positive so it sorts and prints the same way in C++, Python and JSON.
    return static_cast<long long>(Hash & 0x7FFFFFFFFFFFFFFFULL);
}

/** The foundation module is a 100 cm tall box at the baked scale; the wall module 1250 long
 *  and 360 across. Named so the scale arithmetic below reads as geometry, not magic. */
constexpr double FoundationUnitHeightCm = 100.0;
constexpr double ModuleLengthBakedCm = 1250.0;
constexpr double ModuleAcrossBakedCm = 360.0;
constexpr double GateWidthBakedCm = 1560.0;      // 30 amot plus the 4% cornice overhang
constexpr double CornerBakedCm = 556.8;          // 2 x 278.4
}

AMikdashEnclosure::AMikdashEnclosure()
{
    // Ticks only while a dissolve is running; ApplyWeights disables it at the end of one.
    // A precinct sitting in a steady state costs nothing on the game thread.
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = false;

    USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("PrecinctRoot"));
    SetRootComponent(Root);
    Root->SetMobility(EComponentMobility::Static);

    auto MakeInstances = [this, Root](const TCHAR* Name, bool bCastShadow)
    {
        UHierarchicalInstancedStaticMeshComponent* Component =
            CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(Name);
        Component->SetupAttachment(Root);
        Component->SetMobility(EComponentMobility::Static);
        // No collision anywhere on this actor. The precinct is a reading aid; it must never
        // block the walker, never be traced against, and never appear in navmesh generation.
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Component->SetCanEverAffectNavigation(false);
        Component->SetCastShadow(bCastShadow);
        return Component;
    };

    WallInstances = MakeInstances(TEXT("WallInstances"), true);
    GateInstances = MakeInstances(TEXT("GateInstances"), true);
    CornerInstances = MakeInstances(TEXT("CornerInstances"), true);
    FoundationInstances = MakeInstances(TEXT("FoundationInstances"), true);
    // The overlay band is translucent and 1.44 km long on each side; letting it cast shadows
    // would put a grey stripe across the whole Old City for no gain.
    OverlayInstances = MakeInstances(TEXT("OverlayInstances"), false);

    // Defaults that match what is actually in the level. release_enclosure.py overwrites
    // them from its spec, but a hand-placed actor in the editor should still behave.
    ModernBuildingLabelPrefixes = {
        TEXT("SM_JerusalemBuildings_"),      // the 1499 imported OSM context cell actors
        TEXT("RELEASE_OldCityFacades_"),     // the 102 authored facade batches (2106 buildings)
        TEXT("RELEASE_OldCityInfill_"),      // the 88 authored infill batches (1514 buildings)
    };
    ExcludedLabelPrefixes = {
        // THE TRAP. 256 terrain tiles plus 4 FutureMountCut duplicates, each a 400 m square
        // whose AABB swallows the whole Temple court. Excluded by name, before any bounds
        // test runs, because a bounds test cannot tell them from a building.
        TEXT("SM_JerusalemTerrain_"),
        // Hollow Boolean unions. 'Derived union of source outer envelope walls' is 116 wall
        // boxes whose combined AABB is the entire court; treating it as a solid makes every
        // point inside the court look occupied.
        TEXT("Derived union of "),
        // One ISM actor holds 44,793 instances across the whole city; its bounds are the city.
        TEXT("JCTX_ISM_"),
        // Never hide the precinct, or anything the release scripts placed as part of it.
        TEXT("RELEASE_Enclosure"),
    };
}

FSquare AMikdashEnclosure::GetSquare() const
{
    const double Half = static_cast<double>(CourtPlatformHalfExtentCm);
    const double CmPerAmah = static_cast<double>(WorldCmPerAmah);
    const FVec2 Centre = ToVec2(CourtCentreUnrealCm);
    const FAabb2 Platform = {{Centre.X - Half, Centre.Y - Half}, {Centre.X + Half, Centre.Y + Half}};
    if (Reading == EMikdashPrecinctReading::Middot500)
    {
        // The Second Temple reading, placed about the Azarah rather than the platform: its
        // clearances are Middot's own, not the book's 500/501.
        return MakeMiddotHarHaBayitSquare(Centre, CmPerAmah);
    }
    return MakeSquareFromClearances(Platform, static_cast<double>(ClearWestAmot),
                                    static_cast<double>(ClearNorthAmot), PrecinctSideAmot, CmPerAmah);
}

FVector4 AMikdashEnclosure::GetMeasuredClearancesAmot() const
{
    const double Half = static_cast<double>(CourtPlatformHalfExtentCm);
    const FVec2 Centre = ToVec2(CourtCentreUnrealCm);
    const FAabb2 Platform = {{Centre.X - Half, Centre.Y - Half}, {Centre.X + Half, Centre.Y + Half}};
    const FClearances C = ClearancesOf(GetSquare(), Platform, static_cast<double>(WorldCmPerAmah));
    return FVector4(C.WestAmot, C.NorthAmot, C.EastAmot, C.SouthAmot);
}

FVector4 AMikdashEnclosure::GetOuterFacesCm() const
{
    FVec2 Corners[4];
    SquareCorners(GetSquare(), Corners);
    return FVector4(Corners[0].X, Corners[0].Y, Corners[2].X, Corners[2].Y);
}

float AMikdashEnclosure::GetPrecinctSideMetresUnderAmah(const FString& OpinionKey) const
{
    const FTCHARToUTF8 Utf8(*OpinionKey);
    const FAmahOpinion* Opinion = FindAmahOpinion(Utf8.Get());
    if (Opinion == nullptr)
    {
        // No silent default. A caption that says 0 m is a visible bug; a caption that quietly
        // says 1500 m under an opinion nobody holds is an invisible one.
        return 0.0f;
    }
    return static_cast<float>(AmotToRealMetres(
        SquareSideAmot(GetSquare(), static_cast<double>(WorldCmPerAmah)), Opinion->RealCentimetres));
}

FVector2D AMikdashEnclosure::GetWallBaseZRangeCm(int32 Side) const
{
    const int32 Index = ((Side % 4) + 4) % 4;
    return bRingBuilt ? FVector2D(WallBaseZMin[Index], WallBaseZMax[Index]) : FVector2D::ZeroVector;
}

float AMikdashEnclosure::GetDeepestFoundationCm(int32 Side) const
{
    const int32 Index = ((Side % 4) + 4) % 4;
    return bRingBuilt ? static_cast<float>(DeepestFoundation[Index]) : 0.0f;
}

FString AMikdashEnclosure::GetGroundProfileStatus() const
{
    return bGroundFromProfile ? TEXT("profile") : TEXT("level-plane");
}

FVector4 AMikdashEnclosure::GetInstanceCounts() const
{
    return FVector4(static_cast<double>(WallInstances ? WallInstances->GetInstanceCount() : 0),
                    static_cast<double>(GateInstances ? GateInstances->GetInstanceCount() : 0),
                    static_cast<double>(CornerInstances ? CornerInstances->GetInstanceCount() : 0),
                    static_cast<double>(FoundationInstances ? FoundationInstances->GetInstanceCount() : 0));
}

int32 AMikdashEnclosure::GetOverlayInstanceCount() const
{
    return OverlayInstances ? OverlayInstances->GetInstanceCount() : 0;
}

// ---------------------------------------------------------------------------
// Selection
// ---------------------------------------------------------------------------

bool AMikdashEnclosure::IsExcludedLabel(const FString& Label) const
{
    for (const FString& Prefix : ExcludedLabelPrefixes)
    {
        if (!Prefix.IsEmpty() && Label.StartsWith(Prefix, ESearchCase::CaseSensitive)) return true;
    }
    return false;
}

bool AMikdashEnclosure::IsModernBuildingLabel(const FString& Label) const
{
    for (const FString& Prefix : ModernBuildingLabelPrefixes)
    {
        if (!Prefix.IsEmpty() && Label.StartsWith(Prefix, ESearchCase::CaseSensitive)) return true;
    }
    return false;
}

void AMikdashEnclosure::GatherModernBuildings()
{
    BuildingActors.Reset();
    BuildingRefs.clear();
    BuildingInExplicitList.Reset();
    ExplicitFound = ExplicitMissing = ExplicitDuplicated = 0;

    UWorld* World = GetWorld();
    if (World == nullptr) return;

    // The explicit list, minus anything the exclusion guard forbids. Case-sensitive: labels
    // are what the offline receipt recorded, character for character. Mesh names are the
    // same set by another name, for builds where labels are empty.
    TSet<FString> Wanted;
    for (const FString& Label : ExplicitHideLabels)
    {
        if (!Label.IsEmpty() && !IsExcludedLabel(Label)) Wanted.Add(Label);
    }
    TSet<FString> WantedMeshes;
    for (const FString& MeshName : ExplicitHideMeshNames)
    {
        if (!MeshName.IsEmpty()) WantedMeshes.Add(MeshName);
    }
    TMap<FString, int32> Seen;
    TArray<FString> MatchedKeys;   // parallel to BuildingActors: the list entry each actor matched

    // One pass builds the weak pointers, the engine-free refs (for the fallback rule and the
    // count) and the explicit-list membership.
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (Actor == nullptr || Actor == this) continue;
        const FString Label = Actor->GetActorLabel();
        const bool bExcluded = IsExcludedLabel(Label);
        FString MatchedKey;
        if (!bExcluded && Wanted.Contains(Label))
        {
            MatchedKey = Label;
        }
        else if (!bExcluded && WantedMeshes.Num() > 0)
        {
            TArray<UStaticMeshComponent*> MeshComponents;
            Actor->GetComponents<UStaticMeshComponent>(MeshComponents);
            for (const UStaticMeshComponent* Component : MeshComponents)
            {
                if (Component == nullptr || Component->GetStaticMesh() == nullptr) continue;
                const FString MeshName = Component->GetStaticMesh()->GetName();
                if (WantedMeshes.Contains(MeshName))
                {
                    MatchedKey = MeshName;
                    break;
                }
            }
        }
        const bool bExplicit = !MatchedKey.IsEmpty();
        if (!bExcluded && !bExplicit && !IsModernBuildingLabel(Label)) continue;

        FVector Origin = FVector::ZeroVector;
        FVector Extent = FVector::ZeroVector;
        Actor->GetActorBounds(/*bOnlyCollidingComponents=*/false, Origin, Extent);

        FBuildingRef Ref;
        Ref.Id = StableIdFromLabel(Label);
        Ref.CentroidUnrealCm = FVec2{Origin.X, Origin.Y};
        Ref.BoundsUnrealCm = {{Origin.X - Extent.X, Origin.Y - Extent.Y},
                              {Origin.X + Extent.X, Origin.Y + Extent.Y}};
        Ref.bExcluded = bExcluded;
        BuildingRefs.push_back(Ref);
        BuildingActors.Add(Actor);
        BuildingInExplicitList.Add(bExplicit);
        MatchedKeys.Add(MatchedKey);
        if (bExplicit) Seen.FindOrAdd(MatchedKey) += 1;
    }

    // Resolve the list: an entry matched by more than one actor is ambiguous and is REFUSED -
    // every copy stays visible and the count is reported - because hiding "whichever the
    // iterator met" is exactly the kind of quiet nondeterminism the receipt exists to rule
    // out. Resolution is counted over the labels (the receipt's own keys); a label matched
    // through its mesh name counts as found.
    for (const FString& Label : Wanted)
    {
        const int32* Count = Seen.Find(Label);
        if (Count == nullptr)
        {
            // Not matched by label - perhaps by mesh name (cooked build). Any mesh-name key
            // that resolved once stands in for one label; the totals below reconcile.
            ++ExplicitMissing;
        }
        else if (*Count == 1) ++ExplicitFound;
        else ++ExplicitDuplicated;
    }
    int32 MeshMatchedOnce = 0;
    for (const TPair<FString, int32>& Pair : Seen)
    {
        if (!Wanted.Contains(Pair.Key) && Pair.Value == 1) ++MeshMatchedOnce;
    }
    // Labels that were not found by name but whose actor was found by mesh are not missing.
    const int32 Reconciled = FMath::Min(ExplicitMissing, MeshMatchedOnce);
    ExplicitMissing -= Reconciled;
    ExplicitFound += Reconciled;
    for (int32 Index = 0; Index < BuildingActors.Num(); ++Index)
    {
        if (!BuildingInExplicitList[Index]) continue;
        const int32* Count = Seen.Find(MatchedKeys[Index]);
        if (Count != nullptr && *Count != 1) BuildingInExplicitList[Index] = false;
    }
}

void AMikdashEnclosure::SelectedBuildingIndices(TArray<int32>& OutIndices) const
{
    OutIndices.Reset();
    if (ExplicitHideLabels.Num() > 0 || ExplicitHideMeshNames.Num() > 0)
    {
        for (int32 Index = 0; Index < BuildingActors.Num(); ++Index)
        {
            if (BuildingInExplicitList.IsValidIndex(Index) && BuildingInExplicitList[Index]) OutIndices.Add(Index);
        }
        return;
    }
    // Fallback: the geometric centroid rule over actor bounds. Coarser than the offline list
    // (a 100 m cell's bounds centre is not its buildings' centroids) and only used when no
    // list was baked.
    std::vector<long long> Selected;
    SelectBuildings(BuildingRefs, GetSquare(), ESelectionRule::CentroidInside, 0.0, Selected);
    for (int32 Index = 0; Index < BuildingActors.Num(); ++Index)
    {
        if (static_cast<std::size_t>(Index) >= BuildingRefs.size()) break;
        const FBuildingRef& Ref = BuildingRefs[static_cast<std::size_t>(Index)];
        if (Ref.bExcluded) continue;
        if (!IsModernBuildingLabel(BuildingActors[Index].IsValid() ? BuildingActors[Index]->GetActorLabel() : FString())) continue;
        if (std::binary_search(Selected.begin(), Selected.end(), Ref.Id)) OutIndices.Add(Index);
    }
}

int32 AMikdashEnclosure::CountModernBuildingsInside() const
{
    TArray<int32> Indices;
    SelectedBuildingIndices(Indices);
    return Indices.Num();
}

void AMikdashEnclosure::GetHideListResolution(int32& OutFound, int32& OutMissing, int32& OutDuplicated) const
{
    OutFound = ExplicitFound;
    OutMissing = ExplicitMissing;
    OutDuplicated = ExplicitDuplicated;
}

FString AMikdashEnclosure::GetHideSetFingerprint() const
{
    TArray<int32> Indices;
    SelectedBuildingIndices(Indices);
    TArray<FString> Labels;
    for (int32 Index : Indices)
    {
        if (AActor* Actor = BuildingActors[Index].Get()) Labels.Add(Actor->GetActorLabel());
    }
    // Byte order, not FString's case-insensitive order: the receipt sorted these in Python.
    Labels.Sort([](const FString& A, const FString& B) { return FCString::Strcmp(*A, *B) < 0; });
    unsigned long long Hash = 1469598103934665603ULL;
    for (const FString& Label : Labels)
    {
        const FTCHARToUTF8 Utf8(*Label);
        const char* Bytes = Utf8.Get();
        for (int32 Index = 0; Index < Utf8.Length(); ++Index)
        {
            Hash ^= static_cast<unsigned char>(Bytes[Index]);
            Hash *= 1099511628211ULL;
        }
    }
    return FString::Printf(TEXT("%016llx"), Hash);
}

// ---------------------------------------------------------------------------
// Geometry
// ---------------------------------------------------------------------------

FGroundProfile AMikdashEnclosure::MakeGroundProfile() const
{
    FGroundProfile Profile;
    Profile.StepsPerSide = GroundProfileStepsPerSide;
    Profile.HighZUnrealCm.reserve(static_cast<std::size_t>(GroundProfileHighZCm.Num()));
    Profile.LowZUnrealCm.reserve(static_cast<std::size_t>(GroundProfileLowZCm.Num()));
    for (float V : GroundProfileHighZCm) Profile.HighZUnrealCm.push_back(static_cast<double>(V));
    for (float V : GroundProfileLowZCm) Profile.LowZUnrealCm.push_back(static_cast<double>(V));
    return Profile;
}

std::vector<FGateOpening> AMikdashEnclosure::MakeGates(const FSquare& Square) const
{
    // The five gates. E, N and W on the Temple's own axes, given as world coordinates and
    // converted to fractions, so a change to the square's anchoring moves them with it. The
    // east gate at world Y 0 is the axis of the court's east gate and of the walking start,
    // so the tour approach passes through it. The two south gates at a third and two thirds
    // FROM THE SW CORNER. The book gives the COUNT per side (Mishkenei Elyon 196 m.2); every
    // along-wall position is the project's assumption and is recorded as such.
    const FVec2 TempleAxis = ToVec2(CourtCentreUnrealCm);
    FVec2 Corners[4];
    SquareCorners(Square, Corners);
    const double Side = SquareSideUnrealCm(Square);
    std::vector<FGateOpening> Gates;
    auto AddGate = [&](ESide GateSide, const FVec2& At)
    {
        FGateOpening Gate;
        Gate.Side = static_cast<int>(GateSide);
        Gate.CentreFractionAlongSide = FractionAlongSide(Square, Gate.Side, At);
        Gate.WidthAmot = 10.0;   // the book pp. 115-117 after Mishkenei Elyon: opening 10 amot
        Gates.push_back(Gate);
    };
    AddGate(ESide::North, TempleAxis);
    AddGate(ESide::East, TempleAxis);
    AddGate(ESide::South, FVec2{Corners[3].X + Side / 3.0, Corners[3].Y});
    AddGate(ESide::South, FVec2{Corners[3].X + Side * 2.0 / 3.0, Corners[3].Y});
    AddGate(ESide::West, TempleAxis);
    return Gates;
}

void AMikdashEnclosure::BuildRing()
{
    const FSquare Square = GetSquare();
    const double SideLength = SquareSideUnrealCm(Square);
    const double CmPerAmah = static_cast<double>(WorldCmPerAmah);
    const double Scale = ModuleScaleFor(CmPerAmah);
    const double WallHeightCm = AmotToUnrealCm(static_cast<double>(WallHeightAmot), CmPerAmah);
    const double FootingCm = AmotToUnrealCm(static_cast<double>(FoundationFootingAmot), CmPerAmah);
    const double ModuleLengthCm = AmotToUnrealCm(static_cast<double>(WallModuleLengthAmot), CmPerAmah);
    const double OverlaySpacingCm = AmotToUnrealCm(static_cast<double>(OverlaySpacingAmot), CmPerAmah);

    WallInstances->ClearInstances();
    GateInstances->ClearInstances();
    CornerInstances->ClearInstances();
    FoundationInstances->ClearInstances();
    OverlayInstances->ClearInstances();
    WallInstances->SetStaticMesh(WallModuleMesh);
    GateInstances->SetStaticMesh(GateModuleMesh);
    CornerInstances->SetStaticMesh(CornerModuleMesh);
    FoundationInstances->SetStaticMesh(FoundationModuleMesh);
    OverlayInstances->SetStaticMesh(OverlayQuadMesh);

    const FGroundProfile Profile = MakeGroundProfile();
    bGroundFromProfile = GroundProfileValid(Profile);
    if (!bGroundFromProfile && (GroundProfileStepsPerSide > 0 || GroundProfileHighZCm.Num() > 0))
    {
        UE_LOG(LogTemp, Warning, TEXT("AMikdashEnclosure %s: ground profile malformed (%d steps, %d high, %d low); ring placed on the level plane."),
               *GetName(), GroundProfileStepsPerSide, GroundProfileHighZCm.Num(), GroundProfileLowZCm.Num());
    }
    for (int Side = 0; Side < 4; ++Side)
    {
        WallBaseZMin[Side] = 1e300;
        WallBaseZMax[Side] = -1e300;
        DeepestFoundation[Side] = 0.0;
    }

    const std::vector<FGateOpening> Gates = MakeGates(Square);
    FVec2 Corners[4];
    SquareCorners(Square, Corners);
    const FModuleBudget Budget;
    const FWallPlan Plan = PlanWall(Square, ModuleLengthCm, Gates, 10.0, Budget, OverlaySpacingCm, CmPerAmah);

    auto PointAt = [&](int Side, double Fraction)
    {
        const FVec2& From = Corners[Side];
        const FVec2& To = Corners[(Side + 1) % 4];
        return FVec2{From.X + (To.X - From.X) * Fraction, From.Y + (To.Y - From.Y) * Fraction};
    };
    auto AlongYaw = [&](int Side) { return SideOutwardYawDegrees(Square, Side) - 90.0; };
    // One substructure box under a module: its top at the module's plinth, its bottom below
    // the lowest ground the module crosses. XY scale is the module's footprint over the box's
    // baked 1250 x 360.
    auto AddFoundation = [&](const FVec2& At, double Yaw, const FGrounding& G, double LengthCm, double AcrossCm)
    {
        if (FoundationModuleMesh == nullptr || !(G.FoundationDepthUnrealCm > 0.0)) return;
        const FVector Location(At.X, At.Y, G.FoundationBottomZUnrealCm);
        const FVector ScaleXYZ(LengthCm / ModuleLengthBakedCm, AcrossCm / ModuleAcrossBakedCm,
                               G.FoundationDepthUnrealCm / FoundationUnitHeightCm);
        FoundationInstances->AddInstance(FTransform(FRotator(0.0, Yaw, 0.0), Location, ScaleXYZ), /*bWorldSpace=*/true);
    };

    // Wall modules. One instance per surviving segment, at the segment's midpoint, on the
    // side's outward yaw, at the ground the profile gives that segment.
    if (Plan.SegmentsPerSide > 0)
    {
        for (int Side = 0; Side < 4; ++Side)
        {
            const double Yaw = AlongYaw(Side);
            for (int Step = 0; Step < Plan.SegmentsPerSide; ++Step)
            {
                const double Start = Plan.SegmentLengthUnrealCm * static_cast<double>(Step);
                if (!SegmentClearsGates(Side, Start, Plan.SegmentLengthUnrealCm, SideLength, Gates, 10.0, CmPerAmah))
                {
                    continue;
                }
                const double F0 = Start / SideLength;
                const double F1 = (Start + Plan.SegmentLengthUnrealCm) / SideLength;
                const FGrounding G = GroundSpan(Profile, Side, F0, F1, FootingCm);
                const FVec2 At = PointAt(Side, (F0 + F1) * 0.5);
                if (WallModuleMesh != nullptr)
                {
                    WallInstances->AddInstance(FTransform(FRotator(0.0, Yaw, 0.0),
                                                          FVector(At.X, At.Y, G.BaseZUnrealCm),
                                                          FVector(Scale, Scale, Scale)), true);
                }
                AddFoundation(At, Yaw, G, Plan.SegmentLengthUnrealCm, ModuleAcrossBakedCm * Scale);
                WallBaseZMin[Side] = std::min(WallBaseZMin[Side], G.BaseZUnrealCm);
                WallBaseZMax[Side] = std::max(WallBaseZMax[Side], G.BaseZUnrealCm);
                DeepestFoundation[Side] = std::max(DeepestFoundation[Side], G.FoundationDepthUnrealCm);
            }
        }
    }
    for (int Side = 0; Side < 4; ++Side)
    {
        if (WallBaseZMin[Side] > WallBaseZMax[Side]) WallBaseZMin[Side] = WallBaseZMax[Side] = 0.0;
    }

    // Gates. The block is 30 amot wide plus its cornice; it is grounded over that whole width
    // so its threshold sits on the highest ground under it.
    const double GateHalfCm = GateWidthBakedCm * Scale * 0.5;
    for (std::size_t Index = 0; Index < Gates.size(); ++Index)
    {
        const FGateOpening& Gate = Gates[Index];
        const double T = Gate.CentreFractionAlongSide;
        const FGrounding G = GroundSpan(Profile, Gate.Side, T - GateHalfCm / SideLength, T + GateHalfCm / SideLength, FootingCm);
        const FVec2 At = PointAt(Gate.Side, T);
        const double Yaw = AlongYaw(Gate.Side);
        if (GateModuleMesh != nullptr)
        {
            GateInstances->AddInstance(FTransform(FRotator(0.0, Yaw, 0.0), FVector(At.X, At.Y, G.BaseZUnrealCm),
                                                  FVector(Scale, Scale, Scale)), true);
        }
        AddFoundation(At, Yaw, G, GateWidthBakedCm * Scale, ModuleAcrossBakedCm * Scale);
        DeepestFoundation[Gate.Side] = std::max(DeepestFoundation[Gate.Side], G.FoundationDepthUnrealCm);
    }

    // Corners. Station 0 of side i and station 1 of the side before it; the block takes the
    // higher plinth and the lower substructure of the two.
    const double CornerHalfCm = CornerBakedCm * Scale * 0.5;
    for (int Index = 0; Index < 4; ++Index)
    {
        const FGrounding G1 = GroundSpan(Profile, Index, 0.0, CornerHalfCm / SideLength, FootingCm);
        const FGrounding G0 = GroundSpan(Profile, (Index + 3) % 4, 1.0 - CornerHalfCm / SideLength, 1.0, FootingCm);
        FGrounding G = G1;
        G.BaseZUnrealCm = std::max(G0.BaseZUnrealCm, G1.BaseZUnrealCm);
        G.FoundationBottomZUnrealCm = std::min(G0.FoundationBottomZUnrealCm, G1.FoundationBottomZUnrealCm);
        G.FoundationDepthUnrealCm = G.BaseZUnrealCm - G.FoundationBottomZUnrealCm;
        if (CornerModuleMesh != nullptr)
        {
            CornerInstances->AddInstance(
                FTransform(FRotator(0.0, Square.YawDegrees, 0.0),
                           FVector(Corners[Index].X, Corners[Index].Y, G.BaseZUnrealCm),
                           FVector(Scale, Scale, Scale)), true);
        }
        AddFoundation(Corners[Index], Square.YawDegrees, G, CornerBakedCm * Scale, CornerBakedCm * Scale);
        DeepestFoundation[Index] = std::max(DeepestFoundation[Index], G.FoundationDepthUnrealCm);
    }

    // The overlay ribbon. Each quad is scaled to exactly bridge to the next sample, so the
    // band is continuous with no overlap - overlapping translucent quads double their own
    // opacity at every seam and read as a dashed line. It follows the ground like the wall.
    if (OverlayQuadMesh != nullptr)
    {
        std::vector<FBoundarySample> Samples;
        const int PerSide = SampleBoundary(Square, OverlaySpacingCm, Samples);
        if (PerSide > 0)
        {
            const double Step = SideLength / static_cast<double>(PerSide);
            for (std::size_t Index = 0; Index < Samples.size(); ++Index)
            {
                const FBoundarySample& Sample = Samples[Index];
                const double F0 = static_cast<double>(Sample.IndexOnSide) / static_cast<double>(PerSide);
                const double F1 = static_cast<double>(Sample.IndexOnSide + 1) / static_cast<double>(PerSide);
                const FGrounding G = GroundSpan(Profile, Sample.Side, F0, F1, 0.0, 3);
                const FVector Location(Sample.PositionUnrealCm.X, Sample.PositionUnrealCm.Y, G.BaseZUnrealCm);
                const FRotator Rotation(0.0, Sample.OutwardYawDegrees - 90.0, 0.0);
                // Unit slab: X along the wall, Z up. Scale to the sample step and the height.
                const FVector ScaleXYZ(Step, Scale, WallHeightCm);
                OverlayInstances->AddInstance(FTransform(Rotation, Location, ScaleXYZ), true);
            }
        }
    }

    // Corner and gate markers. At 1.44 km a translucent band is a hair on screen; a bright
    // point at each corner and gate is what actually reads at that distance and is what tells
    // a viewer where the far side of the precinct is. Placed a wall height above the ground.
    for (UPointLightComponent* Light : MarkerLights)
    {
        if (Light != nullptr) Light->DestroyComponent();
    }
    MarkerLights.Reset();
    auto AddMarker = [this, WallHeightCm](const FVec2& At, double GroundZ)
    {
        UPointLightComponent* Light = NewObject<UPointLightComponent>(this);
        Light->SetupAttachment(GetRootComponent());
        Light->RegisterComponent();
        Light->SetMobility(EComponentMobility::Movable);   // its intensity is animated
        Light->SetWorldLocation(FVector(At.X, At.Y, GroundZ + WallHeightCm));
        Light->SetAttenuationRadius(6000.0f);
        Light->SetCastShadows(false);
        Light->SetIntensity(0.0f);
        MarkerLights.Add(Light);
    };
    for (int Index = 0; Index < 4; ++Index)
    {
        AddMarker(Corners[Index], SampleGroundHighZ(Profile, Index, 0.0));
    }
    for (std::size_t Index = 0; Index < Gates.size(); ++Index)
    {
        const FGateOpening& Gate = Gates[Index];
        AddMarker(PointAt(Gate.Side, Gate.CentreFractionAlongSide),
                  SampleGroundHighZ(Profile, Gate.Side, Gate.CentreFractionAlongSide));
    }

    if (OverlayMaterial != nullptr)
    {
        OverlayDynamic = UMaterialInstanceDynamic::Create(OverlayMaterial, this);
        OverlayInstances->SetMaterial(0, OverlayDynamic);
    }
    if (WallMaterial != nullptr)
    {
        WallDynamic = UMaterialInstanceDynamic::Create(WallMaterial, this);
        WallInstances->SetMaterial(0, WallDynamic);
        GateInstances->SetMaterial(0, WallDynamic);
        CornerInstances->SetMaterial(0, WallDynamic);
        FoundationInstances->SetMaterial(0, WallDynamic);
    }

    bRingBuilt = true;
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

void AMikdashEnclosure::ApplyWeights(const FStateWeights& Weights)
{
    const bool bShowWall = Weights.SolidWall > 1e-4;
    WallInstances->SetVisibility(bShowWall, true);
    GateInstances->SetVisibility(bShowWall, true);
    CornerInstances->SetVisibility(bShowWall, true);
    FoundationInstances->SetVisibility(bShowWall, true);
    OverlayInstances->SetVisibility(Weights.OverlayBand > 1e-4, true);

    if (WallDynamic != nullptr)
    {
        // The wall fades in as a dissolve rather than as a fade to transparent: a 1.44 km
        // ring of translucent stone is both wrong-looking and expensive to sort.
        WallDynamic->SetScalarParameterValue(TEXT("DissolveAmount"),
                                             static_cast<float>(1.0 - Weights.SolidWall));
    }
    if (OverlayDynamic != nullptr)
    {
        OverlayDynamic->SetScalarParameterValue(TEXT("Opacity"),
                                                static_cast<float>(Weights.OverlayBand * 0.45));
        OverlayDynamic->SetScalarParameterValue(TEXT("Emissive"),
                                                static_cast<float>(Weights.OverlayBand * 12.0));
    }
    for (UPointLightComponent* Light : MarkerLights)
    {
        if (Light != nullptr) Light->SetIntensity(static_cast<float>(Weights.Markers * 40000.0));
    }

    // Buildings. The rule about when a building is hidden outright versus dissolving lives in
    // EnclosureMath.h so that this actor and the release receipt cannot disagree about it.
    const bool bHardHide = ShouldHardHide(Weights.ModernInside);
    const bool bDissolving = NeedsDissolveMaterial(Weights.ModernInside);

    if (!bHardHide && !bDissolving)
    {
        RestoreAllModernBuildings();
        return;
    }

    TArray<int32> Selected;
    SelectedBuildingIndices(Selected);

    // Actor-level collision follows complete hiding in game worlds only. During a
    // partial dissolve, retain the originally configured collision. Editor previews
    // must not bake disabled collision into a subsequently saved map.
    const bool bGameWorld = GetWorld() != nullptr && GetWorld()->IsGameWorld();
    for (int32 Index : Selected)
    {
        AActor* Actor = BuildingActors[Index].Get();
        if (Actor == nullptr) continue;
        int32 RecordedIndex = HiddenBuildings.IndexOfByKey(Actor);
        if (RecordedIndex == INDEX_NONE)
        {
            RecordedIndex = HiddenBuildings.Add(Actor);
            HiddenBuildingsPriorHidden.Add(Actor->IsHidden());
            HiddenBuildingsPriorCollision.Add(Actor->GetActorEnableCollision());
            HiddenBuildingsKeepCollision.Add(ContainsProtectedKotelCollision(Actor));
        }
        Actor->SetActorHiddenInGame(bHardHide || HiddenBuildingsPriorHidden[RecordedIndex]);
        if (bGameWorld)
        {
            Actor->SetActorEnableCollision((!bHardHide || HiddenBuildingsKeepCollision[RecordedIndex])
                                          && HiddenBuildingsPriorCollision[RecordedIndex]);
        }
    }
}

void AMikdashEnclosure::RestoreAllModernBuildings()
{
    for (int32 Index = 0; Index < HiddenBuildings.Num(); ++Index)
    {
        AActor* Actor = HiddenBuildings[Index].Get();
        if (Actor == nullptr) continue;
        const bool bPrior = HiddenBuildingsPriorHidden.IsValidIndex(Index)
                                ? HiddenBuildingsPriorHidden[Index]
                                : false;
        // Restore what it was, not what we assume it was: a building hidden by some other
        // system before we ever saw it must stay hidden.
        Actor->SetActorHiddenInGame(bPrior);
        if (HiddenBuildingsPriorCollision.IsValidIndex(Index))
        {
            Actor->SetActorEnableCollision(HiddenBuildingsPriorCollision[Index]);
        }
    }
    HiddenBuildings.Reset();
    HiddenBuildingsPriorHidden.Reset();
    HiddenBuildingsPriorCollision.Reset();
    HiddenBuildingsKeepCollision.Reset();
}

void AMikdashEnclosure::SetPrecinctStateOver(EMikdashPrecinctState NewState, float Seconds)
{
    if (NewState == CurrentState && !IsTransitioning()) return;
    Transition.From = ToMath(CurrentState);
    Transition.To = ToMath(NewState);
    Transition.ElapsedSeconds = 0.0;
    Transition.DurationSeconds = FMath::Max(0.0f, Seconds);
    CurrentState = NewState;

    if (!(Transition.DurationSeconds > 0.0))
    {
        ApplyWeights(WeightsFor(Transition.To));
        SetActorTickEnabled(false);
    }
    else
    {
        ApplyWeights(BlendWeights(Transition));
        SetActorTickEnabled(true);
    }
    OnPrecinctStateChanged.Broadcast(NewState, Transition.DurationSeconds, HiddenBuildings.Num());
}

void AMikdashEnclosure::SetPrecinctState(EMikdashPrecinctState NewState)
{
    SetPrecinctStateOver(NewState, TransitionSeconds);
}

void AMikdashEnclosure::CyclePrecinctState()
{
    // From the default: one press shows today's city, a second the boundary over it, a third
    // returns to the precinct. All three stay reachable from any of them.
    switch (CurrentState)
    {
    case EMikdashPrecinctState::Yechezkel: SetPrecinctState(EMikdashPrecinctState::Modern); break;
    case EMikdashPrecinctState::Modern:    SetPrecinctState(EMikdashPrecinctState::Overlay); break;
    case EMikdashPrecinctState::Overlay:
    default:                               SetPrecinctState(EMikdashPrecinctState::Yechezkel); break;
    }
}

bool AMikdashEnclosure::IsTransitioning() const
{
    return Transition.DurationSeconds > 0.0 && Transition.ElapsedSeconds < Transition.DurationSeconds;
}

void AMikdashEnclosure::RebuildPrecinct()
{
    // Selection can change on a rebuild. Restore the old selection before replacing
    // it, and do not mistake our own disabled collision for an actor's original state.
    RestoreAllModernBuildings();
    GatherModernBuildings();
    BuildRing();
    ApplyWeights(WeightsFor(ToMath(CurrentState)));
}

void AMikdashEnclosure::MeasureWithoutHiding()
{
    RestoreAllModernBuildings();
    GatherModernBuildings();
    BuildRing();
}

void AMikdashEnclosure::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!IsTransitioning())
    {
        ApplyWeights(WeightsFor(ToMath(CurrentState)));
        SetActorTickEnabled(false);
        return;
    }
    Transition.ElapsedSeconds += static_cast<double>(DeltaSeconds);
    ApplyWeights(BlendWeights(Transition));
}

void AMikdashEnclosure::BeginPlay()
{
    Super::BeginPlay();
    CurrentState = InitialState;
    Transition.From = ToMath(CurrentState);
    Transition.To = ToMath(CurrentState);
    Transition.ElapsedSeconds = 0.0;
    Transition.DurationSeconds = 0.0;
    RebuildPrecinct();
}

void AMikdashEnclosure::EndPlay(const EEndPlayReason::Type Reason)
{
    // Unconditional. Whatever went wrong, the city goes back the way it was found.
    RestoreAllModernBuildings();
    Super::EndPlay(Reason);
}

#if WITH_EDITOR
void AMikdashEnclosure::PostEditChangeProperty(FPropertyChangedEvent& Event)
{
    Super::PostEditChangeProperty(Event);
    if (bRingBuilt) BuildRing();
}
#endif
