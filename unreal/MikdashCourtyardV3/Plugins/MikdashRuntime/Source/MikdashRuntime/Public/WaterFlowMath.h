#pragma once
#include <algorithm>
#include <cmath>
#include <cstddef>

// Engine-independent water math shared by AMikdashWater and the standalone tests.
// Units: centimetres, seconds, cm^3. No Unreal types, no allocation, no globals.
//
// WHAT THIS IS
// ------------
// The arithmetic behind three separate things that happen to share a header:
//
//   1. THE STREAM OF YECHEZKEL 47. A depth-and-width profile keyed to the prophet's
//      four measurements of a thousand amot each (47:3-5), plus the open-channel
//      hydraulics (Manning normal depth, continuity, Froude number) that turn that
//      profile into a flow speed a material can scroll at and a place to put foam.
//
//   2. WAVE AND RIPPLE KINEMATICS. Shallow-water celerity, travelling-wave phase, a
//      damped expanding ripple, and the UV scroll offset a Panner needs so that the
//      normal map moves at the same speed as the water it is pretending to be.
//
//   3. VOLUME AND THE FORTY-SE'AH TEST. Trapezoidal-channel and stepped-pool volumes,
//      and the halachic minimum for a mikveh expressed as three cubic amot, evaluated
//      at each of the three amah opinions this project records.
//
// WHAT THIS IS NOT
// ----------------
// It is not a fluid simulation. There is no free surface solver, no advection, no
// pressure projection and no conservation of anything across time. Manning's equation
// is a steady-uniform-flow empirical correlation for engineered channels; it is used
// here to get ONE defensible number (a speed) out of a width, a depth and a bed slope,
// so that the visual rate of scroll is derived rather than dialled in by eye.
//
// It is also not a halachic instrument. FortySeah() reports arithmetic on published
// shiurim; it does not rule on whether a given pool is kosher, which depends on
// provenance of the water, connection to the ground, and much else that no header
// can encode. See SourceAssets/water-review/sources.md for what is certain, what is
// disputed and what this project authored.
//
// PROVENANCE OF EVERY CONSTANT BELOW is in SourceAssets/water-review/sources.md.
// Constants marked AUTHORED have no textual source and are this project's invention.
namespace MikdashWater
{

// ---------------------------------------------------------------------------
// Units and scale
// ---------------------------------------------------------------------------

/** The project's working amah. Every other script in this repo uses 50 cm (0.5 m);
 *  see Scripts/create_keilim_ti_v1.py and Scripts/create_oldcity_facades.py. It is a
 *  round modelling figure, NOT a claim about the halachic amah -- for that see the
 *  three opinions in AmahOpinion below. */
constexpr double ProjectAmahCm = 50.0;
constexpr double TefachCm = ProjectAmahCm / 6.0;

/** Gravity in cm/s^2, for shallow-water celerity and the Froude number. */
constexpr double GravityCmS2 = 980.665;

constexpr double Pi = 3.14159265358979323846;

inline double Clamp(double V, double Lo, double Hi) { return std::max(Lo, std::min(Hi, V)); }
inline double Saturate(double V) { return Clamp(V, 0.0, 1.0); }
inline bool Finite(double V) { return std::isfinite(V); }

/** Guarded division: returns Fallback rather than an infinity when the divisor vanishes. */
inline double SafeDiv(double Numerator, double Denominator, double Fallback = 0.0)
{
    return std::abs(Denominator) > 1e-12 ? Numerator / Denominator : Fallback;
}

// ---------------------------------------------------------------------------
// 1. The three amah opinions, and the forty-se'ah test
// ---------------------------------------------------------------------------
//
// A mikveh must hold forty se'ah (Mishnah Mikvaos 1:7, and Eruvin 4b, which derives
// the measure as a pit one amah by one amah by three amot deep -- i.e. THREE CUBIC
// AMOT). Everything downstream follows from that identity, so the only free variable
// is the length of the amah, on which the poskim differ. This project reports all
// three rather than choosing.

enum class AmahOpinion
{
    /** R' Avraham Chaim Naeh: amah 48 cm. 3 x 48^3 = 331,776 cm^3 ~ 331.8 L. */
    ChazonNaeh = 0,
    /** Chazon Ish (the stringent shiur): amah 57.6 cm. 3 x 57.6^3 ~ 573,309 cm^3 ~ 573.3 L. */
    ChazonIsh = 1,
    /** The project's 50 cm modelling amah: 3 x 50^3 = 375,000 cm^3 = 375 L exactly.
     *  Present so the modelled geometry can be checked in its own units; it is a
     *  modelling convenience and carries no halachic weight of its own. */
    ProjectModelling = 2,
};
constexpr std::size_t AmahOpinionCount = 3;

inline double AmahCm(AmahOpinion Opinion)
{
    switch (Opinion)
    {
    case AmahOpinion::ChazonNaeh: return 48.0;
    case AmahOpinion::ChazonIsh: return 57.6;
    case AmahOpinion::ProjectModelling: return ProjectAmahCm;
    }
    return ProjectAmahCm;
}

inline const char* AmahOpinionName(AmahOpinion Opinion)
{
    switch (Opinion)
    {
    case AmahOpinion::ChazonNaeh: return "R' A. C. Naeh (amah 48 cm)";
    case AmahOpinion::ChazonIsh: return "Chazon Ish (amah 57.6 cm)";
    case AmahOpinion::ProjectModelling: return "project modelling amah (50 cm)";
    }
    return "unknown";
}

/** Forty se'ah as a volume in cm^3, for a given amah: three cubic amot (Eruvin 4b). */
inline double FortySeahCm3(AmahOpinion Opinion)
{
    const double A = AmahCm(Opinion);
    return 3.0 * A * A * A;
}

/** The same figure per single se'ah, which is how the shiurim are usually quoted. */
inline double OneSeahCm3(AmahOpinion Opinion) { return FortySeahCm3(Opinion) / 40.0; }

inline double Cm3ToLitres(double Cm3) { return Cm3 / 1000.0; }

struct MikvahVerdict
{
    double VolumeCm3 = 0;
    double RequiredCm3 = 0;
    /** Volume / Required. 1.0 is exactly forty se'ah; below 1.0 is short. */
    double Ratio = 0;
    bool Sufficient = false;
};

/** Does a pool of the given water volume hold forty se'ah on the given opinion? */
inline MikvahVerdict FortySeahTest(double VolumeCm3, AmahOpinion Opinion)
{
    MikvahVerdict Out;
    Out.RequiredCm3 = FortySeahCm3(Opinion);
    Out.VolumeCm3 = (Finite(VolumeCm3) && VolumeCm3 > 0.0) ? VolumeCm3 : 0.0;
    Out.Ratio = SafeDiv(Out.VolumeCm3, Out.RequiredCm3, 0.0);
    Out.Sufficient = Out.VolumeCm3 >= Out.RequiredCm3;
    return Out;
}

/** The strictest of the opinions -- what a pool must hold to satisfy all three. */
inline MikvahVerdict FortySeahTestStrictest(double VolumeCm3)
{
    MikvahVerdict Worst = FortySeahTest(VolumeCm3, AmahOpinion::ChazonNaeh);
    for (std::size_t I = 1; I < AmahOpinionCount; ++I)
    {
        const MikvahVerdict Candidate = FortySeahTest(VolumeCm3, static_cast<AmahOpinion>(I));
        if (Candidate.RequiredCm3 > Worst.RequiredCm3) Worst = Candidate;
    }
    return Worst;
}

// ---------------------------------------------------------------------------
// 2. Channel cross-sections and volume
// ---------------------------------------------------------------------------

/** A symmetric trapezoidal channel section: a flat bed of BedWidthCm with banks that
 *  lean out SideSlope centimetres horizontally for every centimetre of rise. SideSlope
 *  0 is a rectangular runnel; 1.5 is a gentle earth bank. */
struct ChannelSection
{
    double BedWidthCm = 0;
    double DepthCm = 0;
    double SideSlope = 0;

    /** Width of the free surface. */
    double TopWidthCm() const { return BedWidthCm + 2.0 * SideSlope * DepthCm; }
    /** Wetted cross-sectional area, cm^2. */
    double AreaCm2() const { return DepthCm * (BedWidthCm + SideSlope * DepthCm); }
    /** Length of bed plus both wetted bank faces, cm. */
    double WettedPerimeterCm() const
    {
        return BedWidthCm + 2.0 * DepthCm * std::sqrt(1.0 + SideSlope * SideSlope);
    }
    /** Area / wetted perimeter -- the length scale Manning's equation is written in. */
    double HydraulicRadiusCm() const { return SafeDiv(AreaCm2(), WettedPerimeterCm(), 0.0); }
    /** Area / top width -- the depth that enters the Froude number. */
    double HydraulicDepthCm() const { return SafeDiv(AreaCm2(), TopWidthCm(), 0.0); }
    bool Valid() const
    {
        return Finite(BedWidthCm) && Finite(DepthCm) && Finite(SideSlope)
            && BedWidthCm >= 0.0 && DepthCm >= 0.0 && SideSlope >= 0.0
            && TopWidthCm() > 0.0;
    }
};

/** Volume of a prismatic run of channel, cm^3: end areas averaged over the run length.
 *  Exact for a linear taper of area, which is what the generated geometry lofts. */
inline double ChannelRunVolumeCm3(const ChannelSection& A, const ChannelSection& B, double RunLengthCm)
{
    if (!(Finite(RunLengthCm) && RunLengthCm > 0.0)) return 0.0;
    return 0.5 * (A.AreaCm2() + B.AreaCm2()) * RunLengthCm;
}

/** One rectangular step of a stepped pool: a tread of the given plan area holding
 *  water to the given depth. Steps are summed to get a mikveh's usable volume. */
struct PoolStep
{
    double LengthCm = 0;
    double WidthCm = 0;
    double WaterDepthCm = 0;
    double VolumeCm3() const
    {
        return std::max(0.0, LengthCm) * std::max(0.0, WidthCm) * std::max(0.0, WaterDepthCm);
    }
};

/** Total water held by a stepped pool. Only the water BELOW the fill line counts;
 *  a step whose tread stands above the fill line contributes nothing. */
inline double SteppedPoolVolumeCm3(const PoolStep* Steps, std::size_t Count)
{
    double Total = 0.0;
    if (!Steps) return 0.0;
    for (std::size_t I = 0; I < Count; ++I) Total += Steps[I].VolumeCm3();
    return Total;
}

/** A plain rectangular basin's volume, cm^3 -- the simplest mikveh geometry. */
inline double BasinVolumeCm3(double LengthCm, double WidthCm, double WaterDepthCm)
{
    return std::max(0.0, LengthCm) * std::max(0.0, WidthCm) * std::max(0.0, WaterDepthCm);
}

// ---------------------------------------------------------------------------
// 3. Open-channel hydraulics
// ---------------------------------------------------------------------------

/** Manning roughness coefficients, dimensionless (SI convention: the 1/n coefficient
 *  below carries the metric unit factor). Standard open-channel-hydraulics values. */
namespace Roughness
{
constexpr double DressedStone = 0.015;   // the cut runnel through the courtyard paving
constexpr double RubbleStone = 0.025;    // the built channel outside the walls
constexpr double NaturalEarth = 0.030;   // the wadi bed running down to the Aravah
}

/** Manning's equation for mean velocity, returned in cm/s.
 *
 *  In SI: V[m/s] = (1/n) * R[m]^(2/3) * S^(1/2). Inputs here are centimetres, so the
 *  hydraulic radius is converted to metres, and the result back to cm/s.
 *
 *  Slope is the dimensionless bed gradient (rise over run), taken as positive; a
 *  non-positive or non-finite slope yields zero velocity rather than a NaN. */
inline double ManningVelocityCmS(double HydraulicRadiusCm, double BedSlope, double ManningN)
{
    if (!(Finite(HydraulicRadiusCm) && Finite(BedSlope) && Finite(ManningN))) return 0.0;
    if (HydraulicRadiusCm <= 0.0 || BedSlope <= 0.0 || ManningN <= 1e-9) return 0.0;
    const double RadiusM = HydraulicRadiusCm / 100.0;
    const double VelocityMs = (1.0 / ManningN) * std::pow(RadiusM, 2.0 / 3.0) * std::sqrt(BedSlope);
    return VelocityMs * 100.0;
}

/** Discharge by continuity, cm^3/s. */
inline double DischargeCm3S(const ChannelSection& Section, double VelocityCmS)
{
    return Section.AreaCm2() * std::max(0.0, VelocityCmS);
}

/** Steady uniform discharge of a section under Manning, cm^3/s. */
inline double NormalDischargeCm3S(const ChannelSection& Section, double BedSlope, double ManningN)
{
    return DischargeCm3S(Section, ManningVelocityCmS(Section.HydraulicRadiusCm(), BedSlope, ManningN));
}

/** Invert the above: the NORMAL DEPTH at which a trapezoidal channel of the given bed
 *  width carries the given discharge. Discharge rises strictly with depth, so plain
 *  bisection on [0, MaxDepthCm] converges; 60 halvings take the bracket below 1e-15 of
 *  its width, far under any tolerance that matters here. Returns 0 for a non-positive
 *  discharge, and MaxDepthCm if the channel cannot carry the flow at all. */
inline double NormalDepthCm(double DischargeCm3PerS, double BedWidthCm, double SideSlope,
                            double BedSlope, double ManningN, double MaxDepthCm = 5000.0)
{
    if (!(Finite(DischargeCm3PerS) && DischargeCm3PerS > 0.0)) return 0.0;
    if (!(Finite(MaxDepthCm) && MaxDepthCm > 0.0)) return 0.0;
    ChannelSection Probe;
    Probe.BedWidthCm = std::max(0.0, BedWidthCm);
    Probe.SideSlope = std::max(0.0, SideSlope);
    Probe.DepthCm = MaxDepthCm;
    if (NormalDischargeCm3S(Probe, BedSlope, ManningN) < DischargeCm3PerS) return MaxDepthCm;
    double Lo = 0.0, Hi = MaxDepthCm;
    for (int I = 0; I < 60; ++I)
    {
        const double Mid = 0.5 * (Lo + Hi);
        Probe.DepthCm = Mid;
        if (NormalDischargeCm3S(Probe, BedSlope, ManningN) < DischargeCm3PerS) Lo = Mid; else Hi = Mid;
    }
    return 0.5 * (Lo + Hi);
}

/** Speed of a small surface disturbance in shallow water, cm/s: sqrt(g * depth). */
inline double ShallowWaterCelerityCmS(double DepthCm)
{
    return (Finite(DepthCm) && DepthCm > 0.0) ? std::sqrt(GravityCmS2 * DepthCm) : 0.0;
}

/** Froude number: flow speed over wave speed. Below 1 the flow is tranquil and the
 *  surface is smooth; above 1 it is shooting, and where it drops back through 1 --
 *  at the foot of a step -- a hydraulic jump throws the foam. */
inline double FroudeNumber(double VelocityCmS, double HydraulicDepthCm)
{
    return SafeDiv(std::max(0.0, VelocityCmS), ShallowWaterCelerityCmS(HydraulicDepthCm), 0.0);
}

enum class FlowRegime
{
    Still = 0,        // no measurable flow
    Subcritical = 1,  // Fr < 1: smooth, controlled from downstream
    Critical = 2,     // Fr ~ 1
    Supercritical = 3 // Fr > 1: shooting; a jump waits wherever it slows
};

inline FlowRegime ClassifyFlow(double Froude, double Tolerance = 0.02)
{
    if (!Finite(Froude) || Froude <= 1e-6) return FlowRegime::Still;
    if (Froude < 1.0 - Tolerance) return FlowRegime::Subcritical;
    if (Froude > 1.0 + Tolerance) return FlowRegime::Supercritical;
    return FlowRegime::Critical;
}

/** Foam intensity in 0..1. Foam is entrained where the flow is fast relative to its own
 *  wave speed; this maps Froude 0.6 -> 0 up to Froude 1.6 -> 1, which puts a soft
 *  edge of white just upstream of every step and a full band at its foot. AUTHORED
 *  mapping: the thresholds are chosen to look right, not measured. */
inline double FoamFromFroude(double Froude)
{
    const double T = Saturate((Froude - 0.6) / 1.0);
    return T * T * (3.0 - 2.0 * T);
}

// ---------------------------------------------------------------------------
// 4. The four stages of Yechezkel 47:3-5
// ---------------------------------------------------------------------------
//
// "And when the man went forth eastward with the line in his hand, he measured a
// thousand amot, and he brought me through the water; the water was to the ankles.
// Again he measured a thousand, and brought me through the water; the water was to
// the knees. Again he measured a thousand, and brought me through; the water was to
// the loins. Afterward he measured a thousand; it was a river that I could not pass
// over, for the water was risen, water to swim in, a river that could not be passed
// over." (Yechezkel 47:3-5.)
//
// The four measurements are CERTAIN as text. Whether they are literal distances on
// the ground or a schema is DISPUTED; see sources.md. This header encodes them as
// literal distances because the reconstruction is a measured one, and flags the
// alternative in the receipt rather than hiding it.
//
// The DEPTHS are the interpretive part. The text names parts of a body, not numbers.
// The figures below are anthropometric fractions of an assumed standing stature,
// which is the only way to turn "to the ankles" into a centimetre value. Stature and
// fractions are AUTHORED; change StatureCm and the whole profile rescales.

constexpr double StatureCm = 170.0;

constexpr double AnkleFraction = 0.07;   // lateral malleolus height / stature
constexpr double KneeFraction = 0.285;   // knee joint line / stature
constexpr double LoinFraction = 0.53;    // iliac crest ("loins") / stature
constexpr double SwimFraction = 1.05;    // over the head: "water to swim in"

/** The trickle at the gate before the first thousand is measured -- Yechezkel 47:2
 *  says the water was MEFAKIM, trickling, from the right shoulder of the gate.
 *  AUTHORED value: enough to be visible, not enough to wet an ankle. */
constexpr double TrickleDepthCm = 0.6;

enum class Stage
{
    Trickle = 0, // at the gate, before the first thousand
    Ankles = 1,  // afsayim, at 1000 amot
    Knees = 2,   // birkayim, at 2000 amot
    Loins = 3,   // motnayim, at 3000 amot
    River = 4,   // "a river that could not be passed over", at 4000 amot
};
constexpr std::size_t StageCount = 5;

inline const char* StageName(Stage S)
{
    switch (S)
    {
    case Stage::Trickle: return "trickle at the gate (mefakim, 47:2)";
    case Stage::Ankles: return "to the ankles (afsayim, 47:3)";
    case Stage::Knees: return "to the knees (birkayim, 47:4)";
    case Stage::Loins: return "to the loins (motnayim, 47:4)";
    case Stage::River: return "a river that could not be passed over (47:5)";
    }
    return "unknown";
}

/** Distance east of the outer east gate, in amot, at which each stage is measured. */
inline double StageDistanceAmot(Stage S) { return 1000.0 * static_cast<double>(static_cast<int>(S)); }

inline double StageDepthCm(Stage S)
{
    switch (S)
    {
    case Stage::Trickle: return TrickleDepthCm;
    case Stage::Ankles: return AnkleFraction * StatureCm;
    case Stage::Knees: return KneeFraction * StatureCm;
    case Stage::Loins: return LoinFraction * StatureCm;
    case Stage::River: return SwimFraction * StatureCm;
    }
    return 0.0;
}

/** Top width of the stream at each stage, in amot. ENTIRELY AUTHORED: no source gives
 *  a width anywhere along the stream. The progression is chosen so that the widening
 *  reads as continuous growth rather than four sudden jumps, and so that the section
 *  at 4000 amot is plainly too broad and too deep to wade. The aggadic tradition that
 *  the stream begins as fine as a locust's antenna and swells as it goes (Yoma 77b-78a)
 *  is corroboration for the SHAPE of this curve, not a source for its numbers. */
inline double StageTopWidthAmot(Stage S)
{
    switch (S)
    {
    case Stage::Trickle: return 1.0;
    case Stage::Ankles: return 4.0;
    case Stage::Knees: return 10.0;
    case Stage::Loins: return 20.0;
    case Stage::River: return 50.0;
    }
    return 0.0;
}

// --- monotone interpolation between the anchors ---------------------------------
//
// The prophet's four figures are exact AT the thousand-amah marks and say nothing
// about what happens between them. Any interpolation is authored; the one requirement
// that is not a matter of taste is that the water must never get shallower as it runs,
// because the text has it rising continuously. Fritsch-Carlson monotone cubic Hermite
// (SIAM J. Numer. Anal. 17(2), 1980) is the standard way to interpolate through
// ordered data without introducing an overshoot, so it is what is used here: it hits
// every anchor exactly and is provably monotone between them.

/** Fritsch-Carlson tangents for equally spaced, strictly increasing samples. */
inline void MonotoneTangents(const double* Y, std::size_t N, double SpacingX, double* OutTangents)
{
    if (!Y || !OutTangents || N < 2 || SpacingX <= 0.0) return;
    // Secant slopes.
    double Secants[StageCount];
    const std::size_t Segments = (N - 1 < StageCount) ? N - 1 : StageCount;
    for (std::size_t I = 0; I < Segments; ++I) Secants[I] = (Y[I + 1] - Y[I]) / SpacingX;

    OutTangents[0] = Secants[0];
    OutTangents[N - 1] = Secants[Segments - 1];
    for (std::size_t I = 1; I + 1 < N; ++I) OutTangents[I] = 0.5 * (Secants[I - 1] + Secants[I]);

    for (std::size_t I = 0; I < Segments; ++I)
    {
        if (std::abs(Secants[I]) < 1e-15)
        {
            OutTangents[I] = 0.0;
            OutTangents[I + 1] = 0.0;
            continue;
        }
        const double A = OutTangents[I] / Secants[I];
        const double B = OutTangents[I + 1] / Secants[I];
        // Project (A, B) back inside the circle of radius 3 that guarantees monotonicity.
        const double Norm = std::sqrt(A * A + B * B);
        if (Norm > 3.0)
        {
            const double Scale = 3.0 / Norm;
            OutTangents[I] = Scale * A * Secants[I];
            OutTangents[I + 1] = Scale * B * Secants[I];
        }
    }
}

/** Evaluate the monotone cubic through equally spaced samples at DistanceX, clamping
 *  outside the sample range. */
inline double MonotoneSample(const double* Y, const double* Tangents, std::size_t N,
                             double SpacingX, double DistanceX)
{
    if (!Y || !Tangents || N == 0 || SpacingX <= 0.0 || !Finite(DistanceX)) return 0.0;
    if (N == 1) return Y[0];
    const double Span = SpacingX * static_cast<double>(N - 1);
    if (DistanceX <= 0.0) return Y[0];
    if (DistanceX >= Span) return Y[N - 1];
    const std::size_t Index = std::min(static_cast<std::size_t>(DistanceX / SpacingX), N - 2);
    const double T = (DistanceX - SpacingX * static_cast<double>(Index)) / SpacingX;
    const double T2 = T * T, T3 = T2 * T;
    const double H00 = 2 * T3 - 3 * T2 + 1;
    const double H10 = T3 - 2 * T2 + T;
    const double H01 = -2 * T3 + 3 * T2;
    const double H11 = T3 - T2;
    return H00 * Y[Index] + H10 * SpacingX * Tangents[Index]
         + H01 * Y[Index + 1] + H11 * SpacingX * Tangents[Index + 1];
}

/** The stream's profile: depth and width as continuous functions of distance east of
 *  the outer east gate. Built once, then sampled. Distances in amot, results in cm. */
struct StreamProfile
{
    double DepthCm[StageCount] = {};
    double TopWidthCm[StageCount] = {};
    double DepthTangents[StageCount] = {};
    double WidthTangents[StageCount] = {};
    double SpacingAmot = 1000.0;
    double AmahCmUsed = ProjectAmahCm;

    /** Distance at which the last measurement is taken: 4000 amot. */
    double SpanAmot() const { return SpacingAmot * static_cast<double>(StageCount - 1); }
    double SpanCm() const { return SpanAmot() * AmahCmUsed; }

    double DepthAtAmot(double Amot) const
    {
        return MonotoneSample(DepthCm, DepthTangents, StageCount, SpacingAmot, Amot);
    }
    double TopWidthAtAmot(double Amot) const
    {
        return MonotoneSample(TopWidthCm, WidthTangents, StageCount, SpacingAmot, Amot);
    }
    double DepthAtCm(double DistanceCm) const { return DepthAtAmot(SafeDiv(DistanceCm, AmahCmUsed)); }
    double TopWidthAtCm(double DistanceCm) const { return TopWidthAtAmot(SafeDiv(DistanceCm, AmahCmUsed)); }

    /** Which of the prophet's stages the given distance has reached (the last stage
     *  whose measuring mark has been passed). */
    Stage StageAtAmot(double Amot) const
    {
        if (!Finite(Amot) || Amot < SpacingAmot) return Stage::Trickle;
        const int Index = static_cast<int>(std::min(Amot / SpacingAmot, static_cast<double>(StageCount - 1)));
        return static_cast<Stage>(Index);
    }

    /** The section at a distance, given a bank side slope. */
    ChannelSection SectionAtAmot(double Amot, double SideSlope) const
    {
        ChannelSection Out;
        Out.SideSlope = std::max(0.0, SideSlope);
        Out.DepthCm = std::max(0.0, DepthAtAmot(Amot));
        // Solve for the bed width that produces the authored TOP width at this depth.
        Out.BedWidthCm = std::max(0.0, TopWidthAtAmot(Amot) - 2.0 * Out.SideSlope * Out.DepthCm);
        return Out;
    }
};

/** Build the profile from the stage constants above, at the given amah. */
inline StreamProfile MakeStreamProfile(double UseAmahCm = ProjectAmahCm)
{
    StreamProfile P;
    P.AmahCmUsed = (Finite(UseAmahCm) && UseAmahCm > 0.0) ? UseAmahCm : ProjectAmahCm;
    for (std::size_t I = 0; I < StageCount; ++I)
    {
        const Stage S = static_cast<Stage>(I);
        P.DepthCm[I] = StageDepthCm(S);
        P.TopWidthCm[I] = StageTopWidthAmot(S) * P.AmahCmUsed;
    }
    MonotoneTangents(P.DepthCm, StageCount, P.SpacingAmot, P.DepthTangents);
    MonotoneTangents(P.TopWidthCm, StageCount, P.SpacingAmot, P.WidthTangents);
    return P;
}

// ---------------------------------------------------------------------------
// 5. Demonstration mode: walking the prophet's measure
// ---------------------------------------------------------------------------
//
// The user can trigger a demonstration in which the stream swells through the four
// stages in sequence, pausing at each measuring mark so the depth can be read against
// a figure standing in it. This is the state machine for that, expressed as pure
// arithmetic so the actor holds no logic of its own.

struct DemoSettings
{
    /** Seconds spent travelling from one thousand-amah mark to the next. */
    double TravelSeconds = 6.0;
    /** Seconds held still at each mark while the measurement is read. */
    double HoldSeconds = 3.0;
    /** Loop back to the trickle after the fourth stage instead of stopping. */
    bool Loop = false;
};

struct DemoState
{
    /** How far east of the gate the demonstration has reached, in amot. */
    double DistanceAmot = 0;
    /** The stage last passed. */
    Stage CurrentStage = Stage::Trickle;
    /** 0..1 across the whole four thousand amot -- what a progress bar would show. */
    double Progress = 0;
    /** True while paused at a measuring mark. */
    bool Holding = false;
    /** True once the fourth measurement has been taken and the demo is not looping. */
    bool Finished = false;
};

/** One full cycle: four travel legs and four holds (the trickle at the gate is the
 *  start state, not a held mark). */
inline double DemoCycleSeconds(const DemoSettings& S)
{
    const double Travel = std::max(0.0, S.TravelSeconds);
    const double Hold = std::max(0.0, S.HoldSeconds);
    return 4.0 * (Travel + Hold);
}

/** Evaluate the demonstration at an elapsed time since it was triggered. */
inline DemoState EvaluateDemo(const DemoSettings& S, double ElapsedSeconds)
{
    DemoState Out;
    const double Travel = std::max(0.0, S.TravelSeconds);
    const double Hold = std::max(0.0, S.HoldSeconds);
    const double Leg = Travel + Hold;
    const double Cycle = 4.0 * Leg;
    double T = (Finite(ElapsedSeconds) && ElapsedSeconds > 0.0) ? ElapsedSeconds : 0.0;

    if (Cycle <= 1e-9)
    {
        Out.DistanceAmot = 4000.0;
        Out.CurrentStage = Stage::River;
        Out.Progress = 1.0;
        Out.Finished = !S.Loop;
        return Out;
    }
    if (T >= Cycle)
    {
        if (!S.Loop)
        {
            Out.DistanceAmot = 4000.0;
            Out.CurrentStage = Stage::River;
            Out.Progress = 1.0;
            Out.Holding = true;
            Out.Finished = true;
            return Out;
        }
        T = std::fmod(T, Cycle);
    }

    const int LegIndex = static_cast<int>(std::min(T / Leg, 3.0));
    const double InLeg = T - Leg * static_cast<double>(LegIndex);
    const double Base = 1000.0 * static_cast<double>(LegIndex);
    if (Travel > 1e-9 && InLeg < Travel)
    {
        Out.DistanceAmot = Base + 1000.0 * (InLeg / Travel);
        Out.Holding = false;
    }
    else
    {
        Out.DistanceAmot = Base + 1000.0;
        Out.Holding = true;
    }
    Out.DistanceAmot = Clamp(Out.DistanceAmot, 0.0, 4000.0);
    Out.CurrentStage = static_cast<Stage>(static_cast<int>(std::min(Out.DistanceAmot / 1000.0, 4.0)));
    Out.Progress = Saturate(Out.DistanceAmot / 4000.0);
    return Out;
}

// ---------------------------------------------------------------------------
// 6. Surface kinematics: scroll, waves, ripples
// ---------------------------------------------------------------------------

/** How far a normal map should have scrolled after Seconds at FlowSpeed, expressed in
 *  TEXTURE TILES so it can go straight into a Panner. TileSizeCm is the world size one
 *  tile of the normal map covers. The result is wrapped into [0, 1) so it never grows
 *  large enough to lose float precision in the shader, which is what makes a long-
 *  running scroll start to judder. */
inline double ScrollTiles(double FlowSpeedCmS, double Seconds, double TileSizeCm)
{
    if (!(Finite(FlowSpeedCmS) && Finite(Seconds) && Finite(TileSizeCm)) || TileSizeCm <= 1e-9) return 0.0;
    const double Tiles = std::fmod(FlowSpeedCmS * Seconds / TileSizeCm, 1.0);
    return Tiles < 0.0 ? Tiles + 1.0 : Tiles;
}

/** Phase of a travelling wave, radians, at a distance downstream and a time.
 *  Positive celerity travels downstream. */
inline double WavePhase(double DistanceCm, double Seconds, double WavelengthCm, double CelerityCmS)
{
    if (!(Finite(DistanceCm) && Finite(Seconds) && Finite(WavelengthCm)) || WavelengthCm <= 1e-9) return 0.0;
    const double K = 2.0 * Pi / WavelengthCm;
    return K * (DistanceCm - CelerityCmS * Seconds);
}

/** Surface elevation of that wave about the mean level, cm. */
inline double WaveElevationCm(double AmplitudeCm, double Phase)
{
    return Finite(Phase) ? AmplitudeCm * std::sin(Phase) : 0.0;
}

/** A ripple spreading from a disturbance -- a foot entering the water, a vessel filled.
 *  The crest travels outward at the shallow-water celerity and decays both with age
 *  (exponentially, time constant DecaySeconds) and with radius (as 1/sqrt(r), the
 *  spreading of a ring of fixed energy). Returns a displacement in cm at the sample
 *  point, zero ahead of the advancing crest. */
struct Ripple
{
    double AmplitudeCm = 4.0;
    double WavelengthCm = 60.0;
    double DecaySeconds = 1.6;
    /** Width of the moving crest band, cm; outside it the ripple is not yet arrived
     *  or has already passed. */
    double CrestWidthCm = 120.0;
};

inline double RippleElevationCm(const Ripple& R, double RadiusCm, double AgeSeconds, double DepthCm)
{
    if (!(Finite(RadiusCm) && Finite(AgeSeconds)) || AgeSeconds < 0.0 || RadiusCm < 0.0) return 0.0;
    const double Celerity = ShallowWaterCelerityCmS(DepthCm);
    if (Celerity <= 1e-9 || R.CrestWidthCm <= 1e-9) return 0.0;
    const double Front = Celerity * AgeSeconds;
    const double Behind = Front - RadiusCm;
    if (Behind < 0.0 || Behind > R.CrestWidthCm) return 0.0;   // not yet arrived, or passed
    const double Age = (R.DecaySeconds > 1e-9) ? std::exp(-AgeSeconds / R.DecaySeconds) : 0.0;
    const double Spread = 1.0 / std::sqrt(std::max(1.0, RadiusCm));
    const double Window = 0.5 * (1.0 - std::cos(2.0 * Pi * (Behind / R.CrestWidthCm)));
    const double Phase = 2.0 * Pi * Behind / std::max(1e-9, R.WavelengthCm);
    return R.AmplitudeCm * Age * Spread * Window * std::cos(Phase);
}

// ---------------------------------------------------------------------------
// 7. What the material needs, in one struct
// ---------------------------------------------------------------------------

/** Everything the water material instance is driven by, evaluated at one point along
 *  the stream. AMikdashWater computes this and pushes it into the dynamic material. */
struct SurfaceDrive
{
    double DepthCm = 0;
    double TopWidthCm = 0;
    double VelocityCmS = 0;
    double DischargeCm3S = 0;
    double Froude = 0;
    FlowRegime Regime = FlowRegime::Still;
    double Foam = 0;
    double CelerityCmS = 0;
    /** Panner offset in tiles, already wrapped to [0, 1). */
    double ScrollTiles = 0;
    /** 0..1 opacity ramp: shallow water is nearly clear, deep water is not. Reaches
     *  full opacity at OpacityFullDepthCm. AUTHORED curve. */
    double Opacity = 0;
    Stage CurrentStage = Stage::Trickle;
};

constexpr double OpacityFullDepthCm = 120.0;

/** Evaluate the whole drive at a distance east of the gate. BedSlope and ManningN
 *  describe the reach being sampled; TileSizeCm and Seconds drive the scroll. */
inline SurfaceDrive EvaluateSurface(const StreamProfile& Profile, double DistanceAmot,
                                    double SideSlope, double BedSlope, double ManningN,
                                    double TileSizeCm, double Seconds)
{
    SurfaceDrive Out;
    const ChannelSection Section = Profile.SectionAtAmot(DistanceAmot, SideSlope);
    Out.DepthCm = Section.DepthCm;
    Out.TopWidthCm = Section.TopWidthCm();
    Out.VelocityCmS = ManningVelocityCmS(Section.HydraulicRadiusCm(), BedSlope, ManningN);
    Out.DischargeCm3S = DischargeCm3S(Section, Out.VelocityCmS);
    Out.CelerityCmS = ShallowWaterCelerityCmS(Section.HydraulicDepthCm());
    Out.Froude = FroudeNumber(Out.VelocityCmS, Section.HydraulicDepthCm());
    Out.Regime = ClassifyFlow(Out.Froude);
    Out.Foam = FoamFromFroude(Out.Froude);
    Out.ScrollTiles = MikdashWater::ScrollTiles(Out.VelocityCmS, Seconds, TileSizeCm);
    const double D = Saturate(Out.DepthCm / OpacityFullDepthCm);
    Out.Opacity = D * D * (3.0 - 2.0 * D);
    Out.CurrentStage = Profile.StageAtAmot(DistanceAmot);
    return Out;
}

} // namespace MikdashWater
