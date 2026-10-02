// STAGED, NOT EXECUTED. Tests instantiate the SAME production StoppedLease;
// fake port models callback ordering, not UE ABI/media/runtime acceptance.
#include "StoppedLease.h"
#include <memory>
#include <map>
#include <iostream>
#include <stdexcept>
using namespace MikdashOnline;
using namespace MikdashOnline::RuntimeCandidate01;
struct Video {};
struct Stream { std::string Id; std::shared_ptr<Video> V=std::make_shared<Video>(); bool Active=false,Connected=false; std::string Url="inherited"; };
struct Port {
    using Streamer=std::shared_ptr<Stream>;using Producer=std::shared_ptr<Video>;
    std::map<std::string,Streamer> Registry;
    std::function<void()> OnCreate,OnRemove,OnProducer;
    double Time=0;int Creates=0,Removes=0,Stops=0,Detaches=0;
    bool Scope=true,NoVideo=false,StickyDetach=false,Stale=false;
    double Now(){return Time;}
    bool ScopeValid(){return Scope;}bool CleanupScopeValid(){return Scope;}
    template<class T> bool Valid(const std::shared_ptr<T>& X){return bool(X);}
    std::string DefaultId(){return "default";}
    bool Registered(const std::string& I){return Stale||bool(Find(I));}
    Streamer Find(const std::string& I){auto It=Registry.find(I);return It==Registry.end()?nullptr:It->second;}
    Streamer Create(const std::string& I){++Creates;auto S=std::make_shared<Stream>();S->Id=I;if(NoVideo)S->V.reset();Registry[I]=S;if(OnCreate)OnCreate();return S;}
    std::string Id(const Streamer& S){return S->Id;}std::string Type(const Streamer&){return "DefaultRtc";}
    bool Streaming(const Streamer& S){return S->Active;}bool Connected(const Streamer& S){return S->Connected;}
    bool UrlEmpty(const Streamer& S){return S->Url.empty();}void ClearUrl(const Streamer& S){S->Url.clear();}
    Producer GetProducer(const Streamer& S){if(OnProducer)OnProducer();return S->V;}
    void SetProducer(const Streamer& S,const Producer& V){++Detaches;if(!StickyDetach)S->V=V;}
    void Stop(const Streamer& S){++Stops;S->Active=false;S->Connected=false;}
    void Remove(const Streamer& S){++Removes;if(OnRemove)OnRemove();for(auto It=Registry.begin();It!=Registry.end();){if(It->second==S)It=Registry.erase(It);else ++It;}}
};
static int Checks=0,Cases=0;
static void Check(bool B){++Checks;if(!B)throw std::runtime_error("ownership assertion failed");}
static Owner O(){return {"session","process","stream","save","settings",1000};}
template<class F>void Case(F Run){Run();++Cases;}
int main(){try{
    Case([]{Port P;auto Foreign=P.Create("stream");P.Creates=0;StoppedLease<Port>L(P);Check(!L.Prepare(O(),10));Check(L.Close());Check(P.Find("stream")==Foreign&&P.Creates==0&&P.Stops==0&&P.Removes==0);});
    Case([]{Port P;P.Stale=true;StoppedLease<Port>L(P);Check(!L.Prepare(O(),10));Check(P.Creates==0);});
    Case([]{Port P;StoppedLease<Port>L(P);auto V=O();V.stream_id="default";Check(!L.Prepare(V,10));Check(P.Creates==0);});
    Case([]{Port P;StoppedLease<Port>L(P);Check(L.Prepare(O(),10));auto S=L.BorrowStopped(O());Check(S&&S->Url.empty());Check(L.Close());Check(L.Close());Check(!S->V&&P.Removes==1&&P.Stops==0);});
    Case([]{Port P;StoppedLease<Port>L(P);Check(L.Prepare(O(),10));auto Own=L.BorrowStopped(O());auto Foreign=P.Create("stream");Check(L.Close());Check(P.Find("stream")==Foreign&&Foreign->V&&P.Stops==0&&!Own->V);});
    Case([]{Port P;StoppedLease<Port>L(P);P.OnCreate=[&]{Check(!L.Close());};Check(!L.Prepare(O(),10));Check(L.Close());Check(P.Removes==1);});
    Case([]{Port P;StoppedLease<Port>L(P);Check(L.Prepare(O(),10));P.OnRemove=[&]{Check(!L.Close());};Check(L.Close());Check(P.Removes==1);});
    Case([]{Port P;P.NoVideo=true;StoppedLease<Port>L(P);Check(!L.Prepare(O(),10));Check(L.Close());Check(P.Removes==1);});
    Case([]{Port P;StoppedLease<Port>L(P);P.OnProducer=[&]{P.Time=11;};Check(!L.Prepare(O(),10));P.OnProducer={};Check(L.Close());});
    Case([]{Port P;StoppedLease<Port>L(P);Check(L.Prepare(O(),10));auto S=L.BorrowStopped(O());S->V=std::make_shared<Video>();auto ForeignV=S->V;Check(!L.Close());Check(S->V==ForeignV&&P.Removes==0&&P.Detaches==0);});
    Case([]{Port P;StoppedLease<Port>L(P);Check(L.Prepare(O(),10));auto S=L.BorrowStopped(O());S->Active=true;Check(!L.Close());Check(!L.Close());Check(P.Stops==1&&P.Removes==0);});
    Case([]{Port P;StoppedLease<Port>L(P);Check(L.Prepare(O(),10));auto Other=O();Other.settings_slot="other";Check(!L.BorrowStopped(Other));Check(L.Matches(O()));P.Time=10;Check(!L.BorrowStopped(O()));Check(L.Close());});
    Case([]{Port P;StoppedLease<Port>L(P);Check(L.Prepare(O(),10));P.StickyDetach=true;Check(!L.Close());Check(P.Removes==0);});
    Case([]{Port P;StoppedLease<Port>L(P);auto Bad=O();Bad.stream_id=std::string(129,'a');Check(!L.Prepare(Bad,10));Check(P.Creates==0);Check(!L.Prepare(O(),90000));});
    std::cout<<Cases<<" cases "<<Checks<<" checks passed\n";return 0;
}catch(...){std::cerr<<"ownership tests failed\n";return 1;}}
