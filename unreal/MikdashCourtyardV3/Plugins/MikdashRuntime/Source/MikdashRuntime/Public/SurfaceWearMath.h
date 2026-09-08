#pragma once
#include <cmath>
#include <cstddef>

// Engine-independent surface-wear arithmetic, shared by AMikdashSurfaceDetail, the
// offline decal planner (Scripts/create_decals.py mirrors these formulas) and the
// standalone test (Tests/SurfaceWearMathTest.cpp). No Unreal, no allocation, no
// global state and no <random>: every "random" value comes from an explicit seed, so
// a given seed always reproduces the same field.
//
// Units: centimetres, days, years, millimetres of annual rainfall. All coverage,
// polish and weathering outputs are fractions in [0,1]. Nothing here is a
// measurement of the historical Mikdash; the constants are an artistic weathering
// model for Jerusalem limestone (meleke) on a building that is maintained daily and
// used heavily, so it models the wear of use and weather, not decay.
namespace MikdashWear
{

// ---------------------------------------------------------------------------
// Deterministic hashing. The only source of variation in this header.
// ---------------------------------------------------------------------------

/** Murmur3 32-bit finalizer. Pure function of the input; no hidden state. */
inline unsigned int Hash32(unsigned int Value)
{
    Value ^= Value >> 16;
    Value *= 0x85ebca6bu;
    Value ^= Value >> 13;
    Value *= 0xc2b2ae35u;
    Value ^= Value >> 16;
    return Value;
}

/** Deterministic value in [0,1) from a seed and an index. Same inputs, same output,
 * in every build configuration. */
inline double Hash01(unsigned int Seed, unsigned int Index)
{
    const unsigned int Mixed = Hash32(Seed * 0x9e3779b9u + Hash32(Index + 0x7f4a7c15u));
    return static_cast<double>(Mixed) * (1.0 / 4294967296.0);
}

/** Deterministic value in [-1,1]. */
inline double HashSigned(unsigned int Seed, unsigned int Index)
{
    return Hash01(Seed, Index) * 2.0 - 1.0;
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

inline double Clamp01(double Value)
{
    if (!(Value > 0.0)) return 0.0;   // also maps NaN to 0
    return Value < 1.0 ? Value : 1.0;
}

inline double ClampRange(double Value, double Low, double High)
{
    if (!(Value > Low)) return Low;
    return Value < High ? Value : High;
}

/** Hermite smoothstep from 1 at Edge0 down to 0 at Edge1 (Edge1 > Edge0). */
inline double SmoothFalloff(double Value, double Edge0, double Edge1)
{
    if (!(Edge1 > Edge0)) return Value <= Edge0 ? 1.0 : 0.0;
    const double T = Clamp01((Value - Edge0) / (Edge1 - Edge0));
    return 1.0 - T * T * (3.0 - 2.0 * T);
}

// ---------------------------------------------------------------------------
// Routes: the walked centre lines
// ---------------------------------------------------------------------------

struct FPoint2
{
    double X;
    double Y;
};

/** One walked route. Points are a world-XY polyline in centimetres.
 * TripsPerDay is the traffic the route carries; HalfWidthCm is the half width of the
 * fully-worn band either side of the centre line, and FeatherCm the distance beyond
 * that over which wear falls to exactly zero. */
struct FRoute
{
    const FPoint2* Points;
    int            Count;
    double         HalfWidthCm;
    double         FeatherCm;
    double         TripsPerDay;
};

/** Squared distance from (Px,Py) to segment AB; OutT (may be null) receives the
 * clamped parametric position of the closest point on the segment. */
inline double SegmentDistanceSq(double Px, double Py, double Ax, double Ay,
                                double Bx, double By, double* OutT = nullptr)
{
    const double Dx = Bx - Ax;
    const double Dy = By - Ay;
    const double LengthSq = Dx * Dx + Dy * Dy;
    double T = 0.0;
    if (LengthSq > 0.0)
    {
        T = Clamp01(((Px - Ax) * Dx + (Py - Ay) * Dy) / LengthSq);
    }
    const double Cx = Ax + Dx * T - Px;
    const double Cy = Ay + Dy * T - Py;
    if (OutT) *OutT = T;
    return Cx * Cx + Cy * Cy;
}

/** Perpendicular distance in centimetres from a point to a route centre line.
 * A route with no usable points is infinitely far away, never zero: an empty route
 * must not read as "you are standing on it". */
inline double DistanceToRoute(double Px, double Py, const FRoute& Route)
{
    if (!Route.Points || Route.Count <= 0) return HUGE_VAL;
    if (Route.Count == 1)
    {
        const double Dx = Route.Points[0].X - Px;
        const double Dy = Route.Points[0].Y - Py;
        return std::sqrt(Dx * Dx + Dy * Dy);
    }
    double Best = HUGE_VAL;
    for (int Index = 0; Index + 1 < Route.Count; ++Index)
    {
        const double DistanceSq = SegmentDistanceSq(Px, Py,
            Route.Points[Index].X, Route.Points[Index].Y,
            Route.Points[Index + 1].X, Route.Points[Index + 1].Y);
        if (DistanceSq < Best) Best = DistanceSq;
    }
    return std::sqrt(Best);
}

/** Wear falloff from a path centre line: exactly 1 inside HalfWidthCm, smoothly to
 * exactly 0 at HalfWidthCm + FeatherCm, and 0 beyond. Monotonically non-increasing
 * in DistanceCm, so wear can never be higher off the route than on it. */
inline double WearFalloff(double DistanceCm, double HalfWidthCm, double FeatherCm)
{
    if (!(DistanceCm == DistanceCm)) return 0.0;         // NaN
    if (DistanceCm <= HalfWidthCm) return 1.0;
    return SmoothFalloff(DistanceCm, HalfWidthCm,
                         HalfWidthCm + (FeatherCm > 0.0 ? FeatherCm : 0.0));
}

/** Traffic converging at a point, in trips per day, summed over every route that
 * reaches it. Where routes meet -- a gate mouth, the foot of a stair -- the sums add,
 * which is exactly why those places wear first. */
inline double TrafficDensity(double Px, double Py, const FRoute* Routes, int RouteCount)
{
    double Total = 0.0;
    if (!Routes) return 0.0;
    for (int Index = 0; Index < RouteCount; ++Index)
    {
        const FRoute& Route = Routes[Index];
        if (!(Route.TripsPerDay > 0.0)) continue;
        Total += Route.TripsPerDay * WearFalloff(DistanceToRoute(Px, Py, Route),
                                                 Route.HalfWidthCm, Route.FeatherCm);
    }
    return Total;
}

/** Saturating foot polish in [0,1) from traffic and elapsed years. Stone stops
 * getting visibly more polished long before it wears away, so this approaches but
 * never reaches 1. HalfTripDays is the trips*days product at which polish is one
 * half. */
inline double FootPolish(double TripsPerDay, double Years, double HalfTripDays = 4.0e6)
{
    if (!(TripsPerDay > 0.0) || !(Years > 0.0) || !(HalfTripDays > 0.0)) return 0.0;
    const double Exposure = TripsPerDay * Years * 365.25;
    return Clamp01(Exposure / (Exposure + HalfTripDays));
}

// ---------------------------------------------------------------------------
// Traffic accumulation onto a grid: deterministic for a seed
// ---------------------------------------------------------------------------

/** A plain XY accumulation grid. The caller owns Cells (NumX * NumY doubles). */
struct FWearGrid
{
    double* Cells;
    int     NumX;
    int     NumY;
    double  MinX;
    double  MinY;
    double  CellCm;
};

inline void ClearGrid(FWearGrid& Grid)
{
    if (!Grid.Cells) return;
    const int Total = Grid.NumX * Grid.NumY;
    for (int Index = 0; Index < Total; ++Index) Grid.Cells[Index] = 0.0;
}

inline double GridValue(const FWearGrid& Grid, double X, double Y)
{
    if (!Grid.Cells || !(Grid.CellCm > 0.0)) return 0.0;
    const int Ix = static_cast<int>(std::floor((X - Grid.MinX) / Grid.CellCm));
    const int Iy = static_cast<int>(std::floor((Y - Grid.MinY) / Grid.CellCm));
    if (Ix < 0 || Iy < 0 || Ix >= Grid.NumX || Iy >= Grid.NumY) return 0.0;
    return Grid.Cells[Iy * Grid.NumX + Ix];
}

/** Walk Walkers notional feet along the route, each with a lateral lane offset and a
 * per-step wobble drawn deterministically from Seed, and add their footfalls to the
 * grid. Two calls with the same seed, route and grid geometry produce bit-identical
 * cells. The lane bias is what makes traffic wear a band rather than a hairline. */
inline void AccumulateRoute(FWearGrid& Grid, const FRoute& Route, int Walkers, unsigned int Seed)
{
    if (!Grid.Cells || !(Grid.CellCm > 0.0)) return;
    if (!Route.Points || Route.Count < 2 || Walkers <= 0) return;

    double Length = 0.0;
    for (int Index = 0; Index + 1 < Route.Count; ++Index)
    {
        const double Dx = Route.Points[Index + 1].X - Route.Points[Index].X;
        const double Dy = Route.Points[Index + 1].Y - Route.Points[Index].Y;
        Length += std::sqrt(Dx * Dx + Dy * Dy);
    }
    if (!(Length > 0.0)) return;

    const int Steps = static_cast<int>(Length / (Grid.CellCm * 0.5)) + 2;
    const double PerFootfall = Route.TripsPerDay
                             / (static_cast<double>(Walkers) * static_cast<double>(Steps));

    for (int Walker = 0; Walker < Walkers; ++Walker)
    {
        const unsigned int WalkerSeed = Hash32(Seed + static_cast<unsigned int>(Walker) * 2654435761u);
        const double Lane = HashSigned(WalkerSeed, 0u) * Route.HalfWidthCm * 0.7;
        for (int Step = 0; Step < Steps; ++Step)
        {
            const double S = (static_cast<double>(Step) + 0.5) / static_cast<double>(Steps) * Length;

            double Travelled = 0.0;
            int    Segment   = 0;
            double T         = 0.0;
            for (; Segment + 2 < Route.Count; ++Segment)
            {
                const double Ex = Route.Points[Segment + 1].X - Route.Points[Segment].X;
                const double Ey = Route.Points[Segment + 1].Y - Route.Points[Segment].Y;
                const double SegmentLength = std::sqrt(Ex * Ex + Ey * Ey);
                if (Travelled + SegmentLength >= S) break;
                Travelled += SegmentLength;
            }
            const double Ax = Route.Points[Segment].X;
            const double Ay = Route.Points[Segment].Y;
            const double Bx = Route.Points[Segment + 1].X;
            const double By = Route.Points[Segment + 1].Y;
            const double Dx = Bx - Ax;
            const double Dy = By - Ay;
            const double SegmentLength = std::sqrt(Dx * Dx + Dy * Dy);
            if (!(SegmentLength > 0.0)) continue;
            T = Clamp01((S - Travelled) / SegmentLength);

            const double Nx = -Dy / SegmentLength;
            const double Ny =  Dx / SegmentLength;
            const double Wobble = HashSigned(WalkerSeed, static_cast<unsigned int>(Step) + 1u)
                                * Route.HalfWidthCm * 0.25;
            const double Px = Ax + Dx * T + Nx * (Lane + Wobble);
            const double Py = Ay + Dy * T + Ny * (Lane + Wobble);

            const int Ix = static_cast<int>(std::floor((Px - Grid.MinX) / Grid.CellCm));
            const int Iy = static_cast<int>(std::floor((Py - Grid.MinY) / Grid.CellCm));
            if (Ix < 0 || Iy < 0 || Ix >= Grid.NumX || Iy >= Grid.NumY) continue;
            Grid.Cells[Iy * Grid.NumX + Ix] += PerFootfall;
        }
    }
}

// ---------------------------------------------------------------------------
// Rain streaking below ledges
// ---------------------------------------------------------------------------

/** Reference annual rainfall for Jerusalem, mm. Streak lengths scale against it. */
const double JerusalemRainfallMm = 550.0;

/** How far below a ledge the dirty runoff streaks reach, in centimetres.
 *
 *   DropHeightCm      free wall face below the ledge; a streak cannot outrun the wall
 *   ProjectionCm      how far the ledge stands proud. A deep cornice throws water
 *                     clear of the face and protects it, so streaking falls off as
 *                     projection grows -- which is why the deep Ulam cornice streaks
 *                     far less than a thin string course of the same height
 *   AnnualRainfallMm  local rainfall; more rain, longer wash
 *   ExposureFraction  0 fully sheltered, 1 fully open to the weather
 *
 * Always in [0, DropHeightCm], and exactly 0 with no rain, no exposure or no wall. */
inline double StreakLengthCm(double DropHeightCm, double ProjectionCm,
                             double AnnualRainfallMm, double ExposureFraction)
{
    if (!(DropHeightCm > 0.0) || !(AnnualRainfallMm > 0.0)) return 0.0;
    const double Exposure = Clamp01(ExposureFraction);
    if (!(Exposure > 0.0)) return 0.0;
    const double RainFactor = std::sqrt(AnnualRainfallMm / JerusalemRainfallMm);
    const double ThrowOff   = std::exp(-ClampRange(ProjectionCm, 0.0, 1.0e6) / 25.0);
    const double Unbounded  = 260.0 * Exposure * RainFactor * ThrowOff;
    return ClampRange(Unbounded, 0.0, DropHeightCm);
}

// ---------------------------------------------------------------------------
// Weathering and lichen
// ---------------------------------------------------------------------------

/** General weathering fraction: exposed old stone weathers, sheltered or new stone
 * does not. Exactly 0 at AgeYears <= 0 or ExposureFraction <= 0, and strictly below
 * 1 for any finite age. */
inline double Weathering(double ExposureFraction, double AgeYears,
                         double AnnualRainfallMm = JerusalemRainfallMm)
{
    const double Exposure = Clamp01(ExposureFraction);
    if (!(Exposure > 0.0) || !(AgeYears > 0.0) || !(AnnualRainfallMm > 0.0)) return 0.0;
    const double RainFactor = std::sqrt(AnnualRainfallMm / JerusalemRainfallMm);
    const double TimeConstantYears = 120.0 / (Exposure * RainFactor);
    return Clamp01(1.0 - std::exp(-AgeYears / TimeConstantYears));
}

/** Lichen coverage fraction. Lichen needs time, moisture and shade: none grows on a
 * wall dressed last season, on a face that never gets wet, or on one in full sun all
 * day. Exactly 0 at or below SettleYears, so newly built stonework carries none. */
inline double LichenCoverage(double ExposureFraction, double ShadeFraction, double AgeYears,
                             double AnnualRainfallMm = JerusalemRainfallMm,
                             double SettleYears = 5.0)
{
    const double Exposure = Clamp01(ExposureFraction);
    const double Shade    = Clamp01(ShadeFraction);
    if (!(AgeYears > SettleYears) || !(Exposure > 0.0) || !(Shade > 0.0)) return 0.0;
    if (!(AnnualRainfallMm > 0.0)) return 0.0;
    const double Moisture = Clamp01(AnnualRainfallMm / (JerusalemRainfallMm * 1.6));
    const double Settled  = Weathering(Exposure, AgeYears - SettleYears, AnnualRainfallMm);
    // Ceiling of 0.45: even a very old shaded wall in Jerusalem is patchy, not green.
    return Clamp01(0.45 * Settled * Shade * Moisture);
}

// ---------------------------------------------------------------------------
// Per-instance stone variation (meleke)
// ---------------------------------------------------------------------------

/** Multiplicative tint and roughness scale for one ashlar instance. Applied to a
 * material INSTANCE parented on the shared limestone instance; the shared parent
 * itself is never edited. */
struct FStoneVariation
{
    double TintR;
    double TintG;
    double TintB;
    double RoughnessScale;
};

/** Deterministic per-instance jitter. Fresh meleke is near-white; it yellows and
 * dulls with weathering, so the age term pushes red up, blue down and roughness up.
 * Every field is clamped into a believable band: tints in [0.88,1.14] and roughness
 * scale in [0.82,1.20]. Index identifies the instance (a hash of its component
 * name); Seed identifies the whole pass. */
inline FStoneVariation StoneVariation(unsigned int Seed, unsigned int Index,
                                      double WeatheringFraction)
{
    const double Age   = Clamp01(WeatheringFraction);
    const double Value = HashSigned(Seed, Index * 3u + 0u);      // overall lightness
    const double Warm  = HashSigned(Seed, Index * 3u + 1u);      // warm / cool cast
    const double Rough = HashSigned(Seed, Index * 3u + 2u);

    const double Lightness = 1.0 + Value * 0.055 - Age * 0.030;
    FStoneVariation Out;
    Out.TintR = ClampRange(Lightness * (1.0 + Warm * 0.020 + Age * 0.055), 0.88, 1.14);
    Out.TintG = ClampRange(Lightness * (1.0 + Warm * 0.008 + Age * 0.022), 0.88, 1.14);
    Out.TintB = ClampRange(Lightness * (1.0 - Warm * 0.024 - Age * 0.060), 0.88, 1.14);
    Out.RoughnessScale = ClampRange(1.0 + Rough * 0.090 + Age * 0.080, 0.82, 1.20);
    return Out;
}

/** Polished stone is smoother, never mirror-bright. Returns the roughness scale to
 * multiply into an already-jittered value. */
inline double PolishRoughnessScale(double PolishFraction)
{
    return ClampRange(1.0 - 0.42 * Clamp01(PolishFraction), 0.58, 1.0);
}

// ---------------------------------------------------------------------------
// Distance fade and decal scoring
// ---------------------------------------------------------------------------

/** 1 inside FadeStartCm, 0 at and beyond FadeEndCm, smooth between. */
inline double DistanceFade(double DistanceCm, double FadeStartCm, double FadeEndCm)
{
    if (!(DistanceCm == DistanceCm)) return 0.0;
    if (DistanceCm <= FadeStartCm) return 1.0;
    return SmoothFalloff(DistanceCm, FadeStartCm, FadeEndCm);
}

/** Selection score for one decal: how much it matters, scaled by how visible it is.
 * Always in [0, Importance]; a decal past its fade end scores exactly 0 and can
 * therefore never displace a visible one. */
inline double DecalScore(double Importance, double DistanceCm,
                         double FadeStartCm, double FadeEndCm)
{
    if (!(Importance > 0.0)) return 0.0;
    return Importance * DistanceFade(DistanceCm, FadeStartCm, FadeEndCm);
}

// ---------------------------------------------------------------------------
// Budget allocator
// ---------------------------------------------------------------------------

/** One category asking for decals. Minimum is a request, not a promise: the cap
 * always wins. */
struct FBudgetRequest
{
    double Weight;      // relative share of whatever is left after the minimums
    int    Requested;   // never allocate more than this
    int    Minimum;     // honoured first, but clipped if the minimums exceed the cap
};

/** Allocate at most Cap decals across Count categories, writing per-category counts
 * to OutCounts and returning the total allocated.
 *
 * Guarantees, in this order:
 *   1. the returned total is <= Cap, always, for every input including absurd ones;
 *   2. OutCounts[i] lies in [0, Requested[i]];
 *   3. the result is a pure function of the inputs (largest remainder, ties to the
 *      lower index), so two runs of the same plan allocate identically. */
inline int AllocateBudget(const FBudgetRequest* Items, int Count, int Cap, int* OutCounts)
{
    if (!OutCounts || Count <= 0) return 0;
    for (int Index = 0; Index < Count; ++Index) OutCounts[Index] = 0;
    if (!Items || Cap <= 0) return 0;

    int Remaining = Cap;

    // Pass 1: minimums, in index order, each clipped by the request and by what is
    // left. If the minimums oversubscribe the cap the later categories get less; the
    // cap is never broken to satisfy a minimum.
    for (int Index = 0; Index < Count && Remaining > 0; ++Index)
    {
        int Want = Items[Index].Minimum;
        if (Want < 0) Want = 0;
        if (Want > Items[Index].Requested) Want = Items[Index].Requested;
        if (Want > Remaining) Want = Remaining;
        OutCounts[Index] = Want;
        Remaining -= Want;
    }

    // Pass 2: share the remainder by weight over the unmet demand.
    double TotalWeight = 0.0;
    for (int Index = 0; Index < Count; ++Index)
    {
        const int Unmet = Items[Index].Requested - OutCounts[Index];
        if (Unmet > 0 && Items[Index].Weight > 0.0) TotalWeight += Items[Index].Weight;
    }
    if (TotalWeight > 0.0 && Remaining > 0)
    {
        const int Share = Remaining;
        for (int Index = 0; Index < Count; ++Index)
        {
            const int Unmet = Items[Index].Requested - OutCounts[Index];
            if (Unmet <= 0 || !(Items[Index].Weight > 0.0)) continue;
            const double Ideal = static_cast<double>(Share) * Items[Index].Weight / TotalWeight;
            int Give = static_cast<int>(std::floor(Ideal));
            if (Give > Unmet)      Give = Unmet;
            if (Give > Remaining)  Give = Remaining;
            if (Give < 0)          Give = 0;
            OutCounts[Index] += Give;
            Remaining -= Give;
        }
        // Largest-remainder top-up, one unit at a time; the lowest index wins a tie.
        while (Remaining > 0)
        {
            int    Best      = -1;
            double BestValue = -1.0;
            for (int Index = 0; Index < Count; ++Index)
            {
                const int Unmet = Items[Index].Requested - OutCounts[Index];
                if (Unmet <= 0 || !(Items[Index].Weight > 0.0)) continue;
                const double Ideal     = static_cast<double>(Share) * Items[Index].Weight / TotalWeight;
                const double Remainder = Ideal - std::floor(Ideal);
                if (Remainder > BestValue + 1e-12)
                {
                    BestValue = Remainder;
                    Best      = Index;
                }
            }
            if (Best < 0) break;                    // nobody can take another one
            OutCounts[Best] += 1;
            Remaining -= 1;
        }
    }

    int Total = 0;
    for (int Index = 0; Index < Count; ++Index) Total += OutCounts[Index];
    return Total;
}

} // namespace MikdashWear
