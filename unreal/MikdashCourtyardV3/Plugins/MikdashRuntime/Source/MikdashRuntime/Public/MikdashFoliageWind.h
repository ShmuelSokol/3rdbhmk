#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MikdashFoliageWind.generated.h"

class UMaterialParameterCollection;
class UMaterialParameterCollectionInstance;
class UWindDirectionalSourceComponent;

/**
 * Engine-free gust math, so the shape of the wind can be reasoned about (and tested) without
 * an Actor, a World or a tick.
 *
 * WHY GUSTS AND NOT A CONSTANT. A constant wind makes a hillside of olives look like a single
 * looping animation, because every plant leans by the same amount for ever and the eye reads
 * the loop immediately. Real wind on an exposed Judean slope arrives in gusts: a slow surge
 * and lull over tens of seconds, a gust front that rises fast and decays slowly over a few
 * seconds, and a fast rattle on top. That is three timescales, and it is the difference
 * between foliage that breathes and foliage that vibrates.
 *
 * The model is a sum of three sine octaves at deliberately incommensurate periods, so the
 * total never repeats on any timescale a player will sit through, sharpened by a power curve
 * so that gusts SPIKE and lulls are long - which is what a real gust distribution looks like,
 * and what a plain sine does not do.
 */
namespace MikdashWind
{
/** Periods in seconds. Chosen incommensurate (their ratios are not simple fractions) so the
 * sum has no audible or visible repeat; the least common multiple is hours long. */
constexpr float SurgePeriodSeconds = 41.3f;
constexpr float GustPeriodSeconds = 11.7f;
constexpr float RattlePeriodSeconds = 3.1f;

/** How hard the gust curve is sharpened. 1 is a plain sine; higher values make the wind sit
 * near its lull for most of the time and spike briefly, as real gusts do. */
constexpr float GustSharpness = 2.2f;

/** Reference speed that GetWindStrengthNormalised() calls 1.0: 15 m/s, a fresh-to-strong
 * breeze (Beaufort 7). Nothing clamps to it; it is a scale so other systems have a number
 * with an agreed meaning rather than raw cm/s. */
constexpr float ReferenceSpeedCmS = 1500.f;

/** Raw gust envelope at time T, in roughly [-0.35, 1.0]. Deterministic and continuous. */
inline float GustEnvelope(float TimeSeconds, float PhaseOffset)
{
	const float Tau = 6.28318530718f;
	const float Surge = FMath::Sin(Tau * (TimeSeconds / SurgePeriodSeconds + PhaseOffset));
	const float Gust = FMath::Sin(Tau * (TimeSeconds / GustPeriodSeconds + PhaseOffset * 1.7f));
	const float Rattle = FMath::Sin(Tau * (TimeSeconds / RattlePeriodSeconds + PhaseOffset * 3.3f));
	// Weighted so the long surge carries the shape and the rattle only textures it.
	const float Sum = 0.55f * Surge + 0.32f * Gust + 0.13f * Rattle;
	// Map -1..1 to 0..1, sharpen, then re-centre so the mean stays near a third rather than
	// near a half: a hillside is calm more often than it is gusting.
	const float Unit = FMath::Pow(FMath::Clamp(0.5f * (Sum + 1.f), 0.f, 1.f), GustSharpness);
	return Unit * 1.35f - 0.35f;
}

/** Instantaneous speed in cm/s for a base speed and a gustiness in [0, 1]. Never negative:
 * wind that reverses because a sine went below zero is a bug, not weather. */
inline float SpeedAt(float BaseSpeedCmS, float Gustiness, float TimeSeconds, float PhaseOffset)
{
	const float Envelope = GustEnvelope(TimeSeconds, PhaseOffset);
	return FMath::Max(0.f, BaseSpeedCmS * (1.f + FMath::Clamp(Gustiness, 0.f, 1.f) * Envelope));
}

/** Bearing wander in degrees. A gust does not arrive from exactly the mean direction; it
 * veers, and the veer is correlated with the gust, so this is driven by the same envelope on
 * a different phase. */
inline float BearingOffsetDegrees(float MaxVeerDegrees, float TimeSeconds, float PhaseOffset)
{
	return MaxVeerDegrees * GustEnvelope(TimeSeconds, PhaseOffset + 0.37f) * 0.75f;
}
}   // namespace MikdashWind

/** Broadcast when the gust envelope crosses the gust threshold upward. Foliage does not need
 * this - it reads the strength every frame - but dust, banners, awnings, birds and the
 * soundscape do, and an event is cheaper for them than polling. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FMikdashWindGust, float, PeakSpeedCmS, float, BearingDegrees);

/**
 * AMikdashFoliageWind - one wind for the whole scene, gusting, with a strength other systems
 * can read.
 *
 * WHAT IT OWNS. The authoritative wind state: a mean speed, a gustiness, a mean bearing, and
 * the instantaneous values derived from them each tick. It publishes that state three ways:
 *   1. Blueprint and C++ getters (GetWindSpeedCmS, GetWindStrengthNormalised, GetWindVectorCmS);
 *   2. a Material Parameter Collection, if one is assigned, so the foliage shaders read the
 *      same numbers the gameplay code does rather than running their own private sine;
 *   3. the engine's own UWindDirectionalSourceComponent, so anything already driven by engine
 *      wind - cloth, particle systems, the built-in foliage wind - moves with everything else.
 *
 * WHAT DRIVES IT. By default, a gentle breeze (see DefaultBaseSpeedCmS). A time-of-day or
 * weather system owns the real weather, so it calls SetWeatherWind() and this actor blends to
 * what it asked for over WeatherBlendSeconds. The setter is deliberately typed in plain floats
 * and declared here with NO reference to any weather class, so this actor compiles and runs on
 * its own and the weather system can be built, changed or removed without touching it.
 *
 * WHAT IT IS NOT. It is not a wind FIELD: there is one wind for the level, not a per-location
 * simulation. On a hillside where the interesting variation is in time rather than in space,
 * and where the foliage is instanced, that is the right trade; a per-instance wind would cost
 * more than it shows.
 */
UCLASS(Blueprintable, meta = (DisplayName = "Mikdash Foliage Wind"))
class MIKDASHRUNTIME_API AMikdashFoliageWind : public AActor
{
	GENERATED_BODY()

public:
	AMikdashFoliageWind();

	// -- authored defaults ---------------------------------------------------

	/** Mean wind speed with no weather system driving it. 220 cm/s is 2.2 m/s, the middle of
	 * Beaufort force 2, "light breeze: leaves rustle, a vane is moved by the wind" - which is
	 * exactly the reading wanted for a calm day on the Mount. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wind|Default", meta = (ClampMin = "0.0"))
	float DefaultBaseSpeedCmS = 220.f;

	/** How much of the mean speed the gusts add and take away, 0 constant to 1 violent.
	 * 0.45 gives a gentle breeze that visibly comes and goes without ever looking stormy. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wind|Default", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float DefaultGustiness = 0.45f;

	/** Mean bearing the wind blows TOWARD, in degrees, 0 = +X (east), 90 = +Y (south) in this
	 * project's frame. 125 is a wind out of the north-west blowing south-east, which is the
	 * prevailing summer wind over Jerusalem - the afternoon sea breeze off the Mediterranean.
	 * It is set as a default because it is prevailing, not because it is always so. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wind|Default", meta = (ClampMin = "0.0", ClampMax = "360.0"))
	float DefaultBearingDegrees = 125.f;

	/** How far a gust veers off the mean bearing. Real gusts veer; a wind that holds its
	 * direction to the degree while its speed swings reads as a machine. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wind|Default", meta = (ClampMin = "0.0", ClampMax = "90.0"))
	float MaxVeerDegrees = 14.f;

	/** Seconds to blend to a new weather-driven wind. A step change in wind is a visible pop
	 * across a whole hillside, so the setter is always ramped. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wind|Default", meta = (ClampMin = "0.0"))
	float WeatherBlendSeconds = 8.f;

	/** Envelope value above which OnGust fires. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wind|Default", meta = (ClampMin = "0.0", ClampMax = "1.0"))
	float GustEventThreshold = 0.62f;

	// -- publication ---------------------------------------------------------

	/** Optional. If set, WindSpeedParameter, WindStrengthParameter and WindVectorParameter are
	 * written into it every tick, so the foliage material reads the same wind the gameplay
	 * code does instead of running its own unsynchronised sine. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wind|Publication")
	TObjectPtr<UMaterialParameterCollection> ParameterCollection;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wind|Publication")
	FName WindSpeedParameter = TEXT("WindSpeedCmS");

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wind|Publication")
	FName WindStrengthParameter = TEXT("WindStrength");

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wind|Publication")
	FName WindVectorParameter = TEXT("WindVector");

	/** Drive the engine's own wind source too, so cloth, particles and any engine foliage wind
	 * agree with this actor rather than fighting it. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wind|Publication")
	bool bDriveEngineWindSource = true;

	/** Engine wind strength is a 0..1 scalar; this is the speed that maps to 1.0. */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Wind|Publication", meta = (ClampMin = "1.0"))
	float EngineWindFullScaleCmS = 1500.f;

	UPROPERTY(BlueprintAssignable, Category = "Wind")
	FMikdashWindGust OnGust;

	// -- the setter the weather system drives --------------------------------

	/**
	 * Set the mean wind. Called by the time-of-day / weather system, which owns the weather;
	 * this actor owns only the gusting. Plain floats and no weather type, so the two systems
	 * stay independent of each other at compile time.
	 *
	 * @param BaseSpeedCmS  mean speed in cm/s. Clamped at 0; 220 is a light breeze, 1500 a
	 *                      strong one.
	 * @param Gustiness     0 constant, 1 violent. Clamped.
	 * @param BearingDeg    direction the wind blows TOWARD, degrees, 0 = +X east, 90 = +Y south.
	 * @param bImmediate    skip the blend. Only for a teleport or a cut, never for weather that
	 *                      the player is watching change.
	 */
	UFUNCTION(BlueprintCallable, Category = "Wind")
	void SetWeatherWind(float BaseSpeedCmS, float Gustiness, float BearingDeg, bool bImmediate = false);

	/** Return to the authored gentle breeze. */
	UFUNCTION(BlueprintCallable, Category = "Wind")
	void ResetToDefaultBreeze(bool bImmediate = false);

	// -- what other systems read ---------------------------------------------

	/** Instantaneous speed in cm/s, gust included. */
	UFUNCTION(BlueprintPure, Category = "Wind")
	float GetWindSpeedCmS() const { return CurrentSpeedCmS; }

	/** Instantaneous speed as a fraction of MikdashWind::ReferenceSpeedCmS (15 m/s). This is
	 * the number to use when something needs "how windy is it" on an agreed scale. */
	UFUNCTION(BlueprintPure, Category = "Wind")
	float GetWindStrengthNormalised() const { return CurrentSpeedCmS / MikdashWind::ReferenceSpeedCmS; }

	/** Mean speed without the gust, i.e. what the weather asked for. */
	UFUNCTION(BlueprintPure, Category = "Wind")
	float GetMeanSpeedCmS() const { return BaseSpeedCmS; }

	/** Instantaneous bearing in degrees, veer included. */
	UFUNCTION(BlueprintPure, Category = "Wind")
	float GetWindBearingDegrees() const { return CurrentBearingDegrees; }

	/** Instantaneous horizontal wind as a world vector in cm/s. */
	UFUNCTION(BlueprintPure, Category = "Wind")
	FVector GetWindVectorCmS() const;

	/** The raw gust envelope, for anything that wants the shape rather than the speed. */
	UFUNCTION(BlueprintPure, Category = "Wind")
	float GetGustEnvelope() const { return CurrentEnvelope; }

	/** The single most recently spawned instance in this world, so a weather system can find
	 * the wind without a hard reference or a level-blueprint wire. Null if none exists. */
	UFUNCTION(BlueprintCallable, Category = "Wind", meta = (WorldContext = "WorldContextObject"))
	static AMikdashFoliageWind* Get(const UObject* WorldContextObject);

	virtual void PostInitializeComponents() override;
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
#if WITH_EDITOR
	virtual bool ShouldTickIfViewportsOnly() const override { return true; }
#endif

private:
	void Initialise();
	void Publish();

	/** Not Transient: it is a default subobject and has to serialise with the actor. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Wind", meta = (AllowPrivateAccess = "true"))
	TObjectPtr<UWindDirectionalSourceComponent> WindSource;

	/** Mean state, and where it is blending to. */
	float BaseSpeedCmS = 220.f;
	float Gustiness = 0.45f;
	float BearingDegrees = 125.f;
	float TargetSpeedCmS = 220.f;
	float TargetGustiness = 0.45f;
	float TargetBearingDegrees = 125.f;

	/** Instantaneous state. */
	float CurrentSpeedCmS = 220.f;
	float CurrentBearingDegrees = 125.f;
	float CurrentEnvelope = 0.f;

	float ElapsedSeconds = 0.f;
	/** Per-actor phase, so two wind actors in one level (a mistake, but a survivable one) do
	 * not gust in lockstep and read as one doubled wind. */
	float PhaseOffset = 0.f;
	bool bWasGusting = false;
	/** The actor ticks in an editor viewport as well as in play, and BeginPlay does not run
	 * there, so initialisation is done lazily on the first tick rather than only in BeginPlay. */
	bool bInitialised = false;
};
