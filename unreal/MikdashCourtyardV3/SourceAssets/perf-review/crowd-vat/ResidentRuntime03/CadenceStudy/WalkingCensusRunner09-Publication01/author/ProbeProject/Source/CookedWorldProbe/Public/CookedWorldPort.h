#pragma once
#include "CoreMinimal.h"
#include "Engine/World.h"
#include "StrictABI.h"
#include "WalkingQuery.h"
namespace CookedWorldPort {
struct FEpoch {
 uint64 World=0,Geometry=0,Binding=0,Publication=0;
 bool AllWritersEnrolled=false,NoPendingPhysicsWork=false;
 bool operator==(const FEpoch&)const=default;
 bool Valid()const{return World&&Geometry&&Binding&&Publication&&AllWritersEnrolled&&NoPendingPhysicsWork;}
};
// Must cover streaming, cook/rebuild, instance reorder, transforms and publication.
// No default implementation: a frame counter is not a publication fence.
struct IFence {virtual ~IFence()=default;virtual FEpoch Read(const UWorld&)const=0;};
enum class ERefusal {None,Invalid,Epoch,Lock,Payload,NotStatic,Budget,Shape,Mapping,Topology,Filter};
struct FShapeStamp {uint64 Component,Instance,Ordinal,ActorAddress,GeometryAddress,LeafAddress;
 bool Query=false,LeafDoCollide=false; EWalkingShape Classification=EWalkingShape::Unknown;
 uint64 BlockChannels=0,OverlapChannels=0; uint8 ObjectChannel=0;
 uint32 GeometryType=0; FString ComponentPath;};
struct FCapture {
 ERefusal Refusal=ERefusal::Invalid;FEpoch Epoch;FBox RequestedBox;
 TUniquePtr<MeasuredStrict::Snapshot> Data;TArray<FShapeStamp> Shapes;
 uint32 PayloadVisits=0,NodeVisits=0,BoundsTests=0,SourceFaceTests=0,ExhaustedMeshes=0;
 uint64 OwnerAgent=0,OwnerIncarnation=0;int32 Profile=INDEX_NONE;FString WalkingFilter;
 bool PublishedBoxEnumerationExhausted=false;
 bool DiagnosticOnly=false,ObservedBoxEnumerationExhausted=false;
 // Neither enumeration nor support coverage can set these in this phase.
 bool ObstacleComplete=false,WorldComplete=false;
};
// All buckets/overlaps, no nearest hit stopping or floor/component exclusions.
COOKEDWORLDPROBE_API FCapture CaptureBox(UWorld&,const MeasuredStrict::Request&,const IFence&,const IProfileOwnerPublisher&);
// Read-only census: no publisher/world certificate, no strict evaluation or movement approval.
COOKEDWORLDPROBE_API FCapture InspectWalkingBox(UWorld&,const MeasuredStrict::Request&,const IProfileOwnerPublisher&);
COOKEDWORLDPROBE_API FString DescribeWalkingCapture(const FCapture&);
// Builds outward query in strict TU, captures that exact box, then classifies all
// copied triangle surfaces. True means surface-clear ONLY, never movement approval.
COOKEDWORLDPROBE_API bool EvaluateSweptSurface(UWorld&,const MeasuredStrict::Request&,
 const IFence&,const IProfileOwnerPublisher&,FCapture&,MeasuredStrict::Evidence&);
}
