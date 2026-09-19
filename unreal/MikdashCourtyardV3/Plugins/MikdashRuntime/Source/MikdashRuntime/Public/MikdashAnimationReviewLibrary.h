#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "MikdashAnimationReviewLibrary.generated.h"

class UAnimSequence;
class USkeletalMeshComponent;

/** Explicit pose evaluation for isolated editor commandlet visual reviews. */
UCLASS()
class MIKDASHRUNTIME_API UMikdashAnimationReviewLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category="Mikdash|Review")
    static bool EvaluateReviewPose(USkeletalMeshComponent* Component, UAnimSequence* Animation, float TimeSeconds);

    /** Advance an unsaved commandlet review world for consecutive shader frames. */
    UFUNCTION(BlueprintCallable, Category="Mikdash|Review")
    static bool AdvanceReviewWorld(UObject* WorldContextObject, float DeltaSeconds);
};
