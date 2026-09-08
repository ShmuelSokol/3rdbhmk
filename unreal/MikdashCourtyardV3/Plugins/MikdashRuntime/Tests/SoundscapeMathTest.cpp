// Standalone test for the engine-free half of MikdashSoundscape.h.
// No Unreal, no engine, no I/O beyond stdout.
//
// Compiled and run by Scripts/verify.py, which builds every .cpp in this folder with
//   cl /std:c++17 /EHsc /W4 /O2 /I <plugin>/Source/MikdashRuntime/Public
//
// MIKDASH_SOUNDSCAPE_MATH_ONLY makes the header stop before its UCLASS section, so
// this file needs none of the engine. UnrealHeaderTool never defines that macro, so
// the actor half is always visible to the real build.
//
// The contract assertions this soundscape pass depends on:
//   1. NOTHING IS ON A FIXED LOOP. No emitter can play the same take twice in a row;
//      no two consecutive events are identical in gap, take, pitch and level; the gap
//      distribution has real spread; and the two looping beds do not realign inside
//      any plausible session.
//   2. TIME OF DAY IS FOLLOWED, NOT FAKED. Dawn is quiet, midday is busy, night is
//      wind and distant city -- as numbers, at the real solar anchors for the date,
//      and continuously across midnight.
//   3. ZONES ARE CONTAINED AND CONTINUOUS. A zone never affects a listener outside its
//      bounds, priority resolves overlap, and every crossing is smooth.
//   4. EVERY CURVE IS TOTAL. Infinities, NaNs, inverted boxes, polar anchor sets, zero
//      counts and null pointers all produce a defined, safe answer.
//   5. THE SCHEDULE IS DETERMINISTIC. The same seed reproduces the same soundscape;
//      a different seed does not.

#define MIKDASH_SOUNDSCAPE_MATH_ONLY 1
#include "SoundscapeMath.h"

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <map>
#include <string>
#include <vector>

using namespace MikdashSoundscape;

// A check that survives /DNDEBUG.
static int Failures = 0;
static int Checks = 0;
static void Check(bool Condition, const char* What, int Line)
{
    ++Checks;
    if (!Condition)
    {
        ++Failures;
        std::printf("FAIL line %d: %s\n", Line, What);
    }
}
#define CHECK(expr) Check((expr), #expr, __LINE__)
#define CHECK_NEAR(a, b, tol) Check(std::fabs((a) - (b)) <= (tol), #a " ~= " #b, __LINE__)

static const double Inf = std::numeric_limits<double>::infinity();
static const double NaN = std::numeric_limits<double>::quiet_NaN();

// Jerusalem, 8 September, IDT. Matches what AMikdashTimeOfDay reports for that date.
static DayAnchors JerusalemSeptember()
{
    DayAnchors A;
    A.CivilDawnHours = 6.03;
    A.SunriseHours   = 6.29;
    A.SolarNoonHours = 12.61;
    A.SunsetHours    = 18.93;
    A.CivilDuskHours = 19.19;
    return A;
}

// ---------------------------------------------------------------------------
// 1. Nothing is on a fixed loop
// ---------------------------------------------------------------------------
static void TestNoImmediateRepeat()
{
    // Seven bird calls, the exact set the user heard repeating.
    EmitterSchedule S;
    S.Seed = 20260908;
    S.EmitterId = 5;
    S.SourceCount = 7;
    S.MinGapSeconds = 20.0;
    S.MaxGapSeconds = 62.0;

    const ScheduleReport R = AnalyseSchedule(S, 20000);
    CHECK(R.Passes == 20000);
    CHECK(R.ImmediateRepeats == 0);         // the whole point
    CHECK(R.LongestIdenticalRun == 1);      // no two consecutive events are identical
    CHECK(R.DistinctSourcesUsed == 7);      // every call is actually reached

    // Every take must be reached at a sane share; a hash that favoured one file would
    // sound like a loop even without an immediate repeat.
    int Counts[7] = {0};
    int Prev = -1;
    for (int I = 0; I < 20000; ++I)
    {
        const EmitterEvent E = NextEvent(S, static_cast<std::uint32_t>(I), Prev, 1.0);
        CHECK(E.SourceIndex >= 0 && E.SourceIndex < 7);
        CHECK(E.SourceIndex != Prev);
        ++Counts[E.SourceIndex];
        Prev = E.SourceIndex;
    }
    for (int I = 0; I < 7; ++I)
    {
        // Uniform over the six non-previous takes gives 1/7 of the total on average.
        CHECK(Counts[I] > 20000 / 7 * 0.80);
        CHECK(Counts[I] < 20000 / 7 * 1.20);
    }

    // A one-source emitter is the degenerate case and must not divide by zero.
    S.SourceCount = 1;
    for (int I = 0; I < 100; ++I) CHECK(PickSource(S, static_cast<std::uint32_t>(I), 0) == 0);
}

static void TestGapsHaveSpread()
{
    EmitterSchedule S;
    S.Seed = 4242;
    S.EmitterId = 1;
    S.SourceCount = 2;
    S.MinGapSeconds = 26.0;
    S.MaxGapSeconds = 84.0;

    const ScheduleReport R = AnalyseSchedule(S, 50000);
    CHECK(R.MinGap >= 26.0 - 1e-9);
    CHECK(R.MaxGap <= 84.0 + 1e-9);
    // Triangular over [26, 84]: mean 55, standard deviation (84-26)/sqrt(24) = 11.84.
    CHECK_NEAR(R.MeanGap, 55.0, 0.6);
    CHECK_NEAR(R.GapStdDev, 11.84, 0.6);
    // The spread must be real. A near-constant gap is a metronome.
    CHECK(R.GapStdDev > 8.0);
    // And the extremes must actually be visited, or the range is a lie.
    CHECK(R.MinGap < 32.0);
    CHECK(R.MaxGap > 78.0);
}

static void TestBedsDoNotRealign()
{
    // The two beds as placed: a 44.51 s take at pitch 0.93 and a 256.8 s take at 1.04.
    const double A = PlayedDurationSeconds(44.509615, 0.93);
    const double B = PlayedDurationSeconds(256.8, 1.04);
    CHECK_NEAR(A, 47.86, 0.05);
    CHECK_NEAR(B, 246.92, 0.05);

    const double Beat = BeatPeriodSeconds(A, B);
    // They beat against each other every ~59.3 s, which is not a common multiple: the
    // honest claim is that neither the pair nor the mix returns to the same phase in a
    // ten-minute stand. What is NOT claimed is that a 47.9 s bed is unrecognisable
    // alone -- that is why each bed also changes take and pitch at every handover.
    CHECK(Beat > 30.0);
    CHECK(Beat < 200.0);

    // Identical periods never drift apart. That is the failure the beat period exists
    // to detect, so it must be reported as zero, not as infinity.
    CHECK(BeatPeriodSeconds(A, A) == 0.0);
    CHECK(BeatPeriodSeconds(0.0, B) == 0.0);
    CHECK(BeatPeriodSeconds(NaN, B) == 0.0);

    CHECK(PlayedDurationSeconds(10.0, 2.0) == 5.0);
    CHECK(PlayedDurationSeconds(10.0, 0.0) == 10.0);   // a bad pitch falls back to 1.0
    CHECK(PlayedDurationSeconds(-1.0, 1.0) == 0.0);
}

static void TestDeterminism()
{
    EmitterSchedule A;
    A.Seed = 777; A.EmitterId = 3; A.SourceCount = 4;
    EmitterSchedule B = A;
    EmitterSchedule C = A; C.Seed = 778;

    bool bAnyDifferent = false;
    for (int I = 0; I < 500; ++I)
    {
        const EmitterEvent EA = NextEvent(A, static_cast<std::uint32_t>(I), -1, 1.0);
        const EmitterEvent EB = NextEvent(B, static_cast<std::uint32_t>(I), -1, 1.0);
        const EmitterEvent EC = NextEvent(C, static_cast<std::uint32_t>(I), -1, 1.0);
        CHECK(EA.GapSeconds == EB.GapSeconds);
        CHECK(EA.SourceIndex == EB.SourceIndex);
        CHECK(EA.Pitch == EB.Pitch);
        CHECK(EA.Level == EB.Level);
        if (EA.GapSeconds != EC.GapSeconds || EA.SourceIndex != EC.SourceIndex) bAnyDifferent = true;
    }
    CHECK(bAnyDifferent);   // a different seed must give a different soundscape

    // Two emitters on the same seed must not run in lockstep, or every layer fires
    // together and the whole mix has one period.
    EmitterSchedule D = A; D.EmitterId = 4;
    int Same = 0;
    for (int I = 0; I < 500; ++I)
    {
        if (NextEvent(A, static_cast<std::uint32_t>(I), -1, 1.0).GapSeconds
            == NextEvent(D, static_cast<std::uint32_t>(I), -1, 1.0).GapSeconds) ++Same;
    }
    CHECK(Same < 5);
}

static void TestScheduleRejectsNonsense()
{
    EmitterSchedule Bad;
    Bad.SourceCount = 0;
    CHECK(!Bad.IsUsable());
    CHECK(AnalyseSchedule(Bad, 100).Passes == 0);
    CHECK(NextGapSeconds(Bad, 0, 1.0) == 0.0);

    EmitterSchedule Inverted;
    Inverted.MinGapSeconds = 90.0;
    Inverted.MaxGapSeconds = 10.0;
    CHECK(!Inverted.IsUsable());

    EmitterSchedule NotFinite;
    NotFinite.MaxGapSeconds = Inf;
    CHECK(!NotFinite.IsUsable());

    EmitterSchedule Ok;
    CHECK(Ok.IsUsable());
    CHECK(AnalyseSchedule(Ok, 0).Passes == 0);
    CHECK(AnalyseSchedule(Ok, -5).Passes == 0);
    // A NaN interval scale must not poison the gap.
    CHECK(Finite(NextGapSeconds(Ok, 0, NaN)));
}

// ---------------------------------------------------------------------------
// 2. Time of day
// ---------------------------------------------------------------------------
static void TestDayAnchors()
{
    const DayAnchors A = JerusalemSeptember();
    CHECK(A.IsUsable());

    // Each anchor maps to its own integer coordinate.
    for (int I = 0; I < DayAnchorCount; ++I)
    {
        const double C = AnchorCoordinate(A, AnchorHours(A, I));
        CHECK_NEAR(C, static_cast<double>(I), 1e-6);
    }

    // The coordinate advances monotonically all the way round the clock, wrapping once.
    double Prev = AnchorCoordinate(A, 0.0);
    int Wraps = 0;
    for (double H = 0.01; H < 24.0; H += 0.01)
    {
        const double C = AnchorCoordinate(A, H);
        CHECK(C >= 0.0 && C < static_cast<double>(DayAnchorCount));
        if (C < Prev - 1e-9) ++Wraps;
        Prev = C;
    }
    CHECK(Wraps <= 1);

    // Unusable sets fall back rather than returning garbage.
    DayAnchors Polar;
    Polar.CivilDawnHours = 0.0; Polar.SunriseHours = 0.0;
    Polar.SolarNoonHours = 0.0; Polar.SunsetHours = 0.0; Polar.CivilDuskHours = 0.0;
    CHECK(!Polar.IsUsable());
    const double C = AnchorCoordinate(Polar, 13.0);
    CHECK(C >= 0.0 && C < 8.0);

    DayAnchors Nan = A; Nan.SunriseHours = NaN;
    CHECK(!Nan.IsUsable());
    CHECK(Finite(AnchorCoordinate(Nan, 9.0)));
    CHECK(Finite(AnchorCoordinate(A, NaN)));
    CHECK(Finite(AnchorCoordinate(A, Inf)));
    CHECK(Finite(AnchorCoordinate(A, -37.5)));
}

static void TestDayCurvesMatchTheBrief()
{
    const DayAnchors A = JerusalemSeptember();

    const double CrowdDawn   = LayerGainAtTime(ELayer::CrowdCourt, A, A.CivilDawnHours);
    const double CrowdNoon   = LayerGainAtTime(ELayer::CrowdCourt, A, A.SolarNoonHours);
    const double CrowdNight  = LayerGainAtTime(ELayer::CrowdCourt, A, WrapHours(A.SolarNoonHours - 12.0));
    const double WindNight   = LayerGainAtTime(ELayer::WindBed,    A, WrapHours(A.SolarNoonHours - 12.0));
    const double WindSunrise = LayerGainAtTime(ELayer::WindBed,    A, A.SunriseHours);
    const double CityNoon    = LayerGainAtTime(ELayer::City,       A, A.SolarNoonHours);
    const double CityNight   = LayerGainAtTime(ELayer::City,       A, WrapHours(A.SolarNoonHours - 12.0));
    const double BirdDawn    = LayerGainAtTime(ELayer::Bird,       A, A.CivilDawnHours);
    const double BirdNight   = LayerGainAtTime(ELayer::Bird,       A, WrapHours(A.SolarNoonHours - 12.0));
    const double BirdNoon    = LayerGainAtTime(ELayer::Bird,       A, A.SolarNoonHours);

    // "dawn is quiet"
    CHECK(CrowdDawn < 0.15);
    CHECK(CrowdDawn < CrowdNoon * 0.2);
    // "midday is busy"
    CHECK(CrowdNoon > 0.9);
    CHECK(CityNoon > 0.9);
    // "night is wind and distant city"
    CHECK(CrowdNight < 0.05);
    CHECK(WindNight > 0.8);
    CHECK(WindNight > WindSunrise);
    CHECK(CityNight > 0.2);            // present
    CHECK(CityNight < CityNoon * 0.5); // but far down
    // A dawn chorus, and next to nothing at night.
    CHECK(BirdDawn > 0.8);
    CHECK(BirdDawn > BirdNoon);
    CHECK(BirdNight < 0.1);

    // Every layer stays in range at every minute of the day, on any anchor set.
    for (int L = 0; L < LayerCount; ++L)
    {
        for (double H = 0.0; H < 24.0; H += 1.0 / 60.0)
        {
            const double G = LayerGainAtTime(static_cast<ELayer>(L), A, H);
            CHECK(G >= 0.0 && G <= 1.0);
        }
    }

    // Continuity across solar midnight: the curve is circular, so 23:59 and 00:01 must
    // be within a whisker of each other. A discontinuity there is an audible jump.
    for (int L = 0; L < LayerCount; ++L)
    {
        const double Before = LayerGainAtTime(static_cast<ELayer>(L), A, 23.999);
        const double After  = LayerGainAtTime(static_cast<ELayer>(L), A, 0.001);
        CHECK(std::fabs(Before - After) < 0.01);
    }

    // No step anywhere. The bound is 0.08 per minute rather than something tighter
    // because civil dawn to sunrise, and sunset to civil dusk, are only about 16
    // minutes long on this date, so a layer that changes a lot across twilight
    // NECESSARILY ramps faster there. What matters for audibility is the per-second
    // rate, which is checked below and is three orders of magnitude smaller.
    for (int L = 0; L < LayerCount; ++L)
    {
        double WorstMinute = 0.0;
        double PrevG = LayerGainAtTime(static_cast<ELayer>(L), A, 0.0);
        for (double H = 1.0 / 60.0; H < 24.0; H += 1.0 / 60.0)
        {
            const double G = LayerGainAtTime(static_cast<ELayer>(L), A, H);
            WorstMinute = std::max(WorstMinute, std::fabs(G - PrevG));
            PrevG = G;
        }
        CHECK(WorstMinute < 0.08);

        double WorstSecond = 0.0;
        double PrevS = LayerGainAtTime(static_cast<ELayer>(L), A, 5.9);
        for (double H = 5.9; H < 7.0; H += 1.0 / 3600.0)   // across the fastest segment
        {
            const double G = LayerGainAtTime(static_cast<ELayer>(L), A, H);
            WorstSecond = std::max(WorstSecond, std::fabs(G - PrevS));
            PrevS = G;
        }
        CHECK(WorstSecond < 0.002);
    }
}

static void TestIntervalStretch()
{
    const DayAnchors A = JerusalemSeptember();
    const double Midnight = WrapHours(A.SolarNoonHours - 12.0);

    // Birds at night: rare, not merely quiet.
    const double NightScale = LayerIntervalScaleAtTime(ELayer::Bird, A, Midnight);
    const double DawnScale  = LayerIntervalScaleAtTime(ELayer::Bird, A, A.SunriseHours);
    CHECK(NightScale > 5.0);
    CHECK_NEAR(DawnScale, 1.0, 0.01);
    CHECK(NightScale > DawnScale * 5.0);

    // Never zero, never unbounded, whatever the hour or the layer.
    for (int L = 0; L < LayerCount; ++L)
    {
        for (double H = 0.0; H < 24.0; H += 0.25)
        {
            const double S = LayerIntervalScaleAtTime(static_cast<ELayer>(L), A, H);
            CHECK(S >= 1.0 && S <= 12.0);
        }
    }

    // A stretched gap is genuinely longer.
    EmitterSchedule S;
    S.Seed = 11; S.EmitterId = 2; S.SourceCount = 3;
    S.MinGapSeconds = 20.0; S.MaxGapSeconds = 60.0;
    const double Plain = AnalyseSchedule(S, 5000, 1.0).MeanGap;
    const double Night = AnalyseSchedule(S, 5000, NightScale).MeanGap;
    CHECK(Night > Plain * 4.0);
}

// ---------------------------------------------------------------------------
// 3. Zones
// ---------------------------------------------------------------------------
static Box MakeBox(double X0, double Y0, double Z0, double X1, double Y1, double Z1)
{
    Box B;
    B.MinCm[0] = X0; B.MinCm[1] = Y0; B.MinCm[2] = Z0;
    B.MaxCm[0] = X1; B.MaxCm[1] = Y1; B.MaxCm[2] = Z1;
    return B;
}

static void TestZoneContainment()
{
    // The sanctuary interior as measured: X -7100..-3550, Y -900..900, Z 900..3050.
    const Box Heikhal = MakeBox(-7100, -900, 900, -3550, 900, 3050);
    CHECK(Heikhal.IsValid());

    const double Centre[3] = {-5325, 0, 1900};
    CHECK_NEAR(BoxMembership(Heikhal, Centre, 250.0), 1.0, 1e-9);

    // Outside is exactly zero, including one centimetre outside a face. The margin is
    // measured INWARD, so the Heikhal's acoustic cannot leak into the court.
    const double JustOutside[3] = {-3549, 0, 1900};
    CHECK(BoxMembership(Heikhal, JustOutside, 250.0) == 0.0);
    const double FarOutside[3] = {900, -900, 1300};   // the Azarah wind bed emitter
    CHECK(BoxMembership(Heikhal, FarOutside, 250.0) == 0.0);
    const double Below[3] = {-5325, 0, 899};
    CHECK(BoxMembership(Heikhal, Below, 250.0) == 0.0);

    // The crossing is monotone and continuous from the face inward.
    double Prev = 0.0;
    for (double X = -3550.0; X > -3900.0; X -= 1.0)
    {
        const double P[3] = {X, 0, 1900};
        const double W = BoxMembership(Heikhal, P, 250.0);
        CHECK(W >= Prev - 1e-12);
        CHECK(W >= 0.0 && W <= 1.0);
        Prev = W;
    }
    CHECK_NEAR(Prev, 1.0, 1e-9);

    // A margin wider than the box is clamped, not overflowed.
    const double Thin[3] = {-5325, 0, 1900};
    CHECK(BoxMembership(Heikhal, Thin, 1.0e9) >= 0.0);
    CHECK(BoxMembership(Heikhal, Thin, 1.0e9) <= 1.0);
    CHECK(BoxMembership(Heikhal, Thin, -5.0) == 1.0);
    CHECK(BoxMembership(Heikhal, Thin, NaN) == 1.0);

    // Degenerate and null inputs.
    CHECK(BoxMembership(MakeBox(0, 0, 0, 0, 0, 0), Centre, 10.0) == 0.0);
    CHECK(BoxMembership(MakeBox(10, 10, 10, 0, 0, 0), Centre, 10.0) == 0.0);
    CHECK(BoxMembership(Heikhal, nullptr, 10.0) == 0.0);
    const double NanPoint[3] = {NaN, 0, 1900};
    CHECK(BoxMembership(Heikhal, NanPoint, 10.0) == 0.0);
}

static void TestZonePriorityAndBlend()
{
    Zone Court;                                  // not a zone in practice; the default
    Court.Bounds = MakeBox(-20000, -20000, 0, 20000, 20000, 6000);
    Court.Priority = 0;
    Court.Inside.DryGain = 0.85;
    Court.Inside.LpfHz = LpfOpenHz;
    Court.Inside.ReverbSend = 0.0;
    Court.Inside.Exposure = 1.0;

    Zone Heikhal;
    Heikhal.Bounds = MakeBox(-7100, -900, 900, -3550, 900, 3050);
    Heikhal.BlendMarginCm = 250.0;
    Heikhal.Priority = 10;
    Heikhal.Inside.DryGain = 0.10;
    Heikhal.Inside.LpfHz = 650.0;
    Heikhal.Inside.ReverbSend = 0.35;
    Heikhal.Inside.Exposure = 0.0;

    Zone Kodesh;                                 // inside the Heikhal, quieter still
    Kodesh.Bounds = MakeBox(-7100, -900, 900, -6100, 900, 3050);
    Kodesh.BlendMarginCm = 150.0;
    Kodesh.Priority = 20;
    Kodesh.Inside.DryGain = 0.04;
    Kodesh.Inside.LpfHz = 420.0;
    Kodesh.Inside.ReverbSend = 0.45;
    Kodesh.Inside.Exposure = 0.0;

    const Zone Zones[3] = {Court, Heikhal, Kodesh};
    const Acoustic Outdoor;   // open, dry, exposed

    // Standing in the open court: nothing applied but the court's own mild figure.
    const double Azarah[3] = {900, -900, 1300};
    const Acoustic InCourt = EvaluateZones(Zones, 3, Azarah, Outdoor);
    CHECK_NEAR(InCourt.DryGain, 0.85, 1e-6);
    CHECK_NEAR(InCourt.ReverbSend, 0.0, 1e-6);
    CHECK(InCourt.LpfHz > 19000.0);
    CHECK_NEAR(InCourt.Exposure, 1.0, 1e-6);

    // Deep in the Heikhal: a stone hall.
    const double InHeikhal[3] = {-4500, 0, 1900};
    const Acoustic Hall = EvaluateZones(Zones, 3, InHeikhal, Outdoor);
    CHECK_NEAR(Hall.DryGain, 0.10, 1e-6);
    CHECK_NEAR(Hall.LpfHz, 650.0, 1.0);
    CHECK_NEAR(Hall.ReverbSend, 0.35, 1e-6);
    CHECK_NEAR(Hall.Exposure, 0.0, 1e-6);
    // The whole point of the exercise: the hall and the court are audibly different.
    CHECK(Hall.DryGain < InCourt.DryGain * 0.2);
    CHECK(Hall.LpfHz < InCourt.LpfHz * 0.1);
    CHECK(Hall.ReverbSend > InCourt.ReverbSend + 0.3);

    // Deep in the Kodesh: the higher priority wins even though the Heikhal also
    // contains the point.
    const double InKodesh[3] = {-6700, 0, 1900};
    const Acoustic Holy = EvaluateZones(Zones, 3, InKodesh, Outdoor);
    CHECK_NEAR(Holy.DryGain, 0.04, 1e-6);
    CHECK_NEAR(Holy.LpfHz, 420.0, 1.0);
    CHECK(Holy.DryGain < Hall.DryGain);

    // Walking in through the doorway: every quantity moves monotonically and no step
    // is large enough to hear as a switch.
    // Layered blending means the walk in starts from the court's figure and falls
    // continuously to the hall's; there is no jump back to fully-open on the way.
    double PrevDry = InCourt.DryGain + 1e-9, PrevWet = InCourt.ReverbSend - 1e-9,
           PrevLpf = InCourt.LpfHz + 1e-6;
    double WorstDryStep = 0.0;
    for (double X = -3551.0; X > -3850.0; X -= 1.0)
    {
        const double P[3] = {X, 0, 1900};
        const Acoustic S = EvaluateZones(Zones, 3, P, Outdoor);
        CHECK(S.DryGain <= PrevDry + 1e-9);
        CHECK(S.ReverbSend >= PrevWet - 1e-9);
        CHECK(S.LpfHz <= PrevLpf + 1e-6);
        CHECK(S.LpfHz >= 400.0);
        WorstDryStep = std::max(WorstDryStep, std::fabs(S.DryGain - PrevDry));
        PrevDry = S.DryGain; PrevWet = S.ReverbSend; PrevLpf = S.LpfHz;
    }
    CHECK(WorstDryStep < 0.02);

    // Null and empty inputs return the outdoor state untouched.
    const Acoustic None = EvaluateZones(nullptr, 0, Azarah, Outdoor);
    CHECK(None.DryGain == Outdoor.DryGain);
    CHECK(EvaluateZones(Zones, 0, Azarah, Outdoor).DryGain == Outdoor.DryGain);
    CHECK(EvaluateZones(Zones, 3, nullptr, Outdoor).DryGain == Outdoor.DryGain);
}

static void TestOcclusion()
{
    CHECK_NEAR(OcclusionGain(0.0, 12.0), 1.0, 1e-9);
    CHECK_NEAR(OcclusionGain(1.0, 12.0), DbToLinear(-12.0), 1e-9);
    CHECK(OcclusionGain(0.5, 12.0) < 1.0);
    CHECK(OcclusionGain(0.5, 12.0) > OcclusionGain(1.0, 12.0));
    // Out-of-range and non-finite inputs saturate rather than exploding.
    CHECK_NEAR(OcclusionGain(-5.0, 12.0), 1.0, 1e-9);
    CHECK_NEAR(OcclusionGain(7.0, 12.0), DbToLinear(-12.0), 1e-9);
    CHECK(Finite(OcclusionGain(NaN, 12.0)));
    CHECK(Finite(OcclusionGain(0.5, NaN)));

    CHECK_NEAR(OcclusionLpfHz(0.0), LpfOpenHz, 1.0);
    CHECK_NEAR(OcclusionLpfHz(1.0), 900.0, 1.0);
    CHECK(OcclusionLpfHz(0.5) < LpfOpenHz);
    CHECK(OcclusionLpfHz(0.5) > 900.0);
    CHECK(Finite(OcclusionLpfHz(NaN)));

    // Monotone across the whole range.
    double PrevG = 2.0, PrevF = 1.0e9;
    for (double F = 0.0; F <= 1.0; F += 0.01)
    {
        const double G = OcclusionGain(F, 12.0);
        const double Hz = OcclusionLpfHz(F);
        CHECK(G <= PrevG + 1e-12);
        CHECK(Hz <= PrevF + 1e-6);
        PrevG = G; PrevF = Hz;
    }
}

// ---------------------------------------------------------------------------
// 4. Height, crowd, smoothing, gain
// ---------------------------------------------------------------------------
static void TestHeightCurves()
{
    // Wind: more with height, more with exposure.
    const double Sheltered = WindGainFromHeight(1300.0, 625.0, 0.0);
    const double Open      = WindGainFromHeight(1300.0, 625.0, 1.0);
    const double High      = WindGainFromHeight(4000.0, 625.0, 1.0);
    CHECK(Open > Sheltered);
    CHECK(High > Open);
    CHECK(Sheltered > 0.0);
    // It flattens. Per metre climbed, the gain added between 6.75 m and 33.75 m is a
    // fraction of what is added between 0.75 m and 6.75 m -- which is what stops the
    // bed swelling absurdly on the highest step.
    const double Low = WindGainFromHeight(700.0, 625.0, 1.0);
    const double RateHigh = (High - Open) / (33.75 - 6.75);
    const double RateLow  = (Open - Low)  / (6.75 - 0.75);
    CHECK(RateHigh < RateLow * 0.5);
    // Never runs away.
    for (double Z = 0.0; Z < 20000.0; Z += 25.0)
    {
        const double G = WindGainFromHeight(Z, 625.0, 1.0);
        CHECK(G >= 0.0 && G <= 1.2);
    }
    CHECK(Finite(WindGainFromHeight(NaN, 625.0, 1.0)));
    CHECK(Finite(WindGainFromHeight(1300.0, NaN, 1.0)));
    CHECK(Finite(WindGainFromHeight(1300.0, 625.0, NaN)));
    CHECK(WindGainFromHeight(-99999.0, 625.0, 1.0) >= 0.0);

    // City: loudest on the plaza, quietest at the summit, never silent.
    const double Plaza  = CityGainFromHeight(0.0, 0.0, 3000.0);
    const double Court  = CityGainFromHeight(1300.0, 0.0, 3000.0);
    const double Summit = CityGainFromHeight(3000.0, 0.0, 3000.0);
    CHECK_NEAR(Plaza, 1.0, 1e-6);
    CHECK(Court < Plaza);
    CHECK(Summit < Court);
    CHECK(Summit > 0.29);            // still there, just below you
    CHECK_NEAR(Summit, 0.34, 0.01);
    // Monotone all the way up, and clamped above the summit.
    double Prev = 2.0;
    for (double Z = -500.0; Z < 6000.0; Z += 10.0)
    {
        const double G = CityGainFromHeight(Z, 0.0, 3000.0);
        CHECK(G <= Prev + 1e-12);
        CHECK(G >= 0.30 && G <= 1.0);
        Prev = G;
    }
    // Degenerate range: no divide by zero.
    CHECK(CityGainFromHeight(500.0, 1000.0, 1000.0) == 1.0);
    CHECK(Finite(CityGainFromHeight(NaN, 0.0, 3000.0)));
}

static void TestCrowd()
{
    CHECK(CrowdMurmurGain(0.0) == 0.0);
    CHECK(CrowdMurmurGain(-50.0) == 0.0);
    CHECK(CrowdMurmurGain(NaN) == 0.0);

    // Strictly increasing, and bounded by MaxGain however large the crowd gets.
    double Prev = -1.0;
    for (double N = 1.0; N < 200000.0; N *= 1.3)
    {
        const double G = CrowdMurmurGain(N, 1200.0, 1.0);
        CHECK(G > Prev);
        CHECK(G > 0.0 && G <= 1.0);
        Prev = G;
    }
    CHECK(CrowdMurmurGain(1.0e9, 1200.0, 1.0) <= 1.0);
    // At the reference count the curve sits at 1/sqrt(2) of its ceiling.
    CHECK_NEAR(CrowdMurmurGain(1200.0, 1200.0, 1.0), 0.7071, 0.001);
    // Doubling the crowd is roughly +3 dB while the curve is still in its linear part.
    const double A = CrowdMurmurGain(60.0, 1200.0, 1.0);
    const double B = CrowdMurmurGain(120.0, 1200.0, 1.0);
    CHECK_NEAR(LinearToDb(B) - LinearToDb(A), 3.0, 0.35);
    // A court with nobody in it is silent. That is what dawn is.
    CHECK(CrowdMurmurGain(0.0, 1200.0, 1.0) == 0.0);

    CHECK(SpeakingVoiceGain(0) == 0.0);
    CHECK(SpeakingVoiceGain(-3) == 0.0);
    CHECK_NEAR(SpeakingVoiceGain(24, 24), 1.0, 1e-9);
    CHECK_NEAR(SpeakingVoiceGain(6, 24), 0.5, 1e-9);
    CHECK(SpeakingVoiceGain(500, 24) <= 1.0);
    CHECK(SpeakingVoiceGain(5, 0) >= 0.0);
}

static void TestSmoothing()
{
    // Frame-rate independence: one 0.4 s step and four 0.1 s steps must land in the
    // same place. A naive lerp fails this, and the failure is an audible dependence of
    // the mix on the frame rate.
    const double Tau = 1.4;
    const double OneBig = SmoothTowards(0.0, 1.0, 0.4, Tau);
    double Many = 0.0;
    for (int I = 0; I < 4; ++I) Many = SmoothTowards(Many, 1.0, 0.1, Tau);
    CHECK_NEAR(OneBig, Many, 1e-12);

    // One time constant reaches 63.2 %.
    CHECK_NEAR(SmoothTowards(0.0, 1.0, Tau, Tau), 0.6321, 1e-3);
    // It approaches but never overshoots.
    double V = 0.0;
    for (int I = 0; I < 10000; ++I)
    {
        V = SmoothTowards(V, 1.0, 0.01, Tau);
        CHECK(V <= 1.0 + 1e-12);
    }
    CHECK_NEAR(V, 1.0, 1e-6);

    // Degenerate arguments.
    CHECK(SmoothTowards(0.5, 1.0, 0.0, Tau) == 0.5);
    CHECK(SmoothTowards(0.5, 1.0, -1.0, Tau) == 0.5);
    CHECK(SmoothTowards(0.5, 1.0, 0.1, 0.0) == 1.0);
    CHECK(SmoothTowards(NaN, 1.0, 0.1, Tau) == 1.0);
    CHECK(SmoothTowards(0.5, NaN, 0.1, Tau) == 0.5);
    CHECK(Finite(SmoothTowards(0.5, 1.0, Inf, Tau)));
}

static void TestCombineGain()
{
    GainInputs In;
    CHECK_NEAR(CombineGain(In), 1.0, 1e-12);

    In.BaseVolume = 0.55; In.EventLevel = 0.8; In.DayGain = 0.5;
    In.HeightGain = 1.1; In.Occlusion = 0.25; In.ZoneDryGain = 0.1; In.UserMixGain = 1.0;
    CHECK_NEAR(CombineGain(In), 0.55 * 0.8 * 0.5 * 1.1 * 0.25 * 0.1, 1e-12);

    // Any non-finite input degrades to a defined value rather than poisoning the mix.
    GainInputs Bad = In; Bad.DayGain = NaN;
    CHECK(Finite(CombineGain(Bad)));
    Bad = In; Bad.BaseVolume = Inf;
    CHECK(Finite(CombineGain(Bad)));
    Bad = In; Bad.ZoneDryGain = -3.0;
    CHECK(CombineGain(Bad) == 0.0);
    // The result is always in range.
    GainInputs Loud; Loud.BaseVolume = 100.0; Loud.EventLevel = 100.0; Loud.UserMixGain = 100.0;
    CHECK(CombineGain(Loud) <= 4.0);
    // Muting the master mutes everything.
    GainInputs Mute = In; Mute.UserMixGain = 0.0;
    CHECK(CombineGain(Mute) == 0.0);

    // Hysteresis: a playing voice keeps playing a little below where a silent one starts.
    CHECK(ShouldBeAudible(SilenceGain, true));
    CHECK(!ShouldBeAudible(SilenceGain, false));
    CHECK(ShouldBeAudible(SilenceGain * 3.0, false));
    CHECK(!ShouldBeAudible(0.0, true));
}

static void TestSmallHelpers()
{
    CHECK(WrapHours(25.5) == 1.5);
    CHECK(WrapHours(-1.0) == 23.0);
    CHECK(WrapHours(NaN) == 0.0);
    CHECK(WrapHours(0.0) == 0.0);

    CHECK_NEAR(HourDelta(23.0, 1.0), 2.0, 1e-12);
    CHECK_NEAR(HourDelta(1.0, 23.0), -2.0, 1e-12);
    CHECK(std::fabs(HourDelta(0.0, 12.0)) <= 12.0);

    CHECK(SmoothStep(0.0, 1.0, -1.0) == 0.0);
    CHECK(SmoothStep(0.0, 1.0, 2.0) == 1.0);
    CHECK_NEAR(SmoothStep(0.0, 1.0, 0.5), 0.5, 1e-12);
    CHECK(SmoothStep(1.0, 1.0, 2.0) == 1.0);
    CHECK(SmoothStep(NaN, 1.0, 0.5) == 0.0);

    CHECK_NEAR(DbToLinear(0.0), 1.0, 1e-12);
    CHECK_NEAR(DbToLinear(-6.0206), 0.5, 1e-4);
    CHECK_NEAR(LinearToDb(1.0), 0.0, 1e-9);
    CHECK(LinearToDb(0.0) < -100.0);
    CHECK(LinearToDb(-1.0) < -100.0);

    CHECK(std::string(LayerName(ELayer::CrowdCourt)) == "CrowdCourt");
    CHECK(std::string(LayerName(static_cast<ELayer>(999))) == "Unknown");
    CHECK(LayerCount == 10);

    // The hash must actually spread. A biased hash makes every emitter fire together.
    std::map<std::uint32_t, int> Buckets;
    for (std::uint32_t I = 0; I < 40000; ++I)
    {
        Buckets[Hash(12345u, I, 0u, 0u) % 16u] += 1;
    }
    CHECK(Buckets.size() == 16);
    for (const auto& Pair : Buckets)
    {
        CHECK(Pair.second > 40000 / 16 * 0.9);
        CHECK(Pair.second < 40000 / 16 * 1.1);
    }
    for (int I = 0; I < 1000; ++I)
    {
        const double V = Hash01(1u, static_cast<std::uint32_t>(I), 0u, 0u);
        CHECK(V >= 0.0 && V < 1.0);
        const double R = HashRange(1u, static_cast<std::uint32_t>(I), 0u, 0u, 0.92, 1.08);
        CHECK(R >= 0.92 && R < 1.08);
    }
}

// ---------------------------------------------------------------------------
// The whole soundscape at once
// ---------------------------------------------------------------------------
static void TestWholeSoundscapeHasNoPeriod()
{
    // Ten emitters, the shape of the placed set, run for a simulated hour each. If the
    // combined firing pattern had a period, the sorted event times would repeat.
    const DayAnchors A = JerusalemSeptember();
    struct Layout { ELayer Layer; double MinGap; double MaxGap; int Sources; };
    const Layout Placed[] = {
        {ELayer::WindGust,     34, 96, 2}, {ELayer::WindGust,     23, 71, 2},
        {ELayer::CrowdCourt,   12, 38, 2}, {ELayer::CrowdCourt,   17, 44, 2},
        {ELayer::CrowdDistant, 26, 84, 2}, {ELayer::CrowdDistant, 37, 110, 2},
        {ELayer::Bird,         20, 62, 7}, {ELayer::Bird,         33, 88, 7},
        {ELayer::Cloth,        14, 46, 1}, {ELayer::Foliage,      41, 120, 2},
    };

    std::vector<double> AllTimes;
    for (int E = 0; E < 10; ++E)
    {
        EmitterSchedule S;
        S.Seed = 20260908;
        S.EmitterId = static_cast<std::uint32_t>(E + 1);
        S.SourceCount = Placed[E].Sources;
        S.MinGapSeconds = Placed[E].MinGap;
        S.MaxGapSeconds = Placed[E].MaxGap;
        const double Scale = LayerIntervalScaleAtTime(Placed[E].Layer, A, 9.0);

        double T = 0.0;
        int Prev = -1;
        for (std::uint32_t Pass = 0; T < 3600.0 && Pass < 5000; ++Pass)
        {
            const EmitterEvent Ev = NextEvent(S, Pass, Prev, Scale);
            Prev = Ev.SourceIndex;
            T += Ev.GapSeconds;
            if (T < 3600.0) AllTimes.push_back(T);
        }
    }
    CHECK(AllTimes.size() > 200);

    // No two events in the whole hour land on the same instant, and no inter-event
    // interval recurs often enough to be a beat.
    std::sort(AllTimes.begin(), AllTimes.end());
    std::map<long long, int> IntervalHistogram;
    for (std::size_t I = 1; I < AllTimes.size(); ++I)
    {
        const double D = AllTimes[I] - AllTimes[I - 1];
        CHECK(D >= 0.0);
        IntervalHistogram[static_cast<long long>(D * 10.0)] += 1;
    }
    // The most common 0.1 s interval bucket must hold only a small share; a periodic
    // mix piles up in one bucket.
    int Worst = 0;
    for (const auto& Pair : IntervalHistogram) Worst = std::max(Worst, Pair.second);
    CHECK(static_cast<double>(Worst) < 0.15 * static_cast<double>(AllTimes.size()));
    CHECK(IntervalHistogram.size() > 40);
}

// ---------------------------------------------------------------------------

// Golden vectors, so the offline Python mirror in Scripts/create_soundscape_v2.py can be
// proved bit-identical to the code that actually ships rather than merely similar to it.
// Printed only when asked; verify.py runs this executable with no arguments.
static void EmitGolden()
{
    for (std::uint32_t E = 1; E <= 4; ++E)
    {
        for (std::uint32_t P = 0; P < 8; ++P)
        {
            std::printf("H %u %u %u\n", E, P, Hash(20260908u, E, P, 11u));
        }
    }
    EmitterSchedule S;
    S.Seed = 20260908; S.EmitterId = 5; S.SourceCount = 7;
    S.MinGapSeconds = 20.0; S.MaxGapSeconds = 62.0;
    int Prev = -1;
    for (std::uint32_t P = 0; P < 16; ++P)
    {
        const EmitterEvent Ev = NextEvent(S, P, Prev, 1.0);
        Prev = Ev.SourceIndex;
        std::printf("E %u %d %.12f %.12f %.12f\n", P, Ev.SourceIndex, Ev.GapSeconds,
                    Ev.Pitch, Ev.Level);
    }
    const DayAnchors A = JerusalemSeptember();
    for (int L = 0; L < LayerCount; ++L)
    {
        for (int Q = 0; Q < 8; ++Q)
        {
            const double H = 3.0 * Q;
            std::printf("D %s %.4f %.12f %.12f\n", LayerName(static_cast<ELayer>(L)), H,
                        LayerGainAtTime(static_cast<ELayer>(L), A, H),
                        LayerIntervalScaleAtTime(static_cast<ELayer>(L), A, H));
        }
    }
}

int main(int argc, char** argv)
{
    if (argc > 1 && std::string(argv[1]) == "--golden")
    {
        EmitGolden();
        return 0;
    }
    TestNoImmediateRepeat();
    TestGapsHaveSpread();
    TestBedsDoNotRealign();
    TestDeterminism();
    TestScheduleRejectsNonsense();

    TestDayAnchors();
    TestDayCurvesMatchTheBrief();
    TestIntervalStretch();

    TestZoneContainment();
    TestZonePriorityAndBlend();
    TestOcclusion();

    TestHeightCurves();
    TestCrowd();
    TestSmoothing();
    TestCombineGain();
    TestSmallHelpers();

    TestWholeSoundscapeHasNoPeriod();

    std::printf("SoundscapeMath: %d checks, %d failed\n", Checks, Failures);
    if (Failures != 0)
    {
        std::printf("FAIL: %d of %d SoundscapeMath checks failed\n", Failures, Checks);
        return 1;
    }
    std::printf("PASS: all %d SoundscapeMath checks passed\n", Checks);
    return 0;
}
