#pragma once
#include <cmath>

namespace MikdashOnline::RuntimeCandidate03 {
// Actual production guard used by the UE owner loop. Inputs are raw QPC seconds.
// Observations never renew lifetime or the last successful frame-service time.
class ExpiryWatch final {
    double Deadline=0, LastObservation=0, LastFrame=0;
    bool Started=false, Revoked=false;
    static bool Number(double N) { return std::isfinite(N)&&N>=0&&N<=1099511627776.0; }
public:
    bool Begin(double Now,double Bound,double OwnerExpiry) {
        if(Started||Revoked) { Revoke(); return false; }
        Started=true;
        if(!Number(Now)||!Number(Bound)||!Number(OwnerExpiry)||Bound<=Now||
           Bound>OwnerExpiry||Bound-Now>86400) { Revoke(); return false; }
        Deadline=Bound; LastObservation=LastFrame=Now; return true;
    }
    bool Observe(double Now) {
        if(!Started||Revoked) return false;
        if(!Number(Now)||Now<LastObservation||Now>=Deadline||Now-LastFrame>0.5) {
            Revoke(); return false;
        }
        LastObservation=Now; return true;
    }
    bool CompleteFrame(double Now) {
        if(!Observe(Now)) return false;
        LastFrame=Now; return true;
    }
    void Revoke() { Revoked=true; }
};
}
