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
    int Accepted=0,RefusedPhysicalLength=0,MetricPeople=0,AuthoredExtensions=0;
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
        const bool Extension=Person.Id=="chananel-ben-mattisyahu" || Person.Id=="rivka-bas-yoezer" || Person.Id=="nechemya-ben-tzuriel";
        if(Extension)
        {
            ++AuthoredExtensions;
            const bool South=Person.Id=="rivka-bas-yoezer";
            std::vector<MikdashRoute::Point2> Before,After;
            std::vector<double> Pauses;std::vector<std::string> Labels;
            for(std::size_t I=0;I<Person.Route.size();++I)
            {
                const auto& S=Person.Route[I];const auto& C=Converted.Route[I];
                Before.push_back({S.X*.96,S.Y*.96});After.push_back({C.X,C.Y});
                Pauses.push_back(C.PauseSeconds);Labels.push_back(C.Label);
                const double Adjustment=(South?(I<2):(I>=2))?(South?-25.0:25.0):0.0;
                Expect(Near(C.Y,S.Y*.96+Adjustment)&&Near(C.X,S.X*.96)&&Near(C.Z,288),"only exact outward edge gets25physicalcm");
                Expect(Same.Route[I].X==S.X&&Same.Route[I].Y==S.Y&&Same.Route[I].Z==S.Z,"legacy full rectangle remains exact");
                Expect(C.PauseSeconds==S.PauseSeconds&&C.Label==S.Label&&C.Action==S.Action,"extension preserves goals pauses and actions");
            }
            Expect(Near(MikdashRoute::LoopLengthCm(Before),5952)&&Near(MikdashRoute::LoopLengthCm(After),6002),"authored59.52m becomes60.02m");
            Expect(!MikdashRoute::ValidateLoopGeometry(Before,Pauses,Labels,&Error)
                &&MikdashRoute::ValidateLoopGeometry(After,Pauses,Labels,&Error),"unchanged production60m minimum enforced");
            for(std::size_t I=0;I<After.size();++I)
            {
                Expect(MikdashRoute::SegmentWithinCorridor(After[I],After[(I+1)%After.size()],Before),"new edge stays in original physical150cm corridor");
                const auto& A=After[I];const auto& B=After[(I+1)%After.size()];bool Inside=true;
                for(int J=0;J<=200;++J)
                { const double T=J/200.0;Inside=Inside&&PointInZone(Selected,Person.Where,{A.X+(B.X-A.X)*T,A.Y+(B.Y-A.Y)*T}); }
                Expect(Inside,"all authored extension segments remain in selected region");
            }
            MikdashPeople::Person Out;Out.Id="unchanged-output";
            auto Changed=Person;Changed.Route[0].X+=.001;
            Expect(!TryPerson(Selected,Changed,Out,Error)&&Out.Id=="unchanged-output","tiny source coordinate edit refuses transactionally");
            Changed=Person;Changed.Route[0].PauseSeconds=5;
            Expect(!TryPerson(Selected,Changed,Out,Error),"changed authored timing requires new review");
            Changed=Person;Changed.Route[0].LookX=7800;
            Expect(!TryPerson(Selected,Changed,Out,Error),"changed gaze signature refuses");
            Changed=Person;Changed.Role="pilgrim";
            Expect(!TryPerson(Selected,Changed,Out,Error),"known id cannot silently change role");
            Changed=Person;Changed.Id="unknown-short-loop";
            Expect(!TryPerson(Selected,Changed,Out,Error)&&Error=="loop length must be 60 to 120 m","unknown short loop is never generically stretched");
            auto MovedOrigin=Selected;MovedOrigin.FixedOrigin.X=10;
            Expect(!TryPerson(MovedOrigin,Person,Out,Error),"authored origin-zero extension refuses moved frame");
            auto Twice=Converted;const double BeforeRetry=Twice.Route[South?0:2].Y;
            Expect(!TryAuthoredRouteExtension(Selected,Person,Twice,Error)
                &&Twice.Route[South?0:2].Y==BeforeRetry,"direct repeated extension refuses without mutation");
        }
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
    Expect(Accepted==24&&RefusedPhysicalLength==0&&AuthoredExtensions==3,"all24 source routes pass with exactly3 reviewed extensions");
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
