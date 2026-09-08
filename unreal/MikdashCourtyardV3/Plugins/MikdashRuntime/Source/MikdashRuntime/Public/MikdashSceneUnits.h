#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MikdashSceneUnitsMath.h"
#include "MikdashSceneUnits.generated.h"

UENUM(BlueprintType)
enum class EMikdashSceneCoordinateRevision : uint8
{
    Legacy50V1,
    Selected48V1
};

/** A world-scoped declaration, not an actor-scale operation. One per candidate.
 * Existing unmarked worlds retain their historical legacy50 interpretation. */
UCLASS(BlueprintType)
class MIKDASHRUNTIME_API AMikdashSceneUnits : public AActor
{
    GENERATED_BODY()
public:
    AMikdashSceneUnits();

    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Mikdash|Scene units")
    int32 DescriptorSchemaVersion = 1;

    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Mikdash|Scene units")
    EMikdashSceneCoordinateRevision CoordinateRevision = EMikdashSceneCoordinateRevision::Legacy50V1;

    /** Must exactly match Legacy50.v1 or Selected48.v1 for the selected enum. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Mikdash|Scene units")
    FName SceneRevision = TEXT("Legacy50.v1");

    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Mikdash|Scene units")
    FVector FixedArchitectureOriginCm = FVector::ZeroVector;

    UFUNCTION(BlueprintPure, Category="Mikdash|Scene units")
    bool ValidateDescriptor(FString& Error) const;

    /** Only decode immutable legacy architectural inputs, never candidate-native properties. */
    UFUNCTION(BlueprintCallable, Category="Mikdash|Scene units")
    bool ConvertLegacyTemplePoint(FVector LegacyPoint, FVector& Converted, FString& Error) const;

    /** Converts floor/support geometry while preserving a real-world body/eye height. */
    UFUNCTION(BlueprintCallable, Category="Mikdash|Scene units")
    bool PlaceAboveLegacyTempleSupport(FVector LegacySupport, double PhysicalHeightCm,
                                      FVector& Converted, FString& Error) const;

    bool TryGetFrame(MikdashSceneUnits::Frame& Frame, FString& Error) const;
    static bool Resolve(const UWorld* World, MikdashSceneUnits::Frame& Frame, FString& Error);
};
