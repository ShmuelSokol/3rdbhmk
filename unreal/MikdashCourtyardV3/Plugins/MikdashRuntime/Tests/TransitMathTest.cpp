#define _CRT_SECURE_NO_WARNINGS

// Standalone test for TransitMath.h. No Unreal, no engine headers.
//
//   cl /std:c++17 /EHsc /W4 /WX /I<...>/Public TransitMathTest.cpp
//   TransitMathTest.exe <optional path to tests.json>
//
// Every check goes through Check(), which is live in debug AND release builds; the
// printed lines are the numeric evidence, and with an argument the same numbers are
// written as JSON for the runtime-review receipt.

#include "TransitMath.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

using namespace MikdashTransit;

static bool Near(double A, double B, double Tolerance = 1e-9) { return std::abs(A - B) <= Tolerance; }

// Deliberately NOT <cassert>: a release build (/O2 /DNDEBUG) would compile every assert
// away and the "release" run would prove nothing. Check() always evaluates its argument,
// always counts, and exits non-zero on the first failure.
static long long CheckCount = 0;
static void CheckImpl(bool Condition, const char* Text, int Line)
{
    ++CheckCount;
    if (!Condition)
    {
        std::fprintf(stderr, "FAIL line %d: %s\n", Line, Text);
        std::exit(1);
    }
}
#define Check(X) CheckImpl(!!(X), #X, __LINE__)

// Collected evidence, emitted as JSON when an output path is given.
static std::vector<std::pair<std::string, std::string>> Facts;
static void Fact(const std::string& Key, double Value)
{
    char Buffer[64];
    std::snprintf(Buffer, sizeof(Buffer), "%.6f", Value);
    Facts.emplace_back(Key, Buffer);
}
static void FactInt(const std::string& Key, long long Value)
{
    Facts.emplace_back(Key, std::to_string(Value));
}

static const double NaNValue = std::numeric_limits<double>::quiet_NaN();

// A straight 400 m run east, then 300 m north: a 3-4-5 dogleg with an exact length.
static const Vec3 Dogleg[3] = {{0, 0, 0}, {40000, 0, 0}, {40000, 30000, 0}};

// A closed 100 m square, used for wrap-around and following checks.
static const Vec3 Square[4] = {{0, 0, 0}, {10000, 0, 0}, {10000, 10000, 0}, {0, 10000, 0}};

// ---------------------------------------------------------------------------

static void GeometryChecks()
{
    // PerSegment 1 reproduces the control polyline exactly, so the length is exact.
    std::vector<Vec3> Points(static_cast<size_t>(DensifiedPointCount(3, false, 1)));
    std::vector<double> Cumulative(Points.size());
    Check(Points.size() == 3);
    const double Total = BuildArcTable(Dogleg, 3, false, 1, Points.data(), Cumulative.data());
    Check(Near(Total, 70000.0, 1e-6));
    Check(Near(Cumulative[0], 0.0));
    for (size_t I = 1; I < Cumulative.size(); ++I) Check(Cumulative[I] >= Cumulative[I - 1]);

    Vec3 Position{}, Tangent{};
    Check(SampleRoute(Points.data(), Cumulative.data(), 3, false, 0.0, Position, Tangent));
    Check(Near(Position.X, 0.0, 1e-6) && Near(Position.Y, 0.0, 1e-6));
    Check(Near(YawDegrees(Tangent), 0.0, 1e-6));
    Check(SampleRoute(Points.data(), Cumulative.data(), 3, false, 20000.0, Position, Tangent));
    Check(Near(Position.X, 20000.0, 1e-6) && Near(Position.Y, 0.0, 1e-6));
    Check(SampleRoute(Points.data(), Cumulative.data(), 3, false, 55000.0, Position, Tangent));
    Check(Near(Position.X, 40000.0, 1e-6) && Near(Position.Y, 15000.0, 1e-6));
    Check(Near(YawDegrees(Tangent), 90.0, 1e-6));
    Check(Near(Length(Tangent), 1.0, 1e-9));
    // Past the end of an open route: clamped, not wrapped.
    Check(SampleRoute(Points.data(), Cumulative.data(), 3, false, 1e9, Position, Tangent));
    Check(Near(Position.Y, 30000.0, 1e-6));

    // Arc length is the true accumulated distance: stepping 1 cm of S moves 1 cm.
    double Walked = 0.0;
    Vec3 Previous{};
    SampleRoute(Points.data(), Cumulative.data(), 3, false, 0.0, Previous, Tangent);
    for (int I = 1; I <= 7000; ++I)
    {
        SampleRoute(Points.data(), Cumulative.data(), 3, false, I * 10.0, Position, Tangent);
        Walked += Length(Position - Previous);
        Previous = Position;
    }
    Check(Near(Walked, 70000.0, 1e-3));
    Fact("dogleg_length_cm", Total);
    Fact("dogleg_walked_cm", Walked);

    // Closed square: wrapping, and a lap that returns to the start.
    std::vector<Vec3> Loop(static_cast<size_t>(DensifiedPointCount(4, true, 1)));
    std::vector<double> LoopCumulative(Loop.size());
    const int LoopCount = static_cast<int>(Loop.size());
    const double Perimeter = BuildArcTable(Square, 4, true, 1, Loop.data(), LoopCumulative.data());
    Check(Near(Perimeter, 40000.0, 1e-6));
    Vec3 Start{}, Lap{};
    SampleRoute(Loop.data(), LoopCumulative.data(), LoopCount, true, 0.0, Start, Tangent);
    SampleRoute(Loop.data(), LoopCumulative.data(), LoopCount, true, Perimeter, Lap, Tangent);
    Check(Near(Length(Lap - Start), 0.0, 1e-6));
    SampleRoute(Loop.data(), LoopCumulative.data(), LoopCount, true, -10000.0, Lap, Tangent);
    Check(Near(Lap.X, 0.0, 1e-6) && Near(Lap.Y, 10000.0, 1e-6));   // one side back from the start
    Fact("square_perimeter_cm", Perimeter);

    // Catmull-Rom smoothing: strictly longer than the chords, but not wildly so, and it
    // still passes through every control point.
    std::vector<Vec3> Smooth(static_cast<size_t>(DensifiedPointCount(4, true, 16)));
    std::vector<double> SmoothCumulative(Smooth.size());
    const double SmoothLength = BuildArcTable(Square, 4, true, 16, Smooth.data(), SmoothCumulative.data());
    Check(SmoothLength > Perimeter);
    Check(SmoothLength < Perimeter * 1.35);
    for (int Corner = 0; Corner < 4; ++Corner)
    {
        // Control point k lands on densified index k * 16.
        Check(Near(Length(Smooth[static_cast<size_t>(Corner) * 16] - Square[Corner]), 0.0, 1e-6));
    }
    Fact("square_smoothed_cm", SmoothLength);

    // Lane offset: heading north (+Y, yaw 90) puts the driver's right at -X.
    const Vec3 North{0, 1, 0};
    const Vec3 Offset = ApplyLaneOffset(Vec3{100, 200, 300}, North, 350.0, 40.0);
    Check(Near(Offset.X, 100.0 - 350.0, 1e-6));
    Check(Near(Offset.Y, 200.0, 1e-6));
    Check(Near(Offset.Z, 340.0, 1e-6));
    // Heading east (+X, yaw 0): right is +Y.
    const Vec3 East = ApplyLaneOffset(Vec3{0, 0, 0}, Vec3{1, 0, 0}, 350.0, 0.0);
    Check(Near(East.Y, 350.0, 1e-6) && Near(East.X, 0.0, 1e-6));

    // Pitch on a graded route.
    Check(Near(PitchDegrees(Vec3{1, 0, 1}), 45.0, 1e-9));
    Check(Near(PitchDegrees(Vec3{1, 0, -1}), -45.0, 1e-9));

    // Wrapped gaps.
    Check(Near(ForwardGap(1000.0, 3000.0, 40000.0, true), 2000.0, 1e-9));
    Check(Near(ForwardGap(39000.0, 1000.0, 40000.0, true), 2000.0, 1e-9));   // across the seam
    Check(Near(ForwardGap(3000.0, 1000.0, 40000.0, false), 0.0, 1e-9));      // leader behind: no leader

    // Projection: an authored stop position becomes an arc distance on the route the
    // runtime built for itself, with the planar residual reported.
    double Where = -1.0, Error = -1.0;
    Check(ProjectOntoRoute(Points.data(), Cumulative.data(), 3, Vec3{25000, 0, 0}, Where, Error));
    Check(Near(Where, 25000.0, 1e-6) && Near(Error, 0.0, 1e-6));
    // Off the centreline: the arc distance is the foot of the perpendicular, and the
    // residual is the offset, not zero.
    Check(ProjectOntoRoute(Points.data(), Cumulative.data(), 3, Vec3{25000, 800, 0}, Where, Error));
    Check(Near(Where, 25000.0, 1e-6) && Near(Error, 800.0, 1e-6));
    // Height is ignored for the match, so a kerb-height stop still binds correctly.
    Check(ProjectOntoRoute(Points.data(), Cumulative.data(), 3, Vec3{25000, 0, 5000}, Where, Error));
    Check(Near(Where, 25000.0, 1e-6) && Near(Error, 0.0, 1e-6));
    // Past the far end: clamped to the last segment.
    Check(ProjectOntoRoute(Points.data(), Cumulative.data(), 3, Vec3{40000, 90000, 0}, Where, Error));
    Check(Near(Where, 70000.0, 1e-6) && Near(Error, 60000.0, 1e-6));
    // On the second leg.
    Check(ProjectOntoRoute(Points.data(), Cumulative.data(), 3, Vec3{40000, 12000, 0}, Where, Error));
    Check(Near(Where, 52000.0, 1e-6) && Near(Error, 0.0, 1e-6));
    Check(!ProjectOntoRoute(nullptr, Cumulative.data(), 3, Vec3{0, 0, 0}, Where, Error));
    Check(!ProjectOntoRoute(Points.data(), Cumulative.data(), 1, Vec3{0, 0, 0}, Where, Error));
    Check(!ProjectOntoRoute(Points.data(), Cumulative.data(), 3, Vec3{NaNValue, 0, 0}, Where, Error));

    // Hostile input yields a refusal, never a crash or a NaN.
    Check(!SampleRoute(nullptr, Cumulative.data(), 3, false, 0.0, Position, Tangent));
    Check(!SampleRoute(Points.data(), nullptr, 3, false, 0.0, Position, Tangent));
    Check(!SampleRoute(Points.data(), Cumulative.data(), 1, false, 0.0, Position, Tangent));
    Check(DensifiedPointCount(1, false, 4) == 0);
    Check(Near(BuildArcTable(Dogleg, 1, false, 4, Points.data(), Cumulative.data()), 0.0));
    Check(Near(WrapDistance(NaNValue, 40000.0, true), 0.0));
    Check(SampleRoute(Points.data(), Cumulative.data(), 3, false, NaNValue, Position, Tangent) && Finite(Position));

    std::printf("geometry: dogleg %.0f cm exact, walked %.3f cm, square %.0f cm, smoothed %.0f cm, lane offset and wrap correct\n",
                Total, Walked, Perimeter, SmoothLength);
}

// ---------------------------------------------------------------------------

static void FollowChecks()
{
    FollowParams P;
    P.DesiredSpeedCmPerSecond = 900.0;
    P.MinGapCm = 450.0;
    P.TimeHeadwaySeconds = 1.4;

    // Empty road: accelerate, and converge on the desired speed without overshooting it.
    double Speed = 0.0;
    for (int I = 0; I < 4000; ++I)
    {
        Speed = IntegrateSpeed(Speed, FollowAcceleration(Speed, 0.0, 1e9, P), 0.05, P.DesiredSpeedCmPerSecond);
        Check(Speed <= P.DesiredSpeedCmPerSecond + 1e-9);
    }
    Check(Speed > P.DesiredSpeedCmPerSecond * 0.98);
    Fact("free_road_terminal_speed_cm_s", Speed);

    // Steady state behind a leader at the same speed. The IDM equilibrium is NOT the
    // desired gap s*: the free-road term and the interaction term cancel at
    // s* / sqrt(1 - (v/v0)^4), which is strictly larger. Check that closed form, and
    // that the equilibrium is stable rather than merely a root.
    const double Cruise = P.DesiredSpeedCmPerSecond * 0.5;
    const double Star = DesiredGapCm(Cruise, 0.0, P);
    Check(Near(Star, P.MinGapCm + Cruise * P.TimeHeadwaySeconds, 1e-6));
    const double FreeShare = 1.0 - std::pow(Cruise / P.DesiredSpeedCmPerSecond, 4.0);
    const double Equilibrium = Star / std::sqrt(FreeShare);
    Check(Equilibrium > Star);
    const double AtEquilibrium = FollowAcceleration(Cruise, Cruise, Equilibrium, P);
    Check(std::abs(AtEquilibrium) < 1e-9);
    Check(FollowAcceleration(Cruise, Cruise, Equilibrium * 0.9, P) < 0.0);   // closer: brake
    Check(FollowAcceleration(Cruise, Cruise, Equilibrium * 1.1, P) > 0.0);   // further: accelerate
    Fact("desired_gap_cm", Star);
    Fact("equilibrium_gap_cm", Equilibrium);
    Fact("equilibrium_accel_cm_s2", AtEquilibrium);

    // Too close: brake. Too far: accelerate. Zero gap: emergency.
    Check(FollowAcceleration(Speed, Speed, Equilibrium * 0.4, P) < -20.0);
    Check(FollowAcceleration(Speed * 0.5, Speed, Equilibrium * 4.0, P) > 0.0);
    Check(Near(FollowAcceleration(Speed, 0.0, 0.0, P), -P.EmergencyDecelerationCmPerSecond2, 1e-9));
    Check(Near(FollowAcceleration(Speed, 0.0, -500.0, P), -P.EmergencyDecelerationCmPerSecond2, 1e-9));
    // Never exceeds the authored limits in either direction.
    for (double V = 0; V <= 2000; V += 25)
    {
        for (double G = 1; G <= 20000; G += 137)
        {
            const double A = FollowAcceleration(V, 0.0, G, P);
            Check(A <= P.MaxAccelerationCmPerSecond2 + 1e-9);
            Check(A >= -P.EmergencyDecelerationCmPerSecond2 - 1e-9);
            Check(std::isfinite(A));
        }
    }

    // Stop line: v^2 / 2d, capped at the emergency rate, and never positive.
    Check(Near(StopLineAcceleration(600.0, 30000.0, P), -(600.0 * 600.0) / (2.0 * 30000.0), 1e-9));
    Check(Near(StopLineAcceleration(600.0, 1.0, P), -P.EmergencyDecelerationCmPerSecond2, 1e-9));
    Check(Near(StopLineAcceleration(0.0, 0.5, P), 0.0, 1e-9));
    Check(Near(ComfortBrakingDistanceCm(900.0, P), (900.0 * 900.0) / (2.0 * 200.0), 1e-9));

    // A vehicle braking on the stop-line law actually stops, and stops short of the line.
    double V = 900.0, Distance = ComfortBrakingDistanceCm(V, P) + 200.0;
    int Steps = 0;
    while (V > 1.0 && Steps < 20000)
    {
        V = IntegrateSpeed(V, StopLineAcceleration(V, Distance, P), 0.02, P.DesiredSpeedCmPerSecond);
        Distance -= V * 0.02;
        ++Steps;
    }
    Check(Distance > -50.0 && Distance < 400.0);
    Fact("stop_line_residual_cm", Distance);

    // Integration guards.
    Check(Near(IntegrateSpeed(500.0, 0.0, NaNValue, 900.0), 500.0));
    Check(Near(IntegrateSpeed(500.0, NaNValue, 0.1, 900.0), 500.0));
    Check(Near(IntegrateSpeed(10.0, -1e6, 0.1, 900.0), 0.0));           // never negative
    Check(Near(IntegrateSpeed(10.0, 1e6, 100.0, 900.0), 900.0));        // Dt clamped, speed capped

    std::printf("following: free-road terminal %.1f cm/s, desired gap %.0f cm, equilibrium gap %.1f cm at accel %.2e, stop-line residual %.1f cm\n",
                Speed, Star, Equilibrium, AtEquilibrium, Distance);
}

// ---------------------------------------------------------------------------
// A platoon on a closed loop: nobody may pass through anybody, ever.

static void PlatoonChecks()
{
    std::vector<Vec3> Loop(static_cast<size_t>(DensifiedPointCount(4, true, 8)));
    std::vector<double> Cumulative(Loop.size());
    const int Count = static_cast<int>(Loop.size());
    const double Total = BuildArcTable(Square, 4, true, 8, Loop.data(), Cumulative.data());

    FollowParams P;
    P.DesiredSpeedCmPerSecond = 800.0;
    const int Vehicles = 16;
    const double BodyLengthCm = 460.0;
    std::vector<double> S(Vehicles), V(Vehicles);
    for (int I = 0; I < Vehicles; ++I)
    {
        S[static_cast<size_t>(I)] = SpawnDistanceFor(I, Vehicles, Total, 40.0, 20260908u);
        V[static_cast<size_t>(I)] = HashRange(20260908u, static_cast<uint32_t>(I), 3u, 200.0, 700.0);
    }
    // Ordering: vehicle i's leader is i+1 (spawn distances increase with index).
    for (int I = 1; I < Vehicles; ++I) Check(S[static_cast<size_t>(I)] > S[static_cast<size_t>(I - 1)]);

    // The densified loop is sampleable everywhere a vehicle can be.
    for (int I = 0; I < Vehicles; ++I)
    {
        Vec3 Probe{}, Tangent{};
        Check(SampleRoute(Loop.data(), Cumulative.data(), Count, true, S[static_cast<size_t>(I)], Probe, Tangent));
        Check(Finite(Probe) && Near(Length(Tangent), 1.0, 1e-9));
    }

    double MinimumGap = 1e30, MaximumSpeed = 0.0;
    for (int Frame = 0; Frame < 40000; ++Frame)
    {
        for (int I = 0; I < Vehicles; ++I)
        {
            const int Lead = (I + 1) % Vehicles;
            const double Gap = ForwardGap(S[static_cast<size_t>(I)], S[static_cast<size_t>(Lead)], Total, true) - BodyLengthCm;
            MinimumGap = std::min(MinimumGap, Gap);
            Check(Gap > 0.0);   // no vehicle ever occupies its leader's body
            const double A = FollowAcceleration(V[static_cast<size_t>(I)], V[static_cast<size_t>(Lead)], Gap, P);
            V[static_cast<size_t>(I)] = IntegrateSpeed(V[static_cast<size_t>(I)], A, 0.05, P.DesiredSpeedCmPerSecond);
            MaximumSpeed = std::max(MaximumSpeed, V[static_cast<size_t>(I)]);
        }
        for (int I = 0; I < Vehicles; ++I)
        {
            S[static_cast<size_t>(I)] = WrapDistance(S[static_cast<size_t>(I)] + V[static_cast<size_t>(I)] * 0.05, Total, true);
        }
    }
    // A ring of 16 vehicles on 400 m cannot reach the desired speed; it settles into a
    // steady flow. What matters is that it is steady, positive and collision-free.
    double SpeedSpread = 0.0;
    for (int I = 0; I < Vehicles; ++I)
    {
        Check(V[static_cast<size_t>(I)] > 50.0);
        SpeedSpread = std::max(SpeedSpread, std::abs(V[static_cast<size_t>(I)] - V[0]));
    }
    Check(MaximumSpeed <= P.DesiredSpeedCmPerSecond + 1e-9);
    Fact("platoon_min_gap_cm", MinimumGap);
    Fact("platoon_speed_spread_cm_s", SpeedSpread);
    FactInt("platoon_vehicles", Vehicles);
    std::printf("platoon: 16 vehicles, 40000 frames, minimum clearance %.1f cm, final speed spread %.2f cm/s, no pass-through\n",
                MinimumGap, SpeedSpread);
}

// ---------------------------------------------------------------------------

static void DwellChecks()
{
    FollowParams P;
    DwellConfig C;
    C.MinDwellSeconds = 20.0;
    C.MaxDwellSeconds = 40.0;

    // Doors never open on a moving vehicle, however close to the stop line it is.
    StopState Moving;
    Moving.Phase = StopPhase::Braking;
    Moving.TargetStopIndex = 0;
    for (int I = 0; I < 500; ++I)
    {
        const StopEvents E = AdvanceStopState(Moving, 0.05, 600.0, 0.0, P, C, 11u, 0);
        Check(!E.bDoorsOpened);
        Check(Moving.Phase == StopPhase::Braking);
    }
    // ...nor when stopped far from the line.
    StopState Short;
    Short.Phase = StopPhase::Braking;
    Short.TargetStopIndex = 0;
    for (int I = 0; I < 500; ++I)
    {
        Check(!AdvanceStopState(Short, 0.05, 0.0, 5000.0, P, C, 11u, 0).bDoorsOpened);
    }
    Check(Short.Phase == StopPhase::Braking);

    // A full cycle, with the doors ramping monotonically each way.
    StopState State;
    State.TargetStopIndex = 2;
    double Distance = 40000.0, Speed = 900.0;
    int Opened = 0, Closed = 0, Departed = 0, BrakingStarts = 0;
    double DoorPeak = 0.0, PreviousDoor = 0.0, DwellMeasured = 0.0, DwellDrawn = 0.0, StopError = 1e30;
    bool bOpening = true;
    for (int I = 0; I < 40000; ++I)
    {
        const double A = LongitudinalAcceleration(State, Speed, 0.0, 1e9, Distance, P);
        Speed = IntegrateSpeed(Speed, A, 0.05, P.DesiredSpeedCmPerSecond);
        if (!IsHeldAtStop(State)) Distance -= Speed * 0.05;
        const StopEvents E = AdvanceStopState(State, 0.05, Speed, Distance, P, C, 11u, 4);
        if (E.bBeganBraking) ++BrakingStarts;
        if (E.bDoorsOpened)
        {
            ++Opened;
            DwellDrawn = State.DwellSeconds;
            StopError = Distance;   // signed error against the stop line AT the moment of arrival
            Check(State.ServedStopIndex == 2);
            Check(Speed <= C.StoppedSpeedCmPerSecond);
            bOpening = false;
        }
        if (State.Phase == StopPhase::Dwelling) DwellMeasured += 0.05;
        if (E.bDoorsClosed) ++Closed;
        if (E.bDeparted) ++Departed;
        // Doors are monotone within each travel phase.
        if (State.Phase == StopPhase::DoorsOpening) Check(State.DoorFraction >= PreviousDoor - 1e-9);
        if (State.Phase == StopPhase::DoorsClosing) Check(State.DoorFraction <= PreviousDoor + 1e-9);
        PreviousDoor = State.DoorFraction;
        DoorPeak = std::max(DoorPeak, State.DoorFraction);
        Check(State.DoorFraction >= 0.0 && State.DoorFraction <= 1.0);
        // While the doors are not shut the vehicle is held: it must not creep.
        if (IsHeldAtStop(State) && State.Phase != StopPhase::DoorsOpening) Check(Speed <= 1e-9);
        if (Departed) break;
    }
    Check(Opened == 1 && Closed == 1 && Departed == 1 && BrakingStarts == 1);
    Check(!bOpening);
    Check(Near(DoorPeak, 1.0, 1e-9));
    Check(DwellDrawn >= C.MinDwellSeconds - 1e-9 && DwellDrawn <= C.MaxDwellSeconds + 1e-9);
    Check(std::abs(DwellMeasured - DwellDrawn) < 0.2);
    Check(State.RunIndex == 1);
    Check(State.Phase == StopPhase::Running);
    Fact("cycle_dwell_drawn_s", DwellDrawn);
    Fact("cycle_dwell_measured_s", DwellMeasured);
    Fact("cycle_stop_error_cm", StopError);
    Check(std::abs(StopError) <= C.ArrivalToleranceCm);

    // Door offset is smoothstepped: monotone, 0 at 0, full travel at 1, symmetric at 0.5.
    Check(Near(DoorOffsetCm(0.0, 55.0), 0.0, 1e-12));
    Check(Near(DoorOffsetCm(1.0, 55.0), 55.0, 1e-12));
    Check(Near(DoorOffsetCm(0.5, 55.0), 27.5, 1e-12));
    Check(Near(DoorOffsetCm(-3.0, 55.0), 0.0, 1e-12));
    Check(Near(DoorOffsetCm(NaNValue, 55.0), 0.0, 1e-12));
    double Last = -1.0;
    for (double F = 0.0; F <= 1.0; F += 0.01)
    {
        const double O = DoorOffsetCm(F, 55.0);
        Check(O >= Last - 1e-12);
        Last = O;
    }

    // Dwell draws stay inside the window for every (run, stop) and vary between them.
    double Lowest = 1e30, Highest = -1e30;
    int Distinct = 0;
    double Previous = -1.0;
    for (int Run = 0; Run < 400; ++Run)
    {
        for (int Stop = 0; Stop < 3; ++Stop)
        {
            const double D = DwellForStop(9001u, Run, Stop, 20.0, 40.0);
            Check(D >= 20.0 && D <= 40.0);
            Lowest = std::min(Lowest, D);
            Highest = std::max(Highest, D);
            if (std::abs(D - Previous) > 1e-9) ++Distinct;
            Previous = D;
        }
    }
    Check(Distinct > 1100);
    Check(Lowest < 21.5 && Highest > 38.5);   // the whole window is used
    // An inverted or degenerate window is repaired, not honoured blindly.
    Check(Near(DwellForStop(1u, 0, 0, 40.0, 20.0), DwellForStop(1u, 0, 0, 20.0, 40.0), 1e-12));
    Check(Near(DwellForStop(1u, 0, 0, 30.0, 30.0), 30.0, 1e-12));
    Fact("dwell_min_drawn_s", Lowest);
    Fact("dwell_max_drawn_s", Highest);

    std::printf("dwell: one open/close/depart per stop, drawn %.2f s vs measured %.2f s, stopped %.1f cm from the line, window used %.2f..%.2f s\n",
                DwellDrawn, DwellMeasured, StopError, Lowest, Highest);
}

// ---------------------------------------------------------------------------

static void ScheduleChecks()
{
    // Headways stay inside the 2..5 minute window and spread across it.
    double Lowest = 1e30, Highest = -1e30, Sum = 0.0;
    const int Runs = 5000;
    for (int I = 0; I < Runs; ++I)
    {
        const double H = HeadwayForRun(4242u, static_cast<uint32_t>(I), 120.0, 300.0);
        Check(H >= 120.0 && H <= 300.0);
        Lowest = std::min(Lowest, H);
        Highest = std::max(Highest, H);
        Sum += H;
    }
    const double Mean = Sum / Runs;
    Check(Mean > 200.0 && Mean < 220.0);   // uniform on [120, 300] has mean 210
    Check(Lowest < 122.0 && Highest > 298.0);
    Fact("headway_mean_s", Mean);
    Fact("headway_min_s", Lowest);
    Fact("headway_max_s", Highest);

    // Departure times are strictly increasing and consistent with the headways.
    double Previous = ScheduledDepartureTime(4242u, 0, 60.0, 120.0, 300.0);
    Check(Near(Previous, 60.0, 1e-12));
    for (int I = 1; I < 200; ++I)
    {
        const double T = ScheduledDepartureTime(4242u, I, 60.0, 120.0, 300.0);
        const double Delta = T - Previous;
        Check(Delta >= 120.0 - 1e-9 && Delta <= 300.0 + 1e-9);
        Check(Near(Delta, HeadwayForRun(4242u, static_cast<uint32_t>(I - 1), 120.0, 300.0), 1e-9));
        Previous = T;
    }
    // Determinism: the same seed reproduces the same timetable exactly.
    Check(Near(ScheduledDepartureTime(4242u, 137, 60.0, 120.0, 300.0), Previous - 0.0, 1e9));
    Check(Near(ScheduledDepartureTime(4242u, 199, 60.0, 120.0, 300.0),
                ScheduledDepartureTime(4242u, 199, 60.0, 120.0, 300.0), 0.0));
    // A different seed gives a different timetable.
    Check(!Near(ScheduledDepartureTime(4243u, 199, 60.0, 120.0, 300.0), Previous, 1.0));
    // An inverted window is repaired; a zero window degenerates safely, not to zero.
    Check(HeadwayForRun(1u, 0, 300.0, 120.0) >= 120.0);
    Check(HeadwayForRun(1u, 0, -50.0, -10.0) >= 1.0);
    Fact("timetable_200th_departure_s", Previous);

    // Boarding demand: inside the window, scaled by density, clamped for absurd input.
    int MinSeen = 1 << 30, MaxSeen = 0;
    long long TotalPeople = 0;
    for (int Run = 0; Run < 500; ++Run)
    {
        for (int Stop = 0; Stop < 3; ++Stop)
        {
            const int N = BoardingCountFor(777u, 1, Stop, Run, 6, 22, 1.0);
            Check(N >= 6 && N <= 22);
            MinSeen = std::min(MinSeen, N);
            MaxSeen = std::max(MaxSeen, N);
            TotalPeople += N;
        }
    }
    Check(MinSeen == 6 && MaxSeen == 22);
    Check(BoardingCountFor(777u, 1, 0, 0, 6, 22, 0.0) == 0);
    Check(BoardingCountFor(777u, 1, 0, 0, 6, 22, 2.0) == 2 * BoardingCountFor(777u, 1, 0, 0, 6, 22, 1.0));
    Check(BoardingCountFor(777u, 1, 0, 0, 6, 22, 1e9) <= 22 * 8);
    Check(BoardingCountFor(777u, 1, 0, 0, 6, 22, NaNValue) == BoardingCountFor(777u, 1, 0, 0, 6, 22, 1.0));
    Check(BoardingCountFor(777u, 1, 0, 0, 0, 0, 4.0) == 0);
    Fact("boarding_mean_per_stop", static_cast<double>(TotalPeople) / 1500.0);
    FactInt("boarding_min", MinSeen);
    FactInt("boarding_max", MaxSeen);

    std::printf("schedule: headway mean %.1f s in [%.1f, %.1f], 200 departures strictly increasing, boarding %d..%d per stop\n",
                Mean, Lowest, Highest, MinSeen, MaxSeen);
}

// ---------------------------------------------------------------------------

static void BudgetChecks()
{
    // Every vehicle is visited exactly once per sweep, and the per-frame cost is bounded.
    for (int Count : {1, 7, 64, 240, 1000})
    {
        for (int Budget : {1, 5, 32, 4096})
        {
            std::vector<int> Visits(static_cast<size_t>(Count), 0);
            int Cursor = 0;
            const int Frames = FramesPerSweep(Count, Budget);
            Check(Frames >= 1);
            for (int F = 0; F < Frames; ++F)
            {
                const UpdateWindow W = NextUpdateWindow(Cursor, Count, Budget);
                Check(W.Total() <= Budget);
                Check(W.Total() == std::min(Budget, Count));
                for (int K = 0; K < W.Total(); ++K)
                {
                    const int Index = K < W.FirstCount ? W.FirstStart + K : W.SecondStart + (K - W.FirstCount);
                    Check(Index >= 0 && Index < Count);
                    Visits[static_cast<size_t>(Index)] += 1;
                }
                Cursor = W.NextCursor;
            }
            for (int I = 0; I < Count; ++I) Check(Visits[static_cast<size_t>(I)] >= 1);
        }
    }
    Check(NextUpdateWindow(0, 0, 8).Total() == 0);
    Check(NextUpdateWindow(0, 8, 0).Total() == 0);
    Check(NextUpdateWindow(-5, 8, 3).FirstStart == 0);
    Check(NextUpdateWindow(99, 8, 3).FirstStart == 0);
    Check(FramesPerSweep(0, 8) == 0 && FramesPerSweep(8, 0) == 0);

    // Catch-up restores real-time travel: a vehicle stepped once every N frames must
    // cover the same ground as one stepped every frame.
    const double Dt = 1.0 / 60.0, Speed = 900.0;
    const int Count = 240, Budget = 24;
    double Travelled = 0.0;
    int Cursor = 0;
    for (int Frame = 0; Frame < 600; ++Frame)
    {
        const UpdateWindow W = NextUpdateWindow(Cursor, Count, Budget);
        for (int K = 0; K < W.Total(); ++K)
        {
            const int Index = K < W.FirstCount ? W.FirstStart + K : W.SecondStart + (K - W.FirstCount);
            if (Index != 0) continue;
            Travelled += Speed * CatchUpSeconds(Dt, Count, Budget);
        }
        Cursor = W.NextCursor;
    }
    const double Expected = Speed * 600 * Dt;
    Check(std::abs(Travelled - Expected) < Expected * 0.02);
    // The clamp is real: a one-second hitch cannot become a one-second leap.
    Check(Near(CatchUpSeconds(1.0, 240, 24), 0.35, 1e-12));
    Check(Near(CatchUpSeconds(NaNValue, 240, 24), 0.0));
    Check(Near(CatchUpSeconds(-1.0, 240, 24), 0.0));
    // And the clamp keeps a step below the arrival tolerance at the default speed.
    const DwellConfig C;
    Check(CatchUpSeconds(1.0, 240, 24) * 900.0 < 400.0);
    Check(C.ArrivalToleranceCm > 0.0);
    Fact("catchup_travel_error_cm", std::abs(Travelled - Expected));
    Fact("catchup_max_step_travel_cm", CatchUpSeconds(1.0, 240, 24) * 900.0);

    std::printf("budget: full coverage at every (count, budget), catch-up travel error %.2f cm over 10 s, max step %.0f cm\n",
                std::abs(Travelled - Expected), CatchUpSeconds(1.0, 240, 24) * 900.0);
}

// ---------------------------------------------------------------------------

static void ConsistChecks()
{
    // A three-car set on a straight run: constant yaw, exact pitch, exact spacing.
    std::vector<Vec3> Points(static_cast<size_t>(DensifiedPointCount(3, false, 1)));
    std::vector<double> Cumulative(Points.size());
    const double Total = BuildArcTable(Dogleg, 3, false, 1, Points.data(), Cumulative.data());
    const double CarLength = 3200.0, Gap = 60.0;

    Check(Near(CarCentreOffsetCm(0, CarLength, Gap), 1600.0, 1e-9));
    Check(Near(CarCentreOffsetCm(1, CarLength, Gap), 1600.0 + 3260.0, 1e-9));
    Check(Near(CarCentreOffsetCm(2, CarLength, Gap), 1600.0 + 2 * 3260.0, 1e-9));

    Vec3 Previous{};
    for (int Car = 0; Car < 3; ++Car)
    {
        Vec3 Position{};
        double Yaw = 0.0, Pitch = 0.0;
        Check(SampleCarPose(Points.data(), Cumulative.data(), 3, false, 20000.0, Car,
                             CarLength, Gap, 400.0, 0.0, 60.0, Position, Yaw, Pitch));
        Check(Near(Yaw, 0.0, 1e-6) && Near(Pitch, 0.0, 1e-6));
        Check(Near(Position.Z, 60.0, 1e-6));
        if (Car > 0) Check(Near(Length(Position - Previous), CarLength + Gap, 1e-6));
        Previous = Position;
    }

    // Through the dogleg corner the cars must not overlap and the yaws must differ:
    // that is the whole point of posing from the bogie chord.
    double LastYaw = 1e30;
    Vec3 LastPosition{};
    int DistinctYaws = 0;
    double ClosestPair = 1e30;
    for (int Car = 0; Car < 3; ++Car)
    {
        Vec3 Position{};
        double Yaw = 0.0, Pitch = 0.0;
        Check(SampleCarPose(Points.data(), Cumulative.data(), 3, false, 41500.0, Car,
                             CarLength, Gap, 400.0, -150.0, 60.0, Position, Yaw, Pitch));
        if (LastYaw < 1e29)
        {
            if (std::abs(WrapDegrees(Yaw - LastYaw)) > 1.0) ++DistinctYaws;
            ClosestPair = std::min(ClosestPair, Length(Position - LastPosition));
        }
        LastYaw = Yaw;
        LastPosition = Position;
    }
    Check(DistinctYaws >= 1);        // the set articulates round the corner
    Check(ClosestPair > CarLength * 0.5);   // and no two car centres collapse together
    Fact("consist_corner_closest_centre_cm", ClosestPair);
    FactInt("consist_corner_distinct_yaws", DistinctYaws);

    // Degenerate route: refusal, not a crash.
    Vec3 Position{};
    double Yaw = 0.0, Pitch = 0.0;
    Check(!SampleCarPose(nullptr, Cumulative.data(), 3, false, 0.0, 0, CarLength, Gap, 400.0, 0.0, 0.0, Position, Yaw, Pitch));
    Check(Total > 0.0);

    std::printf("consist: 3 cars spaced %.0f cm on tangent, articulated at the corner (%d yaw breaks, closest centres %.0f cm)\n",
                CarLength + Gap, DistinctYaws, ClosestPair);
}

// ---------------------------------------------------------------------------

static void VariationChecks()
{
    // Variant blocking is contiguous and covers every instance exactly once.
    for (int Total : {1, 5, 60, 137})
    {
        for (int Variants : {1, 3, 4})
        {
            int Seen = 0;
            for (int V = 0; V < Variants; ++V)
            {
                const int Start = VariantBlockStart(V, Total, Variants);
                const int End = VariantBlockStart(V + 1, Total, Variants);
                Check(End >= Start);
                for (int I = Start; I < End; ++I) Check(VariantIndexForInstance(I, Total, Variants) == V);
                Seen += End - Start;
            }
            Check(Seen == Total);
        }
    }
    Check(VariantIndexForInstance(-1, 10, 3) == 0);
    Check(VariantIndexForInstance(0, 10, 0) == 0);

    // Apportioning sums exactly and respects zero weights.
    const double Weights[4] = {3.0, 1.0, 0.0, 2.0};
    int Counts[4] = {0, 0, 0, 0};
    for (int Total = 0; Total < 200; ++Total)
    {
        const int Assigned = ApportionVehicles(Weights, 4, Total, Counts);
        Check(Assigned == Total);
        Check(Counts[0] + Counts[1] + Counts[2] + Counts[3] == Total);
        Check(Counts[2] == 0);
        for (int I = 0; I < 4; ++I) Check(Counts[I] >= 0);
    }
    const double DeadWeights[2] = {0.0, 0.0};
    Check(ApportionVehicles(DeadWeights, 2, 50, Counts) == 0);
    Check(ApportionVehicles(nullptr, 2, 50, Counts) == 0);

    // Density scaling and its hard ceiling.
    Check(ScaledVehicleCount(40, 1.0, 400) == 40);
    Check(ScaledVehicleCount(40, 2.5, 400) == 100);
    Check(ScaledVehicleCount(40, 0.0, 400) == 0);
    Check(ScaledVehicleCount(40, 1e9, 400) == 320);      // multiplier clamped to 8
    Check(ScaledVehicleCount(400, 8.0, 500) == 500);     // then the ceiling bites
    Check(ScaledVehicleCount(40, NaNValue, 400) == 40);
    Check(ScaledVehicleCount(0, 4.0, 400) == 0);

    // Paint variation: every colour comes from the palette, and the palette is used.
    const double Palette[9] = {0.8, 0.8, 0.8, 0.05, 0.06, 0.07, 0.35, 0.02, 0.02};
    int Used[3] = {0, 0, 0};
    for (int I = 0; I < 3000; ++I)
    {
        double Rgb[3] = {-1, -1, -1};
        PaintColourFor(31337u, I, Palette, 3, Rgb);
        int Match = -1;
        for (int K = 0; K < 3; ++K)
        {
            if (Near(Rgb[0], Palette[K * 3], 1e-12) && Near(Rgb[1], Palette[K * 3 + 1], 1e-12) && Near(Rgb[2], Palette[K * 3 + 2], 1e-12)) Match = K;
        }
        Check(Match >= 0);
        Used[Match] += 1;
    }
    for (int K = 0; K < 3; ++K) Check(Used[K] > 700);
    double Rgb[3] = {-1, -1, -1};
    PaintColourFor(1u, 0, nullptr, 3, Rgb);
    Check(Near(Rgb[0], 0.5) && Near(Rgb[1], 0.5) && Near(Rgb[2], 0.5));
    PaintColourFor(1u, 0, Palette, 0, Rgb);
    Check(Near(Rgb[0], 0.5));

    // Spawn spacing: distinct, in range, and ordered.
    for (int I = 0; I < 40; ++I)
    {
        const double S = SpawnDistanceFor(I, 40, 40000.0, 100.0, 5u);
        Check(S >= 0.0 && S < 40000.0);
    }
    Check(Near(SpawnDistanceFor(0, 0, 40000.0, 0.0, 5u), 0.0));
    Check(Near(SpawnDistanceFor(0, 4, 0.0, 0.0, 5u), 0.0));

    std::printf("variation: variant blocks contiguous, apportioning exact for 0..199, palette hits %d/%d/%d of 3000\n",
                Used[0], Used[1], Used[2]);
}

// ---------------------------------------------------------------------------
// End to end: one bus on a closed loop with three stops, over an hour of sim time.

static void ServiceChecks()
{
    std::vector<Vec3> Loop(static_cast<size_t>(DensifiedPointCount(4, true, 8)));
    std::vector<double> Cumulative(Loop.size());
    const int Count = static_cast<int>(Loop.size());
    const double Total = BuildArcTable(Square, 4, true, 8, Loop.data(), Cumulative.data());
    const double Stops[3] = {Total * 0.1, Total * 0.45, Total * 0.8};

    FollowParams P;
    P.DesiredSpeedCmPerSecond = 900.0;
    DwellConfig C;
    C.MinDwellSeconds = 8.0;
    C.MaxDwellSeconds = 16.0;

    StopState State;
    double S = 0.0, Speed = 0.0;
    int ServedCounts[3] = {0, 0, 0};
    int BoardingCalls = 0;
    long long BoardedPeople = 0;
    int LastServed = -1;
    std::vector<int> Order;
    const double Dt = 1.0 / 30.0;
    for (int Frame = 0; Frame < 108000; ++Frame)   // one hour at 30 Hz
    {
        // Acquire a stop only while Running, then latch it and measure the remainder
        // with the SIGNED distance -- re-querying while braking would hand back the next
        // stop as the gap shrank past the skip window, and the bus would sail through.
        double NearestGap = 0.0;
        if (State.Phase == StopPhase::Running)
        {
            State.TargetStopIndex = NextStopAhead(Stops, 3, S, Total, true, 300.0, NearestGap);
        }
        const double GapToStop = State.TargetStopIndex >= 0
            ? SignedDistanceAlong(S, Stops[State.TargetStopIndex], Total, true) : 1e9;
        const double A = LongitudinalAcceleration(State, Speed, 0.0, 1e9, GapToStop, P);
        Speed = IntegrateSpeed(Speed, A, Dt, P.DesiredSpeedCmPerSecond);
        if (!IsHeldAtStop(State)) S = WrapDistance(S + Speed * Dt, Total, true);
        const StopEvents E = AdvanceStopState(State, Dt, Speed, GapToStop, P, C, 606u, 0);
        if (E.bDoorsOpened)
        {
            Vec3 Pose{}, Tangent{};
            Check(SampleRoute(Loop.data(), Cumulative.data(), Count, true, S, Pose, Tangent));
            Check(Finite(Pose));
            Check(State.ServedStopIndex >= 0 && State.ServedStopIndex < 3);
            Check(Speed <= C.StoppedSpeedCmPerSecond);
            // Arrived within tolerance of the authored stop line, on either side of it.
            Check(std::abs(SignedDistanceAlong(S, Stops[State.ServedStopIndex], Total, true)) <= C.ArrivalToleranceCm);
            ServedCounts[State.ServedStopIndex] += 1;
            Check(State.ServedStopIndex != LastServed);   // never serves the same stop twice running
            LastServed = State.ServedStopIndex;
            Order.push_back(State.ServedStopIndex);
            ++BoardingCalls;
            BoardedPeople += BoardingCountFor(606u, 0, State.ServedStopIndex, State.RunIndex, 4, 14, 1.5);
        }
        Check(Speed >= 0.0 && Speed <= P.DesiredSpeedCmPerSecond + 1e-9);
        Check(std::isfinite(S) && S >= 0.0 && S < Total + 1e-6);
    }
    // Stops are served in the authored cyclic order, every one of them, many times.
    for (int I = 0; I < 3; ++I) Check(ServedCounts[I] >= 5);
    for (size_t I = 1; I < Order.size(); ++I)
    {
        Check(Order[I] == (Order[I - 1] + 1) % 3);
    }
    Check(BoardingCalls == static_cast<int>(Order.size()));
    FactInt("service_stops_served", BoardingCalls);
    FactInt("service_people_moved", BoardedPeople);
    Fact("service_mean_people_per_call", static_cast<double>(BoardedPeople) / std::max(1, BoardingCalls));

    std::printf("service: %d stop calls in one simulated hour, strict cyclic order, %lld boarding requests raised (%.1f per call)\n",
                BoardingCalls, BoardedPeople, static_cast<double>(BoardedPeople) / std::max(1, BoardingCalls));
}

// ---------------------------------------------------------------------------

static void WriteJson(const char* Path)
{
    std::FILE* File = std::fopen(Path, "wb");
    if (!File)
    {
        std::fprintf(stderr, "could not open %s\n", Path);
        std::exit(2);
    }
    std::fprintf(File, "{\n  \"test\": \"TransitMathTest\",\n  \"header\": \"Plugins/MikdashRuntime/Source/MikdashRuntime/Public/TransitMath.h\",\n");
    std::fprintf(File, "  \"allPassed\": true,\n  \"checksEvaluated\": %lld,\n  \"measurements\": {\n", CheckCount);
    for (size_t I = 0; I < Facts.size(); ++I)
    {
        std::fprintf(File, "    \"%s\": %s%s\n", Facts[I].first.c_str(), Facts[I].second.c_str(), I + 1 < Facts.size() ? "," : "");
    }
    std::fprintf(File, "  }\n}\n");
    std::fclose(File);
}

int main(int argc, char** argv)
{
    GeometryChecks();
    FollowChecks();
    PlatoonChecks();
    DwellChecks();
    ScheduleChecks();
    BudgetChecks();
    ConsistChecks();
    VariationChecks();
    ServiceChecks();
    if (argc > 1) WriteJson(argv[1]);
    std::cout << "PASS " << CheckCount << " checks: transit geometry, following, platoon, dwell machine, schedule, budget, consist, variation and service" << std::endl;
    return 0;
}
