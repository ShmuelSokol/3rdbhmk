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

// One canonical authored east approach, shared by editor tooling and live playback.
using IntroPoints = std::array<MikdashUnits::PointCm, 19>;
using AimPoints = std::array<MikdashUnits::PointCm, 6>;
inline IntroPoints LegacyIntroPoints()
{
    return {{{140000,4200,8600}, {129500,1600,6500}, {122500,300,5300},
             {116720,0,4800}, {111500,0,5000}, {103500,0,6500},
             {92000,0,7000}, {81000,0,7300}, {66000,0,5900},
             {50000,0,3800}, {34000,0,2900}, {20000,0,3300},
             {12500,0,3950}, {8300,0,3800}, {7300,0,3450},
             {6200,0,2650}, {5000,0,1800}, {3800,0,1100}, {2100,0,668}}};
}
inline AimPoints LegacyAimPoints()
{
    return {{{-4900,0,3200}, {-4900,0,3200}, {-4900,0,3200},
             {8000,0,2000}, {-2450,0,2200}, {-2450,0,1400}}};
}
inline bool TryIntroPoints(const Frame& F, IntroPoints& Output)
{
    if (!Valid(F)) return false;
    const IntroPoints Legacy = LegacyIntroPoints();
    IntroPoints Candidate = Legacy;
    // Ridge, Kidron and geographic deck controls 0..12 remain metric, except the
    // precinct gate crossing (3): precinct placement scales about its own zero
    // origin, NOT the sanctuary's later Aron pivot. Elevation stays geographic;
    // actual gate-opening clearance remains a native ground-profile acceptance.
    if (F.CoordinateRevision == Revision::Selected48V1)
        Candidate[3].X = Legacy[3].X * (48.0 / 50.0);
    // Temple supports follow measured architecture; clearance above each support
    // remains physical. In particular the final eye is floor+168cm, never *.96.
    const double SupportZ[6] = {3300,3346,300,300,500,500};
    for (std::size_t I = 13; I < Legacy.size(); ++I)
    {
        const auto& P = Legacy[I];
        if (!TryLegacyTempleSupport(F, {P.X,P.Y,SupportZ[I-13]}, P.Z-SupportZ[I-13], Candidate[I])) return false;
    }
    Output = Candidate; return true;
}
inline bool TryAimPoints(const Frame& F, AimPoints& Output)
{
    if (!Valid(F)) return false;
    const AimPoints Legacy = LegacyAimPoints();
    AimPoints Candidate = Legacy;
    for (std::size_t I = 0; I < Legacy.size(); ++I)
        if (!TryLegacyTemplePoint(F, Legacy[I], Candidate[I])) return false;
    Output = Candidate; return true;
}
}
