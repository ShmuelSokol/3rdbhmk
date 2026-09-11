#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

// Engine-independent crowd-field math shared by AMikdashCrowdField and the standalone tests.
// Units: centimeters, seconds, degrees. No Unreal types, no allocation, no globals.
//
// What this is: the arithmetic behind a background instanced crowd -- zone containment,
// a per-zone flow field, bounded per-frame work, speed/phase integration and the two
// distance thresholds (freeze, cull). It is deliberately NOT a navigation or avoidance
// system: instanced figures pass through one another and are not aware of the player.
namespace MikdashCrowd
{
constexpr double Pi = 3.14159265358979323846;

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
inline Vec2 Normalized(const Vec2& A)
{
    const double L = Length(A);
    return L > 1e-9 ? A * (1.0 / L) : Vec2{};
}
inline double Clamp(double V, double Lo, double Hi) { return std::max(Lo, std::min(Hi, V)); }
inline double DegToRad(double D) { return D * Pi / 180.0; }
inline double RadToDeg(double R) { return R * 180.0 / Pi; }
inline Vec2 FromDegrees(double D) { return {std::cos(DegToRad(D)), std::sin(DegToRad(D))}; }
/** Signed yaw in degrees for a direction, in (-180, 180]; zero vector yields 0. */
inline double YawDegrees(const Vec2& D)
{
    return (std::abs(D.X) < 1e-12 && std::abs(D.Y) < 1e-12) ? 0.0 : RadToDeg(std::atan2(D.Y, D.X));
}
inline double WrapDegrees(double D)
{
    if (!std::isfinite(D)) return 0.0;
    D = std::fmod(D + 180.0, 360.0);
    if (D < 0) D += 360.0;
    return D - 180.0;
}

// ---------------------------------------------------------------------------
// Deterministic hashing. The same seed must produce the same crowd in the editor
// preview, in PIE and in a packaged build, so std::rand and engine RNG are avoided.
// ---------------------------------------------------------------------------

/** 32-bit integer avalanche (Murmur3 finalizer). Pure; no state. */
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

// ---------------------------------------------------------------------------
// Zone containment
// ---------------------------------------------------------------------------

/** Even-odd ray cast against a closed simple polygon given as Count consecutive points.
 * Boundary points are not guaranteed either way; callers keep a margin. Degenerate
 * polygons (fewer than three points) contain nothing. */
inline bool PointInPolygon(const Vec2* Points, int Count, const Vec2& P)
{
    if (!Points || Count < 3 || !Finite(P)) return false;
    bool Inside = false;
    for (int I = 0, J = Count - 1; I < Count; J = I++)
    {
        const Vec2& A = Points[I];
        const Vec2& B = Points[J];
        if ((A.Y > P.Y) != (B.Y > P.Y))
        {
            const double Denominator = B.Y - A.Y;
            if (std::abs(Denominator) > 1e-12 && P.X < A.X + (B.X - A.X) * (P.Y - A.Y) / Denominator)
            {
                Inside = !Inside;
            }
        }
    }
    return Inside;
}

/** Squared distance from P to the segment AB. */
inline double DistanceSquaredToSegment(const Vec2& A, const Vec2& B, const Vec2& P)
{
    const Vec2 AB = B - A;
    const double LengthSquared = Dot(AB, AB);
    const double T = LengthSquared > 1e-12 ? Clamp(Dot(P - A, AB) / LengthSquared, 0.0, 1.0) : 0.0;
    const Vec2 D = P - (A + AB * T);
    return Dot(D, D);
}

/** Shortest distance from P to the polygon boundary (positive on both sides). */
inline double DistanceToPolygonEdge(const Vec2* Points, int Count, const Vec2& P)
{
    if (!Points || Count < 2) return 0.0;
    double Best = DistanceSquaredToSegment(Points[Count - 1], Points[0], P);
    for (int I = 1; I < Count; ++I)
    {
        Best = std::min(Best, DistanceSquaredToSegment(Points[I - 1], Points[I], P));
    }
    return std::sqrt(Best);
}

/** Inside the polygon and at least MarginCm clear of its boundary. Used so a figure is
 * never authored straddling a zone edge or hugging a protected polygon. */
inline bool PointInPolygonWithMargin(const Vec2* Points, int Count, const Vec2& P, double MarginCm)
{
    if (!PointInPolygon(Points, Count, P)) return false;
    return !(MarginCm > 0.0) || DistanceToPolygonEdge(Points, Count, P) >= MarginCm;
}

/** True when P is inside any protected polygon, expanded by MarginCm. Protected polygons
 * are the sanctuary interior and the Kotel wall face: an instance there is refused, whether
 * it is being seeded or has just been advanced by a step. */
inline bool PointInAnyProtected(const Vec2* Points, const int* Starts, const int* Counts, int PolygonCount, const Vec2& P, double MarginCm)
{
    if (!Points || !Starts || !Counts || PolygonCount <= 0) return false;
    for (int I = 0; I < PolygonCount; ++I)
    {
        if (Counts[I] < 3) continue;
        if (PointInPolygon(Points + Starts[I], Counts[I], P)) return true;
        if (MarginCm > 0.0 && DistanceToPolygonEdge(Points + Starts[I], Counts[I], P) < MarginCm)
        {
            // Outside but within the keep-out skirt.
            return true;
        }
    }
    return false;
}

/** Axis-aligned bounds of a polygon; returns false for a degenerate polygon. */
inline bool PolygonBounds(const Vec2* Points, int Count, Vec2& OutMin, Vec2& OutMax)
{
    if (!Points || Count < 3) return false;
    OutMin = OutMax = Points[0];
    for (int I = 1; I < Count; ++I)
    {
        OutMin.X = std::min(OutMin.X, Points[I].X);
        OutMin.Y = std::min(OutMin.Y, Points[I].Y);
        OutMax.X = std::max(OutMax.X, Points[I].X);
        OutMax.Y = std::max(OutMax.Y, Points[I].Y);
    }
    return true;
}

/** Shoelace area, always positive. Zone instance counts are apportioned by area * density. */
inline double PolygonArea(const Vec2* Points, int Count)
{
    if (!Points || Count < 3) return 0.0;
    double Twice = 0.0;
    for (int I = 0, J = Count - 1; I < Count; J = I++)
    {
        Twice += Points[J].X * Points[I].Y - Points[I].X * Points[J].Y;
    }
    return std::abs(Twice) * 0.5;
}

// ---------------------------------------------------------------------------
// Flow field
// ---------------------------------------------------------------------------

/** One zone's steering field. Direction is a constant heading (the street or plaza
 * "grain"); the goal pulls figures toward a focus such as a gate mouth or the wall.
 * GoalWeight 0 is a pure directional stream, 1 is a pure convergence on the goal. */
struct FlowZone
{
    Vec2 Goal{};
    double DirectionDegrees = 0.0;
    double GoalWeight = 0.35;
    double SwirlDegrees = 0.0;       // steady lateral bias, degrees added to the blended heading
    double MeanderDegrees = 12.0;    // per-instance heading jitter amplitude, degrees
    double MeanderHz = 0.11;         // how quickly that jitter turns over
};

/** Blended unit heading for an instance at P. Deterministic in (Seed, Index): the same
 * instance meanders the same way every run. Never returns a zero vector for a live zone. */
inline Vec2 SampleFlow(const FlowZone& Zone, const Vec2& P, double TimeSeconds, uint32_t Seed, uint32_t Index)
{
    const Vec2 Streaming = FromDegrees(Zone.DirectionDegrees);
    Vec2 Blended = Streaming;
    const double GoalWeight = Clamp(Zone.GoalWeight, 0.0, 1.0);
    if (GoalWeight > 0.0 && Finite(P))
    {
        const Vec2 ToGoal = Normalized(Zone.Goal - P);
        if (Length(ToGoal) > 0.0)
        {
            Blended = Normalized(Streaming * (1.0 - GoalWeight) + ToGoal * GoalWeight);
        }
    }
    if (Length(Blended) < 1e-9) Blended = Streaming;
    double Heading = YawDegrees(Blended) + Zone.SwirlDegrees;
    if (Zone.MeanderDegrees > 0.0 && std::isfinite(TimeSeconds))
    {
        // A per-instance phase offset makes neighbours drift apart instead of marching in lockstep.
        const double Offset = HashUnit(Seed, Index, 71u) * 2.0 * Pi;
        Heading += Zone.MeanderDegrees * std::sin(2.0 * Pi * Zone.MeanderHz * TimeSeconds + Offset);
    }
    return FromDegrees(WrapDegrees(Heading));
}

/** Turn Current toward Desired by at most MaxTurnDegreesPerSecond * Dt. Keeps a figure
 * from snapping around when the goal direction flips as it passes the goal. */
inline double SteerHeading(double CurrentDegrees, double DesiredDegrees, double Dt, double MaxTurnDegreesPerSecond)
{
    if (!std::isfinite(Dt) || Dt <= 0.0) return WrapDegrees(CurrentDegrees);
    const double Delta = WrapDegrees(DesiredDegrees - CurrentDegrees);
    const double Limit = std::max(0.0, MaxTurnDegreesPerSecond) * Clamp(Dt, 0.0, 0.25);
    return WrapDegrees(CurrentDegrees + Clamp(Delta, -Limit, Limit));
}

// ---------------------------------------------------------------------------
// Speed and gait phase
// ---------------------------------------------------------------------------

constexpr double MinWalkSpeedCmPerSecond = 60.0;
constexpr double MaxWalkSpeedCmPerSecond = 110.0;
constexpr double StrideLengthCm = 78.0;   // one full gait cycle (both feet) at this stride

/** Per-instance walking speed, deterministic in (Seed, Index), in [Min, Max]. */
inline double WalkSpeedFor(uint32_t Seed, uint32_t Index, double MinSpeed = MinWalkSpeedCmPerSecond, double MaxSpeed = MaxWalkSpeedCmPerSecond)
{
    if (!(MaxSpeed > MinSpeed)) return std::max(0.0, MinSpeed);
    return HashRange(Seed, Index, 13u, MinSpeed, MaxSpeed);
}

/** True when this instance stands rather than walks. Ratio is the share of the zone that
 * stands still (praying at the wall, waiting in the court). Deterministic per instance. */
inline bool IsStanding(uint32_t Seed, uint32_t Index, double StandingRatio)
{
    return HashUnit(Seed, Index, 29u) < Clamp(StandingRatio, 0.0, 1.0);
}

/** Advance the 0..1 gait phase. Distance travelled, not wall time, drives it, so a slow
 * figure takes slow steps. A standing figure still breathes at a low idle rate. */
inline double AdvancePhase(double Phase, double SpeedCmPerSecond, double Dt, bool bStanding = false, double StrideCm = StrideLengthCm)
{
    if (!std::isfinite(Phase)) Phase = 0.0;
    if (!std::isfinite(Dt) || Dt <= 0.0) return Phase - std::floor(Phase);
    const double Clamped = Clamp(Dt, 0.0, 0.25);
    const double Stride = StrideCm > 1e-6 ? StrideCm : StrideLengthCm;
    const double Cycles = bStanding ? 0.25 * Clamped : (std::max(0.0, SpeedCmPerSecond) * Clamped) / Stride;
    const double Next = Phase + Cycles;
    return Next - std::floor(Next);
}

/** Vertical bob for a phase, cm. Two rises per gait cycle (one per footfall). Exposed for
 * the tests and for parity with the material, which computes the same curve on the GPU. */
inline double BobHeightCm(double Phase, double AmplitudeCm)
{
    if (!std::isfinite(Phase) || !std::isfinite(AmplitudeCm)) return 0.0;
    return AmplitudeCm * 0.5 * (1.0 - std::cos(4.0 * Pi * Phase));
}

/** Side-to-side lean for a phase, degrees: one sway per gait cycle. */
inline double LeanDegrees(double Phase, double AmplitudeDegrees)
{
    if (!std::isfinite(Phase) || !std::isfinite(AmplitudeDegrees)) return 0.0;
    return AmplitudeDegrees * std::sin(2.0 * Pi * Phase);
}

// ---------------------------------------------------------------------------
// Bounded per-frame work
// ---------------------------------------------------------------------------

/** One contiguous slice of the instance array. A wrapping sweep produces two of them. */
struct UpdateWindow
{
    int FirstStart = 0, FirstCount = 0;
    int SecondStart = 0, SecondCount = 0;
    int NextCursor = 0;
    int Total() const { return FirstCount + SecondCount; }
    bool Wrapped() const { return SecondCount > 0; }
};

/** Round-robin budget: from Cursor, take up to Budget of Count instances, wrapping once.
 * Cost per frame is bounded whatever Count is; every instance is visited exactly once per
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

/** Frames needed for one full sweep of Count instances at Budget per frame. */
inline int FramesPerSweep(int Count, int Budget)
{
    if (Count <= 0 || Budget <= 0) return 0;
    return (Count + Budget - 1) / Budget;
}

/** Seconds of simulated time an instance has missed since its last visit. A round-robin
 * agent must integrate the whole sweep it slept through, not one frame, or the crowd
 * walks at 1/N speed. Clamped so a hitch cannot teleport a figure across the court. */
inline double CatchUpSeconds(double DeltaSeconds, int Count, int Budget, double MaxStepSeconds = 0.5)
{
    if (!std::isfinite(DeltaSeconds) || DeltaSeconds <= 0.0) return 0.0;
    const int Frames = FramesPerSweep(Count, Budget);
    return Clamp(DeltaSeconds * std::max(1, Frames), 0.0, std::max(0.0, MaxStepSeconds));
}

// ---------------------------------------------------------------------------
// Distance policy
// ---------------------------------------------------------------------------

/** What the field should do with one instance this sweep. */
enum class InstanceWork
{
    Simulate,  // near enough that motion reads: integrate and push a new transform
    Freeze,    // visible but far: leave the transform alone, keep paying only the draw
    Cull       // beyond the cull distance: HISM is already not drawing it; skip entirely
};

/** Distance policy. FreezeCm < CullCm is required; if they are given inverted or
 * non-finite the instance is simulated, because a wrong freeze is worse than a slow frame. */
inline InstanceWork ClassifyByDistance(double DistanceCm, double FreezeCm, double CullCm)
{
    if (!std::isfinite(DistanceCm) || !std::isfinite(FreezeCm) || !std::isfinite(CullCm)) return InstanceWork::Simulate;
    if (!(FreezeCm > 0.0) || !(CullCm > FreezeCm)) return InstanceWork::Simulate;
    if (DistanceCm >= CullCm) return InstanceWork::Cull;
    if (DistanceCm >= FreezeCm) return InstanceWork::Freeze;
    return InstanceWork::Simulate;
}

/** Squared planar distance; the caller keeps everything squared to avoid a sqrt per instance. */
inline double DistanceSquared2D(const Vec2& A, const Vec2& B)
{
    const Vec2 D = A - B;
    return Dot(D, D);
}

// ---------------------------------------------------------------------------
// One instance's step
// ---------------------------------------------------------------------------

struct AgentState
{
    Vec2 Position{};
    double HeadingDegrees = 0.0;
    double SpeedCmPerSecond = 0.0;
    double Phase = 0.0;
    bool bStanding = false;
    bool bReseeded = false;   // set by Step when the agent left its zone and was returned
};

/** Advance one agent inside its zone.
 *
 * Steering blends the zone flow with a turn-rate limit; the new position is refused, and
 * the agent re-seeded at ReseedPoint, when it would leave the zone polygon or enter any
 * protected polygon. A standing agent never translates but still keeps a phase, so the
 * material gives it an idle sway.
 *
 * Zone points are Count consecutive Vec2. Protected polygons use the flat
 * (Points, Starts, Counts, PolygonCount) layout of PointInAnyProtected. */
inline void Step(AgentState& Agent,
                 const FlowZone& Zone,
                 const Vec2* ZonePoints, int ZoneCount,
                 const Vec2* ProtectedPoints, const int* ProtectedStarts, const int* ProtectedCounts, int ProtectedPolygons,
                 double ProtectedMarginCm,
                 const Vec2& ReseedPoint,
                 double Dt,
                 double TimeSeconds,
                 uint32_t Seed, uint32_t Index,
                 double MaxTurnDegreesPerSecond = 90.0)
{
    Agent.bReseeded = false;
    if (!std::isfinite(Dt) || Dt <= 0.0 || !Finite(Agent.Position)) return;
    const double Step_ = Clamp(Dt, 0.0, 0.5);
    const Vec2 Desired = SampleFlow(Zone, Agent.Position, TimeSeconds, Seed, Index);
    Agent.HeadingDegrees = SteerHeading(Agent.HeadingDegrees, YawDegrees(Desired), Step_, MaxTurnDegreesPerSecond);
    Agent.Phase = AdvancePhase(Agent.Phase, Agent.SpeedCmPerSecond, Step_, Agent.bStanding);
    if (Agent.bStanding) return;

    const Vec2 Candidate = Agent.Position + FromDegrees(Agent.HeadingDegrees) * (std::max(0.0, Agent.SpeedCmPerSecond) * Step_);
    const bool bLeftZone = !PointInPolygon(ZonePoints, ZoneCount, Candidate);
    const bool bProtected = PointInAnyProtected(ProtectedPoints, ProtectedStarts, ProtectedCounts, ProtectedPolygons, Candidate, ProtectedMarginCm);
    if (bLeftZone || bProtected)
    {
        // Re-seed rather than slide along the boundary: a background figure that reappears
        // at the far side of the zone reads as another pilgrim arriving, and it costs nothing.
        // A re-seed point that is itself outside the zone or inside a protected polygon is
        // refused -- a mis-authored zones.json must never be able to teleport the crowd into
        // the sanctuary. In that case the figure turns around where it stands.
        const bool bReseedUsable = PointInPolygon(ZonePoints, ZoneCount, ReseedPoint)
            && !PointInAnyProtected(ProtectedPoints, ProtectedStarts, ProtectedCounts, ProtectedPolygons, ReseedPoint, ProtectedMarginCm);
        if (bReseedUsable)
        {
            Agent.Position = ReseedPoint;
            Agent.HeadingDegrees = YawDegrees(SampleFlow(Zone, ReseedPoint, TimeSeconds, Seed, Index));
        }
        else
        {
            Agent.HeadingDegrees = WrapDegrees(Agent.HeadingDegrees + 180.0);
        }
        Agent.bReseeded = true;
        return;
    }
    Agent.Position = Candidate;
}

/** Rejection-sample a point inside the zone, clear of every protected polygon.
 * Deterministic in (Seed, Index): the same instance seeds to the same place every run.
 * Returns false after MaxAttempts, which the caller must treat as "this zone is
 * unusable" rather than placing a figure inside the sanctuary. */
inline bool SeedPointInZone(const Vec2* ZonePoints, int ZoneCount,
                            const Vec2* ProtectedPoints, const int* ProtectedStarts, const int* ProtectedCounts, int ProtectedPolygons,
                            double ProtectedMarginCm, double EdgeMarginCm,
                            uint32_t Seed, uint32_t Index, int MaxAttempts,
                            Vec2& OutPoint)
{
    Vec2 Min{}, Max{};
    if (!PolygonBounds(ZonePoints, ZoneCount, Min, Max)) return false;
    for (int Attempt = 0; Attempt < std::max(1, MaxAttempts); ++Attempt)
    {
        const uint32_t Lane = 1000u + static_cast<uint32_t>(Attempt) * 2u;
        const Vec2 P{HashRange(Seed, Index, Lane, Min.X, Max.X), HashRange(Seed, Index, Lane + 1u, Min.Y, Max.Y)};
        if (!PointInPolygonWithMargin(ZonePoints, ZoneCount, P, EdgeMarginCm)) continue;
        if (PointInAnyProtected(ProtectedPoints, ProtectedStarts, ProtectedCounts, ProtectedPolygons, P, ProtectedMarginCm)) continue;
        OutPoint = P;
        return true;
    }
    return false;
}

/** Apportion Total instances across zones by area * density, largest-remainder so the
 * parts sum to exactly Total. Zones with no area or no density get none. Returns the
 * number actually apportioned (Total unless every weight is zero). */
inline int ApportionCounts(const double* Weights, int ZoneCount, int Total, int* OutCounts)
{
    if (!Weights || !OutCounts || ZoneCount <= 0) return 0;
    for (int I = 0; I < ZoneCount; ++I) OutCounts[I] = 0;
    if (Total <= 0) return 0;
    double Sum = 0.0;
    for (int I = 0; I < ZoneCount; ++I)
    {
        if (std::isfinite(Weights[I]) && Weights[I] > 0.0) Sum += Weights[I];
    }
    if (!(Sum > 0.0)) return 0;
    int Assigned = 0;
    for (int I = 0; I < ZoneCount; ++I)
    {
        const double W = (std::isfinite(Weights[I]) && Weights[I] > 0.0) ? Weights[I] : 0.0;
        OutCounts[I] = W > 0.0 ? static_cast<int>(std::floor(Total * W / Sum)) : 0;
        Assigned += OutCounts[I];
    }
    // Largest remainder, each zone taking at most one extra, ties broken by index so the
    // result is reproducible across runs and platforms.
    while (Assigned < Total)
    {
        int Best = -1;
        double BestRemainder = -1.0;
        for (int I = 0; I < ZoneCount; ++I)
        {
            const double W = (std::isfinite(Weights[I]) && Weights[I] > 0.0) ? Weights[I] : 0.0;
            if (W <= 0.0) continue;
            const double Exact = Total * W / Sum;
            if (OutCounts[I] > static_cast<int>(std::floor(Exact))) continue;  // already took its extra
            const double Remainder = Exact - std::floor(Exact);
            if (Remainder > BestRemainder)
            {
                BestRemainder = Remainder;
                Best = I;
            }
        }
        if (Best < 0)
        {
            // Every remainder already spent (all weights identical and exact): top up the
            // first live zone so the parts still sum to Total.
            for (int I = 0; I < ZoneCount && Best < 0; ++I)
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

/** Which pose mesh (and therefore which HISM component) an instance uses. Instances are
 * blocked by pose so a contiguous global window maps to at most two contiguous per-component
 * ranges, which is what makes a batched transform update possible. */
inline int PoseIndexForInstance(int GlobalIndex, int TotalInstances, int PoseCount)
{
    if (PoseCount <= 1 || TotalInstances <= 0 || GlobalIndex < 0) return 0;
    const long long Scaled = static_cast<long long>(GlobalIndex) * PoseCount;
    const int Pose = static_cast<int>(Scaled / TotalInstances);
    return Pose < PoseCount ? Pose : PoseCount - 1;
}

/** First global index that belongs to a pose block, so the actor can map a global index to
 * (component, local index) without a per-instance lookup table. */
inline int PoseBlockStart(int PoseIndex, int TotalInstances, int PoseCount)
{
    if (PoseCount <= 1 || TotalInstances <= 0 || PoseIndex <= 0) return 0;
    if (PoseIndex >= PoseCount) return TotalInstances;
    const long long Scaled = static_cast<long long>(PoseIndex) * TotalInstances;
    return static_cast<int>((Scaled + PoseCount - 1) / PoseCount);
}

/** Garment tint index in [0, PaletteSize) for an instance. Deterministic per instance. */
inline int GarmentIndex(uint32_t Seed, uint32_t Index, int PaletteSize)
{
    if (PaletteSize <= 1) return 0;
    const int Picked = static_cast<int>(HashUnit(Seed, Index, 47u) * PaletteSize);
    return Picked < PaletteSize ? Picked : PaletteSize - 1;
}

/** Uniform scale for an instance: adult height variation only, no children or giants. */
inline double HeightScaleFor(uint32_t Seed, uint32_t Index, double MinScale = 0.92, double MaxScale = 1.08)
{
    if (!(MaxScale > MinScale)) return 1.0;
    return HashRange(Seed, Index, 53u, MinScale, MaxScale);
}

// ---------------------------------------------------------------------------
// Vertex-animated crowd (AMikdashCrowdField::bUseVertexAnimation)
// ---------------------------------------------------------------------------
//
// THE ANCHOR CONTRACT, shared word for word with M_CrowdVAT_V1 (Scripts/create_crowd_vat_v2.py).
// The CPU visits a figure only every few frames. Between visits the MATERIAL draws it at
//     position = Anchor + Velocity * dt,   walk phase = frac(PhaseAtAnchor + Rate * dt),
//     dt = clamp(t - AnchorTime, -NegDt, Horizon)
// and at the next visit the CPU commits exactly the same expression with dt clamped to
// [0, Horizon], then plans a new velocity from there. Position and stride are integrated from one
// anchor with one clamp, so they cannot drift apart. Rate comes from the speed:
//     Rate = Speed / (ClipGroundSpeed * Scale) / CycleSeconds
// which makes ground travel per walk cycle = ClipGroundSpeed * Scale * CycleSeconds, the clip's
// own stride scaled with the figure: the stance foot is world-fixed. That identity is what the
// tests below pin down.

struct VatAnchor
{
    double X = 0, Y = 0, Z = 0;
    double Time = 0;
    double VelX = 0, VelY = 0, VelZ = 0;
    double Phase = 0;      // walk cycles, 0..1
    double Rate = 0;       // walk cycles per second
    double Horizon = 0;    // seconds the material may extrapolate
};

/** Advance an anchor to Now along its current velocity, exactly as the material draws it. */
inline void VatCommit(VatAnchor& A, double Now)
{
    if (!std::isfinite(Now)) return;
    const double H = std::isfinite(A.Horizon) ? std::max(0.0, A.Horizon) : 0.0;
    const double Dt = Clamp(Now - A.Time, 0.0, H);
    A.X += A.VelX * Dt;
    A.Y += A.VelY * Dt;
    A.Z += A.VelZ * Dt;
    const double P = A.Phase + A.Rate * Dt;
    A.Phase = std::isfinite(P) ? P - std::floor(P) : 0.0;
    A.Time = Now;
}

/** The speed a figure may actually walk at: clamped into the play-rate band the clip supports,
 * or 0 when it is too slow to be a walk at all (the figure then idles instead of shuffling). */
inline double VatPlayableSpeed(double Speed, double ClipGroundSpeed, double Scale, double MinRate, double MaxRate)
{
    const double G = ClipGroundSpeed * Scale;
    if (!std::isfinite(Speed) || !std::isfinite(G) || !(G > 0) || Speed <= 0) return 0.0;
    const double Lo = std::max(0.0, MinRate) * G, Hi = std::max(MinRate, MaxRate) * G;
    if (Speed < 0.6 * Lo) return 0.0;
    return Clamp(Speed, Lo, Hi);
}

/** Walk cycles per second for a ground speed: the no-slide rate. */
inline double VatCyclesPerSecond(double Speed, double ClipGroundSpeed, double Scale, double CycleSeconds)
{
    const double G = ClipGroundSpeed * Scale;
    if (!std::isfinite(Speed) || !(G > 0) || !(CycleSeconds > 0) || Speed <= 0) return 0.0;
    return Speed / G / CycleSeconds;
}

/** How long the material may extrapolate a figure: 1.5 sweeps, clamped. Longer than the gap
 * between visits so a figure never stalls; bounded so the look-ahead segment the CPU validated
 * (Speed * Horizon) stays short. */
inline double VatHorizonSeconds(int FramesPerSweepCount, double DeltaSeconds, double MinH, double MaxH)
{
    const double Lo = std::max(0.0, MinH), Hi = std::max(Lo, MaxH);
    if (!std::isfinite(DeltaSeconds) || DeltaSeconds <= 0 || FramesPerSweepCount <= 0) return Lo;
    return Clamp(1.5 * FramesPerSweepCount * DeltaSeconds, Lo, Hi);
}

/** Per-figure cadence bias, 1 +/- Spread, deterministic. Natural pace = ground speed * scale * cadence. */
inline double CadenceFor(uint32_t Seed, uint32_t Index, double Spread)
{
    const double S = std::isfinite(Spread) ? Clamp(Spread, 0.0, 0.5) : 0.0;
    return 1.0 + HashRange(Seed, Index, 61u, -S, S);
}

// Interleaved body assignment for the vertex-animated crowd: global index g lives on component
// g % P at local index g / P, so a party seeded on consecutive indices gets different bodies
// (the blocked layout above gives a whole zone one or two bodies).
inline int InterleavedPose(int GlobalIndex, int PoseCount)
{
    if (PoseCount <= 1 || GlobalIndex < 0) return 0;
    return GlobalIndex % PoseCount;
}
inline int InterleavedLocal(int GlobalIndex, int PoseCount)
{
    if (GlobalIndex < 0) return 0;
    if (PoseCount <= 1) return GlobalIndex;
    return GlobalIndex / PoseCount;
}
/** Instances component Pose holds when Total are interleaved over PoseCount components. */
inline int InterleavedCount(int Pose, int Total, int PoseCount)
{
    if (Total <= 0) return 0;
    if (PoseCount <= 1) return Pose == 0 ? Total : 0;
    if (Pose < 0 || Pose >= PoseCount || Total <= Pose) return 0;
    return (Total - Pose + PoseCount - 1) / PoseCount;
}
/** The contiguous local range of component Pose covered by the global window [Start, Start+Count). */
inline void InterleavedWindow(int Start, int Count, int Pose, int PoseCount, int& OutFirst, int& OutCount)
{
    OutFirst = 0;
    OutCount = 0;
    if (Count <= 0 || Start < 0) return;
    if (PoseCount <= 1)
    {
        if (Pose == 0) { OutFirst = Start; OutCount = Count; }
        return;
    }
    if (Pose < 0 || Pose >= PoseCount) return;
    const int First = Start + ((Pose - Start % PoseCount) + PoseCount) % PoseCount;
    const int End = Start + Count;   // exclusive
    if (First >= End) return;
    OutFirst = First / PoseCount;
    OutCount = (End - 1 - First) / PoseCount + 1;
}
}  // namespace MikdashCrowd
