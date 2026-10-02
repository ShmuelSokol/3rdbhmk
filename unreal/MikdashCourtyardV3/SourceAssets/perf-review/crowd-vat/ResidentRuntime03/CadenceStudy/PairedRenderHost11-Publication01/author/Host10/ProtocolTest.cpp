#include "Source/PairedRenderHost/Public/PairProtocol.h"
#include <iostream>
#include <limits>
#include <cstdlib>
using namespace Paired10;
int N=0;void Check(bool B){++N;if(!B){std::cerr<<"failed "<<N<<"\n";std::exit(1);}}
int main(){
 for(uint64_t G:{uint64_t(1),uint64_t(65536),uint64_t(1)<<48,~uint64_t(0)})for(uint64_t S:{uint64_t(1),uint64_t(65535),uint64_t(1)<<40,~uint64_t(0)}){
  Wire W{};Token(W,77,S);Token(W,81,G);Check(HasToken(W,77,S));Check(HasToken(W,81,G));
  Protocol P(G);Check(!P.Begin(S,false));Check(P.State==Phase::Idle);Check(P.Begin(S,true));Check(!P.Begin(S+1,true));Check(!P.Observe(G,S,true));
  P.Finish(true);Check(!P.Observe(G^1,S,true));Check(!P.Observe(G,S^1,true));Check(P.State==Phase::Pending);Check(!P.Consume(G,S));
  Check(P.Observe(G,S,true));Check(!P.Consume(G^1,S));Check(P.Consume(G,S));Check(!P.Consume(G,S));Check(!P.Begin(S,true));
  for(int Lane=0;Lane<TransportFloats;++Lane){Wire Bad=W;Bad[Lane]+=1;Check(!ExactWire(Bad,W));}
  Wire Bad=W;Bad[0]=std::numeric_limits<float>::quiet_NaN();Check(!ExactWire(Bad,W));Check(ExactWire(W,W));
 }
 for(int Failure=0;Failure<4;++Failure){Protocol P(7);Check(P.Begin(9,true));if(Failure==0)P.Finish(false);else{P.Finish(true);if(Failure==1)Check(!P.Observe(7,9,false));else{if(Failure==3)Check(P.Observe(7,9,true));P.Quarantine();}}Check(P.Closed);Check(!P.Consume(7,9));Check(!P.Begin(10,true));Check(!P.Observe(7,9,true));}
 // Destroy/recreate lateACK cannot acknowledge new generation, even reused serial.
 Protocol Old(10),New(11);Check(Old.Begin(1,true));Old.Finish(true);Old.Quarantine();Check(New.Begin(1,true));New.Finish(true);Check(!New.Observe(10,1,true));Check(New.Observe(11,1,true));
 std::cout<<N<<" protocol checks, 0 failures; no UE/render execution\n";
}
