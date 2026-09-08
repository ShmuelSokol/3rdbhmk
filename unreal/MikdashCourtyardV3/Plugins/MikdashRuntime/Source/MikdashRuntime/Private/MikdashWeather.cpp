#include "MikdashWeather.h"

#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialParameterCollection.h"

namespace
{
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
/** Shortest-arc interpolation of a compass bearing. */
float LerpBearing(float A, float B, float T)
{
    const float Delta = FMath::UnwindDegrees(B - A);
    return FMath::UnwindDegrees(A + Delta * T);
}
const TCHAR* WeatherName(EMikdashWeather W)
{
    switch (W)
    {
    case EMikdashWeather::Clear: return TEXT("Clear");
    case EMikdashWeather::Hazy: return TEXT("Hazy");
    case EMikdashWeather::LightCloud: return TEXT("LightCloud");
    case EMikdashWeather::WinterRain: return TEXT("WinterRain");
    case EMikdashWeather::Khamsin: return TEXT("Khamsin");
    case EMikdashWeather::LightSnow: return TEXT("LightSnow");
    default: return TEXT("?");
    }
}
} // namespace

AMikdashWeather::AMikdashWeather()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = true;
    SetActorEnableCollision(false);
    BuildDefaultProfiles();
}

// ---------------------------------------------------------------------------
// Profiles
// ---------------------------------------------------------------------------

void AMikdashWeather::BuildDefaultProfiles()
{
    Profiles.Reset();
    Profiles.SetNum(int32(EMikdashWeather::LightSnow) + 1);

    {
        // Clear: the identity. Whatever the time-of-day table says is what you get.
        FMikdashWeatherProfile& W = Profiles[int32(EMikdashWeather::Clear)];
        W.Sky = FMikdashSkyModifier();
        W.Wetness = 0.f;
        W.DustAmount = 0.f;
        W.SnowAmount = 0.f;
        W.WindFromDeg = 290.f; // the afternoon westerly off the Mediterranean
        W.WindSpeedKph = 10.f;
        W.GustKph = 5.f;
        W.Frequency = 0.9f;
    }
    {
        // Hazy: the summer default. Dry dust in the air, distance softened, sun a touch
        // warmer, slightly more fog. Fog density x1.35 takes the authored 0.0015 to about
        // 0.0020, still well under the actor's 0.006 ceiling.
        FMikdashWeatherProfile& W = Profiles[int32(EMikdashWeather::Hazy)];
        W.Sky.SunIntensityScale = 0.92f;
        W.Sky.SunTemperatureOffsetK = -250.f;
        W.Sky.SunSourceAngleAddDeg = 0.25f;
        W.Sky.SkyLightIntensityScale = 1.05f;
        W.Sky.FogDensityScale = 1.35f;
        W.Sky.FogColorTint = FLinearColor(1.0f, 0.97f, 0.90f, 1.f);
        W.Sky.CloudCoverageAdd = -0.10f;
        W.Sky.CloudDensityScale = 0.8f;
        W.Sky.AerialPerspectiveScale = 1.25f;
        W.Sky.MieScatteringScale = 1.6f;
        W.Wetness = 0.f;
        W.DustAmount = 0.25f;
        W.WindFromDeg = 290.f;
        W.WindSpeedKph = 12.f;
        W.GustKph = 6.f;
        W.AllowedMonths = {4, 5, 6, 7, 8, 9, 10};
        W.Frequency = 2.0f;
    }
    {
        FMikdashWeatherProfile& W = Profiles[int32(EMikdashWeather::LightCloud)];
        W.Sky.SunIntensityScale = 0.85f;
        W.Sky.SkyLightIntensityScale = 1.15f;
        W.Sky.FogDensityScale = 1.1f;
        W.Sky.CloudCoverageAdd = 0.30f;
        W.Sky.CloudDensityScale = 1.2f;
        W.Sky.ExposureBiasAddEV = 0.1f;
        W.Wetness = 0.f;
        W.DustAmount = 0.05f;
        W.WindFromDeg = 275.f;
        W.WindSpeedKph = 16.f;
        W.GustKph = 9.f;
        W.Frequency = 1.0f;
    }
    {
        // Winter rain, November to March. Grey sky, sun mostly gone, cool light, wet stone
        // through the Wetness readout. Fog scale x1.8 keeps within the ceiling.
        FMikdashWeatherProfile& W = Profiles[int32(EMikdashWeather::WinterRain)];
        W.Sky.SunIntensityScale = 0.30f;
        W.Sky.SunTemperatureOffsetK = +600.f;
        W.Sky.SunSourceAngleAddDeg = 2.5f; // soft, shadowless
        W.Sky.SkyLightIntensityScale = 1.35f;
        W.Sky.FogDensityScale = 1.8f;
        W.Sky.FogColorTint = FLinearColor(0.82f, 0.86f, 0.92f, 1.f);
        W.Sky.CloudCoverageAdd = 0.60f;
        W.Sky.CloudDensityScale = 2.0f;
        W.Sky.ExposureBiasAddEV = 0.4f;
        W.Sky.AerialPerspectiveScale = 1.3f;
        W.Sky.MieScatteringScale = 1.2f;
        W.Wetness = 1.0f;
        W.DustAmount = 0.f;
        W.WindFromDeg = 250.f; // rain comes on the south-westerly
        W.WindSpeedKph = 24.f;
        W.GustKph = 14.f;
        W.AllowedMonths = {11, 12, 1, 2, 3};
        W.Frequency = 0.6f;
    }
    {
        // Khamsin (sharav): hot dry easterly out of the desert, sky yellow-brown, sun a
        // pale disc, contrast gone. Fog x2.6 on 0.0015 is 0.0039, the highest any weather
        // reaches and still under the 0.006 ceiling.
        FMikdashWeatherProfile& W = Profiles[int32(EMikdashWeather::Khamsin)];
        W.Sky.SunIntensityScale = 0.65f;
        W.Sky.SunTemperatureOffsetK = -1400.f;
        W.Sky.SunSourceAngleAddDeg = 1.5f;
        W.Sky.SkyLightIntensityScale = 1.1f;
        W.Sky.FogDensityScale = 2.6f;
        W.Sky.FogColorTint = FLinearColor(1.0f, 0.86f, 0.62f, 1.f);
        W.Sky.CloudCoverageAdd = -0.25f;
        W.Sky.CloudDensityScale = 0.5f;
        W.Sky.ExposureBiasAddEV = 0.2f;
        W.Sky.AerialPerspectiveScale = 1.8f;
        W.Sky.MieScatteringScale = 3.0f;
        W.Wetness = 0.f;
        W.DustAmount = 1.0f;
        W.WindFromDeg = 100.f; // easterly, off the Judean desert
        W.WindSpeedKph = 28.f;
        W.GustKph = 16.f;
        W.AllowedMonths = {3, 4, 5, 9, 10, 11};
        W.Frequency = 0.35f;
    }
    {
        // Light snow, the cheap version: cold white sky, dim sun, snow-cover readout for
        // materials, no falling particles.
        FMikdashWeatherProfile& W = Profiles[int32(EMikdashWeather::LightSnow)];
        W.Sky.SunIntensityScale = 0.35f;
        W.Sky.SunTemperatureOffsetK = +1200.f;
        W.Sky.SunSourceAngleAddDeg = 2.5f;
        W.Sky.SkyLightIntensityScale = 1.6f;
        W.Sky.FogDensityScale = 1.6f;
        W.Sky.FogColorTint = FLinearColor(0.90f, 0.93f, 1.0f, 1.f);
        W.Sky.CloudCoverageAdd = 0.65f;
        W.Sky.CloudDensityScale = 1.8f;
        W.Sky.ExposureBiasAddEV = 0.3f;
        W.Wetness = 0.35f;
        W.DustAmount = 0.f;
        W.SnowAmount = 0.8f;
        W.WindFromDeg = 300.f;
        W.WindSpeedKph = 14.f;
        W.GustKph = 8.f;
        W.AllowedMonths = {12, 1, 2};
        W.Frequency = 0.08f;
    }
}

const FMikdashWeatherProfile& AMikdashWeather::Profile(EMikdashWeather Weather) const
{
    const int32 Index = int32(Weather);
    if (Index >= 0 && Index < Profiles.Num())
    {
        return Profiles[Index];
    }
    static const FMikdashWeatherProfile Empty;
    return Empty;
}

FMikdashSkyModifier AMikdashWeather::LerpModifier(const FMikdashSkyModifier& A, const FMikdashSkyModifier& B, float T)
{
    FMikdashSkyModifier R;
    R.SunIntensityScale = FMath::Lerp(A.SunIntensityScale, B.SunIntensityScale, T);
    R.SunTemperatureOffsetK = FMath::Lerp(A.SunTemperatureOffsetK, B.SunTemperatureOffsetK, T);
    R.SunSourceAngleAddDeg = FMath::Lerp(A.SunSourceAngleAddDeg, B.SunSourceAngleAddDeg, T);
    R.SkyLightIntensityScale = FMath::Lerp(A.SkyLightIntensityScale, B.SkyLightIntensityScale, T);
    R.FogDensityScale = FMath::Lerp(A.FogDensityScale, B.FogDensityScale, T);
    R.FogColorTint = LerpColour(A.FogColorTint, B.FogColorTint, T);
    R.CloudCoverageAdd = FMath::Lerp(A.CloudCoverageAdd, B.CloudCoverageAdd, T);
    R.CloudDensityScale = FMath::Lerp(A.CloudDensityScale, B.CloudDensityScale, T);
    R.ExposureBiasAddEV = FMath::Lerp(A.ExposureBiasAddEV, B.ExposureBiasAddEV, T);
    R.AerialPerspectiveScale = FMath::Lerp(A.AerialPerspectiveScale, B.AerialPerspectiveScale, T);
    R.MieScatteringScale = FMath::Lerp(A.MieScatteringScale, B.MieScatteringScale, T);
    return R;
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

void AMikdashWeather::BeginPlay()
{
    Super::BeginPlay();
    if (Profiles.Num() <= int32(EMikdashWeather::LightSnow))
    {
        BuildDefaultProfiles();
    }

    if (!TimeOfDay)
    {
        if (UWorld* World = GetWorld())
        {
            for (TActorIterator<AMikdashTimeOfDay> It(World); It; ++It)
            {
                TimeOfDay = *It;
                break;
            }
        }
    }

    EMikdashWeather Initial = StartWeather;
    if (bPickSeasonalWeatherOnBeginPlay && TimeOfDay)
    {
        int32 Y, M, D;
        TimeOfDay->GetDate(Y, M, D);
        Initial = PickSeasonalWeather(M, D);
    }
    PreviousWeather = Initial;
    TargetWeather = Initial;
    TransitionAlpha = 1.f;
    SetWeather(Initial, 0.f);
}

void AMikdashWeather::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    GustTime += DeltaSeconds;
    if (TransitionAlpha < 1.f)
    {
        TransitionAlpha = TransitionDuration > 0.f ? FMath::Min(1.f, TransitionAlpha + DeltaSeconds / TransitionDuration) : 1.f;
    }
    PushToScene();
}

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

bool AMikdashWeather::IsWeatherInSeason(EMikdashWeather Weather, int32 MonthOfYear) const
{
    const FMikdashWeatherProfile& P = Profile(Weather);
    return P.AllowedMonths.Num() == 0 || P.AllowedMonths.Contains(MonthOfYear);
}

EMikdashWeather AMikdashWeather::SetWeather(EMikdashWeather NewWeather, float TransitionSeconds)
{
    EMikdashWeather Chosen = NewWeather;
    if (bEnforceSeason && TimeOfDay)
    {
        int32 Y, M, D;
        TimeOfDay->GetDate(Y, M, D);
        if (!IsWeatherInSeason(Chosen, M))
        {
            // Out of season: fall back to the month's plain default, not silently to Clear.
            Chosen = IsWeatherInSeason(EMikdashWeather::Hazy, M) ? EMikdashWeather::Hazy : EMikdashWeather::Clear;
        }
    }

    const EMikdashWeather Old = TargetWeather;
    PreviousWeather = TargetWeather;
    TargetWeather = Chosen;
    TransitionDuration = TransitionSeconds < 0.f ? DefaultTransitionSeconds : TransitionSeconds;
    TransitionAlpha = TransitionDuration <= 0.f ? 1.f : 0.f;
    PushToScene();
    if (Old != Chosen)
    {
        OnWeatherChanged.Broadcast(Chosen, Old);
    }
    return Chosen;
}

EMikdashWeather AMikdashWeather::PickSeasonalWeather(int32 MonthOfYear, int32 Seed) const
{
    // Deterministic: a hash of month and seed, so a given date always renders the same.
    float Total = 0.f;
    for (int32 I = 0; I < Profiles.Num(); ++I)
    {
        if (IsWeatherInSeason(EMikdashWeather(I), MonthOfYear))
        {
            Total += FMath::Max(0.f, Profiles[I].Frequency);
        }
    }
    if (Total <= 0.f)
    {
        return EMikdashWeather::Clear;
    }
    const uint32 Hash = uint32(MonthOfYear * 7919 + Seed * 104729 + 12345);
    float Pick = (float(Hash % 10007) / 10007.f) * Total;
    for (int32 I = 0; I < Profiles.Num(); ++I)
    {
        if (!IsWeatherInSeason(EMikdashWeather(I), MonthOfYear))
        {
            continue;
        }
        Pick -= FMath::Max(0.f, Profiles[I].Frequency);
        if (Pick <= 0.f)
        {
            return EMikdashWeather(I);
        }
    }
    return EMikdashWeather::Hazy;
}

FVector AMikdashWeather::GetWindDirectionWorld() const
{
    // Wind blows TOWARD (from + 180). Compass to world: the world +X axis has bearing
    // WorldXAxisCompassBearingDeg (90 = east) and the frame is left-handed with +Y south,
    // so bearing B maps to (sin(B - Bx + 90), -cos(B - Bx + 90)) ... written out plainly:
    const float TowardDeg = CurrentWindFromDeg + 180.f;
    const float Rel = FMath::DegreesToRadians(TowardDeg - WorldXAxisCompassBearingDeg);
    // Rel = 0 means along +X (east). +90 (south) must map to +Y.
    return FVector(FMath::Cos(Rel), FMath::Sin(Rel), 0.f);
}

FVector AMikdashWeather::GetWindVelocityCmPerSec() const
{
    return GetWindDirectionWorld() * (CurrentWindSpeedKph * (100000.f / 3600.f));
}

FString AMikdashWeather::DescribeState() const
{
    return FString::Printf(TEXT("weather %s (from %s, blend %.2f) | wet %.2f dust %.2f snow %.2f | wind from %.0f deg at %.1f km/h "
                                "| fog x%.2f sun x%.2f cloud %+.2f"),
                           WeatherName(TargetWeather), WeatherName(PreviousWeather), TransitionAlpha, CurrentWetness,
                           CurrentDust, CurrentSnow, CurrentWindFromDeg, CurrentWindSpeedKph, CurrentModifier.FogDensityScale,
                           CurrentModifier.SunIntensityScale, CurrentModifier.CloudCoverageAdd);
}

// ---------------------------------------------------------------------------

void AMikdashWeather::PushToScene()
{
    const FMikdashWeatherProfile& From = Profile(PreviousWeather);
    const FMikdashWeatherProfile& To = Profile(TargetWeather);
    const float T = SmoothStep01(TransitionAlpha);

    CurrentModifier = LerpModifier(From.Sky, To.Sky, T);
    CurrentWetness = FMath::Lerp(From.Wetness, To.Wetness, T);
    CurrentDust = FMath::Lerp(From.DustAmount, To.DustAmount, T);
    CurrentSnow = FMath::Lerp(From.SnowAmount, To.SnowAmount, T);

    // Wind with a slow two-frequency gust so flags and clouds do not move like clockwork.
    const float MeanSpeed = FMath::Lerp(From.WindSpeedKph, To.WindSpeedKph, T);
    const float Gust = FMath::Lerp(From.GustKph, To.GustKph, T);
    const float GustWave = 0.5f + 0.5f * (0.6f * FMath::Sin(GustTime * 0.21f) + 0.4f * FMath::Sin(GustTime * 0.053f + 1.3f));
    CurrentWindSpeedKph = FMath::Max(0.f, MeanSpeed + Gust * (GustWave - 0.35f));
    const float MeanFrom = LerpBearing(From.WindFromDeg, To.WindFromDeg, T);
    const float Veer = 8.f * FMath::Sin(GustTime * 0.087f + 0.7f);
    CurrentWindFromDeg = FMath::UnwindDegrees(MeanFrom + Veer);
    if (CurrentWindFromDeg < 0.f) CurrentWindFromDeg += 360.f;

    if (TimeOfDay)
    {
        // Clouds drift the way the wind blows TOWARD.
        TimeOfDay->SetWind(CurrentWindFromDeg + 180.f, CurrentWindSpeedKph);
        TimeOfDay->SetWeatherModifier(CurrentModifier);
    }

    if (UMaterialParameterCollection* Collection = WeatherParameters.Get())
    {
        if (UWorld* World = GetWorld())
        {
            UKismetMaterialLibrary::SetScalarParameterValue(World, Collection, WetnessParameter, CurrentWetness);
            UKismetMaterialLibrary::SetScalarParameterValue(World, Collection, DustParameter, CurrentDust);
            UKismetMaterialLibrary::SetScalarParameterValue(World, Collection, SnowParameter, CurrentSnow);
            UKismetMaterialLibrary::SetScalarParameterValue(World, Collection, WindSpeedParameter, CurrentWindSpeedKph);
            UKismetMaterialLibrary::SetScalarParameterValue(World, Collection, WindDirectionParameter, CurrentWindFromDeg);
        }
    }
}
