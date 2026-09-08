#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EnclosureMath.h"
#include "MikdashEnclosure.generated.h"

class UHierarchicalInstancedStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UPointLightComponent;

/** The three states of the precinct toggle. Values match MikdashEnclosure::EPrecinctState
 *  in EnclosureMath.h, where the weight table lives; do not renumber one without the other. */
UENUM(BlueprintType)
enum class EMikdashPrecinctState : uint8
{
    /** Jerusalem as it stands today. The Old City is whole, the Temple sits on its platform,
     *  and no enclosure exists. This is the state the level loads in. */
    Modern     UMETA(DisplayName = "Modern (as today)"),
    /** The Yechezkel 42:15-20 precinct built: 500 reeds a side, wall and five gates. Modern
     *  buildings that fall inside are HIDDEN BY VISIBILITY and never destroyed, so Modern
     *  restores every one of them exactly. */
    Yechezkel  UMETA(DisplayName = "Yechezkel precinct (3000 amot)"),
    /** The boundary drawn over the standing modern city as a translucent wall and a ground
     *  line of light. Nothing disappears. This is the state that answers the question the
     *  toggle exists for - which ground the precinct actually covers - so it is the one
     *  that gets the visual care. */
    Overlay    UMETA(DisplayName = "Overlay (boundary over the modern city)"),
};

/** Which reading of the precinct the ring is built from. Both are offered because the
 *  sources genuinely disagree and this project does not adjudicate; see
 *  SourceAssets/enclosure-review/sources.md. */
UENUM(BlueprintType)
enum class EMikdashPrecinctReading : uint8
{
    /** Yechezkel 42:20 as five hundred REEDS, a reed being six amot (Yechezkel 40:5): a
     *  3000-amah square, about 1.44 km a side at the book's own amah. This is the reading
     *  Lishchno Tidreshu holds and the one the level is built for. */
    Yechezkel3000  UMETA(DisplayName = "3000 amot (500 reeds, Yechezkel)"),
    /** Mishnah Middot 2:1's Har HaBayit of the Second Temple: 500 AMOT square, one thirty-
     *  sixth of the area. Drawn as its own ring so the two can be seen at once. */
    Middot500      UMETA(DisplayName = "500 amot (Middot, Second Temple)"),
};

/** Fired whenever the state actually changes, so a HUD or a narration track can follow the
 *  toggle without polling. HiddenBuildingCount is how many modern building actors are
 *  currently hidden by this actor - zero in Modern and in Overlay, always. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FMikdashPrecinctStateSignature,
    EMikdashPrecinctState, NewState, float, TransitionSeconds, int32, HiddenBuildingCount);

/**
 * The sacred precinct of Yechezkel 42:15-20, and the three-state toggle that shows it over
 * modern Jerusalem.
 *
 * WHAT THIS ACTOR IS FOR
 * ----------------------
 * A reader is told the precinct is "five hundred reeds square" and has no idea what that
 * means over the city he knows. Yechezkel's 500 reeds are 3000 amot - roughly 1.44 km a side
 * at the book's own amah - and that square covers most of the Old City. Mishnah Middot's Har
 * HaBayit is 500 AMOT square, one thirty-sixth of the area. The commentaries reconcile the
 * two differently and this project does not choose between them; it draws both and lets a
 * viewer stand inside each.
 *
 * The OVERLAY state is the one that answers the question, because nothing vanishes: the
 * boundary is a translucent wall and a ground line of light laid over the standing city, so
 * the viewer sees exactly which streets and roofs the precinct would cover. YECHEZKEL then
 * shows the same square built, with the modern buildings inside HIDDEN. Hidden, never
 * destroyed - see the visibility contract below.
 *
 * THE VISIBILITY CONTRACT (the part that must not be got wrong)
 * ------------------------------------------------------------
 * This actor NEVER calls Destroy(), NEVER modifies a package, NEVER touches a component's
 * mobility or transform on a building it did not spawn, and NEVER writes to disk. The only
 * thing it does to a modern building is SetActorHiddenInGame plus, while a dissolve is in
 * flight, a scalar on a dynamic material instance. It records every actor it touched in
 * HiddenBuildings and restores all of them on state change, on EndPlay and on
 * RestoreAllModernBuildings(). A crash mid-transition therefore loses nothing: the map on
 * disk is untouched and a reload comes back in Modern with everything visible.
 *
 * WHY THE WALL IS INSTANCED
 * -------------------------
 * A 1.44 km wall as one static mesh is one 1.44 km bounding box: it is never frustum-culled,
 * never occlusion-culled, carries a single LOD for the whole ring, and needs a re-import to
 * change. As N identical modules on a HierarchicalInstancedStaticMeshComponent the renderer
 * gets one draw call per component with per-instance culling and per-instance LOD. At the
 * planned 1250 cm module the whole enclosure is 467 wall + 5 gate + 4 corner instances and
 * about 122k triangles - roughly four per cent of the 3.4 M triangles of the Old City facade
 * set the YECHEZKEL state hides, and comfortably inside an RTX 2070 at 1080p. The numbers are
 * planned by MikdashEnclosure::PlanWall and asserted in EnclosureMathTest.cpp, not guessed.
 *
 * ALL ARITHMETIC IS IN EnclosureMath.h, engine-free and tested standalone. This actor owns
 * components, timers and materials, and nothing else. Scripts/create_enclosure.py builds the
 * modules offline and Scripts/release_enclosure.py places this actor; all four agree about
 * where the square is because all four read that one header.
 */
UCLASS(BlueprintType, Blueprintable)
class MIKDASHRUNTIME_API AMikdashEnclosure : public AActor
{
    GENERATED_BODY()

public:
    AMikdashEnclosure();

    // ---------------------------------------------------------------------
    // Configuration
    // ---------------------------------------------------------------------

    /** Which reading the ring is built from. Changing this in the editor rebuilds the ring. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Shape")
    EMikdashPrecinctReading Reading = EMikdashPrecinctReading::Yechezkel3000;

    /** The state the level opens in. Modern, deliberately: the viewer should recognise the
     *  city before anything is added to it. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|State")
    EMikdashPrecinctState InitialState = EMikdashPrecinctState::Modern;

    /** Centre of the measured court, in world centimetres. The precinct is NOT centred on it:
     *  the square is anchored by the west and north clearances (see EnclosureMath.h). Left at
     *  the origin because architecture-manifest.json bakes world positions into the vertices
     *  and spawns every measured mesh at (0,0,0), so the measured court centre IS the origin.
     *  release_enclosure.py reads this back from the receipts rather than trusting the
     *  default, and refuses to place if the two disagree. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Shape")
    FVector2D CourtCentreUnrealCm = FVector2D(0.0, 0.0);

    /** Half-extent of the court supporting platform, world cm. SM_0127, +-8100 on both axes. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Shape")
    float CourtPlatformHalfExtentCm = 8100.0f;

    /** Clear ground west of the platform, in amot. Lishchno Tidreshu fig. 2'2 (p. 113). */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Shape")
    float ClearWestAmot = 500.0f;

    /** Clear ground north of the platform, in amot. Same figure. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Shape")
    float ClearNorthAmot = 501.0f;

    /** Nominal length of one wall module, world cm. Snapped by PlanWall so a side is a whole
     *  number of modules; a fractional last module shows as a seam from the air. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Wall")
    float WallModuleLengthCm = 1250.0f;

    /** Wall height in amot. Yechezkel 40:5 gives the wall a reed - six amot - of thickness and
     *  of height; the book (pp. 115-117) reads that as the outer wall's own section. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Wall")
    float WallHeightAmot = 6.0f;

    /** Spacing of the overlay ribbon quads and of the ground line of light, world cm. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Overlay")
    float OverlaySpacingCm = 1250.0f;

    /** Seconds a state change takes. Zero is an immediate cut, which is what a load or a
     *  console command wants. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|State")
    float TransitionSeconds = 2.5f;

    /** Modules. Left null the actor still runs and still hides buildings; it simply draws no
     *  wall, which is the honest failure mode for a missing asset. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Assets")
    TObjectPtr<UStaticMesh> WallModuleMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Assets")
    TObjectPtr<UStaticMesh> GateModuleMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Assets")
    TObjectPtr<UStaticMesh> CornerModuleMesh;
    /** A unit quad standing on its lower edge, used for the translucent boundary band. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Assets")
    TObjectPtr<UStaticMesh> OverlayQuadMesh;

    /** Translucent material for the overlay band. Must expose scalar "Opacity" and
     *  "Emissive"; missing parameters are ignored rather than fatal. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Assets")
    TObjectPtr<UMaterialInterface> OverlayMaterial;
    /** Opaque stone material for the built wall. Must expose scalar "DissolveAmount". */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Assets")
    TObjectPtr<UMaterialInterface> WallMaterial;

    /** Actor-label prefixes treated as modern buildings that may be hidden. Matched
     *  case-sensitively against the actor label, then confirmed against the mesh asset path,
     *  because labels are duplicable and asset paths are not. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Selection")
    TArray<FString> ModernBuildingLabelPrefixes;

    /** Label prefixes that must NEVER be hidden or considered, whatever their bounds say.
     *  This is where the 400 m terrain tiles and the hollow union envelopes are kept out.
     *  A terrain tile's AABB is two and a half times the whole Temple court, so without this
     *  list the selection returns a hundred per cent false positives - a failure that has
     *  already cost this project a day. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Selection")
    TArray<FString> ExcludedLabelPrefixes;

    // ---------------------------------------------------------------------
    // Run-time API
    // ---------------------------------------------------------------------

    /** Change state, dissolving over TransitionSeconds. Calling with the current state is a
     *  no-op and fires nothing. */
    UFUNCTION(BlueprintCallable, Category = "Precinct", meta = (DisplayName = "Set Precinct State"))
    void SetPrecinctState(EMikdashPrecinctState NewState);

    /** Change state with an explicit duration. Zero or negative cuts immediately. */
    UFUNCTION(BlueprintCallable, Category = "Precinct")
    void SetPrecinctStateOver(EMikdashPrecinctState NewState, float Seconds);

    /** Modern -> Overlay -> Yechezkel -> Modern. Bound to a key by the player controller. */
    UFUNCTION(BlueprintCallable, Category = "Precinct")
    void CyclePrecinctState();

    UFUNCTION(BlueprintPure, Category = "Precinct")
    EMikdashPrecinctState GetPrecinctState() const { return CurrentState; }

    /** True while a dissolve is in flight. */
    UFUNCTION(BlueprintPure, Category = "Precinct")
    bool IsTransitioning() const;

    /** Show every building this actor has hidden, clear the record, and stop. Safe to call at
     *  any time and idempotent; EndPlay calls it. */
    UFUNCTION(BlueprintCallable, Category = "Precinct")
    void RestoreAllModernBuildings();

    /** Re-run the selection over the current level and rebuild the ring. Called on BeginPlay
     *  and by the release script after placement. */
    UFUNCTION(BlueprintCallable, Category = "Precinct")
    void RebuildPrecinct();

    /** How many modern buildings fall inside the boundary right now. Counts, never hides. */
    UFUNCTION(BlueprintPure, Category = "Precinct")
    int32 CountModernBuildingsInside() const;

    /** Side of the precinct in metres under one opinion about the amah, for a HUD caption.
     *  Keys: "naeh" (48, and the book's own), "project" (50), "feinstein" (54),
     *  "chazon-ish" (57.6), "chazon-ish-stringent" (58). An unknown key returns 0 rather
     *  than a plausible-looking default. */
    UFUNCTION(BlueprintPure, Category = "Precinct")
    float GetPrecinctSideMetresUnderAmah(const FString& OpinionKey) const;

    /** The four clearances actually measured off the placed square, in amot, as
     *  (West, North, East, South). Reported rather than assumed - see the long note in
     *  EnclosureMath.h about why the book's ordering cannot hold on this project's envelope. */
    UFUNCTION(BlueprintPure, Category = "Precinct")
    FVector4 GetMeasuredClearancesAmot() const;

    UPROPERTY(BlueprintAssignable, Category = "Precinct")
    FMikdashPrecinctStateSignature OnPrecinctStateChanged;

    // ---------------------------------------------------------------------

    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;
#if WITH_EDITOR
    virtual void PostEditChangeProperty(FPropertyChangedEvent& Event) override;
#endif

    /** The square, in the engine-free form every consumer shares. Public so the release
     *  script's readback can compare numbers rather than screenshots. */
    MikdashEnclosure::FSquare GetSquare() const;

private:
    void BuildRing();
    void ApplyWeights(const MikdashEnclosure::FStateWeights& Weights);
    void GatherModernBuildings();
    bool IsExcludedLabel(const FString& Label) const;
    bool IsModernBuildingLabel(const FString& Label) const;

    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> WallInstances;
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> GateInstances;
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> CornerInstances;
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> OverlayInstances;
    UPROPERTY(Transient) TArray<TObjectPtr<UPointLightComponent>> MarkerLights;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> OverlayDynamic;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> WallDynamic;

    /** Every actor this instance has hidden, with the visibility it had when we found it, so
     *  a building that was ALREADY hidden by someone else is not "restored" into view. */
    UPROPERTY(Transient) TArray<TWeakObjectPtr<AActor>> HiddenBuildings;
    UPROPERTY(Transient) TArray<bool> HiddenBuildingsPriorHidden;

    /** Candidates found by GatherModernBuildings, in ascending id order. */
    TArray<TWeakObjectPtr<AActor>> BuildingActors;
    std::vector<MikdashEnclosure::FBuildingRef> BuildingRefs;

    EMikdashPrecinctState CurrentState = EMikdashPrecinctState::Modern;
    MikdashEnclosure::FDissolve Transition;
    bool bRingBuilt = false;
};
