#include "MikdashSurfaceAudioRouting.h"
#include <iostream>
#include <cstdlib>
using namespace MikdashSurfaceAudio;
static int Checks = 0;
static void Check(bool Passed) { ++Checks; if (!Passed) { std::cerr << "FAIL " << Checks << '\n'; std::exit(1); } }
int main()
{
    const wchar_t* P = L"/Game/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Surface";
    Check(Route(P,true,true)==Bank::RecordedStone);
    Check(Route(L"/Game/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Surface.SM_MountPlatform_Surface",true,true)==Bank::RecordedStone);
    Check(Route(L"/Game/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Surface.Imposter",true,true)==Bank::Silent);
    Check(Route(L"/Game/MikdashV3/FutureMountV1/Platform/SM_MountPlatform_Skirt",true,true)==Bank::Silent);
    Check(Route(P,false,true)==Bank::Silent);
    Check(Route(P,true,false)==Bank::Silent);
    Check(Route(nullptr,true,true)==Bank::Silent);
    Check(Route(L"",true,true)==Bank::Silent);
    Check(Route(L"/Game/MikdashV3/ArchitectureX/SM_Floor",true,true)==Bank::Silent);
    Check(Route(L"/Game/MikdashV3/Architecture/",true,true)==Bank::Silent);
    Check(Route(L"/Game/MikdashV3/Architecture/../Unknown",true,true)==Bank::Silent);
    Check(Route(L"/Game/MikdashV3/Architecture//Unknown",true,true)==Bank::Silent);
    Check(Route(L"/Game/MikdashV3/Architecture/SM_0146_floor_Heichal_clear_floor",true,true)==Bank::RecordedStone);
    Check(Route(L"/Game/MikdashV3/JerusalemContext/Terrain/SM_Terrain",true,true)==Bank::RecordedSoft);
    Check(Route(L"/Game/MikdashV3/JerusalemContext/Streets/SM_Path",true,true)==Bank::RecordedStone);
    Check(Route(L"/Game/MikdashV3/JerusalemContext/Buildings/SM_Building",true,true)==Bank::RecordedStone);
    Check(Route(L"/Game/MikdashV3/ArrivalReview/BusStudyV1/Meshes/SM_BusStudyV1_Rubber",true,true)==Bank::Silent);
    Check(Route(L"/Game/MikdashV3/MaterialReview/SanctuaryPalmReliefV1/Meshes/SM_Relief",true,true)==Bank::Silent);
    // Fixture path intentionally fictional: production access importer has no frozen destination yet.
    const wchar_t* Access=L"/Game/Test/VerifiedAccess";
    Registration Evidence[]={{Access,Bank::RecordedStone}};
    Check(Route(Access,true,true)==Bank::Silent);
    Check(Route(Access,true,true,Evidence,1)==Bank::RecordedStone);
    Check(Route(L"/Game/Test/VerifiedAccessOther",true,true,Evidence,1)==Bank::Silent);
    Registration Deny[]={{P,Bank::Silent}};
    Check(Route(P,true,true,Deny,1)==Bank::Silent);
    Registration Conflict[]={{P,Bank::RecordedStone},{P,Bank::RecordedSoft}};
    Check(Route(P,true,true,Conflict,2)==Bank::Silent);
    Check(Route(P,true,true,nullptr,1)==Bank::Silent);
    std::cout << "PASS " << Checks << " actual-header routing checks\n";
}
