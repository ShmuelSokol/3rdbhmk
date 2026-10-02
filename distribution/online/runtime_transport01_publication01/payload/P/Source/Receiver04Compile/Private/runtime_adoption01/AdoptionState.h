#pragma once
#include <cmath>
namespace MikdashOnline::Adoption01 {
// Production one-shot sequencing used by Bootstrap, no UE types or adapters.
class AdoptionState final {
public: enum class Phase { Empty, Adopting, Stopped, Closed };
private:
    Phase State=Phase::Empty;double Until=0,Last=-1;
    bool Fresh(double N) {
        if(!std::isfinite(N)||N<0||N>1099511627776.0||N<Last||N>=Until){Abort();return false;}
        Last=N;return true;
    }
public:
    bool Begin(double N,double Deadline,double OwnerExpiry) {
        if(State!=Phase::Empty)return false;
        if(!std::isfinite(Deadline)||!std::isfinite(OwnerExpiry)||Deadline<0||
           Deadline>OwnerExpiry||OwnerExpiry>1099511627776.0){Abort();return false;}
        Until=Deadline;
        if(!Fresh(N)||Until-N>86400){Abort();return false;}
        State=Phase::Adopting;return true;
    }
    bool Check(double N) {return (State==Phase::Adopting||State==Phase::Stopped)&&Fresh(N);}
    bool Commit(double N) {
        if(State!=Phase::Adopting||!Fresh(N))return false;
        State=Phase::Stopped;return true;
    }
    void Abort(){State=Phase::Closed;}
    Phase Get()const{return State;}
};
}
