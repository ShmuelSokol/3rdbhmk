#pragma once
#include "MikdashUnits.h"
#include <array>
#include <cstdint>

// Explicit per-world interpretation of immutable LEGACY source coordinates.
// A native candidate actor/property must not be sent through this decoder again.
namespace MikdashSceneUnits
{
enum class Revision : std::uint8_t { Legacy50V1 = 0, Selected48V1 = 1 };
struct Frame
{
    std::uint32_t SchemaVersion = 1;
    Revision CoordinateRevision = Revision::Legacy50V1;
    MikdashUnits::PointCm FixedOrigin;
};
inline bool Valid(const Frame& F)
{
    return F.SchemaVersion == 1 && MikdashUnits::IsFinite(F.FixedOrigin)
        && (F.CoordinateRevision == Revision::Legacy50V1 || F.CoordinateRevision == Revision::Selected48V1);
}
inline bool TryLegacyTemplePoint(const Frame& F, const MikdashUnits::PointCm& Input,
                                MikdashUnits::PointCm& Output)
{
    if (!Valid(F) || !MikdashUnits::IsFinite(Input)) return false;
    if (F.CoordinateRevision == Revision::Legacy50V1) { Output = Input; return true; }
    return MikdashUnits::TryScaleLegacyArchitecturePoint(Input, F.FixedOrigin, Output);
}
inline bool TryLegacyTempleSupport(const Frame& F, const MikdashUnits::PointCm& Support,
                                  double PhysicalHeightCm, MikdashUnits::PointCm& Output)
{
    MikdashUnits::PointCm Converted;
    return TryLegacyTemplePoint(F, Support, Converted)
        && MikdashUnits::TryPlaceAboveFloor(Converted, PhysicalHeightCm, Output);
}
inline bool TryMetricPoint(const Frame& F, const MikdashUnits::PointCm& Input,
                          MikdashUnits::PointCm& Output)
{
    if (!Valid(F) || !MikdashUnits::IsFinite(Input)) return false;
    Output = MikdashUnits::PreserveMetricContext(Input); return true;
}

using IntroPoints = std::array<MikdashUnits::PointCm, 12>;
using AimPoints = std::array<MikdashUnits::PointCm, 5>;
inline IntroPoints LegacyIntroPoints()
{
    return {{{-38600,48200,4200}, {-31200,39800,5100}, {-23800,30200,5900},
             {-16600,16200,5400}, {-10200,10600,4900}, {-3800,9200,4400},
             {2600,7200,3900}, {6400,4200,2900}, {7000,1200,1900},
             {5200,200,1300}, {3600,0,950}, {2100,0,668}}};
}
inline AimPoints LegacyAimPoints()
{
    return {{{-14800,13900,400}, {-6000,4000,2000}, {-2000,0,2600},
             {-2450,0,2200}, {-2450,0,1400}}};
}
// City/approach controls 0..4 stay fixed. Remaining XY coordinates follow the
// authored Temple shot; height is floor/feature support plus physical clearance.
// Index 5 is abeam the House over the geographic deck (support Z0). The remaining
// supports are wall3425, outer court300, inner floor500. Eye is ALWAYS168cm.
inline bool TryIntroPoints(const Frame& F, IntroPoints& Output)
{
    if (!Valid(F)) return false;
    const IntroPoints Legacy = LegacyIntroPoints();
    IntroPoints Candidate = Legacy;
    const double SupportZ[7] = {0,3425,300,300,300,500,500};
    for (std::size_t I = 5; I < Legacy.size(); ++I)
    {
        const auto& P = Legacy[I];
        if (!TryLegacyTempleSupport(F, {P.X,P.Y,SupportZ[I-5]}, P.Z-SupportZ[I-5], Candidate[I])) return false;
    }
    Output = Candidate; return true;
}
inline bool TryAimPoints(const Frame& F, AimPoints& Output)
{
    if (!Valid(F)) return false;
    const AimPoints Legacy = LegacyAimPoints();
    AimPoints Candidate = Legacy;
    // First target is the real Kotel. Second is an authored Temple-facing target
    // during the Mount reveal, not a geographically surveyed landmark.
    for (std::size_t I = 1; I < Legacy.size(); ++I)
        if (!TryLegacyTemplePoint(F, Legacy[I], Candidate[I])) return false;
    Output = Candidate; return true;
}
}
