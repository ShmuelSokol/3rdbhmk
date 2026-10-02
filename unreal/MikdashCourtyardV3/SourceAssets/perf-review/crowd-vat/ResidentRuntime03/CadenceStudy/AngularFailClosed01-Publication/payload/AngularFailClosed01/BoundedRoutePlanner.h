#pragma once
#include "RuntimePortConstraints.h"
#include <queue>
#include <limits>
// New offline adaptation, NOT the frozen planner. Bounded translated 20cm grid;
// search survives work deferral. All execution still needs full runtime gates.
namespace ActualHorizonReview
{
using namespace RuntimePortReview;
constexpr int Width=91,Nodes=Width*Width;
template<class Gate> Target SelectExecutable(Vec2 Root,Vec2 Goal,const std::vector<Vec2>& Path,std::size_t Cursor,const Steps& S,Gate&& Allowed)
{
    auto T=ExecutableTarget(Root,Path,Cursor,S,Allowed);
    if(T.Valid)return T;
    // A graph endpoint is inside the arrival disk, not necessarily an executable
    // final clip endpoint. Try a fully visible bounded connector INTO that same
    // disk. A minimum-length extension past its centre is allowed only while
    // still inside the original25cm region. Never shorten a committed horizon.
    const double D=Length(Goal-Root);
    if(!S.Valid||D<25||D>99)return T;
    const Vec2 End=Root+Normalized(Goal-Root)*std::max(D,S.Minimum);
    if(Length(End-Goal)>=25||Length(End-Root)>99||!Allowed(Root,End))return T;
    const int Count=Parts(Length(End-Root),S);if(!Count)return T;
    return {true,Root+(End-Root)*(1.0/Count),Cursor};
}
enum class Status { Pending,Found,Unreachable,Invalid,Stale };
struct Budget
{
    int Calls=0,Expanded=0,Queries=0,Pops=0;
    bool Call(){if(Calls>=2)return false;++Calls;return true;}
    bool Query(){if(Queries>=512)return false;++Queries;return true;}
};
struct Planner
{
    Status Result=Status::Pending;Vec2 Start{},Goal{};Steps Limits{};GridFrame Grid{};
    Revisions Revision{};int Stage=0,Connector=0,Active=-1,Edge=0;
    std::vector<double> Cost;std::vector<int> Parent;std::vector<bool> Closed;
    using Item=std::pair<double,int>;
    std::priority_queue<Item,std::vector<Item>,std::greater<Item>> Open;
    std::vector<Vec2> Path;int TotalExpanded=0,TotalQueries=0;
    Planner(Vec2 S,Vec2 G,Steps L,GridFrame F,Revisions R):Start(S),Goal(G),Limits(L),Grid(F),Revision(R)
    {if(!Limits.Valid||!Grid.Contains(S)||!Grid.Contains(G))Result=Status::Invalid;}
    Vec2 Position(int Id)const{return Grid.World({-900.+(Id%Width)*20.,-900.+(Id/Width)*20.});}
    double Heuristic(Vec2 P)const{return std::max(0.,Length(P-Goal)-25);}
    template<class Gate> Status Pump(Budget& Work,Revisions Current,Gate&& Allowed)
    {
        if(Current.Geometry!=Revision.Geometry||Current.RelevantEndpoints!=Revision.RelevantEndpoints)return Result=Status::Stale;
        if(Result!=Status::Pending||!Work.Call())return Result;
        int ThisCall=0;
        while(Stage<2)
        {
            if(!Work.Query())return Result;++TotalQueries;
            const Vec2 P=Stage==0?Start:Goal;
            if(!Allowed(P,P))return Result=Status::Invalid;
            ++Stage;
        }
        if(Cost.empty())
        {
            if(Length(Goal-Start)<25){Path={Start};return Result=Status::Found;}
            Cost.assign(Nodes,std::numeric_limits<double>::infinity());Parent.assign(Nodes,-2);Closed.assign(Nodes,false);
        }
        const Vec2 Local=Grid.Local(Start);
        const int X=static_cast<int>(std::floor((Local.X+900)/20)),Y=static_cast<int>(std::floor((Local.Y+900)/20));
        while(Connector<25)
        {
            const int Nx=X+Connector%5-2,Ny=Y+Connector/5-2;
            if(Nx<0||Nx>=Width||Ny<0||Ny>=Width){++Connector;continue;}
            const int Id=Ny*Width+Nx;const Vec2 P=Position(Id);const double D=Length(P-Start);
            if(D>1e-7&&!Parts(D,Limits)){++Connector;continue;}
            if(!Work.Query())return Result;++TotalQueries;++Connector;
            if(!Allowed(Start,P))continue;
            Cost[Id]=D;Parent[Id]=-1;Open.push({D+Heuristic(P),Id});
        }
        while(true)
        {
            if(Active<0)
            {
                if(Work.Expanded>=96||ThisCall>=64)return Result;
                while(!Open.empty())
                {
                    if(Work.Pops>=512)return Result;
                    ++Work.Pops;const int Id=Open.top().second;Open.pop();
                    if(!Closed[Id]){Active=Id;break;}
                }
                if(Active<0)return Result=Status::Unreachable;
                Closed[Active]=true;++Work.Expanded;++ThisCall;++TotalExpanded;Edge=0;
                if(Length(Position(Active)-Goal)<25)
                {
                    for(int Id=Active;Id>=0;Id=Parent[Id])Path.push_back(Position(Id));
                    Path.push_back(Start);std::reverse(Path.begin(),Path.end());
                    if(Path.size()>1&&Length(Path[1]-Start)<1e-7)Path.erase(Path.begin()+1);
                    return Result=Status::Found;
                }
            }
            while(Edge<9)
            {
                const int Dx=Edge%3-1,Dy=Edge/3-1;
                const int Nx=Active%Width+Dx,Ny=Active/Width+Dy;
                if((Dx==0&&Dy==0)||Nx<0||Nx>=Width||Ny<0||Ny>=Width){++Edge;continue;}
                const int Next=Ny*Width+Nx;
                if(Closed[Next]){++Edge;continue;}
                const Vec2 P=Position(Active),Q=Position(Next);const double New=Cost[Active]+Length(Q-P);
                if(New>=Cost[Next]){++Edge;continue;}
                if(!Work.Query())return Result;++TotalQueries;++Edge;
                if(!Allowed(P,Q))continue;
                Cost[Next]=New;Parent[Next]=Active;Open.push({New+Heuristic(Q),Next});
            }
            Active=-1;
        }
    }
};
}
