// STAGED ONLY under this request's no-native constraint. Real project state and
// real frozen mailbox; no fake UE types. Compile with /I../snapshots/project/Public.
#include "../ResidentTalkAction.h"
#include "../snapshots/native/receiver04/SemanticMailbox.h"
#include <iostream>
#include <stdexcept>
using namespace MikdashDialog;
using namespace MikdashOnline;
using namespace MikdashOnline::Receiver04;
static int Cases=0,Checks=0;
void Check(bool V){++Checks;if(!V)throw std::runtime_error("interaction check");}
template<class F>void Case(F Run){Run();++Cases;}
void InRange(Conversation& C){C.Observe({100,1,true});}
int main(){try{
    Case([]{Conversation C;InRange(C);int After=0;auto R=PressTalkGuarded(C,3,[]{return true;},[&]{++After;return true;});Check(R==TalkOutcome::Applied);Check(C.IsTalking()&&C.LineIndex()==0&&After==1);});
    Case([]{Conversation C;InRange(C);Check(PressTalkGuarded(C,0,[]{return true;},[]{return true;})==TalkOutcome::NoOp);Check(!C.IsTalking());});
    Case([]{Conversation C;Check(PressTalkGuarded(C,2,[]{return true;},[]{return true;})==TalkOutcome::NoOp);Check(!C.IsTalking());});
    Case([]{Conversation C;InRange(C);int After=0;Check(PressTalkGuarded(C,2,[]{return false;},[&]{++After;return true;})==TalkOutcome::Rejected);Check(!C.IsTalking()&&After==0);});
    Case([]{Conversation C;InRange(C);C.PressTalk(1);Check(PressTalkGuarded(C,1,[]{return true;},[]{return true;})==TalkOutcome::Applied);Check(C.LineIndex()==0&&C.AdvanceCount()==1);});
    Case([]{Conversation C;InRange(C);C.PressTalk(2);C.PressTalk(2);Check(PressTalkGuarded(C,2,[]{return true;},[]{return true;})==TalkOutcome::Applied);Check(C.LineIndex()==0&&C.AdvanceCount()==2);});
    Case([]{Conversation C;InRange(C);Check(PressTalkGuarded(C,2,[]{return true;},[]{return false;})==TalkOutcome::Unknown);Check(C.IsTalking());});
    Case([]{double T=100;Context X{1,2,1};SemanticMailbox M(110,[&]{return T;});Check(M.Bind(X));Packet P;P.operation="input";P.action="interact";P.sequence=1;Check(M.Submit(P,X,T));Conversation C;InRange(C);M.PostProcessInput(X,false,[&](const std::string&,double){auto F=M.CurrentFence();T=100.5;auto R=PressTalkGuarded(C,2,[&]{return M.Revalidate(F);},[]{return true;});Check(R==TalkOutcome::Rejected);return Outcome::Rejected;});Consumption Out;Check(!C.IsTalking()&&!M.Take(Out));});
    Case([]{double T=100;Context X{1,2,1};SemanticMailbox M(110,[&]{return T;});Check(M.Bind(X));Packet P;P.operation="input";P.action="interact";P.sequence=1;Check(M.Submit(P,X,T));Conversation C;InRange(C);M.PostProcessInput(X,false,[&](const std::string&,double){auto F=M.CurrentFence();Check(PressTalkGuarded(C,2,[&]{return M.Revalidate(F);},[&]{T=100.5;return true;})==TalkOutcome::Applied);return Outcome::Applied;});Consumption Out;Check(C.IsTalking()&&!M.Take(Out));Check(!M.Submit(P,X,T));});
    Case([]{double T=100;Context X{1,2,1};SemanticMailbox M(110,[&]{return T;});Check(M.Bind(X));Packet P;P.operation="input";P.action="interact";P.sequence=1;Check(M.Submit(P,X,T));Conversation C;InRange(C);M.PostProcessInput(X,false,[&](const std::string&,double){auto F=M.CurrentFence();Check(PressTalkGuarded(C,2,[&]{T=100.2;return M.Revalidate(F);},[&]{T=100.3;return true;})==TalkOutcome::Applied);return Outcome::Applied;});Consumption Out;Check(M.Take(Out));Check(Out.authorized_at==100.2&&Out.outcome==Outcome::Applied);});
    std::cout<<Cases<<" cases "<<Checks<<" checks passed\n";return 0;
}catch(...){std::cerr<<"interaction tests failed\n";return 1;}}
