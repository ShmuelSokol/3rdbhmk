#pragma once
#include <cmath>

// Dependency-free, explicitly selected conversions. Adding this header does NOT
// change the active map, existing defaults, save decoding or geographic imports.
namespace MikdashUnits
{
constexpr double LegacyArchitectureCmPerAmah = 50.0;
constexpr double SelectedBookCmPerAmah = 48.0;
constexpr double LegacyArchitectureToSelectedFactor = SelectedBookCmPerAmah / LegacyArchitectureCmPerAmah;

struct PointCm
{
    double X = 0.0, Y = 0.0, Z = 0.0;
};
inline bool IsFinite(const PointCm& Point)
{
    return std::isfinite(Point.X) && std::isfinite(Point.Y) && std::isfinite(Point.Z);
}
constexpr double LegacyArchitectureAmotToCm(double Amot) { return Amot * LegacyArchitectureCmPerAmah; }
constexpr double SelectedBookAmotToCm(double Amot) { return Amot * SelectedBookCmPerAmah; }
constexpr double LegacyArchitectureCmToSelectedCm(double Cm) { return Cm * LegacyArchitectureToSelectedFactor; }
constexpr double SelectedBookTefachimToCm(double Tefachim) { return Tefachim * (SelectedBookCmPerAmah / 6.0); }
constexpr double SelectedFiveTefachAmotToCm(double Amot) { return Amot * (SelectedBookCmPerAmah * 5.0 / 6.0); }

// Input/output are native world-centimetre axes, not source X-east/Y-up/Z-south.
// Caller supplies the confirmed fixed world origin; a nonzero anchor stays fixed.
// Output is unchanged on invalid input or arithmetic overflow.
inline bool TryScaleLegacyArchitecturePoint(const PointCm& LegacyPoint, const PointCm& FixedOrigin, PointCm& Output)
{
    if (!IsFinite(LegacyPoint) || !IsFinite(FixedOrigin)) return false;
    const PointCm Candidate{
        FixedOrigin.X + (LegacyPoint.X-FixedOrigin.X)*LegacyArchitectureToSelectedFactor,
        FixedOrigin.Y + (LegacyPoint.Y-FixedOrigin.Y)*LegacyArchitectureToSelectedFactor,
        FixedOrigin.Z + (LegacyPoint.Z-FixedOrigin.Z)*LegacyArchitectureToSelectedFactor};
    if (!IsFinite(Candidate)) return false;
    Output = Candidate; return true;
}

// Geometry support point migrates; capsule centre, eye or other physical offset
// retains its real-world centimetres. Do not scale the already-offset actor point.
inline bool TryPlaceAboveMigratedFloor(const PointCm& LegacyFloor, const PointCm& FixedOrigin,
                                      double PhysicalHeightCm, PointCm& Output)
{
    if (!std::isfinite(PhysicalHeightCm) || PhysicalHeightCm < 0.0) return false;
    PointCm Candidate;
    if (!TryScaleLegacyArchitecturePoint(LegacyFloor, FixedOrigin, Candidate)) return false;
    Candidate.Z += PhysicalHeightCm;
    if (!IsFinite(Candidate)) return false;
    Output = Candidate; return true;
}

// For already-migrated support points; no architecture scaling occurs here.
inline bool TryPlaceAboveFloor(const PointCm& Floor, double PhysicalHeightCm, PointCm& Output)
{
    if (!IsFinite(Floor) || !std::isfinite(PhysicalHeightCm) || PhysicalHeightCm < 0.0) return false;
    const PointCm Candidate{Floor.X, Floor.Y, Floor.Z + PhysicalHeightCm};
    if (!IsFinite(Candidate)) return false;
    Output = Candidate; return true;
}

// Explicit historical source decoder, matching the original manifest. This is
// supplied for comparison only; do not replace/version-bypass existing save code.
constexpr PointCm DecodeLegacySourceAmot(double East, double Up, double South)
{
    return {East*LegacyArchitectureCmPerAmah, South*LegacyArchitectureCmPerAmah, Up*LegacyArchitectureCmPerAmah};
}
// Geographic coordinates already expressed in centimetres remain metric and fixed.
constexpr PointCm PreserveMetricContext(const PointCm& GeographicPoint) { return GeographicPoint; }
}
