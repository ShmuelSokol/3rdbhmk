// MikdashSaveGame.cpp -- the engine half of save and resume.
//
// The byte format is not here. It is in Public/SaveMigrationMath.h and is tested by
// Tests/SaveMigrationMathTest.cpp without an editor. This file captures the world into a
// MikdashSave::FSaveRecord, hands it to that encoder, and writes the bytes through
// ISaveGameSystem; and the reverse.

#include "MikdashSaveGame.h"

#include "Containers/Ticker.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerStart.h"
#include "Misc/CoreDelegates.h"
#include "Misc/DateTime.h"
#include "PlatformFeatures.h"
#include "SaveGameSystem.h"
#include "UObject/Package.h"
#include "UObject/UnrealType.h"

#include "MikdashLocalization.h"
#include "MikdashSettings.h"
#include "MikdashTimeOfDay.h"
#include "MikdashSceneUnits.h"
#include "SaveSceneIdentity.h"

DEFINE_LOG_CATEGORY_STATIC(LogMikdashSave, Log, All);

namespace
{
    FString ToUtf8String(const std::string& In)
    {
        return FString(UTF8_TO_TCHAR(In.c_str()));
    }

    std::string FromFString(const FString& In)
    {
        // FTCHARToUTF8::Get() returns const UTF8CHAR*, and UTF8CHAR is char8_t on this
        // platform, not char. The engine's own TCHAR_TO_UTF8 macro casts for exactly this
        // reason; the cast is safe because both are one byte and the bytes are already
        // UTF-8. Length() is the byte count, so a Hebrew label survives intact.
        const FTCHARToUTF8 Converted(*In);
        return std::string(reinterpret_cast<const char*>(Converted.Get()),
                           static_cast<size_t>(Converted.Length()));
    }

    /** The save format's option types, kept in step with MikdashSave::EOptionType. */
    MikdashSave::FOptionValue MakeBoolOption(const FString& Key, bool Value)
    {
        MikdashSave::FOptionValue Option;
        Option.Key = FromFString(Key);
        Option.Type = MikdashSave::EOptionType::Bool;
        Option.BoolValue = Value;
        return Option;
    }

    std::string CurrentMapPackage(const UWorld* World)
    {
        return World ? FromFString(UWorld::RemovePIEPrefix(World->GetOutermost()->GetName())) : std::string();
    }

    /** Validate a walking capsule and a walkable support in this world. No NullRHI
     * guesses, no saved-coordinate scaling, and no resizing of the actual capsule. */
    bool SafeWalkingPosition(const ACharacter* Character, const FVector& Centre)
    {
        if (!Character || Centre.ContainsNaN() || !Character->GetActorEnableCollision()) return false;
        const UWorld* World = Character->GetWorld();
        const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
        const UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
        if (!World || !Capsule || !Movement) return false;
        const float Radius = Capsule->GetScaledCapsuleRadius();
        const float HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
        if (Radius <= 2.f || HalfHeight <= 2.f) return false;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(MikdashSaveSafePosition), false, Character);
        FHitResult Floor;
        if (!World->LineTraceSingleByChannel(Floor, Centre,
            Centre - FVector(0,0,HalfHeight + Movement->MaxStepHeight + 8.f), ECC_Visibility, Query)
            || !Floor.bBlockingHit || !Movement->IsWalkable(Floor)) return false;
        const double FloorGap = Centre.Z - HalfHeight - Floor.ImpactPoint.Z;
        if (FloorGap < -3.0 || FloorGap > Movement->MaxStepHeight + 5.0) return false;
        // Two centimetres of query skin avoids treating floor contact as penetration.
        const FCollisionShape Shape = FCollisionShape::MakeCapsule(Radius-2.f, HalfHeight-2.f);
        return !World->OverlapBlockingTestByChannel(Centre + FVector(0,0,2), FQuat::Identity,
            ECC_Pawn, Shape, Query);
    }
}

// ---------------------------------------------------------------------------
// lifetime
// ---------------------------------------------------------------------------

void UMikdashSaveSystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);

    // The settings subsystem is a dependency in one direction only: this reads its record
    // for the options snapshot. Asking for it here rather than on demand means the
    // ordering is fixed and explicit instead of depending on which one ticks first.
    Collection.InitializeDependency(UMikdashSettingsSubsystem::StaticClass());

    SlotCount = FMath::Clamp(SlotCount, 1, 64);
    if (SlotNamePrefix.IsEmpty())
    {
        SlotNamePrefix = TEXT("MikdashSave");
    }

    NextPeriodicAutosaveRealSeconds = FPlatformTime::Seconds() + FMath::Max(PeriodicAutosaveSeconds, 0.0f);

    TickHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateUObject(this, &UMikdashSaveSystem::TickSave), 0.0f);

    if (bAutosaveOnQuit)
    {
        PreExitHandle = FCoreDelegates::OnEnginePreExit.AddUObject(this, &UMikdashSaveSystem::HandlePreExit);
    }

    UE_LOG(LogMikdashSave, Log, TEXT("Mikdash save system ready: %d manual slots plus autosave, record version %d"),
           SlotCount, MikdashSave::CurrentRecordVersion);
}

void UMikdashSaveSystem::Deinitialize()
{
    // Deinitialize also runs on a clean shutdown, and it runs before OnEnginePreExit in
    // some paths, so the quit autosave is attempted from whichever arrives first and
    // guarded by bQuitAutosaveDone rather than being written twice.
    if (bAutosaveOnQuit)
    {
        HandlePreExit();
    }

    if (TickHandle.IsValid())
    {
        FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
        TickHandle.Reset();
    }
    if (PreExitHandle.IsValid())
    {
        FCoreDelegates::OnEnginePreExit.Remove(PreExitHandle);
        PreExitHandle.Reset();
    }

    Super::Deinitialize();
}

UMikdashSaveSystem* UMikdashSaveSystem::Get(const UObject* WorldContext)
{
    if (!WorldContext)
    {
        return nullptr;
    }
    const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
    UGameInstance* Instance = World ? World->GetGameInstance() : nullptr;
    return Instance ? Instance->GetSubsystem<UMikdashSaveSystem>() : nullptr;
}

// ---------------------------------------------------------------------------
// slots
// ---------------------------------------------------------------------------

FString UMikdashSaveSystem::MakeSlotName(int32 SlotIndex) const
{
    if (SlotIndex >= SlotCount)
    {
        return SlotNamePrefix + TEXT("_Auto");
    }
    const int32 Clamped = FMath::Clamp(SlotIndex, 0, SlotCount - 1);
    return FString::Printf(TEXT("%s_%02d"), *SlotNamePrefix, Clamped);
}

bool UMikdashSaveSystem::ReadSlot(int32 SlotIndex, TArray<uint8>& OutBytes) const
{
    OutBytes.Reset();
    ISaveGameSystem* System = IPlatformFeaturesModule::Get().GetSaveGameSystem();
    if (!System)
    {
        return false;
    }
    const FString Name = MakeSlotName(SlotIndex);
    if (!System->DoesSaveGameExist(*Name, UserIndex))
    {
        return false;
    }
    return System->LoadGame(false, *Name, UserIndex, OutBytes);
}

EMikdashSaveError UMikdashSaveSystem::ToSaveError(MikdashSave::ESaveDecodeError Error)
{
    switch (Error)
    {
    case MikdashSave::ESaveDecodeError::Ok:                    return EMikdashSaveError::None;
    case MikdashSave::ESaveDecodeError::BufferTooSmall:        return EMikdashSaveError::BufferTooSmall;
    case MikdashSave::ESaveDecodeError::BadMagic:              return EMikdashSaveError::BadMagic;
    case MikdashSave::ESaveDecodeError::UnsupportedFormat:     return EMikdashSaveError::UnsupportedFormat;
    case MikdashSave::ESaveDecodeError::VersionTooOld:         return EMikdashSaveError::VersionTooOld;
    case MikdashSave::ESaveDecodeError::VersionTooNew:         return EMikdashSaveError::VersionTooNew;
    case MikdashSave::ESaveDecodeError::PayloadTooLarge:       return EMikdashSaveError::PayloadTooLarge;
    case MikdashSave::ESaveDecodeError::LengthMismatch:        return EMikdashSaveError::LengthMismatch;
    case MikdashSave::ESaveDecodeError::ChecksumMismatch:      return EMikdashSaveError::ChecksumMismatch;
    case MikdashSave::ESaveDecodeError::PayloadUnderrun:       return EMikdashSaveError::PayloadUnderrun;
    case MikdashSave::ESaveDecodeError::PayloadTrailingBytes:  return EMikdashSaveError::PayloadTrailing;
    case MikdashSave::ESaveDecodeError::FieldOutOfRange:       return EMikdashSaveError::FieldOutOfRange;
    }
    return EMikdashSaveError::ReadFailed;
}

FText UMikdashSaveSystem::DescribeError(EMikdashSaveError Error)
{
    // Keys are the ones already in SourceAssets/localization-review/strings.json, several
    // of which the author has reviewed. Several decode errors deliberately share a key:
    // "the payload failed its checksum" and "an array count exceeded its ceiling" are the
    // same event to a visitor -- the file is damaged -- and giving each its own sentence
    // would be handing him a diagnostic to read rather than an answer. The precise code is
    // in the log and in FMikdashSaveSlotInfo::Error for anyone debugging it.
    static const TMap<EMikdashSaveError, FName> Keys = {
        { EMikdashSaveError::SlotEmpty,         TEXT("save.empty") },
        { EMikdashSaveError::ReadFailed,        TEXT("save.loadFailed") },
        { EMikdashSaveError::BufferTooSmall,    TEXT("save.truncated") },
        { EMikdashSaveError::BadMagic,          TEXT("save.corrupt") },
        { EMikdashSaveError::UnsupportedFormat, TEXT("save.corrupt") },
        { EMikdashSaveError::VersionTooOld,     TEXT("save.tooOld") },
        { EMikdashSaveError::VersionTooNew,     TEXT("save.tooNew") },
        { EMikdashSaveError::PayloadTooLarge,   TEXT("save.corrupt") },
        { EMikdashSaveError::LengthMismatch,    TEXT("save.truncated") },
        { EMikdashSaveError::ChecksumMismatch,  TEXT("save.corrupt") },
        { EMikdashSaveError::PayloadUnderrun,   TEXT("save.truncated") },
        { EMikdashSaveError::PayloadTrailing,   TEXT("save.corrupt") },
        { EMikdashSaveError::FieldOutOfRange,   TEXT("save.corrupt") },
    };

    if (Error == EMikdashSaveError::None)
    {
        return FText::GetEmpty();
    }

    if (const FName* Key = Keys.Find(Error))
    {
        if (UMikdashLocalization* Loc = UMikdashLocalization::Get(GEngine ? GEngine->GetCurrentPlayWorld() : nullptr))
        {
            if (Loc->HasKey(*Key))
            {
                return Loc->Text(*Key);
            }
        }
    }

    // No localization subsystem -- a commandlet, or a failure before it came up. The
    // decoder's own English wording is used rather than an empty FText, because an
    // unexplained refusal on a load screen is only marginally better than a crash.
    for (int32 Index = 0; Index <= static_cast<int32>(MikdashSave::ESaveDecodeError::FieldOutOfRange); ++Index)
    {
        const MikdashSave::ESaveDecodeError Candidate = static_cast<MikdashSave::ESaveDecodeError>(Index);
        if (ToSaveError(Candidate) == Error)
        {
            return FText::FromString(FString(ANSI_TO_TCHAR(MikdashSave::DescribeError(Candidate))));
        }
    }
    if (Error == EMikdashSaveError::SlotEmpty)
    {
        return FText::FromString(TEXT("Empty"));
    }
    return FText::FromString(TEXT("The save file could not be read"));
}

FMikdashSaveSlotInfo UMikdashSaveSystem::ScanSlot(int32 SlotIndex) const
{
    FMikdashSaveSlotInfo Info;
    Info.SlotIndex = SlotIndex;
    Info.SlotName = MakeSlotName(SlotIndex);

    TArray<uint8> Bytes;
    if (!ReadSlot(SlotIndex, Bytes))
    {
        ISaveGameSystem* System = IPlatformFeaturesModule::Get().GetSaveGameSystem();
        const bool bExists = System && System->DoesSaveGameExist(*Info.SlotName, UserIndex);
        Info.bExists = bExists;
        Info.Error = bExists ? EMikdashSaveError::ReadFailed : EMikdashSaveError::SlotEmpty;
        Info.ErrorText = DescribeError(Info.Error);
        return Info;
    }

    Info.bExists = true;

    // The whole record is decoded, not just the header. Listing eight slots means eight
    // decodes of a few kilobytes each, which is nothing, and it means a slot that would
    // fail on load is shown as broken in the list rather than looking fine until it is
    // clicked. Peeking at only the header would hide exactly the corruption that matters.
    MikdashSave::FSaveRecord Record;
    MikdashSave::FMigrationReport Report;
    const MikdashSave::ESaveDecodeError Error =
        MikdashSave::Decode(Bytes.GetData(), static_cast<size_t>(Bytes.Num()), Record, Report);

    Info.RecordVersion = MikdashSave::PeekRecordVersion(Bytes.GetData(), static_cast<size_t>(Bytes.Num()));
    if (Error != MikdashSave::ESaveDecodeError::Ok)
    {
        Info.Error = ToSaveError(Error);
        Info.ErrorText = DescribeError(Info.Error);
        return Info;
    }

    Info.bValid = true;
    Info.Error = EMikdashSaveError::None;
    const FString StoredLabel = ToUtf8String(Record.SlotLabel);
    if (!StoredLabel.IsEmpty())
    {
        Info.Label = FText::FromString(StoredLabel);
    }
    else if (SlotIndex >= SlotCount)
    {
        Info.Label = UMikdashLocalization::TextStatic(GEngine ? GEngine->GetCurrentPlayWorld() : nullptr,
                                                     TEXT("save.autosave"));
    }
    Info.SaveTimeUtc = FDateTime::FromUnixTimestamp(static_cast<int64>(Record.SaveTimeUnixSeconds));
    Info.PlayTimeSeconds = static_cast<float>(Record.PlayTimeSeconds);
    Info.MapName = ToUtf8String(Record.MapName);
    Info.bWouldMigrate = Report.StepsApplied > 0;
    Info.CompletedStopCount = static_cast<int32>(Record.CompletedTourStops.size());
    Info.CodexEntryCount = static_cast<int32>(Record.UnlockedCodexEntries.size());
    Info.TimeOfDayHours = Record.TimeOfDayHours;
    return Info;
}

TArray<FMikdashSaveSlotInfo> UMikdashSaveSystem::GetSlotInfos(bool bRefresh)
{
    if (bRefresh || !bSlotCacheValid)
    {
        CachedSlots.Reset(SlotCount + 1);
        for (int32 Index = 0; Index <= SlotCount; ++Index)   // <= : the autosave slot is last
        {
            CachedSlots.Add(ScanSlot(Index));
        }
        bSlotCacheValid = true;
    }
    return CachedSlots;
}

FMikdashSaveSlotInfo UMikdashSaveSystem::GetSlotInfo(int32 SlotIndex, bool bRefresh)
{
    const TArray<FMikdashSaveSlotInfo> All = GetSlotInfos(bRefresh);
    if (All.IsValidIndex(SlotIndex))
    {
        return All[SlotIndex];
    }
    FMikdashSaveSlotInfo Info;
    Info.SlotIndex = SlotIndex;
    Info.SlotName = MakeSlotName(SlotIndex);
    Info.ErrorText = DescribeError(EMikdashSaveError::SlotEmpty);
    return Info;
}

bool UMikdashSaveSystem::HasAnyLoadableSave()
{
    for (const FMikdashSaveSlotInfo& Info : GetSlotInfos(true))
    {
        if (Info.bValid)
        {
            return true;
        }
    }
    return false;
}

FMikdashSaveSlotInfo UMikdashSaveSystem::GetContinueSlot()
{
    FMikdashSaveSlotInfo Best;
    Best.SlotIndex = -1;
    for (const FMikdashSaveSlotInfo& Info : GetSlotInfos(true))
    {
        if (!Info.bValid)
        {
            continue;
        }
        if (Best.SlotIndex < 0 || Info.SaveTimeUtc > Best.SaveTimeUtc)
        {
            Best = Info;
        }
    }
    return Best;
}

int32 UMikdashSaveSystem::FindFirstEmptySlot()
{
    const TArray<FMikdashSaveSlotInfo> All = GetSlotInfos(true);
    for (int32 Index = 0; Index < SlotCount; ++Index)
    {
        if (All.IsValidIndex(Index) && !All[Index].bExists)
        {
            return Index;
        }
    }
    return -1;
}

// ---------------------------------------------------------------------------
// capture and apply
// ---------------------------------------------------------------------------

APlayerController* UMikdashSaveSystem::GetLocalController() const
{
    const UGameInstance* Instance = GetGameInstance();
    return Instance ? Instance->GetFirstLocalPlayerController() : nullptr;
}

AMikdashTimeOfDay* UMikdashSaveSystem::FindTimeOfDay() const
{
    const UGameInstance* Instance = GetGameInstance();
    UWorld* World = Instance ? Instance->GetWorld() : nullptr;
    if (!World)
    {
        return nullptr;
    }
    for (TActorIterator<AMikdashTimeOfDay> It(World); It; ++It)
    {
        return *It;
    }
    return nullptr;
}

UMikdashSettingsSubsystem* UMikdashSaveSystem::GetSettings() const
{
    UGameInstance* Instance = GetGameInstance();
    return Instance ? Instance->GetSubsystem<UMikdashSettingsSubsystem>() : nullptr;
}

void UMikdashSaveSystem::CaptureSessionState(MikdashSave::FSaveRecord& Record) const
{
    Record.CompletedTourStops.clear();
    Record.CompletedTourStops.reserve(static_cast<size_t>(CompletedTourStopOrder.Num()));
    for (const FName& Stop : CompletedTourStopOrder)
    {
        Record.CompletedTourStops.push_back(FromFString(Stop.ToString()));
    }

    Record.UnlockedCodexEntries.clear();
    Record.UnlockedCodexEntries.reserve(static_cast<size_t>(UnlockedCodexOrder.Num()));
    for (const FName& Entry : UnlockedCodexOrder)
    {
        Record.UnlockedCodexEntries.push_back(FromFString(Entry.ToString()));
    }

    Record.CurrentTourStop = FromFString(CurrentTourStop.IsNone() ? FString() : CurrentTourStop.ToString());
    Record.bTourActive = bTourActive;

    Record.Photo.FieldOfViewDegrees = Photo.FieldOfViewDegrees;
    Record.Photo.ExposureCompensation = Photo.ExposureCompensation;
    Record.Photo.FocusDistanceCm = Photo.FocusDistanceCm;
    Record.Photo.Aperture = Photo.Aperture;
    Record.Photo.RollDegrees = Photo.RollDegrees;
    Record.Photo.ResolutionMultiplier = static_cast<uint32_t>(FMath::Clamp(Photo.ResolutionMultiplier, 1, 16));
    Record.Photo.bHideInterface = Photo.bHideInterface;
    Record.Photo.LookId = FromFString(Photo.LookId.IsNone() ? FString() : Photo.LookId.ToString());
}

void UMikdashSaveSystem::CaptureOptions(MikdashSave::FSaveRecord& Record) const
{
    Record.Options.clear();

    const UMikdashSettingsSubsystem* Settings = GetSettings();
    if (!Settings)
    {
        // Recorded rather than silently omitted: a slot with no options block is a slot
        // written without a settings subsystem, and GetSnapshotOptions must be able to
        // say so instead of handing back a default record that looks like a real one.
        return;
    }

    // Reflection over FMikdashSettingsRecord rather than a hand-written field list. That
    // struct belongs to the settings agent; when they add a slider it appears in the
    // snapshot on its own, and when they remove one the key simply stops being written.
    // The save format stores an opaque typed key/value list precisely so this can be true.
    const FMikdashSettingsRecord Snapshot = Settings->GetRecord();
    const UScriptStruct* Struct = FMikdashSettingsRecord::StaticStruct();

    for (TFieldIterator<FProperty> It(Struct); It; ++It)
    {
        const FProperty* Property = *It;
        const void* Value = Property->ContainerPtrToValuePtr<void>(&Snapshot);
        const FString Key = TEXT("settings.") + Property->GetName();

        MikdashSave::FOptionValue Option;
        Option.Key = FromFString(Key);

        if (const FBoolProperty* AsBool = CastField<FBoolProperty>(Property))
        {
            Option.Type = MikdashSave::EOptionType::Bool;
            Option.BoolValue = AsBool->GetPropertyValue(Value);
        }
        else if (const FIntProperty* AsInt = CastField<FIntProperty>(Property))
        {
            Option.Type = MikdashSave::EOptionType::Int;
            Option.IntValue = AsInt->GetPropertyValue(Value);
        }
        else if (const FFloatProperty* AsFloat = CastField<FFloatProperty>(Property))
        {
            Option.Type = MikdashSave::EOptionType::Float;
            Option.FloatValue = AsFloat->GetPropertyValue(Value);
        }
        else if (const FDoubleProperty* AsDouble = CastField<FDoubleProperty>(Property))
        {
            Option.Type = MikdashSave::EOptionType::Float;
            Option.FloatValue = static_cast<float>(AsDouble->GetPropertyValue(Value));
        }
        else if (const FStrProperty* AsString = CastField<FStrProperty>(Property))
        {
            Option.Type = MikdashSave::EOptionType::String;
            Option.StringValue = FromFString(AsString->GetPropertyValue(Value));
        }
        else
        {
            // A property type the format has no slot for. Skipped rather than guessed at;
            // the count in the receipt makes the omission visible.
            continue;
        }

        if (Record.Options.size() >= static_cast<size_t>(MikdashSave::MaxOptionCount))
        {
            break;
        }
        Record.Options.push_back(Option);
    }

    // A marker so a reader can tell "no settings subsystem" from "a settings record with
    // no fields", which are different failures.
    if (Record.Options.size() < static_cast<size_t>(MikdashSave::MaxOptionCount))
    {
        Record.Options.push_back(MakeBoolOption(TEXT("settings.__captured"), true));
    }
}

bool UMikdashSaveSystem::CaptureRecord(MikdashSave::FSaveRecord& Record, const FString& Label) const
{
    Record.RecordVersion = MikdashSave::CurrentRecordVersion;
    Record.SlotLabel = FromFString(Label);
    Record.SaveTimeUnixSeconds = static_cast<uint64_t>(FMath::Max<int64>(0, FDateTime::UtcNow().ToUnixTimestamp()));
    Record.PlayTimeSeconds = static_cast<uint64_t>(FMath::Max(0.0, AccumulatedPlayTimeSeconds));
    Record.BuildNumber = static_cast<uint32_t>(FMath::Max(0, BuildNumber));

    const UGameInstance* Instance = GetGameInstance();
    if (const UWorld* World = Instance ? Instance->GetWorld() : nullptr)
    {
        Record.MapName = FromFString(World->GetMapName());
    }

    if (const APlayerController* Controller = GetLocalController())
    {
        // The pawn's location when there is one, the camera's when there is not: the front
        // end freezes the pawn and takes the view during the title screen, and a save made
        // there must not record the origin.
        FVector Location = FVector::ZeroVector;
        FRotator Rotation = FRotator::ZeroRotator;
        if (const APawn* Pawn = Controller->GetPawn())
        {
            Location = Pawn->GetActorLocation();
            Rotation = Controller->GetControlRotation();
        }
        else
        {
            Controller->GetPlayerViewPoint(Location, Rotation);
        }

        Record.PlayerTransform.X = Location.X;
        Record.PlayerTransform.Y = Location.Y;
        Record.PlayerTransform.Z = Location.Z;
        Record.PlayerTransform.Pitch = MikdashSave::NormalizeDegrees(Rotation.Pitch);
        Record.PlayerTransform.Yaw = MikdashSave::NormalizeDegrees(Rotation.Yaw);
        Record.PlayerTransform.Roll = MikdashSave::NormalizeDegrees(Rotation.Roll);
    }

    if (const AMikdashTimeOfDay* Sky = FindTimeOfDay())
    {
        Record.TimeOfDayHours = MikdashSave::ClampTimeOfDayHours(Sky->GetTimeOfDayHours());
        Record.bTimeOfDayPaused = Sky->IsFrozen();
    }

    CaptureSessionState(Record);
    CaptureOptions(Record);

    const UWorld* World = Instance ? Instance->GetWorld() : nullptr;
    MikdashSaveScene::Identity Identity;
    FString SceneError;
    const bool bValidFrame = AMikdashSceneUnits::Resolve(World, Identity.Frame, SceneError);
    Identity.MapPackage = CurrentMapPackage(World);
    const APlayerController* Controller = GetLocalController();
    const ACharacter* Walker = Controller ? Cast<ACharacter>(Controller->GetPawn()) : nullptr;
    Identity.HasWalkingPosition = Walker && SafeWalkingPosition(Walker, Walker->GetActorLocation());
    if (!bValidFrame)
        UE_LOG(LogMikdashSave, Warning, TEXT("Saving progress with an explicitly invalid spatial identity: %s"), *SceneError);
    if (!MikdashSaveScene::Store(Record, bValidFrame ? &Identity : nullptr))
    {
        UE_LOG(LogMikdashSave, Error, TEXT("Save refused: no extension capacity for required scene identity. Existing slot unchanged."));
        return false;
    }
    return true;
}

void UMikdashSaveSystem::AdoptSessionState(const MikdashSave::FSaveRecord& Record)
{
    CompletedTourStops.Reset();
    CompletedTourStopOrder.Reset();
    for (const std::string& Stop : Record.CompletedTourStops)
    {
        const FString AsString = ToUtf8String(Stop);
        if (AsString.IsEmpty())
        {
            continue;
        }
        const FName Id(*AsString);
        bool bAlready = false;
        CompletedTourStops.Add(Id, &bAlready);
        if (!bAlready)
        {
            CompletedTourStopOrder.Add(Id);
        }
    }

    UnlockedCodex.Reset();
    UnlockedCodexOrder.Reset();
    for (const std::string& Entry : Record.UnlockedCodexEntries)
    {
        const FString AsString = ToUtf8String(Entry);
        if (AsString.IsEmpty())
        {
            continue;
        }
        const FName Id(*AsString);
        bool bAlready = false;
        UnlockedCodex.Add(Id, &bAlready);
        if (!bAlready)
        {
            UnlockedCodexOrder.Add(Id);
        }
    }

    const FString CurrentStopString = ToUtf8String(Record.CurrentTourStop);
    CurrentTourStop = CurrentStopString.IsEmpty() ? NAME_None : FName(*CurrentStopString);
    bTourActive = Record.bTourActive;

    Photo.FieldOfViewDegrees = Record.Photo.FieldOfViewDegrees;
    Photo.ExposureCompensation = Record.Photo.ExposureCompensation;
    Photo.FocusDistanceCm = Record.Photo.FocusDistanceCm;
    Photo.Aperture = Record.Photo.Aperture;
    Photo.RollDegrees = Record.Photo.RollDegrees;
    Photo.ResolutionMultiplier = static_cast<int32>(FMath::Clamp<uint32_t>(Record.Photo.ResolutionMultiplier, 1u, 16u));
    Photo.bHideInterface = Record.Photo.bHideInterface;
    const FString LookString = ToUtf8String(Record.Photo.LookId);
    Photo.LookId = LookString.IsEmpty() ? NAME_None : FName(*LookString);

    AccumulatedPlayTimeSeconds = static_cast<double>(Record.PlayTimeSeconds);

    SnapshotOptions = Record.Options;
    bHasSnapshotOptions = false;
    for (const auto& Option : SnapshotOptions)
        if (Option.Key.compare(0,9,"settings.") == 0) { bHasSnapshotOptions = true; break; }
}

void UMikdashSaveSystem::RestoreSafeCurrentWorldPosition(const FString& Reason)
{
    APlayerController* Controller = GetLocalController();
    ACharacter* Walker = Controller ? Cast<ACharacter>(Controller->GetPawn()) : nullptr;
    if (Walker && SafeWalkingPosition(Walker, Walker->GetActorLocation()))
    {
        LastLocationRestoreOutcome = EMikdashLocationRestoreOutcome::CurrentSafePositionRetained;
        LastLocationRestoreMessage = TEXT("Your progress was restored. ") + Reason
            + TEXT(" You remain at your current safe walking position.");
        return;
    }
    if (Walker && Walker->GetWorld())
    {
        TArray<APlayerStart*> Starts;
        for (TActorIterator<APlayerStart> It(Walker->GetWorld()); It; ++It) Starts.Add(*It);
        Starts.Sort([](const APlayerStart& A, const APlayerStart& B)
            { return A.GetFName().LexicalLess(B.GetFName()); });
        for (APlayerStart* Start : Starts)
        {
            const FVector Position = Start->GetActorLocation();
            if (!SafeWalkingPosition(Walker, Position)) continue;
            if (!Walker->SetActorLocation(Position, false, nullptr, ETeleportType::TeleportPhysics)) continue;
            Walker->GetCharacterMovement()->StopMovementImmediately();
            Controller->SetControlRotation(Start->GetActorRotation());
            LastLocationRestoreOutcome = EMikdashLocationRestoreOutcome::CurrentWorldSpawnUsed;
            LastLocationRestoreMessage = TEXT("Your progress was restored. ") + Reason
                + TEXT(" You have been placed at a checked starting point in the current scene.");
            return;
        }
    }
    // No character, no real floor trace, or no safe spawn: leave all transforms alone.
    // In particular a possessed dove must never receive a saved walking transform.
    LastLocationRestoreOutcome = EMikdashLocationRestoreOutcome::PositionUnchangedUnverified;
    LastLocationRestoreMessage = TEXT("Your progress was restored. ") + Reason
        + TEXT(" A safe walking position could not be checked, so your current position was left unchanged.");
}

void UMikdashSaveSystem::ApplyRecord(const MikdashSave::FSaveRecord& Record)
{
    AdoptSessionState(Record);

    if (bRestorePlayerTransform)
    {
        const UGameInstance* Instance = GetGameInstance();
        const UWorld* World = Instance ? Instance->GetWorld() : nullptr;
        MikdashSceneUnits::Frame Frame;
        FString SceneError;
        const bool bValidFrame = AMikdashSceneUnits::Resolve(World, Frame, SceneError);
        const auto Decision = MikdashSaveScene::Evaluate(Record, bValidFrame ? &Frame : nullptr, CurrentMapPackage(World));
        const bool bSameLayout = Decision == MikdashSaveScene::Decision::RestorePosition
            || Decision == MikdashSaveScene::Decision::RestoreLegacyPosition;
        APlayerController* Controller = GetLocalController();
        APawn* Pawn = Controller ? Controller->GetPawn() : nullptr;
        if (bSameLayout && Cast<ACharacter>(Pawn))
        {
            const FVector Location(Record.PlayerTransform.X, Record.PlayerTransform.Y, Record.PlayerTransform.Z);
            const FRotator Rotation(static_cast<float>(Record.PlayerTransform.Pitch),
                                    static_cast<float>(Record.PlayerTransform.Yaw),
                                    static_cast<float>(Record.PlayerTransform.Roll));
            if (Pawn->SetActorLocation(Location, /*bSweep=*/false, nullptr, ETeleportType::TeleportPhysics))
            {
                // Teleport, not sweep: the saved position is a position the visitor was
                // legitimately standing in, and sweeping there from wherever they are now
                // can stop short against geometry they were never meant to walk through.
                Pawn->SetActorRotation(FRotator(0.0f, Rotation.Yaw, 0.0f), ETeleportType::TeleportPhysics);
                Controller->SetControlRotation(Rotation);
                LastLocationRestoreOutcome = EMikdashLocationRestoreOutcome::SavedPositionRestored;
                LastLocationRestoreMessage = TEXT("Your progress and saved walking position were restored.");
            }
            else RestoreSafeCurrentWorldPosition(TEXT("The saved walking position could not be applied."));
        }
        else
        {
            FString Reason = TEXT("The saved location belongs to a different scene layout.");
            if (Decision == MikdashSaveScene::Decision::InvalidCurrentIdentity)
                Reason = TEXT("The current scene's coordinate identity could not be verified.");
            else if (Decision == MikdashSaveScene::Decision::InvalidSavedIdentity)
                Reason = TEXT("The saved coordinate identity could not be verified.");
            else if (Decision == MikdashSaveScene::Decision::NoWalkingPosition || !Cast<ACharacter>(Pawn))
                Reason = TEXT("There is no compatible saved walking position to apply.");
            RestoreSafeCurrentWorldPosition(Reason);
        }
    }
    else
    {
        LastLocationRestoreOutcome = EMikdashLocationRestoreOutcome::Disabled;
        LastLocationRestoreMessage = TEXT("Your progress was restored; restoring a saved position is disabled.");
    }
    UE_LOG(LogMikdashSave, Log, TEXT("%s"), *LastLocationRestoreMessage);

    if (bRestoreTimeOfDay)
    {
        if (AMikdashTimeOfDay* Sky = FindTimeOfDay())
        {
            Sky->SetTimeOfDayHours(MikdashSave::ClampTimeOfDayHours(Record.TimeOfDayHours));
            Sky->SetFrozen(Record.bTimeOfDayPaused);
            Sky->ApplyNow();
        }
    }

    OnStateRestored.Broadcast();
}

// ---------------------------------------------------------------------------
// saving and loading
// ---------------------------------------------------------------------------

bool UMikdashSaveSystem::WriteSlot(int32 SlotIndex, const MikdashSave::FSaveRecord& Record)
{
    ISaveGameSystem* System = IPlatformFeaturesModule::Get().GetSaveGameSystem();
    if (!System)
    {
        UE_LOG(LogMikdashSave, Error, TEXT("No save game system; slot %d not written"), SlotIndex);
        return false;
    }

    const std::vector<uint8_t> Encoded = MikdashSave::Encode(Record);

    // Encode is the only writer, and its output is what Decode is tested against, so a
    // record that cannot be read back is a bug worth catching here rather than the next
    // time the visitor tries to load. This costs one decode of a few kilobytes per save.
    {
        MikdashSave::FSaveRecord Verify;
        MikdashSave::FMigrationReport Report;
        const MikdashSave::ESaveDecodeError Error =
            MikdashSave::Decode(Encoded.data(), Encoded.size(), Verify, Report);
        if (Error != MikdashSave::ESaveDecodeError::Ok)
        {
            UE_LOG(LogMikdashSave, Error,
                   TEXT("Refusing to write slot %d: the encoded record does not decode (%s). Nothing was written."),
                   SlotIndex, ANSI_TO_TCHAR(MikdashSave::DescribeError(Error)));
            return false;
        }
    }

    TArray<uint8> Bytes;
    Bytes.Append(Encoded.data(), static_cast<int32>(Encoded.size()));

    const FString Name = MakeSlotName(SlotIndex);
    bool bSaved = false;

    if (bAsyncSaves)
    {
        TSharedRef<TArray<uint8>> Shared = MakeShared<TArray<uint8>>(MoveTemp(Bytes));
        TWeakObjectPtr<UMikdashSaveSystem> WeakThis(this);
        const int32 CapturedSlot = SlotIndex;
        System->SaveGameAsync(false, *Name, FPlatformMisc::GetPlatformUserForUserIndex(UserIndex), Shared,
            [WeakThis, CapturedSlot](const FString&, FPlatformUserId, bool bSuccess)
            {
                if (UMikdashSaveSystem* Self = WeakThis.Get())
                {
                    Self->bSlotCacheValid = false;
                    Self->OnSaveCompleted.Broadcast(CapturedSlot, bSuccess);
                }
            });
        // The request was accepted; the outcome arrives on the delegate.
        bSaved = true;
    }
    else
    {
        bSaved = System->SaveGame(false, *Name, UserIndex, Bytes);
        OnSaveCompleted.Broadcast(SlotIndex, bSaved);
    }

    bSlotCacheValid = false;
    if (!bSaved)
    {
        UE_LOG(LogMikdashSave, Error, TEXT("Slot %d (%s) failed to write"), SlotIndex, *Name);
    }
    return bSaved;
}

bool UMikdashSaveSystem::SaveToSlot(int32 SlotIndex, const FString& Label)
{
    MikdashSave::FSaveRecord Record;
    if (!CaptureRecord(Record, Label)) { OnSaveCompleted.Broadcast(SlotIndex, false); return false; }
    const bool bSaved = WriteSlot(SlotIndex, Record);
    if (bSaved)
    {
        UE_LOG(LogMikdashSave, Log, TEXT("Saved slot %d: %d stops, %d codex, play time %.0f s"),
               SlotIndex, static_cast<int32>(Record.CompletedTourStops.size()),
               static_cast<int32>(Record.UnlockedCodexEntries.size()),
               static_cast<double>(Record.PlayTimeSeconds));
    }
    return bSaved;
}

bool UMikdashSaveSystem::Autosave(EMikdashSaveReason Reason)
{
    if (!bAutosaveEnabled)
    {
        return false;
    }
    if (Reason == EMikdashSaveReason::TourStop && !bAutosaveAtTourStops)
    {
        return false;
    }

    const double Now = FPlatformTime::Seconds();
    if (Reason != EMikdashSaveReason::Quit &&
        Now - LastAutosaveRealSeconds < static_cast<double>(FMath::Max(MinimumAutosaveIntervalSeconds, 0.0f)))
    {
        return false;
    }

    // Deliberately no label. A label written here would be a string in whichever language
    // was current at the time, and a slot saved in Hebrew would still read Hebrew after
    // the visitor switched to English. ScanSlot names the autosave slot from the string
    // table instead, so it follows the language rather than the moment it was written.
    MikdashSave::FSaveRecord Record;
    if (!CaptureRecord(Record, FString())) { OnSaveCompleted.Broadcast(GetAutosaveSlotIndex(), false); return false; }
    const bool bSaved = WriteSlot(GetAutosaveSlotIndex(), Record);
    if (bSaved)
    {
        LastAutosaveRealSeconds = Now;
        NextPeriodicAutosaveRealSeconds = Now + static_cast<double>(FMath::Max(PeriodicAutosaveSeconds, 0.0f));
    }
    return bSaved;
}

bool UMikdashSaveSystem::LoadFromSlot(int32 SlotIndex)
{
    LastLocationRestoreOutcome = EMikdashLocationRestoreOutcome::NotAttempted;
    LastLocationRestoreMessage.Reset();
    TArray<uint8> Bytes;
    if (!ReadSlot(SlotIndex, Bytes))
    {
        ISaveGameSystem* System = IPlatformFeaturesModule::Get().GetSaveGameSystem();
        const bool bExists = System && System->DoesSaveGameExist(*MakeSlotName(SlotIndex), UserIndex);
        const EMikdashSaveError Error = bExists ? EMikdashSaveError::ReadFailed : EMikdashSaveError::SlotEmpty;
        OnLoadCompleted.Broadcast(SlotIndex, false, Error);
        return false;
    }

    // Decode in full into a local record BEFORE anything live is touched. This is what
    // makes a corrupt file cost a refused load rather than a half-restored world.
    MikdashSave::FSaveRecord Record;
    MikdashSave::FMigrationReport Report;
    const MikdashSave::ESaveDecodeError DecodeError =
        MikdashSave::Decode(Bytes.GetData(), static_cast<size_t>(Bytes.Num()), Record, Report);

    if (DecodeError != MikdashSave::ESaveDecodeError::Ok)
    {
        const EMikdashSaveError Error = ToSaveError(DecodeError);
        UE_LOG(LogMikdashSave, Warning, TEXT("Slot %d refused: %s. Nothing was changed."),
               SlotIndex, ANSI_TO_TCHAR(MikdashSave::DescribeError(DecodeError)));
        OnLoadCompleted.Broadcast(SlotIndex, false, Error);
        return false;
    }

    if (Report.StepsApplied > 0)
    {
        UE_LOG(LogMikdashSave, Log,
               TEXT("Slot %d migrated v%d -> v%d in %d step(s): %d tour stop(s) dropped, %d field(s) defaulted%s%s"),
               SlotIndex, Report.FromVersion, Report.ToVersion, Report.StepsApplied,
               Report.TourStopsDropped, Report.FieldsDefaulted,
               Report.bCoordinatesConverted ? TEXT(", coordinates converted") : TEXT(""),
               Report.bTimeOfDayPresetOutOfRange ? TEXT(", time-of-day preset out of range") : TEXT(""));
    }

    ApplyRecord(Record);
    bSlotCacheValid = false;
    OnLoadCompleted.Broadcast(SlotIndex, true, EMikdashSaveError::None);
    return true;
}

bool UMikdashSaveSystem::ContinueFromLast()
{
    const FMikdashSaveSlotInfo Slot = GetContinueSlot();
    if (Slot.SlotIndex < 0)
    {
        OnLoadCompleted.Broadcast(-1, false, EMikdashSaveError::SlotEmpty);
        return false;
    }
    return LoadFromSlot(Slot.SlotIndex);
}

bool UMikdashSaveSystem::DeleteSlot(int32 SlotIndex)
{
    ISaveGameSystem* System = IPlatformFeaturesModule::Get().GetSaveGameSystem();
    if (!System)
    {
        return false;
    }
    const bool bDeleted = System->DeleteGame(false, *MakeSlotName(SlotIndex), UserIndex);
    bSlotCacheValid = false;
    return bDeleted;
}

void UMikdashSaveSystem::ResetSessionState()
{
    LastLocationRestoreOutcome = EMikdashLocationRestoreOutcome::NotAttempted;
    LastLocationRestoreMessage.Reset();
    CompletedTourStops.Reset();
    CompletedTourStopOrder.Reset();
    UnlockedCodex.Reset();
    UnlockedCodexOrder.Reset();
    CurrentTourStop = NAME_None;
    bTourActive = false;
    Photo = FMikdashPhotoState();
    SnapshotOptions.clear();
    bHasSnapshotOptions = false;
    AccumulatedPlayTimeSeconds = 0.0;
    bQuitAutosaveDone = false;
}

// ---------------------------------------------------------------------------
// tour and codex
// ---------------------------------------------------------------------------

void UMikdashSaveSystem::NotifyTourStopReached(FName StopId)
{
    if (StopId.IsNone())
    {
        return;
    }
    bool bAlready = false;
    CompletedTourStops.Add(StopId, &bAlready);
    if (!bAlready)
    {
        CompletedTourStopOrder.Add(StopId);
    }
    CurrentTourStop = StopId;
    Autosave(EMikdashSaveReason::TourStop);
}

void UMikdashSaveSystem::SetTourActive(bool bActive)
{
    bTourActive = bActive;
}

bool UMikdashSaveSystem::IsTourStopComplete(FName StopId) const
{
    return CompletedTourStops.Contains(StopId);
}

TArray<FName> UMikdashSaveSystem::GetCompletedTourStops() const
{
    return CompletedTourStopOrder;
}

void UMikdashSaveSystem::SetCurrentTourStop(FName StopId)
{
    CurrentTourStop = StopId;
}

bool UMikdashSaveSystem::UnlockCodexEntry(FName EntryId)
{
    if (EntryId.IsNone())
    {
        return false;
    }
    bool bAlready = false;
    UnlockedCodex.Add(EntryId, &bAlready);
    if (bAlready)
    {
        return false;
    }
    UnlockedCodexOrder.Add(EntryId);
    OnCodexEntryUnlocked.Broadcast(EntryId);
    return true;
}

bool UMikdashSaveSystem::IsCodexEntryUnlocked(FName EntryId) const
{
    return UnlockedCodex.Contains(EntryId);
}

TArray<FName> UMikdashSaveSystem::GetUnlockedCodexEntries() const
{
    return UnlockedCodexOrder;
}

// ---------------------------------------------------------------------------
// photo mode, play time, options
// ---------------------------------------------------------------------------

FMikdashPhotoState UMikdashSaveSystem::GetPhotoState() const
{
    return Photo;
}

void UMikdashSaveSystem::SetPhotoState(const FMikdashPhotoState& In)
{
    Photo = In;
    Photo.ResolutionMultiplier = FMath::Clamp(Photo.ResolutionMultiplier, 1, 16);
}

float UMikdashSaveSystem::GetPlayTimeSeconds() const
{
    return static_cast<float>(AccumulatedPlayTimeSeconds);
}

FText UMikdashSaveSystem::GetPlayTimeText() const
{
    const int64 Total = static_cast<int64>(FMath::Max(0.0, AccumulatedPlayTimeSeconds));
    const int64 Hours = Total / 3600;
    const int64 Minutes = (Total % 3600) / 60;
    const int64 Seconds = Total % 60;

    // Deliberately not FText::AsNumber: this is a clock reading, and a grouping separator
    // or an Eastern Arabic digit set in a Hebrew locale would make it unreadable rather
    // than more correct. Hebrew uses Western digits for clock times.
    const FString Formatted = Hours > 0
        ? FString::Printf(TEXT("%lld:%02lld:%02lld"), Hours, Minutes, Seconds)
        : FString::Printf(TEXT("%lld:%02lld"), Minutes, Seconds);
    return FText::FromString(Formatted);
}

void UMikdashSaveSystem::SetPlayTimeCounting(bool bCounting)
{
    bPlayTimeCounting = bCounting;
}

FMikdashSettingsRecord UMikdashSaveSystem::GetSnapshotOptions(bool& bOutHadSnapshot) const
{
    FMikdashSettingsRecord Record;
    bOutHadSnapshot = false;

    if (!bHasSnapshotOptions)
    {
        return Record;
    }

    const UScriptStruct* Struct = FMikdashSettingsRecord::StaticStruct();
    int32 Applied = 0;

    for (const MikdashSave::FOptionValue& Option : SnapshotOptions)
    {
        const FString Key = ToUtf8String(Option.Key);
        if (!Key.StartsWith(TEXT("settings.")))
        {
            continue;
        }
        const FString FieldName = Key.RightChop(9);
        if (FieldName == TEXT("__captured"))
        {
            bOutHadSnapshot = true;
            continue;
        }

        FProperty* Property = Struct->FindPropertyByName(FName(*FieldName));
        if (!Property)
        {
            // A field the settings agent has since removed. Dropped, not an error: an old
            // slot must still load after their struct changes.
            continue;
        }
        void* Value = Property->ContainerPtrToValuePtr<void>(&Record);

        if (FBoolProperty* AsBool = CastField<FBoolProperty>(Property))
        {
            if (Option.Type == MikdashSave::EOptionType::Bool) { AsBool->SetPropertyValue(Value, Option.BoolValue); ++Applied; }
        }
        else if (FIntProperty* AsInt = CastField<FIntProperty>(Property))
        {
            if (Option.Type == MikdashSave::EOptionType::Int) { AsInt->SetPropertyValue(Value, Option.IntValue); ++Applied; }
        }
        else if (FFloatProperty* AsFloat = CastField<FFloatProperty>(Property))
        {
            if (Option.Type == MikdashSave::EOptionType::Float) { AsFloat->SetPropertyValue(Value, Option.FloatValue); ++Applied; }
        }
        else if (FDoubleProperty* AsDouble = CastField<FDoubleProperty>(Property))
        {
            if (Option.Type == MikdashSave::EOptionType::Float) { AsDouble->SetPropertyValue(Value, static_cast<double>(Option.FloatValue)); ++Applied; }
        }
        else if (FStrProperty* AsString = CastField<FStrProperty>(Property))
        {
            if (Option.Type == MikdashSave::EOptionType::String) { AsString->SetPropertyValue(Value, ToUtf8String(Option.StringValue)); ++Applied; }
        }
    }

    bOutHadSnapshot = bOutHadSnapshot || Applied > 0;
    return Record;
}

// ---------------------------------------------------------------------------
// tick and shutdown
// ---------------------------------------------------------------------------

bool UMikdashSaveSystem::TickSave(float DeltaTime)
{
    if (bPlayTimeCounting)
    {
        // Real seconds, not world seconds: pausing the world for the pause menu should
        // stop the clock, and the front end does that by calling SetPlayTimeCounting.
        // Using world time as well would double-count that decision.
        AccumulatedPlayTimeSeconds += static_cast<double>(FMath::Clamp(DeltaTime, 0.0f, 1.0f));
    }

    if (bAutosaveEnabled && PeriodicAutosaveSeconds > 0.0f)
    {
        const double Now = FPlatformTime::Seconds();
        if (Now >= NextPeriodicAutosaveRealSeconds)
        {
            NextPeriodicAutosaveRealSeconds = Now + static_cast<double>(PeriodicAutosaveSeconds);
            // Only once the visitor is actually in the walkthrough. Autosaving the title
            // screen would overwrite a real autosave with an empty one, which is the one
            // way this feature could destroy progress instead of protecting it.
            const APlayerController* Controller = GetLocalController();
            if (Controller && Controller->GetPawn())
            {
                Autosave(EMikdashSaveReason::Periodic);
            }
        }
    }

    return true;
}

void UMikdashSaveSystem::HandlePreExit()
{
    if (bQuitAutosaveDone || !bAutosaveOnQuit || !bAutosaveEnabled)
    {
        return;
    }
    bQuitAutosaveDone = true;

    const APlayerController* Controller = GetLocalController();
    if (!Controller || !Controller->GetPawn())
    {
        return;
    }

    // Forced synchronous. An async save at OnEnginePreExit has no thread left to finish on.
    const bool bWasAsync = bAsyncSaves;
    bAsyncSaves = false;
    Autosave(EMikdashSaveReason::Quit);
    bAsyncSaves = bWasAsync;
}
