#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>

// ---------------------------------------------------------------------------------------
// Engine-independent ambient-bird flock math shared by AMikdashBirdFlock and the standalone
// test in Plugins/MikdashRuntime/Tests/FlockMathTest.cpp. Units: centimetres, seconds,
// degrees. No Unreal types; no allocation outside the caller's vectors.
//
// WHAT THIS IS: presentation behaviour for scenery birds - boids separation / alignment /
// cohesion, a wander target, a soft ceiling and floor, a wing phase that drives a pose-mesh
// index, perch/launch scheduling and a startle response. Deterministic given a seed.
//
// WHAT THIS IS NOT: an aerodynamic model, an ecological model, or a claim about how any real
// bird flies. Nothing here interacts with the player's white-dove pawn (AMikdashDovePawn);
// ambient birds carry no collision at all.
//
// Species figures (wingspan, body length) live in Profile() below with their citations; they
// are published field-guide ranges, not measurements taken by this project.
// ---------------------------------------------------------------------------------------
namespace MikdashFlock
{

// ------------------------------------------------------------------ small vector algebra
struct Vec3
{
    double X = 0, Y = 0, Z = 0;
};
inline Vec3 operator+(const Vec3& A, const Vec3& B) { return {A.X + B.X, A.Y + B.Y, A.Z + B.Z}; }
inline Vec3 operator-(const Vec3& A, const Vec3& B) { return {A.X - B.X, A.Y - B.Y, A.Z - B.Z}; }
inline Vec3 operator*(const Vec3& A, double S) { return {A.X * S, A.Y * S, A.Z * S}; }
inline Vec3& operator+=(Vec3& A, const Vec3& B) { A.X += B.X; A.Y += B.Y; A.Z += B.Z; return A; }
inline double Dot(const Vec3& A, const Vec3& B) { return A.X * B.X + A.Y * B.Y + A.Z * B.Z; }
inline double LengthSquared(const Vec3& A) { return Dot(A, A); }
inline double Length(const Vec3& A) { return std::sqrt(Dot(A, A)); }
inline bool Finite(const Vec3& A) { return std::isfinite(A.X) && std::isfinite(A.Y) && std::isfinite(A.Z); }
inline double Clamp(double V, double Lo, double Hi) { return std::max(Lo, std::min(Hi, V)); }
inline Vec3 Normalized(const Vec3& A)
{
    const double L = Length(A);
    return L > 1e-9 ? A * (1.0 / L) : Vec3{};
}
/** Rescale to at most MaxLength; zero-safe and NaN-safe. */
inline Vec3 Limit(const Vec3& A, double MaxLength)
{
    if (!Finite(A)) return Vec3{};
    const double L = Length(A);
    if (L <= MaxLength || L < 1e-9) return A;
    return A * (MaxLength / L);
}
constexpr double Pi = 3.14159265358979323846;
inline double DegToRad(double D) { return D * Pi / 180.0; }
inline double RadToDeg(double R) { return R * 180.0 / Pi; }
/** Fractional part in [0,1) for any finite input. */
inline double Frac01(double V)
{
    if (!std::isfinite(V)) return 0.0;
    const double F = std::fmod(V, 1.0);
    return F < 0.0 ? F + 1.0 : F;
}

// ---------------------------------------------------- deterministic hashing (no <random>)
/** 32-bit integer mix. Same inputs give the same value on every platform and every run, so a
 *  flock is reproducible from its seed alone and a receipt can quote its numbers. */
inline uint32_t Hash(uint32_t Seed, uint32_t A, uint32_t B)
{
    uint32_t H = Seed * 2654435761u + A * 2246822519u + B * 3266489917u + 668265263u;
    H ^= H >> 15; H *= 2246822519u;
    H ^= H >> 13; H *= 3266489917u;
    H ^= H >> 16;
    return H;
}
inline double HashUnit(uint32_t Seed, uint32_t A, uint32_t B)
{
    return Hash(Seed, A, B) * (1.0 / 4294967296.0);          // [0,1)
}
inline double HashRange(uint32_t Seed, uint32_t A, uint32_t B, double Lo, double Hi)
{
    return Lo + (Hi - Lo) * HashUnit(Seed, A, B);
}

// ---------------------------------------------------------------------------- the species
enum class SpeciesId : uint8_t
{
    RockDove = 0,        // Columba livia (feral pigeon)
    CommonSwift = 1,     // Apus apus
    HoodedCrow = 2,      // Corvus cornix
    CommonKestrel = 3,   // Falco tinnunculus
    GriffonVulture = 4,  // Gyps fulvus
};
inline int SpeciesCount() { return 5; }

/** Everything the simulation needs about one species. WingspanCm and BodyLengthCm are real
 *  published figures (citations in Profile()); the speeds, beat rates and weights are
 *  presentation values chosen so the bird READS correctly at the distance it is seen. */
struct SpeciesProfile
{
    double WingspanCm = 66.0;          ///< tip to tip, wings extended: drives the mesh scale
    double BodyLengthCm = 33.0;        ///< bill tip to tail tip

    double CruiseSpeedCmPerSecond = 1400.0;
    double MinSpeedCmPerSecond = 500.0;
    double MaxSpeedCmPerSecond = 2200.0;
    double MaxAccelCmPerSecond2 = 1400.0;

    double NeighbourRadiusCm = 900.0;
    double DesiredSeparationCm = 220.0;
    double HardSeparationCm = 90.0;    ///< enforced after integration; two birds never coincide

    double SeparationWeight = 1.7;
    double AlignmentWeight = 0.9;
    double CohesionWeight = 0.6;
    double WanderWeight = 0.8;
    double HomeWeight = 1.6;
    double DampingPerSecond = 0.35;    ///< first-order drag: bleeds overshoot so the flock settles

    double WingBeatHz = 5.2;
    double WingBeatSpread = 0.20;      ///< +-fraction of WingBeatHz, hashed per bird
    double GlideSpeedFraction = 1.10;  ///< > 1 disables gliding for this species
    double GlideDutyFraction = 0.0;    ///< fraction of a beat cycle held on the glide pose

    bool bPerches = true;
    double PerchFraction = 0.35;       ///< target fraction of the flock sitting at any moment
    double PerchSecondsMin = 12.0, PerchSecondsMax = 45.0;
    double FlySecondsMin = 18.0, FlySecondsMax = 60.0;
    double LandingRadiusCm = 140.0;
    double LaunchSpeedCmPerSecond = 700.0;

    double StartleSpeedMultiplier = 1.7;
    double StartleSeconds = 4.0;
    double StartleAccelCmPerSecond2 = 4000.0;

    double CallMeanIntervalSeconds = 9.0;   ///< soundscape hook only; no audio is played here
};

/** Species figures. WINGSPAN AND BODY LENGTH ARE PUBLISHED FIELD-GUIDE RANGES taken at the
 *  mid-point; this project measured nothing itself. Citations:
 *
 *   Rock dove / feral pigeon, Columba livia
 *       length 30-35 cm, wingspan 62-72 cm  -- Svensson, Mullarney & Zetterstrom, Collins
 *       Bird Guide 2nd ed. (2009), Columba livia; same range in Cramp (ed.), Birds of the
 *       Western Palearctic vol. IV. Used: 33 cm / 67 cm.
 *       Jerusalem: abundant resident, nests in wall crevices; the classic bird of the plaza
 *       and of the Kotel's stone courses and its caper growth.
 *
 *   Common swift, Apus apus
 *       length 16-17 cm, wingspan 42-48 cm  -- Collins Bird Guide 2nd ed., Apus apus.
 *       Used: 16.5 cm / 45 cm. Jerusalem: a spring / early-summer breeding visitor, roughly
 *       late February to early July, nesting in crevices of the Old City walls INCLUDING the
 *       Western Wall; the screaming low parties round the walls at dusk are this bird.
 *
 *   Hooded crow, Corvus cornix
 *       length 45-47 cm, wingspan 93-104 cm -- Collins Bird Guide 2nd ed., Corvus cornix.
 *       Used: 46 cm / 98 cm. Jerusalem: abundant urban resident, in ones twos and threes on
 *       parapets, roofs and aerials rather than in wheeling flocks.
 *
 *   Common kestrel, Falco tinnunculus
 *       length 32-35 cm, wingspan 71-80 cm  -- Collins Bird Guide 2nd ed., Falco tinnunculus.
 *       Used: 33 cm / 75 cm. Jerusalem: resident; breeds on tall buildings and on cliff and
 *       wall ledges, hangs and hovers over open ground.
 *
 *   Griffon vulture, Gyps fulvus
 *       length 95-110 cm, wingspan 240-280 cm -- Collins Bird Guide 2nd ed., Gyps fulvus.
 *       Used: 102 cm / 260 cm. PROVIDED BUT NOT PLACED BY DEFAULT: the Israeli griffon is now
 *       a Judean Desert / Golan / Negev bird and is not a routine sight over the city, so a
 *       griffon over the Mount would be a scale prop, not a Jerusalem observation.
 *       Scripts/release_birds.py places the kestrel instead and records that reason. */
inline SpeciesProfile Profile(SpeciesId Species)
{
    SpeciesProfile P;
    switch (Species)
    {
    case SpeciesId::RockDove:
        P.WingspanCm = 67.0; P.BodyLengthCm = 33.0;
        P.CruiseSpeedCmPerSecond = 1500.0; P.MinSpeedCmPerSecond = 600.0; P.MaxSpeedCmPerSecond = 2400.0;
        P.MaxAccelCmPerSecond2 = 1600.0;
        P.NeighbourRadiusCm = 900.0; P.DesiredSeparationCm = 220.0; P.HardSeparationCm = 90.0;
        P.SeparationWeight = 1.7; P.AlignmentWeight = 1.0; P.CohesionWeight = 0.85; P.WanderWeight = 0.7;
        P.HomeWeight = 1.6; P.DampingPerSecond = 0.35;
        P.WingBeatHz = 5.4; P.WingBeatSpread = 0.22; P.GlideSpeedFraction = 0.92; P.GlideDutyFraction = 0.18;
        P.bPerches = true; P.PerchFraction = 0.40;
        P.PerchSecondsMin = 14.0; P.PerchSecondsMax = 55.0;
        P.FlySecondsMin = 20.0; P.FlySecondsMax = 70.0;
        P.LandingRadiusCm = 140.0; P.LaunchSpeedCmPerSecond = 700.0;
        P.StartleSpeedMultiplier = 1.8; P.StartleSeconds = 4.5;
        P.CallMeanIntervalSeconds = 11.0;
        break;
    case SpeciesId::CommonSwift:
        P.WingspanCm = 45.0; P.BodyLengthCm = 16.5;
        P.CruiseSpeedCmPerSecond = 3000.0; P.MinSpeedCmPerSecond = 1800.0; P.MaxSpeedCmPerSecond = 4200.0;
        P.MaxAccelCmPerSecond2 = 5200.0;                  // the tight, snapping turns
        P.NeighbourRadiusCm = 1600.0; P.DesiredSeparationCm = 500.0; P.HardSeparationCm = 130.0;
        P.SeparationWeight = 1.5; P.AlignmentWeight = 0.55; P.CohesionWeight = 0.35; P.WanderWeight = 1.9;
        P.HomeWeight = 1.8; P.DampingPerSecond = 0.12;     // loose: swifts scythe, they do not queue
        P.WingBeatHz = 8.5; P.WingBeatSpread = 0.26; P.GlideSpeedFraction = 0.78; P.GlideDutyFraction = 0.45;
        P.bPerches = false;                                // a swift on the ground is a swift in trouble
        P.PerchFraction = 0.0;
        P.StartleSpeedMultiplier = 1.25; P.StartleSeconds = 2.0;
        P.CallMeanIntervalSeconds = 4.0;                   // the screaming parties
        break;
    case SpeciesId::HoodedCrow:
        P.WingspanCm = 98.0; P.BodyLengthCm = 46.0;
        P.CruiseSpeedCmPerSecond = 1100.0; P.MinSpeedCmPerSecond = 500.0; P.MaxSpeedCmPerSecond = 1700.0;
        P.MaxAccelCmPerSecond2 = 900.0;
        P.NeighbourRadiusCm = 2500.0; P.DesiredSeparationCm = 900.0; P.HardSeparationCm = 220.0;
        P.SeparationWeight = 1.9; P.AlignmentWeight = 0.4; P.CohesionWeight = 0.25; P.WanderWeight = 1.2;
        P.HomeWeight = 1.6; P.DampingPerSecond = 0.45;
        P.WingBeatHz = 3.4; P.WingBeatSpread = 0.24; P.GlideSpeedFraction = 0.85; P.GlideDutyFraction = 0.22;
        P.bPerches = true; P.PerchFraction = 0.55;         // mostly sitting on something
        P.PerchSecondsMin = 25.0; P.PerchSecondsMax = 110.0;
        P.FlySecondsMin = 14.0; P.FlySecondsMax = 45.0;
        P.LandingRadiusCm = 200.0; P.LaunchSpeedCmPerSecond = 550.0;
        P.StartleSpeedMultiplier = 1.5; P.StartleSeconds = 6.0;
        P.CallMeanIntervalSeconds = 7.0;
        break;
    case SpeciesId::CommonKestrel:
        P.WingspanCm = 75.0; P.BodyLengthCm = 33.0;
        P.CruiseSpeedCmPerSecond = 900.0; P.MinSpeedCmPerSecond = 120.0; P.MaxSpeedCmPerSecond = 1800.0;
        P.MaxAccelCmPerSecond2 = 700.0;
        P.NeighbourRadiusCm = 6000.0; P.DesiredSeparationCm = 4000.0; P.HardSeparationCm = 600.0;
        P.SeparationWeight = 2.0; P.AlignmentWeight = 0.0; P.CohesionWeight = 0.0; P.WanderWeight = 1.0;
        P.HomeWeight = 1.2; P.DampingPerSecond = 0.55;     // a lone bird holding a thermal
        P.WingBeatHz = 4.6; P.WingBeatSpread = 0.15; P.GlideSpeedFraction = 0.45; P.GlideDutyFraction = 0.65;
        P.bPerches = false;
        P.PerchFraction = 0.0;
        P.StartleSpeedMultiplier = 1.2; P.StartleSeconds = 3.0;
        P.CallMeanIntervalSeconds = 25.0;
        break;
    case SpeciesId::GriffonVulture:
        P.WingspanCm = 260.0; P.BodyLengthCm = 102.0;
        P.CruiseSpeedCmPerSecond = 1200.0; P.MinSpeedCmPerSecond = 700.0; P.MaxSpeedCmPerSecond = 2000.0;
        P.MaxAccelCmPerSecond2 = 350.0;
        P.NeighbourRadiusCm = 9000.0; P.DesiredSeparationCm = 5000.0; P.HardSeparationCm = 1200.0;
        P.SeparationWeight = 2.0; P.AlignmentWeight = 0.2; P.CohesionWeight = 0.1; P.WanderWeight = 0.7;
        P.HomeWeight = 1.1; P.DampingPerSecond = 0.6;
        P.WingBeatHz = 1.9; P.WingBeatSpread = 0.12; P.GlideSpeedFraction = 0.25; P.GlideDutyFraction = 0.88;
        P.bPerches = false;
        P.PerchFraction = 0.0;
        P.StartleSpeedMultiplier = 1.1; P.StartleSeconds = 3.0;
        P.CallMeanIntervalSeconds = 120.0;
        break;
    }
    return P;
}

// --------------------------------------------------------------------------- flock volume
/** A vertical cylinder round a home point, with a soft band inside the ceiling, the floor and
 *  the rim where the bird is steered back, and a hard clamp at the surfaces themselves. */
struct FlockBounds
{
    Vec3 HomeCm;
    double RadiusCm = 4000.0;
    double FloorZCm = 0.0;
    double CeilingZCm = 3000.0;
    double SoftBandCm = 500.0;         ///< steer-back band thickness at floor and ceiling
    double RadialSoftBandCm = 800.0;
};
inline double BoundedFloorZ(const FlockBounds& B) { return std::min(B.FloorZCm, B.CeilingZCm); }
inline double BoundedCeilingZ(const FlockBounds& B) { return std::max(B.FloorZCm, B.CeilingZCm); }

// -------------------------------------------------------------------------------- the bird
struct Bird
{
    Vec3 Position;
    Vec3 Velocity;
    Vec3 WanderTargetCm;
    double WanderExpiryTime = 0.0;
    double WingPhase = 0.0;            ///< [0,1); 0 is the top of the upstroke
    double WingHz = 5.0;
    double NextDecisionTime = 0.0;     ///< when to try to perch, or to leave the perch
    double StartleRemaining = 0.0;
    int PerchIndex = -1;               ///< >= 0: sitting on that perch
    int TargetPerchIndex = -1;         ///< >= 0: flying in to land on that perch
    uint32_t Seed = 0;
    bool Perched() const { return PerchIndex >= 0; }
};

/** A named ledge. Facing is the direction the sitting bird looks (unit; zero means "outward
 *  from the flock home"). Occupant is the bird index, or -1 when free. */
struct PerchPoint
{
    Vec3 Position;
    Vec3 Facing;
    int Occupant = -1;
};

// ------------------------------------------------------------------------ wing phase / pose
/** Pose meshes generated by Scripts/create_birds.py, in this exact order. The actor keeps one
 *  HISM component per pose; the index selects which one carries the bird this update. */
enum PoseIndex : int
{
    Pose_UpStroke = 0,   ///< wings raised above the back
    Pose_Level = 1,      ///< wings extended level: also the glide and the soar pose
    Pose_DownStroke = 2, ///< wings swept down below the body
    Pose_Perched = 3,    ///< wings folded, legs down
    PoseCount = 4,
};

/** Advance one bird's wing phase; returns the new phase in [0,1).
 *  The per-bird WingHz set by SeedFlock from a hash is what decorrelates the flock: with a
 *  +-20 per cent spread, phases started in lockstep spread out within about ten seconds,
 *  which is what PhaseCoherence() measures in the test. */
inline double AdvanceWing(Bird& B, double Dt)
{
    if (!std::isfinite(Dt) || Dt <= 0.0) return B.WingPhase;
    const double Hz = std::isfinite(B.WingHz) ? Clamp(B.WingHz, 0.1, 40.0) : 1.0;
    B.WingPhase = Frac01(B.WingPhase + Hz * Clamp(Dt, 0.0, 0.5));
    return B.WingPhase;
}

/** True when this bird is fast enough (relative to its species maximum) to hold its wings out.
 *  A swift or a kestrel spends most of its time here; a pigeon almost never does. The glide is
 *  held for GlideDutyFraction of each beat cycle, so a fast bird still flickers a beat in
 *  rather than freezing on one mesh. */
inline bool IsGliding(const SpeciesProfile& P, const Bird& B)
{
    if (B.Perched() || P.GlideSpeedFraction > 1.0) return false;
    const double Speed = Length(B.Velocity);
    if (!std::isfinite(Speed) || P.MaxSpeedCmPerSecond <= 1e-6) return false;
    if (Speed < P.GlideSpeedFraction * P.MaxSpeedCmPerSecond) return false;
    return Frac01(B.WingPhase) < P.GlideDutyFraction;
}

/** Pose mesh index for a phase. */
inline int WingPoseIndex(double Phase, bool bGliding, bool bPerched)
{
    if (bPerched) return Pose_Perched;
    if (bGliding) return Pose_Level;
    const double F = Frac01(Phase);
    if (F < 0.25) return Pose_UpStroke;
    if (F < 0.50) return Pose_Level;
    if (F < 0.75) return Pose_DownStroke;
    return Pose_Level;
}
inline int PoseFor(const SpeciesProfile& P, const Bird& B)
{
    return WingPoseIndex(B.WingPhase, IsGliding(P, B), B.Perched());
}

/** Circular resultant length of the flock's wing phases, in [0,1]. 1 = perfect lockstep,
 *  0 = uniformly spread. The test requires this to fall from 1 to well under 0.35. */
inline double PhaseCoherence(const std::vector<Bird>& Birds)
{
    if (Birds.empty()) return 0.0;
    double Cx = 0.0, Cy = 0.0;
    for (const Bird& B : Birds)
    {
        const double A = 2.0 * Pi * Frac01(B.WingPhase);
        Cx += std::cos(A); Cy += std::sin(A);
    }
    const double N = static_cast<double>(Birds.size());
    return std::sqrt(Cx * Cx + Cy * Cy) / N;
}

// --------------------------------------------------------------------- body orientation
/** Heading in degrees (0 = +X), a pitch from the climb rate, and a bank from the turn. */
inline double YawDegrees(const Vec3& Velocity)
{
    if (std::abs(Velocity.X) < 1e-9 && std::abs(Velocity.Y) < 1e-9) return 0.0;
    return RadToDeg(std::atan2(Velocity.Y, Velocity.X));
}
inline double PitchDegrees(const Vec3& Velocity)
{
    const double S = Length(Velocity);
    if (S < 1e-6) return 0.0;
    return Clamp(RadToDeg(std::asin(Clamp(Velocity.Z / S, -1.0, 1.0))) * 0.7, -35.0, 35.0);
}
inline double RollDegrees(const Vec3& Velocity, const Vec3& Acceleration, double MaxBankDegrees = 45.0)
{
    const double S = Length(Velocity);
    if (S < 1e-6 || !Finite(Acceleration)) return 0.0;
    const Vec3 Forward = Velocity * (1.0 / S);
    const Vec3 Right = Normalized(Vec3{Forward.Y, -Forward.X, 0.0});
    if (Length(Right) < 1e-6) return 0.0;
    const double Lateral = Dot(Acceleration, Right);
    return Clamp(-Lateral / 900.0 * MaxBankDegrees, -MaxBankDegrees, MaxBankDegrees);
}

// ------------------------------------------------------------------- uniform neighbour grid
/** Counting-sort bucket grid. Built once per flock update in O(n); a neighbour query touches
 *  27 cells. This is what keeps an update linear instead of quadratic, and it is the basis of
 *  the per-frame cost figure recorded in SourceAssets/birds-review/. */
struct Grid
{
    double CellCm = 500.0;
    int Nx = 1, Ny = 1, Nz = 1;
    Vec3 Origin;
    std::vector<int> CellStart;   // size Nx*Ny*Nz + 1
    std::vector<int> Items;       // size = number of birds
    std::vector<int> Counter;     // scratch, size Nx*Ny*Nz + 1

    int CellIndex(int Ix, int Iy, int Iz) const { return (Iz * Ny + Iy) * Nx + Ix; }
    void Coords(const Vec3& P, int& Ix, int& Iy, int& Iz) const
    {
        Ix = static_cast<int>(Clamp(std::floor((P.X - Origin.X) / CellCm), 0.0, static_cast<double>(Nx - 1)));
        Iy = static_cast<int>(Clamp(std::floor((P.Y - Origin.Y) / CellCm), 0.0, static_cast<double>(Ny - 1)));
        Iz = static_cast<int>(Clamp(std::floor((P.Z - Origin.Z) / CellCm), 0.0, static_cast<double>(Nz - 1)));
    }

    void Build(const std::vector<Bird>& Birds, double InCellCm)
    {
        CellCm = std::max(50.0, std::isfinite(InCellCm) ? InCellCm : 500.0);
        Vec3 Lo{1e18, 1e18, 1e18}, Hi{-1e18, -1e18, -1e18};
        bool bAny = false;
        for (const Bird& B : Birds)
        {
            if (!Finite(B.Position)) continue;
            bAny = true;
            Lo.X = std::min(Lo.X, B.Position.X); Hi.X = std::max(Hi.X, B.Position.X);
            Lo.Y = std::min(Lo.Y, B.Position.Y); Hi.Y = std::max(Hi.Y, B.Position.Y);
            Lo.Z = std::min(Lo.Z, B.Position.Z); Hi.Z = std::max(Hi.Z, B.Position.Z);
        }
        if (!bAny) { Lo = Vec3{}; Hi = Vec3{}; }
        Origin = Lo - Vec3{CellCm, CellCm, CellCm};
        const double Span = 2.0 * CellCm;
        Nx = std::max(1, std::min(256, static_cast<int>((Hi.X - Lo.X + Span) / CellCm) + 1));
        Ny = std::max(1, std::min(256, static_cast<int>((Hi.Y - Lo.Y + Span) / CellCm) + 1));
        Nz = std::max(1, std::min(64, static_cast<int>((Hi.Z - Lo.Z + Span) / CellCm) + 1));

        const size_t Cells = static_cast<size_t>(Nx) * static_cast<size_t>(Ny) * static_cast<size_t>(Nz);
        Counter.assign(Cells + 1, 0);
        for (const Bird& B : Birds)
        {
            int Ix, Iy, Iz; Coords(B.Position, Ix, Iy, Iz);
            ++Counter[static_cast<size_t>(CellIndex(Ix, Iy, Iz)) + 1];
        }
        for (size_t I = 1; I <= Cells; ++I) Counter[I] += Counter[I - 1];
        CellStart = Counter;
        Items.assign(Birds.size(), 0);
        for (size_t I = 0; I < Birds.size(); ++I)
        {
            int Ix, Iy, Iz; Coords(Birds[I].Position, Ix, Iy, Iz);
            Items[static_cast<size_t>(Counter[static_cast<size_t>(CellIndex(Ix, Iy, Iz))]++)] = static_cast<int>(I);
        }
    }

    /** Calls Visit(int OtherIndex) for every bird in the 27 cells around P. */
    template <class F>
    void ForEachNear(const Vec3& P, F&& Visit) const
    {
        if (CellStart.empty() || !Finite(P)) return;
        int Cx, Cy, Cz; Coords(P, Cx, Cy, Cz);
        for (int Iz = std::max(0, Cz - 1); Iz <= std::min(Nz - 1, Cz + 1); ++Iz)
            for (int Iy = std::max(0, Cy - 1); Iy <= std::min(Ny - 1, Cy + 1); ++Iy)
                for (int Ix = std::max(0, Cx - 1); Ix <= std::min(Nx - 1, Cx + 1); ++Ix)
                {
                    const size_t C = static_cast<size_t>(CellIndex(Ix, Iy, Iz));
                    for (int K = CellStart[C]; K < CellStart[C + 1]; ++K) Visit(Items[static_cast<size_t>(K)]);
                }
    }
};

// ----------------------------------------------------------------------------- the flock
struct FlockConfig
{
    SpeciesProfile Species;
    FlockBounds Bounds;
    uint32_t Seed = 20260908u;
};

/** A round-robin slice of the flock, so a big flock costs a fixed amount per update. */
struct UpdateWindow
{
    int Start = 0, Count = 0, NextCursor = 0;
};
inline UpdateWindow NextUpdateWindow(int Cursor, int Total, int Budget)
{
    UpdateWindow W;
    if (Total <= 0) return W;
    if (Budget <= 0 || Budget >= Total) { W.Count = Total; W.NextCursor = 0; return W; }
    W.Start = ((Cursor % Total) + Total) % Total;
    W.Count = Budget;
    W.NextCursor = (W.Start + Budget) % Total;
    return W;
}
/** Seconds of simulated time one bird owes when only Budget of Total are stepped per update. */
inline double CatchUpSeconds(double UpdateInterval, int Total, int Budget)
{
    if (!std::isfinite(UpdateInterval) || UpdateInterval <= 0 || Total <= 0) return 0.0;
    if (Budget <= 0 || Budget >= Total) return Clamp(UpdateInterval, 0.0, 0.5);
    return Clamp(UpdateInterval * static_cast<double>(Total) / static_cast<double>(Budget), 0.0, 0.5);
}

/** A reproducible point inside the flock cylinder. */
inline Vec3 PointInBounds(const FlockBounds& B, uint32_t Seed, uint32_t A, uint32_t Salt)
{
    const double Angle = HashRange(Seed, A, Salt, 0.0, 2.0 * Pi);
    // sqrt keeps the sample area-uniform instead of clustering at the centre.
    const double R = std::sqrt(HashUnit(Seed, A, Salt + 1u)) * std::max(0.0, B.RadiusCm) * 0.94;
    const double Lo = BoundedFloorZ(B), Hi = BoundedCeilingZ(B);
    const double Z = HashRange(Seed, A, Salt + 2u, Lo + 0.12 * (Hi - Lo), Hi - 0.12 * (Hi - Lo));
    return Vec3{B.HomeCm.X + R * std::cos(Angle), B.HomeCm.Y + R * std::sin(Angle), Z};
}

/** Deterministically fill a flock. Wing phases all start at zero on purpose: the decorrelation
 *  test then measures the mechanism (the hashed per-bird WingHz) rather than the seeding. */
inline void SeedFlock(std::vector<Bird>& Birds, int Count, const FlockConfig& Config)
{
    Birds.clear();
    if (Count <= 0) return;
    Birds.resize(static_cast<size_t>(Count));
    const SpeciesProfile& P = Config.Species;
    for (int I = 0; I < Count; ++I)
    {
        Bird& B = Birds[static_cast<size_t>(I)];
        const uint32_t Index = static_cast<uint32_t>(I);
        B.Seed = Hash(Config.Seed, Index, 7u);
        B.Position = PointInBounds(Config.Bounds, Config.Seed, Index, 100u);
        const double Heading = HashRange(Config.Seed, Index, 200u, 0.0, 2.0 * Pi);
        const double Speed = HashRange(Config.Seed, Index, 201u, 0.6, 1.0) * P.CruiseSpeedCmPerSecond;
        B.Velocity = Vec3{std::cos(Heading) * Speed, std::sin(Heading) * Speed,
                          HashRange(Config.Seed, Index, 202u, -0.1, 0.1) * Speed};
        B.WingPhase = 0.0;
        B.WingHz = P.WingBeatHz * (1.0 + P.WingBeatSpread * HashRange(Config.Seed, Index, 203u, -1.0, 1.0));
        B.WanderTargetCm = PointInBounds(Config.Bounds, Config.Seed, Index, 300u);
        B.WanderExpiryTime = HashRange(Config.Seed, Index, 204u, 2.0, 12.0);
        B.NextDecisionTime = HashRange(Config.Seed, Index, 205u, P.FlySecondsMin * 0.2, P.FlySecondsMax);
        B.PerchIndex = -1;
        B.TargetPerchIndex = -1;
        B.StartleRemaining = 0.0;
    }
}

/** Vertical acceleration that keeps a bird inside the soft band. Positive is up. */
inline double AltitudeAcceleration(const Vec3& Position, const Vec3& Velocity, const FlockBounds& B, double MaxAccel)
{
    const double Lo = BoundedFloorZ(B), Hi = BoundedCeilingZ(B);
    const double Band = std::max(1.0, std::min(B.SoftBandCm, (Hi - Lo) * 0.45));
    double A = 0.0;
    if (Position.Z < Lo + Band) A += MaxAccel * Clamp((Lo + Band - Position.Z) / Band, 0.0, 1.0);
    if (Position.Z > Hi - Band) A -= MaxAccel * Clamp((Position.Z - (Hi - Band)) / Band, 0.0, 1.0);
    // Bleed the vertical speed driving the bird at the surface, so it turns away rather than
    // bouncing: this is what stops the ceiling becoming a trampoline.
    if (A > 0.0 && Velocity.Z < 0.0) A -= Velocity.Z * 0.9;
    if (A < 0.0 && Velocity.Z > 0.0) A -= Velocity.Z * 0.9;
    return A;
}

/** Horizontal acceleration that keeps a bird inside the cylinder. */
inline Vec3 RadialAcceleration(const Vec3& Position, const FlockBounds& B, double MaxAccel)
{
    const Vec3 Offset{Position.X - B.HomeCm.X, Position.Y - B.HomeCm.Y, 0.0};
    const double R = Length(Offset);
    const double Band = std::max(1.0, std::min(B.RadialSoftBandCm, B.RadiusCm * 0.5));
    if (R < B.RadiusCm - Band || R < 1e-6) return Vec3{};
    const double T = Clamp((R - (B.RadiusCm - Band)) / Band, 0.0, 1.0);
    return Offset * (-MaxAccel * T / R);
}

/** Hard clamp: afterwards the bird is inside the cylinder and between floor and ceiling,
 *  whatever the integration did. Velocity into a surface is removed, not reflected. */
inline void ClampToBounds(Bird& B, const FlockBounds& Bounds)
{
    if (!Finite(B.Position)) B.Position = Bounds.HomeCm;
    if (!Finite(B.Velocity)) B.Velocity = Vec3{};
    const double Lo = BoundedFloorZ(Bounds), Hi = BoundedCeilingZ(Bounds);
    if (B.Position.Z < Lo) { B.Position.Z = Lo; if (B.Velocity.Z < 0) B.Velocity.Z = 0; }
    if (B.Position.Z > Hi) { B.Position.Z = Hi; if (B.Velocity.Z > 0) B.Velocity.Z = 0; }
    Vec3 Offset{B.Position.X - Bounds.HomeCm.X, B.Position.Y - Bounds.HomeCm.Y, 0.0};
    const double R = Length(Offset);
    if (R > Bounds.RadiusCm && R > 1e-9)
    {
        const Vec3 Dir = Offset * (1.0 / R);
        B.Position.X = Bounds.HomeCm.X + Dir.X * Bounds.RadiusCm;
        B.Position.Y = Bounds.HomeCm.Y + Dir.Y * Bounds.RadiusCm;
        const double Outward = B.Velocity.X * Dir.X + B.Velocity.Y * Dir.Y;
        if (Outward > 0) { B.Velocity.X -= Dir.X * Outward; B.Velocity.Y -= Dir.Y * Outward; }
    }
}

// ------------------------------------------------------------------------ perch scheduling
/** Release a bird from its perch with a launch impulse away from the ledge and upward. */
inline void Launch(Bird& B, std::vector<PerchPoint>& Perches, const FlockConfig& Config, double Time, int BirdIndex)
{
    const SpeciesProfile& P = Config.Species;
    if (B.PerchIndex >= 0 && B.PerchIndex < static_cast<int>(Perches.size()))
    {
        PerchPoint& Perch = Perches[static_cast<size_t>(B.PerchIndex)];
        if (Perch.Occupant == BirdIndex) Perch.Occupant = -1;
        Vec3 Away = Length(Perch.Facing) > 1e-6
                        ? Normalized(Perch.Facing)
                        : Normalized(Vec3{B.Position.X - Config.Bounds.HomeCm.X,
                                          B.Position.Y - Config.Bounds.HomeCm.Y, 0.0});
        if (Length(Away) < 1e-6) Away = Vec3{1, 0, 0};
        B.Velocity = Away * P.LaunchSpeedCmPerSecond + Vec3{0, 0, P.LaunchSpeedCmPerSecond * 0.6};
    }
    if (B.TargetPerchIndex >= 0 && B.TargetPerchIndex < static_cast<int>(Perches.size()))
    {
        PerchPoint& Reserved = Perches[static_cast<size_t>(B.TargetPerchIndex)];
        if (Reserved.Occupant == BirdIndex) Reserved.Occupant = -1;
    }
    B.PerchIndex = -1;
    B.TargetPerchIndex = -1;
    B.WanderExpiryTime = Time;   // pick a fresh target immediately
    B.NextDecisionTime = Time + HashRange(B.Seed, static_cast<uint32_t>(BirdIndex), 401u,
                                          P.FlySecondsMin, P.FlySecondsMax);
}

/** Nearest unoccupied perch within SearchRadiusCm, or -1. */
inline int NearestFreePerch(const std::vector<PerchPoint>& Perches, const Vec3& From, double SearchRadiusCm, int SelfIndex)
{
    int Best = -1;
    double BestDistanceSquared = SearchRadiusCm * SearchRadiusCm;
    for (size_t I = 0; I < Perches.size(); ++I)
    {
        const PerchPoint& Perch = Perches[I];
        if (Perch.Occupant >= 0 && Perch.Occupant != SelfIndex) continue;
        const double D = LengthSquared(Perch.Position - From);
        if (D < BestDistanceSquared) { BestDistanceSquared = D; Best = static_cast<int>(I); }
    }
    return Best;
}

/** How many of the flock are sitting right now. */
inline int PerchedCount(const std::vector<Bird>& Birds)
{
    int N = 0;
    for (const Bird& B : Birds) if (B.Perched()) ++N;
    return N;
}

// --------------------------------------------------------------------------------- startle
/** Scatter: every bird within RadiusCm of Origin gets a startle timer, and every perched bird
 *  in that radius launches. Deterministic, and safe to call at any time. */
inline void ApplyStartle(std::vector<Bird>& Birds, std::vector<PerchPoint>& Perches,
                         const FlockConfig& Config, const Vec3& Origin, double RadiusCm, double Time)
{
    if (!Finite(Origin) || !std::isfinite(RadiusCm) || RadiusCm <= 0) return;
    const double R2 = RadiusCm * RadiusCm;
    for (size_t I = 0; I < Birds.size(); ++I)
    {
        Bird& B = Birds[I];
        if (LengthSquared(B.Position - Origin) > R2) continue;
        Launch(B, Perches, Config, Time, static_cast<int>(I));   // no-op for a bird already flying
        B.StartleRemaining = Config.Species.StartleSeconds;
        // Do not try to perch again while the startle lasts.
        B.NextDecisionTime = std::max(B.NextDecisionTime, Time + Config.Species.StartleSeconds);
    }
}

/** Acceleration away from a startle origin, fading over the startle timer. */
inline Vec3 StartleAcceleration(const Bird& B, const Vec3& Origin, const SpeciesProfile& P)
{
    if (B.StartleRemaining <= 0.0 || P.StartleSeconds <= 0.0) return Vec3{};
    Vec3 Away = B.Position - Origin;
    Away.Z = std::max(Away.Z, 0.0) + 60.0;                 // startled birds go up as well as out
    const double Fade = Clamp(B.StartleRemaining / P.StartleSeconds, 0.0, 1.0);
    return Normalized(Away) * (P.StartleAccelCmPerSecond2 * Fade);
}

// --------------------------------------------------------------------- overlap resolution
/** Push apart any pair closer than HardSeparationCm. Perched birds are obstacles, never
 *  movers (they sit exactly on their ledge). Exactly coincident pairs are separated along a
 *  hashed direction, so two birds can never occupy the same point. Returns the smallest
 *  pairwise distance seen on the LAST pass. */
inline double ResolveOverlaps(std::vector<Bird>& Birds, Grid& Scratch, double HardSeparationCm, int Iterations = 2)
{
    double Smallest = 1e18;
    if (Birds.size() < 2 || HardSeparationCm <= 0) return Smallest;
    for (int Pass = 0; Pass < std::max(1, Iterations); ++Pass)
    {
        Scratch.Build(Birds, HardSeparationCm * 1.05);
        Smallest = 1e18;
        for (size_t I = 0; I < Birds.size(); ++I)
        {
            Bird& A = Birds[I];
            if (A.Perched()) continue;
            Vec3 Push{};
            Scratch.ForEachNear(A.Position, [&](int J)
            {
                if (static_cast<size_t>(J) == I) return;
                const Bird& Other = Birds[static_cast<size_t>(J)];
                const Vec3 Delta = A.Position - Other.Position;
                double D = Length(Delta);
                if (D < Smallest) Smallest = D;
                if (D >= HardSeparationCm) return;
                // Work in an explicit unit direction and a scalar overlap. Scaling Delta by
                // 1/D instead would be identical for a normal pair but catastrophic for a
                // coincident one: the substituted direction is already unit length, so
                // dividing it by an epsilon D threw the pair tens of kilometres apart in a
                // single pass. Two birds land on exactly one point often enough to matter -
                // two ledges authored at the same place, or two birds clamped to the same
                // point on the cylinder - and the symptom was a bird teleporting to the rim.
                Vec3 Direction;
                if (D < 1e-6)
                {
                    const double Angle = HashRange(A.Seed, static_cast<uint32_t>(J), 909u, 0.0, 2.0 * Pi);
                    Direction = Vec3{std::cos(Angle), std::sin(Angle), 0.0};
                    D = 0.0;
                }
                else
                {
                    Direction = Delta * (1.0 / D);
                }
                // The mover takes the whole correction when the other bird is perched and half
                // otherwise; the other bird takes its own half on its own pass.
                const double Share = Other.Perched() ? 1.0 : 0.5;
                Push += Direction * ((HardSeparationCm - D) * Share);
            });
            if (LengthSquared(Push) > 0.0) A.Position += Push;
        }
    }
    return Smallest;
}

/** Smallest pairwise distance in the flock, computed exactly. O(n^2): for tests and receipts,
 *  never for the per-frame path. */
inline double SmallestPairDistance(const std::vector<Bird>& Birds)
{
    double Smallest = 1e18;
    for (size_t I = 0; I + 1 < Birds.size(); ++I)
        for (size_t J = I + 1; J < Birds.size(); ++J)
            Smallest = std::min(Smallest, Length(Birds[I].Position - Birds[J].Position));
    return Smallest;
}

// ------------------------------------------------------------------------------ the step
struct StepStats
{
    int Stepped = 0;
    int NeighbourTests = 0;
    int Launched = 0;
    int Landed = 0;
    double MeanSpeedCmPerSecond = 0.0;
    double MeanAccelCmPerSecond2 = 0.0;
};

/** Advance one round-robin slice of the flock by Dt seconds of simulated time.
 *
 *  Neighbours must be built by the caller (BuildGrid) so a whole slice sees one consistent
 *  neighbourhood. StartleOrigin is only read while a bird's StartleRemaining is positive. */
inline StepStats Step(std::vector<Bird>& Birds, std::vector<PerchPoint>& Perches, const FlockConfig& Config,
                      const Grid& Neighbours, const UpdateWindow& Window, double Dt, double Time,
                      const Vec3& StartleOrigin)
{
    StepStats Stats;
    const SpeciesProfile& P = Config.Species;
    const FlockBounds& Bounds = Config.Bounds;
    if (Birds.empty() || !std::isfinite(Dt) || Dt <= 0.0) return Stats;
    Dt = Clamp(Dt, 0.0, 0.5);
    const double NeighbourR2 = P.NeighbourRadiusCm * P.NeighbourRadiusCm;
    const double SepR2 = P.DesiredSeparationCm * P.DesiredSeparationCm;
    const int Total = static_cast<int>(Birds.size());
    const int TargetPerched = static_cast<int>(P.PerchFraction * Total + 0.5);
    int SittingNow = PerchedCount(Birds);
    double SpeedSum = 0.0, AccelSum = 0.0;

    for (int K = 0; K < Window.Count; ++K)
    {
        const int I = (Window.Start + K) % Total;
        Bird& B = Birds[static_cast<size_t>(I)];
        AdvanceWing(B, Dt);
        if (B.StartleRemaining > 0.0) B.StartleRemaining = std::max(0.0, B.StartleRemaining - Dt);
        ++Stats.Stepped;

        // ---- sitting on a ledge -------------------------------------------------------
        if (B.Perched())
        {
            if (B.PerchIndex < static_cast<int>(Perches.size()))
                B.Position = Perches[static_cast<size_t>(B.PerchIndex)].Position;
            B.Velocity = Vec3{};
            if (Time >= B.NextDecisionTime)
            {
                Launch(B, Perches, Config, Time, I);
                --SittingNow;
                ++Stats.Launched;
            }
            continue;
        }

        // ---- flying: neighbourhood ----------------------------------------------------
        Vec3 SeparationSum{}, VelocitySum{}, CentroidSum{};
        int NeighbourCount = 0, SeparationCount = 0;
        Neighbours.ForEachNear(B.Position, [&](int J)
        {
            if (J == I) return;
            const Bird& Other = Birds[static_cast<size_t>(J)];
            const Vec3 Delta = Other.Position - B.Position;
            const double D2 = LengthSquared(Delta);
            ++Stats.NeighbourTests;
            if (D2 > NeighbourR2 || D2 < 1e-12) return;
            ++NeighbourCount;
            CentroidSum += Other.Position;
            if (!Other.Perched()) VelocitySum += Other.Velocity;
            if (D2 < SepR2)
            {
                ++SeparationCount;
                SeparationSum += Delta * (-1.0 / D2);      // inverse-square push away from Other
            }
        });

        Vec3 Accel{};
        const double Cruise = P.CruiseSpeedCmPerSecond;
        if (SeparationCount > 0)
        {
            const Vec3 Desired = Normalized(SeparationSum) * Cruise;
            Accel += (Desired - B.Velocity) * P.SeparationWeight;
        }
        if (NeighbourCount > 0)
        {
            if (LengthSquared(VelocitySum) > 1e-9)
            {
                const Vec3 Desired = Normalized(VelocitySum) * Cruise;
                Accel += (Desired - B.Velocity) * P.AlignmentWeight;
            }
            const Vec3 Centroid = CentroidSum * (1.0 / static_cast<double>(NeighbourCount));
            const Vec3 ToCentroid = Centroid - B.Position;
            if (LengthSquared(ToCentroid) > 1.0)
            {
                const Vec3 Desired = Normalized(ToCentroid) * Cruise;
                Accel += (Desired - B.Velocity) * P.CohesionWeight;
            }
        }

        // ---- wander target, or an approach to a chosen ledge ---------------------------
        bool bLandingRun = false;
        if (B.TargetPerchIndex >= 0 && B.TargetPerchIndex < static_cast<int>(Perches.size()))
        {
            PerchPoint& Target = Perches[static_cast<size_t>(B.TargetPerchIndex)];
            if (Target.Occupant >= 0 && Target.Occupant != I)
            {
                B.TargetPerchIndex = -1;                    // somebody else took it
            }
            else
            {
                bLandingRun = true;
                B.WanderTargetCm = Target.Position;
                if (LengthSquared(Target.Position - B.Position) < P.LandingRadiusCm * P.LandingRadiusCm)
                {
                    Target.Occupant = I;
                    B.PerchIndex = B.TargetPerchIndex;
                    B.TargetPerchIndex = -1;
                    B.Position = Target.Position;
                    B.Velocity = Vec3{};
                    B.NextDecisionTime = Time + HashRange(B.Seed, static_cast<uint32_t>(I), 501u,
                                                          P.PerchSecondsMin, P.PerchSecondsMax);
                    ++SittingNow;
                    ++Stats.Landed;
                    continue;
                }
            }
        }
        if (!bLandingRun)
        {
            const bool bWantsPerch = P.bPerches && !Perches.empty() && B.StartleRemaining <= 0.0
                                     && SittingNow < TargetPerched && Time >= B.NextDecisionTime;
            if (bWantsPerch)
            {
                const int Free = NearestFreePerch(Perches, B.Position, Bounds.RadiusCm * 2.0, I);
                if (Free >= 0)
                {
                    B.TargetPerchIndex = Free;
                    Perches[static_cast<size_t>(Free)].Occupant = I;   // reserve it
                    B.WanderTargetCm = Perches[static_cast<size_t>(Free)].Position;
                    bLandingRun = true;
                }
                else
                {
                    B.NextDecisionTime = Time + 5.0;
                }
            }
            if (!bLandingRun && (Time >= B.WanderExpiryTime
                                 || LengthSquared(B.WanderTargetCm - B.Position) < 250.0 * 250.0))
            {
                const uint32_t Tick = static_cast<uint32_t>(Clamp(Time, 0.0, 1e7) * 4.0);
                B.WanderTargetCm = PointInBounds(Bounds, B.Seed, static_cast<uint32_t>(I), 600u + Tick);
                B.WanderExpiryTime = Time + HashRange(B.Seed, static_cast<uint32_t>(I), 601u + Tick, 4.0, 14.0);
            }
        }
        {
            const Vec3 ToTarget = B.WanderTargetCm - B.Position;
            if (LengthSquared(ToTarget) > 1.0)
            {
                const Vec3 Desired = Normalized(ToTarget) * Cruise;
                Accel += (Desired - B.Velocity) * (bLandingRun ? std::max(P.WanderWeight, 1.6) : P.WanderWeight);
            }
        }

        // ---- volume, startle and damping ----------------------------------------------
        Accel += RadialAcceleration(B.Position, Bounds, P.MaxAccelCmPerSecond2) * P.HomeWeight;
        Accel.Z += AltitudeAcceleration(B.Position, B.Velocity, Bounds, P.MaxAccelCmPerSecond2);
        if (B.StartleRemaining > 0.0) Accel += StartleAcceleration(B, StartleOrigin, P);
        Accel += B.Velocity * (-P.DampingPerSecond);        // first-order drag: this is what settles it

        const double AccelCeiling = P.MaxAccelCmPerSecond2 * (B.StartleRemaining > 0.0 ? 2.5 : 1.0);
        Accel = Limit(Accel, AccelCeiling);
        AccelSum += Length(Accel);

        B.Velocity += Accel * Dt;
        const double SpeedCeiling = P.MaxSpeedCmPerSecond * (B.StartleRemaining > 0.0 ? P.StartleSpeedMultiplier : 1.0);
        double Speed = Length(B.Velocity);
        if (!std::isfinite(Speed) || Speed < 1e-9)
        {
            const double Angle = HashRange(B.Seed, static_cast<uint32_t>(I), 701u, 0.0, 2.0 * Pi);
            B.Velocity = Vec3{std::cos(Angle), std::sin(Angle), 0.0} * std::max(1.0, P.MinSpeedCmPerSecond);
            Speed = Length(B.Velocity);
        }
        if (Speed > SpeedCeiling) B.Velocity = B.Velocity * (SpeedCeiling / Speed);
        else if (Speed < P.MinSpeedCmPerSecond) B.Velocity = B.Velocity * (P.MinSpeedCmPerSecond / Speed);

        B.Position += B.Velocity * Dt;
        ClampToBounds(B, Bounds);
        SpeedSum += Length(B.Velocity);
    }
    if (Stats.Stepped > 0)
    {
        Stats.MeanSpeedCmPerSecond = SpeedSum / static_cast<double>(Stats.Stepped);
        Stats.MeanAccelCmPerSecond2 = AccelSum / static_cast<double>(Stats.Stepped);
    }
    return Stats;
}

/** Build the neighbour grid for a flock at its species' neighbour radius. */
inline void BuildGrid(Grid& G, const std::vector<Bird>& Birds, const SpeciesProfile& P)
{
    G.Build(Birds, std::max(200.0, P.NeighbourRadiusCm));
}

/** One complete update: build the grid, step a slice, resolve overlaps. Returns the stats.
 *  The actor calls this from its timer; the test calls it in a loop. */
inline StepStats Update(std::vector<Bird>& Birds, std::vector<PerchPoint>& Perches, const FlockConfig& Config,
                        Grid& Neighbours, Grid& OverlapScratch, int& Cursor, int Budget,
                        double UpdateIntervalSeconds, double Time, const Vec3& StartleOrigin)
{
    const int Total = static_cast<int>(Birds.size());
    const UpdateWindow Window = NextUpdateWindow(Cursor, Total, Budget);
    Cursor = Window.NextCursor;
    BuildGrid(Neighbours, Birds, Config.Species);
    const double Dt = CatchUpSeconds(UpdateIntervalSeconds, Total, Budget);
    StepStats Stats = Step(Birds, Perches, Config, Neighbours, Window, Dt, Time, StartleOrigin);
    ResolveOverlaps(Birds, OverlapScratch, Config.Species.HardSeparationCm, 2);
    for (Bird& B : Birds) ClampToBounds(B, Config.Bounds);
    return Stats;
}

// ---------------------------------------------------------------- soundscape hook helper
/** Rate-limited "a bird should be heard now" test, for the audio hook the soundscape agent
 *  consumes. This module NEVER plays or loads audio; it only says when a call would be due.
 *  Fires at most once per MeanIntervalSeconds on average, per flock. */
inline bool ShouldCall(uint32_t Seed, double Time, double MeanIntervalSeconds, double& NextTimeInOut)
{
    if (!std::isfinite(Time) || MeanIntervalSeconds <= 0) return false;
    if (NextTimeInOut <= 0.0) { NextTimeInOut = Time + MeanIntervalSeconds * 0.5; return false; }
    if (Time < NextTimeInOut) return false;
    const uint32_t Tick = static_cast<uint32_t>(Clamp(Time, 0.0, 1e7));
    NextTimeInOut = Time + MeanIntervalSeconds * HashRange(Seed, Tick, 811u, 0.45, 1.85);
    return true;
}

} // namespace MikdashFlock
