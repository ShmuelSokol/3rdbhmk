#include "NativeLease.h"
#include "Windows/WindowsHWrapper.h"
#include "WinLease.h"
#include "../runtime_settings03/SettingsOwnedCallback.h"
#include "../runtime_candidate05/PrivateBootstrap.h"

namespace MikdashOnline::Settings05 {
class FNativeLease final : public Settings01::IOwnedSessionLease {
public:
    Owner Identity;Descriptor Data;mutable WinLease Kernel;
    bool IsLiveForCurrentProcess() const override {return IsInGameThread()&&Kernel.Live();}
    FString Root() const override {return UTF8_TO_TCHAR(Data.root.c_str());}
    FString SettingsSlot() const override {return UTF8_TO_TCHAR(Identity.settings_slot.c_str());}
    FString SavePrefix() const override {return UTF8_TO_TCHAR(Identity.save_prefix.c_str());}
    uint32 RootVolumeSerial() const override {return Data.volume;}
    uint64 RootFileId() const override {return Data.file;}
};
static TSharedPtr<FNativeLease> Active;
static bool Used=false;
bool AdmitPrivateV2(const TArray<uint8>& Body,double Now,Receiver03::Bootstrap& Out){
    check(IsInGameThread());
    if(Used)return false;Used=true;
    Descriptor D;std::vector<uint8_t> Original;
    if(!Envelope(Body.GetData(),Body.Num(),Original,D))return false;
    TArray<uint8> V1;V1.Append(Original.data(),int32(Original.size()));
    const bool Valid=RuntimeCandidate05::ValidatePrivateRecord(V1,Now,Out);
    FMemory::Memzero(V1.GetData(),V1.Num());FMemory::Memzero(Original.data(),Original.size());
    if(!Valid)return false;
    auto Slot=[](const std::string& S){
        if(S.empty()||S.size()>64)return false;
        for(char C:S)if(!((C>='a'&&C<='z')||(C>='A'&&C<='Z')||(C>='0'&&C<='9')||C=='_'||C=='-'))return false;
        return RootSyntax("C:/"+S);
    };
    if(!Slot(Out.Identity.settings_slot)||!Slot(Out.Identity.save_prefix)||
       D.root.size()+sizeof("/User/Saved/Config/Windows/GameUserSettings.ini")-1>240||
       D.root.size()+sizeof("/User/Saved/SaveGames/")-1+Out.Identity.settings_slot.size()+4>240||
       D.root.size()+sizeof("/User/Saved/SaveGames/")-1+Out.Identity.save_prefix.size()+9>240)return false;
    for(unsigned I=0;I<=64;++I){
        const FString Other=I==64?UTF8_TO_TCHAR((Out.Identity.save_prefix+"_Auto").c_str()):
            FString::Printf(TEXT("%s_%02u"),UTF8_TO_TCHAR(Out.Identity.save_prefix.c_str()),I);
        if(Other.Equals(UTF8_TO_TCHAR(Out.Identity.settings_slot.c_str()),ESearchCase::IgnoreCase))return false;
    }
    Active=MakeShared<FNativeLease>();Active->Identity=Out.Identity;Active->Data=D;
    if(!Active->Kernel.Bind(D,Out.Deadline)){RevokeLease();return false;}
    return true;
}
TSharedPtr<const Settings01::IOwnedSessionLease> FindLease(const Owner& ExactOwner){
    check(IsInGameThread());
    if(!Active.IsValid()||!(Active->Identity==ExactOwner)||!Active->IsLiveForCurrentProcess())return nullptr;
    return Active;
}
bool LeaseLive(){check(IsInGameThread());return Active.IsValid()&&Active->IsLiveForCurrentProcess();}
bool RevokeLease(){
    check(IsInGameThread());
    if(!Active.IsValid())return true;
    Active->Kernel.Revoke();
    if(!Active->Kernel.Close())return false; // retain failed handles, never re-admit
    Active.Reset();return true;
}
TFunction<bool()> MakeOwnedSettingsCallback(const Owner& ExactOwner,AMikdashPlayerController* Controller){
    check(IsInGameThread());
    auto Lease=FindLease(ExactOwner);if(!Lease.IsValid())return [](){return false;};
    auto Check=Settings01::MakeSettingsOwnedCallback(Lease.ToSharedRef(),Controller);
    TWeakObjectPtr<AMikdashPlayerController> Weak(Controller);
    const unsigned Slots=Active->Data.slots;
    return [Check=MoveTemp(Check),Weak,ExactOwner,Slots](){
        if(!IsInGameThread()||!FindLease(ExactOwner).IsValid())return false;
        auto* C=Weak.Get();auto* GI=C?C->GetGameInstance():nullptr;
        auto* Saves=GI?GI->GetSubsystem<UMikdashSaveSystem>():nullptr;
        // Frozen03 validates 1..64; v2 additionally binds the exact allocated count.
        return Saves&&Saves->SlotCount==int32(Slots)&&Check()&&FindLease(ExactOwner).IsValid();
    };
}
}
