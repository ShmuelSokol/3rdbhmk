#include "KohenClothInternal.h"
#include "ChaosClothAsset/CollectionClothFacade.h"
#include "ChaosClothAsset/CollectionClothSimPatternFacade.h"
#include "ChaosClothAsset/CollectionClothRenderPatternFacade.h"
#include "ChaosClothAsset/ClothAssetSKMClothingAsset.h"
#include "ChaosClothAsset/ClothSimulationModel.h"
#include "ChaosClothAsset/ClothEngineTools.h"
#include "ChaosCloth/ChaosClothConfig.h"
#include "ChaosCloth/ChaosClothingSimulationConfig.h"
#include "Chaos/CollectionPropertyFacade.h"
#include "GeometryCollection/ManagedArrayCollection.h"
#include "ClothingAssetBase.h"
#include "PointWeightMap.h"
#include "Utils/ClothingMeshUtils.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "SkinnedAssetCompiler.h"
#include "Materials/MaterialInterface.h"
#include "Animation/Skeleton.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/BufferArchive.h"
#include "Misc/FileHelper.h"
#include "Misc/SecureHash.h"
#include "HAL/FileManager.h"

namespace KohenCloth
{
#define REQUIRE(C, M) do { if (!(C)) { Error = TEXT(M); return false; } } while (false)
FString JsonText(const TSharedRef<FJsonObject>& O)
{ FString T; FJsonSerializer::Serialize(O, TJsonWriterFactory<>::Create(&T)); return T; }
bool WriteJson(const FString& Path, const TSharedRef<FJsonObject>& O)
{
    if (IFileManager::Get().FileExists(*Path)) return false;
    const FString Temp = Path + TEXT(".") + FGuid::NewGuid().ToString() + TEXT(".tmp");
    return FFileHelper::SaveStringToFile(JsonText(O), *Temp, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM)
        && IFileManager::Get().Move(*Path, *Temp, false, false, false, true);
}
bool WriteBinary(const FString& Path, const TArray<float>& Floats)
{
    if (IFileManager::Get().FileExists(*Path)) return false;
    const FString Temp = Path + TEXT(".") + FGuid::NewGuid().ToString() + TEXT(".tmp");
    const TArrayView<const uint8> Bytes(reinterpret_cast<const uint8*>(Floats.GetData()), Floats.Num()*sizeof(float));
    return FFileHelper::SaveArrayToFile(Bytes, *Temp) && IFileManager::Get().Move(*Path,*Temp,false,false,false,true);
}
FString Digest(USkeletalMesh* Mesh, int32 ExcludedSection)
{
    FBufferArchive B;
    auto Name = [&](FString V) { B << V; };
    Name(Mesh->GetSkeleton() ? Mesh->GetSkeleton()->GetPathName() : TEXT("none"));
    const auto& R = Mesh->GetRefSkeleton();
    for (int32 I=0; I<R.GetNum(); ++I)
    {
        Name(R.GetBoneName(I).ToString());
        int32 Parent=R.GetParentIndex(I); B << Parent;
        FTransform T=R.GetRefBonePose()[I]; B << T;
    }
    for (const auto& Mat: Mesh->GetMaterials())
    { Name(Mat.ImportedMaterialSlotName.ToString()); Name(Mat.MaterialSlotName.ToString()); Name(Mat.MaterialInterface ? Mat.MaterialInterface->GetPathName() : TEXT("none")); }
    const auto& L=Mesh->GetImportedModel()->LODModels[0];
    for (int32 S=0; S<L.Sections.Num(); ++S)
    {
        if (S==ExcludedSection) continue;
        const auto& Sec=L.Sections[S];
        int32 Material=Sec.MaterialIndex; B << Material;
        for (auto Bone: Sec.BoneMap) B << Bone;
        for (auto V: Sec.SoftVertices)
        {
            B << V.Position; B << V.TangentX; B << V.TangentY; B << V.TangentZ; B << V.Color;
            for (auto UV: V.UVs) B << UV;
            B.Serialize(V.InfluenceBones,sizeof(V.InfluenceBones)); B.Serialize(V.InfluenceWeights,sizeof(V.InfluenceWeights));
        }
        for (uint32 I=0; I<Sec.NumTriangles*3; ++I)
        { uint32 Index=L.IndexBuffer[Sec.BaseIndex+I]-Sec.BaseVertexIndex; B << Index; }
    }
    FSHAHash Hash; FSHA1::HashBuffer(B.GetData(),B.Num(),Hash.Hash); return Hash.ToString();
}
static bool Vector(const TSharedPtr<FJsonValue>& V,FVector3f& Out)
{
    const TArray<TSharedPtr<FJsonValue>>* A;
    if (!V.IsValid() || !V->TryGetArray(A) || A->Num()!=3) return false;
    double X,Y,Z;
    if (!(*A)[0]->TryGetNumber(X)||!(*A)[1]->TryGetNumber(Y)||!(*A)[2]->TryGetNumber(Z)) return false;
    Out=FVector3f(X,Y,Z); return !Out.ContainsNaN();
}
static void Finish(USkinnedAsset* Asset)
{ TArray<USkinnedAsset*> A{Asset}; FSkinnedAssetCompilingManager::Get().FinishCompilation(A); }
FVector3f Embed(const FMeshToMeshVertData& M,TConstArrayView<FVector3f> P,TConstArrayView<FVector3f> N)
{
    const FVector4f B=M.PositionBaryCoordsAndDist;
    FVector3f V(0,0,0);
    for(int32 K=0;K<3;++K) V+=B[K]*(P[M.SourceMeshVertIndices[K]]+B.W*N[M.SourceMeshVertIndices[K]]);
    return V;
}
bool ValidateMapping(const FStudy& S,const TArray<FMeshToMeshVertData>& Maps,FString& Error)
{
    const auto& Sec=S.Clone->GetImportedModel()->LODModels[0].Sections[S.Section];
    REQUIRE(Maps.Num()==Sec.SoftVertices.Num(),"Mapping count differs from render section");
    for (int32 I=0;I<Maps.Num();++I)
    {
        const auto& M=Maps[I];
        for(int32 K=0;K<3;++K) REQUIRE(M.SourceMeshVertIndices[K]<S.OuterCount,"Cross-layer render mapping refused");
        REQUIRE(!M.PositionBaryCoordsAndDist.ContainsNaN() && !M.NormalBaryCoordsAndDist.ContainsNaN() && !M.TangentBaryCoordsAndDist.ContainsNaN(),"Nonfinite deformer mapping");
        REQUIRE(FMath::IsNearlyEqual(M.Weight,1.f,1.e-5f),"Expected single influence mapping");
        REQUIRE(FVector3f::Distance(Embed(M,S.Points,S.Normals),Sec.SoftVertices[I].Position)<.01f,"Render rest reconstruction exceeds0.01cm");
        FMeshToMeshVertData Tip=M; Tip.PositionBaryCoordsAndDist=M.NormalBaryCoordsAndDist;
        REQUIRE(FVector3f::Distance(Embed(Tip,S.Points,S.Normals),Sec.SoftVertices[I].Position+FVector3f(Sec.SoftVertices[I].TangentZ))<.01f,"Render normal-tip reconstruction exceeds0.01cm");
        Tip.PositionBaryCoordsAndDist=M.TangentBaryCoordsAndDist;
        REQUIRE(FVector3f::Distance(Embed(Tip,S.Points,S.Normals),Sec.SoftVertices[I].Position+Sec.SoftVertices[I].TangentX)<.01f,"Render tangent-tip reconstruction exceeds0.01cm");
    }
    return true;
}
bool Build(USkeletalMesh* Source,const FString& Input,FStudy& S,FString& Error)
{
    using namespace UE::Chaos::ClothAsset;
    REQUIRE(Source && Source->GetPathName().StartsWith(TEXT("/Game/KohenClothFeasibilityV1/Import/")),"Only isolated fresh source import permitted");
    Finish(Source);
    REQUIRE(Source->GetImportedModel() && Source->GetImportedModel()->LODModels.Num()==1 && Source->GetMeshClothingAssets().IsEmpty(),"Source must have one LOD and no cloth");
    REQUIRE(Source->GetRefSkeleton().GetNum()==27,"Expected preserved27-bone rig");
    FString Text; TSharedPtr<FJsonObject> J;
    REQUIRE(FFileHelper::LoadFileToString(Text,*Input) && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),J) && J.IsValid(),"Input JSON could not be read");
    REQUIRE(J->GetStringField(TEXT("schema"))==TEXT("kohen-cloth-feasibility-v1") && J->GetStringField(TEXT("selectedMaterial"))==TEXT("KG_Meil"),"Unsupported input schema/material");
    S.SourceDigest=Digest(Source);
    S.Clone.Reset(DuplicateObject<USkeletalMesh>(Source,GetTransientPackage(),MakeUniqueObjectName(GetTransientPackage(),USkeletalMesh::StaticClass(),TEXT("KohenClothClone"))));
    REQUIRE(S.Clone.IsValid(),"Transient duplication failed");
    Finish(S.Clone.Get());
    REQUIRE(Digest(S.Clone.Get())==S.SourceDigest,"Clone differs from immutable source");
    const auto& Ref=S.Clone->GetRefSkeleton();
    for(int32 I=0;I<27;++I)
    { const int32 P=Ref.GetParentIndex(I); S.RefGlobal.Add(P==INDEX_NONE?Ref.GetRefBonePose()[I]:Ref.GetRefBonePose()[I]*S.RefGlobal[P]); }
    const auto& JB=J->GetArrayField(TEXT("bones")); REQUIRE(JB.Num()==27,"Input bone count differs");
    TArray<FVector3f> AuthorBones;
    for(const auto& V:JB)
    {
        const auto O=V->AsObject(); REQUIRE(O.IsValid(),"Invalid bone object");
        const int32 N=Ref.FindBoneIndex(FName(*O->GetStringField(TEXT("name")))); REQUIRE(N!=INDEX_NONE && !S.BoneRemap.Contains(N),"Input bone names differ");
        S.BoneRemap.Add(N); FVector3f P;
        REQUIRE(Vector(O->TryGetField(TEXT("positionCm")),P),"Invalid bone position"); AuthorBones.Add(P);
    }
    int32 Fits=0; const int32 Permutations[6][3]={{0,1,2},{0,2,1},{1,0,2},{1,2,0},{2,0,1},{2,1,0}};
    for(const auto& P:Permutations) for(int32 Mask=0;Mask<8;++Mask)
    {
        const FVector3f Sign((Mask&1)?1:-1,(Mask&2)?1:-1,(Mask&4)?1:-1); float MaxError=0;
        for(int32 I=0;I<27;++I)
        { const FVector3f A=AuthorBones[I]; MaxError=FMath::Max(MaxError,FVector3f::Distance(FVector3f(A[P[0]],A[P[1]],A[P[2]])*Sign,FVector3f(S.RefGlobal[S.BoneRemap[I]].GetTranslation()))); }
        if(MaxError<.05f) { ++Fits; S.Perm=FIntVector(P[0],P[1],P[2]); S.Signs=Sign; }
    }
    REQUIRE(Fits==1,"No unique source-to-native axis mapping within0.05cm");
    auto& L=S.Clone->GetImportedModel()->LODModels[0];
    for(int32 I=0;I<L.Sections.Num();++I)
    {
        REQUIRE(!L.Sections[I].HasClothingData(),"Source has existing cloth mappings");
        if(S.Clone->GetMaterials()[L.Sections[I].MaterialIndex].ImportedMaterialSlotName==TEXT("KG_Meil"))
        { REQUIRE(S.Section==INDEX_NONE,"Split KG_Meil section needs separate review"); S.Section=I; }
    }
    REQUIRE(S.Section!=INDEX_NONE,"No KG_Meil section");
    S.UnboundDigest=Digest(S.Clone.Get(),S.Section);
    const auto& Sec=L.Sections[S.Section];
    // Exact multiplicities; import splitting/reordering is never treated as proven correspondence.
    auto Key=[](const FVector3f& P){return FString::Printf(TEXT("%lld,%lld,%lld"),FMath::RoundToInt64(P.X*200),FMath::RoundToInt64(P.Y*200),FMath::RoundToInt64(P.Z*200));};
    TMap<FString,int32> Counts;
    for(const auto& V:J->GetArrayField(TEXT("selectedSourceRenderPositionsCm")))
    { FVector3f P; REQUIRE(Vector(V,P),"Invalid source render position"); ++Counts.FindOrAdd(Key(S.ToNative(P))); }
    for(const auto& V:Sec.SoftVertices) { int32* N=Counts.Find(Key(V.Position)); REQUIRE(N && *N>0,"Imported garment render positions differ"); --*N; }
    for(const auto& It:Counts) REQUIRE(It.Value==0,"Imported garment vertex count differs");
    const auto& JP=J->GetArrayField(TEXT("patterns")); REQUIRE(JP.Num()==6,"Expected six physical patterns");
    const TCHAR* Names[]={TEXT("Meil"),TEXT("Ketonet"),TEXT("ShinR"),TEXT("FootR"),TEXT("ShinL"),TEXT("FootL")};
    const FVector3f X=S.ToNative(FVector3f(1,0,0)),Y=S.ToNative(FVector3f(0,1,0)),Z=S.ToNative(FVector3f(0,0,1));
    const bool Mirror=FVector3f::DotProduct(FVector3f::CrossProduct(X,Y),Z)<0;
    for(int32 N=0;N<JP.Num();++N)
    {
        auto O=JP[N]->AsObject(); REQUIRE(O.IsValid(),"Invalid pattern"); FPattern P;
        P.Name=O->GetStringField(TEXT("name")); P.Dynamic=O->GetBoolField(TEXT("dynamic")); P.Start=S.Points.Num();
        REQUIRE(P.Name==Names[N] && P.Dynamic==(N==0),"Only reviewed outer-dynamic/inner-kinematic control is enabled");
        for(const auto& V:O->GetArrayField(TEXT("verticesCm")))
        { FVector3f A; REQUIRE(Vector(V,A),"Nonfinite physical point"); P.Points.Add(S.ToNative(A)); }
        REQUIRE(P.Points.Num()>0 && P.Start+P.Points.Num()<=16384,"Physical vertex budget exceeded");
        for(const auto& V:O->GetArrayField(TEXT("faces")))
        {
            const auto& A=V->AsArray(); REQUIRE(A.Num()==3,"Face must have three indices");
            uint32 T[3]; for(int32 K=0;K<3;++K) { double D=A[K]->AsNumber(); REQUIRE(D==FMath::FloorToDouble(D) && D>=0 && D<P.Points.Num(),"Invalid triangle index"); T[K]=uint32(D); }
            if(Mirror) Swap(T[1],T[2]);
            REQUIRE(FVector3f::CrossProduct(P.Points[T[1]]-P.Points[T[0]],P.Points[T[2]]-P.Points[T[0]]).SizeSquared()>1.e-12f,"Degenerate physical triangle");
            for(int32 K=0;K<3;++K) { P.Indices.Add(T[K]); S.Indices.Add(T[K]+P.Start); }
        }
        const auto& Inf=O->GetArrayField(TEXT("boneInfluences")); const auto& MD=O->GetArrayField(TEXT("maxDistanceCm"));
        REQUIRE(Inf.Num()==P.Points.Num() && MD.Num()==P.Points.Num(),"Physical attribute length differs");
        for(int32 I=0;I<Inf.Num();++I)
        {
            TArray<int32> BI; TArray<float> BW; float Sum=0;
            for(const auto& IV:Inf[I]->AsArray())
            {
                const auto& Pair=IV->AsArray(); REQUIRE(Pair.Num()==2,"Invalid influence");
                const double Bone=Pair[0]->AsNumber(); const float Weight=Pair[1]->AsNumber();
                REQUIRE(Bone>=0 && Bone<27 && Bone==FMath::FloorToDouble(Bone) && FMath::IsFinite(Weight) && Weight>0,"Invalid physical bone weight");
                BI.Add(S.BoneRemap[int32(Bone)]); BW.Add(Weight); Sum+=Weight;
            }
            REQUIRE(FMath::IsNearlyEqual(Sum,1.f,1.e-5f),"Unnormalized physical skin weights");
            const float Max=MD[I]->AsNumber(); REQUIRE(FMath::IsFinite(Max) && Max>=0 && Max<=60 && (N==0 || Max==0),"Invalid control pin map");
            P.Bones.Add(MoveTemp(BI)); P.Weights.Add(MoveTemp(BW)); P.MaxDistance.Add(Max);
        }
        S.Points.Append(P.Points); if(N==0) S.OuterCount=P.Points.Num(); S.Patterns.Add(MoveTemp(P));
    }
    TStrongObjectPtr<UChaosClothConfig> C(NewObject<UChaosClothConfig>());
    const auto Physics=J->GetObjectField(TEXT("studyPhysics"));
    REQUIRE(Physics.IsValid() && Physics->GetNumberField(TEXT("densityKgM2"))==.35 && Physics->GetNumberField(TEXT("minParticleMassKg"))==.0001,"Unreviewed study mass parameters");
    REQUIRE(Physics->GetBoolField(TEXT("geodesicTethers")) && Physics->GetNumberField(TEXT("tetherStiffness"))==1. && Physics->GetNumberField(TEXT("tetherScale"))==1. && Physics->GetNumberField(TEXT("frameSchemaVersion"))==2.,"Unreviewed tether/control configuration");
    // Authored feasibility material: 350g/m2, not a measured/historical textile claim.
    C->MassMode=EClothMassMode::Density; C->Density=.35f; C->MinPerParticleMass=.0001f;
    C->TetherStiffness={1.f,1.f}; C->TetherScale={1.f,1.f}; C->bUseGeodesicDistance=true;
    TStrongObjectPtr<UChaosClothSharedSimConfig> Shared(NewObject<UChaosClothSharedSimConfig>());
    C->bUseSelfCollisions=true; C->SelfCollisionThickness=.5f; C->bUseGravityOverride=true;
    C->Gravity=FVector(S.ToNative(FVector3f(0,0,-980.665f)));
    C->AnimDriveStiffness={0.f,0.f}; C->AnimDriveDamping={0.f,0.f};
    C->bUseBendingElements=true; C->BendingStiffnessWeighted={.1f,.1f};
    Shared->IterationCount=5; Shared->MaxIterationCount=5;
    Chaos::FClothingSimulationConfig Config; Config.Initialize(C.Get(),Shared.Get(),false);
    TSharedRef<FManagedArrayCollection> Collection=MakeShared<FManagedArrayCollection>(*Config.GetPropertyCollection(0));
    Chaos::Softs::FCollectionPropertyMutableFacade Properties(Collection);
    Properties.AddValue(FName(TEXT("SelfCollideAgainstAllKinematicVertices")),true);
    FCollectionClothFacade Cloth(Collection); Cloth.DefineSchema(EClothCollectionExtendedSchemas::RenderDeformer);
    Cloth.SetSkeletalMeshSoftObjectPathName(FSoftObjectPath(Source)); Cloth.SetReferenceBoneName(TEXT("pelvis"));
    for(const auto& P:S.Patterns)
    {
        TArray<FVector2f> UV; for(const auto& V:P.Points) UV.Add(FVector2f(V.X,V.Y));
        // No anisotropic/pattern-space material model: simulation uses authored 3D rest shape.
        auto Pattern=Cloth.AddGetSimPattern(); Pattern.Initialize(UV,P.Points,P.Indices);
        for(int32 I=0;I<P.Points.Num();++I)
        { Cloth.GetSimBoneIndices()[P.Start+I]=P.Bones[I]; Cloth.GetSimBoneWeights()[P.Start+I]=P.Weights[I]; }
    }
    Cloth.AddWeightMap(TEXT("MaxDistance"));
    for(const auto& P:S.Patterns) for(int32 I=0;I<P.Points.Num();++I) Cloth.GetWeightMap(TEXT("MaxDistance"))[P.Start+I]=P.MaxDistance[I];
    FClothEngineTools::GenerateTethers(Collection,FName(TEXT("MaxDistance")),true);
    const auto Anchors=Cloth.GetTetherKinematicIndex();
    const auto Lengths=Cloth.GetTetherReferenceLength();
    REQUIRE(Anchors.Num()==S.Points.Num() && Lengths.Num()==S.Points.Num(),"Tether attribute count mismatch");
    for(int32 I=0;I<S.Points.Num();++I)
    {
        REQUIRE(Anchors[I].Num()==Lengths[I].Num(),"Tether length/anchor mismatch");
        const bool Movable=I<S.OuterCount && S.Patterns[0].MaxDistance[I]>0;
        REQUIRE(Movable ? Anchors[I].Num()>0 : Anchors[I].Num()==0,"Missing dynamic tether or tether on kinematic particle");
        TSet<int32> Unique;
        for(int32 K=0;K<Anchors[I].Num();++K)
        {
            const int32 A=Anchors[I][K]; const float Len=Lengths[I][K];
            REQUIRE(A>=0 && A<S.OuterCount && S.Patterns[0].MaxDistance[A]==0 && !Unique.Contains(A),"Invalid/cross-layer/nonfixed tether anchor");
            REQUIRE(FMath::IsFinite(Len) && Len>0 && Len+.01f>=FVector3f::Distance(S.Points[I],S.Points[A]),"Invalid geodesic tether length");
            Unique.Add(A); ++S.TetherCount;
        }
        S.TetherAnchors.Add(Anchors[I]); S.TetherLengths.Add(Lengths[I]);
    }
    REQUIRE(S.TetherCount>0,"No authored tethers generated");
    const ClothingMeshUtils::ClothMeshDesc Physical(S.Points,S.Indices);
    S.Normals.Append(Physical.GetNormals().GetData(),Physical.GetNormals().Num());
    TArray<FVector3f> RP,RN,RT; TArray<uint32> RI;
    for(const auto& V:Sec.SoftVertices) { RP.Add(V.Position); RN.Add(FVector3f(V.TangentZ)); RT.Add(V.TangentX); }
    for(uint32 I=0;I<Sec.NumTriangles*3;++I) RI.Add(L.IndexBuffer[Sec.BaseIndex+I]-Sec.BaseVertexIndex);
    const ClothingMeshUtils::ClothMeshDesc Target(RP,RN,RT,RI);
    FPointWeightMap MaxDistances(Cloth.GetWeightMap(TEXT("MaxDistance")));
    ClothingMeshUtils::FMeshToMeshFilterSet Filter;
    for(int32 I=0;I<S.Patterns[0].Indices.Num()/3;++I) Filter.SourceTriangles.Add(I);
    for(int32 I=0;I<RP.Num();++I) Filter.TargetVertices.Add(I);
    ClothingMeshUtils::GenerateMeshToMeshVertData(S.Mapping,Target,Physical,&MaxDistances,true,false,100.f,{Filter});
    REQUIRE(ValidateMapping(S,S.Mapping,Error),"Generated render mapping failed outer-only/rest validator");
    auto Render=Cloth.AddGetRenderPattern(); Render.SetNumRenderVertices(RP.Num()); Render.SetNumRenderFaces(RI.Num()/3); Render.SetRenderDeformerNumInfluences(1);
    Render.SetRenderMaterialSoftObjectPathName(FSoftObjectPath(S.Clone->GetMaterials()[Sec.MaterialIndex].MaterialInterface));
    for(int32 I=0;I<RP.Num();++I)
    {
        const auto& V=Sec.SoftVertices[I]; const auto& M=S.Mapping[I];
        Render.GetRenderPosition()[I]=V.Position; Render.GetRenderNormal()[I]=RN[I];
        Render.GetRenderTangentU()[I]=V.TangentX; Render.GetRenderTangentV()[I]=V.TangentY;
        Render.GetRenderUVs()[I]={V.UVs[0]}; Render.GetRenderColor()[I]=FLinearColor(V.Color);
        for(int32 K=0;K<MAX_TOTAL_INFLUENCES;++K) if(V.InfluenceWeights[K])
        { Render.GetRenderBoneIndices()[I].Add(Sec.BoneMap[V.InfluenceBones[K]]); Render.GetRenderBoneWeights()[I].Add(float(V.InfluenceWeights[K])/65535.f); }
        Render.GetRenderDeformerPositionBaryCoordsAndDist()[I]={M.PositionBaryCoordsAndDist};
        Render.GetRenderDeformerNormalBaryCoordsAndDist()[I]={M.NormalBaryCoordsAndDist};
        Render.GetRenderDeformerTangentBaryCoordsAndDist()[I]={M.TangentBaryCoordsAndDist};
        Render.GetRenderDeformerSimIndices3D()[I]={FIntVector3(M.SourceMeshVertIndices[0],M.SourceMeshVertIndices[1],M.SourceMeshVertIndices[2])};
        Render.GetRenderDeformerWeight()[I]={M.Weight}; Render.GetRenderDeformerSkinningBlend()[I]=float(M.SourceMeshVertIndices[3])/65535.f;
    }
    for(int32 I=0;I<RI.Num()/3;++I) Render.GetRenderIndices()[I]=FIntVector3(RI[I*3],RI[I*3+1],RI[I*3+2]);
    S.Cloth.Reset(NewObject<UChaosClothAsset>(GetTransientPackage(),NAME_None,RF_Transient));
    TArray<TSharedRef<const FManagedArrayCollection>> Collections{Collection}; FText BuildError,Verbose;
    S.Cloth->Build(Collections,nullptr,&BuildError,&Verbose); Finish(S.Cloth.Get());
    REQUIRE(BuildError.IsEmpty() && S.Cloth->HasValidClothSimulationModels(),"Cloth asset Build failed; no binding attempted");
    const auto Model=S.Cloth->GetClothSimulationModel();
    REQUIRE(Model.IsValid() && Model->GetNumVertices(0)==S.Points.Num() && Model->GetIndices(0).Num()==S.Indices.Num(),"Built simulation model topology differs");
    int32 BuiltTethers=0; TSet<uint64> BuiltPairs;
    for(const auto& Batch:Model->GetTethers(0)) for(const auto& T:Batch)
    {
        const int32 A=T.Get<0>(), D=T.Get<1>();
        REQUIRE(D>=0 && D<S.OuterCount,"Built tether dynamic index invalid");
        const int32 K=S.TetherAnchors[D].Find(A);
        REQUIRE(K!=INDEX_NONE && FMath::IsNearlyEqual(S.TetherLengths[D][K],T.Get<2>(),.001f),"Built tether differs from validated collection");
        const uint64 Pair=(uint64(uint32(D))<<32)|uint32(A);
        REQUIRE(!BuiltPairs.Contains(Pair),"Duplicate built tether"); BuiltPairs.Add(Pair);
        ++BuiltTethers;
    }
    REQUIRE(BuiltTethers==S.TetherCount,"Built tether count differs");
    for(int32 I=0;I<S.Points.Num();++I) REQUIRE(FVector3f::Distance(Model->GetPositions(0)[I],S.Points[I])<.001f,"Built physical vertex order differs");
    for(int32 I=0;I<S.Indices.Num();++I) REQUIRE(Model->GetIndices(0)[I]==S.Indices[I],"Built physical triangle order differs");
    auto* Wrapper=NewObject<UChaosClothAssetSKMClothingAsset>(S.Clone.Get()); Wrapper->SetAsset(S.Cloth.Get()); S.Clone->AddClothingAsset(Wrapper);
    UClothingAssetBase* Base=Wrapper;
    REQUIRE(Base->BindToSkeletalMesh(S.Clone.Get(),0,S.Section,0),"Native binding returned false"); Finish(S.Clone.Get());
    const auto& Bound=S.Clone->GetImportedModel()->LODModels[0].Sections[S.Section];
    REQUIRE(Bound.ClothMappingDataLODs.Num()==1 && ValidateMapping(S,Bound.ClothMappingDataLODs[0],Error),"Bound mapping missing/cross-layer/invalid");
    for(int32 I=0;I<S.Mapping.Num();++I)
    {
        const auto& A=S.Mapping[I]; const auto& B=Bound.ClothMappingDataLODs[0][I];
        REQUIRE(A.PositionBaryCoordsAndDist==B.PositionBaryCoordsAndDist && A.NormalBaryCoordsAndDist==B.NormalBaryCoordsAndDist && A.TangentBaryCoordsAndDist==B.TangentBaryCoordsAndDist,"Native binding regenerated/reordered mapping");
        for(int32 K=0;K<4;++K) REQUIRE(A.SourceMeshVertIndices[K]==B.SourceMeshVertIndices[K],"Native binding changed mapping indices/blend");
    }
    REQUIRE(Digest(Source)==S.SourceDigest && Source->GetMeshClothingAssets().IsEmpty(),"Immutable source changed");
    REQUIRE(Digest(S.Clone.Get(),S.Section)==S.UnboundDigest && S.Clone->GetSkeleton()==Source->GetSkeleton(),"Head/rig/noncloth sections changed");
    return true;
}
#undef REQUIRE
}
