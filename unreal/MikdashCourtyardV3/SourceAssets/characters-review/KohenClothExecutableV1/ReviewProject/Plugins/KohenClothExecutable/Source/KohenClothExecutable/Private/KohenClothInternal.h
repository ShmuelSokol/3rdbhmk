#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "SkeletalMeshTypes.h"
#include "UObject/StrongObjectPtr.h"
#include "Engine/SkeletalMesh.h"
#include "ChaosClothAsset/ClothAsset.h"

namespace KohenCloth
{
struct FPattern
{
    FString Name;
    bool Dynamic = false;
    int32 Start = 0;
    TArray<FVector3f> Points;
    TArray<uint32> Indices;
    TArray<TArray<int32>> Bones;
    TArray<TArray<float>> Weights;
    TArray<float> MaxDistance;
};
struct FStudy
{
    TStrongObjectPtr<USkeletalMesh> Clone;
    TStrongObjectPtr<UChaosClothAsset> Cloth;
    TArray<FPattern> Patterns;
    TArray<FVector3f> Points, Normals;
    TArray<uint32> Indices;
    TArray<FMeshToMeshVertData> Mapping;
    TArray<FTransform> RefGlobal;
    TArray<int32> BoneRemap;
    FIntVector Perm = FIntVector(0,1,2);
    FVector3f Signs = FVector3f(1,1,1);
    int32 Section = INDEX_NONE;
    int32 OuterCount = 0;
    int32 TetherCount = 0;
    TArray<TArray<int32>> TetherAnchors;
    TArray<TArray<float>> TetherLengths;
    FString SourceDigest, UnboundDigest;
    FVector3f ToNative(const FVector3f& V) const { return FVector3f(V[Perm.X], V[Perm.Y], V[Perm.Z]) * Signs; }
    FVector3f ToAuthor(const FVector3f& V) const
    { FVector3f R; R[Perm.X]=V.X*Signs.X; R[Perm.Y]=V.Y*Signs.Y; R[Perm.Z]=V.Z*Signs.Z; return R; }
};
bool Build(USkeletalMesh* Source, const FString& Input, FStudy& S, FString& Error);
FString Digest(USkeletalMesh* Mesh, int32 ExcludedSection = INDEX_NONE);
FString JsonText(const TSharedRef<FJsonObject>& Object);
bool WriteJson(const FString& Path, const TSharedRef<FJsonObject>& Object);
bool WriteBinary(const FString& Path, const TArray<float>& Floats);
FVector3f Embed(const FMeshToMeshVertData& Map, TConstArrayView<FVector3f> Points,
               TConstArrayView<FVector3f> Normals);
bool ValidateMapping(const FStudy& S, const TArray<FMeshToMeshVertData>& Mapping, FString& Error);
}
