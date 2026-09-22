#include "CrowdGroupMath.h"
#include <iostream>
#include <limits>
int main()
{
    using namespace MikdashCrowd;
    using namespace MikdashCrowdGroups;
    int Checks=0,Failures=0;
    auto Expect=[&](bool Okay,const char* Label){++Checks;if(!Okay){++Failures;std::cerr<<Label<<"\n";}};
    const Vec2 Square[]={{-1000,-1000},{1000,-1000},{1000,1000},{-1000,1000}};
    Geometry World;World.Zone=Square;World.ZoneCount=4;World.EdgeMargin=100;
    auto Gate=[&](const Vec2& A,const Vec2& B){return SegmentAllowed(World,A,B);};
    auto Interior=FindBoundaryRoute({0,0},0,200,Gate);
    Expect(Interior.Clear&&Interior.Heading==0&&Interior.Probes==1,"interior preserves authored direction");
    auto Edge=FindBoundaryRoute({800,0},0,200,Gate);
    Expect(Edge.Clear&&Edge.Heading!=0,"turn guidance changes before committed step reaches east edge");
    int Calls=0;
    auto Bounded=FindBoundaryRoute({0,0},0,1e6,[&](const Vec2& A,const Vec2& B)
    {++Calls;Expect(Length(B-A)<=100,"guidance subsegments respect physical gate length");return true;});
    Expect(Bounded.Clear&&Calls==5,"guidance range capped400cm and five short segments");
    Calls=0;
    Expect(!FindBoundaryRoute({0,0},0,std::numeric_limits<double>::quiet_NaN(),
        [&](const Vec2&,const Vec2&){++Calls;return true;}).Clear&&Calls==0,"invalid lookahead refuses without world query");
    // Keep-out lies between endpoints; endpoint-only guidance would miss it.
    const Vec2 Hole[]={{-50,-100},{50,-100},{50,100},{-50,100}};
    const int Start[]={0},Count[]={4};World.Protected=Hole;World.Starts=Start;World.Counts=Count;World.ProtectedCount=1;World.ProtectedMargin=44;
    auto Around=FindBoundaryRoute({-200,0},0,400,Gate);
    Expect(Around.Clear&&Around.Heading!=0,"intermediate keep-out crossing changes guidance");
    World.ProtectedCount=0;
    // Constant eastward flow on a bounded floor: short-step validation alone
    // reaches the edge before turning. Guidance must sustain travel with normal
    // 90deg/s turns and unchanged geometric movement permission for two minutes.
    Vec2 P{700,0};double Heading=0,Travel=0;int Rejections=0;
    for(int Frame=0;Frame<3600;++Frame)
    {
        const auto Guide=FindBoundaryRoute(P,0,200,Gate);
        const double NextHeading=SteerHeading(Heading,Guide.Clear?Guide.Heading:0,1.0/30.0,90);
        Expect(std::abs(WrapDegrees(NextHeading-Heading))<=3.0000001,"anticipation respects turn cap");
        Heading=NextHeading;const Vec2 Next=P+FromDegrees(Heading)*4;
        if(Gate(P,Next)){P=Next;Travel+=4;}else ++Rejections;
        Expect(PointInPolygonWithMargin(Square,4,P,100),"walker remains within original inset");
    }
    Expect(Travel>10000&&Rejections<100,"boundary guidance sustains walking under constant outward flow");
    std::cout<<"CrowdBoundaryMath: "<<Checks<<" checks, "<<Failures<<" failures\n";
    return Failures?1:0;
}
