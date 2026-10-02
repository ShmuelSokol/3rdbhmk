#include "ScheduledAngular.h"
#include <iostream>
using namespace AngularWalkingStudy;
int Checks=0,Failures=0;
void Check(bool B){++Checks;if(!B)++Failures;}
int main(){
    for(int Population:{2500,5000,10000})for(int Budget:{125,500})for(int Fps:{30,60})for(double Scale:{.92,1.08}) {
        ScheduledTurn T;SpatialIndex Index;const Vec2 Root{0,0};
        T.Core.Current.Root=Root;T.Core.Current.Envelope={50*Scale,0,190*Scale,true};
        T.Core.Current.Yaw=0;T.Core.Previous=T.Core.Current;Check(Index.Insert(1,Root));
        int Holds=0;MotionReservation M{Root,Root,0,0};
        auto Hold=[&](Vec2 P,RotatingEnvelopeStudy::Body B){
            ++Holds;Check(B.Known&&B.Radius==50*Scale);
            ScheduledTurn Estimate;Estimate.Core.Current.TurnDeltaDegrees=180;
            const double End=Estimate.End(0);
            if(!Index.Reserve(1,P,P,0,End))return false;M={P,P,0,End};return true;
        };
        Check(!T.Align(180,0,M,Hold)&&T.Held&&Holds==1);
        // Retargeting while live cannot restart/replace a segment.
        Check(!T.Align(-20,.2,M,Hold)&&Holds==1&&T.Target==180);
        const auto C=AngularControllerStudy::Channels(T.Core.Current,T.Core.Previous);
        Check(C[0]==0&&C[1]==180&&C[2]==0&&C[3]==0);
        float Data[30];for(int I=0;I<30;++I)Data[I]=float(I+.25);
        for(int I=0;I<4;++I)Data[26+I]=C[I];
        for(int I=0;I<26;++I)Check(Data[I]==float(I+.25));
        const double BeforeEnd=std::nextafter(M.End,-INFINITY);
        Check(AngularControllerStudy::Complete(T.Core.Current,BeforeEnd));
        Check(!T.CanCommit(BeforeEnd,M)&&!T.Commit(BeforeEnd,M));
        double LastYaw=0,LastTime=0;bool Committed=false;
        const int Sweeps=(Population+Budget-1)/Budget;
        for(int Frame=0;Frame<8*Fps;++Frame){
            const double Now=Frame*static_cast<double>(static_cast<float>(1.0/Fps));
            const double GameNow=static_cast<float>(Now),Yaw=T.Visible(Now);
            Check(std::abs(WrapDegrees(Yaw-LastYaw))<=90*(GameNow-LastTime)+1e-7);
            LastYaw=Yaw;LastTime=GameNow;
            Check(Length(M.At(Now)-Root)<1e-8);
            const Vec2 Posed[]={{50*Scale,0},{-50*Scale,0},{0,45*Scale},{0,-45*Scale}};
            for(Vec2 P:Posed)Check(Length(AngularControllerStudy::Rotate(P,Yaw))<=50*Scale+1e-7);
            if(!Committed){
                Check(T.Core.Current.Yaw==0);
                int PhysicalCalls=0;
                Check(!T.Core.Translation(Now,M,[&](){++PhysicalCalls;return true;},[](){return true;},[](){return true;}));
                Check(PhysicalCalls==0);
                if(Frame%Sweeps==0&&T.CanCommit(Now,M)){
                    const double PreviousTime=Now-1./Fps;
                    const auto PreviousState=T.Core.Current;
                    Check(T.Commit(Now,M));Check(Index.Relocate(1,Root,Root,Now));Committed=true;
                    const Vec2 Rest{30,20},Delta{5,3};
                    const Vec2 Expected=AngularControllerStudy::Rotate(Rest+Delta,
                        PreviousState.Yaw+AngularControllerStudy::Angle(PreviousState,PreviousTime));
                    Check(Length(AngularControllerStudy::PreviousPosedWorld(T.Core,Rest,Delta,{},PreviousTime)-Expected)<1e-7);
                    const auto Rebased=AngularControllerStudy::Channels(T.Core.Current,T.Core.Previous);
                    Check(Rebased[1]==0&&Rebased[3]==180);
                    int G=0,S=0,R=0;
                    Check(!T.Core.Translation(Now,M,[&](){++G;return true;},[&](){++S;return false;},[&](){++R;return true;}));
                    Check(G==1&&S==1&&R==0);
                    Check(T.Core.Translation(Now,M,[](){return true;},[](){return true;},[&](){return Index.CanReserve(1,Root,{-50,0},Now,.7);}));
                    Check(T.Align(180,Now,M,Hold)&&Holds==1);
                }
            }
        }
        Check(Committed&&T.Starts==1&&T.Commits==1);
    }
    // Existing live translation forbids even calling the turn hold callback.
    ScheduledTurn Live;Live.Core.Current.Envelope={50,0,190,true};int Calls=0;
    Check(!Live.Align(90,0,{{0,0},{10,0},0,1},[&](Vec2,RotatingEnvelopeStudy::Body){++Calls;return true;}));Check(Calls==0);
    // Root80 passes but a posed-body envelope pair of54+54 does not.
    Check(!RotatingEnvelopeStudy::Pair({{0,0},{0,0},0,2},{54,0,205.2,true},{{100,0},{100,0},0,0},{54,0,205.2,true},0));
    // Previous WPO on the translation->turn boundary retains the old linear
    // root at previous time, rather than snapping that root to the new endpoint.
    ScheduledTurn Boundary;Boundary.Core.Current.Root={90,0};Boundary.Core.Current.Envelope={50,0,190,true};
    Boundary.DrainedLinear={{0,0},{90,0},0,1};
    MotionReservation Ended{{90,0},{90,0},1,1};
    Check(!Boundary.Align(90,1,Ended,[](Vec2,RotatingEnvelopeStudy::Body){return true;}));
    const Vec2 Pose{30,20},Vat{5,3};
    Check(Length(Boundary.PreviousPosed(Pose,Vat,Vat,.99,Ended)-(Vec2{89.1,0}+Pose+Vat))<1e-7);
    Check(Length(Boundary.PreviousPosed(Pose,Vat,Vat,1,Ended)-(Vec2{90,0}+Pose+Vat))<1e-7);
    std::cout<<"angular integration checks="<<Checks<<" failures="<<Failures<<"\n";return Failures?1:0;
}
