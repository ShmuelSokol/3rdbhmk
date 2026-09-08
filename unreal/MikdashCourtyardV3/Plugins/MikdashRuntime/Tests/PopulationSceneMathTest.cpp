#include "PopulationSceneMath.h"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
namespace
{
int Checks=0,Failures=0;
void Expect(bool Okay,const char* Name) { ++Checks;if(!Okay){++Failures;std::cerr<<"FAIL "<<Name<<'\n';} }
std::string ReadAll(const std::filesystem::path& Path)
{
    std::ifstream Input(Path,std::ios::binary);
    return std::string((std::istreambuf_iterator<char>(Input)),std::istreambuf_iterator<char>());
}
std::vector<MikdashRoute::Point2> Scaled(const std::vector<MikdashRoute::Point2>& Points,double Ratio)
{
    std::vector<MikdashRoute::Point2> Out;
    for(const auto& P:Points) Out.push_back({P.X*Ratio,P.Y*Ratio});
    return Out;
}
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
    Expect(TryLook(Selected,{5000,1180,300},Look)&&Near(Look.X,4800)&&Near(Look.Y,1132.8)&&Near(Look.Z,288),"pilot group anchor follows Temple frame");
    Expect(TryLook(Legacy,{5000,1180,300},Look)&&Near(Look.X,5000)&&Near(Look.Y,1180)&&Near(Look.Z,300),"pilot group anchor unchanged at legacy");
    Expect(!TryLook(Selected,{5000,1180,0},Look)&&!TryLook(Selected,{5000,1181,300},Look),"group anchor allowlist is exact");
    Expect(!TryLook(Selected,{11111,22222,33333},Look),"unclassified gaze refused");

    // Measured hollow shells: legacy rectangles converted by the frame, padded physically.
    const auto Shells=OuterCourtShellFootprints();
    Expect(Shells.size()==8,"eight measured shell footprints");
    Expect(TryFootprint(Selected,{Shells[1].Legacy,ResidentCapsuleRadiusCm,ResidentCapsuleRadiusCm},R)
        &&Near(R.MaxX,2688+34)&&Near(R.MaxY,2688+34)&&Near(R.MinX,-2688-34),"platform shell converts to measured 2688 face plus physical radius");
    Expect(TryFootprint(Legacy,{Shells[1].Legacy,ResidentCapsuleRadiusCm,ResidentCapsuleRadiusCm},R)
        &&Near(R.MaxX,2834),"platform shell unscaled at legacy plus radius");
    Expect(TryFootprint(Selected,{Shells[0].Legacy,ResidentCapsuleRadiusCm,ResidentCapsuleRadiusCm},R)&&Near(R.MaxX,1608+34),"west step tread face 1608 at 48");
    std::string Error;
    const std::vector<MikdashRoute::Point2> OldYoav={{1675,1050},{3125,1050},{3125,2750},{1675,2750}};
    Expect(!TryShellClearance(Legacy,OldYoav,Error)&&Error.find("hollow architecture shell")!=std::string::npos,"loop inside the platform shell refused at legacy");
    Expect(!TryShellClearance(Selected,Scaled(OldYoav,.96),Error),"loop inside the platform shell refused at 48");
    const std::vector<MikdashRoute::Point2> OldRivka={{1550,-3500},{2850,-3500},{2850,-1700},{1550,-1700}};
    Expect(!TryShellClearance(Legacy,OldRivka,Error)&&Error.find("west terrace")!=std::string::npos,"terrace riser loop names the west steps");
    const std::vector<MikdashRoute::Point2> ClearLoop={{3700,1050},{5150,1050},{5150,2750},{3700,2750}};
    Expect(TryShellClearance(Legacy,ClearLoop,Error)&&Error.empty(),"loop 66 cm east of the E plinth clear at legacy");
    Expect(TryShellClearance(Selected,Scaled(ClearLoop,.96),Error),"same loop clear at 48 (96 cm from the 3456 face)");
    const std::vector<MikdashRoute::Point2> Grazing={{3633,1050},{5150,1050},{5150,2750},{3633,2750}};
    Expect(!TryShellClearance(Legacy,Grazing,Error),"capsule radius overlapping the plinth face refused at legacy");
    const std::vector<MikdashRoute::Point2> Kitchen={{5375,5250},{6825,5250},{6825,5450},{5375,5450}};
    Expect(!TryShellClearance(Legacy,Kitchen,Error)&&Error.find("kitchen")!=std::string::npos,"corner kitchen court is a shell");
    const std::vector<MikdashRoute::Point2> OnlyLegSamples={{2400,-3400},{5050,-3400},{5050,-2900},{2400,-2900}};
    Expect(TryShellClearance(Selected,Scaled(OnlyLegSamples,.96),Error),"lane loop between platform and N plinth clear at 48");
    Expect(!TryShellClearance(Selected,{{4000,1000}},Error),"a single point is not a loop");

    // Exercise production JSON parsing and source data, then the exact runtime decoder.
    const auto Root=std::filesystem::path(__FILE__).parent_path().parent_path().parent_path().parent_path();
    const std::string Text=ReadAll(Root/"Content/Distribution/People/people.json");
    const std::string Text48=ReadAll(Root/"Content/Distribution/People/people-candidate48.json");
    MikdashPeople::Directory Directory,Directory48;
    Expect(!Text.empty()&&MikdashPeople::ReadDirectoryText(Text,Directory,Error),"real staged legacy directory parses");
    Expect(!Text48.empty()&&MikdashPeople::ReadDirectoryText(Text48,Directory48,Error),"real staged candidate48 directory parses");
    Expect(Directory.Version=="people-v3"&&Directory48.Version=="people-v3","both directories stay people-v3");
    Expect(Directory.People.size()==Directory48.People.size(),"both directories carry the same people");
    for(std::size_t I=0;I<Directory.People.size()&&I<Directory48.People.size();++I)
    {
        const auto& A=Directory.People[I];const auto& B=Directory48.People[I];
        bool SameRoute=A.Id==B.Id&&A.Role==B.Role&&A.Route.size()==B.Route.size()&&A.Dialog==B.Dialog&&A.Laps==B.Laps;
        for(std::size_t J=0;SameRoute&&J<A.Route.size();++J)
            SameRoute=A.Route[J].X==B.Route[J].X&&A.Route[J].Y==B.Route[J].Y&&A.Route[J].Z==B.Route[J].Z
                &&A.Route[J].PauseSeconds==B.Route[J].PauseSeconds&&A.Route[J].Label==B.Route[J].Label&&A.Route[J].Action==B.Route[J].Action
                &&A.Route[J].LookX==B.Route[J].LookX&&A.Route[J].LookY==B.Route[J].LookY&&A.Route[J].LookZ==B.Route[J].LookZ;
        Expect(SameRoute,"candidate48 file carries the same legacy source routes as people.json");
    }
    int Accepted=0,Refused=0,MetricPeople=0,AuthoredExtensions=0,FallThroughNotes=0;
    for(const auto& Person:Directory.People)
    {
        MikdashPeople::Person Same,Converted;std::string Note,LegacyNote;
        Expect(TryPerson(Legacy,Person,Same,Error,&LegacyNote),"legacy source behavior preserved");
        Expect(LegacyNote.empty(),"legacy frame never reports an extension note");
        Expect(Same.Route.size()==Person.Route.size()&&Near(Same.Route[0].X,Person.Route[0].X)
            &&Near(Same.Route[0].Z,Person.Route[0].Z),"legacy route coordinates not rewritten");
        if(!TryPerson(Selected,Person,Converted,Error,&Note))
        {
            std::cerr<<"refused "<<Person.Id<<": "<<Error<<'\n';
            ++Refused;continue;
        }
        ++Accepted;
        const bool Locked=Person.Id=="chananel-ben-mattisyahu" || Person.Id=="rivka-bas-yoezer" || Person.Id=="nechemya-ben-tzuriel";
        LockedRouteSignature Lock;
        const bool Extension=Locked&&LockedRouteFor(Person.Id,Lock)&&LockedSignatureMatches(Person,Lock);
        if(Extension)
        {
            ++AuthoredExtensions;
            Expect(Note.empty(),"a matching signature reports no fall-through note");
            const bool South=Lock.First==0;
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
            // Signature changes fall through to the standard classifier instead of refusing.
            MikdashPeople::Person Out;Out.Id="unchanged-output";std::string Why,ChangeNote;
            auto Changed=Person;Changed.Route[0].X+=.001;
            auto Untouched=Changed;
            for(auto& W:Untouched.Route) { W.X*=.96;W.Y*=.96;W.Z*=.96; }
            auto Probe=Untouched;
            Expect(TryAuthoredRouteExtension(Selected,Changed,Probe,Why,&ChangeNote)&&!ChangeNote.empty()
                &&Probe.Route[2].Y==Untouched.Route[2].Y&&Probe.Route[3].Y==Untouched.Route[3].Y,"changed signature: extension returns true without extending and reports a note");
            Expect(!TryPerson(Selected,Changed,Out,Error,&ChangeNote)&&Out.Id=="unchanged-output"
                &&Error=="loop length must be 60 to 120 m"&&!ChangeNote.empty(),"changed signature: the standard classifier refuses the unextended 59.52 m loop");
            Changed=Person;Changed.Route[0].PauseSeconds=5;
            Expect(!TryPerson(Selected,Changed,Out,Error,&ChangeNote)&&Error=="loop length must be 60 to 120 m"&&!ChangeNote.empty(),"changed timing falls through to the standard classifier");
            Changed=Person;Changed.Route[0].LookX=7800;
            Expect(!TryPerson(Selected,Changed,Out,Error,&ChangeNote)&&Error=="loop length must be 60 to 120 m"&&!ChangeNote.empty(),"changed gaze falls through to the standard classifier");
            Changed=Person;Changed.Role="pilgrim";
            Expect(!TryPerson(Selected,Changed,Out,Error,&ChangeNote)&&Error=="loop length must be 60 to 120 m"&&!ChangeNote.empty(),"changed role falls through; the classifier still refuses the short loop");
            Changed=Person;for(auto& W:Changed.Route) if(Near(W.Y,Lock.Expected.MaxY)) W.Y+=50;
            Expect(TryPerson(Selected,Changed,Out,Error,&ChangeNote)&&!ChangeNote.empty()&&Out.Id==Person.Id
                &&Near(Out.Route[Lock.First].Y,(Lock.Expected.MaxY+50)*.96)&&Near(Out.Route[Lock.First+1].Y,(Lock.Expected.MaxY+50)*.96),
                "an authored enlargement passes the standard classifier with no extension applied");
            std::vector<MikdashRoute::Point2> Enlarged;
            for(const auto& W:Out.Route) Enlarged.push_back({W.X,W.Y});
            Expect(Near(MikdashRoute::LoopLengthCm(Enlarged),6048),"authored 63 m enlargement is 60.48 m at 48 on its own");
            Changed=Person;Changed.Id="unknown-short-loop";
            Expect(!TryPerson(Selected,Changed,Out,Error,&ChangeNote)&&Error=="loop length must be 60 to 120 m"&&ChangeNote.empty(),"unknown short loop is never generically stretched and has no note");
            auto MovedOrigin=Selected;MovedOrigin.FixedOrigin.X=10;
            Expect(!TryPerson(MovedOrigin,Person,Out,Error),"authored origin-zero extension refuses moved frame");
            auto Twice=Converted;const double BeforeRetry=Twice.Route[South?0:2].Y;
            Expect(!TryAuthoredRouteExtension(Selected,Person,Twice,Error)
                &&Twice.Route[South?0:2].Y==BeforeRetry,"direct repeated extension refuses without mutation");
        }
        else if(Locked)
        {
            ++FallThroughNotes;
            Expect(!Note.empty()&&Note.find(Person.Id)!=std::string::npos,"changed locked route reports the fall-through once with its id");
            std::vector<MikdashRoute::Point2> Points;
            for(std::size_t I=0;I<Person.Route.size();++I)
            {
                const auto& S=Person.Route[I];const auto& C=Converted.Route[I];
                Expect(Near(C.X,S.X*.96)&&Near(C.Y,S.Y*.96)&&Near(C.Z,288),"fallen-through route is the exact .96 conversion, no 25 cm edge");
                Points.push_back({C.X,C.Y});
            }
            Expect(MikdashRoute::LoopLengthCm(Points)>=6000.0,"fallen-through route meets the physical 60 m minimum on its own");
        }
        else Expect(Note.empty(),"unlocked routes report no note");
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
            std::vector<MikdashRoute::Point2> Points;
            for(const auto& W:Converted.Route) Points.push_back({W.X,W.Y});
            Expect(TryShellClearance(Selected,Points,Error),"every staged outer-court loop clears the measured shells at 48");
            MikdashPeople::Person Twice;
            Expect(!TryPerson(Selected,Converted,Twice,Error),"already converted resident input refused");
        }
    }
    Expect(Accepted>0&&MetricPeople>0,"both Temple and geographic populations survive conversion");
    Expect(Accepted==24&&Refused==0,"all24 staged routes pass the selected48 decoder");
    Expect(AuthoredExtensions==1&&FallThroughNotes==2,"only Chananel keeps the reviewed extension; Rivka and Nechemya fall through by design");
    if(!Directory.People.empty())
    {
        auto Invalid=Selected;Invalid.SchemaVersion=2;
        MikdashPeople::Person Out;
        Expect(!TryPerson(Invalid,Directory.People[0],Out,Error),"invalid world schema cannot start residents");
    }
    std::cout<<"PopulationSceneMath: "<<Checks<<" checks, "<<Failures<<" failures; candidate routes "
        <<Accepted<<" accepted, "<<Refused<<" refused, "<<AuthoredExtensions<<" extension, "<<FallThroughNotes<<" fall-through notes\n";
    return Failures?1:0;
}
