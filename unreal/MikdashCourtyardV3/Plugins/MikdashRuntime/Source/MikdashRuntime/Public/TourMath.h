#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>

// Engine-independent arithmetic for the guided tour: stop sequencing, arrival detection
// with hysteresis, off-route detection and rejoin, progress, resume, and camera-move
// timing. No Unreal type, no I/O, no allocation, no globals.
//
// Shared by three consumers, which is why this is a header and not a .cpp:
//   * AMikdashTourGuide (Private/MikdashTourGuide.cpp) - run-time state;
//   * Scripts/release_tour.py - places one marker per stop at these same coordinates;
//   * Tests/TourMathTest.cpp - the standalone cl.exe test.
// If those three ever disagree about where a stop is or when the visitor arrived, the
// bug is here and only here.
//
// UNITS AND FRAME. Unreal centimetres throughout, in the level's own frame: +X east,
// +Y SOUTH, +Z up. The level is baked at 50 Unreal cm per amah (see EnclosureMath.h,
// ProjectCmPerAmah); this file never converts, it only measures.
//
// WHY HYSTERESIS IS THE CENTRAL IDEA HERE
// A visitor who stops walking and stands still still moves: the character controller
// settles, the camera bobs, the floor trace jitters by a centimetre or two. A single
// radius test would then flip "arrived / not arrived" several times a second and the
// prompt would strobe. So every boolean this file computes that a visitor can sit on
// the boundary of has TWO thresholds: a tighter one to become true and a looser one to
// become false again. The test asserts that a visitor parked exactly on either boundary
// produces exactly one transition, ever.
//
// WHAT THIS FILE DOES NOT DECIDE
// Nothing halachic. It does not know what a stop means, only where it is. The stop
// text, its sources and its confidence labels live in
// SourceAssets/tour-review/tour-stops.json, as data, so they can be corrected and
// translated without a recompile.
namespace MikdashTour
{
// ---------------------------------------------------------------------------
// 1. Points and small vector helpers
// ---------------------------------------------------------------------------

struct Point3
{
    double X = 0.0;
    double Y = 0.0;
    double Z = 0.0;
};

inline bool Finite(const Point3& P)
{
    return std::isfinite(P.X) && std::isfinite(P.Y) && std::isfinite(P.Z);
}
inline bool Same(const Point3& A, const Point3& B, double Tolerance = 1e-9)
{
    return std::abs(A.X - B.X) <= Tolerance && std::abs(A.Y - B.Y) <= Tolerance
        && std::abs(A.Z - B.Z) <= Tolerance;
}
inline Point3 Add(const Point3& A, const Point3& B) { return {A.X + B.X, A.Y + B.Y, A.Z + B.Z}; }
inline Point3 Sub(const Point3& A, const Point3& B) { return {A.X - B.X, A.Y - B.Y, A.Z - B.Z}; }
inline Point3 Scale(const Point3& A, double S) { return {A.X * S, A.Y * S, A.Z * S}; }
inline Point3 Lerp(const Point3& A, const Point3& B, double T)
{
    return {A.X + (B.X - A.X) * T, A.Y + (B.Y - A.Y) * T, A.Z + (B.Z - A.Z) * T};
}
inline double Distance3D(const Point3& A, const Point3& B)
{
    const double DX = A.X - B.X, DY = A.Y - B.Y, DZ = A.Z - B.Z;
    return std::sqrt(DX * DX + DY * DY + DZ * DZ);
}
/** Horizontal distance. Arrival uses this: a visitor standing on the stop is at the
 * stop even though his eye is 160 cm above the floor the stop was measured on, and the
 * Ulam steps mean two stops six amot apart in height are one step apart on the ground. */
inline double Distance2D(const Point3& A, const Point3& B)
{
    const double DX = A.X - B.X, DY = A.Y - B.Y;
    return std::sqrt(DX * DX + DY * DY);
}

/** Compass bearing from A to B in degrees clockwise from north, 0 <= Bearing < 360.
 * North is -Y because +Y is south. Used for the on-screen arrow when no marker mesh
 * was placed in the level. */
inline double BearingDegrees(const Point3& From, const Point3& To)
{
    const double East = To.X - From.X;
    const double South = To.Y - From.Y;
    if (std::abs(East) < 1e-12 && std::abs(South) < 1e-12) return 0.0;
    double Degrees = std::atan2(East, -South) * 180.0 / 3.14159265358979323846;
    if (Degrees < 0.0) Degrees += 360.0;
    if (Degrees >= 360.0) Degrees -= 360.0;
    return Degrees;
}

/** Closest point on the segment AB to P, in the horizontal plane; Z is interpolated at
 * the same parameter so the returned point sits on the segment in 3D too. */
inline Point3 ClosestPointOnSegment2D(const Point3& A, const Point3& B, const Point3& P)
{
    const double DX = B.X - A.X, DY = B.Y - A.Y;
    const double LengthSquared = DX * DX + DY * DY;
    if (LengthSquared <= 1e-12) return A;
    double T = ((P.X - A.X) * DX + (P.Y - A.Y) * DY) / LengthSquared;
    T = std::max(0.0, std::min(1.0, T));
    return Lerp(A, B, T);
}
inline double DistanceToSegment2D(const Point3& A, const Point3& B, const Point3& P)
{
    return Distance2D(ClosestPointOnSegment2D(A, B, P), P);
}

// ---------------------------------------------------------------------------
// 2. A stop, and the leg that leads to it
// ---------------------------------------------------------------------------

/** Hard caps. Fixed arrays rather than vectors so nothing here allocates and the same
 * numbers can be asserted in Python. 24 stops is one more than the tour needs. */
constexpr std::size_t MaxStops = 24;
/** Approach waypoints carried by a stop: the doorways and gate passages the straight
 * line from the previous stop would otherwise cut through a wall to reach. */
constexpr std::size_t MaxWaypoints = 6;
constexpr std::size_t MaxLegPoints = MaxWaypoints + 2;   // previous stand + waypoints + stand

/** Defaults, in Unreal cm. 400 cm is 8 amot: close enough that the visitor is plainly
 * at the place, wide enough that he does not have to hunt for a pixel. */
constexpr double DefaultArriveRadiusCm = 400.0;
constexpr double DefaultLeaveRadiusCm = 620.0;
/** The gap the two radii must keep. Below this the hysteresis is too thin to survive
 * ordinary controller jitter, and a route that asks for it is refused, not clamped. */
constexpr double MinRadiusGapCm = 60.0;
constexpr double MinArriveRadiusCm = 60.0;

/** Off-route corridor. Wider than the arrival radii because the visitor is meant to be
 * able to drift, look at a wall, and come back without being nagged. */
constexpr double DefaultOffRouteCm = 1400.0;
constexpr double DefaultRejoinCm = 900.0;
constexpr double MinCorridorGapCm = 100.0;

struct Stop
{
    /** Stable identifier, also the localisation key root and the JSON entry key. Never
     * shown to a visitor and never translated. */
    const char* Key = "";
    /** Where the visitor ends up: a standable point on the floor of that place. */
    Point3 Stand;
    /** What he should be looking at from there. */
    Point3 Look;
    /** Doorways to pass through on the way here from the previous stop, in order. */
    std::array<Point3, MaxWaypoints> Waypoints{};
    std::size_t WaypointCount = 0;

    double ArriveRadiusCm = DefaultArriveRadiusCm;
    double LeaveRadiusCm = DefaultLeaveRadiusCm;

    /** Explicit camera-move duration in seconds for "walk me there". 0 means derive it
     * from the distance with CameraTuning below. */
    double CameraSeconds = 0.0;
};

/** A polyline: the previous stop's Stand, the target stop's waypoints, the target
 * stop's Stand. Built on demand; never stored. */
struct Leg
{
    std::array<Point3, MaxLegPoints> Points{};
    std::size_t Count = 0;

    double LengthCm() const
    {
        double Total = 0.0;
        for (std::size_t I = 1; I < Count; ++I) Total += Distance2D(Points[I - 1], Points[I]);
        return Total;
    }
    /** Horizontal distance from P to the polyline, and the closest point on it. */
    double DistanceCm(const Point3& P, Point3* OutClosest = nullptr) const
    {
        if (Count == 0) return 0.0;
        if (Count == 1)
        {
            if (OutClosest) *OutClosest = Points[0];
            return Distance2D(Points[0], P);
        }
        double Best = -1.0;
        Point3 BestPoint = Points[0];
        for (std::size_t I = 1; I < Count; ++I)
        {
            const Point3 Candidate = ClosestPointOnSegment2D(Points[I - 1], Points[I], P);
            const double D = Distance2D(Candidate, P);
            if (Best < 0.0 || D < Best) { Best = D; BestPoint = Candidate; }
        }
        if (OutClosest) *OutClosest = BestPoint;
        return Best;
    }
    /** Point at a fraction of the polyline's length, 0 at the start, 1 at the end. */
    Point3 PointAtFraction(double Fraction) const
    {
        if (Count == 0) return Point3();
        if (Count == 1) return Points[0];
        const double Total = LengthCm();
        if (Total <= 1e-9) return Points[Count - 1];
        double Wanted = std::max(0.0, std::min(1.0, Fraction)) * Total;
        for (std::size_t I = 1; I < Count; ++I)
        {
            const double Segment = Distance2D(Points[I - 1], Points[I]);
            if (Wanted <= Segment || I == Count - 1)
            {
                const double T = Segment <= 1e-9 ? 1.0 : std::max(0.0, std::min(1.0, Wanted / Segment));
                return Lerp(Points[I - 1], Points[I], T);
            }
            Wanted -= Segment;
        }
        return Points[Count - 1];
    }
};

// ---------------------------------------------------------------------------
// 3. The route, and why it can refuse itself
// ---------------------------------------------------------------------------

enum class Refusal
{
    None = 0,
    EmptyRoute,
    TooManyStops,
    TooManyWaypoints,
    EmptyKey,
    DuplicateKey,
    NonFiniteCoordinate,
    ArriveRadiusTooSmall,
    RadiiNotSeparated,
    /** Two consecutive stops so close that arriving at one already arrives at the next;
     * the visitor would be told he had reached two places at once. */
    StopsOverlap,
};

inline const char* RefusalText(Refusal Why)
{
    switch (Why)
    {
    case Refusal::None: return "none";
    case Refusal::EmptyRoute: return "the route has no stops";
    case Refusal::TooManyStops: return "more stops than MaxStops";
    case Refusal::TooManyWaypoints: return "a stop carries more than MaxWaypoints approach points";
    case Refusal::EmptyKey: return "a stop has no key";
    case Refusal::DuplicateKey: return "two stops share a key";
    case Refusal::NonFiniteCoordinate: return "a coordinate is not finite";
    case Refusal::ArriveRadiusTooSmall: return "an arrival radius is below MinArriveRadiusCm";
    case Refusal::RadiiNotSeparated: return "arrival and leave radii are closer than MinRadiusGapCm";
    case Refusal::StopsOverlap: return "two consecutive stops are inside each other's arrival radius";
    }
    return "unknown";
}

class Route
{
public:
    bool Add(const Stop& S)
    {
        if (Count_ >= MaxStops) return false;
        Items_[Count_++] = S;
        return true;
    }
    void Clear() { Count_ = 0; }
    std::size_t Count() const { return Count_; }
    bool Empty() const { return Count_ == 0; }
    const Stop& At(std::size_t Index) const { return Items_[Index < Count_ ? Index : 0]; }

    /** -1 when the key is unknown. Never a silent 0: a typo in the JSON must not send
     * the visitor to the first stop of the tour. */
    int IndexOfKey(const char* Key) const
    {
        if (Key == nullptr) return -1;
        for (std::size_t I = 0; I < Count_; ++I)
        {
            if (Items_[I].Key != nullptr && std::strcmp(Items_[I].Key, Key) == 0) return static_cast<int>(I);
        }
        return -1;
    }

    /** Everything a route has to satisfy before a visitor is ever shown it. */
    Refusal Validate(std::size_t* OutBadStop = nullptr) const
    {
        auto Bad = [&](std::size_t Index, Refusal Why) { if (OutBadStop) *OutBadStop = Index; return Why; };
        if (OutBadStop) *OutBadStop = 0;
        if (Count_ == 0) return Refusal::EmptyRoute;
        if (Count_ > MaxStops) return Refusal::TooManyStops;
        for (std::size_t I = 0; I < Count_; ++I)
        {
            const Stop& S = Items_[I];
            if (S.Key == nullptr || S.Key[0] == '\0') return Bad(I, Refusal::EmptyKey);
            for (std::size_t J = 0; J < I; ++J)
            {
                if (std::strcmp(Items_[J].Key, S.Key) == 0) return Bad(I, Refusal::DuplicateKey);
            }
            if (S.WaypointCount > MaxWaypoints) return Bad(I, Refusal::TooManyWaypoints);
            if (!Finite(S.Stand) || !Finite(S.Look)) return Bad(I, Refusal::NonFiniteCoordinate);
            for (std::size_t W = 0; W < S.WaypointCount; ++W)
            {
                if (!Finite(S.Waypoints[W])) return Bad(I, Refusal::NonFiniteCoordinate);
            }
            if (!std::isfinite(S.ArriveRadiusCm) || !std::isfinite(S.LeaveRadiusCm)) return Bad(I, Refusal::NonFiniteCoordinate);
            if (S.ArriveRadiusCm < MinArriveRadiusCm) return Bad(I, Refusal::ArriveRadiusTooSmall);
            if (S.LeaveRadiusCm - S.ArriveRadiusCm < MinRadiusGapCm) return Bad(I, Refusal::RadiiNotSeparated);
        }
        for (std::size_t I = 1; I < Count_; ++I)
        {
            const double Gap = Distance2D(Items_[I - 1].Stand, Items_[I].Stand);
            if (Gap <= std::max(Items_[I - 1].ArriveRadiusCm, Items_[I].ArriveRadiusCm)) return Bad(I, Refusal::StopsOverlap);
        }
        return Refusal::None;
    }
    bool IsValid() const { return Validate() == Refusal::None; }

    /** The polyline from stop Index-1 to stop Index. For Index 0 the leg is the single
     * point of stop 0: before the tour starts there is nowhere to be off-route from. */
    Leg LegTo(std::size_t Index) const
    {
        Leg Out;
        if (Count_ == 0) return Out;
        const std::size_t Target = std::min(Index, Count_ - 1);
        if (Target == 0)
        {
            Out.Points[Out.Count++] = Items_[0].Stand;
            return Out;
        }
        Out.Points[Out.Count++] = Items_[Target - 1].Stand;
        const Stop& S = Items_[Target];
        for (std::size_t W = 0; W < S.WaypointCount && Out.Count < MaxLegPoints - 1; ++W)
        {
            Out.Points[Out.Count++] = S.Waypoints[W];
        }
        Out.Points[Out.Count++] = S.Stand;
        return Out;
    }

    /** Walking length of the whole route, following every approach waypoint. */
    double TotalLengthCm() const
    {
        double Total = 0.0;
        for (std::size_t I = 1; I < Count_; ++I) Total += LegTo(I).LengthCm();
        return Total;
    }
    /** Walking distance from the start of the route to stop Index. */
    double DistanceToStopCm(std::size_t Index) const
    {
        double Total = 0.0;
        const std::size_t Target = Count_ == 0 ? 0 : std::min(Index, Count_ - 1);
        for (std::size_t I = 1; I <= Target; ++I) Total += LegTo(I).LengthCm();
        return Total;
    }

    /** Nearest stop to P within Radius, or -1. This is how a visitor who wandered off
     * and found the menorah by himself is offered the menorah's stop rather than being
     * marched back to the gate he skipped. */
    int NearestStopWithin(const Point3& P, double RadiusCm) const
    {
        int Best = -1;
        double BestDistance = 0.0;
        for (std::size_t I = 0; I < Count_; ++I)
        {
            const double D = Distance2D(Items_[I].Stand, P);
            if (D > RadiusCm) continue;
            if (Best < 0 || D < BestDistance) { Best = static_cast<int>(I); BestDistance = D; }
        }
        return Best;
    }

private:
    std::array<Stop, MaxStops> Items_{};
    std::size_t Count_ = 0;
};

// ---------------------------------------------------------------------------
// 4. Camera-move timing for "walk me there"
// ---------------------------------------------------------------------------

/** Pacing for the camera move. Every number here is a comfort choice, not a measurement:
 * 450 cm/s is 9 amot a second, about a brisk walk at this world scale, and the ceiling
 * keeps the longest leg on the Mount from becoming a minute of staring at paving. */
struct CameraTuning
{
    double SpeedCmPerSec = 450.0;
    double MinSeconds = 1.5;
    double MaxSeconds = 14.0;
};

inline double MoveDurationSeconds(double DistanceCm, const CameraTuning& Tuning)
{
    if (!std::isfinite(DistanceCm) || DistanceCm <= 0.0) return Tuning.MinSeconds;
    const double Speed = Tuning.SpeedCmPerSec > 1e-6 ? Tuning.SpeedCmPerSec : 1e-6;
    const double Raw = DistanceCm / Speed;
    return std::max(Tuning.MinSeconds, std::min(Tuning.MaxSeconds, Raw));
}

/** Smoothstep. Exactly 0 at 0 and exactly 1 at 1, so a move always starts and ends
 * still and always ends exactly on the stop rather than a centimetre short. */
inline double EaseInOut(double Alpha)
{
    const double T = std::max(0.0, std::min(1.0, std::isfinite(Alpha) ? Alpha : 0.0));
    return T * T * (3.0 - 2.0 * T);
}

// ---------------------------------------------------------------------------
// 5. Modes, phases and the resume bookmark
// ---------------------------------------------------------------------------

enum class Mode : std::uint8_t
{
    /** The camera is moved for the visitor. */
    WalkMeThere = 0,
    /** A marker is shown and the visitor walks there himself. */
    FollowTheMarker = 1,
};

enum class Phase : std::uint8_t
{
    NotStarted = 0,
    /** On the way to the current stop: marker up, or camera flying. */
    Travelling,
    /** Inside the current stop's arrival radius; the panel is showing its text. */
    AtStop,
    /** Explicitly paused. No camera time passes and no arrival is latched. */
    Paused,
    /** Every stop visited and the last one acknowledged. */
    Finished,
};

/**
 * Everything needed to put the tour back exactly where it was, including mid-camera-move.
 * Small, trivially copyable, and compared field for field by operator== so the test can
 * assert "exact resume" rather than "close enough".
 */
struct Bookmark
{
    std::uint64_t VisitedMask = 0;
    std::size_t TargetIndex = 0;
    Phase CurrentPhase = Phase::NotStarted;
    Mode TourMode = Mode::FollowTheMarker;
    bool Present = false;          // inside the arrival radius right now (hysteretic)
    bool OffRoute = false;         // outside the corridor right now (hysteretic)
    bool CameraMoving = false;
    double CameraElapsedSeconds = 0.0;
    double CameraDurationSeconds = 0.0;
    Point3 CameraFrom;
    Point3 CameraTo;
    /** Counters, carried so a restored tour reports the same history it had. */
    std::uint32_t ArrivalTransitions = 0;
    std::uint32_t OffRouteTransitions = 0;
};

inline bool operator==(const Bookmark& A, const Bookmark& B)
{
    return A.VisitedMask == B.VisitedMask && A.TargetIndex == B.TargetIndex
        && A.CurrentPhase == B.CurrentPhase && A.TourMode == B.TourMode
        && A.Present == B.Present && A.OffRoute == B.OffRoute && A.CameraMoving == B.CameraMoving
        && A.CameraElapsedSeconds == B.CameraElapsedSeconds
        && A.CameraDurationSeconds == B.CameraDurationSeconds
        && Same(A.CameraFrom, B.CameraFrom, 0.0) && Same(A.CameraTo, B.CameraTo, 0.0)
        && A.ArrivalTransitions == B.ArrivalTransitions && A.OffRouteTransitions == B.OffRouteTransitions;
}
inline bool operator!=(const Bookmark& A, const Bookmark& B) { return !(A == B); }

/** Progress, in the two forms a visitor asks for. */
struct Progress
{
    std::size_t Visited = 0;
    std::size_t Total = 0;
    /** Visited / Total. The honest one: it counts places actually reached. */
    double FractionByStops = 0.0;
    /** Walking distance covered / total route length. Moves smoothly, so it is the one
     * the bar is drawn from. */
    double FractionByDistance = 0.0;
};

// ---------------------------------------------------------------------------
// 6. The guide
// ---------------------------------------------------------------------------

/**
 * The tour's state machine. The route is supplied by the caller and outlives the guide.
 *
 * Contract:
 *   * Observe() is called once a frame with the visitor's world position and the frame
 *     time. It is the ONLY thing that latches an arrival or an off-route change.
 *   * Arrival is hysteretic in space: Present becomes true at ArriveRadius and false
 *     only past LeaveRadius. Off-route is hysteretic the same way.
 *   * Visiting is permanent. Present can drop; the visited bit never clears. That is
 *     what the codex unlock reads.
 *   * Advancing is explicit (Next / Previous / GoToStop). Nothing auto-advances, so a
 *     visitor can stand at the altar for ten minutes and the tour waits.
 *   * While Paused, Observe still tracks position but latches nothing and no camera
 *     time passes; Resume() puts it back exactly.
 */
class Guide
{
public:
    void SetRoute(const Route* Source)
    {
        Route_ = Source;
        Mark_ = Bookmark();
    }
    const Route* GetRoute() const { return Route_; }

    void SetCorridor(double OffRouteCm, double RejoinCm)
    {
        // Refuse a corridor that cannot hold: keep the previous one rather than accept a
        // pair that would strobe.
        if (!std::isfinite(OffRouteCm) || !std::isfinite(RejoinCm)) return;
        if (OffRouteCm - RejoinCm < MinCorridorGapCm) return;
        if (RejoinCm <= 0.0) return;
        OffRouteCm_ = OffRouteCm;
        RejoinCm_ = RejoinCm;
    }
    double OffRouteRadiusCm() const { return OffRouteCm_; }
    double RejoinRadiusCm() const { return RejoinCm_; }
    void SetCameraTuning(const CameraTuning& Tuning) { Tuning_ = Tuning; }
    const CameraTuning& GetCameraTuning() const { return Tuning_; }

    // -- lifecycle ---------------------------------------------------------

    /** Start at stop 0. CameraOrigin is where the visitor is standing now: a
     * "walk me there" flight begins from there, not from a stop he never stood on.
     * Returns false when the route is missing or refuses itself. */
    bool Begin(Mode TourMode, const Point3& CameraOrigin)
    {
        if (Route_ == nullptr || !Route_->IsValid()) return false;
        Mark_ = Bookmark();
        Mark_.TourMode = TourMode;
        Mark_.TargetIndex = 0;
        Mark_.CurrentPhase = Phase::Travelling;
        LastPosition_ = CameraOrigin;
        if (TourMode == Mode::WalkMeThere) StartCameraMoveToTarget(CameraOrigin);
        return true;
    }

    /** The visitor closed the panel. Everything visited stays visited; Resume() returns
     * to exactly this stop, not to the beginning. */
    void Pause()
    {
        if (Mark_.CurrentPhase == Phase::NotStarted || Mark_.CurrentPhase == Phase::Finished) return;
        if (Mark_.CurrentPhase == Phase::Paused) return;
        PhaseBeforePause_ = Mark_.CurrentPhase;
        Mark_.CurrentPhase = Phase::Paused;
    }
    void Resume()
    {
        if (Mark_.CurrentPhase != Phase::Paused) return;
        Mark_.CurrentPhase = PhaseBeforePause_;
    }
    /** Leave the tour entirely. The bookmark survives, so Restore() puts the visitor
     * back at the stop he left from. Deliberately NOT called Stop(): a member function
     * of that name would hide the Stop type inside this class. */
    void EndTour() { Mark_.CurrentPhase = Phase::NotStarted; Mark_.CameraMoving = false; }

    bool IsRunning() const
    {
        return Mark_.CurrentPhase == Phase::Travelling || Mark_.CurrentPhase == Phase::AtStop
            || Mark_.CurrentPhase == Phase::Paused;
    }
    bool IsPaused() const { return Mark_.CurrentPhase == Phase::Paused; }
    Phase GetPhase() const { return Mark_.CurrentPhase; }
    Mode GetMode() const { return Mark_.TourMode; }

    /** Switching mode mid-tour keeps the stop. Turning "walk me there" on starts the
     * camera move to the stop the visitor was already heading for. */
    void SetMode(Mode TourMode, const Point3& CameraOrigin)
    {
        if (Mark_.TourMode == TourMode) return;
        Mark_.TourMode = TourMode;
        if (TourMode == Mode::WalkMeThere && Mark_.CurrentPhase == Phase::Travelling)
        {
            StartCameraMoveToTarget(CameraOrigin);
        }
        else if (TourMode == Mode::FollowTheMarker)
        {
            Mark_.CameraMoving = false;
        }
    }

    // -- sequencing --------------------------------------------------------

    std::size_t TargetIndex() const { return Mark_.TargetIndex; }
    std::size_t StopCount() const { return Route_ ? Route_->Count() : 0; }
    const Stop* TargetStop() const
    {
        if (Route_ == nullptr || Route_->Count() == 0) return nullptr;
        return &Route_->At(Mark_.TargetIndex);
    }

    /** Move to the next stop. Skippable: this works whether or not the current stop was
     * reached, which is exactly what "skip this one" means. At the last stop it finishes
     * the tour only if that stop was actually visited; otherwise it stays put and returns
     * false, so a stray key press cannot end the tour from a place the visitor never saw. */
    bool Next(const Point3& CameraOrigin)
    {
        if (Route_ == nullptr || !IsRunning()) return false;
        if (Mark_.TargetIndex + 1 < Route_->Count()) return GoToStop(Mark_.TargetIndex + 1, CameraOrigin);
        if (!IsVisited(Mark_.TargetIndex)) return false;
        Mark_.CurrentPhase = Phase::Finished;
        Mark_.CameraMoving = false;
        return true;
    }
    bool Previous(const Point3& CameraOrigin)
    {
        if (Route_ == nullptr || !IsRunning() || Mark_.TargetIndex == 0) return false;
        return GoToStop(Mark_.TargetIndex - 1, CameraOrigin);
    }
    /** Jump anywhere. Used by the stop list, and by the "you are near the menorah, go
     * there instead?" offer when the visitor wandered. */
    bool GoToStop(std::size_t Index, const Point3& CameraOrigin)
    {
        if (Route_ == nullptr || Route_->Count() == 0) return false;
        if (Index >= Route_->Count()) return false;
        Mark_.TargetIndex = Index;
        Mark_.Present = false;
        Mark_.OffRoute = false;
        Mark_.CameraMoving = false;
        if (Mark_.CurrentPhase == Phase::NotStarted || Mark_.CurrentPhase == Phase::Finished)
        {
            Mark_.CurrentPhase = Phase::Travelling;
        }
        else if (Mark_.CurrentPhase != Phase::Paused)
        {
            Mark_.CurrentPhase = Phase::Travelling;
        }
        if (Mark_.TourMode == Mode::WalkMeThere && Mark_.CurrentPhase == Phase::Travelling)
        {
            StartCameraMoveToTarget(CameraOrigin);
        }
        return true;
    }

    // -- the once-a-frame call --------------------------------------------

    /**
     * Update presence, arrival and corridor from the visitor's position, and advance any
     * camera move. Returns true on the frame an arrival is first latched for this stop.
     */
    bool Observe(const Point3& VisitorPosition, double DeltaSeconds)
    {
        if (Route_ == nullptr || Route_->Count() == 0) return false;
        if (!Finite(VisitorPosition)) return false;
        LastPosition_ = VisitorPosition;
        if (!IsRunning() || Mark_.CurrentPhase == Phase::Paused) return false;

        // Camera move first: while it runs, the visitor position the caller hands us IS
        // the camera position, so arrival falls out of the move finishing.
        if (Mark_.CameraMoving && std::isfinite(DeltaSeconds) && DeltaSeconds > 0.0)
        {
            Mark_.CameraElapsedSeconds = std::min(Mark_.CameraDurationSeconds,
                                                  Mark_.CameraElapsedSeconds + DeltaSeconds);
            if (Mark_.CameraElapsedSeconds >= Mark_.CameraDurationSeconds) Mark_.CameraMoving = false;
        }

        const Stop& Target = Route_->At(Mark_.TargetIndex);
        const double ToStop = Distance2D(Target.Stand, VisitorPosition);

        bool JustArrived = false;
        if (!Mark_.Present)
        {
            if (ToStop <= Target.ArriveRadiusCm)
            {
                Mark_.Present = true;
                ++Mark_.ArrivalTransitions;
                Mark_.CurrentPhase = Phase::AtStop;
                JustArrived = !IsVisited(Mark_.TargetIndex);
                Mark_.VisitedMask |= Bit(Mark_.TargetIndex);
                // You cannot be off-route while standing on the stop.
                if (Mark_.OffRoute) { Mark_.OffRoute = false; ++Mark_.OffRouteTransitions; }
            }
        }
        else if (ToStop > Target.LeaveRadiusCm)
        {
            Mark_.Present = false;
            ++Mark_.ArrivalTransitions;
            Mark_.CurrentPhase = Phase::Travelling;
        }

        // Corridor. Suppressed while present, and while a camera move is flying the
        // visitor along a path of its own.
        if (!Mark_.Present && !Mark_.CameraMoving)
        {
            const Leg Path = Route_->LegTo(Mark_.TargetIndex);
            const double Corridor = Path.DistanceCm(VisitorPosition);
            if (!Mark_.OffRoute && Corridor > OffRouteCm_)
            {
                Mark_.OffRoute = true;
                ++Mark_.OffRouteTransitions;
            }
            else if (Mark_.OffRoute && Corridor <= RejoinCm_)
            {
                Mark_.OffRoute = false;
                ++Mark_.OffRouteTransitions;
            }
        }
        return JustArrived;
    }

    // -- what the panel reads ---------------------------------------------

    bool IsAtStop() const { return Mark_.Present; }
    bool IsOffRoute() const { return Mark_.OffRoute; }
    std::uint32_t ArrivalTransitionCount() const { return Mark_.ArrivalTransitions; }
    std::uint32_t OffRouteTransitionCount() const { return Mark_.OffRouteTransitions; }

    bool IsVisited(std::size_t Index) const
    {
        return Index < MaxStops && (Mark_.VisitedMask & Bit(Index)) != 0;
    }
    std::size_t VisitedCount() const
    {
        std::size_t Total = 0;
        const std::size_t Limit = Route_ ? Route_->Count() : 0;
        for (std::size_t I = 0; I < Limit; ++I) { if (IsVisited(I)) ++Total; }
        return Total;
    }
    std::uint64_t VisitedMask() const { return Mark_.VisitedMask; }

    /** Distance from the visitor's last observed position to the current stop, and the
     * compass bearing to it, for the on-screen arrow. */
    double DistanceToTargetCm() const
    {
        const Stop* Target = TargetStop();
        return Target ? Distance2D(Target->Stand, LastPosition_) : 0.0;
    }
    double BearingToTargetDegrees() const
    {
        const Stop* Target = TargetStop();
        return Target ? BearingDegrees(LastPosition_, Target->Stand) : 0.0;
    }
    /** Where the marker should stand: the next unpassed approach waypoint if the visitor
     * has not reached it yet, otherwise the stop itself. This is what makes "follow the
     * marker" lead a visitor through a gate instead of into the wall beside it. */
    Point3 MarkerPosition() const
    {
        const Stop* Target = TargetStop();
        if (Target == nullptr) return Point3();
        const Leg Path = Route_->LegTo(Mark_.TargetIndex);
        if (Path.Count <= 2) return Target->Stand;
        // Find the closest polyline point to the visitor, then aim at the next one.
        std::size_t NearestIndex = 0;
        double Best = -1.0;
        for (std::size_t I = 0; I < Path.Count; ++I)
        {
            const double D = Distance2D(Path.Points[I], LastPosition_);
            if (Best < 0.0 || D < Best) { Best = D; NearestIndex = I; }
        }
        const std::size_t Ahead = std::min(NearestIndex + 1, Path.Count - 1);
        return Path.Points[Ahead];
    }
    /** Closest point on the current leg: where "return to the route" sends him. */
    Point3 RejoinPoint() const
    {
        if (Route_ == nullptr || Route_->Count() == 0) return LastPosition_;
        Point3 Closest;
        Route_->LegTo(Mark_.TargetIndex).DistanceCm(LastPosition_, &Closest);
        return Closest;
    }
    double CorridorDistanceCm() const
    {
        if (Route_ == nullptr || Route_->Count() == 0) return 0.0;
        return Route_->LegTo(Mark_.TargetIndex).DistanceCm(LastPosition_);
    }

    Progress GetProgress() const
    {
        Progress Out;
        if (Route_ == nullptr) return Out;
        Out.Total = Route_->Count();
        Out.Visited = VisitedCount();
        Out.FractionByStops = Out.Total == 0 ? 0.0 : static_cast<double>(Out.Visited) / static_cast<double>(Out.Total);
        const double Length = Route_->TotalLengthCm();
        if (Length > 1e-9)
        {
            // Distance covered = distance to the last visited stop, plus how far along
            // the current leg the visitor has come.
            std::size_t LastVisited = 0;
            bool AnyVisited = false;
            for (std::size_t I = 0; I < Out.Total; ++I) { if (IsVisited(I)) { LastVisited = I; AnyVisited = true; } }
            double Covered = AnyVisited ? Route_->DistanceToStopCm(LastVisited) : 0.0;
            if (Mark_.TargetIndex > LastVisited || !AnyVisited)
            {
                const Leg Path = Route_->LegTo(Mark_.TargetIndex);
                const double LegLength = Path.LengthCm();
                if (LegLength > 1e-9)
                {
                    Point3 Closest;
                    Path.DistanceCm(LastPosition_, &Closest);
                    Covered += std::max(0.0, std::min(LegLength, ArcLengthTo(Path, Closest)));
                }
            }
            Out.FractionByDistance = std::max(0.0, std::min(1.0, Covered / Length));
        }
        return Out;
    }

    // -- camera move -------------------------------------------------------

    bool IsCameraMoving() const { return Mark_.CameraMoving; }
    double CameraAlpha() const
    {
        if (Mark_.CameraDurationSeconds <= 1e-9) return 1.0;
        return std::max(0.0, std::min(1.0, Mark_.CameraElapsedSeconds / Mark_.CameraDurationSeconds));
    }
    double CameraRemainingSeconds() const
    {
        return std::max(0.0, Mark_.CameraDurationSeconds - Mark_.CameraElapsedSeconds);
    }
    /** Where the camera is now. Follows the leg polyline, so a "walk me there" through
     * the east gate goes through the gate rather than through the wall. */
    Point3 CameraPosition() const
    {
        if (Route_ == nullptr || Route_->Count() == 0) return Mark_.CameraFrom;
        const double Eased = EaseInOut(CameraAlpha());
        Leg Path = Route_->LegTo(Mark_.TargetIndex);
        // Fly from wherever the visitor actually was, not from the previous stop he may
        // never have stood on: replace the first polyline point with the move's origin.
        if (Path.Count > 0) Path.Points[0] = Mark_.CameraFrom;
        if (Path.Count <= 1) return Lerp(Mark_.CameraFrom, Mark_.CameraTo, Eased);
        return Path.PointAtFraction(Eased);
    }

    // -- save and restore --------------------------------------------------

    Bookmark Save() const { return Mark_; }

    /**
     * Put the tour back exactly. Refuses a bookmark that does not fit this route rather
     * than clamping it, because a silently clamped resume drops the visitor somewhere he
     * has never been and looks like a bug in the building.
     */
    bool Restore(const Bookmark& Saved)
    {
        if (Route_ == nullptr || Route_->Count() == 0) return false;
        if (Saved.TargetIndex >= Route_->Count()) return false;
        const std::uint64_t Allowed = Route_->Count() >= 64
            ? ~static_cast<std::uint64_t>(0)
            : ((static_cast<std::uint64_t>(1) << Route_->Count()) - 1);
        if ((Saved.VisitedMask & ~Allowed) != 0) return false;
        if (!std::isfinite(Saved.CameraElapsedSeconds) || !std::isfinite(Saved.CameraDurationSeconds)) return false;
        if (Saved.CameraElapsedSeconds < 0.0 || Saved.CameraDurationSeconds < 0.0) return false;
        if (Saved.CameraElapsedSeconds > Saved.CameraDurationSeconds + 1e-9) return false;
        if (!Finite(Saved.CameraFrom) || !Finite(Saved.CameraTo)) return false;
        Mark_ = Saved;
        PhaseBeforePause_ = Saved.CurrentPhase == Phase::Paused ? Phase::Travelling : Saved.CurrentPhase;
        return true;
    }

    /** The position last handed to Observe. Exposed so the panel and the test agree. */
    const Point3& LastObservedPosition() const { return LastPosition_; }

private:
    static std::uint64_t Bit(std::size_t Index)
    {
        return Index < 64 ? (static_cast<std::uint64_t>(1) << Index) : 0;
    }

    void StartCameraMoveToTarget(const Point3& From)
    {
        const Stop* Target = TargetStop();
        if (Target == nullptr) return;
        Leg Path = Route_->LegTo(Mark_.TargetIndex);
        if (Path.Count > 0) Path.Points[0] = From;
        const double Length = Path.Count > 1 ? Path.LengthCm() : Distance2D(From, Target->Stand);
        Mark_.CameraFrom = From;
        Mark_.CameraTo = Target->Stand;
        Mark_.CameraDurationSeconds = Target->CameraSeconds > 0.0
            ? Target->CameraSeconds
            : MoveDurationSeconds(Length, Tuning_);
        Mark_.CameraElapsedSeconds = 0.0;
        Mark_.CameraMoving = true;
    }

    /** Distance along the polyline from its start to a point already known to lie on it. */
    static double ArcLengthTo(const Leg& Path, const Point3& OnPath)
    {
        double Total = 0.0;
        for (std::size_t I = 1; I < Path.Count; ++I)
        {
            const double Segment = Distance2D(Path.Points[I - 1], Path.Points[I]);
            const double ToStart = Distance2D(Path.Points[I - 1], OnPath);
            const double ToEnd = Distance2D(Path.Points[I], OnPath);
            if (std::abs(ToStart + ToEnd - Segment) <= 1e-6) return Total + ToStart;
            Total += Segment;
        }
        return Total;
    }

    const Route* Route_ = nullptr;
    Bookmark Mark_;
    Phase PhaseBeforePause_ = Phase::Travelling;
    Point3 LastPosition_;
    CameraTuning Tuning_;
    double OffRouteCm_ = DefaultOffRouteCm;
    double RejoinCm_ = DefaultRejoinCm;
};

// ---------------------------------------------------------------------------
// 7. The codex side: confidence labels
// ---------------------------------------------------------------------------

/**
 * The three labels every codex entry must carry. This project's integrity rests on the
 * distinction, so the label is an enum in code and a required string in the JSON, not a
 * free-text field that can quietly go missing.
 *
 *   Certain  - the sources agree, or one source is decisive and no cited authority
 *              disputes it. Measurements from the navi and the Mishnah live here.
 *   Disputed - the sources disagree, and the entry NAMES who holds what.
 *   Authored - nobody said this. It is the project's own choice, made because a model
 *              has to put something somewhere. Saying so is the point.
 */
enum class Confidence : std::uint8_t
{
    Certain = 0,
    Disputed = 1,
    Authored = 2,
};

inline const char* ConfidenceKey(Confidence Value)
{
    switch (Value)
    {
    case Confidence::Certain: return "certain";
    case Confidence::Disputed: return "disputed";
    case Confidence::Authored: return "authored";
    }
    return "authored";   // the safe default: never claim more than you can show
}

/** Parse the JSON label. Returns false for anything unrecognised, so a typo becomes a
 * loud load failure rather than a silent promotion to "certain". */
inline bool ParseConfidence(const char* Text, Confidence& Out)
{
    if (Text == nullptr) return false;
    if (std::strcmp(Text, "certain") == 0) { Out = Confidence::Certain; return true; }
    if (std::strcmp(Text, "disputed") == 0) { Out = Confidence::Disputed; return true; }
    if (std::strcmp(Text, "authored") == 0) { Out = Confidence::Authored; return true; }
    return false;
}
} // namespace MikdashTour
