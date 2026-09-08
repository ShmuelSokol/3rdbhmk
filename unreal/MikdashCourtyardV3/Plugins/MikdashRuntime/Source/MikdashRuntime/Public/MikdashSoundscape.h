#pragma once

// =============================================================================
// MikdashSoundscape.h
//
// TWO FILES IN ONE HEADER, on purpose.
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


// -----------------------------------------------------------------------------
// PART 2 -- the actor. Skipped when the standalone test compiles this header.
// -----------------------------------------------------------------------------
#ifndef MIKDASH_SOUNDSCAPE_MATH_ONLY

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

#endif   // MIKDASH_SOUNDSCAPE_MATH_ONLY
