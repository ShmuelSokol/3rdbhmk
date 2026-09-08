#include "MikdashSurfaceDetail.h"

#include "Components/DecalComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DecalActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TimerManager.h"

using namespace MikdashWear;

namespace
{
/** The shipped plan. Identical numbers to SurfaceWearMathTest.cpp BudgetChecks and to
 *  SourceAssets/surface-review/surface-detail.json; if the three ever disagree the test
 *  is the one that is right, because it is the one that runs. */
struct FDefaultCategory
{
    const TCHAR* Tag;
    float  Weight;
    int32  Requested;
    int32  Minimum;
    float  FadeStartCm;
    float  FadeEndCm;
};

const FDefaultCategory DefaultCategories[] = {
    { TEXT("MikdashWear_footPolish"),  5.0f, 96, 24, 3000.f,  9000.f },
    { TEXT("MikdashWear_stepNosing"),  4.0f, 72, 18, 2000.f,  6000.f },
    { TEXT("MikdashWear_rainStreak"),  3.0f, 64, 12, 4000.f, 12000.f },
    { TEXT("MikdashWear_dustRunoff"),  2.5f, 48,  8, 4000.f, 12000.f },
    { TEXT("MikdashWear_waterStain"),  2.0f, 24,  6, 2500.f,  7000.f },
    { TEXT("MikdashWear_soot"),        3.5f, 20,  8, 3000.f,  9000.f },
    { TEXT("MikdashWear_lichen"),      1.5f, 60,  0, 2500.f,  7500.f },
    { TEXT("MikdashWear_windDust"),    1.5f, 44,  0, 2500.f,  7500.f },
    { TEXT("MikdashWear_weathering"),  1.0f, 32,  0, 3000.f,  9000.f },
};

/** Copy an FString into a std::wstring without assuming TCHAR is wchar_t. On Windows it
 *  is; on a platform where TCHAR is char16_t this still produces the right characters
 *  for the ASCII package paths involved, and MikdashSurfaceAudio::CanonicalPackage
 *  rejects anything that is not a plain /Game/ path anyway. */
std::wstring ToWide(const FString& Value)
{
    std::wstring Out;
    Out.reserve(static_cast<size_t>(Value.Len()));
    for (int32 Index = 0; Index < Value.Len(); ++Index)
    {
        Out.push_back(static_cast<wchar_t>(Value[Index]));
    }
    return Out;
}

/** The importance the release script stamped on this decal, recovered from its tags.
 *  The tag is "MikdashWearImportance_<milli>", so 0.735 travels as 735. A decal with no
 *  such tag is treated as fully important: it is better to draw an untagged decal than
 *  to silently drop it. */
double ImportanceFromTags(const AActor& Actor)
{
    static const FString Prefix(TEXT("MikdashWearImportance_"));
    for (const FName& Tag : Actor.Tags)
    {
        const FString Text = Tag.ToString();
        if (!Text.StartsWith(Prefix)) continue;
        const int32 Milli = FCString::Atoi(*Text.RightChop(Prefix.Len()));
        return ClampRange(static_cast<double>(Milli) / 1000.0, 0.0, 1.0);
    }
    return 1.0;
}
}

AMikdashSurfaceDetail::AMikdashSurfaceDetail()
{
    // Timers, never Tick. A surface manager that has nothing to re-sort should cost
    // nothing at all, not an empty tick every frame.
    PrimaryActorTick.bCanEverTick = false;
    PrimaryActorTick.bStartWithTickEnabled = false;

    USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("SurfaceDetailRoot"));
    SetRootComponent(Root);
    Root->SetMobility(EComponentMobility::Static);

    for (const FDefaultCategory& Row : DefaultCategories)
    {
        FMikdashWearCategory Category;
        Category.Tag = FName(Row.Tag);
        Category.Weight = Row.Weight;
        Category.Requested = Row.Requested;
        Category.Minimum = Row.Minimum;
        Category.FadeStartCm = Row.FadeStartCm;
        Category.FadeEndCm = Row.FadeEndCm;
        Categories.Add(Category);
    }

    // The measured water surface in the combined map: the laver's water, recessed below
    // its rolled rim (SM_0126 in SourceAssets/architecture-manifest.json, the single mesh
    // the PBR pass skipped as "excluded folder Measured architecture/water"). Listed as a
    // package path so a designer can see it and add to it when more water is placed.
    WaterMeshPrefixes.Add(
        TEXT("/Game/MikdashV3/Architecture/architecture_SM_0126_water_Water_recessed_below_rolled_rim"));

    // The one floor the native receipt identifies by itself rather than by family. Kept
    // here so the two paths are visibly configured from the same evidence; Route falls
    // back to exactly this path internally if the list is empty.
    VerifiedStoneFloors.Add(TEXT("/Game/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Surface"));
}

void AMikdashSurfaceDetail::BeginPlay()
{
    Super::BeginPlay();

    FootstepPool.Reset();
    FootstepMaterials.Reset();
    FootstepExpiry.Reset();
    FootstepBirth.Reset();
    FootstepStartRadius.Reset();

    const int32 PoolSize = FMath::Clamp(FootstepPoolSize, 1, 64);
    for (int32 Index = 0; Index < PoolSize; ++Index)
    {
        UDecalComponent* Decal = NewObject<UDecalComponent>(this);
        if (!Decal) break;
        Decal->SetupAttachment(GetRootComponent());
        Decal->RegisterComponent();
        Decal->SetMobility(EComponentMobility::Movable);
        Decal->SetUsingAbsoluteLocation(true);
        Decal->SetUsingAbsoluteRotation(true);
        Decal->SetUsingAbsoluteScale(true);
        Decal->SetVisibility(false);
        Decal->SortOrder = 40;                       // above the authored wear
        FootstepPool.Add(Decal);
        FootstepMaterials.Add(nullptr);
        FootstepExpiry.Add(-1.0);
        FootstepBirth.Add(-1.0);
        FootstepStartRadius.Add(FootstepPuffRadiusCm);
    }

    RefreshDecalRegistry();

    if (UWorld* World = GetWorld())
    {
        World->GetTimerManager().SetTimer(
            BudgetTimer, this, &AMikdashSurfaceDetail::TickBudget,
            FMath::Max(0.05f, BudgetUpdateIntervalSeconds), true, 0.1f);
        // The footstep pool only needs stepping while something is alive in it; a fixed
        // slow timer is cheaper than a per-decal timer and cannot leak handles.
        World->GetTimerManager().SetTimer(
            FootstepTimer, this, &AMikdashSurfaceDetail::TickFootsteps, 0.06f, true, 0.06f);
    }
}

void AMikdashSurfaceDetail::EndPlay(const EEndPlayReason::Type Reason)
{
    if (UWorld* World = GetWorld())
    {
        World->GetTimerManager().ClearTimer(BudgetTimer);
        World->GetTimerManager().ClearTimer(FootstepTimer);
    }
    Super::EndPlay(Reason);
}

int32 AMikdashSurfaceDetail::CategoryIndexForActor(const AActor* Actor) const
{
    if (!Actor) return INDEX_NONE;
    for (int32 Index = 0; Index < Categories.Num(); ++Index)
    {
        if (Categories[Index].Tag.IsNone()) continue;
        if (Actor->Tags.Contains(Categories[Index].Tag)) return Index;
    }
    return INDEX_NONE;
}

void AMikdashSurfaceDetail::RefreshDecalRegistry()
{
    Registered.Reset();
    LastAllocation.Init(0, Categories.Num());
    VisibleCount = 0;
    bHasBudgetedOnce = false;

    UWorld* World = GetWorld();
    if (!World || Categories.Num() == 0) return;

    for (TActorIterator<ADecalActor> It(World); It; ++It)
    {
        ADecalActor* Actor = *It;
        if (!Actor || !Actor->Tags.Contains(SurfaceWearTag)) continue;
        const int32 CategoryIndex = CategoryIndexForActor(Actor);
        if (CategoryIndex == INDEX_NONE) continue;         // not one of ours; leave alone
        UDecalComponent* Decal = Actor->GetDecal();
        if (!Decal) continue;

        FRegisteredDecal Row;
        Row.Decal = Decal;
        Row.CategoryIndex = CategoryIndex;
        Row.Importance = ImportanceFromTags(*Actor);
        Row.RegistryIndex = Registered.Num();
        Registered.Add(Row);

        // The renderer's own screen-size fade does the last stretch, so a decal that the
        // budget still counts as visible does not pop out at the fade end. Screen size
        // is a fraction of the view, so it falls as 1/distance: this is the fade-end
        // distance expressed the way UDecalComponent wants it.
        const FMikdashWearCategory& Category = Categories[CategoryIndex];
        const float Extent = FMath::Max(1.f, Decal->DecalSize.GetMax());
        Decal->FadeScreenSize = FMath::Clamp(
            Extent / FMath::Max(1.f, Category.FadeEndCm), 0.0005f, 0.05f);
    }

    UpdateDecalBudget();
}

bool AMikdashSurfaceDetail::ViewLocation(FVector& OutLocation) const
{
    const UWorld* World = GetWorld();
    if (!World) return false;
    for (FConstPlayerControllerIterator It = World->GetPlayerControllerIterator(); It; ++It)
    {
        const APlayerController* Controller = It->Get();
        if (!Controller || !Controller->IsLocalController()) continue;
        FVector Location = FVector::ZeroVector;
        FRotator Rotation = FRotator::ZeroRotator;
        Controller->GetPlayerViewPoint(Location, Rotation);
        OutLocation = Location;
        return true;
    }
    return false;
}

void AMikdashSurfaceDetail::TickBudget()
{
    FVector View = FVector::ZeroVector;
    if (!ViewLocation(View)) return;
    // Standing still costs nothing: the sort cannot have changed.
    if (bHasBudgetedOnce
        && FVector::DistSquared(View, LastBudgetViewLocation)
           < static_cast<double>(BudgetMoveThresholdCm) * BudgetMoveThresholdCm)
    {
        return;
    }
    UpdateDecalBudget();
}

void AMikdashSurfaceDetail::UpdateDecalBudget()
{
    const int32 CategoryCount = Categories.Num();
    LastAllocation.Init(0, CategoryCount);
    VisibleCount = 0;
    if (Registered.Num() == 0 || CategoryCount == 0) return;

    FVector View = FVector::ZeroVector;
    const bool bHaveView = ViewLocation(View);

    // 1. Score every decal. DecalScore is importance x distance fade, and returns
    //    exactly zero past the fade end, so a decal nobody can see can never displace
    //    one they can.
    for (FRegisteredDecal& Row : Registered)
    {
        const UDecalComponent* Decal = Row.Decal.Get();
        if (!Decal)
        {
            Row.Score = 0.0;
            continue;
        }
        const FMikdashWearCategory& Category = Categories[Row.CategoryIndex];
        const double Distance = bHaveView
            ? FVector::Dist(View, Decal->GetComponentLocation())
            : 0.0;
        Row.Score = DecalScore(Row.Importance, Distance,
                               Category.FadeStartCm, Category.FadeEndCm);
    }

    // 2. What each category could actually use: how many of its decals score above
    //    zero, capped by its authored request. Asking for more than that would waste
    //    budget on decals that are past their fade end.
    TArray<int32> Live;
    Live.Init(0, CategoryCount);
    for (const FRegisteredDecal& Row : Registered)
    {
        if (Row.Score > 0.0 && Row.Decal.IsValid()) ++Live[Row.CategoryIndex];
    }

    TArray<FBudgetRequest> Items;
    Items.SetNum(CategoryCount);
    for (int32 Index = 0; Index < CategoryCount; ++Index)
    {
        const FMikdashWearCategory& Category = Categories[Index];
        Items[Index].Weight = static_cast<double>(FMath::Max(0.f, Category.Weight));
        Items[Index].Requested = FMath::Min(FMath::Max(0, Category.Requested), Live[Index]);
        Items[Index].Minimum = FMath::Max(0, Category.Minimum);
    }

    TArray<int32> Counts;
    Counts.Init(0, CategoryCount);
    const int32 Allocated = AllocateBudget(Items.GetData(), CategoryCount,
                                           FMath::Max(0, DecalBudget), Counts.GetData());

    // 3. Show the best-scoring N of each category and hide the rest. The sort is by
    //    score, then by registry index, so a tie always resolves the same way and the
    //    set does not flicker when two decals score identically.
    TArray<int32> Order;
    Order.Reserve(Registered.Num());
    for (int32 Index = 0; Index < Registered.Num(); ++Index) Order.Add(Index);
    Order.Sort([this](int32 A, int32 B)
    {
        if (Registered[A].Score != Registered[B].Score) return Registered[A].Score > Registered[B].Score;
        return Registered[A].RegistryIndex < Registered[B].RegistryIndex;
    });

    TArray<int32> Shown;
    Shown.Init(0, CategoryCount);
    for (int32 Index : Order)
    {
        FRegisteredDecal& Row = Registered[Index];
        UDecalComponent* Decal = Row.Decal.Get();
        if (!Decal) continue;
        const bool bVisible = Row.Score > 0.0 && Shown[Row.CategoryIndex] < Counts[Row.CategoryIndex];
        if (bVisible) ++Shown[Row.CategoryIndex];
        if (Decal->IsVisible() != bVisible) Decal->SetVisibility(bVisible);
    }

    LastAllocation = Shown;
    VisibleCount = 0;
    for (int32 Count : Shown) VisibleCount += Count;

    // AllocateBudget guarantees the cap; this is the belt-and-braces read of it, and it
    // is what would catch a future edit that broke the guarantee in a live build.
    ensureMsgf(VisibleCount <= FMath::Max(0, DecalBudget),
               TEXT("Surface wear budget exceeded: %d visible against a cap of %d"),
               VisibleCount, DecalBudget);
    ensureMsgf(VisibleCount <= Allocated,
               TEXT("Shown more decals (%d) than were allocated (%d)"), VisibleCount, Allocated);

    if (bHaveView) LastBudgetViewLocation = View;
    bHasBudgetedOnce = true;
}

// ---------------------------------------------------------------------------
// Surface query
// ---------------------------------------------------------------------------

bool AMikdashSurfaceDetail::BuildFloorEvidence(
    std::vector<std::wstring>& OutStorage,
    std::vector<MikdashSurfaceAudio::Registration>& OutRows) const
{
    OutStorage.clear();
    OutRows.clear();
    OutStorage.reserve(static_cast<size_t>(VerifiedStoneFloors.Num() + VerifiedSoftFloors.Num()));
    for (const FString& Path : VerifiedStoneFloors) OutStorage.push_back(ToWide(Path));
    const size_t SoftBegin = OutStorage.size();
    for (const FString& Path : VerifiedSoftFloors) OutStorage.push_back(ToWide(Path));

    // Only now, when the storage can no longer reallocate, are pointers taken into it.
    OutRows.reserve(OutStorage.size());
    for (size_t Index = 0; Index < OutStorage.size(); ++Index)
    {
        MikdashSurfaceAudio::Registration Row;
        Row.PackagePath = OutStorage[Index].c_str();
        Row.Samples = Index < SoftBegin ? MikdashSurfaceAudio::Bank::RecordedStone
                                        : MikdashSurfaceAudio::Bank::RecordedSoft;
        OutRows.push_back(Row);
    }
    return !OutRows.empty();
}

FMikdashSurfacePoint AMikdashSurfaceDetail::QuerySurfaceAtPoint(FVector WorldPoint) const
{
    FMikdashSurfacePoint Result;
    const UWorld* World = GetWorld();
    if (!World) return Result;

    const FVector Start = WorldPoint + FVector(0.f, 0.f, FMath::Max(1.f, SurfaceTraceUpCm));
    const FVector End = WorldPoint - FVector(0.f, 0.f, FMath::Max(1.f, SurfaceTraceDownCm));

    FCollisionQueryParams Params(SCENE_QUERY_STAT(MikdashSurfaceQuery), /*bTraceComplex=*/false, this);
    FHitResult Hit;
    if (!World->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params))
    {
        return Result;                                   // no evidence: stays Silent
    }

    Result.bHit = true;
    Result.ImpactPoint = Hit.ImpactPoint;
    Result.ImpactNormal = Hit.ImpactNormal;

    const UStaticMeshComponent* Floor = Cast<UStaticMeshComponent>(Hit.GetComponent());
    if (!Floor || !Floor->GetStaticMesh()) return Result;
    Result.FloorMeshPath = Floor->GetStaticMesh()->GetPathName();

    // Strip the ".Object" suffix the way CanonicalPackage expects, then hand the whole
    // decision to the shared router. This actor deliberately owns none of that logic.
    std::vector<std::wstring> Storage;
    std::vector<MikdashSurfaceAudio::Registration> Rows;
    BuildFloorEvidence(Storage, Rows);
    const std::wstring Path = ToWide(Result.FloorMeshPath);
    const MikdashSurfaceAudio::Bank Bank = MikdashSurfaceAudio::Route(
        Path.c_str(), /*Grounded=*/true, /*BlockingWalkableFloor=*/Hit.bBlockingHit,
        Rows.empty() ? nullptr : Rows.data(), Rows.size());
    Result.Bank = static_cast<EMikdashSurfaceBank>(static_cast<uint8>(Bank));

    for (const FString& Prefix : WaterMeshPrefixes)
    {
        if (!Prefix.IsEmpty() && Result.FloorMeshPath.StartsWith(Prefix))
        {
            Result.bWater = true;
            break;
        }
    }
    return Result;
}

MikdashSurfaceAudio::Bank AMikdashSurfaceDetail::QuerySurfaceBank(const FVector& WorldPoint) const
{
    return QuerySurfaceAtPoint(WorldPoint).GetBank();
}

bool AMikdashSurfaceDetail::IsWaterAtPoint(FVector WorldPoint) const
{
    return QuerySurfaceAtPoint(WorldPoint).bWater;
}

// ---------------------------------------------------------------------------
// Footstep response - the visual half only. No sound is played, loaded or referenced.
// ---------------------------------------------------------------------------

int32 AMikdashSurfaceDetail::AcquireFootstepSlot()
{
    if (FootstepPool.Num() == 0) return INDEX_NONE;
    const UWorld* World = GetWorld();
    const double Now = World ? World->GetTimeSeconds() : 0.0;

    // Prefer a free slot; otherwise recycle the oldest. Never allocate.
    for (int32 Offset = 0; Offset < FootstepPool.Num(); ++Offset)
    {
        const int32 Index = (NextFootstepSlot + Offset) % FootstepPool.Num();
        if (FootstepExpiry[Index] <= Now)
        {
            NextFootstepSlot = (Index + 1) % FootstepPool.Num();
            return Index;
        }
    }
    int32 Oldest = 0;
    for (int32 Index = 1; Index < FootstepPool.Num(); ++Index)
    {
        if (FootstepBirth[Index] < FootstepBirth[Oldest]) Oldest = Index;
    }
    NextFootstepSlot = (Oldest + 1) % FootstepPool.Num();
    return Oldest;
}

bool AMikdashSurfaceDetail::SpawnFootstepResponse(FVector WorldPoint, float Speed)
{
    // Cheapest rejections first, so a distant walker never pays for a trace.
    const UWorld* World = GetWorld();
    if (!World) return false;
    const double Now = World->GetTimeSeconds();
    if (Now - LastFootstepTime < static_cast<double>(FMath::Max(0.f, MinFootstepIntervalSeconds)))
    {
        return false;
    }
    FVector View = FVector::ZeroVector;
    if (ViewLocation(View)
        && FVector::DistSquared(View, WorldPoint)
           > static_cast<double>(FootstepMaxViewDistanceCm) * FootstepMaxViewDistanceCm)
    {
        return false;
    }
    return SpawnFootstepResponseFor(QuerySurfaceAtPoint(WorldPoint), Speed);
}

bool AMikdashSurfaceDetail::SpawnFootstepResponseFor(const FMikdashSurfacePoint& Surface, float Speed)
{
    if (!Surface.bHit) return false;

    // A ripple on water, a puff on dry recorded stone or soft ground, and NOTHING on an
    // unrecognised surface. The last case matters: the audio path refuses to invent a
    // footstep sound for an unknown floor family, and the visual half must refuse in
    // exactly the same places, or the two will disagree in front of the player.
    UMaterialInterface* Source = nullptr;
    if (Surface.bWater)
    {
        Source = RippleMaterial;
    }
    else if (Surface.GetBank() == MikdashSurfaceAudio::Bank::RecordedStone
             || Surface.GetBank() == MikdashSurfaceAudio::Bank::RecordedSoft)
    {
        Source = DustPuffMaterial;
    }
    if (!Source) return false;                    // unassigned material: draw nothing

    const int32 Slot = AcquireFootstepSlot();
    if (Slot == INDEX_NONE) return false;
    UDecalComponent* Decal = FootstepPool[Slot];
    if (!Decal) return false;

    UMaterialInstanceDynamic* Dynamic = FootstepMaterials[Slot];
    if (!Dynamic || Dynamic->Parent != Source)
    {
        Dynamic = UMaterialInstanceDynamic::Create(Source, this);
        if (!Dynamic) return false;
        FootstepMaterials[Slot] = Dynamic;
        Decal->SetDecalMaterial(Dynamic);
    }

    const UWorld* World = GetWorld();
    const double Now = World ? World->GetTimeSeconds() : 0.0;
    const float Lifetime = FMath::Max(0.05f, FootstepLifetimeSeconds);

    // Faster feet kick up a slightly bigger puff. This is a scale, never a gate: the
    // decision that a step happened was made by FMikdashFootstepCadence upstream.
    const float SpeedScale = 1.f + 0.35f * FMath::Clamp((Speed - 100.f) / 500.f, 0.f, 1.f);
    const float Radius = FMath::Max(1.f, FootstepPuffRadiusCm) * SpeedScale
                       * (Surface.bWater ? 1.4f : 1.0f);

    FootstepStartRadius[Slot] = Radius;
    FootstepBirth[Slot] = Now;
    FootstepExpiry[Slot] = Now + Lifetime;
    LastFootstepTime = Now;

    // Project straight down onto the impact, with a random yaw so twelve footprints in a
    // row are not twelve copies of one image.
    const float Yaw = static_cast<float>(Hash01(static_cast<unsigned int>(Slot + 1),
                                                static_cast<unsigned int>(Now * 1000.0)) * 360.0);
    Decal->SetWorldLocationAndRotation(Surface.ImpactPoint + FVector(0.f, 0.f, 2.f),
                                       FRotator(-90.f, Yaw, 0.f));
    Decal->DecalSize = FVector(24.f, Radius, Radius);
    Dynamic->SetScalarParameterValue(TEXT("Opacity"), Surface.bWater ? 0.75f : 0.55f);
    Decal->SetVisibility(true);
    return true;
}

void AMikdashSurfaceDetail::TickFootsteps()
{
    const UWorld* World = GetWorld();
    if (!World) return;
    const double Now = World->GetTimeSeconds();
    const float Lifetime = FMath::Max(0.05f, FootstepLifetimeSeconds);

    for (int32 Slot = 0; Slot < FootstepPool.Num(); ++Slot)
    {
        UDecalComponent* Decal = FootstepPool[Slot];
        if (!Decal || !Decal->IsVisible()) continue;
        if (Now >= FootstepExpiry[Slot])
        {
            Decal->SetVisibility(false);
            continue;
        }
        const double Age = FMath::Max(0.0, Now - FootstepBirth[Slot]);
        const double T = Clamp01(Age / static_cast<double>(Lifetime));

        // A puff grows and thins; the same curve reads as an expanding ripple on water,
        // which is why one pool serves both.
        const float Grow = 1.f + 1.15f * static_cast<float>(T);
        const float Radius = FootstepStartRadius[Slot] * Grow;
        Decal->DecalSize = FVector(24.f, Radius, Radius);

        // Fade out with the same smooth curve the distance fade uses, so the two kinds
        // of fade in this actor look like one thing.
        const float Alpha = static_cast<float>(SmoothFalloff(T, 0.15, 1.0));
        if (UMaterialInstanceDynamic* Dynamic = FootstepMaterials[Slot])
        {
            Dynamic->SetScalarParameterValue(TEXT("Opacity"), Alpha * 0.75f);
        }
        Decal->MarkRenderStateDirty();
    }
}
