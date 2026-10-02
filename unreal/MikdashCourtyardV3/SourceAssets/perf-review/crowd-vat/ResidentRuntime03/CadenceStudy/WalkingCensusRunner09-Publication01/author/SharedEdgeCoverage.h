#pragma once
#include "TransformIntervals.h"
#include "SupportCoverage.h"
#include <map>

namespace SharedSupport {
using ConservativeTransform::I;using ConservativeTransform::V;using ConservativeTransform::Ops;
using ConservativeTransform::Precision;
struct Vertex {V position;};
// One vertex ID denotes ONE correlated physical vertex across all incident faces.
// Equal/near rounded coordinates do NOT authorize merging different vertex IDs.
struct Face {std::array<unsigned,3> vertices;FullFootprint::Face key;};
struct Limits {size_t vertices=256,faces=128,edges=384;unsigned operations=200000;};
enum class Status {Covered,BoundaryUncertain,WindingUncertain,HeightOrSlope,Invalid,Budget,Arithmetic};
struct HeightEvidence {FullFootprint::Face key;I residual;I slopeL1;};
struct Result {
    Status status=Status::Invalid;FullFootprint::Request request;
    FullFootprint::Poly footprint;
    std::vector<HeightEvidence> faces;
    double signedMinZ=0,signedMaxZ=0,radius=0;
    unsigned operations=0,boundaryEdges=0,cancelledEdges=0;
    int winding=0;
};
inline I Constant(Ops& op,FullFootprint::Q q){return op.Bound(double(q.n)/double(q.d),double(q.n)/double(q.d));}
inline I Neg(Ops& op,I a){return op.Sub(op.Point(0),a);}
inline I Abs(Ops& op,I a){return op.Bound(a.lo<=0&&a.hi>=0?0:std::min(std::abs(a.lo),std::abs(a.hi)),std::max(std::abs(a.lo),std::abs(a.hi)));}
inline I DivPositive(Ops& op,I n,I d){if(d.lo<=0)throw ConservativeTransform::Refused("unknown denominator");return op.Mul(n,op.Bound(1/d.hi,1/d.lo));}
inline I Side(Ops& op,const V& a,const V& b,const V& p){return ConservativeTransform::Edge(op,a,b,p[0],p[1]);}
inline bool Valid(I a){return std::isfinite(a.lo)&&std::isfinite(a.hi)&&a.lo<=a.hi;}
inline V Point(Ops& op,double x,double y){return {op.Point(x),op.Point(y),op.Point(0)};}
inline bool EdgeDisjoint(Ops& op,const V& a,const V& b,const std::vector<V>& polygon){
    // Separate the entire possible segment from the entire footprint. No endpoints-only hit test.
    for(size_t i=0;i<polygon.size();++i){
        const auto& x=polygon[i];const auto& y=polygon[(i+1)%polygon.size()];
        if(Side(op,x,y,a).hi<0&&Side(op,x,y,b).hi<0)return true;
    }
    bool positive=true,negative=true;
    for(const auto& p:polygon){const auto s=Side(op,a,b,p);positive=positive&&s.lo>0;negative=negative&&s.hi<0;}
    return positive||negative;
}
struct Edge {unsigned a=0,b=0,count=0;};
inline Result Cover(const FullFootprint::Request& request,const std::vector<Vertex>& vertices,const std::vector<Face>& faces,Limits limits={}){
    Result out;out.request=request;
    if(!ConservativeTransform::EnvironmentSupported()){out.status=Status::Arithmetic;return out;}
    Ops op(Precision::Binary64,limits.operations);
    try{
        ConservativeTransform::ScopedIEEE environment;
        if(vertices.size()>limits.vertices||faces.size()>limits.faces){out.status=Status::Budget;return out;}
        const auto seed=FullFootprint::Cover(request,{});
        if(seed.status!=FullFootprint::Status::Insufficient||seed.footprint.empty())return out;
        out.footprint=seed.footprint;out.radius=seed.radius;out.signedMinZ=seed.minZ;out.signedMaxZ=seed.maxZ;
        for(const auto& v:vertices)for(I x:v.position)if(!Valid(x))return out;
        std::vector<V> polygon;
        for(const auto& p:out.footprint)polygon.push_back({Constant(op,p.x),Constant(op,p.y),op.Point(0)});
        std::map<std::pair<unsigned,unsigned>,Edge> edges;
        const I rootX=Constant(op,request.root.x),rootY=Constant(op,request.root.y),rootZ=Constant(op,request.root.z);
        const double tolerance=double(request.heightTolerance.n)/double(request.heightTolerance.d);
        const double slopeMax=double(request.maxSlope.n)/double(request.maxSlope.d);
        const double safeTolerance=std::nextafter(tolerance,-std::numeric_limits<double>::infinity());
        const double safeSlope=std::nextafter(slopeMax,-std::numeric_limits<double>::infinity());
        for(size_t fi=0;fi<faces.size();++fi){
            const auto& f=faces[fi];op.Tick();
            if(!f.key.component||!f.key.shape||!f.key.geometryRevision){out.faces.clear();return out;}
            for(size_t j=0;j<fi;++j){op.Tick();if(f.key==faces[j].key){out.faces.clear();return out;}}
            for(unsigned i:f.vertices)if(i>=vertices.size()){out.faces.clear();return out;}
            if(f.vertices[0]==f.vertices[1]||f.vertices[1]==f.vertices[2]||f.vertices[0]==f.vertices[2]){out.faces.clear();return out;}
            const auto& a=vertices[f.vertices[0]].position;const auto& b=vertices[f.vertices[1]].position;const auto& c=vertices[f.vertices[2]].position;
            const auto normal=op.Cross(op.Sub(b,a),op.Sub(c,a));
            // Only positive projected triangles can contribute support. An uncertain
            // orientation never gets reversed or made upward to manufacture coverage.
            if(normal[2].lo<=0)continue;
            const I slope=DivPositive(op,op.Add(Abs(op,normal[0]),Abs(op,normal[1])),normal[2]);
            if(slope.hi>safeSlope)continue;
            I band{std::numeric_limits<double>::infinity(),-std::numeric_limits<double>::infinity()};
            for(unsigned index:f.vertices){const auto& p=vertices[index].position;
                const I z=op.Sub(p[2],op.Add(op.Add(op.Mul(rootX,p[0]),op.Mul(rootY,p[1])),rootZ));
                band.lo=std::min(band.lo,z.lo);band.hi=std::max(band.hi,z.hi);
            }
            if(band.lo < -safeTolerance||band.hi>safeTolerance)continue;
            out.faces.push_back({f.key,band,slope});
            for(int j=0;j<3;++j){op.Tick();const unsigned u=f.vertices[j],v=f.vertices[(j+1)%3];
                const auto key=std::minmax(u,v);auto i=edges.find(key);
                if(i==edges.end()){
                    if(edges.size()>=limits.edges){out.status=Status::Budget;out.faces.clear();out.operations=op.count;return out;}
                    edges.emplace(key,Edge{u,v,1});
                }else{
                    // Opposite directed incidences cancel symbolically, using the SAME
                    // uncertain vertex variables. No independent shrink/rounding seam.
                    if(i->second.count!=1||i->second.a!=v||i->second.b!=u)return Result{};
                    i->second.count=2;++out.cancelledEdges;
                }
            }
        }
        if(out.faces.empty()){out.status=Status::HeightOrSlope;out.operations=op.count;return out;}
        std::vector<Edge> boundary;
        for(const auto& pair:edges)if(pair.second.count==1)boundary.push_back(pair.second);
        out.boundaryEdges=static_cast<unsigned>(boundary.size());
        if(boundary.empty())return Result{}; // No invented closed all-up surface.
        for(const auto& e:boundary)if(!EdgeDisjoint(op,vertices[e.a].position,vertices[e.b].position,polygon)){
            out.status=Status::BoundaryUncertain;out.faces.clear();out.operations=op.count;return out;
        }
        const double x=(double(request.from.x.n)/request.from.x.d+double(request.to.x.n)/request.to.x.d)*.5;
        const double y=(double(request.from.y.n)/request.from.y.d+double(request.to.y.n)/request.to.y.d)*.5;
        // A single seed establishes winding only AFTER proving no uncancelled
        // boundary can meet ANY point of the connected footprint.
        for(double dy:{0.,.125,-.125,.375,-.375,.625,-.625,1.125,-1.125}){
            const V p=Point(op,x,y+dy);bool interior=true;
            for(size_t j=0;j<polygon.size();++j)if(Side(op,polygon[j],polygon[(j+1)%polygon.size()],p).lo<=0)interior=false;
            if(!interior)continue;
            int winding=0;bool certain=true;
            for(const auto& e:boundary){const auto& a=vertices[e.a].position;const auto& b=vertices[e.b].position;
                const bool aBelow=a[1].hi<p[1].lo,bBelow=b[1].hi<p[1].lo;
                const bool aAbove=a[1].lo>p[1].hi,bAbove=b[1].lo>p[1].hi;
                if((aBelow&&bBelow)||(aAbove&&bAbove))continue;
                if(!((aBelow&&bAbove)||(aAbove&&bBelow))){certain=false;break;}
                const auto side=Side(op,a,b,p);
                if(side.lo<=0&&side.hi>=0){certain=false;break;}
                if(aBelow&&bAbove&&side.lo>0)++winding;
                if(aAbove&&bBelow&&side.hi<0)--winding;
            }
            if(certain&&winding>0){out.winding=winding;out.status=Status::Covered;out.operations=op.count;return out;}
        }
        out.status=Status::WindingUncertain;
    }catch(const ConservativeTransform::Refused&){out.status=op.count>limits.operations?Status::Budget:Status::Arithmetic;}
    catch(const FullFootprint::Arithmetic&){out.status=Status::Arithmetic;}
    catch(const std::bad_alloc&){out.status=Status::Budget;}
    out.faces.clear();out.operations=op.count;return out;
}
}
