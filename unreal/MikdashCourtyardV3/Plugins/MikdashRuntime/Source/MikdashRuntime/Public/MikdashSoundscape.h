#pragma once

// The actor. Its engine-independent maths lives in SoundscapeMath.h, which the
// standalone test compiles on its own.

#include "SoundscapeMath.h"


// -----------------------------------------------------------------------------
// PART 2 -- the actor. Skipped when the standalone test compiles this header.
// -----------------------------------------------------------------------------

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MikdashSoundscape.generated.h"

class UAudioComponent;
class USoundAttenuation;
class USoundBase;
class USoundSubmixBase;
class UReverbEffect;
class AMikdashTimeOfDay;

/** Mirror of MikdashSoundscape::ELayer for the reflection system. The two are kept in
 *  step by static_asserts at the top of MikdashSoundscape.cpp. */
UENUM(BlueprintType)
enum class EMikdashSoundLayer : uint8
{
    WindBed      UMETA(DisplayName = "Wind bed"),
    WindGust     UMETA(DisplayName = "Wind gust"),
    CrowdCourt   UMETA(DisplayName = "Crowd in the courts"),
    CrowdDistant UMETA(DisplayName = "Distant voices"),
    City         UMETA(DisplayName = "Modern city below"),
    Bird         UMETA(DisplayName = "Birds"),
    Service      UMETA(DisplayName = "The service"),
    Footstep     UMETA(DisplayName = "Footsteps"),
    Foliage      UMETA(DisplayName = "Foliage"),
    Cloth        UMETA(DisplayName = "Cloth")
};

/** One placed emitter. Filled by Scripts/release_soundscape_v2.py from the spec, or
 *  authored by hand in the details panel. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashSoundEmitter
{
    GENERATED_BODY()

    /** Human-readable, and the key the release receipt reads back. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter")
    FName Label;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter")
    EMikdashSoundLayer Layer = EMikdashSoundLayer::WindBed;

    /** World location in centimetres. The release script places this actor at the
     *  origin so the numbers in the receipt are the numbers in the spec. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter")
    FVector LocationCm = FVector::ZeroVector;

    /** Takes this emitter may draw from. More than one is what stops repetition. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter")
    TArray<TObjectPtr<USoundBase>> Sources;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter")
    TObjectPtr<USoundAttenuation> Attenuation = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter", meta = (ClampMin = "0.0"))
    float BaseVolume = 1.0f;

    /** True for the continuous beds. False means silence, then one event. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter")
    bool bLooping = false;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter", meta = (ClampMin = "0.0"))
    float MinGapSeconds = 20.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter", meta = (ClampMin = "0.0"))
    float MaxGapSeconds = 70.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter", meta = (ClampMin = "0.05"))
    float MinPitch = 0.92f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter", meta = (ClampMin = "0.05"))
    float MaxPitch = 1.08f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter", meta = (ClampMin = "0.0"))
    float MinLevel = 0.5f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter", meta = (ClampMin = "0.0"))
    float MaxLevel = 1.0f;

    /** Wind and city only. When true the emitter's gain follows the listener's height
     *  (wind rises, city falls) instead of being flat. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter")
    bool bHeightVarying = false;

    /** Trace from this emitter to the listener each update and attenuate what the
     *  court walls block. Off for the beds, which are meant to be everywhere. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter")
    bool bOcclude = false;

    /** Crowd-driven layers scale with the live head count instead of sitting at a
     *  fixed level. Set on the CrowdCourt emitters. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter")
    bool bCrowdScaled = false;

    /** Free text carried into the receipt: where this is and why. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Emitter")
    FString Place;
};

/** One acoustic region. The Heikhal is a stone hall; the open court is not. */
USTRUCT(BlueprintType)
struct MIKDASHRUNTIME_API FMikdashAcousticZone
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zone")
    FName Label;

    /** Axis-aligned, world centimetres. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zone")
    FVector MinCm = FVector::ZeroVector;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zone")
    FVector MaxCm = FVector::ZeroVector;

    /** Crossing distance measured inward from each face, so the zone never reaches
     *  outside its own bounds. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zone", meta = (ClampMin = "0.0"))
    float BlendMarginCm = 250.f;

    /** Higher wins where zones overlap: the Kodesh sits inside the Heikhal. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zone")
    int32 Priority = 0;

    /** Multiplier on every emitter outside this zone, applied to a listener inside it. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zone",
              meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float DryGain = 0.10f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zone", meta = (ClampMin = "20.0"))
    float LowPassHz = 650.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zone",
              meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float ReverbSend = 0.35f;

    /** 0 fully sheltered, 1 fully open. Feeds the wind height/exposure curve, which is
     *  why standing in the Ulam porch does not sound like standing on the platform. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Zone",
              meta = (ClampMin = "0.0", ClampMax = "1.0"))
    float Exposure = 0.f;

    /** Optional. When the release script succeeded in giving an AAudioVolume a real
     *  brush, its path is recorded here so the receipt can say which mechanism is
     *  actually carrying this zone. Never dereferenced at run time; this actor does
     *  not need the volume and does not read it. */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Zone")
    FString BackingAudioVolume;
};

/**
 * The layered soundscape.
 *
 * ONE actor drives every ambience emitter on the Mount. It is spawned and configured
 * by Scripts/release_soundscape_v2.py; nothing here loads an asset by path or by
 * name, so a missing reference is a null pointer and a skipped layer, never a crash
 * and never a silent hard-coded fallback.
 *
 * WHAT IT TOUCHES: only UAudioComponents it created itself, and its own properties.
 * It never writes to AMikdashTimeOfDay, to AMikdashBirdFlock, to the player
 * controller, to any placed AAudioVolume, or to any asset.
 *
 * WHAT IT READS FROM OTHER SYSTEMS, all through public const getters or delegates:
 *   AMikdashTimeOfDay   GetTimeOfDayHours, GetCivilDawnHours, GetSunriseHours,
 *                       GetSolarNoonHours, GetSunsetHours, GetCivilDuskHours, and the
 *                       OnTimeOfDayChanged delegate.
 *   AMikdashBirdFlock   the OnBirdSound delegate. See FMikdashBirdSoundSignature: the
 *                       flock module deliberately plays no audio and only announces
 *                       that a call, wingburst, startle or landing happened. Binding
 *                       to it is the documented contract; that module's files are not
 *                       edited by this one, and binding is done reflectively so this
 *                       module does not even need to include its header.
 *
 * WHAT IT OFFERS TO OTHER SYSTEMS, so they need not be edited either:
 *   PlayFootstep(...)     for whoever owns locomotion. Footstep SURFACE selection
 *                         already exists and is not duplicated here -- see
 *                         MikdashSurfaceAudioRouting.h, which routes a floor mesh path
 *                         to a Stone / Soft / Silent bank. This actor only holds the
 *                         banks and plays them where it is told.
 *   PlayServiceSound(...) for AMikdashServiceActor.
 * Both are BlueprintCallable and both are no-ops until their banks are populated.
 */
UCLASS(Blueprintable, ClassGroup = "Mikdash", meta = (DisplayName = "Mikdash Soundscape"))
class MIKDASHRUNTIME_API AMikdashSoundscape : public AActor
{
    GENERATED_BODY()

public:
    AMikdashSoundscape();

    // ---------------------------------------------------------------- content
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape")
    TArray<FMikdashSoundEmitter> Emitters;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape")
    TArray<FMikdashAcousticZone> Zones;

    /** Bird one-shots, chosen by the event name the flock broadcast. Empty means the
     *  hook is bound and ignored, which is a valid state: the flock still flies. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Birds")
    TArray<TObjectPtr<USoundBase>> BirdCallSounds;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Birds")
    TArray<TObjectPtr<USoundBase>> BirdWingburstSounds;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Birds")
    TObjectPtr<USoundAttenuation> BirdAttenuation = nullptr;

    /** Ceiling on bird one-shots per second across all flocks. Thousands of birds
     *  broadcasting is fine; thousands of voices is not. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Birds",
              meta = (ClampMin = "0.0"))
    float MaxBirdSoundsPerSecond = 3.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Footsteps")
    TArray<TObjectPtr<USoundBase>> FootstepStoneSounds;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Footsteps")
    TArray<TObjectPtr<USoundBase>> FootstepSoftSounds;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Footsteps")
    TObjectPtr<USoundAttenuation> FootstepAttenuation = nullptr;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Service")
    TArray<TObjectPtr<USoundBase>> ServiceSounds;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Service")
    TObjectPtr<USoundAttenuation> ServiceAttenuation = nullptr;

    /** The stone-hall reverb, as a submix with a reverb effect in its chain. Every
     *  emitter sends into it at the level the current zone asks for, which is 0 in the
     *  open court and 0.35 inside the Heikhal.
     *
     *  This is the brush-free half of the reverb answer. See
     *  SourceAssets/soundscape-review/SoundscapeV2/FINDING-AudioVolume-brush.md: an
     *  AAudioVolume spawned from Python DOES get a real cube brush in UE 5.8, but it
     *  gets one only because the placement path happens to run an actor factory, and
     *  the failure mode is silent. A submix send driven from this actor needs no BSP,
     *  no brush builder and no editor-only code path, so it works identically in a
     *  packaged build and can be read back numerically. When the volume does build, it
     *  is placed as well and the two agree; when it does not, this alone carries the
     *  zone. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Reverb")
    TObjectPtr<USoundSubmixBase> ReverbSubmix = nullptr;

    // ---------------------------------------------------------------- geometry
    /** Court floor height. The wind height curve is measured from here. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Geometry")
    float GroundZCm = 625.f;

    /** Plaza level, where the modern city is loudest. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Geometry")
    float PlazaZCm = 0.f;

    /** Highest point a listener can stand. The city curve reaches its floor here. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Geometry")
    float SummitZCm = 3000.f;

    // ---------------------------------------------------------------- behaviour
    /** Changing this changes every gap, pitch and level in the whole soundscape, and
     *  changes nothing else. Two runs with the same seed are identical. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Behaviour")
    int32 Seed = 20260908;

    /** Master multiplier, driven by the settings menu's ambience slider. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Behaviour",
              meta = (ClampMin = "0.0"))
    float MasterVolume = 1.f;

    /** Seconds. How fast a gain change is followed. 1.4 s is slow enough that walking
     *  through the Ulam doorway is a transition rather than a switch. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Behaviour",
              meta = (ClampMin = "0.01"))
    float ZoneBlendSeconds = 1.4f;

    /** Seconds. Each emitter owns two voices and crossfades between them when it moves
     *  to the next take, so the join between one recording and the next is a fade and
     *  not a splice. Two voices per emitter is the price of never hearing a seam. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Behaviour",
              meta = (ClampMin = "0.05"))
    float CrossfadeSeconds = 2.5f;

    /** Seconds between scheduler updates. The audio itself is sample-accurate; this is
     *  only how often gains and gaps are reconsidered. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Behaviour",
              meta = (ClampMin = "0.02"))
    float UpdateIntervalSeconds = 0.25f;

    /** Occlusion traces are spread across updates so no single frame pays for all of
     *  them. This is how many are done per update. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Behaviour",
              meta = (ClampMin = "0"))
    int32 OcclusionTracesPerUpdate = 2;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Behaviour",
              meta = (ClampMin = "0.0"))
    float MaxOcclusionAttenuationDb = 12.f;

    /** Head count of the instanced crowd, and how many residents are speaking. Set by
     *  whoever owns the crowd; if nothing sets them the murmur uses its authored
     *  level unchanged. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Crowd",
              meta = (ClampMin = "0.0"))
    float CrowdHeadCount = 0.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Crowd",
              meta = (ClampMin = "0.0"))
    float CrowdReferenceCount = 1200.f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Crowd",
              meta = (ClampMin = "0"))
    int32 SpeakingResidentCount = 0;

    /** Explicit time-of-day actor. Left empty, the first one in the level is used. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Time")
    TObjectPtr<AMikdashTimeOfDay> TimeOfDay = nullptr;

    /** When no AMikdashTimeOfDay is found, this hour is used and nothing varies. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Time",
              meta = (ClampMin = "0.0", ClampMax = "24.0"))
    float FallbackHours = 9.f;

    /** Bind every AMikdashBirdFlock in the level at BeginPlay. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Soundscape|Birds")
    bool bBindBirdFlocks = true;

    // ---------------------------------------------------------------- API
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Soundscape")
    void RebuildEmitters();

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Soundscape")
    void SetMasterVolume(float NewVolume);

    /** Bank 0 = stone, 1 = soft. Matches MikdashSurfaceAudio::Bank order minus Silent,
     *  which never reaches here. Safe to call every step; a no-op if the bank is
     *  empty. */
    UFUNCTION(BlueprintCallable, Category = "Mikdash|Soundscape")
    void PlayFootstep(int32 Bank, FVector WorldLocationCm, float Level = 1.f);

    UFUNCTION(BlueprintCallable, Category = "Mikdash|Soundscape")
    void PlayServiceSound(FName EventName, FVector WorldLocationCm, float Level = 1.f);

    /** Bound to AMikdashBirdFlock::OnBirdSound. Public so a flock can be bound by hand. */
    UFUNCTION()
    void HandleBirdSound(FName EventName, FName SpeciesName, FVector WorldLocationCm,
                         float Intensity);

    UFUNCTION()
    void HandleTimeOfDayChanged(float NewTimeOfDayHours, float SunAltitudeDegrees);

    /** Current smoothed gain of a layer, 0..4. For the debug overlay and for the
     *  release script's numeric readback. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Soundscape")
    float GetLayerGain(EMikdashSoundLayer Layer) const;

    UFUNCTION(BlueprintPure, Category = "Mikdash|Soundscape")
    FName GetCurrentZoneLabel() const { return CurrentZoneLabel; }

    UFUNCTION(BlueprintPure, Category = "Mikdash|Soundscape")
    int32 GetActiveEmitterCount() const;

    /** Low-pass corner currently applied, in Hz. 20000 means open. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Soundscape")
    float GetCurrentLowPassHz() const { return static_cast<float>(Acoustics.LpfHz); }

    UFUNCTION(BlueprintPure, Category = "Mikdash|Soundscape")
    float GetCurrentDryGain() const { return static_cast<float>(Acoustics.DryGain); }

    UFUNCTION(BlueprintPure, Category = "Mikdash|Soundscape")
    float GetCurrentReverbSend() const { return static_cast<float>(Acoustics.ReverbSend); }

    /** One line naming the hour, the zone, the crowd and the per-layer gains. Written
     *  into the release receipt. */
    UFUNCTION(BlueprintPure, Category = "Mikdash|Soundscape")
    FString DescribeState() const;

    // AActor
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;

protected:
    /** Per-emitter live state. Not reflected: it is rebuilt from Emitters at every
     *  BeginPlay and never saved. */
    struct FEmitterRuntime
    {
        int32  Index = 0;
        uint32 Pass = 0;
        int32  PreviousSource = -1;
        double CountdownSeconds = 0.0;
        double SmoothedGain = 0.0;
        double OcclusionFraction = 0.0;
        /** Which of the emitter's two voices is the current take. */
        int32  ActiveSlot = 0;
        /** Per-voice crossfade envelope, 0..1. */
        double SlotEnvelope[2] = {0.0, 0.0};
        /** The event this emitter is counting down towards, or currently sounding.
         *  Gap and take are drawn together so the silence always belongs to the take
         *  that follows it. */
        MikdashSoundscape::EmitterEvent Pending;
        /** True while a take is sounding; false during the silence before one. */
        bool   bSounding = false;
    };
    TArray<FEmitterRuntime> Runtime;

    /** TWO components per emitter, at 2*i and 2*i+1, so a take change is a crossfade
     *  rather than a splice. Held in a UPROPERTY so the GC keeps them. */
    UPROPERTY(Transient)
    TArray<TObjectPtr<UAudioComponent>> Components;

    /** One-shots spawned for birds, footsteps and the service. Pruned as they finish. */
    UPROPERTY(Transient)
    TArray<TObjectPtr<UAudioComponent>> OneShots;

    UPROPERTY(Transient)
    FName CurrentZoneLabel = NAME_None;

    void DestroyComponents();
    void UpdateAcoustics(const FVector& ListenerCm, double DeltaSeconds);
    void UpdateScheduler(const FVector& ListenerCm, double DeltaSeconds);
    void UpdateOcclusion(const FVector& ListenerCm);
    void PruneOneShots();
    bool GetListenerLocation(FVector& OutCm) const;
    void BindTimeOfDay();
    void BindBirdFlocks();

    MikdashSoundscape::DayAnchors CurrentAnchors() const;
    double CurrentHours() const;
    MikdashSoundscape::EmitterSchedule ScheduleFor(int32 Index) const;
    double TargetGainFor(int32 Index, const FVector& ListenerCm, double EventLevel) const;
    void StartEvent(int32 Index, const MikdashSoundscape::EmitterEvent& Event);
    void ApplyAcousticsTo(UAudioComponent* Component) const;
    UAudioComponent* SpawnOneShot(USoundBase* Sound, USoundAttenuation* Attenuation,
                                  const FVector& LocationCm, float Volume, float Pitch);

    /** Live acoustic state, blended towards the zone target. */
    MikdashSoundscape::Acoustic Acoustics;
    double LayerGains[MikdashSoundscape::LayerCount] = {};
    double UpdateAccumulator = 0.0;
    int32  OcclusionCursor = 0;
    double BirdSoundBudget = 0.0;
    double CachedHours = 9.0;
    /** Advances once per requested one-shot, so two flocks announcing in the same frame
     *  cannot draw the same file. Per instance, not a function-local static: a static
     *  would be shared across every soundscape actor in the process, including the ones
     *  a PIE session creates alongside the editor world. */
    uint32 OneShotCounter = 0;
    bool   bTimeOfDayBound = false;
};

