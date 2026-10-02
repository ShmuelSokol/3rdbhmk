#pragma once
#include <array>
#include <cstdint>
#include <cmath>
#include <cstddef>
#include <atomic>
namespace Paired10 {
// Transport85 v10001: unchanged shader packet77 + exact u64 serial/generation
// encoded as four16-bit float lanes each. Never label this a77-float component.
constexpr int ShaderFloats=77, TransportFloats=85, TransportVersion=10001;
using Wire=std::array<float,TransportFloats>;
inline void Token(Wire& W,int Offset,uint64_t V){for(int I=0;I<4;++I)W[Offset+I]=float((V>>(I*16))&65535);}
inline bool HasToken(const Wire& W,int Offset,uint64_t V){Wire E{};Token(E,Offset,V);for(int I=0;I<4;++I)if(W[Offset+I]!=E[Offset+I])return false;return true;}
enum class Phase {Idle,Writing,Pending,Observed,Quarantined};
struct Protocol {
 uint64_t Generation=0,Serial=0;Phase State=Phase::Idle;bool Closed=false;
 explicit Protocol(uint64_t G):Generation(G){}
 bool Begin(uint64_t S,bool Gates){if(!Gates||Closed||State!=Phase::Idle||S==0||S<=Serial)return false;Serial=S;State=Phase::Writing;return true;}
 void Finish(bool Both){if(State!=Phase::Writing||!Both||Closed){Quarantine();return;}State=Phase::Pending;}
 void Quarantine(){State=Phase::Quarantined;Closed=true;}
 bool Observe(uint64_t G,uint64_t S,bool Exact){if(Closed||State!=Phase::Pending||G!=Generation||S!=Serial)return false;if(!Exact){Quarantine();return false;}State=Phase::Observed;return true;}
 bool Consume(uint64_t G,uint64_t S){if(Closed||State!=Phase::Observed||G!=Generation||S!=Serial)return false;State=Phase::Idle;return true;}
};
// Zero is an exhausted allocator sentinel, never reset to1 after wrap.
inline uint64_t AllocateGeneration(std::atomic<uint64_t>& Counter){
 uint64_t G=Counter.load(std::memory_order_relaxed);
 while(G!=0){if(Counter.compare_exchange_weak(G,G+1,std::memory_order_relaxed))return G;}
 return 0;
}
// Renewal is legal only before ANY physical publication attempt. Serial is
// latched before lease acquisition; even a refused/uncertain attempt forbids it.
inline bool MayRenew(const Protocol& P,size_t JournalCount){return P.Closed&&P.Serial==0&&JournalCount==0;}
// Author policy shared verbatim by native ACK and standalone regression.
// The boolean comes from installed FRenderTransform::IsScaleNonUniform().
template<class T> T FinishExpectedTransform(T Value,bool PrimitiveNonUniform){
 if(PrimitiveNonUniform)Value.Orthogonalize();
 return Value;
}
inline bool ExactWire(const Wire& A,const Wire& B){for(int I=0;I<TransportFloats;++I)if(!std::isfinite(A[I])||A[I]!=B[I])return false;return true;}
}
