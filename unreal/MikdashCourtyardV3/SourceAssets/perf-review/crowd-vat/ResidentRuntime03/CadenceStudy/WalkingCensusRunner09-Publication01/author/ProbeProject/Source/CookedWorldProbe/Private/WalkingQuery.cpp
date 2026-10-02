#include "WalkingQuery.h"
#include "Engine/World.h"
#include "CollisionQueryParams.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "PhysicsEngine/BodyInstance.h"
#include "Physics/PhysicsFiltering.h"
#include "Physics/PhysicsInterfaceCore.h"
#include "Physics/Experimental/PhysScene_Chaos.h"
namespace CookedWorldPort {
namespace {
constexpr const TCHAR* MeasuredEvidence=TEXT("141148270e83f5c0a9eb1854320e27f71e78a50657530090a65b302d967d8932");
bool Build(UWorld& World,const MeasuredStrict::Request& R,const FProfileOwner& O,FWalkingQuery& Q){
 if(!IsInGameThread()||O.World.Get()!=&World||!O.Agent||!O.Incarnation||!O.Generation||
    O.Generation!=R.binding||O.Profile!=R.profile||R.profile<0||R.profile>=6||O.Evidence!=MeasuredEvidence)return false;
 auto* Actor=O.Actor.Get();auto* Visual=O.Visual.Get();
 if(!IsValid(Actor)||!IsValid(Visual)||Actor->GetWorld()!=&World||Visual->GetOwner()!=Actor||
    !Visual->IsRegistered()||Visual->GetWorld()!=&World||!World.GetPhysicsScene())return false;
 FCollisionResponseContainer Responses;ECollisionChannel Channel=ECC_Pawn;
 FMaskFilter Mask=0;bool Complex=false;
 Q={};Q.Owner=O;Q.ActorScale=Actor->GetActorScale3D();Q.VisualRelative=Visual->GetRelativeTransform();
 if(O.Kind==EOwnerKind::Character){
  auto* Character=Cast<ACharacter>(Actor);auto* Updated=O.Updated.Get();
  if(!Character||Visual!=Character->GetMesh()||!Character->GetCharacterMovement()||!Updated||Updated!=Character->GetCapsuleComponent()||
     Character->GetCharacterMovement()->UpdatedPrimitive!=Updated||Updated->GetOwner()!=Character||
     !Updated->IsRegistered()||!Updated->IsPhysicsStateCreated()||!Updated->IsQueryCollisionEnabled()||
     O.Instance!=INDEX_NONE||O.InstanceGeneration)return false;
  // Arbitrary movement ignore lists are not silently trusted as measured collision exclusions.
  if(Updated->GetMoveIgnoreActors().Num()||Updated->GetMoveIgnoreComponents().Num())return false;
  FCollisionQueryParams Params;FCollisionResponseParams Pair;
  Updated->InitSweepCollisionParams(Params,Pair);
  Responses=Pair.CollisionResponse;Channel=Updated->GetCollisionObjectType();
  Mask=Params.IgnoreMask;Complex=Params.bTraceComplex;
  auto* Body=Updated->GetBodyInstance(NAME_None,false);
  if(!Body||Body->WeldParent||Body->OwnerComponent.Get()!=Updated||!Body->GetPhysicsActorHandle())return false;
  Q.BodyAddress=reinterpret_cast<UPTRINT>(Body);Q.ProxyAddress=reinterpret_cast<UPTRINT>(Body->GetPhysicsActorHandle());
  Q.VisualAsset=Character->GetMesh()->GetSkeletalMeshAsset();
 }else if(O.Kind==EOwnerKind::VatInstance){
  auto* ISM=Cast<UInstancedStaticMeshComponent>(Visual);
  if(!ISM||O.Updated.IsValid()||O.Instance<0||O.Instance>=ISM->GetInstanceCount()||!O.InstanceGeneration||
     Visual->GetCollisionEnabled()!=ECollisionEnabled::NoCollision||Actor->GetActorEnableCollision())return false;
  // Explicit virtual walking policy: Pawn channel, bilateral BlockAll responses,
  // simple movement collision. This is NOT the player's profile and excludes no actor.
  Responses.SetAllChannels(ECR_Block);
  Q.VisualAsset=ISM->GetStaticMesh();
  if(!ISM->GetInstanceTransform(O.Instance,Q.InstanceTransform,false))return false;
 }else return false;
 if(!Q.VisualAsset.IsValid()||Q.VisualRelative.ContainsNaN()||Q.ActorScale.ContainsNaN()||Q.InstanceTransform.ContainsNaN())return false;
 if(Channel>=ECC_MAX||Channel==ECC_OverlapAll_Deprecated)return false;
 FPhysicsTraceQueryFilterBuilder Builder(World.GetPhysicsScene());
 Builder.SetCollisionChannelIndex(Channel).SetResponses(Responses).SetMaskFilter(Mask)
  .SetFlags(Chaos::EFilterFlags::ComplexCollision,Complex)
  .SetFlags(Chaos::EFilterFlags::SimpleCollision,!Complex);
 Q.Filter=Builder.Build();return Q.Filter.IsValid();
}
}
bool ResolveWalkingQuery(UWorld& W,const MeasuredStrict::Request& R,const IProfileOwnerPublisher& P,FWalkingQuery& Q){
 Q={};FProfileOwner O;return P.Resolve(R,O)&&Build(W,R,O,Q);
}
bool ValidateWalkingQuery(UWorld& W,const MeasuredStrict::Request& R,const IProfileOwnerPublisher& P,const FWalkingQuery& Q){
 FWalkingQuery Live;if(!ResolveWalkingQuery(W,R,P,Live))return false;
 return Live.Owner==Q.Owner&&Live.Filter==Q.Filter&&Live.BodyAddress==Q.BodyAddress&&Live.ProxyAddress==Q.ProxyAddress&&
  Live.ActorScale.Equals(Q.ActorScale,0)&&Live.VisualRelative.Equals(Q.VisualRelative,0)&&
  Live.VisualAsset==Q.VisualAsset&&Live.InstanceTransform.Equals(Q.InstanceTransform,0);
}
EWalkingShape ClassifyWalkingShape(bool Enabled,bool Self,const Chaos::Filter::FQueryFilterData& Query,
 const Chaos::Filter::FShapeFilterData& Shape){
 if(!Enabled)return EWalkingShape::QueryDisabled;
 if(!Query.IsValid()||Query.GetQueryType()!=Chaos::Filter::FQueryFilterData::EQueryType::Channel||!Shape.IsValid())return EWalkingShape::Unknown;
 if(Self)return EWalkingShape::ExactOwnBody;
 const auto Hit=Query.NarrowFilter(Shape);
 if(Hit==Chaos::Filter::ENarrowFilterResult::None||Hit==Chaos::Filter::ENarrowFilterResult::Overlap)
  return EWalkingShape::NonBlockingResponse;
 if(Hit!=Chaos::Filter::ENarrowFilterResult::Block)return EWalkingShape::Unknown;
 const auto Common=Query.GetFlags()&Shape.GetFlags();
 if(!(Common&Chaos::EFilterFlags::SimpleCollision)&&!(Common&Chaos::EFilterFlags::ComplexCollision))
  return EWalkingShape::OtherComplexity;
 return EWalkingShape::Blocking;
}
}
