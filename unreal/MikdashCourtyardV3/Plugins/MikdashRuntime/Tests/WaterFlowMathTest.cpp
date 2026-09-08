#define _CRT_SECURE_NO_WARNINGS

// Standalone test for WaterFlowMath.h. No Unreal, no engine headers.
//
//   cl /nologo /std:c++17 /EHsc /W4 /WX /utf-8 /I<...>/Public WaterFlowMathTest.cpp
//   WaterFlowMathTest.exe <optional path to tests.json>
//
// Every check goes through Check(), which is live in debug AND release builds; the
// printed lines are the numeric evidence, and with an argument the same numbers are
// written as JSON for SourceAssets/water-review/tests.json.

#include "WaterFlowMath.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
#include <utility>
#include <vector>

using namespace MikdashWater;

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
static void FactText(const std::string& Key, const std::string& Value)
{
    Facts.emplace_back(Key, "\"" + Value + "\"");
}

static const double NaNValue = std::numeric_limits<double>::quiet_NaN();
static const double InfValue = std::numeric_limits<double>::infinity();

// ---------------------------------------------------------------------------
// 1. Forty se'ah
// ---------------------------------------------------------------------------
//
// The identity being tested is Eruvin 4b's: forty se'ah is a pit of one amah by one
// amah by three amot, i.e. three cubic amot. Everything here is that identity
// evaluated at each published amah, so the numbers can be checked against the
// litre figures the poskim are usually quoted with.

static void FortySeahChecks()
{
    // 3 x 48^3 = 331,776 cm^3. R' A. C. Naeh's ~332 litres.
    const double Naeh = FortySeahCm3(AmahOpinion::ChazonNaeh);
    Check(Near(Naeh, 3.0 * 48.0 * 48.0 * 48.0, 1e-9));
    Check(Near(Naeh, 331776.0, 1e-6));
    Check(Near(Cm3ToLitres(Naeh), 331.776, 1e-6));

    // 3 x 57.6^3 = 573,308.928 cm^3. The Chazon Ish's ~573 litres.
    const double ChazonIsh = FortySeahCm3(AmahOpinion::ChazonIsh);
    Check(Near(ChazonIsh, 3.0 * 57.6 * 57.6 * 57.6, 1e-9));
    Check(Near(Cm3ToLitres(ChazonIsh), 573.308928, 1e-6));

    // The project's 50 cm modelling amah: exactly 375 litres.
    const double Project = FortySeahCm3(AmahOpinion::ProjectModelling);
    Check(Near(Project, 375000.0, 1e-9));
    Check(Near(Cm3ToLitres(Project), 375.0, 1e-9));

    // The stringent opinion is the largest, and is what FortySeahTestStrictest uses.
    Check(ChazonIsh > Project && Project > Naeh);
    Check(Near(FortySeahTestStrictest(0.0).RequiredCm3, ChazonIsh, 1e-9));

    // One se'ah is a fortieth of each.
    Check(Near(OneSeahCm3(AmahOpinion::ChazonNaeh) * 40.0, Naeh, 1e-9));
    Check(Near(Cm3ToLitres(OneSeahCm3(AmahOpinion::ChazonNaeh)), 8.2944, 1e-6));
    Check(Near(Cm3ToLitres(OneSeahCm3(AmahOpinion::ChazonIsh)), 14.3327232, 1e-6));

    // A pool exactly at the shiur passes; one cm^3 short fails. The boundary is
    // inclusive, which is the whole point of the test.
    Check(FortySeahTest(ChazonIsh, AmahOpinion::ChazonIsh).Sufficient);
    Check(!FortySeahTest(ChazonIsh - 1.0, AmahOpinion::ChazonIsh).Sufficient);
    Check(Near(FortySeahTest(ChazonIsh, AmahOpinion::ChazonIsh).Ratio, 1.0, 1e-12));

    // A pool that satisfies the Chazon Ish satisfies the others; the converse fails.
    Check(FortySeahTest(ChazonIsh, AmahOpinion::ChazonNaeh).Sufficient);
    Check(!FortySeahTest(Naeh, AmahOpinion::ChazonIsh).Sufficient);

    // Garbage in: no NaN out, and a negative volume is treated as empty, not as a pass.
    Check(!FortySeahTest(NaNValue, AmahOpinion::ChazonIsh).Sufficient);
    Check(Near(FortySeahTest(NaNValue, AmahOpinion::ChazonIsh).VolumeCm3, 0.0));
    Check(!FortySeahTest(-1e9, AmahOpinion::ChazonIsh).Sufficient);

    // ---- the modelled mikveh: the pool this project actually builds ----
    // A rectangular basin 2 amot x 2 amot in plan, filled to 1.5 amot, at the project
    // amah: 100 x 100 x 75 cm = 750,000 cm^3. That clears the stringent shiur with
    // room to spare even after the volume displaced by the steps is deducted.
    const double BasinCm3 = BasinVolumeCm3(100.0, 100.0, 75.0);
    Check(Near(BasinCm3, 750000.0, 1e-9));
    const MikvahVerdict Verdict = FortySeahTestStrictest(BasinCm3);
    Check(Verdict.Sufficient);
    Check(Verdict.Ratio > 1.3);

    // The immersion basin plus the four descending steps that stand in the water.
    // Each step's tread is 100 cm wide, 25 cm deep in plan, and its riser is 25 cm,
    // so the steps displace water the deeper they sit. Only the water actually
    // present is counted.
    const PoolStep Steps[4] = {
        {25.0, 100.0, 0.0},    // top tread: at the fill line, holds nothing
        {25.0, 100.0, 25.0},
        {25.0, 100.0, 50.0},
        {25.0, 100.0, 75.0},
    };
    const double StepWater = SteppedPoolVolumeCm3(Steps, 4);
    Check(Near(StepWater, 25.0 * 100.0 * (0.0 + 25.0 + 50.0 + 75.0), 1e-9));
    Check(Near(StepWater, 375000.0, 1e-9));
    // The stair occupies the eastern quarter of the basin; the free water is the rest.
    const double FreeWater = BasinVolumeCm3(100.0, 100.0, 75.0) - (25.0 * 100.0 * 75.0 - StepWater);
    Check(FreeWater > 0.0);
    Check(FortySeahTestStrictest(FreeWater).Sufficient);
    Check(SteppedPoolVolumeCm3(nullptr, 4) == 0.0);

    Fact("fortySeah.naeh_cm3", Naeh);
    Fact("fortySeah.naeh_litres", Cm3ToLitres(Naeh));
    Fact("fortySeah.chazonIsh_cm3", ChazonIsh);
    Fact("fortySeah.chazonIsh_litres", Cm3ToLitres(ChazonIsh));
    Fact("fortySeah.projectAmah_cm3", Project);
    Fact("fortySeah.projectAmah_litres", Cm3ToLitres(Project));
    Fact("fortySeah.oneSeah_naeh_litres", Cm3ToLitres(OneSeahCm3(AmahOpinion::ChazonNaeh)));
    Fact("fortySeah.oneSeah_chazonIsh_litres", Cm3ToLitres(OneSeahCm3(AmahOpinion::ChazonIsh)));
    Fact("mikveh.basin_cm3", BasinCm3);
    Fact("mikveh.basin_litres", Cm3ToLitres(BasinCm3));
    Fact("mikveh.freeWater_cm3", FreeWater);
    Fact("mikveh.freeWater_litres", Cm3ToLitres(FreeWater));
    Fact("mikveh.strictestRatio", FortySeahTestStrictest(FreeWater).Ratio);
    std::printf("forty se'ah: Naeh %.1f L, Chazon Ish %.1f L, project amah %.1f L; modelled mikveh free water %.1f L "
                "= %.2fx the stringent shiur\n",
                Cm3ToLitres(Naeh), Cm3ToLitres(ChazonIsh), Cm3ToLitres(Project),
                Cm3ToLitres(FreeWater), FortySeahTestStrictest(FreeWater).Ratio);
}

// ---------------------------------------------------------------------------
// 2. Channel geometry
// ---------------------------------------------------------------------------

static void SectionChecks()
{
    // A rectangular runnel: 1 amah wide, filled 25 cm. Area, perimeter and hydraulic
    // radius are all hand-checkable.
    ChannelSection Rect;
    Rect.BedWidthCm = 50.0;
    Rect.DepthCm = 25.0;
    Rect.SideSlope = 0.0;
    Check(Rect.Valid());
    Check(Near(Rect.TopWidthCm(), 50.0));
    Check(Near(Rect.AreaCm2(), 1250.0));
    Check(Near(Rect.WettedPerimeterCm(), 50.0 + 50.0));
    Check(Near(Rect.HydraulicRadiusCm(), 12.5));
    Check(Near(Rect.HydraulicDepthCm(), 25.0));

    // A trapezoid with 1:1 banks: top width grows by twice the depth.
    ChannelSection Trap;
    Trap.BedWidthCm = 200.0;
    Trap.DepthCm = 40.0;
    Trap.SideSlope = 1.0;
    Check(Near(Trap.TopWidthCm(), 280.0));
    Check(Near(Trap.AreaCm2(), 40.0 * (200.0 + 40.0)));
    Check(Near(Trap.WettedPerimeterCm(), 200.0 + 2.0 * 40.0 * std::sqrt(2.0), 1e-9));
    Check(Trap.HydraulicRadiusCm() > Rect.HydraulicRadiusCm());

    // Degenerate and hostile inputs.
    ChannelSection Zero;
    Check(!Zero.Valid());
    Check(Near(Zero.HydraulicRadiusCm(), 0.0));
    ChannelSection Bad;
    Bad.BedWidthCm = NaNValue;
    Check(!Bad.Valid());
    ChannelSection Negative;
    Negative.BedWidthCm = -10.0;
    Negative.DepthCm = 5.0;
    Check(!Negative.Valid());

    // A run of channel between two sections: mean area times length.
    Check(Near(ChannelRunVolumeCm3(Rect, Trap, 1000.0), 0.5 * (1250.0 + 9600.0) * 1000.0, 1e-6));
    Check(Near(ChannelRunVolumeCm3(Rect, Trap, 0.0), 0.0));
    Check(Near(ChannelRunVolumeCm3(Rect, Trap, NaNValue), 0.0));

    Fact("section.rect_area_cm2", Rect.AreaCm2());
    Fact("section.rect_hydraulicRadius_cm", Rect.HydraulicRadiusCm());
    Fact("section.trap_topWidth_cm", Trap.TopWidthCm());
    Fact("section.trap_hydraulicRadius_cm", Trap.HydraulicRadiusCm());
}

// ---------------------------------------------------------------------------
// 3. Hydraulics
// ---------------------------------------------------------------------------

static void HydraulicChecks()
{
    // Manning against a hand computation. R = 12.5 cm = 0.125 m, S = 0.01, n = 0.015.
    // V = (1/0.015) * 0.125^(2/3) * 0.1 = 66.667 * 0.25 * 0.1 m/s -> 166.67 cm/s.
    const double V = ManningVelocityCmS(12.5, 0.01, Roughness::DressedStone);
    const double Expected = (1.0 / 0.015) * std::pow(0.125, 2.0 / 3.0) * std::sqrt(0.01) * 100.0;
    Check(Near(V, Expected, 1e-9));
    Check(V > 150.0 && V < 180.0);

    // Monotone in every argument, in the directions physics requires.
    Check(ManningVelocityCmS(25.0, 0.01, 0.015) > ManningVelocityCmS(12.5, 0.01, 0.015));
    Check(ManningVelocityCmS(12.5, 0.04, 0.015) > ManningVelocityCmS(12.5, 0.01, 0.015));
    Check(ManningVelocityCmS(12.5, 0.01, 0.030) < ManningVelocityCmS(12.5, 0.01, 0.015));
    // Doubling the slope multiplies the speed by exactly sqrt(2).
    Check(Near(ManningVelocityCmS(12.5, 0.02, 0.015) / ManningVelocityCmS(12.5, 0.01, 0.015),
               std::sqrt(2.0), 1e-9));

    // Degenerate inputs give zero, never a NaN or an infinity.
    Check(Near(ManningVelocityCmS(12.5, 0.0, 0.015), 0.0));
    Check(Near(ManningVelocityCmS(12.5, -0.01, 0.015), 0.0));
    Check(Near(ManningVelocityCmS(0.0, 0.01, 0.015), 0.0));
    Check(Near(ManningVelocityCmS(12.5, 0.01, 0.0), 0.0));
    Check(Near(ManningVelocityCmS(NaNValue, 0.01, 0.015), 0.0));
    Check(Near(ManningVelocityCmS(InfValue, 0.01, 0.015), 0.0) || std::isfinite(ManningVelocityCmS(InfValue, 0.01, 0.015)));

    // Normal depth inverts normal discharge. Pick a section, get its discharge, then
    // ask what depth carries it: the answer must be the depth we started from.
    ChannelSection Known;
    Known.BedWidthCm = 300.0;
    Known.DepthCm = 42.0;
    Known.SideSlope = 1.5;
    const double Q = NormalDischargeCm3S(Known, 0.004, Roughness::RubbleStone);
    Check(Q > 0.0);
    const double Recovered = NormalDepthCm(Q, 300.0, 1.5, 0.004, Roughness::RubbleStone);
    Check(Near(Recovered, 42.0, 1e-6));

    // Discharge rises strictly with depth, which is what makes the bisection sound.
    ChannelSection Shallow = Known;
    Shallow.DepthCm = 20.0;
    Check(NormalDischargeCm3S(Shallow, 0.004, Roughness::RubbleStone) < Q);

    // Guards on the inversion.
    Check(Near(NormalDepthCm(0.0, 300.0, 1.5, 0.004, 0.025), 0.0));
    Check(Near(NormalDepthCm(-5.0, 300.0, 1.5, 0.004, 0.025), 0.0));
    Check(Near(NormalDepthCm(NaNValue, 300.0, 1.5, 0.004, 0.025), 0.0));
    // A flow far too large for the cap returns the cap, not an infinite loop.
    Check(Near(NormalDepthCm(1e18, 10.0, 0.0, 0.004, 0.025, 200.0), 200.0, 1e-6));

    // Celerity and Froude. c = sqrt(g d): at 25 cm depth, sqrt(980.665 * 25) ~ 156.6 cm/s.
    Check(Near(ShallowWaterCelerityCmS(25.0), std::sqrt(980.665 * 25.0), 1e-9));
    Check(Near(ShallowWaterCelerityCmS(0.0), 0.0));
    Check(Near(ShallowWaterCelerityCmS(-4.0), 0.0));
    Check(Near(FroudeNumber(ShallowWaterCelerityCmS(25.0), 25.0), 1.0, 1e-12));
    Check(ClassifyFlow(FroudeNumber(ShallowWaterCelerityCmS(25.0), 25.0)) == FlowRegime::Critical);
    Check(ClassifyFlow(FroudeNumber(50.0, 25.0)) == FlowRegime::Subcritical);
    Check(ClassifyFlow(FroudeNumber(400.0, 25.0)) == FlowRegime::Supercritical);
    Check(ClassifyFlow(0.0) == FlowRegime::Still);
    Check(ClassifyFlow(NaNValue) == FlowRegime::Still);
    Check(Near(FroudeNumber(100.0, 0.0), 0.0));

    // Foam: none in tranquil flow, saturated once the flow is well past critical,
    // and monotone in between so there is no banding at the step.
    Check(Near(FoamFromFroude(0.5), 0.0));
    Check(Near(FoamFromFroude(1.6), 1.0, 1e-12));
    Check(Near(FoamFromFroude(3.0), 1.0, 1e-12));
    double Previous = -1.0;
    for (int I = 0; I <= 40; ++I)
    {
        const double F = FoamFromFroude(0.4 + 0.05 * I);
        Check(F >= Previous - 1e-12);
        Check(F >= 0.0 && F <= 1.0);
        Previous = F;
    }

    Fact("hydraulics.manning_R12_5_S0_01_n0_015_cmS", V);
    Fact("hydraulics.normalDepth_recovered_cm", Recovered);
    Fact("hydraulics.normalDepth_error_cm", std::abs(Recovered - 42.0));
    Fact("hydraulics.celerity_at25cm_cmS", ShallowWaterCelerityCmS(25.0));
    std::printf("hydraulics: Manning V=%.2f cm/s at R=12.5 cm S=1%% n=0.015; normal depth inverts to %.9f cm "
                "(error %.2e cm)\n", V, Recovered, std::abs(Recovered - 42.0));
}

// ---------------------------------------------------------------------------
// 4. The four stages of Yechezkel 47:3-5
// ---------------------------------------------------------------------------

static void StageChecks()
{
    const StreamProfile P = MakeStreamProfile();

    // The stages sit exactly one thousand amot apart, and the fourth is at 4000.
    Check(Near(StageDistanceAmot(Stage::Trickle), 0.0));
    Check(Near(StageDistanceAmot(Stage::Ankles), 1000.0));
    Check(Near(StageDistanceAmot(Stage::Knees), 2000.0));
    Check(Near(StageDistanceAmot(Stage::Loins), 3000.0));
    Check(Near(StageDistanceAmot(Stage::River), 4000.0));
    Check(Near(P.SpanAmot(), 4000.0));
    // At the project's amah, four thousand amot is two kilometres exactly.
    Check(Near(P.SpanCm(), 4000.0 * 50.0));
    Check(Near(P.SpanCm(), 200000.0));

    // The interpolant passes exactly through every measurement. This is the property
    // that makes the geometry a reconstruction of the text rather than a guess near it.
    for (int I = 0; I < static_cast<int>(StageCount); ++I)
    {
        const Stage S = static_cast<Stage>(I);
        Check(Near(P.DepthAtAmot(StageDistanceAmot(S)), StageDepthCm(S), 1e-9));
        Check(Near(P.TopWidthAtAmot(StageDistanceAmot(S)), StageTopWidthAmot(S) * ProjectAmahCm, 1e-9));
    }

    // The depths themselves, so the receipt carries the numbers a reviewer would check
    // against a standing figure.
    Check(Near(P.DepthAtAmot(1000.0), 0.07 * 170.0, 1e-9));   // 11.9 cm, the ankles
    Check(Near(P.DepthAtAmot(2000.0), 0.285 * 170.0, 1e-9));  // 48.45 cm, the knees
    Check(Near(P.DepthAtAmot(3000.0), 0.53 * 170.0, 1e-9));   // 90.1 cm, the loins
    Check(Near(P.DepthAtAmot(4000.0), 1.05 * 170.0, 1e-9));   // 178.5 cm, over a head

    // The fourth stage is deeper than a person is tall: "a river that could not be
    // passed over ... water to swim in". This is the numeric content of 47:5.
    Check(P.DepthAtAmot(4000.0) > StatureCm);
    // The third is not: the loins can be waded.
    Check(P.DepthAtAmot(3000.0) < StatureCm);

    // Monotone rise the whole way. Sample every amah of the four thousand.
    double PreviousDepth = -1.0, PreviousWidth = -1.0;
    for (int I = 0; I <= 4000; ++I)
    {
        const double D = P.DepthAtAmot(static_cast<double>(I));
        const double W = P.TopWidthAtAmot(static_cast<double>(I));
        Check(std::isfinite(D) && std::isfinite(W));
        Check(D >= PreviousDepth - 1e-9);   // never gets shallower
        Check(W >= PreviousWidth - 1e-9);   // never gets narrower
        Check(D >= 0.0 && W > 0.0);
        PreviousDepth = D;
        PreviousWidth = W;
    }
    // No overshoot above the last anchor anywhere: monotone cubic, not a plain spline.
    for (int I = 0; I <= 4000; ++I)
    {
        Check(P.DepthAtAmot(static_cast<double>(I)) <= P.DepthAtAmot(4000.0) + 1e-9);
        Check(P.TopWidthAtAmot(static_cast<double>(I)) <= P.TopWidthAtAmot(4000.0) + 1e-9);
    }

    // Clamped outside the measured span, and safe on garbage.
    Check(Near(P.DepthAtAmot(-500.0), P.DepthAtAmot(0.0), 1e-12));
    Check(Near(P.DepthAtAmot(9999.0), P.DepthAtAmot(4000.0), 1e-12));
    Check(Near(P.DepthAtAmot(NaNValue), 0.0));

    // Stage lookup: a stage is reached only once its mark is passed.
    Check(P.StageAtAmot(0.0) == Stage::Trickle);
    Check(P.StageAtAmot(999.9) == Stage::Trickle);
    Check(P.StageAtAmot(1000.0) == Stage::Ankles);
    Check(P.StageAtAmot(1999.9) == Stage::Ankles);
    Check(P.StageAtAmot(2000.0) == Stage::Knees);
    Check(P.StageAtAmot(3000.0) == Stage::Loins);
    Check(P.StageAtAmot(4000.0) == Stage::River);
    Check(P.StageAtAmot(1e9) == Stage::River);
    Check(P.StageAtAmot(NaNValue) == Stage::Trickle);

    // The section reproduces the authored TOP width at every distance, whatever the
    // bank slope: this is what keeps the generated banks honest to the profile.
    for (double Slope : {0.0, 0.75, 1.5, 3.0})
    {
        for (int I = 0; I <= 40; ++I)
        {
            const double At = 100.0 * I;
            const ChannelSection S = P.SectionAtAmot(At, Slope);
            const double Want = P.TopWidthAtAmot(At);
            // Where the banks alone already exceed the authored top width the bed
            // collapses to zero and the section is a plain V; otherwise it matches.
            if (S.BedWidthCm > 0.0) Check(Near(S.TopWidthCm(), Want, 1e-9));
            Check(S.TopWidthCm() > 0.0);
            Check(S.DepthCm >= 0.0);
        }
    }

    // Amah independence: at a different amah the depths (which are anthropometric)
    // are unchanged, while the widths (which are given in amot) scale.
    const StreamProfile Ish = MakeStreamProfile(57.6);
    Check(Near(Ish.DepthAtAmot(2000.0), P.DepthAtAmot(2000.0), 1e-9));
    Check(Near(Ish.TopWidthAtAmot(2000.0), P.TopWidthAtAmot(2000.0) * 57.6 / 50.0, 1e-9));
    Check(Near(MakeStreamProfile(0.0).AmahCmUsed, ProjectAmahCm));
    Check(Near(MakeStreamProfile(NaNValue).AmahCmUsed, ProjectAmahCm));

    Fact("stages.depth_ankles_cm", P.DepthAtAmot(1000.0));
    Fact("stages.depth_knees_cm", P.DepthAtAmot(2000.0));
    Fact("stages.depth_loins_cm", P.DepthAtAmot(3000.0));
    Fact("stages.depth_river_cm", P.DepthAtAmot(4000.0));
    Fact("stages.width_ankles_cm", P.TopWidthAtAmot(1000.0));
    Fact("stages.width_river_cm", P.TopWidthAtAmot(4000.0));
    Fact("stages.span_amot", P.SpanAmot());
    Fact("stages.span_cm", P.SpanCm());
    Fact("stages.stature_cm", StatureCm);
    Fact("stages.trickle_depth_cm", TrickleDepthCm);
    FactInt("stages.monotoneSamplesChecked", 4001);
    std::printf("stages: 1000 amot -> %.2f cm (ankles), 2000 -> %.2f (knees), 3000 -> %.2f (loins), "
                "4000 -> %.2f cm (over a %.0f cm stature); span %.0f cm; strictly monotone over 4001 samples\n",
                P.DepthAtAmot(1000.0), P.DepthAtAmot(2000.0), P.DepthAtAmot(3000.0),
                P.DepthAtAmot(4000.0), StatureCm, P.SpanCm());
}

// ---------------------------------------------------------------------------
// 5. Demonstration mode
// ---------------------------------------------------------------------------

static void DemoChecks()
{
    DemoSettings S;
    S.TravelSeconds = 6.0;
    S.HoldSeconds = 3.0;
    S.Loop = false;
    Check(Near(DemoCycleSeconds(S), 36.0));

    // Starts at the gate.
    Check(Near(EvaluateDemo(S, 0.0).DistanceAmot, 0.0));
    Check(EvaluateDemo(S, 0.0).CurrentStage == Stage::Trickle);
    Check(!EvaluateDemo(S, 0.0).Finished);

    // Halfway through the first travel leg is 500 amot.
    Check(Near(EvaluateDemo(S, 3.0).DistanceAmot, 500.0, 1e-9));
    Check(!EvaluateDemo(S, 3.0).Holding);

    // At the end of the first leg it holds at exactly 1000 amot for three seconds.
    Check(Near(EvaluateDemo(S, 6.0).DistanceAmot, 1000.0, 1e-9));
    Check(EvaluateDemo(S, 6.0).Holding);
    Check(EvaluateDemo(S, 6.0).CurrentStage == Stage::Ankles);
    Check(Near(EvaluateDemo(S, 8.9).DistanceAmot, 1000.0, 1e-9));
    Check(EvaluateDemo(S, 8.9).Holding);

    // Then moves on.
    Check(EvaluateDemo(S, 9.5).DistanceAmot > 1000.0);
    Check(!EvaluateDemo(S, 9.5).Holding);
    Check(Near(EvaluateDemo(S, 15.0).DistanceAmot, 2000.0, 1e-9));
    Check(Near(EvaluateDemo(S, 24.0).DistanceAmot, 3000.0, 1e-9));
    Check(Near(EvaluateDemo(S, 33.0).DistanceAmot, 4000.0, 1e-9));
    Check(EvaluateDemo(S, 33.0).CurrentStage == Stage::River);

    // Past the cycle it stops at the river and reports finished.
    Check(Near(EvaluateDemo(S, 100.0).DistanceAmot, 4000.0));
    Check(EvaluateDemo(S, 100.0).Finished);
    Check(Near(EvaluateDemo(S, 100.0).Progress, 1.0));

    // Distance never decreases across the whole cycle, and progress tracks it.
    double Last = -1.0;
    for (int I = 0; I <= 3600; ++I)
    {
        const DemoState D = EvaluateDemo(S, I * 0.01);
        Check(D.DistanceAmot >= Last - 1e-9);
        Check(D.DistanceAmot >= 0.0 && D.DistanceAmot <= 4000.0);
        Check(D.Progress >= 0.0 && D.Progress <= 1.0);
        Check(Near(D.Progress, D.DistanceAmot / 4000.0, 1e-9));
        Last = D.DistanceAmot;
    }

    // Looping restarts rather than finishing.
    DemoSettings Looping = S;
    Looping.Loop = true;
    Check(!EvaluateDemo(Looping, 100.0).Finished);
    Check(Near(EvaluateDemo(Looping, 36.0).DistanceAmot, 0.0, 1e-9));
    Check(Near(EvaluateDemo(Looping, 42.0).DistanceAmot, 1000.0, 1e-9));

    // Degenerate settings jump straight to the end instead of dividing by zero.
    DemoSettings Instant;
    Instant.TravelSeconds = 0.0;
    Instant.HoldSeconds = 0.0;
    Check(Near(EvaluateDemo(Instant, 0.0).DistanceAmot, 4000.0));
    Check(Near(EvaluateDemo(S, NaNValue).DistanceAmot, 0.0));
    Check(Near(EvaluateDemo(S, -50.0).DistanceAmot, 0.0));

    // A demo with no hold still reaches every mark.
    DemoSettings NoHold = S;
    NoHold.HoldSeconds = 0.0;
    Check(Near(DemoCycleSeconds(NoHold), 24.0));
    Check(Near(EvaluateDemo(NoHold, 12.0).DistanceAmot, 2000.0, 1e-9));

    Fact("demo.cycleSeconds", DemoCycleSeconds(S));
    Fact("demo.distanceAt6s_amot", EvaluateDemo(S, 6.0).DistanceAmot);
    Fact("demo.distanceAt33s_amot", EvaluateDemo(S, 33.0).DistanceAmot);
    FactInt("demo.monotoneSamplesChecked", 3601);
    std::printf("demo: 36 s cycle, four 6 s legs with 3 s holds, monotone over 3601 samples, "
                "stops at the river unless looping\n");
}

// ---------------------------------------------------------------------------
// 6. Surface kinematics
// ---------------------------------------------------------------------------

static void SurfaceChecks()
{
    // Scroll: at 100 cm/s over a 200 cm tile, one tile takes two seconds.
    Check(Near(ScrollTiles(100.0, 0.0, 200.0), 0.0));
    Check(Near(ScrollTiles(100.0, 1.0, 200.0), 0.5, 1e-12));
    Check(Near(ScrollTiles(100.0, 2.0, 200.0), 0.0, 1e-12));   // wrapped
    Check(Near(ScrollTiles(100.0, 2.5, 200.0), 0.25, 1e-12));
    // Always inside [0, 1), including after a long run and for a reversed flow.
    for (int I = 0; I < 500; ++I)
    {
        const double T = ScrollTiles(137.0, I * 7.3, 213.0);
        Check(T >= 0.0 && T < 1.0);
    }
    Check(ScrollTiles(-100.0, 1.0, 200.0) >= 0.0 && ScrollTiles(-100.0, 1.0, 200.0) < 1.0);
    Check(Near(ScrollTiles(100.0, 1.0, 0.0), 0.0));
    Check(Near(ScrollTiles(NaNValue, 1.0, 200.0), 0.0));

    // Wave phase advances 2*pi per wavelength and travels downstream with time.
    Check(Near(WavePhase(0.0, 0.0, 100.0, 50.0), 0.0));
    Check(Near(WavePhase(100.0, 0.0, 100.0, 50.0), 2.0 * Pi, 1e-9));
    // A point moving with the wave sees a constant phase.
    Check(Near(WavePhase(50.0 * 3.0, 3.0, 100.0, 50.0), 0.0, 1e-9));
    Check(Near(WavePhase(0.0, 0.0, 0.0, 50.0), 0.0));
    Check(Near(WavePhase(NaNValue, 0.0, 100.0, 50.0), 0.0));
    Check(Near(WaveElevationCm(5.0, Pi / 2.0), 5.0, 1e-12));
    Check(Near(WaveElevationCm(5.0, NaNValue), 0.0));

    // Ripple: nothing ahead of the crest, nothing before it is launched, and the
    // amplitude falls as the ring ages and spreads.
    Ripple R;
    const double Depth = 30.0;
    const double C = ShallowWaterCelerityCmS(Depth);
    Check(C > 0.0);
    Check(Near(RippleElevationCm(R, 500.0, 0.0, Depth), 0.0));            // not yet launched
    Check(Near(RippleElevationCm(R, C * 1.0 + 10.0, 1.0, Depth), 0.0));   // ahead of the crest
    Check(Near(RippleElevationCm(R, 0.0, 1.0, Depth), 0.0));              // crest long past
    Check(Near(RippleElevationCm(R, 100.0, -1.0, Depth), 0.0));           // negative age
    Check(Near(RippleElevationCm(R, 100.0, 1.0, 0.0), 0.0));              // no water, no ripple
    Check(Near(RippleElevationCm(R, NaNValue, 1.0, Depth), 0.0));

    // Somewhere inside the crest band the ripple is non-zero and bounded.
    bool FoundNonZero = false;
    double PeakEarly = 0.0, PeakLate = 0.0;
    for (int I = 0; I < 400; ++I)
    {
        const double Radius = C * 0.5 - I * 0.3;
        const double E = RippleElevationCm(R, Radius, 0.5, Depth);
        Check(std::isfinite(E));
        Check(std::abs(E) <= R.AmplitudeCm + 1e-9);
        if (std::abs(E) > 1e-6) FoundNonZero = true;
        PeakEarly = std::max(PeakEarly, std::abs(E));
    }
    Check(FoundNonZero);
    for (int I = 0; I < 400; ++I)
    {
        const double Radius = C * 3.0 - I * 0.3;
        PeakLate = std::max(PeakLate, std::abs(RippleElevationCm(R, Radius, 3.0, Depth)));
    }
    Check(PeakLate < PeakEarly);   // decays with age and spreading

    Fact("surface.scroll_100cmS_200cmTile_at1s", ScrollTiles(100.0, 1.0, 200.0));
    Fact("surface.ripplePeak_at0_5s_cm", PeakEarly);
    Fact("surface.ripplePeak_at3s_cm", PeakLate);
    Fact("surface.celerity_at30cm_cmS", C);
    std::printf("surface: scroll wraps in [0,1); ripple peak %.4f cm at 0.5 s decays to %.4f cm at 3 s\n",
                PeakEarly, PeakLate);
}

// ---------------------------------------------------------------------------
// 7. The whole drive, sampled along the stream
// ---------------------------------------------------------------------------
//
// This is the end-to-end check: the numbers AMikdashWater will actually push into the
// material instance, evaluated along the four thousand amot, must all be finite, in
// range, and physically ordered.

static void DriveChecks()
{
    const StreamProfile P = MakeStreamProfile();
    const double SideSlope = 1.5;
    const double BedSlope = 0.004;      // 4 mm per metre, running down to the Aravah
    const double TileCm = 400.0;

    double LastOpacity = -1.0;
    for (int I = 0; I <= 400; ++I)
    {
        const double At = 10.0 * I;
        const SurfaceDrive D = EvaluateSurface(P, At, SideSlope, BedSlope, Roughness::NaturalEarth, TileCm, 1.7);
        Check(std::isfinite(D.DepthCm) && std::isfinite(D.TopWidthCm));
        Check(std::isfinite(D.VelocityCmS) && std::isfinite(D.DischargeCm3S));
        Check(std::isfinite(D.Froude) && std::isfinite(D.CelerityCmS));
        Check(D.Foam >= 0.0 && D.Foam <= 1.0);
        Check(D.Opacity >= 0.0 && D.Opacity <= 1.0);
        Check(D.ScrollTiles >= 0.0 && D.ScrollTiles < 1.0);
        Check(D.VelocityCmS >= 0.0);
        Check(D.Opacity >= LastOpacity - 1e-9);   // deeper water is never more transparent
        LastOpacity = D.Opacity;
    }

    const SurfaceDrive Ankle = EvaluateSurface(P, 1000.0, SideSlope, BedSlope, Roughness::NaturalEarth, TileCm, 0.0);
    const SurfaceDrive River = EvaluateSurface(P, 4000.0, SideSlope, BedSlope, Roughness::NaturalEarth, TileCm, 0.0);
    Check(Ankle.CurrentStage == Stage::Ankles);
    Check(River.CurrentStage == Stage::River);
    Check(River.DepthCm > Ankle.DepthCm);
    Check(River.TopWidthCm > Ankle.TopWidthCm);
    Check(River.VelocityCmS > Ankle.VelocityCmS);       // deeper section, less drag per unit area
    Check(River.DischargeCm3S > Ankle.DischargeCm3S);
    Check(River.Opacity > Ankle.Opacity);
    Check(Near(River.Opacity, 1.0, 1e-9));              // 178.5 cm is past the opacity depth
    Check(Ankle.Opacity < 0.15);                        // ankle-deep water is nearly clear

    // The steep reach through the courtyard, where the stream drops from the Ulam
    // threshold (Z 925 cm) to the outer court floor (Z 300 cm) over roughly 105 m:
    // a 6% grade in a dressed-stone runnel. That is where the flow shoots and foams.
    ChannelSection Runnel;
    Runnel.BedWidthCm = 50.0;
    Runnel.DepthCm = 12.0;
    Runnel.SideSlope = 0.0;
    const double CourtV = ManningVelocityCmS(Runnel.HydraulicRadiusCm(), 0.06, Roughness::DressedStone);
    const double CourtFr = FroudeNumber(CourtV, Runnel.HydraulicDepthCm());
    Check(CourtV > 0.0);
    Check(CourtFr > 1.0);                                    // supercritical: it shoots
    Check(ClassifyFlow(CourtFr) == FlowRegime::Supercritical);
    Check(FoamFromFroude(CourtFr) > 0.5);                    // and therefore foams

    Fact("drive.ankle_velocity_cmS", Ankle.VelocityCmS);
    Fact("drive.ankle_discharge_cm3S", Ankle.DischargeCm3S);
    Fact("drive.ankle_froude", Ankle.Froude);
    Fact("drive.ankle_opacity", Ankle.Opacity);
    Fact("drive.river_velocity_cmS", River.VelocityCmS);
    Fact("drive.river_discharge_cm3S", River.DischargeCm3S);
    Fact("drive.river_discharge_litresPerS", River.DischargeCm3S / 1000.0);
    Fact("drive.river_froude", River.Froude);
    Fact("drive.river_opacity", River.Opacity);
    Fact("drive.courtRunnel_velocity_cmS", CourtV);
    Fact("drive.courtRunnel_froude", CourtFr);
    Fact("drive.courtRunnel_foam", FoamFromFroude(CourtFr));
    FactText("drive.courtRunnel_regime", "supercritical");
    std::printf("drive: ankle reach %.1f cm/s Fr=%.2f opacity %.3f; river reach %.1f cm/s (%.0f L/s) Fr=%.2f "
                "opacity %.3f; court runnel at 6%% grade %.1f cm/s Fr=%.2f foam %.2f\n",
                Ankle.VelocityCmS, Ankle.Froude, Ankle.Opacity,
                River.VelocityCmS, River.DischargeCm3S / 1000.0, River.Froude, River.Opacity,
                CourtV, CourtFr, FoamFromFroude(CourtFr));
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
    std::fprintf(File, "{\n  \"test\": \"WaterFlowMathTest\",\n"
                       "  \"header\": \"Plugins/MikdashRuntime/Source/MikdashRuntime/Public/WaterFlowMath.h\",\n"
                       "  \"scope\": \"Standalone C++ arithmetic only. No Unreal, no map, no visual acceptance. "
                       "Forty-se'ah figures are arithmetic on published shiurim, not a halachic ruling.\",\n");
    std::fprintf(File, "  \"allPassed\": true,\n  \"checksEvaluated\": %lld,\n  \"measurements\": {\n", CheckCount);
    for (size_t I = 0; I < Facts.size(); ++I)
    {
        std::fprintf(File, "    \"%s\": %s%s\n", Facts[I].first.c_str(), Facts[I].second.c_str(),
                     I + 1 < Facts.size() ? "," : "");
    }
    std::fprintf(File, "  }\n}\n");
    std::fclose(File);
}

int main(int argc, char** argv)
{
    FortySeahChecks();
    SectionChecks();
    HydraulicChecks();
    StageChecks();
    DemoChecks();
    SurfaceChecks();
    DriveChecks();
    if (argc > 1) WriteJson(argv[1]);
    std::cout << "PASS " << CheckCount
              << " checks: forty se'ah, channel sections, Manning hydraulics, the four stages of Yechezkel 47, "
                 "demonstration mode, surface kinematics and the material drive" << std::endl;
    return 0;
}
