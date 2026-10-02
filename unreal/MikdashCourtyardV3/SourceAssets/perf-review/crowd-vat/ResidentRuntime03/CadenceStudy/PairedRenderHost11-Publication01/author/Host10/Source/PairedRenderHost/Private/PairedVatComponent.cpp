#include "PairedVatComponent.h"
#include "Engine/InstancedStaticMesh.h"
#include "InstanceDataSceneProxy.h"
#include "InstancedStaticMesh/ISMInstanceDataSceneProxy.h"
#include "RenderTransform.h"
#include "Engine/World.h"
#include "Misc/ScopeLock.h"
#include <atomic>

namespace {
std::atomic<uint64> NextGeneration{1};
// Compare transformed renderer representation exactly, never an epsilon that
// would authorize mismatched basis. Unexpected platform rounding fails closed.
bool Same(const FRenderTransform& A,const FRenderTransform& B){
 for(int I=0;I<3;++I)if(A.TransformRows[I]!=B.TransformRows[I])return false;
 return A.Origin==B.Origin;
}
class FPairedVatProxy final : public FInstancedStaticMeshSceneProxy {
 TSharedRef<FPairedVatSession,ESPMode::ThreadSafe> Session;
public:
 FPairedVatProxy(UPairedVatComponent* C,TSharedRef<FPairedVatSession,ESPMode::ThreadSafe> S):FInstancedStaticMeshSceneProxy(C,C->GetWorld()->GetFeatureLevel()),Session(S){}
 virtual ~FPairedVatProxy() override {Session->Close();}
 virtual void UpdateInstances_RenderThread(FRHICommandListBase& RHICmdList,const FBoxSphereBounds& Bounds,const FBoxSphereBounds& LocalBounds) override {
  FInstancedStaticMeshSceneProxy::UpdateInstances_RenderThread(RHICmdList,Bounds,LocalBounds);
  // This is the renderer's actual scene update callback, NOT a separately queued
  // fence/marker. SynchronizeUpdateTask is the public accessor default in UE5.8.
  const FInstanceSceneDataBuffers* B=GetInstanceSceneDataBuffers();
  FScopeLock Guard(&Session->Lock);
  auto& P=Session->Protocol;if(P.Closed||P.State!=Paired10::Phase::Pending)return;
  const auto& S=Session->Pending;
  bool Exact=B&&!B->IsInstanceDataGPUOnly()&&B->GetNumInstances()==S.Wires.Num()&&B->GetNumCustomDataFloats()==Paired10::TransportFloats;
  if(Exact){
   auto V=B->GetReadView();
   Exact=V.InstanceCustomData.Num()==S.Wires.Num()*Paired10::TransportFloats&&V.PrevInstanceToPrimitiveRelative.Num()==S.Wires.Num();
   int Matched=0;
   if(Exact)for(int I=0;I<S.Wires.Num();++I){
    Paired10::Wire Actual{};for(int J=0;J<Paired10::TransportFloats;++J)Actual[J]=V.InstanceCustomData[I*Paired10::TransportFloats+J];
    if(Paired10::HasToken(Actual,77,P.Serial)&&Paired10::HasToken(Actual,81,P.Generation))++Matched;
   }
   // Old callback before our flush is not our serial; no ACK, no false failure.
   if(Exact&&Matched==0)return;
   Exact=Exact&&Matched==S.Wires.Num();
   for(int I=0;Exact&&I<S.Wires.Num();++I){
    Paired10::Wire Actual{};for(int J=0;J<Paired10::TransportFloats;++J)Actual[J]=V.InstanceCustomData[I*Paired10::TransportFloats+J];
    FRenderTransform Current=FRenderTransform(FMatrix44f(S.Current[I].ToMatrixWithScale()))*V.PrimitiveToRelativeWorld;
    FRenderTransform Previous=FRenderTransform(FMatrix44f(S.Previous[I].ToMatrixWithScale()))*V.PrimitiveToRelativeWorld;
    Current.Orthogonalize();Previous.Orthogonalize();
    Exact=Paired10::HasToken(Actual,77,P.Serial)&&Paired10::HasToken(Actual,81,P.Generation)&&Paired10::ExactWire(Actual,S.Wires[I])
     &&Same(Current,V.InstanceToPrimitiveRelative[I])&&Same(Previous,V.PrevInstanceToPrimitiveRelative[I]);
   }
  }
  P.Observe(P.Generation,P.Serial,Exact);
  // ACK means this proxy consumed the exact render-side CPU instance buffers.
  // GPUScene upload/draw/pixels/motion vectors remain independently UNPROVED.
 }
};
}
UPairedVatComponent::UPairedVatComponent(){
 NumCustomDataFloats=Paired10::TransportFloats;
 SetHasPerInstancePrevTransforms(true);
 SetCollisionEnabled(ECollisionEnabled::NoCollision);SetCanEverAffectNavigation(false);
}
void UPairedVatComponent::OnRegister(){
 if(Session)Session->Close();
 const uint64 G=NextGeneration.fetch_add(1);
 if(G==0){Session.Reset();return;}
 Session=MakeShared<FPairedVatSession,ESPMode::ThreadSafe>(G);
 Super::OnRegister();
}
void UPairedVatComponent::OnUnregister(){if(Session)Session->Close();Super::OnUnregister();}
void UPairedVatComponent::DestroyRenderState_Concurrent(){if(Session)Session->Close();Super::DestroyRenderState_Concurrent();}
FPrimitiveSceneProxy* UPairedVatComponent::CreateStaticMeshSceneProxy(Nanite::FMaterialAudit&,bool bCreateNanite){
 if(bCreateNanite||!Session||CheckPSOPrecachingAndBoostPriority())return nullptr;
 FScopeLock Guard(&Session->Lock);if(Session->Protocol.Closed)return nullptr;
 GetOrCreateInstanceDataSceneProxy();
 return new FPairedVatProxy(this,Session.ToSharedRef());
}
EPairedVatSubmit UPairedVatComponent::Submit(const TArray<FPairedVatItem>& Items,uint64 Serial,TSharedPtr<IPairedVatLease,ESPMode::ThreadSafe> Lease){
 if(!IsInGameThread()||!IsRegistered()||!IsRenderStateCreated()||IsRenderStateDirty()||!GetSceneProxy()||!Session||!Lease
  ||GetInstanceCount()<1||GetInstanceCount()>64||Items.Num()!=GetInstanceCount()||NumCustomDataFloats!=Paired10::TransportFloats
  ||!GetComponentTransform().Equals(FTransform::Identity,0.0)||!Lease->MaterialConsumes9001PrefixOnTransport10001(*this))return EPairedVatSubmit::Hold;
 const auto Tx=Session; // Keep original generation even if lease callback recreates component.
 // Bounded bring-up mapping is component identity + local roots. LWC/rebasing
 // requires a separate verified adapter; do not silently reinterpret world roots.
 FPairedVatSnapshot Next;Next.Items=Items;Next.Lease=Lease;
 for(const auto& I:Items){
  if(!I.Packet.Pending||I.Packet.Data[30]!=float(CurvedVat09::Version)||!CurvedVat09::Finite(I.Packet.BasisRoot)
   ||!FMath::IsFinite(I.Packet.BasisYaw)||!FMath::IsFinite(I.Packet.Scale)||I.Packet.Scale<=0||I.PreviousLocal.ContainsNaN())return EPairedVatSubmit::Hold;
  Paired10::Wire W{};for(int J=0;J<77;++J){if(!FMath::IsFinite(I.Packet.Data[J]))return EPairedVatSubmit::Hold;W[J]=I.Packet.Data[J];}
  Paired10::Token(W,77,Serial);Paired10::Token(W,81,Tx->Protocol.Generation);Next.Wires.Add(W);
  Next.Current.Emplace(FRotator(0,I.Packet.BasisYaw,0),FVector(I.Packet.BasisRoot.X,I.Packet.BasisRoot.Y,I.Packet.BasisRoot.Z),FVector(I.Packet.Scale));
  Next.Previous.Add(I.PreviousLocal);
 }
 // Reserve bounded journal ownership BEFORE asking a lease to acquire anything.
 // Capacity/busy/stale serial refusals cannot call ValidateAndHold.
 {
  FScopeLock Guard(&Tx->Lock);
  if(Tx->Retained.Num()>=64)return EPairedVatSubmit::Hold;
  if(!Tx->Protocol.Begin(Serial,true))return EPairedVatSubmit::Hold;
  Tx->Pending=MoveTemp(Next);
  Tx->Retained.Add(Tx->Pending);
 }
 // No lock across owner code. Writing suppresses render extraction. Even false
 // may represent an uncertain acquisition: retain snapshot/lease, quarantine.
 const bool Held=Lease->ValidateAndHold(*this,Items,Tx->Protocol.Generation,Serial);
 FScopeLock Guard(&Tx->Lock);
 if(!Held||Session!=Tx||Tx->Protocol.Closed||Tx->Protocol.State!=Paired10::Phase::Writing
  ||!IsRegistered()||!IsRenderStateCreated()||IsRenderStateDirty()||!GetSceneProxy()){
  Tx->Protocol.Quarantine();return EPairedVatSubmit::Quarantined;
 }
 bool Both=true;
 // Entire write sequence is one GT call, no latent/flush/reentrant render pump.
 // Game-thread EOF required; render thread cannot extract these UObject arrays.
 for(int I=0;Both&&I<Items.Num();++I)Both=SetCustomData(I,MakeArrayView(Tx->Pending.Wires[I].data(),Paired10::TransportFloats),false);
 Both=Both&&BatchUpdateInstancesTransforms(0,Tx->Pending.Current,Tx->Pending.Previous,false,false,true);
 Tx->Protocol.Finish(Both);
 // Manager marks instances dirty automatically. Never destroy proxy to publish.
 return Both?EPairedVatSubmit::Pending:EPairedVatSubmit::Quarantined;
}
bool UPairedVatComponent::PollConsumed(uint64 Generation,uint64 Serial){
 if(!IsInGameThread()||!Session)return false;
 FScopeLock Guard(&Session->Lock);
 if(!IsRegistered()||!IsRenderStateCreated()||IsRenderStateDirty()||!GetSceneProxy()){Session->Protocol.Quarantine();return false;}
 if(!Session->Protocol.Consume(Generation,Serial))return false;
 Session->LastObserved=Session->Pending;
 // Caller may acknowledge corresponding09 publications by exact item serials.
 // Neither render ACK nor this poll is permission to release physical tails.
 return true;
}

void UPairedVatComponent::SendRenderInstanceData_Concurrent(){
 check(IsInGameThread());
 if(!Session)return;
 {FScopeLock Guard(&Session->Lock);if(Session->Protocol.Closed||Session->Protocol.State==Paired10::Phase::Writing)return;}
 Super::SendRenderInstanceData_Concurrent();
}
