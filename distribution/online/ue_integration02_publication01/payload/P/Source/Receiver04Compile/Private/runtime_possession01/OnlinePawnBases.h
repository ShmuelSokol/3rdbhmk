#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "MikdashDovePawn.h"
#include "OnlinePawnBases.generated.h"

// Native parent insertion for the EXISTING FirstPerson Blueprint parent chain.
// Never spawn this bare class or replace the measured BP_MikdashWalker asset.
// Asset reparent/compile validation is a separate, not-yet-executed editor step.
UCLASS()
class AReceiverPossessionWalkerBase : public ACharacter {
    GENERATED_BODY()
public:
    AReceiverPossessionWalkerBase(const FObjectInitializer& Init=FObjectInitializer::Get());
};

// Uses the actual project's collision, appearance, flight math and Tick code.
UCLASS()
class AReceiverPossessionDove : public AMikdashDovePawn {
    GENERATED_BODY()
public:
    AReceiverPossessionDove(const FObjectInitializer& Init=FObjectInitializer::Get());
};
