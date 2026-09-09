#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MikdashPeopleDirectory.h"
#include "ResidentCrowdRuntime.h"
#include "ResidentRouteLoop.h"
#include "MikdashSceneUnitsMath.h"
#include <vector>
#include "MikdashResidentPopulation.generated.h"

class AMikdashResidentCharacter;
class UAnimSequence;
class UMaterialInterface;
class USkeletalMesh;

/** One registered skeletal body the authored directory may name in "body.variant".
 * Written natively by Scripts/release_resident_bodies_v3.py from the PilgrimRigV3 import
 * receipts; read back, never assumed. The visual scale is per PERSON (people.json), not here. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashResidentBodyVariant
{
    GENERATED_BODY()
    /** Directory key, e.g. V3_Pilgrim_Man_Standard. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") FString Id;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") TObjectPtr<USkeletalMesh> SkeletalMesh;
    /** Clips must live on this mesh's own Skeleton (Interchange prefixes them with the mesh name). */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") TObjectPtr<UAnimSequence> IdleAnimation;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") TObjectPtr<UAnimSequence> WalkAnimation;
    /** Slots that receive the garment variant material: Mantle for robes, Linen for the Youth. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") TArray<FName> GarmentMaterialSlots;
    /** Mesh relative yaw so the body faces the actor's +X: -90 for a mesh that faces UE +Y (PilgrimRigV3 per receipt). */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") double MeshRelativeYaw = -90.0;
    /** Ground speed in cm/s that this variant's WalkAnimation covers at play rate 1.0 and mesh
     * scale 1.0, i.e. stride length / cycle duration. MEASURED, not assumed: forward kinematics
     * over the source GLBs gives 32.0 cm step / 64.0 cm stride per 1.200 s = 53.33 cm/s,
     * identically for all nine PilgrimRigV3 variants. The default below is that measurement, so
     * a map saved before this field existed still gets the right number without a re-apply.
     * The population derives each body's walking pace from this so the stride matches the
     * translation; 0 falls back to the anthropometric pace and the old play rate of 1.0. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") double WalkClipGroundSpeedCmPerSec = 53.33;
    /** Normalised time in the walk clip where the two feet pass each other, so the clip can be
     * entered at the pose closest to the idle stance. Measured: the ball tracks are counter-phase
     * sinusoids crossing at t = 0.30 s and 0.90 s of a 1.200 s cycle, i.e. 0.25 and 0.75. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") double WalkClipNeutralPhase = 0.25;
};

/** The body actually chosen for one spawned person: a registered variant, or the population's
 * default (V2) body when the directory names none or the named one is not usable. */
struct FMikdashResolvedBody
{
    FString VariantId;          // empty = default body
    USkeletalMesh* Mesh = nullptr;
    UAnimSequence* Idle = nullptr;
    UAnimSequence* Walk = nullptr;
    TArray<FName> GarmentSlots;
    double MeshRelativeYaw = 90.0;
    double VisualScale = 1.0;
    double WalkClipGroundSpeedCmPerSec = 0.0;
    double WalkClipNeutralPhase = 0.0;
    bool bFallback = false;
    FString Note;               // why a fallback happened; empty otherwise
};

/** One authored route plan per body. Built either from the original five-figure pilot or
 * from the staged people directory; the physical review below is identical either way.
 * Plain C++ state, never reflected and never serialized: it is rebuilt at every startup
 * from the map properties or the staged file. */
struct FMikdashResidentRoutePlan
{
    FString Key;
    TArray<FVector> Waypoints;
    TArray<FVector> LookTargets;
    /** false: the original pilot's short reviewed step. true: a closed authored loop. */
    bool bLooping = false;
    /** The pilot's original convex outer-visitor box, kept exactly as reviewed. */
    bool bPilotBox = false;
    bool bMountDeck = false;
    double FloorZ = MikdashRoute::FloorZ;
    double CorridorCm = 100.0;
    std::vector<MikdashRoute::Point2> Loop;
    /** This body's own clips; null = the population's shared IdleAnimation/WalkAnimation.
     * Raw pointers are safe: every clip here is also held by a UPROPERTY on this actor. */
    UAnimSequence* IdleClip = nullptr;
    UAnimSequence* WalkClip = nullptr;
    /** Presentational gait facts carried from the resolved body, so Tick never re-resolves. */
    double WalkClipGroundSpeedCmPerSec = 0.0;
    double WalkClipNeutralPhase = 0.0;
    double VisualScale = 1.0;
};

/** Opt-in outer-court and Mount-platform inhabitants. Native integration and visual review
 * are still required.
 *
 * Two mutually exclusive startup paths:
 *  - InitializeReviewedPilot(): the original five reviewed native bodies already placed in
 *    the map, one of which may follow the authored extended loop.
 *  - InitializeAuthoredPeople(): reads Content/Distribution/People/people.json (staged
 *    non-UFS by DefaultGame.ini), spawns one MikdashResidentCharacter per authored person
 *    with that person's registered body variant (or the shared default body), a garment
 *    material chosen by variant key, and that person's own closed loop on its own private
 *    route resource.
 *
 * Both are scripted waypoint behaviour with authored labels and authored lines. No resident
 * has a mind, decides anything, gains ritual eligibility, or is serialized. Nothing here
 * grants access: the floor and capsule review in ReviewSegment is the only physical evidence.
 */
UCLASS(BlueprintType)
class MIKDASHRUNTIME_API AMikdashResidentPopulation : public AActor
{
    GENERATED_BODY()
public:
    AMikdashResidentPopulation();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

    // Explicit activation in a live game world after visual/collision setup.
    UFUNCTION(BlueprintCallable, Category="Residents") bool InitializeReviewedPilot();
    /** Reads the staged directory and spawns one body per authored person. */
    UFUNCTION(BlueprintCallable, Category="Residents") bool InitializeAuthoredPeople();
    UFUNCTION(BlueprintCallable, Category="Residents") void SetPopulationPaused(bool Value);
    UFUNCTION(BlueprintPure, Category="Residents") bool IsPopulationActive() const { return bActive; }
    UFUNCTION(BlueprintPure, Category="Residents") FString GetPopulationStatus() const { return Status; }
    UFUNCTION(BlueprintPure, Category="Residents") bool IsExtendedRouteActive() const { return bExtendedRoute; }
    UFUNCTION(BlueprintPure, Category="Residents") FString GetExtendedRouteStatus() const { return ExtendedStatus; }
    /** What happened when the authored directory was read: version, counts, or the refusal. */
    UFUNCTION(BlueprintPure, Category="Residents") FString GetDirectoryStatus() const { return DirectoryStatus; }
    UFUNCTION(BlueprintPure, Category="Residents") FString GetResolvedDirectoryPath() const { return ResolvedDirectoryPath; }
    UFUNCTION(BlueprintPure, Category="Residents") int32 GetLivingResidentCount() const { return ActiveBodies.Num(); }
    UFUNCTION(BlueprintPure, Category="Residents") AMikdashResidentCharacter* GetResidentAt(int32 Index) const;
    /** Per-startup body accounting: how many spawned bodies used a registered variant and how many fell back. */
    UFUNCTION(BlueprintPure, Category="Residents|People") int32 GetVariantBodyCount() const { return VariantBodyCount; }
    UFUNCTION(BlueprintPure, Category="Residents|People") int32 GetFallbackBodyCount() const { return FallbackBodyCount; }

    // Set only on an explicitly adopted, fully configured authored population.
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") bool bActivateReviewedPilotOnBeginPlay = false;
    /** Opt in to the staged people directory instead of the five-figure pilot. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") bool bSpawnAuthoredPeopleOnBeginPlay = false;
    /** Path under Content/, staged non-UFS by DefaultGame.ini. Absolute paths are honoured. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") FString PeopleDirectoryFile = TEXT("Distribution/People/people.json");
    /** Source JSON and route property values are legacy inputs, never rewritten at runtime. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") FName SourceCoordinateRevision = TEXT("Legacy50.v1");
    /** The default (V2) rig: used by the pilot, by people without a "body", and as the fallback. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") TObjectPtr<USkeletalMesh> ResidentMesh;
    /** Material slot names on the default rig which receive the garment variant material. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") TArray<FName> GarmentMaterialSlots;
    /** Mesh relative yaw of the default rig (it faces UE -Y, so +90 turns it to the actor's +X). */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") double DefaultMeshRelativeYaw = 90.0;
    /** Registered skeletal bodies the directory may name; see FMikdashResidentBodyVariant. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") TArray<FMikdashResidentBodyVariant> BodyVariants;
    /** Parallel arrays: variant key from people.json -> material instance to apply. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") TArray<FString> GarmentVariantKeys;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") TArray<TObjectPtr<UMaterialInterface>> GarmentMaterials;

    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") TArray<TObjectPtr<AMikdashResidentCharacter>> Bodies;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") TObjectPtr<UAnimSequence> IdleAnimation;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") TObjectPtr<UAnimSequence> WalkAnimation;
    /** As FMikdashResidentBodyVariant::WalkClipGroundSpeedCmPerSec, for the default (V2) rig
     * and for the pilot. The V2 walk clip is the same authored motion, so the same measurement
     * applies; set 0 to opt the default body out of pace derivation. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Gait") double DefaultWalkClipGroundSpeedCmPerSec = 53.33;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Gait") double DefaultWalkClipNeutralPhase = 0.25;
    /** Give every body its own pace, cadence and gait phase from its own stable id, so a group
     * never marches in step. Off restores one uniform pace for every resident. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Gait") bool bVaryGaitPerResident = true;
    /** Derive each body's walking pace from its walk clip, and drive that clip's play rate from
     * the body's actual ground speed, so the stride matches the translation. Off restores the
     * previous behaviour: one uniform 180 cm/s and a fixed play rate of 1.0. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Gait") bool bMatchWalkClipToGroundSpeed = true;
    /** OnlyTickPoseWhenRendered on every spawned body's mesh. With two dozen skeletal bodies on
     * an RTX 2070 this is most of the animation cost; a body off screen holds its last pose.
     * DEFAULT OFF, deliberately: release_resident_bodies_v3.py -BodiesVerify reads ball_r/ball_l
     * and head bone world Z out of every spawned body, and an unrendered body would hand it a
     * stale pose and a false failure. Turn this on only after that verifier has been taught to
     * either force-render or read the same numbers another way, and measure the frame time
     * before and after rather than assuming the win. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Gait") bool bTickPoseOnlyWhenRendered = false;

    // Optional authored loop for ONE pilot body (index into Bodies), written by
    // Scripts/release_dove_people_v2.py and validated by ResidentRouteLoop.h at startup.
    // Waypoint 0 must be that body's reviewed start. When the configuration is invalid the
    // population still starts with the five short routes and GetExtendedRouteStatus says why.
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Route") int32 ExtendedRouteBodyIndex = -1;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Route") TArray<FVector> ExtendedRouteWaypoints;
    /** Goal label shown while walking TOWARD waypoint i (GetResidentGoal). */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Route") TArray<FString> ExtendedRouteLabels;
    /** What the resident does during the pause at waypoint i (GetResidentAction). */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Route") TArray<FString> ExtendedRouteActions;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Route") TArray<float> ExtendedRoutePauseSeconds;
    /** World point faced during the pause at waypoint i. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Route") TArray<FVector> ExtendedRouteLookTargets;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|Route") int32 ExtendedRouteLaps = 3;

private:
    MikdashSceneUnits::Frame ActiveSceneFrame;
    TArray<FVector> RuntimeExtendedWaypoints, RuntimeExtendedLookTargets;
    bool ResolveCoordinateFrame(FString& Reason);
    /** Bodies this population is actually driving: the pilot's placed actors, or the ones
     * it spawned from the directory. Only spawned bodies are destroyed on shutdown. */
    UPROPERTY(Transient) TArray<TObjectPtr<AMikdashResidentCharacter>> ActiveBodies;
    bool bBodiesWereSpawned = false;
    int32 VariantBodyCount = 0, FallbackBodyCount = 0;

    TSharedPtr<MikdashCrowd::Runtime> Crowd;
    TArray<FMikdashResidentRoutePlan> RoutePlans;
    TArray<FVector> Origins, Destinations;
    TArray<bool> Walking;
    /** Last play rate written to each body's single-node player; -1 forces the next write. */
    TArray<double> AppliedPlayRate;
    /** World seconds before which a refused corridor review is not retried. */
    TArray<double> ReviewCooldown;
    double FractionalSeconds = 0.0;
    bool bActive = false, bUserPaused = false;
    bool bExtendedRoute = false;
    FString Status = TEXT("Inactive: requires reviewed native bodies or a staged people directory");
    FString ExtendedStatus = TEXT("No extended route configured");
    FString DirectoryStatus = TEXT("Authored people directory not requested");
    FString ResolvedDirectoryPath;
    std::vector<MikdashRoute::Point2> LoopPoints;
    static constexpr double ExtendedLegCorridorCm = 3000.0;

    bool ReviewSegment(int32 BodyIndex, const FVector& From, const FVector& To) const;
    bool ValidateExtendedRoute(const FVector& BodyStart, FString& Reason) const;
    bool IsExtendedBody(int32 BodyIndex) const { return bExtendedRoute && BodyIndex == ExtendedRouteBodyIndex; }
    FString WaypointName(const std::string& Key, std::size_t Index) const;
    void StopPopulation();
    void DestroySpawnedBodies();

    bool LoadDirectoryText(FString& OutText, FString& OutReason);
    UMaterialInterface* GarmentFor(const FString& VariantKey) const;
    /** Chooses the registered variant named by the person, or the default body with a note.
     * Never fails: a missing or inconsistent variant is a logged fallback, not a refusal. */
    FMikdashResolvedBody ResolveBody(const MikdashPeople::Person& Individual) const;
    AMikdashResidentCharacter* SpawnAuthoredBody(const MikdashPeople::Person& Individual,
        const FMikdashResolvedBody& Body, FString& OutReason);
    bool BindConfiguredBodies(const std::vector<MikdashCrowd::Identity>& Plans,
        const std::vector<MikdashCrowd::Route>& Routes);
};
