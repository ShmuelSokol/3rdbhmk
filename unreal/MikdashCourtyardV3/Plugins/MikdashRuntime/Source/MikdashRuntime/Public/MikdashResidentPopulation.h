#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MikdashPeopleDirectory.h"
#include "ResidentCrowdRuntime.h"
#include "ResidentRouteLoop.h"
#include <vector>
#include "MikdashResidentPopulation.generated.h"

class AMikdashResidentCharacter;
class UAnimSequence;
class UMaterialInterface;
class USkeletalMesh;

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
};

/** Opt-in outer-court and Mount-platform inhabitants. Native integration and visual review
 * are still required.
 *
 * Two mutually exclusive startup paths:
 *  - InitializeReviewedPilot(): the original five reviewed native bodies already placed in
 *    the map, one of which may follow the authored extended loop.
 *  - InitializeAuthoredPeople(): reads Content/Distribution/People/people.json (staged
 *    non-UFS by DefaultGame.ini), spawns one MikdashResidentCharacter per authored person
 *    with the shared skeletal mesh, a garment material chosen by variant key, and that
 *    person's own closed loop on its own private route resource.
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

    // Set only on an explicitly adopted, fully configured authored population.
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") bool bActivateReviewedPilotOnBeginPlay = false;
    /** Opt in to the staged people directory instead of the five-figure pilot. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") bool bSpawnAuthoredPeopleOnBeginPlay = false;
    /** Path under Content/, staged non-UFS by DefaultGame.ini. Absolute paths are honoured. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") FString PeopleDirectoryFile = TEXT("Distribution/People/people.json");
    /** The dressed pilgrim rig every spawned body shares. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") TObjectPtr<USkeletalMesh> ResidentMesh;
    /** Material slot names on that rig which receive the garment variant material. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") TArray<FName> GarmentMaterialSlots;
    /** Parallel arrays: variant key from people.json -> material instance to apply. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") TArray<FString> GarmentVariantKeys;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents|People") TArray<TObjectPtr<UMaterialInterface>> GarmentMaterials;

    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") TArray<TObjectPtr<AMikdashResidentCharacter>> Bodies;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") TObjectPtr<UAnimSequence> IdleAnimation;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Residents") TObjectPtr<UAnimSequence> WalkAnimation;

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
    /** Bodies this population is actually driving: the pilot's placed actors, or the ones
     * it spawned from the directory. Only spawned bodies are destroyed on shutdown. */
    UPROPERTY(Transient) TArray<TObjectPtr<AMikdashResidentCharacter>> ActiveBodies;
    bool bBodiesWereSpawned = false;

    TSharedPtr<MikdashCrowd::Runtime> Crowd;
    TArray<FMikdashResidentRoutePlan> RoutePlans;
    TArray<FVector> Origins, Destinations;
    TArray<bool> Walking;
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
    AMikdashResidentCharacter* SpawnAuthoredBody(const MikdashPeople::Person& Individual, FString& OutReason);
    bool BindConfiguredBodies(const std::vector<MikdashCrowd::Identity>& Plans,
        const std::vector<MikdashCrowd::Route>& Routes);
};
