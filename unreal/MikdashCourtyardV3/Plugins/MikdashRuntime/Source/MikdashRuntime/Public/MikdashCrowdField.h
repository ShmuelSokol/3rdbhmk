#pragma once
#include "CoreMinimal.h"
#include "CrowdFieldMath.h"
#include "CrowdGroupMath.h"
#include "GameFramework/Actor.h"
#include "MikdashCrowdField.generated.h"

class UStaticMesh;
class UMaterialInterface;
class UHierarchicalInstancedStaticMeshComponent;

/** How a zone answers "what is the ground height at this XY?" when a line trace cannot. */
UENUM(BlueprintType)
enum class EMikdashCrowdGround : uint8
{
    /** Z = GroundZBase everywhere in the zone. */
    Flat        UMETA(DisplayName = "Flat"),
    /** Z = GroundZBase + GroundSlopeX * X + GroundSlopeY * Y. For the sloping Kotel and street zones. */
    Plane       UMETA(DisplayName = "Fitted plane"),
};

/** A keep-out polygon. Instances are never seeded in one and are turned back at its edge.
 * The sanctuary interior, the inner-court platform, the authored gate corridors and the
 * Kotel wall slab are all expressed this way (SourceAssets/runtime-review/crowd-field/zones.json). */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashCrowdKeepOut
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd") FString Name;
    /** Closed simple polygon in world XY centimetres; the first point is not repeated. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd") TArray<FVector2D> PolygonCm;
};

/** One authored crowd zone: where the figures are, how densely, which way they walk and how
 * many of them just stand. Filled from zones.json by Scripts/release_crowd_field.py. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashCrowdZone
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone") FString Name;

    /** Closed simple polygon in world XY centimetres. Concave outlines are supported: the
     * containment test is a real ray cast, not a bounding box. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone") TArray<FVector2D> PolygonCm;

    /** Relative weight only. The zone's share of CrowdCount is (polygon area / 100 m^2) *
     * DensityPerHundredSqM, renormalised so the shares sum to exactly CrowdCount. Lowering
     * CrowdCount therefore thins every zone in proportion instead of emptying the far ones. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone", meta = (ClampMin = "0.0")) float DensityPerHundredSqM = 20.f;

    /** Share of this zone's figures that stand still (praying at the wall, waiting in the
     * court). They keep a slow idle sway but never translate. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone", meta = (ClampMin = "0.0", ClampMax = "1.0")) float StandingRatio = 0.25f;

    /** Ground fallback, used where the runtime trace misses or is disabled. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone|Ground") EMikdashCrowdGround GroundMode = EMikdashCrowdGround::Flat;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone|Ground") float GroundZBase = 300.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone|Ground") float GroundSlopeX = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone|Ground") float GroundSlopeY = 0.f;

    /** The zone's constant "grain": the heading a figure takes with no goal pull, in degrees
     * (0 faces +X / east). */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone|Flow") float FlowDirectionDegrees = 0.f;
    /** A focus the stream converges on: a gate mouth, the wall face, the end of a street. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone|Flow") FVector2D GoalCm = FVector2D::ZeroVector;
    /** 0 is a pure directional stream, 1 a pure convergence on GoalCm. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone|Flow", meta = (ClampMin = "0.0", ClampMax = "1.0")) float GoalWeight = 0.3f;
    /** A steady lateral bias added to the blended heading; turns a stream into a circulation. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone|Flow") float SwirlDegrees = 0.f;
    /** Per-instance heading jitter, so neighbours drift apart instead of marching in lockstep. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone|Flow", meta = (ClampMin = "0.0")) float MeanderDegrees = 12.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone|Flow", meta = (ClampMin = "0.0")) float MeanderHz = 0.11f;

    /** Where a figure that walks out of the zone comes back in. It is a segment, not a point,
     * and each instance takes a fixed deterministic place along it, so the zone does not
     * fountain everybody out of one spot. A segment that is outside the zone or inside a
     * keep-out is refused at run time and the figure simply turns round instead. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone") FVector2D ReseedEdgeA = FVector2D::ZeroVector;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone") FVector2D ReseedEdgeB = FVector2D::ZeroVector;

    /** How far inside the outline a figure must be seeded, so none is authored straddling an edge. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zone", meta = (ClampMin = "0.0")) float EdgeMarginCm = 100.f;
};

/** Runtime state of one background figure. Deliberately not a UPROPERTY and not a UObject:
 * this is a few dozen bytes each, ten thousand of them is well under a megabyte, and none of
 * it needs to be saved, replicated or reflected. */
struct FMikdashCrowdAgent
{
    FVector2D Position = FVector2D::ZeroVector;
    /** Where this figure returns to when it walks out of its zone. Resolved once at build
     * time to a point that is provably inside the zone and clear of every keep-out, so the
     * per-frame step never has to hope that an authored segment was legal. */
    FVector2D ReseedPoint = FVector2D::ZeroVector;
    float HeadingDegrees = 0.f;
    float SpeedCmPerSecond = 0.f;
    float Phase = 0.f;
    float ScaleFactor = 1.f;
    float GroundZCm = 0.f;
    int32 ZoneIndex = 0;
    int32 GroupIndex = INDEX_NONE;
    int32 GroupMember = 0;
    uint8 bStanding : 1;
    uint8 bValid : 1;
    /** Vertex animation only: 1 while the figure plays (or blends into) the idle clip. */
    uint8 bIdleAnim : 1;

    // Vertex-animation state (AMikdashCrowdField::bUseVertexAnimation only). With it on,
    // Position and GroundZCm are the ANCHOR: where the figure stood at AnchorTime. M_CrowdVAT_V1
    // draws it at Anchor + Velocity * (t - AnchorTime) and advances the walk phase at WalkRate
    // from the same anchor with the same clamp; MikdashCrowd::VatCommit is the CPU half of that
    // contract, so ground travel and stride cannot drift apart between visits.
    FVector2D Velocity = FVector2D::ZeroVector;
    float VelocityZ = 0.f;
    double AnchorTime = 0.0;
    float WalkPhaseAtAnchor = 0.f;
    float WalkRate = 0.f;
    float HorizonSeconds = 0.f;
    double SwitchTime = -1000.0;
    float IdleOffset = 0.f;

    FMikdashCrowdAgent() : bStanding(0), bValid(0), bIdleAnim(1) {}
};

/**
 * A scalable background crowd, separate from and coexisting with the 24 skeletal
 * MikdashResidentCharacter actors.
 *
 * WHAT IT IS. One actor owning up to MaxPoseComponents HierarchicalInstancedStaticMesh
 * components, one per posed figure mesh. It seeds CrowdCount instances (10,000 by default)
 * across the authored zones in zones.json, then walks them along each zone's flow field on a
 * fixed per-frame budget, so the CPU cost is bounded by UpdateBudgetPerFrame and does NOT
 * grow with CrowdCount. Figures never enter the sanctuary, the inner-court platform, the
 * authored gate corridors or the Kotel wall slab.
 *
 * WHAT IT IS NOT. These are instanced background figures. They have no collision, no
 * navigation, no dialog and no articulated
 * limbs: each instance holds one frozen stride pose and the motion you see is its translation
 * across the ground plus a gait bob and lean written into its transform -- UNLESS
 * bUseVertexAnimation is on, in which case every figure is a VAT-baked PilgrimRigV3 body whose
 * material plays the WalkV2 walk (paced from its own ground speed, so it cannot slide) or the
 * idle, each figure on its own phase. Anyone who needs to
 * be talked to, walked around or looked in the eye is a MikdashResidentCharacter, and there
 * are still only 24 of those.
 * Group mode adds deterministic social steering, spatial separation and static-world
 * capsule queries; it is not navmesh pathfinding or collision with the visitor/player.
 *
 * COST. See the class defaults below and Scripts/release_crowd_field.py. On the target
 * hardware (RTX 2070, 16 GB) the intended budget is one HISM draw per pose per LOD with
 * 1,228-triangle LOD0 figures culled at CullDistanceCm, and 500 instance updates a frame,
 * which is one full sweep of a 10,000 crowd every 20 frames. Pass -CrowdCount=2500 on the
 * command line to thin every zone in proportion if that is still too heavy.
 */
UCLASS(BlueprintType, meta = (DisplayName = "Mikdash Crowd Field"))
class MIKDASHRUNTIME_API AMikdashCrowdField : public AActor
{
    GENERATED_BODY()

public:
    AMikdashCrowdField();

    /** One HISM per pose mesh. Fixed at construction so the components serialise cleanly;
     * unused ones simply hold no mesh and no instances. */
    static constexpr int32 MaxPoseComponents = 6;

    // ---------------------------------------------------------------- population

    /** Instances to spawn across all zones. The command line switch -CrowdCount=<n> overrides
     * this at BeginPlay, which is the lever to pull if 10,000 is too heavy on this GPU. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Population", meta = (ClampMin = "0", ClampMax = "60000"))
    int32 CrowdCount = 10000;

    /** Everything random about the crowd -- placement, speed, who stands, garment, height,
     * meander -- is a pure hash of (RandomSeed, instance index), so the same seed gives the
     * same crowd in the editor, in PIE and in a packaged build. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Population")
    int32 RandomSeed = 20260907;

    /** The posed figure meshes, in stride order. Up to MaxPoseComponents are used. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Population")
    TArray<TObjectPtr<UStaticMesh>> PoseMeshes;

    /** Optional override applied to every material slot of every pose mesh. Left unset, each
     * mesh keeps the materials it was imported with. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Population")
    TObjectPtr<UMaterialInterface> CrowdMaterialOverride;

    /** Adult height variation only. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Population", meta = (ClampMin = "0.5", ClampMax = "1.5"))
    float FigureScaleMin = 0.92f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Population", meta = (ClampMin = "0.5", ClampMax = "1.5"))
    float FigureScaleMax = 1.08f;

    /** How many garment tints the material palette carries; the tint index goes out as
     * per-instance custom data 1, normalised to 0..1. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Population", meta = (ClampMin = "1", ClampMax = "32"))
    int32 GarmentPaletteSize = 5;

    // ---------------------------------------------------------------- zones

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zones")
    TArray<FMikdashCrowdZone> Zones;

    /** Polygons no figure may stand in or within ProtectedMarginCm of. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zones")
    TArray<FMikdashCrowdKeepOut> ProtectedPolygons;

    /** Immutable authored property revision, separate from the current world's units. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Crowd|Zones")
    FName SourceCoordinateRevision = TEXT("Legacy50.v1");

    UFUNCTION(BlueprintPure, Category="Crowd") FString GetCoordinateStatus() const { return CoordinateStatus; }
    UFUNCTION(BlueprintPure, Category="Crowd") bool GetRuntimeZone(const FString& Name, FMikdashCrowdZone& Zone) const;
    UFUNCTION(BlueprintPure, Category="Crowd") bool GetRuntimeKeepOut(const FString& Name, FMikdashCrowdKeepOut& KeepOut) const;

    /** Keep-out skirt around every protected polygon, centimetres. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Zones", meta = (ClampMin = "0.0"))
    float ProtectedMarginCm = 150.f;

    // ---------------------------------------------------------------- motion

    /** Instances advanced per frame, round robin. This, not CrowdCount, is what the tick
     * costs. 500 of a 10,000 crowd is one full sweep every 20 frames; each visited instance
     * integrates the whole sweep it slept through, so the crowd still walks at its stated
     * speed. Raising it makes motion smoother and the frame more expensive. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Motion", meta = (ClampMin = "1", ClampMax = "20000"))
    int32 UpdateBudgetPerFrame = 500;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Motion", meta = (ClampMin = "0.0"))
    float MinWalkSpeedCmPerSecond = 60.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Motion", meta = (ClampMin = "0.0"))
    float MaxWalkSpeedCmPerSecond = 110.f;

    /** Authored social motion for background visitors; not family/ritual identities.
     * Turning this off preserves the historical independent-flow preview. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Crowd|Groups")
    bool bEnableVisitorGroups = true;
    /** Target share of people walking/standing independently, not share of groups. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Crowd|Groups", meta=(ClampMin="0.0",ClampMax="1.0"))
    float IndividualVisitorRatio = 0.15f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Crowd|Groups", meta=(ClampMin="110.0",ClampMax="180.0"))
    float GroupSpacingCm = 120.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Crowd|Groups", meta=(ClampMin="25.0"))
    float GroupSlowLagCm = 100.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Crowd|Groups", meta=(ClampMin="50.0"))
    float GroupWaitLagCm = 250.f;
    /** One physical capsule sweep per proposed budgeted move; never all agents per frame.
     * Disabling is a diagnostic mode and cannot establish obstacle acceptance. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Crowd|Groups")
    bool bSweepGroupObstacles = true;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Motion", meta = (ClampMin = "0.0"))
    float MaxTurnDegreesPerSecond = 90.f;

    // ---------------------------------------------------------------- vertex animation

    /** Opt-in (project convention: placing or rebuilding changes nothing until a release script
     * turns it on). Off: the historical frozen posed meshes with a CPU bob. On: PoseMeshes are
     * VAT-baked bodies (Scripts/create_crowd_vat_v2.py) whose M_CrowdVAT_V1 material plays the
     * WalkV2 walk and the idle from per-instance custom data this actor writes (11 floats, layout
     * in Scripts/create_crowd_vat_v2.spec.json); bodies are interleaved over the components so a
     * party is not six copies of one person; BobAmplitudeCm/LeanAmplitudeDegrees are ignored (the
     * clip carries its own pelvis bob); and group steering runs even with bEnableVisitorGroups off,
     * because its look-ahead segment check is what keeps an extrapolated figure out of walls. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|VertexAnimation")
    bool bUseVertexAnimation = false;

    /** Ground speed of the baked walk at play rate 1 and body scale 1. 119.95 cm/s is the WalkV2
     * clip, measured in engine (MeasuredWalkClipGroundSpeedCm in MikdashResidentCharacter.h). Pace
     * AND stride rate are both derived from it: that is the whole no-slide guarantee. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|VertexAnimation", meta = (ClampMin = "10.0"))
    float VatWalkGroundSpeedCmPerSecond = 119.95f;

    /** Seconds per baked walk cycle (two steps). WalkV2: 1.2 s, 100 steps/min. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|VertexAnimation", meta = (ClampMin = "0.1"))
    float VatWalkCycleSeconds = 1.2f;

    /** Per-figure cadence half-width: natural pace = ground speed x scale x (1 +/- this). The
     * residents use 0.07 and it is what keeps two neighbours from stepping together. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|VertexAnimation", meta = (ClampMin = "0.0", ClampMax = "0.3"))
    float VatCadenceSpread = 0.07f;

    /** Play-rate band the walk may be driven at; slower than 0.6 x the minimum is a stop (idle). */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|VertexAnimation", meta = (ClampMin = "0.1"))
    float VatMinPlayRate = 0.45f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|VertexAnimation", meta = (ClampMin = "0.1"))
    float VatMaxPlayRate = 1.55f;

    /** How far ahead in time one visit plans (and the material may extrapolate): 1.5 sweeps,
     * clamped to this band. The planned segment is validated before the figure walks it. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|VertexAnimation", meta = (ClampMin = "0.02"))
    float VatMinHorizonSeconds = 0.12f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|VertexAnimation", meta = (ClampMin = "0.05"))
    float VatMaxHorizonSeconds = 0.7f;

    /** A figure that stopped stays idle at least this long before it walks again (no flicker). */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|VertexAnimation", meta = (ClampMin = "0.0"))
    float VatMinIdleSeconds = 1.0f;

    /** Yaw added to every instance. PilgrimRigV3 bodies face +Y after the glTF import, the crowd
     * heading convention is +X: -90. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|VertexAnimation")
    float MeshYawOffsetDegrees = 0.f;

    /** Seconds after which a paused visitor group turns back toward its anchor instead of
     * standing forever (a permanently paused party was one source of the statue clusters).
     * 0 keeps the historical behaviour. Vertex-animation runtime only. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|VertexAnimation", meta = (ClampMin = "0.0"))
    float PausedGroupResumeSeconds = 0.f;

    static constexpr int32 VatCustomDataFloats = 11;

    /** Figures currently walking (not idle). O(N); for receipts and probes. */
    UFUNCTION(BlueprintPure, Category = "Crowd|VertexAnimation")
    int32 GetVatWalkingCount() const;

    UFUNCTION(BlueprintPure, Category = "Crowd|VertexAnimation")
    int32 GetVatResumedGroupCount() const { return ResumedVisitorGroups; }

    /** One figure's anchor, velocity and stride rate. A probe can check the no-slide identity
     * |Velocity| == WalkCyclesPerSecond x VatWalkGroundSpeedCmPerSecond x Scale x VatWalkCycleSeconds. */
    UFUNCTION(BlueprintPure, Category = "Crowd|VertexAnimation")
    bool GetVatAgentState(int32 AgentIndex, FVector& AnchorLocation, FVector& Velocity, float& WalkCyclesPerSecond,
                          float& Scale, bool& bIdle) const;

    /** Distance covered by one full gait cycle; drives the bob and the material phase rate. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Motion", meta = (ClampMin = "10.0"))
    float StrideLengthCm = 78.f;

    /** Written straight into the instance transform, so the crowd bobs and sways even with a
     * plain default material. Set both to zero for a rigidly gliding crowd. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Motion", meta = (ClampMin = "0.0", ClampMax = "20.0"))
    float BobAmplitudeCm = 3.5f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Motion", meta = (ClampMin = "0.0", ClampMax = "30.0"))
    float LeanAmplitudeDegrees = 4.f;

    // ---------------------------------------------------------------- level of detail

    /** Beyond this distance from the view an instance stops being simulated: its transform is
     * left exactly as it was. It is still drawn (at whatever HISM LOD its screen size picks)
     * until CullDistanceCm. Costs nothing to raise except CPU. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|LOD", meta = (ClampMin = "0.0"))
    float FreezeDistanceCm = 12000.f;

    /** Beyond this distance an instance is skipped entirely by the simulation. It must be at
     * least InstanceEndCullDistanceCm, or figures would still be drawn while frozen forever. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|LOD", meta = (ClampMin = "0.0"))
    float CullDistanceCm = 30000.f;

    /** Pushed to every HISM as InstanceStartCullDistance / InstanceEndCullDistance: the
     * renderer fades instances out between the two and draws nothing past the end. The
     * defaults are tuned for an RTX 2070 at 1080p; drop them first if the GPU is the problem. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|LOD", meta = (ClampMin = "0"))
    int32 InstanceStartCullDistanceCm = 22000;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|LOD", meta = (ClampMin = "0"))
    int32 InstanceEndCullDistanceCm = 30000;

    /** Off by default: ten thousand shadow casters is the single most expensive thing this
     * actor could do, and background figures read fine without their own shadows. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|LOD")
    bool bCastShadows = false;

    /** How many instances the editor preview builds, so the map can be opened and looked at
     * without serialising ten thousand transforms into the .umap. The full CrowdCount is
     * built at BeginPlay. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|LOD", meta = (ClampMin = "0", ClampMax = "20000"))
    int32 EditorPreviewCount = 600;

    // ---------------------------------------------------------------- ground

    /** Trace down at each figure's XY when it is seeded or re-seeded, and stand it on whatever
     * the trace hits. Where the trace misses (and in commandlet runs, where downward traces
     * have historically returned no hit in this project) the zone's flat/plane fallback is
     * used instead and the miss is counted in GetGroundTraceMissCount. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Ground")
    bool bTraceGroundOnSeed = true;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Ground", meta = (ClampMin = "0.0"))
    float GroundTraceStartOffsetCm = 400.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Ground", meta = (ClampMin = "0.0"))
    float GroundTraceDepthCm = 1200.f;

    /** How far the trace may move a figure from the zone's authored ground before the trace is
     * treated as a bad hit (a roof, a passing actor) and the fallback is used instead. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Ground", meta = (ClampMin = "0.0"))
    float GroundTraceMaxDeviationCm = 900.f;

    // ---------------------------------------------------------------- startup

    /** Project convention: startup opt-in defaults to false, so merely placing this actor
     * changes nothing at run time until a release script or a reviewer turns it on. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Crowd|Startup")
    bool bActivateOnBeginPlay = false;

    // ---------------------------------------------------------------- api

    /** Build (or rebuild) the crowd with the given count. Passing a negative count uses
     * CrowdCount, corrected by any -CrowdCount= switch on the command line. Safe to call in
     * the editor: BuildEditorPreview and release_crowd_field.py both go through it. It takes a
     * parameter, so it is BlueprintCallable rather than a CallInEditor button. */
    UFUNCTION(BlueprintCallable, Category = "Crowd")
    void BuildCrowd(int32 OverrideCount = -1);

    /** Build only EditorPreviewCount instances. The editor button. */
    UFUNCTION(BlueprintCallable, CallInEditor, Category = "Crowd")
    void BuildEditorPreview();

    UFUNCTION(BlueprintCallable, CallInEditor, Category = "Crowd")
    void ClearCrowd();

    /** Total instances across every pose component. */
    UFUNCTION(BlueprintPure, Category = "Crowd")
    int32 GetTotalInstanceCount() const;

    /** Instances that were actually seeded (a zone with no usable ground can place fewer than
     * it was apportioned; the difference is a refusal, not a silent success). */
    UFUNCTION(BlueprintPure, Category = "Crowd")
    int32 GetSeededAgentCount() const { return SeededAgents; }

    UFUNCTION(BlueprintPure, Category = "Crowd")
    int32 GetRefusedSeedCount() const { return RefusedSeeds; }

    UFUNCTION(BlueprintPure, Category = "Crowd")
    int32 GetGroundTraceMissCount() const { return GroundTraceMisses; }

    UFUNCTION(BlueprintPure, Category = "Crowd")
    int32 GetReseedFallbackCount() const { return ReseedFallbacks; }

    /** Agents the last sweep left alone because they were past FreezeDistanceCm, and of those,
     * how many were also past CullDistanceCm (and so are not being drawn either). These make
     * the LOD policy inspectable instead of a claim. */
    UFUNCTION(BlueprintPure, Category = "Crowd")
    int32 GetFrozenLastSweepCount() const { return FrozenLastSweep; }

    UFUNCTION(BlueprintPure, Category = "Crowd")
    int32 GetCulledLastSweepCount() const { return CulledLastSweep; }

    /** Per-zone instance counts, in Zones order. Empty until BuildCrowd has run. */
    UFUNCTION(BlueprintPure, Category = "Crowd")
    TArray<int32> GetZoneInstanceCounts() const { return ZoneCounts; }

    /** Frames one full sweep of the crowd takes at the current budget. */
    UFUNCTION(BlueprintPure, Category = "Crowd")
    int32 GetFramesPerSweep() const;

    UFUNCTION(BlueprintPure, Category="Crowd|Groups") int32 GetVisitorGroupCount() const { return VisitorGroups.Num(); }
    UFUNCTION(BlueprintPure, Category="Crowd|Groups") int32 GetGroupedVisitorCount() const { return GroupedVisitors; }
    UFUNCTION(BlueprintPure, Category="Crowd|Groups") int32 GetIndividualVisitorCount() const { return IndividualVisitors; }
    UFUNCTION(BlueprintPure, Category="Crowd|Groups") int32 GetGroupSweepsLastFrame() const { return GroupSweepsLastFrame; }
    UFUNCTION(BlueprintPure, Category="Crowd|Groups") int32 GetGroupRejectedMovesLastFrame() const { return GroupRejectedMovesLastFrame; }
    UFUNCTION(BlueprintPure, Category="Crowd|Groups") int32 GetGroupWaitVisitsLastFrame() const { return GroupWaitVisitsLastFrame; }
    UFUNCTION(BlueprintPure, Category="Crowd|Groups") int32 GetRefusedGroupCount() const { return RefusedGroups; }
    UFUNCTION(BlueprintPure, Category="Crowd|Groups") int32 GetPausedVisitorGroupCount() const { return PausedVisitorGroups; }
    UFUNCTION(BlueprintPure, Category="Crowd|Groups") FString GetVisitorGroupState(int32 GroupIdentity) const;
    UFUNCTION(BlueprintPure, Category="Crowd|Groups")
    bool GetVisitorSocialState(int32 AgentIndex,int32& GroupIdentity,int32& MemberIndex,FVector& Location,bool& Standing) const;

    /** A one-line summary a receipt or a log can quote. */
    UFUNCTION(BlueprintPure, Category = "Crowd")
    FString GetCrowdSummary() const;

    /** The count this actor would build, after applying any -CrowdCount= command-line switch. */
    UFUNCTION(BlueprintPure, Category = "Crowd")
    int32 GetEffectiveCrowdCount() const;

    /** Read -CrowdCount=<n> from the command line; returns Fallback when it is absent or
     * unparseable. Public and static so a test or a release script can reason about it. */
    static int32 ParseCrowdCountSwitch(int32 Fallback);

    // Conservative zone/keep-out review only; coordinator supplies real floor/capsule queries.
    bool IsTransitSegmentAllowed(const FVector& From, const FVector& To, float RadiusCm = 34.f) const;

    virtual void Tick(float DeltaSeconds) override;

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
    // Native property arrays remain untouched; every build decodes fresh into these.
    TArray<FMikdashCrowdZone> RuntimeZones;
    TArray<FMikdashCrowdKeepOut> RuntimeProtectedPolygons;
    FString CoordinateStatus = TEXT("Not resolved");
    bool PrepareRuntimeGeometry();
    UPROPERTY(VisibleAnywhere, Category = "Crowd")
    TArray<TObjectPtr<UHierarchicalInstancedStaticMeshComponent>> PoseComponents;

    /** Live agent state, index-aligned with the global instance index. */
    TArray<FMikdashCrowdAgent> Agents;
    struct FVisitorGroup
    {
        MikdashCrowdGroups::Cohort Cohort;
        int32 ZoneIndex=0;
        FVector2D SeedAnchor=FVector2D::ZeroVector;
        MikdashCrowdGroups::Travel Travel;
        double PausedSince=-1.0;
    };
    TArray<FVisitorGroup> VisitorGroups;
    MikdashCrowdGroups::SpatialIndex VisitorSpacing;
    int32 GroupedVisitors=0,IndividualVisitors=0,RefusedGroups=0,PausedVisitorGroups=0;
    int32 GroupSweepsLastFrame=0,GroupRejectedMovesLastFrame=0,GroupWaitVisitsLastFrame=0;
    int32 ResumedVisitorGroups=0;
    bool bSocialRuntime=false;
    void SeedSocialZone(int32 ZoneIndex,int32 ZoneTotal,int32& GlobalIndex);
    void StepSocialAgent(int32 Index,double Dt,const MikdashCrowd::FlowZone& Flow);
    /** Vertex-animation visit: commit the anchor along the segment validated last time, then plan
     * and validate the next Horizon seconds of travel. A figure that cannot walk idles. */
    void StepSocialAgentVat(int32 Index, double Now, float Horizon, const MikdashCrowd::FlowZone& Flow);
    void CommitVat(FMikdashCrowdAgent& Agent, double Now) const;
    void SetVatIdle(FMikdashCrowdAgent& Agent, double Now) const;
    /** False when the figure is still inside its minimum idle hold (it then stays idle). */
    bool SetVatWalk(FMikdashCrowdAgent& Agent, double Now, const FVector2D& Velocity2D, float VelocityZ, float Horizon, double Speed) const;
    void AppendVatCustomData(int32 Index, TArray<float>& Out) const;
    void PushVat(int32 GlobalStart, int32 GlobalCount);
    double VatNow() const;
    TArray<float> CustomScratch;
    bool SocialSegmentAllowed(int32 ZoneIndex,const MikdashCrowd::Vec2& From,const MikdashCrowd::Vec2& To) const;

    /** Reusable scratch for one batched transform run; never freed between frames. */
    TArray<FTransform> TransformScratch;

    // Zones and keep-outs are flattened once by BuildCrowd into the (points, starts, counts)
    // layout CrowdFieldMath.h takes, so the tick never allocates and never walks a TArray of
    // TArrays per instance.
    TArray<MikdashCrowd::Vec2> KeepOutPointCache;
    TArray<int32> KeepOutStartCache;
    TArray<int32> KeepOutCountCache;
    TArray<MikdashCrowd::Vec2> ZonePointCache;
    TArray<int32> ZoneStartCache;
    TArray<int32> ZoneVertexCountCache;
    TArray<MikdashCrowd::FlowZone> ZoneFlowCache;

    UPROPERTY(Transient) TArray<int32> ZoneCounts;
    UPROPERTY(Transient) int32 SeededAgents = 0;
    UPROPERTY(Transient) int32 RefusedSeeds = 0;
    UPROPERTY(Transient) int32 GroundTraceMisses = 0;
    /** Instances whose zone re-seed segment was unusable and which fall back to returning to
     * their own start point. A large number means a zone's re-seed edge wants re-authoring. */
    UPROPERTY(Transient) int32 ReseedFallbacks = 0;
    UPROPERTY(Transient) int32 ActivePoseCount = 0;
    UPROPERTY(Transient) int32 FrozenLastSweep = 0;
    UPROPERTY(Transient) int32 CulledLastSweep = 0;
    UPROPERTY(Transient) int32 FrozenThisSweep = 0;
    UPROPERTY(Transient) int32 CulledThisSweep = 0;
    UPROPERTY(Transient) int32 UpdateCursor = 0;
    UPROPERTY(Transient) float ElapsedSeconds = 0.f;
    UPROPERTY(Transient) bool bCrowdRunning = false;

    void ConfigureComponents();
    /** Flatten Zones and ProtectedPolygons into the cache arrays above. */
    void CacheGeometry();
    /** Ground height fallback for a zone at a world XY. */
    float ZoneGroundZ(const FMikdashCrowdZone& Zone, const FVector2D& P) const;
    /** Ground height for a figure: the trace where it hits and is plausible, the zone otherwise. */
    float ResolveGroundZ(const FMikdashCrowdZone& Zone, const FVector2D& P);
    /** A legal re-seed point for this instance: walks the zone's re-seed segment from the
     * instance's own deterministic place along it and takes the first sample that is inside
     * the zone and outside every keep-out. Falls back to Fallback (the figure's own seed
     * point, which is legal by construction) when the whole segment is unusable. */
    FVector2D ResolveReseedPoint(const FMikdashCrowdZone& Zone, const MikdashCrowd::Vec2* ZonePolygon, int32 ZoneVertices,
                                 int32 GlobalIndex, const FVector2D& Fallback);
    /** Where the crowd is being looked at from: the local player's view, else this actor. */
    FVector ResolveViewLocation() const;
    FTransform TransformFor(const FMikdashCrowdAgent& Agent) const;
    void PushTransforms(int32 GlobalStart, int32 GlobalCount);
};
