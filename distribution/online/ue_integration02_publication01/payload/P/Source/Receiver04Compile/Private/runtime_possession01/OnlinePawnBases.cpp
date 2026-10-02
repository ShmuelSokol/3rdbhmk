#include "OnlinePawnBases.h"
#include "../native/receiver04/OnlineMovement.h"

AReceiverPossessionWalkerBase::AReceiverPossessionWalkerBase(const FObjectInitializer& Init)
    :Super(Init.SetDefaultSubobjectClass<UReceiver04WalkerMovement>(ACharacter::CharacterMovementComponentName)) {}
AReceiverPossessionDove::AReceiverPossessionDove(const FObjectInitializer& Init)
    :Super(Init.SetDefaultSubobjectClass<UReceiver04DoveMovement>(TEXT("FlightMovement"))) {}
