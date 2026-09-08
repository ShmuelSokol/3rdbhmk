// MikdashCinematics.h -- the cinematic intro, and the orbit shots used for stills.
//
// The walkthrough used to begin with the visitor standing in the inner court with no idea
// where they were. This is the 55 second answer: the modern city, a climb to the Mount,
// a pass over the outer court, and a level run in through the inner eastern gate to the
// exact spot where the player takes control.
//
// TWO WAYS TO PLAY IT, AND WHY
//
//  1. A Level Sequence authored by Scripts/release_intro_sequence.py. That script builds
//     the asset with the Sequencer Python API -- LevelSequenceFactoryNew, a camera cut
//     track, and a spawnable cine camera with transform keys -- so the shot can be opened,
//     inspected and re-timed by hand in the editor like any other sequence.
//
//  2. A native fallback that flies the same path directly, using the arc-length
//     reparameterised spline and the ease curves in CameraPathMath.h.
//
// Both fly the SAME control points, which live in one place: IntroControlPoints() below
// mirrors what the release script writes and what
// Plugins/MikdashRuntime/Tests/CameraPathMathTest.cpp proves clears the geometry. Route 2
// exists so the intro is never missing merely because the asset has not been cooked into
// a particular build, and so the path can be flown in a commandlet with no asset at all.
//
// HOW IT GETS THE VIEW
//
// It does not fight the front end for the view target. UMikdashFrontEnd broadcasts
// OnWalkthroughStarted after it has already put the view back on the visitor's pawn, and
// this subsystem takes over from there and hands it back the same way when the shot ends.
//
// Units are centimetres, seconds and degrees throughout, matching CameraPathMath.h.

#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "UObject/SoftObjectPath.h"

#include "MikdashCinematics.generated.h"

class ACameraActor;
class APlayerController;
class UWorld;

/** Fired when the intro finishes or is skipped, so gameplay can start on the same frame. */
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FMikdashIntroFinished);

/** One promotional orbit: a subject, a ring around it, and a lens. */
USTRUCT(BlueprintType)
struct FMikdashOrbitShot
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Cinematics") FName Id;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Cinematics") FString Description;

    /** What the shot is of, in world centimetres. */
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Cinematics") FVector Subject = FVector::ZeroVector;

    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Cinematics") float RadiusCm = 1000.0f;
    /** Camera height above the subject. */
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Cinematics") float HeightCm = 200.0f;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Cinematics") float StartYawDegrees = 0.0f;
    /** Degrees of arc swept over the shot. A full 360 makes a loopable turntable. */
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Cinematics") float SweepDegrees = 120.0f;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Cinematics") float DurationSeconds = 12.0f;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Cinematics") float FieldOfViewDegrees = 50.0f;
    /** Radius of the thing being framed, used to keep it inside the safe frustum inset. */
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Cinematics") float SubjectRadiusCm = 200.0f;
};

/** A pose on the intro path: what the release script keys and what the fallback flies. */
USTRUCT(BlueprintType)
struct FMikdashCameraKey
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Cinematics") float TimeSeconds = 0.0f;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Cinematics") FVector Location = FVector::ZeroVector;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Cinematics") FRotator Rotation = FRotator::ZeroRotator;
    UPROPERTY(BlueprintReadWrite, Category = "Mikdash|Cinematics") float FieldOfViewDegrees = 60.0f;
};

UCLASS(Config = Game, MinimalAPI)
class UMikdashCinematics : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    MIKDASHRUNTIME_API virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    MIKDASHRUNTIME_API virtual void Deinitialize() override;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Cinematics", meta = (WorldContext = "WorldContext"))
    static MIKDASHRUNTIME_API UMikdashCinematics* Get(const UObject* WorldContext);

    /** Play the intro. Returns false and says why in GetLastRefusalReason if it will not. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Cinematics") MIKDASHRUNTIME_API bool PlayIntro();

    /** Stop now and hand the view back. Called by any key press while the intro runs. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Cinematics") MIKDASHRUNTIME_API void SkipIntro();

    UFUNCTION(BlueprintPure, Category = "Mikdash|Cinematics") bool IsPlaying() const { return bPlaying; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Cinematics") bool HasPlayedThisSession() const { return bPlayedThisSession; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Cinematics") float GetElapsedSeconds() const { return Elapsed; }
    UFUNCTION(BlueprintPure, Category = "Mikdash|Cinematics") MIKDASHRUNTIME_API float GetDurationSeconds() const;
    UFUNCTION(BlueprintPure, Category = "Mikdash|Cinematics") FString GetLastRefusalReason() const { return LastRefusal; }
    /** "sequence" when the authored Level Sequence played, "native" when the fallback did. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Cinematics") FString GetPlaybackRoute() const { return PlaybackRoute; }

    UPROPERTY(BlueprintAssignable, Category = "Mikdash|Cinematics") FMikdashIntroFinished OnIntroFinished;

    // -- the path ----------------------------------------------------------

    /**
     * The intro control points, in world centimetres, in order.
     *
     * These are the numbers the release script writes into the Level Sequence and the
     * numbers CameraPathMathTest.cpp proves clear the 18 blocking volumes by 150 cm. Any
     * change here has to be made in all three places and re-verified.
     */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Cinematics")
    static MIKDASHRUNTIME_API TArray<FVector> IntroControlPoints();

    /** The points the camera aims at, paired with the fraction of the shot they apply at. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Cinematics")
    static MIKDASHRUNTIME_API TArray<FVector> IntroAimPoints();
    UFUNCTION(BlueprintPure, Category = "Mikdash|Cinematics")
    static MIKDASHRUNTIME_API TArray<float> IntroAimAlphas();

    /**
     * Sample the whole shot at a fixed rate, eased, with the look-at already damped.
     * This is what release_intro_sequence.py bakes into the transform track, and what the
     * native fallback evaluates, so the two cannot drift apart.
     */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Cinematics")
    MIKDASHRUNTIME_API TArray<FMikdashCameraKey> BuildIntroKeys(int32 SamplesPerSecond) const;

    /** The promotional orbits. Ids are stable; release_intro_sequence.py writes them out. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Cinematics")
    static MIKDASHRUNTIME_API TArray<FMikdashOrbitShot> OrbitShots();

    /** Sample one orbit, frustum-clamped so the subject is inside the safe inset throughout. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Cinematics")
    static MIKDASHRUNTIME_API TArray<FMikdashCameraKey> BuildOrbitKeys(const FMikdashOrbitShot& Shot, int32 SamplesPerSecond);

    /** Fly one orbit live, for a promotional still without opening the editor. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Cinematics")
    MIKDASHRUNTIME_API bool PlayOrbit(FName OrbitId);

protected:
    /** Turn the intro off entirely from DefaultGame.ini. */
    UPROPERTY(Config) bool bEnabled = true;

    /** Play automatically when the front end says the walkthrough has started. */
    UPROPERTY(Config) bool bPlayOnWalkthroughStart = true;

    /** Play at most once per run, so returning to the menu does not replay it. */
    UPROPERTY(Config) bool bOncePerSession = true;

    /** Total running time. The brief for this shot is 40 to 70 seconds. */
    UPROPERTY(Config) float IntroDurationSeconds = 55.0f;

    /** Trapezoidal speed profile: this much of the shot ramping up, this much down. */
    UPROPERTY(Config) float EaseInFraction = 0.22f;
    UPROPERTY(Config) float EaseOutFraction = 0.32f;

    /** Half life of the look-at damping, in seconds. Larger is lazier. */
    UPROPERTY(Config) float AimHalfLifeSeconds = 0.55f;

    /** Degrees of bank at the sustained turn rate given below. Zero disables banking. */
    UPROPERTY(Config) float MaxBankDegrees = 6.0f;
    UPROPERTY(Config) float YawRateForFullBank = 22.0f;
    UPROPERTY(Config) float BankHalfLifeSeconds = 0.9f;

    UPROPERTY(Config) float StartFieldOfViewDegrees = 62.0f;
    UPROPERTY(Config) float EndFieldOfViewDegrees = 75.0f;

    /** Blend out to the visitor's own view at the end, in seconds. */
    UPROPERTY(Config) float HandoverBlendSeconds = 0.6f;

    /** Authored sequence. Empty, or missing, means the native fallback is used. */
    UPROPERTY(Config) FSoftObjectPath IntroSequence;

    /** Let any key skip. Off makes the intro unskippable, which is rarely a kindness. */
    UPROPERTY(Config) bool bSkippable = true;

    /**
     * Seconds before the skip key is armed. Without this the click or key press that left
     * the title screen is still in the input buffer on the intro's first frame and skips
     * the whole shot instantly.
     */
    UPROPERTY(Config) float SkipArmDelaySeconds = 1.0f;

private:
    UFUNCTION() void HandleWalkthroughStarted();

    bool Tick(float DeltaSeconds);
    void Finish();
    APlayerController* GetOwningController() const;
    bool StartSequencePlayback(APlayerController* Controller);
    bool StartNativePlayback(APlayerController* Controller);
    void EvaluateNative(float Alpha, float DeltaSeconds);

    UPROPERTY(Transient) TObjectPtr<ACameraActor> IntroCamera;
    UPROPERTY(Transient) TObjectPtr<AActor> SequenceActor;
    UPROPERTY(Transient) TWeakObjectPtr<AActor> PreviousViewTarget;

    FTSTicker::FDelegateHandle TickHandle;
    FString LastRefusal;
    FString PlaybackRoute;

    // Live look-at state, so the aim is damped rather than snapped frame to frame.
    double AimPitch = 0.0;
    double AimYaw = 0.0;
    double AimRoll = 0.0;
    double PreviousYaw = 0.0;
    float Elapsed = 0.0f;
    float ActiveDuration = 0.0f;
    bool bPlaying = false;
    bool bPlayedThisSession = false;
    bool bAimInitialised = false;

    // Orbit playback reuses the same ticker; empty when the intro is what is running.
    TArray<FMikdashCameraKey> OrbitKeys;
};
