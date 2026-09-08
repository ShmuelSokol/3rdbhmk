// Standalone test for Public/PlumeMath.h. No Unreal, no test framework, no network.
//
// Build (VS2022 BuildTools, x64 Native Tools / vcvars64):
//   cl /std:c++17 /EHsc /W4 /O2 /I"..\Source\MikdashRuntime\Public" PlumeMathTest.cpp /Fe:PlumeMathTest.exe
//
// Run:
//   PlumeMathTest.exe "C:\Mikdash\Working-5.8\MikdashCourtyardV3\SourceAssets\fx-review\tests.json"
//
// Exit code 0 = every check passed. Non-zero = at least one check failed; the JSON
// receipt still gets written, with the failures listed, so a reviewer sees numbers
// rather than a bare exit code.
//
// The three things this file exists to prove:
//   1. The plume stays inside the envelope the material is authored to cover, at
//      every wind speed, including the Avos 5:5 straight-column depiction.
//   2. The flame flicker is band-limited noise with a plausible peak near the
//      puffing frequency, not white noise.
//   3. No public entry point returns a NaN or an infinity, for any input, including
//      NaN and infinity themselves.

#include "PlumeMath.h"

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <string>
#include <vector>

using namespace MikdashPlume;

namespace
{
struct FCheck
{
    std::string Name;
    bool bPassed = false;
    std::string Detail;
};

std::vector<FCheck> Checks;

void Record(const char* Name, bool bPassed, const std::string& Detail)
{
    FCheck Check;
    Check.Name = Name;
    Check.bPassed = bPassed;
    Check.Detail = Detail;
    Checks.push_back(Check);
}

std::string Num(double Value, int Digits = 6)
{
    char Buffer[64];
    std::snprintf(Buffer, sizeof(Buffer), "%.*g", Digits, Value);
    return std::string(Buffer);
}

std::string JsonEscape(const std::string& In)
{
    std::string Out;
    for (char C : In)
    {
        if (C == '"' || C == '\\')
        {
            Out.push_back('\\');
            Out.push_back(C);
        }
        else if (C == '\n')
        {
            Out += "\\n";
        }
        else
        {
            Out.push_back(C);
        }
    }
    return Out;
}

// ---------------------------------------------------------------------------
// Scene profiles. These match Scripts/release_fx.spec.json; if the spec changes,
// change both. Positions come from receipts, not from invention:
//   outer altar   SourceAssets/architecture-manifest.json, altar meshes SM_0154..SM_0165
//   golden altar  SourceAssets/vessels-review/keilim-move-20260907T171347Z.json
//   Heikhal room  SM_0146_floor_Heichal_clear_floor, SM_0148_roof_Sanctuary_ceiling
// ---------------------------------------------------------------------------
FPlumeProfile OuterAltarProfile()
{
    FPlumeProfile P;
    P.SourceRadiusCm = 250.0;          // modelled wood arrangement, SM_2061..SM_2067 span
    P.RiseSpeedCmS = 340.0;
    P.EntrainmentAlpha = 0.10;
    P.MaxRadiusCm = 900.0;
    P.MaxHeightCm = 4200.0;            // ends above the 3425 cm door head, below the skyline
    P.bStraightColumnInWind = true;    // SOURCE CLAIM, Avos 5:5
    P.MinOpacity = 0.05;
    return P;
}

FPlumeProfile OuterAltarPhysicalProfile()
{
    FPlumeProfile P = OuterAltarProfile();
    P.bStraightColumnInWind = false;   // the physical path, kept live and tested
    return P;
}

FPlumeProfile KetoresProfile()
{
    FPlumeProfile P;
    P.SourceRadiusCm = 21.0;           // golden altar face 41.67 cm, half width
    P.RiseSpeedCmS = 150.0;
    P.EntrainmentAlpha = 0.06;         // "stafflike", Yoma 53a; a narrow column
    P.MaxRadiusCm = 180.0;
    P.MaxHeightCm = 1920.0;            // ceiling 2925 minus altar top 1004.1667 = 1920.83, rounded down
    P.bStraightColumnInWind = false;   // indoors; there is no wind term to apply
    P.MinOpacity = 0.08;
    return P;
}

FCeilingSpread HeikhalRoom()
{
    FCeilingSpread Room;
    Room.SourceZCm = 1004.1666666666667;   // 925 floor + 79.1667 golden altar roof plane
    Room.CeilingZCm = 2925.0;              // SM_0148_roof_Sanctuary_ceiling underside
    Room.RoomRadiusCm = 1050.0;            // Heikhal is 2000 x 1000 cm; half diagonal ~1118
    Room.SpreadTimeConstantS = 7.0;
    Room.FillTimeConstantS = 28.0;
    Room.MaxLayerDepthCm = 950.0;
    return Room;
}

// ---------------------------------------------------------------------------
// 1. Envelope
// ---------------------------------------------------------------------------
void TestPlumeEnvelope()
{
    const FPlumeProfile Straight = OuterAltarProfile();
    const FPlumeProfile Bent = OuterAltarPhysicalProfile();

    // 1a. Straight column: zero axis offset at every wind speed, and every sampled
    // parcel sits inside a vertical cylinder of MaxRadiusCm.
    double WorstStraightOffset = 0.0;
    double WorstStraightRadius = 0.0;
    bool bStraightInside = true;
    for (int W = 0; W <= 40; ++W)
    {
        FWind Wind;
        Wind.SpeedCmS = W * 50.0;                       // 0 .. 2000 cm/s (0 .. 72 km/h)
        Wind.DirX = std::cos(W * 0.37);
        Wind.DirY = std::sin(W * 0.37);
        for (int I = 0; I <= 400; ++I)
        {
            const double Age = I * 0.05;                // 0 .. 20 s
            const FPlumeSample S = SamplePlumeAtAge(Straight, Age, Wind);
            WorstStraightOffset = std::max(WorstStraightOffset, std::fabs(S.AxisOffsetCm));
            WorstStraightRadius = std::max(WorstStraightRadius, S.RadiusCm);
            FVec3 Point;
            Point.X = S.AxisOffsetWorldCm.X;
            Point.Y = S.AxisOffsetWorldCm.Y;
            Point.Z = S.HeightCm;
            if (!IsInsidePlumeEnvelope(Straight, Point, Wind, 0.0))
            {
                bStraightInside = false;
            }
        }
    }
    Record("straight_column_zero_offset_in_any_wind", WorstStraightOffset == 0.0,
           "max |axis offset| over wind 0..2000 cm/s = " + Num(WorstStraightOffset) + " cm (source claim Avos 5:5)");
    Record("straight_column_within_max_radius", bStraightInside && WorstStraightRadius <= Straight.MaxRadiusCm + 1e-9,
           "max sampled radius " + Num(WorstStraightRadius) + " cm <= MaxRadiusCm " + Num(Straight.MaxRadiusCm));

    // 1b. Ring test: a point at 99% of the radius is inside, at 101% is outside, for
    // both profiles and a wind that would bend the physical one hard.
    FWind Gale;
    Gale.SpeedCmS = 900.0;
    Gale.DirX = 1.0;
    Gale.DirY = 0.0;
    bool bRingOk = true;
    int RingSamples = 0;
    for (const FPlumeProfile* Profile : {&Straight, &Bent})
    {
        for (int I = 0; I <= 200; ++I)
        {
            const double H = (Profile->MaxHeightCm * I) / 200.0;
            const double R = PlumeRadiusCm(*Profile, H);
            const double Offset = PlumeAxisOffsetCm(*Profile, H, Gale);
            for (int A = 0; A < 8; ++A)
            {
                const double Theta = (A * 2.0 * Pi) / 8.0;
                FVec3 Inside, Outside;
                Inside.Z = Outside.Z = H;
                Inside.X = Offset + 0.99 * R * std::cos(Theta);
                Inside.Y = 0.99 * R * std::sin(Theta);
                Outside.X = Offset + 1.01 * R * std::cos(Theta);
                Outside.Y = 1.01 * R * std::sin(Theta);
                ++RingSamples;
                if (!IsInsidePlumeEnvelope(*Profile, Inside, Gale, 0.0)) { bRingOk = false; }
                if (IsInsidePlumeEnvelope(*Profile, Outside, Gale, 0.0)) { bRingOk = false; }
            }
        }
    }
    Record("envelope_ring_test", bRingOk,
           std::to_string(RingSamples) + " ring samples per side; 0.99R inside and 1.01R outside for both the straight and the physical profile at 900 cm/s wind");

    // 1c. The physical profile must actually bend, and bend monotonically, or the
    // straight-column claim above would be trivially true of both.
    bool bBendMonotoneInWind = true;
    bool bBendMonotoneInHeight = true;
    double LastOffset = -1.0;
    for (int W = 0; W <= 20; ++W)
    {
        FWind Wind;
        Wind.SpeedCmS = W * 100.0;
        const double Offset = PlumeAxisOffsetCm(Bent, 2000.0, Wind);
        if (Offset < LastOffset - 1e-9) { bBendMonotoneInWind = false; }
        LastOffset = Offset;
    }
    double LastHeightOffset = -1.0;
    for (int I = 0; I <= 200; ++I)
    {
        const double Offset = PlumeAxisOffsetCm(Bent, I * 20.0, Gale);
        if (Offset < LastHeightOffset - 1e-9) { bBendMonotoneInHeight = false; }
        LastHeightOffset = Offset;
    }
    const double BendAtTop = PlumeAxisOffsetCm(Bent, Bent.MaxHeightCm, Gale);
    Record("physical_plume_bends_monotonically", bBendMonotoneInWind && bBendMonotoneInHeight && BendAtTop > 100.0,
           "physical offset at " + Num(Bent.MaxHeightCm) + " cm in a 900 cm/s wind = " + Num(BendAtTop) + " cm; monotone in wind and in height");

    // 1d. Height/age round trip. h(t) must be non-decreasing and t(h(t)) == t below
    // the cap, or the material's height-to-age mapping would drift.
    bool bMonotone = true;
    double WorstRoundTrip = 0.0;
    double Previous = -1.0;
    for (int I = 0; I <= 2000; ++I)
    {
        const double Age = I * 0.01;
        const double H = PlumeHeightAtAgeCm(Bent, Age);
        if (H < Previous - 1e-9) { bMonotone = false; }
        Previous = H;
        if (H < Bent.MaxHeightCm - 1.0)
        {
            WorstRoundTrip = std::max(WorstRoundTrip, std::fabs(PlumeTimeToHeightS(Bent, H) - Age));
        }
    }
    Record("height_age_round_trip", bMonotone && WorstRoundTrip < 1e-6,
           "max |t(h(t)) - t| below the height cap = " + Num(WorstRoundTrip) + " s over 0..20 s");

    // 1e. Opacity must fall with height and never leave [MinOpacity, 1].
    bool bOpacityOk = true;
    double PreviousOpacity = 2.0;
    for (int I = 0; I <= 400; ++I)
    {
        const double O = PlumeOpacity(Bent, I * 10.0);
        if (O > PreviousOpacity + 1e-12) { bOpacityOk = false; }
        if (O < Bent.MinOpacity - 1e-12 || O > 1.0 + 1e-12) { bOpacityOk = false; }
        PreviousOpacity = O;
    }
    Record("opacity_monotone_and_bounded", bOpacityOk,
           "opacity falls monotonically from 1 to " + Num(PlumeOpacity(Bent, 4000.0)) + " and stays within [" + Num(Bent.MinOpacity) + ", 1]");
}

// ---------------------------------------------------------------------------
// 2. Indoor ketores shape
// ---------------------------------------------------------------------------
void TestKetoresShape()
{
    const FPlumeProfile Plume = KetoresProfile();
    const FCeilingSpread Room = HeikhalRoom();
    const FKetoresTiming Timing;

    const double Impinge = CeilingImpingementTimeS(Plume, Room);
    Record("ketores_reaches_ceiling_in_a_plausible_time", Impinge > 5.0 && Impinge < 90.0,
           "column reaches the 2925 cm ceiling from the 1004.17 cm altar top in " + Num(Impinge) + " s");

    // The column must not clip the roof: the plume's own cap sits at or below the
    // ceiling. This is the research document's "smoke stops at architectural
    // boundaries rather than clipping through the roof".
    const double ColumnTopZ = Room.SourceZCm + Plume.MaxHeightCm;
    Record("ketores_column_stops_at_ceiling", ColumnTopZ <= Room.CeilingZCm + 1e-9,
           "column top Z " + Num(ColumnTopZ) + " <= ceiling Z " + Num(Room.CeilingZCm));

    bool bSpreadMonotone = true;
    bool bDepthMonotone = true;
    bool bBottomInRoom = true;
    double LastSpread = -1.0;
    double LastDepth = -1.0;
    for (int I = 0; I <= 2000; ++I)
    {
        const double T = I * 0.1;
        const double R = CeilingSpreadRadiusCm(Room, T);
        const double D = CeilingLayerDepthCm(Room, T);
        const double Bottom = CeilingLayerBottomZCm(Room, T);
        if (R < LastSpread - 1e-9) { bSpreadMonotone = false; }
        if (D < LastDepth - 1e-9) { bDepthMonotone = false; }
        if (R > Room.RoomRadiusCm + 1e-9) { bSpreadMonotone = false; }
        if (D > Room.MaxLayerDepthCm + 1e-9) { bDepthMonotone = false; }
        if (Bottom < Room.SourceZCm - 1e-9 || Bottom > Room.CeilingZCm + 1e-9) { bBottomInRoom = false; }
        LastSpread = R;
        LastDepth = D;
    }
    Record("ceiling_spread_monotone_and_capped", bSpreadMonotone && bDepthMonotone,
           "spread saturates at " + Num(CeilingSpreadRadiusCm(Room, 200.0)) + " / " + Num(Room.RoomRadiusCm) +
           " cm and the layer at " + Num(CeilingLayerDepthCm(Room, 200.0)) + " / " + Num(Room.MaxLayerDepthCm) + " cm");
    Record("layer_bottom_stays_between_altar_and_ceiling", bBottomInRoom,
           "layer underside stays within [" + Num(Room.SourceZCm) + ", " + Num(Room.CeilingZCm) + "] cm for 200 s");

    // No particles before service begins, none after the authored end.
    const double DensityBefore = KetoresDensity(Timing, Plume, Room, -1.0);
    const double End = Impinge + Timing.AccumulateSeconds + Timing.DissipateSeconds;
    const double DensityAfter = KetoresDensity(Timing, Plume, Room, End + 0.01);
    bool bDensityBounded = true;
    for (int I = -50; I <= 4000; ++I)
    {
        const double D = KetoresDensity(Timing, Plume, Room, I * 0.1);
        if (D < 0.0 || D > 1.0 || !std::isfinite(D)) { bDensityBounded = false; }
    }
    Record("ketores_density_zero_outside_the_event", DensityBefore == 0.0 && DensityAfter == 0.0 && bDensityBounded,
           "density 0 before begin and 0 after the " + Num(End) + " s authored end; bounded in [0,1] throughout");

    // All four authored phases must actually occur, in order.
    int PhaseSeen[5] = {0, 0, 0, 0, 0};
    for (int I = 0; I <= 4000; ++I)
    {
        const int Phase = static_cast<int>(KetoresPhaseAt(Timing, Plume, Room, I * 0.05));
        if (Phase >= 0 && Phase <= 4) { ++PhaseSeen[Phase]; }
    }
    const bool bAllPhases = PhaseSeen[1] > 0 && PhaseSeen[2] > 0 && PhaseSeen[3] > 0 && PhaseSeen[4] > 0 && PhaseSeen[0] > 0;
    Record("ketores_four_phases_all_occur", bAllPhases,
           "samples per phase idle/emit/ascend/accumulate/dissipate = " +
           std::to_string(PhaseSeen[0]) + "/" + std::to_string(PhaseSeen[1]) + "/" + std::to_string(PhaseSeen[2]) + "/" +
           std::to_string(PhaseSeen[3]) + "/" + std::to_string(PhaseSeen[4]));
}

// ---------------------------------------------------------------------------
// 3. Flicker spectrum
// ---------------------------------------------------------------------------
struct FSpectrum
{
    double PeakHz = 0.0;
    double Centroid = 0.0;
    double FractionAboveFourF0 = 0.0;
    double Mean = 0.0;
    double Rms = 0.0;
    double MaxAbs = 0.0;
    bool bFinite = true;
};

/** Naive DFT power spectrum of a real signal. N is small enough that O(N * bins) is
 *  a fraction of a second, and a hand-written DFT keeps this file dependency free. */
FSpectrum Analyse(const std::vector<double>& Samples, double SampleRateHz, double F0Hz)
{
    FSpectrum Out;
    const size_t N = Samples.size();
    double Sum = 0.0;
    double SumSquares = 0.0;
    for (double V : Samples)
    {
        if (!std::isfinite(V)) { Out.bFinite = false; }
        Sum += V;
        SumSquares += V * V;
        Out.MaxAbs = std::max(Out.MaxAbs, std::fabs(V));
    }
    Out.Mean = Sum / static_cast<double>(N);
    Out.Rms = std::sqrt(SumSquares / static_cast<double>(N));

    const size_t Bins = N / 2;
    std::vector<double> Power(Bins, 0.0);
    for (size_t K = 1; K < Bins; ++K)
    {
        double Re = 0.0;
        double Im = 0.0;
        const double W = -2.0 * Pi * static_cast<double>(K) / static_cast<double>(N);
        for (size_t Index = 0; Index < N; ++Index)
        {
            // Hann window: without it the resonator's leakage smears the peak.
            const double Window = 0.5 - 0.5 * std::cos(2.0 * Pi * static_cast<double>(Index) / static_cast<double>(N - 1));
            const double V = (Samples[Index] - Out.Mean) * Window;
            const double Angle = W * static_cast<double>(Index);
            Re += V * std::cos(Angle);
            Im += V * std::sin(Angle);
        }
        Power[K] = Re * Re + Im * Im;
    }

    double Total = 0.0;
    double Above = 0.0;
    double WeightedFreq = 0.0;
    double PeakPower = -1.0;
    const double BinHz = SampleRateHz / static_cast<double>(N);
    for (size_t K = 1; K < Bins; ++K)
    {
        const double Hz = static_cast<double>(K) * BinHz;
        Total += Power[K];
        WeightedFreq += Hz * Power[K];
        if (Hz > 4.0 * F0Hz) { Above += Power[K]; }
        if (Power[K] > PeakPower)
        {
            PeakPower = Power[K];
            Out.PeakHz = Hz;
        }
    }
    if (Total > 0.0)
    {
        Out.Centroid = WeightedFreq / Total;
        Out.FractionAboveFourF0 = Above / Total;
    }
    return Out;
}

void TestFlicker()
{
    // Diameters come from the modelled geometry, not from taste:
    //   outer altar wood arrangement SM_2061..SM_2067 spans 325 cm in X
    // The lamp figure is the burning wick, not the oil cup. Cetegen and Ahmed's
    // correlation is in the diameter of the burning region, and for an olive-oil lamp
    // that is the wick; the cup is 12.9 cm as placed but is not what is on fire.
    // 0.6 cm is a design value (D): no source gives a wick thickness. Using the cup
    // would put the lamp at 4.2 Hz, slower than a candle looks, and would collapse
    // the perceptual gap between a 12 m fire arrangement and a wick that this whole
    // section exists to preserve.
    const double AltarDiameterCm = 325.0;
    const double LampDiameterCm = 0.6;
    const double AltarF0 = PuffingFrequencyHz(AltarDiameterCm);
    const double LampF0 = PuffingFrequencyHz(LampDiameterCm);

    Record("puffing_frequency_separates_altar_from_wick", AltarF0 > 0.2 && AltarF0 < 1.5 && LampF0 > 8.0 && LampF0 < 25.0 && LampF0 > 8.0 * AltarF0,
           "f = 1.5/sqrt(D_m): altar " + Num(AltarDiameterCm) + " cm -> " + Num(AltarF0) + " Hz, lamp " +
           Num(LampDiameterCm) + " cm -> " + Num(LampF0) + " Hz");

    const double SampleRate = 240.0;
    const size_t N = 4096;
    struct FCase { const char* Label; double F0; uint32_t Seed; };
    const FCase Cases[2] = {{"altar", AltarF0, 0x4d495a42u}, {"lamp", LampF0, 0x4d454e52u}};

    for (const FCase& Case : Cases)
    {
        FFlicker Flicker;
        Flicker.Reset(Case.Seed, Case.F0, 4.0);
        std::vector<double> Samples;
        Samples.reserve(N);
        // Warm the resonator so the analysed window is not dominated by its start
        // transient; 20 time constants is far more than enough.
        for (int I = 0; I < 4000; ++I) { Flicker.Advance(1.0 / SampleRate); }
        for (size_t I = 0; I < N; ++I) { Samples.push_back(Flicker.Advance(1.0 / SampleRate)); }

        const FSpectrum S = Analyse(Samples, SampleRate, Case.F0);

        // White-noise control at the same length, so "band limited" is measured
        // against something rather than asserted.
        std::vector<double> White;
        White.reserve(N);
        for (size_t I = 0; I < N; ++I) { White.push_back(HashToSigned(0x57484954u, static_cast<uint32_t>(I), Case.Seed)); }
        const FSpectrum W = Analyse(White, SampleRate, Case.F0);

        const bool bPeakNear = std::fabs(S.PeakHz - Case.F0) <= 0.35 * Case.F0;
        const bool bBandLimited = S.FractionAboveFourF0 < 0.20 && S.FractionAboveFourF0 < 0.35 * W.FractionAboveFourF0;
        // Amplitude must be the same for both cases, or the normalisation is a
        // function of frequency and the altar reads as a strobe while the wick reads
        // as a flat card. The band is FlickerTargetRms +/- 25%.
        const bool bAlive = S.Rms > 0.75 * FlickerTargetRms && S.Rms < 1.25 * FlickerTargetRms &&
                            S.MaxAbs < 4.0 && std::fabs(S.Mean) < 0.25 * std::max(S.Rms, 1e-9) + 0.05;

        Record((std::string("flicker_") + Case.Label + "_peak_near_puffing_frequency").c_str(), bPeakNear && S.bFinite,
               "target " + Num(Case.F0) + " Hz, measured peak " + Num(S.PeakHz) + " Hz, centroid " + Num(S.Centroid) + " Hz");
        Record((std::string("flicker_") + Case.Label + "_is_band_limited_not_white").c_str(), bBandLimited,
               "energy above 4*f0: filtered " + Num(S.FractionAboveFourF0) + " vs white-noise control " + Num(W.FractionAboveFourF0));
        Record((std::string("flicker_") + Case.Label + "_amplitude_usable").c_str(), bAlive,
               "rms " + Num(S.Rms) + " (target " + Num(FlickerTargetRms) + " +/- 25%), max|v| " + Num(S.MaxAbs) + ", mean " + Num(S.Mean));
    }

    // Frame-rate independence: the same centre frequency at 30 fps and at 240 fps.
    // A resonator with fixed coefficients would fail this outright.
    double PeakAt[2] = {0.0, 0.0};
    const double Rates[2] = {30.0, 240.0};
    for (int R = 0; R < 2; ++R)
    {
        FFlicker Flicker;
        Flicker.Reset(0x46505321u, 3.0, 4.0);
        for (int I = 0; I < 2000; ++I) { Flicker.Advance(1.0 / Rates[R]); }
        std::vector<double> Samples;
        Samples.reserve(2048);
        for (size_t I = 0; I < 2048; ++I) { Samples.push_back(Flicker.Advance(1.0 / Rates[R])); }
        PeakAt[R] = Analyse(Samples, Rates[R], 3.0).PeakHz;
    }
    Record("flicker_frame_rate_independent", std::fabs(PeakAt[0] - PeakAt[1]) <= 0.35 * 3.0,
           "3 Hz target: peak at 30 fps " + Num(PeakAt[0]) + " Hz, at 240 fps " + Num(PeakAt[1]) + " Hz");

    // The multiplier the material actually receives must stay positive and bounded.
    bool bMultiplierOk = true;
    for (int I = -400; I <= 400; ++I)
    {
        const double M = FlickerMultiplier(I * 0.01, 0.25);
        if (!(M >= 0.75 - 1e-12 && M <= 1.25 + 1e-12)) { bMultiplierOk = false; }
    }
    Record("flicker_multiplier_bounded", bMultiplierOk, "depth 0.25 maps any flicker value into [0.75, 1.25]");
}

// ---------------------------------------------------------------------------
// 4. Embers
// ---------------------------------------------------------------------------
void TestEmbers()
{
    FEmberProfile Ember;
    const FPlumeProfile Plume = OuterAltarProfile();

    const int Count = 40000;
    std::vector<double> Lifetimes;
    Lifetimes.reserve(Count);
    bool bBounded = true;
    double SumLog = 0.0;
    for (int I = 0; I < Count; ++I)
    {
        const double Life = EmberLifetimeS(Ember, 0x454d4252u, static_cast<uint32_t>(I));
        if (!std::isfinite(Life) || Life < Ember.MinLifetimeS - 1e-12 || Life > Ember.MaxLifetimeS + 1e-12) { bBounded = false; }
        Lifetimes.push_back(Life);
        SumLog += std::log(Life);
    }
    std::vector<double> Sorted = Lifetimes;
    std::sort(Sorted.begin(), Sorted.end());
    const double Median = Sorted[Count / 2];
    const double MeanLog = SumLog / Count;
    double VarLog = 0.0;
    for (double Life : Lifetimes) { const double D = std::log(Life) - MeanLog; VarLog += D * D; }
    const double SdLog = std::sqrt(VarLog / Count);

    Record("ember_lifetimes_bounded", bBounded,
           std::to_string(Count) + " draws all within [" + Num(Ember.MinLifetimeS) + ", " + Num(Ember.MaxLifetimeS) + "] s");
    Record("ember_lifetime_is_lognormal", std::fabs(Median - Ember.MedianLifetimeS) < 0.06 * Ember.MedianLifetimeS && std::fabs(SdLog - Ember.LogSigma) < 0.10 * Ember.LogSigma,
           "sample median " + Num(Median) + " s vs requested " + Num(Ember.MedianLifetimeS) + " s; sd of log " + Num(SdLog) + " vs requested " + Num(Ember.LogSigma));
    Record("ember_lifetime_has_a_tail", Sorted[Count - 1] > 3.0 * Median && Sorted[Count / 20] < 0.7 * Median,
           "5th percentile " + Num(Sorted[Count / 20]) + " s, longest " + Num(Sorted[Count - 1]) + " s: most die early, a few ride the column");

    bool bHeightMonotone = true;
    double Previous = -1.0;
    for (int I = 0; I <= 1000; ++I)
    {
        const double H = EmberHeightCm(Ember, Plume, I * 0.01);
        if (!std::isfinite(H) || H < Previous - 1e-9) { bHeightMonotone = false; }
        Previous = H;
    }
    Record("ember_height_monotone", bHeightMonotone,
           "height rises monotonically to " + Num(EmberHeightCm(Ember, Plume, 10.0)) + " cm at 10 s and never exceeds the " + Num(Plume.MaxHeightCm) + " cm cap");

    const bool bFadeOk = EmberBrightness(0.0, 2.0) == 1.0 && EmberBrightness(2.0, 2.0) == 0.0 && EmberBrightness(3.0, 2.0) == 0.0;
    Record("ember_fades_to_black_at_end_of_life", bFadeOk, "brightness 1 at birth, exactly 0 at and after the lifetime");
}

// ---------------------------------------------------------------------------
// 5. Budget
// ---------------------------------------------------------------------------
void TestBudget()
{
    bool bMonotone = true;
    double Previous = 2.0;
    for (int I = 0; I <= 4000; ++I)
    {
        const double Q = DistanceQuality(I * 10.0, 3000.0, 24000.0);
        if (Q > Previous + 1e-12 || Q < 0.0 || Q > 1.0) { bMonotone = false; }
        Previous = Q;
    }
    const bool bEnds = DistanceQuality(0.0, 3000.0, 24000.0) == 1.0 && DistanceQuality(24000.0, 3000.0, 24000.0) == 0.0;
    Record("distance_quality_monotone_and_bounded", bMonotone && bEnds,
           "quality 1 within 3000 cm, 0 beyond 24000 cm, monotone in between");

    bool bCardsOk = true;
    for (int I = 0; I <= 100; ++I)
    {
        const int32_t C = CardCountForQuality(I * 0.01, 4, 28);
        if (C < 0 || C > 28) { bCardsOk = false; }
        if (I > 0 && C < 4) { bCardsOk = false; }
    }
    bCardsOk = bCardsOk && CardCountForQuality(0.0, 4, 28) == 0 && CardCountForQuality(1.0, 4, 28) == 28;
    Record("card_count_respects_bounds", bCardsOk, "0 cards only at quality 0; 4..28 cards otherwise; 28 at full quality");
}

// ---------------------------------------------------------------------------
// 6. NaN and infinity sweep over every public entry point
// ---------------------------------------------------------------------------
void TestNoNaNs()
{
    const double Nan = std::numeric_limits<double>::quiet_NaN();
    const double Inf = std::numeric_limits<double>::infinity();
    const double Nasty[9] = {Nan, Inf, -Inf, 0.0, -0.0, -1e30, 1e30, -1.0, 1e-300};

    int Evaluations = 0;
    int NonFinite = 0;
    std::string FirstBad;

    auto Check = [&](const char* Where, double Value)
    {
        ++Evaluations;
        if (!std::isfinite(Value))
        {
            ++NonFinite;
            if (FirstBad.empty()) { FirstBad = Where; }
        }
    };

    for (double A : Nasty)
    {
        for (double B : Nasty)
        {
            FPlumeProfile P;
            P.SourceRadiusCm = A;
            P.RiseSpeedCmS = B;
            P.EntrainmentAlpha = A;
            P.MaxRadiusCm = B;
            P.MaxHeightCm = A;
            P.BendGain = B;
            P.MinOpacity = A;

            FWind Wind;
            Wind.DirX = A;
            Wind.DirY = B;
            Wind.SpeedCmS = A;

            Check("PlumeRiseSpeedCmS", PlumeRiseSpeedCmS(P, B));
            Check("PlumeRadiusCm", PlumeRadiusCm(P, B));
            Check("PlumeTimeToHeightS", PlumeTimeToHeightS(P, B));
            Check("PlumeHeightAtAgeCm", PlumeHeightAtAgeCm(P, B));
            Check("PlumeAxisOffsetCm", PlumeAxisOffsetCm(P, B, Wind));
            Check("PlumeOpacity", PlumeOpacity(P, B));

            const FPlumeSample S = SamplePlumeAtAge(P, B, Wind);
            Check("SamplePlumeAtAge.Height", S.HeightCm);
            Check("SamplePlumeAtAge.Radius", S.RadiusCm);
            Check("SamplePlumeAtAge.Offset", S.AxisOffsetCm);
            Check("SamplePlumeAtAge.Opacity", S.Opacity);
            Check("SamplePlumeAtAge.RiseSpeed", S.RiseSpeedCmS);
            Check("SamplePlumeAtAge.WorldX", S.AxisOffsetWorldCm.X);
            Check("SamplePlumeAtAge.WorldY", S.AxisOffsetWorldCm.Y);
            Check("SamplePlumeAtAge.WorldZ", S.AxisOffsetWorldCm.Z);

            FVec3 Point;
            Point.X = A;
            Point.Y = B;
            Point.Z = A;
            // Boolean, but it must not trap or assert.
            ++Evaluations;
            (void)IsInsidePlumeEnvelope(P, Point, Wind, B);

            FCeilingSpread Room;
            Room.SourceZCm = A;
            Room.CeilingZCm = B;
            Room.RoomRadiusCm = A;
            Room.SpreadTimeConstantS = B;
            Room.FillTimeConstantS = A;
            Room.MaxLayerDepthCm = B;
            Check("CeilingImpingementTimeS", CeilingImpingementTimeS(P, Room));
            Check("CeilingSpreadRadiusCm", CeilingSpreadRadiusCm(Room, A));
            Check("CeilingLayerDepthCm", CeilingLayerDepthCm(Room, A));
            Check("CeilingLayerBottomZCm", CeilingLayerBottomZCm(Room, A));
            Check("CeilingSpreadFraction", CeilingSpreadFraction(Room, A));

            FKetoresTiming Timing;
            Timing.EmissionSeconds = A;
            Timing.AccumulateSeconds = B;
            Timing.DissipateSeconds = A;
            Check("KetoresDensity", KetoresDensity(Timing, P, Room, B));
            ++Evaluations;
            (void)KetoresPhaseAt(Timing, P, Room, B);

            Check("PuffingFrequencyHz", PuffingFrequencyHz(A));
            FFlicker Flicker;
            Flicker.Reset(0u, A, B);
            for (int I = 0; I < 32; ++I) { Check("FFlicker::Advance", Flicker.Advance(A)); }
            Check("FlickerMultiplier", FlickerMultiplier(A, B));

            Check("NormalQuantile", NormalQuantile(A));
            FEmberProfile Ember;
            Ember.MedianLifetimeS = A;
            Ember.LogSigma = B;
            Ember.MinLifetimeS = A;
            Ember.MaxLifetimeS = B;
            Ember.LaunchSpeedCmS = A;
            Ember.DragTimeConstantS = B;
            Check("EmberLifetimeS", EmberLifetimeS(Ember, 7u, 11u));
            Check("EmberHeightCm", EmberHeightCm(Ember, P, A));
            Check("EmberBrightness", EmberBrightness(A, B));

            Check("DistanceQuality", DistanceQuality(A, B, A));
            ++Evaluations;
            (void)CardCountForQuality(A, -5, 9999);
            Check("EstimatedOverdraw", EstimatedOverdraw(12, A));
        }
    }

    Record("no_nan_or_infinity_from_any_entry_point", NonFinite == 0,
           std::to_string(Evaluations) + " evaluations over the cross product of {NaN, +inf, -inf, 0, -0, -1e30, 1e30, -1, 1e-300}" +
           (NonFinite == 0 ? "; every result finite" : "; first non-finite at " + FirstBad));

    // Determinism: the same seed must give the same stream, or the offline Python
    // generator and the runtime would disagree.
    FFlicker A1, A2;
    A1.Reset(1234u, 7.0, 4.0);
    A2.Reset(1234u, 7.0, 4.0);
    bool bSame = true;
    for (int I = 0; I < 5000; ++I)
    {
        if (A1.Advance(1.0 / 120.0) != A2.Advance(1.0 / 120.0)) { bSame = false; }
    }
    bSame = bSame && EmberLifetimeS(FEmberProfile(), 99u, 7u) == EmberLifetimeS(FEmberProfile(), 99u, 7u);
    Record("deterministic_for_a_given_seed", bSame, "two flickers with seed 1234 agree bit for bit over 5000 steps; ember draws repeat exactly");
}

} // namespace

int main(int Argc, char** Argv)
{
    TestPlumeEnvelope();
    TestKetoresShape();
    TestFlicker();
    TestEmbers();
    TestBudget();
    TestNoNaNs();

    int Failures = 0;
    for (const FCheck& Check : Checks)
    {
        if (!Check.bPassed) { ++Failures; }
        std::printf("%s  %-52s  %s\n", Check.bPassed ? "PASS" : "FAIL", Check.Name.c_str(), Check.Detail.c_str());
    }
    std::printf("\n%d checks, %d failed\n", static_cast<int>(Checks.size()), Failures);

    if (Argc > 1)
    {
        FILE* File = nullptr;
        if (fopen_s(&File, Argv[1], "wb") == 0 && File)
        {
            std::fprintf(File, "{\n");
            std::fprintf(File, "  \"status\": \"%s\",\n", Failures == 0 ? "plume_math_standalone_tests_passed" : "plume_math_standalone_tests_failed");
            std::fprintf(File, "  \"suite\": \"Plugins/MikdashRuntime/Source/MikdashRuntime/Tests/PlumeMathTest.cpp\",\n");
            std::fprintf(File, "  \"header\": \"Plugins/MikdashRuntime/Source/MikdashRuntime/Public/PlumeMath.h\",\n");
            std::fprintf(File, "  \"compiler\": \"MSVC %d, C++%ld\",\n", static_cast<int>(_MSC_VER), static_cast<long>(__cplusplus));
            std::fprintf(File, "  \"checkCount\": %d,\n", static_cast<int>(Checks.size()));
            std::fprintf(File, "  \"failureCount\": %d,\n", Failures);
            std::fprintf(File, "  \"scope\": \"Pure math only. This proves the plume envelope, the flicker spectrum, the ember distribution and NaN safety. It does NOT prove that anything renders, that a material compiles, or that the effect looks right; those remain visual acceptance items.\",\n");
            std::fprintf(File, "  \"checks\": [\n");
            for (size_t I = 0; I < Checks.size(); ++I)
            {
                std::fprintf(File, "    {\"name\": \"%s\", \"passed\": %s, \"detail\": \"%s\"}%s\n",
                             JsonEscape(Checks[I].Name).c_str(), Checks[I].bPassed ? "true" : "false",
                             JsonEscape(Checks[I].Detail).c_str(), I + 1 == Checks.size() ? "" : ",");
            }
            std::fprintf(File, "  ]\n}\n");
            std::fclose(File);
            std::printf("receipt written to %s\n", Argv[1]);
        }
        else
        {
            std::printf("could not write %s\n", Argv[1]);
            return 2;
        }
    }
    return Failures == 0 ? 0 : 1;
}
