#pragma once
#include "Kismet/BlueprintFunctionLibrary.h"
#include "KohenClothExecutableLibrary.generated.h"
class USkeletalMesh;
class UAnimSequence;

UCLASS()
class KOHENCLOTHEXECUTABLE_API UKohenClothExecutableLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    // Only in KohenClothReview project; duplicates imported source transiently.
    // Atomic readback receipts, no asset saves. API feasibility, not garment acceptance.
    UFUNCTION(BlueprintCallable, Category="Kohen Cloth Isolated Review")
    static FString RunOneWalk(USkeletalMesh* ImportedSource, UAnimSequence* Walk,
        const FString& PreparedInputPath, const FString& FreshOutputDirectory);
};
