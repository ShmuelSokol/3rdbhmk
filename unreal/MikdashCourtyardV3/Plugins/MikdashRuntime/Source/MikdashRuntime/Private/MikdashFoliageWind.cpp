#include "MikdashFoliageWind.h"

#include "Components/WindDirectionalSourceComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"

AMikdashFoliageWind::AMikdashFoliageWind()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = true;
	// The wind must keep gusting while the game is paused for a menu or a photo, or the world
	// freezes in a way that reads as a bug rather than as a pause.
	PrimaryActorTick.bTickEvenWhenPaused = true;
	SetActorTickInterval(0.f);

	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	WindSource = CreateDefaultSubobject<UWindDirectionalSourceComponent>(TEXT("WindSource"));
	WindSource->SetupAttachment(Root);
	WindSource->Strength = 0.15f;
	WindSource->Speed = 2.2f;
	WindSource->MinGustAmount = 0.1f;
	WindSource->MaxGustAmount = 0.3f;
}

void AMikdashFoliageWind::BeginPlay()
{
	Super::BeginPlay();
	// A stable per-actor phase from the actor's own name, so a reload gusts the same way and
	// two instances never gust in lockstep.
	PhaseOffset = static_cast<float>(GetTypeHash(GetFName()) % 1000u) / 1000.f;
	ResetToDefaultBreeze(/*bImmediate=*/true);
}

void AMikdashFoliageWind::SetWeatherWind(float InBaseSpeedCmS, float InGustiness, float BearingDeg, bool bImmediate)
{
	TargetSpeedCmS = FMath::Max(0.f, InBaseSpeedCmS);
	TargetGustiness = FMath::Clamp(InGustiness, 0.f, 1.f);
	// Unwind the bearing to the nearest equivalent angle so a change from 350 to 10 degrees
	// blends 20 degrees the short way instead of 340 degrees the wrong way round.
	const float Wrapped = FMath::Fmod(FMath::Fmod(BearingDeg, 360.f) + 360.f, 360.f);
	float Delta = Wrapped - FMath::Fmod(FMath::Fmod(BearingDegrees, 360.f) + 360.f, 360.f);
	if (Delta > 180.f)
	{
		Delta -= 360.f;
	}
	else if (Delta < -180.f)
	{
		Delta += 360.f;
	}
	TargetBearingDegrees = BearingDegrees + Delta;

	if (bImmediate || WeatherBlendSeconds <= 0.f)
	{
		BaseSpeedCmS = TargetSpeedCmS;
		Gustiness = TargetGustiness;
		BearingDegrees = TargetBearingDegrees;
		Publish();
	}
}

void AMikdashFoliageWind::ResetToDefaultBreeze(bool bImmediate)
{
	SetWeatherWind(DefaultBaseSpeedCmS, DefaultGustiness, DefaultBearingDegrees, bImmediate);
}

void AMikdashFoliageWind::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (DeltaSeconds <= 0.f)
	{
		return;
	}
	ElapsedSeconds += DeltaSeconds;

	// Blend the mean toward whatever the weather last asked for. Exponential rather than
	// linear so there is no corner at the end of the ramp.
	if (WeatherBlendSeconds > 0.f)
	{
		const float Alpha = 1.f - FMath::Exp(-DeltaSeconds / FMath::Max(0.01f, WeatherBlendSeconds));
		BaseSpeedCmS = FMath::Lerp(BaseSpeedCmS, TargetSpeedCmS, Alpha);
		Gustiness = FMath::Lerp(Gustiness, TargetGustiness, Alpha);
		BearingDegrees = FMath::Lerp(BearingDegrees, TargetBearingDegrees, Alpha);
	}

	CurrentEnvelope = MikdashWind::GustEnvelope(ElapsedSeconds, PhaseOffset);
	CurrentSpeedCmS = MikdashWind::SpeedAt(BaseSpeedCmS, Gustiness, ElapsedSeconds, PhaseOffset);
	CurrentBearingDegrees = BearingDegrees
		+ MikdashWind::BearingOffsetDegrees(MaxVeerDegrees, ElapsedSeconds, PhaseOffset);

	const bool bGusting = CurrentEnvelope >= GustEventThreshold;
	if (bGusting && !bWasGusting)
	{
		OnGust.Broadcast(CurrentSpeedCmS, CurrentBearingDegrees);
	}
	bWasGusting = bGusting;

	Publish();
}

FVector AMikdashFoliageWind::GetWindVectorCmS() const
{
	const float Radians = FMath::DegreesToRadians(CurrentBearingDegrees);
	return FVector(FMath::Cos(Radians) * CurrentSpeedCmS, FMath::Sin(Radians) * CurrentSpeedCmS, 0.f);
}

void AMikdashFoliageWind::Publish()
{
	const FVector Wind = GetWindVectorCmS();

	if (ParameterCollection)
	{
		if (UWorld* World = GetWorld())
		{
			if (UMaterialParameterCollectionInstance* Instance = World->GetParameterCollectionInstance(ParameterCollection))
			{
				Instance->SetScalarParameterValue(WindSpeedParameter, CurrentSpeedCmS);
				Instance->SetScalarParameterValue(WindStrengthParameter, GetWindStrengthNormalised());
				// W carries the envelope, so a material can phase-shift its own detail motion
				// with the same gust rather than inventing a second one.
				Instance->SetVectorParameterValue(
					WindVectorParameter,
					FLinearColor(static_cast<float>(Wind.X), static_cast<float>(Wind.Y), 0.f, CurrentEnvelope));
			}
		}
	}

	if (bDriveEngineWindSource && WindSource)
	{
		// The engine's wind source takes a 0..1 strength and points along its own +X, so the
		// bearing is applied as a yaw on the component rather than as a vector.
		WindSource->Strength = FMath::Clamp(CurrentSpeedCmS / FMath::Max(1.f, EngineWindFullScaleCmS), 0.f, 1.f);
		WindSource->Speed = CurrentSpeedCmS / 100.f;                    // engine speed is m/s
		WindSource->MinGustAmount = FMath::Clamp(Gustiness * 0.5f, 0.f, 1.f);
		WindSource->MaxGustAmount = FMath::Clamp(Gustiness, 0.f, 1.f);
		WindSource->SetWorldRotation(FRotator(0.f, CurrentBearingDegrees, 0.f));
		WindSource->MarkRenderStateDirty();
	}
}

AMikdashFoliageWind* AMikdashFoliageWind::Get(const UObject* WorldContextObject)
{
	if (!WorldContextObject)
	{
		return nullptr;
	}
	UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::ReturnNull) : nullptr;
	if (!World)
	{
		return nullptr;
	}
	for (TActorIterator<AMikdashFoliageWind> It(World); It; ++It)
	{
		if (IsValid(*It))
		{
			return *It;
		}
	}
	return nullptr;
}
