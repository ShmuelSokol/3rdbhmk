#pragma once

// =============================================================================
// SoundscapeMath.h
//
// The engine-independent half of the soundscape, split out of MikdashSoundscape.h
// so that UnrealHeaderTool sees an unconditional header while the standalone test
// can still compile this half with no Unreal in sight.
//
//   1. namespace MikdashSoundscape -- engine-independent. No Unreal types, no
//      globals, no I/O, no std::rand. Every random draw is a pure integer hash of
//      (Seed, Emitter, Pass, Lane), so the schedule a listener hears in a packaged
//      build is bit-identical to the one Scripts/create_soundscape_v2.py prints
//      offline and to the one Plugins/MikdashRuntime/Tests/SoundscapeMathTest.cpp
//      asserts on.
//
//   2. AMikdashSoundscape -- the actor. It owns one UAudioComponent per emitter,
//      asks the namespace above what should be playing and how loud, and does
//      nothing else. All of the judgement lives in the engine-free half so it can
//      be tested without launching the editor.
//
// The standalone test compiles ONLY the first half, by defining
// MIKDASH_SOUNDSCAPE_MATH_ONLY before including this header. UnrealHeaderTool
// never defines it, so the engine half is always visible to UHT.
//
// Units: centimetres, degrees, seconds, linear gain (not dB) unless a name says
// otherwise. World frame is Unreal's: +X east, +Y south, +Z up.
//
// WHY THIS EXISTS AT ALL. The first ambience pass was rejected as "just a loop of
// some white noise and birds and banging". A USoundCue built from Python could not
// fix that honestly: USoundCue::AllNodes and SoundCueGraph are plain UPROPERTY()
// with neither CPF_Edit nor CPF_BlueprintVisible, so a Python-built cue plays but
// opens empty in the Sound Cue Editor and is destroyed the moment anyone saves it
// there. Moving the randomisation into C++ removes that trap completely: the
// emitters below reference plain USoundWave assets and this actor decides, every
// pass, which take plays, after what silence, at what pitch and at what level.
// There is no cue graph to corrupt and no fixed period to find.
// =============================================================================

// -----------------------------------------------------------------------------
// PART 1 -- engine-independent
// -----------------------------------------------------------------------------
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>

namespace MikdashSoundscape
{
constexpr double Pi = 3.14159265358979323846;

/** Silence floor. Below this a layer is treated as off and its component is stopped,
 *  so an inaudible emitter costs no voice. -60 dB. */
constexpr double SilenceGain = 0.001;

/** The full audible band. Used as "filter open"; the engine bypasses at 20 kHz. */
constexpr double LpfOpenHz = 20000.0;

// ---------------------------------------------------------------------------
// Layers
// ---------------------------------------------------------------------------
/** One entry per acoustic role. The order is part of the saved receipt, so new
 *  layers are appended, never inserted. */
enum class ELayer : int
{
    WindBed = 0,     ///< the continuous air over the Mount; the only never-absent layer
    WindGust,        ///< isolated gusts, silence between them
    CrowdCourt,      ///< the murmur of the instanced crowd standing in the courts
    CrowdDistant,    ///< voices carrying up from the plaza and the city edge
    City,            ///< modern Jerusalem below: traffic, buses, the light rail
    Bird,            ///< driven by AMikdashBirdFlock's OnBirdSound hook, not by a timer
    Service,         ///< the sounds of the service itself
    Footstep,        ///< one-shots requested by whoever owns locomotion; never self-timed
    Foliage,         ///< trees off the Mount, on the slopes
    Cloth,           ///< curtain and garment movement at the gates and the Ulam
    Count
};
constexpr int LayerCount = static_cast<int>(ELayer::Count);

inline const char* LayerName(ELayer L)
{
    switch (L)
    {
    case ELayer::WindBed:      return "WindBed";
    case ELayer::WindGust:     return "WindGust";
    case ELayer::CrowdCourt:   return "CrowdCourt";
    case ELayer::CrowdDistant: return "CrowdDistant";
    case ELayer::City:         return "City";
    case ELayer::Bird:         return "Bird";
    case ELayer::Service:      return "Service";
    case ELayer::Footstep:     return "Footstep";
    case ELayer::Foliage:      return "Foliage";
    case ELayer::Cloth:        return "Cloth";
    default:                   return "Unknown";
    }
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------
inline bool Finite(double V) { return V == V && V > -1.0e300 && V < 1.0e300; }
/** NaN clamps to Lo. Without this Clamp(NaN, 0, 1) returns NaN -- both comparisons are
 *  false -- and one NaN anywhere in the graph silences or detonates the whole mix. */
inline double Clamp(double V, double Lo, double Hi)
{
    if (V != V) return Lo;
    return V < Lo ? Lo : (V > Hi ? Hi : V);
}
inline double Saturate(double V) { return Clamp(V, 0.0, 1.0); }
inline double Lerp(double A, double B, double T) { return A + (B - A) * T; }

/** Smoothstep, so nothing in this file ever hard-switches. */
inline double SmoothStep(double Edge0, double Edge1, double X)
{
    if (!Finite(Edge0) || !Finite(Edge1) || !Finite(X)) return 0.0;
    if (Edge1 <= Edge0) return X < Edge0 ? 0.0 : 1.0;
    const double T = Saturate((X - Edge0) / (Edge1 - Edge0));
    return T * T * (3.0 - 2.0 * T);
}

inline double DbToLinear(double Db) { return std::pow(10.0, Db / 20.0); }
inline double LinearToDb(double Linear)
{
    return Linear <= 1.0e-9 ? -180.0 : 20.0 * std::log10(Linear);
}

/** Wrap into [0, 24). Accepts negatives and multiples of a day. */
inline double WrapHours(double Hours)
{
    if (!Finite(Hours)) return 0.0;
    double H = std::fmod(Hours, 24.0);
    if (H < 0.0) H += 24.0;
    return H;
}

/** Signed shortest distance from A to B on a 24 h circle, in (-12, +12]. */
inline double HourDelta(double A, double B)
{
    double D = WrapHours(B) - WrapHours(A);
    if (D > 12.0) D -= 24.0;
    if (D <= -12.0) D += 24.0;
    return D;
}

// ---------------------------------------------------------------------------
// Deterministic hash RNG
// ---------------------------------------------------------------------------
/** Integer avalanche. Same shape as MikdashScatter and MikdashFlock so a reader who
 *  has seen one has seen all three: no state, no sequence, addressable by coordinate. */
inline std::uint32_t Hash(std::uint32_t Seed, std::uint32_t Emitter, std::uint32_t Pass,
                          std::uint32_t Lane)
{
    std::uint32_t H = Seed * 0x9E3779B9u;
    H ^= Emitter + 0x85EBCA6Bu + (H << 6) + (H >> 2);
    H ^= Pass    + 0xC2B2AE35u + (H << 6) + (H >> 2);
    H ^= Lane    + 0x27D4EB2Fu + (H << 6) + (H >> 2);
    H ^= H >> 16; H *= 0x7FEB352Du;
    H ^= H >> 15; H *= 0x846CA68Bu;
    H ^= H >> 16;
    return H;
}

/** Uniform in [0, 1). */
inline double Hash01(std::uint32_t Seed, std::uint32_t Emitter, std::uint32_t Pass,
                     std::uint32_t Lane)
{
    return static_cast<double>(Hash(Seed, Emitter, Pass, Lane)) / 4294967296.0;
}

inline double HashRange(std::uint32_t Seed, std::uint32_t Emitter, std::uint32_t Pass,
                        std::uint32_t Lane, double Lo, double Hi)
{
    return Lo + (Hi - Lo) * Hash01(Seed, Emitter, Pass, Lane);
}

// ---------------------------------------------------------------------------
// Time of day
// ---------------------------------------------------------------------------
/** Real solar anchors for the current date, read straight off AMikdashTimeOfDay's
 *  BlueprintPure getters (GetCivilDawnHours, GetSunriseHours, GetSolarNoonHours,
 *  GetSunsetHours, GetCivilDuskHours). Nothing here recomputes astronomy; the
 *  soundscape is a consumer of that actor, never a second opinion on it. */
struct DayAnchors
{
    double CivilDawnHours = 5.20;
    double SunriseHours   = 5.75;
    double SolarNoonHours = 12.60;
    double SunsetHours    = 19.45;
    double CivilDuskHours = 20.00;

    /** True when the five values are finite and strictly increasing inside one day.
     *  A polar or corrupted set fails this and callers fall back to DefaultAnchors(). */
    bool IsUsable() const
    {
        if (!Finite(CivilDawnHours) || !Finite(SunriseHours) || !Finite(SolarNoonHours)
            || !Finite(SunsetHours) || !Finite(CivilDuskHours)) return false;
        if (CivilDawnHours < 0.0 || CivilDuskHours > 24.0) return false;
        return CivilDawnHours + 0.02 < SunriseHours
            && SunriseHours + 0.5 < SolarNoonHours
            && SolarNoonHours + 0.5 < SunsetHours
            && SunsetHours + 0.02 < CivilDuskHours;
    }
};

/** Jerusalem, mid-September, IDT. Only used when the live anchors are unusable. */
inline DayAnchors DefaultAnchors() { return DayAnchors(); }

/** The eight points a day is described at. Deliberately the same eight names as
 *  EMikdashTimePreset so a reader can line the two tables up. */
enum class EDayAnchor : int
{
    Night = 0,   ///< solar midnight
    CivilDawn,
    Sunrise,
    Morning,     ///< midway between sunrise and solar noon
    Midday,      ///< solar noon
    Afternoon,   ///< midway between solar noon and sunset
    Sunset,
    CivilDusk,
    Count
};
constexpr int DayAnchorCount = static_cast<int>(EDayAnchor::Count);

/** Clock hour of one anchor. Assumes the caller has already substituted
 *  DefaultAnchors() for an unusable set; AnchorCoordinate does that. */
inline double AnchorHours(const DayAnchors& A, int AnchorIndex)
{
    switch (AnchorIndex)
    {
    case 0: return WrapHours(A.SolarNoonHours - 12.0);
    case 1: return A.CivilDawnHours;
    case 2: return A.SunriseHours;
    case 3: return 0.5 * (A.SunriseHours + A.SolarNoonHours);
    case 4: return A.SolarNoonHours;
    case 5: return 0.5 * (A.SolarNoonHours + A.SunsetHours);
    case 6: return A.SunsetHours;
    case 7: return A.CivilDuskHours;
    default: return 0.0;
    }
}

/** Map a clock hour onto a continuous anchor coordinate in [0, 8).
 *
 *  This is the whole point of taking the anchors from the astronomy actor rather
 *  than hard-coding hours: dawn in December is 06:07 and in June 04:32, and the
 *  soundscape follows the sun, not the clock. */
inline double AnchorCoordinate(const DayAnchors& In, double Hours)
{
    const DayAnchors A = In.IsUsable() ? In : DefaultAnchors();
    const double H = WrapHours(Hours);

    // Walk the eight anchors in clock order from solar midnight and find the interval
    // H falls in. Each step is a positive advance on the 24 h circle.
    for (int I = 0; I < DayAnchorCount; ++I)
    {
        const double Start = AnchorHours(A, I);
        const double End   = AnchorHours(A, (I + 1) % DayAnchorCount);
        double Span = WrapHours(End - Start);
        if (Span <= 1.0e-6) Span = 1.0e-6;
        const double Into = WrapHours(H - Start);
        if (Into < Span)
        {
            return static_cast<double>(I) + Into / Span;
        }
    }
    return 0.0;   // unreachable for a usable anchor set
}

/** Circular linear interpolation of an eight-value curve at a clock hour.
 *
 *  Linear, not spline: a spline overshoots, and an overshoot on a gain curve is an
 *  audible pump at sunset. */
inline double SampleDayCurve(const double Values[DayAnchorCount], const DayAnchors& A,
                             double Hours)
{
    if (!Values) return 0.0;
    const double C = AnchorCoordinate(A, Hours);
    const int I = static_cast<int>(std::floor(C)) % DayAnchorCount;
    const int J = (I + 1) % DayAnchorCount;
    const double T = C - std::floor(C);
    const double VI = Finite(Values[I]) ? Values[I] : 0.0;
    const double VJ = Finite(Values[J]) ? Values[J] : 0.0;
    return Lerp(VI, VJ, Saturate(T));
}

/** Per-layer gain across the day.
 *
 *  Read the rows as: Night, CivilDawn, Sunrise, Morning, Midday, Afternoon, Sunset,
 *  CivilDusk. The brief was "dawn is quiet, midday is busy, night is wind and distant
 *  city", and the three rows that carry that are CrowdCourt (0.06 at civil dawn, 1.00
 *  at midday, 0.02 at night), WindBed (0.88 at night, near its highest) and City
 *  (0.30 at night: present, but far down). */
inline const double* LayerDayGainCurve(ELayer L)
{
    //                                     Night  Dawn   Sunrs  Morng  Midday Aftn   Sunset Dusk
    static const double WindBedC[]      = {0.88,  0.62,  0.52,  0.58,  0.72,  0.92,  0.80,  0.84};
    static const double WindGustC[]     = {0.95,  0.55,  0.40,  0.50,  0.70,  1.00,  0.85,  0.90};
    static const double CrowdCourtC[]   = {0.02,  0.06,  0.28,  0.85,  1.00,  0.78,  0.42,  0.12};
    static const double CrowdDistantC[] = {0.05,  0.10,  0.30,  0.70,  0.90,  0.75,  0.50,  0.22};
    static const double CityC[]         = {0.30,  0.34,  0.55,  0.90,  1.00,  0.95,  0.86,  0.55};
    static const double BirdC[]         = {0.04,  0.85,  1.00,  0.72,  0.34,  0.46,  0.78,  0.30};
    static const double ServiceC[]      = {0.00,  0.45,  1.00,  0.95,  0.70,  0.60,  0.85,  0.10};
    static const double FootstepC[]     = {1.00,  1.00,  1.00,  1.00,  1.00,  1.00,  1.00,  1.00};
    static const double FoliageC[]      = {0.85,  0.60,  0.55,  0.60,  0.75,  0.95,  0.82,  0.86};
    static const double ClothC[]        = {0.70,  0.55,  0.60,  0.85,  1.00,  0.90,  0.75,  0.62};
    switch (L)
    {
    case ELayer::WindBed:      return WindBedC;
    case ELayer::WindGust:     return WindGustC;
    case ELayer::CrowdCourt:   return CrowdCourtC;
    case ELayer::CrowdDistant: return CrowdDistantC;
    case ELayer::City:         return CityC;
    case ELayer::Bird:         return BirdC;
    case ELayer::Service:      return ServiceC;
    case ELayer::Footstep:     return FootstepC;
    case ELayer::Foliage:      return FoliageC;
    case ELayer::Cloth:        return ClothC;
    default:                   return FootstepC;
    }
}

inline double LayerGainAtTime(ELayer L, const DayAnchors& A, double Hours)
{
    return Saturate(SampleDayCurve(LayerDayGainCurve(L), A, Hours));
}

/** How much longer the silence between one-shots gets at this hour.
 *
 *  Gain alone is not enough. A bird call at 4 % volume at midnight is still a bird
 *  call every 40 seconds; what night actually sounds like is almost no birds. So the
 *  gap between events is stretched by the inverse of the day gain, clamped so a quiet
 *  layer becomes rare rather than mathematically silent. */
inline double LayerIntervalScaleAtTime(ELayer L, const DayAnchors& A, double Hours)
{
    const double G = LayerGainAtTime(L, A, Hours);
    return Clamp(1.0 / std::max(G, 0.05), 1.0, 12.0);
}

// ---------------------------------------------------------------------------
// Height and exposure
// ---------------------------------------------------------------------------
/** Wind rises with height and with how little shelter there is.
 *
 *  ExposureFraction is 0 for a listener in a colonnade or a chamber and 1 on the open
 *  platform; the actor derives it from the same zone table that drives reverb, so the
 *  two can never disagree. The height term is a log-shaped curve, not the real
 *  logarithmic wind profile -- it is chosen because it flattens, which is what stops
 *  the bed swelling absurdly when a listener stands on the highest step. */
inline double WindGainFromHeight(double Zcm, double GroundZcm, double ExposureFraction,
                                 double ShelteredFloor = 0.32)
{
    if (!Finite(Zcm) || !Finite(GroundZcm)) return ShelteredFloor;
    const double AboveM = Clamp((Zcm - GroundZcm) / 100.0, 0.0, 120.0);
    const double Open = 0.70 + 0.45 * (std::log1p(AboveM / 6.0) / std::log1p(120.0 / 6.0));
    const double Exposure = Clamp(ExposureFraction, 0.0, 1.0);
    const double Floor = Finite(ShelteredFloor) ? Clamp(ShelteredFloor, 0.0, 1.0) : 0.32;
    return Clamp(Lerp(Floor, Clamp(Open, 0.0, 1.20), Exposure), 0.0, 1.20);
}

/** The modern city fades as you climb.
 *
 *  Loud on the plaza, roughly halved on the platform, a distant presence at the top of
 *  the Ulam steps. A plain inverse-distance attenuation asset cannot express this,
 *  because the city emitters are hundreds of metres out horizontally and climbing 40 m
 *  barely changes that distance. */
inline double CityGainFromHeight(double Zcm, double PlazaZcm, double SummitZcm)
{
    if (!Finite(Zcm) || !Finite(PlazaZcm) || !Finite(SummitZcm)) return 0.5;
    if (SummitZcm <= PlazaZcm + 1.0) return 1.0;
    const double T = Saturate((Zcm - PlazaZcm) / (SummitZcm - PlazaZcm));
    // 1.0 on the plaza -> 0.34 at the summit, curving, never reaching zero: the city
    // is still there, it is just below you.
    return Clamp(1.0 - 0.66 * SmoothStep(0.0, 1.0, T), 0.30, 1.0);
}

// ---------------------------------------------------------------------------
// Acoustic zones -- reverb and occlusion
// ---------------------------------------------------------------------------
struct Box
{
    double MinCm[3] = {0.0, 0.0, 0.0};
    double MaxCm[3] = {0.0, 0.0, 0.0};

    bool IsValid() const
    {
        for (int I = 0; I < 3; ++I)
        {
            if (!Finite(MinCm[I]) || !Finite(MaxCm[I])) return false;
            if (MaxCm[I] <= MinCm[I]) return false;
        }
        return true;
    }
};

/** What a listener standing somewhere should hear applied to the outdoor mix. */
struct Acoustic
{
    double DryGain    = 1.0;         ///< multiplier on every non-local layer
    double LpfHz      = LpfOpenHz;   ///< low-pass corner; LpfOpenHz means open
    double ReverbSend = 0.0;         ///< 0..1 wet send into the stone-hall reverb
    double Exposure   = 1.0;         ///< 0 sheltered .. 1 fully open; feeds the wind curve
};

/** One acoustic region. Priority breaks overlaps; the highest priority with non-zero
 *  membership wins, and the blend margin makes the crossing continuous so there is no
 *  click at a doorway. */
struct Zone
{
    Box      Bounds;
    double   BlendMarginCm = 250.0;
    int      Priority      = 0;
    Acoustic Inside;
};

/** 1 well inside, 0 outside, smoothly interpolated across MarginCm measured INWARD
 *  from each face. The margin is taken inward rather than outward so a zone never
 *  affects a listener outside its declared bounds -- the Heikhal's acoustic must not
 *  leak into the court. */
inline double BoxMembership(const Box& B, const double P[3], double MarginCm)
{
    if (!B.IsValid() || !P) return 0.0;
    double Weight = 1.0;
    for (int I = 0; I < 3; ++I)
    {
        if (!Finite(P[I])) return 0.0;
        if (P[I] <= B.MinCm[I] || P[I] >= B.MaxCm[I]) return 0.0;
        const double Half = 0.5 * (B.MaxCm[I] - B.MinCm[I]);
        const double M = Clamp(Finite(MarginCm) ? MarginCm : 0.0, 0.0, Half);
        if (M <= 1.0e-6) continue;
        const double DistIn = std::min(P[I] - B.MinCm[I], B.MaxCm[I] - P[I]);
        Weight = std::min(Weight, SmoothStep(0.0, M, DistIn));
    }
    return Saturate(Weight);
}

/** Blend the outdoor acoustic through every zone the listener is inside, lowest
 *  priority first.
 *
 *  Layered, NOT winner-takes-all. An earlier version let the highest-priority zone mask
 *  the ones below it, and that is discontinuous: stepping into the outer few
 *  centimetres of the Heikhal's blend shell threw away the court's own figure and
 *  snapped the mix back to fully open before it started falling again. Blending
 *  upwards means the Kodesh reads as a change on top of the Heikhal, which reads as a
 *  change on top of the court, and every crossing is smooth.
 *
 *  O(n^2) in the zone count and allocation-free. There are single-digit zones. */
inline Acoustic EvaluateZones(const Zone* Zones, std::size_t Count, const double P[3],
                              const Acoustic& Outdoor)
{
    Acoustic Result = Outdoor;
    if (!Zones || Count == 0 || !P) return Result;

    int LastPriority = 0;
    bool bAnyDone = false;
    for (;;)
    {
        // Lowest priority still to be applied.
        int NextPriority = 0;
        bool bFound = false;
        for (std::size_t I = 0; I < Count; ++I)
        {
            if (bAnyDone && Zones[I].Priority <= LastPriority) continue;
            if (BoxMembership(Zones[I].Bounds, P, Zones[I].BlendMarginCm) <= 0.0) continue;
            if (!bFound || Zones[I].Priority < NextPriority)
            {
                NextPriority = Zones[I].Priority;
                bFound = true;
            }
        }
        if (!bFound) break;

        // Among the zones at that priority, the one the listener is most inside wins.
        const Zone* Best = nullptr;
        double BestWeight = 0.0;
        for (std::size_t I = 0; I < Count; ++I)
        {
            if (Zones[I].Priority != NextPriority) continue;
            const double W = BoxMembership(Zones[I].Bounds, P, Zones[I].BlendMarginCm);
            if (W > BestWeight)
            {
                BestWeight = W;
                Best = &Zones[I];
            }
        }
        if (Best)
        {
            const double W = Saturate(BestWeight);
            const double PrevLpf = Result.LpfHz;
            Result.DryGain    = Lerp(Result.DryGain,    Best->Inside.DryGain,    W);
            Result.ReverbSend = Lerp(Result.ReverbSend, Best->Inside.ReverbSend, W);
            Result.Exposure   = Lerp(Result.Exposure,   Best->Inside.Exposure,   W);
            // Interpolate the filter in log-frequency: a linear blend from 20 kHz to
            // 650 Hz spends almost all of its travel in a band nobody can hear moving.
            const double A = std::log(std::max(PrevLpf, 20.0));
            const double B = std::log(std::max(Best->Inside.LpfHz, 20.0));
            Result.LpfHz = std::exp(Lerp(A, B, W));
        }
        LastPriority = NextPriority;
        bAnyDone = true;
    }
    return Result;
}

/** Extra attenuation from geometry between an emitter and the listener.
 *
 *  OccludedFraction is whatever the caller's trace produced, 0 clear .. 1 fully
 *  blocked. Kept here so the curve is testable and so the runtime and the offline
 *  report use an identical mapping. */
inline double OcclusionGain(double OccludedFraction, double MaxAttenuationDb = 12.0)
{
    const double F = Saturate(OccludedFraction);
    const double Db = -std::fabs(Finite(MaxAttenuationDb) ? MaxAttenuationDb : 12.0) * F;
    return DbToLinear(Db);
}

/** Occlusion also darkens. Log-interpolated for the same reason as above. */
inline double OcclusionLpfHz(double OccludedFraction, double OpenHz = LpfOpenHz,
                             double BlockedHz = 900.0)
{
    const double F = Saturate(OccludedFraction);
    const double A = std::log(std::max(Finite(OpenHz) ? OpenHz : LpfOpenHz, 20.0));
    const double B = std::log(std::max(Finite(BlockedHz) ? BlockedHz : 900.0, 20.0));
    return std::exp(Lerp(A, B, F));
}

/** Exponential approach with a time constant. Frame-rate independent: halving the
 *  frame time gives the same trajectory, which a naive lerp does not. */
inline double SmoothTowards(double Current, double Target, double DeltaSeconds,
                            double TauSeconds)
{
    if (!Finite(Current)) return Finite(Target) ? Target : 0.0;
    if (!Finite(Target) || !Finite(DeltaSeconds) || DeltaSeconds <= 0.0) return Current;
    if (!Finite(TauSeconds) || TauSeconds <= 1.0e-4) return Target;
    const double Alpha = 1.0 - std::exp(-DeltaSeconds / TauSeconds);
    return Current + (Target - Current) * Saturate(Alpha);
}

// ---------------------------------------------------------------------------
// The scheduler -- why this does not read as a loop
// ---------------------------------------------------------------------------
/** An emitter's timing rule. Beds set bLooping and are crossfaded between takes at
 *  irregular boundaries; everything else is silence, then one event. */
struct EmitterSchedule
{
    std::uint32_t Seed        = 0;
    std::uint32_t EmitterId   = 0;
    int           SourceCount = 1;      ///< number of takes this emitter may draw from
    double        MinGapSeconds = 20.0;
    double        MaxGapSeconds = 70.0;
    double        MinPitch = 0.92;
    double        MaxPitch = 1.08;
    double        MinLevel = 0.50;
    double        MaxLevel = 1.00;
    bool          bLooping = false;

    bool IsUsable() const
    {
        return SourceCount >= 1
            && Finite(MinGapSeconds) && Finite(MaxGapSeconds)
            && MinGapSeconds >= 0.0 && MaxGapSeconds >= MinGapSeconds
            && Finite(MinPitch) && Finite(MaxPitch) && MinPitch > 0.05 && MaxPitch >= MinPitch
            && Finite(MinLevel) && Finite(MaxLevel) && MinLevel >= 0.0 && MaxLevel >= MinLevel;
    }
};

/** What one pass of one emitter does. */
struct EmitterEvent
{
    double GapSeconds = 0.0;   ///< silence BEFORE this event
    int    SourceIndex = 0;    ///< which take
    double Pitch = 1.0;
    double Level = 1.0;
};

/** Draw a take, never the same one twice in a row.
 *
 *  This is the specific failure the user named. A plain uniform draw over seven calls
 *  repeats immediately about one time in seven, which is exactly often enough to be
 *  heard as a loop. Rejecting the previous index makes an immediate repeat impossible,
 *  at the cost of nothing. */
inline int PickSource(const EmitterSchedule& S, std::uint32_t Pass, int PreviousIndex)
{
    const int N = S.SourceCount < 1 ? 1 : S.SourceCount;
    if (N == 1) return 0;
    const int Prev = (PreviousIndex >= 0 && PreviousIndex < N) ? PreviousIndex : -1;
    if (Prev < 0)
    {
        return static_cast<int>(Hash(S.Seed, S.EmitterId, Pass, 11u)
                                % static_cast<std::uint32_t>(N));
    }
    // Draw uniformly over the N-1 takes that are not the previous one.
    const int Offset = static_cast<int>(Hash(S.Seed, S.EmitterId, Pass, 11u)
                                        % static_cast<std::uint32_t>(N - 1));
    return (Prev + 1 + Offset) % N;
}

/** The silence before the next event, stretched by the time of day.
 *
 *  IntervalScale comes from LayerIntervalScaleAtTime. The gap is drawn from a
 *  triangular distribution (the mean of two uniforms) rather than a flat one, so gaps
 *  cluster near the middle and the extremes stay rare -- a flat draw produces runs of
 *  near-minimum gaps that sound like a stutter. */
inline double NextGapSeconds(const EmitterSchedule& S, std::uint32_t Pass,
                             double IntervalScale)
{
    if (!S.IsUsable()) return 0.0;
    const double A = Hash01(S.Seed, S.EmitterId, Pass, 21u);
    const double B = Hash01(S.Seed, S.EmitterId, Pass, 22u);
    const double T = 0.5 * (A + B);
    const double Scale = (Finite(IntervalScale) && IntervalScale > 0.0)
                       ? Clamp(IntervalScale, 0.05, 20.0) : 1.0;
    return Lerp(S.MinGapSeconds, S.MaxGapSeconds, T) * Scale;
}

/** One complete pass: gap, take, pitch, level. Pure in (Seed, EmitterId, Pass). */
inline EmitterEvent NextEvent(const EmitterSchedule& S, std::uint32_t Pass,
                              int PreviousIndex, double IntervalScale)
{
    EmitterEvent E;
    if (!S.IsUsable()) return E;
    E.GapSeconds  = NextGapSeconds(S, Pass, IntervalScale);
    E.SourceIndex = PickSource(S, Pass, PreviousIndex);
    E.Pitch = HashRange(S.Seed, S.EmitterId, Pass, 31u, S.MinPitch, S.MaxPitch);
    E.Level = HashRange(S.Seed, S.EmitterId, Pass, 32u, S.MinLevel, S.MaxLevel);
    return E;
}

/** Measurements over a simulated run, used by the test and printed into the release
 *  receipt. This is the evidence for "nothing is on a fixed loop". */
struct ScheduleReport
{
    int    Passes = 0;
    double SpanSeconds = 0.0;
    double MinGap = 0.0;
    double MaxGap = 0.0;
    double MeanGap = 0.0;
    double GapStdDev = 0.0;
    int    ImmediateRepeats = 0;      ///< must be 0
    int    LongestIdenticalRun = 0;   ///< longest run of identical (source,pitch,level,gap)
    int    DistinctSourcesUsed = 0;
};

/** Simulate an emitter for N passes and measure it. No allocation, no I/O. */
inline ScheduleReport AnalyseSchedule(const EmitterSchedule& S, int Passes,
                                      double IntervalScale = 1.0)
{
    ScheduleReport R;
    if (!S.IsUsable() || Passes <= 0) return R;
    if (Passes > 200000) Passes = 200000;

    bool Seen[64] = {false};
    const int TrackedSources = S.SourceCount < 64 ? S.SourceCount : 64;

    double Sum = 0.0, SumSq = 0.0;
    double PrevGap = -1.0, PrevPitch = -1.0, PrevLevel = -1.0;
    int Prev = -1;
    int Run = 1;

    for (int I = 0; I < Passes; ++I)
    {
        const EmitterEvent E = NextEvent(S, static_cast<std::uint32_t>(I), Prev, IntervalScale);
        if (I == 0) { R.MinGap = R.MaxGap = E.GapSeconds; }
        R.MinGap = std::min(R.MinGap, E.GapSeconds);
        R.MaxGap = std::max(R.MaxGap, E.GapSeconds);
        Sum += E.GapSeconds;
        SumSq += E.GapSeconds * E.GapSeconds;
        R.SpanSeconds += E.GapSeconds;
        if (E.SourceIndex >= 0 && E.SourceIndex < TrackedSources) Seen[E.SourceIndex] = true;
        if (Prev >= 0 && E.SourceIndex == Prev) ++R.ImmediateRepeats;
        const bool Identical = (std::fabs(E.GapSeconds - PrevGap) < 1.0e-9)
                            && (std::fabs(E.Pitch - PrevPitch) < 1.0e-9)
                            && (std::fabs(E.Level - PrevLevel) < 1.0e-9)
                            && (E.SourceIndex == Prev);
        Run = Identical ? Run + 1 : 1;
        R.LongestIdenticalRun = std::max(R.LongestIdenticalRun, Run);
        Prev = E.SourceIndex;
        PrevGap = E.GapSeconds; PrevPitch = E.Pitch; PrevLevel = E.Level;
        ++R.Passes;
    }
    const double N = static_cast<double>(R.Passes);
    R.MeanGap = Sum / N;
    const double Var = std::max(0.0, SumSq / N - R.MeanGap * R.MeanGap);
    R.GapStdDev = std::sqrt(Var);
    for (int I = 0; I < TrackedSources; ++I) if (Seen[I]) ++R.DistinctSourcesUsed;
    return R;
}

/** Where two looping beds realign, in seconds, given their played-back durations
 *  (source length divided by playback pitch).
 *
 *  Reported honestly: this is the beat period of the pair, not a claim that either bed
 *  is individually unrecognisable. A 47.9 s bed is a 47.9 s bed. The number says only
 *  that the COMBINED texture of the two does not recur. */
inline double BeatPeriodSeconds(double PeriodA, double PeriodB)
{
    if (!Finite(PeriodA) || !Finite(PeriodB) || PeriodA <= 0.0 || PeriodB <= 0.0) return 0.0;
    const double Diff = std::fabs(1.0 / PeriodA - 1.0 / PeriodB);
    if (Diff < 1.0e-12) return 0.0;   // identical periods: they never drift apart
    return 1.0 / Diff;
}

/** Playback duration of a take at a given pitch. */
inline double PlayedDurationSeconds(double SourceSeconds, double Pitch)
{
    if (!Finite(SourceSeconds) || SourceSeconds <= 0.0) return 0.0;
    const double P = (Finite(Pitch) && Pitch > 0.05) ? Pitch : 1.0;
    return SourceSeconds / P;
}

// ---------------------------------------------------------------------------
// Crowd density -> murmur level
// ---------------------------------------------------------------------------
/** The courts now hold an instanced crowd of thousands plus 24 speaking residents.
 *  A murmur bed at a fixed level would be wrong in both directions: too loud at dawn
 *  when the court is empty, too thin at midday.
 *
 *  Level follows the square root of head count, the standard incoherent-sum rule for
 *  many uncorrelated sources (doubling the crowd is +3 dB, not +6), then saturates:
 *  past a few thousand voices a court does not get meaningfully louder, it gets
 *  denser. At ReferenceCount the gain is 0.71 * MaxGain; the curve is strictly
 *  increasing and can never exceed MaxGain. */
inline double CrowdMurmurGain(double HeadCount, double ReferenceCount = 1200.0,
                              double MaxGain = 1.0)
{
    if (!Finite(HeadCount) || HeadCount <= 0.0) return 0.0;
    const double Ref = (Finite(ReferenceCount) && ReferenceCount > 1.0) ? ReferenceCount : 1200.0;
    const double Raw = std::sqrt(HeadCount / Ref);
    const double Cap = (Finite(MaxGain) && MaxGain > 0.0) ? MaxGain : 1.0;
    return Cap * Raw / std::sqrt(1.0 + Raw * Raw);
}

/** Speaking residents are individual voices, not a bed: they lift the murmur a little
 *  and, more importantly, justify the murmur's random one-shot layer. */
inline double SpeakingVoiceGain(int SpeakingCount, int MaxTracked = 24)
{
    if (SpeakingCount <= 0) return 0.0;
    const int M = MaxTracked > 0 ? MaxTracked : 24;
    const int C = SpeakingCount < M ? SpeakingCount : M;
    return Saturate(std::sqrt(static_cast<double>(C) / static_cast<double>(M)));
}

// ---------------------------------------------------------------------------
// Final per-emitter gain
// ---------------------------------------------------------------------------
/** Everything above, combined once, in one place, so the runtime and the offline
 *  report cannot drift apart. */
struct GainInputs
{
    ELayer Layer = ELayer::WindBed;
    double BaseVolume = 1.0;        ///< the emitter's authored level
    double EventLevel = 1.0;        ///< this pass's random level
    double DayGain = 1.0;
    double HeightGain = 1.0;
    double Occlusion = 1.0;         ///< already an OcclusionGain() result
    double ZoneDryGain = 1.0;
    double UserMixGain = 1.0;       ///< the settings-menu ambience slider
};

inline double CombineGain(const GainInputs& In)
{
    const double G = (Finite(In.BaseVolume) ? Clamp(In.BaseVolume, 0.0, 4.0) : 0.0)
                   * (Finite(In.EventLevel) ? Clamp(In.EventLevel, 0.0, 4.0) : 1.0)
                   * (Finite(In.DayGain) ? Saturate(In.DayGain) : 1.0)
                   * (Finite(In.HeightGain) ? Clamp(In.HeightGain, 0.0, 2.0) : 1.0)
                   * (Finite(In.Occlusion) ? Saturate(In.Occlusion) : 1.0)
                   * (Finite(In.ZoneDryGain) ? Saturate(In.ZoneDryGain) : 1.0)
                   * (Finite(In.UserMixGain) ? Clamp(In.UserMixGain, 0.0, 4.0) : 1.0);
    return Clamp(G, 0.0, 4.0);
}

/** True when a layer is loud enough to be worth a voice. Hysteresis, so a component
 *  cannot flicker on and off at the threshold. */
inline bool ShouldBeAudible(double Gain, bool bCurrentlyPlaying)
{
    return bCurrentlyPlaying ? Gain > SilenceGain * 0.5 : Gain > SilenceGain * 2.0;
}

}   // namespace MikdashSoundscape
