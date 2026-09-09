#include "MikdashSceneUnitsMath.h"
#include "CameraPathMath.h"
#include <iostream>
#include <limits>

namespace
{
int Checks = 0, Failures = 0;
void Expect(bool Condition, const char* Name)
{
    ++Checks;
    if (!Condition) { ++Failures; std::cerr << "FAIL " << Name << '\n'; }
}
bool Near(double A, double B) { return std::abs(A-B) < 1e-7; }
bool Equal(const MikdashUnits::PointCm& A, const MikdashUnits::PointCm& B)
{ return Near(A.X,B.X) && Near(A.Y,B.Y) && Near(A.Z,B.Z); }
MikdashCamera::SplinePath Build(const MikdashSceneUnits::IntroPoints& Points)
{
    std::vector<MikdashCamera::Vec3> Controls;
    for (const auto& P : Points) Controls.push_back({P.X,P.Y,P.Z});
    MikdashCamera::SplinePath Path;
    Expect(Path.Build(Controls, .5, 96), "production mixed path builds");
    return Path;
}
}
int main()
{
    using namespace MikdashSceneUnits;
    Frame Legacy;
    Frame Selected; Selected.CoordinateRevision = Revision::Selected48V1;
    IntroPoints LegacyPath, SelectedPath;
    AimPoints LegacyAim, SelectedAim;
    Expect(TryIntroPoints(Legacy, LegacyPath), "legacy path accepted");
    Expect(TryIntroPoints(Selected, SelectedPath), "selected path accepted");
    const IntroPoints ExpectedLegacy = LegacyIntroPoints();
    for (std::size_t I = 0; I < LegacyPath.size(); ++I)
        Expect(Equal(LegacyPath[I],ExpectedLegacy[I]), "legacy coordinates unchanged");
    Expect(LegacyPath.size()==19 && LegacyPath.front().X==140000, "active intro starts east with canonical19points");
    for (std::size_t I = 0; I <= 12; ++I)
        if (I != 3) Expect(Equal(SelectedPath[I],LegacyPath[I]), "geographic ridge/Kidron/deck fixed");
    Expect(Equal(SelectedPath[3],{112051.2,0,4800}), "precinct gate crossing uses precinct origin");
    Expect(Equal(SelectedPath[13],{7968,0,3668}), "gate lintel scales;500cm clearance preserved");
    Expect(Equal(SelectedPath[14],{7008,0,3316.16}), "pillar support scales;104cm clearance preserved");
    Expect(Equal(SelectedPath.back(),{2016,0,648}), "selected final eye is480+168");
    Expect(!Near(SelectedPath.back().Z,668*.96), "no scaling of human eye height");
    Expect(TryAimPoints(Legacy,LegacyAim) && TryAimPoints(Selected,SelectedAim), "both aim revisions accepted");
    Expect(Equal(SelectedAim[0],{-4704,0,3072}), "eastern approach aims at converted House");
    Expect(Equal(SelectedAim.back(),{-2352,0,1344}), "Temple target follows geometry");
    // Interleaved worlds cannot inherit the previously selected scene's path.
    IntroPoints LegacyAgain;
    Expect(TryIntroPoints(Legacy,LegacyAgain) && Equal(LegacyAgain.back(),{2100,0,668}), "legacy world after48 unchanged");
    const auto LegacySpline = Build(LegacyPath);
    const auto SelectedSpline = Build(SelectedPath);
    const auto SelectedEnd = SelectedSpline.PointAtEasedAlpha(1);
    const auto LegacyEnd = LegacySpline.PointAtEasedAlpha(1);
    Expect(Near(SelectedEnd.X,2016) && Near(SelectedEnd.Z,648), "selected spline reaches actual mixed-unit eye");
    Expect(Near(LegacyEnd.X,2100) && Near(LegacyEnd.Z,668), "legacy spline endpoint retained");
    for (int I = 0; I <= 100; ++I)
    {
        const auto P = SelectedSpline.PointAtEasedAlpha(static_cast<double>(I)/100);
        Expect(std::isfinite(P.X) && std::isfinite(P.Y) && std::isfinite(P.Z), "selected spline finite throughout");
    }
    Frame Pivot = Selected; Pivot.FixedOrigin = {-6200,0,0};
    IntroPoints PivotPath;
    Expect(TryIntroPoints(Pivot,PivotPath), "reviewed Aron pivot accepted");
    Expect(Equal(PivotPath.back(),{1768,0,648}), "pivot final eye follows temple floor with168cm height");
    Expect(Equal(PivotPath[3],SelectedPath[3]), "sanctuary pivot does not move precinct gate");
    Frame Offset = Selected; Offset.FixedOrigin = {100,200,50};
    MikdashUnits::PointCm P{7,8,9};
    Expect(TryLegacyTempleSupport(Offset,{2100,0,500},168,P) && Equal(P,{2020,8,650}), "nonzero origin plus physical eye");
    Expect(TryMetricPoint(Offset,{-14800,13900,400},P) && Equal(P,{-14800,13900,400}), "metric context unaffected by shifted origin");
    const MikdashUnits::PointCm Sentinel{7,8,9}; P = Sentinel;
    Frame Invalid = Selected; Invalid.SchemaVersion = 2;
    Expect(!TryLegacyTemplePoint(Invalid,{1,2,3},P) && Equal(P,Sentinel), "unknown schema refuses transactionally");
    Invalid = Selected; Invalid.CoordinateRevision = static_cast<Revision>(255);
    Expect(!TryLegacyTemplePoint(Invalid,{1,2,3},P) && Equal(P,Sentinel), "unknown unit revision refuses");
    Invalid = Selected; Invalid.FixedOrigin.Z = std::numeric_limits<double>::quiet_NaN();
    Expect(!TryMetricPoint(Invalid,{1,2,3},P) && Equal(P,Sentinel), "even metric input requires a valid scene frame");
    Expect(!TryLegacyTempleSupport(Selected,{1,2,3},-1,P) && Equal(P,Sentinel), "negative physical offset refuses");
    IntroPoints Unchanged = SelectedPath;
    Expect(!TryIntroPoints(Invalid,SelectedPath) && Equal(SelectedPath.back(),Unchanged.back()), "invalid path decode preserves output");
    std::cout << "MikdashSceneUnits: " << Checks << " checks, " << Failures << " failures\n";
    return Failures ? 1 : 0;
}
