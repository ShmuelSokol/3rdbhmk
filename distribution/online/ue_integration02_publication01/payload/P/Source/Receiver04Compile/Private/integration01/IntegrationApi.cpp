#include "IsolatedGameMode.h"
#include "SettingsLeaseSeam.h"
#include "../runtime_possession01/OnlinePawnBases.h"
#include "../native/receiver04/OnlineMovement.h"
#include "../native/receiver04/OnlineController.h"
#include <type_traits>

static_assert(std::is_base_of_v<AMikdashDovePawn,AReceiverPossessionDove>);
static_assert(std::is_base_of_v<ACharacter,AReceiverPossessionWalkerBase>);
static_assert(std::is_base_of_v<AMikdashPlayerController,AReceiver04Controller>);
static_assert(std::is_same_v<decltype(&MikdashOnline::Receiver04::Authority::BeginPossession),
    bool (MikdashOnline::Receiver04::Authority::*)()>);

// Force compile of the real optional callback type. Not called on startup.
TFunction<bool()> ReceiverIntegrationSettingsApi(
    TSharedPtr<const MikdashOnline::Settings01::IOwnedSessionLease> Lease,
    AMikdashPlayerController* C) {
    return MikdashOnline::Integration01::MakeConditionalSettingsCallback(Lease,C);
}
