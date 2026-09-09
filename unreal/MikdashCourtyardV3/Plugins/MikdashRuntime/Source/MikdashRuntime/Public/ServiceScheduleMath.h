#include "MikdashSceneUnitsMath.h"
#pragma once
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>

// Engine-independent station sequencing, per-lamp timing, interval scheduling,
// the Kodesh HaKodashim boundary test and the scenario gate for one service
// character. No Unreal type appears here so the whole file compiles and runs
// under cl.exe (Plugins/MikdashRuntime/Tests/ServiceScheduleMathTest.cpp).
//
// WHAT THIS DEPICTS, AND WHAT IT DOES NOT ASSERT
// ----------------------------------------------
// This is an authored depiction of one Kohen Gadol performing hatavat ha-nerot
// (tending and kindling the menorah lamps) in the Heikhal, followed by a
// placeholder pause at the golden altar. It is not a rules engine, not a
// halachic permission table, and not rabbinically approved. Evidence classes
// follow Research/halacha-and-service.md: H = earlier-Temple / halachic source
// with the passage named, R = review / disputed / unresolved mapping,
// D = design (pacing, animation length, ordering choices made here).
//
// SOURCE DECISIONS ACTUALLY ENCODED BELOW (full register: sources.md)
//  H  The daily lamp service is ordinarily performed by an ordinary kohen, who
//     may enter the Heikhal for service every day (Rambam, Biat HaMikdash 2:1).
//  H  The Kohen Gadol may nevertheless perform any service he wishes, whenever
//     he wishes, without entering the lottery, and Mishnah Yoma 1:2 (Yoma 14a)
//     names hatavat ha-nerot among the services he performs
//     (Yoma 14a; Rambam, Klei HaMikdash 5:12 -- NOT 5:11, see sources.md).
//     Therefore a Kohen Gadol lighting the menorah is a legitimate depiction.
//  H  He may walk in the Heikhal for service; Klei HaMikdash 5:11 describes him
//     entering the Heikhal wearing the ephod. Biat HaMikdash 2:2 warns against
//     entering when NOT in the midst of service, so this actor only ever walks
//     the Heikhal inside a service sequence -- it has no idle wander state.
//  H  He may not enter the Kodesh HaKodashim except on Yom Kippur
//     (Vayikra 16:2; Rambam, Biat HaMikdash 2:1). KodeshLineX is the hard
//     ordinary-day boundary and no ordinary-day station or leg may reach it.
//  H  A stone with three steps stands before the menorah; the kohen stands on
//     it to clean and kindle (Rambam, Beit HaBechirah 3:11).
//  H  Order used: five lamps are kindled, the kuz is left on the SECOND of the
//     three steps, he departs, later re-enters and kindles the remaining two,
//     takes the kuz and departs (Rambam, Temidin uMusafin 3:17).
//  H  Hatavah per lamp = remove the spent wick and remaining oil, clean, set a
//     new wick and a half-log of oil, kindle (Temidin uMusafin 3:11-3:12).
//  H  The six branch lamps face the central lamp (Beit HaBechirah 3:8, from
//     Bamidbar 8:2); on Rambam's north-south orientation the central lamp is
//     the one facing the Kodesh HaKodashim (Temidin uMusafin 3:13).
//  R  WHICH five and which two: not specified by any source consulted. The
//     order below is an authored placeholder (north to south) pending review.
//  R  Whether hatavah means kindling (Rambam) or only cleaning (Ra'avad and
//     others), and whether the menorah is north-south (Rambam) or east-west
//     (Rashi), are live disputes. We depict Rambam because the placed asset
//     was built to Rambam (release_import_menorah_v4.spec.json).
//  R  The exact position of the incense offering relative to the two remaining
//     lamps follows Abaye's seder (five lamps, blood, two lamps, incense) and
//     needs review against Rambam's own ordering.
//  D  Every duration, walk speed and repeat interval here is a pacing choice.
//     Nothing in the sources fixes a number of seconds.

namespace MikdashService
{
enum class Scenario { OrdinaryDay, YomKippur };

enum class StationKind
{
    UlamApproach,      // outside the Heikhal, east of the doorway
    Doorway,           // between the jambs
    TendingStone,      // on the three-step stone east of the menorah
    Lamp,              // one lamp of the seven, tended from the stone
    KuzOnSecondStep,   // Temidin uMusafin 3:17
    WithdrawOutside,   // the intervening service happens outside; not modelled
    GoldenAltar,       // placeholder pause; smoke belongs to another system
    InnerEntry,        // Yom Kippur scenario only
    InnerExit          // Yom Kippur scenario only
};

enum class Phase { Idle, Walking, Dwelling, Held, Complete, Waiting };

enum class Refusal
{
    None,
    EmptySequence,
    BadGeometry,
    CrossesKodeshLine,
    OutsideReviewedEnvelope,
    ScenarioForbidsStation,
    BadFloorHeight,
    BadLampGrouping,
    DurationOutOfWindow,
    SequenceNotClosed,
    NotConfigured
};

enum class Zone { Outside, Ulam, Doorway, Heikhal, ParochesGap, Kodesh };

struct Point3
{
    double X = 0.0, Y = 0.0, Z = 0.0;
};

// ---------------------------------------------------------------------------
// Measured geometry, read from SourceAssets/architecture-manifest.json floor
// meshes. These are model coordinates in centimetres, not surveyed facts.
//   SM_0146_floor_Heichal_clear_floor   X -5600..-3600  Y +-500  top Z 925
//   SM_0145_floor_Ulam_clear_floor      X -3300..-2750  Y +-500  top Z 925
//   SM_0147_floor_Kodesh_clear_floor    X -6700..-5700  Y +-500  top Z 925
//   partition band                      X -5700..-5600, clear below Z 1225
//                                       only for |Y| < 175 (the paroches gap)
//   Heikhal doorway jambs               inner faces at |Y| = 250.5
// ---------------------------------------------------------------------------
inline constexpr double KodeshLineX = -5600.0;        // the paroches line
inline constexpr double ParochesBandWestX = -5700.0;
inline constexpr double KodeshWestX = -6700.0;
inline constexpr double HeikhalEastX = -3600.0;
inline constexpr double UlamWestX = -3300.0;
inline constexpr double UlamEastX = -2750.0;
inline constexpr double SanctuaryHalfY = 500.0;
inline constexpr double DoorwayHalfY = 250.0;
inline constexpr double ParochesGapHalfY = 175.0;
inline constexpr double FloorZ = 925.0;
inline constexpr double StoneTopZ = 975.0;            // three-step stone top
inline constexpr double HeightToleranceCm = 3.0;
inline constexpr double EdgeInsetCm = 5.0;            // keep off the exact wall
inline constexpr std::size_t LampCount = 7;
inline constexpr std::size_t MaxStations = 32;
inline constexpr int SegmentSamples = 128;

inline bool Finite(const Point3& P)
{
    return std::isfinite(P.X) && std::isfinite(P.Y) && std::isfinite(P.Z);
}

inline double Distance2D(const Point3& A, const Point3& B)
{
    const double DX = A.X - B.X, DY = A.Y - B.Y;
    return std::sqrt(DX * DX + DY * DY);
}

inline bool Between(double V, double Low, double High)
{
    return V >= Low && V <= High;
}

struct Geometry
{
    double KodeshLineX = MikdashService::KodeshLineX;
    double ParochesBandWestX = MikdashService::ParochesBandWestX;
    double KodeshWestX = MikdashService::KodeshWestX;
    double HeikhalEastX = MikdashService::HeikhalEastX;
    double UlamWestX = MikdashService::UlamWestX;
    double UlamEastX = MikdashService::UlamEastX;
    double SanctuaryHalfY = MikdashService::SanctuaryHalfY;
    double DoorwayHalfY = MikdashService::DoorwayHalfY;
    double ParochesGapHalfY = MikdashService::ParochesGapHalfY;
    double FloorZ = MikdashService::FloorZ;
    double StoneTopZ = MikdashService::StoneTopZ;
};

// XY zone only. Height is checked separately: a point may legitimately sit on
// the floor (925) or on top of the three-step stone (975).
inline Zone ZoneOf(const Point3& P, const Geometry& G = Geometry{})
{
    if (!Finite(P)) return Zone::Outside;
    const double AbsY = std::fabs(P.Y);
    if (Between(P.X, G.UlamWestX + EdgeInsetCm, G.UlamEastX - EdgeInsetCm)
        && AbsY <= G.SanctuaryHalfY - EdgeInsetCm) return Zone::Ulam;
    if (Between(P.X, G.HeikhalEastX, G.UlamWestX + EdgeInsetCm)
        && AbsY <= G.DoorwayHalfY - EdgeInsetCm) return Zone::Doorway;
    // Strictly east of the paroches line: the ordinary-day hard boundary.
    if (P.X > G.KodeshLineX + EdgeInsetCm && P.X <= G.HeikhalEastX
        && AbsY <= G.SanctuaryHalfY - EdgeInsetCm) return Zone::Heikhal;
    if (Between(P.X, G.ParochesBandWestX, G.KodeshLineX + EdgeInsetCm)
        && AbsY <= G.ParochesGapHalfY - EdgeInsetCm) return Zone::ParochesGap;
    if (Between(P.X, G.KodeshWestX + EdgeInsetCm, G.ParochesBandWestX)
        && AbsY <= G.SanctuaryHalfY - EdgeInsetCm) return Zone::Kodesh;
    return Zone::Outside;
}

// The scenario gate. OrdinaryDay never permits anything at or west of the
// paroches line; YomKippur permits it and nothing else changes.
inline bool ZonePermitted(Scenario Day, Zone Where)
{
    switch (Where)
    {
    case Zone::Ulam:
    case Zone::Doorway:
    case Zone::Heikhal:
        return true;
    case Zone::ParochesGap:
    case Zone::Kodesh:
        return Day == Scenario::YomKippur;
    default:
        return false;
    }
}

inline bool KindPermitted(Scenario Day, StationKind Kind)
{
    if (Kind == StationKind::InnerEntry || Kind == StationKind::InnerExit)
        return Day == Scenario::YomKippur;
    return true;
}

// A stand height is acceptable if it is the reviewed floor or the stone top.
inline bool HeightPermitted(double Z, const Geometry& G = Geometry{})
{
    return std::isfinite(Z)
        && (std::fabs(Z - G.FloorZ) <= HeightToleranceCm
            || std::fabs(Z - G.StoneTopZ) <= HeightToleranceCm);
}

// Boundary test for one straight leg. The leg is sampled because a leg may be
// permitted at both ends and still cut a corner through a wall or, on an
// ordinary day, clip the paroches line. X is monotone along a segment, so the
// ordinary-day line test alone is exact; the sampling covers the Y narrowing
// at the doorway and at the paroches gap.
inline bool SegmentPermitted(Scenario Day, const Point3& From, const Point3& To, Refusal& Why, const Geometry& G = Geometry{})
{
    Why = Refusal::None;
    if (!Finite(From) || !Finite(To)) { Why = Refusal::BadGeometry; return false; }
    if (Day == Scenario::OrdinaryDay)
    {
        const double MinX = From.X < To.X ? From.X : To.X;
        if (MinX <= G.KodeshLineX) { Why = Refusal::CrossesKodeshLine; return false; }
    }
    for (int Step = 0; Step <= SegmentSamples; ++Step)
    {
        const double T = static_cast<double>(Step) / SegmentSamples;
        const Point3 At{From.X + (To.X - From.X) * T,
                        From.Y + (To.Y - From.Y) * T,
                        From.Z + (To.Z - From.Z) * T};
        const Zone Where = ZoneOf(At, G);
        if (Where == Zone::Outside) { Why = Refusal::OutsideReviewedEnvelope; return false; }
        if (!ZonePermitted(Day, Where))
        {
            Why = (Where == Zone::Kodesh || Where == Zone::ParochesGap)
                ? Refusal::CrossesKodeshLine : Refusal::ScenarioForbidsStation;
            return false;
        }
    }
    return true;
}

// ---------------------------------------------------------------------------
// Stations and the authored plan.
// ---------------------------------------------------------------------------
struct Station
{
    StationKind Kind = StationKind::UlamApproach;
    Point3 Stand;              // where the body's feet rest
    Point3 Face;               // what it turns toward while dwelling
    double DwellSeconds = 0.0;
    int LampIndex = -1;        // 0..6 for Lamp stations, otherwise -1
    // Plain language for the dialog/prompt system. Never a halachic ruling.
    const char* Action = "";
};

struct Plan
{
    std::array<Station, MaxStations> Items{};
    std::size_t Count = 0;

    bool Add(const Station& S)
    {
        if (Count >= MaxStations) return false;
        Items[Count++] = S;
        return true;
    }
    void Clear() { Count = 0; }
};

// Timing. Every number is a pacing choice (D), never a sourced duration.
struct LampSchedule
{
    double PerLampSeconds = 14.0;
    std::size_t FirstGroup = 5;   // Temidin uMusafin 3:17
    std::size_t SecondGroup = 2;

    bool Valid() const
    {
        return std::isfinite(PerLampSeconds) && PerLampSeconds > 0.0
            && FirstGroup + SecondGroup == LampCount
            && FirstGroup > 0 && SecondGroup > 0;
    }
};

struct DwellTimes
{
    double ApproachSeconds = 8.0;
    double DoorwaySeconds = 4.0;
    double StoneSeconds = 6.0;
    double KuzSeconds = 5.0;
    double WithdrawSeconds = 20.0;   // the intervening service is not modelled
    double AltarSeconds = 30.0;      // placeholder; smoke is another system
    double InnerSeconds = 20.0;      // Yom Kippur scenario only

    bool Valid() const
    {
        const double All[] = {ApproachSeconds, DoorwaySeconds, StoneSeconds, KuzSeconds,
                              WithdrawSeconds, AltarSeconds, InnerSeconds};
        for (double V : All) if (!std::isfinite(V) || V < 0.0) return false;
        return true;
    }
};

// Anchors measured from the placed assets, not invented:
//   menorah plinth      release_import_menorah_v4.spec.json placement
//                       location (-5330, 315.176, 925), yaw -90
//   SM_MenorahV4_Lamps  local X +-50.76, branches +-46.95 -> world Y, because
//                       yaw -90 maps local +X to world -Y (branches north-south,
//                       Rambam, Beit HaBechirah 3:8)
//   SM_MenorahV4_StepStone local Y 45.91..135.91 -> world X -5284.1..-5194.1,
//                       local X +-45 -> world Y 270.2..360.2, top Z 975
//   golden altar        release_scale_keilim.spec.json cluster (-4650, 0)
struct Anchors
{
    Point3 UlamApproach{-3200.0, 0.0, FloorZ};
    Point3 Doorway{-3450.0, 0.0, FloorZ};
    Point3 StoneStand{-5239.0, 315.176, StoneTopZ};
    Point3 GoldenAltar{-4650.0, 0.0, FloorZ};
    Point3 AltarFace{-4650.0, 0.0, FloorZ + 100.0};
    // Yom Kippur only. Passes the paroches gap on the centre line.
    Point3 InnerStand{-6100.0, 0.0, FloorZ};

    double MenorahX = -5330.0;
    double MenorahCentreY = 315.176;
    double BranchHalfSpanY = 46.95;   // local X half span of the six branches
    double LampZ = FloorZ + 150.0;    // 18 tefachim (Rambam), 150 cm at 50 cm/amah
    double StoneMinY = 270.2;
    double StoneMaxY = 360.2;

    // Lamp k, indexed 0 = northernmost (world -Y) to 6 = southernmost (+Y).
    // The centre lamp k = 3 sits on the menorah axis and, on Rambam's
    // north-south orientation, is the lamp facing the Kodesh HaKodashim.
    Point3 LampAt(std::size_t K) const
    {
        const double Span = 2.0 * BranchHalfSpanY;
        const double T = LampCount > 1 ? static_cast<double>(K) / (LampCount - 1) : 0.5;
        return Point3{MenorahX, MenorahCentreY - BranchHalfSpanY + Span * T, LampZ};
    }

    // The body never walks between lamps: it stands on the stone and shuffles
    // along the stone top, clamped to the stone footprint, turning to each lamp.
    bool SceneDecoded = false;
    double LampStandZ = StoneTopZ;
    Point3 StandForLamp(std::size_t K) const
    {
        double Y = LampAt(K).Y;
        if (Y < StoneMinY) Y = StoneMinY;
        if (Y > StoneMaxY) Y = StoneMaxY;
        return Point3{StoneStand.X, Y, LampStandZ};
    }
};

// Decode immutable legacy anchors exactly once; all outputs committed together.
inline bool DecodeScene(const MikdashSceneUnits::Frame& F, const Anchors& Legacy,
                        Anchors& Out, Geometry& OutGeometry)
{
    if (!MikdashSceneUnits::Valid(F) || Legacy.SceneDecoded) return false;
    Anchors A = Legacy; Geometry G;
    auto Point = [&F](Point3& P) {
        MikdashUnits::PointCm Converted;
        if (!MikdashSceneUnits::TryLegacyTemplePoint(F,{P.X,P.Y,P.Z},Converted)) return false;
        P = {Converted.X,Converted.Y,Converted.Z}; return true;
    };
    const double AltarLookOffset = Legacy.AltarFace.Z-Legacy.GoldenAltar.Z;
    if (!std::isfinite(AltarLookOffset) || AltarLookOffset < 0) return false;
    if (!Point(A.UlamApproach) || !Point(A.Doorway) || !Point(A.StoneStand)
        || !Point(A.GoldenAltar) || !Point(A.InnerStand)) return false;
    A.AltarFace = A.GoldenAltar; A.AltarFace.Z += AltarLookOffset;
    Point3 Lamp{A.MenorahX,A.MenorahCentreY,A.LampZ};
    if (!Point(Lamp)) return false;
    A.MenorahX=Lamp.X; A.MenorahCentreY=Lamp.Y; A.LampZ=Lamp.Z;
    if (F.CoordinateRevision == MikdashSceneUnits::Revision::Selected48V1)
    {
        // Supported production pivot has Y/Z zero; refuse unsupported zone translations.
        if (F.FixedOrigin.Y != 0 || F.FixedOrigin.Z != 0) return false;
        const double R=48.0/50.0, Shift=F.FixedOrigin.X*(1-R);
        G.KodeshLineX = G.KodeshLineX*R + Shift;
        G.ParochesBandWestX = G.ParochesBandWestX*R + Shift;
        G.KodeshWestX = G.KodeshWestX*R + Shift;
        G.HeikhalEastX = G.HeikhalEastX*R + Shift;
        G.UlamWestX = G.UlamWestX*R + Shift;
        G.UlamEastX = G.UlamEastX*R + Shift;
        G.SanctuaryHalfY = G.SanctuaryHalfY*R;
        G.DoorwayHalfY = G.DoorwayHalfY*R;
        G.ParochesGapHalfY = G.ParochesGapHalfY*R;
        G.FloorZ = G.FloorZ*R;
        G.StoneTopZ = G.StoneTopZ*R;
        A.BranchHalfSpanY*=R; A.StoneMinY*=R; A.StoneMaxY*=R;
    }
    A.LampStandZ=G.StoneTopZ;
    A.SceneDecoded=true; Out=A; OutGeometry=G; return true;
}

// The ordinary-day menorah sequence. Yom Kippur adds a clearly separate inner
// entry and exit around the same daily sequence and simulates nothing else of
// that day: entry and exit only, as commissioned.
inline bool BuildMenorahSequence(Scenario Day, const Anchors& A, const LampSchedule& Lamps,
                                 const DwellTimes& Dwell, Plan& Out, Refusal& Why, const Geometry& G = Geometry{})
{
    Out.Clear();
    Why = Refusal::None;
    if (!Lamps.Valid()) { Why = Refusal::BadLampGrouping; return false; }
    if (!Dwell.Valid()) { Why = Refusal::BadGeometry; return false; }

    auto At = [&](StationKind K, Point3 Stand, Point3 Face, double Sec, int Lamp, const char* Text)
    {
        Station S; S.Kind = K; S.Stand = Stand; S.Face = Face;
        S.DwellSeconds = Sec; S.LampIndex = Lamp; S.Action = Text;
        return Out.Add(S);
    };

    bool Ok = true;
    Ok = Ok && At(StationKind::UlamApproach, A.UlamApproach, A.Doorway, Dwell.ApproachSeconds, -1,
        "Standing in the Ulam, facing the doorway of the Heikhal before the lamp service.");
    Ok = Ok && At(StationKind::Doorway, A.Doorway, A.StoneStand, Dwell.DoorwaySeconds, -1,
        "Passing through the doorway into the Heikhal for the service.");
    Ok = Ok && At(StationKind::TendingStone, A.StoneStand, A.LampAt(3), Dwell.StoneSeconds, -1,
        "Stepping up onto the three-step stone that stands east of the menorah.");
    for (std::size_t K = 0; K < Lamps.FirstGroup; ++K)
        Ok = Ok && At(StationKind::Lamp, A.StandForLamp(K), A.LampAt(K), Lamps.PerLampSeconds,
            static_cast<int>(K),
            "Tending a lamp: clearing the spent wick and oil, setting a fresh wick and oil, kindling it.");
    Ok = Ok && At(StationKind::KuzOnSecondStep, A.StoneStand, A.LampAt(3), Dwell.KuzSeconds, -1,
        "Leaving the kuz on the second of the three steps before going out.");
    Ok = Ok && At(StationKind::Doorway, A.Doorway, A.UlamApproach, Dwell.DoorwaySeconds, -1,
        "Leaving the Heikhal after the first five lamps.");
    Ok = Ok && At(StationKind::WithdrawOutside, A.UlamApproach, A.Doorway, Dwell.WithdrawSeconds, -1,
        "Waiting outside while the service that comes between the two groups of lamps takes place; that service is not depicted here.");
    Ok = Ok && At(StationKind::Doorway, A.Doorway, A.StoneStand, Dwell.DoorwaySeconds, -1,
        "Entering the Heikhal again for the two remaining lamps.");
    for (std::size_t K = Lamps.FirstGroup; K < LampCount; ++K)
        Ok = Ok && At(StationKind::Lamp, A.StandForLamp(K), A.LampAt(K), Lamps.PerLampSeconds,
            static_cast<int>(K),
            "Tending a lamp: clearing the spent wick and oil, setting a fresh wick and oil, kindling it.");
    Ok = Ok && At(StationKind::KuzOnSecondStep, A.StoneStand, A.LampAt(3), Dwell.KuzSeconds, -1,
        "Taking up the kuz from the step and stepping down from the stone.");
    Ok = Ok && At(StationKind::GoldenAltar, A.GoldenAltar, A.AltarFace, Dwell.AltarSeconds, -1,
        "Standing at the golden altar for the incense; the smoke itself is not produced here.");
    if (Day == Scenario::YomKippur)
    {
        Ok = Ok && At(StationKind::InnerEntry, A.InnerStand, Point3{A.InnerStand.X - 100.0, 0.0, G.FloorZ},
            Dwell.InnerSeconds, -1,
            "Yom Kippur scenario only: entering beyond the paroches. Nothing of that service is depicted; this is entry and exit only.");
        Ok = Ok && At(StationKind::InnerExit, Point3{G.KodeshLineX + 200.0, 0.0, G.FloorZ}, A.Doorway,
            Dwell.DoorwaySeconds, -1,
            "Yom Kippur scenario only: coming back out past the paroches.");
    }
    Ok = Ok && At(StationKind::Doorway, A.Doorway, A.UlamApproach, Dwell.DoorwaySeconds, -1,
        "Leaving the Heikhal at the end of the sequence.");
    Ok = Ok && At(StationKind::UlamApproach, A.UlamApproach, A.Doorway, Dwell.ApproachSeconds, -1,
        "Standing again in the Ulam; the sequence is over until the next one.");

    if (!Ok) { Out.Clear(); Why = Refusal::EmptySequence; return false; }
    return true;
}

// ---------------------------------------------------------------------------
// Duration arithmetic and whole-plan validation.
// ---------------------------------------------------------------------------
inline double PlanWalkSeconds(const Plan& P, double SpeedCmPerSec)
{
    if (!std::isfinite(SpeedCmPerSec) || SpeedCmPerSec <= 0.0 || P.Count == 0) return 0.0;
    double Total = 0.0;
    for (std::size_t I = 1; I < P.Count; ++I)
        Total += Distance2D(P.Items[I - 1].Stand, P.Items[I].Stand) / SpeedCmPerSec;
    return Total;
}

inline double PlanDwellSeconds(const Plan& P)
{
    double Total = 0.0;
    for (std::size_t I = 0; I < P.Count; ++I) Total += P.Items[I].DwellSeconds;
    return Total;
}

inline double PlanLoopSeconds(const Plan& P, double SpeedCmPerSec)
{
    return PlanWalkSeconds(P, SpeedCmPerSec) + PlanDwellSeconds(P);
}

// The commissioned window is 3 to 6 minutes. That is a pacing requirement, not
// a sourced duration, so it is a parameter and it is checked, never assumed.
inline constexpr double DefaultMinLoopSeconds = 180.0;
inline constexpr double DefaultMaxLoopSeconds = 360.0;

inline Refusal ValidatePlan(Scenario Day, const Plan& P, double SpeedCmPerSec,
                            double MinLoopSeconds, double MaxLoopSeconds, std::size_t& BadIndex, const Geometry& G = Geometry{})
{
    BadIndex = 0;
    if (P.Count < 2) return Refusal::EmptySequence;
    if (!std::isfinite(SpeedCmPerSec) || SpeedCmPerSec <= 0.0) return Refusal::BadGeometry;
    for (std::size_t I = 0; I < P.Count; ++I)
    {
        BadIndex = I;
        const Station& S = P.Items[I];
        if (!Finite(S.Stand) || !Finite(S.Face)) return Refusal::BadGeometry;
        if (!std::isfinite(S.DwellSeconds) || S.DwellSeconds < 0.0) return Refusal::BadGeometry;
        if (!KindPermitted(Day, S.Kind)) return Refusal::ScenarioForbidsStation;
        if (!HeightPermitted(S.Stand.Z, G)) return Refusal::BadFloorHeight;
        const Zone Where = ZoneOf(S.Stand, G);
        if (Where == Zone::Outside) return Refusal::OutsideReviewedEnvelope;
        if (!ZonePermitted(Day, Where))
            return (Where == Zone::Kodesh || Where == Zone::ParochesGap)
                ? Refusal::CrossesKodeshLine : Refusal::ScenarioForbidsStation;
        if (Day == Scenario::OrdinaryDay && S.Stand.X <= G.KodeshLineX) return Refusal::CrossesKodeshLine;
        if (S.Kind == StationKind::Lamp
            && (S.LampIndex < 0 || static_cast<std::size_t>(S.LampIndex) >= LampCount))
            return Refusal::BadLampGrouping;
    }
    for (std::size_t I = 1; I < P.Count; ++I)
    {
        BadIndex = I;
        Refusal Why = Refusal::None;
        if (!SegmentPermitted(Day, P.Items[I - 1].Stand, P.Items[I].Stand, Why, G)) return Why;
    }
    // The interval restart jumps from the last station back to the first, so
    // the two must be the same point or the body would teleport across the
    // hall between sequences. Refuse rather than allow that.
    BadIndex = P.Count - 1;
    if (Distance2D(P.Items[0].Stand, P.Items[P.Count - 1].Stand) > 1.0
        || std::fabs(P.Items[0].Stand.Z - P.Items[P.Count - 1].Stand.Z) > 1.0)
        return Refusal::SequenceNotClosed;

    BadIndex = P.Count;
    const double Loop = PlanLoopSeconds(P, SpeedCmPerSec);
    if (!std::isfinite(MinLoopSeconds) || !std::isfinite(MaxLoopSeconds) || MinLoopSeconds > MaxLoopSeconds)
        return Refusal::BadGeometry;
    if (Loop < MinLoopSeconds || Loop > MaxLoopSeconds) return Refusal::DurationOutOfWindow;
    return Refusal::None;
}

// Count the lamps a plan actually tends, so a truncated plan cannot silently
// claim the whole service happened.
inline std::size_t LampsTended(const Plan& P)
{
    bool Seen[LampCount] = {};
    for (std::size_t I = 0; I < P.Count; ++I)
    {
        const Station& S = P.Items[I];
        if (S.Kind == StationKind::Lamp && S.LampIndex >= 0
            && static_cast<std::size_t>(S.LampIndex) < LampCount)
            Seen[S.LampIndex] = true;
    }
    std::size_t Total = 0;
    for (bool V : Seen) if (V) ++Total;
    return Total;
}

// ---------------------------------------------------------------------------
// The runner. It never teleports. A leg the caller reports as blocked leaves
// the body standing where it is, in Phase::Held, and the hold is counted.
// ---------------------------------------------------------------------------
struct Progress
{
    Phase State = Phase::Idle;
    std::size_t Index = 0;          // station being walked to, or dwelt at
    double InPhaseSeconds = 0.0;
    double LegLengthCm = 0.0;
    double LegTravelledCm = 0.0;
    std::uint32_t CompletedLoops = 0;
    double HeldSeconds = 0.0;       // total across the life of the actor
    std::uint32_t BlockedLegs = 0;  // number of distinct legs that were held
    bool BlockedNow = false;
};

class Sequencer
{
public:
    struct MotionRequest
    {
        std::size_t Index = 0;
        std::uint64_t Generation = 0;
        Point3 Destination{};
    };
    bool Configure(Scenario Day, const Plan& Sequence, double SpeedCmPerSec,
                   double IntervalSeconds, double MinLoopSeconds = DefaultMinLoopSeconds,
                   double MaxLoopSeconds = DefaultMaxLoopSeconds, const Geometry& G = Geometry{})
    {
        ++MotionGeneration;
        ExternalMotion = false;
        ExternalPaused = false;
        MotionAdmitted = false;
        LastArrivedIndex = 0;
        std::size_t Bad = 0;
        LastRefusal = ValidatePlan(Day, Sequence, SpeedCmPerSec, MinLoopSeconds, MaxLoopSeconds, Bad, G);
        if (LastRefusal != Refusal::None) { BadStation = Bad; Ready = false; return false; }
        if (!std::isfinite(IntervalSeconds) || IntervalSeconds < 0.0)
        {
            LastRefusal = Refusal::BadGeometry; Ready = false; return false;
        }
        Day_ = Day; Sequence_ = Sequence; Speed = SpeedCmPerSec; Interval = IntervalSeconds;
        State = Progress{};
        EntryPending = false;
        State.State = Phase::Dwelling;   // begins standing at station 0
        Ready = true; BadStation = 0;
        return true;
    }

    bool IsReady() const { return Ready; }
    Refusal Why() const { return LastRefusal; }
    std::size_t RefusedStation() const { return BadStation; }
    const Plan& Sequence() const { return Sequence_; }
    const Progress& Where() const { return State; }
    Scenario Day() const { return Day_; }
    double LoopSeconds() const { return PlanLoopSeconds(Sequence_, Speed); }

    // Opt-in motor mode. The caller owns movement and validates physical arrival;
    // this class cannot prove floor/capsule clearance. No native actor uses it yet.
    bool ConfigureExternal(Scenario Day, const Plan& Sequence, double SpeedCmPerSec,
                           double IntervalSeconds, double MinLoopSeconds = DefaultMinLoopSeconds,
                           double MaxLoopSeconds = DefaultMaxLoopSeconds, const Geometry& G = Geometry{})
    {
        if (!Configure(Day, Sequence, SpeedCmPerSec, IntervalSeconds, MinLoopSeconds, MaxLoopSeconds, G)) return false;
        ExternalMotion = true;
        return true;
    }
    bool PendingMotion(MotionRequest& Out) const
    {
        if (!Ready || !ExternalMotion || ExternalPaused ||
            (State.State != Phase::Walking && State.State != Phase::Held)) return false;
        Out = MotionRequest{State.Index, MotionGeneration, Sequence_.Items[State.Index].Stand};
        return true;
    }
    bool AcknowledgeAdmission(const MotionRequest& Request, bool Allowed)
    {
        if (!MatchesMotion(Request)) return false;
        MotionAdmitted = Allowed;
        State.BlockedNow = !Allowed;
        if (!Allowed)
        {
            if (State.State != Phase::Held) ++State.BlockedLegs;
            State.State = Phase::Held;
        }
        else State.State = Phase::Walking;
        return true;
    }
    bool AcknowledgeArrival(const MotionRequest& Request, bool PhysicallyValidated)
    {
        if (!MatchesMotion(Request) || !MotionAdmitted || !PhysicallyValidated) return false;
        LastArrivedIndex = State.Index;
        State.State = Phase::Dwelling;
        State.InPhaseSeconds = 0.0;
        State.BlockedNow = false;
        MotionAdmitted = false;
        ++MotionGeneration; // duplicate arrival/admission cannot affect this dwell
        return true;
    }
    void SetExternalPaused(bool Paused)
    {
        if (!ExternalMotion || Paused == ExternalPaused) return;
        ExternalPaused = Paused;
        ++MotionGeneration; // pre-pause acknowledgments remain stale after resume
        MotionAdmitted = false;
    }
    bool TickExternal(double DeltaSeconds)
    {
        if (!Ready || !ExternalMotion || !std::isfinite(DeltaSeconds) || DeltaSeconds < 0) return false;
        if (ExternalPaused) return true;
        if (State.State == Phase::Walking || State.State == Phase::Held)
        {
            if (State.State == Phase::Held) State.HeldSeconds += DeltaSeconds;
            return true; // no synthetic travel, arrival, or dwell-time credit
        }
        double Remaining = DeltaSeconds;
        for (int Guard=0; Remaining>0 && Guard<4096; ++Guard)
        {
            if (State.State == Phase::Waiting)
            {
                const double Need = Interval-State.InPhaseSeconds;
                if (Remaining<Need) { State.InPhaseSeconds+=Remaining; return true; }
                Remaining-=Need>0 ? Need : 0;
                State.Index=0; LastArrivedIndex=0; State.State=Phase::Dwelling; State.InPhaseSeconds=0;
            }
            else if (State.State == Phase::Dwelling)
            {
                const double Need=Sequence_.Items[State.Index].DwellSeconds-State.InPhaseSeconds;
                if (Remaining<Need) { State.InPhaseSeconds+=Remaining; return true; }
                Remaining-=Need>0 ? Need : 0;
                State.InPhaseSeconds=0;
                if (State.Index+1>=Sequence_.Count)
                {
                    ++State.CompletedLoops;
                    State.State=Interval>0 ? Phase::Waiting : Phase::Dwelling;
                    if (Interval==0) { State.Index=0; LastArrivedIndex=0; }
                    continue;
                }
                ++State.Index; ++MotionGeneration;
                MotionAdmitted=false;
                State.State=Phase::Walking;
                State.LegLengthCm=Distance2D(Sequence_.Items[State.Index-1].Stand,Sequence_.Items[State.Index].Stand);
                State.LegTravelledCm=0;
                return true; // discard remaining dt: motor has not moved yet
            }
            else return false;
        }
        return true;
    }

    // LegBlocked is the caller's capsule sweep result for the CURRENT leg.
    // Returns false and changes nothing when not configured or the step is bad.
    bool Tick(double DeltaSeconds, bool LegBlocked, bool Paused = false)
    {
        return TickWithAdmission(DeltaSeconds,
            [LegBlocked](std::size_t, bool) { return !LegBlocked; }, Paused);
    }

    // Admission is queried BEFORE any distance is consumed, including a leg
    // entered after dwelling in this same call. Entering distinguishes a new
    // traversal (including a repeated loop) from a cached active-leg review.
    // The legacy Tick(bool) API remains for consumers with one global blocker.
    template<class Admission>
    bool TickWithAdmission(double DeltaSeconds, Admission Admit, bool Paused = false)
    {
        if (ExternalMotion) return false;
        if (!Ready) return false;
        if (!std::isfinite(DeltaSeconds) || DeltaSeconds < 0.0) return false;
        if (Paused) return true;

        State.BlockedNow = false;
        double Remaining = DeltaSeconds;
        int Guard = 0;
        while (Remaining > 0.0 && ++Guard < 4096)
        {
            if (State.State == Phase::Dwelling)
            {
                const double Need = Sequence_.Items[State.Index].DwellSeconds - State.InPhaseSeconds;
                if (Remaining < Need) { State.InPhaseSeconds += Remaining; Remaining = 0.0; break; }
                Remaining -= Need > 0.0 ? Need : 0.0;
                State.InPhaseSeconds = 0.0;
                if (State.Index + 1 >= Sequence_.Count)
                {
                    ++State.CompletedLoops;
                    State.State = Interval > 0.0 ? Phase::Waiting : Phase::Dwelling;
                    if (State.State == Phase::Dwelling) { State.Index = 0; }
                    continue;
                }
                ++State.Index;
                State.State = Phase::Walking;
                State.LegLengthCm = Distance2D(Sequence_.Items[State.Index - 1].Stand,
                                               Sequence_.Items[State.Index].Stand);
                State.LegTravelledCm = 0.0;
                EntryPending = true;
                continue;
            }
            if (State.State == Phase::Walking || State.State == Phase::Held)
            {
                const bool Allowed = Admit(State.Index, EntryPending);
                EntryPending = false;
                if (!Allowed)
                {
                    // Hold in place and record. Never advance, never teleport.
                    if (State.State != Phase::Held) { ++State.BlockedLegs; State.State = Phase::Held; }
                    State.HeldSeconds += Remaining;
                    State.InPhaseSeconds += Remaining;
                    State.BlockedNow = true;
                    Remaining = 0.0;
                    break;
                }
                State.State = Phase::Walking;
                const double NeedCm = State.LegLengthCm - State.LegTravelledCm;
                const double CanCm = Remaining * Speed;
                if (CanCm < NeedCm)
                {
                    State.LegTravelledCm += CanCm;
                    State.InPhaseSeconds += Remaining;
                    Remaining = 0.0;
                    break;
                }
                Remaining -= NeedCm > 0.0 ? NeedCm / Speed : 0.0;
                State.LegTravelledCm = State.LegLengthCm;
                State.State = Phase::Dwelling;
                State.InPhaseSeconds = 0.0;
                continue;
            }
            if (State.State == Phase::Waiting)
            {
                const double Need = Interval - State.InPhaseSeconds;
                if (Remaining < Need) { State.InPhaseSeconds += Remaining; Remaining = 0.0; break; }
                Remaining -= Need > 0.0 ? Need : 0.0;
                State.InPhaseSeconds = 0.0;
                State.Index = 0;
                State.State = Phase::Dwelling;
                continue;
            }
            break;   // Idle or Complete: nothing to advance
        }
        return true;
    }

    // Interpolated along the current leg. On a held leg this is the point the
    // body is standing at, which is the previous station.
    Point3 CurrentStand() const
    {
        if (!Ready || Sequence_.Count == 0) return Point3{};
        // Motor mode exposes only the last confirmed station, never invented motion.
        if (ExternalMotion) return Sequence_.Items[LastArrivedIndex].Stand;
        if (State.State == Phase::Walking || State.State == Phase::Held)
        {
            const Point3& A = Sequence_.Items[State.Index - 1].Stand;
            const Point3& B = Sequence_.Items[State.Index].Stand;
            const double T = State.LegLengthCm > 0.0 ? State.LegTravelledCm / State.LegLengthCm : 0.0;
            return Point3{A.X + (B.X - A.X) * T, A.Y + (B.Y - A.Y) * T, A.Z + (B.Z - A.Z) * T};
        }
        return Sequence_.Items[State.Index].Stand;
    }

    Point3 CurrentFace() const
    {
        if (!Ready || Sequence_.Count == 0) return Point3{};
        if (State.State == Phase::Walking || State.State == Phase::Held)
            return Sequence_.Items[State.Index].Stand;
        return Sequence_.Items[State.Index].Face;
    }

    // Plain-language description for the dialog/prompt system. It describes
    // what is being depicted; it never states a rule or a permission.
    const char* CurrentAction() const
    {
        if (!Ready) return "The service sequence is not configured.";
        switch (State.State)
        {
        case Phase::Held:
            return "Standing still: the way ahead is blocked, so the sequence is waiting rather than stepping through anything.";
        case Phase::Waiting:
            return "The lamp service is finished for now; waiting until the next one begins.";
        case Phase::Walking:
            return WalkingTextFor(Sequence_.Items[State.Index].Kind);
        case Phase::Dwelling:
            return Sequence_.Items[State.Index].Action;
        default:
            return "Standing by; the service sequence has not started.";
        }
    }

    // 1-based lamp being tended right now, or 0.
    int CurrentLamp() const
    {
        if (!Ready || State.State != Phase::Dwelling) return 0;
        const Station& S = Sequence_.Items[State.Index];
        return S.Kind == StationKind::Lamp ? S.LampIndex + 1 : 0;
    }

private:
    bool MatchesMotion(const MotionRequest& Request) const
    {
        MotionRequest Current;
        return PendingMotion(Current) && Request.Index==Current.Index && Request.Generation==Current.Generation
            && Request.Destination.X==Current.Destination.X && Request.Destination.Y==Current.Destination.Y
            && Request.Destination.Z==Current.Destination.Z;
    }
    static const char* WalkingTextFor(StationKind Kind)
    {
        switch (Kind)
        {
        case StationKind::Doorway:    return "Walking toward the doorway of the Heikhal.";
        case StationKind::TendingStone: return "Walking across the Heikhal toward the menorah.";
        case StationKind::Lamp:       return "Moving along the stone to the next lamp.";
        case StationKind::GoldenAltar: return "Walking to the golden altar.";
        case StationKind::InnerEntry: return "Yom Kippur scenario only: walking toward the paroches.";
        case StationKind::InnerExit:  return "Yom Kippur scenario only: walking back out.";
        case StationKind::UlamApproach: return "Walking out into the Ulam.";
        default:                      return "Walking to the next station of the sequence.";
        }
    }

    Scenario Day_ = Scenario::OrdinaryDay;
    Plan Sequence_;
    Progress State;
    double Speed = 90.0;
    double Interval = 0.0;
    bool Ready = false;
    bool EntryPending = false;
    bool ExternalMotion = false;
    bool ExternalPaused = false;
    bool MotionAdmitted = false;
    std::uint64_t MotionGeneration = 0;
    std::size_t LastArrivedIndex = 0;
    Refusal LastRefusal = Refusal::NotConfigured;
    std::size_t BadStation = 0;
};
}
