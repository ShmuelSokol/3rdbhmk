#pragma once
#include "SessionSettingsAdmission.h"
#include "MikdashPlayerController.h"
#include "MikdashSettings.h"
#include "MikdashSaveGame.h"
#include "Engine/GameInstance.h"

namespace MikdashOnline::Settings01 {
// Supply to existing ConfigureRemote SettingsOwnership parameter. This does not
// change that controller. Authority/pawn/fence checks remain in the existing caller.
inline TFunction<bool()> MakeSettingsOwnedCallback(
    TSharedRef<const IOwnedSessionLease> Lease, AMikdashPlayerController* Controller) {
    TWeakObjectPtr<AMikdashPlayerController> Weak(Controller);
    return [Lease,Weak]() {
        AMikdashPlayerController* C=Weak.Get();
        if(!IsInGameThread() || !C)return false;
        UGameInstance* GI=C->GetGameInstance();
        if(!GI)return false;
        FReadback Readback;
        // Paths/rejection may be recorded in a PRIVATE bounded runtime receipt by
        // the caller. Do not publish session roots or any config contents.
        return SettingsOwned(*Lease,C,GI->GetSubsystem<UMikdashSettingsSubsystem>(),
            GI->GetSubsystem<UMikdashSaveSystem>(),Readback);
    };
}
