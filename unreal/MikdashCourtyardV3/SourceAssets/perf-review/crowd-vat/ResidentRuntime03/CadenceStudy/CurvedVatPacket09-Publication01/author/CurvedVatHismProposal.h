#pragma once
// REVIEW-ONLY UE-facing source. NOT included in any production module and NOT
// UBT-compiled. Existing 30-float materials/components must never reach here.
#include "CoreMinimal.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "CurvePacket.h"
namespace CurvedVat09 {
// Concrete HISM submission consumes the exact portable packet. Physical
// reservation+enqueue transaction and a real render-ACK implementation belong
// to the actor's host port; there is intentionally no permissive default host.
struct FNativePacketSubmission {
 int32 LocalInstance=INDEX_NONE;Publication Value;FVector LocalFrameWorldOrigin=FVector::ZeroVector;
 uint64 WorldEpoch=0,RouteEpoch=0;
};
class ICurveNativeLease {
public:
 virtual ~ICurveNativeLease()=default;
 virtual bool IsIsolatedEnrolledComponent(const UHierarchicalInstancedStaticMeshComponent&) const=0;
 virtual bool AllSlotsUseVersionedMaterial(int32 LayoutVersion,int32 Floats) const=0;
 virtual bool HoldsCompleteSupportAndImmutableWorld(const FNativePacketSubmission&) const=0;
 virtual bool HasReservationForExactPacket(const FNativePacketSubmission&) const=0;
 virtual bool HasSynchronizedPublicationAndRenderAckProtocol() const=0;
 // Must enclose both HISM writes against scene extraction and any world writer.
 // No implementation is supplied: stock SetCustomData success is NOT this fence.
 virtual bool BeginPairedPublication(uint64 Serial)=0;
 virtual void FinishPairedPublication(uint64 Serial,bool BothWritesSucceeded)=0;
 virtual void QuarantineKeepReservations(uint64 Serial)=0;
};
enum class ESubmit { Hold,SubmittedAwaitingRenderAck,Quarantined };
inline ESubmit SubmitToIsolatedHism(UHierarchicalInstancedStaticMeshComponent& C,const FNativePacketSubmission& S,ICurveNativeLease& Lease){
 if(!IsInGameThread()||!S.Value.Pending||S.LocalInstance<0||S.LocalInstance>=C.GetInstanceCount()||C.NumCustomDataFloats!=Floats
  ||S.Value.Data[30]!=float(Version)||!Lease.IsIsolatedEnrolledComponent(C)||!Lease.AllSlotsUseVersionedMaterial(Version,Floats)
  ||!Lease.HoldsCompleteSupportAndImmutableWorld(S)||!Lease.HasReservationForExactPacket(S)||!Lease.HasSynchronizedPublicationAndRenderAckProtocol())return ESubmit::Hold;
 if(!Lease.BeginPairedPublication(S.Value.Serial))return ESubmit::Hold;
 // BasisYaw MUST include MeshYawOffsetDegrees exactly as TransformFor does.
 // CPU world mapping subtracts the same retained LWC frame before float casts.
 const Vec& R=S.Value.BasisRoot;const FVector Root=S.LocalFrameWorldOrigin+FVector(R.X,R.Y,R.Z);
 TArray<FTransform> Transform;Transform.Emplace(FRotator(0,S.Value.BasisYaw,0),Root,FVector(S.Value.Scale));
 const TArrayView<const float> Data(S.Value.Data.data(),Floats);
 const bool DataWritten=C.SetCustomData(S.LocalInstance,Data,false);
 const bool TransformWritten=DataWritten&&C.BatchUpdateInstancesTransforms(S.LocalInstance,Transform,true,false,true);
 Lease.FinishPairedPublication(S.Value.Serial,DataWritten&&TransformWritten);
 if(!DataWritten||!TransformWritten){Lease.QuarantineKeepReservations(S.Value.Serial);return ESubmit::Quarantined;}
 // Not a render ACK and not permission to release previous/current/successor.
 return ESubmit::SubmittedAwaitingRenderAck;
}
}
