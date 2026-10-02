// Actual production pure header; no UE stand-ins. Staged only, not executed here.
#include "../P/Source/Receiver04Compile/Private/runtime_adoption01/AdoptionState.h"
#include <limits>
#include <cstdio>
using MikdashOnline::Adoption01::AdoptionState;
int main(){
    int checks=0,failures=0;
    auto Check=[&](bool B){++checks;if(!B)++failures;};
    {AdoptionState S;Check(S.Begin(100,110,120));Check(S.Check(101));Check(S.Commit(102));Check(S.Get()==AdoptionState::Phase::Stopped);Check(!S.Begin(103,111,120));}
    {AdoptionState S;Check(!S.Begin(110,110,120));Check(S.Get()==AdoptionState::Phase::Closed);}
    {AdoptionState S;Check(S.Begin(100,110,120));Check(!S.Commit(110));Check(S.Get()==AdoptionState::Phase::Closed);}
    {AdoptionState S;Check(S.Begin(100,110,120));S.Abort();Check(!S.Commit(101));Check(!S.Check(101));Check(!S.Begin(101,111,120));}
    {AdoptionState S;Check(S.Begin(100,110,120));Check(!S.Check(99));Check(!S.Commit(101));}
    {AdoptionState S;Check(!S.Begin(100,121,120));Check(!S.Check(101));}
    {AdoptionState S;Check(!S.Begin(std::numeric_limits<double>::quiet_NaN(),110,120));}
    {AdoptionState S;Check(!S.Begin(100,std::numeric_limits<double>::infinity(),120));}
    {AdoptionState S;Check(!S.Begin(0,86401,86402));}
    {AdoptionState S;Check(S.Begin(100,110,120));Check(S.Commit(101));Check(!S.Check(110));Check(!S.Commit(109));}
    std::printf("adoption_state cases=10 checks=%d failures=%d\n",checks,failures);
    return failures?1:0;
}
