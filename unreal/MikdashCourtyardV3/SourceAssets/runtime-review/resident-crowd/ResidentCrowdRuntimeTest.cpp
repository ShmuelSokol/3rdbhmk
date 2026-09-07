#include "ResidentCrowdRuntime.h"
#include <cstdlib>
#include <iostream>
#include <fstream>
using namespace MikdashCrowd;
static unsigned Checks = 0;
#define CHECK(X) do { ++Checks; if (!(X)) { std::cerr << "FAIL line " << __LINE__ << ": " #X "\n"; std::exit(1); } } while (false)

static std::vector<Identity> Plans()
{
    return {
        {"a", "Authored visitor A", "meeting", SourceRole::Visitor,
            {{"talk", "Meet group", "meeting", "conversation", 3, 7},
             {"walk", "Visit lane", "lane", "observe", 15, 11}}},
        {"b", "Authored visitor B", "meeting", SourceRole::Visitor,
            {{"look", "Observe", "meeting", "look-around", 5, 13},
             {"walk", "Visit lane", "lane", "rest", 20, 17}}}
    };
}
static std::vector<Route> Paths()
{
    return {{"out", "meeting", "lane", "door", 1, 30},
            {"back", "lane", "meeting", "door", 1, 30}};
}
static Runtime World() { Runtime R; CHECK(R.Configure(Plans(), Paths())); return R; }
static const Person& Get(const Runtime& R, const char* Id) { CHECK(R.Find(Id)); return *R.Find(Id); }
static void Ready(Runtime& R)
{
    CHECK(R.SetAccess("a", true)); CHECK(R.SetAccess("b", true)); CHECK(R.Advance(20));
    CHECK(Get(R,"a").Completions[0] == 10); CHECK(Get(R,"b").Completions[0] == 18);
    CHECK(!Get(R,"a").Access); CHECK(R.SetAccess("a",true)); CHECK(R.SetAccess("b",true));
}
static void SchedulePauseAndVariation()
{
    Runtime R = World();
    CHECK(R.Advance(100)); CHECK(Get(R,"a").Completions.empty()); // fails closed
    R = World(); CHECK(R.SetAccess("a",true)); CHECK(R.SetAccess("b",true));
    CHECK(R.Advance(4)); CHECK(Get(R,"a").Remaining == 6); CHECK(Get(R,"b").Remaining == 13);
    R.SetPaused(true); CHECK(R.Advance(99999)); CHECK(R.Now()==4); CHECK(Get(R,"a").Remaining==6);
    R.SetPaused(false); CHECK(R.Advance(6)); CHECK(Get(R,"a").Completions[0]==10);
    CHECK(Get(R,"b").Remaining==8); CHECK(Get(R,"a").State==Phase::AccessReview);
    CHECK(R.SetNear("a",true)); const std::string Saved=R.Save();
    Runtime Loaded=World(); CHECK(Loaded.Load(Saved)); CHECK(Loaded.Save()==Saved);
    CHECK(Get(Loaded,"a").Near); CHECK(!Get(Loaded,"b").Access);
    CHECK(Loaded.SetAccess("b",true)); CHECK(Loaded.Advance(8)); CHECK(Get(Loaded,"b").Completions[0]==18);
}
static void ReservationsAndCallbacks()
{
    Runtime R=World(); Ready(R);
    const Seconds A=R.Reserve("a","out"); CHECK(A!=0); CHECK(R.Reserve("b","out")==0);
    CHECK(R.Reserve("a","out")==0); CHECK(R.Reserve("b","back")==0);
    CHECK(!R.Arrive("a",A+1,"lane")); CHECK(!R.Arrive("a",A,"meeting"));
    R.SetPaused(true); CHECK(!R.Arrive("a",A,"lane")); CHECK(R.Advance(100)); CHECK(R.Now()==20);
    R.SetPaused(false); CHECK(R.Advance(29)); CHECK(Get(R,"a").Completions.size()==1);
    CHECK(R.Arrive("a",A,"lane")); CHECK(!R.Arrive("a",A,"lane"));
    const Seconds B=R.Reserve("b","out"); CHECK(B>A); CHECK(R.Advance(11));
    CHECK(Get(R,"a").State==Phase::Complete); CHECK(Get(R,"a").Completions[1]==60);
    CHECK(R.Arrive("b",B,"lane")); CHECK(R.Advance(17)); CHECK(Get(R,"b").State==Phase::Complete);
    CHECK(R.Advance(10000)); CHECK(Get(R,"b").Completions.size()==2);
}
static void TimeoutAndRevocation()
{
    Runtime R=World(); Ready(R); const Seconds A=R.Reserve("a","out");
    CHECK(R.Advance(30)); CHECK(Get(R,"a").State==Phase::StopRequested);
    CHECK(!R.Arrive("a",A,"lane")); CHECK(R.Reserve("b","out")==0); // still occupies doorway
    CHECK(!R.AcknowledgeStopped("a",A+1)); CHECK(R.AcknowledgeStopped("a",A));
    CHECK(Get(R,"a").Location=="meeting"); CHECK(!Get(R,"a").Access);
    const Seconds B=R.Reserve("b","out"); CHECK(B!=0); CHECK(R.SetAccess("b",false));
    CHECK(Get(R,"b").State==Phase::StopRequested); CHECK(R.SetAccess("b",true));
    CHECK(Get(R,"b").State==Phase::StopRequested); CHECK(!R.Arrive("b",B,"lane"));
    CHECK(R.AcknowledgeStopped("b",B)); CHECK(R.SetAccess("a",true));
    const Seconds A2=R.Reserve("a","out"); CHECK(A2>A); CHECK(!R.Arrive("a",A,"lane"));
    CHECK(R.Arrive("a",A2,"lane")); CHECK(R.Advance(5)); CHECK(Get(R,"a").Remaining==6);
    CHECK(R.SetAccess("a",false)); CHECK(R.Advance(500)); CHECK(Get(R,"a").Remaining==6);
    CHECK(R.SetAccess("a",true)); CHECK(R.Advance(6)); CHECK(Get(R,"a").State==Phase::Complete);
}
static void Persistence(const char* File)
{
    Runtime R=World(); Ready(R); const Seconds Old=R.Reserve("a","out");
    R.SetPaused(true); const std::string Saved=R.Save();
    { std::ofstream Out(File, std::ios::binary); CHECK(bool(Out)); Out << Saved; CHECK(bool(Out)); }
    std::ifstream In(File,std::ios::binary); std::ostringstream Buffer; Buffer << In.rdbuf();
    Runtime Loaded=World(); CHECK(Loaded.Load(Buffer.str())); CHECK(Loaded.IsPaused());
    CHECK(Get(Loaded,"a").RouteId.empty()); CHECK(Get(Loaded,"a").Location=="meeting");
    CHECK(!Loaded.Arrive("a",Old,"lane")); Loaded.SetPaused(false); CHECK(Loaded.SetAccess("a",true));
    const Seconds Fresh=Loaded.Reserve("a","out"); CHECK(Fresh>Old);
    CHECK(!Loaded.Arrive("a",Old,"lane")); CHECK(Loaded.Arrive("a",Fresh,"lane"));
    CHECK(Loaded.Advance(4)); const std::string Partial=Loaded.Save();
    Runtime Again=World(); CHECK(Again.Load(Partial)); CHECK(Get(Again,"a").Remaining==7);
    CHECK(Again.SetAccess("a",true)); CHECK(Again.Advance(7)); CHECK(Get(Again,"a").Completions.size()==2);
    const std::string Before=Again.Save(); CHECK(!Again.Load(Partial+"garbage")); CHECK(Again.Save()==Before);
    CHECK(!Again.Load("MIKDASH_CROWD 1 -1")); CHECK(Again.Save()==Before);
    CHECK(!Again.Load(Partial.substr(0,Partial.size()/2))); CHECK(Again.Save()==Before);
    std::string Corrupt=Partial; Corrupt.replace(Corrupt.find("\"a\""),3,"\"alien\"");
    CHECK(!Again.Load(Corrupt)); CHECK(Again.Save()==Before);
    auto Changed=Plans(); Changed[0].Goals[0].Duration=8;
    Runtime Other; CHECK(Other.Configure(Changed,Paths())); CHECK(!Other.Load(Partial));
    CHECK(Loaded.Load(Saved)); // older save is allowed; token high-water mark still rejects stale callbacks
    Loaded.SetPaused(false); CHECK(Loaded.SetAccess("a",true)); CHECK(Loaded.Reserve("a","out")>Fresh);
}
static void SourceEnvelopeAndValidation()
{
    CHECK(SourceNpcPointPermitted(SourceRole::Visitor,34,0)); CHECK(!SourceNpcPointPermitted(SourceRole::Visitor,50,0));
    CHECK(!SourceNpcPointPermitted(SourceRole::Visitor,75,0)); CHECK(SourceNpcPointPermitted(SourceRole::Visitor,76,49));
    CHECK(!SourceNpcPointPermitted(SourceRole::Visitor,76,50)); CHECK(!SourceNpcPointPermitted(SourceRole::Visitor,60,0));
    CHECK(SourceNpcPointPermitted(SourceRole::Owner,21,-28)); CHECK(!SourceNpcPointPermitted(SourceRole::Owner,20,-28));
    CHECK(SourceNpcPointPermitted(SourceRole::Levi,31.5,0)); CHECK(!SourceNpcPointPermitted(SourceRole::Levi,33.1,0));
    CHECK(SourceNpcPointPermitted(SourceRole::Kohen,0,0)); CHECK(!SourceNpcPointPermitted(SourceRole::Kohen,-48,0));
    CHECK(!SourceNpcPointPermitted(SourceRole::Kohen,0,(std::numeric_limits<double>::infinity)()));
    CHECK(!SourceNpcPointPermitted(static_cast<SourceRole>(99),0,0));
    Runtime R=World(); const std::string Before=R.Save(); auto Bad=Plans(); Bad[1].Id="a";
    CHECK(!R.Configure(Bad,Paths())); CHECK(R.Save()==Before); Bad=Plans(); Bad[0].Goals[0].Duration=0;
    CHECK(!R.Configure(Bad,Paths())); auto BadPaths=Paths(); BadPaths[1].Capacity=2;
    CHECK(!R.Configure(Plans(),BadPaths)); CHECK(R.Save()==Before);
    CHECK(!R.SetAccess("unknown",true)); CHECK(!R.SetNear("unknown",true)); CHECK(R.Reserve("unknown","out")==0);
    CHECK(R.Advance((std::numeric_limits<Seconds>::max)())); CHECK(!R.Advance(1));
}
static void RejectImpossibleElapsedWork()
{
    Runtime R=World(); const std::string Before=R.Save();
    std::string Corrupt=Before;
    const std::string Original="\"a\" \"meeting\" 0 7 0 0";
    const std::size_t At=Corrupt.find(Original); CHECK(At!=std::string::npos);
    Corrupt.replace(At,Original.size(),"\"a\" \"meeting\" 0 1 0 0");
    CHECK(!R.Load(Corrupt)); CHECK(R.Save()==Before); // no six seconds of work at clock zero

    CHECK(R.SetAccess("a",true)); CHECK(R.Advance(4));
    const std::string Partial=R.Save(); // one second legitimately worked after earliest=3
    Runtime Restored=World(); CHECK(Restored.Load(Partial)); CHECK(Get(Restored,"a").Remaining==6);
    Corrupt=Partial;
    const std::string OneSecond="\"a\" \"meeting\" 0 6 0 0";
    const std::size_t PartialAt=Corrupt.find(OneSecond); CHECK(PartialAt!=std::string::npos);
    Corrupt.replace(PartialAt,OneSecond.size(),"\"a\" \"meeting\" 0 5 0 0");
    const std::string BeforeReject=Restored.Save();
    CHECK(!Restored.Load(Corrupt)); CHECK(Restored.Save()==BeforeReject);
    CHECK(Restored.SetAccess("a",true)); CHECK(Restored.Advance(6));
    CHECK(Get(Restored,"a").Completions[0]==10);

    auto P=Plans(); P[0].Goals[1]={"stay","Stay at meeting","meeting","observe",3,11};
    Runtime Later; CHECK(Later.Configure(P,Paths())); CHECK(Later.SetAccess("a",true));
    CHECK(Later.Advance(10)); CHECK(Later.SetAccess("a",true)); CHECK(Later.Advance(1));
    const std::string LaterSave=Later.Save();
    Corrupt=LaterSave;
    const std::string LaterOriginal="\"a\" \"meeting\" 1 10 0 1 10";
    const std::size_t LaterAt=Corrupt.find(LaterOriginal); CHECK(LaterAt!=std::string::npos);
    Corrupt.replace(LaterAt,LaterOriginal.size(),"\"a\" \"meeting\" 1 9 0 1 10");
    CHECK(!Later.Load(Corrupt)); CHECK(Later.Save()==LaterSave); // cannot spend time before preceding completion
    CHECK(Later.Load(LaterSave)); CHECK(Later.SetAccess("a",true)); CHECK(Later.Advance(10));
    CHECK(Get(Later,"a").Completions[1]==21);
}
static void ChunkAndCapacity()
{
    Runtime A=World(), B=World(); CHECK(A.SetAccess("a",true)); CHECK(B.SetAccess("a",true));
    CHECK(A.Advance(14)); for(int I=0;I<14;++I) CHECK(B.Advance(1)); CHECK(A.Save()==B.Save());
    std::vector<Identity> Many;
    for(int I=0;I<256;++I) Many.push_back({"resident_"+std::to_string(I),"Authored", "meeting",SourceRole::Visitor,
        {{"visit","Visit lane","lane","observe",static_cast<Seconds>(I%19),static_cast<Seconds>(7+I%23)}}});
    auto Routes=Paths(); for(Route& R:Routes) R.Capacity=3;
    Runtime Crowd; CHECK(Crowd.Configure(Many,Routes)); CHECK(Crowd.Advance(20));
    unsigned Admitted=0; for(const Identity& I:Many) { CHECK(Crowd.SetAccess(I.Id,true)); if(Crowd.Reserve(I.Id,"out")) ++Admitted; }
    CHECK(Admitted==3); CHECK(Crowd.Advance(1000)); CHECK(Crowd.Reserve("resident_255","out")==0);
    for(int I=0;I<3;++I) { const std::string Id="resident_"+std::to_string(I); CHECK(Crowd.AcknowledgeStopped(Id,Crowd.Find(Id)->Token)); }
    CHECK(Crowd.Reserve("resident_255","out")!=0);
    Runtime Copy; CHECK(Copy.Configure(Many,Routes)); CHECK(Copy.Load(Crowd.Save())); CHECK(Copy.Residents().size()==256);
    auto Opposite=Plans(); Opposite[0].Goals={{"go","Go","lane","observe",0,1}};
    Opposite[1].Start="lane"; Opposite[1].Goals={{"return","Return","meeting","observe",0,1}};
    Runtime Door; CHECK(Door.Configure(Opposite,Paths())); CHECK(Door.SetAccess("a",true)); CHECK(Door.SetAccess("b",true));
    const Seconds Out=Door.Reserve("a","out"); CHECK(Out!=0); CHECK(Door.Reserve("b","back")==0);
    CHECK(Door.Arrive("a",Out,"lane")); CHECK(Door.Reserve("b","back")!=0);
}
int main(int Argc, char** Argv)
{
    CHECK(Argc==2); SchedulePauseAndVariation(); ReservationsAndCallbacks(); TimeoutAndRevocation();
    Persistence(Argv[1]); SourceEnvelopeAndValidation(); RejectImpossibleElapsedWork(); ChunkAndCapacity();
    std::cout << "PASS " << Checks << " checks: schedules, variation, pause, routes, access, memory, disk roundtrip, corruption, capacity\n";
}
