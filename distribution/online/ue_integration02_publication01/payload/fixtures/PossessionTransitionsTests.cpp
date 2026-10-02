#include "PossessionTransitions.h"
#include <cstdio>
#include <cstdlib>

using namespace MikdashOnline;
using namespace MikdashOnline::Receiver04;
using namespace MikdashOnline::Integration01;
static int Cases=0,Checks=0;
#define REQUIRE(x) do{++Checks;if(!(x))std::abort();}while(0)
struct State {
    double Now=100;
    bool Closed=false,Awaiting=false,Possessing=false,NeedsRelease=false;
    Context Native{1,2,1};uint64_t Serial=2;
    std::string Connection="synthetic-connection";
    SemanticMailbox Mailbox{110,[this](){return Now;}};
    State(){REQUIRE(Mailbox.Bind(Native));}
    PossessionState Ref(){return {Closed,Awaiting,Possessing,NeedsRelease,Native,Serial,Connection,Mailbox};}
};
int main(){
    {++Cases;State S;REQUIRE(BeginPossession(S.Ref()));REQUIRE(S.Native.pawn==0&&S.Native.generation==2);
     REQUIRE(S.Connection.empty()&&S.NeedsRelease&&S.Possessing);REQUIRE(FinishPossession(S.Ref()));
     REQUIRE(S.Native.pawn==3&&!S.Possessing&&S.NeedsRelease);}
    {++Cases;State S;REQUIRE(BeginPossession(S.Ref()));REQUIRE(FinishPossession(S.Ref()));
     REQUIRE(BeginPossession(S.Ref()));REQUIRE(FinishPossession(S.Ref()));
     REQUIRE(S.Native.pawn==4&&S.Native.generation==3);}
    {++Cases;State S;S.Awaiting=true;REQUIRE(!BeginPossession(S.Ref()));REQUIRE(S.Native.pawn==2);}
    {++Cases;State S;S.Closed=true;REQUIRE(!BeginPossession(S.Ref()));}
    {++Cases;State S;REQUIRE(BeginPossession(S.Ref()));REQUIRE(!BeginPossession(S.Ref()));}
    {++Cases;State S;REQUIRE(!FinishPossession(S.Ref()));REQUIRE(S.Serial==2);}
    {++Cases;State S;S.Native.generation=9007199254740990ULL;REQUIRE(!BeginPossession(S.Ref()));}
    {++Cases;State S;REQUIRE(BeginPossession(S.Ref()));S.Serial=9007199254740990ULL;
     REQUIRE(!FinishPossession(S.Ref()));REQUIRE(S.Native.pawn==0);}
    {++Cases;State S;Packet P;P.sequence=1;P.operation="input";P.action="look";P.x=0.1;
     REQUIRE(S.Mailbox.Submit(P,S.Native,S.Now));const auto F=S.Mailbox.CurrentFence();
     REQUIRE(BeginPossession(S.Ref()));REQUIRE(!S.Mailbox.Revalidate(F));Consumption C;
     REQUIRE(!S.Mailbox.Take(C));}
    {++Cases;State S;REQUIRE(BeginPossession(S.Ref()));S.Closed=true; // real wrapper Maintain supplies expiry
     REQUIRE(!FinishPossession(S.Ref()));REQUIRE(S.Native.pawn==0&&S.NeedsRelease);}
    std::printf("%d cases %d checks passed\n",Cases,Checks);
}
