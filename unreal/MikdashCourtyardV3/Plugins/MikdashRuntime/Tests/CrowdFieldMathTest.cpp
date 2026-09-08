#include "CrowdFieldMath.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <iostream>
#include <limits>
#include <vector>

using namespace MikdashCrowd;

static bool Near(double A, double B, double Tolerance = 1e-9) { return std::abs(A - B) <= Tolerance; }

// A convex court and a protected block inside it, in the shape the real zones take.
static const Vec2 Court[4] = {{-7000, -7000}, {7000, -7000}, {7000, 7000}, {-7000, 7000}};
static const Vec2 Sanctuary[4] = {{-6800, -1500}, {-2000, -1500}, {-2000, 1500}, {-6800, 1500}};
static const int ProtectedStarts[1] = {0};
static const int ProtectedCounts[1] = {4};

// A deliberately non-convex zone: an L, to prove the containment test is a real ray cast
// and not a bounding-box check.
static const Vec2 LShape[6] = {{0, 0}, {400, 0}, {400, 100}, {100, 100}, {100, 400}, {0, 400}};

static void ContainmentChecks()
{
    assert(PointInPolygon(Court, 4, Vec2{0, 0}));
    assert(!PointInPolygon(Court, 4, Vec2{7001, 0}));
    assert(!PointInPolygon(Court, 4, Vec2{0, -8000}));
    // Degenerate and hostile input contains nothing and does not crash.
    assert(!PointInPolygon(nullptr, 4, Vec2{0, 0}));
    assert(!PointInPolygon(Court, 2, Vec2{0, 0}));
    assert(!PointInPolygon(Court, 4, Vec2{std::numeric_limits<double>::quiet_NaN(), 0}));

    // L-shape: inside both arms, outside the notch that a bounding box would wrongly accept.
    assert(PointInPolygon(LShape, 6, Vec2{50, 50}));
    assert(PointInPolygon(LShape, 6, Vec2{300, 50}));
    assert(PointInPolygon(LShape, 6, Vec2{50, 300}));
    assert(!PointInPolygon(LShape, 6, Vec2{300, 300}));   // the notch
    assert(!PointInPolygon(LShape, 6, Vec2{500, 500}));

    // Margins keep a figure off the boundary.
    assert(PointInPolygonWithMargin(Court, 4, Vec2{0, 0}, 200.0));
    assert(!PointInPolygonWithMargin(Court, 4, Vec2{6950, 0}, 200.0));
    assert(PointInPolygonWithMargin(Court, 4, Vec2{6950, 0}, 0.0));
    assert(Near(DistanceToPolygonEdge(Court, 4, Vec2{6950, 0}), 50.0, 1e-6));
    assert(Near(DistanceToPolygonEdge(Court, 4, Vec2{7100, 0}), 100.0, 1e-6));   // outside, still positive

    // Protected polygons reject both the interior and the keep-out skirt around it.
    assert(PointInAnyProtected(Sanctuary, ProtectedStarts, ProtectedCounts, 1, Vec2{-4000, 0}, 150.0));
    assert(PointInAnyProtected(Sanctuary, ProtectedStarts, ProtectedCounts, 1, Vec2{-1900, 0}, 150.0));   // 100 cm outside, inside the skirt
    assert(!PointInAnyProtected(Sanctuary, ProtectedStarts, ProtectedCounts, 1, Vec2{-1800, 0}, 150.0));  // 200 cm clear
    assert(!PointInAnyProtected(nullptr, nullptr, nullptr, 0, Vec2{-4000, 0}, 150.0));

    // Area and bounds.
    assert(Near(PolygonArea(Court, 4), 14000.0 * 14000.0, 1e-3));
    assert(Near(PolygonArea(LShape, 6), 400.0 * 100.0 + 100.0 * 300.0, 1e-6));
    Vec2 Min{}, Max{};
    assert(PolygonBounds(LShape, 6, Min, Max) && Near(Min.X, 0) && Near(Max.X, 400) && Near(Max.Y, 400));
    assert(!PolygonBounds(LShape, 2, Min, Max));
    std::printf("containment: L-shape notch rejected, %.0f cm skirt honoured, court area %.0f cm2\n",
                150.0, PolygonArea(Court, 4));
}

static void SeedingChecks()
{
    // 4000 seeds land inside the court, clear of the sanctuary and its skirt, and are
    // reproducible: the same instance index seeds to the same point every run.
    int Placed = 0;
    Vec2 First{};
    for (uint32_t I = 0; I < 4000; ++I)
    {
        Vec2 P{};
        if (!SeedPointInZone(Court, 4, Sanctuary, ProtectedStarts, ProtectedCounts, 1, 150.0, 100.0, 20260907u, I, 24, P)) continue;
        assert(PointInPolygonWithMargin(Court, 4, P, 100.0));
        assert(!PointInAnyProtected(Sanctuary, ProtectedStarts, ProtectedCounts, 1, P, 150.0));
        if (I == 7) First = P;
        ++Placed;
    }
    assert(Placed > 3900);   // rejection sampling wastes a few draws on the sanctuary block
    Vec2 Again{};
    assert(SeedPointInZone(Court, 4, Sanctuary, ProtectedStarts, ProtectedCounts, 1, 150.0, 100.0, 20260907u, 7u, 24, Again));
    assert(Near(Again.X, First.X) && Near(Again.Y, First.Y));
    // A different seed gives a different crowd.
    Vec2 Other{};
    assert(SeedPointInZone(Court, 4, Sanctuary, ProtectedStarts, ProtectedCounts, 1, 150.0, 100.0, 99u, 7u, 24, Other));
    assert(!Near(Other.X, First.X, 1.0) || !Near(Other.Y, First.Y, 1.0));
    // A zone entirely swallowed by a protected polygon places nobody rather than placing
    // a figure inside the sanctuary.
    const Vec2 Inside[4] = {{-6000, -1000}, {-3000, -1000}, {-3000, 1000}, {-6000, 1000}};
    Vec2 Impossible{};
    assert(!SeedPointInZone(Inside, 4, Sanctuary, ProtectedStarts, ProtectedCounts, 1, 150.0, 50.0, 1u, 0u, 64, Impossible));
    std::printf("seeding: %d/4000 placed, deterministic, enclosed zone refused\n", Placed);
}

static void FlowChecks()
{
    FlowZone Zone;
    Zone.Goal = Vec2{5000, 0};
    Zone.DirectionDegrees = 0.0;
    Zone.GoalWeight = 1.0;
    Zone.MeanderDegrees = 0.0;
    // Pure convergence: from due south of the goal the heading points north-east-ish at it.
    const Vec2 D = SampleFlow(Zone, Vec2{0, 0}, 0.0, 1u, 0u);
    assert(Near(Length(D), 1.0, 1e-9));
    assert(Near(YawDegrees(D), 0.0, 1e-6));
    const Vec2 D2 = SampleFlow(Zone, Vec2{5000, -1000}, 0.0, 1u, 0u);
    assert(Near(YawDegrees(D2), 90.0, 1e-6));
    // Pure streaming ignores the goal.
    Zone.GoalWeight = 0.0;
    Zone.DirectionDegrees = 135.0;
    assert(Near(YawDegrees(SampleFlow(Zone, Vec2{5000, -1000}, 0.0, 1u, 0u)), 135.0, 1e-6));
    // Standing on the goal must still give a unit heading, not a zero vector.
    Zone.GoalWeight = 1.0;
    Zone.DirectionDegrees = 20.0;
    const Vec2 OnGoal = SampleFlow(Zone, Zone.Goal, 0.0, 1u, 0u);
    assert(Near(Length(OnGoal), 1.0, 1e-9) && Near(YawDegrees(OnGoal), 20.0, 1e-6));
    // Meander stays inside its stated amplitude and differs between instances.
    Zone.MeanderDegrees = 12.0;
    Zone.GoalWeight = 0.0;
    double Extreme = 0.0;
    bool Differ = false;
    for (int I = 0; I < 400; ++I)
    {
        const double T = I * 0.25;
        const double A = WrapDegrees(YawDegrees(SampleFlow(Zone, Vec2{0, 0}, T, 5u, 1u)) - 20.0);
        const double B = WrapDegrees(YawDegrees(SampleFlow(Zone, Vec2{0, 0}, T, 5u, 2u)) - 20.0);
        Extreme = std::max(Extreme, std::abs(A));
        if (std::abs(A - B) > 1.0) Differ = true;
    }
    assert(Extreme <= 12.0001 && Extreme > 10.0 && Differ);
    // Turn-rate limiting: 90 deg/s cannot cover 170 deg in a tenth of a second.
    assert(Near(SteerHeading(0.0, 170.0, 0.1, 90.0), 9.0, 1e-9));
    // An exact half turn is ambiguous; it must still be limited, and to one of the two sides.
    assert(Near(std::abs(SteerHeading(0.0, 180.0, 0.1, 90.0)), 9.0, 1e-9));
    assert(Near(SteerHeading(0.0, 5.0, 1.0, 90.0), 5.0, 1e-9));       // small turns complete
    assert(Near(SteerHeading(170.0, -170.0, 1.0, 90.0), -170.0, 1e-9)); // wraps the short way
    assert(Near(SteerHeading(30.0, 100.0, -1.0, 90.0), 30.0));         // bad dt does nothing
    std::printf("flow: convergence, streaming, on-goal unit heading, meander <= %.2f deg, turn limit\n", Extreme);
}

static void SpeedAndPhaseChecks()
{
    // Every instance walks between 60 and 110 cm/s and the spread actually fills the band.
    double Slowest = 1e9, Fastest = -1e9, Total = 0.0;
    for (uint32_t I = 0; I < 10000; ++I)
    {
        const double S = WalkSpeedFor(4242u, I);
        assert(S >= MinWalkSpeedCmPerSecond - 1e-9 && S <= MaxWalkSpeedCmPerSecond + 1e-9);
        Slowest = std::min(Slowest, S);
        Fastest = std::max(Fastest, S);
        Total += S;
    }
    assert(Slowest < 61.0 && Fastest > 109.0 && std::abs(Total / 10000.0 - 85.0) < 1.0);

    // Standing ratio is honoured to within sampling noise over 10 000 instances.
    int Standing = 0;
    for (uint32_t I = 0; I < 10000; ++I) Standing += IsStanding(4242u, I, 0.30) ? 1 : 0;
    assert(std::abs(Standing - 3000) < 200);
    for (uint32_t I = 0; I < 100; ++I)
    {
        assert(!IsStanding(4242u, I, 0.0));
        assert(IsStanding(4242u, I, 1.0));
    }

    // Phase is driven by distance: one full gait cycle per stride length, at any speed.
    double Phase = 0.0;
    const double Speed = 78.0;   // exactly one stride per second
    for (int I = 0; I < 60; ++I) Phase = AdvancePhase(Phase, Speed, 1.0 / 60.0);
    assert(Near(Phase, 0.0, 1e-9) || Near(Phase, 1.0, 1e-9));
    Phase = 0.0;
    for (int I = 0; I < 240; ++I) Phase = AdvancePhase(Phase, 39.0, 1.0 / 240.0);
    assert(Near(Phase, 0.5, 1e-9));   // half speed, half a cycle in one second
    assert(AdvancePhase(0.4, 100.0, 0.0) >= 0.0 && Near(AdvancePhase(0.4, 100.0, 0.0), 0.4));
    assert(Near(AdvancePhase(std::numeric_limits<double>::quiet_NaN(), 100.0, 0.1), AdvancePhase(0.0, 100.0, 0.1)));
    // A hitch cannot advance more than a quarter second of gait.
    assert(Near(AdvancePhase(0.0, 78.0, 10.0), AdvancePhase(0.0, 78.0, 0.25)));
    // Standing figures keep a slow idle phase rather than freezing solid.
    double Idle = 0.0;
    for (int I = 0; I < 240; ++I) Idle = AdvancePhase(Idle, 0.0, 1.0 / 60.0, true);
    assert(Idle > 0.0 && Idle < 1.0);

    // Bob: two rises per cycle, never negative, peaks at the stated amplitude.
    double PeakBob = 0.0, LowBob = 1e9;
    int Rises = 0;
    double Previous = BobHeightCm(0.0, 4.0);
    bool bGoingUp = false;
    for (int I = 1; I <= 400; ++I)
    {
        const double B = BobHeightCm(I / 400.0, 4.0);
        PeakBob = std::max(PeakBob, B);
        LowBob = std::min(LowBob, B);
        if (B > Previous && !bGoingUp) { bGoingUp = true; ++Rises; }
        if (B < Previous) bGoingUp = false;
        Previous = B;
    }
    assert(Rises == 2 && PeakBob > 3.99 && PeakBob <= 4.0 + 1e-9 && LowBob >= 0.0);
    assert(Near(LeanDegrees(0.25, 6.0), 6.0, 1e-9) && Near(LeanDegrees(0.75, 6.0), -6.0, 1e-9));
    assert(Near(BobHeightCm(std::numeric_limits<double>::infinity(), 4.0), 0.0));
    std::printf("speed/phase: %.1f..%.1f cm/s (mean %.1f), %d/10000 standing at 0.30, %d bob rises per cycle\n",
                Slowest, Fastest, Total / 10000.0, Standing, Rises);
}

static void BudgetChecks()
{
    // 10 000 instances at 500 a frame: every instance visited exactly once per 20 frames,
    // never more than 500 in one frame.
    const int Count = 10000, Budget = 500;
    std::vector<int> Visits(static_cast<size_t>(Count), 0);
    int Cursor = 0;
    assert(FramesPerSweep(Count, Budget) == 20);
    for (int Frame = 0; Frame < 20; ++Frame)
    {
        const UpdateWindow W = NextUpdateWindow(Cursor, Count, Budget);
        assert(W.Total() == Budget);
        for (int I = 0; I < W.FirstCount; ++I) ++Visits[static_cast<size_t>(W.FirstStart + I)];
        for (int I = 0; I < W.SecondCount; ++I) ++Visits[static_cast<size_t>(W.SecondStart + I)];
        Cursor = W.NextCursor;
    }
    for (int I = 0; I < Count; ++I) assert(Visits[static_cast<size_t>(I)] == 1);
    assert(Cursor == 0);

    // A budget that does not divide the count wraps, and still visits everyone exactly
    // once per sweep over the whole cycle.
    const int Odd = 997, OddBudget = 300;
    std::vector<int> OddVisits(static_cast<size_t>(Odd), 0);
    Cursor = 0;
    int Wraps = 0;
    for (int Frame = 0; Frame < 4 * 997 / 300 + 4; ++Frame)
    {
        const UpdateWindow W = NextUpdateWindow(Cursor, Odd, OddBudget);
        assert(W.Total() == OddBudget);
        if (W.Wrapped()) ++Wraps;
        for (int I = 0; I < W.FirstCount; ++I) ++OddVisits[static_cast<size_t>(W.FirstStart + I)];
        for (int I = 0; I < W.SecondCount; ++I) ++OddVisits[static_cast<size_t>(W.SecondStart + I)];
        Cursor = W.NextCursor;
    }
    assert(Wraps > 0);
    int MinVisits = 1 << 30, MaxVisits = 0;
    for (int I = 0; I < Odd; ++I)
    {
        MinVisits = std::min(MinVisits, OddVisits[static_cast<size_t>(I)]);
        MaxVisits = std::max(MaxVisits, OddVisits[static_cast<size_t>(I)]);
    }
    assert(MaxVisits - MinVisits <= 1);   // round robin is fair to within one sweep

    // A budget larger than the crowd is clamped to the crowd.
    const UpdateWindow Small = NextUpdateWindow(0, 12, 500);
    assert(Small.FirstCount == 12 && !Small.Wrapped() && Small.NextCursor == 0);
    // Hostile input is empty, not undefined.
    assert(NextUpdateWindow(0, 0, 500).Total() == 0);
    assert(NextUpdateWindow(0, 100, 0).Total() == 0);
    assert(NextUpdateWindow(-5, 100, 10).FirstStart == 0);
    assert(NextUpdateWindow(1000, 100, 10).FirstStart == 0);
    assert(FramesPerSweep(0, 500) == 0 && FramesPerSweep(1, 500) == 1 && FramesPerSweep(501, 500) == 2);

    // Catch-up: an agent visited once per 20 frames must integrate 20 frames of time, or
    // the crowd crawls at a twentieth of its stated speed.
    const double Dt = 1.0 / 60.0;
    assert(Near(CatchUpSeconds(Dt, Count, Budget), 20.0 * Dt, 1e-12));
    assert(Near(CatchUpSeconds(Dt, 100, 500), Dt, 1e-12));      // one sweep per frame
    assert(Near(CatchUpSeconds(0.4, Count, Budget), 0.5));       // clamped, no teleport
    assert(Near(CatchUpSeconds(-1.0, Count, Budget), 0.0));
    std::printf("budget: 10000/500 -> 20 frames, exactly one visit each, catch-up %.4f s, clamp 0.5 s\n",
                CatchUpSeconds(Dt, Count, Budget));
}

static void DistancePolicyChecks()
{
    assert(ClassifyByDistance(1000.0, 12000.0, 30000.0) == InstanceWork::Simulate);
    assert(ClassifyByDistance(12000.0, 12000.0, 30000.0) == InstanceWork::Freeze);
    assert(ClassifyByDistance(29999.0, 12000.0, 30000.0) == InstanceWork::Freeze);
    assert(ClassifyByDistance(30000.0, 12000.0, 30000.0) == InstanceWork::Cull);
    // Misconfiguration simulates rather than silently freezing the whole crowd.
    assert(ClassifyByDistance(50000.0, 30000.0, 12000.0) == InstanceWork::Simulate);
    assert(ClassifyByDistance(50000.0, 0.0, 30000.0) == InstanceWork::Simulate);
    assert(ClassifyByDistance(std::numeric_limits<double>::quiet_NaN(), 12000.0, 30000.0) == InstanceWork::Simulate);
    assert(Near(DistanceSquared2D(Vec2{0, 0}, Vec2{300, 400}), 250000.0, 1e-6));
    std::printf("distance: simulate < 12000 <= freeze < 30000 <= cull, bad config simulates\n");
}

static void ApportionAndPoseChecks()
{
    // Four zones, unequal weights: the parts sum to exactly the crowd size.
    const double Weights[4] = {5.0, 2.0, 2.5, 0.5};
    int Counts[4] = {0, 0, 0, 0};
    assert(ApportionCounts(Weights, 4, 10000, Counts) == 10000);
    assert(Counts[0] + Counts[1] + Counts[2] + Counts[3] == 10000);
    assert(Counts[0] == 5000 && Counts[1] == 2000 && Counts[2] == 2500 && Counts[3] == 500);
    // Awkward totals still sum exactly.
    for (int Total = 1; Total <= 60; ++Total)
    {
        const double Odd[3] = {1.0, 1.0, 1.0};
        int Three[3] = {0, 0, 0};
        assert(ApportionCounts(Odd, 3, Total, Three) == Total);
        assert(Three[0] + Three[1] + Three[2] == Total);
    }
    // A dead zone (zero or negative weight) receives nobody.
    const double WithDead[3] = {1.0, 0.0, -4.0};
    int Dead[3] = {9, 9, 9};
    assert(ApportionCounts(WithDead, 3, 777, Dead) == 777 && Dead[0] == 777 && Dead[1] == 0 && Dead[2] == 0);
    const double AllDead[2] = {0.0, 0.0};
    int None[2] = {9, 9};
    assert(ApportionCounts(AllDead, 2, 100, None) == 0 && None[0] == 0 && None[1] == 0);
    assert(ApportionCounts(nullptr, 2, 100, None) == 0);

    // Pose blocking: every instance has a pose, blocks are contiguous and their starts
    // agree with the per-instance mapping. This is what lets the actor push a batched
    // transform update instead of 500 individual ones.
    const int Total = 10000, Poses = 6;
    std::vector<int> PerPose(static_cast<size_t>(Poses), 0);
    int PreviousPose = 0;
    for (int I = 0; I < Total; ++I)
    {
        const int P = PoseIndexForInstance(I, Total, Poses);
        assert(P >= 0 && P < Poses);
        assert(P == PreviousPose || P == PreviousPose + 1);   // blocks, never interleaved
        PreviousPose = P;
        ++PerPose[static_cast<size_t>(P)];
    }
    for (int P = 0; P < Poses; ++P)
    {
        assert(PerPose[static_cast<size_t>(P)] > Total / Poses - 2 && PerPose[static_cast<size_t>(P)] < Total / Poses + 2);
        const int Start = PoseBlockStart(P, Total, Poses);
        assert(PoseIndexForInstance(Start, Total, Poses) == P);
        if (Start > 0) assert(PoseIndexForInstance(Start - 1, Total, Poses) == P - 1);
    }
    assert(PoseBlockStart(0, Total, Poses) == 0 && PoseBlockStart(Poses, Total, Poses) == Total);
    assert(PoseIndexForInstance(0, 3, 6) == 0 && PoseIndexForInstance(2, 3, 6) < 6);
    assert(PoseIndexForInstance(5, 10, 1) == 0 && PoseIndexForInstance(-1, 10, 6) == 0);

    // Garment tints spread across the palette; height stays in an adult band.
    std::vector<int> Palette(5, 0);
    for (uint32_t I = 0; I < 5000; ++I)
    {
        const int G = GarmentIndex(11u, I, 5);
        assert(G >= 0 && G < 5);
        ++Palette[static_cast<size_t>(G)];
        const double H = HeightScaleFor(11u, I);
        assert(H >= 0.92 - 1e-9 && H <= 1.08 + 1e-9);
    }
    for (int I = 0; I < 5; ++I) assert(Palette[static_cast<size_t>(I)] > 800);
    assert(GarmentIndex(11u, 3u, 1) == 0 && GarmentIndex(11u, 3u, 0) == 0);
    std::printf("apportion: 5000/2000/2500/500 of 10000, dead zones empty; 6 pose blocks contiguous\n");
}

static void StepChecks()
{
    // A streaming zone: walk east across the court, re-seed at the west edge.
    FlowZone Zone;
    Zone.Goal = Vec2{12000, 0};   // beyond the east edge, so the stream crosses and re-seeds
    Zone.DirectionDegrees = 0.0;
    Zone.GoalWeight = 0.4;
    Zone.MeanderDegrees = 8.0;
    const Vec2 Reseed{-6500, 4000};   // west edge, clear of the sanctuary block

    AgentState Agent;
    Agent.Position = Vec2{-6000, 200};
    Agent.HeadingDegrees = 0.0;
    Agent.SpeedCmPerSecond = 100.0;
    Agent.Phase = 0.0;

    int Reseeds = 0;
    double Travelled = 0.0;
    for (int I = 0; I < 20000; ++I)
    {
        const Vec2 Before = Agent.Position;
        Step(Agent, Zone, Court, 4, Sanctuary, ProtectedStarts, ProtectedCounts, 1, 150.0, Reseed, 1.0 / 60.0, I / 60.0, 777u, 5u);
        // The invariant that matters: never inside the sanctuary, never outside the court.
        assert(PointInPolygon(Court, 4, Agent.Position));
        assert(!PointInAnyProtected(Sanctuary, ProtectedStarts, ProtectedCounts, 1, Agent.Position, 150.0));
        assert(Agent.Phase >= 0.0 && Agent.Phase < 1.0);
        if (Agent.bReseeded) ++Reseeds;
        else Travelled += Length(Agent.Position - Before);
    }
    assert(Reseeds >= 2);   // one crossing per ~140 s at 100 cm/s over ~13500 cm of court
    // Distance actually covered matches the speed to within the meander's cosine loss.
    const double Seconds = (20000 - Reseeds) / 60.0;
    assert(Travelled > 0.95 * 100.0 * Seconds && Travelled <= 100.0 * Seconds + 1e-6);

    // An agent aimed straight into the sanctuary is re-seeded, not admitted.
    AgentState Intruder;
    Intruder.Position = Vec2{-500, 0};
    Intruder.HeadingDegrees = 180.0;
    Intruder.SpeedCmPerSecond = 110.0;
    FlowZone Inward;
    Inward.Goal = Vec2{-5000, 0};
    Inward.GoalWeight = 1.0;
    Inward.DirectionDegrees = 180.0;
    Inward.MeanderDegrees = 0.0;
    bool bBounced = false;
    for (int I = 0; I < 2000 && !bBounced; ++I)
    {
        Step(Intruder, Inward, Court, 4, Sanctuary, ProtectedStarts, ProtectedCounts, 1, 150.0, Reseed, 1.0 / 60.0, I / 60.0, 3u, 1u);
        assert(!PointInAnyProtected(Sanctuary, ProtectedStarts, ProtectedCounts, 1, Intruder.Position, 150.0));
        bBounced = Intruder.bReseeded;
    }
    assert(bBounced);

    // A mis-authored re-seed point INSIDE the sanctuary must never be used: the figure
    // turns round where it stands instead of being teleported into the holy place.
    const Vec2 BadReseed{-5000, 0};   // inside the protected block
    assert(PointInAnyProtected(Sanctuary, ProtectedStarts, ProtectedCounts, 1, BadReseed, 150.0));
    AgentState Stubborn;
    Stubborn.Position = Vec2{-2000 + 150 + 5, 0};   // just clear of the 150 cm skirt, walking at it
    Stubborn.HeadingDegrees = 180.0;
    Stubborn.SpeedCmPerSecond = 110.0;
    bool bTurned = false;
    for (int I = 0; I < 2000; ++I)
    {
        const Vec2 Before = Stubborn.Position;
        Step(Stubborn, Inward, Court, 4, Sanctuary, ProtectedStarts, ProtectedCounts, 1, 150.0, BadReseed, 1.0 / 60.0, I / 60.0, 3u, 1u);
        assert(!PointInAnyProtected(Sanctuary, ProtectedStarts, ProtectedCounts, 1, Stubborn.Position, 150.0));
        if (Stubborn.bReseeded)
        {
            assert(Near(Stubborn.Position.X, Before.X) && Near(Stubborn.Position.Y, Before.Y));
            bTurned = true;
        }
    }
    assert(bTurned);

    // A standing figure never translates but its phase keeps moving.
    AgentState Stander;
    Stander.Position = Vec2{3000, 3000};
    Stander.bStanding = true;
    Stander.SpeedCmPerSecond = 0.0;
    for (int I = 0; I < 600; ++I)
    {
        Step(Stander, Zone, Court, 4, Sanctuary, ProtectedStarts, ProtectedCounts, 1, 150.0, Reseed, 1.0 / 60.0, I / 60.0, 9u, 2u);
    }
    assert(Near(Stander.Position.X, 3000.0) && Near(Stander.Position.Y, 3000.0));
    assert(Stander.Phase > 0.0 && !Stander.bReseeded);

    // A zero or negative step leaves the agent exactly where it was.
    AgentState Held = Agent;
    Step(Held, Zone, Court, 4, Sanctuary, ProtectedStarts, ProtectedCounts, 1, 150.0, Reseed, 0.0, 1.0, 1u, 1u);
    assert(Near(Held.Position.X, Agent.Position.X) && Near(Held.Position.Y, Agent.Position.Y));
    Step(Held, Zone, Court, 4, Sanctuary, ProtectedStarts, ProtectedCounts, 1, 150.0, Reseed, std::numeric_limits<double>::quiet_NaN(), 1.0, 1u, 1u);
    assert(Near(Held.Position.X, Agent.Position.X));

    // The whole crowd, one full sweep, under the round-robin catch-up step: nobody
    // escapes the court and nobody stands in the sanctuary.
    const int Crowd = 2000, Budget = 500;
    std::vector<AgentState> Agents(static_cast<size_t>(Crowd));
    int Seeded = 0;
    for (int I = 0; I < Crowd; ++I)
    {
        AgentState& A = Agents[static_cast<size_t>(I)];
        Vec2 P{};
        if (!SeedPointInZone(Court, 4, Sanctuary, ProtectedStarts, ProtectedCounts, 1, 150.0, 100.0, 20260907u, static_cast<uint32_t>(I), 24, P)) continue;
        A.Position = P;
        A.SpeedCmPerSecond = WalkSpeedFor(20260907u, static_cast<uint32_t>(I));
        A.bStanding = IsStanding(20260907u, static_cast<uint32_t>(I), 0.25);
        A.HeadingDegrees = HashRange(20260907u, static_cast<uint32_t>(I), 3u, -180.0, 180.0);
        A.Phase = HashUnit(20260907u, static_cast<uint32_t>(I), 5u);
        ++Seeded;
    }
    assert(Seeded > 1950);
    int Cursor = 0;
    const double CatchUp = CatchUpSeconds(1.0 / 60.0, Crowd, Budget);
    for (int Frame = 0; Frame < 400; ++Frame)
    {
        const UpdateWindow W = NextUpdateWindow(Cursor, Crowd, Budget);
        for (int K = 0; K < W.Total(); ++K)
        {
            const int Index = K < W.FirstCount ? W.FirstStart + K : W.SecondStart + (K - W.FirstCount);
            AgentState& A = Agents[static_cast<size_t>(Index)];
            if (Length(A.Position) < 1e-9 && A.SpeedCmPerSecond == 0.0) continue;   // never seeded
            Step(A, Zone, Court, 4, Sanctuary, ProtectedStarts, ProtectedCounts, 1, 150.0, Reseed, CatchUp, Frame / 60.0, 20260907u, static_cast<uint32_t>(Index));
            assert(PointInPolygon(Court, 4, A.Position));
            assert(!PointInAnyProtected(Sanctuary, ProtectedStarts, ProtectedCounts, 1, A.Position, 150.0));
        }
        Cursor = W.NextCursor;
    }
    std::printf("step: %d reseeds in 20000 frames, %.0f cm travelled, sanctuary never entered by %d agents over 400 frames\n",
                Reseeds, Travelled, Seeded);
}

int main()
{
    ContainmentChecks();
    SeedingChecks();
    FlowChecks();
    SpeedAndPhaseChecks();
    BudgetChecks();
    DistancePolicyChecks();
    ApportionAndPoseChecks();
    StepChecks();
    std::cout << "PASS: crowd field containment, seeding, flow, speed/phase, round-robin budget, distance policy, apportioning and stepping" << std::endl;
    return 0;
}
