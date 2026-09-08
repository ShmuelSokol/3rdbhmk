#define _CRT_SECURE_NO_WARNINGS

// Standalone test for TourMath.h. No Unreal, no engine headers.
//
//   cl /nologo /std:c++17 /EHsc /W4 /O2 /I<...>/Public TourMathTest.cpp
//   TourMathTest.exe [optional path for a JSON evidence file]
//
// Scripts/verify.py compiles this with /O2 and no /DNDEBUG, but a test that would
// evaporate under NDEBUG is a test nobody can trust, so nothing here uses <cassert>.
// Check() always evaluates its argument, always counts, and exits non-zero at the first
// failure with the file line.
//
// What is actually being proved, in the order the task demands it:
//   1. no boundary flicker  - a visitor parked exactly on an arrival boundary, and a
//      visitor parked exactly on the off-route corridor boundary, each produce exactly
//      ONE state transition no matter how long they loiter or how the floor jitters;
//   2. every stop reachable in order - walking the real route's own leg polylines
//      arrives at all 18 stops, in order, with the visited mask growing one bit at a
//      time and never losing one;
//   3. exact resume - a bookmark taken mid-tour, mid-camera-move, restored and then fed
//      the identical input stream reproduces the identical bookmark every single frame,
//      compared field for field with no tolerance.
// Plus route refusals, camera timing, progress monotonicity and the confidence labels.

#include "TourMath.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

using namespace MikdashTour;

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

static bool Near(double A, double B, double Tolerance = 1e-9) { return std::abs(A - B) <= Tolerance; }

// Collected evidence, written as JSON when an output path is given.
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

// ---------------------------------------------------------------------------
// The real route, mirroring SourceAssets/tour-review/tour-stops.json.
//
// These are the SAME numbers the JSON carries and the SAME numbers
// Scripts/release_tour.py places markers at. The JSON is the source of truth for the
// text; this table exists so the geometry is proved by a compiler and not only by a
// commandlet nobody runs twice. release_tour.py re-implements Route::Validate in Python
// over the JSON, so both sides are checked independently; if they ever disagree the
// disagreement is a bug, and the fix is to make this table match the JSON.
// ---------------------------------------------------------------------------

struct RealStop
{
    const char* Key;
    double Stand[3];
    double Look[3];
    double ArriveCm;
    double LeaveCm;
    // Up to three approach waypoints; a zeroed entry ends the list.
    double Waypoints[3][3];
    int WaypointCount;
};

static const RealStop RealStops[] = {
    // key, stand, look, arriveCm, leaveCm, waypoints, waypointCount
    {"mount-and-house", {12000.0, 0.0, 0.0}, {-4000.0, 0.0, 3000.0}, 800.0, 1100.0, {{0,0,0}, {0,0,0}, {0,0,0}}, 0},
    {"immersion", {11000.0, 900.0, 0.0}, {10000.0, 300.0, 300.0}, 500.0, 750.0, {{0,0,0}, {0,0,0}, {0,0,0}}, 0},
    {"soreg-and-cheil", {10000.0, 0.0, 0.0}, {8000.0, 0.0, 600.0}, 500.0, 750.0, {{0,0,0}, {0,0,0}, {0,0,0}}, 0},
    {"east-outer-gate", {7950.0, 0.0, 300.0}, {6000.0, 0.0, 900.0}, 450.0, 700.0, {{8900.0,0.0,150.0}, {0,0,0}, {0,0,0}}, 1},
    {"outer-court", {4974.0, 0.0, 300.0}, {0.0, 0.0, 1100.0}, 700.0, 1000.0, {{0,0,0}, {0,0,0}, {0,0,0}}, 0},
    {"north-gate-and-inner-wall", {0.0, -4500.0, 300.0}, {0.0, -2700.0, 900.0}, 700.0, 1000.0, {{3400.0,-3400.0,300.0}, {0,0,0}, {0,0,0}}, 1},
    {"east-inner-gate", {3500.0, 0.0, 400.0}, {2600.0, 0.0, 800.0}, 400.0, 650.0, {{3600.0,-3400.0,300.0}, {0,0,0}, {0,0,0}}, 1},
    {"ezras-yisroel", {2300.0, 0.0, 500.0}, {0.0, 0.0, 1100.0}, 450.0, 700.0, {{0,0,0}, {0,0,0}, {0,0,0}}, 0},
    {"duchan", {1450.0, 0.0, 625.0}, {2500.0, 0.0, 800.0}, 350.0, 550.0, {{0,0,0}, {0,0,0}, {0,0,0}}, 0},
    {"outer-altar", {1150.0, 1250.0, 625.0}, {0.0, 0.0, 1100.0}, 600.0, 900.0, {{0,0,0}, {0,0,0}, {0,0,0}}, 0},
    {"kiyor", {-1700.0, 1250.0, 625.0}, {-1950.0, 1500.0, 720.0}, 400.0, 650.0, {{0,0,0}, {0,0,0}, {0,0,0}}, 0},
    {"twelve-steps", {-1300.0, 0.0, 625.0}, {-2450.0, 0.0, 1700.0}, 450.0, 700.0, {{0,0,0}, {0,0,0}, {0,0,0}}, 0},
    {"ulam", {-3000.0, 0.0, 925.0}, {-3450.0, 0.0, 1700.0}, 400.0, 650.0, {{-1900.0,0.0,775.0}, {-2440.0,0.0,925.0}, {0,0,0}}, 2},
    {"heikhal", {-3900.0, 0.0, 925.0}, {-5600.0, 0.0, 1700.0}, 400.0, 650.0, {{-3450.0,0.0,925.0}, {0,0,0}, {0,0,0}}, 1},
    {"menorah", {-4950.0, 315.0, 925.0}, {-5330.0, 315.0, 1075.0}, 300.0, 500.0, {{0,0,0}, {0,0,0}, {0,0,0}}, 0},
    {"shulchan", {-4950.0, -350.0, 925.0}, {-5300.0, -350.0, 1075.0}, 300.0, 500.0, {{0,0,0}, {0,0,0}, {0,0,0}}, 0},
    {"golden-altar", {-4400.0, 0.0, 925.0}, {-4650.0, 0.0, 1010.0}, 300.0, 500.0, {{0,0,0}, {0,0,0}, {0,0,0}}, 0},
    {"paroches", {-5350.0, 0.0, 925.0}, {-5600.0, 0.0, 1075.0}, 350.0, 550.0, {{-5000.0,0.0,925.0}, {0,0,0}, {0,0,0}}, 1},
};
static const std::size_t RealStopCount = sizeof(RealStops) / sizeof(RealStops[0]);

static Point3 P(const double V[3]) { return Point3{V[0], V[1], V[2]}; }

static void BuildRealRoute(Route& Out)
{
    Out.Clear();
    for (std::size_t I = 0; I < RealStopCount; ++I)
    {
        const RealStop& Row = RealStops[I];
        Stop S;
        S.Key = Row.Key;
        S.Stand = P(Row.Stand);
        S.Look = P(Row.Look);
        S.ArriveRadiusCm = Row.ArriveCm;
        S.LeaveRadiusCm = Row.LeaveCm;
        S.WaypointCount = static_cast<std::size_t>(Row.WaypointCount);
        for (int W = 0; W < Row.WaypointCount; ++W) S.Waypoints[static_cast<std::size_t>(W)] = P(Row.Waypoints[W]);
        Check(Out.Add(S));
    }
}

/** A short synthetic route with clean round numbers, used where a hand-checkable
 * distance matters more than the real geometry. */
static void BuildSyntheticRoute(Route& Out)
{
    Out.Clear();
    const double Xs[4] = {0.0, 10000.0, 10000.0, 0.0};
    const double Ys[4] = {0.0, 0.0, 10000.0, 10000.0};
    const char* Keys[4] = {"a", "b", "c", "d"};
    for (int I = 0; I < 4; ++I)
    {
        Stop S;
        S.Key = Keys[I];
        S.Stand = Point3{Xs[I], Ys[I], 0.0};
        S.Look = Point3{Xs[I], Ys[I], 200.0};
        S.ArriveRadiusCm = 400.0;
        S.LeaveRadiusCm = 620.0;
        Check(Out.Add(S));
    }
}

// ---------------------------------------------------------------------------
// 1. Geometry primitives
// ---------------------------------------------------------------------------

static void GeometryChecks()
{
    Check(Near(Distance2D(Point3{0, 0, 500}, Point3{300, 400, -900}), 500.0));
    Check(Near(Distance3D(Point3{0, 0, 0}, Point3{0, 3, 4}), 5.0));

    // +Y is south, so north is -Y. Bearings are clockwise from north.
    Check(Near(BearingDegrees(Point3{0, 0, 0}, Point3{0, -100, 0}), 0.0, 1e-9));      // north
    Check(Near(BearingDegrees(Point3{0, 0, 0}, Point3{100, 0, 0}), 90.0, 1e-9));      // east
    Check(Near(BearingDegrees(Point3{0, 0, 0}, Point3{0, 100, 0}), 180.0, 1e-9));     // south
    Check(Near(BearingDegrees(Point3{0, 0, 0}, Point3{-100, 0, 0}), 270.0, 1e-9));    // west
    Check(BearingDegrees(Point3{5, 5, 5}, Point3{5, 5, 900}) == 0.0);                 // degenerate

    // Closest point on a segment clamps at both ends and interpolates Z.
    const Point3 A{0, 0, 0}, B{1000, 0, 500};
    Check(Same(ClosestPointOnSegment2D(A, B, Point3{-500, 300, 0}), A));
    Check(Same(ClosestPointOnSegment2D(A, B, Point3{5000, 300, 0}), B));
    const Point3 Mid = ClosestPointOnSegment2D(A, B, Point3{500, 900, 0});
    Check(Near(Mid.X, 500.0) && Near(Mid.Y, 0.0) && Near(Mid.Z, 250.0));
    Check(Near(DistanceToSegment2D(A, B, Point3{500, 900, 0}), 900.0));
    // A degenerate segment must not divide by zero.
    Check(Same(ClosestPointOnSegment2D(A, A, Point3{7, 7, 7}), A));

    Check(EaseInOut(0.0) == 0.0);
    Check(EaseInOut(1.0) == 1.0);
    Check(Near(EaseInOut(0.5), 0.5));
    Check(EaseInOut(-5.0) == 0.0 && EaseInOut(5.0) == 1.0);
    Check(EaseInOut(std::nan("")) == 0.0);
    // Monotone, so a camera move never backs up.
    double Previous = -1.0;
    for (int I = 0; I <= 200; ++I)
    {
        const double Value = EaseInOut(I / 200.0);
        Check(Value >= Previous - 1e-12);
        Previous = Value;
    }
    std::printf("Geometry: distances, bearings, segment clamp and easing checked\n");
}

// ---------------------------------------------------------------------------
// 2. Route validation - every refusal is reachable, and the real route passes
// ---------------------------------------------------------------------------

static void RouteValidationChecks()
{
    Route Empty;
    Check(Empty.Validate() == Refusal::EmptyRoute);
    Check(!Empty.IsValid());
    Check(Empty.IndexOfKey("anything") == -1);

    Route Good;
    BuildSyntheticRoute(Good);
    Check(Good.Validate() == Refusal::None);
    Check(Good.Count() == 4);
    Check(Good.IndexOfKey("c") == 2);
    Check(Good.IndexOfKey("nope") == -1);      // never a silent 0
    Check(Good.IndexOfKey(nullptr) == -1);

    auto WithOneStopChanged = [](void (*Mutate)(Stop&)) {
        Route R;
        BuildSyntheticRoute(R);
        Route Rebuilt;
        for (std::size_t I = 0; I < R.Count(); ++I)
        {
            Stop S = R.At(I);
            if (I == 2) Mutate(S);
            Rebuilt.Add(S);
        }
        std::size_t Bad = 999;
        const Refusal Why = Rebuilt.Validate(&Bad);
        return std::pair<Refusal, std::size_t>(Why, Bad);
    };

    Check(WithOneStopChanged([](Stop& S) { S.Key = ""; }).first == Refusal::EmptyKey);
    Check(WithOneStopChanged([](Stop& S) { S.Key = nullptr; }).first == Refusal::EmptyKey);
    Check(WithOneStopChanged([](Stop& S) { S.Key = "a"; }).first == Refusal::DuplicateKey);
    Check(WithOneStopChanged([](Stop& S) { S.Stand.X = std::nan(""); }).first == Refusal::NonFiniteCoordinate);
    Check(WithOneStopChanged([](Stop& S) { S.Look.Z = std::nan(""); }).first == Refusal::NonFiniteCoordinate);
    Check(WithOneStopChanged([](Stop& S) { S.ArriveRadiusCm = 10.0; }).first == Refusal::ArriveRadiusTooSmall);
    Check(WithOneStopChanged([](Stop& S) { S.LeaveRadiusCm = S.ArriveRadiusCm + 1.0; }).first == Refusal::RadiiNotSeparated);
    Check(WithOneStopChanged([](Stop& S) { S.LeaveRadiusCm = S.ArriveRadiusCm - 50.0; }).first == Refusal::RadiiNotSeparated);
    Check(WithOneStopChanged([](Stop& S) { S.WaypointCount = MaxWaypoints + 1; }).first == Refusal::TooManyWaypoints);
    // A stop dropped on top of its neighbour: the visitor would be told he had arrived
    // at two places at once.
    const std::pair<Refusal, std::size_t> Overlap = WithOneStopChanged([](Stop& S) { S.Stand = Point3{10000.0, 200.0, 0.0}; });
    Check(Overlap.first == Refusal::StopsOverlap);
    Check(Overlap.second == 2);
    Check(std::strlen(RefusalText(Refusal::StopsOverlap)) > 10);
    Check(std::strcmp(RefusalText(Refusal::None), "none") == 0);

    // Adding beyond MaxStops refuses rather than overwriting.
    Route Overfull;
    for (std::size_t I = 0; I < MaxStops; ++I)
    {
        Stop S;
        static char Keys[MaxStops][8];
        std::snprintf(Keys[I], sizeof(Keys[I]), "k%02zu", I);
        S.Key = Keys[I];
        S.Stand = Point3{static_cast<double>(I) * 5000.0, 0.0, 0.0};
        S.Look = S.Stand;
        Check(Overfull.Add(S));
    }
    Stop OneTooMany;
    OneTooMany.Key = "spill";
    Check(!Overfull.Add(OneTooMany));
    Check(Overfull.Count() == MaxStops);

    // The real route.
    Route Real;
    BuildRealRoute(Real);
    std::size_t BadStop = 999;
    const Refusal Why = Real.Validate(&BadStop);
    if (Why != Refusal::None)
    {
        std::fprintf(stderr, "real route refused at stop %zu (%s): %s\n",
                     BadStop, Real.At(BadStop).Key, RefusalText(Why));
    }
    Check(Why == Refusal::None);
    Check(Real.Count() == RealStopCount);
    Check(Real.Count() >= 15 && Real.Count() <= 20);      // the brief: fifteen to twenty stops
    Check(Real.IndexOfKey("menorah") > Real.IndexOfKey("heikhal"));
    Check(Real.IndexOfKey("paroches") == static_cast<int>(Real.Count()) - 1);
    Check(Real.TotalLengthCm() > 0.0);
    FactInt("realStopCount", static_cast<long long>(Real.Count()));
    Fact("realRouteLengthCm", Real.TotalLengthCm());
    Fact("realRouteLengthAmot", Real.TotalLengthCm() / 50.0);

    // Distance to a stop only ever grows along the route, and the last equals the total.
    double PreviousDistance = -1.0;
    for (std::size_t I = 0; I < Real.Count(); ++I)
    {
        const double D = Real.DistanceToStopCm(I);
        Check(D >= PreviousDistance - 1e-9);
        PreviousDistance = D;
    }
    Check(Near(Real.DistanceToStopCm(Real.Count() - 1), Real.TotalLengthCm(), 1e-6));
    // Out-of-range indices clamp rather than read past the end.
    Check(Near(Real.DistanceToStopCm(9999), Real.TotalLengthCm(), 1e-6));

    // Every leg starts at the previous stop and ends at this one.
    for (std::size_t I = 1; I < Real.Count(); ++I)
    {
        const Leg Path = Real.LegTo(I);
        Check(Path.Count >= 2);
        Check(Same(Path.Points[0], Real.At(I - 1).Stand));
        Check(Same(Path.Points[Path.Count - 1], Real.At(I).Stand));
        Check(Path.LengthCm() >= Distance2D(Real.At(I - 1).Stand, Real.At(I).Stand) - 1e-6);
        // Every point of the leg is on the leg.
        for (std::size_t Q = 0; Q < Path.Count; ++Q) Check(Path.DistanceCm(Path.Points[Q]) <= 1e-6);
        Check(Same(Path.PointAtFraction(0.0), Path.Points[0], 1e-6));
        Check(Same(Path.PointAtFraction(1.0), Path.Points[Path.Count - 1], 1e-6));
        Check(Path.DistanceCm(Path.PointAtFraction(0.5)) <= 1e-6);
    }
    // Leg 0 is the single starting point: before the tour begins there is nothing to be
    // off-route from.
    Check(Real.LegTo(0).Count == 1);
    Check(Near(Real.LegTo(0).LengthCm(), 0.0));

    // The Heikhal stops are only a few metres apart, so the radius has to be tight for
    // the answer to be unambiguous - which is exactly why NearestStopWithin takes one.
    Check(Real.NearestStopWithin(Point3{-4950.0, 315.0, 925.0}, 400.0) == Real.IndexOfKey("menorah"));
    Check(Real.NearestStopWithin(Point3{4974.0, 0.0, 300.0}, 600.0) == Real.IndexOfKey("outer-court"));
    Check(Real.NearestStopWithin(Point3{500000.0, 0.0, 0.0}, 600.0) == -1);
    std::printf("Route validation: %zu real stops accepted, every refusal reachable\n", Real.Count());
}

// ---------------------------------------------------------------------------
// 3. NO BOUNDARY FLICKER
// ---------------------------------------------------------------------------

static void ArrivalHysteresisChecks()
{
    Route R;
    BuildSyntheticRoute(R);
    Guide G;
    G.SetRoute(&R);
    const Point3 Start{-2000.0, 0.0, 0.0};
    Check(G.Begin(Mode::FollowTheMarker, Start));
    Check(G.GetPhase() == Phase::Travelling);
    Check(!G.IsAtStop());

    const Stop& First = R.At(0);
    const double Arrive = First.ArriveRadiusCm;      // 400
    const double Leave = First.LeaveRadiusCm;        // 620

    // Approach from outside, stopping exactly ON the arrival boundary.
    Check(!G.Observe(Point3{Arrive + 1.0, 0.0, 0.0}, 0.016));
    Check(!G.IsAtStop());
    Check(G.ArrivalTransitionCount() == 0);
    Check(G.Observe(Point3{Arrive, 0.0, 0.0}, 0.016));       // exactly on the boundary arrives
    Check(G.IsAtStop());
    Check(G.GetPhase() == Phase::AtStop);
    Check(G.ArrivalTransitionCount() == 1);
    Check(G.IsVisited(0));

    // Now loiter for ten simulated minutes on the boundary, with the floor trace and the
    // camera bob pushing the position back and forth ACROSS the arrival radius and up to
    // just inside the leave radius. This is precisely the case that strobes without
    // hysteresis. Not one further transition is allowed.
    long long Frames = 0;
    for (int I = 0; I < 36000; ++I)
    {
        const double Wobble = (I % 2 == 0) ? -3.0 : +3.0;
        const double Radius = (I % 7 == 0) ? Leave - 0.5 : Arrive + Wobble;
        Check(!G.Observe(Point3{Radius, 0.0, 0.0}, 1.0 / 60.0));
        Check(G.IsAtStop());
        ++Frames;
    }
    Check(G.ArrivalTransitionCount() == 1);
    FactInt("loiterFramesWithoutFlicker", Frames);

    // Exactly on the leave radius still counts as present: leaving needs to EXCEED it.
    Check(!G.Observe(Point3{Leave, 0.0, 0.0}, 0.016));
    Check(G.IsAtStop());
    Check(G.ArrivalTransitionCount() == 1);
    // One centimetre past it, and only then, he has left.
    Check(!G.Observe(Point3{Leave + 1.0, 0.0, 0.0}, 0.016));
    Check(!G.IsAtStop());
    Check(G.GetPhase() == Phase::Travelling);
    Check(G.ArrivalTransitionCount() == 2);
    Check(G.IsVisited(0));                                   // visiting is permanent

    // Loitering on the LEAVE boundary from outside must not re-arrive either: coming
    // back in requires reaching the tighter arrival radius again.
    for (int I = 0; I < 5000; ++I)
    {
        const double Radius = (I % 2 == 0) ? Leave + 0.5 : Arrive + 1.0;
        G.Observe(Point3{Radius, 0.0, 0.0}, 1.0 / 60.0);
    }
    Check(G.ArrivalTransitionCount() == 2);
    Check(!G.IsAtStop());
    // Re-entering properly does re-arrive, but does not re-fire the "new stop" return.
    Check(!G.Observe(Point3{Arrive - 1.0, 0.0, 0.0}, 0.016));  // already visited: not "just arrived"
    Check(G.IsAtStop());
    Check(G.ArrivalTransitionCount() == 3);
    std::printf("Arrival hysteresis: 36000 boundary frames, 1 transition; leave needs > LeaveRadius\n");
}

static void CorridorHysteresisChecks()
{
    Route R;
    BuildSyntheticRoute(R);
    Guide G;
    G.SetRoute(&R);
    Check(G.Begin(Mode::FollowTheMarker, Point3{0, 0, 0}));
    // Stand on stop 0, then head for stop 1: the leg is the straight run east along Y=0.
    Check(G.Observe(Point3{0, 0, 0}, 0.016));
    Check(G.Next(Point3{0, 0, 0}));
    Check(G.TargetIndex() == 1);

    const double Off = G.OffRouteRadiusCm();     // 1400
    const double Rejoin = G.RejoinRadiusCm();    // 900
    Check(Off - Rejoin >= MinCorridorGapCm);

    // Halfway along the leg, drift sideways to exactly the corridor boundary and stay
    // there, jittering across it, for ten simulated minutes.
    G.Observe(Point3{5000.0, Off, 0.0}, 0.016);
    Check(!G.IsOffRoute());                       // exactly ON the boundary is still on route
    Check(G.OffRouteTransitionCount() == 0);
    G.Observe(Point3{5000.0, Off + 1.0, 0.0}, 0.016);
    Check(G.IsOffRoute());
    Check(G.OffRouteTransitionCount() == 1);
    for (int I = 0; I < 36000; ++I)
    {
        const double Sideways = (I % 3 == 0) ? Off + 0.5 : (I % 3 == 1) ? Off - 2.0 : Rejoin + 1.0;
        G.Observe(Point3{5000.0, Sideways, 0.0}, 1.0 / 60.0);
        Check(G.IsOffRoute());                    // never clears above the rejoin radius
    }
    Check(G.OffRouteTransitionCount() == 1);
    // Exactly on the rejoin radius clears it, and only then.
    G.Observe(Point3{5000.0, Rejoin, 0.0}, 0.016);
    Check(!G.IsOffRoute());
    Check(G.OffRouteTransitionCount() == 2);

    // The rejoin point is on the leg and is the nearest point of it.
    G.Observe(Point3{5000.0, 4000.0, 0.0}, 0.016);
    Check(G.IsOffRoute());
    const Point3 Back = G.RejoinPoint();
    Check(Near(Back.X, 5000.0, 1e-6) && Near(Back.Y, 0.0, 1e-6));
    Check(Near(G.CorridorDistanceCm(), 4000.0, 1e-6));
    // Walking back to it clears the flag.
    G.Observe(Back, 0.016);
    Check(!G.IsOffRoute());

    // Arriving cannot leave the visitor flagged as off-route.
    G.Observe(Point3{9000.0, 3000.0, 0.0}, 0.016);
    Check(G.IsOffRoute());
    G.Observe(R.At(1).Stand, 0.016);
    Check(G.IsAtStop());
    Check(!G.IsOffRoute());
    std::printf("Corridor hysteresis: 36000 boundary frames, 1 transition; rejoin lands on the leg\n");
}

// ---------------------------------------------------------------------------
// 4. EVERY STOP REACHABLE IN ORDER, on the real route
// ---------------------------------------------------------------------------

/** Walk the visitor along a leg polyline in 40 cm steps, feeding every step to Observe.
 * 40 cm is well under every arrival radius, so a stop cannot be stepped over. */
static void WalkLeg(Guide& G, const Leg& Path, std::vector<Point3>* Recorded = nullptr)
{
    const double Total = Path.LengthCm();
    const int Steps = static_cast<int>(Total / 40.0) + 2;
    for (int I = 0; I <= Steps; ++I)
    {
        const Point3 Where = Path.PointAtFraction(static_cast<double>(I) / static_cast<double>(Steps));
        G.Observe(Where, 1.0 / 60.0);
        if (Recorded) Recorded->push_back(Where);
    }
}

static void ReachAllStopsInOrderChecks()
{
    Route R;
    BuildRealRoute(R);
    Guide G;
    G.SetRoute(&R);
    Check(G.Begin(Mode::FollowTheMarker, R.At(0).Stand));

    std::uint64_t PreviousMask = 0;
    for (std::size_t I = 0; I < R.Count(); ++I)
    {
        Check(G.TargetIndex() == I);
        // Everything before I is visited, everything from I on is not.
        for (std::size_t J = 0; J < R.Count(); ++J) Check(G.IsVisited(J) == (J < I));
        WalkLeg(G, R.LegTo(I));
        Check(G.IsAtStop());
        Check(G.IsVisited(I));
        Check(G.GetPhase() == Phase::AtStop);
        // The mask only ever gains bits, exactly one per stop.
        Check((G.VisitedMask() & PreviousMask) == PreviousMask);
        Check(G.VisitedMask() != PreviousMask);
        PreviousMask = G.VisitedMask();
        Check(G.VisitedCount() == I + 1);
        Check(Near(G.DistanceToTargetCm(), Distance2D(R.At(I).Stand, G.LastObservedPosition()), 1e-9));

        const Progress Now = G.GetProgress();
        Check(Now.Visited == I + 1);
        Check(Now.Total == R.Count());
        Check(Near(Now.FractionByStops, static_cast<double>(I + 1) / static_cast<double>(R.Count())));
        Check(Now.FractionByDistance >= -1e-9 && Now.FractionByDistance <= 1.0 + 1e-9);

        if (I + 1 < R.Count())
        {
            Check(G.Next(G.LastObservedPosition()));
            Check(G.GetPhase() == Phase::Travelling);
            Check(!G.IsAtStop());
        }
    }
    // At the last stop, Next() finishes the tour.
    Check(G.TargetIndex() == R.Count() - 1);
    Check(G.Next(G.LastObservedPosition()));
    Check(G.GetPhase() == Phase::Finished);
    Check(G.VisitedCount() == R.Count());
    Check(Near(G.GetProgress().FractionByStops, 1.0));
    Check(!G.Next(G.LastObservedPosition()));       // nothing after the end
    FactInt("stopsReachedInOrder", static_cast<long long>(R.Count()));
    std::printf("Order: all %zu stops reached in sequence, mask monotone, tour finished\n", R.Count());
}

static void SequencingChecks()
{
    Route R;
    BuildRealRoute(R);
    Guide G;
    G.SetRoute(&R);

    // Nothing works before Begin.
    Check(!G.Next(Point3{}));
    Check(!G.Previous(Point3{}));
    Check(G.GetPhase() == Phase::NotStarted);
    Check(!G.IsRunning());

    Check(G.Begin(Mode::FollowTheMarker, R.At(0).Stand));
    // Skipping forward without arriving is allowed - that is what "skip this stop" is.
    Check(G.Next(Point3{}));
    Check(G.TargetIndex() == 1);
    Check(!G.IsVisited(0));
    Check(G.Next(Point3{}));
    Check(G.Next(Point3{}));
    Check(G.TargetIndex() == 3);
    Check(G.Previous(Point3{}));
    Check(G.TargetIndex() == 2);
    Check(G.GoToStop(R.Count() - 1, Point3{}));
    Check(G.TargetIndex() == R.Count() - 1);
    // At the last stop, Next() refuses to finish a tour whose last stop was never seen.
    Check(!G.Next(Point3{}));
    Check(G.GetPhase() != Phase::Finished);
    Check(!G.GoToStop(R.Count(), Point3{}));       // out of range refuses
    Check(G.TargetIndex() == R.Count() - 1);
    Check(!G.Previous(Point3{}) == false);          // previous still works
    Check(G.GoToStop(0, Point3{}));
    Check(!G.Previous(Point3{}));                   // nothing before the first

    // Pause freezes latching; resume puts it back exactly where it was.
    Check(G.GoToStop(4, Point3{}));
    G.Pause();
    Check(G.IsPaused());
    Check(G.GetPhase() == Phase::Paused);
    for (int I = 0; I < 600; ++I) Check(!G.Observe(R.At(4).Stand, 1.0 / 60.0));
    Check(!G.IsAtStop());
    Check(!G.IsVisited(4));                         // standing on it while paused visits nothing
    Check(G.ArrivalTransitionCount() == 0);
    G.Resume();
    Check(!G.IsPaused());
    Check(G.TargetIndex() == 4);
    Check(G.Observe(R.At(4).Stand, 1.0 / 60.0));
    Check(G.IsVisited(4));

    // Wandering off and being found somewhere else entirely.
    const int Menorah = R.IndexOfKey("menorah");
    Check(Menorah > 0);
    const int Found = R.NearestStopWithin(R.At(static_cast<std::size_t>(Menorah)).Stand, 400.0);
    Check(Found == Menorah);
    Check(G.GoToStop(static_cast<std::size_t>(Found), R.At(4).Stand));
    Check(G.TargetIndex() == static_cast<std::size_t>(Menorah));
    Check(G.IsVisited(4));                          // rejoining elsewhere loses no progress

    // Leaving and coming back.
    const Bookmark Left = G.Save();
    G.EndTour();
    Check(G.GetPhase() == Phase::NotStarted);
    Check(G.Restore(Left));
    Check(G.TargetIndex() == static_cast<std::size_t>(Menorah));
    Check(G.IsVisited(4));
    std::printf("Sequencing: skip, back, jump, pause and re-entry checked\n");
}

// ---------------------------------------------------------------------------
// 5. Camera-move timing and "walk me there"
// ---------------------------------------------------------------------------

static void CameraChecks()
{
    CameraTuning Tuning;
    Check(Near(MoveDurationSeconds(Tuning.SpeedCmPerSec * 4.0, Tuning), 4.0));
    Check(Near(MoveDurationSeconds(0.0, Tuning), Tuning.MinSeconds));
    Check(Near(MoveDurationSeconds(-500.0, Tuning), Tuning.MinSeconds));
    Check(Near(MoveDurationSeconds(std::nan(""), Tuning), Tuning.MinSeconds));
    Check(Near(MoveDurationSeconds(10.0, Tuning), Tuning.MinSeconds));           // clamped up
    Check(Near(MoveDurationSeconds(10000000.0, Tuning), Tuning.MaxSeconds));     // clamped down
    CameraTuning Broken;
    Broken.SpeedCmPerSec = 0.0;
    Check(Near(MoveDurationSeconds(1000.0, Broken), Broken.MaxSeconds));         // no division by zero

    Route R;
    BuildRealRoute(R);
    Guide G;
    G.SetRoute(&R);
    const Point3 Origin = R.At(0).Stand;
    Check(G.Begin(Mode::WalkMeThere, Origin));
    Check(G.IsCameraMoving());
    Check(G.CameraAlpha() == 0.0);
    Check(Same(G.CameraPosition(), Origin, 1e-6));

    // Fly the whole tour with the camera, feeding the camera's own position back in as
    // the visitor position, which is what the actor does.
    for (std::size_t I = 0; I < R.Count(); ++I)
    {
        Check(G.TargetIndex() == I);
        double Elapsed = 0.0;
        double PreviousAlpha = -1.0;
        int Frames = 0;
        while (G.IsCameraMoving() && Frames < 20000)
        {
            G.Observe(G.CameraPosition(), 1.0 / 60.0);
            Check(G.CameraAlpha() >= PreviousAlpha - 1e-12);      // never runs backwards
            PreviousAlpha = G.CameraAlpha();
            Elapsed += 1.0 / 60.0;
            ++Frames;
        }
        Check(Frames < 20000);
        Check(Elapsed <= Tuning.MaxSeconds + 0.5);
        Check(G.CameraAlpha() == 1.0);
        Check(G.CameraRemainingSeconds() == 0.0);
        // The move ends exactly on the stop, so the arrival is not a near miss.
        Check(Same(G.CameraPosition(), R.At(I).Stand, 1e-6));
        G.Observe(G.CameraPosition(), 1.0 / 60.0);
        Check(G.IsAtStop());
        Check(G.IsVisited(I));
        if (I + 1 < R.Count())
        {
            Check(G.Next(G.CameraPosition()));
            Check(G.IsCameraMoving());
        }
    }
    Check(G.VisitedCount() == R.Count());

    // Switching modes mid-leg keeps the stop and starts / stops the flight.
    Guide H;
    H.SetRoute(&R);
    Check(H.Begin(Mode::FollowTheMarker, R.At(0).Stand));
    Check(!H.IsCameraMoving());
    Check(H.Next(R.At(0).Stand));
    H.SetMode(Mode::WalkMeThere, R.At(0).Stand);
    Check(H.IsCameraMoving());
    Check(H.TargetIndex() == 1);
    H.SetMode(Mode::FollowTheMarker, R.At(0).Stand);
    Check(!H.IsCameraMoving());
    Check(H.TargetIndex() == 1);
    Check(H.GetMode() == Mode::FollowTheMarker);

    // A camera move does not advance while paused.
    Check(H.GoToStop(2, R.At(1).Stand));
    H.SetMode(Mode::WalkMeThere, R.At(1).Stand);
    Check(H.IsCameraMoving());
    const double AlphaBefore = H.CameraAlpha();
    H.Pause();
    for (int I = 0; I < 600; ++I) H.Observe(H.CameraPosition(), 1.0 / 60.0);
    Check(H.CameraAlpha() == AlphaBefore);
    H.Resume();
    H.Observe(H.CameraPosition(), 1.0 / 60.0);
    Check(H.CameraAlpha() > AlphaBefore);
    std::printf("Camera: duration clamps, monotone alpha, exact landing, pause freezes the move\n");
}

static void MarkerChecks()
{
    Route R;
    BuildRealRoute(R);
    Guide G;
    G.SetRoute(&R);
    Check(G.Begin(Mode::FollowTheMarker, R.At(0).Stand));

    // On a leg with an approach waypoint, the marker leads to the waypoint first and
    // only then to the stop. That is what walks a visitor through a gate rather than
    // into the wall beside it.
    const int WithWaypoint = R.IndexOfKey("east-inner-gate");
    Check(WithWaypoint > 0);
    Check(G.GoToStop(static_cast<std::size_t>(WithWaypoint), R.At(0).Stand));
    const Leg Path = R.LegTo(static_cast<std::size_t>(WithWaypoint));
    Check(Path.Count == 3);
    G.Observe(Path.Points[0], 1.0 / 60.0);
    Check(Same(G.MarkerPosition(), Path.Points[1], 1e-6));
    G.Observe(Path.Points[1], 1.0 / 60.0);
    Check(Same(G.MarkerPosition(), Path.Points[2], 1e-6));
    G.Observe(Path.Points[2], 1.0 / 60.0);
    Check(Same(G.MarkerPosition(), Path.Points[2], 1e-6));   // never past the stop

    // On a leg with no waypoints the marker is simply the stop.
    const int NoWaypoint = R.IndexOfKey("outer-court");
    Check(NoWaypoint > 0);
    Check(R.At(static_cast<std::size_t>(NoWaypoint)).WaypointCount == 0);
    Check(G.GoToStop(static_cast<std::size_t>(NoWaypoint), R.At(0).Stand));
    G.Observe(Point3{20000.0, 20000.0, 0.0}, 1.0 / 60.0);
    Check(Same(G.MarkerPosition(), R.At(static_cast<std::size_t>(NoWaypoint)).Stand, 1e-6));

    // Bearing: from due east of the altar stop, the altar is due west.
    const int Altar = R.IndexOfKey("outer-altar");
    Check(Altar > 0);
    Check(G.GoToStop(static_cast<std::size_t>(Altar), Point3{}));
    const Point3 AltarStand = R.At(static_cast<std::size_t>(Altar)).Stand;
    G.Observe(Point3{AltarStand.X + 5000.0, AltarStand.Y, AltarStand.Z}, 1.0 / 60.0);
    Check(Near(G.BearingToTargetDegrees(), 270.0, 1e-6));
    Check(Near(G.DistanceToTargetCm(), 5000.0, 1e-6));
    std::printf("Marker: waypoint leading, bearing and distance checked\n");
}

// ---------------------------------------------------------------------------
// 6. EXACT RESUME
// ---------------------------------------------------------------------------

static void ExactResumeChecks()
{
    Route R;
    BuildRealRoute(R);

    // Run a tour to the middle, in "walk me there" so a camera move is in flight when
    // the bookmark is taken - the hardest thing to restore.
    Guide G;
    G.SetRoute(&R);
    Check(G.Begin(Mode::WalkMeThere, R.At(0).Stand));
    for (std::size_t I = 0; I < 7; ++I)
    {
        while (G.IsCameraMoving()) G.Observe(G.CameraPosition(), 1.0 / 60.0);
        G.Observe(G.CameraPosition(), 1.0 / 60.0);
        Check(G.IsVisited(I));
        Check(G.Next(G.CameraPosition()));
    }
    // Stop the recording partway through the eighth leg.
    for (int I = 0; I < 25; ++I) G.Observe(G.CameraPosition(), 1.0 / 60.0);
    Check(G.IsCameraMoving());
    Check(G.CameraAlpha() > 0.0 && G.CameraAlpha() < 1.0);

    const Bookmark Saved = G.Save();
    Check(Saved.VisitedMask != 0);
    Check(Saved.TargetIndex == 7);
    Check(Saved.CameraMoving);

    // Record the exact continuation: the frame times AND the resulting bookmarks.
    std::vector<double> FrameTimes;
    std::vector<Bookmark> Expected;
    {
        Guide Continue;
        Continue.SetRoute(&R);
        Check(Continue.Restore(Saved));
        Check(Continue.Save() == Saved);                     // restore is a fixed point
        for (int I = 0; I < 900; ++I)
        {
            const double Delta = (I % 3 == 0) ? 1.0 / 60.0 : (I % 3 == 1) ? 1.0 / 90.0 : 1.0 / 45.0;
            FrameTimes.push_back(Delta);
            Continue.Observe(Continue.CameraPosition(), Delta);
            if (I == 300) Continue.Next(Continue.CameraPosition());
            if (I == 600) { Continue.Pause(); }
            if (I == 650) { Continue.Resume(); }
            Expected.push_back(Continue.Save());
        }
    }

    // Replay it from the same bookmark on a fresh guide: every frame must match exactly,
    // with no tolerance at all.
    {
        Guide Replay;
        Replay.SetRoute(&R);
        Check(Replay.Restore(Saved));
        for (std::size_t I = 0; I < FrameTimes.size(); ++I)
        {
            Replay.Observe(Replay.CameraPosition(), FrameTimes[I]);
            if (I == 300) Replay.Next(Replay.CameraPosition());
            if (I == 600) { Replay.Pause(); }
            if (I == 650) { Replay.Resume(); }
            const Bookmark Now = Replay.Save();
            if (Now != Expected[I])
            {
                std::fprintf(stderr, "resume diverged at frame %zu: target %zu vs %zu, mask %llu vs %llu\n",
                             I, Now.TargetIndex, Expected[I].TargetIndex,
                             static_cast<unsigned long long>(Now.VisitedMask),
                             static_cast<unsigned long long>(Expected[I].VisitedMask));
            }
            Check(Now == Expected[I]);
        }
    }
    FactInt("exactResumeFramesMatched", static_cast<long long>(FrameTimes.size()));

    // A bookmark that does not fit the route is refused, not clamped: a clamped resume
    // drops the visitor somewhere he has never been and reads as a bug in the building.
    Guide Reject;
    Reject.SetRoute(&R);
    Bookmark Bad = Saved;
    Bad.TargetIndex = R.Count();
    Check(!Reject.Restore(Bad));
    Bad = Saved;
    Bad.VisitedMask |= (static_cast<std::uint64_t>(1) << 63);      // a stop this route has not got
    Check(!Reject.Restore(Bad));
    Bad = Saved;
    Bad.CameraElapsedSeconds = Bad.CameraDurationSeconds + 1.0;
    Check(!Reject.Restore(Bad));
    Bad = Saved;
    Bad.CameraElapsedSeconds = -1.0;
    Check(!Reject.Restore(Bad));
    Bad = Saved;
    Bad.CameraDurationSeconds = std::nan("");
    Check(!Reject.Restore(Bad));
    Bad = Saved;
    Bad.CameraFrom.X = std::nan("");
    Check(!Reject.Restore(Bad));
    // And after every refusal the guide is untouched.
    Check(Reject.GetPhase() == Phase::NotStarted);
    Check(Reject.VisitedCount() == 0);

    Guide NoRoute;
    Check(!NoRoute.Restore(Saved));
    Check(!NoRoute.Begin(Mode::FollowTheMarker, Point3{}));
    Route Invalid;
    Guide OnInvalid;
    OnInvalid.SetRoute(&Invalid);
    Check(!OnInvalid.Begin(Mode::FollowTheMarker, Point3{}));

    // SetRoute clears any stale progress rather than carrying another tour's bits.
    Guide Reused;
    Reused.SetRoute(&R);
    Check(Reused.Restore(Saved));
    Check(Reused.VisitedCount() > 0);
    Reused.SetRoute(&R);
    Check(Reused.VisitedCount() == 0);
    Check(Reused.GetPhase() == Phase::NotStarted);
    std::printf("Resume: 900 frames replayed bit-exact; every malformed bookmark refused\n");
}

// ---------------------------------------------------------------------------
// 7. Progress, corridor settings and the confidence labels
// ---------------------------------------------------------------------------

static void ProgressChecks()
{
    Route R;
    BuildRealRoute(R);
    Guide G;
    G.SetRoute(&R);
    Check(G.Begin(Mode::FollowTheMarker, R.At(0).Stand));
    Check(Near(G.GetProgress().FractionByDistance, 0.0, 1e-9));

    double PreviousDistance = -1.0;
    for (std::size_t I = 0; I < R.Count(); ++I)
    {
        std::vector<Point3> Walked;
        WalkLeg(G, R.LegTo(I), &Walked);
        const Progress Now = G.GetProgress();
        // Distance progress never goes backwards from stop to stop.
        Check(Now.FractionByDistance >= PreviousDistance - 1e-9);
        PreviousDistance = Now.FractionByDistance;
        if (I + 1 < R.Count()) Check(G.Next(G.LastObservedPosition()));
    }
    Check(Near(PreviousDistance, 1.0, 1e-6));
    Fact("finalDistanceFraction", PreviousDistance);

    // A corridor pair that cannot hold is refused and the previous one kept.
    Guide C;
    C.SetRoute(&R);
    const double WasOff = C.OffRouteRadiusCm();
    const double WasRejoin = C.RejoinRadiusCm();
    C.SetCorridor(1000.0, 990.0);                       // gap too small
    Check(C.OffRouteRadiusCm() == WasOff && C.RejoinRadiusCm() == WasRejoin);
    C.SetCorridor(500.0, 900.0);                        // inverted
    Check(C.OffRouteRadiusCm() == WasOff);
    C.SetCorridor(1000.0, -5.0);                        // nonsense
    Check(C.OffRouteRadiusCm() == WasOff);
    C.SetCorridor(std::nan(""), 100.0);
    Check(C.OffRouteRadiusCm() == WasOff);
    C.SetCorridor(2000.0, 1200.0);                      // fine
    Check(C.OffRouteRadiusCm() == 2000.0 && C.RejoinRadiusCm() == 1200.0);

    // A non-finite visitor position is ignored rather than poisoning the state.
    Check(C.Begin(Mode::FollowTheMarker, R.At(0).Stand));
    const Bookmark Before = C.Save();
    Check(!C.Observe(Point3{std::nan(""), 0.0, 0.0}, 1.0 / 60.0));
    Check(C.Save() == Before);
    std::printf("Progress: monotone by distance, reaches 1.0; corridor guards hold\n");
}

static void ConfidenceChecks()
{
    Confidence Value = Confidence::Certain;
    Check(ParseConfidence("certain", Value) && Value == Confidence::Certain);
    Check(ParseConfidence("disputed", Value) && Value == Confidence::Disputed);
    Check(ParseConfidence("authored", Value) && Value == Confidence::Authored);
    // Anything else is a loud failure, never a silent promotion to "certain".
    Value = Confidence::Authored;
    Check(!ParseConfidence("Certain", Value));
    Check(!ParseConfidence("probable", Value));
    Check(!ParseConfidence("", Value));
    Check(!ParseConfidence(nullptr, Value));
    Check(Value == Confidence::Authored);          // untouched on failure
    Check(std::strcmp(ConfidenceKey(Confidence::Certain), "certain") == 0);
    Check(std::strcmp(ConfidenceKey(Confidence::Disputed), "disputed") == 0);
    Check(std::strcmp(ConfidenceKey(Confidence::Authored), "authored") == 0);
    std::printf("Confidence labels: round trip exact, unknown label rejected\n");
}

// ---------------------------------------------------------------------------

int main(int argc, char** argv)
{
    GeometryChecks();
    RouteValidationChecks();
    ArrivalHysteresisChecks();
    CorridorHysteresisChecks();
    ReachAllStopsInOrderChecks();
    SequencingChecks();
    CameraChecks();
    MarkerChecks();
    ExactResumeChecks();
    ProgressChecks();
    ConfidenceChecks();

    FactInt("checks", CheckCount);
    if (argc > 1)
    {
        FILE* Out = std::fopen(argv[1], "w");
        if (Out != nullptr)
        {
            std::fprintf(Out, "{\n  \"test\": \"TourMathTest\",\n  \"status\": \"pass\"");
            for (const std::pair<std::string, std::string>& Row : Facts)
            {
                std::fprintf(Out, ",\n  \"%s\": %s", Row.first.c_str(), Row.second.c_str());
            }
            std::fprintf(Out, "\n}\n");
            std::fclose(Out);
        }
    }
    std::printf("PASS: guided tour math, %lld checks\n", CheckCount);
    return 0;
}
