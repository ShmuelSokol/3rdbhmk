#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "IsolatedGameMode.generated.h"

// Isolated integration project only; never installs a replacement walker asset.
UCLASS()
class AReceiverIsolatedGameMode : public AGameModeBase {
    GENERATED_BODY()
public:
    AReceiverIsolatedGameMode();
};
