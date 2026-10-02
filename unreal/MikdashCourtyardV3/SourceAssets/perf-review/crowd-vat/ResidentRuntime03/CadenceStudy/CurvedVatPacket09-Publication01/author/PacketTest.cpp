#include "CurvePacket.h"
#include "float_compat.h"
#include "CurvePacket.ush"
#include "frozen/CrowdGroupMath.h"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <cstring>
using namespace CurvedVat09;
int main(){int checks=0,fail=0;auto C=[&](bool x,const char* s){++checks;if(!x){++fail;std::cerr<<s<<'\n';}};
 Record R;R.Active=true;R.Origin={320,0,.5};R.U={1,0,0};R.V={0,1,0};R.Radius=60;R.Lead=20;R.Arc=60*3.14159265358979323846f/2;R.Length=126;R.Start=600;R.Duration=1.4f;R.Yaw=0;R.Sign=1;R.PhaseStart=.17f;R.CyclesPerCm=1/119.95f;
 R.Tail=true;R.TailTo={400,134.75f,.5};R.TailDuration=.7f;
 C(!ShaderDrained(R,std::nextafter(ConservativeEnd(R),-INFINITY))&&ShaderDrained(R,ConservativeEnd(R)),"float completion uses outward end including successor");
 Legacy L{};for(int i=0;i<30;++i)L[i]=float(i)/31;L[25]=601.2f;
 Packet P{};C(Pack(L,R,R,{350,20,.5},35,P),"pack77 valid bounded curve");C(std::memcmp(P.data(),L.data(),sizeof(L))==0,"30 prefix bits unchanged");
 Record Decoded;C(TryUnpack(P,Current,{350,20,.5},35,Decoded),"typed decoder accepts matching layout and finite packet");auto Wrong=P;Wrong[30]=30;C(!TryUnpack(Wrong,Current,{350,20,.5},35,Decoded),"typed decoder rejects old or unknown layout version");Wrong=P;Wrong[31]=3;C(!TryUnpack(Wrong,Current,{350,20,.5},35,Decoded),"typed decoder rejects unknown motion mode");
 const auto Round=Load(P,Current,{350,20,.5},35);C(Round.Origin.X==R.Origin.X&&Round.Yaw==R.Yaw&&Round.Tail&&Round.CyclesPerCm==R.CyclesPerCm,"pack/unpack world-frame record");
 auto Bad=R;Bad.Radius=1;Packet Before=P;C(!Pack(L,Bad,R,{},0,P)&&P==Before,"invalid radius fails without packet mutation");
 Bad=R;Bad.TailTo={700,900,.5};C(!Pack(L,Bad,R,{},0,P),"illegal tail direction/speed rejected");Bad=R;Bad.Start=5000;C(!Pack(L,Bad,R,{},0,P),"time domain requires explicit epoch reset");
 Bad=R;Bad.Origin.X=100000;C(!Pack(L,Bad,R,{},0,P),"bounded local world mapping refuses out-of-domain root");
 struct Work {int Queries=0;bool Query(){if(Queries>=512)return false;++Queries;return true;}} W;
 struct Mock {bool Clear=false,Atomic=false;int Queries=0,Reservations=0;bool RevalidateFloatPacket(const Publication&,const Admission&,Work& W){++Queries;return W.Query()&&Clear;}bool ReserveAndEnqueueAtomically(const Publication&,const Admission&){if(!Atomic)return false;++Reservations;return true;}} M;
 Admission A;Publication S;C(!Publish(A,L,R,R,{},0,1,S,M,W)&&M.Queries==0,"absent real world fence refuses before publication");
 A.WorldFence=A.CompleteSupport=A.MeasuredBounds=A.MaterialLayout=A.RenderHistoryAvailable=true;
 C(!Publish(A,L,R,R,{},0,1,S,M,W)&&!S.Pending&&!M.Reservations,"fresh float geometry refusal retains state");M.Clear=true;
 C(!Publish(A,L,R,R,{},0,1,S,M,W)&&!S.Pending&&!M.Reservations,"atomic enqueue refusal retains state");M.Atomic=true;
 W.Queries=512;C(!Publish(A,L,R,R,{},0,1,S,M,W)&&!S.Pending,"exhausted shared frame work refuses packet safety validation");W.Queries=0;
 C(Publish(A,L,R,R,{},0,1,S,M,W)&&S.Pending&&M.Reservations==1,"explicit tested-port publication commits once");
 C(!Publish(A,L,R,R,{},0,1,S,M,W)&&M.Reservations==1,"pending renderer acknowledgement prevents replacement");C(!Acknowledge(S,2)&&Acknowledge(S,1),"serial-specific acknowledgement");
 History H;H.CurrentRecord=R;auto N=R;N.Origin.X+=1;H.Stage(N,1);auto N2=N;N2.Origin.X+=1;H.Stage(N2,1);C(H.PreviousRecord.Origin.X==R.Origin.X,"same-frame publication preserves first old curve");
 H.Stage(R,2);C(H.PreviousRecord.Origin.X==N2.Origin.X,"next-frame snapshot advances history");
 MikdashCrowdGroups::MotionReservation MC;MC.Curved=true;MC.CurveOrigin={320,0};MC.CurveU={1,0};MC.CurveV={0,1};MC.CurveRadius=60;MC.CurveLead=20;MC.CurveArc=60*3.14159265358979323846/2;MC.CurveLength=125.99999;MC.CurveStart=600;MC.CurveDuration=double(float(.7))*2;MC.CurveYaw=0;MC.CurveSign=1;MC.CurveOut={400,60};MC.CurveIn={340,0};MC.Start=600;MC.End=601.4;MC.To={400,71.7522};
 auto Imported=FromCommitted(MC,.5,.17f,1/119.95f,0,0,0);C(Valid(Imported),"exact07 MotionReservation adapter produces valid packet");
 auto Mesh=FromCommitted(MC,.5,.17f,1/119.95f,0,0,-90);C(Mesh.Yaw==-90&&Mesh.U.X==1,"mesh basis offset changes posed yaw, never world route direction");
 MC.Curved=false;MC.Chained=true;MC.From={400,71.75};MC.Middle={400,134.75};MC.To={400,197.75};MC.Start=601.4;MC.Split=602.1;MC.End=602.8;
 auto Line=FromCommitted(MC,.5,.25f,1/119.95f,0,0,0);C(Valid(Line)&&Line.Linear&&Line.Active&&Line.Tail,"post-curve linear successor remains encoded instead of dropping into30float layout");
 MC.Curved=true;MC.Chained=false;MC.Start=600;MC.End=601.4;MC.To={400,71.7522};
 const auto Keep=Imported;MC.Start=600.7;MC.From=MC.At(MC.Start);Imported=FromCommitted(MC,.5,.17f,1/119.95f,0,0,0);C(Imported.Start==Keep.Start&&Imported.Origin.X==Keep.Origin.X,"clip retirement cannot reset curve origin/time");
 std::ofstream Out("samples.csv");Out<<std::setprecision(9)<<"case,time,basis,scale,previous,rootx,rooty,rootz,yaw,phase,wpx,wpy,wpz,nx,ny,nz";for(int k=0;k<77;++k)Out<<",p"<<k;Out<<'\n';
 float MaxRebase=0,MaxCurve=0;
 for(int Case=0;Case<8;++Case){auto Cur=R,Old=R;Cur.Sign=Old.Sign=Case&1?-1.f:1.f;Cur.V.Y=Old.V.Y=Cur.Sign;Cur.TailTo.Y=Old.TailTo.Y=134.75f*Cur.Sign;
  if(Case>=4){Cur.Linear=true;Cur.Origin={400,71.75f,.5};Cur.U={0,1,0};Cur.V={-1,0,0};Cur.Arc=0;Cur.Lead=Cur.Length=63;Cur.Duration=.7f;Cur.Yaw=90;Cur.Sign=1;Cur.TailTo={400,197.75f,.5};Old=Cur;}
  Old.Origin.X-=10;Old.TailTo.X-=10;Old.Start-=.2f;const float Basis=Case<2?35.f:-55.f,Scale=Case&2?1.08f:.92f;Vec Root{350,20,.5};C(Pack(L,Cur,Old,Root,Basis,P),"pack sampled case");
  const float Times[]={599.99994f,600,600.000061f,600+20/90.f,600+(20+Cur.Arc)/90.f,601.19995f,601.2f,601.20007f,601.4f,601.4001f,602.1f,602.1001f,603};
  for(float Time:Times)for(int Prev=0;Prev<2;++Prev){const int B=Prev&&Time<L[25]?54:31;auto E=CurveEvaluate(P.data(),B,Time);const float3 Rest{20,7,170},Delta{4+std::sin(Time),2,3},Normal=normalize({.3f,.4f,.866f});auto V=CurveEvaluatePose(P.data(),Time,Prev!=0,Rest,Delta,Normal,Basis,Scale);
   C(std::isfinite(E.RootOffset.x)&&std::isfinite(V.Wpo.x),"float shader equivalent finite at boundaries");
   const auto& Ref=B==31?Cur:Old;const double D=std::clamp((double(Time)-Ref.Start)/Ref.Duration,0.,1.)*Ref.Length;const double Arc=std::clamp(D-Ref.Lead,0.,double(Ref.Arc)),T=Arc/Ref.Radius;
   const double Along=std::min(D,double(Ref.Lead))+Ref.Radius*std::sin(T),Across=Ref.Radius*(1-std::cos(T))+std::max(D-Ref.Lead-Ref.Arc,0.);const double X=Ref.Origin.X+Ref.U.X*Along+Ref.V.X*Across,Y=Ref.Origin.Y+Ref.U.Y*Along+Ref.V.Y*Across;
   const double Alpha=std::clamp((double(Time)-Ref.Start-Ref.Duration)/Ref.TailDuration,0.,1.);const double EX=X+(Ref.TailTo.X-X)*Alpha,EY=Y+(Ref.TailTo.Y-Y)*Alpha;
   const float Error=float(std::hypot(E.RootOffset.x+Root.X-EX,E.RootOffset.y+Root.Y-EY));MaxCurve=std::max(MaxCurve,Error);C(Error<.002f,"bounded test-domain float position versus double analytical path");
   Packet Q;Vec Root2{360,-10,.5};const float Basis2=Basis+90;C(Pack(L,Cur,Old,Root2,Basis2,Q),"rebase packet");auto Z=CurveEvaluatePose(Q.data(),Time,Prev!=0,Rest,Delta,Normal,Basis2,Scale);
   auto W=V.Wpo+CurveRotate(Rest,Basis)*Scale+float3(Root.X,Root.Y,Root.Z);auto W2=Z.Wpo+CurveRotate(Rest,Basis2)*Scale+float3(Root2.X,Root2.Y,Root2.Z);
   const float Diff=length(W-W2);MaxRebase=std::max(MaxRebase,Diff);C(Diff<.002f,"current/previous posed world coherent after HISM root+basis rebase");C(length(V.Normal-Z.Normal)<.0001f,"normal rebase coherent");
   Out<<Case<<','<<Time<<','<<Basis<<','<<Scale<<','<<Prev<<','<<E.RootOffset.x<<','<<E.RootOffset.y<<','<<E.RootOffset.z<<','<<E.Yaw<<','<<E.Phase<<','<<V.Wpo.x<<','<<V.Wpo.y<<','<<V.Wpo.z<<','<<V.Normal.x<<','<<V.Normal.y<<','<<V.Normal.z;for(float F:P)Out<<','<<F;Out<<'\n';
  }
 }
 // Missing/bad version never enables curve evaluation on old30 assets.
 C(CurveEnabled(P.data(),31)==1,"v9001 activates supported record");auto Untagged=P;Untagged[30]=0;C(CurveEnabled(Untagged.data(),31)==0,"missing layout tag disables curved shader path");
 std::cout<<"checks="<<checks<<" failures="<<fail<<" maxFloatPositionError="<<MaxCurve<<" maxRebaseError="<<MaxRebase<<'\n';return fail?1:0;
}
