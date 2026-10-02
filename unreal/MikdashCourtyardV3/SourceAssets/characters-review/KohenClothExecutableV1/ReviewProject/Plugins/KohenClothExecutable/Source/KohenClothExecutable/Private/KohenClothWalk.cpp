#include "KohenClothExecutableLibrary.h"
#include "KohenClothInternal.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Components/SkeletalMeshComponent.h"
#include "ClothingSimulationInstance.h"
#include "ClothingSystemRuntimeTypes.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "PreviewScene.h"
#include "Modules/ModuleManager.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Misc/ScopeExit.h"
#include "HAL/PlatformTime.h"
#include "HAL/IConsoleManager.h"
#include "Utils/ClothingMeshUtils.h"

IMPLEMENT_MODULE(FDefaultModuleImpl,KohenClothExecutable)
namespace KohenCloth
{
static TArray<TSharedPtr<FJsonValue>> Vectors(TConstArrayView<FVector3f> V)
{
    TArray<TSharedPtr<FJsonValue>> A;
    for(const auto& P:V)
    { A.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(P.X),MakeShared<FJsonValueNumber>(P.Y),MakeShared<FJsonValueNumber>(P.Z)})); }
    return A;
}
static FVector3f Skin(const FVector3f& P,const TArray<int32>& Bones,const TArray<float>& Weights,
                     const FStudy& S,const TArray<FTransform>& Pose)
{
    FVector Out=FVector::ZeroVector;
    for(int32 K=0;K<Bones.Num();++K)
    { const int32 B=Bones[K]; Out+=Weights[K]*Pose[B].TransformPosition(S.RefGlobal[B].InverseTransformPosition(FVector(P))); }
    return FVector3f(Out);
}
static TArray<FVector3f> SkinRender(const FStudy& S,const TArray<FTransform>& Pose)
{
    const auto& Sec=S.Clone->GetImportedModel()->LODModels[0].Sections[S.Section];
    TArray<FVector3f> Out; Out.Reserve(Sec.SoftVertices.Num());
    for(const auto& V:Sec.SoftVertices)
    {
        FVector P=FVector::ZeroVector; float Sum=0;
        for(int32 K=0;K<MAX_TOTAL_INFLUENCES;++K) if(V.InfluenceWeights[K])
        {
            const int32 B=Sec.BoneMap[V.InfluenceBones[K]]; const float W=float(V.InfluenceWeights[K])/65535.f;
            P+=W*Pose[B].TransformPosition(S.RefGlobal[B].InverseTransformPosition(FVector(V.Position))); Sum+=W;
        }
        Out.Add(FVector3f(P/FMath::Max(Sum,SMALL_NUMBER)));
    }
    return Out;
}
static bool PoseAt(USkeletalMeshComponent* C,float Time,FString& Error)
{
    C->SetPosition(Time,false); C->TickAnimation(0.f,false); C->RefreshBoneTransforms();
    C->CompleteParallelAnimationEvaluation(true);
    if(C->GetComponentSpaceTransforms().Num()!=27) { Error=TEXT("Pose readback does not contain27bones"); return false; }
    return true;
}
}

FString UKohenClothExecutableLibrary::RunOneWalk(USkeletalMesh* Source,UAnimSequence* Walk,
    const FString& Input,const FString& OutDir)
{
    using namespace KohenCloth;
    auto Receipt=MakeShared<FJsonObject>();
    Receipt->SetStringField(TEXT("status"),TEXT("failed"));
    Receipt->SetBoolField(TEXT("apiFeasibilityCompleted"),false);
    Receipt->SetBoolField(TEXT("drapeAccepted"),false); Receipt->SetBoolField(TEXT("collisionAccepted"),false);
    Receipt->SetStringField(TEXT("control"),TEXT("Outer dynamic, exact rigid-skinned inner. Inner may itself force shelf. Not final cloth solution."));
    Receipt->SetNumberField(TEXT("requestedWalkSamples"),288);
    Receipt->SetNumberField(TEXT("completedWalkSamples"),0);
    Receipt->SetNumberField(TEXT("stepSeconds"),1.0/240.0);
    FString Error; bool MayWrite=false; FStudy S;
    auto End=[&]() {
        if(!Error.IsEmpty()) Receipt->SetStringField(TEXT("error"),Error);
        if(Source && !S.SourceDigest.IsEmpty())
        {
            const bool Preserved=Digest(Source)==S.SourceDigest && Source->GetMeshClothingAssets().IsEmpty();
            Receipt->SetBoolField(TEXT("immutableSourcePreserved"),Preserved);
            if(!Preserved) { Receipt->SetStringField(TEXT("status"),TEXT("failed_source_preservation")); Receipt->SetBoolField(TEXT("apiFeasibilityCompleted"),false); }
        }
        if(MayWrite && !WriteJson(OutDir/TEXT("run.json"),Receipt))
        { Receipt->SetStringField(TEXT("status"),TEXT("failed_receipt_write")); Receipt->SetBoolField(TEXT("apiFeasibilityCompleted"),false); }
        return JsonText(Receipt);
    };
    if(!IsInGameThread() || FPaths::GetBaseFilename(FPaths::GetProjectFilePath())!=TEXT("KohenClothReview"))
    { Error=TEXT("Only isolated KohenClothReview editor project/game thread permitted"); return End(); }
    const FString Allowed=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()/TEXT("KohenClothWalk"));
    if(!FPaths::IsUnderDirectory(FPaths::ConvertRelativePathToFull(OutDir),Allowed) || IFileManager::Get().DirectoryExists(*OutDir))
    { Error=TEXT("Output must be a fresh child of isolated Saved/KohenClothWalk"); return End(); }
    MayWrite=IFileManager::Get().MakeDirectory(*OutDir,true);
    if(!MayWrite) { Error=TEXT("Cannot create fresh output directory"); return End(); }
    if(!Source || !Walk || !Walk->GetPathName().StartsWith(TEXT("/Game/KohenClothFeasibilityV1/Import/"))
        || Walk->GetSkeleton()!=Source->GetSkeleton() || Walk->GetPlayLength()<287.f/240.f)
    { Error=TEXT("Walk must use isolated source skeleton and cover all288samples"); return End(); }
    if(!Build(Source,Input,S,Error)) return End();
    Receipt->SetNumberField(TEXT("tetherCount"),S.TetherCount);
    Receipt->SetNumberField(TEXT("densityKgM2"),.35);
    Receipt->SetNumberField(TEXT("minParticleMassKg"),.0001);
    Receipt->SetStringField(TEXT("massBasis"),TEXT("Authored study choice,350g/m2; not historical or measured textile data"));
    Receipt->SetStringField(TEXT("sourceDigest"),S.SourceDigest);
    Receipt->SetStringField(TEXT("unboundSectionsDigest"),S.UnboundDigest);
    Receipt->SetNumberField(TEXT("simulationVertices"),S.Points.Num()); Receipt->SetNumberField(TEXT("outerVertices"),S.OuterCount);
    Receipt->SetNumberField(TEXT("renderVertices"),S.Mapping.Num()); Receipt->SetNumberField(TEXT("sectionIndex"),S.Section);
    // Topology and ranges are separate from the frame stream; patterns are ready for
    // a later both-dynamic collection without changing particle IDs or correspondence.
    auto Topology=MakeShared<FJsonObject>(); TArray<TSharedPtr<FJsonValue>> Patterns;
    Topology->SetNumberField(TEXT("frameSchemaVersion"),2);
    TArray<TSharedPtr<FJsonValue>> Bindings,Tethers;
    for(const auto& Pat:S.Patterns) for(int32 I=0;I<Pat.Points.Num();++I)
    {
        TArray<TSharedPtr<FJsonValue>> Weights,Attachments;
        for(int32 K=0;K<Pat.Bones[I].Num();++K) Weights.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(Pat.Bones[I][K]),MakeShared<FJsonValueNumber>(Pat.Weights[I][K])}));
        const int32 D=Pat.Start+I;
        for(int32 K=0;K<S.TetherAnchors[D].Num();++K) Attachments.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(S.TetherAnchors[D][K]),MakeShared<FJsonValueNumber>(S.TetherLengths[D][K])}));
        Bindings.Add(MakeShared<FJsonValueArray>(Weights)); Tethers.Add(MakeShared<FJsonValueArray>(Attachments));
    }
    Topology->SetArrayField(TEXT("simulationBoneInfluences"),Bindings); Topology->SetArrayField(TEXT("tethers"),Tethers);
    TArray<TSharedPtr<FJsonValue>> MappingRows;
    for(const auto& M:S.Mapping)
    {
        TArray<TSharedPtr<FJsonValue>> Row;
        for(int32 K=0;K<3;++K) Row.Add(MakeShared<FJsonValueNumber>(M.SourceMeshVertIndices[K]));
        for(int32 K=0;K<4;++K) Row.Add(MakeShared<FJsonValueNumber>(M.PositionBaryCoordsAndDist[K]));
        Row.Add(MakeShared<FJsonValueNumber>(float(M.SourceMeshVertIndices[3])/65535.f));
        MappingRows.Add(MakeShared<FJsonValueArray>(Row));
    }
    Topology->SetArrayField(TEXT("renderPositionMappings"),MappingRows);
    for(const auto& P:S.Patterns)
    {
        auto R=MakeShared<FJsonObject>(); R->SetStringField(TEXT("name"),P.Name); R->SetBoolField(TEXT("dynamic"),P.Dynamic);
        R->SetNumberField(TEXT("start"),P.Start); R->SetNumberField(TEXT("count"),P.Points.Num());
        TArray<TSharedPtr<FJsonValue>> Faces; for(int32 I=0;I<P.Indices.Num();I+=3)
            Faces.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{MakeShared<FJsonValueNumber>(P.Indices[I]),MakeShared<FJsonValueNumber>(P.Indices[I+1]),MakeShared<FJsonValueNumber>(P.Indices[I+2])}));
        R->SetArrayField(TEXT("faces"),Faces); Patterns.Add(MakeShared<FJsonValueObject>(R));
    }
    Topology->SetArrayField(TEXT("patterns"),Patterns);
    Topology->SetStringField(TEXT("binaryLayout"),TEXT("v2 little-endian float32 XYZ AUTHOR cm: simulation, cloth render, original-rig preservation reference, matched-binding nonsimulated render control,27 bone positions"));
    Topology->SetNumberField(TEXT("simulationVertices"),S.Points.Num()); Topology->SetNumberField(TEXT("renderVertices"),S.Mapping.Num());
    Topology->SetStringField(TEXT("winding"),TEXT("faces are native handedness; reverse for author-space parity if axisDeterminant is negative"));
    const float Det=FVector3f::DotProduct(FVector3f::CrossProduct(S.ToNative(FVector3f(1,0,0)),S.ToNative(FVector3f(0,1,0))),S.ToNative(FVector3f(0,0,1)));
    Topology->SetNumberField(TEXT("axisDeterminant"),Det);
    TArray<FVector3f> RestAuthor; for(const auto& P:S.Points) RestAuthor.Add(S.ToAuthor(P));
    Topology->SetArrayField(TEXT("simulationRestAuthorCm"),Vectors(RestAuthor));
    TArray<TSharedPtr<FJsonValue>> BoneNames;
    for(int32 I=0;I<27;++I) BoneNames.Add(MakeShared<FJsonValueString>(S.Clone->GetRefSkeleton().GetBoneName(I).ToString()));
    Topology->SetArrayField(TEXT("boneNames"),BoneNames);
    TArray<TSharedPtr<FJsonValue>> RenderFaces;
    const auto& L=S.Clone->GetImportedModel()->LODModels[0]; const auto& Sec=L.Sections[S.Section];
    RestAuthor.Reset(); for(const auto& V:Sec.SoftVertices) RestAuthor.Add(S.ToAuthor(V.Position));
    Topology->SetArrayField(TEXT("renderRestAuthorCm"),Vectors(RestAuthor));
    for(uint32 I=0;I<Sec.NumTriangles*3;I+=3)
        RenderFaces.Add(MakeShared<FJsonValueArray>(TArray<TSharedPtr<FJsonValue>>{
            MakeShared<FJsonValueNumber>(L.IndexBuffer[Sec.BaseIndex+I]-Sec.BaseVertexIndex),
            MakeShared<FJsonValueNumber>(L.IndexBuffer[Sec.BaseIndex+I+1]-Sec.BaseVertexIndex),
            MakeShared<FJsonValueNumber>(L.IndexBuffer[Sec.BaseIndex+I+2]-Sec.BaseVertexIndex)}));
    Topology->SetArrayField(TEXT("renderFaces"),RenderFaces);
    if(!WriteJson(OutDir/TEXT("topology.json"),Topology)) { Error=TEXT("Topology write failed"); return End(); }
    const IConsoleVariable* WaitForInit=IConsoleManager::Get().FindConsoleVariable(TEXT("p.ChaosClothAsset.WaitForAsyncClothInitialization"));
    if(!WaitForInit || WaitForInit->GetInt()!=1)
    { Error=TEXT("Synchronous harness requires installed WaitForAsyncClothInitialization=1; no setting changed"); return End(); }
    FPreviewScene Scene(FPreviewScene::ConstructionValues().SetCreatePhysicsScene(true).SetCreateDefaultLighting(false).SetForceMipsResident(false));
    TStrongObjectPtr<USkeletalMeshComponent> Component(NewObject<USkeletalMeshComponent>(GetTransientPackage()));
    Component->SetSkeletalMesh(S.Clone.Get()); Component->SetAnimationMode(EAnimationMode::AnimationSingleNode);
    Component->SetAnimation(Walk); Component->SetForcedLOD(1); Component->SetComponentTickEnabled(false);
    Component->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Component->SetAllowClothActors(true);
    Component->SetUpdateClothInEditor(true);
    Scene.AddComponent(Component.Get(),FTransform::Identity);
    ON_SCOPE_EXIT { Component->WaitForExistingParallelClothSimulation_GameThread(); Scene.RemoveComponent(Component.Get()); };
    if(!PoseAt(Component.Get(),0.f,Error)) return End();
    auto& Instances=Component->GetClothingSimulationInstances();
    if(Instances.Num()!=1 || !Instances[0].GetClothingSimulation())
    { Error=TEXT("Expected one instantiated modern cloth simulation"); return End(); }
    auto& Instance=Instances[0];
    const auto* Solver=Instance.GetClothingSimulation();
    Component->ResetClothTeleportMode();
    Instance.FillContextAndPrepareTick(Component.Get(),1.f/240.f,false); Instance.HardResetSimulation();
    double MaxKinematicError=0,MaxDisplacement=0,MaxOriginalDifference=0; TArray<TSharedPtr<FJsonValue>> Frames;
    const double StartTime=FPlatformTime::Seconds();
    // Exactly120settle steps, then288samples. No world ticking or asynchronous cloth tasks.
    for(int32 Step=-120;Step<288;++Step)
    {
        if(FPlatformTime::Seconds()-StartTime>300.0) { Error=TEXT("Five-minute harness budget exceeded; partial frames retained"); return End(); }
        const float Time=FMath::Max(0,Step)/240.f;
        if(!PoseAt(Component.Get(),Time,Error)) return End();
        Component->ResetClothTeleportMode();
        Instance.FillContextAndPrepareTick(Component.Get(),1.f/240.f,false);
        Instance.SyncClothingInteractor(); Instance.Simulate();
        TMap<int32,FClothSimulData> Data; Instance.AppendSimulationData(Data,Component.Get(),nullptr);
        const FClothSimulData* D=Data.Find(0);
        if(!D || D->LODIndex!=0 || D->Positions.Num()!=S.Points.Num() || D->Normals.Num()!=S.Points.Num())
        { Error=TEXT("Missing/stale/incorrect LOD solver readback"); return End(); }
        if(Step==-120)
        {
            Receipt->SetNumberField(TEXT("dynamicParticles"),Solver->GetNumDynamicParticles());
            Receipt->SetNumberField(TEXT("kinematicParticles"),Solver->GetNumKinematicParticles());
            if(Solver->GetNumDynamicParticles()<=0 || Solver->GetNumKinematicParticles()<S.Points.Num()-S.OuterCount)
            { Error=TEXT("Solver dynamic/kinematic particle allocation is invalid"); return End(); }
        }
        TArray<FVector3f> P,N; P.Reserve(S.Points.Num()); N.Reserve(S.Points.Num());
        const FTransform ComponentToWorld=Component->GetComponentTransform();
        for(int32 I=0;I<D->Positions.Num();++I)
        {
            P.Add(FVector3f(ComponentToWorld.InverseTransformPosition(D->Transform.TransformPosition(FVector(D->Positions[I])))));
            N.Add(FVector3f(ComponentToWorld.InverseTransformVectorNoScale(D->Transform.TransformVectorNoScale(FVector(D->Normals[I])))));
            if(P.Last().ContainsNaN() || N.Last().ContainsNaN()) { Error=TEXT("Nonfinite solver readback"); return End(); }
        }
        const auto& Pose=Component->GetComponentSpaceTransforms(); float KinematicError=0;
        for(const auto& Pat:S.Patterns) for(int32 I=0;I<Pat.Points.Num();++I) if(Pat.MaxDistance[I]==0)
            KinematicError=FMath::Max(KinematicError,FVector3f::Distance(P[Pat.Start+I],Skin(Pat.Points[I],Pat.Bones[I],Pat.Weights[I],S,Pose)));
        MaxKinematicError=FMath::Max(MaxKinematicError,double(KinematicError));
        Receipt->SetNumberField(TEXT("maxKinematicReadbackErrorCm"),MaxKinematicError);
        if(KinematicError>.05f) { Error=TEXT("Solver kinematic vertices do not match posed rig within0.05cm; refuse space/timing mismatch"); return End(); }
        if(Step<0) continue;
        const auto Control=SkinRender(S,Pose); TArray<FVector3f> Deformed; TArray<float> Buffer;
        TArray<FVector3f> MatchedPoints,MatchedRender;
        for(const auto& Pat:S.Patterns) for(int32 I=0;I<Pat.Points.Num();++I)
            MatchedPoints.Add(Skin(Pat.Points[I],Pat.Bones[I],Pat.Weights[I],S,Pose));
        // Same physical topology, binding, deformer and skinning blend; no integration.
        const ClothingMeshUtils::ClothMeshDesc MatchedMesh(MatchedPoints,S.Indices);
        const auto MatchedNormals=MatchedMesh.GetNormals();
        for(int32 I=0;I<S.Mapping.Num();++I)
        {
            const float Blend=float(S.Mapping[I].SourceMeshVertIndices[3])/65535.f;
            MatchedRender.Add(FMath::Lerp(Embed(S.Mapping[I],MatchedPoints,MatchedNormals),Control[I],Blend));
        }
        Buffer.Reserve((S.Points.Num()+3*S.Mapping.Num()+27)*3);
        auto Push=[&](const FVector3f& Native) { const auto A=S.ToAuthor(Native); Buffer.Add(A.X); Buffer.Add(A.Y); Buffer.Add(A.Z); };
        for(const auto& V:P) Push(V);
        for(int32 I=0;I<S.Mapping.Num();++I)
        {
            const float Blend=float(S.Mapping[I].SourceMeshVertIndices[3])/65535.f;
            const auto V=FMath::Lerp(Embed(S.Mapping[I],P,N),Control[I],Blend);
            if(V.ContainsNaN()) { Error=TEXT("Nonfinite render reconstruction"); return End(); }
            Deformed.Add(V); Push(V); MaxDisplacement=FMath::Max(MaxDisplacement,double(FVector3f::Distance(V,MatchedRender[I])));
            MaxOriginalDifference=FMath::Max(MaxOriginalDifference,double(FVector3f::Distance(V,Control[I])));
        }
        for(const auto& V:Control) Push(V);
        for(const auto& V:MatchedRender) Push(V);
        for(const auto& T:Pose) Push(FVector3f(T.GetTranslation()));
        const FString Filename=FString::Printf(TEXT("frame-%03d.f32"),Step);
        if(!WriteBinary(OutDir/Filename,Buffer)) { Error=TEXT("Atomic frame write failed"); return End(); }
        auto F=MakeShared<FJsonObject>(); F->SetNumberField(TEXT("index"),Step); F->SetNumberField(TEXT("timeSeconds"),Time);
        F->SetStringField(TEXT("file"),Filename); F->SetNumberField(TEXT("kinematicErrorCm"),KinematicError);
        Frames.Add(MakeShared<FJsonValueObject>(F)); Receipt->SetNumberField(TEXT("completedWalkSamples"),Step+1);
        // Small atomic progress receipts; an interruption leaves every completed frame useful.
        if(Step%24==0 || Step==287)
        { auto Progress=MakeShared<FJsonObject>(); Progress->SetNumberField(TEXT("completed"),Step+1); Progress->SetArrayField(TEXT("frames"),Frames);
          if(!WriteJson(OutDir/FString::Printf(TEXT("progress-%03d.json"),Step),Progress)) { Error=TEXT("Progress receipt write failed"); return End(); } }
    }
    Receipt->SetArrayField(TEXT("frames"),Frames); Receipt->SetNumberField(TEXT("maxRenderDifferenceFromMatchedBindingCm"),MaxDisplacement);
    Receipt->SetNumberField(TEXT("maxRenderDifferenceFromOriginalRigCm"),MaxOriginalDifference);
    Receipt->SetNumberField(TEXT("solverIterations"),Solver->GetNumIterations()); Receipt->SetNumberField(TEXT("solverSubsteps"),Solver->GetNumSubsteps());
    Receipt->SetNumberField(TEXT("elapsedSeconds"),FPlatformTime::Seconds()-StartTime);
    if(Digest(S.Clone.Get(),S.Section)!=S.UnboundDigest) { Error=TEXT("Head/rig/unbound-section preservation failed after walk"); return End(); }
    Receipt->SetBoolField(TEXT("headRigUnboundSectionsPreserved"),true);
    if(MaxDisplacement<.01) { Error=TEXT("No measurable departure from matched-binding nonsimulated control; physics effect unproven"); return End(); }
    Receipt->SetBoolField(TEXT("apiFeasibilityCompleted"),true); Receipt->SetStringField(TEXT("status"),TEXT("readback_complete_not_visual_or_clearance_acceptance"));
    return End();
}
