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
    // World frame: +X east, +Y south, +Z up. Sources for every number are listed in
    // Scripts/release_intro_sequence.spec.json; the path is duplicated here so the
    // geometry of the shipped flythrough is tested, not a synthetic curve.
    return {
        {-38600.0, 48200.0, 3800.0},  // over the Batei Mahase street beside the placed bus
        {-33000.0, 41000.0, 4600.0},  // climbing across the Old City roofs (local max 2875)
        {-26000.0, 31000.0, 5600.0},
        {-20500.0, 21000.0, 5600.0},
        {-16800.0, 15000.0, 4400.0},  // over the Kotel plaza, wall face top 600
        {-12000.0, 10500.0, 3600.0},  // inside the Mount enclosure ring, deck top 0
        {-8000.0, 7000.0, 4400.0},    // climbing to clear the outer court envelope
        {-3500.0, 6200.0, 5200.0},    // south of the House, whose roof reaches 6075
        {600.0, 5400.0, 5000.0},
        {3600.0, 3900.0, 4500.0},
        {2000.0, 2400.0, 4100.0},     // over the inner court wall, top 3625
        {-900.0, 1900.0, 3300.0},     // descending turn inside the inner court
        {-1100.0, -1500.0, 2500.0},
        {1400.0, -2100.0, 1800.0},
        {2000.0, 1500.0, 1100.0},
        {2100.0, 0.0, 668.0},         // the visitor's eye at the PlayerStart
    };
}

// The solid blocks the flythrough must clear, as axis-aligned boxes. Hollow unions are
// NOT used as single boxes here: the outer envelope and the inner side walls enclose the
// whole court, so an AABB test against them flags every point inside it. The inner court
// wall is modelled as four 300 cm bands instead, 300 cm being the measured thickness of
// the inner eastern gate wall jamb (x 2500..2800).
static std::vector<Box> IntroBlockers()
{
    return {
        {{-7000, -2500, 925}, {-2500, 2500, 6075}},    // House walls and roofs
        {{-7500, -2500, -5000}, {-2500, 2500, 924}},   // House and Ulam foundations
        {{-2500, -985, -5000}, {-1400, 985, 925}},     // Ulam stairs
        {{-800, -800, -5000}, {800, 800, 1108.3}},     // altar
        {{-2500, -2500, -5000}, {1575, 2500, 625}},    // Ezras Kohanim floor and its foundation
        {{1575, -2500, -5000}, {2500, 2500, 625}},     // duchan rise and inner court clear floor
        {{-7800, -7800, -5000}, {7800, 7800, 300}},    // outer court floor
        {{-2500, -2800, 625}, {-2200, 2800, 3625}},    // inner court wall, west band
        {{2200, -2800, 625}, {2500, 2800, 3625}},      // inner court wall, east band
        {{-2500, -2800, 625}, {2500, -2500, 3625}},    // inner court wall, north band
        {{-2500, 2500, 625}, {2500, 2800, 3625}},      // inner court wall, south band
        {{2500, -2800, 500}, {2800, 2800, 3500}},      // inner eastern gate wall jamb
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
        MaxPositionJump = std::max(MaxPositionJump, Distance(Before, After));

        const Vec3 Da = Path.DerivativeAtParam(U - E), Db = Path.DerivativeAtParam(U + E);
        const double Scale = std::max(Length(Da), 1e-9);
        MaxDerivativeJump = std::max(MaxDerivativeJump, Distance(Da, Db) / Scale);

        // C0 as well: the curve passes exactly through every control point.
        MaxControlPointError = std::max(MaxControlPointError, Distance(Path.PointAtParam(U), Points[I]));
    }
    // C0 at the two ends too.
    MaxControlPointError = std::max(MaxControlPointError, Distance(Path.PointAtParam(Path.MinParam()), Points.front()));
    MaxControlPointError = std::max(MaxControlPointError, Distance(Path.PointAtParam(Path.MaxParam()), Points.back()));

    Record("continuity", "maxPositionJumpAtInteriorKnotsCm", MaxPositionJump, "<=", 1e-6, "C0 across segment joins");
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
        const double D = EaseTrapezoid(T, 0.22, 0.30) * Intro.TotalLength();
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
    RecordFlag("clamp", "introPathClears12SolidBlocksBy150cm", bClears,
               "600 segment polyline against the House, its foundations, the Ulam stairs, the altar, "
               "three floor slabs, the four inner court wall bands and the east gate jamb");
    // Where the path crosses into the inner court footprint it must be above the wall top.
    double LowestCrossingZ = InfValue;
    for (std::size_t I = 1; I < Polyline.size(); ++I)
    {
        const bool bWasIn = std::abs(Polyline[I - 1].X) < 2500 && std::abs(Polyline[I - 1].Y) < 2800;
        const bool bIsIn = std::abs(Polyline[I].X) < 2500 && std::abs(Polyline[I].Y) < 2800;
        if (bWasIn != bIsIn) LowestCrossingZ = std::min(LowestCrossingZ, std::min(Polyline[I - 1].Z, Polyline[I].Z));
    }
    Record("clamp", "innerCourtWallCrossingZCm", LowestCrossingZ, ">=", 3625.0 + 150.0,
           "the only way into the inner court is over its 3625 cm wall; the path crosses once, high");

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
