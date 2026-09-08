#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MikdashDoveAppearance.generated.h"

class UStaticMesh;

/** Map-placed reference holder for the original DoveV2 meshes (body, left wing, right wing).
 * The dove pawn is spawned from C++ at runtime, so this actor is what makes the imported
 * meshes part of the level's hard references (and therefore cooked). One per map, written
 * by Scripts/release_dove_people_v2.py. Without it the pawn keeps its procedural silhouette.
 */
UCLASS(BlueprintType)
class MIKDASHRUNTIME_API AMikdashDoveAppearance : public AActor
{
    GENERATED_BODY()
public:
    AMikdashDoveAppearance();
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Dove") TObjectPtr<UStaticMesh> BodyMesh;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Dove") TObjectPtr<UStaticMesh> LeftWingMesh;
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Dove") TObjectPtr<UStaticMesh> RightWingMesh;
    /** Local offset of the wing pivots (shoulders) relative to the body origin, cm. */
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Dove") FVector LeftShoulderCm = FVector(2.f, -7.f, 6.f);
    UPROPERTY(EditInstanceOnly, BlueprintReadOnly, Category="Dove") FVector RightShoulderCm = FVector(2.f, 7.f, 6.f);
    bool IsComplete() const { return BodyMesh && LeftWingMesh && RightWingMesh; }
};
