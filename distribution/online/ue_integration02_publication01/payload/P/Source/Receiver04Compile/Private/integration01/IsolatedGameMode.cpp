#include "IsolatedGameMode.h"
#include "../native/receiver04/OnlineController.h"
#include "UObject/ConstructorHelpers.h"
#include "GameFramework/Pawn.h"

AReceiverIsolatedGameMode::AReceiverIsolatedGameMode() {
    PlayerControllerClass=AReceiver04Controller::StaticClass();
    DefaultPawnClass=nullptr; // missing real asset must not spawn DefaultPawn
    static ConstructorHelpers::FClassFinder<APawn> Walker(
        TEXT("/Game/MikdashV3/Gameplay/BP_MikdashWalker"));
    if(Walker.Succeeded()) DefaultPawnClass=Walker.Class;
}
