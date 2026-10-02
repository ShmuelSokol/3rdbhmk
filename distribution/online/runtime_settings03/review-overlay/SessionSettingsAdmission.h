#pragma once
// Review source only. Not compiled, installed, or exercised in Unreal.
#include "CoreMinimal.h"

class AMikdashPlayerController;
class UMikdashSettingsSubsystem;
class UMikdashSaveSystem;

namespace MikdashOnline::Settings01 {
// Supplied by trusted process bootstrap, NEVER by browser messages. No default pass.
// Implementer retains an exclusive session lease for the WHOLE process lifetime,
// including async saves/shutdown; see contract.json for ACL and race premises.
struct IOwnedSessionLease {
    virtual ~IOwnedSessionLease() = default;
    virtual bool IsLiveForCurrentProcess() const = 0;
    virtual FString Root() const = 0;
    virtual FString SettingsSlot() const = 0;
    virtual FString SavePrefix() const = 0;
    virtual uint32 RootVolumeSerial() const = 0;
    virtual uint64 RootFileId() const = 0;
};
struct FReadback {
    FString ProjectUser, ProjectSaved, GameIni, GameUserSettingsIni, SaveDirectory;
    TArray<FString> SaveFiles;
    FString Rejection;
};
// Call on game thread immediately before existing SettingsOwned caller consumes mute.
// No SaveConfig, SaveGame, file creation, config reload, or source mutation.
bool SettingsOwned(const IOwnedSessionLease& Lease,
    const AMikdashPlayerController* Controller,
    const UMikdashSettingsSubsystem* Settings,
    const UMikdashSaveSystem* Saves, FReadback& Out);
}
