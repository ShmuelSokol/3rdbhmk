#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FlockMath.h"
#include <vector>
#include "MikdashBirdFlock.generated.h"

class UHierarchicalInstancedStaticMeshComponent;
class UStaticMesh;

/** Which real bird this flock is. Values MUST match MikdashFlock::SpeciesId in FlockMath.h,
 *  where every wingspan figure and its published source is recorded. */
UENUM(BlueprintType)
enum class EMikdashBirdSpecies : uint8
{
    /** Columba livia - the plaza and Kotel pigeons. Wild-type blue-bar plumage, deliberately
     *  NOT the white of the player's dove pawn. */
    RockDove        UMETA(DisplayName = "Rock dove (feral pigeon)"),
    /** Apus apus - the screaming scythes round the Old City walls at dusk, spring to July. */
    CommonSwift     UMETA(DisplayName = "Common swift"),
    /** Corvus cornix - twos and threes on parapets and roofs. */
    HoodedCrow      UMETA(DisplayName = "Hooded crow"),
    /** Falco tinnunculus - a lone bird riding lift, for scale. */
    CommonKestrel   UMETA(DisplayName = "Common kestrel"),
    /** Gyps fulvus - provided, but see FlockMath.h: not a routine Jerusalem city bird today. */
    GriffonVulture  UMETA(DisplayName = "Griffon vulture"),
};

/** Soundscape hook. THIS MODULE ADDS NO AUDIO: it never loads, creates, spawns or plays a
 *  sound, and it holds no USoundBase reference. It only announces that a bird event just
 *  happened, so the separately-owned soundscape work can decide whether to play anything.
 *
 *  EventName is one of:
 *      "Call"      a species-typical call is due at this flock (rate-limited by
 *                  MikdashFlock::ShouldCall at the species' CallMeanIntervalSeconds)
 *      "Wingburst" several birds left their ledges together - the clatter of a flock going up
 *      "Startle"   Startle() was called on this flock; Intensity is the number of birds affected
 *      "Land"      several birds settled onto ledges together
 *  SpeciesName is the UENUM display key ("RockDove", "CommonSwift", ...).
 *  WorldLocationCm is where the event happened, in world centimetres.
 *  Intensity is a count of birds for the burst events and 1.0 for a call.
 *
 *  Bind in Blueprint (OnBirdSound) or in C++ (AddDynamic). The equivalent named entry point is
 *  AMikdashBirdFlock::EmitBirdSound, which is BlueprintCallable so a soundscape actor can also
 *  drive it directly for a scripted moment. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_FourParams(FMikdashBirdSoundSignature,
    FName, EventName, FName, SpeciesName, FVector, WorldLocationCm, float, Intensity);

/** Ambient bird flock drawn as HierarchicalInstancedStaticMeshComponents - one component per
 *  wing pose (up-stroke, level, down-stroke, perched), with every bird holding one instance in
 *  each and only its current pose carrying a non-zero scale. Per-instance transforms are
 *  rewritten from a timer, never from Tick.
 *
 *  ALL BEHAVIOUR IS IN FlockMath.h and is engine-free and unit-tested standalone
 *  (Plugins/MikdashRuntime/Tests/FlockMathTest.cpp). This actor is the adapter: it owns the
 *  components, the timer, the distance tiering and the sound hook, and nothing else.
 *
 *  COST. The update is O(birds stepped) - neighbours come from a uniform grid, not an
 *  all-pairs loop - and only BirdsPerUpdate of the flock are stepped per timer tick, so the
 *  work per update is a fixed slice however large the flock is. Beyond CullRadiusCm the flock
 *  stops simulating entirely and its components are hidden. GetEstimatedMillisecondsPerFrame()
 *  reports the measured cost so the budget can be checked in a running build rather than
 *  asserted here.
 *
 *  SAFETY. Every component is NoCollision and every bird mesh is imported NoCollision. Ambient
 *  birds must never block, push, or be traced against anything. In particular the player's
 *  white dove pawn (AMikdashDovePawn, F key) is spawned at runtime just above the walker with
 *  AdjustIfPossibleButDontSpawnIfColliding; a colliding flock overhead could have blocked that
 *  take-off. With NoCollision it cannot. This actor never references, spawns, destroys or
 *  reads AMikdashDovePawn.
 *
 *  WHAT THIS IS NOT. Not a simulation of bird behaviour, not migration, not a census, and not
 *  a claim about how many birds of any species are over Jerusalem. It is scenery. */
UCLASS(BlueprintType, Blueprintable)
class MIKDASHRUNTIME_API AMikdashBirdFlock : public AActor
{
    GENERATED_BODY()
public:
    AMikdashBirdFlock();

    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
#if WITH_EDITOR
    virtual void PostEditChangeProperty(FPropertyChangedEvent& Event) override;
#endif

    // ---------------------------------------------------------------- authored properties
    /** Master on/off. Clearing it stops the timer, hides every instance and leaves the actor
     *  in the level; setting it again re-seeds and restarts. Safe to toggle at any time. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds")
    bool bFlockEnabled = true;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds")
    EMikdashBirdSpecies Species = EMikdashBirdSpecies::RockDove;

    /** Birds in this flock. Clamped to MaxBirds. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds", meta = (ClampMin = "0", ClampMax = "600"))
    int32 BirdCount = 60;

    /** Centre of the flock volume, in world centimetres. Zero means "use the actor's own
     *  location", which is what Scripts/release_birds.py relies on. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds")
    FVector HomePointCm = FVector::ZeroVector;

    /** Radius of the cylinder the flock stays inside, centimetres. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds", meta = (ClampMin = "100.0"))
    float RadiusCm = 4000.f;

    /** Soft-then-hard ceiling and floor of the flock volume, world Z in centimetres. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds")
    float CeilingZCm = 4000.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds")
    float FloorZCm = 800.f;

    /** Thickness of the band inside each surface where birds are steered back rather than
     *  clamped, centimetres. The clamp still exists behind it and is what the test asserts. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Volume", meta = (ClampMin = "10.0"))
    float SoftBandCm = 500.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Volume", meta = (ClampMin = "10.0"))
    float RadialSoftBandCm = 800.f;

    /** Deterministic seed. Two flocks with the same seed and count fly identically. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds")
    int32 FlockSeed = 20260908;

    /** Uniform scale on every bird mesh. 1.0 is the real published wingspan. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds", meta = (ClampMin = "0.05"))
    float SizeScale = 1.f;

    /** The four pose meshes, in MikdashFlock::PoseIndex order: up-stroke, level, down-stroke,
     *  perched. Generated by Scripts/create_birds.py, imported by Scripts/release_birds.py.
     *  A missing entry disables that pose (its birds fall back to the level mesh); an empty
     *  array leaves the flock inactive and GetFlockStatus() says so. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Meshes")
    TArray<TObjectPtr<UStaticMesh>> PoseMeshes;

    // ------------------------------------------------------------------------ perching
    /** Ledge points in WORLD centimetres. A perching species sits a fraction of the flock on
     *  these and launches from them again; duplicates are dropped at BeginPlay so two birds
     *  can never share a point. Empty means the flock never lands. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Perching")
    TArray<FVector> PerchPointsCm;

    /** Named ledges: every actor carrying one of these tags contributes perch points along the
     *  top edge of its bounds. Resolved once at BeginPlay; what was found (or not found) is
     *  reported by GetPerchSourceStatus(), so a missing tag is visible instead of silent. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Perching")
    TArray<FName> PerchActorTags;

    /** Perch points generated per tagged actor, spread along its longer horizontal axis. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Perching", meta = (ClampMin = "1", ClampMax = "64"))
    int32 PerchPointsPerTaggedActor = 8;

    /** How far above the tagged actor's bounds top a generated perch sits, centimetres. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Perching")
    float PerchLiftCm = 12.f;

    // ------------------------------------------------------------------------- budget
    /** Timer interval when the viewer is inside NearDistanceCm. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Budget", meta = (ClampMin = "0.016"))
    float NearUpdateIntervalSeconds = 0.05f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Budget", meta = (ClampMin = "0.016"))
    float MidUpdateIntervalSeconds = 0.1f;

    /** Timer interval for a distant but still visible flock. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Budget", meta = (ClampMin = "0.016"))
    float FarUpdateIntervalSeconds = 0.25f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Budget")
    float NearDistanceCm = 12000.f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Budget")
    float MidDistanceCm = 40000.f;

    /** Beyond this distance from every local viewer the flock stops simulating and hides.
     *  Generous on purpose: a flock should never pop into life inside the player's view. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Budget")
    float CullRadiusCm = 120000.f;

    /** Birds stepped per timer tick. The rest catch up on later ticks (round robin), so the
     *  work per update is bounded whatever BirdCount is. 0 means "all of them". */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Budget", meta = (ClampMin = "0"))
    int32 BirdsPerUpdate = 120;

    /** Hard ceiling on BirdCount for any one flock actor. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Budget", meta = (ClampMin = "1"))
    int32 MaxBirds = 600;

    // -------------------------------------------------------------------- sound hook
    /** See FMikdashBirdSoundSignature. No audio is produced by this module. */
    UPROPERTY(BlueprintAssignable, Category = "Birds|Audio")
    FMikdashBirdSoundSignature OnBirdSound;

    /** Set false to stop announcing bird events entirely (the flock still flies). */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Birds|Audio")
    bool bAnnounceBirdSounds = true;

    /** Broadcast one bird event. The named entry point for the soundscape work; also used
     *  internally. Does nothing while bAnnounceBirdSounds is false. */
    UFUNCTION(BlueprintCallable, Category = "Birds|Audio")
    void EmitBirdSound(FName EventName, FVector WorldLocationCm, float Intensity);

    // ------------------------------------------------------------------------ commands
    /** Scatter: every bird within RadiusCm of Origin launches (if sitting) and flees for the
     *  species' startle time. Announces "Startle". */
    UFUNCTION(BlueprintCallable, Category = "Birds")
    void Startle(FVector OriginCm, float StartleRadiusCm);

    /** Master on/off at runtime. */
    UFUNCTION(BlueprintCallable, Category = "Birds")
    void SetFlockEnabled(bool bEnabled);

    /** Re-seed and rebuild from the current properties. Called by BeginPlay and by editor
     *  property changes; safe to call at runtime. */
    UFUNCTION(BlueprintCallable, Category = "Birds")
    bool RebuildFlock();

    // -------------------------------------------------------------------------- status
    UFUNCTION(BlueprintPure, Category = "Birds") int32 GetLiveBirdCount() const { return static_cast<int32>(Birds.size()); }
    UFUNCTION(BlueprintPure, Category = "Birds") int32 GetPerchedBirdCount() const;
    UFUNCTION(BlueprintPure, Category = "Birds") int32 GetResolvedPerchCount() const { return static_cast<int32>(Perches.size()); }
    UFUNCTION(BlueprintPure, Category = "Birds") FString GetFlockStatus() const { return Status; }
    UFUNCTION(BlueprintPure, Category = "Birds") FString GetPerchSourceStatus() const { return PerchSourceStatus; }
    UFUNCTION(BlueprintPure, Category = "Birds") bool IsFlockSimulating() const { return bSimulating; }
    UFUNCTION(BlueprintPure, Category = "Birds") float GetCurrentUpdateIntervalSeconds() const { return CurrentInterval; }
    /** Mean wall-clock cost of one flock update, milliseconds, over the last 64 updates. */
    UFUNCTION(BlueprintPure, Category = "Birds") float GetAverageUpdateMilliseconds() const { return AverageUpdateMs; }
    /** Mean game-thread cost of this flock per rendered frame at FramesPerSecond, milliseconds.
     *  This is the measured number the budget should be judged on. */
    UFUNCTION(BlueprintPure, Category = "Birds") float GetEstimatedMillisecondsPerFrame(float FramesPerSecond = 60.f) const;
    /** Circular resultant of the flock's wing phases: 1 is lockstep, 0 is fully decorrelated. */
    UFUNCTION(BlueprintPure, Category = "Birds") float GetWingPhaseCoherence() const;

protected:
    /** One component per pose, in MikdashFlock::PoseIndex order. */
    UPROPERTY(VisibleAnywhere, Category = "Birds|Meshes")
    TArray<TObjectPtr<UHierarchicalInstancedStaticMeshComponent>> PoseComponents;

private:
    void UpdateFlock();
    void ApplyTimer(float IntervalSeconds);
    void StopSimulation(const FString& Reason);
    bool ResolvePerches();
    void RebuildInstances();
    void WriteInstanceTransform(int32 BirdIndex, bool bForcePoseWrite);
    float DistanceToNearestViewerCm() const;
    MikdashFlock::FlockConfig MakeConfig() const;
    FName SpeciesName() const;

    std::vector<MikdashFlock::Bird> Birds;
    std::vector<MikdashFlock::PerchPoint> Perches;
    MikdashFlock::Grid NeighbourGrid;
    MikdashFlock::Grid OverlapGrid;
    TArray<int32> CurrentPose;

    FTimerHandle UpdateTimer;
    int32 Cursor = 0;
    double SimulationTime = 0.0;
    double NextCallTime = 0.0;
    MikdashFlock::Vec3 LastStartleOrigin;
    float CurrentInterval = 0.f;
    float AverageUpdateMs = 0.f;
    int32 UpdateSamples = 0;
    bool bSimulating = false;
    FString Status = TEXT("Not started");
    FString PerchSourceStatus = TEXT("Perches not resolved");
};
