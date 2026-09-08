// Standalone test for ScatterMath.h. No Unreal, no engine, no I/O beyond stdout and an
// optional JSON snapshot path in argv[1].
//
// Compiled and run by:  Scripts/create_vegetation.py --tests
// which writes SourceAssets/vegetation-review/tests.json.
//
// The four contract assertions the vegetation pass depends on:
//   1. minimum spacing holds for every accepted pair;
//   2. exclusion zones are respected, including the Temple Mount enclosure polygon;
//   3. the realised density matches the requested density within tolerance;
//   4. the scatter is bit-identical for a given seed, and different for a different seed.
#include "ScatterMath.h"

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

using namespace MikdashScatter;

// A check that survives /DNDEBUG. The project's standalone harness compiles every test
// twice, debug and release, and a plain assert() would make the release run vacuous, so
// every assertion below is a real runtime comparison in both configurations.
static int Failures = 0;
static int Checks = 0;
static void Check(bool Ok, const char* Expression, int Line)
{
    ++Checks;
    if (!Ok)
    {
        std::printf("FAIL line %d: %s\n", Line, Expression);
        ++Failures;
    }
}
#define CHECK(Expression) Check((Expression), #Expression, __LINE__)

static bool Near(double A, double B, double Tolerance = 1e-9) { return std::abs(A - B) <= Tolerance; }

// Every measured number the test proves, echoed into the JSON snapshot so a reviewer sees
// values rather than the word PASS.
static std::string Snapshot;
static void Record(const char* Key, double Value)
{
    char Line[256];
    std::snprintf(Line, sizeof(Line), "%s  \"%s\": %.6f", Snapshot.empty() ? "" : ",\n", Key, Value);
    Snapshot += Line;
}
static void RecordInt(const char* Key, long long Value)
{
    char Line[256];
    std::snprintf(Line, sizeof(Line), "%s  \"%s\": %lld", Snapshot.empty() ? "" : ",\n", Key, Value);
    Snapshot += Line;
}

// ---------------------------------------------------------------------------
// A synthetic hillside that behaves like the real one: a ridge running north-south at
// x = 0 falling away east and west, a wadi cut into the eastern flank, and a flat shelf.
// 65 x 65 samples at 2500 cm (25 m), i.e. the same cell size as the project DEM.
// ---------------------------------------------------------------------------
static const int GridSize = 65;
static const double GridStep = 2500.0;
static const double GridOrigin = -80000.0;
static std::vector<double> GridHeights;

// The closed form of the synthetic hillside, kept separate from the sampled grid so the
// tests below can compare SampleTerrain against ground truth instead of against a
// hand-guessed constant. Every grid node is TerrainZ evaluated exactly, so a central
// difference taken on TerrainZ at grid spacing is what SampleTerrain must reproduce
// bit for bit.
static double TerrainZ(double X, double Y)
{
    // Ridge crest 80 000 cm (800 m) at x = 0, falling 1 cm per 4 cm of |x|.
    double Z = 80000.0 - std::abs(X) * 0.25;
    // A wadi: a Gaussian notch 4000 cm deep, sigma 12 000 cm, along y = 0, cut into the
    // eastern flank only. Being a Gaussian it is never exactly zero anywhere, which is a
    // property the aspect check below depends on knowing.
    if (X > 10000.0) Z -= 4000.0 * std::exp(-(Y * Y) / (2.0 * 12000.0 * 12000.0));
    // A flat shelf in the far south-west, for the density test.
    if (X < -50000.0 && Y > 40000.0) Z = 60000.0;
    return Z;
}

/** Central difference on the closed form, at the same spacing SampleTerrain uses. */
static void AnalyticGradient(double X, double Y, double& DzDx, double& DzDy)
{
    DzDx = (TerrainZ(X + GridStep, Y) - TerrainZ(X - GridStep, Y)) / (2.0 * GridStep);
    DzDy = (TerrainZ(X, Y + GridStep) - TerrainZ(X, Y - GridStep)) / (2.0 * GridStep);
}

static double AnalyticAspect(double X, double Y)
{
    double DzDx = 0.0, DzDy = 0.0;
    AnalyticGradient(X, Y, DzDx, DzDy);
    double A = RadToDeg(std::atan2(-DzDy, -DzDx));
    if (A < 0.0) A += 360.0;
    return A;
}

static void BuildTerrain()
{
    GridHeights.resize(static_cast<size_t>(GridSize) * GridSize);
    for (int J = 0; J < GridSize; ++J)
    {
        for (int I = 0; I < GridSize; ++I)
        {
            GridHeights[static_cast<size_t>(J) * GridSize + I] =
                TerrainZ(GridOrigin + I * GridStep, GridOrigin + J * GridStep);
        }
    }
}

static HeightField Terrain()
{
    HeightField F;
    F.Heights = GridHeights.data();
    F.Size = GridSize;
    F.StepCm = GridStep;
    F.OriginXCm = GridOrigin;
    F.OriginYCm = GridOrigin;
    return F;
}

// ---------------------------------------------------------------------------
// 1. Terrain sampling, slope, aspect and concavity
// ---------------------------------------------------------------------------
static void TerrainChecks()
{
    const HeightField F = Terrain();
    CHECK(F.Valid());
    CHECK(Near(F.MaxXCm(), GridOrigin + (GridSize - 1) * GridStep));

    // On the western flank the surface rises east at 0.25, i.e. atan(0.25) = 14.036 deg.
    const TerrainSample West = SampleTerrain(F, Vec2{-40000.0, -60000.0});
    CHECK(Near(West.SlopeDegrees, RadToDeg(std::atan(0.25)), 1e-6));
    // Downhill from the western flank points west (-X), bearing 180. The western flank
    // carries no wadi term at all, so this one IS exact.
    CHECK(Near(West.AspectDegrees, 180.0, 1e-6));
    CHECK(Near(West.AspectDegrees, AnalyticAspect(-40000.0, -60000.0), 1e-9));

    // The eastern flank is the interesting case, and the place an earlier version of this
    // test was simply wrong: it asserted the aspect there was 0 to within 1e-6 degrees.
    // It is not, and SampleTerrain is right to say so. The wadi is a Gaussian, so 60 000 cm
    // off its centreline it still contributes a small but real north-south gradient
    // (dz/dy = -7.238e-06), which swings the downhill bearing 0.00166 deg off due east.
    // The honest assertion is against the closed form of the terrain itself.
    const TerrainSample East = SampleTerrain(F, Vec2{40000.0, -60000.0});
    double EastDzDx = 0.0, EastDzDy = 0.0;
    AnalyticGradient(40000.0, -60000.0, EastDzDx, EastDzDy);
    CHECK(Near(East.DzDx, EastDzDx, 1e-12));
    CHECK(Near(East.DzDy, EastDzDy, 1e-12));
    CHECK(Near(East.AspectDegrees, AnalyticAspect(40000.0, -60000.0), 1e-9));
    CHECK(East.AspectDegrees < 0.01);                  // still downhill toward +X, as intended
    CHECK(East.DzDy < 0.0 && East.AspectDegrees > 0.0);// and the wadi tail really does tilt it
    // On the wadi centreline the Gaussian is even in Y, so dz/dy cancels exactly and the
    // bearing IS exactly due east. That is the point where an exact test belongs.
    const TerrainSample Centreline = SampleTerrain(F, Vec2{40000.0, 0.0});
    CHECK(Near(Centreline.DzDy, 0.0, 1e-15));
    CHECK(Near(Centreline.AspectDegrees, 0.0, 1e-12));
    // Crest height.
    CHECK(Near(HeightAt(F, Vec2{0.0, -60000.0}), 80000.0, 1e-6));

    // The wadi floor is concave; the ridge crest, across the fall line, is not.
    CHECK(Concavity(F, Vec2{40000.0, 0.0}) > 0.0);
    CHECK(Concavity(F, Vec2{40000.0, 22000.0}) < 0.0);

    // Hostile input never crashes and never fabricates a height.
    HeightField Bad;
    CHECK(!Bad.Valid());
    CHECK(Near(HeightAt(Bad, Vec2{0, 0}), 0.0));
    CHECK(Near(HeightAt(F, Vec2{std::numeric_limits<double>::quiet_NaN(), 0}), 0.0));
    // Outside the grid clamps to the edge instead of extrapolating to nonsense.
    CHECK(Near(HeightAt(F, Vec2{-1.0e9, 0.0}), HeightAt(F, Vec2{GridOrigin, 0.0}), 1e-6));

    Record("terrain_west_slope_degrees", West.SlopeDegrees);
    Record("terrain_wadi_concavity", Concavity(F, Vec2{40000.0, 0.0}));
    std::printf("terrain: flank slope %.3f deg, aspect %.1f deg, wadi concavity %+.3e\n",
                West.SlopeDegrees, West.AspectDegrees, Concavity(F, Vec2{40000.0, 0.0}));
}

// ---------------------------------------------------------------------------
// 2. Band filtering: altitude, slope, aspect, concavity
// ---------------------------------------------------------------------------
static void BandChecks()
{
    const HeightField F = Terrain();

    // An olive band: 68 000 to 83 000 cm altitude, 3 to 30 degrees of slope.
    Band Olive;
    Olive.MinAltitudeCm = 68000.0;
    Olive.MaxAltitudeCm = 83000.0;
    Olive.MinSlopeDegrees = 3.0;
    Olive.MaxSlopeDegrees = 30.0;

    CHECK(InBand(Olive, SampleTerrain(F, Vec2{-30000.0, -60000.0})));    // mid flank
    CHECK(!InBand(Olive, SampleTerrain(F, Vec2{-60000.0, -60000.0})));   // too low (65 000)
    // The shelf is flat (slope 0) and below the band: rejected on both counts.
    const TerrainSample Shelf = SampleTerrain(F, Vec2{-70000.0, 60000.0});
    CHECK(Shelf.SlopeDegrees < 3.0);
    CHECK(!InBand(Olive, Shelf));

    // Hard limits give weight 0 outside and 1 inside with no feather.
    CHECK(Near(BandWeight(Olive, SampleTerrain(F, Vec2{-30000.0, -60000.0})), 1.0));
    CHECK(Near(BandWeight(Olive, SampleTerrain(F, Vec2{-60000.0, -60000.0})), 0.0));

    // Feathering makes the edge a ramp, not a wall.
    Band Feathered = Olive;
    Feathered.AltitudeFeatherCm = 4000.0;
    const double AtEdge = BandWeight(Feathered, SampleTerrain(F, Vec2{-46000.0, -60000.0}));   // 68 500 cm
    CHECK(AtEdge > 0.0 && AtEdge < 1.0);

    // Aspect preference: carob wants the sunny face. On this terrain "downhill toward +X"
    // is bearing 0 and "downhill toward -X" is 180.
    Band Carob = Olive;
    Carob.PreferredAspectDegrees = 0.0;
    Carob.AspectWeight = 0.9;
    const double Facing = BandWeight(Carob, SampleTerrain(F, Vec2{30000.0, -60000.0}));
    const double Away = BandWeight(Carob, SampleTerrain(F, Vec2{-30000.0, -60000.0}));
    CHECK(Facing > 0.9 && Away < 0.15 && Facing > Away * 5.0);

    // Concavity preference puts more growth in the wadi than on the shoulder beside it.
    //
    // The trap here, which an earlier version of this test fell into: the wadi is cut
    // 4000 cm deep, so its floor at (40 000, 0) sits at 66 000 cm -- BELOW the olive
    // band's 68 000 cm floor. Reusing the olive band unchanged made the wadi score 0 on
    // altitude before concavity was ever consulted, and the comparison measured nothing.
    // BandWeight was right; the band was wrong. Both facts are now asserted.
    const TerrainSample WadiFloor = SampleTerrain(F, Vec2{40000.0, 0.0});
    const TerrainSample Shoulder = SampleTerrain(F, Vec2{40000.0, 22000.0});
    CHECK(Near(WadiFloor.HeightCm, 66000.0, 1e-6));
    CHECK(WadiFloor.HeightCm < Olive.MinAltitudeCm);
    CHECK(Near(BandWeight(Olive, WadiFloor), 0.0));      // altitude vetoes it, as it should

    // A species whose range actually reaches the wadi floor. Everything else is the olive
    // band, so the only difference between the two points is the concavity term.
    Band Wadi = Olive;
    Wadi.MinAltitudeCm = 60000.0;
    Wadi.ConcavityWeight = 0.8;
    CHECK(InBand(Wadi, WadiFloor) && InBand(Wadi, Shoulder));
    CHECK(Concavity(F, Vec2{40000.0, 0.0}) > 0.0);       // concave floor
    CHECK(Concavity(F, Vec2{40000.0, 22000.0}) < 0.0);   // convex shoulder
    const double InWadi = BandWeight(Wadi, WadiFloor, Concavity(F, Vec2{40000.0, 0.0}));
    const double OnShoulder = BandWeight(Wadi, Shoulder, Concavity(F, Vec2{40000.0, 22000.0}));
    CHECK(InWadi > OnShoulder);
    // The weighting spans the full declared range: saturated wet ground keeps weight 1,
    // dry convex ground is cut to 1 - ConcavityWeight.
    CHECK(Near(InWadi, 1.0, 1e-9));
    CHECK(Near(OnShoulder, 1.0 - Wadi.ConcavityWeight, 1e-9));

    Record("band_feathered_edge_weight", AtEdge);
    Record("band_aspect_facing_weight", Facing);
    Record("band_aspect_away_weight", Away);
    Record("band_wadi_weight", InWadi);
    Record("band_shoulder_weight", OnShoulder);
    std::printf("bands: feather edge %.3f, aspect facing %.3f vs away %.3f, wadi %.3f vs shoulder %.3f\n",
                AtEdge, Facing, Away, InWadi, OnShoulder);
}

// ---------------------------------------------------------------------------
// 3. Exclusion primitives, including a non-convex enclosure polygon
// ---------------------------------------------------------------------------
// A deliberately non-convex ring, so the containment test is proved to be a real ray cast
// and not a bounding box: an L covering the same quadrant shape the Mount enclosure has
// where the Kotel plaza notches into it.
static const Vec2 Enclosure[6] = {
    {-21000.0, -25000.0}, {15000.0, -25000.0}, {15000.0, 0.0},
    {0.0, 0.0}, {0.0, 26000.0}, {-21000.0, 26000.0}};

static const ExclusionCircle Circles[2] = {{50000.0, 50000.0, 900.0}, {-60000.0, 20000.0, 400.0}};
static const ExclusionBox Boxes[1] = {{20000.0, -70000.0, 26000.0, -64000.0, 500.0}};
static const ExclusionCapsule Capsules[1] = {{-70000.0, -70000.0, 70000.0, -70000.0, 800.0}};
static const ExclusionPolygon Polygons[1] = {{0, 6, 1500.0}};

static ExclusionSet MakeExclusions()
{
    ExclusionSet S;
    S.Circles = Circles; S.CircleCount = 2;
    S.Boxes = Boxes; S.BoxCount = 1;
    S.Capsules = Capsules; S.CapsuleCount = 1;
    S.Polygons = Polygons; S.PolygonCount = 1;
    S.PolygonPoints = Enclosure; S.PolygonPointCount = 6;
    return S;
}

static void ExclusionChecks()
{
    // Ray cast, not a bounding box: the notch at (+7500, +13000) is inside the L's AABB
    // but outside the ring, and must NOT be excluded by the polygon.
    CHECK(PointInPolygon(Enclosure, 6, Vec2{-10000.0, -10000.0}));
    CHECK(PointInPolygon(Enclosure, 6, Vec2{10000.0, -10000.0}));
    CHECK(PointInPolygon(Enclosure, 6, Vec2{-10000.0, 13000.0}));
    CHECK(!PointInPolygon(Enclosure, 6, Vec2{7500.0, 13000.0}));       // the notch
    CHECK(!PointInPolygon(Enclosure, 6, Vec2{40000.0, 40000.0}));
    // Degenerate and non-finite input contains nothing and does not crash.
    CHECK(!PointInPolygon(nullptr, 6, Vec2{0, 0}));
    CHECK(!PointInPolygon(Enclosure, 2, Vec2{0, 0}));
    CHECK(!PointInPolygon(Enclosure, 6, Vec2{std::numeric_limits<double>::quiet_NaN(), 0}));

    CHECK(Near(DistanceToPolygonEdge(Enclosure, 6, Vec2{-21000.0 - 700.0, 0.0}), 700.0, 1e-6));
    // The 1500 cm margin catches a point just outside the west wall line.
    CHECK(PointInPolygonWithMargin(Enclosure, 6, Vec2{-22000.0, 0.0}, 1500.0));
    CHECK(!PointInPolygonWithMargin(Enclosure, 6, Vec2{-23000.0, 0.0}, 1500.0));

    const ExclusionSet S = MakeExclusions();
    CHECK(IsExcluded(S, Vec2{-10000.0, -10000.0}));                    // inside the enclosure
    CHECK(IsExcluded(S, Vec2{50600.0, 50000.0}));                      // inside a circle
    CHECK(!IsExcluded(S, Vec2{51000.0, 50000.0}));                     // 1000 > 900 radius
    CHECK(IsExcluded(S, Vec2{51000.0, 50000.0}, 200.0));               // crown radius reaches it
    CHECK(IsExcluded(S, Vec2{23000.0, -67000.0}));                     // inside a box
    CHECK(IsExcluded(S, Vec2{19700.0, -67000.0}));                     // inside the box margin
    CHECK(!IsExcluded(S, Vec2{19000.0, -67000.0}));
    CHECK(IsExcluded(S, Vec2{0.0, -70500.0}));                         // inside the road capsule
    CHECK(!IsExcluded(S, Vec2{0.0, -69000.0}));
    CHECK(IsExcluded(S, Vec2{std::numeric_limits<double>::quiet_NaN(), 0.0}));
    // A malformed ring is refused (excludes everything) rather than silently ignored: the
    // failure mode of a bad enclosure polygon must be "no trees", never "trees in the Azarah".
    ExclusionPolygon Broken[1] = {{0, 6, 0.0}};
    ExclusionSet BadSet;
    BadSet.Polygons = Broken; BadSet.PolygonCount = 1;
    BadSet.PolygonPoints = Enclosure; BadSet.PolygonPointCount = 3;   // range overruns
    CHECK(IsExcluded(BadSet, Vec2{1.0e6, 1.0e6}));

    // An empty set excludes nothing.
    ExclusionSet Empty;
    CHECK(!IsExcluded(Empty, Vec2{0.0, 0.0}));
    std::printf("exclusion: L-notch not excluded, %d primitives honoured, malformed ring refuses everything\n", 5);
}

// ---------------------------------------------------------------------------
// 4. Poisson disc: minimum spacing and saturation
// ---------------------------------------------------------------------------
static void PoissonChecks()
{
    ScatterRequest R;
    R.MinXCm = 0.0; R.MinYCm = 0.0; R.MaxXCm = 40000.0; R.MaxYCm = 40000.0;
    R.MinSpacingCm = 600.0;
    R.Seed = 20260908u;

    const std::vector<Vec2> Points = PoissonDisc(R);
    CHECK(Points.size() > 1000);

    double Worst = 1.0e300;
    for (size_t I = 1; I < Points.size(); ++I)
    {
        for (size_t J = 0; J < I; ++J) Worst = std::min(Worst, DistanceSquared(Points[I], Points[J]));
        CHECK(Points[I].X >= R.MinXCm && Points[I].X < R.MaxXCm);
        CHECK(Points[I].Y >= R.MinYCm && Points[I].Y < R.MaxYCm);
    }
    Worst = std::sqrt(Worst);
    CHECK(Worst >= R.MinSpacingCm - 1e-6);

    // Saturation. The reference is the hexagonal ideal, 2 / (sqrt(3) r^2) points per unit
    // area -- the densest possible packing at this spacing.
    //
    // An earlier version of this test demanded more than 0.55 of that ideal and failed at
    // 0.539. The sampler is not at fault: dart-throwing cannot reach hexagonal packing.
    // Random sequential adsorption jams at a disc packing fraction of about 0.547 against
    // hexagonal 0.9069, i.e. 0.60 of the ideal, and Bridson with a finite k stops short of
    // even that. Measured against an independent reference implementation of the same
    // algorithm driven by std::mt19937 instead of this header's hash, over five seeds:
    //     k = 10  ->  0.502 (reference 0.502)
    //     k = 30  ->  0.539 (reference 0.540)
    //     k = 64  ->  0.561 (reference 0.562)
    // The hash stream and a real RNG agree to 0.2%, so the number below is the algorithm's
    // behaviour and not a defect in the hashing. The window is tight on purpose: a change
    // that quietly degraded the sampler would fall out of the bottom of it.
    const double Ideal = 2.0 / (std::sqrt(3.0) * R.MinSpacingCm * R.MinSpacingCm) * 40000.0 * 40000.0;
    const double Fraction = Points.size() / Ideal;
    CHECK(Fraction > 0.52 && Fraction < 0.56);

    // More candidates per point means a denser set, monotonically, and k is honoured.
    ScatterRequest Sparse = R; Sparse.CandidatesPerPoint = 10;
    ScatterRequest Dense = R;  Dense.CandidatesPerPoint = 64;
    const size_t SparseCount = PoissonDisc(Sparse).size();
    const size_t DenseCount = PoissonDisc(Dense).size();
    CHECK(SparseCount < Points.size() && Points.size() < DenseCount);
    CHECK(static_cast<double>(SparseCount) / Ideal > 0.48);
    CHECK(static_cast<double>(DenseCount) / Ideal < 0.60);
    // k is clamped, not trusted: a hostile value neither hangs nor throws.
    ScatterRequest Silly = R; Silly.CandidatesPerPoint = -5;
    CHECK(!PoissonDisc(Silly).empty());
    Silly.CandidatesPerPoint = 1000000;
    CHECK(!PoissonDisc(Silly).empty());

    // Degenerate requests return nothing rather than looping or allocating wildly.
    ScatterRequest Bad = R;
    Bad.MaxXCm = Bad.MinXCm;
    CHECK(PoissonDisc(Bad).empty());
    Bad = R; Bad.MinSpacingCm = 0.0;
    CHECK(PoissonDisc(Bad).empty());
    Bad = R; Bad.MinSpacingCm = 0.001;   // would need a 5.7e11-cell grid: refused
    CHECK(PoissonDisc(Bad).empty());

    RecordInt("poisson_points", static_cast<long long>(Points.size()));
    Record("poisson_min_spacing_cm", Worst);
    Record("poisson_saturation_fraction_of_hex_ideal", Fraction);
    std::printf("poisson: %zu points, closest pair %.3f cm (asked %.0f), %.1f%% of the hexagonal ideal\n",
                Points.size(), Worst, R.MinSpacingCm, Fraction * 100.0);
}

// ---------------------------------------------------------------------------
// 5. The full Scatter(): spacing, exclusion, density, determinism
// ---------------------------------------------------------------------------
static std::vector<InstanceTransform> RunScatter(uint32_t Seed, double Density, bool UseExclusions,
                                                 ScatterStats* Stats)
{
    static const ExclusionSet Set = MakeExclusions();
    const HeightField F = Terrain();

    ScatterRequest R;
    R.MinXCm = -78000.0; R.MinYCm = -78000.0; R.MaxXCm = 78000.0; R.MaxYCm = 78000.0;
    R.MinSpacingCm = 900.0;
    R.DensityPer100SqM = Density;
    R.Seed = Seed;

    ScatterFilters Filters;
    Filters.Terrain = &F;
    Filters.SpeciesBand.MinAltitudeCm = 55000.0;
    Filters.SpeciesBand.MaxAltitudeCm = 85000.0;
    Filters.SpeciesBand.MaxSlopeDegrees = 35.0;
    Filters.Exclusions = UseExclusions ? &Set : nullptr;
    Filters.CrownRadiusCm = 250.0;
    Filters.Jitter.ScaleMin = 0.8;
    Filters.Jitter.ScaleMax = 1.3;
    Filters.Jitter.HeightRatioMin = 0.9;
    Filters.Jitter.HeightRatioMax = 1.15;
    Filters.Jitter.MaxTiltDegrees = 6.0;
    Filters.Jitter.DownhillTiltFraction = 0.35;
    return Scatter(R, Filters, Stats);
}

static void ScatterSpacingAndExclusionChecks()
{
    static const ExclusionSet Set = MakeExclusions();
    ScatterStats Stats;
    const std::vector<InstanceTransform> Instances = RunScatter(20260908u, 0.35, true, &Stats);
    CHECK(Instances.size() > 500);

    // (1) MINIMUM SPACING holds for every accepted pair.
    const double Closest = MinimumSpacingFast(Instances, 900.0);
    CHECK(Closest >= 900.0 - 1e-6);
    // The fast grid form must agree with the honest quadratic form on a subset.
    std::vector<InstanceTransform> Subset(Instances.begin(), Instances.begin() + 400);
    CHECK(Near(MinimumSpacing(Subset), MinimumSpacingFast(Subset, 900.0), 1e-9));

    // (2) EXCLUSION ZONES are respected -- with the species crown radius included, which
    // is the test that matters: a trunk 200 cm outside the enclosure whose crown overhangs
    // it is still refused.
    int InsideEnclosure = 0;
    double NearestToEnclosureEdge = 1.0e300;
    for (const InstanceTransform& T : Instances)
    {
        const Vec2 P{T.XCm, T.YCm};
        CHECK(!IsExcluded(Set, P, 250.0));
        if (PointInPolygon(Enclosure, 6, P)) ++InsideEnclosure;
        if (!PointInPolygon(Enclosure, 6, P))
            NearestToEnclosureEdge = std::min(NearestToEnclosureEdge, DistanceToPolygonEdge(Enclosure, 6, P));
        CHECK(std::isfinite(T.XCm) && std::isfinite(T.YCm) && std::isfinite(T.ZCm));
    }
    CHECK(InsideEnclosure == 0);
    // Nobody stands closer than the polygon margin plus the crown radius.
    CHECK(NearestToEnclosureEdge >= 1500.0 + 250.0 - 1e-6);

    // Band filtering actually bit.
    CHECK(Stats.RejectedByBand > 0);
    CHECK(Stats.RejectedByExclusion > 0);

    RecordInt("scatter_instances", static_cast<long long>(Instances.size()));
    Record("scatter_min_spacing_cm", Closest);
    RecordInt("scatter_inside_enclosure", InsideEnclosure);
    Record("scatter_nearest_to_enclosure_edge_cm", NearestToEnclosureEdge);
    RecordInt("scatter_rejected_by_band", Stats.RejectedByBand);
    RecordInt("scatter_rejected_by_exclusion", Stats.RejectedByExclusion);
    std::printf("scatter: %zu instances, closest pair %.2f cm, 0 inside the enclosure, nearest %.0f cm outside it\n",
                Instances.size(), Closest, NearestToEnclosureEdge);
}

static void DensityChecks()
{
    // (3) DENSITY MATCHES THE REQUEST. Measured over an open rectangle with no exclusions
    // and a band that accepts the whole rectangle, so nothing but the density cap thins it.
    const HeightField F = Terrain();
    const double Requested[3] = {0.05, 0.25, 1.20};
    double WorstError = 0.0;
    for (int Case = 0; Case < 3; ++Case)
    {
        ScatterRequest R;
        R.MinXCm = -40000.0; R.MinYCm = -40000.0; R.MaxXCm = 40000.0; R.MaxYCm = 40000.0;
        R.MinSpacingCm = 400.0;
        R.DensityPer100SqM = Requested[Case];
        R.Seed = 4400u + static_cast<uint32_t>(Case);

        ScatterFilters Filters;
        Filters.Terrain = &F;
        Filters.SpeciesBand.MinSlopeDegrees = 0.0;
        Filters.SpeciesBand.MaxSlopeDegrees = 90.0;     // accepts everything
        ScatterStats Stats;
        const std::vector<InstanceTransform> Instances = Scatter(R, Filters, &Stats);

        const double Area = (R.MaxXCm - R.MinXCm) * (R.MaxYCm - R.MinYCm);
        const double Realised = Instances.size() * SquareCmPer100SqM / Area;
        const double Error = std::abs(Realised - Requested[Case]) / Requested[Case];
        WorstError = std::max(WorstError, Error);
        // Within 1%: the only loss is integer rounding of the target count.
        CHECK(Error < 0.01);
        CHECK(!Stats.SaturationLimited);
        CHECK(Near(Stats.RealisedDensityPer100SqM, Realised, 1e-9));
        CHECK(static_cast<int>(Instances.size()) == Stats.AcceptedCount);
        // Spacing survives the thinning.
        CHECK(MinimumSpacingFast(Instances, 400.0) >= 400.0 - 1e-6);
        std::printf("density: asked %.3f/100 m2, got %.4f (%.3f%% error), %zu instances\n",
                    Requested[Case], Realised, Error * 100.0, Instances.size());
    }

    // Asking for more than the disc radius can hold is reported, not silently delivered.
    ScatterRequest Greedy;
    Greedy.MinXCm = 0.0; Greedy.MinYCm = 0.0; Greedy.MaxXCm = 20000.0; Greedy.MaxYCm = 20000.0;
    Greedy.MinSpacingCm = 1500.0;
    Greedy.DensityPer100SqM = 50.0;      // far beyond saturation at 15 m spacing
    Greedy.Seed = 7u;
    ScatterFilters Plain;
    ScatterStats GreedyStats;
    const std::vector<InstanceTransform> Few = Scatter(Greedy, Plain, &GreedyStats);
    CHECK(GreedyStats.SaturationLimited);
    CHECK(static_cast<int>(Few.size()) == GreedyStats.SaturatedCount);
    CHECK(GreedyStats.RealisedDensityPer100SqM < Greedy.DensityPer100SqM);

    // A zero or negative request yields nothing rather than a full saturated set.
    ScatterRequest Zero = Greedy;
    Zero.DensityPer100SqM = 1e-9;
    CHECK(Scatter(Zero, Plain, nullptr).empty());

    // MaxPoints caps hard.
    ScatterRequest Capped = Greedy;
    Capped.DensityPer100SqM = 0.0;
    Capped.MaxPoints = 25;
    CHECK(Scatter(Capped, Plain, nullptr).size() == 25);

    Record("density_worst_relative_error", WorstError);
    RecordInt("density_saturation_limited_count", GreedyStats.SaturatedCount);
}

static void DeterminismChecks()
{
    // (4) DETERMINISTIC FOR A GIVEN SEED, and genuinely different for another.
    ScatterStats StatsA, StatsB, StatsC;
    const std::vector<InstanceTransform> A = RunScatter(20260908u, 0.35, true, &StatsA);
    const std::vector<InstanceTransform> B = RunScatter(20260908u, 0.35, true, &StatsB);
    const std::vector<InstanceTransform> C = RunScatter(20260909u, 0.35, true, &StatsC);

    CHECK(A.size() == B.size());
    CHECK(!A.empty());
    for (size_t I = 0; I < A.size(); ++I)
    {
        // Bit-identical, not merely close: the same seed must give the same map on every
        // run, so a receipt's instance count can be re-derived offline.
        CHECK(std::memcmp(&A[I], &B[I], sizeof(InstanceTransform)) == 0);
    }
    CHECK(StatsA.RejectedByBand == StatsB.RejectedByBand);
    CHECK(StatsA.RejectedByExclusion == StatsB.RejectedByExclusion);

    size_t Same = 0;
    const size_t Compare = std::min(A.size(), C.size());
    for (size_t I = 0; I < Compare; ++I)
    {
        if (std::memcmp(&A[I], &C[I], sizeof(InstanceTransform)) == 0) ++Same;
    }
    CHECK(Same * 100 < Compare);   // under 1% coincidence between different seeds

    // The pure hash helpers are stable and in range.
    for (uint32_t I = 0; I < 5000; ++I)
    {
        const double U = HashUnit(99u, I, 3u);
        CHECK(U >= 0.0 && U < 1.0);
        CHECK(Near(U, HashUnit(99u, I, 3u)));
        const double R = HashRange(99u, I, 4u, -7.0, 11.0);
        CHECK(R >= -7.0 && R <= 11.0);
        const double Bell = HashBell(99u, I, 5u);
        CHECK(Bell >= -3.0 && Bell <= 3.0);
    }

    RecordInt("determinism_instances", static_cast<long long>(A.size()));
    RecordInt("determinism_identical_across_seeds", static_cast<long long>(Same));
    std::printf("determinism: %zu instances identical across two runs of seed 20260908; %zu of %zu coincide with seed 20260909\n",
                A.size(), Same, Compare);
}

// ---------------------------------------------------------------------------
// 6. Clustering, terracing and per-instance jitter
// ---------------------------------------------------------------------------
static void ClusterChecks()
{
    ClusterField F;
    F.Count = 12;
    F.RadiusCm = 6000.0;
    F.Strength = 0.9;
    F.MinXCm = -40000.0; F.MinYCm = -40000.0; F.MaxXCm = 40000.0; F.MaxYCm = 40000.0;
    F.Seed = 555u;

    CHECK(Near(ClusterWeight(F, ClusterCentre(F, 0)), 1.0, 1e-9));
    // Well away from every centre the weight falls to 1 - Strength.
    double Lowest = 1.0;
    for (int I = 0; I < 4000; ++I)
    {
        const Vec2 P{HashRange(7u, static_cast<uint32_t>(I), 1u, F.MinXCm, F.MaxXCm),
                     HashRange(7u, static_cast<uint32_t>(I), 2u, F.MinYCm, F.MaxYCm)};
        const double W = ClusterWeight(F, P);
        CHECK(W >= 1.0 - F.Strength - 1e-9 && W <= 1.0 + 1e-9);
        Lowest = std::min(Lowest, W);
    }
    CHECK(Near(Lowest, 1.0 - F.Strength, 1e-6));

    // Disabled clustering is exactly 1 everywhere.
    ClusterField Off;
    CHECK(Near(ClusterWeight(Off, Vec2{123.0, 456.0}), 1.0));

    // Clustering only removes points, so spacing survives and the count falls.
    const HeightField Terr = Terrain();
    ScatterRequest R;
    R.MinXCm = -40000.0; R.MinYCm = -40000.0; R.MaxXCm = 40000.0; R.MaxYCm = 40000.0;
    R.MinSpacingCm = 700.0;
    R.Seed = 31u;
    ScatterFilters Plain;
    Plain.Terrain = &Terr;
    Plain.SpeciesBand.MaxSlopeDegrees = 90.0;
    ScatterFilters Clustered = Plain;
    Clustered.Clusters = F;
    const size_t Uniform = Scatter(R, Plain, nullptr).size();
    const std::vector<InstanceTransform> Grouped = Scatter(R, Clustered, nullptr);
    CHECK(Grouped.size() < Uniform);
    CHECK(MinimumSpacingFast(Grouped, 700.0) >= 700.0 - 1e-6);

    RecordInt("cluster_uniform_count", static_cast<long long>(Uniform));
    RecordInt("cluster_grouped_count", static_cast<long long>(Grouped.size()));
    std::printf("clusters: %zu uniform -> %zu clustered, spacing intact, floor weight %.3f\n",
                Uniform, Grouped.size(), Lowest);
}

static void TerraceChecks()
{
    const HeightField F = Terrain();
    TerraceField T;
    T.Enabled = true;
    T.BenchWidthCm = 500.0;
    T.Snap = 1.0;
    T.JitterFraction = 0.0;
    T.Seed = 2u;

    // On the western flank the fall line is -X, so snapping quantises X to 500 cm.
    const TerrainSample S = SampleTerrain(F, Vec2{-30000.0, -60000.0});
    for (int I = 0; I < 200; ++I)
    {
        const Vec2 P{-30000.0 + I * 37.0, -60000.0 + I * 11.0};
        const Vec2 Q = SnapToTerrace(T, S, P, static_cast<uint32_t>(I));
        const double Along = -Q.X;                          // downhill is -X here
        CHECK(Near(std::fmod(std::abs(Along), 500.0), 0.0, 1e-6)
               || Near(std::fmod(std::abs(Along), 500.0), 500.0, 1e-6));
        CHECK(Near(Q.Y, P.Y, 1e-9));                        // moved along the fall line only
        CHECK(std::abs(Q.X - P.X) <= 250.0 + 1e-6);         // never further than half a bench
    }

    // Flat ground is left alone: terraces exist because of the fall.
    const TerrainSample Flat = SampleTerrain(F, Vec2{-70000.0, 60000.0});
    const Vec2 OnFlat{-70123.0, 60321.0};
    CHECK(Near(SnapToTerrace(T, Flat, OnFlat, 0).X, OnFlat.X));
    // Disabled or zero-snap leaves the point untouched.
    TerraceField Off = T;
    Off.Enabled = false;
    CHECK(Near(SnapToTerrace(Off, S, OnFlat, 0).X, OnFlat.X));

    // Jitter stays inside its declared fraction of the bench width.
    TerraceField Jittered = T;
    Jittered.JitterFraction = 0.15;
    for (int I = 0; I < 500; ++I)
    {
        const Vec2 P{-30000.0 + I * 13.0, -60000.0};
        const Vec2 Q = SnapToTerrace(Jittered, S, P, static_cast<uint32_t>(I));
        const double Offset = std::abs(-Q.X - std::floor(-Q.X / 500.0 + 0.5) * 500.0);
        CHECK(Offset <= 0.15 * 500.0 + 1e-6);
    }
    std::printf("terraces: 500 cm benches quantised along the fall line, flat ground untouched\n");
}

static void JitterChecks()
{
    const HeightField F = Terrain();
    const TerrainSample S = SampleTerrain(F, Vec2{-30000.0, -60000.0});
    JitterRange J;
    J.ScaleMin = 0.75; J.ScaleMax = 1.35;
    J.HeightRatioMin = 0.9; J.HeightRatioMax = 1.2;
    J.YawMinDegrees = 0.0; J.YawMaxDegrees = 360.0;
    J.MaxTiltDegrees = 8.0;
    J.DownhillTiltFraction = 0.0;

    double MinScale = 1e9, MaxScale = -1e9, MaxTilt = 0.0, YawSum = 0.0;
    const int N = 20000;
    for (int I = 0; I < N; ++I)
    {
        const InstanceTransform T = MakeInstance(Vec2{0.0, 0.0}, 0.0, S, J, 8080u, static_cast<uint32_t>(I));
        CHECK(T.ScaleX >= J.ScaleMin - 1e-12 && T.ScaleX <= J.ScaleMax + 1e-12);
        CHECK(Near(T.ScaleX, T.ScaleY));
        const double Ratio = T.ScaleZ / T.ScaleX;
        CHECK(Ratio >= J.HeightRatioMin - 1e-9 && Ratio <= J.HeightRatioMax + 1e-9);
        CHECK(T.YawDegrees >= 0.0 && T.YawDegrees <= 360.0);
        const double Tilt = std::sqrt(T.PitchDegrees * T.PitchDegrees + T.RollDegrees * T.RollDegrees);
        CHECK(Tilt <= J.MaxTiltDegrees + 1e-9);
        MinScale = std::min(MinScale, T.ScaleX);
        MaxScale = std::max(MaxScale, T.ScaleX);
        MaxTilt = std::max(MaxTilt, Tilt);
        YawSum += T.YawDegrees;
        // Same seed and index always gives the same pose.
        const InstanceTransform Again = MakeInstance(Vec2{0.0, 0.0}, 0.0, S, J, 8080u, static_cast<uint32_t>(I));
        CHECK(std::memcmp(&T, &Again, sizeof(InstanceTransform)) == 0);
    }
    // Yaw is uniform over the full circle, so its mean is near 180.
    CHECK(std::abs(YawSum / N - 180.0) < 4.0);
    // The scale bell actually spans most of its range.
    CHECK(MinScale < J.ScaleMin + 0.06 && MaxScale > J.ScaleMax - 0.06);

    // A downhill-biased lean really does point downhill (bearing 180 on the western flank),
    // i.e. pitch strongly negative, roll near zero.
    JitterRange Downhill = J;
    Downhill.DownhillTiltFraction = 1.0;
    double PitchSum = 0.0, RollSum = 0.0;
    for (int I = 0; I < 2000; ++I)
    {
        const InstanceTransform T = MakeInstance(Vec2{0.0, 0.0}, 0.0, S, Downhill, 9090u, static_cast<uint32_t>(I));
        PitchSum += T.PitchDegrees;
        RollSum += T.RollDegrees;
    }
    CHECK(PitchSum / 2000.0 < -3.0);
    CHECK(std::abs(RollSum / 2000.0) < 0.5);

    // No tilt requested means exactly upright.
    JitterRange Upright = J;
    Upright.MaxTiltDegrees = 0.0;
    const InstanceTransform Straight = MakeInstance(Vec2{0.0, 0.0}, 0.0, S, Upright, 1u, 1u);
    CHECK(Near(Straight.PitchDegrees, 0.0) && Near(Straight.RollDegrees, 0.0));

    Record("jitter_min_scale", MinScale);
    Record("jitter_max_scale", MaxScale);
    Record("jitter_max_tilt_degrees", MaxTilt);
    std::printf("jitter: scale %.3f..%.3f over %d draws, max tilt %.2f deg, downhill lean mean pitch %.2f deg\n",
                MinScale, MaxScale, N, MaxTilt, PitchSum / 2000.0);
}

// ---------------------------------------------------------------------------
// 7. The draw budget arithmetic that justifies the instance cap
// ---------------------------------------------------------------------------
static void BudgetChecks()
{
    // The shipped tree LOD ladder: LOD0 near, LOD1, LOD2, then a billboard.
    const LodStep Tree[4] = {{0.0, 3000}, {4000.0, 900}, {12000.0, 260}, {30000.0, 2}};
    CHECK(LodForDistance(Tree, 4, 0.0) == 0);
    CHECK(LodForDistance(Tree, 4, 3999.0) == 0);
    CHECK(LodForDistance(Tree, 4, 4000.0) == 1);
    CHECK(LodForDistance(Tree, 4, 29999.0) == 2);
    CHECK(LodForDistance(Tree, 4, 1.0e6) == 3);
    CHECK(LodForDistance(nullptr, 4, 100.0) == 0);
    CHECK(LodForDistance(Tree, 0, 100.0) == 0);

    // 24 000 trees over the vegetated part of the 6.4 x 6.4 km terrain, culled at 60 000 cm,
    // with a third of the disc actually in frustum and unoccluded.
    const double AreaSqCm = 6.4e5 * 6.4e5;
    const double Triangles = ExpectedTrianglesPerFrame(24000, AreaSqCm, 60000.0, Tree, 4, 1.0 / 3.0);
    CHECK(Triangles > 0.0);
    CHECK(Triangles < 3.5e6);          // the stated 3.5 M-triangle foliage ceiling
    // Doubling the instances doubles the triangles: the estimate is linear, as claimed.
    CHECK(Near(ExpectedTrianglesPerFrame(48000, AreaSqCm, 60000.0, Tree, 4, 1.0 / 3.0), Triangles * 2.0, 1.0));
    // Nothing visible costs nothing.
    CHECK(Near(ExpectedTrianglesPerFrame(24000, AreaSqCm, 60000.0, Tree, 4, 0.0), 0.0));
    CHECK(Near(ExpectedTrianglesPerFrame(0, AreaSqCm, 60000.0, Tree, 4, 1.0), 0.0));

    // Grass: many more instances but a short cull distance, which is why it is affordable.
    const LodStep Grass[2] = {{0.0, 24}, {3000.0, 8}};
    const double GrassTriangles = ExpectedTrianglesPerFrame(120000, AreaSqCm, 8000.0, Grass, 2, 1.0 / 3.0);
    CHECK(GrassTriangles < 1.0e6);

    Record("budget_tree_triangles_per_frame", Triangles);
    Record("budget_grass_triangles_per_frame", GrassTriangles);
    Record("budget_total_triangles_per_frame", Triangles + GrassTriangles);
    std::printf("budget: 24000 trees %.0f tris/frame + 120000 grass %.0f tris/frame = %.2f M\n",
                Triangles, GrassTriangles, (Triangles + GrassTriangles) / 1.0e6);
}

int main(int Argc, char** Argv)
{
    BuildTerrain();
    TerrainChecks();
    BandChecks();
    ExclusionChecks();
    PoissonChecks();
    ScatterSpacingAndExclusionChecks();
    DensityChecks();
    DeterminismChecks();
    ClusterChecks();
    TerraceChecks();
    JitterChecks();
    BudgetChecks();

    if (Argc > 1)
    {
        if (std::FILE* Handle = std::fopen(Argv[1], "w"))
        {
            std::fprintf(Handle, "{\n%s\n}\n", Snapshot.c_str());
            std::fclose(Handle);
        }
    }
    std::printf("checks run: %d, failures: %d\n", Checks, Failures);
    if (Failures != 0)
    {
        std::cout << "FAIL: " << Failures << " of " << Checks << " ScatterMath checks failed" << std::endl;
        return 1;
    }
    std::cout << "PASS: terrain sampling, altitude/slope/aspect bands, exclusion primitives, "
                 "Poisson-disc spacing, density match, determinism, clustering, terracing, "
                 "per-instance jitter and the draw budget" << std::endl;
    return 0;
}
