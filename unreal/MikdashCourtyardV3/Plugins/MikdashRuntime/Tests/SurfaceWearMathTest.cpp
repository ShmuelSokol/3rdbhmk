#define _CRT_SECURE_NO_WARNINGS

// Standalone test for SurfaceWearMath.h. No Unreal, no engine headers.
//
//   cl /nologo /std:c++17 /EHsc /W4 /WX /utf-8 /I<...>/Public SurfaceWearMathTest.cpp
//   SurfaceWearMathTest.exe <optional path to tests.json>
//
// Every check goes through Check(), which is live in debug AND release builds; the
// printed lines are the numeric evidence, and with an argument the same numbers are
// written as JSON for SourceAssets/surface-review/tests.json.
//
// The routes below are the real ones, derived from SourceAssets/architecture-manifest.json
// (gate thresholds, stair flights, court floors) and kept in step with the table in
// Scripts/create_decals.py. Nothing here claims visual acceptance.

#include "SurfaceWearMath.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

using namespace MikdashWear;

// Deliberately NOT <cassert>: a release build (/O2 /DNDEBUG) would compile every
// assert away and the "release" run would prove nothing. Check() always evaluates
// its argument, always counts, and exits non-zero on the first failure.
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
    char Buffer[64];
    std::snprintf(Buffer, sizeof(Buffer), "%lld", Value);
    Facts.emplace_back(Key, Buffer);
}

// ---------------------------------------------------------------------------
// The measured routes (world XY centimetres, +X east, +Y south, from the manifest)
// ---------------------------------------------------------------------------

static const FPoint2 EastPilgrimAxis[] = {
    {9400.0, 0.0},    // foot of the outer east stair, outside the court
    {8600.0, 0.0},    // head of that stair, court level Z 300
    {7950.0, 0.0},    // outer east gate threshold
    {3700.0, 0.0},    // foot of the inner east stair
    {2650.0, 0.0},    // inner east gate threshold
    {2100.0, 0.0},    // Ezras Yisrael strip
};
static const FPoint2 NorthGateRoute[] = {
    {0.0, -9200.0}, {0.0, -8600.0}, {0.0, -7950.0}, {0.0, -4000.0}, {0.0, -2650.0}, {0.0, -2100.0},
};
static const FPoint2 SouthGateRoute[] = {
    {0.0,  9200.0}, {0.0,  8600.0}, {0.0,  7950.0}, {0.0,  4000.0}, {0.0,  2650.0}, {0.0,  2100.0},
};
static const FPoint2 LaverToRamp[] = {
    {-2300.0, 0.0}, {-1950.0, 1500.0}, {-900.0, 2100.0}, {0.0, 2300.0}, {0.0, 710.0},
};
static const FPoint2 UlamStair[] = {
    {-1200.0, 0.0}, {-1425.0, 0.0}, {-2375.0, 0.0}, {-2450.0, 0.0},
};
static const FPoint2 OuterCourtRing[] = {
    {7000.0, -7000.0}, {7000.0, 7000.0}, {-7000.0, 7000.0}, {-7000.0, -7000.0}, {7000.0, -7000.0},
};

static const FRoute Routes[] = {
    {EastPilgrimAxis, 6, 220.0, 320.0, 9000.0},
    {NorthGateRoute,  6, 190.0, 300.0, 3400.0},
    {SouthGateRoute,  6, 190.0, 300.0, 3400.0},
    {LaverToRamp,     5, 110.0, 160.0, 1400.0},
    {UlamStair,       4,  95.0, 140.0,  600.0},
    {OuterCourtRing,  5, 260.0, 420.0, 2200.0},
};
static const int RouteCount = 6;

// ---------------------------------------------------------------------------

static void FalloffChecks()
{
    // On the centre line, exactly 1; far away, exactly 0. Not "about".
    Check(WearFalloff(0.0, 200.0, 300.0) == 1.0);
    Check(WearFalloff(200.0, 200.0, 300.0) == 1.0);
    Check(WearFalloff(500.0, 200.0, 300.0) == 0.0);
    Check(WearFalloff(5000.0, 200.0, 300.0) == 0.0);
    Check(WearFalloff(std::nan(""), 200.0, 300.0) == 0.0);

    // Monotonically non-increasing with distance, and always inside [0,1].
    double Previous = 1.0;
    for (int Step = 0; Step <= 600; ++Step)
    {
        const double Distance = static_cast<double>(Step);
        const double Value = WearFalloff(Distance, 200.0, 300.0);
        Check(Value >= 0.0 && Value <= 1.0);
        Check(Value <= Previous + 1e-12);
        Previous = Value;
    }
    Fact("falloffOnCentreLine", WearFalloff(0.0, 200.0, 300.0));
    Fact("falloffAtHalfWidth", WearFalloff(200.0, 200.0, 300.0));
    Fact("falloffBeyondFeather", WearFalloff(500.0, 200.0, 300.0));

    // A route with no points is infinitely far, never zero distance.
    const FRoute Empty = {nullptr, 0, 100.0, 100.0, 100.0};
    Check(DistanceToRoute(0.0, 0.0, Empty) > 1.0e30);
    Check(TrafficDensity(0.0, 0.0, &Empty, 1) == 0.0);
    Check(TrafficDensity(0.0, 0.0, nullptr, 4) == 0.0);
}

static void RouteWearChecks()
{
    // Wear is highest where traffic converges: the outer east gate threshold carries
    // the pilgrim axis, and the inner east threshold carries it again.
    const double OuterEastGate = TrafficDensity(7950.0, 0.0, Routes, RouteCount);
    const double InnerEastGate = TrafficDensity(2650.0, 0.0, Routes, RouteCount);
    const double NorthGate     = TrafficDensity(0.0, -7950.0, Routes, RouteCount);
    const double RampFoot      = TrafficDensity(0.0, 2300.0, Routes, RouteCount);
    const double UlamFoot      = TrafficDensity(-1425.0, 0.0, Routes, RouteCount);

    // ... and near zero in the corners of the outer court, where nobody goes.
    const double DeadCornerNE  = TrafficDensity(6200.0, -6200.0, Routes, RouteCount);
    const double DeadCornerSW  = TrafficDensity(-6200.0, 6200.0, Routes, RouteCount);
    const double MidCourtVoid  = TrafficDensity(5000.0, -5000.0, Routes, RouteCount);

    Check(OuterEastGate > 0.0);
    Check(InnerEastGate > 0.0);
    Check(OuterEastGate >= 9000.0);            // the whole axis passes through it
    Check(DeadCornerNE == 0.0);                // exactly zero, not merely small
    Check(DeadCornerSW == 0.0);
    Check(MidCourtVoid == 0.0);
    Check(OuterEastGate > NorthGate);          // the east axis is the busy one
    Check(NorthGate > UlamFoot);
    Check(RampFoot > 0.0);

    // Every named wear site outranks every off-route probe by a wide margin.
    const double Sites[] = {OuterEastGate, InnerEastGate, NorthGate, RampFoot, UlamFoot};
    const double Voids[] = {DeadCornerNE, DeadCornerSW, MidCourtVoid,
                            TrafficDensity(-5200.0, -5200.0, Routes, RouteCount),
                            TrafficDensity(4400.0, 3900.0, Routes, RouteCount)};
    for (int S = 0; S < 5; ++S)
    {
        for (int V = 0; V < 5; ++V) Check(Sites[S] > Voids[V] + 100.0);
    }

    Fact("trafficOuterEastGate", OuterEastGate);
    Fact("trafficInnerEastGate", InnerEastGate);
    Fact("trafficNorthGate", NorthGate);
    Fact("trafficRampFoot", RampFoot);
    Fact("trafficUlamStairFoot", UlamFoot);
    Fact("trafficDeadCornerNorthEast", DeadCornerNE);
    Fact("trafficDeadCornerSouthWest", DeadCornerSW);
    Fact("trafficMidCourtVoid", MidCourtVoid);

    // Polish saturates: it stays inside [0,1) and rises with both traffic and time.
    const double GatePolish  = FootPolish(OuterEastGate, 40.0);
    const double CourtPolish = FootPolish(MidCourtVoid, 40.0);
    const double Century     = FootPolish(OuterEastGate, 100.0);
    Check(GatePolish > 0.0 && GatePolish < 1.0);
    Check(CourtPolish == 0.0);
    Check(Century > GatePolish);
    Check(Century < 1.0);
    Check(FootPolish(OuterEastGate, 0.0) == 0.0);
    Check(FootPolish(0.0, 40.0) == 0.0);
    Check(FootPolish(1.0e12, 1.0e6) < 1.0);
    Fact("polishGateForty", GatePolish);
    Fact("polishGateCentury", Century);
    Fact("polishMidCourtVoid", CourtPolish);
}

// ---------------------------------------------------------------------------

static const int GridX = 96;
static const int GridY = 96;
static double CellsA[GridX * GridY];
static double CellsB[GridX * GridY];
static double CellsC[GridX * GridY];

static void FillGrid(double* Cells, unsigned int Seed)
{
    FWearGrid Grid = {Cells, GridX, GridY, -9600.0, -9600.0, 200.0};
    ClearGrid(Grid);
    for (int Index = 0; Index < RouteCount; ++Index)
    {
        AccumulateRoute(Grid, Routes[Index], 24, Seed);
    }
}

static void AccumulationChecks()
{
    FillGrid(CellsA, 20260908u);
    FillGrid(CellsB, 20260908u);          // same seed
    FillGrid(CellsC, 777u);               // different seed

    // Determinism: same seed, bit-identical grid.
    long long IdenticalCells = 0;
    long long DifferingCells = 0;
    for (int Index = 0; Index < GridX * GridY; ++Index)
    {
        Check(CellsA[Index] == CellsB[Index]);
        ++IdenticalCells;
        if (CellsA[Index] != CellsC[Index]) ++DifferingCells;
    }
    Check(DifferingCells > 0);            // a different seed really does scatter differently
    FactInt("gridCellsCompared", IdenticalCells);
    FactInt("gridCellsChangedByNewSeed", DifferingCells);

    // Conservation: no footfall is lost or invented, and nothing goes negative.
    double TotalA = 0.0;
    double TotalC = 0.0;
    double Peak   = 0.0;
    for (int Index = 0; Index < GridX * GridY; ++Index)
    {
        Check(CellsA[Index] >= 0.0);
        TotalA += CellsA[Index];
        TotalC += CellsC[Index];
        if (CellsA[Index] > Peak) Peak = CellsA[Index];
    }
    double TotalTrips = 0.0;
    for (int Index = 0; Index < RouteCount; ++Index) TotalTrips += Routes[Index].TripsPerDay;
    Check(TotalA <= TotalTrips + 1e-6);           // never more than was put in
    Check(TotalA > TotalTrips * 0.80);            // and almost all of it landed in bounds
    Check(std::fabs(TotalA - TotalC) < TotalTrips * 0.05);
    Fact("gridTotalTripsIn", TotalTrips);
    Fact("gridTotalAccumulated", TotalA);
    Fact("gridPeakCell", Peak);

    const FWearGrid Grid = {CellsA, GridX, GridY, -9600.0, -9600.0, 200.0};
    // On the east axis the grid is loaded; in the dead corner it is empty.
    const double OnAxis  = GridValue(Grid, 5000.0, 0.0) + GridValue(Grid, 5200.0, 0.0)
                         + GridValue(Grid, 4800.0, 0.0);
    const double OffAxis = GridValue(Grid, 5000.0, -5000.0) + GridValue(Grid, -5000.0, 5000.0)
                         + GridValue(Grid, 4000.0, 3000.0);
    Check(OnAxis > 0.0);
    Check(OffAxis == 0.0);
    Check(GridValue(Grid, 1.0e9, 1.0e9) == 0.0);      // out of bounds reads zero, not garbage
    Fact("gridOnEastAxis", OnAxis);
    Fact("gridOffAxis", OffAxis);
}

// ---------------------------------------------------------------------------

static void StreakChecks()
{
    // A thin string course high on the court wall streaks; a deep cornice throws the
    // water clear and streaks far less from the same height.
    const double ThinCourse = StreakLengthCm(2400.0, 8.75, JerusalemRainfallMm, 1.0);
    const double DeepCornice = StreakLengthCm(2400.0, 55.0, JerusalemRainfallMm, 1.0);
    Check(ThinCourse > DeepCornice);
    Check(ThinCourse > 0.0);
    Check(DeepCornice > 0.0);

    // A streak can never be longer than the wall below it.
    for (int Drop = 1; Drop <= 400; ++Drop)
    {
        const double Height = static_cast<double>(Drop);
        const double Length = StreakLengthCm(Height, 10.0, JerusalemRainfallMm, 1.0);
        Check(Length >= 0.0);
        Check(Length <= Height + 1e-9);
    }

    // Sheltered, dry or unsupported cases are exactly zero.
    Check(StreakLengthCm(2400.0, 10.0, JerusalemRainfallMm, 0.0) == 0.0);
    Check(StreakLengthCm(2400.0, 10.0, 0.0, 1.0) == 0.0);
    Check(StreakLengthCm(0.0, 10.0, JerusalemRainfallMm, 1.0) == 0.0);
    Check(StreakLengthCm(-50.0, 10.0, JerusalemRainfallMm, 1.0) == 0.0);

    // More rain, longer streak; more shelter, shorter.
    Check(StreakLengthCm(3000.0, 10.0, 1100.0, 1.0) > StreakLengthCm(3000.0, 10.0, 550.0, 1.0));
    Check(StreakLengthCm(3000.0, 10.0, 550.0, 0.4) < StreakLengthCm(3000.0, 10.0, 550.0, 1.0));

    Fact("streakThinStringCourse", ThinCourse);
    Fact("streakDeepUlamCornice", DeepCornice);
    Fact("streakLowSill", StreakLengthCm(120.0, 8.0, JerusalemRainfallMm, 1.0));
}

static void WeatheringChecks()
{
    // New stone carries nothing at all; old exposed stone carries a lot.
    Check(Weathering(1.0, 0.0) == 0.0);
    Check(Weathering(1.0, -10.0) == 0.0);
    Check(Weathering(0.0, 500.0) == 0.0);
    Check(LichenCoverage(1.0, 0.8, 0.0) == 0.0);
    Check(LichenCoverage(1.0, 0.8, 5.0) == 0.0);          // still inside the settle time
    Check(LichenCoverage(1.0, 0.0, 400.0) == 0.0);        // full sun, no lichen
    Check(LichenCoverage(0.0, 1.0, 400.0) == 0.0);        // never wetted, no lichen

    const double NewOuterWall = Weathering(1.0, 0.0);
    const double OldOuterWall = Weathering(1.0, 400.0);
    const double ShelteredOld = Weathering(0.25, 400.0);
    Check(OldOuterWall > ShelteredOld);
    Check(OldOuterWall < 1.0);
    Check(NewOuterWall == 0.0);

    const double OldShadedLichen = LichenCoverage(0.9, 0.75, 400.0);
    const double NewShadedLichen = LichenCoverage(0.9, 0.75, 1.0);
    Check(OldShadedLichen > 0.0);
    Check(OldShadedLichen <= 0.45);
    Check(NewShadedLichen == 0.0);

    // Monotone in age, and never out of range at any age.
    double PreviousWeather = -1.0;
    double PreviousLichen  = -1.0;
    for (int Year = 0; Year <= 800; ++Year)
    {
        const double Age = static_cast<double>(Year);
        const double W = Weathering(0.85, Age);
        const double L = LichenCoverage(0.85, 0.6, Age);
        Check(W >= 0.0 && W < 1.0);
        Check(L >= 0.0 && L <= 0.45);
        Check(W >= PreviousWeather - 1e-12);
        Check(L >= PreviousLichen - 1e-12);
        PreviousWeather = W;
        PreviousLichen  = L;
    }

    Fact("weatheringNewOuterWall", NewOuterWall);
    Fact("weatheringOldOuterWall", OldOuterWall);
    Fact("weatheringShelteredOld", ShelteredOld);
    Fact("lichenOldShaded", OldShadedLichen);
    Fact("lichenNewShaded", NewShadedLichen);
}

static void StoneVariationChecks()
{
    // Every jittered instance stays inside the stated meleke band, for both the new
    // inner stonework and the old weathered outer courses.
    double MinTint = 10.0;
    double MaxTint = -10.0;
    double MinRough = 10.0;
    double MaxRough = -10.0;
    double SumR = 0.0;
    double SumB = 0.0;
    const int Samples = 4096;
    for (int Index = 0; Index < Samples; ++Index)
    {
        const double Age = (Index % 2) ? 0.0 : 0.85;
        const FStoneVariation V = StoneVariation(20260908u, static_cast<unsigned int>(Index), Age);
        const double Tints[3] = {V.TintR, V.TintG, V.TintB};
        for (int C = 0; C < 3; ++C)
        {
            Check(Tints[C] >= 0.88 && Tints[C] <= 1.14);
            if (Tints[C] < MinTint) MinTint = Tints[C];
            if (Tints[C] > MaxTint) MaxTint = Tints[C];
        }
        Check(V.RoughnessScale >= 0.82 && V.RoughnessScale <= 1.20);
        if (V.RoughnessScale < MinRough) MinRough = V.RoughnessScale;
        if (V.RoughnessScale > MaxRough) MaxRough = V.RoughnessScale;
        if (Age > 0.0) { SumR += V.TintR; SumB += V.TintB; }
    }
    // Weathered meleke yellows: on average red sits above blue.
    Check(SumR > SumB);
    // The jitter is real variation, not a constant.
    Check(MaxTint - MinTint > 0.03);
    Check(MaxRough - MinRough > 0.03);

    // Determinism: identical inputs, identical output.
    const FStoneVariation A = StoneVariation(20260908u, 1234u, 0.5);
    const FStoneVariation B = StoneVariation(20260908u, 1234u, 0.5);
    const FStoneVariation C = StoneVariation(20260908u, 1235u, 0.5);
    Check(A.TintR == B.TintR && A.TintG == B.TintG && A.TintB == B.TintB);
    Check(A.RoughnessScale == B.RoughnessScale);
    Check(A.TintR != C.TintR || A.TintG != C.TintG || A.TintB != C.TintB);

    Check(PolishRoughnessScale(0.0) == 1.0);
    Check(PolishRoughnessScale(1.0) >= 0.58);
    Check(PolishRoughnessScale(1.0) < PolishRoughnessScale(0.0));
    Check(PolishRoughnessScale(-5.0) == 1.0);
    Check(PolishRoughnessScale(50.0) >= 0.58);

    Fact("stoneTintMinimum", MinTint);
    Fact("stoneTintMaximum", MaxTint);
    Fact("stoneRoughnessMinimum", MinRough);
    Fact("stoneRoughnessMaximum", MaxRough);
    Fact("stoneWeatheredMeanRed", SumR / (Samples / 2));
    Fact("stoneWeatheredMeanBlue", SumB / (Samples / 2));
    Fact("polishRoughnessScaleFull", PolishRoughnessScale(1.0));
}

static void FadeChecks()
{
    Check(DistanceFade(0.0, 3000.0, 9000.0) == 1.0);
    Check(DistanceFade(3000.0, 3000.0, 9000.0) == 1.0);
    Check(DistanceFade(9000.0, 3000.0, 9000.0) == 0.0);
    Check(DistanceFade(50000.0, 3000.0, 9000.0) == 0.0);
    Check(DecalScore(1.0, 50000.0, 3000.0, 9000.0) == 0.0);
    Check(DecalScore(0.0, 0.0, 3000.0, 9000.0) == 0.0);

    double Previous = 1.0;
    for (int Step = 0; Step <= 200; ++Step)
    {
        const double Distance = static_cast<double>(Step) * 60.0;
        const double Fade = DistanceFade(Distance, 3000.0, 9000.0);
        Check(Fade >= 0.0 && Fade <= 1.0);
        Check(Fade <= Previous + 1e-12);
        const double Score = DecalScore(0.8, Distance, 3000.0, 9000.0);
        Check(Score >= 0.0 && Score <= 0.8 + 1e-12);
        Previous = Fade;
    }
    Fact("fadeAtStart", DistanceFade(3000.0, 3000.0, 9000.0));
    Fact("fadeMidway", DistanceFade(6000.0, 3000.0, 9000.0));
    Fact("fadeAtEnd", DistanceFade(9000.0, 3000.0, 9000.0));
}

// ---------------------------------------------------------------------------

static void BudgetChecks()
{
    // The nine wear categories actually planned, in the priority order used by
    // AMikdashSurfaceDetail. Weight is the share of the leftover budget.
    FBudgetRequest Plan[9] = {
        {5.0, 96, 24},   // 0 foot polish on routes and thresholds
        {4.0, 72, 18},   // 1 step nosings
        {3.0, 64, 12},   // 2 rain streaks below ledges
        {2.5, 48,  8},   // 3 dust runoff
        {2.0, 24,  6},   // 4 water staining near drainage
        {3.5, 20,  8},   // 5 soot above lamps and the altar
        {1.5, 60,  0},   // 6 lichen on the old outer stonework
        {1.5, 44,  0},   // 7 wind-blown dust in corners
        {1.0, 32,  0},   // 8 miscellaneous weathering
    };
    int Counts[9] = {0};

    // The cap is never exceeded, at any cap, and the per-category request is never
    // exceeded either.
    long long TotalRequested = 0;
    for (int Index = 0; Index < 9; ++Index) TotalRequested += Plan[Index].Requested;

    for (int Cap = 0; Cap <= 700; ++Cap)
    {
        const int Total = AllocateBudget(Plan, 9, Cap, Counts);
        Check(Total <= Cap);
        Check(Total >= 0);
        int Sum = 0;
        for (int Index = 0; Index < 9; ++Index)
        {
            Check(Counts[Index] >= 0);
            Check(Counts[Index] <= Plan[Index].Requested);
            Sum += Counts[Index];
        }
        Check(Sum == Total);
        Check(Total <= static_cast<int>(TotalRequested));
        // Below saturation the allocator spends everything it is given.
        if (Cap <= static_cast<int>(TotalRequested)) Check(Total == Cap);
        else Check(Total == static_cast<int>(TotalRequested));
    }

    // Determinism: same plan, same cap, same answer.
    int First[9] = {0};
    int Second[9] = {0};
    AllocateBudget(Plan, 9, 220, First);
    AllocateBudget(Plan, 9, 220, Second);
    for (int Index = 0; Index < 9; ++Index) Check(First[Index] == Second[Index]);

    // At the shipping cap of 220 the guaranteed minimums are all met and the busy
    // categories get the larger share.
    Check(First[0] >= Plan[0].Minimum);
    Check(First[5] >= Plan[5].Minimum);
    Check(First[0] > First[8]);
    Check(First[0] + First[1] > First[6] + First[7]);
    int ShippingTotal = 0;
    for (int Index = 0; Index < 9; ++Index) ShippingTotal += First[Index];
    Check(ShippingTotal == 220);

    // Absurd inputs: minimums that alone blow the cap, negative values, a null plan.
    FBudgetRequest Greedy[3] = {{1.0, 500, 400}, {1.0, 500, 400}, {1.0, 500, 400}};
    int GreedyCounts[3] = {0};
    const int GreedyTotal = AllocateBudget(Greedy, 3, 100, GreedyCounts);
    Check(GreedyTotal == 100);
    Check(GreedyCounts[0] + GreedyCounts[1] + GreedyCounts[2] == 100);

    FBudgetRequest Broken[3] = {{-1.0, -5, -9}, {0.0, 10, 0}, {2.0, 4, 99}};
    int BrokenCounts[3] = {0};
    const int BrokenTotal = AllocateBudget(Broken, 3, 6, BrokenCounts);
    Check(BrokenTotal <= 6);
    Check(BrokenCounts[0] == 0);                    // a negative request allocates nothing
    Check(BrokenCounts[2] <= 4);                    // the minimum cannot exceed the request

    Check(AllocateBudget(nullptr, 9, 220, Counts) == 0);
    Check(AllocateBudget(Plan, 0, 220, Counts) == 0);
    Check(AllocateBudget(Plan, 9, 0, Counts) == 0);
    Check(AllocateBudget(Plan, 9, -50, Counts) == 0);
    Check(AllocateBudget(Plan, 9, 220, nullptr) == 0);

    FactInt("budgetCap", 220);
    FactInt("budgetAllocatedAtCap", ShippingTotal);
    FactInt("budgetTotalRequested", TotalRequested);
    FactInt("budgetFootPolishAtCap", First[0]);
    FactInt("budgetStepNosingAtCap", First[1]);
    FactInt("budgetRainStreakAtCap", First[2]);
    FactInt("budgetDustRunoffAtCap", First[3]);
    FactInt("budgetWaterStainAtCap", First[4]);
    FactInt("budgetSootAtCap", First[5]);
    FactInt("budgetLichenAtCap", First[6]);
    FactInt("budgetWindDustAtCap", First[7]);
    FactInt("budgetWeatheringAtCap", First[8]);
    FactInt("budgetOversubscribedMinimumsCapHeld", GreedyTotal);
}

// ---------------------------------------------------------------------------

static void WriteJson(const char* Path)
{
    FILE* File = std::fopen(Path, "wb");
    if (!File)
    {
        std::fprintf(stderr, "Could not open %s for writing\n", Path);
        std::exit(2);
    }
    std::fprintf(File, "{\n  \"test\": \"SurfaceWearMathTest\",\n"
                       "  \"header\": \"Plugins/MikdashRuntime/Source/MikdashRuntime/Public/SurfaceWearMath.h\",\n"
                       "  \"scope\": \"Standalone C++ arithmetic only. No Unreal, no map, no decal placement and no "
                       "visual acceptance. Route geometry is read from SourceAssets/architecture-manifest.json; the "
                       "weathering constants are an artistic model for Jerusalem meleke, not a measurement.\",\n"
                       "  \"routeSeed\": 20260908,\n");
    std::fprintf(File, "  \"allPassed\": true,\n  \"checksEvaluated\": %lld,\n  \"measurements\": {\n", CheckCount);
    for (size_t Index = 0; Index < Facts.size(); ++Index)
    {
        std::fprintf(File, "    \"%s\": %s%s\n", Facts[Index].first.c_str(), Facts[Index].second.c_str(),
                     Index + 1 < Facts.size() ? "," : "");
    }
    std::fprintf(File, "  }\n}\n");
    std::fclose(File);
}

int main(int argc, char** argv)
{
    FalloffChecks();
    RouteWearChecks();
    AccumulationChecks();
    StreakChecks();
    WeatheringChecks();
    StoneVariationChecks();
    FadeChecks();
    BudgetChecks();
    if (argc > 1) WriteJson(argv[1]);
    std::cout << "PASS " << CheckCount
              << " checks: path falloff, route traffic convergence, seeded accumulation, "
                 "ledge streak length, weathering and lichen, meleke instance jitter, "
                 "distance fade and the decal budget allocator" << std::endl;
    return 0;
}
