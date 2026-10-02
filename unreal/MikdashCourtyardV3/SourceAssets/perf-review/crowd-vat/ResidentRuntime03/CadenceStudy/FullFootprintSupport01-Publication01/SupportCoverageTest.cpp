#include "SupportCoverage.h"
#include <iostream>
using namespace FullFootprint;
int checks=0,failures=0;
void Check(bool yes,const char* label){++checks;if(!yes){++failures;std::cerr<<"FAIL "<<label<<'\n';}}
Face F(uint64_t face,uint64_t component=1){return {component,0,1,1,face};}
Patch Rect(int x0,int y0,int x1,int y1,uint64_t face=0,uint64_t comp=1,Plane p={}){
    return Rectangle(F(face,comp),Q(x0),Q(y0),Q(x1),Q(y1),p);
}
bool Covered(const Request& r,const std::vector<Patch>& p){return Cover(r,p).status==Status::Covered;}
int main(){
    Request r;auto floor=Rect(-200,-200,300,200);
    auto c=Cover(r,{floor});Check(c.status==Status::Covered,"single rectangle");
    Check(c.minZ==MeasuredBodyStudy::Profiles[1].MinZ&&c.minZ<0,"signed minZ unchanged");
    Check(c.radius==MeasuredBodyStudy::Profiles[1].Radius,"actual measured radius");
    Check(SupportPointCandidate(c,1,1,1,F(0),{},Q(0)),"exact floor point allowed");
    Check(!SupportPointCandidate(c,2,1,1,F(0),{},Q(0)),"world invalidation");
    Check(!SupportPointCandidate(c,1,2,1,F(0),{},Q(0)),"geometry invalidation");
    Check(!SupportPointCandidate(c,1,1,2,F(0),{},Q(0)),"binding invalidation");
    Check(!SupportPointCandidate(c,1,1,1,F(1),{},Q(0)),"same component different face stays obstacle");
    Check(!SupportPointCandidate(c,1,1,1,F(0,2),{},Q(0)),"different component stays obstacle");
    Check(!SupportPointCandidate(c,1,1,1,F(0),{},Q(1)),"same face off surface stays obstacle");
    Check(!SupportPointCandidate(c,1,1,1,F(0),{Q(150),Q(0)},Q(0)),"outside footprint not certified");
    auto limited=r;limited.contactBelowRoot=Q(1,10);auto lc=Cover(limited,{floor});
    Check(lc.status==Status::Covered&&!SupportPointCandidate(lc,1,1,1,F(0),{},Q(0)),"coverage does not waive signed lower-bound policy");
    auto a=Triangle(F(1),{Q(-200),Q(-200)},Q(0),{Q(200),Q(-200)},Q(0),{Q(200),Q(200)},Q(0));
    auto b=Triangle(F(2,2),{Q(-200),Q(-200)},Q(0),{Q(200),Q(200)},Q(0),{Q(-200),Q(200)},Q(0));
    auto triangles=Cover(r,{a,b});Check(triangles.status==Status::Covered&&triangles.supportFaces.size()==2,"multi triangle component union exact seam");
    Check(SupportPointCandidate(triangles,1,1,1,F(2,2),{Q(-20),Q(20)},Q(0)),"second component contact");
    std::vector<Patch> hole{Rect(-200,-200,-1,200,1),Rect(1,-200,200,200,2),Rect(-1,-200,1,-1,3),Rect(-1,1,1,200,4)};
    Check(!Covered(r,hole),"interior hole despite all footprint vertices covered");
    auto duplicateArea=hole;duplicateArea.push_back(Rect(-200,-200,-1,200,5));
    Check(!Covered(r,duplicateArea),"overlapping area cannot fill hole");
    auto tiny=std::vector<Patch>{Rectangle(F(1),Q(-200),Q(-200),Q(-1,1000000),Q(200)),Rectangle(F(2),Q(1,1000000),Q(-200),Q(200),Q(200))};
    auto tc=Cover(r,tiny);Check(tc.status==Status::Insufficient||tc.status==Status::ArithmeticRange,"tiny gap never rounded closed");
    Check(!Covered(r,{Rect(-58,-200,200,200)}),"less than actual radius refused");
    Check(!Covered(r,{Rect(-59,-59,58,59)}),"circumscribed corner coverage required");
    r.to={Q(100),Q(0)};
    Check(Covered(r,{floor}),"full swept body footprint");
    auto swept=Cover(r,{floor});
    Check(!SupportPointCandidate(swept,1,1,1,F(0),{Q(120),Q(0)},Q(0),Q(0)),"future endpoint is not present support contact");
    Check(SupportPointCandidate(swept,1,1,1,F(0),{Q(120),Q(0)},Q(0),Q(1)),"contact witness at correct root time");
    Check(!SupportPointCandidate(swept,1,1,1,F(0),{},Q(0),Q(2)),"out of interval contact time");
    Check(!Covered(r,{Rect(-60,-100,60,100,1),Rect(90,-100,200,100,2)}),"endpoint coverage insufficient between endpoints");
    Check(Covered(r,{Rect(-60,-60,50,60,1),Rect(50,-60,160,60,2,2)}),"swept multiple rectangles shared boundary");
    r.to={Q(70),Q(70)};Check(Covered(r,{floor}),"diagonal sweep");
    r={};r.root={Q(1,10),Q(0),Q(0)};
    auto slope=Rect(-200,-200,200,200,1,1,r.root);
    Check(Covered(r,{slope}),"tilted matching affine root surface");
    auto tilted=Cover(r,{slope});
    Check(!SupportPointCandidate(tilted,1,1,1,F(1),{Q(40),Q(0)},Q(4)),"uphill surface above root is not exempted as contact");
    auto tiltTri=Triangle(F(2),{Q(-200),Q(-200)},Q(-20),{Q(200),Q(-200)},Q(20),{Q(200),Q(200)},Q(20));
    auto tiltTri2=Triangle(F(3),{Q(-200),Q(-200)},Q(-20),{Q(200),Q(200)},Q(20),{Q(-200),Q(200)},Q(-20));
    Check(Covered(r,{tiltTri,tiltTri2}),"tilted triangles union");
    r.root={};Check(!Covered(r,{slope}),"height mismatch throughout footprint");
    auto steep=r;steep.root={Q(1),Q(0),Q(0)};
    Check(Cover(steep,{floor}).status==Status::InvalidInput,"steep requested root refused");
    auto riser=Rect(-200,-200,200,200,9,1,{Q(0),Q(0),Q(20)});
    Check(!Covered(r,{riser}),"raised tread not floor at root");
    auto withRiser=Cover(r,{floor,riser});
    Check(withRiser.status==Status::Covered&&!SupportPointCandidate(withRiser,1,1,1,F(9),{},Q(20)),"floor support never ignores same-component riser");
    bool vertical=false;try{Triangle(F(7),{Q(0),Q(0)},Q(0),{Q(0),Q(0)},Q(20),{Q(0),Q(10)},Q(20));}catch(const Invalid&){vertical=true;}
    Check(vertical,"vertical riser cannot be support height graph");
    Check(Cover(r,{}).status==Status::Insufficient,"no patches");
    Check(Cover(r,{floor,floor}).status==Status::InvalidInput,"duplicate identity even after coverage refused");
    auto reverse=floor;std::reverse(reverse.xy.begin(),reverse.xy.end());
    Check(Cover(r,{reverse}).status==Status::InvalidInput,"clockwise malformed patch");
    auto degenerate=floor;degenerate.xy[1]=degenerate.xy[0];
    Check(Cover(r,{degenerate}).status==Status::InvalidInput,"zero edge malformed patch");
    Limits lim;lim.patches=0;Check(Cover(r,{floor},lim).status==Status::Budget,"patch budget");
    lim={};lim.operations=0;Check(Cover(r,{floor},lim).status==Status::Budget,"operation budget");
    lim={};lim.vertices=3;Check(Cover(r,{floor},lim).status==Status::Budget,"vertex budget");
    lim={};lim.fragments=1;Check(Cover(r,{Rect(-1,-1,1,1)},lim).status==Status::Budget,"fragment budget");
    auto far=r;far.from={Q(1000000000),Q(0)};far.to=far.from;
    Check(Cover(far,{floor}).status==Status::ArithmeticRange,"bounded exact arithmetic refuses overflow");
    auto invalid=r;invalid.profile=6;Check(Cover(invalid,{floor}).status==Status::InvalidInput,"unknown measured profile");
    invalid=r;invalid.geometryVersion=0;Check(Cover(invalid,{floor}).status==Status::InvalidInput,"unknown geometry version");
    invalid=r;invalid.to={Q(101),Q(0)};Check(Cover(invalid,{floor}).status==Status::InvalidInput,"existing 100cm bound unchanged");
    for(int profile=0;profile<6;++profile){r={};r.profile=profile;auto m=Cover(r,{floor});
        Check(m.status==Status::Covered,"all actual measured profiles");
        Check(m.minZ==MeasuredBodyStudy::Profiles[profile].MinZ&&m.maxZ==MeasuredBodyStudy::Profiles[profile].MaxZ,"signed measured vertical interval exact");
        auto half=static_cast<int>(std::ceil(m.radius));
        Check(Covered(r,{Rect(-half,-half,half,half)}),"outward square exact boundary");
        Check(!Covered(r,{Rect(-half+1,-half,half,half)}),"missing strip at each scale");
    }
    // Translation, patch order and overlapping subdivisions: deterministic exact replay.
    for(int offset=-20;offset<=20;++offset){r={};r.from={Q(offset),Q(offset)};r.to={Q(offset+30),Q(offset+20)};
        std::vector<Patch> split{Rect(offset-70,offset-70,offset+10,offset+90,1),Rect(offset+10,offset-70,offset+100,offset+90,2,2)};
        Check(Covered(r,split),"translated split coverage");std::reverse(split.begin(),split.end());Check(Covered(r,split),"patch order invariance");
        split[0].xy[0].x=Q(offset+11);split[0].xy[3].x=Q(offset+11);
        Check(!Covered(r,split),"translated one centimetre slit");
    }
    std::cout<<"FullFootprintSupport01 checks="<<checks<<" failures="<<failures<<" scope=exact-explicit-static-patches; no UE/world equivalence\n";
    return failures?1:0;
}
