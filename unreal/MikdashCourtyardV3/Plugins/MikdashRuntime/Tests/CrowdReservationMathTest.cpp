#include "CrowdGroupMath.h"
#include <iostream>
#include <limits>
#include <random>
int main()
{
    using namespace MikdashCrowd;
    using namespace MikdashCrowdGroups;
    int Checks=0,Failures=0;
    auto Expect=[&](bool Okay,const char* Label){++Checks;if(!Okay){++Failures;std::cerr<<Label<<"\n";}};
    {
        SpatialIndex S;
        Expect(S.Insert(0,{0,0})&&S.Insert(1,{80,80}),"crossing seed");
        Expect(S.Reserve(0,{0,0},{99,0},0,1),"first crossing plan is safe against stationary neighbor");
        Expect(!S.Reserve(1,{80,80},{80,-19},0,1),"simultaneous crossing refused");
        Expect(!S.CanReserve(0,{0,0},{0,0},.5,.5),"early stop/replan refused");
        Expect(!S.Relocate(0,{0,0},{49.5,0},.5),"early partial commit refused");
        Expect(!S.Relocate(0,{0,0},{98,0},1),"wrong completed endpoint refused");
        Expect(!S.Reserve(0,{0,0},{1,0},2,1),"expired path must commit its actual endpoint before replanning");
        Expect(S.Relocate(0,{0,0},{99,0},1),"completed endpoint commit");
        Expect(S.Reserve(0,{99,0},{198,0},1,1),"completed movement can replan");
    }
    {
        SpatialIndex S;
        Expect(S.Insert(0,{0,0})&&S.Insert(1,{-120,0}),"following seed");
        Expect(S.Reserve(0,{0,0},{99,0},0,1),"leader reserves");
        Expect(S.Reserve(1,{-120,0},{-21,0},0,1),"follower advances at constant120cm gap");
        Expect(S.Relocate(1,{-120,0},{-21,0},1),"follower reaches endpoint");
        Expect(!S.Reserve(1,{-21,0},{78,0},1,1),"stopped leader endpoint remains protected even before index commit");
    }
    {
        SpatialIndex S;
        Expect(S.Insert(0,{190,0})&&S.Insert(1,{270,80}),"cell boundary seed");
        Expect(S.Reserve(0,{190,0},{289,0},3,1),"cross-cell reservation");
        Expect(!S.Reserve(1,{270,80},{270,-19},3,1),"neighbor planned path found across cells");
        Expect(S.Relocate(0,{190,0},{289,0},4),"cross-cell commit");
    }
    const MotionReservation A{{0,0},{100,0},0,1};
    {
        SpatialIndex S;S.Insert(0,{0,0});S.Insert(1,{-120,0});
        Expect(S.Reserve(0,{0,0},{99,0},0,1)&&S.Reserve(1,{-120,0},{-21,0},.5,1),
            "staggered follower evaluates moving leader at common time");
    }
    Expect(ReservationDistance(A,{{200,0},{100,0},0,1},0)==0,"head-on collision");
    Expect(ReservationDistance(A,{{50,100},{50,-100},0,2},0)<50,"unequal duration collision approach");
    Expect(ReservationDistance(A,{{100,200},{100,0},2,4},0)==0,"later collision with stopped endpoint");
    Expect(std::abs(ReservationDistance(A,{{-120,0},{-20,0},0,1},0)-120)<1e-9,"analytic following gap");
    Expect(ReservationDistance(A,{{100,80},{100,80},0,0},5)==80,"expired intervals retain endpoints");
    {
        SpatialIndex S;S.Insert(0,{0,0});
        const double Nan=std::numeric_limits<double>::quiet_NaN();
        Expect(!S.Reserve(0,{0,0},{1,0},Nan,1),"nonfinite time refused");
        Expect(!S.Reserve(0,{0,0},{1,0},0,0),"zero duration refused");
        Expect(!S.Reserve(0,{0,0},{101,0},0,1),"oversized reservation refused");
        Expect(!S.Reserve(7,{0,0},{1,0},0,1),"unknown occupant refused");
    }
    // Independent dense-time oracle: exact continuous minimum cannot exceed
    // any sample and cannot be substantially below the closest dense sample.
    std::mt19937 Rng(61729);
    std::uniform_real_distribution<double> Pos(-300,300),Time(0,2),Duration(.05,1);
    for(int Case=0;Case<250;++Case)
    {
        MotionReservation P{{Pos(Rng),Pos(Rng)},{Pos(Rng),Pos(Rng)},Time(Rng),0};
        MotionReservation Q{{Pos(Rng),Pos(Rng)},{Pos(Rng),Pos(Rng)},Time(Rng),0};
        P.End=P.Start+Duration(Rng);Q.End=Q.Start+Duration(Rng);
        const double Now=Time(Rng),Until=std::max({Now,P.End,Q.End});
        auto Sample=[](const MotionReservation& M,double T){
            if(T<=M.Start)return M.From;if(T>=M.End)return M.To;
            return M.From+(M.To-M.From)*((T-M.Start)/(M.End-M.Start));};
        double Dense=1e30;
        for(int I=0;I<=20000;++I)
        {
            const double T=Now+(Until-Now)*I/20000.0;
            Dense=std::min(Dense,Length(Sample(P,T)-Sample(Q,T)));
        }
        const double Exact=ReservationDistance(P,Q,Now);
        Expect(Exact<=Dense+1e-8&&Dense-Exact<1.0,"continuous minimum agrees with independent dense oracle");
        Expect(std::abs(Exact-ReservationDistance(Q,P,Now))<1e-9,"distance symmetry");
    }
    std::cout<<"CrowdReservationMath: "<<Checks<<" checks, "<<Failures<<" failures\n";
    return Failures?1:0;
}
