#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

// Engine-independent transit math shared by AMikdashTransit and the standalone tests.
// Units: centimeters, seconds, degrees. No Unreal types, no allocation, no globals.
//
// What this is: the arithmetic behind an instanced road- and rail-traffic layer --
// arc-length sampling of an authored route, lane offsets, car-following, stop-and-go
// braking, a randomised station headway, a dwell/door state machine and the same
// bounded round-robin budget the crowd field uses.
//
// What this is NOT: it is not a traffic simulation, a navigation solver, a physics
// model or a signalling system. Vehicles run on authored polylines, never leave them,
// never turn off, never yield at junctions and never collide -- they only keep a
// following distance behind the vehicle in front of them on the SAME route. The routes
// themselves are authored interpretation (see routes.json); the light-rail line in
// particular is an authored future proposal, not surveyed infrastructure.
namespace MikdashTransit
{
constexpr double Pi = 3.14159265358979323846;

// ---------------------------------------------------------------------------
// Small vector type
// ---------------------------------------------------------------------------

struct Vec3
{
    double X = 0, Y = 0, Z = 0;
};
inline Vec3 operator+(const Vec3& A, const Vec3& B) { return {A.X + B.X, A.Y + B.Y, A.Z + B.Z}; }
inline Vec3 operator-(const Vec3& A, const Vec3& B) { return {A.X - B.X, A.Y - B.Y, A.Z - B.Z}; }
inline Vec3 operator*(const Vec3& A, double S) { return {A.X * S, A.Y * S, A.Z * S}; }
inline double Dot(const Vec3& A, const Vec3& B) { return A.X * B.X + A.Y * B.Y + A.Z * B.Z; }
inline double Length(const Vec3& A) { return std::sqrt(Dot(A, A)); }
inline double Length2D(const Vec3& A) { return std::sqrt(A.X * A.X + A.Y * A.Y); }
inline bool Finite(const Vec3& A) { return std::isfinite(A.X) && std::isfinite(A.Y) && std::isfinite(A.Z); }
inline Vec3 Normalized(const Vec3& A)
{
    const double L = Length(A);
    return L > 1e-9 ? A * (1.0 / L) : Vec3{};
}
inline double Clamp(double V, double Lo, double Hi) { return std::max(Lo, std::min(Hi, V)); }
inline double DegToRad(double D) { return D * Pi / 180.0; }
inline double RadToDeg(double R) { return R * 180.0 / Pi; }

/** Signed yaw in degrees for a direction's XY part, in (-180, 180]; zero vector yields 0. */
inline double YawDegrees(const Vec3& D)
{
    return (std::abs(D.X) < 1e-12 && std::abs(D.Y) < 1e-12) ? 0.0 : RadToDeg(std::atan2(D.Y, D.X));
}
/** Signed pitch in degrees for a direction, positive nose-up, matching Unreal's sign. */
inline double PitchDegrees(const Vec3& D)
{
    const double Flat = Length2D(D);
    return (Flat < 1e-12 && std::abs(D.Z) < 1e-12) ? 0.0 : RadToDeg(std::atan2(D.Z, Flat));
}
inline double WrapDegrees(double D)
{
    if (!std::isfinite(D)) return 0.0;
    D = std::fmod(D + 180.0, 360.0);
    if (D < 0) D += 360.0;
    return D - 180.0;
}
/** Unreal's right vector for a yaw-only rotation: FRotator(0, Yaw, 0).GetRightVector().
 * Positive lane offsets therefore put a vehicle to the driver's right of the centreline. */
inline Vec3 RightFromYaw(double YawDeg)
{
    const double R = DegToRad(YawDeg);
    return {-std::sin(R), std::cos(R), 0.0};
}

// ---------------------------------------------------------------------------
// Deterministic hashing. Identical construction to MikdashCrowd, repeated locally so
// this header has no dependency: the same seed must produce the same traffic in the
// editor preview, in PIE and in a packaged build, so std::rand is avoided.
// ---------------------------------------------------------------------------

inline uint32_t HashInt(uint32_t V)
{
    V ^= V >> 16;
    V *= 0x85ebca6bu;
    V ^= V >> 13;
    V *= 0xc2b2ae35u;
    V ^= V >> 16;
    return V;
}
inline uint32_t HashCombine(uint32_t Seed, uint32_t Value) { return HashInt(Seed ^ (Value + 0x9e3779b9u + (Seed << 6) + (Seed >> 2))); }
/** Uniform double in [0,1). Stream index Lane keeps unrelated draws independent. */
inline double HashUnit(uint32_t Seed, uint32_t Index, uint32_t Lane)
{
    return HashCombine(HashCombine(Seed, Index), Lane) * (1.0 / 4294967296.0);
}
inline double HashRange(uint32_t Seed, uint32_t Index, uint32_t Lane, double Lo, double Hi)
{
    return Lo + (Hi - Lo) * HashUnit(Seed, Index, Lane);
}
/** Integer in [Lo, Hi] inclusive; Hi <= Lo yields Lo. */
inline int HashIntRange(uint32_t Seed, uint32_t Index, uint32_t Lane, int Lo, int Hi)
{
    if (Hi <= Lo) return Lo;
    const int Span = Hi - Lo + 1;
    const int Picked = Lo + static_cast<int>(HashUnit(Seed, Index, Lane) * Span);
    return Picked > Hi ? Hi : Picked;
}

// ---------------------------------------------------------------------------
// Route geometry: densification and arc-length sampling
// ---------------------------------------------------------------------------

/** Centripetal Catmull-Rom (alpha 0.5) point on the P1..P2 span. Centripetal rather than
 * uniform, so an authored route with a short segment next to a long one does not cusp or
 * loop -- OSM centrelines routinely have that shape. */
inline Vec3 CatmullRom(const Vec3& P0, const Vec3& P1, const Vec3& P2, const Vec3& P3, double T)
{
    const double Alpha = 0.5;
    auto Knot = [Alpha](double Base, const Vec3& A, const Vec3& B)
    {
        const double D = Length(B - A);
        return Base + std::pow(D > 1e-9 ? D : 1e-9, Alpha);
    };
    const double T0 = 0.0;
    const double T1 = Knot(T0, P0, P1);
    const double T2 = Knot(T1, P1, P2);
    const double T3 = Knot(T2, P2, P3);
    const double T_ = T1 + Clamp(T, 0.0, 1.0) * (T2 - T1);
    auto Lerp = [](const Vec3& A, const Vec3& B, double Lo, double Hi, double X)
    {
        const double Span = Hi - Lo;
        if (std::abs(Span) < 1e-12) return A;
        const double W = (X - Lo) / Span;
        return A * (1.0 - W) + B * W;
    };
    const Vec3 A1 = Lerp(P0, P1, T0, T1, T_);
    const Vec3 A2 = Lerp(P1, P2, T1, T2, T_);
    const Vec3 A3 = Lerp(P2, P3, T2, T3, T_);
    const Vec3 B1 = Lerp(A1, A2, T0, T2, T_);
    const Vec3 B2 = Lerp(A2, A3, T1, T3, T_);
    return Lerp(B1, B2, T1, T2, T_);
}

/** How many densified points BuildArcTable will write for a route of Count control
 * points. Callers size their buffers with this before building. Returns 0 for a
 * degenerate route. PerSegment is clamped to [1, 64]. */
inline int DensifiedPointCount(int Count, bool bClosed, int PerSegment)
{
    if (Count < 2) return 0;
    const int Steps = static_cast<int>(Clamp(static_cast<double>(PerSegment), 1.0, 64.0));
    const int Segments = bClosed ? Count : Count - 1;
    return Segments * Steps + 1;
}

/** Densify a control polyline into an arc-length-tabulated polyline.
 *
 * OutPoints and OutCumulative must each hold DensifiedPointCount entries. PerSegment > 1
 * runs a centripetal Catmull-Rom through the control points; PerSegment == 1 reproduces
 * the control polyline exactly, which is what a straight rail alignment wants.
 * OutCumulative[0] is 0 and the array is non-decreasing. Returns total length in cm. */
inline double BuildArcTable(const Vec3* Points, int Count, bool bClosed, int PerSegment,
                            Vec3* OutPoints, double* OutCumulative)
{
    const int Total = DensifiedPointCount(Count, bClosed, PerSegment);
    if (!Points || !OutPoints || !OutCumulative || Total <= 0) return 0.0;
    const int Steps = static_cast<int>(Clamp(static_cast<double>(PerSegment), 1.0, 64.0));
    const int Segments = bClosed ? Count : Count - 1;
    auto At = [Points, Count, bClosed](int I) -> const Vec3&
    {
        if (bClosed) return Points[((I % Count) + Count) % Count];
        return Points[static_cast<int>(Clamp(static_cast<double>(I), 0.0, static_cast<double>(Count - 1)))];
    };
    int Written = 0;
    for (int S = 0; S < Segments; ++S)
    {
        for (int K = 0; K < Steps; ++K)
        {
            const double T = static_cast<double>(K) / static_cast<double>(Steps);
            OutPoints[Written++] = Steps == 1 ? At(S) : CatmullRom(At(S - 1), At(S), At(S + 1), At(S + 2), T);
        }
    }
    OutPoints[Written++] = bClosed ? At(0) : At(Count - 1);
    OutCumulative[0] = 0.0;
    for (int I = 1; I < Written; ++I)
    {
        const double Step = Length(OutPoints[I] - OutPoints[I - 1]);
        OutCumulative[I] = OutCumulative[I - 1] + (std::isfinite(Step) ? Step : 0.0);
    }
    return OutCumulative[Written - 1];
}

/** Bring a distance into [0, TotalLength). Closed routes wrap; open routes clamp (an
 * open route is a shuttle -- the caller reverses it, this only keeps S in range). */
inline double WrapDistance(double S, double TotalLength, bool bClosed)
{
    if (!std::isfinite(S) || !(TotalLength > 1e-6)) return 0.0;
    if (!bClosed) return Clamp(S, 0.0, TotalLength);
    double W = std::fmod(S, TotalLength);
    if (W < 0) W += TotalLength;
    return W;
}

/** Sample a densified route at arc length S. OutTangent is a unit vector. Returns false
 * on a degenerate route, leaving the outputs untouched. Binary search over the cumulative
 * table: O(log N) per vehicle per step, no allocation. */
inline bool SampleRoute(const Vec3* Points, const double* Cumulative, int Count, bool bClosed,
                        double S, Vec3& OutPosition, Vec3& OutTangent)
{
    if (!Points || !Cumulative || Count < 2) return false;
    const double Total = Cumulative[Count - 1];
    if (!(Total > 1e-6)) return false;
    const double D = WrapDistance(S, Total, bClosed);
    int Lo = 0, Hi = Count - 1;
    while (Hi - Lo > 1)
    {
        const int Mid = (Lo + Hi) / 2;
        if (Cumulative[Mid] <= D) Lo = Mid; else Hi = Mid;
    }
    const double Span = Cumulative[Hi] - Cumulative[Lo];
    const double T = Span > 1e-9 ? (D - Cumulative[Lo]) / Span : 0.0;
    OutPosition = Points[Lo] * (1.0 - T) + Points[Hi] * T;
    Vec3 Tangent = Normalized(Points[Hi] - Points[Lo]);
    if (Length(Tangent) < 1e-9)
    {
        // Duplicate points across the sampled span: walk outward for a usable direction
        // rather than handing the caller a zero yaw that would snap a vehicle flat.
        for (int Offset = 1; Offset < Count && Length(Tangent) < 1e-9; ++Offset)
        {
            const int A = std::max(0, Lo - Offset);
            const int B = std::min(Count - 1, Hi + Offset);
            Tangent = Normalized(Points[B] - Points[A]);
        }
    }
    OutTangent = Length(Tangent) > 1e-9 ? Tangent : Vec3{1, 0, 0};
    return true;
}

/** Apply a lane offset (positive = to the driver's right) and a ride height to a sampled
 * centreline pose. Yaw comes from the tangent's XY part only, so a graded route does not
 * roll the lane offset out of the horizontal. */
inline Vec3 ApplyLaneOffset(const Vec3& Position, const Vec3& Tangent, double LaneOffsetCm, double RideHeightCm)
{
    const Vec3 Right = RightFromYaw(YawDegrees(Tangent));
    return Position + Right * LaneOffsetCm + Vec3{0, 0, RideHeightCm};
}

/** Forward gap in cm from BehindS to AheadS along the route, in [0, TotalLength).
 * On a closed route this is the wrapped forward distance, which is exactly what a
 * follower needs. On an open route a "leader" that is actually behind yields 0, which
 * the caller must read as "no leader" and replace with a large gap. */
inline double ForwardGap(double BehindS, double AheadS, double TotalLength, bool bClosed)
{
    if (!(TotalLength > 1e-6) || !std::isfinite(BehindS) || !std::isfinite(AheadS)) return 0.0;
    double Gap = AheadS - BehindS;
    if (bClosed)
    {
        Gap = std::fmod(Gap, TotalLength);
        if (Gap < 0) Gap += TotalLength;
    }
    return std::max(0.0, Gap);
}

/** Nearest point on a densified route to Target, returned as an arc distance.
 *
 * This is how an authored stop becomes a stop distance: routes.json gives every stop a
 * world position, and the actor projects it onto the arc table it built itself. Nothing
 * therefore depends on the generator and the runtime densifying the polyline identically,
 * which they otherwise would have to, in two languages.
 *
 * Only the XY plane is used for the match, so a stop authored at kerb height still binds
 * to the right point on a graded route. Returns false on a degenerate route; OutErrorCm
 * receives the planar residual, which the caller should report rather than swallow -- a
 * large residual means the stop was authored off its route. */
inline bool ProjectOntoRoute(const Vec3* Points, const double* Cumulative, int Count,
                             const Vec3& Target, double& OutDistanceCm, double& OutErrorCm)
{
    if (!Points || !Cumulative || Count < 2 || !Finite(Target)) return false;
    double BestSquared = -1.0;
    for (int I = 1; I < Count; ++I)
    {
        const Vec3 A = Points[I - 1];
        const Vec3 B = Points[I];
        const double DX = B.X - A.X, DY = B.Y - A.Y;
        const double LengthSquared = DX * DX + DY * DY;
        const double T = LengthSquared > 1e-9
            ? Clamp(((Target.X - A.X) * DX + (Target.Y - A.Y) * DY) / LengthSquared, 0.0, 1.0) : 0.0;
        const double EX = Target.X - (A.X + DX * T), EY = Target.Y - (A.Y + DY * T);
        const double Squared = EX * EX + EY * EY;
        if (BestSquared < 0.0 || Squared < BestSquared)
        {
            BestSquared = Squared;
            OutDistanceCm = Cumulative[I - 1] + (Cumulative[I] - Cumulative[I - 1]) * T;
        }
    }
    if (BestSquared < 0.0) return false;
    OutErrorCm = std::sqrt(BestSquared);
    return true;
}

/** Signed arc distance from FromS to ToS, wrapped into (-TotalLength/2, TotalLength/2].
 *
 * Positive means ahead, negative means just behind. This is the distance the braking
 * controller must use once a stop has been acquired: with the unsigned ForwardGap, a
 * vehicle that overshoots the stop line by a few centimetres reads as ONE LAP SHORT of
 * it and accelerates away for another circuit instead of settling on the line. */
inline double SignedDistanceAlong(double FromS, double ToS, double TotalLength, bool bClosed)
{
    if (!(TotalLength > 1e-6) || !std::isfinite(FromS) || !std::isfinite(ToS)) return 0.0;
    if (!bClosed) return ToS - FromS;
    double D = std::fmod(ToS - FromS, TotalLength);
    if (D < 0) D += TotalLength;
    if (D > TotalLength * 0.5) D -= TotalLength;
    return D;
}

/** Evenly spaced start distances around a route with a deterministic jitter, so traffic
 * does not read as a parade. Returns a distance in [0, TotalLength). */
inline double SpawnDistanceFor(int Index, int Count, double TotalLength, double JitterCm, uint32_t Seed)
{
    if (Count <= 0 || !(TotalLength > 1e-6)) return 0.0;
    const double Even = TotalLength * (static_cast<double>(std::max(0, Index)) / static_cast<double>(Count));
    const double Jitter = JitterCm > 0.0 ? HashRange(Seed, static_cast<uint32_t>(Index), 7u, -JitterCm, JitterCm) : 0.0;
    return WrapDistance(Even + Jitter, TotalLength, true);
}

// ---------------------------------------------------------------------------
// Longitudinal control: car-following and stop-and-go
// ---------------------------------------------------------------------------

/** Longitudinal parameters for one vehicle class. Accelerations are cm/s^2 and are held
 * positive; the model supplies the sign. */
struct FollowParams
{
    double DesiredSpeedCmPerSecond = 900.0;   // ~32 km/h, an urban approach road
    double MinGapCm = 450.0;                  // bumper-to-bumper standstill gap
    double TimeHeadwaySeconds = 1.4;
    double MaxAccelerationCmPerSecond2 = 130.0;
    double ComfortDecelerationCmPerSecond2 = 200.0;
    double EmergencyDecelerationCmPerSecond2 = 600.0;
};

/** Standstill-plus-headway target gap for the Intelligent Driver Model. */
inline double DesiredGapCm(double SpeedCmPerSecond, double ApproachRateCmPerSecond, const FollowParams& P)
{
    const double V = std::max(0.0, SpeedCmPerSecond);
    const double A = std::max(1e-3, P.MaxAccelerationCmPerSecond2);
    const double B = std::max(1e-3, P.ComfortDecelerationCmPerSecond2);
    const double Dynamic = V * ApproachRateCmPerSecond / (2.0 * std::sqrt(A * B));
    return std::max(0.0, P.MinGapCm) + std::max(0.0, V * std::max(0.0, P.TimeHeadwaySeconds) + Dynamic);
}

/** Intelligent Driver Model acceleration, cm/s^2, signed. GapCm is bumper-to-bumper
 * clearance to the vehicle ahead; pass a huge value when there is no leader. A
 * non-positive gap (an authored overlap, or a leader that stopped on top of the
 * follower) returns the emergency deceleration rather than dividing by zero. */
inline double FollowAcceleration(double SpeedCmPerSecond, double LeadSpeedCmPerSecond, double GapCm, const FollowParams& P)
{
    const double V0 = std::max(1e-3, P.DesiredSpeedCmPerSecond);
    const double V = std::max(0.0, std::isfinite(SpeedCmPerSecond) ? SpeedCmPerSecond : 0.0);
    const double A = std::max(1e-3, P.MaxAccelerationCmPerSecond2);
    const double Free = A * (1.0 - std::pow(V / V0, 4.0));
    if (!std::isfinite(GapCm) || GapCm > 1e7) return Clamp(Free, -P.EmergencyDecelerationCmPerSecond2, A);
    if (GapCm <= 1e-3) return -P.EmergencyDecelerationCmPerSecond2;
    const double Approach = V - std::max(0.0, LeadSpeedCmPerSecond);
    const double Star = DesiredGapCm(V, Approach, P);
    const double Interaction = A * (Star / GapCm) * (Star / GapCm);
    return Clamp(Free - Interaction, -P.EmergencyDecelerationCmPerSecond2, A);
}

/** Constant deceleration that just reaches zero speed in DistanceCm; negative. At or past
 * the stop line this returns the emergency deceleration. */
inline double StopLineAcceleration(double SpeedCmPerSecond, double DistanceCm, const FollowParams& P)
{
    const double V = std::max(0.0, SpeedCmPerSecond);
    if (!std::isfinite(DistanceCm) || DistanceCm <= 1.0) return V > 0.0 ? -P.EmergencyDecelerationCmPerSecond2 : 0.0;
    const double Required = (V * V) / (2.0 * DistanceCm);
    return -Clamp(Required, 0.0, P.EmergencyDecelerationCmPerSecond2);
}

/** Distance needed to come to rest at the comfort deceleration, cm. */
inline double ComfortBrakingDistanceCm(double SpeedCmPerSecond, const FollowParams& P)
{
    const double V = std::max(0.0, SpeedCmPerSecond);
    return (V * V) / (2.0 * std::max(1e-3, P.ComfortDecelerationCmPerSecond2));
}

/** Integrate speed by an acceleration over Dt, never below 0 nor above MaxSpeed. Dt is
 * clamped so one hitched frame cannot launch a vehicle down the route. */
inline double IntegrateSpeed(double SpeedCmPerSecond, double AccelerationCmPerSecond2, double Dt, double MaxSpeedCmPerSecond)
{
    if (!std::isfinite(Dt) || Dt <= 0.0) return std::max(0.0, SpeedCmPerSecond);
    const double Step = Clamp(Dt, 0.0, 0.5);
    const double A = std::isfinite(AccelerationCmPerSecond2) ? AccelerationCmPerSecond2 : 0.0;
    const double V = std::max(0.0, SpeedCmPerSecond) + A * Step;
    return Clamp(V, 0.0, std::max(0.0, MaxSpeedCmPerSecond));
}

// ---------------------------------------------------------------------------
// Station arrival schedule
// ---------------------------------------------------------------------------

/** Randomised service headway, seconds. The user-facing default for the light-rail line
 * is 120..300 s, i.e. a train every two to five minutes. */
inline double HeadwayForRun(uint32_t Seed, uint32_t RunIndex, double MinSeconds, double MaxSeconds)
{
    const double Lo = std::max(1.0, std::min(MinSeconds, MaxSeconds));
    const double Hi = std::max(Lo, std::max(MinSeconds, MaxSeconds));
    return HashRange(Seed, RunIndex, 101u, Lo, Hi);
}

/** Absolute time of the RunIndex-th departure from the head of the line, given the first
 * departure time. Deterministic and strictly increasing in RunIndex. O(RunIndex): callers
 * advance one run at a time, they never query far ahead. */
inline double ScheduledDepartureTime(uint32_t Seed, int RunIndex, double FirstDepartureSeconds, double MinSeconds, double MaxSeconds)
{
    double T = std::isfinite(FirstDepartureSeconds) ? FirstDepartureSeconds : 0.0;
    for (int I = 0; I < std::max(0, RunIndex); ++I)
    {
        T += HeadwayForRun(Seed, static_cast<uint32_t>(I), MinSeconds, MaxSeconds);
    }
    return T;
}

/** Dwell for one (run, stop) pair, seconds, inside the authored window. The user-facing
 * default for the train is 20..40 s. */
inline double DwellForStop(uint32_t Seed, int RunIndex, int StopIndex, double MinSeconds, double MaxSeconds)
{
    const double Lo = std::max(0.0, std::min(MinSeconds, MaxSeconds));
    const double Hi = std::max(Lo, std::max(MinSeconds, MaxSeconds));
    const uint32_t Index = HashCombine(static_cast<uint32_t>(std::max(0, RunIndex)), static_cast<uint32_t>(std::max(0, StopIndex)));
    return HashRange(Seed, Index, 103u, Lo, Hi);
}

/** How many pedestrians the crowd system is asked to move for one call at a stop, scaled
 * by the global density multiplier and clamped so a mis-typed multiplier cannot ask the
 * crowd for an unbounded number of figures. */
inline int BoardingCountFor(uint32_t Seed, int VehicleId, int StopIndex, int RunIndex,
                            int MinCount, int MaxCount, double DensityMultiplier)
{
    if (MaxCount <= 0) return 0;
    const int Lo = std::max(0, std::min(MinCount, MaxCount));
    const int Hi = std::max(Lo, MaxCount);
    const uint32_t Index = HashCombine(HashCombine(static_cast<uint32_t>(std::max(0, VehicleId)),
                                                   static_cast<uint32_t>(std::max(0, StopIndex))),
                                       static_cast<uint32_t>(std::max(0, RunIndex)));
    const int Base = HashIntRange(Seed, Index, 107u, Lo, Hi);
    const double Density = Clamp(std::isfinite(DensityMultiplier) ? DensityMultiplier : 1.0, 0.0, 8.0);
    const int Scaled = static_cast<int>(std::lround(Base * Density));
    return static_cast<int>(Clamp(static_cast<double>(Scaled), 0.0, static_cast<double>(Hi) * 8.0));
}

// ---------------------------------------------------------------------------
// Dwell / door state machine
// ---------------------------------------------------------------------------

enum class StopPhase : uint8_t
{
    Running,       // between stops, following the vehicle in front
    Braking,       // stop line acquired, decelerating to it
    DoorsOpening,  // stopped, doors travelling open
    Dwelling,      // doors open, boarding
    DoorsClosing,  // dwell expired, doors travelling shut
    Departing      // doors shut, accelerating back to the desired speed
};

/** Timings and thresholds for the stop cycle. The same machine drives a bus and a train;
 * only the numbers differ. */
struct DwellConfig
{
    double DoorOpenSeconds = 1.6;
    double DoorCloseSeconds = 1.8;
    double MinDwellSeconds = 20.0;
    double MaxDwellSeconds = 40.0;
    double ArrivalToleranceCm = 120.0;          // how close to the stop line counts as arrived
    double StoppedSpeedCmPerSecond = 4.0;       // below this the vehicle is at rest
    double BrakingMarginCm = 600.0;             // lead over the comfort braking distance
    double DepartureSpeedFraction = 0.55;       // leave Departing at this share of desired speed
    double MaxDepartingSeconds = 20.0;          // and unconditionally after this long
    double DoorTravelCm = 55.0;                 // leaf travel used by DoorOffsetCm
};

/** Live per-vehicle stop state. Plain data; the actor keeps one per vehicle instance. */
struct StopState
{
    StopPhase Phase = StopPhase::Running;
    double PhaseSeconds = 0.0;
    double DwellSeconds = 0.0;     // drawn on entering DoorsOpening
    double DoorFraction = 0.0;     // 0 shut, 1 fully open
    int TargetStopIndex = -1;      // stop being approached or served
    int ServedStopIndex = -1;      // last stop whose doors actually opened
    int RunIndex = 0;              // stops this vehicle has completed
};

/** Edge events from one AdvanceStopState call. The actor turns bDoorsOpened into a
 * RequestBoarding broadcast and bDoorsClosed into the alighting half. */
struct StopEvents
{
    bool bBeganBraking = false;
    bool bDoorsOpened = false;
    bool bDoorsClosed = false;
    bool bDeparted = false;
};

/** Door leaf offset in cm for a door fraction, smoothstepped so the leaf eases at both
 * ends instead of snapping. Used either as a mesh offset or as a material parameter. */
inline double DoorOffsetCm(double Fraction, double TravelCm)
{
    const double F = Clamp(std::isfinite(Fraction) ? Fraction : 0.0, 0.0, 1.0);
    return std::max(0.0, TravelCm) * (F * F * (3.0 - 2.0 * F));
}

/** True when the vehicle should begin braking for a stop line DistanceCm ahead. */
inline bool ShouldBeginBraking(double SpeedCmPerSecond, double DistanceCm, const FollowParams& P, const DwellConfig& C)
{
    if (!std::isfinite(DistanceCm) || DistanceCm < 0.0) return true;
    return DistanceCm <= ComfortBrakingDistanceCm(SpeedCmPerSecond, P) + std::max(0.0, C.BrakingMarginCm);
}

/** Advance one vehicle's stop cycle.
 *
 * DistanceToStopCm is the remaining arc length to the current target stop line; it is
 * ignored once the doors are moving. SpeedCmPerSecond is the speed the longitudinal
 * controller produced this step. Seed/VehicleId feed the dwell draw so two buses at the
 * same stop do not dwell for identical times.
 *
 * The machine never runs backwards and never skips a phase, so a hitched frame cannot
 * open doors on a moving vehicle: DoorsOpening is entered only from Braking, and only
 * when the vehicle is both slow AND within ArrivalToleranceCm of the stop line. */
inline StopEvents AdvanceStopState(StopState& State, double Dt, double SpeedCmPerSecond, double DistanceToStopCm,
                                   const FollowParams& P, const DwellConfig& C,
                                   uint32_t Seed, int VehicleId)
{
    StopEvents Events;
    if (!std::isfinite(Dt) || Dt <= 0.0) return Events;
    const double Step = Clamp(Dt, 0.0, 0.5);
    State.PhaseSeconds += Step;
    const double Speed = std::max(0.0, std::isfinite(SpeedCmPerSecond) ? SpeedCmPerSecond : 0.0);

    switch (State.Phase)
    {
    case StopPhase::Running:
        if (State.TargetStopIndex >= 0 && ShouldBeginBraking(Speed, DistanceToStopCm, P, C))
        {
            State.Phase = StopPhase::Braking;
            State.PhaseSeconds = 0.0;
            Events.bBeganBraking = true;
        }
        break;

    case StopPhase::Braking:
        if (Speed <= C.StoppedSpeedCmPerSecond && std::abs(DistanceToStopCm) <= std::max(1.0, C.ArrivalToleranceCm))
        {
            State.Phase = StopPhase::DoorsOpening;
            State.PhaseSeconds = 0.0;
            State.DwellSeconds = DwellForStop(HashCombine(Seed, static_cast<uint32_t>(std::max(0, VehicleId))),
                                              State.RunIndex, State.TargetStopIndex, C.MinDwellSeconds, C.MaxDwellSeconds);
        }
        break;

    case StopPhase::DoorsOpening:
    {
        const double Span = std::max(1e-3, C.DoorOpenSeconds);
        State.DoorFraction = Clamp(State.PhaseSeconds / Span, 0.0, 1.0);
        if (State.PhaseSeconds >= Span)
        {
            State.DoorFraction = 1.0;
            State.Phase = StopPhase::Dwelling;
            State.PhaseSeconds = 0.0;
            State.ServedStopIndex = State.TargetStopIndex;
            Events.bDoorsOpened = true;
        }
        break;
    }

    case StopPhase::Dwelling:
        State.DoorFraction = 1.0;
        if (State.PhaseSeconds >= std::max(0.0, State.DwellSeconds))
        {
            State.Phase = StopPhase::DoorsClosing;
            State.PhaseSeconds = 0.0;
        }
        break;

    case StopPhase::DoorsClosing:
    {
        const double Span = std::max(1e-3, C.DoorCloseSeconds);
        State.DoorFraction = Clamp(1.0 - State.PhaseSeconds / Span, 0.0, 1.0);
        if (State.PhaseSeconds >= Span)
        {
            State.DoorFraction = 0.0;
            State.Phase = StopPhase::Departing;
            State.PhaseSeconds = 0.0;
            State.RunIndex += 1;
            Events.bDoorsClosed = true;
        }
        break;
    }

    case StopPhase::Departing:
        State.DoorFraction = 0.0;
        if (Speed >= P.DesiredSpeedCmPerSecond * Clamp(C.DepartureSpeedFraction, 0.0, 1.0)
            || State.PhaseSeconds >= std::max(1.0, C.MaxDepartingSeconds))
        {
            State.Phase = StopPhase::Running;
            State.PhaseSeconds = 0.0;
            Events.bDeparted = true;
        }
        break;
    }
    return Events;
}

/** True while the vehicle must be held at rest: the doors are not fully shut. */
inline bool IsHeldAtStop(const StopState& State)
{
    return State.Phase == StopPhase::DoorsOpening || State.Phase == StopPhase::Dwelling || State.Phase == StopPhase::DoorsClosing;
}

/** The longitudinal acceleration for one vehicle this step: the more restrictive of
 * car-following and the stop line, and a hard hold while the doors are not shut. This is
 * the single entry point the actor uses, so the two controllers can never disagree. */
inline double LongitudinalAcceleration(const StopState& State, double SpeedCmPerSecond, double LeadSpeedCmPerSecond,
                                       double GapCm, double DistanceToStopCm, const FollowParams& P)
{
    if (IsHeldAtStop(State)) return -P.EmergencyDecelerationCmPerSecond2;
    const double Follow = FollowAcceleration(SpeedCmPerSecond, LeadSpeedCmPerSecond, GapCm, P);
    if (State.Phase != StopPhase::Braking || State.TargetStopIndex < 0) return Follow;
    return std::min(Follow, StopLineAcceleration(SpeedCmPerSecond, DistanceToStopCm, P));
}

// ---------------------------------------------------------------------------
// Articulated consist
// ---------------------------------------------------------------------------

/** Arc-length offset behind the head reference point for the centre of car CarIndex.
 * Car 0 sits fully behind the head point, so a CarCount set occupies
 * CarCount * CarLength + (CarCount - 1) * Gap of track. */
inline double CarCentreOffsetCm(int CarIndex, double CarLengthCm, double CouplingGapCm)
{
    const double L = std::max(0.0, CarLengthCm);
    const double G = std::max(0.0, CouplingGapCm);
    return L * 0.5 + std::max(0, CarIndex) * (L + G);
}

/** Pose one car of an articulated consist by sampling its two bogies and averaging.
 * Taking the chord between the bogies, rather than the tangent at the car centre, is what
 * makes a long car read as rigid through a curve instead of bending with the rail.
 * Returns false on a degenerate route. */
inline bool SampleCarPose(const Vec3* Points, const double* Cumulative, int Count, bool bClosed,
                          double HeadDistanceCm, int CarIndex, double CarLengthCm, double CouplingGapCm,
                          double BogieInsetCm, double LaneOffsetCm, double RideHeightCm,
                          Vec3& OutPosition, double& OutYawDegrees, double& OutPitchDegrees)
{
    const double Centre = HeadDistanceCm - CarCentreOffsetCm(CarIndex, CarLengthCm, CouplingGapCm);
    const double HalfBase = std::max(1.0, CarLengthCm * 0.5 - std::max(0.0, BogieInsetCm));
    Vec3 Front{}, Rear{}, TangentFront{}, TangentRear{};
    if (!SampleRoute(Points, Cumulative, Count, bClosed, Centre + HalfBase, Front, TangentFront)) return false;
    if (!SampleRoute(Points, Cumulative, Count, bClosed, Centre - HalfBase, Rear, TangentRear)) return false;
    const Vec3 Chord = Front - Rear;
    const Vec3 Direction = Length(Chord) > 1e-6 ? Normalized(Chord) : TangentFront;
    OutYawDegrees = YawDegrees(Direction);
    OutPitchDegrees = PitchDegrees(Direction);
    OutPosition = ApplyLaneOffset((Front + Rear) * 0.5, Direction, LaneOffsetCm, RideHeightCm);
    return true;
}

// ---------------------------------------------------------------------------
// Bounded per-frame work. Same contract as MikdashCrowd::NextUpdateWindow, repeated here
// so the transit actor has no cross-header dependency.
// ---------------------------------------------------------------------------

struct UpdateWindow
{
    int FirstStart = 0, FirstCount = 0;
    int SecondStart = 0, SecondCount = 0;
    int NextCursor = 0;
    int Total() const { return FirstCount + SecondCount; }
    bool Wrapped() const { return SecondCount > 0; }
};

/** Round-robin budget: from Cursor, take up to Budget of Count vehicles, wrapping once.
 * Cost per frame is bounded whatever Count is; every vehicle is visited exactly once per
 * ceil(Count / Budget) frames. Out-of-range input yields an empty window, not a crash. */
inline UpdateWindow NextUpdateWindow(int Cursor, int Count, int Budget)
{
    UpdateWindow Window;
    if (Count <= 0 || Budget <= 0) return Window;
    if (Cursor < 0 || Cursor >= Count) Cursor = 0;
    const int Take = std::min(Budget, Count);
    Window.FirstStart = Cursor;
    Window.FirstCount = std::min(Take, Count - Cursor);
    const int Remaining = Take - Window.FirstCount;
    if (Remaining > 0)
    {
        Window.SecondStart = 0;
        Window.SecondCount = Remaining;
    }
    Window.NextCursor = (Cursor + Take) % Count;
    return Window;
}

inline int FramesPerSweep(int Count, int Budget)
{
    if (Count <= 0 || Budget <= 0) return 0;
    return (Count + Budget - 1) / Budget;
}

/** Seconds a vehicle has missed since its last visit. A round-robin vehicle must
 * integrate the whole sweep it slept through, not one frame, or the traffic crawls at
 * 1/N speed. Clamped so a hitch cannot teleport a bus through a stop.
 *
 * NOTE the coupling this creates: with catch-up, one vehicle is effectively simulated at
 * Budget/Count of the frame rate, so MaxStepSeconds must stay well under the time a
 * vehicle takes to cross ArrivalToleranceCm at its desired speed, or the stop-line test
 * can be stepped over. The 0.35 s default at 900 cm/s covers 315 cm, which is why the
 * dwell machine requires a LOW SPEED as well as a small distance -- distance alone would
 * be unsafe at these step sizes. */
inline double CatchUpSeconds(double DeltaSeconds, int Count, int Budget, double MaxStepSeconds = 0.35)
{
    if (!std::isfinite(DeltaSeconds) || DeltaSeconds <= 0.0) return 0.0;
    const int Frames = FramesPerSweep(Count, Budget);
    return Clamp(DeltaSeconds * std::max(1, Frames), 0.0, std::max(0.0, MaxStepSeconds));
}

// ---------------------------------------------------------------------------
// Instance variation and apportioning
// ---------------------------------------------------------------------------

/** Which body variant (and therefore which HISM component) a road vehicle uses. Blocked,
 * like the crowd's poses, so a contiguous global window maps to at most two contiguous
 * per-component ranges, which is what makes a batched transform update possible. */
inline int VariantIndexForInstance(int GlobalIndex, int TotalInstances, int VariantCount)
{
    if (VariantCount <= 1 || TotalInstances <= 0 || GlobalIndex < 0) return 0;
    const long long Scaled = static_cast<long long>(GlobalIndex) * VariantCount;
    const int Variant = static_cast<int>(Scaled / TotalInstances);
    return Variant < VariantCount ? Variant : VariantCount - 1;
}

/** First global index belonging to a variant block. VariantIndex == VariantCount is the
 * end sentinel and yields TotalInstances, so [Start(V), Start(V+1)) is the half-open
 * range of block V for every V including the last -- the single-variant case included,
 * which is why the count guard cannot be tested before the sentinel. */
inline int VariantBlockStart(int VariantIndex, int TotalInstances, int VariantCount)
{
    if (TotalInstances <= 0 || VariantCount <= 0 || VariantIndex <= 0) return 0;
    if (VariantIndex >= VariantCount) return TotalInstances;
    const long long Scaled = static_cast<long long>(VariantIndex) * TotalInstances;
    return static_cast<int>((Scaled + VariantCount - 1) / VariantCount);
}

/** Per-instance paint colour drawn from a palette, written as three floats in [0,1]. The
 * mesh carries a vertex-colour paint mask that multiplies this in, so one mesh yields many
 * cars. Deterministic in (Seed, Index). */
inline void PaintColourFor(uint32_t Seed, int Index, const double* PaletteRgb, int PaletteSize, double* OutRgb)
{
    if (!OutRgb) return;
    OutRgb[0] = OutRgb[1] = OutRgb[2] = 0.5;
    if (!PaletteRgb || PaletteSize <= 0) return;
    const int Pick = HashIntRange(Seed, static_cast<uint32_t>(std::max(0, Index)), 59u, 0, PaletteSize - 1);
    for (int I = 0; I < 3; ++I) OutRgb[I] = Clamp(PaletteRgb[Pick * 3 + I], 0.0, 1.0);
}

/** Apportion Total vehicles across routes by an authored weight, largest-remainder so the
 * parts sum to exactly Total. Routes with no weight get none. Returns the number actually
 * apportioned (Total unless every weight is zero). */
inline int ApportionVehicles(const double* Weights, int RouteCount, int Total, int* OutCounts)
{
    if (!Weights || !OutCounts || RouteCount <= 0) return 0;
    for (int I = 0; I < RouteCount; ++I) OutCounts[I] = 0;
    if (Total <= 0) return 0;
    double Sum = 0.0;
    for (int I = 0; I < RouteCount; ++I)
    {
        if (std::isfinite(Weights[I]) && Weights[I] > 0.0) Sum += Weights[I];
    }
    if (!(Sum > 0.0)) return 0;
    int Assigned = 0;
    for (int I = 0; I < RouteCount; ++I)
    {
        const double W = (std::isfinite(Weights[I]) && Weights[I] > 0.0) ? Weights[I] : 0.0;
        OutCounts[I] = W > 0.0 ? static_cast<int>(std::floor(Total * W / Sum)) : 0;
        Assigned += OutCounts[I];
    }
    // Largest remainder, each route taking at most one extra, ties broken by index so the
    // result is reproducible across runs and platforms.
    while (Assigned < Total)
    {
        int Best = -1;
        double BestRemainder = -1.0;
        for (int I = 0; I < RouteCount; ++I)
        {
            const double W = (std::isfinite(Weights[I]) && Weights[I] > 0.0) ? Weights[I] : 0.0;
            if (W <= 0.0) continue;
            const double Exact = Total * W / Sum;
            if (OutCounts[I] > static_cast<int>(std::floor(Exact))) continue;   // already took its extra
            const double Remainder = Exact - std::floor(Exact);
            if (Remainder > BestRemainder)
            {
                BestRemainder = Remainder;
                Best = I;
            }
        }
        if (Best < 0)
        {
            for (int I = 0; I < RouteCount && Best < 0; ++I)
            {
                if (std::isfinite(Weights[I]) && Weights[I] > 0.0) Best = I;
            }
            if (Best < 0) break;
        }
        OutCounts[Best] += 1;
        Assigned += 1;
    }
    return Assigned;
}

/** Scale an authored vehicle count by the global density multiplier, clamped to a hard
 * ceiling so a mis-typed multiplier cannot allocate an unbounded instance array. */
inline int ScaledVehicleCount(int AuthoredCount, double DensityMultiplier, int HardCeiling)
{
    if (AuthoredCount <= 0) return 0;
    const double Density = Clamp(std::isfinite(DensityMultiplier) ? DensityMultiplier : 1.0, 0.0, 8.0);
    const int Scaled = static_cast<int>(std::lround(AuthoredCount * Density));
    return static_cast<int>(Clamp(static_cast<double>(Scaled), 0.0, static_cast<double>(std::max(0, HardCeiling))));
}

/** Nearest stop ahead of a vehicle: the index into StopDistances with the smallest
 * strictly-forward gap, and that gap. Returns -1 when there is none. The stop the vehicle
 * is currently standing at is skipped by requiring the gap to exceed SkipWithinCm, which
 * is what stops a departing vehicle from immediately re-acquiring the stop it just left.
 *
 * CALL THIS ONLY WHILE StopPhase::Running. Once a target is acquired it must be LATCHED
 * until departure, and its remaining distance measured with SignedDistanceAlong: keep
 * re-querying while braking and the shrinking gap crosses SkipWithinCm, the query hands
 * back the NEXT stop, and the vehicle accelerates straight through the one it was
 * stopping at. AMikdashTransit::AdvanceVehicle follows exactly that rule. */
inline int NextStopAhead(const double* StopDistances, int StopCount, double VehicleS, double TotalLength, bool bClosed,
                         double SkipWithinCm, double& OutGapCm)
{
    OutGapCm = 0.0;
    if (!StopDistances || StopCount <= 0) return -1;
    int Best = -1;
    double BestGap = 0.0;
    for (int I = 0; I < StopCount; ++I)
    {
        const double Gap = ForwardGap(VehicleS, StopDistances[I], TotalLength, bClosed);
        if (Gap <= std::max(0.0, SkipWithinCm)) continue;
        if (Best < 0 || Gap < BestGap)
        {
            Best = I;
            BestGap = Gap;
        }
    }
    OutGapCm = Best >= 0 ? BestGap : 0.0;
    return Best;
}
}  // namespace MikdashTransit
