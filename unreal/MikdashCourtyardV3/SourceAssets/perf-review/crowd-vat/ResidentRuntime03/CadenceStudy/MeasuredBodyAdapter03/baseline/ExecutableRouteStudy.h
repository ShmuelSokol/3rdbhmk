#pragma once
#include "CrowdGroupMath.h"
#include <queue>
#include <limits>

// OFFLINE prototype. A fixed 20cm, 8-connected lattice over the fixture's
// [-900,900]^2 inset: 91^2 nodes, at most 8281 expansions, 8 edges per expansion.
// Resolution follows the existing geometry sampler, not terminal coordinates.
// Every edge is separately validated: diagonals cannot cut occupied corners.
// Attach the off-grid start to its surrounding 5x5 lattice nodes (<85cm).
// Goal is the existing 25cm arrival region. Start connectors shorter than a
// playable VAT step are excluded. Completeness is ONLY for this finite graph;
// sub-grid corridors and routes outside this domain can be missed. Failure is
// graph-unreachable, not a proof of continuous-space impossibility. The callback
// must use frozen peers; moving peers require execution-time revalidation.
namespace DetourRoutingStudy
{
using namespace MikdashCrowd;
constexpr double Cell=20,Low=-900,High=900,Arrival=25;
constexpr int Width=91,Nodes=Width*Width;
enum class Status { Found, Unreachable, Invalid, WorkLimit };
struct Route
{
    Status Result=Status::Invalid;
    std::vector<Vec2> Points;
    int Expanded=0,Queries=0;
    double Distance=0;
};
inline Vec2 Position(int Id) { return {Low+(Id%Width)*Cell,Low+(Id/Width)*Cell}; }
template<class Gate> Route Find(Vec2 Start,Vec2 Goal,double MinimumStep,Gate&& Allowed,int Limit=Nodes)
{
    Route Out;
    const auto Inside=[](Vec2 P){return Finite(P)&&P.X>=Low&&P.X<=High&&P.Y>=Low&&P.Y<=High;};
    if(!Inside(Start)||!Inside(Goal)||!std::isfinite(MinimumStep)||MinimumStep<=0||MinimumStep>Cell||Limit<0) return Out;
    const auto Check=[&](Vec2 A,Vec2 B){++Out.Queries;return Allowed(A,B);};
    if(!Check(Start,Start)||!Check(Goal,Goal)) return Out;
    if(Length(Goal-Start)<Arrival) {Out.Result=Status::Found;Out.Points.push_back(Start);return Out;}
    std::vector<double> Cost(Nodes,std::numeric_limits<double>::infinity());
    std::vector<int> Parent(Nodes,-2);
    std::vector<bool> Closed(Nodes,false);
    using Item=std::pair<double,int>;
    std::priority_queue<Item,std::vector<Item>,std::greater<Item>> Open;
    const auto Heuristic=[&](Vec2 P){return std::max(0.0,Length(P-Goal)-Arrival);};
    const int X=static_cast<int>(std::floor((Start.X-Low)/Cell));
    const int Y=static_cast<int>(std::floor((Start.Y-Low)/Cell));
    for(int Dy=-2;Dy<=2;++Dy) for(int Dx=-2;Dx<=2;++Dx)
    {
        const int Nx=X+Dx,Ny=Y+Dy;
        if(Nx<0||Ny<0||Nx>=Width||Ny>=Width) continue;
        const int Id=Ny*Width+Nx;const Vec2 P=Position(Id);const double D=Length(P-Start);
        // Start attachments must be executable at the fixed VAT horizon,
        // not merely longer than one minimum-speed step. Preserve corners.
        const double MaximumStep=MinimumStep*(90.0/(119.95*.45));
        const int Parts=std::max(1,static_cast<int>(std::ceil(D/MaximumStep)));
        if(D>1e-7&&D/Parts<MinimumStep-1e-7) continue;
        if(!Check(Start,P)) continue;
        Cost[Id]=D;Parent[Id]=-1;Open.push({D+Heuristic(P),Id});
    }
    int Finish=-1;
    while(!Open.empty())
    {
        const int Id=Open.top().second;Open.pop();if(Closed[Id]) continue;
        if(Out.Expanded>=Limit) {Out.Result=Status::WorkLimit;return Out;}
        Closed[Id]=true;++Out.Expanded;const Vec2 P=Position(Id);
        if(Length(P-Goal)<Arrival) {Finish=Id;break;}
        const int Cx=Id%Width,Cy=Id/Width;
        for(int Dy=-1;Dy<=1;++Dy) for(int Dx=-1;Dx<=1;++Dx)
        {
            if(Dx==0&&Dy==0) continue;
            const int Nx=Cx+Dx,Ny=Cy+Dy;
            if(Nx<0||Ny<0||Nx>=Width||Ny>=Width) continue;
            const int Next=Ny*Width+Nx;if(Closed[Next]) continue;
            const Vec2 Q=Position(Next);const double New=Cost[Id]+Length(Q-P);
            if(New>=Cost[Next]||!Check(P,Q)) continue;
            Cost[Next]=New;Parent[Next]=Id;Open.push({New+Heuristic(Q),Next});
        }
    }
    if(Finish<0) {Out.Result=Status::Unreachable;return Out;}
    for(int Id=Finish;Id>=0;Id=Parent[Id]) Out.Points.push_back(Position(Id));
    Out.Points.push_back(Start);std::reverse(Out.Points.begin(),Out.Points.end());
    if(Out.Points.size()>1&&Length(Out.Points[1]-Start)<1e-7) Out.Points.erase(Out.Points.begin()+1);
    Out.Distance=Cost[Finish];Out.Result=Status::Found;return Out;
}
}
