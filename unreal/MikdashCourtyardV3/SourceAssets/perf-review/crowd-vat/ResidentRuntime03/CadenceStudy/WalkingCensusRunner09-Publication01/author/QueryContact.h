#pragma once
// Private to StrictKernel.cpp. Never compiled inline into the Chaos module.
namespace QueryContact {
using namespace ConservativeTransform;
inline FullFootprint::Request Decode(const MeasuredStrict::Request& r){
 auto q=[](MeasuredStrict::Q x){return FullFootprint::Q(x.n,x.d);};
 FullFootprint::Request out;out.serial=r.acquisition;out.worldVersion=r.world;
 out.geometryVersion=r.geometry;out.bindingVersion=r.binding;out.profile=r.profile;
 out.from={q(r.from[0]),q(r.from[1])};out.to={q(r.to[0]),q(r.to[1])};
 out.root={q(r.root[0]),q(r.root[1]),q(r.root[2])};out.maxSlope=q(r.maxSlope);
 out.heightTolerance=q(r.heightTolerance);out.contactBelowRoot=q(r.contactBelowRoot);return out;
}
struct Envelope {
 MeasuredStrict::Query query{};std::vector<V> polygon;
 I bodyLower,bodyUpper;double contactLow,contactHigh,contactBelow;
};
inline Envelope Build(const MeasuredStrict::Request& raw,const FullFootprint::Request& request){
 ScopedIEEE environment;Ops op(Precision::Binary64,200000);
 const auto seed=FullFootprint::Cover(request,{});
 if(seed.status!=FullFootprint::Status::Insufficient||seed.footprint.empty())throw Refused("invalid swept request");
 Envelope e;auto minX=seed.footprint[0].x,maxX=minX,minY=seed.footprint[0].y,maxY=minY;
 for(auto p:seed.footprint){
  if(p.x<minX)minX=p.x;if(maxX<p.x)maxX=p.x;if(p.y<minY)minY=p.y;if(maxY<p.y)maxY=p.y;
  e.polygon.push_back({SharedSupport::Constant(op,p.x),SharedSupport::Constant(op,p.y),op.Point(0)});
 }
 auto a=request.root.At(request.from),b=request.root.At(request.to);
 const auto rootMin=SharedSupport::Constant(op,b<a?b:a),rootMax=SharedSupport::Constant(op,a<b?b:a);
 const auto tolerance=SharedSupport::Constant(op,request.heightTolerance);
 e.bodyLower=op.Add(rootMin,op.Point(seed.minZ));e.bodyUpper=op.Add(rootMax,op.Point(seed.maxZ));
 // Intersection, NOT union, of all root-height contact bands along the move.
 // Entire eligible face must fit this slab, so no point/time contact is skipped.
 e.contactLow=op.Sub(rootMax,tolerance).hi;e.contactHigh=op.Add(rootMin,tolerance).lo;
 e.contactBelow=SharedSupport::Constant(op,request.contactBelowRoot).lo;
 const double lo[3]={SharedSupport::Constant(op,minX).lo,SharedSupport::Constant(op,minY).lo,
   std::min(e.bodyLower.lo,op.Sub(rootMin,tolerance).lo)};
 const double hi[3]={SharedSupport::Constant(op,maxX).hi,SharedSupport::Constant(op,maxY).hi,
   std::max(e.bodyUpper.hi,op.Add(rootMax,tolerance).hi)};
 for(int j=0;j<3;++j){const auto world=op.Add(I{lo[j],hi[j]},op.Point(raw.origin[j]));
  e.query.min[j]=world.lo;e.query.max[j]=world.hi;}
 return e;
}
inline bool Same(const MeasuredStrict::Query& a,const MeasuredStrict::Query& b){
 // Captured query must be this request's exact outward result, not a guessed box.
 return std::memcmp(&a,&b,sizeof(a))==0;
}
inline bool Separated(Ops& op,const Triangle& triangle,const Envelope& e){
 bool below=true,above=true;
 for(const auto& v:triangle){below=below&&v[2].hi<e.bodyLower.lo;above=above&&v[2].lo>e.bodyUpper.hi;}
 if(below||above)return true;
 for(size_t i=0;i<e.polygon.size();++i){bool outside=true;
  for(const auto& v:triangle)outside=outside&&Edge(op,e.polygon[i],e.polygon[(i+1)%e.polygon.size()],v[0],v[1]).hi<0;
  if(outside)return true;
 }
 return false; // Unknown intersection, never a fabricated penetration finding.
}
inline bool Contact(const Triangle& triangle,const Envelope& e,double signedMinZ,bool certifiedFace){
 if(!certifiedFace||signedMinZ < -e.contactBelow||e.contactLow>e.contactHigh)return false;
 for(const auto& v:triangle)if(v[2].lo<e.contactLow||v[2].hi>e.contactHigh)return false;
 return true; // All barycentric points of THIS face, for all move times, fit policy.
}
}
