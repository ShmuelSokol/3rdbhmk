#include "CookedWorldPort.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "PhysicsEngine/BodyInstance.h"
#include "Physics/PhysicsInterfaceCore.h"
#include "Physics/Experimental/ChaosScopedSceneLock.h"
#include "Physics/Experimental/PhysScene_Chaos.h"
#include "Physics/Experimental/PhysicsUserData_Chaos.h"
#include "PhysicsProxy/SingleParticlePhysicsProxy.h"
#include "Chaos/ChaosScene.h"
#include "Chaos/ISpatialAcceleration.h"
#include "Chaos/SpatialAccelerationCollection.h"
#include "Chaos/ParticleHandle.h"
#include "Chaos/ImplicitObjectScaled.h"
#include "Chaos/ImplicitObjectTransformed.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Chaos/CollisionFilterData.h"
#include "UObject/StrongObjectPtr.h"
#include <map>
#include <set>
#include <array>
#include <algorithm>

namespace CookedWorldPort {
namespace {
struct FStop {ERefusal Why;};
void Need(bool B,ERefusal R){if(!B)throw FStop{R};}
struct FRead final:FScopedSceneLock_Chaos {
 FChaosScene* Scene;
 explicit FRead(FChaosScene* S):FScopedSceneLock_Chaos(S,EPhysicsInterfaceScopedLockType::Read),Scene(S){}
 bool Held()const{return bHasLock;}
 bool SameScene(const FPhysicsActorHandle& A){return GetSceneForActor(A)==Scene;}
};
uint32 FloatBits(const float& V){uint32 B;FMemory::Memcpy(&B,&V,4);return B;}
bool Finite(double V){uint64 B;FMemory::Memcpy(&B,&V,8);return (B&0x7ff0000000000000ULL)!=0x7ff0000000000000ULL;}
bool Positive(double V){uint64 B;FMemory::Memcpy(&B,&V,8);return Finite(V)&&!(B>>63)&&(B&0x7fffffffffffffffULL)!=0;}
MeasuredStrict::Transform Raw(const FTransform& T){
 const auto S=T.GetScale3D(),P=T.GetTranslation();const auto Q=T.GetRotation();
 MeasuredStrict::Transform R{{S.X,S.Y,S.Z},{P.X,P.Y,P.Z},{Q.X,Q.Y,Q.Z,Q.W}};
 for(int J=0;J<3;++J)Need(Positive(R.scale[J])&&Finite(R.translation[J]),ERefusal::Shape);
 for(double V:R.quaternion)Need(Finite(V),ERefusal::Shape);return R;
}
void CopyMesh(const Chaos::FTriangleMeshImplicitObject& M,MeasuredStrict::Shape& S,FCapture& Out){
 auto& D=*Out.Data;const auto& P=M.Particles();const auto& E=M.Elements();const int32 NF=E.GetNumTriangles();
 Need(P.Size()>0&&NF>0,ERefusal::Topology);
 // UE5.8 exported but INTERNAL accessor: exact source/layout pinned; needs native API review.
 // Do not call FindOverlappingTriangles: it allocates the full result before caller limits.
 PRAGMA_DISABLE_INTERNAL_WARNINGS
 const auto& BVH=M.GetBVH();
 PRAGMA_ENABLE_INTERNAL_WARNINGS
 Need(!BVH.Nodes.IsEmpty(),ERefusal::Topology);
 S.firstVertex=D.vertices;S.firstFace=D.faces;S.vertices=S.faces=0;
 std::map<uint32,uint32> Remap; // ORIGINAL particle index -> one copied vertex; no coordinates.
 std::map<std::pair<uint32,uint32>,std::pair<uint32,uint32>> Edges;
 std::set<std::array<uint32,3>> Triangles;std::set<int32> External,VisitedNodes,VisitedFaces;
 TArray<int32,TInlineAllocator<32>> Stack;Stack.Add(0);
 auto ReadPoint=[&](uint32 Index){Need(Index<uint32(P.Size()),ERefusal::Topology);const auto& V=P.GetX(Index);
  static_assert(sizeof(V.X)==4);MeasuredStrict::Vertex Dest{};Dest.originalParticle=Index;
  Dest.xyzBits[0]=FloatBits(V.X);Dest.xyzBits[1]=FloatBits(V.Y);Dest.xyzBits[2]=FloatBits(V.Z);
  for(uint32 B:Dest.xyzBits)Need((B&0x7f800000u)!=0x7f800000u,ERefusal::Topology);return Dest;
 };
 while(!Stack.IsEmpty()){
  Need(++Out.NodeVisits<=2048,ERefusal::Budget);const int32 NodeIndex=Stack.Pop(EAllowShrinking::No);
  Need(BVH.Nodes.IsValidIndex(NodeIndex)&&VisitedNodes.insert(NodeIndex).second,ERefusal::Topology);
  const auto& Children=BVH.Nodes[NodeIndex].Children;
  for(int Child=0;Child<2;++Child){const int32 Index=Children.GetChildOrFaceIndex(Child),Count=Children.GetFaceCount(Child);
   if(Index==INDEX_NONE){Need(Count==0,ERefusal::Topology);continue;}
   Need(Index>=0&&Count>=0,ERefusal::Topology);
   if(Count>0)Need(Index<=NF&&Count<=NF-Index,ERefusal::Topology);
   else Need(BVH.Nodes.IsValidIndex(Index),ERefusal::Topology);
   Need(++Out.BoundsTests<=4096,ERefusal::Budget);
   alignas(16) float Low[4],High[4];const auto& Bounds=Children.GetBounds(Child);
   VectorStoreAligned(Bounds.GetMin(),Low);VectorStoreAligned(Bounds.GetMax(),High);
   uint32 LoBits[3],HiBits[3];for(int J=0;J<3;++J){LoBits[J]=FloatBits(Low[J]);HiBits[J]=FloatBits(High[J]);}
   const auto BoundResult=MeasuredStrictCullBounds(&S,LoBits,HiBits,&D.capturedQuery);
   Need(BoundResult!=MeasuredStrict::Cull::Refused,ERefusal::Shape);
   if(BoundResult==MeasuredStrict::Cull::Disjoint)continue;
   if(Count==0){Need(Stack.Num()<2048,ERefusal::Budget);Stack.Add(Index);continue;}
   // Skip quantized per-face BVH bounds. Test ORIGINAL triangle vertices instead,
   // avoiding unproved dequantization/FMA rounding in normal engine FP mode.
   for(int32 I=Index;I<Index+Count;++I){
    Need(++Out.SourceFaceTests<=4096,ERefusal::Budget);Need(VisitedFaces.insert(I).second,ERefusal::Topology);
    MeasuredStrict::Vertex Points[3];uint32 Original[3];
    for(int J=0;J<3;++J){const int32 V=E.RequiresLargeIndices()?int32(E.GetLargeIndexBuffer()[I][J]):int32(E.GetSmallIndexBuffer()[I][J]);
     Need(V>=0,ERefusal::Topology);Original[J]=uint32(V);Points[J]=ReadPoint(Original[J]);}
    Need(Original[0]!=Original[1]&&Original[1]!=Original[2]&&Original[0]!=Original[2],ERefusal::Topology);
    const auto FaceResult=MeasuredStrictCullTriangle(&S,Points,&D.capturedQuery);
    Need(FaceResult!=MeasuredStrict::Cull::Refused,ERefusal::Shape);
    if(FaceResult==MeasuredStrict::Cull::Disjoint)continue;
    Need(D.faces<MeasuredStrict::MaxFaces,ERefusal::Budget);
    auto& F=D.face[D.faces++];F.shape=D.shapes;F.internal=uint32(I);
    F.external=M.GetExternalFaceIndexFromInternal(I);Need(F.external>=0&&External.insert(F.external).second,ERefusal::Mapping);
    for(int J=0;J<3;++J){auto Found=Remap.find(Original[J]);
     if(Found==Remap.end()){Need(D.vertices<MeasuredStrict::MaxVertices,ERefusal::Budget);
      const uint32 Dest=D.vertices++;D.vertex[Dest]=Points[J];Remap.emplace(Original[J],Dest);F.index[J]=Dest;++S.vertices;
     }else F.index[J]=Found->second;
    }
    ++S.faces;std::array<uint32,3> Sorted{Original[0],Original[1],Original[2]};std::sort(Sorted.begin(),Sorted.end());
    Need(Triangles.insert(Sorted).second,ERefusal::Topology);
    for(int J=0;J<3;++J){uint32 A=Original[J],B=Original[(J+1)%3];auto Key=std::make_pair(std::min(A,B),std::max(A,B));
     auto Found=Edges.find(Key);if(Found==Edges.end())Edges.emplace(Key,std::make_pair(A,B));
     else{Need(Found->second.first==B&&Found->second.second==A,ERefusal::Topology);Found->second={UINT32_MAX,UINT32_MAX};}
    }
   }
  }
 }
 ++Out.ExhaustedMeshes; // Only reached after the entire bounded worklist drains.
 // No orientation filtering; original indices retained even for vertical/downward faces.
}
void Visit(const Chaos::FImplicitObject& G,MeasuredStrict::Shape& S,FCapture& Out,FShapeStamp& Stamp,unsigned Depth=0){
 using namespace Chaos;
 Need(Depth<MeasuredStrict::MaxDepth,ERefusal::Budget);
 const float Margin=G.GetMarginf();Need((FloatBits(Margin)&0x7fffffffu)==0,ERefusal::Shape);
 switch(G.GetType()){
 case ImplicitObjectType::TriangleMesh:
  Stamp.LeafAddress=reinterpret_cast<UPTRINT>(&G);Stamp.LeafDoCollide=G.GetDoCollide();
  CopyMesh(G.GetObjectChecked<FTriangleMeshImplicitObject>(),S,Out);return;
 case ImplicitObjectType::Transformed:{
  const auto& T=G.GetObjectChecked<TImplicitObjectTransformed<FReal,3>>();Need(S.depth<MeasuredStrict::MaxDepth&&T.GetTransformedObject()!=nullptr,ERefusal::Shape);
  S.outerToInner[S.depth++]=Raw(T.GetTransform());Visit(*T.GetTransformedObject(),S,Out,Stamp,Depth+1);return;}
 case ImplicitObjectType::IsScaled|ImplicitObjectType::TriangleMesh:{
  const auto& T=G.GetObjectChecked<TImplicitObjectScaled<FTriangleMeshImplicitObject>>();Need(S.depth<MeasuredStrict::MaxDepth&&T.GetUnscaledObject()!=nullptr,ERefusal::Shape);
  const auto V=T.GetScale();Need(Positive(V.X)&&Positive(V.Y)&&Positive(V.Z),ERefusal::Shape);
  S.outerToInner[S.depth++]={{V.X,V.Y,V.Z},{0,0,0},{0,0,0,1}};Visit(*T.GetUnscaledObject(),S,Out,Stamp,Depth+1);return;}
 case ImplicitObjectType::IsInstanced|ImplicitObjectType::TriangleMesh:{
  const auto& T=G.GetObjectChecked<TImplicitObjectInstanced<FTriangleMeshImplicitObject>>();Need(T.GetInstancedObject()!=nullptr,ERefusal::Shape);
  Visit(*T.GetInstancedObject(),S,Out,Stamp,Depth+1);return;}
 default:throw FStop{ERefusal::Shape}; // Boxes, convex, heightfields, unions, unknown wrappers.
 }
}
struct FCollector final:Chaos::ISpatialVisitor<Chaos::FAccelerationStructureHandle,Chaos::FReal>{
 UWorld& World;FRead& Lock;FCapture& Out;const FWalkingQuery& Walking;
 TArray<TStrongObjectPtr<UPrimitiveComponent>> KeepAlive;
 TArray<FPhysicsActorHandle> Actors;
 FCollector(UWorld& W,FRead& L,FCapture& O,const FWalkingQuery& Q):World(W),Lock(L),Out(O),Walking(Q){}
 bool Overlap(const Chaos::TSpatialVisitorData<Chaos::FAccelerationStructureHandle>& Item)override{
  Need(++Out.PayloadVisits<=64,ERefusal::Budget);
  auto* Particle=Item.Payload.GetExternalGeometryParticle_ExternalThread();Need(Particle!=nullptr,ERefusal::Payload);
  auto* Body=FPhysicsUserData_Chaos::Get<FBodyInstance>(Particle->UserData());Need(Body&&Body->WeldParent==nullptr,ERefusal::Payload);
  auto* Component=Body->OwnerComponent.Get();
  Need(IsValid(Component)&&Component->GetWorld()==&World&&Component->IsRegistered()&&Component->IsPhysicsStateCreated(),ERefusal::Payload);
  auto* ISM=Cast<UInstancedStaticMeshComponent>(Component);const int32 Instance=ISM?Body->InstanceBodyIndex:INDEX_NONE;
  Need((!ISM||(Instance>=0&&Instance<ISM->GetInstanceCount()))&&Component->GetBodyInstance(NAME_None,false,Instance)==Body,ERefusal::Payload);
  const auto Actor=Body->GetPhysicsActorHandle();Need(Actor&&Particle->GetProxy()==Actor&&Lock.SameScene(Actor),ERefusal::Payload);
  if(Actors.Contains(Actor))return true;Need(Actors.Num()<16,ERefusal::Budget);Actors.Add(Actor);KeepAlive.Emplace(Component);
  Need(FPhysicsInterface::IsInScene(Actor),ERefusal::Payload);
  const int32 Count=FPhysicsInterface::GetNumShapes(Actor);Need(Count>0&&Count<=32,ERefusal::Budget);
  TArray<FPhysicsShapeHandle> Shapes;FPhysicsInterface::GetAllShapes_AssumedLocked(Actor,Shapes);Need(Shapes.Num()==Count,ERefusal::Epoch);
  for(int32 I=0;I<Count;++I){const auto& Shape=Shapes[I];Need(Shape.IsValid(),ERefusal::Shape);
   Need(Out.Shapes.Num()<32,ERefusal::Budget);
   const auto& G=Shape.GetGeometry();FShapeStamp Stamp{Component->GetUniqueID(),Instance==INDEX_NONE?0:uint64(Instance)+1,uint64(I)+1,
      reinterpret_cast<UPTRINT>(Actor),reinterpret_cast<UPTRINT>(&G),0,FPhysicsInterface::IsQueryShape(Shape),false};
   const bool ExactSelf=Walking.Owner.Kind==EOwnerKind::Character&&
    Walking.Owner.Updated.Get()==Component&&Component->GetOwner()==Walking.Owner.Actor.Get()&&
    Walking.BodyAddress==reinterpret_cast<UPTRINT>(Body)&&Walking.ProxyAddress==reinterpret_cast<UPTRINT>(Actor);
   const auto Filter=FPhysicsInterface::GetShapeFilterData(Shape);
   Stamp.Classification=ClassifyWalkingShape(Stamp.Query,ExactSelf,Walking.Filter,Filter);
   Stamp.GeometryType=static_cast<uint32>(G.GetType());Stamp.ComponentPath=Component->GetPathName();
   if(Filter.IsValid()){Stamp.BlockChannels=Filter.GetBlockChannels();Stamp.OverlapChannels=Filter.GetOverlapChannels();Stamp.ObjectChannel=Filter.GetCollisionChannelIndex();}
   Out.Shapes.Add(Stamp); // Keep counted classification evidence even if a later blocker refuses.
   Need(Stamp.Classification!=EWalkingShape::Unknown,ERefusal::Filter);
   if(Stamp.Classification!=EWalkingShape::Blocking)continue;
   // Only now inspect geometry support/static mobility. Never drop unsupported BLOCKING shapes.
   Need(Cast<UStaticMeshComponent>(Component)!=nullptr,ERefusal::Shape);
   Need(Component->GetMobility()==EComponentMobility::Static&&FPhysicsInterface::IsStatic(Actor),ERefusal::NotStatic);
   auto& D=*Out.Data;Need(D.shapes<MeasuredStrict::MaxShapes,ERefusal::Budget);auto& S=D.shape[D.shapes];
   S.component=Stamp.Component;S.instance=Stamp.Instance;S.ordinal=Stamp.Ordinal;S.depth=1;
   S.outerToInner[0]=Raw(FPhysicsInterface::GetGlobalPose_AssumesLocked(Actor));
   Visit(G,S,Out,Stamp);++D.shapes;Out.Shapes.Last()=Stamp;

  }return true;
 }
 bool PrePreFilter(const Chaos::FAccelerationStructureHandle&)const override{return false;}
 bool Raycast(const Chaos::TSpatialVisitorData<Chaos::FAccelerationStructureHandle>&,Chaos::FQueryFastData&)override{throw FStop{ERefusal::Payload};}
 bool Sweep(const Chaos::TSpatialVisitorData<Chaos::FAccelerationStructureHandle>&,Chaos::FQueryFastData&)override{throw FStop{ERefusal::Payload};}
};
}
namespace {
FCapture CaptureImpl(UWorld& World,const MeasuredStrict::Request& Request,const IFence* Fence,
 const IProfileOwnerPublisher& Publisher){
 FCapture Out;Out.DiagnosticOnly=Fence==nullptr;
 if(!IsInGameThread()||!Request.acquisition)return Out;
 try{
  MeasuredStrict::Query Enclosure{};Need(MeasuredStrictMakeQuery(&Request,&Enclosure),ERefusal::Invalid);
  const FBox Box(FVector(Enclosure.min[0],Enclosure.min[1],Enclosure.min[2]),FVector(Enclosure.max[0],Enclosure.max[1],Enclosure.max[2]));
  Out.RequestedBox=Box;
  FWalkingQuery Walking;Need(ResolveWalkingQuery(World,Request,Publisher,Walking),ERefusal::Filter);
  Out.OwnerAgent=Walking.Owner.Agent;Out.OwnerIncarnation=Walking.Owner.Incarnation;
  Out.Profile=Walking.Owner.Profile;Out.WalkingFilter=Walking.Filter.ToString();
  TStrongObjectPtr<AActor> KeepOwner(Walking.Owner.Actor.Get());
  TStrongObjectPtr<UPrimitiveComponent> KeepVisual(Walking.Owner.Visual.Get()),KeepUpdated(Walking.Owner.Updated.Get());
  if(Fence){Out.Epoch=Fence->Read(World);Need(Out.Epoch.Valid()&&Out.Epoch.World==Request.world&&
   Out.Epoch.Geometry==Request.geometry&&Out.Epoch.Binding==Request.binding,ERefusal::Epoch);}
  auto* Scene=World.GetPhysicsScene();Need(Scene!=nullptr,ERefusal::Lock);
  {
   FRead Lock(Scene);Need(Lock.Held(),ERefusal::Lock);
   if(Fence)Need(Fence->Read(World)==Out.Epoch,ERefusal::Epoch);
   Need(ValidateWalkingQuery(World,Request,Publisher,Walking),ERefusal::Filter);
   const auto* Accel=Scene->GetSpacialAcceleration();Need(Accel&&Accel->GetType()==Chaos::ESpatialAcceleration::Collection,ERefusal::Payload);
   Out.Data=MakeUnique<MeasuredStrict::Snapshot>();Out.Data->acquisition=Request.acquisition;
   for(int J=0;J<3;++J){Out.Data->capturedQuery.min[J]=Box.Min[J];Out.Data->capturedQuery.max[J]=Box.Max[J];}
   Out.Data->world=Request.world;Out.Data->geometry=Request.geometry;Out.Data->binding=Request.binding;
   FCollector Collector(World,Lock,Out,Walking);
   Accel->Overlap(Chaos::FAABB3(Chaos::FVec3(Box.Min),Chaos::FVec3(Box.Max)),Collector);
   Need(ValidateWalkingQuery(World,Request,Publisher,Walking),ERefusal::Filter);
   if(Fence)Need(Fence->Read(World)==Out.Epoch,ERefusal::Epoch);
  }
  if(Fence)Need(Fence->Read(World)==Out.Epoch,ERefusal::Epoch);
  Need(ValidateWalkingQuery(World,Request,Publisher,Walking),ERefusal::Filter);
  Out.Refusal=ERefusal::None;Out.ObservedBoxEnumerationExhausted=true;
  Out.PublishedBoxEnumerationExhausted=Fence!=nullptr;
 }catch(const FStop& E){Out.Refusal=E.Why;}catch(...){Out.Refusal=ERefusal::Budget;}
 if(Out.Refusal!=ERefusal::None){Out.Data.Reset();Out.PublishedBoxEnumerationExhausted=false;Out.ObservedBoxEnumerationExhausted=false;}
 return Out;
}
}
FCapture CaptureBox(UWorld& W,const MeasuredStrict::Request& R,const IFence& F,const IProfileOwnerPublisher& P){
 return CaptureImpl(W,R,&F,P);
}
FCapture InspectWalkingBox(UWorld& W,const MeasuredStrict::Request& R,const IProfileOwnerPublisher& P){
 return CaptureImpl(W,R,nullptr,P);
}
bool EvaluateSweptSurface(UWorld& World,const MeasuredStrict::Request& Request,
 const IFence& Fence,const IProfileOwnerPublisher& Publisher,FCapture& Capture,MeasuredStrict::Evidence& Evidence){
 Evidence={};Capture=CaptureBox(World,Request,Fence,Publisher);
 if(Capture.Refusal!=ERefusal::None||Capture.DiagnosticOnly||!Capture.Data||!Capture.PublishedBoxEnumerationExhausted)return false;
 if(!(Fence.Read(World)==Capture.Epoch))return false;
 if(!MeasuredStrictCover(Capture.Data.Get(),&Request,&Evidence))return false;
 if(!(Fence.Read(World)==Capture.Epoch)){Evidence={};return false;}
 return Evidence.status==MeasuredStrict::Status::SurfaceClear;
 // Still no solid-volume, universal publisher or complete-world movement certificate.
}
}
