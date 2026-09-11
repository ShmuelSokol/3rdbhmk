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
class UBoxComponent;

/** The three states of the precinct toggle. Values match MikdashEnclosure::EPrecinctState
 *  in EnclosureMath.h, where the weight table lives; do not renumber one without the other. */
UENUM(BlueprintType)
enum class EMikdashPrecinctState : uint8
{
    /** Jerusalem as it stands today. The Old City is whole, the Temple sits on its platform,
     *  and no enclosure exists. Reachable from the default by one press of the cycle key. */
    Modern     UMETA(DisplayName = "Modern (as today)"),
    /** The Yechezkel 42:15-20 precinct built: 500 reeds a side, wall and five gates, following
     *  the terrain. Modern buildings that fall inside are HIDDEN BY VISIBILITY and never
     *  destroyed, so Modern restores every one of them exactly. THIS IS THE DEFAULT STATE the
     *  level opens in (Shmuel's decision, 8 September 2026). */
    Yechezkel  UMETA(DisplayName = "Yechezkel precinct (3000 amot)"),
    /** The boundary drawn over the standing modern city as a translucent wall and a ground
     *  line of light. Nothing disappears. This is the state that shows which ground the
     *  precinct covers, so it is the one that gets the visual care. */
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
 * Yechezkel's 500 reeds are 3000 amot - 1,440 m a side at the book's own 48 cm amah - and
 * that square covers the eastern two fifths of the Old City, the Kidron, the slope of the
 * Mount of Olives, the City of David and Silwan. The level opens in YECHEZKEL: the wall
 * built as the verse states it, following the ground, with the modern buildings inside it
 * hidden. MODERN shows today's city with nothing added; OVERLAY draws the boundary over the
 * standing city so a viewer sees exactly which streets and roofs it covers. Mishnah Middot's
 * 500-AMAH Har HaBayit is offered as the other reading and drawn as its own ring.
 *
 * THE VISIBILITY CONTRACT (the part that must not be got wrong)
 * ------------------------------------------------------------
 * This actor NEVER calls Destroy(), NEVER modifies a package, NEVER touches a component's
 * mobility or transform on a building it did not spawn, and NEVER writes to disk. The only
 * visual change to a modern building is SetActorHiddenInGame. In game worlds only, a
 * fully hidden selected building also has actor collision disabled; component collision
 * settings are never rewritten. The exact retained Kotel base mesh is a conservative
 * collision exception: its whole batch keeps original collision even while hidden.
 * It records the prior visibility and actor collision in
 * HiddenBuildings and restores them on state change, on EndPlay and on
 * RestoreAllModernBuildings(). A crash mid-transition therefore loses nothing: the map on
 * disk is untouched and a reload comes back with everything visible.
 *
 * WHICH BUILDINGS - the explicit list
 * -----------------------------------
 * The modern city is batched one actor per 100 m cell, so the set to hide is a set of
 * ACTORS, and it is computed OFFLINE by Scripts/create_enclosure.py from the frozen OSM
 * partition (buildings-manifest.json components -> cells) and the facade manifest, then baked
 * here as ExplicitHideLabels by Scripts/release_enclosure.py. Every decision - including what
 * to do with a cell the wall line cuts - is recorded in
 * SourceAssets/enclosure-review/precinct-<Target>.json. When the list is empty the actor
 * falls back to the geometric centroid rule over actor bounds, which is coarser and is
 * reported as such by GetHideListResolution().
 *
 * TERRAIN-FOLLOWING
 * -----------------
 * The wall does not sit on the level plane. A ground profile (601 stations a side, highest and
 * lowest ground under the footprint) is baked onto GroundProfileHighZCm / GroundProfileLowZCm
 * by the release script, from the OSM terrain grid and the FutureMountV1 tile receipts. Every
 * wall, gate and corner instance takes its own Z from GroundSpan(): plinth on the highest
 * ground it crosses, a substructure box (FoundationModuleMesh) filling down to the lowest
 * ground less a one-amah footing. Where the east and south walls drop into the Kidron the
 * substructure is tens of metres; the sources say nothing about that, and it is authored.
 *
 * WHY THE WALL IS INSTANCED
 * -------------------------
 * A 1.44 km wall as one static mesh is one 1.44 km bounding box: never frustum-culled, never
 * occlusion-culled, one LOD for the whole ring. As N identical modules on
 * HierarchicalInstancedStaticMeshComponents the renderer gets one draw call per component
 * with per-instance culling and LOD. 467 wall + 5 gate + 4 corner + 476 foundation + 480
 * overlay instances, 118,656 triangles in all - about 3.5% of the 3.4 M triangles of the Old
 * City facade set the YECHEZKEL state hides. Asserted in EnclosureMathTest.cpp.
 *
 * TWO MAPS. The main map is baked at 50 Unreal cm per amah; the isolated candidate at 48.
 * WorldCmPerAmah and CourtPlatformHalfExtentCm are set per map by the release script; the
 * modules (baked at 50) scale uniformly by WorldCmPerAmah / 50. The city and terrain are
 * metric in both and do not move.
 *
 * ALL ARITHMETIC IS IN EnclosureMath.h, engine-free and tested standalone. This actor owns
 * components, timers and materials, and nothing else.
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

    /** The state the level opens in. YECHEZKEL by decision: the precinct exactly as 42:15-20
     *  states it is the default view; MODERN and OVERLAY remain one and two presses away. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|State")
    EMikdashPrecinctState InitialState = EMikdashPrecinctState::Yechezkel;

    /** The level's baked world scale, Unreal cm per amah: 50 on the main map, 48 on the
     *  candidate. Set by the release script from its target; the modules scale by this / 50. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Shape")
    float WorldCmPerAmah = 50.0f;

    /** Centre of the measured court, in world centimetres. The precinct is NOT centred on it:
     *  the square is anchored by the west and north clearances (see EnclosureMath.h). Left at
     *  the origin because architecture-manifest.json bakes world positions into the vertices
     *  and spawns every measured mesh at (0,0,0), so the measured court centre IS the origin.
     *  release_enclosure.py proves this from the receipts and refuses to place otherwise. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Shape")
    FVector2D CourtCentreUnrealCm = FVector2D(0.0, 0.0);

    /** Half-extent of the court supporting platform, world cm. SM_0127: +-8100 on the main
     *  map, +-7776 on the 48 cm candidate. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Shape")
    float CourtPlatformHalfExtentCm = 8100.0f;

    /** Clear ground west of the platform, in amot. Lishchno Tidreshu fig. 2'2 (p. 113). */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Shape")
    float ClearWestAmot = 500.0f;

    /** Clear ground north of the platform, in amot. Same figure. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Shape")
    float ClearNorthAmot = 501.0f;

    /** Nominal length of one wall module in AMOT (25). Snapped by PlanWall so a side is a
     *  whole number of modules; a fractional last module shows as a seam from the air. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Wall")
    float WallModuleLengthAmot = 25.0f;

    /** Wall height in amot. Yechezkel 40:5 gives the wall a reed - six amot - of thickness and
     *  of height; the book (pp. 115-117) reads that as the outer wall's own section. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Wall")
    float WallHeightAmot = 6.0f;

    /** How far below the LOWEST ground a module crosses its substructure reaches, in amot.
     *  AUTHORED; one amah. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Wall")
    float FoundationFootingAmot = 1.0f;

    /** Wall thickness in amot. Yechezkel 40:5: a reed. The paved deck stops one of these
     *  inside the outer face, so the wall stands at the plaza's edge and not on it. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Wall")
    float WallThicknessAmot = 6.0f;

    /** Spacing of the overlay ribbon quads and of the ground line of light, in amot (25). */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Overlay")
    float OverlaySpacingAmot = 25.0f;

    // ---------------------------------------------------------------------
    // The plaza (Shmuel's decision of 9 September 2026 - see EnclosureMath.h section 6b)
    // ---------------------------------------------------------------------

    /** Build the flat paved deck that fills the precinct, its retaining walls where the
     *  ground falls away and its scarp where the ground rises. TRUE by decision: the
     *  YECHEZKEL state used to hide the modern buildings and leave bald DEM terrain, which
     *  read as a patch cut out of the city rather than as a place. Turning this off restores
     *  exactly the previous behaviour, wall grounding included, and is the honest fallback
     *  when the plaza meshes are missing. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Plaza")
    bool bBuildPlaza = true;

    /** cp19: a 45-degree wash on every batter ledge of the retaining (fill) ring, so the ledge line
     *  survives at the aerial camera. Extra instances of the same band mesh; see PlazaBandIsLedge. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Plaza")
    bool bPlazaLedgeWash = true;

    /** The seven plaza modules. Any of them null simply omits that component's instances;
     *  a plaza with no deck tile is not built at all and GetPlazaStatus() says so. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Plaza|Assets")
    TObjectPtr<UStaticMesh> PlazaDeckTileMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Plaza|Assets")
    TObjectPtr<UStaticMesh> PlazaWayTileMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Plaza|Assets")
    TObjectPtr<UStaticMesh> PlazaRibMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Plaza|Assets")
    TObjectPtr<UStaticMesh> PlazaKerbMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Plaza|Assets")
    TObjectPtr<UStaticMesh> PlazaChannelMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Plaza|Assets")
    TObjectPtr<UStaticMesh> PlazaRetainingBandMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Plaza|Assets")
    TObjectPtr<UStaticMesh> PlazaStepMesh;

    /** Field paving. Wants five per-instance custom data floats - cos and sin of the panel's
     *  course angle, the panel's UV origin in cm on both axes, and a tonal offset - so that
     *  one component can lay 14,000 tiles in five directions from one draw call. A material
     *  without those parameters still renders; it simply repeats, which is the defect the
     *  plaza exists to fix, so the release script proves the parameters are there. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Plaza|Assets")
    TObjectPtr<UMaterialInterface> PlazaPavingMaterial;
    /** Large dressed slabs, for the five processional ways. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Plaza|Assets")
    TObjectPtr<UMaterialInterface> PlazaSlabMaterial;
    /** Herodian ashlar, for the ribs, kerbs, channels, retaining bands and steps - the same
     *  family as the precinct wall and the Kotel. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Plaza|Assets")
    TObjectPtr<UMaterialInterface> PlazaAshlarMaterial;

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
    /** A plain 1250 x 360 x 100 cm box (at 50 cm/amah), scaled in Z per instance to the
     *  substructure depth. Null draws no foundations: the wall then floats where the ground
     *  falls away under a module. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Assets")
    TObjectPtr<UStaticMesh> FoundationModuleMesh;
    /** A unit slab standing on its lower edge, used for the translucent boundary band. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Assets")
    TObjectPtr<UStaticMesh> OverlayQuadMesh;

    /** Translucent material for the overlay band. Must expose scalar "Opacity" and
     *  "Emissive"; missing parameters are ignored rather than fatal. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Assets")
    TObjectPtr<UMaterialInterface> OverlayMaterial;
    /** Opaque stone material for the built wall, gates, corners and foundations. A scalar
     *  "DissolveAmount" is driven if the material has one. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Assets")
    TObjectPtr<UMaterialInterface> WallMaterial;

    /** Ground profile: StepsPerSide steps per side, so StepsPerSide + 1 stations a side, four
     *  sides consecutively (north, east, south, west, each from its clockwise start corner).
     *  Highest and lowest ground under the wall footprint at each station, world cm. Baked by
     *  the release script from SourceAssets/enclosure-review/precinct-<Target>.json; empty
     *  means "level plane", which is reported by GetGroundProfileStatus(). */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Ground")
    int32 GroundProfileStepsPerSide = 0;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Ground")
    TArray<float> GroundProfileHighZCm;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Ground")
    TArray<float> GroundProfileLowZCm;

    /** The exact actor labels the YECHEZKEL state hides, computed offline (see the class
     *  comment). When non-empty this list IS the selection; the geometric rule is not used. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Selection")
    TArray<FString> ExplicitHideLabels;

    /** The same set as static-mesh ASSET NAMES (SM_JerusalemBuildings_Grid_*,
     *  SM_OldCityFacades_Grid_*, SM_OldCityInfill_Grid_*), one per hidden actor. Actor labels
     *  are editor data and can be empty in a cooked build; the mesh an actor renders is not.
     *  An actor is in the hide set when EITHER its label or its mesh name is listed. The
     *  release script derives these from the labels and proves the mapping against the level. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Selection")
    TArray<FString> ExplicitHideMeshNames;

    /** Actor-label prefixes treated as modern buildings that may be hidden by the FALLBACK
     *  geometric rule (only when ExplicitHideLabels is empty). */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Selection")
    TArray<FString> ModernBuildingLabelPrefixes;

    /** Label prefixes that must NEVER be hidden or considered, whatever their bounds say.
     *  This is where the 400 m terrain tiles and the hollow union envelopes are kept out.
     *  Applied to the explicit list too, as a last guard. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Selection")
    TArray<FString> ExcludedLabelPrefixes;

    /** ------------------------------------------------------------------------------------
     *  TAGGED STATE ACTORS. Some things the precinct must swap are not buildings and can
     *  never be. A terrain tile carries no building identity - BuildingIdentityLabel returns
     *  an EMPTY label for any mesh outside the two audited building folders, and an actor
     *  whose single component is instanced is refused outright - and that narrowness is
     *  load-bearing: it is what keeps the 269-entry audited hide list from drifting. A
     *  roofscape batch is one actor holding a single HISM, refused by the same two rules. So
     *  no value in ExplicitHideLabels, ExplicitHideMeshNames or ModernBuildingLabelPrefixes
     *  can ever reach either of them. They are driven by ACTOR TAG instead, which the release
     *  scripts write when they place the actor, and never by mesh path or actor name.
     *
     *  The rule is one line and it composes: an actor is hidden when ANY tag it carries
     *  appears in the list for the phase now standing. An actor carrying a tag from BOTH
     *  lists - the one terrain tile that is at once the precinct's original and the Kotel
     *  plaza's original, because a twin of it stands in every state - is hidden in every
     *  state, which is exactly right and needs no special case.
     *
     *  Hidden while the Yechezkel precinct stands (SolidWall > 0), shown otherwise. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Selection")
    TArray<FName> HideWhileWallStandsTags;

    /** The reverse phase: hidden while today's city stands (MODERN and OVERLAY), shown while
     *  the precinct does. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Precinct|Selection")
    TArray<FName> HideWhileModernCityStandsTags;

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

    /** Yechezkel -> Modern -> Overlay -> Yechezkel. Bind this to a key in the player
     *  controller; from the default one press shows today's city, two the overlay. */
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

    /** Gather and build the ring WITHOUT touching any building's visibility. This is what the
     *  release script calls in the editor world for its numeric readback, so a commandlet never
     *  leaves an editor actor hidden; nothing it does is saved. */
    UFUNCTION(BlueprintCallable, Category = "Precinct")
    void MeasureWithoutHiding();

    /** How many modern building actors the current selection would hide. Counts, never hides. */
    UFUNCTION(BlueprintPure, Category = "Precinct")
    int32 CountModernBuildingsInside() const;

    /** How the explicit hide list resolved against the loaded level: labels found once,
     *  labels missing, labels found more than once (a duplicate label is ambiguous and is
     *  refused - all copies are left visible and reported here). Zeros when the list is empty. */
    UFUNCTION(BlueprintPure, Category = "Precinct")
    void GetHideListResolution(int32& OutFound, int32& OutMissing, int32& OutDuplicated) const;

    /** FNV-1a over the sorted labels that WILL be hidden, so the release receipt can prove
     *  the level resolved exactly the recorded set. Hex, 16 characters. */
    UFUNCTION(BlueprintPure, Category = "Precinct")
    FString GetHideSetFingerprint() const;

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

    /** The four outer faces in world cm as (West, North, East, South). */
    UFUNCTION(BlueprintPure, Category = "Precinct")
    FVector4 GetOuterFacesCm() const;

    /** Lowest and highest plinth Z of the wall instances on one side (0 north, 1 east, 2 south,
     *  3 west), world cm, as (Min, Max). Both zero when the ring has not been built. */
    UFUNCTION(BlueprintPure, Category = "Precinct")
    FVector2D GetWallBaseZRangeCm(int32 Side) const;

    /** Deepest substructure on one side, world cm. */
    UFUNCTION(BlueprintPure, Category = "Precinct")
    float GetDeepestFoundationCm(int32 Side) const;

    /** "profile" when every instance took its Z from the baked profile, "level-plane" when
     *  the profile was empty or malformed and the ring sits at Z 0. */
    UFUNCTION(BlueprintPure, Category = "Precinct")
    FString GetGroundProfileStatus() const;

    /** Number of instances per component after the last build: (Wall, Gate, Corner, Foundation)
     *  and the overlay count separately, for the receipt. */
    UFUNCTION(BlueprintPure, Category = "Precinct")
    FVector4 GetInstanceCounts() const;
    UFUNCTION(BlueprintPure, Category = "Precinct")
    int32 GetOverlayInstanceCount() const;

    /** How many tagged state actors the last gather matched, split by which phase hides them.
     *  A zero here means the tags in the level and the tags in these lists do not agree,
     *  which is otherwise completely silent. For the receipt. */
    UFUNCTION(BlueprintPure, Category = "Precinct")
    void GetStateTaggedCounts(int32& OutMatched, int32& OutHiddenWithWall,
                              int32& OutHiddenWithCity) const;

    /** Instances per plaza component after the last build, in the order the receipt lists
     *  them. Eight numbers rather than a struct so a Blueprint or a Python readback can pull
     *  them without a reflected type. */
    UFUNCTION(BlueprintPure, Category = "Precinct|Plaza")
    void GetPlazaCounts(int32& OutDeckTiles, int32& OutWayTiles, int32& OutRibs, int32& OutKerbs,
                        int32& OutChannels, int32& OutRetainingBands, int32& OutScarpBands,
                        int32& OutSteps) const;

    /** Triangles the plaza adds at LOD0 over all its instances, from the module budget in
     *  EnclosureMath.h times the counts above. The generator writes the same number. */
    UFUNCTION(BlueprintPure, Category = "Precinct|Plaza")
    int32 GetPlazaTriangleCount() const;

    /** Deck top in world cm. Zero, and section 6b of EnclosureMath.h is why. */
    UFUNCTION(BlueprintPure, Category = "Precinct|Plaza")
    float GetPlazaDeckTopZCm() const;

    /** The paved rectangle in world cm as (XMin, YMin, XMax, YMax): the precinct square
     *  inset by one wall thickness on every side. */
    UFUNCTION(BlueprintPure, Category = "Precinct|Plaza")
    FVector4 GetPlazaExtentCm() const;

    /** Paving cells across and down, and how many distinct super-panels the frozen split
     *  produced over them. The panel count is the single number that proves the runtime and
     *  Scripts/create_precinct_plaza.py laid the same plaza. */
    UFUNCTION(BlueprintPure, Category = "Precinct|Plaza")
    void GetPlazaGrid(int32& OutCellsX, int32& OutCellsY, int32& OutPanels) const;

    /** Tallest retaining stack (fill) and scarp (cut) on one side, world cm, as (Retaining,
     *  Scarp). Both zero when the plaza has not been built. */
    UFUNCTION(BlueprintPure, Category = "Precinct|Plaza")
    FVector2D GetPlazaFaceHeightsCm(int32 Side) const;

    /** "built", "disabled" when bBuildPlaza is false, "no-deck-mesh" when the deck tile is
     *  missing. Never a silent nothing: a plaza that did not build must say why. */
    UFUNCTION(BlueprintPure, Category = "Precinct|Plaza")
    FString GetPlazaStatus() const;

    /** Walkable collision of the runtime plaza (EnclosureMath.h section 6c): deck proxy boxes,
     *  gate bridges, and the instance bodies of the inside gate flights, retaining and scarp.
     *  Game worlds only, and on only while the plaza is visible. Launch with
     *  -MikdashNoPlazaCollision to build none of it (the frame-time A/B switch). */
    UFUNCTION(BlueprintPure, Category = "Precinct|Plaza")
    FString GetPlazaCollisionStatus() const;

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
    /** The deck, its ways, ribs, kerbs, channels, retaining/scarp faces and gate stairs.
     *  Called by BuildRing with the square and the ground profile it already has, because
     *  the plaza's retaining stacks must be driven by the SAME profile the wall stands on -
     *  two independent samplings of the ground is how a wall ends up floating over its own
     *  retaining wall. */
    void BuildPlaza(const MikdashEnclosure::FSquare& Square,
                    const MikdashEnclosure::FGroundProfile& Profile);
    bool PlazaEnabled() const;
    /** Section 6c. Destroys the proxies of a previous build. */
    void ClearPlazaCollision();
    void AddPlazaCollisionBox(const MikdashEnclosure::FPlazaCollisionBox& Box, FName Kind);
    /** Collision follows visibility, in game worlds only - the rule ApplyStateTaggedActors
     *  already follows for the tagged actors, so the whole plaza switches as one. */
    void ApplyPlazaCollision(bool bShow);
    void ApplyWeights(const MikdashEnclosure::FStateWeights& Weights);
    void GatherModernBuildings();
    /** Called from inside the GatherModernBuildings pass, BEFORE the building-identity test
     *  whose empty label is the whole reason these actors need their own channel. */
    void ConsiderStateTaggedActor(AActor* Actor);
    void ApplyStateTaggedActors(bool bWallStands);
    void RestoreStateTaggedActors();
    /** The buildings half of RestoreAllModernBuildings, on its own. */
    void RestoreHiddenBuildings();
    bool IsExcludedLabel(const FString& Label) const;
    bool IsModernBuildingLabel(const FString& Label) const;
    MikdashEnclosure::FGroundProfile MakeGroundProfile() const;
    std::vector<MikdashEnclosure::FGateOpening> MakeGates(const MikdashEnclosure::FSquare& Square) const;
    /** The actors the current rule selects, as indices into BuildingActors. */
    void SelectedBuildingIndices(TArray<int32>& OutIndices) const;

    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> WallInstances;
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> GateInstances;
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> CornerInstances;
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> FoundationInstances;
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> OverlayInstances;
    /** The plaza, in the order GetPlazaCounts reports: deck, way, rib, kerb, channel,
     *  retaining, scarp, step. Retaining and scarp share one mesh and one material but are
     *  separate components so the receipt can count fill and cut apart, which is the number
     *  that says how much of the precinct is a platform and how much is a quarry. */
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> PlazaDeckInstances;
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> PlazaWayInstances;
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> PlazaRibInstances;
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> PlazaKerbInstances;
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> PlazaChannelInstances;
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> PlazaRetainingInstances;
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> PlazaScarpInstances;
    UPROPERTY(Transient) TObjectPtr<UHierarchicalInstancedStaticMeshComponent> PlazaStepInstances;
    /** Section 6c proxies: collision only, never drawn, never saved (RF_Transient, and
     *  created only in game worlds). Tagged MikdashPlazaFloor for the footstep router. */
    UPROPERTY(Transient) TArray<TObjectPtr<UBoxComponent>> PlazaCollisionBoxes;
    UPROPERTY(Transient) TArray<TObjectPtr<UPointLightComponent>> MarkerLights;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> OverlayDynamic;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> WallDynamic;

    /** Every actor this instance has hidden, with the visibility it had when we found it, so
     *  a building that was ALREADY hidden by someone else is not "restored" into view. */
    UPROPERTY(Transient) TArray<TWeakObjectPtr<AActor>> HiddenBuildings;
    UPROPERTY(Transient) TArray<bool> HiddenBuildingsPriorHidden;
    UPROPERTY(Transient) TArray<bool> HiddenBuildingsPriorCollision;
    UPROPERTY(Transient) TArray<bool> HiddenBuildingsKeepCollision;

    /** Actors matched by HideWhileWallStandsTags / HideWhileModernCityStandsTags, with the
     *  two booleans each carried when first seen, so EndPlay puts the level back as found.
     *  Never spawned, never destroyed, never reparented here - only the booleans move. */
    UPROPERTY(Transient) TArray<TWeakObjectPtr<AActor>> StateTaggedActors;
    UPROPERTY(Transient) TArray<bool> StateTaggedHideWithWall;
    UPROPERTY(Transient) TArray<bool> StateTaggedHideWithCity;
    UPROPERTY(Transient) TArray<bool> StateTaggedPriorHidden;
    UPROPERTY(Transient) TArray<bool> StateTaggedPriorCollision;

    /** Candidates found by GatherModernBuildings. */
    TArray<TWeakObjectPtr<AActor>> BuildingActors;
    /** Exact audited mesh-to-label inverse, shared by editor/PIE and cooked builds. */
    TArray<FString> BuildingIdentityLabels;
    std::vector<MikdashEnclosure::FBuildingRef> BuildingRefs;
    /** Parallel to BuildingActors: true when the actor's label is in ExplicitHideLabels. */
    TArray<bool> BuildingInExplicitList;
    int32 ExplicitFound = 0;
    int32 ExplicitMissing = 0;
    int32 ExplicitDuplicated = 0;

    /** Per-side readback from the last BuildRing. */
    double WallBaseZMin[4] = {0.0, 0.0, 0.0, 0.0};
    double WallBaseZMax[4] = {0.0, 0.0, 0.0, 0.0};
    double DeepestFoundation[4] = {0.0, 0.0, 0.0, 0.0};
    bool bGroundFromProfile = false;

    /** Per-side readback from the last BuildPlaza: tallest retaining stack (fill) and
     *  tallest scarp (cut), world cm. */
    double PlazaRetainingMax[4] = {0.0, 0.0, 0.0, 0.0};
    double PlazaScarpMax[4] = {0.0, 0.0, 0.0, 0.0};
    int32 PlazaCellsX = 0;
    int32 PlazaCellsY = 0;
    int32 PlazaPanels = 0;
    FString PlazaStatus = TEXT("not-built");
    bool bPlazaCollisionAllowed = false;
    bool bPlazaCollisionOn = false;
    int32 PlazaDeckCollisionBoxCount = 0;
    int32 PlazaGateBridgeCount = 0;

    EMikdashPrecinctState CurrentState = EMikdashPrecinctState::Yechezkel;
    MikdashEnclosure::FDissolve Transition;
    bool bRingBuilt = false;
};
