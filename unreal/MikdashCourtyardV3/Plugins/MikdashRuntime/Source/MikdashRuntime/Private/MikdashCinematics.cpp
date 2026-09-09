#include "MikdashCinematics.h"

#include "CameraPathMath.h"
#include "MikdashFrontEnd.h"
#include "MikdashSceneUnits.h"

#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "LevelSequence.h"
#include "LevelSequenceActor.h"
#include "LevelSequencePlayer.h"
#include "MovieSceneSequencePlaybackSettings.h"
#include "UObject/UObjectGlobals.h"

DEFINE_LOG_CATEGORY_STATIC(LogMikdashCinematics, Log, All);

namespace
{
using MikdashCamera::Orientation;
using MikdashCamera::SplinePath;
using MikdashCamera::Vec3;

Vec3 ToMath(const FVector& V) { return Vec3{V.X, V.Y, V.Z}; }
FVector ToVec(const Vec3& V) { return FVector(V.X, V.Y, V.Z); }
FRotator ToRotator(const Orientation& O) { return FRotator(O.Pitch, O.Yaw, O.Roll); }

/** Resolve immutable legacy inputs into a local world snapshot before playback. */
bool BuildIntroForWorld(const UWorld* World, MikdashSceneUnits::Frame& Frame,
                       SplinePath& Path, TArray<FVector>& AimPoints, FString& Error)
{
    MikdashSceneUnits::Frame CandidateFrame;
    if (!AMikdashSceneUnits::Resolve(World, CandidateFrame, Error)) return false;
    MikdashSceneUnits::IntroPoints Controls;
    MikdashSceneUnits::AimPoints Targets;
    if (!MikdashSceneUnits::TryIntroPoints(CandidateFrame, Controls)
        || !MikdashSceneUnits::TryAimPoints(CandidateFrame, Targets))
    {
        Error = TEXT("Invalid scene-unit intro conversion."); return false;
    }
    std::vector<Vec3> Points;
    for (const auto& P : Controls) Points.push_back(Vec3{P.X,P.Y,P.Z});
    SplinePath CandidatePath;
    if (!CandidatePath.Build(Points, 0.5, 96))
    { Error = TEXT("The scene-unit intro control points did not build a spline."); return false; }
    TArray<FVector> CandidateAim;
    for (const auto& P : Targets) CandidateAim.Add(FVector(P.X,P.Y,P.Z));
    Frame = CandidateFrame;
    Path = MoveTemp(CandidatePath);
    AimPoints = MoveTemp(CandidateAim);
    return true;
}

/** Where the camera looks at this fraction of the shot, before damping. */
FVector AimAt(float Alpha, const TArray<FVector>& Points)
{
    const TArray<float> Alphas = UMikdashCinematics::IntroAimAlphas();
    if (Points.Num() == 0)
    {
        return FVector::ZeroVector;
    }
    if (Points.Num() == 1 || Alpha <= Alphas[0])
    {
        return Points[0];
    }
    for (int32 I = 1; I < Points.Num(); ++I)
    {
        if (Alpha <= Alphas[I])
        {
            const float Span = Alphas[I] - Alphas[I - 1];
            const float T = Span > KINDA_SMALL_NUMBER ? (Alpha - Alphas[I - 1]) / Span : 0.0f;
            // Smoothstepped, so the aim never changes direction with a corner in it.
            const float S = static_cast<float>(MikdashCamera::SmootherStep(T));
            return FMath::Lerp(Points[I - 1], Points[I], S);
        }
    }
    return Points.Last();
}
} // namespace

// =====================================================================================
// the path
// =====================================================================================

TArray<FVector> UMikdashCinematics::IntroControlPoints()
{
    // Authored east approach: Yechezkel 43:1-4 direction; choreography is authored.
    // The same canonical list feeds BuildIntroForWorld; do not maintain a second path.
    TArray<FVector> Result;
    for (const auto& P : MikdashSceneUnits::LegacyIntroPoints()) Result.Add(FVector(P.X,P.Y,P.Z));
    return Result;
}

TArray<FVector> UMikdashCinematics::IntroAimPoints()
{
    TArray<FVector> Result;
    for (const auto& P : MikdashSceneUnits::LegacyAimPoints()) Result.Add(FVector(P.X,P.Y,P.Z));
    return Result;
}

TArray<float> UMikdashCinematics::IntroAimAlphas()
{
    return {0.00f, 0.17f, 0.45f, 0.78f, 0.93f, 1.00f};
}

float UMikdashCinematics::GetDurationSeconds() const
{
    // Clamped to the brief. A shot shorter than 40 seconds cannot establish the approach and
    // one longer than 70 outstays its welcome before the visitor has touched a key.
    return FMath::Clamp(IntroDurationSeconds, 40.0f, 70.0f);
}

// =====================================================================================
// lifetime
// =====================================================================================

void UMikdashCinematics::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    if (!bEnabled || !bPlayOnWalkthroughStart)
    {
        return;
    }
    // The front end owns the title screen and its own menu camera and puts the view back
    // on the pawn before it broadcasts. Binding here means the intro takes over cleanly
    // instead of fighting it for the view target.
    if (UGameInstance* Instance = GetGameInstance())
    {
        if (UMikdashFrontEnd* FrontEnd = Instance->GetSubsystem<UMikdashFrontEnd>())
        {
            FrontEnd->OnWalkthroughStarted.AddDynamic(this, &UMikdashCinematics::HandleWalkthroughStarted);
        }
        else
        {
            UE_LOG(LogMikdashCinematics, Log,
                   TEXT("No front end subsystem; the intro will only play when PlayIntro() is called."));
        }
    }
}

void UMikdashCinematics::Deinitialize()
{
    if (bPlaying)
    {
        SkipIntro();
    }
    if (TickHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
        TickHandle.Reset();
    }
    if (UGameInstance* Instance = GetGameInstance())
    {
        if (UMikdashFrontEnd* FrontEnd = Instance->GetSubsystem<UMikdashFrontEnd>())
        {
            FrontEnd->OnWalkthroughStarted.RemoveDynamic(this, &UMikdashCinematics::HandleWalkthroughStarted);
        }
    }
    Super::Deinitialize();
}

UMikdashCinematics* UMikdashCinematics::Get(const UObject* WorldContext)
{
    if (const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr)
    {
        if (UGameInstance* Instance = World->GetGameInstance())
        {
            return Instance->GetSubsystem<UMikdashCinematics>();
        }
    }
    return nullptr;
}

APlayerController* UMikdashCinematics::GetOwningController() const
{
    const UGameInstance* Instance = GetGameInstance();
    return Instance ? Instance->GetFirstLocalPlayerController() : nullptr;
}

void UMikdashCinematics::HandleWalkthroughStarted()
{
    PlayIntro();
}

// =====================================================================================
// playback
// =====================================================================================

bool UMikdashCinematics::PlayIntro()
{
    LastRefusal.Reset();
    if (!bEnabled)
    {
        LastRefusal = TEXT("Cinematics are disabled in configuration.");
        return false;
    }
    if (bPlaying)
    {
        return true;
    }
    if (bOncePerSession && bPlayedThisSession)
    {
        LastRefusal = TEXT("The intro has already played this session.");
        return false;
    }
    APlayerController* Controller = GetOwningController();
    if (!Controller || !GetWorld())
    {
        LastRefusal = TEXT("No world or player controller.");
        return false;
    }
    if (!BuildIntroForWorld(GetWorld(), ActiveSceneFrame, ActiveIntroPath, ActiveIntroAimPoints, LastRefusal))
    {
        return false;
    }

    PreviousViewTarget = Controller->GetViewTarget();
    Elapsed = 0.0f;
    NativeStepGate.Reset();
    ActiveDuration = GetDurationSeconds();
    bAimInitialised = false;
    OrbitKeys.Reset();

    const bool bStarted = StartSequencePlayback(Controller) || StartNativePlayback(Controller);
    if (!bStarted)
    {
        LastRefusal = TEXT("Neither the authored sequence nor the native fallback could start.");
        return false;
    }

    bPlaying = true;
    bPlayedThisSession = true;
    Controller->SetCinematicMode(true, /*bHidePlayer*/ true, /*bAffectsHUD*/ true,
                                 /*bAffectsMovement*/ true, /*bAffectsTurning*/ true);
    if (!TickHandle.IsValid())
    {
        TickHandle = FTSTicker::GetCoreTicker().AddTicker(
            FTickerDelegate::CreateUObject(this, &UMikdashCinematics::Tick), 0.0f);
    }
    UE_LOG(LogMikdashCinematics, Log, TEXT("Intro playing over %.1f s by the %s route, path %.0f cm."),
           ActiveDuration, *PlaybackRoute, ActiveIntroPath.TotalLength());
    return true;
}

bool UMikdashCinematics::StartSequencePlayback(APlayerController* Controller)
{
    // Existing sequences contain legacy world-space keys. Until a sequence has
    // explicit matching coordinate metadata, candidate48 uses its converted native path.
    if (ActiveSceneFrame.CoordinateRevision != MikdashSceneUnits::Revision::Legacy50V1)
    {
        if (!IntroSequence.IsNull())
            UE_LOG(LogMikdashCinematics, Log, TEXT("Selected48 scene uses native intro; configured sequence has no selected48 coordinate receipt."));
        return false;
    }
    // No asset configured: the native fallback is the intended route, not a failure.
    if (IntroSequence.IsNull())
    {
        return false;
    }
    UWorld* World = GetWorld();
    if (!World)
    {
        return false;
    }
    ULevelSequence* Sequence = Cast<ULevelSequence>(IntroSequence.TryLoad());
    if (!Sequence)
    {
        UE_LOG(LogMikdashCinematics, Log,
               TEXT("Intro sequence %s is configured but not loadable; using the native path instead."),
               *IntroSequence.ToString());
        return false;
    }

    FMovieSceneSequencePlaybackSettings PlaybackSettings;
    PlaybackSettings.bAutoPlay = false;
    PlaybackSettings.bPauseAtEnd = true;
    // The camera cut track in the sequence owns the view for its whole length, which is
    // exactly what we want: no view target juggling of our own while it runs.
    PlaybackSettings.bDisableCameraCuts = false;

    ALevelSequenceActor* Actor = nullptr;
    ULevelSequencePlayer* Player = ULevelSequencePlayer::CreateLevelSequencePlayer(World, Sequence, PlaybackSettings, Actor);
    if (!Player || !Actor)
    {
        return false;
    }
    SequenceActor = Actor;
    Player->Play();
    PlaybackRoute = TEXT("sequence");
    (void)Controller;
    return true;
}

bool UMikdashCinematics::StartNativePlayback(APlayerController* Controller)
{
    UWorld* World = GetWorld();
    if (!World || !Controller)
    {
        return false;
    }
    const SplinePath& Path = ActiveIntroPath;
    const FVector Start = ToVec(Path.PointAtDistance(0.0));
    const Orientation Aim = MikdashCamera::LookAt(ToMath(Start), ToMath(AimAt(0.0f, ActiveIntroAimPoints)));

    FActorSpawnParameters Params;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    IntroCamera = World->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), Start, ToRotator(Aim), Params);
    if (!IntroCamera)
    {
        return false;
    }
    if (UCameraComponent* Component = IntroCamera->GetCameraComponent())
    {
        Component->SetFieldOfView(StartFieldOfViewDegrees);
        Component->bConstrainAspectRatio = false;
    }
    AimPitch = Aim.Pitch;
    AimYaw = Aim.Yaw;
    AimRoll = 0.0;
    PreviousYaw = Aim.Yaw;
    bAimInitialised = true;

    // Cut, not blend: the shot begins on its own first frame rather than sliding out of
    // wherever the visitor's head happened to be.
    Controller->SetViewTargetWithBlend(IntroCamera, 0.0f);
    PlaybackRoute = TEXT("native");
    return true;
}

bool UMikdashCinematics::Tick(float DeltaSeconds)
{
    if (!bPlaying)
    {
        TickHandle.Reset();
        return false;
    }
    // Keep external sequence timing unchanged: its player advances on its own
    // world clock. Only native/orbit playback owns this bounded choreography clock.
    const bool bUsesNativeClock = OrbitKeys.Num() > 0 || PlaybackRoute == TEXT("native");
    const float AcceptedStep = bUsesNativeClock ? NativeStepGate.Accept(DeltaSeconds) : DeltaSeconds;
    Elapsed += AcceptedStep;

    // The skip key is armed only after the press that started the walkthrough has had time
    // to clear, or the intro ends on its own first frame.
    if (bSkippable && Elapsed >= FMath::Max(SkipArmDelaySeconds, 0.0f))
    {
        if (APlayerController* Controller = GetOwningController())
        {
            if (Controller->PlayerInput && Controller->WasInputKeyJustPressed(EKeys::AnyKey))
            {
                SkipIntro();
                return false;
            }
        }
    }

    const float Duration = FMath::Max(ActiveDuration, 0.01f);
    const float Alpha = FMath::Clamp(Elapsed / Duration, 0.0f, 1.0f);

    if (OrbitKeys.Num() > 0)
    {
        // Orbit playback: the keys are already baked, so this is a straight look-up.
        const float Position = Alpha * static_cast<float>(OrbitKeys.Num() - 1);
        const int32 Index = FMath::Clamp(FMath::FloorToInt(Position), 0, OrbitKeys.Num() - 1);
        const int32 Next = FMath::Min(Index + 1, OrbitKeys.Num() - 1);
        const float T = Position - static_cast<float>(Index);
        if (IntroCamera)
        {
            IntroCamera->SetActorLocation(FMath::Lerp(OrbitKeys[Index].Location, OrbitKeys[Next].Location, T));
            IntroCamera->SetActorRotation(FMath::Lerp(OrbitKeys[Index].Rotation, OrbitKeys[Next].Rotation, T));
            if (UCameraComponent* Component = IntroCamera->GetCameraComponent())
            {
                Component->SetFieldOfView(FMath::Lerp(OrbitKeys[Index].FieldOfViewDegrees,
                                                      OrbitKeys[Next].FieldOfViewDegrees, T));
            }
        }
    }
    else if (PlaybackRoute == TEXT("native"))
    {
        EvaluateNative(Alpha, AcceptedStep);
    }

    if (Alpha >= 1.0f)
    {
        Finish();
        return false;
    }
    return true;
}

void UMikdashCinematics::EvaluateNative(float Alpha, float DeltaSeconds)
{
    if (!IntroCamera)
    {
        return;
    }
    const SplinePath& Path = ActiveIntroPath;

    // Trapezoidal speed: ramp up, hold a genuinely constant speed through the middle of
    // the flight, ramp down into the arrival. EaseInOutCubic would give one velocity peak
    // in the middle instead, which reads as a surge on a shot this long.
    const double Eased = MikdashCamera::EaseTrapezoid(Alpha, EaseInFraction, EaseOutFraction);
    const FVector Location = ToVec(Path.PointAtEasedAlpha(Eased));
    IntroCamera->SetActorLocation(Location);

    // Look-at, damped. The target itself is smoothstepped between the aim points, and the
    // rotator is then damped toward it, so neither the target nor the pointing has a
    // corner in it.
    const Orientation Target = MikdashCamera::LookAt(ToMath(Location), ToMath(AimAt(Alpha, ActiveIntroAimPoints)));
    Orientation Current;
    Current.Pitch = AimPitch;
    Current.Yaw = AimYaw;
    Current.Roll = AimRoll;
    const Orientation Damped = MikdashCamera::OrientationTowards(Current, Target, DeltaSeconds, AimHalfLifeSeconds);

    // Bank into the turn, from the yaw rate the damping just produced.
    const double YawRate = DeltaSeconds > KINDA_SMALL_NUMBER
                               ? MikdashCamera::ShortestDeltaDegrees(PreviousYaw, Damped.Yaw) / DeltaSeconds
                               : 0.0;
    const double TargetBank = MikdashCamera::BankFromTurnRate(YawRate, MaxBankDegrees, YawRateForFullBank);
    AimRoll = MikdashCamera::RollTowards(AimRoll, TargetBank, DeltaSeconds, BankHalfLifeSeconds);
    PreviousYaw = Damped.Yaw;
    AimPitch = Damped.Pitch;
    AimYaw = Damped.Yaw;

    IntroCamera->SetActorRotation(FRotator(AimPitch, AimYaw, AimRoll));
    if (UCameraComponent* Component = IntroCamera->GetCameraComponent())
    {
        // Widen gently into the arrival so the last beat sits at the walking field of view
        // and the hand-over is not a lens change.
        const float Lens = FMath::Lerp(StartFieldOfViewDegrees, EndFieldOfViewDegrees,
                                       static_cast<float>(MikdashCamera::SmootherStep(Alpha)));
        Component->SetFieldOfView(Lens);
    }
}

void UMikdashCinematics::SkipIntro()
{
    if (!bPlaying)
    {
        return;
    }
    UE_LOG(LogMikdashCinematics, Log, TEXT("Intro skipped at %.1f s of %.1f s."), Elapsed, ActiveDuration);
    Finish();
}

void UMikdashCinematics::Finish()
{
    bPlaying = false;
    if (TickHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
        TickHandle.Reset();
    }

    APlayerController* Controller = GetOwningController();
    if (Controller)
    {
        Controller->SetCinematicMode(false, true, true, true, true);
        if (APawn* Pawn = Controller->GetPawn())
        {
            Controller->SetViewTargetWithBlend(Pawn, HandoverBlendSeconds);
            // The visitor looks where the last frame of the shot looked, so control
            // arrives without the view snapping somewhere else.
            Controller->SetControlRotation(FRotator(0.0f, static_cast<float>(AimYaw), 0.0f));
        }
        else if (AActor* Previous = PreviousViewTarget.Get())
        {
            Controller->SetViewTargetWithBlend(Previous, HandoverBlendSeconds);
        }
    }

    if (SequenceActor)
    {
        if (ALevelSequenceActor* Actor = Cast<ALevelSequenceActor>(SequenceActor))
        {
            if (ULevelSequencePlayer* Player = Actor->GetSequencePlayer())
            {
                Player->Stop();
            }
        }
        SequenceActor->Destroy();
        SequenceActor = nullptr;
    }
    if (IntroCamera)
    {
        IntroCamera->Destroy();
        IntroCamera = nullptr;
    }
    OrbitKeys.Reset();
    OnIntroFinished.Broadcast();
}

// =====================================================================================
// baked keys
// =====================================================================================

TArray<FMikdashCameraKey> UMikdashCinematics::BuildIntroKeys(int32 SamplesPerSecond) const
{
    TArray<FMikdashCameraKey> Keys;
    MikdashSceneUnits::Frame Frame;
    SplinePath Path;
    TArray<FVector> AimPoints;
    FString Error;
    if (!BuildIntroForWorld(GetWorld(), Frame, Path, AimPoints, Error))
    {
        UE_LOG(LogMikdashCinematics, Warning, TEXT("Intro key build refused: %s"), *Error);
        return Keys;
    }
    const float Duration = GetDurationSeconds();
    const int32 Rate = FMath::Clamp(SamplesPerSecond, 1, 120);
    const int32 Count = FMath::Max(2, FMath::RoundToInt(Duration * Rate));
    const float Step = Duration / static_cast<float>(Count);
    Keys.Reserve(Count + 1);

    // Baked exactly the way the live fallback evaluates, damping included, so the authored
    // sequence and the native route are the same shot rather than two similar ones.
    Orientation Current;
    double Roll = 0.0;
    double LastYaw = 0.0;
    bool bFirst = true;
    for (int32 I = 0; I <= Count; ++I)
    {
        const float Time = Step * static_cast<float>(I);
        const float Alpha = FMath::Clamp(Time / FMath::Max(Duration, 0.01f), 0.0f, 1.0f);
        const double Eased = MikdashCamera::EaseTrapezoid(Alpha, EaseInFraction, EaseOutFraction);
        const FVector Location = ToVec(Path.PointAtEasedAlpha(Eased));
        const Orientation Target = MikdashCamera::LookAt(ToMath(Location), ToMath(AimAt(Alpha, AimPoints)));
        if (bFirst)
        {
            Current = Target;
            LastYaw = Target.Yaw;
            bFirst = false;
        }
        else
        {
            Current = MikdashCamera::OrientationTowards(Current, Target, Step, AimHalfLifeSeconds);
            const double YawRate = MikdashCamera::ShortestDeltaDegrees(LastYaw, Current.Yaw) / FMath::Max(Step, 1e-4f);
            const double TargetBank = MikdashCamera::BankFromTurnRate(YawRate, MaxBankDegrees, YawRateForFullBank);
            Roll = MikdashCamera::RollTowards(Roll, TargetBank, Step, BankHalfLifeSeconds);
            LastYaw = Current.Yaw;
        }

        FMikdashCameraKey Key;
        Key.TimeSeconds = Time;
        Key.Location = Location;
        Key.Rotation = FRotator(Current.Pitch, Current.Yaw, Roll);
        Key.FieldOfViewDegrees = FMath::Lerp(StartFieldOfViewDegrees, EndFieldOfViewDegrees,
                                             static_cast<float>(MikdashCamera::SmootherStep(Alpha)));
        Keys.Add(Key);
    }
    return Keys;
}

TArray<FMikdashOrbitShot> UMikdashCinematics::OrbitShots()
{
    // Subjects are the placed coordinates recorded in the receipts under SourceAssets/.
    // Radii are chosen so the subject fills a comfortable part of the frame at the lens
    // given; BuildOrbitKeys then clamps every sample so it really is inside the safe inset.
    TArray<FMikdashOrbitShot> Shots;

    FMikdashOrbitShot Menorah;
    Menorah.Id = TEXT("menorah");
    Menorah.Description = TEXT("Menorah turntable, Heichal floor top 925");
    Menorah.Subject = FVector(-5330.0, 315.0, 1100.0);
    Menorah.RadiusCm = 900.0f;
    Menorah.HeightCm = 120.0f;
    Menorah.StartYawDegrees = 20.0f;
    Menorah.SweepDegrees = 140.0f;
    Menorah.DurationSeconds = 14.0f;
    Menorah.FieldOfViewDegrees = 42.0f;
    Menorah.SubjectRadiusCm = 220.0f;
    Shots.Add(Menorah);

    FMikdashOrbitShot Altar;
    Altar.Id = TEXT("goldenAltar");
    Altar.Description = TEXT("Golden altar, Heichal");
    Altar.Subject = FVector(-4650.0, 0.0, 1050.0);
    Altar.RadiusCm = 800.0f;
    Altar.HeightCm = 150.0f;
    Altar.StartYawDegrees = 0.0f;
    Altar.SweepDegrees = 120.0f;
    Altar.DurationSeconds = 12.0f;
    Altar.FieldOfViewDegrees = 45.0f;
    Altar.SubjectRadiusCm = 180.0f;
    Shots.Add(Altar);

    FMikdashOrbitShot Aron;
    Aron.Id = TEXT("aron");
    Aron.Description = TEXT("Aron and keruvim, Kodesh floor X -6700 to -5700");
    Aron.Subject = FVector(-6200.0, 0.0, 1063.0);
    Aron.RadiusCm = 620.0f;
    Aron.HeightCm = 90.0f;
    Aron.StartYawDegrees = 25.0f;
    Aron.SweepDegrees = 90.0f;
    Aron.DurationSeconds = 12.0f;
    Aron.FieldOfViewDegrees = 48.0f;
    Aron.SubjectRadiusCm = 160.0f;
    Shots.Add(Aron);

    FMikdashOrbitShot OuterAltar;
    OuterAltar.Id = TEXT("altar");
    OuterAltar.Description = TEXT("The altar in the inner court, upper tier 1067, wood 1091");
    OuterAltar.Subject = FVector(0.0, 0.0, 900.0);
    OuterAltar.RadiusCm = 2600.0f;
    OuterAltar.HeightCm = 900.0f;
    OuterAltar.StartYawDegrees = 30.0f;
    OuterAltar.SweepDegrees = 200.0f;
    OuterAltar.DurationSeconds = 18.0f;
    OuterAltar.FieldOfViewDegrees = 55.0f;
    OuterAltar.SubjectRadiusCm = 900.0f;
    Shots.Add(OuterAltar);

    FMikdashOrbitShot House;
    House.Id = TEXT("house");
    House.Description = TEXT("The House from outside, Golden roof top 6130");
    House.Subject = FVector(-4900.0, 0.0, 3200.0);
    House.RadiusCm = 9000.0f;
    House.HeightCm = 3200.0f;
    House.StartYawDegrees = 20.0f;
    House.SweepDegrees = 150.0f;
    House.DurationSeconds = 20.0f;
    House.FieldOfViewDegrees = 55.0f;
    House.SubjectRadiusCm = 3000.0f;
    Shots.Add(House);

    FMikdashOrbitShot Court;
    Court.Id = TEXT("outerCourt");
    Court.Description = TEXT("The whole enclosure, outer platform 8100 square");
    Court.Subject = FVector(0.0, 0.0, 1500.0);
    Court.RadiusCm = 17000.0f;
    Court.HeightCm = 8000.0f;
    Court.StartYawDegrees = 45.0f;
    Court.SweepDegrees = 360.0f;
    Court.DurationSeconds = 26.0f;
    Court.FieldOfViewDegrees = 55.0f;
    Court.SubjectRadiusCm = 9000.0f;
    Shots.Add(Court);

    return Shots;
}

TArray<FMikdashCameraKey> UMikdashCinematics::BuildOrbitKeys(const FMikdashOrbitShot& Shot, int32 SamplesPerSecond)
{
    TArray<FMikdashCameraKey> Keys;
    const int32 Rate = FMath::Clamp(SamplesPerSecond, 1, 120);
    const float Duration = FMath::Max(Shot.DurationSeconds, 0.5f);
    const int32 Count = FMath::Max(2, FMath::RoundToInt(Duration * Rate));
    Keys.Reserve(Count + 1);

    // The frustum spec the orbits are framed against. SafeInset 0.8 keeps the subject clear
    // of the corners, which is where the lens distortion and the vignette live.
    MikdashCamera::FrustumSpec Spec;
    Spec.HorizontalFovDegrees = Shot.FieldOfViewDegrees;
    Spec.AspectRatio = 16.0 / 9.0;
    Spec.NearClipCm = 10.0;
    Spec.SafeInset = 0.8;

    for (int32 I = 0; I <= Count; ++I)
    {
        const float Alpha = static_cast<float>(I) / static_cast<float>(Count);
        // Eased in and out, so a turntable starts and stops without a jerk even when it is
        // cut into a loop.
        const double Eased = MikdashCamera::SmootherStep(Alpha);
        const double Yaw = Shot.StartYawDegrees + Shot.SweepDegrees * Eased;
        const double Radians = MikdashCamera::DegToRad(Yaw);
        const FVector Position(Shot.Subject.X + Shot.RadiusCm * FMath::Cos(Radians),
                               Shot.Subject.Y + Shot.RadiusCm * FMath::Sin(Radians),
                               Shot.Subject.Z + Shot.HeightCm);
        const Orientation Aim = MikdashCamera::LookAt(ToMath(Position), ToMath(Shot.Subject));

        // Guarantee the framing rather than assume it: push back off the subject if the
        // radius is too tight for the lens, and re-aim onto the safe inset if it is not
        // already inside it.
        const double MinDistance = Shot.SubjectRadiusCm * 1.35;
        const MikdashCamera::FrustumClampResult Safe =
            MikdashCamera::FrustumSafeClamp(ToMath(Position), Aim, ToMath(Shot.Subject), Spec, MinDistance);

        FMikdashCameraKey Key;
        Key.TimeSeconds = Duration * Alpha;
        Key.Location = ToVec(Safe.Position);
        Key.Rotation = ToRotator(Safe.Rotation);
        Key.FieldOfViewDegrees = Shot.FieldOfViewDegrees;
        Keys.Add(Key);
    }
    return Keys;
}

bool UMikdashCinematics::PlayOrbit(FName OrbitId)
{
    LastRefusal.Reset();
    if (bPlaying)
    {
        LastRefusal = TEXT("Something is already playing.");
        return false;
    }
    const TArray<FMikdashOrbitShot> Shots = OrbitShots();
    const FMikdashOrbitShot* Found = Shots.FindByPredicate(
        [OrbitId](const FMikdashOrbitShot& S) { return S.Id == OrbitId; });
    if (!Found)
    {
        LastRefusal = FString::Printf(TEXT("No orbit called %s."), *OrbitId.ToString());
        return false;
    }
    APlayerController* Controller = GetOwningController();
    UWorld* World = GetWorld();
    if (!Controller || !World)
    {
        LastRefusal = TEXT("No world or player controller.");
        return false;
    }

    OrbitKeys = BuildOrbitKeys(*Found, 30);
    if (OrbitKeys.Num() < 2)
    {
        LastRefusal = TEXT("The orbit produced no keys.");
        return false;
    }

    FActorSpawnParameters Params;
    Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    IntroCamera = World->SpawnActor<ACameraActor>(ACameraActor::StaticClass(),
                                                  OrbitKeys[0].Location, OrbitKeys[0].Rotation, Params);
    if (!IntroCamera)
    {
        LastRefusal = TEXT("Could not spawn the orbit camera.");
        OrbitKeys.Reset();
        return false;
    }
    if (UCameraComponent* Component = IntroCamera->GetCameraComponent())
    {
        Component->SetFieldOfView(OrbitKeys[0].FieldOfViewDegrees);
        Component->bConstrainAspectRatio = false;
    }

    PreviousViewTarget = Controller->GetViewTarget();
    Controller->SetViewTargetWithBlend(IntroCamera, 0.0f);
    Controller->SetCinematicMode(true, true, true, true, true);

    PlaybackRoute = TEXT("orbit");
    Elapsed = 0.0f;
    NativeStepGate.Reset();
    ActiveDuration = FMath::Max(Found->DurationSeconds, 0.5f);
    bPlaying = true;
    if (!TickHandle.IsValid())
    {
        TickHandle = FTSTicker::GetCoreTicker().AddTicker(
            FTickerDelegate::CreateUObject(this, &UMikdashCinematics::Tick), 0.0f);
    }
    UE_LOG(LogMikdashCinematics, Log, TEXT("Orbit %s playing over %.1f s."), *OrbitId.ToString(), ActiveDuration);
    return true;
}
