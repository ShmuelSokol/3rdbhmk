#include "StrictABI.h" // Exactly the POD header available to the actual Chaos caller.
#include <xmmintrin.h>
#include <cstring>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <memory>
using namespace MeasuredStrict;
int checks=0,failed=0;
void Check(bool b){++checks;if(!b){++failed;std::cerr<<"failed ABI check "<<checks<<'\n';}}
Request RequestAt(int profile=1){Request r{};r.acquisition=r.world=r.geometry=r.binding=1;r.profile=profile;
 for(auto& x:r.from)x={0,1};r.to[0]={20,1};r.to[1]={0,1};for(auto& x:r.root)x={0,1};
 r.maxSlope={1,2};r.heightTolerance={1,100};r.contactBelowRoot={1,2};return r;}
void Point(Snapshot& s,unsigned i,float x,float y,float z){float values[3]{x,y,z};
 s.vertex[i].originalParticle=i;for(int j=0;j<3;++j)std::memcpy(&s.vertex[i].xyzBits[j],&values[j],4);}
void Floor(Snapshot& s,const Request& r){s={};s.acquisition=s.world=s.geometry=s.binding=1;s.vertices=4;s.faces=2;s.shapes=1;
 auto& shape=s.shape[0];shape.component=7;shape.instance=3;shape.ordinal=1;shape.vertices=4;shape.faces=2;shape.depth=1;
 shape.outerToInner[0]={{1,1,1},{r.origin[0],r.origin[1],r.origin[2]},{0,0,0,1}};
 Point(s,0,-200,-200,0);Point(s,1,200,-200,0);Point(s,2,200,200,0);Point(s,3,-200,200,0);
 s.face[0]={{0,1,2},10,0,1000};s.face[1]={{0,2,3},11,0,1001};Check(MeasuredStrictMakeQuery(&r,&s.capturedQuery));}
void AddTriangle(Snapshot& s,float x,float z,bool vertical){
 Point(s,4,x,-5,z);Point(s,5,x+10,5,z);Point(s,6,x,5,vertical?z+10:z);
 s.face[2]={{4,5,6},12,0,1002};s.vertices=7;s.faces=3;s.shape[0].vertices=7;s.shape[0].faces=3;}
int main(){
 auto s=std::make_unique<Snapshot>();Evidence e{};auto r=RequestAt();
 Floor(*s,r);Check(MeasuredStrictCover(s.get(),&r,&e));Check(e.status==Status::SurfaceClear&&e.contactFaces==2);
 Check(e.queryEnclosed&&e.surfaceClassificationComplete&&!e.obstaclesComplete&&!e.worldComplete);
 Check(e.signedMinZ<0&&e.query.min[2]<=e.signedMinZ&&e.query.max[2]>=e.signedMaxZ);
 uint32_t lower[3],upper[3];float l[3]{-200,-200,0},u[3]{200,200,0};
 for(int j=0;j<3;++j){std::memcpy(&lower[j],&l[j],4);std::memcpy(&upper[j],&u[j],4);}
 Check(MeasuredStrictCullBounds(&s->shape[0],lower,upper,&s->capturedQuery)==Cull::Keep);
 s->shape[0].outerToInner[0].translation[0]=10000;
 Check(MeasuredStrictCullBounds(&s->shape[0],lower,upper,&s->capturedQuery)==Cull::Disjoint);
 Check(MeasuredStrictCullTriangle(&s->shape[0],s->vertex,&s->capturedQuery)==Cull::Disjoint);
 s->shape[0].outerToInner[0].translation[0]=0;
 Check(MeasuredStrictCullTriangle(&s->shape[0],s->vertex,&s->capturedQuery)==Cull::Keep);
 s->capturedQuery.min[0]+=1;Check(!MeasuredStrictCover(s.get(),&r,&e));Check(e.status==Status::Refused&&!e.queryEnclosed);
 Floor(*s,r);AddTriangle(*s,-5,0,true);Check(MeasuredStrictCover(s.get(),&r,&e));
 Check(e.status==Status::PotentialObstacle&&e.contactFaces==2&&e.potentialFaces==1);
 Check(e.faceClass[2]==FaceClass::PotentialObstacle); // SAME component/instance/shape as floor.
 Floor(*s,r);AddTriangle(*s,300,0,true);Check(MeasuredStrictCover(s.get(),&r,&e));
 Check(e.status==Status::SurfaceClear&&e.separatedFaces==1);
 Floor(*s,r);AddTriangle(*s,-5,200,false);Check(MeasuredStrictCover(s.get(),&r,&e));Check(e.separatedFaces==1);
 r.contactBelowRoot={0,1};Floor(*s,r);Check(MeasuredStrictCover(s.get(),&r,&e));Check(e.status==Status::PotentialObstacle);
 r=RequestAt();r.root[0]={1,8};Floor(*s,r);
 Point(*s,0,-200,-200,-25);Point(*s,1,200,-200,25);Point(*s,2,200,200,25);Point(*s,3,-200,200,-25);
 Check(MeasuredStrictCover(s.get(),&r,&e));Check(e.status==Status::PotentialObstacle); // Tilt does not exempt high contacts.
 r=RequestAt();r.acquisition=0;Query q{};Check(!MeasuredStrictMakeQuery(&r,&q));
 r=RequestAt();r.to[0]={101,1};Check(!MeasuredStrictMakeQuery(&r,&q));
 const unsigned saved=_mm_getcsr(),base=(saved&~0x8040u);
 for(unsigned mode:{0u,0x8000u,0x40u,0x8040u}){
  r=RequestAt();r.origin[0]=10000.1;r.origin[1]=-43000.96;r.origin[2]=.5;
  _mm_setcsr(base|mode);Floor(*s,r);
  auto& t=s->shape[0].outerToInner[0];for(double& scale:t.scale)scale=double(float(.96));
  t.quaternion[2]=.3826834323650898;t.quaternion[3]=.9238795325112867;
  const unsigned state=_mm_getcsr();
  Check(MeasuredStrictCullBounds(&s->shape[0],lower,upper,&s->capturedQuery)==Cull::Keep);
  Check(_mm_getcsr()==state);
  Check(MeasuredStrictCover(s.get(),&r,&e));Check(_mm_getcsr()==state);Check(e.status==Status::SurfaceClear);
 }
 _mm_setcsr(saved);
 std::ofstream csv("query-enclosure.csv");csv<<std::setprecision(17);
 for(int profile=0;profile<6;++profile){r=RequestAt(profile);r.from[0]={1,10};r.to[0]={201,10};
  r.origin[0]=10000.1;r.origin[1]=-43000.96;r.origin[2]=.5;Floor(*s,r);
  Check(MeasuredStrictCover(s.get(),&r,&e));Check(e.status==Status::SurfaceClear);
  csv<<profile<<','<<e.radius<<','<<e.signedMinZ<<','<<e.signedMaxZ;
  for(int j=0;j<3;++j)csv<<','<<e.query.min[j]<<','<<e.query.max[j];csv<<'\n';
 }
 std::cout<<checks<<" actual ABI path checks "<<failed<<" failures\n";return failed?1:0;
}
