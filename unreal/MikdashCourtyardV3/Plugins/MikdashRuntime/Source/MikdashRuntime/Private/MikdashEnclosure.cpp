#include "MikdashEnclosure.h"

#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
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
/** Cooked actors have no editor label. Recover ONLY the three audited building
 * identities from their actual mesh package, reversing hideListMeshNameRule in
 * release_enclosure.spec.json. Never classify by generated actor object name.
 * Unknown, instanced or multi-mesh actors stay outside this selection. The same
 * resolver runs in editor/PIE and packaged builds so native parity is testable. */
FString BuildingIdentityLabel(const AActor* Actor)
{
    if (Actor == nullptr) return FString();
    TInlineComponentArray<UStaticMeshComponent*> Components;
    Actor->GetComponents(Components);
    if (Components.Num() != 1 || Cast<UInstancedStaticMeshComponent>(Components[0]) != nullptr) return FString();
    const UStaticMesh* Mesh = Components[0]->GetStaticMesh();
    if (Mesh == nullptr) return FString();
    const FString AssetPath = Mesh->GetPathName();
    const FString MeshName = Mesh->GetName();
    if (AssetPath == FString(TEXT("/Game/MikdashV3/JerusalemContext/Buildings/")) + MeshName + TEXT(".") + MeshName
        && (MeshName.StartsWith(TEXT("SM_JerusalemBuildings_Grid_"), ESearchCase::CaseSensitive)
            || MeshName.StartsWith(TEXT("SM_JerusalemBuildings_Large_"), ESearchCase::CaseSensitive)))
        return MeshName;
    if (AssetPath != FString(TEXT("/Game/MikdashV3/JerusalemContext/OldCityFacadesV1/Meshes/")) + MeshName + TEXT(".") + MeshName)
        return FString();
    if (MeshName.StartsWith(TEXT("SM_OldCityFacades_Grid_"), ESearchCase::CaseSensitive))
        return FString(TEXT("RELEASE_OldCityFacades_")) + MeshName.RightChop(18);
    if (MeshName.StartsWith(TEXT("SM_OldCityInfill_Grid_"), ESearchCase::CaseSensitive))
        return FString(TEXT("RELEASE_OldCityInfill_")) + MeshName.RightChop(17);
    return FString();
}

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

/** Plaza modules are baked at ProjectCmPerAmah like every other module here. Only the two
 *  paving tiles are ever scaled non-uniformly, and only to clip a partial cell at the ring. */
constexpr double PlazaCellBakedCm = 1250.0;      // 25 amot at 50 cm/amah

/** A super-panel packed into one integer, so a TSet can count distinct panels without
 *  allocating. The grid indices run about -30..+95, so a 1000 offset is generous. */
uint64 PackPanel(const FPlazaPanel& Panel)
{
    auto Field = [](int Value) { return static_cast<uint64>(static_cast<uint32>(Value + 1000) & 0xFFFFu); };
    return (Field(Panel.I0) << 48) | (Field(Panel.J0) << 32) | (Field(Panel.I1) << 16) | Field(Panel.J1);
}

/** Unit outward vector of a side, in world XY. */
FVec2 OutwardOf(const FSquare& Square, int Side)
{
    const double Radians = DegToRad(SideOutwardYawDegrees(Square, Side));
    return FVec2{std::cos(Radians), std::sin(Radians)};
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
    FoundationInstances = MakeInstances(TEXT("FoundationInstances"), true);
    // The overlay band is translucent and 1.44 km long on each side; letting it cast shadows
    // would put a grey stripe across the whole Old City for no gain.
    OverlayInstances = MakeInstances(TEXT("OverlayInstances"), false);

    // The plaza. Deck, way and rib are FLAT and are excluded from shadow casting outright:
    // a ground plane casts nothing, and ShadowDepths was the single most expensive pass in
    // this build before the Nanite pass (8.62 ms - PERFORMANCE-BUDGET.md). That one decision
    // keeps about 20,000 instances out of the virtual shadow map every frame.
    PlazaDeckInstances = MakeInstances(TEXT("PlazaDeckInstances"), false);
    PlazaWayInstances = MakeInstances(TEXT("PlazaWayInstances"), false);
    PlazaRibInstances = MakeInstances(TEXT("PlazaRibInstances"), false);
    PlazaKerbInstances = MakeInstances(TEXT("PlazaKerbInstances"), true);
    PlazaChannelInstances = MakeInstances(TEXT("PlazaChannelInstances"), true);
    PlazaRetainingInstances = MakeInstances(TEXT("PlazaRetainingInstances"), true);
    PlazaScarpInstances = MakeInstances(TEXT("PlazaScarpInstances"), true);
    PlazaStepInstances = MakeInstances(TEXT("PlazaStepInstances"), true);
    // Five floats per paving instance: cos and sin of its panel's course angle, the panel's
    // UV origin in cm on both axes, and its tonal offset. This is what lets ONE draw call
    // lay fourteen thousand tiles in five directions with no two panels starting the pattern
    // in the same place, which is the whole anti-repetition scheme.
    PlazaDeckInstances->NumCustomDataFloats = 5;
    PlazaWayInstances->NumCustomDataFloats = 5;

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

    // Tagged state actors (see HideWhileWallStandsTags in the header). These strings are the
    // tags Scripts/release_precinct_terrain_cut.py and Scripts/release_city_detail.py write
    // onto the actors they place; they are the contract between those scripts and this one.
    HideWhileWallStandsTags = {
        // The real hillside inside the precinct. The quarried twin stands in its place while
        // the deck is there, and the deck is opaque, so nobody ever sees the quarry floor.
        FName(TEXT("PrecinctCutOriginal")),
        // The Western Wall Plaza cut is a MODERN feature whose decks sit 11 m BELOW the
        // precinct deck: buried and pointless in Yechezkel, so it is the opposite sense.
        FName(TEXT("KotelPlazaCutTwin")),
        // Roofscape that decorates the buildings the precinct hides. Left standing it floats
        // over the deck with nothing under it.
        FName(TEXT("CityDetailZone_Precinct")),
    };
    HideWhileModernCityStandsTags = {
        // Present-day Jerusalem must not have a quarry in it.
        FName(TEXT("PrecinctCutTwin")),
        // While today's city stands, the Kotel-cut twin of this tile is the one on show.
        FName(TEXT("KotelPlazaCutOriginal")),
        // The ways UP from the modern street onto the deck - RELEASE_PrecinctApproachV1,
        // placed by Scripts/release_precinct_approaches.py. They are part of the built
        // precinct and follow the plaza exactly: present in YECHEZKEL, gone in MODERN (which
        // must restore today's city untouched) and gone in OVERLAY (which exists to show the
        // standing city under the boundary line). They cannot be reached any other way:
        // BuildingIdentityLabel returns an EMPTY label for any mesh outside the two audited
        // building folders, and PlazaV1 meshes are outside both - which is exactly the
        // narrowness that keeps the audited building hide list from drifting, so it is
        // preserved rather than widened, and the actor is driven by TAG like every other
        // whole-actor member of a state.
        FName(TEXT("PrecinctApproachV1")),
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

void AMikdashEnclosure::ConsiderStateTaggedActor(AActor* Actor)
{
    if (Actor == nullptr || Actor->Tags.Num() == 0) return;
    bool bHideWithWall = false;
    bool bHideWithCity = false;
    for (const FName& Tag : Actor->Tags)
    {
        if (HideWhileWallStandsTags.Contains(Tag)) bHideWithWall = true;
        if (HideWhileModernCityStandsTags.Contains(Tag)) bHideWithCity = true;
    }
    if (!bHideWithWall && !bHideWithCity) return;
    StateTaggedActors.Add(Actor);
    StateTaggedHideWithWall.Add(bHideWithWall);
    StateTaggedHideWithCity.Add(bHideWithCity);
    StateTaggedPriorHidden.Add(Actor->IsHidden());
    StateTaggedPriorCollision.Add(Actor->GetActorEnableCollision());
}

void AMikdashEnclosure::ApplyStateTaggedActors(bool bWallStands)
{
    // Collision follows visibility here rather than a recorded prior, and that is the point:
    // these actors are placed on disk in ONE state's configuration, so their "prior" is the
    // Yechezkel answer, not a neutral one. An invisible hillside must never block a walker on
    // the deck, and a visible one must always carry the walker. Editor worlds are left alone
    // so a preview cannot bake disabled collision into a map that is later saved.
    const bool bGameWorld = GetWorld() != nullptr && GetWorld()->IsGameWorld();
    for (int32 Index = 0; Index < StateTaggedActors.Num(); ++Index)
    {
        AActor* Actor = StateTaggedActors[Index].Get();
        if (Actor == nullptr) continue;
        const bool bHide = bWallStands ? StateTaggedHideWithWall[Index]
                                       : StateTaggedHideWithCity[Index];
        Actor->SetActorHiddenInGame(bHide);
        if (bGameWorld) Actor->SetActorEnableCollision(!bHide);
    }
}

void AMikdashEnclosure::RestoreStateTaggedActors()
{
    const bool bGameWorld = GetWorld() != nullptr && GetWorld()->IsGameWorld();
    for (int32 Index = 0; Index < StateTaggedActors.Num(); ++Index)
    {
        AActor* Actor = StateTaggedActors[Index].Get();
        if (Actor == nullptr) continue;
        if (StateTaggedPriorHidden.IsValidIndex(Index))
        {
            Actor->SetActorHiddenInGame(StateTaggedPriorHidden[Index]);
        }
        if (bGameWorld && StateTaggedPriorCollision.IsValidIndex(Index))
        {
            Actor->SetActorEnableCollision(StateTaggedPriorCollision[Index]);
        }
    }
    StateTaggedActors.Reset();
    StateTaggedHideWithWall.Reset();
    StateTaggedHideWithCity.Reset();
    StateTaggedPriorHidden.Reset();
    StateTaggedPriorCollision.Reset();
}

void AMikdashEnclosure::GetStateTaggedCounts(int32& OutMatched, int32& OutHiddenWithWall,
                                             int32& OutHiddenWithCity) const
{
    OutMatched = StateTaggedActors.Num();
    OutHiddenWithWall = 0;
    OutHiddenWithCity = 0;
    for (int32 Index = 0; Index < StateTaggedActors.Num(); ++Index)
    {
        if (StateTaggedHideWithWall.IsValidIndex(Index) && StateTaggedHideWithWall[Index])
        {
            ++OutHiddenWithWall;
        }
        if (StateTaggedHideWithCity.IsValidIndex(Index) && StateTaggedHideWithCity[Index])
        {
            ++OutHiddenWithCity;
        }
    }
}

void AMikdashEnclosure::GatherModernBuildings()
{
    StateTaggedActors.Reset();
    StateTaggedHideWithWall.Reset();
    StateTaggedHideWithCity.Reset();
    StateTaggedPriorHidden.Reset();
    StateTaggedPriorCollision.Reset();
    BuildingActors.Reset();
    BuildingIdentityLabels.Reset();
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
        // Tags are read FIRST, and deliberately: the empty label two lines below is exactly
        // why a terrain twin or a roofscape batch can never enter the building hide list.
        ConsiderStateTaggedActor(Actor);
        const FString Label = BuildingIdentityLabel(Actor);
        if (Label.IsEmpty()) continue; // no unverified actor-name or mesh-name fallback
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
        BuildingIdentityLabels.Add(Label);
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
        if (!BuildingActors[Index].IsValid() || !BuildingIdentityLabels.IsValidIndex(Index)
            || !IsModernBuildingLabel(BuildingIdentityLabels[Index])) continue;
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
        if (BuildingActors[Index].IsValid() && BuildingIdentityLabels.IsValidIndex(Index)) Labels.Add(BuildingIdentityLabels[Index]);
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

    // THE WALL STANDS ON THE PLAZA. With a deck present a module's plinth is the HIGHER of
    // the deck and the ground outside it (PlazaWallBaseZUnrealCm): on a fill side that is the
    // deck, and the retaining wall below carries it; on a cut side it is the outside grade,
    // and the wall stands on the crest of the scarp with the plaza a storey below its inner
    // face. Without a deck this is a no-op and the wall grounds exactly as it always did.
    //
    // The substructure is capped at the deck underside for the same reason: below that there
    // is no ground, only the retaining ring, and a foundation box reaching a hundred metres
    // into a void would be visible from the Kidron as a row of dropped teeth.
    const bool bDeck = PlazaEnabled();
    const double DeckTopZ = PlazaDeckTopZUnrealCm(CmPerAmah);
    const double DeckUndersideZ = PlazaDeckUndersideZUnrealCm(CmPerAmah);
    auto SeatOnDeck = [&](FGrounding& G)
    {
        if (!bDeck) return;
        G.BaseZUnrealCm = PlazaWallBaseZUnrealCm(G.GroundHighZUnrealCm, DeckTopZ, true);
        G.FoundationBottomZUnrealCm = std::max(G.FoundationBottomZUnrealCm, DeckUndersideZ);
        G.FoundationDepthUnrealCm = std::max(0.0, G.BaseZUnrealCm - G.FoundationBottomZUnrealCm);
    };
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
                FGrounding G = GroundSpan(Profile, Side, F0, F1, FootingCm);
                SeatOnDeck(G);
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
        FGrounding G = GroundSpan(Profile, Gate.Side, T - GateHalfCm / SideLength, T + GateHalfCm / SideLength, FootingCm);
        SeatOnDeck(G);
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
        FGrounding G1 = GroundSpan(Profile, Index, 0.0, CornerHalfCm / SideLength, FootingCm);
        FGrounding G0 = GroundSpan(Profile, (Index + 3) % 4, 1.0 - CornerHalfCm / SideLength, 1.0, FootingCm);
        SeatOnDeck(G1);
        SeatOnDeck(G0);
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
                // The overlay band is drawn over the STANDING modern city, so it follows the
                // real ground and never the deck: in OVERLAY there is no deck to stand on.
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

    BuildPlaza(Square, Profile);

    bRingBuilt = true;
}

// ---------------------------------------------------------------------------
// The plaza
// ---------------------------------------------------------------------------

bool AMikdashEnclosure::PlazaEnabled() const
{
    return bBuildPlaza && PlazaDeckTileMesh != nullptr;
}

/** The deck, its processional ways, its panel ribs, its kerbs, its drainage, its retaining
 *  and scarp faces and its gate stairs.
 *
 *  EVERY POSITION HERE COMES OUT OF EnclosureMath.h section 6b, and so does the copy in
 *  Scripts/create_precinct_plaza.py. That is not tidiness: the plaza is 34,000 instances laid
 *  out by a hash function, and the only way to know that the receipt describes what the
 *  runtime built is for both to call the same arithmetic and for the release script to
 *  compare the counts afterwards. A cached panel table would break that the first time one
 *  side rebuilt and the other did not, which is why PlazaPanelAt walks from the root instead.
 *
 *  The retaining stacks are driven by the SAME ground profile the wall was just grounded on,
 *  passed in rather than re-sampled, because two independent samplings of the same terrain is
 *  exactly how a wall ends up floating a few centimetres above its own retaining wall.
 */
void AMikdashEnclosure::BuildPlaza(const FSquare& Square, const FGroundProfile& Profile)
{
    UHierarchicalInstancedStaticMeshComponent* const Components[8] = {
        PlazaDeckInstances, PlazaWayInstances, PlazaRibInstances, PlazaKerbInstances,
        PlazaChannelInstances, PlazaRetainingInstances, PlazaScarpInstances, PlazaStepInstances};
    UStaticMesh* const Meshes[8] = {
        PlazaDeckTileMesh, PlazaWayTileMesh, PlazaRibMesh, PlazaKerbMesh,
        PlazaChannelMesh, PlazaRetainingBandMesh, PlazaRetainingBandMesh, PlazaStepMesh};
    for (int Index = 0; Index < 8; ++Index)
    {
        if (Components[Index] == nullptr) continue;
        Components[Index]->ClearInstances();
        Components[Index]->SetStaticMesh(Meshes[Index]);
    }
    for (int Side = 0; Side < 4; ++Side)
    {
        PlazaRetainingMax[Side] = 0.0;
        PlazaScarpMax[Side] = 0.0;
    }
    PlazaCellsX = PlazaCellsY = PlazaPanels = 0;

    if (!bBuildPlaza)
    {
        PlazaStatus = TEXT("disabled");
        return;
    }
    if (PlazaDeckTileMesh == nullptr)
    {
        // The honest failure mode for a missing asset: say so, build nothing, and leave the
        // wall standing on the terrain exactly as it did before the plaza existed.
        PlazaStatus = TEXT("no-deck-mesh");
        return;
    }

    const double CmPerAmah = static_cast<double>(WorldCmPerAmah);
    const double Scale = ModuleScaleFor(CmPerAmah);
    const FPlazaGrid Grid = PlanPlazaGrid(Square, static_cast<double>(WallThicknessAmot), CmPerAmah);
    if (Grid.CellsX() <= 0 || Grid.CellsY() <= 0)
    {
        PlazaStatus = TEXT("empty-grid");
        return;
    }
    const double DeckZ = Grid.DeckTopZUnrealCm;
    const double CellCm = Grid.CellUnrealCm;
    const double WallThickCm = AmotToUnrealCm(static_cast<double>(WallThicknessAmot), CmPerAmah);
    const double SideLength = SquareSideUnrealCm(Square);
    PlazaCellsX = Grid.CellsX();
    PlazaCellsY = Grid.CellsY();

    FVec2 Corners[4];
    SquareCorners(Square, Corners);
    auto PointAt = [&](int Side, double Fraction)
    {
        const FVec2& From = Corners[Side];
        const FVec2& To = Corners[(Side + 1) % 4];
        return FVec2{From.X + (To.X - From.X) * Fraction, From.Y + (To.Y - From.Y) * Fraction};
    };

    // --- the five processional ways ---------------------------------------------------
    // MakePlazaWays and PlazaCellIsWay live in EnclosureMath.h so that this actor, the
    // standalone test and Scripts/create_precinct_plaza.py cannot lay them differently.
    const std::vector<FGateOpening> Gates = MakeGates(Square);
    std::vector<FPlazaWay> Ways;
    MakePlazaWays(Square, Grid, static_cast<double>(CourtPlatformHalfExtentCm), Gates, Ways);

    // --- the deck field, the ways and the panel ribs -----------------------------------
    TSet<uint64> Panels;
    Panels.Reserve(1024);
    for (int I = Grid.I0; I < Grid.I1; ++I)
    {
        for (int J = Grid.J0; J < Grid.J1; ++J)
        {
            double X0, Y0, X1, Y1;
            PlazaCellExtent(Grid, I, J, X0, Y0, X1, Y1);
            const double DX = X1 - X0;
            const double DY = Y1 - Y0;
            if (!(DX > 0.0) || !(DY > 0.0)) continue;

            const FPlazaPanel Panel = PlazaPanelAt(Grid, I, J);
            Panels.Add(PackPanel(Panel));
            const int Course = PlazaPanelCourseIndex(Grid, Panel);
            const double Radians = DegToRad(PlazaCourseAngleDegrees(Course));
            double OriginU = 0.0, OriginV = 0.0;
            PlazaPanelUvOriginAmot(Panel, OriginU, OriginV);

            const bool bWay = PlazaCellIsWay(Ways, I, J);
            UHierarchicalInstancedStaticMeshComponent* Target = bWay ? PlazaWayInstances : PlazaDeckInstances;
            UStaticMesh* Mesh = bWay ? PlazaWayTileMesh.Get() : PlazaDeckTileMesh.Get();
            if (Target != nullptr && Mesh != nullptr)
            {
                const FVector Location((X0 + X1) * 0.5, (Y0 + Y1) * 0.5, DeckZ);
                const FVector ScaleXYZ(DX / PlazaCellBakedCm, DY / PlazaCellBakedCm, Scale);
                const int32 At = Target->AddInstance(
                    FTransform(FRotator(0.0, Square.YawDegrees, 0.0), Location, ScaleXYZ), true);
                // cos, sin, the panel's UV origin in cm on both axes, and the tonal offset.
                Target->SetCustomDataValue(At, 0, static_cast<float>(std::cos(Radians)), false);
                Target->SetCustomDataValue(At, 1, static_cast<float>(std::sin(Radians)), false);
                Target->SetCustomDataValue(At, 2, static_cast<float>(AmotToUnrealCm(OriginU, CmPerAmah)), false);
                Target->SetCustomDataValue(At, 3, static_cast<float>(AmotToUnrealCm(OriginV, CmPerAmah)), false);
                Target->SetCustomDataValue(At, 4, static_cast<float>(PlazaTintAt(I, J)), false);
            }

            // A rib wherever this cell's panel differs from the one west or north of it. The
            // ribs ARE the panel outlines, so no separate edge list can go stale.
            if (PlazaRibInstances != nullptr && PlazaRibMesh != nullptr)
            {
                if (I > Grid.I0 && !PlazaSamePanel(PlazaPanelAt(Grid, I - 1, J), Panel))
                {
                    PlazaRibInstances->AddInstance(
                        FTransform(FRotator(0.0, Square.YawDegrees + 90.0, 0.0),
                                   FVector(X0, (Y0 + Y1) * 0.5, DeckZ),
                                   FVector(DY / PlazaCellBakedCm, Scale, Scale)), true);
                }
                if (J > Grid.J0 && !PlazaSamePanel(PlazaPanelAt(Grid, I, J - 1), Panel))
                {
                    PlazaRibInstances->AddInstance(
                        FTransform(FRotator(0.0, Square.YawDegrees, 0.0),
                                   FVector((X0 + X1) * 0.5, Y0, DeckZ),
                                   FVector(DX / PlazaCellBakedCm, Scale, Scale)), true);
                }
            }
        }
    }
    PlazaPanels = Panels.Num();

    // --- way kerbs: both long edges of every way ---------------------------------------
    if (PlazaKerbInstances != nullptr && PlazaKerbMesh != nullptr)
    {
        for (const FPlazaWay& Run : Ways)
        {
            for (int Edge = 0; Edge < 2; ++Edge)
            {
                const double Line = static_cast<double>(Edge == 0 ? Run.Band0 : Run.Band1) * CellCm;
                for (int Along = Run.Along0; Along < Run.Along1; ++Along)
                {
                    double X0, Y0, X1, Y1;
                    PlazaCellExtent(Grid, Run.bNorthSouth ? Run.Band0 : Along,
                                    Run.bNorthSouth ? Along : Run.Band0, X0, Y0, X1, Y1);
                    if (Run.bNorthSouth)
                    {
                        PlazaKerbInstances->AddInstance(
                            FTransform(FRotator(0.0, Square.YawDegrees + 90.0, 0.0),
                                       FVector(Line, (Y0 + Y1) * 0.5, DeckZ),
                                       FVector((Y1 - Y0) / PlazaCellBakedCm, Scale, Scale)), true);
                    }
                    else
                    {
                        PlazaKerbInstances->AddInstance(
                            FTransform(FRotator(0.0, Square.YawDegrees, 0.0),
                                       FVector((X0 + X1) * 0.5, Line, DeckZ),
                                       FVector((X1 - X0) / PlazaCellBakedCm, Scale, Scale)), true);
                    }
                }
            }
        }
    }

    // --- drainage: a perimeter ring, then cross channels on a non-periodic stride -------
    // Culverted, not cut, where a channel meets a processional way: a road with an open
    // trench across it is not a road. The culvert itself is not modelled, and the receipt
    // counts how many modules were left out for it.
    if (PlazaChannelInstances != nullptr && PlazaChannelMesh != nullptr)
    {
        const double Inset = AmotToUnrealCm(PlazaPerimeterChannelInsetAmot, CmPerAmah);
        for (int I = Grid.I0; I < Grid.I1; ++I)
        {
            double X0, Y0, X1, Y1;
            PlazaCellExtent(Grid, I, Grid.J0, X0, Y0, X1, Y1);
            if (!(X1 > X0)) continue;
            const FVector ScaleXYZ((X1 - X0) / PlazaCellBakedCm, Scale, Scale);
            const FRotator Rotation(0.0, Square.YawDegrees, 0.0);
            PlazaChannelInstances->AddInstance(
                FTransform(Rotation, FVector((X0 + X1) * 0.5, Grid.YMinUnrealCm + Inset, DeckZ), ScaleXYZ), true);
            PlazaChannelInstances->AddInstance(
                FTransform(Rotation, FVector((X0 + X1) * 0.5, Grid.YMaxUnrealCm - Inset, DeckZ), ScaleXYZ), true);
        }
        for (int J = Grid.J0; J < Grid.J1; ++J)
        {
            double X0, Y0, X1, Y1;
            PlazaCellExtent(Grid, Grid.I0, J, X0, Y0, X1, Y1);
            if (!(Y1 > Y0)) continue;
            const FVector ScaleXYZ((Y1 - Y0) / PlazaCellBakedCm, Scale, Scale);
            const FRotator Rotation(0.0, Square.YawDegrees + 90.0, 0.0);
            PlazaChannelInstances->AddInstance(
                FTransform(Rotation, FVector(Grid.XMinUnrealCm + Inset, (Y0 + Y1) * 0.5, DeckZ), ScaleXYZ), true);
            PlazaChannelInstances->AddInstance(
                FTransform(Rotation, FVector(Grid.XMaxUnrealCm - Inset, (Y0 + Y1) * 0.5, DeckZ), ScaleXYZ), true);
        }
        for (int K = Grid.I0 + 1; K < Grid.I1; ++K)
        {
            if (!PlazaHasChannelLine(Grid.I0, K, Grid.I1)) continue;
            for (int J = Grid.J0; J < Grid.J1; ++J)
            {
                if (PlazaCellIsWay(Ways, K, J) || PlazaCellIsWay(Ways, K - 1, J)) continue;
                double X0, Y0, X1, Y1;
                PlazaCellExtent(Grid, K, J, X0, Y0, X1, Y1);
                if (!(Y1 > Y0)) continue;
                PlazaChannelInstances->AddInstance(
                    FTransform(FRotator(0.0, Square.YawDegrees + 90.0, 0.0),
                               FVector(static_cast<double>(K) * CellCm, (Y0 + Y1) * 0.5, DeckZ),
                               FVector((Y1 - Y0) / PlazaCellBakedCm, Scale, Scale)), true);
            }
        }
        for (int K = Grid.J0 + 1; K < Grid.J1; ++K)
        {
            if (!PlazaHasChannelLine(Grid.J0, K, Grid.J1)) continue;
            for (int I = Grid.I0; I < Grid.I1; ++I)
            {
                if (PlazaCellIsWay(Ways, I, K) || PlazaCellIsWay(Ways, I, K - 1)) continue;
                double X0, Y0, X1, Y1;
                PlazaCellExtent(Grid, I, K, X0, Y0, X1, Y1);
                if (!(X1 > X0)) continue;
                PlazaChannelInstances->AddInstance(
                    FTransform(FRotator(0.0, Square.YawDegrees, 0.0),
                               FVector((X0 + X1) * 0.5, static_cast<double>(K) * CellCm, DeckZ),
                               FVector((X1 - X0) / PlazaCellBakedCm, Scale, Scale)), true);
            }
        }
    }

    // --- retaining (fill) and scarp (cut), module by module round the ring --------------
    // Two faces of the same wall. Where the ground is BELOW the deck the retaining wall runs
    // down from the deck edge, its outer face coplanar with the precinct's own outer face, so
    // the 3000 amot are measured where the wall stands - as Yechezkel 42:15 measures them,
    // from outside. Where the ground is ABOVE the deck the plaza is a cut and the same bands
    // rise from the deck to the outside grade as a revetment, facing inward, with the wall on
    // the crest. A single module can carry both when the ground crosses the deck under it.
    const double BandHeightCm = AmotToUnrealCm(PlazaRetainingBandHeightAmot, CmPerAmah);
    const int SegmentsPerSide = (SideLength > 0.0 && CellCm > 0.0)
        ? std::max(1, static_cast<int>(std::floor(SideLength / CellCm + 0.5))) : 0;
    for (int Side = 0; Side < 4 && SegmentsPerSide > 0; ++Side)
    {
        const FVec2 Out = OutwardOf(Square, Side);
        const double Yaw = SideOutwardYawDegrees(Square, Side) - 90.0;
        for (int Step = 0; Step < SegmentsPerSide; ++Step)
        {
            const double F0 = static_cast<double>(Step) / static_cast<double>(SegmentsPerSide);
            const double F1 = static_cast<double>(Step + 1) / static_cast<double>(SegmentsPerSide);
            const FGrounding G = GroundSpan(Profile, Side, F0, F1, 0.0);
            const FVec2 At = PointAt(Side, (F0 + F1) * 0.5);

            const double Fill = DeckZ - G.GroundLowZUnrealCm;
            if (Fill > 0.0 && PlazaRetainingInstances != nullptr && PlazaRetainingBandMesh != nullptr)
            {
                const int Bands = PlazaBandCount(Fill, CmPerAmah);
                // cp19 wash. Not on the first or last module of a side: the battered bands of two
                // sides leave an open notch at each corner, and a rolled band's end would show in it.
                const bool bWashHere = bPlazaLedgeWash && Step > 0 && Step < SegmentsPerSide - 1;
                const double WashInset = PlazaLedgeWashOriginInsetUnrealCm(BandHeightCm);
                for (int Band = 0; Band < Bands; ++Band)
                {
                    const double Batter = PlazaBandBatterUnrealCm(Band, CmPerAmah);
                    PlazaRetainingInstances->AddInstance(
                        FTransform(FRotator(0.0, Yaw, 0.0),
                                   FVector(At.X + Out.X * Batter, At.Y + Out.Y * Batter,
                                           DeckZ - static_cast<double>(Band) * BandHeightCm),
                                   FVector(Scale, Scale, Scale)), true);
                    if (bWashHere && PlazaBandIsLedge(Band))
                    {
                        // Roll -45 (FRotator: positive roll turns local +Y DOWN) tips the band's outer
                        // face up-and-out; its top-outer arris goes WashInset in and up from the
                        // ledge's outer arris, so the rolled face ends exactly on that arris.
                        const double LedgeZ = DeckZ - static_cast<double>(Band) * BandHeightCm;
                        PlazaRetainingInstances->AddInstance(
                            FTransform(FRotator(0.0, Yaw, -PlazaLedgeWashDegrees),
                                       FVector(At.X + Out.X * (Batter - WashInset),
                                               At.Y + Out.Y * (Batter - WashInset),
                                               LedgeZ + WashInset),
                                       FVector(Scale, Scale, Scale)), true);
                    }
                }
                PlazaRetainingMax[Side] = std::max(PlazaRetainingMax[Side], Fill);
            }

            const double Cut = G.GroundHighZUnrealCm - DeckZ;
            if (Cut > 0.0 && PlazaScarpInstances != nullptr && PlazaRetainingBandMesh != nullptr)
            {
                const int Bands = PlazaBandCount(Cut, CmPerAmah);
                const FVec2 Inner{At.X - Out.X * WallThickCm, At.Y - Out.Y * WallThickCm};
                for (int Band = 0; Band < Bands; ++Band)
                {
                    const double Batter = PlazaBandBatterUnrealCm(Band, CmPerAmah);
                    // Yaw + 180 turns the band's face inward, toward the plaza, with its body
                    // in the hillside: a revetment, not a free-standing wall.
                    PlazaScarpInstances->AddInstance(
                        FTransform(FRotator(0.0, Yaw + 180.0, 0.0),
                                   FVector(Inner.X + Out.X * Batter, Inner.Y + Out.Y * Batter,
                                           DeckZ + static_cast<double>(Band + 1) * BandHeightCm),
                                   FVector(Scale, Scale, Scale)), true);
                }
                PlazaScarpMax[Side] = std::max(PlazaScarpMax[Side], Cut);
            }
        }
    }

    // --- gate stairs, INSIDE the ring ---------------------------------------------------
    // Only where the gate threshold stands above the deck, which is the cut sides: the east
    // gate is about forty metres up on the Mount of Olives slope and needs a monumental
    // flight down to the plaza, the west gate a short one. Where the deck stands ABOVE the
    // outside ground - up to sixty metres at the south-west gate - the approach is OUTSIDE
    // the precinct, over modern buildings this project deliberately leaves standing, and it
    // is recorded as unbuilt rather than invented. See the limitations in the receipt.
    if (PlazaStepInstances != nullptr && PlazaStepMesh != nullptr && SideLength > 0.0)
    {
        const double Riser = AmotToUnrealCm(PlazaStepRiserAmot, CmPerAmah);
        const double Tread = AmotToUnrealCm(PlazaStepTreadAmot, CmPerAmah);
        const int LandingUnits = std::max(1, static_cast<int>(std::floor(
            PlazaLandingDepthAmot / PlazaStepTreadAmot + 0.5)));
        const double HalfCell = CellCm * 0.5 / SideLength;
        for (std::size_t Index = 0; Index < Gates.size(); ++Index)
        {
            const FGateOpening& Gate = Gates[Index];
            const double T = Gate.CentreFractionAlongSide;
            const FGrounding G = GroundSpan(Profile, Gate.Side,
                                            std::max(0.0, T - HalfCell), std::min(1.0, T + HalfCell), 0.0);
            const double Base = PlazaWallBaseZUnrealCm(G.GroundHighZUnrealCm, DeckZ, true);
            const int Steps = PlazaFlightSteps(Base - DeckZ, CmPerAmah);
            if (Steps <= 0) continue;
            const int Landings = PlazaFlightLandings(Steps);
            const FVec2 At = PointAt(Gate.Side, T);
            const FVec2 Out = OutwardOf(Square, Gate.Side);
            // The SAME convention the retaining bands use forty lines up, and for the same
            // reason. SM_PlazaV1_Step is 50 amot along local +X - the WIDTH of the flight -
            // and 2 amot along local +Y, which is the tread and the direction of ascent. A UE
            // yaw t maps local +X to (cos t, sin t), so the bare outward yaw laid the fifty
            // amot ALONG -Out, the direction this loop travels, and ran the treads across the
            // flight instead of across the walker. Minus ninety puts the width along the side
            // and points local +Y outward, which is uphill: the flight descends from the gate.
            const double Yaw = SideOutwardYawDegrees(Square, Gate.Side) - 90.0;
            const FVector ScaleXYZ(Scale, Scale, Scale);
            double Distance = WallThickCm;
            double Z = Base;
            int LandingsPlaced = 0;
            for (int Step = 0; Step < Steps; ++Step)
            {
                Z -= Riser;
                Distance += Tread;
                PlazaStepInstances->AddInstance(
                    FTransform(FRotator(0.0, Yaw, 0.0),
                               FVector(At.X - Out.X * Distance, At.Y - Out.Y * Distance, Z),
                               ScaleXYZ), true);
                if ((Step + 1) % PlazaStepsPerFlight == 0 && LandingsPlaced < Landings)
                {
                    for (int Unit = 0; Unit < LandingUnits; ++Unit)
                    {
                        Distance += Tread;
                        PlazaStepInstances->AddInstance(
                            FTransform(FRotator(0.0, Yaw, 0.0),
                                       FVector(At.X - Out.X * Distance, At.Y - Out.Y * Distance, Z),
                                       ScaleXYZ), true);
                    }
                    ++LandingsPlaced;
                }
            }
        }
    }

    if (PlazaPavingMaterial != nullptr && PlazaDeckInstances != nullptr)
    {
        PlazaDeckInstances->SetMaterial(0, PlazaPavingMaterial);
    }
    if (PlazaSlabMaterial != nullptr && PlazaWayInstances != nullptr)
    {
        PlazaWayInstances->SetMaterial(0, PlazaSlabMaterial);
    }
    if (PlazaAshlarMaterial != nullptr)
    {
        UHierarchicalInstancedStaticMeshComponent* const Stone[5] = {
            PlazaRibInstances, PlazaKerbInstances, PlazaChannelInstances,
            PlazaRetainingInstances, PlazaScarpInstances};
        for (UHierarchicalInstancedStaticMeshComponent* Component : Stone)
        {
            if (Component != nullptr) Component->SetMaterial(0, PlazaAshlarMaterial);
        }
        if (PlazaStepInstances != nullptr) PlazaStepInstances->SetMaterial(0, PlazaAshlarMaterial);
    }

    PlazaStatus = TEXT("built");
}

void AMikdashEnclosure::GetPlazaCounts(int32& OutDeckTiles, int32& OutWayTiles, int32& OutRibs,
                                       int32& OutKerbs, int32& OutChannels, int32& OutRetainingBands,
                                       int32& OutScarpBands, int32& OutSteps) const
{
    auto Count = [](const UHierarchicalInstancedStaticMeshComponent* Component)
    {
        return Component != nullptr ? Component->GetInstanceCount() : 0;
    };
    OutDeckTiles = Count(PlazaDeckInstances);
    OutWayTiles = Count(PlazaWayInstances);
    OutRibs = Count(PlazaRibInstances);
    OutKerbs = Count(PlazaKerbInstances);
    OutChannels = Count(PlazaChannelInstances);
    OutRetainingBands = Count(PlazaRetainingInstances);
    OutScarpBands = Count(PlazaScarpInstances);
    OutSteps = Count(PlazaStepInstances);
}

int32 AMikdashEnclosure::GetPlazaTriangleCount() const
{
    int32 Deck = 0, Way = 0, Rib = 0, Kerb = 0, Channel = 0, Retaining = 0, Scarp = 0, Step = 0;
    GetPlazaCounts(Deck, Way, Rib, Kerb, Channel, Retaining, Scarp, Step);
    const FPlazaModuleBudget Budget;
    return Deck * Budget.DeckTileTriangles + Way * Budget.WayTileTriangles
         + Rib * Budget.RibTriangles + Kerb * Budget.KerbTriangles
         + Channel * Budget.ChannelTriangles
         + (Retaining + Scarp) * Budget.RetainingBandTriangles
         + Step * Budget.StepTriangles;
}

float AMikdashEnclosure::GetPlazaDeckTopZCm() const
{
    return static_cast<float>(PlazaDeckTopZUnrealCm(static_cast<double>(WorldCmPerAmah)));
}

FVector4 AMikdashEnclosure::GetPlazaExtentCm() const
{
    const FPlazaGrid Grid = PlanPlazaGrid(GetSquare(), static_cast<double>(WallThicknessAmot),
                                          static_cast<double>(WorldCmPerAmah));
    return FVector4(Grid.XMinUnrealCm, Grid.YMinUnrealCm, Grid.XMaxUnrealCm, Grid.YMaxUnrealCm);
}

void AMikdashEnclosure::GetPlazaGrid(int32& OutCellsX, int32& OutCellsY, int32& OutPanels) const
{
    OutCellsX = PlazaCellsX;
    OutCellsY = PlazaCellsY;
    OutPanels = PlazaPanels;
}

FVector2D AMikdashEnclosure::GetPlazaFaceHeightsCm(int32 Side) const
{
    const int Index = ((Side % 4) + 4) % 4;
    return FVector2D(PlazaRetainingMax[Index], PlazaScarpMax[Index]);
}

FString AMikdashEnclosure::GetPlazaStatus() const
{
    return PlazaStatus;
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
    // The plaza is part of the built precinct, so it follows the wall exactly: present in
    // YECHEZKEL, gone in MODERN (which must restore today's city untouched) and gone in
    // OVERLAY (whose whole point is the standing city seen under the boundary line - a deck
    // laid over it would hide the thing the overlay exists to show).
    UHierarchicalInstancedStaticMeshComponent* const PlazaComponents[8] = {
        PlazaDeckInstances, PlazaWayInstances, PlazaRibInstances, PlazaKerbInstances,
        PlazaChannelInstances, PlazaRetainingInstances, PlazaScarpInstances, PlazaStepInstances};
    for (UHierarchicalInstancedStaticMeshComponent* Component : PlazaComponents)
    {
        if (Component != nullptr) Component->SetVisibility(bShowWall, true);
    }
    // Beside the plaza and for the same reason: parts of the built precinct - and parts of
    // today's city - that are whole ACTORS rather than instances on this one. Terrain twins,
    // the hillside they replace, the Kotel plaza cut and the precinct roofscape all move here.
    ApplyStateTaggedActors(bShowWall);

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
        RestoreHiddenBuildings();
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
    RestoreHiddenBuildings();
    // Same contract, one call further: whatever this actor moved, it puts back. EndPlay,
    // RebuildPrecinct and MeasureWithoutHiding all reach the tagged terrain and roofscape
    // actors through here. ApplyWeights deliberately does NOT - see RestoreHiddenBuildings.
    RestoreStateTaggedActors();
}

/** Buildings only. ApplyWeights calls THIS, not RestoreAllModernBuildings, on the path where
 *  no building is hidden: the tagged state actors were set a few lines earlier in the same
 *  call and restoring them here would immediately undo the swap this function exists to make. */
void AMikdashEnclosure::RestoreHiddenBuildings()
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
