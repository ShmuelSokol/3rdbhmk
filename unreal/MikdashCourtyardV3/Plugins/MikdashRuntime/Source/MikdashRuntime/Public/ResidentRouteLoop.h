#pragma once
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <string>
#include <vector>

// Engine-independent authored-loop route helpers for ONE extended outer-court resident.
// Centimeters, seconds, degrees. Shared by AMikdashResidentPopulation, the character
// adapter and the standalone tests. This is scripted waypoint behavior with pauses and a
// sidestep retry; it is not a mind, a navmesh, or an access authority. The adapter's
// floor/capsule review remains the only physical evidence.
namespace MikdashRoute
{
struct Point2
{
    double X = 0, Y = 0;
};
inline double Distance(const Point2& A, const Point2& B) { return std::hypot(A.X - B.X, A.Y - B.Y); }
inline bool Finite(const Point2& P) { return std::isfinite(P.X) && std::isfinite(P.Y); }

// Authored region for the extended loop: outer court floor Z 300, east of the inner court,
// inside the outer wall margin, and clear of the y=0 east-gate corridor (|y| >= 900).
constexpr double MinX = 1500.0, MaxX = 7000.0, MaxAbsY = 6000.0, MinAbsY = 900.0;
constexpr double FloorZ = 300.0, FloorToleranceCm = 12.0;
constexpr std::size_t MinPoints = 4, MaxPoints = 6;
constexpr double MinLoopCm = 6000.0, MaxLoopCm = 12000.0;
constexpr double MinPauseSeconds = 3.0, MaxPauseSeconds = 5.0;
constexpr double CorridorMarginCm = 150.0;
constexpr double BlockedSeconds = 2.0;
constexpr double BlockedSpeedCmPerSecond = 15.0;
constexpr double SidestepCm = 100.0;
constexpr double TurnRateDegreesPerSecond = 120.0;

inline bool PointInRegion(const Point2& P)
{
    return Finite(P) && P.X >= MinX && P.X <= MaxX && std::abs(P.Y) >= MinAbsY && std::abs(P.Y) < MaxAbsY;
}

inline double LoopLengthCm(const std::vector<Point2>& Points)
{
    double Total = 0;
    for (std::size_t I = 0; I < Points.size(); ++I)
        Total += Distance(Points[I], Points[(I + 1) % Points.size()]);
    return Total;
}

// The shape rules alone: a closed loop of 4..6 authored points, 60..120 m around, with a
// 3..5 s pause and a readable single-line label at each point, and no two consecutive points
// closer than 2 m. The CALLER is responsible for having already checked that every point
// lies in whatever region it authored, which is why the extended-route pilot uses
// ValidateLoop below and the people directory checks its own zone first.
inline bool ValidateLoopGeometry(const std::vector<Point2>& Points, const std::vector<double>& PauseSeconds,
    const std::vector<std::string>& Labels, std::string* Reason = nullptr)
{
    auto Fail = [Reason](const char* Why) { if (Reason) *Reason = Why; return false; };
    if (Points.size() < MinPoints || Points.size() > MaxPoints) return Fail("loop needs 4 to 6 waypoints");
    if (PauseSeconds.size() != Points.size() || Labels.size() != Points.size()) return Fail("pauses/labels must match waypoints");
    for (std::size_t I = 0; I < Points.size(); ++I)
    {
        if (!Finite(Points[I])) return Fail("waypoint is not finite");
        if (!std::isfinite(PauseSeconds[I]) || PauseSeconds[I] < MinPauseSeconds || PauseSeconds[I] > MaxPauseSeconds) return Fail("pause must be 3 to 5 seconds");
        if (Labels[I].empty() || Labels[I].size() > 120 || Labels[I].find_first_of("\r\n") != std::string::npos) return Fail("label must be one short line");
        if (Distance(Points[I], Points[(I + 1) % Points.size()]) < 200.0) return Fail("consecutive waypoints too close");
    }
    const double Length = LoopLengthCm(Points);
    if (Length < MinLoopCm || Length > MaxLoopCm) return Fail("loop length must be 60 to 120 m");
    if (Reason) Reason->clear();
    return true;
}

// The same shape rules with every point additionally inside the authored outer-court region.
inline bool ValidateLoop(const std::vector<Point2>& Points, const std::vector<double>& PauseSeconds,
    const std::vector<std::string>& Labels, std::string* Reason = nullptr)
{
    for (std::size_t I = 0; I < Points.size(); ++I)
        if (!PointInRegion(Points[I]))
        {
            if (Reason) *Reason = "waypoint outside authored outer-court region";
            return false;
        }
    return ValidateLoopGeometry(Points, PauseSeconds, Labels, Reason);
}

inline double DistanceToSegment(const Point2& P, const Point2& A, const Point2& B)
{
    const double DX = B.X - A.X, DY = B.Y - A.Y, L2 = DX * DX + DY * DY;
    double T = L2 > 1e-12 ? ((P.X - A.X) * DX + (P.Y - A.Y) * DY) / L2 : 0.0;
    T = std::max(0.0, std::min(1.0, T));
    return Distance(P, Point2{A.X + DX * T, A.Y + DY * T});
}
inline double DistanceToLoop(const Point2& P, const std::vector<Point2>& Points)
{
    double Best = std::numeric_limits<double>::infinity();
    for (std::size_t I = 0; I < Points.size(); ++I)
        Best = std::min(Best, DistanceToSegment(P, Points[I], Points[(I + 1) % Points.size()]));
    return Best;
}
// Every 25 cm sample of segment A-B stays within the corridor margin of the authored loop.
inline bool SegmentWithinCorridor(const Point2& A, const Point2& B, const std::vector<Point2>& Points,
    double MarginCm = CorridorMarginCm, double StepCm = 25.0)
{
    if (!Finite(A) || !Finite(B) || Points.size() < 2 || !(MarginCm > 0) || !(StepCm > 0)) return false;
    const int Samples = std::max(1, static_cast<int>(std::ceil(Distance(A, B) / StepCm)));
    for (int Step = 0; Step <= Samples; ++Step)
    {
        const double T = static_cast<double>(Step) / Samples;
        if (DistanceToLoop(Point2{A.X + (B.X - A.X) * T, A.Y + (B.Y - A.Y) * T}, Points) > MarginCm) return false;
    }
    return true;
}

// Goal j of a looping plan walks from point j%N to point (j+1)%N.
struct Leg
{
    std::size_t From = 0, To = 0;
};
inline Leg LegForGoal(std::size_t GoalIndex, std::size_t PointCount)
{
    Leg Result;
    if (PointCount == 0) return Result;
    Result.From = GoalIndex % PointCount; Result.To = (GoalIndex + 1) % PointCount;
    return Result;
}

/** Detects a body that has been held still against an active target for two seconds and
 * proposes an alternating 100 cm sidestep. The adapter must review the sidestep before use. */
class BlockRecovery
{
public:
    // MovedCm is the horizontal distance the feet moved this tick. Returns true once per
    // two blocked seconds; the caller then asks for a sidestep target.
    bool Advance(double Dt, double MovedCm, bool bHasTarget)
    {
        if (!bHasTarget || !std::isfinite(Dt) || Dt <= 0 || !std::isfinite(MovedCm) || MovedCm < 0) { StillSeconds = 0; return false; }
        Dt = std::min(Dt, 0.25);
        if (MovedCm / Dt >= BlockedSpeedCmPerSecond) { StillSeconds = 0; return false; }
        StillSeconds += Dt;
        if (StillSeconds < BlockedSeconds) return false;
        StillSeconds = 0; ++Attempts;
        return true;
    }
    // Perpendicular to the blocked direction, alternating sides on each request.
    Point2 SidestepTarget(const Point2& Feet, const Point2& Target)
    {
        const double DX = Target.X - Feet.X, DY = Target.Y - Feet.Y, L = std::hypot(DX, DY);
        const double NX = L > 1e-9 ? -DY / L : 0.0, NY = L > 1e-9 ? DX / L : 1.0;
        const Point2 Result{Feet.X + NX * SidestepCm * Side, Feet.Y + NY * SidestepCm * Side};
        Side = -Side;
        return Result;
    }
    void Reset() { StillSeconds = 0; Attempts = 0; Side = 1; }
    int AttemptCount() const { return Attempts; }
    double StillTime() const { return StillSeconds; }
private:
    double StillSeconds = 0;
    int Attempts = 0;
    int Side = 1;
};

inline double WrapDegrees(double D)
{
    D = std::fmod(D + 180.0, 360.0);
    if (D < 0) D += 360.0;
    return D - 180.0;
}
inline double YawTowardDegrees(const Point2& From, const Point2& To)
{
    return std::atan2(To.Y - From.Y, To.X - From.X) * 180.0 / 3.14159265358979323846;
}
// Constant-rate turn toward a target yaw; returns the new yaw.
inline double TurnToward(double CurrentYaw, double TargetYaw, double Dt, double RateDegreesPerSecond = TurnRateDegreesPerSecond)
{
    if (!std::isfinite(CurrentYaw) || !std::isfinite(TargetYaw) || !std::isfinite(Dt) || Dt <= 0) return CurrentYaw;
    const double Delta = WrapDegrees(TargetYaw - CurrentYaw);
    const double Step = RateDegreesPerSecond * std::min(Dt, 0.25);
    if (std::abs(Delta) <= Step) return WrapDegrees(TargetYaw);
    return WrapDegrees(CurrentYaw + (Delta > 0 ? Step : -Step));
}
} // namespace MikdashRoute
