// Standalone test for Public/CameraPathMath.h. No Unreal, no test framework.
//
//   "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
//   cl /nologo /EHsc /W4 /std:c++17 /I<...>\Source\MikdashRuntime\Public CameraPathMathTest.cpp
//   CameraPathMathTest.exe <path to SourceAssets/cinematics-review/tests.json>
//
// Every check records its measured number, not just a pass flag, so the receipt shows
// how much headroom each tolerance actually had.
#define _CRT_SECURE_NO_WARNINGS
#include "CameraPathMath.h"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

using namespace MikdashCamera;

static const double NaNValue = std::numeric_limits<double>::quiet_NaN();
static const double InfValue = std::numeric_limits<double>::infinity();

// ---------------------------------------------------------------------------------
// Tiny receipt writer. Records name, measured value, tolerance and pass for each check.
// ---------------------------------------------------------------------------------
struct Metric
{
    std::string Group;
    std::string Name;
    double Measured = 0;
    double Tolerance = 0;
    std::string Comparison; // "<=", ">=", "=="
    bool bPassed = false;
    std::string Note;
};

static std::vector<Metric> Metrics;
static int Failures = 0;

static bool Record(const char* Group, const char* Name, double Measured, const char* Comparison, double Tolerance, const char* Note)
{
    bool bOk = false;
    if (std::string(Comparison) == "<=") bOk = std::isfinite(Measured) && Measured <= Tolerance;
    else if (std::string(Comparison) == ">=") bOk = std::isfinite(Measured) && Measured >= Tolerance;
    else bOk = std::isfinite(Measured) && std::abs(Measured - Tolerance) <= 1e-12;
    Metrics.push_back({Group, Name, Measured, Tolerance, Comparison, bOk, Note});
    if (!bOk)
    {
        ++Failures;
        std::cerr << "FAIL " << Group << "/" << Name << ": measured " << Measured << " " << Comparison << " " << Tolerance << "\n";
    }
    return bOk;
}

static void RecordFlag(const char* Group, const char* Name, bool bValue, const char* Note)
{
    Metrics.push_back({Group, Name, bValue ? 1.0 : 0.0, 1.0, "==", bValue, Note});
    if (!bValue)
    {
        ++Failures;
        std::cerr << "FAIL " << Group << "/" << Name << "\n";
    }
}

static std::string JsonEscape(const std::string& In)
{
    std::string Out;
    for (std::size_t I = 0; I < In.size(); ++I)
    {
        const char C = In[I];
        if (C == '"' || C == '\\') { Out += '\\'; Out += C; }
        else if (C == '\n') { Out += "\\n"; }
        else { Out += C; }
    }
    return Out;
}

static std::string Number(double V)
{
    if (!std::isfinite(V)) return "null";
    char Buffer[64];
    std::snprintf(Buffer, sizeof(Buffer), "%.12g", V);
    return Buffer;
}

// ---------------------------------------------------------------------------------
// The intro flythrough path, as the release script authors it. Coordinates come from the
// map receipts (see Scripts/release_intro_sequence.spec.json); they are duplicated here
// so the geometry of the real path is tested, not just a synthetic curve.
// ---------------------------------------------------------------------------------
static std::vector<Vec3> IntroControlPoints()
{
    // World frame: +X east, +Y south, +Z up, centimetres. The approach is from the EAST,
    // through the east gate of the 3,000-amah precinct wall: Yechezkel 43:1-4. Every number
    // below is a coordinate recorded in a receipt under SourceAssets/ or a bound read out of
    // SourceAssets/architecture-manifest.json or enclosure-review/precinct-Main50.json; the
    // sources are listed shot by shot in Scripts/release_intro_sequence.spec.json. The path
    // is duplicated here so the geometry of the shipped flythrough is what is exercised.
    return {
        {140000.0, 4200.0, 8600.0},  // over the eastern slope of the Mount of Olives (DEM ~1060,
                                     // modern tops ~1100), looking west down the axis
        {129500.0, 1600.0, 6500.0},  // descending toward the gate
        {122500.0,  300.0, 5300.0},  // settling onto the axis
        {116720.0,    0.0, 4800.0},  // THROUGH the east gate at its module centre: E gate at
                                     // (116900, 0), module X 116549..116900, opening |Y| < 250,
                                     // plinth 3551.4, lintel soffit 6051.4 (precinct-Main50.json,
                                     // geometry-manifest.json SM_EnclosureV2_Gate)
        {111500.0,    0.0, 5000.0},
        {103500.0,    0.0, 6500.0},  // over the Olives ridge; modern tops to 4993 (Modern state)
        { 92000.0,    0.0, 7000.0},
        { 81000.0,    0.0, 7300.0},  // the crest, modern tops 5543
        { 66000.0,    0.0, 5900.0},
        { 50000.0,    0.0, 3800.0},  // out over the Kidron, floor about -6000 at X 26-32 k
        { 34000.0,    0.0, 2900.0},
        { 20000.0,    0.0, 3300.0},  // rising to the Mount platform, deck top 0 to X 14953
        { 12500.0,    0.0, 3950.0},
        {  8300.0,    0.0, 3800.0},  // over the court's east gate; lintel and jamb tops 3300
        {  7300.0,    0.0, 3450.0},  // over the vestibule pillars and palm fronds, top 3346
        {  6200.0,    0.0, 2650.0},  // the dive across the outer court, floor top 300
        {  5000.0,    0.0, 1800.0},
        {  3800.0,    0.0, 1100.0},  // level at the inner eastern vestibule, landings and stairs top 500
        {  2100.0,    0.0,  668.0},  // the visitor's eye at Mikdash_PlayerStart [2100, 0]:
                                     // inner court clear floor top 500 plus 168 eye height
    };
}

// The solid blocks the flythrough must clear, as axis-aligned boxes.
//
// Every box is a conservative cover of real geometry: envelopes of named meshes in
// SourceAssets/architecture-manifest.json, the box decomposition of that manifest's hollow
// unions (source_elements_json, which recomposes to each union's bounds exactly), and the
// precinct wall modules reconstructed from enclosure-review/precinct-Main50.json with the
// same GroundSpan rule the placer uses. Hollow union AABBs themselves are never used: the
// "outer envelope walls" union spans the whole court.
//
// The precinct wall is 1.5 km a side; only the modules the path comes within 5 km of are
// listed. Elsewhere the path is on the axis Y 0, 33 km from the north and south walls and
// 150 km from the west wall, so nothing there can be in the way.
static std::vector<Box> IntroBlockers()
{
    return {
        // -- the Mikdash ----------------------------------------------------------------
        {{-7500, -2540, 425}, {-2382, 2540, 6130}},      // House, its walls and the Golden roof
        {{-7500, -8129, 405}, {-2392, 8129, 3475}},      // west wings, cells and service passages
        {{-8100, 7800, 300}, {8100, 8100, 3425}},        // outer perimeter wall, south band
        {{-8100, -8100, 300}, {8100, -7800, 3425}},      // outer perimeter wall, north band
        {{7800, -8100, 300}, {8100, -250, 3425}},        // outer perimeter wall, east band north of the gate
        {{7800, 250, 300}, {8100, 8100, 3425}},          // outer perimeter wall, east band south of the gate
        {{7800, -250, 2800}, {8100, 250, 3300}},         // court east gate lintel (union decomposition)
        {{-8100, -8100, 300}, {-7800, 8100, 3425}},      // outer perimeter wall, west band
        {{-8100, -8100, -5000}, {8100, 8100, 300}},      // outer court deck and its foundation
        {{-2800, -2800, -5000}, {2800, 2800, 499}},      // inner court podium
        {{-2500, -2500, -5000}, {1575, 2500, 625}},      // raised priest court and Ezras Kohanim floor
        {{-2500, -2800, 625}, {2500, -2500, 3625}},      // inner court wall, north band
        {{-2500, 2500, 625}, {2500, 2800, 3625}},        // inner court wall, south band
        {{2500, -2800, 500}, {2800, -250, 3500}},        // inner eastern gate jamb, north
        {{2500, 250, 500}, {2800, 2800, 3500}},          // inner eastern gate jamb, south
        {{2500, -250, 3000}, {2800, 250, 3500}},         // inner eastern gate lintel
        {{2800, -625, 300}, {3450, 625, 500}},           // inner eastern vestibule, landings and stairs
        {{-2500, -985, 625}, {-1400, 985, 925}},         // Ulam stairs
        {{-800, -800, 625}, {800, 800, 1091}},           // altar, wood on the upper tier at 1091
        // -- the court's east gate, piece by piece (manifest meshes and union boxes) ------
        {{7291, -525, 300}, {7409, -225, 3346}},         // vestibule pillar, collars and palm fronds, north
        {{7291, 225, 300}, {7409, 525, 3346}},           // vestibule pillar, collars and palm fronds, south
        {{7300, -625, 2800}, {7800, 625, 2900}},         // vestibule entablature, over the axis
        {{7400, -625, 300}, {7800, -325, 2800}},         // vestibule wall, north
        {{7400, 325, 300}, {7800, 625, 2800}},           // vestibule wall, south
        {{7782, -282, 300}, {8018, -261, 2840}},         // open gate leaf, north
        {{7782, 261, 300}, {8018, 282, 2840}},           // open gate leaf, south
        {{7772, -8100, 3201}, {7828, -250, 3312}},       // court string course and cornice, west run, north
        {{7772, 250, 3201}, {7828, 8100, 3312}},         // court string course and cornice, west run, south
        {{8072, -8100, 3201}, {8128, -250, 3312}},       // court string course and cornice, east run, north
        {{8072, 250, 3201}, {8128, 8100, 3312}},         // court string course and cornice, east run, south
        {{8100, -2275, 300}, {8900, -375, 700}},         // outer eastern cells, north
        {{8100, 375, 300}, {8900, 2275, 700}},           // outer eastern cells, south
        {{7300, -7800, 2675}, {7800, -600, 2925}},       // raised pavement gallery, east run, north
        {{7300, 600, 2675}, {7800, 7800, 2925}},         // raised pavement gallery, east run, south
        // -- the 3,000-amah precinct wall: east gate and its neighbours (RELEASE_EnclosureV2) --
        {{116549, -780, 2750}, {116900, -250, 6551}},    // E gate pier, north, substructure to lintel top
        {{116549, 250, 2750}, {116900, 780, 6551}},      // E gate pier, south
        {{116549, -250, 6051}, {116900, 250, 6551}},     // E gate lintel over the 500 x 2500 opening
        {{116549, -780, 2750}, {116900, 780, 3551}},     // E gate threshold and substructure
        {{116540, -4400, 4279}, {116900, -3150, 4896}},  // E wall module 23, plinth 4596
        {{116540, -3150, 3904}, {116900, -1900, 4687}},  // E wall module 24, plinth 4387
        {{116540, 1850, 1654}, {116900, 3100, 2586}},    // E wall module 28, plinth 2286
        {{116540, 3100, 1300}, {116900, 4350, 2062}},    // E wall module 29, plinth 1762
    };
}

// ---------------------------------------------------------------------------------
// 1. C1 continuity across every interior control point.
// ---------------------------------------------------------------------------------
static void ContinuityChecks()
{
    // Deliberately uneven spacing: a uniform Catmull-Rom would cusp here.
    std::vector<Vec3> Points = {
        {0, 0, 0}, {1200, 300, 100}, {1350, 1500, 260}, {5000, 1700, 900}, {5100, 5200, 950}, {9000, 5400, 400}};
    SplinePath Path;
    RecordFlag("continuity", "buildSucceeded", Path.Build(Points, 0.5, 64), "centripetal Catmull-Rom, 64 samples per segment");

    double MaxPositionJump = 0.0;
    double MaxDerivativeJump = 0.0;
    double MaxControlPointError = 0.0;
    for (std::size_t I = 1; I + 1 < Path.NumPoints(); ++I)
    {
        const double U = Path.KnotAt(I);
        const double Span = std::min(U - Path.KnotAt(I - 1), Path.KnotAt(I + 1) - U);
        const double E = Span * 1e-9;
        const Vec3 Before = Path.PointAtParam(U - E), After = Path.PointAtParam(U + E);
        // Distance(Before, After) on its own is not a discontinuity measure: it is
        // dominated by the curve's own travel across the probe window, |dP/dU| * 2E,
        // which on this path is several times 1e-6 cm and has nothing to do with C0.
        // Subtracting that travel leaves the jump itself, which for a C0 curve is zero
        // to within the cancellation noise of differencing two coordinates of this size.
        const Vec3 Travel = Path.DerivativeAtParam(U) * (2.0 * E);
        MaxPositionJump = std::max(MaxPositionJump, Distance(After - Before, Travel));

        const Vec3 Da = Path.DerivativeAtParam(U - E), Db = Path.DerivativeAtParam(U + E);
        const double Scale = std::max(Length(Da), 1e-9);
        MaxDerivativeJump = std::max(MaxDerivativeJump, Distance(Da, Db) / Scale);

        // C0 as well: the curve passes exactly through every control point.
        MaxControlPointError = std::max(MaxControlPointError, Distance(Path.PointAtParam(U), Points[I]));
    }
    // C0 at the two ends too.
    MaxControlPointError = std::max(MaxControlPointError, Distance(Path.PointAtParam(Path.MinParam()), Points.front()));
    MaxControlPointError = std::max(MaxControlPointError, Distance(Path.PointAtParam(Path.MaxParam()), Points.back()));

    Record("continuity", "maxPositionJumpAtInteriorKnotsCm", MaxPositionJump, "<=", 1e-6,
           "C0 across segment joins, measured as the residual after the smooth travel is removed");
    Record("continuity", "maxRelativeDerivativeJumpAtInteriorKnots", MaxDerivativeJump, "<=", 1e-6,
           "C1: one-sided dP/dU limits agree; the two segments share the tangent (P[i+1]-P[i-1])/(u[i+1]-u[i-1])");
    Record("continuity", "maxControlPointInterpolationErrorCm", MaxControlPointError, "<=", 1e-9,
           "the curve interpolates its control points, ends included");

    // The tangent never reverses or vanishes anywhere along the curve; a cusp would show
    // up here as a near-zero speed or a sudden direction flip.
    double MinSpeed = InfValue;
    double MinTangentDot = 1.0;
    Vec3 Previous = Path.TangentAtParam(Path.MinParam());
    for (int I = 1; I <= 4000; ++I)
    {
        const double U = Path.MinParam() + (Path.MaxParam() - Path.MinParam()) * (static_cast<double>(I) / 4000);
        const Vec3 D = Path.DerivativeAtParam(U);
        MinSpeed = std::min(MinSpeed, Length(D));
        const Vec3 T = Normalized(D);
        MinTangentDot = std::min(MinTangentDot, Dot(T, Previous));
        Previous = T;
    }
    Record("continuity", "minSpeedAlongCurve", MinSpeed, ">=", 1e-3, "no cusp: |dP/dU| never collapses");
    Record("continuity", "minConsecutiveTangentDot", MinTangentDot, ">=", 0.995, "no direction flip between adjacent samples");

    // The same checks on the real intro path.
    SplinePath Intro;
    RecordFlag("continuity", "introPathBuilt", Intro.Build(IntroControlPoints(), 0.5, 96), "the shipped intro control points");
    double IntroDerivativeJump = 0.0;
    for (std::size_t I = 1; I + 1 < Intro.NumPoints(); ++I)
    {
        const double U = Intro.KnotAt(I);
        const double Span = std::min(U - Intro.KnotAt(I - 1), Intro.KnotAt(I + 1) - U);
        const double E = Span * 1e-9;
        const Vec3 Da = Intro.DerivativeAtParam(U - E), Db = Intro.DerivativeAtParam(U + E);
        IntroDerivativeJump = std::max(IntroDerivativeJump, Distance(Da, Db) / std::max(Length(Da), 1e-9));
    }
    Record("continuity", "introMaxRelativeDerivativeJump", IntroDerivativeJump, "<=", 1e-6, "C1 on the shipped path");
    Record("continuity", "introTotalLengthCm", Intro.TotalLength(), ">=", 40000.0, "the flythrough covers a real distance");
    Record("continuity", "introTotalLengthUpperCm", Intro.TotalLength(), "<=", 160000.0,
           "at the 68 second running time the shot is authored for, 1.4 km is already 21 m/s "
           "average; a longer path would have to be flown faster than the shot reads");

    // The shipped path must not cusp either: a flick backwards in a 68 second establishing
    // shot is the single most obvious way for a camera move to look machine-made.
    double IntroMinTangentDot = 1.0;
    Vec3 IntroPrevious = Intro.TangentAtParam(Intro.MinParam());
    for (int I = 1; I <= 4000; ++I)
    {
        const double U = Intro.MinParam() + (Intro.MaxParam() - Intro.MinParam()) * (static_cast<double>(I) / 4000);
        const Vec3 T = Intro.TangentAtParam(U);
        IntroMinTangentDot = std::min(IntroMinTangentDot, Dot(T, IntroPrevious));
        IntroPrevious = T;
    }
    Record("continuity", "introMinConsecutiveTangentDot", IntroMinTangentDot, ">=", 0.999,
           "no direction flip anywhere on the shipped path");
}

// ---------------------------------------------------------------------------------
// 2. Arc-length reparameterisation: even spacing.
// ---------------------------------------------------------------------------------
static void ArcLengthChecks()
{
    SplinePath Path;
    // Segment lengths here differ by more than 10x, which is exactly the case that makes
    // an un-reparameterised spline speed up and slow down.
    std::vector<Vec3> Points = {{0, 0, 0}, {400, 0, 0}, {4600, 900, 200}, {5000, 4000, 250}, {12000, 4300, 1400}, {12400, 8000, 1500}};
    RecordFlag("arcLength", "buildSucceeded", Path.Build(Points, 0.5, 96), "");

    // A: chords between evenly spaced arc-length samples are equal to within the sagitta
    // the curvature implies; nothing here is a straight line so a small deficit is real.
    const int Divisions = 400;
    const double Step = Path.TotalLength() / Divisions;
    double MinChord = InfValue, MaxChord = 0.0;
    std::vector<Vec3> Samples = Path.SampleEvenly(Divisions);
    for (std::size_t I = 1; I < Samples.size(); ++I)
    {
        const double Chord = Distance(Samples[I - 1], Samples[I]);
        MinChord = std::min(MinChord, Chord);
        MaxChord = std::max(MaxChord, Chord);
    }
    const double ChordSpread = (MaxChord - MinChord) / Step;
    Record("arcLength", "evenSampleChordSpreadFraction", ChordSpread, "<=", 0.02,
           "max minus min chord between 400 evenly spaced points, over the nominal step");

    // B: an independent arc-length measure. A 400k-point polyline in parameter space is
    // integrated by brute force, then every ParamAtDistance answer is checked against it.
    // This does not reuse the class's own distance table, so it catches a table that is
    // self-consistently wrong.
    const int Fine = 400000;
    std::vector<double> FineParam(Fine + 1), FineLength(Fine + 1);
    Vec3 Last = Path.PointAtParam(Path.MinParam());
    FineParam[0] = Path.MinParam();
    FineLength[0] = 0.0;
    for (int I = 1; I <= Fine; ++I)
    {
        const double U = Path.MinParam() + (Path.MaxParam() - Path.MinParam()) * (static_cast<double>(I) / Fine);
        const Vec3 P = Path.PointAtParam(U);
        FineParam[I] = U;
        FineLength[I] = FineLength[I - 1] + Distance(Last, P);
        Last = P;
    }
    const double IndependentLength = FineLength[Fine];
    const double LengthAgreement = std::abs(IndependentLength - Path.TotalLength()) / Path.TotalLength();
    Record("arcLength", "totalLengthAgreementFraction", LengthAgreement, "<=", 1e-5,
           "Gauss-Legendre table total vs a 400k-point brute force polyline");

    double MaxResidualCm = 0.0;
    for (int I = 0; I <= Divisions; ++I)
    {
        const double Target = Step * I;
        const double U = Path.ParamAtDistance(Target);
        // Interpolate the brute-force cumulative length at U.
        int Lo = 0, Hi = Fine;
        while (Hi - Lo > 1)
        {
            const int Mid = (Lo + Hi) / 2;
            if (FineParam[Mid] <= U) Lo = Mid; else Hi = Mid;
        }
        const double Denominator = FineParam[Hi] - FineParam[Lo];
        const double Frac = Denominator > 1e-15 ? (U - FineParam[Lo]) / Denominator : 0.0;
        const double Measured = FineLength[Lo] + (FineLength[Hi] - FineLength[Lo]) * Frac;
        MaxResidualCm = std::max(MaxResidualCm, std::abs(Measured - Target));
    }
    Record("arcLength", "maxDistanceInversionResidualCm", MaxResidualCm, "<=", 0.01,
           "|true arc length at ParamAtDistance(s) - s| over 401 targets; path is about "
           "the length of the intro flythrough");
    Record("arcLength", "maxDistanceInversionResidualFraction", MaxResidualCm / Path.TotalLength(), "<=", 1e-6, "");

    // C: contrast. Sampling at even PARAMETER instead of even distance is visibly uneven,
    // which is the whole reason the reparameterisation exists. This asserts the naive
    // route really is bad, so a regression that silently drops the table would show up.
    double NaiveMin = InfValue, NaiveMax = 0.0;
    Vec3 PreviousPoint = Path.PointAtParam(Path.MinParam());
    for (int I = 1; I <= Divisions; ++I)
    {
        const double U = Path.MinParam() + (Path.MaxParam() - Path.MinParam()) * (static_cast<double>(I) / Divisions);
        const Vec3 P = Path.PointAtParam(U);
        const double Chord = Distance(PreviousPoint, P);
        NaiveMin = std::min(NaiveMin, Chord);
        NaiveMax = std::max(NaiveMax, Chord);
        PreviousPoint = P;
    }
    Record("arcLength", "uniformParameterChordSpreadFraction", (NaiveMax - NaiveMin) / Step, ">=", 0.2,
           "the un-reparameterised control: even parameter steps are demonstrably uneven in space");

    // The intro path itself must be even, because the visitor watches it.
    SplinePath Intro;
    Intro.Build(IntroControlPoints(), 0.5, 96);
    std::vector<Vec3> IntroSamples = Intro.SampleEvenly(300);
    const double IntroStep = Intro.TotalLength() / 300;
    double IntroMin = InfValue, IntroMax = 0.0;
    for (std::size_t I = 1; I < IntroSamples.size(); ++I)
    {
        const double Chord = Distance(IntroSamples[I - 1], IntroSamples[I]);
        IntroMin = std::min(IntroMin, Chord);
        IntroMax = std::max(IntroMax, Chord);
    }
    Record("arcLength", "introEvenSampleChordSpreadFraction", (IntroMax - IntroMin) / IntroStep, "<=", 0.02, "");
}

// ---------------------------------------------------------------------------------
// 3. Endpoints and degenerate inputs produce no NaN.
// ---------------------------------------------------------------------------------
static void EndpointChecks()
{
    SplinePath Path;
    Path.Build(IntroControlPoints(), 0.5, 96);

    const Vec3 Probe[8] = {
        Path.PointAtParam(Path.MinParam()),
        Path.PointAtParam(Path.MaxParam()),
        Path.DerivativeAtParam(Path.MinParam()),
        Path.DerivativeAtParam(Path.MaxParam()),
        Path.PointAtDistance(0.0),
        Path.PointAtDistance(Path.TotalLength()),
        Path.TangentAtDistance(0.0),
        Path.TangentAtDistance(Path.TotalLength()),
    };
    bool bAllFinite = true;
    for (int I = 0; I < 8; ++I) bAllFinite = bAllFinite && Finite(Probe[I]);
    RecordFlag("endpoints", "endpointEvaluationsFinite", bAllFinite, "position, derivative and tangent at both ends");

    // The reflected phantom point makes the end tangent the endpoint chord direction, so
    // the end tangents are unit length and point along the path, not off into nothing.
    Record("endpoints", "startTangentLength", Length(Probe[6]), ">=", 0.999999, "");
    Record("endpoints", "endTangentLength", Length(Probe[7]), ">=", 0.999999, "");
    Record("endpoints", "startPointErrorCm", Distance(Probe[0], IntroControlPoints().front()), "<=", 1e-9, "");
    Record("endpoints", "endPointErrorCm", Distance(Probe[1], IntroControlPoints().back()), "<=", 1e-9, "");
    Record("endpoints", "distanceZeroMatchesStartCm", Distance(Probe[4], Probe[0]), "<=", 1e-6, "");
    Record("endpoints", "distanceFullMatchesEndCm", Distance(Probe[5], Probe[1]), "<=", 1e-6, "");

    // Out-of-range and non-finite inputs clamp instead of exploding.
    bool bClampsCleanly = Finite(Path.PointAtParam(-1e9)) && Finite(Path.PointAtParam(1e9)) &&
                          Finite(Path.PointAtParam(NaNValue)) && Finite(Path.PointAtParam(InfValue)) &&
                          Finite(Path.PointAtDistance(-500.0)) && Finite(Path.PointAtDistance(1e12)) &&
                          Finite(Path.PointAtDistance(NaNValue)) && Finite(Path.PointAtEasedAlpha(NaNValue)) &&
                          Finite(Path.DerivativeAtParam(NaNValue));
    RecordFlag("endpoints", "outOfRangeAndNonFiniteInputsClamp", bClampsCleanly, "");
    Record("endpoints", "negativeDistanceClampsToStartCm", Distance(Path.PointAtDistance(-500.0), Probe[0]), "<=", 1e-6, "");
    Record("endpoints", "hugeDistanceClampsToEndCm", Distance(Path.PointAtDistance(1e12), Probe[1]), "<=", 1e-6, "");

    // Two points is the minimum viable path and must not divide by zero anywhere.
    SplinePath Pair;
    RecordFlag("endpoints", "twoPointPathBuilds", Pair.Build({{0, 0, 0}, {1000, 0, 0}}, 0.5, 8), "");
    RecordFlag("endpoints", "twoPointPathFinite",
               Finite(Pair.PointAtDistance(0)) && Finite(Pair.PointAtDistance(Pair.TotalLength())) &&
                   Finite(Pair.DerivativeAtParam(Pair.MinParam())) && Finite(Pair.DerivativeAtParam(Pair.MaxParam())),
               "");
    Record("endpoints", "twoPointStraightLengthCm", Pair.TotalLength(), "<=", 1000.0000001, "a two point path is a straight line");
    Record("endpoints", "twoPointStraightLengthLowerCm", Pair.TotalLength(), ">=", 999.9999999, "");

    // Bad inputs are refused rather than silently producing a broken path.
    SplinePath Bad;
    RecordFlag("endpoints", "rejectsSinglePoint", !Bad.Build({{0, 0, 0}}, 0.5, 32), "");
    RecordFlag("endpoints", "rejectsDuplicateConsecutivePoints", !Bad.Build({{0, 0, 0}, {0, 0, 0}, {100, 0, 0}}, 0.5, 32), "");
    RecordFlag("endpoints", "rejectsNonFinitePoint", !Bad.Build({{0, 0, 0}, {NaNValue, 0, 0}, {100, 0, 0}}, 0.5, 32), "");
    RecordFlag("endpoints", "rejectedBuildLeavesObjectInvalid", !Bad.IsValid() && !Finite(Bad.PointAtParam(0.5)) == false, "");
    RecordFlag("endpoints", "invalidPathEvaluatesToZeroNotNaN", Finite(Bad.PointAtParam(0.5)) && Finite(Bad.PointAtDistance(10.0)), "");
}

// ---------------------------------------------------------------------------------
// 4. Ease curves are monotonic, pinned at both ends, and NaN-safe.
// ---------------------------------------------------------------------------------
static void EasingChecks()
{
    struct Curve
    {
        const char* Name;
        double (*Fn)(double);
    };
    static const Curve Curves[] = {
        {"easeLinear", &EaseLinear},
        {"smoothStep", &SmoothStep},
        {"smootherStep", &SmootherStep},
        {"easeInOutSine", &EaseInOutSine},
        {"easeInCubic", &EaseInCubic},
        {"easeOutCubic", &EaseOutCubic},
        {"easeInOutCubic", &EaseInOutCubic},
    };
    const int Steps = 20000;
    for (std::size_t C = 0; C < sizeof(Curves) / sizeof(Curves[0]); ++C)
    {
        double WorstDecrease = 0.0;
        double Previous = Curves[C].Fn(0.0);
        bool bFinite = std::isfinite(Previous);
        for (int I = 1; I <= Steps; ++I)
        {
            const double V = Curves[C].Fn(static_cast<double>(I) / Steps);
            bFinite = bFinite && std::isfinite(V);
            WorstDecrease = std::max(WorstDecrease, Previous - V);
            Previous = V;
        }
        const std::string Base = Curves[C].Name;
        Record("easing", (Base + ".worstDecrease").c_str(), WorstDecrease, "<=", 0.0, "monotonic non-decreasing on [0,1]");
        Record("easing", (Base + ".atZero").c_str(), Curves[C].Fn(0.0), "==", 0.0, "");
        Record("easing", (Base + ".atOne").c_str(), Curves[C].Fn(1.0), "==", 1.0, "");
        RecordFlag("easing", (Base + ".finiteEverywhere").c_str(), bFinite, "");
        RecordFlag("easing", (Base + ".saturatesOutOfRange").c_str(),
                   std::abs(Curves[C].Fn(-5.0)) <= 1e-15 && std::abs(Curves[C].Fn(5.0) - 1.0) <= 1e-15, "");
        RecordFlag("easing", (Base + ".nanMapsToZero").c_str(), std::abs(Curves[C].Fn(NaNValue)) <= 1e-15, "");
    }

    // The trapezoid is the one the long travelling shots use; check a spread of ramp
    // splits, including degenerate and over-unity ones.
    static const double Splits[7][2] = {{0.0, 0.0}, {0.25, 0.25}, {0.4, 0.1}, {0.0, 0.5}, {0.5, 0.0}, {0.7, 0.7}, {1.0, 1.0}};
    double WorstTrapezoidDecrease = 0.0;
    double WorstEndError = 0.0;
    bool bTrapezoidFinite = true;
    for (int S = 0; S < 7; ++S)
    {
        double Previous = EaseTrapezoid(0.0, Splits[S][0], Splits[S][1]);
        bTrapezoidFinite = bTrapezoidFinite && std::isfinite(Previous);
        WorstEndError = std::max(WorstEndError, std::abs(Previous));
        for (int I = 1; I <= Steps; ++I)
        {
            const double V = EaseTrapezoid(static_cast<double>(I) / Steps, Splits[S][0], Splits[S][1]);
            bTrapezoidFinite = bTrapezoidFinite && std::isfinite(V);
            WorstTrapezoidDecrease = std::max(WorstTrapezoidDecrease, Previous - V);
            Previous = V;
        }
        WorstEndError = std::max(WorstEndError, std::abs(EaseTrapezoid(1.0, Splits[S][0], Splits[S][1]) - 1.0));
    }
    Record("easing", "easeTrapezoid.worstDecrease", WorstTrapezoidDecrease, "<=", 0.0, "monotonic for every ramp split tried");
    Record("easing", "easeTrapezoid.worstEndpointError", WorstEndError, "<=", 1e-12, "pinned to 0 and 1 for every ramp split");
    RecordFlag("easing", "easeTrapezoid.finiteEverywhere", bTrapezoidFinite, "");
    RecordFlag("easing", "easeTrapezoid.nonFiniteFractionsSafe",
               std::isfinite(EaseTrapezoid(0.5, NaNValue, InfValue)) && std::abs(EaseTrapezoid(NaNValue, 0.2, 0.2)) <= 1e-15, "");

    // Zero ramps degenerate to linear; a middle ramp really does hold constant speed.
    Record("easing", "easeTrapezoid.zeroRampIsLinear", std::abs(EaseTrapezoid(0.37, 0.0, 0.0) - 0.37), "<=", 1e-12, "");
    const double Mid1 = EaseTrapezoid(0.45, 0.2, 0.2), Mid2 = EaseTrapezoid(0.55, 0.2, 0.2);
    const double Mid3 = EaseTrapezoid(0.35, 0.2, 0.2), Mid4 = EaseTrapezoid(0.45, 0.2, 0.2);
    Record("easing", "easeTrapezoid.constantMiddleSpeedError", std::abs((Mid2 - Mid1) - (Mid4 - Mid3)), "<=", 1e-12,
           "equal time steps inside the hold cover equal distance");
    // Symmetric split is symmetric about the half way point.
    Record("easing", "easeTrapezoid.symmetryError", std::abs(EaseTrapezoid(0.5, 0.3, 0.3) - 0.5), "<=", 1e-12, "");

    // Eased position along a real path stays monotonic in distance too.
    SplinePath Intro;
    Intro.Build(IntroControlPoints(), 0.5, 96);
    double WorstBackwards = 0.0;
    double LastDistance = 0.0;
    for (int I = 0; I <= 4000; ++I)
    {
        const double T = static_cast<double>(I) / 4000;
        const double D = EaseTrapezoid(T, 0.30, 0.30) * Intro.TotalLength();
        WorstBackwards = std::max(WorstBackwards, LastDistance - D);
        LastDistance = D;
    }
    Record("easing", "easedIntroDistanceNeverReverses", WorstBackwards, "<=", 0.0, "");
}

// ---------------------------------------------------------------------------------
// 5. Look-at, roll damping, banking.
// ---------------------------------------------------------------------------------
static void OrientationChecks()
{
    // LookAt and MakeBasis must agree: the basis forward is the normalised direction.
    double WorstAimError = 0.0;
    const Vec3 From{1000, -2000, 500};
    static const Vec3 Targets[6] = {{2000, -2000, 500}, {1000, 3000, 500}, {1000, -2000, 4000},
                                    {1000, -2000, -4000}, {-5330, 315, 925}, {-6200, 0, 925}};
    for (int I = 0; I < 6; ++I)
    {
        const Orientation R = LookAt(From, Targets[I]);
        const Basis B = MakeBasis(R);
        WorstAimError = std::max(WorstAimError, Distance(B.Forward, Normalized(Targets[I] - From)));
    }
    Record("orientation", "lookAtForwardMatchesDirection", WorstAimError, "<=", 1e-12,
           "MakeBasis reproduces FRotationMatrix, so LookAt output can be keyed directly");

    // The basis stays orthonormal at every roll.
    double WorstOrthoError = 0.0;
    for (int I = -180; I <= 180; I += 5)
    {
        const Basis B = MakeBasis({35.0, -117.0, static_cast<double>(I)});
        WorstOrthoError = std::max(WorstOrthoError, std::abs(Length(B.Forward) - 1.0));
        WorstOrthoError = std::max(WorstOrthoError, std::abs(Length(B.Right) - 1.0));
        WorstOrthoError = std::max(WorstOrthoError, std::abs(Length(B.Up) - 1.0));
        WorstOrthoError = std::max(WorstOrthoError, std::abs(Dot(B.Forward, B.Right)));
        WorstOrthoError = std::max(WorstOrthoError, std::abs(Dot(B.Forward, B.Up)));
        WorstOrthoError = std::max(WorstOrthoError, std::abs(Dot(B.Right, B.Up)));
    }
    Record("orientation", "basisOrthonormalityError", WorstOrthoError, "<=", 1e-12, "");
    RecordFlag("orientation", "degenerateLookAtIsIdentity",
               LookAt({5, 5, 5}, {5, 5, 5}).Yaw == 0.0 && LookAt({5, 5, 5}, {5, 5, 5}).Pitch == 0.0, "");
    RecordFlag("orientation", "nonFiniteLookAtIsIdentity", LookAt({0, 0, 0}, {NaNValue, 0, 0}).Yaw == 0.0, "");

    // Roll damping: converges, never overshoots, always takes the short way round.
    double Roll = 170.0;
    const double Target = -170.0; // 20 degrees away across the wrap, not 340
    double WorstStep = 0.0;
    for (int I = 0; I < 600; ++I)
    {
        const double Next = RollTowards(Roll, Target, 1.0 / 60.0, 0.25);
        WorstStep = std::max(WorstStep, std::abs(ShortestDeltaDegrees(Roll, Next)));
        Roll = Next;
    }
    Record("orientation", "rollDampingResidualDegrees", std::abs(ShortestDeltaDegrees(Roll, Target)), "<=", 1e-6, "");
    Record("orientation", "rollDampingMaxStepDegrees", WorstStep, "<=", 20.0, "never overshoots the 20 degree gap");
    Record("orientation", "rollDampingHalfLifeError",
           std::abs(RollTowards(0.0, 100.0, 0.25, 0.25) - 50.0), "<=", 1e-9, "one half life covers exactly half the gap");
    Record("orientation", "rollDampingIsNoOpForZeroDt", std::abs(RollTowards(12.0, -30.0, 0.0, 0.2) - 12.0), "<=", 1e-12, "");
    Record("orientation", "rollDampingIsNoOpForNaNDt", std::abs(RollTowards(12.0, -30.0, NaNValue, 0.2) - 12.0), "<=", 1e-12, "");
    Record("orientation", "rollDampingHitchIsClamped", std::abs(RollTowards(0.0, 100.0, 10.0, 0.25)), "<=", 99.9,
           "a ten second hitch is clamped to a quarter second of motion");
    Record("orientation", "rollDampingNaNTargetHolds", std::abs(RollTowards(12.0, NaNValue, 0.1, 0.2) - 12.0), "<=", 1e-12, "");

    // Whole-rotator damping unwraps each axis.
    const Orientation Damped = OrientationTowards({0, 179.0, 0}, {0, -179.0, 0}, 0.25, 0.25);
    Record("orientation", "yawDampingTakesShortWayDegrees", std::abs(ShortestDeltaDegrees(179.0, Damped.Yaw)), "<=", 1.0001,
           "179 to -179 is one degree of motion, so half a half-life is under a degree");
    RecordFlag("orientation", "pitchDampingStaysInGimbalSafeRange",
               OrientationTowards({80, 0, 0}, {200, 0, 0}, 1.0, 0.01).Pitch <= 89.9, "");

    // Banking.
    Record("orientation", "bankLeftTurnIsNegative", BankFromTurnRate(30.0, 12.0, 30.0), "==", -12.0, "");
    Record("orientation", "bankRightTurnIsPositive", BankFromTurnRate(-30.0, 12.0, 30.0), "==", 12.0, "");
    Record("orientation", "bankSaturates", BankFromTurnRate(3000.0, 12.0, 30.0), "==", -12.0, "");
    Record("orientation", "bankStraightIsZero", BankFromTurnRate(0.0, 12.0, 30.0), "==", 0.0, "");
    Record("orientation", "bankNaNIsZero", BankFromTurnRate(NaNValue, 12.0, 30.0), "==", 0.0, "");

    // Unwrapping keys.
    Record("orientation", "unwrapKeepsShortestTurn", UnwrapDegrees(179.0, -179.0), "==", 181.0, "");
    Record("orientation", "unwrapAccumulatesAcrossTurns", UnwrapDegrees(-181.0, 175.0), "==", -185.0, "");
}

// ---------------------------------------------------------------------------------
// 6. Clamps: photo-mode leash, frustum safety, segment/box clearance.
// ---------------------------------------------------------------------------------
static void ClampChecks()
{
    const Box Level{{-8100, -8100, 200}, {8100, 8100, 3400}};
    RecordFlag("clamp", "insidePointUntouched", Distance(ClampToBox({100, 200, 900}, Level, 50.0), Vec3{100, 200, 900}) <= 1e-12, "");
    const Vec3 Outside = ClampToBox({99999, -99999, 99999}, Level, 100.0);
    RecordFlag("clamp", "outsidePointPulledInsideMargin", BoxContains(Level, Outside) &&
                                                             Outside.X <= 8000.0000001 && Outside.Y >= -8000.0000001 && Outside.Z <= 3300.0000001, "");
    RecordFlag("clamp", "nanPositionGoesToBoxCentre", Finite(ClampToBox({NaNValue, 0, 0}, Level, 0.0)), "");
    const Box Thin{{0, 0, 0}, {100, 100, 100}};
    RecordFlag("clamp", "oversizedMarginCollapsesToCentre", Distance(ClampToBox({999, 999, 999}, Thin, 500.0), Vec3{50, 50, 50}) <= 1e-12, "");

    const Vec3 Anchor{6300, 0, 400};
    RecordFlag("clamp", "sphereLeashKeepsCloseCamera", Distance(ClampToSphere({6500, 0, 400}, Anchor, 3000.0), Vec3{6500, 0, 400}) <= 1e-12, "");
    Record("clamp", "sphereLeashRadiusErrorCm", std::abs(Distance(ClampToSphere({60000, 0, 400}, Anchor, 3000.0), Anchor) - 3000.0), "<=", 1e-9, "");
    RecordFlag("clamp", "sphereLeashNaNGoesToAnchor", Distance(ClampToSphere({NaNValue, 0, 0}, Anchor, 3000.0), Anchor) <= 1e-12, "");

    // Slab test.
    const Box Wall{{-100, -5000, 0}, {100, 5000, 3000}};
    RecordFlag("clamp", "segmentThroughWallDetected", SegmentIntersectsBox({-500, 0, 500}, {500, 0, 500}, Wall, 0.0), "");
    RecordFlag("clamp", "segmentPassingOverWallClears", !SegmentIntersectsBox({-500, 0, 4000}, {500, 0, 4000}, Wall, 0.0), "");
    RecordFlag("clamp", "segmentStoppingShortClears", !SegmentIntersectsBox({-500, 0, 500}, {-200, 0, 500}, Wall, 0.0), "");
    RecordFlag("clamp", "inflationCatchesNearMiss", SegmentIntersectsBox({-500, 0, 3200}, {500, 0, 3200}, Wall, 300.0), "");
    RecordFlag("clamp", "nonFiniteSegmentIsNotAHit", !SegmentIntersectsBox({NaNValue, 0, 0}, {500, 0, 500}, Wall, 0.0), "");

    // The shipped intro path must clear the sanctuary block, the outer wall line and the
    // ground plane by a real margin. These boxes are the ones the release spec records.
    SplinePath Intro;
    Intro.Build(IntroControlPoints(), 0.5, 96);
    const std::vector<Vec3> Polyline = Intro.SampleEvenly(600);
    const std::vector<Box> Blockers = IntroBlockers();
    std::size_t Segment = 0, Which = 0;
    const bool bClears = PolylineClearsBoxes(Polyline, Blockers, 150.0, &Segment, &Which);
    RecordFlag("clamp", "introPathClears42SolidBlocksBy150cm", bClears,
               "600 segment polyline against the House, the west wings, the perimeter bands, the "
               "outer deck, the inner podium and priest court, the inner court walls, both gates "
               "of the court piece by piece, the Ulam stairs, the altar, and the east gate of the "
               "precinct wall with its neighbouring modules");
    // The path enters the PRECINCT the way Yechezkel 43:1-4 has the glory enter: from the
    // east, through the east gate. The gate module is X 116549..116900; the opening is 500 cm
    // wide between piers at |Y| >= 250 and runs from the plinth at 3551.4 to the lintel
    // soffit at 6051.4. With the 150 cm margin the flyable window is |Y| <= 100 and
    // 3701.4 <= Z <= 5901.4, at every X across the module's depth.
    int PrecinctCrossings = 0;
    double PrecinctWorstLateral = 0.0, PrecinctLowestZ = InfValue, PrecinctHighestZ = -InfValue;
    for (std::size_t I = 1; I < Polyline.size(); ++I)
    {
        const Vec3& A = Polyline[I - 1];
        const Vec3& B = Polyline[I];
        if ((A.X > 116900.0) != (B.X > 116900.0)) ++PrecinctCrossings;
        if (std::max(A.X, B.X) >= 116549.0 && std::min(A.X, B.X) <= 116900.0)
        {
            PrecinctWorstLateral = std::max(PrecinctWorstLateral, std::max(std::abs(A.Y), std::abs(B.Y)));
            PrecinctLowestZ = std::min(PrecinctLowestZ, std::min(A.Z, B.Z));
            PrecinctHighestZ = std::max(PrecinctHighestZ, std::max(A.Z, B.Z));
        }
    }
    Record("clamp", "precinctEastGateCrossings", static_cast<double>(PrecinctCrossings), "==", 1.0,
           "the camera crosses the precinct's east face once, inward, and nowhere else");
    Record("clamp", "precinctGateLateralOffsetCm", PrecinctWorstLateral, "<=", 100.0,
           "half the 500 cm opening less the 150 cm margin, across the whole module depth");
    Record("clamp", "precinctGateHeightLowerCm", PrecinctLowestZ, ">=", 3551.4 + 150.0, "plinth plus the margin");
    Record("clamp", "precinctGateHeightUpperCm", PrecinctHighestZ, "<=", 6051.4 - 150.0, "lintel soffit less the margin");

    // The path enters the inner court the way a visitor does: through the inner eastern
    // gateway, not over the wall. The opening is 500 cm wide (jambs at |Y| >= 250, manifest
    // "Context 15/16 Inner eastern gate wall jamb") and runs from the threshold at 500 to
    // the lintel soffit at 3000. With the same 150 cm margin the flyable window is
    // |Y| <= 100 and 650 <= Z <= 2850, which is what these three checks pin down. It
    // crosses that plane once: a second crossing would mean the camera backed out again.
    // Only the stretch of the X = 2500 plane that is actually the inner court's eastern
    // wall counts, i.e. within the wall bands at |Y| < 2800. The long approach leg crosses
    // the same plane far to the south of the enclosure, over open ground, which is not a
    // wall crossing at all.
    int WallLineCrossings = 0;
    double GateY = 0.0, GateZ = 0.0;
    for (std::size_t I = 1; I < Polyline.size(); ++I)
    {
        const bool bWestward = Polyline[I - 1].X > 2500.0 && Polyline[I].X <= 2500.0;
        const bool bEastward = Polyline[I - 1].X <= 2500.0 && Polyline[I].X > 2500.0;
        if (!bWestward && !bEastward) continue;
        const double Span = Polyline[I].X - Polyline[I - 1].X;
        const double T = std::abs(Span) > 1e-9 ? (2500.0 - Polyline[I - 1].X) / Span : 0.0;
        const double CrossY = Polyline[I - 1].Y + (Polyline[I].Y - Polyline[I - 1].Y) * T;
        const double CrossZ = Polyline[I - 1].Z + (Polyline[I].Z - Polyline[I - 1].Z) * T;
        if (std::abs(CrossY) >= 2800.0) continue;
        ++WallLineCrossings;
        if (bWestward) { GateY = CrossY; GateZ = CrossZ; }
    }
    Record("clamp", "innerCourtWallLineCrossings", static_cast<double>(WallLineCrossings), "==", 1.0,
           "the camera crosses the inner court wall line once, inward");
    Record("clamp", "gateTransitLateralOffsetCm", std::abs(GateY), "<=", 100.0,
           "half the 500 cm gateway less the 150 cm margin");
    Record("clamp", "gateTransitHeightLowerCm", GateZ, ">=", 650.0, "threshold 500 plus the margin");
    Record("clamp", "gateTransitHeightUpperCm", GateZ, "<=", 2850.0, "lintel soffit 3000 less the margin");

    // The shot ends exactly where the visitor takes control, to the centimetre. A hand-off
    // that lands anywhere else is a visible jump on the first frame of gameplay.
    Record("clamp", "introArrivesAtPlayerStartCm", Distance(Polyline.back(), Vec3{2100.0, 0.0, 668.0}), "<=", 1e-6,
           "Mikdash_PlayerStart [2100, 0], inner court clear floor top 500 plus 168 cm eye height");

    // How much margin the path actually has. The binding constraint is the last metre:
    // an eye 168 cm above the floor it stands on cannot clear that floor by more.
    double LargestClearingInflate = 0.0;
    for (double Trial = 0.0; Trial <= 400.0; Trial += 1.0)
    {
        if (!PolylineClearsBoxes(Polyline, Blockers, Trial)) break;
        LargestClearingInflate = Trial;
    }
    Record("clamp", "introLargestClearingInflateCm", LargestClearingInflate, ">=", 150.0,
           "largest uniform inflation of all 42 blocks the path still clears; capped by the "
           "168 cm eye height at the arrival point");

    // Frustum-safe clamp.
    FrustumSpec Spec;
    Spec.HorizontalFovDegrees = 70.0;
    Spec.AspectRatio = 16.0 / 9.0;
    Spec.NearClipCm = 10.0;
    Spec.SafeInset = 0.8;
    const Vec3 Menorah{-5330, 315, 925};

    // Already framed: nothing changes.
    const Orientation Aimed = LookAt({-4000, 315, 1100}, Menorah);
    const FrustumClampResult Framed = FrustumSafeClamp({-4000, 315, 1100}, Aimed, Menorah, Spec, 100.0);
    RecordFlag("frustum", "wellFramedSubjectIsUntouched", !Framed.bPositionClamped && !Framed.bRotationClamped, "");
    RecordFlag("frustum", "wellFramedSubjectReportsInSafeFrustum", SubjectInSafeFrustum({-4000, 315, 1100}, Aimed, Menorah, Spec), "");

    // Off to the side: re-aimed onto the inset edge exactly, in one pass.
    Orientation Swung = Aimed;
    Swung.Yaw = WrapDegrees(Swung.Yaw + 40.0);
    const FrustumClampResult Corrected = FrustumSafeClamp({-4000, 315, 1100}, Swung, Menorah, Spec, 100.0);
    RecordFlag("frustum", "offAxisSubjectTriggersRotationClamp", Corrected.bRotationClamped && !Corrected.bPositionClamped, "");
    const Basis CorrectedBasis = MakeBasis(Corrected.Rotation);
    const Vec3 ToSubject = Menorah - Corrected.Position;
    const double InsetHalfH = 70.0 * 0.5 * 0.8;
    const double MeasuredH = RadToDeg(std::atan2(Dot(ToSubject, CorrectedBasis.Right), Dot(ToSubject, CorrectedBasis.Forward)));
    Record("frustum", "correctedSubjectLandsOnInsetEdgeDegrees", std::abs(std::abs(MeasuredH) - InsetHalfH), "<=", 1e-9,
           "with zero roll the yaw correction is exact, so one pass suffices");
    RecordFlag("frustum", "correctedResultIsInSafeFrustum", SubjectInSafeFrustum(Corrected.Position, Corrected.Rotation, Menorah, Spec), "");

    // Too close: pushed back to the minimum distance, never inside the near plane.
    const FrustumClampResult TooClose = FrustumSafeClamp({-5330, 315, 940}, Aimed, Menorah, Spec, 250.0);
    RecordFlag("frustum", "tooCloseTriggersPositionClamp", TooClose.bPositionClamped, "");
    Record("frustum", "pushedBackDistanceErrorCm", std::abs(Distance(TooClose.Position, Menorah) - 250.0), "<=", 1e-9, "");
    // Camera exactly on the subject still yields a finite pose.
    const FrustumClampResult OnTop = FrustumSafeClamp(Menorah, Aimed, Menorah, Spec, 250.0);
    RecordFlag("frustum", "cameraOnSubjectStaysFinite", Finite(OnTop.Position) && std::isfinite(OnTop.Rotation.Yaw), "");
    Record("frustum", "cameraOnSubjectPushedToMinCm", std::abs(Distance(OnTop.Position, Menorah) - 250.0), "<=", 1e-9, "");
    // A zero minimum distance is still lifted above the near plane.
    const FrustumClampResult NearPlane = FrustumSafeClamp({-5330, 315, 926}, Aimed, Menorah, Spec, 0.0);
    Record("frustum", "nearPlaneFloorRespectedCm", Distance(NearPlane.Position, Menorah), ">=", 15.0 - 1e-9,
           "minimum distance is lifted to 1.5x the near clip even when the caller asks for zero");

    // Behind the camera: fully re-aimed.
    Orientation Backwards = Aimed;
    Backwards.Yaw = WrapDegrees(Backwards.Yaw + 180.0);
    const FrustumClampResult Reversed = FrustumSafeClamp({-4000, 315, 1100}, Backwards, Menorah, Spec, 100.0);
    Record("frustum", "subjectBehindCameraOffAxisDegrees", Reversed.SubjectOffAxisDegrees, ">=", 90.0, "");
    Record("frustum", "reAimedYawErrorDegrees",
           std::abs(ShortestDeltaDegrees(Reversed.Rotation.Yaw, LookAt({-4000, 315, 1100}, Menorah).Yaw)), "<=", 1e-9, "");

    // Rolled camera: the conservative inscribed cone is used, so the result holds at any
    // roll the visitor dials in.
    Orientation Rolled = Aimed;
    Rolled.Roll = 33.0;
    Rolled.Yaw = WrapDegrees(Rolled.Yaw + 25.0);
    const FrustumClampResult RolledResult = FrustumSafeClamp({-4000, 315, 1100}, Rolled, Menorah, Spec, 100.0);
    RecordFlag("frustum", "rolledOffAxisSubjectIsClamped", RolledResult.bRotationClamped, "");
    bool bHoldsAtEveryRoll = true;
    for (int R = -180; R <= 180; R += 5)
    {
        Orientation Probe = RolledResult.Rotation;
        Probe.Roll = static_cast<double>(R);
        const Basis PB = MakeBasis(Probe);
        const Vec3 D = Menorah - RolledResult.Position;
        const double Cz = Dot(D, PB.Forward);
        const double Off = RadToDeg(std::acos(Clamp(Cz / Length(D), -1.0, 1.0)));
        const double ConeHalf = std::min(70.0 * 0.5, VerticalFovDegrees(Spec) * 0.5) * 0.8;
        bHoldsAtEveryRoll = bHoldsAtEveryRoll && Off <= ConeHalf + 1e-6;
    }
    RecordFlag("frustum", "rolledClampHoldsAtEveryRollAngle", bHoldsAtEveryRoll,
               "the inscribed cone guarantee is what photo mode relies on when the visitor tilts the horizon");

    // Degenerate inputs never produce a NaN pose.
    const FrustumClampResult BadSubject = FrustumSafeClamp({0, 0, 0}, Aimed, {NaNValue, 0, 0}, Spec, 100.0);
    RecordFlag("frustum", "nonFiniteSubjectIsSafe", Finite(BadSubject.Position) && std::isfinite(BadSubject.Rotation.Yaw), "");
    FrustumSpec Silly;
    Silly.HorizontalFovDegrees = 0.0;
    Silly.AspectRatio = 0.0;
    Silly.NearClipCm = -5.0;
    Silly.SafeInset = 99.0;
    const FrustumClampResult SillyResult = FrustumSafeClamp({-4000, 315, 1100}, Aimed, Menorah, Silly, -50.0);
    RecordFlag("frustum", "degenerateSpecIsClampedNotDivided",
               Finite(SillyResult.Position) && std::isfinite(SillyResult.Rotation.Pitch) && std::isfinite(VerticalFovDegrees(Silly)), "");

    // Framing helper.
    Record("frustum", "fovToFrameSphereDegrees", FovToFrame(200.0, 1000.0, 0.8), ">=", 28.0, "");
    Record("frustum", "fovToFrameSphereDegreesUpper", FovToFrame(200.0, 1000.0, 0.8), "<=", 30.0, "");
    Record("frustum", "fovToFrameInsideSphereSaturates", FovToFrame(500.0, 100.0, 0.8), "==", 170.0, "");
    Record("frustum", "fovToFrameNaNSaturates", FovToFrame(NaNValue, 100.0, 0.8), "==", 170.0, "");
}

// ---------------------------------------------------------------------------------
int main(int Argc, char** Argv)
{
    ContinuityChecks();
    ArcLengthChecks();
    EndpointChecks();
    EasingChecks();
    OrientationChecks();
    ClampChecks();

    const char* OutPath = Argc > 1 ? Argv[1] : "tests.json";
    FILE* File = std::fopen(OutPath, "wb");
    if (!File)
    {
        std::cerr << "Could not open " << OutPath << " for writing\n";
        return 2;
    }
    std::fprintf(File, "{\n");
    std::fprintf(File, "  \"suite\": \"CameraPathMathTest\",\n");
    std::fprintf(File, "  \"header\": \"Plugins/MikdashRuntime/Source/MikdashRuntime/Public/CameraPathMath.h\",\n");
    std::fprintf(File, "  \"source\": \"Plugins/MikdashRuntime/Tests/CameraPathMathTest.cpp\",\n");
    std::fprintf(File, "  \"scope\": \"Engine-independent camera path math only. Passing here establishes no visual, "
                       "Sequencer, packaged-build or halachic acceptance.\",\n");
    std::fprintf(File, "  \"checks\": %d,\n", static_cast<int>(Metrics.size()));
    std::fprintf(File, "  \"failures\": %d,\n", Failures);
    std::fprintf(File, "  \"status\": \"%s\",\n", Failures == 0 ? "all_camera_path_math_checks_passed" : "camera_path_math_checks_failed");
    std::fprintf(File, "  \"metrics\": [\n");
    for (std::size_t I = 0; I < Metrics.size(); ++I)
    {
        const Metric& M = Metrics[I];
        std::fprintf(File, "    {\"group\": \"%s\", \"name\": \"%s\", \"measured\": %s, \"comparison\": \"%s\", "
                           "\"tolerance\": %s, \"passed\": %s%s%s%s}%s\n",
                     JsonEscape(M.Group).c_str(), JsonEscape(M.Name).c_str(), Number(M.Measured).c_str(),
                     JsonEscape(M.Comparison).c_str(), Number(M.Tolerance).c_str(), M.bPassed ? "true" : "false",
                     M.Note.empty() ? "" : ", \"note\": \"", M.Note.empty() ? "" : JsonEscape(M.Note).c_str(),
                     M.Note.empty() ? "" : "\"", I + 1 == Metrics.size() ? "" : ",");
    }
    std::fprintf(File, "  ]\n}\n");
    std::fclose(File);

    std::cout << "CameraPathMath: " << Metrics.size() << " checks, " << Failures << " failures. Receipt: " << OutPath << "\n";
    if (Failures == 0)
    {
        std::cout << "  C1 continuity, even arc-length spacing, finite endpoints, monotonic easing,\n"
                     "  look-at/roll damping and the frustum-safe clamp all hold.\n";
    }
    return Failures == 0 ? 0 : 1;
}
