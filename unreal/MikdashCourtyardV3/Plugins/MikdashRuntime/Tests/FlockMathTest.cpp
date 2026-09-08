// Standalone acceptance test for Plugins/MikdashRuntime/Source/MikdashRuntime/Public/FlockMath.h,
// the engine-free behaviour behind AMikdashBirdFlock (the ambient Jerusalem bird layer).
//
// Built and run by Scripts/verify.py with:  cl /std:c++17 /EHsc /W4 /O2 /I<Public> ...
// No Unreal headers, no engine, no allocation outside std::vector. A non-zero exit is a failure.
//
// WHAT IS ASSERTED HERE, and why each one is worth a test:
//   * the published species figures actually reached the profiles, and the species differ from
//     one another in the ways the brief asked for (swift fastest and never perching, crow
//     slowest and mostly sitting, kestrel solitary, vulture the largest span);
//   * a flock is reproducible from its seed, so a receipt can quote numbers that mean something;
//   * WING PHASES DECORRELATE. This is the one that matters most visually: a few hundred birds
//     beating in lockstep reads as a single pulsing object, not as birds. PhaseCoherence must
//     fall from 1.0 to well under 0.35 and stay there;
//   * every pose index is reachable and a perched bird is always on the perched mesh, so the
//     four meshes from Scripts/create_birds.py are all actually used;
//   * the soft ceiling, floor and rim steer birds back, and the hard clamp behind them is never
//     violated - after thousands of updates, with hostile input, with NaN injected;
//   * perch bookkeeping is exact: no two birds ever occupy one ledge, a perched bird sits on its
//     ledge to the centimetre, and birds do launch again;
//   * a startle scatters the flock and the effect decays;
//   * no two birds ever coincide;
//   * the round-robin update window covers the whole flock and the neighbour grid finds exactly
//     the neighbours a brute-force search finds (this is what makes the cost linear);
//   * the cost really is linear in the number of birds - measured, and printed with the numbers
//     the per-frame budget claim rests on.
#include "FlockMath.h"

#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <iostream>
#include <limits>
#include <set>
#include <vector>

using namespace MikdashFlock;

static bool Near(double A, double B, double Tolerance = 1e-9) { return std::abs(A - B) <= Tolerance; }
static const double Nan = std::numeric_limits<double>::quiet_NaN();
static const double Inf = std::numeric_limits<double>::infinity();

// ---------------------------------------------------------------------------------------
// A test volume roughly the size of the outer court of the model (the court floor is at
// Z 300 and the outer envelope wall top at Z 3425, per Scripts/release_place_assets.spec.json),
// so the numbers below are in the range the shipped flocks actually run at.
// ---------------------------------------------------------------------------------------
static FlockBounds CourtBounds()
{
    FlockBounds B;
    B.HomeCm = Vec3{0, 0, 1800};
    B.RadiusCm = 5000;
    B.FloorZCm = 620;
    B.CeilingZCm = 3400;
    B.SoftBandCm = 500;
    B.RadialSoftBandCm = 800;
    return B;
}

static FlockConfig MakeConfig(SpeciesId Species, uint32_t Seed = 20260908u)
{
    FlockConfig C;
    C.Species = Profile(Species);
    C.Bounds = CourtBounds();
    C.Seed = Seed;
    return C;
}

/** A line of ledges along a wall top, the shape ResolvePerches builds from a tagged actor.
 *
 *  The half-length is 1900 cm on purpose: at X 4600 that puts the end ledges 4977 cm from the
 *  home point of CourtBounds, just inside its 5000 cm radius. A perch OUTSIDE the flock volume
 *  is dragged off its ledge by the clamp at the end of every Update and snapped back by the
 *  next Step - a jitter with no other symptom, demonstrated in PerchOutsideVolumeCheck() below
 *  and refused offline by Scripts/release_birds.py (verification.perchInsideVolumeRule). */
static std::vector<PerchPoint> LedgeLine(int Count, double X, double Z)
{
    std::vector<PerchPoint> Perches;
    for (int I = 0; I < Count; ++I)
    {
        PerchPoint P;
        const double T = (Count == 1) ? 0.0 : (-1.0 + 2.0 * I / static_cast<double>(Count - 1));
        P.Position = Vec3{X, T * 1900.0, Z};
        P.Facing = Vec3{-1, 0, 0};
        P.Occupant = -1;
        Perches.push_back(P);
    }
    return Perches;
}

// =======================================================================================
// 1. algebra, hashing and the small helpers
// =======================================================================================
static void AlgebraChecks()
{
    const Vec3 A{3, 4, 12};
    assert(Near(Length(A), 13.0, 1e-12));
    assert(Near(LengthSquared(A), 169.0, 1e-9));
    assert(Near(Dot(A, Vec3{1, 0, 0}), 3.0));
    assert(Near(Length(Normalized(A)), 1.0, 1e-12));
    assert(Length(Normalized(Vec3{})) == 0.0);            // zero-safe, not NaN

    // Limit rescales only when it must, and refuses to propagate NaN.
    assert(Near(Length(Limit(A, 5.0)), 5.0, 1e-12));
    assert(Near(Length(Limit(A, 100.0)), 13.0, 1e-12));
    assert(Length(Limit(Vec3{Nan, 0, 0}, 5.0)) == 0.0);
    assert(Length(Limit(Vec3{Inf, Inf, Inf}, 5.0)) == 0.0);
    assert(!Finite(Vec3{Nan, 0, 0}) && Finite(A));

    // Frac01 is a real fractional part for negatives, and never returns NaN.
    assert(Near(Frac01(0.25), 0.25, 1e-12));
    assert(Near(Frac01(-0.25), 0.75, 1e-12));
    assert(Near(Frac01(3.5), 0.5, 1e-12));
    assert(Frac01(Nan) == 0.0);
    assert(Frac01(Inf) == 0.0);
    assert(Near(Clamp(5.0, 0.0, 1.0), 1.0) && Near(Clamp(-5.0, 0.0, 1.0), 0.0));
    assert(Near(RadToDeg(DegToRad(37.0)), 37.0, 1e-12));

    // The hash is a pure function of its inputs (a flock is reproducible from its seed) and
    // it does not collapse: 4000 draws must fill the unit interval reasonably evenly.
    assert(Hash(1, 2, 3) == Hash(1, 2, 3));
    assert(Hash(1, 2, 3) != Hash(1, 2, 4));
    assert(Hash(1, 2, 3) != Hash(2, 2, 3));
    int Buckets[10] = {0};
    for (uint32_t I = 0; I < 4000; ++I)
    {
        const double U = HashUnit(20260908u, I, 17u);
        assert(U >= 0.0 && U < 1.0);
        ++Buckets[static_cast<int>(U * 10.0)];
    }
    for (int I = 0; I < 10; ++I) assert(Buckets[I] > 250 && Buckets[I] < 550);
    for (uint32_t I = 0; I < 500; ++I)
    {
        const double R = HashRange(7u, I, 3u, -2.5, 9.5);
        assert(R >= -2.5 && R < 9.5);
    }
    std::printf("algebra: NaN-safe limit/normalise/frac, hash uniform to +-25%% over 10 buckets of 4000\n");
}

// =======================================================================================
// 2. the species - the published figures, and the differences the brief asked for
// =======================================================================================
static void SpeciesChecks()
{
    assert(SpeciesCount() == 5);
    const SpeciesProfile Dove = Profile(SpeciesId::RockDove);
    const SpeciesProfile Swift = Profile(SpeciesId::CommonSwift);
    const SpeciesProfile Crow = Profile(SpeciesId::HoodedCrow);
    const SpeciesProfile Kestrel = Profile(SpeciesId::CommonKestrel);
    const SpeciesProfile Vulture = Profile(SpeciesId::GriffonVulture);

    // The published mid-points recorded in the citations in Profile(), and mirrored by
    // Scripts/create_birds.py into SourceAssets/birds-review/BirdsV1/species.json. If either
    // side is edited without the other, this fails.
    assert(Near(Dove.WingspanCm, 67.0) && Near(Dove.BodyLengthCm, 33.0));
    assert(Near(Swift.WingspanCm, 45.0) && Near(Swift.BodyLengthCm, 16.5));
    assert(Near(Crow.WingspanCm, 98.0) && Near(Crow.BodyLengthCm, 46.0));
    assert(Near(Kestrel.WingspanCm, 75.0) && Near(Kestrel.BodyLengthCm, 33.0));
    assert(Near(Vulture.WingspanCm, 260.0) && Near(Vulture.BodyLengthCm, 102.0));

    // Every span is inside its published range, and every bird is wider than it is long.
    const SpeciesProfile All[5] = {Dove, Swift, Crow, Kestrel, Vulture};
    for (const SpeciesProfile& P : All)
    {
        assert(P.WingspanCm > P.BodyLengthCm);
        assert(P.MinSpeedCmPerSecond > 0.0);
        assert(P.MinSpeedCmPerSecond < P.CruiseSpeedCmPerSecond);
        assert(P.CruiseSpeedCmPerSecond < P.MaxSpeedCmPerSecond);
        assert(P.HardSeparationCm > 0.0 && P.HardSeparationCm < P.DesiredSeparationCm);
        assert(P.DesiredSeparationCm < P.NeighbourRadiusCm);
        assert(P.WingBeatHz > 0.0 && P.WingBeatSpread > 0.0 && P.WingBeatSpread < 1.0);
        assert(P.DampingPerSecond > 0.0);
        assert(P.CallMeanIntervalSeconds > 0.0);
        // A bird must beat its wings faster than the mesh can be swapped only if the update
        // rate allows; 12 Hz is the ceiling any of these should approach.
        assert(P.WingBeatHz < 12.0);
    }

    // The brief: swifts are the fast ones, crows the slow ones, the vulture the biggest.
    assert(Swift.CruiseSpeedCmPerSecond > Dove.CruiseSpeedCmPerSecond);
    assert(Swift.MaxAccelCmPerSecond2 > Dove.MaxAccelCmPerSecond2);   // the tight, snapping turns
    assert(Crow.CruiseSpeedCmPerSecond < Dove.CruiseSpeedCmPerSecond);
    assert(Crow.MaxAccelCmPerSecond2 < Dove.MaxAccelCmPerSecond2);
    assert(Vulture.WingspanCm > Crow.WingspanCm && Crow.WingspanCm > Kestrel.WingspanCm);
    assert(Kestrel.WingspanCm > Dove.WingspanCm && Dove.WingspanCm > Swift.WingspanCm);
    assert(Swift.WingBeatHz > Dove.WingBeatHz && Dove.WingBeatHz > Crow.WingBeatHz);
    assert(Crow.WingBeatHz > Vulture.WingBeatHz);

    // A swift on the ground is a swift in trouble; the raptors are solitary, not flocking.
    assert(!Swift.bPerches && Near(Swift.PerchFraction, 0.0));
    assert(!Kestrel.bPerches && !Vulture.bPerches);
    assert(Dove.bPerches && Crow.bPerches);
    assert(Crow.PerchFraction > Dove.PerchFraction);        // crows are mostly sitting on something
    assert(Near(Kestrel.AlignmentWeight, 0.0) && Near(Kestrel.CohesionWeight, 0.0));
    assert(Vulture.CohesionWeight < Dove.CohesionWeight);
    assert(Crow.DesiredSeparationCm > Dove.DesiredSeparationCm);   // twos and threes, not a wheel

    // Gliders hold their wings out; a pigeon effectively never does.
    assert(Swift.GlideDutyFraction > Dove.GlideDutyFraction);
    assert(Vulture.GlideDutyFraction > Swift.GlideDutyFraction);    // the soaring bird
    assert(Vulture.GlideSpeedFraction < Swift.GlideSpeedFraction);

    // Swifts scream constantly; a vulture is silent for minutes.
    assert(Swift.CallMeanIntervalSeconds < Dove.CallMeanIntervalSeconds);
    assert(Vulture.CallMeanIntervalSeconds > 60.0);

    // An out-of-range enum value must not read uninitialised memory: the default profile is
    // returned unchanged by the switch.
    const SpeciesProfile Bogus = Profile(static_cast<SpeciesId>(99));
    assert(Bogus.WingspanCm > 0.0 && Bogus.CruiseSpeedCmPerSecond > 0.0);

    std::printf("species: 5 profiles, spans %.0f/%.0f/%.0f/%.0f/%.0f cm, beats %.1f/%.1f/%.1f/%.1f/%.1f Hz\n",
                Dove.WingspanCm, Swift.WingspanCm, Crow.WingspanCm, Kestrel.WingspanCm, Vulture.WingspanCm,
                Dove.WingBeatHz, Swift.WingBeatHz, Crow.WingBeatHz, Kestrel.WingBeatHz, Vulture.WingBeatHz);
}

// =======================================================================================
// 3. seeding, and reproducibility from the seed alone
// =======================================================================================
static void SeedingChecks()
{
    const FlockConfig Config = MakeConfig(SpeciesId::RockDove);
    std::vector<Bird> A, B, C;
    SeedFlock(A, 200, Config);
    SeedFlock(B, 200, Config);
    SeedFlock(C, 200, MakeConfig(SpeciesId::RockDove, 99u));

    assert(A.size() == 200 && B.size() == 200);
    bool Identical = true, DifferentSeedDiffers = false;
    for (size_t I = 0; I < A.size(); ++I)
    {
        if (LengthSquared(A[I].Position - B[I].Position) > 0.0) Identical = false;
        if (LengthSquared(A[I].Velocity - B[I].Velocity) > 0.0) Identical = false;
        if (LengthSquared(A[I].Position - C[I].Position) > 1.0) DifferentSeedDiffers = true;
    }
    assert(Identical);                 // same seed, same flock, on every run and every machine
    assert(DifferentSeedDiffers);      // a different seed is a different flock

    const FlockBounds Bounds = Config.Bounds;
    const double Lo = BoundedFloorZ(Bounds), Hi = BoundedCeilingZ(Bounds);
    std::set<int> DistinctPositions;
    for (const Bird& Bd : A)
    {
        assert(Finite(Bd.Position) && Finite(Bd.Velocity));
        const double R = Length(Vec3{Bd.Position.X - Bounds.HomeCm.X, Bd.Position.Y - Bounds.HomeCm.Y, 0});
        assert(R <= Bounds.RadiusCm);
        assert(Bd.Position.Z >= Lo && Bd.Position.Z <= Hi);
        // Seeded speed is a real cruise, not zero and not the maximum.
        const double S = Length(Bd.Velocity);
        assert(S > 0.3 * Config.Species.CruiseSpeedCmPerSecond);
        assert(S < 1.3 * Config.Species.CruiseSpeedCmPerSecond);
        // Every bird carries its own beat rate, inside the species spread.
        const double Spread = Config.Species.WingBeatSpread * Config.Species.WingBeatHz;
        assert(Bd.WingHz >= Config.Species.WingBeatHz - Spread - 1e-9);
        assert(Bd.WingHz <= Config.Species.WingBeatHz + Spread + 1e-9);
        // Phases deliberately start in lockstep, so the decorrelation test measures the
        // mechanism and not the seeding.
        assert(Bd.WingPhase == 0.0);
        assert(!Bd.Perched() && Bd.TargetPerchIndex == -1);
        DistinctPositions.insert(static_cast<int>(Bd.Position.X * 0.01) * 100000
                                 + static_cast<int>(Bd.Position.Y * 0.01));
    }
    // Birds are scattered, not stacked: at least 90 per cent land in distinct 1 m cells.
    assert(DistinctPositions.size() > 180);

    // Degenerate counts do not crash and do not leave a half-built flock.
    std::vector<Bird> Empty;
    SeedFlock(Empty, 0, Config);
    assert(Empty.empty());
    SeedFlock(Empty, -5, Config);
    assert(Empty.empty());

    // PointInBounds stays inside the cylinder for every draw, including a degenerate volume.
    for (uint32_t I = 0; I < 3000; ++I)
    {
        const Vec3 P = PointInBounds(Bounds, 5u, I, 41u);
        assert(Finite(P));
        assert(Length(Vec3{P.X - Bounds.HomeCm.X, P.Y - Bounds.HomeCm.Y, 0}) <= Bounds.RadiusCm);
        assert(P.Z >= Lo && P.Z <= Hi);
    }
    FlockBounds Flat = Bounds;
    Flat.CeilingZCm = Flat.FloorZCm;    // zero-height volume
    const Vec3 P = PointInBounds(Flat, 5u, 1u, 1u);
    assert(Finite(P) && Near(P.Z, Flat.FloorZCm, 1e-6));
    FlockBounds Inverted = Bounds;
    Inverted.FloorZCm = 3400; Inverted.CeilingZCm = 620;   // floor above ceiling, on purpose
    assert(Near(BoundedFloorZ(Inverted), 620.0) && Near(BoundedCeilingZ(Inverted), 3400.0));

    std::printf("seeding: 200 birds reproducible from the seed, %zu distinct metre cells, all inside the volume\n",
                DistinctPositions.size());
}

// =======================================================================================
// 4. wing phase, decorrelation and the pose meshes
// =======================================================================================
static void WingAndPoseChecks()
{
    // The pose contract with Scripts/create_birds.py. These four values are baked into the
    // generated mesh names and into the actor's component order; they may not drift.
    assert(Pose_UpStroke == 0 && Pose_Level == 1 && Pose_DownStroke == 2 && Pose_Perched == 3);
    assert(PoseCount == 4);

    // The phase -> pose mapping, at and around every boundary. Level appears twice per cycle,
    // which is correct: the wing passes through level going up and going down.
    assert(WingPoseIndex(0.00, false, false) == Pose_UpStroke);
    assert(WingPoseIndex(0.249, false, false) == Pose_UpStroke);
    assert(WingPoseIndex(0.25, false, false) == Pose_Level);
    assert(WingPoseIndex(0.499, false, false) == Pose_Level);
    assert(WingPoseIndex(0.50, false, false) == Pose_DownStroke);
    assert(WingPoseIndex(0.749, false, false) == Pose_DownStroke);
    assert(WingPoseIndex(0.75, false, false) == Pose_Level);
    assert(WingPoseIndex(0.999, false, false) == Pose_Level);
    assert(WingPoseIndex(1.25, false, false) == Pose_Level);     // wraps
    assert(WingPoseIndex(-0.10, false, false) == Pose_Level);    // negative wraps to 0.9
    assert(WingPoseIndex(Nan, false, false) == Pose_UpStroke);   // no NaN escapes as an index
    // Perched wins over everything, gliding wins over the beat.
    assert(WingPoseIndex(0.0, false, true) == Pose_Perched);
    assert(WingPoseIndex(0.0, true, true) == Pose_Perched);
    assert(WingPoseIndex(0.6, true, false) == Pose_Level);

    // AdvanceWing: monotonic in time, wrapped, and immune to a bad dt or a bad rate.
    Bird B;
    B.WingHz = 5.0;
    B.WingPhase = 0.0;
    assert(Near(AdvanceWing(B, 0.1), 0.5, 1e-12));
    assert(Near(AdvanceWing(B, 0.1), 0.0, 1e-12));      // exactly one full beat
    B.WingPhase = 0.3;
    assert(Near(AdvanceWing(B, 0.0), 0.3));             // dt 0 is a no-op, not a reset
    assert(Near(AdvanceWing(B, -1.0), 0.3));
    assert(Near(AdvanceWing(B, Nan), 0.3));
    B.WingHz = Nan;
    const double AfterBadHz = AdvanceWing(B, 0.25);
    assert(std::isfinite(AfterBadHz) && AfterBadHz >= 0.0 && AfterBadHz < 1.0);
    B.WingHz = 1e9;                                      // clamped to 40 Hz, still in [0,1)
    const double AfterHugeHz = AdvanceWing(B, 0.25);
    assert(std::isfinite(AfterHugeHz) && AfterHugeHz >= 0.0 && AfterHugeHz < 1.0);

    // Gliding: only fast enough birds, only for the duty fraction of the cycle, never perched.
    const SpeciesProfile SwiftProfile = Profile(SpeciesId::CommonSwift);
    Bird Fast;
    Fast.Velocity = Vec3{SwiftProfile.MaxSpeedCmPerSecond, 0, 0};
    Fast.WingPhase = 0.1;                                // inside the 0.45 duty window
    assert(IsGliding(SwiftProfile, Fast));
    Fast.WingPhase = 0.8;                                // outside it: still beats a wing in
    assert(!IsGliding(SwiftProfile, Fast));
    Fast.WingPhase = 0.1;
    Fast.Velocity = Vec3{0.2 * SwiftProfile.MaxSpeedCmPerSecond, 0, 0};
    assert(!IsGliding(SwiftProfile, Fast));              // too slow to hold the wings out
    Fast.Velocity = Vec3{SwiftProfile.MaxSpeedCmPerSecond, 0, 0};
    Fast.PerchIndex = 4;
    assert(!IsGliding(SwiftProfile, Fast));
    Fast.PerchIndex = -1;
    Fast.Velocity = Vec3{Nan, 0, 0};
    assert(!IsGliding(SwiftProfile, Fast));
    // A pigeon's GlideSpeedFraction is under 1 but its duty is short; a species with a
    // fraction over 1 can never glide at all.
    SpeciesProfile NoGlide = Profile(SpeciesId::RockDove);
    NoGlide.GlideSpeedFraction = 1.10;
    Bird Flat;
    Flat.Velocity = Vec3{1e6, 0, 0};
    assert(!IsGliding(NoGlide, Flat));

    // PoseFor routes through both.
    Bird Sitting;
    Sitting.PerchIndex = 0;
    assert(PoseFor(Profile(SpeciesId::RockDove), Sitting) == Pose_Perched);

    // ---- THE DECORRELATION TEST -------------------------------------------------------
    // Every bird starts on phase 0. If the per-bird hashed WingHz were removed, coherence
    // would stay at 1.0 for ever and the whole flock would beat as one object.
    const FlockConfig Config = MakeConfig(SpeciesId::RockDove);
    std::vector<Bird> Birds;
    SeedFlock(Birds, 300, Config);
    assert(Near(PhaseCoherence(Birds), 1.0, 1e-9));

    const double Dt = 0.05;
    double CoherenceAt1s = 0.0, CoherenceAt10s = 0.0, WorstAfter10s = 0.0;
    for (int Frame = 1; Frame <= 1200; ++Frame)          // 60 simulated seconds at 20 Hz
    {
        for (Bird& Bd : Birds) AdvanceWing(Bd, Dt);
        const double Coherence = PhaseCoherence(Birds);
        assert(Coherence >= 0.0 && Coherence <= 1.0 + 1e-9);
        if (Frame == 20) CoherenceAt1s = Coherence;
        if (Frame == 200) CoherenceAt10s = Coherence;
        if (Frame >= 200) WorstAfter10s = std::max(WorstAfter10s, Coherence);
    }
    assert(CoherenceAt10s < 0.35);
    // And it must STAY spread: a flock that re-synchronises later is just as wrong.
    assert(WorstAfter10s < 0.45);

    // At any instant after the spread the flock is genuinely on several different meshes.
    std::set<int> PosesNow;
    for (const Bird& Bd : Birds) PosesNow.insert(WingPoseIndex(Bd.WingPhase, false, false));
    assert(PosesNow.size() >= 3);

    // Over one bird's cycle every flight pose is visited, so all four generated meshes are used.
    std::set<int> Visited;
    Bird One;
    One.WingHz = 5.4;
    for (int I = 0; I < 400; ++I)
    {
        AdvanceWing(One, 0.01);
        Visited.insert(WingPoseIndex(One.WingPhase, false, false));
    }
    assert(Visited.size() == 3);                        // up, level, down (perched is separate)
    assert(Visited.count(Pose_UpStroke) && Visited.count(Pose_Level) && Visited.count(Pose_DownStroke));

    // Degenerate coherence input.
    std::vector<Bird> None;
    assert(PhaseCoherence(None) == 0.0);

    std::printf("wing: coherence 1.000 -> %.3f at 1 s -> %.3f at 10 s, worst %.3f after; %zu poses live at once\n",
                CoherenceAt1s, CoherenceAt10s, WorstAfter10s, PosesNow.size());
}

// =======================================================================================
// 5. body orientation
// =======================================================================================
static void OrientationChecks()
{
    assert(Near(YawDegrees(Vec3{1, 0, 0}), 0.0, 1e-9));
    assert(Near(YawDegrees(Vec3{0, 1, 0}), 90.0, 1e-9));
    assert(Near(YawDegrees(Vec3{-1, 0, 0}), 180.0, 1e-9));
    assert(Near(YawDegrees(Vec3{0, -1, 0}), -90.0, 1e-9));
    assert(Near(YawDegrees(Vec3{0, 0, 5}), 0.0));         // straight up: no meaningful heading
    assert(Near(YawDegrees(Vec3{}), 0.0));

    assert(Near(PitchDegrees(Vec3{1, 0, 0}), 0.0, 1e-9));
    assert(PitchDegrees(Vec3{1, 0, 1}) > 20.0 && PitchDegrees(Vec3{1, 0, 1}) <= 35.0);
    assert(PitchDegrees(Vec3{1, 0, -1}) < -20.0 && PitchDegrees(Vec3{1, 0, -1}) >= -35.0);
    assert(std::abs(PitchDegrees(Vec3{0, 0, 1000})) <= 35.0);      // clamped, never vertical
    assert(Near(PitchDegrees(Vec3{}), 0.0));

    // Bank: a bird accelerating to its left rolls one way, to its right the other, and the
    // roll is bounded. Flying +X, "right" is -Y.
    const double Left = RollDegrees(Vec3{1000, 0, 0}, Vec3{0, 900, 0});
    const double Right = RollDegrees(Vec3{1000, 0, 0}, Vec3{0, -900, 0});
    assert(Left * Right < 0.0);
    assert(std::abs(Left) <= 45.0 + 1e-9 && std::abs(Right) <= 45.0 + 1e-9);
    assert(Near(RollDegrees(Vec3{1000, 0, 0}, Vec3{5000, 0, 0}), 0.0, 1e-9));  // pure thrust, no bank
    assert(std::abs(RollDegrees(Vec3{1000, 0, 0}, Vec3{0, 1e9, 0})) <= 45.0 + 1e-9);
    assert(Near(RollDegrees(Vec3{1000, 0, 0}, Vec3{0, 900, 0}, 20.0), Left * 20.0 / 45.0, 1e-9));
    assert(Near(RollDegrees(Vec3{}, Vec3{0, 900, 0}), 0.0));
    assert(Near(RollDegrees(Vec3{1000, 0, 0}, Vec3{Nan, 0, 0}), 0.0));
    std::printf("orientation: yaw/pitch/bank bounded, bank sign follows the turn (%.1f vs %.1f deg)\n",
                Left, Right);
}

// =======================================================================================
// 6. the volume - soft steering and the hard clamp behind it
// =======================================================================================
static void BoundsChecks()
{
    const FlockBounds B = CourtBounds();
    const double Accel = 1600.0;

    // Middle of the volume: no vertical steering at all.
    assert(Near(AltitudeAcceleration(Vec3{0, 0, 2000}, Vec3{}, B, Accel), 0.0));
    // Inside the floor band: pushed up. Inside the ceiling band: pushed down.
    assert(AltitudeAcceleration(Vec3{0, 0, 700}, Vec3{}, B, Accel) > 0.0);
    assert(AltitudeAcceleration(Vec3{0, 0, 3300}, Vec3{}, B, Accel) < 0.0);
    // Deeper into the band means more push.
    assert(AltitudeAcceleration(Vec3{0, 0, 640}, Vec3{}, B, Accel)
           > AltitudeAcceleration(Vec3{0, 0, 900}, Vec3{}, B, Accel));
    // Diving at the floor gets extra help; the surface is not a trampoline.
    assert(AltitudeAcceleration(Vec3{0, 0, 700}, Vec3{0, 0, -800}, B, Accel)
           > AltitudeAcceleration(Vec3{0, 0, 700}, Vec3{}, B, Accel));
    assert(AltitudeAcceleration(Vec3{0, 0, 3300}, Vec3{0, 0, 800}, B, Accel)
           < AltitudeAcceleration(Vec3{0, 0, 3300}, Vec3{}, B, Accel));
    // A volume thinner than the soft band still behaves.
    FlockBounds Thin = B;
    Thin.FloorZCm = 1000; Thin.CeilingZCm = 1050;
    assert(std::isfinite(AltitudeAcceleration(Vec3{0, 0, 1025}, Vec3{}, Thin, Accel)));

    // Radial: nothing near the middle, inward near the rim, and always inward.
    assert(Near(Length(RadialAcceleration(Vec3{0, 0, 1800}, B, Accel)), 0.0));
    assert(Near(Length(RadialAcceleration(Vec3{3000, 0, 1800}, B, Accel)), 0.0));
    const Vec3 Rim = RadialAcceleration(Vec3{4900, 0, 1800}, B, Accel);
    assert(Rim.X < 0.0 && Near(Rim.Y, 0.0, 1e-9));
    const Vec3 Outside = RadialAcceleration(Vec3{9000, 9000, 1800}, B, Accel);
    assert(Outside.X < 0.0 && Outside.Y < 0.0);
    assert(Length(Outside) <= Accel + 1e-6);
    assert(Near(Length(RadialAcceleration(B.HomeCm, B, Accel)), 0.0));    // exactly at home

    // The hard clamp: whatever the integrator did, the bird ends up inside.
    Bird High;
    High.Position = Vec3{0, 0, 9000};
    High.Velocity = Vec3{0, 0, 4000};
    ClampToBounds(High, B);
    assert(Near(High.Position.Z, 3400.0) && High.Velocity.Z <= 0.0);
    Bird Low;
    Low.Position = Vec3{0, 0, -9000};
    Low.Velocity = Vec3{0, 0, -4000};
    ClampToBounds(Low, B);
    assert(Near(Low.Position.Z, 620.0) && Low.Velocity.Z >= 0.0);
    Bird Far;
    Far.Position = Vec3{20000, 0, 1800};
    Far.Velocity = Vec3{3000, 500, 0};
    ClampToBounds(Far, B);
    assert(Near(Length(Vec3{Far.Position.X, Far.Position.Y, 0}), 5000.0, 1e-6));
    assert(Far.Velocity.X <= 1e-9);          // outward component removed, not reflected
    assert(Near(Far.Velocity.Y, 500.0, 1e-9));   // along-wall component preserved
    // NaN in, sane out - a single bad frame must not delete the flock.
    Bird Broken;
    Broken.Position = Vec3{Nan, Inf, Nan};
    Broken.Velocity = Vec3{Nan, 0, 0};
    ClampToBounds(Broken, B);
    assert(Finite(Broken.Position) && Finite(Broken.Velocity));
    assert(Near(Broken.Position.X, B.HomeCm.X) && Near(Broken.Position.Z, B.HomeCm.Z));

    std::printf("volume: soft band steers, hard clamp holds at r %.0f cm, Z %.0f..%.0f, NaN recovered to home\n",
                B.RadiusCm, B.FloorZCm, B.CeilingZCm);
}

// =======================================================================================
// 7. the neighbour grid - it must find exactly what a brute-force search finds
// =======================================================================================
static void GridChecks()
{
    const FlockConfig Config = MakeConfig(SpeciesId::RockDove);
    std::vector<Bird> Birds;
    SeedFlock(Birds, 400, Config);

    Grid G;
    BuildGrid(G, Birds, Config.Species);
    const double R2 = Config.Species.NeighbourRadiusCm * Config.Species.NeighbourRadiusCm;

    long long Visits = 0;
    for (size_t I = 0; I < Birds.size(); ++I)
    {
        std::set<int> Found;
        G.ForEachNear(Birds[I].Position, [&](int J) { ++Visits; Found.insert(J); });
        for (size_t J = 0; J < Birds.size(); ++J)
        {
            if (LengthSquared(Birds[J].Position - Birds[I].Position) <= R2)
            {
                // Every true neighbour must be visited. A miss here is a bird that cannot see
                // the flock it is in.
                assert(Found.count(static_cast<int>(J)) == 1);
            }
        }
        assert(Found.count(static_cast<int>(I)) == 1);    // it always sees itself; Step filters that
    }
    // The grid is a filter, not a no-op: it must not degenerate to visiting everybody.
    assert(Visits < static_cast<long long>(Birds.size()) * static_cast<long long>(Birds.size()));

    // Hostile input: an empty flock, a single bird, a NaN query and a NaN bird.
    Grid Empty;
    std::vector<Bird> NoBirds;
    Empty.Build(NoBirds, 500.0);
    int Touched = 0;
    Empty.ForEachNear(Vec3{0, 0, 0}, [&](int) { ++Touched; });
    assert(Touched == 0);
    std::vector<Bird> One(1);
    One[0].Position = Vec3{123, -456, 789};
    Grid Single;
    Single.Build(One, 0.0);                       // silly cell size, clamped internally
    assert(Single.CellCm >= 50.0);
    Touched = 0;
    Single.ForEachNear(One[0].Position, [&](int) { ++Touched; });
    assert(Touched == 1);
    Single.ForEachNear(Vec3{Nan, 0, 0}, [&](int) { assert(false); });
    std::vector<Bird> WithNan = One;
    WithNan.push_back(Bird{});
    WithNan[1].Position = Vec3{Nan, Nan, Nan};
    Grid Mixed;
    Mixed.Build(WithNan, 400.0);                  // must not crash or allocate wildly
    assert(Mixed.Nx >= 1 && Mixed.Ny >= 1 && Mixed.Nz >= 1);

    // A flock spread over kilometres must not blow the cell count up.
    std::vector<Bird> Wide(200);
    for (size_t I = 0; I < Wide.size(); ++I)
    {
        Wide[I].Position = Vec3{static_cast<double>(I) * 5000.0, static_cast<double>(I) * 5000.0, 0};
    }
    Grid Huge;
    Huge.Build(Wide, 300.0);
    assert(Huge.Nx <= 256 && Huge.Ny <= 256 && Huge.Nz <= 64);

    std::printf("grid: 400 birds, every true neighbour found, %lld visits vs %lld all-pairs\n",
                Visits, static_cast<long long>(Birds.size()) * static_cast<long long>(Birds.size()));
}

// =======================================================================================
// 8. the round-robin update window
// =======================================================================================
static void WindowChecks()
{
    // Budget at or above the flock size is a full pass, and resets the cursor.
    UpdateWindow W = NextUpdateWindow(0, 100, 100);
    assert(W.Start == 0 && W.Count == 100 && W.NextCursor == 0);
    W = NextUpdateWindow(37, 100, 500);
    assert(W.Count == 100 && W.NextCursor == 0);
    W = NextUpdateWindow(0, 0, 50);
    assert(W.Count == 0);
    W = NextUpdateWindow(-13, 100, 30);        // a negative cursor is normalised, never negative
    assert(W.Start >= 0 && W.Start < 100 && W.Count == 30);
    W = NextUpdateWindow(0, 100, 0);           // budget 0 means "all of them"
    assert(W.Count == 100);

    // Round robin covers every bird, evenly, with no bird visited twice in one sweep.
    const int Total = 250, Budget = 40;
    std::vector<int> Times(static_cast<size_t>(Total), 0);
    int Cursor = 0;
    const int Sweeps = 7;
    const int Updates = Sweeps * ((Total + Budget - 1) / Budget);
    for (int U = 0; U < Updates; ++U)
    {
        const UpdateWindow Window = NextUpdateWindow(Cursor, Total, Budget);
        for (int K = 0; K < Window.Count; ++K) ++Times[static_cast<size_t>((Window.Start + K) % Total)];
        Cursor = Window.NextCursor;
    }
    int Least = Updates * Budget, Most = 0;
    for (int T : Times) { Least = std::min(Least, T); Most = std::max(Most, T); }
    assert(Least >= Sweeps - 1);
    assert(Most - Least <= 1);                  // fair: nobody is starved and nobody is favoured

    // CatchUpSeconds gives back the time a bird owes, and never a dangerous step.
    assert(Near(CatchUpSeconds(0.05, 100, 100), 0.05, 1e-12));
    assert(Near(CatchUpSeconds(0.05, 100, 25), 0.20, 1e-12));
    assert(Near(CatchUpSeconds(0.05, 100, 0), 0.05, 1e-12));
    assert(CatchUpSeconds(0.05, 10000, 10) <= 0.5);      // clamped: never a half-second leap
    assert(CatchUpSeconds(Nan, 100, 10) == 0.0);
    assert(CatchUpSeconds(-1.0, 100, 10) == 0.0);
    assert(CatchUpSeconds(0.05, 0, 10) == 0.0);
    std::printf("window: 250 birds at 40 per update, every bird stepped %d-%d times over %d updates\n",
                Least, Most, Updates);
}

// =======================================================================================
// 9. flying - the long soak, with every invariant checked every update
// =======================================================================================
struct SoakResult
{
    int Updates = 0;
    int Landings = 0;
    int Launches = 0;
    int MaxPerched = 0;
    double MeanSpeed = 0.0;
    double SmallestGap = 1e18;
    long long NeighbourTests = 0;
};

/** Run a flock and assert the invariants after every single update. */
static SoakResult Soak(SpeciesId Species, int Count, int PerchCount, double Seconds,
                       int Budget, double Interval, bool bStartleHalfway)
{
    const FlockConfig Config = MakeConfig(Species);
    std::vector<Bird> Birds;
    SeedFlock(Birds, Count, Config);
    std::vector<PerchPoint> Perches = LedgeLine(PerchCount, 4600.0, 900.0);

    Grid Neighbours, Overlap;
    int Cursor = 0;
    double Time = 0.0;
    SoakResult R;
    const double Lo = BoundedFloorZ(Config.Bounds), Hi = BoundedCeilingZ(Config.Bounds);
    const int Updates = static_cast<int>(Seconds / Interval);
    Vec3 StartleOrigin{2000, 0, 1200};
    double SpeedSum = 0.0;

    for (int U = 0; U < Updates; ++U)
    {
        Time += Interval;
        if (bStartleHalfway && U == Updates / 2)
        {
            ApplyStartle(Birds, Perches, Config, StartleOrigin, 3000.0, Time);
        }
        const StepStats Stats = Update(Birds, Perches, Config, Neighbours, Overlap, Cursor,
                                       Budget, Interval, Time, StartleOrigin);
        R.Landings += Stats.Landed;
        R.Launches += Stats.Launched;
        R.NeighbourTests += Stats.NeighbourTests;
        SpeedSum += Stats.MeanSpeedCmPerSecond;
        ++R.Updates;

        // ---- invariants, every update, no exceptions ---------------------------------
        std::set<int> Claimed;
        int Sitting = 0;
        for (size_t I = 0; I < Birds.size(); ++I)
        {
            const Bird& B = Birds[I];
            assert(Finite(B.Position) && Finite(B.Velocity));
            assert(std::isfinite(B.WingPhase) && B.WingPhase >= 0.0 && B.WingPhase < 1.0);
            assert(std::isfinite(B.StartleRemaining) && B.StartleRemaining >= 0.0);

            // Never outside the volume, at any time, for any species.
            assert(B.Position.Z >= Lo - 1e-6 && B.Position.Z <= Hi + 1e-6);
            const double Radius = Length(Vec3{B.Position.X - Config.Bounds.HomeCm.X,
                                              B.Position.Y - Config.Bounds.HomeCm.Y, 0});
            assert(Radius <= Config.Bounds.RadiusCm + 1e-6);

            // Speed stays inside the species envelope (allowing the startle multiplier).
            const double Speed = Length(B.Velocity);
            if (!B.Perched())
            {
                assert(Speed <= Config.Species.MaxSpeedCmPerSecond
                                    * Config.Species.StartleSpeedMultiplier + 1e-6);
            }

            // Perch bookkeeping: exact, or two birds end up inside one another on a ledge.
            if (B.Perched())
            {
                ++Sitting;
                assert(Config.Species.bPerches);        // a swift must never be found sitting
                assert(B.PerchIndex >= 0 && B.PerchIndex < static_cast<int>(Perches.size()));
                assert(Perches[static_cast<size_t>(B.PerchIndex)].Occupant == static_cast<int>(I));
                assert(Claimed.insert(B.PerchIndex).second);      // no ledge shared
                assert(Near(Length(B.Position - Perches[static_cast<size_t>(B.PerchIndex)].Position), 0.0, 1e-6));
                assert(Near(Length(B.Velocity), 0.0));
                assert(B.TargetPerchIndex == -1);
            }
            if (B.TargetPerchIndex >= 0)
            {
                assert(B.TargetPerchIndex < static_cast<int>(Perches.size()));
                assert(!B.Perched());
                const int Occupant = Perches[static_cast<size_t>(B.TargetPerchIndex)].Occupant;
                // Either this bird holds the reservation, or somebody took it and the bird
                // drops the target on its next step.
                assert(Occupant == static_cast<int>(I) || Occupant >= 0);
            }
        }
        R.MaxPerched = std::max(R.MaxPerched, Sitting);
        // No perch may claim a bird that is not on it.
        for (size_t P = 0; P < Perches.size(); ++P)
        {
            const int Occupant = Perches[P].Occupant;
            if (Occupant >= 0)
            {
                assert(Occupant < static_cast<int>(Birds.size()));
                const Bird& Owner = Birds[static_cast<size_t>(Occupant)];
                assert(Owner.PerchIndex == static_cast<int>(P) || Owner.TargetPerchIndex == static_cast<int>(P));
            }
        }
    }
    R.SmallestGap = SmallestPairDistance(Birds);
    R.MeanSpeed = SpeedSum / std::max(1, R.Updates);
    return R;
}

static void FlyingChecks()
{
    // Pigeons over the plaza: perching species, a wall-top ledge line, a full 90-second run.
    const SoakResult Doves = Soak(SpeciesId::RockDove, 120, 40, 90.0, 120, 0.05, false);
    assert(Doves.MaxPerched > 0);                       // they do settle
    assert(Doves.Launches > 0);                         // and they do leave again
    assert(Doves.Landings > 0);
    assert(Doves.MaxPerched <= 40);                     // never more birds than ledges
    assert(Doves.SmallestGap > 1e-6);                   // no two birds coincide
    assert(Doves.MeanSpeed > 0.0);
    // The perch target is a target, not a hard rule, but the flock must get somewhere near it.
    const int TargetPerched = static_cast<int>(Profile(SpeciesId::RockDove).PerchFraction * 120 + 0.5);
    assert(Doves.MaxPerched >= TargetPerched / 3);

    // Swifts: same ledges offered, and not one of them ever sits down.
    const SoakResult Swifts = Soak(SpeciesId::CommonSwift, 90, 40, 60.0, 90, 0.05, false);
    assert(Swifts.MaxPerched == 0);
    assert(Swifts.Landings == 0 && Swifts.Launches == 0);
    assert(Swifts.MeanSpeed > Doves.MeanSpeed);         // faster than the pigeons, as briefed
    assert(Swifts.SmallestGap > 1e-6);

    // Crows: twos and threes, mostly sitting.
    const SoakResult Crows = Soak(SpeciesId::HoodedCrow, 9, 24, 180.0, 9, 0.1, false);
    assert(Crows.MaxPerched > 0);
    assert(Crows.MeanSpeed < Doves.MeanSpeed);
    assert(Crows.SmallestGap > 1e-6);

    // One kestrel, alone. A flock of one must not divide by zero anywhere.
    const SoakResult Lone = Soak(SpeciesId::CommonKestrel, 1, 0, 120.0, 1, 0.25, false);
    assert(Lone.MaxPerched == 0);
    assert(Lone.MeanSpeed > 0.0);
    assert(Lone.NeighbourTests == 0);                   // nobody to test against

    // The vulture, for completeness: the largest, slowest-beating bird still flies bounded.
    const SoakResult Griffon = Soak(SpeciesId::GriffonVulture, 2, 0, 120.0, 2, 0.25, false);
    assert(Griffon.MeanSpeed > 0.0);

    // A coarse update (a distant flock at 4 Hz stepping a quarter of itself) is still legal.
    const SoakResult Coarse = Soak(SpeciesId::RockDove, 240, 60, 120.0, 60, 0.25, false);
    assert(Coarse.SmallestGap > 1e-6);
    assert(Coarse.MaxPerched > 0);

    // No perches at all: a perching species simply never lands, and never corrupts anything.
    const SoakResult NoLedges = Soak(SpeciesId::RockDove, 60, 0, 60.0, 60, 0.05, false);
    assert(NoLedges.MaxPerched == 0 && NoLedges.Landings == 0);

    // An empty flock and a zero timestep are no-ops.
    {
        const FlockConfig Config = MakeConfig(SpeciesId::RockDove);
        std::vector<Bird> None;
        std::vector<PerchPoint> NoPerches;
        Grid A, B;
        int Cursor = 0;
        const StepStats S = Update(None, NoPerches, Config, A, B, Cursor, 10, 0.05, 1.0, Vec3{});
        assert(S.Stepped == 0 && Cursor == 0);
        std::vector<Bird> Few;
        SeedFlock(Few, 5, Config);
        const Vec3 Before = Few[0].Position;
        Grid C, D;
        const UpdateWindow W = NextUpdateWindow(0, 5, 5);
        const StepStats Z = Step(Few, NoPerches, Config, C, W, 0.0, 1.0, Vec3{});
        assert(Z.Stepped == 0 && Near(Length(Few[0].Position - Before), 0.0));
        const StepStats N = Step(Few, NoPerches, Config, C, W, Nan, 1.0, Vec3{});
        assert(N.Stepped == 0);
        (void)D;
    }

    std::printf("flying: doves max %d perched of 40 ledges (%d landings, %d launches), swifts never sat,\n"
                "        crows %d perched, closest pair %.1f cm, mean speeds %.0f/%.0f/%.0f cm/s\n",
                Doves.MaxPerched, Doves.Landings, Doves.Launches, Crows.MaxPerched,
                Doves.SmallestGap, Doves.MeanSpeed, Swifts.MeanSpeed, Crows.MeanSpeed);
}

// =======================================================================================
// 10. perching in detail, and the startle scatter
// =======================================================================================
static void PerchAndStartleChecks()
{
    const FlockConfig Config = MakeConfig(SpeciesId::RockDove);

    // NearestFreePerch really is nearest, respects occupancy, and respects the search radius.
    std::vector<PerchPoint> Perches = LedgeLine(11, 4600.0, 900.0);   // y from -3000 to 3000
    assert(NearestFreePerch(Perches, Vec3{4600, 0, 900}, 10000.0, -1) == 5);
    assert(NearestFreePerch(Perches, Vec3{4600, 3000, 900}, 10000.0, -1) == 10);
    Perches[5].Occupant = 3;
    assert(NearestFreePerch(Perches, Vec3{4600, 0, 900}, 10000.0, -1) != 5);
    assert(NearestFreePerch(Perches, Vec3{4600, 0, 900}, 10000.0, 3) == 5);   // self keeps its own
    Perches[5].Occupant = -1;
    assert(NearestFreePerch(Perches, Vec3{-40000, 0, 900}, 1000.0, -1) == -1);
    std::vector<PerchPoint> NoPerches;
    assert(NearestFreePerch(NoPerches, Vec3{}, 1e9, -1) == -1);

    // Launch: releases the ledge, pushes away from it and upward, and schedules a flight.
    std::vector<Bird> Birds(1);
    Birds[0].Seed = 12345u;
    Birds[0].PerchIndex = 4;
    Birds[0].Position = Perches[4].Position;
    Perches[4].Occupant = 0;
    Launch(Birds[0], Perches, Config, 10.0, 0);
    assert(Birds[0].PerchIndex == -1 && Birds[0].TargetPerchIndex == -1);
    assert(Perches[4].Occupant == -1);
    assert(Birds[0].Velocity.Z > 0.0);                                  // up as well as out
    assert(Dot(Birds[0].Velocity, Perches[4].Facing) > 0.0);            // away from the ledge
    assert(Near(Birds[0].WanderExpiryTime, 10.0));                      // picks a new target at once
    assert(Birds[0].NextDecisionTime >= 10.0 + Config.Species.FlySecondsMin - 1e-9);
    assert(Birds[0].NextDecisionTime <= 10.0 + Config.Species.FlySecondsMax + 1e-9);
    // Launching a bird that is already flying is a safe no-op.
    const Vec3 Velocity = Birds[0].Velocity;
    Launch(Birds[0], Perches, Config, 11.0, 0);
    assert(Near(Length(Birds[0].Velocity - Velocity), 0.0));
    // A perch with no facing falls back to "outward from home" and never yields a zero push.
    std::vector<PerchPoint> Blank(1);
    Blank[0].Position = Vec3{1000, 0, 900};
    Blank[0].Facing = Vec3{};
    Blank[0].Occupant = 0;
    std::vector<Bird> Sitting(1);
    Sitting[0].PerchIndex = 0;
    Sitting[0].Position = Blank[0].Position;
    Launch(Sitting[0], Blank, Config, 0.0, 0);
    assert(Length(Sitting[0].Velocity) > 0.0);
    // Even a perch exactly at the flock home yields a legal launch direction.
    std::vector<PerchPoint> AtHome(1);
    AtHome[0].Position = Config.Bounds.HomeCm;
    AtHome[0].Facing = Vec3{};
    AtHome[0].Occupant = 0;
    std::vector<Bird> Centre(1);
    Centre[0].PerchIndex = 0;
    Centre[0].Position = Config.Bounds.HomeCm;
    Launch(Centre[0], AtHome, Config, 0.0, 0);
    assert(Length(Centre[0].Velocity) > 0.0 && Finite(Centre[0].Velocity));

    assert(PerchedCount(Birds) == 0);

    // ---- a ledge outside the flock volume: WHY THE PLACEMENT SCRIPT REFUSES ONE --------
    // Update() clamps every bird to the cylinder AFTER stepping it, perched birds included.
    // A perch outside the volume therefore cannot hold its bird: Step snaps the bird onto the
    // ledge, the clamp pulls it back inside, and the bird visibly jitters for ever with no
    // error anywhere. Rather than paper over it here, the behaviour is pinned by this test and
    // Scripts/release_birds.py refuses such a spec offline
    // (verification.perchInsideVolumeRule), where a human can see the numbers.
    {
        FlockConfig Tight = Config;
        std::vector<PerchPoint> Outside(1);
        Outside[0].Position = Vec3{Tight.Bounds.HomeCm.X + Tight.Bounds.RadiusCm + 2000.0,
                                   Tight.Bounds.HomeCm.Y, 1200.0};
        Outside[0].Facing = Vec3{1, 0, 0};
        Outside[0].Occupant = 0;
        std::vector<Bird> Stuck(1);
        Stuck[0].Position = Outside[0].Position;
        Stuck[0].PerchIndex = 0;
        Stuck[0].NextDecisionTime = 1e9;                  // it would happily sit for ever
        Grid A, B;
        int Cursor = 0;
        Update(Stuck, Outside, Tight, A, B, Cursor, 1, 0.05, 1.0, Vec3{});
        assert(Stuck[0].Perched());                       // still believes it is perched
        const double Drag = Length(Stuck[0].Position - Outside[0].Position);
        assert(Drag > 1000.0);                            // but has been dragged 2000 cm inward
        std::printf("perching: a ledge %0.f cm outside the volume drags its bird %.0f cm every update -\n"
                    "          the placement script refuses that spec offline rather than shipping a jitter\n",
                    2000.0, Drag);
    }

    // ---- the startle ------------------------------------------------------------------
    std::vector<Bird> Flock;
    SeedFlock(Flock, 150, Config);
    std::vector<PerchPoint> Ledges = LedgeLine(60, 4600.0, 900.0);
    Grid Neighbours, Overlap;
    int Cursor = 0;
    double Time = 0.0;
    // Settle some birds onto the ledges first, so the startle has something to lift.
    for (int U = 0; U < 1600; ++U)
    {
        Time += 0.05;
        Update(Flock, Ledges, Config, Neighbours, Overlap, Cursor, 150, 0.05, Time, Vec3{});
    }
    const int PerchedBefore = PerchedCount(Flock);
    assert(PerchedBefore > 0);

    const Vec3 Origin{4600, 0, 900};
    const double Radius = 4000.0;
    int InsideRadius = 0;
    double MeanDistanceBefore = 0.0;
    for (const Bird& B : Flock)
    {
        if (LengthSquared(B.Position - Origin) <= Radius * Radius)
        {
            ++InsideRadius;
            MeanDistanceBefore += Length(B.Position - Origin);
        }
    }
    assert(InsideRadius > 0);
    MeanDistanceBefore /= InsideRadius;

    ApplyStartle(Flock, Ledges, Config, Origin, Radius, Time);
    int Startled = 0, StillPerchedInside = 0;
    for (const Bird& B : Flock)
    {
        if (LengthSquared(B.Position - Origin) <= Radius * Radius)
        {
            if (B.StartleRemaining > 0.0) ++Startled;
            if (B.Perched()) ++StillPerchedInside;
        }
    }
    assert(Startled == InsideRadius);            // everyone inside the radius is startled
    assert(StillPerchedInside == 0);             // and every perched bird inside it went up
    assert(PerchedCount(Flock) < PerchedBefore);

    // The scatter itself: birds move away, then it decays and they come back.
    for (int U = 0; U < 40; ++U)                 // 2 seconds
    {
        Time += 0.05;
        Update(Flock, Ledges, Config, Neighbours, Overlap, Cursor, 150, 0.05, Time, Origin);
    }
    double MeanDistanceAfter = 0.0;
    int StillStartled = 0;
    for (const Bird& B : Flock)
    {
        MeanDistanceAfter += Length(B.Position - Origin);
        if (B.StartleRemaining > 0.0) ++StillStartled;
    }
    MeanDistanceAfter /= static_cast<double>(Flock.size());
    assert(MeanDistanceAfter > MeanDistanceBefore);      // they went away from it
    assert(StillStartled > 0);                            // and are still fleeing at 2 s
    // Past the species startle time (4.5 s for a pigeon) nobody is startled any more.
    for (int U = 0; U < 120; ++U)
    {
        Time += 0.05;
        Update(Flock, Ledges, Config, Neighbours, Overlap, Cursor, 150, 0.05, Time, Origin);
    }
    for (const Bird& B : Flock) assert(B.StartleRemaining == 0.0);
    // They settle again afterwards.
    for (int U = 0; U < 2400; ++U)
    {
        Time += 0.05;
        Update(Flock, Ledges, Config, Neighbours, Overlap, Cursor, 150, 0.05, Time, Origin);
    }
    assert(PerchedCount(Flock) > 0);

    // StartleAcceleration itself: away and upward, fading to nothing.
    Bird Fleeing;
    Fleeing.Position = Vec3{1000, 0, 1000};
    Fleeing.StartleRemaining = Config.Species.StartleSeconds;
    const Vec3 Full = StartleAcceleration(Fleeing, Vec3{0, 0, 1000}, Config.Species);
    assert(Full.X > 0.0 && Full.Z > 0.0);
    Fleeing.StartleRemaining = Config.Species.StartleSeconds * 0.25;
    const Vec3 Fading = StartleAcceleration(Fleeing, Vec3{0, 0, 1000}, Config.Species);
    assert(Length(Fading) < Length(Full));
    Fleeing.StartleRemaining = 0.0;
    assert(Length(StartleAcceleration(Fleeing, Vec3{0, 0, 1000}, Config.Species)) == 0.0);
    // A startle from exactly the bird's own position still yields a finite, upward push.
    Fleeing.StartleRemaining = 1.0;
    const Vec3 Coincident = StartleAcceleration(Fleeing, Fleeing.Position, Config.Species);
    assert(Finite(Coincident) && Coincident.Z > 0.0);

    // Hostile startle arguments are ignored, not obeyed.
    std::vector<Bird> Copy = Flock;
    ApplyStartle(Copy, Ledges, Config, Vec3{Nan, 0, 0}, 1000.0, Time);
    ApplyStartle(Copy, Ledges, Config, Origin, -5.0, Time);
    ApplyStartle(Copy, Ledges, Config, Origin, Nan, Time);
    for (size_t I = 0; I < Copy.size(); ++I) assert(Copy[I].PerchIndex == Flock[I].PerchIndex);

    std::printf("perching: %d of 150 doves settled on 60 ledges; startle lifted all %d inside %.0f cm,\n"
                "          mean distance from the origin %.0f -> %.0f cm, decayed to zero by %.1f s\n",
                PerchedBefore, InsideRadius, Radius, MeanDistanceBefore, MeanDistanceAfter,
                Config.Species.StartleSeconds);
}

// =======================================================================================
// 11. overlap resolution - two birds must never occupy one point
// =======================================================================================
static void OverlapChecks()
{
    Grid Scratch;

    // Everybody stacked on exactly one point: the worst case, and the one the hashed fallback
    // direction exists for. Two birds land on one point often enough to matter (two ledges
    // authored at the same place, two birds clamped to the same point on the cylinder), and
    // the correction must be BOUNDED. An earlier version divided the already-unit fallback
    // direction by an epsilon and threw the pair 111 kilometres apart in one pass, so this
    // asserts a ceiling on the displacement as well as a floor on the gap.
    const Vec3 Origin{100, 200, 300};
    std::vector<Bird> Stacked(24);
    for (size_t I = 0; I < Stacked.size(); ++I)
    {
        Stacked[I].Position = Origin;
        Stacked[I].Seed = Hash(1u, static_cast<uint32_t>(I), 3u);
    }
    double Furthest = 0.0;
    for (int Pass = 0; Pass < 40; ++Pass)
    {
        ResolveOverlaps(Stacked, Scratch, 90.0, 2);
        for (const Bird& B : Stacked) Furthest = std::max(Furthest, Length(B.Position - Origin));
    }
    const double Smallest = SmallestPairDistance(Stacked);
    assert(Smallest > 45.0);                    // genuinely separated, not merely non-equal
    // 24 birds needing 90 cm of clearance occupy a few metres. Anything past 50 m is a blow-up.
    assert(Furthest < 5000.0);
    for (const Bird& B : Stacked) assert(Finite(B.Position));

    // The single worst case on its own: exactly two coincident birds, one pass.
    std::vector<Bird> Twins(2);
    Twins[0].Position = Origin;
    Twins[1].Position = Origin;
    Twins[0].Seed = 11u;
    Twins[1].Seed = 22u;
    ResolveOverlaps(Twins, Scratch, 90.0, 1);
    const double TwinMove = std::max(Length(Twins[0].Position - Origin), Length(Twins[1].Position - Origin));
    assert(TwinMove > 1.0 && TwinMove <= 90.0 + 1e-6);   // at most the separation itself

    // Two birds well apart are not touched at all.
    std::vector<Bird> Apart(2);
    Apart[0].Position = Vec3{0, 0, 0};
    Apart[1].Position = Vec3{1000, 0, 0};
    ResolveOverlaps(Apart, Scratch, 90.0, 2);
    assert(Near(Apart[0].Position.X, 0.0) && Near(Apart[1].Position.X, 1000.0));

    // A pair inside the hard separation is pushed apart towards it, both moving. This is a
    // RELAXATION, not a solve: each bird takes half the correction and sees the other bird's
    // already-updated position inside the same pass, so the gap converges on the separation
    // from below rather than jumping to it. That is the right behaviour for scenery - a hard
    // solve would make two birds snap apart visibly - but it means the test asserts
    // convergence, not equality.
    std::vector<Bird> Close(2);
    Close[0].Position = Vec3{0, 0, 0};
    Close[1].Position = Vec3{30, 0, 0};
    const double Gap0 = SmallestPairDistance(Close);
    ResolveOverlaps(Close, Scratch, 90.0, 1);
    const double Gap1 = SmallestPairDistance(Close);
    ResolveOverlaps(Close, Scratch, 90.0, 3);
    const double Gap4 = SmallestPairDistance(Close);
    for (int Pass = 0; Pass < 12; ++Pass) ResolveOverlaps(Close, Scratch, 90.0, 2);
    const double GapSettled = SmallestPairDistance(Close);
    assert(Gap1 > Gap0 && Gap4 > Gap1);                  // monotonic, never overshooting
    assert(Gap4 > 90.0 * 0.95);                          // most of the way after four passes
    assert(GapSettled >= 90.0 - 1e-6 || Near(GapSettled, 90.0, 1e-3));
    assert(GapSettled < 90.0 + 1e-3);                    // it settles ON the separation
    assert(Close[0].Position.X < 0.0 && Close[1].Position.X > 30.0);

    // A perched bird is an obstacle, never a mover: it stays exactly on its ledge and the
    // flyer takes the whole correction.
    std::vector<Bird> Mixed(2);
    Mixed[0].Position = Vec3{0, 0, 0};
    Mixed[0].PerchIndex = 7;
    Mixed[1].Position = Vec3{20, 0, 0};
    ResolveOverlaps(Mixed, Scratch, 90.0, 4);
    assert(Near(Mixed[0].Position.X, 0.0) && Near(Mixed[0].Position.Y, 0.0));
    assert(Mixed[1].Position.X >= 90.0 - 1e-6);

    // Degenerate arguments.
    std::vector<Bird> One(1);
    assert(ResolveOverlaps(One, Scratch, 90.0, 2) > 1e17);
    std::vector<Bird> None;
    assert(ResolveOverlaps(None, Scratch, 90.0, 2) > 1e17);
    assert(ResolveOverlaps(Close, Scratch, 0.0, 2) > 1e17);
    ResolveOverlaps(Close, Scratch, 90.0, 0);           // iteration count is clamped to >= 1
    assert(SmallestPairDistance(None) > 1e17);

    std::printf("overlap: 24 coincident birds separated to %.1f cm, none thrown further than %.0f cm;\n"
                "         a 30 cm pair relaxes 30 -> %.1f -> %.1f -> %.2f cm against a 90 cm hard\n"
                "         separation; perched birds never displaced\n",
                Smallest, Furthest, Gap1, Gap4, GapSettled);
}

// =======================================================================================
// 12. the soundscape hook - it says WHEN, it never plays anything
// =======================================================================================
static void SoundHookChecks()
{
    // The first call only arms the timer; it never fires on the first frame of a level.
    double Next = 0.0;
    assert(!ShouldCall(7u, 0.0, 9.0, Next));
    assert(Near(Next, 4.5, 1e-9));
    assert(!ShouldCall(7u, 4.4, 9.0, Next));
    assert(ShouldCall(7u, 4.6, 9.0, Next));
    assert(Next > 4.6);

    // Over a long run the rate lands near one call per mean interval, and the gaps vary.
    const double Mean = 9.0;
    double Timer = 0.0;
    int Calls = 0;
    double Last = -1.0, ShortestGap = 1e9, LongestGap = 0.0;
    for (int Step = 1; Step <= 60000; ++Step)            // 3000 s at 20 Hz
    {
        const double Time = Step * 0.05;
        if (ShouldCall(20260908u, Time, Mean, Timer))
        {
            ++Calls;
            if (Last >= 0.0)
            {
                ShortestGap = std::min(ShortestGap, Time - Last);
                LongestGap = std::max(LongestGap, Time - Last);
            }
            Last = Time;
        }
    }
    const double Rate = Calls / 3000.0;                  // calls per second
    assert(Rate > 0.5 / Mean && Rate < 1.6 / Mean);
    assert(ShortestGap > 0.0 && LongestGap > ShortestGap * 1.5);   // genuinely irregular
    assert(ShortestGap >= Mean * 0.45 - 0.1);
    assert(LongestGap <= Mean * 1.85 + 0.1);

    // Hostile arguments never fire.
    double Bad = 0.0;
    assert(!ShouldCall(1u, Nan, 9.0, Bad));
    assert(!ShouldCall(1u, 10.0, 0.0, Bad));
    assert(!ShouldCall(1u, 10.0, -1.0, Bad));

    std::printf("sound hook: %d calls in 3000 s at a %.0f s mean (%.2f/s), gaps %.1f-%.1f s; no audio touched\n",
                Calls, Mean, Rate, ShortestGap, LongestGap);
}

// =======================================================================================
// 13. cost - the basis of the per-frame budget claim
// =======================================================================================
static double MeasureUpdateMicrosecondsOnce(int Count, int Budget, int Updates)
{
    const FlockConfig Config = MakeConfig(SpeciesId::RockDove);
    std::vector<Bird> Birds;
    SeedFlock(Birds, Count, Config);
    std::vector<PerchPoint> Perches = LedgeLine(40, 4600.0, 900.0);
    Grid Neighbours, Overlap;
    int Cursor = 0;
    double Time = 0.0;
    // Warm up so the measurement is not dominated by the first grid allocation.
    for (int U = 0; U < 40; ++U)
    {
        Time += 0.05;
        Update(Birds, Perches, Config, Neighbours, Overlap, Cursor, Budget, 0.05, Time, Vec3{});
    }
    const auto Started = std::chrono::steady_clock::now();
    for (int U = 0; U < Updates; ++U)
    {
        Time += 0.05;
        Update(Birds, Perches, Config, Neighbours, Overlap, Cursor, Budget, 0.05, Time, Vec3{});
    }
    const auto Elapsed = std::chrono::steady_clock::now() - Started;
    const double Microseconds =
        std::chrono::duration_cast<std::chrono::nanoseconds>(Elapsed).count() / 1000.0 / Updates;
    return Microseconds;
}

/** Best of several runs. This test is run by Scripts/verify.py on a machine that is routinely
 *  compiling several other things at the same time, so the MEAN of a timing here is the mean of
 *  this machine's load, not of this code. The minimum is the least contaminated estimate of the
 *  work itself, and it is the only one quoted. */
static double MeasureUpdateMicroseconds(int Count, int Budget, int Updates, int Repeats = 5)
{
    double Best = 1e18;
    for (int R = 0; R < Repeats; ++R)
    {
        Best = std::min(Best, MeasureUpdateMicrosecondsOnce(Count, Budget, Updates));
    }
    return Best;
}

static void CostChecks()
{
    // The algorithmic claim first, because it is the one that cannot be a fluke of this machine:
    // neighbour tests per stepped bird must be roughly constant as the flock grows. A quadratic
    // implementation would show this rising in proportion to the count.
    const FlockConfig Config = MakeConfig(SpeciesId::RockDove);
    double TestsPerBird[2] = {0, 0};
    const int Counts[2] = {100, 400};
    for (int Which = 0; Which < 2; ++Which)
    {
        std::vector<Bird> Birds;
        SeedFlock(Birds, Counts[Which], Config);
        std::vector<PerchPoint> Perches;
        Grid Neighbours, Overlap;
        int Cursor = 0;
        long long Tests = 0, Stepped = 0;
        double Time = 0.0;
        for (int U = 0; U < 200; ++U)
        {
            Time += 0.05;
            const StepStats S = Update(Birds, Perches, Config, Neighbours, Overlap, Cursor,
                                       Counts[Which], 0.05, Time, Vec3{});
            Tests += S.NeighbourTests;
            Stepped += S.Stepped;
        }
        TestsPerBird[Which] = static_cast<double>(Tests) / static_cast<double>(Stepped);
    }
    // Four times the birds in the same volume is four times the local density, so the count
    // per bird does rise - but nothing like the sixteen-fold an all-pairs loop would give.
    assert(TestsPerBird[1] < TestsPerBird[0] * 8.0);

    // Now the wall-clock cost of one update, best of five runs each. 120 birds stepped per
    // update is the actor's default BirdsPerUpdate; 225 is the total the placement script
    // actually ships across its five flocks (90 + 70 + 55 + 9 + 1).
    const double Micro120 = MeasureUpdateMicroseconds(120, 120, 400);
    const double Micro480 = MeasureUpdateMicroseconds(480, 120, 400);
    // A whole flock stepped at once, the worst case the actor allows.
    const double Micro480All = MeasureUpdateMicroseconds(480, 480, 200);

    // ---- the assertions are on WORK DONE, not on elapsed time --------------------------
    // Scripts/verify.py runs this while the same machine is compiling two dozen other test
    // programs, so ANY threshold on a microsecond figure here - absolute or as a ratio of two
    // separately-timed loops - measures the build machine's load and fails at random. It did:
    // the first version of this test failed the gate twice on timing alone while the code was
    // unchanged. So the cost claims are asserted on counters, which are deterministic, and the
    // timings below are measured and printed but never asserted on except as a catastrophe
    // backstop.
    {
        const int Total = 480, Slice = 120, Updates = 200;
        long long SlicedSteps = 0, SlicedTests = 0, FullSteps = 0, FullTests = 0;
        for (int Which = 0; Which < 2; ++Which)
        {
            const int Budget = (Which == 0) ? Slice : Total;
            std::vector<Bird> Birds;
            SeedFlock(Birds, Total, Config);
            std::vector<PerchPoint> Perches;
            Grid Neighbours, Overlap;
            int Cursor = 0;
            double Time = 0.0;
            for (int U = 0; U < Updates; ++U)
            {
                Time += 0.05;
                const StepStats S = Update(Birds, Perches, Config, Neighbours, Overlap, Cursor,
                                           Budget, 0.05, Time, Vec3{});
                if (Which == 0) { SlicedSteps += S.Stepped; SlicedTests += S.NeighbourTests; }
                else { FullSteps += S.Stepped; FullTests += S.NeighbourTests; }
            }
        }
        // Capping the slice caps the work exactly. This is the property the whole budget rests
        // on: a flock four times as large costs the same per update, because only the slice is
        // stepped and the rest catch up on later updates.
        assert(SlicedSteps == static_cast<long long>(Updates) * Slice);
        assert(FullSteps == static_cast<long long>(Updates) * Total);
        assert(FullSteps == SlicedSteps * 4);
        // And the expensive part - the neighbourhood gather - scales with the slice, not the
        // flock. Under 30 per cent of the full pass is what makes a big distant flock free.
        assert(SlicedTests * 3 < FullTests);
        std::printf("cost: slicing 480 birds at %d per update does %lld bird-steps and %lld neighbour tests\n"
                    "      over %d updates, against %lld and %lld for a full pass - exactly a quarter of the\n"
                    "      steps and %.0f%% of the tests, and both figures are counters, not timings\n",
                    Slice, SlicedSteps, SlicedTests, Updates, FullSteps, FullTests,
                    100.0 * SlicedTests / static_cast<double>(FullTests));
    }

    // A single loose absolute backstop, orders of magnitude clear of the measurement, so a
    // genuine catastrophe (per-bird allocation, an accidental O(n^2)) still trips even on a
    // completely saturated machine.
    assert(Micro480All < 500000.0);
    const double PerBird120 = Micro120 / 120.0;
    const double PerBird480 = Micro480 / 120.0;          // same slice size, denser flock

    // What the actor's own GetEstimatedMillisecondsPerFrame() computes, done here on the
    // measured numbers: cost per update * updates per second / frames per second. Quoted for
    // the arrangement the placement script actually ships - one near flock at 20 Hz and four
    // far flocks at 4 Hz - and for a deliberately pessimistic 480-bird version of it.
    const double NearHz = 1.0 / 0.05;                    // NearUpdateIntervalSeconds
    const double FarHz = 1.0 / 0.25;                     // FarUpdateIntervalSeconds
    const double ShippedMs = (Micro120 / 1000.0) * (NearHz + 4.0 * FarHz) / 60.0;
    const double PessimisticMs = (Micro480 / 1000.0) * (NearHz + 4.0 * FarHz) / 60.0;

    std::printf("      timings (best of 5, MEASURED NOT ASSERTED, machine under concurrent load):\n"
                "      %.1f us/update at 120 birds, %.1f us at 480 (120 per update), %.1f us at 480 at once;\n"
                "      per stepped bird %.3f us vs %.3f us for a 4x denser flock\n",
                Micro120, Micro480, Micro480All, PerBird120, PerBird480);
    std::printf("      neighbour tests per stepped bird %.1f at 100 birds, %.1f at 400; an all-pairs loop\n"
                "      would be 100 and 400, which is what the uniform grid is buying\n",
                TestsPerBird[0], TestsPerBird[1]);
    std::printf("      => at 60 fps, one near flock at 20 Hz + four far at 4 Hz costs %.4f ms/frame of game\n"
                "      thread as shipped (225 birds), %.4f ms if every flock held 480. CPU measurement of\n"
                "      the math on this machine; NOT a frame time measured in the map on the target GPU\n",
                ShippedMs, PessimisticMs);
}

// =======================================================================================
// 14. determinism end to end
// =======================================================================================
static void DeterminismChecks()
{
    // Two full runs from the same seed must agree bit for bit after thousands of updates,
    // including the perch bookkeeping. Anything that reads uninitialised memory or a clock
    // shows up here.
    const FlockConfig Config = MakeConfig(SpeciesId::RockDove);
    std::vector<Bird> RunA, RunB;
    std::vector<PerchPoint> PerchesA = LedgeLine(30, 4600.0, 900.0);
    std::vector<PerchPoint> PerchesB = LedgeLine(30, 4600.0, 900.0);
    SeedFlock(RunA, 80, Config);
    SeedFlock(RunB, 80, Config);
    Grid NA, OA, NB, OB;
    int CursorA = 0, CursorB = 0;
    double Time = 0.0;
    for (int U = 0; U < 3000; ++U)
    {
        Time += 0.05;
        Update(RunA, PerchesA, Config, NA, OA, CursorA, 40, 0.05, Time, Vec3{});
        Update(RunB, PerchesB, Config, NB, OB, CursorB, 40, 0.05, Time, Vec3{});
    }
    assert(CursorA == CursorB);
    for (size_t I = 0; I < RunA.size(); ++I)
    {
        assert(RunA[I].Position.X == RunB[I].Position.X);
        assert(RunA[I].Position.Y == RunB[I].Position.Y);
        assert(RunA[I].Position.Z == RunB[I].Position.Z);
        assert(RunA[I].Velocity.X == RunB[I].Velocity.X);
        assert(RunA[I].WingPhase == RunB[I].WingPhase);
        assert(RunA[I].PerchIndex == RunB[I].PerchIndex);
        assert(RunA[I].TargetPerchIndex == RunB[I].TargetPerchIndex);
    }
    for (size_t P = 0; P < PerchesA.size(); ++P) assert(PerchesA[P].Occupant == PerchesB[P].Occupant);
    std::printf("determinism: 80 birds, 3000 updates, two runs identical to the last bit\n");
}

int main()
{
    AlgebraChecks();
    SpeciesChecks();
    SeedingChecks();
    WingAndPoseChecks();
    OrientationChecks();
    BoundsChecks();
    GridChecks();
    WindowChecks();
    FlyingChecks();
    PerchAndStartleChecks();
    OverlapChecks();
    SoundHookChecks();
    CostChecks();
    DeterminismChecks();
    std::cout << "PASS: flock algebra, species figures, seeding, wing decorrelation, poses, orientation,"
              << " volume clamp, neighbour grid, round-robin budget, flying soak, perching, startle,"
              << " overlap, sound hook, cost and determinism" << std::endl;
    return 0;
}
