#include "PopulationSceneMath.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
namespace
{
int Checks=0,Failures=0;
void Expect(bool Okay,const char* Name) { ++Checks;if(!Okay){++Failures;std::cerr<<"FAIL "<<Name<<'\n';} }
}
int main()
{
    using namespace MikdashPopulationScene;
    MikdashSceneUnits::Frame Legacy,Selected;Selected.CoordinateRevision=MikdashSceneUnits::Revision::Selected48V1;
    Expect(CrowdZoneScope("OuterCourtEast")==Scope::Temple,"court scope explicit");
    Expect(CrowdZoneScope("KotelPlazaStrip")==Scope::Metric && CrowdZoneScope("StreetBateiMahase")==Scope::Metric,"geographic scopes explicit");
    Expect(CrowdZoneScope("NewAmbiguousZone")==Scope::Unknown,"unknown scope refuses inference");
    PaddedFootprint Source;Rect R;
    Expect(Footprint("EastGateCorridor",Source) && TryFootprint(Selected,Source,R),"known footprint converted");
    Expect(Near(R.MinX,2300)&&Near(R.MaxX,8356)&&Near(R.MinY,-722)&&Near(R.MaxY,722),"architecture footprint with unchanged100/50 pads");
    Expect(!Near(R.MinX,2400*.96),"not blanket scaling baked physical padding");
    std::vector<MikdashRoute::Point2> Corners={{2400,-750},{8700,-750},{8700,750},{2400,750}};
    Expect(IsRect(Corners,Padded(Source)),"audited legacy padded footprint recognized");
    Corners[0].X*=.96;
    Expect(!IsRect(Corners,Padded(Source)),"already converted or edited footprint rejected");
    Expect(TryFootprint(Legacy,Source,R)&&Near(R.MinX,2400)&&Near(R.MaxY,750),"legacy footprint unchanged");
    Expect(TryFootprint(Selected,{{4700,900,5300,1450},-34,-34},R)
        &&Near(R.MinX,4546)&&Near(R.MaxX,5054),"pilot physical capsule inset remains34");
    double Floor=0;
    Expect(TryFloor(Selected,MikdashPeople::Zone::OuterCourt,Floor)&&Near(Floor,288),"selected resident support288");
    Expect(TryFloor(Selected,MikdashPeople::Zone::MountDeck,Floor)&&Near(Floor,0),"geographic mount floor retained");
    MikdashUnits::PointCm Look;
    Expect(TryLook(Selected,{11500,0,0},Look)&&Near(Look.X,11500),"deck arrival gaze metric");
    Expect(TryLook(Selected,{8600,0,0},Look)&&Near(Look.X,8256),"deck visitor gate gaze follows Temple");
    Expect(!TryLook(Selected,{11111,22222,33333},Look),"unclassified gaze refused");

    // Exercise production JSON parsing and source data, then the exact runtime decoder.
    const auto Root=std::filesystem::path(__FILE__).parent_path().parent_path().parent_path().parent_path();
    std::ifstream Input(Root/"Content/Distribution/People/people.json",std::ios::binary);
    const std::string Text((std::istreambuf_iterator<char>(Input)),std::istreambuf_iterator<char>());
    MikdashPeople::Directory Directory;std::string Error;
    Expect(!Text.empty()&&MikdashPeople::ReadDirectoryText(Text,Directory,Error),"real staged legacy directory parses");
    int Accepted=0,RefusedPhysicalLength=0,MetricPeople=0;
    for(const auto& Person:Directory.People)
    {
        MikdashPeople::Person Same,Converted;
        Expect(TryPerson(Legacy,Person,Same,Error),"legacy source behavior preserved");
        Expect(Same.Route.size()==Person.Route.size()&&Near(Same.Route[0].X,Person.Route[0].X)
            &&Near(Same.Route[0].Z,Person.Route[0].Z),"legacy route coordinates not rewritten");
        if(!TryPerson(Selected,Person,Converted,Error))
        {
            Expect(Error=="loop length must be 60 to 120 m","candidate rejection has explicit physical length reason");
            ++RefusedPhysicalLength;continue;
        }
        ++Accepted;
        Expect(Converted.Dialog==Person.Dialog&&Converted.Mission==Person.Mission&&Converted.Role==Person.Role
            &&Converted.Laps==Person.Laps,"personality goals and roles unchanged");
        if(Person.Where==MikdashPeople::Zone::MountDeck)
        {
            ++MetricPeople;
            for(std::size_t I=0;I<Person.Route.size();++I)
                Expect(Near(Converted.Route[I].X,Person.Route[I].X)&&Near(Converted.Route[I].Y,Person.Route[I].Y)
                    &&Near(Converted.Route[I].Z,Person.Route[I].Z),"metric resident route fixed");
        }
        else
        {
            Expect(Near(Converted.Route[0].X,Person.Route[0].X*.96)&&Near(Converted.Route[0].Z,288),"Temple route feet converted");
            MikdashPeople::Person Twice;
            Expect(!TryPerson(Selected,Converted,Twice,Error),"already converted resident input refused");
        }
    }
    Expect(Accepted>0&&MetricPeople>0,"both Temple and geographic populations survive conversion");
    if(!Directory.People.empty())
    {
        auto Invalid=Selected;Invalid.SchemaVersion=2;
        MikdashPeople::Person Out;
        Expect(!TryPerson(Invalid,Directory.People[0],Out,Error),"invalid world schema cannot start residents");
    }
    std::cout<<"PopulationSceneMath: "<<Checks<<" checks, "<<Failures<<" failures; candidate routes "
        <<Accepted<<" accepted, "<<RefusedPhysicalLength<<" below physical length requirement\n";
    return Failures?1:0;
}
