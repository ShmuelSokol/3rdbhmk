#include "MikdashUnits.h"
#include <iostream>
#include <limits>
#include <cmath>
namespace
{
int Checks=0,Failures=0;
void Expect(bool Condition,const char* Name) { ++Checks; if(!Condition) { ++Failures; std::cerr<<"FAIL "<<Name<<"\n"; } }
bool Near(double A,double B) { return std::abs(A-B)<1e-8; }
bool Equal(const MikdashUnits::PointCm& A,const MikdashUnits::PointCm& B) { return Near(A.X,B.X)&&Near(A.Y,B.Y)&&Near(A.Z,B.Z); }
}
int main()
{
    using namespace MikdashUnits;
    Expect(LegacyArchitectureCmPerAmah==50,"legacy constant preserved");
    Expect(SelectedBookCmPerAmah==48,"selected book constant explicit");
    Expect(Near(LegacyArchitectureToSelectedFactor,.96),"factor 48/50");
    Expect(LegacyArchitectureAmotToCm(3000)==150000,"historical enclosure preserved");
    Expect(SelectedBookAmotToCm(3000)==144000,"selected enclosure 1440m");
    Expect(SelectedBookAmotToCm(500)==24000,"selected 500 amah square 240m");
    Expect(SelectedBookAmotToCm(2)==96 && SelectedBookAmotToCm(1)==48 && SelectedBookAmotToCm(3)==144,"table book dimensions");
    Expect(SelectedBookTefachimToCm(1)==8,"tefach eight cm");
    Expect(SelectedFiveTefachAmotToCm(1)==40 && SelectedFiveTefachAmotToCm(2)==80,"five-tefach altar dimensions");
    Expect(LegacyArchitectureCmToSelectedCm(125)==120,"125cm amah-derived vessel becomes120");
    const PointCm Zero{}; PointCm Result;
    Expect(TryScaleLegacyArchitecturePoint({-8100,-9450,0},Zero,Result)&&Equal(Result,{-7776,-9072,0}),"architecture min bound");
    Expect(TryScaleLegacyArchitecturePoint({9200,9450,6130},Zero,Result)&&Equal(Result,{8832,9072,5884.8}),"architecture max bound");
    const PointCm Anchor{1000,-2000,250};
    Expect(TryScaleLegacyArchitecturePoint(Anchor,Anchor,Result)&&Equal(Result,Anchor),"nonzero origin fixed");
    Expect(TryScaleLegacyArchitecturePoint({1100,-2200,550},Anchor,Result)&&Equal(Result,{1096,-2192,538}),"scale displacement about origin, not absolute location");
    Expect(TryPlaceAboveMigratedFloor({4900,1000,300},Zero,96,Result)&&Equal(Result,{4704,960,384}),"capsule height unscaled");
    Expect(!Near(Result.Z,396*.96),"reject naive scaling of capsule centre");
    Expect(TryPlaceAboveMigratedFloor({4900,1000,300},Zero,160,Result)&&Near(Result.Z,448),"eye height remains160cm");
    Expect(TryPlaceAboveFloor({4704,960,288},96,Result)&&Equal(Result,{4704,960,384}),"already migrated floor not scaled twice");
    Expect(Equal(DecodeLegacySourceAmot(1,2,3),{50,150,100}),"legacy axis swap and50cm intact");
    const PointCm Kotel{-15678.015,8682.933,-1399.695};
    Expect(Equal(PreserveMetricContext(Kotel),Kotel),"geographic context remains fixed");
    const PointCm Sentinel{7,8,9}; Result=Sentinel;
    Expect(!TryScaleLegacyArchitecturePoint({std::numeric_limits<double>::infinity(),0,0},Zero,Result)&&Equal(Result,Sentinel),"nonfinite point transactional refusal");
    Expect(!TryScaleLegacyArchitecturePoint(Zero,{0,std::numeric_limits<double>::quiet_NaN(),0},Result)&&Equal(Result,Sentinel),"nonfinite origin refusal");
    Expect(!TryPlaceAboveMigratedFloor(Zero,Zero,-1,Result)&&Equal(Result,Sentinel),"negative physical height refusal");
    Expect(!TryPlaceAboveFloor(Zero,std::numeric_limits<double>::infinity(),Result)&&Equal(Result,Sentinel),"infinite offset refusal");
    const double Huge=std::numeric_limits<double>::max();
    Expect(!TryScaleLegacyArchitecturePoint({Huge,0,0},{-Huge,0,0},Result)&&Equal(Result,Sentinel),"overflow refusal");
    Expect(!TryPlaceAboveFloor({0,0,Huge},Huge,Result)&&Equal(Result,Sentinel),"placement overflow refusal");
    std::cout<<"MikdashUnits checks="<<Checks<<" failures="<<Failures<<"\n";return Failures?1:0;
}
