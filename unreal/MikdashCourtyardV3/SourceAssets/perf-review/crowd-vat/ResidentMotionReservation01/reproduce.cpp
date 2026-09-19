#include "CrowdGroupMath.h"
#include <iostream>
#include <iomanip>

// Diagnostic of the existing production index, NOT an acceptance test.
// Exit zero means the defect was reproduced, not that movement is safe.
int main()
{
    using namespace MikdashCrowdGroups;
    using namespace MikdashCrowd;
    SpatialIndex Index;
    const Vec2 A{0,0}, B{80,80}, AEnd{99,0}, BEnd{80,-19};
    const bool Seeded=Index.Insert(0,A)&&Index.Insert(1,B);
    const bool PlanA=Index.SegmentClear(A,AEnd,0);
    const bool PlanB=Index.SegmentClear(B,BEnd,1);
    // Both 99cm paths pass against the other stored anchor. At the same
    // normalized time 80/99, the rendered roots occupy precisely (80,0).
    const double T=80.0/99.0;
    const double CrossingDistance=Length((A+(AEnd-A)*T)-(B+(BEnd-B)*T));
    const bool Committed=Index.Relocate(0,A,AEnd)&&Index.Relocate(1,B,BEnd);
    const double EndDistance=Length(AEnd-BEnd);
    // Both proposed escape steps increase distance monotonically, but the
    // segment's starting point is already inside the forbidden 80cm radius.
    const bool EscapeA=Index.SegmentClear(AEnd,AEnd+Vec2{90,0},0);
    const bool EscapeB=Index.SegmentClear(BEnd,BEnd+Vec2{0,-90},1);
    std::cout<<std::boolalpha<<std::setprecision(15)
        <<"{\n  \"diagnostic_only\": true,\n"
        <<"  \"seeded\": "<<Seeded<<",\n"
        <<"  \"accepted_plan_a\": "<<PlanA<<",\n"
        <<"  \"accepted_plan_b\": "<<PlanB<<",\n"
        <<"  \"simultaneous_crossing_distance_cm\": "<<CrossingDistance<<",\n"
        <<"  \"committed\": "<<Committed<<",\n"
        <<"  \"end_distance_cm\": "<<EndDistance<<",\n"
        <<"  \"escape_a_accepted\": "<<EscapeA<<",\n"
        <<"  \"escape_b_accepted\": "<<EscapeB<<"\n}\n";
    return Seeded&&PlanA&&PlanB&&Committed&&CrossingDistance<1e-9
        &&EndDistance<MinSeparationCm&&!EscapeA&&!EscapeB?0:1;
}
