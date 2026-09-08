#include "MikdashTimeOfDay.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/SkyLight.h"
#include "Engine/TextureCube.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

DEFINE_LOG_CATEGORY_STATIC(LogMikdashSky, Log, All);

namespace
{
/** Smooth 0..1 ramp, used for every preset blend so a scrub never shows a kink. */
float SmoothStep01(float T)
{
    T = FMath::Clamp(T, 0.f, 1.f);
    return T * T * (3.f - 2.f * T);
}

FLinearColor LerpColour(const FLinearColor& A, const FLinearColor& B, float T)
{
    return FLinearColor(FMath::Lerp(A.R, B.R, T), FMath::Lerp(A.G, B.G, T), FMath::Lerp(A.B, B.B, T),
                        FMath::Lerp(A.A, B.A, T));
}

FMikdashSkyPreset LerpPreset(const FMikdashSkyPreset& A, const FMikdashSkyPreset& B, float T)
{
    FMikdashSkyPreset R;
    R.SunIntensityLux = FMath::Lerp(A.SunIntensityLux, B.SunIntensityLux, T);
    R.SunTemperatureK = FMath::Lerp(A.SunTemperatureK, B.SunTemperatureK, T);
    R.SunSourceAngleDeg = FMath::Lerp(A.SunSourceAngleDeg, B.SunSourceAngleDeg, T);
    R.SunVolumetricScatteringIntensity =
        FMath::Lerp(A.SunVolumetricScatteringIntensity, B.SunVolumetricScatteringIntensity, T);
    R.MoonIntensityLux = FMath::Lerp(A.MoonIntensityLux, B.MoonIntensityLux, T);
    R.MoonTemperatureK = FMath::Lerp(A.MoonTemperatureK, B.MoonTemperatureK, T);
    R.SkyLightIntensity = FMath::Lerp(A.SkyLightIntensity, B.SkyLightIntensity, T);
    R.FogDensity = FMath::Lerp(A.FogDensity, B.FogDensity, T);
    R.FogHeightFalloff = FMath::Lerp(A.FogHeightFalloff, B.FogHeightFalloff, T);
    R.FogStartDistance = FMath::Lerp(A.FogStartDistance, B.FogStartDistance, T);
    R.FogMaxOpacity = FMath::Lerp(A.FogMaxOpacity, B.FogMaxOpacity, T);
    R.FogColorScale = LerpColour(A.FogColorScale, B.FogColorScale, T);
    R.DirectionalInscatteringLuminance = LerpColour(A.DirectionalInscatteringLuminance, B.DirectionalInscatteringLuminance, T);
    R.bVolumetricFog = T < 0.5f ? A.bVolumetricFog : B.bVolumetricFog;
    R.CloudCoverage = FMath::Lerp(A.CloudCoverage, B.CloudCoverage, T);
    R.CloudDensity = FMath::Lerp(A.CloudDensity, B.CloudDensity, T);
    R.ExposureBiasEV = FMath::Lerp(A.ExposureBiasEV, B.ExposureBiasEV, T);
    R.ExposureMinEV100 = FMath::Lerp(A.ExposureMinEV100, B.ExposureMinEV100, T);
    R.ExposureMaxEV100 = FMath::Lerp(A.ExposureMaxEV100, B.ExposureMaxEV100, T);
    R.AerialPerspectiveViewDistanceScale =
        FMath::Lerp(A.AerialPerspectiveViewDistanceScale, B.AerialPerspectiveViewDistanceScale, T);
    R.MieScatteringScale = FMath::Lerp(A.MieScatteringScale, B.MieScatteringScale, T);
    R.SkyLuminanceFactor = FMath::Lerp(A.SkyLuminanceFactor, B.SkyLuminanceFactor, T);
    return R;
}

/** Two-decimal clock string for the debug line. */
FString ClockString(float Hours)
{
    const float H = FMath::Fmod(FMath::Fmod(Hours, 24.f) + 24.f, 24.f);
    const int32 Hour = FMath::FloorToInt(H);
    const int32 Minute = FMath::FloorToInt((H - Hour) * 60.f);
    return FString::Printf(TEXT("%02d:%02d"), Hour, Minute);
}
} // namespace

AMikdashTimeOfDay::AMikdashTimeOfDay()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = true;
    // Editor ticking is OFF: this actor writes to shared lighting actors, and a background
    // tick in the level editor would leave the map looking different from what is saved.
    PrimaryActorTick.bTickEvenWhenPaused = false;
    SetActorEnableCollision(false);
    bIsEditorOnlyActor = false;

    BuildDefaultPresets();
}

// ---------------------------------------------------------------------------
// The table
// ---------------------------------------------------------------------------

void AMikdashTimeOfDay::BuildDefaultPresets()
{
    Presets.Reset();
    Presets.SetNum(int32(EMikdashTimePreset::Night) + 1);

    // Shared, non-negotiable fog geometry: the authored tune from
    // SourceAssets/lighting-review/fog-tune-20260908T024650Z.json.
    auto AuthoredFog = [](FMikdashSkyPreset& P)
    {
        P.FogHeightFalloff = 0.15f;
        P.FogStartDistance = 8000.f;
        P.FogMaxOpacity = 1.f;
        P.bVolumetricFog = false;
    };

    {
        FMikdashSkyPreset& P = Presets[int32(EMikdashTimePreset::Dawn)];
        AuthoredFog(P);
        // Civil twilight. The disc is still down; almost everything comes from the sky.
        // The sun's own intensity is nearly irrelevant here because the engine multiplies
        // it by the atmospheric transmittance, which is close to zero below the horizon.
        P.SunIntensityLux = 18000.f;
        P.SunTemperatureK = 3200.f;
        P.SunSourceAngleDeg = 1.0f;
        P.SunVolumetricScatteringIntensity = 1.4f;
        P.MoonIntensityLux = 1.2f;
        P.MoonTemperatureK = 8500.f;
        P.SkyLightIntensity = 1.35f;
        P.FogDensity = 0.0020f;
        P.FogColorScale = FLinearColor(1.00f, 0.78f, 0.68f, 1.f);
        P.DirectionalInscatteringLuminance = FLinearColor(120.f, 70.f, 55.f, 1.f);
        P.CloudCoverage = 0.30f;
        P.CloudDensity = 0.12f;
        P.ExposureBiasEV = 0.5f;
        P.ExposureMinEV100 = -1.f;
        P.ExposureMaxEV100 = 14.f;
        P.AerialPerspectiveViewDistanceScale = 2.2f;
        P.MieScatteringScale = 0.0075f;
        P.SkyLuminanceFactor = 1.f;
    }
    {
        FMikdashSkyPreset& P = Presets[int32(EMikdashTimePreset::Sunrise)];
        AuthoredFog(P);
        // Disc on the horizon over the Mount of Olives. Long shadows west across the courts.
        P.SunIntensityLux = 26000.f;
        P.SunTemperatureK = 2500.f;
        P.SunSourceAngleDeg = 0.8f;
        P.SunVolumetricScatteringIntensity = 1.6f;
        P.MoonIntensityLux = 0.6f;
        P.MoonTemperatureK = 8500.f;
        P.SkyLightIntensity = 1.15f;
        P.FogDensity = 0.0019f;
        P.FogColorScale = FLinearColor(1.00f, 0.84f, 0.66f, 1.f);
        P.DirectionalInscatteringLuminance = FLinearColor(1400.f, 700.f, 320.f, 1.f);
        P.CloudCoverage = 0.32f;
        P.CloudDensity = 0.13f;
        P.ExposureBiasEV = 0.25f;
        P.ExposureMinEV100 = 0.f;
        P.ExposureMaxEV100 = 14.f;
        P.AerialPerspectiveViewDistanceScale = 2.1f;
        P.MieScatteringScale = 0.0070f;
        P.SkyLuminanceFactor = 1.f;
    }
    {
        FMikdashSkyPreset& P = Presets[int32(EMikdashTimePreset::Morning)];
        AuthoredFog(P);
        // Matches the reviewed live scene exactly: 30 klux at 5000 K, source angle 0.5,
        // volumetric scattering 1.0, fog 0.0015, exposure bias 0, bounds EV 0..14.
        P.SunIntensityLux = 30000.f;
        P.SunTemperatureK = 5000.f;
        P.SunSourceAngleDeg = 0.5f;
        P.SunVolumetricScatteringIntensity = 1.0f;
        P.MoonIntensityLux = 0.f;
        P.MoonTemperatureK = 8000.f;
        P.SkyLightIntensity = 1.0f;
        P.FogDensity = 0.0015f;
        P.FogColorScale = FLinearColor(1.00f, 0.96f, 0.90f, 1.f);
        P.DirectionalInscatteringLuminance = FLinearColor(1500.f, 1170.f, 750.f, 1.f);
        P.CloudCoverage = 0.35f;
        P.CloudDensity = 0.15f;
        P.ExposureBiasEV = 0.f;
        P.ExposureMinEV100 = 0.f;
        P.ExposureMaxEV100 = 14.f;
        P.AerialPerspectiveViewDistanceScale = 1.8f;
        P.MieScatteringScale = 0.0050f;
        P.SkyLuminanceFactor = 1.f;
    }
    {
        FMikdashSkyPreset& P = Presets[int32(EMikdashTimePreset::Midday)];
        AuthoredFog(P);
        // Solar noon. FOG IS THE AUTHORED TUNE, UNCHANGED: 0.0015 / 0.15 / 8000 /
        // volumetric off. Exposure bias 0 and bounds EV 0..14, which are the live values.
        P.SunIntensityLux = 42000.f;
        P.SunTemperatureK = 5600.f;
        P.SunSourceAngleDeg = 0.5f;
        P.SunVolumetricScatteringIntensity = 0.8f;
        P.MoonIntensityLux = 0.f;
        P.MoonTemperatureK = 8000.f;
        P.SkyLightIntensity = 1.10f;
        P.FogDensity = 0.0015f;
        P.FogColorScale = FLinearColor(1.00f, 1.00f, 1.00f, 1.f);
        P.DirectionalInscatteringLuminance = FLinearColor(1200.f, 1150.f, 1050.f, 1.f);
        P.CloudCoverage = 0.30f;
        P.CloudDensity = 0.14f;
        P.ExposureBiasEV = 0.f;
        P.ExposureMinEV100 = 0.f;
        P.ExposureMaxEV100 = 14.f;
        P.AerialPerspectiveViewDistanceScale = 1.6f;
        P.MieScatteringScale = 0.0045f;
        P.SkyLuminanceFactor = 1.f;
    }
    {
        FMikdashSkyPreset& P = Presets[int32(EMikdashTimePreset::Afternoon)];
        AuthoredFog(P);
        P.SunIntensityLux = 28000.f;
        P.SunTemperatureK = 4700.f;
        P.SunSourceAngleDeg = 0.5f;
        P.SunVolumetricScatteringIntensity = 1.1f;
        P.MoonIntensityLux = 0.f;
        P.MoonTemperatureK = 8000.f;
        P.SkyLightIntensity = 0.95f;
        P.FogDensity = 0.0015f;
        P.FogColorScale = FLinearColor(1.00f, 0.94f, 0.84f, 1.f);
        P.DirectionalInscatteringLuminance = FLinearColor(1600.f, 1150.f, 700.f, 1.f);
        P.CloudCoverage = 0.35f;
        P.CloudDensity = 0.15f;
        P.ExposureBiasEV = 0.f;
        P.ExposureMinEV100 = 0.f;
        P.ExposureMaxEV100 = 14.f;
        P.AerialPerspectiveViewDistanceScale = 1.9f;
        P.MieScatteringScale = 0.0055f;
        P.SkyLuminanceFactor = 1.f;
    }
    {
        FMikdashSkyPreset& P = Presets[int32(EMikdashTimePreset::Sunset)];
        AuthoredFog(P);
        P.SunIntensityLux = 26000.f;
        P.SunTemperatureK = 2300.f;
        P.SunSourceAngleDeg = 0.8f;
        P.SunVolumetricScatteringIntensity = 1.6f;
        P.MoonIntensityLux = 0.8f;
        P.MoonTemperatureK = 8500.f;
        P.SkyLightIntensity = 1.10f;
        P.FogDensity = 0.0018f;
        P.FogColorScale = FLinearColor(1.00f, 0.76f, 0.55f, 1.f);
        P.DirectionalInscatteringLuminance = FLinearColor(1700.f, 800.f, 330.f, 1.f);
        P.CloudCoverage = 0.38f;
        P.CloudDensity = 0.16f;
        P.ExposureBiasEV = 0.25f;
        P.ExposureMinEV100 = 0.f;
        P.ExposureMaxEV100 = 14.f;
        P.AerialPerspectiveViewDistanceScale = 2.1f;
        P.MieScatteringScale = 0.0075f;
        P.SkyLuminanceFactor = 1.f;
    }
    {
        FMikdashSkyPreset& P = Presets[int32(EMikdashTimePreset::Dusk)];
        AuthoredFog(P);
        P.SunIntensityLux = 18000.f;
        P.SunTemperatureK = 3000.f;
        P.SunSourceAngleDeg = 1.0f;
        P.SunVolumetricScatteringIntensity = 1.4f;
        P.MoonIntensityLux = 1.6f;
        P.MoonTemperatureK = 8500.f;
        P.SkyLightIntensity = 1.4f;
        P.FogDensity = 0.0020f;
        P.FogColorScale = FLinearColor(0.88f, 0.78f, 0.82f, 1.f);
        P.DirectionalInscatteringLuminance = FLinearColor(110.f, 65.f, 60.f, 1.f);
        P.CloudCoverage = 0.34f;
        P.CloudDensity = 0.13f;
        P.ExposureBiasEV = 0.6f;
        P.ExposureMinEV100 = -1.5f;
        P.ExposureMaxEV100 = 14.f;
        P.AerialPerspectiveViewDistanceScale = 2.2f;
        P.MieScatteringScale = 0.0080f;
        P.SkyLuminanceFactor = 1.f;
    }
    {
        FMikdashSkyPreset& P = Presets[int32(EMikdashTimePreset::Night)];
        AuthoredFog(P);
        // The sun value is inert: below about -6 degrees the atmosphere transmittance the
        // renderer applies is effectively zero, so this light contributes nothing. It is
        // kept at a daylight magnitude so blending toward dusk stays smooth.
        P.SunIntensityLux = 15000.f;
        P.SunTemperatureK = 3800.f;
        P.SunSourceAngleDeg = 0.5f;
        P.SunVolumetricScatteringIntensity = 1.0f;
        // Full-moon illuminance in reality is about 0.25 lux, which no tonemapped render
        // can show. 3 lux is a deliberate cinematic lift, scaled at run time by the
        // illuminated fraction so a new moon really is dark.
        P.MoonIntensityLux = 3.0f;
        P.MoonTemperatureK = 9000.f;
        P.SkyLightIntensity = 3.0f;
        P.FogDensity = 0.0016f;
        P.FogColorScale = FLinearColor(0.55f, 0.64f, 0.88f, 1.f);
        P.DirectionalInscatteringLuminance = FLinearColor(0.f, 0.f, 0.f, 1.f);
        P.CloudCoverage = 0.28f;
        P.CloudDensity = 0.12f;
        P.ExposureBiasEV = 1.4f;
        P.ExposureMinEV100 = -3.f;
        P.ExposureMaxEV100 = 14.f;
        P.AerialPerspectiveViewDistanceScale = 1.6f;
        P.MieScatteringScale = 0.0040f;
        P.SkyLuminanceFactor = 1.f;
    }
}

MikdashSun::ETimePreset AMikdashTimeOfDay::TimePresetToNative(EMikdashTimePreset Preset)
{
    switch (Preset)
    {
    case EMikdashTimePreset::Dawn: return MikdashSun::ETimePreset::Dawn;
    case EMikdashTimePreset::Sunrise: return MikdashSun::ETimePreset::Sunrise;
    case EMikdashTimePreset::Morning: return MikdashSun::ETimePreset::Morning;
    case EMikdashTimePreset::Midday: return MikdashSun::ETimePreset::Midday;
    case EMikdashTimePreset::Afternoon: return MikdashSun::ETimePreset::Afternoon;
    case EMikdashTimePreset::Sunset: return MikdashSun::ETimePreset::Sunset;
    case EMikdashTimePreset::Dusk: return MikdashSun::ETimePreset::Dusk;
    default: return MikdashSun::ETimePreset::Night;
    }
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

void AMikdashTimeOfDay::BeginPlay()
{
    Super::BeginPlay();

    if (Presets.Num() <= int32(EMikdashTimePreset::Night))
    {
        BuildDefaultPresets();
    }

    BindSceneActors();
    CaptureSnapshot();

    if (bApplyStartPresetOnBeginPlay)
    {
        JumpToPreset(StartPreset);
    }
    else
    {
        ApplyNow();
    }
}

void AMikdashTimeOfDay::EndPlay(const EEndPlayReason::Type Reason)
{
    if (bRestoreOnEndPlay)
    {
        RestoreSnapshot();
    }
    Super::EndPlay(Reason);
}

void AMikdashTimeOfDay::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);

    const float Rate = GetRateMultiplier();
    if (Rate > 0.f && DeltaSeconds > 0.f)
    {
        AdvanceHours(DeltaSeconds * Rate / 3600.f);
    }
    else
    {
        // Frozen still applies, because weather and wind keep moving.
        ApplyNow();
    }

    CloudWindPhase += DeltaSeconds * WindSpeedKph / 3600.f;
}

#if WITH_EDITOR
void AMikdashTimeOfDay::PostEditChangeProperty(FPropertyChangedEvent& Event)
{
    Super::PostEditChangeProperty(Event);
    // Only recompute the readouts. Writing to the shared lighting actors from an editor
    // property change would dirty other people's packages, so the scene is left alone
    // until play begins or ApplyNow() is called explicitly.
    RecomputeAstronomy();
    RecomputeBlend();
}
#endif

// ---------------------------------------------------------------------------
// Binding
// ---------------------------------------------------------------------------

void AMikdashTimeOfDay::BindSceneActors()
{
    UWorld* World = GetWorld();
    if (!World)
    {
        return;
    }

    if (!SunLight)
    {
        // The sun is the directional light flagged as the atmosphere sun; if none is
        // flagged, the brightest one wins. Picking "the first directional light" would bind
        // to a fill light in a map that has more than one.
        ADirectionalLight* Best = nullptr;
        float BestIntensity = -1.f;
        for (TActorIterator<ADirectionalLight> It(World); It; ++It)
        {
            ADirectionalLight* Light = *It;
            if (!Light || Light == MoonLight)
            {
                continue;
            }
            UDirectionalLightComponent* C = Light->FindComponentByClass<UDirectionalLightComponent>();
            if (!C)
            {
                continue;
            }
            if (C->bAtmosphereSunLight && C->AtmosphereSunLightIndex == 0)
            {
                Best = Light;
                break;
            }
            if (C->Intensity > BestIntensity)
            {
                BestIntensity = C->Intensity;
                Best = Light;
            }
        }
        SunLight = Best;
    }

    if (!SkyLight)
    {
        for (TActorIterator<ASkyLight> It(World); It; ++It)
        {
            SkyLight = *It;
            break;
        }
    }
    if (!SkyAtmosphere)
    {
        for (TActorIterator<ASkyAtmosphere> It(World); It; ++It)
        {
            SkyAtmosphere = *It;
            break;
        }
    }
    if (!VolumetricCloud)
    {
        for (TActorIterator<AVolumetricCloud> It(World); It; ++It)
        {
            VolumetricCloud = *It;
            break;
        }
    }
    if (!HeightFog)
    {
        for (TActorIterator<AExponentialHeightFog> It(World); It; ++It)
        {
            HeightFog = *It;
            break;
        }
    }
    if (!PostProcessVolume)
    {
        // Prefer an unbound volume: that is the one that actually grades the walkthrough.
        APostProcessVolume* Fallback = nullptr;
        for (TActorIterator<APostProcessVolume> It(World); It; ++It)
        {
            APostProcessVolume* Volume = *It;
            if (!Volume)
            {
                continue;
            }
            if (Volume->bUnbound)
            {
                PostProcessVolume = Volume;
                break;
            }
            if (!Fallback)
            {
                Fallback = Volume;
            }
        }
        if (!PostProcessVolume)
        {
            PostProcessVolume = Fallback;
        }
    }

    if (!MoonLight && bSpawnMoonLightIfMissing && bDriveMoon)
    {
        FActorSpawnParameters Params;
        Params.Owner = this;
        Params.ObjectFlags |= RF_Transient; // never saved into the map
        ADirectionalLight* Spawned = World->SpawnActor<ADirectionalLight>(ADirectionalLight::StaticClass(),
                                                                         FVector::ZeroVector, FRotator::ZeroRotator, Params);
        if (Spawned)
        {
            Spawned->SetMobility(EComponentMobility::Movable);
#if WITH_EDITOR
            Spawned->SetActorLabel(TEXT("MikdashTimeOfDay_Moon"));
#endif
            if (UDirectionalLightComponent* C = Spawned->FindComponentByClass<UDirectionalLightComponent>())
            {
                C->SetAtmosphereSunLight(true);
                C->SetAtmosphereSunLightIndex(1);
                C->SetLightSourceAngle(0.545f); // the moon's real angular diameter
                C->SetIntensity(0.f);
                C->SetUseTemperature(true);
                C->SetTemperature(9000.f);
                C->SetCastShadows(true);
            }
            MoonLight = Spawned;
            bSpawnedMoonLight = true;
        }
    }

    // A time-of-day sun must be movable or the rotation will not take.
    if (SunLight)
    {
        if (UDirectionalLightComponent* C = SunLight->FindComponentByClass<UDirectionalLightComponent>())
        {
            if (C->Mobility != EComponentMobility::Movable)
            {
                UE_LOG(LogMikdashSky, Warning,
                       TEXT("Sun light '%s' is not Movable; the time-of-day rotation will not apply. Set it Movable in "
                            "the map (release_sky_tod.py records and can set this)."),
                       *SunLight->GetName());
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Snapshot
// ---------------------------------------------------------------------------

void AMikdashTimeOfDay::CaptureSnapshot()
{
    Snapshot = FMikdashSkySnapshot();

    if (SunLight)
    {
        Snapshot.SunRotation = SunLight->GetActorRotation();
        if (const UDirectionalLightComponent* C = SunLight->FindComponentByClass<UDirectionalLightComponent>())
        {
            Snapshot.SunIntensity = C->Intensity;
            Snapshot.bSunUseTemperature = C->bUseTemperature;
            Snapshot.SunTemperature = C->Temperature;
            Snapshot.SunSourceAngle = C->LightSourceAngle;
            Snapshot.SunVolumetricScattering = C->VolumetricScatteringIntensity;
        }
    }
    if (SkyLight)
    {
        if (const USkyLightComponent* C = SkyLight->FindComponentByClass<USkyLightComponent>())
        {
            Snapshot.SkyLightIntensity = C->Intensity;
        }
    }
    if (HeightFog)
    {
        if (const UExponentialHeightFogComponent* C = HeightFog->FindComponentByClass<UExponentialHeightFogComponent>())
        {
            Snapshot.FogDensity = C->FogDensity;
            Snapshot.FogHeightFalloff = C->FogHeightFalloff;
            Snapshot.FogStartDistance = C->StartDistance;
            Snapshot.FogMaxOpacity = C->FogMaxOpacity;
            Snapshot.bFogVolumetric = C->bEnableVolumetricFog;
            Snapshot.FogColorScale = C->SkyAtmosphereAmbientContributionColorScale;
            Snapshot.FogDirectionalInscattering = C->DirectionalInscatteringLuminance;
        }
    }
    if (SkyAtmosphere)
    {
        if (const USkyAtmosphereComponent* C = SkyAtmosphere->FindComponentByClass<USkyAtmosphereComponent>())
        {
            Snapshot.AerialPerspectiveScale = C->AerialPespectiveViewDistanceScale;
            Snapshot.MieScatteringScale = C->MieScatteringScale;
            Snapshot.SkyLuminanceFactor = C->SkyLuminanceFactor;
        }
    }
    if (VolumetricCloud)
    {
        if (const UVolumetricCloudComponent* C = VolumetricCloud->FindComponentByClass<UVolumetricCloudComponent>())
        {
            Snapshot.CloudMaterial = C->GetMaterial();
        }
    }
    if (PostProcessVolume)
    {
        Snapshot.PostProcess = PostProcessVolume->Settings;
        Snapshot.bPostProcessValid = true;
    }
    Snapshot.bValid = true;
}

void AMikdashTimeOfDay::RestoreSnapshot()
{
    if (!Snapshot.bValid)
    {
        return;
    }

    if (SunLight)
    {
        SunLight->SetActorRotation(Snapshot.SunRotation);
        if (UDirectionalLightComponent* C = SunLight->FindComponentByClass<UDirectionalLightComponent>())
        {
            C->SetIntensity(Snapshot.SunIntensity);
            C->SetUseTemperature(Snapshot.bSunUseTemperature);
            C->SetTemperature(Snapshot.SunTemperature);
            C->SetLightSourceAngle(Snapshot.SunSourceAngle);
            C->SetVolumetricScatteringIntensity(Snapshot.SunVolumetricScattering);
        }
    }
    if (SkyLight)
    {
        if (USkyLightComponent* C = SkyLight->FindComponentByClass<USkyLightComponent>())
        {
            C->SetIntensity(Snapshot.SkyLightIntensity);
        }
    }
    if (HeightFog)
    {
        if (UExponentialHeightFogComponent* C = HeightFog->FindComponentByClass<UExponentialHeightFogComponent>())
        {
            C->SetFogDensity(Snapshot.FogDensity);
            C->SetFogHeightFalloff(Snapshot.FogHeightFalloff);
            C->SetStartDistance(Snapshot.FogStartDistance);
            C->SetFogMaxOpacity(Snapshot.FogMaxOpacity);
            C->SetVolumetricFog(Snapshot.bFogVolumetric);
            C->SetSkyAtmosphereAmbientContributionColorScale(Snapshot.FogColorScale);
            C->SetDirectionalInscatteringColor(Snapshot.FogDirectionalInscattering);
        }
    }
    if (SkyAtmosphere)
    {
        if (USkyAtmosphereComponent* C = SkyAtmosphere->FindComponentByClass<USkyAtmosphereComponent>())
        {
            C->SetAerialPespectiveViewDistanceScale(Snapshot.AerialPerspectiveScale);
            C->SetMieScatteringScale(Snapshot.MieScatteringScale);
            C->SetSkyLuminanceFactor(Snapshot.SkyLuminanceFactor);
        }
    }
    if (VolumetricCloud)
    {
        if (UVolumetricCloudComponent* C = VolumetricCloud->FindComponentByClass<UVolumetricCloudComponent>())
        {
            C->SetMaterial(Snapshot.CloudMaterial);
        }
    }
    if (PostProcessVolume && Snapshot.bPostProcessValid)
    {
        PostProcessVolume->Settings = Snapshot.PostProcess;
    }
    CloudMaterialInstance = nullptr;
}

// ---------------------------------------------------------------------------
// Time API
// ---------------------------------------------------------------------------

double AMikdashTimeOfDay::CurrentTimeZoneOffset() const
{
    if (bUseIsraeliDaylightSaving)
    {
        return MikdashSun::IsraelUtcOffsetHours(Year, Month, Day, TimeOfDayHours);
    }
    return ManualTimeZoneOffsetHours;
}

void AMikdashTimeOfDay::SetTimeOfDayHours(float NewHours)
{
    TimeOfDayHours = float(MikdashSun::Wrap24(NewHours));
    ApplyNow();
}

void AMikdashTimeOfDay::SetNormalizedTime(float Normalized)
{
    SetTimeOfDayHours(float(MikdashSun::HoursFromNormalizedTime(Normalized)));
}

void AMikdashTimeOfDay::AdvanceHours(float DeltaHours)
{
    float NewHours = TimeOfDayHours + DeltaHours;
    if (bAdvanceDateAtMidnight)
    {
        while (NewHours >= 24.f)
        {
            NewHours -= 24.f;
            ++Day;
            if (Day > MikdashSun::DaysInMonth(Year, Month))
            {
                Day = 1;
                ++Month;
                if (Month > 12)
                {
                    Month = 1;
                    ++Year;
                }
            }
        }
        while (NewHours < 0.f)
        {
            NewHours += 24.f;
            --Day;
            if (Day < 1)
            {
                --Month;
                if (Month < 1)
                {
                    Month = 12;
                    --Year;
                }
                Day = MikdashSun::DaysInMonth(Year, Month);
            }
        }
    }
    TimeOfDayHours = float(MikdashSun::Wrap24(NewHours));
    ApplyNow();
}

void AMikdashTimeOfDay::SetRateMultiplier(float NewRate)
{
    RateMultiplier = FMath::Max(0.f, NewRate);
    if (RateMultiplier > 0.f)
    {
        bFrozen = false;
    }
}

void AMikdashTimeOfDay::SetFrozen(bool bNewFrozen)
{
    bFrozen = bNewFrozen;
}

void AMikdashTimeOfDay::SetDate(int32 NewYear, int32 NewMonth, int32 NewDay)
{
    Year = FMath::Clamp(NewYear, 1900, 2200);
    Month = FMath::Clamp(NewMonth, 1, 12);
    Day = FMath::Clamp(NewDay, 1, MikdashSun::DaysInMonth(Year, Month));
    ApplyNow();
}

void AMikdashTimeOfDay::GetDate(int32& OutYear, int32& OutMonth, int32& OutDay) const
{
    OutYear = Year;
    OutMonth = Month;
    OutDay = Day;
}

float AMikdashTimeOfDay::GetPresetHours(EMikdashTimePreset Preset) const
{
    const double Tz = CurrentTimeZoneOffset();
    const MikdashSun::FDayEvents Events =
        MikdashSun::ComputeDayEvents(LatitudeDeg, LongitudeDeg, Year, Month, Day, Tz);
    return float(MikdashSun::PresetHours(Events, TimePresetToNative(Preset)));
}

void AMikdashTimeOfDay::JumpToPreset(EMikdashTimePreset Preset)
{
    SetTimeOfDayHours(GetPresetHours(Preset));
}

void AMikdashTimeOfDay::SetWeatherModifier(const FMikdashSkyModifier& Modifier)
{
    WeatherModifier = Modifier;
    ApplyNow();
}

void AMikdashTimeOfDay::SetWind(float DirectionDeg, float SpeedKph)
{
    WindDirectionDeg = float(MikdashSun::Wrap360(DirectionDeg));
    WindSpeedKph = FMath::Max(0.f, SpeedKph);
}

// ---------------------------------------------------------------------------
// Astronomy and blending
// ---------------------------------------------------------------------------

void AMikdashTimeOfDay::RecomputeAstronomy()
{
    const double Tz = CurrentTimeZoneOffset();
    CachedTimeZoneOffset = float(Tz);

    CachedEvents = MikdashSun::ComputeDayEvents(LatitudeDeg, LongitudeDeg, Year, Month, Day, Tz);
    CachedSunriseHours = float(CachedEvents.SunriseHours);
    CachedSunsetHours = float(CachedEvents.SunsetHours);
    CachedSolarNoonHours = float(CachedEvents.SolarNoonHours);
    CachedCivilDawnHours = float(CachedEvents.CivilDawnHours);
    CachedCivilDuskHours = float(CachedEvents.CivilDuskHours);

    const MikdashSun::FSolarAngles Sun =
        MikdashSun::SolarPosition(LatitudeDeg, LongitudeDeg, Year, Month, Day, TimeOfDayHours, Tz);
    CachedSunAltitudeDeg = float(Sun.AltitudeDeg);
    CachedSunAzimuthDeg = float(Sun.AzimuthDeg);

    const MikdashSun::FMoonState Moon =
        MikdashSun::MoonState(LatitudeDeg, LongitudeDeg, Year, Month, Day, TimeOfDayHours, Tz);
    CachedMoonAltitudeDeg = float(Moon.AltitudeDeg);
    CachedMoonAzimuthDeg = float(Moon.AzimuthDeg);
    CachedMoonPhaseFraction = float(Moon.PhaseFraction);
    CachedMoonIllumination = float(Moon.IlluminatedFraction);
    CachedMoonAgeDays = float(Moon.AgeDays);
    CachedMoonLimbAngleDeg = float(Moon.BrightLimbAngleDeg);

    // 0 while the sun is up, 1 once it is below NightSunAltitudeDeg.
    CachedNightBlend = 1.f - SmoothStep01((CachedSunAltitudeDeg - NightSunAltitudeDeg) / FMath::Max(1.f, -NightSunAltitudeDeg));
}

void AMikdashTimeOfDay::RecomputeBlend()
{
    if (Presets.Num() <= int32(EMikdashTimePreset::Night))
    {
        BuildDefaultPresets();
    }

    // Ring coordinate: hours since SOLAR midnight. Night sits at both ends of the ring, so
    // the eight keys are strictly increasing and dawn is never confused with dusk.
    const double SolarMidnight = MikdashSun::Wrap24(CachedEvents.SolarNoonHours + 12.0);
    auto Ring = [SolarMidnight](double Hours) { return MikdashSun::Wrap24(Hours - SolarMidnight); };

    struct FKey
    {
        double RingHours;
        int32 Index;
    };
    FKey Keys[9] = {
        {0.0, int32(EMikdashTimePreset::Night)},
        {Ring(CachedEvents.CivilDawnHours), int32(EMikdashTimePreset::Dawn)},
        {Ring(CachedEvents.SunriseHours), int32(EMikdashTimePreset::Sunrise)},
        {Ring(MikdashSun::PresetHours(CachedEvents, MikdashSun::ETimePreset::Morning)), int32(EMikdashTimePreset::Morning)},
        {Ring(CachedEvents.SolarNoonHours), int32(EMikdashTimePreset::Midday)},
        {Ring(MikdashSun::PresetHours(CachedEvents, MikdashSun::ETimePreset::Afternoon)),
         int32(EMikdashTimePreset::Afternoon)},
        {Ring(CachedEvents.SunsetHours), int32(EMikdashTimePreset::Sunset)},
        {Ring(CachedEvents.CivilDuskHours), int32(EMikdashTimePreset::Dusk)},
        {24.0, int32(EMikdashTimePreset::Night)},
    };
    // Defensive: keep the ring strictly increasing even if a pathological latitude/date
    // reorders the events. Without this the bracket search below could pick a zero-width
    // interval and divide by zero.
    for (int32 I = 1; I < 9; ++I)
    {
        Keys[I].RingHours = FMath::Max(Keys[I].RingHours, Keys[I - 1].RingHours + 1e-4);
    }

    const double Now = Ring(TimeOfDayHours);
    int32 Lower = 0;
    for (int32 I = 0; I + 1 < 9; ++I)
    {
        if (Now >= Keys[I].RingHours && Now <= Keys[I + 1].RingHours)
        {
            Lower = I;
            break;
        }
        if (I + 2 == 9)
        {
            Lower = 7;
        }
    }
    const double Span = FMath::Max(1e-6, Keys[Lower + 1].RingHours - Keys[Lower].RingHours);
    const float Alpha = SmoothStep01(float((Now - Keys[Lower].RingHours) / Span));

    FMikdashSkyPreset Blended = LerpPreset(Presets[Keys[Lower].Index], Presets[Keys[Lower + 1].Index], Alpha);

    // Weather. Clear weather ships an identity modifier, so with clear skies the blended
    // preset is exactly the table value.
    Blended.SunIntensityLux *= WeatherModifier.SunIntensityScale;
    Blended.SunTemperatureK += WeatherModifier.SunTemperatureOffsetK;
    Blended.SunSourceAngleDeg += WeatherModifier.SunSourceAngleAddDeg;
    Blended.SkyLightIntensity *= WeatherModifier.SkyLightIntensityScale;
    Blended.FogDensity *= WeatherModifier.FogDensityScale;
    Blended.FogColorScale = Blended.FogColorScale * WeatherModifier.FogColorTint;
    Blended.CloudCoverage = FMath::Clamp(Blended.CloudCoverage + WeatherModifier.CloudCoverageAdd, 0.f, 1.f);
    Blended.CloudDensity = FMath::Clamp(Blended.CloudDensity * WeatherModifier.CloudDensityScale, 0.f, 1.f);
    Blended.ExposureBiasEV += WeatherModifier.ExposureBiasAddEV;
    Blended.AerialPerspectiveViewDistanceScale *= WeatherModifier.AerialPerspectiveScale;
    Blended.MieScatteringScale *= WeatherModifier.MieScatteringScale;

    // Guards that no preset or weather edit can talk its way past.
    Blended.FogDensity = FMath::Clamp(Blended.FogDensity, 0.f, MaxFogDensity);
    if (bForbidVolumetricFog)
    {
        Blended.bVolumetricFog = false;
    }
    if (CachedNightBlend > 0.99f)
    {
        Blended.SkyLightIntensity = FMath::Max(Blended.SkyLightIntensity, NightSkyLightFloor);
    }

    CachedBlended = Blended;
}

// ---------------------------------------------------------------------------
// Application
// ---------------------------------------------------------------------------

FRotator AMikdashTimeOfDay::RotationForSky(double AzimuthDeg, double AltitudeDeg) const
{
    // SunPositionMath returns the rotation for a world whose +X points east. If the map's
    // +X points somewhere else, rotate the compass azimuth by the difference.
    const double Adjusted = AzimuthDeg - (double(WorldXAxisCompassBearingDeg) - 90.0);
    double Pitch = 0, Yaw = 0, Roll = 0;
    MikdashSun::LightRotationForSky(Adjusted, AltitudeDeg, Pitch, Yaw, Roll);
    return FRotator(float(Pitch), float(Yaw), float(Roll));
}

void AMikdashTimeOfDay::ApplyNow()
{
    RecomputeAstronomy();
    RecomputeBlend();
    ApplyToScene();
    OnTimeOfDayChanged.Broadcast(TimeOfDayHours, CachedSunAltitudeDeg);
}

void AMikdashTimeOfDay::ApplyToScene()
{
    const FMikdashSkyPreset& P = CachedBlended;
    if (bDriveSun) ApplySun(P);
    if (bDriveMoon) ApplyMoon(P);
    if (bDriveSkyLight) ApplySkyLight(P);
    if (bDriveSkyAtmosphere) ApplySkyAtmosphere(P);
    if (bDriveClouds) ApplyClouds(P);
    if (bDriveFog) ApplyFog(P);
    if (bDriveExposure) ApplyExposure(P);
}

void AMikdashTimeOfDay::ApplySun(const FMikdashSkyPreset& P)
{
    if (!SunLight)
    {
        return;
    }
    SunLight->SetActorRotation(RotationForSky(CachedSunAzimuthDeg, CachedSunAltitudeDeg));

    UDirectionalLightComponent* C = SunLight->FindComponentByClass<UDirectionalLightComponent>();
    if (!C)
    {
        return;
    }

    float Intensity = P.SunIntensityLux;
    if (bFadeSunBelowHorizon)
    {
        // Only used when the sun is NOT an atmosphere light, because then the renderer does
        // not apply transmittance and a sun below the horizon would light the ground.
        Intensity *= SmoothStep01((CachedSunAltitudeDeg + 1.5f) / 1.5f);
    }
    C->SetIntensity(Intensity);
    C->SetUseTemperature(true);
    C->SetTemperature(FMath::Clamp(P.SunTemperatureK, 1700.f, 12000.f));
    C->SetLightSourceAngle(FMath::Clamp(P.SunSourceAngleDeg, 0.f, 5.f));
    C->SetVolumetricScatteringIntensity(P.SunVolumetricScatteringIntensity);
}

void AMikdashTimeOfDay::ApplyMoon(const FMikdashSkyPreset& P)
{
    if (!MoonLight)
    {
        return;
    }
    MoonLight->SetActorRotation(RotationForSky(CachedMoonAzimuthDeg, CachedMoonAltitudeDeg));

    UDirectionalLightComponent* C = MoonLight->FindComponentByClass<UDirectionalLightComponent>();
    if (!C)
    {
        return;
    }

    // Moonlight scales with the lit fraction of the disc, and with a cubic-ish falloff
    // rather than linearly: a half moon gives roughly a tenth of full-moon illuminance in
    // reality, because the lit crescent is foreshortened and backscatter drops off.
    const float Illum = FMath::Clamp(CachedMoonIllumination, 0.f, 1.f);
    const float PhaseFalloff = Illum * Illum * (0.35f + 0.65f * Illum);
    // Fade out while the moon is on or below the horizon; the atmosphere transmittance does
    // most of this already, but the moon is dim enough that a residual glow is visible.
    const float HorizonFade = SmoothStep01((CachedMoonAltitudeDeg + 1.f) / 3.f);
    const float Intensity = P.MoonIntensityLux * PhaseFalloff * HorizonFade;

    C->SetIntensity(Intensity);
    C->SetUseTemperature(true);
    C->SetTemperature(FMath::Clamp(P.MoonTemperatureK, 4000.f, 15000.f));
    // The atmosphere draws the moon as a round disc. It cannot show a crescent; a mesh moon
    // driven by GetMoonBrightLimbAngleDegrees() is the way to get the terminator. The disc
    // is dimmed with the phase so at least it does not read as full every night.
    C->SetAtmosphereSunDiskColorScale(FLinearColor(Illum, Illum, Illum, 1.f));
}

void AMikdashTimeOfDay::ApplySkyLight(const FMikdashSkyPreset& P)
{
    if (!SkyLight)
    {
        return;
    }
    USkyLightComponent* C = SkyLight->FindComponentByClass<USkyLightComponent>();
    if (!C)
    {
        return;
    }
    C->SetIntensity(P.SkyLightIntensity);

    // bLowerHemisphereIsBlack, SourceType and Cubemap are deliberately never written: the
    // reviewed scene runs SLS_CAPTURED_SCENE with the lower hemisphere NOT black, and that
    // is the tune the 2026-09-08 fog pass established.

    if (C->bRealTimeCapture)
    {
        // Real-time capture follows the sun on its own; nothing more to do.
        return;
    }
    if (FMath::Abs(CachedSunAltitudeDeg - LastRecaptureSunAltitudeDeg) >= SkyLightRecaptureIntervalDeg)
    {
        LastRecaptureSunAltitudeDeg = CachedSunAltitudeDeg;
        C->RecaptureSky();
    }
}

void AMikdashTimeOfDay::ApplySkyAtmosphere(const FMikdashSkyPreset& P)
{
    if (!SkyAtmosphere)
    {
        return;
    }
    USkyAtmosphereComponent* C = SkyAtmosphere->FindComponentByClass<USkyAtmosphereComponent>();
    if (!C)
    {
        return;
    }
    C->SetAerialPespectiveViewDistanceScale(P.AerialPerspectiveViewDistanceScale);
    C->SetMieScatteringScale(P.MieScatteringScale);
    C->SetSkyLuminanceFactor(FLinearColor(P.SkyLuminanceFactor, P.SkyLuminanceFactor, P.SkyLuminanceFactor, 1.f));
}

void AMikdashTimeOfDay::ApplyClouds(const FMikdashSkyPreset& P)
{
    if (!VolumetricCloud)
    {
        return;
    }
    UVolumetricCloudComponent* C = VolumetricCloud->FindComponentByClass<UVolumetricCloudComponent>();
    if (!C)
    {
        return;
    }

    if (!CloudMaterialInstance)
    {
        UMaterialInterface* Base = C->GetMaterial();
        if (!Base)
        {
            return;
        }
        // A dynamic instance, not an edit of the asset: the map's cloud material instance
        // (MI_Cloud_Scattered, itself a copy of the protected MI_Cloud) is never written to
        // disk by this actor.
        CloudMaterialInstance = UMaterialInstanceDynamic::Create(Base, this);
        if (!CloudMaterialInstance)
        {
            return;
        }
        C->SetMaterial(CloudMaterialInstance);
    }

    CloudMaterialInstance->SetScalarParameterValue(CloudCoverageParameter, P.CloudCoverage);
    CloudMaterialInstance->SetScalarParameterValue(CloudDensityParameter, P.CloudDensity);

    // Wind: direction as a unit vector in R/G, speed in B, an accumulating phase in A so a
    // material that prefers an offset over a velocity can use it directly.
    const float WindRad = float(MikdashSun::Rad(WindDirectionDeg));
    CloudMaterialInstance->SetVectorParameterValue(
        CloudWindParameter, FLinearColor(FMath::Sin(WindRad), FMath::Cos(WindRad), WindSpeedKph / 100.f, CloudWindPhase));
}

void AMikdashTimeOfDay::ApplyFog(const FMikdashSkyPreset& P)
{
    if (!HeightFog)
    {
        return;
    }
    UExponentialHeightFogComponent* C = HeightFog->FindComponentByClass<UExponentialHeightFogComponent>();
    if (!C)
    {
        return;
    }

    // The authored tune is the default in every preset row; the clamp above already caps
    // density. Falloff, start distance and the volumetric switch come straight from the
    // preset, which ships 0.15 / 8000 / off everywhere.
    C->SetFogDensity(FMath::Clamp(P.FogDensity, 0.f, MaxFogDensity));
    C->SetFogHeightFalloff(P.FogHeightFalloff);
    C->SetStartDistance(P.FogStartDistance);
    C->SetFogMaxOpacity(P.FogMaxOpacity);
    C->SetVolumetricFog(bForbidVolumetricFog ? false : P.bVolumetricFog);
    C->SetSkyAtmosphereAmbientContributionColorScale(P.FogColorScale);
    C->SetDirectionalInscatteringColor(P.DirectionalInscatteringLuminance);
}

bool AMikdashTimeOfDay::UsesExtendedLuminanceRange() const
{
    static IConsoleVariable* Cvar =
        IConsoleManager::Get().FindConsoleVariable(TEXT("r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange"));
    return Cvar && Cvar->GetInt() != 0;
}

void AMikdashTimeOfDay::ApplyExposure(const FMikdashSkyPreset& P)
{
    if (!PostProcessVolume)
    {
        return;
    }
    FPostProcessSettings& S = PostProcessVolume->Settings;

    S.bOverride_AutoExposureBias = 1;
    S.AutoExposureBias = P.ExposureBiasEV;

    // With ExtendDefaultLuminanceRange OFF (this project's setting, confirmed in the
    // lighting receipts) the min/max brightness fields are raw scene luminance, so the
    // EV100 figures in the preset have to be written as 2^EV. With the cvar ON they are
    // EV100 directly. Getting this backwards is the classic "interiors went black" bug.
    const bool bExtended = UsesExtendedLuminanceRange();
    S.bOverride_AutoExposureMinBrightness = 1;
    S.bOverride_AutoExposureMaxBrightness = 1;
    S.AutoExposureMinBrightness = bExtended ? P.ExposureMinEV100 : FMath::Pow(2.f, P.ExposureMinEV100);
    S.AutoExposureMaxBrightness = bExtended ? P.ExposureMaxEV100 : FMath::Pow(2.f, P.ExposureMaxEV100);

    // Film curve, bloom, vignette, Lumen quality and the metering percentiles are NOT
    // written here. The 2026-09-08 fill-highlight pass tuned film_shoulder 0.30,
    // film_white_clip 0.02 and auto_exposure_high_percent 95; those stay exactly as
    // authored.
}

// ---------------------------------------------------------------------------
// Readouts
// ---------------------------------------------------------------------------

FText AMikdashTimeOfDay::GetMoonPhaseName() const
{
    const float F = CachedMoonPhaseFraction;
    if (F < 0.02f || F > 0.98f) return NSLOCTEXT("Mikdash", "MoonNew", "New moon");
    if (F < 0.23f) return NSLOCTEXT("Mikdash", "MoonWaxCres", "Waxing crescent");
    if (F < 0.27f) return NSLOCTEXT("Mikdash", "MoonFirstQ", "First quarter");
    if (F < 0.48f) return NSLOCTEXT("Mikdash", "MoonWaxGib", "Waxing gibbous");
    if (F < 0.52f) return NSLOCTEXT("Mikdash", "MoonFull", "Full moon");
    if (F < 0.73f) return NSLOCTEXT("Mikdash", "MoonWanGib", "Waning gibbous");
    if (F < 0.77f) return NSLOCTEXT("Mikdash", "MoonLastQ", "Last quarter");
    return NSLOCTEXT("Mikdash", "MoonWanCres", "Waning crescent");
}

FString AMikdashTimeOfDay::DescribeState() const
{
    return FString::Printf(
        TEXT("%04d-%02d-%02d %s UTC%+.0f | sun alt %.2f az %.2f | rise %s noon %s set %s | civil %s..%s | moon alt %.2f "
             "illum %.0f%% age %.1fd (%s) | fog %.5f | skylight %.2f | sun %.0f lx %.0f K | exposure bias %+.2f EV"),
        Year, Month, Day, *ClockString(TimeOfDayHours), CachedTimeZoneOffset, CachedSunAltitudeDeg, CachedSunAzimuthDeg,
        *ClockString(CachedSunriseHours), *ClockString(CachedSolarNoonHours), *ClockString(CachedSunsetHours),
        *ClockString(CachedCivilDawnHours), *ClockString(CachedCivilDuskHours), CachedMoonAltitudeDeg,
        CachedMoonIllumination * 100.f, CachedMoonAgeDays, *GetMoonPhaseName().ToString(), CachedBlended.FogDensity,
        CachedBlended.SkyLightIntensity, CachedBlended.SunIntensityLux, CachedBlended.SunTemperatureK,
        CachedBlended.ExposureBiasEV);
}
