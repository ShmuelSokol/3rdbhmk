#include "MikdashEnclosure.h"
#include "KotelClosureRuntimeData.h"
#include "MikdashPhotoMode.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshResources.h"
#include "Engine/World.h"
#include "PhysicsEngine/BodyInstance.h"
#include "PhysicsEngine/BodySetup.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Camera/PlayerCameraManager.h"
#include "Materials/MaterialInterface.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "HAL/PlatformFileManager.h"
#include "HAL/PlatformTime.h"
#include "HAL/PlatformMisc.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
namespace Data = KotelClosureRuntimeData;
using UE::Geometry::FDynamicMesh3;
using UE::Geometry::FIndex3i;
const TCHAR* AshlarPath = TEXT("/Game/MikdashV3/FutureMountV1/PrecinctPlazaV1/Materials/MI_PrecinctPlaza_Ashlar.MI_PrecinctPlaza_Ashlar");
// Material slot 0 of the V2 retaining wall. M_Context_Building's VCMeanLum is 0.38, so a
// constant 97/255 colour overlay leaves its vertex-colour modulation at exactly 1.0 and the
// wall reads as the same limestone as the Jewish Quarter infill behind it.
const FVector4f WallColour(KotelClosureRuntimeData::VertexColourByte / 255.0f,
                           KotelClosureRuntimeData::VertexColourByte / 255.0f,
                           KotelClosureRuntimeData::VertexColourByte / 255.0f, 1.0f);
FVector Vector(const Data::FVec3& P) { return FVector(P.X, P.Y, P.Z); }
FTransform Transform(const Data::FDeckTransform& T)
{
    return FTransform(FRotator(T.Rotation.X, T.Rotation.Y, T.Rotation.Z), Vector(T.Location), Vector(T.Scale));
}
bool Identity(const FTransform& T) { return T.IsValid() && T.Equals(FTransform::Identity, 1e-6); }
bool IsCandidateWorld(UWorld* World)
{
    if (!World || !World->IsGameWorld()) return false;
    FString Name = World->GetOutermost()->GetName();
    if (World->WorldType == EWorldType::PIE)
    {
        const int32 Slash = Name.Find(TEXT("/"), ESearchCase::CaseSensitive, ESearchDir::FromEnd);
        FString Leaf = Name.Mid(Slash + 1);
        if (Leaf.StartsWith(TEXT("UEDPIE_")))
        {
            const int32 EndPrefix = Leaf.Find(TEXT("_"), ESearchCase::CaseSensitive, ESearchDir::FromStart, 7);
            if (EndPrefix == INDEX_NONE) return false;
            Name = Name.Left(Slash + 1) + Leaf.Mid(EndPrefix + 1);
        }
    }
    return Name == UTF8_TO_TCHAR(Data::ExpectedMapPackage);
}
bool ActualVisible(const UPrimitiveComponent* Component)
{
    return Component && Component->IsRegistered() && Component->IsVisible() && !Component->bHiddenInGame
        && Component->GetOwner() && !Component->GetOwner()->IsHidden();
}
bool ClosurePhysicsDataReady(const UDynamicMeshComponent* Component)
{
    const UBodySetup* Setup = Component ? Component->GetBodySetup() : nullptr;
    if (!Setup || !Setup->bCreatedPhysicsMeshes || Setup->bFailedToCreatePhysicsMeshes
        || !Setup->bDoubleSidedGeometry || Setup->CollisionTraceFlag != CTF_UseComplexAsSimple
        || Setup->TriMeshGeometries.Num() == 0) return false;
    for (const auto& TriangleMesh : Setup->TriMeshGeometries) if (!TriangleMesh.IsValid()) return false;
    return true;
}
bool ClosureResponsesMatch(const UPrimitiveComponent* Component)
{
    FCollisionResponseContainer Expected(ECR_Ignore);
    Expected.SetResponse(ECC_Pawn, ECR_Block);
    return Component && Component->GetCollisionObjectType() == ECC_WorldStatic
        && Component->GetCollisionResponseToChannels() == Expected;
}
TSharedRef<FJsonObject> ComponentReadback(const UPrimitiveComponent* Component)
{
    TSharedRef<FJsonObject> Item = MakeShared<FJsonObject>();
    Item->SetBoolField(TEXT("exists"), Component != nullptr);
    if (!Component) return Item;
    Item->SetStringField(TEXT("path"), Component->GetPathName());
    Item->SetStringField(TEXT("componentName"), Component->GetName());
    Item->SetStringField(TEXT("class"), Component->GetClass()->GetPathName());
    Item->SetStringField(TEXT("worldTransform"), Component->GetComponentTransform().ToString());
    Item->SetBoolField(TEXT("visible"), Component->IsVisible());
    Item->SetBoolField(TEXT("hiddenInGame"), Component->bHiddenInGame);
    Item->SetBoolField(TEXT("actualVisible"), ActualVisible(Component));
    Item->SetBoolField(TEXT("registered"), Component->IsRegistered());
    Item->SetBoolField(TEXT("transient"), Component->HasAnyFlags(RF_Transient));
    Item->SetNumberField(TEXT("collisionMode"), static_cast<int32>(Component->GetCollisionEnabled()));
    Item->SetNumberField(TEXT("configuredCollisionMode"), static_cast<int32>(Component->BodyInstance.GetCollisionEnabled(false)));
    Item->SetStringField(TEXT("collisionProfile"), Component->GetCollisionProfileName().ToString());
    Item->SetNumberField(TEXT("pawnResponse"), static_cast<int32>(Component->GetCollisionResponseToChannel(ECC_Pawn)));
    Item->SetBoolField(TEXT("physicsStateCreated"), Component->IsPhysicsStateCreated());
    const FBodyInstance* PhysicsBody = Component->GetBodyInstance();
    Item->SetBoolField(TEXT("bodyInstanceValid"), PhysicsBody && PhysicsBody->IsValidBodyInstance());
    Item->SetBoolField(TEXT("affectsNavigation"), Component->CanEverAffectNavigation());
    Item->SetBoolField(TEXT("generatesOverlap"), Component->GetGenerateOverlapEvents());
    Item->SetStringField(TEXT("material"), GetPathNameSafe(Component->GetMaterial(0)));
    if (const UMaterialInterface* Material = Component->GetMaterial(0)) Item->SetBoolField(TEXT("materialTwoSided"), Material->IsTwoSided());
    if (const AActor* ComponentActor = Component->GetOwner())
    {
        Item->SetStringField(TEXT("actor"), ComponentActor->GetPathName());
        Item->SetStringField(TEXT("actorName"), ComponentActor->GetName());
        Item->SetStringField(TEXT("actorTransform"), ComponentActor->GetActorTransform().ToString());
        Item->SetBoolField(TEXT("actorHidden"), ComponentActor->IsHidden());
        Item->SetBoolField(TEXT("actorCollisionEnabled"), ComponentActor->GetActorEnableCollision());
        TArray<TSharedPtr<FJsonValue>> Tags;
        for (FName Tag : ComponentActor->Tags) Tags.Add(MakeShared<FJsonValueString>(Tag.ToString()));
        Item->SetArrayField(TEXT("actorTags"), Tags);
    }
    if (const UStaticMeshComponent* Static = Cast<UStaticMeshComponent>(Component))
    {
        Item->SetStringField(TEXT("mesh"), GetPathNameSafe(Static->GetStaticMesh()));
        if (const UStaticMesh* Asset = Static->GetStaticMesh())
        {
            Item->SetStringField(TEXT("assetBoundsOriginCm"), Asset->GetBounds().Origin.ToString());
            Item->SetStringField(TEXT("assetBoundsExtentCm"), Asset->GetBounds().BoxExtent.ToString());
            const FStaticMeshRenderData* RenderData = Asset->GetRenderData();
            if (RenderData && RenderData->LODResources.Num() > 0)
            {
                Item->SetNumberField(TEXT("renderLod0Vertices"), RenderData->LODResources[0].GetNumVertices());
                Item->SetNumberField(TEXT("renderLod0Triangles"), RenderData->LODResources[0].GetNumTriangles());
                Item->SetStringField(TEXT("renderCountsScope"), TEXT("cooked render/fallback LOD, not canonical source triangle count"));
            }
        }
    }
    if (const UInstancedStaticMeshComponent* Instances = Cast<UInstancedStaticMeshComponent>(Component))
        Item->SetNumberField(TEXT("instanceCount"), Instances->GetInstanceCount());
    if (const UDynamicMeshComponent* Dynamic = Cast<UDynamicMeshComponent>(Component))
    {
        const UBodySetup* Setup = Dynamic->GetBodySetup();
        Item->SetBoolField(TEXT("physicsDataReady"), ClosurePhysicsDataReady(Dynamic));
        Item->SetBoolField(TEXT("pawnOnlyResponses"), ClosureResponsesMatch(Dynamic));
        Item->SetBoolField(TEXT("asyncCooking"), Dynamic->bUseAsyncCooking);
        Item->SetBoolField(TEXT("complexCollisionEnabled"), Dynamic->bEnableComplexCollision);
        Item->SetBoolField(TEXT("physicsMeshesCreated"), Setup && Setup->bCreatedPhysicsMeshes);
        Item->SetBoolField(TEXT("physicsMeshCreationFailed"), Setup && Setup->bFailedToCreatePhysicsMeshes);
        Item->SetBoolField(TEXT("doubleSidedPhysics"), Setup && Setup->bDoubleSidedGeometry);
        Item->SetNumberField(TEXT("chaosTriangleMeshCount"), Setup ? Setup->TriMeshGeometries.Num() : 0);
        Item->SetNumberField(TEXT("collisionTraceFlag"), Setup ? static_cast<int32>(Setup->CollisionTraceFlag) : -1);
    }
    return Item;
}
const EMikdashPrecinctState ProbeStates[] = {EMikdashPrecinctState::Modern, EMikdashPrecinctState::Yechezkel,
    EMikdashPrecinctState::Overlay, EMikdashPrecinctState::Modern};
const TCHAR* ProbeStateNames[] = {TEXT("Modern"), TEXT("Yechezkel"), TEXT("Overlay"), TEXT("Modern-again")};
}

void AMikdashEnclosure::ClearKotelClosure()
{
    if (KotelClosure.IsValid()) KotelClosure->DestroyComponent();
    KotelClosure.Reset();
    KotelClosureTerrain.Reset();
    KotelClosureDeck.Reset();
    KotelClosureTerrainMaterial.Reset();
    KotelClosureDeckMaterial.Reset();
    bKotelClosureValidated = false;
    KotelClosureStatus = TEXT("cleared");
}

void AMikdashEnclosure::PrepareKotelClosure()
{
    ClearKotelClosure();
    KotelClosureStatus = TEXT("guard:not-candidate-game-world");
    if (!IsCandidateWorld(GetWorld())) return;
    bKotelClosureDisabled = FParse::Param(FCommandLine::Get(), TEXT("MikdashDisableKotelClosure"));
    auto Refuse = [this](const TCHAR* Reason) {
        ClearKotelClosure();
        KotelClosureStatus = FString(TEXT("guard:")) + Reason;
        UE_LOG(LogTemp, Warning, TEXT("KotelClosureRuntimeV1 %s"), *KotelClosureStatus);
    };
    int32 Enclosures = 0, PlazaActors = 0;
    TArray<UStaticMeshComponent*> TerrainMatches;
    TArray<UInstancedStaticMeshComponent*> DeckMatches;
    for (TActorIterator<AActor> It(GetWorld()); It; ++It)
    {
        if (Cast<AMikdashEnclosure>(*It)) ++Enclosures;
        const bool IsPlaza = It->ActorHasTag(FName(UTF8_TO_TCHAR(Data::ExpectedDeckTag)));
        if (IsPlaza) ++PlazaActors;
        TInlineComponentArray<UStaticMeshComponent*> Components;
        It->GetComponents(Components);
        for (UStaticMeshComponent* Component : Components)
        {
            if (!Component->GetStaticMesh()) continue;
            const FString Path = Component->GetStaticMesh()->GetPathName();
            if (Path == UTF8_TO_TCHAR(Data::TerrainMeshPath)) TerrainMatches.Add(Component);
            if (IsPlaza && Path == UTF8_TO_TCHAR(Data::DeckMeshPath))
                if (UInstancedStaticMeshComponent* Deck = Cast<UInstancedStaticMeshComponent>(Component)) DeckMatches.Add(Deck);
        }
    }
    if (Enclosures != 1 || IsHidden() || PlazaActors != 1 || TerrainMatches.Num() != 1 || DeckMatches.Num() != 1)
    { Refuse(TEXT("scene-identity-not-unique")); return; }
    if (!HideWhileWallStandsTags.Contains(FName(UTF8_TO_TCHAR(Data::ExpectedTerrainTag)))
        || HideWhileModernCityStandsTags.Contains(FName(UTF8_TO_TCHAR(Data::ExpectedTerrainTag))))
    { Refuse(TEXT("terrain-state-policy-mismatch")); return; }
    if (!PlazaAshlarMaterial || PlazaAshlarMaterial->GetPathName() != AshlarPath)
    { Refuse(TEXT("loaded-plaza-ashlar-missing-or-unexpected")); return; }
    // The retaining face itself is Old City limestone: the master the neighbouring Jewish
    // Quarter infill already uses, so it is cooked with this map. The legacy pieces in front
    // of the Western Wall keep the loaded plaza ashlar in slot 1.
    UMaterialInterface* Limestone = LoadObject<UMaterialInterface>(nullptr, UTF8_TO_TCHAR(Data::LimestoneMaterialPath));
    if (!Limestone) { Refuse(TEXT("old-city-limestone-material-missing")); return; }
    KotelClosureLimestone = Limestone;
    KotelClosureTerrain = TerrainMatches[0];
    KotelClosureDeck = DeckMatches[0];
    UPrimitiveComponent* Sources[] = {TerrainMatches[0], DeckMatches[0]};
    for (int32 Index = 0; Index < 2; ++Index)
    {
        KotelClosureSourceCollisionProfiles[Index] = Sources[Index]->GetCollisionProfileName();
        KotelClosureSourceCollisionModes[Index] = static_cast<uint8>(Sources[Index]->BodyInstance.GetCollisionEnabled(false));
        if (!Sources[Index]->GetMaterial(0)) { Refuse(TEXT("source-material-missing")); return; }
    }
    KotelClosureTerrainMaterial = TerrainMatches[0]->GetMaterial(0);
    KotelClosureDeckMaterial = DeckMatches[0]->GetMaterial(0);
    double DeckError = 0.0;
    if (!ValidateKotelClosureSources(DeckError)) { Refuse(TEXT("source-transform-tag-deck-or-physics-mismatch")); return; }
    bKotelClosureValidated = true;
    if (bKotelClosureDisabled)
    {
        KotelClosureStatus = TEXT("disabled-validated");
        return;
    }
    FDynamicMesh3 Mesh;
    Mesh.EnableAttributes();
    Mesh.Attributes()->SetNumNormalLayers(1);
    Mesh.Attributes()->SetNumUVLayers(1);
    Mesh.Attributes()->EnablePrimaryColors();
    Mesh.Attributes()->EnableMaterialID();
    auto* NormalOverlay = Mesh.Attributes()->PrimaryNormals();
    auto* UVOverlay = Mesh.Attributes()->PrimaryUV();
    auto* ColorOverlay = Mesh.Attributes()->PrimaryColors();
    auto* MaterialIDs = Mesh.Attributes()->GetMaterialID();
    if (!ColorOverlay || !MaterialIDs) { Refuse(TEXT("compiled-attribute-set-unavailable")); return; }
    for (int32 Index = 0; Index < Data::VertexCount; ++Index)
    {
        const FVector Point = Vector(Data::Vertices[Index]);
        const FVector Normal = Vector(Data::Normals[Index]);
        const Data::FVec2 UV = Data::UVs[Index];
        if (Point.ContainsNaN() || Normal.ContainsNaN() || !Normal.IsNormalized() || !FMath::IsFinite(UV.X) || !FMath::IsFinite(UV.Y)
            || Mesh.AppendVertex(Point) != Index
            || NormalOverlay->AppendElement(FVector3f(Normal)) != Index
            || UVOverlay->AppendElement(FVector2f(UV.X, UV.Y)) != Index
            || ColorOverlay->AppendElement(WallColour) != Index)
        { Refuse(TEXT("compiled-vertex-or-overlay-invalid")); return; }
    }
    for (int32 Index = 0; Index < Data::TriangleCount; ++Index)
    {
        const auto T = Data::Triangles[Index];
        const FIndex3i Native(T.A, T.C, T.B); // same reversal as the proved native importer
        const int32 Material = Data::MaterialIds[Index];
        if (Material < 0 || Material >= Data::MaterialCount
            || Mesh.AppendTriangle(Native) != Index
            || NormalOverlay->SetTriangle(Index, Native) != UE::Geometry::EMeshResult::Ok
            || UVOverlay->SetTriangle(Index, Native) != UE::Geometry::EMeshResult::Ok
            || ColorOverlay->SetTriangle(Index, Native) != UE::Geometry::EMeshResult::Ok)
        { Refuse(TEXT("compiled-triangle-or-overlay-invalid")); return; }
        MaterialIDs->SetValue(Index, Material);
    }
    if (!Mesh.CheckValidity({}, UE::Geometry::EValidityCheckFailMode::ReturnOnly))
    { Refuse(TEXT("dynamic-mesh-invalid")); return; }
    KotelClosure = NewObject<UDynamicMeshComponent>(this, NAME_None, RF_Transient);
    // OwnedComponents is collected by AActor::AddReferencedObjects; no new UPROPERTY
    // is needed, preserving compatibility with the existing unversioned cooked map.
    AddOwnedComponent(KotelClosure.Get());
    KotelClosure->SetVisibility(false);
    KotelClosure->SetHiddenInGame(true);
    KotelClosure->SetWorldTransform(FTransform::Identity);
    KotelClosure->SetCollisionProfileName(TEXT("NoCollision"));
    KotelClosure->SetCollisionObjectType(ECC_WorldStatic);
    KotelClosure->SetCollisionResponseToAllChannels(ECR_Ignore);
    KotelClosure->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
    KotelClosure->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    KotelClosure->SetCanEverAffectNavigation(false);
    KotelClosure->SetGenerateOverlapEvents(false);
    KotelClosure->bUseAsyncCooking = false;
    KotelClosure->SetDeferredCollisionUpdatesEnabled(true, false);
    KotelClosure->SetComplexAsSimpleCollisionEnabled(true, false);
    KotelClosure->GetBodySetup()->bDoubleSidedGeometry = true;
    KotelClosure->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
    KotelClosure->ConfigureMaterialSet({KotelClosureLimestone.Get(), PlazaAshlarMaterial});
    KotelClosure->SetMesh(MoveTemp(Mesh));
    KotelClosure->ComponentTags.Add(TEXT("KotelClosureRuntimeV1"));
    KotelClosure->RegisterComponent();
    // Build the final immutable face mesh synchronously only after registration.
    // Hidden states retain cooked Chaos geometry but expose no collision queries.
    KotelClosure->SetDeferredCollisionUpdatesEnabled(false, false);
    KotelClosure->UpdateCollision(false);
    double PositionError, NormalError, UVError;
    if (!ValidateKotelClosureMesh(PositionError, NormalError, UVError))
    { Refuse(TEXT("registered-mesh-readback-failed")); return; }
    KotelClosureStatus = TEXT("prepared-hidden");
    UE_LOG(LogTemp, Display, TEXT("KotelClosureRuntimeV1 prepared vertices=%d triangles=%d deck=%d deckErrorCm=%.9f positionErrorCm=%.9f normalError=%.9f"),
        Data::VertexCount, Data::TriangleCount, Data::DeckCount, DeckError, PositionError, NormalError);
}

bool AMikdashEnclosure::ValidateKotelClosureSources(double& OutDeckErrorCm) const
{
    OutDeckErrorCm = 0.0;
    UStaticMeshComponent* Terrain = KotelClosureTerrain.Get();
    UInstancedStaticMeshComponent* Deck = KotelClosureDeck.Get();
    if (!IsCandidateWorld(GetWorld()) || !Terrain || !Deck || !PlazaAshlarMaterial || PlazaAshlarMaterial->GetPathName() != AshlarPath
        || Terrain->GetClass() != UStaticMeshComponent::StaticClass()
        || Deck->GetClass() != UHierarchicalInstancedStaticMeshComponent::StaticClass()
        || !Terrain->GetStaticMesh() || Terrain->GetStaticMesh()->GetPathName() != UTF8_TO_TCHAR(Data::TerrainMeshPath)
        || !Deck->GetStaticMesh() || Deck->GetStaticMesh()->GetPathName() != UTF8_TO_TCHAR(Data::DeckMeshPath)
        || Deck->GetInstanceCount() != Data::DeckCount
        || !Identity(Terrain->GetComponentTransform()) || !Identity(Terrain->GetOwner()->GetActorTransform())
        || !Identity(Deck->GetComponentTransform()) || !Identity(Deck->GetOwner()->GetActorTransform())
        || !Terrain->GetOwner()->ActorHasTag(FName(UTF8_TO_TCHAR(Data::ExpectedTerrainTileTag)))
        || !Deck->GetOwner()->ActorHasTag(FName(UTF8_TO_TCHAR(Data::ExpectedDeckTag)))
        || Terrain->GetMaterial(0) != KotelClosureTerrainMaterial.Get() || Deck->GetMaterial(0) != KotelClosureDeckMaterial.Get()) return false;
    const UPrimitiveComponent* Sources[] = {Terrain, Deck};
    for (int32 Index = 0; Index < 2; ++Index)
    {
        const UPrimitiveComponent* Source = Sources[Index];
        if (!Source->IsRegistered() || !Source->IsVisible() || Source->bHiddenInGame
            || Source->GetCollisionProfileName() != KotelClosureSourceCollisionProfiles[Index]
            || static_cast<uint8>(Source->BodyInstance.GetCollisionEnabled(false)) != KotelClosureSourceCollisionModes[Index]
            || !Source->GetOwner()->ActorHasTag(FName(UTF8_TO_TCHAR(Data::ExpectedTerrainTag)))) return false;
        for (FName Tag : Source->GetOwner()->Tags) if (HideWhileModernCityStandsTags.Contains(Tag)) return false;
    }
    for (int32 Index = 0; Index < Data::DeckCount; ++Index)
    {
        FTransform Actual;
        if (!Deck->GetInstanceTransform(Index, Actual, true) || !Actual.IsValid()) return false;
        const FTransform Expected = Transform(Data::DeckTransforms[Index]);
        for (const FVector Probe : {FVector::ZeroVector, FVector(625,0,0), FVector(0,625,0), FVector(0,0,50)})
            OutDeckErrorCm = FMath::Max(OutDeckErrorCm, FVector::Distance(Actual.TransformPosition(Probe), Expected.TransformPosition(Probe)));
        if (OutDeckErrorCm > 0.1) return false;
    }
    return true;
}

bool AMikdashEnclosure::ValidateKotelClosureMesh(double& OutPositionErrorCm, double& OutNormalError, double& OutUVError) const
{
    OutPositionErrorCm = OutNormalError = OutUVError = 0.0;
    if (!bKotelClosureValidated) return false;
    if (bKotelClosureDisabled) return !KotelClosure.IsValid();
    const bool CollisionActive = ActualVisible(KotelClosure.Get());
    const ECollisionEnabled::Type ExpectedCollision = CollisionActive ? ECollisionEnabled::QueryOnly : ECollisionEnabled::NoCollision;
    if (!KotelClosure.IsValid() || !KotelClosure->IsRegistered() || !KotelClosure->HasAnyFlags(RF_Transient)
        || !Identity(KotelClosure->GetComponentTransform())
        || KotelClosure->GetNumMaterials() != Data::MaterialCount
        || KotelClosure->GetMaterial(0) != KotelClosureLimestone.Get()
        || KotelClosure->GetMaterial(1) != PlazaAshlarMaterial
        || KotelClosure->GetCollisionEnabled() != ExpectedCollision
        || KotelClosure->BodyInstance.GetCollisionEnabled(false) != ExpectedCollision
        || !ClosureResponsesMatch(KotelClosure.Get()) || !ClosurePhysicsDataReady(KotelClosure.Get())
        || KotelClosure->CanEverAffectNavigation() || KotelClosure->GetGenerateOverlapEvents()
        || !KotelClosure->bEnableComplexCollision || KotelClosure->bUseAsyncCooking
        || KotelClosure->CollisionType != CTF_UseComplexAsSimple
        || (CollisionActive && (!KotelClosure->IsPhysicsStateCreated() || !KotelClosure->BodyInstance.IsValidBodyInstance()))
        || KotelClosure->GetTangentsType() != EDynamicMeshComponentTangentsMode::AutoCalculated) return false;
    bool Passed = true;
    KotelClosure->ProcessMesh([&](const FDynamicMesh3& Mesh) {
        if (Mesh.VertexCount() != Data::VertexCount || Mesh.TriangleCount() != Data::TriangleCount || !Mesh.HasAttributes()) { Passed = false; return; }
        const auto* Normals = Mesh.Attributes()->PrimaryNormals();
        const auto* UVs = Mesh.Attributes()->PrimaryUV();
        const auto* Colors = Mesh.Attributes()->PrimaryColors();
        const auto* Materials = Mesh.Attributes()->HasMaterialID() ? Mesh.Attributes()->GetMaterialID() : nullptr;
        if (!Normals || !UVs || !Colors || !Materials || !Normals->IsTriangleStorageValid() || !UVs->IsTriangleStorageValid()
            || !Colors->IsTriangleStorageValid()) { Passed = false; return; }
        for (int32 Index = 0; Index < Data::TriangleCount; ++Index)
        {
            if (Materials->GetValue(Index) != Data::MaterialIds[Index]) { Passed = false; return; }
        }
        for (int32 Index = 0; Index < Data::VertexCount; ++Index)
        {
            if (!Mesh.IsVertex(Index)) { Passed = false; return; }
            OutPositionErrorCm = FMath::Max(OutPositionErrorCm, FVector::Distance(Mesh.GetVertex(Index), Vector(Data::Vertices[Index])));
        }
        for (int32 Index = 0; Index < Data::TriangleCount; ++Index)
        {
            const auto Expected = Data::Triangles[Index];
            const FIndex3i Native(Expected.A, Expected.C, Expected.B);
            if (!Mesh.IsTriangle(Index) || Mesh.GetTriangle(Index) != Native || !Normals->IsSetTriangle(Index) || !UVs->IsSetTriangle(Index))
            { Passed = false; return; }
            const FIndex3i NormalIDs = Normals->GetTriangle(Index), UVIDs = UVs->GetTriangle(Index);
            for (int32 Corner = 0; Corner < 3; ++Corner)
            {
                if (!Normals->IsElement(NormalIDs[Corner]) || !UVs->IsElement(UVIDs[Corner])) { Passed = false; return; }
                const FVector ActualNormal(Normals->GetElement(NormalIDs[Corner]));
                const FVector2f ActualUV = UVs->GetElement(UVIDs[Corner]);
                if (ActualNormal.ContainsNaN() || !FMath::IsFinite(ActualUV.X) || !FMath::IsFinite(ActualUV.Y)) { Passed = false; return; }
                OutNormalError = FMath::Max(OutNormalError, FVector::Distance(ActualNormal, Vector(Data::Normals[Native[Corner]])));
                const auto ExpectedUV = Data::UVs[Native[Corner]];
                OutUVError = FMath::Max(OutUVError, FVector2D::Distance(FVector2D(ActualUV), FVector2D(ExpectedUV.X, ExpectedUV.Y)));
            }
        }
    });
    return Passed && OutPositionErrorCm <= 0.1 && OutNormalError <= 1e-5 && OutUVError <= 1e-4;
}

void AMikdashEnclosure::ApplyKotelClosureVisibility()
{
    if (!bKotelClosureValidated || bKotelClosureDisabled) return;
    UStaticMeshComponent* Terrain = KotelClosureTerrain.Get();
    const bool Show = ActualVisible(Terrain);
    if (!Terrain || !Identity(Terrain->GetComponentTransform()) || !Identity(Terrain->GetOwner()->GetActorTransform()))
    {
        ClearKotelClosure();
        KotelClosureStatus = TEXT("guard:source-lost-or-moved");
        UE_LOG(LogTemp, Warning, TEXT("KotelClosureRuntimeV1 %s"), *KotelClosureStatus);
        return;
    }
    if (KotelClosure.IsValid() && KotelClosure->IsVisible() != Show)
    {
        double DeckError, PositionError, NormalError, UVError;
        if (!ValidateKotelClosureSources(DeckError) || !ValidateKotelClosureMesh(PositionError, NormalError, UVError))
        {
            ClearKotelClosure();
            KotelClosureStatus = TEXT("guard:state-swap-readback-failed");
            UE_LOG(LogTemp, Warning, TEXT("KotelClosureRuntimeV1 %s"), *KotelClosureStatus);
            return;
        }
        KotelClosure->SetVisibility(Show, false);
        KotelClosure->SetHiddenInGame(!Show, false);
        KotelClosure->SetCollisionEnabled(Show ? ECollisionEnabled::QueryOnly : ECollisionEnabled::NoCollision);
        if (!ValidateKotelClosureMesh(PositionError, NormalError, UVError))
        {
            ClearKotelClosure();
            KotelClosureStatus = TEXT("guard:collision-state-activation-failed");
            UE_LOG(LogTemp, Warning, TEXT("KotelClosureRuntimeV1 %s"), *KotelClosureStatus);
            return;
        }
        KotelClosureStatus = Show ? TEXT("active-visible") : TEXT("prepared-hidden");
        if (FParse::Param(FCommandLine::Get(), TEXT("MikdashKotelClosureDiagnostic")))
            UE_LOG(LogTemp, Display, TEXT("KotelClosureRuntimeV1 collision state readback %s"), *GetKotelClosureRuntimeReadback());
    }
    KotelClosureStatus = Show ? TEXT("active-visible") : TEXT("prepared-hidden");
}

FString AMikdashEnclosure::GetKotelClosureRuntimeStatus() const { return KotelClosureStatus; }
TSharedRef<FJsonObject> AMikdashEnclosure::KotelClosureReadback() const
{
    TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
    Row->SetStringField(TEXT("collisionPolicy"), TEXT("pawn-only-query-v1"));
    double DeckError, PositionError, NormalError, UVError;
    const bool SourcesPassed = ValidateKotelClosureSources(DeckError);
    const bool MeshPassed = ValidateKotelClosureMesh(PositionError, NormalError, UVError);
    const bool VisibilityPassed = bKotelClosureDisabled ? !KotelClosure.IsValid() : KotelClosure.IsValid() && ActualVisible(KotelClosure.Get()) == ActualVisible(KotelClosureTerrain.Get());
    Row->SetStringField(TEXT("status"), KotelClosureStatus);
    Row->SetBoolField(TEXT("disabled"), bKotelClosureDisabled);
    Row->SetBoolField(TEXT("passed"), SourcesPassed && MeshPassed && VisibilityPassed);
    Row->SetBoolField(TEXT("sourceIdentitiesTransformsMaterialsPhysicsIntact"), SourcesPassed);
    Row->SetBoolField(TEXT("meshReadbackPassed"), MeshPassed);
    Row->SetBoolField(TEXT("visibilityMatchesActualTerrain"), VisibilityPassed);
    Row->SetNumberField(TEXT("maxDeckTransformErrorCm"), DeckError);
    Row->SetNumberField(TEXT("maxPositionErrorCm"), PositionError);
    Row->SetNumberField(TEXT("maxNormalError"), NormalError);
    Row->SetNumberField(TEXT("maxUVError"), UVError);
    Row->SetObjectField(TEXT("terrain"), ComponentReadback(KotelClosureTerrain.Get()));
    Row->SetObjectField(TEXT("deck"), ComponentReadback(KotelClosureDeck.Get()));
    Row->SetObjectField(TEXT("closure"), ComponentReadback(KotelClosure.Get()));
    int32 Vertices = 0, Triangles = 0;
    if (KotelClosure.IsValid()) KotelClosure->ProcessMesh([&](const FDynamicMesh3& Mesh) { Vertices = Mesh.VertexCount(); Triangles = Mesh.TriangleCount(); });
    Row->SetNumberField(TEXT("vertexCount"), Vertices);
    Row->SetNumberField(TEXT("triangleCount"), Triangles);
    Row->SetNumberField(TEXT("terrainComponentCollisionModeBefore"), KotelClosureSourceCollisionModes[0]);
    Row->SetNumberField(TEXT("deckComponentCollisionModeBefore"), KotelClosureSourceCollisionModes[1]);
    Row->SetStringField(TEXT("terrainComponentCollisionProfileBefore"), KotelClosureSourceCollisionProfiles[0].ToString());
    Row->SetStringField(TEXT("deckComponentCollisionProfileBefore"), KotelClosureSourceCollisionProfiles[1].ToString());
    return Row;
}
FString AMikdashEnclosure::GetKotelClosureRuntimeReadback() const
{
    FString JSON;
    FJsonSerializer::Serialize(KotelClosureReadback(), TJsonWriterFactory<>::Create(&JSON));
    return JSON;
}
void AMikdashEnclosure::StartKotelClosureProbe()
{
    if (!FParse::Param(FCommandLine::Get(), TEXT("MikdashKotelClosureDiagnostic"))) return;
    UE_LOG(LogTemp, Display, TEXT("KotelClosureRuntimeV1 initial readback %s"), *GetKotelClosureRuntimeReadback());
    if (!FParse::Param(FCommandLine::Get(), TEXT("MikdashKotelClosureProbe"))) return;
    KotelClosureProbeStageStart = FPlatformTime::Seconds();
    KotelClosureProbeTicker = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateUObject(this, &AMikdashEnclosure::TickKotelClosureProbe), 0.5f);
}

bool AMikdashEnclosure::FinishKotelClosureProbe(const TCHAR* Reason)
{
    if (bKotelClosureProbeOwnsPhoto)
        if (UMikdashPhotoMode* Photo = UMikdashPhotoMode::Get(this)) Photo->Exit();
    bKotelClosureProbeOwnsPhoto = false;
    TSharedRef<FJsonObject> Receipt = MakeShared<FJsonObject>();
    Receipt->SetBoolField(TEXT("passed"), bKotelClosureProbePassed && KotelClosureProbeRows.Num() == 4);
    Receipt->SetStringField(TEXT("reason"), Reason);
    Receipt->SetStringField(TEXT("map"), GetWorld() ? GetWorld()->GetOutermost()->GetName() : TEXT("None"));
    Receipt->SetStringField(TEXT("planSha256"), UTF8_TO_TCHAR(Data::PlanSha256));
    Receipt->SetStringField(TEXT("wallSha256"), UTF8_TO_TCHAR(Data::WallSha256));
    Receipt->SetStringField(TEXT("legacyClosureSha256"), UTF8_TO_TCHAR(Data::LegacyClosureSha256));
    Receipt->SetStringField(TEXT("wallGeneratorSha256"), UTF8_TO_TCHAR(Data::WallGeneratorSha256));
    Receipt->SetStringField(TEXT("generatorSha256"), UTF8_TO_TCHAR(Data::GeneratorSha256));
    Receipt->SetStringField(TEXT("expectedSourceTerrainAssetSha256"), UTF8_TO_TCHAR(Data::TerrainSha256));
    Receipt->SetStringField(TEXT("sourceHashScope"), TEXT("frozen provenance only; runtime guards compare identities, transforms and runtime closure mesh readback, not asset-file SHA"));
    const bool Headless = FParse::Param(FCommandLine::Get(), TEXT("MikdashKotelClosureHeadless"));
    Receipt->SetBoolField(TEXT("headless"), Headless);
    Receipt->SetStringField(TEXT("scope"), Headless
        ? TEXT("headless native identity/geometry/visibility/physics readback only; no photo or visual acceptance")
        : TEXT("native identity/geometry/visibility/physics readback; PNG visual acceptance separate"));
    Receipt->SetBoolField(TEXT("disabled"), bKotelClosureDisabled);
    Receipt->SetArrayField(TEXT("states"), KotelClosureProbeRows);
    TArray<TSharedPtr<FJsonValue>> Photos;
    for (const FString& Path : KotelClosureProbePhotos) Photos.Add(MakeShared<FJsonValueString>(Path));
    Receipt->SetArrayField(TEXT("photoPaths"), Photos);
    Receipt->SetObjectField(TEXT("finalReadback"), KotelClosureReadback());
    FString JSON;
    FJsonSerializer::Serialize(Receipt, TJsonWriterFactory<>::Create(&JSON));
    const FString Directory = FPaths::ProjectSavedDir() / TEXT("Diagnostics");
    FPlatformFileManager::Get().GetPlatformFile().CreateDirectoryTree(*Directory);
    const FString Output = Directory / FString::Printf(TEXT("KotelClosureRuntimeV1-%lld.json"), FDateTime::UtcNow().GetTicks());
    const bool Saved = FFileHelper::SaveStringToFile(JSON, *Output);
    UE_LOG(LogTemp, Display, TEXT("KotelClosureRuntimeV1 probe complete passed=%d saved=%d receipt=%s"),
        bKotelClosureProbePassed && KotelClosureProbeRows.Num() == 4, Saved, *Output);
    KotelClosureProbeTicker.Reset();
    if (Saved) FPlatformMisc::RequestExit(false);
    return false; // an unsuccessful write stays in the log for the outer watchdog
}

bool AMikdashEnclosure::TickKotelClosureProbe(float DeltaSeconds)
{
    (void)DeltaSeconds;
    const double Now = FPlatformTime::Seconds();
    const double Elapsed = Now - KotelClosureProbeStageStart;
    UWorld* World = GetWorld();
    APlayerController* Controller = World ? World->GetFirstPlayerController() : nullptr;
    if (FParse::Param(FCommandLine::Get(), TEXT("MikdashKotelClosureHeadless")))
    {
        if (!Controller || !Controller->GetPawn())
        {
            if (KotelClosureProbeStage == 0 && Elapsed < 120.0) return true;
            bKotelClosureProbePassed = false;
            return FinishKotelClosureProbe(TEXT("failed-headless-no-player"));
        }
        if (KotelClosureProbeStage == 0)
        {
            KotelClosureProbeStage = 1;
            KotelClosureProbeStageStart = Now;
            return true;
        }
        if (KotelClosureProbeStage == 1)
        {
            if (Elapsed < 15.0) return true;
            SetPrecinctStateOver(ProbeStates[KotelClosureProbeStateIndex], 0.0f);
            KotelClosureProbeStage = 2;
            KotelClosureProbeStageStart = Now;
            return true;
        }
        if (Elapsed < 1.0) return true;
        TSharedRef<FJsonObject> Row = KotelClosureReadback();
        Row->SetStringField(TEXT("state"), ProbeStateNames[KotelClosureProbeStateIndex]);
        Row->SetStringField(TEXT("photoPath"), TEXT(""));
        Row->SetBoolField(TEXT("headless"), true);
        const bool ExpectedVisible = !bBuildPlaza || ProbeStates[KotelClosureProbeStateIndex] != EMikdashPrecinctState::Yechezkel;
        const UStaticMeshComponent* Terrain = KotelClosureTerrain.Get();
        const UInstancedStaticMeshComponent* Deck = KotelClosureDeck.Get();
        const bool StatePassed = Terrain && Deck && ActualVisible(Terrain) == ExpectedVisible
            && ActualVisible(Deck) == ExpectedVisible
            && Terrain->GetOwner()->GetActorEnableCollision() == ExpectedVisible
            && Deck->GetOwner()->GetActorEnableCollision() == ExpectedVisible;
        Row->SetBoolField(TEXT("sourceStateVisibilityAndActorCollisionPassed"), StatePassed);
        const bool Passed = Row->GetBoolField(TEXT("passed")) && StatePassed;
        Row->SetBoolField(TEXT("passed"), Passed);
        bKotelClosureProbePassed = bKotelClosureProbePassed && Passed;
        KotelClosureProbeRows.Add(MakeShared<FJsonValueObject>(Row));
        UE_LOG(LogTemp, Display, TEXT("KotelClosureRuntimeV1 headless state=%s passed=%d"),
            ProbeStateNames[KotelClosureProbeStateIndex], Passed);
        ++KotelClosureProbeStateIndex;
        if (KotelClosureProbeStateIndex >= UE_ARRAY_COUNT(ProbeStates)) return FinishKotelClosureProbe(TEXT("complete-headless"));
        SetPrecinctStateOver(ProbeStates[KotelClosureProbeStateIndex], 0.0f);
        KotelClosureProbeStageStart = Now;
        return true;
    }
    UMikdashPhotoMode* Photo = UMikdashPhotoMode::Get(this);
    if (KotelClosureProbeStage == 0)
    {
        if (!Controller || !Controller->GetPawn() || !Photo)
        {
            if (Elapsed < 120.0) return true;
            bKotelClosureProbePassed = false;
            return FinishKotelClosureProbe(TEXT("failed-no-player-or-photo-subsystem"));
        }
        // Do not seize an already active user photo session.
        if (Photo->IsActive())
        {
            bKotelClosureProbePassed = false;
            return FinishKotelClosureProbe(TEXT("failed-photo-already-active"));
        }
        KotelClosureProbeStage = 1;
        KotelClosureProbeStageStart = Now;
        return true;
    }
    if (!Controller || !Controller->GetPawn() || !Photo)
    {
        bKotelClosureProbePassed = false;
        return FinishKotelClosureProbe(TEXT("failed-player-lost"));
    }
    if (KotelClosureProbeStage == 1)
    {
        if (Elapsed < 15.0) return true;
        SetPrecinctStateOver(ProbeStates[KotelClosureProbeStateIndex], 0.0f);
        if (!Photo->Enter())
        {
            bKotelClosureProbePassed = false;
            return FinishKotelClosureProbe(TEXT("failed-photo-enter"));
        }
        bKotelClosureProbeOwnsPhoto = true;
        KotelClosureProbeStage = 2;
        KotelClosureProbeStageStart = Now;
        return true;
    }
    if (KotelClosureProbeStage == 2)
    {
        if (Elapsed < 3.0) return true;
        KotelClosureProbePhoto = Photo->TakePhoto(2);
        if (KotelClosureProbePhoto.IsEmpty())
        {
            bKotelClosureProbePassed = false;
            return FinishKotelClosureProbe(TEXT("failed-photo-request"));
        }
        KotelClosureProbeStage = 3;
        KotelClosureProbeStageStart = Now;
        return true;
    }
    if (KotelClosureProbeStage == 4)
    {
        if (Elapsed < 1.0) return true; // prior view target's 0.25s blend has finished
        SetPrecinctStateOver(ProbeStates[KotelClosureProbeStateIndex], 0.0f);
        if (!Photo->Enter())
        {
            bKotelClosureProbePassed = false;
            return FinishKotelClosureProbe(TEXT("failed-next-photo-enter"));
        }
        bKotelClosureProbeOwnsPhoto = true;
        KotelClosureProbeStage = 2;
        KotelClosureProbeStageStart = Now;
        return true;
    }
    if (Elapsed < 5.0) return true;
    if (FPlatformFileManager::Get().GetPlatformFile().FileSize(*KotelClosureProbePhoto) <= 0)
    {
        if (Elapsed < 30.0) return true;
        bKotelClosureProbePassed = false;
        return FinishKotelClosureProbe(TEXT("failed-png-timeout"));
    }
    TSharedRef<FJsonObject> Row = KotelClosureReadback();
    Row->SetStringField(TEXT("state"), ProbeStateNames[KotelClosureProbeStateIndex]);
    Row->SetStringField(TEXT("photoPath"), KotelClosureProbePhoto);
    Row->SetBoolField(TEXT("photoExists"), true);
    const bool ExpectedSourceVisible = !bBuildPlaza || ProbeStates[KotelClosureProbeStateIndex] != EMikdashPrecinctState::Yechezkel;
    const UStaticMeshComponent* Terrain = KotelClosureTerrain.Get();
    const UInstancedStaticMeshComponent* Deck = KotelClosureDeck.Get();
    const bool StatePassed = Terrain && Deck && ActualVisible(Terrain) == ExpectedSourceVisible
        && ActualVisible(Deck) == ExpectedSourceVisible
        && Terrain->GetOwner()->GetActorEnableCollision() == ExpectedSourceVisible
        && Deck->GetOwner()->GetActorEnableCollision() == ExpectedSourceVisible;
    Row->SetBoolField(TEXT("sourceStateVisibilityAndActorCollisionPassed"), StatePassed);
    const bool PhasePassed = Row->GetBoolField(TEXT("passed")) && StatePassed;
    Row->SetBoolField(TEXT("passed"), PhasePassed);
    bKotelClosureProbePassed = bKotelClosureProbePassed && PhasePassed;
    if (Controller->PlayerCameraManager)
    {
        const FMinimalViewInfo& Camera = Controller->PlayerCameraManager->GetCameraCacheView();
        Row->SetStringField(TEXT("cameraLocationCm"), Camera.Location.ToString());
        Row->SetStringField(TEXT("cameraRotation"), Camera.Rotation.ToString());
        Row->SetNumberField(TEXT("cameraFov"), Camera.FOV);
        Row->SetStringField(TEXT("viewTarget"), GetPathNameSafe(Controller->GetViewTarget()));
        Row->SetStringField(TEXT("pawn"), GetPathNameSafe(Controller->GetPawn()));
    }
    KotelClosureProbeRows.Add(MakeShared<FJsonValueObject>(Row));
    KotelClosureProbePhotos.Add(KotelClosureProbePhoto);
    UE_LOG(LogTemp, Display, TEXT("KotelClosureRuntimeV1 state=%s passed=%d photo=%s"),
        ProbeStateNames[KotelClosureProbeStateIndex], PhasePassed, *KotelClosureProbePhoto);
    Photo->Exit();
    bKotelClosureProbeOwnsPhoto = false;
    ++KotelClosureProbeStateIndex;
    if (KotelClosureProbeStateIndex >= UE_ARRAY_COUNT(ProbeStates)) return FinishKotelClosureProbe(TEXT("complete"));
    KotelClosureProbeStage = 4;
    KotelClosureProbeStageStart = Now;
    return true;
}

void AMikdashEnclosure::StopKotelClosureProbe()
{
    if (KotelClosureProbeTicker.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(KotelClosureProbeTicker);
        KotelClosureProbeTicker.Reset();
    }
    if (bKotelClosureProbeOwnsPhoto)
        if (UMikdashPhotoMode* Photo = UMikdashPhotoMode::Get(this)) Photo->Exit();
    bKotelClosureProbeOwnsPhoto = false;
}
