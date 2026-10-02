#include "Source/PairedRenderHost/Public/PairProtocol.h"
#include <iostream>
#include <limits>
#include <cstdlib>
#include <memory>
#include <vector>
#include <algorithm>
using namespace Paired10;
int N=0;void Check(bool B){++N;if(!B){std::cerr<<"failed "<<N<<"\n";std::exit(1);}}

// Engine-free event harness: same MayRenew rule used by the component, with
// retained shared ownership. Exercises engine's destroy/create without register.
struct Life {
 struct Session {Protocol P;size_t Journal=0;std::shared_ptr<int> Reservation;Session(uint64_t G):P(G){}};
 uint64_t Next=1;std::shared_ptr<Session> Current;std::vector<std::shared_ptr<Session>> Retired;
 bool Create(){if(Current){if(!Current->P.Closed)return true;if(!MayRenew(Current->P,Current->Journal))return false;Retired.push_back(Current);}Current=std::make_shared<Session>(Next++);return true;}
 void Destroy(){Current->P.Quarantine();}
};
struct Basis {
 float M[3][3]{};int Repairs=0;
 // Independent numerical witness using textbook modified Gram-Schmidt.
 // No UE source compiled/copied. The production template calls actual UE method.
 void Orthogonalize(){++Repairs;for(int Target=1;Target<3;++Target)for(int Axis=0;Axis<Target;++Axis){
  float Projection=0,Length=0;for(int J=0;J<3;++J){Projection+=M[Target][J]*M[Axis][J];Length+=M[Axis][J]*M[Axis][J];}
  float Ratio=Projection/Length;for(int J=0;J<3;++J)M[Target][J]-=Ratio*M[Axis][J];
 }}
};
Basis RotatedPrevious(){
 // Fixed general3D rotation from normalized non-axis-aligned quaternion.
 const double Raw[4]={.17,.31,.43,.79};double Norm=0;for(double X:Raw)Norm+=X*X;Norm=std::sqrt(Norm);
 const double X=Raw[0]/Norm,Y=Raw[1]/Norm,Z=Raw[2]/Norm,W=Raw[3]/Norm;
 Basis B;double R[3][3]={{1-2*(Y*Y+Z*Z),2*(X*Y-Z*W),2*(X*Z+Y*W)},
 {2*(X*Y+Z*W),1-2*(X*X+Z*Z),2*(Y*Z-X*W)},
 {2*(X*Z-Y*W),2*(Y*Z+X*W),1-2*(X*X+Y*Y)}};
 for(int I=0;I<3;++I)for(int J=0;J<3;++J)B.M[I][J]=float(R[I][J]);return B;
}
void Regression(){
 std::atomic<uint64_t> Counter{~uint64_t(0)-1};
 Check(AllocateGeneration(Counter)==~uint64_t(0)-1);Check(AllocateGeneration(Counter)==~uint64_t(0));
 Check(AllocateGeneration(Counter)==0);Check(AllocateGeneration(Counter)==0);Check(Counter.load()==0);
 Life L;Check(L.Create());auto Initial=L.Current;Check(Initial->P.Generation==1);
 // Initial PSO pending: no proxy/publication, destroy/create WITHOUT OnRegister.
 L.Destroy();Check(L.Create());Check(L.Current->P.Generation==2);Check(L.Retired[0]==Initial);Check(Initial->P.Closed);
 auto Ready=L.Current;L.Destroy();Check(L.Create());Check(L.Current->P.Generation==3);Check(Ready->P.Closed); // empty live-proxy recreation
 Check(L.Current->P.Begin(1,true));L.Current->P.Finish(true);
 Check(!L.Current->P.Observe(Initial->P.Generation,1,true));Initial->P.Quarantine();Check(!L.Current->P.Closed);
 // Writing/pending/observed/consumed cases all own historical obligations.
 for(int Stage=0;Stage<4;++Stage){
  Life A;Check(A.Create());Check(A.Current->P.Begin(1,true));A.Current->Journal=1;A.Current->Reservation=std::make_shared<int>(42);
  std::weak_ptr<int> Held=A.Current->Reservation;auto Old=A.Current;
  if(Stage>=1)A.Current->P.Finish(true);if(Stage>=2)Check(A.Current->P.Observe(1,1,true));if(Stage>=3)Check(A.Current->P.Consume(1,1));
  A.Destroy();Check(!A.Create());Check(A.Current==Old);Check(!Held.expired());Check(A.Current->Journal==1);Check(!A.Current->P.Observe(1,1,true));Check(!A.Current->P.Consume(1,1));
 }
 Protocol NoJournalButAdmitted(8);Check(NoJournalButAdmitted.Begin(1,true));NoJournalButAdmitted.Quarantine();Check(!MayRenew(NoJournalButAdmitted,0));
 Protocol UnexpectedJournal(9);UnexpectedJournal.Quarantine();Check(!MayRenew(UnexpectedJournal,1));Check(MayRenew(UnexpectedJournal,0));
 Basis Input=RotatedPrevious();Basis Wrong=Input;Wrong.Orthogonalize();float Diff=0;
 for(int I=0;I<3;++I)for(int J=0;J<3;++J)Diff=std::max(Diff,std::abs(Input.M[I][J]-Wrong.M[I][J]));
 Check(Diff>0); // Old Host10 would reject the exact unchanged engine buffer.
 for(bool PrimitiveNonUniform:{false,true}){
  Basis Expected=Input;if(PrimitiveNonUniform)Expected.Orthogonalize();
  Basis Actual=FinishExpectedTransform(Input,PrimitiveNonUniform);
  Check(Actual.Repairs==(PrimitiveNonUniform?1:0));
  for(int I=0;I<3;++I)for(int J=0;J<3;++J)Check(Actual.M[I][J]==Expected.M[I][J]);
 }
 std::cout<<"general-rotation false-repair max difference "<<Diff<<"; identity branch exact, no epsilon\n";
}
int main(){
 Regression();
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
