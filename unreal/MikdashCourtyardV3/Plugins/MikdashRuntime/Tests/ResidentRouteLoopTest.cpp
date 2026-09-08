#include "ResidentRouteLoop.h"
#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>

using namespace MikdashRoute;

static bool Near(double A, double B, double Tolerance = 1e-6) { return std::abs(A - B) <= Tolerance; }

// The authored loop shipped by Scripts/release_dove_people_v2.spec.json for resident 04.
static std::vector<Point2> AuthoredLoop()
{
    return {{5240, 1330}, {6300, 1000}, {6900, 1000}, {6700, 3200}, {5400, 3000}};
}
static std::vector<double> AuthoredPauses() { return {4, 3, 5, 4, 3}; }
static std::vector<std::string> AuthoredLabels()
{
    return {"Rejoin the visiting group and wait", "Walk toward the outer eastern gate", "Pause at the court's edge and look at the gate",
        "Walk along the northern side of the court", "Turn back toward the visiting group"};
}

static void LoopValidation()
{
    std::string Reason;
    assert(ValidateLoop(AuthoredLoop(), AuthoredPauses(), AuthoredLabels(), &Reason) && Reason.empty());
    const double Length = LoopLengthCm(AuthoredLoop());
    assert(Length > 6000 && Length < 12000);
    std::cout << "authored loop length cm=" << Length << '\n';
    // Region rules: the y=0 corridor, the inner court, and the outer wall margin are refused.
    std::vector<Point2> Corridor = AuthoredLoop(); Corridor[1] = {6300, 400};
    assert(!ValidateLoop(Corridor, AuthoredPauses(), AuthoredLabels(), &Reason) && Reason.find("region") != std::string::npos);
    std::vector<Point2> Inner = AuthoredLoop(); Inner[3] = {1200, 3200};
    assert(!ValidateLoop(Inner, AuthoredPauses(), AuthoredLabels()));
    std::vector<Point2> Wall = AuthoredLoop(); Wall[2] = {7400, 1000};
    assert(!ValidateLoop(Wall, AuthoredPauses(), AuthoredLabels()));
    // Count, pause and label rules.
    std::vector<Point2> Three = {{5240, 1330}, {6300, 1000}, {6900, 2500}};
    assert(!ValidateLoop(Three, {3, 3, 3}, {"a", "b", "c"}, &Reason) && Reason.find("4 to 6") != std::string::npos);
    std::vector<double> LongPause = AuthoredPauses(); LongPause[0] = 9;
    assert(!ValidateLoop(AuthoredLoop(), LongPause, AuthoredLabels(), &Reason) && Reason.find("pause") != std::string::npos);
    std::vector<std::string> BadLabel = AuthoredLabels(); BadLabel[1] = "";
    assert(!ValidateLoop(AuthoredLoop(), AuthoredPauses(), BadLabel));
    std::vector<Point2> Short = {{5240, 1330}, {5300, 1330}, {5400, 1400}, {5300, 1500}};
    assert(!ValidateLoop(Short, {3, 3, 3, 3}, {"a", "b", "c", "d"}, &Reason));
    std::vector<Point2> Huge = {{1600, 1000}, {6900, 1000}, {6900, 5900}, {1600, 5900}};
    assert(!ValidateLoop(Huge, {3, 3, 3, 3}, {"a", "b", "c", "d"}, &Reason) && Reason.find("length") != std::string::npos);
    std::vector<Point2> NaN = AuthoredLoop(); NaN[0].X = std::numeric_limits<double>::quiet_NaN();
    assert(!ValidateLoop(NaN, AuthoredPauses(), AuthoredLabels()));
}

static void CorridorAndLegs()
{
    const std::vector<Point2> Loop = AuthoredLoop();
    // Along a leg, on it, offset within the margin, and offset beyond it.
    assert(SegmentWithinCorridor({5240, 1330}, {6300, 1000}, Loop));
    assert(SegmentWithinCorridor({5240, 1330 + 140}, {6300, 1000 + 140}, Loop));
    assert(!SegmentWithinCorridor({5240, 1330 + 200}, {6300, 1000 + 200}, Loop));
    // A 100 cm sidestep from a point on the loop stays inside the 150 cm corridor.
    BlockRecovery Recovery;
    const Point2 Side = Recovery.SidestepTarget({5800, 1156}, {6300, 1000});
    assert(Near(Distance(Side, {5800, 1156}), 100));
    assert(SegmentWithinCorridor({5800, 1156}, Side, Loop) && SegmentWithinCorridor(Side, {6300, 1000}, Loop));
    // A shortcut across the loop interior leaves the corridor.
    assert(!SegmentWithinCorridor({6300, 1000}, {5400, 3000}, Loop));
    assert(!SegmentWithinCorridor({6300, 1000}, {6900, 1000}, {}, 150));
    assert(Near(DistanceToSegment({0, 5}, {-10, 0}, {10, 0}), 5) && Near(DistanceToSegment({20, 0}, {-10, 0}, {10, 0}), 10));
    // Goal j walks point j%N -> (j+1)%N; three laps of five points end back at the start.
    const std::size_t N = Loop.size();
    Leg First = LegForGoal(0, N); assert(First.From == 0 && First.To == 1);
    Leg Last = LegForGoal(N - 1, N); assert(Last.From == N - 1 && Last.To == 0);
    Leg Wrap = LegForGoal(N, N); assert(Wrap.From == 0 && Wrap.To == 1);
    assert(LegForGoal(3 * N - 1, N).To == 0);
    assert(LegForGoal(2, 0).From == 0 && LegForGoal(2, 0).To == 0);
}

static void BlockRecoveryChecks()
{
    BlockRecovery R;
    // Walking normally at 180 cm/s never triggers.
    for (int I = 0; I < 600; ++I) assert(!R.Advance(1.0 / 60, 3.0, true));
    // Held still: triggers once after two seconds, then again after another two.
    int Triggers = 0, FirstTick = -1;
    for (int I = 0; I < 250; ++I) if (R.Advance(1.0 / 60, 0.0, true)) { ++Triggers; if (FirstTick < 0) FirstTick = I; }
    assert(Triggers == 2 && FirstTick >= 118 && FirstTick <= 122 && R.AttemptCount() == 2);
    // Progress resets the timer; creeping under 15 cm/s still counts as blocked.
    R.Reset();
    for (int I = 0; I < 90; ++I) assert(!R.Advance(1.0 / 60, 0.0, true));
    assert(!R.Advance(1.0 / 60, 5.0, true) && Near(R.StillTime(), 0));
    for (int I = 0; I < 119; ++I) assert(!R.Advance(1.0 / 60, 0.2, true));
    assert(R.Advance(1.0 / 60, 0.2, true) || R.Advance(1.0 / 60, 0.2, true));
    // No target, bad delta or negative distance never triggers and clears the timer.
    R.Reset();
    for (int I = 0; I < 200; ++I) assert(!R.Advance(1.0 / 60, 0.0, false));
    for (int I = 0; I < 200; ++I) assert(!R.Advance(std::numeric_limits<double>::quiet_NaN(), 0.0, true));
    assert(!R.Advance(1.0 / 60, -1.0, true) && Near(R.StillTime(), 0));
    // A one-second hitch cannot fire on its own: delta is clamped to a quarter second.
    R.Reset(); assert(!R.Advance(5.0, 0.0, true) && Near(R.StillTime(), 0.25));
    // Sidestep alternates sides and is perpendicular to the blocked direction.
    R.Reset();
    const Point2 A = R.SidestepTarget({0, 0}, {100, 0}); const Point2 B = R.SidestepTarget({0, 0}, {100, 0});
    assert(Near(A.X, 0) && Near(A.Y, 100) && Near(B.X, 0) && Near(B.Y, -100));
    const Point2 Degenerate = R.SidestepTarget({7, 7}, {7, 7});
    assert(Near(Distance(Degenerate, {7, 7}), 100));
}

static void TurningChecks()
{
    assert(Near(YawTowardDegrees({0, 0}, {10, 0}), 0) && Near(YawTowardDegrees({0, 0}, {0, 10}), 90) && Near(YawTowardDegrees({0, 0}, {-10, 0}), 180));
    // 120 deg/s: a 90 degree turn completes in 0.75 s, monotonic, no overshoot.
    double Yaw = 0; int Ticks = 0;
    while (!Near(Yaw, 90) && Ticks < 1000) { const double Next = TurnToward(Yaw, 90, 1.0 / 60); assert(Next >= Yaw - 1e-9 && Next <= 90 + 1e-9); Yaw = Next; ++Ticks; }
    assert(Ticks >= 44 && Ticks <= 46);
    // Shortest way around the wrap.
    assert(TurnToward(170, -170, 1.0 / 60) > 170 || TurnToward(170, -170, 1.0 / 60) < -170);
    assert(Near(TurnToward(179, -179, 1.0), -179));
    assert(Near(TurnToward(45, 45, 0.1), 45));
    assert(Near(TurnToward(45, 90, 0), 45) && Near(TurnToward(45, std::numeric_limits<double>::quiet_NaN(), 0.1), 45));
    assert(Near(WrapDegrees(540), 180) || Near(WrapDegrees(540), -180));
    assert(Near(WrapDegrees(-190), 170));
}

int main()
{
    LoopValidation();
    CorridorAndLegs();
    BlockRecoveryChecks();
    TurningChecks();
    std::cout << "Resident route loop: region/length validation, corridor, leg mapping, two-second block recovery with alternating sidestep, and pause turning checks passed\n";
}
