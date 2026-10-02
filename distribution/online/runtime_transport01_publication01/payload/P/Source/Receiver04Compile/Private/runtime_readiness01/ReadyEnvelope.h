#pragma once
#include "../runtime_settings05/PrivateEnvelope.h"
namespace MikdashOnline::Readiness01 {
inline bool Envelope(const uint8_t* P,size_t N,std::vector<uint8_t>& V2,
                     Settings05::Descriptor& D,uint64_t& Event) {
    if(!P||N<=52||N>4092||std::string(reinterpret_cast<const char*>(P),4)!="MKR1")return false;
    uint64_t H=0;
    if(!Settings05::Hex(reinterpret_cast<const char*>(P+4),16,H)||!H)return false;
    std::vector<uint8_t> V1;
    const bool Good=Settings05::Envelope(P+52,N-52,V1,D);
    // V1 may contain the original receiver key; wipe before releasing storage.
    volatile uint8_t* W=V1.data();for(size_t I=0;I<V1.size();++I)W[I]=0;
    if(!Good||H==D.event||std::string(reinterpret_cast<const char*>(P+20),32)!=D.generation)return false;
    V2.assign(P+52,P+N);Event=H;return true;
}
}
