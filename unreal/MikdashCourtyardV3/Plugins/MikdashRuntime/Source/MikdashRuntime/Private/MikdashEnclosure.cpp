#include "MikdashEnclosure.h"

#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

using namespace MikdashEnclosure;

namespace
{
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
    // The overlay band is translucent and 1.44 km long on each side; letting it cast shadows
    // would put a grey stripe across the whole Old City for no gain.
    OverlayInstances = MakeInstances(TEXT("OverlayInstances"), false);

    // Defaults that match what is actually in the level. release_enclosure.py overwrites
    // them from its spec, but a hand-placed actor in the editor should still behave.
    ModernBuildingLabelPrefixes = {
        TEXT("SM_JerusalemBuildings_"),      // the 1499 imported OSM context buildings
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
    const FVec2 Centre = ToVec2(CourtCentreUnrealCm);
    const FAabb2 Platform = {{Centre.X - Half, Centre.Y - Half}, {Centre.X + Half, Centre.Y + Half}};
    if (Reading == EMikdashPrecinctReading::Middot500)
    {
        // The Second Temple reading, placed about the Azarah rather than the platform: its
        // clearances are Middot's own, not the book's 500/501.
        return MakeMiddotHarHaBayitSquare(Centre);
    }
    return MakeSquareFromClearances(Platform, static_cast<double>(ClearWestAmot),
                                    static_cast<double>(ClearNorthAmot), PrecinctSideAmot);
}

FVector4 AMikdashEnclosure::GetMeasuredClearancesAmot() const
{
    const double Half = static_cast<double>(CourtPlatformHalfExtentCm);
    const FVec2 Centre = ToVec2(CourtCentreUnrealCm);
    const FAabb2 Platform = {{Centre.X - Half, Centre.Y - Half}, {Centre.X + Half, Centre.Y + Half}};
    const FClearances C = ClearancesOf(GetSquare(), Platform);
    return FVector4(C.WestAmot, C.NorthAmot, C.EastAmot, C.SouthAmot);
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
    return static_cast<float>(AmotToRealMetres(SquareSideAmot(GetSquare()), Opinion->RealCentimetres));
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

    UWorld* World = GetWorld();
    if (World == nullptr) return;

    // Two passes over the actor list would be wasteful; one pass builds both the weak
    // pointers and the engine-free refs, and the ordering is fixed afterwards by sorting on
    // the stable id inside SelectBuildings, so however the editor enumerated actors this run
    // the resulting set is identical.
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (Actor == nullptr || Actor == this) continue;
        const FString Label = Actor->GetActorLabel();
        const bool bExcluded = IsExcludedLabel(Label);
        if (!bExcluded && !IsModernBuildingLabel(Label)) continue;

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
    }
}

int32 AMikdashEnclosure::CountModernBuildingsInside() const
{
    std::vector<long long> Selected;
    const FSelectionCounts Counts =
        SelectBuildings(BuildingRefs, GetSquare(), ESelectionRule::CentroidInside, 0.0, Selected);
    return Counts.Selected;
}

// ---------------------------------------------------------------------------
// Geometry
// ---------------------------------------------------------------------------

void AMikdashEnclosure::BuildRing()
{
    const FSquare Square = GetSquare();
    const double SideLength = SquareSideUnrealCm(Square);
    const double WallHeightCm = AmotToUnrealCm(static_cast<double>(WallHeightAmot));

    WallInstances->ClearInstances();
    GateInstances->ClearInstances();
    CornerInstances->ClearInstances();
    OverlayInstances->ClearInstances();
    WallInstances->SetStaticMesh(WallModuleMesh);
    GateInstances->SetStaticMesh(GateModuleMesh);
    CornerInstances->SetStaticMesh(CornerModuleMesh);
    OverlayInstances->SetStaticMesh(OverlayQuadMesh);

    // The five gates, given as world coordinates on the Temple's own axes and converted to
    // fractions along their side. Doing it this way rather than storing fractions means a
    // change to the square's anchoring moves the gates with it instead of sliding them.
    const FVec2 TempleAxis = ToVec2(CourtCentreUnrealCm);
    std::vector<FGateOpening> Gates;
    auto AddGate = [&](ESide Side, const FVec2& At)
    {
        FGateOpening Gate;
        Gate.Side = static_cast<int>(Side);
        Gate.CentreFractionAlongSide = FractionAlongSide(Square, Gate.Side, At);
        Gate.WidthAmot = 10.0;   // Yechezkel 40:48 / the book pp. 115-117: opening 10 amot
        Gates.push_back(Gate);
    };
    AddGate(ESide::North, TempleAxis);
    AddGate(ESide::East, TempleAxis);
    AddGate(ESide::West, TempleAxis);
    // The two south gates at a third and two thirds of the south wall. The book gives the
    // COUNT per side, not the position; this spacing is the project's assumption and is
    // recorded as such in enclosure-design.json `uncertainties`.
    FVec2 Corners[4];
    SquareCorners(Square, Corners);
    AddGate(ESide::South, FVec2{Corners[3].X + (Corners[2].X - Corners[3].X) / 3.0, Corners[2].Y});
    AddGate(ESide::South, FVec2{Corners[3].X + (Corners[2].X - Corners[3].X) * 2.0 / 3.0, Corners[2].Y});

    const FModuleBudget Budget;
    const FWallPlan Plan = PlanWall(Square, static_cast<double>(WallModuleLengthCm), Gates, 10.0,
                                    Budget, static_cast<double>(OverlaySpacingCm));

    // Wall modules. One instance per surviving segment, placed at the segment's midpoint with
    // the side's outward yaw, so the module's local +X runs along the wall and its +Y outward.
    if (WallModuleMesh != nullptr && Plan.SegmentsPerSide > 0)
    {
        for (int Side = 0; Side < 4; ++Side)
        {
            const FVec2& From = Corners[Side];
            const FVec2& To = Corners[(Side + 1) % 4];
            const double Yaw = SideOutwardYawDegrees(Square, Side);
            for (int Step = 0; Step < Plan.SegmentsPerSide; ++Step)
            {
                const double Start = Plan.SegmentLengthUnrealCm * static_cast<double>(Step);
                if (!SegmentClearsGates(Side, Start, Plan.SegmentLengthUnrealCm, SideLength, Gates,
                                        10.0))
                {
                    continue;
                }
                const double T = (Start + Plan.SegmentLengthUnrealCm * 0.5) / SideLength;
                const FVector Location(From.X + (To.X - From.X) * T, From.Y + (To.Y - From.Y) * T, 0.0);
                // Yaw - 90 turns the outward normal into the along-wall direction.
                WallInstances->AddInstance(FTransform(FRotator(0.0, Yaw - 90.0, 0.0), Location),
                                           /*bWorldSpace=*/true);
            }
        }
    }

    if (GateModuleMesh != nullptr)
    {
        for (std::size_t Index = 0; Index < Gates.size(); ++Index)
        {
            const FGateOpening& Gate = Gates[Index];
            const FVec2& From = Corners[Gate.Side];
            const FVec2& To = Corners[(Gate.Side + 1) % 4];
            const double T = Gate.CentreFractionAlongSide;
            const FVector Location(From.X + (To.X - From.X) * T, From.Y + (To.Y - From.Y) * T, 0.0);
            const double Yaw = SideOutwardYawDegrees(Square, Gate.Side);
            GateInstances->AddInstance(FTransform(FRotator(0.0, Yaw - 90.0, 0.0), Location), true);
        }
    }

    if (CornerModuleMesh != nullptr)
    {
        for (int Index = 0; Index < 4; ++Index)
        {
            CornerInstances->AddInstance(
                FTransform(FRotator(0.0, Square.YawDegrees, 0.0),
                           FVector(Corners[Index].X, Corners[Index].Y, 0.0)), true);
        }
    }

    // The overlay ribbon. Each quad is scaled to exactly bridge to the next sample, so the
    // band is continuous with no overlap - overlapping translucent quads double their own
    // opacity at every seam and read as a dashed line, which is the classic way this effect
    // looks cheap.
    if (OverlayQuadMesh != nullptr)
    {
        std::vector<FBoundarySample> Samples;
        const int PerSide = SampleBoundary(Square, static_cast<double>(OverlaySpacingCm), Samples);
        if (PerSide > 0)
        {
            const double Step = SideLength / static_cast<double>(PerSide);
            for (std::size_t Index = 0; Index < Samples.size(); ++Index)
            {
                const FBoundarySample& Sample = Samples[Index];
                const FVector Location(Sample.PositionUnrealCm.X, Sample.PositionUnrealCm.Y, 0.0);
                const FRotator Rotation(0.0, Sample.OutwardYawDegrees - 90.0, 0.0);
                // Unit quad: X along the wall, Z up. Scale to the sample step and the height.
                const FVector Scale(Step, 1.0, WallHeightCm);
                OverlayInstances->AddInstance(FTransform(Rotation, Location, Scale), true);
            }
        }
    }

    // Corner and gate markers. At 1.44 km a translucent band is a hair on screen; a bright
    // point at each corner and gate is what actually reads at that distance and is what tells
    // a viewer where the far side of the precinct is.
    for (UPointLightComponent* Light : MarkerLights)
    {
        if (Light != nullptr) Light->DestroyComponent();
    }
    MarkerLights.Reset();
    auto AddMarker = [this, WallHeightCm](const FVec2& At)
    {
        UPointLightComponent* Light = NewObject<UPointLightComponent>(this);
        Light->SetupAttachment(GetRootComponent());
        Light->RegisterComponent();
        Light->SetMobility(EComponentMobility::Movable);   // its intensity is animated
        Light->SetWorldLocation(FVector(At.X, At.Y, WallHeightCm));
        Light->SetAttenuationRadius(6000.0f);
        Light->SetCastShadows(false);
        Light->SetIntensity(0.0f);
        MarkerLights.Add(Light);
    };
    for (int Index = 0; Index < 4; ++Index) AddMarker(Corners[Index]);
    for (std::size_t Index = 0; Index < Gates.size(); ++Index)
    {
        const FGateOpening& Gate = Gates[Index];
        const FVec2& From = Corners[Gate.Side];
        const FVec2& To = Corners[(Gate.Side + 1) % 4];
        const double T = Gate.CentreFractionAlongSide;
        AddMarker(FVec2{From.X + (To.X - From.X) * T, From.Y + (To.Y - From.Y) * T});
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

    std::vector<long long> Selected;
    SelectBuildings(BuildingRefs, GetSquare(), ESelectionRule::CentroidInside, 0.0, Selected);

    // Only actors in the selected set are touched, and only their visibility.
    for (int32 Index = 0; Index < BuildingActors.Num(); ++Index)
    {
        AActor* Actor = BuildingActors[Index].Get();
        if (Actor == nullptr) continue;
        if (static_cast<std::size_t>(Index) >= BuildingRefs.size()) continue;
        const FBuildingRef& Ref = BuildingRefs[static_cast<std::size_t>(Index)];
        if (Ref.bExcluded) continue;
        if (!std::binary_search(Selected.begin(), Selected.end(), Ref.Id)) continue;

        const bool bAlreadyRecorded = HiddenBuildings.Contains(Actor);
        if (!bAlreadyRecorded)
        {
            HiddenBuildings.Add(Actor);
            HiddenBuildingsPriorHidden.Add(Actor->IsHidden());
        }
        // NEVER Destroy, NEVER modify the package. Visibility only.
        Actor->SetActorHiddenInGame(bHardHide);
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
    }
    HiddenBuildings.Reset();
    HiddenBuildingsPriorHidden.Reset();
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
    switch (CurrentState)
    {
    case EMikdashPrecinctState::Modern:    SetPrecinctState(EMikdashPrecinctState::Overlay); break;
    case EMikdashPrecinctState::Overlay:   SetPrecinctState(EMikdashPrecinctState::Yechezkel); break;
    case EMikdashPrecinctState::Yechezkel:
    default:                               SetPrecinctState(EMikdashPrecinctState::Modern); break;
    }
}

bool AMikdashEnclosure::IsTransitioning() const
{
    return Transition.DurationSeconds > 0.0 && Transition.ElapsedSeconds < Transition.DurationSeconds;
}

void AMikdashEnclosure::RebuildPrecinct()
{
    GatherModernBuildings();
    BuildRing();
    ApplyWeights(WeightsFor(ToMath(CurrentState)));
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
