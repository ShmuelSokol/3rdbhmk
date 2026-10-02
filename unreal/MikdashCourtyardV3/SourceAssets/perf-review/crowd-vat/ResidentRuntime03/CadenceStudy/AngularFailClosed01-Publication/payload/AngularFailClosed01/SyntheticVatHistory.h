#pragma once
#include "CrowdFieldMath.h"
// Analytic, time-varying NONZERO clip poses for history verification only.
// Not resident texture samples or native animation acceptance.
namespace SyntheticVatStudy {
struct Clip {bool Walking=false;double Start=0;};
inline MikdashCrowd::Vec2 Sample(const Clip& C,double Time) {
 const double Phase=(Time-C.Start)*(C.Walking?7.:2.);
 return C.Walking?MikdashCrowd::Vec2{3.*std::sin(Phase)+1.,1.5*std::cos(Phase)}
                 :MikdashCrowd::Vec2{.8*std::cos(Phase),.5*std::sin(Phase)+.25};
}
struct History {
 Clip Current{},Previous{};float Updated=-1;
 int Switches=0;
 void Observe(float MutationTime,bool Walking,double Now) {
   if(Updated!=MutationTime){Previous=Current;Updated=MutationTime;}
   if(Current.Walking!=Walking){Current={Walking,Now};++Switches;}
 }
};
}
