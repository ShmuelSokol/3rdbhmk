#pragma once
#include "RouteContinuityStudy.h"
// OFFLINE: rolling shared route, maximum three anchors (two400cm legs).
// Goal frontier = minimum member progress + existing100cm SlowLag. Individual
// progress is monotone route bookkeeping, never an unreserved position update.
// Body yaw, clip speed, horizon and hard250cm formation permission are unchanged.
namespace TravellingCohortStudy
{
using namespace MikdashCrowd;using namespace MikdashCrowdGroups;
struct Travel
{
    bool Active=false,Failed=false;int Count=0,Legs=0;
    Vec2 Offset[MaxMembers]{};std::vector<Vec2> Anchors;
    int Segment[MaxMembers]{};double Progress[MaxMembers]{},Base=0,Frontier=0;
    int FormationRefusals=0,GoalUpdates=0;
    double MaximumFormationError=0,MaximumPhysicalLag=0;
    void Begin(int N,const Vec2* Goals)
    {
        Count=N;Active=true;Anchors.push_back(Goals[0]);
        for(int I=0;I<N;++I)Offset[I]=Goals[I]-Goals[0];
    }
    template<class Gate> bool Append(Gate&& Allowed)
    {
        if(Anchors.size()>=3)return false;
        const auto Guide=FindBoundaryRoute(Anchors.back(),0,400,[&](Vec2 A,Vec2 B)
        {for(int I=0;I<Count;++I)if(!Allowed(A+Offset[I],B+Offset[I]))return false;return true;});
        if(!Guide.Clear)return false;
        Anchors.push_back(Anchors.back()+FromDegrees(Guide.Heading)*400);++Legs;return true;
    }
    Vec2 At(double Along) const
    {
        const double Local=Clamp(Along-Base,0.0,400.0*(Anchors.size()-1));
        const size_t I=std::min(static_cast<size_t>(Local/400),Anchors.size()-2);
        return Anchors[I]+(Anchors[I+1]-Anchors[I])*Clamp((Local-I*400)/400,0.0,1.0);
    }
    template<class Gate> bool Update(const Vec2* Roots,Vec2* Goals,double Lead,Gate&& Allowed)
    {
        if(Failed)return false;
        if(Anchors.size()<2&&!Append(Allowed)){Failed=true;return false;}
        for(int I=0;I<Count;++I)
        {
            int& S=Segment[I];const Vec2 P=Roots[I]-Offset[I];
            // Cross at most one route corner per observation. A close corner
            // grants no physical movement; reservations still own every cm.
            if(S+2<static_cast<int>(Anchors.size())&&Length(P-Anchors[S+1])<25)++S;
            const Vec2 D=Anchors[S+1]-Anchors[S];
            const double T=Clamp(Dot(P-Anchors[S],D)/Dot(D,D),0.0,1.0);
            Progress[I]=std::max(Progress[I],Base+400*(S+T));
        }
        bool Past=true;for(int I=0;I<Count;++I)if(Segment[I]==0)Past=false;
        if(Past)
        {
            Anchors.erase(Anchors.begin());Base+=400;
            for(int I=0;I<Count;++I)--Segment[I];
        }
        Frontier=Progress[0];for(int I=1;I<Count;++I)Frontier=std::min(Frontier,Progress[I]);Frontier+=Lead;
        if(Frontier>Base+400*(Anchors.size()-1)-Lead)
            if(Anchors.size()<3&&!Append(Allowed)){Failed=true;return false;}
        // A member must visit its own corner before looking onto the next leg.
        // Otherwise a geometrically legal shortcut can bypass the corner used
        // by segment bookkeeping and permanently clamp its progress there.
        for(int I=0;I<Count;++I)
            Goals[I]=At(std::min(std::max(Frontier,Progress[I]),Base+400*(Segment[I]+1)))+Offset[I];
        ++GoalUpdates;return true;
    }
    // Relative position is linear between any pair of reservation endpoints.
    // Norm is convex, so checking all breakpoints bounds its maximum over the
    // complete segments and the indefinite endpoint holds, not just samples.
    bool Within(const MotionReservation* Motions,double Now,double Hard) const
    {
        for(int I=1;I<Count;++I)
        {
            const double Times[]={Now,std::max(Now,Motions[0].End),std::max(Now,Motions[I].End)};
            for(double T:Times)
            {
                const Vec2 Relative=Motions[I].At(T)-Motions[0].At(T);
                if(Length(Relative-Offset[I])>Hard+1e-7)return false;
                if(Length(Relative)-Length(Offset[I])>Hard+1e-7)return false;
            }
        }
        return true;
    }
};
}
