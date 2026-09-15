#pragma once
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/UnrealType.h"

namespace LegacyRoofRuntime
{
// Exact native names for release_legacy_roof_zones.COPY_PROPERTIES. Navigation,
// overlap and collision use public APIs separately. Never copy UObject internals.
static const FName RenderProperties[] = {
    TEXT("Mobility"), TEXT("CastShadow"), TEXT("bCastDynamicShadow"),
    TEXT("bCastStaticShadow"), TEXT("bCastContactShadow"), TEXT("bCastFarShadow"),
    TEXT("bCastInsetShadow"), TEXT("bAffectDynamicIndirectLighting"), TEXT("bAffectDistanceFieldLighting"),
    TEXT("bVisibleInRayTracing"), TEXT("bVisibleInReflectionCaptures"), TEXT("bVisibleInRealTimeSkyCaptures"),
    TEXT("bRenderInMainPass"), TEXT("bRenderInDepthPass"), TEXT("bReceivesDecals"), TEXT("bUseAsOccluder"),
    TEXT("BoundsScale"), TEXT("MinDrawDistance"), TEXT("LDMaxDrawDistance"), TEXT("bNeverDistanceCull"),
    TEXT("bAllowCullDistanceVolume"), TEXT("InstanceStartCullDistance"), TEXT("InstanceEndCullDistance"),
    TEXT("bEvaluateWorldPositionOffset"), TEXT("WorldPositionOffsetDisableDistance"),
    TEXT("bReverseCulling"), TEXT("bDisallowNanite"), TEXT("ForcedLodModel"), TEXT("bOverrideMinLOD"),
    TEXT("MinLOD"), TEXT("LightmapType"), TEXT("LightingChannels"), TEXT("bRenderCustomDepth"),
    TEXT("CustomDepthStencilValue"), TEXT("CustomDepthStencilWriteMask"),
    TEXT("TranslucencySortPriority"), TEXT("TranslucencySortDistanceOffset")
};
inline bool Properties(UInstancedStaticMeshComponent* Source, UInstancedStaticMeshComponent* Target, bool Copy)
{
    for (FName Name : RenderProperties)
    {
        FProperty* Property = FindFProperty<FProperty>(UInstancedStaticMeshComponent::StaticClass(), Name);
        if (!Property) return false;
        if (Copy) Property->CopyCompleteValue_InContainer(Target, Source);
        if (!Property->Identical_InContainer(Source, Target)) return false;
    }
    return true;
}
inline bool CaptureProperties(const UInstancedStaticMeshComponent* Source, TArray<FString>& Values)
{
    Values.Reset();
    for (FName Name : RenderProperties)
    {
        FProperty* Property = FindFProperty<FProperty>(UInstancedStaticMeshComponent::StaticClass(), Name);
        if (!Property) return false;
        FString Value;
        // ExportText_Direct deliberately exports Data == Delta, including zero/false
        // values. A null Delta suppresses default-valued fields and returns false.
        const void* ValuePointer = Property->ContainerPtrToValuePtr<void>(Source);
        if (!Property->ExportText_Direct(Value, ValuePointer, ValuePointer, nullptr, PPF_None)) return false;
        Values.Add(Value);
    }
    return true;
}
inline bool Inert(const UInstancedStaticMeshComponent* Component)
{
    return Component && Component->GetCollisionEnabled() == ECollisionEnabled::NoCollision
        && Component->GetCollisionProfileName() == FName(TEXT("NoCollision"))
        && !Component->CanEverAffectNavigation() && !Component->GetGenerateOverlapEvents()
        && Component->NumCustomDataFloats == 0;
}
inline bool Finite(const FTransform& Transform)
{
    // ContainsNaN checks NaN AND infinity; IsValid additionally requires a unit quaternion.
    return Transform.IsValid() && !Transform.ContainsNaN();
}
inline double TransformError(const FTransform& A, const FTransform& B)
{
    double Error = 0.0;
    for (const FVector& Probe : {FVector::ZeroVector, FVector(100,0,0), FVector(0,100,0), FVector(0,0,100)})
        Error = FMath::Max(Error, FVector::Distance(A.TransformPosition(Probe), B.TransformPosition(Probe)));
    return Error;
}
inline FString MeshPath(int32 Group)
{
    const FString Name = Group == 0 ? TEXT("SM_JerusalemInstance_Rooftop_tanks") : TEXT("SM_JerusalemInstance_Rooftop_panels");
    return FString(TEXT("/Game/MikdashV3/JerusalemContext/DecorativeInstancesV1/Meshes/")) + Name + TEXT(".") + Name;
}
}
