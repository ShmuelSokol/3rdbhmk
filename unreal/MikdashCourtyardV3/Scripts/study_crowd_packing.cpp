// Offline packing experiment. Uses runtime geometry/group math; omits native
// collision and ground. Results are geometry-only experiments, not acceptance
// or mathematical capacity bounds (changed rejections can change later packing).
#include "CrowdFieldMath.h"
#include "CrowdGroupMath.h"
#include "../SourceAssets/perf-review/crowd-vat/packing-study01/packing-fixture.h"
#include <algorithm>
#include <iostream>
#include <vector>
using namespace MikdashCrowd;
using namespace MikdashCrowdGroups;
int main()
{
    for(const auto& Z:Zones) for(int Mode=0;Mode<3;++Mode)
    {
        SpatialIndex Occupied;
        Geometry G;G.Zone=Z.P;G.ZoneCount=4;G.EdgeMargin=Z.Margin;
        G.Protected=Protected;G.Starts=Starts;G.Counts=Counts;G.ProtectedCount=ProtectedCount;G.ProtectedMargin=150;
        const auto Batches=PlanSeedBatches(Z.Count,Z.First,.15,20260907u);
        const Vec2 U=Z.P[1]-Z.P[0], V=Z.P[3]-Z.P[0];
        const Vec2 Axis=Length(U)>Length(V)?U:V;
        int Placed=0,Refused=0,Trials=0;int RefusedBySize[7]{};
        for(const auto& Batch:Batches)
        {
            std::vector<Vec2> Candidates;
            for(int Attempt=0;Attempt<1024;++Attempt)
            {
                Vec2 P;
                if(SeedPointInZone(Z.P,4,Protected,Starts,Counts,ProtectedCount,150,Z.Margin,
                    20260907u,static_cast<uint32_t>(Batch.First)+static_cast<uint32_t>(Attempt)*65537u,1,P))
                    Candidates.push_back(P);
            }
            if(Mode) std::stable_sort(Candidates.begin(),Candidates.end(),[&](const Vec2&A,const Vec2&B)
                {const double a=A.X*Axis.X+A.Y*Axis.Y,b=B.X*Axis.X+B.Y*Axis.Y;return Mode==1?a<b:a>b;});
            bool Done=false;
            for(const auto& Anchor:Candidates)
            {
                ++Trials;Vec2 Points[MaxMembers];Points[0]=Anchor;
                const double Heading=YawDegrees(SampleFlow(Z.Flow,Anchor,0,20260907u,Batch.First));
                bool Okay=true;
                for(int M=0;M<Batch.Count&&Okay;++M)
                {
                    if(M) Points[M]=Anchor+WorldOffset(Offset(M,20260907u,Batch.First,120),Heading);
                    Okay=SegmentAllowed(G,Points[M],Points[M])&&Occupied.SegmentClear(Points[M],Points[M],-1);
                    for(int O=0;O<M;++O) if(Length(Points[O]-Points[M])<MinSeparationCm) Okay=false;
                    const int Pieces=std::max(1,static_cast<int>(std::ceil(Length(Points[M]-Anchor)/80.)));
                    for(int I=0;I<Pieces&&Okay;++I)
                        Okay=SegmentAllowed(G,Anchor+(Points[M]-Anchor)*(double(I)/Pieces),Anchor+(Points[M]-Anchor)*(double(I+1)/Pieces));
                }
                if(!Okay) continue;
                int Inserted=0;
                for(;Inserted<Batch.Count;++Inserted) if(!Occupied.Insert(Batch.First+Inserted,Points[Inserted])) break;
                if(Inserted!=Batch.Count)
                {for(int I=0;I<Inserted;++I) Occupied.Remove(Batch.First+I,Points[I]);continue;}
                Placed+=Batch.Count;Done=true;break;
            }
            if(!Done){Refused+=Batch.Count;++RefusedBySize[Batch.Count];}
        }
        std::cout<<Z.Name<<" mode="<<Mode<<" placed="<<Placed<<" refused="<<Refused<<" trials="<<Trials<<" refusedCohortsBySize=";
        for(int S=1;S<=6;++S) std::cout<<S<<":"<<RefusedBySize[S]<<",";
        std::cout<<"\n";
    }
}
