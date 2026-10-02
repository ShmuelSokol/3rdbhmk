#pragma once
#include <array>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <cfenv>
#if defined(_M_X64) || defined(__x86_64__)
#include <xmmintrin.h>
#endif
#if defined(__FAST_MATH__)
#error Conservative intervals require strict IEEE floating point, not fast math.
#endif

namespace ConservativeTransform {
static_assert(std::numeric_limits<double>::is_iec559&&std::numeric_limits<float>::is_iec559&&sizeof(double)==8&&sizeof(float)==4,"IEEE binary32/64 required");
enum class Precision {Binary64,Binary32};
struct Refused : std::runtime_error {using std::runtime_error::runtime_error;};
// Source contract: strict floating point on x64, masked exceptions, nearest rounding.
// DAZ concerns INPUTS; FTZ concerns RESULTS. Neither may affect proof arithmetic.
inline bool EnvironmentSupported(){
#if defined(_M_X64) || defined(__x86_64__)
    const unsigned csr=_mm_getcsr();
    return std::fegetround()==FE_TONEAREST && (csr&0x6000u)==0 && (csr&0x1f80u)==0x1f80u;
#else
    return false; // No guessed ARM/x87 environment equivalence.
#endif
}
class ScopedIEEE final {
    unsigned saved=0;
public:
    ScopedIEEE(){
        if(!EnvironmentSupported())throw Refused("unsupported floating-point environment");
#if defined(_M_X64) || defined(__x86_64__)
        saved=_mm_getcsr();_mm_setcsr(saved&~0x8040u);
#endif
    }
    ~ScopedIEEE() noexcept {
#if defined(_M_X64) || defined(__x86_64__)
        _mm_setcsr(saved);
#endif
    }
    ScopedIEEE(const ScopedIEEE&)=delete;
    ScopedIEEE& operator=(const ScopedIEEE&)=delete;
};
struct I {double lo,hi;};
using V=std::array<I,3>;
struct Ops {
    Precision mode=Precision::Binary64;unsigned count=0,limit=4096;
    explicit Ops(Precision p=Precision::Binary64,unsigned budget=4096):mode(p),limit(budget){
        if(!EnvironmentSupported())throw Refused("unsupported floating-point environment");
    }
    void Tick(){if(++count>limit)throw Refused("operation budget");}
    I Point(double x){ ScopedIEEE environment;
        if(!std::isfinite(x))throw Refused("nonfinite input");
        if(mode==Precision::Binary32)return Bound(x,x); // Enclose input narrowing too.
        if(std::abs(x)<std::numeric_limits<double>::min())return {std::min(x,0.0),std::max(x,0.0)};
        return {x,x};
    }
    I Bound(double lo,double hi){ ScopedIEEE environment;
        Tick();if(!std::isfinite(lo)||!std::isfinite(hi)||lo>hi)throw Refused("arithmetic range");
        if(mode==Precision::Binary32){
            const float a=static_cast<float>(lo),b=static_cast<float>(hi);
            lo=std::min(lo,double(std::nextafter(a,-std::numeric_limits<float>::infinity())));
            hi=std::max(hi,double(std::nextafter(b,std::numeric_limits<float>::infinity())));
        }else{
            lo=std::nextafter(lo,-std::numeric_limits<double>::infinity());
            hi=std::nextafter(hi,std::numeric_limits<double>::infinity());
        }
        if(!std::isfinite(lo)||!std::isfinite(hi))throw Refused("outward bound overflow");
        // Enclose flush-to-zero implementations as well as gradual underflow.
        const double tiny=mode==Precision::Binary32?double(std::numeric_limits<float>::min()):std::numeric_limits<double>::min();
        if(lo<tiny&&hi>-tiny){lo=std::min(lo,-tiny);hi=std::max(hi,tiny);}
        return {lo,hi};
    }
    I Add(I a,I b){ ScopedIEEE environment;return Bound(a.lo+b.lo,a.hi+b.hi);}
    I Sub(I a,I b){ ScopedIEEE environment;return Bound(a.lo-b.hi,a.hi-b.lo);}
    I Mul(I a,I b){ ScopedIEEE environment;
        std::array<double,4> p{a.lo*b.lo,a.lo*b.hi,a.hi*b.lo,a.hi*b.hi};
        return Bound(*std::min_element(p.begin(),p.end()),*std::max_element(p.begin(),p.end()));
    }
    V Add(V a,V b){return {Add(a[0],b[0]),Add(a[1],b[1]),Add(a[2],b[2])};}
    V Sub(V a,V b){return {Sub(a[0],b[0]),Sub(a[1],b[1]),Sub(a[2],b[2])};}
    V Mul(V a,I b){return {Mul(a[0],b),Mul(a[1],b),Mul(a[2],b)};}
    V Cross(V a,V b){return {Sub(Mul(a[1],b[2]),Mul(a[2],b[1])),Sub(Mul(a[2],b[0]),Mul(a[0],b[2])),Sub(Mul(a[0],b[1]),Mul(a[1],b[0]))};}
};
struct Transform {std::array<double,3> scale,translation;std::array<double,4> quaternion;};
inline V Apply(Ops& op,V p,const Transform& t){
    ScopedIEEE environment;
    V q;for(int i=0;i<3;++i){p[i]=op.Mul(p[i],op.Point(t.scale[i]));q[i]=op.Point(t.quaternion[i]);}
    const auto twice=op.Mul(op.Cross(q,p),op.Point(2));
    const auto rotated=op.Add(op.Add(p,op.Mul(twice,op.Point(t.quaternion[3]))),op.Cross(q,twice));
    V translation;for(int i=0;i<3;++i)translation[i]=op.Point(t.translation[i]);
    return op.Add(rotated,translation);
}
inline V Chain(Ops& op,const std::array<double,3>& p,const Transform* chain,size_t n,const std::array<double,3>& localOrigin){
    ScopedIEEE environment;
    if(n==0||n>8)throw Refused("transform depth");
    V v;for(int i=0;i<3;++i)v[i]=op.Point(p[i]);
    for(size_t i=0;i<n;++i)v=Apply(op,v,chain[i]);
    for(int i=0;i<3;++i)v[i]=op.Sub(v[i],op.Point(localOrigin[i]));
    return v;
}
struct GridBox {std::array<int64_t,3> lo,hi;};
inline GridBox OuterBox(const V& v,int exponent=-10){
    ScopedIEEE environment;
    if(exponent < -20||exponent>0)throw Refused("grid exponent");
    const double step=std::ldexp(1.0,exponent);GridBox r;
    for(int i=0;i<3;++i){
        double a=std::floor(v[i].lo/step),b=std::ceil(v[i].hi/step);
        if(!std::isfinite(a)||!std::isfinite(b)||std::abs(a)>double(int64_t(1)<<40)||std::abs(b)>double(int64_t(1)<<40))throw Refused("grid range");
        r.lo[i]=static_cast<int64_t>(a);r.hi[i]=static_cast<int64_t>(b);
    }return r;
}
// Convex hull of the three vertex boxes encloses every possible transformed
// triangle. Do not replace a mesh/union with one AABB or call intersection penetration.
using Triangle=std::array<V,3>;
inline I Edge(Ops& op,const V& a,const V& b,I x,I y){return op.Sub(op.Mul(op.Sub(b[0],a[0]),op.Sub(y,a[1])),op.Mul(op.Sub(b[1],a[1]),op.Sub(x,a[0])));}
struct InnerTriangle {std::array<std::array<int64_t,2>,3> xy;int exponent=-10;};
inline InnerTriangle Inner(Ops& op,const Triangle& t,int exponent=-10){
    ScopedIEEE environment;
    if(exponent < -20||exponent>0)throw Refused("grid exponent");
    const double step=std::ldexp(1.0,exponent);
    std::array<std::array<double,2>,3> mid{};std::array<double,2> center{};
    for(int i=0;i<3;++i)for(int j=0;j<2;++j){mid[i][j]=t[i][j].lo+(t[i][j].hi-t[i][j].lo)*.5;center[j]+=mid[i][j]/3;}
    // Trial construction may round; acceptance is independently interval-proved.
    for(int attempt=0;attempt<20;++attempt){
        const double fraction=std::ldexp(1.0,attempt-20);InnerTriangle out;out.exponent=exponent;
        for(int i=0;i<3;++i)for(int j=0;j<2;++j){
            const double candidate=std::nearbyint((mid[i][j]+(center[j]-mid[i][j])*fraction)/step);
            if(!std::isfinite(candidate)||std::abs(candidate)>double(int64_t(1)<<40))throw Refused("inner grid range");
            out.xy[i][j]=static_cast<int64_t>(candidate);
        }
        bool yes=true;
        for(int vertex=0;vertex<3;++vertex)for(int edge=0;edge<3;++edge){
            auto x=op.Point(double(out.xy[vertex][0])*step),y=op.Point(double(out.xy[vertex][1])*step);
            if(Edge(op,t[edge],t[(edge+1)%3],x,y).lo<=0)yes=false;
        }
        // All three vertices lie strictly inside all three possible halfplanes;
        // convexity proves the WHOLE returned polygon, not sampled coverage.
        if(yes){
            auto x=op.Point(double(out.xy[2][0])*step),y=op.Point(double(out.xy[2][1])*step);
            V a{op.Point(double(out.xy[0][0])*step),op.Point(double(out.xy[0][1])*step),op.Point(0)};
            V b{op.Point(double(out.xy[1][0])*step),op.Point(double(out.xy[1][1])*step),op.Point(0)};
            if(Edge(op,a,b,x,y).lo>0)return out;
        }
    }throw Refused("no certified inner triangle within budget");
}
inline bool ObstacleSeparated(Ops& op,const Triangle& tri,const std::array<double,4>& plane){
    ScopedIEEE environment;
    // Outside one candidate-body halfspace: all possible vertices strictly outside
    // implies all convex combinations outside. No separation => unknown/obstacle.
    for(const auto& vertex:tri){I d=op.Point(plane[3]);for(int i=0;i<3;++i)d=op.Add(d,op.Mul(vertex[i],op.Point(plane[i])));if(d.hi>=0)return false;}
    return true;
}
inline bool HeightBand(const Triangle& tri,double lower,double upper){
    ScopedIEEE environment;
    if(!std::isfinite(lower)||!std::isfinite(upper)||lower>upper)return false;
    for(const auto& v:tri)if(v[2].lo<lower||v[2].hi>upper)return false;
    return true; // Every barycentric point height is in this band; NOT an exact plane.
}
}
