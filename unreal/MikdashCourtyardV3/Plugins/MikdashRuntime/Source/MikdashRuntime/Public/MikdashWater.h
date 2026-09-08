#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "WaterFlowMath.h"
#include "MikdashWater.generated.h"

class UMaterialInstanceDynamic;
class UStaticMeshComponent;
class IConsoleObject;

// AMikdashWater: the actor that makes the stream of Yechezkel 47 move.
//
// WHAT IT DOES AND DOES NOT DO
// ----------------------------
// It owns no geometry. The channel, its water ribbons and the mikvaot are static meshes
// built offline by Scripts/create_water_geometry.py and placed by Scripts/release_water.py;
// this actor finds those meshes by tag, makes a dynamic material instance for each, and
// pushes numbers into them on an interval. Every number it pushes comes out of
// WaterFlowMath.h, which is engine-independent and covered by
// Plugins/MikdashRuntime/Tests/WaterFlowMathTest.cpp. There is no simulation here, and no
// arithmetic the tests do not already exercise: if a flow speed is wrong it is wrong in the
// header, where it can be proven wrong without launching the editor.
//
// It also asserts nothing about the water. What is textual, what is disputed and what this
// project invented is recorded in SourceAssets/water-review/sources.md. The depths are
// anthropometric fractions of an assumed stature; the widths have no source at all; the
// four stages are built as literal distances, which is one reading of 47:3-5 and not the
// only one.

/** Mirrors MikdashWater::Stage for Blueprint and the details panel. */
UENUM(BlueprintType)
enum class EMikdashWaterStage : uint8
{
    /** At the gate, before the first thousand: mefakim, trickling (47:2). */
    Trickle = 0     UMETA(DisplayName = "Trickle at the gate (47:2)"),
    /** Afsayim, at 1000 amot (47:3). */
    Ankles  = 1     UMETA(DisplayName = "To the ankles (47:3)"),
    /** Birkayim, at 2000 amot (47:4). */
    Knees   = 2     UMETA(DisplayName = "To the knees (47:4)"),
    /** Motnayim, at 3000 amot (47:4). */
    Loins   = 3     UMETA(DisplayName = "To the loins (47:4)"),
    /** A river that could not be passed over, at 4000 amot (47:5). */
    River   = 4     UMETA(DisplayName = "A river that could not be passed over (47:5)"),
};

/** Scalar parameter names the water material must expose.
 *
 *  These literals are the contract between this actor and the material built by
 *  Scripts/release_water.py. That script's offline check greps THIS FILE for every name in
 *  its spec and refuses to run if one is missing, because a mismatch is otherwise
 *  completely invisible: SetScalarParameterValue against a name the material does not have
 *  is not an error, it silently does nothing, and the water simply sits still. */
namespace MikdashWaterParameters
{
/** cm/s, the Manning normal velocity of the reach being sampled. */
inline constexpr const TCHAR* FlowSpeed    = TEXT("WaterFlowSpeed");
/** 0..1, the Panner offset in tiles, pre-wrapped so a long session cannot judder. */
inline constexpr const TCHAR* ScrollTiles  = TEXT("WaterScrollTiles");
/** cm, the design depth at the sampled distance. Drives the depth colour and refraction. */
inline constexpr const TCHAR* Depth        = TEXT("WaterDepth");
/** 0..1, the depth-derived opacity ramp. */
inline constexpr const TCHAR* Opacity      = TEXT("WaterOpacity");
/** 0..1, foam from the Froude number: white where the flow goes supercritical. */
inline constexpr const TCHAR* Foam         = TEXT("WaterFoam");
/** The Froude number itself, for anything that wants the raw regime. */
inline constexpr const TCHAR* Froude       = TEXT("WaterFroude");
/** cm, the free surface rise above its built level. Non-zero only during a demonstration. */
inline constexpr const TCHAR* SurfaceRise  = TEXT("WaterSurfaceRise");
/** cm, the current ripple displacement at the ripple centre, decaying with age. */
inline constexpr const TCHAR* Ripple       = TEXT("WaterRipple");
/** 0..4 as a float: the stage last passed. */
inline constexpr const TCHAR* StageIndex   = TEXT("WaterStage");
/** 0..1 across the whole four thousand amot; 0 when no demonstration is running. */
inline constexpr const TCHAR* DemoProgress = TEXT("WaterDemoProgress");
}

/** Drives the water materials of the Yechezkel 47 stream and of the mikvaot.
 *
 *  One per map, written into the level by Scripts/release_water.py, which also sets
 *  StreamMeshTag to the tag it puts on every water ribbon it places. */
UCLASS(BlueprintType)
class MIKDASHRUNTIME_API AMikdashWater : public AActor
{
    GENERATED_BODY()

public:
    AMikdashWater();

    // -- what to drive ------------------------------------------------------------

    /** Component tag carried by every water-surface mesh component this actor drives.
     *  Set by the release script; every static mesh component in the level carrying this
     *  tag gets a dynamic material instance. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash Water|Binding")
    FName StreamMeshTag = TEXT("MikdashWaterSurface");

    /** Explicit components, used INSTEAD of the tag sweep when non-empty. Lets a reviewer
     *  point the actor at a single ribbon without retagging the level. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash Water|Binding")
    TArray<TObjectPtr<UStaticMeshComponent>> ExplicitSurfaces;

    /** Seconds between pushes. The material is a scroll and a colour ramp, not a
     *  simulation, so it does not need a per-frame update; at 1/30 s a whole court of
     *  ribbons costs a handful of SetScalarParameterValue calls. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash Water|Binding",
              meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float UpdateIntervalSeconds = 0.0333f;

    // -- the reach this actor samples ---------------------------------------------

    /** Distance east of the outer east gate, in amot, at which the profile is sampled for
     *  the steady (non-demonstration) look. 0 is the trickle at the threshold. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash Water|Reach",
              meta = (ClampMin = "0.0", ClampMax = "4000.0"))
    float SampleDistanceAmot = 0.0f;

    /** Bed slope of the reach, as a fall per unit run. AUTHORED. The court runnel is cut
     *  far steeper than the far field, and the Froude number -- and therefore the foam --
     *  is very sensitive to it: 1 per cent runs subcritical and glassy, 6 per cent runs
     *  supercritical and white. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash Water|Reach",
              meta = (ClampMin = "0.0001", ClampMax = "0.5"))
    float BedSlope = 0.01f;

    /** Manning roughness. MikdashWater::Roughness carries the three this project uses:
     *  0.015 dressed stone, 0.025 rubble, 0.030 natural earth. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash Water|Reach",
              meta = (ClampMin = "0.005", ClampMax = "0.1"))
    float ManningN = 0.015f;

    /** Horizontal per vertical on the bank faces. Must match the geometry script's
     *  BANK_SIDE_SLOPE, or the section this actor solves is not the section on screen. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash Water|Reach",
              meta = (ClampMin = "0.0", ClampMax = "5.0"))
    float BankSideSlope = 1.2f;

    /** World size, cm, of one tile of the normal map. Sets how fast the scroll reads. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash Water|Reach",
              meta = (ClampMin = "1.0"))
    float NormalTileSizeCm = 200.0f;

    // -- demonstration -------------------------------------------------------------

    /** Seconds to travel from one thousand-amah mark to the next. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash Water|Demonstration",
              meta = (ClampMin = "0.0"))
    float DemoTravelSeconds = 6.0f;

    /** Seconds held at each mark while the depth is read against the gauge post. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash Water|Demonstration",
              meta = (ClampMin = "0.0"))
    float DemoHoldSeconds = 3.0f;

    /** Loop back to the trickle after the fourth measurement instead of stopping. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash Water|Demonstration")
    bool bDemoLoops = false;

    /** How far the free surface may rise, cm, at full demonstration swell. AUTHORED, and
     *  deliberately small: the built channel is a fixed solid, so a rise larger than the
     *  kerb would put the surface through the bank instead of over it. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash Water|Demonstration",
              meta = (ClampMin = "0.0", ClampMax = "50.0"))
    float DemoMaxSurfaceRiseCm = 8.0f;

    /** Start the demonstration: the stream swells through the four stages in order,
     *  pausing at each measuring mark. Also bound to the console command
     *  "Mikdash.Water.Demo". */
    UFUNCTION(BlueprintCallable, Category = "Mikdash Water|Demonstration")
    void StartDemonstration(bool bLoop = false);

    /** Stop it and return to the steady sample at SampleDistanceAmot. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash Water|Demonstration")
    void StopDemonstration();

    UFUNCTION(BlueprintPure, Category = "Mikdash Water|Demonstration")
    bool IsDemonstrationRunning() const { return bDemonstrating; }

    /** 0..1 across the whole four thousand amot; 0 when no demonstration is running. */
    UFUNCTION(BlueprintPure, Category = "Mikdash Water|Demonstration")
    float GetDemonstrationProgress() const { return DemoProgress; }

    // -- ripples -------------------------------------------------------------------

    /** Disturb the surface at a world point -- a foot entering the water, a vessel being
     *  filled. One ripple at a time; a second call restarts it. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash Water|Ripple")
    void AddRipple(FVector WorldLocation, float AmplitudeCm = 4.0f);

    /** Ripple displacement, cm, at a world point right now. Zero ahead of the advancing
     *  crest and once it has passed. */
    UFUNCTION(BlueprintPure, Category = "Mikdash Water|Ripple")
    float GetRippleElevationCm(FVector WorldLocation) const;

    // -- readouts (what a reviewer reads in the details panel) ----------------------

    /** Depth, cm, at the distance currently being driven. */
    UFUNCTION(BlueprintPure, Category = "Mikdash Water|Readout")
    float GetCurrentDepthCm() const { return LastDepthCm; }

    /** Manning normal velocity, cm/s, at the distance currently being driven. */
    UFUNCTION(BlueprintPure, Category = "Mikdash Water|Readout")
    float GetCurrentFlowSpeedCmS() const { return LastFlowSpeedCmS; }

    /** Discharge, litres per second, at the distance currently being driven. */
    UFUNCTION(BlueprintPure, Category = "Mikdash Water|Readout")
    float GetCurrentDischargeLitresPerSecond() const { return LastDischargeLitresS; }

    UFUNCTION(BlueprintPure, Category = "Mikdash Water|Readout")
    EMikdashWaterStage GetCurrentStage() const { return CurrentStage; }

    /** How many surface components this actor actually found and is driving. Zero means
     *  the tag is wrong or the release script has not run, and the water will look
     *  painted on rather than flowing. */
    UFUNCTION(BlueprintPure, Category = "Mikdash Water|Readout")
    int32 GetDrivenSurfaceCount() const { return DynamicMaterials.Num(); }

    // -- AActor --------------------------------------------------------------------

    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void Tick(float DeltaSeconds) override;

private:
    /** Collect the surface components and make one dynamic material instance per slot. */
    void BindSurfaces();

    /** Sample the profile at a distance and push the result into every bound material. */
    void PushDrive(double DistanceAmot, double SurfaceRiseCm);

    MikdashWater::StreamProfile Profile;

    UPROPERTY(Transient)
    TArray<TObjectPtr<UMaterialInstanceDynamic>> DynamicMaterials;

    /** Seconds since BeginPlay, driving the scroll. Never reset; ScrollTiles wraps it. */
    double ElapsedSeconds = 0.0;
    double SinceLastPush = 0.0;

    bool bDemonstrating = false;
    double DemoElapsed = 0.0;
    float DemoProgress = 0.0f;

    FVector RippleCentre = FVector::ZeroVector;
    /** Negative means no ripple is active. */
    double RippleAgeSeconds = -1.0;
    MikdashWater::Ripple RippleShape;

    float LastDepthCm = 0.0f;
    float LastFlowSpeedCmS = 0.0f;
    float LastDischargeLitresS = 0.0f;
    EMikdashWaterStage CurrentStage = EMikdashWaterStage::Trickle;

    /** Console command handle, registered in BeginPlay and released in EndPlay. */
    IConsoleObject* DemoCommand = nullptr;
};
