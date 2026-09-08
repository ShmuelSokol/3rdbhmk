#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "SurfaceWearMath.h"
#include "MikdashSurfaceAudioRouting.h"
#include <string>
#include <vector>
#include "MikdashSurfaceDetail.generated.h"

class UDecalComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;

// ---------------------------------------------------------------------------
// Surface enumeration
//
// THERE IS ONLY ONE surface enumeration in this project and it is
// MikdashSurfaceAudio::Bank, declared in MikdashSurfaceAudioRouting.h and consumed by
// AMikdashPlayerController::UpdateFootsteps. This file does NOT define a second one.
//
// EMikdashSurfaceBank below is a strict mirror, and exists for exactly one reason: a
// plain C++ enum class inside a namespace cannot be a UENUM, so Blueprint and the
// details panel cannot see Bank. Every enumerator has the same name, the same order and
// - asserted at compile time below - the same numeric value. The authoritative API,
// QuerySurfaceBank(), returns MikdashSurfaceAudio::Bank itself; the UENUM only ever
// appears on the Blueprint-facing wrappers.
//
// If a value is ever added to Bank, this file stops compiling until it is added here
// too. That is deliberate.
// ---------------------------------------------------------------------------

UENUM(BlueprintType)
enum class EMikdashSurfaceBank : uint8
{
    /** No footstep evidence, or evidence that conflicts. Fails closed, exactly as
     *  MikdashSurfaceAudio::Route does. Water reads as Silent too - see bWater. */
    Silent          UMETA(DisplayName = "Silent (no evidence)"),
    /** A verified hard floor: the measured architecture, the street paving, the mount
     *  platform surface. */
    RecordedStone   UMETA(DisplayName = "Recorded stone"),
    /** A verified soft floor: the Jerusalem context terrain. */
    RecordedSoft    UMETA(DisplayName = "Recorded soft"),
};

static_assert(static_cast<uint8>(EMikdashSurfaceBank::Silent)
              == static_cast<uint8>(MikdashSurfaceAudio::Bank::Silent),
              "EMikdashSurfaceBank must mirror MikdashSurfaceAudio::Bank exactly");
static_assert(static_cast<uint8>(EMikdashSurfaceBank::RecordedStone)
              == static_cast<uint8>(MikdashSurfaceAudio::Bank::RecordedStone),
              "EMikdashSurfaceBank must mirror MikdashSurfaceAudio::Bank exactly");
static_assert(static_cast<uint8>(EMikdashSurfaceBank::RecordedSoft)
              == static_cast<uint8>(MikdashSurfaceAudio::Bank::RecordedSoft),
              "EMikdashSurfaceBank must mirror MikdashSurfaceAudio::Bank exactly");

/** What the surface query found under a point.
 *
 *  Bank is the shared enumeration, unchanged. bWater is a SEPARATE flag and not a
 *  fourth bank value, because water is not a footstep sample bank: a foot in the laver
 *  is still Silent to MikdashSurfaceAudio::Route, which has no recorded water sample
 *  and must keep failing closed. Adding Water to Bank would have changed the meaning of
 *  an enumeration this actor does not own and would have silently altered which
 *  footstep sound the player controller plays. The visual response reads bWater; the
 *  audio routing never sees it. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashSurfacePoint
{
    GENERATED_BODY()

    /** True only if a downward trace actually hit something. Everything else is
     *  meaningless when this is false. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Surface")
    bool bHit = false;

    /** The shared bank. Mirrors MikdashSurfaceAudio::Bank value for value. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Surface")
    EMikdashSurfaceBank Bank = EMikdashSurfaceBank::Silent;

    /** Standing water at this point. Orthogonal to Bank; see the struct comment. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Surface")
    bool bWater = false;

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Surface")
    FVector ImpactPoint = FVector::ZeroVector;

    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Surface")
    FVector ImpactNormal = FVector::UpVector;

    /** The floor mesh package the decision was made from, so a receipt can record why. */
    UPROPERTY(BlueprintReadOnly, Category = "Mikdash|Surface")
    FString FloorMeshPath;

    /** The authoritative type, for C++ callers. */
    MikdashSurfaceAudio::Bank GetBank() const
    {
        return static_cast<MikdashSurfaceAudio::Bank>(static_cast<uint8>(Bank));
    }
};

/** One budget category. Mirrors MikdashWear::FBudgetRequest; the values ship in
 *  SourceAssets/surface-review/surface-detail.json and are pinned by
 *  Plugins/MikdashRuntime/Tests/SurfaceWearMathTest.cpp. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashWearCategory
{
    GENERATED_BODY()

    /** The actor tag the release script stamps on every decal of this category, e.g.
     *  "MikdashWear_footPolish". */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface")
    FName Tag;

    /** Share of whatever budget is left after the minimums. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface", meta = (ClampMin = "0.0"))
    float Weight = 1.f;

    /** Never show more than this many of the category, however much budget is spare. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface", meta = (ClampMin = "0"))
    int32 Requested = 0;

    /** Honoured first. A request, not a promise: the cap always wins. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface", meta = (ClampMin = "0"))
    int32 Minimum = 0;

    /** Distance at which this category starts fading, centimetres. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface", meta = (ClampMin = "0.0"))
    float FadeStartCm = 3000.f;

    /** Distance at which it is fully gone. Beyond this a decal scores exactly zero and
     *  can never displace a visible one. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface", meta = (ClampMin = "0.0"))
    float FadeEndCm = 9000.f;
};

/** Ambient surface-wear manager: the decal budget, the distance fade, the surface query
 *  and the visual half of the footstep response.
 *
 *  WHAT IT MANAGES, AND WHAT PUT IT THERE
 *  Scripts/release_surface_detail.py places the wear decals into the map as ADecalActors
 *  and tags every one with SurfaceWearTag plus its category tag. This actor never
 *  spawns, moves or destroys those decals and never edits a material asset; it only
 *  decides, several times a second, which of them are worth drawing right now. The
 *  authored set is 460 decals and the shipping cap is 220 - see
 *  SourceAssets/surface-review/surface-detail.json for the whole table with a written
 *  rationale for every entry.
 *
 *  BUDGET. Every visible decal is scored by MikdashWear::DecalScore: its authored
 *  importance multiplied by its distance fade, so a decal past its fade end scores
 *  exactly zero and can never displace a visible one. MikdashWear::AllocateBudget then
 *  splits DecalBudget across the categories - minimums first, remainder by weight - and
 *  the top-scoring N of each category are shown. All of that arithmetic is engine-free
 *  and unit-tested standalone in Plugins/MikdashRuntime/Tests/SurfaceWearMathTest.cpp;
 *  this actor is the adapter and holds no formula of its own.
 *
 *  FADE. Each decal's FadeScreenSize is set from its category's fade window, so the
 *  renderer drops it smoothly rather than popping when the budget re-sorts.
 *
 *  FOOTSTEP RESPONSE. SpawnFootstepResponse() is the VISUAL half only: a dust puff on
 *  dry stone, a ripple on water, both short-lived decals from a fixed-size pool. This
 *  actor plays no sound, holds no USoundBase and never touches the footstep audio path;
 *  the audio half is AMikdashPlayerController::UpdateFootsteps via
 *  MikdashSurfaceAudio::Route, and the two share the same Bank enumeration precisely so
 *  they cannot disagree about what the player is standing on.
 *
 *  COST. Driven by a timer, never by Tick. The update is one pass over the registered
 *  decals - no traces, no allocation after BeginPlay - and the surface query traces only
 *  when a footfall actually asks it to, rate-limited by MinFootstepIntervalSeconds. The
 *  footstep pool is fixed, so a burst of footfalls recycles the oldest puff instead of
 *  allocating. See surface-detail.json costEstimate; that estimate is arithmetic, and no
 *  frame has been captured.
 *
 *  MATERIALS. This actor creates dynamic material instances for the footstep pool only,
 *  from the two materials assigned below. It NEVER edits a material asset and never
 *  touches a shared parent. The wear decals' own materials are set once, offline, by the
 *  release script.
 *
 *  WHAT THIS IS NOT. Not a weathering simulation, not a claim about the historical
 *  Mikdash, and not decay: the Mikdash is maintained daily, so what is depicted is the
 *  wear of heavy use and weather - polish, soot, dust, rain-washed stone - and never
 *  cracks, spalling or ruin. */
UCLASS(BlueprintType, Blueprintable)
class MIKDASHRUNTIME_API AMikdashSurfaceDetail : public AActor
{
    GENERATED_BODY()

public:
    AMikdashSurfaceDetail();

    // -- surface query ------------------------------------------------------

    /** The authoritative query. Traces down from just above WorldPoint and classifies
     *  the floor with MikdashSurfaceAudio::Route, using the same verified-floor
     *  evidence the audio path uses. Returns Bank::Silent for anything unrecognised;
     *  it fails closed by design. */
    MikdashSurfaceAudio::Bank QuerySurfaceBank(const FVector& WorldPoint) const;

    /** The same query, with the impact and the water flag, for Blueprint. */
    UFUNCTION(BlueprintCallable, BlueprintPure = false, Category = "Mikdash|Surface")
    FMikdashSurfacePoint QuerySurfaceAtPoint(FVector WorldPoint) const;

    /** Standing water at this point, from the water mesh list below. Water is not a
     *  Bank value; see FMikdashSurfacePoint. */
    UFUNCTION(BlueprintCallable, BlueprintPure, Category = "Mikdash|Surface")
    bool IsWaterAtPoint(FVector WorldPoint) const;

    // -- footstep response (visual only) ------------------------------------

    /** Spawn the visual response to one footfall: a dust puff on dry stone, a ripple on
     *  water, nothing at all on an unrecognised surface. Plays no sound. Returns true
     *  if something was actually spawned.
     *
     *  Speed is the walker's 2D speed in cm/s and only scales the puff; it is never used
     *  to decide whether a step happened. That decision belongs to
     *  FMikdashFootstepCadence, which the player controller already owns. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Surface")
    bool SpawnFootstepResponse(FVector WorldPoint, float Speed);

    /** As above, but for a caller that has already queried the surface and does not
     *  want a second trace. */
    bool SpawnFootstepResponseFor(const FMikdashSurfacePoint& Surface, float Speed);

    // -- budget -------------------------------------------------------------

    /** Re-discover the tagged decals in the level. Called once at BeginPlay; call it
     *  again only if decals were added or removed at run time. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Surface")
    void RefreshDecalRegistry();

    /** Re-score and re-budget immediately instead of waiting for the timer. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Surface")
    void UpdateDecalBudget();

    UFUNCTION(BlueprintCallable, BlueprintPure, Category = "Mikdash|Surface")
    int32 GetRegisteredDecalCount() const { return Registered.Num(); }

    UFUNCTION(BlueprintCallable, BlueprintPure, Category = "Mikdash|Surface")
    int32 GetVisibleDecalCount() const { return VisibleCount; }

    /** Per-category visible counts from the last budget pass, in category order. */
    UFUNCTION(BlueprintCallable, BlueprintPure, Category = "Mikdash|Surface")
    TArray<int32> GetVisibleCountsByCategory() const { return LastAllocation; }

    // -- configuration ------------------------------------------------------

    /** Actor tag the release script stamps on every wear decal it places. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface")
    FName SurfaceWearTag = FName(TEXT("MikdashSurfaceWearV1"));

    /** Total decals that may be visible at once. 220 of the 460 authored. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface", meta = (ClampMin = "0"))
    int32 DecalBudget = 220;

    /** The nine categories, in the priority order the budget uses. Defaults are the
     *  shipped plan; SurfaceWearMathTest.cpp pins the same numbers. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface")
    TArray<FMikdashWearCategory> Categories;

    /** How often the budget is re-scored, seconds. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface", meta = (ClampMin = "0.05"))
    float BudgetUpdateIntervalSeconds = 0.35f;

    /** Below this camera movement the budget pass is skipped entirely, centimetres.
     *  Standing still costs nothing. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface", meta = (ClampMin = "0.0"))
    float BudgetMoveThresholdCm = 120.f;

    /** Material for the dust puff. Left unset, no puff is spawned and the actor still
     *  works; it never substitutes a placeholder. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface")
    TObjectPtr<UMaterialInterface> DustPuffMaterial;

    /** Material for the water ripple. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface")
    TObjectPtr<UMaterialInterface> RippleMaterial;

    /** Size of the footstep decal pool. Fixed: a burst recycles rather than allocates. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface", meta = (ClampMin = "1", ClampMax = "64"))
    int32 FootstepPoolSize = 12;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface", meta = (ClampMin = "0.05"))
    float FootstepLifetimeSeconds = 1.15f;

    /** Nothing spawns closer together in time than this, per actor. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface", meta = (ClampMin = "0.0"))
    float MinFootstepIntervalSeconds = 0.11f;

    /** Beyond this the footstep response is skipped: nobody can see a 12 cm puff from
     *  40 metres and it is not worth a trace. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface", meta = (ClampMin = "0.0"))
    float FootstepMaxViewDistanceCm = 4000.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface", meta = (ClampMin = "1.0"))
    float FootstepPuffRadiusCm = 34.f;

    /** How far up and down the surface query traces from the point it is given. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface", meta = (ClampMin = "1.0"))
    float SurfaceTraceUpCm = 120.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface", meta = (ClampMin = "1.0"))
    float SurfaceTraceDownCm = 260.f;

    /** Floor meshes with an explicit verified recorded-stone sample. Passed straight to
     *  MikdashSurfaceAudio::Route as evidence; anything not listed falls through to the
     *  family rules in that header, exactly as the audio path does. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface")
    TArray<FString> VerifiedStoneFloors;

    /** Floor meshes with an explicit verified recorded-soft sample. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface")
    TArray<FString> VerifiedSoftFloors;

    /** Package prefixes that are standing water. A hit on one of these sets bWater; it
     *  does NOT change the Bank, which stays whatever Route decides. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Surface")
    TArray<FString> WaterMeshPrefixes;

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    /** One registered wear decal. Weak: the release script owns these actors and this
     *  actor must never keep one alive or assume it still exists. */
    struct FRegisteredDecal
    {
        TWeakObjectPtr<UDecalComponent> Decal;
        int32  CategoryIndex = 0;
        double Importance = 1.0;
        double Score = 0.0;
        int32  RegistryIndex = 0;
    };

    void TickBudget();
    void TickFootsteps();
    bool ViewLocation(FVector& OutLocation) const;
    int32 CategoryIndexForActor(const AActor* Actor) const;
    bool BuildFloorEvidence(std::vector<std::wstring>& OutStorage,
                            std::vector<MikdashSurfaceAudio::Registration>& OutRows) const;
    int32 AcquireFootstepSlot();

    TArray<FRegisteredDecal> Registered;
    TArray<int32> LastAllocation;
    int32 VisibleCount = 0;
    FVector LastBudgetViewLocation = FVector::ZeroVector;
    bool bHasBudgetedOnce = false;

    UPROPERTY(Transient)
    TArray<TObjectPtr<UDecalComponent>> FootstepPool;

    UPROPERTY(Transient)
    TArray<TObjectPtr<UMaterialInstanceDynamic>> FootstepMaterials;

    TArray<double> FootstepExpiry;
    TArray<double> FootstepBirth;
    TArray<float>  FootstepStartRadius;
    int32  NextFootstepSlot = 0;
    double LastFootstepTime = -1000.0;

    FTimerHandle BudgetTimer;
    FTimerHandle FootstepTimer;
};
