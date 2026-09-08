#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstddef>
#include <vector>

// Engine-independent fire, smoke, flicker and ember math for the Mikdash effects.
// Shared by AMikdashFXDirector (Private/MikdashFXDirector.cpp), by the material
// parameter derivation in Scripts/create_fx_materials.py, by the numeric readback in
// Scripts/release_fx.py and by the standalone test
// Plugins/MikdashRuntime/Source/MikdashRuntime/Tests/PlumeMathTest.cpp.
//
// Units: centimetres, seconds, Hertz, degrees. World frame is Unreal's: +X east,
// +Y south, +Z up. No Unreal types, no globals, no I/O, no std::rand. Every random
// draw is a pure integer hash of (Seed, Index, Lane), so the offline Python
// generator, the editor commandlet and a packaged build agree bit for bit.
//
// What this is NOT. It is not a fluid solver and it is not a combustion model. It
// answers six questions: how wide is a rising plume at a given height, where is its
// axis, how does an indoor plume behave once it reaches a ceiling, how bright is a
// flame from one instant to the next, how long does an ember live, and how much of
// all this should be drawn at a given viewing distance.
//
// SOURCE CLAIM, not physics: FPlumeProfile::bStraightColumnInWind makes the outer
// altar's smoke column rise vertically at any wind speed. Avos 5:5 lists among the
// miracles of the Mikdash that the column of smoke from the arrangement was not
// dispersed by the wind. This flag is therefore a depiction of a cited claim, and it
// is deliberately a separate switch from the physical bent-plume path below, which
// remains available and is exercised by the tests. Nothing here asserts that a real
// plume behaves this way.
namespace MikdashPlume
{
constexpr double Pi = 3.14159265358979323846;

/** Hard magnitude ceilings. Every length and every time this header returns is
 *  clamped to these before it leaves, so a caller that passes 1e30 gets a large but
 *  finite number instead of an overflow that turns into an infinity two
 *  multiplications later. 1e9 cm is 10,000 km; 1e6 s is eleven days. Neither is
 *  reachable by any real scene value in this project. */
constexpr double MaxLengthCm = 1.0e9;
constexpr double MaxTimeS = 1.0e6;

// ---------------------------------------------------------------------------
// Deterministic hashing. No engine RNG, no std::rand, no global state.
// ---------------------------------------------------------------------------
inline uint32_t HashUint32(uint32_t X)
{
    // Finalizer of Austin Appleby's MurmurHash3; avalanche is good enough that the
    // low bits of consecutive indices are independent to the eye.
    X ^= X >> 16;
    X *= 0x7feb352du;
    X ^= X >> 15;
    X *= 0x846ca68bu;
    X ^= X >> 16;
    return X;
}

inline uint32_t HashCombine3(uint32_t Seed, uint32_t Index, uint32_t Lane)
{
    return HashUint32(HashUint32(Seed * 0x9e3779b9u + 0x85ebca6bu) ^ (Index * 0xc2b2ae35u) ^ HashUint32(Lane * 0x27d4eb2fu + 0x165667b1u));
}

/** Uniform in [0,1). Never returns 1.0, so log(1-u) and the probit below are safe. */
inline double HashToUnit(uint32_t Seed, uint32_t Index, uint32_t Lane)
{
    return static_cast<double>(HashCombine3(Seed, Index, Lane)) * (1.0 / 4294967296.0);
}

/** Uniform in (-1,1). */
inline double HashToSigned(uint32_t Seed, uint32_t Index, uint32_t Lane)
{
    return HashToUnit(Seed, Index, Lane) * 2.0 - 1.0;
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------
struct FVec3
{
    double X = 0.0, Y = 0.0, Z = 0.0;
};

inline double Clamp(double Value, double Low, double High)
{
    return Value < Low ? Low : (Value > High ? High : Value);
}

/** Every public entry point runs its result through this, so a caller that feeds in
 *  a NaN or an infinity gets a finite fallback instead of poisoning a render thread. */
inline double Finite(double Value, double Fallback = 0.0)
{
    return std::isfinite(Value) ? Value : Fallback;
}

/** Clamp a length into [0, MaxLengthCm], mapping NaN to 0. */
inline double ClampLength(double Value)
{
    const double V = Finite(Value, 0.0);
    return V < 0.0 ? 0.0 : (V > MaxLengthCm ? MaxLengthCm : V);
}

/** Clamp a duration into [0, MaxTimeS], mapping NaN to 0. */
inline double ClampTime(double Value)
{
    const double V = Finite(Value, 0.0);
    return V < 0.0 ? 0.0 : (V > MaxTimeS ? MaxTimeS : V);
}

inline double Lerp(double A, double B, double T)
{
    return A + (B - A) * Clamp(T, 0.0, 1.0);
}

/** Horizontal wind. Direction need not be normalised; the accessors normalise it. */
struct FWind
{
    double DirX = 1.0;
    double DirY = 0.0;
    double SpeedCmS = 0.0;
};

inline void NormalisedWindDir(const FWind& Wind, double& OutX, double& OutY)
{
    const double Length = std::sqrt(Wind.DirX * Wind.DirX + Wind.DirY * Wind.DirY);
    if (!(Length > 1e-9))
    {
        OutX = 1.0;
        OutY = 0.0;
        return;
    }
    OutX = Wind.DirX / Length;
    OutY = Wind.DirY / Length;
}

// ---------------------------------------------------------------------------
// Rising plume
// ---------------------------------------------------------------------------
/** A top-hat buoyant plume. SourceRadiusCm is the radius of the burning area, not of
 *  a particle. EntrainmentAlpha is the linear spreading constant: the plume half
 *  angle is atan(alpha), so 0.11 gives the roughly 6 degree half angle that the
 *  Morton-Taylor-Turner top-hat model uses for a pure plume. RiseSpeedCmS is the
 *  centreline speed at the source; above it the speed decays as h^(-1/3), which is
 *  the same model's similarity solution. Both are artistic values here: they set the
 *  look, and no measurement of Temple smoke exists to calibrate them against. */
struct FPlumeProfile
{
    double SourceRadiusCm = 250.0;
    double RiseSpeedCmS = 320.0;
    double EntrainmentAlpha = 0.11;
    double MaxRadiusCm = 1800.0;
    /** Vertical extent that the effect draws at all. Beyond this the plume is faded out. */
    double MaxHeightCm = 4000.0;
    /** Physical bend gain when bStraightColumnInWind is false. 1.0 = pure advection. */
    double BendGain = 1.0;
    /** SOURCE CLAIM (Avos 5:5), not physics: hold the column vertical in any wind. */
    bool bStraightColumnInWind = false;
    /** Dilution floor so a very tall column never reads as perfectly clear. */
    double MinOpacity = 0.02;
};

/** Centreline speed at a height above the source, h^(-1/3) similarity decay. */
inline double PlumeRiseSpeedCmS(const FPlumeProfile& Profile, double HeightAboveSourceCm)
{
    const double R0 = std::max(1.0, Finite(Profile.SourceRadiusCm, 1.0));
    const double H = std::max(0.0, Finite(HeightAboveSourceCm));
    const double W0 = std::max(1.0, Finite(Profile.RiseSpeedCmS, 1.0));
    return Finite(W0 * std::cbrt(R0 / (R0 + H)), W0);
}

/** Radius of the visible column at a height above the source. Linear entrainment,
 *  clamped so a tall column does not become a wall. */
inline double PlumeRadiusCm(const FPlumeProfile& Profile, double HeightAboveSourceCm)
{
    const double R0 = std::max(1.0, Finite(Profile.SourceRadiusCm, 1.0));
    const double Alpha = Clamp(Finite(Profile.EntrainmentAlpha, 0.11), 0.0, 1.0);
    const double H = std::max(0.0, Finite(HeightAboveSourceCm));
    const double MaxR = std::max(R0, ClampLength(Finite(Profile.MaxRadiusCm, R0)));
    return ClampLength(Clamp(R0 + Alpha * H, R0, MaxR));
}

/** Time for a smoke parcel released at the source to reach a height, obtained by
 *  integrating dh/dt = PlumeRiseSpeedCmS in closed form:
 *      t(h) = 3 * ((R0+h)^(4/3) - R0^(4/3)) / (4 * W0 * R0^(1/3)).
 *  Monotone in h, exactly 0 at h = 0, finite for every finite h >= 0. */
inline double PlumeTimeToHeightS(const FPlumeProfile& Profile, double HeightAboveSourceCm)
{
    const double R0 = std::max(1.0, Finite(Profile.SourceRadiusCm, 1.0));
    const double W0 = std::max(1.0, Finite(Profile.RiseSpeedCmS, 1.0));
    const double H = std::max(0.0, Finite(HeightAboveSourceCm));
    const double A43 = std::pow(R0, 4.0 / 3.0);
    const double T = 3.0 * (std::pow(R0 + H, 4.0 / 3.0) - A43) / (4.0 * W0 * std::cbrt(R0));
    return ClampTime(T);
}

/** Inverse of PlumeTimeToHeightS: height reached by a parcel of the given age. */
inline double PlumeHeightAtAgeCm(const FPlumeProfile& Profile, double AgeSeconds)
{
    const double R0 = std::max(1.0, Finite(Profile.SourceRadiusCm, 1.0));
    const double W0 = std::max(1.0, Finite(Profile.RiseSpeedCmS, 1.0));
    const double T = std::max(0.0, Finite(AgeSeconds));
    const double Inner = std::pow(R0, 4.0 / 3.0) + (4.0 / 3.0) * W0 * std::cbrt(R0) * T;
    const double H = std::pow(std::max(Inner, 1e-12), 0.75) - R0;
    return Clamp(ClampLength(H), 0.0, ClampLength(Profile.MaxHeightCm));
}

/** Lateral displacement of the plume axis at a height, along the wind direction.
 *
 *  bStraightColumnInWind == true returns exactly 0 at every wind speed. That is the
 *  Avos 5:5 depiction, recorded as a source claim.
 *
 *  Otherwise the parcel is advected horizontally for as long as it has been rising:
 *  offset(h) = BendGain * WindSpeed * t(h). This is plain advection of a rising
 *  parcel, which is the honest cheap answer; it is not a validated bent-plume
 *  trajectory model. */
inline double PlumeAxisOffsetCm(const FPlumeProfile& Profile, double HeightAboveSourceCm, const FWind& Wind)
{
    if (Profile.bStraightColumnInWind)
    {
        return 0.0;
    }
    const double Speed = std::max(0.0, Finite(Wind.SpeedCmS));
    const double Gain = Clamp(Finite(Profile.BendGain, 1.0), 0.0, 1.0e6);
    return ClampLength(Gain * ClampLength(Speed) * PlumeTimeToHeightS(Profile, HeightAboveSourceCm));
}

/** Optical depth proxy. A top-hat plume conserves smoke mass, so concentration falls
 *  as (R0/R)^2. Clamped to MinOpacity..1. */
inline double PlumeOpacity(const FPlumeProfile& Profile, double HeightAboveSourceCm)
{
    const double R0 = std::max(1.0, Finite(Profile.SourceRadiusCm, 1.0));
    const double R = std::max(R0, PlumeRadiusCm(Profile, HeightAboveSourceCm));
    const double Ratio = R0 / R;
    const double Floor = Clamp(Finite(Profile.MinOpacity, 0.0), 0.0, 1.0);
    return Clamp(Finite(Ratio * Ratio, Floor), Floor, 1.0);
}

struct FPlumeSample
{
    double HeightCm = 0.0;
    double RadiusCm = 0.0;
    double AxisOffsetCm = 0.0;
    double RiseSpeedCmS = 0.0;
    double Opacity = 0.0;
    /** World-space offset of the axis from the source, wind direction applied. */
    FVec3 AxisOffsetWorldCm;
};

inline FPlumeSample SamplePlumeAtAge(const FPlumeProfile& Profile, double AgeSeconds, const FWind& Wind)
{
    FPlumeSample Out;
    Out.HeightCm = PlumeHeightAtAgeCm(Profile, AgeSeconds);
    Out.RadiusCm = PlumeRadiusCm(Profile, Out.HeightCm);
    Out.AxisOffsetCm = PlumeAxisOffsetCm(Profile, Out.HeightCm, Wind);
    Out.RiseSpeedCmS = PlumeRiseSpeedCmS(Profile, Out.HeightCm);
    Out.Opacity = PlumeOpacity(Profile, Out.HeightCm);
    double DirX = 1.0, DirY = 0.0;
    NormalisedWindDir(Wind, DirX, DirY);
    Out.AxisOffsetWorldCm.X = DirX * Out.AxisOffsetCm;
    Out.AxisOffsetWorldCm.Y = DirY * Out.AxisOffsetCm;
    Out.AxisOffsetWorldCm.Z = Out.HeightCm;
    return Out;
}

/** Is a point (given as an offset from the plume source) inside the drawn envelope?
 *  SlackCm widens the test; the effect budget uses a small slack so a card that
 *  wobbles by a texel is not judged to have escaped. */
inline bool IsInsidePlumeEnvelope(const FPlumeProfile& Profile, const FVec3& OffsetFromSourceCm, const FWind& Wind, double SlackCm = 0.0)
{
    const double H = Finite(OffsetFromSourceCm.Z);
    if (H < -ClampLength(SlackCm) || H > ClampLength(Profile.MaxHeightCm) + ClampLength(SlackCm))
    {
        return false;
    }
    const double Clamped = Clamp(H, 0.0, ClampLength(Profile.MaxHeightCm));
    const double Radius = PlumeRadiusCm(Profile, Clamped) + ClampLength(SlackCm);
    const double Offset = PlumeAxisOffsetCm(Profile, Clamped, Wind);
    double DirX = 1.0, DirY = 0.0;
    NormalisedWindDir(Wind, DirX, DirY);
    const double DX = Finite(OffsetFromSourceCm.X) - DirX * Offset;
    const double DY = Finite(OffsetFromSourceCm.Y) - DirY * Offset;
    return DX * DX + DY * DY <= Radius * Radius;
}

// ---------------------------------------------------------------------------
// Indoor plume: rise, ceiling impingement, spread, descending layer
// ---------------------------------------------------------------------------
/** Geometry of the room the ketores plume rises into, plus the two time constants
 *  that shape the spread. Yoma 53a describes a stafflike column rising to the
 *  ceiling and smoke then spreading and descending until the chamber is filled;
 *  the shape below follows that description. Every number is artistic: the sugya
 *  gives no rise velocity, layer depth or duration. */
struct FCeilingSpread
{
    double SourceZCm = 0.0;
    double CeilingZCm = 2925.0;
    /** Largest radius the ceiling layer may reach before the walls stop it. */
    double RoomRadiusCm = 1000.0;
    /** Radial spread of the ceiling jet: r = RoomRadius * (1 - exp(-t/tau)). */
    double SpreadTimeConstantS = 6.0;
    /** Downward growth of the layer once it has reached the walls. */
    double FillTimeConstantS = 25.0;
    double MaxLayerDepthCm = 900.0;
};

/** Seconds from release at the source until the column touches the ceiling. */
inline double CeilingImpingementTimeS(const FPlumeProfile& Profile, const FCeilingSpread& Room)
{
    const double Rise = ClampLength(Room.CeilingZCm) - ClampLength(Room.SourceZCm);
    if (!(Rise > 0.0))
    {
        return 0.0;
    }
    return PlumeTimeToHeightS(Profile, Rise);
}

/** Radius of the ceiling layer, seconds after impingement. Saturates at RoomRadius. */
inline double CeilingSpreadRadiusCm(const FCeilingSpread& Room, double SecondsSinceImpingement)
{
    const double T = std::max(0.0, Finite(SecondsSinceImpingement));
    const double Tau = std::max(1e-3, Finite(Room.SpreadTimeConstantS, 1.0));
    const double MaxR = ClampLength(Room.RoomRadiusCm);
    return Clamp(Finite(MaxR * (1.0 - std::exp(-T / Tau))), 0.0, MaxR);
}

/** Depth of the descending layer below the ceiling, seconds after impingement.
 *  Only starts growing once the layer has substantially reached the walls, which is
 *  why the fill term is delayed by one spread time constant. */
inline double CeilingLayerDepthCm(const FCeilingSpread& Room, double SecondsSinceImpingement)
{
    const double Tau = std::max(1e-3, Finite(Room.SpreadTimeConstantS, 1.0));
    const double T = std::max(0.0, Finite(SecondsSinceImpingement) - Tau);
    const double Fill = std::max(1e-3, Finite(Room.FillTimeConstantS, 1.0));
    const double MaxD = ClampLength(Room.MaxLayerDepthCm);
    return Clamp(Finite(MaxD * (1.0 - std::exp(-T / Fill))), 0.0, MaxD);
}

/** World Z of the underside of the descending layer. Never below the source. */
inline double CeilingLayerBottomZCm(const FCeilingSpread& Room, double SecondsSinceImpingement)
{
    const double Ceiling = ClampLength(Room.CeilingZCm);
    const double Bottom = Ceiling - CeilingLayerDepthCm(Room, SecondsSinceImpingement);
    return std::max(ClampLength(Room.SourceZCm), Finite(Bottom, Ceiling));
}

/** 0 before the column reaches the ceiling, 1 when the layer has finished filling.
 *  Drives the material's spread mask so the indoor effect is one continuous shape
 *  rather than two effects cross-faded. */
inline double CeilingSpreadFraction(const FCeilingSpread& Room, double SecondsSinceImpingement)
{
    const double MaxR = std::max(1e-3, ClampLength(Room.RoomRadiusCm));
    return Clamp(CeilingSpreadRadiusCm(Room, SecondsSinceImpingement) / MaxR, 0.0, 1.0);
}

/** Phase of one authored ketores event, in the four phases the research document
 *  asks for: emission, ascent, accumulation, dissipating tail. */
enum class EKetoresPhase : int32_t
{
    Idle = 0,
    Emitting = 1,
    Ascending = 2,
    Accumulating = 3,
    Dissipating = 4,
};

struct FKetoresTiming
{
    double EmissionSeconds = 20.0;
    double AccumulateSeconds = 45.0;
    double DissipateSeconds = 60.0;
};

inline EKetoresPhase KetoresPhaseAt(const FKetoresTiming& Timing, const FPlumeProfile& Profile, const FCeilingSpread& Room, double SecondsSinceBegin)
{
    const double T = Finite(SecondsSinceBegin, -1.0);
    if (T < 0.0)
    {
        return EKetoresPhase::Idle;
    }
    const double Impinge = CeilingImpingementTimeS(Profile, Room);
    const double Emission = std::max(0.0, Finite(Timing.EmissionSeconds));
    const double Accumulate = std::max(0.0, Finite(Timing.AccumulateSeconds));
    const double Dissipate = std::max(0.0, Finite(Timing.DissipateSeconds));
    if (T < std::min(Emission, Impinge))
    {
        return EKetoresPhase::Emitting;
    }
    if (T < Impinge)
    {
        return EKetoresPhase::Ascending;
    }
    if (T < Impinge + Accumulate)
    {
        return EKetoresPhase::Accumulating;
    }
    if (T < Impinge + Accumulate + Dissipate)
    {
        return EKetoresPhase::Dissipating;
    }
    return EKetoresPhase::Idle;
}

/** Overall density multiplier for one authored event: ramps in over the emission,
 *  holds while the room fills, then decays to zero over the tail. Exactly 0 before
 *  the event begins and after it ends, so no emitter is left running. */
inline double KetoresDensity(const FKetoresTiming& Timing, const FPlumeProfile& Profile, const FCeilingSpread& Room, double SecondsSinceBegin)
{
    const double T = Finite(SecondsSinceBegin, -1.0);
    if (T < 0.0)
    {
        return 0.0;
    }
    const double Impinge = CeilingImpingementTimeS(Profile, Room);
    const double Emission = std::max(1e-3, Finite(Timing.EmissionSeconds, 1.0));
    const double Accumulate = std::max(0.0, Finite(Timing.AccumulateSeconds));
    const double Dissipate = std::max(1e-3, Finite(Timing.DissipateSeconds, 1.0));
    const double HoldEnd = Impinge + Accumulate;
    if (T < Emission)
    {
        return Clamp(T / Emission, 0.0, 1.0);
    }
    if (T < HoldEnd)
    {
        return 1.0;
    }
    if (T < HoldEnd + Dissipate)
    {
        const double U = (T - HoldEnd) / Dissipate;
        // Smooth cubic falloff; reaches exactly 0 at u = 1 with zero slope.
        return Clamp(Finite(1.0 - U * U * (3.0 - 2.0 * U)), 0.0, 1.0);
    }
    return 0.0;
}

// ---------------------------------------------------------------------------
// Flame flicker: band-limited noise, not white noise
// ---------------------------------------------------------------------------
/** Puffing frequency of a buoyant diffusion flame of the given diameter.
 *  f = 1.5 / sqrt(D_metres) is the widely reported correlation for pool fires
 *  (Cetegen and Ahmed 1993, and many later restatements). It is used here only to
 *  pick a plausible centre frequency; a small wick flickers fast and a 12 m fire
 *  arrangement flickers slowly, which is exactly the perceptual difference the
 *  altar and the menorah need. */
inline double PuffingFrequencyHz(double DiameterCm)
{
    const double Metres = std::max(1e-4, Finite(DiameterCm, 1.0) * 0.01);
    return Clamp(Finite(1.5 / std::sqrt(Metres), 1.0), 0.05, 60.0);
}

/** A two-pole resonator driven by hashed white noise. The output is band-limited
 *  around FrequencyHz with bandwidth FrequencyHz/Q, so its spectrum has a clear
 *  peak instead of the flat spectrum of the white noise a naive implementation
 *  would show. State is three doubles; Advance is branch-light and allocation free. */
struct FFlicker
{
    uint32_t Seed = 1u;
    uint32_t Step = 0u;
    double FrequencyHz = 10.0;
    double Q = 4.0;
    double Y1 = 0.0;
    double Y2 = 0.0;
    double Value = 0.0;

    void Reset(uint32_t InSeed, double InFrequencyHz, double InQ = 4.0)
    {
        Seed = InSeed ? InSeed : 1u;
        Step = 0u;
        FrequencyHz = Clamp(Finite(InFrequencyHz, 10.0), 0.05, 60.0);
        Q = Clamp(Finite(InQ, 4.0), 0.5, 40.0);
        Y1 = Y2 = Value = 0.0;
    }

    /** Advance by DtS seconds and return the new flicker value, roughly in [-1,1].
     *  The resonator coefficients are recomputed from Dt each call, so a variable
     *  frame rate does not change the centre frequency. */
    double Advance(double DtS)
    {
        const double Dt = Clamp(Finite(DtS, 1.0 / 60.0), 1.0 / 1000.0, 0.25);
        // Nyquist guard: never resonate above half the effective sample rate.
        const double SampleRate = 1.0 / Dt;
        const double F = std::min(FrequencyHz, SampleRate * 0.45);
        const double Omega = 2.0 * Pi * F * Dt;
        // Pole radius from the requested Q: bandwidth = F/Q, r = exp(-pi*BW*Dt).
        const double R = Clamp(std::exp(-Pi * (F / Q) * Dt), 0.0, 0.9999);
        const double White = HashToSigned(Seed, Step++, 0x464c4b52u);
        const double Y = 2.0 * R * std::cos(Omega) * Y1 - R * R * Y2 + (1.0 - R) * White;
        Y2 = Y1;
        Y1 = Finite(Y);
        // Normalise: the resonator's gain at the peak is about 1/(1-r), and the
        // (1-r) input scaling already cancels most of it. The residual scale keeps
        // the output near unit amplitude across the useful Q range.
        Value = Clamp(Finite(Y1 * std::sqrt(2.0 * Q)), -4.0, 4.0);
        return Value;
    }
};

/** Map a flicker value to a multiplier around 1. Depth 0.25 gives a 0.75..1.25
 *  swing, which reads as a live flame without strobing. Always positive. */
inline double FlickerMultiplier(double FlickerValue, double Depth)
{
    const double D = Clamp(Finite(Depth, 0.0), 0.0, 0.9);
    return Clamp(Finite(1.0 + D * Clamp(Finite(FlickerValue), -1.0, 1.0), 1.0), 1.0 - D, 1.0 + D);
}

// ---------------------------------------------------------------------------
// Embers
// ---------------------------------------------------------------------------
/** Probit (inverse standard normal CDF), Peter Acklam's rational approximation.
 *  Relative error below 1.15e-9 over the open interval; the tails are clamped so a
 *  hashed 0.0 cannot produce an infinity. */
inline double NormalQuantile(double P)
{
    const double Prob = Clamp(Finite(P, 0.5), 1e-12, 1.0 - 1e-12);
    static const double A[6] = {-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00};
    static const double B[5] = {-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01};
    static const double C[6] = {-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00};
    static const double D[4] = {7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00};
    const double PLow = 0.02425;
    double X;
    if (Prob < PLow)
    {
        const double Q = std::sqrt(-2.0 * std::log(Prob));
        X = (((((C[0] * Q + C[1]) * Q + C[2]) * Q + C[3]) * Q + C[4]) * Q + C[5]) / ((((D[0] * Q + D[1]) * Q + D[2]) * Q + D[3]) * Q + 1.0);
    }
    else if (Prob <= 1.0 - PLow)
    {
        const double Q = Prob - 0.5;
        const double R = Q * Q;
        X = (((((A[0] * R + A[1]) * R + A[2]) * R + A[3]) * R + A[4]) * R + A[5]) * Q / (((((B[0] * R + B[1]) * R + B[2]) * R + B[3]) * R + B[4]) * R + 1.0);
    }
    else
    {
        const double Q = std::sqrt(-2.0 * std::log(1.0 - Prob));
        X = -(((((C[0] * Q + C[1]) * Q + C[2]) * Q + C[3]) * Q + C[4]) * Q + C[5]) / ((((D[0] * Q + D[1]) * Q + D[2]) * Q + D[3]) * Q + 1.0);
    }
    return Clamp(Finite(X), -8.0, 8.0);
}

/** Ember burnout parameters. A log-normal lifetime is the usual description of
 *  firebrand burnout times, and it has the shape the eye expects: most embers die
 *  early, a few ride the column a long way. MedianS is the log-normal median (not
 *  the mean); Sigma is the standard deviation of the natural log. */
struct FEmberProfile
{
    double MedianLifetimeS = 1.6;
    double LogSigma = 0.55;
    double MinLifetimeS = 0.25;
    double MaxLifetimeS = 8.0;
    /** Upward speed an ember inherits from the fire, before the plume carries it. */
    double LaunchSpeedCmS = 220.0;
    /** Exponential velocity decay time; embers cool and lag the gas. */
    double DragTimeConstantS = 1.1;
};

inline double EmberLifetimeS(const FEmberProfile& Profile, uint32_t Seed, uint32_t Index)
{
    const double U = Clamp(HashToUnit(Seed, Index, 0x454d4252u), 1e-9, 1.0 - 1e-9);
    const double Median = std::max(1e-3, Finite(Profile.MedianLifetimeS, 1.0));
    const double Sigma = Clamp(Finite(Profile.LogSigma, 0.5), 0.0, 3.0);
    const double Life = Median * std::exp(Sigma * NormalQuantile(U));
    const double Low = std::max(1e-3, Finite(Profile.MinLifetimeS, 0.1));
    const double High = std::max(Low, Finite(Profile.MaxLifetimeS, 10.0));
    return Clamp(Finite(Life, Low), Low, High);
}

/** Height of one ember above the fire at a given age: launch impulse decaying with
 *  drag, plus the plume that keeps carrying it. Monotone in age, finite everywhere. */
inline double EmberHeightCm(const FEmberProfile& Ember, const FPlumeProfile& Plume, double AgeSeconds)
{
    const double T = std::max(0.0, Finite(AgeSeconds));
    const double Tau = std::max(1e-3, Finite(Ember.DragTimeConstantS, 1.0));
    const double V0 = ClampLength(Ember.LaunchSpeedCmS);
    const double Impulse = ClampLength(V0 * Tau * (1.0 - std::exp(-T / Tau)));
    return Clamp(ClampLength(Impulse + PlumeHeightAtAgeCm(Plume, T)), 0.0, ClampLength(Plume.MaxHeightCm));
}

/** Brightness of an ember over its life: bright at birth, fading to black exactly at
 *  the end of its lifetime so no ember pops out of existence while still lit. */
inline double EmberBrightness(double AgeSeconds, double LifetimeS)
{
    const double Life = std::max(1e-3, Finite(LifetimeS, 1.0));
    const double U = Clamp(Finite(AgeSeconds) / Life, 0.0, 1.0);
    const double Fade = 1.0 - U;
    return Clamp(Finite(Fade * Fade), 0.0, 1.0);
}

// ---------------------------------------------------------------------------
// Budget and distance falloff
// ---------------------------------------------------------------------------
/** One effect's share of the frame. Quality 1 at FullDetailCm and closer, 0 beyond
 *  CutoffCm, smooth in between so nothing pops. Squared falloff because the screen
 *  area an effect covers falls off with the square of distance. */
inline double DistanceQuality(double DistanceCm, double FullDetailCm, double CutoffCm)
{
    const double D = ClampLength(DistanceCm);
    const double Full = ClampLength(FullDetailCm);
    const double Cut = std::max(Full + 1.0, ClampLength(Finite(CutoffCm, Full + 1.0)));
    if (D <= Full)
    {
        return 1.0;
    }
    if (D >= Cut)
    {
        return 0.0;
    }
    const double U = (D - Full) / (Cut - Full);
    return Clamp(Finite(1.0 - U * U * (3.0 - 2.0 * U)), 0.0, 1.0);
}

/** How many cards an effect should draw at this quality. Never negative, never more
 *  than MaxCards, and 0 only when quality is 0 so a visible effect never vanishes. */
inline int32_t CardCountForQuality(double Quality, int32_t MinCards, int32_t MaxCards)
{
    const double Q = Clamp(Finite(Quality), 0.0, 1.0);
    const int32_t Low = std::max(0, MinCards);
    const int32_t High = std::max(Low, MaxCards);
    if (Q <= 0.0)
    {
        return 0;
    }
    const double Count = static_cast<double>(Low) + (static_cast<double>(High - Low)) * Q;
    const int32_t Rounded = static_cast<int32_t>(std::floor(Count + 0.5));
    return Rounded < Low ? Low : (Rounded > High ? High : Rounded);
}

/** Total translucent overdraw an effect contributes, in screen fractions, used by
 *  the director to keep the sum under a budget. CardArea is the fraction of the
 *  screen one card covers at this distance; the estimate is deliberately crude and
 *  is a budget, not a measurement. */
inline double EstimatedOverdraw(int32_t CardCount, double CardScreenFraction)
{
    const double Fraction = Clamp(Finite(CardScreenFraction), 0.0, 1.0);
    return Clamp(Finite(static_cast<double>(std::max(0, CardCount)) * Fraction), 0.0, 64.0);
}

} // namespace MikdashPlume
