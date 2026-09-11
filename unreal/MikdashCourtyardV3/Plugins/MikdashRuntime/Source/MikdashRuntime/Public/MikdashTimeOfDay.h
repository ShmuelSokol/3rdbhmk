#pragma once
#include "CoreMinimal.h"
#include "Engine/Scene.h"
#include "GameFramework/Actor.h"
#include "SunPositionMath.h"
#include "MikdashTimeOfDay.generated.h"

class ADirectionalLight;
class AExponentialHeightFog;
class APostProcessVolume;
class ASkyAtmosphere;
class ASkyLight;
class AVolumetricCloud;
class UMaterialInstanceDynamic;
class UMaterialInterface;

/** The eight named times of day. Mirrors MikdashSun::ETimePreset one-for-one; the
 * reflected copy exists because UENUM cannot wrap a plain enum class from a non-UObject
 * header. TimePresetToNative() is the only place the two are related. */
UENUM(BlueprintType)
enum class EMikdashTimePreset : uint8
{
    Dawn UMETA(DisplayName = "Dawn (civil twilight)"),
    Sunrise UMETA(DisplayName = "Sunrise"),
    Morning UMETA(DisplayName = "Morning"),
    Midday UMETA(DisplayName = "Midday (solar noon)"),
    Afternoon UMETA(DisplayName = "Afternoon"),
    Sunset UMETA(DisplayName = "Sunset"),
    Dusk UMETA(DisplayName = "Dusk (civil twilight)"),
    Night UMETA(DisplayName = "Night")
};

/** One row of the lighting table. A sun rotation on its own is not a time of day: the
 * intensity, the colour temperature, the sky light, the fog and the exposure all have to
 * move together or dawn looks like noon with a low sun.
 *
 * FOG DEFAULTS ARE THE AUTHORED TUNE. Every preset below ships fog density 0.0015,
 * height falloff 0.15, start distance 8000 and volumetric fog OFF, which is the tune
 * recorded in SourceAssets/lighting-review/fog-tune-20260908T024650Z.json. Only Dawn,
 * Sunrise, Sunset, Dusk and Night lift the density, and only slightly; midday is byte-for-
 * byte the authored value. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashSkyPreset
{
    GENERATED_BODY()

    /** Sun illuminance in lux. Real clear-sky sun is 60-100 klux at noon; the scene meters
     * with histogram auto exposure, so what matters is the ratio to the sky light. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sun")
    float SunIntensityLux = 30000.f;

    /** Colour temperature in kelvin against the tonemapper's 6500 K white point. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sun")
    float SunTemperatureK = 5000.f;

    /** Angular diameter of the solar disc in degrees. 0.5 is the real sun; a wider disc
     * softens contact shadows, which reads as haze. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sun")
    float SunSourceAngleDeg = 0.5f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sun")
    float SunVolumetricScatteringIntensity = 1.f;

    /** Moon illuminance in lux at full moon. A real full moon is about 0.25 lux; that is
     * far below anything a tonemapped render can show, so this is a deliberately raised
     * cinematic value, scaled at run time by the illuminated fraction. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Moon")
    float MoonIntensityLux = 0.4f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Moon")
    float MoonTemperatureK = 8000.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Sky")
    float SkyLightIntensity = 1.f;

    /** Authored tune: 0.0015. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fog")
    float FogDensity = 0.0015f;

    /** Authored tune: 0.15. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fog")
    float FogHeightFalloff = 0.15f;

    /** Authored tune: 8000 cm. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fog")
    float FogStartDistance = 8000.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fog")
    float FogMaxOpacity = 1.f;

    /** Multiplier on the SkyAtmosphere colour the height fog inherits. This is the fog
     * COLOUR control; the fog does not get a flat authored colour, so the haze always
     * agrees with the sky behind it. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fog")
    FLinearColor FogColorScale = FLinearColor(1.f, 1.f, 1.f, 1.f);

    /** Physical-scale glow around the sun direction, cd/m2. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fog")
    FLinearColor DirectionalInscatteringLuminance = FLinearColor(0.f, 0.f, 0.f, 1.f);

    /** Authored tune: OFF. Volumetric fog is the expensive path and the reviewed scene
     * does not use it. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Fog")
    bool bVolumetricFog = false;

    /** 0 = clear sky, 1 = overcast. Written to the cloud material's coverage parameter. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Clouds", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float CloudCoverage = 0.35f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Clouds", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float CloudDensity = 0.15f;

    /** Exposure compensation in stops, added to the post-process volume's bias. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exposure")
    float ExposureBiasEV = 0.f;

    /** Auto-exposure bounds in EV100. Converted to the units the project's
     * r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange cvar implies. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exposure")
    float ExposureMinEV100 = 0.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Exposure")
    float ExposureMaxEV100 = 14.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Atmosphere")
    float AerialPerspectiveViewDistanceScale = 1.8f;

    /** Engine property name carries the historical "Pespective" spelling; this one does
     * not. Mie scattering makes the horizon dustier and warmer. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Atmosphere")
    float MieScatteringScale = 0.005f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Atmosphere")
    float SkyLuminanceFactor = 1.f;
};

/** What weather does to the time-of-day result. AMikdashWeather owns the values;
 * AMikdashTimeOfDay is the single place that writes to the scene, so the two can never
 * fight over the same property. Clear weather is exactly the identity. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashSkyModifier
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
    float SunIntensityScale = 1.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
    float SunTemperatureOffsetK = 0.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
    float SunSourceAngleAddDeg = 0.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
    float SkyLightIntensityScale = 1.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
    float FogDensityScale = 1.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
    FLinearColor FogColorTint = FLinearColor(1.f, 1.f, 1.f, 1.f);

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
    float CloudCoverageAdd = 0.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
    float CloudDensityScale = 1.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
    float ExposureBiasAddEV = 0.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
    float AerialPerspectiveScale = 1.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
    float MieScatteringScale = 1.f;
};

/** Everything the actor overwrote, captured once at BeginPlay and restored at EndPlay so
 * a play session never leaves the authored lighting changed. */
USTRUCT()
struct FMikdashSkySnapshot
{
    GENERATED_BODY()

    UPROPERTY() bool bValid = false;

    UPROPERTY() FRotator SunRotation = FRotator::ZeroRotator;
    UPROPERTY() float SunIntensity = 0.f;
    UPROPERTY() bool bSunUseTemperature = false;
    UPROPERTY() float SunTemperature = 0.f;
    UPROPERTY() float SunSourceAngle = 0.f;
    UPROPERTY() float SunVolumetricScattering = 0.f;

    UPROPERTY() float SkyLightIntensity = 0.f;

    UPROPERTY() float FogDensity = 0.f;
    UPROPERTY() float FogHeightFalloff = 0.f;
    UPROPERTY() float FogStartDistance = 0.f;
    UPROPERTY() float FogMaxOpacity = 0.f;
    UPROPERTY() bool bFogVolumetric = false;
    UPROPERTY() FLinearColor FogColorScale = FLinearColor::White;
    UPROPERTY() FLinearColor FogDirectionalInscattering = FLinearColor::Black;

    UPROPERTY() float AerialPerspectiveScale = 0.f;
    UPROPERTY() float MieScatteringScale = 0.f;
    UPROPERTY() FLinearColor SkyLuminanceFactor = FLinearColor::White;

    UPROPERTY() TObjectPtr<UMaterialInterface> CloudMaterial = nullptr;

    UPROPERTY() FPostProcessSettings PostProcess;
    UPROPERTY() bool bPostProcessValid = false;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FMikdashTimeOfDayChanged, float, TimeOfDayHours, float, SunAltitudeDegrees);

/**
 * Drives the whole sky from one normalized time value: directional sun, moon, sky
 * atmosphere, sky light, volumetric clouds, exponential height fog and the post-process
 * exposure. The sun and moon directions come from real astronomy for Jerusalem
 * (SunPositionMath.h, NOAA solar coordinates, sub-minute rise/set accuracy against USNO);
 * the LOOK at each time comes from the eight-row preset table, blended along the day.
 *
 * WHAT THIS ACTOR TOUCHES, at run time only:
 *   ADirectionalLight  rotation, Intensity, bUseTemperature, Temperature, LightSourceAngle,
 *                      VolumetricScatteringIntensity
 *   ASkyLight          Intensity (and RecaptureSky when the sun moves far enough)
 *   ASkyAtmosphere     AerialPespectiveViewDistanceScale, MieScatteringScale,
 *                      SkyLuminanceFactor
 *   AVolumetricCloud   the component's material is swapped for a dynamic instance of the
 *                      same material, then coverage/density/wind parameters are set on it
 *   AExponentialHeightFog  FogDensity, FogHeightFalloff, StartDistance, FogMaxOpacity,
 *                      SkyAtmosphereAmbientContributionColorScale,
 *                      DirectionalInscatteringLuminance, bEnableVolumetricFog
 *   APostProcessVolume AutoExposureBias, AutoExposureMinBrightness, AutoExposureMaxBrightness
 *
 * WHAT IT NEVER TOUCHES: materials on any mesh, normal or roughness of any surface, wall
 * relief, mesh transforms, Lumen quality, film tonemapper curve (slope/toe/shoulder/white
 * clip), bloom, vignette, SkyLight bLowerHemisphereIsBlack, SkyLight source type or
 * cubemap, and every actor that is not one of the six classes above. The 2026-09-07 pass
 * that flattened wall relief changed material and tonemapper settings; nothing here goes
 * near either. The film curve values set by the fill-highlight pass (film_shoulder 0.30,
 * film_white_clip 0.02, auto_exposure_high_percent 95) are read but never written.
 *
 * The authored fog tune (density 0.0015, falloff 0.15, start 8000, volumetric off) is the
 * default in every preset row, and is the EXACT value at Midday, Morning and Afternoon.
 * FogDensity is additionally hard-clamped to MaxFogDensity after weather is applied.
 *
 * Everything overwritten is snapshotted at BeginPlay and restored at EndPlay.
 */
UCLASS(Blueprintable, ClassGroup = "Mikdash", meta = (DisplayName = "Mikdash Time Of Day"))
class MIKDASHRUNTIME_API AMikdashTimeOfDay : public AActor
{
    GENERATED_BODY()

public:
    AMikdashTimeOfDay();

    // -----------------------------------------------------------------------
    // Time
    // -----------------------------------------------------------------------

    /** Wall-clock hour in Jerusalem, 0..24. The single source of truth. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Time",
              meta = (ClampMin = "0.0", ClampMax = "24.0", UIMin = "0.0", UIMax = "24.0"))
    float TimeOfDayHours = 6.0f;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Time", meta = (ClampMin = "1900", ClampMax = "2200"))
    int32 Year = 2026;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Time", meta = (ClampMin = "1", ClampMax = "12"))
    int32 Month = 9;

    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Time", meta = (ClampMin = "1", ClampMax = "31"))
    int32 Day = 8;

    /** Game seconds per real second of clock advance, expressed as a multiple of real
     * time. 1 = real time, 60 = a minute per second, 0 = frozen. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Time", meta = (ClampMin = "0.0"))
    float RateMultiplier = 0.f;

    /** Frozen wins over RateMultiplier. A scene locked for review must stay locked. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Time")
    bool bFrozen = true;

    /** Roll the date forward when the clock passes midnight. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Time")
    bool bAdvanceDateAtMidnight = true;

    /** The preset applied on BeginPlay. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Time")
    EMikdashTimePreset StartPreset = EMikdashTimePreset::Morning;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Time")
    bool bApplyStartPresetOnBeginPlay = true;

    // -----------------------------------------------------------------------
    // Place and clock
    // -----------------------------------------------------------------------

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Location")
    double LatitudeDeg = MikdashSun::JerusalemLatitudeDeg;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Location")
    double LongitudeDeg = MikdashSun::JerusalemLongitudeDeg;

    /** Use the Israeli daylight-saving rule (IDT from the Friday before the last Sunday of
     * March to the last Sunday of October) instead of ManualTimeZoneOffsetHours. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Location")
    bool bUseIsraeliDaylightSaving = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Location", meta = (EditCondition = "!bUseIsraeliDaylightSaving"))
    double ManualTimeZoneOffsetHours = 2.0;

    /** Compass bearing, in the project world frame, that the +X axis points along. The
     * Walkthrough map is +X east, +Y south, +Z up, so this is 90. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Location")
    float WorldXAxisCompassBearingDeg = 90.f;

    // -----------------------------------------------------------------------
    // Scene actors. Left empty they are found by class on BeginPlay.
    // -----------------------------------------------------------------------

    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Mikdash|Scene")
    TObjectPtr<ADirectionalLight> SunLight = nullptr;

    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Mikdash|Scene")
    TObjectPtr<ADirectionalLight> MoonLight = nullptr;

    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Mikdash|Scene")
    TObjectPtr<ASkyLight> SkyLight = nullptr;

    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Mikdash|Scene")
    TObjectPtr<ASkyAtmosphere> SkyAtmosphere = nullptr;

    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Mikdash|Scene")
    TObjectPtr<AVolumetricCloud> VolumetricCloud = nullptr;

    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Mikdash|Scene")
    TObjectPtr<AExponentialHeightFog> HeightFog = nullptr;

    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Mikdash|Scene")
    TObjectPtr<APostProcessVolume> PostProcessVolume = nullptr;

    /** Spawn a second directional light for the moon if MoonLight is empty. The moon light
     * is registered as atmosphere light index 1 so the SkyAtmosphere gives it a disc and a
     * night sky glow. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Scene")
    bool bSpawnMoonLightIfMissing = true;

    // -----------------------------------------------------------------------
    // What to drive. Every channel can be switched off independently, so a regression can
    // be bisected without deleting the actor.
    // -----------------------------------------------------------------------

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Drive") bool bDriveSun = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Drive") bool bDriveMoon = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Drive") bool bDriveSkyLight = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Drive") bool bDriveSkyAtmosphere = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Drive") bool bDriveClouds = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Drive") bool bDriveFog = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Drive") bool bDriveExposure = true;

    /** Hard ceiling on fog density after presets and weather. The authored tune is 0.0015;
     * this stops any preset or weather edit from turning the courts into soup. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Drive", meta = (ClampMin = "0.0"))
    float MaxFogDensity = 0.0060f;

    /** Never write bEnableVolumetricFog = true, whatever a preset says. The reviewed scene
     * runs with volumetric fog off and an RTX 2070 budget. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Drive")
    bool bForbidVolumetricFog = true;

    // -----------------------------------------------------------------------
    // Distant haze (HorizonHazeV1, 11 Sep 2026)
    //
    // The height fog inherits the SkyAtmosphere's CLEAR-SKY ambient colour (times the
    // preset's FogColorScale), and the aerial perspective is clear-sky Rayleigh too. Both are
    // blue even when the preset's own sky is grey overcast, so the far-field terrain ring
    // (Scripts/release_horizon_ring.py) saturated to one flat blue strip that read as sea
    // (frames cp21/cp21b P1 and D1). The haze is tied to the sky state each preset already
    // carries: its CloudCoverage (after weather) pulls the fog colour toward a luminance-
    // preserving warm grey, but only while the sun is high enough for the clear-sky ambient to
    // be blue; the far-field fog cap and the aerial-perspective multiplier keep distant ridges
    // stepping back in value instead of merging. Review overrides: mikdash.Haze.* console
    // variables; mikdash.Haze.Enable 0 restores the pre-HorizonHazeV1 behaviour exactly.
    // -----------------------------------------------------------------------

    /** 0 disables the overcast haze colour; 1 applies the full tint at full cover. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Haze", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float OvercastHazeStrength = 1.0f;

    /** Per-channel multiplier on the fog colour at full weight. Normalised to Rec.709
     * luminance 1 before use, so it changes the haze colour and never its brightness. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Haze")
    FLinearColor OvercastHazeTint = FLinearColor(1.0f, 0.80f, 0.55f, 1.f);

    /** Blended CloudCoverage mapped to 0..1 cover weight (smoothstep X..Y). The cloud
     * material already reads as mostly overcast at 0.25, the Hazy summer default. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Haze")
    FVector2D OvercastCoverageRange = FVector2D(0.05f, 0.30f);

    /** Sun altitude in degrees mapped to 0..1 (smoothstep X..Y). Below X the clear-sky
     * ambient is already warm (dawn, sunset), so the tint fades out instead of doubling it. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Haze")
    FVector2D OvercastSunAltitudeRangeDeg = FVector2D(2.f, 20.f);

    /** Ceiling on the height fog's max opacity. It only binds on pixels already that
     * heavily fogged (tens of km out, low land), so nothing near the camera changes; far
     * ridges keep part of their own value and read as land. Negative = preset value. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Haze")
    float FarHazeMaxOpacity = 0.45f;

    /** Multiplier on the preset's AerialPerspectiveViewDistanceScale (1.7-2.2 in daylight,
     * x1.25 more under Hazy weather). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Haze", meta = (ClampMin = "0.0"))
    float AerialPerspectiveMultiplier = 0.45f;

    /** Degrees of sun movement between sky light recaptures. Recapturing every frame is
     * the single most expensive thing a time-of-day system can do. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Drive", meta = (ClampMin = "0.1"))
    float SkyLightRecaptureIntervalDeg = 2.f;

    /** Restore every property this actor wrote when play ends. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Drive")
    bool bRestoreOnEndPlay = true;

    // -----------------------------------------------------------------------
    // Clouds
    // -----------------------------------------------------------------------

    /** Scalar parameter on the cloud material that sets coverage. The engine's
     * m_SimpleVolumetricCloud (and MI_Cloud_Scattered, derived from it) exposes
     * Cloud_GlobalCoverage, Cloud_GlobalDensity, Layout_CloudGlobalScale, StormClouds. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Clouds")
    FName CloudCoverageParameter = FName("Cloud_GlobalCoverage");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Clouds")
    FName CloudDensityParameter = FName("Cloud_GlobalDensity");

    /** Vector parameter carrying wind. R and G are the wind direction, B the speed. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Clouds")
    FName CloudWindParameter = FName("Layout_WindControls");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Clouds")
    FName CloudStormParameter = FName("StormClouds");

    // -----------------------------------------------------------------------
    // Night sky
    // -----------------------------------------------------------------------

    // A star cubemap is deliberately NOT offered here: applying one means switching the sky
    // light from SLS_CAPTURED_SCENE to a specified cubemap at night, which changes how the
    // whole scene is lit and is a review decision, not a default. The night sky is the
    // atmosphere lit by the moon (atmosphere light index 1) plus NightSkyLightFloor.

    /** Sun altitude, in degrees, below which "night" lighting is fully in effect. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Night")
    float NightSunAltitudeDeg = -12.f;

    /** Minimum SkyLight Intensity once the night blend reaches 1. SkyLight Intensity is a
     * MULTIPLIER on the real-time capture, and the captured night sky is nearly black, so a
     * value well above 1 is normal here and is what keeps the courts navigable instead of
     * pitch dark. It does not brighten the day: it is only applied at full night. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Night")
    float NightSkyLightFloor = 3.0f;

    /** Force the sun's Intensity to zero once it is below the horizon.
     *
     * OFF by default, and that is deliberate. The engine already multiplies an atmosphere
     * light's colour by the atmospheric transmittance toward the sun
     * (SkyAtmosphereRendering.cpp, SetAtmosphereRelatedProperties), so a sun below the
     * horizon stops lighting the ground on its own while the sky keeps its twilight
     * gradient. Forcing the intensity to zero instead would also black out the SkyAtmosphere
     * at dawn and dusk, which is exactly the shot this system exists for. Turn it on only
     * if bAtmosphereSunLight has been cleared on the sun for some other reason. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Night")
    bool bFadeSunBelowHorizon = false;

    // -----------------------------------------------------------------------
    // The table
    // -----------------------------------------------------------------------

    /** Eight rows, indexed by EMikdashTimePreset. Filled with the shipped table in the
     * constructor; editable per instance. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Presets")
    TArray<FMikdashSkyPreset> Presets;

    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Time")
    FMikdashTimeOfDayChanged OnTimeOfDayChanged;

    // -----------------------------------------------------------------------
    // API
    // -----------------------------------------------------------------------

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Time")
    void SetTimeOfDayHours(float NewHours);

    UFUNCTION(BlueprintPure, Category = "Mikdash|Time")
    float GetTimeOfDayHours() const { return TimeOfDayHours; }

    /** 0..1: how far the fog colour is pulled toward OvercastHazeTint right now. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Haze")
    float GetOvercastHazeWeight() const;

    /** 0 at midnight, 0.5 at noon. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Time")
    void SetNormalizedTime(float Normalized);

    UFUNCTION(BlueprintPure, Category = "Mikdash|Time")
    float GetNormalizedTime() const { return TimeOfDayHours / 24.f; }

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Time")
    void AdvanceHours(float DeltaHours);

    /** 0 freezes. Setting a non-zero rate also clears bFrozen. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Time")
    void SetRateMultiplier(float NewRate);

    UFUNCTION(BlueprintPure, Category = "Mikdash|Time")
    float GetRateMultiplier() const { return bFrozen ? 0.f : RateMultiplier; }

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Time")
    void SetFrozen(bool bNewFrozen);

    UFUNCTION(BlueprintPure, Category = "Mikdash|Time")
    bool IsFrozen() const { return bFrozen || RateMultiplier <= 0.f; }

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Time")
    void SetDate(int32 NewYear, int32 NewMonth, int32 NewDay);

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Time")
    void GetDate(int32& OutYear, int32& OutMonth, int32& OutDay) const;

    /** Jump to a named time of day on the CURRENT date. The hour is derived from that
     * day's real sunrise, solar noon and sunset, so "sunrise" in December is 06:35 and in
     * June 05:34, not a fixed number. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Time")
    void JumpToPreset(EMikdashTimePreset Preset);

    UFUNCTION(BlueprintPure, Category = "Mikdash|Time")
    float GetPresetHours(EMikdashTimePreset Preset) const;

    /** Force a full re-apply without waiting for the next tick. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Time")
    void ApplyNow();

    /** Re-run the find-by-class binding. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Scene")
    void BindSceneActors();

    UFUNCTION(BlueprintPure, Category = "Mikdash|Sun") float GetSunAltitudeDegrees() const { return CachedSunAltitudeDeg; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Sun") float GetSunAzimuthDegrees() const { return CachedSunAzimuthDeg; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Sun") float GetSunriseHours() const { return CachedSunriseHours; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Sun") float GetSunsetHours() const { return CachedSunsetHours; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Sun") float GetSolarNoonHours() const { return CachedSolarNoonHours; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Sun") float GetCivilDawnHours() const { return CachedCivilDawnHours; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Sun") float GetCivilDuskHours() const { return CachedCivilDuskHours; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Sun") float GetTimeZoneOffsetHours() const { return CachedTimeZoneOffset; }

    UFUNCTION(BlueprintPure, Category = "Mikdash|Moon") float GetMoonAltitudeDegrees() const { return CachedMoonAltitudeDeg; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Moon") float GetMoonAzimuthDegrees() const { return CachedMoonAzimuthDeg; }
    /** 0 new, 0.25 first quarter, 0.5 full, 0.75 last quarter. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Moon") float GetMoonPhaseFraction() const { return CachedMoonPhaseFraction; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Moon") float GetMoonIlluminatedFraction() const { return CachedMoonIllumination; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Moon") float GetMoonAgeDays() const { return CachedMoonAgeDays; }
    /** Degrees east of north; the lit limb faces this way. Exposed for a mesh moon; the
     * atmosphere's moon disc is round and cannot show a crescent. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Moon") float GetMoonBrightLimbAngleDegrees() const { return CachedMoonLimbAngleDeg; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Moon") FText GetMoonPhaseName() const;

    /** 0 in full day, 1 once the sun is below NightSunAltitudeDeg. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Sun") float GetNightBlend() const { return CachedNightBlend; }

    UFUNCTION(BlueprintPure, Category = "Mikdash|Presets")
    FMikdashSkyPreset GetBlendedPreset() const { return CachedBlended; }

    /** Called by AMikdashWeather. The modifier is stored, not applied immediately; the
     * next apply folds it in. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Weather")
    void SetWeatherModifier(const FMikdashSkyModifier& Modifier);

    UFUNCTION(BlueprintPure, Category = "Mikdash|Weather")
    FMikdashSkyModifier GetWeatherModifier() const { return WeatherModifier; }

    /** Wind, in the same units AMikdashWeather uses, pushed into the cloud material. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Weather")
    void SetWind(float DirectionDeg, float SpeedKph);

    /** A single line naming date, clock, sun and moon. Written into the release receipt
     * and useful in a debug overlay. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Time")
    FString DescribeState() const;

    static MikdashSun::ETimePreset TimePresetToNative(EMikdashTimePreset Preset);

    // AActor
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;
#if WITH_EDITOR
    virtual void PostEditChangeProperty(FPropertyChangedEvent& Event) override;
#endif

protected:
    /** Fill Presets with the shipped eight-row table. */
    void BuildDefaultPresets();

    void RecomputeAstronomy();
    void RecomputeBlend();
    void ApplyToScene();

    void ApplySun(const FMikdashSkyPreset& P);
    void ApplyMoon(const FMikdashSkyPreset& P);
    void ApplySkyLight(const FMikdashSkyPreset& P);
    void ApplySkyAtmosphere(const FMikdashSkyPreset& P);
    void ApplyClouds(const FMikdashSkyPreset& P);
    void ApplyFog(const FMikdashSkyPreset& P);
    void ApplyExposure(const FMikdashSkyPreset& P);

    FLinearColor EffectiveFogColorScale(const FMikdashSkyPreset& P) const;
    float EffectiveFogMaxOpacity(const FMikdashSkyPreset& P) const;
    float EffectiveAerialPerspectiveMultiplier() const;

    /** Last value of mikdash.TimeOfDay.ForcePreset acted on (review captures only). */
    int32 LastForcedPreset = -1;

    void CaptureSnapshot();
    void RestoreSnapshot();

    FRotator RotationForSky(double AzimuthDeg, double AltitudeDeg) const;
    double CurrentTimeZoneOffset() const;

    /** True when the project's r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange is
     * on, in which case the min/max brightness fields are EV100 rather than raw luminance.
     * This project runs with it OFF, so the actor writes 2^EV. */
    bool UsesExtendedLuminanceRange() const;

    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> CloudMaterialInstance = nullptr;
    UPROPERTY(Transient) FMikdashSkySnapshot Snapshot;
    UPROPERTY(Transient) FMikdashSkyModifier WeatherModifier;
    UPROPERTY(Transient) FMikdashSkyPreset CachedBlended;

    float CachedSunAltitudeDeg = 0.f;
    float CachedSunAzimuthDeg = 90.f;
    float CachedSunriseHours = 6.f;
    float CachedSunsetHours = 18.f;
    float CachedSolarNoonHours = 12.f;
    float CachedCivilDawnHours = 5.5f;
    float CachedCivilDuskHours = 18.5f;
    float CachedTimeZoneOffset = 2.f;

    float CachedMoonAltitudeDeg = 0.f;
    float CachedMoonAzimuthDeg = 0.f;
    float CachedMoonPhaseFraction = 0.f;
    float CachedMoonIllumination = 0.f;
    float CachedMoonAgeDays = 0.f;
    float CachedMoonLimbAngleDeg = 0.f;

    float CachedNightBlend = 0.f;
    float LastRecaptureSunAltitudeDeg = -1000.f;
    float LastBroadcastHours = -1.f;
    int32 LastBroadcastDateKey = 0;

    float WindDirectionDeg = 270.f;
    float WindSpeedKph = 8.f;
    float CloudWindPhase = 0.f;

    MikdashSun::FDayEvents CachedEvents;
    bool bSpawnedMoonLight = false;
};
