#pragma once
#include "MeasuredProfiles.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <stdexcept>
#include <vector>

// Exact rational predicates/clipping, with deliberately bounded arithmetic.
// Coordinates are local centimetres. No implicit conversion from UE floats.
namespace FullFootprint {
struct Arithmetic : std::exception {};
struct BudgetExceeded : std::exception {};
struct Invalid : std::exception {};
struct Q {
    int64_t n=0,d=1;
    Q(int64_t a=0,int64_t b=1) {
        constexpr int64_t L=1000000000;
        if(b==0 || a < -2000000000000000000LL || a > 2000000000000000000LL ||
           b < -2000000000000000000LL || b > 2000000000000000000LL) throw Arithmetic{};
        if(b<0){a=-a;b=-b;}
        auto g=std::gcd(a,b);a/=g;b/=g;
        if(a < -L || a > L || b>L)throw Arithmetic{};
        n=a;d=b;
    }
};
inline Q operator+(Q a,Q b){return {a.n*b.d+b.n*a.d,a.d*b.d};}
inline Q operator-(Q a,Q b){return {a.n*b.d-b.n*a.d,a.d*b.d};}
inline Q operator*(Q a,Q b){return {a.n*b.n,a.d*b.d};}
inline Q operator/(Q a,Q b){return {a.n*b.d,a.d*b.n};}
inline bool operator<(Q a,Q b){return a.n*b.d<b.n*a.d;}
inline bool operator==(Q a,Q b){return a.n==b.n&&a.d==b.d;}
inline Q Abs(Q a){return {a.n<0?-a.n:a.n,a.d};}
struct V {Q x,y;};
inline V operator+(V a,V b){return {a.x+b.x,a.y+b.y};}
inline V operator-(V a,V b){return {a.x-b.x,a.y-b.y};}
inline V operator*(V a,Q b){return {a.x*b,a.y*b};}
inline Q Cross(V a,V b){return a.x*b.y-a.y*b.x;}
inline Q Side(V a,V b,V p){return Cross(b-a,p-a);}
using Poly=std::vector<V>;
struct Limits {size_t patches=128,fragments=512,vertices=8192,operations=200000;};
struct Work {
    Limits l;size_t operations=0;
    void Tick(size_t n=1){if(n>l.operations-operations)throw BudgetExceeded{};operations+=n;}
    void Check(const std::vector<Poly>& p){size_t v=0;if(p.size()>l.fragments)throw BudgetExceeded{};
        for(const auto& a:p){if(a.size()>l.vertices-v)throw BudgetExceeded{};v+=a.size();}}
};
inline bool Area(const Poly& p) { // Nondegeneracy only, never an area-sum certificate.
    for(size_t i=2;i<p.size();++i)if(Side(p[0],p[1],p[i]).n!=0)return true;
    return false;
}
inline Poly Clip(const Poly& p,V a,V b,bool inside,Work& w){
    Poly out;if(p.empty())return out;
    for(size_t i=0;i<p.size();++i){w.Tick();V u=p[i],v=p[(i+1)%p.size()];
        Q su=Side(a,b,u),sv=Side(a,b,v);bool iu=inside?su.n>=0:su.n<=0,iv=inside?sv.n>=0:sv.n<=0;
        auto add=[&](V t){if(out.empty()||!(out.back().x==t.x&&out.back().y==t.y))out.push_back(t);
            if(out.size()>w.l.vertices)throw BudgetExceeded{};};
        if(iu)add(u);if(iu!=iv)add(u+(v-u)*(su/(su-sv)));
    }
    if(out.size()>1&&out.front().x==out.back().x&&out.front().y==out.back().y)out.pop_back();
    return out;
}
inline Poly Hull(Poly p,Work& w){
    std::sort(p.begin(),p.end(),[](V a,V b){return a.x<b.x || (a.x==b.x&&a.y<b.y);});
    p.erase(std::unique(p.begin(),p.end(),[](V a,V b){return a.x==b.x&&a.y==b.y;}),p.end());
    Poly h;
    for(auto v:p){while(h.size()>1&&Side(h[h.size()-2],h.back(),v).n<=0){w.Tick();h.pop_back();}h.push_back(v);}
    const auto k=h.size();
    for(size_t i=p.size()-1;i-->0;){auto v=p[i];while(h.size()>k&&Side(h[h.size()-2],h.back(),v).n<=0){w.Tick();h.pop_back();}h.push_back(v);}
    h.pop_back();return h;
}
struct Face {
    uint64_t component=0,instance=0,shape=0,geometryRevision=0,face=0;
    bool operator==(const Face& b)const{return component==b.component&&instance==b.instance&&shape==b.shape&&geometryRevision==b.geometryRevision&&face==b.face;}
};
struct Plane {Q x,y,z;Q At(V p)const{return x*p.x+y*p.y+z;}};
struct Patch {Face key;Poly xy;Plane height;}; // Strictly convex CCW triangle/rectangle only.
inline Patch Triangle(Face key,V a,Q za,V b,Q zb,V c,Q zc){
    auto u=b-a,v=c-a;Q det=Cross(u,v);if(det.n==0)throw Invalid{};
    Q x=((zb-za)*v.y-(zc-za)*u.y)/det,y=(u.x*(zc-za)-v.x*(zb-za))/det;
    if(det.n<0)std::swap(b,c);
    return {key,{a,b,c},{x,y,za-x*a.x-y*a.y}};
}
inline Patch Rectangle(Face key,Q x0,Q y0,Q x1,Q y1,Plane p={}){
    return {key,{{x0,y0},{x1,y0},{x1,y1},{x0,y1}},p};
}
struct Request {
    uint64_t serial=1,worldVersion=1,geometryVersion=1,bindingVersion=1;
    int profile=1;V from{},to{};Plane root;
    Q maxSlope{1,2},heightTolerance{1,100},contactBelowRoot{1,2};
};
enum class Status {Covered,Insufficient,InvalidInput,Budget,ArithmeticRange};
struct Certificate {
    uint32_t schema=1;
    Status status=Status::InvalidInput;
    Request request;Poly footprint;std::vector<Patch> supportFaces;
    double radius=0,minZ=0,maxZ=0; // Exact copied measured profile, never clamp minZ.
    size_t operations=0,residualFragments=0;
};
inline Certificate Cover(const Request& r,const std::vector<Patch>& patches,Limits limits={}){
    Certificate c;c.request=r;Work w{limits};
    try{
        if(!r.serial||!r.worldVersion||!r.geometryVersion||!r.bindingVersion||r.profile<0||r.profile>=6||
           r.maxSlope.n<0||r.heightTolerance.n<0||r.contactBelowRoot.n<0)throw Invalid{};
        const V step=r.to-r.from;
        if(Q(10000)<step.x*step.x+step.y*step.y)throw Invalid{}; // Existing 100cm index bound.
        if(patches.size()>limits.patches)throw BudgetExceeded{};
        const auto& b=MeasuredBodyStudy::Profiles[r.profile];c.radius=b.Radius;c.minZ=b.MinZ;c.maxZ=b.MaxZ;
        // Circumscribed square: each disc lies inside [-ceil(radius),+ceil(radius)]^2.
        // Convex hull of endpoint squares contains every translated disc on the segment.
        Q rad(static_cast<int64_t>(std::ceil(b.Radius)));Poly corners;
        for(V p:{r.from,r.to})for(int x:{-1,1})for(int y:{-1,1})corners.push_back(p+V{rad*Q(x),rad*Q(y)});
        c.footprint=Hull(corners,w);std::vector<Poly> remaining{c.footprint};w.Check(remaining);
        if(r.maxSlope<Abs(r.root.x)+Abs(r.root.y))throw Invalid{};
        // Validate ALL supplied patches, even when earlier patches cover the footprint.
        for(size_t i=0;i<patches.size();++i){const auto& p=patches[i];w.Tick();
            if(!p.key.component||!p.key.shape||!p.key.geometryRevision||(p.xy.size()!=3&&p.xy.size()!=4))throw Invalid{};
            for(size_t j=0;j<i;++j){w.Tick();if(p.key==patches[j].key)throw Invalid{};}
            for(size_t j=0;j<p.xy.size();++j){w.Tick();if(Side(p.xy[j],p.xy[(j+1)%p.xy.size()],p.xy[(j+2)%p.xy.size()]).n<=0)throw Invalid{};}
            // Height and slope check over WHOLE footprint is conservative (may over-refuse).
            bool eligible=!(r.maxSlope<Abs(p.height.x)+Abs(p.height.y));
            for(V v:c.footprint){w.Tick();if(r.heightTolerance<Abs(p.height.At(v)-r.root.At(v)))eligible=false;}
            if(!eligible)continue;
            c.supportFaces.push_back(p);
            std::vector<Poly> next;
            for(auto piece:remaining){
                for(size_t j=0;j<p.xy.size()&&!piece.empty();++j){
                    auto outside=Clip(piece,p.xy[j],p.xy[(j+1)%p.xy.size()],false,w);
                    if(Area(outside)){next.push_back(std::move(outside));w.Check(next);}
                    piece=Clip(piece,p.xy[j],p.xy[(j+1)%p.xy.size()],true,w);
                }
            }
            remaining=std::move(next);w.Check(remaining);
        }
        c.residualFragments=remaining.size();c.status=remaining.empty()?Status::Covered:Status::Insufficient;
    }catch(const BudgetExceeded&){c.status=Status::Budget;}
    catch(const Arithmetic&){c.status=Status::ArithmeticRange;}
    catch(const Invalid&){c.status=Status::InvalidInput;}
    catch(const std::bad_alloc&){c.status=Status::Budget;}
    c.operations=w.operations;
    if(c.status!=Status::Covered)c.supportFaces.clear();return c;
}
inline bool In(const Poly& p,V v){for(size_t j=0;j<p.size();++j)if(Side(p[j],p[(j+1)%p.size()],v).n<0)return false;return !p.empty();}
// This classifies ONE exact point witness, not an overlap, manifold, face, or component.
// Unexamined contacts remain potential obstacles; no obstacle-clear certificate exists here.
inline bool SupportPointCandidate(const Certificate& c,uint64_t world,uint64_t geometry,uint64_t binding,const Face& face,V xy,Q z,Q fraction=Q(0)){
    try{
        if(c.status!=Status::Covered||world!=c.request.worldVersion||geometry!=c.request.geometryVersion||binding!=c.request.bindingVersion||
           fraction.n<0||Q(1)<fraction||c.minZ < -double(c.request.contactBelowRoot.n)/double(c.request.contactBelowRoot.d)||!In(c.footprint,xy))return false;
        const V root=c.request.from+(c.request.to-c.request.from)*fraction;
        const Q rad(static_cast<int64_t>(std::ceil(c.radius)));
        if(rad<Abs(xy.x-root.x)||rad<Abs(xy.y-root.y)||c.request.heightTolerance<Abs(z-c.request.root.At(root)))return false;
        for(const auto& p:c.supportFaces)if(face==p.key&&In(p.xy,xy)&&z==p.height.At(xy))return true;
    }catch(const Arithmetic&){}return false;
}
}
