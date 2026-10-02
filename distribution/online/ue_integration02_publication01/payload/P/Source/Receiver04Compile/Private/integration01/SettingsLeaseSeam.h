#pragma once
#include "../runtime_settings03/SettingsOwnedCallback.h"

namespace MikdashOnline::Integration01 {
// No implementation of IOwnedSessionLease is invented here. The parent's
// private_settings_descriptor is NOT that lease and is absent from bootstrap v1.
inline TFunction<bool()> MakeConditionalSettingsCallback(
    TSharedPtr<const Settings01::IOwnedSessionLease> Lease,
    AMikdashPlayerController* Controller) {
    if(!Lease.IsValid()) return [](){return false;};
    return Settings01::MakeSettingsOwnedCallback(Lease.ToSharedRef(),Controller);
}
}
