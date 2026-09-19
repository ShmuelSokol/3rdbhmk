#include "CrowdGroundMath.h"
#include "CrowdGroupMath.h"
#include "../Source/MikdashRuntime/Private/CrowdKotelGroundData.h"
#include "../Source/MikdashRuntime/Private/CrowdStreetGroundData.h"
#include <iostream>
int main()
{
    using namespace MikdashCrowdGround;
    int Fail=0;
    auto Check=[&](bool Good,const char* Why){if(!Good){++Fail;std::cerr<<Why<<'\n';}};
    const Triangle Faces[]={{{0,0,10},{10,0,20},{0,10,30}},{{0,0,0},{0,0,1},{0,0,2}}};
    Check(std::abs(TerrainHeight(Faces,2,3)-18)<1e-10,"barycentric slope");
    Check(std::abs(TerrainHeight(Faces,5,5)-25)<1e-10,"triangle boundary");
    Check(!std::isfinite(TerrainHeight(Faces,8,8)),"outside is not extrapolated");
    Check(!std::isfinite(TerrainHeight(Faces,Missing(),0)),"NaN is refused");
    const DeckRect Decks[]={{0,0,10,10,100},{5,5,15,15,125}};
    Check(DeckHeight(Decks,6,6)==125,"highest deck top");
    Check(!std::isfinite(DeckHeight(Decks,20,20)),"uncovered deck has no invented floor");
    // Independent native contacts from the retained pre-fix diagnosis.
    const double Plaza=DeckHeight(CrowdKotelGroundData::Plaza,-15701.651815,15185.028171);
    Check(std::abs(Plaza+1234.594)<1e-6,"plaza uses paving, not buried terrain");
    Check(std::abs(Plaza+1234.552579)<.05,"matches initialized native paving");
    const double A=TerrainHeight(CrowdKotelGroundData::Approach,-17493.716185,19663.014450);
    const double B=TerrainHeight(CrowdKotelGroundData::Approach,-18304.046321,20059.048569);
    Check(std::abs(A+1556.211004)<.01,"approach native contact A");
    Check(std::abs(B+1494.023615)<.01,"approach native contact B");
    double Moved=0;
    Check(MikdashCrowdGroups::FollowPlane(A+.04,A,B,Moved)&&std::abs(Moved-(B+.04))<1e-8,
          "movement follows exact surface difference and retains contact offset");
    Check(!MikdashCrowdGroups::FollowPlane(A,A,Missing(),Moved),"movement cannot cross missing support");
    const double StreetTerrain=TerrainHeight(CrowdStreetGroundData::Street,-37409.103863,47107.001752);
    Check(std::abs(StreetTerrain-889.5093043147889)<.001,"street uses original terrain after fallback repair");
    Check(std::abs(TerrainHeight(CrowdStreetGroundData::Street,-37840.18529,46646.836323)-980.810144)<.001,
          "street chooses native asphalt above terrain");
    bool Covered=true;
    for(int X=0;X<=100;++X) for(int Y=0;Y<=100;++Y)
        Covered=Covered && std::isfinite(TerrainHeight(CrowdStreetGroundData::Street,-38800+22.*X,46200+13.*Y));
    Check(Covered,"entire street zone has support on 101x101 grid");
    Check(!std::isfinite(TerrainHeight(CrowdStreetGroundData::Street,0,0)),"street does not invent distant ground");
    std::cout<<"Crowd ground checks: "<<(Fail?"FAIL":"PASS")<<'\n';
    return Fail?1:0;
}
