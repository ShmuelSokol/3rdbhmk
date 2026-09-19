#include "MikdashAnimationReviewLibrary.h"

#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"

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
