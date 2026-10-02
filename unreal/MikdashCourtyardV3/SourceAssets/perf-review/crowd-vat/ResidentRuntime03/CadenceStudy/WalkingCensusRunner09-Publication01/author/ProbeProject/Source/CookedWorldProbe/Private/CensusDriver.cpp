#include "CensusDriver.h"
#include "CookedWorldPort.h"
#include "MikdashCrowdField.h"
#include "Containers/Ticker.h"
#include "Engine/Engine.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture.h"
#include "EngineUtils.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Materials/MaterialInstanceConstant.h"
#include "Dom/JsonObject.h"
#include "HAL/PlatformFileManager.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformTime.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UObject/Package.h"
#include "UObject/UObjectIterator.h"

namespace {
FTSTicker::FDelegateHandle Handle;
double Started=0;
TSharedPtr<FJsonObject> Inputs,Run;
bool ReadJson(const FString& Path,TSharedPtr<FJsonObject>& Out){
 FString S;return FFileHelper::LoadFileToString(S,*Path)&&
 FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(S),Out)&&Out.IsValid();
}
bool Finish(const FString& Error,const TSharedPtr<FJsonObject>& Observation=nullptr){
 auto J=MakeShared<FJsonObject>();J->SetNumberField(TEXT("schema"),1);
 J->SetStringField(TEXT("status"),Error.IsEmpty()?TEXT("diagnostic_observed"):TEXT("refused"));
 J->SetStringField(TEXT("error"),Error);J->SetBoolField(TEXT("worldReady"),false);
 if(Run.IsValid())for(const TCHAR* K:{TEXT("nonce"),TEXT("manifest"),TEXT("seal"),TEXT("savePrefix")})
  J->SetStringField(K,Run->GetStringField(K));
 J->SetBoolField(TEXT("measuredCorrespondenceConditional"),true);
 if(Observation)J->SetObjectField(TEXT("observation"),Observation);
 FString S;FJsonSerializer::Serialize(J,TJsonWriterFactory<>::Create(&S));
 const FString Out=FPaths::ProjectDir()/TEXT("../native.json");
 auto& FS=FPlatformFileManager::Get().GetPlatformFile();
 const bool Saved=!FS.FileExists(*Out)&&FFileHelper::SaveStringToFile(S,*Out,FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
 FPlatformMisc::RequestExitWithStatus(false,(Saved&&Error.IsEmpty())?0:1);return false;
}
// Synchronous game-thread diagnostic only. Never supplied as IFence or retained
// across a tick; no promise about future writers or committed movement horizons.
struct FObservedOwner final:CookedWorldPort::IProfileOwnerPublisher {
 CookedWorldPort::FProfileOwner O;TWeakObjectPtr<AMikdashCrowdField> Crowd;
 FVector Anchor;int32 Index=INDEX_NONE;
 bool Resolve(const MeasuredStrict::Request& R,CookedWorldPort::FProfileOwner& Out)const override {
  auto* A=Crowd.Get();FVector P,V;float Rate=0,Scale=0;bool Idle=false;
  if(!IsInGameThread()||!A||R.binding!=O.Generation||R.profile!=O.Profile||
    !A->GetVatAgentState(Index,P,V,Rate,Scale,Idle)||!Idle||Scale!=1.f||Rate!=0.f||
    V!=FVector::ZeroVector||P!=Anchor||!A->GetActorTransform().Equals(FTransform::Identity,0))return false;
  Out=O;return true;
 }
};
bool Tick(float){
 if(FPlatformTime::Seconds()-Started>90.0)return Finish(TEXT("native_startup_deadline"));
 if(!GEngine)return true;
 UWorld* W=nullptr;
 for(const auto& C:GEngine->GetWorldContexts())if(C.World()&&C.World()->WorldType==EWorldType::Game){
  if(W)return Finish(TEXT("multiple_game_worlds"));W=C.World();
 }
 if(!W||!W->HasBegunPlay())return true;
 if(W->GetOutermost()->GetName()!=Inputs->GetStringField(TEXT("map")))return Finish(TEXT("wrong_map"));
 AMikdashCrowdField* Crowd=nullptr;int32 Count=0;
 for(TActorIterator<AMikdashCrowdField> It(W);It;++It){Crowd=*It;if(++Count>1)return Finish(TEXT("multiple_crowds"));}
 if(!Crowd||Crowd->GetTotalInstanceCount()==0)return true;
 if(Crowd->GetTotalInstanceCount()!=48||Crowd->GetEffectiveCrowdCount()!=48||
    Crowd->PoseMeshes.Num()!=2||!Crowd->bUseVertexAnimation||Crowd->FigureScaleMin!=1.f||Crowd->FigureScaleMax!=1.f||
    Crowd->GetActorEnableCollision()||!Crowd->GetActorTransform().Equals(FTransform::Identity,0))return Finish(TEXT("owner_scope"));
 const auto& Variants=Inputs->GetArrayField(TEXT("variants"));
 if(Variants.Num()!=2)return Finish(TEXT("variant_config"));
 TArray<UHierarchicalInstancedStaticMeshComponent*> Components;Crowd->GetComponents(Components);
 UHierarchicalInstancedStaticMeshComponent* Visuals[2]={nullptr,nullptr};
 for(int32 Pose=0;Pose<2;++Pose){
  const auto V=Variants[Pose]->AsObject();
  if(!Crowd->PoseMeshes[Pose]||Crowd->PoseMeshes[Pose]->GetPathName()!=V->GetStringField(TEXT("mesh")))return Finish(TEXT("pose_asset"));
  for(auto* C:Components)if(C->GetInstanceCount()>0&&C->GetStaticMesh()==Crowd->PoseMeshes[Pose]){
   if(Visuals[Pose])return Finish(TEXT("ambiguous_pose_component"));Visuals[Pose]=C;
  }
  auto* C=Visuals[Pose];
  if(!C||C->GetInstanceCount()!=24||C->GetCollisionEnabled()!=ECollisionEnabled::NoCollision||
    !C->GetComponentTransform().Equals(FTransform::Identity,0)||C->GetNumMaterials()!=6)return Finish(TEXT("component_scope"));
  const auto& Slots=V->GetArrayField(TEXT("slots"));if(Slots.Num()!=6)return Finish(TEXT("slot_config"));
  for(int32 S=0;S<6;++S){
   auto* M=Cast<UMaterialInstanceConstant>(C->GetMaterial(S));
   if(!M||M!=C->GetStaticMesh()->GetMaterial(S)||M->GetPathName()!=Slots[S]->AsArray()[2]->AsString())return Finish(TEXT("material_override"));
   const auto Params=V->GetObjectField(TEXT("parameters"))->GetObjectField(M->GetName());
   for(const auto& Pair:Params->Values)if(Pair.Value->Type==EJson::String){
    UTexture* T=nullptr;
    if(!M->GetTextureParameterValue(FHashedMaterialParameterInfo(FName(*Pair.Key)),T)||!T||T->GetPathName()!=Pair.Value->AsString())return Finish(TEXT("texture_binding"));
   }
  }
 }
 for(auto* C:Components)if(C->GetInstanceCount()>0&&C!=Visuals[0]&&C!=Visuals[1])return Finish(TEXT("extra_instances"));
 // Capture the actual resident anchor with exact doubles; no nearest-cm rounding.
 for(int32 I=0;I<48;++I){
  FVector P,V;float Rate=0,Scale=0;bool Idle=false;
  if(!Crowd->GetVatAgentState(I,P,V,Rate,Scale,Idle))return Finish(TEXT("agent_readback"));
  if(!Idle||Rate!=0.f||V!=FVector::ZeroVector||Scale!=1.f||P.ContainsNaN())continue;
  const int32 Pose=I%2,Local=I/2;auto* Visual=Visuals[Pose];FTransform T;
  if(!Visual->GetInstanceTransform(Local,T,true)||T.ContainsNaN()||T.GetLocation()!=FVector(FVector3f(P))||
     T.GetScale3D()!=FVector::OneVector||T.GetRotation().X!=0.0||T.GetRotation().Y!=0.0)return Finish(TEXT("instance_mapping"));
  FObservedOwner Publisher;Publisher.Crowd=Crowd;Publisher.Index=I;Publisher.Anchor=P;
  auto& O=Publisher.O;O.Kind=CookedWorldPort::EOwnerKind::VatInstance;
  O.Agent=I+1;O.Incarnation=1;O.Generation=1;O.InstanceGeneration=1;
  O.Profile=static_cast<int32>(Variants[Pose]->AsObject()->GetNumberField(TEXT("profile")));
  O.Evidence=Inputs->GetStringField(TEXT("evidence"));O.World=W;O.Actor=Crowd;O.Visual=Visual;O.Instance=Local;
  MeasuredStrict::Request R{};R.acquisition=1;R.world=W->GetUniqueID();R.geometry=1;R.binding=1;R.profile=O.Profile;
  for(auto& Q:R.from)Q={0,1};for(auto& Q:R.to)Q={0,1};for(auto& Q:R.root)Q={0,1};
  R.maxSlope={1,2};R.heightTolerance={1,1};R.contactBelowRoot={1,1};
  // ISM stores its matrix as float32. Query around the read-back rendered anchor,
  // not the unquantized CPU agent position; keep that separate for revalidation.
  const FVector RenderAnchor=T.GetLocation();
  R.origin[0]=RenderAnchor.X;R.origin[1]=RenderAnchor.Y;R.origin[2]=RenderAnchor.Z;
  auto Capture=CookedWorldPort::InspectWalkingBox(*W,R,Publisher);
  TSharedPtr<FJsonObject> Result;
  if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(CookedWorldPort::DescribeWalkingCapture(Capture)),Result))return Finish(TEXT("serialize_capture"));
  auto Obs=MakeShared<FJsonObject>();Obs->SetObjectField(TEXT("capture"),Result);
  Obs->SetStringField(TEXT("map"),W->GetOutermost()->GetName());Obs->SetNumberField(TEXT("residents"),48);
  Obs->SetNumberField(TEXT("agentIndex"),I);Obs->SetNumberField(TEXT("instance"),Local);Obs->SetNumberField(TEXT("pose"),Pose);
  Obs->SetNumberField(TEXT("profile"),O.Profile);Obs->SetNumberField(TEXT("scale"),Scale);Obs->SetBoolField(TEXT("idle"),true);
  Obs->SetStringField(TEXT("mesh"),Visual->GetStaticMesh()->GetPathName());Obs->SetStringField(TEXT("evidence"),O.Evidence);
  TArray<TSharedPtr<FJsonValue>> Origin;for(double X:R.origin)Origin.Add(MakeShared<FJsonValueNumber>(X));Obs->SetArrayField(TEXT("origin"),Origin);
  TArray<TSharedPtr<FJsonValue>> Packages;int32 Seen=0;
  const auto Allowed=Inputs->GetObjectField(TEXT("packages"));
  TSet<FString> Names;for(const auto& Pair:Allowed->Values)Names.Add(Pair.Value->AsObject()->GetStringField(TEXT("package")));
  for(TObjectIterator<UPackage> It;It;++It){
   if(++Seen>32768)return Finish(TEXT("package_iteration_budget"));const FString Name=It->GetName();
   if(Name.StartsWith(TEXT("/Game/"))){if(!Names.Contains(Name))return Finish(TEXT("unlisted_project_package"));Packages.Add(MakeShared<FJsonValueString>(Name));}
  }
  Obs->SetArrayField(TEXT("loadedProjectPackages"),Packages);
  // Geometry/filter refusal is a valid diagnostic observation, never an acceptance.
  return Finish(FString(),Obs);
 }
 return true;
}
}
void StartWalkingCensus09(){
 if(!FParse::Param(FCommandLine::Get(),TEXT("WalkingCensus09")))return;
 Started=FPlatformTime::Seconds();
 if(!ReadJson(FPaths::ProjectDir()/TEXT("CensusInputs.json"),Inputs)||
    !ReadJson(FPaths::ProjectDir()/TEXT("CensusRun.json"),Run)){Finish(TEXT("missing_config"));return;}
 Handle=FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateStatic(&Tick));
}
void StopWalkingCensus09(){if(Handle.IsValid())FTSTicker::RemoveTicker(Handle);}
