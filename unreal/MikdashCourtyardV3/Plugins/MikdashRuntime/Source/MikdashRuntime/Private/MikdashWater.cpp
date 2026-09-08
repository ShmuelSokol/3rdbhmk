#include "MikdashWater.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace MW = MikdashWater;

namespace
{
/** MikdashWater::Stage -> the Blueprint-facing enum. Kept as an explicit switch rather
 *  than a cast so that adding a stage to the header forces a compile error here instead
 *  of quietly producing an out-of-range enum value in the details panel. */
EMikdashWaterStage ToBlueprintStage(MW::Stage S)
{
    switch (S)
    {
    case MW::Stage::Trickle: return EMikdashWaterStage::Trickle;
    case MW::Stage::Ankles:  return EMikdashWaterStage::Ankles;
    case MW::Stage::Knees:   return EMikdashWaterStage::Knees;
    case MW::Stage::Loins:   return EMikdashWaterStage::Loins;
    case MW::Stage::River:   return EMikdashWaterStage::River;
    }
    return EMikdashWaterStage::Trickle;
}
}

AMikdashWater::AMikdashWater()
{
    // Ticking is on, but PushDrive() is rate-limited by UpdateIntervalSeconds. A tick that
    // only accumulates a double is cheaper than the timer bookkeeping would be, and unlike
    // a timer it stays correct when the world is time-dilated for a demonstration.
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = true;

    USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("WaterRoot"));
    SetRootComponent(Root);
    Root->SetMobility(EComponentMobility::Static);

    Profile = MW::MakeStreamProfile();
}

void AMikdashWater::BeginPlay()
{
    Super::BeginPlay();

    // Rebuilt here rather than trusted from the constructor: MakeStreamProfile() reads the
    // header constants, and a hot-reloaded header must not leave a stale profile behind.
    Profile = MW::MakeStreamProfile();

    BindSurfaces();
    PushDrive(static_cast<double>(SampleDistanceAmot), 0.0);

    if (DemoCommand == nullptr)
    {
        DemoCommand = IConsoleManager::Get().RegisterConsoleCommand(
            TEXT("Mikdash.Water.Demo"),
            TEXT("Run the Yechezkel 47 demonstration: the stream swells through the four "
                 "measurements of a thousand amot, holding at each mark. "
                 "Mikdash.Water.Demo [0|1|loop] -- 0 stops it, loop repeats."),
            FConsoleCommandWithArgsDelegate::CreateWeakLambda(this, [this](const TArray<FString>& Args)
            {
                if (Args.Num() > 0 && (Args[0] == TEXT("0") || Args[0].Equals(TEXT("stop"), ESearchCase::IgnoreCase)))
                {
                    StopDemonstration();
                    return;
                }
                const bool bLoop = Args.Num() > 0 && Args[0].Equals(TEXT("loop"), ESearchCase::IgnoreCase);
                StartDemonstration(bLoop);
            }),
            ECVF_Default);
    }
}

void AMikdashWater::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    // A console object outlives the actor if it is not unregistered, and the next PIE
    // session then registers a second command with the same name over a dead delegate.
    if (DemoCommand != nullptr)
    {
        IConsoleManager::Get().UnregisterConsoleObject(DemoCommand);
        DemoCommand = nullptr;
    }
    DynamicMaterials.Reset();
    Super::EndPlay(EndPlayReason);
}

void AMikdashWater::BindSurfaces()
{
    DynamicMaterials.Reset();

    TArray<UStaticMeshComponent*> Surfaces;
    if (ExplicitSurfaces.Num() > 0)
    {
        for (const TObjectPtr<UStaticMeshComponent>& Component : ExplicitSurfaces)
        {
            if (Component)
            {
                Surfaces.Add(Component);
            }
        }
    }
    else if (UWorld* World = GetWorld())
    {
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            TArray<UStaticMeshComponent*> Found;
            It->GetComponents(Found);
            for (UStaticMeshComponent* Component : Found)
            {
                if (Component && Component->ComponentHasTag(StreamMeshTag))
                {
                    Surfaces.Add(Component);
                }
            }
        }
    }

    for (UStaticMeshComponent* Component : Surfaces)
    {
        const int32 SlotCount = Component->GetNumMaterials();
        for (int32 Slot = 0; Slot < SlotCount; ++Slot)
        {
            if (UMaterialInstanceDynamic* Dynamic = Component->CreateAndSetMaterialInstanceDynamic(Slot))
            {
                DynamicMaterials.Add(Dynamic);
            }
        }
    }
}

void AMikdashWater::StartDemonstration(bool bLoop)
{
    bDemoLoops = bLoop;
    bDemonstrating = true;
    DemoElapsed = 0.0;
    DemoProgress = 0.0f;
    SinceLastPush = UpdateIntervalSeconds;   // push on the very next tick, not up to 1/30 s later
}

void AMikdashWater::StopDemonstration()
{
    bDemonstrating = false;
    DemoElapsed = 0.0;
    DemoProgress = 0.0f;
    PushDrive(static_cast<double>(SampleDistanceAmot), 0.0);
}

void AMikdashWater::AddRipple(FVector WorldLocation, float AmplitudeCm)
{
    RippleCentre = WorldLocation;
    RippleAgeSeconds = 0.0;
    RippleShape.AmplitudeCm = FMath::Max(0.0f, AmplitudeCm);
}

float AMikdashWater::GetRippleElevationCm(FVector WorldLocation) const
{
    if (RippleAgeSeconds < 0.0)
    {
        return 0.0f;
    }
    const double Radius = FVector::Dist(WorldLocation, RippleCentre);
    const double Depth = FMath::Max(0.1f, LastDepthCm);
    return static_cast<float>(MW::RippleElevationCm(RippleShape, Radius, RippleAgeSeconds, Depth));
}

void AMikdashWater::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);

    ElapsedSeconds += DeltaSeconds;
    SinceLastPush += DeltaSeconds;
    if (RippleAgeSeconds >= 0.0)
    {
        RippleAgeSeconds += DeltaSeconds;
        // Past six decay constants the displacement is under a thousandth of the amplitude;
        // holding the ripple alive after that costs a Dist() per tick and shows nothing.
        if (RippleAgeSeconds > 6.0 * RippleShape.DecaySeconds)
        {
            RippleAgeSeconds = -1.0;
        }
    }

    double Distance = static_cast<double>(SampleDistanceAmot);
    double SurfaceRise = 0.0;
    if (bDemonstrating)
    {
        DemoElapsed += DeltaSeconds;
        MW::DemoSettings Settings;
        Settings.TravelSeconds = DemoTravelSeconds;
        Settings.HoldSeconds = DemoHoldSeconds;
        Settings.Loop = bDemoLoops;

        const MW::DemoState State = MW::EvaluateDemo(Settings, DemoElapsed);
        Distance = State.DistanceAmot;
        DemoProgress = static_cast<float>(State.Progress);
        // The swell is a presentation flourish on top of the profile's own deepening, not a
        // second depth model: it rises with progress and is capped well below the kerb so
        // the surface can never be driven out through the bank, which is fixed geometry.
        SurfaceRise = static_cast<double>(DemoMaxSurfaceRiseCm) * State.Progress;
        if (State.Finished && !bDemoLoops)
        {
            bDemonstrating = false;
        }
    }

    if (SinceLastPush + KINDA_SMALL_NUMBER < UpdateIntervalSeconds)
    {
        return;
    }
    SinceLastPush = 0.0;
    PushDrive(Distance, SurfaceRise);
}

void AMikdashWater::PushDrive(double DistanceAmot, double SurfaceRiseCm)
{
    const MW::SurfaceDrive Drive = MW::EvaluateSurface(
        Profile, DistanceAmot, static_cast<double>(BankSideSlope), static_cast<double>(BedSlope),
        static_cast<double>(ManningN), static_cast<double>(NormalTileSizeCm), ElapsedSeconds);

    LastDepthCm = static_cast<float>(Drive.DepthCm);
    LastFlowSpeedCmS = static_cast<float>(Drive.VelocityCmS);
    LastDischargeLitresS = static_cast<float>(MW::Cm3ToLitres(Drive.DischargeCm3S));
    CurrentStage = ToBlueprintStage(Drive.CurrentStage);

    const float RippleNow = (RippleAgeSeconds >= 0.0)
        ? static_cast<float>(MW::RippleElevationCm(RippleShape, 0.0, RippleAgeSeconds, FMath::Max(0.1f, LastDepthCm)))
        : 0.0f;

    for (const TObjectPtr<UMaterialInstanceDynamic>& Dynamic : DynamicMaterials)
    {
        if (!Dynamic)
        {
            continue;
        }
        Dynamic->SetScalarParameterValue(FName(MikdashWaterParameters::FlowSpeed), LastFlowSpeedCmS);
        Dynamic->SetScalarParameterValue(FName(MikdashWaterParameters::ScrollTiles), static_cast<float>(Drive.ScrollTiles));
        Dynamic->SetScalarParameterValue(FName(MikdashWaterParameters::Depth), LastDepthCm);
        Dynamic->SetScalarParameterValue(FName(MikdashWaterParameters::Opacity), static_cast<float>(Drive.Opacity));
        Dynamic->SetScalarParameterValue(FName(MikdashWaterParameters::Foam), static_cast<float>(Drive.Foam));
        Dynamic->SetScalarParameterValue(FName(MikdashWaterParameters::Froude), static_cast<float>(Drive.Froude));
        Dynamic->SetScalarParameterValue(FName(MikdashWaterParameters::SurfaceRise), static_cast<float>(SurfaceRiseCm));
        Dynamic->SetScalarParameterValue(FName(MikdashWaterParameters::Ripple), RippleNow);
        Dynamic->SetScalarParameterValue(FName(MikdashWaterParameters::StageIndex), static_cast<float>(static_cast<int32>(Drive.CurrentStage)));
        Dynamic->SetScalarParameterValue(FName(MikdashWaterParameters::DemoProgress), bDemonstrating ? DemoProgress : 0.0f);
    }
}
