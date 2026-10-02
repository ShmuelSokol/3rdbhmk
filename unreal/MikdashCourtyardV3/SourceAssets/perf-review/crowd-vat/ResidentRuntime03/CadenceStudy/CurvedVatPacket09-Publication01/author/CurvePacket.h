#pragma once
#include <array>
#include <cmath>
#include <algorithm>
#include <cstdint>
namespace CurvedVat09 {
constexpr int Floats=77,Version=9001,Current=31,Previous=54,RecordFloats=23;
struct Vec {float X=0,Y=0,Z=0;};
struct Record {
 bool Active=false,Tail=false,Linear=false;Vec Origin{},U{1,0,0},V{0,1,0},TailTo{};
 float Radius=60,Lead=0,Arc=0,Length=0,Start=0,Duration=1,Yaw=0,Sign=1,TailDuration=1,PhaseStart=0,CyclesPerCm=0;
};
using Packet=std::array<float,Floats>;using Legacy=std::array<float,30>;
inline bool Finite(Vec V){return std::isfinite(V.X)&&std::isfinite(V.Y)&&std::isfinite(V.Z);}
inline bool Valid(const Record& R){
 if(!R.Active)return true;
 if(!Finite(R.Origin)||!Finite(R.U)||!Finite(R.V)||!Finite(R.TailTo))return false;
 if(std::abs(R.Origin.X)>8192||std::abs(R.Origin.Y)>8192||std::abs(R.TailTo.X)>8192||std::abs(R.TailTo.Y)>8192)return false;
 if(R.Tail){const float T=R.Arc/R.Radius;const float X=R.Origin.X+R.U.X*(R.Lead+R.Radius*std::sin(T))+R.V.X*(R.Radius*(1-std::cos(T))+R.Length-R.Lead-R.Arc);const float Y=R.Origin.Y+R.U.Y*(R.Lead+R.Radius*std::sin(T))+R.V.Y*(R.Radius*(1-std::cos(T))+R.Length-R.Lead-R.Arc);const float DX=R.TailTo.X-X,DY=R.TailTo.Y-Y; if(std::abs(DX*(R.Linear?R.U.Y:R.V.Y)-DY*(R.Linear?R.U.X:R.V.X))>.001f||DX*(R.Linear?R.U.X:R.V.X)+DY*(R.Linear?R.U.Y:R.V.Y)<0||std::hypot(DX,DY)>90*R.TailDuration)return false;}
 const float S[]={R.Radius,R.Lead,R.Arc,R.Length,R.Start,R.Duration,R.Yaw,R.Sign,R.TailDuration,R.PhaseStart,R.CyclesPerCm};for(float F:S)if(!std::isfinite(F))return false;
 return R.Radius>=60&&R.Radius<=100&&R.Lead>=0&&((R.Linear&&R.Arc==0&&R.Lead==R.Length)||(!R.Linear&&R.Arc>0&&R.Arc<=R.Radius*1.570797f))&&R.Length>=R.Lead+R.Arc&&R.Length<=198&&R.Duration>0&&R.Duration<=4&&R.Start>=0&&R.Start<=4096
  &&R.Length/R.Duration<=90&&R.Length/R.Duration/R.Radius*57.29577951308232f<=90
  &&std::abs(R.U.X*R.U.X+R.U.Y*R.U.Y-1)<1e-6f&&std::abs(R.V.X*R.V.X+R.V.Y*R.V.Y-1)<1e-6f&&std::abs(R.U.X*R.V.X+R.U.Y*R.V.Y)<1e-6f
  &&R.U.Z==0&&R.V.Z==0&&std::abs(R.Sign)==1&&std::abs(R.U.X*R.V.Y-R.U.Y*R.V.X-R.Sign)<1e-6f
  &&(!R.Tail||(R.TailDuration>0&&R.TailDuration<=2&&R.TailTo.Z==R.Origin.Z))&&R.CyclesPerCm>0&&R.PhaseStart>=0&&R.PhaseStart<1;
}
inline void Store(Packet& P,int B,const Record& R,Vec BasisRoot,float BasisYaw){
 P[B]=R.Active?(R.Linear?2.f:1.f):0.f;if(!R.Active)return;
 const float F[]={R.Origin.X-BasisRoot.X,R.Origin.Y-BasisRoot.Y,R.Origin.Z-BasisRoot.Z,R.U.X,R.U.Y,R.V.X,R.V.Y,R.Radius,R.Lead,R.Arc,R.Length,R.Start,R.Duration,R.Yaw-BasisYaw,R.Sign,R.Tail?1.f:0.f,R.TailTo.X-BasisRoot.X,R.TailTo.Y-BasisRoot.Y,R.TailTo.Z-BasisRoot.Z,R.TailDuration,R.PhaseStart,R.CyclesPerCm};
 std::copy(F,F+22,P.begin()+B+1);
}
inline Record Load(const Packet& P,int B,Vec BasisRoot,float BasisYaw){
 Record R;if(P[30]!=Version||(B!=Current&&B!=Previous))return R;R.Active=P[B]==1||P[B]==2;R.Linear=P[B]==2;if(!R.Active)return R;
 R.Origin={P[B+1]+BasisRoot.X,P[B+2]+BasisRoot.Y,P[B+3]+BasisRoot.Z};R.U={P[B+4],P[B+5],0};R.V={P[B+6],P[B+7],0};
 R.Radius=P[B+8];R.Lead=P[B+9];R.Arc=P[B+10];R.Length=P[B+11];R.Start=P[B+12];R.Duration=P[B+13];R.Yaw=P[B+14]+BasisYaw;R.Sign=P[B+15];R.Tail=P[B+16]==1;
 R.TailTo={P[B+17]+BasisRoot.X,P[B+18]+BasisRoot.Y,P[B+19]+BasisRoot.Z};R.TailDuration=P[B+20];R.PhaseStart=P[B+21];R.CyclesPerCm=P[B+22];return R;
}
inline bool TryUnpack(const Packet& P,int B,Vec Root,float Yaw,Record& Out){
 if(P[30]!=Version||(B!=Current&&B!=Previous)||!Finite(Root)||!std::isfinite(Yaw))return false;
 for(float F:P)if(!std::isfinite(F))return false;
 if((P[B]!=0&&P[B]!=1&&P[B]!=2)||(P[B+16]!=0&&P[B+16]!=1))return false;
 const Record R=Load(P,B,Root,Yaw);if(!Valid(R))return false;Out=R;return true;
}
inline bool Pack(const Legacy& L,const Record& C,const Record& Old,Vec Root,float Yaw,Packet& Out){
 if(!Valid(C)||!Valid(Old)||!Finite(Root)||!std::isfinite(Yaw))return false;
 for(float F:L)if(!std::isfinite(F))return false;
 Packet P{};std::copy(L.begin(),L.end(),P.begin());P[30]=float(Version);Store(P,Current,C,Root,Yaw);Store(P,Previous,Old,Root,Yaw);
 for(float F:P)if(!std::isfinite(F))return false;
 for(int B:{Current,Previous})if(P[B])for(int K:{1,2,3,17,18,19})if(std::abs(P[B+K])>8192)return false;
 Out=P;return true;
}
// Exact shared07/08 MotionReservation adapter: absolute curve origin survives
// clip-window retirement. Caller owns VAT phase at record start (curve original start or linear prefix start) snapshot, not derived from yaw.
template<class Motion> Record FromCommitted(const Motion& M,float RootZ,float PhaseAtCurveStart,float CyclesPerCm,double FrameX,double FrameY,float MeshYawOffsetDegrees){
 Record R;R.Active=M.Curved||M.Chained;if(!R.Active)return R;
 if(!M.Curved){
  R.Linear=true;R.Origin={float(M.From.X-FrameX),float(M.From.Y-FrameY),RootZ};
  const double DX=M.Middle.X-M.From.X,DY=M.Middle.Y-M.From.Y,L=std::hypot(DX,DY);
  if(!(L>0)){R.Radius=0;return R;}R.U={float(DX/L),float(DY/L),0};R.V={-R.U.Y,R.U.X,0};
  R.Lead=R.Length=float(L);R.Arc=0;R.Start=float(M.Start);R.Duration=float(M.Split-M.Start);R.Yaw=float(std::atan2(DY,DX)*57.29577951308232)+MeshYawOffsetDegrees;
  R.Tail=true;R.TailTo={float(M.To.X-FrameX),float(M.To.Y-FrameY),RootZ};R.TailDuration=float(M.End-M.Split);R.PhaseStart=PhaseAtCurveStart;R.CyclesPerCm=CyclesPerCm;return R;
 }
 R.Origin={float(M.CurveOrigin.X-FrameX),float(M.CurveOrigin.Y-FrameY),RootZ};R.U={float(M.CurveU.X),float(M.CurveU.Y),0};R.V={float(M.CurveV.X),float(M.CurveV.Y),0};
 R.Radius=float(M.CurveRadius);R.Lead=float(M.CurveLead);R.Arc=float(M.CurveArc);R.Length=float(M.CurveLength);R.Start=float(M.CurveStart);R.Duration=float(M.CurveDuration);R.Yaw=float(M.CurveYaw)+MeshYawOffsetDegrees;R.Sign=float(M.CurveSign);
 R.Tail=M.Chained;R.TailTo={float(M.To.X-FrameX),float(M.To.Y-FrameY),RootZ};R.TailDuration=R.Tail?float(M.End-M.Split):1;R.PhaseStart=PhaseAtCurveStart;R.CyclesPerCm=CyclesPerCm;return R;
}
// Preserve the PRE-first-update record for every publication in a frame.
struct History {
 Record CurrentRecord{},PreviousRecord{};uint64_t Frame=0;bool Initialized=false;
 void Stage(const Record& Next,uint64_t NewFrame){if(!Initialized||NewFrame!=Frame){PreviousRecord=CurrentRecord;Frame=NewFrame;Initialized=true;}CurrentRecord=Next;}
};
// Reservation retirement must use stored FLOAT start/durations, rounded outward,
// not only the original double controller end. Render ACK is an independent gate.
inline float ConservativeEnd(const Record& R){
 const double Exact=double(R.Start)+double(R.Duration)+(R.Tail?double(R.TailDuration):0.);
 float End=float(Exact);if(double(End)<Exact)End=std::nextafter(End,INFINITY);return std::nextafter(End,INFINITY);
}
inline bool ShaderDrained(const Record& R,float Now){return !R.Active||Now>=ConservativeEnd(R);}
struct Admission {
 bool WorldFence=false,CompleteSupport=false,MeasuredBounds=false,MaterialLayout=false,RenderHistoryAvailable=false;
 uint64_t RouteEpoch=0,WorldEpoch=0; // no default true physical permission
};
struct Publication {Packet Data{};Vec BasisRoot{};float BasisYaw=0,Scale=1;uint64_t Serial=0;bool Pending=false;};
// Port must freshly validate the FLOAT packet's swept corridor/support/peers,
// then atomically reserve+enqueue immutable data AND its HISM basis. If either
// fails it must leave index and publication unchanged. Mere CanReserve is not ACK.
template<class Port,class Work> bool Publish(const Admission& A,const Legacy& L,const Record& C,const Record& Old,Vec Root,float Yaw,float Scale,Publication& State,Port& P,Work& SharedFrameWork){
 if(SharedFrameWork.Queries>=512||!A.WorldFence||!A.CompleteSupport||!A.MeasuredBounds||!A.MaterialLayout||!A.RenderHistoryAvailable||State.Pending||(State.Serial>0&&Scale!=State.Scale)||!std::isfinite(Scale)||Scale<=0)return false;
 Publication Next;Next.BasisRoot=Root;Next.BasisYaw=Yaw;Next.Scale=Scale;Next.Serial=State.Serial+1;Next.Pending=true;
 if(!Pack(L,C,Old,Root,Yaw,Next.Data)||!P.RevalidateFloatPacket(Next,A,SharedFrameWork)||SharedFrameWork.Queries>512)return false;
 if(!P.ReserveAndEnqueueAtomically(Next,A))return false;State=Next;return true;
}
inline bool Acknowledge(Publication& P,uint64_t Serial){if(!P.Pending||P.Serial!=Serial)return false;P.Pending=false;return true;}
}
