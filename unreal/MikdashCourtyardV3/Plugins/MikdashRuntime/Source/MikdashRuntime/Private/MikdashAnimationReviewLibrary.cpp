#include "MikdashAnimationReviewLibrary.h"

#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"

bool UMikdashAnimationReviewLibrary::AdvanceReviewWorld(UObject* WorldContextObject, float DeltaSeconds)
{
#if WITH_EDITOR
    UWorld* World = IsValid(WorldContextObject) ? WorldContextObject->GetWorld() : nullptr;
    if (!IsRunningCommandlet() || !World || World->IsGameWorld() ||
        !World->GetOutermost()->GetName().StartsWith(TEXT("/Temp/")) ||
        !FMath::IsFinite(DeltaSeconds) || DeltaSeconds <= 0.f || DeltaSeconds > 1.f / 15.f)
    {
        return false;
    }
    const double Before = World->GetTimeSeconds();
    World->Tick(LEVELTICK_All, DeltaSeconds);
    return FMath::Abs((World->GetTimeSeconds() - Before) - DeltaSeconds) < 0.00001;
#else
    return false;
#endif
}

bool UMikdashAnimationReviewLibrary::EvaluateReviewPose(USkeletalMeshComponent* Component, UAnimSequence* Animation, float TimeSeconds)
{
#if WITH_EDITOR
    if (!IsRunningCommandlet() || !IsValid(Component) || !IsValid(Animation) ||
        !Component->IsRegistered() || !Component->GetOwner() ||
        !Component->GetOwner()->HasAnyFlags(RF_Transient) || !Component->GetWorld() ||
        Component->GetWorld()->IsGameWorld() || !FMath::IsFinite(TimeSeconds) ||
        TimeSeconds < 0.f || TimeSeconds > Animation->GetPlayLength())
    {
        return false;
    }
    const USkeletalMesh* Mesh = Component->GetSkeletalMeshAsset();
    if (!Mesh || Mesh->GetSkeleton() != Animation->GetSkeleton())
    {
        return false;
    }
    Component->SetAnimationMode(EAnimationMode::AnimationSingleNode);
    Component->SetAnimation(Animation);
    Component->SetPosition(TimeSeconds, false);
    Component->TickAnimation(0.f, false);
    Component->RefreshBoneTransforms();
    Component->UpdateComponentToWorld();
    Component->MarkRenderTransformDirty();
    Component->MarkRenderDynamicDataDirty();
    return true;
#else
    return false;
#endif
}
