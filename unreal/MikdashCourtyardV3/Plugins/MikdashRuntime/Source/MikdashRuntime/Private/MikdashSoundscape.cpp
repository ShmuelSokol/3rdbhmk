// =============================================================================
// MikdashSoundscape.cpp
//
// The thin half. Every decision worth arguing about lives in the engine-free
// namespace at the top of MikdashSoundscape.h and is tested by
// Plugins/MikdashRuntime/Tests/SoundscapeMathTest.cpp. This file only moves the
// numbers that namespace produces onto UAudioComponents.
//
// Two deliberate choices are worth reading before changing anything here.
//
// 1. THE BIRD FLOCK IS BOUND REFLECTIVELY, not by including MikdashBirdFlock.h.
//    That module is owned by someone else and is under active change. Looking its
//    OnBirdSound multicast delegate up by name, checking its signature, and adding
//    a script delegate means this file compiles and links whatever they do to
//    theirs, and degrades to "no bird sounds" rather than to a build break. The
//    hook itself is their documented contract (see FMikdashBirdSoundSignature in
//    MikdashBirdFlock.h): the flock module plays no audio and only announces that
//    a call, wingburst, startle or landing happened.
//
// 2. REVERB IS A SUBMIX SEND, NOT AN AUDIOVOLUME. See
//    SourceAssets/soundscape-review/SoundscapeV2/FINDING-AudioVolume-brush.md. A
//    Python-spawned AAudioVolume does get a real brush in UE 5.8, but only as a
//    side effect of the placement path running an actor factory, and the failure
//    mode is a silently zero-sized volume. The zone table on this actor needs no
//    BSP at all, works the same in a packaged build, and can be read back as a
//    number. Where the volume does build, it is placed too and the two agree.
// =============================================================================

#include "MikdashSoundscape.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/AudioComponent.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "MikdashTimeOfDay.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundSubmix.h"
#include "UObject/UnrealType.h"

namespace
{
using namespace MikdashSoundscape;

/** The reflected enum and the engine-free enum must stay in step; the actor casts
 *  one straight to the other. */
static_assert(static_cast<int>(EMikdashSoundLayer::WindBed)      == static_cast<int>(ELayer::WindBed),      "layer order drift");
static_assert(static_cast<int>(EMikdashSoundLayer::WindGust)     == static_cast<int>(ELayer::WindGust),     "layer order drift");
static_assert(static_cast<int>(EMikdashSoundLayer::CrowdCourt)   == static_cast<int>(ELayer::CrowdCourt),   "layer order drift");
static_assert(static_cast<int>(EMikdashSoundLayer::CrowdDistant) == static_cast<int>(ELayer::CrowdDistant), "layer order drift");
static_assert(static_cast<int>(EMikdashSoundLayer::City)         == static_cast<int>(ELayer::City),         "layer order drift");
static_assert(static_cast<int>(EMikdashSoundLayer::Bird)         == static_cast<int>(ELayer::Bird),         "layer order drift");
static_assert(static_cast<int>(EMikdashSoundLayer::Service)      == static_cast<int>(ELayer::Service),      "layer order drift");
static_assert(static_cast<int>(EMikdashSoundLayer::Footstep)     == static_cast<int>(ELayer::Footstep),     "layer order drift");
static_assert(static_cast<int>(EMikdashSoundLayer::Foliage)      == static_cast<int>(ELayer::Foliage),      "layer order drift");
static_assert(static_cast<int>(EMikdashSoundLayer::Cloth)        == static_cast<int>(ELayer::Cloth),        "layer order drift");

constexpr double FallbackTakeSeconds = 30.0;

/** A USoundWave that is itself flagged looping reports an enormous duration. Nothing
 *  in this pass ships such an asset, but a hand-edited one must not become an
 *  emitter that never advances to its next take. */
double SafeDuration(const USoundBase* Sound)
{
    if (!Sound) return FallbackTakeSeconds;
    const double D = static_cast<double>(Sound->GetDuration());
    if (!MikdashSoundscape::Finite(D) || D <= 0.05 || D > 36000.0) return FallbackTakeSeconds;
    return D;
}

ELayer ToNative(EMikdashSoundLayer L)
{
    const int I = static_cast<int>(L);
    return (I >= 0 && I < LayerCount) ? static_cast<ELayer>(I) : ELayer::WindBed;
}

/** True when a multicast delegate property carries the four-parameter bird-sound
 *  signature this actor's handler expects. Binding to a delegate whose signature has
 *  drifted would feed the handler a mismatched parameter buffer, so the shape is
 *  checked and a mismatch is skipped rather than risked. */
bool SignatureLooksLikeBirdSound(const FMulticastDelegateProperty* Prop)
{
    if (!Prop || !Prop->SignatureFunction) return false;
    int32 ParamCount = 0;
    bool bNameFirst = false, bNameSecond = false, bVector = false, bFloat = false;
    for (TFieldIterator<FProperty> It(Prop->SignatureFunction); It && (It->PropertyFlags & CPF_Parm); ++It)
    {
        const FProperty* P = *It;
        if (P->PropertyFlags & CPF_ReturnParm) return false;
        if (ParamCount == 0) bNameFirst = P->IsA<FNameProperty>();
        if (ParamCount == 1) bNameSecond = P->IsA<FNameProperty>();
        if (ParamCount == 2)
        {
            const FStructProperty* S = CastField<FStructProperty>(P);
            bVector = S && S->Struct && S->Struct->GetFName() == NAME_Vector;
        }
        if (ParamCount == 3) bFloat = P->IsA<FFloatProperty>() || P->IsA<FDoubleProperty>();
        ++ParamCount;
    }
    return ParamCount == 4 && bNameFirst && bNameSecond && bVector && bFloat;
}

}   // namespace

// ---------------------------------------------------------------------------

AMikdashSoundscape::AMikdashSoundscape()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bStartWithTickEnabled = true;

    USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    Root->SetMobility(EComponentMobility::Static);
    SetRootComponent(Root);

    for (int32 I = 0; I < MikdashSoundscape::LayerCount; ++I)
    {
        LayerGains[I] = 0.0;
    }
}

// ---------------------------------------------------------------------------
// lifetime
// ---------------------------------------------------------------------------

void AMikdashSoundscape::BeginPlay()
{
    Super::BeginPlay();
    BindTimeOfDay();
    RebuildEmitters();
    if (bBindBirdFlocks)
    {
        BindBirdFlocks();
    }
}

void AMikdashSoundscape::EndPlay(const EEndPlayReason::Type Reason)
{
    if (bTimeOfDayBound && TimeOfDay)
    {
        TimeOfDay->OnTimeOfDayChanged.RemoveDynamic(this, &AMikdashSoundscape::HandleTimeOfDayChanged);
    }
    bTimeOfDayBound = false;

    // Unbind from every flock that was bound reflectively. A stale script delegate on
    // a surviving actor would call into a destroyed listener.
    if (UWorld* World = GetWorld())
    {
        FScriptDelegate Delegate;
        Delegate.BindUFunction(this, GET_FUNCTION_NAME_CHECKED(AMikdashSoundscape, HandleBirdSound));
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            AActor* Actor = *It;
            if (!IsValid(Actor)) continue;
            FMulticastDelegateProperty* Prop =
                FindFProperty<FMulticastDelegateProperty>(Actor->GetClass(), TEXT("OnBirdSound"));
            if (!Prop) continue;
            Prop->RemoveDelegate(Delegate, Actor);
        }
    }

    DestroyComponents();
    Super::EndPlay(Reason);
}

void AMikdashSoundscape::DestroyComponents()
{
    for (TObjectPtr<UAudioComponent>& C : Components)
    {
        if (C)
        {
            C->Stop();
            C->DestroyComponent();
        }
    }
    Components.Reset();
    for (TObjectPtr<UAudioComponent>& C : OneShots)
    {
        if (C)
        {
            C->Stop();
            C->DestroyComponent();
        }
    }
    OneShots.Reset();
    Runtime.Reset();
}

void AMikdashSoundscape::RebuildEmitters()
{
    DestroyComponents();

    const int32 Count = Emitters.Num();
    Runtime.SetNum(Count);
    Components.SetNum(Count * 2);

    for (int32 I = 0; I < Count; ++I)
    {
        FEmitterRuntime& R = Runtime[I];
        R.Index = I;
        R.Pass = 0;
        R.PreviousSource = -1;
        R.ActiveSlot = 0;
        R.SlotEnvelope[0] = 0.0;
        R.SlotEnvelope[1] = 0.0;
        R.SmoothedGain = 0.0;
        R.OcclusionFraction = 0.0;
        R.bSounding = false;

        // Draw pass zero now so every emitter starts at a different point in its own
        // silence. Without this the whole soundscape fires together at BeginPlay,
        // which is the single most recognisable "this is a loop" moment there is.
        const MikdashSoundscape::EmitterSchedule S = ScheduleFor(I);
        R.Pending = MikdashSoundscape::NextEvent(S, R.Pass, R.PreviousSource, 1.0);
        R.PreviousSource = R.Pending.SourceIndex;
        R.CountdownSeconds = R.Pending.GapSeconds
            * MikdashSoundscape::Hash01(static_cast<uint32>(Seed), static_cast<uint32>(I), 0u, 77u);
    }

    UpdateAccumulator = 0.0;
    OcclusionCursor = 0;
    Acoustics = MikdashSoundscape::Acoustic();
    CurrentZoneLabel = NAME_None;
}

// ---------------------------------------------------------------------------
// binding
// ---------------------------------------------------------------------------

void AMikdashSoundscape::BindTimeOfDay()
{
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
    if (TimeOfDay && !bTimeOfDayBound)
    {
        TimeOfDay->OnTimeOfDayChanged.AddDynamic(this, &AMikdashSoundscape::HandleTimeOfDayChanged);
        bTimeOfDayBound = true;
        CachedHours = static_cast<double>(TimeOfDay->GetTimeOfDayHours());
    }
    else if (!TimeOfDay)
    {
        CachedHours = static_cast<double>(FallbackHours);
    }
}

void AMikdashSoundscape::BindBirdFlocks()
{
    UWorld* World = GetWorld();
    if (!World) return;

    FScriptDelegate Delegate;
    Delegate.BindUFunction(this, GET_FUNCTION_NAME_CHECKED(AMikdashSoundscape, HandleBirdSound));

    int32 Bound = 0;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (!IsValid(Actor)) continue;
        FMulticastDelegateProperty* Prop =
            FindFProperty<FMulticastDelegateProperty>(Actor->GetClass(), TEXT("OnBirdSound"));
        if (!Prop) continue;
        if (!SignatureLooksLikeBirdSound(Prop))
        {
            UE_LOG(LogTemp, Warning,
                   TEXT("MikdashSoundscape: %s exposes OnBirdSound with an unexpected signature; "
                        "not binding. Birds will fly silently."),
                   *Actor->GetName());
            continue;
        }
        Prop->AddDelegate(Delegate, Actor);
        ++Bound;
    }
    UE_LOG(LogTemp, Log, TEXT("MikdashSoundscape: bound the bird-sound hook on %d flock actor(s)."), Bound);
}

// ---------------------------------------------------------------------------
// tick
// ---------------------------------------------------------------------------

void AMikdashSoundscape::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);

    const double Dt = FMath::Clamp(static_cast<double>(DeltaSeconds), 0.0, 0.25);
    if (Dt <= 0.0) return;

    BirdSoundBudget = FMath::Min(BirdSoundBudget + Dt * FMath::Max(0.f, MaxBirdSoundsPerSecond),
                                 static_cast<double>(FMath::Max(1.f, MaxBirdSoundsPerSecond)));

    UpdateAccumulator += Dt;
    const double Interval = FMath::Max(0.02, static_cast<double>(UpdateIntervalSeconds));
    if (UpdateAccumulator < Interval) return;
    const double Step = UpdateAccumulator;
    UpdateAccumulator = 0.0;

    FVector Listener = FVector::ZeroVector;
    const bool bHaveListener = GetListenerLocation(Listener);

    PruneOneShots();
    UpdateAcoustics(Listener, Step);
    if (bHaveListener)
    {
        UpdateOcclusion(Listener);
    }
    UpdateScheduler(Listener, Step);
}

bool AMikdashSoundscape::GetListenerLocation(FVector& OutCm) const
{
    if (const APlayerCameraManager* Cam = UGameplayStatics::GetPlayerCameraManager(this, 0))
    {
        OutCm = Cam->GetCameraLocation();
        return true;
    }
    if (const APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0))
    {
        OutCm = Pawn->GetActorLocation();
        return true;
    }
    return false;
}

double AMikdashSoundscape::CurrentHours() const
{
    if (TimeOfDay)
    {
        return static_cast<double>(TimeOfDay->GetTimeOfDayHours());
    }
    return static_cast<double>(FallbackHours);
}

MikdashSoundscape::DayAnchors AMikdashSoundscape::CurrentAnchors() const
{
    MikdashSoundscape::DayAnchors A;
    if (TimeOfDay)
    {
        A.CivilDawnHours = static_cast<double>(TimeOfDay->GetCivilDawnHours());
        A.SunriseHours   = static_cast<double>(TimeOfDay->GetSunriseHours());
        A.SolarNoonHours = static_cast<double>(TimeOfDay->GetSolarNoonHours());
        A.SunsetHours    = static_cast<double>(TimeOfDay->GetSunsetHours());
        A.CivilDuskHours = static_cast<double>(TimeOfDay->GetCivilDuskHours());
    }
    // An unusable set (a polar date, or an actor that has not computed yet) is caught
    // inside AnchorCoordinate, which substitutes DefaultAnchors().
    return A;
}

void AMikdashSoundscape::HandleTimeOfDayChanged(float NewTimeOfDayHours, float /*SunAltitudeDegrees*/)
{
    CachedHours = static_cast<double>(NewTimeOfDayHours);
}

// ---------------------------------------------------------------------------
// zones
// ---------------------------------------------------------------------------

void AMikdashSoundscape::UpdateAcoustics(const FVector& ListenerCm, double DeltaSeconds)
{
    MikdashSoundscape::Acoustic Target;   // outdoors: open, dry, fully exposed
    FName TargetLabel = NAME_None;

    if (Zones.Num() > 0)
    {
        TArray<MikdashSoundscape::Zone, TInlineAllocator<8>> Native;
        Native.Reserve(Zones.Num());
        TArray<FName, TInlineAllocator<8>> Labels;
        Labels.Reserve(Zones.Num());
        for (const FMikdashAcousticZone& Z : Zones)
        {
            MikdashSoundscape::Zone N;
            N.Bounds.MinCm[0] = Z.MinCm.X; N.Bounds.MinCm[1] = Z.MinCm.Y; N.Bounds.MinCm[2] = Z.MinCm.Z;
            N.Bounds.MaxCm[0] = Z.MaxCm.X; N.Bounds.MaxCm[1] = Z.MaxCm.Y; N.Bounds.MaxCm[2] = Z.MaxCm.Z;
            N.BlendMarginCm = Z.BlendMarginCm;
            N.Priority = Z.Priority;
            N.Inside.DryGain = Z.DryGain;
            N.Inside.LpfHz = Z.LowPassHz;
            N.Inside.ReverbSend = Z.ReverbSend;
            N.Inside.Exposure = Z.Exposure;
            Native.Add(N);
            Labels.Add(Z.Label);
        }
        const double P[3] = {ListenerCm.X, ListenerCm.Y, ListenerCm.Z};
        Target = MikdashSoundscape::EvaluateZones(Native.GetData(),
                                                  static_cast<SIZE_T>(Native.Num()), P,
                                                  MikdashSoundscape::Acoustic());

        // Report the zone the listener is most inside, for the overlay and the receipt.
        double BestWeight = 0.0;
        int32 BestPriority = MIN_int32;
        for (int32 I = 0; I < Native.Num(); ++I)
        {
            const double W = MikdashSoundscape::BoxMembership(Native[I].Bounds, P,
                                                              Native[I].BlendMarginCm);
            if (W <= 0.0) continue;
            if (Native[I].Priority > BestPriority
                || (Native[I].Priority == BestPriority && W > BestWeight))
            {
                BestPriority = Native[I].Priority;
                BestWeight = W;
                TargetLabel = Labels[I];
            }
        }
    }

    const double Tau = FMath::Max(0.01, static_cast<double>(ZoneBlendSeconds));
    Acoustics.DryGain    = MikdashSoundscape::SmoothTowards(Acoustics.DryGain,    Target.DryGain,    DeltaSeconds, Tau);
    Acoustics.ReverbSend = MikdashSoundscape::SmoothTowards(Acoustics.ReverbSend, Target.ReverbSend, DeltaSeconds, Tau);
    Acoustics.Exposure   = MikdashSoundscape::SmoothTowards(Acoustics.Exposure,   Target.Exposure,   DeltaSeconds, Tau);
    // The filter is smoothed in log-frequency for the same reason it is blended there.
    {
        const double A = FMath::Loge(FMath::Max(Acoustics.LpfHz, 20.0));
        const double B = FMath::Loge(FMath::Max(Target.LpfHz, 20.0));
        Acoustics.LpfHz = FMath::Exp(MikdashSoundscape::SmoothTowards(A, B, DeltaSeconds, Tau));
    }
    CurrentZoneLabel = TargetLabel;
}

void AMikdashSoundscape::ApplyAcousticsTo(UAudioComponent* Component) const
{
    if (!Component) return;
    const bool bFiltered = Acoustics.LpfHz < MikdashSoundscape::LpfOpenHz * 0.98;
    Component->SetLowPassFilterEnabled(bFiltered);
    if (bFiltered)
    {
        Component->SetLowPassFilterFrequency(static_cast<float>(Acoustics.LpfHz));
    }
    if (ReverbSubmix)
    {
        Component->SetSubmixSend(ReverbSubmix, static_cast<float>(Acoustics.ReverbSend));
    }
}

// ---------------------------------------------------------------------------
// occlusion
// ---------------------------------------------------------------------------

void AMikdashSoundscape::UpdateOcclusion(const FVector& ListenerCm)
{
    UWorld* World = GetWorld();
    if (!World || Emitters.Num() == 0) return;
    const int32 Budget = FMath::Clamp(OcclusionTracesPerUpdate, 0, Emitters.Num());
    if (Budget == 0) return;

    FCollisionQueryParams Params(FName(TEXT("MikdashSoundscapeOcclusion")), false, this);
    Params.bTraceComplex = false;

    for (int32 N = 0; N < Budget; ++N)
    {
        OcclusionCursor = (OcclusionCursor + 1) % Emitters.Num();
        const int32 I = OcclusionCursor;
        if (!Runtime.IsValidIndex(I)) continue;
        if (!Emitters[I].bOcclude)
        {
            Runtime[I].OcclusionFraction = 0.0;
            continue;
        }
        const bool bBlocked = World->LineTraceTestByChannel(
            Emitters[I].LocationCm, ListenerCm, ECC_Visibility, Params);
        // One ray is a binary answer; smoothing it over successive visits turns it into
        // a fraction, which is what the occlusion curve wants. A wall the listener is
        // walking past therefore fades rather than snapping.
        const double Target = bBlocked ? 1.0 : 0.0;
        Runtime[I].OcclusionFraction =
            MikdashSoundscape::Lerp(Runtime[I].OcclusionFraction, Target, 0.35);
    }
}

// ---------------------------------------------------------------------------
// scheduling
// ---------------------------------------------------------------------------

MikdashSoundscape::EmitterSchedule AMikdashSoundscape::ScheduleFor(int32 Index) const
{
    MikdashSoundscape::EmitterSchedule S;
    if (!Emitters.IsValidIndex(Index)) return S;
    const FMikdashSoundEmitter& E = Emitters[Index];
    S.Seed = static_cast<uint32>(Seed);
    S.EmitterId = static_cast<uint32>(Index + 1);
    S.SourceCount = FMath::Max(1, E.Sources.Num());
    S.MinGapSeconds = E.MinGapSeconds;
    S.MaxGapSeconds = FMath::Max(E.MinGapSeconds, E.MaxGapSeconds);
    S.MinPitch = E.MinPitch;
    S.MaxPitch = FMath::Max(E.MinPitch, E.MaxPitch);
    S.MinLevel = E.MinLevel;
    S.MaxLevel = FMath::Max(E.MinLevel, E.MaxLevel);
    S.bLooping = E.bLooping;
    return S;
}

double AMikdashSoundscape::TargetGainFor(int32 Index, const FVector& ListenerCm,
                                         double EventLevel) const
{
    if (!Emitters.IsValidIndex(Index)) return 0.0;
    const FMikdashSoundEmitter& E = Emitters[Index];
    const MikdashSoundscape::ELayer Layer = ToNative(E.Layer);
    const MikdashSoundscape::DayAnchors A = CurrentAnchors();
    const double Hours = CurrentHours();

    MikdashSoundscape::GainInputs In;
    In.Layer = Layer;
    In.BaseVolume = E.BaseVolume;
    In.EventLevel = EventLevel;
    In.DayGain = MikdashSoundscape::LayerGainAtTime(Layer, A, Hours);
    In.UserMixGain = MasterVolume;
    In.ZoneDryGain = Acoustics.DryGain;
    In.Occlusion = Runtime.IsValidIndex(Index)
        ? MikdashSoundscape::OcclusionGain(Runtime[Index].OcclusionFraction,
                                           MaxOcclusionAttenuationDb)
        : 1.0;

    if (E.bHeightVarying)
    {
        if (Layer == MikdashSoundscape::ELayer::City)
        {
            In.HeightGain = MikdashSoundscape::CityGainFromHeight(
                ListenerCm.Z, PlazaZCm, SummitZCm);
        }
        else
        {
            In.HeightGain = MikdashSoundscape::WindGainFromHeight(
                ListenerCm.Z, GroundZCm, Acoustics.Exposure);
        }
    }

    if (E.bCrowdScaled)
    {
        const double Crowd = MikdashSoundscape::CrowdMurmurGain(
            CrowdHeadCount, CrowdReferenceCount, 1.0);
        const double Voices = MikdashSoundscape::SpeakingVoiceGain(SpeakingResidentCount, 24);
        // The head count sets the bed; the speaking residents lift it a little. A court
        // with nobody in it is silent, which is the whole point at dawn.
        In.HeightGain *= MikdashSoundscape::Clamp(Crowd + 0.25 * Voices, 0.0, 1.25);
    }

    return MikdashSoundscape::CombineGain(In);
}

void AMikdashSoundscape::UpdateScheduler(const FVector& ListenerCm, double DeltaSeconds)
{
    const MikdashSoundscape::DayAnchors A = CurrentAnchors();
    const double Hours = CurrentHours();
    const double FadeTau = FMath::Max(0.02, static_cast<double>(CrossfadeSeconds) / 3.0);

    double LayerAccum[MikdashSoundscape::LayerCount] = {};

    for (int32 I = 0; I < Emitters.Num() && I < Runtime.Num(); ++I)
    {
        const FMikdashSoundEmitter& E = Emitters[I];
        FEmitterRuntime& R = Runtime[I];
        const MikdashSoundscape::ELayer Layer = ToNative(E.Layer);

        R.CountdownSeconds -= DeltaSeconds;
        if (R.CountdownSeconds <= 0.0)
        {
            if (R.bSounding)
            {
                // The take has run out. Draw the next pass; its gap is the silence that
                // follows. Looping beds have a zero gap, so the next take starts
                // immediately and overlaps the tail of this one.
                R.Pass += 1;
                const MikdashSoundscape::EmitterSchedule S = ScheduleFor(I);
                const double Scale = MikdashSoundscape::LayerIntervalScaleAtTime(Layer, A, Hours);
                R.Pending = MikdashSoundscape::NextEvent(S, R.Pass, R.PreviousSource, Scale);
                R.PreviousSource = R.Pending.SourceIndex;
                R.CountdownSeconds = R.Pending.GapSeconds;
                R.bSounding = false;
                if (R.Pending.GapSeconds <= 0.0)
                {
                    StartEvent(I, R.Pending);
                    R.bSounding = true;
                }
            }
            else
            {
                StartEvent(I, R.Pending);
                R.bSounding = true;
            }
        }

        // ---- gain ----
        const double Target = R.bSounding ? TargetGainFor(I, ListenerCm, R.Pending.Level) : 0.0;
        R.SmoothedGain = MikdashSoundscape::SmoothTowards(R.SmoothedGain, Target,
                                                          DeltaSeconds, FadeTau);
        const int32 Other = 1 - R.ActiveSlot;
        R.SlotEnvelope[R.ActiveSlot] =
            MikdashSoundscape::SmoothTowards(R.SlotEnvelope[R.ActiveSlot], R.bSounding ? 1.0 : 0.0,
                                             DeltaSeconds, FadeTau);
        R.SlotEnvelope[Other] =
            MikdashSoundscape::SmoothTowards(R.SlotEnvelope[Other], 0.0, DeltaSeconds, FadeTau);

        for (int32 Slot = 0; Slot < 2; ++Slot)
        {
            UAudioComponent* C = Components.IsValidIndex(I * 2 + Slot) ? Components[I * 2 + Slot].Get()
                                                                      : nullptr;
            if (!C) continue;
            const double Gain = R.SmoothedGain * R.SlotEnvelope[Slot];
            const bool bWasPlaying = C->IsPlaying();
            if (!MikdashSoundscape::ShouldBeAudible(Gain, bWasPlaying))
            {
                if (bWasPlaying) C->Stop();
                continue;
            }
            if (!bWasPlaying)
            {
                // Audible again after being stopped for cost. Resuming from sample zero
                // would put a recognisable restart in the middle of a bed, so the take
                // is resumed at a hashed offset instead.
                if (USoundBase* Sound = C->Sound)
                {
                    const double Length = SafeDuration(Sound);
                    const double Offset = Length * MikdashSoundscape::Hash01(
                        static_cast<uint32>(Seed), static_cast<uint32>(I), R.Pass, 91u + Slot);
                    C->Play(static_cast<float>(FMath::Clamp(Offset, 0.0, Length * 0.9)));
                }
                else
                {
                    continue;
                }
            }
            C->SetVolumeMultiplier(static_cast<float>(Gain));
            ApplyAcousticsTo(C);
        }

        const int32 LayerIndex = static_cast<int32>(Layer);
        if (LayerIndex >= 0 && LayerIndex < MikdashSoundscape::LayerCount)
        {
            LayerAccum[LayerIndex] = FMath::Max(LayerAccum[LayerIndex], R.SmoothedGain);
        }
    }

    for (int32 I = 0; I < MikdashSoundscape::LayerCount; ++I)
    {
        LayerGains[I] = LayerAccum[I];
    }
}

void AMikdashSoundscape::StartEvent(int32 Index, const MikdashSoundscape::EmitterEvent& Event)
{
    if (!Emitters.IsValidIndex(Index) || !Runtime.IsValidIndex(Index)) return;
    const FMikdashSoundEmitter& E = Emitters[Index];
    FEmitterRuntime& R = Runtime[Index];

    USoundBase* Sound = E.Sources.IsValidIndex(Event.SourceIndex)
                      ? E.Sources[Event.SourceIndex].Get() : nullptr;
    if (!Sound)
    {
        // No asset for this take. Do not invent one and do not stall: wait one take
        // length and try the next pass. A missing reference must be inaudible, never a
        // substitution the listener cannot account for.
        R.CountdownSeconds = FallbackTakeSeconds;
        return;
    }

    const int32 Slot = 1 - R.ActiveSlot;
    const int32 SlotIndex = Index * 2 + Slot;
    if (!Components.IsValidIndex(SlotIndex)) return;

    UAudioComponent* C = Components[SlotIndex].Get();
    if (!C)
    {
        C = UGameplayStatics::SpawnSoundAtLocation(this, Sound, E.LocationCm, FRotator::ZeroRotator,
                                                   0.f, static_cast<float>(Event.Pitch), 0.f,
                                                   E.Attenuation, nullptr, /*bAutoDestroy=*/false);
        if (!C) return;
        C->bAllowSpatialization = true;
        C->bIsUISound = false;
        Components[SlotIndex] = C;
    }
    else
    {
        C->Stop();
        C->SetSound(Sound);
        C->SetWorldLocation(E.LocationCm);
        C->SetPitchMultiplier(static_cast<float>(Event.Pitch));
        C->SetVolumeMultiplier(0.f);
        C->Play(0.f);
    }
    ApplyAcousticsTo(C);

    R.ActiveSlot = Slot;
    R.SlotEnvelope[Slot] = FMath::Max(R.SlotEnvelope[Slot], 1.0e-3);

    // A looping bed hands over CrossfadeSeconds before its take ends, so the two takes
    // overlap and the join is a fade. A one-shot simply runs to its end.
    const double Played = MikdashSoundscape::PlayedDurationSeconds(SafeDuration(Sound), Event.Pitch);
    const double Overlap = E.bLooping ? FMath::Min(static_cast<double>(CrossfadeSeconds), Played * 0.4)
                                      : 0.0;
    R.CountdownSeconds = FMath::Max(0.1, Played - Overlap);
}

// ---------------------------------------------------------------------------
// one-shots requested by other systems
// ---------------------------------------------------------------------------

UAudioComponent* AMikdashSoundscape::SpawnOneShot(USoundBase* Sound, USoundAttenuation* Attenuation,
                                                  const FVector& LocationCm, float Volume, float Pitch)
{
    if (!Sound || Volume <= static_cast<float>(MikdashSoundscape::SilenceGain)) return nullptr;
    UAudioComponent* C = UGameplayStatics::SpawnSoundAtLocation(
        this, Sound, LocationCm, FRotator::ZeroRotator, Volume, Pitch, 0.f,
        Attenuation, nullptr, /*bAutoDestroy=*/false);
    if (!C) return nullptr;
    C->bAllowSpatialization = true;
    C->bIsUISound = false;
    ApplyAcousticsTo(C);
    OneShots.Add(C);
    return C;
}

void AMikdashSoundscape::PruneOneShots()
{
    for (int32 I = OneShots.Num() - 1; I >= 0; --I)
    {
        UAudioComponent* C = OneShots[I].Get();
        if (!C)
        {
            OneShots.RemoveAtSwap(I);
            continue;
        }
        if (!C->IsPlaying() && !C->IsActive())
        {
            C->DestroyComponent();
            OneShots.RemoveAtSwap(I);
        }
    }
}

void AMikdashSoundscape::HandleBirdSound(FName EventName, FName /*SpeciesName*/,
                                         FVector WorldLocationCm, float Intensity)
{
    if (BirdSoundBudget < 1.0) return;   // rate limit, shared across every flock

    const bool bBurst = (EventName == TEXT("Wingburst")) || (EventName == TEXT("Startle"))
                     || (EventName == TEXT("Land"));
    const TArray<TObjectPtr<USoundBase>>& Bank = bBurst ? BirdWingburstSounds : BirdCallSounds;
    if (Bank.Num() == 0) return;

    const MikdashSoundscape::DayAnchors A = CurrentAnchors();
    const double Day = MikdashSoundscape::LayerGainAtTime(MikdashSoundscape::ELayer::Bird,
                                                          A, CurrentHours());
    // At night the flock still flies and still announces; it is simply not heard.
    if (Day <= MikdashSoundscape::SilenceGain * 4.0) return;

    // Draw from the bank by hashing the event, so two flocks announcing in the same
    // frame do not pick the same file.
    const double Spread = FMath::Clamp(
        FMath::Abs(WorldLocationCm.X) + FMath::Abs(WorldLocationCm.Y), 0.0, 4.0e9);
    const uint32 Salt = GetTypeHash(EventName)
                      ^ static_cast<uint32>(FMath::IsFinite(Spread) ? Spread : 0.0);
    ++OneShotCounter;
    const int32 Pick = static_cast<int32>(
        MikdashSoundscape::Hash(static_cast<uint32>(Seed), Salt, OneShotCounter, 41u)
        % static_cast<uint32>(Bank.Num()));

    const double Level = MikdashSoundscape::Clamp(
        Day * MasterVolume * Acoustics.DryGain
        * (bBurst ? MikdashSoundscape::Clamp(0.4 + 0.1 * Intensity, 0.4, 1.0) : 0.85),
        0.0, 2.0);
    const double Pitch = MikdashSoundscape::HashRange(static_cast<uint32>(Seed), Salt,
                                                      OneShotCounter, 42u, 0.92, 1.08);

    if (SpawnOneShot(Bank[Pick].Get(), BirdAttenuation, WorldLocationCm,
                     static_cast<float>(Level), static_cast<float>(Pitch)))
    {
        BirdSoundBudget -= 1.0;
    }
}

void AMikdashSoundscape::PlayFootstep(int32 Bank, FVector WorldLocationCm, float Level)
{
    // Bank 0 = stone, 1 = soft, matching MikdashSurfaceAudio::Bank minus Silent. The
    // SURFACE decision is not made here: MikdashSurfaceAudioRouting.h already routes a
    // floor mesh path to a bank, and duplicating that would be a second opinion nobody
    // asked for.
    const TArray<TObjectPtr<USoundBase>>& Set = (Bank == 1) ? FootstepSoftSounds : FootstepStoneSounds;
    if (Set.Num() == 0) return;

    ++OneShotCounter;
    const int32 Pick = static_cast<int32>(
        MikdashSoundscape::Hash(static_cast<uint32>(Seed), 909u, OneShotCounter, 51u)
        % static_cast<uint32>(Set.Num()));
    const double Pitch = MikdashSoundscape::HashRange(static_cast<uint32>(Seed), 909u,
                                                      OneShotCounter, 52u, 0.94, 1.06);
    SpawnOneShot(Set[Pick].Get(), FootstepAttenuation, WorldLocationCm,
                 static_cast<float>(MikdashSoundscape::Clamp(Level * MasterVolume, 0.0, 2.0)),
                 static_cast<float>(Pitch));
}

void AMikdashSoundscape::PlayServiceSound(FName EventName, FVector WorldLocationCm, float Level)
{
    if (ServiceSounds.Num() == 0) return;
    const MikdashSoundscape::DayAnchors A = CurrentAnchors();
    const double Day = MikdashSoundscape::LayerGainAtTime(MikdashSoundscape::ELayer::Service,
                                                          A, CurrentHours());
    if (Day <= MikdashSoundscape::SilenceGain * 4.0) return;

    ++OneShotCounter;
    const uint32 Salt = GetTypeHash(EventName);
    const int32 Pick = static_cast<int32>(
        MikdashSoundscape::Hash(static_cast<uint32>(Seed), Salt, OneShotCounter, 61u)
        % static_cast<uint32>(ServiceSounds.Num()));
    const double Pitch = MikdashSoundscape::HashRange(static_cast<uint32>(Seed), Salt,
                                                      OneShotCounter, 62u, 0.97, 1.03);
    SpawnOneShot(ServiceSounds[Pick].Get(), ServiceAttenuation, WorldLocationCm,
                 static_cast<float>(MikdashSoundscape::Clamp(Level * Day * MasterVolume, 0.0, 2.0)),
                 static_cast<float>(Pitch));
}

// ---------------------------------------------------------------------------
// readback
// ---------------------------------------------------------------------------

void AMikdashSoundscape::SetMasterVolume(float NewVolume)
{
    MasterVolume = FMath::Clamp(NewVolume, 0.f, 4.f);
}

float AMikdashSoundscape::GetLayerGain(EMikdashSoundLayer Layer) const
{
    const int32 I = static_cast<int32>(Layer);
    if (I < 0 || I >= MikdashSoundscape::LayerCount) return 0.f;
    return static_cast<float>(LayerGains[I]);
}

int32 AMikdashSoundscape::GetActiveEmitterCount() const
{
    int32 N = 0;
    for (const TObjectPtr<UAudioComponent>& C : Components)
    {
        if (C && C->IsPlaying()) ++N;
    }
    return N;
}

FString AMikdashSoundscape::DescribeState() const
{
    FString LayerText;
    for (int32 I = 0; I < MikdashSoundscape::LayerCount; ++I)
    {
        LayerText += FString::Printf(TEXT("%s%s=%.3f"), I == 0 ? TEXT("") : TEXT(" "),
                                  ANSI_TO_TCHAR(MikdashSoundscape::LayerName(
                                      static_cast<MikdashSoundscape::ELayer>(I))),
                                  LayerGains[I]);
    }
    return FString::Printf(
        TEXT("MikdashSoundscape %02.0f:%02.0f zone=%s dry=%.3f lpf=%.0fHz wet=%.3f exposure=%.2f ")
        TEXT("emitters=%d/%d voices=%d crowd=%.0f speaking=%d | %s"),
        FMath::Floor(CurrentHours()), FMath::Fmod(CurrentHours(), 1.0) * 60.0,
        *CurrentZoneLabel.ToString(), Acoustics.DryGain, Acoustics.LpfHz, Acoustics.ReverbSend,
        Acoustics.Exposure, GetActiveEmitterCount(), Emitters.Num(), OneShots.Num(),
        CrowdHeadCount, SpeakingResidentCount, *LayerText);
}
