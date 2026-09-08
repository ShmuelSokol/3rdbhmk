#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MikdashTimeOfDay.h"
#include "MikdashWeather.generated.h"

class UMaterialParameterCollection;

/** Jerusalem weather, kept to what the city actually gets. */
UENUM(BlueprintType)
enum class EMikdashWeather : uint8
{
    Clear UMETA(DisplayName = "Clear"),
    /** Summer default: dry, dusty, the Judean hills soft in the distance. */
    Hazy UMETA(DisplayName = "Hazy (summer default)"),
    LightCloud UMETA(DisplayName = "Light cloud"),
    /** November to March only. Wet stone, grey sky, low sun. Rare on purpose. */
    WinterRain UMETA(DisplayName = "Winter rain"),
    /** Sharav / khamsin: hot dust-laden easterly, yellow-brown sky, spring and autumn. */
    Khamsin UMETA(DisplayName = "Khamsin dust haze"),
    /** Jerusalem gets snow roughly one winter in three. This is the cheap version: a
     * white-out sky, a cold sun and a snow-cover value for materials; no particles. */
    LightSnow UMETA(DisplayName = "Light snow (cheap)")
};

/** One weather's look and its physical readouts. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashWeatherProfile
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
    FMikdashSkyModifier Sky;

    /** 0 dry .. 1 running wet. Read by surface materials through the parameter collection. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float Wetness = 0.f;

    /** 0 clean air .. 1 khamsin. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float DustAmount = 0.f;

    /** 0 none .. 1 settled cover. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float SnowAmount = 0.f;

    /** Prevailing wind for this weather. Compass degrees the wind blows FROM. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind")
    float WindFromDeg = 290.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind", meta = (ClampMin = "0.0"))
    float WindSpeedKph = 12.f;

    /** Peak gust above the mean, km/h. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind", meta = (ClampMin = "0.0"))
    float GustKph = 6.f;

    /** Months (1..12) in which this weather is plausible; empty means any month. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather")
    TArray<int32> AllowedMonths;

    /** Relative frequency used by PickSeasonalWeather. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Weather", meta = (ClampMin = "0.0"))
    float Frequency = 1.f;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FMikdashWeatherChanged, EMikdashWeather, NewWeather, EMikdashWeather, OldWeather);

/**
 * Modest, believable Jerusalem weather. Owns the weather state, the wind and the
 * surface readouts; DOES NOT write to any lighting actor itself. Every visual change goes
 * through AMikdashTimeOfDay::SetWeatherModifier so there is exactly one writer of the sky,
 * sun, fog, clouds and exposure, and Clear weather is the identity (the time-of-day table
 * unmodified).
 *
 * Other systems read the weather three ways:
 *   1. BlueprintPure getters (wetness, dust, snow, wind vector, wind speed).
 *   2. The OnWeatherChanged delegate.
 *   3. An optional UMaterialParameterCollection (WeatherParameters). If assigned, the
 *      scalar parameters named below are written every tick; a surface material that
 *      reads "Mikdash_Wetness" darkens and sharpens its roughness, "Mikdash_Snow" whitens.
 *      NO material in the project is modified by this actor; adopting the response is a
 *      material author's decision, made per material, and the reliefs are untouched.
 *
 * Wind: direction and speed with a slow two-frequency gust, exposed as a world-frame
 * vector (project frame: +X east, +Y south) and pushed to the cloud material through the
 * time-of-day actor so cloud drift follows the same wind everything else reads.
 */
UCLASS(Blueprintable, ClassGroup = "Mikdash", meta = (DisplayName = "Mikdash Weather"))
class MIKDASHRUNTIME_API AMikdashWeather : public AActor
{
    GENERATED_BODY()

public:
    AMikdashWeather();

    /** Weather at BeginPlay. Hazy is Jerusalem's summer default. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Mikdash|Weather")
    EMikdashWeather StartWeather = EMikdashWeather::Hazy;

    /** Ignore StartWeather and pick from the season of the time-of-day actor's date. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Weather")
    bool bPickSeasonalWeatherOnBeginPlay = false;

    /** Refuse out-of-season requests (rain in July) and fall back to Hazy. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Weather")
    bool bEnforceSeason = true;

    /** Seconds a weather change takes to blend. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Weather", meta = (ClampMin = "0.0"))
    float DefaultTransitionSeconds = 20.f;

    /** Six rows indexed by EMikdashWeather, filled in the constructor and editable. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Weather")
    TArray<FMikdashWeatherProfile> Profiles;

    /** Found by class on BeginPlay if empty. */
    UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Mikdash|Scene")
    TObjectPtr<AMikdashTimeOfDay> TimeOfDay = nullptr;

    /** Optional. Left empty, no material parameter is written anywhere. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Materials")
    TSoftObjectPtr<UMaterialParameterCollection> WeatherParameters;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Materials") FName WetnessParameter = FName("Mikdash_Wetness");
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Materials") FName DustParameter = FName("Mikdash_Dust");
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Materials") FName SnowParameter = FName("Mikdash_Snow");
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Materials") FName WindSpeedParameter = FName("Mikdash_WindSpeedKph");
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Materials") FName WindDirectionParameter = FName("Mikdash_WindFromDeg");

    /** Compass bearing of the world +X axis; 90 for this project (east). */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Mikdash|Wind")
    float WorldXAxisCompassBearingDeg = 90.f;

    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Weather")
    FMikdashWeatherChanged OnWeatherChanged;

    // -----------------------------------------------------------------------

    /** Blend to a weather over TransitionSeconds (negative = DefaultTransitionSeconds).
     * Returns the weather actually chosen, which differs when bEnforceSeason rejects it. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Weather")
    EMikdashWeather SetWeather(EMikdashWeather NewWeather, float TransitionSeconds = -1.f);

    UFUNCTION(BlueprintPure, Category = "Mikdash|Weather")
    EMikdashWeather GetWeather() const { return TargetWeather; }

    /** 0 while settled, 0..1 during a blend. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Weather")
    float GetTransitionAlpha() const { return TransitionAlpha; }

    /** Deterministic pick for a month: the same month always gives the same weather, so
     * a release capture is reproducible. Uses the profiles' AllowedMonths and Frequency. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Weather")
    EMikdashWeather PickSeasonalWeather(int32 MonthOfYear, int32 Seed = 0) const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Weather")
    bool IsWeatherInSeason(EMikdashWeather Weather, int32 MonthOfYear) const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Weather") float GetWetness() const { return CurrentWetness; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Weather") float GetDustAmount() const { return CurrentDust; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Weather") float GetSnowAmount() const { return CurrentSnow; }

    /** Compass bearing the wind blows FROM, with gusts folded in. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Wind") float GetWindFromDegrees() const { return CurrentWindFromDeg; }
    /** Mean plus gust, km/h. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Wind") float GetWindSpeedKph() const { return CurrentWindSpeedKph; }
    /** Unit vector in world space pointing the way the wind BLOWS TOWARD. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Wind") FVector GetWindDirectionWorld() const;
    /** Wind velocity in cm/s, world space, ready for cloth, flags and smoke. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Wind") FVector GetWindVelocityCmPerSec() const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Weather")
    FMikdashSkyModifier GetCurrentSkyModifier() const { return CurrentModifier; }

    UFUNCTION(BlueprintPure, Category = "Mikdash|Weather")
    FString DescribeState() const;

    // AActor
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;

protected:
    void BuildDefaultProfiles();
    const FMikdashWeatherProfile& Profile(EMikdashWeather Weather) const;
    void PushToScene();
    static FMikdashSkyModifier LerpModifier(const FMikdashSkyModifier& A, const FMikdashSkyModifier& B, float T);

    EMikdashWeather PreviousWeather = EMikdashWeather::Hazy;
    EMikdashWeather TargetWeather = EMikdashWeather::Hazy;
    float TransitionAlpha = 1.f;
    float TransitionDuration = 20.f;
    float GustTime = 0.f;

    UPROPERTY(Transient) FMikdashSkyModifier CurrentModifier;
    float CurrentWetness = 0.f;
    float CurrentDust = 0.f;
    float CurrentSnow = 0.f;
    float CurrentWindFromDeg = 290.f;
    float CurrentWindSpeedKph = 12.f;
};
