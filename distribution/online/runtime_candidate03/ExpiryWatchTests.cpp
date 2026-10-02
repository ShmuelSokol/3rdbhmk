#include "ExpiryWatch.h"
#include <iostream>
#include <limits>
#include <stdexcept>
using MikdashOnline::RuntimeCandidate03::ExpiryWatch;
static int Cases=0,Checks=0;
static void Check(bool V) { ++Checks; if(!V) throw std::runtime_error("expiry assertion"); }
template<class F> void Case(F Run) { Run(); ++Cases; }
int main() { try {
    Case([] { ExpiryWatch W; Check(W.Begin(100,101,102)); Check(W.CompleteFrame(100.5)); Check(!W.CompleteFrame(101)); });
    Case([] { ExpiryWatch W; Check(W.Begin(100,110,110)); Check(!W.CompleteFrame(100.500001)); Check(!W.Observe(100.1)); });
    Case([] { ExpiryWatch W; Check(W.Begin(100,110,110)); Check(W.Observe(100.4)); Check(!W.Observe(100.3)); });
    Case([] { ExpiryWatch W; Check(W.Begin(100,110,110)); Check(W.Observe(100.25)); Check(W.Observe(100.5)); Check(!W.Observe(100.6)); });
    Case([] { ExpiryWatch W; Check(W.Begin(100,110,110)); for(int I=1;I<=20;++I) Check(W.CompleteFrame(100+I*0.25)); Check(W.Observe(105)); });
    Case([] { ExpiryWatch W; Check(!W.Begin(100,100,110)); Check(!W.Begin(100,101,110)); });
    Case([] { ExpiryWatch W; Check(!W.Begin(100,112,110)); Check(!W.Observe(100)); });
    Case([] { ExpiryWatch W; Check(W.Begin(100,86500,86500)); ExpiryWatch X; Check(!X.Begin(100,86500.01,86501)); });
    Case([] { ExpiryWatch W; Check(W.Begin(100,110,110)); W.Revoke(); W.Revoke(); Check(!W.Observe(100)); Check(!W.CompleteFrame(100)); });
    Case([] { ExpiryWatch W; Check(W.Begin(100,110,110)); Check(!W.Begin(100,120,120)); Check(!W.Observe(100)); });
    Case([] { for(double Bad : {std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),-1.0,1e300}) { ExpiryWatch W; Check(!W.Begin(Bad,110,110)); ExpiryWatch X; Check(X.Begin(100,110,110)); Check(!X.Observe(Bad)); } });
    Case([] { ExpiryWatch W; Check(W.Begin(100,100.4,110)); Check(W.Observe(100.3)); Check(!W.CompleteFrame(100.4)); Check(!W.Observe(100.3)); });
    Case([] { ExpiryWatch W; W.Revoke(); Check(!W.Begin(100,110,110)); Check(!W.Observe(100)); });
    std::cout<<Cases<<" cases "<<Checks<<" checks passed\n"; return 0;
} catch(...) { std::cerr<<"expiry tests failed\n"; return 1; } }
