#include "SessionSettingsAdmission.h"
#include "MikdashPlayerController.h"
#include "MikdashSettings.h"
#include "MikdashSaveGame.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/CoreDelegates.h"
#include "Misc/Paths.h"
#include "HAL/PlatformFileManager.h"
#include "HAL/PlatformFile.h"
#include "PlatformFeatures.h"
#include "SaveGameSystem.h"
#include "UObject/UnrealType.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "GameFramework/GameUserSettings.h"
#if PLATFORM_WINDOWS
#include "Windows/WindowsHWrapper.h"
#endif

namespace MikdashOnline::Settings01 {
namespace {
bool Component(const FString& S) {
    if(S.IsEmpty() || S.Len()>100 || S==TEXT(".") || S==TEXT("..") ||
       S.EndsWith(TEXT(".")) || S.EndsWith(TEXT(" "))) return false;
    for(TCHAR C:S) if(!((C>='a'&&C<='z') || (C>='A'&&C<='Z') ||
        (C>='0'&&C<='9') || C=='_' || C=='-' || C=='.' || C==' ')) return false;
    FString Stem=S; int32 Dot;
    if(Stem.FindChar('.',Dot)) Stem.LeftInline(Dot);
    Stem.ToUpperInline();
    if(Stem==TEXT("CON") || Stem==TEXT("PRN") || Stem==TEXT("AUX") || Stem==TEXT("NUL")) return false;
    if(Stem.Len()==4 && (Stem.StartsWith(TEXT("COM")) || Stem.StartsWith(TEXT("LPT"))) &&
       Stem[3]>='0' && Stem[3]<='9') return false;
    return true;
}
bool Canon(const FString& In,FString& Out) {
    Out=In.Replace(TEXT("\\"),TEXT("/"));
    if(Out.Len()<4 || Out.Len()>240 || !FChar::IsAlpha(Out[0]) || Out[0]>127 ||
       Out[1]!=':' || Out[2]!='/') return false;
    if(Out.EndsWith(TEXT("/"))) Out.LeftChopInline(1);
    TArray<FString> Parts; Out.Mid(3).ParseIntoArray(Parts,TEXT("/"),false);
    for(const FString& P:Parts) if(!Component(P)) return false;
    return Parts.Num()>0;
}
bool Same(const FString& A,const FString& B) {
    FString X,Y; return Canon(A,X)&&Canon(B,Y)&&X.Equals(Y,ESearchCase::IgnoreCase);
}
// Require pre-created directories. Only the final regular file may be missing.
// Every existing ancestor, including the drive root, is opened without following
// reparses; final DOS path must equal the lexical path (reject aliases/mounts).
bool DiskPath(const FString& Path,bool Directory,uint32* Volume=nullptr,uint64* Id=nullptr) {
#if PLATFORM_WINDOWS
    FString P; if(!Canon(Path,P)) return false;
    if(::GetDriveTypeW(*P.Left(3))!=DRIVE_FIXED)return false;
    TArray<FString> Parts; P.Mid(3).ParseIntoArray(Parts,TEXT("/"),false);
    FString Current=P.Left(3);
    for(int32 I=-1;I<Parts.Num();++I) {
        if(I>=0) {if(!Current.EndsWith(TEXT("/")))Current+=TEXT("/"); Current+=Parts[I];}
        const bool Last=I==Parts.Num()-1;
        HANDLE H=::CreateFileW(*Current,FILE_READ_ATTRIBUTES,
            FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,
            FILE_FLAG_BACKUP_SEMANTICS|FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
        if(H==INVALID_HANDLE_VALUE) {
            return Last && !Directory && ::GetLastError()==ERROR_FILE_NOT_FOUND;
        }
        BY_HANDLE_FILE_INFORMATION Info{}; WCHAR Name[1024]{};
        const bool Got=::GetFileInformationByHandle(H,&Info)!=0;
        const DWORD N=::GetFinalPathNameByHandleW(H,Name,1024,FILE_NAME_NORMALIZED|VOLUME_NAME_DOS);
        ::CloseHandle(H);
        FString Final=N>0&&N<1024?FString(Name):FString();
        if(Final.StartsWith(TEXT("\\\\?\\"))) Final=Final.Mid(4);
        Final.ReplaceInline(TEXT("\\"),TEXT("/"));
        if(!Got || !N || N>=1024 || !Final.Equals(Current,ESearchCase::IgnoreCase) ||
            (Info.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT)) return false;
        const bool IsDir=(Info.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)!=0;
        if(IsDir != (!Last||Directory)) return false;
        if(!IsDir && Info.nNumberOfLinks!=1) return false;
        if(Last) {
            if(Volume)*Volume=Info.dwVolumeSerialNumber;
            if(Id)*Id=(uint64(Info.nFileIndexHigh)<<32)|Info.nFileIndexLow;
        }
    }
    return true;
#else
    return false;
#endif
}
bool Branch(const FString& Key,const FString& Expected,FString& Actual) {
    if(Key.IsEmpty())return false;
    FConfigBranch* B=GConfig->FindBranchWithNoReload(FName(*Key),Key);
    if(!B||B->bIsSafeUnloaded)return false;
    Actual=FPaths::ConvertRelativePathToFull(B->IniPath);
    return Same(Actual,Expected)&&DiskPath(Actual,false);
}
bool ConfigObject(const UObject* Obj,const FString& Expected) {
    if(!IsValid(Obj))return false;
    const UClass* C=Obj->GetClass();
    if(C->ClassConfigName!=FName(TEXT("Game")) || !C->HasAnyClassFlags(CLASS_Config) ||
       C->HasAnyClassFlags(CLASS_DefaultConfig|CLASS_GlobalUserConfig|CLASS_PerObjectConfig))return false;
    // Avoid invoking GetConfigName's loading fallback: Game is already known.
    if(!GConfig->IsKnownConfigName(C->ClassConfigName))return false;
    FString Actual;
    if(!Branch(C->GetConfigName(),Expected,Actual))return false;
    // SaveConfig may route inherited GlobalConfig properties to their owner class.
    // Reject this wider write surface instead of assuming all go to Game.ini.
    for(TFieldIterator<FProperty> It(C);It;++It)
        if(It->HasAnyPropertyFlags(CPF_Config|CPF_GlobalConfig) &&
           It->HasAnyPropertyFlags(CPF_GlobalConfig))return false;
    return true;
}
bool StockFileChain() {
#if PLATFORM_USE_PLATFORM_FILE_MANAGED_STORAGE_WRAPPER
    return false; // Managed-storage write behavior is outside this audited closure.
#else
    IPlatformFile* P=&FPlatformFileManager::Get().GetPlatformFile();
    // Audited Pak OpenWrite forwards the identical path to LowerLevel. No sandbox,
    // network, profiling/custom wrapper accepted merely because it has a lower level.
    if(FCString::Strcmp(P->GetName(),TEXT("PakFile"))==0) P=P->GetLowerLevel();
    return P==&IPlatformFile::GetPlatformPhysical() && P->GetLowerLevel()==nullptr;
#endif
}
}
bool SettingsOwned(const IOwnedSessionLease& Lease,const AMikdashPlayerController* Controller,
    const UMikdashSettingsSubsystem* Settings,const UMikdashSaveSystem* Saves,FReadback& Out) {
    Out=FReadback();
    auto Fail=[&](const TCHAR* Why){Out.Rejection=Why;return false;};
    if(!IsInGameThread() || GIsEditor || !Lease.IsLiveForCurrentProcess())return Fail(TEXT("ownership/thread/runtime"));
    if(!IsValid(Controller)||!IsValid(Settings)||!IsValid(Saves))return Fail(TEXT("live objects"));
    UGameInstance* GI=Controller->GetGameInstance();
    if(!GI || GI->GetSubsystem<UMikdashSettingsSubsystem>()!=Settings ||
       GI->GetSubsystem<UMikdashSaveSystem>()!=Saves ||
       Settings->GetClass()!=UMikdashSettingsSubsystem::StaticClass() ||
       Saves->GetClass()!=UMikdashSaveSystem::StaticClass())return Fail(TEXT("subsystem identity"));
    UGameUserSettings* Graphics=GEngine?GEngine->GetGameUserSettings():nullptr;
    if(!Graphics || Graphics->GetClass()!=UGameUserSettings::StaticClass() ||
       Graphics->OnUpdateCloudDataFromGameUserSettings.IsBound() ||
       Graphics->OnUpdateGameUserSettingsFileFromCloud.IsBound())return Fail(TEXT("graphics/cloud backend"));
    FString Root; if(!Canon(Lease.Root(),Root))return Fail(TEXT("root syntax"));
    uint32 Volume=0; uint64 Id=0;
    if(!DiskPath(Root,true,&Volume,&Id) || Volume!=Lease.RootVolumeSerial() || Id!=Lease.RootFileId())
        return Fail(TEXT("root identity/reparse"));
    if(!GConfig || GConfig->AreFileOperationsDisabled() || !StockFileChain() ||
       FCoreDelegates::TSPreSaveConfigFileDelegate().IsBound())return Fail(TEXT("config/file backend"));
    Out.ProjectUser=FPaths::ConvertRelativePathToFull(FPaths::ProjectUserDir());
    Out.ProjectSaved=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());
    if(!Same(Out.ProjectUser,Root+TEXT("/User")) || !Same(Out.ProjectSaved,Root+TEXT("/User/Saved")) ||
       !DiskPath(Out.ProjectSaved,true))return Fail(TEXT("effective user/saved paths"));
    const FString IniDir=Root+TEXT("/User/Saved/Config/Windows");
    const FString Game=IniDir+TEXT("/Game.ini");
    if(!Branch(GGameIni,Game,Out.GameIni) || !ConfigObject(Controller,Game) ||
       !ConfigObject(Settings,Game) || !ConfigObject(Saves,Game) ||
       !Branch(GGameUserSettingsIni,IniDir+TEXT("/GameUserSettings.ini"),Out.GameUserSettingsIni))
        return Fail(TEXT("effective INI destination/class"));
    FConfigBranch* EngineBranch=GConfig->FindBranchWithNoReload(FName(*GEngineIni),GEngineIni);
    FString CustomBackend;
    if(!EngineBranch || EngineBranch->bIsSafeUnloaded || IsRunningDedicatedServer())
        return Fail(TEXT("platform config/runtime"));
    const TCHAR* ModuleName=FPlatformMisc::GetPlatformFeaturesModuleName();
    if(!ModuleName || FCString::Strcmp(ModuleName,TEXT("WindowsPlatformFeatures"))!=0 ||
       !FModuleManager::GetModulePtr<IPlatformFeaturesModule>(FName(ModuleName)))
        return Fail(TEXT("platform backend not initialized"));
    GConfig->GetString(TEXT("PlatformFeatures"),TEXT("SaveGameSystemModule"),CustomBackend,GEngineIni);
    if(!CustomBackend.IsEmpty())return Fail(TEXT("custom save module configured"));
    IPlatformFeaturesModule& Features=IPlatformFeaturesModule::Get();
    // Qualified base call obtains the actual shared generic singleton, not a cast,
    // a fresh lookalike instance, or an assumption about SaveGameSystemModule config.
    if(Features.GetSaveGameSystem()!=Features.IPlatformFeaturesModule::GetSaveGameSystem())
        return Fail(TEXT("unsupported save backend"));
    Out.SaveDirectory=Out.ProjectSaved/TEXT("SaveGames");
    if(!Same(Out.SaveDirectory,Root+TEXT("/User/Saved/SaveGames")) || !DiskPath(Out.SaveDirectory,true))
        return Fail(TEXT("save directory"));
    if(!Component(Lease.SettingsSlot()) || !Component(Lease.SavePrefix()) ||
       Settings->SaveSlot!=Lease.SettingsSlot() || Saves->SlotNamePrefix!=Lease.SavePrefix() ||
       Settings->SaveUserIndex!=0 || Saves->UserIndex!=0 || Saves->SlotCount<1 || Saves->SlotCount>64)
        return Fail(TEXT("slot ownership/bounds"));
    TSet<FString> Slots; Slots.Add(Settings->SaveSlot.ToLower());
    Out.SaveFiles.Add(Out.SaveDirectory/(Settings->SaveSlot+TEXT(".sav")));
    for(int32 I=0;I<=Saves->SlotCount;++I) {
        FString Slot=Saves->MakeSlotName(I);
        if(!Component(Slot)||Slots.Contains(Slot.ToLower()))return Fail(TEXT("slot traversal/collision"));
        Slots.Add(Slot.ToLower()); Out.SaveFiles.Add(Out.SaveDirectory/(Slot+TEXT(".sav")));
    }
    for(const FString& File:Out.SaveFiles)if(!DiskPath(File,false))return Fail(TEXT("save file alias/reparse"));
    // Caller must immediately revalidate its existing Authority fence after this
    // bounded IO, then consume. The lifetime lease prevents external path races.
    if(!Lease.IsLiveForCurrentProcess())return Fail(TEXT("expired ownership"));
    return true;
}
}
