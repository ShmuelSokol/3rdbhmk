#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

// Engine-independent arithmetic for AMikdashTransitBoardingBridge, the layer that turns a
// transit "doors are open for N seconds" event into background figures boarding and
// alighting. Units: centimetres, seconds, degrees. No Unreal types, no allocation, no
// globals. Covered by Plugins/MikdashRuntime/Tests/BoardingBridgeMathTest.cpp.
//
// What this decides: how many of a requested group a dwell can actually host, WHEN each
// boarder must leave the platform so the last one is through the door before the doors
// close, when each alighter steps off, which alighters stop to photograph the Mount and for
// how long, whether one more group may start under the concurrency cap, and where on the
// kerb-side apron figures may stand so none is ever inside the vehicle.
//
// What it does NOT decide: anything about the world. Ground height, keep-outs, the
// vehicle body and the crowd's own zones are the actor's business, and the actor refuses
// a plan this header produced whenever the world says no.
namespace MikdashBoardingBridge
{
constexpr double Pi = 3.14159265358979323846;

/** A dwell shorter than this cannot host an exchange at all: with the door-open and
 * door-close edges inside it there is no time for anyone to walk anywhere. */
constexpr double MinUsableDwellSeconds = 4.0;
/** No boarder walks further than this to a door; beyond it the figure was never
 * plausibly "waiting at the stop". Matches the crowd field's own transfer bound. */
constexpr double MaxWalkCm = 3000.0;
/** Share of the dwell given to alighting before boarders may reach the door. */
constexpr double AlightingShare = 0.45;

struct Vec2
{
    double X = 0, Y = 0;
};
inline Vec2 operator+(const Vec2& A, const Vec2& B) { return {A.X + B.X, A.Y + B.Y}; }
inline Vec2 operator-(const Vec2& A, const Vec2& B) { return {A.X - B.X, A.Y - B.Y}; }
inline Vec2 operator*(const Vec2& A, double S) { return {A.X * S, A.Y * S}; }
inline double Dot(const Vec2& A, const Vec2& B) { return A.X * B.X + A.Y * B.Y; }
inline double Length(const Vec2& A) { return std::sqrt(Dot(A, A)); }
inline bool Finite(const Vec2& A) { return std::isfinite(A.X) && std::isfinite(A.Y); }
inline double Clamp(double V, double Lo, double Hi) { return std::max(Lo, std::min(Hi, V)); }

// ---------------------------------------------------------------------------
// Deterministic hashing. Same construction as CrowdFieldMath.h / TransitMath.h so the
// bridge's randomness has the same character; kept local so this header stands alone.
// ---------------------------------------------------------------------------

inline uint32_t HashInt(uint32_t V)
{
    V ^= V >> 16; V *= 0x7feb352dU;
    V ^= V >> 15; V *= 0x846ca68bU;
    V ^= V >> 16;
    return V;
}
inline uint32_t HashCombine(uint32_t Seed, uint32_t Value) { return HashInt(Seed ^ (Value + 0x9e3779b9U + (Seed << 6) + (Seed >> 2))); }
/** Uniform in [0, 1). */
inline double HashUnit(uint32_t Seed, uint32_t Index, uint32_t Lane)
{
    return HashCombine(HashCombine(Seed, Index), Lane) * (1.0 / 4294967296.0);
}
inline double HashRange(uint32_t Seed, uint32_t Index, uint32_t Lane, double Lo, double Hi)
{
    return Lo + (Hi - Lo) * HashUnit(Seed, Index, Lane);
}

/** One seed per (stop, run, direction). The same vehicle run at the same stop always
 * produces the same group: same gather spots, same photographers, same walking speeds.
 * Alighting and boarding at the same call are different groups and get different seeds. */
inline uint32_t GroupSeed(uint32_t BaseSeed, int StopIndex, int RunIndex, bool bAlighting)
{
    const uint32_t Stop = static_cast<uint32_t>(std::max(0, StopIndex));
    const uint32_t Run = static_cast<uint32_t>(std::max(0, RunIndex));
    return HashCombine(HashCombine(HashCombine(BaseSeed, Stop), Run), bAlighting ? 0x51u : 0xA7u);
}

// ---------------------------------------------------------------------------
// The dwell window
// ---------------------------------------------------------------------------

/** How one dwell is divided. Times are seconds after the doors finished opening, which is
 * when AMikdashTransit fires. Alighters step off during [0, AlightEnd]; boarders may reach
 * the door from BoardStart and must ALL be through it by Deadline, which sits
 * CloseMargin before the doors begin to close. */
struct Window
{
    double AlightEnd = 0.0;
    double BoardStart = 0.0;
    double Deadline = 0.0;
    double Dwell = 0.0;
    bool bUsable = false;
};

inline Window DwellWindow(double SecondsAvailable, double CloseMarginSeconds = 1.0)
{
    Window W;
    if (!std::isfinite(SecondsAvailable) || !std::isfinite(CloseMarginSeconds) || CloseMarginSeconds < 0.0
        || SecondsAvailable < MinUsableDwellSeconds)
    {
        return W;
    }
    W.Dwell = SecondsAvailable;
    W.AlightEnd = SecondsAvailable * AlightingShare;
    W.BoardStart = W.AlightEnd;
    W.Deadline = SecondsAvailable - CloseMarginSeconds;
    W.bUsable = W.Deadline > W.BoardStart + 0.5;
    return W;
}

// ---------------------------------------------------------------------------
// Group sizing
// ---------------------------------------------------------------------------

/** How many people a door can pass in one phase of the window. Doors is the number of
 * doorways the figures can use; SecondsPerPerson is the time one person takes to step
 * through one doorway. Floors, so the last one is never scheduled on the deadline itself. */
inline int DoorThroughput(double PhaseSeconds, int Doors, double SecondsPerPerson)
{
    if (!std::isfinite(PhaseSeconds) || PhaseSeconds <= 0.0 || Doors <= 0
        || !std::isfinite(SecondsPerPerson) || SecondsPerPerson <= 0.0)
    {
        return 0;
    }
    // Person k (0-based) uses the door at slot floor(k / Doors) * SecondsPerPerson; the
    // last admitted person must have a slot strictly inside the phase.
    const double Slots = std::floor(PhaseSeconds / SecondsPerPerson);
    const double People = Slots * Doors;
    return static_cast<int>(Clamp(People, 0.0, 4096.0));
}

/** The size of the group the bridge actually animates. Requested is what the transit
 * layer asked for; the answer is bounded by what the doors can pass inside the phase,
 * the per-group cap, and the figures the bridge still has free. Below MinGroup the whole
 * group is refused (0) rather than showing a lone straggler for a request of twenty. */
inline int GroupSizeForDwell(int Requested, const Window& W, bool bAlighting, int Doors, double SecondsPerPerson,
                             int MaxPerGroup, int PoolAvailable, int MinGroup = 1)
{
    if (Requested <= 0 || !W.bUsable || MaxPerGroup <= 0 || PoolAvailable <= 0) return 0;
    const double Phase = bAlighting ? W.AlightEnd : (W.Deadline - W.BoardStart);
    const int Throughput = DoorThroughput(Phase, Doors, SecondsPerPerson);
    const int Admitted = std::min(std::min(Requested, Throughput), std::min(MaxPerGroup, PoolAvailable));
    return Admitted >= std::max(1, MinGroup) ? Admitted : 0;
}

// ---------------------------------------------------------------------------
// Concurrency
// ---------------------------------------------------------------------------

/** Nothing in the transit layer caps concurrent exchanges: sixteen stops can all have a
 * vehicle at the kerb at once. The bridge admits a new group only under this cap. */
inline bool AdmitGroup(int ActiveGroups, int Cap)
{
    return Cap > 0 && ActiveGroups >= 0 && ActiveGroups < Cap;
}

// ---------------------------------------------------------------------------
// Timing of each figure
// ---------------------------------------------------------------------------

/** When alighter k steps off the vehicle. A short reaction after the doors open, then
 * the doors release people at SecondsPerPerson each. */
inline double AlightStepOutSeconds(int Member, int Doors, double SecondsPerPerson, double ReactionSeconds = 0.4)
{
    const int Slot = Member / std::max(1, Doors);
    return ReactionSeconds + Slot * SecondsPerPerson;
}

struct ConvergePlan
{
    double DepartAt = 0.0;    // seconds after the doors opened that this boarder starts walking
    double ArriveAt = 0.0;    // seconds after the doors opened that this boarder is through the door
    bool bFits = false;       // false: this person cannot make the door before Deadline and is not animated
};

/** Schedule boarder k so the LAST boarder is through the door before Deadline. Each
 * boarder is given a door slot from BoardStart onward and leaves the platform just early
 * enough to arrive at the slot; someone standing far away leaves at once and arrives when
 * the walk allows. Anyone whose earliest arrival is after Deadline does not fit. */
inline ConvergePlan ConvergeSchedule(int Member, double DistanceCm, double SpeedCmPerSecond, const Window& W,
                                     int Doors, double SecondsPerPerson)
{
    ConvergePlan Plan;
    if (!W.bUsable || Member < 0 || !std::isfinite(DistanceCm) || DistanceCm < 0.0 || DistanceCm > MaxWalkCm
        || !std::isfinite(SpeedCmPerSecond) || SpeedCmPerSecond <= 0.0 || !std::isfinite(SecondsPerPerson)
        || SecondsPerPerson <= 0.0)
    {
        return Plan;
    }
    const double Walk = DistanceCm / SpeedCmPerSecond;
    const int Slot = Member / std::max(1, Doors);
    const double SlotTime = W.BoardStart + Slot * SecondsPerPerson;
    Plan.ArriveAt = std::max(SlotTime, Walk);
    Plan.DepartAt = Plan.ArriveAt - Walk;
    Plan.bFits = Plan.ArriveAt <= W.Deadline;
    return Plan;
}

/** A per-figure walking speed, deterministic in the group seed. */
inline double WalkSpeedFor(uint32_t Seed, int Member, double MinCmPerSecond, double MaxCmPerSecond)
{
    const double Lo = std::min(MinCmPerSecond, MaxCmPerSecond);
    const double Hi = std::max(MinCmPerSecond, MaxCmPerSecond);
    return HashRange(Seed, static_cast<uint32_t>(std::max(0, Member)), 13u, Lo, Hi);
}

// ---------------------------------------------------------------------------
// Photographers
// ---------------------------------------------------------------------------

/** Mark exactly PhotographerCount of Count members as photographers, deterministically.
 * Members are ranked by a hash and the lowest-ranked K are chosen, so the same group
 * always picks the same people and a different run picks different ones. OutFlags must
 * hold Count entries. Returns the number actually marked (min of the two counts). */
inline int SelectPhotographers(uint32_t Seed, int Count, int PhotographerCount, bool* OutFlags)
{
    if (!OutFlags || Count <= 0) return 0;
    for (int I = 0; I < Count; ++I) OutFlags[I] = false;
    const int K = std::max(0, std::min(PhotographerCount, Count));
    if (K == 0) return 0;
    // Selection by rank: for each member count how many others hash lower; the K lowest
    // win. O(n^2) on groups of at most a few hundred, never allocates.
    int Marked = 0;
    for (int I = 0; I < Count && Marked < K; ++I)
    {
        const double Mine = HashUnit(Seed, static_cast<uint32_t>(I), 31u);
        int Lower = 0;
        for (int J = 0; J < Count; ++J)
        {
            if (J == I) continue;
            const double Other = HashUnit(Seed, static_cast<uint32_t>(J), 31u);
            if (Other < Mine || (Other == Mine && J < I)) ++Lower;
        }
        if (Lower < K) { OutFlags[I] = true; ++Marked; }
    }
    return Marked;
}

/** How long one photographer stands facing the Mount before walking on. */
inline double PhotographerHoldSeconds(uint32_t Seed, int Member, double MinSeconds = 4.0, double MaxSeconds = 9.0)
{
    const double Lo = std::min(MinSeconds, MaxSeconds);
    const double Hi = std::max(MinSeconds, MaxSeconds);
    return HashRange(Seed, static_cast<uint32_t>(std::max(0, Member)), 37u, Lo, Hi);
}

// ---------------------------------------------------------------------------
// The apron: where figures may stand at a stop
// ---------------------------------------------------------------------------

/** The kerb-side half-plane at one door. Out points from the door threshold toward the
 * shelter/platform face (away from the vehicle); Side runs along the kerb. Any point with
 * a positive depth along Out is outside the vehicle body; the vehicle is on the other
 * side of the door plane. */
struct Apron
{
    Vec2 Door;
    Vec2 Out;
    Vec2 Side;
};

/** Build the apron from this arrival's door point and the stop's platform-face point.
 * Refused when the two nearly coincide, because then "away from the vehicle" is unknown. */
inline bool MakeApron(const Vec2& Door, const Vec2& FurniturePoint, Apron& OutApron, double MinSeparationCm = 50.0)
{
    if (!Finite(Door) || !Finite(FurniturePoint)) return false;
    const Vec2 D = FurniturePoint - Door;
    const double L = Length(D);
    if (!(L >= MinSeparationCm)) return false;
    OutApron.Door = Door;
    OutApron.Out = D * (1.0 / L);
    OutApron.Side = Vec2{-OutApron.Out.Y, OutApron.Out.X};
    return true;
}

/** Signed distance of P beyond the door plane, positive on the kerb side. */
inline double KerbDepth(const Apron& A, const Vec2& P) { return Dot(P - A.Door, A.Out); }

/** True when P is at least ClearanceCm outside the vehicle body. */
inline bool OutsideVehicle(const Apron& A, const Vec2& P, double ClearanceCm)
{
    return Finite(P) && KerbDepth(A, P) >= ClearanceCm;
}

/** Where boarder k waits before the doors open: a jittered lattice on the apron between
 * NearCm and FarCm from the door plane, spread HalfWidthCm either side along the kerb.
 * Rows fill from the front, so a small group stands near the door and a big one deepens.
 * Every point is at least NearCm - JitterCm from the door plane. */
inline Vec2 GatherPoint(const Apron& A, uint32_t Seed, int Member, double NearCm, double FarCm, double HalfWidthCm,
                        double SpacingCm = 90.0, double JitterCm = 25.0)
{
    const double Spacing = std::max(30.0, SpacingCm);
    const int Columns = std::max(1, static_cast<int>(std::floor((2.0 * HalfWidthCm) / Spacing)));
    const int Row = std::max(0, Member) / Columns;
    const int Column = std::max(0, Member) % Columns;
    const double Depth = std::min(FarCm, NearCm + Row * Spacing) + HashRange(Seed, static_cast<uint32_t>(Member), 41u, -JitterCm, JitterCm);
    const double Across = (Column - (Columns - 1) * 0.5) * Spacing + HashRange(Seed, static_cast<uint32_t>(Member), 43u, -JitterCm, JitterCm);
    return A.Door + A.Out * std::max(NearCm - JitterCm, Depth) + A.Side * Across;
}

/** Where alighter k walks to: a fan on the kerb side, radius in [MinRadiusCm, MaxRadiusCm],
 * within +-HalfAngleDegrees of straight away from the door. With the default 70 degrees the
 * kerb depth is never less than 0.34 * MinRadiusCm, so a 600 cm minimum keeps everyone at
 * least two metres clear of the vehicle. */
inline Vec2 DispersalPoint(const Apron& A, uint32_t Seed, int Member, double MinRadiusCm, double MaxRadiusCm,
                           double HalfAngleDegrees = 70.0)
{
    const double Lo = std::max(0.0, std::min(MinRadiusCm, MaxRadiusCm));
    const double Hi = std::max(MinRadiusCm, MaxRadiusCm);
    const double Half = Clamp(HalfAngleDegrees, 0.0, 85.0) * Pi / 180.0;
    const double Radius = HashRange(Seed, static_cast<uint32_t>(std::max(0, Member)), 47u, Lo, Hi);
    const double Angle = HashRange(Seed, static_cast<uint32_t>(std::max(0, Member)), 53u, -Half, Half);
    return A.Door + A.Out * (Radius * std::cos(Angle)) + A.Side * (Radius * std::sin(Angle));
}

/** Yaw in degrees (0 faces +X) from From toward To; 0 when they coincide. */
inline double YawToward(const Vec2& From, const Vec2& To)
{
    const Vec2 D = To - From;
    if (std::abs(D.X) < 1e-9 && std::abs(D.Y) < 1e-9) return 0.0;
    return std::atan2(D.Y, D.X) * 180.0 / Pi;
}

/** Samples needed to walk a segment at StepCm so no keep-out narrower than StepCm is skipped. */
inline int SegmentSampleCount(double LengthCm, double StepCm = 25.0)
{
    if (!std::isfinite(LengthCm) || LengthCm <= 0.0) return 1;
    return std::max(1, static_cast<int>(std::ceil(LengthCm / std::max(1.0, StepCm))));
}

/** Position along a straight walk after Elapsed seconds; clamps at the target. */
inline Vec2 WalkPosition(const Vec2& From, const Vec2& To, double SpeedCmPerSecond, double Elapsed)
{
    const Vec2 D = To - From;
    const double L = Length(D);
    if (L < 1e-9) return To;
    if (!std::isfinite(Elapsed) || Elapsed <= 0.0 || !std::isfinite(SpeedCmPerSecond) || SpeedCmPerSecond <= 0.0) return From;
    const double T = Clamp(SpeedCmPerSecond * Elapsed / L, 0.0, 1.0);
    return From + D * T;
}

/** Height variation for a figure, matching the crowd field's adult range by default. */
inline double FigureScaleFor(uint32_t Seed, int Member, double MinScale = 0.92, double MaxScale = 1.08)
{
    return HashRange(Seed, static_cast<uint32_t>(std::max(0, Member)), 59u, std::min(MinScale, MaxScale), std::max(MinScale, MaxScale));
}

/** Garment tint index for the crowd material's custom data 1, in [0, PaletteSize). */
inline int GarmentIndexFor(uint32_t Seed, int Member, int PaletteSize)
{
    if (PaletteSize <= 1) return 0;
    const int Picked = static_cast<int>(HashUnit(Seed, static_cast<uint32_t>(std::max(0, Member)), 61u) * PaletteSize);
    return std::min(PaletteSize - 1, std::max(0, Picked));
}
}  // namespace MikdashBoardingBridge
