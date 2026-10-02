#include "../runtime_settings05/NativeLease.h"
#include "MikdashPlayerController.h"
TFunction<bool()> ReceiverIntegrationSettingsV2Api(const MikdashOnline::Owner& Owner,AMikdashPlayerController* Controller){
    return MikdashOnline::Settings05::MakeOwnedSettingsCallback(Owner,Controller);
}
