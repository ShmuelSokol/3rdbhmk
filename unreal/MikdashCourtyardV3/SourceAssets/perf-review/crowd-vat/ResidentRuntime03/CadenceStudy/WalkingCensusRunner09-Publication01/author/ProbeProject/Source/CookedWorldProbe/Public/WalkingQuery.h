#pragma once
#include "CoreMinimal.h"
#include "Components/PrimitiveComponent.h"
#include "Chaos/CollisionFilterData.h"
#include "StrictABI.h"
class ACharacter;
namespace CookedWorldPort {
enum class EOwnerKind : uint8 { Unknown, Character, VatInstance };
// Issued by the measured-profile publisher, never inferred from a player/controller.
// Publisher must resolve exact measured assets, scale, root offset and instance incarnation.
struct FProfileOwner {
 EOwnerKind Kind=EOwnerKind::Unknown;
 uint64 Agent=0,Incarnation=0,Generation=0; int32 Profile=INDEX_NONE;
 FString Evidence;
 TWeakObjectPtr<UWorld> World;
 TWeakObjectPtr<AActor> Actor;
 TWeakObjectPtr<UPrimitiveComponent> Visual;
 TWeakObjectPtr<UPrimitiveComponent> Updated;
 int32 Instance=INDEX_NONE; uint64 InstanceGeneration=0;
 bool operator==(const FProfileOwner&)const=default;
};
struct IProfileOwnerPublisher {
 virtual ~IProfileOwnerPublisher()=default;
 // No default implementation. False/unknown identity means no query or self exclusion.
 // Pure bounded read: called under a scene read lock; must not wait, mutate, or take a write lock.
 // The owning publisher increments Generation before any body/asset/instance remapping;
 // pointer equality alone cannot detect destroy/recreate ABA. An unenrolled publisher returns false.
 virtual bool Resolve(const MeasuredStrict::Request&,FProfileOwner&)const=0;
};
struct FWalkingQuery {
 FProfileOwner Owner;
 Chaos::Filter::FQueryFilterData Filter;
 UPTRINT BodyAddress=0,ProxyAddress=0;
 FTransform VisualRelative=FTransform::Identity; FVector ActorScale=FVector::ZeroVector;
 TWeakObjectPtr<UObject> VisualAsset;
 FTransform InstanceTransform=FTransform::Identity;
 // Immutable for one acquisition. VAT has no physical own body and no ignore list.
};
enum class EWalkingShape : uint8 { Unknown, QueryDisabled, ExactOwnBody,
 NonBlockingResponse, OtherComplexity, Blocking };
COOKEDWORLDPROBE_API bool ResolveWalkingQuery(UWorld&,const MeasuredStrict::Request&,
 const IProfileOwnerPublisher&,FWalkingQuery&);
COOKEDWORLDPROBE_API bool ValidateWalkingQuery(UWorld&,const MeasuredStrict::Request&,
 const IProfileOwnerPublisher&,const FWalkingQuery&);
// Uses installed Chaos narrow filter; geometry class is deliberately absent.
COOKEDWORLDPROBE_API EWalkingShape ClassifyWalkingShape(bool QueryEnabled,bool ExactSelf,
 const Chaos::Filter::FQueryFilterData&,const Chaos::Filter::FShapeFilterData&);
}
