#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstddef>
#include <vector>

// Engine-independent vegetation scatter math, shared by Scripts/create_vegetation.py's
// reference implementation, by Scripts/release_vegetation.py's readback checks and by the
// standalone test Plugins/MikdashRuntime/Tests/ScatterMathTest.cpp.
//
// Units: centimetres, degrees, seconds. World frame is Unreal's: +X east, +Y south, +Z up.
// No Unreal types, no globals, no I/O, no std::rand. Every random draw comes from a pure
// integer hash of (Seed, Index, Lane), so the same seed reproduces the same scatter in the
// offline Python generator, in the editor commandlet and in a packaged build.
//
// What this is NOT: it is not an ecosystem simulation and it is not a collision system.
// It answers four questions only -- where may a plant stand (band + exclusion), how far
// apart must plants stand (Poisson disc), how do plants clump (cluster weighting), and how
// does one instance differ from its neighbour (scale/rotation jitter).
namespace MikdashScatter
{
constexpr double Pi = 3.14159265358979323846;
/** One "hundred square metres" in square centimetres. Densities are quoted per 100 m^2,
 * matching the crowd-field convention and the way field botany quotes cover. */
constexpr double SquareCmPer100SqM = 1.0e6;

// ---------------------------------------------------------------------------
// Small vector helpers
// ---------------------------------------------------------------------------
struct Vec2
{
    double X = 0.0, Y = 0.0;
};
inline Vec2 operator+(const Vec2& A, const Vec2& B) { return {A.X + B.X, A.Y + B.Y}; }
inline Vec2 operator-(const Vec2& A, const Vec2& B) { return {A.X - B.X, A.Y - B.Y}; }
inline Vec2 operator*(const Vec2& A, double S) { return {A.X * S, A.Y * S}; }
inline double Dot(const Vec2& A, const Vec2& B) { return A.X * B.X + A.Y * B.Y; }
inline double Length(const Vec2& A) { return std::sqrt(Dot(A, A)); }
inline double DistanceSquared(const Vec2& A, const Vec2& B)
{
    const double DX = A.X - B.X, DY = A.Y - B.Y;
    return DX * DX + DY * DY;
}
inline double Distance(const Vec2& A, const Vec2& B) { return std::sqrt(DistanceSquared(A, B)); }
inline bool Finite(const Vec2& A) { return std::isfinite(A.X) && std::isfinite(A.Y); }
inline double Clamp(double V, double Lo, double Hi) { return std::max(Lo, std::min(Hi, V)); }
inline int ClampInt(int V, int Lo, int Hi) { return std::max(Lo, std::min(Hi, V)); }
inline long long ClampLong(long long V, long long Lo, long long Hi) { return std::max(Lo, std::min(Hi, V)); }
inline double DegToRad(double D) { return D * Pi / 180.0; }
inline double RadToDeg(double R) { return R * 180.0 / Pi; }

/** Hermite ramp: 0 at or below Lo, 1 at or above Hi, smooth in between. Lo >= Hi yields a
 * hard step so a caller can ask for an unfeathered band without a special case. */
inline double SmoothStep(double V, double Lo, double Hi)
{
    if (!std::isfinite(V) || !std::isfinite(Lo) || !std::isfinite(Hi)) return 0.0;
    if (Hi <= Lo) return V >= Hi ? 1.0 : 0.0;
    const double T = Clamp((V - Lo) / (Hi - Lo), 0.0, 1.0);
    return T * T * (3.0 - 2.0 * T);
}

// ---------------------------------------------------------------------------
// Deterministic hashing (same construction as MikdashCrowd, repeated so this header
// stands alone and can be compiled without the crowd module).
// ---------------------------------------------------------------------------

/** 32-bit integer avalanche (Murmur3 finalizer). Pure; no state. */
inline uint32_t HashInt(uint32_t V)
{
    V ^= V >> 16;
    V *= 0x85ebca6bu;
    V ^= V >> 13;
    V *= 0xc2b2ae35u;
    V ^= V >> 16;
    return V;
}
inline uint32_t HashCombine(uint32_t Seed, uint32_t Value)
{
    return HashInt(Seed ^ (Value + 0x9e3779b9u + (Seed << 6) + (Seed >> 2)));
}
/** Uniform double in [0,1). Lane keeps unrelated draws for the same index independent, so
 * adding a new jittered property never disturbs the ones already authored. */
inline double HashUnit(uint32_t Seed, uint32_t Index, uint32_t Lane)
{
    return HashCombine(HashCombine(Seed, Index), Lane) * (1.0 / 4294967296.0);
}
inline double HashRange(uint32_t Seed, uint32_t Index, uint32_t Lane, double Lo, double Hi)
{
    return Lo + (Hi - Lo) * HashUnit(Seed, Index, Lane);
}
/** Two independent unit draws combined into an approximately normal deviate in
 * [-3, 3] (mean 0, sd ~0.7). Used for size jitter, where a bell is more lifelike
 * than a flat range. */
inline double HashBell(uint32_t Seed, uint32_t Index, uint32_t Lane)
{
    const double A = HashUnit(Seed, Index, Lane);
    const double B = HashUnit(Seed, Index, Lane + 0x51ed2701u);
    return Clamp((A + B + HashUnit(Seed, Index, Lane + 0x1b873593u)) * 2.0 - 3.0, -3.0, 3.0);
}

// ---------------------------------------------------------------------------
// Terrain: a regular square height grid, sampled the way the source terrain mesh is
// triangulated (two triangles per cell, diagonal from (i,j) to (i+1,j+1)), so a height
// read here equals the height of the mesh the player actually walks on. Bilinear would
// float a plant above, or sink it below, the rendered surface on every steep cell.
// ---------------------------------------------------------------------------
struct HeightField
{
    const double* Heights = nullptr;   ///< Size*Size samples, row-major, row index j = Y.
    int Size = 0;                      ///< Samples per side (>= 2).
    double StepCm = 1.0;               ///< World spacing between samples.
    double OriginXCm = 0.0;            ///< World X of sample (0, 0).
    double OriginYCm = 0.0;            ///< World Y of sample (0, 0).

    bool Valid() const
    {
        return Heights != nullptr && Size >= 2 && std::isfinite(StepCm) && StepCm > 0.0
            && std::isfinite(OriginXCm) && std::isfinite(OriginYCm);
    }
    double MinXCm() const { return OriginXCm; }
    double MinYCm() const { return OriginYCm; }
    double MaxXCm() const { return OriginXCm + (Size - 1) * StepCm; }
    double MaxYCm() const { return OriginYCm + (Size - 1) * StepCm; }
};

/** Ground height in cm. Points outside the grid clamp to the edge rather than extrapolate;
 * an invalid grid yields 0. Never returns NaN for finite input. */
inline double HeightAt(const HeightField& Field, Vec2 P)
{
    if (!Field.Valid() || !Finite(P)) return 0.0;
    const double U = Clamp((P.X - Field.OriginXCm) / Field.StepCm, 0.0, Field.Size - 1.0001);
    const double V = Clamp((P.Y - Field.OriginYCm) / Field.StepCm, 0.0, Field.Size - 1.0001);
    const int I = static_cast<int>(U);
    const int J = static_cast<int>(V);
    const double A = U - I;
    const double B = V - J;
    const double H00 = Field.Heights[static_cast<size_t>(J) * Field.Size + I];
    const double H10 = Field.Heights[static_cast<size_t>(J) * Field.Size + I + 1];
    const double H01 = Field.Heights[static_cast<size_t>(J + 1) * Field.Size + I];
    const double H11 = Field.Heights[static_cast<size_t>(J + 1) * Field.Size + I + 1];
    if (A + B <= 1.0) return H00 + (H10 - H00) * A + (H01 - H00) * B;
    return H11 + (H01 - H11) * (1.0 - A) + (H10 - H11) * (1.0 - B);
}

/** Local terrain description used by every band filter. */
struct TerrainSample
{
    double HeightCm = 0.0;
    /** Angle between the surface normal and vertical, 0 flat, 90 a cliff. */
    double SlopeDegrees = 0.0;
    /** Downhill compass bearing in degrees, 0 = downhill toward +X (east), 90 = toward +Y
     * (south, in this project's frame). Zero on flat ground. */
    double AspectDegrees = 0.0;
    double DzDx = 0.0;
    double DzDy = 0.0;
};

/** Central-difference gradient over one cell. Deliberately grid-scale rather than
 * finer: a 25 m DEM has no honest sub-cell slope, and pretending otherwise would put
 * scrub on imaginary cliffs. */
inline TerrainSample SampleTerrain(const HeightField& Field, Vec2 P)
{
    TerrainSample Out;
    if (!Field.Valid() || !Finite(P)) return Out;
    const double H = Field.StepCm;
    Out.HeightCm = HeightAt(Field, P);
    Out.DzDx = (HeightAt(Field, {P.X + H, P.Y}) - HeightAt(Field, {P.X - H, P.Y})) / (2.0 * H);
    Out.DzDy = (HeightAt(Field, {P.X, P.Y + H}) - HeightAt(Field, {P.X, P.Y - H})) / (2.0 * H);
    const double G = std::sqrt(Out.DzDx * Out.DzDx + Out.DzDy * Out.DzDy);
    Out.SlopeDegrees = RadToDeg(std::atan(G));
    Out.AspectDegrees = G < 1e-9 ? 0.0 : RadToDeg(std::atan2(-Out.DzDy, -Out.DzDx));
    if (Out.AspectDegrees < 0.0) Out.AspectDegrees += 360.0;
    return Out;
}

/** Positive where the ground is locally concave (a wadi or a gully collecting runoff),
 * negative on a convex ridge, in units of 1/cm scaled by the cell size so the number is
 * order 1. This is what makes growth denser in the valleys without hand-painting them. */
inline double Concavity(const HeightField& Field, Vec2 P)
{
    if (!Field.Valid() || !Finite(P)) return 0.0;
    const double H = Field.StepCm;
    const double C = HeightAt(Field, P);
    const double Sum = HeightAt(Field, {P.X + H, P.Y}) + HeightAt(Field, {P.X - H, P.Y})
                     + HeightAt(Field, {P.X, P.Y + H}) + HeightAt(Field, {P.X, P.Y - H});
    return (Sum - 4.0 * C) / H;
}

// ---------------------------------------------------------------------------
// Bands: altitude and slope, each with a feather so a species fades out at the edge of
// its range instead of stopping on a contour line.
// ---------------------------------------------------------------------------
struct Band
{
    double MinAltitudeCm = -1.0e9;
    double MaxAltitudeCm = 1.0e9;
    /** Feather width applied inside each altitude limit. 0 gives a hard edge. */
    double AltitudeFeatherCm = 0.0;
    double MinSlopeDegrees = 0.0;
    double MaxSlopeDegrees = 90.0;
    double SlopeFeatherDegrees = 0.0;
    /** Preferred downhill bearing, and how strongly it matters. AspectWeight 0 ignores
     * aspect entirely (the usual case); 1 means a plant only grows on that face.
     * Carob wants the hot southern exposure, oak and terebinth the shaded northern one. */
    double PreferredAspectDegrees = 0.0;
    double AspectWeight = 0.0;
    /** Extra weight given to concave ground (wadis). 0 ignores it. */
    double ConcavityWeight = 0.0;
};

/** Membership weight in [0,1]. Zero means "this species does not grow here"; the caller
 * uses the value as an acceptance probability so the edge of a band is ragged, as a real
 * vegetation boundary is, rather than a clean line. */
inline double BandWeight(const Band& B, const TerrainSample& S, double ConcavityValue = 0.0)
{
    if (!std::isfinite(S.HeightCm) || !std::isfinite(S.SlopeDegrees)) return 0.0;
    double W = SmoothStep(S.HeightCm, B.MinAltitudeCm, B.MinAltitudeCm + B.AltitudeFeatherCm)
             * (1.0 - SmoothStep(S.HeightCm, B.MaxAltitudeCm - B.AltitudeFeatherCm, B.MaxAltitudeCm));
    W *= SmoothStep(S.SlopeDegrees, B.MinSlopeDegrees, B.MinSlopeDegrees + B.SlopeFeatherDegrees)
       * (1.0 - SmoothStep(S.SlopeDegrees, B.MaxSlopeDegrees - B.SlopeFeatherDegrees, B.MaxSlopeDegrees));
    if (W <= 0.0) return 0.0;
    if (B.AspectWeight > 0.0 && S.SlopeDegrees > 1.0)
    {
        double Delta = std::fmod(std::abs(S.AspectDegrees - B.PreferredAspectDegrees), 360.0);
        if (Delta > 180.0) Delta = 360.0 - Delta;
        const double Align = 0.5 * (1.0 + std::cos(DegToRad(Delta)));   // 1 facing, 0 opposite
        W *= (1.0 - B.AspectWeight) + B.AspectWeight * Align;
    }
    if (B.ConcavityWeight > 0.0 && std::isfinite(ConcavityValue))
    {
        const double Wet = Clamp(0.5 + 0.5 * ConcavityValue * 4000.0, 0.0, 1.0);
        W *= (1.0 - B.ConcavityWeight) + B.ConcavityWeight * Wet;
    }
    return Clamp(W, 0.0, 1.0);
}

/** Hard predicate form, for callers that want a yes/no band test (and for the tests). */
inline bool InBand(const Band& B, const TerrainSample& S)
{
    return S.HeightCm >= B.MinAltitudeCm && S.HeightCm <= B.MaxAltitudeCm
        && S.SlopeDegrees >= B.MinSlopeDegrees && S.SlopeDegrees <= B.MaxSlopeDegrees;
}

// ---------------------------------------------------------------------------
// Exclusion. Four primitive shapes cover everything that must stay clear:
//   Circle   - a single object with a radius (an existing placeholder tree, a lamp).
//   Box      - an axis-aligned XY footprint plus margin (a building, a stair block, an
//              architecture manifest AABB, one decomposed box of a hollow union).
//   Capsule  - a segment with a half width (a road, a path, a stair run, a wall chain).
//   Polygon  - an arbitrary closed ring plus margin (the Temple Mount enclosure, a plaza,
//              a court, an OSM building footprint).
// A caller assembles a set of these from measured receipts and asks one question.
// ---------------------------------------------------------------------------
struct ExclusionCircle
{
    double XCm = 0.0, YCm = 0.0, RadiusCm = 0.0;
};
struct ExclusionBox
{
    double MinXCm = 0.0, MinYCm = 0.0, MaxXCm = 0.0, MaxYCm = 0.0, MarginCm = 0.0;
};
struct ExclusionCapsule
{
    double X0Cm = 0.0, Y0Cm = 0.0, X1Cm = 0.0, Y1Cm = 0.0, HalfWidthCm = 0.0;
};
/** Ring stored as a range into a shared point array so a whole set of polygons is three
 * flat arrays and no allocation. First point is NOT repeated. */
struct ExclusionPolygon
{
    int Start = 0, Count = 0;
    double MarginCm = 0.0;
};

/** Even-odd ray cast. Degenerate or non-finite input contains nothing rather than
 * crashing or, worse, silently reporting "outside" for a point in the sanctuary. */
inline bool PointInPolygon(const Vec2* Points, int Count, Vec2 P)
{
    if (Points == nullptr || Count < 3 || !Finite(P)) return false;
    bool Inside = false;
    for (int I = 0, J = Count - 1; I < Count; J = I++)
    {
        const Vec2 A = Points[I];
        const Vec2 B = Points[J];
        if (!Finite(A) || !Finite(B)) return false;
        if ((A.Y > P.Y) != (B.Y > P.Y))
        {
            const double Denominator = B.Y - A.Y;
            if (std::abs(Denominator) < 1e-12) continue;
            const double X = A.X + (P.Y - A.Y) * (B.X - A.X) / Denominator;
            if (P.X < X) Inside = !Inside;
        }
    }
    return Inside;
}

/** Shortest distance from P to a segment. */
inline double DistanceToSegment(Vec2 A, Vec2 B, Vec2 P)
{
    const Vec2 AB = B - A;
    const double LenSq = Dot(AB, AB);
    if (LenSq < 1e-12) return Distance(A, P);
    const double T = Clamp(Dot(P - A, AB) / LenSq, 0.0, 1.0);
    return Distance(A + AB * T, P);
}

/** Unsigned distance to the ring, whether P is inside it or not. */
inline double DistanceToPolygonEdge(const Vec2* Points, int Count, Vec2 P)
{
    if (Points == nullptr || Count < 2 || !Finite(P)) return 0.0;
    double Best = 1.0e300;
    for (int I = 0, J = Count - 1; I < Count; J = I++)
    {
        Best = std::min(Best, DistanceToSegment(Points[J], Points[I], P));
    }
    return Best;
}

/** Inside the ring, or within Margin of it. This is the test used for the Temple Mount
 * enclosure, so it must be conservative: an unusable polygon excludes nothing and the
 * caller is expected to check Valid...() first. */
inline bool PointInPolygonWithMargin(const Vec2* Points, int Count, Vec2 P, double Margin)
{
    if (PointInPolygon(Points, Count, P)) return true;
    return Margin > 0.0 && Count >= 3 && Points != nullptr
        && DistanceToPolygonEdge(Points, Count, P) <= Margin;
}

/** Everything a scatter must keep away from. All pointers may be null with a zero count. */
struct ExclusionSet
{
    const ExclusionCircle* Circles = nullptr;
    int CircleCount = 0;
    const ExclusionBox* Boxes = nullptr;
    int BoxCount = 0;
    const ExclusionCapsule* Capsules = nullptr;
    int CapsuleCount = 0;
    const ExclusionPolygon* Polygons = nullptr;
    int PolygonCount = 0;
    const Vec2* PolygonPoints = nullptr;
    int PolygonPointCount = 0;
};

/** True if the point is inside any exclusion primitive (its own radius already folded into
 * the primitive's margin by the caller, or passed as ExtraRadius here for a plant whose
 * crown is wider than its trunk). A non-finite point is always excluded. */
inline bool IsExcluded(const ExclusionSet& Set, Vec2 P, double ExtraRadiusCm = 0.0)
{
    if (!Finite(P)) return true;
    const double R = std::isfinite(ExtraRadiusCm) && ExtraRadiusCm > 0.0 ? ExtraRadiusCm : 0.0;
    for (int I = 0; I < Set.CircleCount && Set.Circles != nullptr; ++I)
    {
        const ExclusionCircle& C = Set.Circles[I];
        const double Reach = C.RadiusCm + R;
        const double DX = P.X - C.XCm, DY = P.Y - C.YCm;
        if (DX * DX + DY * DY <= Reach * Reach) return true;
    }
    for (int I = 0; I < Set.BoxCount && Set.Boxes != nullptr; ++I)
    {
        const ExclusionBox& B = Set.Boxes[I];
        const double M = B.MarginCm + R;
        if (P.X >= B.MinXCm - M && P.X <= B.MaxXCm + M && P.Y >= B.MinYCm - M && P.Y <= B.MaxYCm + M) return true;
    }
    for (int I = 0; I < Set.CapsuleCount && Set.Capsules != nullptr; ++I)
    {
        const ExclusionCapsule& C = Set.Capsules[I];
        if (DistanceToSegment({C.X0Cm, C.Y0Cm}, {C.X1Cm, C.Y1Cm}, P) <= C.HalfWidthCm + R) return true;
    }
    for (int I = 0; I < Set.PolygonCount && Set.Polygons != nullptr && Set.PolygonPoints != nullptr; ++I)
    {
        const ExclusionPolygon& G = Set.Polygons[I];
        if (G.Count < 3 || G.Start < 0 || G.Start + G.Count > Set.PolygonPointCount) return true;   // unusable ring: refuse
        if (PointInPolygonWithMargin(Set.PolygonPoints + G.Start, G.Count, P, G.MarginCm + R)) return true;
    }
    return false;
}

// ---------------------------------------------------------------------------
// Clustering. Real hillside vegetation is patchy: a grove here, bare rock there. A
// cluster field is a set of deterministic centres; a candidate's weight is high near a
// centre and low between them. Clustering only ever REMOVES candidates, so minimum
// spacing is preserved by construction.
// ---------------------------------------------------------------------------
struct ClusterField
{
    /** 0 disables clustering and every candidate keeps weight 1. */
    int Count = 0;
    double RadiusCm = 0.0;
    /** 0 uniform, 1 nothing at all survives between clusters. */
    double Strength = 0.0;
    double MinXCm = 0.0, MinYCm = 0.0, MaxXCm = 0.0, MaxYCm = 0.0;
    uint32_t Seed = 0;
};

inline Vec2 ClusterCentre(const ClusterField& F, int Index)
{
    return {HashRange(F.Seed, static_cast<uint32_t>(Index), 11u, F.MinXCm, F.MaxXCm),
            HashRange(F.Seed, static_cast<uint32_t>(Index), 12u, F.MinYCm, F.MaxYCm)};
}

/** Weight in [1-Strength, 1]: 1 at a cluster centre, falling to 1-Strength beyond
 * RadiusCm. With Count 0 or Strength 0 it is exactly 1 everywhere. */
inline double ClusterWeight(const ClusterField& F, Vec2 P)
{
    if (F.Count <= 0 || F.Strength <= 0.0 || F.RadiusCm <= 0.0 || !Finite(P)) return 1.0;
    double Best = 1.0e300;
    for (int I = 0; I < F.Count; ++I)
    {
        Best = std::min(Best, DistanceSquared(P, ClusterCentre(F, I)));
    }
    const double T = Clamp(std::sqrt(Best) / F.RadiusCm, 0.0, 1.0);
    const double Falloff = 1.0 - T * T * (3.0 - 2.0 * T);   // 1 at the centre, 0 at the rim
    return Clamp((1.0 - F.Strength) + F.Strength * Falloff, 0.0, 1.0);
}

// ---------------------------------------------------------------------------
// Terraces. The Judean hillsides are farmed in stone-walled benches, so a grove planted
// with a plain scatter reads as wild woodland rather than as an olive terrace. This
// quantises the DOWNHILL coordinate to a bench spacing, which lines the trees up along
// the contour while leaving them free along it.
// ---------------------------------------------------------------------------
struct TerraceField
{
    bool Enabled = false;
    /** Horizontal distance between bench faces, measured along the fall line. */
    double BenchWidthCm = 500.0;
    /** How hard a plant is pulled onto the bench line: 0 none, 1 exactly on it. */
    double Snap = 0.0;
    /** Fraction of BenchWidthCm the plant may still wander along the fall line. */
    double JitterFraction = 0.15;
    uint32_t Seed = 0;
};

/** Move P onto the nearest bench of a terraced slope. Flat ground (slope below
 * MinSlopeDegrees) is left untouched: terraces exist because of the fall, and snapping on
 * the flat would produce visible stripes in an open field. */
inline Vec2 SnapToTerrace(const TerraceField& T, const TerrainSample& S, Vec2 P,
                          uint32_t Index, double MinSlopeDegrees = 4.0)
{
    if (!T.Enabled || T.Snap <= 0.0 || T.BenchWidthCm <= 0.0 || !Finite(P)) return P;
    if (S.SlopeDegrees < MinSlopeDegrees) return P;
    const double G = std::sqrt(S.DzDx * S.DzDx + S.DzDy * S.DzDy);
    if (G < 1e-9) return P;
    const Vec2 Downhill{-S.DzDx / G, -S.DzDy / G};
    const double Along = Dot(P, Downhill);
    const double Snapped = std::floor(Along / T.BenchWidthCm + 0.5) * T.BenchWidthCm
        + (HashUnit(T.Seed, Index, 33u) - 0.5) * 2.0 * T.JitterFraction * T.BenchWidthCm;
    return P + Downhill * ((Snapped - Along) * Clamp(T.Snap, 0.0, 1.0));
}

// ---------------------------------------------------------------------------
// Per-instance jitter
// ---------------------------------------------------------------------------
struct JitterRange
{
    double ScaleMin = 0.85, ScaleMax = 1.20;
    /** Extra vertical stretch applied on top of the uniform scale, so a stand of the same
     * species is not a set of identical silhouettes uniformly resized. 1 disables it. */
    double HeightRatioMin = 1.0, HeightRatioMax = 1.0;
    double YawMinDegrees = 0.0, YawMaxDegrees = 360.0;
    /** Maximum lean off vertical. A tree on a slope leans a little; a shrub leans more. */
    double MaxTiltDegrees = 0.0;
    /** How much of the tilt follows the downhill direction rather than a random bearing.
     * 0 random lean, 1 always leans downhill (which looks wrong: real trees grow up). */
    double DownhillTiltFraction = 0.0;
};

struct InstanceTransform
{
    double XCm = 0.0, YCm = 0.0, ZCm = 0.0;
    double YawDegrees = 0.0, PitchDegrees = 0.0, RollDegrees = 0.0;
    double ScaleX = 1.0, ScaleY = 1.0, ScaleZ = 1.0;
};

/** Deterministic per-instance pose. Only Seed and Index enter the random draws, so the
 * same instance always looks the same however the list is batched or resumed. */
inline InstanceTransform MakeInstance(Vec2 P, double GroundZCm, const TerrainSample& S,
                                      const JitterRange& J, uint32_t Seed, uint32_t Index)
{
    InstanceTransform Out;
    Out.XCm = P.X;
    Out.YCm = P.Y;
    Out.ZCm = GroundZCm;
    const double Uniform = Clamp(0.5 * (J.ScaleMin + J.ScaleMax)
        + HashBell(Seed, Index, 1u) * (J.ScaleMax - J.ScaleMin) * 0.5, J.ScaleMin, J.ScaleMax);
    const double Height = HashRange(Seed, Index, 2u, J.HeightRatioMin, J.HeightRatioMax);
    Out.ScaleX = Uniform;
    Out.ScaleY = Uniform;
    Out.ScaleZ = Uniform * (Height > 0.0 ? Height : 1.0);
    Out.YawDegrees = HashRange(Seed, Index, 3u, J.YawMinDegrees, J.YawMaxDegrees);
    if (J.MaxTiltDegrees > 0.0)
    {
        const double Tilt = J.MaxTiltDegrees * std::sqrt(HashUnit(Seed, Index, 4u));
        const double G = std::sqrt(S.DzDx * S.DzDx + S.DzDy * S.DzDy);
        const double Downhill = G < 1e-9 ? 0.0 : RadToDeg(std::atan2(-S.DzDy, -S.DzDx));
        const double Random = HashRange(Seed, Index, 5u, 0.0, 360.0);
        const double Blend = Clamp(J.DownhillTiltFraction, 0.0, 1.0);
        const double Bearing = DegToRad(Random + Blend * (Downhill - Random));
        Out.PitchDegrees = Tilt * std::cos(Bearing);
        Out.RollDegrees = Tilt * std::sin(Bearing);
    }
    return Out;
}

// ---------------------------------------------------------------------------
// Poisson-disc scatter (Bridson 2007, "Fast Poisson Disk Sampling in Arbitrary
// Dimensions"), with the random source replaced by the deterministic hash above.
//
// The saturated Poisson set is generated FIRST, then thinned. That order matters: it is
// what lets a caller ask for a density well below saturation and still get a guaranteed
// minimum spacing, and it is what makes the realised density land on the requested value
// instead of on whatever the disc radius happens to imply.
// ---------------------------------------------------------------------------
struct ScatterRequest
{
    double MinXCm = 0.0, MinYCm = 0.0, MaxXCm = 0.0, MaxYCm = 0.0;
    /** Poisson radius: no two accepted points are ever closer than this. */
    double MinSpacingCm = 100.0;
    /** Requested plants per 100 m^2 of the request rectangle, BEFORE band, exclusion and
     * cluster filtering remove any. Set to 0 to keep the whole saturated set. */
    double DensityPer100SqM = 0.0;
    /** Hard cap, applied after everything else. 0 means no cap. */
    int MaxPoints = 0;
    /** Bridson's k. 30 is the paper's value and saturates well; lower is faster and
     * leaves more gaps. */
    int CandidatesPerPoint = 30;
    uint32_t Seed = 0;
};

struct ScatterStats
{
    int SaturatedCount = 0;      ///< Points the Poisson pass produced.
    int RequestedCount = 0;      ///< Points the requested density implies.
    int AcceptedCount = 0;       ///< Points that survived every filter.
    int RejectedByBand = 0;
    int RejectedByExclusion = 0;
    int RejectedByCluster = 0;
    int RejectedByCap = 0;
    double AreaSqCm = 0.0;
    double RealisedDensityPer100SqM = 0.0;
    bool SaturationLimited = false;
};

/** Saturated Poisson-disc point set over the request rectangle. Deterministic in Seed.
 * Returns an empty vector for a degenerate rectangle or a non-positive spacing. */
inline std::vector<Vec2> PoissonDisc(const ScatterRequest& R)
{
    std::vector<Vec2> Points;
    const double W = R.MaxXCm - R.MinXCm;
    const double H = R.MaxYCm - R.MinYCm;
    if (!(W > 0.0) || !(H > 0.0) || !(R.MinSpacingCm > 0.0)
        || !std::isfinite(W) || !std::isfinite(H) || !std::isfinite(R.MinSpacingCm))
    {
        return Points;
    }
    const int K = std::max(1, std::min(64, R.CandidatesPerPoint));
    const double Cell = R.MinSpacingCm / std::sqrt(2.0);
    const long long CellsX = static_cast<long long>(std::ceil(W / Cell)) + 1;
    const long long CellsY = static_cast<long long>(std::ceil(H / Cell)) + 1;
    // A grid larger than this means the caller asked for an unreasonable region/spacing
    // ratio; refusing beats allocating tens of gigabytes.
    if (CellsX <= 0 || CellsY <= 0 || CellsX * CellsY > 64000000LL) return Points;
    const int GX = static_cast<int>(CellsX);
    const int GY = static_cast<int>(CellsY);
    std::vector<int> Grid(static_cast<size_t>(GX) * GY, -1);

    auto CellIndex = [&](Vec2 P) {
        const int CX = ClampInt(static_cast<int>((P.X - R.MinXCm) / Cell), 0, GX - 1);
        const int CY = ClampInt(static_cast<int>((P.Y - R.MinYCm) / Cell), 0, GY - 1);
        return static_cast<size_t>(CY) * GX + CX;
    };
    auto FarEnough = [&](Vec2 P) {
        const int CX = ClampInt(static_cast<int>((P.X - R.MinXCm) / Cell), 0, GX - 1);
        const int CY = ClampInt(static_cast<int>((P.Y - R.MinYCm) / Cell), 0, GY - 1);
        const double RSq = R.MinSpacingCm * R.MinSpacingCm;
        for (int Y = std::max(0, CY - 2); Y <= std::min(GY - 1, CY + 2); ++Y)
        {
            for (int X = std::max(0, CX - 2); X <= std::min(GX - 1, CX + 2); ++X)
            {
                const int Index = Grid[static_cast<size_t>(Y) * GX + X];
                if (Index >= 0 && DistanceSquared(Points[static_cast<size_t>(Index)], P) < RSq) return false;
            }
        }
        return true;
    };

    uint32_t Draw = 0;
    std::vector<int> Active;
    const Vec2 First{R.MinXCm + W * HashUnit(R.Seed, Draw++, 7u),
                     R.MinYCm + H * HashUnit(R.Seed, Draw++, 7u)};
    Points.push_back(First);
    Grid[CellIndex(First)] = 0;
    Active.push_back(0);

    while (!Active.empty())
    {
        // Deterministic pick from the active list (Bridson picks uniformly at random).
        const size_t Slot = static_cast<size_t>(HashUnit(R.Seed, Draw++, 8u) * Active.size());
        const size_t Pick = std::min(Slot, Active.size() - 1);
        const Vec2 Origin = Points[static_cast<size_t>(Active[Pick])];
        bool Placed = false;
        for (int Attempt = 0; Attempt < K; ++Attempt)
        {
            const double Angle = 2.0 * Pi * HashUnit(R.Seed, Draw++, 9u);
            // sqrt keeps the annulus sample area-uniform between r and 2r.
            const double Radius = R.MinSpacingCm * std::sqrt(1.0 + 3.0 * HashUnit(R.Seed, Draw++, 10u));
            const Vec2 Candidate{Origin.X + Radius * std::cos(Angle), Origin.Y + Radius * std::sin(Angle)};
            if (Candidate.X < R.MinXCm || Candidate.X >= R.MaxXCm
                || Candidate.Y < R.MinYCm || Candidate.Y >= R.MaxYCm) continue;
            if (!FarEnough(Candidate)) continue;
            Grid[CellIndex(Candidate)] = static_cast<int>(Points.size());
            Active.push_back(static_cast<int>(Points.size()));
            Points.push_back(Candidate);
            Placed = true;
            break;
        }
        if (!Placed)
        {
            Active[Pick] = Active.back();
            Active.pop_back();
        }
    }
    return Points;
}

/** What a caller supplies to turn the saturated set into a species' actual planting. */
struct ScatterFilters
{
    const HeightField* Terrain = nullptr;
    Band SpeciesBand;
    const ExclusionSet* Exclusions = nullptr;
    /** Crown radius added to every exclusion primitive for this species. */
    double CrownRadiusCm = 0.0;
    ClusterField Clusters;
    TerraceField Terraces;
    JitterRange Jitter;
    /** Vertical offset applied to the sampled ground height, e.g. to sink a trunk flare
     * a little below the surface so no gap shows on a slope. */
    double GroundOffsetCm = 0.0;
};

/** The whole pipeline: Poisson -> deterministic shuffle -> band, exclusion and cluster
 * acceptance -> terrace snap -> density cap -> per-instance jitter.
 *
 * Order note: the density cap is applied to points that already passed the filters, so a
 * species whose band covers only part of the rectangle still reaches its requested density
 * inside that part rather than being thinned twice.
 */
inline std::vector<InstanceTransform> Scatter(const ScatterRequest& R, const ScatterFilters& F,
                                              ScatterStats* StatsOut = nullptr)
{
    std::vector<InstanceTransform> Out;
    ScatterStats Stats;
    Stats.AreaSqCm = std::max(0.0, (R.MaxXCm - R.MinXCm)) * std::max(0.0, (R.MaxYCm - R.MinYCm));

    const std::vector<Vec2> Candidates = PoissonDisc(R);
    Stats.SaturatedCount = static_cast<int>(Candidates.size());
    if (Candidates.empty())
    {
        if (StatsOut) *StatsOut = Stats;
        return Out;
    }

    // Requested count from the density. Rounding is nearest so a half plant does not
    // systematically bias a large tiled region low.
    int Target = R.DensityPer100SqM > 0.0
        ? static_cast<int>(std::floor(R.DensityPer100SqM * Stats.AreaSqCm / SquareCmPer100SqM + 0.5))
        : Stats.SaturatedCount;
    if (R.MaxPoints > 0) Target = std::min(Target, R.MaxPoints);
    Stats.RequestedCount = Target;
    if (Target <= 0)
    {
        if (StatsOut) *StatsOut = Stats;
        return Out;
    }

    // Deterministic visiting order. Sorting by a hash of the point's own index gives the
    // same permutation for the same seed on every platform, without std::shuffle's
    // implementation-defined engine.
    std::vector<uint32_t> Order(Candidates.size());
    for (size_t I = 0; I < Order.size(); ++I) Order[I] = static_cast<uint32_t>(I);
    std::stable_sort(Order.begin(), Order.end(), [&](uint32_t A, uint32_t B) {
        const uint32_t HA = HashCombine(R.Seed ^ 0x5bf03635u, A);
        const uint32_t HB = HashCombine(R.Seed ^ 0x5bf03635u, B);
        return HA != HB ? HA < HB : A < B;
    });

    for (uint32_t Index : Order)
    {
        if (static_cast<int>(Out.size()) >= Target)
        {
            ++Stats.RejectedByCap;
            continue;
        }
        Vec2 P = Candidates[Index];
        TerrainSample S;
        double Weight = 1.0;
        if (F.Terrain != nullptr && F.Terrain->Valid())
        {
            S = SampleTerrain(*F.Terrain, P);
            Weight = BandWeight(F.SpeciesBand, S, Concavity(*F.Terrain, P));
            if (Weight <= 0.0 || HashUnit(R.Seed, Index, 21u) >= Weight)
            {
                ++Stats.RejectedByBand;
                continue;
            }
        }
        const double Cluster = ClusterWeight(F.Clusters, P);
        if (Cluster < 1.0 && HashUnit(R.Seed, Index, 22u) >= Cluster)
        {
            ++Stats.RejectedByCluster;
            continue;
        }
        // Terracing moves the point, so exclusion is tested on the FINAL position; a tree
        // snapped onto a bench must not end up inside a building that the pre-snap point
        // cleared.
        P = SnapToTerrace(F.Terraces, S, P, Index);
        if (F.Exclusions != nullptr && IsExcluded(*F.Exclusions, P, F.CrownRadiusCm))
        {
            ++Stats.RejectedByExclusion;
            continue;
        }
        double GroundZ = F.GroundOffsetCm;
        if (F.Terrain != nullptr && F.Terrain->Valid())
        {
            S = SampleTerrain(*F.Terrain, P);            // re-sample after the snap
            GroundZ += S.HeightCm;
        }
        Out.push_back(MakeInstance(P, GroundZ, S, F.Jitter, R.Seed, Index));
    }

    Stats.AcceptedCount = static_cast<int>(Out.size());
    Stats.SaturationLimited = Stats.AcceptedCount < Target;
    Stats.RealisedDensityPer100SqM = Stats.AreaSqCm > 0.0
        ? Stats.AcceptedCount * SquareCmPer100SqM / Stats.AreaSqCm : 0.0;
    if (StatsOut) *StatsOut = Stats;
    return Out;
}

/** Smallest distance between any two instances, or -1 for fewer than two. O(n^2) on a
 * flat list and O(n) per cell on the grid variant below; this one exists so a test can
 * assert the spacing invariant without trusting the accelerator. */
inline double MinimumSpacing(const std::vector<InstanceTransform>& Instances)
{
    if (Instances.size() < 2) return -1.0;
    double Best = 1.0e300;
    for (size_t I = 1; I < Instances.size(); ++I)
    {
        for (size_t J = 0; J < I; ++J)
        {
            const double DX = Instances[I].XCm - Instances[J].XCm;
            const double DY = Instances[I].YCm - Instances[J].YCm;
            Best = std::min(Best, DX * DX + DY * DY);
        }
    }
    return std::sqrt(Best);
}

/** Uniform-grid minimum spacing, for lists too long for the quadratic form. Same answer,
 * O(n) memory. Each point is compared against the 3x3 cell neighbourhood, and each pair
 * exactly once (B > A). */
inline double MinimumSpacingFast(const std::vector<InstanceTransform>& Instances, double CellCm)
{
    const size_t N = Instances.size();
    if (N < 2) return -1.0;
    if (!(CellCm > 0.0)) return MinimumSpacing(Instances);
    double MinX = 1e300, MinY = 1e300, MaxX = -1e300, MaxY = -1e300;
    for (const InstanceTransform& T : Instances)
    {
        if (!std::isfinite(T.XCm) || !std::isfinite(T.YCm)) return MinimumSpacing(Instances);
        MinX = std::min(MinX, T.XCm); MaxX = std::max(MaxX, T.XCm);
        MinY = std::min(MinY, T.YCm); MaxY = std::max(MaxY, T.YCm);
    }
    const long long GX = static_cast<long long>((MaxX - MinX) / CellCm) + 1;
    const long long GY = static_cast<long long>((MaxY - MinY) / CellCm) + 1;
    if (GX <= 0 || GY <= 0 || GX * GY > 16000000LL) return MinimumSpacing(Instances);
    std::vector<std::vector<int>> Cells(static_cast<size_t>(GX * GY));
    std::vector<long long> Cell(N);
    for (size_t I = 0; I < N; ++I)
    {
        const long long CX = ClampLong(static_cast<long long>((Instances[I].XCm - MinX) / CellCm), 0LL, GX - 1);
        const long long CY = ClampLong(static_cast<long long>((Instances[I].YCm - MinY) / CellCm), 0LL, GY - 1);
        Cell[I] = CY * GX + CX;
        Cells[static_cast<size_t>(Cell[I])].push_back(static_cast<int>(I));
    }
    double Best = 1.0e300;
    for (size_t A = 0; A < N; ++A)
    {
        const long long CX = Cell[A] % GX;
        const long long CY = Cell[A] / GX;
        for (long long NY = std::max(0LL, CY - 1); NY <= std::min(GY - 1, CY + 1); ++NY)
        {
            for (long long NX = std::max(0LL, CX - 1); NX <= std::min(GX - 1, CX + 1); ++NX)
            {
                for (int B : Cells[static_cast<size_t>(NY * GX + NX)])
                {
                    if (static_cast<size_t>(B) <= A) continue;
                    const double DX = Instances[A].XCm - Instances[static_cast<size_t>(B)].XCm;
                    const double DY = Instances[A].YCm - Instances[static_cast<size_t>(B)].YCm;
                    Best = std::min(Best, DX * DX + DY * DY);
                }
            }
        }
    }
    return Best >= 1.0e300 ? MinimumSpacing(Instances) : std::sqrt(Best);
}

// ---------------------------------------------------------------------------
// Level-of-detail and draw budget. These are the numbers the release script uses to
// justify the instance cap, kept here so the budget is testable rather than asserted.
// ---------------------------------------------------------------------------
struct LodStep
{
    double ScreenSizeStartCm = 0.0;   ///< Distance at which this LOD takes over.
    int Triangles = 0;
};

/** Which LOD a given distance falls in. Steps must be ordered near to far. */
inline int LodForDistance(const LodStep* Steps, int Count, double DistanceCm)
{
    if (Steps == nullptr || Count <= 0 || !std::isfinite(DistanceCm)) return 0;
    int Chosen = 0;
    for (int I = 0; I < Count; ++I)
    {
        if (DistanceCm >= Steps[I].ScreenSizeStartCm) Chosen = I;
    }
    return Chosen;
}

/** Expected triangles from N instances uniformly spread over a disc of CullRadiusCm,
 * viewed from its centre. This is the arithmetic behind the instance budget: it converts
 * "how many plants are placed" into "how many triangles a frame draws". */
inline double ExpectedTrianglesPerFrame(int Instances, double AreaSqCm, double CullRadiusCm,
                                        const LodStep* Steps, int Count, double VisibleFraction)
{
    if (Instances <= 0 || Steps == nullptr || Count <= 0 || AreaSqCm <= 0.0 || CullRadiusCm <= 0.0) return 0.0;
    const double Density = Instances / AreaSqCm;
    double Total = 0.0;
    for (int I = 0; I < Count; ++I)
    {
        const double Inner = Steps[I].ScreenSizeStartCm;
        const double Outer = I + 1 < Count ? Steps[I + 1].ScreenSizeStartCm : CullRadiusCm;
        if (Outer <= Inner) continue;
        const double Ring = Pi * (std::min(Outer, CullRadiusCm) * std::min(Outer, CullRadiusCm) - Inner * Inner);
        if (Ring <= 0.0) continue;
        Total += Ring * Density * Steps[I].Triangles;
    }
    return Total * Clamp(VisibleFraction, 0.0, 1.0);
}

}   // namespace MikdashScatter
