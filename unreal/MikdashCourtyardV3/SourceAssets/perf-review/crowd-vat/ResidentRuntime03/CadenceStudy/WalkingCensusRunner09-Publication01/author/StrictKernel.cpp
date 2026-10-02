#include "StrictABI.h"
#include "SharedEdgeCoverage.h"
#include <cstring>
#include <type_traits>
#include "QueryContact.h"
#if !defined(_MSC_VER) || !defined(_M_X64) || defined(__clang__)
#error This build closure requires reviewed MSVC x64 strict compilation.
#endif
static_assert(std::is_trivially_copyable_v<MeasuredStrict::Snapshot>);
extern "C" __declspec(noinline) bool MeasuredStrictCover(const MeasuredStrict::Snapshot* s,
 const MeasuredStrict::Request* r,MeasuredStrict::Evidence* output) noexcept {
 using namespace MeasuredStrict;using namespace ConservativeTransform;
 if(!output)return false;*output={};
 if(!s||!r)return false;
 try {
  ScopedIEEE environment;
  if(!s->acquisition||s->acquisition!=r->acquisition||!s->world||s->world!=r->world||
    !s->geometry||s->geometry!=r->geometry||!s->binding||s->binding!=r->binding||
    !s->shapes||s->shapes>MaxShapes||s->vertices>MaxVertices||s->faces>MaxFaces)return false;
  const auto request=QueryContact::Decode(*r);
  const auto envelope=QueryContact::Build(*r,request);
  if(!QueryContact::Same(envelope.query,s->capturedQuery))return false;
  std::vector<SharedSupport::Vertex> vertices;std::vector<SharedSupport::Face> faces;
  unsigned nextVertex=0,nextFace=0;
  for(unsigned shapeIndex=0;shapeIndex<s->shapes;++shapeIndex){const auto& shape=s->shape[shapeIndex];
   if(!shape.component||!shape.ordinal||!shape.depth||shape.depth>MaxDepth||
      shape.firstVertex!=nextVertex||shape.firstFace!=nextFace||
      shape.vertices>s->vertices-nextVertex||shape.faces>s->faces-nextFace)return false;
   ConservativeTransform::Transform transforms[MaxDepth];
   for(unsigned k=0;k<shape.depth;++k){const auto& t=shape.outerToInner[shape.depth-1-k];
    for(unsigned j=0;j<3;++j){if(!std::isfinite(t.scale[j])||t.scale[j]<=0)return false;
      transforms[k].scale[j]=t.scale[j];transforms[k].translation[j]=t.translation[j];}
    for(unsigned j=0;j<4;++j)transforms[k].quaternion[j]=t.quaternion[j];
   }
   for(unsigned i=0;i<shape.vertices;++i){
    for(unsigned j=0;j<i;++j)if(s->vertex[nextVertex+i].originalParticle==s->vertex[nextVertex+j].originalParticle)return false;
    std::array<double,3> point;
    for(unsigned j=0;j<3;++j){float x;std::memcpy(&x,&s->vertex[nextVertex+i].xyzBits[j],4);point[j]=double(x);}
    Ops op(Precision::Binary64);auto v=Chain(op,point,transforms,shape.depth,{r->origin[0],r->origin[1],r->origin[2]});
    vertices.push_back({v});
   }
   for(unsigned i=0;i<shape.faces;++i){const auto& f=s->face[nextFace+i];
    if(f.shape!=shapeIndex||f.external<0)return false;
    for(unsigned j=0;j<3;++j)if(f.index[j]<nextVertex||f.index[j]>=nextVertex+shape.vertices)return false;
    faces.push_back({{f.index[0],f.index[1],f.index[2]},
      {shape.component,shape.instance,shape.ordinal,s->geometry,f.internal}});
   }
   nextVertex+=shape.vertices;nextFace+=shape.faces;
  }
  if(nextVertex!=s->vertices||nextFace!=s->faces)return false;
  auto covered=SharedSupport::Cover(request,vertices,faces);
  if(covered.status!=SharedSupport::Status::Covered)return false;
  Evidence result{};result.status=Status::SupportCovered;result.vertices=s->vertices;result.faces=s->faces;
  result.radius=covered.radius;result.signedMinZ=covered.signedMinZ;result.signedMaxZ=covered.signedMaxZ;
  for(unsigned i=0;i<s->vertices;++i)for(unsigned j=0;j<3;++j)result.vertex[i][j]={vertices[i].position[j].lo,vertices[i].position[j].hi};
  for(unsigned i=0;i<s->faces;++i)for(const auto& f:covered.faces)if(f.key==faces[i].key)result.supportFace[i]=1;
  result.query=envelope.query;result.queryEnclosed=1;
  Ops classification(Precision::Binary64,200000);
  for(unsigned i=0;i<s->faces;++i){const auto& face=s->face[i];
   Triangle triangle{vertices[face.index[0]].position,vertices[face.index[1]].position,vertices[face.index[2]].position};
   if(QueryContact::Separated(classification,triangle,envelope)){
    result.faceClass[i]=FaceClass::Separated;++result.separatedFaces;
   }else if(QueryContact::Contact(triangle,envelope,result.signedMinZ,result.supportFace[i]!=0)){
    result.faceClass[i]=FaceClass::SupportContact;++result.contactFaces;
   }else{result.faceClass[i]=FaceClass::PotentialObstacle;++result.potentialFaces;}
  }
  result.surfaceClassificationComplete=1;
  result.status=result.potentialFaces?Status::PotentialObstacle:Status::SurfaceClear;
  // Surface classification alone cannot establish solid containment or world completeness.
  *output=result;return true;
 }catch(...){return false;} // No C++ exceptions cross the POD ABI boundary.
}

extern "C" __declspec(noinline) bool MeasuredStrictMakeQuery(const MeasuredStrict::Request* r,
 MeasuredStrict::Query* output) noexcept {
 if(!output)return false;*output={};if(!r)return false;
 try{ConservativeTransform::ScopedIEEE environment;*output=QueryContact::Build(*r,QueryContact::Decode(*r)).query;return true;}
 catch(...){return false;}
}

namespace {
ConservativeTransform::V ToWorld(ConservativeTransform::Ops& op,ConservativeTransform::V point,const MeasuredStrict::Shape& shape){
 if(!shape.depth||shape.depth>MeasuredStrict::MaxDepth)throw ConservativeTransform::Refused("depth");
 for(unsigned k=shape.depth;k-->0;){const auto& raw=shape.outerToInner[k];ConservativeTransform::Transform t;
  for(int j=0;j<3;++j){if(!std::isfinite(raw.scale[j])||raw.scale[j]<=0)throw ConservativeTransform::Refused("scale");
   t.scale[j]=raw.scale[j];t.translation[j]=raw.translation[j];}
  for(int j=0;j<4;++j)t.quaternion[j]=raw.quaternion[j];point=ConservativeTransform::Apply(op,point,t);
 }return point;
}
double DecodeFloat(uint32_t bits){float x;std::memcpy(&x,&bits,4);return double(x);}
bool Outside(const ConservativeTransform::V& bounds,const MeasuredStrict::Query& query){
 for(int j=0;j<3;++j){if(!std::isfinite(query.min[j])||!std::isfinite(query.max[j])||query.min[j]>query.max[j])
   throw ConservativeTransform::Refused("query");}
 for(int j=0;j<3;++j)if(bounds[j].hi<query.min[j]||bounds[j].lo>query.max[j])return true;
 return false;
}
}
extern "C" __declspec(noinline) MeasuredStrict::Cull MeasuredStrictCullBounds(const MeasuredStrict::Shape* s,
 const uint32_t* lo,const uint32_t* hi,const MeasuredStrict::Query* q) noexcept {
 using namespace ConservativeTransform;using MeasuredStrict::Cull;
 if(!s||!lo||!hi||!q)return Cull::Refused;
 try{ScopedIEEE environment;Ops op(Precision::Binary64,20000);V box{};
  for(int j=0;j<3;++j)box[j]=op.Bound(DecodeFloat(lo[j]),DecodeFloat(hi[j]));
  return Outside(ToWorld(op,box,*s),*q)?Cull::Disjoint:Cull::Keep;
 }catch(...){return Cull::Refused;}
}
extern "C" __declspec(noinline) MeasuredStrict::Cull MeasuredStrictCullTriangle(const MeasuredStrict::Shape* s,
 const MeasuredStrict::Vertex* points,const MeasuredStrict::Query* q) noexcept {
 using namespace ConservativeTransform;using MeasuredStrict::Cull;
 if(!s||!points||!q)return Cull::Refused;
 try{ScopedIEEE environment;Ops op(Precision::Binary64,20000);V box{};
  for(int i=0;i<3;++i){V point{};for(int j=0;j<3;++j)point[j]=op.Point(DecodeFloat(points[i].xyzBits[j]));
   point=ToWorld(op,point,*s);
   for(int j=0;j<3;++j){if(i==0)box[j]=point[j];else{box[j].lo=std::min(box[j].lo,point[j].lo);box[j].hi=std::max(box[j].hi,point[j].hi);}}
  }
  return Outside(box,*q)?Cull::Disjoint:Cull::Keep;
 }catch(...){return Cull::Refused;}
}
