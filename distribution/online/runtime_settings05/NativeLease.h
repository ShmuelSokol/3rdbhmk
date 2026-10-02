#pragma once
#include "CoreMinimal.h"
#include "../runtime_settings03/SessionSettingsAdmission.h"
#include "../Native/receiver03/Wire.h"
namespace MikdashOnline::Settings05 {
// Game-thread only, one provisioning per process. No browser or second pipe API.
bool AdmitPrivateV2(const TArray<uint8>& Body,double Now,Receiver03::Bootstrap& Out);
TSharedPtr<const Settings01::IOwnedSessionLease> FindLease(const Owner& ExactOwner);
bool LeaseLive();
bool RevokeLease();
TFunction<bool()> MakeOwnedSettingsCallback(const Owner& ExactOwner,AMikdashPlayerController* Controller);
}
