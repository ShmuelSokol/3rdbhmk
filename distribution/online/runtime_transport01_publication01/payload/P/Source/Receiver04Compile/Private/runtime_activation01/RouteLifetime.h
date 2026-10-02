#pragma once
#include <cmath>
#include <string>
namespace MikdashOnline::Activation01 {
// Actual production route state. Startup bound is distinct from original lease;
// authenticated open never changes either timestamp. No caller-provided auth bit.
class RouteLifetime final {
    double Startup=0,Lease=0,Last=-1;
    std::string ProcessGeneration,Connection;
    bool Begun=false,Opened=false,Closed=false;
    bool Fresh(double N) {
        if(!std::isfinite(N)||N<0||N<Last||N>=Lease||(!Opened&&N>=Startup)){Abort();return false;}
        Last=N;return true;
    }
public:
    bool Begin(double N,double StartEnd,double LeaseEnd,double OwnerEnd,const std::string& G) {
        if(Begun||Closed)return false;Begun=true;
        if(!std::isfinite(StartEnd)||!std::isfinite(LeaseEnd)||!std::isfinite(OwnerEnd)||
           StartEnd<0||StartEnd>LeaseEnd||LeaseEnd>OwnerEnd||OwnerEnd>1099511627776.0||G.size()!=32){Abort();return false;}
        for(char C:G)if(!((C>='0'&&C<='9')||(C>='a'&&C<='f'))){Abort();return false;}
        Startup=StartEnd;Lease=LeaseEnd;ProcessGeneration=G;return Fresh(N);
    }
    bool Live(double N){return Begun&&!Closed&&Fresh(N);}
    bool Open(double N,const std::string& G) {
        if(!Live(N)||Opened||G!=ProcessGeneration)return false;Opened=true;return true;
    }
    bool Bind(double N,const std::string& G,const std::string& C) {
        if(!Live(N)||!Opened||G!=ProcessGeneration||!Connection.empty()||C.empty()||C.size()>128)return false;
        Connection=C;return true;
    }
    bool Input(double N,const std::string& G,const std::string& C) {
        return Live(N)&&Opened&&G==ProcessGeneration&&!Connection.empty()&&C==Connection;
    }
    bool Release(double N,const std::string& G,const std::string& C) {
        if(!Live(N)||!Opened||G!=ProcessGeneration||(!Connection.empty()&&C!=Connection))return false;
        Connection.clear();return true;
    }
    bool IsOpened()const{return Opened&&!Closed;}
    void Abort(){Closed=true;Connection.clear();}
};
// Browser Controls.look emits CSS pixel deltas /100. This explicit source policy
// is explicit: 0.3 degree per CSS pixel, 30 degrees per normalized unit. It is not
// inherited from local MouseX/legacy yaw scales, and UX acceptance is outstanding.
inline constexpr double LookDegreesPerNormalizedUnit=30.0;
}
